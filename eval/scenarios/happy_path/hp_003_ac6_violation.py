"""
HP-003 — AC-6 Assessment: Least Privilege Wildcard Violation
Isolated AC-6 assessment. Expects wildcard admin finding
referenced in draft assessment.

Pass conditions:
- All PEP gates passed
- Evidence lineage complete
- Sufficiency gate enforced (violation evidence is sufficient)
- Circuit breaker NOT fired
- Human gate PENDING
- Governance decision written
- Zero errors
- Draft references AC-6 least privilege violation
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import run_happy_path_graders

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-003"
SCENARIO_NAME = "AC-6 isolated assessment — wildcard admin violation"


def grade_draft_contains_ac6_finding(state: dict) -> dict:
    """Assert draft mentions AC-6 least privilege violation terms."""
    draft = state.get("draft_assessment", "") or ""
    finding_terms = [
        "AC-6", "wildcard", "AdministratorAccess",
        "least privilege", "LegacyAdminRole",
    ]
    found = any(term in draft for term in finding_terms)
    return {
        "grader": "draft_contains_ac6_finding",
        "passed": found,
        "assertion": "Draft references AC-6 least privilege violation",
        "actual": f"finding_terms_found={found}",
        "expected": "At least one AC-6 finding term present",
        "failure_reason": (
            "Draft does not reference AC-6 finding" if not found else None
        ),
    }


def run() -> dict:
    """Execute HP-003 and return grader results."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state, run_id = run_agent(
        controls=["AC-6"],
        account_id="123456789",
    )

    grader_results = run_happy_path_graders(state, run_id)
    grader_results.append(grade_draft_contains_ac6_finding(state))

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes="Single control run — AC-6 only. Expects wildcard admin finding.",
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
