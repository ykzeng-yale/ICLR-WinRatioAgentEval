# Round 9: open-model evidence audit of PR 8

**Assessment: the coding experiment provides completed, useful prospective laboratory evidence, including a negative result. Preserve its raw data. Do not import its nominal 95% online confidence-sequence claims until two distinct inference issues are corrected. The frozen head contains no completed real tau2 open-model results.** The necessary immediate work is analysis/provenance correction, not another model run.

Reviewed [PR 8](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/8) at frozen head **`ab24f1bc2d787241b7493cf2c9f2b406908a5a74`**, including its body, experiment code, original episode records, designs, manifests, summaries, monitoring CSV, and mock tau2 outputs. The PR head matched the requested commit when inspected. All work was read-only against the owner’s files; aggregate checks and source snapshots are under `work/round9_open_model_audit/`. No model or job was launched, no weights were downloaded, and no provider credentials or commercial-model endpoint were used. This report is the only deliverable-tree file written by this reviewer.

## 1. What is actually completed

The local coding records support **1,182 completed episodes on 591 distinct tasks**, exactly one episode per task for each workflow and one sampling trial. The tasks are 427 MBPP-sanitized and 164 HumanEval. Workflow A is `single_shot`; B is `self_test_repair`, with generated self-tests and at most two repairs. Both use the same recorded model, `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, through **`http://127.0.0.1:8080/v1`**. The OpenAI-compatible interface name does not make these commercial OpenAI calls.

Independent checks from `episodes.jsonl`, without running model or benchmark code, established:

| Quantity | A: single shot | B: self-test/repair |
|---|---:|---:|
| Planned and recorded episodes | 591 | 591 |
| Hidden-test successes | 433 | 433 |
| Failures retained | 158 | 158 |
| Verification timeouts | 2 | 0 |
| Recorded API errors / connection retries | 0 / 0 | 0 / 0 |
| Model calls | 591 | 1,748 |
| Completion tokens | 41,491 | 185,088 |
| Prompt tokens | 71,218 | 528,191 |
| Mean measured workflow latency | 2.7997 seconds | 12.4761 seconds |

All **2,339 call records** name the configured local model and have `finish_reason=stop`; no token count is marked estimated. Every `(task, workflow, trial)` key is unique. All planned units occur in the frozen pass/arrival order, and timestamps are sequential. The design is generated before the first episode. The single unpaired arrival, **`mbpp/256`**, is retained in the same-task analysis and is prespecified to be absent from the cross-arrival analysis; it is not a missing pair.

The independent comparator reconstruction agrees with every stored same-task score and every online monitor score:

| Contrast, always B minus A | Units | B wins / ties / B losses | Net preference |
|---|---:|---:|---:|
| Pass-1 cross-arrival | 295 pairs | 69 / 18 / 208 | −0.47118644 |
| Same-task shadow, both passes | 591 tasks | 41 / 121 / 429 | −0.65651438 |

There are **40 B-only successes and 40 A-only successes** in the same-task comparison. The primary success-gain hypothesis is not supported. The observations strongly favor A on resources under the chosen hierarchy; the result should remain a retained negative finding, not motivate selective reruns until B wins. Calling B “harmful” must mean unfavorable on the prespecified composite, not an established safety or success-rate harm.

### The tau2 denominator is not completed real evidence

At this frozen head, `results/tau2_open/` contains only the frozen design and its hash outside `dryrun/`. The 196 episode rows under `dryrun/` are explicitly **mock data**, with `dry_run=True`; their report warns against use in the paper. There is no committed real run manifest, completed real episode table, or real endpoint-derived tau2 result to audit. Therefore the PR body’s “running” status is not completed evidence and its dry-run success counts must not be cited as observations.

The tau2 plan comprises **49 tasks × two trials × two arms = 196 planned real episodes**, with task 0 excluded prospectively after smoke use. The intended agents are Qwen2.5-7B-Instruct and Qwen3-4B-Instruct-2507, with the same Qwen2.5-7B user simulator. The present audit neither checks a live job nor changes that queue.

## 2. Exposure design: coding is prospective; tau2 is batched generation with replay analysis

For coding, `design.py` freezes a random permutation and a Bernoulli orientation for each disjoint adjacent pair. I reproduced that permutation and all 295 orientations from seed **20260918** and the canonical task identifiers; orientation counts are 127 versus 168. `run_stream.py` then physically executes pass 1 in that order, with one assigned workflow per arrival, and updates its monitoring output after each pair. Pass 2 executes the complementary workflow for every task. These are fresh, sequential, randomized laboratory exposures, not a rearrangement of old benchmark outcomes. Execution deliberately continues after crossings, so the crossing is a recorded decision that could have been taken, not an actual deployment or stopping intervention. There are no production users.

By contrast, `experiments/tau2_open/run_tau2_open.py:13–17,443,451` explicitly runs **all of arm A and then all of arm B**, with each arm trial-major in task order. Its random arrival/orientation file is used **only in subsequent analysis**. Even when its real runs complete, the accurate description will be **prospectively specified batch collection of fresh open-model trajectories with a prespecified replay analysis**, not physically randomized sequential exposure. Duration comparisons can also inherit batch/period effects. Preserve this distinction in the paper and PR.

