"""Conservative health checks for PCPulse snapshots."""
import math
from dataclasses import dataclass, fields

from .models import HealthCheck, Snapshot, Status


@dataclass(frozen=True)
class Thresholds:
    mem_warn: float = 85.0
    mem_error: float = 95.0
    disk_warn: float = 85.0
    disk_error: float = 95.0
    cpu_warn: float = 90.0
    swap_warn: float = 50.0
    swap_error: float = 90.0
    temp_warn: float = 85.0
    temp_error: float = 95.0


_PHRASE: dict[Status, str] = {
    "ok": "within the normal threshold",
    "warning": "high",
    "error": "critically high",
    "unknown": "unavailable",
}


def _validate_thresholds(t: Thresholds) -> None:
    for item in fields(t):
        value = getattr(t, item.name)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f"{item.name} must be a finite percentage between 0 and 100")
    for warn, error in (
        ("mem_warn", "mem_error"),
        ("disk_warn", "disk_error"),
        ("swap_warn", "swap_error"),
        ("temp_warn", "temp_error"),
    ):
        if getattr(t, warn) > getattr(t, error):
            raise ValueError(f"{warn} must not exceed {error}")


def _level(value: float, warn: float, error: float) -> Status:
    if value >= error:
        return "error"
    if value >= warn:
        return "warning"
    return "ok"


def _usage(
    check_id: str, label: str, value: float, warn: float, error: float, where: str = ""
) -> HealthCheck:
    status = _level(value, warn, error)
    message = f"{label} usage is {_PHRASE[status]}{where}."
    return HealthCheck(check_id, status, message, {"used_percent": value})


def run_checks(snapshot: Snapshot, thresholds: Thresholds | None = None) -> list[HealthCheck]:
    t = thresholds or Thresholds()
    _validate_thresholds(t)
    checks: list[HealthCheck] = []

    mem = snapshot.memory.used_percent
    if mem is None:
        checks.append(HealthCheck("memory.usage", "unknown", "Memory usage is unavailable."))
    else:
        checks.append(_usage("memory.usage", "Memory", mem, t.mem_warn, t.mem_error))

    load = snapshot.cpu.load_percent
    if load is None:
        checks.append(HealthCheck("cpu.load", "unknown", "CPU load is unavailable."))
    elif load >= t.cpu_warn:
        checks.append(HealthCheck("cpu.load", "warning", "CPU load is high.", {"load_percent": load}))
    else:
        checks.append(HealthCheck("cpu.load", "ok", "CPU load is within the normal threshold.", {"load_percent": load}))

    swap = snapshot.swap
    if swap is not None and swap.used_percent is not None:
        checks.append(_usage("swap.usage", "Swap", swap.used_percent, t.swap_warn, t.swap_error))

    for disk in snapshot.disks:
        if disk.used_percent is None:
            checks.append(HealthCheck(f"disk.usage:{disk.path}", "unknown", f"Disk usage unavailable for {disk.path}.", {"used_percent": None}))
        else:
            checks.append(_usage(f"disk.usage:{disk.path}", "Disk", disk.used_percent, t.disk_warn, t.disk_error, f" on {disk.path}"))

    if snapshot.temperatures:
        # Use hardware-provided critical/high limits when sensible; otherwise fall back
        # to conservative defaults. Thresholds are sensor-specific, not universal.
        for sensor in snapshot.temperatures:
            warn = sensor.high_celsius if sensor.high_celsius is not None and 0 < sensor.high_celsius <= 150 else t.temp_warn
            error = sensor.critical_celsius if sensor.critical_celsius is not None and warn <= sensor.critical_celsius <= 200 else t.temp_error
            if error < warn:
                error = t.temp_error
            status = _level(sensor.value, warn, error)
            checks.append(HealthCheck(
                f"temperature:{sensor.label}", status,
                f"Temperature is {_PHRASE[status]} ({sensor.label}: {sensor.value:.1f} C).",
                {"label": sensor.label, "celsius": sensor.value, "warn_celsius": warn, "error_celsius": error},
            ))

    for gpu in snapshot.gpus:
        if gpu.utilization_percent is not None:
            status = "warning" if gpu.utilization_percent >= 95 else "ok"
            checks.append(HealthCheck(f"gpu.utilization:{gpu.name}", status, f"GPU utilization is {'high' if status == 'warning' else 'within the normal threshold'} ({gpu.name}: {gpu.utilization_percent:.1f}%).", {"utilization_percent": gpu.utilization_percent}))

    for disk in snapshot.storage_health:
        status: Status = "error" if disk.health_status == "failed" else "warning" if disk.percentage_used is not None and disk.percentage_used >= 90 else "ok" if disk.health_status == "passed" else "unknown"
        checks.append(HealthCheck(f"storage.health:{disk.device}", status, f"Storage health for {disk.device}: {disk.health_status}.", {"health_status": disk.health_status, "percentage_used": disk.percentage_used}))

    bat = snapshot.battery
    if bat is not None and bat.percent is not None:
        details = {"percent": bat.percent, "plugged_in": bat.plugged_in}
        if bat.plugged_in is False and bat.percent <= 10:
            checks.append(HealthCheck("battery.level", "error", "Battery is critically low.", details))
        elif bat.plugged_in is False and bat.percent <= 20:
            checks.append(HealthCheck("battery.level", "warning", "Battery is low.", details))
        else:
            checks.append(HealthCheck("battery.level", "ok", "Battery level is within the normal range.", details))
    if bat is not None and bat.health_percent is not None:
        status = "error" if bat.health_percent < 50 else "warning" if bat.health_percent < 80 else "ok"
        checks.append(HealthCheck("battery.health", status, f"Battery health is {bat.health_percent:.1f}% of design capacity.", {"health_percent": bat.health_percent}))
    for error in snapshot.collection_errors:
        checks.append(HealthCheck(f"collection:{error.component}", "unknown", f"Could not collect {error.component}: {error.message}", {"error_type": error.error_type}))
    return checks
