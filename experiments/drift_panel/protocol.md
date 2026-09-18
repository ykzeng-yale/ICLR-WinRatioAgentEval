# Drift and unequal-law-null panel: frozen protocol

Frozen 2026-09-18, before any random number was drawn for this panel. The only computation performed before freezing was the deterministic `--design-check` mode of `run_drift_panel.py` (closed-form per-step targets, running averages and violation windows; no sampling). This is an internal frozen plan, not a public preregistration. It is an extension designed after the paper's first simulations (`experiments/simulation_protocol.md` lists "drifting running-average targets" as a required extension) and must be labelled as such. The sha256 of this file is stored in `results/drift_panel/manifest.json`; the runner refuses to start if the hash passed on the command line differs from the file.

Synthetic CPU-only Monte Carlo. No model, API or benchmark call. Code uses only `src/winstats.py` (`normal_mixture_radius`, `betting_log_e_ternary`, `compare`, `Tier`), numpy, scipy (matplotlib for figures).

## 1. Data-generating mechanism

Pair i (one execution of A, one of B; N pairs = 2N executions) has independent arm outcomes: compliance ~ Bern(sA_i / sB_i), success ~ Bern(pA_i / pB_i), cost_A = r_i * k_i * LN(0, sigma_i), cost_B = k_i * LN(0, sigma_i). All parameter paths are deterministic functions of i, so the conditional mean given the past equals the per-step mean. Hierarchy and scores are those of `run_simulations.py`: compliance, then success (when compliance ties, including both noncompliant), then cost only if both compliant and both successful and |cA-cB| > tol*max(cA,cB) (tol = 0.05 except C2). Gate scores: Z0 = hierarchy sign (net benefit), Z1 = successA-successB, Z2 = compliantA-compliantB, all in {-1,0,1}. The common cost scale k_i cancels in the relative-tolerance comparison by construction; it is included to show exactly that.

Per-step targets (exact): with agree = sA sB + (1-sA)(1-sB), a = log(1-tol), mu = log r, sd = sqrt(2) sigma, rp = Phi((a-mu)/sd) - Phi((a+mu)/sd):
mu_0i = (sA-sB) + agree (pA-pB) + sA sB pA pB rp; mu_1i = pA-pB; mu_2i = sA-sB. Running targets: bar-mu_jn = n^{-1} sum_{i<=n} mu_ji (Theorem normal_cs / drift_gate notation). Where a scenario prescribes a net-benefit path, r_i is obtained by 200-step bisection on mu (error < 1e-13).

Thresholds c = (0, -0.03, -0.01). A running target is "violated at n" iff bar-mu_jn <= c_j + 1e-9 (the tolerance only absorbs floating-point error at exact boundaries).

## 2. Scenarios (index = seed index, in this order)

Common-drift paths (family A): p_i = 0.75 + 0.10 sin(2 pi i/2000) - 0.10*1[i>5000]; s_i = 0.990 + 0.005 sin(2 pi i/2500); sigma_i = 0.45(1 + 0.3 sin(2 pi i/3000)); k_i = exp(0.5 sin(2 pi i/2500)) * (1 + 1[i>5000]).

