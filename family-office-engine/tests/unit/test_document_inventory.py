import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.document_inventory import (
    DocumentInventoryError,
    DocumentOrganizationError,
    build_document_inventory,
    organize_documents,
)


class DocumentInventoryTest(unittest.TestCase):
    def test_builds_inventory_for_workspace_inbox(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            pensione = inbox / "pensione"
            banca = inbox / "banca"
            pensione.mkdir(parents=True)
            banca.mkdir(parents=True)
            (pensione / "simulazione.pdf").write_bytes(b"synthetic pdf")
            (banca / "saldo.xls").write_bytes(b"synthetic xls")
            (inbox / ".gitkeep").write_text("", encoding="utf-8")
            output_path = root / "snapshots" / "document-inventory.snapshot.json"

            result = build_document_inventory(inbox, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["schema_version"], "document-inventory/v1")
            self.assertEqual(written["record_type"], "DocumentInventorySnapshot")
            self.assertEqual(written["summary"]["document_count"], 2)
            self.assertEqual(written["summary"]["categories"]["pensione"], 1)
            self.assertEqual(written["next_import_candidates"][0]["category"], "pensione")
            self.assertIn("sha256", written["documents"][0])

    def test_rejects_missing_inbox(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            with self.assertRaisesRegex(DocumentInventoryError, "Inbox path not found"):
                build_document_inventory(
                    root / "missing",
                    root / "snapshots" / "document-inventory.snapshot.json",
                )

    def test_organize_plans_destination_paths_without_moving(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest_path = documents / "manifest.json"
            (inbox / "pensione").mkdir(parents=True)
            (inbox / "pensione" / "sintesi_posizione_aderente_2026.pdf").write_bytes(b"fonte")
            (inbox / "pensione" / "riepilogo-simulazione.pdf").write_bytes(b"inps")

            result = organize_documents(inbox, documents, manifest_path)

            self.assertEqual(result["status"], "planned")
            self.assertEqual(result["summary"]["operation_count"], 2)
            destinations = {operation["filename"]: operation for operation in result["operations"]}
            self.assertEqual(destinations["sintesi_posizione_aderente_2026.pdf"]["destination_category"], "fonte")
            self.assertEqual(destinations["riepilogo-simulazione.pdf"]["destination_category"], "pensione/inps")
            self.assertTrue((inbox / "pensione" / "riepilogo-simulazione.pdf").exists())

    def test_organize_routes_directa_documents(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest_path = documents / "manifest.json"
            (inbox / "directa").mkdir(parents=True)
            (inbox / "directa" / "rendiconto_directa.pdf").write_bytes(b"directa")

            result = organize_documents(inbox, documents, manifest_path)

            operation = result["operations"][0]
            self.assertEqual(operation["destination_category"], "investimenti/directa")
            self.assertEqual(operation["destination_relative_path"], "investimenti\\directa\\rendiconto_directa.pdf")

    def test_organize_routes_payroll_documents(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest_path = documents / "manifest.json"
            (inbox / "bustepaga").mkdir(parents=True)
            (inbox / "bustepaga" / "cedolino_gennaio.pdf").write_bytes(b"payroll")

            result = organize_documents(inbox, documents, manifest_path)

            operation = result["operations"][0]
            self.assertEqual(operation["destination_category"], "redditi/buste-paga")
            self.assertEqual(
                operation["destination_relative_path"],
                "redditi\\buste-paga\\cedolino_gennaio.pdf",
            )

    def test_organize_routes_spanish_pension_documents(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest_path = documents / "manifest.json"
            (inbox / "pensione_spagna").mkdir(parents=True)
            (inbox / "pensione").mkdir(parents=True)
            (inbox / "pensione_spagna" / "vida_laboral.pdf").write_bytes(b"spanish pension")
            (inbox / "pensione" / "plan_universal_2025.pdf").write_bytes(b"spanish plan")

            result = organize_documents(inbox, documents, manifest_path)

            destinations = {
                operation["filename"]: operation["destination_category"]
                for operation in result["operations"]
            }
            self.assertEqual(destinations["vida_laboral.pdf"], "pensione/spagna")
            self.assertEqual(destinations["plan_universal_2025.pdf"], "pensione/spagna")

    def test_inventory_suggests_directa_and_spanish_pension_imports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            (inbox / "directa").mkdir(parents=True)
            (inbox / "pensione_spagna").mkdir(parents=True)
            (inbox / "pensione" / "spagna").mkdir(parents=True)
            (inbox / "directa" / "rendiconto.pdf").write_bytes(b"directa")
            (inbox / "pensione_spagna" / "vida_laboral.pdf").write_bytes(b"spanish pension")
            (inbox / "pensione" / "spagna" / "vida_laboral_2.pdf").write_bytes(b"spanish pension")
            output_path = root / "snapshots" / "document-inventory.snapshot.json"

            result = build_document_inventory(inbox, output_path)

            candidates = {
                candidate["category"]: candidate["suggested_increment"]
                for candidate in result["next_import_candidates"]
            }
            self.assertEqual(candidates["directa"], "Import Directa investment statements.")
            self.assertEqual(candidates["pensione_spagna"], "Import Spanish pension documents.")
            self.assertEqual(result["summary"]["categories"]["pensione_spagna"], 2)

    def test_inventory_suggests_payroll_import(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            (inbox / "bustepaga").mkdir(parents=True)
            (inbox / "bustepaga" / "cedolino.pdf").write_bytes(b"payroll")
            output_path = root / "snapshots" / "document-inventory.snapshot.json"

            result = build_document_inventory(inbox, output_path)

            candidates = {
                candidate["category"]: candidate["suggested_increment"]
                for candidate in result["next_import_candidates"]
            }
            self.assertEqual(candidates["bustepaga"], "Import payroll payslips.")

    def test_organize_apply_moves_files_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest_path = documents / "manifest.json"
            (inbox / "investimenti_italia").mkdir(parents=True)
            source = inbox / "investimenti_italia" / "rendiconto.pdf"
            source.write_bytes(b"statement")

            result = organize_documents(inbox, documents, manifest_path, apply=True)

            self.assertEqual(result["status"], "applied")
            self.assertFalse(source.exists())
            self.assertTrue((documents / "investimenti" / "italia" / "rendiconto.pdf").exists())
            written = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(written["operations"][0]["action"], "moved")

    def test_organize_plans_unique_destination_for_duplicate_names(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            documents = root / "documents"
            manifest_path = documents / "manifest.json"
            (inbox / "fonte").mkdir(parents=True)
            (inbox / "pensione").mkdir(parents=True)
            (inbox / "fonte" / "sintesi_posizione_aderente.pdf").write_bytes(b"fonte")
            (inbox / "pensione" / "sintesi_posizione_aderente.pdf").write_bytes(b"fonte")

            result = organize_documents(inbox, documents, manifest_path)

            destinations = [
                operation["destination_relative_path"]
                for operation in result["operations"]
            ]
            self.assertEqual(len(destinations), 2)
            self.assertEqual(len(set(destinations)), 2)
            self.assertIn("fonte\\sintesi_posizione_aderente.pdf", destinations)
            self.assertIn("fonte\\sintesi_posizione_aderente__from_pensione.pdf", destinations)

    def test_organize_rejects_destination_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            inbox = root / "inbox"
            inbox.mkdir()

            with self.assertRaisesRegex(DocumentOrganizationError, "outside workspace"):
                organize_documents(
                    inbox,
                    root.parent / "outside-documents",
                    root / "documents" / "manifest.json",
                )


if __name__ == "__main__":
    unittest.main()
