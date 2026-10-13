"""OS-backed locks release on process exit; no stale lock-file deletion."""

import importlib
import os
import time
from contextlib import contextmanager
from pathlib import Path

from .errors import AssetError


@contextmanager
def project_lock(root: Path, timeout: float = 20):
    directory = root / ".nativestore"
    if directory.is_symlink():
        raise AssetError("Lock directory cannot be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "assets.lock"
    if path.is_symlink():
        raise AssetError("Lock file cannot be a symlink")
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    msvcrt = importlib.import_module("msvcrt")

                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl = importlib.import_module("fcntl")

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise AssetError("Another asset operation holds this project's lock") from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            if os.name == "nt":
                msvcrt = importlib.import_module("msvcrt")

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
