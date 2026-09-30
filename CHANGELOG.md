# Changelog

## Unreleased

- Markdown uptime is human-readable (for example `2h 16m`)
- On Windows, `kernel` now reports the NT version instead of just `11`
- `--include-identity` now adds hostname and username to Markdown output
- `doctor` checks CPU load (warns at 90% or higher)

## 0.1.2

- CI now runs on Linux, Windows, and macOS
- Snapshot output is validated against the JSON Schema in tests
- Added RELEASING.md and a bug report issue template
- Fixed Markdown showing 'unavailable% used'
- `doctor` skips empty card readers and optical drives
- Steadier CPU load sampling

## 0.1.1

- Fixed lint and type-check CI failures
- Removed unused `rich` dependency
- `doctor` ignores read-only squashfs, ISO, and loop mounts
- `--json` and `--markdown` are now mutually exclusive
- Added `python -m pcpulse`

## 0.1.0 — Initial public release

- Cross-platform system snapshot API
- JSON and Markdown serialization
- CLI snapshot and doctor commands
- Versioned snapshot schema
- Privacy-conscious identity opt-in
- Automated tests and development tooling
