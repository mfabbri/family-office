import copy
import json
import tempfile
import unittest
from pathlib import Path

from family_office_engine.services.wealth_strategy import WealthStrategyError, build_wealth_strategy

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_INPUT = REPOSITORY_ROOT / "family-office-engine" / "examples" / "wealth-strategy-input-sample.json"


class WealthStrategyTest(unittest.TestCase):
    def test_builds_ranked_strategy_packages_from_source_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = build_wealth_strategy(SAMPLE_INPUT, root / "wealth-strategy.json", **_source_paths(root))

            self.assertEqual(result["schema_version"], "wealth-strategy/v1")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["summary"]["package_count"], 3)
            self.assertEqual(result["ranking"][0]["package_id"], "balanced_liquidity_first")
            self.assertEqual(result["packages"][0]["weighted_score"], "3.80")
            self.assertRegex(result["reproducibility"]["content_hash"], r"^[0-9a-f]{64}$")

    def test_missing_required_source_blocks_only_affected_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = _source_paths(root)
            paths["work_exit_snapshot_path"] = root / "missing-work-exit.json"

            result = build_wealth_strategy(SAMPLE_INPUT, root / "wealth-strategy.json", **paths)

            self.assertEqual(result["status"], "partial")
            blocked = next(item for item in result["packages"] if item["package_id"] == "balanced_liquidity_first")
            self.assertEqual(blocked["status"], "blocked_source")
            self.assertIn("missing_source_snapshot", {gap["code"] for gap in blocked["data_gaps"]})
            self.assertEqual(result["summary"]["comparable_package_count"], 2)

    def test_incompatible_components_block_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["packages"][0]["components"].append(
                {
                    "component_id": "portfolio_foreign_declarative",
                    "source_key": "tax_aware_portfolio",
                    "selector": {"collection": "options", "id_field": "option_id", "id": "foreign_declarative_low_turnover"},
                }
            )
            input_path = _write_json(root / "input.json", data)

            result = build_wealth_strategy(input_path, root / "wealth-strategy.json", **_source_paths(root))

            package = next(item for item in result["packages"] if item["package_id"] == "balanced_liquidity_first")
            self.assertEqual(package["status"], "blocked_source")
            self.assertIn("incompatible_components", {gap["code"] for gap in package["data_gaps"]})

    def test_requires_two_to_four_packages(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
            data["packages"] = data["packages"][:1]

            with self.assertRaisesRegex(WealthStrategyError, "2 to 4"):
                build_wealth_strategy(_write_json(root / "input.json", data), root / "out.json", **_source_paths(root))


def _source_paths(root: Path) -> dict:
    return {
        "liquidity_plan_snapshot_path": _write_json(root / "liquidity.json", _snapshot("liquidity-plan/v1", summary={"status": "complete"})),
        "tax_aware_portfolio_snapshot_path": _write_json(
            root / "tax.json",
            _snapshot(
                "tax-aware-portfolio/v1",
                options=[
                    {"option_id": "domestic_admin_balanced", "status": "complete", "totals": {"net_expected_return": "3430.00"}},
                    {"option_id": "foreign_declarative_low_turnover", "status": "complete", "totals": {"net_expected_return": "4520.00"}},
                ],
            ),
        ),
        "cross_border_it_es_snapshot_path": _write_json(root / "cross.json", _snapshot("cross-border-it-es/v1")),
        "real_estate_plan_snapshot_path": _write_json(
            root / "real-estate.json",
            _snapshot(
                "real-estate-plan/v1",
                alternatives=[
                    {"strategy": "sell", "status": "complete", "liquidity_amount": "229900.00"},
                    {"strategy": "hold", "status": "complete", "annual_net_cashflow_or_proceeds": "-5100.00"},
                ],
            ),
        ),
        "protection_gap_snapshot_path": _write_json(root / "protection.json", _snapshot("protection-gap/v1", summary={"total_shortfall": "70000.00"})),
        "estate_plan_snapshot_path": _write_json(
            root / "estate.json",
            _snapshot(
                "estate-plan/v2",
                scenarios=[
                    {"scenario_id": "equalized_children_with_spouse_cash", "status": "complete", "reserve_conflicts": []},
                    {"scenario_id": "will_home_to_spouse_cash_to_children", "status": "partial", "reserve_conflicts": [{"code": "child_reserved_share_shortfall"}]},
                ],
            ),
        ),
        "work_exit_snapshot_path": _write_json(root / "work-exit.json", _snapshot("work-exit-feasibility/v1", first_sustainable_exit_date="2039-01-01")),
    }


def _snapshot(schema_version: str, **extra: object) -> dict:
    data = {
        "schema_version": schema_version,
        "record_type": "SyntheticSnapshot",
        "status": "complete",
        "reproducibility": {"hash_algorithm": "sha256", "content_hash": "0" * 64},
        "data_gaps": [],
    }
    data.update(copy.deepcopy(extra))
    return data


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
