# Public case schemas

The reference CLI consumes two shapes: a **DCF case** (`validate`, `run`, `reverse`) and a
**screen input** (`screen`).

## A. Screen input

```json
{
  "case_id": "synthetic-growth-screen-001",
  "company_name": "Synthetic Growth Co.",
  "as_of": "2026-09-17",
  "currency": "CNY",
  "price": 100.0,
  "trailing_eps": 2.0,
  "forward_eps": { "bear": 2.6, "base": 3.0, "bull": 3.5 },
  "forward_growth_horizon_years": 3,
  "historical_eps_cagr": { "low": 0.28, "high": 0.42, "years": 5 },
  "high_growth_years": 6,
  "quality_flags": {
    "one_off_boost": false,
    "mna_driven": false,
    "leverage_driven": false,
    "dilution_driven": false,
    "cyclical": false,
    "low_base": false
  },
  "quality_metrics": {
    "roic": 0.22,
    "wacc": 0.09,
    "fcff_conversion": 0.72,
    "net_debt_to_ebitda": 0.8,
    "annual_dilution": 0.005
  },
  "sources": {
    "forward_eps": "consensus aggregation, 2026-09-15",
    "roic": "FY2025 annual report, computed NOPAT / invested capital"
  }
}
```

Rules:

- `forward_eps` must carry all three views. A single-point consensus is not a screen.
- `historical_eps_cagr` is a **verification input**. It is never a PEG denominator, and the
  CLI never substitutes it into one.
- `quality_metrics` is optional, but `structural_growth` cannot be returned without it.
- `quality_flags` must be present and explicit. An absent flag is an unexplained gap, not a
  false one.
- Every non-obvious number should appear in `sources`. The CLI does not verify sources; the
  governance gates do.

## B. DCF case

```json
{
  "case_id": "stable-slug",
  "company_name": "Synthetic Company",
  "valuation_date": "2026-06-30",
  "currency": "CNY",
  "per_share_currency": "CNY",
  "bridge": {
    "net_debt": 250,
    "minority_interest": 0,
    "non_operating_investments": 50,
    "diluted_shares": 100
  },
  "growth_quality": {
    "roic": 0.22,
    "reinvestment_rate": 0.55,
    "high_growth_years": 6,
    "fcff_conversion": 0.72,
    "net_debt_to_ebitda": 0.8,
    "annual_dilution": 0.005
  },
  "scenarios": {
    "bear": {
      "probability": 0.25,
      "wacc": 0.105,
      "terminal_growth": 0.02,
      "revenue": [1000, 1060, 1113],
      "ebit_margin": [0.12, 0.115, 0.11],
      "tax_rate": [0.25, 0.25, 0.25],
      "da_pct_revenue": [0.03, 0.03, 0.03],
      "capex_pct_revenue": [0.04, 0.04, 0.04],
      "nwc_pct_revenue": [0.12, 0.12, 0.12],
      "opening_nwc": 112
    }
  }
}
```

Rules:

- All scenario arrays must have the same non-zero length.
- Rates are decimal fractions. Money fields must use one model currency.
- `growth_quality` is optional. When supplied, the growth-quality gates run and may hold the
  result at `DRAFT_REVIEW` or return `BLOCKED`.
- `roic` and `reinvestment_rate` are compared against each scenario's `terminal_growth` via
  `g = ROIC × reinvestment rate`.
- The public CLI does not perform FX conversion or fetch market data.
