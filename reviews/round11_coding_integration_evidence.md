# Round 11: minimal coding-evidence integration

**Decision: the proposed safe subset can be integrated now.** No unresolved prerequisite requires new model runs, importing contributed `wincs.py`, or waiting for airline results. Import preserved coding observations, frozen outcome/workflow definitions, and provenance; recompute all displayed statistics with the root-owned builder. Keep same-task results descriptive and use only the qualified R1 running-conditional-mean interval. The Round 10 defects remain excluded, not silently declared fixed.

Frozen source: PR 8 head `c89b525cd8e51564ca8c23399201d9cfdf0431a3`, unchanged. Date: 2026-09-19. This audit read committed blobs into `work/round11_coding_audit/`; it did not change the source repository, Git state, manuscript, other reviews or worker branch. No model, generated benchmark program, or previous Monte Carlo study was executed. Tiny direct arithmetic independently reconstructed the anchors below. Only small public license/model-card text was retrieved.

## 1. Import allowlist

Use a new, explicitly named imported-evidence directory. The following six logical artifacts are sufficient for **aggregate reanalysis**; proposed destination names are suggestions, not files created by this audit.

| Artifact | Frozen input | Minimum retained content |
|---|---|---|
| `observations.jsonl` | `results/local_stream/episodes.jsonl` | A deterministic, row-preserving field projection specified below; all 1,182 rows. |
| `design.json` | `results/local_stream/design.json` and `.sha256` | All 591 arrival records, task/benchmark labels, pass assignments, orientation/pair indices, seed, cardinalities and task/config hashes. For anonymous release omit researcher-repository Git identifiers and record a new derived-file hash. |
| `config.json` | `experiments/local_stream/config.json` | Original model, temperature, token limits, workflow limits, hierarchy and tolerance settings. Add a separate note that mutable benchmark URLs are superseded for retrieval by the pinned source manifest; do not quietly edit the frozen configuration. |
| `provenance.json` | `results/local_stream/run_manifest.json`, `data_manifest.json` | Whitelisted model revision/file hashes, hardware/runtime, task-source hashes/revisions/notices, original evidence hashes, projection specification and new artifact hashes. Remove local paths, machine/account identifiers and research-repository links/commit IDs from the anonymous copy. |
| `collection_definitions` | `agent.py`, `verify.py`, `sandbox.py`, `data.py`, `design.py`, `common.py`, `run_stream.py` under `experiments/local_stream/` | Preserve the exact frozen source as clearly marked, nonexecuted archival text, or extract the relevant definitions with source hashes/locations: prompts, response parsing, self-test/repair, verifier rule, latency/resource accounting, task construction, seed calculation and exposure schedule. The root analytical builder must not import or execute these collection modules. |
| `SOURCE_NOTICES.md` and license text | Public benchmark/model notices plus source manifest | MBPP/Austin et al., HumanEval/Chen et al., Qwen/MLX conversion identity; relevant license links/text, what is redistributed, and what is only referenced. |

The whole contributed protocol/report/analysis directory is **not** needed. In particular, exclude `src/wincs.py`, all contributed `analysis*.py`, `run_v2_all.py`, inference/decision CSVs, the v1/v2 reports, the contributed confidence-sequence figures, timing-pilot/dry-run observations and all tau2 files. The archival `run_stream.py` contains the old monitor implementation, so mark it historical collection provenance rather than a dependency or source of the new inferential claim. Only its exposure/accounting definitions are required for this integration.

Do not import `summary_v2.json` wholesale: it contains excluded E2 and R2 inference. Likewise, `resources_v2.csv` and `task_scores.csv` are validation references, not necessary primary inputs. The root builder can reconstruct their allowed numbers from the projected observations and design.

### Observation projection

Retain these columns/fields, in original row order, without numerical rounding:

```text
task_id, benchmark, variant, variant_letter, trial,
arrival_index, pair_index, orientation, pass, start_ts, end_ts,
n_llm_calls, prompt_tokens, completion_tokens, tokens_estimated,
n_executions, repair_rounds, self_test_passed, success, timed_out,
connection_retries, llm_call_seconds, execution_seconds,
finish_reasons, response_models, verify_seconds, sentinel_seen,
entry_point_defined, verify_returncode, latency_s,
sandbox_flag, hack_flags, static_flags
```

