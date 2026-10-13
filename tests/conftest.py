import pytest

from nativestore.cli import new_project


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("NATIVESTORE_DATA_DIR", str(tmp_path / "data"))
    return new_project("expense-desk", tmp_path)
