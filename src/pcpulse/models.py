"""Typed public data models returned by PCPulse."""
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Status = Literal["ok", "warning", "error", "unknown"]


@dataclass(frozen=True)
class CpuInfo:
    logical_cores: int | None
    physical_cores: int | None
    load_percent: float | None


@dataclass(frozen=True)
class MemoryInfo:
    total_bytes: int | None
    available_bytes: int | None
    used_bytes: int | None
    used_percent: float | None


@dataclass(frozen=True)
class DiskInfo:
    path: str
    total_bytes: int | None
    free_bytes: int | None
    used_percent: float | None


@dataclass(frozen=True)
class DiskIoInfo:
    read_bytes: int | None = None
    write_bytes: int | None = None
    read_rate_bytes_per_sec: float | None = None
    write_rate_bytes_per_sec: float | None = None


@dataclass(frozen=True)
class SwapInfo:
    total_bytes: int | None
    used_bytes: int | None
    used_percent: float | None


@dataclass(frozen=True)
class BatteryInfo:
    percent: float | None
    plugged_in: bool | None
    design_capacity_mwh: int | None = None
    full_charge_capacity_mwh: int | None = None
    cycle_count: int | None = None
    health_percent: float | None = None


@dataclass(frozen=True)
class NetworkInterface:
    name: str
    is_up: bool | None
    bytes_sent: int | None
    bytes_recv: int | None
    send_rate_bytes_per_sec: float | None = None
    recv_rate_bytes_per_sec: float | None = None


@dataclass(frozen=True)
class SensorReading:
    label: str
    value: float
    high_celsius: float | None = None
    critical_celsius: float | None = None


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vendor: str | None = None
    utilization_percent: float | None = None
    memory_total_bytes: int | None = None
    memory_used_bytes: int | None = None
    temperature_celsius: float | None = None
    source: str | None = None


@dataclass(frozen=True)
class StorageHealthInfo:
    device: str
    model: str | None = None
    health_status: str = "unknown"
    temperature_celsius: float | None = None
    percentage_used: float | None = None
    power_on_hours: int | None = None


@dataclass(frozen=True)
class HardwareInfo:
    cpu_vendor: str | None = None
    cpu_model: str | None = None
    cpu_frequency_mhz: float | None = None
    system_vendor: str | None = None
    system_model: str | None = None
    motherboard_vendor: str | None = None
    motherboard_model: str | None = None


@dataclass(frozen=True)
class CollectionError:
    component: str
    error_type: str
    message: str


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    memory_percent: float | None
    rss_bytes: int | None


@dataclass(frozen=True)
class Snapshot:
    collected_at: str
    schema_version: str
    os: str
    kernel: str
    architecture: str
    cpu: CpuInfo
    memory: MemoryInfo
    disks: list[DiskInfo] = field(default_factory=list)
    uptime_seconds: float | None = None
    hostname: str | None = None
    username: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    swap: SwapInfo | None = None
    battery: BatteryInfo | None = None
    network: list[NetworkInterface] = field(default_factory=list)
    temperatures: list[SensorReading] = field(default_factory=list)
    fans: list[SensorReading] = field(default_factory=list)
    processes: list[ProcessInfo] | None = None
    hardware: HardwareInfo | None = None
    gpus: list[GpuInfo] = field(default_factory=list)
    storage_health: list[StorageHealthInfo] = field(default_factory=list)
    disk_io: DiskIoInfo | None = None
    collection_errors: list[CollectionError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HealthCheck:
    id: str
    status: Status
    message: str
    details: dict[str, Any] = field(default_factory=dict)
