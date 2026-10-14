"""Authenticated development diagnostics. Never collect request/command values."""

import hashlib
import html
import linecache
import os
import re
import threading
import traceback
from collections import deque
from pathlib import Path


def enabled() -> bool:
    import sys

    return os.environ.get("NATIVESTORE_DEV") == "1" and not getattr(sys, "_MEIPASS", None)


class Diagnostics:
    def __init__(self):
        self.lock = threading.Lock()
        self.events: deque = deque(maxlen=200)
        self.error: dict = {}

    def record(self, kind, name, status, duration):
        with self.lock:
            self.events.append(
                {
                    "kind": kind,
                    "name": name,
                    "status": status,
                    "duration_ms": round(duration * 1000, 2),
                }
            )

    def exception(self, error):
        frames = traceback.extract_tb(error.__traceback__)
        # No exception values or frame locals: either can contain application secrets.
        with self.lock:
            self.error = {
                "type": type(error).__name__,
                "frames": [
                    {
                        "file": frame.filename,
                        "line": frame.lineno,
                        "function": frame.name,
                        "source": safe_source(frame.filename, frame.lineno),
                    }
                    for frame in frames[-10:]
                ],
            }

    def snapshot(self, app):
        with self.lock:
            return {
                "events": list(self.events),
                "error": dict(self.error),
                "routes": [{"path": p, "method": m} for p, m, _ in app.routes],
                "commands": sorted(app.commands),
                "components": list(getattr(app.templates, "rendered", [])),
            }


def revision(root: Path) -> dict:
    groups: dict[str, list] = {"templates": [], "styles": [], "scripts": []}
    for folder in ("templates", "static", "blueprints"):
        for path in (root / folder).rglob("*"):
            if not path.is_file() or "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            group = (
                "styles"
                if path.suffix == ".css"
                else "scripts"
                if path.suffix in (".js", ".mjs")
                else "templates"
                if path.suffix == ".html"
                else None
            )
            if group:
                stat = path.stat()
                groups[group].append((str(path.relative_to(root)), stat.st_mtime_ns, stat.st_size))
    return {
        key: hashlib.sha256(repr(sorted(values)).encode()).hexdigest()
        for key, values in groups.items()
    }


def safe_source(filename, number):
    source = linecache.getline(filename, number).strip()
    if re.search(r"password|secret|token|authorization|cookie", source, re.I):
        return "[redacted source]"
    return re.sub(r"(['\"])(?:\\.|(?!\1).)*?\1", "[literal]", source)[:200]


def error_page(error, diagnostics):
    diagnostics.exception(error)
    lines = "".join(
        f"<li>{html.escape(frame['file'])}:{frame['line']} — {html.escape(frame['function'])}<pre>{html.escape(frame.get('source', ''))}</pre></li>"
        for frame in diagnostics.error["frames"]
    )
    return f"""<!doctype html><html><head><title>NativeStore development error</title></head>
<body><h1>{html.escape(type(error).__name__)}</h1><p>Inspect the source locations below. Exception values and locals are omitted to protect application data.</p><ol>{lines}</ol><a href="/__nativestore/dev">Developer tools</a><script defer src="/__nativestore/dev.js"></script></body></html>"""


PANEL = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>NativeStore developer tools</title></head>
<body><h1>NativeStore developer tools</h1><p>Routes, commands, recent requests, rendered templates, and source locations. No request values are collected.</p><pre id="diagnostics"></pre><script defer src="/__nativestore/dev.js"></script></body></html>"""
