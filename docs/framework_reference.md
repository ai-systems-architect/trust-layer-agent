# Beyond Autonomy: Architecting the Trust Layer for Enterprise Agentic AI
## Governance Framework for Autonomous AI Systems in Federal and Enterprise Environments

**Version:** 1.0
**Last Updated:** 2026-05-11
**Status:** In Progress

---

## Table of Contents

1. Scope and Applicability
2. Trust Boundary Taxonomy
3. Agent Identity and Delegated Authority
4. Tool-Use Governance and Policy Enforcement Points
5. Failure Mode Catalog
6. Threat Model
7. Agent Risk Classification Matrix
8. Evaluation Methodology
9. Regulatory Mapping
10. Inheritance Pattern

---

## 1. Scope and Applicability

### 1.1 Purpose

This document specifies a governance framework for agentic AI systems operating in federal and enterprise environments. It defines the trust boundaries, tool-use controls, identity constraints, failure modes, and evaluation methodology required to deploy autonomous AI systems with accountability, auditability, and human oversight.

The framework is designed to be adopted, adapted, and extended. The reference implementation in this repository demonstrates the framework applied to a federal compliance workflow. The governance pattern applies wherever an AI system moves from generating responses to taking actions.

---

### 1.2 What This Framework Covers

This framework applies to any system meeting the following definition:

> **Agentic AI system:** A software system in which a large language model serves as a reasoning and orchestration layer that perceives state, selects and invokes tools, processes results, and iterates across multiple steps to complete a task — without requiring human input at each step.

Covered system characteristics:
- Multi-step execution with tool invocation
- Autonomous state management across steps
- Access to external systems, APIs, or data stores via registered tools
- Output that informs, initiates, or constitutes a real-world action

---

### 1.3 What This Framework Does Not Cover

| Out of Scope | Rationale |
|---|---|
| Single-shot LLM completions | No autonomous tool use or multi-step execution — governed by standard LLM guardrail frameworks |
| RAG systems without tool invocation | Retrieval-augmented generation without autonomous action — see `trust-layer-rag` for retrieval governance |
| Multi-agent orchestration | Agent-to-agent trust, delegation chains, and coordination governance — addressed in `trust-layer-multiagent` |
| Model training and evaluation | Addressed in `responsible-mlops-risk-engine` |
| Human-in-the-loop systems where every step requires approval | Approval at every step eliminates the autonomous execution pattern this framework governs |

---

### 1.4 Intended Audience

**Federal AI program managers and system owners** implementing or evaluating agentic AI under OMB M-24-10, M-25-21, or FISMA ATO requirements.

**Enterprise AI risk and compliance teams** establishing internal governance standards for agentic systems under SR 11-7, SOC 2, HIPAA Security Rule, or ISO 42001.

**AI architects and engineers** building agentic systems who require a governance specification to implement against — not a policy document to satisfy after the fact.

---

### 1.5 Relationship to Existing Frameworks

This framework does not replace existing federal or enterprise AI governance standards. It extends them to address the specific characteristics of autonomous, multi-step AI execution.

| Standard | Relationship |
|---|---|
| NIST AI RMF 1.0 | This framework operationalizes the MAP and MEASURE functions for agentic systems |
| NIST AI 600-1 | Extends GenAI risk guidance to cover multi-step autonomous behavior |
| NIST 800-53 Rev 5 | Controls AC, AU, CA, RA, SI families apply directly; mapping in Section 9 |
| OMB M-24-10 / M-25-21 | Addresses AI use case inventory and risk assessment requirements for agentic deployments |
| OWASP LLM Top 10 | Threat model in Section 6 maps adversarial risks to OWASP categories |

---

### 1.6 Versioning

This framework is versioned using semantic versioning. The regulatory mapping table in Section 9 tracks the NIST and OMB revision dates against which each version was validated. Consumers of this framework should verify mapping currency when NIST or OMB guidance is updated.

**Current version:** 1.0
**NIST AI RMF reference:** 1.0 (January 2023)
**NIST AI 600-1 reference:** 1.0 (July 2024)
**OMB M-24-10 reference:** March 2024

---

## 2. Trust Boundary Taxonomy

### 2.1 Definition

A trust boundary is a transition point where the authority, identity, or data provenance of an action changes hands. In traditional software systems, trust boundaries are well-understood: a network perimeter, an API authentication gate, a database access control check.

