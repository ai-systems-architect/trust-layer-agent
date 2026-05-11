# Beyond Retrieval, Into Autonomy: Architecting the Trust Layer for Federal Agentic AI
![Visitor Count](https://api.visitorbadge.io/api/VisitorHit?user=ai-systems-architect&repo=trust-layer-agent&countColor=%23263759)

Raghunath Devayajanam · May 2026

*A reference implementation of accountable autonomous AI for federal compliance workflows — the governance pattern is the deliverable, the agent is the proof it works.*

**Federal Agentic Governance · NIST 800-53 Access Control Evidence Collection**

A documented governance framework for autonomous, multi-step AI agents performing federal compliance work, demonstrated through a single-agent reference implementation that drafts NIST 800-53 Access Control evidence assessments from synthetic IAM and CloudTrail fixtures. Every tool call is gated by a versioned trust ledger; every state transition is captured in a reasoning trace; every assessment artifact is bound to its evidence lineage and human-approver token.

Built as a **governance demonstration vehicle** — not a production audit tool. The agent drafts assessments grounded in retrieved evidence and the framework document. It does not determine whether a system is compliant — that determination is a human Authorizing Official's call. The trust ledger enforces this boundary at the tool layer (`submit_assessment_artifact` is `HUMAN_GATED`, `modify_iam_policy` is `DENIED`).

**What makes this distinctive:**

- **The framework is the deliverable.** `docs/framework.md` is a standalone governance reference document covering trust boundaries, policy enforcement points, reasoning trace requirements, failure mode catalog, threat model, and mappings to NIST AI RMF, NIST AI 600-1, OMB M-24-10 / M-25-21, FedRAMP, and NIST 800-53 Rev 5. The agent under `src/` is the demonstration that the pattern is implementable.
- **Trust ledger as a versioned artifact** — `config/trust_ledger.yaml` is a schema-driven tool registry binding each tool to its risk tier, autonomy class, evidence-lineage requirements, allowed/prohibited actions, data classifications, policy enforcement points, and audit retention. Tools not in the ledger are implicitly denied. Prospects can adopt this pattern directly.
- **Agent Risk Classification Matrix** — four-tier (Low / Moderate / High / Critical) classification with autonomy classes (`AUTONOMOUS` / `HUMAN_GATED` / `DENIED`), mapped to OMB / NIST impact-based language. See `docs/agent_risk_classification_matrix.md`.
- **Three-tier evaluation strategy** — code-based graders for deterministic assertions (PEP fired, citation present, refusal triggered), LLM-as-judge for qualitative compliance behavior (was a hedge justified given the context?), and human review for edge cases and high-stakes outputs. Specified in the framework; implemented in `eval/` during Phase 3.
- **Decision-log discipline continued from P2.** Numbering picks up at DL-030 from [trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag) (which ended at DL-029). The portfolio reads as one continuous body of architectural reasoning, not four disconnected projects.
- **P2 consumed as a service, not reimplemented.** The agent's `lookup_compliance_requirement` tool calls the upstream governed RAG system from [trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag) rather than rebuilding retrieval. Layered governance: data layer (P1) → retrieval layer (P2) → reasoning layer (P3).
- **Single-agent demonstration with explicit scope boundary.** Multi-agent orchestration governance is the subject of a separate project (P4) and is deliberately excluded here — keeping P3 single-agent is what makes it tractable and what makes the P3 → P4 progression coherent.

Designed for high-stakes, audit-sensitive environments where accountability, traceability, and controlled behavior of autonomous AI matter more than agent breadth or speed.

---

### 📄 Project artifacts

- **[Governance Framework](docs/framework.md)** — the Phase 1 reference document; trust boundary taxonomy, tool-use governance, PEPs, reasoning trace requirements, failure mode catalog, threat model, federal framework mappings.
- **[Trust Ledger](config/trust_ledger.yaml)** — versioned tool registry; risk tier, autonomy class, PEPs, evidence lineage requirements per tool.
- **[Agent Risk Classification Matrix](docs/agent_risk_classification_matrix.md)** — four-tier classification with autonomy class definitions and tier assignment criteria.
- **[Example Governance Decision](docs/examples/governance_decision.json)** — sample decision record showing identity, risk tier, approval status, evidence lineage, and PEP outcomes.
- **[Architecture](docs/architecture.md)** · **[Decision log](docs/decision_log.md)**

🔗 **Related portfolio projects**

- **[trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag)** — predecessor portfolio project. Governed Retrieval-Augmented Generation over four federal compliance frameworks (NIST 800-53, NIST AI RMF 1.0, NIST AI 600-1, FedRAMP Moderate). This project extends that discipline from **retrieval governance** to **reasoning governance**, and consumes the trust-layer-rag retrieval system as a tool the agent calls.
- **[responsible-mlops-risk-engine](https://github.com/ai-systems-architect/responsible-mlops-risk-engine)** — earlier portfolio project. Same governance discipline (NIST AI RMF 1.0, fairness audits, drift monitoring, decision-log rigor) applied to **end-to-end traditional ML** — XGBoost income risk scoring on US Census data. The first project in the arc.

---

> Independent portfolio project demonstrating production-grade governed agentic AI architecture for federal compliance workflows. Built against public NIST control families and synthetic IAM / CloudTrail fixtures. Not affiliated with or endorsed by any agency, contractor, or commercial vendor. Views are the author's own.
>
> Companion to [trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag) and [responsible-mlops-risk-engine](https://github.com/ai-systems-architect/responsible-mlops-risk-engine).

---

## Project Status

**Phase 1 — Governance framework document.** Active. The framework document (`docs/framework.md`) is the working deliverable. The agent under `src/` is built in Phase 2 once the framework is settled; the three-tier evaluation harness under `eval/` follows in Phase 3.

The build is phased so that each phase produces a portfolio-ready artifact and can be stopped without leaving the work half-finished. Decisions are captured in `docs/decision_log.md` in-flight. Deferred scope is tracked in `FUTURE_WORK.md`.

---

## Demonstration Scope

The agent demonstrates governance over a focused subset of NIST 800-53 Rev 5 Access Control (AC) family evidence collection — candidate controls: AC-2 (account management), AC-3 (access enforcement), AC-6 (least privilege), AC-17 (remote access) — against synthetic IAM policies and CloudTrail event fixtures. Scope is deliberately narrow so the governance instrumentation can be deep.

Synthetic data is a feature, not a limitation. The governance pattern is what transfers across deployments — not the dataset. Real telemetry integration is documented in `FUTURE_WORK.md`.

---

## Repository Layout

```
config/
  trust_ledger.yaml                       Tool registry: risk tier, autonomy class, PEPs, evidence lineage
docs/
  framework.md                            Governance framework (Phase 1 deliverable)
  architecture.md                         Agent architecture (state machine, tools, PEPs, traces)
  decision_log.md                         DL-030 onwards (continues from trust-layer-rag DL-029)
  agent_risk_classification_matrix.md     Four-tier classification + autonomy classes
  examples/
    governance_decision.json              Sample decision record
src/                                      Agent implementation (Phase 2)
eval/                                     Evaluation scenarios and three-tier graders (Phase 3)
```

---

## Future Work

Scope deliberately deferred from this project. Each item below is documented to signal that it has been considered and intentionally excluded — not overlooked.

### Production Required

**Real telemetry integration.** The agent operates against synthetic IAM policies and CloudTrail event fixtures. Connecting to real AWS IAM, real CloudTrail, and real ticketing systems requires production AWS account permissions, sample-data handling agreements, and a security review that exceeds portfolio scope. The integration pattern is documented in `docs/framework.md`; the wiring is intentionally not built. Required when this codebase is adopted for any real federal program. Trigger: a sponsoring program with the necessary authorities and a target environment.

**Identity and delegated authority — mocked → wired.** The framework specifies agent identity, scoped credentials, and impersonation prevention. The trust ledger declares the execution identity (`audit-readonly-role`, short-lived session credentials, impersonation disallowed) at the schema layer. A mocked role-assumption flow is in scope for Phase 2; wiring it to a real IAM role with STS session issuance is production work, not portfolio work.

### Stretch

**Multi-control coverage.** Extend the agent from the AC-family demonstration to AU (audit logging), IA (identification and authentication), and CM (configuration management). The framework is control-family-agnostic; AC was selected as the demonstration family because it touches every federal system and the failure modes are visible to non-specialist reviewers. Extension follows the pattern documented in `docs/framework.md`. Each additional family is roughly the same effort as the original AC implementation.

**Enterprise framework mappings.** Translate the federal mappings (NIST AI RMF, OMB M-24-10 / M-25-21, FedRAMP, 800-53) to: **SR 11-7** (banking model risk management), **HIPAA Security Rule** (health information audit workflows), **SOC 2 Type II** (evidence collection), and **ISO 27001 / 42001** (internal audit and AI management system). These translations are written work — articles that cite this codebase as the substrate — not additional code in this repository.

**Continuous monitoring agent variant.** Apply the same governance framework to a runtime ConMon agent rather than a periodic assessment agent. Same trust ledger pattern, different PEP behavior (streaming vs. batch), different reasoning trace cadence (every detection vs. every assessment). Documented as a pattern extension; reference implementation deferred.

**Operational observability dashboards.** Phase 3 captures input tokens, state transition latency, tool call frequency, and cache hit rates per run. Building a hosted dashboard surface over that data (Grafana over Langfuse, or similar) is a separate engineering exercise. The instrumentation is the load-bearing part; the dashboard is presentation.

### Considered and Deferred

**Multi-agent orchestration governance.** Planner-executor patterns, agent-to-agent messaging, and multi-agent state synchronization governance are deliberately out of scope for this project. The single-agent constraint is what makes this codebase tractable and what makes the P3 → P4 portfolio progression coherent. Multi-agent governance is the subject of a separate project (P4) in this portfolio arc, not an extension of this one.

**Self-correction loop.** Re-attempt evidence collection with a broadened search radius when the sufficiency-assessment state determines evidence is incomplete. Evaluated and deferred for the single-agent case: the human-gated review at `awaiting-human-review` provides the correctness floor, and the re-attempt pattern is more appropriate for multi-agent workflows where one agent's confidence judgment feeds another agent's next action. Reconsider in P4.

**Direct LLM SDK orchestration vs. LangGraph.** LangGraph is currently the candidate orchestration framework; a hand-rolled state machine over the model SDK directly is the alternative. The framework choice is captured as a pending entry in `docs/decision_log.md` and will be logged when made. Hand-rolled would maximize auditability and minimize lock-in but costs implementation time that LangGraph absorbs. The decision turns on whether LangGraph's reasoning trace integrates cleanly enough with the framework's reasoning-trace requirements.

---

## License

MIT License — see [LICENSE](LICENSE.md).

Copyright (c) 2026 Raghunath Devayajanam.

This project references US Government public-domain compliance frameworks (NIST 800-53 Rev 5, NIST AI RMF 1.0, NIST AI 600-1, OMB M-24-10 / M-25-21, FedRAMP). Those documents are works of the US Government and are not subject to copyright protection in the United States (17 U.S.C. § 105). They are referenced here to demonstrate governance patterns for autonomous AI in federal compliance contexts. No US Government endorsement is implied.
