"""Stage real compiled artifacts into a platform wheel; never invent artifact hashes."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from nativestore.runtime import PROTOCOL, VERSION, platform_key

parser = argparse.ArgumentParser()
parser.add_argument("--desktop", required=True, type=Path)
parser.add_argument("--tools", required=True, type=Path)
parser.add_argument("--destination", type=Path, default=Path("src/nativestore/native"))
args = parser.parse_args()
args.destination.mkdir(parents=True, exist_ok=True)
entries = []
for kind in ("desktop", "tools"):
    source = getattr(args, kind).resolve(strict=True)
    name = "nativestore-" + kind + (".exe" if platform_key().startswith("windows") else "")
    target = args.destination / name
    shutil.copy2(source, target)
    with target.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    entries.append({"kind": kind, "platform": platform_key(), "file": name, "sha256": sha256})
(args.destination / "manifest.json").write_text(
    json.dumps(
        {"schema": 1, "version": VERSION, "protocol": PROTOCOL, "artifacts": entries}, indent=2
    )
    + "\n"
)
print("Staged native artifacts for", platform_key())
