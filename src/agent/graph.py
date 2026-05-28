"""
LangGraph state machine — five-node governance agent.

Graph structure (Framework Section 11):

    Direct edges (deterministic governance boundaries):
        planning → evidence_gathering
        evidence_gathering → sufficiency_assessment
        drafting → awaiting_human_review
        circuit_breaker → END

    Conditional edges (routing functions, LLM-driven within bounds):
        sufficiency_assessment → {evidence_gathering, drafting, circuit_breaker}
        awaiting_human_review  → {END, drafting}

Circuit breakers are checked exclusively in routing functions — not inside
nodes — so they cannot be bypassed by node logic (Framework Section 11.2).

References:
    DL-030: LangGraph selected; PEPs inserted inside execution path
    DL-031: AC-2, AC-3, AC-6, AC-17 demonstration scope
    DL-035: Ephemeral per-run memory — graph state discarded on completion
    Framework Section 4.3: Policy Enforcement Points
    Framework Section 5: Failure Mode Catalog (FM-003, FM-005)
    Framework Section 11: Deterministic vs. Probabilistic Orchestration
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.agent.trust_ledger import TrustLedger, load_trust_ledger

logger = logging.getLogger(__name__)

# ── Circuit breaker thresholds (Framework Section 4.4) ────────────────────────
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "50"))
MAX_EVIDENCE_RETRIES: int = 3

# ── Langfuse client (optional — disabled gracefully if not configured) ─────────
# Langfuse 2.x API: client.trace(session_id=...) → trace.span(name=...) → span.end()
# The client initialises even without credentials (logs a warning but doesn't raise).
# _span() wraps the full trace().span() call and falls back to _NullSpan on any error.
try:
    from langfuse import Langfuse
    _langfuse_client: Optional[Any] = Langfuse()
except Exception as _lf_exc:  # noqa: BLE001
    _langfuse_client = None
    logger.warning("Langfuse import failed — instrumentation disabled: %s", _lf_exc)


class _NullSpan:
    """No-op span returned when Langfuse is not configured or unavailable."""

    def end(self, **kwargs: Any) -> None:  # noqa: ANN401
        pass


def _span(name: str, session_id: str = "", input: Optional[Any] = None) -> Any:
    """
    Create a Langfuse span under a per-run trace, or return a no-op fallback.

    Uses Langfuse 2.x API: client.trace(session_id=run_id).span(name, input).
    Falls back to _NullSpan on any error so instrumentation never breaks the graph.
    """
    if _langfuse_client is None:
        return _NullSpan()
    try:
        trace = _langfuse_client.trace(session_id=session_id or name)
        return trace.span(name=name, input=input)
    except Exception as _exc:  # noqa: BLE001
        logger.debug("Langfuse span creation failed — using NullSpan: %s", _exc)
        return _NullSpan()


def _ts() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _parse_llm_json(text: str) -> Dict[str, Any]:
    """
    Parse JSON from an LLM response, stripping any markdown code fences.

    LLMs sometimes wrap JSON in ```json … ``` even when instructed not to.
    This helper strips the fences before calling json.loads so callers don't
    need to guard against both formats.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Walk backward to find the closing ``` line
        end_idx = len(lines) - 1
        while end_idx > 0 and not lines[end_idx].strip().startswith("```"):
            end_idx -= 1
        text = "\n".join(lines[1:end_idx]).strip()
    return json.loads(text)


# ── Module-level trust ledger (set by build_graph, read by nodes) ─────────────
# Nodes are top-level functions — they cannot close over build_graph()'s local
# trust_ledger variable. A module-level reference is the simplest solution
# without restructuring the entire graph as a class.
_trust_ledger: Optional[Any] = None  # type: TrustLedger, set by build_graph()


# ── Nodes ──────────────────────────────────────────────────────────────────────

