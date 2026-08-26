import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from family_office_engine.cli.main import main
from family_office_engine.services.execution_executor import ExecutionExecutorError, build_evidence_bundle, execute_plan
from family_office_engine.services.tool_registry import build_tool_registry


class ExecutionExecutorTest(unittest.TestCase):
    def test_executes_registered_tool_and_keeps_only_value_hashes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            index_path = Path(tmp_dir) / "index.json"
            index_path.write_text(json.dumps({"schema_version": "citation-index/v1", "as_of_date": "2026-01-01", "citations": []}), encoding="utf-8")
            request = _request(index_path)

            snapshot = execute_plan(request)

        self.assertEqual("evidence-bundle/v1", snapshot["schema_version"])
        self.assertEqual("complete", snapshot["status"])
        self.assertEqual("succeeded", snapshot["nodes"][0]["execution_state"])
        self.assertNotIn("value", snapshot["sources"][0])
        self.assertEqual(64, len(snapshot["sources"][0]["value_hash"]))

    def test_partial_failure_and_safe_retry_are_visible(self):
        request = _request(Path("synthetic-index.json"), node_count=2)
        calls = []

        def invoke(tool_id, schema_version, parameters):
            calls.append(tool_id)
            if len(calls) == 1:
                raise ValueError("temporary failure")
            if len(calls) >= 3:
                raise ValueError("terminal failure")
            return {"output": {"schema_version": schema_version, "status": "complete", "data_gaps": []}, "data_gaps": []}

        with patch("family_office_engine.services.execution_executor.invoke_registered_tool", side_effect=invoke):
            snapshot = execute_plan(request)

        self.assertEqual("partial", snapshot["status"])
        self.assertEqual(2, snapshot["nodes"][0]["attempts"])
        self.assertEqual("succeeded", snapshot["nodes"][0]["execution_state"])
        self.assertEqual("failed", snapshot["nodes"][1]["execution_state"])
        self.assertEqual(2, snapshot["nodes"][1]["attempts"])

    def test_rejects_stale_version_and_marks_missing_authorization_skipped(self):
        stale = _request(Path("synthetic-index.json"))
        stale["execution_plan"]["tool_registry"]["content_hash"] = "0" * 64
        with self.assertRaisesRegex(ExecutionExecutorError, "lineage is stale"):
            execute_plan(stale)

        denied = _request(Path("synthetic-index.json"))
        denied["authorization_grants"] = {}
        snapshot = execute_plan(denied)
        self.assertEqual("failed", snapshot["status"])
        self.assertEqual("skipped", snapshot["nodes"][0]["execution_state"])
        self.assertEqual("authorization_required", snapshot["errors"][0]["message"])

    def test_writes_bundle_and_cli_smoke(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            index_path = root / "index.json"
            request_path = root / "request.json"
            output_path = root / "evidence.json"
            index_path.write_text(json.dumps({"schema_version": "citation-index/v1", "as_of_date": "2026-01-01", "citations": []}), encoding="utf-8")
            request_path.write_text(json.dumps(_request(index_path)), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["orchestration", "execute", "--input", str(request_path), "--output", str(output_path)])

            self.assertEqual(0, exit_code)
            self.assertTrue(output_path.exists())
            self.assertIn("complete 1 nodes", stdout.getvalue())
            self.assertEqual("complete", build_evidence_bundle(request_path, root / "second.json")["status"])


def _request(index_path: Path, node_count: int = 1) -> dict:
    registry = build_tool_registry()
    lineage = {"schema_version": registry["schema_version"], "content_hash": registry["reproducibility"]["content_hash"]}
    tool = next(item for item in registry["tools"] if item["tool_id"] == "knowledge.citations.search")
    nodes = []
    values = {}
    for number in range(node_count):
        node_id = f"search_{number}"
        nodes.append({"node_id": node_id, "tool_id": tool["tool_id"], "depends_on": [], "input_bindings": {"index_path": {"source": "citation_index", "reference": str(index_path), "sensitivity": "ordinary"}}, "output_schema_version": tool["output_schema_version"], "authorization_policy": tool["authorization_policy"]})
        values[node_id] = {"index_path": {"reference": str(index_path), "value": str(index_path)}}
    plan_core = {"plan_id": "synthetic-search-plan", "tool_registry": lineage, "nodes": nodes, "execution_order": [node["node_id"] for node in nodes]}
    plan = {"schema_version": "execution-plan/v1", "record_type": "ExecutionPlan", "status": "ready", **plan_core, "reproducibility": {"content_hash": "a" * 64}}
    return {"schema_version": "execution-request/v1", "record_type": "ExecutionRequest", "execution_id": "synthetic-execution", "execution_plan": plan, "authorization_grants": {node["node_id"]: tool["authorization_policy"] for node in nodes}, "execution_policy": {"max_attempts": 2, "timeout_seconds": 30}, "binding_values": values}
