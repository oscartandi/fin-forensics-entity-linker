from fastapi.testclient import TestClient
from src.data_generator import generate_synthetic_network
from src.graph_builder import ForensicGraphBuilder
from src.forensics_engine import FinancialForensicsEngine
from src.api import app

client = TestClient(app)


def _build_test_engine() -> FinancialForensicsEngine:
    payload = generate_synthetic_network(seed=42)
    builder = ForensicGraphBuilder()
    graph = builder.build_from_payload(payload)
    return FinancialForensicsEngine(graph)


def test_circular_laundering_detection():
    engine = _build_test_engine()
    cycles = engine.detect_circular_laundering(min_hops=3, max_hops=6)
    assert len(cycles) >= 1
    ring = cycles[0]
    assert ring["hops"] == 4
    assert "ACC_101" in ring["cycle_path"]
    assert ring["value_decay_pct"] < 15.0


def test_mule_ring_shared_infrastructure():
    engine = _build_test_engine()
    result = engine.investigate_entity("ACC_201", hops=2)
    assert "MULE_RING_SHARED_INFRASTRUCTURE" in result["detected_typologies"]
    assert "DEV_MULE_99" in result["shared_infrastructure"]
    assert "ACC_202" in result["shared_infrastructure"]["DEV_MULE_99"]
    assert result["forensic_risk_score"] >= 45


def test_hidden_ubo_exposure():
    engine = _build_test_engine()
    result = engine.investigate_entity("ACC_301", hops=3)
    assert "HIDDEN_SANCTIONED_UBO_EXPOSURE" in result["detected_typologies"]
    assert len(result["ubo_exposures"]) == 1
    assert result["ubo_exposures"][0]["high_risk_entity"] == "PER_PEP_01"
    assert result["ubo_exposures"][0]["hops_away"] == 3


def test_api_endpoints():
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    inv_resp = client.get("/investigate/ACC_101?hops=3")
    assert inv_resp.status_code == 200
    data = inv_resp.json()
    assert data["entity_id"] == "ACC_101"
    assert "CIRCULAR_FLOW_ROUND_TRIPPING" in data["detected_typologies"]

    not_found = client.get("/investigate/UNKNOWN_999")
    assert not_found.status_code == 404
