"""
Trust ledger loader and validator.

Loads config/trust_ledger.yaml and exposes a typed model for use by the
graph and Policy Enforcement Points. Any tool not present in the ledger is
an implicit DENY — callers must treat a None return from get_tool() as a
hard rejection, not a soft miss.

References:
    Framework Section 4: Tool-Use Governance and Policy Enforcement Points
    Framework Section 4.2: Trust Ledger Registration Requirements
    config/trust_ledger.yaml: governance artifact (schema_version 1.0)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, field_validator
from pydantic import ConfigDict

logger = logging.getLogger(__name__)


class PolicyEnforcementPoints(BaseModel):
    """PEP handler names bound per tool in the trust ledger."""

    model_config = ConfigDict(extra="allow")

    pre_call: Optional[str] = None
    post_call: Optional[str] = None


class ToolEntry(BaseModel):
    """Single registered tool entry from the trust ledger."""

    model_config = ConfigDict(extra="allow")

    tool_id: str
    tool_name: str
    description: str = ""
    autonomy_class: str   # AUTONOMOUS | HUMAN_GATED | DENIED
    risk_tier: str        # LOW | MEDIUM | HIGH | CRITICAL
    human_review_required: Optional[bool] = None
    evidence_lineage_required: Optional[bool] = None
    required_evidence_fields: List[str] = []
    required_approver_role: Optional[str] = None
    allowed_actions: List[str] = []
    prohibited_actions: List[str] = []
    data_classifications_allowed: List[str] = []
    policy_enforcement_points: Optional[PolicyEnforcementPoints] = None
    max_calls_per_run: int = 0
    timeout_seconds: int = 0
    audit_retention_days: int = 365

    @field_validator("autonomy_class")
    @classmethod
    def validate_autonomy_class(cls, v: str) -> str:
        valid = {"AUTONOMOUS", "HUMAN_GATED", "DENIED"}
        if v not in valid:
            raise ValueError(f"autonomy_class must be one of {valid}, got '{v}'")
        return v

    @field_validator("risk_tier")
    @classmethod
    def validate_risk_tier(cls, v: str) -> str:
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v not in valid:
            raise ValueError(f"risk_tier must be one of {valid}, got '{v}'")
        return v


class ExecutionIdentity(BaseModel):
    """Declared execution identity for the agent run."""

    model_config = ConfigDict(extra="allow")

    iam_role: str
    privilege_scope: str
    credential_source: str
    impersonation_allowed: bool


class TrustLedger(BaseModel):
    """Validated trust ledger loaded from YAML."""

    schema_version: str
    last_reviewed: Optional[str] = None
    reviewed_by: Optional[str] = None
    execution_identity: ExecutionIdentity
    # Keyed by tool_id for fast lookup.
    tools: Dict[str, ToolEntry]


def load_trust_ledger(path: str = "config/trust_ledger.yaml") -> TrustLedger:
    """
    Load and validate the trust ledger from YAML.

    Raises FileNotFoundError if the ledger is missing — the agent must not
    start without a validated trust ledger.
    """
    ledger_path = Path(path)
    if not ledger_path.exists():
        raise FileNotFoundError(
            f"Trust ledger not found at '{path}'. "
            "Ensure config/trust_ledger.yaml is present before starting the agent."
        )

    with open(ledger_path, "r") as fh:
        raw: Dict[str, Any] = yaml.safe_load(fh)

    # Build tool dict keyed by tool_id.
    tools: Dict[str, ToolEntry] = {}
    for tool_raw in raw.get("tools", []):
        entry = ToolEntry(**tool_raw)
        tools[entry.tool_id] = entry

    ledger = TrustLedger(
        schema_version=raw["schema_version"],
        last_reviewed=raw.get("last_reviewed"),
        reviewed_by=raw.get("reviewed_by"),
        execution_identity=ExecutionIdentity(**raw["execution_identity"]),
        tools=tools,
    )

    logger.info(
        "Trust ledger loaded: %d tools registered, schema_version=%s, "
        "reviewed_by=%s",
        len(ledger.tools),
        ledger.schema_version,
        ledger.reviewed_by,
    )
    return ledger


def get_tool(ledger: TrustLedger, tool_name: str) -> Optional[ToolEntry]:
    """
    Return the ToolEntry for a given tool_name, or None if not registered.

    Implicit DENY: callers must treat None as a hard rejection.
    Searches by tool_name (not tool_id) since invocations reference name.
    """
    for entry in ledger.tools.values():
        if entry.tool_name == tool_name:
            return entry
    return None
