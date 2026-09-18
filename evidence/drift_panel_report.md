# Drift and unequal-law-null panel: report

Date 2026-09-18. Synthetic independent-pair streams; CPU only; no model or API calls. Protocol `experiments/drift_panel/protocol.md` (sha256 `bb497cbb...276cc`) was frozen before any random draw; this is an internally frozen extension, not a public preregistration. All numbers below are read from `results/drift_panel/results.csv`, `permutation_results.csv` and `manifest.json` (runner sha256 `1bc0a113...3a41`, `src/winstats.py` sha256 `3053f8a1...7fd9`). Runtime 53.3 s with 5 workers.

Settings: max 10,000 pairs = 20,000 executions; 199 looks (every 50 from 100, plus the ten group looks); one-sided alpha 0.05 per gate, split rules use 0.05/3; thresholds 0 / -0.03 / -0.01; 10,000 replicates for null, boundary and drift cells, 2,000 for power cells; Wilson 95% intervals in brackets.

## 1. Events

D_n = the rule's deployment condition holds at look n; tau = first such look.
- E_stationary: defined only when one fixed gate's conditional mean is at or below its threshold at every step (A1-A3, C1, C2). Then every look is violated and E_stationary = ever-deploy.
- E_running_any: some look n has D_n while a claimed running-average target at n is at or below its threshold (the Theorem drift_gate event, read over all looks). E_running_first: the same at tau only.
- E_current_first: descriptive; at tau the current per-step target is violated. No rule claims to control it.
- Guarded rules claim all three gates; win-only rules claim net benefit only.
In B no fixed gate's conditional null holds at every step, so E_stationary is undefined there and the stationary IUT guarantee of guarded betting does not apply.

Exact targets were checked with 10^6 draws scored by `winstats.compare` for 44 parameter sets (132 target comparisons): max |z| = 2.34, 5 of 132 with |z| > 2, none above the protocol's flag of 4.

## 2. Guaranteed versus observed

"Guaranteed" is what the paper's theorems give for that rule in that cell; "observed" is the Monte Carlo rate. A guarantee is not evidence from this panel and an observation is not a guarantee.

### 2.1 Common drift, conditional null at every step (E_stationary = ever-false-deployment)

| rule | guaranteed bound | A1 identical | A2 success boundary | A3 compliance boundary |
|---|---|---|---|---|
| win_only_betting | 0.05 (A1 only) | 0.0097 [0.0080, 0.0118] | deploys 1.0000; not an error of its own claim (nb 0.18-0.62) but a guardrail failure | same, 1.0000 |
| win_only_normal_mixture | 0.05 (A1 only) | 0.0089 [0.0072, 0.0109] | 1.0000 (as above) | 1.0000 (as above) |
| guarded_betting | 0.05 | 0.0055 [0.0042, 0.0072] | 0.0038 [0.0028, 0.0052] | 0.0038 [0.0028, 0.0052] |
| guarded_betting_split | 0.0167 | 0.0015 [0.0009, 0.0025] | 0.0013 [0.0008, 0.0022] | 0.0010 [0.0005, 0.0018] |
| guarded_normal_mixture | 0.05 | 0 [0, 0.0004] | 0 [0, 0.0004] | 0 [0, 0.0004] |
| guarded_normal_mixture_split | 0.0167 | 0 [0, 0.0004] | 0 [0, 0.0004] | 0 [0, 0.0004] |
| guarded_repeated_wald | none | 0.2686 [0.2600, 0.2774] | 0.3052 [0.2963, 0.3143] | 0.2977 [0.2888, 0.3067] |
| guarded_group_bonferroni_wald | none (asymptotic) | 0.0222 [0.0195, 0.0253] | 0.0217 [0.0190, 0.0247] | 0.0230 [0.0202, 0.0261] |
| guarded_fixed_wald | none (asymptotic) | 0.0486 [0.0446, 0.0530] | 0.0508 [0.0467, 0.0553] | 0.0510 [0.0469, 0.0555] |

