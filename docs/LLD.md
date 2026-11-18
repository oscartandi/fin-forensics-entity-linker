# Low-Level Design (LLD): Multi-Hop Financial Forensics & Entity Link Toolkit

## 1. Repository & Module Structure

```text
fin-forensics-entity-linker/
├── docs/
│   ├── HLD.md                 # High-Level System Architecture & Scaling Blueprint
│   └── LLD.md                 # Low-Level Module, Algorithm & Schema Specification
├── src/
│   ├── __init__.py
│   ├── graph_builder.py       # Graph schema, node/edge builders & synthetic typology seeder
│   ├── forensics.py           # Subgraph extraction, cycle decay, Louvain & UBO algorithms
│   ├── sar_generator.py       # Regulatory SAR/UAR narrative template engine
│   ├── visualizer.py          # Interactive HTML5 Canvas force-directed graph generator
│   └── api.py                 # FastAPI application, endpoints & Pydantic models
├── tests/
│   └── test_forensics.py      # Unit & integration test suite (pytest)
├── requirements.txt
└── README.md
```

---

## 2. Graph Data Model & Ontology

### Node Types (`node_type`)
| Label | Primary Key Pattern | Key Properties |
| :--- | :--- | :--- |
| `Account` | `ACC_xxx` | `owner_name`, `account_type`, `country`, `risk_flag` |
| `Company` | `COMP_xxx` | `name`, `jurisdiction`, `is_shell`, `incorporation_date` |
| `Person` | `PER_xxx` | `name`, `nationality`, `is_pep`, `is_sanctioned` |
| `Device` | `DEV_xxx` | `device_hash`, `os_family`, `first_seen` |
| `IP` | `IP_xxx` | `ip_address`, `asn`, `is_vpn_or_tor` |

### Directed Edge Types (`edge_type`)
| Relationship | Source $
ightarrow$ Target | Edge Attributes |
| :--- | :--- | :--- |
| `TRANSFERRED_TO` | `Account` $
ightarrow$ `Account` | `amount` (float), `currency` (str), `timestamp` (ISO-8601), `tx_id` (str) |
| `LOGGED_IN_FROM` | `Account` $
ightarrow$ `Device` | `timestamp` (ISO-8601), `session_count` (int) |
| `CONNECTED_VIA` | `Account` $
ightarrow$ `IP` | `timestamp` (ISO-8601), `geo_country` (str) |
| `HELD_BY` | `Account` $
ightarrow$ `Company` | `relationship_role` (str), `opened_date` (str) |
| `OWNED_BY` | `Company` $
ightarrow$ `Company` / `Person` | `ownership_pct` (float), `effective_date` (str) |

---

## 3. Core Algorithmic Specifications & Complexity

### A. Circular Flow (Round-Tripping) Detection (`detect_circular_flows`)
* **Objective:** Detect layered money laundering loops where funds return to the originator with minimal fee/commission loss.
* **Algorithm:**
  1. Extract induced directed transaction subgraph $G_{tx} = (V_{acc}, E_{tx})$ within $k$ hops.
  2. Enumerate elementary directed cycles $C = (v_0 
ightarrow v_1 
ightarrow \dots 
ightarrow v_m 
ightarrow v_0)$ where $3 \le m \le 6$.
  3. Compute **Value Retention Ratio**:
     $$	ext{Retention Ratio} = rac{	ext{Amount}(v_{m} 
ightarrow v_0)}{	ext{Amount}(v_0 
ightarrow v_1)}$$
  4. Flag cycle if $	ext{Retention Ratio} \ge 0.75$ (i.e., value decay $< 25\%$) and timestamps are monotonically non-decreasing.
* **Complexity:** $O((V_{sub} + E_{sub})(c + 1))$ on bounded $k$-hop subgraph using Johnson's cycle-finding algorithm.

### B. Mule Ring / Device Farm Detection (`detect_mule_communities`)
* **Objective:** Identify coordinated synthetic identity or mule account clusters sharing infrastructure.
* **Algorithm:**
  1. Project bipartite infrastructure edges (`LOGGED_IN_FROM`, `CONNECTED_VIA`) onto an undirected account co-occurrence graph $G_{infra}$.
  2. Weight edges between accounts $(u, v)$ by shared device/IP count.
  3. Partition $G_{infra}$ using **Louvain Modularity Optimization** (`nx.community.louvain_communities`).
  4. Flag clusters where $\ge 3$ distinct accounts share a single `Device` hash or high-risk exit `IP` as `INFRASTRUCTURE_MULE_RING`.
* **Complexity:** $O(V_{sub} \log V_{sub})$ average case for Louvain community partitioning.

### C. Hidden UBO Exposure Traversal (`trace_ubo_exposure`)
* **Objective:** Uncover indirect control or ownership by Politically Exposed Persons (PEPs) or Sanctioned entities across nested shell companies.
* **Algorithm:**
  1. Filter graph to corporate/ownership edges (`HELD_BY`, `OWNED_BY`).
  2. Execute Breadth-First Search (BFS) from `entity_id` up to depth $d \le 	ext{hops}$.
  3. Inspect every reachable terminal or intermediate `Person` / `Company` node for `is_sanctioned == True` or `is_pep == True`.
  4. Calculate **Effective Ownership Stake**:
     $$	ext{Effective Ownership} = \prod_{e \in 	ext{path}} rac{	ext{ownership\_pct}(e)}{100}$$
* **Complexity:** $O(V_{own} + E_{own})$ via BFS traversal.

---

## 4. Risk Scoring Matrix (`calculate_forensic_score`)

| Triggered Typology | Base Score Contribution | Severity Thresholds |
| :--- | :--- | :--- |
| `HIDDEN_SANCTIONED_UBO_EXPOSURE` | `+50` pts (Critical Compliance Hit) | `0 – 24`: **LOW** |
| `CIRCULAR_FLOW_ROUND_TRIPPING` | `+40` pts | `25 – 49`: **MEDIUM** |
| `INFRASTRUCTURE_MULE_RING` | `+35` pts | `50 – 74`: **HIGH** |
| `PEP_UBO_EXPOSURE` | `+25` pts | `75 – 100`: **CRITICAL** (Capped at 100) |

---

## 5. REST API Endpoint & Schema Contracts (`src/api.py`)

### `GET /investigate/{entity_id}`
* **Query Parameters:** `hops: int = Query(default=3, ge=1, le=6)`
* **Response Model (`InvestigationReport`):**
```json
{
  "entity_id": "ACC_301",
  "hops_analyzed": 3,
  "forensic_risk_score": 50,
  "risk_severity": "HIGH",
  "detected_typologies": [
    "HIDDEN_SANCTIONED_UBO_EXPOSURE"
  ],
  "circular_flows": [],
  "mule_cluster_peers": [],
  "ubo_exposures": [
    {
      "high_risk_entity": "PER_PEP_01",
      "label": "Sanctioned_Beneficial_Owner",
      "hops_away": 3,
      "ownership_chain": [
        "ACC_301",
        "COMP_SHELL_B",
        "COMP_SHELL_A",
        "PER_PEP_01"
      ]
    }
  ]
}
```

### Error Handling Contract
* `404 Not Found`: Returned when `entity_id` does not exist in the active graph vertex set.
* `422 Unprocessable Entity`: Returned by FastAPI/Pydantic when `hops` falls outside `[1, 6]`.
