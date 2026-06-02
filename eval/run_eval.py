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
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

SCENARIO_TIERS = ["happy_path", "failure_modes", "adversarial"]


def run_all() -> None:
    """Run all evaluation scenarios and produce eval report."""
    logger.info("Phase 3 Evaluation Suite — starting full run")
    logger.info("Tiers: happy_path (8) | failure_modes (7) | adversarial (4)")
    # TODO Phase 3 — implement scenario execution
    logger.info("Scaffold only — scenarios not yet implemented")


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
    elif args.tier:
        logger.info("Single tier mode: %s", args.tier)
    else:
        run_all()


if __name__ == "__main__":
    main()
