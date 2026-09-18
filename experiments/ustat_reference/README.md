# Sequential U-statistic reference baseline (GitHub issue #3)

Estimand-aligned all-pairs comparator for the disjoint-pair procedures of the
paper. Everything here is a reference baseline; it does not modify the paper's
code (`src/winstats.py`, `experiments/run_simulations.py`,
`experiments/run_online_methods.py` are imported read-only, and
`results/online_methods_results.csv` is read only for the reproduction check).

Revision history: first version audited as commit `e1ea314`
(`reviews/round8_ustat_preintegration_review.md`); this version answers the
four points of that review (AsympCS guarantee statement, simultaneous vs
retained guarded conventions, guardrail-boundary calibration nulls, Gaussian-limit
wording of independent increments). The result files of the audited version are
kept in `results/ustat_reference/previous_e1ea314/`.

## Files

| File | Content |
|---|---|
| `ustat.py` | Library: exact re-draw of the paper's generator with raw runs (`generate_raw`), O(n log n) all-pairs hierarchical U-statistic and Hoeffding/Sen projection variance at many looks (`hierarchical_prefix_stats`), brute-force oracle (`kernel_matrix`, n <= 2000 only), analytic conditional means and Monte Carlo efficiency components (`efficiency_components`), Lan-DeMets alpha-spending boundaries by Armitage-McPherson-Rowe recursion (`gs_boundaries`, `gs_exit_probabilities`, `spending`), one-sided normal-mixture boundary (`one_sided_normal_mixture_boundary`). |
| `run_ustat_reference.py` | Study: 8 scenarios of `run_online_methods.SCENARIOS`, seeds `SeedSequence([20260918, j])`, 10000 records per arm, 2000 replicates, 199 looks (100..10000 step 50) for the anytime rules, 10 planned looks (1000k) for group-sequential rules. `--calibration-only`: four null scenarios at 10000 replicates (see Calibration). |
| `rare_event_diagnostic.py` | Round 9 archive of the report's Section 4.7 diagnostic: re-runs ONLY the `compliance_boundary` calibration scenario on the frozen stream `SeedSequence([20260918, 109])` (10000 replicates, batch 25, single process, about 8 s) and records every false rejection of the COMPONENT compliance gate (first-crossing look n, noncompliant runs per arm at that look, statistic, variance estimate) for each rule; asserts that its counts equal the `gate_compliance_*` rows of `null_calibration.csv`. Writes `rare_event_diagnostic.csv` and `rare_event_diagnostic_manifest.json` (seeds, code hashes, runtime, summary). |
| `../../results/ustat_reference/` | `ustat_reference_results.csv` (deployment rates, Wilson CI, runs used, median stop; one row per method and convention), `ustat_reference_gate_rates.csv` (per-gate rejection rates, convention-free), `ustat_reference_efficiency.csv` (Var(h), zeta_10, zeta_01, ARE, predicted fixed-horizon power), `ustat_reference_estimator_check.csv` (empirical vs estimated variance at n = 10000), `ustat_reference_reproduction_check.json` (row-by-row comparison of the recomputed betting rows with `results/online_methods_results.csv`), `null_calibration.csv` + `calibration_manifest.json` (four nulls, 10000 replicates), `rare_event_diagnostic.csv` + `rare_event_diagnostic_manifest.json` (component compliance-gate false rejections at `compliance_boundary`, one row each), `manifest.json` (seeds, hashes, boundaries, boundary validation, runtime, peak RSS, machine), `run.log`, `calibration_run.log`; `previous_e1ea314/` holds the audited version's outputs. |
| `../../evidence/ustat_reference_report.md` | Report: response to the pre-integration review, derivation-to-code correspondence, and the comparison tables. |

## Run

```
.venv/bin/python experiments/ustat_reference/run_ustat_reference.py            # full study (2000 replicates, 8 workers)
.venv/bin/python experiments/ustat_reference/run_ustat_reference.py --replicates 50 --out /tmp/smoke
.venv/bin/python experiments/ustat_reference/run_ustat_reference.py --calibration-only --replicates 10000   # null, tie_heavy_null, success_boundary, compliance_boundary
.venv/bin/python experiments/ustat_reference/rare_event_diagnostic.py   # Round 9: compliance_boundary only, component compliance-gate first crossings (about 8 s)
```

## Execution accounting (root convention)

