"""Explicit, namespaced reusable features using the normal App machinery."""

import re
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .app import Context, call
from .config import safe_path
from .errors import RouteError
from .router import discover, overlap, segments, within_prefix


@dataclass
class Blueprint:
    name: str
    root: str | Path
    defaults: dict = field(default_factory=dict)
    native_features: tuple[str, ...] = ()
    _commands: list = field(default_factory=list, init=False, repr=False)
    _startup: list = field(default_factory=list, init=False, repr=False)
    _shutdown: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.name) or self.name == "ns":
            raise RouteError("Blueprint name must be a lowercase Python identifier other than ns")
        root = Path(self.root).resolve(strict=True)
        self.root = root.parent if root.is_file() else root

    def command(self, name=None):
        def register(handler):
            self._commands.append((name or handler.__name__, handler))
            return handler

        return register

    def startup(self, handler):
        self._startup.append(handler)
        return handler

    def shutdown(self, handler):
        self._shutdown.append(handler)
        return handler


@dataclass
class BlueprintContext(Context):
    blueprint_name: str = ""
    config: Any = None
    prefix: str = ""

    def render(self, template: str, *, status: int = 200, **data: Any):
        if ":" not in template:
            template = self.blueprint_name + ":" + template
        data.setdefault("blueprint_prefix", self.prefix)
        return super().render(template, status=status, **data)

    @property
    def static_url(self) -> str:
        return "/static/blueprints/" + self.blueprint_name


def mount(app, blueprint: Blueprint, prefix: str, overrides: dict) -> None:
    from .loader import load_module

    prefix = prefix.rstrip("/")
    segments(prefix or "/")
    if "{" in prefix or blueprint.name in app.blueprints:
        raise RouteError("Blueprint needs a unique name and a static prefix")
    if any(feature not in app.config.native_features for feature in blueprint.native_features):
        raise RouteError("Application must explicitly enable blueprint native capabilities")
    settings = MappingProxyType({**blueprint.defaults, **overrides})
    routes = discover(Path(blueprint.root))
    for route in routes:
        path = prefix + (route.path if route.path != "/" else "") or "/"
        if any(overlap(path, existing) for existing, _, _ in app.routes):
            raise RouteError(f"Blueprint route collides: {path}")
        if any(within_prefix(path, p) for p, _ in app.adapters):
            raise RouteError("Blueprint route overlaps a framework adapter")
    old_routes, old_commands = list(app.routes), dict(app.commands)
    namespace = blueprint.name
    try:
        for index, route in enumerate(routes):
            file = safe_path(Path(blueprint.root), route.source)
            package_parts: list[str] = []
            parent = file.parent
            while (parent / "__init__.py").is_file():
                package_parts.insert(0, parent.name)
                parent = parent.parent
            if file.is_relative_to(app.root):
                package_parts = list(file.relative_to(app.root).parent.parts)
            module = load_module(file, f"_ns_{namespace}_{index}", ".".join(package_parts))
            handler = getattr(module, "page" if route.kind == "pages" else "handler", None)
            if not callable(handler):
                raise RouteError(f"Blueprint handler missing: {route.source}")

            def wrap(callback):
                @wraps(callback)
                def handle(ctx):
                    scoped = BlueprintContext(
                        ctx.app,
                        ctx.params,
                        ctx.query,
                        ctx.body,
                        ctx.method,
                        ctx.raw_body,
                        ctx.headers,
                        namespace,
                        settings,
                        prefix,
                    )
                    return call(callback, scoped)

                return handle

            path = prefix + (route.path if route.path != "/" else "") or "/"
            app.page(path, method=getattr(module, "method", "GET"))(wrap(handler))
        for name, handler in blueprint._commands:
            app.command(f"{namespace}.{name}")(handler)
        for callback in blueprint._startup:
            app.execution.run(
                lambda fn=callback: call(fn, app, settings), app.config.command_timeout
            )
        app.templates.add_namespace(namespace, Path(blueprint.root) / "templates")
        app.blueprints[namespace] = blueprint
        app._shutdown.extend(
            lambda fn=callback: call(fn, app, settings) for callback in blueprint._shutdown
        )
    except Exception:
        app.routes, app.commands = old_routes, old_commands
        for callback in reversed(blueprint._shutdown):
            call(callback, app, settings)
        raise
