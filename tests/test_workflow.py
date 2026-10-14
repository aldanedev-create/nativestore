from decimal import Decimal

import pytest

from nativestore import App, Blueprint, Field, Form, NativeStoreError, RouteError
from nativestore.cli import new_project
from nativestore.generators import generate
from nativestore.loader import load_app
from nativestore.testing import TestClient


@pytest.mark.parametrize("ui", ["angular", "minimal", "htmx", "alpine", "htmx-alpine"])
def test_starter_forms_and_resources(tmp_path, monkeypatch, ui):
    monkeypatch.setenv("NATIVESTORE_DATA_DIR", str(tmp_path / "data"))
    root = new_project("sample", tmp_path, ui=ui)
    with load_app(root) as app:
        client = TestClient(app)
        page = client.get("/")
        assert page.status == 200
        assert "/__nativestore/ui.js" in page.body
        result = client.post("/greet", form={"name": "<Ada>"})
        assert result.status == 200
        assert "&lt;Ada&gt;" in result.body
        result = client.post("/greet", form={"name": ""}, headers={"HX-Request": "true"})
        assert result.status == 422 and "This field is required" in result.body
        if ui == "angular":
            assert "ngCspNonce=" in page.body
            assert (root / "frontend/package-lock.json").is_file()
        if "alpine" in ui:
            assert page.body.index("/__nativestore/ui.js") < page.body.index(
                "/static/vendor/alpine.js"
            )


def test_form_validation():
    form = Form(
        name=Field(min_length=2),
        price=Field(kind="decimal", minimum=Decimal("0.01")),
        count=Field(kind="integer", minimum=1),
        category=Field(choices=("Work", "Home")),
        tags=Field(multiple=True, required=False),
    )
    result = form.validate(
        {
            "name": ["Ada"],
            "price": ["1.25"],
            "count": ["2"],
            "category": ["Work"],
            "tags": ["one", "two"],
        }
    )
    assert result.valid and result.data["price"] == Decimal("1.25")
    assert result.data["tags"] == ["one", "two"]
    bad = form.validate(
        {"name": ["a", "b"], "price": ["NaN"], "count": ["1.5"], "category": ["Other"]}
    )
    assert set(bad.errors) == {"name", "price", "count", "category"}
    assert not form.validate(None).valid


def test_generators_and_blueprint_lifecycle(project):
    generate(project, "page", "customers")
    generate(project, "component", "CustomerCard")
    generate(project, "blueprint", "inventory")
    for kind, name in (
        ("page", "customers"),
        ("component", "CustomerCard"),
        ("blueprint", "inventory"),
        ("page", "../escape"),
    ):
        with pytest.raises(NativeStoreError):
            generate(project, kind, name)
    bp = Blueprint("inventory", project / "blueprints/inventory")
    events = []
    bp.defaults = {"currency": "USD"}

    @bp.command()
    def add_item(name: str) -> str:
        return name

    @bp.startup
    def start(app, config):
        events.append(config["currency"])

    @bp.shutdown
    def stop(app, config):
        events.append("closed")

    with load_app(project) as app:
        app.mount_blueprint(bp, prefix="/inventory", config={"currency": "JMD"})
        assert app.dispatch("/inventory").status == 200
        assert app.dispatch("/customers").status == 200
        assert (
            app.invoke({"protocol": 1, "command": "inventory.add_item", "args": {"name": "Bolt"}})[
                "result"
            ]
            == "Bolt"
        )
        with pytest.raises(RouteError):
            app.mount_blueprint(bp, prefix="/other")
    assert events == ["JMD", "closed"]


def test_blueprint_conflicts_leave_app_unchanged(project):
    generate(project, "blueprint", "inventory")
    bp = Blueprint("inventory", project / "blueprints/inventory")
    with load_app(project) as app:
        before = list(app.routes)
        with pytest.raises(RouteError):
            app.mount_blueprint(bp, prefix="/")
        assert app.routes == before and not app.blueprints
        bp.native_features = ("dialog",)
        with pytest.raises(RouteError):
            app.mount_blueprint(bp, prefix="/inventory")


def test_asgi_lifespan_state_and_request_copy(project):
    async def application(scope, receive, send):
        if scope["type"] == "lifespan":
            scope["state"]["value"] = "ready"
            while True:
                message = await receive()
                await send({"type": message["type"] + ".complete"})
                if message["type"] == "lifespan.shutdown":
                    return
        else:
            assert scope["path"] == "/framework/items"
            assert scope["root_path"] == "/framework"
            assert scope["state"].pop("value") == "ready"
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

    with App(root=project) as app:
        app.mount_asgi(application, prefix="/framework")
        assert app.dispatch("/framework/items").status == 200
        assert app.dispatch("/framework/items").status == 200


def test_ui_components_render(project):
    with App(root=project) as app:
        for name, args in (
            ("Field", {"name": "name", "label": "Name"}),
            ("Alert", {"message": "Hi"}),
            ("Dropdown", {}),
            ("Dialog", {}),
            ("Tabs", {}),
            ("Loading", {}),
            ("Table", {"headings": ["Name"], "rows": [["Ada"]]}),
        ):
            assert app.templates.render("ns:" + name + ".html", **args)


def test_asset_wiring_is_idempotent_and_removable(project):
    from nativestore.assets import Assets

    assets = Assets(project)
    layout = project / "templates/Layout.html"
    original = layout.read_text()
    assets.add("htmx")
    assets.add("htmx")
    with App(root=project) as app:
        markup = app.templates.render("ns:Assets.html")
        assert markup.count("/static/vendor/htmx.js") == 1
        assets.remove("htmx")
        assert "/static/vendor/htmx.js" not in app.templates.render("ns:Assets.html")
    assert layout.read_text() == original


def test_blueprint_relative_imports_and_components(project):
    generate(project, "blueprint", "inventory")
    root = project / "blueprints/inventory"
    (root / "services.py").write_text('label = "Stock"\n')
    (root / "pages/index.py").write_text(
        "from ..services import label\n"
        'def page(ctx): return ctx.render("Index.html", title=label)\n'
    )
    (root / "templates/Index.css").write_text("h1 { color: green; }")
    with load_app(project) as app:
        app.mount_blueprint(Blueprint("inventory", root), prefix="/inventory")
        assert "Stock" in app.dispatch("/inventory").body
        assert app.templates.asset("inventory:Index.css").is_file()


def test_template_reload_in_development(project, monkeypatch):
    monkeypatch.setenv("NATIVESTORE_DEV", "1")
    template = project / "templates/Reload.html"
    template.write_text("<p>Before</p>")
    with App(root=project) as app:
        assert "Before" in app.templates.render("Reload.html")
        template.write_text("<p>After</p>")
        assert "After" in app.templates.render("Reload.html")


def test_field_quotes_values_and_optional_required(project):
    with App(root=project) as app:
        html = app.templates.render(
            "ns:Field.html",
            name="example",
            label="Example",
            value='Ada Lovelace" autofocus onclick="bad',
            required=False,
        )
        assert 'value="Ada Lovelace&#34; autofocus onclick=&#34;bad"' in html
        assert " required" not in html
