# Pre-registered protocol: tau2-bench open-model prospective stream (issues #1 and #2)

Status: design FROZEN on 2026-09-18 (revision 2, see section 17) before any
tau2 episode of the design was run. The only tau2 episodes run on this stack
so far are the coordinator's pipeline checks: two smoke runs of airline task
`0` (`data/simulations/{local_smoke,llama_smoke}`, one trial each, max-steps
40/60) and one tool-call verification of the arm-B model on a RETAIL task
(`data/simulations/smoke_retail_4b`, retail task `0`, one trial, max-steps
60). Airline task `0` is therefore EXCLUDED from the design (section 3); the
retail task belongs to another domain and is not a design unit. Design file
`results/tau2_open/design.json`, whole-file sha256
`c8fa5728e8a9602813ffac10ea4ef88642ef3550aa9d5a5b7028c25586186597`
(including generation timestamp and provenance fields); content-only sha256
(arrivals, seed, task list hash, config hash; what `design.py
--print-sha-only` reproduces in any process, independent of
`PYTHONHASHSEED`)
`8b515c3b1590178144b28475240dd574a65dd3fa426ee6951ca41b0c6144ea9d`; task
list sha256 `ce69ae4bffd2fb06c43d3cbbf08c121bee4f13baa93b6b85b4a14e73acf5d310`;
config sha256 `347b7bbdd8b24ef73f8e7f4047625a7d5cd7ec56d7a9e054c6efbdc605122c58`.
Any change after the first design episode is a deviation and must be logged
in section 13. The mock dry run (`run_tau2_open.py --dry-run`, e.g.
`results/tau2_open/dryrun/`) is pipeline testing only and is never reported
as a result. The auditor decides readiness; this document is the
pre-registration the audit checks.

## 1. Question and hypotheses

We compare two open-weight agent models on tau2-bench (airline domain) with
the SAME open-weight user simulator, so that every model in the loop is
open, free of paid APIs and reproducible by other researchers:

- Arm A (incumbent): agent `qwen2.5-7b-instruct` (Qwen/Qwen2.5-7B-Instruct-GGUF,
  Q4_K_M; base Qwen/Qwen2.5-7B-Instruct, Apache-2.0).
- Arm B (candidate): agent `qwen3-4b-instruct-2507`
  (unsloth/Qwen3-4B-Instruct-2507-GGUF, Q4_K_M; base
  Qwen/Qwen3-4B-Instruct-2507, Apache-2.0). B is a NEWER but SMALLER model
  than A.
- User simulator for BOTH arms: `qwen2.5-7b-instruct` (same GGUF, same server).

The pre-registered deployment question is whether the cheaper candidate B can
replace the incumbent A under the guarded rule (section 10). Hypotheses,
stated before data:

- H1 (direction-uncertain): task success differs between the arms. The
  direction is NOT pre-specified: A is larger, B is a newer generation with
  a native tool-calling template, so either sign is plausible a priori. The
  test is the same-task success-difference CI (B - A) excluding 0, and the
  guarded decision states whether B may replace A.
- H2 (directional, expected): B uses fewer agent completion tokens per
  episode than A (same-task token-difference CI < 0).
- H3: the hierarchical decision is determined by success first: under the
  frozen hierarchy (success > agent completion tokens > assistant tool calls,
  absorbing rule) the success tier's contribution to NB has the sign of NB
  and its magnitude is at least the combined magnitude of the lower tiers'
  contributions (`success_tier_determines_sign`, reported for E1 and E2).
- H4: a token-first (cost-first) rule (sensitivity, section 11(e)) prefers B
  (NB > 0 with CI/CS lower bound > 0) if H2 holds; when the frozen hierarchy
  does not prefer B, the objectives disagree.
- H5: absolute success levels are not comparable to the paper's archived
  commercial-model tau2 runs: the user simulator is a 4-bit 7B model that
  follows scenarios less faithfully than GPT-4.1, so success is lowered for
  both arms; only the within-experiment contrast (A vs B under one user
  simulator, one hardware configuration) is the object of inference. Success
  rates are reported per arm and never compared with archived levels.

Scores are oriented B vs A throughout (+1 = arm B preferred), exactly as in
`experiments/local_stream/`; "deploy B" means "the candidate replaces the
incumbent", and the guardrail protects against deploying B when its success
is inferior by more than the margin.

## 2. Design targets and estimands

Two contrasts from the same episodes, reported separately:

- E1 cross-arrival (online) contrast: for the 49 prespecified pass-1 pairs
  the two arrivals are different (task, trial) units, each observed once
  under one arm, arm order randomized by R_k. Z_k = hierarchy(B episode vs A
  episode) compares across units; E[Z_k] is the population net benefit of B
  over A for a random pair of arrivals from the unit population. This is the
  design an online evaluator can run when it cannot replay the same task to
  both systems. Block 1 (arrivals 1-49, trial 0) visits every task exactly
  once, block 2 (arrivals 50-98, trial 1) repeats the tasks with trial 1.
  Because a block holds an odd number of units, pair 25 (arrivals 49 and 50)
  straddles the two blocks. The prespecified block-1 subset is the set of
  pairs whose two arrivals are both in block 1 = pairs 1-24 (48 distinct
  tasks), which covers the monitoring minimum of 20 pairs; a pair's block in
  the outputs is the larger block of its two arrivals, so pair 25 is assigned
  to block 2 and `n_pairs_straddling_blocks` (= 1) is reported. Pairs in
  block 2 are not independent of pairs in block 1 that involve the same
  task. The primary E1 analysis uses all 49 pairs and states this; the
  block-1-only analysis (24 pairs, distinct tasks) is a prespecified
  secondary result.
