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
        self.catalog.add_folder(Path(__file__).with_name("components"), prefix="ns")
        from .integrations import asset_tags

        self.catalog.jinja_env.globals["nativestore_assets"] = lambda: (
            asset_tags(root.parent) + self.catalog.render_assets()
        )
        self.namespaces: dict[str, Path] = {}
        self.rendered: list[str] = []

    def add_namespace(self, name: str, root: Path) -> None:
        if name in self.namespaces or name == "ns":
            raise ConfigurationError("Template namespace is already registered")
        self.catalog.add_folder(root, prefix=name)
        self.namespaces[name] = root

    def clear(self) -> None:
        with self.lock:
            if self.catalog.jinja_env.cache is not None:
                self.catalog.jinja_env.cache.clear()
            self.catalog._cache.clear()

    def asset(self, relative: str) -> Path:
        prefix, separator, name = relative.partition(":")
        if separator:
            if prefix not in self.namespaces:
                raise ConfigurationError("Unknown component asset namespace")
            file = safe_path(self.namespaces[prefix], name)
        else:
            file = safe_path(self.root, relative)
        if file.suffix not in (".css", ".js", ".mjs"):
            raise ConfigurationError("Only component CSS and JavaScript assets can be served")
        return file

    def render(self, template: str, **data: Any) -> str:
        # Public templates use paths; JinjaX component templates use dots.
        if not template.endswith(".html"):
            raise NativeStoreError("Templates must use the .html extension")
        prefix, separator, relative = template.partition(":")
        if separator:
            if prefix not in self.namespaces and prefix != "ns":
                raise ConfigurationError("Unknown template namespace")
            directory = self.namespaces.get(prefix, Path(__file__).with_name("components"))
            safe_path(directory, relative)
            component = prefix + ":" + relative[:-5].replace("/", ".")
        else:
            safe_path(self.root, template)
            component = template[:-5].replace("/", ".")
        with self.lock:
            from .devtools import enabled

            if enabled():
                self.clear()
                self.rendered = (self.rendered + [template])[-50:]
            return str(self.catalog.render(component, **data))
