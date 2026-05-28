"""
Tool T-005 — lookup_compliance_requirement.

Retrieves compliance requirement text from the trust-layer-rag P2 FastAPI
service for each control in the declared scope. Evidence items returned by
P2 are PEP-2 sanitized before entering agent reasoning state.

Registered in config/trust_ledger.yaml as:
    autonomy_class: AUTONOMOUS
    risk_tier: LOW
    max_calls_per_run: 20
    evidence_lineage_required: true

P2 unreachability is a degraded — not fatal — condition (FM-002). The agent
continues with IAM and CloudTrail evidence; missing compliance requirement
text is recorded in errors and surfaced in sufficiency assessment.

P2 API contract:
    POST {P2_RAG_BASE_URL}/retrieve
    Body: {"query": str, "control_family": str, "framework": str, "top_k": int}
    Response: {"chunks": [{"text": str, "source_uri": str, "evidence_hash": str,
                            "retrieval_timestamp": str, "relevance_score": float,
                            "framework": str, "control_id": str}]}

References:
    DL-031: AC-2, AC-3, AC-6, AC-17 demonstration scope
    Framework Section 4.3: Policy Enforcement Points
    Framework Section 5: Failure Mode Catalog — FM-002 (tool unavailability)
    FUTURE_WORK.md: Real telemetry integration
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.agent.pep import PEP1Validator, PEP2Sanitizer, record_pep_outcome
from src.agent.state import AgentState, EvidenceItem
from src.agent.trust_ledger import TrustLedger, get_tool

logger = logging.getLogger(__name__)

TOOL_ID = "T-005"
TOOL_NAME = "lookup_compliance_requirement"
_DEFAULT_P2_BASE_URL = "http://localhost:8000"


def _p2_base_url() -> str:
    """Return P2 RAG base URL from environment, falling back to localhost."""
    return os.getenv("P2_RAG_BASE_URL", _DEFAULT_P2_BASE_URL).rstrip("/")


def _build_request_body(control_id: str, control_family: str) -> Dict[str, Any]:
    """Build the P2 /retrieve request body for a single control."""
    return {
        "query": f"compliance requirements for {control_id}",
        "control_family": control_family,
        "framework": "NIST-800-53",
        "top_k": 5,
    }


def _map_chunk_to_evidence_item(
    chunk: Dict[str, Any],
    control_id: str,
    retrieval_ts: str,
) -> EvidenceItem:
    """
    Map a P2 response chunk to an EvidenceItem.

    P2 is expected to populate source_uri, evidence_hash, retrieval_timestamp,
    and relevance_score. Missing fields default to safe sentinel values so
    PEP-2 lineage checks catch them explicitly.
    """
    return {
        "control_id": chunk.get("control_id", control_id),
        "source_uri": chunk.get("source_uri", ""),
        "retrieval_timestamp": chunk.get("retrieval_timestamp", retrieval_ts),
        "evidence_hash": chunk.get("evidence_hash", ""),
        "text": chunk.get("text", ""),
        "relevance_score": float(chunk.get("relevance_score", 0.0)),
        "framework": chunk.get("framework", "NIST-800-53"),
        "tool_id": TOOL_ID,
    }


def lookup_compliance_requirement(
    state: AgentState,
    trust_ledger: TrustLedger,
    control_ids: Optional[List[str]] = None,
) -> Tuple[List[EvidenceItem], List[str]]:
    """
    Retrieve compliance requirement text from the P2 RAG service.

    Issues one POST /retrieve request per control in control_ids (or
    state["controls_to_assess"]). PEP-1 is applied once before any request.
    PEP-2 is applied to each chunk returned by P2.

    P2 unreachability (httpx.RequestError) is handled gracefully — the tool
    returns an empty evidence list and a descriptive error. The agent continues
    (FM-002: tool unavailability is degraded, not fatal).

    Args:
        state:         Current agent run state (read-only within tool scope).
        trust_ledger:  Validated trust ledger — used by PEP-1 and timeout lookup.
        control_ids:   Controls to query; defaults to state["controls_to_assess"].

    Returns:
        evidence_items: List of PEP-2-cleared EvidenceItem dicts.
        errors:         List of error strings (PEP denials, P2 errors, PEP-2 denials).
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

    # ── Resolve timeout from trust ledger ─────────────────────────────────────
    tool_entry = get_tool(trust_ledger, TOOL_NAME)
    timeout_seconds = tool_entry.timeout_seconds if tool_entry else 15

    target_controls = control_ids or state["controls_to_assess"]
    control_family = state["declared_control_family"]
    base_url = _p2_base_url()
    pep2 = PEP2Sanitizer()

    # ── One request per control ───────────────────────────────────────────────
    for control_id in target_controls:
        body = _build_request_body(control_id, control_family)
        retrieval_ts = datetime.now(timezone.utc).isoformat()

        try:
            response = httpx.post(
                f"{base_url}/retrieve",
                json=body,
                timeout=float(timeout_seconds),
            )
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()

        except httpx.RequestError as exc:
            # FM-002: P2 unreachable — log and continue, do not crash agent
            msg = (
                f"{TOOL_NAME}: P2 unreachable for control {control_id} "
                f"at {base_url}/retrieve — {exc} (FM-002: degraded, not fatal)"
            )
            logger.warning("[%s] %s", state["run_id"], msg)
            errors.append(msg)
            continue

        except httpx.HTTPStatusError as exc:
            msg = (
                f"{TOOL_NAME}: P2 returned HTTP {exc.response.status_code} "
                f"for control {control_id}"
            )
            logger.warning("[%s] %s", state["run_id"], msg)
            errors.append(msg)
            continue

        # ── Map and PEP-2 each chunk ──────────────────────────────────────────
        chunks: List[Dict[str, Any]] = payload.get("chunks", [])
        if not chunks:
            logger.info(
                "[%s] %s: P2 returned 0 chunks for control=%s",
                state["run_id"],
                TOOL_NAME,
                control_id,
            )

        for chunk in chunks:
            raw_item = _map_chunk_to_evidence_item(chunk, control_id, retrieval_ts)
            pep2_result = pep2.sanitize(raw_item)

            record_pep_outcome(state, {
                "gate": "PEP-2",
                "tool_id": TOOL_ID,
                "tool_name": TOOL_NAME,
                "source_uri": raw_item.get("source_uri"),
                "passed": pep2_result["passed"],
                "failure_reason": pep2_result["failure_reason"],
            })

            if pep2_result["passed"]:
                evidence_items.append(pep2_result["sanitized_item"])
            else:
                errors.append(
                    f"PEP-2 rejected P2 chunk for {control_id}: "
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
