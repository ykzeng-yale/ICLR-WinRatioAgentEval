# Pre-registered protocol: local-model prospective stream (issues #1 and #2)

Status: design FROZEN on 2026-09-18 before any model call; harness amended
2026-09-18 after the pre-registration audit
(`reviews/local_stream_preregistration_audit.md`), still before any model
call on a design task (see the Freeze section and the deviations log). Design file
`results/local_stream/design.json`, sha256
`6175b81562efe1b1c87b113050f70c5daab2143e272cba39fb9a796f0d645457` (whole
file, including generation timestamp and provenance fields); content-only
sha256 (arrivals, seed, task list hash, config hash; what
`design.py --print-sha-only` reproduces in any process)
`da84ff558deb2baf19d8728e3c50aea9e01e2411a5855cf07a2fac3594b8d4ad`; task list
sha256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`;
config sha256 `2dfb51966780698be326a8897c9e384a5513a7c1a47505c42b8a15c6c5baaf5b`.
Any change after the first real episode is a deviation and must be logged in
section 13. The mock dry run (`results/local_stream/dryrun/`) is pipeline
testing only and is never reported as a result.

## 1. Question and hypotheses

We compare two inexpensive coding workflows built on the same local model on a
stream of public, automatically verifiable programming tasks:

- A `single_shot`: one completion, first code block is the answer.
- B `self_test_repair`: write code, write its own assert tests (without hidden
  tests), execute, repair from the traceback up to twice (<= 4 model calls).

Primary hypotheses (directional, stated before data):

- H1: B has higher hidden-test success than A (self-testing catches some errors).
- H2: B has higher latency and more completion tokens than A (more calls, more execution).
- H3: Under the pre-specified hierarchy success > latency > tokens with the
  absorbing rule, the net benefit of B vs A is positive (the hierarchy prefers B).
- H4: A latency-first or token-first hierarchy (sensitivity, section 11) prefers A.
  The disagreement between H3 and H4 is the substantive point: which system
  "wins" is a property of the pre-specified objective, not of the data alone.
- H5 (guardrail): B's success is not inferior to A's by more than 0.03.

## 2. Estimands

Two distinct contrasts are estimated from the same run and reported separately:

- E1 cross-arrival (online) contrast: for pass-1 pairs k = 1..295 the two
  arrivals are different tasks, each exposed once to one variant, with the
  variant order randomized by R_k. The pair score Z_k = hierarchy(B episode vs A
  episode) is a comparison across different tasks; E[Z_k] is the population net
  benefit of B over A for a random pair of task arrivals. Pairs are independent
  across k (disjoint arrivals, fresh model calls), which is the unit for the
  anytime-valid analysis. This is the design an online evaluator can run when it
  cannot replay the same task to both systems.
- E2 same-task shadow contrast: pass 1 + pass 2 give one A and one B episode for
  every task (two per variant per task if trial 2 runs). Task-level win/loss
  scores are averaged within task and inference is task-clustered
  (`wincs.clustered_summary`). This is the paired "shadow evaluation" target.
  E2 is more precise than E1 for the same number of episodes; E1 is the one a
  truly online stream delivers. Both are reported; neither is reduced to the other.

## 3. Task set and strata

All 427 MBPP-sanitized problems (google-research `sanitized-mbpp.json`) and all
164 HumanEval problems (openai/human-eval `HumanEval.jsonl.gz`): 591 tasks, no
selection, no exclusion. Benchmark is the stratum; per-stratum results and an
equal-weight stratified combination are reported alongside the pooled
(task-weighted) result. Canonical ordering: MBPP by numeric task_id, then
HumanEval by numeric index; `work/local_stream/data/tasks.json` and its sha256
are in `data_manifest.json` with each download's URL, byte size and sha256.

## 4. Design (frozen; `design.py`)

- Seed 20260918 -> `numpy.random.SeedSequence` -> `default_rng`; independent of
  `PYTHONHASHSEED` (tested).
- Arrival order = random permutation of the 591 tasks.
- Pairs: arrivals (2k-1, 2k), k = 1..295. Orientation R_k ~ Bernoulli(1/2), fixed
  per pair: R_k = 1 means the first arrival of pair k gets A in pass 1 and the
  second gets B; R_k = 0 reverses. Arrival 591 has no partner: it is run in both
  passes and enters E2 only; its pass-1 variant is one extra Bernoulli draw.
- Pass 1 runs every arrival with its pass-1 variant, in arrival order, one at a
  time. Pass 2 then runs the complementary variant for every arrival in the same
  order. Every task therefore receives both variants exactly once per trial.
- Optional trial 2 (seed 20260919, disabled in config): a second design with the
  same rules; if run, both trials' episodes are replicates in E2 and trial 2's
  pass-1 pairs form an independent replicate of E1. The decision to run trial 2
  is a resource decision taken before looking at trial-1 outcomes, else logged
  as a deviation.
- Same-task paired shadow vs randomized AB/BA exposure: E1 uses only pass-1
  pairs (each arrival exposed once; AB/BA randomized); E2 uses pass 1 + pass 2
  (same task, both variants). Pass-2 episodes never enter E1.

## 5. Model, prompts, workflow variants

- Model: `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` (MLX 4-bit conversion of
  Qwen/Qwen2.5-Coder-7B-Instruct, 7.61B parameters), served by `mlx_lm.server`
  (mlx_lm 0.31.3) as an OpenAI-compatible endpoint at
  `http://127.0.0.1:8080/v1`. Expected snapshot revision
  `019cc73c45c770444708a6dd8690c66243cc5c80` (4,295,890,004 bytes); the served
  revision and the `/v1/models` reply are recorded in `run_manifest.json`.
  Weights stay in the huggingface cache outside the repository.
