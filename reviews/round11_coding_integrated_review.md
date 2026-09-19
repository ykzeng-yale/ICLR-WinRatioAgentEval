# Round 11: independent review of the integrated coding evidence

Reviewed September 19, 2026. **PASS for the bounded observation, analysis, and manuscript integration. No unresolved numerical or scientific blocker remains for this narrow use.** This is an AI scientific/code audit, not human peer review, a fresh model experiment, or a submission/acceptance certification.

I read the Round 11 evidence and target reviews, then independently checked root's builder, projected observations, all comparison/resource/band outputs, the three new manuscript files, and retained collection definitions against the frozen source under `work/round11_coding_source`. I did not execute the builder, collection modules, generated candidate programs, verifiers, models, or simulations. Only an independently written, standard-library arithmetic checker and this report were written in the authorized audit locations.

## Projection and observation integrity

The raw episode file matches SHA256 `95179f93acf72597c9b15257863ffee6acceed19414cf2b630beed62ec0effa0`. Every one of the 1,182 rows is preserved in original order, with all 37 declared original fields unchanged and `error_present = bool(error)` as the sole derived field. Reconstructing the compact sorted-key projection from raw values reproduced its bytes exactly: SHA256 `2551abc878ea8d2daaca2c14716428dabe4de959bdcb2080c3f2f014393ae512`. No numerical rounding, outcome filtering, dropped failure, or removed timeout was found.

There are exactly 591 tasks (427 MBPP and 164 HumanEval), one A and one B observation per task, trial 1 only, and two ordered passes of arrivals 1–591. Every exposure agrees with the original assignment. The design-selected leftover is `mbpp/256`; it is excluded only from first-pass pairing and remains in the same-task and resource summaries. Episode timestamps are ordered without overlap at their recorded precision. The exported assignment and configuration preserve their stated original values; the local endpoint is explicitly omitted from the analytical configuration.

Original errors are all null and retry logs all empty, consistent with the exported flags and provenance counts. No token totals are estimated, no connection retries are recorded, and all 2,339 recorded model-call finish reasons are `stop`. Both verifier timeouts are retained, in A. Archived success labels agree with successful verifier return codes and the sentinel condition. This is a label-consistency check, not independent reexecution of the hidden tests.

## Independently reconstructed numerical results

The checker uses a direct scalar hierarchy, without importing root's `compare` or any contributed inference routine: compare success first; joint failure ties; after joint success compare latency, then completion tokens, requiring a strict difference greater than 10% of the larger value. Positive signs favor B. Pair construction comes from original design assignments, not task sorting.

- **Every first-pass row matches:** all 295 signs, decisive tiers, success differences, pair indices and A/B task identities equal `results/open_coding/first_pass_pairs.csv`. They also match the original recorded monitor's scores. Counts are 69 B wins, 18 ties and 208 losses; net benefit is −139/295 = −0.4711864407. Success decides 67 wins/52 losses; latency decides 2 wins/156 losses; completion tokens decide none. Success difference is 15/295 = 0.0508474576.
- **Every same-task row matches:** all 591 scores, tiers, task/benchmark labels and success differences equal `same_task_scores.csv`. Counts are 41 wins, 121 ties and 429 losses; net benefit is −388/591 = −0.6565143824. Joint success/failure counts are 393/118, with 40 successes unique to each workflow.
- **Every R1 row matches exactly:** independent scalar square-root/logarithm evaluation agrees with all 295 rows and all eight numerical fields in `running_mean_bands.csv`, with maximum discrepancy zero. No running intersection is used. At n=295 the radius is 0.1828387393, net-benefit band [−0.6540251800, −0.2883477014], and separate success band [−0.1319912817, 0.2336861969]. The net-benefit upper endpoint first becomes negative at pair 60 and remains negative through pair 295. No success lower endpoint exceeds −0.03.
- **Every resource aggregate matches:** all exported fields and summary values were rebuilt from raw records, including means, medians, token sums, verifier time, model calls, executions, timeouts and errors. A/B success totals are 433/433; model calls 591/1,748; prompt tokens 71,218/528,191; completion tokens 41,491/185,088; total tokens 112,709/713,279; mean workflow latency 2.799659256/12.476102618 seconds; medians 2.079464667/10.131067500 seconds; self-test executions 0/1,157. Dividing B by A gives 4.456293240 for mean latency, 4.460919235 for completion tokens and 6.328500830 for total tokens, correctly rounded in the manuscript.

