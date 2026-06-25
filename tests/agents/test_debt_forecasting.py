import json
import networkx as nx
import pytest

from src.analysis.debt_forecaster import TopologicalDebtForecaster
from src.agents.llm_provider import BaseLLMProvider
from src.agents.state import GraphState
from src.agents.workflow import build_archon_graph
from src.retrieval.schemas import AssembledAgentContext, StructuralContext, SemanticContext
from src.agents.schemas import AgentReport, Severity

# ---------------------------------------------------------------------------
# Unit Test: Topological Debt Forecaster
# ---------------------------------------------------------------------------

def test_topological_debt_forecaster():
    """
    Test that a highly coupled "God Object" scores significantly higher 
    TDI than a simple, independent helper node.
    """
    G = nx.DiGraph()

    # Create a God Object node
    G.add_node("god_object", symbol_name="GodObject", file_path="core/god.py")
    
    # Create simple helper nodes
    G.add_node("helper1", symbol_name="HelperOne", file_path="utils/help1.py")
    G.add_node("helper2", symbol_name="HelperTwo", file_path="utils/help2.py")
    G.add_node("helper3", symbol_name="HelperThree", file_path="utils/help3.py")

    # The helpers depend on the god object (e.g. they call it)
    G.add_edge("helper1", "god_object", edge_type="CALLS")
    G.add_edge("helper2", "god_object", edge_type="CALLS")
    G.add_edge("helper3", "god_object", edge_type="CALLS")
    
    # Create an independent, uncoupled helper node
    G.add_node("loner", symbol_name="Loner", file_path="utils/loner.py")
    
    ast_metadata = {
        "god_object": {"complexity": 50.0},
        "helper1": {"complexity": 2.0},
        "helper2": {"complexity": 1.0},
        "helper3": {"complexity": 3.0},
        "loner": {"complexity": 1.0}
    }

    choke_points = TopologicalDebtForecaster.compute_technical_debt_index(G, ast_metadata)
    
    assert len(choke_points) > 0
    # The first choke point must be the god object
    top_cp = choke_points[0]
    assert top_cp.node_id == "god_object"
    assert top_cp.complexity_score == 50.0
    
    # Its blast radius should be higher than the helpers 
    # (Since 3 nodes depend on god_object, its descendants in reversed graph are 3)
    # Loner's blast radius is 0
    
    loner_cp = next((cp for cp in choke_points if cp.node_id == "loner"), None)
    assert loner_cp is not None
    assert top_cp.tdi > loner_cp.tdi

# ---------------------------------------------------------------------------
# Integration Test: LangGraph Routing for Technical Debt
# ---------------------------------------------------------------------------

def _make_debt_context(token: str = "debt-wf-001") -> AssembledAgentContext:
    return AssembledAgentContext(
        tracking_token=token,
        structural=StructuralContext(
            impacted_file_paths=["core/god.py"],
            impacted_symbol_ids=["god_object"],
            blast_radius_score=0.8,
            choke_points=[
                {
                    "node_id": "god_object",
                    "symbol_name": "GodObject",
                    "file_path": "core/god.py",
                    "centrality_score": 0.45,
                    "blast_radius_score": 0.8,
                    "complexity_score": 50.0,
                    "tdi": 18.0
                }
            ]
        ),
        semantic=SemanticContext(
            documentation_chunks=["The core/god.py module handles everything."],
            relevance_scores=[0.90],
            source_files=["docs/arch.md"]
        )
    )

class MockDebtOrchestratorLLM(BaseLLMProvider):
    """
    Deterministic mock that ensures TechnicalDebtAgent is routed to.
    """
    async def complete(self, system_prompt: str, user_message: str) -> str:
        if "Planner Agent" in system_prompt:
            return json.dumps({
                "selected_agents": ["technical_debt"],
                "rationale": "High TDI detected in the structural context choke points."
            })
        elif "Technical Debt Agent" in system_prompt:
            return json.dumps({
                "findings": [{
                    "issue": "Severe Structural Choke Point at GodObject",
                    "evidence": "TDI is 18.0 with complexity 50.0",
                    "reasoning": "GodObject intersects high complexity and extreme coupling.",
                    "impact": "Unmanageable maintenance costs in the future.",
                    "recommendation": "Decompose GodObject into domain-specific services.",
                    "severity": "HIGH"
                }]
            })
        return json.dumps({"findings": []})

@pytest.mark.asyncio
async def test_full_dag_technical_debt_activated():
    """
    Verify that planner can select technical_debt and route to it, 
    and that synthesis combines the result correctly.
    """
    compiled = build_archon_graph(llm=MockDebtOrchestratorLLM())

    initial_state: GraphState = {
        "assembled_context": _make_debt_context(),
        "selected_agents": [],
        "routing_rationale": "",
        "raw_specialist_reports": [],
        "final_report": None,
    }

    result = await compiled.ainvoke(initial_state)

    # Agent should have been routed
    assert "technical_debt" in result["selected_agents"]

    # Specialist report must have been collected
    assert len(result["raw_specialist_reports"]) == 1
    agent_names = {r.agent_name for r in result["raw_specialist_reports"]}
    assert "TechnicalDebtAgent" in agent_names

    # Final synthesised report must exist
    final: AgentReport = result["final_report"]
    assert final is not None
    assert final.agent_name == "SynthesisAgent"
    
    assert len(final.findings) == 1
    assert final.findings[0].severity == Severity.HIGH
    assert "GodObject" in final.findings[0].issue
