# NativeStore

**Python applications. Desktop windows. One workflow.**

NativeStore is a Python-first desktop application framework with JinjaX HTML
components, a Rust/Tauri shell, file-based pages, explicitly registered Python
commands, verified browser assets, and a Windows packaging pipeline.

**Status: 0.1.0, release preparation.** The portable Python workflow is implemented
and tested. Native desktop source and Windows packaging orchestration are included;
Windows installer creation and clean-machine launch must be verified on Windows
before a production release. Do not treat this source archive as a finished installer.

## Install from this source

```bash
python -m pip install -e ".[dev,packaging]"
python -m nativestore new expense-desk
cd expense-desk
python -m nativestore dev --browser
```

The distribution has not been published to PyPI by this task. `python -m nativestore`
works even when your Python scripts directory is not on PATH. If it is on PATH,
use the shorter `nativestore` commands.

Desktop development additionally requires Rust and your platform's Tauri native
prerequisites. Windows needs Visual Studio 2022 C++ build tools, the Windows SDK,
and WebView2. The first desktop development build compiles the Tauri shell:

```bash
nativestore dev
nativestore test
nativestore add htmx
nativestore add alpine
nativestore add lucide
nativestore routes
```

The starter is a real local expense app: JinjaX component layout, Python commands,
SQLite persistence, add/delete forms, JSON API and a second page. Its default UI
uses local vanilla JavaScript; installing an optional library does not silently
rewrite templates. Add its script tag when using that library.

## Write Python

```python
from nativestore import App
app = App(title="My Desk", name="my-desk")

@app.command()
def greet(name: str) -> dict[str, str]:
    return {"message": f"Hello, {name}!"}
```

From a local JavaScript file:

```javascript
const result = await NativeStore.invoke("greet", {name: "Ada"});
```

For file-based pages, export `page(ctx)` from `pages/index.py`:

```python
def page(ctx):
    return ctx.render("pages/Index.html", title="My Desk")
```

The entry file is `main.py`, intentionally avoiding the `app.py` versus `app/`
Python import-name collision in the proposed tree.

## Build on Windows x64

```powershell
python -m pip install -e ".[packaging]"
cargo install tauri-cli --version "^2" --locked
cd expense-desk
python -m nativestore build
```

This freezes the Python backend and interpreter with PyInstaller, packages selected
application resources, and asks Tauri to create an NSIS installer with an offline
WebView2 installer. It returns an actual installer path or an error. Builds need
network access for uncached Rust dependencies, Tauri tooling and WebView2.
Applications importing other Python packages must install them in the build environment.

Production build support is currently Windows x64 only. Verified native runtime resolution and optional Flask/ASGI adapters are implemented.
GitHub Actions has compiled the Windows runtime, passed a real native window/backend smoke test, and built a verified Windows wheel. Installer and clean-machine validation remain release gates.
See [Actions](https://github.com/aldanedev-create/nativestore/actions) for current results.
Signing, application auto-update and further installer platforms remain future work. End users should eventually need neither Python nor Rust; that
promise still requires clean Windows installation testing.

## Verify the framework

```bash
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src/nativestore --exclude scaffold
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace --locked
```

The Cargo workspace has eight crates: CLI, configuration, router, assets, development,
builder, protocol, and test support. Verified native wheels use Rust for scanning,
asset verification and build planning. Portable wheels retain Python fallbacks.
The Tauri shell remains the native window and capability engine.

Optional HTTP integrations use `app.mount_wsgi(flask_app, prefix="/legacy")` and
`app.mount_asgi(fastapi_app, prefix="/backend")`. Install the corresponding extras.
Native dialogs, clipboard, notifications and window controls are opt-in Tauri APIs;
see [native features](docs/native.md). The basic Windows window/backend smoke test has passed; native feature groups still require acceptance testing.

Documentation: [quickstart](docs/quickstart.md), [CLI](docs/cli.md),
[configuration](docs/configuration.md), [routing](docs/routing.md),
[templates](docs/templates.md), [bridge](docs/bridge.md), [assets](docs/assets.md),
[packaging](docs/packaging.md), [architecture](docs/architecture.md),
[compatibility](docs/compatibility.md), [validation](VALIDATION.md).
