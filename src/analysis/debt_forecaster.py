import networkx as nx
from typing import Dict, List, Optional
from pydantic import BaseModel

class ChokePoint(BaseModel):
    node_id: str
    symbol_name: str
    file_path: str
    centrality_score: float
    blast_radius_score: float
    complexity_score: float
    tdi: float

class TopologicalDebtForecaster:
    @staticmethod
    def compute_technical_debt_index(G: nx.DiGraph, ast_metadata: Optional[Dict[str, dict]] = None) -> List[ChokePoint]:
        if ast_metadata is None:
            ast_metadata = {}
            
        if G.number_of_nodes() == 0:
            return []

        # Centrality
        try:
            centrality = nx.pagerank(G)
        except Exception:
            # Fallback to degree centrality if pagerank fails to converge
            centrality = nx.degree_centrality(G)

        total_nodes = G.number_of_nodes()
        reversed_G = G.reverse(copy=False)

        choke_points = []
        for node_id in G.nodes():
            node_data = G.nodes[node_id]
            symbol_name = node_data.get("symbol_name", str(node_id))
            file_path = node_data.get("file_path", "unknown")
            
            # Blast radius
            impacted = nx.descendants(reversed_G, node_id)
            blast_radius = len(impacted) / total_nodes if total_nodes > 0 else 0.0

            # Complexity
            complexity = node_data.get("cyclomatic_complexity") or ast_metadata.get(node_id, {}).get("complexity", 1.0)
            
            # TDI
            c_score = centrality.get(node_id, 0.0)
            tdi = c_score * blast_radius * complexity

            choke_points.append(ChokePoint(
                node_id=node_id,
                symbol_name=symbol_name,
                file_path=file_path,
                centrality_score=c_score,
                blast_radius_score=blast_radius,
                complexity_score=complexity,
                tdi=tdi
            ))
            
        # Sort by highest TDI and return top 5
        choke_points.sort(key=lambda x: x.tdi, reverse=True)
        return choke_points[:5]
