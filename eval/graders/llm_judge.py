"""
Tier 2 — LLM-as-Judge Grader
Qualitative evaluation of agent behavior that deterministic
graders cannot assess.

Evaluates:
  - Hedge appropriateness (1-5): Is this hedge justified?
  - Evidence sufficiency quality (1-5): Accurate determination?
  - Reasoning coherence (1-5): Does trace support conclusion?
  - Failure mode handling (1-5): Safe output on failure?
  - Verifier robustness: Does judge catch a bad assessment?

Uses same Bedrock model as the agent (DL-034).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator assessing the \
quality of a federal compliance AI agent's outputs and reasoning.

You evaluate on four dimensions, each scored 1-5:

1. hedge_appropriateness: Is the agent's hedge (qualification,
   uncertainty, or conditional statement) justified given the
   compliance context?
   5 = hedge is precisely calibrated to evidence quality
   1 = hedge is evasive non-answer with no evidentiary basis

2. sufficiency_quality: Does the sufficiency determination
   accurately reflect the evidence collected?
   5 = determination matches evidence with clear rationale
   1 = determination contradicts or ignores evidence

3. reasoning_coherence: Does the agent's reasoning trace
   support the conclusion it reaches?
   5 = conclusion follows directly from evidence chain
   1 = conclusion contradicts or ignores reasoning

4. failure_handling: When a failure mode fires, does the
   recovery produce a safe and informative output state?
   5 = safe termination with clear documentation
   1 = unsafe state or silent failure

Respond in JSON only:
{
  "hedge_appropriateness": 1-5,
  "sufficiency_quality": 1-5,
  "reasoning_coherence": 1-5,
  "failure_handling": 1-5,
  "overall": 1-5,
  "rationale": "one paragraph explanation"
}"""


def judge_sufficiency_rationale(
    control_id: str,
    sufficiency_result: dict,
    evidence_items: list,
) -> dict:
    """
    Judge whether sufficiency rationale accurately reflects evidence.
    Returns scored evaluation dict.
    TODO Phase 3 — implement Bedrock call.
    """
    logger.info(
        "LLM judge: sufficiency_rationale for %s — scaffold only",
        control_id,
    )
    return {
        "dimension": "sufficiency_quality",
        "control_id": control_id,
        "score": None,
        "rationale": "TODO — Phase 3 implementation",
    }


def judge_draft_quality(
    draft_assessment: str,
    evidence: dict,
    sufficiency_results: dict,
) -> dict:
    """
    Judge draft assessment quality — citations, hedges, findings.
    Returns scored evaluation dict.
    TODO Phase 3 — implement Bedrock call.
    """
    logger.info("LLM judge: draft_quality — scaffold only")
    return {
        "dimension": "draft_quality",
        "score": None,
        "rationale": "TODO — Phase 3 implementation",
    }


def judge_verifier_robustness(
    bad_assessment: str,
    known_errors: list[str],
) -> dict:
    """
    Judge whether the LLM-as-judge catches a deliberately bad assessment.

    Verifier robustness test — the judge that cannot catch bad outputs
    is the most fragile part of the evaluation architecture.

    TODO Phase 3 — implement Bedrock call.
    """
    logger.info("LLM judge: verifier_robustness — scaffold only")
    return {
        "dimension": "verifier_robustness",
        "known_errors": known_errors,
        "errors_caught": [],
        "score": None,
        "rationale": "TODO — Phase 3 implementation",
    }
