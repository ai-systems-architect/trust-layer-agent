# Decision Log — The Trust Layer for Enterprise Agentic AI

All architectural decisions recorded here. Format: decision made, rationale,
alternatives evaluated. Referenced from `src/` and `config/trust_ledger.yaml`
via DL-XXX pointers once the agent is implemented.

Numbering continues across the portfolio. Predecessor project
[trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag)
ended at **DL-029**. The first entry in this log is **DL-030**.

---

## Pending decisions (to be logged when made)

- **DL-032 candidate — Synthetic fixture design.** [Phase 2] IAM policy and CloudTrail
  event fixture format; adversarial seed cases (prompt injection in retrieved
  evidence content, over-privileged role, dormant credential, missing MFA).
- **DL-033 candidate — LLM provider and model for agent + judge.** [Phase 2] Generation
  model for the agent itself and the LLM-as-judge tier in the eval harness.
- **DL-034 candidate — Identity scope: mocked vs. wired.** [Phase 2] Whether agent
  identity / delegated authority is conceptual-only, mocked with simulated
  role assumption, or wired to real STS. Mocked is the working assumption.

---

## DL-030 — Orchestration Framework: LangGraph

**Decision:** LangGraph selected as the agent orchestration framework.
**Date:** 2026-05-26

**Rationale:** The governance requirement — deterministic boundaries enforced as direct edges, probabilistic reasoning bounded within states — maps directly to LangGraph's explicit node/edge architecture. Direct edges enforce hard state transitions at governance boundaries (sufficiency gate, HUMAN_GATED submission, circuit breakers) without LLM override. Conditional edges bound probabilistic reasoning within declared states (tool selection, query formulation, sufficiency assessment). The framework makes the state machine visible and auditable without additional instrumentation overhead. Langfuse integration is native and well-documented. The governance pattern is framework-agnostic — it transfers to any stateful agent framework or hand-rolled implementation. LangGraph is the vehicle, not the architecture.

**Alternatives evaluated:**
- Hand-rolled state machine over Anthropic SDK directly — maximum auditability, no framework lock-in, full control over every state transition. Eliminated on LOE grounds: LangGraph absorbs the state management overhead that hand-rolled requires, without hiding the governance-critical transitions. Remains the right choice if LangGraph's reasoning trace integration proves insufficient during [Phase 2].
- CrewAI — role-based multi-agent framework. Wrong abstraction for single-agent governance workflows. Better fit for [P4] multi-agent orchestration.
- Google ADK — Google ecosystem oriented, not compatible with AWS Bedrock stack.
- Amazon Bedrock Agents — AWS native but manages the orchestration loop internally, making direct PEP instrumentation difficult. Governance controls would sit outside the execution path rather than inside it.
- Pydantic AI — type-safe agent framework with strong validation story. Promising but insufficiently documented in federal production contexts. Revisit for [P4].

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
