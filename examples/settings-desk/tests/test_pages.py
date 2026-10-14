from nativestore.loader import load_app
from nativestore.testing import TestClient
from pathlib import Path


def test_starter():
    with load_app(Path(__file__).resolve().parents[1]) as app:
        client = TestClient(app)
        assert client.get("/").status == 200
        assert "Welcome to NativeStore" in client.get("/").body
        assert client.post("/greet", form={"name": "Ada"}).status == 200
        assert client.post("/greet", form={"name": ""}).status == 422
