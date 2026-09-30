"""Pydantic schemas for the rule-based audit subsystem."""

import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class UrgencyLevel(str, Enum):
    ROUTINE = "ROUTINE"
    ELEVATED = "ELEVATED_RISK"
    CRITICAL_STAT = "CRITICAL_STAT_PANIC"


class SystemIntegrityStatus(str, Enum):
    VALIDATED = "VALIDATED_OPTIMAL"
    DISCORDANT = "DISCORDANT_ANOMALY"
    RECALIBRATION_REQUIRED = "RECALIBRATION_REQUIRED"


class SystemTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task_id: str = Field(..., min_length=1, max_length=128)
    target_identifier: str = Field(..., min_length=1, max_length=256)
    primary_metric: float = Field(..., allow_inf_nan=False)
    secondary_metric: float = Field(default=0.0, allow_inf_nan=False)
    status_descriptor: str = Field(default="NOMINAL", min_length=1, max_length=128)
    is_critical_flag: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class AgentAlert(BaseModel):
    alert_id: str
    origin_worker: str
    urgency: UrgencyLevel
    summary: str
    technical_details: str
    actionable_remediation: str
    standard_reference: str = "Internal rule-set thresholds"
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ConsensusDossier(BaseModel):
    dossier_id: str
    system_slug: str = "crispr-offtarget-cas12-cas9-agent"
    domain: str = "Research-use CRISPR audit utilities"
    task_id: str
    target_identifier: str
    overall_urgency: UrgencyLevel
    integrity_status: SystemIntegrityStatus
    total_alerts: int
    critical_alerts_count: int
    alerts: List[AgentAlert]
    standard_reference: str = "Internal rule-set thresholds"
    consensus_summary: str
    audit_hash: str
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
