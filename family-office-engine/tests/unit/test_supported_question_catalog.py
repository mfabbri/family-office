import unittest

from family_office_engine.services.supported_question_catalog import (
    ASSESSMENT_SCHEMA_VERSION,
    CATALOG_SCHEMA_VERSION,
    assess_question_capability,
    build_supported_question_catalog,
)
from family_office_engine.services.tool_registry import build_tool_registry


class SupportedQuestionCatalogTest(unittest.TestCase):
    def test_catalog_covers_each_registered_tool_and_is_reproducible(self):
        catalog = build_supported_question_catalog()
        repeat = build_supported_question_catalog()

        self.assertEqual(CATALOG_SCHEMA_VERSION, catalog["schema_version"])
        self.assertEqual(catalog["reproducibility"]["content_hash"], repeat["reproducibility"]["content_hash"])
        available_tools = {
            tool_id
            for intent in catalog["intents"]
            if intent["capability_status"] == "available"
            for tool_id in intent["required_tools"]
        }
        registry_tools = {tool["tool_id"] for tool in build_tool_registry()["tools"]}
        self.assertEqual(registry_tools, available_tools)
        available_tool_records = [
            tool_id
            for intent in catalog["intents"]
            if intent["capability_status"] == "available"
            for tool_id in intent["required_tools"]
        ]
        self.assertEqual(len(available_tool_records), len(set(available_tool_records)))

    def test_investment_opportunity_requires_comparison_and_declared_gaps(self):
        result = assess_question_capability(["investment_opportunity"])

        self.assertEqual(ASSESSMENT_SCHEMA_VERSION, result["schema_version"])
        self.assertFalse(result["executable"])
        self.assertIn("minimum_data_missing", {problem["code"] for problem in result["problems"]})
        self.assertEqual(["planning.investment_opportunity_comparison.build"], result["intent_results"][0]["required_tools"])

    def test_missing_data_is_explicit_for_available_capability(self):
        result = assess_question_capability(["liquidity_and_cashflow"], ["planning-goals/v1"])

        self.assertFalse(result["executable"])
        self.assertIn("minimum_data_missing", {problem["code"] for problem in result["problems"]})
        self.assertEqual(["asset-availability/v1", "net-worth/v1"], result["intent_results"][0]["missing_data"])

    def test_overlap_unknown_and_out_of_scope_are_not_silently_accepted(self):
        result = assess_question_capability(
            ["retirement_and_work_exit", "cross_border_tax_and_reporting", "not_a_catalog_intent"]
        )

        codes = {problem["code"] for problem in result["problems"]}
        self.assertIn("intent_unsupported", codes)
        self.assertIn("intent_overlap_requires_clarification", codes)

        professional = assess_question_capability(["professional_advice_or_out_of_scope"])
        self.assertIn("professional_or_out_of_scope_request", {problem["code"] for problem in professional["problems"]})


if __name__ == "__main__":
    unittest.main()
