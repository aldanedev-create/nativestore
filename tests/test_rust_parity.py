import json
import os
import subprocess
from pathlib import Path

import pytest

from nativestore.router import manifest

BINARY = (
    Path(__file__).resolve().parents[1]
    / "target/debug"
    / ("nativestore-cli.exe" if os.name == "nt" else "nativestore-cli")
)
pytestmark = pytest.mark.skipif(not BINARY.is_file(), reason="Build Rust CLI for parity tests")


def test_manifest_parity(project):
    (project / "pages/users").mkdir()
    (project / "pages/users/[id].py").write_text("raise RuntimeError('must not execute')")
    result = subprocess.run([str(BINARY), "routes"], cwd=project, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == manifest(project)


def test_conflict_parity(project):
    (project / "pages/[name].py").write_text("")
    result = subprocess.run([str(BINARY), "routes"], cwd=project, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Ambiguous" in result.stderr


def test_unsafe_names(project):
    (project / "pages/bad.name.py").write_text("")
    result = subprocess.run([str(BINARY), "routes"], cwd=project, capture_output=True, text=True)
    assert result.returncode != 0


def test_native_config_plan_snapshot_and_assets(project):
    from dataclasses import asdict
    from pathlib import Path

    from nativestore.config import Config

    registry = Path(__file__).parents[1] / "src/nativestore/registry.json"
    expected = json.loads(json.dumps(asdict(Config.load(project))))
    result = subprocess.run([str(BINARY), "config"], cwd=project, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected
    result = subprocess.run(
        [str(BINARY), "build-plan"], cwd=project, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["installer"] == "nsis"
    result = subprocess.run([str(BINARY), "snapshot"], cwd=project, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "main.py" in {e["path"] for e in json.loads(result.stdout)}
    result = subprocess.run(
        [str(BINARY), "verify-assets", str(registry)], cwd=project, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
