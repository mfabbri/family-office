import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.tax_events import TaxEventsError, generate_impatriati_events


class TaxEventsTest(unittest.TestCase):
    def test_generate_impatriati_events_writes_schedule(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tax-events.snapshot.json"

            result = generate_impatriati_events(2026, 2029, "0.30", "legacy_pre_2024", output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(result["record_type"], "TaxEventsSnapshot")
            self.assertEqual(len(written["events"]), 4)
            self.assertEqual(written["events"][0]["tax_year"], 2026)
            self.assertEqual(written["events"][-1]["tax_year"], 2029)
            self.assertEqual(written["events"][0]["taxable_income_share"], "0.30")

    def test_generate_impatriati_events_rejects_invalid_year_range(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(TaxEventsError, "end_year"):
                generate_impatriati_events(2030, 2029, "0.30", "legacy_pre_2024", Path(tmp_dir) / "out.json")

    def test_generate_impatriati_events_rejects_invalid_share(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(TaxEventsError, "between 0 and 1"):
                generate_impatriati_events(2026, 2029, "1.50", "legacy_pre_2024", Path(tmp_dir) / "out.json")


if __name__ == "__main__":
    unittest.main()
