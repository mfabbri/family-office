import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.spanish_pension_rules import (
    SpanishPensionRulesError,
    accrued_pension_percentage,
    base_reguladora_parameters,
    load_rule_pack,
    ordinary_retirement_age,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPAIN_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "spain" / "statutory-retirement-general.json"


class SpanishPensionRulesTest(unittest.TestCase):
    def test_loads_official_baseline_rule_pack(self):
        rule_pack = load_rule_pack(SPAIN_RULE_PACK)

        self.assertEqual(rule_pack["schema_version"], "spanish-statutory-pension-rule-pack/v1")
        self.assertEqual(rule_pack["jurisdiction"], "ES")
        self.assertEqual(rule_pack["source_refs"][0]["source_id"], "boe.lgss.rdl-8-2015.consolidated")
        self.assertIn("Ordinary retirement only", rule_pack["limitations"][1])

    def test_rejects_rule_pack_without_official_source(self):
        broken = _load_fixture()
        broken["source_refs"] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_pack_path = Path(tmp_dir) / "spanish-rules.json"
            rule_pack_path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(SpanishPensionRulesError, "source_ref"):
                load_rule_pack(rule_pack_path)

    def test_ordinary_retirement_age_uses_2026_transition(self):
        rule_pack = load_rule_pack(SPAIN_RULE_PACK)

        early_age = ordinary_retirement_age(rule_pack, 2026, contribution_months=459)
        standard_age = ordinary_retirement_age(rule_pack, 2026, contribution_months=458)

        self.assertEqual(early_age["age"], {"years": 65, "months": 0})
        self.assertEqual(standard_age["age"], {"years": 66, "months": 10})
        self.assertEqual(early_age["matched_rule"]["source_provision"], "Disposicion transitoria septima")

    def test_base_reguladora_parameters_uses_2026_transition(self):
        rule_pack = load_rule_pack(SPAIN_RULE_PACK)

        params = base_reguladora_parameters(rule_pack, 2026)

        self.assertEqual(params["lookback_months"], 304)
        self.assertEqual(params["selected_highest_bases"], 302)
        self.assertEqual(params["divisor"], "352.33")

    def test_accrued_pension_percentage_uses_first_15_years_floor(self):
        rule_pack = load_rule_pack(SPAIN_RULE_PACK)

        result = accrued_pension_percentage(rule_pack, 2026, contribution_months=180)

        self.assertEqual(result["percentage"], "0.5")
        self.assertEqual(result["additional_months"], 0)
        self.assertEqual(result["applied_segments"], [])

    def test_accrued_pension_percentage_uses_2026_transition(self):
        rule_pack = load_rule_pack(SPAIN_RULE_PACK)

        result = accrued_pension_percentage(rule_pack, 2026, contribution_months=300)

        self.assertEqual(result["percentage"], "0.7378")
        self.assertEqual(result["additional_months"], 120)
        self.assertEqual(result["applied_segments"][0]["applied_months"], 49)
        self.assertEqual(result["applied_segments"][0]["monthly_rate"], "0.0021")
        self.assertEqual(result["applied_segments"][1]["applied_months"], 71)
        self.assertEqual(result["applied_segments"][1]["monthly_rate"], "0.0019")

    def test_accrued_pension_percentage_caps_2027_schedule_at_100_percent(self):
        rule_pack = load_rule_pack(SPAIN_RULE_PACK)

        result = accrued_pension_percentage(rule_pack, 2027, contribution_months=600)

        self.assertEqual(result["percentage"], "1")
        self.assertEqual(result["applied_segments"][0]["applied_months"], 248)
        self.assertEqual(result["applied_segments"][1]["applied_months"], 16)

    def test_rejects_deferred_percentage_schedule(self):
        broken = _load_fixture()
        broken["pension_percentage"].pop("additional_month_schedule")
        broken["pension_percentage"]["additional_month_schedule_status"] = "deferred_pending_full_estimator_rule_pack"
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_pack_path = Path(tmp_dir) / "spanish-rules.json"
            rule_pack_path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(SpanishPensionRulesError, "additional_month_schedule"):
                load_rule_pack(rule_pack_path)

    def test_rejects_rule_pack_without_required_limitations(self):
        broken = _load_fixture()
        broken["limitations"] = ["Too short"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            rule_pack_path = Path(tmp_dir) / "spanish-rules.json"
            rule_pack_path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(SpanishPensionRulesError, "limitations"):
                load_rule_pack(rule_pack_path)


def _load_fixture() -> dict:
    return json.loads(SPAIN_RULE_PACK.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
