"""
src/agents/remediation_agent.py
────────────────────────────────
Phase 15: Remediation Specialist Agent

This agent receives a specific architectural or technical-debt violation finding
alongside the offending code snippet and produces a structured RemediationPlan
containing a verifiable code fix.

Constitutional invariants enforced here:
- Output is a strict Pydantic v2 schema — no free-form markdown text.
- The LLM must emit raw JSON only; parsing failures return None (safe default).
- The agent never writes to disk; it only proposes — the engine validates.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from src.agents.llm_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Output Schema
# ─────────────────────────────────────────────────────────────────────────────

class RemediationPlan(BaseModel):
    """
    Strict Pydantic v2 schema for LLM-generated code fixes.
    All four fields are required — partial plans are rejected.
    """
    target_symbol_id: str = Field(
        description="The stable symbol ID this fix targets (matches the knowledge graph)."
    )
    original_code_block: str = Field(
        description="The verbatim original code block being replaced."
    )
    proposed_code_block: str = Field(
        description=(
            "The proposed replacement code. Must be syntactically valid. "
            "Must be idiomatic for the file's language."
        )
    )
    explanation: str = Field(
        description="One-paragraph explanation of why this change resolves the finding."
    )


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are the Remediation Agent for Archon, an AI Staff Engineer platform.

Your role is to receive a precise architectural or technical-debt violation finding
and the offending code snippet, then produce a targeted, idiomatic code fix.

You MUST respond with a single valid JSON object matching EXACTLY this schema:
{
  "target_symbol_id": "<symbol id from the finding>",
  "original_code_block": "<exact verbatim copy of the offending code>",
  "proposed_code_block": "<your clean replacement code>",
  "explanation": "<one paragraph explaining why this fix resolves the violation>"
}

Rules:
- Do NOT output markdown, comments, or any text outside the JSON object.
- proposed_code_block must be syntactically valid Python or TypeScript (match the language).
- proposed_code_block must be a drop-in replacement for original_code_block.
- Do NOT change logic beyond what is necessary to fix the specific violation.
- Do NOT hallucinate imports, symbols, or identifiers not present in the context.
- If you cannot produce a safe fix, output: {"error": "cannot_fix", "reason": "<why>"}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────

class RemediationAgent:
    """
    Specialist LLM agent that proposes verifiable code fixes for structural violations.

    This agent only PROPOSES — it never writes to disk.
    The AutonomousRemediationEngine is responsible for Tree-sitter validation
    and final patch generation.
    """

    NAME = "RemediationAgent"

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def propose_fix(
        self,
        target_symbol_id: str,
        original_code_block: str,
        finding_context: str,
    ) -> Optional[RemediationPlan]:
        """
        Calls the LLM to generate a structured RemediationPlan.

        Parameters
        ----------
        target_symbol_id : str
            Stable graph ID of the symbol being remediated.
        original_code_block : str
            The verbatim code block that contains the violation.
        finding_context : str
            Human-readable summary of the violation finding (Issue + Evidence + Reasoning).

        Returns
        -------
        RemediationPlan | None
            A validated plan, or None if the LLM response cannot be parsed safely.
        """
        user_message = (
            f"FINDING CONTEXT:\n{finding_context}\n\n"
            f"TARGET SYMBOL ID: {target_symbol_id}\n\n"
            f"ORIGINAL CODE BLOCK:\n```\n{original_code_block}\n```\n\n"
            "Produce the remediation JSON now."
        )

        raw = await self.llm.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
        )

        return self._parse_plan(raw, target_symbol_id)

    def _parse_plan(self, raw: str, target_symbol_id: str) -> Optional[RemediationPlan]:
        try:
            data = json.loads(raw)

            # Agent signalled it cannot produce a safe fix
            if "error" in data:
                logger.warning(
                    "RemediationAgent declined to fix %s: %s",
                    target_symbol_id,
                    data.get("reason", "unknown"),
                )
                return None

            return RemediationPlan(**data)

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning(
                "RemediationAgent returned unparseable response for %s: %s",
                target_symbol_id,
                exc,
            )
            return None