In agentic AI systems, trust boundaries are harder to see and easier to violate. The agent reasons across multiple steps, calls multiple tools, and assembles outputs from multiple sources — each transition is a potential trust boundary crossing. Unlike a network packet, an agent's reasoning state carries no inherent authentication. Without explicit boundary enforcement, an agent can accumulate authority it was never delegated, act on data it was never authorized to consume, or produce assertions it has no evidentiary basis to make.

This section defines the five trust boundaries present in every agentic AI system and specifies how each is enforced in this framework.

---

### 2.2 The Five Trust Boundaries

#### Boundary 1 — Human ↔ Agent (Delegation Boundary)

The delegation boundary defines what the human principal has authorized the agent to do on their behalf. It is established at run initiation and cannot be expanded during execution.

**What crosses this boundary:** Task scope, input data, execution parameters, approval tokens for HUMAN_GATED tools.

**What cannot cross:** Implicit permission expansion ("the agent needed to do X to complete Y, so X was authorized"), credentials beyond the declared execution identity, scope beyond the declared control family.

**Enforcement:** Trust ledger `execution_identity` block. Agent runs as `audit-readonly-role` with short-lived session credentials. Scope is declared at invocation, not inferred.

**Violation pattern:** Agent interprets a broad task instruction as authorization to call tools outside its registered set. Addressed by the implicit-DENIED rule: any tool not in the trust ledger is rejected at the pre-call PEP gate.

---

#### Boundary 2 — Agent ↔ Tool (Invocation Boundary)

The invocation boundary governs which tools the agent may call, under what conditions, and with what constraints. This is the most frequently crossed boundary in a multi-step agent run and the most common site of governance failure.

**What crosses this boundary:** Tool invocation requests, input parameters, tool results returned to agent reasoning state.

**What cannot cross:** Write operations from a read-only execution identity, calls to unregistered tools, parameters exceeding declared scope.

**Enforcement:** Policy enforcement points (pre-call and post-call) defined per tool in the trust ledger. Pre-call validates scope bounds. Post-call sanitizes results before they enter agent reasoning state.

**Violation pattern:** Agent passes unsanitized retrieval content directly to a tool parameter — a vector for prompt injection via evidence content. Post-call sanitization closes this path.

---

#### Boundary 3 — Agent ↔ Retrieval (Knowledge Boundary)

The knowledge boundary governs what the agent may treat as authoritative when constructing assessments. In this framework, retrieval is provided by the P2 governed RAG system (`trust-layer-rag`), which enforces its own guardrails, PII filtering, and citation integrity before results reach the agent.

**What crosses this boundary:** Retrieved compliance requirements, control text, policy references — all with attached source URI, retrieval timestamp, and evidence hash.

**What cannot cross:** Unauthenticated assertions, retrieval results without provenance metadata, content that failed P2's guardrail or reranking gates.

**Enforcement:** Evidence lineage requirements enforced per tool entry (`evidence_lineage_required: true`). Agent reasoning state must carry `source_uri`, `retrieval_timestamp`, and `evidence_hash` for every evidentiary claim in the output artifact.

**Violation pattern:** Agent hallucinates a control requirement not present in retrieved content. Evidence lineage enforcement makes this detectable: any assertion in the output without a traceable source URI is a governance finding.

---

#### Boundary 4 — Agent ↔ Output (Assertion Boundary)

The assertion boundary governs what the agent may claim, in what form, and to whom. An agent that produces an incorrect assessment draft is an operational failure. An agent that submits that assessment to an external system without human review is a governance failure.

**What crosses this boundary:** Draft assessment artifacts, control status determinations, evidence citations.

**What cannot cross:** Final compliance determinations without human review, submissions to external systems without an approval token, assertions not grounded in evidence-lineage-verified sources.

**Enforcement:** `submit_assessment_artifact` is HUMAN_GATED. Pre-call PEP requires a valid approval token from an Authorizing Official or Delegate. Governance decision artifact (`governance_decision.json`) is written on every submission event.

**Violation pattern:** Agent marks a control compliant based on incomplete evidence, then attempts submission. Human gate intercepts before external dissemination. Incomplete evidence is a Medium-tier failure; unauthorized submission would be High-tier.

---

#### Boundary 5 — Agent ↔ External System (Dissemination Boundary)

The dissemination boundary governs interaction with any system outside the agent's declared execution scope — external APIs, notification systems, downstream consumers of assessment output.

