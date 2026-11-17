from typing import Any, Dict, List
import networkx as nx


class ForensicGraphBuilder:
    """
    Constructs a heterogeneous directed multigraph (MultiDiGraph) representing
    financial entities (Accounts, Companies, Persons, Devices, IPs) and their
    multi-relational interactions (Transfers, Logins, Ownership).
    """

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def build_from_payload(self, payload: Dict[str, List[Dict[str, Any]]]) -> nx.MultiDiGraph:
        """Populates the NetworkX MultiDiGraph from entity and edge dictionaries."""
        self.graph.clear()

        for entity in payload.get("entities", []):
            node_id = entity["id"]
            attrs = {k: v for k, v in entity.items() if k != "id"}
            self.graph.add_node(node_id, **attrs)

        for edge in payload.get("edges", []):
            src = edge["source"]
            dst = edge["target"]
            attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
            self.graph.add_edge(src, dst, **attrs)

        return self.graph

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns node and edge counts grouped by entity and relationship type."""
        node_types: Dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            n_type = data.get("type", "Unknown")
            node_types[n_type] = node_types.get(n_type, 0) + 1

        edge_types: Dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            e_type = data.get("relation", "Unknown")
            edge_types[e_type] = edge_types.get(e_type, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_breakdown": node_types,
            "edge_breakdown": edge_types,
        }
