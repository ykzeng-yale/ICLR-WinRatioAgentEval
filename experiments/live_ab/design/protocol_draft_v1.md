# live_ab: prospective, physically randomized, single-exposure, live-stopped laboratory A/B trials with open-weight models

**Protocol draft v1 (2026-09-19). Status: DRAFT, not frozen. No design episode has been run.**
Intended location after review: `experiments/live_ab/protocol.md` on branch `session60/live-ab`; results under `results/live_ab/<trial>/`.
This document becomes binding only through the freeze procedure of section 12.1 ("internally frozen, publicly timestamped by a pushed commit and an issue comment"; it is never called "preregistered" without that qualifier). The accurate chronology phrase is "frozen before any design-task outcome", not "before any model call": out-of-design smoke and calibration calls happen before the freeze and are tagged as such (section 5.8).

Inputs to this draft (all in `<scratch>/live_ab_design/`, SHA-256 prefix in brackets): `R1_accepted_method.md` [07acd3a7], `R2_constraints_checklist.md` [728c5a1c], `R3_harness_plan.md` [fa51f797], `R4_power_analysis.md` [2d1a4eaa], `power_sim.py` [59d87b6c], `power_results.csv` [d934c453], and the drafter's supplementary planning simulation `P5_supp_power.py` [bd6c935a] with output `P5_supp_power.json` [0ec6241f]. Root references are cited as `file:line` at root main `955579d` (paper and `src/winstats.py` byte-identical to the merged `410b158`; `src/winstats.py` SHA-256 `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69`).

Label convention used everywhere below: **incumbent** and **candidate** (never the letters A/B, because `paper/main.tex` calls the candidate A while `paper/open_coding_appendix.tex` calls it B). Scores are always computed as `compare(candidate, incumbent)`: positive favours the candidate.

---

## 0. Register of decisions and of items needing confirmation

### 0.1 DECISIONS taken by the drafter (each is argued where it is used)

