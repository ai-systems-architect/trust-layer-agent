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
- **DL-032 candidate — Synthetic fixture design.** IAM policy and CloudTrail
  event fixture format; adversarial seed cases (prompt injection in retrieved
  evidence content, over-privileged role, dormant credential, missing MFA).
- **DL-033 candidate — LLM provider and model for agent + judge.** Generation
  model for the agent itself and the LLM-as-judge tier in the eval harness.
- **DL-034 candidate — Identity scope: mocked vs. wired.** Whether agent
  identity / delegated authority is conceptual-only, mocked with simulated
  role assumption, or wired to real STS. Mocked is the working assumption.

---

## DL-031 — AC Control Selection

**Decision:** Demonstration scope locked to four controls: AC-2 (Account Management), AC-3 (Access Enforcement), AC-6 (Least Privilege), AC-17 (Remote Access).
**Date:** 2026-05-11

**Rationale:** The AC family contains approximately 25 controls. Assessing all 25 in a reference implementation adds surface area without adding governance signal — the framework pattern is visible in four controls as clearly as in twenty-five. The four selected were chosen because they (1) touch every federal system regardless of agency or mission, (2) produce observable evidence from IAM policies and CloudTrail logs that synthetic fixtures can credibly represent, and (3) exhibit distinct failure modes — AC-2 surfaces dormant credential patterns, AC-3 surfaces policy attachment gaps, AC-6 surfaces wildcard permission abuse, AC-17 surfaces remote access anomalies. Together they demonstrate the full evidence-collection-to-assessment pipeline without requiring fixtures that simulate domain-specific system configurations.

**Alternatives evaluated:**
- Full AC family (25 controls) — eliminated. Adds implementation time without proportional governance signal. Extension to the full family is documented in `FUTURE_WORK.md`.
- IA family (Identification and Authentication) — evaluated. Strong federal relevance but evidence collection requires MFA and PIV configuration data that is harder to represent credibly in synthetic fixtures.
- AU family (Audit and Accountability) — evaluated. High signal for compliance workflows but overlaps with the agent's own audit trail requirements, creating a confusing demonstration where the agent audits the same class of controls it is itself subject to.
- Mixed family (two AC + two AU) — eliminated. Splitting across families reduces the coherence of the demonstration without a clear benefit. AC family as a unit is a universally understood federal concept; a mixed set requires more context to interpret.

---

## DL-035 — Memory Architecture: Ephemeral Per-Run

**Decision:** Agent uses ephemeral per-run memory. No persistent memory across runs. Authoritative knowledge sourced from P2 governed RAG on demand.
**Date:** 2026-05-16

**Rationale:** Ephemeral memory enforces governance clarity, audit trail integrity, and data minimization without requiring a separate purge mechanism. Each run starts with a declared scope; persistent memory would introduce state that cannot be fully attributed to a specific authorized scope declaration. Static authoritative knowledge (NIST control text, FedRAMP requirements) is provided by the retrieval layer on demand — eliminating the primary motivation for persistent memory in this use case.

**Alternatives evaluated:**
- Persistent agent memory — deferred. Creates a second state store outside the per-run audit trail, introducing provenance and compliance gaps. Relevant for multi-agent workflows in P4 where shared evidence accumulation across sub-agents is required.
- Retrieval-augmented memory — deferred. Prior run results stored in a vector store and retrieved as context. Introduces cross-run provenance complexity without sufficient benefit in the single-agent, bounded-scope use case.

---
