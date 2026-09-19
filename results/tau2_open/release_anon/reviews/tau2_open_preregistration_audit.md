# Pre-registration audit: `experiments/tau2_open/` (tau2-bench airline, open weights only)

Auditor role: independent pre-registration auditor (did not write any of this code).
**Round 2 (re-audit of pre-freeze revision 2) is appended at the end of this file; its verdict supersedes the round-1 verdict below.**
Date: 2026-09-18. Scope: `experiments/tau2_open/` (9 files), `results/tau2_open/design.json`
(frozen), `results/tau2_open/dryrun/`, the tau2-bench checkout at commit `b7ea907` and the
two smoke JSONs under its `data/simulations/`. No git command, no paid API, no model call:
every check below ran against local files, two throwaway HTTP stubs on ports 8098/8099, or
GET `/props` on the coordinator's running 8081 server. No tau2 episode was run; the GPU was
not used; nothing under `results/tau2_open/` was modified.

**Verdict: NOT YET READY TO FREEZE, for one pre-registration decision, not for a harness
defect.** The harness, design, parser, metrics, hierarchy semantics, estimands, refusal paths
and tests all pass independent re-execution. Three items must be closed before the first
design episode (section "Must fix"): (1) the coordinator's `llama_smoke` run is a same-stack
arm-A episode of design unit (task `0`, trial 0) whose outcome was known before the protocol
was written, and the brief's rule is that smoke tasks are excluded from the design; the
protocol keeps task `0` and does not log this in the deviations table; (2) the
`<FREEZE_COMMIT_ID>` placeholder; (3) the running 8081 server does not match the frozen
server settings and must be stopped (not accepted). Five small hardenings are recommended
(section "Should fix"); because any change after the first episode is a deviation, they
should be applied now or explicitly declined.

| # | Item | Verdict |
|---|---|---|
| 1 | Design determinism, pairing and orientation | **PASS** |
| 2 | Agent/user routing to the two servers actually verified | **PASS** (independently re-verified in dry mode) |
| 3 | Parser correctness on `local_smoke` and `llama_smoke` | **PASS** (hand counts match) |
| 4 | Metric definitions (tokens source, duration scope, tool-call counting) | **PASS** (one wording fix, should-fix 3) |
| 5 | Hierarchy / tolerance semantics vs `winstats.compare` and `experiments/protocol.md` | **PASS** |
| 6 | Estimands E1 / E2 | **PASS** with remarks |
| 7 | Protocol completeness vs issues #1/#2 and deviations log | **FAIL** on the task-0 smoke disclosure (must-fix 1); otherwise complete |
| 8 | Reproducibility: hashes, manifest, lock/refusal paths, resume | **PASS** (freeze commit id pending, coordinator step) |
| 9 | Licenses | **PASS** (3B is Qwen Research License, non-commercial; disclosed) |
| 10 | No design episode executed | **PASS** |
| 11 | Unit tests | **PASS** 15/15 in 1.5 s |
| 12 | No commercial model anywhere in the loop (user's requirement) | **PASS** (verified in tau2 source; see item 2) |

All reproducers use `PY=<REPO>/.venv/bin/python`
from the repository root, or `uv run python` inside the tau2-bench checkout
`<TMP>/tau2-bench`.

---

## 1. Design determinism, pairing and orientation - PASS

Verified independently (not via the builder's tests only):

- `design.py --print-sha-only` under `PYTHONHASHSEED=0` and `=12345` (two processes) gives the
  same content sha256 `0b968f1d678a381569aed364a99c22d5502caffd2d1a624d14583d3b2f133112`, and
  `generate(cfg, 20260918)` in-process reproduces the frozen `design.json` content exactly.
- Whole-file sha256 of `results/tau2_open/design.json` = `b88e3deb...3251495` = `design.sha256`;
  `config_hash` in the design = sha256 of canonical `config.json` = `8ecde511...a90b52`;
  `task_list_sha256` = `a48ccc61...0648b` recomputed from config; `generator_sha256` recorded in
  the design equals the current sha256 of `design.py` (`3e0aef09...c488fa`), so the generator was
  not edited after generation.
- 100 arrivals, 50 pairs, 0 unpaired; arrivals 1-50 are all trial-0 units, 51-100 all trial-1
  units; each block visits each of the 50 tasks exactly once; pairs (2k-1, 2k) never contain the
  same task twice (0/50); `{pass1_arm}` of a pair is `{A, B}`; `pass1_arm == A` iff
  `orientation == 1` for the first arrival; `pass2_arm` is the complement. 22/50 pairs have
  R = 1 (protocol section 4 says 22: correct). 28/50 tasks have the same pass-1 arm in both
  trials, 22 the opposite: as expected under independent Bernoulli draws.
- Orientation logic: `v1 = A if (R == 1) == (pos == 0) else B` reproduces the stated rule
  (R = 1: first arrival -> A, second -> B; R = 0 reversed). `check_pairing_invariants` catches
  a corrupted pair (tested). `write_design` refuses overwrite, refuses `--force` when
  `episodes.csv` or `raw/` exists, and `load_design` refuses a hash mismatch (tested).
- The per-trial-block stratified permutation (deviation from an unrestricted permutation of the
  100 units) was decided before any outcome, is stated in protocol sections 2, 4 and 13 and in
  `design.json` (`arrival_blocking`), has a legitimate purpose (the first 25 pairs, covering
  `min_n = 20`, compare distinct tasks) and both the all-50 and block-1 analyses are
  pre-specified. Acceptable.

Reproducer:

```bash
PYTHONHASHSEED=0 $PY experiments/tau2_open/design.py --print-sha-only
PYTHONHASHSEED=12345 $PY experiments/tau2_open/design.py --print-sha-only
shasum -a 256 results/tau2_open/design.json; cat results/tau2_open/design.sha256
```

Minor: the final `for arm in (A, B)` loop of `check_pairing_invariants` does not use `arm`
(it counts units per task twice); harmless, no-op duplicate.

## 2. Routing of agent vs user simulator to the two servers - PASS

The harness relies on tau2 forwarding `--agent-llm-args` / `--user-llm-args` verbatim to
`litellm.completion(**kwargs)` and on litellm honouring `api_base` per call. I verified this
in dry mode, without any model server:

1. tau2 source (commit `b7ea907`): `cli.py` parses both flags with `type=json.loads` and puts
   them in `TextRunConfig.llm_args_agent` / `llm_args_user`; `runner/helpers.py` builds
   `AgentInfo(llm_args=config.llm_args_agent)` and `UserInfo(llm_args=config.llm_args_user)`;
   `agent/llm_agent.py` (line 128-133) and `user/user_simulator.py` (line 235-240) both call
   `generate(model=self.llm, ..., **self.llm_args)`; `utils/llm_utils.py::generate` calls
   `litellm.completion(model=model, messages=..., tools=..., tool_choice=..., **kwargs)`.
   No code path filters `api_base`. `litellm.drop_params = True` drops unsupported *provider*
   params, not litellm's own `api_base`.
2. Stub test through tau2's own `generate()`: two local HTTP stubs on 8098 and 8099 each answer
   a minimal chat completion whose `model` field names its own port; with
   `OPENAI_API_BASE=http://127.0.0.1:9/v1` (a closed port) in the environment,
   `generate(model='openai/qwen2.5-7b-instruct', api_base='http://127.0.0.1:8098/v1', temperature=0.0)`
   returned `raw_data.model = stub-8098`, the same with `openai/qwen2.5-3b-instruct` and
   `api_base=...:8099/v1` returned `stub-8099`, a third call went back to 8098; hit counts
   `{8098: 2, 8099: 1}`; the request bodies carried `model = qwen2.5-7b-instruct` /
   `qwen2.5-3b-instruct` and `temperature = 0.0`. So the per-call kwarg is honoured and wins
   over the environment fallback, in the same process, for two different targets.
3. `run_tau2_open.tau2_command` sets `api_base` 8081 for the user in both arms, 8081 for arm A's
   agent and 8082 for arm B's agent (unit test `test_tau2_command_routes_roles_to_their_servers`,
   re-run). `OPENAI_API_BASE` is only a fallback (8081).
4. Post-hoc check: `check_results_info` compares `raw_data.model` of every assistant message with
   the arm's alias and the tau2 `info` block (agent/user llm, seed, max_steps, num_trials,
   git_commit, trial seeds) with the frozen config. A single-model llama-server ignores the
   request's `model` field and answers with its own alias, so a misrouted agent would be caught.