The paper's resource table matches these values. Hidden verification is excluded from the workflow-latency and self-test-execution endpoints. Subtracting one verifier execution per row is justified for this frozen dataset: every row has a recorded executed verifier, and execution/call list lengths agree with the counts. This is not a generic rule for future rows with empty candidates or unexecuted verifiers.

## Scientific and manuscript scope

`paper/open_coding_results.tex` and `paper/open_coding_appendix.tex` distinguish newly collected laboratory exposures from post-hoc inference and production evaluation. They explicitly identify the fixed normal-mixture application as post hoc and unadjusted for analysis selection. Its target is the running average of history-conditional pair means, with a filtration excluding future outcomes; it is not the all-pairs fixed-roster functional. The text correctly avoids asserting conditional fair-coin allocation while conditioning on the complete realized schedule.

The two 95% constructions are marginal, not a joint 95% region. The success guardrail is not certified; the negative composite signal is not success harm, proof of success noninferiority, or reverse guarded approval of A. The pair-60 crossing is chronological reanalysis, not a realized stopping or resource saving. All planned episodes were collected.

Same-task estimates remain descriptive because complementary passes, shared orientation coins and period effects can induce dependence. The manuscript attaches no E2 interval, E1–E2 comparison uncertainty, iid task-population interpretation, or hardware-invariant ranking. The claims concern archived verifier labels, local elapsed workflow time and recorded token totals, not complete semantic correctness, money, energy, production latency or adversarial robustness. The supplied source README additionally records that originally mutable benchmark downloads were retrospectively matched to pinned bytes and that all sanitized MBPP tasks, rather than only a test split, were included.

**One wording repair was requested and verified:** appendix sampling settings now say “a 1,024-token completion cap per call,” avoiding an implication that each call consumed exactly 1,024 tokens. No other material text correction remains.

## Collection provenance and reproduction boundary

All nine `.txt` collection snapshots match their source-manifest hashes. The seven Python collection modules also exactly match the hashes recorded in the original invocation; configuration and protocol hashes match their frozen inputs. Their definitions support the stated one-solution versus self-test/repair workflows, at most four model calls, reference-derived MBPP signature, absence of hidden-verifier feedback in repairs, success/sentinel rule, and workflow-latency stopping point before hidden verification. They are clearly marked historical, nonexecuted text, including superseded monitor assumptions.

The exported model inventory, hardware/runtime fields and original run/benchmark manifest hashes match the original invocation and retained source. A bounded scan of analytical data and collection evidence found no identifying local-user paths, names or research-branch commit identifiers. This is not a substitute for final whole-archive anonymity QA.

The analysis builder imports only the root `winstats` comparison and normal-mixture functions. It does not import contributed `wincs`, E2/R2 inference, capital-endpoint inversion, or executable collection snapshots. All currently listed output hashes plus builder/core hashes in `results/open_coding_integrity.json` match. The new contribution supports exact aggregate reanalysis from archived metrics; it does not reproduce model generation or reexecute hidden tests. Those limitations are explicit and do not block this scoped integration. Pending airline evidence and broader validation remain separate tasks.

## Retained independent audit and frozen hashes

The standard-library checker is in outer-workspace `work/round11_integrated_audit/check_integrated.py`; its machine-readable result is `check_results.json`. It takes `--repo` and `--output`, reads source/output files, and writes only its chosen audit JSON. No source-module import or generated-program execution occurs. This audit is reproducible without model calls.

- `experiments/build_open_coding_results.py`: `31297d8f6d84bd39402f77263ea217a7c5b8d623cff8c0fdee7764000e78a48d`.
- `paper/open_coding_results.tex`: `fb6221fc5fccdc34831725b87e1359fb14e0adbfbec501ec888746f893d5a118`.
- `paper/open_coding_appendix.tex`: `5052a9a43d69a9494d1fa61674a112a25f48b47a400cbcb7cad01193701c3f22`.
- `paper/open_coding_resource_rows.tex`: `fd884a106ab2b304232b41a5ab234f1875e074637b2d416ee83c438c8879e10f`.
- `results/open_coding_integrity.json`: `a3cd9ea9dbde6360486f3ba33bfb70799f54c74f7f4770cac0f8ecf57a3502ad`.
- `evidence/open_coding_collection/source_manifest.json`: `eea3655975a98e3af4ffbd9f3af96e3e4789ec090ff3f084146bb03b59831b8b`.

Final disposition: accept these integrated coding observations and qualified R1 summaries. No new experiment or further numerical repair is required by this audit.
