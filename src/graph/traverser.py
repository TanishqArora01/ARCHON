import networkx as nx

class GraphImpactTraverser:
    @staticmethod
    def calculate_blast_radius(G: nx.DiGraph, altered_node_id: str) -> dict:
        """
        Calculates the blast radius of a given node in the graph.
        
        An edge A -> B (e.g. A CALLS B) means A depends on B.
        If B is altered, it impacts A.
        Therefore, we must find all nodes that can reach B in the directed graph.
        We do this by reversing the graph and finding descendants.
        """
        if altered_node_id not in G:
            return {
                "impacted_node_ids": [],
                "blast_radius_score": 0.0
            }
            
        # Create a view of the graph with all edges reversed
        reversed_G = G.reverse(copy=False)
        
        # Find all downstream nodes affected by this change (which are descendants in the reversed graph)
        impacted_nodes = set(nx.descendants(reversed_G, altered_node_id))
        impacted_nodes.add(altered_node_id)
        
        total_nodes = G.number_of_nodes()
        score = len(impacted_nodes) / total_nodes if total_nodes > 0 else 0.0
        
        return {
            "impacted_node_ids": list(impacted_nodes),
            "blast_radius_score": float(score)
        }

    @staticmethod
    def calculate_centrality(G: nx.DiGraph) -> dict:
        try:
            return nx.pagerank(G)
        except Exception:
            return nx.degree_centrality(G)
