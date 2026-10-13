"""Headless application behavior; HTTP authentication has separate transport tests."""

import json as json_module
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from .app import App, Response
from .errors import NativeStoreError


class TestClient:
    __test__ = False

    def __init__(self, app: App):
        self.app = app

    def request(self, method: str, path: str, *, json=None, form=None, headers=None) -> Response:
        if json is not None and form is not None:
            raise NativeStoreError("Supply either JSON or a form")
        parts = urlsplit(path)
        if parts.scheme or parts.netloc or not parts.path.startswith("/"):
            raise NativeStoreError("TestClient requires a relative application URL")
        raw, body = b"", None
        values = dict(headers or {})
        if json is not None:
            raw = json_module.dumps(json, allow_nan=False).encode()
            body = json
            values["Content-Type"] = "application/json"
        elif form is not None:
            raw = urlencode(form, doseq=True).encode()
            body = parse_qs(raw.decode(), max_num_fields=1000)
            values["Content-Type"] = "application/x-www-form-urlencoded"
        return self.app.dispatch(
            unquote(parts.path),
            method=method,
            query=parse_qs(parts.query, max_num_fields=1000),
            body=body,
            raw_body=raw,
            headers=values,
        )

    def get(self, path: str) -> Response:
        return self.request("GET", path)

    def post(self, path: str, **kwargs) -> Response:
        return self.request("POST", path, **kwargs)

    def invoke(self, command: str, **args) -> dict:
        return self.app.invoke({"protocol": 1, "command": command, "args": args})

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.app.close()
