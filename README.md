# trust-layer-agent
## Beyond Autonomy: Architecting the Trust Layer for Enterprise Agentic AI

Federal agencies and enterprises are deploying agentic AI — systems that don't just answer questions but take autonomous actions across multiple steps. The governance frameworks designed for static models don't transfer. This project demonstrates what governed agentic AI looks like in production: a working compliance agent instrumented against a governance framework that any federal program or enterprise AI risk team can adopt.

The agent collects audit evidence for NIST 800-53 AC-family controls, assesses sufficiency, generates a cited compliance assessment, and gates submission behind a mandatory human approval checkpoint — with every tool call validated against a trust ledger, every evidence item carrying a lineage hash, and every governance decision written as a runtime audit artifact.

**Governance artifacts are checked into this repository before a single line of agent code was written. The framework is the deliverable. The agent is the proof it works.**

---

## Overview

This project is a reference implementation of accountable autonomous AI for federal compliance workflows. It answers one question: what does a governed agentic AI system look like, end to end, in a production-grade environment?

The answer has three components:

1. A governance framework document — the specification and consulting deliverable.
2. A working LangGraph agent — the proof the framework works.
3. A three-tier evaluation suite — deterministic graders, LLM-as-judge, and human review criteria.

---

## The Problem

Federal agencies and enterprises are deploying agentic AI without governance frameworks designed for autonomous, multi-step behavior. NIST AI RMF, AI 600-1, and OMB M-24-10 do not prescribe how to instrument agents. The gap between "deploying agents" and "governing agents" is the problem this repository addresses.

---

## Repository Structure

```
config/trust_ledger.yaml                       Tool registration and governance controls
docs/framework.md                              Governance framework document (in progress)
docs/agent_risk_classification_matrix.md       Risk tier definitions
docs/decision_log.md                           Architecture decision log
docs/examples/governance_decision.json         Runtime governance artifact schema
src/                                           Agent implementation
eval/                                          Evaluation suite
FUTURE_WORK.md                                 Documented extensions, not built
```

---

## What's Built

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
┌──────▼──────┐         ┌──────▼──────┐
│     END     │         │   drafting  │
└─────────────┘         └─────────────┘
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

### Portfolio Arc

```
┌──────────────────────────────────────────────────────────┐
│  P4  trust-layer-multiagent      ORCHESTRATION LAYER     │
│      Agent-to-agent trust, delegation, audit chains      │
├──────────────────────────────────────────────────────────┤
│  P3  trust-layer-agent           REASONING LAYER  ◄ here │
│      Autonomous action, tool use, human oversight        │
├──────────────────────────────────────────────────────────┤
│  P2  trust-layer-rag             RETRIEVAL LAYER         │
│      Knowledge retrieval, guardrails, citation integrity │
├──────────────────────────────────────────────────────────┤
│  P1  responsible-mlops-          DATA AND MODEL LAYER    │
│      risk-engine                 Fairness, drift, ATO    │
└──────────────────────────────────────────────────────────┘
```

---

## Governance Artifacts

Three artifacts are the foundation before any code:

- **Trust Ledger** (`config/trust_ledger.yaml`) — explicit tool registration covering autonomy class, risk tier, policy enforcement points, and evidence lineage requirements. Tools not listed are implicitly DENIED.
- **Risk Classification Matrix** (`docs/agent_risk_classification_matrix.md`) — four tiers (Low → Critical) mapping autonomy class, human approval requirements, failure impact, and logging requirements.
- **Governance Decision Schema** (`docs/examples/governance_decision.json`) — runtime artifact capturing tool request, approval status, evidence lineage, and PEP outcomes per agent run.

---

## Observability

Langfuse traces are the audit trail — every state transition, tool invocation, PEP outcome, and token count is captured as a first-class governance artifact, not observability tooling.

---

## Portfolio Arc

| Project | Layer | Governance concerns |
|---|---|---|
| P1 `responsible-mlops-risk-engine` | Data and model layer | Training data, fairness, drift monitoring |
| P2 `trust-layer-rag` | Retrieval layer | Knowledge retrieval, guardrails, PII, citation integrity |
| P3 `trust-layer-agent` *(this project)* | Reasoning layer | Autonomous action, tool use, human oversight, audit trail |
| `trust-layer-multiagent` | Orchestration layer | Agent-to-agent trust, delegation, coordination governance |

---

## Build Status

| Phase | Status |
|---|---|
| Phase 1 — Governance Framework Document | In Progress |
| Agent Implementation | Planned |
| Evaluation Suite | Planned |
| Phase 4 — Decision Log | Running |

---

## Regulatory Alignment

- NIST AI RMF 1.0
- NIST AI 600-1
- OMB M-24-10
- NIST 800-53 Rev 5 (AC, AU, CA, RA, SI families)
