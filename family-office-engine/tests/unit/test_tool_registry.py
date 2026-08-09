import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.tool_registry import (
    SCHEMA_VERSION,
    ToolRegistryError,
    build_tool_registry,
    invoke_registered_tool,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROTECTION_SAMPLE = REPOSITORY_ROOT / "family-office-engine" / "examples" / "protection-gap-sample.json"


class ToolRegistryTest(unittest.TestCase):
    def test_builds_valid_registry_snapshot(self):
        snapshot = build_tool_registry()

        self.assertEqual(snapshot["schema_version"], SCHEMA_VERSION)
        self.assertEqual(snapshot["status"], "complete")
        self.assertGreaterEqual(snapshot["tool_count"], 10)
        self.assertEqual(snapshot["tool_count"], len(snapshot["tools"]))
        self.assertTrue(snapshot["policy"]["llm_may_invoke_only_registered_tools"])
        self.assertTrue(snapshot["policy"]["llm_must_not_calculate_tax_pension_financial_values"])
        self.assertRegex(snapshot["reproducibility"]["content_hash"], r"^[0-9a-f]{64}$")
        tool_ids = {tool["tool_id"] for tool in snapshot["tools"]}
        self.assertIn("planning.wealth_strategy.build", tool_ids)
        self.assertIn("planning.work_exit_feasibility.build", tool_ids)
        self.assertIn("knowledge.citations.search", tool_ids)

    def test_writes_registry_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "tool-registry.json"

            snapshot = build_tool_registry(output_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(snapshot["schema_version"], "tool-registry/v1")

    def test_unknown_tool_is_rejected(self):
        with self.assertRaisesRegex(ToolRegistryError, "Unknown registered tool"):
            invoke_registered_tool("planning.unknown.build", "unknown/v1", {})

    def test_incompatible_requested_output_version_is_rejected(self):
        with self.assertRaisesRegex(ToolRegistryError, "produces protection-gap/v1"):
            invoke_registered_tool(
                "planning.protection_gap.build",
                "protection-gap/v2",
                {"input_path": PROTECTION_SAMPLE, "output_path": "unused.json"},
            )

    def test_invokes_registered_tool_with_validated_parameters(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "protection.json"

            result = invoke_registered_tool(
                "planning.protection_gap.build",
                "protection-gap/v1",
                {"input_path": PROTECTION_SAMPLE, "output_path": output_path},
            )

            self.assertEqual(result["schema_version"], "tool-invocation/v1")
            self.assertEqual(result["tool"]["actual_output_schema_version"], "protection-gap/v1")
            self.assertEqual(result["output"]["schema_version"], "protection-gap/v1")
            self.assertTrue(output_path.exists())

    def test_missing_required_parameter_is_rejected(self):
        with self.assertRaisesRegex(ToolRegistryError, "Missing required parameters"):
            invoke_registered_tool("planning.protection_gap.build", "protection-gap/v1", {"input_path": PROTECTION_SAMPLE})


if __name__ == "__main__":
    unittest.main()
