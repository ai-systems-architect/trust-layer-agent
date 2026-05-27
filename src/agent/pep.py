"""
Policy Enforcement Point (PEP) stubs — PEP-1 and PEP-2.

PEPs are explicit checkpoints where governance controls are applied.
This module implements PEP-1 (pre-call validation) and PEP-2 (post-call
sanitization). PEP-3 (pre-output release) is enforced in the drafting node.

PEPs are called explicitly at node boundaries — not inside LangGraph's
internal orchestration — so they are visible to the audit trail and cannot
be bypassed by the orchestration framework (DL-030, Framework Section 11).

References:
    DL-030: LangGraph PEP insertion rationale — inside execution path,
            not at orchestration boundaries
    Framework Section 4.3: Policy Enforcement Points
    Framework Section 6.2: TM-001 (prompt injection via PEP-2 scan)
    Framework Section 6.2: TM-002 (confused deputy via PEP-1 scope check)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agent.state import AgentState
from src.agent.trust_ledger import TrustLedger, ToolEntry, get_tool

logger = logging.getLogger(__name__)


# ── PEP outcome constants ──────────────────────────────────────────────────────

class PEPOutcome:
    PASSED = "PASSED"
    DENIED = "DENIED"
    SANITIZED = "SANITIZED"


# ── PEP-1 — Pre-Call Validation ───────────────────────────────────────────────

def pep1_pre_call(
    state: AgentState,
    ledger: TrustLedger,
    tool_name: str,
    tool_args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    PEP-1 — Pre-Call Validation.

    Six checks applied in sequence. All six must pass for invocation to proceed.
    Returns a result dict with keys: gate, tool_name, outcome, failure_reason,
    and tool_entry (populated on PASSED).

    Checks implemented (stubs marked TODO for Agent Implementation):
        1. Tool registration   — implicit DENY if not in ledger
        2. Autonomy class      — DENIED rejected; HUMAN_GATED requires token
        3. Scope bounds        — TODO: validate args against declared run scope
        4. Call count          — TODO: enforce max_calls_per_run
        5. Prohibited actions  — TODO: reject if args reference prohibited list
        6. Data classification — TODO: reject if data exceeds allowed level
    """
    result: Dict[str, Any] = {
        "gate": "PEP-1",
        "tool_name": tool_name,
        "outcome": PEPOutcome.DENIED,
        "failure_reason": None,
        "tool_entry": None,
    }

    # Check 1: Tool registration — implicit DENY
    tool_entry: Optional[ToolEntry] = get_tool(ledger, tool_name)
    if tool_entry is None:
        result["failure_reason"] = (
            f"Tool '{tool_name}' not registered in trust ledger — implicit DENY"
        )
        logger.warning("PEP-1 DENIED [implicit DENY]: %s", result["failure_reason"])
        return result

    # Check 2a: DENIED autonomy class — hard rejection regardless of context
    if tool_entry.autonomy_class == "DENIED":
        result["failure_reason"] = (
            f"Tool '{tool_name}' autonomy_class=DENIED — "
            "rejected at pre-call gate, logged and alerted"
        )
        logger.error("PEP-1 DENIED [DENIED tool]: %s", result["failure_reason"])
        return result

    # Check 2b: HUMAN_GATED — requires valid approval token
    if tool_entry.autonomy_class == "HUMAN_GATED":
        if not state.get("approval_token"):
            result["failure_reason"] = (
                f"Tool '{tool_name}' autonomy_class=HUMAN_GATED — "
                "approval token required before invocation"
            )
            logger.warning(
                "PEP-1 DENIED [HUMAN_GATED, no token]: %s",
                result["failure_reason"],
            )
            return result

    # Check 3: Scope bounds — declared account_id and control family
    # TODO (Agent Implementation): validate tool_args["account_id"] matches
    #   state["declared_account_id"]. Reject cross-account invocations (TM-002).
    # TODO (Agent Implementation): validate tool_args["control_family"] matches
    #   state["declared_control_family"].

    # Check 4: Call count — max_calls_per_run
    # TODO (Agent Implementation): compare state["tool_call_counts"][tool_name]
    #   against tool_entry.max_calls_per_run. Reject if exceeded.

    # Check 5: Prohibited actions
    # TODO (Agent Implementation): scan tool_args for any action string that
    #   appears in tool_entry.prohibited_actions. Reject if found.

    # Check 6: Data classification
    # TODO (Agent Implementation): compare requested data classification
    #   against tool_entry.data_classifications_allowed. Reject if exceeded.

    result["outcome"] = PEPOutcome.PASSED
    result["tool_entry"] = tool_entry
    logger.info("PEP-1 PASSED: tool=%s autonomy=%s", tool_name, tool_entry.autonomy_class)
    return result


# ── PEP-2 — Post-Call Sanitization ───────────────────────────────────────────

def pep2_post_call(
    state: AgentState,
    tool_name: str,
    tool_result: Any,
) -> Dict[str, Any]:
    """
    PEP-2 — Post-Call Sanitization.

    Four checks on the raw tool result before it enters the agent's
    reasoning state. Returns a result dict with keys: gate, tool_name,
    outcome, sanitized_result, failure_reason.

    Checks implemented (stubs marked TODO for Agent Implementation):
        1. Evidence lineage — verify source_uri, retrieval_timestamp,
           evidence_hash present in result
        2. PII scan         — detect and redact PII patterns
        3. Injection scan   — detect prompt injection in retrieved content
                              (TM-001 mitigation)
        4. Result size      — reject oversized results that flood context
    """
    result: Dict[str, Any] = {
        "gate": "PEP-2",
        "tool_name": tool_name,
        "outcome": PEPOutcome.PASSED,
        "sanitized_result": tool_result,
        "failure_reason": None,
    }

    # Check 1: Evidence lineage fields
    # TODO (Agent Implementation): verify tool_result contains source_uri,
    #   retrieval_timestamp, evidence_hash. Set outcome=DENIED and return
    #   if any required field is absent (FM-001 mitigation).

    # Check 2: PII scan
    # TODO (Agent Implementation): run PII detection (regex + classifier)
    #   over tool_result content. Redact detected PII and set
    #   outcome=SANITIZED. Log redaction event.

    # Check 3: Prompt injection scan (TM-001)
    # TODO (Agent Implementation): scan tool_result for injection patterns
    #   (e.g. "[SYSTEM", "IGNORE PREVIOUS", instruction-like imperative
    #   sentences in retrieved content). Set outcome=DENIED if detected.
    #   Injection must be caught here — not at output layer.

    # Check 4: Result size
    # TODO (Agent Implementation): check len(str(tool_result)) against
    #   a configured max (e.g. 50_000 chars). Set outcome=DENIED if exceeded
    #   to prevent context window flooding.

    logger.info("PEP-2 PASSED (stub): tool=%s", tool_name)
    return result


# ── Shared utility ────────────────────────────────────────────────────────────

def record_pep_outcome(
    state: AgentState,
    pep_result: Dict[str, Any],
) -> AgentState:
    """
    Append a PEP result dict to state["pep_outcomes"].

    Called after every PEP-1 and PEP-2 check so the governance decision
    record has a complete audit trail of all gate outcomes for this run.
    """
    state["pep_outcomes"].append(pep_result)
    return state
