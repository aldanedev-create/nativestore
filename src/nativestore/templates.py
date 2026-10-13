from pathlib import Path
from threading import RLock
from typing import Any

from .config import safe_path
from .errors import ConfigurationError, NativeStoreError


class Templates:
    def __init__(self, root: Path) -> None:
        try:
            import jinjax
            from jinja2 import Environment, StrictUndefined
        except ImportError as exc:
            raise NativeStoreError(
                "Install the declared jinjax dependency to render templates"
            ) from exc
        self.root = root
        self.lock = RLock()
        self.catalog = jinjax.Catalog(
            file_ext=".html",
            auto_reload=True,
            jinja_env=Environment(autoescape=True, undefined=StrictUndefined),
        )
        self.catalog.add_folder(root)

    def asset(self, relative: str) -> Path:
        file = safe_path(self.root, relative)
        if file.suffix not in (".css", ".js", ".mjs"):
            raise ConfigurationError("Only component CSS and JavaScript assets can be served")
        return file

    def render(self, name: str, **data: Any) -> str:
        # Public names use paths; JinjaX component names use dots.
        if not name.endswith(".html"):
            raise NativeStoreError("Templates must use the .html extension")
        safe_path(self.root, name)
        component = name[:-5].replace("/", ".")
        with self.lock:
            return str(self.catalog.render(component, **data))
