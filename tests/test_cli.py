import sys

from pcpulse.cli import main


def test_schema_command(capsys):
    old=sys.argv
    try:
        sys.argv=["pcpulse","schema"]
        assert main()==0
        assert capsys.readouterr().out.strip()=="1.0"
    finally: sys.argv=old
