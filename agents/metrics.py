"""Minimal thread-safe Prometheus metrics for the audit subsystem."""

from threading import Lock


class SystemMetricsCollector:
    def __init__(self):
        self.system_name = "crispr-offtarget-cas12-cas9-agent"
        self.tasks_total = 0
        self.critical_alerts_total = 0
        self.elevated_alerts_total = 0
        self.routine_tasks_total = 0
        self.phi_blocks_total = 0
        self.audit_blocks_total = 0
        self.processing_latency_sum = 0.0
        self._lock = Lock()

    def record_task(self, urgency: str, duration_sec: float):
        with self._lock:
            self.tasks_total += 1
            self.processing_latency_sum += duration_sec
            self.audit_blocks_total += 1
            urgency_upper = str(urgency).upper()
            if "CRITICAL" in urgency_upper:
                self.critical_alerts_total += 1
            elif "ELEVATED" in urgency_upper:
                self.elevated_alerts_total += 1
            else:
                self.routine_tasks_total += 1

    def record_phi_block(self):
        with self._lock:
            self.phi_blocks_total += 1

    def export_prometheus_text(self) -> str:
        with self._lock:
            tasks_total = self.tasks_total
            critical_total = self.critical_alerts_total
            elevated_total = self.elevated_alerts_total
            routine_total = self.routine_tasks_total
            phi_blocks_total = self.phi_blocks_total
            audit_blocks_total = self.audit_blocks_total
            latency_sum = self.processing_latency_sum

        average_latency = latency_sum / max(1, tasks_total)
        system_label = self.system_name
        lines = [
            "# HELP system_tasks_total Total audit-subsystem tasks processed",
            "# TYPE system_tasks_total counter",
            f'system_tasks_total{{system="{system_label}"}} {tasks_total}',
            "",
            "# HELP alerts_triggered_total Total outcomes by urgency tier",
            "# TYPE alerts_triggered_total counter",
            f'alerts_triggered_total{{system="{system_label}",urgency="CRITICAL_STAT"}} {critical_total}',
            f'alerts_triggered_total{{system="{system_label}",urgency="ELEVATED_RISK"}} {elevated_total}',
            f'alerts_triggered_total{{system="{system_label}",urgency="ROUTINE"}} {routine_total}',
            "",
            "# HELP phi_outbound_blocks_total Total sensitive-identifier guard blocks",
            "# TYPE phi_outbound_blocks_total counter",
            f'phi_outbound_blocks_total{{system="{system_label}"}} {phi_blocks_total}',
            "",
            "# HELP audit_chain_blocks_total Total HMAC-SHA256 audit entries signed",
            "# TYPE audit_chain_blocks_total counter",
            f'audit_chain_blocks_total{{system="{system_label}"}} {audit_blocks_total}',
            "",
            "# HELP task_processing_duration_avg_seconds Average task evaluation latency",
            "# TYPE task_processing_duration_avg_seconds gauge",
            f'task_processing_duration_avg_seconds{{system="{system_label}"}} {average_latency:.4f}',
            "",
        ]
        return "\n".join(lines)


GLOBAL_METRICS = SystemMetricsCollector()
