---
name: dcf-sherry
description: Governed valuation for growth stocks — screen, price, and gate. Use for PEG triage with forward-consensus growth, growth-duration and growth-quality classification, normalized earnings and mid-cycle multiples for cyclical or low-base growth, reverse DCF pricing, three-scenario FCFF DCFs, WACC and terminal-value review, ROIC-WACC and cash-conversion gates, dilution and leverage gates, sensitivity analysis, assumption dossiers, workbook contracts, and fail-closed valuation quality gates. Do not use it to produce a buy/sell recommendation from incomplete evidence.
---

# Governed Valuation for Growth Stocks

Forked from `dcf-valuation-governance` v1.0.1. The original treated valuation as an
auditable research system. This fork keeps that spine and adds the missing half: **how a
growth stock is classified before it is priced.**

## The three-layer principle

> Never price a high-growth stock off a static P/E.
> **Screen** with PEG — forward consensus growth, never historical CAGR.
> **Price** with a reverse DCF.
> **Gate** with ROIC and cash-flow quality.

What decides valuation is the **duration × quality** of growth. PEG measures only the
**slope**. So do not ask "is growth above 30%?" — ask "how many years can this growth
last, and what sustains it?"

Three rules are non-negotiable here:

1. **Layering, not combination.** Triage, pricing, and gating are separate layers with
   separate tools. PEG never prices. A reverse DCF never screens. A quality gate never
   sets the number — it only blocks one.
2. **Forward, not historical.** Any growth rate used as a PEG denominator must be a
   forward expectation, carried in bear/base/bull. Historical CAGR is admissible only as
   a sanity check on whether the expectation is absurd.
3. **Duration and quality, not a threshold.** Classification is by how long growth lasts
   and what returns it earns, never by "growth is above 30%".

## Non-negotiable output state

Return one of:

- `PASS`: required inputs, explicit assumptions, model checks, sensitivity, and independent recalculation all pass.
- `DRAFT_REVIEW`: the model runs, but one or more evidence or review gates remain open.
- `BLOCKED`: required facts or structural inputs are missing; do not fill them with invented values.

Never turn missing data into zero. Never describe a `DRAFT_REVIEW` model as final.
Never let a screen result stand in for a valuation.

## Workflow

### Layer 0 — Triage

1. **Screen before you model.** Read `references/growth-triage.md`.
   - Compute PEG only as a coarse filter, with the denominator taken from forward
     consensus in bear/base/bull. State explicitly that historical CAGR is not a denominator.
   - Classify by growth duration and growth quality, not by a growth threshold.
   - Route the name to one of: `structural_growth` → Layer 1 pricing;
     `cyclical_normalize` → normalized earnings / mid-cycle multiple;
     `pseudo_growth` → restate or reject; `undetermined` → more evidence, stay `BLOCKED`.
   - If the evidence needed to classify is missing, classification may not default to
     `structural_growth`.

### Layer 1 — Pricing

2. **Route the valuation family.** Read `references/valuation-routing.md`.
   - Ordinary operating company: FCFF DCF.
   - Bank, insurer, or broker: FCFE, DDM, residual income, or fair-PB.
   - Property, resources, or strong segment economics: NAV or SOTP.
   - Cyclical or low-base growth: normalized earnings, mid-cycle multiple, or mid-cycle DCF.
3. **Freeze the valuation date and units.**
   - State valuation date, reporting cut-off, model currency, per-share currency, diluted shares, and bridge items.
4. **Build the evidence and assumption dossiers.**
   - Historical facts must trace to primary disclosures.
   - Separate `fact`, `calculation`, and `judgment`.
   - Cover revenue, margin, reinvestment, risk/terminal value, equity bridge, and growth duration.
   - Give every material assumption a base view, bear/base/bull range, evidence, counter-evidence, and falsifier.
5. **Build integrated operating forecasts before valuation.**
   - Forecast business drivers and complete statements or equivalent schedules.
   - Derive FCFF from operations; do not type a free-standing cash-flow series with no bridge.
6. **Run three scenarios.**
   - Probabilities must be explicit and sum to 100%.
   - Each scenario must carry its own WACC, terminal growth, growth duration, and forecast path.
7. **Run valuation checks.**
   - Require `WACC > terminal growth`.
   - Reconcile `g = ROIC × reinvestment rate` against the terminal growth actually used.
   - Reconcile enterprise value to equity value and diluted per-share value.
   - Report terminal-value share of enterprise value.
   - Produce WACC × terminal-growth sensitivity and reverse DCF.
