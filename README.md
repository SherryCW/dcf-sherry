# dcf-sherry — Governed Valuation for Growth Stocks

A fork of `dcf-valuation-governance` v1.0.1 (sha256
`d110c1811877298f2bed958c93353cc3cbee1309211780b3955b9888423672d4`).

The original answered "how do we build and audit a DCF?" This fork adds the question that
comes first: **which method does this growth stock deserve, and what does its price actually
require?**

## The three layers

| Layer | Question | Tool | Reference |
|---|---|---|---|
| 0 — Triage | Which method does this name deserve? | PEG as a coarse filter, with forward-consensus growth; classification by growth duration × quality | `references/growth-triage.md` |
| 1 — Pricing | What does the price already assume? | Reverse DCF: implied perpetual growth, and implied growth duration | `references/valuation-routing.md` |
| 2 — Gates | Is the growth assumption admissible? | ROIC − WACC, cash conversion, leverage and dilution, duration consistency | `references/growth-quality-gates.md` |

Non-negotiables, inherited and extended:

1. Growth stocks are never priced off a static P/E.
2. PEG denominators are forward expectations. Historical CAGR is a verification input only —
   the CLI records `used_as_peg_denominator: false` to make that auditable.
3. Classification is by duration and quality, never by a growth threshold.
4. Gates can hold or block a result. They never set a value.
5. A screen result is never a valuation, and neither is a trade instruction.

## What the fork changed

- **New** `references/growth-triage.md` — Layer 0 screen, red flags, normalization routing.
- **New** `references/growth-quality-gates.md` — four growth-quality gates, pass/warn/fail.
- **New** `screen` command in the CLI, plus a `growth_quality` block for `run`.
- **New** implied growth duration in `reverse`: how many further years of consensus growth the
  price requires, compared against the stated duration of the advantage.
- **Extended** routing (normalized earnings and mid-cycle multiples), governance gates
  (forward-G rule, ROIC − WACC, reinvestment-consistent terminal growth), and the workbook
  contract (32 modules, including a triage sheet and a growth-duration schedule).
- **Fixed** the test harness: the upstream tests imported the CLI from a repository path that
  does not exist once the skill is installed, so `unittest discover` failed on 1 error and ran
  0 real tests. The suite now resolves the script relative to the skill root.
- **Removed** an apples-to-oranges comparison in the original reverse DCF design, where an
  implied *perpetual* growth rate was being compared against a *near-term* consensus rate.
  Near-term consensus now enters the duration calculation instead.

## Quick start

```bash
PY=python3
$PY scripts/dcf_cli.py screen --input examples/synthetic-growth-screen.json
$PY scripts/dcf_cli.py screen --input examples/synthetic-cyclical-screen.json
$PY scripts/dcf_cli.py validate --input examples/synthetic-consumer-case.json
$PY scripts/dcf_cli.py run --input examples/synthetic-growth-case.json
$PY scripts/dcf_cli.py reverse --input examples/synthetic-growth-case.json \
  --scenario base --target-price 42 --sustained-growth 0.18
$PY -m unittest discover -s tests -v
```

## What the examples demonstrate

**`synthetic-growth-screen.json`** — a 50% forward grower with a 13% ROIC − WACC spread, no red
flags, and a 6-year advantage. Screen: `structural_growth` → `reverse_dcf_pricing`, status
`PASS`. PEG 0.67 base.

**`synthetic-cyclical-screen.json`** — a rebound off a trough year. Base PEG is **0.30**, the
cheapest name in the book, and it is not a growth stock at all: `cyclical_normalize` →
`normalized_earnings`, status `DRAFT_REVIEW`. This is the whole point of Layer 0.

**`synthetic-growth-case.json`** — the DCF for a structural grower with all ten growth-quality
checks passing. Its status is still `DRAFT_REVIEW`, because terminal value is 85% of enterprise
value in the bull case. A growth DCF dominated by its terminal value is exactly why Layer 1
prices with a reverse DCF instead.

At a price of 42 on that case:

```text
implied_terminal_growth                     6.62%   (model assumes 3.00%)
sustainable_growth_reference                3.08%   (ROIC 22% x reinvestment 14%)
funded_by_reinvestment                      false
implied_growth_duration_years               7.3     (at 18% sustained growth)
stated_growth_duration_years                7.0
duration_within_stated_advantage            false
```

Which is the sentence the whole skill exists to produce: not "is growth above 30%", but
**"this price needs 18% growth for 7.3 more years, and the advantage is argued to last 7."**

## What remains private

This is a sanitized public skill, not a dump of any production engine. Real company cases,
holdings, licensed research, reference models, source documents, generated workbooks, local run
logs, machine identity, and credentials are deliberately excluded.

## Limitations, stated honestly

- The CLI is a reference implementation on a fixed forecast structure. It is not a substitute
  for an integrated workbook.
- The implied-duration solve extrapolates final-year economics at a constant growth rate. It is
  an inverse, not a forecast, and it is labelled as such in the output.
- The screen classifies from supplied evidence. It does not fetch or verify sources; the
  governance gates do that.
- Growth duration is a judgment. The skill forces it to be explicit, sourced, and falsifiable —
  it cannot make it correct.

## Attribution

Upstream: `dcf-valuation-governance` v1.0.1. `SECURITY.md` and the disclosure boundary are
carried over unchanged.

## Disclaimer

Educational and research use only. Nothing here is investment advice, a recommendation, or a
promise of returns.
