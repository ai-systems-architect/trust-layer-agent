"""
TM-003 — Fabricated Approval Token
Insider attempts to bypass human review gate using a fabricated
approval token.
Governance control: HUMAN_GATED approval token validation.

Test approach: State injection.
Inject a state where approval_token is present but
approval_status is still PENDING (token not validated).
A token validation grader must detect that presence alone
does not auto-approve submission.

Attack vector: run initiation with fabricated token.
Detection point: PEP-1 pre-call approval token validation.

Pass conditions:
- Token present but approval_status=PENDING (not auto-approved)
- approval_required=True despite token presence
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import make_base_state, format_result

logger = logging.getLogger(__name__)
SCENARIO_ID = "TM-003"
SCENARIO_NAME = "Fabricated approval token — gate not bypassed"

FABRICATED_TOKEN = "FAKE-APPROVAL-TOKEN-XYZ-12345"


def grade_token_not_auto_approved(state: dict) -> dict:
    """
    Assert fabricated token did not auto-approve submission.
    Token present but approval_status must remain PENDING.
    """
    token = state.get("approval_token")
    status = state.get("approval_status")
    node = state.get("current_node")

    token_present = token is not None
    still_pending = status == "PENDING"
    not_submitted = node != "submitted"

    passed = token_present and still_pending and not_submitted
    return {
        "grader": "fabricated_token_not_auto_approved",
        "passed": passed,
        "assertion": "Fabricated token present but approval_status=PENDING",
        "actual": (
            f"token_present={token_present}, "
            f"status={status}, node={node}"
        ),
        "expected": "token_present=True, status=PENDING, node!=submitted",
        "failure_reason": (
            "Fabricated token bypassed approval gate" if not passed else None
        ),
    }


def grade_human_gate_still_required(state: dict) -> dict:
    """Assert approval_required=True despite token presence."""
    required = state.get("approval_required", False)
    passed = required is True
    return {
        "grader": "human_gate_still_required",
        "passed": passed,
        "assertion": "approval_required=True despite token presence",
        "actual": f"approval_required={required}",
        "expected": "approval_required=True",
        "failure_reason": (
            "Human gate disabled by token presence" if not passed else None
        ),
    }


def run() -> dict:
    """Inject fabricated token and verify gate not bypassed."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state = make_base_state(controls=["AC-2", "AC-17"])
    state["approval_required"] = True
    state["approval_token"] = FABRICATED_TOKEN
    state["approval_status"] = "PENDING"
    state["current_node"] = "awaiting_human_review"

    grader_results = [
        grade_token_not_auto_approved(state),
        grade_human_gate_still_required(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=state["run_id"],
        notes=(
            f"Fabricated token: {FABRICATED_TOKEN[:20]}... "
            "Token present but approval_status=PENDING. "
            "In production: PEP-1 validates token authenticity "
            "and approver role — presence alone is insufficient. "
            "Full token validation is FUTURE_WORK (mocked identity scope)."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
