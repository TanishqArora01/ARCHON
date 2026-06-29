from __future__ import annotations

from typing import Annotated, List, Optional
from typing_extensions import TypedDict

from src.agents.schemas import AgentReport
from src.retrieval.schemas import AssembledAgentContext


def _append_reports(old: list[AgentReport], new: list[AgentReport]) -> list[AgentReport]:
    """
    Reducer for the parallel specialist report channel.

    LangGraph calls this function whenever a node writes to `raw_specialist_reports`.
    Using a list-append reducer allows two specialist nodes executing concurrently
    to each push their single AgentReport into the same shared channel without
    overwriting one another.
    """
    return old + new


class GraphState(TypedDict):
    """
    The shared state substrate that flows through every node in the Archon DAG.

    Fields
    ------
    assembled_context : AssembledAgentContext
        The single unified context block assembled by HybridRetrievalEngine.
        This is the ONLY data source agents may read from.

    selected_agents : List[str]
        Populated by the planner_node after routing decision.
        Valid values: "architecture", "maintainability", "technical_debt", "impact".

    routing_rationale : str
        The planner's justification for its routing choice (for observability).

    raw_specialist_reports : Annotated[List[AgentReport], _append_reports]
        Parallel write channel for specialist agents.
        The Annotated reducer merges concurrent writes from all active specialists
        into a single accumulated list without race conditions.

    final_report : Optional[AgentReport]
        Populated by synthesis_node after merging all specialist reports.
        This is the authoritative output of the entire DAG.
    """

    assembled_context: AssembledAgentContext
    selected_agents: List[str]
    routing_rationale: str
    raw_specialist_reports: Annotated[List[AgentReport], _append_reports]
    final_report: Optional[AgentReport]
