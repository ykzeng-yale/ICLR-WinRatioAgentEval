# Round 10: PR 8 repair and evidence audit

Reviewed frozen head **`c89b525cd8e51564ca8c23399201d9cfdf0431a3`**, relative to Round 9 head `ab24f1bc2d787241b7493cf2c9f2b406908a5a74`; the principal repair is `e0610088`. Date: 2026-09-18. This is an independent, bounded audit of the repair, not a new model experiment or a complete audit of other PRs. I previously authored the separate paid pilot, not this open-model experiment. Root sources and Git state remained read-only; only this review and isolated scratch under `work/round10_pr8_audit/` were written.

**Verdict: numerical repair reproduced; partial scientific closure.** The corrected coding results are suitable for integration as descriptive evidence and under the explicitly qualified R1/R2 targets below. Do not integrate the current claim that the same-task uncertainty is assumption-free or automatically conservative under the actual two-pass randomized design. That needs a dependence/target correction. No additional model execution is needed to address the findings. The airline experiment remains incomplete evidence at this frozen head.

## 1. What was independently reproduced

I inspected the aggregate runner and its reachable analysis, data-parsing, figure, report and anonymization functions before execution. None of those executed model calls or generated benchmark programs. The runner imports harness modules but does not invoke their model or program-execution functions.

The isolated snapshot contains 131 source/result files. The two small public benchmark sources were downloaded from the manifest's immutable revisions, only into scratch, and their bytes verified:

| Source | Bytes | SHA-256 |
|---|---:|---|
| MBPP sanitized | 255,053 | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` |
| HumanEval gzip | 44,877 | `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef` |

The inspected parser rebuilt the genuine 591-task list to the exact recorded canonical SHA-256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`. No synthetic task metadata was substituted. I did not re-fetch the out-of-design full-MBPP timing-pilot source or download any weights.

Command run from the isolated snapshot:

```text
python3 experiments/local_stream/run_v2_all.py
```

All six stages passed, approximately 190 seconds in total (185.6 seconds for the Monte Carlo CS check). Runtime: Python 3.14.4, NumPy 2.4.1, SciPy 1.17.0, pandas 2.3.3, Matplotlib 3.10.8. Independent comparison with the frozen Git blobs found:

- All four regenerated v2 CSVs byte-identical: `decision_rules_v2.csv`, `resources_v2.csv`, `running_cs_v2.csv`, `sensitivity_v2.csv`.
- `summary_v2.json` exactly equal after removing only `generated_at`; `two_sided_cs_check.json` exactly equal after removing only `elapsed_s`.
- Both report files text-identical after normalizing ISO generation timestamps.
- All six raw coding evidence files byte-identical before/after and unchanged from the Round 9 head: episodes, monitor CSV/state, design JSON/hash, run manifest.
- Every recorded raw, source, script, frozen-file, output and v1-preservation hash in the committed `analysis_v2_manifest.json` matches the corresponding frozen blob.
- Figure bytes differ across plotting-library environments, consistent with the manifest's stated limitation. Numerical inputs and figure source code are identical; this audit does not claim pixel identity.
- Anonymized-copy regeneration is not byte-identical across locations. The runner successfully generated 11 copies; three original artifacts are absent from the Git snapshot: the raw dry-run manifest/episodes and the original git-ignored local data manifest. The existing anonymized dry-run copies remain available. A separate missing mapped copy is documented in finding 5.

The Monte Carlo check reproduced corrected ever-miscoverage 0.0100, 0.0105 and 0.0100 for its three iid laws, 2,000 streams each, horizon 2,000. These are useful regression diagnostics, not a proof under the actual fixed-roster design. I also independently inverted the capital using `scipy.special.xlogy` and Brent roots on 107 sparse, boundary and random count vectors: no inward bound was detected; maximum endpoint difference was `2.85e-8` with the default stake grid.

Audit records in scratch: `snapshot_manifest.json`, `manifest_audit.json`, `aggregate_reproduction_audit.json`, `cs_inversion_independent_audit.json`, `endpoint_witness.json`, `e2_dependence_witness.json`, `additional_scope_checks.json`, and `audit_aggregate.log`.

