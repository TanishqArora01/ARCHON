"""
src/agents/workflow.py
─────────────────────
Phase 9: Agentic Intelligence — LangGraph DAG Orchestrator

Node execution order:
    planner_node
        ↓ (conditional routing)
    architecture_agent_node  ┐  (parallel — each with its own NVIDIA NIM model)
    maintainability_agent_node
    technical_debt_agent_node
    impact_agent_node         ┘
        ↓ (all converge)
    synthesis_node
        ↓
    END

When LLM_PROVIDER=nvidia, each agent uses a dedicated NVIDIA NIM model:
  planner        → meta/llama-3.1-70b-instruct
  architecture   → meta/llama-3.3-70b-instruct
  maintainability → mistralai/mistral-large-2-instruct
  technical_debt → google/gemma-3-27b-it
  impact         → nvidia/llama-3.1-nemotron-70b-instruct
  synthesis      → meta/llama-3.1-8b-instruct
"""

from __future__ import annotations

import json
import logging
from typing import List

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from src.agents.architecture_agent import ArchitectureAgent
from src.agents.impact_agent import ImpactAgent
from src.agents.llm_provider import BaseLLMProvider, build_llm_provider, build_agent_llm_provider
from src.agents.maintainability_agent import MaintainabilityAgent
from src.agents.schemas import AgentReport
from src.agents.state import GraphState
from src.agents.synthesis_agent import SynthesisAgent
from src.retrieval.assembler import ContextAssembler
from src.observability.decorators import trace_and_time

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
# Routing Schema
# ────────────────────────────────────────────────────────────────────────────

class RoutingPlan(BaseModel):
    """
    Structured output from the Planner node.
    The planner must respond with exactly this JSON structure.
    """
    selected_agents: List[str]
    rationale: str


_PLANNER_SYSTEM_PROMPT = """You are the Planner Agent for Archon, an AI Staff Engineer platform.

Your job is to read a pre-assembled repository context block and decide which specialist
analysis agents should be activated for this request.

Available specialists:
- "architecture"     — detects layer violations, boundary issues, architecture drift
- "maintainability"  — detects coupling, complexity, technical debt, refactoring opportunities
- "technical_debt"   — forecasts structural drag and compounding costs for structural choke points
- "impact"           — evaluates change impact, blast radius, and risk scoring

You MUST respond with a single valid JSON object matching this exact schema:
{
  "selected_agents": ["architecture", "maintainability", "technical_debt", "impact"],
  "rationale": "<one sentence explaining why these agents were chosen>"
}

Rules:
- `selected_agents` must contain at least one value.
- Valid values are only: "architecture", "maintainability", "technical_debt", "impact".
- Do not output markdown, only raw JSON.
- When in doubt, activate all specialists.
"""


# ────────────────────────────────────────────────────────────────────────────
# Node Definitions
# ────────────────────────────────────────────────────────────────────────────

@trace_and_time("agent_execution_latency", agent_type="planner")
async def planner_node(state: GraphState, llm: BaseLLMProvider) -> dict:
    """
    Evaluates the assembled context and produces a RoutingPlan.
    Writes `selected_agents` and `routing_rationale` into shared state.
    """
    preselected = state.get("selected_agents") or []
    if preselected:
        return {
            "selected_agents": preselected,
            "routing_rationale": state.get("routing_rationale") or "Pre-selected agent run.",
        }

    context_str = ContextAssembler.format_context_for_llm(state["assembled_context"])

    raw = await llm.complete(
        system_prompt=_PLANNER_SYSTEM_PROMPT,
        user_message=context_str,
    )

    # Parse routing plan — default to all agents on parse failure
    try:
        from src.agents.parsing import parse_json_from_llm
        data = parse_json_from_llm(raw)
        plan = RoutingPlan(**data)

        # Sanitise: keep only valid agent names
        valid = {"architecture", "maintainability", "technical_debt", "impact"}
        selected = [a for a in plan.selected_agents if a in valid]
        if not selected:
            selected = ["architecture", "maintainability", "technical_debt", "impact"]
        rationale = plan.rationale
    except Exception:
        logger.warning("Planner returned malformed JSON; defaulting to all agents.")
        selected = ["architecture", "maintainability", "technical_debt", "impact"]
        rationale = "Defaulted due to planner parse failure."

    return {
        "selected_agents": selected,
        "routing_rationale": rationale,
    }


@trace_and_time("agent_execution_latency", agent_type="architecture")
async def architecture_agent_node(state: GraphState, llm: BaseLLMProvider) -> dict:
    """Runs the ArchitectureAgent and appends its report to the parallel channel."""
    agent = ArchitectureAgent(llm_provider=llm)
    report: AgentReport = await agent.analyze(state["assembled_context"])
    return {"raw_specialist_reports": [report]}


@trace_and_time("agent_execution_latency", agent_type="maintainability")
async def maintainability_agent_node(state: GraphState, llm: BaseLLMProvider) -> dict:
    """Runs the MaintainabilityAgent and appends its report to the parallel channel."""
    agent = MaintainabilityAgent(llm_provider=llm)
    report: AgentReport = await agent.analyze(state["assembled_context"])
    return {"raw_specialist_reports": [report]}


