# trust-layer-agent

A reference implementation of accountable autonomous AI for federal compliance workflows.

This repository is the demonstration vehicle for an **agentic governance framework** — a
documented pattern, with a working agent showing it in action, for how federal programs
(and adjacent enterprise risk domains) can deploy autonomous AI with defensible governance.

The framework is the deliverable; the agent is the proof it works.

## Project status

**Phase 1 — Governance framework document.** In progress. See [docs/framework.md](docs/framework.md).

The build is phased so that each phase produces a portfolio-ready artifact and can be
stopped without leaving the work half-finished. Decisions captured in
[docs/decision_log.md](docs/decision_log.md). Deferred scope tracked in
[FUTURE_WORK.md](FUTURE_WORK.md).

## Repository layout

```
docs/
  framework.md        — the governance framework (Phase 1 deliverable)
  decision_log.md     — running record of architectural decisions
src/                  — agent implementation (Phase 2)
eval/                 — evaluation scenarios and graders (Phase 3)
FUTURE_WORK.md        — documented but unbuilt scope
```

## Demonstration scope

The agent demonstrates governance over **NIST 800-53 Rev 5 Access Control (AC) family**
evidence collection — specifically a focused subset of AC controls, against synthetic
IAM and CloudTrail fixtures. Scope is deliberately narrow so the governance instrumentation
can be deep. See `docs/framework.md` for the specific control selection and rationale.

## License

MIT — see [LICENSE](LICENSE).
