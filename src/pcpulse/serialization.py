import json
from dataclasses import asdict
from typing import Any

from .models import HealthCheck, Snapshot


def to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return snapshot.to_dict()


def to_json(snapshot: Snapshot) -> str:
    return json.dumps(to_dict(snapshot), indent=2)


def checks_to_json(checks: list[HealthCheck]) -> str:
    return json.dumps([asdict(c) for c in checks], indent=2) + "\n"


def checks_to_text(checks: list[HealthCheck]) -> str:
    return "".join(f"[{c.status.upper()}] {c.message}\n" for c in checks)


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


def format_bytes(value: int | None) -> str:
    if value is None:
        return "unavailable"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _pct(value: float | None) -> str:
    return f"{value}%" if value is not None else "unavailable"


def _battery(snapshot: Snapshot) -> str | None:
    bat = snapshot.battery
    if bat is None:
        return None
    state = {True: "plugged in", False: "on battery", None: "power state unknown"}[bat.plugged_in]
    return f"{_pct(bat.percent)} ({state})"


def to_text(snapshot: Snapshot) -> str:
    cpu = snapshot.cpu
    lines = [
        f"OS: {snapshot.os}",
        f"Kernel: {snapshot.kernel}",
        f"Architecture: {snapshot.architecture}",
        f"CPU: {cpu.logical_cores} logical / {cpu.physical_cores} physical",
        f"CPU load: {cpu.load_percent}%",
        f"Memory: {snapshot.memory.used_percent}% used",
    ]
    if snapshot.swap is not None and snapshot.swap.used_percent is not None:
        lines.append(f"Swap: {snapshot.swap.used_percent}% used")
    battery = _battery(snapshot)
    if battery:
        lines.append(f"Battery: {battery}")
    if snapshot.processes is not None:
        lines.append("Top processes by memory:")
        lines += [f"  {p.pid} {p.name}: {format_bytes(p.rss_bytes)}" for p in snapshot.processes]
    return "\n".join(lines) + "\n"


def to_markdown(snapshot: Snapshot) -> str:
    rows: list[tuple[str, object]] = [
        ("OS", snapshot.os),
        ("Kernel", snapshot.kernel),
        ("Architecture", snapshot.architecture),
        ("CPU logical", snapshot.cpu.logical_cores),
        ("CPU physical", snapshot.cpu.physical_cores),
        ("CPU load", snapshot.cpu.load_percent),
        ("Memory used", snapshot.memory.used_percent),
    ]
    if snapshot.swap is not None:
        rows.append(("Swap used", snapshot.swap.used_percent))
    battery = _battery(snapshot)
    if battery:
        rows.append(("Battery", battery))
    rows.append(("Uptime", format_uptime(snapshot.uptime_seconds)))
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
    if snapshot.network:
        out += ["", "## Network"]
        for n in snapshot.network:
            state = {True: "up", False: "down", None: "unknown"}[n.is_up]
            out.append(
                f"- {n.name}: {state}, sent {format_bytes(n.bytes_sent)}, "
                f"received {format_bytes(n.bytes_recv)}"
            )
    if snapshot.temperatures or snapshot.fans:
        out += ["", "## Sensors"]
        out += [f"- {r.label}: {r.value:.1f} C" for r in snapshot.temperatures]
        out += [f"- {r.label}: {r.value:.0f} RPM" for r in snapshot.fans]
    if snapshot.processes is not None:
        out += ["", "## Top processes by memory", "", "| PID | Name | Memory |", "|---|---|---|"]
        out += [f"| {p.pid} | {p.name} | {format_bytes(p.rss_bytes)} |" for p in snapshot.processes]
    return "\n".join(out) + "\n"
