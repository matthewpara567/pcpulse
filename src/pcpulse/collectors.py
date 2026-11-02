"""Best-effort, local-only system collectors.


Optional probes never prevent the rest of a snapshot from being returned.
External tools are invoked only with fixed argument lists (never through a shell).
"""
# ruff: noqa: BLE001 - isolate arbitrary failures from optional OS and driver probes.
import csv
import getpass
import json
import math
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

import psutil

from .models import (
    BatteryInfo,
    CollectionError,
    CpuInfo,
    DiskInfo,
    DiskIoInfo,
    GpuInfo,
    HardwareInfo,
    MemoryInfo,
    NetworkInterface,
    ProcessInfo,
    SensorReading,
    Snapshot,
    StorageHealthInfo,
    SwapInfo,
)

SCHEMA_VERSION = "1.2"
_SKIP_FSTYPES = {"squashfs", "iso9660", "erofs"}
T = TypeVar("T")


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _record_error(errors: list[CollectionError], component: str, exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        message = "Permission denied."
    elif isinstance(exc, (NotImplementedError, AttributeError)):
        message = "Not supported on this platform."
    elif isinstance(exc, (psutil.AccessDenied,)):
        message = "Permission denied."
    elif isinstance(exc, (psutil.NoSuchProcess, psutil.ZombieProcess)):
        message = "The process no longer exists."
    else:
        message = "The metric could not be collected."
    item = CollectionError(component, type(exc).__name__, message)
    if item not in errors:
        errors.append(item)


def _safe(
    component: str, fn: Callable[[], T], fallback: T, errors: list[CollectionError]
) -> T:
    try:
        return fn()
    except Exception as exc:  # A failed optional probe must not abort a full snapshot.
        _record_error(errors, component, exc)
        return fallback


def _disks(errors: list[CollectionError]) -> list[DiskInfo]:
    parts = _safe("disk.partitions", lambda: psutil.disk_partitions(all=False), [], errors)
    disks: list[DiskInfo] = []
    seen: set[str] = set()
    for part in parts:
        try:
            mountpoint = str(part.mountpoint)
            fstype = str(part.fstype or "").lower()
            opts = str(part.opts or "").lower()
            device = str(part.device or "")
            if (
                not mountpoint
                or mountpoint in seen
                or fstype in _SKIP_FSTYPES
                or device.startswith("/dev/loop")
                or not fstype
                or "cdrom" in opts
            ):
                continue
            seen.add(mountpoint)
            usage = psutil.disk_usage(mountpoint)
            disks.append(
                DiskInfo(
                    mountpoint,
                    int(usage.total),
                    int(usage.free),
                    _finite(usage.percent),
                )
            )
        except Exception as exc:
            _record_error(errors, "disk.usage", exc)
            disks.append(DiskInfo(str(getattr(part, "mountpoint", "unknown")), None, None, None))
    return disks


def _swap(errors: list[CollectionError]) -> SwapInfo | None:
    try:
        s = psutil.swap_memory()
        return SwapInfo(int(s.total), int(s.used), _finite(s.percent) if s.total else None)
    except Exception as exc:
        _record_error(errors, "swap", exc)
        return None


def _linux_battery_metadata() -> tuple[int | None, int | None, int | None]:
    """Read Linux power-supply metadata. Sysfs energy values are expressed in µWh."""
    roots = sorted(Path("/sys/class/power_supply").glob("BAT*"))
    for root in roots:
        try:
            design_raw = (root / "energy_full_design").read_text(encoding="ascii").strip()
            full_raw = (root / "energy_full").read_text(encoding="ascii").strip()
            design = int(design_raw) // 1000
            full = int(full_raw) // 1000
            try:
                cycles = int((root / "cycle_count").read_text(encoding="ascii").strip())
            except (OSError, ValueError):
                cycles = None
            return design or None, full or None, cycles
        except (OSError, ValueError):
            # Some batteries expose charge (µAh) instead of energy (µWh). Do not
            # guess capacity without a voltage conversion.
            continue
    return None, None, None


def _battery(errors: list[CollectionError]) -> BatteryInfo | None:
    percent: float | None = None
    plugged: bool | None = None
    fn = getattr(psutil, "sensors_battery", None)
    if fn is not None:
        try:
            battery = fn()
            if battery is not None:
                percent = _finite(battery.percent)
                plugged = battery.power_plugged if isinstance(battery.power_plugged, bool) else None
        except Exception as exc:
            _record_error(errors, "battery", exc)
    design, full, cycles = _safe(
        "battery.health", _linux_battery_metadata, (None, None, None), errors
    )
    health = (full / design * 100.0) if design and full is not None else None
    if percent is None and design is None and full is None and cycles is None:
        return None
    return BatteryInfo(percent, plugged, design, full, cycles, _finite(health))


def _network(
    sample_interval_seconds: float, errors: list[CollectionError]
) -> list[NetworkInterface]:
    stats = _safe("network.interfaces", psutil.net_if_stats, {}, errors)
    before = _safe("network.counters", lambda: psutil.net_io_counters(pernic=True), {}, errors)
    after = before
    elapsed = 0.0
    if sample_interval_seconds > 0:
        start = time.monotonic()
        time.sleep(sample_interval_seconds)
        sampled = _safe("network.counters", lambda: psutil.net_io_counters(pernic=True), None, errors)
        after = sampled if sampled is not None else before
        if sampled is not None:
            elapsed = max(time.monotonic() - start, 0.001)
    out: list[NetworkInterface] = []
    for name in sorted(stats):
        if name == "lo" or name.lower().startswith("loopback"):
            continue
        current = after.get(name)
        initial = before.get(name)
        sent = int(current.bytes_sent) if current is not None else None
        received = int(current.bytes_recv) if current is not None else None
        tx_rate = rx_rate = None
        if elapsed and current is not None and initial is not None:
            tx_rate = _finite(max(0, current.bytes_sent - initial.bytes_sent) / elapsed)
            rx_rate = _finite(max(0, current.bytes_recv - initial.bytes_recv) / elapsed)
        out.append(
            NetworkInterface(
                name,
                bool(stats[name].isup),
                sent,
                received,
                tx_rate,
                rx_rate,
            )
        )
    return out


def _disk_io(sample_interval_seconds: float, errors: list[CollectionError]) -> DiskIoInfo | None:
    before = _safe("disk.io", psutil.disk_io_counters, None, errors)
    if before is None:
        return None
    elapsed = 0.0
    after = before
    if sample_interval_seconds > 0:
        start = time.monotonic()
        time.sleep(sample_interval_seconds)
        sampled = _safe("disk.io", psutil.disk_io_counters, None, errors)
        if sampled is not None:
            after = sampled
            elapsed = max(time.monotonic() - start, 0.001)
    read_rate = write_rate = None
    if elapsed:
        read_rate = _finite(max(0, after.read_bytes - before.read_bytes) / elapsed)
        write_rate = _finite(max(0, after.write_bytes - before.write_bytes) / elapsed)
    return DiskIoInfo(
        int(after.read_bytes),
        int(after.write_bytes),
        read_rate,
        write_rate,
    )


def _readings(func_name: str, errors: list[CollectionError]) -> list[SensorReading]:
    fn = getattr(psutil, func_name, None)
    if fn is None:
        return []
    data = _safe(f"sensors.{func_name}", fn, {}, errors)
    out: list[SensorReading] = []
    try:
        for chip in sorted(data):
            for index, entry in enumerate(data[chip]):
                current = _finite(getattr(entry, "current", None))
                if current is None:
                    continue
                out.append(
                    SensorReading(
                        f"{chip}:{getattr(entry, 'label', None) or index}",
                        current,
                        _finite(getattr(entry, "high", None)),
                        _finite(getattr(entry, "critical", None)),
                    )
                )
    except Exception as exc:
        _record_error(errors, f"sensors.{func_name}", exc)
    return out


def _top_processes(limit: int, errors: list[CollectionError]) -> list[ProcessInfo]:
    rows: list[ProcessInfo] = []
    try:
        for process in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
            try:
                info = process.info or {}
                mem = info.get("memory_info")
                if mem is None:
                    continue
                pct = _finite(info.get("memory_percent"))
                rows.append(
                    ProcessInfo(
                        int(info.get("pid", process.pid)),
                        str(info.get("name") or "?"),
                        round(pct, 1) if pct is not None else None,
                        int(mem.rss),
                    )
                )
            except (psutil.Error, OSError):
                # Processes can exit or become inaccessible while enumerating.
                continue
    except Exception as exc:
        _record_error(errors, "processes", exc)
    rows.sort(key=lambda row: row.rss_bytes or 0, reverse=True)
    return rows[: max(1, limit)]


def _read_text(path: str) -> str | None:
    try:
        value = Path(path).read_text(encoding="utf-8", errors="replace").strip()
        return value or None
    except OSError:
        return None


def _hardware(errors: list[CollectionError]) -> HardwareInfo:
    cpu_vendor = cpu_model = None
    cpuinfo = _read_text("/proc/cpuinfo")
    if cpuinfo:
        for line in cpuinfo.splitlines():
            if ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            if key in {"vendor_id", "CPU implementer"} and cpu_vendor is None:
                cpu_vendor = value
            elif key in {"model name", "Hardware", "Processor"} and cpu_model is None:
                cpu_model = value
            if cpu_vendor and cpu_model:
                break
    cpu_model = cpu_model or platform.processor() or None
    frequency = _safe(
        "hardware.cpu_frequency",
        lambda: getattr(psutil.cpu_freq(), "current", None),
        None,
        errors,
    )
    dmi = Path("/sys/class/dmi/id")
    return HardwareInfo(
        cpu_vendor=cpu_vendor,
        cpu_model=cpu_model,
        cpu_frequency_mhz=_finite(frequency),
        system_vendor=_read_text(str(dmi / "sys_vendor")),
        system_model=_read_text(str(dmi / "product_name")),
        motherboard_vendor=_read_text(str(dmi / "board_vendor")),
        motherboard_model=_read_text(str(dmi / "board_name")),
    )


def _gpu_vendor(pci_vendor: str | None) -> str | None:
    return {
        "0x10de": "NVIDIA",
        "0x1002": "AMD",
        "0x1022": "AMD",
        "0x8086": "Intel",
        "0x106b": "Apple",
    }.get((pci_vendor or "").lower())


def _gpus(errors: list[CollectionError]) -> list[GpuInfo]:
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,utilization.gpu,memory.total,memory.used,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if result.returncode == 0:
                out: list[GpuInfo] = []
                for row in csv.reader(result.stdout.splitlines()):
                    if not row:
                        continue

                    def number(value: str) -> float | None:
                        return _finite(value.strip()) if value.strip().lower() not in {"n/a", "[not supported]"} else None

                    total_mb = number(row[2]) if len(row) > 2 else None
                    used_mb = number(row[3]) if len(row) > 3 else None
                    out.append(
                        GpuInfo(
                            name=row[0].strip(),
                            vendor="NVIDIA",
                            utilization_percent=number(row[1]) if len(row) > 1 else None,
                            memory_total_bytes=int(total_mb * 1024 * 1024) if total_mb is not None else None,
                            memory_used_bytes=int(used_mb * 1024 * 1024) if used_mb is not None else None,
                            temperature_celsius=number(row[4]) if len(row) > 4 else None,
                            source="nvidia-smi",
                        )
                    )
                if out:
                    return out
            else:
                _record_error(errors, "gpu.nvidia_smi", RuntimeError("nvidia-smi failed"))
        except Exception as exc:
            _record_error(errors, "gpu.nvidia_smi", exc)

    out = []
    if platform.system() == "Linux":
        for device in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
            try:
                card_name = device.parent.name
                if not re.fullmatch(r"card[0-9]+", card_name):
                    continue
                vendor_id = _read_text(str(device / "vendor"))
                device_id = _read_text(str(device / "device"))
                product = _read_text(str(device / "product_name"))
                total = _read_text(str(device / "mem_info_vram_total"))
                used = _read_text(str(device / "mem_info_vram_used"))
                busy = _read_text(str(device / "gpu_busy_percent"))
                vendor = _gpu_vendor(vendor_id)
                out.append(
                    GpuInfo(
                        name=product or (f"GPU {device_id}" if device_id else card_name),
                        vendor=vendor,
                        utilization_percent=_finite(busy),
                        memory_total_bytes=int(total) if total and total.isdigit() else None,
                        memory_used_bytes=int(used) if used and used.isdigit() else None,
                        source="linux-drm-sysfs",
                    )
                )
            except OSError as exc:
                _record_error(errors, "gpu.sysfs", exc)
    return out


def _storage_devices() -> list[str]:
    devices: set[str] = set()
    if platform.system() == "Linux":
        by_id = Path("/dev/disk/by-id")
        if by_id.exists():
            for item in by_id.iterdir():
                if "-part" in item.name:
                    continue
                try:
                    target = str(item.resolve())
                    if target.startswith("/dev/") and not target.startswith("/dev/dm-"):
                        devices.add(target)
                except OSError:
                    continue
    if not devices:
        for part in psutil.disk_partitions(all=False):
            device = str(part.device or "")
            if not device.startswith("/dev/"):
                continue
            device = re.sub(r"p[0-9]+$", "", device)
            device = re.sub(r"[0-9]+$", "", device) if re.search(r"/(sd|vd|xvd)[a-z]+[0-9]+$", device) else device
            if device != "/dev":
                devices.add(device)
    return sorted(devices)[:8]


def _storage_health(errors: list[CollectionError]) -> list[StorageHealthInfo]:
    smartctl = shutil.which("smartctl")
    if not smartctl:
        return []
    devices = _safe("storage.devices", _storage_devices, [], errors)
    out: list[StorageHealthInfo] = []
    for device in devices:
        try:
            result = subprocess.run(
                [smartctl, "-j", "-a", device],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                _record_error(errors, "storage.smartctl", RuntimeError("Invalid smartctl JSON"))
                continue
            if not isinstance(data, dict):
                _record_error(errors, "storage.smartctl", ValueError("SMART JSON root is not an object"))
                continue
            nvme = data.get("nvme_smart_health_information_log") or {}
            if not isinstance(nvme, dict):
                nvme = {}
            temp = _finite(nvme.get("temperature"))
            percentage_used = _finite(nvme.get("percentage_used"))
            power_on_time = nvme.get("power_on_time")
            power_hours = power_on_time.get("hours") if isinstance(power_on_time, dict) else None
            if temp is None:
                temperature_data = data.get("temperature") or {}
                temp = _finite(temperature_data.get("current")) if isinstance(temperature_data, dict) else None
            if temp is None:
                ata = data.get("ata_smart_attributes") or {}
                table = ata.get("table", []) if isinstance(ata, dict) else []
                for attr in table if isinstance(table, list) else []:
                    if isinstance(attr, dict) and attr.get("id") == 194:
                        raw_data = attr.get("raw")
                        raw = raw_data.get("value") if isinstance(raw_data, dict) else None
                        temp = _finite(raw)
                        break
            smart_status = data.get("smart_status") or {}
            passed = smart_status.get("passed") if isinstance(smart_status, dict) else None
            health_status = "passed" if passed is True else "failed" if passed is False else "unknown"
            model = data.get("model_name") or data.get("model_family")
            smartctl_meta = data.get("smartctl") or {}
            exit_status = smartctl_meta.get("exit_status", 0) if isinstance(smartctl_meta, dict) else 0
            if exit_status != 0 and health_status == "unknown":
                _record_error(errors, "storage.smartctl", RuntimeError("smartctl reported an unsuccessful or incomplete query"))
            out.append(
                StorageHealthInfo(
                    device=device,
                    model=str(model) if model else None,
                    health_status=health_status,
                    temperature_celsius=temp,
                    percentage_used=percentage_used,
                    power_on_hours=int(power_hours) if isinstance(power_hours, (int, float)) and math.isfinite(power_hours) and power_hours >= 0 else None,
                )
            )
        except Exception as exc:
            _record_error(errors, "storage.smartctl", exc)
    return out


def collect_snapshot(
    *,
    include_identity: bool = False,
    include_processes: bool = False,
    process_limit: int = 5,
    include_storage_health: bool = False,
    sample_interval_seconds: float = 0.0,
) -> Snapshot:
    """Collect a local snapshot; unsupported or inaccessible metrics are recorded as errors."""
    if not math.isfinite(sample_interval_seconds) or not 0 <= sample_interval_seconds <= 30:
        raise ValueError("sample_interval_seconds must be between 0 and 30")
    if process_limit < 1:
        raise ValueError("process_limit must be at least 1")

    errors: list[CollectionError] = []
    vm = _safe("memory", psutil.virtual_memory, None, errors)
    memory = (
        MemoryInfo(int(vm.total), int(vm.available), int(vm.used), _finite(vm.percent))
        if vm is not None
        else MemoryInfo(None, None, None, None)
    )
    logical = _safe("cpu.logical_cores", psutil.cpu_count, None, errors)
    physical = _safe("cpu.physical_cores", lambda: psutil.cpu_count(logical=False), None, errors)
    load = _safe("cpu.load", lambda: psutil.cpu_percent(interval=0.3), None, errors)
    uptime = _safe("uptime", lambda: max(0.0, time.time() - psutil.boot_time()), None, errors)
    system = _safe("platform.system", platform.system, "Unknown", errors)
    kernel = _safe(
        "platform.kernel",
        lambda: platform.version() if system == "Windows" else platform.release(),
        "Unknown",
        errors,
    )
    architecture = _safe("platform.architecture", platform.machine, "Unknown", errors)

    network = _network(sample_interval_seconds, errors)
    disk_io = _disk_io(sample_interval_seconds, errors)
    temperatures = _readings("sensors_temperatures", errors)
    fans = _readings("sensors_fans", errors)
    gpus = _gpus(errors)
    for gpu in gpus:
        if gpu.temperature_celsius is not None:
            temperatures.append(SensorReading(f"GPU:{gpu.name}", gpu.temperature_celsius))

    battery = _battery(errors)
    return Snapshot(
        collected_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        schema_version=SCHEMA_VERSION,
        os=system,
        kernel=kernel,
        architecture=architecture,
        cpu=CpuInfo(logical, physical, _finite(load)),
        memory=memory,
        disks=_disks(errors),
        uptime_seconds=_finite(uptime),
        hostname=platform.node() if include_identity else None,
        username=getpass.getuser() if include_identity else None,
        swap=_swap(errors),
        battery=battery,
        network=network,
        temperatures=temperatures,
        fans=fans,
        processes=_top_processes(process_limit, errors) if include_processes else None,
        hardware=_hardware(errors),
        gpus=gpus,
        storage_health=_storage_health(errors) if include_storage_health else [],
        disk_io=disk_io,
        collection_errors=errors,
    )
