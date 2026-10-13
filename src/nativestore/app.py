import asyncio
import inspect
import json
import logging
import os
import re
import sys
import threading
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from .config import Config, current_project
from .errors import BridgeError, RouteError
from .execution import Execution, ExecutionBusy, ExecutionTimeout
from .router import match, overlap, segments
from .templates import Templates

log = logging.getLogger("nativestore")


@dataclass
class Response:
    body: str | bytes
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    headers: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Context:
    app: "App"
    params: dict[str, str] = field(default_factory=dict)
    query: dict[str, list[str]] = field(default_factory=dict)
    body: Any = None
    method: str = "GET"
    raw_body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)

    def render(self, name: str, **data: Any) -> Response:
        return Response(self.app.templates.render(name, **data))

    def json(self, data: Any, status: int = 200) -> Response:
        return Response(json.dumps(data, allow_nan=False), status, "application/json")

    @property
    def data_dir(self) -> Path:
        return self.app.data_dir


def valid(value: Any, annotation: Any) -> bool:
    if annotation in (str, int, float, bool):
        return type(value) is annotation or (annotation is float and type(value) is int)
    if annotation is type(None):
        return value is None
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        return any(valid(value, a) for a in args)
    if origin is list and len(args) == 1:
        return type(value) is list and all(valid(v, args[0]) for v in value)
    if origin is dict and len(args) == 2:
        return type(value) is dict and all(
            valid(k, args[0]) and valid(v, args[1]) for k, v in value.items()
        )
    return False


def call(handler: Callable, *args: Any, **kwargs: Any) -> Any:
    result = handler(*args, **kwargs)
    if inspect.isawaitable(result):

        async def await_result():
            return await result

        return asyncio.run(await_result())
    return result


