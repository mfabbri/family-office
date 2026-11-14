import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULE_PACK = REPOSITORY_ROOT / "family-office-rules" / "spain" / "statutory-retirement-general.json"
BRANCHES = ("3.2.a", "3.2.b", "3.2.c", "3.2.d", "3.2.e")


def wizard_answers(
    *,
    as_of="",
    filing_conflict="non-conflicting",
    article_3_2=None,
    article_3_2_conflicts=None,
    article_3_3=True,
    article_3_3_conflict="non-conflicting",
    eu_status="none",
):
    answers = [
        as_of,
        "2026-10-20",
        "2026-10-20",
        "yes",  # actual application
        "yes",  # domestic Spanish filing
        "synthetic:filing",
        "synthetic:filing-scope",
        filing_conflict,
        "yes",  # ordinary RG scope documented
        "synthetic:ordinary-rg",
    ]
    for branch in BRANCHES:
        not_applicable = True if article_3_2 is None else article_3_2.get(branch, True)
        conflicts = {} if article_3_2_conflicts is None else article_3_2_conflicts
        conflict_status = conflicts.get(branch, "non-conflicting")
        answers.extend(("yes" if not_applicable else "no", conflict_status, f"synthetic:exclude-{branch}"))
    answers.extend(
        (
            "yes" if article_3_3 else "no",
            article_3_3_conflict,
            "synthetic:exclude-3.3",
            eu_status,
        )
    )
    if eu_status == "none":
        answers.append("synthetic:no-eu-periods")
    return answers


