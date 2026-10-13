# Compatibility and validation status

| Capability | Implementation | Validation |
| --- | --- | --- |
| Python API, JinjaX, SQLite starter | Complete current contracts | Portable automated tests |
| HTTP bridge, admission, deadlines, result limits | Implemented | Real HTTP/lifecycle/timeout tests |
| Rust CLI/config/router/assets/dev/builder/protocol/test support | Implemented | Rust tests, Clippy, Python parity/integration |
| Frontend registry, cache, hashes, project locks | Implemented | Cache/tamper/concurrent update tests |
| JinjaX component CSS/JS | Implemented | Real rendering and authenticated asset requests |
| Flask WSGI adapter | Implemented | Real form/cookie tests |
| FastAPI ASGI adapter and lifespan | Implemented | Real startup/request/validation/shutdown tests |
| Versioned native runtime resolution | Implemented | Compatibility/path/hash/offline tests |
| Tauri shell and four native feature groups | Source implemented | Native compile/launch pending |
| Windows NSIS packaging | Orchestration implemented | Windows build and clean VM pending |
| Native Windows wheels | CI and staging implemented | CI execution pending |
| macOS/Linux installer build | Unsupported | Fails explicitly |
| Menus/tray/shortcuts/updater | Planned | Not advertised as implemented |
| Code signing and PyPI publication | Not configured/performed | Owner configuration needed |

Normal release version: 0.1.0. Version naming does not replace platform validation.
Requires Python >=3.11 and JinjaX >=0.60,<1. Rust tooling pins 1.92.0.
No claim is made that unverified native features or installers are production-validated.
