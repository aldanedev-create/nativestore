from pathlib import Path
from nativestore.loader import load_app
from nativestore.testing import TestClient


def test_inventory():
    with load_app(Path(__file__).resolve().parents[3]) as app:
        client = TestClient(app)
        assert client.get("/inventory").status == 200
        result = client.post("/inventory/api/add", form={"name":"Bolts", "quantity":"5"})
        assert result.status == 200 and "Bolts" in result.body
        assert client.post("/inventory/api/add", form={"name":"", "quantity":"-1"}).status == 422
