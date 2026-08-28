import json,tempfile,unittest
from pathlib import Path
from family_office_engine.services.decision_memory import DecisionMemoryError,apply_decision_memory,update_decision_memory
class DecisionMemoryTest(unittest.TestCase):
 def test_update_revoke_conflict_and_no_raw_text(self):
  first=apply_decision_memory(_input())
  second=apply_decision_memory(_input(),first)
  self.assertEqual("superseded",second["entries"][0]["state"]); self.assertEqual(2,second["entries"][1]["version"])
  revoked=apply_decision_memory({**_input(),"action":"revoke","expected_current_version":2},second); self.assertEqual("revoked",revoked["entries"][-1]["state"])
  self.assertEqual("conflict",apply_decision_memory({**_input(),"expected_current_version":99},second)["status"])
  with self.assertRaisesRegex(DecisionMemoryError,"conversation text"): apply_decision_memory({**_input(),"conversation_text":"secret"})
 def test_writes_private_memory(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); inp=root/"input.json"; mem=root/"memory.json"; inp.write_text(json.dumps(_input()),encoding="utf-8")
   self.assertTrue(update_decision_memory(inp,mem)["policy"]["workspace_private_only"]); self.assertTrue(mem.exists())
def _input():
 h="a"*64
 return {"schema_version":"decision-memory-input/v1","record_type":"DecisionMemoryInput","decision_key":"synthetic-decision","action":"record","validated_lineage":{n:{"schema_version":v,"content_hash":h} for n,v in {"scenario":"decision-scenario/v2","evidence_bundle":"evidence-bundle/v1","advisory_response":"advisory-response/v1","answer_confidence":"answer-confidence/v1"}.items()}}
