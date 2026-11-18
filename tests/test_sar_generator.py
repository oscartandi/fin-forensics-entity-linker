from fastapi.testclient import TestClient
from src.api import app
from src.sar_generator import generate_sar_narrative

client = TestClient(app)


def test_generate_sar_narrative_high_risk():
    sample_investigation = {
        "entity_id": "ACC_301",
        "forensic_risk_score": 50,
        "risk_severity": "HIGH",
        "detected_typologies": ["HIDDEN_SANCTIONED_UBO_EXPOSURE"],
        "ubo_exposures": [
            {
                "high_risk_entity": "PER_PEP_01",
                "label": "Sanctioned_Beneficial_Owner",
                "hops_away": 3,
                "ownership_chain": ["ACC_301", "COMP_SHELL_B", "COMP_SHELL_A", "PER_PEP_01"],
            }
        ],
    }

    sar = generate_sar_narrative(sample_investigation)

    assert sar["subject_entity_id"] == "ACC_301"
    assert sar["recommended_action"] == "ESCALATE_SAR_FILING"
    assert "PER_PEP_01" in sar["narrative"]
    assert "ACC_301 -> COMP_SHELL_B -> COMP_SHELL_A -> PER_PEP_01" in sar["narrative"]


def test_sar_endpoint_success():
    response = client.get("/investigate/ACC_301/sar?hops=3")
    assert response.status_code == 200
    data = response.json()
    assert data["subject_entity_id"] == "ACC_301"
    assert "narrative" in data
    assert "recommended_action" in data


def test_sar_endpoint_not_found():
    response = client.get("/investigate/NON_EXISTENT_ID/sar")
    assert response.status_code == 404