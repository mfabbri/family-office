from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from family_office_engine.services import pension_entitlement_timeline_producer as producer
from family_office_engine.services.pension_timeline_source_gate import (
    EVENTS,
    JURISDICTIONS,
    PACK_REGISTRY,
)
from family_office_engine.services.eu_pension_coordination import coordinate_it_es_pensions
from family_office_engine.services.it_es_eu_pension_pro_rata import build_it_es_eu_pension_pro_rata
from family_office_engine.services.pension_timeline_source_gate import select_eu_pension_rule_pack


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RULES_ROOT = REPOSITORY_ROOT / "family-office-rules"
TIMELINE_DIRECTORY = REPOSITORY_ROOT / "family-office-workspace"


def _selection(pack_id: str) -> dict[str, object]:
    spec = PACK_REGISTRY[pack_id]
    return {
        "status": "candidate_selected",
        "rule_pack_id": pack_id,
        "digest_sha256": spec["sha256"],
        "transition_classification": "acquired_before_application_date" if pack_id.endswith("v11.1.1") else "post_application_contingency",
        "activation_allowed": False,
        "human_review_required": True,
        "data_gaps": [],
    }


def _candidate_bundle(pack_id: str) -> producer.PublicPensionEvidenceBundle:
    eu_spec = PACK_REGISTRY[pack_id]
    eu_path = RULES_ROOT / "cross-border" / eu_spec["path"]
    eu_metadata = {
        "path": str(eu_path),
        "rule_pack_id": pack_id,
        "sha256": eu_spec["sha256"],
        "valid_from": eu_spec["valid_from"].isoformat(),
        "valid_to": eu_spec["valid_to"].isoformat(),
    }
    it_path = RULES_ROOT / "italy/2026/inps-old-age-eligibility.json"
    es_path = RULES_ROOT / "spain/statutory-retirement-general.json"
    services = {
        # Deliberately tempting diagnostic values must never become timeline dates/amounts.
        "IT": {
            "rule_pack_id": "it.inps-old-age-eligibility.2026-2028.v2",
            "candidate_date": "2026-10-01",
            "first_eligible_month": "2026-10",
            "amount": "1234.56",
            "status": "assessed",
        },
        "ES": {
            "status": "complete",
            "retirement_date": "2030-01",
            "gross_pension": {"annual_amount": "4321.00"},
            "rule_pack": {
                "path": str(es_path),
                "rule_pack_id": "es.seguridad-social.statutory-retirement.general.2026-baseline.v2",
                "schema_version": "spanish-statutory-pension-rule-pack/v1",
            },
        },
        "EU_COORDINATION": {
            "status": "partial",
            "rule_pack": dict(eu_metadata),
            "national_entitlements": [
                {"country": "IT", "status": "not_assessed", "amount": None},
                {"country": "ES", "status": "not_assessed", "amount": None},
            ],
            "annex_viii_match_status": "not_matched",
            "data_gaps": [{"code": "consumer_output_not_assessed", "message": "Candidate only.", "severity": "blocking"}],
        },
        "EU_PRO_RATA": {
            "status": "blocked_missing_inputs",
            "rule_pack": dict(eu_metadata),
            "spanish_theoretical_pension": {"status": "complete", "amounts": {"monthly": "9999.99"}},
            "spanish_pro_rata_pension": {"status": "not_assessed", "amounts": None},
            "data_gaps": [{"code": "consumer_output_not_assessed", "message": "Candidate only.", "severity": "blocking"}],
        },
    }
    return producer.PublicPensionEvidenceBundle(
        service_snapshots=services,
        rule_pack_paths={"IT": it_path, "ES": es_path, "EU": eu_path},
        eu_rule_selection=_selection(pack_id),
    )


