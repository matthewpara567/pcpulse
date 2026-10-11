from dataclasses import dataclass

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
        checks.append(
            HealthCheck("cpu.load", "warning", "CPU load is high.", {"load_percent": load})
        )
    else:
        checks.append(
            HealthCheck(
                "cpu.load", "ok", "CPU load is within the normal threshold.", {"load_percent": load}
            )
        )

    swap = snapshot.swap
    if swap is not None and swap.used_percent is not None:
        checks.append(_usage("swap.usage", "Swap", swap.used_percent, t.swap_warn, t.swap_error))

    for d in snapshot.disks:
        if d.used_percent is None:
            msg = f"Disk usage unavailable for {d.path}."
            checks.append(
                HealthCheck(f"disk.usage:{d.path}", "unknown", msg, {"used_percent": None})
            )
        else:
            checks.append(
                _usage(
                    f"disk.usage:{d.path}",
                    "Disk",
                    d.used_percent,
                    t.disk_warn,
                    t.disk_error,
                    f" on {d.path}",
                )
            )

    if snapshot.temperatures:
        hottest = max(snapshot.temperatures, key=lambda r: r.value)
        status = _level(hottest.value, t.temp_warn, t.temp_error)
        checks.append(
            HealthCheck(
                "temperature.max",
                status,
                f"Temperature is {_PHRASE[status]} ({hottest.label}: {hottest.value:.1f} C).",
                {"label": hottest.label, "celsius": hottest.value},
            )
        )

    bat = snapshot.battery
    if bat is not None and bat.percent is not None:
        details = {"percent": bat.percent, "plugged_in": bat.plugged_in}
        if bat.plugged_in is False and bat.percent <= 10:
            checks.append(
                HealthCheck("battery.level", "error", "Battery is critically low.", details)
            )
        elif bat.plugged_in is False and bat.percent <= 20:
            checks.append(HealthCheck("battery.level", "warning", "Battery is low.", details))
        else:
            checks.append(
                HealthCheck(
                    "battery.level", "ok", "Battery level is within the normal range.", details
                )
            )
    return checks