5. Pre-flight per server: `Servers.ensure` probes `/props` and `/v1/models` and refuses an alias,
   model path, context or slot mismatch; `smoke_check` sends one non-task completion per port
   and refuses a model-id mismatch or missing `usage`.

tau2 defaults that could have put a commercial model in the loop, checked in source:
`--auto-review` default False (review model `claude-opus-4-5` unused); `--hallucination-retries`
default 3 but the check runs only when `result.ticks` is non-empty (full-duplex voice runs), so
it is inert for text runs (both smoke JSONs: `hallucination_retries_used = 0`,
`hallucination_check = null`); NL-assertion evaluation (`DEFAULT_LLM_NL_ASSERTIONS =
gpt-4.1-2025-04-14`) is only invoked under `EvaluationType.NL_ASSERTIONS` / `ALL_WITH_NL_ASSERTIONS`
(marked WIP), not under the default `ALL`; all 50 airline tasks have `reward_basis = [DB,
COMMUNICATE]` and the smoke `reward_info` shows `nl_assertions: null`; the airline environment
has no LLM interface (`interface_agent.py` with `DEFAULT_LLM_ENV_INTERFACE` is not used by the
airline domain). Hence the agent, the user simulator, the environment and the reward are all
free of commercial models. Passing `--hallucination-retries 0` explicitly is recommended
(should-fix 2) so the behaviour does not depend on the `ticks` guard.

Reproducer (dry, no model call; run inside the tau2-bench checkout):

```bash
OPENAI_API_KEY=sk-x OPENAI_API_BASE=http://127.0.0.1:9/v1 uv run python - <<'EOF'
import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
def H(port):
    class _H(BaseHTTPRequestHandler):
        def do_POST(self):
            n=int(self.headers.get('Content-Length',0)); self.rfile.read(n)
            b=json.dumps(dict(id='x',object='chat.completion',created=0,model='stub-%d'%port,
              choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='pong'))],
              usage=dict(prompt_tokens=3,completion_tokens=1,total_tokens=4))).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
        def log_message(self,*a): pass
    return _H
S=[HTTPServer(('127.0.0.1',p),H(p)) for p in (8098,8099)]
for s in S: threading.Thread(target=s.serve_forever,daemon=True).start()
from tau2.utils.llm_utils import generate
from tau2.data_model.message import UserMessage
for m,b in (('openai/qwen2.5-7b-instruct','http://127.0.0.1:8098/v1'),('openai/qwen2.5-3b-instruct','http://127.0.0.1:8099/v1')):
    print(m, b, '->', generate(model=m, messages=[UserMessage(role='user',content='pong')], temperature=0.0, api_base=b, num_retries=0).raw_data['model'])
for s in S: s.shutdown()
EOF
```

Expected: `stub-8098` then `stub-8099`.

## 3. Parser correctness on the smoke JSONs - PASS

Independent hand count over `messages[]` (assistant messages only, `usage` present):

| file | completion | prompt | agent calls | tool calls | user msgs with usage (excluded) | duration | termination | reward |
|---|---|---|---|---|---|---|---|---|
| `llama_smoke` | 397 | 31,842 | 6 (7 assistant msgs; turn-0 greeting has no usage) | 1 | 6 | 60.255 s | user_stop | 1.0 |
| `local_smoke` | 716 | 111,850 | 20 (21 assistant msgs) | 0 | 20 | 57.256 s | max_steps | 0.0 |

