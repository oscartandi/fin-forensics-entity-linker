import json
from typing import Any, Dict, List
import networkx as nx


NODE_STYLES: Dict[str, Dict[str, str]] = {
    "ACCOUNT": {"color": "#3b82f6", "shape": "dot", "group": "Account"},
    "COMPANY": {"color": "#f59e0b", "shape": "diamond", "group": "Shell / Company"},
    "PERSON": {"color": "#ef4444", "shape": "star", "group": "Person / UBO"},
    "DEVICE": {"color": "#8b5cf6", "shape": "triangle", "group": "Device Hash"},
    "IP": {"color": "#10b981", "shape": "square", "group": "IP Exit Node"},
}


def build_ego_subgraph_payload(
    graph: nx.MultiDiGraph, entity_id: str, hops: int = 3
) -> Dict[str, Any]:
    """Extracts an undirected ego-network around entity_id and serializes nodes/edges."""
    if entity_id not in graph:
        raise ValueError(f"Entity '{entity_id}' not found in forensic graph.")

    undirected = graph.to_undirected()
    ego_nodes = nx.ego_graph(undirected, entity_id, radius=hops).nodes()
    sub = graph.subgraph(ego_nodes)

    nodes_payload: List[Dict[str, Any]] = []
    for node_id, attrs in sub.nodes(data=True):
        node_type = str(attrs.get("node_type", attrs.get("type", "ACCOUNT"))).upper()
        style = NODE_STYLES.get(
            node_type, {"color": "#64748b", "shape": "dot", "group": node_type}
        )
        is_target = node_id == entity_id
        is_sanctioned = bool(attrs.get("is_sanctioned") or attrs.get("is_pep"))

        color = "#dc2626" if is_sanctioned else ("#22d3ee" if is_target else style["color"])
        size = 28 if is_target else (24 if is_sanctioned else 18)

        nodes_payload.append(
            {
                "id": node_id,
                "label": f"{node_id}\n({attrs.get('label', node_type)})",
                "title": json.dumps({**attrs, "id": node_id}, default=str),
                "color": color,
                "shape": style["shape"],
                "size": size,
                "group": style["group"],
            }
        )

    edges_payload: List[Dict[str, Any]] = []
    for u, v, attrs in sub.edges(data=True):
        rel = attrs.get("relation", attrs.get("edge_type", "LINKED"))
        amount = attrs.get("amount")
        label = f"{rel} (${amount:,.0f})" if isinstance(amount, (int, float)) else str(rel)
        edges_payload.append(
            {
                "from": u,
                "to": v,
                "label": label,
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f8fafc"},
            }
        )

    return {
        "target_entity": entity_id,
        "hops": hops,
        "node_count": len(nodes_payload),
        "edge_count": len(edges_payload),
        "nodes": nodes_payload,
        "edges": edges_payload,
    }


def render_ego_network_html(payload: Dict[str, Any]) -> str:
    """Renders an interactive Vis.js dark-mode forensic graph canvas."""
    nodes_json = json.dumps(payload["nodes"])
    edges_json = json.dumps(payload["edges"])
    target = payload["target_entity"]
    hops = payload["hops"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Forensic Ego-Network: {target}</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{
      margin: 0;
      background-color: #0f172a;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    header {{
      padding: 12px 20px;
      background: #1e293b;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .badge {{
      background: #0284c7;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
    }}
    .legend {{
      display: flex;
      gap: 14px;
      font-size: 0.8rem;
      color: #cbd5e1;
    }}
    #network {{
      flex: 1;
      width: 100%;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <strong>Forensic Ego-Network Explorer</strong> &mdash; Target: <code>{target}</code> (Radius: {hops} hops)
    </div>
    <div class="legend">
      <span>&#9679; Target (Cyan)</span>
      <span>&#9679; Account (Blue)</span>
      <span>&#9670; Shell/Company (Amber)</span>
      <span>&#9733; Person/UBO (Red)</span>
      <span>&#9650; Device (Purple)</span>
      <span>&#9632; IP Node (Green)</span>
    </div>
    <span class="badge">{payload['node_count']} Nodes | {payload['edge_count']} Edges</span>
  </header>
  <div id="network"></div>
  <script>
    const nodes = new vis.DataSet({nodes_json});
    const edges = new vis.DataSet({edges_json});
    const container = document.getElementById("network");
    const data = {{ nodes, edges }};
    const options = {{
      nodes: {{
        font: {{ color: "#f8fafc", size: 12 }},
        borderWidth: 2
      }},
      edges: {{
        font: {{ color: "#cbd5e1", size: 10, align: "middle", strokeWidth: 0 }},
        smooth: {{ type: "dynamic" }}
      }},
      physics: {{
        stabilization: {{ iterations: 150 }},
        barnesHut: {{ gravitationalConstant: -4000, springLength: 140 }}
      }},
      interaction: {{ hover: true, tooltipDelay: 100 }}
    }};
    new vis.Network(container, data, options);
  </script>
</body>
</html>"""