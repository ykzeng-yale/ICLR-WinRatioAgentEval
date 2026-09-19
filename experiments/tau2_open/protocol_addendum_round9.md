# tau2 open-model stream: protocol addendum, Round 9

**Status.** Written 2026-09-18 in response to the root session's Round 9 audit of PR 8, while the real collection
was still running and **before any real tau2 outcome was analysed or inspected for this addendum** (only the
frozen design, config, code and mock dry-run outputs were read). It is nevertheless a POST-FREEZE document: the
frozen `protocol.md`, `config.json`, `design.py`, `build_episodes.py` and `run_tau2_open.py` are not edited, and
the running job was not touched. Where this addendum and `protocol.md` disagree on wording or on the scope of an
inferential claim, this addendum governs. It narrows claims; it does not add outcomes, arms, tasks or stopping
rules. The 196 rows under `results/tau2_open/dryrun/` are mock data and are never evidence.

## (a) What the collection is

The tau2 collection is a **prospectively specified batch collection of fresh open-model trajectories (all of arm
A, then all of arm B, trial-major in task order) with a prespecified stream/replay analysis**. It is **not**
physically randomized sequential exposure: the random arrival order and the AB/BA orientations of
`results/tau2_open/design.json` are used only by the analysis, after both batches exist. Consequences:

- no live stopping, no stopping savings and no operational latency claim follow from it; a crossing is "the
  decision the prespecified rule would have returned on the prespecified ordering", nothing more;
- duration (and any other time-sensitive) comparisons between arms can inherit **batch/period effects** (arm A
  and arm B run in different wall-clock periods, with different server processes and thermal/cache states); they
  are reported as descriptive, with the batch schedule stated next to them;
- this differs from the local coding stream, whose pass 1 was physically executed in the randomized order. The
  two experiments must not be described with the same exposure label.

## (b) Inference: R1 / R2, repeated tasks, shared seeds

The roster (49 airline tasks; task 0 excluded prospectively after smoke use) is FIXED; units are (task, trial)
with two trials per task; the design permutes the 49 trial-0 units (block 1) and the 49 trial-1 units (block 2)
and forms 49 disjoint consecutive pairs with independent Bernoulli(1/2) orientations (pair 25 straddles the
blocks). The same two readings as in `experiments/local_stream/protocol_addendum_round9.md` apply to the 49-pair
stream:

