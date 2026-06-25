"""
tests/remediation/test_remediation.py
───────────────────────────────────────
Integration tests for Phase 15: Autonomous Remediation & Verifiable Patch Generation.

Test coverage:
  1. Valid proposed code  →  AST gate passes  →  unified diff is produced.
  2. Broken proposed code →  AST gate blocks  →  None returned on every attempt.
  3. Agent returning None →  engine handles gracefully, returns None.
  4. parse_code_string    →  unit tests for the Tree-sitter invariant gate directly.
  5. generate_unified_diff→  unit tests for the deterministic patch generator.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.remediation_agent import RemediationPlan
from src.agents.schemas import Finding, Severity
from src.environment.parser.engine import ParserEngine
from src.remediation.engine import AutonomousRemediationEngine
from src.remediation.patches import generate_unified_diff


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def parser():
    return ParserEngine()


@pytest.fixture()
def sample_finding() -> Finding:
    return Finding(
        issue="Direct database access in Controller layer violates architecture boundary",
        evidence="ConcreteController.handle_request calls db.query() directly",
        reasoning="Controllers must delegate to Service layer; direct DB access couples layers",
        impact="High coupling increases blast radius; changes to schema break controller logic",
        recommendation="Extract database call into a dedicated Repository/Service method",
        severity=Severity.HIGH,
    )


VALID_FIX = """\
class ConcreteController(BaseController):
    def handle_request(self, payload: dict) -> bool:
        if not self._validate(payload):
            return False
        return True

    def _validate(self, payload: dict) -> bool:
        return "id" in payload
"""

# double-def is reliably flagged as ERROR by Tree-sitter's Python grammar
BROKEN_FIX = "def def handle_request(self, payload):\n    return True\n"


# ─────────────────────────────────────────────────────────────────────────────
# 1.  parse_code_string unit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_code_string_valid_python(parser: ParserEngine):
    result = parser.parse_code_string(VALID_FIX, language="python")
    assert result.is_valid is True
    assert result.error_nodes == []


def test_parse_code_string_broken_python(parser: ParserEngine):
    result = parser.parse_code_string(BROKEN_FIX, language="python")
    assert result.is_valid is False
    assert len(result.error_nodes) > 0
    # At least one node should be classified as ERROR
    assert any("ERROR" in n or "MISSING" in n for n in result.error_nodes)


def test_parse_code_string_unsupported_language(parser: ParserEngine):
    result = parser.parse_code_string("fn main() {}", language="rust")
    assert result.is_valid is False
    assert any("UNSUPPORTED_LANGUAGE" in n for n in result.error_nodes)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  generate_unified_diff unit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_unified_diff_produces_diff():
    original = "def foo():\n    return 1\n"
    proposed = "def foo():\n    return 42\n"
    diff = generate_unified_diff(original, proposed, file_path="src/foo.py")
    assert diff.strip() != ""
    assert "--- a/src/foo.py" in diff
    assert "+++ b/src/foo.py" in diff
    assert "-    return 1" in diff
    assert "+    return 42" in diff


def test_generate_unified_diff_identical_code_returns_empty():
    code = "def foo():\n    return 1\n"
    diff = generate_unified_diff(code, code, file_path="src/foo.py")
    assert diff.strip() == ""


# ─────────────────────────────────────────────────────────────────────────────
# 3.  AutonomousRemediationEngine — valid fix path
# ─────────────────────────────────────────────────────────────────────────────

ORIGINAL_CODE = """\
class ConcreteController(BaseController):
    def handle_request(self, payload: dict) -> bool:
        def validate(p: dict) -> bool:
            return "id" in p
        if validate(payload):
            return True
        return False
