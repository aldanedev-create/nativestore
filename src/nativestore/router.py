import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import safe_path
from .errors import RouteError


@dataclass(frozen=True)
class Route:
    path: str
    source: str
    kind: str


def segments(path: str) -> list[str]:
    if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
        raise RouteError("Routes must be absolute URL paths")
    if path != "/" and path.endswith("/"):
        raise RouteError("Routes must not end in a slash")
    result = [] if path == "/" else path[1:].split("/")
    names = []
    for part in result:
        if re.fullmatch(r"\{[a-zA-Z_][a-zA-Z_0-9]*\}", part):
            names.append(part[1:-1])
        elif not re.fullmatch(r"[a-zA-Z0-9_-]+", part):
            raise RouteError(f"Invalid route segment: {part!r}")
    if len(names) != len(set(names)):
        raise RouteError("Repeated route parameter")
    if result and result[0] in ("static", "__nativestore"):
        raise RouteError("Route uses a reserved namespace")
    return result


def overlap(a: str, b: str) -> bool:
    left, right = segments(a), segments(b)
    return len(left) == len(right) and all(
        x == y or x.startswith("{") or y.startswith("{") for x, y in zip(left, right, strict=False)
    )


def match(pattern: str, path: str) -> dict[str, str] | None:
    if not path.startswith("/") or "?" in path or "#" in path:
        return None
    expected = segments(pattern)
    actual = [] if path == "/" else path.lstrip("/").split("/")
    if len(expected) != len(actual):
        return None
    params = {}
    for a, b in zip(expected, actual, strict=False):
        if a.startswith("{"):
            if not b or b in (".", "..") or "\\" in b or "\x00" in b:
                return None
            params[a[1:-1]] = b
        elif a != b:
            return None
    return params


def discover(root: Path) -> list[Route]:
    routes: list[Route] = []
    for kind in ("pages", "api"):
        directory = root / kind
        if not directory.exists():
            continue
        if not directory.resolve().is_relative_to(root.resolve()):
            raise RouteError(f"{kind} escapes project")
        for file in sorted(directory.rglob("*.py")):
            relative = file.relative_to(root).as_posix()
            safe_path(root, relative)
            pieces = list(file.relative_to(directory).with_suffix("").parts)
            if any(p.startswith("_") for p in pieces):
                continue
            if pieces[-1] == "index":
                pieces.pop()
            parts = []
            for part in pieces:
                if re.fullmatch(r"\[[A-Za-z_][A-Za-z_0-9]*\]", part):
                    part = "{" + part[1:-1] + "}"
                parts.append(part)
            path = "/" + "/".join((["api"] if kind == "api" else []) + parts)
            segments(path)
            for previous in routes:
                if overlap(path, previous.path):
                    raise RouteError(f"Ambiguous routes: {previous.source} and {relative} ({path})")
            routes.append(Route(path, relative, kind))
    return sorted(routes, key=lambda r: (r.path, r.source))


def manifest(root: Path) -> dict:
    return {"protocol": 1, "routes": [asdict(r) for r in discover(root)]}


def within_prefix(pattern: str, prefix: str) -> bool:
    if not prefix:
        return True
    expected, base = segments(pattern), segments(prefix)
    return len(expected) >= len(base) and all(
        a == b or a.startswith("{") for a, b in zip(expected, base, strict=False)
    )
