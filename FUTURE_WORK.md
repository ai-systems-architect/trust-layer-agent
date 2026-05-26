# Future Work

Scope deliberately deferred from this project. Each item below is documented to signal that it has been considered and intentionally excluded — not overlooked.

---

### Production Required

**Real telemetry integration.** The agent operates against synthetic IAM policies and CloudTrail event fixtures. Connecting to real AWS IAM, real CloudTrail, and real ticketing systems requires production AWS account permissions, sample-data handling agreements, and a security review that exceeds portfolio scope. The integration pattern is documented in `docs/framework_reference.md`; the wiring is intentionally not built. Required when this codebase is adopted for any real federal program. Trigger: a sponsoring program with the necessary authorities and a target environment.

**Identity and delegated authority — mocked → wired.** The framework specifies agent identity, scoped credentials, and impersonation prevention. The trust ledger declares the execution identity (`audit-readonly-role`, short-lived session credentials, impersonation disallowed) at the schema layer. A mocked role-assumption flow is in scope for Agent Implementation; wiring it to a real IAM role with STS session issuance is production work, not portfolio work.

---

### Stretch

**Multi-control coverage.** Extend the agent from the AC-family demonstration to AU (audit logging), IA (identification and authentication), and CM (configuration management). The framework is control-family-agnostic; AC was selected as the demonstration family because it touches every federal system and the failure modes are visible to non-specialist reviewers (see DL-031). Extension follows the pattern documented in `docs/framework_reference.md`. Each additional family is roughly the same effort as the original AC implementation.

**Enterprise framework mappings.** Translate the federal mappings (NIST AI RMF, OMB M-24-10 / M-25-21, FedRAMP, 800-53) to: **SR 11-7** (banking model risk management), **HIPAA Security Rule** (health information audit workflows), **SOC 2 Type II** (evidence collection), and **ISO 27001 / 42001** (internal audit and AI management system). These translations are written work — articles that cite this codebase as the substrate — not additional code in this repository.

**Continuous monitoring agent variant.** Apply the same governance framework to a runtime ConMon agent rather than a periodic assessment agent. Same trust ledger pattern, different PEP behavior (streaming vs. batch), different reasoning trace cadence (every detection vs. every assessment). Documented as a pattern extension; reference implementation deferred.

**Operational observability dashboards.** The Evaluation Suite captures input tokens, state transition latency, tool call frequency, and cache hit rates per run. Building a hosted dashboard surface over that data (Grafana over Langfuse, or similar) is a separate engineering exercise. The instrumentation is the load-bearing part; the dashboard is presentation.

---

### Considered and Deferred

**Multi-agent orchestration governance.** [`trust-layer-multiagent`] Planner-executor patterns, agent-to-agent messaging, and multi-agent state synchronization governance are deliberately out of scope for this project. The single-agent constraint is what makes this codebase tractable and what makes the `trust-layer-agent` → `trust-layer-multiagent` portfolio progression coherent. Multi-agent governance is the subject of `trust-layer-multiagent` in this portfolio arc, not an extension of this one.

**Self-correction loop.** [`trust-layer-multiagent`] Re-attempt evidence collection with a broadened search radius when the sufficiency-assessment state determines evidence is incomplete. Evaluated and deferred for the single-agent case: the human-gated review at `awaiting-human-review` provides the correctness floor, and the re-attempt pattern is more appropriate for multi-agent workflows where one agent's confidence judgment feeds another agent's next action. Reconsider in `trust-layer-multiagent`.

**Direct LLM SDK orchestration vs. LangGraph.** LangGraph was selected (DL-030). A hand-rolled state machine over the model SDK directly remains viable if LangGraph's reasoning trace integration proves insufficient during Agent Implementation — the governance pattern is framework-agnostic and transfers cleanly. No further evaluation required unless Agent Implementation surfaces a blocker.
