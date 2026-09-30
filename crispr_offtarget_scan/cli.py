"""
Command-line interface for the legacy rule-based CRISPR scan coordinator.
"""
import argparse
import csv
import os
import sys

from .agents import CRISPRScanCoordinator
from .models import FrontierPayload

coordinator = CRISPRScanCoordinator()

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
        prog="crispr-offtarget-scan",
        description="Legacy rule-based CRISPR scan coordinator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="TARGET-GEN-01")
    p_audit.add_argument("--primary", type=float, default=29.4)
    p_audit.add_argument("--secondary", type=float, default=15.1)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True, type=_validate_safe_path)
    p_batch.add_argument("-o", "--output", default="results.csv", type=_validate_safe_path)

    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = FrontierPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = coordinator.process(payload)
        print("=" * 80)
        print("  CRISPR SCAN COORDINATOR")
        print(f"  Task: {dossier['task_id']} | Status: [{dossier['overall_status']}] | Total Alerts: {dossier['total_alerts']}")
        print("=" * 80)
        for alert in dossier["alerts"]:
            print(f"\n  [{alert['status']}] from {alert['origin_agent']}:")
            print(f"  Summary: {alert['summary']}")
            print(f"  Details: {alert['technical_details']}")
            print(f"  Action:  {alert['actionable_remediation']}")
        print("\n" + "=" * 80)
        return 0

    if args.command == "chat":
        answer = coordinator.query_supervisory_chat(" ".join(args.query))
        print(f"\n[CRISPRScanCoordinator]:\n{answer}\n")
        return 0

    if args.command == "batch":
        with open(args.input, mode="r", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        out_fields = fieldnames + ["overall_status", "total_alerts", "critical_count", "consensus_summary"]
        out_rows = []
        for row in rows:
            payload = FrontierPayload(
                task_id=row.get("task_id", "TASK-01"),
                target_identifier=row.get("target_identifier", "TARGET-01"),
                primary_metric=float(row.get("primary_metric", 15.0)),
                secondary_metric=float(row.get("secondary_metric", 5.0)),
                status_descriptor=row.get("status_descriptor", "NOMINAL"),
                is_critical_flag=_parse_bool(row.get("is_critical_flag", False)),
            )
            dossier = coordinator.process(payload)
            row_dict = dict(row)
            row_dict["overall_status"] = dossier["overall_status"]
            row_dict["total_alerts"] = dossier["total_alerts"]
            row_dict["critical_count"] = dossier["critical_count"]
            row_dict["consensus_summary"] = dossier["consensus_summary"]
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
            from .server import create_app
        except ImportError:
            print("API dependencies are not installed. Run: pip install -e '.[api]'")
            return 1

        app = create_app()
        if app is None:
            print("FastAPI is unavailable. Run: pip install -e '.[api]'")
            return 1
        print(f"Starting CRISPR scan coordinator on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
