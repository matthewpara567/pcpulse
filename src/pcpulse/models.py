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
class SwapInfo:
    total_bytes: int | None
    used_bytes: int | None
    used_percent: float | None


@dataclass(frozen=True)
class BatteryInfo:
    percent: float | None
    plugged_in: bool | None


@dataclass(frozen=True)
class NetworkInterface:
    name: str
    is_up: bool | None
    bytes_sent: int | None
    bytes_recv: int | None


@dataclass(frozen=True)
class SensorReading:
    label: str
    value: float


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HealthCheck:
    id: str
    status: Status
    message: str
    details: dict[str, Any] = field(default_factory=dict)
