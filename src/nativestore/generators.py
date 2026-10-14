"""Conservative generators: validate first and never replace existing files."""

import re
from pathlib import Path

from .config import safe_path
from .errors import NativeStoreError
from .router import discover, overlap, segments


def generate(root: Path, kind: str, name: str) -> list[Path]:
    if kind == "page":
        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_]*)*", name):
            raise NativeStoreError("Page name must be lowercase path segments")
        route = "/" + name
        segments(route)
        if any(overlap(route, item.path) for item in discover(root)):
            raise NativeStoreError("Generated page would collide with an existing route")
        component = "".join(p.title().replace("_", "") for p in name.split("/"))
        files = {
            f"pages/{name}.py": f'def page(ctx):\n    return ctx.render("pages/{component}.html")\n',
            f"templates/pages/{component}.html": f'<Layout title="{component}"><h1>{component}</h1></Layout>\n',
            f"tests/test_page_{name.replace('/', '_')}.py": f'''from pathlib import Path
from nativestore.loader import load_app


def test_generated_page():
    with load_app(Path(__file__).resolve().parents[1]) as app:
        response = app.dispatch("{route}")
        assert response.status == 200
        assert "{component}" in response.body
''',
        }
    elif kind == "component":
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
            raise NativeStoreError("Component name must be PascalCase")
        files = {
            f"templates/{name}.html": "{#def title #}\n<section><h2>{{ title }}</h2>{{ content }}</section>\n",
            f"templates/{name}.css": "section { margin-block: 1rem; }\n",
            f"tests/test_component_{name.lower()}.py": f'''from pathlib import Path
from nativestore.templates import Templates


def test_component_escapes_title():
    templates = Templates(Path(__file__).resolve().parents[1] / "templates")
    html = templates.render("{name}.html", title="<script>alert(1)</script>")
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
''',
        }
    elif kind == "blueprint":
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name == "ns":
            raise NativeStoreError(
                "Blueprint name must be a lowercase Python identifier other than ns"
            )
        prefix = f"blueprints/{name}"
        files = {
            prefix
            + "/__init__.py": f'from nativestore import Blueprint\n\nblueprint = Blueprint(name="{name}", root=__file__)\n',
            prefix + "/pages/__init__.py": "",
            prefix
            + "/pages/index.py": 'def page(ctx):\n    return ctx.render("Index.html", title="Blueprint")\n',
            prefix
            + "/templates/Index.html": f"{{#def title #}}\n<Layout title={{{{ title }}}}><h1>{name}</h1></Layout>\n",
            prefix + "/services.py": '"""Keep reusable feature business logic here."""\n',
            prefix
            + "/forms.py": "from nativestore import Field, Form\n\nname_form = Form(name=Field(max_length=80))\n",
            prefix + "/static/style.css": "h1 { font-weight: 700; }\n",
            prefix + "/tests/test_feature.py": f"""from pathlib import Path
from nativestore import App
from blueprints.{name} import blueprint


def test_blueprint():
    with App(root=Path(__file__).resolve().parents[3]) as app:
        app.mount_blueprint(blueprint, prefix="/{name}")
        assert app.dispatch("/{name}").status == 200
""",
        }
    else:
        raise NativeStoreError("Unknown generator")
    targets = [safe_path(root, path) for path in files]
    if any(path.exists() for path in targets):
        raise NativeStoreError("Generation would replace an existing file")
    written = []
    try:
        for path, content in zip(targets, files.values(), strict=True):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
            written.append(path)
    except Exception:
        for path in written:
            path.unlink()
        raise
    return targets
