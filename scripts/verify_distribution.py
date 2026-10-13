"""Inspect actual wheel/sdist contents and any shipped native artifact integrity."""

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path, nargs="?", default=Path("dist"))
args = parser.parse_args()
files = list(args.directory.glob("*.whl")) + list(args.directory.glob("*.tar.gz"))
if not files:
    raise SystemExit("No distributions to verify")
for file in files:
    if file.suffix == ".whl":
        with zipfile.ZipFile(file) as archive:
            names = archive.namelist()
            assert not any("/target/" in n or "__pycache__" in n for n in names)
            for relative in (
                "bridge.js",
                "desktop/src/main.rs",
                "desktop/icons/icon.ico",
                "scaffold/main.py",
                "scaffold/templates/Layout.html",
                "licenses/alpine.txt",
            ):
                assert "nativestore/" + relative in names, relative
            manifest = "nativestore/native/manifest.json"
            if manifest in names:
                data = json.loads(archive.read(manifest))
                assert data["version"] == "0.1.0" and data["protocol"] == 1
                for entry in data["artifacts"]:
                    content = archive.read("nativestore/native/" + entry["file"])
                    assert hashlib.sha256(content).hexdigest() == entry["sha256"]
                assert not file.name.endswith("none-any.whl"), (
                    "Native binaries require a platform wheel"
                )
    else:
        with tarfile.open(file) as archive:
            names = archive.getnames()
            assert any(n.endswith("/README.md") for n in names)
            assert any(n.endswith("/setup.py") for n in names)
            assert any(n.endswith("/tests/conftest.py") for n in names)
            assert not any("/native/manifest.json" in n for n in names), (
                "sdist must not embed platform binaries"
            )
    print("Verified", file.name)