## 2. Closure of Round 9 findings

| Round 9 issue | Round 10 assessment |
|---|---|
| Maximum of two capitals tested at `1/alpha` | **Main defect fixed.** Both ternary and Bernoulli functions now use `(K+ + K-)/2`; numerical inversion returns outside iterates. Endpoint arithmetic still needs the small repair in finding 4. |
| Fixed roster described as iid, stationary population inference asserted | **Substantially repaired.** R1 now targets a running pair/conditional mean; R2 is expressly an iid-roster model. See filtration/episode-law qualifications below. |
| Same-task uncertainty and Welch language | **Partially repaired.** Pass-1 components now use pair differences. E2 adds a valid variance identity under independence, but its actual-design independence and automatic-CLT claims remain unsupported. |
| Composite harm confused with safety harm or approval of A | **Fixed in v2 report.** It now means an unfavorable composite signal, incumbent retained. |
| Guardrail precision, E1/E2 comparison | **Fixed in v2 report.** Online noninferiority is not established; same-task approximate margin slack is explicitly fragile; E1/E2 difference is descriptive. |
| Mutable source URLs, missing source manifest | **Fixed for design-task provenance.** Immutable URLs and hashes are committed and independently verified. |
| Anonymous release | **Mostly repaired.** Existing copies pass the bounded identifier/numerical checks; one listed copy is missing. |
| Airline mislabeled as randomized physical exposure | **Fixed in addendum.** It is batch collection plus prespecified replay. Final real artifacts and all-attempt accounting are still pending. |
| Freeze and analysis history | **Improved.** Original evidence/v1 outputs preserved; v2 labeled post hoc; smoke/timing-pilot history distinguished from design-task freeze. PR body is still stale. |

## 3. R1 and R2: exact safe scope

### R1 normal-mixture construction is valid for a running conditional-mean target

`protocol_addendum_round9.md:42–79` and `analysis_v2.py:53–84` implement a valid bounded-score construction: for a specified history filtration, set `mu_k = E[Z_k | F_(k-1)]`. Since `Z_k` lies in `[-1,1]`, its centered increment has conditional range length 2 and conditional sub-Gaussian variance proxy 1. The stated normal-mixture boundary with `V_n=n`, `rho=100`, two-sided `alpha=.05` therefore covers `n^-1 sum mu_k` simultaneously. The code correctly takes **no running intersection**, since this target can move. The analogous statement applies separately to the running conditional mean of the success difference. Separate 95% intervals do not imply a joint 95% rectangular region.

For the interpretation `mu_k = [m(s_k,t_k)+m(t_k,s_k)]/2`, additionally specify an orientation-independent episode-law model: conditional on the pairing and past, the coin is fair and future potential episodes obey the claimed task-specific law. The statements at lines 44–46 that different tasks and separate calls *therefore* make pair scores independent are stronger than the design alone establishes. Thermal state, order, caching or other history dependence can affect latency. The addendum explicitly allows a conditional-mean interpretation at lines 63–65; use that interpretation in the report table and captions too. With history dependence, do not automatically retain the time-invariant `m(s,t)` formula or its equality in expectation to a fixed roster target `theta_N`.

The current R1 result is NB `-0.4712`, CS `[-0.6540,-0.2883]`, first upper bound below zero at pair 60; success-difference CS `[-0.1320,0.2337]`. These are post-hoc analyses of a prespecified observed stream, not a prospectively chosen new decision rule. Fixing `rho` before computing these particular intervals, after seeing the outcomes, does not retroactively preregister the analysis. The disclosure already makes this clear.

The addendum conservatively labels the original fixed-stake e-process crossing descriptive under R1. Root/theory are separately considering a stronger running-conditional-mean result for fixed nonnegative stake mixtures. Adoption of that new theorem is **not required for this PR's conservative wording**, and it must not be conflated with inference for `theta_N` or retained crossings of a moving current target.