- Sampling: temperature 0.7, top_p 0.95, max_tokens 1024 per call; request
  timeout 300 s; up to 2 retries on connection errors (logged per episode).
- Shared prompt. System: expert Python programmer, one complete self-contained
  solution in a single python code block, imports included, no tests. User,
  MBPP: the `prompt` text plus ONLY the function signature line
  `def name(args):` of the entry point, reconstructed with `ast` from the
  reference solution's def statement ("Use exactly this function signature");
  NO assert of `test_list` is ever shown, not even the first one (the
  `signature_example` field kept in `tasks.json` for hash stability is unused).
  In 416/427 tasks the entry point is the first def of the reference; in 11 the
  first def is a helper and the entry point's def is used, because the hidden
  asserts call the entry point. User, HumanEval: the `prompt` (signature +
  docstring; 76/164 contain the benchmark's own `>>>` doctest examples, which
  is standard benchmark content). Hidden tests (`test_list` in full,
  `challenge_test_list`, HumanEval `test`/`check`) are consumed only by
  `verify.py` and are never placed in any prompt (unit test
  `test_hidden_tests_never_in_prompt` checks every task: no `assert` in any
  MBPP prompt, no `check(` or test text in any HumanEval prompt).
- Variant A: one call; candidate = first ```python block (fallback: whole text).
- Variant B: call 1 code; call 2 asks for 3-5 asserts for the function without
  hidden tests; execute code + self-tests in the sandbox; on failure (assertion,
  exception, timeout, syntax error, or static block) call 3 repairs given the
  last 2,000 characters of the traceback; at most 2 repair rounds (<= 4 calls);
  the final candidate is the last code produced whether or not self-tests pass.
  `self_test_passed` is recorded.
- Per-call seeds derived from (trial, arrival, variant, round) are sent; Metal
  sampling is not guaranteed bit-reproducible and this is not relied upon.

## 6. Outcomes and the hierarchy

Per episode (see `agent.py` record): success (hidden tests pass AND the
verifier's sentinel was printed, section 7), latency_s (section 8),
verify_seconds, completion_tokens, prompt_tokens, n_llm_calls, n_executions,
repair_rounds, self_test_passed, sentinel_seen, hack_flags, static_flags,
sandbox_flag, sandbox_kind, sandbox_profile_sha256, timed_out, error,
final_code, response_models (served model id of every call), model, endpoint,
harness_git_hash, config_hash, start/end timestamps.

Token source: `completion_tokens` (and `prompt_tokens`) are the server's
`usage.completion_tokens` / `usage.prompt_tokens` summed over every call of
the episode (for B this includes the test-writing and repair calls). If a
response carries no `usage`, the count is estimated (cached model tokenizer,
else characters/4) and the episode is flagged `tokens_estimated`; the count of
such episodes per variant is reported in the failure accounting.

Hierarchy (B vs A), tiers in order: (1) success, higher better, no tolerance;
(2) latency_s, lower better, relative tolerance 0.10 (|dL| <= 0.10 x max(L_A,
L_B) is a tie at this tier); (3) completion_tokens, lower better, relative
tolerance 0.10. Absorbing rule: tiers 2 and 3 are compared only if both
episodes succeeded; a pair with exactly one success is decided at tier 1; a
pair with two failures is a tie. Implementation: `winstats.compare` with the
eligibility mask, identical to `experiments/run_replay.py`.

## 7. What counts as a failure (outcomes, never exclusions)

Every enrolled arrival yields a record. Verification (`verify.py`) runs
candidate + ALL hidden asserts of `test_list` (+ `challenge_test_list`, which
is empty for all 427 sanitized tasks) for MBPP, or candidate + benchmark
`test` + `check(entry_point)` for HumanEval, followed by
`print('__LS_VERIFY_OK__<16-hex nonce>')`; the nonce is drawn per call and
never shown to the model. success = True iff the sandboxed program exited with
status 0, did not time out, AND its raw stdout ends with the sentinel.
success = False whenever: any hidden assert fails; the program raises;
wall-clock timeout (10 s) or CPU limit (10 s) in verification; the program
exits (status 0 or not) before the hidden tests ran, e.g. `sys.exit`,
`raise SystemExit`, `os._exit` (sentinel absent); empty or unextractable code;
entry point not defined (NameError in the asserts; a HumanEval candidate that
drops the prompt's `from typing import List` fails the same way, counted
equally for A and B); API/HTTP error or connection failure after retries
(`error` recorded, the episode is kept with its latency and whatever tokens
were consumed). `sandbox_flag` (static heuristic match, section 9) and
`hack_flags` (static heuristics on the candidate: SystemExit, `_exit`,
`sys.exit`, `def __eq__`, `builtins`, `sys.modules`, `__file__`, `atexit`)
are RECORDED and never decide success; the numbers of flagged episodes and of
flagged successes per variant are reported so a reviewer can judge whether
any success is suspect. Known limitation shared with every MBPP/HumanEval
harness: a candidate returning a universal object whose `__eq__` is always
True passes equality asserts; it is flagged, not prevented. A candidate that
reads its own program file to learn the nonce would also be flagged
(`__file__`); the sentinel is a defence against early exit, not against a
deliberately adversarial model. No episode is re-run for a bad outcome; the
only re-run path is resume of an episode that never completed (absent from
`episodes.jsonl`). Counts of each failure kind per variant are reported
(`components.failure_accounting`). Abstentions do not exist in this task
format; an empty answer is a failure.

## 8. Latency scope

latency_s is the wall-clock time from immediately before the episode's first
model call to the moment the final candidate exists: all model calls (queueing
in the single-request local server included), all of the agent's OWN sandbox
executions (variant B's self-tests) and harness overhead. It EXCLUDES
hidden-test verification, which is grader time, not system latency; that is
recorded separately as `verify_seconds` (reported per variant, not part of
any tier). It also excludes model loading (server started before the run) and
data loading. Decision taken before any outcome exists (audit section 5): a
verification timeout on a failed candidate would otherwise add up to 10 s to
the latency of failed episodes and inflate the component means. The stream is a
single local inference stream: strictly sequential, no concurrency, one episode
at a time, so latencies are not confounded by contention between arms. Wall
clock uses `time.perf_counter`; hardware and OS are in the manifest.
`llm_call_seconds` and `execution_seconds` are also recorded per episode for
decomposition. A repeated run on other hardware will change latency and hence
tier-2 outcomes; results are conditional on the recorded hardware.

## 9. Sandbox

Binding guards (`sandbox.py`; the run manifest records the profile text and
its sha256, and every episode records `sandbox_kind` and
`sandbox_profile_sha256`):

- macOS Seatbelt via `/usr/bin/sandbox-exec -p <profile>`; the profile is
  derived from `Path.home()`, the interpreter prefix and the temp directory:
  `(deny network*)`; `(deny file-read* (subpath $HOME))` with
  `(allow file-read* (subpath <interpreter prefix>))`; `(deny file-write*
  (subpath $HOME))` and `(deny file-write*` for `$TMPDIR`, `/tmp`,
  `/private/tmp`, `/var/tmp`, `/private/var/tmp)` with `(allow file-write*
  (subpath $TMPDIR/ls_sbx))` (the parent of every program's own cwd) and
  `/dev/null`; `(deny process-exec (subpath /bin) (subpath /usr/bin) (subpath
  /usr/local/bin) (subpath /opt) (subpath /sbin) (subpath /usr/sbin))`.
- The interpreter is the venv's base interpreter (`pyvenv.cfg` `home`,
  realpath), never the venv symlink, so `sys.executable` does not reveal the
  repository path; `python -I -S prog.py`, fresh cwd under `$TMPDIR/ls_sbx`,
  environment PATH only, stdin closed.
- Process group: `start_new_session=True`; on wall-clock timeout (10 s) the
  whole group receives SIGKILL (no orphans; verified with a 20-way fork).
- rlimits in the child: RLIMIT_CPU 10 s; RLIMIT_NPROC 64 (macOS counts per
  uid, so any fork from the sandbox fails with EAGAIN); RLIMIT_AS/RLIMIT_DATA
  requested at 2 GB (macOS rejects the call; the applied limits are recorded
  per episode in `sandbox_limits_applied`; on Linux the memory cap is
  enforced). There is NO memory cap on macOS: a 3 GB allocation succeeds
  (audit table); this is disclosed, not fixed.
- stdout/stderr capped at 64 KB in the record; the raw stdout tail is kept
  for the sentinel check so a chatty but correct program is not penalised.

Containment verified before freezing (audit section 2 programs, re-run after
the fix; unit test `test_adversarial_programs_contained`): outbound connect via
`_socket` alias (EPERM); `os.remove` of a file outside the cwd built from a
concatenated path (EPERM); `os.popen('id')` / `subprocess.run(['/bin/ls'])`
(exec denied or fork refused); read of `~/.zshrc`, of a repository file and of
`<sys.executable>/../../.env` (all PermissionError); write under `$HOME` and
under `/private/tmp` (PermissionError); fork x20 then sleep (timed out, group
killed, no orphan); infinite loop (timed out); `raise SystemExit(0)`,
`os._exit(0)` and an indented `sys.exit(0)` in wrong code (exit status 0 but
success = False by the sentinel). The static regex list of the previous
version (os.system/popen/exec*/spawn*/fork, subprocess, shutil.rmtree,
socket, urllib, requests, http.client, ctypes, multiprocessing, sys.exit,
os.remove/unlink, `__import__`/importlib, open on absolute paths,
sys.executable/`__file__`) is NOT a guard: every program is executed and a
match is only recorded (`static_flags`, `sandbox_flag`) for post-hoc review,
since the audit showed six of eight attack classes bypassed it. All 591
reference solutions pass verification under the Seatbelt profile (unit test
sample of 40 plus the pre-freeze full check). Outside macOS the Seatbelt layer
is absent and recorded as `sandbox_kind = none`; the stream is run on the
macOS host described in section 14.

## 10. Monitoring and decision semantics

After every completed pass-1 pair (both episodes of pair k recorded) the
following are computed from the cumulative counts, using
`winstats.betting_log_e_ternary` (mixture of 40 constant bets):

- win e-process: H0: E[Z] <= 0 (B not preferred);
- harm e-process: H0: E[Z] >= 0 (B not harmful), i.e. the same statistic with
  wins and losses swapped;
- guardrail e-process on the success difference D_k = success_B - success_A in
  {-1,0,1}: H0: E[D] <= -0.03 (B inferior by more than the margin).

alpha = 0.05, threshold log(1/alpha) for each e-process; decisions are only
read after min_n = 20 pairs. "Deploy B" = win and guardrail e-processes both
crossed; "B harmful" = harm e-process crossed. The three first-crossing
indices are recorded (`monitor_state.json`), and e-values at every pair are
logged (`monitor_pass1.csv`). Execution never stops early: all 591 arrivals
and both passes are completed so the fixed-horizon (E1 at n = 295) and shadow
(E2) analyses are available; the anytime-valid decision is the one that would
have been taken at the recorded crossing. Because the win and guardrail
processes are used as a conjunction and each is a valid e-process at level
alpha, the guarded deploy decision has type-I error <= alpha under the
respective nulls; the harm process is a second, separately reported test.
Arrivals are a random permutation of the fixed 591-task population (sampling
without replacement), so pair scores are exchangeable rather than i.i.d.; the
E1 null is the superpopulation null E[Z] <= 0 for a random pair of task
arrivals, and `winstats.betting_log_e_ternary` tests the pointwise conditional
null, as documented in the project's replay analysis.

## 11. Analysis plan (`analysis.py`)

(a) E1 online: NB, WR, win/tie/loss, tier decomposition, betting CS for NB
(`wincs.betting_cs_ternary`), CS for WR among decided pairs
(`wincs.win_ratio_cs_decided`), betting CS for the success difference, guarded
decision and first-crossing indices, fixed-horizon decision at n = 295, and
per-benchmark NB for pairs whose two arrivals share a benchmark.
(b) E2 shadow: `wincs.task_level_scores` (pairing 'all' over replicates) and
`wincs.clustered_summary` (t reference, T-1 df) pooled, per benchmark, and
equal-weight stratified; tier contribution means.
(c) Components (B - A): success, latency_s, completion_tokens, prompt_tokens,
n_llm_calls, n_executions: same-task paired t CIs over tasks (cluster =
task) and, for E1, Welch CIs across the two independent arms; medians and
ratio of means for latency and tokens; failure accounting per variant.
(d) Decision-rule table on the same data: success-only (paired CI), Pareto on
means, utility grid u = w1 d_success - w2 rel_d_latency - w3 rel_d_tokens for
w in {(1,0,0), (.8,.1,.1), (.6,.2,.2), (.5,.25,.25), (.34,.33,.33), (.2,.4,.4)}
(point estimates), hierarchical NB (CI/CS), guarded (NB and non-inferiority),
conjunction (all components non-inferior/better), plus the anytime guarded
decision from (a).
(e) Sensitivity: relative tolerance in {0, 0.10, 0.20} for the non-success
tiers, crossed with four tier orders: success > latency_s > completion_tokens
and success > completion_tokens > latency_s (both with the frozen absorbing
rule), and, testing H4, the naive resource-first hierarchies
latency_s > success > completion_tokens and completion_tokens > success >
latency_s with NO eligibility mask: every tier is compared for every pair
(the absorbing rule is defined relative to success being the top tier and is
not applied when it is not; a pair is decided at the first tier that is not a
tie under its tolerance). NB with CI/CS and the decision for E1 and E2 under
each of the 12 rows (`sensitivity.csv`, column `eligibility`). H4 is
supported if the two resource-first rows give NB < 0 (prefer A) where the
frozen hierarchy gives NB > 0. The utility grid in (d) is kept as the second,
weight-based view of the same disagreement.
Primary result = (a) guarded decision and (b) pooled NB with its CI under the
frozen hierarchy; everything else is secondary or sensitivity.

## 12. How the replication bears on the paper

- It provides an actual prospective randomized stream with independently
  generated seeds, a frozen design and no paid API, complementing the
  historical replays and the 9-pair paid pilot; it tests whether the guarded
  anytime-valid rule reaches a decision within 295 independent pairs on a
  real, cheap system pair, and how E1 (cross-arrival) and E2 (same-task)
  precision compare on the same episodes.
- It exercises the disagreement between objectives (success-first vs
  latency/token-first) on real outcomes, which the decision-ablation
  simulations only show synthetically.
- Limits: one model, one hardware configuration, function-level coding tasks
  with binary automatic verification (no long-horizon tool use, no human
  grading), latency specific to a local single-stream server, and no
  production traffic. MBPP/HumanEval are widely used in code-model training
  data, so absolute success rates are optimistic; the between-variant contrast
  is the object of interest, not the absolute level. If the guardrail or win
  process does not cross by n = 295, the paper must report that the stream was
  too short for this effect size at alpha 0.05, not weaken the claim ex post.
  If B has lower success (H1 false), the hierarchy will prefer A and the paper
  reports that as the pre-specified outcome.

## 13. Deviations log

| date | deviation | reason | effect on analysis |
|---|---|---|---|
| 2026-09-18 | RLIMIT_AS 2 GB cannot be set on macOS (setrlimit rejected); RLIMIT_CPU 10 s and 10 s wall clock apply | kernel limitation | memory guard best-effort on this host; recorded per episode |
| 2026-09-18 (pre-outcome) | MBPP prompt changed from "task text + first assert of test_list" to "task text + def signature line only"; all asserts graded | audit item 1: the first assert was shown and graded, contradicting section 5 | none on B vs A (both variants see the same prompt); absolute success rates may be lower than the MBPP convention; `tasks.json` unchanged (hash preserved) |
| 2026-09-18 (pre-outcome) | success now requires the verifier sentinel; early exits with status 0 are failures | audit item 3: wrong code + `raise SystemExit(0)` passed | outcome definition tightened before any outcome exists |
| 2026-09-18 (pre-outcome) | latency_s excludes hidden-test verification (`verify_seconds` recorded separately) | audit section 5 | tier-2 comparisons and latency means refer to system time only |
| 2026-09-18 (pre-outcome) | static blocklist demoted to a recorded flag; Seatbelt + process-group kill + RLIMIT_NPROC are the guards; base interpreter instead of the venv symlink | audit item 2: 6 of 8 attack classes escaped the blocklist; repository `.env` was readable | `sandbox_flag` no longer forces success = False; flagged episodes are reported |
| 2026-09-18 (pre-outcome) | run refuses config drift (design/episodes hash), missing/mismatching model snapshot revision, mismatching served model id, concurrent runs (lock), `--only-pass 2` before pass 1; manifest append-only | audit items 4, 7.2, 7.3 and non-blocking items | none on estimands; provenance only |
| 2026-09-18 (pre-outcome) | sensitivity 11(e) extended with the two resource-first hierarchies (no eligibility mask) | audit item 7.1: H4 was not tested | H4 now has a pre-specified test |
| 2026-09-18 (pre-outcome) | timing pilot on 6 full-MBPP tasks outside the design (`timing_pilot.py`, `results/local_stream/timing_pilot/`) | runtime projection requested by the coordinator | none: pilot tasks are disjoint from the design by task_id and prompt text and never enter the analysis |
| 2026-09-18 (pre-outcome) | `extract_code` strips a trailing special token (`<|im_end|>`, `<|endoftext|>`, ...) in the no-code-block fallback | `mlx_lm.server` 0.31.3 leaves the stop token in `message.content` (seen in the smoke completion) | avoids a spurious SyntaxError when a reply has no code fence; identical for A and B |
| _pending_ | | | |

## 14. Licenses, model, hardware

- Model card `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` (fetched 2026-09-18):
  metadata `license: apache-2.0`; "Converted from Qwen/Qwen2.5-Coder-7B-Instruct"
  with mlx-lm 0.18.1, 4-bit. Base card `Qwen/Qwen2.5-Coder-7B-Instruct`: license
  Apache-2.0; 7.61B parameters; states improvements in code generation, code
  reasoning and code fixing and "a more comprehensive foundation for real-world
  applications such as Code Agents". Tool use here means executing
  self-written tests via the harness (the model emits code; the harness runs
  it); no native function calling is required, and the base card's code-agent
  statement is the capability we rely on.
- MBPP: HF dataset card `google-research-datasets/mbpp` license CC-BY-4.0
  (sanitized config: 427 problems); the source repository
  google-research/google-research is Apache-2.0. Attribution: Austin et al.,
  "Program Synthesis with Large Language Models" (2021).
- HumanEval: `openai/human-eval` LICENSE, "The MIT License", "Copyright (c)
  OpenAI"; 164 problems. Attribution: Chen et al., "Evaluating Large Language
  Models Trained on Code" (2021).
- Hardware at freezing: Apple M5, 32 GB unified memory, macOS 26.5.2, Python
  3.12.13, numpy 2.4.1, scipy 1.17.0, pandas 3.0.6, mlx_lm 0.31.3; 280 GB free.
  Estimated cache/runtime: 4.3 GB weights, 6-8 GB resident. The run manifest
  records the actual values and sha256 of every harness file.

## 15. Requirement checklist

Issue #1 (larger prospective randomized stream)

| requirement | where |
|---|---|
| frozen design before outcomes | section 4; `design.json` + sha256 generated 2026-09-18 before any model call |
| independently generated seeds | section 4: seed 20260918 via SeedSequence, unrelated to the pilot's seeds; trial 2 seed 20260919 |
| task strata | section 3: benchmark stratum; per-stratum and stratified results in 11(b) |
| retained failures and every enrolled episode | section 7; `episodes.jsonl` keeps every arrival incl. errors |
| same-task paired shadow vs randomized AB/BA exposure | section 2 (E1 vs E2), section 4 |
| exact model/config/harness versions | section 5, 14; `run_manifest.json` (snapshot revision + per-file sha256, `/v1/models`, served model id of the smoke completion, package versions, harness file hashes, sandbox profile hash, git hash); run refuses a config hash different from the design or from existing episodes |
| immutable run manifest | `run_manifest.json` is append-only: one record per invocation, earlier records and top-level fields never modified (`test_manifest_append_only`) |
| task/seed accounting | `design.json` lists every arrival; `data_manifest.json`; resume keyed by (task, variant, trial) |
| correct independent-unit uncertainty | E1: pairs independent (betting CS, e-processes); E2: task clusters (`clustered_summary`) |
| continuous-monitoring analysis | section 10; `monitor_pass1.csv`, `monitor_state.json` |
| abstention/incomplete runs reported | section 7; `failure_accounting` per variant |

Issue #2 (local-model replication)

| requirement | where |
|---|---|
| model license and tool-use capability verified | section 14; served model produces runnable code on the 6 out-of-design pilot tasks (`timing_pilot/summary.json`) |
| cache/runtime space estimated | section 14; README resource estimates |
| model snapshot documented | section 5 (revision, bytes); `run_stream.check_snapshot` locates the huggingface snapshot, records revision, file list, sizes and sha256, refuses if revision != `model_revision_expected`; served model id checked on a smoke completion and on every episode |
| existing public verifiable benchmark, fixed task selection | section 3 (all 591 tasks, no selection) |
| two meaningfully inexpensive workflow variants | section 5 (1 call vs <= 4 calls, local model) |
| weights outside the repo | section 5; huggingface cache; `work/` git-ignored |
| runnable instructions | README.md |
| hardware/config hashes | `run_manifest.json`: hardware, config hash, harness file sha256 |
| frozen task and seed manifest | `data_manifest.json`, `design.json` |
| retained failure records | section 7 (incl. sentinel, hack/static flags, entry-point failures) |
| latency measurement scope | section 8 (excludes hidden-test verification; `verify_seconds` separate) |
| resource use | manifest (server RSS at start/end of each invocation, snapshot bytes) + README + `results/local_stream/timing_pilot/summary.json`; per-episode tokens, calls, executions |
| task-level hierarchical scores and component outcomes | `task_scores.csv`, `episodes_flat.csv`, 11(b)-(c) |
| uncertainty appropriate for repeated tasks | task-clustered CIs (E2) |
| how the replication changes or limits conclusions | section 12 |

## 16. Freeze

- Design frozen: `results/local_stream/design.json`, whole-file sha256
  `6175b81562efe1b1c87b113050f70c5daab2143e272cba39fb9a796f0d645457`, content
  sha256 `da84ff558deb2baf19d8728e3c50aea9e01e2411a5855cf07a2fac3594b8d4ad`,
  config sha256 `2dfb51966780698be326a8897c9e384a5513a7c1a47505c42b8a15c6c5baaf5b`
  (unchanged by the audit fixes; `config.json` was not edited).
- Harness frozen at commit: `d9793d56430e65c600e241f325a7cd540d23a668`.
  The post-fix sha256 of every harness file is in
  `results/local_stream/dryrun/run_manifest.json` (invocation record,
  `harness_file_sha256`, incl. `protocol.md`) and will be re-recorded by the
  first real invocation in `results/local_stream/run_manifest.json`.
- Model snapshot: `019cc73c45c770444708a6dd8690c66243cc5c80`, 11 files,
  4,295,890,004 bytes, per-file sha256 recorded by the pre-flight check.
- Sandbox profile sha256 on the freeze host: recorded in the dry-run manifest
  (`sandbox.profile_sha256`) and re-recorded per invocation; it depends on
  `$HOME`, the interpreter prefix and `$TMPDIR`.
- Any change to `experiments/local_stream/*.py`, `config.json` or this file
  after the first real episode is a deviation (section 13).
