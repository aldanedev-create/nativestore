# ADR 1: Authenticated loopback transport

Accepted. Serve JinjaX pages and command requests on one ephemeral
127.0.0.1 origin. Use bootstrap token -> HttpOnly SameSite cookie, exact Host/Origin
checks and restrictive CSP. Native Tauri navigation is restricted to that origin.
This supports ordinary HTML pages and headless HTTP testing without inventing an
IPC template loader. A serial server minimizes shared application races but limits
concurrency; a future ASGI transport must preserve authentication and origin checks.
