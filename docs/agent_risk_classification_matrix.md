# Agent Risk Classification Matrix

**Version:** 1.0  
**Last Reviewed:** 2026-05-11  
**Scope:** Applies to all tools registered in `config/trust_ledger.yaml`

---

## Classification Tiers

| Risk Tier | Example Agent Actions | Autonomy Class | Human Approval Required | Failure Impact | Logging Requirement |
|---|---|---|---|---|---|
| **Low** | Read policy documents, retrieve compliance requirements, search CloudTrail | AUTONOMOUS | No | Localized incorrect retrieval | Structured audit log, 365-day retention |
| **Medium** | Cross-source aggregation, sufficiency assessment, draft generation | AUTONOMOUS | No — output flagged for review | Incomplete or misleading assessment draft | Full reasoning trace + token counts, 365-day retention |
| **High** | Submit assessment artifact, external dissemination | HUMAN_GATED | Yes — Authorizing Official or Delegate | Incorrect compliance assertion or external dissemination | Approval event + submitter identity, 2555-day retention |
| **Critical** | Modify IAM policies, delete records, assume elevated roles | DENIED | Not applicable | Unauthorized system modification or privilege escalation | Attempt logged and alerted, 365-day retention |

---

## Autonomy Class Definitions

| Class | Behavior |
|---|---|
| `AUTONOMOUS` | Agent executes without pause. Output may still be flagged for human review depending on `human_review_required` in the tool entry. |
| `HUMAN_GATED` | Execution is blocked until an explicit approval token is received from a qualified approver. No fallback execution path. |
| `DENIED` | Execution is rejected at the pre-call PEP gate regardless of context. Attempt is logged and alerted. Run terminates. |

---

## Tier Assignment Criteria

A tool's risk tier is determined by the **worst-case failure impact** of that tool executing incorrectly or under adversarial conditions — not by its intended happy-path behavior. Reversibility is a primary criterion — actions with no recovery path are assigned a higher tier regardless of intent.

| Factor | Increases Tier |
|---|---|
| Write access to any system | +1 tier minimum |
| External dissemination of output | +1 tier minimum |
| IAM or access control modification | Escalates to CRITICAL |
| Output consumed by downstream automated system | +1 tier |
| No reversibility on action | +1 tier |

---

## Notes

- Tier assignments are reviewed when tools are added, modified, or when the threat model is updated.
- The matrix is a governance artifact, not a technical constraint. Enforcement is implemented via `policy_enforcement_points` in `trust_ledger.yaml`.
- Future work: map tiers to OMB M-24-10 impact levels (Low / Moderate / High) for ATO alignment.
