# Future Work

Scope deliberately deferred from this project. Each item below is documented to
signal that it has been considered and intentionally excluded — not overlooked.

## Multi-control coverage (Phase 6)

Extend from the AC-family demonstration to AU (audit logging), IA (identification
and authentication), and CM (configuration management). The framework is
control-family-agnostic; AC was selected as the demonstration family because it
touches every federal system and is universally relevant. Extension follows the
pattern documented in `docs/framework.md`.

## Real telemetry integration (Phase 7)

Connecting the agent to real CloudTrail, real IAM, and real ticketing systems.
Requires production AWS permissions, sample data handling, and security review
that exceeds portfolio scope. The integration pattern is documented in the
framework; the wiring is not built.

## Multi-agent extension

Planner-executor patterns, agent-to-agent messaging, and multi-agent orchestration
governance. This is the subject of a separate project (P4 in the portfolio arc)
and is deliberately not added to this single-agent demonstration.

## Continuous monitoring (Phase 9)

Applying the same governance framework to runtime ConMon agents rather than
periodic assessment. Same pattern, different cadence and PEP behavior.

## Enterprise framework mappings (Phase 10)

Translating the federal mappings (NIST AI RMF, OMB, FedRAMP, 800-53) to:

- **SR 11-7** — banking model risk management.
- **HIPAA Security Rule** — health information audit workflows.
- **SOC 2** — Type II evidence collection.
- **ISO 27001 / 42001** — internal audit and AI management system.

These translations are written work (articles), not additional code.
