"""Freeze and exercise a generated backend; does not test the native Tauri window."""

import argparse
import http.client
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

import nativestore
from nativestore.builder import hidden_imports, stage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    with tempfile.TemporaryDirectory(prefix="nativestore-frozen-") as temporary:
        out = Path(temporary) / "stage"
        stage(root, out)
        entry = out / "backend.py"
        entry.write_text('from nativestore.host import main\nif __name__ == "__main__": main()\n')
        package = Path(nativestore.__file__).parent
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "backend",
            "--distpath",
            str(out / "dist"),
            "--workpath",
            str(out / "work"),
            "--specpath",
            str(out),
            "--paths",
            str(root),
            "--collect-all",
            "jinjax",
        ]
        separator = ";" if os.name == "nt" else ":"
        for source, destination in [
            (package / "bridge.js", "nativestore"),
            (package / "registry.json", "nativestore"),
            (out / "project", "project"),
        ]:
            command.extend(["--add-data", f"{source}{separator}{destination}"])
        for module in hidden_imports(root):
            command.extend(["--hidden-import", module])
        command.append(str(entry))
        subprocess.run(command, check=True)
        executable = out / "dist" / ("backend.exe" if os.name == "nt" else "backend")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "NATIVESTORE"))}
        env.update(
            PATH=str(out / "no-python"),
            NATIVESTORE_SUPERVISED="1",
            NATIVESTORE_DATA_DIR=str(out / "store"),
        )
        process = subprocess.Popen(
            [str(executable)],
            cwd=out,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            lines = queue.Queue()
            threading.Thread(
                target=lambda: lines.put(process.stdout.readline()), daemon=True
            ).start()
            line = lines.get(timeout=30)
            if not line:
                raise RuntimeError(process.stderr.read())
            ready = json.loads(line)
            url = urlsplit(ready["url"])
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
            connection.request("GET", url.path + "?" + url.query)
            response = connection.getresponse()
            assert response.status == 303
            cookie = response.getheader("Set-Cookie").split(";")[0]
            response.read()
            connection.close()
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
            connection.request("GET", "/", headers={"Cookie": cookie})
            response = connection.getresponse()
            assert response.status == 200 and b"Expense Desk" in response.read()
            connection.close()
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=10)
            connection.request(
                "POST",
                "/__nativestore/invoke",
                json.dumps(
                    {
                        "protocol": 1,
                        "command": "add_expense",
                        "args": {"description": "Frozen test", "amount_cents": 1234},
                    }
                ),
                {
                    "Cookie": cookie,
                    "Origin": f"http://{url.netloc}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            assert response.status == 200 and json.loads(response.read())["ok"]
            connection.close()
            process.stdin.close()
            assert process.wait(timeout=10) == 0
            print("Frozen backend passed without Python on PATH.")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
