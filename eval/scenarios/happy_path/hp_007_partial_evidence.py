"""
HP-007 — Partial Evidence: P2 Unavailable (FM-002 Graceful Degradation)
Run with P2 RAG service unavailable. T-005 degrades gracefully.
Agent continues with IAM + CloudTrail evidence only but cannot
reach sufficient=True for all controls — circuit breaker fires at
MAX_EVIDENCE_RETRIES.

NOTE: P2 must NOT be running when this scenario executes.
This is an intentional circuit-breaker scenario, not a crash.

Pass conditions (correct FM-002 behavior):
- FM-002 errors logged but no unhandled exceptions
- Circuit breaker fires at MAX_EVIDENCE_RETRIES (expected_fired=True)
- circuit_breaker_reason contains "MAX_EVIDENCE_RETRIES"
- PEP gates pass for T-001 and T-004 (IAM + CloudTrail succeed)
- Evidence lineage intact for collected items
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import (
    grade_pep_outcomes,
    grade_evidence_lineage,
    grade_circuit_breaker,
)

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-007"
SCENARIO_NAME = "Partial evidence — P2 unavailable, FM-002 graceful degradation"


def grade_fm002_graceful(state: dict) -> dict:
    """
    Assert T-005 failures are FM-002 type (P2 unreachable),
    not unhandled exceptions propagated to graph state.
    """
    errors = state.get("errors", [])
    fm002_keywords = ["P2 unreachable", "FM-002", "Connection refused", "HTTP 500"]
    fm002_errors = [
        e for e in errors
        if any(kw in e for kw in fm002_keywords)
    ]
    unhandled = [e for e in errors if e not in fm002_errors]
    passed = len(unhandled) == 0
    return {
        "grader": "fm002_graceful_degradation",
        "passed": passed,
        "assertion": "T-005 failures are FM-002 type, no unhandled errors",
        "actual": (
            f"fm002_errors={len(fm002_errors)}, unhandled={len(unhandled)}"
        ),
        "expected": "unhandled=0",
        "failure_reason": (
            f"Unhandled errors: {unhandled[:2]}" if not passed else None
        ),
    }


def run() -> dict:
    """
    Execute HP-007. P2 must NOT be running.
    Circuit breaker expected to fire at MAX_EVIDENCE_RETRIES.
    """
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)
    logger.warning(
        "%s — NOTE: P2 must NOT be running for this scenario", SCENARIO_ID
    )

    state, run_id = run_agent(
        controls=["AC-2", "AC-3", "AC-6", "AC-17"],
    )

    grader_results = [
        grade_pep_outcomes(state),
        grade_evidence_lineage(state),
        grade_circuit_breaker(state, expected_fired=True),
        grade_fm002_graceful(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes=(
            "REQUIRES P2 DOWN. Circuit breaker expected to fire. "
            "Validates FM-002 graceful degradation behavior."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
