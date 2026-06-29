from __future__ import annotations

import json
from typing import List

from src.agents.llm_provider import BaseLLMProvider
from src.agents.schemas import AgentReport, Finding
from src.retrieval.assembler import ContextAssembler
from src.retrieval.schemas import AssembledAgentContext

SYSTEM_PROMPT = """You are the Technical Debt Agent for Archon, an AI Staff Engineer platform.

Your role is to analyse repository context and forecast technical debt by identifying:
- Structural Choke Points where high complexity intersects with extreme coupling.
- The compounding cost of maintaining these choke points.
- High-risk nodes that will induce structural drag over time if not refactored.

You will receive a pre-assembled context block containing structural impact data,
specifically identifying the top Structural Choke Points and their Technical Debt Index (TDI).

You MUST respond with a single valid JSON object in this exact schema:
{
  "findings": [
    {
      "issue": "<one-sentence issue title>",
      "evidence": "<specific structural metrics or TDI evidence>",
      "reasoning": "<explanation of how this choke point creates structural drag>",
      "impact": "<forecast of maintenance cost and scaling risk over time>",
      "recommendation": "<specific actionable architectural refactoring suggestion>",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }
  ]
}

If no significant technical debt issues or choke points are found, return: {"findings": []}

Rules:
- Never hallucinate file paths or symbol names not present in the context.
- Focus specifically on the listed Structural Choke Points and their centrality/blast radius.
- Every claim must cite evidence from the provided context block.
- Do not output markdown, only raw JSON.
"""


class TechnicalDebtAgent:
    """
    Analyses assembled repository context for technical debt forecasting.
    Implements the Technical Debt Agent role for Phase 11.
    """

    NAME = "TechnicalDebtAgent"

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

    def _parse_findings(self, raw: str) -> List[Finding]:
        try:
            from src.agents.parsing import parse_json_from_llm
            data = parse_json_from_llm(raw)
            raw_findings = data.get("findings", [])
            findings = []
            for f in raw_findings:
                try:
                    findings.append(Finding(**f))
                except Exception:
                    continue
            return findings
        except json.JSONDecodeError:
            return []
