# Adjudication of the residual comparison disagreements

100 per-pair rows and 98 band rows, from the bounded partial v2 comparison
(`results/live_ab_validation_v2/comparison_v2/comparison_defects.csv`). My standing default was to adjudicate
without editing either side, and no objection was raised.

## The state, and why it is delicate

Every one of the 100 per-pair rows is the same shape. Revealed arm = incumbent, so `sgn = -1`; revealed cost
`L_r = 10.0`; pending candidate certified elapsed `ell = 10.526315789473685`; frozen `tol = 0.05`.

`#12` reports `[-1, -1]`, a collapse. `#11` reports `[-1, 0]`, keeping a tie.

## The adjudication, computed rather than argued

The two implementations use forms that are **equivalent in exact arithmetic and not in floating point at this
boundary**:

- `#11`'s certificate asks `x > L_r/(1 - tol)`. Measured: `L_r/(1-tol) = 10.52631578947368496` and
  `ell = 10.52631578947368496`. **They are equal as float64**, so the strict test fails, no certificate fires,
  and the enclosure stays `[-1, 0]`.
- `#12` evaluates the operative comparator predicate itself, `|x - L_r| > tol * max(|x|, |L_r|)`. Measured at
  `x = ell`: `|x - L_r| = 0.52631578947368496` against `tol*max = 0.52631578947368429`. The first **is** strictly
  greater, so the tier is decisive, the incumbent wins, and the score is `-1`.

Enumerating the feasible completions: the candidate failing gives `-1`; the candidate succeeding at any
`x >= ell` gives `-1`, because decisiveness holds at `x = ell` and for every larger `x`. **The feasible set is
`{-1}` and the tight enclosure is `[-1, -1]`.**

In exact rational arithmetic `ell > 10/0.95` is **true**, so the boundary is not genuinely tied; only the float
rearrangement makes it look tied.

## Verdict

**`#12` is correct and tight. `#11` is conservative, not wrong.** Direction across all 100 rows: `#11` contains
`#12` in **100 of 100**, narrower in **0**. No validity consequence, and no `#11` result is affected.

## The recommendation, and why it is the same defect as before

`#11`'s certificate should evaluate **the predicate the comparator actually uses** rather than an
algebraically-equivalent rearrangement of it. This is the same class of defect as the earlier item-5
incompleteness: **the rule is stated in one algebraic form and the comparator implements another**, and the two
part company exactly where the decision is tightest. Testing a rearrangement is testing a different function at
the boundary.

Scope discipline: this is 100 rows in a **bounded partial run** of 8 of 200 cell streams. It is not a rate, and
the full frozen comparison set has not been run. Neither side was edited to produce this adjudication.
