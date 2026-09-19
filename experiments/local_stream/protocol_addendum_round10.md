# Local stream: protocol addendum, Round 10 (POST HOC)

**Status: POST HOC. Written on 2026-09-19, after all 1,182 episodes, the v1 analysis, the Round 9 (v2) re-analysis
and their outcomes had been seen. Nothing in this addendum is preregistered.** It responds to the root session's
Round 10 audit of PR 8 (findings 1, 2, 4, 5, 6 and its section 3). It **supersedes the conflicting sentences of
`protocol_addendum_round9.md`**, which is not edited and remains in the record; section 6 below lists the
superseded sentences. `protocol.md`, `analysis.py` and the harness remain the frozen originals; `analysis_v2.py` is
unchanged. No episode was re-run, no model was called, no generated program was executed, and no raw evidence
file (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `run_manifest.json`, `design.*`) was modified.
The Round 9 outputs are preserved in `results/local_stream/v2_pre_round10/`, the v1 outputs in
`results/local_stream/v1_pre_round9/`. All point estimates are unchanged.

Notation is that of the Round 9 addendum: `Z_k` in {-1, 0, +1} is the hierarchical score of pass-1 pair k (B minus
A), `D_k` its success difference, `S_t = h(Y_B(t), Y_A(t))` the same-task score of roster task t.

## 1. R1: the target is a running conditional mean

**Filtration.** `F_k = sigma( design information that is independent of future outcomes, revealed pair data up to
pair k )`. "Design information" is the frozen arrival order, pairing and orientation coins (drawn from the seed
before any design-task outcome existed); "revealed pair data" are the episode records of pairs 1..k. `F_0`
contains no outcome.

**Target.** `mu_k = E[ Z_k | F_(k-1) ]`, and the R1 target at time n is the running conditional mean

    mu_bar_n = (1/n) sum_{k<=n} mu_k .

**Statement.** `Z_k` lies in [-1, 1], so `Z_k - mu_k` is a martingale difference with conditional range 2
(conditionally sub-Gaussian with variance proxy 1). The normal-mixture boundary with `V_n = n`, `rho = 100`,
two-sided `alpha = 0.05` therefore covers `mu_bar_n` simultaneously over n with probability at least 0.95. Nothing
else is used: no independence of pairs, no stationarity, no iid sampling. Because the target can move with n (and
with the history), **no running intersection** is taken. The same construction, separately, covers the running
conditional mean of `D_k`.

**What is NOT part of the R1 guarantee.**

- The interpretation `mu_k = [ m(s_k, t_k) + m(t_k, s_k) ] / 2` and the identity `E_design[ mu_bar ] = theta_N`
  hold **only under an additional orientation-independent, history-independent stable episode-law model**:
  conditional on the pairing and the past, the coin is fair and each future episode follows a fixed task- and
  workflow-specific law. The design alone does not establish this; thermal state, execution order and caching can
  affect latency (tier 2 of the hierarchy). The Round 9 sentence that different tasks and separate model calls
  *therefore* make the pair scores independent is withdrawn. With history dependence the time-invariant `m(s,t)`
  formula and its link to a fixed roster target `theta_N` are not retained. No statement about `theta_N` is made.
- The two separate 95% intervals (NB and success difference) are **not a joint 95% region**.
- `rho = 100` is the library default, but it was fixed for this analysis **after the outcomes had been seen**.
  Fixing it before computing these particular intervals does not preregister them: R1 is a post hoc analysis of a
  prespecified observed stream, not a prospectively chosen decision rule.
