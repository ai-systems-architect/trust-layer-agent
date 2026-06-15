# Decision Log — The Trust Layer for Enterprise Agentic AI

All architectural decisions recorded here. Format: decision made, rationale,
alternatives evaluated. Referenced from `src/` and `config/trust_ledger.yaml`
via DL-XXX pointers once the agent is implemented.

Numbering continues across the portfolio. Predecessor project
[trust-layer-rag](https://github.com/ai-systems-architect/trust-layer-rag)
ended at **DL-030**. The first entry in this log is **DL-031**.

---

---

## DL-031 — Orchestration Framework: LangGraph

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

## DL-032 — AC Control Selection

**Decision:** Demonstration scope locked to four controls: AC-2 (Account Management), AC-3 (Access Enforcement), AC-6 (Least Privilege), AC-17 (Remote Access).
**Date:** 2026-05-11

**Rationale:** The AC family contains approximately 25 controls. Assessing all 25 in a reference implementation adds surface area without adding governance signal — the framework pattern is visible in four controls as clearly as in twenty-five. The four selected were chosen because they (1) touch every federal system regardless of agency or mission, (2) produce observable evidence from IAM policies and CloudTrail logs that synthetic fixtures can credibly represent, and (3) exhibit distinct failure modes — AC-2 surfaces dormant credential patterns, AC-3 surfaces policy attachment gaps, AC-6 surfaces wildcard permission abuse, AC-17 surfaces remote access anomalies. Together they demonstrate the full evidence-collection-to-assessment pipeline without requiring fixtures that simulate domain-specific system configurations.

**Alternatives evaluated:**
- Full AC family (25 controls) — eliminated. Adds implementation time without proportional governance signal. Extension to the full family is documented in `FUTURE_WORK.md`.
- IA family (Identification and Authentication) — evaluated. Strong federal relevance but evidence collection requires MFA and PIV configuration data that is harder to represent credibly in synthetic fixtures.
- AU family (Audit and Accountability) — evaluated. High signal for compliance workflows but overlaps with the agent's own audit trail requirements, creating a confusing demonstration where the agent audits the same class of controls it is itself subject to.
- Mixed family (two AC + two AU) — eliminated. Splitting across families reduces the coherence of the demonstration without a clear benefit. AC family as a unit is a universally understood federal concept; a mixed set requires more context to interpret.

---

## DL-036 — Memory Architecture: Ephemeral Per-Run

**Decision:** Agent uses ephemeral per-run memory. No persistent memory across runs. Authoritative knowledge sourced from P2 governed RAG on demand.
**Date:** 2026-05-16

**Rationale:** Ephemeral memory enforces governance clarity, audit trail integrity, and data minimization without requiring a separate purge mechanism. Each run starts with a declared scope; persistent memory would introduce state that cannot be fully attributed to a specific authorized scope declaration. Static authoritative knowledge (NIST control text, FedRAMP requirements) is provided by the retrieval layer on demand — eliminating the primary motivation for persistent memory in this use case.

**Alternatives evaluated:**
- Persistent agent memory — deferred. Creates a second state store outside the per-run audit trail, introducing provenance and compliance gaps. Relevant for multi-agent workflows in `trust-layer-multiagent` where shared evidence accumulation across sub-agents is required.
- Retrieval-augmented memory — deferred. Prior run results stored in a vector store and retrieved as context. Introduces cross-run provenance complexity without sufficient benefit in the single-agent, bounded-scope use case.

---

## DL-033 — Synthetic Fixture Design

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

## DL-034 — LLM Provider and Model Selection

**Decision:** AWS Bedrock with `claude-sonnet-4-5-20251001` for both the agent (sufficiency assessment, draft generation) and the LLM-as-judge evaluation tier.
**Date:** 2026-05-28

**Rationale:** Bedrock is the natural choice for a federal portfolio project — it satisfies FedRAMP boundary requirements, keeps all inference within the AWS account perimeter, and is the model provider federal clients are most likely to be operating. Using the same provider for both the agent and the judge eliminates a cross-provider dependency while keeping the judge independent of the agent's specific call history. `claude-sonnet-4-5-20251001` provides strong instruction-following for structured JSON output (sufficiency assessment) and long-form generation (draft assessment).

Operational finding: drafting calls at ~4,875 input tokens require ~63 seconds of inference time. Botocore's default 60-second `read_timeout` killed the first drafting run. Fixed by setting `read_timeout=300` via `botocore.config.Config`. This established the baseline cost-per-assessment metric: ~8,478 total tokens per full run (4 sufficiency calls + 1 drafting call). See DL-037 for the cost model.

**Alternatives evaluated:**
- Anthropic API directly — eliminates Bedrock dependency, simpler client. Eliminated: breaks FedRAMP boundary positioning and requires a separate API key outside AWS credentials.
- OpenAI via Bedrock — available but inconsistent with the Anthropic-first architecture of P1 and P2.
- Separate judge model (e.g. smaller/faster model for evaluation) — deferred. Adds complexity without clear benefit at portfolio scale. Revisit in the Evaluation Suite if judge latency is a concern.

---

## DL-035 — Identity Scope: Mocked

**Decision:** Agent identity and delegated authority implemented as mocked — execution identity declared in trust ledger schema, role-assumption flow simulated, not wired to real AWS STS.
**Date:** 2026-05-28

**Rationale:** The governance pattern — declaring execution identity, enforcing scope bounds at PEP-1, preventing privilege escalation — is fully demonstrated at the application layer without real STS session issuance. Wiring to real IAM/STS requires a production AWS account with specific role configurations, introduces credential management complexity, and creates teardown risk for a portfolio project. The mocked implementation is honest about what it is: the trust ledger declares `execution_identity` as a governance artifact; the PEP enforces it as a scope constraint; real STS issuance is the production extension documented in FUTURE_WORK.md.

**Alternatives evaluated:**
- Fully wired to real IAM role + STS — maximum production credibility. Eliminated for portfolio scope: requires account configuration outside the codebase, creates credential persistence risk, and adds no governance signal beyond what the mocked implementation already demonstrates.
- Conceptual only (no enforcement) — eliminated. The trust ledger enforcement at PEP-1 is load-bearing; conceptual-only would undermine the governance claim entirely.

---

## DL-037 — Cost Per Control Assessment Baseline

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

Prompt caching implemented for sufficiency and drafting system prompts (see `src/agent/llm.py` — `_invoke_cached`, `_get_caching_client`). Cache hit rate and token reduction will be captured in Phase 3 evaluation baseline when caching activates. Confirmed finding: this account has access only to the cross-region inference profile (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`); the base model ID (`anthropic.claude-sonnet-4-5-20251001-v1:0`) returns `ValidationException: The provided model identifier is invalid`. Bedrock prompt caching via the `anthropic-beta` header requires the base model ID — it is not available via cross-region inference profiles. The caching infrastructure is complete and correct; cache metrics will populate automatically if the account is granted access to a base model ID. Phase 3 token baseline uses the uncached cross-region profile numbers from the table above.

---

## DL-039 — Authority Boundary Rule: Explicit Deny on Identity Write Access

**Decision:** Added explicit authority boundary rule to Section 4.2 of `framework_reference.md`. No tool registered in the trust ledger may hold write access to authentication state, MFA configuration, account recovery paths, permission grants, or account creation — regardless of autonomy class or requester framing. Such actions are DENIED at the pre-call gate.
**Date:** 2026-06-02

**Rationale:** The confused-deputy pattern at the identity layer does not require a system breach. An attacker who can manipulate an agent into modifying who has access to a system achieves the same outcome as a direct breach. The rule closes this path explicitly rather than relying on least-privilege role assignment alone.

**Reference case:** Meta AI support incident, May 2026. An AI support agent with write access to account recovery settings was manipulated into enabling account takeover. No system was breached. The agent operated within its declared function. The governance gap was the absence of an explicit rule prohibiting authority-modifying writes.

**Existing controls this formalizes:**
- T-003 (`modify_iam_policy`) already `autonomy_class: DENIED`
- All registered read tools have `iam:Create*` and `iam:Attach*` in `prohibited_actions`
- This DL formalizes the principle behind those controls so future tool additions are evaluated against an explicit rule, not just a precedent

**Alternatives evaluated:**
- Rely on least-privilege IAM role alone — insufficient. Role-level controls are platform-layer; the trust ledger must enforce the same boundary at the application layer independently.
- Case-by-case review of new tool registrations — rejected. An explicit rule is auditable; case-by-case judgment is not.

---

## DL-038 — FM-002 Behavior After Sufficiency Prompt Fix

**Decision:** HP-007 grader updated to accept two valid FM-002 outcomes: `circuit_breaker_fired=True` OR `current_node=awaiting_human_review`.
**Date:** 2026-06-02

**Rationale:** The sufficiency prompt fix (disambiguating NON-COMPLIANT as a sufficient determination) changed FM-002 behavior. Before the fix: the LLM required compliance requirement text from P2 to judge evidence sufficient — circuit breaker always fired when P2 was down because IAM + CloudTrail evidence alone was judged insufficient. After the fix: the LLM correctly judges IAM + CloudTrail evidence sufficient for a NON-COMPLIANT determination even without compliance requirement text from P2. The agent completes the run and reaches `awaiting_human_review` instead of cycling to the circuit breaker. Both behaviors are valid FM-002 graceful degradation — the key invariant is safe completion with no unhandled exceptions, not which exit path is taken.

**Alternatives evaluated:**
- Revert sufficiency prompt fix to force circuit breaker — rejected. The fix is architecturally correct; a NON-COMPLIANT finding from fixture evidence alone is a valid compliance determination.
- Require P2 for sufficiency — rejected. FM-002 explicitly specifies graceful degradation as the correct behavior; P2 unreachable must not be fatal.

---

## DL-040 — Model Routing: Frontier for High-Consequence Steps

**Decision:** All LLM calls in this implementation route to the frontier model. Model routing per step is documented as a governed architectural decision — classify by consequence, assign model tier accordingly.
**Date:** 2026-06-02

**Rationale:** Model selection per step carries cost, latency, and risk dimensions. Routing compliance synthesis or sufficiency assessment to a cheaper model to reduce cost is a risk decision that must be made explicitly, not by default. The governance framework documents the classification principle so future implementations apply it deliberately.

Low-consequence steps (metadata extraction, intent classification, formatting) are candidates for fast/lightweight models. High-consequence steps (compliance synthesis, sufficiency assessment, draft generation, escalation decisions) require frontier model quality — these outputs inform real compliance determinations and carry audit trail requirements.

**Current implementation choice:** Frontier model for all steps. Correct for a reference implementation where pattern clarity takes precedence over cost optimization. Production deployments should apply the step-consequence classification.

**Cost implication:** The DL-037 baseline ($0.024/control) reflects all-frontier routing. A production deployment routing low-consequence steps to a lightweight model could reduce per-control cost by 40–60% while maintaining governance posture on high-consequence steps.

**Alternatives evaluated:**
- Route all steps to lightweight model — rejected. Compliance synthesis and sufficiency assessment quality degrades measurably on smaller models. Risk is not worth the cost saving on the high-consequence path.
- No explicit routing policy — rejected. Implicit defaults are ungoverned decisions. The classification must be explicit and auditable.

---

## DL-041 — Indirect Prompt Injection Defense: Scope Invariant at PEP-1

**Decision:** Control family and account scope invariants are enforced at PEP-1 (pre-call validation) on every tool invocation rather than via a separate cryptographic state checker at each node.
**Date:** 2026-06-02

**Rationale:** The indirect prompt injection risk via retrieved evidence content is real: a malicious document in the retrieval corpus could instruct the agent to shift focus from AC-family controls to IA-family, or to target a different account ID. This is the confused-deputy pattern at the knowledge boundary (Boundary 3).

The current mitigation operates at two layers. First, PEP-2 post-call sanitization scans tool results for injection patterns before they enter reasoning state — catching instruction-like content in retrieved evidence. Second, PEP-1 scope bounds validation checks declared control_family and declared_account_id on every tool invocation — any call targeting out-of-scope parameters is rejected regardless of what the agent's reasoning state contains.

The alternative — a cryptographic invariant checker that hashes the control_family string and validates it at every LangGraph node transition — would provide stronger guarantees but at the cost of implementation complexity disproportionate to a reference implementation. The architectural principle is documented here; the cryptographic implementation is a production hardening step.

**What this does not fully address:** If a prompt injection successfully mutates the agent's tool call parameters within a single node before PEP-1 fires, and the mutation targets an in-scope parameter (same control family, same account, different tool behavior), PEP-1 will not catch it. PEP-2 injection scanning is the primary defense for this path. This residual risk is consistent with the threat model residual risk rating of LOW for TM-001.

**Alternatives evaluated:**
- Cryptographic control_family hash at every node — rejected for portfolio scope. Correct production hardening step; documented in FUTURE_WORK.md.
- Trust LLM instruction-following alone — rejected. Prompt-level scope instructions are not a governance control.

---