Store constant model/endpoint/sandbox/latency-scope information once in provenance. The observed `error` fields are all null and all `retry_log` lists are empty; preserve these verified facts in provenance, or retain the fields after validating their emptiness. Do not silently drop future nonempty errors. Distinguish omitted constant metadata from redacted free text.

The audit's example projection uses sorted-key compact JSON, UTF-8, LF, one row per line, with the 33 fields above. It has 1,182 rows, 990,571 bytes, SHA-256 `d2d325d3d77ee8b8bfeae778e9ea9121a75cb98ecbf92360d1b81b96333da83e`. It is available only in scratch as `projection_example.jsonl`; root may independently recreate it or choose a narrower declared projection. Its exact specification is `projection_spec.json`.

Required source hashes:

| Frozen input | SHA-256 |
|---|---|
| Original episodes | `95179f93acf72597c9b15257863ffee6acceed19414cf2b630beed62ec0effa0` |
| Original design JSON | `6175b81562efe1b1c87b113050f70c5daab2143e272cba39fb9a796f0d645457` |
| Original configuration file bytes | `0b40e6530ff70660116d409ad3887e0999ab5d73fa43af1f88fd93df032f4b73` |
| Canonical configuration object | `2dfb51966780698be326a8897c9e384a5513a7c1a47505c42b8a15c6c5baaf5b` |
| Original run manifest | `f2efc949ff13745aae0b2c5f902de6af05087a606c03803a6e9bc0a25815aa4f` |
| Committed sanitized benchmark manifest | `df0cd99b2795c750adea1d3972862b7a876e9b4893058b92e98ef5250de27064` |

Original and derived hashes must not be interchanged. Retain the untouched source privately; never describe the projected data as byte-identical raw traces. The projection permits exact numerical reanalysis of **archived verifier labels**; it does not independently rerun the verifier or reproduce model generations.

## 2. Why the full episode file needs a deliberate release decision

The source is not a metric-only table:

- `final_code` is populated in all 1,182 rows (273,787 UTF-8 bytes).
- `self_test_code` is populated in 591 rows (235,693 bytes).
- `verify_stderr` is populated in 316 rows; 312 contain local-user or per-user temporary paths, and 298 contain an assertion line.
- Against the exact pinned task definitions already verified in Round 10, seven final-code strings contain an entire reference-solution string; 286 stderr records, 28 generated self-test records and two final-code records contain at least one supplied assertion line.

These are exact text-overlap checks, not evidence that hidden tests were supplied to the model or that short solution matches establish memorization. They do establish that the full raw/sanitized episode files redistribute generated executable programs and benchmark material. The existing anonymized copy replaces identifiers but does not remove that material. For the minimal analytical import, omit `final_code`, `self_test_code`, `verify_stderr`, any traceback/free-form error text and `retry_log` contents; retain explicit failure flags and counts. Generated programs must never be executed by an aggregate reproduction entrypoint.

The original run manifest includes user cache paths, interpreter paths, process commands and other host metadata. The existing `release_anon` copy removes many path/name strings, but a fresh allowlist-based provenance export is safer for this narrow import. Keep model revision/file names/hashes, package versions and scientific settings; do not retain entire process listings, absolute paths, host names, account names, author-repository URLs or researcher commit identifiers. Exact timestamps are evidence of chronology, not a general assurance of anonymity; include them only if useful. Record all transformations and hash the exported files.

Do not rely on the absent `release_anon/work/local_stream/data/data_manifest.json` copy identified in Round 10. The separate committed `results/local_stream/data_manifest.json` is present and verified, and fully supplies the necessary benchmark-source facts.

## 3. Independently reconstructed numerical anchors

**Denominator:** 591 tasks = 427 MBPP sanitized + 164 HumanEval; one A and one B episode per task; all observations have `trial=1`. Exactly 1,182 distinct `(task_id, variant)` rows; no missing episodes or exclusions. Both passes have arrival indices 1 through 591 in order. There are 295 disjoint pass-1 pairs; `mbpp/256` is the prespecified leftover and contributes to same-task descriptions only. Orientation counts are 127 with `R=1`, 168 with `R=0`; `R=1` means A on the first arrival and B on the second, reversed for `R=0`.

