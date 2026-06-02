"""
HP-002 — AC-3 Assessment: Complete Evidence, One Finding
Isolated AC-3 assessment. Expects NON-COMPLIANT finding
(missing permissions boundary) referenced in draft assessment.

Pass conditions:
- All PEP gates passed
- Evidence lineage complete
- Sufficiency gate enforced (NON-COMPLIANT finding is sufficient)
- Circuit breaker NOT fired
- Human gate PENDING
- Governance decision written
- Zero errors
- Draft assessment contains AC-3 finding reference
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import run_happy_path_graders

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-002"
SCENARIO_NAME = "AC-3 isolated assessment — missing boundary finding"


def grade_draft_contains_ac3_finding(state: dict) -> dict:
    """Assert draft mentions AC-3 finding terms."""
    draft = state.get("draft_assessment", "") or ""
    finding_terms = [
        "AC-3", "missing_permissions_boundary",
        "boundary", "DeveloperRole",
    ]
    found = any(term in draft for term in finding_terms)
    return {
        "grader": "draft_contains_ac3_finding",
        "passed": found,
        "assertion": "Draft assessment references AC-3 finding",
        "actual": f"finding_terms_found={found}",
        "expected": "At least one AC-3 finding term present",
        "failure_reason": (
            "Draft does not reference AC-3 finding" if not found else None
        ),
    }


def run() -> dict:
    """Execute HP-002 and return grader results."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state, run_id = run_agent(
        controls=["AC-3"],
        account_id="123456789",
    )

    grader_results = run_happy_path_graders(state, run_id)
    grader_results.append(grade_draft_contains_ac3_finding(state))

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes="Single control run — AC-3 only. Expects missing boundary finding.",
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
