"""
src/remediation/patches.py
──────────────────────────
Converts raw code string pairs into a standard unified diff format.
Deterministic — no LLM involvement.
"""
from __future__ import annotations

import difflib


def generate_unified_diff(
    original_code: str,
    proposed_code: str,
    file_path: str = "target_file",
    context_lines: int = 3,
) -> str:
    """
    Produces a standard unified diff string between two code blocks.

    Parameters
    ----------
    original_code : str
        The original source code snippet.
    proposed_code : str
        The LLM-proposed replacement snippet (already AST-validated).
    file_path : str
        Label used for the diff header (e.g. 'src/services/auth.py').
    context_lines : int
        Number of unchanged context lines to include around each hunk.

    Returns
    -------
    str
        A unified diff string, empty if there are no differences.
    """
    original_lines = original_code.splitlines(keepends=True)
    proposed_lines = proposed_code.splitlines(keepends=True)

    # Ensure trailing newline for clean diffs
    if original_lines and not original_lines[-1].endswith("\n"):
        original_lines[-1] += "\n"
    if proposed_lines and not proposed_lines[-1].endswith("\n"):
        proposed_lines[-1] += "\n"

    diff = list(
        difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=context_lines,
        )
    )

    return "".join(diff)
