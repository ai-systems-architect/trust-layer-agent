"""
HP-001 — Full AC-Family Run: Complete Evidence, All Controls
Standard happy path: all four controls assessed with full evidence
from IAM fixtures, CloudTrail fixtures, and P2 compliance text.

Pass conditions:
- All PEP gates passed (34 outcomes expected)
- Evidence lineage complete for all items
- Sufficiency gate enforced (all 4 controls sufficient)
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
SCENARIO_ID = "HP-001"
SCENARIO_NAME = "Full AC-family run — complete evidence, all controls"


def run() -> dict:
    """Execute HP-001 and return grader results."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state, run_id = run_agent(
        controls=["AC-2", "AC-3", "AC-6", "AC-17"],
        account_id="123456789",
    )

    grader_results = run_happy_path_graders(state, run_id)

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes=(
            "Baseline happy path. All four controls assessed. "
            "P2 must be running for T-005 compliance text."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