- E2 same-task shadow contrast: both arms are run on every (task, trial)
  unit, so each task has 2 A and 2 B episodes. Task-level win/loss scores
  average the cross comparisons within task (`wincs.task_level_scores`,
  pairing `all` = 4 comparisons; `offdiagonal` (2, distinct tau2 trials) and
  `diagonal` (2, same tau2 trial) as sensitivity, mirroring the paper's
  amendment) and inference is task-clustered (`wincs.clustered_summary`, t
  reference with T-1 = 48 df). Cluster-robust inference is valid whatever the
  dependence between the two trials of an arm.

Because tau2 executes each arm as a batch (trial-major, task order 1..49),
the EXECUTION order is not the ARRIVAL order. The stream order and the
per-pair orientation are prespecified in `design.json` before any outcome
exists, and the analysis uses only those prespecified pairings; there is no
adaptivity (no arm assignment, task selection or stopping depends on
observed outcomes). Sequential validity (e-processes, betting CSs) therefore
refers to the prespecified sequence Z_1, ..., Z_49, which is the sequence an
online evaluator would have observed had the episodes been run in arrival
order; it does not claim that the episodes were physically produced in that
order. Execution never stops early.

## 3. Task set

49 of the 50 tasks of the tau2-bench `airline` domain (`data/tau2/domains/
airline/tasks.json`, ids "1".."49"; sha256 of tasks.json
`ccd8ba737b4cc371415af70151187788f728d6108d0916e73bb4317b40542052`, policy.md
`10dc0525421521208be39cee235bba84a16e2bcba9899eb93d92cd81d2f62fc4`, db.json
`1af9fea6e03ca7ca15a22bb3fcaf3e351393e3fc9070b6777947da8996f7531b`), passed
explicitly via `--task-ids`. Task `0` is excluded (config
`excluded_task_ids`) because the coordinator's pipeline smoke runs
(`llama_smoke`: same 7B stack as arm A, outcome success, 397 completion
tokens, 1 tool call, 13 messages, 60 s; `local_smoke`: mlx stack, failure)
used it before this protocol was written; the exclusion was decided before
any design episode and the smoke outcomes never enter the analysis. No other
selection or exclusion. tau2 commit
`b7ea9074c1cba482b30687fecdb5c8425fd6f619` (installed from source with `uv`).
One domain only (no strata); the paper's three-domain hierarchy is mirrored in
the outcome hierarchy, not in the task set. Two tau2 trials per task per arm:
98 units per arm, 196 episodes in total.

## 4. Design (frozen; `design.py`)

- Seed 20260918 -> `numpy.random.SeedSequence` -> `default_rng`; independent
  of `PYTHONHASHSEED` (tested in two processes with different hash seeds).
- Units: the 98 (task, trial) pairs (49 tasks x trials {0, 1}).
- Arrival order (`arrival_blocking = "by_trial"`): arrivals 1..49 are a random
  permutation of the 49 trial-0 units; arrivals 50..98 a random permutation
  of the 49 trial-1 units. Each block visits every task exactly once. This is
  a stratified random permutation of the 98 units; it was chosen (before any
  outcome) so that the first pairs, which cover the monitoring minimum of 20
  pairs, compare distinct tasks only (section 2).
- Pairs: arrivals (2k-1, 2k), k = 1..49. Orientation R_k ~ Bernoulli(1/2),
  fixed per pair: R_k = 1 means the first arrival of pair k is observed under
  arm A in pass 1 and the second under arm B; R_k = 0 reverses (22 of the 49
  pairs have R_k = 1; 26 of the 49 tasks have the same pass-1 arm in both
  trials). No unpaired arrival. Pair 25 straddles the blocks (arrival 49 =
  trial 0, arrival 50 = trial 1).
- Pass 1 = the single-exposure stream: each unit observed under its
  `pass1_arm`. Pass 2 = the complementary arm on the same unit (shadow). In
  execution both passes are produced by the two tau2 batches (arm A: all 98
  units; arm B: all 98 units); which episode is "pass 1" and which is
  "pass 2" for a unit is fixed by `design.json` and joined by
  `build_episodes.py`.
- tau2 seeds: `--seed 300` (tau2 default); tau2 derives the per-trial seeds
  `random.seed(300); [randint(0, 10**6) for 2 trials]` = [626729, 373753],
  identical for both arms (recorded per episode and checked against the
  frozen expectation). The tau2 trial seed is not forwarded to the model
  server; with agent temperature 0.3 (section 5) the two trials of a unit are
  genuine sampling replicates of the agent under llama.cpp's own per-request
  sampler seed, plus run-to-run nondeterminism of the serving stack. The
  fraction of tasks whose two trials give identical outcome vectors is
  reported per arm (`replicate_identical_fraction`).

## 5. Models, serving, routing, sampling

- Agent A: `Qwen/Qwen2.5-7B-Instruct-GGUF`, revision
  `bb5d59e06d9551d752d08b292a50eb208b07ab1f`, files
  `qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` (3,993,201,344 bytes, sha256
  `dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db`) and
  `qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf` (689,872,288 bytes, sha256
  `539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a`);
  alias `qwen2.5-7b-instruct`; served on port 8081. The same server serves the
  user simulator for both arms.
