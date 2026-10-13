# Combined NativeStore implementation and release plan

This continues the existing project and combines the original master prompt with the
14-phase feature plan. Tauri remains responsible for windows, webviews, native capabilities
and bundling. Python retains business logic and JinjaX rendering. The release uses 0.1.0
without a prerelease suffix, while implementation and verification remain separate.

| Phase | Current result | Remaining acceptance work |
| --- | --- | --- |
| 1. Public API/configuration | Typed commands, responses, project precedence, platform data paths | Final supported-version CI matrix |
| 2. Tauri integration | Shell, handshake, cleanup, navigation restrictions, native smoke mode | Actual native launch and exit |
| 3. Bridge | Strict schemas, typed args, deadlines, single application execution, bounded sockets/results | Native JS invocation test; hard cancellation is not promised |
| 4. JinjaX | Catalog, escaping, composition, static/co-located assets | Packaged Windows rendering |
| 5. Routing | Static/dynamic paths, conflicts, manifests, relative imports | Native distribution parity tests in Windows CI |
| 6. Developer tools | Generation, watcher/restarts, doctor, test client, native artifact fallback | Desktop workflow in installed wheel |
| 7. Frontend libraries | Verified registry, cache, lock, add/remove/update, notices | More reviewed registry entries as needed |
| 8. Python packaging | Static import discovery, explicit hidden imports/resources, frozen smoke script | Representative native-extension packages on Windows |
| 9. Windows installer | PyInstaller sidecar, Tauri NSIS, WebView2 config, native smoke gate | Clean VM install/UI/exit/upgrade/uninstall |
| 10. Runtime delivery | Trusted manifests, hashes, cache, platform wheel staging, CI | Produce and retain real Windows native artifacts |
| 11. Native features | Dialog, clipboard, notifications, window source through Tauri | Validate operations; later menus/tray/shortcuts/updater |
| 12. Optional adapters | Real Flask and FastAPI HTTP/lifespan adapters | Packaged adapter example; unsupported streaming/WebSockets explicit |
| 13. Further platforms | Portable backend/data paths and platform-aware artifact resolver | Native macOS/Linux installer implementations and platform tests |
| 14. Documentation/release | Guides, support matrix, inspectors and guarded publishing workflow | Repository/PyPI trusted-publisher setup and successful gates |

Publication acceptance: install the actual wheel, generate an app, use real JinjaX in a
native window, invoke Python from the frontend, persist local records, install verified
libraries, run headless tests, build the Windows installer and validate it on clean Windows
without separately installed Python/Rust. Only then publish the exact validated artifacts.

Current release blockers are external/native validation, additional promised platform
implementation, future native feature groups, and owner release setup. There are no empty
placeholder crates representing completed work. Every remaining item must stay visible.
