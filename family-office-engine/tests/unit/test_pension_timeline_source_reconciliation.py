"""Synthetic guards for the source-version reconciliation candidate."""

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OLD_IT_PACK = ROOT / "family-office-rules/italy/2026/inps-old-age-eligibility.json"
IT_CANDIDATE = ROOT / "family-office-rules/italy/2026/inps-old-age-eligibility-v3.json"
MATRIX = ROOT / "family-office-knowledge/pensions/pension-timeline-source-matrix-v0.6.md"
EU_RULES = ROOT / "family-office-rules/cross-border/eu-pension-coordination-it-es-v12.1.1.json"
EU_RULES_PREAMENDMENT = ROOT / "family-office-rules/cross-border/eu-pension-coordination-it-es-v11.1.1.json"
ES_RULES = ROOT / "family-office-rules/spain/statutory-retirement-general-v3.json"


class PensionTimelineSourceReconciliationTests(unittest.TestCase):
    def test_italian_candidate_separates_original_law_from_consolidated_view(self):
        old_digest = hashlib.sha256(OLD_IT_PACK.read_bytes()).hexdigest()
        self.assertEqual(
            old_digest,
            "2b824d7ca46b4faaa38a83a7cd2d53769bcda6713251e17146a6244a1b0edee9",
        )
        old_pack = json.loads(OLD_IT_PACK.read_text(encoding="utf-8"))
        candidate = json.loads(IT_CANDIDATE.read_text(encoding="utf-8"))
        self.assertEqual(old_pack["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v2")
        self.assertEqual(candidate["rule_pack_id"], "it.inps-old-age-eligibility.2026-2028.v3")
        self.assertEqual(candidate["provenance_status"], "candidate_pending_exact_hash_normative_review")

        roles = {row["source_id"]: row["legal_role"] for row in candidate["source_refs"]}
        self.assertEqual(roles["normattiva.dl-201-2011.art24"], "official_consolidated_consultation")
        self.assertEqual(roles["gazzetta.dl-201-2011.11g0247"], "primary_legislation")
        self.assertEqual(roles["gazzetta.l-214-2011.11g0256"], "primary_legislation")

    def test_current_matrix_keeps_all_15_rows_unknown_at_half_open_cutoff(self):
        text = MATRIX.read_text(encoding="utf-8")
        self.assertIn("2026-11-14", text)
        self.assertIn("`valid_to=2026-11-15` is exclusive", text)
        self.assertIn("it.inps-old-age-eligibility.2026-2028.v3", text)

        matrix_section = text.split("## Five-event matrix", 1)[1].split("\n## ", 1)[0]
        rows = [line for line in matrix_section.splitlines() if line.startswith("| `")]
        self.assertEqual(len(rows), 15)
        self.assertTrue(all("`null + stable data_gaps`" in row for row in rows))
        event_jurisdictions = set()
        for row in rows:
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            event_jurisdictions.add((cells[0].strip(" `"), cells[1].strip(" `")))
        self.assertEqual(len(event_jurisdictions), 15)
        self.assertEqual({jurisdiction for _, jurisdiction in event_jurisdictions}, {"IT", "ES", "EU"})

    def test_active_knowledge_notes_name_only_v0_6_as_current_matrix(self):
        knowledge_root = ROOT / "family-office-knowledge"
        active_notes = [
            knowledge_root / "pensions/pension-timeline-source-matrix-v0.6.md",
            knowledge_root / "pensions/pension-timeline-events-it-es-eu.md",
            knowledge_root / "international/eu-pension-coordination-it-es.md",
            knowledge_root / "international/spain-pension.md",
        ]
        current_matrix_claims = []
        stale_v03_claims = []
        for path in active_notes:
            note_text = path.read_text(encoding="utf-8")
            prose = re.sub(r"https?://\S+", "", note_text)
            for marker in ("?", chr(0x00c3), chr(0x00c2), chr(0xfffd)):
                self.assertNotIn(marker, prose, f"{path.name} contains encoding marker {marker!r}")
            for line in note_text.splitlines():
                current_matrix_claims.extend(
                    (path.name, match.group(0))
                    for match in re.finditer(
                        r"(?i)(?:matrice.*?v0\.\d+.*?riferimento corrente|"
                        r"riferimento corrente.*?matrice.*?v0\.\d+)",
                        line,
                    )
                )
                stale_v03_claims.extend(
                    (path.name, match.group(0))
                    for match in re.finditer(
                        r"(?i)(?:matrice.*?v0\.3.*?riferimento corrente|"
                        r"riferimento corrente.*?matrice.*?v0\.3)",
                        line,
                    )
                )

        self.assertEqual(len(current_matrix_claims), 1, current_matrix_claims)
        self.assertIn("v0.6", current_matrix_claims[0][1])
        self.assertEqual(stale_v03_claims, [])
        event_note = (knowledge_root / "pensions/pension-timeline-events-it-es-eu.md").read_text(encoding="utf-8")
        canonical_line = (
            "**Riferimento corrente della matrice (2026-11-15):** "
            "`pension-timeline-source-matrix-v0.6.md` e' il solo riferimento "
            "versionato corrente per fonti, periodi e supporto dei 15 rami."
        )
        self.assertIn(canonical_line, event_note.splitlines())
        for version in ("v0.3", "v0.4", "v0.5"):
            self.assertIn(f"La matrice {version} " + chr(0x00e8) + " storica", event_note)

    def test_normative_source_identity_is_utf8_clean_and_manifest_anchor_is_exact(self):
        expected_authority = "Agencia Estatal Bolet" + chr(0x00ed) + "n Oficial del Estado"
        packs = (
            json.loads(EU_RULES_PREAMENDMENT.read_text(encoding="utf-8")),
            json.loads(EU_RULES.read_text(encoding="utf-8")),
        )
        for pack in packs:
            source = next(
                row for row in pack["source_refs"]
                if row.get("source_id") == "boe.lgss.rdl-8-2015.consolidated"
            )
            self.assertEqual(source["authority"], expected_authority)
            identity_fields = " ".join(
                str(source.get(field, "")) for field in ("source_id", "title", "authority")
            )
            for marker in (chr(0x00c3), chr(0x00c2), chr(0xfffd)):
                self.assertNotIn(marker, identity_fields)

        codigo_civil = "C" + chr(0x00f3) + "digo Civil"
        spanish_note = (ROOT / "family-office-knowledge/international/spain-pension.md").read_text(encoding="utf-8")
        self.assertIn(codigo_civil, spanish_note)
        manifest = (ROOT / "family-office-engine/docs/roadmap/v4.14w-z-e-review-manifest-v0.9.md").read_text(encoding="utf-8")
        self.assertIn(codigo_civil, manifest)
        self.assertEqual(manifest.splitlines()[0], "# V4.14w-z-e - exact-hash normative review manifest v0.9")
        self.assertNotIn("?", manifest.splitlines()[0])
        self.assertNotIn(chr(0xfffd), manifest)

    def test_annex_and_article_57_versions_are_explicitly_reconciled(self):
        text = MATRIX.read_text(encoding="utf-8")
        self.assertIn("Article 57 contract v0.29", text)
        self.assertIn("Annex evidence v0.3", text)
        self.assertIn("standalone `eu_pension_coordination.py`", text)
        self.assertRegex(text, re.compile(r"COM\(2026\) 980.*not operative", re.IGNORECASE))

    def test_eu_article_50_amendment_is_versioned_at_its_application_boundary(self):
        candidate = json.loads(EU_RULES.read_text(encoding="utf-8"))
        preamendment = json.loads(EU_RULES_PREAMENDMENT.read_text(encoding="utf-8"))
        source = next(
            row for row in candidate["source_refs"]
            if row["source_id"] == "eurlex-reg-2026-2359-oj"
        )
        self.assertEqual(candidate["rule_pack_id"], "eu.it-es.pension-coordination.2026.v12.1.1")
        self.assertEqual(preamendment["valid_to"], "2026-10-31")
        self.assertEqual(candidate["amendment_scope"]["prior_rule_pack_id"], preamendment["rule_pack_id"])
        self.assertEqual(preamendment["version_transition"]["successor_pack"], candidate["rule_pack_id"])
        self.assertEqual(candidate["transition_policy"]["rule_selection"]["prior_pack"], preamendment["rule_pack_id"])
        self.assertEqual(candidate["valid_from"], "2026-11-01")
        self.assertEqual(candidate["amendment_scope"]["supersedes_from"], "2026-11-01")
        transition = candidate["transition_policy"]
        self.assertEqual(transition["provision"], "Regulation (EC) No 883/2004 Article 87b(1)-(3)")
        self.assertIn("Article 91(3)(1)(b)", transition["relevant_application_date_source"])
        self.assertEqual(transition["rule_selection"]["prior_pack_valid_through"], "2026-10-31")
        self.assertEqual(transition["rule_selection"]["candidate_pack_valid_from"], "2026-11-01")
        self.assertIn("not contingency_date alone", transition["rule_selection"]["basis"])
        self.assertEqual(transition["rule_selection"]["missing_or_ambiguous_timing_action"], "not_assessed_with_data_gaps")
        self.assertIn("before", transition["effects"]["paragraph_1"])
        self.assertIn("Periods completed before", transition["effects"]["paragraph_2"])
        self.assertIn("contingency arising before", transition["effects"]["paragraph_3"])
        self.assertEqual(source["source_role"], "primary_publication")
        self.assertTrue(any("Article 50(2)" in provision for provision in source["provisions"]))
        self.assertIn("2026-10-31", candidate["amendment_scope"]["boundary_regressions"])
        self.assertIn("2026-11-01", candidate["amendment_scope"]["boundary_regressions"])
        text = MATRIX.read_text(encoding="utf-8")
        self.assertIn("Regulation (EU) 2026/2359", text)
        self.assertNotRegex(text, re.compile(r"PE-CONS 29/26.*not operative", re.IGNORECASE))

    def test_catalog_cites_the_whole_regulation_and_v0_6_references_are_unique(self):
        catalog = json.loads((ROOT / "family-office-knowledge/sources/citation-catalog.json").read_text(encoding="utf-8"))
        citation = next(item for item in catalog["citations"] if item["citation_id"] == "eu.regulation.2026-2359")
        self.assertIn("eu.regulation.2026-2359.annex-viii-part-i", citation["alias_citation_ids"])
        self.assertIn("Article 1(36)", citation["official_reference"])
        self.assertEqual(citation["published_on"], "2026-10-27")
        document = next(item for item in catalog["documents"] if item["document_id"] == "knowledge.pensions.timeline-source-matrix-v0.6")
        self.assertEqual(len(document["citation_ids"]), len(set(document["citation_ids"])))
        self.assertIn("eu.regulation.2026-2359", document["citation_ids"])
        self.assertIn("v11.1.1/v12.1.1", MATRIX.read_text(encoding="utf-8"))
        self.assertIn("general.2026-baseline.v3", MATRIX.read_text(encoding="utf-8"))

    def test_spain_consolidated_consultation_has_unambiguous_source_id(self):
        candidate = json.loads(ES_RULES.read_text(encoding="utf-8"))
        source_rows = []

        def collect_sources(value):
            if isinstance(value, dict):
                if value.get("title") == "Codigo Civil, articulo 5.1":
                    source_rows.append(value)
                for child in value.values():
                    collect_sources(child)
            elif isinstance(value, list):
                for child in value:
                    collect_sources(child)

        collect_sources(candidate)
        source = next(
            row for row in source_rows
        )
        self.assertEqual(source["source_id"], "boe.codigo-civil.article-5.1.consolidated-consultation")
        self.assertEqual(source["source_role"], "official_consolidated_consultation")
        self.assertEqual(source["url"], "https://www.boe.es/buscar/act.php?id=BOE-A-1889-4763")


if __name__ == "__main__":
    unittest.main()
