from pcpulse import collect_snapshot
def test_snapshot_has_core_fields():
    s=collect_snapshot()
    assert s.schema_version=="1.0"
    assert s.os and s.architecture