def planning_node(state: AgentState) -> AgentState:
    """
    Planning node — decompose the assessment request into evidence requirements.

    Deterministic setup: establishes run scope, initialises evidence containers.
    Probabilistic (TODO — Agent Implementation): LLM decomposes each control
    in controls_to_assess into specific evidence requirements, drawing from
    NIST 800-53 control text retrieved via the trust-layer-rag RAG bridge.

    Framework Section 11.3 — probabilistic reasoning within a bounded state.
    """
    span = _span(
        name="planning",
        session_id=state["run_id"],
        input={
            "run_id": state["run_id"],
            "controls_to_assess": state["controls_to_assess"],
            "declared_control_family": state["declared_control_family"],
            "declared_account_id": state["declared_account_id"],
        },
    )
    try:
        state["current_node"] = "planning"
        state["iteration_count"] = state.get("iteration_count", 0) + 1

        # TODO (Agent Implementation): LLM call — decompose each control in
        #   controls_to_assess into evidence requirements using NIST 800-53
        #   control text from trust-layer-rag. Populate reasoning trace scratchpad.
        # TODO (Agent Implementation): Initialise state["evidence"] with empty
        #   per-control containers: {control_id: []} for each control.
        # TODO (Agent Implementation): Record decomposition rationale in
        #   reasoning trace (Framework Section 3.6 — planning state entry).

        logger.info(
            "planning_node: run_id=%s controls=%s",
            state["run_id"],
            state["controls_to_assess"],
        )
        return state
    finally:
        span.end(output={
            "current_node": state["current_node"],
            "iteration_count": state.get("iteration_count"),
        })


def evidence_gathering_node(state: AgentState) -> AgentState:
    """
    Evidence-gathering node — invoke all three registered tools for each control.

    T-001 (query_iam_policies) and T-004 (search_cloudtrail_events) load from
    local fixtures — always succeed. T-005 (lookup_compliance_requirement) calls
    the P2 RAG bridge — may return FM-002 graceful degradation if P2 is not
    running; evidence from T-001/T-004 is retained regardless.

    PEP-1 and PEP-2 are enforced inside each tool. Outcomes are recorded in
    state["pep_outcomes"] via record_pep_outcome() calls within the tools.

    Evidence from previous retry cycles accumulates — containers are initialized
    with setdefault so existing items are never discarded on retry.

    Deterministic boundary — trust ledger enforces tool permissions.
    Probabilistic — in future iterations, LLM drives query formulation per control.
    """
    span = _span(
        name="evidence_gathering",
        session_id=state["run_id"],
        input={
            "run_id": state["run_id"],
            "evidence_retry_count": state.get("evidence_retry_count", 0),
            "controls_with_evidence": list(state.get("evidence", {}).keys()),
        },
    )
    try:
        state["current_node"] = "evidence_gathering"
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        # Increment retry counter here so it persists in state.
        # Routing functions are read-only in LangGraph — mutations are discarded.
        state["evidence_retry_count"] = state.get("evidence_retry_count", 0) + 1

        if _trust_ledger is None:
            state["errors"].append(
                "evidence_gathering_node: trust ledger not initialized — "
                "call build_graph() before invoking the graph"
            )
            return state

        from src.tools import (  # noqa: PLC0415
            lookup_compliance_requirement,
            query_iam_policies,
            search_cloudtrail_events,
        )

        # Carry forward evidence from prior retries; init containers for all controls.
        evidence: Dict[str, Any] = {
            ctrl: list(items) for ctrl, items in state["evidence"].items()
        }
        for ctrl in state["controls_to_assess"]:
            evidence.setdefault(ctrl, [])

        tool_call_counts = dict(state["tool_call_counts"])
        errors = list(state["errors"])

        # ── T-001: IAM policies (AUTONOMOUS / LOW) ────────────────────────────
        iam_items, iam_errors = query_iam_policies(
            state=state, trust_ledger=_trust_ledger
        )
        tool_call_counts["T-001"] = tool_call_counts.get("T-001", 0) + 1
        for item in iam_items:
            cid = item["control_id"]
            if cid in evidence:
                evidence[cid].append(item)
        errors.extend(iam_errors)

        # ── T-004: CloudTrail events (AUTONOMOUS / LOW) ───────────────────────
        ct_items, ct_errors = search_cloudtrail_events(
            state=state, trust_ledger=_trust_ledger
        )
        tool_call_counts["T-004"] = tool_call_counts.get("T-004", 0) + 1
        for item in ct_items:
            cid = item["control_id"]
            if cid in evidence:
                evidence[cid].append(item)
        errors.extend(ct_errors)

        # ── T-005: Compliance requirements from P2 RAG (one call per control) ─
        # FM-002: P2 unreachable is a degraded condition — log and continue.
        # Missing compliance text is surfaced in sufficiency_results.missing_fields.
        for ctrl in state["controls_to_assess"]:
            req_items, req_errors = lookup_compliance_requirement(
                state=state, trust_ledger=_trust_ledger, control_ids=[ctrl]
            )
            tool_call_counts["T-005"] = tool_call_counts.get("T-005", 0) + 1
            evidence[ctrl].extend(req_items)
            errors.extend(req_errors)

        state["evidence"] = evidence
        state["tool_call_counts"] = tool_call_counts
        state["errors"] = errors

        evidence_counts = {k: len(v) for k, v in evidence.items()}
        logger.info(
            "evidence_gathering_node: run_id=%s counts=%s pep_outcomes=%d errors=%d",
            state["run_id"],
            evidence_counts,
            len(state.get("pep_outcomes", [])),
            len(errors),
        )
        return state
    finally:
        span.end(output={
            "evidence_counts": {
                k: len(v) for k, v in state.get("evidence", {}).items()
            },
            "tool_call_counts": state.get("tool_call_counts", {}),
            "pep_outcomes": len(state.get("pep_outcomes", [])),
        })


