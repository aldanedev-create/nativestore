# Validation — 0.1.0, 2026-10-13

Authoring environment: Linux x86_64, Python 3.12.14, Rust 1.92.0, JinjaX 0.66.
This continues the previously created NativeStore project using the combined requirements.

| Check | Result |
| --- | --- |
| Framework pytest | 84 passed, including real HTTP, typed bridge, deadlines/busy recovery, forms, assets, native integrity, dependency inventory and adapter lifecycle |
| Generated app pytest | 2 passed |
| Rust workspace | 16 tests passed across eight concrete crates; Clippy passed |
| Native CLI integration | Config, route parity, asset verification, snapshots and build plans exercised |
| Ruff and Mypy | Passed; 19 framework modules type checked |
| JavaScript syntax | bridge.js passed node --check |
| Wheel/sdist | Built and Twine checked; cached files excluded by explicit package rules |
| Distribution inspection | Required sources/icons/templates/notices present, no target trees or Python caches |
| Clean environment installation | 0.1.0 wheel installed in a fresh venv; generated app's tests passed |
| Frozen backend | Real PyInstaller executable launched with Python absent from PATH; starter rendering, Python command and shutdown passed |
| Python dependency audit | No known vulnerabilities in inspected task-installed packages; unpublished framework excluded from advisory lookup |
| Rust workspace audit | No reported vulnerabilities |
| Desktop dependency audit | Two transitive warnings: RUSTSEC-2024-0370 and RUSTSEC-2024-0429; not suppressed |
| Tauri compilation | Attempted; blocked by absent pkg-config/GLib/GTK/WebKit development dependencies |
| Native window/features smoke | Source and CI provided; not executed in this environment |
| Windows native wheel | Staging and workflow provided; real Windows artifact not produced here |
| Windows installer/clean VM | Not verified; publication gate |
| PyPI publishing | Not performed; trusted publisher ownership/setup and Windows gates outstanding |

Normal version naming is 0.1.0. Native implementation source is not represented as native
validation. The locally built wheel is portable; development without a precompiled runtime
still needs Rust/native prerequisites or explicit browser debugging. Consult RELEASE_PLAN.md
and docs/compatibility.md for remaining platform and feature acceptance work.

## GitHub Actions — 2026-10-13

Source is published at https://github.com/aldanedev-create/nativestore.
The Python 3.11–3.13 Windows/Linux matrix, Rust checks and dependency audit
passed after fixing the Windows lock-module typing and isolating the audit runtime.
Jinja2 now requires at least 3.1.6. The desktop audit retains the two warnings above.

[Native Windows run](https://github.com/aldanedev-create/nativestore/actions/runs/38461813533)
compiled Tauri, loaded an actual native window, rendered the starter, exercised its Python
command, and shut down successfully. The Windows wheel passed distribution and Twine
checks and was uploaded as an artifact. An earlier launch failed without diagnostics;
the diagnostic rerun passed. Native feature permissions and clean Windows installation
are not covered by this basic smoke test. Installer checks are still running.

## Developer workflow update — 2026-10-14

- Approved default: JinjaX + modern Angular 22.2.2, Node.js 24 for builds.
- 99 Python tests passed; 17 Rust tests passed; Ruff/Mypy and Clippy passed.
- Angular AOT compilation passed with the committed npm lock.
- Real Chromium interactions passed for Angular Python bridge calls and HTMX/Alpine
  validation/icon updates under the existing CSP.
- Real PyInstaller executables passed without Python on PATH for minimal, Angular,
  and local inventory blueprint apps. Wheel/sdist resource inspection and Twine passed.
- Development panel authentication, production exclusion, redaction, template reload,
  asset add/remove idempotence, blueprint collisions/lifecycle/imports, form escaping
  and ASGI state isolation are covered by tests.
- Native inspector and revised Windows installer require a new Windows Actions run.
  Prior Windows native wheel/installer checks succeeded; that does not validate this
  revised native source. Clean VM install/upgrade/uninstall and native capability
  operations remain release gates. No PyPI publication was performed.
