# Decision Log

Running record of architectural and scoping decisions for this project. Numbering
continues the sequence from the P2 (retrieval governance) decision log so the
portfolio reads as one coherent arc across projects.

> **TODO — starting number.** Confirm the next DL number from P2's final entry and
> renumber the first entry below accordingly. Format below is a placeholder; adjust
> to match P2's exact format if it differs.

## Entry format

```
## DL-NNN: <short title>

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by DL-MMM | Reversed
**Phase:** 1 | 2 | 3 | 4 | 5

**Context.** What problem or choice prompted this decision.

**Decision.** What was chosen.

**Alternatives considered.** What was rejected and why.

**Consequences.** What this commits us to, what it precludes, and what would
trigger a revisit.
```

## Pending decisions (to be logged when made)

- Orchestration framework choice: LangGraph vs. hand-rolled state machine over
  the Anthropic SDK directly. Governance auditability is the dominant criterion.
- Specific AC controls in scope (candidates: AC-2, AC-3, AC-6, AC-17).
- Trust ledger schema (YAML vs. JSON; required fields; PEP handler binding).
- Identity & delegated authority: conceptual-only vs. mocked role-assumption.
- LLM provider and model selection for the agent and for the LLM-as-judge tier.
- Synthetic fixture format and adversarial seed cases (prompt injection in
  retrieved evidence).

---

<!-- Real entries begin below. -->
