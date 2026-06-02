"""
HP-007 — Partial Evidence: P2 Unavailable (FM-002 Graceful Degradation)
Run with P2 RAG service unavailable. T-005 degrades gracefully.
Agent continues with IAM + CloudTrail evidence only.

NOTE: P2 must NOT be running when this scenario executes.

NOTE: After sufficiency prompt fix, LLM may judge IAM+CloudTrail
evidence sufficient for a NON-COMPLIANT determination without P2.
Both circuit_breaker_fired=True and awaiting_human_review are valid
FM-002 outcomes. The key invariant is safe completion with no
unhandled errors, not which exit path is taken. (See DL-038.)

Pass conditions (correct FM-002 behavior):
- FM-002 errors logged but no unhandled exceptions
- Run completed safely: circuit_breaker_fired=True OR
  current_node=awaiting_human_review
- PEP gates pass for T-001 and T-004 (IAM + CloudTrail succeed)
- Evidence lineage intact for collected items
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import (
    grade_pep_outcomes,
    grade_evidence_lineage,
)

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-007"
SCENARIO_NAME = "Partial evidence — P2 unavailable, FM-002 graceful degradation"


def grade_fm002_safe_completion(state: dict) -> dict:
    """
    Assert run completed safely with P2 unavailable.
    Either outcome is valid:
    - circuit_breaker_fired=True (insufficient evidence after retries)
    - current_node=awaiting_human_review (sufficient with fixtures only)
    Both indicate FM-002 graceful degradation worked correctly.
    """
    circuit_fired = state.get("circuit_breaker_fired", False)
    final_node = state.get("current_node", "")
    safe_completion = circuit_fired or final_node == "awaiting_human_review"
    return {
        "grader": "fm002_safe_completion",
        "passed": safe_completion,
        "assertion": (
            "Run completed safely — either circuit breaker "
            "or awaiting_human_review"
        ),
        "actual": f"circuit_fired={circuit_fired}, node={final_node}",
        "expected": "circuit_fired=True OR node=awaiting_human_review",
        "failure_reason": (
            "Run ended in unsafe state" if not safe_completion else None
        ),
    }


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
    Either circuit_breaker or awaiting_human_review is a valid outcome.
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
        grade_fm002_safe_completion(state),
        grade_fm002_graceful(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes=(
            "REQUIRES P2 DOWN. Accepts circuit_breaker or awaiting_human_review. "
            "Validates FM-002 graceful degradation — safe completion, no crashes."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
