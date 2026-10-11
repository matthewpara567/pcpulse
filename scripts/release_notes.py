"""Print the CHANGELOG.md section for one version (used by the release workflow)."""

import re
import sys
from pathlib import Path


def extract(changelog: str, version: str) -> str:
    pattern = rf"^## {re.escape(version)}[ \t]*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, changelog, flags=re.MULTILINE | re.DOTALL)
    if match is None or not match.group(1).strip():
        raise SystemExit(f"CHANGELOG.md has no notes for version {version}")
    return match.group(1).strip() + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: release_notes.py VERSION CHANGELOG_PATH")
    version, path = sys.argv[1], Path(sys.argv[2])
    sys.stdout.write(extract(path.read_text(encoding="utf-8"), version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
