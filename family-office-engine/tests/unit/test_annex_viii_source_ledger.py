import hashlib
import json
import unittest
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = REPOSITORY_ROOT / "family-office-knowledge" / "international" / "eu-annex-viii-part-2-catalogue-v0.4.json"
SCHEMA_PATH = REPOSITORY_ROOT / "family-office-knowledge" / "international" / "eu-annex-viii-part-2-catalogue-v0.4.schema.json"

EXPECTED_SOURCE_URLS = {
    "32009R0988": "https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng",
    "32010R1244": "https://eur-lex.europa.eu/eli/reg/2010/1244/oj/eng",
    "32012R1224": "https://eur-lex.europa.eu/eli/reg/2012/1224/oj/eng",
    "32013R0517": "https://eur-lex.europa.eu/eli/reg/2013/517/oj/eng",
    "32013R1372": "https://eur-lex.europa.eu/eli/reg/2013/1372/oj/eng",
    "32017R0492": "https://eur-lex.europa.eu/eli/reg/2017/492/oj/eng",
}
EXPECTED_SOURCE_LOCATORS = {
    "32009R0988": {"OJ L 284, 30.10.2009, p. 57", "OJ L 284, 30.10.2009, p. 58"},
    "32010R1244": {"OJ L 338, 22.12.2010, p. 35"},
    "32012R1224": {"OJ L 349, 19.12.2012, p. 46"},
    "32013R0517": {"OJ L 158, 10.6.2013, p. 26"},
    "32013R1372": {"OJ L 346, 20.12.2013, p. 27"},
    "32017R0492": {"OJ L 76, 22.3.2017, p. 14"},
}
EXPECTED_SNAPSHOT_ENTRY_IDS = {
    "AT-a", "AT-b", "AT-c", "AT-d", "AT-e", "AT-f", "AT-g", "BG-1", "CZ-1",
    "DK-a", "DK-b", "DK-c", "EE-1", "FR-1", "HR-1", "HU-1", "LV-1", "PL-1",
    "PT-1", "SE-1", "SI-1", "SK-1", "UK-1",
}
EXPECTED_OFFICIAL_TEXT = {
    ("DK-c", "2013-01-08"): "Benefits in the event of death (accrued based on contributions to Arbejdsmarkedets Tillægspension related to the time after 1 January 2002) referred to in the Consolidated Act on Labour Market Supplementary Pension (Arbejdsmarkedets Tillægspension) 942:2009.",
    ("SE-1", "2010-05-01"): "Income-based pension and premium pension (Act 1998:674).",
    ("SE-1", "2013-01-08"): "Income pensions and premium pensions (Chapters 62 and 64 of the Social Insurance Code (2010:110)).",
}
EXPECTED_LOCATORS = {
    ("BG-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("CZ-1", "2014-01-01"): "OJ L 346, 20.12.2013, p. 27",
    ("DK-a", "2013-01-08"): "OJ L 349, 19.12.2012, p. 46",
    ("DK-b", "2013-01-08"): "OJ L 349, 19.12.2012, p. 46",
    ("DK-c", "2013-01-08"): "OJ L 349, 19.12.2012, p. 46",
    ("EE-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("FR-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("HR-1", "2013-07-01"): "OJ L 158, 10.6.2013, p. 26",
    ("LV-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("HU-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-a", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-a", "2014-01-01"): "OJ L 346, 20.12.2013, p. 27",
    ("AT-b", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-c", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-d", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-e", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-f", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("AT-g", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("PL-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("PT-1", "2011-01-11"): "OJ L 338, 22.12.2010, p. 35",
    ("SI-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("SK-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("SE-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
    ("SE-1", "2013-01-08"): "OJ L 349, 19.12.2012, p. 46",
    ("SE-1", "2017-04-11"): "OJ L 76, 22.3.2017, p. 14",
    ("UK-1", "2010-05-01"): "OJ L 284, 30.10.2009, p. 57",
}


class AnnexViiiSourceLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_and_canonical_entries_digest_are_valid(self):
        _assert_valid_candidate(self.ledger, self.schema)

    def test_snapshot_count_and_historical_versions_are_explicit(self):
        entries = self.ledger["entries"]
        self.assertEqual(len(entries), 26)
        active_at_snapshot = [entry for entry in entries if _in_half_open_interval(entry, date(2019, 7, 31))]
        self.assertEqual(len(active_at_snapshot), 23)
        self.assertEqual(len({entry["entry_id"] for entry in active_at_snapshot}), 23)
        self.assertEqual(
            [(entry["valid_from"], entry["valid_to"]) for entry in entries if entry["entry_id"] == "AT-a"],
            [("2010-05-01", "2014-01-01"), ("2014-01-01", None)],
        )
        self.assertEqual(
            [(entry["valid_from"], entry["valid_to"]) for entry in entries if entry["entry_id"] == "SE-1"],
            [("2010-05-01", "2013-01-08"), ("2013-01-08", "2017-04-11"), ("2017-04-11", None)],
        )

    def test_boundaries_are_half_open_and_dk_c_preserves_official_after_wording(self):
        entries = self.ledger["entries"]
        self.assertFalse(_is_active(entries, "BG-1", "2010-04-30"))
        self.assertTrue(_is_active(entries, "BG-1", "2010-05-01"))
        self.assertFalse(_is_active(entries, "PT-1", "2011-01-10"))
        self.assertTrue(_is_active(entries, "PT-1", "2011-01-11"))
        self.assertFalse(_is_active(entries, "DK-a", "2013-01-07"))
        self.assertTrue(_is_active(entries, "DK-a", "2013-01-08"))
        self.assertFalse(_is_active(entries, "HR-1", "2013-06-30"))
        self.assertTrue(_is_active(entries, "HR-1", "2013-07-01"))
        self.assertTrue(_is_active(entries, "AT-a", "2013-12-31"))
        self.assertTrue(_is_active(entries, "AT-a", "2014-01-01"))
        self.assertFalse(_is_active(entries, "CZ-1", "2013-12-31"))
        self.assertTrue(_is_active(entries, "CZ-1", "2014-01-01"))
        self.assertTrue(_is_active(entries, "SE-1", "2013-01-07"))
        self.assertTrue(_is_active(entries, "SE-1", "2013-01-08"))
        self.assertTrue(_is_active(entries, "SE-1", "2017-04-10"))
        self.assertTrue(_is_active(entries, "SE-1", "2017-04-11"))
        dk_c = next(entry for entry in entries if entry["entry_id"] == "DK-c")
        self.assertIn("time after 1 January 2002", dk_c["official_text"])
        self.assertNotIn("on or after 1 January 2002", dk_c["official_text"])

    def test_ledger_does_not_claim_matching_or_territorial_applicability(self):
        serialized = json.dumps(self.ledger, ensure_ascii=False).casefold()
        self.assertNotIn('"matched"', serialized)
        self.assertNotIn('"not_matched"', serialized)
        self.assertIn("united kingdom, eea and switzerland territorial applicability is not assessed", serialized)

    def test_schema_requires_scope_limitations_and_only_official_source_urls(self):
        validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        for mutation in ("remove_scope_limitations", "replace_url"):
            with self.subTest(mutation=mutation):
                candidate = json.loads(json.dumps(self.ledger))
                if mutation == "remove_scope_limitations":
                    del candidate["scope_limitations"]
                else:
                    candidate["entries"][0]["source"]["url"] = "https://example.invalid/source"
                with self.assertRaises(ValidationError):
                    validator.validate(candidate)

    def test_semantic_contract_fails_closed_on_integrity_and_source_mutations(self):
        for mutate in (_mutate_digest, _mutate_duplicate, _mutate_overlap, _mutate_gap, _mutate_source, _mutate_locator, _mutate_official_journal_locator, _mutate_text, _mutate_missing_row, _mutate_missing_act, _mutate_missing_source):
            with self.subTest(mutate=mutate.__name__):
                candidate = json.loads(json.dumps(self.ledger))
                mutate(candidate)
                with self.assertRaises((AssertionError, KeyError, ValueError, ValidationError)):
                    _assert_valid_candidate(candidate, self.schema)

    def test_contract_rejects_dates_outside_documented_snapshot_or_review(self):
        for field, value in (("valid_from", "2019-08-01"), ("valid_to", "2026-11-08")):
            with self.subTest(field=field):
                candidate = json.loads(json.dumps(self.ledger))
                candidate["entries"][0][field] = value
                candidate["entries_sha256"] = _entries_digest(candidate["entries"])
                with self.assertRaises((AssertionError, KeyError, ValueError)):
                    _assert_semantic_contract(candidate)


def _in_half_open_interval(entry, as_of):
    start = date.fromisoformat(entry["valid_from"])
    end = date.fromisoformat(entry["valid_to"]) if entry["valid_to"] else None
    return start <= as_of and (end is None or as_of < end)


def _is_active(entries, entry_id, as_of):
    candidate_date = date.fromisoformat(as_of)
    return any(_in_half_open_interval(entry, candidate_date) for entry in entries if entry["entry_id"] == entry_id)


def _entries_digest(entries):
    canonical_entries = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical_entries).hexdigest().upper()


def _assert_valid_candidate(ledger, schema):
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(ledger)
    _assert_semantic_contract(ledger)


def _assert_semantic_contract(ledger):
    entries = ledger["entries"]
    assert ledger["catalogue_id"] == "eu-annex-viii-part-2-source-ledger-v0.4"
    assert ledger["schema_version"] == "eu-annex-viii-part-2-source-ledger/v0.4"
    assert ledger["status"] == "source_ledger_only"
    assert ledger["documented_snapshot_only"] is True
    assert ledger["scope_limitations"]
    assert len(entries) == 26
    assert ledger["entries_sha256"] == _entries_digest(entries)
    snapshot = date.fromisoformat(ledger["snapshot_as_of"])
    reviewed = date.fromisoformat(ledger["reviewed_on"])
    seen_keys = set()
    observed_sources = set()
    by_id = {}
    for entry in entries:
        key = (entry["entry_id"], entry["valid_from"])
        assert key not in seen_keys
        seen_keys.add(key)
        observed_sources.add(entry["source"]["celex"])
        assert entry["source"]["celex"] in EXPECTED_SOURCE_URLS
        assert entry["source"]["url"] == EXPECTED_SOURCE_URLS[entry["source"]["celex"]]
        assert entry["source"]["official_journal_locator"] == EXPECTED_LOCATORS[key]
        assert entry["source"]["official_journal_locator"] in EXPECTED_SOURCE_LOCATORS[entry["source"]["celex"]]
        assert date.fromisoformat(entry["valid_from"]) <= snapshot
        assert date.fromisoformat(entry["valid_from"]) <= reviewed
        if entry["valid_to"] is not None:
            assert date.fromisoformat(entry["valid_from"]) < date.fromisoformat(entry["valid_to"])
            assert date.fromisoformat(entry["valid_to"]) <= snapshot
            assert date.fromisoformat(entry["valid_to"]) <= reviewed
        by_id.setdefault(entry["entry_id"], []).append(entry)
        expected_text = EXPECTED_OFFICIAL_TEXT.get(key)
        if expected_text is not None:
            assert entry["official_text"] == expected_text
    assert observed_sources == set(EXPECTED_SOURCE_URLS)
    assert seen_keys == set(EXPECTED_LOCATORS)
    snapshot_entries = [entry for entry in entries if _in_half_open_interval(entry, snapshot)]
    assert len(snapshot_entries) == 23
    assert {entry["entry_id"] for entry in snapshot_entries} == EXPECTED_SNAPSHOT_ENTRY_IDS
    for versions in by_id.values():
        versions.sort(key=lambda entry: entry["valid_from"])
        for previous, current in zip(versions, versions[1:]):
            assert previous["valid_to"] == current["valid_from"]


def _mutate_digest(candidate):
    candidate["entries_sha256"] = "0" * 64


def _mutate_duplicate(candidate):
    candidate["entries"][1]["entry_id"] = candidate["entries"][0]["entry_id"]
    candidate["entries"][1]["valid_from"] = candidate["entries"][0]["valid_from"]
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_overlap(candidate):
    _entry(candidate, "SE-1", "2013-01-08")["valid_from"] = "2013-01-07"
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_gap(candidate):
    _entry(candidate, "SE-1", "2013-01-08")["valid_from"] = "2013-01-09"
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_source(candidate):
    candidate["entries"][0]["source"]["celex"] = "32000R0001"
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_locator(candidate):
    candidate["entries"][0]["source"]["url"] = "https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng?mutated"
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_official_journal_locator(candidate):
    _entry(candidate, "SE-1", "2010-05-01")["source"]["official_journal_locator"] = "OJ L 284, 30.10.2009, p. 58"
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_text(candidate):
    candidate["entries"][4]["official_text"] = "Benefits on or after 1 January 2002."
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_missing_row(candidate):
    candidate["entries"].pop()
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_missing_act(candidate):
    entry = _entry(candidate, "PT-1", "2011-01-11")
    entry["source"]["celex"] = "32009R0988"
    entry["source"]["url"] = EXPECTED_SOURCE_URLS["32009R0988"]
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _mutate_missing_source(candidate):
    del candidate["entries"][0]["source"]
    candidate["entries_sha256"] = _entries_digest(candidate["entries"])


def _entry(candidate, entry_id, valid_from):
    return next(entry for entry in candidate["entries"] if entry["entry_id"] == entry_id and entry["valid_from"] == valid_from)


if __name__ == "__main__":
    unittest.main()
