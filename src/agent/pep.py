"""
Policy Enforcement Point (PEP) — PEP-1, PEP-2, and shared utilities.

Two interfaces are provided:

  Class-based (preferred for new tool implementations):
      PEP1Validator  — pre-call validation; instantiated with the trust ledger.
      PEP2Sanitizer  — post-call sanitization; instantiated without arguments.

  Function-based (preserved for graph node integration — Agent Implementation):
      pep1_pre_call  — wraps PEP1Validator for graph.py call sites.
      pep2_post_call — wraps PEP2Sanitizer for graph.py call sites.
      record_pep_outcome — appends a PEP result to state["pep_outcomes"].

PEPs are called explicitly at node boundaries — not inside LangGraph's
internal orchestration — so they are visible to the audit trail and cannot
be bypassed by the orchestration framework (DL-031, Framework Section 11).

References:
    DL-031: LangGraph PEP insertion rationale — inside execution path
    Framework Section 4.3: Policy Enforcement Points
    Framework Section 6.2: TM-001 (prompt injection via PEP-2 scan)
    Framework Section 6.2: TM-002 (confused deputy via PEP-1 scope check)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agent.state import AgentState, EvidenceItem
from src.agent.trust_ledger import TrustLedger, ToolEntry, get_tool

logger = logging.getLogger(__name__)


# ── PEP outcome constants ──────────────────────────────────────────────────────

class PEPOutcome:
    PASSED = "PASSED"
    DENIED = "DENIED"
    SANITIZED = "SANITIZED"


# ── Injection patterns (TM-001 mitigation) ────────────────────────────────────

_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"\[SYSTEM", re.IGNORECASE),
    re.compile(r"IGNORE\s+(PREVIOUS|INSTRUCTIONS|ABOVE)", re.IGNORECASE),
    re.compile(r"you are now\b", re.IGNORECASE),
    re.compile(r"disregard\s+(your|all|previous)", re.IGNORECASE),
    re.compile(r"new\s+instructions?:", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
]

# Required evidence lineage fields (Framework Section 4.2, FM-001 mitigation)
_REQUIRED_LINEAGE_FIELDS: List[str] = [
    "source_uri",
    "retrieval_timestamp",
    "evidence_hash",
]


# ── PEP-1 — Pre-Call Validation (class-based) ─────────────────────────────────

class PEP1Validator:
    """
    PEP-1 — Pre-Call Validation.

    Instantiate with the trust ledger. Call validate() before every tool
    invocation. All six checks must pass for invocation to proceed.

    Checks:
        1. Tool registration   — tool_name must appear in ledger (implicit DENY)
        2. Autonomy class      — DENIED rejects; HUMAN_GATED requires token
        3. Call count          — enforces max_calls_per_run
        4. Scope bounds        — declared_control_family must be non-empty
        5. Prohibited actions  — stub; pass-through (Agent Implementation)
        6. Data classification — stub; pass-through (Agent Implementation)
    """

    def __init__(self, trust_ledger: TrustLedger) -> None:
        self._ledger = trust_ledger

    def validate(
        self,
        tool_id: str,
        tool_name: str,
        current_call_count: int,
        declared_control_family: str,
        declared_account_id: str,
        approval_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run PEP-1 checks and return a result dict.

        Returns:
            passed (bool): True only if all checks pass.
            check_performed (str): last check reached before pass or fail.
            failure_reason (Optional[str]): populated on failure.
            tool_entry (Optional[ToolEntry]): populated on pass.
        """
        result: Dict[str, Any] = {
            "gate": "PEP-1",
            "tool_id": tool_id,
            "tool_name": tool_name,
            "passed": False,
            "check_performed": "tool_registration",
            "failure_reason": None,
            "tool_entry": None,
        }

        # Check 1: Tool registration — implicit DENY if not in ledger
        tool_entry: Optional[ToolEntry] = get_tool(self._ledger, tool_name)
        if tool_entry is None:
            result["failure_reason"] = (
                f"Tool '{tool_name}' not registered in trust ledger — implicit DENY"
            )
            logger.warning("PEP-1 DENIED [unregistered]: %s", result["failure_reason"])
            return result

        # Verify tool_id matches the registered entry
        if tool_entry.tool_id != tool_id:
            result["failure_reason"] = (
                f"Tool ID mismatch: caller declared '{tool_id}', "
                f"ledger has '{tool_entry.tool_id}' for tool_name='{tool_name}'"
            )
            logger.warning("PEP-1 DENIED [tool_id mismatch]: %s", result["failure_reason"])
            return result

        # Check 2a: DENIED autonomy class — hard rejection
        result["check_performed"] = "autonomy_class"
        if tool_entry.autonomy_class == "DENIED":
            result["failure_reason"] = (
                f"Tool '{tool_name}' autonomy_class=DENIED — "
                "rejected at pre-call gate, logged and alerted"
            )
            logger.error("PEP-1 DENIED [DENIED tool]: %s", result["failure_reason"])
            return result

        # Check 2b: HUMAN_GATED — requires a valid approval token
        if tool_entry.autonomy_class == "HUMAN_GATED":
            if not approval_token:
                result["failure_reason"] = (
                    f"Tool '{tool_name}' autonomy_class=HUMAN_GATED — "
                    "approval token required before invocation"
                )
                logger.warning(
                    "PEP-1 DENIED [HUMAN_GATED, no token]: %s",
                    result["failure_reason"],
                )
                return result

        # Check 3: Call count — max_calls_per_run
        result["check_performed"] = "call_count"
        max_calls = tool_entry.max_calls_per_run
        if max_calls > 0 and current_call_count >= max_calls:
            result["failure_reason"] = (
                f"Tool '{tool_name}' call limit reached: "
                f"{current_call_count}/{max_calls} (max_calls_per_run)"
            )
            logger.warning("PEP-1 DENIED [call limit]: %s", result["failure_reason"])
            return result

        # Check 4: Scope bounds — declared_control_family must be present
        result["check_performed"] = "scope_bounds"
        if not declared_control_family:
            result["failure_reason"] = (
                "declared_control_family is empty — cannot validate scope bounds (TM-002)"
            )
            logger.warning("PEP-1 DENIED [scope_bounds]: %s", result["failure_reason"])
            return result
        # TODO (Agent Implementation): also validate declared_account_id against
        #   tool_args["account_id"] to reject cross-account invocations (TM-002).

        # Check 5: Prohibited actions — stub (Agent Implementation)
        result["check_performed"] = "prohibited_actions"
        # TODO (Agent Implementation): scan invocation args for any action string
        #   that appears in tool_entry.prohibited_actions. Reject if found.

        # Check 6: Data classification — stub (Agent Implementation)
        result["check_performed"] = "data_classification"
        # TODO (Agent Implementation): compare requested data classification level
        #   against tool_entry.data_classifications_allowed. Reject if exceeded.

        result["passed"] = True
        result["tool_entry"] = tool_entry
        logger.info(
            "PEP-1 PASSED: tool=%s autonomy=%s calls=%d/%d",
            tool_name,
            tool_entry.autonomy_class,
            current_call_count,
            max_calls,
        )
        return result


