# Independent verification of the contributed module `src/wincs.py` (post issue #4 fix)

Session: `iclr-winratioagentevals-60` audit worker, 2026-09-17/18. Auditor did not write the code.
Scope: `src/wincs.py` (581 lines) as on disk at audit time, its own tests `src/test_wincs.py`, GitHub issue #4
("Audit blocker: generic multinomial CS projection excludes deterministic boundary laws", opened by ykzeng-yale, no comments),
and the Lindon & Malek (2022) summary in `evidence/lit_sequential.md`.
All numbers below come from scripts the auditor ran in this session (scratchpad `audit_linear.py`, `audit_linear2.py`,
`audit_misc.py`, `audit_coverage_lite.py`, `audit_drift.py`, plus inline checks); nothing is quoted from memory.
`wincs.py` was not edited; proposed patches are given as diffs at the end and were tested only on a scratch copy.

## Verdict

**Needs changes before integration (two code fixes, one of them a validity fix), otherwise sound.**

* The issue #4 defects are fixed: deterministic boundary laws and constant functionals now give exact, correctly ordered bounds
  (`net_benefit([0,3,0]) = (-0.6580048106646681, 1.0)`; analytic lower bound `2*exp(c_n/3)-1 = -0.6580048106646605`;
  constant functional gives exactly `(1.0, 1.0)`).
* `linear_bound` is mathematically correct (Lagrangian/KKT parametrisation, monotone bisection, provably conservative outside
  iterate, feasibility certificate). Against brute force it was never anti-conservative by more than 1.1e-16 (K=3, 1200 bounds vs
  a 1500-point simplex grid) or 5.0e-11 (K=5, 2400 bounds vs multi-start SLSQP), and it is tight to within the reference
  solvers' own resolution.
* `ratio_bound` agrees with a closed-form one-dimensional solution to 3e-13 relative on zero-tie tables and was never
  anti-conservative in 294 K=3 cases.
* **Defect D1 (must fix, crash):** the tightness certificate in `linear_bound` uses an absolute tolerance while `ratio_bound`
  feeds it coefficients of size up to 1e6; `MultinomialCS.win_ratio` raises `RuntimeError` whenever the win-ratio lower bound
  exceeds roughly 1e5 (e.g. counts `[0, 1e7, 0]`, `[1e7, 1e7, 0]`; 17/900 calls in a large-count sweep). A two-line
  scale-invariant fix removes all failures with no change (6.8e-13 relative) elsewhere.
* **Defect D2 (must fix, validity):** both betting capital processes use `max(K+, K-)` against the threshold `1/delta`.
  Waudby-Smith & Ramdas' hedged capital is `max(theta K+, (1-theta) K-)`, i.e. with theta = 1/2 the threshold must be `2/delta`
  (equivalently: average the two capitals). As coded, the only available guarantee is a union bound at level `2*delta`, and for
  long horizons the miscoverage of the coded CS provably exceeds `delta` (Ville's inequality is an equality for each of K+ and K-
  because both converge to 0 a.s.). Empirically at horizons up to 10,000 the observed ever-miss rates stay below `delta` but are about twice those of the corrected rule and grow with the horizon
  (see Section 5), which is why the module's own test passes; this is a finite-horizon artefact of the tiny stakes in the grid,
  not a proof. One-line fix.
* **Defect D3 (should fix, robustness):** `_invert_capital` scans 201 equally spaced candidates; when the betting CS is narrower
  than the grid step (n above ~1e5-1e6 decided pairs) it can contain no grid point and the function returns `nan` for both ends.
  It also reports the *inside* bisection iterate, so the returned interval is a subset of the true CS (anti-conservative by
  at most the bisection resolution, ~6e-7). Seeding the scan with the sample mean (always inside the betting CS) and returning
  the outside iterate fixes both.
* Minor items (D4-D8): undocumented ratio caps, missing input validation, unequal-weight degrees of freedom in
  `clustered_summary`, a relative-margin subtlety in `compare_censored`, and `test_wincs.py` runs its betting test only under
  `__main__` ordering quirks. None affects correctness of the paper-facing quantities.

## 1. Issue #4 reproducers (fixed)

