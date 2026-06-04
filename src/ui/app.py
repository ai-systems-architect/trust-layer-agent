"""
Streamlit UI for the Trust Layer governed compliance agent.

Demonstrates the governed AC-family assessment workflow with the
human approval gate as the centerpiece interaction.

The agent runs in a background thread; the UI polls for updates via
a threading.Queue and reruns every second during execution.

Usage:
    streamlit run src/ui/app.py --server.port 8501
    Or: bash scripts/run_ui.sh
"""

from __future__ import annotations

import json
import queue as queuelib
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path before src.* imports.
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

import httpx  # noqa: E402
import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────

ALL_CONTROLS = ["AC-2", "AC-3", "AC-6", "AC-17"]
OUTPUTS_DIR = _ROOT / "outputs"

# Graph node keys (as set by each node in state["current_node"]) and their
# human-readable labels. Includes circuit_breaker as a non-happy-path outcome.
NODE_ORDER = [
    "planning",
    "evidence_gathering",
    "sufficiency_assessment",
    "drafting",
    "awaiting_human_review",
]
NODE_LABELS = {
    "planning": "Planning",
    "evidence_gathering": "Evidence Gathering",
    "sufficiency_assessment": "Sufficiency Assessment",
    "drafting": "Drafting",
    "awaiting_human_review": "Awaiting Human Review",
    "circuit_breaker": "Circuit Breaker",
}

# ── Session state ──────────────────────────────────────────────────────────────


