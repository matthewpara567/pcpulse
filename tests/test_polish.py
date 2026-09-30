import platform

from pcpulse import collect_snapshot, run_checks
from pcpulse.models import CpuInfo, MemoryInfo, Snapshot
from pcpulse.serialization import format_uptime, to_markdown


def _snap(load, **kw):
    return Snapshot(
        collected_at="t",
        schema_version="1.0",
        os="Linux",
        kernel="6",
        architecture="x86_64",
        cpu=CpuInfo(4, 2, load),
        memory=MemoryInfo(1, 1, 0, 10.0),
        **kw,
    )


def _cpu_status(load):
    return next(c.status for c in run_checks(_snap(load)) if c.id == "cpu.load")


def test_cpu_check_thresholds():
    assert _cpu_status(10.0) == "ok"
    assert _cpu_status(90.0) == "warning"
    assert _cpu_status(None) == "unknown"


def test_format_uptime():
    assert format_uptime(None) == "unavailable"
    assert format_uptime(30) == "0m"
    assert format_uptime(8211.6) == "2h 16m"
    assert format_uptime(3 * 86400 + 4 * 3600 + 5 * 60) == "3d 4h 5m"


def test_markdown_identity_only_when_present():
    assert "Hostname" not in to_markdown(_snap(1.0))
    md = to_markdown(_snap(1.0, hostname="box", username="me"))
    assert "| Hostname | box |" in md
    assert "| Username | me |" in md


def test_windows_kernel_uses_nt_version(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "version", lambda: "10.0.26100")
    monkeypatch.setattr(platform, "release", lambda: "11")
    assert collect_snapshot().kernel == "10.0.26100"
