import json
from typing import Any

from .models import Snapshot


def to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return snapshot.to_dict()


def to_json(snapshot: Snapshot) -> str:
    return json.dumps(to_dict(snapshot), indent=2)


def format_uptime(seconds: float | None) -> str:
    if seconds is None:
        return "unavailable"
    minutes = int(seconds // 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    parts = [f"{days}d"] if days else []
    if days or hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def to_markdown(snapshot: Snapshot) -> str:
    rows: list[tuple[str, object]] = [
        ("OS", snapshot.os),
        ("Kernel", snapshot.kernel),
        ("Architecture", snapshot.architecture),
        ("CPU logical", snapshot.cpu.logical_cores),
        ("CPU physical", snapshot.cpu.physical_cores),
        ("CPU load", snapshot.cpu.load_percent),
        ("Memory used", snapshot.memory.used_percent),
        ("Uptime", format_uptime(snapshot.uptime_seconds)),
    ]
    if snapshot.hostname is not None:
        rows.append(("Hostname", snapshot.hostname))
    if snapshot.username is not None:
        rows.append(("Username", snapshot.username))
    out = ["# PCPulse System Snapshot", "", "| Metric | Value |", "|---|---|"]
    out += [f"| {k} | {v if v is not None else 'unavailable'} |" for k, v in rows]
    out += ["", "## Disks"]
    out += [
        f"- {d.path}: {f'{d.used_percent}% used' if d.used_percent is not None else 'unavailable'}"
        for d in snapshot.disks
    ]
    return "\n".join(out) + "\n"
