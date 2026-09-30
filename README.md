# PCPulse

**Local-first, privacy-conscious, cross-platform PC diagnostics for humans, scripts, support tools, and developer applications.**

PCPulse is an open-source Python library and CLI for collecting useful system diagnostics without requiring a cloud service. It turns local machine information into typed Python objects and stable machine-readable output.

## Highlights

- Cross-platform system snapshots
- CPU, memory, disk, OS, architecture, and uptime information
- JSON and Markdown output
- Conservative local health checks with `pcpulse doctor`
- Versioned snapshot schema
- Privacy-first identity handling
- Python library API for integration into other tools
- No telemetry or mandatory network service
- MIT licensed
- Tests, linting, type checking, CI, security guidance, and contributor documentation

## Installation

Install the published package when available:

    python -m pip install pcpulse

For development:

    git clone https://github.com/matthewpara567/pcpulse.git
    cd pcpulse
    python -m pip install -e '.[dev]'

## Quick start

Collect a human-readable snapshot:

    pcpulse snapshot

Get JSON:

    pcpulse snapshot --json

Get Markdown:

    pcpulse snapshot --markdown

Run health checks:

    pcpulse doctor

Get machine-readable health checks:

    pcpulse doctor --json

Identity information is excluded by default. Opt in explicitly:

    pcpulse snapshot --include-identity

## Python API

    from pcpulse import collect_snapshot, run_checks

    snapshot = collect_snapshot()
    print(snapshot.to_dict())

    for check in run_checks(snapshot):
        print(check.status, check.message)

The library is intended to be the stable integration layer. The CLI is an interface over that library.

## Privacy

PCPulse is designed around a local-first model:

- No telemetry is required.
- No account is required.
- No cloud backend is required.
- Hostname and username are not collected unless explicitly requested.
- Collectors are read-only diagnostics and do not intentionally modify the host.
- Applications should sanitize reports before sharing them externally.

A diagnostic report can still contain machine-specific information such as operating-system details, mount paths, hardware counts, or uptime. Review output before publishing it.

## Snapshot schema

Snapshots carry an explicit schema version so consumers can distinguish format changes:

    "schema_version": "1.0"

The canonical JSON Schema is stored at:

    schemas/snapshot-1.0.schema.json

Consumers should treat schema changes as compatibility-sensitive and avoid assuming that every platform exposes every metric.

## Health checks

`pcpulse doctor` performs conservative checks for conditions such as high memory usage and high disk utilization.

A check can report:

- `ok`
- `warning`
- `error`
- `unknown`

Unknown is preferred over inventing a value when the operating system does not expose a metric.

## Architecture

PCPulse separates:

1. **Collectors** — read local system information.
2. **Models** — provide typed Python representations.
3. **Serialization** — converts snapshots to JSON or Markdown.
4. **Health checks** — interprets selected metrics.
5. **CLI** — provides a user-facing command interface.

This separation makes PCPulse useful as a library without requiring applications to scrape terminal output.

## Development

Install development dependencies:

    python -m pip install -e '.[dev]'

Run the test suite:

    pytest -q

Run linting:

    ruff check .

Run type checking:

    mypy src

## Contributing

Bug fixes, documentation improvements, tests, platform compatibility work, and carefully scoped features are welcome.

Before opening a pull request:

- Keep the change focused.
- Add or update tests where appropriate.
- Document public API or schema changes.
- Consider privacy implications.
- Run the test, lint, and type-check commands.
- Avoid unrelated formatting churn.

See CONTRIBUTING.md for details.

## Security

Please do not disclose vulnerabilities in public issues. Follow SECURITY.md for responsible reporting.

Security-sensitive areas include unintended network activity, unsafe parsing, dependency vulnerabilities, command execution, and accidental disclosure of local information.

## Project structure

    pcpulse/
    ├── .github/
    │   ├── ISSUE_TEMPLATE/
    │   └── workflows/
    ├── docs/
    ├── examples/
    ├── schemas/
    ├── src/
    │   └── pcpulse/
    ├── tests/
    ├── CHANGELOG.md
    ├── CODE_OF_CONDUCT.md
    ├── CONTRIBUTING.md
    ├── GOVERNANCE.md
    ├── LICENSE
    ├── MAINTAINERS.md
    ├── README.md
    ├── RELEASING.md
    ├── SECURITY.md
    ├── SUPPORT.md
    └── pyproject.toml

## Design principles

PCPulse follows a few simple principles:

- **Local-first:** the core collector should work without a cloud service.
- **Privacy-first:** identity data is opt-in.
- **Structured:** machine-readable output is a first-class interface.
- **Best-effort:** unavailable metrics are represented as unavailable.
- **Read-only:** diagnostics should not silently modify the host.
- **Compatibility-conscious:** public API and schema changes should be deliberate.
- **Small core:** features should justify their maintenance cost.

## Roadmap

Potential future work includes:

- More detailed platform-specific hardware metrics
- Battery, temperature, and fan information where safely available
- Pluggable collectors
- Richer diagnostic bundles
- More schema validation tooling
- Additional operating-system compatibility tests
- Release provenance and artifact-integrity improvements

Roadmap items are not promises and may change as the project evolves.

## License

PCPulse is released under the MIT License. See LICENSE.

## Status

PCPulse is currently an early open-source project. APIs and schema details may evolve before the first stable release.
