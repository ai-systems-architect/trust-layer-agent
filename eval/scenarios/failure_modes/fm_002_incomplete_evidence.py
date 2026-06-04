"""
FM-002 — Incomplete Evidence Collection
P2 unavailable. T-005 degrades gracefully. Agent cannot collect
compliance requirement text. Circuit breaker fires at MAX_EVIDENCE_RETRIES.

Test approach: State injection.
Inject a state with circuit_breaker_fired=True and FM-002 errors.
Verify graders correctly identify this as FM-002 behavior.

Pass conditions:
- circuit_breaker_fired=True
- FM-002 errors present and non-fatal
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import make_base_state, format_result
from eval.graders.deterministic import grade_circuit_breaker

logger = logging.getLogger(__name__)
SCENARIO_ID = "FM-002"
SCENARIO_NAME = "Incomplete evidence — P2 unavailable, circuit breaker fires"


def grade_fm002_errors_present(state: dict) -> dict:
    """Assert FM-002 errors are present and non-fatal."""
    errors = state.get("errors", [])
    fm002_present = any(
        "FM-002" in e or "P2 unreachable" in e or "Connection refused" in e
        for e in errors
    )
    return {
        "grader": "fm002_errors_present",
        "passed": fm002_present,
        "assertion": "FM-002 errors present in state",
        "actual": f"errors={errors[:2]}",
        "expected": "At least one FM-002 error",
        "failure_reason": (
            "No FM-002 errors found" if not fm002_present else None
        ),
    }


def run() -> dict:
    """Inject FM-002 state and verify graders catch it."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state = make_base_state(controls=["AC-2", "AC-3", "AC-6", "AC-17"])

    # Inject FM-002 state
    state["circuit_breaker_fired"] = True
    state["circuit_breaker_reason"] = "MAX_EVIDENCE_RETRIES=3 exceeded"
    state["current_node"] = "circuit_breaker"
    state["errors"] = [
        (
            "lookup_compliance_requirement: P2 unreachable "
            "for control AC-2 — [Errno 61] Connection refused "
            "(FM-002: degraded, not fatal)"
        ),
        (
            "lookup_compliance_requirement: P2 unreachable "
            "for control AC-17 — [Errno 61] Connection refused "
            "(FM-002: degraded, not fatal)"
        ),
    ]
    state["sufficiency_results"]["AC-17"]["sufficient"] = False
    state["sufficiency_results"]["AC-17"]["missing_fields"] = [
        "compliance_requirement_text"
    ]

    grader_results = [
        grade_circuit_breaker(state, expected_fired=True),
        grade_fm002_errors_present(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=state["run_id"],
        notes=(
            "State injection. FM-002 errors and circuit breaker injected. "
            "For live FM-002 behavior see HP-007."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