def sufficiency_assessment_node(state: AgentState) -> AgentState:
    """
    Sufficiency-assessment node — LLM judges whether collected evidence
    is adequate to support a compliance determination for each control.

    LLM assessment is probabilistic. Gate enforcement is deterministic:
    route_sufficiency() checks that all controls report sufficient=True
    before routing to drafting — the LLM cannot bypass this (FM-005 prevention).

    Evidence with 0 items short-circuits to sufficient=False without an LLM call.
    LLM failures are caught per-control and recorded as sufficient=False with
    a failure_reason, so one bad LLM call cannot silently pass the gate.
    """
    from src.agent.llm import get_llm, invoke_with_logging  # noqa: PLC0415

    span = _span(
        name="sufficiency_assessment",
        session_id=state["run_id"],
        input={
            "run_id": state["run_id"],
            "controls_to_assess": state["controls_to_assess"],
            "evidence_item_counts": {
                k: len(v) for k, v in state.get("evidence", {}).items()
            },
        },
    )
    try:
        state["current_node"] = "sufficiency_assessment"
        state["iteration_count"] = state.get("iteration_count", 0) + 1

        llm = get_llm()
        sufficiency_results: Dict[str, Any] = {}

        _SYSTEM_PROMPT = (
            "You are a federal compliance assessor evaluating whether collected "
            "evidence is sufficient to assess a NIST 800-53 control.\n\n"
            "For each control, evaluate:\n"
            "1. Is there at least one IAM policy document showing role permissions?\n"
            "2. Is there at least one CloudTrail event showing access activity?\n"
            "3. Does the evidence clearly address the control's key requirements?\n"
            "4. Does the evidence cover the control's key requirements?\n\n"
            "Important: Sufficient means there is enough evidence to make a compliance "
            "determination — including a NON-COMPLIANT determination. A documented "
            "compliance gap, violation, or finding IS sufficient evidence. Do not require "
            "evidence of compliance to mark evidence as sufficient.\n\n"
            "Respond in JSON only — no markdown fences, no prose before or after:\n"
            '{"sufficient": true or false, '
            '"missing_fields": ["list of what is missing, or [] if sufficient"], '
            '"rationale": "one sentence explanation"}'
        )

        for control_id in state["controls_to_assess"]:
            evidence_items = state["evidence"].get(control_id, [])

            # Short-circuit: no evidence → insufficient, no LLM call needed
            if not evidence_items:
                sufficiency_results[control_id] = {
                    "control_id": control_id,
                    "sufficient": False,
                    "evidence_count": 0,
                    "missing_fields": [
                        "iam_policy", "cloudtrail_event", "compliance_requirement"
                    ],
                    "rationale": "No evidence collected for this control.",
                }
                continue

            evidence_summary = "\n\n".join(
                f"Source: {item['source_uri']}\n{item['text'][:500]}"
                for item in evidence_items[:6]
            )

            user_prompt = (
                f"Control: {control_id}\n\n"
                f"Evidence collected ({len(evidence_items)} items):\n\n"
                f"{evidence_summary}\n\n"
                f"Is this evidence sufficient to assess {control_id}? "
                "Respond in JSON only."
            )

            try:
                response_text, _ = invoke_with_logging(
                    llm=llm,
                    system_prompt=_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    run_id=state["run_id"],
                    node_name=f"sufficiency_{control_id}",
                )
                result = _parse_llm_json(response_text)
                sufficiency_results[control_id] = {
                    "control_id": control_id,
                    "sufficient": bool(result.get("sufficient", False)),
                    "evidence_count": len(evidence_items),
                    "missing_fields": result.get("missing_fields", []),
                    "rationale": result.get("rationale", ""),
                }
            except Exception as exc:
                logger.error(
                    "sufficiency_assessment_node: LLM error for %s run_id=%s: %s",
                    control_id, state["run_id"], exc,
                )
                sufficiency_results[control_id] = {
                    "control_id": control_id,
                    "sufficient": False,
                    "evidence_count": len(evidence_items),
                    "missing_fields": ["llm_assessment_failed"],
                    "rationale": f"Sufficiency assessment error: {exc}",
                }

        state["sufficiency_results"] = sufficiency_results
        all_sufficient = all(
            r.get("sufficient", False) for r in sufficiency_results.values()
        )
        logger.info(
            "sufficiency_assessment_node: run_id=%s all_sufficient=%s results=%s",
            state["run_id"],
            all_sufficient,
            {k: v.get("sufficient") for k, v in sufficiency_results.items()},
        )
        return state
    finally:
        span.end(output={
            "sufficiency_results": {
                k: v.get("sufficient")
                for k, v in state.get("sufficiency_results", {}).items()
            },
        })