- Agent B: `unsloth/Qwen3-4B-Instruct-2507-GGUF`, snapshot
  `a06e946bb6b655725eafa393f4a9745d460374c9`, file
  `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (2,497,281,120 bytes, sha256
  `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`), local
  path `~/.cache/huggingface/hub/models--unsloth--Qwen3-4B-Instruct-2507-GGUF/
  snapshots/a06e946bb6b655725eafa393f4a9745d460374c9/`; base weights
  `Qwen/Qwen3-4B-Instruct-2507` (a non-thinking instruct model; no `<think>`
  blocks); alias `qwen3-4b-instruct-2507`; served on port 8082 during arm B
  only.
- Server: llama.cpp `llama-server` built 2026-09-18 from commit
  `4fea119de30f6a923992780f6fd5ccb0bee5d47d` (version 0.4.1-dev, build
  b1-4fea119, AppleClang 21, Metal); flags `-m <gguf> --alias <alias> --port
  <port> -c 32768 -np 1 --jinja -ngl 99 --host 127.0.0.1`. `--jinja` applies
  the model's own chat template, which emits OpenAI-style structured
  `tool_calls` (`/props` `chat_template_caps.supports_tool_calls = true` for
  both models; verified end to end: the coordinator's `llama_smoke` airline
  episode on the 7B stack contains one structured tool call with reward 1.0,
  and the coordinator's `smoke_retail_4b` episode on the Qwen3-4B stack
  contains 5 structured tool calls with reward 1.0, served-model fields
  assistant = `qwen3-4b-instruct-2507`, user = `qwen2.5-7b-instruct`; the
  earlier `mlx_lm` stack produced zero tool calls). `-np 1` = one slot, so the
  32,768-token context is not split; the airline system prompt is about 4.9k
  tokens and 100 steps stay well inside it; a `context_window_exceeded`
  termination is retained as an outcome if it happens. The harness starts the
  servers it needs with exactly these flags and stops those it started; a
  server already listening on a needed port with other settings (alias, model
  path, context, slots) is refused (section 9). Weights stay in the
  huggingface cache outside the repository.
- Routing: tau2 forwards `--agent-llm-args` / `--user-llm-args` verbatim as
  `litellm.completion(**kwargs)`, and litellm 1.81.11 reads `api_base` from
  those kwargs (`api_base = kwargs.get("api_base", None)` in
  `litellm.main.completion`; verified live and in dry mode with two stubs by
  the audit). Arm A: agent `openai/qwen2.5-7b-instruct` with `api_base` 8081,
  user `openai/qwen2.5-7b-instruct` with `api_base` 8081. Arm B: agent
  `openai/qwen3-4b-instruct-2507` with `api_base` 8082, user unchanged on
  8081. No proxy and no multi-model router are used. `OPENAI_API_KEY` is set
  to a placeholder string when unset (litellm requires one; the local server
  ignores it); `OPENAI_API_BASE` points at 8081 as a fallback only. After each
  batch the served model id (`raw_data.model`) of every ASSISTANT message is
  checked against the arm's agent alias and of every USER message against
  the user-simulator alias (`info_mismatches` in the manifest); a
  single-model llama-server answers with its own alias, so a misrouted role
  is detected.
- Sampling: agent temperature 0.3 in BOTH arms; user simulator temperature
  0.0; both sent per request in the llm args (`agent_temperature`,
  `user_temperature` in `config.json`; the info block's `llm_args` are
  checked after each batch). This deviates from the released tau2 runs and
  from the tau2 default (temperature 0 for both roles; section 13): with a
  positive temperature the two tau2 trials are genuine replicates under
  llama.cpp sampling instead of near-copies of one greedy decode. Per-request
  seeds: tau2 forwards its per-trial seed (626729 for trial 0, 373753 for
  trial 1; `orchestrator.set_seed` -> `LLMConfigMixin.set_seed`) as `seed`
  in every agent and user-simulator request, and llama-server seeds its
  sampler with it; both arms receive the same seeds and the two trials differ
  by seed, so they remain distinct sampling replicates. A re-run therefore
  reproduces the agent's sampling up to the serving stack's nondeterminism
  (Metal kernels, batching); the per-episode `seed` field is the record, since
  tau2's info block stores the pre-`set_seed` llm args. No other sampling parameter is sent; `max_tokens` is tau2's
  default (unset). Tool calls: tau2 passes the domain tool schemas with
  `tool_choice = "auto"`.
- tau2 flags: `--domain airline --agent llm_agent --user user_simulator
  --num-trials 2 --task-ids 1 ... 49 --max-steps 100 --max-errors 10
  --max-concurrency 1 --hallucination-retries 0 --seed 300 --save-to
  tau2_open_arm{A,B} --auto-resume --log-level WARNING`. `--max-steps 100`
  (tau2 default is 200) bounds an episode at 100 orchestrator steps; hitting
  it is an outcome (section 7). `--max-concurrency 1`: one episode at a time,
  one local inference stream, so durations are comparable between arms and
  not confounded by contention (section 8). `--max-errors 10`: tau2 default.
  `--hallucination-retries 0` (flag present in this tau2 version, default 3,
  documented as full-duplex only): passed explicitly so that no review model
  (`--review-model`, default a commercial model) can be invoked on any path;
  `--auto-review` stays at its default False.
- Prompts, policy, tools, user scenarios and the reward function are tau2's
  own at the pinned commit; nothing is modified.

## 6. Outcomes and the hierarchy

Per episode (`build_episodes.py`, `results/tau2_open/episodes.csv`): arm,
agent_model, user_model, task_id, trial, tau2_seed, arrival_index,
pair_index, position_in_pair, orientation, pass, block, success, reward,
agent_tokens_completion, agent_tokens_prompt, n_agent_llm_calls,
n_assistant_tool_calls, n_assistant_messages, n_user_messages,
n_tool_messages, n_messages, duration, agent_generation_seconds,
termination_reason, max_steps_hit, error, tokens_source,
tokens_estimated_calls, served_models, simulation_id, start/end time,
source_file, config_hash. Every episode of both batches is retained.

- success = `reward_info.reward == 1`. tau2 evaluates each task's
  `reward_basis`, which is `[DB, COMMUNICATE]` for every airline task at the
  pinned commit (database end state and required communicated facts); the
  reward is 1.0 only if every evaluated check passes; a missing reward is a
  failure. NL assertions are NOT evaluated under tau2's default
  `EvaluationType.ALL` (they are a WIP path that would call gpt-4.1), the
  airline environment has no LLM interface, `--auto-review` is off and
  `--hallucination-retries` is 0, so no LLM judge and no commercial model
  enter the agent, the user simulator, the environment or the reward.
- agent_tokens_completion / agent_tokens_prompt: litellm cost is 0 for these
  unmapped local model names, so cost is measured in tokens. tau2 stores the
  server's `usage` on every message produced by an LLM call
  (`get_response_usage`); assistant messages with `usage` are the agent's LLM
  calls (the scripted greeting at turn 0 has none; user-simulator usage sits
  on user messages and is NOT counted as agent cost). Completion and prompt
  tokens are summed over those assistant messages; prompt tokens count the
  context re-sent at every call. If an agent call lacks `usage`, its tokens
  are estimated from the message text and tool-call arguments (llama-server
  `/tokenize` when `--tokenize-url` is given, else characters/4), the
  episode is flagged `tokens_source = usage+estimate` with
  `tokens_estimated_calls`, and the counts are reported per arm. In the
  smoke JSONs every LLM call carried usage.
- n_assistant_tool_calls: number of structured tool calls emitted by the
  agent (sum of `len(tool_calls)` over assistant messages).
- duration: tau2's `duration` (wall-clock seconds of the whole simulation,
  section 8). agent_generation_seconds: sum of `generation_time_seconds` over
  assistant messages (agent inference only) for decomposition.
- termination_reason (tau2 enum: user_stop, agent_stop, max_steps, timeout,
  too_many_errors, agent_error, user_error, infrastructure_error,
  context_window_exceeded, unexpected_error); max_steps_hit = termination
  `max_steps`; error = the termination reason when it is not user_stop /
  agent_stop / max_steps.

Hierarchy (B vs A), tiers in order, mirroring `experiments/protocol.md`
(success > historical inference cost > assistant tool-call count): (1)
success, higher better, no tolerance; (2) agent_tokens_completion (cost
proxy), lower better, relative tolerance 0.05 (|dT| <= 0.05 x max(T_A, T_B)
is a tie at this tier; exact threshold equality is a tie); (3)
n_assistant_tool_calls, lower better, absolute zero tolerance (any strict
difference is decisive). Absorbing rule: tiers 2 and 3 are compared only if
both episodes succeeded; a pair with exactly one success is decided at tier
1; a pair with two failures is a tie. Implementation: `winstats.compare` with
the eligibility mask, identical to `experiments/local_stream/`.

## 7. What counts as a failure (outcomes, never exclusions)

Every (arm, task, trial) unit yields a record. success = False whenever tau2's
reward is below 1: any failed DB/communicate check, termination at
`max_steps` (100), `too_many_errors`, agent/user/infrastructure errors,
`context_window_exceeded`, or a missing reward. tau2 writes an
infrastructure-failure record for a unit whose simulation raised (controller
`make_infra_failure_sim`, termination `infrastructure_error`); within one
tau2 invocation it is kept with reward 0. On `--auto-resume`, however, tau2
DROPS `infrastructure_error` records from `results.json` and re-runs those
units (`runner/checkpoint.py`: `done_runs` excludes them). Therefore: (a) the
harness keeps, besides the canonical raw copy
`raw/tau2_open_arm<X>.json` (overwritten after every invocation), a
per-invocation copy `raw/tau2_open_arm<X>.<invocation_id>.json` that is never
overwritten, so every infrastructure-failure record of an interrupted
invocation survives; (b) the manifest records per arm run
`n_infrastructure_error_rerun_on_resume` (records present before the
invocation, i.e. re-run by tau2) and `n_infrastructure_error_now`; the paper
reports the total number of units re-run for infrastructure errors (sum over
invocations) and the number still failing in the final raw copy. No episode
is re-run for a bad OUTCOME; the only re-run paths are `--auto-resume` of a
unit absent from `results.json` (interrupted run) and tau2's own
infrastructure-error retry above. Zero-tool-call episodes are counted per arm
(`zero_tool_call_episodes`) as a diagnostic of the tool-calling stack (a
systematic zero would indicate a serving defect, as in the mlx feasibility
note, not an agent property). Abstentions do not exist in this task format.
Counts of every termination reason, max-steps hits, errors and
token-estimation flags per arm are reported (`components.failure_accounting`).

## 8. Latency / duration scope

`duration` is tau2's wall-clock time of the whole simulation: agent LLM
calls, user-simulator LLM calls (same 7B server for both arms), tool
execution in the environment and orchestrator overhead. It INCLUDES the user
simulator, which is why duration is a sensitivity tier (section 11(e)) and
not part of the primary hierarchy, matching `experiments/protocol.md`
("duration belongs in sensitivity because tau2 simulation duration includes
the user simulator"). `agent_generation_seconds` (agent inference time only)
is reported as a component. With `--max-concurrency 1` and one llama-server
slot per model, episodes are strictly sequential; during arm B two servers
are resident (7B user + Qwen3-4B agent) but only one request is in flight at
a time. Durations are conditional on the recorded hardware (section 14) and
exclude server start-up and model loading (servers are ready before tau2
starts; `load_seconds` is recorded in the manifest). Nothing else may use the
GPU while the stream runs.

## 9. Environment and integrity

The tau2 environment executes the airline tools against its in-memory
database; no model-written code is executed, so no sandbox is needed. The
harness never modifies tau2's data, prompts or reward code (file hashes in
section 3 are checked before each run). The run refuses to start when: the
config hash differs from `design.config_hash`; the task list hash differs
from the design; the tau2 or llama.cpp checkout commit differs from the
expected commit (read from `.git` files, no git command); any GGUF file is
missing or its size/sha256 differs; an airline data file hash differs; a
server already listening on a needed port has a different alias, model path,
context size or slot count (unless `--accept-running-server`, which is
recorded; the coordinator stops the temporary 8081/8082 servers used for the
smoke runs before launch, so the harness starts its own servers with the
frozen settings); another invocation holds `run.lock`. After each batch the
served model id of every agent message and of every user-simulator message,
the tau2 info block (agent/user llm, agent/user llm_args temperature, seed,
max_steps, num_trials, git_commit) and the per-trial seeds are compared with
the frozen configuration; mismatches are recorded in the manifest and change
its status. The manifest is append-only (one record per invocation; earlier
records and top-level fields are never modified).

## 10. Monitoring and decision semantics

For the prespecified pass-1 sequence, after each pair k the following are
computed from cumulative counts with `winstats.betting_log_e_ternary`
(mixture of 40 constant bets):

- win e-process: H0: E[Z] <= 0 (B, the candidate, not preferred);
- harm e-process: H0: E[Z] >= 0 (B not harmful), i.e. wins and losses swapped;
- guardrail e-process on D_k = success_B - success_A in {-1, 0, 1}: H0: E[D]
  <= -0.03 (B inferior by more than the margin).

alpha = 0.05, threshold log(1/alpha) each; decisions are read only after
min_n = 20 pairs. "Deploy B" (B may replace A) = win and guardrail
e-processes both crossed; "B harmful" = harm e-process crossed. Because tau2
executes arms in batches, the monitoring log (`monitor_pass1.csv`, e-values
at every pair; `monitor_state.json`, first-crossing indices) is computed
post hoc over the prespecified sequence by `analysis.py`; it is exactly the
log an online evaluator would have produced, since no quantity in it
depends on execution order or on anything observed. Execution never stops
early: all 196 episodes are run so that the fixed-horizon (E1 at n = 49) and
shadow (E2) analyses are available; the anytime-valid decision is the one at
the recorded crossing. The win and guardrail processes are used as a
conjunction, each a valid e-process at level alpha under its null, so the
guarded deploy decision has type-I error <= alpha under the respective nulls;
the harm process is a separately reported test. Arrivals are a stratified
random permutation of a fixed finite unit population (sampling without
replacement) and block 2 reuses the tasks of block 1, so pair scores are
exchangeable within block rather than i.i.d.; the E1 null is the
superpopulation null for a random pair of arrivals, and
`betting_log_e_ternary` tests the pointwise conditional null, as documented
in the project's replay analysis. The block-1 monitoring (pairs 1-24,
distinct tasks) is reported alongside.

## 11. Analysis plan (`analysis.py`)

(a) E1 online: NB, WR, win/tie/loss, tier decomposition and the H3 flag
`success_tier_determines_sign`, betting CS for NB
(`wincs.betting_cs_ternary`), CS for WR among decided pairs
(`wincs.win_ratio_cs_decided`), betting CS for the success difference,
guarded decision and first-crossing indices, fixed-horizon decision at n =
49, the number of pairs whose two units share a task (different trial), the
number of pairs straddling the blocks, and the same for the block-1 subset
(`online_block1`, pairs with both arrivals in block 1 = pairs 1-24).
(b) E2 shadow: `wincs.task_level_scores` (pairing `all`; `offdiagonal` and
`diagonal` as `shadow_pairing` sensitivity) and `wincs.clustered_summary` (t
reference, 48 df); tier contribution means and the H3 flag;
replicate-identical fraction per arm. Runs are sorted by tau2 trial within a
task before pairing (`runs_by_task`), so `diagonal` pairs the trial-0 A run
with the trial-0 B run and the trial-1 with the trial-1 run (same tau2 trial
seed, same user-simulator scenario decoding); `offdiagonal` pairs across
trials. `episodes.csv` is written trial-major per arm, but the pairing does
not depend on file order.
(c) Components (B - A): success, agent_tokens_completion, agent_tokens_prompt,
n_assistant_tool_calls, n_agent_llm_calls, duration,
agent_generation_seconds: same-task paired t CIs over tasks (cluster =
task; trials averaged within task) and, for E1, Welch CIs across the two
independent arms; medians and ratio of means; failure accounting per arm.
(d) Decision-rule table on the same data: success-only (paired CI), Pareto on
means (success up, tokens down, calls down), utility grid u = w1 d_success -
w2 rel_d_tokens - w3 rel_d_calls for w in {(1,0,0), (.8,.1,.1), (.6,.2,.2),
(.5,.25,.25), (.34,.33,.33), (.2,.4,.4)} (point estimates), hierarchical NB
(CI/CS), guarded (NB and success non-inferiority at margin 0.03),
conjunction (success non-inferior AND tokens lower AND calls lower), plus
the anytime guarded decision and the success-only betting CS from (a).
(e) Sensitivity (`sensitivity.csv`, 20 rows): relative tolerance for the cost
tiers (tokens, duration) in {0, 0.05, 0.10, 0.20} (tool calls keep
tolerance 0) crossed with five tier orders: success > tokens > calls with the
frozen absorbing rule (the primary row at 0.05); success > calls > tokens
(steps before tokens, absorbing); success > duration > tokens (duration as a
tier, absorbing); success > tokens > calls lexicographic WITHOUT the
absorbing rule (two failures ranked by cost); and, testing H4, tokens >
success > calls with NO eligibility mask (every tier compared for every
pair). NB with CI/CS and the decision for E1 and E2 under each row. H4 is
supported if the token-first row gives NB > 0 with a positive CI/CS lower
bound. The hypothesis table in `report.md` maps H1-H5 to these outputs.
Primary result = (a) guarded decision and (b) pooled NB with its CI under the
frozen hierarchy; everything else is secondary or sensitivity.

## 12. How this experiment bears on the paper

- It reproduces the paper's primary real-data hierarchy (success > inference
  cost > tool calls, absorbing failure, 5 % cost margin, 3-point success
  guardrail) on the same benchmark (tau2-bench airline) with open weights
  only: agent models, user simulator and serving stack are all open
  (Apache-2.0 weights, MIT software) and pinned by hash, so any researcher
  can re-run it without a paid API.
- It provides a prospective randomized stream with a frozen design and a
  same-task shadow contrast on the paper's own benchmark, complementing the
  historical replays (commercial models, GPT-4.1 user simulator) and the
  coding-task local stream (`experiments/local_stream/`).
- It exercises a realistic deployment question (can a newer, smaller,
  cheaper candidate replace the incumbent?) where success and cost can
  disagree (H3 vs H4) and the direction of the success contrast is genuinely
  uncertain a priori (H1).
- Limits: one domain, 49 tasks, 49 pairs (short stream: with |NB| around 0.2
  and 40 % ties, 49 pairs give limited power; if no e-process crosses by n =
  49 the paper reports that the stream was too short for this effect size at
  alpha 0.05, not a weakened claim); one hardware configuration; 4-bit
  quantized weights; a 7B user simulator that follows scenarios less
  faithfully than GPT-4.1, which lowers success for both arms and can add
  user-side noise; agent sampling at temperature 0.3, seeded per trial by tau2 and
  reproducible only up to the serving stack's nondeterminism; no production traffic. Absolute success rates are NOT
  comparable with the paper's archived commercial-model numbers (H5), only
  the within-experiment contrast is. Whatever the sign of the success
  contrast, the paper reports the pre-specified outcome.

## 13. Deviations log

| date | deviation | reason | effect on analysis |
|---|---|---|---|
| 2026-09-18 (pre-outcome) | arrival order is a per-trial-block stratified permutation, not an unrestricted permutation of the 98 units | so that the first pairs (covering min_n = 20) compare distinct tasks; decided before any outcome | E1 primary uses all 49 pairs; block-1 subset (pairs 1-24) reported (section 2) |
| 2026-09-18 (pre-outcome) | agent temperature 0.3 in both arms (user simulator 0.0) instead of the released tau2 runs' and tau2 default temperature 0 for both roles | so that the two tau2 trials are genuine sampling replicates; tau2 forwards its per-trial seed in every request and llama-server seeds its sampler with it, so replicates differ by seed and a re-run reproduces sampling up to serving-stack nondeterminism (section 5) | E2 trials are replicates rather than near-copies; `replicate_identical_fraction` reported; no effect on estimands |
| 2026-09-18 (pre-outcome) | llama-server context 32768 with one slot (`-c 32768 -np 1`) instead of the coordinator's smoke setting (`-c 16384`, 4 slots) | the airline agent prompt is about 4.9k tokens and grows with 100 steps | the runner refuses a running server with other settings unless `--accept-running-server` (logged); the harness starts its own servers |
| _pending_ | | | |

## 14. Licenses, models, software, hardware

- `Qwen/Qwen2.5-7B-Instruct-GGUF` model card (fetched 2026-09-18): license
  `apache-2.0`; quantized from `Qwen/Qwen2.5-7B-Instruct` (Apache-2.0); Q4_K_M
  listed at 4.68 GB. Tool use: the Qwen2.5 chat template (served by
  `--jinja`) defines `<tool_call>` JSON blocks that llama-server parses into
  OpenAI `tool_calls`; verified end to end in the coordinator's `llama_smoke`
  tau2 episode (1 structured tool call, reward 1.0).
- `Qwen/Qwen3-4B-Instruct-2507` model card (base weights; fetched
  2026-09-18 via WebFetch): the model "is released under the Apache 2.0
  license, as indicated by the 'License: apache-2.0' tag" on the Hugging
  Face model card; the local copy of the base repository (snapshot
  `cdbee75f17c01a7cc42f958dc650907174af0554`) carries an `Apache License
  Version 2.0` file. `unsloth/Qwen3-4B-Instruct-2507-GGUF` model card
  (fetched 2026-09-18 via WebFetch): "License: apache-2.0", base model
  `Qwen/Qwen3-4B-Instruct-2507`, Q4_K_M listed at 2.5 GB. Tool use: the Qwen3
  chat template served by `--jinja` reports `supports_tool_calls = true` and
  produced 5 structured tool calls with reward 1.0 in the coordinator's
  `smoke_retail_4b` tau2 episode (retail task, not a design unit).
- The whole stack is therefore Apache-2.0 (Qwen2.5-7B-Instruct GGUF,
  Qwen3-4B-Instruct-2507 base and GGUF) and MIT (tau2-bench, llama.cpp).
  tau2-bench: MIT License, Copyright (c) 2025 Sierra Research; commit
  `b7ea9074c1cba482b30687fecdb5c8425fd6f619`, package version 1.0.1, litellm
  1.81.11 (MIT). llama.cpp: MIT License, Copyright (c) 2023-2026 The ggml
  authors; commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d`.
