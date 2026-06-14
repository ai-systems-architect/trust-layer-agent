# Architecture — trust-layer-agent

## Overview

`trust-layer-agent` implements the reasoning and action governance layer of the Trust Layer
portfolio. It demonstrates governed agentic AI for federal compliance workflows — a LangGraph
agent instrumented against a governance framework that enforces tool permissions, evidence
lineage, and human oversight at the state machine level.

---

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit UI  (:8501)                       │
│        Run config → Live status → Draft review → Approve/Reject │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      trust-layer-agent                          │
│                                                                 │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │   trust_    │   │   LangGraph  │   │  Langfuse Cloud  │    │
│  │ ledger.yaml │──►│    State     │──►│  Traces + Tokens │    │
│  │  5 tools    │   │   Machine    │   │  Per-node spans  │    │
│  │  PEP rules  │   │   5 nodes    │   └──────────────────┘    │
│  └─────────────┘   └──────┬───────┘                           │
│                            │                                    │
│             ┌──────────────┼──────────────────┐               │
│             ▼              ▼                  ▼               │
│    ┌────────────┐  ┌─────────────┐  ┌──────────────────┐     │
│    │   T-001    │  │    T-004    │  │      T-005       │     │
│    │ IAM Policy │  │ CloudTrail  │  │  Compliance RAG  │     │
│    │  Fixtures  │  │  Fixtures   │  │  POST /retrieve  │     │
│    │  LOW/AUTO  │  │  LOW/AUTO   │  │    LOW/AUTO      │     │
│    └────────────┘  └─────────────┘  └────────┬─────────┘     │
└───────────────────────────────────────────────┼───────────────┘
                                                │ HTTP
┌───────────────────────────────────────────────▼───────────────┐
│                     trust-layer-rag  (:8000)                  │
│   Presidio PII scrub → pgvector HNSW + BM25 → Cohere rerank  │
│   Bedrock Guardrails → Evidence chunks with lineage metadata  │
└───────────────────────────────────────────────────────────────┘

Output artifacts (outputs/):
  governance_decision_{run_id}.json  — runtime audit record
  draft_assessment_{run_id}.md       — cited compliance assessment
```

---

## Agent State Machine

```
┌─────────────┐
│   planning  │  Validates scope, initializes evidence buckets
└──────┬──────┘
       │ direct edge
┌──────▼──────────┐
│   evidence_     │  T-001 IAM + T-004 CloudTrail + T-005 P2 RAG
│   gathering     │  PEP-1 (pre-call) → execute → PEP-2 (post-call)
└──────┬──────────┘
       │ conditional edge
┌──────▼──────────┐  insufficient  ┌──────────────────┐
│   sufficiency_  │ ──────────────►│   evidence_      │
│   assessment    │                │   gathering(retry)│
└──────┬──────────┘                └──────────────────┘
       │ sufficient (all controls)
       │  MAX_RETRIES → circuit_breaker
┌──────▼──────┐
│   drafting  │  Bedrock LLM → markdown assessment + citations
└──────┬──────┘
       │ direct edge
┌──────▼──────────────┐
│   awaiting_human_   │  HUMAN_GATED — run suspended
│   review            │  governance_decision.json written
└──────┬──────────────┘
       │ APPROVED              │ REJECTED
┌──────▼──────┐         ┌──────▼──────┐
│     END     │         │   drafting  │
└─────────────┘         └─────────────┘
```

State is ephemeral per run (DL-036). No state persists across agent invocations. The
`run_id` is the only durable identifier; all artifacts are keyed to it.

---

## Policy Enforcement Points

```
                    Agent decides to invoke tool
                               │
                               ▼
                  ┌─────────────────────────────┐
                  │    PEP-1: Pre-Call Validation│
                  │  1. Tool registered?         │ NO  → DENIED + alert + terminate
                  │  2. Autonomy class?          │ DENIED → reject immediately
                  │  3. Scope bounds valid?      │ HUMAN_GATED → require approval token
                  │  4. Call count < max?        │ NO  → circuit breaker
                  │  5. Prohibited action?       │ YES → DENIED + alert
                  │  6. Data classification OK?  │ NO  → DENIED
                  └─────────────┬───────────────┘
                                │ ALL 6 PASS
                                ▼
                           Tool executes
                                │
                                ▼
                  ┌─────────────────────────────┐
                  │    PEP-2: Post-Call          │
                  │    Sanitization              │
                  │  1. Evidence lineage valid?  │ NO  → strip + flag
                  │  2. PII detected?            │ YES → redact
                  │  3. Injection pattern?       │ YES → sanitize + flag
                  │  4. Result size OK?          │ NO  → truncate
                  └─────────────┬───────────────┘
                                │ ALL 4 PASS
                                ▼
                   Result enters reasoning state