- Report tables and captions use the conditional-mean wording ("running conditional mean of the pair scores given
  the stated filtration"), not "design-based with no assumption" and not "average over the pairs actually formed".

Numbers (unchanged from v2): NB -0.4712, CS [-0.6540, -0.2883], upper bound first below 0 at pair 60;
success-difference CS [-0.1320, 0.2337]; the gate is not established.

## 2. R2: unconditional model-based inference over hypothetical iid rosters

**Model.** The roster is an iid sample from a task distribution P; the permutation and coins are independent of
tasks and outcomes; episodes follow **independent, stable** task- and workflow-specific laws.

**Filtration.** `F` = past revealed pair data plus design information that is independent of future task values.
It is **not** the entire realized roster: if `F_0` contained the realized task vector, `E[Z_k | F_(k-1)] = theta_P`
would not follow from the iid-roster argument. The coarse filtration is legitimate here because the frozen
monitoring calculations use only past pair scores.

**Statement.** Under this model `E[Z_k | F_(k-1)] = theta_P`, and the corrected hedged betting CS, the decided-pair
win-ratio CS and the one-sided e-processes are time-uniformly valid for `theta_P` (respectively `E D`, WR). This is
**unconditional model-based inference over hypothetical iid rosters with independent stable episode laws; it is
not a guarantee conditional on the curated benchmark** (MBPP-sanitized and HumanEval were authored and filtered,
not sampled), and the fixed benchmark counts and public curation do not establish the model.

Numbers (v2; unchanged by the endpoint repair of section 4 to within 1e-8): NB CS [-0.6281, -0.2880], first below
0 at pair 42 and stays below from pair 50; success-difference CS [-0.0786, 0.1794]; decided-pair WR CS
[0.2010, 0.5299].

## 3. Monitor crossings

Unchanged: harm e-process first read above log 20 at pair 24; win and gate never crossed; nothing was stopped or
deployed. Under R1 the fixed-stake e-process crossings stay **descriptive** (they test the pointwise conditional
null `mu_k >= 0` for every k). The root session's separate running-conditional-mean theorem for fixed nonnegative
stake mixtures is **not imported** here. Under the R2 model the crossings carry the anytime guarantee for
`theta_P`. Label: "composite harm signal for B; incumbent A retained" (not a success-rate or safety harm and not a
reverse guarded approval of A).

## 4. E2 (same-task shadow contrast): model-based task-level intervals and orientation-pair clusters

**Withdrawn.** The Round 9 statements that "the only randomness is model sampling", that the task-level t
interval is conservative for the finite-roster target by the Lindeberg CLT for bounded scores, and that the
task-level Hoeffding interval needs no assumption. The randomized pass assignment is part of the randomness, and
the two tasks of a design pair share one AB/BA orientation coin and complementary pass positions; all episodes
share one machine.

**Counterexample (Round 10 audit, finding 1).** Take a pair of tasks. Both workflows are identical within a task
and period. Task 1 succeeds in pass 1 and fails in pass 2; task 2 fails in pass 1 and succeeds in pass 2. Under
one fair AB/BA orientation the two same-task success scores are (1, 1); under the other they are (-1, -1). Each
task's mean score is zero, but `Var((S_1 + S_2)/2) = 1` while `s^2/2 = 0` in both realizations. No model noise or
shared stochastic call is needed. Positive covariance within the orientation pair defeats the variance identity
for the actual design; in general `E[s^2/N]` acquires the extra term `-2 sum_{i<j} Cov(S_i, S_j) / (N(N-1))`.

**Boundedness is not a CLT (finding 2).** For independent `S_t ~ Bernoulli(1/N)` the total variance stays bounded;
at N = 591 all scores are 0 with probability 0.367568 and the zero-width t interval excludes the mean 1/591. A
Lindeberg / variance-growth condition (and a well-behaved variance estimator) is required; latency and token
component differences additionally need finite-moment CLT conditions.

**Kept, relabelled MODEL-BASED.** The task-level t interval and the task-level Hoeffding interval
(`+/- sqrt(2 log(2/alpha)/N)` = 0.11173) are valid under *independent task scores with stable task-specific
episode laws and no relevant pass/period effects*; the t interval additionally under a Lindeberg / variance-growth
regularity condition, and it is approximate. Under that model the identity
`E[s^2/N] = Var(S_bar) + sum_t (tau_t - tau_bar)^2 / (N(N-1))` is correct.

**Added: orientation-pair cluster analysis.**

- Clusters: the 295 design pairs of `results/local_stream/design.json` (the two tasks that shared one AB/BA coin
  and complementary pass positions) plus the singleton unpaired task `mbpp/256`; G = 296.
- Target: the **assignment-averaged same-task preference over the roster**, `(1/591) sum_t E[S_t]`, where the
  expectation is over the orientation coins (which decide the pass in which each workflow sees task t) and over
  episode randomness.
- Estimator: total same-task score / 591 (the same point estimate as before).
- (a) Cluster-robust variance by linearization with cluster totals `T_g` and sizes `n_g`:
  `e_g = T_g - n_g NB_hat`, `var = G/(G-1) * sum_g e_g^2 / 591^2`, t reference on G-1 = 295 df. **Approximate.**
- (b) Exact range-based final-time Hoeffding bound under independent clusters: a pair total has range 4 and the
  singleton range 2, so the radius is `sqrt( 2 (4*295 + 1) log(2/alpha) ) / 591 = 0.15794` at alpha = 0.05.
  Final-time only (E2 is analysed once), not time-uniform.
- **Independent clusters is still an assumption.** Arbitrary dependence inside a design pair is allowed;
  dependence across clusters through shared machine state (thermal state, caches, server history) is not excluded
  by the design, and neither interval handles it.
- The same two intervals are reported for the same-task success difference. **The -0.03 margin is not certified
  by any of the four intervals**: the t-type lower ends (-0.029749 task-level, -0.029460 cluster-robust) clear it
  by less than 0.001 and only under their model plus a normal approximation; the Hoeffding lower ends are -0.1117
  (task-level, model-based) and -0.1579 (cluster).

Results: same-task NB -0.6565; task-level SE 0.02485, t interval [-0.7053, -0.6077], task-level Hoeffding
[-0.7682, -0.5448] (both model-based); cluster-robust SE 0.02488 (ratio 1.0012), cluster t interval
[-0.7055, -0.6076] (approximate), cluster Hoeffding [-0.8145, -0.4986]. Observed within-pair correlation of the two
task scores 0.0008 (descriptive). That the cluster-robust and task-level SEs nearly coincide is an empirical
observation about this sample, not a guarantee.

**Added: descriptive pass/period table** (`pass_effects_v3.csv`): per variant, success rate, mean latency and mean
completion tokens in pass 1 versus pass 2, with simple differences. No inference is claimed; for a given variant
the two passes cover different tasks (a random split of the roster), so a difference mixes task composition with
any period effect. Period effects on latency are not separately identified.

## 5. Other Round 10 repairs

- **Endpoint arithmetic (finding 4).** `src/wincs.py`: `betting_log_capital_ternary` and
  `betting_log_capital_bernoulli` evaluated `0 * log(0)` as NaN and then dropped the whole stake, so that, e.g.,
  `exp(log capital)` was 0.9875 instead of 1 at n = 0 or at the endpoint mean of an all-win sample. The terms are
  now `count * log1p(arg)` masked to exactly 0 when `count == 0`; a stake whose factor is 0 kills the capital only
  when its count is positive. The defect was conservative in every checked case. New regression test
  `test_endpoint_normalization_round10` in `src/test_wincs.py`. `run_v3_all.py` regenerates the v2 numerical
  outputs with the repaired file and records the largest change in `v2_vs_v3_numeric_check.json` (interior CS
  endpoints are expected to be unchanged to about 1e-8). Status: principal tail-budget defect repaired (Round 9) and
  endpoint normalization repaired (Round 10); this is not a generic certification of every boundary case.
- **Anonymized copies (finding 5).** The sanitized copy of the git-ignored local data manifest is now at the
  non-ignored path `results/local_stream/release_anon/local_data_manifest.anon.json` (original sha256 kept in
  `MAPPING.json`). Regeneration of anonymized copies is location-dependent; no byte-for-byte portability is
  claimed. All committed anonymous copies were re-scanned for absolute home-directory path prefixes, the account name, host names and e-mail
  patterns (result in `MAPPING.json -> identifier_scan`).
- **PR body (finding 6).** A corrected description is provided in `results/local_stream/PR8_BODY_round10.md`.
- Wording kept from Round 9: design frozen **before design-task outcomes** (smoke checks and the out-of-design
  timing pilot called the model earlier); the E1 minus E2 difference is descriptive; "composite harm signal for B;
  incumbent A retained".

## 6. Sentences of `protocol_addendum_round9.md` superseded by this addendum

| Round 9 location | superseded text (abridged) | replaced by |
|---|---|---|
| section 3, R1 heading and first paragraph | "no sampling assumption"; "the episodes of different pairs use different tasks and separate model calls, so Z_1..Z_295 are independent with mu_k = (1/2)[m(s_k,t_k)+m(t_k,s_k)]" | section 1: mu_k = E[Z_k \| F_(k-1)]; the m(s,t) reading needs an additional stable episode-law model |
| section 3, "Relation to a roster-level target" | "E_design[mu_bar_n] = theta_N" stated as a property of the design | holds only under the additional model; no theta_N statement |
| section 3, R1 | "rho = 100 ... was fixed in analysis_v2.py before any R1 number was computed" (as mitigation) | fixed after outcomes were seen; post hoc |
| section 3, R2 item 2 | "E[Z_k \| F_{k-1}] = theta_P" with F undefined | section 2: F defined; unconditional model-based inference; independent stable episode laws required |
| section 4, first bullet | "the only randomness is model sampling ... independent across tasks"; "t interval is therefore (asymptotically, by the Lindeberg CLT for independent bounded scores) conservative"; Hoeffding interval described as needing no assumption | section 4: model-based labels, counterexample, cluster analysis |
| section 4, last paragraph | "conservative for the running average of means under R1" (pair-level component t intervals) | approximate and model-based |
| section 5, first bullet | margin cleared "under that single approximation" | margin not certified by any interval |

## 7. Files

`analysis_v3.py`, `make_report_v3.py`, `make_release_anon_v3.py`, `run_v3_all.py` (aggregate command) and this
addendum in `experiments/local_stream/`; outputs `summary_v3.json`, `decision_rules_v3.csv`, `e2_cluster_v3.csv`,
`pass_effects_v3.csv`, `report_v3.md`, `v2_vs_v3_numeric_check.json`, `analysis_v3_manifest.json`,
`PR8_BODY_round10.md`, `v2_pre_round10/` in `results/local_stream/`.
