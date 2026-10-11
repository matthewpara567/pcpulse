import getpass
import platform
import time
from datetime import datetime, timezone
from typing import Any

import psutil

from .models import (
    BatteryInfo,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInterface,
    ProcessInfo,
    SensorReading,
    Snapshot,
    SwapInfo,
)

SCHEMA_VERSION = "1.1"
_SKIP_FSTYPES = {"squashfs", "iso9660", "erofs"}


def _disks() -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    seen: set[str] = set()
    for part in psutil.disk_partitions(all=False):
        if (
            part.mountpoint in seen
            or part.fstype in _SKIP_FSTYPES
            or part.device.startswith("/dev/loop")
            or not part.fstype
            or "cdrom" in part.opts
        ):
            continue
        seen.add(part.mountpoint)
        try:
            u = psutil.disk_usage(part.mountpoint)
            disks.append(DiskInfo(part.mountpoint, u.total, u.free, u.percent))
        except (OSError, PermissionError):
            disks.append(DiskInfo(part.mountpoint, None, None, None))
    return disks


def _swap() -> SwapInfo | None:
    try:
        s = psutil.swap_memory()
    except (OSError, RuntimeError):
        return None
    return SwapInfo(s.total, s.used, s.percent if s.total else None)


def _battery() -> BatteryInfo | None:
    fn: Any = getattr(psutil, "sensors_battery", None)
    if fn is None:
        return None
    try:
        b = fn()
    except (OSError, RuntimeError):
        return None
    if b is None:
        return None
    plugged = b.power_plugged if isinstance(b.power_plugged, bool) else None
    return BatteryInfo(float(b.percent), plugged)


def _network() -> list[NetworkInterface]:
    # Names and counters only. Addresses (IP/MAC) are never collected.
    try:
        stats = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)
    except (OSError, RuntimeError):
        return []
    out: list[NetworkInterface] = []
    for name in sorted(stats):
        if name == "lo" or name.lower().startswith("loopback"):
            continue
        c = counters.get(name)
        out.append(
            NetworkInterface(
                name, stats[name].isup, c.bytes_sent if c else None, c.bytes_recv if c else None
            )
        )
    return out


def _readings(func_name: str) -> list[SensorReading]:
    fn: Any = getattr(psutil, func_name, None)
    if fn is None:
        return []
    try:
        data = fn()
    except (OSError, RuntimeError):
        return []
    out: list[SensorReading] = []
    for chip in sorted(data):
        for i, entry in enumerate(data[chip]):
            current = getattr(entry, "current", None)
            if current is None:
                continue
            out.append(SensorReading(f"{chip}:{entry.label or i}", float(current)))
    return out


def _top_processes(limit: int) -> list[ProcessInfo]:
    rows: list[ProcessInfo] = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
        info = p.info
        mem = info.get("memory_info")
        if mem is None:
            continue
        pct = info.get("memory_percent")
        rows.append(
            ProcessInfo(
                info["pid"],
                info.get("name") or "?",
                round(pct, 1) if pct is not None else None,
                mem.rss,
            )
        )
    rows.sort(key=lambda r: r.rss_bytes or 0, reverse=True)
    return rows[: max(1, limit)]


def collect_snapshot(
    *,
    include_identity: bool = False,
    include_processes: bool = False,
    process_limit: int = 5,
) -> Snapshot:
    vm = psutil.virtual_memory()
    return Snapshot(
        collected_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        schema_version=SCHEMA_VERSION,
        os=platform.system(),
        kernel=platform.version() if platform.system() == "Windows" else platform.release(),
        architecture=platform.machine(),
        cpu=CpuInfo(
            psutil.cpu_count(), psutil.cpu_count(logical=False), psutil.cpu_percent(interval=0.3)
        ),
        memory=MemoryInfo(vm.total, vm.available, vm.used, vm.percent),
        disks=_disks(),
        uptime_seconds=round(max(0.0, time.time() - psutil.boot_time()), 1),
        hostname=platform.node() if include_identity else None,
        username=getpass.getuser() if include_identity else None,
        swap=_swap(),
        battery=_battery(),
        network=_network(),
        temperatures=_readings("sensors_temperatures"),
        fans=_readings("sensors_fans"),
        processes=_top_processes(process_limit) if include_processes else None,
    )