def _init_session_state() -> None:
    defaults: dict = {
        "run_status": "idle",   # idle | running | completed | error
        "run_id": None,
        "run_thread": None,
        "update_queue": None,
        "completed_nodes": [],  # list of node_key strings in completion order
        "current_state": {},    # accumulated merged state from all node updates
        "error_message": "",
        "p2_online": None,      # None = not yet checked
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Background agent thread ────────────────────────────────────────────────────


def _make_initial_state(
    controls: list[str], account_id: str, run_id: str
) -> dict:
    return {
        "run_id": run_id,
        "initiating_principal": "ui-user",
        "declared_control_family": "AC",
        "declared_account_id": account_id,
        "controls_to_assess": controls,
        "run_start_time": datetime.now(timezone.utc).isoformat(),
        "evidence": {},
        "sufficiency_results": {},
        "evidence_retry_count": 0,
        "draft_assessment": None,
        "draft_timestamp": None,
        "approval_required": False,
        "approval_token": None,
        "approval_status": None,
        "approver_role": None,
        "approval_timestamp": None,
        "pep_outcomes": [],
        "tool_call_counts": {},
        "iteration_count": 0,
        "circuit_breaker_fired": False,
        "circuit_breaker_reason": None,
        "errors": [],
        "current_node": "",
    }


def _agent_thread(
    initial_state: dict, update_q: queuelib.Queue
) -> None:
    """
    Background thread: stream agent execution and post node updates.

    LangGraph stream_mode="updates" yields {node_name: delta_state} after
    each node completes. We post each update to the queue for the main
    Streamlit thread to drain on the next poll cycle.
    """
    try:
        from src.agent.graph import create_graph  # noqa: PLC0415
        graph = create_graph()
        accumulated: dict = dict(initial_state)

        for update in graph.stream(
            initial_state,
            config={"recursion_limit": 100},
        ):
            # update is {node_name: {delta_state}} in "updates" mode
            if not isinstance(update, dict):
                continue
            for node_name, delta in update.items():
                if node_name.startswith("__"):
                    continue  # skip LangGraph internal markers
                if isinstance(delta, dict):
                    accumulated.update(delta)
                update_q.put(("update", {
                    "node": node_name,
                    "delta": delta if isinstance(delta, dict) else {},
                    "accumulated": dict(accumulated),
                }))

        update_q.put(("done", dict(accumulated)))
    except Exception as exc:  # noqa: BLE001
        update_q.put(("error", str(exc)))


def _start_run(controls: list[str], account_id: str) -> None:
    """Initialise session state and start the background agent thread."""
    run_id = str(uuid.uuid4())
    q: queuelib.Queue = queuelib.Queue()
    initial_state = _make_initial_state(controls, account_id, run_id)

    thread = threading.Thread(
        target=_agent_thread,
        args=(initial_state, q),
        daemon=True,
    )

    st.session_state.run_status = "running"
    st.session_state.run_id = run_id
    st.session_state.update_queue = q
    st.session_state.run_thread = thread
    st.session_state.completed_nodes = []
    st.session_state.current_state = {}
    st.session_state.error_message = ""

    thread.start()


def _drain_queue() -> None:
    """Drain pending queue messages into session state (called on each rerun)."""
    q = st.session_state.update_queue
    if q is None:
        return

    while not q.empty():
        try:
            msg_type, payload = q.get_nowait()
        except queuelib.Empty:
            break

        if msg_type == "update":
            node_name = payload.get("node", "")
            # Strip "_node" suffix to match NODE_ORDER / NODE_LABELS keys
            node_key = node_name.removesuffix("_node")
            if node_key and node_key not in st.session_state.completed_nodes:
                st.session_state.completed_nodes.append(node_key)
            # Merge accumulated state
            accumulated = payload.get("accumulated", {})
            if accumulated:
                st.session_state.current_state = accumulated

        elif msg_type == "done":
            st.session_state.run_status = "completed"
            if payload:
                st.session_state.current_state = payload

        elif msg_type == "error":
            st.session_state.run_status = "error"
            st.session_state.error_message = str(payload)


# ── P2 health check ────────────────────────────────────────────────────────────


def _check_p2() -> bool:
    try:
        resp = httpx.get("http://localhost:8000/health", timeout=3.0)
        return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False


# ── File helpers ───────────────────────────────────────────────────────────────


def _read_governance_decision(run_id: str) -> dict | None:
    path = OUTPUTS_DIR / f"governance_decision_{run_id}.json"
    if path.exists():
        with open(path) as fh:
            return json.load(fh)
    return None


def _read_draft_assessment(run_id: str) -> str | None:
    path = OUTPUTS_DIR / f"draft_assessment_{run_id}.md"
    return path.read_text() if path.exists() else None


def _approve_run(run_id: str) -> None:
    path = OUTPUTS_DIR / f"governance_decision_{run_id}.json"
    if path.exists():
        with open(path) as fh:
            doc = json.load(fh)
        doc["approval_status"] = "APPROVED"
        doc["approver_id"] = "ui-user"
        doc["decision_timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as fh:
            json.dump(doc, fh, indent=2)
    st.session_state.current_state["approval_status"] = "APPROVED"


def _reset_run() -> None:
    st.session_state.run_status = "idle"
    st.session_state.run_id = None
    st.session_state.run_thread = None
    st.session_state.update_queue = None
    st.session_state.completed_nodes = []
    st.session_state.current_state = {}
    st.session_state.error_message = ""


# ── UI sections ────────────────────────────────────────────────────────────────


def _render_sidebar() -> tuple[list[str], str]:
    with st.sidebar:
        st.header("Run Configuration")
        st.caption("Select controls and account scope.")

        controls = [
            ctrl for ctrl in ALL_CONTROLS
            if st.checkbox(ctrl, value=True, key=f"ctrl_{ctrl}")
        ]

        account_id = st.text_input(
            "Account ID", value="123456789", key="account_id"
        )

        # P2 status — check once per session
        if st.session_state.p2_online is None:
            st.session_state.p2_online = _check_p2()

        if st.session_state.p2_online:
            st.success("P2 RAG service: Online")
        else:
            st.warning("P2 RAG service: Offline — FM-002 degradation mode")

        st.divider()

        is_running = st.session_state.run_status == "running"
        if st.button(
            "🚀 Run Assessment",
            disabled=is_running,
            use_container_width=True,
            type="primary",
        ):
            if not controls:
                st.error("Select at least one control.")
            else:
                _start_run(controls, account_id)
                st.rerun()

        if st.session_state.run_status != "idle":
            if st.button("↩ New Run", use_container_width=True):
                _reset_run()
                st.rerun()

    return controls, account_id


def _render_status_panel() -> None:
    state = st.session_state.current_state
    completed = st.session_state.completed_nodes
    run_status = st.session_state.run_status

    st.subheader("Agent Status")

    for node_key in NODE_ORDER:
        label = NODE_LABELS[node_key]

        if node_key in completed:
            with st.expander(f"✅ {label}", expanded=False):
                if node_key == "evidence_gathering":
                    evidence = state.get("evidence", {})
                    pep_count = len(state.get("pep_outcomes", []))
                    counts = {k: len(v) for k, v in evidence.items()}
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.json(counts, expanded=False)
                    with col_b:
                        st.metric("PEP Outcomes", pep_count)

                elif node_key == "sufficiency_assessment":
                    sufficiency = state.get("sufficiency_results", {})
                    for ctrl, res in sufficiency.items():
                        icon = "✅" if res.get("sufficient") else "❌"
                        rationale = (res.get("rationale") or "")[:80]
                        st.write(f"{icon} **{ctrl}** — {rationale}")

                elif node_key == "drafting":
                    draft_len = len(state.get("draft_assessment") or "")
                    st.metric("Draft length", f"{draft_len:,} chars")

                elif node_key == "awaiting_human_review":
                    st.caption(
                        f"Approval status: {state.get('approval_status', 'PENDING')}"
                    )
        elif run_status == "running":
            # Infer active node: the first in NODE_ORDER not yet completed
            next_node = next(
                (n for n in NODE_ORDER if n not in completed), None
            )
            if node_key == next_node:
                st.info(f"⏳ {label} — running…")
            else:
                st.text(f"⬜ {label}")
        else:
            st.text(f"⬜ {label}")

    # Circuit breaker — non-happy-path terminal
    if "circuit_breaker" in completed:
        reason = state.get("circuit_breaker_reason", "unknown")
        st.error(f"🔴 Circuit Breaker fired: {reason}")


def _render_draft_panel() -> None:
    state = st.session_state.current_state
    run_id = st.session_state.run_id

    draft = state.get("draft_assessment") or _read_draft_assessment(run_id)
    if not draft:
        return

    st.subheader("Draft Assessment")
    with st.expander("View Draft", expanded=True):
        st.markdown(draft)

    st.download_button(
        label="⬇ Download Draft (.md)",
        data=draft,
        file_name=f"draft_assessment_{run_id}.md",
        mime="text/markdown",
    )


def _render_governance_panel() -> None:
    state = st.session_state.current_state
    if not state:
        return

    st.subheader("Governance Decision")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Risk Tier", "HIGH")
    with col2:
        st.metric("Autonomy Class", "HUMAN_GATED")
    with col3:
        st.metric("PEP Outcomes", len(state.get("pep_outcomes", [])))
    with col4:
        errors = [
            e for e in state.get("errors", [])
            if "P2 unreachable" not in e and "FM-002" not in e
        ]
        st.metric("Errors", len(errors))

    # Evidence lineage summary — one row per control
    evidence = state.get("evidence", {})
    if evidence:
        st.caption("Evidence lineage")
        rows = []
        for ctrl, items in evidence.items():
            tool_ids = sorted(set(i.get("tool_id", "?") for i in items))
            rows.append({
                "Control": ctrl,
                "Items": len(items),
                "Tools": ", ".join(tool_ids),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_approval_gate() -> None:
    state = st.session_state.current_state
    run_id = st.session_state.run_id
    approval_status = state.get("approval_status")

    if approval_status == "PENDING":
        st.subheader("🔐 Human Approval Gate")
        st.info(
            "Assessment is suspended pending Authorizing Official review. "
            "Review the draft above before approving."
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ APPROVE",
                type="primary",
                use_container_width=True,
            ):
                _approve_run(run_id)
                st.rerun()
        with col2:
            if st.button(
                "❌ REJECT — Re-run",
                use_container_width=True,
            ):
                _reset_run()
                st.rerun()

    elif approval_status == "APPROVED":
        st.success("✅ Assessment APPROVED — governance decision finalised.")

        gov_doc = _read_governance_decision(run_id)
        if gov_doc:
            st.download_button(
                label="⬇ Download Governance Decision (.json)",
                data=json.dumps(gov_doc, indent=2),
                file_name=f"governance_decision_{run_id}.json",
                mime="application/json",
                type="primary",
            )


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(
        page_title="Trust Layer Agent",
        page_icon="🔐",
        layout="wide",
    )
    st.title("🔐 Trust Layer — Governed Compliance Agent")
    st.caption(
        "NIST 800-53 AC-Family Assessment | "
        "LangGraph state machine | "
        "Human-in-the-Loop governance"
    )

    _init_session_state()
    _render_sidebar()

    run_status = st.session_state.run_status

    if run_status == "idle":
        st.info(
            "Select controls and click **Run Assessment** to begin. "
            "The agent collects IAM and CloudTrail evidence, "
            "assesses sufficiency, drafts the compliance report, "
            "and suspends at the human approval gate."
        )
        return

    # Drain any pending updates from the background thread.
    _drain_queue()

    # Re-read run_status after drain (may have changed to "completed").
    run_status = st.session_state.run_status

    col_left, col_right = st.columns([1, 2])

    with col_left:
        _render_status_panel()

        if run_status == "error":
            st.error(
                f"Agent error: {st.session_state.get('error_message', 'unknown')}"
            )

    with col_right:
        if run_status in ("running", "completed"):
            state = st.session_state.current_state
            if state.get("draft_assessment"):
                _render_draft_panel()
                _render_governance_panel()
                _render_approval_gate()
            elif run_status == "running":
                st.info("Draft will appear here once the drafting node completes.")

    # Poll every second while the background thread is active.
    if run_status == "running":
        time.sleep(1)
        st.rerun()


if __name__ == "__main__":
    main()