`build_episodes.parse_results_file` returns exactly these values (`success` True/False,
`tokens_source = usage`, `tokens_estimated_calls = 0`, `served_models` `qwen2.5-7b-instruct` /
`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, `n_messages` 14 / 41,
`agent_generation_seconds` 42.84 / 38.00, `error = None` for `max_steps`). Tool messages carry
no usage; user-simulator usage sits on user messages and is not counted. The missing-usage path
estimates from content plus tool-call arguments (characters/4 or `/tokenize`), flags the
episode and counts the calls (unit test). `success` requires `reward == 1` (missing reward =
failure). `agent_usage` is `null` in tau2's JSON for these models, so per-message usage is the
right source. Note: `local_smoke` was produced with the mlx agent, not a design model; it is a
parser fixture only.

Reproducer: `$PY -m unittest experiments.tau2_open.tests_tau2_open.ParserTests -v`, or the
hand count:

```bash
$PY - <<'EOF'
import json; d=json.load(open('<TMP>/tau2-bench/data/simulations/llama_smoke/results.json'))
a=[m for m in d['simulations'][0]['messages'] if m['role']=='assistant']
print(sum((m.get('usage') or {}).get('completion_tokens',0) for m in a), sum((m.get('usage') or {}).get('prompt_tokens',0) for m in a), sum(len(m.get('tool_calls') or []) for m in a))
EOF
```

## 4. Metric definitions - PASS (one wording fix)

- Tokens: sum of `usage.completion_tokens` / `prompt_tokens` over assistant messages with usage =
  the agent's LLM calls; litellm cost is 0 for these unmapped names (confirmed:
  `agent_cost = 0.0` in both smoke JSONs), so tokens are the cost proxy. Documented.
- Duration: tau2 `duration` (whole simulation, includes user simulator and tools); therefore a
  sensitivity tier only, matching `experiments/protocol.md`. `agent_generation_seconds` is
  recorded separately. `--max-concurrency 1` and one slot per server make it a single stream.
- Tool calls: `sum(len(tool_calls))` over assistant messages only.
- Wording fix (should-fix 3): protocol section 6 says the reward is "the product of its DB,
  action, NL and communicate checks". NL assertions are not evaluated under tau2's default
  `EvaluationType.ALL`, and all 50 airline tasks have `reward_basis = [DB, COMMUNICATE]`; state
  that, and that no LLM judge enters the reward.

## 5. Hierarchy and tolerance semantics - PASS

`analysis.pair_scores` and `shadow_analysis` call `winstats.compare(XB, XA, tiers, eligible)`
with tiers from `config.json`: success (higher, tol 0) > `agent_tokens_completion` (lower, rel
tol 0.05) > `n_assistant_tool_calls` (lower, tol 0). `compare` uses
`tol = rel * max(|a|, |b|)` and decides only when `|delta| > tol`, so exact threshold equality
is a tie and tool calls decide on any strict difference: identical to
`experiments/protocol.md` ("abs(cost_A-cost_B) > 0.05*max(cost_A,cost_B)"; zero-call absolute
tolerance) and to `experiments/local_stream/`. Absorbing rule = eligibility mask (tiers 2-3
only when both succeeded), two failures tie; lexicographic non-absorbing and token-first rows
use no mask. Unit test `test_pair_scores_rules` checks a 4 % token gap (tie at 5 %, decided by
calls), both-failed tie, 10 % gap decided by tokens, tolerance 0, lexicographic and token-first
behaviour; `test_monitor_matches_direct_recomputation_on_mock` recomputes all 50 e-values with
`betting_log_e_ternary` directly (win H0 E[Z] <= 0; harm = swapped counts; gate on D = success_B -
success_A with threshold -0.03; alpha 0.05; `min_n` 20) and matches to 1e-9. Orientation is
B vs A everywhere I checked: online `compare(XB, XA)`, shadow `task_level_scores(RB, RA)`,
components `welch_ci(x=A, y=B)` (diff = B - A) and paired diffs `tb - ta`.

## 6. Estimands - PASS with remarks

- E1 (cross-arrival, single exposure): the 50 prespecified pass-1 pairs; `completed_pairs`
  joins by `(pass1_arm, task_id, trial)` from `design.json`; `pass` is assigned by
  `attach_design` (1 if the episode's arm is the unit's `pass1_arm`). Monitoring is computed post
  hoc over the prespecified sequence; nothing in it depends on execution order or on observed
  outcomes, and there is no adaptivity, so the e-processes are the log an online evaluator would
  have produced. Block 2 reuses the 50 tasks with fresh randomization (new permutation, new
  orientations); conditional on block 1 the expected block-2 pair score is still the
  finite-population net benefit, so the conjunction test remains valid for the null on the
  100-unit population. What block 2 cannot do is add evidence about *new tasks*; the paper
  must phrase the E1 target as this 50-task population (the protocol already says so and
  reports the block-1 subset). Remark only.
- E2 (same-task shadow): `task_level_scores` with pairing `all` (2 x 2 comparisons per task),
  `offdiagonal` / `diagonal` as sensitivity, `clustered_summary` with T - 1 = 49 df; valid
  whether or not the two temperature-0 trials are identical; `replicate_identical_fraction`
  reported per arm. Remark: `diagonal` pairs the i-th A run with the i-th B run, which is "same
  tau2 seed" only because `write_episodes` sorts by (arm, trial, task) and `load_episodes`
  preserves file order; document this (should-fix 5).
- Components, decision-rule table, 20 sensitivity rows (4 tolerances x 5 orders incl. duration
  tier, lexicographic, token-first H4), block-1-only analysis and the H1-H5 mapping are
  present and exercised by the mock dry run (`results/tau2_open/dryrun/report.md` carries the
  MOCK banner; `summary.dry_run = true`).

## 7. Protocol completeness vs issues #1/#2 and deviations log - FAIL (one item)

Every issue-#1 and issue-#2 requirement in the protocol's section 15 table maps to a concrete
section or artifact and I found each of them implemented (frozen design before outcomes,
independent seeds, retained failures, E1 vs E2, exact versions and hashes, append-only
manifest, unit/seed accounting, cluster-correct uncertainty, monitoring log, license and
tool-use verification, cache/runtime estimates, weights outside the repo, runnable README,
latency scope, resource use, task-level scores, limits). The deviations log records the
stratified permutation, the 3B license and the server settings.

The failing item: the coordinator's `llama_smoke` run is an episode of design unit (task `0`,
trial 0, tau2 seed 626729) on the *same stack as arm A* (same 7B GGUF as agent and user, same
llama.cpp commit, same tau2 commit, temperature 0, `--jinja`), differing only in `max-steps` 60
(irrelevant: it stopped by `user_stop` after 13 messages), `-c 16384` and 4 slots. Its
outcome (success, 397 completion tokens, 1 tool call, 60 s) was therefore known before
`protocol.md` and `config.json` were written (smoke 12:05, protocol 12:24). The status paragraph
discloses that task `0` was kept, but (a) the deviations table (section 13) has no row for it,
(b) the known outcome is not stated, and (c) the brief to this audit says a smoke task is
excluded from the design. The influence on any pre-specified choice is implausible (the
hierarchy, margin and tolerance mirror `experiments/protocol.md`, fixed long before), but
pre-registration hygiene is binary. See must-fix 1 for the two acceptable resolutions.

## 8. Reproducibility - PASS (freeze commit pending)

- GGUF: sizes and sha256 of the three files re-hashed by me with `common.gguf_record` match
  `config.json` (7B parts 3,993,201,344 and 689,872,288 bytes; 3B 2,104,932,768 bytes); HF
  `refs/main` = the pinned revisions. Airline `tasks.json`, `policy.md`, `db.json` sha256 match.
  tau2 checkout HEAD = `b7ea907...`; llama.cpp HEAD = `4fea119...`; running 8081 server reports
  `build_info b1-4fea119`.
- Manifest: append-only (second dry run appends a record, first record byte-identical;
  `complete_invocation` refuses to overwrite a filled field); records config, preflight hashes,
  tau2 and server commands, harness file hashes, hardware, packages. Lock: a live-pid lock
  refuses a concurrent run (tested); a dead-pid lock is removed.
- Refusal paths exercised: config drift (`max_steps` 50 -> "config hash ... differs"), dry run
  into the primary results dir, lock, design hash mismatch, force-regeneration after outcomes.
  Live reproducer against the coordinator's 8081 server (GET only):
  `Servers(cfg, tmp).ensure('qwen2.5-7b-instruct', 8081)` -> `SystemExit: ... does not match the
  config (n_ctx 16384 != 32768; slots 4 != 1); stop it or pass --accept-running-server`; with
  `accept_running=True` the mismatch is recorded. Port 8082: nothing listening.
- Resume: tau2 `--auto-resume` keys done units by `(trial, task_id, seed)`; trial seeds from
  `random.seed(300)` are `[626729, 373753]` (recomputed), identical for both arms and checked by
  `check_results_info`. An arm whose raw copy holds all 100 units is skipped. Caveat (should-fix
  4): on resume tau2 drops `INFRASTRUCTURE_ERROR` simulations from `done_runs` and re-runs them,
  and `run_arm` overwrites `raw/tau2_open_arm*.json` with `copy2`, so an infrastructure-failure
  record of an interrupted invocation is not retained in `raw/` after a resume; protocol section
  7 currently says such records are kept.
- Harness hashes: all current files match the dry-run manifest except `tests_tau2_open.py`
  (edited after the dry run; irrelevant to outcomes). `design.json.harness_git_hash`
  (`526dff7b...`) is the current branch HEAD, not a freeze commit; `<FREEZE_COMMIT_ID>` in
  protocol section 16 must be filled after committing (must-fix 2; same coordinator step as in
  `reviews/local_stream_preregistration_audit_round2.md`).

## 9. Licenses - PASS

`tau2-bench/LICENSE`: MIT, Copyright (c) 2025 Sierra Research. `llama.cpp/LICENSE`: MIT,
Copyright (c) 2023-2026 The ggml authors. Qwen2.5-7B-Instruct-GGUF: Apache-2.0;
Qwen2.5-3B-Instruct-GGUF: Qwen Research License (non-commercial research/evaluation only), as
recorded in `config.json` and protocol sections 13-14 with the required notice text. This is a
documented deviation from the brief's Apache-2.0 assumption; research evaluation is within the
license, weights are not redistributed, and reproducers must accept it. The paper must say so.

## 10. No design episode executed - PASS

`tau2-bench/data/simulations/` holds only `llama_smoke/` (task `0`, 1 trial, max-steps 60, 7B
agent and user) and `local_smoke/` (task `0`, 1 trial, max-steps 40, mlx agent); no
`tau2_open_arm*` directory exists. `results/tau2_open/` holds `design.json`, `design.sha256` and
`dryrun/` only (no `raw/`, `episodes.csv`, `logs/`, `run_manifest.json`, `run.lock`). No
llama-server on 8082; the only llama-server is the coordinator's 8081 smoke server (pid 68461);
`mlx_lm.server` on 8080 belongs to the other experiment and was not touched. This audit made no
completion request to any model server.

## 11. Unit tests - PASS

`$PY -m unittest experiments/tau2_open/tests_tau2_open.py -v`: 15 tests, OK, 1.49 s (design
determinism across two `PYTHONHASHSEED` values in subprocesses, pairing invariants,
overwrite/hash refusals, parser on both smoke JSONs, missing-usage flagging, design join,
dry run + append-only manifest, per-role routing in the tau2 command, config-drift refusal,
primary-dir and lock refusals, `check_results_info`, pair-score rules, monitor recomputation
against `winstats`, partial-episode analysis). None contacts a server.

---

## Must fix (before the first design episode)

1. **Task `0` smoke disclosure / exclusion.** Either (recommended) exclude task `0`: set
   `task_ids` to `"1".."49"`, regenerate the design with `design.py --force` (allowed: no
   `episodes.csv` or `raw/` exists), and update the counts in `protocol.md`, `README.md` and the
   tests (98 units, 49 pairs, 49 df; with an odd block size pair 25 straddles the two blocks, so
   define the block-1 subset as "pairs whose two arrivals are both in block 1" = pairs 1-24, which
   still covers `min_n = 20`; `check_pairing_invariants` and `analysis.online_analysis(blocks_keep={1})`
   already behave this way, `test_pairing_invariants`, `test_deterministic_...` and
   `test_monitor_matches_...` hard-code 100/50/25 and must be updated), then re-freeze the four
   hashes. In-memory check of this variant: 98 units, 49 pairs, straddling pair = 25 only, 24
   pairs fully in block 1. Or (acceptable) retain task `0` and add a row to the deviations log
   (section 13) stating that `llama_smoke` is a same-stack arm-A episode of unit (0, trial 0)
   whose outcome (success, 397 completion tokens, 1 tool call, 13 messages, 60 s) was known
   before the protocol was written, with the server-setting differences. The coordinator must
   record which option was taken.
2. **Freeze commit.** Commit `experiments/tau2_open/` and `results/tau2_open/design.*` and fill
   `<FREEZE_COMMIT_ID>` in protocol section 16 (this sandbox runs no git command).
3. **Stop the coordinator's 8081 server** (`-c 16384`, 4 slots) before `run_tau2_open.py`; do not
   use `--accept-running-server`, which would run the whole stream under settings other than the
   frozen ones and would have to be logged as a deviation. Start after the mlx_lm experiment
   releases the GPU (about 18:30 UTC).

## Should fix (small; apply now or decline explicitly, since later changes are deviations)

1. Extend `check_results_info` to user messages: `raw_data.model` of every user message must
   equal `cfg['user_alias']` (the field is present: all 6 user messages in `llama_smoke` carry
   `model = qwen2.5-7b-instruct`). Today only the agent side is checked post hoc.
2. Add `--hallucination-retries 0` to `tau2_command` so text-run behaviour does not rely on
   tau2's full-duplex guard; update `test_tau2_command_routes_roles_to_their_servers`.
3. Protocol section 6 wording: the reward uses the task's `reward_basis` (`[DB, COMMUNICATE]`
   for all 50 airline tasks); NL assertions are not evaluated (tau2 WIP, would call gpt-4.1);
   no LLM judge and no commercial model enter agent, user, environment or reward.
4. Keep a per-invocation raw copy (e.g. `raw/tau2_open_arm<A>.<invocation_id>.json`) in addition
   to the overwritten canonical copy, and state in section 7 that tau2 re-runs
   `INFRASTRUCTURE_ERROR` units on resume (their number can then be reported).
5. Document in section 11(b) that the `diagonal` pairing means same tau2 trial because
   `episodes.csv` is written trial-major per arm.

## Not defects (for the record)

- Runtime is a planning estimate; the manifest records measured values.
- At temperature 0 the two trials may be near-identical; disclosed, E2 inference is
  cluster-robust, `replicate_identical_fraction` is reported.
- 50 online pairs give limited power; the protocol commits to reporting "too short" rather
  than a weakened claim.
- The user-simulator prompt, tools, reward and data are tau2's own at the pinned commit; the
  harness hashes them and refuses drift.


---

# Round 2: re-audit of pre-freeze revision 2 (2026-09-18, 13:00 local)

Same auditor role and constraints as round 1: no git command, no paid API, no tau2 episode, no
model completion, no GPU work; GET `/props` and `/v1/models` on the coordinator's two running
servers were the only requests to a model server. Nothing under `results/tau2_open/` was
modified; my scratch dry run lives in the session scratchpad (`audit_r2/dry`). Files audited:
`experiments/tau2_open/` (9 files, hashes below), `results/tau2_open/design.{json,sha256}`,
`results/tau2_open/dryrun/`, the tau2-bench checkout `b7ea907`, the llama.cpp checkout
`4fea119`, the three smoke JSONs, the Hugging Face API for the arm-B repositories.

**Verdict: NOT YET READY TO FREEZE, for one factual correction to the pre-registration text
plus the two coordinator steps carried over from round 1.** Every coordinator decision and
every round-1 must-fix/should-fix item is implemented exactly as stated in the fixer summary
and re-verified below (items R2.1-R2.12). The new item (R2.13, must-fix 1) is not a harness
defect and does not touch the design, the estimands or the analysis: tau2 forwards its
per-trial seed as a per-request `seed` to BOTH the agent and the user-simulator server, and
llama-server honours it, whereas protocol sections 4, 5, 12 and 13, `config.json`
`sampling_note`, `README.md` and the `run_tau2_open.py` docstring state that no per-request
seed is sent. A pre-registration must describe the sampling mechanism correctly; the fix is a
wording change that must be made before the first episode (after it, it is a deviation).

| # | Item | Verdict |
|---|---|---|
| R2.1 | Task 0 excluded; design regenerated: 98 units, 49 pairs, 0 unpaired, block-1 subset = pairs 1-24 | **PASS** |
| R2.2 | Determinism across `PYTHONHASHSEED`; four hashes consistent between config.json, design.json, design.sha256, protocol.md | **PASS** |
| R2.3 | Arm B model, GGUF, size, sha256, revision, alias, port, license | **PASS** (independently confirmed against the HF API) |
| R2.4 | Pre-flight GGUF hash check uses the new file (all three files re-hashed) | **PASS** |
| R2.5 | Temperatures 0.3 (agent, both arms) / 0.0 (user) sent per request; `--temp 0` dropped from the server flags | **PASS** |
| R2.6 | Hypotheses H1-H5 reworded; H3 flag implemented and consistent with the protocol wording | **PASS** |
| R2.7 | Hardening (i): user-message served-model and llm_args temperature checks | **PASS** |
| R2.8 | Hardening (ii): `--hallucination-retries 0` (flag exists, `type=int`) | **PASS** |
| R2.9 | Hardening (iii): section 6 reward wording | **PASS** |
| R2.10 | Hardening (iv): per-invocation raw copies, infra-error counting, section 7 wording | **PASS** |
| R2.11 | Hardening (v): diagonal pairing = same tau2 trial regardless of file order | **PASS** |
| R2.12 | Tests (16/16), mock dry run, no design episode, running servers refused | **PASS** |
| R2.13 | Sampling statement "no per-request seed is sent" | **FAIL** (must-fix 1) |

Current harness file sha256 (all nine equal the hashes recorded in
`results/tau2_open/dryrun/run_manifest.json`, so the dry run was made with exactly these files):
`analysis.py 36dd49e1...ec36c5`, `build_episodes.py 85d95b72...a73a8`, `common.py 14f1a15c...bc0997`,
`design.py 2d7ef2c6...6d6038`, `run_tau2_open.py f71edff0...d4932`, `tests_tau2_open.py d74ad11c...658ff`,
`config.json (whole file) 12e6c6ea...2b00dd`, `protocol.md eb8979d8...540b6`, `README.md 1ecd0c6c...54da1`.

## R2.1 Design: task 0 excluded, 98/49/24 - PASS

Independently recomputed from `results/tau2_open/design.json` (not via the tests): 98 arrivals,
49 pairs, 0 unpaired; task `0` absent; arrivals 1-49 all trial 0, 50-98 all trial 1; each block
visits each of the 49 tasks once; no pair contains the same task twice (0/49); `{pass1_arm}` of
every pair is `{A, B}` with `pass1_arm == A` iff `orientation == 1` for the first arrival; 22
pairs have R = 1 and 26 tasks have the same pass-1 arm in both trials (protocol section 4 says 22
and 26: correct). Pair 25 = arrivals 49 (block 1, task 14) and 50 (block 2, task 40) is the only
straddling pair; the pairs whose two arrivals are both in block 1 are exactly 1-24, covering 48
distinct tasks and `min_n = 20`. `analysis.pair_blocks` / `completed_pairs` assign a pair the
larger block of its arrivals, so `online_analysis(blocks_keep={1})` gives 24 pairs and
`n_pairs_straddling_blocks` is 1 for all-49 and 0 for block 1 (seen in both dry-run summaries).
`check_pairing_invariants` passes on the frozen file; `config.json` `task_ids` = "1".."49" with the
`excluded_task_ids` note; section 3 of the protocol discloses the `llama_smoke` outcome (success,
397 completion tokens, 1 tool call, 13 messages, 60 s) as required by round-1 must-fix 1.

## R2.2 Determinism and hash consistency - PASS

`design.py --print-sha-only` under `PYTHONHASHSEED` 0, 7 and 99999 (three processes) prints
`8b515c3b1590178144b28475240dd574a65dd3fa426ee6951ca41b0c6144ea9d`, equal to the content sha256 of
the frozen file and to an in-process `generate(cfg, 20260918)` (arrivals identical). Whole-file
sha256 of `design.json` = `c8fa5728...86597` = `design.sha256`. `design.config_hash` =
`347b7bbd...122c58` = sha256 of canonical `config.json` (`load_config`). `task_list_sha256`
`ce69ae4b...d310` recomputed from config. `generator_sha256` in the design equals the current
sha256 of `design.py`, so the generator was not edited after generation. The status paragraph and
section 16 of `protocol.md` and `README.md` carry the same four values. The dry-run design
(`results/tau2_open/dryrun/design.json`) and my scratch dry-run design have the same content
sha256 as the frozen primary design (they differ only in the timestamp).

```bash
for s in 0 7 99999; do PYTHONHASHSEED=$s $PY experiments/tau2_open/design.py --print-sha-only; done
shasum -a 256 results/tau2_open/design.json; cat results/tau2_open/design.sha256
```

## R2.3 / R2.4 Arm B model and GGUF check - PASS

`config.json`: `unsloth/Qwen3-4B-Instruct-2507-GGUF`, revision `a06e946bb6b655725eafa393f4a9745d460374c9`,
file `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, 2,497,281,120 bytes, sha256 `3605803b...67e597`, alias
`qwen3-4b-instruct-2507`, port 8082, base `Qwen/Qwen3-4B-Instruct-2507`, license apache-2.0.
Verified: (a) local file re-hashed by me = `3605803b...67e597`, 2,497,281,120 bytes; the HF cache
`refs/main` = `a06e946b...`; (b) `common.gguf_record(verify_hash=True)` returns `ok = True` for
both models (7B parts 3,993,201,344 and 689,872,288 bytes unchanged), so the pre-flight of
`run_tau2_open.py` hashes the new file; (c) Hugging Face API (no token): repo sha `a06e946b...`,
`cardData.license = apache-2.0`, tag `license:apache-2.0`, `base_model = Qwen/Qwen3-4B-Instruct-2507`;
the tree listing gives the Q4_K_M file 2,497,281,120 bytes with LFS oid `3605803b...67e597`,
identical to the local hash; base repo `Qwen/Qwen3-4B-Instruct-2507` sha `cdbee75f...`, license
apache-2.0, and the local base snapshot carries an Apache License 2.0 file and
`license: apache-2.0` in its README front matter. `server_command` for 8082 uses `--jinja`,
`-c 32768 -np 1`, the Q4_K_M path, no `--temp`. The running 8082 smoke server reports
`chat_template_caps.supports_tool_calls = true`. The `smoke_retail_4b` JSON (retail task 0, not a
design unit) parses to served models assistant `qwen3-4b-instruct-2507`, user
`qwen2.5-7b-instruct`, 5 tool calls, reward 1.0, 1283 completion tokens, 17 agent calls. The
Qwen Research License now appears only in the revision history (section 17), as intended.

## R2.5 Temperatures - PASS

`tau2_command` puts `{"temperature": 0.3, "api_base": ...}` in `--agent-llm-args` for both arms and
`{"temperature": 0.0, "api_base": http://127.0.0.1:8081/v1}` in `--user-llm-args`;
`llama_extra_args` has no `--temp`. Stub test through tau2's own `generate()` (two HTTP stubs on
8098/8099, `OPENAI_API_BASE` pointing at a closed port): the agent call reached 8099 with body
`model = qwen3-4b-instruct-2507, temperature = 0.3`, the user call reached 8098 with
`model = qwen2.5-7b-instruct, temperature = 0.0`; no `max_tokens`, `top_p` in the body.
`check_results_info` on the real `llama_smoke` JSON (arm A stack at temperature 0) reports
`agent temperature 0.0 != 0.3`, `max_steps 60 != 100`, `num_trials 1 != 2`, i.e. the temperature
check works on real tau2 output (tau2 records `llm_args` in `info`). The deviation from the
released runs' temperature 0 is logged in section 13.