def drafting_node(state: AgentState) -> AgentState:
    """
    Drafting node — produce the assessment artifact with full evidence lineage.

    Output is a draft. Human review is mandatory before submission — enforced
    as a direct edge to awaiting_human_review (Framework Section 11.2).
    The agent cannot route around this edge regardless of its reasoning output.
    """
    span = _span(
        name="drafting",
        session_id=state["run_id"],
        input={
            "run_id": state["run_id"],
            "sufficiency_results": state.get("sufficiency_results", {}),
            "approval_status": state.get("approval_status"),
        },
    )
    try:
        state["current_node"] = "drafting"
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        state["approval_required"] = True

        # TODO (Agent Implementation): LLM generates draft assessment markdown.
        #   Each finding: control_id, determination, evidence citations
        #   (source_uri + evidence_hash), compliance status.
        # TODO (Agent Implementation): Run PEP-3 pre-output checks:
        #   a. Evidence completeness — every assertion has lineage fields.
        #   b. Sufficiency assertion present for every control.
        #   c. human_review_required flag set.
        #   d. Submission gate not bypassed.
        # TODO (Agent Implementation): Populate state["draft_assessment"] (md)
        #   and state["draft_timestamp"].

        state["draft_timestamp"] = _ts()
        logger.info(
            "drafting_node: run_id=%s approval_required=%s",
            state["run_id"],
            state["approval_required"],
        )
        return state
    finally:
        span.end(output={
            "draft_timestamp": state.get("draft_timestamp"),
            "approval_required": state.get("approval_required"),
        })