class App:
    def __init__(
        self,
        title: str = "NativeStore",
        frontend: str = "static",
        width: int = 1100,
        height: int = 750,
        root: str | Path | None = None,
        name: str = "nativestore-app",
    ) -> None:
        self.root = Path(
            root or current_project.get() or os.environ.get("NATIVESTORE_ROOT") or Path.cwd()
        ).resolve()
        if name == "nativestore-app" and (self.root / "nativestore.toml").is_file():
            name = Config.load(self.root).name
        self.config = Config(name=name, title=title, width=width, height=height)
        self.config.validate(self.root)
        if (self.root / "nativestore.toml").is_file():
            self.config = Config.load(self.root)
        if frontend != "static":
            raise ValueError("Only the static frontend directory is currently supported")
        self.routes: list[tuple[str, str, Callable]] = []
        self.commands: dict[str, tuple[Callable, dict]] = {}
        self._templates: Templates | None = None
        self.execution = Execution()
        self.adapters: list[tuple[str, Any]] = []
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library/Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
        self.data_dir = Path(
            os.environ.get("NATIVESTORE_DATA_DIR", str(base / "NativeStore" / self.config.name))
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def templates(self) -> Templates:
        if self._templates is None:
            self._templates = Templates(self.root / "templates")
        return self._templates

    def page(self, path: str, *, method: str = "GET") -> Callable:
        segments(path)
        if method not in ("GET", "POST", "PUT", "DELETE"):
            raise RouteError("Unsupported method")

        def register(handler: Callable) -> Callable:
            for route, verb, _ in self.routes:
                if verb == method and overlap(route, path):
                    raise RouteError(f"Ambiguous {method} routes: {route} and {path}")
            self.routes.append((path, method, handler))
            return handler

        return register

    def command(self, name: str | None = None) -> Callable:
        def register(handler: Callable) -> Callable:
            command_name = name or handler.__name__
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", command_name):
                raise BridgeError("Invalid command name")
            if command_name in self.commands:
                raise BridgeError(f"Duplicate command: {command_name}")
            hints = get_type_hints(handler)
            for p in inspect.signature(handler).parameters.values():
                if p.kind not in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
                    raise BridgeError(
                        "Commands cannot accept positional-only or variadic parameters"
                    )
                if p.name not in hints or not supported(hints[p.name]):
                    raise BridgeError(
                        f"{command_name}.{p.name} needs a supported JSON type annotation"
                    )
                if p.default is not inspect.Parameter.empty and not valid(p.default, hints[p.name]):
                    raise BridgeError(f"Invalid default for {p.name}")
            self.commands[command_name] = (handler, hints)
            return handler

        return register

    def invoke(self, message: Any) -> dict:
        if threading.current_thread() is self.execution.worker:
            return self._invoke(message)
        try:
            return self.execution.run(lambda: self._invoke(message), self.config.command_timeout)
        except (ExecutionBusy, ExecutionTimeout) as exc:
            code = "execution_busy" if isinstance(exc, ExecutionBusy) else "execution_timeout"
            return {"protocol": 1, "ok": False, "error": {"code": code, "message": code}}

    def _invoke(self, message: Any) -> dict:
        if type(message) is not dict or set(message) != {"protocol", "command", "args"}:
            raise BridgeError("Expected protocol, command and args")
        if type(message["protocol"]) is not int or message["protocol"] != 1:
            raise BridgeError("Unsupported protocol")
        if type(message["command"]) is not str or type(message["args"]) is not dict:
            raise BridgeError("Invalid command message")
        if message["command"] not in self.commands:
            raise BridgeError("Command is not registered")
        handler, hints = self.commands[message["command"]]
        try:
            bound = inspect.signature(handler).bind(**message["args"])
            bound.apply_defaults()
        except TypeError as exc:
            raise BridgeError("Invalid command arguments") from exc
        if not all(valid(v, hints[k]) for k, v in bound.arguments.items()):
            raise BridgeError("Command arguments do not match their annotations")
        try:
            result = call(handler, **bound.arguments)
            encoded = json.dumps(result, allow_nan=False).encode("utf-8")
            if len(encoded) > self.config.max_result_bytes:
                return {
                    "protocol": 1,
                    "ok": False,
                    "error": {
                        "code": "result_too_large",
                        "message": "Command result exceeds configured limit",
                    },
                }

            return {"protocol": 1, "ok": True, "result": result}
        except Exception:
            log.exception("Command failed: %s", message["command"])
            return {
                "protocol": 1,
                "ok": False,
                "error": {"code": "command_failed", "message": "Command failed"},
            }

    def dispatch(
        self,
        path: str,
        *,
        method: str = "GET",
        query: dict | None = None,
        body: Any = None,
        raw_body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> Response:
        if threading.current_thread() is self.execution.worker:
            return self._dispatch(path, method, query, body, raw_body, headers)
        try:
            return self.execution.run(
                lambda: self._dispatch(path, method, query, body, raw_body, headers),
                self.config.command_timeout,
            )
        except ExecutionBusy:
            return Response("Application is busy", 503, "text/plain")
        except ExecutionTimeout:
            return Response("Application execution deadline exceeded", 504, "text/plain")

    def _dispatch(self, path, method, query, body, raw_body, headers) -> Response:
        for pattern, verb, handler in self.routes:
            params = match(pattern, path)
            if params is not None and verb == method:
                result = call(
                    handler,
                    Context(self, params, query or {}, body, method, raw_body, headers or {}),
                )
                if isinstance(result, Response):
                    return result
                if isinstance(result, str):
                    return Response(result)
                return Response(
                    json.dumps(result, allow_nan=False), content_type="application/json"
                )
        for prefix, adapter in self.adapters:
            if path == prefix or path.startswith(prefix + "/") or prefix == "":
                context = Context(self, {}, query or {}, body, method, raw_body, headers or {})
                return adapter.handle(context, path[len(prefix) :] or "/", prefix)
        return Response("Not found", 404, "text/plain")

    def mount_wsgi(self, application: Any, *, prefix: str = "/legacy") -> None:
        from .adapters import WSGIAdapter

        self._mount(prefix, WSGIAdapter(application))

    def mount_asgi(self, application: Any, *, prefix: str = "/api") -> None:
        from .adapters import ASGIAdapter

        self._mount(prefix, ASGIAdapter(application))

    def _mount(self, prefix: str, adapter: Any) -> None:
        prefix = prefix.rstrip("/")
        try:
            segments(prefix or "/")
            if "{" in prefix or any(p == prefix for p, _ in self.adapters):
                raise RouteError("Adapter prefixes must be unique static paths")
        except Exception:
            adapter.close()
            raise
        self.adapters.append((prefix, adapter))

    def __enter__(self) -> "App":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def close(self) -> None:
        self.execution.close()
        for _, adapter in self.adapters:
            adapter.close()

    def run(self) -> None:
        from .cli import development

        try:
            development(self.root, browser=False, watch=False)
        finally:
            self.close()


def supported(annotation: Any) -> bool:
    if annotation in (str, int, float, bool, type(None)):
        return True
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        return bool(args) and all(supported(a) for a in args)
    if origin is list:
        return len(args) == 1 and supported(args[0])
    if origin is dict:
        return len(args) == 2 and args[0] is str and supported(args[1])
    return False