## R2.6 Hypotheses and the H3 flag - PASS

Section 1 states H1 (direction-uncertain success difference, deployment question), H2 (fewer
completion tokens), H3 (success tier determines the sign: same sign as NB and magnitude at least
the combined magnitude of lower tiers), H4 (token-first prefers B if H2 holds), H5 (absolute
levels not comparable). `analysis.success_determines_sign` implements exactly the H3 wording
(returns None when NB = 0) and is reported as `success_tier_determines_sign` for E1 (from the
tier decomposition, whose contributions sum to NB: checked 0.0816 = 0.0612 + 0 + 0.0204 on the
mock) and E2 (from `tier_contribution_mean`, which sums to the clustered NB: checked). The
report's hypothesis table maps H1-H5 to these outputs; H4 is the sensitivity row
`agent_tokens_completion>success>n_assistant_tool_calls` with eligibility `none`. The H3
operationalisation is the fixer's reading of the coordinator's wording; it is now written in
the protocol, so it is pre-registered either way.

## R2.7-R2.11 The five hardenings - PASS

- (i) `check_results_info` collects `raw_data.model` per role and requires the assistant set to
  equal the arm alias and the user set to equal `user_alias`; it also checks agent/user llm_args
  temperatures. Unit test covers a misrouted user message and a wrong temperature; mock runs
  give `info_mismatches = []` for both arms.
