"""
Tool T-004 — search_cloudtrail_events.

Reads CloudTrail event fixtures for the declared account scope and returns
evidence items that have passed PEP-1 (pre-call) and PEP-2 (post-call) checks.

Registered in config/trust_ledger.yaml as:
    autonomy_class: AUTONOMOUS
    risk_tier: LOW
    max_calls_per_run: 20
    evidence_lineage_required: true

Synthetic data only. Real CloudTrail integration documented in FUTURE_WORK.md.
The integration pattern (real CloudTrail LookupEvents, STS session scope) is
specified in docs/framework_reference.md Section 3 (Agent Identity).

References:
    DL-032: AC-2, AC-3, AC-6, AC-17 demonstration scope
    Framework Section 4.3: Policy Enforcement Points
    FUTURE_WORK.md: Real telemetry integration
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from src.agent.pep import PEP1Validator, PEP2Sanitizer, record_pep_outcome
from src.agent.state import AgentState, EvidenceItem
from src.agent.trust_ledger import TrustLedger

logger = logging.getLogger(__name__)

FIXTURES_PATH = Path("fixtures/cloudtrail_events")
TOOL_ID = "T-004"
TOOL_NAME = "search_cloudtrail_events"


def search_cloudtrail_events(
    state: AgentState,
    trust_ledger: TrustLedger,
    control_ids: Optional[List[str]] = None,
) -> Tuple[List[EvidenceItem], List[str]]:
    """
    Search CloudTrail event fixtures for the declared account scope.

    Applies PEP-1 before loading any fixture and PEP-2 on each raw item before
    it is returned. Both gate outcomes are recorded in state["pep_outcomes"].

    CloudTrail fixture files contain a top-level "Records" list. Each record
    carries control_id and finding metadata directly on the record object.

    Args:
        state:         Current agent run state (read-only within tool scope).
        trust_ledger:  Validated trust ledger — used by PEP-1.
        control_ids:   Controls to filter by; defaults to state["controls_to_assess"].

    Returns:
        evidence_items: List of PEP-2-cleared EvidenceItem dicts.
        errors:         List of error strings (PEP denials + fixture load errors).
    """
    evidence_items: List[EvidenceItem] = []
    errors: List[str] = []

    # ── PEP-1: Pre-call validation ────────────────────────────────────────────
    pep1 = PEP1Validator(trust_ledger)
    pep1_result = pep1.validate(
        tool_id=TOOL_ID,
        tool_name=TOOL_NAME,
        current_call_count=state["tool_call_counts"].get(TOOL_ID, 0),
        declared_control_family=state["declared_control_family"],
        declared_account_id=state["declared_account_id"],
        approval_token=state.get("approval_token"),
    )
    record_pep_outcome(state, {
        "gate": "PEP-1",
        "tool_id": TOOL_ID,
        "tool_name": TOOL_NAME,
        "passed": pep1_result["passed"],
        "check_performed": pep1_result.get("check_performed"),
        "failure_reason": pep1_result["failure_reason"],
    })

    if not pep1_result["passed"]:
        msg = f"PEP-1 rejected {TOOL_NAME}: {pep1_result['failure_reason']}"
        logger.warning("[%s] %s", state["run_id"], msg)
        return [], [msg]

    # ── Load fixtures ─────────────────────────────────────────────────────────
    target_controls = control_ids or state["controls_to_assess"]
    pep2 = PEP2Sanitizer()

    for fixture_file in sorted(FIXTURES_PATH.glob("*.json")):
        try:
            with open(fixture_file) as fh:
                event_doc = json.load(fh)
        except Exception as exc:
            errors.append(f"Error loading fixture {fixture_file.name}: {exc}")
            continue

        # CloudTrail fixtures wrap records in a top-level "Records" list.
        records = event_doc.get("Records", [event_doc])

        for record in records:
            control_id = record.get("control_id", "")
            if control_id not in target_controls:
                continue

            chunk_text = json.dumps(record, indent=2)
            evidence_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
            retrieval_ts = datetime.now(timezone.utc).isoformat()
            source_uri = f"fixtures://cloudtrail_events/{fixture_file.name}"

            raw_item: EvidenceItem = {
                "control_id": control_id,
                "source_uri": source_uri,
                "retrieval_timestamp": retrieval_ts,
                "evidence_hash": evidence_hash,
                "text": chunk_text,
                "relevance_score": 1.0,
                "framework": "NIST-800-53",
                "tool_id": TOOL_ID,
            }

            # ── PEP-2: Post-call sanitization ─────────────────────────────────
            pep2_result = pep2.sanitize(raw_item)
            record_pep_outcome(state, {
                "gate": "PEP-2",
                "tool_id": TOOL_ID,
                "tool_name": TOOL_NAME,
                "source_uri": source_uri,
                "passed": pep2_result["passed"],
                "failure_reason": pep2_result["failure_reason"],
            })

            if pep2_result["passed"]:
                evidence_items.append(pep2_result["sanitized_item"])
            else:
                errors.append(
                    f"PEP-2 rejected record from {fixture_file.name}: "
                    f"{pep2_result['failure_reason']}"
                )

    logger.info(
        "[%s] %s: returned %d evidence items for controls=%s",
        state["run_id"],
        TOOL_NAME,
        len(evidence_items),
        target_controls,
    )
    return evidence_items, errors
