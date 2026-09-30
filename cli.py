"""
Command-line interface for the CRISPR off-target agent subsystem.
"""
import argparse
import csv
import os
import sys

from agents.base import AuditLogger
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off", ""}


def _validate_safe_path(filepath: str) -> str:
    """Reject parent-directory traversal using either POSIX or Windows separators."""
    raw_path = os.fspath(filepath)
    if any(part == ".." for part in raw_path.replace("\\", "/").split("/")):
        raise argparse.ArgumentTypeError(
            f"Path traversal detected in '{filepath}'. Paths must not contain '..' segments."
        )
    return os.path.normpath(raw_path)


def _parse_bool(value) -> bool:
    """Parse common CSV boolean representations without treating every non-empty string as true."""
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="crispr-agent",
        description="Rule-based CRISPR off-target audit subsystem",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_audit = subparsers.add_parser("audit", help="Run a single rule-based task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    p_chat = subparsers.add_parser("chat", help="Query the deterministic supervisor")
    p_chat.add_argument("query", nargs="+")

    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True, type=_validate_safe_path)
    p_batch.add_argument("-o", "--output", default="results.csv", type=_validate_safe_path)

    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print("  CRISPR OFF-TARGET AGENT")
        print("  Rule-based audit subsystem; research-use only")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for alert in dossier.alerts:
            print(f"\n  [{alert.urgency.value}] from {alert.origin_worker}:")
            print(f"  Summary: {alert.summary}")
            print(f"  Details: {alert.technical_details}")
            print(f"  Action:  {alert.actionable_remediation}")
        print(f"\n  HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        answer = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[CRISPR Agent Supervisor]:\n{answer}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0 if valid else 1

    if args.command == "batch":
        with open(args.input, mode="r", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        out_fields = fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]
        out_rows = []
        for row in rows:
            task_id = row.get("task_id", "TASK-01")
            payload = SystemTaskPayload(
                task_id=task_id,
                target_identifier=row.get("target_identifier", "TARGET-01"),
                primary_metric=float(row.get("primary_metric", 15.0)),
                secondary_metric=float(row.get("secondary_metric", 5.0)),
                status_descriptor=row.get("status_descriptor", "NOMINAL"),
                is_critical_flag=_parse_bool(row.get("is_critical_flag", False)),
            )
            dossier = supervisor.process_task(payload)
            row_dict = dict(row)
            row_dict["overall_urgency"] = dossier.overall_urgency.value
            row_dict["integrity_status"] = dossier.integrity_status.value
            row_dict["total_alerts"] = dossier.total_alerts
            row_dict["audit_hash"] = dossier.audit_hash
            out_rows.append(row_dict)

        with open(args.output, mode="w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"Processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
            from agents.api import app
        except ImportError:
            print("API dependencies are not installed. Run: pip install -e '.[api]'")
            return 1

        print(f"Starting CRISPR Off-Target Agent API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