- (ii) `--hallucination-retries 0` in `tau2_command`; `cli.py` line 455 defines the flag
  (`type=int`, default 3), `runner/batch.py` uses it only when `is_full_duplex`; `--auto-review`
  stays default False.
- (iii) Section 6: `reward_basis = [DB, COMMUNICATE]`, NL assertions not evaluated, no LLM judge.
- (iv) `store_raw` writes `raw/tau2_open_arm<X>.<invocation_id>.json` and refuses to overwrite it
  (tested); `run_arm` records `n_infrastructure_error_rerun_on_resume` (count before the
  invocation) and `n_infrastructure_error_now`; section 7 documents tau2's resume behaviour
  (`checkpoint.py` drops `infrastructure_error` records).
- (v) `runs_by_task` sorts episodes by trial before stacking; test compares normal and reversed
  file order; section 11(b) documents diagonal = same tau2 trial.

## R2.12 Tests, dry run, no design episode, servers - PASS

- `$PY -m unittest experiments/tau2_open/tests_tau2_open.py -v`: 16 tests, OK, 1.6 s (three
  parser tests run against the present smoke JSONs; none contacts a server).
- Fresh dry run in the scratchpad (`run_tau2_open.py --dry-run --results-dir .../audit_r2/dry`,
  then `analysis.py`): 196 episodes, 49 online pairs, 24 block-1 pairs, 49 shadow tasks,
  `info_mismatches [] []`, per-invocation copies present; `online`, `online_block1`, `shadow`,
  `sensitivity` (20 rows) and `decision_rules` are identical to `results/tau2_open/dryrun/summary.json`
  (deterministic mock); `report.md` carries the MOCK banner. The committed dry-run manifest
  records `config_hash 347b7bbd...` and the current harness hashes.
