from __future__ import annotations

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Finding(BaseModel):
    """
    A single structured engineering finding.
    Every finding must include all five fields per the agents.md Review Output Standard.
    """
    issue: str
    evidence: str
    reasoning: str
    impact: str
    recommendation: str
    severity: Severity = Severity.MEDIUM


class AgentReport(BaseModel):
    """
    The full output of a specialist agent run, containing zero or more findings.
    The tracking_token links this report back to the AssembledAgentContext it consumed.
    """
    agent_name: str
    tracking_token: str
    findings: List[Finding] = Field(default_factory=list)