```

PEP-1 is implemented in `src/agent/pep.py` (`PEP1Validator`). PEP-2 is implemented in
`src/agent/pep.py` (`PEP2Sanitizer`). PEP-3 (post-run lineage audit) is a stub; see
`FUTURE_WORK.md`.

---

## Trust Ledger

The trust ledger (`config/trust_ledger.yaml`) is the governance contract between the agent
and the system. Every tool must be registered before invocation. Unregistered tools are
implicitly DENIED.

```
Tool Registration fields:
  tool_id                   — unique identifier
  autonomy_class            — AUTONOMOUS | HUMAN_GATED | DENIED
  risk_tier                 — LOW | MEDIUM | HIGH | CRITICAL
  allowed_actions           — explicit IAM action allowlist
  prohibited_actions        — explicit IAM action denylist
  policy_enforcement_points — pre_call + post_call handlers
  max_calls_per_run         — hard circuit breaker ceiling
  evidence_lineage_required — source_uri + hash + timestamp
  audit_retention_days      — minimum retention requirement
```

Registered tools:

| Tool ID | Name                          | Risk     | Autonomy    |
|---------|-------------------------------|----------|-------------|
| T-001   | query_iam_policies            | LOW      | AUTONOMOUS  |
| T-002   | submit_assessment_artifact    | HIGH     | HUMAN_GATED |
| T-003   | modify_iam_policy             | CRITICAL | DENIED      |
| T-004   | search_cloudtrail_events      | LOW      | AUTONOMOUS  |
| T-005   | lookup_compliance_requirement | LOW      | AUTONOMOUS  |

T-003 (`modify_iam_policy`) is registered as DENIED to document the authority boundary
explicitly (DL-039). Any attempt to invoke it is rejected before execution, not at the
IAM layer.

---

## P2 Integration

P3 consumes P2 (`trust-layer-rag`) as a governed knowledge service via FastAPI:

```
POST http://localhost:8000/retrieve
{
  "query": "compliance requirements for AC-2",
  "control_family": "AC",
  "framework": "NIST-800-53",
  "top_k": 5
}
```

Response chunks carry evidence lineage: `source_uri`, `evidence_hash`,
`retrieval_timestamp`, `relevance_score`, `framework`, `control_id`.

P2 enforces its own governance before returning results:
Presidio PII scrub → hybrid retrieval → Cohere rerank → Bedrock Guardrails.
P3 enforces PEP-2 on what P2 returns. Two independent governance checkpoints on every
piece of knowledge the agent acts on.

P2 unreachable is a documented non-fatal condition (DL-038). The agent reaches
`awaiting_human_review` rather than firing the circuit breaker when P2 is down,
because IAM + CloudTrail evidence alone is sufficient for a sufficiency determination.

---

## Governance Decision Record

Written at runtime for every HUMAN_GATED event (`outputs/governance_decision_{run_id}.json`):

```json
{
  "run_id": "...",
  "tool_requested": "submit_assessment_artifact",
  "risk_tier": "HIGH",
  "autonomy_class": "HUMAN_GATED",
  "approval_required": true,
  "approval_status": "PENDING | APPROVED | REJECTED",
  "pep_outcomes": {"total": 34, "passed": 34, "failed": 0},
  "evidence_lineage": { "...per control..." },
  "decision_timestamp": "..."
}
```

The Streamlit UI reads this file to populate the approval gate. On APPROVED, the record
is updated in place with `approval_status: APPROVED` and `approver_timestamp`.

---

## Observability

Langfuse Cloud traces every state transition and tool call:

- Input/output tokens per node
- PEP outcome per tool invocation
- State transition latency
- Evidence lineage in trace input

All nodes are decorated with `@observe` (Langfuse 3.x pattern). The planning node sets
`session_id`, `name`, `user_id`, and metadata on the trace root. LLM calls in `llm.py`
use `update_current_generation()` to attach model ID, token counts, and cache metrics.

Prompt caching is enabled for the Bedrock system prompt via the
`anthropic-beta: prompt-caching-2024-07-31` header injected at the boto3 event level
(DL-037). Cache hit rates are visible in the Langfuse generation metadata.

Dashboard: us.cloud.langfuse.com → trust-layer-agent project

---

## Evaluation Suite

Three-tier evaluation covering 19 scenarios:

| Tier | Method | Scenarios |
|------|--------|-----------|
| 1 | Deterministic graders | Happy path (HP-001–008), Failure modes (FM-001–007) |
| 2 | LLM-as-judge | Adversarial (TM-001–004) |
| 3 | Human review criteria | Documented in `eval/human_review_log.md` |

Run: `python eval/generate_report.py` → `eval/results/eval_report.md`

Current result: 19/19 pass.

---

## Regulatory Alignment

| Framework | Coverage |
|-----------|----------|
| NIST AI RMF 1.0 | MAP and MEASURE functions |
| NIST AI 600-1 | Multi-step autonomous behavior |
| NIST 800-53 Rev 5 | AC, AU, CA, RA, SI families |
| OMB M-24-10 / M-25-21 | AI use case inventory |
| FedRAMP ConMon | Evidence collection pattern |
| OWASP LLM Top 10 | Adversarial threat coverage |

Full mapping: `docs/framework_reference.md` Section 9