```
>>> MultinomialCS(1).net_benefit([0, 3, 0])
(-0.6580048106646681, 1.0)                      # issue: (-0.658004810664131, 0.9997631258037212)
>>> linear_bound([2,3,4], [1,1,1], np.ones(3), .05, False), linear_bound([2,3,4], [1,1,1], np.ones(3), .05, True)
(1.0, 1.0)                                      # issue: 0.9998987738540442 / 0.9998864406920706 (reversed)
>>> MultinomialCS(1).net_benefit([5, 0, 0]);  MultinomialCS(1).net_benefit([0, 0, 7])
(-0.7012209500854412, 0.7012209500854412);  (-1.0, 0.21866075411842667)
>>> MultinomialCS(1).win_ratio([0, 3, 0]);  MultinomialCS(1).win_ratio([0, 0, 7]);  MultinomialCS(1).win_ratio([5, 0, 0])
(0.20626911763793856, inf);  (0.0, 1.5597075924979085);  (0.0, inf)
>>> MultinomialCS(1).win_odds([0, 3, 0]);  MultinomialCS(1).win_odds([5, 0, 0])
(0.20626911763793856, inf);  (0.17562624649050232, 5.693909765667258)
>>> MultinomialCS(1).net_benefit([0, 0, 0]);  MultinomialCS(1).net_benefit([0, 1, 0])
(-1.0, 1.0);  (-0.9666666666666777, 1.0)
```
The `[0,3,0]` lower bound has a closed form: the CS is `{3 log p_w > c_n}`, the minimum of `p_w - p_l` is at `p_l = 1 - p_w`,
`p_w = exp(c_n/3) = 0.170997594668`, so `NB_lo = 2 exp(c_n/3) - 1 = -0.6580048106646605`; the code returns
`-0.6580048106646681` (7.6e-15 below, i.e. conservative outside iterate). `win_ratio([0,3,0]) = 0.2063 = p_w/(1-p_w)` at the same
point. The all-win law has `NB = 1`, `WR = WO = inf` and is included. The module's own `test_boundary_laws_issue4` passes.

## 2. (a) Dirichlet-multinomial mixture martingale and CS

Definitions in the code: `log M_n(p) = log B(prior + x) - log B(prior) - sum_k x_k log p_k`,
`CS_n = {p : sum_k x_k log p_k > c_n}`, `c_n = log B(prior + x) - log B(prior) + log delta`.

* This is exactly Lindon & Malek Eq. (3) / Theorem 2.4 as summarised in `evidence/lit_sequential.md`
  (`O_n(theta) = Beta(alpha0 + S_n)/Beta(alpha0) * theta^{-S_n}`, `C_n(u) = {theta : O_n(theta) < 1/u}`), with
  `Beta(v) = prod Gamma(v_i)/Gamma(sum v_i)` implemented as `log_beta`. The strict inequality matches their definition; `in_cs`
  uses `>`, `linear_bound` optimises over the closure `>=`, which has the same suprema because the strict superlevel set of the
  concave log-likelihood is non-empty (the MLE is always inside, see below).
* Martingale property checked by exhaustive enumeration: `E_p[M_n] = 1.000000000000` for n in {1,3,6}, three laws (including one with
  a near-zero cell) and a non-uniform prior `(1, 2, 0.5)`; the closed form equals the product of predictive ratios
  (`-1.329724009631` both ways). Ville then gives `P(exists n: p_true not in CS_n) <= delta`, and every functional bound is an image
  of the same set, so simultaneity across NB, WR, WO, tier contributions and all n holds without any multiplicity correction.
* `M_n(MLE) = marginal likelihood / maximum likelihood <= 1 < 1/delta`, so CS_n is never empty and always contains the MLE
  (empirical max over 500 random tables: 0.228). This is what makes the "exact boundary" branch of `linear_bound` valid
  (see 3).
* The CS lives in the face where every positive-count cell has `p_k > 0` (zero-count cells may have `p_k = 0`; the code uses
  `0 log 0 = 0`). Consequently a functional's supremum equals the vertex value `cmax` iff every positive-count cell carries the
  maximal coefficient, and otherwise is strictly less. The code's two-way split on `top[pos].all()` reflects exactly this.
* Default prior `1.0` is Lindon & Malek's uniform choice (their recommended informative alternative `alpha = k theta0` is
  supported through the `prior` argument). Prior sensitivity on `[10,30,20]`: lower/upper NB `(-0.337, 0.613)` at prior 0.1,
  `(-0.251, 0.544)` at 1.0, `(-0.227, 0.525)` at 5.0. As expected the CS is exact for every prior fixed before data.
* Time-uniform coverage simulation: see Section 5.

## 3. (b) `linear_bound`

Problem: `sup c'p` over `{p in simplex : ell(p) >= c_n}`, `ell(p) = sum x_k log p_k`.

*Derivation check.* Maximising `c'p + lam ell(p)` on the simplex: for `p_k > 0` stationarity gives
`c_k + lam x_k/p_k = nu`, i.e. `p_k = lam x_k/(nu - c_k)`; writing `nu = cmax + g` with `g >= 0` gives the code's
`p_k = lam x_k/(g + d_k)`, `d_k = cmax - c_k >= 0`. Zero-count cells have derivative `c_k - nu <= 0`, hence `p_k = 0` unless
`c_k = cmax` and `g = 0`, in which case they absorb the remaining mass (the `free_top` branch). `g` is fixed by `sum p = 1`
(`f(g) = 0`, `f` strictly decreasing, bracket doubling + `brentq` at machine precision). If a positive-count cell is at the top,
`f(0+) = +inf` so a root `g > 0` exists; otherwise `f(0) <= 0` triggers the `g = 0` remainder branch. Every case returns a KKT
point of a concave problem, hence the exact Lagrangian maximiser.

