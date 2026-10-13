"""Launch the real Tauri runtime and require its built-in window/backend smoke test."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("executable", type=Path)
parser.add_argument("--project", type=Path)
args = parser.parse_args()
executable = args.executable.resolve(strict=True)
command = [str(executable), "--smoke-test"]
env = os.environ.copy()
if args.project:
    env.update(NATIVESTORE_ROOT=str(args.project.resolve()), NATIVESTORE_PYTHON=sys.executable)
    command.append("--development")
else:
    env.pop("NATIVESTORE_PYTHON", None)
    env.pop("NATIVESTORE_ROOT", None)
with tempfile.TemporaryDirectory(prefix="nativestore-desktop-") as temporary:
    env["NATIVESTORE_DATA_DIR"] = temporary
    diagnostics = Path(temporary) / "native-startup.log"
    env["NATIVESTORE_DIAGNOSTICS"] = str(diagnostics)
    process = subprocess.Popen(command, env=env)
    try:
        result = process.wait(timeout=120)
        if result:
            raise SystemExit(f"Native desktop smoke test failed with status {result}")
    finally:
        if diagnostics.exists():
            print(diagnostics.read_text(encoding="utf-8"), file=sys.stderr, flush=True)
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
print("Real native window loaded the starter and its Python command; runtime exited successfully.")
