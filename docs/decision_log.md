# Decision Log — The Trust Layer for Enterprise Agentic AI

All architectural decisions recorded here. Format: decision made, rationale,
alternatives evaluated. Referenced from `src/` and `config/trust_ledger.yaml`
via DL-XXX pointers once the agent is implemented.

Numbering continues across the portfolio. Predecessor project
[trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag)
ended at **DL-029**. The first entry in this log is **DL-030**.

---

---

## DL-030 — Orchestration Framework: LangGraph

**Decision:** LangGraph selected as the agent orchestration framework.
**Date:** 2026-05-26

**Rationale:** The governance requirement — deterministic boundaries enforced as direct edges, probabilistic reasoning bounded within states — maps directly to LangGraph's explicit node/edge architecture. Direct edges enforce hard state transitions at governance boundaries (sufficiency gate, HUMAN_GATED submission, circuit breakers) without LLM override. Conditional edges bound probabilistic reasoning within declared states (tool selection, query formulation, sufficiency assessment). The framework makes the state machine visible and auditable without additional instrumentation overhead. Langfuse integration is native and well-documented. The governance pattern is framework-agnostic — it transfers to any stateful agent framework or hand-rolled implementation. LangGraph is the vehicle, not the architecture.

**Alternatives evaluated:**
- Hand-rolled state machine over Anthropic SDK directly — maximum auditability, no framework lock-in, full control over every state transition. Eliminated on LOE grounds: LangGraph absorbs the state management overhead that hand-rolled requires, without hiding the governance-critical transitions. Remains the right choice if LangGraph's reasoning trace integration proves insufficient during Agent Implementation.
- CrewAI — role-based multi-agent framework. Wrong abstraction for single-agent governance workflows. Better fit for `trust-layer-multiagent` multi-agent orchestration.
- Google ADK — Google ecosystem oriented, not compatible with AWS Bedrock stack.
- Amazon Bedrock Agents — AWS native, strong enterprise deployment characteristics, FedRAMP-eligible infrastructure. Rejected on governance architecture grounds: this framework requires deterministic Policy Enforcement Point (PEP) insertion between each reasoning-to-action transition — `reasoning → PEP-1 → tool execution → PEP-2 → result validation → reasoning continuation`. Bedrock Agents manages this internal sequencing — reasoning progression, tool invocation ordering, result incorporation — inside its orchestration loop. Governance controls can be applied at orchestration entry and exit boundaries, but cannot be deterministically inserted between internal execution transitions. This is a mismatch with the framework's PEP architecture, not a general limitation for regulated enterprise workloads.
- Pydantic AI — type-safe agent framework with strong validation story. Promising but insufficiently documented in federal production contexts. Revisit for `trust-layer-multiagent`.

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
- Persistent agent memory — deferred. Creates a second state store outside the per-run audit trail, introducing provenance and compliance gaps. Relevant for multi-agent workflows in `trust-layer-multiagent` where shared evidence accumulation across sub-agents is required.
- Retrieval-augmented memory — deferred. Prior run results stored in a vector store and retrieved as context. Introduces cross-run provenance complexity without sufficient benefit in the single-agent, bounded-scope use case.

---

## DL-032 — Synthetic Fixture Design

**Decision:** IAM policy and CloudTrail event fixtures stored as JSON files in `fixtures/iam_policies/` and `fixtures/cloudtrail_events/`. Eight fixtures total — four per source type, one per control (AC-2, AC-3, AC-6, AC-17). Each fixture exhibits a known compliance finding.
**Date:** 2026-05-28

**Rationale:** JSON files in a versioned `fixtures/` directory are visible, readable artifacts — a prospect reviewing the repo sees realistic-looking evidence data with documented findings, not hidden Python constants. The realism is in the instrumentation and governance pattern, not the dataset. Synthetic data was chosen deliberately: the governance pattern transfers; real IAM and CloudTrail data requires production permissions and data handling agreements outside portfolio scope (documented in FUTURE_WORK.md).

Each fixture was designed to exhibit a specific finding:
- AC-2: over-privileged role (IAM) + dormant credential reactivated (CloudTrail)
- AC-3: missing permissions boundary (IAM) + unauthorized access attempt (CloudTrail)
- AC-6: wildcard AdministratorAccess (IAM) + privilege escalation attempt (CloudTrail)
- AC-17: remote access role without MFA condition (IAM) + SSM session without MFA (CloudTrail)

