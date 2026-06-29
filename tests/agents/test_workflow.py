"""
tests/agents/test_workflow.py
─────────────────────────────
Integration tests for the Phase 9 LangGraph DAG.

All LLM calls are mocked — no live Ollama required.
"""

from __future__ import annotations

import json
import pytest

from src.agents.llm_provider import BaseLLMProvider
from src.agents.schemas import AgentReport, Severity
from src.agents.workflow import build_archon_graph
from src.agents.state import GraphState
from src.retrieval.schemas import AssembledAgentContext, StructuralContext, SemanticContext


# ────────────────────────────────────────────────────────────────────────────
# Helpers & Fixtures
# ────────────────────────────────────────────────────────────────────────────

def _make_context(token: str = "wf-test-001") -> AssembledAgentContext:
    return AssembledAgentContext(
        tracking_token=token,
        repository_name="test_repo",
        query_text="test query",
        structural=StructuralContext(
            impacted_file_paths=["core/auth.py", "api/routes.py"],
            impacted_symbol_ids=["node-auth-uuid", "node-routes-uuid"],
            blast_radius_score=0.67,
        ),
        semantic=SemanticContext(
            documentation_chunks=["AuthService is the canonical auth boundary per ADR-002."],
            relevance_scores=[0.98],
            source_files=["docs/adr/ADR-002-auth.md"],
        ),
    )


class MockOrchestratorLLM(BaseLLMProvider):
    """
    Deterministic mock that distinguishes calls by system prompt content.

    - Planner prompt   → returns RoutingPlan activating both specialists
    - Architecture     → returns one HIGH finding
    - Maintainability  → returns one MEDIUM finding
    """

    async def complete(self, system_prompt: str, user_message: str) -> str:
        if "Planner Agent" in system_prompt:
            return json.dumps({
                "selected_agents": ["architecture", "maintainability"],
                "rationale": "Both structural and maintainability analysis are warranted "
                             "given the high blast radius score.",
            })
        elif "Architecture Agent" in system_prompt:
            return json.dumps({
                "findings": [{
                    "issue": "Controller bypasses service layer",
                    "evidence": "api/routes.py directly imports core/auth.py "
                                "(blast_radius_score=0.67)",
                    "reasoning": "Violates the layered architecture declared in ADR-002.",
                    "impact": "Breaks testability and creates hidden coupling.",
                    "recommendation": "Route all authentication through AuthService.",
                    "severity": "HIGH",
                }]
            })
        elif "Maintainability Agent" in system_prompt:
            return json.dumps({
                "findings": [{
                    "issue": "AuthService has high coupling (blast radius 0.67)",
                    "evidence": "2 files directly depend on core/auth.py per structural context.",
                    "reasoning": "A blast radius above 0.3 signals fragile coupling.",
                    "impact": "Any change to AuthService risks cascading failures.",
                    "recommendation": "Extract an IAuthService interface to invert the dependency.",
                    "severity": "MEDIUM",
                }]
            })
        return json.dumps({"findings": []})


class MalformedPlannerLLM(BaseLLMProvider):
    """Planner returns garbage; specialists return valid findings."""

    async def complete(self, system_prompt: str, user_message: str) -> str:
        if "Planner Agent" in system_prompt:
            return "{{broken json}}"
        elif "Architecture Agent" in system_prompt:
            return json.dumps({
                "findings": [{
                    "issue": "Fallback architecture finding",
                    "evidence": "fallback evidence",
                    "reasoning": "fallback reasoning",
                    "impact": "fallback impact",
                    "recommendation": "fallback recommendation",
                    "severity": "LOW",
                }]
            })
        elif "Maintainability Agent" in system_prompt:
            return json.dumps({"findings": []})
        return json.dumps({"findings": []})


# ────────────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_dag_both_specialists_activated():
    """
    Happy path: planner selects both specialists, both run concurrently,
    SynthesisAgent merges into a single final report sorted HIGH-first.
    """
    compiled = build_archon_graph(llm=MockOrchestratorLLM())

    initial_state: GraphState = {
        "assembled_context": _make_context(),
        "selected_agents": [],
        "routing_rationale": "",
        "raw_specialist_reports": [],
        "final_report": None,
    }

    result = await compiled.ainvoke(initial_state)

    # Both agents must have been routed
    assert "architecture" in result["selected_agents"]
    assert "maintainability" in result["selected_agents"]

    # Both specialist reports must have been collected
    assert len(result["raw_specialist_reports"]) == 2
    agent_names = {r.agent_name for r in result["raw_specialist_reports"]}
    assert "ArchitectureAgent" in agent_names
    assert "MaintainabilityAgent" in agent_names

    # Final synthesised report must exist
    final: AgentReport = result["final_report"]
    assert final is not None
    assert final.agent_name == "SynthesisAgent"

    # Two distinct findings (one from each specialist)
    assert len(final.findings) == 2

    # HIGH severity must be ranked first
    assert final.findings[0].severity == Severity.HIGH
    assert final.findings[1].severity == Severity.MEDIUM

    # Tracking token must propagate through
    assert final.tracking_token == "wf-test-001"


@pytest.mark.asyncio
async def test_planner_malformed_json_defaults_to_all_agents():
    """
    When the planner returns unparseable JSON, the workflow must default
    to activating all specialists rather than crashing or producing no output.
    """
    compiled = build_archon_graph(llm=MalformedPlannerLLM())

    initial_state: GraphState = {
        "assembled_context": _make_context(),
        "selected_agents": [],
        "routing_rationale": "",
        "raw_specialist_reports": [],
        "final_report": None,
    }

    result = await compiled.ainvoke(initial_state)

    # Must have defaulted to all 4 agents
    assert set(result["selected_agents"]) == {"architecture", "maintainability", "technical_debt", "impact"}

    # Final report must still exist (the arch agent returned one LOW finding,
    # the maint agent returned nothing)
    final: AgentReport = result["final_report"]
    assert final is not None
    assert len(final.findings) == 1
    assert final.findings[0].severity == Severity.LOW
