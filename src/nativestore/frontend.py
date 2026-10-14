"""Compile Angular before serving or freezing; end users run only built assets."""

import shutil
import subprocess
from pathlib import Path

from .errors import BuildError


def compile_frontend(root: Path) -> None:
    frontend = root / "frontend"
    if not (frontend / "angular.json").is_file():
        return
    npm = shutil.which("npm.cmd" if __import__("os").name == "nt" else "npm")
    if not npm:
        raise BuildError("Angular development requires Node.js 24 LTS and npm")
    if not (frontend / "node_modules/@angular/build").is_dir():
        raise BuildError("Install Angular dependencies first: cd frontend && npm ci")
    result = subprocess.run([npm, "run", "build"], cwd=frontend)
    if result.returncode:
        raise BuildError("Angular compilation failed; see compiler diagnostics above")
