import json

from test_http import request
from test_http import server as server


def test_devtools_authentication_and_redaction(server, monkeypatch):
    monkeypatch.setenv("NATIVESTORE_DEV", "1")
    assert request(server, "/__nativestore/dev", authenticated=False)[0] == 403
    assert request(server, "/__nativestore/dev")[0] == 200
    request(server, "/?password=do-not-record")
    status, raw, _ = request(server, "/__nativestore/dev/data")
    data = json.loads(raw)
    assert status == 200 and data["routes"]
    assert b"do-not-record" not in raw and b"password" not in raw

    @server.app.page("/failure")
    def failed(ctx):
        raise RuntimeError("secret-value-must-not-leak")

    status, body, _ = request(server, "/failure")
    assert status == 500 and b"RuntimeError" in body
    assert b"secret-value-must-not-leak" not in body
    monkeypatch.delenv("NATIVESTORE_DEV")
    assert request(server, "/__nativestore/dev")[0] == 404
    assert request(server, "/__nativestore/dev/data")[0] == 404
    assert b"RuntimeError" not in request(server, "/failure")[1]