*Monotonicity.* For `lam1 < lam2` adding the two optimality inequalities gives `(lam2 - lam1)(ell(p2) - ell(p1)) >= 0`, so
`ell(p(lam))` is non-decreasing and `c'p(lam)` non-increasing; the log-scale bisection is therefore well defined. The bracket
searches cannot fail in exact arithmetic: as `lam -> 0` some positive-count non-top cell gets mass `~lam` so `ell -> -inf`
(the non-exact case), and `ell(p(lam)) -> ell(MLE) >= c_n - log delta > c_n` as `lam -> inf`.

*Conservativeness of the outside iterate.* For any feasible `p` and any `lam`,
`c'p <= c'p_lam + lam (ell(p_lam) - ell(p)) <= c'p_lam + lam (ell(p_lam) - c_n) < c'p_lam` when `ell(p_lam) < c_n`.
So `obj_out >= sup` always (weak duality), independent of numerical tolerances; `p_in` is feasible so `obj_in <= sup`. The
certificate (`ell_in >= c_n - 1e-9`, simplex membership, `obj_out - obj_in <= 1e-7`) guarantees the reported bound is within
1e-7 of an explicitly feasible point. Verified rigorous.

*Exact branch.* When `top[pos].all()`, `p_face` is the MLE, always inside (Section 2), so returning `cmax` is exact.

*Numerical results (delta = 0.05, uniform prior).*

| check | cases | worst anti-conservative | worst looseness |
|---|---|---|---|
| K=3, random n in [1, 5000] incl. forced zeros, coef in {NB, p_win, constant, random}; vs 1500-point simplex grid | 1200 bound pairs | 1.1e-16 | 2.5e-3 (grid resolution 1/1500 per coordinate; NB step 1.3e-3) |
| K=5, random n in [1, 5000], 25% tables with 1-3 zero cells, coef in {NB, tier0, tier1, p_win, constant, random}; vs 12-start SLSQP | 2400 bounds (12 SLSQP failures skipped) | 5.0e-11 | 2.4e-2 in 3 cases where SLSQP stalled; the module's certificate proves a feasible point within 1e-7 of the bound in every call |
| delta monotonicity: delta in {0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 1e-3, 1e-6}, K in {3,5} | 1600 evaluations | 0 violations (bounds widen monotonically) | - |
| adversarial coefficient scales 1e-3..1e6, K in {3,5,7}, n up to 1e7, delta down to 1e-9 | 5844 calls | 0 exceptions | - |
| huge counts n = 1e5..1e9, K=3/5 | 10 tables | no certificate failures; widths shrink as n^{-1/2} (K=3: 2.32e-2, 7.93e-3, 2.68e-3, 9.0e-4, 3.0e-4) | ~2-3 ms per bound |

Degenerate tables (`[0,0,0]`, single observations, `[1e6,0,0]`, `[1e8,3e8,2e8]`, K=5 analogues) all return finite, ordered,
sensible bounds (full table in `audit_linear.log`). `[0,0,0]` gives `(-1,1)`, `(0,inf)`. Runtime: 0.82-0.89 ms per call
(K=3/5, n <= 5000).

## 4. (c) `ratio_bound`

Level-set reduction: `sup num'p/den'p >= r` attainable iff `max (num - r den)'p >= 0`; requires `den'p > 0` on the CS for the
upper bound, which the code checks first (`inf den'p <= 1e-12 -> inf`), and `num'p > 0` for the lower bound (`-> 0`). The bisection
invariants (`a` attainable / `b` not, for the upper; `a` not attainable / `b` attainable for the lower) make the returned values
conservative in both directions; 80 geometric halvings of `[1e-6, 1e6]` give ~1e-12 relative resolution.

* Independent check on zero-tie tables, where the extremum is on the `p_t = 0` face and solves
  `x_w log p_w + x_l log(1 - p_w) = c_n` in one variable: `[0,8,20]` exact `0.06111833` vs code `0.06111833`
  (3.3e-13 relative); `[0,4,4]` 3.1e-13; `[0,249,25]` 4.5e-13; `[0,10,0]` 8.6e-13.
* 294 K=3 cases (WR and WO, random n up to 5000, 20% with a zero cell) vs a 6000-point one-dimensional boundary parametrisation:
  worst anti-conservativeness 0. All "looseness" flags in that run were traced to the reference (grid) missing the
  `p_l -> 1 - p_w` face or the `p_l` resolution; none to the code.
* Unbounded handling is correct: `[0,3,0] -> (0.206, inf)`, `[5,0,0] -> (0, inf)` (0/0 law inside the set), `[0,0,7] -> (0, 1.56)`.
* Runtime ~80-90 ms per bound (80 linear subproblems), ~0.4-0.5 s for NB+WR+WO at n = 1e6-1e9.

