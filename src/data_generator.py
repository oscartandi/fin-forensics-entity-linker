import random
from datetime import datetime, timedelta
from typing import Dict, List, Any


def generate_synthetic_network(seed: int = 42) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates a synthetic financial network containing entities (Accounts, Companies,
    Devices, IPs, UBOs) and edges (Transfers, Logins, Ownership) with injected
    AML/fraud typologies for forensic testing.
    """
    random.seed(seed)
    base_time = datetime(2026, 11, 1, 9, 0, 0)

    entities: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Baseline Legitimate Accounts & Corporate Entities
    for i in range(1, 21):
        entities.append({
            "id": f"ACC_{i:03d}",
            "type": "Account",
            "label": f"Retail_Account_{i}",
            "jurisdiction": random.choice(["IN", "SG", "UK", "US", "AE"]),
            "risk_flag": False,
        })

    for i in range(1, 35):
        src = f"ACC_{random.randint(1, 20):03d}"
        dst = f"ACC_{random.randint(1, 20):03d}"
        if src != dst:
            edges.append({
                "source": src,
                "target": dst,
                "relation": "TRANSFERRED_TO",
                "amount": round(random.uniform(500.0, 15000.0), 2),
                "currency": "USD",
                "timestamp": (base_time + timedelta(hours=i * 2)).isoformat(),
            })

    # 2. Typology A: Circular Flow / Round-Tripping Ring (4-Hop Cycle)
    # ACC_101 -> ACC_102 -> ACC_103 -> ACC_104 -> ACC_101 with ~4% decay per hop
    ring_accounts = ["ACC_101", "ACC_102", "ACC_103", "ACC_104"]
    for idx, acc_id in enumerate(ring_accounts):
        entities.append({
            "id": acc_id,
            "type": "Account",
            "label": f"Offshore_Trading_{idx + 1}",
            "jurisdiction": random.choice(["CY", "BVI", "PA", "AE"]),
            "risk_flag": False,
        })

    ring_amounts = [250000.0, 241000.0, 232500.0, 224000.0]
    for i in range(len(ring_accounts)):
        src = ring_accounts[i]
        dst = ring_accounts[(i + 1) % len(ring_accounts)]
        edges.append({
            "source": src,
            "target": dst,
            "relation": "TRANSFERRED_TO",
            "amount": ring_amounts[i],
            "currency": "USD",
            "timestamp": (base_time + timedelta(hours=10 + i * 3)).isoformat(),
        })

    # 3. Typology B: Mule Ring / Shared Device & IP Farm
    shared_device = "DEV_MULE_99"
    shared_ip = "185.220.101.44"
    entities.extend([
        {"id": shared_device, "type": "Device", "label": "Rooted_Android_Device", "risk_flag": True},
        {"id": shared_ip, "type": "IP", "label": "High_Risk_Exit_Node", "risk_flag": True},
    ])

    mule_accounts = ["ACC_201", "ACC_202", "ACC_203", "ACC_204", "ACC_205"]
    for idx, m_acc in enumerate(mule_accounts):
        entities.append({
            "id": m_acc,
            "type": "Account",
            "label": f"Mule_Node_{idx + 1}",
            "jurisdiction": "IN",
            "risk_flag": False,
        })
        edges.append({
            "source": m_acc,
            "target": shared_device,
            "relation": "LOGGED_IN_FROM",
            "timestamp": (base_time + timedelta(minutes=15 * idx)).isoformat(),
        })
        edges.append({
            "source": m_acc,
            "target": shared_ip,
            "relation": "CONNECTED_VIA",
            "timestamp": (base_time + timedelta(minutes=15 * idx)).isoformat(),
        })
        # Funneling funds from mules into a single collector account (ACC_299)
        edges.append({
            "source": m_acc,
            "target": "ACC_299",
            "relation": "TRANSFERRED_TO",
            "amount": 9800.0,
            "currency": "USD",
            "timestamp": (base_time + timedelta(hours=2, minutes=10 * idx)).isoformat(),
        })

    entities.append({
        "id": "ACC_299",
        "type": "Account",
        "label": "Aggregator_Collector_Vault",
        "jurisdiction": "AE",
        "risk_flag": False,
    })

    # 4. Typology C: Hidden UBO Exposure via Layered Shell Companies
    entities.extend([
        {"id": "PER_PEP_01", "type": "Person", "label": "Sanctioned_Beneficial_Owner", "risk_flag": True},
        {"id": "COMP_SHELL_A", "type": "Company", "label": "Apex_Holdings_Ltd", "jurisdiction": "BVI", "risk_flag": False},
        {"id": "COMP_SHELL_B", "type": "Company", "label": "Meridian_Logistics_FZE", "jurisdiction": "AE", "risk_flag": False},
        {"id": "ACC_301", "type": "Account", "label": "Meridian_Operating_Acct", "jurisdiction": "AE", "risk_flag": False},
    ])

    edges.extend([
        {"source": "COMP_SHELL_A", "target": "PER_PEP_01", "relation": "OWNED_BY", "ownership_pct": 100.0},
        {"source": "COMP_SHELL_B", "target": "COMP_SHELL_A", "relation": "OWNED_BY", "ownership_pct": 85.0},
        {"source": "ACC_301", "target": "COMP_SHELL_B", "relation": "HELD_BY", "ownership_pct": 100.0},
    ])

    return {"entities": entities, "edges": edges}


if __name__ == "__main__":
    network = generate_synthetic_network()
    print(f"Generated {len(network['entities'])} entities and {len(network['edges'])} relationships.")