# ── PEP-2 — Post-Call Sanitization (class-based) ─────────────────────────────

class PEP2Sanitizer:
    """
    PEP-2 — Post-Call Sanitization.

    Instantiate without arguments. Call sanitize() on each raw evidence item
    before it enters agent reasoning state.

    Checks:
        1. Evidence lineage — source_uri, retrieval_timestamp, evidence_hash present
        2. Injection scan   — flag prompt injection patterns in text (TM-001)
        3. PII scan         — stub; pass-through (Agent Implementation)
        4. Result size      — stub; pass-through (Agent Implementation)
    """

    def sanitize(self, raw_item: EvidenceItem) -> Dict[str, Any]:
        """
        Run PEP-2 checks on a raw evidence item and return a result dict.

        Returns:
            passed (bool): True if item clears all checks.
            sanitized_item (EvidenceItem): the item (unchanged if PASSED).
            failure_reason (Optional[str]): populated on failure.
        """
        result: Dict[str, Any] = {
            "gate": "PEP-2",
            "passed": False,
            "sanitized_item": raw_item,
            "failure_reason": None,
        }

        # Check 1: Evidence lineage — required fields must be present and non-empty
        missing = [
            f for f in _REQUIRED_LINEAGE_FIELDS
            if not raw_item.get(f)  # type: ignore[call-overload]
        ]
        if missing:
            result["failure_reason"] = (
                f"Evidence item missing required lineage fields: {missing} "
                "(FM-001 mitigation — item rejected)"
            )
            logger.warning("PEP-2 DENIED [lineage]: %s", result["failure_reason"])
            return result

        # Check 2: Prompt injection scan (TM-001)
        text_content = str(raw_item.get("text", ""))  # type: ignore[call-overload]
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text_content):
                result["failure_reason"] = (
                    f"Prompt injection pattern detected in evidence text "
                    f"(pattern: '{pattern.pattern}') — item rejected (TM-001)"
                )
                logger.error("PEP-2 DENIED [injection]: %s", result["failure_reason"])
                return result

        # Check 3: PII scan — stub (Agent Implementation)
        # TODO (Agent Implementation): run PII detection (regex + classifier) over
        #   text_content. Redact detected PII, set outcome=SANITIZED, log redaction.

        # Check 4: Result size — stub (Agent Implementation)
        # TODO (Agent Implementation): check len(text_content) against configured max
        #   (e.g. 50_000 chars). Reject if exceeded to prevent context window flooding.

        result["passed"] = True
        logger.info(
            "PEP-2 PASSED: source_uri=%s",
            raw_item.get("source_uri"),  # type: ignore[call-overload]
        )
        return result