8. **Price with the reverse DCF.**
   - Invert the model on the current price. Report two things, because they answer different
     questions:
     - **Implied perpetual growth** — what terminal growth the price requires, against the
       model's own assumption and against the growth that reinvestment can actually fund
       (`ROIC × reinvestment rate`).
     - **Implied growth duration** — how many further years the price requires at the
       forward-consensus growth rate, holding final-year economics constant. Compare that
       against the stated duration of the advantage.
   - Never compare an implied *perpetual* growth rate against a *near-term* consensus growth
     rate. That is an apples-to-oranges comparison. Near-term consensus belongs in the
     duration calculation, not in the perpetual-growth comparison.
   - Durations that fall outside the stated advantage, or that the model cannot reach at all,
     are the finding — not a footnote.

### Layer 2 — Gates

9. **Apply growth-quality and governance gates.**
   - Read `references/growth-quality-gates.md`, `references/workbook-contract.md`,
     and `references/governance-gates.md`.
   - Growth-quality gates: ROIC − WACC spread, cash conversion, leverage and dilution,
     growth-duration consistency.
   - Recalculate independently, scan formula errors, and bind outputs to a run manifest and hashes.
10. **Communicate uncertainty.**
   - Present a range and the variables that change it.
   - State evidence gaps, falsifiers, and what would move the valuation.
   - Add "educational analysis, not investment advice."

## Public reference CLI

The bundled CLI runs a synthetic or user-provided case. It is a transparent reference
implementation, not a substitute for an integrated production workbook.

```bash
python3 scripts/dcf_cli.py screen --input examples/synthetic-growth-screen.json
python3 scripts/dcf_cli.py screen --input examples/synthetic-cyclical-screen.json
python3 scripts/dcf_cli.py validate --input examples/synthetic-consumer-case.json
python3 scripts/dcf_cli.py run --input examples/synthetic-growth-case.json
python3 scripts/dcf_cli.py reverse \
  --input examples/synthetic-growth-case.json \
  --scenario base \
  --target-price 42 \
  --sustained-growth 0.18
```

The `screen` output must include:

- trailing P/E, forward P/E, and PEG per bear/base/bull;
- the explicit statement that historical CAGR was used for verification, not as a denominator;
- the historical-versus-forward divergence check;
- `classification` and `required_next_step`;
- a machine-readable status.

The `run` output must include:

- enterprise value, equity value, and value per diluted share;
- explicit-period PV and terminal-value PV;
- terminal-value share;
- probability-weighted expected value;
- base-case WACC × terminal-growth sensitivity;
- reverse DCF;
- growth-quality checks and warnings, when `growth_quality` is supplied;
- a machine-readable status.

The `reverse` output must include:

- implied perpetual growth, the model's assumed terminal growth, and the gap;
- the sustainable growth reference (`ROIC × reinvestment rate`) and whether the implied
  growth is funded by reinvestment;
- implied growth duration at the sustained growth rate, the extension beyond the explicit
  horizon, and whether it falls inside the stated duration of the advantage;
- an explicit "not reachable" result when the price cannot be justified by any defensible
  duration.

## Required answer structure

1. **Conclusion and status** — valuation range, probability-weighted value, `PASS/DRAFT_REVIEW/BLOCKED`.
2. **Screen result** — PEG band, classification, and the duration and quality evidence behind it.
3. **Method routing** — why this valuation family fits the company.
4. **Source and cut-off** — disclosures, dates, units, currency.
5. **Operating model** — business drivers and statement links.
6. **Assumption dossier** — bear/base/bull plus evidence and falsifiers.
7. **DCF bridge** — FCFF, WACC, terminal value, EV-to-equity, per share.
8. **Reverse DCF** — implied perpetual growth against the model and against reinvestment
   capacity; implied growth duration against the stated advantage.
9. **Quality gates and limitations** — checks passed, open gaps, independent recalculation.

## Stop rules

Stop and return `BLOCKED` when:

- the valuation date, share count, or bridge cannot be established;
- a material assumption has no evidence or explicit judgment label;
- `WACC <= terminal growth`;
- probabilities do not sum to 100%;
- formula errors or independent recalculation differences remain;
- the method is structurally wrong for the company;
- a growth rate is used as a PEG denominator without a forward-consensus basis;
- a cyclical or low-base name is priced off unadjusted peak or trough earnings.

Stop and return `DRAFT_REVIEW` when:

- the screen cannot classify the name because quality evidence is missing;
- ROIC − WACC is negative but the model still assumes growth creates value;
- the terminal growth used is inconsistent with `ROIC × reinvestment rate`;
- the assumed growth duration reaches beyond the explicit forecast horizon;
- the implied growth duration exceeds the stated duration of the advantage, or the price is
  not reachable at the consensus growth rate within any defensible duration.

Keep research and execution separate. A valuation result is not a trade instruction.
