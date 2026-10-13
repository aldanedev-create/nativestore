"""Resolve versioned native executables from wheels or a trusted release manifest."""

import hashlib
import json
import platform
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from .assets import atomic
from .config import safe_path
from .errors import NativeStoreError

VERSION = "0.1.0"
PROTOCOL = 1
MAX_RUNTIME = 150 * 1024 * 1024


def platform_key() -> str:
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    machine = platform.machine().lower()
    architecture = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine)
    if system is None or architecture is None:
        raise NativeStoreError("No supported native runtime for this platform")
    return f"{system}-{architecture}"


def checksum(file: Path) -> str:
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Runtime:
    def __init__(self, manifest: Path | None = None, cache: Path | None = None):
        self.directory = Path(__file__).with_name("native")
        self.manifest = manifest or self.directory / "manifest.json"
        self.cache = cache or Path.home() / ".cache/nativestore/runtimes"

    def entries(self) -> list[dict]:
        if not self.manifest.is_file():
            return []
        try:
            data = json.loads(self.manifest.read_text())
            if set(data) != {"schema", "version", "protocol", "artifacts"}:
                raise ValueError("Unknown manifest fields")
            if (
                type(data["schema"]) is not int
                or type(data["protocol"]) is not int
                or data["schema"] != 1
                or data["protocol"] != PROTOCOL
                or data["version"] != VERSION
            ):
                raise ValueError("Incompatible native runtime version/protocol")
            if not isinstance(data["artifacts"], list):
                raise ValueError("artifacts must be a list")
            keys = set()
            for entry in data["artifacts"]:
                if set(entry) not in (
                    {"kind", "platform", "file", "sha256"},
                    {"kind", "platform", "file", "sha256", "url"},
                ):
                    raise ValueError("Invalid artifact schema")
                if not all(isinstance(v, str) for v in entry.values()):
                    raise ValueError("Invalid artifact values")
                if entry["kind"] not in ("desktop", "tools"):
                    raise ValueError("Unknown runtime artifact kind")
                if not re.fullmatch(r"(?:windows|linux|macos)-(?:x86_64|arm64)", entry["platform"]):
                    raise ValueError("Invalid platform")
                if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.exe)?", entry["file"]):
                    raise ValueError("Artifact must have a safe executable filename")
                if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
                    raise ValueError("Invalid artifact hash")
                key = (entry["kind"], entry["platform"])
                if key in keys:
                    raise ValueError("Duplicate native artifact")
                keys.add(key)
            return data["artifacts"]
        except (ValueError, TypeError, KeyError) as exc:
            raise NativeStoreError(f"Invalid native runtime manifest: {exc}") from exc

    def resolve(self, kind: str) -> Path | None:
        entry = next(
            (e for e in self.entries() if e["kind"] == kind and e["platform"] == platform_key()),
            None,
        )
        if entry is None:
            return None
        for directory in (self.manifest.parent, self.cache / entry["sha256"]):
            file = safe_path(directory, entry["file"])
            if file.is_file():
                if file.stat().st_size > MAX_RUNTIME or checksum(file) != entry["sha256"]:
                    raise NativeStoreError(f"Native {kind} artifact failed integrity verification")
                return file
        return None

    def install(self, kind: str, *, offline: bool = False) -> Path:
        present = self.resolve(kind)
        if present:
            return present
        entry = next(
            (e for e in self.entries() if e["kind"] == kind and e["platform"] == platform_key()),
            None,
        )
        if entry is None:
            raise NativeStoreError(f"No trusted {kind} artifact for this platform")
        if offline or "url" not in entry:
            raise NativeStoreError("Verified runtime is unavailable offline")
        source = urlsplit(entry["url"])
        if (
            source.scheme != "https"
            or source.netloc != "github.com"
            or not re.fullmatch(r"/[^/]+/[^/]+/releases/download/[^/]+/[^/]+", source.path)
            or source.query
        ):
            raise NativeStoreError("Runtime must use an approved GitHub release URL")

        class Redirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                parts = urlsplit(newurl)
                if parts.scheme != "https" or parts.hostname not in (
                    "github.com",
                    "release-assets.githubusercontent.com",
                    "objects.githubusercontent.com",
                ):
                    raise NativeStoreError("Unsafe native runtime redirect")
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        with urllib.request.build_opener(Redirect()).open(entry["url"], timeout=30) as stream:
            data = stream.read(MAX_RUNTIME + 1)
        if len(data) > MAX_RUNTIME or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise NativeStoreError("Downloaded runtime failed integrity verification")
        target = safe_path(self.cache / entry["sha256"], entry["file"])
        atomic(target, data)
        target.chmod(target.stat().st_mode | 0o700)
        return target
