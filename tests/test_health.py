from pcpulse import collect_snapshot, run_checks
def test_health_checks_return_results():
    checks=run_checks(collect_snapshot())
    assert checks
    assert all(c.status in {"ok","warning","error","unknown"} for c in checks)
