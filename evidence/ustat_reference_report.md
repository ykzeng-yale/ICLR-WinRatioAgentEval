# Sequential U-statistic reference baseline vs the disjoint-pair betting e-process

GitHub issue #3. Dates: 2026-09-17/18 (first version, audited as commit `e1ea314`); revised 2026-09-18 in response to `reviews/round8_ustat_preintegration_review.md`. Author: reference-baseline subagent (this session).
Code: `experiments/ustat_reference/{ustat.py, run_ustat_reference.py, README.md}`.
Results: `results/ustat_reference/{ustat_reference_results.csv, ustat_reference_gate_rates.csv, ustat_reference_efficiency.csv, ustat_reference_estimator_check.csv, ustat_reference_reproduction_check.json, null_calibration.csv, manifest.json, calibration_manifest.json, run.log, calibration_run.log}`; the audited version's outputs are preserved unchanged in `results/ustat_reference/previous_e1ea314/`.
Nothing under `paper/`, `src/`, the paper's experiment scripts or the paper's result files was modified; they were imported or read only.

Every number below was produced by code run in this session or read from the named files. "Predicted" means a normal-approximation formula evaluated on Monte Carlo variance components; "empirical" means the 2000-replicate (or 10000-replicate) simulation. Runs are counted per arm: N records per arm = 2N executions = N disjoint pairs (Section 3).

## 0. Response to the pre-integration review

The review (`reviews/round8_ustat_preintegration_review.md`, audited commit `e1ea314`) asked for four corrections before integration. What changed for each:

