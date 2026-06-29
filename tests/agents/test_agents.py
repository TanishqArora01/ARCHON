import json
import pytest

from src.agents.llm_provider import BaseLLMProvider
from src.agents.schemas import AgentReport, Finding, Severity
from src.agents.architecture_agent import ArchitectureAgent
from src.agents.maintainability_agent import MaintainabilityAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.retrieval.schemas import AssembledAgentContext, StructuralContext, SemanticContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(tracking_token: str = "test-token-001") -> AssembledAgentContext:
    return AssembledAgentContext(
        tracking_token=tracking_token,
        repository_name="test_repo",
        query_text="test query",
        structural=StructuralContext(
            impacted_file_paths=["core/auth.py", "api/routes.py"],
            impacted_symbol_ids=["node-b-uuid"],
            blast_radius_score=0.5,
        ),
        semantic=SemanticContext(
            documentation_chunks=["AuthService acts as the single source of truth."],
            relevance_scores=[0.95],
            source_files=["docs/adr/ADR-002-auth.md"],
        ),
    )


class MockLLMProvider(BaseLLMProvider):
    """Returns a deterministic single finding so tests never hit the network."""

    def __init__(self, issue: str = "Duplicate auth path detected", severity: str = "HIGH"):
        self._issue = issue
        self._severity = severity

    async def complete(self, system_prompt: str, user_message: str) -> str:
        payload = {
            "findings": [
                {
                    "issue": self._issue,
                    "evidence": "api/routes.py calls core/auth.py with a blast_radius_score of 0.50",
                    "reasoning": "A parallel authentication path bypasses the canonical AuthService, "
                                 "introducing divergence risk.",
                    "impact": "Authorization inconsistencies and increased maintenance cost.",
                    "recommendation": "Consolidate authentication into AuthService and remove the "
                                      "secondary path in api/routes.py.",
                    "severity": self._severity,
                }
            ]
        }
        return json.dumps(payload)


class MalformedMockLLMProvider(BaseLLMProvider):
    """Returns invalid JSON to test graceful degradation."""

    async def complete(self, system_prompt: str, user_message: str) -> str:
        return "not json at all {{ broken"


# ---------------------------------------------------------------------------
# ArchitectureAgent tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_architecture_agent_returns_report():
    agent = ArchitectureAgent(llm_provider=MockLLMProvider())
    ctx = _make_context()
    report = await agent.analyze(ctx)

    assert isinstance(report, AgentReport)
    assert report.agent_name == "ArchitectureAgent"
    assert report.tracking_token == ctx.tracking_token
    assert len(report.findings) == 1

    finding = report.findings[0]
    assert finding.severity == Severity.HIGH
    assert "auth" in finding.issue.lower()
    assert "api/routes.py" in finding.evidence


@pytest.mark.asyncio
async def test_architecture_agent_handles_malformed_llm_response():
    agent = ArchitectureAgent(llm_provider=MalformedMockLLMProvider())
    ctx = _make_context()
    report = await agent.analyze(ctx)

    # Must never raise — graceful degradation returns empty findings
    assert report.findings == []
    assert report.tracking_token == ctx.tracking_token


# ---------------------------------------------------------------------------
# MaintainabilityAgent tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_maintainability_agent_returns_report():
    agent = MaintainabilityAgent(
        llm_provider=MockLLMProvider(
            issue="High coupling detected in AuthService", severity="MEDIUM"
        )
    )
    ctx = _make_context()
    report = await agent.analyze(ctx)

    assert report.agent_name == "MaintainabilityAgent"
    assert len(report.findings) == 1
    assert report.findings[0].severity == Severity.MEDIUM


# ---------------------------------------------------------------------------
# SynthesisAgent tests
# ---------------------------------------------------------------------------

def test_synthesis_agent_merges_and_ranks():
    synth = SynthesisAgent()

    arch_report = AgentReport(
        agent_name="ArchitectureAgent",
        tracking_token="tok-001",
        findings=[
            Finding(
                issue="Layer violation: controller calls DB directly",
                evidence="graph edge: controller.py -> db/models.py",
                reasoning="Violates declared architecture rules.",
                impact="Breaks testability and architecture boundaries.",
                recommendation="Introduce a service layer.",
                severity=Severity.HIGH,
            )
        ],
    )

    maint_report = AgentReport(
        agent_name="MaintainabilityAgent",
        tracking_token="tok-001",
        findings=[
            Finding(
                issue="High coupling in AuthService",
                evidence="blast_radius_score=0.5 across 2 files",
                reasoning="Wide blast radius indicates fragile coupling.",
                impact="Any change to AuthService risks breaking api/routes.py.",
                recommendation="Extract an interface to reduce coupling.",
                severity=Severity.MEDIUM,
            ),
            # Duplicate of the arch finding — should be deduplicated
            Finding(
                issue="Layer violation: controller calls DB directly",
                evidence="same graph edge",
                reasoning="Same architectural violation.",
                impact="Same impact.",
                recommendation="Same recommendation.",
                severity=Severity.HIGH,
            ),
        ],
    )

    final = synth.synthesize([arch_report, maint_report])

    assert final.agent_name == "SynthesisAgent"
    assert final.tracking_token == "tok-001"

    # Should deduplicate to 2 unique findings
    assert len(final.findings) == 2

    # HIGH severity must come first
    assert final.findings[0].severity == Severity.HIGH
    assert final.findings[1].severity == Severity.MEDIUM


def test_synthesis_agent_handles_empty_reports():
    synth = SynthesisAgent()
    final = synth.synthesize([])
    assert final.findings == []
    assert final.tracking_token == ""
