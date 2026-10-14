# Building NativeStore applications

Tauri remains the native engine. The default starter is JinjaX + modern Angular,
selected by the project owner. Angular is compiled ahead of time using Node.js 24;
end users run the bundled desktop app without Node, Python, or Rust installations.
Teloce is not integrated. Flask and FastAPI are optional adapters.

## Create and launch

```bash
python -m nativestore new my-desk
cd my-desk/frontend
npm ci --ignore-scripts
cd ..
python -m nativestore dev --devtools
```

`dev` builds Angular before starting the secure localhost Python server and Tauri
window. Frontend source changes rebuild Angular; template/JavaScript changes refresh
the window; CSS changes reload stylesheets; Python/config changes restart the backend.
The watcher skips node_modules and build caches. A failed Angular compilation reports
its compiler diagnostics. The Python server is local, not a public website deployment.

Choose another starter with `--ui minimal`, `--ui htmx`, `--ui alpine`,
`--ui htmx-alpine`, or the original `--ui expense`. These need no Node.js.
JinjaX-only applications use ordinary links and POST forms. HTMX and Alpine are optional.

## JinjaX and Angular

JinjaX renders the outer page and a `<ns-greeting>` mount element. Angular owns that
subtree and calls Python through the authenticated `NativeStore.invoke` bridge.
Angular templates live in TypeScript, preventing interpolation collisions with JinjaX.
Do not let HTMX or Alpine also mutate the Angular-owned subtree.

The starter uses Angular 22.2.2, standalone components, signals, strict TypeScript,
AOT compilation and a committed npm lockfile. It does not start an Angular HTTP server
or allow JavaScript eval. `<ns:Assets />` adds the compiled local main.js module when
available. `ctx.render` supplies a fresh style nonce; declare `{#def nativestore_nonce #}`
in a JinjaX page that renders `ngCspNonce={{ nativestore_nonce }}` on the Angular mount.
The response's CSP permits Angular styles with that nonce without unsafe-inline.

Run `nativestore build` on Windows x64; it compiles Angular before freezing the Python
backend and copying static resources into Tauri's NSIS package.

## Managed optional assets and UI

Place `<ns:Assets />` in the layout head. It reads the verified asset lock at render
time; adding/removing a library does not edit custom layout code. Install with:

```bash
nativestore add htmx
nativestore add alpine
nativestore add lucide
```

Scripts load in this order: bridge, HTMX, Lucide, framework UI behavior, optional
`static/js/ui.js`, Alpine CSP. Register custom `Alpine.data()` providers in that ui.js
file's `alpine:init` listener. NativeStore disables HTMX eval/script-tag processing,
shows HTTP 422 fragments, and refreshes Lucide after swaps. Existing layouts need the
explicit `<ns:Assets />` opt-in; legacy script tags should be removed to avoid duplication.

Built-in components: `ns:Field`, `ns:Alert`, `ns:Loading`, `ns:Dialog`, `ns:Dropdown`,
`ns:Tabs`, and `ns:Table`. Dialog/dropdown/tabs require Alpine. Dialog uses the native
HTML dialog element for focus trapping and Escape handling. Tabs currently provide
two labelled panels; the second panel contains its descriptive label. Compose your own
component for more complex tab content. There is no framework-specific visual theme.

## Forms

```python
from nativestore import Field, Form

@app.page('/submit', method='POST')
def submit(ctx):
    result = ctx.validate(Form(
        name=Field(min_length=1, max_length=80),
        quantity=Field(kind='integer', minimum=0),
    ))
    return ctx.render('Result.html', form=result,
                      status=200 if result.valid else 422)
```

`form.values` retains submitted text, `form.errors` maps fields to messages, and
`form.data` contains parsed values. Decimal values are finite Decimal objects;
integer fields reject fractional numbers. Unknown input fields are ignored. Scalar
fields reject repeated values; use `multiple=True` for repeated inputs. These helpers
validate application data; they do not provide account authentication or authorization.

## Generators

```bash
nativestore make page customers
nativestore make component CustomerCard
nativestore make blueprint inventory
```

Generators reject unsafe paths, existing files and discovered route collisions.
Blueprint generation is explicit: import and mount it in main.py. Run generated
blueprint tests with `python -m pytest blueprints/inventory/tests`; the default app
`nativestore test` command runs the top-level tests directory.

## Debugging

`nativestore dev --browser` opens browser debugging instead of Tauri.
`nativestore dev --devtools` opens the native webview inspector; browser mode uses the
browser's own inspector. Open `/__nativestore/dev` in an authenticated development
session for routes, commands, timings, recent template names and sanitized source frames.
Request/command values, query strings, headers and frame locals are not collected.

```bash
pip install 'nativestore[debug]'
nativestore dev --debug --debug-port 5678
# Explicitly pause startup until attachment:
nativestore dev --debug --wait-debugger
```

Attach VS Code's Python debugger to localhost:5678. Debugger dependencies are excluded
from production freezing; frozen apps ignore development diagnostics even if inherited
environment variables request them. `doctor` reports native runtime, Node/npm and debugger
availability. Existing runtime manifest/hash/offline checks remain in place; Windows
native wheels contain the prebuilt desktop executable. Other platforms still require
source compilation until their native wheels are built and validated.
