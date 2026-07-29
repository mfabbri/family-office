import json
import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from family_office_engine.services.it_es_eu_pension_pro_rata import build_it_es_eu_pension_pro_rata
from family_office_engine.services.spanish_eu_theoretical_pension import (
    build_spanish_eu_theoretical_pension,
    load_spanish_eu_theoretical_rule_pack,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
THEORETICAL_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "spanish-eu-theoretical-pension.json"
PRO_RATA_RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "cross-border" / "eu-pension-coordination-it-es.json"


class SpanishEuTheoreticalPensionTest(unittest.TestCase):
    def test_calculates_theoretical_amount_from_spanish_bases_and_foreign_months(self):
        result = self._build(_pro_rata_input(), _reconciliation(_months("2021-01", 12, "3000.00")))

        self.assertEqual(result["schema_version"], "spanish-eu-theoretical-pension/v1")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["periods"]["spain_months"], 12)
        self.assertEqual(result["periods"]["foreign_eu_months"], 292)
        self.assertEqual(result["base_reguladora"]["selected_base_count"], 302)
        self.assertTrue(
            all(item["basis_source"] != "italian_contribution_base" for item in result["base_reguladora"]["selected_bases"])
        )
        self.assertIn(
            "nearest_spanish_base_updated_by_ipc",
            {item["basis_source"] for item in result["base_reguladora"]["selected_bases"]},
        )

        expected_base = _money(Decimal("3000.00") * Decimal("302") / Decimal("352.33"))
        expected_monthly = _money(Decimal(expected_base) * Decimal("0.7454"))
        expected_annual = _money(Decimal(expected_monthly) * Decimal("14"))
        self.assertEqual(result["base_reguladora"]["amount"], expected_base)
        self.assertEqual(result["accrued_percentage"]["percentage"], "0.7454")
        self.assertEqual(result["spanish_theoretical_pension"]["monthly_gross_amount"], expected_monthly)
        self.assertEqual(result["spanish_theoretical_pension"]["annual_gross_amount"], expected_annual)
        self.assertEqual(result["spanish_theoretical_pension"]["basis"], "spanish_only_bases")

    def test_blocks_when_ipc_for_foreign_months_is_missing(self):
        rule_pack = json.loads(THEORETICAL_RULE_PACK.read_text(encoding="utf-8"))
        rule_pack["ipc_index"]["identity_ranges"] = []
        rule_pack["ipc_index"]["values"] = {"2021-01": "1.000000"}

        result = self._build(
            _pro_rata_input(),
            _reconciliation(_months("2021-01", 12, "3000.00")),
            rule_pack_override=rule_pack,
        )

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("missing_ipc_for_foreign_months", {gap["code"] for gap in result["data_gaps"]})
        self.assertIsNone(result["spanish_theoretical_pension"])

    def test_reports_spanish_month_without_official_base_separately(self):
        payload = _pro_rata_input()
        payload["insurance_periods"][1]["end_date"] = "2022-01-31"

        result = self._build(payload, _reconciliation(_months("2021-01", 12, "3000.00")))

        codes = {gap["code"] for gap in result["data_gaps"]}
        self.assertIn("missing_spanish_official_base_months", codes)
        self.assertNotIn("missing_eu_periods_in_base_window", codes)

    def test_ignores_upstream_missing_theoretical_gap_because_this_service_calculates_it(self):
        payload = _pro_rata_input()
        payload["data_gaps"] = [
            {
                "code": "missing_spanish_theoretical_amount",
                "message": "Spanish theoretical pension from Spanish-only bases must be supplied before pro-rata can be calculated.",
            }
        ]

        result = self._build(payload, _reconciliation(_months("2021-01", 12, "3000.00")))

        self.assertEqual(result["status"], "complete")
        self.assertNotIn("missing_spanish_theoretical_amount", {gap["code"] for gap in result["data_gaps"]})

    def test_blocks_uncovered_retirement_year(self):
        payload = _pro_rata_input()
        payload["retirement_date"] = "2046-01"

        result = self._build(payload, _reconciliation(_months("2021-01", 12, "3000.00")))

        self.assertEqual(result["status"], "blocked_missing_inputs")
        self.assertIn("retirement_date_not_covered_by_rule_pack", {gap["code"] for gap in result["data_gaps"]})

    def test_marks_future_years_as_planning_projection_not_official_law(self):
        payload = _pro_rata_input()
        payload["retirement_date"] = "2027-12"
        payload["insurance_periods"].append(_period("IT", "2026-12-01", "2027-11-30"))

        result = self._build(payload, _reconciliation(_months("2021-01", 12, "3000.00")))

        self.assertEqual(result["rule_pack"]["calculation_mode"], "planning_projection_not_official_future_law")
        self.assertIn("planning_projection_not_official_future_law", {warning["code"] for warning in result["warnings"]})
        self.assertIn("projected_ipc_assumption", {warning["code"] for warning in result["warnings"]})
        self.assertNotIn("synthetic_ipc_index", {warning["code"] for warning in result["warnings"]})

    def test_pro_rata_uses_theoretical_snapshot_without_manual_amount_in_input(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            pro_rata_input_path = root / "it-es-eu-pension-pro-rata-input.json"
            reconciliation_path = root / "spanish-reconciliation.json"
            theoretical_path = root / "spanish-eu-theoretical.snapshot.json"
            pro_rata_output_path = root / "it-es-eu-pension-pro-rata.snapshot.json"
            payload = _pro_rata_input()
            pro_rata_input_path.write_text(json.dumps(payload), encoding="utf-8")
            reconciliation_path.write_text(json.dumps(_reconciliation(_months("2021-01", 12, "3000.00"))), encoding="utf-8")

            theoretical = build_spanish_eu_theoretical_pension(
                pro_rata_input_path,
                reconciliation_path,
                THEORETICAL_RULE_PACK,
                theoretical_path,
            )
            self.assertEqual(theoretical["status"], "complete")

            result = build_it_es_eu_pension_pro_rata(
                pro_rata_input_path,
                PRO_RATA_RULE_PACK,
                pro_rata_output_path,
                spanish_theoretical_snapshot_path=theoretical_path,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["spanish_theoretical_pension"]["source_country"], "ES")
            self.assertEqual(result["spanish_pro_rata_pension"]["status"], "calculated")
            self.assertEqual(result["spanish_pro_rata_pension"]["ratio"]["spain_months"], 12)
            self.assertEqual(result["spanish_pro_rata_pension"]["ratio"]["total_eu_non_overlapping_months"], 304)

    def test_rejects_unofficial_rule_source(self):
        broken = json.loads(THEORETICAL_RULE_PACK.read_text(encoding="utf-8"))
        broken["source_refs"][0]["url"] = "https://example.com/not-official"
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rules.json"
            path.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "official EU, BOE or Seguridad Social URL"):
                load_spanish_eu_theoretical_rule_pack(path)

    def _build(self, payload: dict, reconciliation: dict, rule_pack_override: dict | None = None) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "it-es-eu-pension-pro-rata-input.json"
            reconciliation_path = root / "spanish-reconciliation.json"
            output_path = root / "spanish-eu-theoretical.snapshot.json"
            rule_pack_path = THEORETICAL_RULE_PACK
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            reconciliation_path.write_text(json.dumps(reconciliation), encoding="utf-8")
            if rule_pack_override is not None:
                rule_pack_path = root / "rules.json"
                rule_pack_path.write_text(json.dumps(rule_pack_override), encoding="utf-8")

            result = build_spanish_eu_theoretical_pension(input_path, reconciliation_path, rule_pack_path, output_path)

            self.assertTrue(output_path.exists())
            return result


