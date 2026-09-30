import sys
from importlib.metadata import version as distribution_version

import pcpulse

from pcpulse.cli import main


def test_schema_command(capsys):
    old = sys.argv
    try:
        sys.argv = ["pcpulse", "schema"]
        assert main() == 0
        assert capsys.readouterr().out.strip() == "1.0"
    finally:
        sys.argv = old


def test_version_matches_distribution():
    assert pcpulse.__version__ == distribution_version("pcpulse")
