"""Managed asset rendering leaves application templates intact."""

from pathlib import Path

from markupsafe import Markup

from .assets import Assets


def asset_tags(root: Path) -> Markup:
    installed = {entry["name"]: entry for entry in Assets(root).locked()}
    paths = ["/__nativestore/bridge.js"]
    paths.extend(
        "/static/vendor/" + installed[name]["path"]
        for name in ("htmx", "lucide")
        if name in installed
    )
    paths.append("/__nativestore/ui.js")
    if (root / "static/js/ui.js").is_file():
        paths.append("/static/js/ui.js")
    if "alpine" in installed:
        paths.append("/static/vendor/" + installed["alpine"]["path"])
    from .devtools import enabled

    if enabled():
        paths.append("/__nativestore/dev.js")
    tags = ['<link rel="stylesheet" href="/__nativestore/ui.css">']
    tags.extend(f'<script defer src="{path}"></script>' for path in paths)
    if (root / "static/angular/browser/main.js").is_file():
        tags.append('<script type="module" src="/static/angular/browser/main.js"></script>')
    return Markup("\n".join(tags))