| # | name | definition | replicates |
|---|---|---|---|
| 0 | A1_identical_null | both arms (s_i, p_i), r=1; all targets 0 at every step | 10,000 |
| 1 | A2_success_boundary | pA = p_i - 0.03 at every step, r = 0.4, compliance equal | 10,000 |
| 2 | A3_compliance_boundary | sA = s_i - 0.01 at every step, r = 0.4, success equal | 10,000 |
| 3 | A4_constant_nb_0p10 | equal success/compliance, r_i solved so mu_0i = 0.10 exactly | 2,000 |
| 4 | A5_joint_gain | pA = p_i + 0.05, r = 0.75 | 2,000 |
| 5 | A6_strong_all_gates | sB = s_i - 0.07, pA = p_i + 0.10, r = 0.55 (added because the range-based CS cannot pass a -0.01 compliance gate within 10,000 pairs unless the compliance difference exceeds about +0.023: radius at n=10,000 is 0.0327 at alpha and 0.0360 at alpha/3) | 2,000 |
| 6 | B1_nb_pos_then_neg | sB=.90, sA=.98, pB=.75, pA=.85, sigma=.45; mu_0i = +0.2 (i<=3000), -0.2 after. bar-mu_0n <= 0 iff n >= 6000 | 10,000 |
| 7 | B2_nb_neg_then_pos | as B1 with -0.2 then +0.2. bar-mu_0n <= 0 iff n <= 6000 | 10,000 |
| 8 | B3a_alternating_violator | sB=.90, pB=.75; blocks (0,2000],(2000,4000],(4000,10000]: mu_0 = 0, .2, .2; mu_1 = -.03, -.03, +.15; mu_2 = +.08, -.10, -.01. Violated running targets: net benefit n<=2000 (exactly 0), success n<=4000 (exactly -0.03), compliance n>=4000 (exactly -0.01). Every look has a violated target; no gate is violated at all looks | 10,000 |
| 9 | B3b_cycling_violator | blocks ending 500,1000,5000,8000,10000: mu_0 = 0,.2,.2,-.3,0; mu_1 = -.03,-.03,.15,.15,.15; mu_2 = .08,-.10,-.01,-.01,.08. Violated: net benefit n<=500 and n>=8000, success n<=1000, compliance 1000<=n<=8000 | 10,000 |
| 10 | C1_unequal_law_null | s=.995 both, pB=.75, r=1.10 (A costlier), pA = agree pB/(agree + s^2 pB rp) in closed form (about 0.823) so theta = mu_0 = 0 exactly; stationary | 10,000 |
| 11 | C2_unequal_law_null_tie_heavy | as C1 with pB=.10, r=1.50, tol=0.50 (most pairs tie), pA closed form | 10,000 |

B cells are error-rate cells and therefore use 10,000 replicates.

## 3. Rules (all evaluated on every scenario, same streams)

