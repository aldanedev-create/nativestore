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
    app = load_app(root.resolve())
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
