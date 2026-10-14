import ast
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .assets import Assets
from .config import Config, safe_path
from .errors import BuildError


def stage(root: Path, destination: Path) -> Path:
    config = Config.load(root)
    if destination.exists():
        raise BuildError("Build staging destination already exists")
    if not safe_path(root, config.entry).is_file():
        raise BuildError("Application entry file is missing")
    for resource in config.extra_resources:
        if not safe_path(root, resource).exists():
            raise BuildError(f"Configured resource is missing: {resource}")
    Assets(root).verify()
    from .runtime import Runtime

    tools = Runtime().resolve("tools")
    native_plan = None
    if tools is not None:
        result = subprocess.run(
            [str(tools), "build-plan"], cwd=root, capture_output=True, text=True, timeout=30
        )
        if result.returncode:
            raise BuildError(f"Native build planning failed: {result.stderr.strip()}")
        native_plan = json.loads(result.stdout)
    project = destination / "project"
    project.mkdir(parents=True)
    if native_plan is not None:
        (destination / "build-plan.json").write_text(json.dumps(native_plan, indent=2))
    # An explicit list avoids bundling .env, virtual environments or local databases.
    for name in (
        config.entry,
        "nativestore.toml",
        "nativestore.lock",
        "app",
        "pages",
        "api",
        "templates",
        "static",
        "blueprints",
        *config.extra_resources,
    ):
        source = safe_path(root, name)
        if not source.exists():
            continue
        if source.is_dir():
            for file in source.rglob("*"):
                if file.is_symlink():
                    raise BuildError(f"Symlinks are not permitted in packaged resources: {file}")
            shutil.copytree(
                source,
                project / name,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".env*", "*.sqlite*", "*.db", "tests"
                ),
            )
        else:
            if source.is_symlink():
                raise BuildError("Cannot package symlink")
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    notices = Path(__file__).with_name("licenses")
    if notices.is_dir():
        shutil.copytree(notices, project / "THIRD_PARTY_LICENSES")
    from .inventory import collect

    collect(root, project / "THIRD_PARTY_LICENSES")
    desktop = destination / "desktop"
    shutil.copytree(
        Path(__file__).with_name("desktop"),
        desktop,
        ignore=shutil.ignore_patterns("target", "__pycache__"),
    )
    config_path = desktop / "tauri.conf.json"
    data = json.loads(config_path.read_text())
    data.update(productName=config.title, version=config.version, identifier=config.identifier)
    data["bundle"] = {
        "active": True,
        "targets": ["nsis"],
        "externalBin": ["binaries/nativestore-backend"],
        "icon": ["icons/icon.png", "icons/icon.ico"],
        "windows": {"webviewInstallMode": {"type": "offlineInstaller"}},
    }
    config_path.write_text(json.dumps(data, indent=2))
    return desktop


def hidden_imports(root: Path) -> list[str]:
    imports = set(Config.load(root).hidden_imports)
    for directory in (root / "app", root / "pages", root / "api", root / "blueprints"):
        if not directory.exists():
            continue
        for file in directory.rglob("*.py"):
            relative = file.relative_to(root).with_suffix("")
            if all(part.isidentifier() for part in relative.parts):
                imports.add(".".join(relative.parts))
    files = [root / Config.load(root).entry]
    for folder in ("app", "pages", "api", "blueprints"):
        files.extend((root / folder).rglob("*.py"))
    for file in files:
        tree = ast.parse(file.read_text(), filename=str(file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module)
    return sorted(imports)


def build(root: Path) -> Path:
    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise BuildError(
            "Installer builds currently require Windows x64; cross-compilation is unsupported"
        )
    if not shutil.which("cargo"):
        raise BuildError("Install Rust with the MSVC toolchain and Visual Studio C++ build tools")
    check = subprocess.run(["cargo", "tauri", "--version"], capture_output=True, text=True)
    if check.returncode:
        raise BuildError("Install the Tauri CLI: cargo install tauri-cli --version ^2 --locked")
    if importlib.util.find_spec("PyInstaller") is None:
        raise BuildError("Install nativestore[packaging] in the application environment")
    from .frontend import compile_frontend

    compile_frontend(root)
    # Use a new build directory each time; never delete a user directory.
    import tempfile

    parent = root / ".nativestore/builds"
    parent.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="release-", dir=parent))
    destination.rmdir()
    desktop = stage(root, destination)
    entry = destination / "backend_entry.py"
    entry.write_text("from nativestore.host import main\nif __name__ == '__main__': main()\n")
    binary_dir = desktop / "binaries"
    binary_dir.mkdir()
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--onefile",
                "--exclude-module",
                "debugpy",
                "--name",
                "nativestore-backend-x86_64-pc-windows-msvc",
                "--distpath",
                str(binary_dir),
                "--workpath",
                str(destination / "pyinstaller-work"),
                "--specpath",
                str(destination),
                "--paths",
                str(root),
                "--collect-all",
                "jinjax",
                "--add-data",
                f"{Path(__file__).with_name('bridge.js')};nativestore",
                "--add-data",
                f"{Path(__file__).with_name('registry.json')};nativestore",
                "--add-data",
                f"{destination / 'project'};project",
                *freeze_data_arguments(destination / "project"),
                *[arg for module in hidden_imports(root) for arg in ("--hidden-import", module)],
                str(entry),
            ],
            check=True,
        )
        subprocess.run(["cargo", "tauri", "build", "--bundles", "nsis"], cwd=desktop, check=True)
    except subprocess.CalledProcessError as exc:
        raise BuildError(
            f"Build failed with exit code {exc.returncode}; staging retained at {destination}"
        ) from exc
    bundles = list((desktop / "target/release/bundle/nsis").glob("*.exe"))
    if not bundles:
        raise BuildError("Tauri returned success but produced no NSIS installer")
    return bundles[0]


def freeze_data_arguments(project: Path) -> list[str]:
    package = Path(__file__).parent
    separator = ";" if sys.platform == "win32" else ":"
    resources = [(package / name, "nativestore") for name in ("ui.js", "ui.css")]
    resources.extend(
        [
            (package / "components", "nativestore/components"),
            (package / "licenses", "nativestore/licenses"),
        ]
    )
    return [
        arg
        for source, destination in resources
        for arg in ("--add-data", f"{source}{separator}{destination}")
    ]
