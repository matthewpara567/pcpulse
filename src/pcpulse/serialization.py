import json
from typing import Any

from .models import Snapshot


def to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return snapshot.to_dict()


def to_json(snapshot: Snapshot) -> str:
    return json.dumps(to_dict(snapshot), indent=2)


def to_markdown(snapshot: Snapshot) -> str:
    rows = [
        ("OS", snapshot.os),
        ("Kernel", snapshot.kernel),
        ("Architecture", snapshot.architecture),
        ("CPU logical", snapshot.cpu.logical_cores),
        ("CPU physical", snapshot.cpu.physical_cores),
        ("CPU load", snapshot.cpu.load_percent),
        ("Memory used", snapshot.memory.used_percent),
        ("Uptime seconds", snapshot.uptime_seconds),
    ]
    out = ["# PCPulse System Snapshot", "", "| Metric | Value |", "|---|---|"]
    out += [f"| {k} | {v if v is not None else 'unavailable'} |" for k, v in rows]
    out += ["", "## Disks"]
    out += [
        f"- {d.path}: {d.used_percent if d.used_percent is not None else 'unavailable'}% used"
        for d in snapshot.disks
    ]
    return "\n".join(out) + "\n"
