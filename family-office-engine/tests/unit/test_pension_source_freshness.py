import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from family_office_engine.governance.pension_source_freshness import (
    MAX_REVIEW_INTERVAL_DAYS,
    PensionSourceFreshnessError,
    audit_active_pension_rule_packs,
    audit_pension_rule_pack,
    record_pension_source_review,
    require_fresh_pension_rule_pack,
)


class PensionSourceFreshnessTest(unittest.TestCase):
    def test_fresh_sources_report_legal_validity_separately_and_never_check_network(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_root = Path(temp_dir)
            relative = Path("cross-border/eu-pack.json")
            pack_path = rules_root / relative
            pack_path.parent.mkdir(parents=True)
            pack_path.write_text(json.dumps(_pack()), encoding="utf-8")

            report = audit_active_pension_rule_packs(rules_root, "2026-10-11", [relative])

        self.assertEqual(report["status"], "fresh")
        self.assertFalse(report["network_checked"])
        self.assertEqual(report["rule_packs"][0]["legal_validity"], {
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
        })
        self.assertEqual(report["rule_packs"][0]["sources"][0]["status"], "fresh")

    def test_due_date_is_usable_on_the_due_day_but_overdue_after_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rules.json"
            path.write_text(json.dumps(_pack()), encoding="utf-8")

            due_day = audit_pension_rule_pack(path, "2027-01-09")
            overdue = audit_pension_rule_pack(path, "2027-01-10")

        self.assertEqual(due_day["status"], "fresh")
        self.assertEqual(overdue["status"], "blocked")
        self.assertIn("normative_source_review_overdue", {gap["code"] for gap in overdue["data_gaps"]})

    def test_missing_provenance_and_review_metadata_fail_closed(self):
        pack = _pack()
        del pack["source_refs"][0]["authority"]
        del pack["source_refs"][0]["next_review_due"]

        report = self._audit(pack, "2026-10-11")

        self.assertEqual(report["status"], "blocked")
        self.assertIn("normative_source_provenance_missing", {gap["code"] for gap in report["data_gaps"]})

    def test_invalid_and_future_review_dates_fail_closed(self):
        invalid = _pack()
        invalid["source_refs"][0]["reviewed_on"] = "11/10/2026"
        future = _pack()
        future["source_refs"][0]["reviewed_on"] = "2026-10-12"
        future["source_refs"][0]["next_review_due"] = "2027-01-10"

        invalid_report = self._audit(invalid, "2026-10-11")
        future_report = self._audit(future, "2026-10-11")

        self.assertIn("normative_source_review_metadata_invalid", {gap["code"] for gap in invalid_report["data_gaps"]})
        self.assertIn("normative_source_review_metadata_invalid", {gap["code"] for gap in future_report["data_gaps"]})

    def test_review_interval_cannot_exceed_ninety_days(self):
        pack = _pack()
        pack["source_refs"][0]["next_review_due"] = "2027-01-10"

        report = self._audit(pack, "2026-10-11")

        self.assertEqual(MAX_REVIEW_INTERVAL_DAYS, 90)
        self.assertIn("normative_source_review_metadata_invalid", {gap["code"] for gap in report["data_gaps"]})

    def test_review_due_date_must_be_after_review_date(self):
        pack = _pack()
        pack["source_refs"][0]["next_review_due"] = pack["source_refs"][0]["reviewed_on"]

        report = self._audit(pack, "2026-10-11")

        self.assertIn("normative_source_review_metadata_invalid", {gap["code"] for gap in report["data_gaps"]})

    def test_non_official_or_non_https_sources_are_blocked(self):
        pack = _pack()
        pack["source_refs"][0]["url"] = "http://example.test/rule"

        report = self._audit(pack, "2026-10-11")

        self.assertIn("normative_source_provenance_missing", {gap["code"] for gap in report["data_gaps"]})

    def test_consumer_assertion_raises_on_overdue_rule_pack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rules.json"
            pack = _pack()
            pack["source_refs"][0]["next_review_due"] = "2026-10-10"
            path.write_text(json.dumps(pack), encoding="utf-8")

            with self.assertRaisesRegex(PensionSourceFreshnessError, "normative_source_review_overdue"):
                require_fresh_pension_rule_pack(path, "2026-10-11")

    def test_guided_review_writer_updates_only_freshness_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rules.json"
            pack = _pack()
            path.write_text(json.dumps(pack), encoding="utf-8")

            result = record_pension_source_review(path, "official.test.rule", "2026-10-11")
            updated = json.loads(path.read_text(encoding="utf-8"))

        source = updated["source_refs"][0]
        self.assertEqual(result["next_review_due"], "2027-01-09")
        self.assertEqual(source["retrieved_on"], "2026-07-29")
        self.assertEqual(source["reviewed_on"], "2026-10-11")
        self.assertEqual(source["next_review_due"], "2027-01-09")
        self.assertEqual(updated["valid_to"], "2026-12-31")

    def test_guided_review_writer_rejects_unofficial_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rules.json"
            pack = _pack()
            pack["source_refs"][0]["url"] = "https://example.test/rule"
            path.write_text(json.dumps(pack), encoding="utf-8")

            with self.assertRaisesRegex(PensionSourceFreshnessError, "non-official HTTPS source"):
                record_pension_source_review(path, "official.test.rule", "2026-10-11")

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), pack)

    def test_all_active_packs_are_auditable_without_network(self):
        repository_root = Path(__file__).resolve().parents[3]
        rules_root = repository_root / "family-office-rules"

        report = audit_active_pension_rule_packs(rules_root, date(2026, 10, 11))

        self.assertEqual(report["status"], "fresh", report["data_gaps"])
        self.assertFalse(report["network_checked"])
        self.assertEqual(len(report["rule_packs"]), 5)

    def _audit(self, pack: dict, as_of: str) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rules.json"
            path.write_text(json.dumps(pack), encoding="utf-8")
            return audit_pension_rule_pack(path, as_of)


def _pack() -> dict:
    return {
        "schema_version": "test-pension-rule-pack/v1",
        "rule_pack_id": "test.pension.v1",
        "jurisdiction": "EU",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31",
        "source_refs": [{
            "source_id": "official.test.rule",
            "title": "Official pension source",
            "authority": "Official Authority",
            "jurisdiction": "EU",
            "url": "https://eur-lex.europa.eu/test",
            "provisions": ["Article 52"],
            "retrieved_on": "2026-07-29",
            "reviewed_on": "2026-10-11",
            "next_review_due": "2027-01-09",
        }],
    }


if __name__ == "__main__":
    unittest.main()
