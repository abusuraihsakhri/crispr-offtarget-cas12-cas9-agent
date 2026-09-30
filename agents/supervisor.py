"""Coordinator for the rule-based audit subsystem."""

import time
import uuid
from typing import Dict, List

from .base import AuditLogger, PHIGuard, SecurityException
from .llm_factory import LLMFactory
from .metrics import GLOBAL_METRICS
from .models import (
    AgentAlert,
    ConsensusDossier,
    SystemIntegrityStatus,
    SystemTaskPayload,
    UrgencyLevel,
)
from .workers import InvariantQCWorker, ProtocolConformanceWorker, SafetyEscalationWorker


class SystemSupervisor:
    """Coordinate deterministic threshold workers and audit each completed task."""

    def __init__(self, model_provider: str = "mock"):
        self.qc_worker = InvariantQCWorker()
        self.safety_worker = SafetyEscalationWorker()
        self.conformance_worker = ProtocolConformanceWorker()
        self.llm = LLMFactory.create(model_provider, system_name="CRISPR Off-Target Agent")
        self.dossier_registry: Dict[str, ConsensusDossier] = {}

    @staticmethod
    def _guard_payload(payload: SystemTaskPayload) -> None:
        try:
            PHIGuard.assert_no_phi(payload.task_id)
            PHIGuard.assert_no_phi(payload.target_identifier)
            PHIGuard.assert_no_phi(payload.status_descriptor)
            PHIGuard.assert_no_phi(str(payload.attributes))
        except SecurityException:
            GLOBAL_METRICS.record_phi_block()
            raise

    def process_task(
        self,
        payload: SystemTaskPayload,
        actor: str = "SystemSupervisor",
    ) -> ConsensusDossier:
        started = time.perf_counter()
        self._guard_payload(payload)

        alerts: List[AgentAlert] = []
        alerts.extend(self.qc_worker.evaluate(payload))
        alerts.extend(self.safety_worker.evaluate(payload))
        alerts.extend(self.conformance_worker.evaluate(payload))

        critical_count = sum(
            alert.urgency == UrgencyLevel.CRITICAL_STAT for alert in alerts
        )
        elevated_count = sum(alert.urgency == UrgencyLevel.ELEVATED for alert in alerts)

        if critical_count:
            overall_urgency = UrgencyLevel.CRITICAL_STAT
            integrity_status = SystemIntegrityStatus.RECALIBRATION_REQUIRED
        elif elevated_count:
            overall_urgency = UrgencyLevel.ELEVATED
            integrity_status = SystemIntegrityStatus.DISCORDANT
        else:
            overall_urgency = UrgencyLevel.ROUTINE
            integrity_status = SystemIntegrityStatus.VALIDATED

        audit_entry = AuditLogger.log(
            actor=actor,
            actor_tier="supervisor",
            event_type="TASK_EVALUATION_COMPLETED",
            details={
                "task_id": payload.task_id,
                "target_identifier": payload.target_identifier,
                "overall_urgency": overall_urgency.value,
                "total_alerts": len(alerts),
            },
        )

        dossier = ConsensusDossier(
            dossier_id=f"DOSSIER-{uuid.uuid4().hex[:8].upper()}",
            task_id=payload.task_id,
            target_identifier=payload.target_identifier,
            overall_urgency=overall_urgency,
            integrity_status=integrity_status,
            total_alerts=len(alerts),
            critical_alerts_count=critical_count,
            alerts=alerts,
            consensus_summary=(
                f"Deterministic three-worker evaluation completed with status "
                f"[{overall_urgency.value}]. Total alerts: {len(alerts)}."
            ),
            audit_hash=audit_entry["current_hash"],
        )

        self.dossier_registry[dossier.dossier_id] = dossier
        GLOBAL_METRICS.record_task(
            overall_urgency.value,
            time.perf_counter() - started,
        )
        return dossier

    def query_supervisory_chat(self, query: str) -> str:
        try:
            PHIGuard.assert_no_phi(query)
        except SecurityException:
            GLOBAL_METRICS.record_phi_block()
            raise
        return self.llm.invoke(query)
