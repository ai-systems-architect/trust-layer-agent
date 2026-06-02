"""
Test run script — synthetic AC-family invocation.

Initialises the graph with a clean per-run state and invokes it against
the four AC-family controls selected in DL-032. Node implementations are
stubs; this script exercises the graph structure and state machine routing.

Usage (from repo root):
    python -m scripts.run_agent

    Or with PYTHONPATH:
    PYTHONPATH=. python scripts/run_agent.py

References:
    DL-032: AC-2, AC-3, AC-6, AC-17 selected as demonstration scope
    DL-036: Each invocation starts with clean ephemeral state
    Framework Section 3: Agent Identity and Delegated Authority
"""

from __future__ import annotations

import logging
import sys
import time
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

import httpx  # noqa: E402

from src.agent.graph import create_graph  # noqa: E402
from src.agent.state import AgentState  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def check_p2_warmup() -> bool:
    """
    Check whether the P2 RAG service is up before invoking the graph.

    A 200 response means P2 is healthy; a 3-second sleep follows to let
    Presidio/spaCy finish loading before the first /retrieve call arrives.

    Connection refused means P2 is not running — T-005 will hit FM-002
    graceful degradation on every call (non-fatal, agent continues with
    IAM and CloudTrail evidence only).

    Returns:
        True if P2 responded with HTTP 200, False otherwise.
    """
    p2_url = "http://localhost:8000/health"
    try:
        resp = httpx.get(p2_url, timeout=5.0)
        if resp.status_code == 200:
            logger.info(
                "P2 RAG service is up — waiting 3 seconds for Presidio/spaCy warmup"
            )
            time.sleep(3)
            return True
        logger.warning(
            "P2 RAG service returned HTTP %d — T-005 will degrade to FM-002 (non-fatal)",
            resp.status_code,
        )
        return False
    except httpx.ConnectError:
        logger.warning(
            "P2 RAG service unreachable — T-005 will degrade to FM-002 (non-fatal)"
        )
        return False
    except Exception as exc:
        logger.warning("P2 health check error — T-005 will degrade to FM-002: %s", exc)
        return False


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

    check_p2_warmup()

    initial_state = make_initial_state()
    logger.info(
        "Starting run: run_id=%s controls=%s account=%s",
        initial_state["run_id"],
        initial_state["controls_to_assess"],
        initial_state["declared_account_id"],
    )

    # recursion_limit must exceed MAX_ITERATIONS * nodes-per-cycle to allow
    # circuit breakers to fire before LangGraph's internal limit.
    final_state: AgentState = graph.invoke(
        initial_state,
        config={"recursion_limit": 200},
    )

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

    # Flush Langfuse traces before process exits
    try:
        from langfuse import get_client  # noqa: PLC0415
        get_client().flush()
        logger.info("Langfuse traces flushed")
    except Exception as e:  # noqa: BLE001
        logger.warning("Langfuse flush failed: %s", e)


if __name__ == "__main__":
    main()
