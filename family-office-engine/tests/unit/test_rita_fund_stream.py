import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.rita_fund_stream import build_rita_fund_stream


class RitaFundStreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "fund.txt").write_text("synthetic fund evidence", encoding="utf-8")
        self.data = {"as_of": "2026-10-20", "observations": []}
        self.add("benefit_type", "rita")

    def add(self, field, value, **changes):
        item = {"field": field, "value": value, "source_ref": "fund.txt", "issuer": "Synthetic fund",
                "coverage_start": "2026-01-01", "coverage_end": "2026-12-31", "basis": "attested",
                "sha256": hashlib.sha256((self.root / "fund.txt").read_bytes()).hexdigest()}
        item.update(changes)
        self.data["observations"].append(item)

    def build(self):
        return build_rita_fund_stream(self.data, self.root)

    def test_request_does_not_imply_acceptance_or_payment(self):
        self.add("request_date", "2026-02-01")
        self.add("gross_amount", "120.00")
        result = self.build()
        self.assertEqual(result["facts"]["request_date"], "2026-02-01")
        self.assertIsNone(result["facts"]["acceptance_date"])
        self.assertIsNone(result["facts"]["actual_payments"])
        self.assertIsNone(result["net_amount"])
        self.assertIn("missing_fact", {gap["code"] for gap in result["data_gaps"]})

    def test_missing_evidence_bad_coverage_and_estimates_fail_closed(self):
        self.add("fund", "Example", source_ref="absent.txt")
        self.add("frequency", "monthly", issuer="")
        self.add("gross_amount", "100", basis="estimated")
        self.add("acceptance_date", "2026-05-01", coverage_end="2026-09-01")
        result = self.build()
        for name in ("fund", "frequency", "gross_amount", "acceptance_date"):
            self.assertIsNone(result["facts"][name])
        self.assertEqual(sum(g["code"] == "unusable_evidence" for g in result["data_gaps"]), 4)

    def test_conflicts_preserve_provenance_but_not_value(self):
        self.add("gross_amount", "100")
        self.add("gross_amount", "200")
        result = self.build()
        self.assertIsNone(result["facts"]["gross_amount"])
        self.assertEqual(len(result["provenance"]["gross_amount"]), 2)
        self.assertIn("conflicting_or_unusable_fact", {g["code"] for g in result["data_gaps"]})

    def test_schedule_and_actual_payment_remain_separate(self):
        self.add("request_date", "2026-01-01")
        self.add("acceptance_date", "2026-02-01")
        self.add("scheduled_start", "2026-03-01")
        self.add("scheduled_end", "2026-12-01")
        self.add("actual_payments", [{"date": "2026-03-05", "gross_amount": "100.00"}])
        result = self.build()
        self.assertEqual(result["facts"]["scheduled_start"], "2026-03-01")
        self.assertEqual(result["facts"]["actual_payments"][0]["date"], "2026-03-05")
        self.assertIsNone(result["net_amount"])
        self.assertEqual(len(result["provenance"]["acceptance_date"][0]["sha256"]), 64)

    def test_inconsistent_dates_and_payment_are_not_promoted(self):
        self.add("acceptance_date", "2026-04-01")
        self.add("scheduled_start", "2026-03-01")
        self.add("actual_payments", [{"date": "2026-11-01", "gross_amount": "1"}])
        result = self.build()
        self.assertIsNone(result["facts"]["acceptance_date"])
        self.assertIsNone(result["facts"]["scheduled_start"])
        self.assertIsNone(result["facts"]["actual_payments"])
        self.assertIn("conflicting_dates", {g["code"] for g in result["data_gaps"]})

    def test_source_must_be_inside_workspace(self):
        self.add("fund", "Example", source_ref="../outside.txt")
        self.assertIsNone(self.build()["facts"]["fund"])

    def test_non_rita_benefit_is_excluded(self):
        self.data["observations"].clear()
        self.add("benefit_type", "other")
        self.add("acceptance_date", "2026-03-01")
        result = self.build()
        self.assertIsNone(result["facts"]["benefit_type"])
        self.assertIsNone(result["facts"]["acceptance_date"])
        self.assertEqual(result["stream_availability"], "unavailable_or_not_assessable")
        self.assertIn("non_rita_benefit_excluded", {g["code"] for g in result["data_gaps"]})

    def test_unattested_benefit_suppresses_all_other_facts(self):
        for kind in ("missing", "estimated", "conflicting"):
            with self.subTest(kind=kind):
                self.data["observations"].clear()
                if kind == "estimated":
                    self.add("benefit_type", "rita", basis="estimated")
                if kind == "conflicting":
                    self.add("benefit_type", "rita")
                    self.add("benefit_type", "other")
                self.add("acceptance_date", "2026-03-01")
                self.add("gross_amount", "100")
                self.add("actual_payments", [{"date": "2026-04-01", "gross_amount": "100"}])
                result = self.build()
                self.assertTrue(all(value is None for value in result["facts"].values()))
                self.assertEqual(result["stream_availability"], "unavailable_or_not_assessable")
                self.assertIn("rita_benefit_not_attested", {g["code"] for g in result["data_gaps"]})

    def test_source_mutation_requires_fresh_transcription(self):
        self.add("acceptance_date", "2026-03-01")
        self.assertEqual(self.build()["facts"]["acceptance_date"], "2026-03-01")
        (self.root / "fund.txt").write_text("changed synthetic evidence", encoding="utf-8")
        result = self.build()
        self.assertIsNone(result["facts"]["acceptance_date"])
        self.assertIn("source_digest_mismatch", {g["code"] for g in result["data_gaps"]})
        self.data["observations"].clear()
        self.add("benefit_type", "rita")
        self.add("acceptance_date", "2026-03-01")
        self.assertEqual(self.build()["facts"]["acceptance_date"], "2026-03-01")

    def test_source_mutation_during_validation_is_fail_closed(self):
        self.add("acceptance_date", "2026-03-01")
        source = self.root / "fund.txt"
        original_read_bytes = Path.read_bytes
        reads = 0

        def mutate_after_snapshot(path):
            nonlocal reads
            content = original_read_bytes(path)
            if path == source and reads == 0:
                reads += 1
                source.write_text("changed synthetic evidence", encoding="utf-8")
            return content

        with patch("family_office_engine.services.rita_fund_stream.Path.read_bytes", new=mutate_after_snapshot):
            result = self.build()
        self.assertIsNone(result["facts"]["acceptance_date"])
        self.assertIn("source_changed_during_validation", {gap["code"] for gap in result["data_gaps"]})

    def test_overlapping_date_and_payment_conflicts_are_reported(self):
        self.add("request_date", "2026-05-01")
        self.add("acceptance_date", "2026-04-01")
        self.add("actual_payments", [{"date": "2026-03-01", "gross_amount": "100"}])
        result = self.build()
        self.assertTrue(all(result["facts"][field] is None for field in
                            ("request_date", "acceptance_date", "actual_payments")))
        self.assertTrue({"conflicting_dates", "payment_before_acceptance"} <=
                        {g["code"] for g in result["data_gaps"]})

    def test_non_adjacent_dates_conflict_when_intermediate_dates_are_missing(self):
        self.add("request_date", "2026-06-01")
        self.add("scheduled_end", "2026-05-01")
        result = self.build()
        self.assertIsNone(result["facts"]["request_date"])
        self.assertIsNone(result["facts"]["scheduled_end"])
        self.assertIn({"code": "conflicting_dates", "fields": ["request_date", "scheduled_end"]},
                      result["data_gaps"])

    def test_amount_frequency_coverage_and_duplicate_payments(self):
        self.add("gross_amount", "-1")
        self.add("frequency", "not a cadence")
        self.add("request_date", "2025-12-31")
        self.add("actual_payments", [{"date": "2026-03-01", "gross_amount": "100"},
                                     {"date": "2026-03-01", "gross_amount": "200"}])
        result = self.build()
        for field in ("gross_amount", "frequency", "request_date", "actual_payments"):
            self.assertIsNone(result["facts"][field])

    def test_public_wizard_records_evidence_and_gaps(self):
        answers = iter(["2026-10-20", "Example", "fund.txt", "Synthetic fund", "2026-01-01",
                        "2026-12-31", "attested"] + [""] * 12)
        with patch("family_office_engine.cli.main.resolve_repo", return_value=self.root), \
             patch("builtins.input", side_effect=lambda _prompt: next(answers)), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            code = main(["rita-stream"])
        self.assertEqual(code, 0)
        self.assertIn("Quale flusso RITA", out.getvalue())
        self.assertIn("Prossima azione", out.getvalue())
        snapshot = json.loads((self.root / "snapshots/rita-fund-stream.snapshot.json").read_text(encoding="utf-8"))
        self.assertIsNone(snapshot["facts"]["fund"])
        self.assertEqual(snapshot["provenance"]["fund"][0]["sha256"],
                         hashlib.sha256((self.root / "fund.txt").read_bytes()).hexdigest())
        self.assertIsNone(snapshot["facts"]["acceptance_date"])
        self.assertTrue((self.root / "planning/rita-fund-stream.draft.json").exists())

    def test_public_wizard_saves_progress_on_interruption(self):
        answers = iter(["2026-10-20", "Example", "fund.txt"])
        def answer(_prompt):
            return next(answers, None) if answers is not None else None
        def interrupted(prompt):
            value = answer(prompt)
            if value is None:
                raise EOFError
            return value
        with patch("family_office_engine.cli.main.resolve_repo", return_value=self.root), \
             patch("builtins.input", side_effect=interrupted), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["rita-stream"]), 1)
        draft = json.loads((self.root / "planning/rita-fund-stream.draft.json").read_text(encoding="utf-8"))
        self.assertEqual(draft["pending"]["fund"]["source_ref"], "fund.txt")

    def test_public_wizard_resumes_invalid_as_of_draft(self):
        with patch("family_office_engine.cli.main.resolve_repo", return_value=self.root), \
             patch("builtins.input", side_effect=["not-a-date", EOFError]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["rita-stream"]), 1)
        draft_path = self.root / "planning/rita-fund-stream.draft.json"
        self.assertEqual(json.loads(draft_path.read_text(encoding="utf-8"))["as_of"], "not-a-date")
        with patch("family_office_engine.cli.main.resolve_repo", return_value=self.root), \
             patch("builtins.input", side_effect=["2026-10-20"] + [""] * 13), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["rita-stream"]), 0)
        snapshot = json.loads((self.root / "snapshots/rita-fund-stream.snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["as_of"], "2026-10-20")


if __name__ == "__main__":
    unittest.main()
