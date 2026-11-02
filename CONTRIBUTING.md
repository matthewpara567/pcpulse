# Contributing to PCPulse

Thanks for considering a contribution. PCPulse is a local-first diagnostics library and CLI. Contributions should make diagnostics more accurate, portable, understandable, or privacy-preserving.

## Before you start

- Read the [README](README.md) to understand the project and its design principles.
- Check existing issues and pull requests before starting substantial work.
- For a large change, open an issue first so the scope can be discussed.
- If you are new to the project, documentation, tests, and small platform-compatibility fixes are good places to start.

## Development setup

PCPulse supports Python 3.10 and newer.

```bash
git clone https://github.com/matthewpara567/pcpulse.git
cd pcpulse
python -m pip install -e ".[dev]"
```

## Checks to run

Run these from the repository root:

```bash
pytest -q
ruff check .
mypy src
```

If a check cannot be run on your operating system, mention that in your pull request rather than claiming it passed.

## Choosing a change

Useful contributions include:

- Fixing incorrect or missing platform metrics.
- Adding tests for operating-system-specific behavior.
- Improving error handling when a metric is unavailable.
- Improving CLI help, examples, and documentation.
- Improving schema validation and compatibility tests.
- Reducing unnecessary permissions, data collection, or dependencies.

Please avoid adding telemetry, cloud requirements, or automatic collection of identifying information. Hostname, username, and process information must remain opt-in.

## Code and test expectations

- Keep pull requests focused; split unrelated changes.
- Add regression tests for bug fixes.
- Add or update tests when behavior changes.
- Preserve cross-platform behavior where possible.
- Treat unavailable hardware and OS metrics as unavailable; do not fabricate values.
- Document public API, CLI, and schema changes.
- Avoid adding dependencies unless they provide clear value.
- Do not include real personal diagnostic output in tests, screenshots, or examples.

## Pull requests

A useful pull request description explains:

1. What problem it solves.
2. What changed and why.
3. Which tests and checks were run, including the operating system and Python version where relevant.
4. Any compatibility, privacy, or schema implications.

Small, reviewable pull requests are easier to assess and merge. Please be respectful and constructive in reviews and discussions.

## Reporting bugs

When reporting a bug, include the PCPulse version, Python version, operating system, expected behavior, actual behavior, and minimal reproduction steps. Remove hostnames, usernames, serial numbers, IP addresses, and other private information from diagnostic output before sharing it.

## Security issues

Do not report security vulnerabilities in public issues. Follow [SECURITY.md](SECURITY.md) for responsible disclosure.
