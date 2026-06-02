"""
HP-006 — Re-Run After Human Rejection
Simulates a human reviewer rejecting the draft and the agent
producing a fresh independent run. Validates ephemeral memory
(DL-036) — no state shared between runs.

Implementation: two sequential agent runs. Each starts from clean
state. The second run represents the re-run after rejection.

Pass conditions (run 2):
- All PEP gates passed
- Fresh evidence collected (new run_id)
- Sufficiency gate enforced
- Circuit breaker NOT fired
- Human gate PENDING
- Governance decision written
- Zero errors
- Run IDs are different (truly independent runs)
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import run_happy_path_graders

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-006"
SCENARIO_NAME = "Re-run after rejection — ephemeral memory validated"


def run() -> dict:
    """Execute HP-006 — two independent runs, grade the second."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    # Run 1: initial submission (would be rejected by human reviewer)
    logger.info("%s — Run 1 (simulating initial submission)", SCENARIO_ID)
    state_1, run_id_1 = run_agent(controls=["AC-2", "AC-3"])
    logger.info(
        "%s — Run 1 complete: run_id=%s node=%s",
        SCENARIO_ID, run_id_1, state_1.get("current_node"),
    )

    # Run 2: re-run after rejection
    logger.info("%s — Run 2 (re-run after rejection)", SCENARIO_ID)
    state_2, run_id_2 = run_agent(controls=["AC-2", "AC-3"])

    grader_results = run_happy_path_graders(state_2, run_id_2)

    independent_run = run_id_1 != run_id_2
    grader_results.append({
        "grader": "runs_are_independent",
        "passed": independent_run,
        "assertion": "Run 2 has different run_id — ephemeral, not cached",
        "actual": (
            f"run_id_1={run_id_1[:8]}... run_id_2={run_id_2[:8]}..."
        ),
        "expected": "Different run_ids",
        "failure_reason": (
            "Run IDs identical — state may be shared"
            if not independent_run else None
        ),
    })

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state_2,
        run_id=run_id_2,
        notes=(
            f"Run 1 (rejected): {run_id_1[:8]}... | "
            f"Run 2 (re-run): {run_id_2[:8]}... "
            "Validates ephemeral memory — no state shared between runs."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
