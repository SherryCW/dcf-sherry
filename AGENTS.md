# Working agreement

- Keep examples synthetic or user-provided.
- Never invent missing financial facts; return `BLOCKED`.
- Keep valuation results separate from trade instructions.
- Preserve the public/private disclosure boundary in `SECURITY.md`.
- Run `python3 -m unittest discover -s tests -v` after calculation changes.
- Do not weaken `WACC > terminal growth`, probability, bridge, or finite-number checks.
- Do not let the screen produce a price, or the pricing layer produce a classification.
- Do not put a historical growth rate into a PEG denominator.
- Do not compare an implied perpetual growth rate against a near-term consensus growth rate.
- Do not let a missing quality flag or missing quality metric pass silently: absent evidence is
  an open gate, not a false one.
- Do not soften a gate to make an example pass. Change the example instead.
