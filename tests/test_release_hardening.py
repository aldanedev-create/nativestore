import hashlib
import json
import threading
import time
from dataclasses import replace

import pytest

from nativestore import App, ConfigurationError, NativeStoreError
from nativestore.assets import Assets, digest
from nativestore.config import Config
from nativestore.runtime import Runtime, platform_key


def test_deadline_preserves_single_execution_and_recovers(project):
    app = App(root=project)
    app.config = replace(app.config, command_timeout=0.05)
    release = threading.Event()
    finished = threading.Event()

    @app.command()
    def delayed() -> int:
        release.wait(timeout=2)
        finished.set()
        return 42

    message = {"protocol": 1, "command": "delayed", "args": {}}
    try:
        started = time.monotonic()
        assert app.invoke(message)["error"]["code"] == "execution_timeout"
        assert time.monotonic() - started < 1
        assert app.invoke(message)["error"]["code"] == "execution_busy"
        release.set()
        assert finished.wait(timeout=2)
        # Dispatch queues only after the preceding job has released its admission lock.
        app.execution.worker.join(timeout=0.01)
        assert app.invoke(message)["result"] == 42
    finally:
        release.set()
        app.close()


def test_large_result_and_recursive_internal_command(project):
    app = App(root=project)
    app.config = replace(app.config, max_result_bytes=1024)

    @app.command()
    def too_large() -> str:
        return "x" * 2000

    @app.command()
    def inner() -> int:
        return 12

    @app.command()
    def outer() -> int:
        return app.invoke({"protocol": 1, "command": "inner", "args": {}})["result"]

    try:
        assert (
            app.invoke({"protocol": 1, "command": "too_large", "args": {}})["error"]["code"]
            == "result_too_large"
        )
        assert app.invoke({"protocol": 1, "command": "outer", "args": {}})["result"] == 12
    finally:
        app.close()


@pytest.mark.parametrize(
    "values",
    [
        {"command_timeout": True},
        {"request_workers": 0},
        {"max_result_bytes": 1},
        {"hidden_imports": ("a..b",)},
        {"extra_resources": ("../secret",)},
    ],
)
def test_hardened_config_rejects_bad_values(tmp_path, values):
    with pytest.raises(ConfigurationError):
        Config(**values).validate(tmp_path)


def test_real_asset_threads_do_not_lose_lock_entries(project, tmp_path):
    entries = []
    cache = tmp_path / "cache"
    cache.mkdir()
    for name in ("first", "second"):
        data = name.encode()
        entry = {
            "name": name,
            "version": "1",
            "url": f"https://cdn.jsdelivr.net/{name}.js",
            "path": name + ".js",
            "sha256": digest(data),
            "license": "MIT",
            "license_url": "https://example.test/license",
        }
        entries.append(entry)
        (cache / entry["sha256"]).write_bytes(data)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"schema": 1, "packages": entries}))
    managers = [Assets(project, cache, registry) for _ in entries]
    errors = []

    def install(manager, name):
        try:
            manager.add(name, offline=True)
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=install, args=(manager, entry["name"]))
        for manager, entry in zip(managers, entries, strict=True)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert not errors
    assert {e["name"] for e in managers[0].locked()} == {"first", "second"}
    managers[0].verify()


def test_asset_rollback_on_lock_write_failure(project, tmp_path, monkeypatch):
    manager = Assets(project)
    entry = manager.registry["packages"][0]
    data = b"new-content"
    monkeypatch.setattr(manager, "bytes", lambda *_: data)
    target = project / "static/vendor" / entry["path"]
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(b"old-content")
    monkeypatch.setattr(manager, "save", lambda _: (_ for _ in ()).throw(OSError("disk error")))
    with pytest.raises(OSError):
        manager.add(entry["name"])
    assert target.read_bytes() == b"old-content"


def test_real_runtime_integrity_and_compatibility(tmp_path):
    binary = tmp_path / "nativestore-desktop"
    binary.write_bytes(b"actual-local-artifact")
    manifest = tmp_path / "manifest.json"
    data = {
        "schema": 1,
        "version": "0.1.0",
        "protocol": 1,
        "artifacts": [
            {
                "kind": "desktop",
                "platform": platform_key(),
                "file": binary.name,
                "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            }
        ],
    }
    manifest.write_text(json.dumps(data))
    runtime = Runtime(manifest, tmp_path / "cache")
    assert runtime.install("desktop", offline=True) == binary
    binary.write_bytes(b"corrupted")
    with pytest.raises(NativeStoreError, match="integrity"):
        runtime.resolve("desktop")
    data["version"] = "9.0.0"
    manifest.write_text(json.dumps(data))
    with pytest.raises(NativeStoreError, match="version"):
        runtime.resolve("desktop")


def test_runtime_path_traversal_rejected(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "version": "0.1.0",
                "protocol": 1,
                "artifacts": [
                    {
                        "kind": "desktop",
                        "platform": platform_key(),
                        "file": "../binary",
                        "sha256": "0" * 64,
                    }
                ],
            }
        )
    )
    with pytest.raises(NativeStoreError):
        Runtime(manifest).resolve("desktop")


def test_project_config_is_authoritative_and_relative_handlers_load(project):
    from nativestore.loader import load_app

    config = project / "nativestore.toml"
    config.write_text(
        config.read_text() + '\ncommand_timeout = 0.5\nnative_features = ["window"]\n'
    )
    (project / "pages/_helper.py").write_text('message = "relative import works"')
    (project / "pages/relative.py").write_text(
        "from ._helper import message\ndef page(ctx): return message\n"
    )
    with load_app(project) as app:
        assert app.config.command_timeout == 0.5
        assert app.config.native_features == ("window",)
        assert app.dispatch("/relative").body == "relative import works"


def test_native_feature_configuration_rejects_unknown_permissions(tmp_path):
    with pytest.raises(ConfigurationError):
        Config(native_features=("shell",)).validate(tmp_path)


def test_headless_client_handles_real_query_and_form_requests(project):
    from nativestore.testing import TestClient

    with App(root=project) as app:
        app.page("/query")(lambda ctx: ctx.json(ctx.query))
        app.page("/form", method="POST")(lambda ctx: ctx.json(ctx.body))
        client = TestClient(app)
        assert json.loads(client.get("/query?name=Ada&name=Grace").body) == {
            "name": ["Ada", "Grace"]
        }
        assert json.loads(client.post("/form", form={"name": "Ada"}).body) == {"name": ["Ada"]}
