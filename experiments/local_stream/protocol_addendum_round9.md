# Local stream: protocol addendum, Round 9 (POST HOC)

**Status: POST HOC. Written on 2026-09-18 after all 1,182 episodes were run and after the v1 analysis and its
outcomes had been seen. Nothing in this addendum is preregistered.** It responds to the root session's Round 9
audit of PR 8 (`reviews/round9_open_model_evidence_audit.md`). `protocol.md` and `analysis.py` remain the frozen
originals and are not edited. No episode was re-run, no model was called, and no raw evidence file
(`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `run_manifest.json`, `design.*`) was modified. The
v1 outputs are preserved in `results/local_stream/v1_pre_round9/`.

Two independent defects of the v1 inference are repaired: (1) the two-sided betting CS implementation, and
(2) the statement of the target and of the sampling assumptions under which each procedure is valid. A corrected
tail budget does **not** repair (2); they are handled separately.

## 1. Two-sided CS correction (analysis-code deviation)

v1 `src/wincs.py` thresholded `max(K+, K-)` at `1/delta`. The maximum of two one-sided capitals is not a
unit-initial nonnegative supermartingale (for one fair +/-1 observation, `E max(K+, K-) = 1 + mean(stakes) =
1.0637 > 1`), so the union bound gives `2 delta`, not `delta`. v2 uses the hedged capital `(K+ + K-)/2` of
Waudby-Smith and Ramdas (2024), which is a test martingale at the true mean, inverted with a conservative
(outside-iterate) bisection. The corrected file is the independently audited version from the contribution
worktree; `src/test_wincs.py` and `experiments/local_stream/check_two_sided_cs.py` (exact witness + simulated
time-uniform miscoverage, 2,000 streams of length 2,000) are the regression checks. The one-sided e-processes of
the monitor (`winstats.betting_log_e_ternary`) never used the faulty maximum, so `monitor_pass1.csv` and the
crossing at pair 24 are numerically unaffected.

## 2. What is random, and what is fixed

- The **roster** of N = 591 tasks (427 MBPP-sanitized + 164 HumanEval, no selection) is FIXED.
- The **design** draws one uniformly random permutation of the roster and, for the n = 295 disjoint consecutive
  pairs (arrivals 2k-1, 2k), independent orientation coins R_k ~ Bernoulli(1/2) deciding which task of the pair is
  exposed to B in pass 1. One arrival (`mbpp/256`) is unpaired by design and enters E2 only.
- Each **episode** has its own model-sampling randomness (temperature 0.7, per-call seeds derived from frozen
  quantities) and measured latency.

Notation: `Y_A(t)`, `Y_B(t)` = random outcome vector (success, latency, completion tokens) of workflow A/B on task
t; `h` = the frozen hierarchical comparator in {-1, 0, +1} (B minus A); `m(s, t) = E h(Y_B(s), Y_A(t))`, the
expectation over model sampling only, for an ordered pair of distinct roster tasks. `Z_k` = score of pair k;
`D_k` = success difference of pair k, also in {-1, 0, +1}.

## 3. E1 (cross-arrival contrast): two separated readings

### R1. Design-based reading, conditional on the realized pairing (no sampling assumption)

Condition on the realized permutation, i.e. on the unordered pairs `{s_k, t_k}`. Then the orientation coins are
independent across pairs and the episodes of different pairs use different tasks and separate model calls, so
`Z_1, ..., Z_295` are independent with

    mu_k = E[Z_k | pairing] = (1/2) [ m(s_k, t_k) + m(t_k, s_k) ].

The `mu_k` differ from pair to pair (they depend on which two tasks were matched); the sequence is NOT
identically distributed. The R1 target is the running average

    mu_bar_n = (1/n) sum_{k<=n} mu_k,

"the average symmetric prioritized preference for B over the pairs actually formed". Because `Z_k - mu_k` is a
martingale difference with values in an interval of length 2 (conditionally sub-Gaussian with variance proxy 1),
the Hoeffding-type normal-mixture confidence sequence

    nb_hat_n +/- sqrt( (n + rho) log( (n + rho) / (rho alpha^2) ) ) / n,     rho = 100, alpha = 0.05, V_n = n,

(`src/winstats.normal_mixture_radius`; paper Theorem `normal_cs`; Howard, Ramdas, McAuliffe and Sekhon 2021)
covers `mu_bar_n` simultaneously for all n with probability at least 0.95, with **no stationarity, exchangeability
or iid assumption**. If episode noise were serially dependent (for example latency through the thermal state of
the machine), the same statement holds with `mu_k` read as the conditional mean of `Z_k` given the past, i.e.
for the running average of conditional means. rho = 100 is the library default used throughout the paper and was
fixed in `analysis_v2.py` before any R1 number was computed; it was nevertheless chosen after the outcomes of
this experiment were known, which is part of the post hoc status. Because the target `mu_bar_n` moves with n, **no
running intersection** of the intervals is taken. The same construction is applied to `D_k` (target: running
average of the pairs' mean success differences) with the gate threshold -0.03.

Relation to a roster-level target. Under the uniformly random matching every ordered pair of distinct tasks is
equally likely to be the (first, second) arrival of pair k, so

    E_design[ mu_bar_n ] = theta_N := (1 / (N (N - 1))) sum_{s != t} m(s, t),

the finite-roster cross-task preference. The confidence statement above is about `mu_bar_n`, conditional on the
matching, not about `theta_N`: `mu_bar_n` deviates from `theta_N` by the matching's own sampling error, which
this CS does not cover. **No without-replacement (finite-population) martingale or confidence sequence for
`theta_N` is claimed.**

### R2. Superpopulation reading (an ASSUMPTION)

Assume the roster `t_1, ..., t_N` is an iid sample from a task-generating distribution P, and the permutation and
coins are independent of tasks and outcomes. Then:

1. A uniformly random permutation of an iid sample, drawn independently of it, is again an iid sequence from P
   (the joint law of an iid vector is permutation invariant, so conditionally on the permutation the permuted
   vector has the same product law; mix over permutations).
2. Disjoint consecutive pairs of an iid sequence are iid pairs; adding independent orientation coins and
   independent episode noise keeps `(Z_k)` iid. Hence `E[Z_k | F_{k-1}] = E[Z_k] = theta_P`, where
   `theta_P = E_{s,t ~ P iid} (1/2)[m(s,t) + m(t,s)] = E_{s,t} m(s,t)`, exactly.

Under R2 the preregistered one-sided betting e-processes (win, gate, harm), the CORRECTED two-sided betting CS
and the decided-pair win-ratio CS are valid time-uniformly for `theta_P` (respectively for `E D` and for
`WR = P(win)/P(loss)`). Treating a curated benchmark roster (MBPP-sanitized and HumanEval were authored and
filtered, not sampled) as an iid sample from a task distribution is a modelling assumption that **cannot be
verified from the data**; that is why R1 is reported alongside, and why R2 numbers are always labelled with the
assumption.

### Monitor crossings

Observed: harm e-process first read above log 20 at pair 24; win and gate never crossed; no deploy.

- Under R1 the crossings are reported **descriptively**. The one-sided e-processes test the pointwise
  conditional null (for harm: `mu_k >= 0` for every realized pair k). That is a stronger null than
  `mu_bar_n >= 0` or `theta_N >= 0`; rejecting it does not by itself bound `mu_bar_n` or `theta_N`. The R1
  evidence about the sign of `mu_bar_n` is the normal-mixture CS above.
- Under R2 the crossings carry the stated anytime guarantee at alpha = 0.05 for `theta_P`.

Nothing more is claimed. Section 10 of `protocol.md` substituted the pointwise conditional-mean null for a
"superpopulation null" without proof; this addendum supersedes that paragraph and the phrase "independent pairs"
in section 2 and in the v1 report: the pairs are independent **conditional on the matching** (R1) or iid **under
the iid-roster model** (R2), not unconditionally iid draws from a fixed roster.

### Decision label

The preregistered code value `B_harmful` is kept in the data files. In prose it is **"composite harm signal for
B; incumbent A retained"**: an unfavourable result for B on the prespecified COMPOSITE hierarchy, driven by the
latency tier (success counts are equal, 433/591 each). It is not a success-rate harm, not a safety harm, and not a
reverse guarded approval of A; no guardrail was tested in A's favour.

## 4. E2 (same-task shadow contrast)

All N = 591 roster tasks have one A and one B episode. `S_t = h(Y_B(t), Y_A(t))`, `tau_t = E S_t`.

- **Finite-roster target** `theta_roster = (1/N) sum_t tau_t`; the only randomness is model sampling (and
  measured latency), independent across tasks. `S_bar` is unbiased with `Var(S_bar) = (1/N^2) sum_t Var(S_t)`.
  The usual task-level variance estimator is conservative (Neyman-type):
  `E[s^2 / N] = Var(S_bar) + (1 / (N (N - 1))) sum_t (tau_t - tau_bar)^2 >= Var(S_bar)`,
  because between-task variation of the means inflates `s^2` while it does not contribute to the sampling error of
  a census of the roster. The t interval is therefore (asymptotically, by the Lindeberg CLT for independent
  bounded scores) conservative for `theta_roster`. An assumption-free fixed-n Hoeffding interval
  (`+/- sqrt(2 log(2/alpha) / N)`) is reported next to it; it is not time-uniform and is not needed to be, since
  E2 is analysed once at the end.
- **Superpopulation target** `theta_task,P = E_{t~P} tau_t` under the iid-roster model: the same interval is the
  conventional task-clustered interval (one cluster per task).

Both statements are kept. The pass of exposure (pass 1 or pass 2) is assigned by the design; with a sequential
single-request server there is no concurrency between arms, but period effects on latency between pass 1 and
pass 2 are not separately identified and are part of the episode noise.

Pass-1 component contrasts are reported from **pair-level differences** `d_k = X_{B,k} - X_{A,k}` (n = 295;
conservative for the running average of means under R1, iid under R2). The v1 "independent-arm Welch" intervals
are kept in the v1 files only: the two arms of pass 1 are a random split of a fixed roster, not independent
samples.

## 5. Guardrail, E1 versus E2, and resources (wording corrections)

- Same-task success difference: 0.000, t interval lower end -0.029748506, which clears the -0.03 margin by
  0.00025 under that single approximation. This is **not a robust non-inferiority result**. The online gate did
  not cross, and the online success intervals reach about -0.08 (R2, corrected) and -0.13 (R1).
- The E1 minus E2 difference (about 0.185) is **descriptive**: different targets, shared episodes, different unit
  counts and exposure passes, and no joint uncertainty is claimed for the difference.
- "Frozen before any model call" is corrected to **"frozen before any design-task outcome"**: smoke checks and
  the 6-task out-of-design timing pilot called the model earlier and are disclosed. The run and every episode
  recorded harness commit `526dff7b...`; the freeze commit named in protocol section 16 is `d9793d5...`; per the
  audit's Git reconciliation all 13 recorded file hashes match `526dff7b`, and at `d9793d5` only `protocol.md`
  differs (the other 12 files are identical). Both commits precede the first episode. This is a timestamped
  internal freeze, not an external registration.
- Resources are reported per arm as prompt tokens, completion tokens, total tokens, model calls and latency.
  Completion tokens are generation counts, not dollars, energy or total compute. `n_executions` includes the one
  hidden-verifier execution per episode, which `latency_s` excludes.
- The negative result for H1 is retained as is. No new variants, no reruns.

## 6. Files

`analysis_v2.py`, `make_figures_v2.py`, `make_report_v2.py`, `check_two_sided_cs.py`, `verify_data_manifest.py`,
`make_release_anon.py`, `run_v2_all.py` (aggregate command) in `experiments/local_stream/`; outputs
`summary_v2.json`, `decision_rules_v2.csv`, `sensitivity_v2.csv`, `running_cs_v2.csv`, `resources_v2.csv`,
`two_sided_cs_check.json`, `report_v2.md`, `figures_v2/`, `data_manifest.json`, `release_anon/`,
`analysis_v2_manifest.json` in `results/local_stream/`.
