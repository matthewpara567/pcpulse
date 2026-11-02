# Changelog

## 0.3.0

- Make collectors best-effort and include structured collection errors.
- Add GPU telemetry using NVIDIA tooling and Linux DRM sysfs where available.
- Add optional SMART storage health probing through smartctl.
- Add battery capacity and health metadata where Linux sysfs exposes energy values.
- Add CPU, system, and motherboard inventory metadata.
- Add network throughput and disk I/O sampling.
- Improve terminal output with disk free/total, uptime, GPU and throughput information.
- Escape system-provided values in Markdown reports.
- Validate health thresholds and use sensor-reported temperature limits when sane.
- Add JSON Schema export and ZIP diagnostic report bundles.
- Require PyPI publishing before creating a GitHub Release.
- Add snapshot schema 1.2.

## 0.2.0

- Add snapshot schema 1.1 and swap, battery, network, temperatures, fans, and optional processes.
- Add configurable doctor thresholds and snapshot output/watch options.