| Quantity | A: single shot | B: self test and repair |
|---|---:|---:|
| Episodes | 591 | 591 |
| Success / failure | 433 / 158 | 433 / 158 |
| Model calls | 591 | 1,748 |
| Prompt tokens | 71,218 | 528,191 |
| Completion tokens | 41,491 | 185,088 |
| Total tokens | 112,709 | 713,279 |
| Workflow latency sum, s | 1654.5986205209047 | 7373.376646980643 |
| Workflow latency mean, s | 2.7996592563805494 | 12.47610261756454 |
| Workflow latency median, s | 2.079464666545391 | 10.131067499518394 |
| Hidden-verifier time sum, s | 31.36548403929919 | 9.67181489802897 |
| Executions including hidden verifier | 591 | 1,748 |
| Agent self-test executions | 0 | 1,157 |
| Verifier timeouts | 2 | 0 |
| Missing entry-point flags | 1 | 2 |

Totals: 2,339 model calls, 599,409 prompt tokens, 226,579 completion tokens, 825,988 total tokens. No API/connection errors, connection retries, estimated-token records, sandbox flags or heuristic hack flags. All 2,339 recorded call finish reasons are `stop`. Missing-entry-point flags are descriptive; actual success is the verifier's executed-result/sentinel rule, not simply that flag.

B/A ratios: model calls `2.957698815566836`; prompt tokens `7.416537953888062`; completion tokens `4.4609192354968545`; total tokens `6.328500829569954`; mean workflow latency `4.456293239661556`. These are token counts and measured local workflow durations, not dollars, energy, production latency or a general compute ratio.

### Comparator specification

Score `+1` favors B. Compare success first. If both fail, return a tie and do not compare resource tiers. If both succeed, compare latency, then completion tokens. For either resource tier, declare a difference only when `abs(B-A) > 0.10 * max(abs(A),abs(B))`; lower is better. Equal/within-tolerance values fall through; an unresolved comparison is a tie. Use strict `>` and the original unrounded observations. Do not replace the denominator in the relative tolerance by only A, an average, or the minimum.

**E1, pass-1 cross-arrival:** 69 B wins / 18 ties / 208 B losses; NB `-0.4711864406779661` (`-139/295`). Success-tier B wins/losses = 67/52; latency-tier wins/losses = 2/156; completion-tier = 0/0. Success difference B−A = `0.05084745762711865` (`15/295`).

**E2, same task, descriptive only:** 41 B wins / 121 ties / 429 B losses; NB `-0.6565143824027073` (`-388/591`). Success patterns: 393 both succeed, 40 only B, 40 only A, 118 neither. Thus same-task success difference is exactly zero. HumanEval: 11/19/134 wins/ties/losses, NB `-0.75`; MBPP: 30/102/295, NB `-0.6206088992974239`. Do not attach the contributed same-task t/Hoeffding/WR intervals or reverse-approval labels.

### R1 recomputation

For bounded pair scores `Z_k` and success differences `D_k`, define the target as the running average of conditional means under an explicitly specified pre-pair history. The bounded-score normal-mixture radius is

```text
r_n = sqrt((n + 100) * log((n + 100)/(100 * 0.05^2))) / n.
```

Apply it separately to the running averages of `Z_k` and `D_k`, clipping to `[-1,1]` if desired. Do not take a running intersection. At `n=295`:

- Radius `0.1828387393137264`.
- NB interval `[-0.6540251799916925, -0.2883477013642397]`.
- Success-difference interval `[-0.13199128168660776, 0.23368619694084505]`.
- First NB upper bound below zero: pair 60.
- The success lower bound never exceeds `-0.03` during the recorded sequence.

This analysis was introduced after the outcomes were known and must be labeled post hoc. It is a running conditional-mean statement for this laboratory stream, not a confidence interval for a fixed benchmark-population contrast. Separate 95% intervals are not a joint 95% rectangle. The reported first-crossing time is a reconstructed analysis result; collection continued through all planned episodes. No actual stopping savings, deployment or reverse guarded approval occurred.

The stronger symmetric-orientation formula using a time-invariant task kernel additionally needs stable/no relevant order-effect episode laws. For the robust minimal integration, use the history-conditional target directly and do not import that stronger identity, iid claims or R2 outputs.

## 4. Workflow and provenance that must accompany the numbers

