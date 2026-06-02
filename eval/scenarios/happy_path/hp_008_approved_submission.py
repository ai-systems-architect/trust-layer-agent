"""
HP-008 — Approved Submission Flow
Validates the full run to human gate: evidence collected,
sufficiency assessed, draft generated, run suspended at
awaiting_human_review with PENDING status and both output
artifacts written.

Full STS-wired token approval is documented in FUTURE_WORK.md.
This scenario validates the PENDING gate and artifact outputs.

Pass conditions:
- All PEP gates passed
- Evidence lineage complete
- Sufficiency gate enforced
- Circuit breaker NOT fired
- Human gate PENDING (approval_status=PENDING)
- Governance decision written
- Draft assessment file written and non-empty
- approval_required=True in final state
- Zero errors
"""

from __future__ import annotations

import logging
from pathlib import Path

from eval.scenarios.helpers import run_agent, format_result
from eval.graders.deterministic import (
    grade_pep_outcomes,
    grade_evidence_lineage,
    grade_sufficiency_gate,
    grade_circuit_breaker,
    grade_zero_errors,
    grade_governance_decision_written,
)

logger = logging.getLogger(__name__)
SCENARIO_ID = "HP-008"
SCENARIO_NAME = "Approved submission flow — PENDING gate confirmed"


def grade_draft_written(run_id: str) -> dict:
    """Assert draft assessment file was written to outputs/ and is non-empty."""
    path = Path("outputs") / f"draft_assessment_{run_id}.md"
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    passed = exists and size > 100
    return {
        "grader": "draft_assessment_written",
        "passed": passed,
        "assertion": "draft_assessment_{run_id}.md written and non-empty",
        "actual": f"exists={exists}, size={size}",
        "expected": "exists=True, size>100",
        "failure_reason": (
            "Draft not written or empty" if not passed else None
        ),
    }


def grade_approval_required_true(state: dict) -> dict:
    """Assert approval_required is True in final state."""
    approval_required = state.get("approval_required", False)
    passed = approval_required is True
    return {
        "grader": "approval_required_true",
        "passed": passed,
        "assertion": "approval_required=True in final state",
        "actual": f"approval_required={approval_required}",
        "expected": "approval_required=True",
        "failure_reason": (
            "Submission gate not set" if not passed else None
        ),
    }


def run() -> dict:
    """Execute HP-008 and return grader results."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state, run_id = run_agent(
        controls=["AC-2", "AC-3", "AC-6", "AC-17"],
    )

    grader_results = [
        grade_pep_outcomes(state),
        grade_evidence_lineage(state),
        grade_sufficiency_gate(state),
        grade_circuit_breaker(state, expected_fired=False),
        grade_zero_errors(state),
        grade_governance_decision_written(run_id),
        grade_draft_written(run_id),
        grade_approval_required_true(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes=(
            "Validates full run reaches PENDING human gate with both "
            "output artifacts written. "
            "Token-based approval is FUTURE_WORK."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
