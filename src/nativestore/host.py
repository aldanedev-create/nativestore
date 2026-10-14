"""Private backend entry; stdout is reserved for the startup protocol."""

import json
import os
import signal
import sys
import threading
from contextlib import redirect_stdout
from pathlib import Path

from .loader import load_app
from .server import Server


def main() -> None:
    bundled = getattr(sys, "_MEIPASS", None)
    root = Path(bundled) / "project" if bundled else Path(os.environ.get("NATIVESTORE_ROOT", "."))
    os.environ["NATIVESTORE_ROOT"] = str(root.resolve())
    from .devtools import enabled

    if enabled() and os.environ.get("NATIVESTORE_DEBUG_PORT"):
        import debugpy

        port = int(os.environ["NATIVESTORE_DEBUG_PORT"])
        debugpy.listen(("127.0.0.1", port))
        print(f"Python debugger listening on localhost:{port}", file=sys.stderr, flush=True)
        if os.environ.get("NATIVESTORE_DEBUG_WAIT") == "1":
            print("Waiting for debugger attachment…", file=sys.stderr, flush=True)
            debugpy.wait_for_client()
    try:
        app = load_app(root.resolve())
    except Exception as error:
        if not enabled():
            raise
        from .app import App, Response
        from .devtools import error_page

        app = App(root=root.resolve())
        failure = error_page(error, app.diagnostics)
        app.page("/")(lambda ctx: Response(failure, 500))
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if os.environ.get("NATIVESTORE_SUPERVISED") == "1":

        def parent_watchdog():
            sys.stdin.buffer.read()
            stop()
            # Bound shutdown even if an application handler is blocked.
            threading.Timer(5, lambda: os._exit(0)).start()

        threading.Thread(target=parent_watchdog, daemon=True).start()
    with Server(app) as server:
        print(
            json.dumps(
                {
                    "protocol": 1,
                    "url": server.bootstrap_url,
                    "title": app.config.title,
                    "width": app.config.width,
                    "height": app.config.height,
                    "native_features": list(app.config.native_features),
                }
            ),
            flush=True,
        )
        try:
            with redirect_stdout(sys.stderr):
                while running:
                    server.handle_request()
        finally:
            app.close()


if __name__ == "__main__":
    main()