**D1 (crash) - reproducer:**
```
>>> MultinomialCS(1).win_ratio([0, 1e7, 0])
RuntimeError: linear_bound: bound gap too large (1.39662e-07)
>>> MultinomialCS(1).win_ratio([1e7, 1e7, 0])      # same error; [0, 1e6, 0] works only by luck (33406.76, inf)
```
Mechanism: `ratio_bound` calls `linear_bound` with `coef = num - m*den`, `m` up to 1e6. The lam-bisection stops at relative
tolerance 1e-12, and the objective moves by about `m * 1e-12` per unit of relative lam near the boundary, so the certified gap is
`~0.78 * m * 1e-12` (1.4e-7 at `m = 10^5.25 = 177828`, the fourth geometric midpoint), which exceeds the *absolute* tolerance
`1e-7 * max(1, |obj_out|)` because `|obj_out| < 1` there. Every table whose WR lower bound (or WO/WR upper bound) exceeds
~1.3e5 hits this; in a sweep of 300 random tables with n in [1e5, 1e9] (30% with a zero cell), 17/900 functional calls raised.
Fix (tested on a scratch copy, 0/900 failures afterwards, bounds on 200 moderate tables unchanged to 6.8e-13 relative): make
the certificate tolerance scale with the coefficient magnitude and normalise the ratio subproblems (patch P1 below).
Note also that the bound is provably conservative even when the certificate trips, so raising is stricter than necessary;
a warning plus returning `obj_out` would be an acceptable alternative.

**D4 (documentation):** `lo=1e-6, hi=1e6` are hard caps. `inf` for the upper bound means "a ratio above 1e6 is attainable",
not "unbounded" (e.g. `[170, 2622, 1]` returns `inf` although the true supremum is finite, ~1.6e8), and the lower bound is
capped at 1e6 (`[0, 1e8, 0] -> 999999.9999999999` after P1, true value ~3e6). Both directions remain conservative; document it.

## 5. Time-uniform coverage simulations

All simulations: i.i.d. cells, uniform prior, `audit_coverage_lite.py` / `audit_drift.py` (a larger run with N up to 20,000
was started but killed after 45 min of CPU contention with other agents' jobs; the lean run reproduces every check at >= 4000
reps). "Ever-miss" = fraction of replications in which the true parameter leaves the CS at *some* n <= N.

**Multinomial CS (Dirichlet-multinomial mixture), N = 2000, 4000 reps, cells (tie, win, loss).** Miscoverage of `p` is measured
on the martingale directly; miscoverage of the NB and `p_win` projections is measured exactly with the ternary constrained
log-likelihood (true value inside the projection iff the hyperplane meets the CS), spot-checked against `linear_bound` on 300
random looks (0 disagreements).

| delta | p | ever-miss p (se) | ever-miss NB projection | ever-miss p_win projection |
|---|---|---|---|---|
| 0.05 | (0.5, 0.3, 0.2) | 0.0335 (0.0028) | 0.0065 | 0.0065 |
| 0.05 | (0.05, 0.9, 0.05) | 0.0200 (0.0022) | 0.0110 | 0.0090 |
| 0.05 | (0.2, 0.2, 0.6) | 0.0328 (0.0028) | 0.0097 | 0.0070 |
| 0.05 | (0.02, 0.49, 0.49) | 0.0205 (0.0022) | 0.0045 | 0.0057 |
| 0.10 | (0.5, 0.3, 0.2) | 0.0717 (0.0041) | 0.0127 | 0.0155 |
| 0.10 | (0.05, 0.9, 0.05) | 0.0377 (0.0030) | 0.0203 | 0.0245 |
| 0.10 | (0.2, 0.2, 0.6) | 0.0815 (0.0043) | 0.0190 | 0.0198 |
| 0.10 | (0.02, 0.49, 0.49) | 0.0597 (0.0037) | 0.0107 | 0.0130 |

All rates are below `delta` (as they must be: exact martingale, finite horizon). The projections are markedly conservative for
a single functional (a factor 3-5 below delta), which is the price of simultaneity over all functionals; the paper should
say so when comparing widths with the betting CS.

**Betting capital evaluated at the true mean (ternary scores), 4000 reps.** "Coded" is `max(K+, K-)` against `1/delta` as in
`betting_log_capital_ternary`; "average" is the Waudby-Smith & Ramdas hedged capital `(K+ + K-)/2` (patch P2).

| delta | p (pos, tie, neg) | N | coded max-hedge ever-miss (se) | average-hedge ever-miss |
|---|---|---|---|---|
| 0.05 | (0.35, 0.4, 0.25) | 2000 | 0.0180 (0.0021) | 0.0095 |
| 0.05 | (0.45, 0.1, 0.45) | 2000 | 0.0232 (0.0024) | 0.0123 |
| 0.05 | (0.5, 0.0, 0.5) | 10000 | 0.0372 (0.0030) | 0.0173 |
| 0.05 | (0.3, 0.4, 0.3) | 10000 | 0.0253 (0.0025) | 0.0100 |
| 0.10 | (0.35, 0.4, 0.25) | 2000 | 0.0470 (0.0033) | 0.0253 |
| 0.10 | (0.45, 0.1, 0.45) | 2000 | 0.0508 (0.0035) | 0.0240 |
| 0.10 | (0.5, 0.0, 0.5) | 10000 | 0.0775 (0.0042) | 0.0345 |
| 0.10 | (0.3, 0.4, 0.3) | 10000 | 0.0612 (0.0038) | 0.0293 |

