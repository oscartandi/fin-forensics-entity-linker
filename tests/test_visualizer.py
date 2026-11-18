from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_visualize_entity_success():
    response = client.get("/visualize/ACC_301?hops=3")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ACC_301" in response.text
    assert "graphCanvas" in response.text


def test_visualize_entity_not_found():
    response = client.get("/visualize/UNKNOWN_NODE_999")
    assert response.status_code == 404