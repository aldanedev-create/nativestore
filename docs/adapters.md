# Optional Flask and FastAPI integrations

Install `nativestore[flask]` or `nativestore[fastapi]` in the application environment.
The core does not depend on either framework.

```python
from flask import Flask, request
from fastapi import FastAPI
from nativestore import App

app = App()
legacy = Flask(__name__)

@legacy.post("/submit")
def submit():
    return {"name": request.form["name"]}

backend = FastAPI()

@backend.get("/items")
async def items():
    return {"items": []}

app.mount_wsgi(legacy, prefix="/legacy")
app.mount_asgi(backend, prefix="/backend")
```

Requests still pass through NativeStore's session authentication, origin restrictions,
CSP and byte limits. WSGI gets buffered request input, query values and HTTP headers;
responses preserve repeated Set-Cookie headers. ASGI uses a persistent event loop,
acknowledged startup/shutdown lifespan, buffered HTTP bodies and deadline cancellation.
Relative Python imports in file handlers are supported via their real package parent.

Compatibility is deliberately HTTP-only. ASGI applications must implement lifespan.
WebSockets, unbounded streaming, external OAuth redirects, request upgrade/hijacking and
framework development servers are not automatically compatible. CSP may require adapting
third-party documentation pages that load CDN assets. A mounted application does not gain
filesystem/shell access from frontend JavaScript; its own trusted Python code still needs
application authorization checks.

Use App as a context manager or call app.close() in headless tests to release workers and
adapter lifespan resources. One project per backend process is the supported deployment
model; embedded multi-project import namespace isolation is not advertised.
