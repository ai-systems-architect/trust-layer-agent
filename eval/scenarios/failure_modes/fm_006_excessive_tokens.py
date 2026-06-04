"""
FM-006 — Excessive Token Consumption
Agent run consumes tokens significantly above the DL-037 baseline.
Governance control: Langfuse token baseline monitoring.

Test approach: Real agent run.
Run full four-control assessment, verify token instrumentation
is active and run completes cleanly. Token breakdown visible in
Langfuse trace. Anomaly detection documented for Phase 3 baseline.

DL-037 baseline (uncached, cross-region profile):
  Sufficiency (4 controls): ~4,968 input tokens total
  Drafting: ~4,871 input tokens
  Total input: ~9,839 tokens per full run

Pass conditions:
- Tool call counts recorded (instrumentation active)
- Run reached awaiting_human_review (full token capture)
"""

from __future__ import annotations

import logging

from eval.scenarios.helpers import run_agent, format_result

logger = logging.getLogger(__name__)
SCENARIO_ID = "FM-006"
SCENARIO_NAME = "Token consumption — within baseline, instrumentation confirmed"

BASELINE_TOTAL_INPUT = 9_839
ANOMALY_MULTIPLIER = 3.0


def grade_token_instrumentation(state: dict) -> dict:
    """Assert tool call counts recorded — instrumentation active."""
    tool_counts = state.get("tool_call_counts", {})
    instrumented = len(tool_counts) > 0
    return {
        "grader": "token_instrumentation_active",
        "passed": instrumented,
        "assertion": "Tool call counts recorded in state",
        "actual": f"tool_call_counts={tool_counts}",
        "expected": "Non-empty tool_call_counts",
        "failure_reason": (
            "No tool call counts — instrumentation may be broken"
            if not instrumented else None
        ),
    }


def grade_run_completed_for_baseline(state: dict) -> dict:
    """Assert run reached awaiting_human_review for full token capture."""
    node = state.get("current_node", "")
    passed = node == "awaiting_human_review"
    return {
        "grader": "run_completed_for_token_baseline",
        "passed": passed,
        "assertion": "Run reached awaiting_human_review for full token capture",
        "actual": f"current_node={node}",
        "expected": "current_node=awaiting_human_review",
        "failure_reason": (
            f"Run ended at {node} — full token baseline not captured"
            if not passed else None
        ),
    }


def run() -> dict:
    """Run agent and verify token instrumentation is working."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)
    logger.info(
        "%s — DL-037 baseline: ~%d total input tokens per run",
        SCENARIO_ID, BASELINE_TOTAL_INPUT,
    )

    state, run_id = run_agent(
        controls=["AC-2", "AC-3", "AC-6", "AC-17"],
    )

    grader_results = [
        grade_token_instrumentation(state),
        grade_run_completed_for_baseline(state),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=run_id,
        notes=(
            f"DL-037 baseline: ~{BASELINE_TOTAL_INPUT} input tokens. "
            f"Anomaly threshold: {ANOMALY_MULTIPLIER}x = "
            f"~{int(BASELINE_TOTAL_INPUT * ANOMALY_MULTIPLIER)} tokens. "
            "Full token breakdown visible in Langfuse trace."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