# ── Function-based interface (graph.py integration — Agent Implementation) ────
#
# These wrap the class-based implementations for use at graph node call sites.
# Preserved for forward compatibility with the TODO stubs in graph.py.

def pep1_pre_call(
    state: AgentState,
    ledger: TrustLedger,
    tool_name: str,
    tool_args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    PEP-1 function wrapper — for graph node integration (Agent Implementation).

    Delegates to PEP1Validator. tool_id is resolved from the ledger by tool_name.
    Returns a result dict with keys: gate, tool_name, outcome, failure_reason,
    tool_entry. Maps PEP1Validator result to the legacy outcome-constant shape
    expected by record_pep_outcome.
    """
    validator = PEP1Validator(ledger)
    tool_entry = get_tool(ledger, tool_name)
    tool_id = tool_entry.tool_id if tool_entry else "UNKNOWN"

    v_result = validator.validate(
        tool_id=tool_id,
        tool_name=tool_name,
        current_call_count=state.get("tool_call_counts", {}).get(tool_id, 0),
        declared_control_family=state.get("declared_control_family", ""),
        declared_account_id=state.get("declared_account_id", ""),
        approval_token=state.get("approval_token"),
    )

    # Map to legacy outcome shape for record_pep_outcome / pep_outcomes list
    return {
        "gate": "PEP-1",
        "tool_name": tool_name,
        "outcome": PEPOutcome.PASSED if v_result["passed"] else PEPOutcome.DENIED,
        "failure_reason": v_result["failure_reason"],
        "tool_entry": v_result["tool_entry"],
    }


def pep2_post_call(
    state: AgentState,
    tool_name: str,
    tool_result: Any,
) -> Dict[str, Any]:
    """
    PEP-2 function wrapper — for graph node integration (Agent Implementation).

    Delegates to PEP2Sanitizer when tool_result is a dict (EvidenceItem).
    Falls back to a pass-through for non-dict results.
    Returns a result dict with keys: gate, tool_name, outcome, sanitized_result,
    failure_reason.
    """
    sanitizer = PEP2Sanitizer()

    if isinstance(tool_result, dict):
        s_result = sanitizer.sanitize(tool_result)  # type: ignore[arg-type]
        outcome = PEPOutcome.PASSED if s_result["passed"] else PEPOutcome.DENIED
        return {
            "gate": "PEP-2",
            "tool_name": tool_name,
            "outcome": outcome,
            "sanitized_result": s_result["sanitized_item"],
            "failure_reason": s_result["failure_reason"],
        }

    # Non-dict tool result — pass through (no lineage check applicable)
    logger.info("PEP-2 PASSED (non-dict result): tool=%s", tool_name)
    return {
        "gate": "PEP-2",
        "tool_name": tool_name,
        "outcome": PEPOutcome.PASSED,
        "sanitized_result": tool_result,
        "failure_reason": None,
    }


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