The coded rule is consistently about twice the corrected rule (union of two one-sided level-`delta` events), and its rate grows
with the horizon (0.047-0.051 at N = 2000 to 0.061-0.078 at N = 10,000 for delta = 0.1), as the D2 argument predicts; it stays
below `delta` at these horizons only because the small stakes have not yet reached their Ville limit. No finite-N simulation can
certify the coded rule at level `delta`; the corrected rule is certified by the martingale argument.

**Public API over looks (every 25 pairs up to N = 2000, 4000 reps, delta = 0.05).**

| p (pos, tie, neg) | NB betting CS ever-miss | nan fraction | WR CS (decided pairs) ever-miss | final NB width | final WR CS (truth) |
|---|---|---|---|---|---|
| (0.35, 0.4, 0.25) | 0.0160 | 0 | 0.0158 | 0.111 | [1.161, 1.698] (1.40) |
| (0.45, 0.1, 0.45) | 0.0145 | 0 | 0.0145 | 0.137 | [0.860, 1.168] (1.00) |
| (0.2, 0.7, 0.1) | 0.0150 | 0 | 0.0152 | 0.078 | [1.522, 2.675] (2.00) |

(About 105-112 s per configuration for the vectorised inversion of 4000 x 80 looks.)

**D3 reproducer (`_invert_capital` grid miss).** Deterministic near-expected counts `n * (0.35 + s/2, 0.4, 0.25 - s/2)`:

| n | shift s | NB betting CS | WR CS |
|---|---|---|---|
| 1e4 | 0 | (0.0750, 0.1249), width 0.0499 | (1.286, 1.524) |
| 1e5 | 0 | (0.0921, 0.1079), width 0.0158 | (1.363, 1.438) |
| 1e6 | 0 | (0.0975, 0.1025), width 0.0050 | (1.388, 1.412) |
| 1e6 | 0.003 | **(nan, nan)** | (1.402, 1.427) |
| 1e6 | 0.005 | **(nan, nan)** | **(nan, nan)** |
| 1e7 | 0 | (0.0992, 0.1008), width 0.0016 | **(nan, nan)** |
| 1e7 | 0.003 / 0.005 | **(nan, nan)** | **(nan, nan)** |

Once the CS is narrower than the grid step (0.01 on [-1,1], 0.005 on [0,1]) the result depends on where the interval falls
relative to the grid and is `nan` most of the time. Endpoint side on `[300,400,250]`: `logcap(lo) - thr = -1.4e-6` and
`logcap(hi) - thr = -4.4e-5` (both endpoints are *inside*); at `lo - 1e-7` the capital already exceeds the threshold, so the
reported interval is a strict subset of the true CS by ~1e-7 (negligible in practice, but the wrong side for a guarantee).

## 6. (d) Ternary closed forms and e-process / CS equivalence

* Quadratic: from `x_w/(u+c) + x_l/u - 2x_t/(1-2u-c) = 0` multiplying out gives `A = -2n`,
  `B = x_w(1-c) + x_l(1-c) - 2x_l c - 2x_t c`, `C = x_l c (1-c)` - matches the code. Candidates = both roots + both endpoints,
  clipped to `[max(0,-c), (1-c)/2]`, `nan -> -inf`: correct for zero counts and for `c = +-1` (single feasible point).