def awaiting_human_review_node(state: AgentState) -> AgentState:
    """
    Awaiting-human-review node — gate artifact behind Authorizing Official approval.

    The approval token is validated here via PEP-1 (HUMAN_GATED check for
    submit_assessment_artifact). The run suspends until a token is provided
    externally. Re-invoke the graph with an updated state to resume.

    Routing (route_human_review):
        APPROVED → END     (governance decision record written)
        REJECTED → drafting (redraft with rejection reason)
        PENDING  → END     (re-invoke when token arrives)
    """
    span = _span(
        name="awaiting_human_review",
        session_id=state["run_id"],
        input={
            "run_id": state["run_id"],
            "approval_status": state.get("approval_status", "PENDING"),
            "approver_role": state.get("approver_role"),
        },
    )
    try:
        state["current_node"] = "awaiting_human_review"

        if not state.get("approval_status"):
            state["approval_status"] = "PENDING"

        # TODO (Agent Implementation): Validate approval token authenticity and
        #   approver_role against trust ledger T-002 required_approver_role.
        # TODO (Agent Implementation): Write governance_decision.json artifact:
        #   run_id, initiating_principal, tool invocations, PEP outcomes,
        #   approval event (token, role, timestamp).
        # TODO (Agent Implementation): If REJECTED, record rejection reason and
        #   open questions in state for the redraft cycle.

        logger.info(
            "awaiting_human_review_node: run_id=%s status=%s",
            state["run_id"],
            state.get("approval_status"),
        )
        return state
    finally:
        span.end(output={
            "approval_status": state.get("approval_status"),
            "approval_timestamp": state.get("approval_timestamp"),
        })


def circuit_breaker_node(state: AgentState) -> AgentState:
    """
    Circuit breaker terminal node — safe termination on limit exceeded.

    Produces a documented terminal state. All evidence collected up to
    the circuit breaker event is retained in state for audit purposes.
    The run does not continue after this node (direct edge to END).
    """
    span = _span(
        name="circuit_breaker",
        session_id=state["run_id"],
        input={
            "run_id": state["run_id"],
            "iteration_count": state.get("iteration_count"),
            "evidence_retry_count": state.get("evidence_retry_count"),
        },
    )
    try:
        state["current_node"] = "circuit_breaker"
        state["circuit_breaker_fired"] = True

        if not state.get("circuit_breaker_reason"):
            if state.get("iteration_count", 0) >= MAX_ITERATIONS:
                state["circuit_breaker_reason"] = (
                    f"MAX_ITERATIONS={MAX_ITERATIONS} exceeded"
                )
            elif state.get("evidence_retry_count", 0) >= MAX_EVIDENCE_RETRIES:
                state["circuit_breaker_reason"] = (
                    f"MAX_EVIDENCE_RETRIES={MAX_EVIDENCE_RETRIES} exceeded"
                )
            else:
                state["circuit_breaker_reason"] = "circuit_breaker_fired by node"

        logger.error(
            "circuit_breaker_node: run_id=%s reason=%s",
            state["run_id"],
            state["circuit_breaker_reason"],
        )
        return state
    finally:
        span.end(output={
            "circuit_breaker_reason": state.get("circuit_breaker_reason"),
        })


# ── Routing functions (deterministic governance boundaries) ────────────────────

def route_sufficiency(state: AgentState) -> str:
    """
    Route from sufficiency_assessment node.

    Circuit breakers checked first — before any reasoning-based routing.
    This is a deterministic boundary: the LLM cannot influence whether a
    circuit breaker fires (Framework Section 11.2).

    Returns:
        "circuit_breaker"    — MAX_ITERATIONS or MAX_EVIDENCE_RETRIES exceeded
        "drafting"           — all controls report sufficient=True
        "evidence_gathering" — one or more controls insufficient; retry
    """
    # Circuit breaker: max iterations (FM-003)
    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        logger.error(
            "route_sufficiency: MAX_ITERATIONS=%d reached run_id=%s",
            MAX_ITERATIONS,
            state["run_id"],
        )
        return "circuit_breaker"

    # Circuit breaker: max evidence retries
    if state.get("evidence_retry_count", 0) >= MAX_EVIDENCE_RETRIES:
        logger.error(
            "route_sufficiency: MAX_EVIDENCE_RETRIES=%d reached run_id=%s",
            MAX_EVIDENCE_RETRIES,
            state["run_id"],
        )
        return "circuit_breaker"

    # Check node-set circuit_breaker_fired flag
    if state.get("circuit_breaker_fired"):
        return "circuit_breaker"

    # Governance gate: all controls must be sufficient (FM-005).
    # The LLM determines sufficiency in the node; the routing function
    # enforces that the threshold is met before drafting begins.
    sufficiency = state.get("sufficiency_results", {})
    controls = state.get("controls_to_assess", [])
    all_sufficient = all(
        sufficiency.get(ctrl, {}).get("sufficient", False)
        for ctrl in controls
    )

    if all_sufficient:
        return "drafting"

    # Insufficient — loop back; retry count is incremented inside evidence_gathering_node
    return "evidence_gathering"


