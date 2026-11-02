"""Stable JSON, text, Markdown, and report serialization."""
import json
import math
from dataclasses import asdict
from typing import Any

from .models import HealthCheck, Snapshot


def to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return snapshot.to_dict()


def _clean(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def to_json(snapshot: Snapshot) -> str:
    return json.dumps(_clean(to_dict(snapshot)), indent=2, allow_nan=False)


def checks_to_json(checks: list[HealthCheck]) -> str:
    return json.dumps(_clean([asdict(c) for c in checks]), indent=2, allow_nan=False) + "\n"


def checks_to_text(checks: list[HealthCheck]) -> str:
    return "".join(f"[{c.status.upper()}] {c.message}\n" for c in checks)


def format_uptime(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
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
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _pct(value: float | None) -> str:
    return f"{value}%" if value is not None else "unavailable"


def _battery(snapshot: Snapshot) -> str | None:
    bat = snapshot.battery
    if bat is None:
        return None
    state = {True: "plugged in", False: "on battery", None: "power state unknown"}[bat.plugged_in]
    return f"{_pct(bat.percent)} ({state})"


def _md(value: object) -> str:
    """Escape untrusted/system-provided text before inserting it in Markdown tables."""
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")


def _temp(value: float | None) -> str:
    return f"{value:.1f} C" if value is not None and math.isfinite(value) else "unavailable"


def _rate(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "unavailable"
    return f"{value * 8 / 1_000_000:.2f} Mbps"


def to_text(snapshot: Snapshot) -> str:
    cpu = snapshot.cpu
    lines = [
        f"OS: {snapshot.os}",
        f"Kernel: {snapshot.kernel}",
        f"Architecture: {snapshot.architecture}",
        f"CPU: {cpu.logical_cores} logical / {cpu.physical_cores} physical",
        f"CPU load: {_pct(cpu.load_percent)}",
        f"Memory: {_pct(snapshot.memory.used_percent)} used",
        f"Uptime: {format_uptime(snapshot.uptime_seconds)}",
    ]
    if snapshot.hardware and snapshot.hardware.cpu_model:
        lines.append(f"CPU model: {snapshot.hardware.cpu_model}")
    for disk in snapshot.disks:
        lines.append(f"Disk {disk.path}: {_pct(disk.used_percent)} used; free {format_bytes(disk.free_bytes)} / {format_bytes(disk.total_bytes)}")
    if snapshot.disk_io:
        lines.append(f"Disk I/O: read {_rate(snapshot.disk_io.read_rate_bytes_per_sec)}, write {_rate(snapshot.disk_io.write_rate_bytes_per_sec)}")
    for gpu in snapshot.gpus:
        lines.append(f"GPU: {gpu.name}; load {_pct(gpu.utilization_percent)}; VRAM {format_bytes(gpu.memory_used_bytes)} / {format_bytes(gpu.memory_total_bytes)}")
    for device in snapshot.storage_health:
        lines.append(f"Storage health {device.device}: {device.health_status}; temperature {_pct(device.temperature_celsius)}; wear {_pct(device.percentage_used)}")
    if snapshot.swap is not None and snapshot.swap.used_percent is not None:
        lines.append(f"Swap: {snapshot.swap.used_percent}% used")
    battery = _battery(snapshot)
    if battery:
        lines.append(f"Battery: {battery}")
    if snapshot.battery and snapshot.battery.health_percent is not None:
        lines.append(f"Battery health: {snapshot.battery.health_percent:.1f}%")
    for net in snapshot.network:
        lines.append(f"Network {net.name}: down {_rate(net.recv_rate_bytes_per_sec)}, up {_rate(net.send_rate_bytes_per_sec)}")
    if snapshot.processes is not None:
        lines.append("Top processes by memory:")
        lines += [f"  {p.pid} {p.name}: {format_bytes(p.rss_bytes)}" for p in snapshot.processes]
    if snapshot.collection_errors:
        lines.append(f"Collection warnings: {len(snapshot.collection_errors)} (see JSON for details)")
    return "\n".join(lines) + "\n"


def to_markdown(snapshot: Snapshot) -> str:
    rows: list[tuple[str, object]] = [
        ("OS", snapshot.os), ("Kernel", snapshot.kernel), ("Architecture", snapshot.architecture),
        ("CPU logical", snapshot.cpu.logical_cores), ("CPU physical", snapshot.cpu.physical_cores),
        ("CPU load", snapshot.cpu.load_percent), ("Memory used", snapshot.memory.used_percent),
        ("Uptime", format_uptime(snapshot.uptime_seconds)),
    ]
    if snapshot.hardware:
        for label, value in (("CPU model", snapshot.hardware.cpu_model), ("System model", snapshot.hardware.system_model), ("Motherboard", snapshot.hardware.motherboard_model)):
            if value:
                rows.append((label, value))
    if snapshot.swap is not None:
        rows.append(("Swap used", snapshot.swap.used_percent))
    battery = _battery(snapshot)
    if battery:
        rows.append(("Battery", battery))
    if snapshot.battery and snapshot.battery.health_percent is not None:
        rows.append(("Battery health", f"{snapshot.battery.health_percent:.1f}%"))
    out = ["# PCPulse System Snapshot", "", "| Metric | Value |", "|---|---|"]
    out += [f"| {_md(k)} | {_md(v if v is not None else 'unavailable')} |" for k, v in rows]
    out += ["", "## Disks", "", "| Mount | Used | Free | Total |", "|---|---:|---:|---:|"]
    out += [f"| {_md(d.path)} | {_md(_pct(d.used_percent))} | {_md(format_bytes(d.free_bytes))} | {_md(format_bytes(d.total_bytes))} |" for d in snapshot.disks]
    if snapshot.disk_io:
        out += ["", "## Disk I/O", f"- Read: {_md(_rate(snapshot.disk_io.read_rate_bytes_per_sec))}", f"- Write: {_md(_rate(snapshot.disk_io.write_rate_bytes_per_sec))}"]
    if snapshot.gpus:
        out += ["", "## GPUs"]
        for gpu in snapshot.gpus:
            out.append(f"- {_md(gpu.name)} ({_md(gpu.vendor or 'unknown')}): load {_md(_pct(gpu.utilization_percent))}, VRAM {_md(format_bytes(gpu.memory_used_bytes))} / {_md(format_bytes(gpu.memory_total_bytes))}, temperature {_md(_temp(gpu.temperature_celsius))}")
    if snapshot.storage_health:
        out += ["", "## Storage health"]
        for device in snapshot.storage_health:
            out.append(f"- {_md(device.device)} ({_md(device.model or 'unknown')}): {_md(device.health_status)}, temperature {_md(_pct(device.temperature_celsius))}, wear {_md(_pct(device.percentage_used))}")
    if snapshot.network:
        out += ["", "## Network", "", "| Interface | State | Down | Up |", "|---|---|---:|---:|"]
        for n in snapshot.network:
            state = {True: "up", False: "down", None: "unknown"}[n.is_up]
            out.append(f"| {_md(n.name)} | {state} | {_md(_rate(n.recv_rate_bytes_per_sec))} | {_md(_rate(n.send_rate_bytes_per_sec))} |")
    if snapshot.temperatures or snapshot.fans:
        out += ["", "## Sensors"]
        out += [f"- {_md(r.label)}: {r.value:.1f} C" for r in snapshot.temperatures]
        out += [f"- {_md(r.label)}: {r.value:.0f} RPM" for r in snapshot.fans]
    if snapshot.processes is not None:
        out += ["", "## Top processes by memory", "", "| PID | Name | Memory |", "|---|---|---:|"]
        out += [f"| {p.pid} | {_md(p.name)} | {format_bytes(p.rss_bytes)} |" for p in snapshot.processes]
    if snapshot.collection_errors:
        out += ["", "## Collection warnings"]
        out += [f"- {_md(e.component)}: {_md(e.message)}" for e in snapshot.collection_errors]
    return "\n".join(out) + "\n"