## 3. Two separate inference issues require correction

### P1: the two-sided CS implementation is missing a tail adjustment

`experiments/local_stream/analysis.py:81–85` imports `betting_cs_ternary` and `win_ratio_cs_decided` from the frozen contributed `src/wincs.py`. In that file:

```python
# wincs.py:498 and :546
return np.maximum(logk(lam), logk(-lam))
# wincs.py:507
thr = np.log(1 / delta)
```

The maximum of two separately valid one-sided capitals is not itself their unit-initial nonnegative supermartingale. The implementation uses neither one-half weights nor a directional `alpha/2` threshold allocation. A tiny mathematical check with a fair single ±1 observation gives expected maximum capital **1.06370423 > 1**, directly refuting the claimed e-process interpretation of that maximum. The standard union bound gives at most **2α**, not α, for crossing either unweighted tail. This identifies a missing justification; it does not claim that this particular dataset empirically realizes 10% miscoverage.

The owner should preserve the old outputs, correct the two-sided construction using a proved weighted hedge/mixture or explicit tail allocation, add a small mathematical regression check, and regenerate **analysis outputs only** from the unchanged raw episodes. No new agent inference is required.

For scale only, invoking the existing mathematical inversion at directional level `.025` gives the following endpoint changes:

| Final online interval | Stored `.05` calculation | Directional `.025` calculation |
|---|---|---|
| Net preference | [−0.618372, −0.300831] | [−0.628293, −0.287739] |
| Success difference | [−0.069805, 0.170709] | [−0.078792, 0.179575] |
| Win ratio | [0.208271, 0.514054] | [0.200861, 0.530218] |

These are a diagnostic calculation, **not certified replacement population intervals**, because the next issue remains. They show that the directional interpretation is unlikely to reverse simply from the tail adjustment. The one-sided harm statistic from core `winstats.betting_log_e_ternary` does not use this faulty maximum; its numerical crossing at pair 24 is unaffected by this implementation bug.

### P1: a random permutation of a fixed roster does not establish the monitor’s conditional null

Protocol section 2 calls disjoint pairs “independent.” Section 10 later correctly acknowledges that the 591 tasks are sampled without replacement and the scores are exchangeable rather than iid, but then substitutes a **pointwise conditional-mean null** for the stated superpopulation mean null without proving that implication. Disjoint task identities, fresh random generation, and randomized AB/BA orientation do not make the remaining fixed roster an independent draw from an unchanged product law.

Consequently, neither the corrected two-sided construction nor the one-sided harm crossing automatically supplies the claimed population guarantee for this roster. This is an **estimand/assumption issue separate from the tail bug**. The owner should choose an explicit finite-roster/randomization target with valid inference, or clearly restrict the monitor guarantee to its stronger conditional-null assumption and label the observed paths/crossings as an operational illustration. Preserve the original exposures; do not relabel a reanalysis as preregistered. A finite-population-valid or design-based reanalysis may resolve the inferential question without new model calls.

The same caution applies to “295 independent pairs,” independent-arm Welch wording, and a blanket inference claim transported to the tau2 replay. The fixed-time same-task t intervals are conventional task-level uncertainty summaries; they also require a stated task-sampling/superpopulation model rather than a claim of an exact design-based census interval.

### Guardrail precision and comparison of estimands

The reconstructed same-task success t interval has lower endpoint **−0.029748506**, only **0.000251494** above the illustrative −0.03 margin. Calling this a robust noninferiority result is unwarranted; the nominal gate barely passes under that specific fixed-time approximation. The online gate did not cross, and even the stored success interval extends to −0.070. The coding data therefore do not demonstrate precise online certification of a 3-percentage-point success guardrail.

The E1 and E2 estimates differ by about 0.185, with different tier/tie patterns. This is informative descriptive evidence for distinguishing estimands. It is not an established population difference or a matched-efficiency comparison: they have different targets, share data, differ in sample size and exposure pass, and the report gives no joint uncertainty for their difference. If a stronger comparison is desired, use the existing data with a prespecified joint task/design-based analysis and retain its post hoc status.

## 4. Provenance and metric audit

The coding manifest records model revision **`019cc73c45c770444708a6dd8690c66243cc5c80`**, 11 model files and hashes totaling 4,295,890,004 bytes, Python 3.12.13, `mlx_lm` 0.31.3, and an Apple M5 host with 32 GB memory. These are recorded provenance, not a new independent inspection of remote weights or license text. The report acknowledges that Metal sampling is not guaranteed bit-reproducible. Per-call seeds are derivable from frozen code, trial, arrival, workflow, call type, and repair round; they are not explicit seed fields in each episode record. The deterministic design is reproducible; exact new generations and timings are not guaranteed.

