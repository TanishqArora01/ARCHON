from __future__ import annotations

import json

from src.agents.llm_provider import BaseLLMProvider
from src.agents.schemas import AgentReport, Finding
from src.retrieval.assembler import ContextAssembler
from src.retrieval.schemas import AssembledAgentContext

SYSTEM_PROMPT = """You are the Maintainability Agent for Archon, an AI Staff Engineer platform.

Your role is to analyse repository context and identify:
- High complexity areas (deep call chains, wide blast radius)
- Code duplication patterns (similar symbols appearing in multiple impacted files)
- Technical debt indicators (deprecated patterns, missing abstraction layers)
- Refactoring opportunities (consolidating overlapping responsibilities)

You will receive a pre-assembled context block containing structural impact data
(blast radius, impacted files/symbols) and semantic documentation (ADRs, READMEs, design docs).

You MUST respond with a single valid JSON object in this exact schema:
{
  "findings": [
    {
      "issue": "<one-sentence issue title>",
      "evidence": "<specific graph or documentation evidence>",
      "reasoning": "<maintainability reasoning for why this is a problem>",
      "impact": "<long-term maintenance cost or risk>",
      "recommendation": "<specific actionable refactoring suggestion>",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }
  ]
}

If no maintainability issues are found, return: {"findings": []}

Rules:
- Never hallucinate file paths or symbol names not present in the context.
- Blast radius score above 0.3 is a strong signal of high-risk coupling.
- Every claim must cite evidence from the provided context block.
- Do not output markdown, only raw JSON.
"""


class MaintainabilityAgent:
    """
    Analyses assembled repository context for maintainability issues and technical debt.
    Implements the Maintainability Agent role from agents.md.
    """

    NAME = "MaintainabilityAgent"

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
            data = json.loads(raw)
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