**Alternatives evaluated:**
- Python dicts in `src/fixtures/` — importable directly, no file I/O. Eliminated: hides the evidence data from repo browsing; not a visible consulting artifact.
- Real CloudTrail/IAM data — eliminated. Requires production permissions and data handling agreements. Documented in FUTURE_WORK.md as the production extension path.

---

## DL-033 — LLM Provider and Model Selection

**Decision:** AWS Bedrock with `claude-sonnet-4-5-20251001` for both the agent (sufficiency assessment, draft generation) and the LLM-as-judge evaluation tier.
**Date:** 2026-05-28

**Rationale:** Bedrock is the natural choice for a federal portfolio project — it satisfies FedRAMP boundary requirements, keeps all inference within the AWS account perimeter, and is the model provider federal clients are most likely to be operating. Using the same provider for both the agent and the judge eliminates a cross-provider dependency while keeping the judge independent of the agent's specific call history. `claude-sonnet-4-5-20251001` provides strong instruction-following for structured JSON output (sufficiency assessment) and long-form generation (draft assessment).

Operational finding: drafting calls at ~4,875 input tokens require ~63 seconds of inference time. Botocore's default 60-second `read_timeout` killed the first drafting run. Fixed by setting `read_timeout=300` via `botocore.config.Config`. This established the baseline cost-per-assessment metric: ~8,478 total tokens per full run (4 sufficiency calls + 1 drafting call). See DL-036 for the cost model.

**Alternatives evaluated:**
- Anthropic API directly — eliminates Bedrock dependency, simpler client. Eliminated: breaks FedRAMP boundary positioning and requires a separate API key outside AWS credentials.
- OpenAI via Bedrock — available but inconsistent with the Anthropic-first architecture of P1 and P2.
- Separate judge model (e.g. smaller/faster model for evaluation) — deferred. Adds complexity without clear benefit at portfolio scale. Revisit in the Evaluation Suite if judge latency is a concern.

---

## DL-034 — Identity Scope: Mocked

**Decision:** Agent identity and delegated authority implemented as mocked — execution identity declared in trust ledger schema, role-assumption flow simulated, not wired to real AWS STS.
**Date:** 2026-05-28

**Rationale:** The governance pattern — declaring execution identity, enforcing scope bounds at PEP-1, preventing privilege escalation — is fully demonstrated at the application layer without real STS session issuance. Wiring to real IAM/STS requires a production AWS account with specific role configurations, introduces credential management complexity, and creates teardown risk for a portfolio project. The mocked implementation is honest about what it is: the trust ledger declares `execution_identity` as a governance artifact; the PEP enforces it as a scope constraint; real STS issuance is the production extension documented in FUTURE_WORK.md.

**Alternatives evaluated:**
- Fully wired to real IAM role + STS — maximum production credibility. Eliminated for portfolio scope: requires account configuration outside the codebase, creates credential persistence risk, and adds no governance signal beyond what the mocked implementation already demonstrates.
- Conceptual only (no enforcement) — eliminated. The trust ledger enforcement at PEP-1 is load-bearing; conceptual-only would undermine the governance claim entirely.

---

## DL-036 — Cost Per Control Assessment Baseline

**Decision:** Token economics documented as a first-class operational metric. Baseline established from first successful end-to-end run.
**Date:** 2026-05-28

**Baseline (run_id: 4df2065a, four AC-family controls, P2 live):**

| Component | Tokens In | Tokens Out |
|---|---|---|
| Sufficiency — AC-2 | 1,207 | 76 |
| Sufficiency — AC-3 | 1,184 | 85 |
| Sufficiency — AC-6 | 1,312 | 82 |
| Sufficiency — AC-17 | 1,265 | 81 |
| Drafting (all 4 controls) | 4,875 | 3,603 |
| **Total** | **9,843** | **3,927** |

**Cost calculation (`claude-sonnet-4-5-20251001` on Bedrock):**
- Input: ~$0.003/1K tokens × 9.843K = ~$0.030
- Output: ~$0.015/1K tokens × 3.927K = ~$0.059
- **Total per run: ~$0.089**
- **Cost per control assessed: ~$0.022**

**Interpretation:** At $0.022 per control, a full FedRAMP Moderate baseline (325 controls) would cost approximately $7.15 in model inference. The governance overhead (PEP enforcement, evidence lineage, audit trail) adds no model cost — it is instrumentation, not inference. This is the number a fractional buyer multiplies by their control count to evaluate operational viability.

**Note:** Token counts will increase with real evidence (production IAM policies and CloudTrail events are larger than synthetic fixtures). A 3–5× multiplier on input tokens is a reasonable production estimate, putting full-baseline cost at $20–35 per run.

---
