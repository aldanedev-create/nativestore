from pathlib import Path

from nativestore.loader import load_app


def test_home_and_bridge(tmp_path, monkeypatch):
    monkeypatch.setenv("NATIVESTORE_DATA_DIR", str(tmp_path))
    app = load_app(Path(__file__).resolve().parents[1])
    assert "A little clarity" in app.dispatch("/").body
    result = app.invoke(
        {
            "protocol": 1,
            "command": "add_expense",
            "args": {"description": "Coffee", "amount_cents": 350},
        }
    )
    assert result["ok"]
    assert app.dispatch("/api/expenses").status == 200
