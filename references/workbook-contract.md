# Workbook contract

A production valuation workbook should expose a coherent model, not a decorative
spreadsheet.

## Minimum modules

1. Cover and navigation
2. Source register and valuation date
3. Triage sheet (Layer 0: PEG band, forward growth views, historical CAGR verification, classification, red flags)
4. Assumption dossier
5. Growth-duration schedule (years, competing reason it ends, evidence, falsifier)
6. Historical income statement
7. Historical balance sheet
8. Historical cash-flow statement
9. Invested capital and ROIC history
10. Revenue drivers
11. Margin and operating-cost drivers
12. Working-capital schedules
13. Capex and depreciation
14. Debt and interest
15. Tax schedule
16. Share count and dilution schedule
17. Forecast income statement
18. Forecast balance sheet
19. Forecast cash-flow statement
20. Statement reconciliation
21. FCFF bridge
22. WACC
23. Terminal value
24. Reinvestment and sustainable-growth check (`g = ROIC × reinvestment rate`)
25. EV-to-equity bridge
26. Bear/base/bull scenarios
27. Sensitivity tables
28. Reverse DCF (implied growth)
29. Implied growth versus forward consensus
30. Normalized earnings / mid-cycle sheet (required for `cyclical_normalize`, otherwise marked not applicable)
31. Growth-quality summary (ROIC − WACC, cash conversion, leverage, dilution)
32. Checks and release summary

## Hard checks

- The balance sheet balances for every forecast period.
- Cash movement reconciles to the cash-flow statement.
- Debt and interest use the same timing convention.
- FCFF reconciles to the operating schedules.
- Terminal value uses a stable cash-flow definition.
- Per-share value uses diluted, not basic, shares unless explicitly justified.
- All scenario probabilities sum to 100%.
- Every scenario satisfies `WACC > g`.
- Terminal growth reconciles with `ROIC × reinvestment rate` within a declared tolerance.
- ROIC − WACC spread is computed and sourced for every scenario.
- The PEG denominator is a forward growth rate; any historical CAGR cell is labelled a
  verification input and is not referenced by the PEG formula.
- A growth duration is entered for every scenario, with a stated reason it ends.
- No formula error tokens remain after independent recalculation.
- The release summary says `MASTER PASS` only when every hard check is true.

## Check formatting

- Hard checks return a boolean and a message. A check that cannot be evaluated returns
  `FALSE` with the reason, never a blank cell.
- A triage or normalization sheet that is not applicable says "not applicable" with the
  reason, so that a skipped module is distinguishable from a forgotten one.
