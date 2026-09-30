from pcpulse import collect_snapshot, run_checks

snapshot = collect_snapshot()
print(snapshot.to_dict())

for check in run_checks(snapshot):
    print(check.status, check.message)
