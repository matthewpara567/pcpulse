import argparse
import json

from . import __version__, collect_snapshot, run_checks
from .serialization import to_json, to_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pcpulse",
        description="Privacy-first cross-platform PC diagnostics.",
    )
    parser.add_argument("--version", action="version", version=__version__)

    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot", help="Collect a local system snapshot.")
    snapshot.add_argument("--json", action="store_true")
    snapshot.add_argument("--markdown", action="store_true")
    snapshot.add_argument("--include-identity", action="store_true")

    doctor = sub.add_parser("doctor", help="Run conservative local health checks.")
    doctor.add_argument("--json", action="store_true")

    sub.add_parser("schema", help="Show the current snapshot schema version.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "schema":
        print("1.0")
        return 0

    if args.command == "snapshot":
        snapshot = collect_snapshot(include_identity=args.include_identity)
        if args.json:
            print(to_json(snapshot))
        elif args.markdown:
            print(to_markdown(snapshot), end="")
        else:
            print(f"OS: {snapshot.os}")
            print(f"Kernel: {snapshot.kernel}")
            print(f"Architecture: {snapshot.architecture}")
            print(
                f"CPU: {snapshot.cpu.logical_cores} logical / "
                f"{snapshot.cpu.physical_cores} physical"
            )
            print(f"CPU load: {snapshot.cpu.load_percent}%")
            print(f"Memory: {snapshot.memory.used_percent}% used")
        return 0

    if args.command == "doctor":
        checks = run_checks(collect_snapshot())
        if args.json:
            print(json.dumps([check.__dict__ for check in checks], indent=2))
        else:
            for check in checks:
                print(f"[{check.status.upper()}] {check.message}")
        return 0 if not any(check.status == "error" for check in checks) else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