Reading: for the betting and normal-mixture rules the upper Wilson limits are below 0.05 in all three cells (observation consistent with, and far inside, the guarantee). Repeated Wald is above 0.05 (lower limits 0.26-0.30). Bonferroni group Wald is below 0.05 in these cells, without a finite-sample guarantee. Fixed-horizon Wald is not resolved relative to 0.05 in A2, A3 (intervals contain 0.05) and its A1 interval [0.0446, 0.0530] also contains 0.05: no level claim is made. Shared drift in difficulty, cost dispersion and cost scale did not produce any visible inflation for the finite-sample rules, as the theory predicts (the conditional null holds at every step).

Guarantee source: Theorem betting applied to the fixed gate (the proof of Theorem iut uses only that gate; the theorem as stated assumes all score means constant, which A2/A3 do not satisfy for net benefit, so the citation should be to the proof argument or the theorem statement relaxed); Theorem drift_gate, fixed-index clause, for the normal-mixture rules.

### 2.2 Power under common drift (2,000 replicates)

| rule | A4 nb = 0.10 exactly, other gates 0: deploy rate; mean pairs (MCSE) | A5 joint gain | A6 all gates strongly satisfied |
|---|---|---|---|
| win_only_betting | 1.000; 964 (12) | 1.000; 185 (2) | 1.000; 100 (0) |
| guarded_betting | 0.9585 [0.9488, 0.9664]; 4394 (51) | 1.000; 2081 (29) | 1.000; 241 (2) |
| guarded_betting_split | 0.9160 [0.9030, 0.9274]; 5360 (53) | 1.000; 2659 (33) | 1.000; 279 (2) |
| guarded_normal_mixture | 0 [0, 0.0019]; 10000 | 0 [0, 0.0019]; 10000 | 1.000; 1481 (6) |
| guarded_normal_mixture_split | 0 [0, 0.0019]; 10000 | 0 [0, 0.0019]; 10000 | 1.000; 1868 (7) |
| guarded_repeated_wald (invalid) | 1.000; 1091 (22) | 1.000; 456 (9) | 1.000; 121 (1) |
| guarded_group_bonferroni_wald | 0.990; 3522 (43) | 1.000; 1658 (21) | 1.000; 1000 (0) |
| guarded_fixed_wald | 0.999; 10000 | 1.000; 10000 | 1.000; 10000 |

