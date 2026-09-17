#!/usr/bin/env python3
"""Transparent reference implementation: growth triage, three-scenario FCFF DCF, reverse DCF.

Layer 0 `screen` classifies a name by growth duration and quality and never prices it.
Layer 1 `run` / `reverse` price it. Layer 2 growth-quality checks gate the result.

This educational CLI deliberately keeps the calculations inspectable. It does not fetch
market data and does not replace an integrated production workbook.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ERROR_TOKENS = ("TBD", "TODO", "N/A?", "#REF!", "#DIV/0!", "#VALUE!", "#NAME?")
REQUIRED_SCENARIOS = ("bear", "base", "bull")
ARRAY_FIELDS = (
    "revenue",
    "ebit_margin",
    "tax_rate",
    "da_pct_revenue",
    "capex_pct_revenue",
    "nwc_pct_revenue",
)
GROWTH_QUALITY_FIELDS = (
    "roic",
    "reinvestment_rate",
    "high_growth_years",
    "fcff_conversion",
    "net_debt_to_ebitda",
    "annual_dilution",
)
RED_FLAG_FIELDS = (
    "one_off_boost",
    "mna_driven",
    "leverage_driven",
    "dilution_driven",
    "cyclical",
    "low_base",
)
PRE_ROUTING_RED_FLAGS = ("one_off_boost", "mna_driven", "leverage_driven", "dilution_driven")
NORMALIZE_TRIGGERS = ("cyclical", "low_base")
PEG_DENOMINATOR_NOTE = (
    "PEG denominator is forward consensus EPS growth. Historical CAGR is a verification "
    "input only and is never substituted into the denominator."
)
TERMINAL_GROWTH_TOLERANCE = 0.02
MIN_ROIC_SPREAD = 0.01
MIN_FCFF_CONVERSION = 0.50
MAX_NET_DEBT_TO_EBITDA = 3.0
MAX_ANNUAL_DILUTION = 0.02
MIN_GROWTH_DURATION_YEARS = 3
MAX_EXTENSION_YEARS = 30
DECELERATION_RATIO = 1.5
INFLECTION_RATIO = 0.5


class CaseError(ValueError):
    """Raised when a case fails a hard validation gate."""


def load_case(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CaseError("case root must be an object")
    return data


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CaseError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise CaseError(f"{label} must be finite")
    return number


def _check_tokens(value: str, label: str) -> None:
    if any(token in value.upper() for token in ERROR_TOKENS):
        raise CaseError(f"{label} contains a placeholder or error token")


# --------------------------------------------------------------------------------------
# Layer 0 — growth triage
# --------------------------------------------------------------------------------------


def validate_screen_input(screen: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for field in ("case_id", "company_name", "as_of", "currency"):
        value = screen.get(field)
        if not isinstance(value, str) or not value.strip():
            raise CaseError(f"missing non-empty {field}")
        _check_tokens(value, field)

    price = _finite_number(screen.get("price"), "price")
    trailing_eps = _finite_number(screen.get("trailing_eps"), "trailing_eps")
    if price <= 0:
        raise CaseError("price must be positive")
    if trailing_eps <= 0:
        raise CaseError("trailing_eps must be positive; PEG is undefined on non-positive earnings")

    forward_eps = screen.get("forward_eps")
    if not isinstance(forward_eps, dict) or tuple(sorted(forward_eps)) != tuple(sorted(REQUIRED_SCENARIOS)):
        raise CaseError("forward_eps must contain exactly bear, base, and bull")
    for name in REQUIRED_SCENARIOS:
        value = _finite_number(forward_eps[name], f"forward_eps.{name}")
        if value <= 0:
            raise CaseError(f"forward_eps.{name} must be positive; PEG is undefined on non-positive earnings")

    horizon = screen.get("forward_growth_horizon_years")
    horizon_years = _finite_number(horizon, "forward_growth_horizon_years")
    if horizon_years <= 0:
        raise CaseError("forward_growth_horizon_years must be positive")

    high_growth_years = _finite_number(screen.get("high_growth_years"), "high_growth_years")
    if high_growth_years <= 0:
        raise CaseError("high_growth_years must be positive")

    flags = screen.get("quality_flags")
    if not isinstance(flags, dict):
        raise CaseError("quality_flags must be an object")
    for field in RED_FLAG_FIELDS:
        if field not in flags:
            raise CaseError(f"quality_flags.{field} must be stated explicitly, not omitted")
        if not isinstance(flags[field], bool):
            raise CaseError(f"quality_flags.{field} must be a boolean")

    metrics = screen.get("quality_metrics")
    if metrics is not None:
        if not isinstance(metrics, dict):
            raise CaseError("quality_metrics must be an object when present")
        for item in ("roic", "wacc"):
            _finite_number(metrics.get(item), f"quality_metrics.{item}")
        for item in ("fcff_conversion", "net_debt_to_ebitda", "annual_dilution"):
            if metrics.get(item) is not None:
                _finite_number(metrics[item], f"quality_metrics.{item}")

    history = screen.get("historical_eps_cagr")
    if history is not None:
        if not isinstance(history, dict):
            raise CaseError("historical_eps_cagr must be an object when present")
        low = _finite_number(history.get("low"), "historical_eps_cagr.low")
        high = _finite_number(history.get("high"), "historical_eps_cagr.high")
        if low > high:
            raise CaseError("historical_eps_cagr.low must not exceed historical_eps_cagr.high")
        if history.get("years") is not None:
            years = _finite_number(history["years"], "historical_eps_cagr.years")
            if years <= 0:
                raise CaseError("historical_eps_cagr.years must be positive")
    else:
        warnings.append("historical_eps_cagr absent; the forward expectation cannot be verified against history")

    sources = screen.get("sources")
    if not isinstance(sources, dict) or not sources:
        warnings.append("no sources declared; growth-quality gates cannot be cleared from the screen alone")
    return warnings


def screen_case(screen: dict[str, Any]) -> dict[str, Any]:
    """Classify by growth duration and quality. Never produces a price."""
    warnings = validate_screen_input(screen)
    price = float(screen["price"])
    trailing_eps = float(screen["trailing_eps"])
    forward_eps = {name: float(screen["forward_eps"][name]) for name in REQUIRED_SCENARIOS}
    horizon_years = float(screen["forward_growth_horizon_years"])
    high_growth_years = float(screen["high_growth_years"])
    flags = dict(screen["quality_flags"])
    metrics = screen.get("quality_metrics") or {}

    trailing_pe = price / trailing_eps
    forward_pe = {name: price / forward_eps[name] for name in REQUIRED_SCENARIOS}
    forward_growth = {name: forward_eps[name] / trailing_eps - 1.0 for name in REQUIRED_SCENARIOS}
    peg = {name: forward_pe[name] / (forward_growth[name] * 100.0) for name in REQUIRED_SCENARIOS}

    history = screen.get("historical_eps_cagr")
    verification: dict[str, Any] = {
        "status": "not_supplied",
        "note": PEG_DENOMINATOR_NOTE,
    }
    if history is not None:
        low = float(history["low"])
        high = float(history["high"])
        base_growth = forward_growth["base"]
        verification = {
            "low": low,
            "high": high,
            "years": history.get("years"),
            "forward_base_growth": base_growth,
            "forward_growth_horizon_years": horizon_years,
            "used_as_peg_denominator": False,
            "note": PEG_DENOMINATOR_NOTE,
        }
        if base_growth > 0:
            if low > base_growth * DECELERATION_RATIO:
                verification["divergence"] = "historical_far_above_forward"
                warnings.append(
                    "historical CAGR is far above forward consensus: the expectation is a sharp "
                    "deceleration. State the reason or leave the gate open."
                )
            elif high < base_growth * INFLECTION_RATIO:
                verification["divergence"] = "forward_far_above_historical"
                warnings.append(
                    "forward consensus requires an inflection the history does not show. State the "
                    "driver and its evidence."
                )
            else:
                verification["divergence"] = "consistent"

    spread: float | None = None
    if "roic" in metrics and "wacc" in metrics:
        spread = float(metrics["roic"]) - float(metrics["wacc"])
    quality = {
        "roic": metrics.get("roic"),
        "wacc": metrics.get("wacc"),
        "roic_wacc_spread": spread,
        "fcff_conversion": metrics.get("fcff_conversion"),
        "net_debt_to_ebitda": metrics.get("net_debt_to_ebitda"),
        "annual_dilution": metrics.get("annual_dilution"),
        "evidence_complete": spread is not None,
    }

    red_flags = [field for field in PRE_ROUTING_RED_FLAGS if flags[field]]
    normalize_flags = [field for field in NORMALIZE_TRIGGERS if flags[field]]

    if red_flags:
        classification = "pseudo_growth"
        next_step = "restate_or_reject"
    elif normalize_flags:
        classification = "cyclical_normalize"
        next_step = "normalized_earnings"
    elif spread is None:
        classification = "undetermined"
        next_step = "gather_evidence"
        warnings.append(
            "quality evidence missing: classification may not default to structural_growth"
        )
    elif spread <= 0:
        classification = "undetermined"
        next_step = "gather_evidence"
        warnings.append("ROIC does not exceed WACC: growth is not currently value-creating")
    elif high_growth_years < MIN_GROWTH_DURATION_YEARS:
        classification = "undetermined"
        next_step = "gather_evidence"
        warnings.append(
            f"growth duration of {high_growth_years:g} years is below the {MIN_GROWTH_DURATION_YEARS}-year "
            "threshold for a structural growth classification"
        )
    else:
        classification = "structural_growth"
        next_step = "reverse_dcf_pricing"

    if classification == "structural_growth" and spread is not None and spread < MIN_ROIC_SPREAD:
        warnings.append(
            f"ROIC - WACC spread of {spread:.4f} is thinner than {MIN_ROIC_SPREAD:.2f}; the growth case is marginal"
        )

    if classification == "structural_growth" and peg["base"] <= 0:
        warnings.append("PEG is non-positive; verify the forward growth view")

    if classification == "pseudo_growth":
        status = "BLOCKED"
    elif classification == "structural_growth" and not warnings:
        status = "PASS"
    else:
        status = "DRAFT_REVIEW"

    return {
        "schema_version": 1,
        "layer": "triage",
        "status": status,
        "case_id": screen["case_id"],
        "company_name": screen["company_name"],
        "as_of": screen["as_of"],
        "currency": screen["currency"],
        "multiples": {
            "price": price,
            "trailing_eps": trailing_eps,
            "trailing_pe": trailing_pe,
            "forward_pe": forward_pe,
            "forward_growth": forward_growth,
            "peg": peg,
        },
        "peg_denominator": {
            "basis": "forward_consensus_eps_growth",
            "horizon_years": horizon_years,
            "note": PEG_DENOMINATOR_NOTE,
        },
        "historical_verification": verification,
        "growth_duration": {"high_growth_years": high_growth_years},
        "quality": quality,
        "quality_flags": flags,
        "red_flags": red_flags + normalize_flags,
        "classification": classification,
        "required_next_step": next_step,
        "warnings": warnings,
        "disclaimer": "Educational triage only; not investment advice and not a valuation.",
    }


# --------------------------------------------------------------------------------------
# Layer 1 / 2 — case validation, DCF, growth-quality checks
# --------------------------------------------------------------------------------------


def validate_case(case: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for field in ("case_id", "company_name", "valuation_date", "currency", "per_share_currency"):
        value = case.get(field)
        if not isinstance(value, str) or not value.strip():
            raise CaseError(f"missing non-empty {field}")
        _check_tokens(value, field)

    bridge = case.get("bridge")
    if not isinstance(bridge, dict):
        raise CaseError("bridge must be an object")
    for field in ("net_debt", "minority_interest", "non_operating_investments"):
        _finite_number(bridge.get(field), f"bridge.{field}")
    diluted_shares = _finite_number(bridge.get("diluted_shares"), "bridge.diluted_shares")
    if diluted_shares <= 0:
        raise CaseError("bridge.diluted_shares must be greater than zero")

    scenarios = case.get("scenarios")
    if not isinstance(scenarios, dict) or tuple(sorted(scenarios)) != tuple(sorted(REQUIRED_SCENARIOS)):
        raise CaseError("scenarios must contain exactly bear, base, and bull")

    forecast_years: int | None = None
    for name in REQUIRED_SCENARIOS:
        scenario = scenarios[name]
        if not isinstance(scenario, dict):
            raise CaseError(f"scenarios.{name} must be an object")
        probability = _finite_number(scenario.get("probability"), f"{name}.probability")
        if probability < 0 or probability > 1:
            raise CaseError(f"{name}.probability must be between zero and one")

        wacc = _finite_number(scenario.get("wacc"), f"{name}.wacc")
        terminal_growth = _finite_number(scenario.get("terminal_growth"), f"{name}.terminal_growth")
        if not 0 < wacc < 1:
            raise CaseError(f"{name}.wacc must be between zero and one")
        if not -0.20 < terminal_growth < 0.20:
            raise CaseError(f"{name}.terminal_growth is outside the supported range")
        if wacc <= terminal_growth:
            raise CaseError(f"{name} fails WACC > terminal growth")

        lengths: set[int] = set()
        for field in ARRAY_FIELDS:
            values = scenario.get(field)
            if not isinstance(values, list) or not values:
                raise CaseError(f"{name}.{field} must be a non-empty array")
            lengths.add(len(values))
            for index, value in enumerate(values):
                number = _finite_number(value, f"{name}.{field}[{index}]")
                if field == "revenue" and number <= 0:
                    raise CaseError(f"{name}.{field}[{index}] must be positive")
                if field != "revenue" and not -1 < number < 1:
                    raise CaseError(f"{name}.{field}[{index}] must be a decimal rate")
        if len(lengths) != 1:
            raise CaseError(f"{name} forecast arrays must have the same length")
        years = lengths.pop()
        if forecast_years is None:
            forecast_years = years
        elif years != forecast_years:
            raise CaseError("all scenarios must use the same forecast horizon")

        opening_nwc = _finite_number(scenario.get("opening_nwc"), f"{name}.opening_nwc")
        if opening_nwc < 0:
            warnings.append(f"{name}: opening NWC is negative; confirm the business model")

    probability_total = sum(float(scenarios[name]["probability"]) for name in REQUIRED_SCENARIOS)
    if abs(probability_total - 1.0) > 1e-9:
        raise CaseError(f"scenario probabilities sum to {probability_total:.10f}, not 1")
    if forecast_years is not None and forecast_years < 3:
        warnings.append("forecast horizon is shorter than three years")
    if case["currency"] != case["per_share_currency"]:
        warnings.append("model and per-share currencies differ; the public CLI does not perform FX conversion")

    quality = case.get("growth_quality")
    if quality is not None:
        if not isinstance(quality, dict):
            raise CaseError("growth_quality must be an object when present")
        for field in GROWTH_QUALITY_FIELDS:
            value = quality.get(field)
            if value is None:
                raise CaseError(f"growth_quality.{field} must be supplied when growth_quality is present")
            number = _finite_number(value, f"growth_quality.{field}")
            if field in ("high_growth_years", "net_debt_to_ebitda") and number < 0:
                raise CaseError(f"growth_quality.{field} must not be negative")
            if field in ("roic", "reinvestment_rate", "fcff_conversion", "annual_dilution") and not -1 < number < 1:
                raise CaseError(f"growth_quality.{field} must be a decimal rate")
    return warnings


def growth_quality_checks(case: dict[str, Any], forecast_years: int) -> list[dict[str, Any]]:
    """Layer 2 gates. They can hold or block a result; they never set a value."""
    quality = case.get("growth_quality")
    if not quality:
        return []
    roic = float(quality["roic"])
    reinvestment_rate = float(quality["reinvestment_rate"])
    high_growth_years = float(quality["high_growth_years"])
    conversion = float(quality["fcff_conversion"])
    leverage = float(quality["net_debt_to_ebitda"])
    dilution = float(quality["annual_dilution"])
    implied_sustainable_growth = roic * reinvestment_rate

    checks: list[dict[str, Any]] = []
    for name in REQUIRED_SCENARIOS:
        scenario = case["scenarios"][name]
        wacc = float(scenario["wacc"])
        terminal_growth = float(scenario["terminal_growth"])
        spread = roic - wacc

        if spread <= 0:
            checks.append(
                {
                    "check": "Q1_roic_wacc_spread",
                    "scenario": name,
                    "status": "fail",
                    "value": spread,
                    "message": (
                        f"ROIC {roic:.4f} does not exceed WACC {wacc:.4f}: the model assumes growth "
                        "creates value while the spread is negative"
                    ),
                }
            )
        elif spread < MIN_ROIC_SPREAD:
            checks.append(
                {
                    "check": "Q1_roic_wacc_spread",
                    "scenario": name,
                    "status": "warn",
                    "value": spread,
                    "message": f"ROIC - WACC spread of {spread:.4f} is thinner than {MIN_ROIC_SPREAD:.2f}",
                }
            )
        else:
            checks.append(
                {
                    "check": "Q1_roic_wacc_spread",
                    "scenario": name,
                    "status": "pass",
                    "value": spread,
                    "message": f"ROIC - WACC spread of {spread:.4f} is positive",
                }
            )

        gap = terminal_growth - implied_sustainable_growth
        if gap > TERMINAL_GROWTH_TOLERANCE:
            checks.append(
                {
                    "check": "Q2_terminal_growth_reinvestment_consistency",
                    "scenario": name,
                    "status": "warn",
                    "value": gap,
                    "message": (
                        f"terminal growth {terminal_growth:.4f} exceeds ROIC x reinvestment "
                        f"{implied_sustainable_growth:.4f} by {gap:.4f}: growth without funding"
                    ),
                }
            )
        elif abs(gap) > TERMINAL_GROWTH_TOLERANCE:
            checks.append(
                {
                    "check": "Q2_terminal_growth_reinvestment_consistency",
                    "scenario": name,
                    "status": "warn",
                    "value": gap,
                    "message": (
                        f"terminal growth {terminal_growth:.4f} is below ROIC x reinvestment "
                        f"{implied_sustainable_growth:.4f} by {abs(gap):.4f}: state which anchor governs"
                    ),
                }
            )
        else:
            checks.append(
                {
                    "check": "Q2_terminal_growth_reinvestment_consistency",
                    "scenario": name,
                    "status": "pass",
                    "value": gap,
                    "message": (
                        f"terminal growth {terminal_growth:.4f} reconciles with ROIC x reinvestment "
                        f"{implied_sustainable_growth:.4f}"
                    ),
                }
            )

    if conversion < MIN_FCFF_CONVERSION:
        checks.append(
            {
                "check": "Q3_cash_conversion",
                "scenario": "all",
                "status": "warn",
                "value": conversion,
                "message": f"FCFF / NOPAT of {conversion:.4f} is below {MIN_FCFF_CONVERSION:.2f}",
            }
        )
    else:
        checks.append(
            {
                "check": "Q3_cash_conversion",
                "scenario": "all",
                "status": "pass",
                "value": conversion,
                "message": f"FCFF / NOPAT of {conversion:.4f} clears the floor",
            }
        )

    if leverage > MAX_NET_DEBT_TO_EBITDA:
        checks.append(
            {
                "check": "Q4_leverage",
                "scenario": "all",
                "status": "warn",
                "value": leverage,
                "message": f"net debt / EBITDA of {leverage:.2f}x exceeds {MAX_NET_DEBT_TO_EBITDA:.1f}x",
            }
        )
    else:
        checks.append(
            {
                "check": "Q4_leverage",
                "scenario": "all",
                "status": "pass",
                "value": leverage,
                "message": f"net debt / EBITDA of {leverage:.2f}x is within tolerance",
            }
        )

    if dilution > MAX_ANNUAL_DILUTION:
        checks.append(
            {
                "check": "Q5_dilution",
                "scenario": "all",
                "status": "warn",
                "value": dilution,
                "message": f"annual dilution of {dilution:.4f} exceeds {MAX_ANNUAL_DILUTION:.2f}",
            }
        )
    else:
        checks.append(
            {
                "check": "Q5_dilution",
                "scenario": "all",
                "status": "pass",
                "value": dilution,
                "message": f"annual dilution of {dilution:.4f} is within tolerance",
            }
        )

    if high_growth_years > forecast_years:
        checks.append(
            {
                "check": "Q6_growth_duration_consistency",
                "scenario": "all",
                "status": "warn",
                "value": high_growth_years - forecast_years,
                "message": (
                    f"growth duration of {high_growth_years:g} years reaches beyond the "
                    f"{forecast_years}-year explicit horizon: the terminal value carries growth the "
                    "model never demonstrated year by year"
                ),
            }
        )
    elif high_growth_years <= forecast_years - 2:
        checks.append(
            {
                "check": "Q6_growth_duration_consistency",
                "scenario": "all",
                "status": "warn",
                "value": forecast_years - high_growth_years,
                "message": (
                    f"growth duration of {high_growth_years:g} years is shorter than the "
                    f"{forecast_years}-year horizon: the forecast has not faded to the terminal rate"
                ),
            }
        )
    else:
        checks.append(
            {
                "check": "Q6_growth_duration_consistency",
                "scenario": "all",
                "status": "pass",
                "value": high_growth_years - forecast_years,
                "message": (
                    f"growth duration of {high_growth_years:g} years is consistent with the "
                    f"{forecast_years}-year horizon"
                ),
            }
        )
    return checks


def scenario_dcf(case: dict[str, Any], name: str, wacc: float | None = None, terminal_growth: float | None = None) -> dict[str, Any]:
    scenario = case["scenarios"][name]
    rate = float(scenario["wacc"] if wacc is None else wacc)
    growth = float(scenario["terminal_growth"] if terminal_growth is None else terminal_growth)
    if rate <= growth:
        raise CaseError(f"{name} fails WACC > terminal growth")

    rows: list[dict[str, float | int]] = []
    previous_nwc = float(scenario["opening_nwc"])
    pv_explicit = 0.0
    for index, revenue_value in enumerate(scenario["revenue"]):
        year = index + 1
        revenue = float(revenue_value)
        ebit = revenue * float(scenario["ebit_margin"][index])
        nopat = ebit * (1.0 - float(scenario["tax_rate"][index]))
        depreciation = revenue * float(scenario["da_pct_revenue"][index])
        capex = revenue * float(scenario["capex_pct_revenue"][index])
        nwc = revenue * float(scenario["nwc_pct_revenue"][index])
        delta_nwc = nwc - previous_nwc
        fcff = nopat + depreciation - capex - delta_nwc
        discount_factor = (1.0 + rate) ** year
        pv_fcff = fcff / discount_factor
        pv_explicit += pv_fcff
        rows.append(
            {
                "year": year,
                "revenue": revenue,
                "ebit": ebit,
                "nopat": nopat,
                "depreciation": depreciation,
                "capex": capex,
                "delta_nwc": delta_nwc,
                "fcff": fcff,
                "discount_factor": discount_factor,
                "pv_fcff": pv_fcff,
            }
        )
        previous_nwc = nwc

    terminal_fcff = float(rows[-1]["fcff"]) * (1.0 + growth)
    terminal_value = terminal_fcff / (rate - growth)
    terminal_discount_factor = float(rows[-1]["discount_factor"])
    pv_terminal = terminal_value / terminal_discount_factor
    enterprise_value = pv_explicit + pv_terminal

    bridge = case["bridge"]
    equity_value = (
        enterprise_value
        - float(bridge["net_debt"])
        - float(bridge["minority_interest"])
        + float(bridge["non_operating_investments"])
    )
    value_per_share = equity_value / float(bridge["diluted_shares"])
    terminal_share = pv_terminal / enterprise_value if enterprise_value else math.nan
    return {
        "scenario": name,
        "probability": float(scenario["probability"]),
        "wacc": rate,
        "terminal_growth": growth,
        "forecast": rows,
        "pv_explicit_fcff": pv_explicit,
        "terminal_fcff": terminal_fcff,
        "terminal_value_at_horizon": terminal_value,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
        "terminal_value_share": terminal_share,
    }


def sensitivity(case: dict[str, Any], wacc_steps: tuple[float, ...] = (-0.01, -0.005, 0.0, 0.005, 0.01), growth_steps: tuple[float, ...] = (-0.01, -0.005, 0.0, 0.005, 0.01)) -> dict[str, Any]:
    base = case["scenarios"]["base"]
    base_wacc = float(base["wacc"])
    base_growth = float(base["terminal_growth"])
    rows: list[dict[str, Any]] = []
    for growth_delta in growth_steps:
        growth = base_growth + growth_delta
        values: list[float | None] = []
        for wacc_delta in wacc_steps:
            wacc = base_wacc + wacc_delta
            if wacc <= growth:
                values.append(None)
            else:
                values.append(scenario_dcf(case, "base", wacc=wacc, terminal_growth=growth)["value_per_share"])
        rows.append({"terminal_growth": growth, "values": values})
    return {
        "wacc_columns": [base_wacc + delta for delta in wacc_steps],
        "rows": rows,
    }


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    warnings = validate_case(case)
    scenarios = {name: scenario_dcf(case, name) for name in REQUIRED_SCENARIOS}
    expected_value = sum(item["probability"] * item["value_per_share"] for item in scenarios.values())
    terminal_shares = [item["terminal_value_share"] for item in scenarios.values()]
    if max(terminal_shares) > 0.80:
        warnings.append("terminal value exceeds 80% of enterprise value in at least one scenario")

    forecast_years = len(case["scenarios"]["base"]["revenue"])
    checks = growth_quality_checks(case, forecast_years)
    failures = [item for item in checks if item["status"] == "fail"]
    check_warnings = [item for item in checks if item["status"] == "warn"]
    for item in check_warnings:
        warnings.append(f"{item['check']} ({item['scenario']}): {item['message']}")

    if failures:
        status = "BLOCKED"
    elif warnings:
        status = "DRAFT_REVIEW"
    else:
        status = "PASS"

    return {
        "schema_version": 1,
        "layer": "pricing",
        "status": status,
        "case_id": case["case_id"],
        "company_name": case["company_name"],
        "valuation_date": case["valuation_date"],
        "currency": case["currency"],
        "scenarios": scenarios,
        "probability_weighted_value_per_share": expected_value,
        "base_sensitivity": sensitivity(case),
        "growth_quality_checks": checks,
        "growth_quality_summary": {
            "supplied": bool(case.get("growth_quality")),
            "passed": len([item for item in checks if item["status"] == "pass"]),
            "warned": len(check_warnings),
            "failed": len(failures),
        },
        "warnings": warnings,
        "disclaimer": "Educational analysis only; not investment advice.",
    }


def _extended_enterprise_value(case: dict[str, Any], scenario_name: str, extension_years: int, sustained_growth: float) -> float:
    """Value the case again with `extension_years` added past the explicit horizon.

    Extension years repeat the final explicit year's economics, growing revenue at
    `sustained_growth`. This is an extrapolation and is labelled as one in the output.
    """
    scenario = case["scenarios"][scenario_name]
    rate = float(scenario["wacc"])
    growth = float(scenario["terminal_growth"])
    base = scenario_dcf(case, scenario_name)
    if extension_years <= 0:
        return float(base["enterprise_value"])

    margin = float(scenario["ebit_margin"][-1])
    tax = float(scenario["tax_rate"][-1])
    da = float(scenario["da_pct_revenue"][-1])
    capex = float(scenario["capex_pct_revenue"][-1])
    nwc_pct = float(scenario["nwc_pct_revenue"][-1])

    revenue = float(scenario["revenue"][-1])
    previous_nwc = revenue * nwc_pct
    year = len(scenario["revenue"])
    pv_extension = 0.0
    fcff = 0.0
    for _ in range(extension_years):
        year += 1
        revenue = revenue * (1.0 + sustained_growth)
        nwc = revenue * nwc_pct
        fcff = revenue * margin * (1.0 - tax) + revenue * da - revenue * capex - (nwc - previous_nwc)
        previous_nwc = nwc
        pv_extension += fcff / (1.0 + rate) ** year

    terminal_value = fcff * (1.0 + growth) / (rate - growth)
    pv_terminal = terminal_value / (1.0 + rate) ** year
    return float(base["pv_explicit_fcff"]) + pv_extension + pv_terminal


def implied_growth_duration(case: dict[str, Any], scenario_name: str, target_enterprise: float, sustained_growth: float) -> dict[str, Any]:
    """Years of sustained growth the current price requires. The core growth question."""
    previous_years = 0
    previous_value = _extended_enterprise_value(case, scenario_name, 0, sustained_growth)
    if target_enterprise <= previous_value:
        return {
            "implied_growth_duration_years": 0.0,
            "extension_years_beyond_horizon": 0.0,
            "reachable": True,
            "note": (
                "the target enterprise value is at or below the value of the explicit forecast alone: "
                "the price requires no growth beyond the stated horizon"
            ),
        }
    for extension_years in range(1, MAX_EXTENSION_YEARS + 1):
        value = _extended_enterprise_value(case, scenario_name, extension_years, sustained_growth)
        if value >= target_enterprise:
            span = value - previous_value
            fraction = (target_enterprise - previous_value) / span if span > 0 else 0.0
            solved = previous_years + max(0.0, min(1.0, fraction))
            return {
                "implied_growth_duration_years": solved,
                "extension_years_beyond_horizon": solved,
                "reachable": True,
                "note": (
                    f"the price requires {solved:.1f} further years at {sustained_growth:.2%} beyond the "
                    "explicit horizon, holding final-year economics constant"
                ),
            }
        previous_years = float(extension_years)
        previous_value = value
    return {
        "implied_growth_duration_years": None,
        "extension_years_beyond_horizon": None,
        "reachable": False,
        "note": (
            f"not reachable within {MAX_EXTENSION_YEARS} extension years at {sustained_growth:.2%}: the "
            "price implies growth beyond any defensible duration"
        ),
    }


def implied_terminal_growth(
    case: dict[str, Any],
    scenario_name: str,
    target_price: float,
    sustained_growth: float | None = None,
) -> dict[str, Any]:
    validate_case(case)
    if scenario_name not in REQUIRED_SCENARIOS:
        raise CaseError("scenario must be bear, base, or bull")
    if not math.isfinite(target_price) or target_price <= 0:
        raise CaseError("target price must be positive and finite")
    if sustained_growth is not None and not -1 < sustained_growth < 1:
        raise CaseError("sustained growth must be a decimal rate")

    scenario = scenario_dcf(case, scenario_name)
    bridge = case["bridge"]
    target_equity = target_price * float(bridge["diluted_shares"])
    target_enterprise = (
        target_equity
        + float(bridge["net_debt"])
        + float(bridge["minority_interest"])
        - float(bridge["non_operating_investments"])
    )
    required_pv_terminal = target_enterprise - float(scenario["pv_explicit_fcff"])
    if required_pv_terminal <= 0:
        raise CaseError("target price is below the value of explicit cash flows after the equity bridge")
    horizon_factor = float(scenario["forecast"][-1]["discount_factor"])
    required_terminal_value = required_pv_terminal * horizon_factor
    terminal_fcff_pre_growth = float(scenario["forecast"][-1]["fcff"])
    wacc = float(scenario["wacc"])
    implied_growth = (required_terminal_value * wacc - terminal_fcff_pre_growth) / (
        required_terminal_value + terminal_fcff_pre_growth
    )
    model_terminal_growth = float(case["scenarios"][scenario_name]["terminal_growth"])

    output: dict[str, Any] = {
        "schema_version": 1,
        "layer": "pricing",
        "case_id": case["case_id"],
        "scenario": scenario_name,
        "target_price": target_price,
        "target_enterprise_value": target_enterprise,
        "wacc": wacc,
        "implied_growth": implied_growth,
        "implied_terminal_growth": implied_growth,
        "model_terminal_growth": model_terminal_growth,
        "implied_excess_perpetual_growth": implied_growth - model_terminal_growth,
        "feasible_under_gordon_growth": implied_growth < wacc,
        "disclaimer": "Educational reverse DCF only; not investment advice.",
    }

    quality = case.get("growth_quality") or {}
    if "roic" in quality and "reinvestment_rate" in quality:
        sustainable = float(quality["roic"]) * float(quality["reinvestment_rate"])
        output["sustainable_growth_reference"] = sustainable
        output["implied_growth_above_reinvestment_capacity"] = implied_growth - sustainable
        output["funded_by_reinvestment"] = implied_growth <= sustainable

    revenue_path = [float(value) for value in case["scenarios"][scenario_name]["revenue"]]
    model_final_growth = revenue_path[-1] / revenue_path[-2] - 1.0
    rate_used = model_final_growth if sustained_growth is None else sustained_growth
    output["sustained_growth_used"] = rate_used
    output["sustained_growth_basis"] = (
        "final-year revenue growth of the model" if sustained_growth is None else "supplied forward growth rate"
    )
    duration = implied_growth_duration(case, scenario_name, target_enterprise, rate_used)
    output.update(duration)

    stated_duration = quality.get("high_growth_years")
    if stated_duration is not None:
        output["stated_growth_duration_years"] = float(stated_duration)
        implied_years = duration["implied_growth_duration_years"]
        if implied_years is None:
            output["duration_within_stated_advantage"] = False
        else:
            output["duration_within_stated_advantage"] = implied_years <= float(stated_duration)
    return output


def _rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, list):
        return [_rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: _rounded(item) for key, item in value.items()}
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "run", "screen"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--input", required=True)
    reverse_parser = subparsers.add_parser("reverse")
    reverse_parser.add_argument("--input", required=True)
    reverse_parser.add_argument("--scenario", choices=REQUIRED_SCENARIOS, default="base")
    reverse_parser.add_argument("--target-price", type=float, required=True)
    reverse_parser.add_argument(
        "--sustained-growth",
        type=float,
        default=None,
        help=(
            "growth rate assumed to persist past the explicit horizon, as a decimal. Pass the "
            "forward consensus rate here to measure the implied duration at consensus growth "
            "rather than at the model's own fade. Defaults to the final-year revenue growth."
        ),
    )
    args = parser.parse_args()

    try:
        case = load_case(args.input)
        if args.command == "validate":
            output: dict[str, Any] = {"status": "PASS", "warnings": validate_case(case)}
        elif args.command == "screen":
            output = screen_case(case)
        elif args.command == "run":
            output = run_case(case)
        else:
            output = implied_terminal_growth(case, args.scenario, args.target_price, args.sustained_growth)
    except (CaseError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(_rounded(output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
