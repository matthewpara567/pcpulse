import getpass
import platform
import time
from datetime import datetime, timezone

import psutil

from .models import CpuInfo, DiskInfo, MemoryInfo, Snapshot

SCHEMA_VERSION = "1.0"
_SKIP_FSTYPES = {"squashfs", "iso9660", "erofs"}


def collect_snapshot(*, include_identity: bool = False) -> Snapshot:
    vm = psutil.virtual_memory()
    disks, seen = [], set()
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
    return Snapshot(
        collected_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        schema_version=SCHEMA_VERSION,
        os=platform.system(),
        kernel=platform.release(),
        architecture=platform.machine(),
        cpu=CpuInfo(
            psutil.cpu_count(), psutil.cpu_count(logical=False), psutil.cpu_percent(interval=0.3)
        ),
        memory=MemoryInfo(vm.total, vm.available, vm.used, vm.percent),
        disks=disks,
        uptime_seconds=max(0.0, time.time() - psutil.boot_time()),
        hostname=platform.node() if include_identity else None,
        username=getpass.getuser() if include_identity else None,
    )
