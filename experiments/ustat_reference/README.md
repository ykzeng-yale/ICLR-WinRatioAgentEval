# Sequential U-statistic reference baseline (GitHub issue #3)

Estimand-aligned all-pairs comparator for the disjoint-pair procedures of the
paper. Everything here is a reference baseline; it does not modify the paper's
code (`src/winstats.py`, `experiments/run_simulations.py`,
`experiments/run_online_methods.py` are imported read-only).

## Files

| File | Content |
|---|---|
| `ustat.py` | Library: exact re-draw of the paper's generator with raw runs (`generate_raw`), O(n log n) all-pairs hierarchical U-statistic and Hoeffding/Sen projection variance at many looks (`hierarchical_prefix_stats`), brute-force oracle (`kernel_matrix`, n <= 2000 only), analytic conditional means and Monte Carlo efficiency components (`efficiency_components`), Lan-DeMets alpha-spending boundaries by Armitage-McPherson-Rowe recursion (`gs_boundaries`, `gs_exit_probabilities`, `spending`), one-sided normal-mixture boundary (`one_sided_normal_mixture_boundary`). |
| `run_ustat_reference.py` | Study: 8 scenarios of `run_online_methods.SCENARIOS`, seeds `SeedSequence([20260918, j])`, 10000 runs per arm, 2000 replicates, 199 looks (100..10000 step 50) for the anytime CS, 10 planned looks (1000k) for group-sequential rules. |
| `../../results/ustat_reference/` | `ustat_reference_results.csv` (deployment rates, Wilson CI, runs used, median stop), `ustat_reference_gate_rates.csv` (per-gate rejection rates), `ustat_reference_efficiency.csv` (Var(h), zeta_10, zeta_01, ARE, predicted fixed-horizon power), `ustat_reference_estimator_check.csv` (empirical vs estimated variance at n = 10000), `manifest.json` (seeds, hashes, boundaries, boundary validation, runtime, peak RSS), `run.log`. |
| `../../evidence/ustat_reference_report.md` | Report with the derivation-to-code correspondence and the comparison. |

## Run

```
.venv/bin/python experiments/ustat_reference/run_ustat_reference.py            # full study (2000 replicates, 8 workers)
.venv/bin/python experiments/ustat_reference/run_ustat_reference.py --replicates 50 --out /tmp/smoke
.venv/bin/python experiments/ustat_reference/run_ustat_reference.py --calibration-only --replicates 10000   # null + tie_heavy_null only, fresh seeds -> null_calibration.csv
```

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
  4.877, 3.357, 2.680, 2.290, 2.031). Independent increments of the cumulative
  all-pairs statistic: Bergemann & Hanson (2026) Prop. 1; Zhang & Wu (2024) Prop. 3.1.
* `allpairs_asympcs`: asymptotic anytime-valid CS (Waudby-Smith et al. 2024 sense)
  for the two-sample U-statistic using its Hoeffding linear term with variance
  zeta_10 + zeta_01 and the exact one-sided normal-mixture boundary (rho^2 = 100,
  the paper's tuning), evaluated at the paper's 199 looks. Cai, Hu & Li (2026)
  state the one-sample version U_n +/- 2 sigma_hat_n gamma(n); no two-sample
  theorem is given there, so this is the standard AsympCS route, not their theorem.
* `disjoint_gs_obf`: the same OBF group-sequential rule on the paper's disjoint-pair
  mean (isolates the design effect from the boundary effect).
* `disjoint_betting`: the paper's betting e-process recomputed on the same stream
  (bit-identical to `results/online_methods_results.csv`).

`guarded_*` = intersection-union of the three gates (net benefit > 0, success
difference > -0.03, compliance difference > -0.01), each with its own level-0.05
one-sided procedure. Primary semantics: each gate's sequential test stops at its
first crossing, deployment at the first look at which all three have crossed.
`*_simultaneous` uses the paper's convention (all three beyond their boundary at
the same look).

Validity classes: `disjoint_betting` is exact finite-sample for any stopping
rule; `allpairs_asympcs` is asymptotically anytime-valid; the group-sequential
rules are asymptotically valid only at the 10 planned looks; the fixed Wald
anchors are asymptotically valid only at n = 10000.

## Tests

`python -c` snippets used during development are recorded in the report; the
core assertions are: generator identity with `run_simulations.generate`,
O(n log n) statistics equal to the brute-force kernel matrix (U, p_w, p_l,
zeta_10, zeta_01 to 1e-12) at several prefixes, kernel matrix equal to
`winstats.compare`, analytic conditional means integrating to `exact_targets`,
boundary reference values, and Monte Carlo crossing frequencies.
