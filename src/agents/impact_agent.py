from __future__ import annotations

import json

from src.agents.llm_provider import BaseLLMProvider
from src.agents.schemas import AgentReport, Finding
from src.retrieval.assembler import ContextAssembler
from src.retrieval.schemas import AssembledAgentContext

SYSTEM_PROMPT = """You are the Impact Agent for Archon, an AI Staff Engineer platform.

Your role is to analyse repository context and evaluate the impact of changes, specifically:
- Change Impact: What logic or systems are affected by the proposed changes.
- Dependency Analysis: Downstream effects on dependent modules or services.
- Blast Radius Estimation: Interpreting the blast radius score and identifying high-risk areas.
- Risk Scoring: Assigning risk levels based on the structural impact.

You will receive a pre-assembled context block containing structural impact data (blast radius, impacted files/symbols).

You MUST respond with a single valid JSON object in this exact schema:
{
  "findings": [
    {
      "issue": "<one-sentence issue title>",
      "evidence": "<specific graph or structural evidence>",
      "reasoning": "<reasoning for the impact or risk level>",
      "impact": "<what is the potential fallout of this change>",
      "recommendation": "<specific actionable advice to mitigate risk>",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }
  ]
}

If no impact issues are found, return: {"findings": []}

Rules:
- Never hallucinate file paths or symbol names not present in the context.
- Every claim must cite evidence from the provided context block.
- Use `blast_radius_score` and `impacted_file_paths` from the context when available.
- Do not output markdown, only raw JSON.
"""


class ImpactAgent:
    """
    Analyses change impact and risk scoring based on structural repository context.
    """

    NAME = "ImpactAgent"

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def analyze(self, context: AssembledAgentContext) -> AgentReport:
        context_str = ContextAssembler.format_context_for_llm(context)

        raw_response = await self.llm.complete(
            system_prompt=SYSTEM_PROMPT,
            user_message=context_str,
        )

        findings = self._parse_findings(raw_response)

        return AgentReport(
            agent_name=self.NAME,
            tracking_token=context.tracking_token,
            findings=findings,
        )

    def _parse_findings(self, raw: str) -> list[Finding]:
        try:
            from src.agents.parsing import parse_json_from_llm
            data = parse_json_from_llm(raw)
            raw_findings = data.get("findings", [])
            findings = []
            for f in raw_findings:
                try:
                    findings.append(Finding(**f))
                except Exception:
                    # Skip malformed individual findings but continue
                    continue
            return findings
        except json.JSONDecodeError:
            # Log parse failure but never crash — return empty findings
            return []
