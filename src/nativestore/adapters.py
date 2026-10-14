"""HTTP adapters run behind NativeStore's authentication and origin policy."""

import asyncio
import io
import logging
import sys
import threading
from typing import Any
from urllib.parse import urlencode

from .app import Response
from .errors import NativeStoreError


def response(status, headers, body):
    content_type = next(
        (v for k, v in headers if k.lower() == "content-type"), "application/octet-stream"
    )
    return Response(
        body, status, content_type, [(k, v) for k, v in headers if k.lower() != "content-type"]
    )


class WSGIAdapter:
    def __init__(self, application):
        if not callable(application):
            raise NativeStoreError("WSGI application must be callable")
        self.application = application

    def handle(self, ctx, path, prefix):
        captured: dict[str, Any] = {}
        chunks = []
        size = 0

        def write(chunk):
            nonlocal size
            if not isinstance(chunk, bytes):
                raise NativeStoreError("WSGI returned a non-byte chunk")
            size += len(chunk)
            if size > ctx.app.config.max_result_bytes:
                raise NativeStoreError("WSGI response exceeds configured limit")
            chunks.append(chunk)

        def start_response(status, headers, exc_info=None):
            if exc_info and captured:
                raise exc_info[1].with_traceback(exc_info[2])
            captured.update(status=int(status.split()[0]), headers=list(headers))
            return write

        environ = {
            "REQUEST_METHOD": ctx.method,
            "SCRIPT_NAME": prefix,
            "PATH_INFO": path.encode("utf-8").decode("latin-1"),
            "QUERY_STRING": urlencode(ctx.query, doseq=True),
            "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "0",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(ctx.raw_body),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "CONTENT_LENGTH": str(len(ctx.raw_body)),
        }
        for key, value in ctx.headers.items():
            name = key.upper().replace("-", "_")
            environ[name if name in ("CONTENT_TYPE", "CONTENT_LENGTH") else "HTTP_" + name] = value
        result = self.application(environ, start_response)
        try:
            for chunk in result:
                write(chunk)
        finally:
            close = getattr(result, "close", None)
            if close:
                close()
        if not captured:
            raise NativeStoreError("WSGI application did not start a response")
        return response(captured["status"], captured["headers"], b"".join(chunks))

    def close(self):
        pass


class ASGIAdapter:
    def __init__(self, application):
        if not callable(application):
            raise NativeStoreError("ASGI application must be callable")
        self.application = application
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(
            target=self.loop.run_forever, daemon=True, name="nativestore-asgi"
        )
        self.thread.start()
        self.closed = False
        self.started = False
        self.state: dict[str, Any] = {}
        self.incoming: Any = None
        self.outgoing: Any = None
        self.lifespan = None
        try:
            asyncio.run_coroutine_threadsafe(self._start(), self.loop).result(timeout=10)
        except Exception as exc:
            self.close()
            raise NativeStoreError("ASGI lifespan startup failed") from exc

    async def _start(self):
        self.incoming = asyncio.Queue()
        self.outgoing = asyncio.Queue()
        self.lifespan = asyncio.create_task(
            self.application(
                {
                    "type": "lifespan",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "state": self.state,
                },
                self.incoming.get,
                self.outgoing.put,
            )
        )
        await self.incoming.put({"type": "lifespan.startup"})
        notification = asyncio.create_task(self.outgoing.get())
        done, _ = await asyncio.wait(
            {notification, self.lifespan}, return_when=asyncio.FIRST_COMPLETED
        )
        if notification not in done:
            notification.cancel()
            await asyncio.gather(notification, return_exceptions=True)
            error = self.lifespan.exception()
            if error:
                raise error
            raise NativeStoreError("ASGI lifespan did not acknowledge startup")
        if notification.result().get("type") != "lifespan.startup.complete":
            raise NativeStoreError("ASGI application rejected startup")
        self.started = True

    async def _request(self, ctx, path, prefix):
        starts, chunks = [], []
        received, size = False, 0

        async def receive():
            nonlocal received
            if not received:
                received = True
                return {"type": "http.request", "body": ctx.raw_body, "more_body": False}
            await asyncio.Event().wait()

        async def send(message):
            nonlocal size
            if message["type"] == "http.response.start":
                starts.append(message)
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > ctx.app.config.max_result_bytes:
                    raise NativeStoreError("ASGI response exceeds configured limit")
                chunks.append(chunk)
            else:
                raise NativeStoreError("Unsupported ASGI response message")

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": ctx.method,
            "scheme": "http",
            "path": prefix + path,
            "raw_path": (prefix + path).encode(),
            "state": self.state.copy(),
            "root_path": prefix,
            "query_string": urlencode(ctx.query, doseq=True).encode(),
            "headers": [
                (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in ctx.headers.items()
            ],
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 0),
        }
        await self.application(scope, receive, send)
        if len(starts) != 1:
            raise NativeStoreError("ASGI must start exactly one response")
        start = starts[0]
        return response(
            start["status"],
            [(k.decode("latin-1"), v.decode("latin-1")) for k, v in start["headers"]],
            b"".join(chunks),
        )

    def handle(self, ctx, path, prefix):
        future = asyncio.run_coroutine_threadsafe(self._request(ctx, path, prefix), self.loop)
        try:
            return future.result(timeout=ctx.app.config.command_timeout)
        except TimeoutError:
            future.cancel()
            return Response("ASGI execution deadline exceeded", 504, "text/plain")

    async def _stop(self):
        try:
            if self.started:
                await self.incoming.put({"type": "lifespan.shutdown"})
                message = await asyncio.wait_for(self.outgoing.get(), timeout=5)
                if message.get("type") != "lifespan.shutdown.complete":
                    raise NativeStoreError("ASGI lifespan shutdown failed")
        finally:
            tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            asyncio.run_coroutine_threadsafe(self._stop(), self.loop).result(timeout=6)
        except Exception:
            logging.getLogger("nativestore").exception("ASGI shutdown failed")
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=2)
            if not self.thread.is_alive():
                self.loop.close()
