import json
from collections import namedtuple
from pathlib import Path

import psutil
import pytest
from jsonschema import Draft202012Validator

from pcpulse import cli, collect_snapshot, run_checks
from pcpulse.health import Thresholds
from pcpulse.models import (
    BatteryInfo,
    CpuInfo,
    MemoryInfo,
    NetworkInterface,
    ProcessInfo,
    SensorReading,
    Snapshot,
    SwapInfo,
)
from pcpulse.serialization import format_bytes, to_markdown, to_text


def snap(mem=10.0, load=1.0, **kw):
    return Snapshot(
        collected_at="t",
        schema_version="1.1",
        os="Linux",
        kernel="6",
        architecture="x86_64",
        cpu=CpuInfo(4, 2, load),
        memory=MemoryInfo(1, 1, 0, mem),
        **kw,
    )


def status(checks, check_id):
    return next(c.status for c in checks if c.id == check_id)


def ids(checks):
    return {c.id for c in checks}


# --- thresholds -------------------------------------------------------------


def test_default_and_custom_thresholds():
    assert status(run_checks(snap(mem=90.0)), "memory.usage") == "warning"
    assert status(run_checks(snap(mem=96.0)), "memory.usage") == "error"
    relaxed = Thresholds(mem_warn=95.0, mem_error=99.0)
    assert status(run_checks(snap(mem=90.0), relaxed), "memory.usage") == "ok"
    assert status(run_checks(snap(load=60.0), Thresholds(cpu_warn=50.0)), "cpu.load") == "warning"


# --- swap, battery, temperature ---------------------------------------------


def test_swap_check():
    assert "swap.usage" not in ids(run_checks(snap()))
    assert "swap.usage" not in ids(run_checks(snap(swap=SwapInfo(0, 0, None))))
    assert status(run_checks(snap(swap=SwapInfo(100, 10, 10.0))), "swap.usage") == "ok"
    assert status(run_checks(snap(swap=SwapInfo(100, 60, 60.0))), "swap.usage") == "warning"
    assert status(run_checks(snap(swap=SwapInfo(100, 95, 95.0))), "swap.usage") == "error"


def test_battery_check():
    assert "battery.level" not in ids(run_checks(snap()))
    low = run_checks(snap(battery=BatteryInfo(15.0, False)))
    assert status(low, "battery.level") == "warning"
    critical = run_checks(snap(battery=BatteryInfo(5.0, False)))
    assert status(critical, "battery.level") == "error"
    charging = run_checks(snap(battery=BatteryInfo(5.0, True)))
    assert status(charging, "battery.level") == "ok"


def test_temperature_check():
    assert "temperature.max" not in ids(run_checks(snap()))
    for value, expected in [(60.0, "ok"), (90.0, "warning"), (96.0, "error")]:
        temps = [SensorReading("a", 40.0), SensorReading("b", value)]
        assert status(run_checks(snap(temperatures=temps)), "temperature.max") == expected


# --- collectors -------------------------------------------------------------


def test_network_never_collects_addresses():
    for n in collect_snapshot().network:
        assert set(n.__dict__) == {"name", "is_up", "bytes_sent", "bytes_recv"}


def test_processes_are_opt_in_and_limited():
    assert collect_snapshot().processes is None
    s = collect_snapshot(include_processes=True, process_limit=3)
    assert s.processes is not None
    assert 1 <= len(s.processes) <= 3
    sizes = [p.rss_bytes or 0 for p in s.processes]
    assert sizes == sorted(sizes, reverse=True)


def test_fake_sensors_and_battery(monkeypatch):
    temp = namedtuple("temp", "label current high critical")
    fan = namedtuple("fan", "label current")
    batt = namedtuple("batt", "percent secsleft power_plugged")
    monkeypatch.setattr(
        psutil,
        "sensors_temperatures",
        lambda: {"cpu": [temp("core", 55.0, None, None)]},
        raising=False,
    )
    monkeypatch.setattr(psutil, "sensors_fans", lambda: {"case": [fan("", 1200)]}, raising=False)
    monkeypatch.setattr(psutil, "sensors_battery", lambda: batt(42, 3600, False), raising=False)
    s = collect_snapshot()
    assert s.temperatures == [SensorReading("cpu:core", 55.0)]
    assert s.fans == [SensorReading("case:0", 1200.0)]
    assert s.battery == BatteryInfo(42.0, False)


