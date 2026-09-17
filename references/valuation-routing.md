# Valuation routing

Choose the method from the economics of the claim being valued — and from the Layer 0
classification. Read `growth-triage.md` first: the classification decides which rows below
are admissible.

| Company economics | Primary family | Why | Common misuse |
|---|---|---|---|
| Ordinary operating company | FCFF DCF | Operations fund debt and equity together | Forecasting FCFF without integrated operating schedules |
| Bank / insurer / broker | FCFE, DDM, residual income, fair-PB | Debt and regulatory capital are operating inputs | Applying enterprise-value FCFF to financial liabilities |
| Property developer / owner | NAV or SOTP | Project and asset values dominate | A single perpetual-growth DCF hides project maturity |
| Resource producer | NAV, reserve life, scenario DCF | Depletion and commodity scenarios dominate | Stable terminal growth after reserves expire |
| Conglomerate / strong segments | SOTP plus segment DCF | Segment economics and capital structures differ | One blended margin and WACC |
| Early-stage / negative cash flow | Milestone scenarios, reverse DCF | Evidence is about survival and scale thresholds | Long precise forecasts with no financing constraint |
| Cyclical or low-base growth | Normalized earnings, mid-cycle multiple, mid-cycle DCF | Peak or trough earnings are not a run rate | Extrapolating a rebound year as a growth rate |
| Structural high growth | Reverse DCF as the primary tool, three-scenario FCFF as the cross-check | The price is a statement about duration and reinvestment, not about next year | Pricing off a static P/E or a single PEG point |

## Routing by Layer 0 classification

| Classification | Admissible methods | Not admissible |
|---|---|---|
| `structural_growth` | Reverse DCF (primary), three-scenario FCFF, SOTP where segments differ | Static P/E, single-point PEG, terminal growth above reinvestment-implied growth |
| `cyclical_normalize` | Normalized earnings, mid-cycle multiple, mid-cycle DCF | Unadjusted peak/trough earnings, PEG, extrapolated rebound growth |
| `pseudo_growth` | Restated organic growth, then re-screen | Any method that accepts the headline growth rate |
| `undetermined` | None — gather evidence first | Any pricing method |

## Method roles

- **Reverse DCF is the pricing instrument for growth names.** It answers what the price
  already assumes, which is the only question that matters when the growth rate itself is
  the contested variable. The three-scenario DCF then tests whether that assumption is
  reachable, not whether the stock is cheap.
- **Multiples are cross-checks, never the primary method** for a growth name. A mid-cycle
  multiple is acceptable as the primary method only for `cyclical_normalize` names.
- **A terminal multiple and a terminal growth rate must not both be optimized.** Pick one
  anchor and state it.

For mixed cases, state the primary method, the cross-check, and what each method is allowed
to conclude.
