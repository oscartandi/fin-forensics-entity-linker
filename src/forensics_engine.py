from typing import Any, Dict, List, Set
import networkx as nx


class FinancialForensicsEngine:
    """
    Executes multi-hop graph traversal, circular money laundering detection,
    shared infrastructure linking, and UBO exposure scoring.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    def _get_transfer_subgraph(self) -> nx.DiGraph:
        """Extracts a directed graph containing only TRANSFERRED_TO edges."""
        tx_graph = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            if data.get("relation") == "TRANSFERRED_TO":
                amount = float(data.get("amount", 0.0))
                if tx_graph.has_edge(u, v):
                    tx_graph[u][v]["amount"] += amount
                else:
                    tx_graph.add_edge(u, v, amount=amount, timestamp=data.get("timestamp"))
        return tx_graph

    def detect_circular_laundering(self, min_hops: int = 3, max_hops: int = 6, max_decay: float = 0.25) -> List[Dict[str, Any]]:
        """
        Detects round-tripping money laundering cycles where funds return to the
        originating account within [min_hops, max_hops] with bounded value loss.
        """
        tx_graph = self._get_transfer_subgraph()
        suspicious_cycles: List[Dict[str, Any]] = []

        for cycle in nx.simple_cycles(tx_graph):
            hop_count = len(cycle)
            if not (min_hops <= hop_count <= max_hops):
                continue
            
            hop_amounts = []
            for i in range(hop_count):
                u = cycle[i]
                v = cycle[(i + 1) % hop_count]
                hop_amounts.append(tx_graph[u][v]["amount"])

            # Find the largest transfer (the true starting point of the laundering ring)
            max_idx = hop_amounts.index(max(hop_amounts))
            cycle = cycle[max_idx:] + cycle[:max_idx]
            hop_amounts = hop_amounts[max_idx:] + hop_amounts[:max_idx]

            initial_amount = hop_amounts[0]
            final_amount = hop_amounts[-1]
            if initial_amount <= 0:
                continue

            retention_ratio = final_amount / initial_amount
            decay = 1.0 - retention_ratio

            if 0 <= decay <= max_decay:
                suspicious_cycles.append({
                    "cycle_path": cycle + [cycle[0]],
                    "hops": hop_count,
                    "initial_amount_usd": round(initial_amount, 2),
                    "returned_amount_usd": round(final_amount, 2),
                    "value_decay_pct": round(decay * 100, 2),
                })

        return suspicious_cycles

    def find_shared_infrastructure(self, entity_id: str) -> Dict[str, List[str]]:
        """
        Finds other accounts sharing the same Device or IP attributes as the target entity.
        """
        if entity_id not in self.graph:
            return {}

        shared_links: Dict[str, List[str]] = {}
        infra_relations = {"LOGGED_IN_FROM", "CONNECTED_VIA"}

        for _, target, data in self.graph.out_edges(entity_id, data=True):
            if data.get("relation") in infra_relations:
                co_users = [
                    src for src, _, e_data in self.graph.in_edges(target, data=True)
                    if e_data.get("relation") in infra_relations and src != entity_id
                ]
                if co_users:
                    shared_links[target] = sorted(list(set(co_users)))

        return shared_links

    def trace_ubo_exposure(self, entity_id: str, max_hops: int = 4) -> List[Dict[str, Any]]:
        """
        Traces ownership/control edges up to max_hops to detect links to high-risk
        or sanctioned Beneficial Owners (UBOs).
        """
        if entity_id not in self.graph:
            return []

        exposures: List[Dict[str, Any]] = []
        ownership_relations = {"OWNED_BY", "HELD_BY"}

        own_graph = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            if data.get("relation") in ownership_relations:
                own_graph.add_edge(u, v, relation=data.get("relation"))

        if entity_id not in own_graph:
            return []

        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("risk_flag") and node in own_graph and node != entity_id:
                if nx.has_path(own_graph, entity_id, node):
                    path = nx.shortest_path(own_graph, entity_id, node)
                    if len(path) - 1 <= max_hops:
                        exposures.append({
                            "high_risk_entity": node,
                            "label": attrs.get("label", "Unknown"),
                            "hops_away": len(path) - 1,
                            "ownership_chain": path,
                        })

        return exposures

    def investigate_entity(self, entity_id: str, hops: int = 3) -> Dict[str, Any]:
        """
        Performs a comprehensive multi-hop forensic investigation around an entity
        and computes an explainable composite risk score (0-100).
        """
        if entity_id not in self.graph:
            raise ValueError(f"Entity '{entity_id}' not found in forensic graph.")

        undirected = self.graph.to_undirected()
        ego_nodes: Set[str] = set(nx.single_source_shortest_path_length(undirected, entity_id, cutoff=hops).keys())
        subgraph = self.graph.subgraph(ego_nodes)

        cycles = [c for c in self.detect_circular_laundering() if entity_id in c["cycle_path"]]
        shared_infra = self.find_shared_infrastructure(entity_id)
        ubo_exposures = self.trace_ubo_exposure(entity_id, max_hops=hops)

        # Explainable Risk Scoring (0 - 100)
        risk_score = 0
        typology_flags: List[str] = []

        if self.graph.nodes[entity_id].get("risk_flag"):
            risk_score += 40
            typology_flags.append("DIRECT_WATCHLIST_OR_HIGH_RISK_FLAG")

        if cycles:
            risk_score += 45
            typology_flags.append("CIRCULAR_FLOW_ROUND_TRIPPING")

        if shared_infra:
            linked_accounts = sum(len(v) for v in shared_infra.values())
            risk_score += min(40, 15 + linked_accounts * 5)
            typology_flags.append("MULE_RING_SHARED_INFRASTRUCTURE")

        if ubo_exposures:
            risk_score += 50
            typology_flags.append("HIDDEN_SANCTIONED_UBO_EXPOSURE")

        risk_score = min(100, risk_score)
        severity = "CRITICAL" if risk_score >= 75 else "HIGH" if risk_score >= 45 else "MEDIUM" if risk_score >= 20 else "LOW"

        return {
            "entity_id": entity_id,
            "entity_metadata": dict(self.graph.nodes[entity_id]),
            "forensic_risk_score": risk_score,
            "risk_severity": severity,
            "detected_typologies": typology_flags,
            "circular_flows": cycles,
            "shared_infrastructure": shared_infra,
            "ubo_exposures": ubo_exposures,
            "subgraph_summary": {
                "hop_radius": hops,
                "connected_entities": len(subgraph.nodes),
                "connected_relationships": len(subgraph.edges),
            },
        }
    def detect_mule_communities(self, min_size: int = 3) -> list[dict]:
        """Detect tightly clustered mule rings and shared-infrastructure communities using Louvain."""
        undirected = self.graph.to_undirected()
        communities = nx.algorithms.community.louvain_communities(undirected, seed=42)

        suspicious_clusters = []
        for idx, community in enumerate(communities, start=1):
            if len(community) < min_size:
                continue

            accounts = []
            shared_infra = []
            for n in community:
                attrs = self.graph.nodes[n]
                node_type = str(attrs.get("entity_type") or attrs.get("type") or attrs.get("node_type") or "").lower()
                if node_type == "account" or str(n).startswith("ACC_"):
                    accounts.append(n)
                elif node_type in ("device", "ip") or str(n).startswith(("DEV_", "IP_")):
                    shared_infra.append(n)

            if len(accounts) >= 2 and len(shared_infra) >= 1:
                suspicious_clusters.append({
                    "community_id": f"COMM_{idx:02d}",
                    "total_nodes": len(community),
                    "linked_accounts": sorted(accounts),
                    "shared_infrastructure": sorted(shared_infra),
                    "typology": "MULE_RING_COMMUNITY",
                })

        return suspicious_clusters