def test_missing_sensors_are_empty(monkeypatch):
    monkeypatch.delattr(psutil, "sensors_temperatures", raising=False)
    monkeypatch.delattr(psutil, "sensors_battery", raising=False)
    s = collect_snapshot()
    assert s.temperatures == []
    assert s.battery is None


# --- output -----------------------------------------------------------------


def test_format_bytes():
    assert format_bytes(None) == "unavailable"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(5 * 1024**3) == "5.0 GB"


def test_markdown_and_text_show_new_data():
    s = snap(
        swap=SwapInfo(100, 10, 10.0),
        battery=BatteryInfo(80.0, True),
        network=[NetworkInterface("eth0", True, 2048, 4096)],
        temperatures=[SensorReading("cpu:core", 55.0)],
        fans=[SensorReading("case:0", 1200.0)],
        processes=[ProcessInfo(1, "init", 1.0, 1024)],
    )
    md = to_markdown(s)
    for expected in [
        "| Swap used | 10.0 |",
        "80.0% (plugged in)",
        "## Network",
        "eth0: up, sent 2.0 KB, received 4.0 KB",
        "cpu:core: 55.0 C",
        "case:0: 1200 RPM",
        "| 1 | init | 1.0 KB |",
    ]:
        assert expected in md
    text = to_text(s)
    assert "Swap: 10.0% used" in text
    assert "Battery: 80.0% (plugged in)" in text
    assert "1 init: 1.0 KB" in text


def test_full_snapshot_matches_schema():
    path = Path(__file__).resolve().parents[1] / "schemas" / "snapshot-1.1.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(collect_snapshot(include_processes=True).to_dict())


# --- CLI --------------------------------------------------------------------


def fake(monkeypatch, **kw):
    monkeypatch.setattr(cli, "collect_snapshot", lambda **_: snap(**kw))


def test_fail_on(monkeypatch):
    fake(monkeypatch, mem=90.0)  # warning
    assert cli.main(["doctor"]) == 0
    assert cli.main(["doctor", "--fail-on", "warning"]) == 1
    fake(monkeypatch, mem=99.0)  # error
    assert cli.main(["doctor"]) == 1
    assert cli.main(["doctor", "--fail-on", "never"]) == 0


def test_threshold_flags(monkeypatch, capsys):
    fake(monkeypatch, mem=90.0)
    assert cli.main(["doctor", "--warn-mem", "95", "--error-mem", "99"]) == 0
    assert "[OK] Memory usage" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["doctor", "--warn-mem", "95", "--error-mem", "90"],
        ["doctor", "--warn-mem", "150"],
        ["doctor", "--watch", "0"],
        ["doctor", "--watch", "1", "--output", "x.txt"],
        ["snapshot", "--top", "0"],
    ],
)
def test_bad_arguments_exit_with_usage_error(argv):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2


def test_output_file(tmp_path, capsys):
    target = tmp_path / "report.json"
    assert cli.main(["snapshot", "--json", "--output", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "1.1"
    assert capsys.readouterr().out == ""


def test_watch_stops_on_ctrl_c(monkeypatch, capsys):
    calls = []

    def fake_sleep(seconds):
        calls.append(seconds)
        raise KeyboardInterrupt

    fake(monkeypatch, mem=10.0)
    monkeypatch.setattr(cli.time, "sleep", fake_sleep)
    assert cli.main(["doctor", "--watch", "2"]) == 0
    assert calls == [2.0]
    assert "[OK] Memory usage" in capsys.readouterr().out


def test_snapshot_processes_flag(monkeypatch, capsys):
    seen = {}

    def fake_collect(**kw):
        seen.update(kw)
        return snap(processes=[ProcessInfo(7, "demo", 1.0, 2048)])

    monkeypatch.setattr(cli, "collect_snapshot", fake_collect)
    assert cli.main(["snapshot", "--include-processes", "--top", "2"]) == 0
    assert seen["include_processes"] is True and seen["process_limit"] == 2
    assert "7 demo: 2.0 KB" in capsys.readouterr().out
