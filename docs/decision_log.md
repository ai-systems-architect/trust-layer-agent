# Decision Log — The Trust Layer for Enterprise Agentic AI

All architectural decisions recorded here. Format: decision made, rationale,
alternatives evaluated. Referenced from `src/` and `config/trust_ledger.yaml`
via DL-XXX pointers once the agent is implemented.

Numbering continues across the portfolio. Predecessor project
[trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag)
ended at **DL-029**. The first entry in this log is **DL-030**.

---

## Pending decisions (to be logged when made)

- **DL-030 candidate — Orchestration framework.** LangGraph vs. hand-rolled
  state machine over the model SDK directly. Auditability of the reasoning
  trace is the dominant criterion. Log when the framework choice is made.
- **DL-031 candidate — AC control selection.** Specific AC controls in the
  demonstration scope (candidates: AC-2, AC-3, AC-6, AC-17). Log when the
  final set is locked.
- **DL-032 candidate — Synthetic fixture design.** IAM policy and CloudTrail
  event fixture format; adversarial seed cases (prompt injection in retrieved
  evidence content, over-privileged role, dormant credential, missing MFA).
- **DL-033 candidate — LLM provider and model for agent + judge.** Generation
  model for the agent itself and the LLM-as-judge tier in the eval harness.
- **DL-034 candidate — Identity scope: mocked vs. wired.** Whether agent
  identity / delegated authority is conceptual-only, mocked with simulated
  role assumption, or wired to real STS. Mocked is the working assumption.

---

<!-- Real entries (DL-030 onwards) begin below. Format follows trust-layer-rag:

## DL-NNN — <Short Title>
**Decision:** <one-line decision>
**Date:** YYYY-MM-DD [| **Updated:** YYYY-MM-DD]

**Rationale:** <paragraph(s)>

**Alternatives evaluated:**
- <option> — <treatment or exclusion reason>

---
-->
