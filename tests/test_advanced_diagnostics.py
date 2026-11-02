import json
import math
import zipfile
from pathlib import Path

import pytest

from pcpulse import collect_snapshot
from pcpulse.cli import main
from pcpulse.health import Thresholds, run_checks
from pcpulse.models import CollectionError, CpuInfo, MemoryInfo, SensorReading, Snapshot
from pcpulse.serialization import to_json, to_markdown


def minimal_snapshot(**kwargs):
    return Snapshot(
        collected_at="now", schema_version="1.2", os="Linux", kernel="test",
        architecture="x86_64", cpu=CpuInfo(4, 2, 10.0),
        memory=MemoryInfo(100, 80, 20, 20.0), **kwargs
    )


@pytest.mark.parametrize("kwargs", [
    {"mem_warn": math.nan}, {"mem_error": math.inf}, {"mem_warn": 110},
    {"disk_warn": -1}, {"swap_warn": 95, "swap_error": 90},
])
def test_thresholds_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        run_checks(minimal_snapshot(), Thresholds(**kwargs))


def test_markdown_escapes_untrusted_strings():
    snap = minimal_snapshot(hostname="host|bad\nrow", disks=[])
    text = to_markdown(snap)
    assert "host\\|bad row" in text
    assert "\nrow" not in text


def test_json_normalizes_non_finite_values():
    snap = minimal_snapshot(cpu=CpuInfo(4, 2, math.nan))
    parsed = json.loads(to_json(snap))
    assert parsed["cpu"]["load_percent"] is None


def test_collectors_continue_when_memory_probe_fails(monkeypatch):
    import pcpulse.collectors as collectors
    monkeypatch.setattr(collectors.psutil, "virtual_memory", lambda: (_ for _ in ()).throw(PermissionError()))
    snap = collect_snapshot(sample_interval_seconds=0)
    assert snap.memory.total_bytes is None
    assert any(error.component == "memory" for error in snap.collection_errors)
    assert snap.os


def test_schema_export(tmp_path):
    target = tmp_path / "schema.json"
    assert main(["schema", "--output", str(target)]) == 0
    schema = json.loads(target.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.2"


def test_report_bundle(tmp_path):
    target = tmp_path / "report.zip"
    assert main(["report", "--output", str(target), "--sample-interval", "0"]) == 0
    with zipfile.ZipFile(target) as archive:
        assert {"snapshot.json", "snapshot.md", "health-checks.json", "snapshot-1.2.schema.json"} <= set(archive.namelist())
        snapshot = json.loads(archive.read("snapshot.json"))
        assert snapshot["schema_version"] == "1.2"


def test_temperature_check_uses_sensor_thresholds():
    snap = minimal_snapshot(temperatures=[SensorReading("cpu", 80.0, 75.0, 90.0)])
    checks = run_checks(snap)
    temperature = next(check for check in checks if check.id == "temperature:cpu")
    assert temperature.status == "warning"


def test_collection_error_is_serialized():
    snap = minimal_snapshot(collection_errors=[CollectionError("gpu", "OSError", "unavailable")])
    assert "collection_errors" in json.loads(to_json(snap))
