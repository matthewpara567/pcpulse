from .models import HealthCheck, Snapshot


def run_checks(snapshot: Snapshot) -> list[HealthCheck]:
    checks = []
    mem = snapshot.memory.used_percent
    if mem is None:
        checks.append(HealthCheck("memory.available", "unknown", "Memory usage is unavailable."))
    elif mem >= 95:
        checks.append(
            HealthCheck(
                "memory.usage", "error", "Memory usage is critically high.", {"used_percent": mem}
            )
        )
    elif mem >= 85:
        checks.append(
            HealthCheck("memory.usage", "warning", "Memory usage is high.", {"used_percent": mem})
        )
    else:
        checks.append(
            HealthCheck(
                "memory.usage",
                "ok",
                "Memory usage is within the normal threshold.",
                {"used_percent": mem},
            )
        )
    load = snapshot.cpu.load_percent
    if load is None:
        checks.append(HealthCheck("cpu.load", "unknown", "CPU load is unavailable."))
    elif load >= 90:
        checks.append(
            HealthCheck("cpu.load", "warning", "CPU load is high.", {"load_percent": load})
        )
    else:
        checks.append(
            HealthCheck(
                "cpu.load", "ok", "CPU load is within the normal threshold.", {"load_percent": load}
            )
        )
    for d in snapshot.disks:
        v = d.used_percent
        if v is None:
            status, msg = "unknown", f"Disk usage unavailable for {d.path}."
        elif v >= 95:
            status, msg = "error", f"Disk usage is critically high on {d.path}."
        elif v >= 85:
            status, msg = "warning", f"Disk usage is high on {d.path}."
        else:
            status, msg = "ok", f"Disk usage is within the normal threshold on {d.path}."
        checks.append(HealthCheck(f"disk.usage:{d.path}", status, msg, {"used_percent": v}))
    return checks
