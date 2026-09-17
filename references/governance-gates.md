# Governance gates

These are the structural gates. The growth-specific gates live in
`growth-quality-gates.md`; both sets must pass.

## Gate 1 — source integrity

- Historical facts trace to primary disclosures.
- Market data has a valuation date and source.
- Broker material is counter-evidence, not formula authority.
- The Layer 0 classification's red flags each carry a source. An unsourced red flag is an
  open gate, not a cleared one.

## Gate 2 — assumption integrity

- Each material assumption is labeled `fact`, `calculation`, or `judgment`.
- Revenue, margin, reinvestment, risk/terminal, equity bridge, and **growth duration** are covered.
- Bear/base/bull ranges, counter-evidence, and falsifiers are explicit.
- **Any growth rate used as a PEG denominator is a forward expectation with a stated
  horizon.** Historical CAGR is labeled a verification input and is never the denominator.
- **Growth duration is an assumption with its own dossier entry**: the number of years, the
  competing reason it ends, the evidence, and the falsifier.
- The historical-versus-forward growth divergence is either explained or explicitly flagged
  as an open question.

## Gate 3 — model integrity

- Statements or equivalent schedules reconcile.
- FCFF follows `NOPAT + D&A - Capex - ΔNWC`.
- `WACC > g`, probabilities sum to 100%, units are consistent.
- Enterprise-to-equity and diluted-share bridges are explicit.
- `terminal growth` reconciles with `ROIC × reinvestment rate` within a declared tolerance.
- **ROIC − WACC spread is reported per scenario**, with its source.

## Gate 4 — workbook integrity

- Formula cells are formulas where expected.
- No `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or stale cached errors.
- Checks, sensitivities, and reverse DCF are present.
- A triage sheet, a normalized-earnings sheet where applicable, and a growth-duration
  schedule are present.

## Gate 5 — independent recalculation

- Recalculate with an engine independent of the workbook writer.
- Re-run the same contract on the recalculated file.
- Compare key outputs within a declared tolerance.

## Gate 6 — release integrity

- Persist an immutable run id.
- Bind source revision, runtime, checks, artifacts, and SHA-256 in a run manifest.
- Promote `latest` only when every hard gate passes.
- Preserve failed runs for diagnosis; never overwrite a prior run id.

`PASS` requires all six gates plus every growth-quality gate. Anything less remains
`DRAFT_REVIEW` or `BLOCKED`.

## Promotion boundary

A screen result is never a release artifact. Only a fully gated valuation may set
`MASTER PASS`, and even then it is research output, not a trade instruction.
