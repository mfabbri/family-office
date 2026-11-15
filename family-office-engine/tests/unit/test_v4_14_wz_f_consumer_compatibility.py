import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import family_office_engine.services.it_es_eu_pension_pro_rata as pro_rata
import family_office_engine.services.eu_pension_coordination as coordination
from family_office_engine.services.it_es_eu_pension_pro_rata import (
    ItEsEuPensionProRataError,
    build_it_es_eu_pension_pro_rata,
    load_rule_pack,
)
from family_office_engine.services.eu_pension_coordination import (
    EuPensionCoordinationError,
    coordinate_it_es_pensions,
    load_rule_pack as load_coordination_rule_pack,
)
from family_office_engine.services.pension_income import compose_pension_income
from family_office_engine.services.pension_timeline_source_gate import PACK_REGISTRY


ROOT = Path(__file__).resolve().parents[3]
RULES = ROOT / "family-office-rules" / "cross-border"


class EuConsumerCompatibilityTests(unittest.TestCase):
    def test_candidate_packs_load_only_with_pinned_identity_digest_and_period(self):
        for pack_id, spec in PACK_REGISTRY.items():
            with self.subTest(pack_id=pack_id):
                path = RULES / spec["path"]
                pack = load_rule_pack(path)
                self.assertEqual(pack["rule_pack_id"], pack_id)
                self.assertEqual(pack["pro_rata_method"]["article_57_source_bound"]["contract_schema_version"], "v0.29")
                coordinated_pack = load_coordination_rule_pack(path)
                self.assertEqual(coordinated_pack["rule_pack_id"], pack_id)
                with patch.object(pro_rata, "_file_sha256", return_value="0" * 64):
                    with self.assertRaisesRegex(ItEsEuPensionProRataError, "digest"):
                        load_rule_pack(path)
                with patch.object(coordination.hashlib, "sha256", return_value=type("Digest", (), {"hexdigest": lambda self: "0" * 64})()):
                    with self.assertRaisesRegex(EuPensionCoordinationError, "digest"):
                        load_coordination_rule_pack(path)

    def test_period_drift_is_rejected_by_both_public_loaders(self):
        path = RULES / PACK_REGISTRY["eu.it-es.pension-coordination.2026.v12.1.1"]["path"]
        for module, loader, error in (
            (pro_rata, load_rule_pack, ItEsEuPensionProRataError),
            (coordination, load_coordination_rule_pack, EuPensionCoordinationError),
        ):
            original_read = module._read_json

            def drifted_read(read_path, label, *, original_read=original_read):
                result = original_read(read_path, label)
                if read_path == path:
                    result["valid_from"] = "2026-11-02"
                return result

            with self.subTest(loader=loader.__module__), patch.object(module, "_read_json", side_effect=drifted_read):
                with self.assertRaisesRegex(error, "period"):
                    loader(path)

    def test_missing_selection_writes_null_identity_and_never_reads_input(self):
        for pack_id, spec in PACK_REGISTRY.items():
            with self.subTest(pack_id=pack_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                input_path = root / "input-must-not-be-read.json"
                output_path = root / "output.json"
                result = build_it_es_eu_pension_pro_rata(input_path, RULES / spec["path"], output_path)
                self.assertEqual(result["status"], "blocked_missing_inputs")
                self.assertIsNone(result["rule_pack"]["rule_pack_id"])
                self.assertIsNone(result["rule_pack"]["sha256"])
                self.assertIsNone(result["rule_pack"]["valid_from"])
                self.assertEqual(result["spanish_entitlement"]["status"], "not_assessed")
                self.assertIsNone(result["spanish_theoretical_pension"]["amounts"])
                self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_assessed")
                self.assertIsNone(result["spanish_pro_rata_pension"]["amounts"])
                self.assertEqual(result["data_gaps"][0]["code"], "legal_applicability_unknown")
                self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), result)

    def test_matching_boundary_selection_exposes_only_pack_metadata(self):
        cases = (
            (
                "eu.it-es.pension-coordination.2026.v11.1.1",
                {"member_state": "IT", "applicable_date": "2026-11-01", "right_acquisition_date": "2026-10-31", "contingency_date": "2026-10-31", "transition_classification": "acquired_before_application_date", "pre_application_periods": "none"},
            ),
            (
                "eu.it-es.pension-coordination.2026.v12.1.1",
                {"member_state": "ES", "applicable_date": "2026-11-01", "right_acquisition_date": "2026-11-01", "contingency_date": "2026-11-01", "transition_classification": "post_application_contingency", "pre_application_periods": "none"},
            ),
        )
        for pack_id, selection in cases:
            spec = PACK_REGISTRY[pack_id]
            with self.subTest(pack_id=pack_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output_path = root / "output.json"
                result = build_it_es_eu_pension_pro_rata(
                    root / "input-must-not-be-read.json",
                    RULES / spec["path"],
                    output_path,
                    eu_rule_selection=selection,
                )
                self.assertEqual(result["rule_pack"]["rule_pack_id"], pack_id)
                self.assertEqual(result["rule_pack"]["sha256"], spec["sha256"])
                self.assertEqual(result["rule_pack"]["valid_from"], spec["valid_from"].isoformat())
                self.assertEqual(result["rule_pack"]["valid_to"], spec["valid_to"].isoformat())
                self.assertEqual(result["data_gaps"][0]["code"], "consumer_output_not_assessed")
                self.assertIsNone(result["spanish_theoretical_pension"]["amounts"])
                self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_assessed")
                self.assertIsNone(result["spanish_pro_rata_pension"]["amounts"])
                self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), result)

    def test_selection_for_other_candidate_returns_null_pack_identity(self):
        spec = PACK_REGISTRY["eu.it-es.pension-coordination.2026.v11.1.1"]
        selection = {"member_state": "ES", "applicable_date": "2026-11-01", "right_acquisition_date": "2026-11-01", "contingency_date": "2026-11-01", "transition_classification": "post_application_contingency", "pre_application_periods": "none"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_it_es_eu_pension_pro_rata(
                root / "input-must-not-be-read.json",
                RULES / spec["path"],
                root / "output.json",
                eu_rule_selection=selection,
            )
        self.assertEqual(result["data_gaps"][0]["code"], "source_version_missing")
        self.assertIsNone(result["rule_pack"]["rule_pack_id"])
        self.assertIsNone(result["rule_pack"]["sha256"])
        self.assertEqual(result["spanish_pro_rata_pension"]["status"], "not_assessed")
        self.assertIsNone(result["spanish_pro_rata_pension"]["amounts"])

    def test_coordination_consumer_short_circuits_before_reading_individual_snapshots(self):
        selection = {"member_state": "IT", "applicable_date": "2026-11-01", "right_acquisition_date": "2026-10-31", "contingency_date": "2026-10-31", "transition_classification": "acquired_before_application_date", "pre_application_periods": "none"}
        spec = PACK_REGISTRY["eu.it-es.pension-coordination.2026.v11.1.1"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = coordinate_it_es_pensions(
                root / "inps-must-not-be-read.json",
                root / "spain-must-not-be-read.json",
                RULES / spec["path"],
                root / "output.json",
                eu_rule_selection=selection,
            )
            persisted = json.loads((root / "output.json").read_text(encoding="utf-8"))
        self.assertEqual(result, persisted)
        self.assertEqual(result["rule_pack"]["rule_pack_id"], "eu.it-es.pension-coordination.2026.v11.1.1")
        self.assertEqual(result["rule_pack"]["valid_from"], "2026-01-01")
        self.assertEqual(result["rule_pack"]["valid_to"], "2026-10-31")
        self.assertEqual({item["status"] for item in result["national_entitlements"]}, {"not_assessed"})
        self.assertTrue(all(item["amount"] is None for item in result["national_entitlements"]))
        self.assertEqual(result["data_gaps"][0]["code"], "consumer_output_not_assessed")

    def test_coordination_consumer_missing_selection_returns_null_identity_and_gap(self):
        spec = PACK_REGISTRY["eu.it-es.pension-coordination.2026.v12.1.1"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = coordinate_it_es_pensions(
                root / "inps-must-not-be-read.json",
                root / "spain-must-not-be-read.json",
                RULES / spec["path"],
                root / "output.json",
            )
        self.assertIsNone(result["rule_pack"]["rule_pack_id"])
        self.assertIsNone(result["rule_pack"]["sha256"])
        self.assertEqual(result["data_gaps"][0]["code"], "legal_applicability_unknown")
        self.assertEqual(result["period_summary"]["status"], "not_assessed")

    def test_coordination_consumer_cross_pack_selection_is_not_reported_as_selected(self):
        spec = PACK_REGISTRY["eu.it-es.pension-coordination.2026.v11.1.1"]
        selection = {"member_state": "ES", "applicable_date": "2026-11-01", "right_acquisition_date": "2026-11-01", "contingency_date": "2026-11-01", "transition_classification": "post_application_contingency", "pre_application_periods": "none"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = coordinate_it_es_pensions(
                root / "inps-must-not-be-read.json", root / "spain-must-not-be-read.json",
                RULES / spec["path"], root / "output.json", eu_rule_selection=selection,
            )
        self.assertEqual(result["data_gaps"][0]["code"], "source_version_missing")
        self.assertIsNone(result["rule_pack"]["rule_pack_id"])

    def test_candidate_coordination_gap_propagates_without_income_stream(self):
        selection = {"member_state": "ES", "applicable_date": "2026-11-01", "right_acquisition_date": "2026-11-01", "contingency_date": "2026-11-01", "transition_classification": "post_application_contingency", "pre_application_periods": "none"}
        spec = PACK_REGISTRY["eu.it-es.pension-coordination.2026.v12.1.1"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            coordination_path = root / "coordination.json"
            coordinate_it_es_pensions(
                root / "inps-must-not-be-read.json", root / "spain-must-not-be-read.json",
                RULES / spec["path"], coordination_path, eu_rule_selection=selection,
            )
            result = compose_pension_income(
                None, None, root / "income.json", eu_coordination_snapshot_path=coordination_path,
                include_rita=False,
            )
        self.assertEqual(result["income_streams"], [])
        self.assertIn("consumer_output_not_assessed", {gap["code"] for gap in result["data_gaps"]})
        self.assertEqual(result["data_gaps"][0]["source"], "eu_pension_coordination")


if __name__ == "__main__":
    unittest.main()
