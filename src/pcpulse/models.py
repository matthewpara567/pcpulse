from dataclasses import asdict, dataclass, field
from typing import Any
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
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
@dataclass(frozen=True)
class HealthCheck:
    id: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
