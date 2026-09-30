import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pcpulse import collect_snapshot

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "snapshot-1.0.schema.json"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_snapshot_matches_schema():
    _validator().validate(collect_snapshot().to_dict())


def test_snapshot_with_identity_matches_schema():
    _validator().validate(collect_snapshot(include_identity=True).to_dict())
