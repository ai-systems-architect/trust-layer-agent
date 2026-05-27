"""
Test run script — synthetic AC-family invocation.

Initialises the graph with a clean per-run state and invokes it against
the four AC-family controls selected in DL-031. Node implementations are
stubs; this script exercises the graph structure and state machine routing.

Usage (from repo root):
    python -m scripts.run_agent

    Or with PYTHONPATH:
    PYTHONPATH=. python scripts/run_agent.py

References:
    DL-031: AC-2, AC-3, AC-6, AC-17 selected as demonstration scope
    DL-035: Each invocation starts with clean ephemeral state
    Framework Section 3: Agent Identity and Delegated Authority
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on the path when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env before importing modules that read env vars.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional for script execution

from src.agent.graph import create_graph  # noqa: E402
from src.agent.state import AgentState  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def make_initial_state() -> AgentState:
    """
    Build the initial AgentState for a synthetic AC-family test run.

    All fields must be present — TypedDict does not support defaults.
    Evidence, PEP outcomes, and governance counters are initialised empty.
    """
    return AgentState(
        # Run identity (Framework Section 3 — declared at invocation)
        run_id=str(uuid.uuid4()),
        initiating_principal="test-user",
        declared_control_family="AC",
        declared_account_id="123456789",
        controls_to_assess=["AC-2", "AC-3", "AC-6", "AC-17"],
        run_start_time=datetime.now(timezone.utc).isoformat(),

        # Evidence — empty at run start
        evidence={},
        sufficiency_results={},
        evidence_retry_count=0,

        # Draft output — populated in drafting node
        draft_assessment=None,
        draft_timestamp=None,

        # Human gate — approval_status set to PENDING in awaiting_human_review
        approval_required=False,
        approval_token=None,
        approval_status=None,
        approver_role=None,
        approval_timestamp=None,

        # Governance instrumentation
        pep_outcomes=[],
        tool_call_counts={},
        iteration_count=0,
        circuit_breaker_fired=False,
        circuit_breaker_reason=None,

        # Error tracking
        errors=[],

        # Current position
        current_node="",
    )


def main() -> None:
    """Run the agent with a synthetic test invocation and print final state."""
    logger.info("Initialising trust-layer-agent graph")
    graph = create_graph()

    initial_state = make_initial_state()
    logger.info(
        "Starting run: run_id=%s controls=%s account=%s",
        initial_state["run_id"],
        initial_state["controls_to_assess"],
        initial_state["declared_account_id"],
    )

    final_state: AgentState = graph.invoke(initial_state)

    logger.info("─" * 60)
    logger.info("Run complete — final state summary")
    logger.info("  run_id:                %s", final_state.get("run_id"))
    logger.info("  current_node:          %s", final_state.get("current_node"))
    logger.info("  iteration_count:       %d", final_state.get("iteration_count", 0))
    logger.info("  evidence_retry_count:  %d", final_state.get("evidence_retry_count", 0))
    logger.info("  circuit_breaker_fired: %s", final_state.get("circuit_breaker_fired"))
    logger.info(
        "  circuit_breaker_reason: %s", final_state.get("circuit_breaker_reason")
    )
    logger.info("  approval_status:       %s", final_state.get("approval_status"))
    logger.info("  pep_outcomes:          %d recorded", len(final_state.get("pep_outcomes", [])))
    logger.info("  errors:                %s", final_state.get("errors"))
    logger.info("─" * 60)


if __name__ == "__main__":
    main()
