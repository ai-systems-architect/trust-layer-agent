# Beyond Autonomy: Architecting the Trust Layer for Enterprise Agentic AI

**`trust-layer-agent`** · Reasoning layer (P3) of the Trust Layer portfolio

Federal agencies and enterprises are deploying agentic AI — systems that don't just answer questions but take autonomous actions across multiple steps. The governance frameworks designed for static models don't transfer. This project demonstrates what a production-grade governed agentic AI pattern looks like implemented end to end: a working compliance agent instrumented against a governance framework that any federal program or enterprise AI risk team can adopt.

The agent collects audit evidence for NIST 800-53 AC-family controls, assesses sufficiency, generates a cited compliance assessment, and gates submission behind a mandatory human approval checkpoint — with every tool call validated against a trust ledger, every evidence item carrying a lineage hash, and every governance decision written as a runtime audit artifact.

**Governance artifacts are checked into this repository before a single line of agent code was written. The framework is the deliverable. The agent is the proof it works.**

---

## Scope and Assumptions

This is a production-grade governance pattern implemented against synthetic data in a non-production deployment.

| Dimension | This Implementation | Production Requirement |
|---|---|---|
| Data | Synthetic IAM + CloudTrail fixtures | Real AWS telemetry with data handling agreements |
| Identity | Application-layer declaration; no real STS | Real IAM role + STS short-lived session |
| Observability | Langfuse Cloud Hobby (synthetic traces only) | Self-hosted Langfuse within FedRAMP boundary |
| ATO | Not applicable — reference implementation | Program-level ATO with FedRAMP-aligned infrastructure |

Federal alignment is pattern-based. Actual deployment into an ATO boundary requires FedRAMP-aligned infrastructure and program-level authority to operate. Production extension paths are documented in `FUTURE_WORK.md`.

---

## Overview

This project is a reference implementation of accountable autonomous AI for federal compliance workflows. It answers one question: what does a governed agentic AI system look like, end to end, as a production-grade pattern implemented against synthetic data?

The answer has three components:

1. A governance framework document — the specification and consulting deliverable.
2. A working LangGraph agent — the proof the framework works.
3. A three-tier evaluation suite — deterministic graders, LLM-as-judge, and human review criteria.

---

## The Problem

Federal agencies and enterprises are deploying agentic AI without governance frameworks designed for autonomous, multi-step behavior. NIST AI RMF, AI 600-1, and OMB M-24-10 do not prescribe how to instrument agents. The gap between "deploying agents" and "governing agents" is the problem this repository addresses.

---

## What's Built

Three artifacts are complete. The governance framework specifies every rule before any code was written. The agent proves the framework works. The evaluation suite proves the agent fails safely — 19/19 scenarios pass across happy path, failure mode, and adversarial tiers.

A reviewer asks the agent to assess an AC-family control. The agent *plans* the evidence
it needs, then *gathers* it by calling three read-only tools — IAM policies (T-001),
CloudTrail events (T-004), and compliance requirements from P2's RAG service (T-005) —
with every call validated by PEP-1 before execution and sanitized by PEP-2 after. It then
*assesses sufficiency*: if the evidence is incomplete it loops back to gather more, and if
it can never reach sufficiency a circuit breaker fires. Once sufficient, it *drafts* a
cited compliance assessment with a frontier model. The draft does **not** auto-submit —
submission is a HIGH-risk, HUMAN_GATED action, so the run suspends at *awaiting human
review* and writes a `governance_decision.json` audit record. A human approves (run ends,
artifact released) or rejects (back to drafting). Every transition, tool call, and PEP
outcome is traced to Langfuse.

Three tiers are complete: governance framework, working agent, and evaluation suite. The diagrams below show the state machine, system architecture, and policy enforcement sequence.

### Agent State Machine

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
┌──────▼──────┐         ┌──────▼─────────────────────┐
│     END     │         │  drafting                  │
└─────────────┘         │  (rejection reason passed  │
                        │   in, new draft generated) │
                        └────────────────────────────┘
