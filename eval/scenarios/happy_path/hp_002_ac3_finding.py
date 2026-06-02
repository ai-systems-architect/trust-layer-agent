"""
HP-002 — AC-3 Access Enforcement Finding
Happy path scenario: AC-3 evidence shows an unauthorized access attempt
in CloudTrail and a missing permissions boundary in the IAM policy.
Evidence is sufficient for a NON-COMPLIANT determination.

Tests that a documented compliance finding (not absence of evidence)
correctly passes the sufficiency gate and produces a draft with
NON-COMPLIANT finding and remediation recommendation.

Pass conditions (deterministic graders):
- All PEP gates passed
- Evidence lineage complete
- Sufficiency gate enforced (NON-COMPLIANT finding is sufficient)
- Circuit breaker NOT fired
- Human gate PENDING
- Governance decision written
- Zero errors
"""

from __future__ import annotations


def run() -> dict:
    """
    Execute HP-002 scenario and return grader results.
    TODO Phase 3 — implement scenario execution.
    """
    return {"scenario": "HP-002", "status": "not_implemented"}