As in `paper/pairing_efficiency.tex` and `reviews/round6_pairing_efficiency_identity.md`:
a replicate draws N = 10000 records per arm, i.e. 2N executions, which form
N disjoint pairs (A_i, B_i). At a look with n records per arm both designs have
consumed the same 2n executions; the disjoint-pair rules use the n pairs, the
all-pairs rules use all n x n cross comparisons of the same records. "runs per
arm" in the output files is therefore the same number as the paper's "pairs",
and `max_runs_per_arm = 10000` is the paper's `max_pairs = 10000`. No factor of
two enters any efficiency statement.

## Methods

Kernel: compliance > success > cost (5% relative tolerance, cost tier only if
both runs are compliant and successful; all other equalities are absorbing ties),
identical to the paper's `generate` and to `winstats.compare` with
`Tier('cost', higher_better=False, relative_tolerance=.05)` (asserted in tests).

* `allpairs_fixed_wald`: U = U_w - U_l over all n_A x n_B pairs, variance
  zeta_10/n_A + zeta_01/n_B from the sample variances of the per-observation
  conditional means (Sen 1960; Bebu & Lachin 2016). One-sided Wald at n = 10000.
* `allpairs_gs_{obf,pocock,hsd}`: K = 10 equally spaced looks, information
  fraction t_k = n_k/N, one-sided alpha = 0.05 spent by Lan-DeMets O'Brien-Fleming-type,
  Pocock-type or Hwang-Shih-DeCani (gamma = -3) spending; boundaries from the
  recursive numerical integration (validated: K = 5, alpha = 0.025, OBF gives
  4.877, 3.357, 2.680, 2.290, 2.031). The recursion uses the canonical
  Gaussian-limit covariance of the standardized cumulative all-pairs statistics,
  Cov(Z_k, Z_l) = sqrt(t_k/t_l), i.e. asymptotically independent increments
  (Zhang & Wu 2024, Thm 3.4, joint asymptotic normality under converging stage
  fractions; Bergemann & Hanson 2026, Prop. 1, is the exact finite-sample
  covariance identity Cov(U_k, U_l) = Var(U_l) for nested looks). Covariance
  alone is not finite-sample independence of the increments of the nonlinear
  statistic. The information fraction n_k/N is the first-order limit of
  Var(U_N)/Var(U_{n_k}), not the exact finite-sample fraction. The variance used
  is the first-order term (zeta_10 + zeta_01)/n; the omitted finite-sample term
  (Var(h) - zeta_10 - zeta_01)/n^2 is, from `ustat_reference_efficiency.csv`,
  5.9e-6 to 2.5e-5 at n = 100 (0.13%-0.41% of the retained 4.4e-3 to 6.9e-3) and
  5.9e-8 to 2.5e-7 at the first planned look n = 1000. For the additive success
  and compliance kernels the all-pairs and disjoint point estimates are identical
  (arm-mean difference), but identical component point estimates do not imply
  identical finite-sample variance estimates or stopping times: the disjoint
  variance estimate differs by the empirical cross-arm covariance.
* `allpairs_asympcs_projection_gaussian`: projection-based Gaussian anytime
  monitoring of the all-pairs statistic at the paper's 199 looks, lower bound
  `U_n - sigma_hat_n u_alpha(n)/n`, `sigma_hat_n^2 = zeta10_hat + zeta01_hat`,
  `u_alpha` the exact one-sided normal-mixture boundary (rho^2 = 100, the paper's
  tuning), monitored from the first look n = 100. Its guarantee is stated in the
  next section.
* `disjoint_gs_obf`: the same OBF group-sequential rule on the paper's disjoint-pair
  mean (isolates the design effect from the boundary effect).
* `disjoint_betting`: the paper's betting e-process recomputed on the same stream.

## What `allpairs_asympcs_projection_gaussian` guarantees (fixed tuning)

Let the arm records form i.i.d. vectors X_i = (A_i, B_i) (independent arms:
A_i and B_i are independent, the pairing is bookkeeping) and define the
symmetric kernel

    k(X_i, X_j) = { h(A_i, B_j) + h(A_j, B_i) } / 2 .

Its one-sample order-2 U-statistic U_n^* = C(n,2)^{-1} sum_{i<j} k(X_i, X_j)
has the product-law target theta = E h(A, B). With the disjoint-pair mean
D_n = n^{-1} sum_i h(A_i, B_i),

    U_n = (1 - 1/n) U_n^* + D_n / n ,      |U_n - U_n^*| <= 2/n