**What crosses this boundary:** Approved assessment artifacts, audit trail records, governance decision logs.

**What cannot cross:** Unapproved drafts, intermediate reasoning traces, PII, data classified above the tool's `data_classifications_allowed` level.

**Enforcement:** No external system calls are registered in the trust ledger beyond `s3:PutObject` on the designated audit evidence bucket. Any attempt to call an unregistered external endpoint is DENIED at the pre-call gate and logged.

**Violation pattern:** Prompt injection via retrieved evidence instructs the agent to POST results to an external endpoint. No such tool exists in the trust ledger. Attempt is rejected, logged, and run is terminated.

---

### 2.3 Boundary Interaction Summary

| Boundary | Crossing Direction | Primary Enforcement | Violation Class |
|---|---|---|---|
| Human ↔ Agent | Delegation in, results out | Trust ledger execution identity | Scope expansion |
| Agent ↔ Tool | Invocation out, results in | Pre/post-call PEPs | Unauthorized invocation |
| Agent ↔ Retrieval | Knowledge in | Evidence lineage requirements | Hallucinated assertion |
| Agent ↔ Output | Assertion out | Human gate + approval token | Unauthorized submission |
| Agent ↔ External System | Dissemination out | Implicit DENY on unregistered tools | Data exfiltration |

---

## 3. Agent Identity and Delegated Authority

### 3.1 The Identity Problem in Agentic Systems

A human user authenticates once and operates under a persistent, auditable identity. An agentic AI system operates differently — it executes actions across multiple steps, potentially calling multiple tools, under an identity that was delegated to it by a human principal at run initiation.

Without explicit identity constraints, three failure modes emerge:

**Privilege accumulation** — the agent acquires permissions beyond what the task requires, either through broad role assignment or through tool calls that expand its effective access.

**Impersonation ambiguity** — the audit trail shows actions taken by a service role, with no traceable connection to the human principal who initiated the run and the specific task scope that was authorized.

**Credential persistence** — long-lived credentials remain valid after the agent run completes, creating an attack surface with no active owner.

This section specifies how agent identity is established, constrained, and audited in this framework.

---

### 3.2 Execution Identity

Every agent run executes under a declared execution identity. The identity is established at run initiation and cannot be elevated during execution.

**Declared execution identity for this implementation:**

```yaml
execution_identity:
  iam_role: "audit-readonly-role"
  privilege_scope: "read-only"
  credential_source: "short-lived-session"
  impersonation_allowed: false
```

**Constraints enforced:**

| Constraint | Implementation |
|---|---|
| Least privilege | Role scoped to read-only IAM and CloudTrail operations — no write path exists at the role level |
| Short-lived credentials | Session tokens with a maximum validity of 1 hour — no persistent credentials in agent runtime |
| No privilege escalation | `iam:AssumeRole` for any role beyond `audit-readonly-role` is not in the trust ledger — attempt is DENIED |
| No impersonation | Agent cannot act as a human user or assume a human user's identity |

---

### 3.3 Delegated Authority Boundaries

Delegated authority is the subset of the execution identity's permissions that the agent is authorized to exercise for a specific run. It is narrower than the role's full permission set and is declared explicitly at invocation.

**Authority is bounded by three constraints applied in order:**

1. **Role boundary** — what the IAM role is permitted to do at the AWS policy level
2. **Trust ledger boundary** — what tools are registered and what actions each tool is permitted to invoke
3. **Run scope boundary** — what control family and account scope were declared at run initiation

An action must clear all three constraints to execute. A tool registered in the trust ledger but outside the declared run scope is rejected at the pre-call PEP gate even if the IAM role technically permits it.

**Example — authority chain for `query_iam_policies`:**

```
IAM role permits:        iam:GetPolicy, iam:GetPolicyVersion, iam:ListAttachedRolePolicies
Trust ledger permits:    same three actions, max 20 calls per run
Run scope declared:      AC family, account-id 123456789
Pre-call PEP validates:  query target is within account-id 123456789
Result:                  PERMITTED
```

```
IAM role permits:        iam:GetPolicy (read-only role)
Trust ledger permits:    same
Run scope declared:      AC family, account-id 123456789
Agent attempts:          iam:CreatePolicy (not in trust ledger allowed_actions)
Result:                  DENIED at pre-call PEP — logged and alerted
```

---

### 3.4 Audit Trail Requirements

