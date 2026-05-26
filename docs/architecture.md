# Architecture — The Trust Layer for Enterprise Agentic AI

High-level system design. For why each component was chosen over alternatives,
see [decision_log.md](decision_log.md). For the governance pattern this
architecture implements, see [framework.md](framework.md).

---

## Status

**Phase 1 stub.** The governance framework (`framework.md`) is the active
deliverable; the agent implementation under `src/` follows in Agent Implementation. The
section headers below are commitments to address each topic as the agent
is built.

---

## Overview

(Drafted in Agent Implementation.) The agent is a single-agent LangGraph state machine
(candidate — see decision log) that drafts NIST 800-53 Access Control
evidence assessments from synthetic IAM and CloudTrail fixtures. Every
tool call is gated by the trust ledger (`config/trust_ledger.yaml`);
every state transition is captured in a reasoning trace; every assessment
artifact is bound to its evidence lineage and a human-approver token.

---

## State Machine

The agent's explicit states:

- `planning` — decompose the control assessment request into specific evidence
  requirements drawn from the framework document and 800-53 control text.
- `evidence-gathering` — call evidence tools, collect citations, store
  intermediate evidence in the reasoning trace.
- `sufficiency-assessment` — judge whether collected evidence supports an
  assessment; loop back to `evidence-gathering` with refined queries if not.
- `drafting` — produce the draft assessment artifact with full citation trail
  back to evidence sources.
- `awaiting-human-review` — gate the artifact behind an Authorizing Official
  (or delegate) approval token before any submission.

(State transition diagram and per-state PEP bindings drafted in Agent Implementation.)

---

## Tool Inventory

All tools are declared in `config/trust_ledger.yaml`. Tools not in the ledger
are implicitly denied. Initial set demonstrates the full trust class spectrum:

| Tool | Risk Tier | Autonomy Class | Purpose |
|---|---|---|---|
| `query_iam_policies` | LOW | AUTONOMOUS | Read IAM policy documents for AC-family evidence |
| `submit_assessment_artifact` | HIGH | HUMAN_GATED | Write draft assessment to designated output store; requires Authorizing Official token |
| `modify_iam_policy` | CRITICAL | DENIED | Registered solely to demonstrate denial enforcement at the pre-call PEP |

Tools added in Agent Implementation:

- `search_cloudtrail_events` — query synthetic CloudTrail fixture set; supports the AC-2 and AC-6 evidence streams (dormant credentials, over-privileged actions).
- `lookup_compliance_requirement` — calls upstream [trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag) retrieval for the relevant NIST 800-53 control text. This is the explicit P2 → P3 architectural bridge: the agent consumes governed RAG rather than reimplementing retrieval.

---

## Identity and Delegated Authority

Execution identity is declared in `config/trust_ledger.yaml`:

- **IAM role:** `audit-readonly-role`
- **Privilege scope:** read-only
- **Credential source:** short-lived session
- **Impersonation:** disallowed

Mocked role assumption is in scope for Agent Implementation — the agent will simulate
assuming the role, the ledger will validate the role binding, and a deliberate
out-of-scope action (e.g., attempting to call `iam:CreateUser`) will be
rejected at the pre-call PEP to demonstrate the enforcement path.

Wiring to a real AWS STS session is production work, not portfolio work.
See [README — Future Work](../README.md#future-work).

---

## Policy Enforcement Points

Three PEPs are bound per tool in the trust ledger:

1. **`pre_call`** — argument inspection, authority check, trust-class gate
   against the ledger. Examples: `validate_scope_bounds` (T-001),
   `require_human_approval_token` (T-002), `reject_log_and_alert` (T-003).
2. **`post_call`** — output inspection for sensitive data, injected instructions,
   schema violations. Examples: `sanitize_account_identifiers` (T-001),
   `log_submission_event` (T-002).
3. **`pre_output_release`** — final gate before any artifact reaches the user
   or an external system. Binds to the human-review step of the state machine.

PEP handler functions are bound by name in the ledger; implementations land
under `src/peps/` in Agent Implementation.

---

## Reasoning Trace

(Drafted in Agent Implementation.) Langfuse-backed instrumentation on every state transition
and every tool call. Initial capture set:

- Input and output tokens per state and per tool call.
- State transition latency.
- Tool call frequency, failure rates, and PEP outcomes (passed / blocked / sanitized).
- Evidence lineage hash chain from retrieval through assessment artifact.

Trace fidelity must be sufficient to reconstruct any agent run for after-the-fact
audit. Retention and access controls on the trace store are governed by
[framework.md § Reasoning Trace Requirements](framework.md).

---

## Evaluation

(Drafted in Evaluation Suite — see [framework.md § Evaluation Methodology](framework.md).)

Three independent evaluation tiers, complementary by design:

- **Code-based graders** — deterministic assertions (refusal fired, citation
  present, PEP blocked the action, evidence lineage hash matches).
- **LLM-as-judge** — qualitative grading where determinism is wrong (was a
  compliance hedge justified given the retrieved evidence?).
- **Human review** — edge cases, high-stakes outputs, and disagreements
  between the first two tiers.

---

## Repository Structure

```
trust-layer-agent/
├── README.md                    Project overview, status, future work
├── LICENSE.md                   MIT
├── config/
│   └── trust_ledger.yaml        Tool registry: risk tier, autonomy, PEPs, lineage
├── docs/
│   ├── architecture.md          This file
│   ├── framework.md             Governance framework (Phase 1 deliverable)
│   ├── decision_log.md          DL-030 onwards (continues from trust-layer-rag)
│   ├── agent_risk_classification_matrix.md
│   └── examples/
│       └── governance_decision.json
├── src/                         Agent implementation
└── eval/                        Three-tier graders
```