One local open-weight model was used for both workflows: `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, revision `019cc73c45c770444708a6dd8690c66243cc5c80`; a loopback OpenAI-compatible API is a local serving interface, not a commercial model call. Temperature 0.7, top-p 0.95, maximum 1,024 tokens per request. A asks for one Python solution. B generates a solution, requests 3–5 self-tests, executes them and allows at most two repair rounds against those generated tests. No hidden-verifier feedback drives the repairs. Exact prompt strings and response parsing are in frozen `agent.py`.

MBPP prompts include the problem plus a reference-derived function signature; HumanEval prompts use the original function prompt. Hidden verification executes supplied tests and requires the randomized end sentinel. The resulting label means passing this benchmark verifier, not exhaustive semantic correctness. Public benchmark training overlap is plausible; equal observed success does not establish equivalence or 3-point noninferiority.

Workflow latency ends when the final candidate exists: model calls plus the workflow's own self-test execution and local overhead. Hidden verification is timed separately. Conversely, `n_executions` includes hidden verification; do not label all executions as agent tool calls. `execution_seconds` contains both self-test and verifier timing entries, so it must not simply be summed into workflow latency.

Recorded runtime: Apple M5, 32 GiB memory, macOS 26.5.2, Python 3.12.13, `mlx_lm` 0.31.3, NumPy 2.4.1. The manifest records the `mlx` package version as `unknown`; do not fill it in by inference. Collection lasted 9,071 seconds between the first episode start and last episode end. Per-call seeds are derived by the frozen harness from trial, arrival, variant, call kind and repair round; response records do not themselves contain every original request body. State seeded requests with reproducibility limited by runtime/hardware, not bit-identical model replay.

Design sources: MBPP sanitized at google-research commit `f82046ba5aabbbb427dbfd38a254d26bff08b533`; HumanEval dataset file at commit `463c980b59e818ace59f6f9803cd92c749ceae61`. The canonical task-list hash is `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`. The original mutable-URL downloads were retrospectively matched to these pinned bytes in Round 10; describe this as provenance repair, not an originally pinned-download claim. All 427 sanitized MBPP tasks were used, not only a held-out test split.

License/attribution evidence checked in this audit: the [MLX model card](https://huggingface.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit) and its exact pinned README declare Apache-2.0; the [Google Research MBPP dataset card](https://huggingface.co/datasets/google-research-datasets/mbpp) declares CC-BY-4.0; [HumanEval's current repository license](https://github.com/openai/human-eval/blob/master/LICENSE) is MIT. Retain benchmark/model attribution even when releasing only derived observations. If benchmark snippets or code are redistributed, include the applicable notices/license text. The HumanEval **dataset-file** revision predates the accessible `LICENSE` path, so use separately recorded license provenance rather than constructing a nonexistent license URL at that data-file revision. Small inspected texts and hashes are saved under scratch `licenses/`.

There is no top-level `LICENSE` file at this PR head. Do not describe the contributed research harness as having a verified MIT/Apache license merely because its model/dependencies do. This does not prevent the project's author from integrating their own contributed experiment and root-owned analysis, but the package's eventual code-license statement is a separate release matter.

## 5. Acceptance checks for the root builder

1. Validate original hashes, then the projected-file hash and field manifest; assert 1,182 rows, 591 tasks, exactly A/B per task and trial 1 only. Preserve all failures and both timeout records.
2. Reconstruct E1 using pass-1 design assignments and pairs, not arbitrary adjacent rows or task sorting. Exclude the single unpaired arrival only from E1. Reconstruct E2 by task, descriptively.
3. Match the numerical anchors above before formatting, including resource-tier eligibility and strict 10% tolerance. Preserve raw precision.
4. Recompute R1 from root code with the specified moving target; no contributed `wincs` import, E2 uncertainty, R2 claim or decision-rule table.
5. Check the final anonymous artifact for free-text code/assertions, local paths, account/host identifiers and researcher GitHub links/commit IDs; record the projection and provenance changes rather than rewriting raw history.

**No safe-subset blocker remains.** The deliverable should be described as reproducible reanalysis of complete, prospectively collected laboratory observations with post-hoc R1 inference. Full model-generation replay, independent reexecution of every verifier, fixes to contributed generic inference, and unfinished airline evidence are outside this narrow integration.
