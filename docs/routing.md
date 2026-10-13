# Routing conventions

| Source | Route | Export |
| --- | --- | --- |
| pages/index.py | / | page(ctx) |
| pages/settings.py | /settings | page(ctx) |
| pages/users/[id].py | /users/{id} | page(ctx) |
| pages/users/index.py | /users | page(ctx) |
| api/expenses.py | /api/expenses | handler(ctx) |

An optional module-level `method` string selects GET, POST, PUT or DELETE.
Default is GET. `ctx.params` supplies strings; no automatic integer conversion.
`ctx.query` maps query keys to lists; `ctx.body` contains parsed JSON for mutations.

Filename scanning imports no application code. Paths are sorted deterministically.
`__init__.py` and paths beginning with underscore are ignored. Segments contain ASCII
letters, digits, hyphens or underscores; [name] becomes a parameter. Repeated parameter
names, unsafe paths, reserved static/ and __nativestore/ routes are rejected.
A static route overlapping a dynamic route is rejected rather than resolved by order.
Catch-all paths, optional segments, nested layouts and route groups are not implemented.

Explicit `@app.page("/path", method="GET")` registrations are supported. File routes
are added during `load_app`; duplicate explicit/file routes fail. File manifests are
conservative and reject overlaps irrespective of module method, because scanning does
not execute code. Python and Rust manifest parity is tested for supported routes.
