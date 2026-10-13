# JavaScript-to-Python bridge

Register typed functions with `@app.command()` and call them from external JavaScript:

```javascript
const result = await NativeStore.invoke("greet", {name: "Ada"});
```

Protocol 1 uses `{protocol: 1, command: "greet", args: {name: "Ada"}}`. Unknown fields,
unknown commands, duplicate JSON keys, nonfinite numbers, missing/extra parameters and
wrong argument types fail. Supported annotations: str, int, float, bool, None, list[T],
dict[str,T] and unions. Boolean values are not accepted as integers.

Successful replies contain protocol, ok and result. Application exceptions expose only
a generic frontend message; tracebacks remain in trusted backend stderr. Async functions
are awaited. Responses and command results have a configured byte limit.

The service binds 127.0.0.1 on an ephemeral port. A private startup handshake provides a
random bootstrap token to Tauri. Bootstrap sets a per-port HttpOnly SameSite=Strict cookie
and redirects to /. Exact Host and Origin checks protect the bridge. Native navigation
stays within this origin. There is no arbitrary Python evaluation or shell endpoint.

`command_timeout` defaults to 30 seconds. A timed-out call returns execution_timeout;
further calls return execution_busy while that function is still running. A synchronous
function may still finish and change data after its caller times out: do not treat the
reply as cancellation, and do not automatically retry non-idempotent writes. Shutdown is
bounded by the supervisor. Hard per-command process isolation remains a separate future option.

Application calls, including Python pages, are serialized. Static assets and HTTP admission
remain responsive. `request_workers` limits simultaneous sockets. Mutations accept JSON,
form bodies or raw bytes on ordinary routes/adapters; the invoke endpoint requires JSON.
Streaming HTTP, WebSockets through adapters and general command cancellation are not supported.