Looks: every 50 pairs from 100 to 10,000 plus the ten group looks (identical to `run_simulations.py`; 199 looks). alpha = 0.05.
1. win_only_betting: E_0n(0) >= 1/alpha. 2. win_only_normal_mixture: L_0n(alpha) > 0.
3. guarded_betting: E_jn(c_j) >= 1/alpha for all j at the same look (paper's stationary IUT rule).
4. guarded_betting_split: same with 1/(alpha/3). Exploratory comparator; not a rule proposed in the paper.
5. guarded_normal_mixture: L_jn(alpha) > c_j for all j. 6. guarded_normal_mixture_split: L_jn(alpha/3) > c_j for all j (the paper's drift rule, J+1 = 3).
7. guarded_repeated_wald, 8. guarded_group_bonferroni_wald (10 looks, alpha/10), 9. guarded_fixed_wald (n=10,000 only); definitions copied from `run_simulations.py` (estimated-variance one-sided Wald bounds, per-gate alpha).
Betting grid: 40 geometric bets from 1e-4 to 0.99/(1+c); rho = 100; V_n = n.

## 4. Events and metrics (per scenario x rule)

Let D_n = "the rule's deployment condition holds at look n", tau = first look with D_n (capped at 10,000 if none).
- ever_deploy: some D_n.
- E_running_first: tau exists and some claimed running target is violated at tau.
- E_running_any: exists a look n with D_n and some claimed running target violated at n (monitoring without stopping; this is the event of Theorem drift_gate read over all looks, and it contains E_running_first).
- E_current_first (descriptive only, no rule claims to control it): at tau some claimed per-step target mu_{j,tau} <= c_j.
"Claimed" targets: all three gates for guarded rules; net benefit only for win-only rules (a win-only deployment of an arm that fails a guardrail is a deployment failure relative to the guardrails but not an error of its own claim; it is visible through ever_deploy).
- E_stationary (false deployment under a stationary/pointwise conditional null) is defined only where one fixed gate j* has mu_{j*,i} <= c_{j*} at every step: A1, A2, A3, C1, C2. There every look is violated, so E_stationary = ever_deploy = E_running_any = E_running_first. In family B no fixed gate's conditional null holds at every step, E_stationary is undefined, and the stationary IUT guarantee of the betting rule does not apply.
- Sample use: mean of tau (pairs), MCSE, mean executions = 2 x pairs, median tau among deployers (conditional summary only).
- Intervals: 95% Wilson.

## 5. What is guaranteed (stated before the run)

| cells | rule | guarantee from the paper's theorems |
|---|---|---|
| A1-A3, C1, C2 | betting rules (win-only only in A1, C1, C2) | P(ever deploy) <= alpha: Theorem betting applied to the fixed gate j* (the argument of Theorem iut; note Theorem iut is stated for constant means of all scores, whereas here only gate j* is constant or at its boundary; its proof uses only gate j*). |
| A1-A3, C1, C2 | normal-mixture rules, per-gate or split | <= alpha (split: <= alpha/3): Theorem drift_gate, fixed-index clause. |
| B1, B2 | normal-mixture rules | Only net benefit is ever violated, so E_running_any is contained in miscoverage of the net-benefit CS: <= alpha (per-gate), <= alpha/3 (split), by Theorem normal_cs. |
| B3a, B3b | guarded_normal_mixture_split | P(E_running_any) <= alpha by Theorem drift_gate. |
| B3a, B3b | guarded_normal_mixture (per-gate alpha) | Only the union bound 3 alpha = 0.15. |
| B (all) | betting rules | No guarantee claimed by the paper (the conditional null fails at some steps). Remark recorded before the run, to be checked by the theory owner and NOT a paper claim: for nonnegative bets, prod(1+lambda(mu_i-c)) <= exp(lambda n (bar-mu_n - c)) <= 1 whenever bar-mu_n <= c, so at such n the wealth is dominated by the mean-one martingale prod (1+lambda(Z_i-c))/(1+lambda(mu_i-c)); Ville then bounds P(exists n: bar-mu_n <= c and E_n(c) >= 1/alpha') by alpha'. If correct, the single-gate betting test controls the running-average error event too, per-gate betting has the 3 alpha union bound in B3 and the split betting rule has alpha. The panel can only fail to contradict this. |
| all | Wald rules | None finite-sample. |
| all | E_current_first, and any statement about the current or future effect | None. |

An observed rate is reported with its Wilson interval. A rate is described as "below 0.05" only if the upper Wilson limit is below 0.05, as "above 0.05" only if the lower limit is above 0.05, and otherwise as "not resolved". Guaranteed and merely observed control are reported in separate columns.

## 6. Unequal-law contrast (C)

theta = 0 is verified by the exact formula and by 10^6 Monte Carlo pair draws scored with `winstats.compare` (seeds SeedSequence([20260919, 9000+k])); the same verification is run for every distinct parameter set of B and C and for steps 1, 2000, 5000, 5001, 10000 of each A scenario. Report exact, MC, SE, z; no abort threshold, but any |z| > 4 is a logged problem.
Equality-in-distribution contrast: fixed-sample label-permutation test at 500 pairs (1,000 executions), B = 199 permutations, statistic max(|z| of success-rate difference, |z| of Wilcoxon rank-sum on cost), p = (#{T_perm >= T_obs} incl. observed)/(200), reject at p <= 0.05; component tests reported too. Compliance is not used (equal by design). Cells: C0 equal-law calibration (both arms pB=.75, r=1; 10,000 replicates), C1 and C2 laws (2,000 replicates each). Seeds SeedSequence([20260919, 8000+k]). The permutation test and the sequential rules test different nulls; rejection by the former in C1/C2 is a correct rejection of equality in law, not evidence against theta <= 0.

## 7. Computation

Seeds: scenario k uses SeedSequence([20260919, k]).spawn(40); chunk c (500 replicates) uses child c, so results do not depend on the number of workers. At most 5 worker processes. Runtime recorded. Figures: (1) design running-target paths for B, (2) error rates with Wilson intervals for null/boundary/drift cells, (3) deployment rate and mean capped pairs for the power cells.

## 8. Deviations

Any departure from this file is logged in `evidence/drift_panel_report.md` under "Deviations".
