# Platform support

PCPulse uses `psutil` to collect operating-system and hardware information. It is designed to run on Windows, macOS, and Linux, but the availability and detail of individual metrics depend on the operating system, permissions, hardware, and Python environment.

## Automated test matrix

The repository's GitHub Actions CI workflow currently tests these combinations on GitHub-hosted runners:

| Operating system | Python versions |
| --- | --- |
| Ubuntu | 3.10, 3.11, 3.12, 3.13, 3.14 |
| Windows | 3.10, 3.11, 3.12, 3.13, 3.14 |
| macOS | 3.10, 3.11, 3.12, 3.13, 3.14 |

This is the automated test matrix, not a guarantee that every hardware metric is available on every version or machine. Runner images can change over time.

## Metric availability

| Metric | Notes |
| --- | --- |
| CPU, memory, uptime, OS, architecture | Core snapshot information; values are provided by the host OS and `psutil`. |
| Disk usage | Depends on mounted filesystems and access permissions. Some pseudo, optical, or empty filesystems are intentionally skipped. |
| Swap | May be unavailable or report zero when the host does not expose swap. |
| Battery | Only available on systems where the OS reports a battery. |
| Network | Interface names and byte counters only; IP and MAC addresses are not collected. |
| Temperatures and fans | Hardware- and OS-dependent; many systems expose neither through the available interfaces. |
| Top processes | Collected only when explicitly requested because process names can be sensitive. |

PCPulse should represent unavailable metrics as unavailable rather than guessing or substituting invented values.

## Reporting compatibility problems

When reporting a platform issue, include:

- PCPulse version (`pcpulse --version`)
- Python version
- Operating system and version
- The affected metric or command
- A minimal reproduction and sanitized error output

Remove hostnames, usernames, serial numbers, IP addresses, and other identifying information before sharing diagnostic output. See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md).
