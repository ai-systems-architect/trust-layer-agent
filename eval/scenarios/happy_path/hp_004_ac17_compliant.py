"""
HP-004 — AC-17 Assessment: Remote Access With MFA Present
Isolated AC-17 assessment. Both the NON-COMPLIANT fixture
(ac17_remote_access_no_mfa.json) and the COMPLIANT fixture
(ac17_remote_access_with_mfa.json) are loaded, giving the agent
mixed evidence for the same control.

Tests that the agent handles mixed compliant/non-compliant evidence
for a single control and produces a determination based on the
totality of evidence, with citations to both fixture sources.

Pass conditions:
- All PEP gates passed
- Evidence lineage complete (both fixtures loaded)
- Sufficiency gate enforced (mixed evidence is sufficient)
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
SCENARIO_ID = "HP-004"
SCENARIO_NAME = "AC-17 isolated assessment — MFA compliant fixture present"


def grade_multiple_ac17_items(state: dict) -> dict:
    """Assert multiple AC-17 evidence items loaded (both fixtures)."""
    ac17_items = state.get("evidence", {}).get("AC-17", [])
    # Expect at least 2 IAM items: the non-compliant and compliant fixtures
    iam_items = [
        i for i in ac17_items if "iam_policies" in i.get("source_uri", "")
    ]
    passed = len(iam_items) >= 2
    return {
        "grader": "multiple_ac17_iam_fixtures",
        "passed": passed,
        "assertion": "At least 2 AC-17 IAM fixtures loaded (compliant + non-compliant)",
        "actual": f"iam_items={len(iam_items)}",
        "expected": "iam_items>=2",
        "failure_reason": (
            f"Only {len(iam_items)} IAM fixture(s) loaded" if not passed else None
        ),
    }


def run() -> dict:
    """Execute HP-004 and return grader results."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state, run_id = run_agent(
        controls=["AC-17"],
        account_id="123456789",
    )

    grader_results = run_happy_path_graders(state, run_id)
    grader_results.append(grade_multiple_ac17_items(state))

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes=(
            "AC-17 run with both compliant and non-compliant fixtures. "
            "Validates agent handles mixed evidence for same control."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
