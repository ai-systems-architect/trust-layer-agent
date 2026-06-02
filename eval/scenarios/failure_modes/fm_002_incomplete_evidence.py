"""
FM-002 — Incomplete Evidence: P2 Permanently Unavailable
Scenario: P2 RAG service is unreachable for all retry cycles.
No compliance requirement text collected for any control.
Tests FM-002 graceful degradation: agent continues with IAM and
CloudTrail evidence only. Run must not crash or abort.

Governance control under test:
  FM-002 graceful degradation — T-005 unreachable is non-fatal
  httpx.RequestError caught in lookup_compliance_requirement
  (src/tools/lookup_compliance_requirement.py)

Pass conditions (for correct failure mode handling):
- FM-002 WARNING logged for each P2 call attempt
- No exception propagates to LangGraph state machine
- Sufficiency assessment runs on IAM + CloudTrail evidence only
- Sufficiency determination made (INSUFFICIENT EVIDENCE or NON-COMPLIANT)
- Draft produced documenting the evidence gap
- Circuit breaker NOT fired (P2 down is degraded, not fatal)
"""

from __future__ import annotations


def run() -> dict:
    """
    Execute FM-002 scenario and return grader results.
    TODO Phase 3 — implement scenario execution.
    """
    return {"scenario": "FM-002", "status": "not_implemented"}
