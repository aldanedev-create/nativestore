import json
import platform

import pytest

from nativestore.assets import Assets, digest
from nativestore.builder import build, stage
from nativestore.cli import main, new_project
from nativestore.errors import AssetError, BuildError, NativeStoreError


@pytest.fixture
def assets(project, tmp_path):
    data = b"console.log('verified');"
    entry = dict(
        name="htmx",
        version="1.0.0",
        url="https://cdn.jsdelivr.net/test.js",
        path="htmx.js",
        sha256=digest(data),
        license="MIT",
        license_url="https://example.test/LICENSE",
    )
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"schema": 1, "packages": [entry]}))
    manager = Assets(project, tmp_path / "cache", registry)
    return manager, data


def test_verified_cache_install_remove(assets):
    manager, data = assets
    manager.cache.mkdir()
    (manager.cache / digest(data)).write_bytes(data)
    manager.add("htmx@1.0.0", offline=True)
    manager.verify()
    assert manager.locked()[0]["version"] == "1.0.0"
    manager.remove("htmx")
    assert manager.locked() == []


def test_corrupt_cache_rejected(assets):
    manager, data = assets
    manager.cache.mkdir()
    (manager.cache / digest(data)).write_bytes(b"corrupt")
    with pytest.raises(AssetError):
        manager.add("htmx", offline=True)
    assert not manager.lock_path.exists()


def test_hash_mismatch(assets, monkeypatch):
    manager, _ = assets
    monkeypatch.setattr("nativestore.assets.download", lambda _: b"tampered")
    with pytest.raises(AssetError, match="Integrity"):
        manager.add("htmx")


def test_lock_tampering(assets):
    manager, _ = assets
    entry = dict(manager.registry["packages"][0], path="../../secret")
    manager.save([entry])
    with pytest.raises(AssetError):
        manager.locked()


def test_unapproved_version(assets):
    with pytest.raises(AssetError):
        assets[0].resolve("htmx@999")


def test_stage_excludes_private_files(project, tmp_path):
    (project / ".env").write_text("secret")
    (project / "app/.env").write_text("secret")
    (project / "app/data.db").write_text("private data")
    desktop = stage(project, tmp_path / "stage")
    assert desktop.is_dir()
    staged = desktop.parent / "project"
    assert not (staged / ".env").exists()
    assert not (staged / "app/data.db").exists()
    assert (staged / "templates/Layout.html").exists()
    assert json.loads((desktop / "tauri.conf.json").read_text())["bundle"]["targets"] == ["nsis"]


def test_unsupported_build(project, monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    with pytest.raises(BuildError, match="Windows"):
        build(project)


def test_scaffold_preserves_existing(project):
    with pytest.raises(NativeStoreError):
        new_project("expense-desk", project.parent)


@pytest.mark.parametrize("name", ["../evil", "BadName", "a/b", "", "x;rm"])
def test_bad_project_name(tmp_path, name):
    with pytest.raises(NativeStoreError):
        new_project(name, tmp_path)


def test_cli_routes_and_errors(project, monkeypatch, capsys):
    monkeypatch.chdir(project)
    assert main(["routes"]) == 0
    assert json.loads(capsys.readouterr().out)["protocol"] == 1
    assert main(["add", "unknown"]) == 1


def test_staging_collects_installed_dependency_versions(project, tmp_path):
    desktop = stage(project, tmp_path / "inventory-stage")
    records = json.loads(
        (desktop.parent / "project/THIRD_PARTY_LICENSES/python-dependencies.json").read_text()
    )
    assert {"nativestore", "jinjax", "jinja2", "markupsafe"}.issubset(
        {e["name"].lower() for e in records}
    )
    assert all(e["version"] for e in records)
