"""
src/remediation/engine.py
──────────────────────────
Phase 15: Autonomous Remediation Engine

Orchestrates the full self-healing loop:
  1. Ask RemediationAgent to propose a fix  →  RemediationPlan
  2. Feed proposed_code_block into ParserEngine.parse_code_string()  (invariant gate)
  3. If AST is clean  →  generate a unified diff via patches.generate_unified_diff()
  4. If AST has ERROR/MISSING nodes  →  attempt one retry, then return None

Constitutional invariants enforced:
- No code patch may leave this engine without passing the Tree-sitter gate.
- If two consecutive LLM attempts produce broken ASTs, the patch is suppressed entirely.
- LLMs never bypass the graph layer (this engine only calls them via RemediationAgent).
"""
from __future__ import annotations

import logging
from typing import Optional

from src.agents.llm_provider import BaseLLMProvider
from src.agents.remediation_agent import RemediationAgent, RemediationPlan
from src.agents.schemas import Finding, Severity
from src.environment.parser.engine import ParserEngine
from src.remediation.patches import generate_unified_diff

logger = logging.getLogger(__name__)

# Severity levels that trigger autonomous remediation
_REMEDIABLE_SEVERITIES = {Severity.HIGH, Severity.MEDIUM}

# Maximum LLM retry attempts before the patch is suppressed
_MAX_RETRIES = 2


class AutonomousRemediationEngine:
    """
    Coordinates RemediationAgent proposals with Tree-sitter AST validation.

    Usage
    -----
    engine = AutonomousRemediationEngine(llm_provider=OllamaLLMProvider())
    patch_diff = await engine.generate_verifiable_fix(
        parser_engine=parser,
        finding=finding,
        original_context="def handle_request(self, payload):\n    ...",
        target_symbol_id="snap::src/services/auth.py::handle_request",
        language="python",
        file_path="src/services/auth.py",
    )
    """

    def __init__(self, llm_provider: BaseLLMProvider):
        self._agent = RemediationAgent(llm_provider=llm_provider)

    async def generate_verifiable_fix(
        self,
        parser_engine: ParserEngine,
        finding: Finding,
        original_context: str,
        target_symbol_id: str,
        language: str = "python",
        file_path: str = "target_file.py",
    ) -> Optional[str]:
        """
        Attempt to produce a Tree-sitter–validated unified diff for ``finding``.

        Returns
        -------
        str | None
            A unified diff string if the fix passes the AST invariant gate,
            or ``None`` if every attempt produced syntactically invalid code.
        """
        # Build a concise finding context string for the LLM
        finding_context = (
            f"Issue: {finding.issue}\n"
            f"Evidence: {finding.evidence}\n"
            f"Reasoning: {finding.reasoning}\n"
            f"Impact: {finding.impact}\n"
            f"Recommendation: {finding.recommendation}"
        )

        for attempt in range(1, _MAX_RETRIES + 1):
            logger.info(
                "RemediationEngine: attempt %d/%d for symbol %s",
                attempt, _MAX_RETRIES, target_symbol_id,
            )

            # ── Step 1: Ask RemediationAgent for a proposal ───────────────────
            plan: Optional[RemediationPlan] = await self._agent.propose_fix(
                target_symbol_id=target_symbol_id,
                original_code_block=original_context,
                finding_context=finding_context,
            )

            if plan is None:
                logger.warning(
                    "RemediationAgent returned no plan on attempt %d — skipping.", attempt
                )
                continue

            # ── Step 2: Tree-sitter invariant gate ───────────────────────────
            validation = parser_engine.parse_code_string(
                code=plan.proposed_code_block,
                language=language,
            )

            if validation.is_valid:
                logger.info(
                    "AST gate PASSED for %s (attempt %d). Generating diff.",
                    target_symbol_id, attempt,
                )
                # ── Step 3: Generate unified diff ────────────────────────────
                diff = generate_unified_diff(
                    original_code=plan.original_code_block,
                    proposed_code=plan.proposed_code_block,
                    file_path=file_path,
                )
                return diff if diff.strip() else None  # empty diff = no change

            else:
                logger.warning(
                    "AST gate FAILED for %s (attempt %d). Error nodes: %s",
                    target_symbol_id,
                    attempt,
                    validation.error_nodes,
                )

        # All retries exhausted — suppress the patch
        logger.error(
            "All %d remediation attempts produced invalid ASTs for %s. Patch suppressed.",
            _MAX_RETRIES, target_symbol_id,
        )
        return None

    @staticmethod
    def should_remediate(finding: Finding) -> bool:
        """
        Returns True if the finding severity warrants autonomous remediation.
        Only HIGH and MEDIUM findings are routed into the engine.
        LOW findings receive recommendations only — no automated patch.
        """
        return finding.severity in _REMEDIABLE_SEVERITIES