@trace_and_time("agent_execution_latency", agent_type="technical_debt")
async def technical_debt_agent_node(state: GraphState, llm: BaseLLMProvider) -> dict:
    """Runs the TechnicalDebtAgent and appends its report to the parallel channel."""
    from src.agents.debt_agent import TechnicalDebtAgent
    agent = TechnicalDebtAgent(llm_provider=llm)
    report: AgentReport = await agent.analyze(state["assembled_context"])
    return {"raw_specialist_reports": [report]}


@trace_and_time("agent_execution_latency", agent_type="impact")
async def impact_agent_node(state: GraphState, llm: BaseLLMProvider) -> dict:
    """Runs the ImpactAgent and appends its report to the parallel channel."""
    agent = ImpactAgent(llm_provider=llm)
    report: AgentReport = await agent.analyze(state["assembled_context"])
    return {"raw_specialist_reports": [report]}


@trace_and_time("agent_execution_latency", agent_type="synthesis")
async def synthesis_node(state: GraphState) -> dict:
    """
    Deterministic convergence node — no LLM call.
    Merges all specialist reports via SynthesisAgent and writes the final report.
    """
    synth = SynthesisAgent()
    final = synth.synthesize(state["raw_specialist_reports"])
    return {"final_report": final}


# ────────────────────────────────────────────────────────────────────────────
# Conditional Routing
# ────────────────────────────────────────────────────────────────────────────

def route_to_specialists(state: GraphState) -> list[str]:
    """
    Inspects `state.selected_agents` and returns the node names to activate.
    LangGraph will execute all returned names concurrently using Send().
    """
    mapping = {
        "architecture": "architecture_agent",
        "maintainability": "maintainability_agent",
        "technical_debt": "technical_debt_agent",
        "impact": "impact_agent",
    }
    return [mapping[a] for a in state["selected_agents"] if a in mapping]


# ────────────────────────────────────────────────────────────────────────────
# Graph Factory
# ────────────────────────────────────────────────────────────────────────────

def build_archon_graph(llm: BaseLLMProvider | None = None):
    """
    Constructs and compiles the Archon LangGraph DAG.

    When ``llm`` is explicitly provided (e.g. in tests), that single provider
    is used for ALL nodes — planner and all specialists.

    When ``llm`` is None (production), each specialist agent gets its own
    per-agent LLM provider via ``build_agent_llm_provider()``.
    When LLM_PROVIDER=nvidia, each agent routes to its specialized NVIDIA NIM
    model from build.nvidia.com.

    Parameters
    ----------
    llm : BaseLLMProvider | None
        Override LLM for all nodes. Pass None in production.

    Returns
    -------
    CompiledGraph
        A compiled, executable LangGraph state machine.
    """
    # If an explicit LLM is passed (e.g. in tests), use it for all nodes.
    # Otherwise each node gets its own per-agent provider.
    if llm is not None:
        planner_llm = llm
        arch_llm = llm
        maint_llm = llm
        debt_llm = llm
        impact_llm = llm
    else:
        planner_llm = build_agent_llm_provider("planner")
        arch_llm = build_agent_llm_provider("architecture")
        maint_llm = build_agent_llm_provider("maintainability")
        debt_llm = build_agent_llm_provider("technical_debt")
        impact_llm = build_agent_llm_provider("impact")

    graph = StateGraph(GraphState)

    # ── Node wrappers (async def so LangGraph can properly await them) ────
    async def _planner(s: GraphState) -> dict:
        return await planner_node(s, planner_llm)

    async def _arch(s: GraphState) -> dict:
        return await architecture_agent_node(s, arch_llm)

    async def _maint(s: GraphState) -> dict:
        return await maintainability_agent_node(s, maint_llm)

    async def _debt(s: GraphState) -> dict:
        return await technical_debt_agent_node(s, debt_llm)

    async def _impact(s: GraphState) -> dict:
        return await impact_agent_node(s, impact_llm)

    # ── Register nodes ────────────────────────────────────────────────────
    graph.add_node("planner", _planner)  # type: ignore
    graph.add_node("architecture_agent", _arch)  # type: ignore
    graph.add_node("maintainability_agent", _maint)  # type: ignore
    graph.add_node("technical_debt_agent", _debt)  # type: ignore
    graph.add_node("impact_agent", _impact)  # type: ignore
    graph.add_node("synthesis", synthesis_node)  # type: ignore

    # ── Edges ──────────────────────────────────────────────────────────────
    # Entry point
    graph.add_edge(START, "planner")

    # Conditional fan-out: planner → specialist(s) concurrently
    graph.add_conditional_edges(
        "planner",
        route_to_specialists,
        {
            "architecture_agent": "architecture_agent",
            "maintainability_agent": "maintainability_agent",
            "technical_debt_agent": "technical_debt_agent",
            "impact_agent": "impact_agent",
        },
    )

    # All specialist paths converge at synthesis
    graph.add_edge("architecture_agent", "synthesis")
    graph.add_edge("maintainability_agent", "synthesis")
    graph.add_edge("technical_debt_agent", "synthesis")
    graph.add_edge("impact_agent", "synthesis")

    # Terminal
    graph.add_edge("synthesis", END)

    return graph.compile()

