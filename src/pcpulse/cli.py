import argparse
import os
import sys
import time
import zipfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from . import __version__, collect_snapshot, run_checks
from .collectors import SCHEMA_VERSION
from .health import Thresholds
from .models import HealthCheck
from .serialization import checks_to_json, checks_to_text, to_json, to_markdown, to_text

_THRESHOLD_FLAGS = {
    "warn_mem": "mem_warn", "error_mem": "mem_error",
    "warn_disk": "disk_warn", "error_disk": "disk_error",
    "warn_cpu": "cpu_warn", "warn_swap": "swap_warn", "error_swap": "swap_error",
}
_PAIRS = [("mem_warn", "mem_error", "memory"), ("disk_warn", "disk_error", "disk"), ("swap_warn", "swap_error", "swap")]


def _percent(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 0 <= number <= 100:
        raise argparse.ArgumentTypeError("must be between 0 and 100")
    return number


def _seconds(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 1 <= number <= 86400:
        raise argparse.ArgumentTypeError("must be between 1 and 86400 seconds")
    return number


def _interval(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 0 <= number <= 30:
        raise argparse.ArgumentTypeError("must be between 0 and 30 seconds")
    return number


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a whole number") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--output", metavar="FILE", help="Write the report to FILE.")
    parser.add_argument("--watch", type=_seconds, metavar="SECONDS", help="Refresh the report every SECONDS until Ctrl+C.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pcpulse", description="Privacy-first cross-platform PC diagnostics.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot", help="Collect a local system snapshot.")
    fmt = snapshot.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true")
    fmt.add_argument("--markdown", action="store_true")
    snapshot.add_argument("--include-identity", action="store_true")
    snapshot.add_argument("--include-processes", action="store_true", help="Include top processes by memory (process names can be private).")
    snapshot.add_argument("--include-storage-health", action="store_true", help="Probe SMART health when smartctl is installed; may require elevated privileges.")
    snapshot.add_argument("--sample-interval", type=_interval, default=0.5, metavar="SECONDS", help="Sampling window for network and disk throughput (0 disables rate sampling; default: 0.5).")
    snapshot.add_argument("--top", type=_positive_int, default=5, metavar="N")
    _add_common(snapshot)

    doctor = sub.add_parser("doctor", help="Run conservative local health checks.")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--fail-on", choices=["warning", "error", "never"], default="error")
    for flag in _THRESHOLD_FLAGS:
        doctor.add_argument("--" + flag.replace("_", "-"), dest=flag, type=_percent, metavar="PERCENT")
    _add_common(doctor)

    schema = sub.add_parser("schema", help="Show the snapshot schema version or write the schema JSON.")
    schema.add_argument("-o", "--output", metavar="FILE", help="Write the bundled JSON Schema to FILE.")
    report = sub.add_parser("report", help="Create a ZIP diagnostic report bundle.")
    report.add_argument("-o", "--output", metavar="FILE", required=True, help="Destination ZIP file.")
    report.add_argument("--include-identity", action="store_true")
    report.add_argument("--include-processes", action="store_true")
    report.add_argument("--include-storage-health", action="store_true")
    report.add_argument("--sample-interval", type=_interval, default=0.5, metavar="SECONDS")
    return parser


def _thresholds(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Thresholds:
    overrides = {field: getattr(args, flag) for flag, field in _THRESHOLD_FLAGS.items() if getattr(args, flag) is not None}
    thresholds = replace(Thresholds(), **overrides)
    for warn, error, label in _PAIRS:
        if getattr(thresholds, warn) > getattr(thresholds, error):
            parser.error(f"{label}: the warning level is higher than the error level")
    return thresholds


def _exit_code(checks: list[HealthCheck], fail_on: str) -> int:
    if fail_on == "never":
        return 0
    bad = {"error"} if fail_on == "error" else {"warning", "error"}
    return 1 if any(c.status in bad for c in checks) else 0


def _watch(render: Callable[[], tuple[str, int]], interval: float) -> int:
    if os.name == "nt":
        os.system("")
    code = 0
    try:
        while True:
            text, code = render()
            clear = "\033[2J\033[H" if sys.stdout.isatty() else ""
            sys.stdout.write(clear + text)
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        return code


def _schema_text() -> str:
    return (Path(__file__).parent / "schemas" / f"snapshot-{SCHEMA_VERSION}.schema.json").read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "schema":
        if args.output:
            Path(args.output).write_text(_schema_text(), encoding="utf-8")
        else:
            print(SCHEMA_VERSION)
        return 0

    if args.command == "report":
        snapshot = collect_snapshot(
            include_identity=args.include_identity,
            include_processes=args.include_processes,
            include_storage_health=args.include_storage_health,
            sample_interval_seconds=args.sample_interval,
        )
        checks = run_checks(snapshot)
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("snapshot.json", to_json(snapshot) + "\n")
            archive.writestr("snapshot.md", to_markdown(snapshot))
            archive.writestr("health-checks.json", checks_to_json(checks))
            archive.writestr(f"snapshot-{SCHEMA_VERSION}.schema.json", _schema_text())
        return 0

    if args.watch is not None and args.output:
        parser.error("--watch cannot be combined with --output")

    if args.command == "snapshot":
        def render() -> tuple[str, int]:
            snap = collect_snapshot(
                include_identity=args.include_identity,
                include_processes=args.include_processes,
                process_limit=args.top,
                include_storage_health=args.include_storage_health,
                sample_interval_seconds=args.sample_interval,
            )
            if args.json:
                return to_json(snap) + "\n", 0
            return (to_markdown(snap) if args.markdown else to_text(snap)), 0
    else:
        thresholds = _thresholds(args, parser)
        def render() -> tuple[str, int]:
            checks = run_checks(collect_snapshot(), thresholds)
            output = checks_to_json(checks) if args.json else checks_to_text(checks)
            return output, _exit_code(checks, args.fail_on)

    if args.watch is not None:
        return _watch(render, args.watch)
    output, code = render()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