### R2 is mathematically coherent with additional explicit conditions

The iid-roster permutation argument at lines 83–91 is correct **under its model**, provided independent/stable episode laws and a filtration that does not condition on the entire realized task vector/future outcomes are used. An iid vector remains iid after an independent permutation; disjoint pairs then have the required common law. This is unconditional model-based inference over hypothetical iid rosters, not a guarantee conditional on the observed curated benchmark. The fixed benchmark counts and public curation do not themselves establish that model.

The phrase `E[Z_k | F_(k-1)] = theta_P` should define `F`: past revealed pair data, plus design information independent of future task values, is sufficient. If `F_0` contains the entire realized task roster, that displayed equality does not follow from the iid-roster argument. A coarser statistical filtration is possible here because the frozen monitoring calculations use only past pair scores; it should be stated rather than silently identifying it with everything the investigator knew.

Safe R2 numbers, with that qualification: NB CS `[-0.6281,-0.2880]`, success-difference CS `[-0.0786,0.1794]`, decided-pair WR CS `[0.2010,0.5299]`; NB first excludes zero at pair 42 and stays excluded from pair 50. The one-sided harm crossing remains numerically pair 24; neither win nor success gate crossed. No episode was stopped or deployed on that crossing.

## 4. Remaining findings, ordered by integration importance

### Finding 1 — E2 independence is an additional model, not a property of this two-pass design

**Locations:** local addendum lines 124–140; `analysis_v2.py:147–165`; `report_v2.md:78–79`, same-task component/decision tables.

The identity

`E[s²/N] = Var(Sbar) + sum_t (tau_t-taubar)² / [N(N-1)]`

is correct for independent, not necessarily identically distributed task scores. Under that assumption, the displayed Hoeffding radius is also valid. But “only randomness is model sampling” omits randomized pass assignment, and separate calls do not remove dependence induced by shared AB/BA orientation coins or shared machine state. Calling the resulting interval “assumption-free” is incorrect.

**Exact counterexample using this design:** take a pair of tasks. Both workflows are identical within a task and period. Task 1 succeeds in pass 1 and fails in pass 2; task 2 fails in pass 1 and succeeds in pass 2. Under one fair AB/BA orientation, the two same-task success scores are `(1,1)`; under the other they are `(-1,-1)`. Thus each task's mean score is zero, but `Var((S1+S2)/2)=1` while `s²/2=0` in both realizations. No model noise or shared stochastic call is needed. Positive covariance within the orientation pair defeats the claimed variance identity for the actual design. With general covariance, the right side of the identity acquires an additional `-2 sum_(i<j) Cov(S_i,S_j) / [N(N-1)]` term for `E[s²/N]`.

**Required remedy before inferential integration:** either label E2 intervals as model-based approximations under independent task scores and stable/no relevant pass effects, or analyze the known orientation pairs as clusters and explicitly define the corresponding assignment-averaged target. Conditional on independent pair clusters, a range-based final-time bound for 295 clusters of size 2 plus one singleton has radius `sqrt(2(4*295+1) log(40))/591 = 0.15794`, compared with the current independent-task radius `0.11173`. This is an illustrative valid replacement under independent clusters, not a claim that it handles arbitrary thermal dependence or that this audit has changed the supplied analyses. Preserve the raw data and point estimates.

### Finding 2 — Boundedness alone does not establish the asserted Lindeberg CLT

**Locations:** local addendum lines 131–133; `analysis_v2.py:134–135`; report's repeated “conservative” labels.

A conservative variance expectation is not by itself conservative interval coverage. Bounded independent scores need a nondegenerate variance-growth/Lindeberg condition (and appropriate variance-estimator behavior) for the stated asymptotic normal argument. For a bounded triangular array `S_t ~ Bernoulli(1/N)` independently, the total variance remains bounded. At `N=591`, all scores are zero with probability `0.367568`; the zero-width t interval then excludes the positive mean `1/591`. This does not diagnose the present nondegenerate observed sample, but it disproves the blanket inference from boundedness alone. Latency component differences additionally need finite-moment/CLT conditions; they are not bounded ternary scores.

