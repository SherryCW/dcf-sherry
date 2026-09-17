# Layer 0 — Growth triage

Screening is not valuation. This layer answers one question only: **which pricing method
does this name deserve?** It never produces a target price.

## Rule 0 — no static P/E pricing

A high-growth stock is never priced off a trailing static P/E. But the classification that
follows is **not** "growth above some threshold". It is:

- **duration** — how many years can this growth plausibly persist?
- **quality** — what return on capital does the growth earn, and does it convert to cash?

A 15% grower with a 12-year advantage and positive ROIC − WACC spread is a growth stock. A
60% grower on a low base, one government order, or leverage is not.

## Rule 1 — PEG is a coarse filter only, and its denominator is forward

PEG is admissible in exactly one place: narrowing a large universe down to names worth a
full valuation. It is not a pricing tool and never appears in the conclusion.

Denominator `G` requirements:

- **Must** be a forward expectation — forward consensus EPS growth, carried in three
  views: bear / base / bull.
- **Must not** be a historical CAGR. Report historical CAGR separately, labelled as a
  *verification input* only.
- **Must** be attached to a named horizon. "G = 25%" is meaningless without "next 3 years".
- When bear/base/bull PEGs straddle a decision boundary, the answer is not a midpoint. It
  is "insufficient evidence" → `undetermined`.

Verification use of historical CAGR:

- `historical_cagr` far above forward `G` → the market expects a sharp deceleration.
  State why. Missing explanation is an open gate.
- `historical_cagr` far below forward `G` → the expectation requires an inflection.
  State the driver and its evidence.
- Either way, historical CAGR is never substituted into the denominator.

PEG degenerates and must not be used when:

- earnings are near zero or negative (denominator undefined);
- growth is cyclical rather than structural;
- growth is a low-base rebound, a one-off order, an FX or inventory gain;
- growth is bought with debt or with shareholder dilution;
- the multiple is distorted by a non-recurring gain or loss.

## Rule 2 — classify by duration and quality

Required inputs: forward growth views, expected duration of the advantage, and quality
metrics (ROIC, WACC, cash conversion, leverage, share-count trend).

| Classification | Condition | Route to |
|---|---|---|
| `pseudo_growth` | Any quality red flag: one-off boost, M&A-driven, leverage-driven, or share-count growth that eats the per-share gain | Restate the growth, or reject |
| `cyclical_normalize` | Cyclical earnings, or growth off a depressed base | Normalized earnings / mid-cycle multiple |
| `structural_growth` | No red flags, `ROIC > WACC`, duration ≥ 3 years | Layer 1 — reverse DCF pricing |
| `undetermined` | Quality evidence missing, or duration cannot be argued | Gather evidence; stay `BLOCKED` |

Precedence is top-down. A name with a red flag is never upgraded to `structural_growth`
because its PEG looks cheap.

Quality red flags are facts about *how* the growth arrived, and each requires a source:

- **one-off boost** — a single contract, a price spike, a litigation or disposal gain;
- **M&A-driven** — growth from consolidation rather than organic volume or price;
- **leverage-driven** — net debt / EBITDA rising materially through the growth period;
- **dilution-driven** — share count growing such that per-share growth lags earnings growth.

Classification may **not** default to `structural_growth` when evidence is missing. The
fail-closed default is `undetermined`.

## Rule 3 — cyclical and low-base growth go to normalized earnings

When `cyclical_normalize` is the route:

- Rebasing `G` upward is not allowed. A rebound year is not a growth rate.
- Build normalized earnings: mid-cycle revenue, mid-cycle margin, through-cycle tax.
- Price off a **mid-cycle multiple**, or run the DCF on normalized mid-cycle cash flow with
  a mid-cycle terminal assumption.
- State the mid-cycle definition explicitly: which years, which margin, why that margin is
  representative.
- Report the current position in the cycle and how far the normalization moved the value.

## Output contract

The screen produces, and the answer must state:

1. trailing P/E, forward P/E per view, PEG per view, and the `G` horizon used;
2. `historical_cagr_low` and `historical_cagr_high` — the plausible range of history, shown
   for verification, explicitly excluded from the denominator;
3. the historical-versus-forward divergence and whether it is explained;
4. quality metrics and any red flags, each with its source;
5. `classification` and `required_next_step`;
6. the status: `PASS` only when inputs are complete and the classification is
   `structural_growth`; `DRAFT_REVIEW` when evidence is incomplete; `BLOCKED` when a red
   flag sends the name out of this method entirely.

## What this layer cannot do

- It cannot rank two names by PEG without their duration and quality, because the gap
  between a 3-year and a 10-year advantage is larger than the gap between 1.0x and 1.5x PEG.
- It cannot price. PEG has no terminal value, no reinvestment, no cost of capital.
- It cannot rescue an unclassifiable name. `undetermined` is a legitimate result.