* 3000 random cases (n in [0, 300], c in [-1, 1] including +-1, +-0.99x and 0) vs a dense-grid + bounded scalar optimiser:
  worst absolute difference 3.2e-6 on a value of magnitude 2e3 (1.6e-9 relative; the one flagged case `[261, 2, 0]`,
  `c = -0.9989` is the reference's tolerance, the closed form is the larger value).
* `ternary_log_eprocess_nb = inf_{H0} M_n(p)`: valid e-process for the composite `H0: NB <= c` (infimum of test martingales,
  as in Ramdas et al. 2023), with the supremum over the half-space placed at the MLE if feasible and on the hyperplane
  otherwise (concavity). Equivalence `E_n >= 1/delta  <=>  CS_n ∩ H0 = ∅  <=>  NB_lo > c`: 1497/1497 random cases agree
  (n in [1,400], 20% zero cells, delta in {0.01, 0.05, 0.2}, c in [-0.95, 0.95]); none within 1e-6 of the boundary.

## 7. (e) Betting CS inversion and `win_ratio_cs_decided`

*Capital processes.* For a fixed grid of stakes `lam` (prespecified, `|lam| <= 0.5` for range-2 ternary scores, `<= 1` for the
Bernoulli version) each `prod (1 + lam (z_i - m))` is a nonnegative test martingale for the mean `m`, and the mixture over the
grid is one too; a stake hitting `1 + lam(z - m) = 0` gives `-inf` log-capital for that stake only (handled by `log1p` /
`nan -> -inf`). This part is standard (Waudby-Smith & Ramdas 2024).

*D2 (validity).* The code compares `max(K+_n(m), K-_n(m))` with `1/delta`. WSR's hedged capital is
`K± = max(theta K+, (1-theta) K-)`, valid because it is dominated by the martingale `theta K+ + (1-theta) K-`; with
`theta = 1/2` the CS is `{m : max(K+, K-) < 2/delta}`. The coded rule is `{m : max(K+, K-) < 1/delta}`, i.e. a level-`delta` CS
from each one-sided capital combined without a union-bound correction: the guarantee available is `2 delta`. It is not merely
loose: each one-sided mixture capital converges to 0 a.s. under the true mean (every constant-stake term has negative drift),
so by Ville's equality `P(sup_n K+_n >= 1/delta) -> delta` as the horizon grows, and the coded miscoverage event
`{sup max(K+, K-) >= 1/delta}` contains it strictly. The finite-horizon rates in Section 5 are below `delta` only because
the smallest stakes (1e-4) need extremely long horizons to reach their Ville limit. Fix: patch P2 (average the two capitals,
or equivalently test the max against `2/delta`). Cost: slightly wider intervals (the stake mixture is then over 80 signed stakes).

*Quasi-convexity and inversion.* `K+(m)` is non-increasing in `m` and `K-(m)` non-decreasing (each factor is monotone), so
`max(K+, K-)` is quasi-convex and the CS is an interval; `_invert_capital`'s "first inside / last inside" logic is valid.

*D3 (grid miss / inside iterate).* See table in Section 5 for the `nan` behaviour at large n. Also, the reported lower end is the
last *inside* bisection iterate (`lo = b`) and the upper end the last inside iterate (`hi = a`), so the returned interval is a
subset of the true CS, anti-conservative by up to `(grid step)/2^14 ~ 6e-7`. Measured on `[300,400,250]`: capital at
`lo - 1e-7` and `hi + 1e-7` is already above the threshold (see `audit_coverage.log`). Patch P3 returns the outside iterates
and seeds the scan with the sample mean `m_hat`, which is always inside since by AM-GM
`prod (1 + lam (z_i - m_hat)) <= (mean(1 + lam (z_i - m_hat)))^n = 1` for both signs of `lam`.

*Conditioning on decided pairs (validity argument).* Let `Z_i in {-1,0,+1}` be i.i.d. with cell law `p`, `D_i = 1{Z_i != 0}`,
`W_i = 1{Z_i = +1}`, `q = p_w/(p_w + p_l) = WR/(1+WR)`. Two independent arguments:
1. *Thinning.* For i.i.d. `Z`, the subsequence `(W_{tau_j})` at the decided times `tau_1 < tau_2 < ...` is i.i.d. Bernoulli(q)
   (strong Markov / thinning of an i.i.d. sequence by an event determined by the same coordinate). A CS valid uniformly in the
   decided-count index `j` is valid uniformly in calendar time `n`, because the CS at time `n` is the CS at index `j = N_n`
   (`N_n` = number of decided pairs by `n`, non-decreasing), so `{exists n: q not in CS_{N_n}} ⊆ {exists j: q not in CS_j}`.
2. *Direct martingale in the original filtration.* `K_n = prod_{i<=n} (1 + lam (W_i - q))^{D_i}` satisfies
   `E[K_n | F_{n-1}] = K_{n-1} [(1 - P(D_n=1)) + P(D_n=1) (1 + lam (E[W_n | D_n=1] - q))] = K_{n-1}`, so it is a test
   martingale for `q` in the pair filtration without any i.i.d. assumption on the *tie rate*: only
   `P(W_n = 1 | F_{n-1}, D_n = 1) = q` is needed. The predictable thinning is therefore harmless, and a drifting tie
   probability with a constant conditional win ratio is still covered (checked: table below).
   The guarantee does *not* extend to a drifting WR (checked: 80% ever-miss when q drifts 0.5 -> 0.7 and the CS is compared to
   the average q), which is expected and consistent with the module docstring ("for iid pairs").

| WR CS on decided pairs, q = 0.6 (WR 1.5), N = 3000, delta = 0.05, 4000 reps | coded max-hedge | average-hedge (P2) |
|---|---|---|
| i.i.d., tie rate 0.4 | 0.0213 | 0.0105 |
| tie rate drifting 0.05 -> 0.9, constant q | 0.0185 | 0.0085 |
| tie rate step 0.9 -> 0.05 at n = 500, constant q | 0.0307 | 0.0177 |
| q drifting 0.5 -> 0.7 (WR not constant; not a defect) | 0.8023 | - |

Mapping `q -> q/(1-q)`: monotone, so endpoints map to endpoints; `q_hi >= 1 - 1e-12 -> inf` and `n = 0 -> (0, inf)` are
handled. `q_lo = 1` would give `inf/inf`; unreachable in practice (q = 1 is always inside when all decided pairs are wins).

## 8. (f) `clustered_summary`

* Estimand: fixed-weight average over tasks of the within-task win/loss rates from `task_level_scores` (all-pairs,
  diagonal or off-diagonal pairing, each unbiased for its own within-task expectation). Tasks are the clusters, so the U-statistic
  dependence between replicate comparisons inside a task is absorbed entirely; only between-task variability enters.
* Equal weights: `nb_se` equals `sd(win - loss)/sqrt(T)` to 1e-10 and the CI equals the textbook `t_{T-1}` interval.
  Weighted: `Var = sum w_t^2 (d_t - d_bar)^2 * T/(T-1)`, `d_bar` the weighted mean - matches the code to 1e-10.
* Delta method: `Var(log p_w - log p_l) = v_w/p_w^2 + v_l/p_l^2 - 2 c_wl/(p_w p_l)` (correct; jackknife 0.1222 vs
  delta 0.1217 on a T=50 example). Win odds `= (1+NB)/(1-NB)` with `d log WO/dNB = 2/(1-NB^2)` (correct; identity verified
  to 1e-10). `t_{T-1}` reference; `T = 1 -> nan`; `p_w = 0` or `p_l = 0 -> WR nan/inf with nan CI` (sensible).
* Coverage (4000 reps, T = 40, 4 replicate runs per task, exact truth): gamma-distributed weights: NB 0.979, WR 0.979
  (conservative, discreteness of 4 runs); **one task carrying 43% of the weight: NB 0.924** (nominal 0.95). The `T/(T-1)`
  factor and `T-1` degrees of freedom are appropriate for equal weights only; with strongly unequal weights the effective number
  of clusters is `(sum w)^2 / sum w^2` and the `t` quantile should use `df_eff - 1` (Kish) or a Satterthwaite approximation
  (**D6**, minor: only matters for domain-balancing weights that concentrate on few tasks). `weights` summing to 0 or negative
  produce `nan` silently (**D5**).
* `task_bootstrap`: percentile bootstrap over tasks with re-normalised weights; consistent with the above. `stratified_combine`
  returns `sum w^2 Var` - correct for independent strata.

## 9. (g) `compare_censored`

Rule: A wins iff A completed and `t_a + margin < t_b` (B had not finished by then, completed or censored); symmetric for B;
otherwise tie. Checked all 11 configurations of (done/censored) x (order/equality): the score is antisymmetric under swapping
arms in every case; both censored -> tie; A done at 3 vs B censored at 2.9 -> tie (B might have finished at 2.95), vs B censored
at 3.5 -> A wins. This is Gehan/Pocock-style pairwise scoring and is semantically right for *timeouts as independent
right-censoring*. Two caveats to document rather than fix:
* The estimand is defined with respect to the censoring (timeout) mechanism: a longer timeout in one arm, or timeouts
  correlated with difficulty, changes `p_tie` and hence WR/WO (NB is affected less since indeterminate pairs score 0). Paper text
  must state that both arms share the same timeout policy, or that the timeout itself is a protocol outcome.
* `relative=True` uses `margin * max(t_a, t_b)` where `t_b` may be a censoring time, so the margin is inflated by the timeout
  (**D7**, minor; e.g. margin 0.5 with B censored at 100 requires `t_a < 50`). Consider `margin * min(t_a, t_b)` or the
  completed time only. `nan` times silently become ties (**D5**).

## 10. Other observations

* Input validation gaps (**D5**): `delta = 0` returns the whole simplex silently, `delta > 1` returns a nonsense set, non-integer
  and `nan` counts are accepted (`[nan,1,1] -> (-1,1)`), `inf` counts raise from inside `brentq`, and a prior of the wrong length
  fails with a broadcast error. `pairs_for_power` does not check `net_benefit != 0`.
* `test_wincs.py` (**D8**): `test_betting_cs` and `test_boundary_laws_issue4` are defined after the first `__main__` block and
  run only via the later `__main__` blocks; under `pytest` all functions run, but the file has no pytest fixtures for the 60 s
  runtime (measured 63 s wall). The coverage tests use 1000-4000 reps and `<= delta + 3 se` acceptance, which cannot detect the
  D2 factor at these horizons; add a long-horizon check or, better, a unit test that the hedged capital at the sample mean
  is <= 1 and that the two-sided threshold is `2/delta`.
* `functionals` returns `win_ratio = inf` when `p_l = 0` even if `p_w = 0` (0/0); harmless for display.
* Performance is adequate for online monitoring: 0.85 ms per linear bound, ~85 ms per ratio bound, the full
  `MultinomialCS` set in ~0.35-0.5 s even at n = 1e9; betting inversion is vectorised over looks.

## 11. Proposed patches (not applied; tested on a scratch copy only)

**P1 - scale-invariant certificate and ratio subproblems (fixes D1).**
```diff
--- a/src/wincs.py  (linear_bound, certificate)
-        if obj_out - obj_in > 1e-7 * max(1.0, abs(obj_out)):
+        if obj_out - obj_in > 1e-7 * max(1.0, abs(obj_out), float(np.abs(c).max())):
             raise RuntimeError('linear_bound: bound gap too large (%g)' % (obj_out - obj_in))
--- a/src/wincs.py  (ratio_bound: normalise every subproblem so coefficients are O(1))
-        if linear_bound(counts, num - b * den, prior, delta, True) >= 0:
+        if linear_bound(counts, (num - b * den) / max(1.0, b), prior, delta, True) >= 0:
 ...
-            if linear_bound(counts, num - m * den, prior, delta, True) >= 0:
+            if linear_bound(counts, (num - m * den) / max(1.0, m), prior, delta, True) >= 0:
 ...
-        if linear_bound(counts, num - a * den, prior, delta, False) <= 0:
+        if linear_bound(counts, (num - a * den) / max(1.0, a), prior, delta, False) <= 0:
 ...
-            if linear_bound(counts, num - m * den, prior, delta, False) <= 0:
+            if linear_bound(counts, (num - m * den) / max(1.0, m), prior, delta, False) <= 0:
```
Result on the scratch copy: `[0,1e7,0] -> (289529.08, inf)`, `[0,1e8,0] -> (999999.99 [cap], inf)`, `[1e7,1e7,1] -> (325535.99, inf)`;
0/900 exceptions in the large-count sweep; 200 moderate tables identical to 6.8e-13 relative. Also document the caps
(`lo`, `hi`) in the docstring (D4).

**P2 - hedged capital at the correct level (fixes D2).** In both `betting_log_capital_ternary` and
`betting_log_capital_bernoulli`:
```diff
-    return np.maximum(logk(lam), logk(-lam))
+    # Hedged capital of Waudby-Smith & Ramdas (theta = 1/2): the average of the two one-sided mixture capitals is itself a
+    # test martingale, so {m : capital < 1/delta} is a level-delta CS. max(K+, K-) alone only gives level 2*delta.
+    return np.logaddexp(logk(lam), logk(-lam)) - np.log(2)
```
(Equivalent alternative: keep `max` and compare against `log(2/delta)` in `_invert_capital`.) Update the docstrings and
`test_betting_cs` accordingly; widths grow slightly.

**P3 - robust inversion (fixes D3).** In `_invert_capital`, accept an optional `center` (sample mean) that is always inside,
insert it into the scan, and return the *outside* iterates:
```diff
-def _invert_capital(logcap, delta, lo0=-1.0, hi0=1.0, coarse=201, iters=14):
+def _invert_capital(logcap, delta, lo0=-1.0, hi0=1.0, coarse=201, iters=14, center=None):
     thr = np.log(1 / delta)
     ms = np.linspace(lo0, hi0, coarse)
-    inside = np.stack([logcap(np.asarray(m)) < thr for m in ms], -1)
+    inside = np.stack([logcap(np.asarray(m)) < thr for m in ms], -1)
+    if center is not None:   # sample mean: capital <= 1 there (AM-GM), so it is always inside
+        c = np.clip(np.asarray(center, float), lo0, hi0)
+        j = np.clip(np.searchsorted(ms, c), 1, coarse - 1)   # bracket ms[j-1] <= c <= ms[j]
+        # mark the bracketing grid points as "inside" only for locating first/last; bisect from c itself
+        inside[..., j - 1] |= True; inside[..., j] |= True   # (then use c as the inside seed in the two bisections below)
 ...
-    lo = np.where(first > 0, b, lo0)
+    lo = np.where(first > 0, a, lo0)     # a is the last iterate OUTSIDE the set: conservative
 ...
-    hi = np.where(last < coarse - 1, a, hi0)
+    hi = np.where(last < coarse - 1, b, hi0)
```
and pass `center=(pos - neg)/max(n,1)` from `betting_cs_ternary` and `center=n_win/max(n,1)` from `win_ratio_cs_decided`.
A simpler drop-in alternative is `coarse = max(201, int(4 * sqrt(n_max)))` so the grid step is always below the CS half-width,
at higher cost. The exact seeding code should be written by the module owner; the sketch above only fixes the semantics.

**P5 - validation (D5).** Add `if not 0 < delta < 1: raise ValueError`, `np.isfinite(counts).all()`, prior length check in
`MultinomialCS._prior`, `weights` positivity in `clustered_summary`, and a `nan` check in `compare_censored`.

## 12. What was not checked

* `task_level_scores` with `eligible` masks (only the default path was exercised through the module's own offline test).
* Non-uniform priors in the coverage simulation (only prior = 1; exactness for any fixed prior follows from the martingale
  identity, which was verified with prior (1, 2, 0.5)).
* Betting CS at horizons beyond 10,000 (cost); the D2 argument at long horizons is analytical, not simulated, though the
  horizon trend 2,000 -> 10,000 is in the expected direction.

## Appendix: commands

```
cd /Users/yukangzengcmac/ICLR-WinRatioAgentEvals
.venv/bin/python src/test_wincs.py            # 63 s, all pass
.venv/bin/python <scratchpad>/audit_linear.py   .venv/bin/python <scratchpad>/audit_linear2.py
.venv/bin/python <scratchpad>/audit_misc.py     .venv/bin/python -u <scratchpad>/audit_coverage_lite.py
.venv/bin/python <scratchpad>/audit_drift.py
```
Scratchpad: `/private/tmp/claude-501/-Users-yukangzengcmac-ICLR-WinRatioAgentEvals/35a3ef1c-e430-45ac-b78e-94ba942c34a1/scratchpad/`
(logs `audit_*.log`, patched copy `wincs_patched.py`).
