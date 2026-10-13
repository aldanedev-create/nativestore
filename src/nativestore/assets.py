import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

from .config import safe_path
from .errors import AssetError
from .locking import project_lock

MAX_DOWNLOAD = 20 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(url: str) -> bytes:
    from urllib.parse import urlsplit

    def approved(value: str) -> bool:
        parts = urlsplit(value)
        return parts.scheme == "https" and parts.netloc == "cdn.jsdelivr.net" and not parts.username

    if not approved(url):
        raise AssetError("Only approved HTTPS asset sources are allowed")

    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not approved(newurl):
                raise AssetError("Unsafe asset redirect")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    try:
        with urllib.request.build_opener(Redirect()).open(url, timeout=20) as response:
            data = response.read(MAX_DOWNLOAD + 1)
        if len(data) > MAX_DOWNLOAD:
            raise AssetError("Asset exceeds download limit")
        return data
    except OSError as exc:
        raise AssetError(f"Asset download failed: {exc}") from exc


def atomic(path: Path, data: bytes) -> None:
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".nativestore-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Assets:
    def __init__(self, root: Path, cache: Path | None = None, registry: Path | None = None) -> None:
        self.root = root.resolve()
        self.registry_path = registry or Path(__file__).with_name("registry.json")
        self.cache = cache or Path.home() / ".cache/nativestore/assets"
        try:
            self.registry = json.loads(self.registry_path.read_text())
            if (
                set(self.registry) != {"schema", "packages"}
                or type(self.registry["schema"]) is not int
                or self.registry["schema"] != 1
            ):
                raise AssetError("Unsupported registry schema")
            for entry in self.registry["packages"]:
                if set(entry) != {
                    "name",
                    "version",
                    "url",
                    "path",
                    "sha256",
                    "license",
                    "license_url",
                }:
                    raise AssetError("Invalid registry entry")
                if not all(isinstance(v, str) and v for v in entry.values()):
                    raise AssetError("Invalid registry values")
                if not re.fullmatch(r"[a-z][a-z0-9-]*", entry["name"]):
                    raise AssetError("Invalid package name")
                if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
                    raise AssetError("Invalid integrity hash")
                safe_path(self.root / "static/vendor", entry["path"])
            identities = [(e["name"], e["version"]) for e in self.registry["packages"]]
            if len(identities) != len(set(identities)):
                raise AssetError("Duplicate registry identity")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise AssetError(f"Invalid asset registry: {exc}") from exc

    @property
    def lock_path(self) -> Path:
        return self.root / "nativestore.lock"

    def locked(self) -> list[dict]:
        if not self.lock_path.exists():
            return []
        try:
            data = json.loads(self.lock_path.read_text())
            if set(data) != {"schema", "packages"} or data["schema"] != 1:
                raise AssetError("Invalid lock schema")
            entries = data["packages"]
            if not isinstance(entries, list):
                raise AssetError("Invalid lock entries")
            for entry in entries:
                if entry not in self.registry["packages"]:
                    raise AssetError("Lock entry is not in the trusted registry")
            if len({e["name"] for e in entries}) != len(entries):
                raise AssetError("Duplicate locked package")
            return entries
        except (ValueError, TypeError, KeyError) as exc:
            raise AssetError("Invalid lock file") from exc

    def save(self, entries: list[dict]) -> None:
        atomic(
            self.lock_path,
            (
                json.dumps(
                    {"schema": 1, "packages": sorted(entries, key=lambda e: e["name"])}, indent=2
                )
                + "\n"
            ).encode(),
        )

    def resolve(self, spec: str) -> dict:
        name, sep, version = spec.partition("@")
        entries = [
            e
            for e in self.registry["packages"]
            if e["name"] == name and (not sep or e["version"] == version)
        ]
        if not entries:
            raise AssetError(f"No approved registry version for {spec}")
        return entries[-1]

    def bytes(self, entry: dict, offline: bool = False) -> bytes:
        file = self.cache / entry["sha256"]
        if file.is_file():
            data = file.read_bytes()
            if digest(data) == entry["sha256"]:
                return data
            file.unlink()
        if offline:
            raise AssetError(f"Verified cache unavailable for {entry['name']}")
        data = download(entry["url"])
        if digest(data) != entry["sha256"]:
            raise AssetError(f"Integrity check failed for {entry['name']}")
        atomic(file, data)
        return data

    def add(self, spec: str, *, offline: bool = False) -> None:
        entry = self.resolve(spec)
        data = self.bytes(entry, offline)
        with project_lock(self.root):
            entries = self.locked()
            file = safe_path(self.root / "static/vendor", entry["path"])
            previous = file.read_bytes() if file.exists() else None
            atomic(file, data)
            entries = [e for e in entries if e["name"] != entry["name"]] + [entry]
            try:
                self.save(entries)
            except Exception:
                if previous is None:
                    file.unlink(missing_ok=True)
                else:
                    atomic(file, previous)
                raise

    def remove(self, name: str) -> None:
        with project_lock(self.root):
            entries = self.locked()
            target = next((e for e in entries if e["name"] == name), None)
            if target is None:
                raise AssetError(f"Package is not installed: {name}")
            file = safe_path(self.root / "static/vendor", target["path"])
            previous = file.read_bytes() if file.exists() else None
            file.unlink(missing_ok=True)
            try:
                self.save([e for e in entries if e["name"] != name])
            except Exception:
                if previous is not None:
                    atomic(file, previous)
                raise

    def verify(self) -> None:
        import subprocess

        from .runtime import Runtime

        tools = Runtime().resolve("tools")
        if tools is not None:
            result = subprocess.run(
                [str(tools), "verify-assets", str(self.registry_path.resolve())],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode:
                raise AssetError(f"Native asset verification failed: {result.stderr.strip()}")
            return
        for entry in self.locked():
            file = safe_path(self.root / "static/vendor", entry["path"])
            if not file.is_file() or digest(file.read_bytes()) != entry["sha256"]:
                raise AssetError(f"Installed asset is missing or corrupt: {entry['name']}")

    def update(self, *, offline: bool = False) -> None:
        for entry in self.locked():
            self.add(entry["name"], offline=offline)