class PensionEntitlementTimelineProducerTest(unittest.TestCase):
    def test_all_15_public_branches_aggregate_to_five_null_events(self):
        bundle = _candidate_bundle("eu.it-es.pension-coordination.2026.v12.1.1")
        branches = producer.map_public_service_branches(bundle)
        self.assertEqual(15, len(branches))
        self.assertEqual({(event, jurisdiction) for event in EVENTS for jurisdiction in JURISDICTIONS},
                         {(branch.event, branch.jurisdiction) for branch in branches})
        for branch in branches:
            with self.subTest(event=branch.event, jurisdiction=branch.jurisdiction):
                self.assertEqual("not_assessed", branch.status)
                self.assertIsNone(branch.date)
                self.assertIsNone(branch.payer)
                self.assertIsNone(branch.amount)
                self.assertEqual("diagnostic_only", branch.evidence_role)
                self.assertEqual("blocking", branch.data_gaps[0]["severity"])
                if branch.jurisdiction in {"IT", "ES"}:
                    self.assertEqual("source_version_missing", branch.data_gaps[0]["code"])

        timeline = producer.produce_source_bound_pension_timeline(
            member_id="synthetic-member", as_of_date="2026-11-15", evidence_bundle=bundle
        )
        self.assertEqual("not_assessed", timeline["status"])
        self.assertEqual("unknown", timeline["pension_amount_basis"]["basis_state"])
        self.assertEqual(5, len(timeline["events"]))
        for event_name, event in timeline["events"].items():
            with self.subTest(event=event_name):
                self.assertEqual("not_assessed", event["status"])
                self.assertIsNone(event["date"])
                self.assertEqual([], event["evidence"])
                self.assertEqual(3, len(event["data_gaps"]))

    def test_italian_v2_service_binding_fails_closed_against_v3_candidate(self):
        bundle = _candidate_bundle("eu.it-es.pension-coordination.2026.v12.1.1")
        snapshots = dict(bundle.service_snapshots)
        snapshots["IT"] = {
            "rule_pack_id": "it.inps-old-age-eligibility.2026-2028.v2",
            "candidate_date": "2026-10-01",
            "status": "assessed",
        }
        branches = producer.map_public_service_branches(
            producer.PublicPensionEvidenceBundle(
                service_snapshots=snapshots,
                rule_pack_paths=bundle.rule_pack_paths,
                eu_rule_selection=bundle.eu_rule_selection,
            )
        )
        italian = [branch for branch in branches if branch.jurisdiction == "IT"]
        self.assertEqual(5, len(italian))
        self.assertTrue(all(branch.data_gaps[0]["code"] == "source_version_missing" for branch in italian))
        self.assertTrue(all(branch.date is None and branch.amount is None for branch in italian))

    def test_spanish_legacy_loader_schema_cannot_attest_v3_candidate(self):
        bundle = _candidate_bundle("eu.it-es.pension-coordination.2026.v12.1.1")
        snapshots = dict(bundle.service_snapshots)
        snapshots["ES"] = {
            "status": "complete",
            "rule_pack": {
                "path": str(RULES_ROOT / producer.DOMESTIC_PACK_REGISTRY["ES"]["path"]),
                "rule_pack_id": producer.DOMESTIC_PACK_REGISTRY["ES"]["rule_pack_id"],
                "schema_version": "spanish-statutory-pension-rule-pack/v1",
            },
        }
        paths = dict(bundle.rule_pack_paths)
        paths["ES"] = RULES_ROOT / producer.DOMESTIC_PACK_REGISTRY["ES"]["path"]
        branches = producer.map_public_service_branches(
            producer.PublicPensionEvidenceBundle(
                service_snapshots=snapshots,
                rule_pack_paths=paths,
                eu_rule_selection=bundle.eu_rule_selection,
            )
        )
        spanish = [branch for branch in branches if branch.jurisdiction == "ES"]
        self.assertEqual(5, len(spanish))
        self.assertTrue(all(branch.data_gaps[0]["code"] == "source_version_missing" for branch in spanish))

    def test_inclusive_periods_normalize_to_half_open_boundaries(self):
        self.assertEqual(
            ("2026-01-01", "2026-11-01"),
            producer.normalize_inclusive_validity("2026-01-01", "2026-10-31"),
        )
        self.assertEqual(
            ("2026-11-01", "2027-01-01"),
            producer.normalize_inclusive_validity("2026-11-01", "2026-12-31"),
        )
        self.assertEqual(("2026-01-01", None), producer.normalize_inclusive_validity("2026-01-01", None))
        with self.assertRaises(ValueError):
            producer.normalize_inclusive_validity("2026-01-02", "2026-01-01")
        with self.assertRaises(ValueError):
            producer.normalize_inclusive_validity("2026-01-01", "2026-1-2")

    def test_both_eu_packs_have_exact_binding_and_unchanged_outcome(self):
        for pack_id in PACK_REGISTRY:
            with self.subTest(pack_id=pack_id):
                branches = producer.map_public_service_branches(_candidate_bundle(pack_id))
                eu = [branch for branch in branches if branch.jurisdiction == "EU"]
                spec = PACK_REGISTRY[pack_id]
                self.assertEqual(5, len(eu))
                self.assertTrue(all(branch.rule_pack_id == pack_id for branch in eu))
                self.assertTrue(all(branch.digest_sha256 == spec["sha256"] for branch in eu))
                self.assertEqual("2026-11-01" if pack_id.endswith("v11.1.1") else "2027-01-01", eu[0].valid_to_exclusive)
                self.assertTrue(all(branch.status == "not_assessed" and branch.date is None for branch in eu))

    def test_cross_pack_and_metadata_mismatches_fail_closed(self):
        bundle = _candidate_bundle("eu.it-es.pension-coordination.2026.v12.1.1")
        bad_cases = {
            "wrong selector digest": ("selection", {**bundle.eu_rule_selection, "digest_sha256": "0" * 64}),
            "transition pack conflict": ("selection", {**bundle.eu_rule_selection, "transition_classification": "acquired_before_application_date"}),
            "wrong consumer digest": ("consumer_digest", "0" * 64),
            "wrong consumer path": ("consumer_path", str(RULES_ROOT.parent / "outside.json")),
            "cross-pack consumer": ("cross_pack", "eu.it-es.pension-coordination.2026.v11.1.1"),
            "wrong period": ("period", "2026-11-02"),
        }
        for label, (kind, value) in bad_cases.items():
            with self.subTest(case=label):
                snapshots = {key: dict(item) if isinstance(item, dict) else item for key, item in bundle.service_snapshots.items()}
                selection = bundle.eu_rule_selection
                if kind == "selection":
                    selection = value
                elif kind == "consumer_digest":
                    meta = dict(snapshots["EU_PRO_RATA"]["rule_pack"])
                    meta["sha256"] = value
                    snapshots["EU_PRO_RATA"] = {**snapshots["EU_PRO_RATA"], "rule_pack": meta}
                elif kind == "consumer_path":
                    meta = dict(snapshots["EU_COORDINATION"]["rule_pack"])
                    meta["path"] = value
                    snapshots["EU_COORDINATION"] = {**snapshots["EU_COORDINATION"], "rule_pack": meta}
                elif kind == "cross_pack":
                    other = PACK_REGISTRY[value]
                    meta = dict(snapshots["EU_PRO_RATA"]["rule_pack"])
                    meta.update({
                        "rule_pack_id": value,
                        "sha256": other["sha256"],
                        "valid_from": other["valid_from"].isoformat(),
                        "valid_to": other["valid_to"].isoformat(),
                        "path": str(RULES_ROOT / "cross-border" / other["path"]),
                    })
                    snapshots["EU_PRO_RATA"] = {**snapshots["EU_PRO_RATA"], "rule_pack": meta}
                elif kind == "period":
                    meta = dict(snapshots["EU_PRO_RATA"]["rule_pack"])
                    meta["valid_from"] = value
                    snapshots["EU_PRO_RATA"] = {**snapshots["EU_PRO_RATA"], "rule_pack": meta}
                changed = producer.PublicPensionEvidenceBundle(
                    service_snapshots=snapshots,
                    rule_pack_paths=bundle.rule_pack_paths,
                    eu_rule_selection=selection,
                )
                eu = [branch for branch in producer.map_public_service_branches(changed) if branch.jurisdiction == "EU"]
                self.assertTrue(all(branch.data_gaps[0]["code"] == "source_version_missing" for branch in eu))
                self.assertTrue(all(branch.date is None and branch.amount is None for branch in eu))

    def test_canonical_path_escape_and_source_drift_fail_closed(self):
        bundle = _candidate_bundle("eu.it-es.pension-coordination.2026.v12.1.1")
        escaped = producer.PublicPensionEvidenceBundle(
            service_snapshots=bundle.service_snapshots,
            rule_pack_paths={**bundle.rule_pack_paths, "EU": RULES_ROOT.parent / "outside.json"},
            eu_rule_selection=bundle.eu_rule_selection,
        )
        escaped_eu = [branch for branch in producer.map_public_service_branches(escaped) if branch.jurisdiction == "EU"]
        self.assertTrue(all(branch.data_gaps[0]["code"] == "source_version_missing" for branch in escaped_eu))

        with patch.object(producer, "_read_rule_pack_bytes", return_value=b"{}"):  # source drift
            drifted_eu = [branch for branch in producer.map_public_service_branches(bundle) if branch.jurisdiction == "EU"]
        self.assertTrue(all(branch.data_gaps[0]["code"] == "source_version_missing" for branch in drifted_eu))

    def test_eu_evidence_only_snapshot_does_not_create_income_stream(self):
        coordination_path = TIMELINE_DIRECTORY / "synthetic-eu-coordination.json"
        pro_rata_path = TIMELINE_DIRECTORY / "synthetic-eu-pro-rata.json"
        input_path = TIMELINE_DIRECTORY / "synthetic-eu-input.json"
        output_path = TIMELINE_DIRECTORY / "synthetic-pension-income.json"
        original_read_text = Path.read_text
        from family_office_engine.services.pension_income import compose_pension_income
        for pack_id in PACK_REGISTRY:
            with self.subTest(pack_id=pack_id):
                pack_path = RULES_ROOT / "cross-border" / PACK_REGISTRY[pack_id]["path"]
                before_application = pack_id.endswith("v11.1.1")
                selection_inputs = {
                    "member_state": "IT",
                    "applicable_date": "2026-11-01",
                    "right_acquisition_date": "2026-10-31" if before_application else "2026-11-01",
                    "contingency_date": "2026-10-31" if before_application else "2026-11-01",
                    "transition_classification": "acquired_before_application_date" if before_application else "post_application_contingency",
                    "pre_application_periods": "none",
                }
                selection = select_eu_pension_rule_pack(**selection_inputs, rules_root=pack_path.parent)
                self.assertEqual(pack_id, selection["rule_pack_id"])
                with patch.object(Path, "write_text"), patch.object(Path, "mkdir"):
                    coordination_snapshot = coordinate_it_es_pensions(
                        TIMELINE_DIRECTORY / "synthetic-inps.json",
                        TIMELINE_DIRECTORY / "synthetic-spanish.json",
                        pack_path,
                        coordination_path,
                        eu_rule_selection=selection_inputs,
                    )
                    pro_rata_snapshot = build_it_es_eu_pension_pro_rata(
                        input_path,
                        pack_path,
                        pro_rata_path,
                        eu_rule_selection=selection_inputs,
                    )
                bundle = _candidate_bundle(pack_id)
                snapshots = dict(bundle.service_snapshots)
                snapshots["EU_COORDINATION"] = coordination_snapshot
                snapshots["EU_PRO_RATA"] = pro_rata_snapshot
                bundle = producer.PublicPensionEvidenceBundle(
                    service_snapshots=snapshots,
                    rule_pack_paths=bundle.rule_pack_paths,
                    eu_rule_selection=selection,
                )
                timeline = producer.produce_source_bound_pension_timeline(
                    member_id="synthetic-member",
                    as_of_date="2026-11-15",
                    evidence_bundle=bundle,
                )
                self.assertTrue(all(event["status"] == "not_assessed" and event["date"] is None for event in timeline["events"].values()))

                def read_text(path: Path, *args, **kwargs):
                    if path == coordination_path:
                        return json.dumps(coordination_snapshot)
                    return original_read_text(path, *args, **kwargs)

                with patch.object(Path, "read_text", read_text), patch.object(Path, "write_text"), patch.object(Path, "mkdir"):
                    result = compose_pension_income(
                        None,
                        None,
                        output_path,
                        eu_coordination_snapshot_path=coordination_path,
                    )
                self.assertEqual("blocked_missing_inputs", result["status"])
                self.assertEqual([], result["income_streams"])
                self.assertIsNone(result["summary"]["gross_annual_recurring_total"])

    def test_invalid_as_of_date_and_empty_member_id_are_rejected(self):
        bundle = _candidate_bundle("eu.it-es.pension-coordination.2026.v12.1.1")
        with self.assertRaisesRegex(ValueError, "member_id"):
            producer.produce_source_bound_pension_timeline(member_id=" ", as_of_date="2026-11-15", evidence_bundle=bundle)
        with self.assertRaisesRegex(ValueError, "as_of_date"):
            producer.produce_source_bound_pension_timeline(member_id="synthetic-member", as_of_date="2026-1-5", evidence_bundle=bundle)


if __name__ == "__main__":
    unittest.main()