def _pro_rata_input() -> dict:
    return {
        "schema_version": "it-es-eu-pension-pro-rata-input/v1",
        "scenario": "ordinary",
        "retirement_date": "2026-12",
        "date_of_birth": "1960-01-01",
        "recent_contribution_anchor_date": "2026-12-01",
        "inps_history_status": "complete_dated_history",
        "future_assumptions_status": "explicit",
        "sources": [{"source_id": "synthetic-spanish-eu-theoretical", "type": "synthetic_fixture"}],
        "insurance_periods": [
            _period("IT", "2001-08-01", "2020-12-31"),
            _period("ES", "2021-01-01", "2021-12-31"),
            _period("IT", "2022-01-01", "2026-11-30"),
        ],
    }


def _period(country: str, start: str, end: str) -> dict:
    return {"country": country, "start_date": start, "end_date": end, "period_type": "compulsory", "source_document": f"synthetic-{country.lower()}-periods"}


def _reconciliation(months: list[dict]) -> dict:
    return {
        "schema_version": "spanish-contribution-reconciliation/v1",
        "record_type": "SpanishContributionReconciliationSnapshot",
        "status": "complete",
        "summary": {"covered_month_count": len(months), "usable_month_count": len(months), "data_gap_count": 0, "anomaly_count": 0},
        "months": months,
        "data_gaps": [],
        "anomalies": [],
    }


def _months(start_month: str, count: int, amount: str) -> list[dict]:
    start_year, start_month_number = (int(part) for part in start_month.split("-"))
    months: list[dict] = []
    for offset in range(count):
        index = start_year * 12 + start_month_number - 1 + offset
        month_key = f"{index // 12:04d}-{index % 12 + 1:02d}"
        months.append(
            {
                "month": month_key,
                "covered_by_vida_laboral": True,
                "periods": [{"source_document": "synthetic-vida-laboral.txt"}],
                "official_bases": [{"base_amount": amount, "source_document": "synthetic-bases.csv"}],
                "payroll_bases": [],
                "selected_base": {
                    "month": month_key,
                    "base_amount": amount,
                    "currency": "EUR",
                    "source_type": "official_bases",
                    "confidence": "high",
                    "source_documents": ["synthetic-bases.csv"],
                    "component_count": 1,
                },
                "usable_for_estimator": True,
                "data_gap_codes": [],
                "anomaly_codes": [],
            }
        )
    return months


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


if __name__ == "__main__":
    unittest.main()
