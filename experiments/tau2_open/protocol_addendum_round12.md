# tau2_open: Round 12 addendum (report-only corrections, 2026-09-19)

Status: POST HOC wording corrections requested by the root session's Round 12 review of owner head
`55fb1e51234ad712c56799455bd704b829ed1d26` (root integration commit `45e8ee2715f148c81db7f6510d66677f57e03f0a`;
`reviews/round12_integration_ledger.md`, `reviews/round12_airline_inference_review.md`,
`reviews/round12_airline_evidence_review.md` on main). No model was run. No analysis was rerun. No observation, raw file,
log, frozen file, earlier addendum or earlier report was edited: `protocol_addendum_round10.md` and
`results/tau2_open/report_final.md` stay byte-unchanged, and the corrected report is the new file
`results/tau2_open/report_final_v2.md` (script `make_report_final_v2.py`, hashes in `report_final_v2_manifest.json`).

Where this addendum conflicts with `protocol_addendum_round10.md` or with `report_final.md`, this addendum governs.

## 1. History-conditional running-mean construction (supersedes the paragraph "History-conditional alternative" of the Round 10 addendum)

Withdrawn: "using it would require the conditions of 1.3 to be stated as assumptions" and "that target is not constant
across pairs even under an iid roster".

Correct statement. For any score `Z_k` in [-1, 1] adapted to a filtration `F_k`, `Z_k - E[Z_k | F_(k-1)]` is a bounded
martingale difference, and the normal-mixture boundary covers the running mean of `E[Z_k | F_(k-1)]` uniformly in n.
This needs **no common mean and no independent episodes**. Reuse of the 49 tasks across the two trial blocks means
that a constant conditional mean is **not guaranteed**; it does not mean that the conditional mean must vary in every
model. The construction is **not used** for tau2_open and no tau2 result is reported under it. This does not affect
the observed-array statement of section 2 of the Round 10 addendum, whose proof does not use it.

## 2. Final errors of the observed-array replay illustration (corrects one sentence of the Round 10 addendum)

The Round 10 addendum said, for both scores, "at n = 49 it is 0.0102". That is right for the net benefit only.
Recomputed from the per-pair rows of `results/tau2_open/round10_handoff_numbers.json`:

| score | observed replay mean | orientation-averaged target of the observed array | final absolute error | largest error on the path | target inside the band at every n |
|---|---|---|---|---|---|
| hierarchical net benefit | 0.020408 | 0.010204 | **0.010204** | 0.375 at n = 4 | yes |
| success difference | 0.020408 | 0.000000 | **0.020408** | 0.375 at n = 4 | yes |

Unchanged: the target (the orientation average of the complete retained array, given the matching), the nominal model
(independent fair replay coins; collection, amendment and retention independent of those coins; the pre-pair history
excludes future coins), the radius 0.6297 at n = 49 and the band [-0.609, 0.650]. The target is already computable
from the array, so the band is an illustration of a masked replay, not an inference about new tasks, fresh runs or
production.

## 3. Marginal, not joint

The net-benefit band and the success-difference band are each a **marginal** 95% time-uniform band. Together they do
**not** form a joint 95% statement; the union bound gives at least 90% simultaneous coverage, and a joint 95%
statement would need the error budget to be split. Their observed paths and endpoints coincide in this data set; their
targets do not (0.010204 and 0). Neither band certifies success non-inferiority or a guarded deployment.

## 4. Resource sentence and the margin sentence of `report_final.md`

- Withdrawn: "B used significantly fewer assistant tool calls" (section 1). The resource differences are descriptive
  means of canonical retained records. The task-clustered t intervals printed for them are model-dependent
  (independent tasks, normal approximation, unbounded counts, batch collection with period effects), unadjusted for
  multiplicity, and computed on canonical totals that omit discarded attempts. Complete failed-attempt usage is
  unavailable; the root's independent log reconstruction gives a lower bound of 246,284 additional generated arm-A
  tokens. No significance, operational-efficiency, total-cost or elapsed-saving claim is made.
- Withdrawn: "A guardrail of this size is not certifiable on a benchmark domain of 50 tasks at these success levels,
  whatever the method" (section 8). Correct statement: the specified replay rule and the reported intervals did not
  certify the 0.03 margin on these data. The retained records and a variance-based sample-size heuristic do not prove
  a method-independent impossibility.

- Withdrawn: "The intervals are conservative for the finite-roster average" (section 3.2). The task-clustered t
  intervals are model-dependent and approximate. Independence between tasks is not sufficient: they also need
  variance growth / nondegeneracy of the task scores, a Lindeberg or no-dominant-task condition and a consistent
  variance estimator.
- Withdrawn: "cannot clear -0.03 whatever the truth" and "Forty-nine pairs cannot resolve a 0.03 guardrail" (section
  3.1), for the same reason as the section 8 sentence: they are statements about one interval and one rule on these
  data, not about every method.
- Withdrawn: "Resolved secondary facts" (section 8) and the emphasis on the component interval cells (section 3.3).
  The resource rows are descriptive means.
- Section 10: the rating "met" for the run manifest covers the append-only run manifest only, not the decision
  chronology of deviation 1, which has no immutable record. The two uncertainty requirements are rated "not
  established" for the model-dependent intervals.

## 5. Separation of statement kinds

`report_final_v2.md` section 0 classifies every kind of statement in the report, and sections 3.3, 4, 5, 7.2, 8 and 10
carry a status pointer to it:

1. descriptive observations (canonical counts and means, all-attempt accounting): accepted by the root as descriptive
   collection results;
2. the observed-array replay band: optional post hoc illustration under the nominal coin model;
3. fixed-mean betting CS, decided-pair win-ratio CS, task-clustered t intervals, Welch intervals of the frozen
   `report.md`: model-dependent, assumptions not established by the design, **excluded from the root integration**,
   kept only as the record of the prespecified analysis;
4. decisions derived from those intervals or from sensitivity variants (decision-rule table, hierarchy / tolerance
   sensitivity, infrastructure-exclusion and omit-five sensitivities): outputs of stated rules on these data, kept
   separate from the descriptive observations and excluded from the root integration.

Unverified and stated as such: the actual sampler receipt (seed consumption inside the inference servers), an
immutable decision chronology for deviation 1, and complete failed-attempt usage. No fresh-run, production,
equivalence or operational-saving conclusion follows from this experiment.

## 6. Scope of issues #1 and #2

This experiment is a prospectively specified **batch collection with a prespecified replay analysis**. It is not a
live randomized A/B exposure and not an independent replication by a second party. Whether the broader confirmatory
ambitions of issues #1 and #2 are pursued is the repository owner's decision; no further run is requested or started.
