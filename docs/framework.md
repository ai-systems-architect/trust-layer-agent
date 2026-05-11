# Agentic AI Governance Framework for Federal Compliance Workflows

**Status:** Drafting (Phase 1).
**Version:** 0.1.0-draft.
**Scope:** Governance pattern for autonomous, multi-step AI agents performing federal
compliance work. Demonstrated against NIST 800-53 Rev 5 Access Control evidence
collection; pattern is control-family-agnostic.

---

> This document is the consulting deliverable. The agent under `src/` is the
> demonstration that the pattern works. Sections below are placeholders for the
> Phase 1 build — to be filled in order. Each section header is a commitment to
> address that topic before Phase 1 closes.

## 1. Scope and applicability

What this framework governs (agentic systems with tool use, persistent state across
steps, and non-deterministic reasoning) vs. what it does not (single-shot LLM calls,
classical ML inference, deterministic automation).

## 2. Trust boundary taxonomy

The three-class partition that every action falls into:

- **Autonomous actions** — agent may take without prior human approval.
- **Human-approved actions** — agent must request approval, present rationale, and
  wait for an explicit affirmative.
- **Prohibited actions** — agent must not take under any condition; PEPs enforce.

## 3. Tool-use governance

Tool registration, allowlisting, schema requirements, audit hooks, and the binding
between each tool and its trust class. The **trust ledger** (a versioned config
artifact in the repo) is the source of truth.

### 3.1 Trust ledger schema

To be drafted. Candidate fields: `tool_name`, `autonomy_class`, `required_approver_role`,
`pep_pre_handler`, `pep_post_handler`, `audit_retention_days`, `data_classifications_allowed`.

## 4. Reasoning trace requirements

What must be captured at every state transition and every tool call, retention
duration, access controls on the trace store, and the minimum trace fidelity
required to reconstruct an agent run for after-the-fact audit.

## 5. Policy Enforcement Points (PEPs)

Three named checkpoints:

1. **Pre-tool-call validation** — argument inspection, authority check, trust-class
   gate against the ledger.
2. **Post-tool-call sanitization** — output inspection for sensitive data, injected
   instructions, schema violations.
3. **Pre-output release review** — final assessment artifact gated against the
   trust ledger and (where required) human approval.

## 6. Failure mode catalog

Operational and adversarial failure modes the framework anticipates. Each entry
specifies the failure, how PEPs / reasoning traces detect it, and the expected
agent response.

Initial candidates:

- Hallucinated progress (agent claims an evidence source was checked when it was not).
- Infinite reasoning loops / non-convergence.
- Tool misuse (correct tool called with semantically wrong arguments).
- Prompt injection via retrieved evidence content.
- Cascading errors across agent steps (early bad inference poisons later state).
- Confused-deputy: agent persuaded to use its delegated authority on behalf of
  an unauthorized requester.
- Tool result contradicts prior reasoning — does the agent update or anchor?

## 7. Threat model

Adversary classes and their capabilities. Out-of-scope adversaries are explicit.
Includes: insider misuse, compromised retrieval corpus, prompt injection in
ingested evidence, agent-as-confused-deputy.

## 8. Agent identity and delegated authority

Which IAM role the agent runs as, how its authority is bounded, how scoped
credentials are issued, and how impersonation is prevented. Zero-trust alignment.

## 9. Data classification handling

How the agent recognizes and refuses to process inputs above its authorized
classification level. Ledger binding for classification-allowed-set per tool.

## 10. Evaluation methodology

The three-tier grader strategy:

- **Code-based graders** — deterministic assertions (refusal fired, citation present,
  PEP blocked the action).
- **LLM-as-judge** — qualitative grading where determinism is wrong (was a hedge
  justified given the compliance context?).
- **Human review** — edge cases, high-stakes outputs, and disagreements between
  the first two tiers.

## 11. Agent risk classification matrix

| Risk tier | Example | Autonomy allowed | Human approval |
|-----------|---------|------------------|----------------|
| Low       | TBD     | TBD              | TBD            |
| Moderate  | TBD     | TBD              | TBD            |
| High      | TBD     | TBD              | TBD            |
| Critical  | TBD     | TBD              | TBD            |

Aligns with OMB / NIST impact-based language.

## 12. Mapping to federal frameworks

- **NIST AI RMF** — Govern / Map / Measure / Manage alignment.
- **NIST AI 600-1** — Generative AI profile coverage and the agentic extensions
  not yet codified.
- **OMB M-24-10 / M-25-21** — use case inventory, risk assessment, minimum practices.
- **FedRAMP** — ConMon implications for agent-driven assessment.
- **NIST 800-53 Rev 5** — AC, AU, CA, RA, SI family touchpoints.

## 13. Inheritance pattern

What an agency platform provides (identity, logging substrate, key management,
network controls) vs. what the application provides (trust ledger, PEPs,
reasoning trace store, eval harness).

## 14. Versioning and revision

How this framework is versioned, how mappings to underlying federal guidance are
updated as that guidance evolves, and the deprecation pathway for superseded
sections.

---

## Appendix A — Worked failure examples

(Populated in Phase 3 from real agent runs.)
