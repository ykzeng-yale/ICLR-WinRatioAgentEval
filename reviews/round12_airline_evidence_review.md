# Round 12 airline evidence review

Frozen handoff: `55fb1e51234ad712c56799455bd704b829ed1d26` (`origin/review-pr8`). Reviewed 2026-09-19. Scope: the airline raw records, new attempt ledger, policy flags, amendment erratum, collection provenance and a minimal anonymous projection. This is an independent saved-data/source audit; the reviewer authored the separate historical commercial pilot but did not collect this open-model airline study. No model calls, weight downloads, generated-program execution, contributed analysis imports, source edits or Git mutations were performed.

**Recommendation: the descriptive subset can be integrated.** The new ledger closes the previously missing attempt denominator. The data do not establish a clean randomized comparison of two fixed deployment policies, an independently replicated sampling experiment, full resource totals, or a production A/B result. Those limitations can be stated directly; they do not require discarding the observations or rerunning models for this descriptive integration. Do not import the contributed confidence intervals, significance statements, generic `wincs` code or population claims.

## 1. Denominators independently reconcile

I separately parsed the canonical JSON, CSV fields, τ2 log run/failure events and llama.cpp request-completion/cancellation events. The scratch audit uses only standard-library saved-data arithmetic. Its checks pass; it does not call the owner's `make_round10_handoff.py` or analysis functions.

| Quantity | A | B | Total |
|---|---:|---:|---:|
| Planned task × trial slots | 98 | 98 | 196 |
| Canonical records | 98 | 98 | 196 |
| Retained nonempty trajectories | 96 | 98 | 194 |
| Infrastructure placeholders | 2 | 0 | 2 |
| τ2 attempts started | 108 | 98 | 206 |
| Discarded attempts | 12 | 0 | 12 |
| Recorded success, with infrastructure failures mapped to unsuccessful | 15 | 15 | 30 |

The plan is tasks 1–49, two trials, two arms; task 0 was excluded for prior smoke use. There are no duplicated or absent canonical keys. The two placeholders are A/task 6/trial 0 and A/task 32/trial 1. They have no messages, null reward and zero recorded duration. Their zeros are placeholders, not measurements of zero work.

The 206 τ2-level attempts consist of 194 attempts yielding retained trajectories, 11 logged failed attempts, and one interrupted attempt. Invocation 1 has 8 attempts; invocation 2 has 198. The three repeated units are A/6/0 with 7 attempts, A/15/0 with 2, and A/32/1 with 4. All other 193 units have one attempt. There are 9 within-invocation retries and one cross-invocation restart of a unit lacking a saved record, giving 10 attempts beyond one per planned slot. A/15/0 is the only retained trajectory obtained after a failed attempt and has reward 0; all 30 successes arose on their first and only attempt.

The twelve discarded attempts comprise five context-overflow failures, four JSON parsing failures after truncation, two request-timeout failures and one owner interruption. This is **an attempt ledger at the τ2 simulation level**, not a count of individual model requests. Nested request retries must not be conflated with these 206 attempts.

The owner's JSON field `missing_outcomes: 0` is acceptable only as shorthand for no absent canonical records. It must not become “no missing outcomes/usage” in the paper: two canonical rewards and the twelve discarded trajectories are unavailable. The canonical failure mapping keeps all 196 planned slots in the descriptive comparator.

The new `unit_policy_flags.csv` has exactly 196 unique keys, matches raw cap-hit maxima, completion-limit flags and attempt counts, and identifies 5 pre-amendment units (A/tasks 1–5/trial 0) and 191 under the amendment. The 191 include the two final placeholders; this is the policy of their final invocation, not evidence of 191 completed capped trajectories.

## 2. Canonical results and measurement meaning

Independently recomputed B-versus-A scores use success first; on two successes, fewer agent completion tokens with 5% tolerance relative to the larger count, then fewer assistant tool calls; two failures tie.

| Saved-array contrast | Comparisons | B wins | Ties | B losses | Net preference |
|---|---:|---:|---:|---:|---:|
| E1, prescribed cross-unit replay pairs | 49 | 10 | 30 | 9 | 1/49 = 0.02040816 |
| E2, all four trial combinations per task | 196 | 28 | 141 | 27 | 1/196 = 0.00510204 |
| E2, same-trial diagonal | 98 | 13 | 73 | 12 | 1/98 = 0.01020408 |
| E2, cross-trial off-diagonal | 98 | 15 | 68 | 15 | 0 |

