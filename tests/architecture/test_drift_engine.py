import tempfile
import yaml
import os
import networkx as nx

from src.architecture.rules import ArchitectureRules, ComponentRules
from src.architecture.drift_engine import DriftEngine

def test_rules_parser():
    rules_dict = {
        "Controller": {
            "can_call": ["Service"]
        },
        "Service": {
            "can_call": ["Repository"]
        },
        "Forbidden": {
            "Controller": {
                "cannot_call": ["Database"]
            }
        }
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(rules_dict, f)
        f_name = f.name
    
    try:
        rules = ArchitectureRules.load_from_file(f_name)
        assert "Controller" in rules.components
        assert "Service" in rules.components
        
        ctrl = rules.components["Controller"]
        assert "Service" in ctrl.can_call
        assert "Database" in ctrl.cannot_call
        
        svc = rules.components["Service"]
        assert "Repository" in svc.can_call
    finally:
        os.remove(f_name)


def test_drift_engine():
    rules = ArchitectureRules(components={
        "Controller": ComponentRules(can_call=["Service"], cannot_call=["Database"]),
        "Service": ComponentRules(can_call=["Repository"]),
        "Repository": ComponentRules(can_call=["Database"]),
        "Database": ComponentRules()
    })
    
    engine = DriftEngine(rules)
    
    graph = nx.DiGraph()
    # Node attributes: symbol_name, file_path
    graph.add_node("n1", symbol_name="UserController", file_path="controllers/user.py")
    graph.add_node("n2", symbol_name="UserService", file_path="services/user.py")
    graph.add_node("n3", symbol_name="UserRepository", file_path="repositories/user.py")
    graph.add_node("n4", symbol_name="Database", file_path="db/connection.py")
    
    # Valid edge
    graph.add_edge("n1", "n2", edge_type="CALLS")
    # Valid edge
    graph.add_edge("n2", "n3", edge_type="CALLS")
    # Valid edge
    graph.add_edge("n3", "n4", edge_type="CALLS")
    
    # Invalid edge: Controller cannot call Database
    graph.add_edge("n1", "n4", edge_type="CALLS")
    
    # Invalid edge: Service calling Controller (not in can_call)
    graph.add_edge("n2", "n1", edge_type="CALLS")
    
    violations = engine.detect_drift(graph)
    
    assert len(violations) == 2
    
    cannot_call = [v for v in violations if v.rule_type == "cannot_call"]
    assert len(cannot_call) == 1
    assert cannot_call[0].from_component == "Controller"
    assert cannot_call[0].to_component == "Database"
    assert "cannot call" in cannot_call[0].message
    
    can_call = [v for v in violations if v.rule_type == "can_call"]
    assert len(can_call) == 1
    assert can_call[0].from_component == "Service"
    assert can_call[0].to_component == "Controller"
    assert "not permitted" in can_call[0].message
