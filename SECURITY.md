# Security policy

NativeStore is preparing a normal 0.1.0 release. Platform verification is separate from
version naming. Application Python, templates, dependencies, configuration and shipped
artifact/asset manifests are trusted inputs; arbitrary application code is not sandboxed.

Defaults include explicit command registration, supported argument types, strict JSON
schemas, response limits, per-port authenticated HttpOnly cookies, exact Host/Origin checks,
HTML escaping, restrictive CSP and validated project paths. There is no Python eval endpoint
or general frontend shell/filesystem permission. Tauri grants configured native operations
only to the exact application origin and main window through its capability system.

Application execution is serialized and caller waiting has a deadline. A synchronous
handler can continue after timeout; new calls are refused while it runs. Do not retry writes
blindly or interpret that error as cancellation. HTTP sockets have timeouts and bounded
admission. Shutdown has a supervisor watchdog. Hard cancellation of synchronous Python
requires a different isolation design and is not advertised here.

Asset changes use OS-backed locks and rollback failed lock writes. Runtime/asset bytes are
verified against trusted SHA-256 manifests before execution/use. Ordinary application APIs
and optional adapters still need their own business authorization. A registered Python
function can access resources granted to its operating-system process; Tauri's frontend
capabilities do not sandbox that Python function.

Dependency audits retain RUSTSEC-2024-0370 (proc-macro-error unmaintained) and
RUSTSEC-2024-0429 (GLib VariantStrIter unsoundness) warnings in the transitive Linux desktop
graph. No suppression or speculative upstream patch is configured. Native Windows/clean VM
checks and further native operation testing remain publication gates.

Report vulnerabilities privately to the repository maintainer. A concrete security contact
must be configured when the repository/release owner is assigned. Local administrators,
compromised trusted dependencies and malicious application source are outside the bridge's
session-token protection. Never embed secrets in distributed frontend or application source.
