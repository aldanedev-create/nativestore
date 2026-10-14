# NativeStore developer workflow implementation

Tauri remains the window, capability and bundling engine. JinjaX-only applications
remain supported. HTMX, Alpine CSP and Lucide are optional local assets. Teloce is
excluded. Flask/FastAPI adapters remain optional.

1. Default to JinjaX + modern Angular (approved by the user); also generate minimal,
   HTMX, Alpine and combined starters, preserving the explicit expense example.
   Angular builds use Node.js 24 and AOT; packaged applications require no Node.js.
2. Render installed libraries through a managed JinjaX asset component, preserving layouts.
3. Supply accessible composable UI components and CSP-compatible Alpine behavior.
4. Validate forms in Python and preserve values/errors for HTML and HTMX.
5. Add development-only errors, reload feedback, request/command panels and debugger support.
6. Generate pages/components/blueprints without replacing files or accepting collisions.
7. Explicitly mount blueprints with route/command/template/asset namespaces, lifecycle hooks
   and application-approved native capabilities; include local resources in frozen builds.
8. Verify prebuilt runtime workflows and improve runtime diagnostics.
9. Harden adapters, including ASGI lifespan state propagation and prefix conflicts.
10. Add runnable examples, starter/blueprint/frontend CI and Windows native/package checks.

Acceptance: headless functionality, actual HTML/JS interactions under the existing CSP,
resource integrity, deterministic generation, normal forms and HTMX errors, blueprint
collisions and cleanup, optional framework lifecycle, and production exclusion of dev tools.
Windows installer installation and native operation verification require Windows CI.
Implementation progress and platform evidence are recorded in VALIDATION.md; no unexecuted
acceptance check is represented as passed.

## Implemented in this change

Starters and managed assets; UI components and form helpers; generators; development-only
error/panel/reload support and optional debugpy; explicit blueprint mounting; local blueprint
packaging; ASGI lifespan state; Angular compilation and locked dependencies; runnable Angular,
HTMX, inventory and settings examples; browser and frozen frontend CI.

## Acceptance still requiring platform execution

New native inspector behavior and the revised installer must pass Windows CI. Clean-machine
installation, native feature operations, upgrades and uninstallation remain release gates.
Installed third-party blueprint resources require explicit build configuration. Further native
platform wheels are not produced by this implementation.