These are saved-array descriptive contrasts, with 49 tasks underlying E2 rather than 196 independent observations. All 19 decided E1 pairs resolve on success. E2 has 50 success-tier decisions, 4 completion-token decisions and 1 tool-call decision; all 141 ties are two failures. The E2 net contributions are 0 from success, +2/196 from completion tokens and −1/196 from tool calls. Thus the resource hierarchy influences only five E2 comparisons here. Do not present this small study as strong empirical identification of a general advantage of the hierarchy.

Reward provenance is more specific than “all trajectories independently verified.” The 124 user-stop trajectories (A 55, B 69) carry `DB`/`COMMUNICATE` reward bases; 30 pass. Another 70 retained trajectories have reward 0 without a reward basis (A: 27 max-steps and 14 too-many-errors; B: 29 max-steps). Two additional infrastructure records have null reward. All retained records lack saved hallucination-review, user-review or external-judge artifacts. A truncation is not automatically a task failure: of four canonical length-finished responses, A/task 31/trial 1 ultimately has reward 1.

## 3. All-role resources and the missing-work boundary

Every retained response's prompt/completion counts agrees with its raw response usage; completion counts also agree with llama.cpp `timings.predicted_n`. The 196 projected rows use no token estimates, but the two empty placeholders contribute no response records. The saved resource totals below deliberately exclude discarded attempts.

| Saved-trajectory quantity | A | B |
|---|---:|---:|
| Agent model calls | 2,485 | 2,263 |
| Agent prompt tokens | 20,412,368 | 19,138,768 |
| Agent completion tokens | 248,996 | 223,345 |
| User-simulator model calls | 1,720 | 1,812 |
| User-simulator prompt tokens | 4,373,819 | 5,915,658 |
| User-simulator completion tokens | 85,101 | 82,565 |
| Agent + user completion tokens | 334,097 | 305,910 |
| Assistant tool calls | 979 | 520 |
| Recorded trajectory duration, seconds | 15,851.156604 | 12,096.152344 |

Independent server-log totals match the handoff:

- A/user server, invocation 1: 193 completed requests and 16,444 generated tokens; 17 canceled requests, comprising 16 approximately 600-second request timeouts and one owner-stop abort. Last progress records establish at least 198,280 generated tokens on canceled requests.
- A/user server, invocation 2: 6,259 completed requests and 448,226 generated tokens, plus 20 context-limit rejections. B agent server: 2,264 completed requests and 223,347 generated tokens. Its totals equal 2,263 retained agent responses plus one 2-token smoke request.
- Across the two A/user-server sessions, completed requests contain 48,004 generated tokens beyond retained trajectories, after excluding four smoke tokens. Together with canceled-request progress, **at least 246,284 generated tokens from A collection are absent from the retained trajectories**. Attribution of this omitted work between agent and user is unavailable. Canceled progress is a lower bound, not a completed-response usage record. Full failed-attempt prompt usage and trajectories are unavailable.

All three server sessions contain six smoke completion tokens altogether. These are neither enrolled episodes nor failed-attempt usage. The lower bound above excludes them.

Use “saved-trajectory resource totals” and “complete failed-attempt usage unavailable.” Do not claim a complete token/latency/cost advantage. Native completion tokens are the chosen resource proxy, not common monetary cost, energy or compute across distinct models. Prompt totals include repeated context; agent totals omit simulator work unless the latter is separately shown. Durations are also affected by separate wall-clock batches and one resident server during A versus two during B. Do not divide by 98 and label the resulting averages as fully measured operational per-task costs.

## 4. Amendment and source provenance

The erratum appropriately withdraws the incorrect 20:45 UTC decision time and the claim that the five early records were demonstrably unaffected. Manifest/log content places the amended invocation at 20:33:06 UTC, with its first response around 20:33:13. Its command contains 1,024-token caps for both roles and a 1,800-second simulation timeout. The earlier invocation command has neither. Filesystem modification time is not preserved as independent, tamper-proof evidence by this review; use the content ordering, not that timestamp alone.

The five pre-amendment A rewards are 0, 0, 1, 1, 0. Their realized maxima, 514 agent and 205 user completion tokens, and durations 46.9–432.3 seconds did not reach the later limits. This does not prove counterfactual equivalence to a run with the new request fields and serving state. The change was after seeing A performance/operational evidence and before all B outcomes. The planned denominator should remain intact; omitting these units is only a labeled post hoc sensitivity.

The canonical capped responses contain four A-agent `finish_reason=length` events, each exactly 1,024 tokens; none occur for B or either user simulator. No saved post-amendment response exceeds 1,024. Nine τ2 truncation warnings include five from discarded attempts. No canonical trajectory terminates with the τ2 simulation-timeout reason; maximum retained duration is about 899.1 seconds for A and 492.2 for B. Request-level 600-second timeouts are a different mechanism from the 1,800-second simulation timeout.