| id | decision | section |
|---|---|---|
| D1 | Randomization unit = disjoint pair of consecutive arrivals; ONE fair OS-entropy orientation coin per pair; every task is still executed under exactly one arm. Departs from the coordinator's wording "coin per arrival". | 4.1 |
| D2 | Live OS entropy with a write-ahead, hash-chained, externally anchored log; NO pre-drawn random tape, NO seed, NO commit-reveal key. | 4.3 |
| D3 | Two concurrent workers, **pair-synchronous** in the randomized phase (the two episodes of one pair run concurrently; the next pair is enrolled and its coin drawn only after both are revealed). Work-conserving two-worker loop after a decision. | 5.1 |
| D4 | Serving = `llama-server` (llama.cpp commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d`), GGUF Q4_K_M, one process per model, `-np 2`; `mlx_lm.server` is not used (it serializes seeded requests and cannot give a sampler receipt). | 2.2 |
| D5 | T3 candidate model = IBM Granite 3.3 8B Instruct (Apache-2.0); fallback = Qwen3-4B-Instruct-2507 (Apache-2.0, already on disk and hashed). Both T3 arms use the `single_shot` workflow. | 2.4 |
| D6 | Hierarchy: T1, T2, T4 use the accepted coding hierarchy success > latency (10%) > completion tokens (10%); T3 uses success > latency (10%) only (tokens are not comparable across tokenizers). | 6.2 |
| D7 | Roster = extended roster EXT (591 pilot-roster tasks + MBPP-full-only tasks) if the outcome-blind availability rule of 3.3 is met, else the 591-task roster. Every trial uses the whole roster once, with its own arrival order. No epochs, no task replication within a trial. | 3 |
| D8 | Pairs are formed inside four outcome-blind baseline strata (pilot pattern "solved by both / exactly one / neither workflow", and "no pilot data"). | 3.5 |
| D9 | Live driver = split fixed-grid betting gates (`winstats.betting_log_e_ternary`, `prop:bet_running` + `thm:drift_gate`). The split normal-mixture confidence sequence is computed at every look and reported as the secondary construction. A complete fallback parameterization with the normal mixture as driver is given in 8.9. | 8 |
| D10 | A prespecified harm gate: the same betting construction applied to the score `-Z` at level `alpha_H`. Action label `RETAIN_INCUMBENT (unfavourable composite signal)`. | 8.3 |
| D11 | Error budget: 0.05 per trial. T1, T2, T4: `(alpha_NB, alpha_S, alpha_H) = (0.005, 0.04, 0.005)`. T3: `0.05/3` each. Program-wide union bound over the four trials = 0.20, stated as such; no program-wide 0.05 claim. | 8.4 |
| D12 | Success non-inferiority margin `delta = 0.10` on EXT; `delta = 0.15` if only the 591-task roster is available or if the normal-mixture fallback is the driver. The paper's 0.03 is declared "not certifiable at this sample size" in advance. | 10 |
| D13 | `n_min = 20` pairs; one look per completed pair; no retained crossings; no running intersection. | 8.2 |
| D14 | Asynchronous rule: the live decision uses the **completed enrollment prefix** (`prop:delay`). The partial-information enclosure statistic is computed at every log event and recorded as the matched comparator; it never drives traffic. | 7.3, 8.6 |
| D15 | Episodes in flight at a decision (impossible under D3 + D14 except after a crash) run to completion, are revealed, flagged and excluded from monitoring. No early termination of any episode, ever. | 8.7 |
| D16 | After a decision every remaining arrival of the frozen order is executed under the decided arm; this phase is an operational record, outside all inference. | 8.7 |
| D17 | Sampling: temperature 0.7, top_p 0.95, top_k 0, min_p 0.0, max_tokens 1024 per call, all other samplers neutral, `cache_prompt: false`; every field sent explicitly on every request. | 5.3 |
| D18 | Per-request seeds from a bijective index code (unique by construction, independent of the coin). | 5.4 |
| D19 | No episode-level retry. HTTP connection retries: 2 (as in the pilot). An attempt that never returned is re-run under the SAME arm (max 3 attempts, then scored as failure). Every try is logged. | 5.5, 6.4 |
| D20 | Anchors: local commit + push every 25 completed pairs or 10 minutes; issue comment with the chain head at freeze, trial start, decision, amendment and trial end. | 11.4 |
| D21 | Execution order T4, T2, T1, T3, one freeze for all four; no trial is repeated. | 12.4 |
| D22 | Closed-loop arrivals (next pair as soon as the previous pair is fully revealed); no arrival clock. | 5.1 |
| D23 | T2 is described as "costly candidate with equal pilot success", not "harmful candidate": its expected negative composite comes from the latency tier, not from success. | 1.2 |
| D24 | "Savings" are reported as (i) exact count of rejected-arm exposures avoided versus the fixed-horizon randomized design, (ii) measured totals of the run, (iii) a projection of time/tokens labelled as a projection. | 9.4 |
| D25 | Arrivals are a fixed permutation of a finite roster (single exposure), so the targets are running averages and the split-level, same-prefix, no-retention rule of `thm:drift_gate` applies. Arrivals drawn iid with replacement (which could justify the stationary full-level rule `thm:iut`) are rejected: they would break single exposure and rest on a stationarity argument the root already declined for this kind of roster. | 8.5 |

### 0.2 Items marked CONFIRM

| id | who | item | default in this draft if confirmed | fallback |
|---|---|---|---|---|
| C1 | coordinator | D1: pair-orientation coin instead of per-arrival coin | pair coin | none: per-arrival coins have no accepted score (`thm:pair_id` does not cover them) |
| C2 | coordinator | D3: pair-synchronous two-worker execution satisfies "two or more concurrent workers, out-of-order reveals with real timestamps" | accepted | sliding-window W=2 with the weaker claim of 7.5 |
| C3 | root (GitHub issue, before freeze) | D9: split same-prefix fixed-grid betting gates as the live driver | betting | 8.9 normal-mixture driver, `delta = 0.15` |
| C4 | root | D10: harm gate = `prop:bet_running` applied to `-Z` at `alpha_H` | betting harm gate | upper endpoint of the two-sided normal-mixture NB band below 0 (8.9) |
| C5 | root | D11: per-trial 0.05, unequal within-trial allocation, union bound 0.20 across trials | as stated | equal thirds everywhere; or program-level split `alpha_e = 0.0125` (then T1 deploy is improbable, stated in advance) |
| C6 | root and user | D12: `delta = 0.10` is a laboratory demonstration margin | 0.10 | 0.15 |
| C7 | root | D8: pairing within pilot-pattern strata (baseline covariate, `paper/main.tex:171-172`, `paper/theory.tex:238-245`) | stratified | strata {S1, S2} only |
| C8 | root | Reading of "no interference between the two positions" (`paper/theory.tex:185`) under concurrent within-pair execution: potential outcomes are indexed by the pair's orientation (7.4) | accepted | claim only the history-conditional guarantee |
| C9 | user | Downloads in the pre-freeze phase: pinned `mbpp.jsonl` (563,743 bytes), Granite GGUF (about 5 GB), LICENSE files of the model repositories | approved | 591-task roster; T3 fallback model |
| C10 | user | `git push` of anchor commits and `gh issue comment` from the user's account during runs | approved | local commits only; every "publicly timestamped" wording for run-time anchors is dropped |
| C11 | coordinator | Provenance of the cached `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` file (appeared in the cache on 2026-09-19); hash is recomputed at preflight | as recorded in 2.3 | re-download at the pinned revision |
| C12 | coordinator | Re-run of R4's full simulator for the final frozen configuration (strata, allocation, horizon); the numbers of 10.3 are a planning approximation | done before freeze | freeze with 10.2 and 10.3 as they are, labelled as such |
| C13 | root / author | Code licence of the harness for the arXiv release (the repository has no top-level LICENSE; the harness must not be described as MIT or Apache) | decided by author | release without licence statement |
| C14 | coordinator | The working branch contains root `410b158`; root main is at `955579d`. The new branch `session60/live-ab` is created from current root main by merge, never rebase | done | - |
| C15 | coordinator | Exact Hugging Face repository id, file name, revision and SHA-256 of the Granite GGUF can only be pinned at download time (the drafter had no network access) | pinned pre-freeze | T3 fallback model |
| C16 | root | Error control of the partial-information (enclosure) betting statistic under the running-average null is a one-line corollary of pathwise domination plus `prop:bet_running` that is not written in the paper (`thm:async_betting` is stated for the pointwise conditional null) | comparator reported as a measured timing comparison only, no error-control claim | same |

---

## 1. Purpose and claims

### 1.1 Purpose

The root's `EXPERIMENT_QUEUE.md` lists one conditional experiment: "Concurrent open-model prefix study with actual reveal timestamps; prospective randomized exposure trial. Required for measured operational savings or live-deployment claims". The root's gap assessment (`reviews/round9_experiment_gap_assessment.md:35`) asks for "actual reveal timestamps, nonanticipating certificates, fixed endpoint horizons and the matched completed-prefix comparator", with "the target and shared-resource assumptions" specified first.

`live_ab` is that experiment. It consists of four separately frozen trials on one Apple M5 (32 GB) with open-weight models served on the loopback interface only. In each trial:

1. tasks arrive in a prespecified order; consecutive arrivals form disjoint pairs;
2. when a pair is enrolled, a fresh fair coin from operating-system entropy fixes which arrival receives the candidate; the coin is durably logged before either episode is dispatched; each task is executed under exactly one arm;
3. the two episodes of the pair run concurrently on two workers; their outcomes are revealed out of arrival order with recorded timestamps;
4. a monitoring rule that was fixed before the first design-task outcome is evaluated at every completed pair on the enrollment-order prefix;
5. when the rule crosses, the dispatcher changes the traffic: all remaining arrivals run under the decided arm; nothing is replayed.

The 1,182 delivered coding episodes (`results/local_stream/`) are **pilot data**. They informed hierarchy, tolerances, margin, strata, error allocation, hypothesis directions and the power analysis. No pilot episode enters any trial table.

### 1.2 The four trials

| trial | incumbent | candidate | what is known in advance | expected live event |
|---|---|---|---|---|
| T1 "cheap candidate" | `self_test_repair` on Qwen2.5-Coder-7B | `single_shot` on the same model | pilot on the same 591 tasks (MLX stack): equal success 433/591, candidate 4.46 times faster | net-benefit gate crosses early; guarded deploy only if the success gate also crosses (probability 0.4 to 0.85, section 10) |
| T2 "costly candidate with equal pilot success" | `single_shot` | `self_test_repair` | mirror image of T1 | harm gate crosses, incumbent retained, remaining candidate exposures avoided |
| T3 "model swap" | `single_shot` on Qwen2.5-Coder-7B | `single_shot` on Granite 3.3 8B Instruct | nothing on these tasks; the only trial with unknown outcome | unknown |
| T4 "A/A control" | `single_shot` on Qwen2.5-Coder-7B | the identical system | exact null by construction | no decision; a decision has probability at most 0.01 under the exact null |

T1 and T2 are confirmatory demonstrations of live operation of a frozen rule on a contrast whose pilot answer is known on the same tasks; this is disclosed wherever they are reported (R2 K7).

### 1.3 Claims the trials MAY support (each only if literally true at the end)

1. "An internally frozen, publicly timestamped, physically randomized (fresh OS-entropy coin per arrival pair, logged before execution), single-exposure, live-stopped laboratory A/B trial on N fixed benchmark tasks with open-weight models on one Apple M5."
2. "The monitoring rule was the fixed-stake betting construction of `src/winstats.py` at SHA-256 56955ce0..., with all levels, thresholds, the hierarchy, the margin and the horizon frozen before the first design-task outcome. Under adaptedness and boundedness of the scores, the probability that the rule issues a deploy decision at any enrolled prefix at which a running conditional-mean criterion is false, or a retain decision at a prefix at which the running conditional-mean net benefit is nonnegative, is at most 0.05 in that trial."
3. "In trial Tk the rule crossed at enrolled pair n at calendar time t; the dispatcher switched at t'; the remaining M arrivals ran under the decided arm." This is a measured event, not a replay.
4. "Relative to the prespecified fixed-horizon randomized design, the decision avoided exactly M_pairs exposures to the rejected arm", plus measured wall-clock and token totals of the run; any time or token "saving" is labelled "projection from pre-decision means".
5. "Outcomes were revealed out of arrival order with recorded timestamps; the completed-prefix rule and the partial-information enclosure statistic reached their crossings at calendar times t1 and t2" for this run and this serving regime.
6. "Failure-inclusive usage accounting reconciles client and server counters to within X tokens; every request's sampler settings were recorded as received by the server."
7. T2: "the prespecified rule rejected the candidate (unfavourable composite signal); the incumbent was retained". T4: "in one A/A control path no gate crossed" (or, if one did, it is reported as the rare event it is). T3: whatever happens, including abstention.
8. "The success-difference gate at margin delta crossed / did not cross"; non-crossing is abstention.

### 1.4 Claims that are FORBIDDEN in any report, index, PR text or manuscript sentence derived from these trials

1. Production A/B evidence, user benefit, deployment safety, or "deployed" without "in the laboratory dispatcher".
2. A population, fixed-roster (theta_N), superpopulation or fresh-task effect; iid-task inference; the word "independent" for pairs or episodes.
3. Empirical calibration or type-I-error control from one or four streams; "holds its level"; "error rate is zero".
4. Equivalence or non-inferiority from equal or similar success counts. Only a gate crossing at the frozen margin is called non-inferiority, and then "at margin delta for the running target".
5. "Approval of the incumbent", "the incumbent satisfies the guardrail", success harm or safety harm from a composite harm crossing.
6. Joint 95% coverage from marginal bands; a "two-sided 95%" object from two one-sided level-alpha processes; a program-wide alpha when each trial used its own.
7. Significance of resource differences; t, Welch, cluster-t or delta-method intervals; win-ratio confidence sequences; anything from `src/wincs.py`.
8. Hardware-, model-, workload- or tokenizer-invariant rankings; dollars, energy or "compute" from token counts; cross-model token comparisons as cost.
9. A causal assignment-average reading without naming the coin model, the filtration and the concurrency regime of section 7.
10. Measured time or token savings derived from counterfactual or replayed paths; per-task "operational cost" from retained-only totals.
11. "Preregistered" without "internally frozen, publicly timestamped"; "before any model call".
12. Bit-reproducible generation; independent re-adjudication of success labels; exhaustive correctness. Success is the archived verifier label.
13. "Assumption-free", "impossible for any method", "not certifiable whatever the method", "conservative" without conditions, mechanism claims from post-crossing diagnostics. The permitted sentence is "this prespecified rule did not certify margin delta on these data".
14. That post-decision single-arm data validate the decision or predict future benefit.
15. That the hierarchical rule is generally better than component rules.
16. That the root "approved" the trial, the PR or the methods beyond what a root disposition literally states. Owner-side verification is AI review, not human peer review or author sign-off, and says so.
17. Mock or dry-run outputs cited as observations.

---

## 2. Systems

### 2.1 Hardware and host

One Apple M5 laptop, 32 GB unified memory (34,359,738,368 bytes), macOS 26.5.2 (build 25F84) at drafting time. The exact chip string, memory, OS build and power state are read from an allowlist at every invocation and logged; nothing else about the host is recorded (no user name, no host name, no process listing). During a trial: mains power, `caffeinate` active, no other GPU job, exclusive lock file, preflight scan of the two service ports; the harness refuses to attach to a server it did not start. Hardware and runtime are printed next to every resource table; no hardware-invariant statement is made.

### 2.2 Serving software (D4)

`llama-server` built from llama.cpp commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d` (the commit already frozen in `experiments/tau2_open/config.json`). The binary's SHA-256 and the commit read from the checkout's `.git` are part of the freeze bundle. Reasons for not using the pilot's `mlx_lm.server` 0.31.3 (R3, section 0): it routes every request that carries a seed to a single-request path and drains running batches, so two workers would only queue; it returns no sampler settings; its `model` response field is an echo of the request, so a served-model check is vacuous. `llama-server` returns, with the request field `"verbose": true`, the object `__verbose.generation_settings` (seed, temperature, top_k, top_p, min_p, penalties, sampler order, n_predict), `id_slot`, token counts and the rendered prompt; `usage` and `timings` are always returned; `model` is the server-side alias; `/metrics` exposes cumulative token counters.

Frozen launch line, one process per model (paths are written as tokens in every tracked artifact):

```
llama-server -m <HF_CACHE>/<gguf file> --alias <alias> --host 127.0.0.1 --port <port>
  -np 2 -c 16384 --no-kv-unified -ngl 99 --jinja --metrics --no-context-shift --offline
  --log-file <WORK>/live_ab/<trial>/logs/llama_<port>.log --log-timestamps
```

`-np 2` equals the number of workers, so no request ever waits for a slot; `--no-kv-unified -c 16384` gives each slot 8,192 tokens (pilot maximum summed over a `self_test_repair` episode: 3,934 prompt and 1,474 completion tokens); `--no-context-shift` turns an overflow into a visible truncation; `--offline` forbids network access. Ports: 8091 (Qwen2.5-Coder), 8092 (T3 candidate). T1, T2, T4: one resident server for the whole trial. T3: both servers resident for the whole trial including the post-decision phase (serving arrangement identical for both arms, R2 item 30).

Because GGUF Q4_K_M under llama.cpp is a different quantization and kernel path from the pilot's MLX 4-bit build, all pilot numbers are planning numbers only.

### 2.3 Models

| role | base model (licence) | GGUF repository, revision | file | bytes | SHA-256 |
|---|---|---|---|---|---|
| T1, T2, T4 both arms; T3 incumbent | `Qwen/Qwen2.5-Coder-7B-Instruct` (Apache-2.0) | `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` @ `13fb94bfda8c8cf22497dc57b78f391a9acb426a` | `qwen2.5-coder-7b-instruct-q4_k_m.gguf` | 4,683,073,536 | `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c` (content-addressed cache blob name; recomputed at every preflight) CONFIRM C11 |
| T3 candidate (primary) | `ibm-granite/granite-3.3-8b-instruct` (Apache-2.0) | `ibm-granite/granite-3.3-8b-instruct-GGUF` @ revision pinned at download | the Q4_K_M file of that repository | pinned at download | pinned at download CONFIRM C15, C9 |
| T3 candidate (fallback) | `Qwen/Qwen3-4B-Instruct-2507` (Apache-2.0; LICENSE file in the base repository at revision `cdbee75f17c01a7cc42f958dc650907174af0554`, SHA-256 `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`) | `unsloth/Qwen3-4B-Instruct-2507-GGUF` @ `a06e946bb6b655725eafa393f4a9745d460374c9` (community conversion; licence tag apache-2.0) | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` | 2,497,281,120 | `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597` |

Aliases (served `model` field, asserted on every response): `qwen2.5-coder-7b-instruct-q4km`, `t3-candidate`.

Licence evidence (R2 item 92; "open weights alone do not establish an unrestricted licence"): for every model the freeze bundle records repository id, revision, and the SHA-256 of the LICENSE file at that revision, or, where the repository has only a model card, the literal statement "licence declared on the model card only" plus the base-model repository, its revision and its LICENSE hash, plus the converter's repository for community conversions. `Qwen2.5-3B-Instruct` (Qwen research licence) and any model under a Llama, Gemma, OpenRAIL or "research/non-production" licence are not eligible. No API key is read; the HTTP client hard-asserts a loopback base URL; preflight fails if an API-key environment variable is present; there is no LLM judge (success is the executable verifier).

Memory: 4.7 GB (coder) + about 5 GB (Granite Q4_K_M) + KV caches of at most 2.6 GB per server at 16k context; well inside 32 GB.

### 2.4 Choice of the T3 model (D5)

Requirements fixed before looking at any T3 output: (i) Apache-2.0 or MIT weights; (ii) a different model family from Qwen (different vendor, tokenizer and training data), so that the contrast is a genuine model swap; (iii) parameter count close to the incumbent's 7.6 B, so that the latency tier is not decided by size alone and the outcome is not predictable from the parameter count; (iv) a GGUF published by the licensor, so that licence evidence is first-party; (v) a dense transformer supported by the pinned llama.cpp commit with its embedded chat template under `--jinja`; (vi) instruction-tuned with published code-generation ability of the same order as the incumbent.

Granite 3.3 8B Instruct meets all six (8.2 B parameters, Apache-2.0, IBM-published GGUF). Considered and not chosen: `microsoft/phi-4` (MIT, 14 B: twice the decode cost, so the latency tier would be decided by size); `microsoft/Phi-4-mini-instruct` (MIT, 3.8 B: a size contrast rather than a family swap); `mistralai/Mistral-7B-Instruct-v0.3` (Apache-2.0, weak at code, outcome predictable); `01-ai/Yi-Coder-9B-Chat` (Apache-2.0, no first-party GGUF); DeepSeek-Coder, Code Llama, StarCoder2, Gemma (licences outside Apache-2.0/MIT). The rationale contains no outcome of any candidate on any design task.

Fallback rule (evaluated before the freeze, from preflight facts only): if the Granite GGUF cannot be fetched or hashed, its licence evidence cannot be recorded, the chat template fails under `--jinja`, or the receipt smoke test (5.7) fails, the T3 candidate is `Qwen3-4B-Instruct-2507`. That model is from the same vendor as the incumbent and is smaller; T3 is then described as "model-generation and size swap within one vendor", not as a family swap. The choice is recorded in the freeze bundle; after the freeze it cannot change.

Both T3 arms use `single_shot`: it is the cheaper workflow, it isolates the model swap, and the choice is made now, independently of the T1 result.

### 2.5 Arms

| trial | incumbent | candidate | servers |
|---|---|---|---|
| T1 | workflow `self_test_repair`, coder model | workflow `single_shot`, coder model | 8091 |
| T2 | `single_shot`, coder | `self_test_repair`, coder | 8091 |
| T3 | `single_shot`, coder | `single_shot`, T3 candidate model | 8091 + 8092 |
| T4 | `single_shot`, coder | `single_shot`, coder (identical system; the arm label is the only difference) | 8091 |

Workflows are the delivered, audited ones: `experiments/local_stream/agent.py` (SHA-256 `3cf2056330c72ebd5d2884f48d6ec2daa706fcc685ad67e3c2609d809ff75b64`), `sandbox.py` (`d461570937ddbe1fb241288721a1a06b44bd41dd72ccdc2e2ffa2f144184c6ff`), `verify.py` (`7473678b1990ca2a5a1900b45251fddcd2882f2b371d76d3a59fe669a607dbb6`), reused byte-identically through an injected model object (R3 A.1); any byte change requires a new leakage and sandbox audit before the freeze. `single_shot` = one model call. `self_test_repair` = code call, test-writing call, execution of the agent's own tests in the Seatbelt sandbox, at most 2 repair calls; hidden tests never enter a prompt and the verifier gives no feedback to the agent. The legacy field `variant_letter` inside the reused record is ignored; the harness carries its own `arm` field in {`incumbent`, `candidate`}.

---

## 3. Task pool

### 3.1 Sources (pinned; mutable `master` URLs are never used)

| stratum family | source | pinned revision | file | bytes | SHA-256 | licence |
|---|---|---|---|---|---|---|
| S1 | MBPP sanitized, all 427 problems (not a test split) | google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533` | `mbpp/sanitized-mbpp.json` | 255,053 | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` | CC-BY-4.0 |
| S1 | HumanEval, all 164 problems | openai/human-eval `463c980b59e818ace59f6f9803cd92c749ceae61` | `data/HumanEval.jsonl.gz` | 44,877 | `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef` | MIT (licence provenance recorded separately from the data revision) |
| S2 | MBPP full, problems not in the sanitized subset | google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533` | `mbpp/mbpp.jsonl` | 563,743 | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` | CC-BY-4.0 |

The S1 canonical task list is the delivered one (list SHA-256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`). The S2 file is not on disk; fetching it (one pinned URL, 564 KB, byte and hash check, refusal on mismatch) is a pre-freeze step that needs approval (CONFIRM C9). Raw third-party data stay outside git; `SOURCE_NOTICES.md` carries the attributions (Austin et al. 2021; Chen et al. 2021).

### 3.2 Exclusions (all prospective, outcome-blind with respect to every model; the list with reasons is frozen in `roster.json`)

1. The six timing-pilot tasks `mbpp_full/39, 122, 522, 547, 869, 966` (they are the out-of-design smoke and calibration tasks, 5.8).
2. S2 problems whose normalized prompt duplicates an S1 task (normalization of `experiments/local_stream/timing_pilot.py:35-36`); the S1 version is kept.
3. S2 problems whose entry point cannot be resolved by `mbpp_entry_point` (`experiments/local_stream/data.py:35-44`).
4. Any task of S1 or S2 whose reference solution does not pass `verify()` twice in a row inside the Seatbelt sandbox on the trial machine (no model involved).
5. Nothing else. No task is excluded for difficulty, length, or any model output.

### 3.3 Roster rule (outcome-blind, evaluated once, before the freeze)

Let `n_S2` be the number of S2 tasks that survive 3.2. If the download is approved and `n_S2 >= 400`, the roster is **EXT** = S1 plus S2 and `delta = 0.10`. Otherwise the roster is **S1** (591 tasks) and `delta = 0.15`. The rule depends only on file availability and on reference-solution sweeps. The expected size of EXT is at most 1,132 tasks (591 + 547 - 6) minus duplicates and sweep failures.

### 3.4 Why tasks that were used in the pilot are acceptable, and why the pool is not split

