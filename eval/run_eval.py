"""
Phase 3 Evaluation Runner — trust-layer-agent
Runs all evaluation scenarios and produces eval_report.md.

Three-tier evaluation architecture:
  Tier 1: Deterministic code-based graders (eval/graders/deterministic.py)
  Tier 2: LLM-as-judge (eval/graders/llm_judge.py)
  Tier 3: Human review (eval/human_review_log.md)

Usage:
  python eval/run_eval.py                    # run all scenarios
  python eval/run_eval.py --tier happy_path  # run one tier
  python eval/run_eval.py --scenario hp_001  # run one scenario

NOTE: HP-007 (P2 unavailable) must be run separately with P2 stopped.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path before any local imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

SCENARIO_TIERS = ["happy_path", "failure_modes", "adversarial"]


def run_happy_path() -> list[dict]:
    """Run all happy path scenarios (except HP-007 which requires P2 down)."""
    from eval.scenarios.happy_path import (  # noqa: PLC0415
        hp_001_ac2_complete,
        hp_002_ac3_finding,
        hp_003_ac6_violation,
        hp_004_ac17_compliant,
        hp_005_multi_control,
        hp_006_rerun_after_rejection,
        hp_008_approved_submission,
    )

    scenarios = [
        hp_001_ac2_complete,
        hp_002_ac3_finding,
        hp_003_ac6_violation,
        hp_004_ac17_compliant,
        hp_005_multi_control,
        hp_006_rerun_after_rejection,
        hp_008_approved_submission,
    ]

    logger.info(
        "NOTE: HP-007 (P2 down) must be run separately with P2 not running."
    )

    results = []
    for scenario in scenarios:
        try:
            result = scenario.run()
            results.append(result)
            status = "PASS" if result["passed"] else "FAIL"
            logger.info(
                "%-10s %-8s %s",
                result["scenario_id"],
                status,
                result["grader_pass_rate"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Scenario %s crashed: %s",
                getattr(scenario, "__name__", "UNKNOWN"),
                exc,
            )
            results.append({
                "scenario_id": getattr(scenario, "SCENARIO_ID", "UNKNOWN"),
                "passed": False,
                "error": str(exc),
            })

    passed = sum(1 for r in results if r.get("passed"))
    logger.info("Happy path complete: %d/%d passed", passed, len(results))
    return results


def run_failure_modes() -> list[dict]:
    """Run all 7 failure mode scenarios."""
    from eval.scenarios.failure_modes import (  # noqa: PLC0415
        fm_001_hallucinated_assertion,
        fm_002_incomplete_evidence,
        fm_003_reasoning_loop,
        fm_004_tool_timeout,
        fm_005_sufficiency_gate_bypass,
        fm_006_excessive_tokens,
        fm_007_stale_evidence,
    )

    scenarios = [
        fm_001_hallucinated_assertion,
        fm_002_incomplete_evidence,
        fm_003_reasoning_loop,
        fm_004_tool_timeout,
        fm_005_sufficiency_gate_bypass,
        fm_006_excessive_tokens,
        fm_007_stale_evidence,
    ]

    results = []
    for scenario in scenarios:
        try:
            result = scenario.run()
            results.append(result)
            status = "PASS" if result["passed"] else "FAIL"
            logger.info(
                "%-10s %-8s %s",
                result["scenario_id"],
                status,
                result["grader_pass_rate"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Scenario %s crashed: %s",
                getattr(scenario, "__name__", "UNKNOWN"),
                exc,
            )
            results.append({
                "scenario_id": getattr(scenario, "SCENARIO_ID", "UNKNOWN"),
                "passed": False,
                "error": str(exc),
            })

    passed = sum(1 for r in results if r.get("passed"))
    logger.info("Failure modes complete: %d/%d passed", passed, len(results))
    return results


def run_all() -> list[dict]:
    """Run all evaluation scenarios."""
    logger.info("Phase 3 Evaluation Suite — starting full run")
    hp_results = run_happy_path()
    fm_results = run_failure_modes()
    all_results = hp_results + fm_results
    passed = sum(1 for r in all_results if r.get("passed"))
    logger.info(
        "Full eval complete: %d/%d scenarios passed",
        passed, len(all_results),
    )
    logger.info("Adversarial scenarios — not yet implemented")
    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="trust-layer-agent Phase 3 Evaluation Runner"
    )
    parser.add_argument(
        "--tier",
        choices=SCENARIO_TIERS,
        help="Run only one scenario tier",
    )
    parser.add_argument(
        "--scenario",
        help="Run a single scenario by prefix (e.g. hp_001)",
    )
    args = parser.parse_args()

    logger.info(
        "Eval run started: %s",
        datetime.now(timezone.utc).isoformat(),
    )

    if args.scenario:
        logger.info("Single scenario mode: %s", args.scenario)
        # TODO Phase 3 — route to individual scenario by prefix
    elif args.tier:
        logger.info("Single tier mode: %s", args.tier)
        if args.tier == "happy_path":
            run_happy_path()
        elif args.tier == "failure_modes":
            run_failure_modes()
    else:
        run_all()


if __name__ == "__main__":
    main()
