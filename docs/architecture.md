# Architecture

NativeStore builds on Tauri for native windows, webviews, capabilities and installer
bundling. Python owns application services, pages, templates and registered commands.
The framework coordinates those systems without introducing a replacement desktop engine.

| Layer | Responsibility |
| --- | --- |
| Python public API | App, Context, Response, decorators, lifecycle and testing |
| Python transport | Authenticated local HTTP, bounded admission and serialized application execution |
| JinjaX adapter | Real Catalog rendering, escaping, component composition and co-located assets |
| Rust config/router | Validated project configuration and import-free route discovery |
| Rust assets/dev/builder | Asset hash checks, deterministic watch snapshots and Windows build plans |
| Rust protocol/test support | Protocol contracts and safe filesystem fixtures |
| Rust CLI | Native operations plus Python command delegation |
| Tauri runtime | Window, sidecar supervision, exact-origin capabilities and native plugins |

Verified native binaries are resolved through a version/protocol/hash manifest.
A native wheel avoids compilation during normal installation/development startup.
Without those artifacts, portable development can explicitly use a browser or compile
the shell with Rust and platform prerequisites. Installer builds still require build tools.

Application calls are serialized on one daemon worker. HTTP sockets use bounded workers,
so one slow connection does not monopolize the listener. A deadline bounds caller waiting;
it does not forcibly terminate a synchronous Python handler. While such a handler runs,
subsequent application calls fail as busy, preventing overlapping state mutations.

Optional ASGI adapters own one persistent event loop and lifespan. Native operations use
Tauri's official plugins and capabilities. Only configured features receive permissions,
restricted to the actual session origin and main window. Default native features are empty.