Executions are twice the pairs. The range-based normal-mixture rule cannot pass a -0.01 compliance gate within 10,000 pairs unless the compliance difference exceeds about +0.023 (radius 0.0327 at alpha, 0.0360 at alpha/3, at n = 10,000), so it never deploys in A4/A5 (as in the paper's first simulations) and needs A6-type effects (compliance +0.07) to deploy. In A6 the alpha split costs the CS rule 1868 vs 1481 mean pairs (+26%); the split costs betting 279 vs 241 in A6, 2659 vs 2081 in A5 and 5360 vs 4394 plus 4.3 points of deployment rate in A4.

### 2.3 Treatment-by-time drift (E_running_any; E_stationary undefined)

| rule | guaranteed for E_running | B1 pos then neg | B2 neg then pos | B3a alternating | B3b cycling |
|---|---|---|---|---|---|
| guarded_normal_mixture_split (paper's drift rule) | B1/B2 0.0167; B3 0.05 (Thm drift_gate) | 0.0001 [0.0000, 0.0006] | 0 [0, 0.0004] | 0 [0, 0.0004] | 0 [0, 0.0004] |
| guarded_normal_mixture, per-gate alpha | B1/B2 0.05 (only nb is ever violated, Thm normal_cs); B3 only the union bound 0.15 | 0.0001 [0.0000, 0.0006] | 0.0001 [0.0000, 0.0006] | 0 [0, 0.0004] | 0 [0, 0.0004] |
| guarded_betting, per-gate alpha | none from the paper | 0.0001 [0.0000, 0.0006] | 0.0001 [0.0000, 0.0006] | 0.0037 [0.0027, 0.0051] | 0.0048 [0.0036, 0.0064] |
| guarded_betting_split | none from the paper | 0.0001 [0.0000, 0.0006] | 0 [0, 0.0004] | 0.0008 [0.0004, 0.0016] | 0.0015 [0.0009, 0.0025] |
| win_only_betting (nb claim only) | none from the paper | 0.0001 | 0.0001 | 0.0068 [0.0054, 0.0086] | 0.0033 [0.0024, 0.0046] |
| win_only_normal_mixture (nb claim only) | 0.05 (Thm normal_cs) | 0.0001 | 0.0001 | 0.0067 [0.0053, 0.0085] | 0.0026 [0.0018, 0.0038] |
| guarded_repeated_wald | none | 0.0470 [0.0430, 0.0513] | 0.0462 [0.0423, 0.0505] | 0.2861 [0.2773, 0.2950] | 0.3189 [0.3098, 0.3281] |
| guarded_group_bonferroni_wald | none | 0.0041 [0.0030, 0.0056] | 0.0050 [0.0038, 0.0066] | 0.0168 [0.0145, 0.0195] | 0.0193 [0.0168, 0.0222] |
| guarded_fixed_wald | none | 0 (never deploys; final running nb = -0.08) | 0 [0, 0.0004] (deploys 1.000, correctly: final running nb = +0.08) | 0.0495 [0.0454, 0.0539] | 0.0445 [0.0406, 0.0487] |

What is guaranteed: only the normal-mixture rows, and in B3 only the split rule at 0.05. What is merely observed: everything else, including the low betting rates. In B3a/B3b every look has a violated running target at its exact boundary and no gate is violated at all looks (Figure 1), so every guarded deployment is an E_running error; the per-gate normal-mixture and both betting rules stayed far below 0.05 (upper limits at most 0.0064), and the per-gate-vs-split distinction was not empirically detectable for the CS rule because it made zero deployments in either form. The panel therefore does not demonstrate that the alpha split is necessary in practice; it shows the split rule's guarantee is not contradicted and that the range-based CS is so conservative here that both forms are inert in B3. Repeated Wald is above 0.05 in B3a/B3b; in B1/B2 its interval contains 0.05 (not resolved). Fixed Wald in B3a is not resolved; in B3b the upper limit is 0.0487.

Descriptive facts that no guarantee covers:
- B1: every sequential rule deploys in 10,000/10,000 replicates (betting and normal-mixture rules at mean 283 to 1484 pairs; repeated Wald at 145; group Bonferroni Wald at its first look, 1000), with the first deployment always before the reversal at n = 3000 (E_current_first = 0, E_running_first = 0). Those deployments are correct for the running target and for the then-current effect, yet the effect is -0.2 for the remaining 7,000 pairs and the final running net benefit is -0.08. A running-average guarantee says nothing about the future (paper, after Theorem drift_gate).
- B2: the sequential rules deploy in all replicates at mean 7395 to 7586 pairs, i.e. after the running average crosses 0 at n = 6000; repeated Wald deploys at mean 6685 with 4.6% of first deployments at a violated look.
- B3: win-only rules deploy in all replicates while a guardrail running target is violated at every look; by their own claim the error rate is that in the table.

Remark recorded in the protocol before the run (not a paper claim; for the theory owner to verify): with nonnegative bets, prod(1+lambda(mu_i-c)) <= exp(lambda n (bar-mu_n - c)) <= 1 whenever bar-mu_n <= c, so at such n the betting wealth is dominated by the mean-one martingale prod(1+lambda(Z_i-c))/(1+lambda(mu_i-c)), and Ville gives P(exists n: bar-mu_n <= c, E_n(c) >= 1/a) <= a. If correct, betting gates also control the running-average event, per-gate betting would have the 3 alpha union bound under alternating violators and split betting alpha. The observed betting rates in B are consistent with this but cannot establish it.

### 2.4 Unequal-law null (theta = 0 exactly, laws differ)

C1: s = 0.995, pB = 0.75, A 10% costlier, pA = 0.823269 (closed form). Exact theta = -2.8e-17; MC 0.000056 (SE 0.00096, 10^6 draws); success difference +0.0733; tie probability 0.083.
C2 (tie-heavy): pB = 0.10, A 50% costlier, 50% cost tolerance, pA = 0.102917. Exact theta = 0; MC -0.000029 (SE 0.00044); tie probability 0.806.

| rule (H0: theta <= 0) | guaranteed | C1 false deployment | C2 false deployment |
|---|---|---|---|
| win_only_betting | 0.05 | 0.0095 [0.0078, 0.0116] | 0.0103 [0.0085, 0.0125] |
| win_only_normal_mixture | 0.05 | 0.0086 [0.0070, 0.0106] | 0 [0, 0.0004] |
| guarded_betting | 0.05 | 0.0064 [0.0050, 0.0082] | 0.0073 [0.0058, 0.0092] |
| guarded_betting_split | 0.0167 | 0.0019 [0.0012, 0.0030] | 0.0024 [0.0016, 0.0036] |
| guarded normal mixture (both) | 0.05 / 0.0167 | 0 [0, 0.0004] | 0 [0, 0.0004] |
| guarded_repeated_wald | none | 0.3150 [0.3060, 0.3242] | 0.3212 [0.3121, 0.3304] |
| guarded_group_bonferroni_wald | none | 0.0226 [0.0199, 0.0257] | 0.0257 [0.0228, 0.0290] |
| guarded_fixed_wald | none | 0.0520 [0.0478, 0.0565] (not resolved) | 0.0508 [0.0467, 0.0553] (not resolved) |

Equality-in-law contrast (label permutation, 500 pairs = 1,000 executions, 199 permutations, max of success-rate and cost rank-sum statistics): equal-law calibration cell C0 rejects 0.0429 [0.0391, 0.0471] (10,000 replicates); C1 rejects 0.9430 [0.9320, 0.9523]; C2 rejects 1.0000 [0.9981, 1.0000] (success-only component 0.045 in C2, cost-rank component 1.000). The permutation test correctly rejects equality in distribution while the mean-win rules correctly do not deploy: they test different nulls. A rank/permutation rejection is not evidence of positive net benefit, and the weak null theta <= 0 is controlled by the betting/CS rules without any equal-law assumption. With 81% ties the range-based normal-mixture bound becomes more conservative (0 vs 0.0086 win-only), the ternary betting rule does not.

## 3. Deviations from the protocol

1. Code bug fixed after the first full run: E_current_first for win-only rules was computed over all three gates instead of the claimed net-benefit gate. The panel was rerun with identical seeds; a field-by-field diff shows only the win-only E_current_first columns changed, and `permutation_results.csv` is byte-identical. The first run is not retained in the tree. E_current_first is descriptive only.
2. A crash-only smoke test (50 replicates per cell, seed 20260920, scratch directory) was run after the protocol freeze and before the full run; its streams are disjoint from the reported ones.
3. `permutation_results.csv` and `make_figures.py` are additional files not named in the task's deliverable list.
4. No other deviation. `guarded_betting_split`, `win_only_normal_mixture` and cell A6 were added at protocol time (before the freeze), not after results.

## 4. Limitations

Independent pairs with deterministic parameter paths (no adaptive drift, no dependence across pairs, no delayed outcomes); one monitoring schedule; one bet grid and rho; block designs chosen by hand. B3 exercises boundary-tight alternating violators but the finite-sample rules are conservative enough that no rule other than the Wald baselines approached 0.05, so the panel cannot rank the per-gate and split rules on error, only on sample use. Monte Carlo resolution at 10,000 replicates: a true rate of 0 has upper limit 0.0004.

Figures: `results/drift_panel/figures/fig1_design_running_targets.png`, `fig2_error_rates.png`, `fig3_power_sample_use.png`.
