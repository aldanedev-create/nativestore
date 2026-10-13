import json

import pytest

from nativestore import App, BridgeError, ConfigurationError, RouteError
from nativestore.config import Config, safe_path
from nativestore.loader import load_app
from nativestore.router import discover, manifest, match
from nativestore.testing import TestClient


@pytest.mark.parametrize(
    "path", ["../secret", "/etc/passwd", "a/../b", "a//b", "a\\b", "C:/x", "a\x00b"]
)
def test_unsafe_paths(tmp_path, path):
    with pytest.raises(ConfigurationError):
        safe_path(tmp_path, path)


@pytest.mark.parametrize("width", [True, "1000", 0, 9000])
def test_invalid_config(tmp_path, width):
    with pytest.raises(ConfigurationError):
        Config(width=width).validate(tmp_path)


def test_config_unknown_fields(project):
    file = project / "nativestore.toml"
    file.write_text(file.read_text() + 'unknown = "bad"\n')
    with pytest.raises(ConfigurationError):
        Config.load(project)


def test_routes_are_deterministic_without_imports(project):
    (project / "pages/user").mkdir()
    (project / "pages/user/[id].py").write_text('raise RuntimeError("must not import")')
    first = manifest(project)
    assert first == manifest(project)
    assert any(r["path"] == "/user/{id}" for r in first["routes"])
    assert match("/user/{id}", "/user/23") == {"id": "23"}
    assert match("/user/{id}", "/user/../x") is None


def test_route_conflict(project):
    (project / "pages/[name].py").write_text("")
    with pytest.raises(RouteError, match="Ambiguous"):
        discover(project)


def test_duplicate_page(project):
    app = App(root=project)
    app.page("/users/{id}")(lambda ctx: "user")
    with pytest.raises(RouteError):
        app.page("/users/new")(lambda ctx: "new")


@pytest.mark.parametrize("path", ["/static/foo", "/__nativestore/x", "/a/", "/a?b", "/a/{id}/{id}"])
def test_bad_registration(project, path):
    with pytest.raises(RouteError):
        App(root=project).page(path)


def test_real_template_and_persistence(project):
    app = load_app(project)
    client = TestClient(app)
    assert "A little clarity" in client.get("/").body
    assert "JinjaX" in client.get("/settings").body
    identity = client.invoke("add_expense", description="Bus fare", amount_cents=250)["result"][
        "id"
    ]
    second = load_app(project)
    rows = second.invoke({"protocol": 1, "command": "list_expenses", "args": {}})["result"]
    assert rows[0]["amount_cents"] == 250
    assert json.loads(second.dispatch("/api/expenses").body)[0]["description"] == "Bus fare"
    assert client.invoke("delete_expense", expense_id=identity)["result"]["deleted"]
    assert client.invoke("list_expenses")["result"] == []


def test_jinjax_escapes(project):
    app = load_app(project)
    assert "&lt;script&gt;" in app.templates.render("pages/Settings.html", title="<script>")


def test_async_and_strict_commands(project):
    app = App(root=project)

    @app.command()
    async def greet(name: str, age: int = 12):
        return {"name": name, "age": age}

    assert TestClient(app).invoke("greet", name="Ada")["result"]["age"] == 12
    for args in ({"name": 3}, {"name": "Ada", "age": True}, {"name": "Ada", "extra": 1}, {}):
        with pytest.raises(BridgeError):
            TestClient(app).invoke("greet", **args)


@pytest.mark.parametrize(
    "message",
    [
        None,
        {},
        {"protocol": True, "command": "x", "args": {}},
        {"protocol": 1, "command": "eval", "args": {}},
        {"protocol": 1, "command": "x", "args": {}, "eval": "1"},
    ],
)
def test_malformed_bridge(project, message):
    with pytest.raises(BridgeError):
        App(root=project).invoke(message)


def test_untyped_command_rejected(project):
    def bad(value):
        return value

    with pytest.raises(BridgeError):
        App(root=project).command()(bad)


def test_private_error(project):
    app = App(root=project)

    @app.command()
    def fail():
        raise RuntimeError("secret password")

    result = TestClient(app).invoke("fail")
    assert not result["ok"] and "secret" not in json.dumps(result)


def test_nonserializable_result(project):
    app = App(root=project)

    @app.command()
    def fail():
        return float("nan")

    assert not TestClient(app).invoke("fail")["ok"]


def test_template_path_traversal(project):
    with pytest.raises(ConfigurationError):
        load_app(project).templates.render("../secret.html")
