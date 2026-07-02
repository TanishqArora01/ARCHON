"""
src/api/agents.py
─────────────────
Agents API — expose multi-agent system status and model assignments.

Endpoints:
  GET  /api/v1/agents            — list all agents with their NVIDIA NIM model assignments
  GET  /api/v1/agents/health     — check which providers are reachable
  POST /api/v1/agents/run        — trigger a targeted agent analysis run
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from src.api.security import require_api_token
from src.core.config import settings
from src.db.models import Repository
from src.db.session import AsyncSessionLocal
from src.services.analysis_jobs import enqueue_repository_analysis, run_inline_analysis
from src.services.repositories import get_or_create_default_tenant

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["agents"],
    dependencies=[Depends(require_api_token)],
)

NVIDIA_REASONING_URL = "https://build.nvidia.com/explore/reasoning"
VALID_SPECIALIST_AGENTS = frozenset({"architecture", "maintainability", "technical_debt", "impact"})


# ─── Schemas ────────────────────────────────────────────────────────────────

class AgentInfo(BaseModel):
    name: str
    label: str
    role: str
    provider: str
    model: str
    model_url: str | None = None
    status: str = "ready"


class AgentHealthResponse(BaseModel):
    nvidia_configured: bool
    nvidia_reachable: bool
    ollama_reachable: bool
    active_provider: str
    agents: list[AgentInfo]


class AgentRunRequest(BaseModel):
    repository_id: str
    agents: list[str] | None = None  # None = planner selects specialists


class AgentRunResponse(BaseModel):
    status: str
    message: str
    repository_id: str
    job_id: str
    analysis_run_id: str | None = None


# ─── Agent definitions ──────────────────────────────────────────────────────

def _get_agent_definitions() -> list[AgentInfo]:
    """Build the list of all agents with their current model assignments."""
    provider = settings.LLM_PROVIDER.lower()
    nvidia_configured = bool(settings.NVIDIA_API_KEY)

    agents = [
        AgentInfo(
            name="planner",
            label="Planner Agent",
            role="Evaluates repository context and routes tasks to specialist agents",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_PLANNER_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                NVIDIA_REASONING_URL
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="architecture",
            label="Architecture Agent",
            role="Detects layer violations, boundary issues, and architecture drift",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_ARCHITECTURE_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                NVIDIA_REASONING_URL
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="maintainability",
            label="Maintainability Agent",
            role="Detects coupling, complexity, and refactoring opportunities",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_MAINTAINABILITY_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                NVIDIA_REASONING_URL
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="technical_debt",
            label="Technical Debt Agent",
            role="Forecasts structural drag and compounding costs for choke points",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_DEBT_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                NVIDIA_REASONING_URL
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="impact",
            label="Impact Agent",
            role="Evaluates change impact, blast radius, and risk scoring",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_IMPACT_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                NVIDIA_REASONING_URL
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="synthesis",
            label="Synthesis Agent",
            role="Deterministic convergence — aggregates all specialist findings into final report",
            provider="deterministic",
            model="no-llm-required",
            model_url=None,
        ),
    ]
    return agents


async def _check_nvidia_reachable() -> bool:
    if not settings.NVIDIA_API_KEY:
        return False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"{settings.NVIDIA_BASE_URL.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
            )
            return resp.status_code == 200
    except Exception:
        return False


def _validate_selected_agents(agents: list[str] | None) -> list[str] | None:
    if agents is None:
        return None

    selected = [agent for agent in agents if agent in VALID_SPECIALIST_AGENTS]
    if not selected:
        raise HTTPException(
            status_code=400,
            detail=(
                "No valid specialist agents requested. "
                f"Valid values: {', '.join(sorted(VALID_SPECIALIST_AGENTS))}"
            ),
        )
    return selected


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """
    List all Archon agents with their current LLM model assignments.

    When LLM_PROVIDER=nvidia, each agent is assigned a specialized NVIDIA NIM
    model from build.nvidia.com optimized for its task.
    """
    return _get_agent_definitions()


@router.get("/health", response_model=AgentHealthResponse)
async def check_agent_health() -> AgentHealthResponse:
    """
    Check the health of all agent providers.
    Tests NVIDIA NIM API reachability and Ollama local runtime.
    """
    nvidia_configured = bool(settings.NVIDIA_API_KEY)
    nvidia_reachable = await _check_nvidia_reachable()
    ollama_reachable = False

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            ollama_reachable = resp.status_code == 200
    except Exception:
        ollama_reachable = False

    active_provider = settings.LLM_PROVIDER
    agents = _get_agent_definitions()

    for agent in agents:
        if agent.provider == "nvidia":
            if not nvidia_configured:
                agent.status = "unconfigured"
            elif not nvidia_reachable:
                agent.status = "unreachable"
            else:
                agent.status = "ready"
        elif agent.provider == "ollama":
            agent.status = "ready" if ollama_reachable else "unreachable"
        elif agent.provider == "mock":
            agent.status = "ready"
        elif agent.provider == "deterministic":
            agent.status = "ready"
        else:
            agent.status = "unknown"

    return AgentHealthResponse(
        nvidia_configured=nvidia_configured,
        nvidia_reachable=nvidia_reachable,
        ollama_reachable=ollama_reachable,
        active_provider=active_provider,
        agents=agents,
    )


@router.post("/run", response_model=AgentRunResponse)
async def run_agents(payload: AgentRunRequest, background_tasks: BackgroundTasks) -> AgentRunResponse:
    """
    Trigger a targeted agent analysis run on a specific repository.

    This enqueues a fresh analysis job using the currently configured LLM provider.
    When `agents` is omitted, the planner selects specialists. When provided,
    only the listed specialist agents run.
    """
    selected_agents = _validate_selected_agents(payload.agents)
    event_metadata_extra: dict | None = None
    if selected_agents is not None:
        event_metadata_extra = {"selected_agents": selected_agents}

    async with AsyncSessionLocal() as session:
        repo = await session.get(Repository, payload.repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        tenant = await get_or_create_default_tenant(session)
        job_id, task_payload, queued = await enqueue_repository_analysis(
            session,
            repo,
            tenant_id=tenant.id,
            event_type="agent_run",
            event_metadata_extra=event_metadata_extra,
        )
        await session.commit()

    if not queued:
        background_tasks.add_task(run_inline_analysis, task_payload)

    agents_note = ""
    if selected_agents:
        agents_note = f" Specialists: {', '.join(selected_agents)}."

    return AgentRunResponse(
        status="queued",
        message=(
            f"Agent analysis queued for repository '{repo.name}'. "
            f"Using provider: {settings.LLM_PROVIDER}.{agents_note}"
        ),
        repository_id=payload.repository_id,
        job_id=job_id,
        analysis_run_id=None,
    )