**Remedy:** state the necessary regularity and dependence assumptions and label the t intervals approximate. Retain the exact bounded-score concentration alternative under its actual independence or conditional-martingale conditions.

### Finding 3 — Airline repeated seeds and conditioning require further narrowing

**Locations:** tau2 addendum lines 34–68.

The disclosure of task reuse across trial blocks and the rejection of an automatic full-stream iid claim are improvements. However, the two trial seeds are reused across **all tasks**, not only the two arms of a single task. Thus the assertion at lines 61–62 that all common-seed dependence is “within task-by-trial cells” and automatically absorbed by task clustering is not established. Distinct tasks can share a random seed source or a batch state. The first 24 pairs also require the independent-episode model, not merely unique task labels.

A clean replay reading is available without further execution: condition on the complete collected outcome array **itself**, not merely its law, and on the matching. If collection did not use the replay orientation coins and there was no outcome-driven selection of the order, each independent orientation coin randomizes between two fixed comparator values. This supports an orientation-randomization running-mean statement about the **observed replay array**. It is not fresh-run, new-task or production performance inference. Alternatively use a history-conditional target with its conditions explicitly stated. No tau2 result has been certified under either reading here because real arrays are absent at this head.

### Finding 4 — Zero-count endpoint arithmetic remains wrong, conservatively in checked cases

**Locations:** `src/wincs.py:527–530` and `594–597`.

The code still evaluates `0*log(0)` and converts the resulting NaN for the entire bet to `-inf`. With default stakes, `exp(betting_log_capital_ternary(0,0,0,1))` and `exp(betting_log_capital_ternary(5,0,0,1))` both equal `0.9875`; the correct hedged capital is `1`. The all-loss endpoint and Bernoulli endpoints have the analogous defect. This underestimates boundary capital, so these witnesses are conservative; they do **not** overturn the reproduced interior coding CS or demonstrate undercoverage. The 107-case independent inversion check found no inward bound.

**Remedy:** use `xlogy(count, nonnegative_factor)` or explicitly mask zero-count terms before summing logs; add empty/all-win/all-loss endpoint normalization tests. The aggregate Monte Carlo check uses interior means and does not catch this. Treat closure as “principal tail-budget defect repaired,” not complete generic endpoint certification.

### Finding 5 — One anonymized artifact is listed but not committed

`release_anon/MAPPING.json` lists `results/local_stream/release_anon/work/local_stream/data/data_manifest.json`, SHA-256 `5f28f427514f5a576f4f39f93351226e94543d19790cc388ca0df759fc2e54c0`, but the path is absent from the frozen Git tree. This may reflect the broad `work/` ignore rule. The new `results/local_stream/data_manifest.json` is present and sufficient for the successful source verification; the missing copy does not invalidate the numerical results.

Existing anonymous copies matched their listed hashes. In eight available JSON/JSONL original-copy pairs every numeric/boolean/null leaf was identical. A bounded scan of committed anonymous copies found no account-name, personal-email or absolute `/Users/` path indicators. This is a scoped copy check, not approval to publish the entire identifiable research branch as an anonymous supplement.

**Remedy:** supply the missing sanitized copy outside an ignored path, or mark it unavailable/remove the promise from the mapping. Package from the explicit sanitized allowlist. Regeneration currently depends on the executing account/repository location; do not claim portable byte-for-byte anonymized-copy reproduction.

### Finding 6 — PR body still advertises superseded findings

The live PR body at the frozen head still gives the uncorrected CS `[-0.618,-0.301]`, says “before any outcome,” presents “every fixed-horizon rule agrees,” and causally explains the E1/E2 difference as the estimand-map mechanism. V2 correctly narrows these statements. Update the PR body to point to `report_v2.md`, quote corrected assumption-labeled intervals, use “before design-task outcomes,” and preserve the descriptive E1/E2 distinction. The report pointer is fixed; the public-facing body is not.

## 5. Airline amendment and all-attempt boundary

