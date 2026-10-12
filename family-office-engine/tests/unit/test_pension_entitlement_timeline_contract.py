import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/pension-entitlement-timeline.schema.json"
EVENT_NAMES = (
    "eligibility_date",
    "requirements_met_date",
    "official_recognition_date",
    "economic_effective_date",
    "first_cash_payment_date",
)


def event(status="not_assessed", value=None, refs=None, gaps=None):
    return {
        "status": status,
        "date": value,
        "source_refs": refs or [],
        "data_gaps": gaps or ([{"code": "not_approved", "message": "No supported rule for this event."}] if status == "not_assessed" else []),
    }


def snapshot():
    return {
        "schema_version": "pension-entitlement-timeline/v1",
        "record_type": "PensionEntitlementTimeline",
        "status": "not_assessed",
        "member_id": "synthetic-member",
        "as_of_date": "2026-10-11",
        "events": {name: event() for name in EVENT_NAMES},
        "data_gaps": [{"code": "timeline_not_approved", "message": "The full timeline remains blocked pending independent normative approval."}],
        "limitations": ["Contract only; no date, amount, stream or payment is inferred."],
    }


class PensionEntitlementTimelineContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def test_all_five_events_can_fail_closed_as_null_with_explicit_gaps(self):
        self.validator.validate(snapshot())

    def test_supported_events_need_source_refs_and_distinct_dates_are_not_collapsed(self):
        value = snapshot()
        value["status"] = "partial"
        value["events"]["eligibility_date"] = event("supported", "2026-01-01", ["official-source-1"])
        value["events"]["requirements_met_date"] = event("supported", "2026-02-01", ["verified-record-2"])
        value["events"]["official_recognition_date"] = event()
        self.validator.validate(value)
        value["events"]["economic_effective_date"] = event("supported", "2026-03-01")
        with self.assertRaises(ValidationError):
            self.validator.validate(value)

    def test_unknown_event_cannot_emit_a_date_or_omit_its_gap(self):
        value = snapshot()
        value["events"]["first_cash_payment_date"] = event("not_assessed", "2026-04-01")
        with self.assertRaises(ValidationError):
            self.validator.validate(value)


if __name__ == "__main__":
    unittest.main()