- No design episode: `tau2-bench/data/simulations/` holds only `llama_smoke`, `local_smoke`,
  `smoke_retail_4b` (retail domain); `results/tau2_open/` holds `design.json`, `design.sha256`,
  `dryrun/` only (no `raw/`, `episodes.csv`, `run_manifest.json`, `run.lock`).
- Running servers: pid 68461 on 8081 (7B, `-c 16384`, 4 slots, `--temp 0`) and pid 73741 on 8082
  (Qwen3-4B, `-c 16384`, 4 slots) are still up. `Servers(cfg, tmp).ensure(alias, port)` refuses
  both with `n_ctx 16384 != 32768; slots 4 != 1` (GET only); with `accept_running=True` the
  mismatch is recorded. The coordinator must still stop them (must-fix 2).
- tau2 checkout HEAD `b7ea9074...`, llama.cpp HEAD `4fea119d...` (read from `.git` files);
  `design.harness_git_hash` `526dff7b...` = current `refs/heads/session60/local-stream`, not a
  freeze commit (must-fix 3).

## R2.13 Per-request seed: the pre-registration text is wrong - FAIL

Claim in `protocol.md` (sections 4, 5, 12, 13), `config.json` `sampling_note`, `README.md` and the
`run_tau2_open.py` docstring: "no per-request seed is sent", "tau2 does not forward its trial
seed to the model server", "llama-server draws its own sampler seed per request", therefore
"agent sampling is NOT bit-reproducible".

