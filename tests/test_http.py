import http.client
import json
import threading
from urllib.parse import urlsplit

import pytest

from nativestore.loader import load_app
from nativestore.server import Server


@pytest.fixture
def server(project):
    with Server(load_app(project)) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server
        server.shutdown()
        thread.join(timeout=5)


def request(
    server, path="/", method="GET", body=None, authenticated=True, origin=True, headers=None
):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    values = {"Content-Type": "application/json"}
    if authenticated:
        values["Cookie"] = f"{server.cookie_name}={server.token}"
    if origin:
        values["Origin"] = server.origin
    values.update(headers or {})
    connection.request(method, path, body, values)
    response = connection.getresponse()
    status, result, response_headers = response.status, response.read(), dict(response.getheaders())
    connection.close()
    return status, result, response_headers


def test_bootstrap_cookie_and_security_headers(server):
    parts = urlsplit(server.bootstrap_url)
    status, _, headers = request(server, parts.path + "?" + parts.query, authenticated=False)
    assert status == 303
    assert "HttpOnly" in headers["Set-Cookie"] and "SameSite=Strict" in headers["Set-Cookie"]
    assert headers["Location"] == "/"
    assert "unsafe-eval" not in headers["Content-Security-Policy"]
    assert request(server, authenticated=False)[0] == 403


def test_http_command_and_template(server):
    assert b"A little clarity" in request(server)[1]
    body = json.dumps(
        {
            "protocol": 1,
            "command": "add_expense",
            "args": {"description": "Lunch", "amount_cents": 1200},
        }
    )
    status, result, _ = request(server, "/__nativestore/invoke", "POST", body)
    assert status == 200 and json.loads(result)["ok"]
    assert json.loads(request(server, "/api/expenses")[1])[0]["amount_cents"] == 1200


@pytest.mark.parametrize(
    "headers",
    [{"Host": "evil.test"}, {"Origin": "https://evil.test"}, {"Sec-Fetch-Site": "cross-site"}],
)
def test_host_and_origin_rejected(server, headers):
    assert request(server, headers=headers)[0] == 403


def test_post_requires_origin(server):
    assert request(server, "/__nativestore/invoke", "POST", "{}", origin=False)[0] == 403


@pytest.mark.parametrize(
    "path",
    ["/static/../main.py", "/static/%2e%2e/main.py", "/static/%2Fetc/passwd", "/static/C:/secret"],
)
def test_traversal_rejected(server, path):
    assert request(server, path)[0] == 400


def test_bridge_method_and_body_limits(server):
    assert request(server, "/__nativestore/invoke")[0] == 405
    assert request(server, "/__nativestore/invoke", "POST", "garbage")[0] == 400
    assert (
        request(
            server, "/__nativestore/invoke", "POST", "{}", headers={"Content-Length": "1048577"}
        )[0]
        == 413
    )
    assert (
        request(
            server, "/__nativestore/invoke", "POST", "{}", headers={"Content-Type": "text/plain"}
        )[0]
        == 415
    )


def test_static_and_bridge_resource(server):
    assert request(server, "/static/js/app.js")[0] == 200
    assert b"Object.freeze" in request(server, "/__nativestore/bridge.js")[1]


def test_duplicate_json_keys_rejected(server):
    raw = '{"protocol":1,"command":"list_expenses","args":{},"command":"eval"}'
    assert request(server, "/__nativestore/invoke", "POST", raw)[0] == 400


def test_regular_form_route_and_response_header_policy(server):
    from nativestore import Response

    server.app.page("/submit", method="POST")(
        lambda ctx: Response(
            ctx.body["name"][0],
            headers=[("X-Application", "yes"), ("Content-Security-Policy", "default-src *")],
        )
    )
    status, body, headers = request(
        server,
        "/submit",
        "POST",
        "name=Ada",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 200 and body == b"Ada"
    assert headers["X-Application"] == "yes"
    assert "default-src *" not in headers["Content-Security-Policy"]


def test_jinjax_colocated_assets_and_hidden_template_source(server):
    root = server.app.root / "templates"
    (root / "Asset.html").write_text(
        "{#def title #}{{ catalog.render_assets() }}<p>{{ title }}</p>"
    )
    (root / "Asset.css").write_text("p { color: green; }")
    html = server.app.templates.render("Asset.html", title="Safe")
    assert "/static/components/Asset.css" in html
    assert request(server, "/static/components/Asset.css")[1] == b"p { color: green; }"
    assert request(server, "/static/components/Asset.html")[0] != 200
