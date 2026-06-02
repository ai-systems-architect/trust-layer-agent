"""
Shared helpers for evaluation scenarios.
Provides agent invocation, state capture, and result formatting.
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so src.* and eval.* imports resolve correctly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.agent.graph import create_graph  # noqa: E402
from eval.graders.deterministic import (  # noqa: E402
    grade_pep_outcomes,
    grade_evidence_lineage,
    grade_sufficiency_gate,
    grade_circuit_breaker,
    grade_human_gate,
    grade_governance_decision_written,
    grade_zero_errors,
)

logger = logging.getLogger(__name__)

# Re-export graders so scenario files can import from one place.
__all__ = [
    "run_agent",
    "format_result",
    "grade_pep_outcomes",
    "grade_evidence_lineage",
    "grade_sufficiency_gate",
    "grade_circuit_breaker",
    "grade_human_gate",
    "grade_governance_decision_written",
    "grade_zero_errors",
]


def run_agent(
    controls: list[str],
    account_id: str = "123456789",
    control_family: str = "AC",
    initiating_principal: str = "eval-runner",
) -> tuple[dict, str]:
    """
    Run the agent with the given configuration and return (final_state, run_id).

    Creates a fresh graph per call (ephemeral memory — DL-036).
    Requires P2 to be running for T-005 calls; degrades gracefully if not.
    """
    run_id = str(uuid.uuid4())
    initial_state: dict = {
        # Run identity
        "run_id": run_id,
        "initiating_principal": initiating_principal,
        "declared_control_family": control_family,
        "declared_account_id": account_id,
        "controls_to_assess": controls,
        "run_start_time": datetime.now(timezone.utc).isoformat(),
        # Evidence — empty at run start
        "evidence": {},
        "sufficiency_results": {},
        "evidence_retry_count": 0,
        # Draft output
        "draft_assessment": None,
        "draft_timestamp": None,
        # Human gate
        "approval_required": False,
        "approval_token": None,
        "approval_status": None,
        "approver_role": None,
        "approval_timestamp": None,
        # Governance instrumentation
        "pep_outcomes": [],
        "tool_call_counts": {},
        "iteration_count": 0,
        "circuit_breaker_fired": False,
        "circuit_breaker_reason": None,
        # Error tracking
        "errors": [],
        # Current position
        "current_node": "",
    }

    graph = create_graph()
    final_state: dict = graph.invoke(
        initial_state,
        config={"recursion_limit": 100},
    )
    return final_state, run_id


def format_result(
    scenario_id: str,
    scenario_name: str,
    grader_results: list[dict],
    state: dict,
    run_id: str,
    notes: str = "",
) -> dict:
    """Format scenario results for the eval report."""
    passed_count = sum(1 for g in grader_results if g["passed"])
    total = len(grader_results)
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed_count == total,
        "grader_pass_rate": f"{passed_count}/{total}",
        "grader_results": grader_results,
        "final_node": state.get("current_node"),
        "approval_status": state.get("approval_status"),
        "pep_outcomes_count": len(state.get("pep_outcomes", [])),
        "circuit_breaker_fired": state.get("circuit_breaker_fired"),
        "error_count": len(state.get("errors", [])),
        "notes": notes,
    }
