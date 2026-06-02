"""
HP-005 — Multi-Control Run: AC-2 and AC-3
Two-control run validating independent evidence chains
and per-control sufficiency assessment.

Pass conditions:
- All PEP gates passed
- Evidence lineage complete for both controls
- Both controls have independent sufficiency results
- Sufficiency gate enforced
- Circuit breaker NOT fired
- Human gate PENDING
- Governance decision written
- Zero errors
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import run_happy_path_graders

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-005"
SCENARIO_NAME = "Multi-control run — AC-2 and AC-3 independent chains"


def grade_both_controls_assessed(state: dict) -> dict:
    """Assert both AC-2 and AC-3 have sufficiency results."""
    results = state.get("sufficiency_results", {})
    ac2_present = "AC-2" in results
    ac3_present = "AC-3" in results
    passed = ac2_present and ac3_present
    return {
        "grader": "both_controls_assessed",
        "passed": passed,
        "assertion": "AC-2 and AC-3 both have sufficiency results",
        "actual": f"AC-2={ac2_present}, AC-3={ac3_present}",
        "expected": "AC-2=True, AC-3=True",
        "failure_reason": (
            f"Missing: {'AC-2' if not ac2_present else 'AC-3'}"
            if not passed else None
        ),
    }


def run() -> dict:
    """Execute HP-005 and return grader results."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state, run_id = run_agent(
        controls=["AC-2", "AC-3"],
        account_id="123456789",
    )

    grader_results = run_happy_path_graders(state, run_id)
    grader_results.append(grade_both_controls_assessed(state))

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes="Two-control subset run. Validates independent evidence chains.",
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
