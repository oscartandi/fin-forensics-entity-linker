import json
from typing import Any, Dict, List
import networkx as nx


NODE_STYLES: Dict[str, Dict[str, str]] = {
    "ACCOUNT": {"color": "#3b82f6", "shape": "circle", "group": "Account"},
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
            node_type, {"color": "#64748b", "shape": "circle", "group": node_type}
        )
        is_target = node_id == entity_id
        is_sanctioned = bool(attrs.get("is_sanctioned") or attrs.get("is_pep"))

        color = "#dc2626" if is_sanctioned else ("#22d3ee" if is_target else style["color"])
        radius = 22 if is_target else (19 if is_sanctioned else 15)

        nodes_payload.append(
            {
                "id": node_id,
                "label": f"{node_id} ({attrs.get('label', node_type)})",
                "details": {**attrs, "id": node_id},
                "color": color,
                "shape": style["shape"],
                "radius": radius,
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
    """Renders an offline-ready interactive HTML5 Canvas force-directed graph."""
    nodes_json = json.dumps(payload["nodes"])
    edges_json = json.dumps(payload["edges"])
    target = payload["target_entity"]
    hops = payload["hops"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Forensic Ego-Network: {target}</title>
  <style>
    body {{
      margin: 0;
      background-color: #0f172a;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      padding: 12px 20px;
      background: #1e293b;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
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
    #canvas-wrap {{
      position: relative;
      flex: 1;
      width: 100%;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
      cursor: grab;
    }}
    canvas:active {{
      cursor: grabbing;
    }}
    #inspector {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(30, 41, 59, 0.92);
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 0.82rem;
      max-width: 360px;
      color: #e2e8f0;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <strong>Forensic Ego-Network Explorer</strong> &mdash; Target: <code>{target}</code> (Radius: {hops} hops)
    </div>
    <div class="legend">
      <span style="color:#22d3ee">&#9679; Target</span>
      <span style="color:#3b82f6">&#9679; Account</span>
      <span style="color:#f59e0b">&#9670; Shell/Company</span>
      <span style="color:#ef4444">&#9733; Person/UBO</span>
      <span style="color:#8b5cf6">&#9650; Device</span>
      <span style="color:#10b981">&#9632; IP Node</span>
    </div>
    <span class="badge">{payload['node_count']} Nodes | {payload['edge_count']} Edges</span>
  </header>
  <div id="canvas-wrap">
    <canvas id="graphCanvas"></canvas>
    <div id="inspector">Drag any node to reposition &bull; Click a node to inspect metadata</div>
  </div>
  <script>
    const nodes = {nodes_json};
    const edges = {edges_json};
    const canvas = document.getElementById("graphCanvas");
    const ctx = canvas.getContext("2d");
    const inspector = document.getElementById("inspector");

    function resize() {{
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    }}
    window.addEventListener("resize", resize);
    resize();

    // Arrange nodes cleanly around center
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const spread = Math.min(cx, cy) * 0.55;
    nodes.forEach((n, i) => {{
      const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1);
      n.x = n.id === "{target}" ? cx : cx + spread * Math.cos(angle);
      n.y = n.id === "{target}" ? cy : cy + spread * Math.sin(angle);
    }});

    const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
    let dragging = null;

    function drawArrow(fromX, fromY, toX, toY, targetRadius) {{
      const dx = toX - fromX;
      const dy = toY - fromY;
      const dist = Math.hypot(dx, dy) || 1;
      const ux = dx / dist;
      const uy = dy / dist;
      const endX = toX - ux * (targetRadius + 6);
      const endY = toY - uy * (targetRadius + 6);
      const headLen = 10;
      const angle = Math.atan2(dy, dx);

      ctx.beginPath();
      ctx.moveTo(fromX, fromY);
      ctx.lineTo(endX, endY);
      ctx.strokeStyle = "#64748b";
      ctx.lineWidth = 1.8;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(endX, endY);
      ctx.lineTo(endX - headLen * Math.cos(angle - Math.PI / 6), endY - headLen * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(endX - headLen * Math.cos(angle + Math.PI / 6), endY - headLen * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fillStyle = "#94a3b8";
      ctx.fill();
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw directed edges + labels
      edges.forEach(e => {{
        const src = nodeMap[e.from];
        const dst = nodeMap[e.to];
        if (!src || !dst) return;
        drawArrow(src.x, src.y, dst.x, dst.y, dst.radius);

        const midX = (src.x + dst.x) / 2;
        const midY = (src.y + dst.y) / 2 - 6;
        ctx.font = "11px Segoe UI, sans-serif";
        ctx.fillStyle = "#cbd5e1";
        ctx.textAlign = "center";
        ctx.fillText(e.label, midX, midY);
      }});

      // Draw nodes + labels
      nodes.forEach(n => {{
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#f8fafc";
        ctx.stroke();

        ctx.font = "bold 12px Segoe UI, sans-serif";
        ctx.fillStyle = "#f8fafc";
        ctx.textAlign = "center";
        ctx.fillText(n.label, n.x, n.y + n.radius + 16);
      }});

      requestAnimationFrame(draw);
    }}

    canvas.addEventListener("mousedown", e => {{
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      for (const n of nodes) {{
        if (Math.hypot(mx - n.x, my - n.y) <= n.radius + 4) {{
          dragging = n;
          inspector.innerHTML = `<strong>${{n.id}}</strong> (${{n.group}})<br><pre style="margin:4px 0 0;white-space:pre-wrap;color:#93c5fd">${{JSON.stringify(n.details, null, 2)}}</pre>`;
          break;
        }}
      }}
    }});

    canvas.addEventListener("mousemove", e => {{
      if (!dragging) return;
      const rect = canvas.getBoundingClientRect();
      dragging.x = e.clientX - rect.left;
      dragging.y = e.clientY - rect.top;
    }});

    window.addEventListener("mouseup", () => {{ dragging = null; }});
    draw();
  </script>
</body>
</html>"""