What tau2 `b7ea907` actually does (source): `runner/batch.py` lines 742-743 derive
`seeds = [626729, 373753]` from `random.seed(300)` and pass `seeds[trial]` to the orchestrator
(line 832 -> `run_task(..., seed=seed)`); `orchestrator/orchestrator.py` lines 526-528:
`if self.seed is not None: self.agent.set_seed(self.seed); self.user.set_seed(self.seed)`;
`LLMAgent` and `UserSimulator` both inherit `set_seed` from `agent/base/llm_config.py::LLMConfigMixin`
(MRO checked in-process), which executes `self.llm_args["seed"] = seed`. Those `llm_args` are the
kwargs of every `generate()` call, and litellm puts `seed` in the OpenAI request body.
Empirical confirmation (stub on 8098, no model): `LLMAgent(llm='openai/qwen3-4b-instruct-2507',
llm_args={'temperature': 0.3, 'api_base': ...})`, then `set_seed(626729)`, then `generate(**llm_args)`
-> request body keys `['messages', 'model', 'seed', 'temperature']` with `seed = 626729`,
`temperature = 0.3`. llama-server (commit `4fea119`) reads the request `seed` into
`params.sampling.seed` (`tools/server/server-schema.cpp` line 176) and seeds the sampler chain
with it (only `LLAMA_DEFAULT_SEED` triggers a random seed).