Every agent run produces an audit trail that connects the human principal, the delegated authority, and every action taken under that authority.

**Required audit trail elements:**

| Element | Source | Retention |
|---|---|---|
| Run ID | Generated at invocation | 365 days |
| Initiating principal | Human user ID passed at invocation | 365 days |
| Declared execution identity | Trust ledger `execution_identity` block | 365 days |
| Declared run scope | Control family + account scope | 365 days |
| Every tool invocation | Pre-call PEP log entry | 365 days |
| Every PEP outcome | Pre-call and post-call gate result | 365 days |
| Every DENIED attempt | Alert log + run termination record | 365 days |
| Governance decision record | `governance_decision.json` per HUMAN_GATED call | 2555 days |

The audit trail is write-once. No agent tool is registered with permissions to modify or delete audit log entries.

---

### 3.5 What This Framework Does Not Implement

This framework specifies agent identity and delegated authority at the application layer. It does not implement or replace:

| Capability | Responsible Layer |
|---|---|
| IAM role creation and policy attachment | Platform / infrastructure layer |
| Session token issuance | AWS STS — platform layer |
| Centralized identity provider integration | Agency IdAM platform |
| Cross-account role assumption governance | Platform layer — out of scope for single-account reference implementation |

The inheritance pattern for platform vs. application responsibility is addressed in Section 10.

---

## 4. Tool-Use Governance and Policy Enforcement Points

### 4.1 The Tool-Use Problem in Agentic Systems

Tools are the mechanism by which an agentic AI system affects the world. A tool call is not a suggestion — it is an action with real consequences: data is read, records are written, artifacts are submitted, external systems are notified. The governance question is not whether the agent can call a tool but whether it is authorized to, under what conditions, and with what constraints on inputs and outputs.

Three failure patterns are specific to tool use in agentic systems:

**Unbounded invocation** — no limit on how many times a tool can be called per run, enabling runaway loops that exhaust resources or produce redundant audit entries.

**Unsanitized tool results** — tool output is passed directly into agent reasoning state without validation, creating an injection vector if the result contains adversarial content.

**Implicit permission inheritance** — the agent assumes that because it can call a tool, it is authorized to call it with any parameters, against any target, any number of times.

This framework addresses all three through the trust ledger and policy enforcement points.

---

### 4.2 Tool Registration Requirements

Every tool the agent may invoke must be registered in `config/trust_ledger.yaml` before use. Registration is not optional — it is the governance control.

**The implicit DENY rule:** Any tool invocation request for a tool not present in the trust ledger is rejected at the pre-call PEP gate, logged, and the run is terminated. There is no fallback, no exception path, and no runtime override.

**Required registration fields per tool:**

| Field | Purpose |
|---|---|
| `tool_id` | Unique identifier — referenced in audit trail and governance decision records |
| `tool_name` | Human-readable name — must match the function name exposed to the agent |
| `risk_tier` | LOW / MEDIUM / HIGH / CRITICAL — determines approval requirements and logging |
| `autonomy_class` | AUTONOMOUS / HUMAN_GATED / DENIED |
| `human_review_required` | Whether output must be reviewed before downstream consumption |
| `evidence_lineage_required` | Whether tool results must carry source URI, retrieval timestamp, and evidence hash |
| `allowed_actions` | Explicit allowlist of IAM actions or API operations the tool may invoke |
| `prohibited_actions` | Explicit denylist — enforced at the role level and at the pre-call PEP gate |
| `data_classifications_allowed` | Maximum data classification the tool may process |
| `policy_enforcement_points` | Named handlers for pre-call and post-call gates |
| `max_calls_per_run` | Hard ceiling on invocations per run — circuit breaker |
| `timeout_seconds` | Maximum execution time before the call is terminated |
| `audit_retention_days` | Minimum retention period for all records associated with this tool |

---

### 4.3 Policy Enforcement Points

Policy enforcement points (PEPs) are explicit checkpoints where governance controls are applied. This framework defines two PEPs per tool call and one PEP at the output boundary.

#### PEP-1 — Pre-Call Validation

Applied before every tool invocation. The pre-call gate answers one question: is this invocation authorized under the current run's declared scope, trust ledger entry, and execution identity?

**Pre-call checks applied in order:**