- Hardware at freezing: Apple M5, 10 cores, 32 GB unified memory, macOS
  26.5.2; repository Python 3.12.13, numpy 2.4.1, scipy 1.17.0, pandas 3.0.6;
  about 268 GB disk free. Memory: 7B Q4_K_M about 4.7 GB + 32k KV cache
  about 1.8 GB; Qwen3-4B Q4_K_M about 2.5 GB + KV; both resident during arm
  B, about 11 GB total. Runtime planning estimate (not measured): the
  `llama_smoke` episode took 60 s for 13 messages on the 7B server and the
  `smoke_retail_4b` episode 150 s for 36 messages on the 4B agent + 7B user;
  with up to 100 steps, 1-5 min per episode is expected, i.e. roughly 4-16 h
  for 196 episodes sequentially. The manifest records the measured values.
- Cache: about 7.2 GB of GGUF files (7,180,354,752 bytes, three files) under
  `~/.cache/huggingface/hub`; nothing enters the repository except
  `results/tau2_open/` (raw tau2 JSON copies, about 5-20 MB per arm per
  invocation copy, and the derived CSV/JSON files).

## 15. Requirement checklist

Issue #1 (larger prospective randomized stream)

| requirement | where |
|---|---|
| frozen design before outcomes | section 4; `design.json` + sha256 generated 2026-09-18 before any design episode |
| independently generated seeds | section 4: design seed 20260918 via SeedSequence; tau2 trial seeds derived from `--seed 300` and recorded per episode |
| task strata | single domain (section 3); trial blocks reported (block-1 subset vs all) |
| retained failures and every enrolled episode | section 7; `episodes.csv` keeps every unit incl. errors and max-steps hits; per-invocation raw copies keep infrastructure-error records |
| same-task paired shadow vs randomized AB/BA exposure | section 2 (E1 vs E2), section 4 |
| exact model/config/harness versions | sections 3, 5, 14; `run_manifest.json` (GGUF sha256 + sizes, llama-server `/props`, tau2 commit, llama.cpp commit, smoke completion, package versions, harness file hashes, git hash); run refuses config drift |
| immutable run manifest | append-only invocations (`test_dry_run_builds_episodes_and_manifest_is_append_only`) |
| task/seed accounting | `design.json` lists every unit; tau2 `results.json` holds every simulation with seed; resume keyed by (trial, task, seed) |
| correct independent-unit uncertainty | E1: prespecified pairs (betting CS, e-processes; block structure disclosed); E2: task clusters |
| continuous-monitoring analysis | section 10; `monitor_pass1.csv`, `monitor_state.json` |
| abstention/incomplete runs reported | section 7; `failure_accounting` per arm |