"""

@pytest.mark.asyncio
async def test_engine_valid_fix_produces_diff(parser: ParserEngine, sample_finding: Finding):
    """
    When the agent returns syntactically valid Python, the engine must:
      - pass the AST gate
      - return a non-empty unified diff string
    """
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="unused")  # agent is mocked directly

    engine = AutonomousRemediationEngine(llm_provider=mock_llm)

    # Mock the internal agent to return a valid plan
    valid_plan = RemediationPlan(
        target_symbol_id="snap::core.py::ConcreteController",
        original_code_block=ORIGINAL_CODE,
        proposed_code_block=VALID_FIX,
        explanation="Extracted nested validate() to a proper private method.",
    )
    engine._agent.propose_fix = AsyncMock(return_value=valid_plan)  # type: ignore[method-assign]

    diff = await engine.generate_verifiable_fix(
        parser_engine=parser,
        finding=sample_finding,
        original_context=ORIGINAL_CODE,
        target_symbol_id="snap::core.py::ConcreteController",
        language="python",
        file_path="tests/fixtures/control_repo/py_repo/core.py",
    )

    assert diff is not None
    assert diff.strip() != ""
    assert "--- a/tests/fixtures/control_repo/py_repo/core.py" in diff
    assert "+++ b/tests/fixtures/control_repo/py_repo/core.py" in diff


# ─────────────────────────────────────────────────────────────────────────────
# 4.  AutonomousRemediationEngine — broken fix path (invariant gate blocks)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_broken_fix_is_blocked(parser: ParserEngine, sample_finding: Finding):
    """
    When the agent returns syntactically invalid Python on every attempt,
    the engine must return None and never produce a diff.
    """
    mock_llm = MagicMock()
    engine = AutonomousRemediationEngine(llm_provider=mock_llm)

    broken_plan = RemediationPlan(
        target_symbol_id="snap::core.py::ConcreteController",
        original_code_block=ORIGINAL_CODE,
        proposed_code_block=BROKEN_FIX,
        explanation="Attempt with a syntax error — should be rejected.",
    )
    engine._agent.propose_fix = AsyncMock(return_value=broken_plan)  # type: ignore[method-assign]

    diff = await engine.generate_verifiable_fix(
        parser_engine=parser,
        finding=sample_finding,
        original_context=ORIGINAL_CODE,
        target_symbol_id="snap::core.py::ConcreteController",
        language="python",
        file_path="tests/fixtures/control_repo/py_repo/core.py",
    )

    # Constitutional invariant: broken AST → None, zero patches published
    assert diff is None
    # The agent should have been called _MAX_RETRIES times
    assert engine._agent.propose_fix.call_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# 5.  AutonomousRemediationEngine — agent declines (returns None)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_handles_agent_returning_none(parser: ParserEngine, sample_finding: Finding):
    """
    When the agent consistently returns None (e.g. it cannot safely fix the issue),
    the engine must return None without raising exceptions.
    """
    mock_llm = MagicMock()
    engine = AutonomousRemediationEngine(llm_provider=mock_llm)
    engine._agent.propose_fix = AsyncMock(return_value=None)  # type: ignore[method-assign]

    diff = await engine.generate_verifiable_fix(
        parser_engine=parser,
        finding=sample_finding,
        original_context=ORIGINAL_CODE,
        target_symbol_id="snap::core.py::ConcreteController",
        language="python",
    )

    assert diff is None


# ─────────────────────────────────────────────────────────────────────────────
# 6.  should_remediate severity filter
# ─────────────────────────────────────────────────────────────────────────────

def test_should_remediate_high_severity():
    f = Finding(
        issue="x", evidence="x", reasoning="x", impact="x",
        recommendation="x", severity=Severity.HIGH,
    )
    assert AutonomousRemediationEngine.should_remediate(f) is True


def test_should_remediate_medium_severity():
    f = Finding(
        issue="x", evidence="x", reasoning="x", impact="x",
        recommendation="x", severity=Severity.MEDIUM,
    )
    assert AutonomousRemediationEngine.should_remediate(f) is True


def test_should_not_remediate_low_severity():
    f = Finding(
        issue="x", evidence="x", reasoning="x", impact="x",
        recommendation="x", severity=Severity.LOW,
    )
    assert AutonomousRemediationEngine.should_remediate(f) is False
