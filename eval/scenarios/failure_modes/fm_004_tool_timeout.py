"""
FM-004 — Tool Timeout: T-005 httpx.ReadTimeout Handled Gracefully
Scenario: mock lookup_compliance_requirement to raise httpx.ReadTimeout
(simulating P2 exceeding the configured timeout_seconds). Tests that
tool-level timeouts are caught as FM-002 degradation without crashing
the agent or propagating exceptions to the LangGraph state machine.

Governance control under test:
  FM-002 graceful degradation — httpx.ReadTimeout caught in T-005
  Timeout logged as WARNING; evidence gap surfaced in sufficiency_results
  (src/tools/lookup_compliance_requirement.py)

Pass conditions (for correct failure mode handling):
- T-005 timeout logged as WARNING (not ERROR, not uncaught exception)
- No exception propagates to graph.py or LangGraph
- sufficiency_results[control].missing_fields contains compliance gap
- Run continues with IAM + CloudTrail evidence from T-001 and T-004
- Circuit breaker NOT fired (timeout is degraded, not fatal)
- errors list may contain timeout record (non-fatal documentation)
"""

from __future__ import annotations


def run() -> dict:
    """
    Execute FM-004 scenario and return grader results.
    TODO Phase 3 — implement scenario execution.
    """
    return {"scenario": "FM-004", "status": "not_implemented"}
