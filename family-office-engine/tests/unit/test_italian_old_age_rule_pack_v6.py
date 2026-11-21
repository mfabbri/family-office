"""Synthetic tests for the non-active branch-specific Italian Rules v6 candidate."""
import json
import unittest
from pathlib import Path
from family_office_engine.services.italian_old_age_eligibility import ItalianOldAgeEligibilityError, assess_italian_old_age_eligibility
ROOT=Path(__file__).resolve().parents[3]
RULES=ROOT/"family-office-rules/italy/2026"
V2=RULES/"inps-old-age-eligibility.json"
V3=RULES/"inps-old-age-eligibility-v3.json"
V4=RULES/"inps-old-age-eligibility-v4.json"
V5=RULES/"inps-old-age-eligibility-v5.json"
V6=RULES/"inps-old-age-eligibility-v6.json"
KNOWLEDGE=ROOT/"family-office-knowledge/pensions/italian-pension-adjustment-2027-2028-exceptions-v0.4.md"
CATALOG=ROOT/"family-office-knowledge/sources/citation-catalog.json"
class ItalianOldAgeRulePackV6Tests(unittest.TestCase):
 def test_heavy_work_periods_are_explicit_alternatives_with_primary_chain(self):
  pack=json.loads(V6.read_text(encoding="utf-8")); branch=next(b for b in pack["adjustment_exception_contract"]["exception_conditions"]["alternative_evidence_branches"] if b["branch_id"]=="heavy_or_arduous_work_dlgs67_2011")
  self.assertEqual(branch["period_requirement_operator"],"any_of")
  alternatives=branch["period_requirement_alternatives"]
  self.assertEqual([x["alternative_id"] for x in alternatives],["seven_of_last_ten_years","at_least_half_of_total_working_life"])
  self.assertIn("gazzetta.l-232-2016.16g00242",branch["source_refs"])
  law=next(s for s in pack["source_refs"] if s["source_id"]=="gazzetta.l-232-2016.16g00242")
  self.assertEqual(law["legal_role"],"primary_legislation")
  self.assertEqual(law["provision_periods"][0]["legal_effective_from"],"2017-01-01")
  self.assertEqual(branch["computation_rule"]["fully_figurative_periods_count"],"excluded")
 def test_inps_circular_metadata_has_correct_period_and_title(self):
  cat=json.loads(CATALOG.read_text(encoding="utf-8")); citation=next(c for c in cat["citations"] if c["citation_id"]=="it.inps.circular-28-2026")
  self.assertIn("2027-2028",citation["title"]); self.assertEqual(citation["valid_from"],"2027-01-01"); self.assertEqual(citation["valid_to"],"2028-12-31")
 def test_v06_preserves_three_separate_age_references_and_no_personal_result(self):
  pack=json.loads(V6.read_text(encoding="utf-8")); c=pack["adjustment_exception_contract"]; branches=c["exception_conditions"]["alternative_evidence_branches"]
  ages=[(b["administrative_age_reference"]["years"],b["administrative_age_reference"]["months"]) for b in branches]
  self.assertEqual(ages,[(66,7),(67,0),(66,7)])
  self.assertTrue(c["no_individual_outcome"]); self.assertEqual(c["exception_conditions"]["missing_or_conflicting_evidence"],"not_assessed_with_blocking_data_gaps")
 def test_knowledge_v04_explains_alternatives_and_keeps_gaps(self):
  note=KNOWLEDGE.read_text(encoding="utf-8")
  self.assertIn("legge 232/2016",note); self.assertIn("periodi sono alternativi",note); self.assertIn("periodi totalmente figurativi",note); self.assertIn("not_assessed + data_gaps",note)
  self.assertIn("it.l-232-2016.original",json.dumps(json.loads(CATALOG.read_text(encoding="utf-8"))["documents"]))
 def test_knowledge_heavy_work_table_requires_alternative_periods(self):
  """Prevents prose and the administrative table from diverging on OR vs AND."""
  note=KNOWLEDGE.read_text(encoding="utf-8")
  rows=[line for line in note.splitlines() if line.startswith("| Lavori faticosi e pesanti |")]
  self.assertEqual(len(rows),1,"Expected exactly one heavy-work administrative row")
  cells=rows[0].split("|")
  self.assertEqual(len(cells),6)
  self.assertEqual(cells[2].strip(),"Categorie e condizioni D.Lgs. 67/2011; 7 anni negli ultimi 10 oppure almeno meta' della vita lavorativa complessiva; almeno 30 anni contributivi")
 def test_engine_rejects_candidate_and_all_prior_packs_stay_immutable(self):
  with self.assertRaises(ItalianOldAgeEligibilityError): assess_italian_old_age_eligibility({},V6,"2026-10-13")
  self.assertEqual(json.loads(V2.read_text(encoding="utf-8"))["rule_pack_id"],"it.inps-old-age-eligibility.2026-2028.v2")
  self.assertEqual(json.loads(V3.read_text(encoding="utf-8"))["rule_pack_id"],"it.inps-old-age-eligibility.2026-2028.v3")
  self.assertEqual(json.loads(V4.read_text(encoding="utf-8"))["rule_pack_id"],"it.inps-old-age-eligibility.2026-2028.v4")
  self.assertEqual(json.loads(V5.read_text(encoding="utf-8"))["rule_pack_id"],"it.inps-old-age-eligibility.2026-2028.v5")
if __name__=="__main__": unittest.main()
