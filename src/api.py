from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from src.data_generator import generate_synthetic_network
from src.graph_builder import ForensicGraphBuilder
from src.forensics_engine import FinancialForensicsEngine
from src.sar_generator import generate_sar_narrative
from fastapi.responses import HTMLResponse, RedirectResponse
from src.visualizer import build_ego_subgraph_payload, render_ego_network_html

app = FastAPI(
    title="Multi-Hop Financial Forensics & Entity Link API",
    description="Graph intelligence service for detecting round-tripping rings, mule clusters, and layered UBO exposure.",
    version="1.0.0",
)

# Initialize synthetic forensic graph in memory
_payload = generate_synthetic_network(seed=42)
_builder = ForensicGraphBuilder()
_graph = _builder.build_from_payload(_payload)
_engine = FinancialForensicsEngine(_graph)


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {"status": "healthy", "graph_stats": _builder.get_summary_stats()}


@app.get("/investigate/{entity_id}")
def investigate_entity(
    entity_id: str,
    hops: int = Query(default=4, ge=1, le=6, description="Multi-hop traversal radius"),
):
    try:
        return _engine.investigate_entity(entity_id=entity_id, hops=hops)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/investigate/{entity_id}/sar")
def get_entity_sar_report(
    entity_id: str,
    hops: int = Query(default=4, ge=1, le=6, description="Multi-hop traversal radius"),
):
    """Run multi-hop forensic investigation and compile an automated SAR narrative."""
    try:
        investigation = _engine.investigate_entity(entity_id=entity_id, hops=hops)
        return generate_sar_narrative(investigation)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/typologies/cycles")
def get_circular_laundering_rings(
    min_hops: int = Query(default=3, ge=3, le=6),
    max_hops: int = Query(default=6, ge=3, le=8),
):
    cycles = _engine.detect_circular_laundering(min_hops=min_hops, max_hops=max_hops)
    return {"total_cycles_detected": len(cycles), "cycles": cycles}


@app.get("/typologies/communities")
def get_mule_communities(min_size: int = 3):
    """Detect clustered mule rings and shared-device communities via Louvain algorithm."""
    communities = _engine.detect_mule_communities(min_size=min_size)
    return {
        "total_communities_detected": len(communities),
        "communities": communities,
    }

@app.get("/visualize/{entity_id}", response_class=HTMLResponse)
def visualize_entity_network(
    entity_id: str,
    hops: int = Query(default=3, ge=1, le=5, description="Multi-hop ego-network radius"),
):
    """Render an interactive Vis.js forensic network graph for the target entity."""
    try:
        payload = build_ego_subgraph_payload(_graph, entity_id=entity_id, hops=hops)
        return HTMLResponse(content=render_ego_network_html(payload))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))