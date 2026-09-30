import json
from pcpulse import collect_snapshot
from pcpulse.serialization import to_json, to_markdown
def test_json_is_valid():
    assert json.loads(to_json(collect_snapshot()))["schema_version"]=="1.0"
def test_markdown_contains_title():
    assert "PCPulse System Snapshot" in to_markdown(collect_snapshot())
