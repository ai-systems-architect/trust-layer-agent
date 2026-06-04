"""
FM-007 — Stale Evidence
Agent incorporates evidence from outside the declared run window.
Governance control: retrieval timestamp validation (PEP-3 pre-output).

Test approach: State injection.
Inject evidence items with retrieval_timestamps from 2024
(well outside any current run window). A timestamp validation
grader must detect these as stale.

Pass conditions:
- Stale timestamp grader detects outdated retrieval_timestamps
- Affected items identified by source_uri
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from eval.scenarios.helpers import make_base_state, format_result

logger = logging.getLogger(__name__)
SCENARIO_ID = "FM-007"
SCENARIO_NAME = "Stale evidence — outdated retrieval timestamp detected"

STALE_THRESHOLD_HOURS = 24


def grade_stale_timestamps(state: dict, run_start_time: str) -> dict:
    """
    Detect evidence items with retrieval_timestamps older than
    STALE_THRESHOLD_HOURS before run_start_time.
    Expects stale items to be present — passes if any are found.
    """
    try:
        run_start = datetime.fromisoformat(run_start_time)
        if run_start.tzinfo is None:
            run_start = run_start.replace(tzinfo=timezone.utc)
    except Exception:
        run_start = datetime.now(timezone.utc)

    stale_items: list[str] = []
    for control_id, items in state.get("evidence", {}).items():
        for item in items:
            ts_str = item.get("retrieval_timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_hours = (run_start - ts).total_seconds() / 3600
                if age_hours > STALE_THRESHOLD_HOURS:
                    stale_items.append(
                        f"{control_id}:{item.get('source_uri', '?')} "
                        f"({age_hours:.0f}h old)"
                    )
            except Exception:
                stale_items.append(
                    f"{control_id}:{item.get('source_uri', '?')} "
                    f"(unparseable timestamp)"
                )

    # We EXPECT stale items — grader passes when detection fires
    passed = len(stale_items) > 0
    return {
        "grader": "stale_timestamp_detected",
        "passed": passed,
        "assertion": (
            f"Stale evidence items detected "
            f"(>{STALE_THRESHOLD_HOURS}h before run start)"
        ),
        "actual": f"stale_items={stale_items[:3]}",
        "expected": "At least one stale item detected",
        "failure_reason": (
            "No stale items detected — timestamp validation may not work"
            if not passed else None
        ),
    }


def run() -> dict:
    """Inject stale timestamps and verify detection."""
    logger.info("%s — starting: %s", SCENARIO_ID, SCENARIO_NAME)

    state = make_base_state(controls=["AC-2", "AC-17"])

    # Inject stale timestamps — 2024, well outside any run window
    stale_ts = "2024-11-01T09:00:00+00:00"
    for control_id in state["evidence"]:
        for item in state["evidence"][control_id]:
            item["retrieval_timestamp"] = stale_ts

    run_start = datetime.now(timezone.utc).isoformat()
    state["run_start_time"] = run_start

    grader_results = [
        grade_stale_timestamps(state, run_start),
    ]

    result = format_result(
        scenario_id=SCENARIO_ID,
        scenario_name=SCENARIO_NAME,
        grader_results=grader_results,
        state=state,
        run_id=state["run_id"],
        notes=(
            f"Injected retrieval_timestamps from 2024 "
            f"(>{STALE_THRESHOLD_HOURS}h threshold). "
            "Timestamp validation grader must detect stale items. "
            "In production: PEP-3 pre-output validates evidence currency."
        ),
    )

    logger.info(
        "%s — %s (%s graders passed)",
        SCENARIO_ID,
        "PASS" if result["passed"] else "FAIL",
        result["grader_pass_rate"],
    )
    return result
