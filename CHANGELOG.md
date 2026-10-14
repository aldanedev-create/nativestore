# Changelog

## Developer workflow update — 2026-10-14

Added the approved default JinjaX + Angular 22 starter, optional minimal/HTMX/Alpine
starters, managed assets and reusable UI components, Python form validation, safe
page/component/blueprint generators, explicit blueprint mounting, and development
reload/error/request/command diagnostics with optional debugpy and native inspector.
ASGI lifespan state and mounted paths are preserved. Local blueprint and compiled
Angular resources are included in frozen builds; debugpy is excluded. Added examples
and real browser/frozen-app CI. Tauri remains the native runtime.

## 0.1.0 — release preparation, 2026-10-13

Continues the existing NativeStore implementation. Added OS-backed project asset locks
and rollback, bounded HTTP workers, serialized application execution and caller deadlines,
result limits, strict duplicate-key JSON parsing, ordinary form bodies, response-header
policy, project configuration precedence, native platform data paths, relative handler
imports and co-located JinjaX component assets.

Added real Flask WSGI and FastAPI/ASGI lifespan adapters, versioned native artifact
resolution with integrity checks, platform-wheel staging, explicit hidden imports and
resources, and the remaining Rust workspace crates with CLI integrations.

Integrated opt-in Tauri dialogs, clipboard, notifications and window permissions in native
source, plus native smoke mode and guarded Windows wheel/installer release workflows.
Native platform verification and publication have not been completed in this environment.