(checked numerically to 1e-16 on the brute-force kernel matrix; the bound is
attained with factor 1/2 at most). Writing a(A) = E_B h(A,B) - theta and
b(B) = E_A h(A,B) - theta, the first projection of k is {a(A) + b(B)}/2, so the
Hoeffding linear term of U_n^* is n^{-1} sum_i {a(A_i) + b(B_i)} with variance
sigma_A^2 + sigma_B^2 = zeta_10 + zeta_01 under independent arms (this is the
variance the code estimates; Cai-Hu-Li's one-sample `2 sigma_hat_n` is our
`sqrt(zeta10_hat + zeta01_hat)`). The bounded kernel |h| <= 1 supplies every
moment condition of the strong Gaussian approximation; nondegeneracy
zeta_10 + zeta_01 > 0 is required (it holds in every frozen scenario,
zeta_10 + zeta_01 >= 0.44 in `ustat_reference_efficiency.csv`; the `V > 0`
check in the runner is a numerical convention, not a theorem for degenerate
kernels); and the row/column conditional-mean variance estimator is strongly
consistent (its component second moments are bounded multi-sample averages with
repeated-index terms of vanishing order, and U_n -> theta a.s.).

Under these conditions the lower bound is a (1 - alpha)-**asymptotic** confidence
sequence in the sense of Waudby-Smith et al. (2024; time-uniform CLT route):
it is asymptotically equivalent to an exact time-uniform confidence sequence.
It is **not** a finite-sample 5% crossing bound from the first implemented look
n = 100, and it is **not** Cai, Hu & Li's (2026) delayed-start family (their
Theorems 1-3 are one-sample statements with their own start time and boundary
family; we run fixed tuning rho^2 = 100 from n = 100 and there is no two-sample
theorem in that paper). The empirical calibration tables (report Sections 4.1
and 4.6) are the only finite-sample statement made about this row. The label
applies to the frozen i.i.d. independent-arm generator with nondegenerate
projections; it does not extend to degenerate kernels, dependent paired seeds,
drifting arm laws or adaptively selected records.

## Guarded conventions

`guarded_*` = intersection-union of the three gates (net benefit > 0, success
difference > -0.03, compliance difference > -0.01), each with its own level-0.05
one-sided procedure. Every multi-look rule is written in two conventions:

* `guarded_<rule>_simultaneous` (paper convention): deploy at the first look at
  which all three gate statistics are beyond their boundaries **at that same
  look** (same-look conjunction). This is what `results/online_methods_results.csv`
  does for `guarded_betting`, `guarded_group_bonferroni_wald` and
  `guarded_fixed_wald`. **All comparisons with the paper use these rows only**,
  and `guarded_disjoint_betting_simultaneous` is the row checked for exact
  reproduction of the paper's `guarded_betting` (`ustat_reference_reproduction_check.json`).
* `guarded_<rule>_retained`: each gate's sequential test stops at its own first
  crossing and the crossing is retained; deploy at the first look by which all
  three gates have crossed, possibly at different looks. Reported for
  completeness; not compared to the paper and not claimed to reproduce any paper row.

`win_only_<rule>` rows involve a single gate and are convention-free;
`guarded_allpairs_fixed_wald` has one look, at which the two conventions
coincide, so it carries no suffix. Both conventions admit the intersection-union
argument (a deployment under a violated gate requires that gate's erroneous
rejection), so the difference is comparison scope, not validity.

## Calibration nulls (`--calibration-only`, 10000 replicates, fresh seeds `SeedSequence([20260918, 100 + index])`)

| Scenario | (s_A, s_B, p_A, p_B, cost ratio) | gate at its boundary | other gates |
|---|---|---|---|
| `null` | (.995,.995,.75,.75,1.) | net benefit, theta = 0 | success 0, compliance 0 (strictly favorable) |
| `tie_heavy_null` | (.995,.995,.30,.30,1.) | net benefit, theta = 0 | success 0, compliance 0 |
| `success_boundary` | (.995,.995,.72,.75,.4) | success difference = -0.03 | net benefit +0.424, compliance 0 |
| `compliance_boundary` | (.985,.995,.75,.75,.4) | compliance difference = -0.01 | net benefit +0.458, success 0 |

The two boundary scenarios are those of `experiments/run_stress_tests.py`.
Every guarded deployment in these four scenarios is a type I error of the
guarded rule at the named boundary. Seed indices: 0 and 6 for the two
`SCENARIOS` members (unchanged from the first calibration run), 8 and 9 for the
boundary scenarios.