At this frozen head, the **only non-dry-run files** under `results/tau2_open/` are `design.json` and `design.sha256`. All saved raw invocations in Git are explicitly mock dry-run data. There is no real run manifest, no real per-invocation raw array and none of the amendment's cited real logs to inspect. `SESSION60_RESULTS_INDEX.md` reports 27/98 arm-A units, four successes and one infrastructure error, with arm B not started; these are owner progress statements, not independently verified completed evidence. Their absence is expected while the owner is still collecting, but it prevents treating them as final results.

The documented amendment adds a 1,024-token cap to both roles/arms and a 1,800-second simulation timeout after runaway generation on A task 6. Five A task-trial units completed before the amendment are retained; two failed attempts on task 6 reportedly left no outcome record. This is a material post-freeze operational amendment, transparently motivated by a failure before any B outcomes. It is not blind to all A performance: durations, token lengths and a failure were seen. Describe the five retained trajectories as *not reaching the later caps*, rather than claiming an experimentally verified counterfactual invariance under the changed serving regime.

The runner retains canonical and per-invocation raw copies after each arm subprocess returns (`run_tau2_open.py:270–298`). It also documents that upstream auto-resume drops infrastructure-error records and reruns those units. An interrupted subprocess can terminate before the ordinary copy step; final handoff must therefore include the interrupted invocation snapshot/logs as well as completed invocation copies. A final canonical success after retry does not erase the original infrastructure attempt.

Required at the owner's handoff, without restarting or expanding the experiment for this audit:

1. All real invocation manifests, exact commands, immutable raw copies, amendment hashes and failure logs, including interrupted invocation 1.
2. Reconcile the fixed 196 planned units against unique units, all attempts, retries, timeouts, token truncations, infrastructure errors and missing outcomes. State the rule used to select a canonical outcome among attempts and report failure-inclusive operational accounting separately.
3. Flag the five pre-amendment units and all amended units; retain both policies in provenance. Any omit-five sensitivity must be labeled post hoc and must not replace the planned denominator or hide initial failures.
4. Verify seed forwarding, agent/user served-model identities, actual cap/timeout application and token accounting from pinned call paths/raw metadata. Separate measured historical observations from intended configuration.
5. Label all temporal decisions **replay of batch collection**, with all A then all B, not physically randomized arrivals, live stopping savings, or production A/B.

## 6. Integration-safe handoff

**Safe now, with ordinary scope limits:** unchanged 1,182 observed coding episodes and complete denominator; 433/591 success in each workflow, 40 discordances each direction; resource totals and measured latency; E1 counts 69 wins/18 ties/208 losses over 295 pairs and NB `-0.4712`; E2 NB `-0.6565` descriptively; preserved monitoring paths and crossing indices; negative primary finding retained; no online success-guardrail certification. Model/runtime/task/seed provenance is substantially documented and source hashes reproduced. This is a prospective randomized **laboratory coding stream**, followed by complementary shadow runs, not a production experiment or an external preregistration.

Use `episodes.jsonl`, `monitor_pass1.csv`, `resources_v2.csv`, `running_cs_v2.csv`, and `summary_v2.json` for those quantities, choosing sanitized copies for anonymous release. The corrected CS numbers are integration-safe only with the R1 conditional-running target or explicit R2 assumptions above. `decision_rules_v2.csv`, `sensitivity_v2.csv`, the E2 fields of `summary_v2.json`, and the corresponding report/figure labels need their model-based uncertainty status preserved or repaired; “guarded_hierarchical A” is not a validated reverse online deployment approval.

**Still required:** repair E2 dependence/CLT/“assumption-free” wording or provide the correctly targeted cluster analysis; clarify R1/R2 filtrations and stable-law conditions; close the endpoint arithmetic and missing anonymous-copy issues; refresh the PR body; await the owner's complete airline handoff and audit its attempt selection before incorporating airline results. Optional extra models or new coding tasks are not needed to close these validity findings. No result here changes the frozen manuscript or its current readiness score automatically.