Issue #2 (open/local-model replication)

| requirement | where |
|---|---|
| model licenses and tool-use capability verified | section 14 (Apache-2.0 throughout; structured tool calls verified in `llama_smoke` and `smoke_retail_4b`) |
| cache/runtime space estimated | section 14 |
| model snapshots documented | section 5: HF revisions/snapshots, per-file bytes and sha256; pre-flight re-hashes and refuses a mismatch |
| existing public benchmark, fixed task selection | section 3 (airline tasks 1-49; task 0 excluded before any outcome) |
| two meaningfully different systems | 7B incumbent vs newer 4B candidate under one user simulator |
| weights outside the repo | huggingface cache (section 14) |
| runnable instructions | README.md |
| hardware/config hashes | `run_manifest.json` |
| frozen task and seed manifest | `design.json`, config `task_ids`, airline data hashes |
| retained failure records | section 7 |
| latency measurement scope | section 8 |
| resource use | manifest (server RSS at start/end of each batch, load seconds, elapsed), per-episode tokens/calls/duration |
| task-level hierarchical scores and component outcomes | `task_scores.csv`, `episodes.csv`, 11(b)-(c) |
| uncertainty appropriate for repeated tasks | task-clustered CIs (E2) |
| how the replication changes or limits conclusions | section 12 |

