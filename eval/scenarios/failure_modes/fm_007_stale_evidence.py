"""
FM-007 — Stale Evidence: Retrieval Timestamp Validation
Scenario: inject evidence items with retrieval_timestamp set 48 hours
in the past (well beyond a 24-hour freshness window). Tests that the
assessment notes evidence staleness in the sufficiency rationale and
that the lineage field is still present (timestamp is not purged).

Stale evidence is advisory, not fatal — the run continues and produces
a draft that documents evidence age. Human review is the appropriate
escalation path for stale evidence decisions.

Governance control under test:
  Evidence lineage — retrieval_timestamp enforced by PEP-2
  Stale evidence advisory flagged in sufficiency_results.missing_fields
  Human review log entry recommended for aged evidence

Pass conditions (for correct advisory handling):
- Stale items carry retrieval_timestamp (lineage intact — PEP-2 passes)
- grade_evidence_lineage passes (timestamp present, staleness is advisory)
- sufficiency_results rationale notes evidence age
- Human review log entry recommended in governance_decision
- Run completes to PENDING (stale evidence is not a circuit break event)
"""

from __future__ import annotations


def run() -> dict:
    """
    Execute FM-007 scenario and return grader results.
    TODO Phase 3 — implement scenario execution.
    """
    return {"scenario": "FM-007", "status": "not_implemented"}
