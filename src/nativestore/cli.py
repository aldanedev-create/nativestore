import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from .assets import Assets
from .builder import build
from .config import Config
from .errors import NativeStoreError
from .router import manifest
from .runtime import Runtime


def new_project(name: str, parent: Path, ui: str = "angular") -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name):
        raise NativeStoreError("Project name must use lowercase letters, digits and hyphens")
    destination = parent / name
    if destination.exists():
        raise NativeStoreError(f"Destination already exists: {destination}")
    shutil.copytree(
        Path(__file__).with_name("scaffold"),
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for filename in ("nativestore.toml", "pyproject.toml", "main.py"):
        file = destination / filename
        file.write_text(
            file.read_text()
            .replace("expense-desk", name)
            .replace("dev.nativestore.expensedesk", f"dev.nativestore.{name}")
        )
    from .starters import configure

    try:
        configure(destination, ui)
    except Exception:
        shutil.rmtree(destination)
        raise
    return destination


def changes(root: Path, tools: Path | None = None) -> tuple:
    if tools is not None:
        result = subprocess.run(
            [str(tools), "snapshot"], cwd=root, capture_output=True, text=True, timeout=20
        )
        if result.returncode:
            raise NativeStoreError(f"Native file scan failed: {result.stderr.strip()}")
        return tuple((e["path"], e["modified_ns"], e["size"]) for e in json.loads(result.stdout))
    files = [root / "nativestore.toml", *root.glob("*.py")]
    for folder in ("app", "pages", "api", "templates", "static", "blueprints", "frontend"):
        for directory, directories, names in os.walk(root / folder):
            directories[:] = [
                name
                for name in directories
                if name not in ("node_modules", "__pycache__", ".angular", "target", ".git")
            ]
            files.extend(Path(directory) / name for name in names)
    return tuple(
        sorted(
            (str(p), p.stat().st_mtime_ns, p.stat().st_size)
            for p in files
            if p.is_file() and "__pycache__" not in p.parts and "node_modules" not in p.parts
        )
    )


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def development(
    root: Path,
    *,
    browser: bool,
    watch: bool,
    devtools: bool = False,
    debug: bool = False,
    debug_port: int = 5678,
    wait_debugger: bool = False,
) -> None:
    Config.load(root)
    if wait_debugger and not debug:
        raise NativeStoreError("--wait-debugger requires --debug")
    env = os.environ.copy()
    from .frontend import compile_frontend

    compile_frontend(root)
    env["NATIVESTORE_DEV"] = "1"
    if debug:
        if not 1 <= debug_port <= 65535:
            raise NativeStoreError("Debugger port must be between 1 and 65535")
        if importlib.util.find_spec("debugpy") is None:
            raise NativeStoreError("Install nativestore[debug] for debugger support")
        env["NATIVESTORE_DEBUG_PORT"] = str(debug_port)
        env["NATIVESTORE_DEBUG_WAIT"] = "1" if wait_debugger else "0"
    env["NATIVESTORE_DEVTOOLS"] = "1" if devtools else "0"
    env["NATIVESTORE_ROOT"] = str(root.resolve())
    env["NATIVESTORE_PYTHON"] = sys.executable
    native = None if browser else Runtime().resolve("desktop")
    if not browser and native is None and not shutil.which("cargo"):
        raise NativeStoreError(
            "Desktop development needs Rust. Install it, or use dev --browser for debugging"
        )
    command = [sys.executable, "-m", "nativestore.host"]
    if native is not None:
        command = [str(native), "--development"]
        if devtools:
            command.append("--devtools")
    elif not browser:
        desktop = root / ".nativestore/desktop-dev"
        shutil.copytree(
            Path(__file__).with_name("desktop"),
            desktop,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("target", "__pycache__"),
        )
        result = subprocess.run(["cargo", "build", "--manifest-path", str(desktop / "Cargo.toml")])
        if result.returncode:
            raise NativeStoreError(
                "Tauri compilation failed; check the native platform prerequisites"
            )
        executable = "nativestore-desktop.exe" if sys.platform == "win32" else "nativestore-desktop"
        command = [str(desktop / "target/debug" / executable)]
    while True:
        before = changes(root)

        def restart_files(snapshot):
            return tuple(
                item for item in snapshot if str(item[0]).endswith((".py", ".toml", ".lock"))
            )

        def frontend_files(snapshot):
            return tuple(item for item in snapshot if "frontend" in Path(item[0]).parts)

        frontend_before = frontend_files(before)
        process = subprocess.Popen(
            command, env=env, stdout=subprocess.PIPE if browser else None, text=True
        )
        try:
            if browser:
                assert process.stdout is not None
                import queue
                import threading

                ready: queue.Queue = queue.Queue()
                threading.Thread(
                    target=lambda stream=process.stdout, target=ready: target.put(
                        stream.readline()
                    ),
                    daemon=True,
                ).start()
                try:
                    line = ready.get(timeout=None if wait_debugger else 30)
                    handshake = json.loads(line)
                    if handshake.get("protocol") != 1:
                        raise ValueError("Unsupported backend protocol")
                except (ValueError, queue.Empty) as exc:
                    raise NativeStoreError(
                        "Python backend did not produce a valid startup handshake"
                    ) from exc
                print("Backend started; opening browser debugging session.", flush=True)
                webbrowser.open(handshake["url"])
            while process.poll() is None:
                if watch:
                    current = changes(root)
                    if restart_files(current) != restart_files(before):
                        print("Python/configuration changed; restarting backend…", flush=True)
                        break
                    if frontend_files(current) != frontend_before:
                        compile_frontend(root)
                        frontend_before = frontend_files(current)
                        print("Angular rebuilt; refreshing the interface.", flush=True)
                time.sleep(0.3)
            if process.poll() is not None:
                if process.returncode:
                    raise NativeStoreError(
                        f"Development process exited with code {process.returncode}"
                    )
                return
        finally:
            stop(process)
        if not watch:
            return


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nativestore")
    p.add_argument("--version", action="version", version="NativeStore 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)
    from .starters import UI_CHOICES

    new = sub.add_parser("new")
    new.add_argument("name")
    new.add_argument("--ui", choices=UI_CHOICES, default="angular")
    make = sub.add_parser("make")
    make.add_argument("kind", choices=("page", "component", "blueprint"))
    make.add_argument("name")
    for cmd in ("add", "remove"):
        s = sub.add_parser(cmd)
        s.add_argument("package")
        if cmd == "add":
            s.add_argument("--offline", action="store_true")
    sub.add_parser("list")
    sub.add_parser("update").add_argument("--offline", action="store_true")
    sub.add_parser("routes")
    sub.add_parser("doctor")
    runtime = sub.add_parser("runtime")
    runtime.add_argument("--manifest", type=Path, required=True)
    runtime.add_argument("--offline", action="store_true")
    dev = sub.add_parser("dev")
    dev.add_argument("--browser", action="store_true")
    dev.add_argument("--no-watch", action="store_true")
    dev.add_argument("--devtools", action="store_true")
    dev.add_argument("--debug", action="store_true")
    dev.add_argument("--debug-port", type=int, default=5678)
    dev.add_argument("--wait-debugger", action="store_true")
    sub.add_parser("test")
    sub.add_parser("build")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path.cwd()
    try:
        if args.command == "new":
            print(new_project(args.name, root, args.ui))
        elif args.command == "runtime":
            print(Runtime(args.manifest).install("desktop", offline=args.offline))
        elif args.command == "doctor":
            print(
                json.dumps(
                    {
                        "python": sys.version.split()[0],
                        "platform": sys.platform,
                        "cargo": shutil.which("cargo"),
                        "jinjax": importlib.util.find_spec("jinjax") is not None,
                        "windows_packaging": sys.platform == "win32",
                        "node": shutil.which("node"),
                        "npm": shutil.which("npm"),
                        "runtime": str(Runtime().resolve("desktop") or "source build required"),
                        "debugpy": importlib.util.find_spec("debugpy") is not None,
                    },
                    indent=2,
                )
            )
        else:
            Config.load(root)
            if args.command in ("add", "remove", "list", "update"):
                assets = Assets(root)
                if args.command == "add":
                    assets.add(args.package, offline=args.offline)
                elif args.command == "remove":
                    assets.remove(args.package)
                elif args.command == "update":
                    assets.update(offline=args.offline)
                else:
                    print(json.dumps(assets.locked(), indent=2))
            elif args.command == "make":
                from .generators import generate

                for path in generate(root, args.kind, args.name):
                    print(path.relative_to(root))
            elif args.command == "routes":
                native_tools = Runtime().resolve("tools")
                if native_tools:
                    return subprocess.run([str(native_tools), "routes"], cwd=root).returncode
                print(json.dumps(manifest(root), indent=2))
            elif args.command == "dev":
                development(
                    root,
                    browser=args.browser,
                    watch=not args.no_watch,
                    devtools=args.devtools,
                    debug=args.debug,
                    debug_port=args.debug_port,
                    wait_debugger=args.wait_debugger,
                )
            elif args.command == "test":
                return subprocess.run(
                    [sys.executable, "-m", "pytest", "tests"], cwd=root
                ).returncode
            elif args.command == "build":
                print(build(root))
        return 0
    except NativeStoreError as exc:
        print(f"NativeStore: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as exc:
        print(f"NativeStore: {exc}", file=sys.stderr)
        return 1
