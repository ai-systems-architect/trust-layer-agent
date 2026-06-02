"""
HP-007 — Partial Evidence with Retry Cycle
Scenario: P2 RAG unavailable on first evidence-gathering pass.
Only IAM and CloudTrail fixtures collected (2 items per control).
Sufficiency assessment returns False for all controls.
Second pass with P2 available adds compliance requirement text,
driving sufficiency to True for all controls.

Tests evidence accumulation across retry cycles and FM-002 graceful
degradation behavior. Verifies that setdefault accumulation pattern
retains IAM + CloudTrail items from cycle 1 in cycle 2.

Pass conditions:
- evidence_retry_count == 1 (exactly one retry cycle)
- Final evidence counts include T-005 items (>2 per control)
- Sufficiency gate passes after retry
- Circuit breaker NOT fired (retry count 1 < MAX_EVIDENCE_RETRIES=3)
- Human gate PENDING
- Governance decision written
"""

from __future__ import annotations


def run() -> dict:
    """
    Execute HP-007 scenario and return grader results.
    TODO Phase 3 — implement scenario execution.
    """
    return {"scenario": "HP-007", "status": "not_implemented"}
