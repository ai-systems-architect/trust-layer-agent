"""
Agent state schema — ephemeral per-run TypedDict.

Every field is scoped to a single run. No state persists across runs (DL-035).
The state dict is the only memory the agent has during execution; it is
initialized at run start and discarded on completion.

References:
    DL-035: Memory Architecture — ephemeral per-run, no cross-run persistence
    Framework Section 3: Agent Identity and Delegated Authority
    Framework Section 3.6: Reasoning Trace Requirements
    Framework Section 4: Tool-Use Governance and Policy Enforcement Points
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing import TypedDict


class AgentState(TypedDict):
    """
    Ephemeral run-scoped state for the governance agent.

    Fields are grouped by concern. All fields must be populated in the
    initial state dict passed to graph.invoke(). See scripts/run_agent.py.
    """

    # ── Run identity ──────────────────────────────────────────────────────
    # Declared at invocation; fixed for the duration of the run (DL-035).
    run_id: str
    initiating_principal: str
    declared_control_family: str
    declared_account_id: str
    controls_to_assess: List[str]
    run_start_time: str  # ISO 8601 UTC

    # ── Evidence ──────────────────────────────────────────────────────────
    # evidence: keyed by control_id. Each value is a list of evidence items.
    # Each item carries source_uri, retrieval_timestamp, evidence_hash (PEP-2).
    evidence: Dict[str, List[Dict[str, Any]]]
    # sufficiency_results: keyed by control_id.
    # Each value: {"sufficient": bool, "rationale": str, "gaps": List[str]}
    sufficiency_results: Dict[str, Dict[str, Any]]
    evidence_retry_count: int  # incremented by route_sufficiency on retry

    # ── Draft output ──────────────────────────────────────────────────────
    draft_assessment: Optional[str]   # markdown — populated in drafting node
    draft_timestamp: Optional[str]    # ISO 8601 UTC

    # ── Human gate ────────────────────────────────────────────────────────
    # approval_status: APPROVED | REJECTED | PENDING
    approval_required: bool
    approval_token: Optional[str]
    approval_status: Optional[str]
    approver_role: Optional[str]
    approval_timestamp: Optional[str]  # ISO 8601 UTC

    # ── Governance instrumentation ────────────────────────────────────────
    # pep_outcomes: list of PEP result dicts appended on every gate check.
    pep_outcomes: List[Dict[str, Any]]
    # tool_call_counts: {tool_name: count} — checked against max_calls_per_run.
    tool_call_counts: Dict[str, int]
    iteration_count: int         # incremented at entry of every node
    circuit_breaker_fired: bool
    circuit_breaker_reason: Optional[str]

    # ── Error tracking ────────────────────────────────────────────────────
    errors: List[str]

    # ── Current position ──────────────────────────────────────────────────
    current_node: str