class SpanishOrdinaryRgDailyContractCliTests(unittest.TestCase):
    def run_wizard(self, answers):
        output = io.StringIO()
        args = ["pension-es-evidence", "--rule-pack", str(RULE_PACK)]
        rule_pack = json.loads(RULE_PACK.read_text(encoding="utf-8"))
        with (
            patch("builtins.input", side_effect=answers),
            patch("family_office_engine.cli.main.load_rule_pack", return_value=rule_pack),
            patch.object(Path, "write_text", side_effect=AssertionError("report-only command must not write files")),
            contextlib.redirect_stdout(output),
        ):
            status = main(args)
        return status, output.getvalue()

    def test_complete_synthetic_evidence_reports_completeness_only_and_writes_nothing(self):
        status, output = self.run_wizard(wizard_answers())

        self.assertEqual(status, 0)
        self.assertIn("Question: Is the evidence for this documented ordinary Spanish RG application complete", output)
        self.assertIn("evidence contract complete: yes", output)
        self.assertIn("assumptions:", output)
        self.assertIn("human-review flag: required", output)
        for field in (
            "eligibility",
            "legal_status",
            "contribution_obligation",
            "lgss_205_1_b_anchor",
            "recognition",
            "economic_effect",
            "payment",
            "hecho_causante",
        ):
            self.assertIn(f"{field}: not_assessed", output)
        self.assertIn("not an eligibility", output)

    def test_missing_or_conflicting_article_3_exclusions_fail_closed(self):
        cases = (
            (wizard_answers(article_3_2={"3.2.a": False}), "article_3_2_a_evidence_unknown"),
            (wizard_answers(article_3_3=False), "article_3_3_evidence_unknown"),
        )
        for answers, gap_code in cases:
            with self.subTest(gap=gap_code):
                status, output = self.run_wizard(answers)
                self.assertEqual(status, 2)
                self.assertIn("evidence contract complete: no", output)
                self.assertIn(gap_code, output)
                self.assertIn("eligibility: not_assessed", output)

    def test_explicit_conflicting_and_unknown_conflict_statuses_fail_closed(self):
        filing_cases = (
            ("conflicting", "authoritative_filing_evidence_conflicting"),
            ("unknown", "authoritative_filing_conflict_status_unknown"),
        )
        for status_value, gap_code in filing_cases:
            with self.subTest(source="filing", status=status_value):
                status, output = self.run_wizard(wizard_answers(filing_conflict=status_value))
                self.assertEqual(status, 2)
                self.assertIn(gap_code, output)

        for branch in BRANCHES:
            for status_value in ("conflicting", "unknown"):
                gap_code = f"article_{branch.replace('.', '_')}_evidence_conflicting"
                with self.subTest(source=f"article_{branch}", status=status_value):
                    status, output = self.run_wizard(
                        wizard_answers(article_3_2_conflicts={branch: status_value})
                    )
                    self.assertEqual(status, 2)
                    self.assertIn(gap_code, output)

        article_3_3_cases = (
            ("conflicting", "article_3_3_evidence_conflicting"),
            ("unknown", "article_3_3_evidence_conflicting"),
        )
        for status_value, gap_code in article_3_3_cases:
            with self.subTest(source="article_3_3", status=status_value):
                status, output = self.run_wizard(
                    wizard_answers(article_3_3_conflict=status_value)
                )
                self.assertEqual(status, 2)
                self.assertIn(gap_code, output)

    def test_blank_and_invalid_conflict_answers_remain_unknown(self):
        blank_answers = wizard_answers(filing_conflict="")
        invalid_then_unknown_answers = wizard_answers()
        invalid_then_unknown_answers[7] = "not-a-conflict-status"
        invalid_then_unknown_answers.insert(8, "unknown")

        for label, answers in (
            ("blank", blank_answers),
            ("invalid_then_unknown", invalid_then_unknown_answers),
        ):
            with self.subTest(answer=label):
                status, output = self.run_wizard(answers)
                self.assertEqual(status, 2)
                self.assertIn("authoritative_filing_conflict_status_unknown", output)
                self.assertNotIn("authoritative_filing_evidence_conflicting", output)
                if label == "invalid_then_unknown":
                    self.assertIn("Value not recognized", output)

    def test_eu_unknown_or_present_is_outside_the_contract(self):
        cases = (
            ("unknown", "eu_periods_unknown"),
            ("present", "eu_coordination_out_of_scope"),
        )
        for eu_status, gap_code in cases:
            with self.subTest(eu_status=eu_status):
                status, output = self.run_wizard(wizard_answers(eu_status=eu_status))
                self.assertEqual(status, 2)
                self.assertIn(gap_code, output)
                self.assertIn("payment: not_assessed", output)

    def test_as_of_before_source_review_cutoff_fails_closed(self):
        cases = (
            ("2026-11-13", 2, "contract_source_evidence_cutoff_gap"),
            ("2026-11-14", 0, "evidence contract complete: yes"),
            ("2026-11-15", 2, "contract_currentness_gap"),
        )
        for assessment_date, expected_status, expected_output in cases:
            with self.subTest(as_of=assessment_date):
                status, output = self.run_wizard(wizard_answers(as_of=assessment_date))
                self.assertEqual(status, expected_status)
                self.assertIn(expected_output, output)
                self.assertIn("recognition: not_assessed", output)

    def test_interruption_returns_without_a_pension_conclusion(self):
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=EOFError),
            contextlib.redirect_stdout(output),
        ):
            status = main(["pension-es-evidence", "--rule-pack", str(RULE_PACK)])

        self.assertEqual(status, 2)
        self.assertIn("interrupted; no pension conclusion was produced", output.getvalue())
        self.assertNotIn("eligibility:", output.getvalue())

    def test_mid_wizard_interruption_returns_without_a_pension_conclusion(self):
        output = io.StringIO()
        with (
            patch("builtins.input", side_effect=("", "2026-10-20", EOFError)),
            contextlib.redirect_stdout(output),
        ):
            status = main(["pension-es-evidence", "--rule-pack", str(RULE_PACK)])

        self.assertEqual(status, 2)
        self.assertIn("interrupted; no pension conclusion was produced", output.getvalue())
        self.assertNotIn("eligibility:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