Consequences (all wording; no code, design or analysis change is needed):

- Every agent AND user-simulator request of trial t carries `seed = seeds[t]` (626729 for trial
  0, 373753 for trial 1), the same value in both arms. The two trials therefore differ by seed
  (they remain distinct sampling replicates, so the section-13 rationale for temperature 0.3
  still holds), and within a trial every request uses one fixed seed.
- The reproducibility statement must be inverted: a re-run sends the same seeds, so agent
  sampling is reproducible up to the serving stack's own nondeterminism (Metal kernels, batch
  composition); "not bit-reproducible" is at most a hardware caveat, not a consequence of a
  missing seed.
- `info.agent_info.llm_args` in `results.json` does NOT show the seed (the mixin deep-copies
  `llm_args` before mutating it; both smoke JSONs confirm), so `check_results_info` cannot and
  need not check it; the per-episode `seed` field already records the trial seed.
- The E2 `diagonal` pairing is now literally "same sampler seed for A and B".
- `replicate_identical_fraction` keeps its meaning (agreement between two differently seeded
  trials).

Reproducer (inside the tau2-bench checkout, no model server):

```bash
OPENAI_API_KEY=sk-x uv run python - <<'PYEOF'
import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
bodies=[]
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n=int(self.headers.get('Content-Length',0)); bodies.append(json.loads(self.rfile.read(n)))
        b=json.dumps(dict(id='x',object='chat.completion',created=0,model='stub',choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='pong'))],usage=dict(prompt_tokens=3,completion_tokens=1,total_tokens=4))).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
S=HTTPServer(('127.0.0.1',8098),H); threading.Thread(target=S.serve_forever,daemon=True).start()
from tau2.agent.llm_agent import LLMAgent
from tau2.utils.llm_utils import generate
from tau2.data_model.message import UserMessage
a=LLMAgent(tools=[], domain_policy='p', llm='openai/qwen3-4b-instruct-2507', llm_args=dict(temperature=0.3, api_base='http://127.0.0.1:8098/v1'))
a.set_seed(626729); generate(model=a.llm, messages=[UserMessage(role='user',content='pong')], num_retries=0, **a.llm_args)
print(sorted(bodies[-1]), bodies[-1]['seed']); S.shutdown()
PYEOF
```

Expected: `['messages', 'model', 'seed', 'temperature'] 626729`.

## Round-2 must fix (before the first design episode)

1. **Correct the per-request-seed statements.** Replace "no per-request seed is sent / tau2
   does not forward its trial seed / llama-server draws its own sampler seed" in `protocol.md`
   sections 4, 5, 12 and 13 (deviations row 2), `README.md` (Routing paragraph and "Sampling"
   sentence), the `run_tau2_open.py` docstring and `config.json` `sampling_note` with: tau2
   forwards the per-trial seed (626729 / 373753) as `seed` in every agent and user-simulator
   request (`orchestrator.set_seed` -> `LLMConfigMixin.set_seed`), llama-server seeds its
   sampler with it, both arms receive the same seeds, the two trials differ by seed, and a re-run
   reproduces the agent's sampling up to the serving stack's nondeterminism. Add the change as
   revision-2 item 7 (or revision 3) in section 17. Two acceptable ways to handle `config.json`:
   (a) leave `config.json` untouched (hashes unchanged) and state in section 17 that its
   `sampling_note` text is superseded by section 5; or (b) fix the note in `config.json` and
   regenerate the design with `design.py --force` (allowed: no `raw/` or `episodes.csv`), then
   re-freeze the four hashes; I verified that changing only this free-text field leaves every
   arrival, pair and orientation identical and changes only `config_hash` (the dry run would have
   to be regenerated again under option (b)). The coordinator records which option was taken.
2. **Stop the coordinator's two smoke servers** (pid 68461 on 8081, pid 73741 on 8082; `-c 16384`,
   4 slots) before `run_tau2_open.py`; do not use `--accept-running-server` for the design run.
   Unchanged from round 1; the harness refuses both as verified today.
3. **Freeze commit.** Commit `experiments/tau2_open/` and `results/tau2_open/design.*` after item 1
   and fill `<FREEZE_COMMIT_ID>` in protocol section 16. Unchanged from round 1.

## Round-2 should fix (optional; declining is acceptable if recorded)

1. After item 1 above, `protocol.md` section 4 could additionally state that `check_results_info`
   cannot observe the request seed (the info block carries the pre-`set_seed` llm_args) and that
   the per-episode `seed` field is the record of it.

## Not defects (round 2)

- The `smoke_retail_4b` verification ran on the 8082 server with `-c 16384` and 4 slots, not the
  frozen settings; it is a retail-domain tool-call check, not a design unit, and is disclosed.
- The primary results directory still contains no manifest; the first real invocation creates it.
- `Servers.ensure` accepts a freshly started server as soon as its alias answers; since the harness
  starts it with the frozen flags this is fine, and the recorded `/props` probe documents `n_ctx`
  and slots for the manifest.