The apparently conflicting harness commits can be reconciled from Git without new execution. All 13 recorded file hashes match the audited head and the recorded run commit **`526dff7b...`**. At freeze commit **`d9793d5...`**, only `protocol.md` differs; the other 12 files match. Both commit timestamps precede the first episode timestamp, and the follow-up commit records the freeze identifier. The “before any model call” phrase should be narrowed to **before any design-task outcome**: smoke checks and the out-of-design timing pilot are separately disclosed. This is a timestamped internal protocol freeze, not an external registration.

The primary metrics are valid for their stated scope:

- Success is observed hidden-test execution plus a nonce sentinel, with failures retained. I checked aggregate flags and code paths, but did not execute candidate programs or independently rerun every hidden test. Benchmark success is not exhaustive functional correctness; public benchmark exposure/training overlap limits generalization.
- `latency_s` measures model calls and the workflow’s own self-tests until the final candidate exists; it excludes hidden verification. Reconstructed sums of recorded call/self-test times agree within roughly 0.006 seconds. This is local single-host workflow latency, not queueing or production-user latency.
- Completion tokens are reported generation counts, not dollars, energy, or total compute. Prompt tokens should remain visible because B uses substantially more of them. The two workflow arms share the same tokenizer, making this within-model comparison interpretable; future different-model token comparisons need additional care.
- `n_executions` includes the hidden-verifier execution, whereas workflow latency excludes it. Keep verifier operations separate when calling these “agent tool calls.” The present hierarchy uses success, latency, and completion tokens, not that execution count.
- All successful/failing units are retained. The observed ratios of mean latency and completion tokens are about 4.46, but this one run does not establish those ratios on other hardware or workloads.

### P2 provenance and release repairs

The referenced `work/local_stream/data/data_manifest.json` is **not committed**, nor are the original task files. Configuration URLs point to mutable `master` resources. The canonical task-list hash is supplied, but the report’s claimed raw download hashes/manifest are not available in this PR snapshot. Before release, provide a sanitized source manifest with immutable upstream revisions, raw-byte hashes, canonical task hash, required notices, and a deterministic retrieval/build check; preserve the original local source artifacts. This needs no model rerun.

The committed manifests/config/README contain personal absolute filesystem paths and host-specific execution paths. These are normal development provenance but cannot be copied unchanged into an anonymous submission package. Produce sanitized release copies while retaining the originals and their hashes. Do not rewrite raw evidence merely to conceal provenance.

The tau2 sampling documentation also needs reconciliation before its results are interpreted: `config.json` says no per-request seed is sent, while the README and runner docstring say tau2 forwards its trial seed in every request. Verify the eventual raw requests/response metadata and actual pinned harness behavior, then record the correct reproducibility scope. Its frozen agent-token metric excludes user-simulator tokens, so both should be disclosed and token counts should not be called monetary cost.

## 5. Remaining experiments: priorities, not an automatic request for more runs

**Scientifically necessary before using the new evidence:** correct the two-sided inference implementation, resolve or narrow the fixed-roster inference claim, reconcile provenance/metric labels, and regenerate reviewed analyses from the preserved 1,182 episodes. Independently confirm the corrected aggregates and packaging. These are no-inference tasks, not new experiments.

**Necessary only for claims beyond the completed coding scope:** if the paper claims open-model evaluation on interactive tool-agent workflows, obtain and audit the queued real tau2 outputs, retaining the full 196-unit planned denominator and every failure/infrastructure attempt. Label the batch design accurately. If it remains incomplete, report missingness and retain the coding-only scope rather than treating mock results as evidence. If the main empirical claim specifically requires a physically randomized interactive arrival stream, this tau2 batch design does not satisfy it; an amended future open-model design would have to randomize actual exposure before outcomes, with no retroactive relabeling.

**Necessary only for a precision or deployment-certification claim:** plan a valid target and sample size for the 0.03 guardrail before another generation run. The existing online result is inconclusive for that margin; collecting a small second run without a precision calculation will not solve the problem. Use free simulation/analytic planning first, then any authorized execution must remain open-weight/open-source only.

**Optional additions:** more model families, another coding benchmark, a second stochastic replicate, hardware replication, or a targeted workflow ablation may improve external validity or explain repair failures. They are not prerequisites for honestly reporting this negative result. A success-improving comparator would be informative if independently motivated and prospectively frozen, but searching until a preferred ranking appears is not a valid completion criterion. A joint E1/E2 sensitivity analysis can use existing data rather than new generations.

The highest-value immediate action is to ask the existing PR owner for the concrete analysis and documentation corrections above, preserve the completed raw evidence, and await the separately authorized open-model job’s actual artifacts. Do not rerun proprietary models, launch an unplanned replacement experiment, or change the owner’s branch as part of this review.

## Evidence retained

`aggregate_audit.json` contains the reconstructed denominators, scores, metadata, and gate slack. `two_sided_cs_audit.json` contains the tail-allocation diagnostic and one-step expectation witness. `git_provenance_reconciliation.json` records the freeze/run/head hash reconciliation. `snapshot.json` records the audited source-file hashes. All are under `work/round9_open_model_audit/`. These checks substantiate the reported completed measurements while keeping inferential claims and outstanding experiments separate.
