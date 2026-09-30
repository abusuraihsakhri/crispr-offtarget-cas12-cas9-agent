"""High-throughput simulator for the deterministic audit subsystem."""

import random
import sys
import time

from agents.base import AuditLogger, PHIGuard, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor


def run_simulation(iterations: int = 100):
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")

    print(f"Starting audit-subsystem simulation ({iterations} tasks)...")
    supervisor = SystemSupervisor(model_provider="mock")
    started = time.time()
    routine_count = 0
    elevated_count = 0
    critical_count = 0
    phi_test_count = 0
    phi_blocked_count = 0

    for index in range(iterations):
        payload = SystemTaskPayload(
            task_id=f"SIM-{index + 1:04d}",
            target_identifier=f"SPECIMEN-{random.randint(100, 999)}",
            primary_metric=round(random.uniform(5.0, 40.0), 2),
            secondary_metric=round(random.uniform(1.0, 20.0), 2),
            status_descriptor=random.choice(
                ["NOMINAL", "DISCORDANT_ANOMALY", "MUTANT_VARIANT", "OPTIMAL"]
            ),
            is_critical_flag=random.random() < 0.15,
        )

        dossier = supervisor.process_task(payload)
        if dossier.overall_urgency.value == "CRITICAL_STAT_PANIC":
            critical_count += 1
        elif dossier.overall_urgency.value == "ELEVATED_RISK":
            elevated_count += 1
        else:
            routine_count += 1

        if (index + 1) % 25 == 0:
            phi_test_count += 1
            try:
                PHIGuard.assert_no_phi(
                    f"Patient John Doe MRN-{random.randint(100000, 999999)} test"
                )
            except SecurityException:
                phi_blocked_count += 1

    elapsed = time.time() - started
    intercept_rate = (
        f"{phi_blocked_count / phi_test_count * 100:.1f}%"
        if phi_test_count
        else "not exercised"
    )

    print("\n" + "=" * 70)
    print("  SIMULATION SUMMARY")
    print("=" * 70)
    print(f"  Total Tasks Processed:      {iterations}")
    print(
        f"  Elapsed Time:               {elapsed:.3f} seconds "
        f"({iterations / max(0.001, elapsed):.1f} tasks/sec)"
    )
    print(f"  Routine Outcomes:           {routine_count} ({routine_count / iterations * 100:.1f}%)")
    print(f"  Elevated Outcomes:          {elevated_count} ({elevated_count / iterations * 100:.1f}%)")
    print(f"  Critical-flag Outcomes:     {critical_count} ({critical_count / iterations * 100:.1f}%)")
    print(f"  Identifier Guard Tests:     {phi_blocked_count}/{phi_test_count} ({intercept_rate})")
    print(f"  HMAC Audit Ledger Blocks:   {len(AuditLogger.get_trail())}")
    print(f"  HMAC Integrity Check:       {AuditLogger.verify_integrity()}")
    print("=" * 70)


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run_simulation(count)