## 16. Freeze

- Design frozen: `results/tau2_open/design.json`, whole-file sha256
  `c8fa5728e8a9602813ffac10ea4ef88642ef3550aa9d5a5b7028c25586186597`, content
  sha256 `8b515c3b1590178144b28475240dd574a65dd3fa426ee6951ca41b0c6144ea9d`,
  config sha256 `347b7bbdd8b24ef73f8e7f4047625a7d5cd7ec56d7a9e054c6efbdc605122c58`,
  task list sha256 `ce69ae4bffd2fb06c43d3cbbf08c121bee4f13baa93b6b85b4a14e73acf5d310`.
- Harness frozen at commit: `<FREEZE_COMMIT_ID>` (to be filled by the
  coordinator after committing `experiments/tau2_open/` and
  `results/tau2_open/design.*`; this sandbox runs no git command). The
  sha256 of every harness file is recorded by each invocation
  (`harness_file_sha256`, incl. `protocol.md`).
- Model files: the three GGUF files of section 5 (7,180,354,752 bytes in
  total), re-hashed by the pre-flight check of every invocation.
- Servers: llama.cpp commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d`; tau2
  commit `b7ea9074c1cba482b30687fecdb5c8425fd6f619`; started by the harness
  with the frozen flags (section 5).
- Any change to `experiments/tau2_open/*.py`, `config.json` or this file after
  the first design episode is a deviation (section 13).

## 17. Revision history (pre-freeze; no outcome of the design existed)

Revision 1 (2026-09-18 12:24): first frozen version (audit
`reviews/tau2_open_preregistration_audit.md`): 50 airline tasks, arm B =
Qwen2.5-3B-Instruct (Qwen Research License, non-commercial), temperature 0
for both roles, design content sha256
`0b968f1d678a381569aed364a99c22d5502caffd2d1a624d14583d3b2f133112`, config
sha256 `8ecde511b093eaa6b96cb6dc5ec99bd48cc21c3756bbe6b937d2bff7d5a90b52`.

Revision 2 (2026-09-18, this document; coordinator decisions after the
audit, applied before any design episode, so they are pre-freeze changes,
not deviations):

1. Airline task `0` excluded (audit must-fix 1, option "exclude"): task_ids
   "1".."49"; design regenerated with `design.py --force` (allowed: no
   `episodes.csv` or `raw/` existed); 98 units, 49 pairs; block-1 subset
   defined as the pairs whose two arrivals are both in block 1 (pairs 1-24,
   covers min_n = 20); counts updated in this protocol, README and tests
   (98/49/24); the four hashes re-frozen (status paragraph, section 16).
2. Arm B agent changed from Qwen2.5-3B-Instruct (Q4_K_M, Qwen Research
   License, non-commercial; declined alternative) to Qwen3-4B-Instruct-2507
   (base Apache-2.0; quantization `unsloth/Qwen3-4B-Instruct-2507-GGUF`
   snapshot `a06e946b...`, file `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`,
   2,497,281,120 bytes, sha256 `3605803b...`), alias `qwen3-4b-instruct-2507`
   on port 8082 with `--jinja`; structured tool calls verified by the
   coordinator on a synthetic prompt and on one tau2 RETAIL task (reward 1.0,
   5 tool calls, served-model fields assistant = `qwen3-4b-instruct-2507`,
   user = `qwen2.5-7b-instruct`). The whole stack is now Apache-2.0 / MIT
   (section 14); the Qwen Research License row of the revision-1 deviations
   log is withdrawn.
3. Agent temperature 0.3 in both arms, user simulator 0.0 (section 5;
   deviation from the released runs' temperature 0 logged in section 13);
   per-trial seeds are forwarded by tau2 in every request (see item 5). The
   server flag `--temp 0` of revision 1 was dropped
   from `llama_extra_args` because temperature is sent per request by tau2
   for both roles.
4. Hypotheses reworded (section 1): H1 direction-uncertain (deployment
   question: can the cheaper candidate B replace the incumbent A under the
   guarded rule), H2 B uses fewer completion tokens (expected), H3 the
   hierarchical decision is determined by success first
   (`success_tier_determines_sign`), H4 a token-first rule prefers B if H2
   holds, H5 absolute success levels are not comparable to the paper's
   archived commercial-model runs (weaker user simulator).
5. All five audit should-fix hardenings applied: (i) `check_results_info`
   verifies the served model of every user-simulator message (and the
   llm_args temperatures); (ii) `--hallucination-retries 0` is passed (flag
   exists in this tau2 version); (iii) section 6 reward wording
   (`reward_basis = [DB, COMMUNICATE]`, no NL assertions, no LLM judge);
   (iv) per-invocation raw copies and the INFRASTRUCTURE_ERROR resume note
   (section 7); (v) `diagonal` pairing = same tau2 trial, now enforced by
   sorting runs by trial (section 11(b)).
6. The harness starts its own servers with the frozen settings; the
   coordinator stops the temporary 8081/8082 smoke servers before launch;
   the pre-flight refusal for a mismatched running server is kept.

Still open for the coordinator: the freeze commit id (section 16) after
committing; stopping the temporary servers; launching after the other GPU
experiment ends.
5. Seed wording corrected after the round-2 audit (2026-09-18, pre-outcome):
   earlier text said no per-request seed is sent; in fact tau2 b7ea907
   forwards the per-trial seed (626729 / 373753) as `seed` in every agent and
   user request (`orchestrator.set_seed` -> `LLMConfigMixin.set_seed`) and
   llama-server seeds its sampler with it (sections 4, 5, 12, 13 updated).
   `config.json` was left untouched (option a of the audit) so the frozen
   hashes are unchanged; its `sampling_note` field is superseded by section 5
   of this protocol.
