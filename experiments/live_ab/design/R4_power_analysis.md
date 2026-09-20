# R4 — Pilot-based power analysis for the prospective live A/B trial (CPU only)

Reader R4, session 60, 2026-09-19. No model server was started, no LLM/API call, no download, no git state change,
no repository file touched. Everything is in
`<SCRATCH>`:

| File | Content |
|---|---|
| `power_sim.py` | simulator (parts `T1`, `T2`, `T4`, `sens`, `long`, `merge`); each part ran < 5 min, < 2.1 GB RSS |
| `power_results.csv` | 1,664 rows = every (trial x design x resampling cell x success-shift x method x alpha scheme x delta x min_n) |
| `power_required_horizon.csv` | T1 long-horizon run (8,000 pairs, 2,000 reps): pairs needed for 50/80/90% power |
| `power_T3_analytic.csv` | analytic planning table for the unknown-outcome model swap (T3) |
| `power_summary.json` | input hashes, pilot facts, plug-in population targets, oracle growth rates, seed |
| `make_report_tables.py`, `report_tables.md` | table rendering only |

## 0. Bottom line

1. **A 3-point or 5-point success guardrail cannot be certified on 591 or on 1,138 tasks.** With cross-task pairs at
   73% success the success-difference score is non-zero in 39% of pairs (variance 0.39). Under the most favourable
   assumption (true success difference exactly 0) the probability that the live guarded-deploy rule fires in T1 is
   2-3% (delta=0.03) and 6-8% (delta=0.05) on 591 tasks, and 6% / 17% on 1,138 tasks, with no alpha split; with the
   split the root requires for a fixed-roster stream it is 1% / 3% and 2% / 9%. 80% power needs about **6,100-7,500
   pairs (delta=0.03)** and **2,300-2,700 pairs (delta=0.05)**, i.e. 12,000-15,000 and 4,500-5,500 single-exposure tasks.
2. **Feasible margins:** delta=0.15 on 591 tasks (betting gates: 76-88% power, deploy at pair ~140-170 of 295) and
   delta=0.10 only on 1,138 tasks (67-79%). delta=0.10 on 591 tasks is a coin flip at best (25-42%).
   With the root's *primary* construction (normal-mixture band, rho=100) nothing is feasible on 591 tasks
   (delta=0.15: 5-23%) and only delta=0.15 on 1,138 tasks (64-84%).
3. **These are optimistic.** If the cheap candidate is truly 2-3 points worse (well inside the pilot's uncertainty,
   paired SE 0.015), power at delta=0.15 / 591 tasks falls from 76% to 56% / 46% (split) and at delta=0.10 / 1,138 tasks
   from 67% to 37% / 25%.
4. **The harm direction is cheap and certain:** in T2 the harm gate fires in 100% of replicates, median pair 34-42
   (betting) or 64-79 (normal mixture), i.e. after ~70-160 of 591 arrivals; live stopping then avoids 84-93%
   (betting) / 72-88% (normal mixture) of the candidate's scheduled exposures and 53-59% / 46-56% of total episode
   latency. This is where a *measured* operational saving can realistically be demonstrated.
5. **A/A (T4):** false-decision rates are far below nominal for every scheme (<= 2.0% any decision, <= 0.8% false
   deploy, <= 1.2% false harm, at nominal 5% per direction); a single T4 run will almost surely end with "no decision".
6. **min_n (10 vs 20) is immaterial** (max |difference| in P(deploy) 0.0007; harm median shifts by <= 1 pair). Keep 20.
7. **One coin per disjoint arrival pair (root design) rather than one coin per arrival**: it gives exactly 295 / 569
   pairs; per-arrival coins give on average 285.8 / 555.5 pairs (3% of arrivals are never paired), cost 1-2 points of
   power, and are not covered by the root's `thm:pair_id`.

