from typing import List, Optional
import networkx as nx
from pydantic import BaseModel
from src.architecture.rules import ArchitectureRules

class DriftViolation(BaseModel):
    from_node_id: str
    from_node_name: str
    from_component: str
    to_node_id: str
    to_node_name: str
    to_component: str
    rule_type: str  # "can_call" or "cannot_call"
    message: str

class DriftEngine:
    """
    Detects architectural drift by validating a NetworkX graph against parsed ArchitectureRules.
    """
    def __init__(self, rules: ArchitectureRules):
        self.rules = rules

    def _determine_component(self, node_data: dict) -> Optional[str]:
        """
        Heuristic to map a node to a component defined in rules.
        Checks symbol_name and file_path (case-insensitive substring match).
        """
        symbol_name = node_data.get("symbol_name", "").lower()
        file_path = node_data.get("file_path", "").lower()

        # Iterate over configured components
        for component in self.rules.components.keys():
            comp_lower = component.lower()
            if comp_lower in symbol_name or comp_lower in file_path:
                return component
        return None

    def detect_drift(self, graph: nx.DiGraph) -> List[DriftViolation]:
        violations = []
        
        for u, v, data in graph.edges(data=True):
            edge_type = data.get("edge_type", "")
            # Only consider structural dependency edges
            if edge_type not in ("CALLS", "IMPORTS", "DEPENDS_ON"):
                continue

            from_node = graph.nodes[u]
            to_node = graph.nodes[v]

            from_comp = self._determine_component(from_node)
            to_comp = self._determine_component(to_node)

            if not from_comp or not to_comp:
                continue
                
            if from_comp == to_comp:
                continue  # Calls within same component are generally fine

            from_symbol = from_node.get("symbol_name", str(u))
            to_symbol = to_node.get("symbol_name", str(v))

            comp_rules = self.rules.components.get(from_comp)
            if not comp_rules:
                continue

            # Check explicit forbidden rules
            if to_comp in comp_rules.cannot_call:
                violations.append(DriftViolation(
                    from_node_id=str(u),
                    from_node_name=from_symbol,
                    from_component=from_comp,
                    to_node_id=str(v),
                    to_node_name=to_symbol,
                    to_component=to_comp,
                    rule_type="cannot_call",
                    message=f"Architecture Violation: {from_comp} ({from_symbol}) cannot call {to_comp} ({to_symbol})"
                ))
            
            # Check implicit boundaries (if can_call is defined)
            elif comp_rules.can_call and to_comp not in comp_rules.can_call:
                violations.append(DriftViolation(
                    from_node_id=str(u),
                    from_node_name=from_symbol,
                    from_component=from_comp,
                    to_node_id=str(v),
                    to_node_name=to_symbol,
                    to_component=to_comp,
                    rule_type="can_call",
                    message=f"Architecture Violation: {from_comp} ({from_symbol}) is not permitted to call {to_comp} ({to_symbol}). Permitted targets: {comp_rules.can_call}"
                ))

        return violations