1. Validity of every guarantee in section 8 rests on the scores being adapted, bounded and produced by a frozen rule, and the causal reading rests on fresh coins. Neither rests on task novelty. The pilot can influence the trial only through design choices, and those are frozen and disclosed.
2. No outcome of the new trials is known: the serving stack (llama.cpp Q4_K_M), the seeds and the concurrency regime are new and sampling is at temperature 0.7.
3. The claims are about this laboratory stream (1.3), not about fresh tasks; public-benchmark exposure of the models is disclosed and no contamination-free claim is made.
4. A split that holds out every pilot task would leave at most the S2 stratum (fewer than 275 pairs), too few for any success gate (section 10). The drafter judges a split unnecessary and harmful.
5. Disclosure that accompanies every T1/T2 result: hierarchy, tolerances, margin, error allocation, strata and hypothesis direction were chosen with pilot knowledge of the same tasks; T1 and T2 are confirmatory live-operation demonstrations; only T3 has an unknown outcome. The S2 stratum is pilot-naive; a by-stratum read-out (S1 versus S2) is prespecified as descriptive.
6. Precedent respected: units whose outcomes were seen in smoke use are excluded (the six timing-pilot tasks), as task 0 was in the airline study.

Each trial uses the whole roster once with its own arrival order, so a task is executed once per trial and up to four times in the program, never twice within a trial. The four trials are therefore not independent replicates and are never pooled or described as such.

### 3.5 Strata and pairing (D8)

Strata (baseline covariates, fixed before any trial outcome; derived from `results/local_stream/episodes_flat.csv`, SHA-256 `1237b82f99c5ea8ad1e319e0ec45873ba85a2ff13d670d508d78ae06547bd540`):

| stratum | definition | tasks | pairs | unpaired |
|---|---|---|---|---|
| `S1_k2` | S1 task solved by both workflows in the pilot | 393 | 196 | 1 |
| `S1_k1` | solved by exactly one workflow | 80 | 40 | 0 |
| `S1_k0` | solved by neither | 118 | 59 | 0 |
| `S2` | MBPP-full-only task (no pilot data) | `n_S2` | `floor(n_S2/2)` | `n_S2 mod 2` |

(The counts of the S1 strata change only if 3.2 item 4 removes a task; the frozen `roster.json` is authoritative.) Pairs are formed inside a stratum. Reason: the paper's design forms "disjoint pairs of arrivals within a prespecified stratum" (`paper/main.tex:171-172`); stratified pairing "reduces cross-context comparisons" (`paper/theory.tex:238-245`). For the success component the pair target is the average same-task success effect of the two tasks (`paper/theory.tex:247-258`), so over the full roster the success target does not depend on how pairs are formed; only the variance does (planning value: share of pairs with nonzero success difference 0.19 within S1 strata versus 0.39 unstratified). For the hierarchical score the target is the within-stratum cross-task preference; it is therefore not comparable with the pilot's unstratified value of 0.47 in absolute size, and no such comparison is made. If the pilot pattern predicts the new stack poorly, efficiency is lost, never validity. CONFIRM C7.

### 3.6 Arrival order (seeded, hash-committed; it is not the assignment mechanism)

For trial number `e` (T1 = 1, T2 = 2, T3 = 3, T4 = 4):

```python
rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([60260919, e])))
pairs, leftovers = [], []
for stratum in ["S1_k2", "S1_k1", "S1_k0", "S2"]:            # fixed order; S2 absent on roster S1
    uids = sorted(roster[stratum])                            # bytewise order of uid strings
    u = [uids[j] for j in rng.permutation(len(uids))]
    pairs += [(stratum, u[2*m], u[2*m + 1]) for m in range(len(u) // 2)]
    leftovers += u[2 * (len(u) // 2):]
enrollment = [pairs[j] for j in rng.permutation(len(pairs))]  # random interleaving of whole pairs
```

Pair `i` (1-based) = `enrollment[i-1]`; its position 1 is arrival `2i-1`, its position 2 is arrival `2i`. Leftover tasks receive the arrival numbers after `2*N_P` in list order; they are never randomized and are executed only in a post-decision phase. The resulting file `arrival_order_T<e>.json` (pairs, strata, uids, leftovers, `N_P`) is the authoritative object; its SHA-256 is in the freeze bundle, so later numpy versions are irrelevant. The file contains no arm, no coin and nothing from which a coin can be computed.

Horizon: `N_P` = number of pairs in the file (EXT: 295 + `floor(n_S2/2)`, at most 568; S1: 295). There is no extension, no second pass and no re-randomization of unused tasks.

---

## 4. Randomization

### 4.1 Unit and coin (D1, CONFIRM C1)

The coordinator's design text says "a fresh fair coin at each arrival". This protocol uses **one fresh fair coin per disjoint pair of consecutive arrivals** instead, because the only randomized online design in the root's paper is the disjoint-pair orientation design (`paper/main.tex:171-177`; `paper/theory.tex:179-236`, `thm:pair_id`): one coin `R_i` decides which position of pair `i` receives which system, so every pair contains exactly one episode per arm and, with probability 1/2, the score `Z_i` is the observed oriented kernel in {-1, 0, 1} with `V_n = n`. Independent per-arrival coins would produce pairs with two episodes of the same arm, for which neither the paper nor `src/winstats.py` defines a score; outcome- or latency-driven matching of k-th candidate with k-th incumbent episode is not covered by `thm:pair_id`; and R4 found that per-arrival coins leave about 3% of arrivals unpaired, make the number of pairs random and cost 0.5 to 2 points of power. What the coordinator's intent requires is preserved: the coin is physical, fresh, logged before execution and never redrawn, and each task is executed under one arm only.

Definition. For pair `i` with positions 1 and 2 (arrivals `2i-1`, `2i`): `R_i = 1` assigns the candidate to position 1 and the incumbent to position 2; `R_i = 0` reverses. `P(R_i = 1) = 1/2`.

### 4.2 Code path (normative)

```python
raw = os.urandom(8)                 # macOS kernel CSPRNG; the only source of assignment randomness
bit = raw[0] & 1                    # R_i
eventlog.append("coin_drawn", {..., "raw_hex": raw.hex(), "bit": bit, ...}, durable=True)
# durable=True returns only after fcntl(fd, F_FULLFSYNC) succeeded.
# Only after that return may either job of pair i be sent to a worker.
```

Invariants, each enforced by the orchestrator and re-checked by the independent log verifier: (i) at most one `coin_drawn` per pair; (ii) `coin_drawn` for pair `i` appears after the `episode_revealed` events of both episodes of pair `i-1`; (iii) every `episode_started` of the randomized phase points to the earlier durable `coin_drawn` of its pair; (iv) no `coin_drawn` after a `decision`; (v) a coin is never redrawn: on resume a durable coin is reused, and a torn (non-durable) coin line can never have been acted on because dispatch requires the completed fsync; torn bytes stay in the file and are counted (`n_torn_recoveries`, expected 0); (vi) no other randomness influences the assignment: a unit test monkeypatches `os.urandom` and checks that arms follow the patched stream exactly.

### 4.3 Live entropy versus a committed random tape (D2)

Options considered for verifiability:

| option | what it proves | why accepted or rejected |
|---|---|---|
| (a) tape of coins drawn in advance and hash-committed | coins were fixed before outcomes and not redrawn | Rejected. The whole orientation sequence would exist before the first episode. That is the configuration the root criticised in the pilot (`reviews/round11_coding_target_scope.md:50`; counterexample in `reviews/round12_coding_correction_and_baseline_delta.md:41-49`): anything that can read the tape can anticipate assignments, and a filtration that contains the tape makes the current coin degenerate. |
| (b) commit-reveal key (coin = keyed hash of the pair index, key revealed at the end) | same as (a), with the tape hidden | Rejected for the same reason in weaker form: future coins exist in harness memory; the root's standard is that future coins do not exist ("A fixed seed is not physical randomness", R2 items 5 to 7). |
| (c) public randomness beacon | third-party verifiable coins | Rejected: needs network calls during the run; policy is loopback only. |
| (d) live OS entropy, write-ahead logged, hash-chained, externally anchored | the coin existed before its pair was executed; no second coin for the pair is in the log; the log prefix containing the coin existed at the next external anchor | **Chosen.** |

What (d) does not prove, stated openly: a third party cannot cryptographically exclude that an operator killed the process after reading a coin and before dispatch, deleted the log tail and restarted. Mitigations that make such an act visible or costly: the single-writer append-only file is never truncated by the harness; invalid tail bytes are legal only when the next event commits to their offset, length and SHA-256; anchors (local commit, push, issue comment) bound the window in which a rewrite is possible to at most 25 pairs or 10 minutes; `llama-server`'s own timestamped log and the server token counters (11.5) would show requests that are absent from the event log; operator actions are logged events; the operator console shows no arm-level outcome summary before the decision event. The residual reliance on operator honesty is stated in the report as an assumption ("collection, retry and amendment logic is arm-blind and coin-independent").

