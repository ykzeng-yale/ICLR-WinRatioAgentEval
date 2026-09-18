# Sequential U-statistic reference baseline vs the disjoint-pair betting e-process

GitHub issue #3. Date: 2026-09-17/18. Author: reference-baseline subagent (this session).
Code: `experiments/ustat_reference/{ustat.py, run_ustat_reference.py, README.md}`.
Results: `results/ustat_reference/{ustat_reference_results.csv, ustat_reference_gate_rates.csv, ustat_reference_efficiency.csv, ustat_reference_estimator_check.csv, null_calibration.csv, manifest.json, calibration_manifest.json, run.log, calibration_run.log}`.
Nothing under `paper/`, `src/`, the paper's experiment scripts or the paper's result files was modified; they were imported or read only.

Every number below was produced by code run in this session or read from the named files. "Predicted" means a normal-approximation formula evaluated on Monte Carlo variance components; "empirical" means the 2000-replicate (or 10000-replicate) simulation.

## 1. What the primary sources say and how the code maps to them

Sources were fetched in this session from arXiv HTML/abs pages and the OUP abstract page (see `evidence/lit_winstats.md` rows 4, 31, 32, 36 for bibliographic details).

| Source | Statement extracted | Code |
|---|---|---|
| Bebu & Lachin 2016 (Biostatistics 17:178-187; OUP page) | `U_v = (1/(nm)) sum_i sum_j phi_v(X_i, Y_j)`, v = 1 (treatment wins), 2 (treatment loses); `sqrt(N)(U - tau) -> N(0, Sigma)` with `sigma_uv = (N/m) xi_10^{uv} + (N/n) xi_01^{uv}`, `xi_10^{uv} = Cov(phi_u(X_1,Y_1), phi_v(X_1,Y_1'))`, `xi_01^{uv} = Cov(phi_u(X_1,Y_1), phi_v(X_1',Y_1))`; log WR by the delta method. | `ustat.hierarchical_prefix_stats` returns `pw = U_1`, `pl = U_2`, `U = U_1 - U_2` (net benefit); the net-benefit variance `var_u = zeta10/n_A + zeta01/n_B` is the quadratic form `sigma_11 + sigma_22 - 2 sigma_12` of the Bebu-Lachin covariance applied to the signed kernel `h = phi_1 - phi_2`, i.e. `zeta10 = Var(E[h(X,Y) | X])`, `zeta01 = Var(E[h(X,Y) | Y])`. Estimators: sample variances of the per-observation conditional means `ghat_10(X_i) = n_B^{-1} sum_j h(X_i,Y_j)` and `ghat_01(Y_j)` (Sen 1960 / the "nonparametric variance from concordant-discordant pair frequencies" of Bebu-Lachin). |
| Bergemann & Hanson 2026 (arXiv:2601.22525v1) | Same `U_nu`; `sigma_uv = (N/m) xi_10 + (N/n) xi_01`; **Proposition 1**: for looks k < l, `cov(U_1k - U_2k, U_1l - U_2l) = var(U_1l - U_2l)` (independent increments of the cumulative all-pairs win difference); information fraction = subjects analysed at the look / subjects at the final look; HSD spending with gamma = -3 for two-sided alpha = 0.05, K = 3 looks at 50/75/100%, boundaries from gsDesign; simulated type I error 0.0517 (N = 200), 0.0487 (N = 400) with complete data. | Information fraction `t_k = n_k / N = k/10` (`run_ustat_reference.py`, `t10`); the cumulative all-pairs statistic at look k uses the first `n_k` runs of each arm (`hierarchical_prefix_stats` with `looks`); `spending('hsd', t, alpha, gamma=-3)`; one-sided alpha = 0.05 here (the paper's gates are one-sided), so their two-sided 0.05 is not reproduced. |
| Zhang & Wu 2024 (arXiv:2410.06281) | Eq. 3.1: `U_{nu k} = (1/(m_k n_k)) sum_{i<=m_k} sum_{j<=n_k} phi_nu(D_i; D'_j)`; **Prop. 3.1**: `Cov(D_p, D_q) = sqrt(V(Delta U_q) / V(Delta U_p))`, `t_k = V(Delta U_K)/V(Delta U_k)`; **Thm 3.4**: canonical joint normal law across K looks under Condition C1 (stage fractions converge); variance `V(Delta U) = [(n-1)/(mn)] xi^{10} + [(m-1)/(mn)] xi^{01} + [1/(mn)] xi^{11}` with `xi^{10}_{uv}, xi^{01}_{uv}, xi^{11}_{uv}` the Hoeffding components of the signed kernel; spending `alpha(t) = alpha t^2`; boundaries by the recursion `P(S_1 > c_1) = alpha_1`, `P(S_1 < c_1, ..., S_k >= c_k) = alpha_k` (one-sided). | Boundaries: `ustat.gs_boundaries` implements exactly this recursion (Armitage-McPherson-Rowe sub-density propagation on a Simpson grid, `brentq` per look). `spending('kim_demets2')` is their `alpha t^2` (implemented, not run). Variance: the leading two terms are used (`zeta10/n + zeta01/n`); the `xi^{11}/(mn)` term is dropped (order 1/n^2, below 1e-8 at n = 100 relative to 1e-3). Information is taken as `n_k/N` rather than the estimated `V_K/V_k`; with equal arm sizes and stationary streams these coincide asymptotically. |
| Cai, Hu & Li 2026 (arXiv:2605.14692v2) | One-sample degree-2 `U_n`; Hoeffding `U_n - theta = (2/n) sum h_1(X_i) + R_n`; nondegeneracy `sigma^2 = Var(h_1) > 0`; **Thm 1** strong Gaussian approximation with error `O(n^{-1+1/(2+delta)})`; **Thm 2** jackknife `sigma_hat_n^2 = n^{-1} sum_i {(n-1)^{-1} sum_{j != i} h(X_i,X_j)}^2 - U_n^2`; **Thm 3** `[U_n +/- 2 sigma_hat_n gamma_{alpha,m}(n)]` is a (1-alpha)-AsympCS with a stitched LIL boundary (eta = 2, s = 1.4) or a Gaussian-mixture boundary; MMD appears only as a degenerate example; no two-sample theorem. | Not directly applicable (two-sample kernel). What is implemented is the standard AsympCS route of Waudby-Smith et al. (2024) applied to the two-sample Hoeffding linear term: with `n_A = n_B = n`, `U_n - theta ~ n^{-1} sum_i {g_10(X_i) + g_01(Y_i)}`, an i.i.d. average with variance `zeta10 + zeta01`, so the CS is `U_n - sigma_hat_n u_alpha(n)/n` with `sigma_hat_n^2 = zeta10_hat + zeta01_hat` (the two-sample analogue of their jackknife; the per-observation conditional means are exactly the leave-one-out row means) and `u_alpha` the exact one-sided normal-mixture boundary of Howard et al. (2021) with `V = n`, `rho^2 = 100` (the paper's tuning in `winstats.normal_mixture_radius`). This is labelled `allpairs_asympcs`; it is **not** a theorem of Cai-Hu-Li. |

One-sided normal mixture used for `allpairs_asympcs`: mixing `exp(lambda S - lambda^2 V/2)` over a half-normal `lambda` with variance `1/rho^2` gives `M = 2 sqrt(rho^2/(V+rho^2)) exp(S^2/(2(V+rho^2))) Phi(S/sqrt(V+rho^2))`; the boundary solves `M = 1/alpha` (`ustat.one_sided_normal_mixture_boundary`). Monte Carlo on 20000 Gaussian random walks of length 20000: crossing frequency 0.0409 +/- 0.0015 at alpha = 0.05 (valid; conservative over a finite horizon).

## 2. Implementation checks (all run in this session)

* Generator identity: `ustat.generate_raw` draws the same stream as `run_simulations.generate` and its `(z, dq, ds)` are bit-identical (asserted). As a stronger check, the paper's betting rule recomputed on these streams reproduces every `guarded_betting` and `win_only_betting` row of `results/online_methods_results.csv` exactly (deployments and mean pairs used, all 8 scenarios; Section 4.0).
* O(n log n) statistics vs brute-force kernel matrix (`ustat.kernel_matrix`, n <= 700) at prefixes 50/120/333/700 in four scenarios: `U`, `p_w`, `p_l`, `zeta10`, `zeta01` agree to 1e-12; the kernel matrix agrees with `winstats.compare` using `Tier('cost', higher_better=False, relative_tolerance=.05)` with the both-compliant-both-successful eligibility mask; its diagonal equals the paper's disjoint-pair `z`. Unequal arm sizes (300 vs 450) also agree.
* Analytic conditional means `g_10`, `g_01` (`ustat.conditional_mean_given_a/b`) integrate to `run_simulations.exact_targets` within Monte Carlo error in all 8 scenarios (Section 4.5 table: `theta_exact` vs `theta_mc`, MCSE about 0.001).
* Boundary code: Lan-DeMets OBF-type, one-sided alpha = 0.025, K = 5 equally spaced: computed 4.8769, 3.3570, 2.6803, 2.2898, 2.0310 vs reference 4.877, 3.357, 2.680, 2.290, 2.031. Constant-boundary Pocock and O'Brien-Fleming constants recovered by root finding on the same recursion: 2.4132 and 2.0401 (textbook two-sided-0.05 values 2.413 and 2.040). K = 1 returns `Phi^{-1}(0.95)` exactly. Cumulative exit probabilities under H0 match the spending function to 1e-14 for all three K = 10 designs. Monte Carlo on 400000 Brownian paths at the K = 10 OBF boundaries: overall crossing 0.0498 +/- 0.0003.
* K = 10, one-sided alpha = 0.05 boundaries used: OBF 6.088, 4.229, 3.396, 2.906, 2.579, 2.342, 2.160, 2.015, 1.895, 1.795; Pocock-type 2.412, 2.363, 2.317, 2.280, 2.250, 2.225, 2.204, 2.187, 2.171, 2.158; HSD(-3) 3.116, 2.982, 2.838, 2.694, 2.549, 2.403, 2.254, 2.101, 1.943, 1.779 (`manifest.json`).
* Variance estimator at n = 10000 (`ustat_reference_estimator_check.csv`): mean estimated `Var(U)` vs empirical variance of `U` across 2000 replicates: null 6.55e-5 vs 6.74e-5, efficiency_gain 6.05e-5 vs 5.92e-5, weak_gain 6.55e-5 vs 6.55e-5, tie_heavy_efficiency 4.48e-5 vs 4.45e-5 (relative MC error of an empirical variance from 2000 replicates is 3.2%).

## 3. Study design and fairness statement

* Generator, 8 scenarios (6 of `run_simulations.py` plus `tie_heavy_null`, `tie_heavy_efficiency`), seeds `SeedSequence([20260918, j])`, 2000 replicates, batch 25: identical to `run_online_methods.py`. Each replicate is 10000 runs of A and 10000 runs of B; disjoint-pair rules see pair i = (A_i, B_i); all-pairs rules compare every A_i with every B_j among the same executions. "Runs used" is per arm, so 10000 runs per arm is the same execution budget as 10000 pairs.
* Same one-sided alpha = 0.05 per gate, same thresholds (net benefit > 0, success difference > -0.03, compliance difference > -0.01), same intersection-union guarded rule, same 199 looks (100..10000 step 50) for the anytime rules, same 10 looks (1000k) for the group-sequential rules.
* Validity classes: `disjoint_betting` (the paper) is exact finite-sample under optional stopping at any look. `allpairs_asympcs` is asymptotically anytime-valid. `allpairs_gs_*` and `disjoint_gs_obf` are asymptotically valid only at the 10 planned looks. `allpairs_fixed_wald` and the paper's `guarded_fixed_wald` are asymptotically valid only at n = 10000. Group-sequential rules therefore use only 10 planned looks and are not anytime-valid comparators.
* Guarded semantics: primary rows let each gate's sequential test stop at its first crossing and deploy at the first look at which all three have crossed ("ever"); `*_simultaneous` rows use the paper's convention (all three statistics beyond their boundaries at the same look). Both are reported for the betting rule; they differ by at most 0.2 percentage points in deployment rate and by < 3% in mean runs.
* No comparison below mixes different nulls: every method tests the same three one-sided hypotheses with the same thresholds.

## 4. Results (2000 replicates unless stated; Wilson 95% CIs; runs per arm)

### 4.0 Data identity

Recomputed `guarded_disjoint_betting_simultaneous` vs the paper's `guarded_betting` (deployments / mean pairs): null 12/9965.3 vs 12/9965.3; efficiency_gain 1932/4361.8 vs 1932/4361.8; success_regression 0 vs 0; safety_regression 0 vs 0; joint_gain 2000/1426.8 vs 2000/1426.8; weak_gain 70/9837.8 vs 70/9837.8; tie_heavy_null 15/9954.1 vs 15/9954.1; tie_heavy_efficiency 1875/4790.7 vs 1875/4790.7. Win-only rows match likewise (16, 2000, 2000, 2000, 2000, 83, 21, 2000). The comparison is on the same executions.

### 4.1 Calibration at the boundary null (net-benefit gate, theta = 0 = c)

Win-only deployment rate = type I error of the net-benefit gate at its boundary.

| Method | null | tie_heavy_null | validity |
|---|---|---|---|
| allpairs_fixed_wald (n = 10000) | 0.0570 [0.0477, 0.0680] | 0.0405 [0.0327, 0.0501] | asymptotic, one look |
| allpairs_gs_obf (10 looks) | 0.0575 [0.0481, 0.0686] | 0.0435 [0.0354, 0.0533] | asymptotic, planned looks |
| allpairs_gs_pocock | 0.0570 [0.0477, 0.0680] | 0.0505 [0.0417, 0.0610] | asymptotic, planned looks |
| allpairs_gs_hsd | 0.0570 [0.0477, 0.0680] | 0.0440 [0.0359, 0.0539] | asymptotic, planned looks |
| allpairs_asympcs (199 looks) | 0.0275 [0.0212, 0.0356] | 0.0200 [0.0147, 0.0271] | asymptotic, anytime |
| disjoint_gs_obf (10 looks) | 0.0530 [0.0440, 0.0637] | 0.0445 [0.0363, 0.0544] | asymptotic, planned looks |
| disjoint_betting (paper) | 0.0080 [0.0049, 0.0130] | 0.0105 [0.0069, 0.0160] | exact, anytime |
| paper guarded_fixed_wald (disjoint, n = 10000) | 0.0495 [0.0408, 0.0599] | 0.0455 [0.0372, 0.0555] | asymptotic, one look |
| paper guarded_group_bonferroni_wald | 0.0230 [0.0173, 0.0305] | 0.0200 [0.0147, 0.0271] | asymptotic, planned looks |

All all-pairs and group-sequential rules are at nominal level within Monte Carlo error at 2000 replicates (the 0.057 values are 1.4 SE above 0.05; see the 10000-replicate calibration in Section 4.6). The asymptotic CS is conservative at the boundary (0.02-0.03), as expected for a normal mixture evaluated over a finite horizon with rho^2 tuned at n = 100 (its Gaussian-walk crossing rate was 0.041). The exact betting rule is the most conservative (0.008-0.011). Guarded rates in the null scenarios equal the win-only rates for every method except the anytime rules, whose success gate occasionally has not yet passed (guarded asympcs 0.0275/0.0200; guarded betting 0.0080/0.0105 "ever", 0.0060/0.0075 "simultaneous").

### 4.2 Regression scenarios (a false gate; guarded deployment should be 0)

success_regression (success difference -0.10 vs threshold -0.03): every method 0/2000 (upper CI 0.0019).
safety_regression (compliance difference -0.02 vs threshold -0.01): 0/2000 for all rules except `guarded_allpairs_asympcs` "ever" 9/2000 = 0.0045 [0.0024, 0.0085] (simultaneous variant 0/2000). Diagnostic (Section 4.7): all nine come from n = 200-250 per arm where arm A had no noncompliant run and arm B had one or two, so the plug-in sigma_hat is determined by a single event. This is the same rare-event failure mode as the paper's `guarded_repeated_wald` (0.0195 in this scenario), and it is a property of asymptotic plug-in variances, not of the all-pairs statistic.

### 4.3 Power and stopping times (admissible scenarios)

Deployment rate; mean runs per arm (capped at 10000); median runs among deployments.

| Scenario | Method | rate [CI] | mean runs | median |
|---|---|---|---|---|
| efficiency_gain | guarded_allpairs_fixed_wald | 0.9995 | 10000 | 10000 |
| | guarded_allpairs_gs_obf | 0.9995 [0.9972, 0.9999] | 4467.5 | 4000 |
| | guarded_allpairs_gs_pocock | 0.9975 | 3101.5 | 3000 |
| | guarded_allpairs_gs_hsd | 0.9995 | 3923.5 | 4000 |
| | guarded_allpairs_asympcs | 0.9815 [0.9746, 0.9865] | 3258.6 | 2550 |
| | guarded_disjoint_gs_obf | 0.9995 | 4471.5 | 4000 |
| | guarded_disjoint_betting (paper, simultaneous) | 0.9660 [0.9571, 0.9731] | 4361.8 | 3750 |
| | paper guarded_group_bonferroni_wald | 0.9930 | 3588.0 | 3000 |
| joint_gain | guarded_allpairs_gs_obf | 1.0 | 2397.5 | 2000 |
| | guarded_allpairs_gs_pocock | 1.0 | 1233.0 | 1000 |
| | guarded_allpairs_gs_hsd | 1.0 | 1497.5 | 1000 |
| | guarded_allpairs_asympcs | 1.0 | 698.4 | 550 |
| | guarded_disjoint_gs_obf | 1.0 | 2393.0 | 2000 |
| | guarded_disjoint_betting (paper) | 1.0 | 1426.8 | 1300 |
| | paper guarded_group_bonferroni_wald | 1.0 | 1305.5 | 1000 |
| weak_gain (theta = 0.0099) | guarded_allpairs_fixed_wald | 0.3280 [0.3078, 0.3489] | 10000 | 10000 |
| | guarded_allpairs_gs_obf | 0.3170 [0.2970, 0.3377] | 9246.5 | 8000 |
| | guarded_allpairs_gs_pocock | 0.2630 [0.2442, 0.2827] | 8891.5 | 6000 |
| | guarded_allpairs_gs_hsd | 0.3110 | 9242.0 | 8000 |
| | guarded_allpairs_asympcs | 0.1160 [0.1027, 0.1308] | 9271.1 | 2675 |
| | guarded_disjoint_gs_obf | 0.2450 [0.2267, 0.2643] | 9451.5 | 8000 |
| | guarded_disjoint_betting (paper) | 0.0350 [0.0278, 0.0440] | 9837.8 | 5075 |
| | paper guarded_fixed_wald (disjoint) | 0.2575 [0.2388, 0.2771] | 10000 | 10000 |
| | paper guarded_group_bonferroni_wald | 0.1090 [0.0961, 0.1234] | 9519.5 | 5000 |
| tie_heavy_efficiency | guarded_allpairs_gs_obf | 0.9995 | 4688.5 | 4000 |
| | guarded_allpairs_gs_pocock | 0.9985 | 3309.5 | 3000 |
| | guarded_allpairs_gs_hsd | 1.0 | 4164.0 | 4000 |
| | guarded_allpairs_asympcs | 0.9660 [0.9571, 0.9731] | 3586.3 | 2875 |
| | guarded_disjoint_gs_obf | 0.9995 | 4686.0 | 4000 |
| | guarded_disjoint_betting (paper) | 0.9375 [0.9260, 0.9473] | 4790.7 | 4100 |
| | paper guarded_group_bonferroni_wald | 0.9900 | 3872.0 | 3000 |

Win-only (net-benefit gate alone) stopping in the strong-effect scenarios: all group-sequential rules stop at the first planned look (1000 runs, both designs); `allpairs_asympcs` mean 102-121 runs (median 100) vs `disjoint_betting` 107-145 (median 100-150); in tie_heavy_efficiency `allpairs_asympcs` 1022 (median 850) vs `disjoint_betting` 1562 (median 1400), and `allpairs_gs_obf` 2728 vs `disjoint_gs_obf` 2875.

### 4.4 Fixed-horizon anchor power (n = 10000 per arm)

Net-benefit gate in weak_gain: all-pairs Wald 0.3280 [0.3078, 0.3489] (normal-approximation prediction from the Monte Carlo variance components: 0.3367); the paper's disjoint fixed Wald on the same executions 0.2575 [0.2388, 0.2771] (prediction 0.2730). Everywhere else the anchor power is 1.0 (effects) or 0 (false gates).

### 4.5 Asymptotic efficiency of all pairs vs disjoint pairs (`ustat_reference_efficiency.csv`, 1e6 Monte Carlo pairs, analytic conditional means)

| Scenario | theta exact | theta MC | Var(h) | zeta10 | zeta01 | ARE = Var(h)/(zeta10+zeta01) | empirical Var ratio at n = 10000 (2000 reps) |
|---|---|---|---|---|---|---|---|
| null | 0.0000 | -0.0010 | 0.9026 | 0.3276 | 0.3272 | 1.378 | 1.337 |
| efficiency_gain | 0.3625 | 0.3639 | 0.7828 | 0.4863 | 0.1184 | 1.295 | 1.286 |
| success_regression | 0.3106 | 0.3110 | 0.8054 | 0.6317 | 0.0594 | 1.166 | 1.181 |
| safety_regression | 0.4105 | 0.4106 | 0.7547 | 0.5473 | 0.0688 | 1.225 | 1.213 |
| joint_gain | 0.3060 | 0.3063 | 0.8304 | 0.3489 | 0.2415 | 1.406 | 1.398 |
| weak_gain | 0.0099 | 0.0093 | 0.9041 | 0.3241 | 0.3308 | 1.381 | 1.349 |
| tie_heavy_null | 0.0000 | 0.0005 | 0.5085 | 0.2206 | 0.2201 | 1.154 | 1.171 |
| tie_heavy_efficiency | 0.0580 | 0.0583 | 0.5075 | 0.3056 | 0.1426 | 1.133 | 1.155 |

(MCSE of theta MC about 0.001; the empirical variance ratio has relative MC error about 4.5%.) The all-pairs statistic is 13-41% more efficient than the disjoint-pair mean for the hierarchical net benefit; equivalently, disjoint pairs need 1.13-1.41 times as many runs for the same asymptotic precision on that gate. Consistency with the empirical results: (i) weak_gain fixed-horizon power 0.328 vs 0.258 matches the predicted 0.337 vs 0.273; (ii) under the same OBF rule, win-only stopping in tie_heavy_efficiency is 2728 vs 2875 mean runs (ratio 1.054, compressed by the 1000-run look grid; ARE 1.13) and the weak_gain group-sequential power is 0.317 vs 0.245.

**The efficiency gain does not transfer to the guarded decision.** For the success and compliance gates the kernel is additive, `g(a) - g(b)`, so the all-pairs U-statistic is exactly the difference of arm means, which is the same number as the disjoint-pair mean of `dq`/`ds`; its projection variance `(Var_A + Var_B)/n` is the disjoint variance; ARE = 1 identically. Since the guarded rules in efficiency_gain, joint_gain and tie_heavy_efficiency are bottlenecked by the success gate (success difference 0 or +0.09 vs threshold -0.03), the guarded all-pairs and disjoint group-sequential rules stop at practically the same time (4467.5 vs 4471.5; 2397.5 vs 2393.0; 4688.5 vs 4686.0 mean runs). Only in weak_gain, where the net-benefit gate is the bottleneck, does the guarded rule inherit the gain (0.317 vs 0.245 power).

### 4.6 Ten-thousand-replicate null calibration (`null_calibration.csv`, fresh seed stream `SeedSequence([20260918, 100 + j])`)

Net-benefit gate at its boundary (win-only rate; guarded rates are identical for the group-sequential rules), 10000 replicates per scenario, runtime 715 s (two worker processes, one per scenario), peak child RSS 339 MB:

| Method | null | tie_heavy_null |
|---|---|---|
| allpairs_fixed_wald (n = 10000) | 0.0503 [0.0462, 0.0548] | 0.0523 [0.0481, 0.0568] |
| allpairs_gs_obf | 0.0496 [0.0455, 0.0540] | 0.0505 [0.0464, 0.0550] |
| allpairs_gs_pocock | 0.0505 [0.0464, 0.0550] | 0.0545 [0.0502, 0.0591] |
| allpairs_gs_hsd | 0.0493 [0.0452, 0.0537] | 0.0494 [0.0453, 0.0538] |
| allpairs_asympcs | 0.0243 [0.0215, 0.0275] | 0.0309 [0.0277, 0.0345] |
| disjoint_gs_obf | 0.0538 [0.0495, 0.0584] | 0.0501 [0.0460, 0.0546] |
| disjoint_betting (paper rule, "ever") | 0.0092 [0.0075, 0.0113] | 0.0080 [0.0064, 0.0099] |
| disjoint_betting (paper convention, simultaneous, guarded) | 0.0053 [0.0041, 0.0069] | 0.0060 [0.0047, 0.0077] |

The 2000-replicate values of 0.057 in Section 4.1 were Monte Carlo noise: at 10000 replicates every all-pairs and group-sequential rule is within its Wilson interval of 0.05 (the tie_heavy_null Pocock value 0.0545 is 2.1 SE above 0.05; the others are within 1.1 SE). The AsympCS spends about half of its budget (0.024-0.031) and the exact betting rule about one fifth (0.008-0.009). True-gate pass rates by n = 10000 for the anytime rules: success gate (difference 0 vs threshold -0.03) 0.985/0.968 for the AsympCS and 0.971/0.942 for the betting rule; compliance gate 1.000 for both.

### 4.7 Diagnostic: AsympCS false compliance-gate passes in safety_regression

Re-running the first 2000 replicates of safety_regression and recording the first look at which the compliance-gate CS lower bound exceeded -0.01: nine replicates, first crossings at n = 200 (7) and n = 250 (2); in every case arm A had 200/200 (or 250/250) compliant runs and arm B 199/200 or 248/250, giving `U = +0.005` (or `+0.008`), `sigma_hat = 0.0707` (or `0.0893`), radius 0.0146 (0.0162) and lower bound -0.0096 (-0.0082). Rejections by look: {200: 7, 250: 6, 300: 3, 350: 1, 400: 2, 450: 1}; none after n = 450. With sa = 0.975 the probability that all 200 A runs are compliant is 0.975^200 = 0.6%, so this is the tail where the plug-in variance of a rare-event difference collapses. The exact betting rule has no such failure (0/2000).

## 5. Interpretation for the paper (suggested wording; no dominance claims)

1. Positioning sentence for the limitations/related-work paragraph: "A correctly analysed all-pairs U-statistic (Bebu and Lachin 2016) is asymptotically 13-41% more efficient than the disjoint-pair mean for the hierarchical net benefit on our simulation scenarios (Hoeffding variance ratio Var(h)/(zeta_10+zeta_01)), but identical for the component guardrail gates, so guarded stopping times of the two designs coincide when a guardrail is the bottleneck."
2. Sequential comparators: the Zhang-Wu / Bergemann-Hanson group-sequential all-pairs design with Lan-DeMets OBF spending holds its level at the 10 planned looks (0.0496 [0.0455, 0.0540] and 0.0505 [0.0464, 0.0550] at the boundary null over 10000 replicates) but is not anytime-valid and cannot be evaluated at the 199 looks; the asymptotic anytime CS (Waudby-Smith et al. route on the U-statistic) is conservative at the boundary (0.02-0.03) and reaches the strong-effect deployments at similar or slightly earlier looks than the betting rule (efficiency_gain 3259 vs 4362 mean runs, joint_gain 698 vs 1427, tie_heavy_efficiency 3586 vs 4791), at the price of asymptotic validity and a demonstrable rare-event failure on the compliance gate at n <= 450 (0.45% false guarded deployments in safety_regression vs 0 for the exact rule).
3. The paper's own asymptotic disjoint comparators are the right frame of reference: the OBF group-sequential rule on disjoint pairs (added here) has higher power than the paper's Bonferroni-at-10-looks rule (weak_gain 0.245 vs 0.109) with the same validity class, so if the paper keeps a planned-look comparator it should be the Lan-DeMets one rather than Bonferroni.
4. Do not claim that the betting rule is "as efficient" as all-pairs methods: at the boundary null the betting rule spends 0.8-1.1% of its 5% budget, and in weak_gain its power is 0.035-0.042 vs 0.317 (all-pairs OBF) and 0.116 (all-pairs AsympCS). That gap is the joint price of exactness, anytime validity and disjoint pairs; Section 4.5 attributes at most a factor 1.38 in variance to the pairing.

## 6. Problems, caveats, and what was not done

* The Cai-Hu-Li theorem is one-sample; the two-sample AsympCS here is the standard time-uniform-CLT route with the Hoeffding projection variance and is labelled as such. Their stitched LIL boundary was not implemented (the mixture boundary is the one comparable to the paper's CS).
* Information fraction uses `n_k/N` (Bergemann-Hanson's subject fraction) rather than the estimated variance ratio of Zhang-Wu; under stationary streams these agree.
* The `xi^{11}/(mn)` term of Zhang-Wu's variance is omitted (order 1/n^2).
* All-pairs and group-sequential rules are asymptotic: the null rates 0.057 (n = 10000, 2000 replicates) were within Monte Carlo error of 0.05 and the 10000-replicate check (Section 4.6) gives 0.049-0.055. At n = 100-450 the asymptotic CS is unreliable for rare-event gates (Section 4.7).
* Only the primary "ever" semantics is compared across all rules; the paper's "simultaneous" convention changes rates by <= 0.2 pp and mean runs by < 3%.
* Runtime: main study 412 s wall-clock with 8 worker processes (per scenario 335-409 s CPU; 2000 replicates x 8 scenarios, 199 looks each, about 0.06 s per replicate); peak RSS 457 MB parent, 244 MB maximum child (`resource.getrusage`). Efficiency Monte Carlo with 1e6 pairs per scenario is included in that time. Null calibration: 715 s wall-clock (10000 replicates x 2 scenarios, 2 workers), peak child RSS 339 MB. Machine: 10-core Apple silicon, 32 GB.
* Provenance: `manifest.json` records `run_ustat_reference.py` sha256 `ed7c1236...` (the version that ran the main study); the `--calibration-only` mode was added afterwards (current sha256 `aaa91835...`, recorded in `calibration_manifest.json`); the main-study code path and `ustat.py` (`8be5638f...`) are unchanged between the two.
* No paid APIs, no git commands, no files outside `experiments/ustat_reference/`, `results/ustat_reference/` and this report were created or modified.
