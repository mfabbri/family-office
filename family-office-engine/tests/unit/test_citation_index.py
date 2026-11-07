import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.citation_index import (
    CitationIndexError,
    build_citation_index,
    search_citation_index,
)
from family_office_engine.services.tool_registry import build_tool_registry, invoke_registered_tool

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = REPOSITORY_ROOT / "family-office-knowledge"
CATALOG_PATH = KNOWLEDGE_ROOT / "sources" / "citation-catalog.json"


class CitationIndexTest(unittest.TestCase):
    def test_builds_real_public_corpus_with_explicit_gaps_and_contracts(self):
        first = build_citation_index(
            CATALOG_PATH,
            KNOWLEDGE_ROOT,
            contract_records=build_tool_registry()["tools"],
            as_of_date="2026-08-09",
        )
        second = build_citation_index(
            CATALOG_PATH,
            KNOWLEDGE_ROOT,
            contract_records=build_tool_registry()["tools"],
            as_of_date="2026-08-09",
        )

        self.assertEqual(first["schema_version"], "citation-index/v1")
        self.assertEqual(first["status"], "complete_with_gaps")
        self.assertGreaterEqual(first["summary"]["citation_count"], 10)
        self.assertEqual(first["summary"]["knowledge_document_count"], 28)
        self.assertGreaterEqual(first["summary"]["contract_count"], 15)
        self.assertEqual(
            first["reproducibility"]["content_hash"],
            second["reproducibility"]["content_hash"],
        )
        gap_codes = {gap["code"] for gap in first["data_gaps"]}
        self.assertIn("knowledge_document_citation_missing", gap_codes)
        self.assertNotIn("unindexed_knowledge_document", gap_codes)
        self.assertIn("eu.aml.regulation.2024-1624", {item["citation_id"] for item in first["citations"]})
        document_ids = {item["document_id"] for item in first["knowledge_documents"]}
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.19", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.20", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.21", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.22", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.24", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.25", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.26", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.27", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-evidence-audit-v0.28", document_ids)
        self.assertIn("knowledge.international.eu-pension-art57-public-boundary-regressions-v0.23", document_ids)
        self.assertIn("knowledge.international.eu-annex-viii-part2-catalogue-candidate", document_ids)

    def test_temporal_search_excludes_abrogated_source_but_supports_historical_query(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            catalog_path = _write_catalog(root, include_abrogated=True)
            index_path = root / "index.json"
            build_citation_index(catalog_path, root, output_path=index_path, as_of_date="2026-06-01")

            current = search_citation_index(index_path, topic="taxation", as_of_date="2026-06-01")
            historical = search_citation_index(index_path, topic="taxation", as_of_date="2024-06-01")

            self.assertEqual([item["citation_id"] for item in current["citations"]], ["source.current"])
            self.assertEqual(current["excluded_citations"], [{"citation_id": "source.old", "reason": "abrogated"}])
            self.assertEqual([item["citation_id"] for item in historical["citations"]], ["source.old"])

    def test_missing_citation_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            catalog_path = _write_catalog(root)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["documents"][0]["citation_ids"] = ["source.missing"]
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            with self.assertRaisesRegex(CitationIndexError, "unknown citations"):
                build_citation_index(catalog_path, root, as_of_date="2026-06-01")

    def test_duplicate_locator_is_deduplicated_with_alias(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            catalog_path = _write_catalog(root, duplicate=True)

            index = build_citation_index(catalog_path, root, as_of_date="2026-06-01")

            self.assertEqual(index["summary"]["citation_count"], 1)
            self.assertEqual(index["citations"][0]["alias_citation_ids"], ["source.current.alias"])
            self.assertEqual(index["knowledge_documents"][0]["citation_ids"], ["source.current"])

    def test_decision_and_publication_dates_are_preserved_but_not_validity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            catalog_path = _write_catalog(root)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            case_law = catalog["citations"][0]
            case_law.update({
                "citation_id": "a.case",
                "title": "Synthetic binding judgment",
                "source_type": "case_law",
                "authority_level": "binding_case_law",
                "url": "https://example.test/case",
                "valid_from": None,
                "valid_to": None,
                "decision_date": "2004-11-11",
                "published_on": "2005-01-08",
            })
            primary_law = dict(case_law)
            primary_law.update({
                "citation_id": "z.law",
                "title": "Synthetic primary law",
                "source_type": "legislation",
                "authority_level": "primary_law",
                "url": "https://example.test/law",
                "valid_from": "2004-01-01",
                "decision_date": None,
                "published_on": None,
            })
            catalog["citations"] = [case_law, primary_law]
            catalog["documents"][0]["citation_ids"] = ["z.law", "a.case"]
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            index = build_citation_index(catalog_path, root, as_of_date="2026-06-01")
            case_record = next(item for item in index["citations"] if item["citation_id"] == "a.case")
            self.assertEqual(case_record["decision_date"], "2004-11-11")
            self.assertEqual(case_record["published_on"], "2005-01-08")
            self.assertIsNone(case_record["valid_from"])

            index_path = root / "index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            result = search_citation_index(
                index_path, topic="taxation", as_of_date="2026-06-01", include_inactive=True
            )
            # Both authority levels rank equally; reversed IDs make the secondary ID ordering observable.
            self.assertEqual([item["citation_id"] for item in result["citations"]], ["a.case", "z.law"])
            self.assertEqual(
                next(item for item in result["citations"] if item["citation_id"] == "a.case")["temporal_status"],
                "unknown_validity",
            )

    def test_knowledge_path_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            catalog_path = _write_catalog(root)
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["documents"][0]["path"] = "../outside.md"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            with self.assertRaisesRegex(CitationIndexError, "escapes repository root"):
                build_citation_index(catalog_path, root, as_of_date="2026-06-01")

    def test_registered_search_tool_reads_built_index(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            catalog_path = _write_catalog(root)
            index_path = root / "index.json"
            build_citation_index(catalog_path, root, output_path=index_path, as_of_date="2026-06-01")

            result = invoke_registered_tool(
                "knowledge.citations.search",
                "citation-search/v1",
                {"index_path": index_path, "jurisdiction": "IT", "as_of_date": "2026-06-01"},
            )

            self.assertEqual(result["schema_version"], "tool-invocation/v1")
            self.assertEqual(result["output"]["citation_count"], 1)


def _write_catalog(root: Path, include_abrogated: bool = False, duplicate: bool = False) -> Path:
    (root / "taxation").mkdir(parents=True)
    (root / "taxation" / "note.md").write_text("# Synthetic tax note\n", encoding="utf-8")
    citations = [
        {
            "citation_id": "source.current",
            "title": "Current synthetic source",
            "issuer": "Synthetic Authority",
            "source_type": "legislation",
            "authority_level": "primary_law",
            "url": "https://example.test/current?a=1&b=2",
            "jurisdictions": ["IT"],
            "topics": ["taxation"],
            "valid_from": "2025-01-01",
            "valid_to": "2026-12-31",
            "verified_at": "2026-01-15",
            "source_status": "active",
        }
    ]
    citation_ids = ["source.current"]
    if include_abrogated:
        citations.append(
            {
                "citation_id": "source.old",
                "title": "Old synthetic source",
                "issuer": "Synthetic Authority",
                "source_type": "legislation",
                "authority_level": "primary_law",
                "url": "https://example.test/old",
                "jurisdictions": ["IT"],
                "topics": ["taxation"],
                "valid_from": "2020-01-01",
                "valid_to": "2024-12-31",
                "verified_at": "2024-01-15",
                "source_status": "abrogated",
            }
        )
        citation_ids.append("source.old")
    if duplicate:
        alias = dict(citations[0])
        alias["citation_id"] = "source.current.alias"
        alias["url"] = "https://EXAMPLE.test/current?b=2&a=1#fragment"
        citations.append(alias)
        citation_ids.append("source.current.alias")
    catalog = {
        "schema_version": "knowledge-citation-catalog/v1",
        "catalog_id": "synthetic-catalog",
        "corpus_roots": ["taxation"],
        "excluded_paths": [],
        "citations": citations,
        "documents": [
            {
                "document_id": "knowledge.synthetic.tax",
                "path": "taxation/note.md",
                "topics": ["taxation"],
                "jurisdictions": ["IT"],
                "citation_ids": citation_ids,
            }
        ],
    }
    catalog_path = root / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    return catalog_path


if __name__ == "__main__":
    unittest.main()
