# Layer 2 — Growth-quality gates

These gates run after the model, before any number is released. They never set a value.
They only decide whether the model's growth assumption is allowed to stand.

A gate result is one of: **pass**, **warn** (→ `DRAFT_REVIEW`), **fail** (→ `BLOCKED`).

## Gate Q1 — ROIC − WACC spread

The return spread is what makes growth worth anything. Growth at a negative spread
destroys value while looking impressive.

- Require `ROIC > WACC` for the growth period. Report the spread per scenario, in bps.
- Require the ROIC used to trace to a source: reported ROIC, a computed
  `NOPAT / invested capital`, or an explicit `judgment` with its reasoning.
- **Fail** when the model assumes growth creates value while the spread is negative — the
  model is internally inconsistent.
- **Warn** when the spread is positive but thinner than 100 bps, or when ROIC trends down
  through the forecast while the growth rate does not.
- Require the ROIC and the reinvestment assumption to be consistent: high growth with a
  low reinvestment rate is not a conservative assumption, it is an arithmetic error.

Do not accept "the industry is different" as a substitute for a measured spread.

## Gate Q2 — Cash conversion

Earnings that never become cash cannot fund growth, and cannot be paid out.

- Require a conversion ratio: `FCFF / NOPAT` over the explicit period, and comparably
  `FCF / net income` where net income is the reference metric.
- **Warn** below 50%, and **warn** when conversion deteriorates materially across the
  forecast without a stated working-capital or capex reason.
- **Fail** when the working-capital or capex schedule is missing such that conversion
  cannot be computed at all.
- Cross-check: rising revenue with rising receivables and inventory faster than revenue is
  a conversion warning, not a growth signal.

## Gate Q3 — Leverage and dilution

Growth financed by debt or by shareholders is not the same growth.

- Report `net debt / EBITDA` at the start and end of the forecast. **Warn** above 3.0x, or
  on a rising trend that the growth depends on.
- Report the diluted share count trend. **Warn** when annual dilution exceeds 2%, or when
  per-share growth lags earnings growth.
- **Warn** when the model's equity bridge uses a diluted share count that does not include
  options, convertibles, or scheduled issuance.
- **Fail** when the share count cannot be established.

## Gate Q4 — Growth duration consistency

The duration of the advantage is the single most valuable and most abused input.

- Require an explicit `high_growth_years` per scenario, with the competitive reason it
  ends: a patent, a contract, a network, a cost position, a regulated monopoly.
- Require `terminal growth` to reconcile with `ROIC × reinvestment rate` for a sustainable
  firm. A terminal growth above the reinvestment implied rate is growth without funding.
- **Warn** when `high_growth_years` reaches beyond the explicit forecast horizon — the
  terminal value is then carrying growth that the model never demonstrated year by year.
- **Warn** when `high_growth_years` is materially shorter than the explicit horizon while
  the forecast still grows at the high rate at the horizon — the forecast has not faded.
- **Fail** when no duration is stated for a `structural_growth` name.

## Gate composition

`PASS` requires every gate to pass, all six governance gates to pass, and the Layer 0
classification to be `structural_growth` with complete inputs.

Any `warn` holds the result at `DRAFT_REVIEW`. Any `fail` returns `BLOCKED`. A
`cyclical_normalize` name that has not been normalized cannot pass — normalization is a
prerequisite, not an optional refinement.

## The boundary these gates do not cross

A gate cannot conclude "therefore buy" or "therefore sell". It concludes only that the
growth assumption is or is not admissible. Valuation outputs stay research artifacts.