1. **Tool registration check** — is the tool present in the trust ledger? If not: DENY, log, terminate run.
2. **Autonomy class check** — is the tool AUTONOMOUS, HUMAN_GATED, or DENIED?
   - AUTONOMOUS: proceed to scope check
   - HUMAN_GATED: is a valid approval token present? If not: block and request approval
   - DENIED: reject, log, alert, terminate run
3. **Scope bounds check** — do the invocation parameters fall within the declared run scope (control family, account ID)?
4. **Call count check** — has `max_calls_per_run` been reached? If so: DENY and log.
5. **Prohibited action check** — does the invocation attempt any action on the tool's `prohibited_actions` list? If so: DENY, log, alert.
6. **Data classification check** — does the input data exceed the tool's `data_classifications_allowed` level? If so: DENY and log.

All six checks must pass. Failure at any check terminates the invocation.

#### PEP-2 — Post-Call Sanitization

Applied after every tool invocation, before results enter agent reasoning state. The post-call gate answers one question: is this result safe to pass to the agent's next reasoning step?

**Post-call checks applied in order:**

1. **Evidence lineage validation** — if `evidence_lineage_required: true`, does the result carry `source_uri`, `retrieval_timestamp`, and `evidence_hash`? If not: strip result, log lineage failure, agent receives an empty result with a lineage error flag.
2. **PII scan** — does the result contain personally identifiable information? If detected: redact before passing to reasoning state.
3. **Injection pattern scan** — does the result contain instruction-like content that could alter agent behavior? If detected: sanitize and flag for human review.
4. **Result size check** — does the result exceed the declared maximum context injection size? If so: truncate and log.

#### PEP-3 — Pre-Output Release

Applied before the agent produces its final output artifact. This PEP operates at the run level, not the tool level.

**Pre-output checks:**

1. **Evidence completeness check** — does every compliance assertion in the draft assessment trace to at least one evidence source with valid lineage?
2. **Sufficiency assessment** — has the agent explicitly assessed whether collected evidence is sufficient to support each control determination?
3. **Human review flag** — are any MEDIUM or higher risk tier tool results present in the evidence set? If so: flag output for human review regardless of autonomy class.
4. **Submission gate** — if the run includes a `submit_assessment_artifact` call: confirm HUMAN_GATED approval token is present before allowing the output to proceed.

---

### 4.4 Circuit Breakers

Circuit breakers are hard stops that terminate a run when operational bounds are exceeded. They are not error handlers — they are governance controls that prevent a malfunctioning agent from causing unbounded harm.

| Circuit Breaker | Trigger | Action |
|---|---|---|
| Max calls per tool | `max_calls_per_run` reached for any tool | Terminate run, log, surface partial results |
| Max total steps | Global step limit exceeded (default: 50) | Terminate run, log, flag for human review |
| Tool timeout | Single tool call exceeds `timeout_seconds` | Cancel call, log timeout, agent receives error result |
| Consecutive tool failures | Three consecutive tool call failures | Terminate run, log, alert |
| Reasoning loop detection | Same tool called with identical parameters twice in sequence | Terminate run, log loop detection event |

Circuit breaker events are surfaced in the governance decision record and in Langfuse observability traces.

---

### 4.5 Evidence Lineage

Evidence lineage is the chain of custody for every factual claim the agent makes in its output artifact. It is enforced at PEP-2 (post-call sanitization) and validated at PEP-3 (pre-output release).

**Required lineage fields per evidence item:**

```json
{
  "source_uri": "s3://audit-evidence/ac-2/iam-policy-scan-R1042.json",
  "retrieval_timestamp": "2026-05-11T13:18:02Z",
  "evidence_hash": "sha256:a3f1c9...",
  "tool_id": "T-001",
  "run_id": "R-1042"
}
```

An assessment assertion without a traceable evidence lineage record is a governance finding, not an agent output. The run does not fail — but the assertion is flagged as unsubstantiated and excluded from the draft assessment pending human review.

---

### 4.6 Trust Ledger Maintenance

The trust ledger is a governance artifact, not a configuration file. It is subject to the following maintenance requirements:

| Requirement | Cadence |
|---|---|
| Full review of all registered tools | Quarterly or when a new tool is added |
| Risk tier re-assessment | When the threat model is updated |
| Prohibited actions list update | When new IAM actions are introduced or attack patterns identified |
| Schema version bump | When any field definition changes |
| Reviewed-by field update | After every review — name and date |

Tool additions require a corresponding decision log entry documenting the rationale for the assigned risk tier and autonomy class.