Outcome (report Section 4.6; 10000 replicates per cell; pointwise 95% Wilson
intervals; observed rates, not calibration verdicts; an interval containing 0.05
means compatibility with 5% at this Monte Carlo precision, SE about 0.0022, and
is not a proof of calibration for other sample sizes or outcome laws).

* Net-benefit and success boundaries, component gate at its boundary: fixed
  Wald, all-pairs OBF/Pocock/HSD and disjoint OBF observe 0.0483-0.0545 (every
  interval contains 0.05 except Pocock in `tie_heavy_null`, 0.0545
  [0.0502, 0.0591]); projection-Gaussian 0.0243-0.0309; betting 0.0080-0.0092.
* Compliance boundary. Three different events are reported separately and are
  never compared with each other:

  | Rule | COMPONENT compliance-gate rejection | SIMULTANEOUS guarded deployment | RETAINED-crossing guarded deployment |
  |---|---|---|---|
  | allpairs_fixed_wald | 551: 5.51% [5.08%, 5.97%] | 550: 5.50% [5.07%, 5.96%] | single look |
  | allpairs_gs_obf | 546: 5.46% [5.03%, 5.92%] | 540: 5.40% [4.97%, 5.86%] | 545: 5.45% [5.02%, 5.91%] |
  | allpairs_gs_pocock | 643: 6.43% [5.97%, 6.93%] | 509: 5.09% [4.68%, 5.54%] | 643: 6.43% [5.97%, 6.93%] |
  | allpairs_gs_hsd | 567: 5.67% [5.23%, 6.14%] | 523: 5.23% [4.81%, 5.68%] | 566: 5.66% [5.22%, 6.13%] |
  | allpairs_asympcs_projection_gaussian | 725: 7.25% [6.76%, 7.77%] | 183: 1.83% [1.59%, 2.11%] | 711: 7.11% [6.62%, 7.63%] |
  | disjoint_gs_obf | 545: 5.45% [5.02%, 5.91%] | 539: 5.39% [4.96%, 5.85%] | 544: 5.44% [5.01%, 5.90%] |
  | disjoint_betting | 76: 0.76% [0.61%, 0.95%] | 31: 0.31% [0.22%, 0.44%] | 72: 0.72% [0.57%, 0.91%] |

  The projection-Gaussian component compliance-gate error is 7.25%. Its
  simultaneous guarded deployment rate is 1.83%. Its retained-crossing guarded
  deployment rate is 7.11%. The 7.25% is not an error rate of the simultaneous
  guarded rule, and the 1.83% does not certify the compliance test as calibrated.
  Component-gate excess over 5% is clear for projection-Gaussian and Pocock
  (exploratory Bonferroni-adjusted one-sided exact binomial p over the 28 gate
  cells: 4.7e-21, 4.7e-9), borderline for HSD (0.038), and not retained for fixed
  Wald and the two OBF rules (0.31, 0.54, 0.61); no blanket statement that all
  asymptotic rules fail is made.
* Archived diagnostic (`rare_event_diagnostic.csv`): of the 725 projection-Gaussian
  false component-gate rejections, 410 (56.6%) first cross at n <= 500 and 540
  (74.5%) at n <= 1000 (median 400); 239 have zero noncompliant arm-A runs at the
  crossing look (median noncompliant counts 1 in A, 4 in B); the variance estimate
  is below the true variance in 675 (93%). This is consistent with, but does not
  by itself establish, underestimation of the plug-in variance of a rare-event
  difference as the mechanism (no oracle-variance or delayed-start ablation was run).

Validity classes: `disjoint_betting` is exact finite-sample for any stopping
rule; `allpairs_asympcs_projection_gaussian` is an asymptotic confidence sequence
as stated above; the group-sequential rules are asymptotically valid only at the
10 planned looks; the fixed Wald anchors are asymptotically valid only at n = 10000.

## Tests

`python -c` snippets used during development are recorded in the report; the
core assertions are: generator identity with `run_simulations.generate`,
O(n log n) statistics equal to the brute-force kernel matrix (U, p_w, p_l,
zeta_10, zeta_01 to 1e-12) at several prefixes, kernel matrix equal to
`winstats.compare`, the symmetric-kernel reduction identity above, analytic
conditional means integrating to `exact_targets`, boundary reference values,
Monte Carlo crossing frequencies, and exact reproduction of the paper's
`win_only_betting` and `guarded_betting` rows by `win_only_disjoint_betting`
and `guarded_disjoint_betting_simultaneous`.