**Recommendation.** Prespecify the betting gates (`betting_log_e_ternary`, the 40-stake grid as shipped) with the
Bonferroni split alpha/3 for win / guard / harm (threshold 60 each) on the 1,138-task roster, guardrail margin
**delta = 0.10**, min_n = 20, pair-orientation coins, completed-enrollment-prefix monitoring. Expect, honestly:
T2 harm stop near pair 40 with certainty; T1 net-benefit gate crossing near pair 40 with certainty but guarded
deployment only with probability ~0.65 if the two workflows really have equal success (0.25-0.37 if the candidate is
2-3 points worse), at median pair ~340, saving ~28% of incumbent exposures / ~18% of latency in expectation;
T4 no decision. If the root requires the normal-mixture band as primary, state in the protocol that the primary
guardrail is expected NOT to be certified for delta <= 0.10 and declare delta = 0.15 (power ~0.64-0.72 on 1,138 tasks).
A margin of 0.03 or 0.05 should be declared in advance as "not certifiable at this sample size" rather than tested and
reported as a failure. On the 591-task roster alone the only honest prespecification is delta = 0.15.

## 1. What was simulated

**Pilot.** `results/local_stream/episodes_flat.csv` (sha256 `1237b82f...`; `episodes.jsonl` sha256 `95179f93...` equals the
root's `RAW_SHA`). 591 tasks, one episode per task and arm. single_shot 433/591, self_test_repair 433/591; same-task
discordance 40 vs 40; mean latency 2.80 s vs 12.48 s; mean completion tokens 70 vs 313.

**Library functions used read-only by import from `src/winstats.py` (sha256 `56955ce0...`):**
`Tier`, `compare` (hierarchical pair score), `betting_log_e_ternary` (fixed-grid betting e-process; `thm:betting`,
`prop:bet_running`), `normal_mixture_radius` (two-sided normal-mixture CS, `thm:normal_cs`). Nothing in the library was
re-implemented. The library has no trial simulator, no guarded first-crossing routine and no timing model; those three
pieces are implemented in `power_sim.py` in the simplest faithful way:
- pair score exactly as the root's `experiments/build_open_coding_results.py::score`: tiers success (no tolerance) >
  latency_s (10% relative) > completion_tokens (10% relative), lower tiers eligible only when both episodes succeeded.
  **Check:** the script reproduces the root's E1 counts on the pilot pairs (69 wins / 18 ties / 208 losses) before
  simulating, and aborts otherwise.
- e-processes exactly as the pilot's frozen monitor (`experiments/local_stream/run_stream.py:89-91`):
  win `betting_log_e_ternary(pos,neg,n,0)`, harm `betting_log_e_ternary(neg,pos,n,0)`, guard
  `betting_log_e_ternary(qpos,qneg,n,-delta)` on the success-difference score.
- guarded deploy = first look n >= min_n at which win AND guard are both over their thresholds **at the same current
  look** (the paper's reported implementation, `theory.tex` eq. deploy_rule; no retained crossings). Harm stop = first
  look at which the harm process crosses. Ties between the two cannot occur in practice; harm has precedence in code.
  The retained-evidence variant is reported in column `p_deploy_retained_variant` (it differs from the current-look rule by at most 0.0033 in any row, and by < 0.0002 in the pilot-plug-in T1 cells).
- second monitor family `normal_mixture`: lower bound `mean - normal_mixture_radius(n, a, rho=100) > c` for win/guard,
  upper bound `< 0` for harm (the root's retained coding analysis made prospective).

**Plug-in population values (all ordered pairs of different tasks).** T1 (candidate single_shot vs incumbent
self_test_repair): P(win)=0.709, P(tie)=0.079, P(loss)=0.212, net benefit +0.497, success difference 0.000,
P(d=+1)=P(d=-1)=0.196. T2 is the mirror image (NB -0.497). T4 (A/A): P(win)=P(loss)=0.443, tie 0.114, NB 0.

**Trial mechanics per replicate.** Random arrival order; physical fair coin; one arm per task; outcome = pilot outcome
of that task under the assigned arm.
- Resampling cells: `perm591` (the 591 tasks, each once, random order — the literal new trial on the pilot roster,
  horizon 295 pairs), `boot591` (591 draws with replacement), `boot1138` (1,138 draws with replacement, horizon 569
  pairs, mimicking MBPP-full 974 + HumanEval 164).
- Designs: `pair_coin` = the root's randomized disjoint-pair design (consecutive arrivals 2i-1, 2i; one coin per pair
  decides which position gets the candidate; an odd last arrival is unpaired); `arrival_coin` = the coordinator's
  wording (one coin per arrival; pair k = k-th candidate arrival with k-th incumbent arrival; pairs available =
  min(nA, nB), a random number).
- Live stopping and savings: 2 workers; arrival i starts when a worker frees up, runs for its pilot latency; the monitor
  looks at the completed enrollment prefix, so the decision time is the moment all episodes of pairs 1..tau have
  finished; every arrival not yet started at that moment runs under the decided arm (in-flight episodes finish under
  their assigned arm and count as exposed). "Saved" = arrivals whose (counterfactual) coin would have sent them to the
  inferior arm, signed negative after a wrong decision; averaged over ALL replicates including those with no decision.
  Inferior arm: T1 incumbent (self_test_repair, same success, 4.5x slower), T2 candidate; T4 none.
- Alpha schemes (a_win, a_guard, a_harm), alpha = 0.05:
  `nosplit_iut` (.05,.05,.05) = paper `thm:iut`, valid only for stationary conditional means, per-direction 5%
  (this was the pilot's rule); `deploy_bonf2` (.025,.025,.05) = paper `thm:drift_gate` for the two deploy gates;
  `twosided_equal` (.025,.025,.025) = equal split between the deploy direction and the harm direction (for the
  normal-mixture family this is one two-sided NB band at .025 plus a guard band at .025, joint 5%);
  `bonf3` (.05/3 each; thresholds 60) = Bonferroni over the three monitored processes, the only scheme whose
  trial-level error (any false decision) is <= 5% for running-average targets on a fixed roster.
- Monte Carlo: 20,000 replicates per main cell (max MC SE 0.0035), 10,000 per sensitivity cell (max SE 0.005),
  2,000 for the 8,000-pair run. Seeds: `SeedSequence([20260919, trial, design, cell, shift])`.

## 2. T1 — cheap candidate (incumbent self_test_repair, candidate single_shot)

The net-benefit gate crossed in 100% of replicates for every method/scheme; the harm gate never fired (0 of 20,000).
Whether the trial "deploys" is therefore decided entirely by the success guardrail.

**P(guarded deploy), pair_coin design, min_n = 20**

| method | scheme | delta | 591 tasks, permuted roster (295 pairs) | 591 bootstrap (295) | 1,138 bootstrap (569) |
|---|---|---|---|---|---|
| betting | nosplit_iut | 0.03 | 0.022 | 0.030 | 0.056 |
| betting | nosplit_iut | 0.05 | 0.061 | 0.075 | 0.169 |
| betting | nosplit_iut | 0.10 | 0.407 | 0.418 | 0.793 |
| betting | nosplit_iut | 0.15 | 0.878 | 0.859 | 0.996 |
| betting | deploy_bonf2 (= twosided_equal in T1) | 0.03 | 0.010 | 0.016 | 0.032 |
| betting | deploy_bonf2 | 0.05 | 0.035 | 0.044 | 0.112 |
| betting | deploy_bonf2 | 0.10 | 0.303 | 0.322 | 0.715 |
| betting | deploy_bonf2 | 0.15 | 0.817 | 0.796 | 0.993 |
| betting | bonf3 | 0.03 | 0.007 | 0.011 | 0.022 |
| betting | bonf3 | 0.05 | 0.024 | 0.033 | 0.089 |
| betting | bonf3 | 0.10 | 0.255 | 0.273 | 0.667 |
| betting | bonf3 | 0.15 | 0.775 | 0.759 | 0.989 |
| normal_mixture | nosplit_iut | 0.03 / 0.05 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.003 |
| normal_mixture | nosplit_iut | 0.10 | 0.011 | 0.019 | 0.193 |
| normal_mixture | nosplit_iut | 0.15 | 0.207 | 0.228 | 0.842 |
| normal_mixture | deploy_bonf2 (= twosided_equal) | 0.10 | 0.003 | 0.006 | 0.099 |
| normal_mixture | deploy_bonf2 | 0.15 | 0.091 | 0.112 | 0.722 |
| normal_mixture | bonf3 | 0.10 | 0.001 | 0.003 | 0.063 |
| normal_mixture | bonf3 | 0.15 | 0.055 | 0.070 | 0.644 |

**Stopping pair index and expected savings, betting gates (quartiles are conditional on stopping; "censored median"
treats no-decision as beyond the horizon, "-" = more than half of the trials never decide)**

| scheme | delta | cell | P(deploy) | Q1 / median / Q3 of stop pair | censored median | arrivals already started at decision (median) | E[fraction of all arrivals saved from the slow arm] | E[fraction of incumbent exposures avoided] | E[fraction of total latency saved] |
|---|---|---|---|---|---|---|---|---|---|
| nosplit_iut | 0.10 | perm591 | 0.407 | 114 / 180 / 239 | - | 361 | 0.083 | 0.166 | 0.105 |
| nosplit_iut | 0.15 | perm591 | 0.878 | 89 / 143 / 202 | 159 | 289 | 0.219 | 0.438 | 0.277 |
| bonf3 | 0.10 | perm591 | 0.255 | 135 / 197 / 250 | - | 395 | 0.046 | 0.091 | 0.058 |
| bonf3 | 0.15 | perm591 | 0.775 | 115 / 171 / 226 | 202 | 343 | 0.164 | 0.328 | 0.208 |
| nosplit_iut | 0.10 | boot1138 | 0.793 | 172 / 287 / 408 | 348 | 577 | 0.193 | 0.386 | 0.245 |
| nosplit_iut | 0.15 | boot1138 | 0.996 | 96 / 159 / 238 | 159 | 320 | 0.343 | 0.686 | 0.434 |
| bonf3 | 0.10 | boot1138 | 0.667 | 220 / 338 / 445 | 445 | 678 | 0.140 | 0.279 | 0.177 |
| bonf3 | 0.15 | boot1138 | 0.989 | 130 / 202 / 289 | 204 | 407 | 0.305 | 0.609 | 0.386 |

For delta = 0.03 / 0.05 the expected saving is below 2% / 5% of incumbent exposures in every cell (rows in the CSV),
because the trial almost never decides. The maximum possible value of "fraction of all arrivals saved" is 0.5.

**Pairs needed (T1, pair_coin, bootstrap stream of 8,000 pairs, betting, min_n=20, 2,000 reps)**

| scheme | delta | pairs for 50% power | 80% | 90% | oracle lower bound log(1/a)/g* |
|---|---|---|---|---|---|
| nosplit_iut | 0.03 | 3,659 | 6,136 | 7,735 | 2,610 |
| nosplit_iut | 0.05 | 1,298 | 2,274 | 2,864 | 940 |
| nosplit_iut | 0.10 | 337 | 567 | 705 | 236 |
| nosplit_iut | 0.15 | 158 | 259 | 322 | 106 |
| deploy_bonf2 | 0.03 | 4,302 | 7,091 | > 8,000 | 3,213 |
| deploy_bonf2 | 0.05 | 1,548 | 2,591 | 3,190 | 1,158 |
| deploy_bonf2 | 0.10 | 399 | 647 | 797 | 291 |
| deploy_bonf2 | 0.15 | 188 | 295 | 367 | 130 |
| bonf3 | 0.03 | 4,770 | 7,537 | > 8,000 | 3,567 |
| bonf3 | 0.05 | 1,706 | 2,740 | 3,360 | 1,285 |
| bonf3 | 0.10 | 436 | 702 | 847 | 323 |
| bonf3 | 0.15 | 202 | 318 | 394 | 145 |

Rule of thumb from these runs: median crossing ~ 1.4 x oracle, 80% power ~ 2.4 x oracle, where oracle =
log(1/alpha_gate) / max_lambda E log(1 + lambda (d + delta)). Number of tasks = 2 x pairs. The normal-mixture band needs
radius(n) < delta: n = 922 pairs for delta 0.10 and 12,094 pairs for delta 0.03 at alpha .05 (R1's table), before any noise.

**Sensitivity of T1 to the true success difference (bootstrap cells, betting, min_n=20).** Candidate successes/failures
were flipped independently so that the candidate's true success rate moves by the stated amount; "predictive" draws the
shift per replicate from N(0, 0.0151^2), the pilot's paired standard error.

| scheme | cell | delta | cand. -0.03 | cand. -0.02 | pilot (0) | predictive | cand. +0.02 |
|---|---|---|---|---|---|---|---|
| nosplit_iut | 591 | 0.10 | 0.165 | 0.237 | 0.418 | 0.417 | 0.630 |
| nosplit_iut | 591 | 0.15 | 0.606 | 0.704 | 0.859 | 0.837 | 0.949 |
| nosplit_iut | 1138 | 0.05 | 0.028 | 0.058 | 0.169 | 0.209 | 0.405 |
| nosplit_iut | 1138 | 0.10 | 0.383 | 0.521 | 0.793 | 0.761 | 0.947 |
| nosplit_iut | 1138 | 0.15 | 0.935 | 0.968 | 0.996 | 0.990 | 1.000 |
| bonf3 | 591 | 0.10 | 0.086 | 0.133 | 0.273 | 0.284 | 0.474 |
| bonf3 | 591 | 0.15 | 0.456 | 0.561 | 0.759 | 0.735 | 0.895 |
| bonf3 | 1138 | 0.05 | 0.011 | 0.027 | 0.089 | 0.122 | 0.270 |
| bonf3 | 1138 | 0.10 | 0.250 | 0.374 | 0.667 | 0.650 | 0.886 |
| bonf3 | 1138 | 0.15 | 0.873 | 0.928 | 0.989 | 0.978 | 0.999 |

At shift -0.03 and delta = 0.03 the guardrail null is true (boundary); the simulated false-deploy rate is 0.009
(nosplit, 1,138) / 0.002 (bonf3), below the nominal level, as it must be.

## 3. T2 — harmful candidate (incumbent single_shot, candidate self_test_repair)

Deploy never fired (0 of 20,000 in every cell). Harm stop fired in 100% of replicates in every cell, scheme and method.
Rows do not depend on delta.

| method | scheme | min_n | Q1 / median / Q3 of harm-stop pair | arrivals started at decision (median) | E[frac. of candidate exposures avoided] 591 / 1,138 | E[frac. of total latency saved] 591 / 1,138 |
|---|---|---|---|---|---|---|
| betting | nosplit_iut (threshold 20) | 10 | 22 / 34 / 48 | 69 | 0.872 / 0.933 | 0.552 / 0.591 |
| betting | nosplit_iut | 20 | 24 / 34-35 / 48-49 | 71 | 0.866 / 0.930 | 0.548 / 0.589 |
| betting | twosided_equal (40) | 20 | 27 / 40 / 55 | 81 | 0.849 / 0.921 | 0.538 / 0.584 |
| betting | bonf3 (60) | 20 | 29 / 42 / 59 | 87 | 0.840 / 0.916 | 0.532 / 0.580 |
| normal_mixture | nosplit_iut | any | 55 / 64 / 76 | 131 | 0.770 / 0.880 | 0.488 / 0.558 |
| normal_mixture | twosided_equal | any | 62 / 74 / 86 | 149 | 0.741 / 0.865 | 0.469 / 0.548 |
| normal_mixture | bonf3 | any | 66 / 78 / 92 | 159 | 0.724 / 0.856 | 0.459 / 0.542 |

Consistency with the delivered pilot: the pilot's own betting harm crossing was at pair 24 (simulated Q1 = 24) and the
root's retained normal-mixture upper endpoint went below zero at pair 60 (simulated Q1-median 55-64). Shifting the
candidate's true success by -0.03 ... +0.02 moves the median harm-stop pair by at most 2 (41-44, bonf3) — the harm is
driven by the latency tier among the ~54% of pairs where both succeed, not by success. **Wording caution for the
paper:** in T2 "harm" means negative hierarchical net benefit (cost tier), not a lower success rate.

## 4. T4 — A/A negative control (single_shot vs single_shot)

Maximum over the three resampling cells, min_n = 10 (min_n = 20 is lower by <= 0.002):

| method | scheme | nominal bound on any false decision | P(false deploy), delta 0.03 / 0.15 | P(false harm stop) | P(any decision), delta 0.15 |
|---|---|---|---|---|---|
| betting | nosplit_iut | 0.10 | 0.004 / 0.008 | 0.012 | 0.020 |
| betting | deploy_bonf2 | 0.10 | 0.002 / 0.004 | 0.012 | 0.016 |
| betting | twosided_equal | 0.05 | 0.002 / 0.004 | 0.005 | 0.009 |
| betting | bonf3 | 0.05 | 0.001 / 0.003 | 0.004 | 0.006 |
| normal_mixture | nosplit_iut | 0.10 | 0.000 / 0.004 | 0.003 | 0.007 |
| normal_mixture | twosided_equal | 0.05 | 0.000 / 0.002 | 0.001 | 0.003 |
| normal_mixture | bonf3 | 0.05 | 0.000 / 0.001 | 0.001 | 0.002 |

The arrival_coin design gives the same picture (max any-decision 0.019). The fixed 40-stake mixture is conservative by
a factor of 4-5 at NB = 0 with 11% ties. Note that in A/A the guardrail alternative is TRUE (difference 0 > -delta), so
the guard gate alone crosses as often as in T1 (e.g. 0.76-0.86 at delta 0.15 on 591 tasks); false deployment is
controlled only by the net-benefit gate. A single A/A run cannot "verify" a 5% error rate — it is a sanity check of
the plumbing; the expected observation is "no crossing in 295/569 pairs" with probability >= 0.98.

## 5. Design findings that the protocol should absorb

1. **Coin unit.** `arrival_coin` leaves on average 9.2 of 295 (13.5 of 569) potential pairs unformed, the pair count is
   random (minimum over all replicates 243 / 499), and pair composition depends on the coins, which the root's identification theorem
   does not cover. P(deploy) is 0.5-2 points lower than under `pair_coin` (e.g. bonf3, delta 0.15, permuted roster: 0.751 vs
   0.775). Use one OS-entropy coin per consecutive arrival pair, drawn and logged when the first member of the pair
   arrives; this is still one physical coin, one arm per task, and yields exactly 295 / 569 pairs.
2. **Horizon.** 295 pairs = the 591-task roster; 569 pairs = 1,138 tasks. Doubling the roster is what moves delta = 0.10 from
   "coin flip" to "probable". It does nothing for delta <= 0.05.
3. **Concurrency overhead is small.** With 2 workers and prefix-ordered monitoring the number of arrivals already
   started at the decision is about 2 tau + 2..5 (e.g. harm median pair 34 -> 69-71 arrivals started).
4. **Scheme cost.** Going from no split to alpha/3 costs 10-15 points of power at the feasible margins and 7-8 pairs of
   median delay in the harm direction; it buys a trial-level 5% statement that does not need stationarity. Given the
   Round 9 objection to pointwise conditional nulls on a permuted fixed roster, `bonf3` (or `twosided_equal` if the root
   accepts stationarity by design) is the scheme that can enter the paper without re-analysis.
5. **Variance lever not simulated (needs a third run to calibrate):** prespecified outcome-blind stratified pairing by
   the PILOT outcome of the task. Using the other arm as a proxy for a fresh run, fresh success is about 0.91 for
   tasks solved in the pilot and 0.25 for unsolved ones, so within-stratum discordance would be about 0.22 instead of
   0.39 and the required pairs would shrink by roughly 0.57 (delta = 0.10: ~325 instead of 567 pairs for 80% power,
   no split). This applies only to the 591 pilot tasks, uses pilot outcomes as a baseline covariate, and changes the
   estimand to a stratum-weighted one; it must be cleared with the root before freezing. Benchmark-only
   stratification (HumanEval/MBPP) is useless (discordance 0.38 vs 0.39).
6. **T3 (model swap, unknown outcome) planning table** (analytic; ties 8%, discordance 0.39; 80% column = 2.4 x
   oracle as calibrated above; Delta = true success advantage of the candidate, so the guard sees delta + Delta):

| gate | effect size | oracle pairs a=.05 | oracle pairs a=.05/3 | ~80% power a=.05 | ~80% power a=.05/3 |
|---|---|---|---|---|---|
| win NB>0 | NB 0.05 | 2,204 | 3,012 | 5,289 | 7,229 |
| win NB>0 | NB 0.10 | 550 | 752 | 1,320 | 1,804 |
| win NB>0 | NB 0.15 | 244 | 333 | 585 | 800 |
| win NB>0 | NB 0.20 | 137 | 187 | 328 | 448 |
| win NB>0 | NB 0.30 | 60 | 82 | 144 | 197 |
| win NB>0 | NB 0.50 | 21 | 29 | 50 | 68 |
| guard | delta+Delta 0.05 | 941 | 1,286 | 2,259 | 3,087 |
| guard | delta+Delta 0.08 | 369 | 504 | 885 | 1,209 |
| guard | delta+Delta 0.10 | 236 | 323 | 567 | 775 |
| guard | delta+Delta 0.13 | 140 | 192 | 337 | 461 |
| guard | delta+Delta 0.15 | 106 | 145 | 254 | 347 |
| guard | delta+Delta 0.20 | 60 | 82 | 144 | 197 |

   With 569 pairs T3 has ~80% power for |NB| >= ~0.15 (no split) or ~0.18 (alpha/3) and can certify delta = 0.10 only if the new model is at least as
   successful as the incumbent. A model swap that changes success by 5+ points shows up in the NB gate (success is
   the top tier), not in the guardrail.

## 6. Limitations — read before quoting any number

- **This is a plug-in simulation from pilot data of the same tasks; it is optimistic about between-run variability.**
  Each (task, arm) has one pilot run at temperature 0.7. The simulation treats that outcome as the outcome the new trial
  would see, so (a) the true success difference is fixed at exactly 0 (pilot: 433 vs 433, paired SE 0.015; the
  "predictive" and shift columns are the honest range), (b) per-task stochasticity of fresh runs, new seeds, a
  different server build or sampler path, thermal state and the GPU contention of two concurrent workers are not
  modelled, (c) the 547 tasks that would extend the roster to 1,138 are represented by resampled pilot tasks, although
  MBPP-full tasks outside the sanitized subset may be harder or noisier, (d) latencies are pilot latencies measured
  with one request at a time; with two concurrent requests both arms slow down and the 10% latency tolerance may bind
  differently (the 4.5x gap makes the sign robust, the tie rate less so).
- The A/A cell reuses the single pilot run of single_shot for both arms (different tasks within a pair, so pairs are
  still independent draws); it cannot show run-to-run drift of one arm.
- Savings are computed under the completed-prefix monitor with 2 workers and no queueing of the monitor itself; the
  root's partial-information enclosures (`asynchronous.tex`) could decide slightly earlier and are not simulated.
  Savings are expectations over all replicates, including no-decision runs (saving 0) and wrong decisions (negative);
  they are simulated, not measured, and must not be reported as operational savings.
- The power numbers are specific to the shipped 40-stake grid (`geomspace(1e-4, .99/(1+c), 40)`, uniform weights);
  changing the grid after seeing these numbers would be a design choice made on pilot data (legitimate if frozen before
  the first live episode, but it must be declared as such).
- No claim about T3 is simulated; its table is analytic.
