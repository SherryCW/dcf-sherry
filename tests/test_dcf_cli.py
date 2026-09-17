from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dcf_cli.py"
SPEC = importlib.util.spec_from_file_location("dcf_cli", SCRIPT)
assert SPEC and SPEC.loader
DCF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DCF)


def _load(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class DcfCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = _load("synthetic-consumer-case.json")

    def test_synthetic_case_passes_validation(self) -> None:
        self.assertEqual(DCF.validate_case(self.case), [])

    def test_run_is_finite_and_probability_weighted(self) -> None:
        result = DCF.run_case(self.case)
        values = result["scenarios"]
        expected = sum(item["probability"] * item["value_per_share"] for item in values.values())
        self.assertAlmostEqual(result["probability_weighted_value_per_share"], expected, places=10)
        self.assertTrue(math.isfinite(expected))
        self.assertGreater(values["bull"]["value_per_share"], values["base"]["value_per_share"])
        self.assertGreater(values["base"]["value_per_share"], values["bear"]["value_per_share"])

    def test_fcff_bridge_reconciles(self) -> None:
        result = DCF.scenario_dcf(self.case, "base")
        for row in result["forecast"]:
            reconstructed = row["nopat"] + row["depreciation"] - row["capex"] - row["delta_nwc"]
            self.assertAlmostEqual(row["fcff"], reconstructed, places=10)

    def test_equity_bridge_reconciles(self) -> None:
        result = DCF.scenario_dcf(self.case, "base")
        bridge = self.case["bridge"]
        expected = (
            result["enterprise_value"]
            - bridge["net_debt"]
            - bridge["minority_interest"]
            + bridge["non_operating_investments"]
        )
        self.assertAlmostEqual(result["equity_value"], expected, places=10)
        self.assertAlmostEqual(result["value_per_share"], expected / bridge["diluted_shares"], places=10)

    def test_wacc_must_exceed_growth(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["scenarios"]["base"]["wacc"] = 0.03
        broken["scenarios"]["base"]["terminal_growth"] = 0.03
        with self.assertRaises(DCF.CaseError):
            DCF.validate_case(broken)

    def test_probabilities_must_sum_to_one(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["scenarios"]["bull"]["probability"] = 0.20
        with self.assertRaises(DCF.CaseError):
            DCF.validate_case(broken)

    def test_sensitivity_center_matches_base(self) -> None:
        base = DCF.scenario_dcf(self.case, "base")["value_per_share"]
        table = DCF.sensitivity(self.case)
        self.assertAlmostEqual(table["rows"][2]["values"][2], base, places=10)

    def test_reverse_dcf_recovers_model_growth(self) -> None:
        base = DCF.scenario_dcf(self.case, "base")
        reverse = DCF.implied_terminal_growth(self.case, "base", base["value_per_share"])
        self.assertAlmostEqual(
            reverse["implied_terminal_growth"],
            self.case["scenarios"]["base"]["terminal_growth"],
            places=8,
        )


class ScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.growth = _load("synthetic-growth-screen.json")
        self.cyclical = _load("synthetic-cyclical-screen.json")

    def test_peg_denominator_is_forward_never_historical(self) -> None:
        result = DCF.screen_case(self.growth)
        denominator = result["peg_denominator"]
        self.assertEqual(denominator["basis"], "forward_consensus_eps_growth")
        self.assertIn("never", denominator["note"])
        self.assertIs(result["historical_verification"]["used_as_peg_denominator"], False)

    def test_peg_matches_forward_eps_ratio(self) -> None:
        result = DCF.screen_case(self.growth)
        price = self.growth["price"]
        trailing = self.growth["trailing_eps"]
        for name in DCF.REQUIRED_SCENARIOS:
            forward = self.growth["forward_eps"][name]
            growth = forward / trailing - 1.0
            expected_peg = (price / forward) / (growth * 100.0)
            self.assertAlmostEqual(result["multiples"]["peg"][name], expected_peg, places=10)

    def test_peg_is_cheap_and_still_cyclical(self) -> None:
        result = DCF.screen_case(self.cyclical)
        self.assertLess(result["multiples"]["peg"]["base"], 0.5)
        self.assertEqual(result["classification"], "cyclical_normalize")
        self.assertEqual(result["required_next_step"], "normalized_earnings")
        self.assertIn("cyclical", result["red_flags"])

    def test_structural_growth_requires_quality_evidence(self) -> None:
        stripped = json.loads(json.dumps(self.growth))
        stripped.pop("quality_metrics")
        result = DCF.screen_case(stripped)
        self.assertEqual(result["classification"], "undetermined")
        self.assertNotEqual(result["status"], "PASS")

    def test_missing_quality_flag_is_a_hard_error(self) -> None:
        broken = json.loads(json.dumps(self.growth))
        broken["quality_flags"].pop("low_base")
        with self.assertRaises(DCF.CaseError):
            DCF.validate_screen_input(broken)

    def test_quality_flag_overrides_cheap_peg(self) -> None:
        flagged = json.loads(json.dumps(self.growth))
        flagged["quality_flags"]["one_off_boost"] = True
        result = DCF.screen_case(flagged)
        self.assertEqual(result["classification"], "pseudo_growth")
        self.assertEqual(result["status"], "BLOCKED")

    def test_screen_never_returns_a_price(self) -> None:
        result = DCF.screen_case(self.growth)
        self.assertNotIn("value_per_share", result)
        self.assertNotIn("enterprise_value", result)

    def test_non_positive_earnings_block_peg(self) -> None:
        broken = json.loads(json.dumps(self.growth))
        broken["trailing_eps"] = -1.0
        with self.assertRaises(DCF.CaseError):
            DCF.validate_screen_input(broken)


class GrowthQualityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = _load("synthetic-growth-case.json")

    def test_all_quality_gates_pass_on_designed_case(self) -> None:
        result = DCF.run_case(self.case)
        self.assertEqual(result["growth_quality_summary"]["failed"], 0)
        self.assertEqual(result["growth_quality_summary"]["warned"], 0)
        self.assertTrue(result["growth_quality_summary"]["supplied"])

    def test_terminal_growth_above_reinvestment_capacity_warns(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["scenarios"]["base"]["terminal_growth"] = 0.075
        result = DCF.run_case(broken)
        warned = [item for item in result["growth_quality_checks"] if item["check"].startswith("Q2")]
        self.assertTrue(any(item["status"] == "warn" for item in warned))

    def test_roic_below_wacc_blocks(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["growth_quality"]["roic"] = 0.05
        result = DCF.run_case(broken)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertGreater(result["growth_quality_summary"]["failed"], 0)

    def test_duration_beyond_horizon_warns(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["growth_quality"]["high_growth_years"] = 9
        result = DCF.run_case(broken)
        duration = [item for item in result["growth_quality_checks"] if item["check"].startswith("Q6")]
        self.assertTrue(any(item["status"] == "warn" for item in duration))

    def test_low_cash_conversion_warns(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["growth_quality"]["fcff_conversion"] = 0.2
        result = DCF.run_case(broken)
        self.assertTrue(any(item["check"].startswith("Q3") and item["status"] == "warn" for item in result["growth_quality_checks"]))

    def test_missing_growth_quality_field_is_a_hard_error(self) -> None:
        broken = json.loads(json.dumps(self.case))
        broken["growth_quality"].pop("reinvestment_rate")
        with self.assertRaises(DCF.CaseError):
            DCF.validate_case(broken)

    def test_case_without_growth_quality_is_unchanged(self) -> None:
        plain = _load("synthetic-consumer-case.json")
        result = DCF.run_case(plain)
        self.assertEqual(result["growth_quality_checks"], [])
        self.assertIs(result["growth_quality_summary"]["supplied"], False)


class ReverseDurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = _load("synthetic-growth-case.json")

    def test_extension_of_zero_years_equals_base_value(self) -> None:
        base = DCF.scenario_dcf(self.case, "base")["enterprise_value"]
        self.assertAlmostEqual(DCF._extended_enterprise_value(self.case, "base", 0, 0.18), base, places=6)

    def test_value_increases_with_extension_years(self) -> None:
        values = [DCF._extended_enterprise_value(self.case, "base", years, 0.18) for years in range(0, 8)]
        for earlier, later in zip(values, values[1:]):
            self.assertGreater(later, earlier)

    def test_implied_duration_is_positive_at_a_price_above_the_horizon_value(self) -> None:
        base = DCF.scenario_dcf(self.case, "base")["value_per_share"]
        higher = DCF.implied_terminal_growth(self.case, "base", base * 1.5, 0.18)
        self.assertTrue(higher["reachable"])
        self.assertGreater(higher["implied_growth_duration_years"], 0)

    def test_price_at_horizon_value_needs_no_extension(self) -> None:
        base = DCF.scenario_dcf(self.case, "base")
        at_value = DCF.implied_terminal_growth(self.case, "base", base["value_per_share"], 0.18)
        self.assertAlmostEqual(at_value["implied_growth_duration_years"], 0.0, places=6)

    def test_sustained_growth_defaults_to_final_year_revenue_growth(self) -> None:
        result = DCF.implied_terminal_growth(self.case, "base", 42.0)
        revenue = self.case["scenarios"]["base"]["revenue"]
        self.assertAlmostEqual(result["sustained_growth_used"], revenue[-1] / revenue[-2] - 1.0, places=10)
        self.assertEqual(result["sustained_growth_basis"], "final-year revenue growth of the model")

    def test_duration_is_compared_against_the_stated_advantage(self) -> None:
        result = DCF.implied_terminal_growth(self.case, "base", 42.0, 0.18)
        self.assertIn("duration_within_stated_advantage", result)
        self.assertIsInstance(result["duration_within_stated_advantage"], bool)
        self.assertGreater(result["implied_growth_duration_years"], result["stated_growth_duration_years"])

    def test_implied_growth_above_reinvestment_capacity_is_flagged(self) -> None:
        result = DCF.implied_terminal_growth(self.case, "base", 42.0, 0.18)
        self.assertGreater(result["implied_growth_above_reinvestment_capacity"], 0)
        self.assertIs(result["funded_by_reinvestment"], False)

    def test_unreachable_price_is_reported_not_extrapolated(self) -> None:
        result = DCF.implied_growth_duration(self.case, "base", 10**9, 0.02)
        self.assertIs(result["reachable"], False)
        self.assertIsNone(result["implied_growth_duration_years"])


if __name__ == "__main__":
    unittest.main()