1. **State the actual fixed-tuning AsympCS guarantee.** The description in `ustat.py` (module docstring), `README.md` (section "What `allpairs_asympcs_projection_gaussian` guarantees") and this report (Section 1, Cai-Hu-Li row) was replaced by the symmetric-kernel one-sample reduction: with X_i = (A_i, B_i) i.i.d. and k(X_i, X_j) = {h(A_i, B_j) + h(A_j, B_i)}/2, the one-sample order-2 U-statistic U_n^* has the product-law target and U_n = (1 - 1/n) U_n^* + D_n/n with |U_n - U_n^*| <= 2/n (checked numerically, Section 2); the first projection of k is {a(A) + b(B)}/2, so the linear-term variance is sigma_A^2 + sigma_B^2 = zeta_10 + zeta_01; the bounded kernel supplies the moment conditions; nondegeneracy zeta_10 + zeta_01 > 0 is required (holds in every frozen scenario; the `V > 0` check is a numerical convention); and the row/column conditional-mean variance estimator is strongly consistent. The guarantee is stated as an **asymptotic** confidence sequence in the Waudby-Smith et al. (2024) time-uniform-CLT sense, explicitly **not** a finite-sample 5% crossing bound from n = 100 and **not** Cai-Hu-Li's delayed-start family. The method was renamed `allpairs_asympcs_projection_gaussian` in every CSV, the manifest and the README; the label is restricted to the frozen i.i.d. independent-arm generator with nondegenerate projections.
2. **Primary guarded rows retained crossings at different looks.** Every multi-look guarded rule now has two rows: `guarded_<rule>_simultaneous` (same-look conjunction, the paper's convention) and `guarded_<rule>_retained` (each gate keeps its first crossing). The previous version had simultaneous rows only for the all-pairs rules and the betting rule and no simultaneous disjoint OBF row; now all-pairs OBF/Pocock/HSD, all-pairs AsympCS, disjoint OBF and disjoint betting have both. The reproduction check against `results/online_methods_results.csv` uses `win_only_disjoint_betting` and `guarded_disjoint_betting_simultaneous` only, is computed by the runner itself (`ustat_reference_reproduction_check.json`) and is reported in Section 4.0; no bit-identity is claimed for any retained row. Every comparison with the paper (Sections 4.1-4.3, 4.6, 5) uses simultaneous rows; retained rows are listed separately for information. The 10-look versus 199-look monitoring difference is stated with each comparison.
3. **Calibration did not examine guardrail-boundary nulls.** `--calibration-only` now runs four nulls at 10000 replicates: `null` and `tie_heavy_null` (net-benefit boundary, both guardrails strictly favorable) plus `success_boundary` (.995,.995,.72,.75,.4) with the success difference exactly -0.03 = threshold and `compliance_boundary` (.985,.995,.75,.75,.4) with the compliance difference exactly -0.01 = threshold, both taken from `experiments/run_stress_tests.py`. Section 4.6 reports guarded deployment rates (simultaneous and retained) and the boundary gate's own rejection rate for every rule with Wilson intervals, and states which rules hold their level at each boundary.
4. **Independent increments.** `ustat.py`, `README.md` and Section 1 now describe independent increments as the canonical Gaussian-limit covariance property Cov(Z_k, Z_l) = sqrt(t_k/t_l) of the standardized cumulative all-pairs statistics (Zhang & Wu Thm 3.4 joint asymptotic normality; Bergemann & Hanson Prop. 1 as the exact finite-sample covariance identity), state that covariance alone is not finite-sample independence of the increments of the nonlinear statistic, and describe the information fraction n_k/N as the first-order limit of Var(U_N)/Var(U_{n_k}) rather than the exact finite-sample fraction.

Also adopted from the review's checks: the execution accounting is stated explicitly (Section 3, root convention); the main study was rerun with identical seeds because the row set changed (Section 6 records runtime, memory and hashes); the previous CSVs are preserved.

## 1. What the primary sources say and how the code maps to them

Sources were fetched in the first session from arXiv HTML/abs pages and the OUP abstract page (see `evidence/lit_winstats.md` rows 4, 31, 32, 36 for bibliographic details).

| Source | Statement extracted | Code |
|---|---|---|
| Bebu & Lachin 2016 (Biostatistics 17:178-187; OUP page) | `U_v = (1/(nm)) sum_i sum_j phi_v(X_i, Y_j)`, v = 1 (treatment wins), 2 (treatment loses); `sqrt(N)(U - tau) -> N(0, Sigma)` with `sigma_uv = (N/m) xi_10^{uv} + (N/n) xi_01^{uv}`, `xi_10^{uv} = Cov(phi_u(X_1,Y_1), phi_v(X_1,Y_1'))`, `xi_01^{uv} = Cov(phi_u(X_1,Y_1), phi_v(X_1',Y_1))`; log WR by the delta method. | `ustat.hierarchical_prefix_stats` returns `pw = U_1`, `pl = U_2`, `U = U_1 - U_2` (net benefit); the net-benefit variance `var_u = zeta10/n_A + zeta01/n_B` is the quadratic form `sigma_11 + sigma_22 - 2 sigma_12` of the Bebu-Lachin covariance applied to the signed kernel `h = phi_1 - phi_2`, i.e. `zeta10 = Var(E[h(X,Y) | X])`, `zeta01 = Var(E[h(X,Y) | Y])`. Estimators: sample variances of the per-observation conditional means `ghat_10(X_i) = n_B^{-1} sum_j h(X_i,Y_j)` and `ghat_01(Y_j)` (Sen 1960 / the "nonparametric variance from concordant-discordant pair frequencies" of Bebu-Lachin). This is the first-order (projection) variance; the exact finite-N variance adds the residual term sigma_R^2/N^2 (`paper/pairing_efficiency.tex`). |
| Bergemann & Hanson 2026 (arXiv:2601.22525v1) | Same `U_nu`; `sigma_uv = (N/m) xi_10 + (N/n) xi_01`; **Proposition 1**: for looks k < l, `cov(U_1k - U_2k, U_1l - U_2l) = var(U_1l - U_2l)` (the exact covariance identity of the cumulative all-pairs win difference at nested looks with unchanged subject-level endpoints); information fraction = subjects analysed at the look / subjects at the final look; HSD spending with gamma = -3 for two-sided alpha = 0.05, K = 3 looks at 50/75/100%, boundaries from gsDesign; simulated type I error 0.0517 (N = 200), 0.0487 (N = 400) with complete data. | Information fraction `t_k = n_k / N = k/10` (`run_ustat_reference.py`, `t10`); the cumulative all-pairs statistic at look k uses the first `n_k` runs of each arm (`hierarchical_prefix_stats` with `looks`); `spending('hsd', t, alpha, gamma=-3)`; one-sided alpha = 0.05 here (the paper's gates are one-sided), so their two-sided 0.05 is not reproduced. The covariance identity is what makes the canonical structure the right Gaussian limit; it is not by itself finite-sample independence of increments (Section 0, point 4). |
| Zhang & Wu 2024 (arXiv:2410.06281) | Eq. 3.1: `U_{nu k} = (1/(m_k n_k)) sum_{i<=m_k} sum_{j<=n_k} phi_nu(D_i; D'_j)`; **Prop. 3.1**: `Cov(D_p, D_q) = sqrt(V(Delta U_q) / V(Delta U_p))`, `t_k = V(Delta U_K)/V(Delta U_k)`; **Thm 3.4**: canonical joint normal law across K looks under Condition C1 (stage fractions converge); variance `V(Delta U) = [(n-1)/(mn)] xi^{10} + [(m-1)/(mn)] xi^{01} + [1/(mn)] xi^{11}` with `xi^{10}_{uv}, xi^{01}_{uv}, xi^{11}_{uv}` the Hoeffding components of the signed kernel; spending `alpha(t) = alpha t^2`; boundaries by the recursion `P(S_1 > c_1) = alpha_1`, `P(S_1 < c_1, ..., S_k >= c_k) = alpha_k` (one-sided). | Boundaries: `ustat.gs_boundaries` implements exactly this recursion (Armitage-McPherson-Rowe sub-density propagation on a Simpson grid, `brentq` per look) for the canonical Gaussian limit. `spending('kim_demets2')` is their `alpha t^2` (implemented, not run). Variance: the leading two terms are used (`zeta10/n + zeta01/n`); the `xi^{11}/(mn)` term is dropped (order 1/n^2, below 1e-8 at n = 100 relative to 1e-3). Information is taken as `n_k/N`, the first-order limit of `V_K/V_k` for the balanced stationary design with fixed look proportions; it is not the exact finite-sample fraction. |
| Cai, Hu & Li 2026 (arXiv:2605.14692v2) | One-sample degree-2 `U_n`; Hoeffding `U_n - theta = (2/n) sum h_1(X_i) + R_n`; nondegeneracy `sigma^2 = Var(h_1) > 0`; **Thm 1** strong Gaussian approximation with error `O(n^{-1+1/(2+delta)})` under moment conditions; **Thm 2** jackknife `sigma_hat_n^2 = n^{-1} sum_i {(n-1)^{-1} sum_{j != i} h(X_i,X_j)}^2 - U_n^2`; **Thm 3** `[U_n +/- 2 sigma_hat_n gamma_{alpha,m}(n)]` is a (1-alpha)-AsympCS with a stitched LIL boundary (eta = 2, s = 1.4) or a Gaussian-mixture boundary, in a delayed-start family with start time m; MMD appears only as a degenerate example; no two-sample theorem. | What is implemented (`allpairs_asympcs_projection_gaussian`) is the Waudby-Smith et al. (2024) time-uniform-CLT route applied through the symmetric-kernel reduction. With `X_i = (A_i, B_i)` and `k(X_i, X_j) = {h(A_i,B_j) + h(A_j,B_i)}/2`, the one-sample order-2 statistic `U_n^*` of `k` has mean theta and `U_n = (1 - 1/n) U_n^* + D_n/n`, `|U_n - U_n^*| <= 2/n`; the first projection of `k` is `{a(A) + b(B)}/2`, so `2 h_1` in their notation is `a(A) + b(B)` with variance `sigma_A^2 + sigma_B^2 = zeta10 + zeta01` (their `2 sigma_hat_n` is our `sqrt(zeta10_hat + zeta01_hat)`); |h| <= 1 supplies the moment conditions of their Thm 1; `zeta10 + zeta01 > 0` is required and holds in every frozen scenario; the row/column conditional-mean variance estimator is strongly consistent (bounded multi-sample averages with repeated-index terms of vanishing order). The CS is `U_n - sigma_hat_n u_alpha(n)/n` with `u_alpha` the exact one-sided normal-mixture boundary of Howard et al. (2021), `V = n`, `rho^2 = 100` (the paper's tuning), from the first look n = 100. This yields an **asymptotic** CS (asymptotically equivalent to an exact time-uniform CS), not a finite-sample 5% crossing bound from n = 100 and not their delayed-start family; the `2/n` residual is negligible against the boundary width `sigma u(n)/n`, of order `sqrt(log n / n)`. |

One-sided normal mixture used for `allpairs_asympcs_projection_gaussian`: mixing `exp(lambda S - lambda^2 V/2)` over a half-normal `lambda` with variance `1/rho^2` gives `M = 2 sqrt(rho^2/(V+rho^2)) exp(S^2/(2(V+rho^2))) Phi(S/sqrt(V+rho^2))`; the boundary solves `M = 1/alpha` (`ustat.one_sided_normal_mixture_boundary`). Monte Carlo on 20000 Gaussian random walks of length 20000 (first session): crossing frequency 0.0409 +/- 0.0015 at alpha = 0.05 (valid for exactly Gaussian increments; conservative over a finite horizon).

## 2. Implementation checks

Run in the first session unless marked (revised):

* Generator identity: `ustat.generate_raw` draws the same stream as `run_simulations.generate` and its `(z, dq, ds)` are bit-identical (asserted). (Revised) The paper's betting rule recomputed on these streams reproduces the `win_only_betting` and `guarded_betting` rows of `results/online_methods_results.csv` exactly through the `win_only_disjoint_betting` and `guarded_disjoint_betting_simultaneous` rows; the runner writes the row-by-row comparison to `ustat_reference_reproduction_check.json` (Section 4.0). The retained-crossing betting row is a different decision rule and is not expected to, and does not, reproduce the paper row.
* O(n log n) statistics vs brute-force kernel matrix (`ustat.kernel_matrix`, n <= 700) at prefixes 50/120/333/700 in four scenarios: `U`, `p_w`, `p_l`, `zeta10`, `zeta01` agree to 1e-12; the kernel matrix agrees with `winstats.compare` using `Tier('cost', higher_better=False, relative_tolerance=.05)` with the both-compliant-both-successful eligibility mask; its diagonal equals the paper's disjoint-pair `z`. Unequal arm sizes (300 vs 450) also agree.
* (Revised) Symmetric-kernel reduction: on the brute-force kernel matrix in all 8 scenarios at n = 2, 5, 37, 400, `max |U_n - ((1 - 1/n) U_n^* + D_n/n)| = 1.1e-16` and `max n |U_n - U_n^*| / 2 = 0.5 <= 1`; on 200000 Monte Carlo records of efficiency_gain, `Var{a(A) + b(B)} = 0.6035` against `zeta10 + zeta01 = 0.6053` with `Cov(a, b) = -0.0009` (independent arms).
* Analytic conditional means `g_10`, `g_01` (`ustat.conditional_mean_given_a/b`) integrate to `run_simulations.exact_targets` within Monte Carlo error in all 8 scenarios (Section 4.5 table: `theta_exact` vs `theta_mc`, MCSE about 0.001).
* Boundary code: Lan-DeMets OBF-type, one-sided alpha = 0.025, K = 5 equally spaced: computed 4.8769, 3.3570, 2.6803, 2.2898, 2.0310 vs reference 4.877, 3.357, 2.680, 2.290, 2.031. Constant-boundary Pocock and O'Brien-Fleming constants recovered by root finding on the same recursion: 2.4132 and 2.0401 (textbook two-sided-0.05 values 2.413 and 2.040). K = 1 returns `Phi^{-1}(0.95)` exactly. Cumulative exit probabilities under H0 match the spending function to 1e-14 for all three K = 10 designs. Monte Carlo on 400000 Brownian paths at the K = 10 OBF boundaries: overall crossing 0.0498 +/- 0.0003.
* K = 10, one-sided alpha = 0.05 boundaries used: OBF 6.088, 4.229, 3.396, 2.906, 2.579, 2.342, 2.160, 2.015, 1.895, 1.795; Pocock-type 2.412, 2.363, 2.317, 2.280, 2.250, 2.225, 2.204, 2.187, 2.171, 2.158; HSD(-3) 3.116, 2.982, 2.838, 2.694, 2.549, 2.403, 2.254, 2.101, 1.943, 1.779 (`manifest.json`).
* Variance estimator at n = 10000 (`ustat_reference_estimator_check.csv`, unchanged by the revision because the streams are identical): mean estimated `Var(U)` vs empirical variance of `U` across 2000 replicates: null 6.55e-5 vs 6.74e-5, efficiency_gain 6.05e-5 vs 5.92e-5, weak_gain 6.55e-5 vs 6.55e-5, tie_heavy_efficiency 4.48e-5 vs 4.45e-5 (relative MC error of an empirical variance from 2000 replicates is 3.2%).

## 3. Study design, execution accounting and fairness statement

* Generator, 8 scenarios (6 of `run_simulations.py` plus `tie_heavy_null`, `tie_heavy_efficiency`), seeds `SeedSequence([20260918, j])`, 2000 replicates, batch 25: identical to `run_online_methods.py`.
* **Execution accounting (root convention, `paper/pairing_efficiency.tex`, `reviews/round6_pairing_efficiency_identity.md`).** Each replicate draws N = 10000 records per arm, i.e. 2N = 20000 executions, which form N = 10000 disjoint pairs (A_i, B_i). At a look with n records per arm both designs have consumed the same 2n executions: the disjoint-pair rules use the n pairs, the all-pairs rules use all n x n cross comparisons of the same records. "runs per arm" in every table below is therefore the paper's "pairs", `max_runs_per_arm = 10000` is the paper's `max_pairs = 10000`, and no factor of two enters any efficiency statement.
* Same one-sided alpha = 0.05 per gate, same thresholds (net benefit > 0, success difference > -0.03, compliance difference > -0.01), same intersection-union guarded rule, same 199 looks (100..10000 step 50) for the anytime rules, same 10 looks (1000k) for the group-sequential rules.
* Validity classes: `disjoint_betting` (the paper) is exact finite-sample under optional stopping at any look. `allpairs_asympcs_projection_gaussian` is an asymptotic confidence sequence (Section 0, point 1). `allpairs_gs_*` and `disjoint_gs_obf` are asymptotically valid only at the 10 planned looks. `allpairs_fixed_wald` and the paper's `guarded_fixed_wald` are asymptotically valid only at n = 10000. Group-sequential rules therefore use only 10 planned looks and are not anytime-valid comparators.
* Guarded conventions: `*_simultaneous` = deploy at the first look at which all three gate statistics are beyond their boundaries at that same look (the paper's convention; `guarded_betting`, `guarded_group_bonferroni_wald`, `guarded_fixed_wald` in `results/online_methods_results.csv` all use it). `*_retained` = each gate keeps its first crossing; deploy at the first look by which all three have crossed. **Every comparison with the paper uses simultaneous rows.** Win-only rows have one gate and are convention-free; the fixed Wald anchor has one look. Both conventions admit the intersection-union argument (a deployment under a violated gate requires that gate's erroneous rejection), so the difference is comparison scope, not validity.
* No comparison below mixes different nulls: every method tests the same three one-sided hypotheses with the same thresholds.

## 4. Results (2000 replicates unless stated; Wilson 95% CIs; runs per arm = pairs; 2N executions at N)

### 4.0 Data identity and reproduction of the paper's betting rows

`ustat_reference_reproduction_check.json` (written by the runner, comparing string-equal CSV fields: deployments, mean pairs used, median pairs among deployments, both Wilson bounds, MCSE) against `results/online_methods_results.csv`:

| Scenario | `guarded_disjoint_betting_simultaneous` (recomputed) | paper `guarded_betting` | `win_only_disjoint_betting` / paper `win_only_betting` |
|---|---|---|---|
| null | 12 / 9965.325 / 2900 | 12 / 9965.325 / 2900 | 16 / 16 |
| efficiency_gain | 1932 / 4361.825 / 3750 | 1932 / 4361.825 / 3750 | 2000 / 2000 |
| success_regression | 0 / 10000 / - | 0 / 10000 / - | 2000 / 2000 |
| safety_regression | 0 / 10000 / - | 0 / 10000 / - | 2000 / 2000 |
| joint_gain | 2000 / 1426.8 / 1300 | 2000 / 1426.8 / 1300 | 2000 / 2000 |
| weak_gain | 70 / 9837.75 / 5075 | 70 / 9837.75 / 5075 | 83 / 83 |
| tie_heavy_null | 15 / 9954.15 / 2350 | 15 / 9954.15 / 2350 | 21 / 21 |
| tie_heavy_efficiency | 1875 / 4790.7 / 4100 | 1875 / 4790.7 / 4100 | 2000 / 2000 |

(deployments / mean runs per arm / median runs among deployments.) All 16 expected comparisons are identical (`all_expected_rows_identical: true`). The retained-crossing row `guarded_disjoint_betting_retained` is a different decision rule and differs from the paper row in 6 of 8 scenarios (null 16 vs 12 deployments; efficiency_gain 1933 / 4260.3 vs 1932 / 4361.8; joint_gain mean 1423.9 vs 1426.8; weak_gain 83 vs 70; tie_heavy_null 21 vs 15; tie_heavy_efficiency mean 4708.7 vs 4790.7); no identity is claimed for it. Consistency with the audited run: because the seeds are unchanged, all 152 rows of `previous_e1ea314/ustat_reference_results.csv` that still exist are bit-identical to the new file under the renaming (`allpairs_asympcs` -> `allpairs_asympcs_projection_gaussian`, unsuffixed guarded -> `_retained`); the new file adds `guarded_disjoint_gs_obf_simultaneous` (8 rows) and drops the duplicate `win_only_disjoint_betting_simultaneous`; `ustat_reference_efficiency.csv`, `ustat_reference_estimator_check.csv` and `ustat_reference_gate_rates.csv` are identical after renaming.

### 4.1 Calibration at the net-benefit boundary null in the main study (theta = 0 = c; 2000 replicates)

Win-only deployment rate = type I error of the net-benefit gate at its boundary; guarded rates under the simultaneous convention.

| Method | null win-only | null guarded (simultaneous) | tie_heavy_null win-only | tie_heavy_null guarded (simultaneous) | validity |
|---|---|---|---|---|---|
| allpairs_fixed_wald (n = 10000) | 0.0570 [0.0477, 0.0680] | 0.0570 | 0.0405 [0.0327, 0.0501] | 0.0405 | asymptotic, one look |
| allpairs_gs_obf (10 looks) | 0.0575 [0.0481, 0.0686] | 0.0575 | 0.0435 [0.0354, 0.0533] | 0.0435 | asymptotic, planned looks |
| allpairs_gs_pocock | 0.0570 [0.0477, 0.0680] | 0.0560 | 0.0505 [0.0417, 0.0610] | 0.0505 | asymptotic, planned looks |
| allpairs_gs_hsd | 0.0570 [0.0477, 0.0680] | 0.0565 | 0.0440 [0.0359, 0.0539] | 0.0440 | asymptotic, planned looks |
| allpairs_asympcs_projection_gaussian (199 looks) | 0.0275 [0.0212, 0.0356] | 0.0235 | 0.0200 [0.0147, 0.0271] | 0.0190 | asymptotic CS |
| disjoint_gs_obf (10 looks) | 0.0530 [0.0440, 0.0637] | 0.0530 | 0.0445 [0.0363, 0.0544] | 0.0445 | asymptotic, planned looks |
| disjoint_betting (paper) | 0.0080 [0.0049, 0.0130] | 0.0060 | 0.0105 [0.0069, 0.0160] | 0.0075 | exact, anytime |
| paper guarded_fixed_wald (disjoint, n = 10000) | - | 0.0495 [0.0408, 0.0599] | - | 0.0455 [0.0372, 0.0555] | asymptotic, one look |
| paper guarded_group_bonferroni_wald | - | 0.0230 [0.0173, 0.0305] | - | 0.0200 [0.0147, 0.0271] | asymptotic, planned looks |

At 2000 replicates all all-pairs and group-sequential rules are within Monte Carlo error of 0.05 (the 0.057 values are 1.4 SE above 0.05; the 10000-replicate calibration in Section 4.6 gives 0.049-0.054). The asymptotic CS is conservative at this boundary (0.02-0.03), as expected for a normal mixture evaluated over a finite horizon with rho^2 tuned at n = 100 (its Gaussian-walk crossing rate was 0.041). The exact betting rule is the most conservative (0.006-0.011). Guarded simultaneous rates equal the win-only rates for the group-sequential rules except for one or two replicates (Pocock, HSD in null) and are lower for the anytime rules, whose success gate has not always passed at the same look.

### 4.2 Regression scenarios (a false gate; guarded deployment should be 0)

success_regression (success difference -0.10 vs threshold -0.03): every rule 0/2000 under both conventions (upper CI 0.0019).
safety_regression (compliance difference -0.02 vs threshold -0.01): every simultaneous row 0/2000; the only nonzero row is `guarded_allpairs_asympcs_projection_gaussian_retained` 9/2000 = 0.0045 [0.0024, 0.0085], which is the AsympCS compliance gate's own false rejection rate (`ustat_reference_gate_rates.csv`: 9/2000, convention-free; 0/2000 for every other rule's compliance gate). Section 4.7 traces all nine to n = 200-250 per arm. Under the simultaneous convention these early false crossings do not become deployments because the success gate has not passed at the same look.

### 4.3 Power and stopping times (admissible scenarios; simultaneous convention; paper rows for comparison)

Deployment rate; mean runs per arm (capped at 10000; = mean pairs = half the mean executions); median runs among deployments. Group-sequential rules monitor 10 planned looks (1000k); the AsympCS, the betting rule and the paper's `guarded_group_bonferroni_wald` monitor the 199 looks (the Bonferroni rule deploys only at the 10 planned looks).

| Scenario | Rule | rate [CI] | mean runs per arm | median |
|---|---|---|---|---|
| efficiency_gain | guarded_allpairs_fixed_wald | 0.9995 [0.9972, 0.9999] | 10000 | 10000 |
| | guarded_allpairs_gs_obf_simultaneous | 0.9995 [0.9972, 0.9999] | 4469.0 | 4000 |
| | guarded_allpairs_gs_pocock_simultaneous | 0.9975 [0.9942, 0.9989] | 3113.5 | 3000 |
| | guarded_allpairs_gs_hsd_simultaneous | 0.9995 [0.9972, 0.9999] | 3932.0 | 4000 |
| | guarded_allpairs_asympcs_projection_gaussian_simultaneous | 0.9815 [0.9746, 0.9865] | 3359.0 | 2700 |
| | guarded_disjoint_gs_obf_simultaneous | 0.9995 [0.9972, 0.9999] | 4472.5 | 4000 |
| | guarded_disjoint_betting_simultaneous = paper guarded_betting | 0.9660 [0.9571, 0.9731] | 4361.8 | 3750 |
| | paper guarded_group_bonferroni_wald | 0.9930 [0.9883, 0.9958] | 3588.0 | 3000 |
| joint_gain | guarded_allpairs_gs_obf_simultaneous | 1.0 | 2397.5 | 2000 |
| | guarded_allpairs_gs_pocock_simultaneous | 1.0 | 1233.0 | 1000 |
| | guarded_allpairs_gs_hsd_simultaneous | 1.0 | 1497.5 | 1000 |
| | guarded_allpairs_asympcs_projection_gaussian_simultaneous | 1.0 | 715.0 | 550 |
| | guarded_disjoint_gs_obf_simultaneous | 1.0 | 2393.0 | 2000 |
| | guarded_disjoint_betting_simultaneous = paper guarded_betting | 1.0 | 1426.8 | 1300 |
| | paper guarded_group_bonferroni_wald | 1.0 | 1305.5 | 1000 |
| weak_gain (theta = 0.0099) | guarded_allpairs_fixed_wald | 0.3280 [0.3078, 0.3489] | 10000 | 10000 |
| | guarded_allpairs_gs_obf_simultaneous | 0.3170 [0.2970, 0.3377] | 9246.5 | 8000 |
| | guarded_allpairs_gs_pocock_simultaneous | 0.2625 [0.2437, 0.2822] | 8904.0 | 6000 |
| | guarded_allpairs_gs_hsd_simultaneous | 0.3110 [0.2911, 0.3316] | 9249.0 | 8000 |
| | guarded_allpairs_asympcs_projection_gaussian_simultaneous | 0.1055 [0.0928, 0.1197] | 9377.3 | 3500 |
| | guarded_disjoint_gs_obf_simultaneous | 0.2450 [0.2267, 0.2643] | 9451.5 | 8000 |
| | guarded_disjoint_betting_simultaneous = paper guarded_betting | 0.0350 [0.0278, 0.0440] | 9837.8 | 5075 |
| | paper guarded_fixed_wald (disjoint) | 0.2575 [0.2388, 0.2771] | 10000 | 10000 |
| | paper guarded_group_bonferroni_wald | 0.1090 [0.0961, 0.1234] | 9519.5 | 5000 |
| tie_heavy_efficiency | guarded_allpairs_gs_obf_simultaneous | 0.9995 [0.9972, 0.9999] | 4688.5 | 4000 |
| | guarded_allpairs_gs_pocock_simultaneous | 0.9985 [0.9956, 0.9995] | 3320.5 | 3000 |
| | guarded_allpairs_gs_hsd_simultaneous | 1.0 | 4171.0 | 4000 |
| | guarded_allpairs_asympcs_projection_gaussian_simultaneous | 0.9655 [0.9566, 0.9726] | 3682.8 | 3000 |
| | guarded_disjoint_gs_obf_simultaneous | 0.9995 [0.9972, 0.9999] | 4686.0 | 4000 |
| | guarded_disjoint_betting_simultaneous = paper guarded_betting | 0.9375 [0.9260, 0.9473] | 4790.7 | 4100 |
| | paper guarded_group_bonferroni_wald | 0.9900 [0.9846, 0.9935] | 3872.0 | 3000 |

Retained-crossing rows (`*_retained`, for information, not compared with the paper): they differ from the simultaneous rows by at most one deployment and by less than 3% in mean runs for every group-sequential rule (e.g. efficiency_gain all-pairs OBF 4467.5 vs 4469.0, Pocock 3101.5 vs 3113.5), and by more for the two anytime rules where gates cross at different looks: AsympCS efficiency_gain 3258.6 vs 3359.0 mean runs, weak_gain 232 vs 211 deployments (0.116 vs 0.1055); betting efficiency_gain 4260.3 vs 4361.8, weak_gain 83 vs 70 deployments (0.0415 vs 0.035).

Win-only (net-benefit gate alone, convention-free) stopping in the strong-effect scenarios: all group-sequential rules stop at the first planned look (1000 runs, both designs); `allpairs_asympcs_projection_gaussian` mean 102-121 runs (median 100) vs `disjoint_betting` 107-145 (median 100-150); in tie_heavy_efficiency the AsympCS 1022 (median 850) vs `disjoint_betting` 1562 (median 1400), and `allpairs_gs_obf` 2728 vs `disjoint_gs_obf` 2875.

### 4.4 Fixed-horizon anchor power (n = 10000 per arm)

Net-benefit gate in weak_gain: all-pairs Wald 0.3280 [0.3078, 0.3489] (normal-approximation prediction from the Monte Carlo variance components: 0.3367); the paper's disjoint fixed Wald on the same executions 0.2575 [0.2388, 0.2771] (prediction 0.2730). Everywhere else the anchor power is 1.0 (effects) or 0 (false gates).

### 4.5 Asymptotic efficiency of all pairs vs disjoint pairs (`ustat_reference_efficiency.csv`, 1e6 Monte Carlo pairs, analytic conditional means)

| Scenario | theta exact | theta MC | Var(h) | zeta10 | zeta01 | ARE = Var(h)/(zeta10+zeta01) | empirical Var ratio at n = 10000 (2000 reps) |
|---|---|---|---|---|---|---|---|
| null | 0.0000 | -0.0010 | 0.9026 | 0.3276 | 0.3272 | 1.378 | 1.337 |
| efficiency_gain | 0.3625 | 0.3639 | 0.7828 | 0.4863 | 0.1184 | 1.294 | 1.286 |
| success_regression | 0.3106 | 0.3110 | 0.8054 | 0.6317 | 0.0594 | 1.165 | 1.181 |
| safety_regression | 0.4105 | 0.4106 | 0.7547 | 0.5473 | 0.0688 | 1.225 | 1.213 |
| joint_gain | 0.3060 | 0.3063 | 0.8304 | 0.3489 | 0.2415 | 1.406 | 1.398 |
| weak_gain | 0.0099 | 0.0093 | 0.9041 | 0.3241 | 0.3308 | 1.381 | 1.349 |
| tie_heavy_null | 0.0000 | 0.0005 | 0.5085 | 0.2206 | 0.2201 | 1.154 | 1.171 |
| tie_heavy_efficiency | 0.0580 | 0.0583 | 0.5075 | 0.3056 | 0.1426 | 1.132 | 1.155 |

(MCSE of theta MC about 0.001; the empirical variance ratio has relative MC error about 4.5%; the exact finite-N identity is Var(D_N)/Var(U_N) = (sigma_A^2+sigma_B^2+sigma_R^2)/(sigma_A^2+sigma_B^2+sigma_R^2/N), `paper/pairing_efficiency.tex`.) Both estimators use the same 2N executions. The all-pairs statistic is 13-41% more efficient than the disjoint-pair mean for the hierarchical net benefit; equivalently, disjoint pairs need 1.13-1.41 times as many records per arm for the same asymptotic precision on that gate. Consistency with the empirical results: (i) weak_gain fixed-horizon power 0.328 vs 0.258 matches the predicted 0.337 vs 0.273; (ii) under the same OBF rule, win-only stopping in tie_heavy_efficiency is 2728 vs 2875 mean runs (ratio 1.054, compressed by the 1000-run look grid; ARE 1.13) and the weak_gain group-sequential power is 0.317 vs 0.245 (simultaneous rows; identical under the retained convention).

**The efficiency gain does not transfer to the guarded decision.** For the success and compliance gates the kernel is additive, `g(a) - g(b)`, so the all-pairs U-statistic is exactly the difference of arm means, which is the same number as the disjoint-pair mean of `dq`/`ds`; its projection variance `(Var_A + Var_B)/n` is the disjoint variance; ARE = 1 identically. Since the guarded rules in efficiency_gain, joint_gain and tie_heavy_efficiency are bottlenecked by the success gate (success difference 0 or +0.09 vs threshold -0.03), the guarded all-pairs and disjoint group-sequential rules stop at practically the same time under the simultaneous convention (4469.0 vs 4472.5; 2397.5 vs 2393.0; 4688.5 vs 4686.0 mean runs). Only in weak_gain, where the net-benefit gate is the bottleneck, does the guarded rule inherit the gain (0.317 vs 0.245 power).

### 4.6 Ten-thousand-replicate calibration at four nulls (`null_calibration.csv`, fresh seed streams `SeedSequence([20260918, 100 + index])`, index 0 / 6 / 8 / 9)

Scenarios: `null` (.995,.995,.75,.75,1.) and `tie_heavy_null` (.995,.995,.30,.30,1.) put the net-benefit gate at its boundary (theta = 0) with both guardrails strictly favorable; `success_boundary` (.995,.995,.72,.75,.4) puts the success difference exactly at its threshold -0.03 with net benefit +0.424 and compliance difference 0; `compliance_boundary` (.985,.995,.75,.75,.4) puts the compliance difference exactly at its threshold -0.01 with net benefit +0.458 and success difference 0 (both boundary scenarios as in `experiments/run_stress_tests.py`). Every guarded deployment is a type I error at the named boundary. Runtime 835 s (four worker processes, one per scenario), peak child RSS 238 MB. The `null` and `tie_heavy_null` streams are those of the audited calibration run and every previously existing row is bit-identical to `previous_e1ea314/null_calibration.csv`.

**Guarded deployment rate, simultaneous convention (the paper's rule):**

| Rule | null | tie_heavy_null | success_boundary | compliance_boundary |
|---|---|---|---|---|
| allpairs_fixed_wald (n = 10000, one look) | 0.0503 [0.0462, 0.0548] | 0.0523 [0.0481, 0.0568] | 0.0483 [0.0443, 0.0527] | **0.0550 [0.0507, 0.0596]** |
| allpairs_gs_obf (10 looks) | 0.0496 [0.0455, 0.0540] | 0.0505 [0.0464, 0.0550] | 0.0508 [0.0467, 0.0553] | 0.0540 [0.0497, 0.0586] |
| allpairs_gs_pocock (10 looks) | 0.0501 [0.0460, 0.0546] | 0.0537 [0.0495, 0.0583] | 0.0477 [0.0437, 0.0521] | 0.0509 [0.0468, 0.0554] |
| allpairs_gs_hsd (10 looks) | 0.0491 [0.0450, 0.0535] | 0.0494 [0.0453, 0.0538] | 0.0492 [0.0451, 0.0536] | 0.0523 [0.0481, 0.0568] |
| allpairs_asympcs_projection_gaussian (199 looks) | 0.0196 [0.0171, 0.0225] | 0.0252 [0.0223, 0.0285] | 0.0189 [0.0164, 0.0218] | 0.0183 [0.0159, 0.0211] (but see gate row) |
| disjoint_gs_obf (10 looks) | 0.0538 [0.0495, 0.0584] | 0.0501 [0.0460, 0.0546] | 0.0510 [0.0469, 0.0555] | 0.0539 [0.0496, 0.0585] |
| disjoint_betting (paper rule, 199 looks) | 0.0053 [0.0041, 0.0069] | 0.0060 [0.0047, 0.0077] | 0.0043 [0.0032, 0.0058] | 0.0031 [0.0022, 0.0044] |

**The boundary gate's own rejection rate (ever rejected by n = 10000; convention-free; this is the type I error of that gate's test at its boundary):**

| Rule | null (net-benefit gate) | tie_heavy_null (net-benefit gate) | success_boundary (success gate) | compliance_boundary (compliance gate) |
|---|---|---|---|---|
| allpairs_fixed_wald | 0.0503 [0.0462, 0.0548] | 0.0523 [0.0481, 0.0568] | 0.0483 [0.0443, 0.0527] | **0.0551 [0.0508, 0.0597]** |
| allpairs_gs_obf | 0.0496 [0.0455, 0.0540] | 0.0505 [0.0464, 0.0550] | 0.0508 [0.0467, 0.0553] | **0.0546 [0.0503, 0.0592]** |
| allpairs_gs_pocock | 0.0505 [0.0464, 0.0550] | **0.0545 [0.0502, 0.0591]** | 0.0489 [0.0448, 0.0533] | **0.0643 [0.0597, 0.0693]** |
| allpairs_gs_hsd | 0.0493 [0.0452, 0.0537] | 0.0494 [0.0453, 0.0538] | 0.0496 [0.0455, 0.0540] | **0.0567 [0.0523, 0.0614]** |
| allpairs_asympcs_projection_gaussian | 0.0243 [0.0215, 0.0275] | 0.0309 [0.0277, 0.0345] | 0.0257 [0.0228, 0.0290] | **0.0725 [0.0676, 0.0777]** |
| disjoint_gs_obf | 0.0538 [0.0495, 0.0584] | 0.0501 [0.0460, 0.0546] | 0.0510 [0.0469, 0.0555] | **0.0545 [0.0502, 0.0591]** |
| disjoint_betting | 0.0092 [0.0075, 0.0113] | 0.0080 [0.0064, 0.0099] | 0.0081 [0.0065, 0.0101] | 0.0076 [0.0061, 0.0095] |

(For the success and compliance gates the all-pairs statistic equals the arm-mean difference, so the `allpairs_gs_obf` and `disjoint_gs_obf` gate rows differ only by their variance estimators' handling of the same arm means; bold = Wilson interval entirely above 0.05.)

**Retained-crossing convention (for information):**

| Rule | null | tie_heavy_null | success_boundary | compliance_boundary |
|---|---|---|---|---|
| allpairs_gs_obf | 0.0496 [0.0455, 0.0540] | 0.0505 [0.0464, 0.0550] | 0.0508 [0.0467, 0.0553] | 0.0545 [0.0502, 0.0591] |
| allpairs_gs_pocock | 0.0505 [0.0464, 0.0550] | 0.0545 [0.0502, 0.0591] | 0.0489 [0.0448, 0.0533] | 0.0643 [0.0597, 0.0693] |
| allpairs_gs_hsd | 0.0493 [0.0452, 0.0537] | 0.0494 [0.0453, 0.0538] | 0.0496 [0.0455, 0.0540] | 0.0566 [0.0522, 0.0613] |
| allpairs_asympcs_projection_gaussian | 0.0243 [0.0215, 0.0275] | 0.0309 [0.0277, 0.0345] | 0.0257 [0.0228, 0.0290] | 0.0711 [0.0662, 0.0763] |
| disjoint_gs_obf | 0.0538 [0.0495, 0.0584] | 0.0501 [0.0460, 0.0546] | 0.0510 [0.0469, 0.0555] | 0.0544 [0.0501, 0.0590] |
| disjoint_betting | 0.0091 [0.0074, 0.0112] | 0.0080 [0.0064, 0.0099] | 0.0081 [0.0065, 0.0101] | 0.0072 [0.0057, 0.0091] |

**Which rules hold their level at each boundary** ("holds" = Wilson interval contains or lies below 0.05; 28 gate-level cells are tested, so one or two 2-SE excursions are expected by chance):

* Net-benefit boundary (`null`, `tie_heavy_null`): every rule holds its level or is conservative. The all-pairs group-sequential rules, the disjoint OBF rule and the fixed Wald are at 0.049-0.054 (guarded simultaneous and gate-level); the AsympCS spends 0.020-0.025 guarded (0.024-0.031 gate-level); the betting rule 0.005-0.006 guarded (0.008-0.009 gate-level). The single excursion is the Pocock net-benefit gate in `tie_heavy_null`, 0.0545 [0.0502, 0.0591] (2.1 SE; guarded simultaneous 0.0537 [0.0495, 0.0583]).
* Success boundary (`success_boundary`, success difference = -0.03): every rule holds its level. Gate-level 0.0483-0.0510 for the six asymptotic rules (all intervals contain 0.05), 0.0257 for the AsympCS, 0.0081 for the betting rule; guarded simultaneous 0.0477-0.0510, 0.0189 and 0.0043. The success gate is not a rare-event gate (p = 0.72 vs 0.75), so the normal approximation is accurate from n = 100 and the calibration at this boundary is resolved: all rules hold.
* Compliance boundary (`compliance_boundary`, compliance difference = -0.01; expected noncompliance counts 1.5 and 0.5 per 100 records): **no asymptotic rule holds its level at the gate level.** Fixed Wald 0.0551, OBF 0.0546, HSD 0.0567, disjoint OBF 0.0545 (all intervals above 0.05 by 0.0002-0.0023), Pocock 0.0643, and the AsympCS 0.0725 [0.0676, 0.0777]; only the exact betting rule holds (0.0076). As guarded rules under the simultaneous convention the fixed Wald exceeds (0.0550 [0.0507, 0.0596]), the OBF-type rules are marginal (0.0540 and 0.0539, lower bounds 0.0497/0.0496), Pocock (0.0509) and HSD (0.0523) are within their intervals, and the AsympCS shows only 0.0183 because the same-look conjunction with its slow success gate (passes by n = 10000 in 98.1% of replicates, typically after thousands of runs) masks the compliance gate's early excess; under the retained convention its guarded rate is 0.0711 [0.0662, 0.0763]. **This is the interesting case: the projection-based Gaussian CS does not hold its nominal level at the rare-event guardrail boundary within the n = 100..10000 window (7.25% vs 5%), the asymptotic group-sequential rules are mildly anti-conservative there (5.5-6.4%), and the exact betting rule is the only rule that holds level at both guardrail boundaries.** Calibration at the compliance boundary is therefore resolved negatively for the asymptotic rules at the gate level and positively for the betting rule.
* Context: the paper's own stress test (`results/stress_results.csv`, 2000 replicates, a different seed stream) has `guarded_betting` 0.0075 / 0.0045 and `guarded_fixed_wald` 0.0545 / 0.0520 at the success / compliance boundaries, consistent with the rows above.

### 4.7 Diagnostics of the AsympCS compliance-gate failures

*safety_regression (main study, compliance difference -0.02).* Re-running the first 2000 replicates and recording the first look at which the compliance-gate CS lower bound exceeded -0.01 (first session; same seeds, same nine replicates in the current run): first crossings at n = 200 (7) and n = 250 (2); in every case arm A had 200/200 (or 250/250) compliant runs and arm B 199/200 or 248/250, giving `U = +0.005` (or `+0.008`), `sigma_hat = 0.0707` (or `0.0893`), radius 0.0146 (0.0162) and lower bound -0.0096 (-0.0082). Rejections by look: {200: 7, 250: 6, 300: 3, 350: 1, 400: 2, 450: 1}; none after n = 450. With sa = 0.975 the probability that all 200 A runs are compliant is 0.975^200 = 0.6%, so this is the tail where the plug-in variance of a rare-event difference collapses. The exact betting rule has no such failure (0/2000).

*compliance_boundary (calibration, 10000 replicates).* Because the compliance gate is additive, its all-pairs statistic is the arm-mean difference, and the gate can be recomputed from the same seed stream (`SeedSequence([20260918, 109])`) without the all-pairs machinery; the recomputation reproduces every count of `null_calibration.csv` exactly (AsympCS 725, OBF 546, Pocock 643, HSD 567, fixed Wald 551, betting 76), which is an independent check of the stream and of the additive-kernel identity. First-crossing looks of the false compliance rejections:

| Rule | rejections | first crossing: 10% / 25% / 50% / 75% / 90% quantile (records per arm) | share at n <= 500 | share at n <= 1000 |
|---|---|---|---|---|
| allpairs_asympcs_projection_gaussian | 725 (0.0725) | 200 / 250 / 400 / 1050 / 3180 | 0.566 | 0.745 |
| allpairs_gs_pocock | 643 (0.0643) | 1000 / 2000 / 4000 / 7000 / 9000 | 0 (no look) | 0.219 |
| allpairs_gs_hsd | 567 (0.0567) | 3000 / 6000 / 8000 / 9000 / 10000 | 0 | 0.060 |
| allpairs_gs_obf | 546 (0.0546) | 5000 / 6000 / 8000 / 9000 / 10000 | 0 | 0 |
| disjoint_betting | 76 (0.0076) | 475 / 850 / 1825 / 4025 / 7550 | 0.118 | 0.316 |

At the AsympCS crossing look, 239 of the 725 replicates had zero noncompliant A runs and the median noncompliant counts were 1 (arm A) and 4 (arm B): the false rejections are the collapse of the plug-in variance of a rare-event difference at n = 100-1000, exactly the finite-sample regime that the asymptotic guarantee (Section 0, point 1) does not cover. The Pocock excess comes from spending most of its alpha at the early planned looks (n = 1000-3000) where the same approximation is anti-conservative; OBF and HSD spend late and are only mildly affected; the fixed Wald at n = 10000 (150 vs 50 expected noncompliant runs) shows the classical mild anti-conservatism of the one-sided Wald test for a difference of small proportions.

## 5. Interpretation for the paper (suggested wording; no dominance claims; simultaneous convention throughout)

1. Positioning sentence for the limitations/related-work paragraph: "A correctly analysed all-pairs U-statistic (Bebu and Lachin 2016) is asymptotically 13-41% more efficient than the disjoint-pair mean for the hierarchical net benefit on our simulation scenarios at the same 2N executions (Hoeffding variance ratio Var(h)/(zeta_10+zeta_01)), but identical for the component guardrail gates, so guarded stopping times of the two designs coincide when a guardrail is the bottleneck."
2. Sequential comparators: the Zhang-Wu / Bergemann-Hanson group-sequential all-pairs design with Lan-DeMets OBF spending holds its level at the 10 planned looks at the net-benefit boundary (0.0496 [0.0455, 0.0540], 0.0505 [0.0464, 0.0550]) and at the success boundary (0.0508 [0.0467, 0.0553]) over 10000 replicates, is marginally anti-conservative at the rare-event compliance boundary (gate-level 0.0546 [0.0503, 0.0592]), and is not anytime-valid (10 looks, not 199). The projection-based Gaussian CS (asymptotic CS, Waudby-Smith et al. route, 199 looks like the betting rule) is conservative at the net-benefit and success boundaries (0.019-0.025 guarded), reaches the strong-effect deployments earlier than the betting rule under the same simultaneous convention (efficiency_gain 3359 vs 4362 mean runs per arm, joint_gain 715 vs 1427, tie_heavy_efficiency 3683 vs 4791), but does not hold its level at the compliance boundary (compliance gate 0.0725 [0.0676, 0.0777] over the 199 looks; 0.0045 false guarded deployments in safety_regression under the retained convention), because its plug-in variance collapses for rare-event gates at n <= 1000. That is the price of an asymptotic guarantee monitored from n = 100.
3. The paper's own asymptotic disjoint comparators are the right frame of reference: the OBF group-sequential rule on disjoint pairs (added here, simultaneous convention) has higher power than the paper's Bonferroni-at-10-looks rule (weak_gain 0.245 vs 0.109) with the same validity class and the same 10 looks, so if the paper keeps a planned-look comparator it should be the Lan-DeMets one rather than Bonferroni.
4. Do not claim that the betting rule is "as efficient" as all-pairs methods: at the net-benefit boundary null the guarded betting rule spends 0.5-0.6% of its 5% budget (0.8-0.9% on the gate), and in weak_gain its power is 0.035 vs 0.317 (all-pairs OBF, 10 looks) and 0.1055 (all-pairs AsympCS, 199 looks). That gap is the joint price of exactness, anytime validity and disjoint pairs; Section 4.5 attributes at most a factor 1.38 in variance to the pairing.
5. What the boundary calibration adds for the paper's exactness argument: at the compliance boundary (a 1.5%-vs-0.5% rare-event guardrail) every asymptotic rule tested here exceeds its nominal gate-level 5% (5.5-7.3%) and the exact betting rule is the only rule that holds level at both guardrail boundaries (0.0081 and 0.0076 gate-level). This supports the paper's choice of an exact guardrail test without claiming that the asymptotic rules are invalid in their own asymptotic sense.

## 6. Problems, caveats, and what was not done

* The AsympCS label is the asymptotic one stated in Section 0, point 1; no finite-sample crossing bound is claimed, and Section 4.6 shows that none holds at the rare-event compliance boundary in the n = 100..10000 window. Cai-Hu-Li's stitched LIL boundary and delayed-start family were not implemented (the mixture boundary is the one comparable to the paper's CS).
* Information fraction uses `n_k/N` (the first-order limit) rather than the estimated variance ratio of Zhang-Wu; the `xi^{11}/(mn)` term of their variance is omitted (order 1/n^2). Independent increments are used only as the Gaussian-limit covariance structure (Section 0, point 4).
* The group-sequential rules monitor 10 looks and the anytime rules 199; comparisons between the two classes in Section 4.3 state this, and the paper's `guarded_group_bonferroni_wald` also deploys only at the 10 planned looks.
* Multiplicity: the calibration tables test 28 gate-level and 28 guarded cells; the Pocock excursion at `tie_heavy_null` (2.1 SE) is within what chance produces, whereas the compliance-boundary excess is systematic across all six asymptotic rules and is explained by the diagnostic in Section 4.7.
* Only the simultaneous convention is compared with the paper; retained rows are listed for information. Both conventions are intersection-union rules and hold the gate-level guarantee of the underlying tests; the difference is comparison scope.
* Runtime (this revision, `manifest.json` / `calibration_manifest.json`): main study 310 s wall-clock with 8 worker processes (per scenario 243-308 s CPU; 2000 replicates x 8 scenarios, 199 looks each, about 0.15 s per replicate including all rules), peak RSS 460 MB parent, 241 MB maximum child (`resource.getrusage`); the efficiency Monte Carlo with 1e6 pairs per scenario is included. Calibration: 835 s wall-clock (10000 replicates x 4 scenarios, 4 workers, one per scenario, per scenario 645-835 s), peak RSS 335 MB parent, 238 MB maximum child. Machine: 10-core Apple M5, 32 GB, macOS 26.5.2, Python 3.12.13, numpy 2.4.1, scipy 1.17.0.
* Provenance: both manifests record `ustat.py` sha256 `ee98a9b344a628fa1dc49d4c314ef9c52252de70aee74316f8d022b93ea58f5d` and `run_ustat_reference.py` sha256 `cb96f8a58577dc9980109b5ed6932a64deae1f73005e0adf5b5af703103809e8` (the same code ran the main study and the calibration; the only change to `ustat.py` since the audited `8be5638f...` is the module docstring). The audited version's outputs are preserved unchanged in `results/ustat_reference/previous_e1ea314/` (results sha256 `a8a88e7b...`, calibration `da32f87c...`, efficiency `94579d45...`, estimator check `781f1e27...`, gate rates `b759a010...`). Seeds: main study `SeedSequence([20260918, j])`, j = position in `run_online_methods.SCENARIOS`; calibration `SeedSequence([20260918, 100 + index])` with index 0, 6, 8, 9; efficiency Monte Carlo seeds 1000 + j.
* No paid APIs, no git commands, no files outside `experiments/ustat_reference/`, `results/ustat_reference/` and this report were created or modified.
