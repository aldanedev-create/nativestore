import importlib.util
import sys
from contextlib import redirect_stdout
from pathlib import Path

from .app import App
from .config import Config, current_project, safe_path
from .errors import NativeStoreError
from .router import discover


def load_module(file: Path, name: str, package: str = ""):

    name = f"{package}.{name}" if package else name
    spec = importlib.util.spec_from_file_location(name, file)
    if spec is None or spec.loader is None:
        raise NativeStoreError(f"Cannot load {file}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[name] = module
    with redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    return module


def load_app(root: Path) -> App:
    config = Config.load(root)
    sys.path.insert(0, str(root))
    token = current_project.set(root.resolve())
    try:
        module = load_module(
            safe_path(root, config.entry),
            "_nativestore_entry",
            ".".join(Path(config.entry).parent.parts),
        )
    finally:
        current_project.reset(token)
    app = getattr(module, "app", None)
    if not isinstance(app, App):
        raise NativeStoreError("Entry must export a nativestore.App named app")
    app.root = root.resolve()
    app.config = config
    for i, route in enumerate(discover(root)):
        module = load_module(
            safe_path(root, route.source),
            f"_nativestore_route_{i}",
            ".".join(Path(route.source).parent.parts),
        )
        handler = getattr(module, "page" if route.kind == "pages" else "handler", None)
        if not callable(handler):
            raise NativeStoreError(f"{route.source} must export a callable handler")
        method = getattr(module, "method", "GET")
        app.page(route.path, method=method)(handler)
    return app
