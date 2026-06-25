"""
src/agents/workflow.py
─────────────────────
Phase 9: Agentic Intelligence — LangGraph DAG Orchestrator

Node execution order:
    planner_node
        ↓ (conditional routing)
    architecture_agent_node  ┐  (parallel)
    maintainability_agent_node ┘
        ↓ (both converge)
    synthesis_node
        ↓
    END
"""

from __future__ import annotations

import json
import logging
from typing import List

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from src.agents.architecture_agent import ArchitectureAgent
from src.agents.llm_provider import BaseLLMProvider, build_llm_provider
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

You MUST respond with a single valid JSON object matching this exact schema:
{
  "selected_agents": ["architecture", "maintainability", "technical_debt"],
  "rationale": "<one sentence explaining why these agents were chosen>"
}

Rules:
- `selected_agents` must contain at least one value.
- Valid values are only: "architecture", "maintainability", "technical_debt".
- Do not output markdown, only raw JSON.
- When in doubt, activate both specialists.
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
    context_str = ContextAssembler.format_context_for_llm(state["assembled_context"])

    raw = await llm.complete(
        system_prompt=_PLANNER_SYSTEM_PROMPT,
        user_message=context_str,
    )

    # Parse routing plan — default to both agents on parse failure
    try:
        data = json.loads(raw)
        plan = RoutingPlan(**data)

        # Sanitise: keep only valid agent names
        valid = {"architecture", "maintainability", "technical_debt"}
        selected = [a for a in plan.selected_agents if a in valid]
        if not selected:
            selected = ["architecture", "maintainability", "technical_debt"]
        rationale = plan.rationale
    except Exception:
        logger.warning("Planner returned malformed JSON; defaulting to all agents.")
        selected = ["architecture", "maintainability", "technical_debt"]
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
    }
    return [mapping[a] for a in state["selected_agents"] if a in mapping]


# ────────────────────────────────────────────────────────────────────────────
# Graph Factory
# ────────────────────────────────────────────────────────────────────────────

def build_archon_graph(llm: BaseLLMProvider | None = None):
    """
    Constructs and compiles the Archon LangGraph DAG.

    Parameters
    ----------
    llm : BaseLLMProvider
        The LLM backend to inject into all nodes that require one.
        Defaults to OllamaLLMProvider (qwen2.5) if not supplied.

    Returns
    -------
    CompiledGraph
        A compiled, executable LangGraph state machine.
    """
    if llm is None:
        llm = build_llm_provider()

    graph = StateGraph(GraphState)

    # ── Node wrappers (async def so LangGraph can properly await them) ────
    async def _planner(s: GraphState) -> dict:
        return await planner_node(s, llm)

    async def _arch(s: GraphState) -> dict:
        return await architecture_agent_node(s, llm)

    async def _maint(s: GraphState) -> dict:
        return await maintainability_agent_node(s, llm)

    async def _debt(s: GraphState) -> dict:
        return await technical_debt_agent_node(s, llm)

    # ── Register nodes ────────────────────────────────────────────────────
    graph.add_node("planner", _planner)  # type: ignore
    graph.add_node("architecture_agent", _arch)  # type: ignore
    graph.add_node("maintainability_agent", _maint)  # type: ignore
    graph.add_node("technical_debt_agent", _debt)  # type: ignore
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
        },
    )

    # Both specialist paths converge at synthesis
    graph.add_edge("architecture_agent", "synthesis")
    graph.add_edge("maintainability_agent", "synthesis")
    graph.add_edge("technical_debt_agent", "synthesis")

    # Terminal
    graph.add_edge("synthesis", END)

    return graph.compile()
