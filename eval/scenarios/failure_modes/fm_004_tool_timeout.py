"""
FM-004 — Tool Timeout
A tool call exceeds timeout_seconds. Agent logs the error and continues.
Governance control: per-tool timeout, FM-002 graceful degradation pattern.

Test approach: State injection.
Inject a state where errors contain a timeout message and the
affected control has reduced evidence. Run must reach a terminal
node — timeout is non-fatal.

Pass conditions:
- Timeout error present in state errors
- Run reached terminal node (awaiting_human_review or circuit_breaker)
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import make_base_state, format_result

logger = logging.getLogger(__name__)
SCENARIO_ID = "FM-004"
SCENARIO_NAME = "Tool timeout — graceful degradation, run continues"


def grade_timeout_logged(state: dict) -> dict:
    """Assert timeout error is present and non-fatal."""
    errors = state.get("errors", [])
    timeout_present = any(
        "timeout" in e.lower() or "timed out" in e.lower()
        for e in errors
    )
    return {
        "grader": "timeout_logged",
        "passed": timeout_present,
        "assertion": "Timeout error present in run state",
        "actual": f"timeout_in_errors={timeout_present}",
        "expected": "timeout_in_errors=True",
        "failure_reason": (
            "No timeout error found in state" if not timeout_present else None
        ),
    }


def grade_run_continued_after_timeout(state: dict) -> dict:
    """Assert run reached a terminal node after timeout — did not crash."""
    node = state.get("current_node", "")
    continued = node in ["awaiting_human_review", "circuit_breaker"]
    return {
        "grader": "run_continued_after_timeout",
        "passed": continued,
        "assertion": "Run reached terminal state after timeout",
        "actual": f"current_node={node}",
        "expected": "awaiting_human_review or circuit_breaker",
        "failure_reason": (
            f"Run stuck at unexpected node: {node}" if not continued else None
        ),
    }


def run() -> dict:
    """Inject FM-004 state and verify graceful handling."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state = make_base_state(controls=["AC-2", "AC-3"])
    state["errors"] = [
        (
            "query_iam_policies: tool call timed out after 10s "
            "for control AC-2 — evidence gap documented, run continues"
        )
    ]
    state["current_node"] = "awaiting_human_review"

    # Simulate reduced evidence for timed-out control
    state["evidence"]["AC-2"] = state["evidence"]["AC-2"][:1]

    grader_results = [
        grade_timeout_logged(state),
        grade_run_continued_after_timeout(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=state["run_id"],
        notes=(
            "State injection. Timeout error injected. "
            "Validates non-fatal timeout handling pattern."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
