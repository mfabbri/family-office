from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("validate-codex-model-routing.py")
spec = importlib.util.spec_from_file_location("fo_model_validator", path)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


class ModelRoutingV4Tests(unittest.TestCase):
    def test_historical_route_3_1_retained_only_while_blocked(self):
        route = {"policy_version": "3.1", "tier": "critical", "agent": "fo_normative_reviewer", "model": "gpt-5.6-sol", "reasoning_effort": "xhigh"}
        self.assertIn("legacy", validator.validate_route(route, "blocked"))
        with self.assertRaises(SystemExit):
            validator.validate_route(route, "in_progress")

    def test_sol_regular_review(self):
        route = {"policy_version": "4.0", "tier": "critical", "agent": "fo_normative_reviewer", "model": "gpt-6.2-sol", "reasoning_effort": "high"}
        self.assertEqual(validator.validate_route(route, "selected"), "4.0")

    def test_astra_escalation_requires_specific_budget(self):
        route = {"policy_version": "4.0", "tier": "critical", "agent": "fo_normative_escalation", "model": "gpt-6.2-astra", "reasoning_effort": "high"}
        with self.assertRaises(SystemExit):
            validator.validate_route(route, "selected")
        route["delegation_budget"] = {"max_events": 3, "authorization": "explicit", "scope": "specific law conflict", "blocker": "documented"}
        self.assertEqual(validator.validate_route(route, "selected"), "4.0")

    def test_refuses_wrong_model_or_tier(self):
        route = {"policy_version": "4.0", "tier": "medium", "agent": "fo_normative_reviewer", "model": "gpt-6.2-sol", "reasoning_effort": "high"}
        with self.assertRaises(SystemExit):
            validator.validate_route(route, "selected")


if __name__ == "__main__":
    unittest.main()
