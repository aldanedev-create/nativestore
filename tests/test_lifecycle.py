import http.client
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit


def test_real_backend_starts_and_exits_with_parent(project, tmp_path):
    env = os.environ.copy()
    env.update(
        NATIVESTORE_ROOT=str(project),
        NATIVESTORE_DATA_DIR=str(tmp_path / "store"),
        NATIVESTORE_SUPERVISED="1",
        PYTHONPATH=str(Path(__file__).parents[1] / "src"),
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "nativestore.host"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        ready = json.loads(lines.get(timeout=20))
        assert ready["protocol"] == 1
        url = urlsplit(ready["url"])
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        conn.request("GET", url.path + "?" + url.query)
        response = conn.getresponse()
        cookie = response.getheader("Set-Cookie").split(";")[0]
        assert response.status == 303
        response.read()
        conn.close()
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        conn.request("GET", "/", headers={"Cookie": cookie})
        response = conn.getresponse()
        assert b"A little clarity" in response.read()
        conn.close()
        process.stdin.close()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