```

### System Architecture

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

### Policy Enforcement Points

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

---

## Portfolio Arc

| Project | Layer | Status |
|---|---|---|
| [`responsible-mlops-risk-engine`](https://github.com/ai-systems-architect/responsible-mlops-risk-engine) | Data and model | ✅ Complete |
| [`trust-layer-rag`](https://github.com/ai-systems-architect/trust-layer-rag) | Retrieval | ✅ Complete |
| **[`trust-layer-agent`](https://github.com/ai-systems-architect/trust-layer-agent)** | **Reasoning and action** | **✅ Complete** |
| `trust-layer-multiagent` | Orchestration | 🚧 In Progress |

---

## Repository Structure

```
config/trust_ledger.yaml                       Tool registration and governance controls
docs/framework.md                              Governance framework — plain-language version
docs/framework_reference.md                    Governance framework — full technical specification
docs/architecture.md                           System architecture and diagrams
docs/decision_log.md                           Architecture decision log (DL-031 onward)
docs/agent_risk_classification_matrix.md       Risk tier definitions
docs/examples/governance_decision.json         Runtime governance artifact schema
src/agent/                                     LangGraph state machine, PEPs, LLM, tools
src/tools/                                      Tool implementations (T-001, T-004, T-005)
src/ui/app.py                                  Streamlit UI — run config, live status, approval gate
scripts/run_agent.py                           CLI entry point for a single agent run
scripts/run_ui.sh                              Launch the Streamlit UI
eval/                                          Three-tier evaluation suite (19 scenarios)
eval/results/eval_report.md                    Generated evaluation report
fixtures/                                       Synthetic IAM policies and CloudTrail events
outputs/                                        Runtime artifacts — governance decisions + drafts
FUTURE_WORK.md                                 Documented extensions, not built
```

---

## Governance Artifacts

Three artifacts are the foundation before any code:

- **Trust Ledger** (`config/trust_ledger.yaml`) — explicit tool registration covering autonomy class, risk tier, policy enforcement points, and evidence lineage requirements. Tools not listed are implicitly DENIED.
- **Risk Classification Matrix** (`docs/agent_risk_classification_matrix.md`) — four tiers (Low → Critical) mapping autonomy class, human approval requirements, failure impact, and logging requirements.
- **Governance Decision Schema** (`docs/examples/governance_decision.json`) — runtime artifact capturing tool request, approval status, evidence lineage, and PEP outcomes per agent run.

---

## Regulatory Alignment

- NIST AI RMF 1.0
- NIST AI 600-1
- OMB M-24-10
- NIST 800-53 Rev 5 (AC, AU, CA, RA, SI families)

---

## Observability

Langfuse captures the reasoning trace and observability evidence — state transition latency, tool invocation records, PEP outcomes, and token counts per node. Formal audit artifacts (`governance_decision_{run_id}.json` and `draft_assessment_{run_id}.md`) are written separately to `outputs/` and are the authoritative runtime record.

---

## Evaluation Results

19/19 scenarios pass across three tiers.

| Tier | Scenarios | Result |
|---|---|---|
| Happy path | 8 | ✅ 8/8 |
| Failure modes | 7 | ✅ 7/7 |
| Adversarial | 4 | ✅ 4/4 |

Key findings: FM-005 (sufficiency gate bypass) confirmed the hard state machine gate catches 100% of bypass attempts. TM-004 (verifier robustness) confirmed the LLM judge identifies errors in a deliberately bad assessment without being told what to look for. TM-001 (prompt injection) confirmed detection fires at the evidence layer — injection never reached agent reasoning state.

Full report: [`eval/results/eval_report.md`](eval/results/eval_report.md)

---

## Status

Complete and verified end to end — governance framework, LangGraph agent with PEP enforcement, Streamlit UI with human approval gate, and a three-tier evaluation suite passing 19/19 (8 happy-path, 7 failure-mode, 4 adversarial). Decision log spans DL-031 → DL-041. Full results: [`eval/results/eval_report.md`](eval/results/eval_report.md)

---

## Quickstart

Requires Python 3.9+, AWS credentials with Bedrock access, and a Langfuse cloud account (us.cloud.langfuse.com).

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure (AWS Bedrock + Langfuse keys)
cp .env.example .env        # then fill in credentials

# 3. Run one agent assessment (synthetic AC-family fixtures)
python scripts/run_agent.py

# 4. Launch the UI — live status + human approval gate at :8501
bash scripts/run_ui.sh

# 5. Run the evaluation suite → eval/results/eval_report.md
python eval/generate_report.py
```

The agent runs entirely against synthetic IAM/CloudTrail fixtures — no real AWS account or production data required. P2 (`trust-layer-rag`) must be running on `:8000` — T-005 calls the governed retrieval API to supply compliance requirement text for each control. Without P2, T-005 degrades gracefully (FM-002) but sufficiency assessment will fail for most controls and the circuit breaker will fire. See DL-038 for the documented behavior change.

Execution identity (`audit-readonly-role`) is declared at the application layer — no real AWS STS session issuance. Production wiring is documented in `FUTURE_WORK.md` and DL-035.
