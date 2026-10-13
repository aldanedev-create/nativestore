# Windows packaging

Run builds on Windows x64 with Python 3.11+, the project's installed dependencies,
NativeStore's packaging extra, Rust/MSVC, Visual Studio C++ build tools, Windows SDK,
and Tauri CLI v2. `nativestore build` stages an explicit resource set, uses PyInstaller
onefile for Python, names the sidecar with its target triple, and invokes Tauri's NSIS
bundler. WebView2 uses the offlineInstaller bundle mode. No Node.js is required.

Stage includes entry, config, lock, app/, pages/, api/, templates/, static/. It excludes
.env files, Python caches and common SQLite/database files. Avoid putting any secrets
in this source tree: exclusion rules are not a comprehensive secret detector.
Package imports are collected from Python source via AST without executing code;
application Python packages are hidden imports. Truly dynamic dependencies may need
additional packaging support and must be exercised by clean-machine smoke tests.

The native host starts the adjacent bundled Python executable. Frozen Python reads
its staged resources from sys._MEIPASS/project. Application data goes into a writable
user directory, not the install directory. Runtime exit kills/reaps the backend; a
stdin-lifetime watchdog also shuts it down if its parent disappears.

The pipeline is implemented but the Windows installer has not been produced in the
Linux authoring environment. Before calling it supported, build on Windows, install
into a clean Windows VM without Python/Rust, launch, exercise commands/persistence,
close, check for leftover backend processes, uninstall, and verify data policy.
Unsigned installers may be flagged by Windows; code signing is not yet configured.
Prebuilt reusable Tauri runtime artifacts and verified runtime downloads remain planned.

Tauri configuration source: https://v2.tauri.app/reference/config/
Sidecar naming source: https://v2.tauri.app/develop/sidecar/

To reproduce the portable freeze smoke test from the source root, run
`python scripts/smoke_frozen_backend.py examples/expense-desk`. This exercises the
frozen backend only, not an installer or native webview.

Staging also records the installed Python dependency closure declared by the application
(and core framework dependencies) and copies available upstream license notices into
THIRD_PARTY_LICENSES/python-dependencies.json and package-specific notice folders.
Review packages lacking notices and the native Cargo dependency licenses before release.
