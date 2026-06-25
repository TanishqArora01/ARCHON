from __future__ import annotations

from src.agents.schemas import AgentReport, Finding, Severity


class SynthesisAgent:
    """
    Merges findings from all specialist agents into a single deduplicated, ranked report.
    Implements the Synthesis Agent role from agents.md.

    The Synthesis Agent does NOT call an LLM. Its logic is deterministic:
    - Collect all findings from specialist reports
    - Deduplicate findings with identical issue text
    - Sort by severity: HIGH > MEDIUM > LOW
    """

    NAME = "SynthesisAgent"

    _SEVERITY_ORDER = {
        Severity.HIGH: 0,
        Severity.MEDIUM: 1,
        Severity.LOW: 2,
    }

    def synthesize(self, reports: list[AgentReport]) -> AgentReport:
        """
        Accepts a list of specialist AgentReports and returns a merged, ranked final report.
        The tracking_token is taken from the first report in the list.
        """
        if not reports:
            return AgentReport(
                agent_name=self.NAME,
                tracking_token="",
                findings=[],
            )

        tracking_token = reports[0].tracking_token

        # Collect all findings, deduplicating by issue text
        seen_issues: set[str] = set()
        merged: list[Finding] = []

        for report in reports:
            for finding in report.findings:
                normalized = finding.issue.strip().lower()
                if normalized not in seen_issues:
                    seen_issues.add(normalized)
                    merged.append(finding)

        # Sort by severity: HIGH first
        merged.sort(key=lambda f: self._SEVERITY_ORDER[f.severity])

        return AgentReport(
            agent_name=self.NAME,
            tracking_token=tracking_token,
            findings=merged,
        )
