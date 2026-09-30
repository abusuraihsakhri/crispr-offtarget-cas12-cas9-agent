"""Deterministic threshold workers used by the generic audit subsystem."""

import uuid
from typing import List

from .models import AgentAlert, SystemTaskPayload, UrgencyLevel


class InvariantQCWorker:
    """Flag a primary metric above the subsystem's configured threshold."""

    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        if payload.primary_metric <= 25.0:
            return []
        return [
            AgentAlert(
                alert_id=f"QC-{uuid.uuid4().hex[:6]}",
                origin_worker="InvariantQCWorker",
                urgency=UrgencyLevel.ELEVATED,
                summary="Primary Metric Threshold Exceeded",
                technical_details=(
                    f"Primary metric ({payload.primary_metric:.2f}) exceeds "
                    "the configured threshold (25.00)."
                ),
                actionable_remediation=(
                    "Review the source measurement and the threshold configuration."
                ),
            )
        ]


class SafetyEscalationWorker:
    """Compatibility-named worker for the critical flag and secondary threshold."""

    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        if not payload.is_critical_flag and payload.secondary_metric <= 12.0:
            return []
        return [
            AgentAlert(
                alert_id=f"SAFE-{uuid.uuid4().hex[:6]}",
                origin_worker="SafetyEscalationWorker",
                urgency=(
                    UrgencyLevel.CRITICAL_STAT
                    if payload.is_critical_flag
                    else UrgencyLevel.ELEVATED
                ),
                summary="Secondary Threshold or Critical Flag Triggered",
                technical_details=(
                    f"critical_flag={payload.is_critical_flag}; "
                    f"secondary_metric={payload.secondary_metric:.2f}; "
                    "configured threshold=12.00."
                ),
                actionable_remediation=(
                    "Review the originating record and confirm whether escalation is warranted."
                ),
            )
        ]


class ProtocolConformanceWorker:
    """Flag configured status keywords that indicate a discordant record."""

    TRIGGER_WORDS = ("DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT")

    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        descriptor = str(payload.status_descriptor)
        if not any(word in descriptor.upper() for word in cls.TRIGGER_WORDS):
            return []
        return [
            AgentAlert(
                alert_id=f"CONF-{uuid.uuid4().hex[:6]}",
                origin_worker="ProtocolConformanceWorker",
                urgency=UrgencyLevel.ELEVATED,
                summary="Status Descriptor Trigger Detected",
                technical_details=(
                    f"Descriptor {descriptor!r} contains a configured discordance keyword."
                ),
                actionable_remediation=(
                    "Review the status descriptor and source record for consistency."
                ),
            )
        ]
