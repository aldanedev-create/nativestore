import re
import tomllib
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError

current_project: ContextVar[Path | None] = ContextVar("nativestore_project", default=None)


@dataclass(frozen=True)
class Config:
    name: str = "nativestore-app"
    title: str = "NativeStore"
    entry: str = "main.py"
    width: int = 1100
    height: int = 750
    identifier: str = "dev.nativestore.app"
    version: str = "0.1.0"
    command_timeout: float = 30
    max_result_bytes: int = 1_048_576
    request_workers: int = 16
    hidden_imports: tuple[str, ...] = ()
    extra_resources: tuple[str, ...] = ()
    native_features: tuple[str, ...] = ()

    @classmethod
    def load(cls, root: Path) -> "Config":
        try:
            data = tomllib.loads((root / "nativestore.toml").read_text())
            if set(data) != {"app"} or not isinstance(data["app"], dict):
                raise ValueError("Expected only an [app] table")
            values = data["app"]
            for key in ("hidden_imports", "extra_resources", "native_features"):
                if key in values:
                    if not isinstance(values[key], list):
                        raise ValueError(f"{key} must be a list")
                    values[key] = tuple(values[key])
            config = cls(**values)
            config.validate(root)
            return config
        except (OSError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"Invalid nativestore.toml: {exc}") from exc

    def validate(self, root: Path) -> None:
        for field in ("name", "title", "entry", "identifier", "version"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field):
                raise ConfigurationError(f"{field} must be a nonempty string")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", self.name):
            raise ConfigurationError("name must be lowercase letters, digits and hyphens")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9-]*)+", self.identifier):
            raise ConfigurationError("identifier must be reverse-domain notation")
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise ConfigurationError("version must be major.minor.patch")
        if len(self.title) > 200:
            raise ConfigurationError("title must not exceed 200 characters")
        for field in ("width", "height"):
            value = getattr(self, field)
            if type(value) is not int or not 320 <= value <= 7680:
                raise ConfigurationError(f"{field} must be an integer from 320 to 7680")
        if (
            type(self.command_timeout) not in (int, float)
            or not 0.05 <= self.command_timeout <= 600
        ):
            raise ConfigurationError("command_timeout must be between 0.05 and 600 seconds")
        if (
            type(self.max_result_bytes) is not int
            or not 1024 <= self.max_result_bytes <= 20_971_520
        ):
            raise ConfigurationError("max_result_bytes must be between 1024 and 20971520")
        if type(self.request_workers) is not int or not 1 <= self.request_workers <= 64:
            raise ConfigurationError("request_workers must be between 1 and 64")
        if len(self.native_features) != len(set(self.native_features)) or any(
            name not in ("dialog", "clipboard", "notifications", "window")
            for name in self.native_features
        ):
            raise ConfigurationError("Unknown or duplicate native feature")
        for name in self.hidden_imports:
            if not isinstance(name, str) or not all(p.isidentifier() for p in name.split(".")):
                raise ConfigurationError("Invalid hidden import")
        for resource in self.extra_resources:
            safe_path(root, resource)
        if Path(self.entry).suffix != ".py":
            raise ConfigurationError("entry must be a Python file")
        safe_path(root, self.entry)


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise ConfigurationError("Invalid relative path")
    parts = relative.split("/")
    if Path(relative).is_absolute() or any(p in ("", ".", "..") or ":" in p for p in parts):
        raise ConfigurationError(f"Unsafe path: {relative!r}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ConfigurationError(f"Path escapes project: {relative!r}")
    return path
