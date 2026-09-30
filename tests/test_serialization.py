import json

from pcpulse import collect_snapshot
from pcpulse.serialization import to_json, to_markdown


def test_json_is_valid():
    assert json.loads(to_json(collect_snapshot()))["schema_version"]=="1.0"
def test_markdown_contains_title():
    assert "PCPulse System Snapshot" in to_markdown(collect_snapshot())


def test_markdown_unavailable_disk_has_no_stray_percent():
    from dataclasses import replace

    from pcpulse.models import DiskInfo

    snap = replace(collect_snapshot(), disks=[DiskInfo("X:\\", None, None, None)])
    md = to_markdown(snap)
    assert "X:\\: unavailable" in md
    assert "unavailable%" not in md