A preflight self-test draws 10,000 non-design coins and checks the count against binomial limits (it tests the plumbing, not the kernel's generator); these draws are tagged `phase=SMOKE` and never used.

### 4.4 What is pseudorandom and why that is harmless

The arrival order (3.6) and the per-request sampling seeds (5.4) are deterministic functions of frozen constants and indices. Neither is an assignment mechanism; neither depends on the coin; both are in `F_0`.

### 4.5 Arm-blind operation

Dispatcher, client, retry, timeout, cap, resume and amendment logic are identical for both arms; the only arm-dependent code is the lookup of the workflow name and server URL from the frozen arm table. Any operator intervention is a logged `operator_action` with a reason code.

---

## 5. Execution model

### 5.1 Workers and scheduling (D3, D22, CONFIRM C2)

`W = 2` long-lived worker processes (`multiprocessing` spawn context, single-threaded because `sandbox.py` uses `Popen(preexec_fn=...)`, one duplex pipe each, own HTTP session). The orchestrator is the only writer of the event log.

**Randomized phase, pair-synchronous.** For `i = 1, 2, ..., N_P`: enroll pair `i`; draw and durably log `R_i`; send position 1 to worker 0 and position 2 to worker 1 (in that order, without waiting in between); both episodes run concurrently against the server(s); each is revealed when its worker returns the final record (after hidden-test verification). Pair `i+1` is enrolled only after both episodes of pair `i` are revealed and the monitor has been evaluated. There is no arrival clock (closed loop).

Why pair-synchronous rather than a sliding window: with a sliding window on one GPU, the final record of pair `i-1` (its wall-clock latency, possibly a load-induced timeout) can depend on the coin of pair `i`, because a `self_test_repair` neighbour occupies the second slot about 4.5 times longer than a `single_shot` neighbour. The filtration `F_{i-1}` contains that final record, so conditioning on it would be informative about `R_i` and `E(Z_i | F_{i-1})` would no longer be the fair-coin average; this is the warning of `paper/asynchronous.tex:72-76` and the root's request to "specify the target and shared-resource assumptions first". Under the pair-synchronous rule `R_i` does not exist while pair `i-1` runs, so cross-pair interference through the coin is excluded physically, not by assumption. The price is throughput (the fast worker idles until its partner finishes), which is irrelevant here: a full T1 horizon of 568 pairs takes about 3 hours. What is kept from the coordinator's intent: two concurrent workers, real reveal timestamps, reveals out of arrival order (position 2 is revealed before position 1 whenever it holds the faster episode), and early certificates (7.6). With two workers a sliding window would not give a materially richer asynchronous study either: at most two pairs can be incomplete at any time (R4: arrivals started at the decision are about 2 tau + 2 to 5).

**Post-decision phase, work-conserving.** After a decision the remaining arrivals of the frozen order are taken one at a time by whichever worker is free; both run the decided arm.

### 5.2 Server configuration

As in 2.2; identical for the whole trial including the post-decision phase. A supervisor polls `/health` every 5 s; on process exit or 3 consecutive failures it logs `server_down`, restarts with the identical argv, logs `server_restarted`, and compares `/props` with the values of `server_started` (difference: `trial_aborted`, 6.4 row 6). `/metrics` is scraped at trial start, at every anchor, immediately before any planned stop, after every restart, and at the end.

### 5.3 Sampling parameters (D17)

Every request body contains exactly: `model` (alias), `messages`, `temperature: 0.7`, `top_p: 0.95`, `top_k: 0`, `min_p: 0.0`, `typical_p: 1.0`, `repeat_penalty: 1.0`, `presence_penalty: 0.0`, `frequency_penalty: 0.0`, `mirostat: 0`, `max_tokens: 1024`, `seed` (5.4), `cache_prompt: false`, `stream: false`, `verbose: true`. Temperature, top_p and the completion cap are the pilot's values; `top_k: 0` and `min_p: 0.0` disable samplers the MLX pilot did not have, so that llama.cpp's command-line defaults (temperature 0.8, top-k 40, min-p 0.05) can never leak in. Both arms and both models use the same values. "1,024-token completion cap per call"; truncation (`finish_reason == "length"`) is counted per request and is not an error. `cache_prompt: false` removes slot-dependent prefix reuse from latency. Statements about what is sent are generated from a captured request of the frozen harness, never from documentation. Requests are seeded, but regeneration is not bit-identical (continuous batching); no bit-reproducibility is claimed.

### 5.4 Per-request seeds (D18)

The pilot's seed formula collided across units (2,960 distinct values for 4,728 calls). New rule, unique by construction and a function of indices only (never of the arm or the coin):

```
idx  = ((((e * 4096 + arrival) * 4 + attempt) * 8 + call_index) * 4 + try_index)
seed = (idx * 2654435761 + 40503) mod 2**31
```

with `e` in 1..4 the trial number, `arrival` <= 4095, `attempt` in 1..3, `call_index` in 0..7 (order of `chat()` invocations within the attempt), `try_index` in 0..3 (HTTP retry). The multiplier is odd, so the map is a bijection modulo 2^31; all seeds are distinct and below `0xFFFFFFFF` (llama.cpp's "random" sentinel). A unit test enumerates the full grid. Smoke and calibration requests use `e = 0`. The seed sent and the seed receipted are both logged. The seed that `run_episode` computes internally is ignored by the injected client.

### 5.5 Timeouts and retries (D19)

| parameter | value | note |
|---|---|---|
| `request_timeout_s` | 180, or `30 * ceil(4 * c_max / 30)` if that is larger, where `c_max` is the slowest call of the out-of-design calibration (5.8) | fixed before the freeze; identical for both arms |
| `max_connection_retries` | 2 (three tries), backoff `min(2 * (k + 1), 10)` s, only for connection errors and timeouts | as in the pilot; HTTP 4xx/5xx and malformed bodies are not retried |
| `server_recovery_s` | 180 | how long a try may wait for a supervised restart |
| `sandbox_timeout_s`, `sandbox_cpu_s` | 10, 10 | pilot values |
| `sandbox_output_cap_bytes` | 65,536 | pilot value |
| `max_repair_rounds` | 2 | pilot value |
| `episode_hard_cap_s` | 1,800 | watchdog; exceeding it is handled as a dead worker (6.4 row 10) |
| `max_attempts` | 3 | an attempt is re-run only if it never returned to the orchestrator |

There is **no episode-level retry**: a completed episode is never re-run, whatever its outcome; the canonical record of an arrival is the first attempt that returns. Every try of every request of every attempt is logged with its usage or with `usage_known: false` (11.5).

### 5.6 Sandbox

`experiments/local_stream/sandbox.py` unchanged: macOS Seatbelt profile (profile SHA-256 recorded per episode), fresh temporary directory per execution, process-group kill, CPU and wall limits, output cap. macOS enforces no memory cap; this is disclosed, `W` is kept at 2, and RSS is sampled in `server_health`. `TMPDIR` is set to the neutral path `/private/tmp/labsbx` so that no account name enters any record. Success = hidden checks exit 0 AND the per-call nonce sentinel is seen (`verify.py:78-82`).

### 5.7 Sampler receipt and served-model assertion

For every response the client compares `__verbose.generation_settings` with the request for the frozen key list `receipt_keys` (seed, temperature, top_k, top_p, min_p, typical_p, repeat_penalty, presence_penalty, frequency_penalty, mirostat, n_predict; exact key names are fixed by the receipt smoke test at the pinned commit). Integers must be equal; floats must agree within 1e-6 (the server echoes float32). The `model` field must equal the arm's alias. A mismatch is handled by 6.4 rows 12 and 13 (episode revealed, then `trial_aborted`); it is never a silent continue and never a dropped episode. The receipt path is first proven against the stub server in the unit tests and then against the real server in the smoke test, both before the freeze.

### 5.8 Pre-freeze out-of-design phase

Tasks: the six timing-pilot tasks of 3.2 and four hand-written prompts stored in the config; never a design task. Purpose: receipt smoke test per server; chat-template check of the T3 candidate; calibration of call durations at concurrency 1 and 2 for both workflows and both models (sets `request_timeout_s` by the rule of 5.5; checks memory); end-to-end rehearsal of the orchestrator, anchor and verifier. All of it is written to a separate chain under `results/live_ab/_prefreeze/` with `phase` in {`SMOKE`, `TIMING_PILOT`}; its tokens are reported separately and excluded from every trial total. Success outcomes of these runs are not inspected for any design choice; the only quantities used are durations, memory and receipt equality.

---

## 6. Outcomes, hierarchy, tolerances, failure rules

### 6.1 Episode endpoints

| field | definition |
|---|---|
| `success` in {0, 1} | archived verifier label: hidden checks exit 0 and sentinel seen; verifier timeout, missing sentinel, empty or unextractable code, and every failure path of 6.4 give 0. It is not semantic correctness and not an independent re-adjudication. |
| `latency_s` | as in `agent.py:247`: wall time (`perf_counter`) from the start of `run_episode` to the existence of the final candidate program; includes all model calls, connection retries and backoff, waiting for a supervised server restart, and the agent's own test executions; excludes hidden-test verification and model loading. For an arrival with aborted attempts, the certified elapsed time of each aborted attempt (7.6) is added, so that the endpoint clock never restarts. In every table the field is named `latency_s_w2sync` ("workflow latency under pair-synchronous two-worker load on this host") and is never pooled with the pilot's sequential `latency_s` nor with post-decision latencies. |
| `completion_tokens` | sum of server-reported completion tokens over all responses of the arrival, including aborted attempts; requests without a response contribute their known count (none) and are listed under unknown usage (11.5). |
| recorded, not scored | prompt tokens, number of model calls, failed calls, self-test executions (`n_self_test_executions`) and verifier executions (`n_verifier_executions`) as separate fields, repair rounds, `finish_reason` per request, truncation flag, verifier return code, sentinel flag, verifier seconds, `timed_out`, `error_class`, `infra_flag`, overlap seconds with the partner episode, per-call `predicted_per_second` and `id_slot`. |

The evaluation horizon of an episode is fixed: the workflow runs to its own end under the caps of 5.5; nothing terminates it early.

### 6.2 Hierarchy (D6)

| trial | tier 0 | tier 1 | tier 2 |
|---|---|---|---|
| T1, T2, T4 | `success`, higher better, tolerance 0 | `latency_s`, lower better, relative tolerance 0.10 of the larger value | `completion_tokens`, lower better, relative tolerance 0.10 of the larger value |
| T3 | same | same | none |

Rule of `winstats.compare` (`src/winstats.py:25-48`): for tier k, `tol = relative_tolerance * max(|a_k|, |b_k|)`; the tier is decisive iff it is the first with `|a_k - b_k| > tol` (strict; exact equality is a tie) and the pair is eligible for it. Eligibility: tier 0 always; tiers 1 and 2 only if both episodes succeeded. Joint failure is a tie. The 10% tolerance is an operational preference, not a significance test. T1, T2, T4 use the hierarchy the root accepted for the coding stream (`results/open_coding/collection_config.json`; `paper/open_coding_appendix.tex:42-56`). T3 drops the token tier because native token counts of two tokenizers are not a common cost unit (R2 item 80); tokens of each model are reported separately and never compared as cost. Under the pair-synchronous regime both episodes of a pair start together on the same GPU, so the latency comparison inside a pair is made under a shared load; this is part of the endpoint definition.

The kernel is never refitted; its code hash is in the freeze bundle and in every `monitor_update`.

### 6.3 Pair scores

With `vals(r) = [success, latency_s, completion_tokens]` (T3: first two) and `both = success_cand and success_inc`:

```python
z, tier = compare(vals(cand), vals(inc), tiers, [True, both, both])   # Z_i in {-1,0,1}; positive favours the candidate
d = int(success_cand) - int(success_inc)                              # D_i in {-1,0,1}
```

All values are finite by construction (6.4), as `compare` requires.

### 6.4 Failure-to-outcome rules (fixed in advance; intention to treat)

Principle: every arrival with a durable assignment yields exactly one revealed outcome under that assignment. A completed episode is never re-run. An attempt is re-run only when it never returned, under the same arm, never with a new coin. All usage of every attempt and try is logged; unknown values are `null` with a reason, never 0.

| # | event | outcome rule | accounting |
|---|---|---|---|
| 1 | request timeout | retry per 5.5; after the last try the call raises; `run_episode` records the error and grades the last candidate that exists; `success = 0` if none | `llm_error` per try, `usage_known: false`; the server cancels generation on disconnect; tokens bounded by the `/metrics` delta |
| 2 | HTTP 4xx/5xx | not retried; same consequence as row 1 | `llm_error` with status |
| 3 | HTTP 200 without `usage` or `timings`, or non-JSON | treated as row 2 (`malformed`); no token estimation path exists | `llm_error` |
| 4 | `finish_reason == "length"` or `truncated` | not an error; text used as is; `truncated_any` recorded | full usage known |
| 5 | server crash or hang | supervised restart with identical argv; the client waits up to `server_recovery_s`; waiting time is inside `latency_s`; if recovery fails the call fails as row 1; `infra_flag = true` on both episodes of the pair in flight | `server_down`, `server_restarted`; counters lost across a crash reported as an unreconciled window |
| 6 | restarted server differs in props, slots, alias or build | `trial_aborted`; nothing further is dispatched; everything revealed so far stays reportable | anchor |
| 7 | sandbox wall or CPU kill, fork refusal, permission error | in a self-test: a failed self-test (triggers repair); in verification: `success = 0`, `timed_out` recorded | execution seconds |
| 8 | sentinel missing with exit 0 | `success = 0` | `sentinel_seen` |
| 9 | empty or unextractable code | `success = 0` | record |
| 10 | worker dies, or `episode_hard_cap_s` exceeded (worker killed) | `attempt_aborted`; new worker; same arrival, same arm, `attempt + 1`; after `max_attempts` the arrival is revealed with `success = 0`, `error_class = harness_abort`, `latency_s` = sum of certified elapsed times, tokens = known tokens; `infra_flag = true`; the partner episode is not disturbed | calls seen so far are already logged; unknown tail bounded by `/metrics` |
| 11 | orchestrator crash, power loss, operator stop | resume per 12.3; every open attempt gets `attempt_aborted(orchestrator_restart)` and is re-run under the same arm, possibly without a concurrent partner (`partner_concurrent: false`, `infra_flag = true`) | `invocation_started.resumed` |
| 12 | sampler receipt differs from the request | the episode completes and is revealed; then `trial_aborted(receipt_mismatch)` before the next dispatch | `receipt_mismatch` list |
| 13 | served `model` alias differs | as row 12 | |
| 14 | clock step or sleep | logged `clock_anomaly`; overlapping episodes get `infra_flag` | |
| 15 | disk full or log write error | dispatch stops at once (an unloggable coin may not be used); running episodes finish; their content-addressed records are recovered as orphans on resume | |
| 16 | memory pressure | none beyond the sandbox kill; disclosed | RSS samples |
| 17 | monitor exception | dispatch pauses (`trial_paused`); no decision is taken by hand; after an amendment (12.2) the monitor is replayed from the log, which is legitimate because it is a pure function of logged events | |

Primary analysis keeps every pair, including all `infra_flag` pairs. A sensitivity read-out without them is labelled descriptive in advance (9.3).

---

## 7. Pairing under out-of-order reveals, and the exact filtration

### 7.1 Pairing rule

Pairs are the consecutive arrivals `(2i-1, 2i)` of the frozen arrival order (3.6); positions are fixed before the orientation is randomized. Nothing about a pair depends on reveal order, completion time or any outcome. Matching by completion order is never used.

### 7.2 Filtrations (enrollment order)

Let `W_i` be the complete fixed-horizon records of both episodes of pair `i` (all attempts, tries, timestamps, outcomes).

- `F_0` = sigma(roster, strata, arrival order and pairing, frozen protocol: hierarchy, tolerances, caps, systems and model hashes, levels, stake grid, margin, `n_min`, `N_P`, seed rule). In the design-based reading `F_0` also contains, for every pair and each of its two orientations, the potential records and reveal paths. **`F_0` contains no coin and no quantity from which a coin can be computed.**
- `H_i` = `F_{i-1}` joined with the information used to enroll pair `i` (its stratum and task identities). `P(R_i = 1 | H_i, potential records of pair i) = 1/2`.
- `F_i` = `F_{i-1}` joined with sigma(`R_i`, `W_i`).

Consequences, in the root's terms: the current pair's coin `R_i` is **not** in `F_{i-1}`; it enters at `F_i`. Earlier coins `R_1..R_{i-1}` are in `F_{i-1}`. Later coins are in no `F_j`, `j <= i`, and do not physically exist while pair `i` runs (4.2 invariant ii). The scores `Z_i`, `D_i` are `F_i`-measurable with the predictable range [-1, 1]. Targets: `mu_i = E(Z_i | F_{i-1})`, `nu_i = E(D_i | F_{i-1})`, running averages `mubar_n = n^{-1} sum_{i<=n} mu_i` and `nubar_n` likewise.

The evaluator's real information at calendar time t (`G_t`: reveal order, timestamps, partial traces) is a different filtration. No martingale argument is made in `G_t`. Every live decision at `(n, t)` implies a statement about the enrollment-order process, where the error bound lives (`paper/asynchronous.tex:111-127`), so the live stopping time needs no stopping-time property with respect to `(F_i)`.

### 7.3 "Reveal order" made precise (D14)

The event log is written in reveal order with real timestamps. The monitor is re-evaluated at log events, but its statistic is always a function of an **enrollment-order prefix**: the live decision uses the completed prefix `N_c(t)` = number of leading pairs whose two episodes are both revealed (`prop:delay`, `paper/theory.tex:535-563`: `N(t)` may be any data-dependent integer such that the first `N(t)` pairs are complete). Scores are never accumulated in completion order and a pending pair is never skipped. This is the meaning given here to the coordinator's phrase "the monitor consumes outcomes in reveal order"; literal completion-order scoring falsely deployed in 1000 of 1000 null runs of the root's simulation (`paper/async_results.tex:18-21`).

### 7.4 Concurrency inside a pair and the causal reading (CONFIRM C8)

`thm:pair_id` is stated with "no interference between the two positions". Under pair-synchronous execution the two episodes of a pair do share the GPU. Because a pair has only two possible assignments, potential outcomes indexed by (position, arm) are the same objects as potential outcomes indexed by the pair's orientation: `Y_{i1}^{cand}` is by definition the record of position 1 when position 2 concurrently runs the incumbent, which is the only way the design can ever produce it. Consistency therefore holds, the proof of `thm:pair_id` goes through verbatim, and

`E(Z_i | H_i, potential records) = m_i = (1/2) { h(Y_{i1}^{cand}, Y_{i2}^{inc}) + h(Y_{i2}^{cand}, Y_{i1}^{inc}) }`, hence `mu_i = E(m_i | F_{i-1})`.

The estimand is thus explicitly "preference between the two systems when one episode of each runs side by side on this host", not latency of either system running alone or under a production load. Carry-over from earlier pairs (thermal state, operating-system caches) may change the potential records of pair `i`; this is allowed, because those are functions of the history in `H_i`. What must not happen, a dependence of pair `i-1`'s record on `R_i`, is excluded physically (5.1).

Assumptions that remain for the causal reading, all listed in the report: the OS entropy bit is fair and independent of the pair's potential records; execution is nonanticipating; systems are fixed for the whole trial; the operator does not act on coins. For T4 the two arms are one system, so `mu_i = 0` exactly for any hierarchy and any load.

### 7.5 Fallback if C2 is declined (sliding window, W = 2)

If the coordinator requires a work-conserving sliding window in the randomized phase, everything else in this protocol stays, with these changes: pair `i+1` is enrolled and its coin drawn as soon as a worker is free; the only guarantee claimed is the history-conditional running-mean guarantee of 8.5, which needs no interference assumption; the fair-coin reading of `mu_i` is stated only "under the additional assumption that a pair's final record does not depend on later pairs' orientations"; every episode's overlap with other episodes and their arms is logged; a load-invariant sensitivity hierarchy (success > completion tokens) is reported descriptively. The drafter does not recommend this.

### 7.6 Enclosures for the pending pair (used only by the comparator of 8.6)

Enclosures are logical certainties derived from worker-stamped facts, never predictions, and never widen (`paper/asynchronous.tex:33-56, 247-300`).

- Pending `success` lies in {0, 1}.
- Certified elapsed time of a pending attempt: `ell = max_e (t_e - t_c1)`, where `t_c1` is the worker's monotonic time at entry into the first `chat()` call of the attempt and `t_e` runs over the worker's monotonic send and receive stamps of all its logged request events. Validity: `latency_s = t_final - t_0` with `t_0 <= t_c1` (the clock starts before the first call) and `t_final >= t_e` (the final candidate cannot exist before the last response, or exception, that has been seen). Orchestrator timers and message arrival times are never used. For an arrival with aborted attempts the certified elapsed times add (6.1), so a certificate issued before an abort stays valid.
- One episode revealed (arm `r`, `sgn = +1` if `r` is the candidate, else `-1`; success `s_r`; latency `L_r`), partner pending with certified `ell`:
  - `s_r = 0`: `Z_i` and `D_i` both lie in {0, `-sgn`}.
  - `s_r = 1`: `D_i` lies in {0, `sgn`}. If `0.9 * ell > L_r + 1e-9`, then `Z_i = sgn` with certainty (if the partner fails the revealed episode wins at tier 0; if it succeeds, its latency `x >= ell` satisfies `x - L_r > 0.1 x`, so the revealed episode wins at tier 1). Otherwise `Z_i` lies in [-1, 1].
- Neither revealed: [-1, 1] for both scores.
- No certificate is ever derived from tokens (that would need an upper bound on the partner's latency, which the design does not provide).

This is the worked example of `paper/asynchronous.tex:283-292` in the present hierarchy: in T1 and T2 the composite sign of a pair is usually certified when the slow episode sends its second or third request, while the success-difference enclosure stays one-sided until the reveal.

---

## 8. Monitoring rule

### 8.1 Statistics at a completed prefix n

`P_n = #{i <= n: Z_i = +1}`, `M_n = #{i <= n: Z_i = -1}`, `Pd_n`, `Md_n` likewise for `D_i`. With `L = winstats.betting_log_e_ternary` (grid `numpy.geomspace(1e-4, 0.99/(1 + c), 40)`, equal weights, `bets = 40`, file SHA-256 56955ce0...):

| gate | null about the running target | statistic | crossing |
|---|---|---|---|
| net benefit (NB) | `mubar_n <= 0` | `L(P_n, M_n, n, threshold=0.0)` | `>= log(1/alpha_NB)` |
| success non-inferiority (S) | `nubar_n <= -delta` | `L(Pd_n, Md_n, n, threshold=-delta)` | `>= log(1/alpha_S)` |
| harm (H) | `mubar_n >= 0` | `L(M_n, P_n, n, threshold=0.0)` (the score `-Z`) | `>= log(1/alpha_H)` |

Comparisons are made in float64 as `loge >= numpy.log(1.0/alpha_j)`.

### 8.2 Looks (D13)

One look at every completed pair `n = N_c(t)` with `n >= n_min = 20`, in increasing `n`. A minimum is not needed for validity (the bounds are uniform over all n) but is frozen. No retained crossing: only the current prefix counts (the pilot's harm wealth was above 20 at pairs 14 and 24 and below it until pair 48, which is why the decision and its prefix are logged at the instant of the crossing). No running intersection of any band.

### 8.3 Decision rule and action map (D10, CONFIRM C3, C4)

At look n:

1. if the H gate crosses: decision `RETAIN_INCUMBENT (unfavourable composite signal)`;
2. else if the NB gate and the S gate both cross at this same n: decision `DEPLOY_CANDIDATE`;
3. else continue; if `n = N_P`: `ABSTAIN_AT_HORIZON`.

(Harm has precedence if both could ever hold at once.) A `RETAIN` decision is a statement about the composite only: it is not success harm, not safety harm and not an approval of the incumbent in the reverse direction. The paper's rule has no harm or futility test; the harm gate used here is `prop:bet_running` applied verbatim to the adapted score `-Z_i` in [-1, 1] with `c = 0`; what is new is only its use as a stopping action, which the root is asked to confirm (C4).

### 8.4 Levels (D11, CONFIRM C5)

| trial | `alpha_NB` | `alpha_S` | `alpha_H` | thresholds on E | sum |
|---|---|---|---|---|---|
| T1, T2, T4 | 0.005 | 0.04 | 0.005 | 200, 25, 200 | 0.05 |
| T3 | 0.05/3 | 0.05/3 | 0.05/3 | 60, 60, 60 | 0.05 |

Reason for the unequal split in T1, T2, T4: any allocation with sum at most alpha is valid under `thm:drift_gate`; the pilot shows a very large composite effect (net benefit about 0.5 in absolute value, crossing at a few dozen pairs at any level) and a success component whose certification is the bottleneck, so the budget is spent where it is needed. Planning effect: about +8 to +10 points of deploy probability in T1 and about 10 pairs of extra delay of the T2 harm crossing (10.3). The allocation is pilot-informed and disclosed as such; it was fixed before any design-task outcome. T2 uses the identical rule with the arms swapped and T4 is the control of that same rule. T3 has no pilot basis for an asymmetric split and uses equal thirds.

Across trials: each trial is its own experiment about its own candidate with its own 0.05; no selection among the four is made and no combined claim is formed. By the union bound the probability of at least one false decision in the program is at most 0.20 (`paper/theory.tex:484-492`), and that is how it is reported. The log E values at the decision prefix are reported so that a reader can apply a program-level split (per-trial 0.0125) descriptively.

### 8.5 Guarantee claimed and the theorems it rests on

For each trial, with `(F_i)` of 7.2, scores adapted and in [-1, 1], and stakes, weights, thresholds and levels fixed before the first design-task outcome:

- `P{ exists n: DEPLOY at n, and (mubar_n <= 0 or nubar_n <= -delta) } <= alpha_NB + alpha_S`   (`thm:drift_gate`, betting clause, `paper/theory.tex:494-521`, via `prop:bet_running`, `paper/theory.tex:408-436`);
- `P{ exists n: RETAIN at n, and mubar_n >= 0 } <= alpha_H`   (`prop:bet_running` for `-Z`);
- hence `P{ any false decision statement in the trial } <= 0.05`.

The arrivals are a fixed permutation of a finite roster, which does not give a constant conditional mean (`reviews/round9_open_model_evidence_audit.md:75-81`); therefore the full-level stationary rule `thm:iut` and retained crossings are not used (D25). No stationarity, independence, identical distribution or exchangeability is assumed; task composition, machine state, serial dependence and informative delay are allowed. The decision is a statement about the running average of history-conditional pair means **at the logged prefix**: not about the latest arrival, a future workload, the all-pairs roster functional, a task superpopulation or production traffic (`paper/theory.tex:524-531`). The interpretation of `mu_i` as the fair-coin orientation average of pair `i` additionally uses `thm:pair_id` and section 7.4. The bounds above are joint for the three processes of a trial because the levels were split; they are not a joint confidence region for effect sizes.

### 8.6 Matched asynchronous comparator (never drives traffic)

At every log event of a pending pair (request sent, response received, episode revealed) the monitor also evaluates the enrolled prefix `N_e(t)` (= `N_c(t)` or `N_c(t) + 1`), replacing the pending pair's scores by their enclosures: lower enclosures in the NB and S gates, the upper enclosure in the H gate, all at the same prefix, same thresholds, `N_e >= n_min`. The first event time `t_enc` at which this comparator would cross, the time `t_dec` of the live completed-prefix decision, and their difference are recorded. Both times are measured on a path that no decision had yet altered, so neither is a replay; `t_enc <= t_dec` always, because lower-enclosure wealth is dominated by complete-data wealth at the same prefix. Status of the comparator's own error control: for the normal-mixture construction it is `thm:async_cs` with the split of `paper/asynchronous.tex:381-388`; for betting under the running-average null it follows from pathwise domination plus `prop:bet_running`, a one-line corollary that is not written in the paper. It is therefore reported as a measured timing comparison only, with no error-control claim, unless the root confirms the corollary (CONFIRM C16).

### 8.7 Traffic after a decision; in-flight episodes; post-decision phase (D15, D16)

- On a crossing the orchestrator appends `decision` (durable), requests an immediate anchor, appends `traffic_switch` and changes phase to `decided_candidate` or `decided_incumbent`. From then on no coin is drawn; every remaining arrival (both positions of pairs `n+1..N_P` in order, then the unpaired leftovers) receives `arm_assigned_by_decision` and runs under the decided arm with two work-conserving workers. The switch latency (crossing detected to first non-randomized dispatch) is measured.
- Under 5.1 and 7.3 no episode is in flight at a decision. If one ever is (only after a crash recovery), it runs to its frozen horizon, is revealed with `post_decision_inflight: true`, counts in the exposure ledger and is excluded from monitoring. No episode is ever terminated early, so the endpoint definition never changes for a pending episode (`paper/asynchronous.tex:396-400`).
- The post-decision phase is an **operational record**: single-arm, outside the monitored process, no inference, never pooled with pre-decision data, never called validation.
- `ABSTAIN_AT_HORIZON`: the trial ends when pair `N_P` completes; leftovers are not executed.

### 8.8 Maximum horizon

`N_P` pairs from `arrival_order_T<e>.json`. No extension, no second pass, no rerun, no reselection of model or seed. A failed or abstaining trial is reported, not repeated; a repeat would be a new trial with its own frozen protocol and level.

### 8.9 Secondary construction, and the complete fallback if C3 is declined

At every look the harness also logs the split normal-mixture confidence sequence exactly as the root applied it to the pilot (`normal_mixture_radius(n, alpha, rho=100.)`, `V_n = n`, clipped to [-1, 1], no running intersection): a two-sided NB band at level `a_NB2` and a success-difference band at level `a_S2`, with `(a_NB2, a_S2)` = (0.01, 0.04) in T1, T2, T4 and (1/30, 1/60) in T3 (the NB band is two-sided, so its level is `alpha_NB + alpha_H`). Under the betting driver these bands are the prespecified **secondary** construction: they are valid at the stopping prefix because they are time-uniform (`thm:normal_cs`), and they are what is displayed as interval estimates of `mubar_n` and `nubar_n`.

If the root declines betting as the live driver, the frozen config sets `driver = "normal_mixture"` and the rule becomes: `RETAIN` iff the NB upper endpoint is below 0; `DEPLOY` iff the NB lower endpoint is above 0 and the success lower endpoint is above `-delta`, at the same completed prefix, `n >= 20`; `delta = 0.15`; guarantee `thm:normal_cs` + `thm:drift_gate` with total level 0.05; the betting statistics are then logged as secondary. The expected consequence is stated in advance: under this driver `delta = 0.10` is not expected to be certified (planning probability at most 0.2) and the T2 crossing comes later (R4: median pair 74 to 79 at comparable levels, against about 40 to 60 for betting).

### 8.10 Descriptive side read-outs logged at every look (never decide anything)

The S-gate log E at `delta` in {0.03, 0.05, 0.10, 0.15}; the truncated "success-only" composite (tier 0 alone) with the same NB and H gates, as the prespecified component-rule comparator (R2 item 24); share of pairs decided at each tier; all read-outs by stratum family (S1, S2).

---

## 9. Estimands, analyses and hypotheses

### 9.1 Primary estimands (one pair of targets per trial)

`mubar_n` and `nubar_n` of 7.2: the running averages, in enrollment order, of the history-conditional means of the hierarchical pair score and of the success-difference pair score, at the decision prefix `n = tau` (or at `N_P` if no decision). Under 7.4, `mu_i` is the conditional expectation of the orientation-averaged within-stratum preference `m_i`, and `nu_i` that of the average same-task success effect of the two tasks of pair `i`. Every table caption names this target. Not targeted: `theta_N` (all-pairs roster functional), any superpopulation mean, any same-task preference, any future workload.

### 9.2 Primary analysis = the live decision

The primary result of a trial is the logged decision (`DEPLOY_CANDIDATE`, `RETAIN_INCUMBENT`, `ABSTAIN_AT_HORIZON`), its prefix `tau`, its calendar time, and the three log E values at `tau` against their frozen thresholds, with the guarantee of 8.5. It is recomputed from the event log alone by the independent verifier and by the deterministic builder; the recomputation must reproduce every `monitor_update` and the `decision` exactly. There is no second, post hoc primary analysis.

### 9.3 Strict separation of statements

**Design-based (valid from the coin, boundedness and the frozen rule only):** the decision and its error bound (8.5); the secondary split normal-mixture bands at `tau` or `N_P` (8.9), each with its own level and the explicit sentence that the pair of bands is jointly valid at level 0.05 only because the levels were split; the fair-coin interpretation of the targets under the listed assumptions of 7.4; the exact count of rejected-arm exposures avoided (9.4); in T4, exactness of the null. Coin balance (number of pairs with `R_i = 1`) is reported as a description of the draw, not tested.

**Descriptive only (no interval, no test, never feeding a decision):** observed net benefit, success difference, win/tie/loss shares, win ratio and win odds (`winstats.summary`) at the stopping prefix, with the sentence that point values at a data-dependent stopping time are biased by optional stopping; per-arm counts, means and medians of latency, tokens, calls, truncations, failures; tier shares; by-stratum read-outs; the sensitivity hierarchies (success only; success > tokens for T1, T2, T4; primary hierarchy without `infra_flag` pairs); the side read-outs of 8.10; `t_enc`, `t_dec` and switch latency (measured quantities of this run); everything from the post-decision phase; the projection of 9.4(iii). The words "significant", "equivalent", "non-inferior" (other than for a crossed S gate) do not appear.

**Not produced at all:** t, Welch, cluster-t, bootstrap or delta-method intervals; win-ratio confidence sequences; fixed-mean (iid-roster) readings of the e-values; any function of `src/wincs.py`; any comparison with, or pooling of, pilot episodes.

### 9.4 Exposure and saving quantities (D24)

Let `tau` be the decision prefix, `M = N_P - tau` the number of pairs not yet enrolled.

1. **Exact design quantity:** "exposures to the rejected arm avoided relative to the prespecified fixed-horizon randomized design" = `M` (each remaining pair would have contained exactly one episode of each arm; under the decision all `2M` remaining paired arrivals run the decided arm). It needs no counterfactual outcome. Also reported: `M / N_P`.
2. **Measured totals:** wall-clock time, busy time per worker, prompt and completion tokens (successful and failed calls, unknown-usage calls counted separately), by phase and arm, from the exposure ledger.
3. **Projection, labelled as such:** `M x (mean pre-decision latency of rejected-arm episodes - mean pre-decision latency of decided-arm episodes)`, same for tokens; caption "projection from pre-decision means under mixed pair-synchronous load; not a measured saving".

### 9.5 Hypotheses and what counts as support

| trial | prespecified expectation | support | everything else |
|---|---|---|---|
| T1 | (a) NB gate crosses; (b) guarded deployment of `single_shot` within the horizon | (a) NB log E >= log 200 at some look; (b) the `DEPLOY_CANDIDATE` decision event | `ABSTAIN_AT_HORIZON` = "the success gate at margin delta was not certified by this rule on this stream" (the most likely non-supporting outcome, probability about 0.15 to 0.6, section 10); `RETAIN` would contradict the pilot and is reported as observed |
| T2 | the rule rejects `self_test_repair` | `RETAIN_INCUMBENT` | abstention or deployment reported as observed |
| T3 | none (two-sided, outcome unknown) | not applicable | each of the three outcomes is reported with the same prominence |
| T4 | no decision | `ABSTAIN_AT_HORIZON` | a decision has probability at most `alpha_NB + alpha_H = 0.01` under the exact null and is reported as that event; one A/A path is never described as evidence of calibration |

---

## 10. Power analysis and the resulting choice of margin and horizon

### 10.1 What was simulated

R4 (`R4_power_analysis.md`, `power_sim.py`, seed base 20260919, 20,000 replicates per main cell, maximum Monte Carlo standard error 0.0035): plug-in replay of the 1,182 pilot episodes; random arrival order; fair coin; outcome of a task under an arm = its single pilot outcome; pair scores by `winstats.compare` exactly as the root's builder (the script first reproduces the root's 69/18/208 pilot counts); monitors = `winstats.betting_log_e_ternary` and `winstats.normal_mixture_radius` at same-prefix first crossing; cells: 591 tasks permuted (295 pairs), 591 and 1,138 draws with replacement (295 and 569 pairs). Pilot facts: success 433/591 in both workflows, same-task discordance 40 versus 40 (paired standard error of the success difference 0.0151), mean latency 2.80 s versus 12.48 s; cross-task pairs have a nonzero success difference in 39% of pairs.

### 10.2 R4 results that decide the design

- **Margins 0.03 and 0.05 are not certifiable at any feasible single-exposure size.** T1, betting, true success difference 0: P(guarded deploy) = 0.007 to 0.030 (delta 0.03) and 0.024 to 0.075 (delta 0.05) on 591 tasks; 0.022 to 0.056 and 0.089 to 0.169 on 1,138 tasks. Pairs for 80% power: 6,136 to 7,537 (delta 0.03), 2,274 to 2,740 (0.05), 567 to 702 (0.10), 259 to 318 (0.15). The normal-mixture radius reaches 0.03 only at 12,094 pairs (the root's own number).
- **Feasible:** delta 0.15 on 591 tasks (betting 0.76 to 0.88); delta 0.10 only on about 1,138 tasks (0.67 to 0.79); delta 0.10 on 591 tasks is 0.26 to 0.41.
- **Normal mixture as driver:** on 591 tasks at most 0.23 even at delta 0.15; on 1,138 tasks 0.64 to 0.84 at delta 0.15 and 0.06 to 0.19 at delta 0.10.
- **Sensitivity to a truly worse candidate** (alpha/3, delta 0.10, 1,138 tasks): 0.667 at equal success, 0.374 at -2 points, 0.250 at -3 points; these shifts are 1.3 and 2.0 paired standard errors of the pilot's success difference, so neither is excluded by the pilot.
- **T2:** harm stop in 100% of replicates; betting median pair 34 to 42 (interquartile range about 24 to 59); normal mixture 64 to 79; expected candidate exposures avoided 84 to 93% (betting). The harm signal comes from the latency tier, not from success.
- **T4:** any-decision rate at most 0.020 (no split) and 0.006 (alpha/3), far below nominal; one A/A path shows "no crossing" with probability at least 0.98.
- **T3 (analytic):** with about 569 pairs, roughly 80% power for |net benefit| >= 0.15 to 0.18; the success gate sees `delta + Delta`, so delta 0.10 is certifiable only if the candidate model is at least as successful as the incumbent.
- `n_min` 10 versus 20 is immaterial; per-arrival coins lose 3% of arrivals and 0.5 to 2 points of power.

### 10.3 Drafter's supplementary planning simulation for the chosen configuration

R4 did not simulate fresh-run variability, stratified pairing or an unequal split. `P5_supp_power.py` (4,000 replicates per cell, standard error at most 0.008, 119 s, 1.9 GB) uses a latent model instead of replaying pilot outcomes: each task has a success probability common to both workflows (true difference 0), Beta(0.386, 0.141) fitted by moments to the pilot read as two exchangeable runs per task (mean 433/591, both-solved share 393/591), updated by the task's pilot pattern; "pilot predictiveness" w = 0.7 shrinks probabilities toward the mean to mimic a weaker link between the MLX pilot and the GGUF stack; S2 tasks have no pilot data and mean success 0.60 or 0.45; both-succeed pairs are won, tied, lost by the cheap candidate with the pilot shares 0.957 / 0.013 / 0.030. On the cells that overlap with R4 it agrees with R4 (unstratified, 295 pairs, equal thirds: 0.29 at delta 0.10 and 0.76 at delta 0.15, against R4's 0.26 to 0.27 and 0.76 to 0.78).

T1, P(guarded deploy), betting driver, `n_min = 20`:

| roster (pairs) | pairing | levels | delta | equal success: w=1, S2 0.60 / w=1, S2 0.45 / w=0.7 | candidate -2 points | candidate -3 points |
|---|---|---|---|---|---|---|
| EXT (568) | **stratified** | **(.005, .04, .005)** | **0.10** | **0.86 / 0.85 / 0.79** | 0.62 / 0.63 / 0.53 | 0.46 / 0.50 / 0.40 |
| EXT (568) | stratified | equal thirds | 0.10 | 0.78 / 0.77 / 0.69 | 0.50 / 0.50 / 0.40 | 0.35 / 0.38 / 0.30 |
| EXT (568) | unstratified | (.005, .04, .005) | 0.10 | 0.70 / 0.65 / 0.71 | 0.45 / 0.44 / 0.46 | 0.33 / 0.35 / 0.33 |
| EXT (568) | unstratified | equal thirds | 0.10 | 0.59 / 0.53 / 0.59 | 0.34 / 0.32 / 0.34 | 0.23 / 0.24 / 0.23 |
| EXT (568) | stratified | (.005, .04, .005) | 0.05 | 0.18 / 0.18 / 0.16 | - | - |
| S1 (295) | stratified | (.005, .04, .005) | 0.15 | 0.99 / - / 0.94 | 0.94 / - / 0.82 | 0.89 / - / 0.72 |
| S1 (295) | stratified | (.005, .04, .005) | 0.10 | 0.76 / - / 0.53 | 0.47 / - / 0.28 | 0.32 / - / 0.20 |

Chosen row in bold: stopping pair (conditional on deploying) quartiles about 170 / 280 / 395 of 568. Secondary normal-mixture bands in the same cells: both lower bounds above their thresholds with probability 0.12 to 0.16 at delta 0.10, and about 0.8 at delta 0.15 (the fallback of 8.9). T2 (mirror): the harm gate at threshold 200 crosses in every replicate, median pair 51 to 65 (interquartile range about 37 to 89), against 43 to 53 at threshold 60; so about 88 to 91% of the scheduled candidate exposures would be avoided. The harm gate never fired in T1 cells.

### 10.4 Choice, honestly stated

- **Margin:** `delta = 0.10` on EXT. It is a laboratory demonstration margin chosen for feasibility: it is the smallest value of the grid {0.03, 0.05, 0.10, 0.15} at which the available single-exposure horizon gives a realistic chance of certification. It is not proposed as a production margin; a 10-point success loss would rarely be acceptable in practice. The paper's 0.03 (and 0.05) are declared in advance "not certifiable at this sample size" (they would need roughly 4,500 to 15,000 single-exposure tasks), rather than tested and reported as failures; their log E are logged descriptively (8.10). If only the 591-task roster is available, or if the normal mixture is the driver, `delta = 0.15`.
- **Horizon:** all pairs of the roster, once (at most 568 on EXT, 295 on S1).
- **Honest expectation.** T1: NB gate crosses within about 60 pairs with near certainty; guarded deployment with probability about 0.8 if the two workflows truly have equal success on the new stack and the pilot strata remain predictive, about 0.5 to 0.6 if the candidate is truly 2 points worse, about 0.4 to 0.5 at 3 points worse; abstention on the success gate is therefore a likely and legitimate outcome and is prespecified as such. T2: `RETAIN_INCUMBENT` near pair 50 to 65. T4: no decision. T3: unknown; abstention is likely unless |net benefit| exceeds about 0.15.
- **Limits of these numbers.** They are planning values from one pilot run per task and arm on a different serving stack. Not modelled: changes of success rates, token counts and speeds under GGUF Q4_K_M; GPU contention inside a pair; the true difficulty of S2 tasks; thermal drift. The supplementary simulation is a planning approximation by the protocol drafter, not an R4 product; R4's full simulator is to be re-run on the final frozen configuration and its script, seed and output hash added to the freeze bundle (CONFIRM C12). Simulated savings are expectations, never reported as measured savings.

---

## 11. Event log, hash chain, anchoring, usage accounting, sampler receipt

### 11.1 Files per trial

`results/live_ab/<trial>/events.jsonl` (the chain; by construction free of generated code, tracebacks, absolute paths and account names, 13.2), `anchors/anchor_<seq>.json`, and, outside git under `<WORK>/live_ab/<trial>/`: `records/<sha256>.json` (full `run_episode` records, content-addressed, fsynced, write-once), `requests/<request_id>.json.gz` (full request and response bodies), `logs/llama_<port>.log`. Only hashes of the private files enter tracked artifacts.

### 11.2 Envelope and event types

Every line is one JSON object: `seq` (0-based, gapless), `type`, `t_wall_ns`, `t_mono_ns` (comparable within one invocation; on macOS the monotonic clock is system-wide, so worker stamps are comparable with each other), `inv` (invocation id), `trial`, `prev`, `body`, `h`. Arms are always `incumbent` / `candidate`; `pair` and `arrival` are 1-based indices of the frozen order; `attempt` starts at 1. "D" = durable (`F_FULLFSYNC` before anything depends on the event).

| # | type | body (main fields) | D |
|---|---|---|---|
| 1 | `trial_started` (seq 0) | freeze bundle hash, config hash and full config, arrival-order hash, roster hash, `N_P`, arms table {workflow, server id, alias, GGUF hash}, monitor block {driver, function names, `winstats` hash, levels, thresholds, delta, `n_min`, tiers, eligibility rule, tie rule, secondary construction and its levels}, coin block {source `os.urandom(8)`, bit `byte0 & 1`, map `1 -> candidate at position 1`}, seed rule, failure-rule hash, harness and reused file hashes, protocol hash, freeze commit, external freeze anchor (URL and server timestamp), hardware allowlist, package lock hash, llama.cpp commit and binary hash | yes |
| 2 | `invocation_started` / `invocation_refused` | pid, argv (tokenized paths), `resumed`, log head at start, reconstructed state, drift list against `trial_started` (any drift in config, harness, weights, binary = refusal) | yes |
| 3 | `server_started` | server id, argv, port, GGUF {bytes, sha256 recomputed now}, `/props` {alias, total_slots, n_ctx per slot, build info, default generation settings, chat-template hash}, load seconds, smoke {request hash, receipt, usage, timings, ok} | yes |
| 4 | `server_health` | ok, slots busy, `/metrics` counters, RSS, `clock_anomaly` | no |
| 5 | `server_down` | detection, return code, in-flight list, last counters, `counters_lost` | yes |
| 6 | `server_restarted` | argv, load seconds, props (must equal #3) | yes |
| 7 | `pair_enrolled` | pair, stratum, arrivals, task uids, phase, in-flight list (must be empty in the randomized phase) | yes |
| 8 | `coin_drawn` | pair, entropy source, `raw_hex` (16 hex characters), `bit`, assignment {arrival: arm} | **yes, before any dispatch** |
| 9 | `arm_assigned_by_decision` | arrival, arm, `decision_seq` | yes |
| 10 | `episode_started` | arrival, pair, position, attempt, arm, workflow, server id, worker, task uid, `assignment_seq` (seq of #8 or #9), worker monotonic start stamp | no |
| 11 | `llm_request` | arrival, attempt, `call_index`, kind (code / tests / repair), `try_index`, client request id, server id, body hash, `sampling_sent` (all fields of 5.3), messages hash, message count, prompt characters, worker monotonic stamps (`t_c1` on the first call, `t_send`), partner in flight | no |
| 12 | `llm_response` | identifying keys, HTTP status, response id, `model`, system fingerprint, `finish_reason`, `usage` {prompt, completion, total, cached}, `timings`, `receipt` (whole `generation_settings` object), `id_slot`, stop type, `truncated`, tokens cached / evaluated / predicted, rendered-prompt hash, content hash, client seconds, worker monotonic receive stamp, `receipt_mismatch` (empty list when equal) | no |
| 13 | `llm_error` | identifying keys, `error_class` (timeout / connection / http_4xx / http_5xx / malformed), HTTP status, SHA-256 of the full error text, client seconds, `will_retry`, `usage_known: false`, bracketing `/metrics` delta if available | no |
| 14 | `episode_revealed` | arrival, pair, position, attempt, arm, `reveal_index`, outcome {success, latency_s, completion_tokens, prompt_tokens, n_llm_calls, n_failed_calls, n_self_test_executions, n_verifier_executions, repair_rounds, timed_out, truncated_any, error_class, infra_flag, partner_concurrent}, record hash, worker start and end stamps, verify seconds, sentinel flag, verifier return code, sandbox profile hash, overlap seconds with the partner, `post_decision_inflight`, `recovered_orphan` | yes |
| 15 | `attempt_aborted` | arrival, attempt, reason (worker_died / hard_cap / orchestrator_restart / operator_stop), seqs of calls seen, known tokens, calls with unknown usage, certified elapsed `ell`, rule `rerun_same_arm` | yes |
| 16 | `monitor_update` | trigger (reveal / llm_event), `n_completed`, `n_enrolled`; completed block {P, M, Pd, Md, observed NB and success difference, three log E, thresholds, secondary bands (radius, endpoints), flags}; enclosure block {enclosures of the pending pair, certified `ell`, lower/upper-enclosure log E and bands, flags}; side read-outs of 8.10; kernel code hash | no |
| 17 | `decision` | kind, `tau`, `monitor_seq`, the three log E and thresholds, in-flight list (expected empty), next unassigned arrival, rule id (`bet_split_v1` or `nm_split_v1`) | yes + anchor |
| 18 | `traffic_switch` | decision seq, arm, first affected arrival, switch latency | yes |
| 19 | `anchor` | `upto_seq`, `upto_h`, log bytes, log hash, pairs completed, record-manifest hash, trigger | yes |
| 20 | `anchor_receipt` / `anchor_failed` | anchor seq, commit id, branch, pushed (bool), external {kind, URL, server `created_at`}, or error | no |
| 21 | `amendment` / `amendment_effective` | id, text hash, path, reason, `what_was_known` (counts of revealed outcomes by arm and gate statistics at this seq, computed by the harness, never typed), first affected pair | yes |
| 22 | `log_recovery` | torn offset, length, hash | yes |
| 23 | `trial_paused` / `trial_resumed` / `operator_action` | reason code, free text hash | yes |
| 24 | `usage_reconciliation` | per server and window: counter deltas versus summed `usage`, unaccounted prompt and predicted tokens, windows with lost counters | yes |
| 25 | `invocation_ended`, `trial_ended` / `trial_aborted` | status; exposure ledger by phase and arm; reconciliation totals; torn recoveries; aborted attempts; longest unanchored span; final head | yes + anchor |

Correspondence with the event names of R2's checklist: `ENROLL` = 7; `COIN` = 8; `DISPATCH` = 10; `REQUEST_SENT` = 11; `RESPONSE` / `ABORT` / `TIMEOUT` = 12 / 15 / 13; `EPISODE_END`, `VERIFY`, `REVEAL` = 14 (one event; verifier fields inside); `LOOK` = 16; `DECISION` = 17; `SWITCH` = 18; `AMENDMENT` = 21; `RESUME` = 2 with `resumed: true`; `ANCHOR` = 19, 20.

### 11.3 Hash chain

`canon(x) = json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`; floats by Python `repr`; NaN and infinities forbidden. `h_i = SHA256(canon(event_i without "h"))`; `event_i.prev = h_{i-1}`; `event_0.prev = SHA256("live_ab/eventlog-v1|" + freeze_bundle_sha256)`, so a log cannot be replayed under another protocol. Line i is exactly `canon(event_i) + "\n"`. Single writer; descriptor opened `O_WRONLY|O_APPEND|O_CREAT`; one `os.write` per line; the file is never truncated or rewritten. A byte run that fails verification is legal only as the last line of a file being opened for resume, or when the next valid event is a `log_recovery` committing to exactly those bytes. The independent verifier `lab_verify_log.py` checks: canonical round trip, gapless `seq`, chain, the invariants of 4.2, one reveal per arrival, exactly one terminal event per `llm_request` unless its attempt was aborted, monotone `n` in reveal-triggered monitor updates, exact equality of every replayed `monitor_update` and `decision`, record hashes, anchor heads against `git show <commit>:<path>`, usage reconciliation. Prototype (`eventlog_proto.py`): tampering, deletion and a wrong genesis are detected; 4.0 ms per durable append.

### 11.4 Git anchoring (D20, CONFIRM C10)

Triggers: `trial_started`; every 25 completed pairs or 10 minutes, whichever comes first; every `decision`; every `amendment`; `trial_ended`. A separate anchor process commits `events.jsonl` and the anchor file on branch `session60/live-ab` and pushes; the commit id returns as `anchor_receipt` (it cannot be inside the event it anchors). At freeze, trial start, decision, amendment and trial end it also posts an issue comment containing `upto_h`; the comment's server-side `created_at` is the external timestamp. Local commit times are client-side and are never cited as evidence; file modification times are never cited. Anchoring never blocks a trial (`anchor_failed` is logged; the report lists the longest unanchored span), with one exception: an amendment cannot take effect without its external receipt (12.2). Before each commit the anchor process scans the files to be committed for forbidden patterns (13.2); on a hit it withholds the commit and logs `anchor_failed(forbidden_pattern)`. Pushing and commenting act on the user's account and need the user's go-ahead for the run phase; without it, anchors are local commits only and every "publicly timestamped" wording for run-time events is dropped from the report (the freeze commit is then pushed by the user by hand).

### 11.5 Usage accounting for every attempt

Two ledgers reconcile by construction: request level (one `llm_request` before and exactly one `llm_response` or `llm_error` after, for every try of every call of every attempt, including retried, failed, aborted and post-decision ones) and episode level (`episode_revealed`, `attempt_aborted`). Separate counters and tables for episodes, attempts, model requests, connection retries. Unknown usage is `null` with a reason, never 0. For requests without a response the server-side counters bound the unknown part: `/metrics` (`prompt_tokens_total`, `tokens_predicted_total`) is scraped at the window boundaries of 5.2, and `usage_reconciliation` reports, per window, counter delta minus summed client-side usage; windows that span a crash are reported as unreconciled (`counters_lost`). Summary fields are named literally (`requests_without_usage`, `episodes_with_harness_abort`, `canonical_records_absent`); there is no field called `missing_outcomes`. Smoke and calibration traffic lives in its own chain with its own phase tags and is reported separately. Trial wall-clock, per-worker busy and idle time and per-episode durations are all logged; each summary states which one it uses. Tokens are never converted into money, energy or "compute"; prompt tokens stay visible.

### 11.6 Sampler receipt

As in 5.7: exact request body hash and `sampling_sent` before the POST; the server's `generation_settings` object stored whole in `llm_response.receipt`; comparison on `receipt_keys`; per-request, never once per file. This closes the root's "actual sampler receipt unverified" finding for these trials only; no claim is made about the pilot.

---

## 12. Freeze, deviations, operational stopping, resume

### 12.1 Freeze procedure (one freeze for all four trials)

1. Branch `session60/live-ab` from current root main (merge only; never rebase, reset, force-push; no existing file under `experiments/{local_stream,tau2_open}`, `results/{local_stream,tau2_open}`, `paper/`, `src/`, `reviews/` is touched; the only shared file that may change is `results/SESSION60_RESULTS_INDEX.md`).
2. Harness, unit tests, mock-server dry runs (every derived file carries a MOCK banner and sits under a path that every builder excludes).
3. GitHub issue "Conditional experiment: prospective randomized live-stopped trial (live_ab)" with this protocol's hash, resources (one M5, about 8 GPU hours), outputs, and the questions C3 to C8 and C16 for the root. The freeze waits for the root's answers; each unanswered item takes the fallback of table 0.2, and the issue records which.
4. Pre-freeze out-of-design phase (5.8), downloads (C9), reference sweep (3.2), roster rule (3.3), T3 model rule (2.4), timeout rule (5.5), R4 re-run (C12).
5. Freeze bundle = SHA-256 over the canonical JSON of {config hash, roster hash, the four arrival-order hashes, protocol hash, hash of every `lab_*.py`, of the reused `local_stream` files, of `src/winstats.py`, GGUF hashes, LICENSE hashes, llama.cpp commit and binary hash, environment lock hash, power-analysis script and output hashes}. Preflight fails on any "unknown".
6. Commit and push; post commit id and bundle hash on the issue. Only then may a design episode start. The runner refuses to start on any hash mismatch and re-verifies harness, config, binary and weights at every invocation.
7. Corrections to the frozen protocol are errata files; the frozen bytes never change.

### 12.2 Amendments

An amendment is: a hash-chained `amendment` event (what, why, first affected pair, and `what_was_known` computed by the harness) -> anchor -> pushed commit and issue comment -> `amendment_effective`, which the runner accepts only if the anchor receipt covers the amendment event. Times are never typed by hand. An amendment applies to both arms, flags every unit with its regime, keeps all units in the denominator, and claims no counterfactual invariance. Monitoring parameters (levels, thresholds, delta, grid, `n_min`, hierarchy, tolerances, horizon, driver, harm rule) cannot be amended within a trial; changing any of them, or any system version (model file, server build, prompts, sampling), ends the trial (`trial_aborted`) and any continuation is a new trial id with its own level and freeze. Owner-side verification reports name the exact commit and file hashes they checked and are never edited afterwards.

### 12.3 Resume (a pure function of the verified log)

1. Verify the chain; commit a torn tail with `log_recovery`; refuse on any drift against `trial_started`; take the exclusive lock.
2. For each pair in frozen order: no durable coin -> it is simply the next pair; durable coin and both reveals -> done forever; durable coin with a missing reveal -> if a content-addressed record for (arrival, attempt) exists that no event references, reveal it (`recovered_orphan: true`; re-running would be a second draw), else `attempt_aborted` and re-run under the same arm.
3. Rebuild the monitor by replay. If a `decision` exists, the phase is restored and no coin is ever drawn again.
4. Recovered orphans are revealed first, in arrival order (frozen tie rule). No resume path deletes, overwrites or re-runs a revealed unit.

### 12.4 Order of trials and stopping for operational reasons (D21)

Order: T4, T2, T1, T3. T4 first, so that a plumbing defect is found where it costs no claim; T3 last, so that the only unknown-outcome trial runs on the most exercised harness. The order is fixed; a later trial does not depend on an earlier result.

A trial may be paused only between pairs (`trial_paused` with a reason code from the frozen list: hardware, power, thermal shutdown, disk, server cannot be restarted, operator unavailable, monitor exception). The operator console shows progress counts but no arm-level outcome summary and no gate statistic before the decision event, so that a pause cannot be outcome-driven; any look at the raw log by the operator is an `operator_action`. A paused trial is resumed as the same trial. A trial that cannot be completed is closed with `trial_aborted(operational)`; everything revealed is reported; no decision other than one already logged is claimed; it is not restarted. Automatic aborts: 6.4 rows 6, 12, 13; ten consecutive `harness_abort` outcomes (pause, then amendment or abort).

---

## 13. Reproducibility and anonymization

### 13.1 Reproducibility

- One deterministic builder `experiments/live_ab/build_live_ab_results.py` (standard library, numpy, `src/winstats.py` only) regenerates every table and figure input from the tracked files; it has no import path to the harness, the sandbox or an HTTP client (a test checks this), never runs a model or a generated program, and writes timestamp-free outputs (run metadata in a sidecar). Figures: the numeric inputs are hashed; pixel identity is never claimed.
- Tracked deliverables per trial: `events.jsonl`, `anchors/`, `metrics.csv` (row-preserving projection, one row per arrival: no `final_code`, no self-test code, no stderr, no tracebacks; keeps `error_present`, error class, retry counts), `pairs.csv` (pair, stratum, coin, scores, decisive tier, flags), `monitor.csv` (one row per look), `decision.json`, `exposure_ledger.json`, `usage_reconciliation.json`, `config.json`, `roster.json`, `arrival_order.json`, `provenance.json` with two separate hash tables (original private files; derived tracked files), `env_lock.txt` (`pip freeze`, interpreter, OS build, llama.cpp commit and binary hash, launch lines), non-executed `.txt` snapshots of the harness sources, `SOURCE_NOTICES.md`, `DELIVERY_LEDGER.md` (collection status, audited observations, accepted analysis, manuscript claims, excluded methods, deferred extensions), and a versioned generated report. Reports are versioned (`report_v1.md`, ...) and never overwritten; exactly one governing document per trial is named first everywhere. Counts quoted in hand-off notes come from an included command.
- A consistency check proves reproducibility of numbers, not their sampling assumptions; the verifier report says so.
- Generation is seeded but not bit-reproducible; success labels are archived verifier labels.

### 13.2 Anonymization and release hygiene

- No tracked artifact contains an absolute path, an account name, a host name or a repository URL with an account name. The harness writes repository-relative paths and the tokens `<REPO>`, `<WORK>`, `<HF_CACHE>`, `<LLAMA_BIN>`; host facts come from an allowlist (chip, memory, OS build); the environment dump is allowlisted (no credentials, no environment variables beyond an allowlist); error texts enter tracked files only as class plus SHA-256.
- A release check scans every text member of every tracked or packaged file for: the local account name, the GitHub account name, the institution name, the repository name, `/Users/`, `/home/`, `/private/tmp/`, `/var/folders/`, and e-mail patterns, anywhere in a string, not only as a prefix. It is a bounded known-pattern check and is described as such, not as a proof. Two exemptions are allowlisted by exact string: the pattern list of this paragraph (in the protocol and in the scanner source) and the neutral sandbox root `/private/tmp/labsbx`.
- Raw evidence is never rewritten to conceal provenance. If a forbidden pattern is ever found in `events.jsonl`, the raw chain is kept privately with its hash and a sanitized copy is released with an original-to-release hash map; the sanitizer uses relative paths and fixed replacement tokens, so it is location-independent; no byte identity across machines is claimed unless tested.
- Two variants of the hand-off are produced (with and without researcher repository URLs and commit ids), because the root builds an anonymous code archive even though the target is now arXiv.
- Licensing text: MBPP CC-BY-4.0, HumanEval MIT, model licences as recorded in 2.3; the harness itself is described with no licence until the author decides (CONFIRM C13).

---

## 14. What will be reported whatever the outcome

For every trial, including aborted, abstaining and "wrong-direction" ones, in the same format and with the same prominence:

1. the freeze record (commit, bundle hash, issue link, root answers to C3 to C8 and C16, fallbacks taken) and every amendment, pause, operator action and erratum;
2. enrollment: pairs enrolled, completed, flagged (`infra_flag`, `partner_concurrent: false`, `recovered_orphan`), attempts aborted, torn recoveries, longest unanchored span; unpaired leftovers;
3. the decision or abstention, `tau`, calendar times, the three log E and thresholds at `tau` or `N_P`, the full look-by-look trajectory (`monitor.csv`), the secondary normal-mixture bands with their levels, the verifier's replay result;
4. win/tie/loss counts, tier shares, per-arm success counts, observed net benefit and success difference, labelled descriptive and optional-stopping biased;
5. the comparator timings `t_enc`, `t_dec`, switch latency; reveal-order statistics (how often position 2 was revealed first, certified-early pairs);
6. the exposure ledger by phase and arm; exact exposures avoided; measured totals; the labelled projection;
7. failure-inclusive usage accounting and the reconciliation residual as a number; receipt mismatches (expected 0); served-model assertions;
8. by-stratum read-outs, sensitivity hierarchies and side read-outs at the other margins, all labelled descriptive;
9. the power-analysis expectation next to what happened, including the case "T1 abstained on the success gate", which is reported as abstention of this rule at this margin on this stream and never as evidence that the workflows differ or are equivalent;
10. for T4: whether any gate crossed; if one did, the statement that this event has probability at most 0.01 under the exact null and did occur;
11. for T3: the model identity, licence evidence and the non-outcome rationale of 2.4, whichever model was used;
12. unsuccessful hypotheses, negative and inconclusive results are retained in the results index under their own heading; nothing is rerun to obtain a different answer; deferred items are listed as deferred.

The results index separates: observations; the prespecified live analysis; owner-side descriptive readings; excluded methods. The PR body is regenerated from the governing report at each hand-off. No statement says or implies that the root approved anything beyond the literal text of a root disposition.

---

## Appendix A. Crosswalk to R2's pre-registration checklist

| checklist item | section |
|---|---|
| Trial ids; incumbent, candidate; model repo, revision, weight hash, quantization, licence evidence; serving stack, commit, launch command; host; workers; resident servers | 1.2, 2.1 to 2.5, 5.1 |
| Pilot disclosure; T1/T2 predictable; T3 only unknown; shared roster or blocks | 1.1, 1.2, 3.4 |
| Laboratory scope; open-weight only; loopback only | 1.3, 1.4, 2.3 |
| Roster: pinned sources, task-list hash, prospective exclusions, arrival permutation and its hash | 3.1 to 3.6 |
| Unit of randomization; coin q = 1/2 from OS entropy; code path; logged-before-dispatch; odd leftover | 4.1, 4.2, 3.6 |
| Dispatcher and concurrency rule; overlap record | 5.1, 6.1, 11.2 (#11, #14) |
| Per-request seed policy | 5.4 |
| Sampling settings, completion cap, context limit, request / episode / verifier timeouts from an out-of-design timing pilot | 5.3, 5.5, 5.8, 2.2 |
| Kernel: tiers, directions, tolerance, eligibility, joint failure = tie; kernel code hash | 6.2, 11.2 (#16) |
| Scores Z and D; ITT failure rule | 6.3, 6.4 |
| Filtrations; coins >= i outside F_{i-1}; targets; assumptions per reading | 7.2, 7.4 |
| Monitoring statistic, file hash, thresholds with rationale for delta, alpha program / trial / gate / direction, same-prefix conjunction, no retention, no running intersection | 8.1 to 8.5, 10.4 |
| Asynchronous rule: primary completed prefix, secondary enclosure, looks, minimum n | 7.3, 7.6, 8.2, 8.6 |
| Action map, live switch, in-flight pairs, horizon, ABSTAIN_AT_HORIZON | 8.3, 8.7, 8.8 |
| What is descriptive only | 9.3, 8.10 |
| Exposures avoided (exact) and projection (formula, label) | 9.4 |
| Power analysis: script, seed, output hash; operating characteristics; A/A rate; guardrail power at the chosen delta | 10, 12.1 step 5 |
| Event schema, hash chain, fsync rule, anchor cadence and push rule | 11.2 to 11.4 |
| Sampler-receipt mechanism and preflight proof | 5.7, 5.8, 11.6 |
| Usage reconciliation; smoke tagging | 11.5, 5.8 |
| Manifest: environment lock, harness hashes per invocation, model-id assertion, weight hash preflight, Seatbelt profile hash | 11.2 (#1 to #3, #14), 12.1, 13.1 |
| Exclusive-use lock and preflight server scan | 2.1 |
| Amendment procedure | 12.2 |
| Crash and resume; no deletion or rerun of logged units | 12.3 |
| No extension, no rerun, no model or seed reselection; failed hypotheses retained | 8.8, 14 |
| Output file list, deterministic builder, metrics projection, hash tables, sanitized-copy rule, notices, delivery ledger | 13.1, 13.2 |
| Allowed and forbidden claim lists copied into the protocol | 1.3, 1.4 |
| Freeze record; "before any design-task outcome" | header, 12.1 |
| AI-review disclaimer with exact commits | 1.4 item 16, 12.2 |

R2's conflicts K1 to K8 are resolved in 4.1 (K1), 7.3 and 8.6 (K2), 5.1 and 7.4 (K3), 9.4 (K4), 10 (K5), 8.4 (K6), 3.4 (K7), 8.7 and 9.3 (K8).

## Appendix B. Frozen configuration skeleton (values of this draft; `null` = pinned in the pre-freeze phase)

```json
{
  "experiment": "live_ab", "protocol_version": "v1-draft",
  "trials": {
    "T1": {"trial_no": 1, "incumbent": {"workflow": "self_test_repair", "server": "coder"}, "candidate": {"workflow": "single_shot", "server": "coder"}, "tiers": 3, "levels": [0.005, 0.04, 0.005]},
    "T2": {"trial_no": 2, "incumbent": {"workflow": "single_shot", "server": "coder"}, "candidate": {"workflow": "self_test_repair", "server": "coder"}, "tiers": 3, "levels": [0.005, 0.04, 0.005]},
    "T3": {"trial_no": 3, "incumbent": {"workflow": "single_shot", "server": "coder"}, "candidate": {"workflow": "single_shot", "server": "t3"}, "tiers": 2, "levels": [0.016666666666666666, 0.016666666666666666, 0.016666666666666666]},
    "T4": {"trial_no": 4, "incumbent": {"workflow": "single_shot", "server": "coder"}, "candidate": {"workflow": "single_shot", "server": "coder"}, "tiers": 3, "levels": [0.005, 0.04, 0.005]}
  },
  "execution_order": ["T4", "T2", "T1", "T3"],
  "servers": {
    "coder": {"port": 8091, "alias": "qwen2.5-coder-7b-instruct-q4km", "hf_repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "hf_revision": "13fb94bfda8c8cf22497dc57b78f391a9acb426a", "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "bytes": 4683073536, "sha256": "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c", "license": "apache-2.0", "license_evidence": null},
    "t3": {"port": 8092, "alias": "t3-candidate", "hf_repo": "ibm-granite/granite-3.3-8b-instruct-GGUF", "hf_revision": null, "file": null, "bytes": null, "sha256": null, "license": "apache-2.0", "license_evidence": null,
           "fallback": {"hf_repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF", "hf_revision": "a06e946bb6b655725eafa393f4a9745d460374c9", "file": "Qwen3-4B-Instruct-2507-Q4_K_M.gguf", "bytes": 2497281120, "sha256": "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597"}}
  },
  "llama_cpp_commit": "4fea119de30f6a923992780f6fd5ccb0bee5d47d", "llama_server_sha256": null,
  "llama_args": ["-np", "2", "-c", "16384", "--no-kv-unified", "-ngl", "99", "--jinja", "--metrics", "--no-context-shift", "--offline", "--host", "127.0.0.1", "--log-timestamps"],
  "workers": 2, "randomized_phase_schedule": "pair_synchronous", "post_decision_schedule": "work_conserving",
  "sampling": {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "typical_p": 1.0, "repeat_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0, "mirostat": 0, "max_tokens": 1024, "cache_prompt": false, "stream": false, "verbose": true},
  "receipt_keys": null, "receipt_float_tolerance": 1e-06,
  "seed_rule": {"multiplier": 2654435761, "increment": 40503, "modulus": 2147483648},
  "request_timeout_s": 180, "max_connection_retries": 2, "server_recovery_s": 180, "episode_hard_cap_s": 1800, "max_attempts": 3,
  "sandbox": {"timeout_s": 10.0, "cpu_s": 10, "mem_bytes": 2147483648, "output_cap_bytes": 65536, "tmpdir": "/private/tmp/labsbx"}, "max_repair_rounds": 2,
  "hierarchy": [{"name": "success", "higher_better": true, "relative_tolerance": 0.0}, {"name": "latency_s", "higher_better": false, "relative_tolerance": 0.10}, {"name": "completion_tokens", "higher_better": false, "relative_tolerance": 0.10}],
  "eligibility_rule": "tiers after the first are compared only when both episodes succeeded; joint failure is a tie",
  "monitor": {"driver": "betting", "rule_id": "bet_split_v1", "bets": 40, "delta": 0.10, "n_min": 20, "look": "every completed pair", "retention": false, "running_intersection": false,
              "secondary": {"construction": "normal_mixture", "rho": 100.0, "levels_T1_T2_T4": [0.01, 0.04], "levels_T3": [0.03333333333333333, 0.016666666666666666]},
              "side_deltas": [0.03, 0.05, 0.10, 0.15], "winstats_sha256": "56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69"},
  "coin": {"source": "os.urandom(8)", "bit": "byte0 & 1", "map": "1 -> candidate at position 1", "unit": "pair"},
  "design_seed_base": 60260919, "strata": ["S1_k2", "S1_k1", "S1_k0", "S2"], "roster_rule": {"min_s2_tasks": 400, "delta_if_s1_only": 0.15},
  "anchor": {"pairs": 25, "minutes": 10, "push": null, "issue_comment_triggers": ["freeze", "trial_started", "decision", "amendment", "trial_ended"]},
  "smoke_tasks": ["mbpp_full/39", "mbpp_full/122", "mbpp_full/522", "mbpp_full/547", "mbpp_full/869", "mbpp_full/966"]
}
```

## Appendix C. Harness modules and the test plan (from R3; normative for the implementer)

New code under `experiments/live_ab/` with the prefix `lab_` (nothing shadows existing modules): `lab_common` (paths, freeze bundle), `lab_data` (roster, sweep, exclusions), `lab_design` (arrival order only), `lab_eventlog`, `lab_coin`, `lab_client` (logged client with receipt comparison; same interface as the pilot's client so that `agent.py` stays byte-identical), `lab_server` (start, probe, supervise, `/metrics`), `lab_worker`, `lab_monitor` (pure functions of the verified log: completed-prefix statistics, enclosures, secondary bands, decision), `lab_orchestrator` (single log writer, pair-synchronous scheduler, switch, exposure ledger, resume), `lab_anchor`, `lab_verify_log`, `lab_mock_server`, `tests_live_ab`, `build_live_ab_results`. Reused unchanged and hashed: `local_stream/{agent,sandbox,verify,data,common}.py`, helper functions of `run_stream.py`, `src/winstats.py`. Not reused: `local_stream/design.py` (seeded orientations stored before the run), the sequential main loop of `run_stream.py`, the pilot's monitor table, the pilot's HTTP client, the rewritable manifest, the airline amendment loader.

Tests without any model (all must pass before the freeze): chain and tamper tests; coin write-ahead (fsync-before-dispatch spy, patched `os.urandom`, one coin per pair, none after a decision, coin of pair i+1 only after both reveals of pair i); seed uniqueness over the full grid; monitor equality with `winstats` to the last bit, `n_min`, same-prefix conjunction, harm precedence, no retention, enclosure logic of 7.6 including the 0.9 rule and the abort case, replay equality; scheduler and switch with scripted latencies (position 2 revealed first, decision only at pair completion, post-decision assignment, horizon exhaustion, leftovers); the eight kill points of R3's resume matrix; client fault handling for every injected fault; usage reconciliation against mock counters; reused pilot test classes; freeze-bundle drift refusal; forbidden-pattern scan; builder isolation. Mock-server dry runs: T1-like abstention, wide-margin deploy with switch, T2-like harm stop, A/A wiring, chaos kills, and an anchor drill in a throwaway repository outside the project.

## Appendix D. What this draft deliberately leaves to the pre-freeze phase

Values marked `null` in Appendix B; `n_S2` and therefore `N_P` and `delta` (rule 3.3); the T3 model (rule 2.4); `request_timeout_s` (rule 5.5); `receipt_keys` (smoke test 5.7); the root's answers to C3 to C8 and C16 and the user's answers to C9 and C10. Each is decided by a rule written above that uses no design-task outcome, and each decided value is recorded in the freeze bundle before the first design episode.