def route_human_review(state: AgentState) -> str:
    """
    Route from awaiting_human_review node.

    Deterministic boundary: approval_status drives routing exclusively.
    PENDING terminates the run; the graph is re-invoked when a token arrives.

    Returns:
        "end"      — APPROVED (write governance decision record) or PENDING
        "drafting" — REJECTED (redraft with rejection reason)
    """
    status = state.get("approval_status", "PENDING")
    if status == "APPROVED":
        logger.info(
            "route_human_review: APPROVED run_id=%s approver=%s",
            state["run_id"],
            state.get("approver_role"),
        )
        return "end"
    if status == "REJECTED":
        logger.info(
            "route_human_review: REJECTED run_id=%s — routing to drafting",
            state["run_id"],
        )
        return "drafting"
    # PENDING: suspend run; re-invoke graph when approval token is provided
    logger.info(
        "route_human_review: PENDING run_id=%s — run suspended",
        state["run_id"],
    )
    return "end"


# ── Graph construction ─────────────────────────────────────────────────────────

def build_graph(trust_ledger: TrustLedger) -> Any:
    """
    Build and compile the LangGraph state machine.

    Sets the module-level _trust_ledger reference so that evidence_gathering_node
    and sufficiency_assessment_node can access it without LangGraph config threading.

    Direct edges (unconditional — Framework Section 11.2):
        planning            → evidence_gathering
        evidence_gathering  → sufficiency_assessment
        drafting            → awaiting_human_review
        circuit_breaker     → END

    Conditional edges (routing functions — Framework Section 11.3):
        sufficiency_assessment → {evidence_gathering, drafting, circuit_breaker}
        awaiting_human_review  → {END, drafting}
    """
    global _trust_ledger
    _trust_ledger = trust_ledger

    graph: StateGraph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("planning", planning_node)
    graph.add_node("evidence_gathering", evidence_gathering_node)
    graph.add_node("sufficiency_assessment", sufficiency_assessment_node)
    graph.add_node("drafting", drafting_node)
    graph.add_node("awaiting_human_review", awaiting_human_review_node)
    graph.add_node("circuit_breaker", circuit_breaker_node)

    # Entry point
    graph.set_entry_point("planning")

    # Direct edges — deterministic, unconditional
    graph.add_edge("planning", "evidence_gathering")
    graph.add_edge("evidence_gathering", "sufficiency_assessment")
    graph.add_edge("drafting", "awaiting_human_review")
    graph.add_edge("circuit_breaker", END)

    # Conditional edges — routing functions
    graph.add_conditional_edges(
        "sufficiency_assessment",
        route_sufficiency,
        {
            "evidence_gathering": "evidence_gathering",
            "drafting": "drafting",
            "circuit_breaker": "circuit_breaker",
        },
    )
    graph.add_conditional_edges(
        "awaiting_human_review",
        route_human_review,
        {
            "end": END,
            "drafting": "drafting",
        },
    )

    logger.info(
        "Graph compiled: %d nodes, trust_ledger schema_version=%s",
        6,
        trust_ledger.schema_version,
    )
    return graph.compile()


def create_graph(ledger_path: str = "config/trust_ledger.yaml") -> Any:
    """
    Load the trust ledger and build the compiled graph.

    Entry point for scripts/run_agent.py and test harnesses.
    Raises FileNotFoundError if the trust ledger is missing.
    """
    ledger = load_trust_ledger(ledger_path)
    return build_graph(ledger)