Both historical runner versions are recoverable, improving on the erratum's hash-only wording:

- Invocation 1: `35a8d5a1c8b9155a39ad211252b928c244553893:experiments/tau2_open/run_tau2_open.py` has SHA256 `215e943a371a778900033586a28cd00b7e0f49f77966354ff3d2b6913c1c06ee`, matching the manifest exactly.
- Invocation 2: `4f01206a7d579f0ea02b6445c852d60d0ca23009` and current handoff bytes have SHA256 `27797f68e2aff6e088d0300f4be9baac903ef34b71ec84116125c2fa664ff75c`, also exact.

The other eight recorded harness/config/document hashes are unchanged between invocations. The amendment bytes retain SHA256 `696aede45eb45360a1a7e3e78626ec5d86ef745af5f2a02c5d0248adc272ce8f`. Preserve the two runner snapshots and superseding erratum as nonexecuted provenance text; do not silently replace the historical claim or original manifest.

I downloaded only small pinned upstream source/document bytes. At τ2 commit `b7ea9074c1cba482b30687fecdb5c8425fd6f619`, the [retry implementation](https://github.com/sierra-research/tau2-bench/blob/b7ea9074c1cba482b30687fecdb5c8425fd6f619/src/tau2/runner/progress.py) retries exceptions up to four attempts per invocation, returns the first non-exception trajectory regardless of its reward, and writes an empty infrastructure placeholder after exhaustion. [Checkpoint resume](https://github.com/sierra-research/tau2-bench/blob/b7ea9074c1cba482b30687fecdb5c8425fd6f619/src/tau2/runner/checkpoint.py) retains completed records, permits changed settings with auto-resume, drops prior infrastructure placeholders, and returns the previous info block. The observed second invocation retained five completed A units; no previously saved infrastructure record was rerun. Old A info therefore legitimately lacks the later cap fields. Use invocation commands and unit flags for the changed settings.

### Model, runtime, data and seed record

A and both arms' user simulator use Qwen2.5-7B-Instruct Q4_K_M; B uses Qwen3-4B-Instruct-2507 Q4_K_M. The configured agent/user temperatures are 0.3/0.0, with max steps 100, max errors 10, concurrency 1, and hallucination retries 0. All 8,280 retained model-response identifiers match those role assignments. The owner recorded successful weight-size/hash preflight checks in both invocations. This audit verified the manifest consistency, not the multi-gigabyte weight bytes themselves.

| Artifact | Pinned revision / recorded hash |
|---|---|
| Qwen/Qwen2.5-7B-Instruct-GGUF | revision `bb5d59e06d9551d752d08b292a50eb208b07ab1f`; two shards SHA256 `dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db`, `539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a` |
| unsloth/Qwen3-4B-Instruct-2507-GGUF | revision `a06e946bb6b655725eafa393f4a9745d460374c9`; SHA256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597` |
| llama.cpp | `4fea119de30f6a923992780f6fd5ccb0bee5d47d`; context 32,768; one slot; Jinja tool template; local loopback endpoints |
| Runtime recorded by harness | Apple M5, 32 GiB, macOS 26.5.2, Python 3.12.13; NumPy 2.4.1, SciPy 1.17.0, pandas 3.0.6, requests 2.34.2 |
| τ2 | commit above, source package version 1.0.1; protocol reports LiteLLM 1.81.11, but a complete executed environment lock is not deposited |

The pinned [Qwen2.5 GGUF card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/blob/bb5d59e06d9551d752d08b292a50eb208b07ab1f/README.md) and [Qwen3 GGUF card](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/blob/a06e946bb6b655725eafa393f4a9745d460374c9/README.md) declare Apache-2.0. The Qwen2.5 snapshot supplies the license text; the Qwen3 card points to the base-model license, and no same-revision GGUF `LICENSE` file was available at the tested URL. τ2's pinned repository license is MIT. Preserve upstream attribution/licenses for copied source. No weights need be distributed for metrics reanalysis.

The pinned public airline tasks and policy download to SHA256 `ccd8ba737b4cc371415af70151187788f728d6108d0916e73bb4317b40542052` and `10dc0525421521208be39cee235bba84a16e2bcba9899eb93d92cd81d2f62fc4`, exactly the preflight values. All fields supplied in the 49 selected upstream tasks match their raw-JSON counterparts; the embedded policy matches exactly. The database hash is recorded (`1af9fea6e03ca7ca15a22bb3fcaf3e351393e3fc9070b6777947da8996f7531b`); this audit did not download/rebuild that database or rerun its evaluator.

Seed 300 produces the two τ2 trial seeds 626729 and 373753, each reused on all 49 tasks in both arms. The pinned [LLM configuration mixin](https://github.com/sierra-research/tau2-bench/blob/b7ea9074c1cba482b30687fecdb5c8425fd6f619/src/tau2/agent/base/llm_config.py) inserts this seed into `llm_args`; orchestrator initialization calls it on agent and user, and both generation paths forward these arguments to LiteLLM. Thus the original manifest's “no per-request seed is sent” is not supported by source. Request bodies and server sampler seeds are not saved, so actual final sampler receipt is unverified. Neither independence nor bitwise repeatability follows. The addendum correctly withdraws independence confined to task-by-trial cells.

## 5. Minimal anonymous import and exclusions

For root's new, independently implemented descriptive builder, the following is sufficient:

1. A deterministic 196-row metrics projection, preserving arm/task/trial/seed, replay matching/orientation fields, raw reward plus missingness, chosen success mapping, termination reason, agent/user prompt and completion totals and model-call counts, assistant tool calls, recorded duration, response-usage presence and length-finish counts. Preserve the two placeholder rows and explicit missing-resource flags. Per-row source hashes and original compressed/uncompressed raw hashes can establish the projection lineage.
2. A 206-row attempt projection retaining key, invocation 1/2, attempt number, retained/discarded/interrupted classification, coded failure cause, cap regime, approximate elapsed time, truncation count and categorized request timeout/context-rejection counts. Keep the word “approximate” on log-derived timing and “lower bound” on canceled generation. Omit free-form failure messages, invocation UUIDs and local paths unless needed in a separate private audit.
3. The 196-row policy flags, sanitized design/config, a factual manifest subset, and a concise explicit erratum precedence note. Retain both runner versions plus `common.py`, `design.py`, `build_episodes.py` and the amendment as nonexecuted `.txt` historical source. The new handoff parser can be provenance text if its source logic is useful, but its analysis imports must not become a reproduction dependency.
4. Input/output/source hashes, source revision and primary upstream links, source/license attribution, and a small aggregate log-accounting artifact documenting the at-least-246,284 omitted generated tokens and unknown role allocation.

Do **not** import raw conversations, tool arguments, full benchmark instructions, traceback strings, the unredacted manifest/config, generated reports/figures with unsupported inferential claims, or contributed inference code. The raw JSON contains 9,973 messages, duplicated benchmark tasks, email-like synthetic dialogue content and local traceback paths. A metrics projection avoids republishing this content. Historical source/docs that mention superseded validity claims must be clearly marked; they are not active statistical guarantees.

This projected package reproduces arithmetic from a frozen metrics dataset. It should not claim to reproduce model inference, all failed attempts, or independently verify every original reward without the raw tasks/database/evaluator. No new run is required to make the *descriptive* saved-data analysis honest. A higher claim about fresh-run population effects, live deployment decisions or full resource consumption would require new properly logged/randomized evidence and appropriate inference; current snapshots cannot retroactively supply it.

## 6. Frozen input audit anchors

| File | SHA256 |
|---|---|
| `episodes.csv` | `5abbc1ce1acdc248ecf049276621a07449228ea3d8954e5af978559f3e11922f` |
| `all_attempt_accounting.csv` | `138fcf4adbe1e7194b7bd7e0b61b2eb166179690cb8d0b233b6fd45dff93bfeb` |
| `unit_policy_flags.csv` | `d9fe7ac806e6e03755934df392325837c97166d79db0a9e0fe32f0c62e6fcf7b` |
| `run_manifest.json` | `5ee827214337991a1f860d5158ed77d3f29f4169069191eecdb1ec04055f70d6` |
| `design.json` | `c8fa5728e8a9602813ffac10ea4ef88642ef3550aa9d5a5b7028c25586186597` |
| Uncompressed raw A | `887c66a23c2c1c2188279ce658efb15436648a9e26251b62f569521df4845fd8` |
| Uncompressed raw B | `39a49567936fb14f5444ae6e406c43abd1cfbb21198540c8b8df585d8fa1c8f6` |

Scratch evidence: `work/round12_airline_evidence/snapshot.json`, `independent_check.py`, `independent_numbers.json`, `independent_scores.json`, and the pinned upstream source/download manifests. All writes outside this review are confined to that scratch directory. Root source and Git state were not changed.
