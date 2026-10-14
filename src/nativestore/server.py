import hmac
import json
import logging
import mimetypes
import re
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, unquote, urlsplit

from .app import App, Response
from .config import safe_path
from .errors import BridgeError, ConfigurationError

MAX_BODY = 1_048_576
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'; frame-src 'none'"
)


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, app: App):
        self.app = app
        self.slots = threading.BoundedSemaphore(app.config.request_workers)
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", 0), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.cookie_name = f"nativestore_{self.server_port}"
        self.bootstrap_url = f"{self.origin}/__nativestore/bootstrap?token={self.token}"
        self.timeout = 1

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            try:
                request.settimeout(1)
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def server_close(self):
        super().server_close()
        self.app.close()


class Handler(BaseHTTPRequestHandler):
    server: Server
    protocol_version = "HTTP/1.0"

    def log_message(self, format: str, *args) -> None:
        # Bootstrap URLs contain credentials; never log request URLs.
        pass

    def send(
        self, response: Response, *, cookie: str | None = None, location: str | None = None
    ) -> None:
        body = response.body.encode() if isinstance(response.body, str) else response.body
        if len(body) > self.server.app.config.max_result_bytes:
            body = b"Response exceeds configured limit"
            response = Response(body, 502, "text/plain")
        if not 200 <= response.status <= 599:
            raise ValueError("Invalid response status")
        protected = {
            "content-length",
            "content-type",
            "content-security-policy",
            "connection",
            "transfer-encoding",
            "referrer-policy",
            "x-content-type-options",
            "cache-control",
        }
        for name, value in response.headers:
            if name.lower() in protected:
                continue
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) or any(
                c in value for c in "\r\n\x00"
            ):
                raise ValueError("Invalid response header")

        if len(response.headers) > 100:
            raise ValueError("Too many response headers")
        if any(c in response.content_type for c in "\r\n\x00"):
            raise ValueError("Invalid response content type")
        self._response_status = response.status
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(body)))
        policy = CSP
        if response.csp_nonce:
            policy = policy.replace(
                "style-src 'self'", "style-src 'self' 'nonce-" + response.csp_nonce + "'"
            )
        self.send_header("Content-Security-Policy", policy)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        for name, value in response.headers:
            if name.lower() not in protected:
                self.send_header(name, value)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        if location:
            self.send_header("Location", location)
        self.end_headers()
        self.wfile.write(body)

    def error(self, status: int, code: str) -> None:
        self.send(
            Response(
                json.dumps({"protocol": 1, "ok": False, "error": {"code": code, "message": code}}),
                status,
                "application/json",
            )
        )

    def do_GET(self) -> None:
        self.tracked_request()

    def do_POST(self) -> None:
        self.tracked_request()

    def do_PUT(self) -> None:
        self.tracked_request()

    def do_DELETE(self) -> None:
        self.tracked_request()

    def tracked_request(self) -> None:
        from .devtools import enabled
        from .router import match

        started = time.monotonic()
        self._response_status = 500
        try:
            self.handle_request()
        finally:
            if enabled():
                path = urlsplit(self.path).path
                if not path.startswith("/__nativestore/dev"):
                    name = next(
                        (
                            pattern
                            for pattern, verb, _ in self.server.app.routes
                            if verb == self.command and match(pattern, path) is not None
                        ),
                        "/static/*" if path.startswith("/static/") else "/internal-or-unmatched",
                    )
                    self.server.app.diagnostics.record(
                        "request",
                        self.command + " " + name,
                        self._response_status,
                        time.monotonic() - started,
                    )

    def handle_request(self) -> None:
        self.connection.settimeout(5)
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            return self.error(403, "invalid_host")
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            return self.error(403, "invalid_origin")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            return self.error(403, "cross_site")
        parts = urlsplit(self.path)
        if parts.scheme or parts.netloc:
            return self.error(400, "invalid_path")
        if self.command == "GET" and parts.path == "/__nativestore/bootstrap":
            token = parse_qs(parts.query).get("token", [""])[0]
            if not hmac.compare_digest(token, self.server.token):
                return self.error(403, "unauthorized")
            return self.send(
                Response("", 303),
                cookie=f"{self.server.cookie_name}={token}; HttpOnly; SameSite=Strict; Path=/",
                location="/",
            )
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = (
                cookie[self.server.cookie_name].value if self.server.cookie_name in cookie else ""
            )
        except Exception:
            token = ""
        if not hmac.compare_digest(token, self.server.token):
            return self.error(403, "unauthorized")
        if self.command != "GET" and origin != self.server.origin:
            return self.error(403, "origin_required")
        body = None
        raw = b""
        if self.command != "GET":
            if self.headers.get("Transfer-Encoding"):
                return self.error(400, "unsupported_transfer_encoding")
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= MAX_BODY:
                    return self.error(413, "body_too_large")
                content_type = self.headers.get_content_type()
                if parts.path == "/__nativestore/invoke" and content_type != "application/json":
                    return self.error(415, "json_required")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return self.error(400, "incomplete_body")

                def strict_object(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result:
                            raise ValueError("Duplicate JSON key")
                        result[key] = value
                    return result

                if content_type == "application/json":
                    body = json.loads(
                        raw,
                        object_pairs_hook=strict_object,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
                    )
                elif content_type == "application/x-www-form-urlencoded":
                    body = parse_qs(raw.decode("utf-8"), max_num_fields=1000)
                else:
                    body = raw
            except (ValueError, OSError, RecursionError):
                return self.error(400, "invalid_json")
        try:
            path = unquote(parts.path, errors="strict")
            if path == "/__nativestore/invoke":
                if self.command != "POST":
                    return self.error(405, "post_required")
                result = self.server.app.invoke(body)
                return self.send(
                    Response(json.dumps(result, allow_nan=False), content_type="application/json")
                )
            from .devtools import PANEL, enabled, revision

            if enabled() and self.command == "GET":
                if path == "/__nativestore/dev":
                    return self.send(Response(PANEL))
                if path == "/__nativestore/dev/data":
                    return self.send(
                        Response(
                            json.dumps(self.server.app.diagnostics.snapshot(self.server.app)),
                            content_type="application/json",
                        )
                    )
                if path == "/__nativestore/dev/revision":
                    return self.send(
                        Response(
                            json.dumps(revision(self.server.app.root)),
                            content_type="application/json",
                        )
                    )
                if path == "/__nativestore/dev.js":
                    return self.send(
                        Response(
                            Path(__file__).with_name("dev.js").read_bytes(),
                            content_type="text/javascript",
                        )
                    )
            if path in ("/__nativestore/ui.js", "/__nativestore/ui.css") and self.command == "GET":
                name = path.rsplit("/", 1)[-1]
                return self.send(
                    Response(
                        Path(__file__).with_name(name).read_bytes(),
                        content_type="text/css" if name.endswith(".css") else "text/javascript",
                    )
                )
            if path.startswith("/static/blueprints/") and self.command == "GET":
                name, _, relative = path[len("/static/blueprints/") :].partition("/")
                blueprint = self.server.app.blueprints.get(name)
                if blueprint is None:
                    return self.error(404, "not_found")
                file = safe_path(Path(blueprint.root) / "static", relative)
                if not file.is_file():
                    return self.error(404, "not_found")
                if file.stat().st_size > 20 * MAX_BODY:
                    return self.error(413, "asset_too_large")
                return self.send(
                    Response(
                        file.read_bytes(),
                        content_type=mimetypes.guess_type(file.name)[0]
                        or "application/octet-stream",
                    )
                )
            if path == "/__nativestore/bridge.js" and self.command == "GET":
                return self.send(
                    Response(
                        Path(__file__).with_name("bridge.js").read_bytes(),
                        content_type="text/javascript",
                    )
                )
            if path.startswith("/__nativestore/"):
                return self.error(404, "not_found")
            if path.startswith("/static/components/") and self.command == "GET":
                file = self.server.app.templates.asset(path[len("/static/components/") :])
                if not file.is_file():
                    return self.error(404, "not_found")
                if file.stat().st_size > 20 * MAX_BODY:
                    return self.error(413, "asset_too_large")
                mime = "text/css" if file.suffix == ".css" else "text/javascript"
                return self.send(Response(file.read_bytes(), content_type=mime))
            if path.startswith("/static/") and self.command == "GET":
                file = safe_path(self.server.app.root / "static", path[len("/static/") :])
                if not file.is_file():
                    return self.error(404, "not_found")
                if file.stat().st_size > 20 * MAX_BODY:
                    return self.error(413, "asset_too_large")
                mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                return self.send(Response(file.read_bytes(), content_type=mime))
            response = self.server.app.dispatch(
                path,
                method=self.command,
                query=parse_qs(parts.query, max_num_fields=1000),
                body=body,
                raw_body=raw,
                headers=dict(self.headers.items()),
            )
            return self.send(response)
        except (BridgeError, ConfigurationError, UnicodeError):
            return self.error(400, "invalid_request")
        except Exception as error:
            from .devtools import enabled, error_page

            if enabled():
                return self.send(Response(error_page(error, self.server.app.diagnostics), 500))
            logging.getLogger("nativestore").exception("Request failed")
            return self.error(500, "request_failed")