- **R1 (design-based, conditional on the realized matching and on the collected trajectories' law).** The
  orientation coins are independent across pairs, so the pair scores are independent given the matching, with
  means `mu_k = (1/2)[m(u_k, v_k) + m(v_k, u_k)]` for the two units of pair k; the target is the running average
  `mu_bar_n` over the pairs actually formed. The normal-mixture CS (`winstats.normal_mixture_radius`, V_n = n,
  rho = 100, two-sided alpha = 0.05, no running intersection) is valid for it with no iid or stationarity
  assumption. With n = 49 its radius is `sqrt(149 log(149 / 0.25)) / 49 = 0.63`, so it will be wide; that is the
  honest price of the design-based reading at this sample size and will be reported as such. No
  without-replacement martingale for a roster-level cross-task target is claimed.
- **R2 (superpopulation model, an ASSUMPTION).** The one-sided betting e-processes and the corrected two-sided
  betting / win-ratio CSs are valid for a fixed mean only if the pair scores have a common conditional mean. For
  this design that needs more than an iid roster: **each task appears twice in the stream** (once per trial
  block), so pairs in block 2 reuse the tasks of block 1 and the 49 pair scores are not iid draws even under an
  iid-roster model (task effects are shared across the two blocks). The block-1 subset (pairs 1 to 24, each task
  at most once) is the part of the stream for which the iid-roster argument of the local-stream addendum applies
  verbatim. For the full 49-pair stream the e-process crossings and betting CSs are therefore reported as an
  **operational illustration under the pointwise conditional-null assumption**, with the block-1 result shown
  next to it; no population guarantee is asserted for the full stream.
- **Monitor crossings** are descriptive under R1 (they test `mu_k >= 0`, or `<= 0`, for every pair, a stronger
  null than one about `mu_bar_n`), and carry an anytime guarantee only under the stated R2-type assumption.
- **Fixed-horizon uncertainty uses the task as the cluster.** Two trials per task are replicates inside one
  cluster (49 clusters, not 98 independent units); same-task contrasts use `wincs.clustered_summary` over tasks,
  and component contrasts use per-task means before the paired interval. Cross-arrival component contrasts will
  not be described as independent-arm Welch intervals; pair-level differences with the task-repeat caveat are
  used, and their intervals are labelled approximate.
- **Shared tau2 trial seeds across arms.** tau2 derives the per-trial seeds (626729, 373753) from `--seed 300`
  and uses the same two seeds in both arms, and the same user-simulator model at temperature 0. Episodes of arm
  A and arm B with the same trial index are therefore not independent replicates in the sampling sense (common
  random numbers for the user simulator and the agent sampler seed). This dependence is within task-by-trial
  cells, so it is absorbed by task-level clustering for same-task contrasts, but it must be **stated**, it makes
  "same trial" (diagonal) and "cross trial" pairings different estimands, and it limits the reading of the two
  trials as genuine independent sampling replicates. The report will give the diagonal and all-pairs versions
  side by side and will not claim the between-trial variation estimates run-to-run variability of a fresh seed.
- Same-task intervals are, as for the coding stream, conservative for the finite-roster average and conventional
  task-clustered intervals under a superpopulation model; both statements will be given. With 49 tasks the t
  reference is an approximation and is labelled so.

## (c) Seed forwarding: `config.json -> sampling_note` is superseded

`config.json` (frozen, not edited) says that no per-request seed is sent and that llama-server draws its own
sampler seed. The README and the runner docstring say the opposite: tau2 forwards its per-trial seed as `seed`
in every request. The `sampling_note` is **superseded**: the working assumption is that the per-trial seed is
forwarded in every request. This is a documentation correction; it changes no request that the running job
sends. **The eventual raw results must be checked for it** before any reproducibility statement is made:
(i) the per-simulation `seed` fields in the tau2 result JSONs equal the expected trial seeds in both arms;
(ii) the raw request/response metadata (or the pinned tau2 commit's LLM-call code path, read at the pinned
commit) show `seed` in the request body for both agent and user calls; (iii) the reproducibility scope is then
recorded as "seeded sampler, not guaranteed bit-reproducible across llama.cpp builds, batch composition or
hardware". If the check fails, the scope reverts to "unseeded sampling replicates" and section (b)'s
shared-seed caveat is withdrawn accordingly. Either way the finding is recorded in the results report.

## (d) Tokens

The frozen resource tier uses **agent completion tokens**. They **exclude user-simulator tokens**, and they are
generation counts, **not monetary cost**, energy or total compute. The report will give, per arm: agent prompt
tokens, agent completion tokens, user-simulator prompt and completion tokens, totals, number of model calls and
durations, with the batch-schedule caveat of (a). The two arms use different agent models (Qwen2.5-7B-Instruct
versus Qwen3-4B-Instruct-2507); token counts across different models (different tokenizers and parameter
counts) are not a common unit of compute, which will be stated next to any token comparison.

## (e) Corrected two-sided CS (post-freeze analysis-code deviation)

`experiments/tau2_open/analysis.py` imports `betting_cs_ternary` and `win_ratio_cs_decided` from `src/wincs.py`.
On 2026-09-18 `src/wincs.py` was replaced by the corrected, independently audited version (hedged capital
`(K+ + K-)/2` against `1/delta` instead of `max(K+, K-)`; sha256
`6a6a0b51bf46d64079614af3aefc364800c1862fd7635728c2949be7f2907a3b`). The call sites in `analysis.py` pass only
`(counts..., alpha)` and need **no edit** (the removed `coarse` argument was never passed); `analysis.py` is
byte-unchanged. The tau2 analysis will therefore use the corrected two-sided CS. This is a post-freeze
analysis-code deviation required by the audit; it was made before any real tau2 outcome was analysed, it cannot
make an interval narrower than the uncorrected one, and the one-sided monitor e-processes
(`winstats.betting_log_e_ternary`) are unaffected. The R1 normal-mixture CS of (b) will be added by a separate
`analysis_v2`-style script, not by editing the frozen `analysis.py`.

## Denominator and missingness (unchanged, restated)

49 tasks x 2 trials x 2 arms = 196 planned real episodes. Every enrolled unit, failure and infrastructure
attempt is retained; abstention or an incomplete collection is reported as such with its missingness counts, and
the scope then stays "coding only" for completed open-model evidence. No proprietary or commercial model is
called anywhere in this experiment.
