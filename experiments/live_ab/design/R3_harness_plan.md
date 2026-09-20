# R3. Harness reuse and engineering plan for the live single-exposure A/B trial

Reader R3, 2026-09-19. Read-only inspection of the repository at branch `session60/local-stream` (HEAD `ce8b506`);
no git state change, no model server, no LLM call, no download. CPU-only checks were run with
`<REPO>/.venv/bin/python`. Everything written by this reader is in
`<scratchpad>/live_ab_design/`:

| file | what it is |
|---|---|
| `R3_harness_plan.md` | this plan |
| `eventlog_proto.py` | 150-line stdlib prototype of the hash-chained log, the write-ahead OS coin and the resume rule; its self-test passes (chain verify, torn-tail recovery without truncation, tamper / deletion / wrong-genesis detection; 4.0 ms per durable append with `F_FULLFSYNC`) |
| `_llama_server_help.txt` | captured output of `llama-server --help` (721 lines; the only way the binary was run) |

Paths below are relative to `<REPO>/` unless absolute. `LS` =
`experiments/local_stream`, `T2` = `experiments/tau2_open`, `LCPP` =
`<scratchpad>/llama.cpp/tools/server` (checkout `4fea119de30f6a923992780f6fd5ccb0bee5d47d`, the commit frozen in
`T2/config.json:27`), `MLX` = `.venv/lib/python3.12/site-packages/mlx_lm` (mlx_lm 0.31.3, mlx 0.32.2).

## 0. Findings that change the plan (read these first)

1. **`mlx_lm.server` serializes every request that carries a `seed`.** `MLX/server.py:685-686`:
   `_is_batchable = model_provider.is_batchable and args.seed is None`; a seeded request goes to `_serve_single`
   (`:813-815`, `:922-958`, which calls `mx.random.seed(args.seed)` on the process-global RNG) and, if a batch is
   running, the batch is drained first (`:831-836`). The existing client always sends a seed (`LS/agent.py:124-125`,
   seeds set unconditionally at `:209-214`). With the delivered harness, two workers against `mlx_lm.server` would just
   queue. Without a seed it does continuous batching (`BatchGenerator`, `:821-827`; `--decode-concurrency` 32,
   `--prompt-concurrency` 8, `:1854-1864`), but then sampling uses one shared global RNG and nothing can be receipted.
2. **`mlx_lm.server` cannot give a sampler receipt.** The response carries `usage` (+ `cached_tokens`)
   (`MLX/server.py:1339-1347`), a version `system_fingerprint` (`:49-51`) and `model` = **the request's own `model`
   string echoed back** (`:1163`, `:1307`); no temperature/top_p/seed echo, no timings. Consequence for the delivered
   pilot: the "served model id" check in `LS/run_stream.py:161-183, 320-323` was vacuous under mlx_lm (it compares the
   request with its echo). llama-server fills `model` from the loaded model's alias server-side
   (`LCPP/server-context.cpp:1374-1380, 4329`), so there the check is real.
3. **llama-server can return the receipt per request.** A request body field `"verbose": true`
   (`LCPP/server-schema.cpp:17-18`; default off unless server verbosity > 9, `:537`; extra body fields are passed through
   by the chat endpoint, `LCPP/server-common.cpp:1414-1420`) adds `__verbose` to the `/v1/chat/completions` response
   (`LCPP/server-task.cpp:451-454`) = the native result (`:340-361`): `generation_settings` (seed, temperature, top_k,
   top_p, min_p, typical_p, penalties, mirostat, samplers order, n_predict/max_tokens, chat_format; `:96-142`), `id_slot`,
   `tokens_predicted`, `tokens_evaluated`, `tokens_cached`, `truncated`, `stop_type`, the rendered `prompt`. `usage`
   (`:365-372`) and `timings` (`cache_n, prompt_n, prompt_ms, predicted_n, predicted_ms, *_per_second`;
   `LCPP/server-common.cpp:86-96`) are always present in the non-streamed chat response (`:455-457`).
4. **The frozen per-call seed formula collides across units.** `LS/agent.py:209` (`trial*1_000_003 + arrival*7 + bit`)
   plus `:214` (`+10*round + 3*tests`) gives 2,960 distinct values for the 4,728 possible (arrival, variant, kind, round)
   calls of the delivered design, maximum multiplicity 2 (computed by this reader). This is the "seeds shared across
   units" criticism in concrete form; the live trial must not reuse the formula.
5. **Feasibility flag for the coordinator (not R3's topic, but it sizes the scheduler).** With the root's accepted
   construction `winstats.normal_mixture_radius(n, alpha=.05, rho=100.)` (`src/winstats.py:51-61`) the radius is
   0.536 / 0.281 / 0.183 / 0.128 / 0.096 at n = 60 / 147 / 295 / 569 / 1,000 units and first reaches 0.10 at n = 922,
   0.05 at n = 3,978 and **0.03 at n = 12,094** units (unsplit alpha = .05; an alpha split across gates only widens
   it; sibling files `R2_margin_feasibility.json` and `power_*.csv` carry the simulation view). A success non-inferiority gate with margin 0.03 and a true
   difference of 0 therefore cannot cross on 591 (or 1,138) single-exposure tasks; a harm crossing at NB near -0.47
   needs about 60-75 units (consistent with the root's pair-60 replay crossing,
   `reviews/round11_coding_target_scope.md:67`). Either the margin, the horizon (task replication in epochs) or the
   claim ("no deploy decision reached within the horizon" is a legitimate prespecified outcome) must be fixed before
   freeze. The scheduler below supports epochs for that reason.
6. **Data**: only the 427 sanitized MBPP + 164 HumanEval tasks are on disk. The full 974-task `mbpp.jsonl` was only ever
   fetched into memory (section D).
7. **GGUF for the coding model**: `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct-GGUF/` appeared
   today (13:37-13:40 local): one 4,683,073,536-byte blob named `509287f7...894d3c` (HF names LFS blobs by sha256),
   `refs/main` present, snapshot dir `13fb94bf...` still empty. Someone else is fetching it; R3 did not touch it. Cached
   and complete already: `Qwen2.5-7B-Instruct` Q4_K_M (2 files), `unsloth/Qwen3-4B-Instruct-2507` Q4_K_M,
   `Qwen2.5-3B-Instruct` Q4_K_M (this one is NOT Apache/MIT: Qwen research licence), MLX `Qwen2.5-Coder-7B-Instruct-4bit`.

---

## A. Module-by-module map

### A.1 Reusable UNCHANGED (import from `experiments/local_stream/`, hash into the freeze bundle)

| module | what is reused | lines | notes for the live trial |
|---|---|---|---|
| `LS/data.py` | `build_tasks`, `mbpp_entry_point`, `load_tasks`, `task_list_sha256` | 35-62, 95-102 | `prepare()` hard-codes 427/164 (`:73-74`) and mutable `master` URLs from config (`:68-69`); fine for the 591-task roster, not for an extended roster (A.2 `lab_data.py`). |
| `LS/agent.py` prompts | `SYSTEM_PROMPT`, `TEST_PROMPT`, `REPAIR_PROMPT`, `signature_line`, `build_user_prompt`, `extract_code` | 35-42, 47-83 | Hidden tests never enter a prompt; audited on all 591 tasks (`reviews/local_stream_preregistration_audit_round2.md:41-60`). |
| `LS/agent.py` episode | `run_episode(task, variant, model, cfg, meta)` | 195-263 | Reusable as is **if the model object is injected** (A.2 `lab_client.py`): it only needs `.chat(messages, ctx)`, `.model`, `.name`. Its own seed (`:209, :214`) is passed in `ctx['seed']` and the new client ignores it. Exceptions in any call become `error` + verification of the last candidate (`:242-249`): a failed repair call still grades the pre-repair code. Latency stops before hidden-test verification (`:247`). Legacy field to ignore: `variant_letter` (`:198`, hard-wired single_shot=A) conflicts with T1 where the incumbent A is self_test_repair; the live harness uses its own `arm` in {incumbent, candidate}. `endpoint` (`:203`) comes from `cfg['base_url']`: pass a per-arm shallow copy of cfg (same `_config_hash`) when T3 uses two servers. |
| `LS/sandbox.py` | `run_program`, `sandbox_info`, Seatbelt profile, process-group kill, rlimits | 57-104, 107-198 | Process-safe (fresh `mkdtemp` under `$TMPDIR/ls_sbx`, `:73-77, :154`). **Not thread-safe**: `Popen(..., preexec_fn=...)` (`:165-166`) is documented by CPython as unsafe with threads, so workers must be single-threaded *processes* (A.2 `lab_worker.py`). No memory cap on macOS (protocol section 9); with W concurrent sandboxes a runaway allocation is W times worse: keep W small and log RSS. |
| `LS/verify.py` | `verify`, `build_program`, nonce sentinel, `hack_flags` | 23-83 | Nonce per call (`:78`), success = exit 0 AND stdout tail ends with the sentinel (`:81-82`). Unchanged. |
| `LS/common.py` | `canonical_json`, `sha256_*`, `load_config`/`config_hash`, `harness_git_hash` (reads `.git` files, no git command), `hardware_info`, `package_versions`, `process_rss_bytes`, `hf_snapshot_record` | 25-55, 58-81, 93-116, 164-210 | `RESULTS_DIR`, `CONFIG_PATH`, `HARNESS_FILES` (`:17-22`) point at local_stream: the new harness defines its own. `read_jsonl` silently skips a torn line (`:139-142`) and `append_jsonl` (`:146-152`) has no chain: neither is used for the event log. |
| `LS/run_stream.py` helpers | `tiers_from_config` (46-55), `outcome_vector` (58-59), `pair_scores` (62-80: hierarchy + absorbing mask via `winstats.compare`), `RunLock` (186-219), `model_name_matches` (161-164), `check_config_frozen` (152-158) | | `pair_scores` is direction-fixed "B vs A" by argument order; the monitor passes (candidate, incumbent). |
| `LS/timing_pilot.py` | `_norm`, `assert_disjoint`, the full-MBPP row-to-task mapping | 35-36, 66-72, 77-85 | Template for the extended roster; its URL is the mutable `master` (`:29`) and must be replaced by the pinned one. |
| `T2/run_tau2_open.py` server handling | `http_json` (63-67), `server_probe` via `/props` + `/v1/models` (70-80), `server_command` (83-86), `Servers.ensure` (97-135: refuse a foreign server on the port by alias / n_ctx / slots / model_path `:102-117`; `Popen(start_new_session=True)` with log file `:118-122`; readiness loop with exit detection, 600 s `:124-132`), `stop_started` (137-149, SIGTERM then SIGKILL on the group), `smoke_check` (152-165: refuses when `model` != alias or `usage` missing) | | Copy the pattern into `lab_server.py`; add `--metrics`, the `/health` poll, the receipt assertion and the crash supervisor. |
| `T2/common.py` | `gguf_record` (148-169: size + sha256 of every GGUF file against frozen values) | | Reuse the pattern for the coding-model GGUF(s). |
| `T2/run_tau2_open.py` pre-flight | pinned llama.cpp commit read from `.git` (419-424), GGUF check (433-436), per-invocation never-overwritten raw copy (269-278) | | Same refusals in the live harness. |
| `src/winstats.py` (root-owned, read-only) | `Tier`, `compare` (12-48), `normal_mixture_radius` (51-61) | | The monitor imports these and nothing from `wincs.py`; the file's sha256 goes into the freeze bundle. |
| `LS/tests_local_stream.py` | Sandbox/Verify/Agent test classes | 32-201 | Run unchanged as part of the live test suite (they do not touch the stream logic). |

### A.2 NOT reusable, and what replaces it

| delivered piece | why it cannot be used | replacement (new directory `experiments/live_ab/`, module prefix `lab_` so nothing shadows `common.py`/`design.py`/`data.py` of `LS` or `T2`) |
|---|---|---|
| `LS/design.py:27-52` | arm orientation comes from a seeded PRNG stored in `design.json` before the run: the coins sit in the time-0 filtration (root: `reviews/round11_coding_target_scope.md:50`); both arms are run on every task | `lab_design.py`: freezes ONLY the arrival order (and epochs), the roster hash and the config hash. No assignment anywhere in the file. Same refuse-to-overwrite and self-hash pattern as `LS/design.py:59-80`. |
| `LS/run_stream.py:310-338` main loop | strictly sequential, both passes, "never stops early" (`:145`), resume keyed on (task, variant, trial) (`:297, :314-317`); an episode is silently NOT recorded when the served model changes (`:320-323`: a discarded attempt with no usage record) | `lab_orchestrator.py` (below) |
| `LS/run_stream.py:83-102` `monitor_table` | betting e-process (`betting_log_e_ternary`), which the root excluded for the delivered data; pairs are design pairs in arrival order | `lab_monitor.py` with the root's normal-mixture band, fed in reveal order |
| `LS/agent.py:104-148` `OpenAICompatModel` | drops everything except text/usage; failed tries keep only a `repr` in `retry_log` (`:142-146`), so timed-out generations have no usage record; an HTTP error raises without any record (`:147-148`); one `requests.Session` shared by design; seed from the colliding formula | `lab_client.py` |
| `LS/run_stream.py:224-260` manifest | a rewritten JSON file (tmp + `os.replace`), mutable in principle; timestamps are local only | the event log (section B) + anchors |
| `T2/run_tau2_open.py:174-182` amendment loader | a post-freeze file picked up by mtime with a hand-typed `decided_utc`: the root's "no immutable record" finding (`T2/deviation_1_erratum.md:14`) | `amendment` / `amendment_effective` events gated on an external anchor receipt (section B.3) |
| `LS/data.py:65-92` `prepare` | fixed 427+164, mutable URLs | `lab_data.py` (section D) |

### A.3 New modules

`experiments/live_ab/`:

1. **`lab_common.py`**: paths (`results/live_ab/<trial_id>/`), `sys.path` shim that adds ONLY `experiments/local_stream` and
   `src`; `freeze_bundle()` = sha256 over the canonical JSON of {config hash, arrival-order hash, roster hash, protocol.md
   sha256, sha256 of every `lab_*.py`, of the reused `LS/{agent,sandbox,verify,data,common,run_stream}.py`, of
   `src/winstats.py`, GGUF sha256(s), llama.cpp commit}. The bundle hash is the genesis of the event chain (B.2), so a log
   cannot be replayed under a different protocol.
2. **`lab_data.py`**: roster builder (section D) + reference-solution sweep under the sandbox + frozen exclusion list.
3. **`lab_design.py`**: arrival order. `order[e]` = permutation of the roster for epoch e from
   `numpy.random.SeedSequence([design_seed, e])` (a prespecified order is allowed to be pseudorandom; it carries no
   assignment). Arrival k = (epoch, position) -> task uid. Frozen with its sha256 before the first model call.
4. **`lab_eventlog.py`**: the single-writer chain of B.2 (prototype: `eventlog_proto.py`). `append(type, body, durable)`;
   `durable=True` uses `fcntl.F_FULLFSYNC` (plain `fsync` on macOS does not force the drive cache).
5. **`lab_coin.py`**: `os.urandom(8)`; arm = lowest bit of byte 0 under the frozen map {0: incumbent, 1: candidate}; the 8
   raw bytes are logged. **Write-ahead rule**: `coin_drawn` is appended with `durable=True` and only after that call
   returns may the job be sent to a worker. No coin is ever drawn in advance (no pre-generated list, no seed, no
   commit-reveal key: any of these would put the coins into the harness's memory before outcomes and recreate the
   filtration problem). After a decision no coin is drawn at all (`arm_assigned_by_decision`).
6. **`lab_client.py`** `LoggedLlamaClient` (same interface as `OpenAICompatModel`):
   - request body = {model alias, messages, temperature, top_p, top_k, min_p, max_tokens, seed, `cache_prompt: false`,
     `verbose: true`, stream: false}; every sampler field is sent explicitly so the server's CLI defaults
     (`_llama_server_help.txt:250-254`: temp 0.8, top-k 40, top-p 0.95, min-p 0.05) can never leak in. NOTE for the
     protocol: the pilot's MLX runs had no top-k/min-p; the llama.cpp trial must state its own values (suggest
     `top_k: 0, min_p: 0.0` to mirror the pilot).
   - seed = first 31 bits of `sha256("<trial_id>|<arrival>|<attempt>|<call_index>|<try>")`, never 0xFFFFFFFF (llama.cpp's
     "random" sentinel, `LCPP/server-context.cpp:1808-1810`); a unit test proves all seeds distinct over the full grid
     of the frozen horizon. The seed sent and the seed receipted are both logged. No bit-reproducibility is claimed:
     with continuous batching logits depend on batch composition (`LCPP/README.md:587`).
   - emits `llm_request` BEFORE the POST and exactly one of `llm_response` / `llm_error` after it, for every try
     including retried and failed ones, through the worker's pipe (B.1). It compares the receipt
     (`__verbose.generation_settings`) with the request and records `receipt_mismatch` fields; a mismatch is a
     prespecified abort of the trial (E, row 12), not a silent continue.
   - returns the dict `run_episode` expects (`text, prompt_tokens, completion_tokens, tokens_estimated=None,
     call_seconds, retries, retry_log, finish_reason, response_model`), so `LS/agent.py` stays byte-identical.
   - no token estimation path: a 200 response without `usage` is an `llm_error(malformed)`.
7. **`lab_server.py`**: start / probe / supervise llama-server (pattern of `T2/run_tau2_open.py:83-149`). Command (frozen):
   `llama-server -m <gguf> --alias <alias> --host 127.0.0.1 --port <p> -np <W> -c <W*ctx_slot> --no-kv-unified -ngl 99
   --jinja --metrics --no-context-shift --offline --log-file <dir>/llama_<p>.log --log-timestamps` (flags at
   `_llama_server_help.txt:448-452, 25, 430-433, 596-601, 438, 209, 199, 224`). Pre-flight refusals: alias, `total_slots
   == W`, per-slot `n_ctx`, `model_path` realpath, build commit, GGUF size+sha256, and a smoke completion (non-task
   prompt) whose response MUST contain `usage`, `timings` and `__verbose.generation_settings` equal to the request.
   Supervisor: `/health` every 5 s; on exit or 3 consecutive failures emit `server_down`, restart with the same argv,
   emit `server_restarted` (load seconds), never touch the assignment state. `/metrics` counters
   (`llamacpp:prompt_tokens_total`, `llamacpp:tokens_predicted_total`, `n_decode_total`;
   `LCPP/server-task.cpp:1526-1546`) are scraped at start, at every anchor, around every restart and at the end for the
   usage reconciliation (B.1 #24). A restart zeroes the counters, hence the scrape immediately before a planned stop and
   the `counters_lost` flag after a crash.
8. **`lab_worker.py`**: W long-lived worker **processes** (`multiprocessing.get_context('spawn')`, one duplex `Pipe` each,
   single-threaded, own `requests.Session`). Job in: {arrival, attempt, task uid, arm spec (workflow variant, server
   base_url, alias), sampling}. The worker runs the unchanged `run_episode`, streams the client's request/response
   messages up the pipe as they happen, writes the full record to `records/<sha256>.json` (content-addressed,
   fsynced) and finally sends {record_sha256, outcome vector}. The worker never writes the event log.
9. **`lab_monitor.py`** (pure functions of the verified log prefix; no I/O, no clock):
   - `units(revealed_events, rule)`: builds the monitored units Z_n in [-1,1] and D_n in {-1,0,1} from the reveal-ordered
     outcome vectors with `pair_scores` (candidate vs incumbent). The unit rule is a frozen config value (open question
     Q1); the code path must make it impossible to look at an outcome value when forming a unit (it receives arm labels
     and reveal indices first, outcomes second).
   - `band(n, S)`: `S/n -/+ normal_mixture_radius(n, alpha_gate, rho)` for Z and, separately, for D, clipped to
     [-1,1], with NO running intersection (this mirrors what the root retained for the pilot, see sibling report
     `R1_accepted_method.md` section 0.1); alpha, its split across the gates, rho, min_n and margin come from the
     frozen config. The harness logs both bands at every unit; how they combine (marginal vs joint coverage, alpha
     split under drifting targets) is the root's text, not the harness's.
   - `decide(state)`: evaluated on the CURRENT prefix only, never on a remembered earlier crossing of one gate:
     deploy_candidate iff `nb_lo > 0 and d_lo > -margin and n >= min_n` at the same update; harm_keep_incumbent iff
     `nb_hi < 0 and n >= min_n` (R1 notes the paper has no endorsed harm gate yet: the rule id and its alpha share
     must come from the coordinator); first crossing wins; both on the same update resolves to harm (prespecified).
   - Replayability: `lab_verify_log.py` recomputes every `monitor_update` and `decision` from the log alone and must
     reproduce them exactly (floats compared by `repr`).
10. **`lab_orchestrator.py`**: the only writer of the event log; single-threaded loop around
    `multiprocessing.connection.wait(pipes + [timer])`:
    - *Arrival scheduler*: closed loop. When a worker is idle and the phase allows, take the next arrival of the frozen
      order, emit `arrival_ready` (with the list of in-flight arrivals and their arms = the contention context), assign
      (coin or decision), dispatch. An open-loop Poisson clock is a config option, off by default (Q4).
    - *Reveal*: on a worker's final message append `episode_revealed` (durable) with `reveal_index` = count of reveals so
      far; feed the monitor; append `monitor_update`; on a crossing append `decision` (durable), request an immediate
      anchor, set the phase.
    - *Live traffic switch*: phases `randomizing -> decided_candidate | decided_incumbent | horizon_exhausted`. After a
      decision every arrival not yet assigned gets `arm_assigned_by_decision` (no coin). Episodes in flight at the
      decision run to completion, are revealed with `post_decision_inflight: true`, and are NOT fed to the monitor (the
      decision prefix is closed at the crossing); they count in the exposure ledger. The first arrival affected is
      recorded in `traffic_switch`. T4 (A/A) uses the same code; its expected path is `horizon_exhausted`.
    - *Exposure ledger*: per phase and arm: episodes, wall seconds, prompt/completion tokens from successful AND failed
      calls, unknown-usage calls; emitted in `trial_ended`. This is what "measured exposure" can honestly mean; no
      counterfactual is computed by the harness.
    - *Resume*: section E.2.
11. **`lab_anchor.py`**: separate process started by the operator for the run phase; watches for `anchor` events and does
    `git add` + `git commit` of `events.jsonl`, `records/` and the anchor file on the trial branch, optionally `git
    push` and an issue comment carrying the chain head; writes the result back through a spool directory that the
    orchestrator turns into `anchor_receipt` / `anchor_failed`. Anchoring never blocks the trial. (R3 ran none of this;
    pushing and commenting act on the user's account and need the user's go-ahead in the run phase.)
12. **`lab_verify_log.py`**: independent verifier (chain, seq gaps, write-ahead order, one coin per arrival, one reveal per
    arrival, record hashes, monitor replay, usage reconciliation, anchor heads vs `git show <commit>:events.jsonl`).
13. **`lab_mock_server.py`** and **`tests_live_ab.py`**: section F.

---

## B. Event log

### B.1 Envelope and event types (JSON lines, one event per line, UTF-8, `\n` terminated)

Envelope (every event): `seq` (int, 0-based, gapless), `type`, `t_wall_ns` (`time.time_ns()` at append),
`t_mono_ns` (`time.monotonic_ns()`; comparable only within one `inv`), `inv` (invocation id, uuid4 hex), `trial`
(e.g. `"T1"`), `prev` (hex), `body` (object), `h` (hex). Arms are always `"incumbent"` / `"candidate"`; `arrival` is the
1-based index in the frozen order; `attempt` starts at 1.

| # | type | body fields | durable |
|---|---|---|---|
| 1 | `trial_started` (seq 0 only) | `freeze_bundle_sha256`, `config_sha256`, `config` (full), `arrival_order_sha256`, `roster_sha256`, `n_arrivals_max`, `epochs`, `workers`, `arms` {incumbent/candidate: {workflow, server_id, alias, gguf_sha256}}, `monitor` {construction: "winstats.normal_mixture_radius", alpha, rho, min_n, margin, tiers, absorbing_rule, unit_rule, consumption: "reveal_order", tie_rule}, `coin` {source: "os.urandom(8)", bit: "byte0&1", map}, `seed_rule`, `failure_rules_sha256`, `harness_file_sha256` {..}, `reused_file_sha256` {..}, `winstats_sha256`, `protocol_sha256`, `freeze_commit`, `freeze_external_anchor` (URL + server timestamp), `hardware`, `packages`, `llama_cpp_commit` | yes |
| 2 | `invocation_started` | `pid`, `argv`, `resumed` (bool), `log_head_at_start`, `state` {n_coins, n_revealed, n_open_attempts, phase}, `hardware`, `packages`, `drift` (list of differences from `trial_started`; non-empty drift in harness/config hashes = refusal, logged as `invocation_refused`) | yes |
| 3 | `server_started` | `server_id`, `argv`, `pid`, `port`, `gguf` [{path, bytes, sha256}], `props` {model_alias, model_path, total_slots, n_ctx_slot, build_info, default_generation_settings, chat_template_sha256}, `models`, `load_seconds`, `smoke` {request_sha256, receipt, usage, timings, ok} | yes |
| 4 | `server_health` | `server_id`, `ok`, `slots_busy`, `metrics` {prompt_tokens_total, tokens_predicted_total, n_decode_total, requests_processing, requests_deferred}, `rss_bytes` | no |
| 5 | `server_down` | `server_id`, `detected_by` (exit code / health), `returncode`, `inflight` [{arrival, attempt, arm}], `last_metrics`, `counters_lost` | yes |
| 6 | `server_restarted` | `server_id`, `argv`, `pid`, `load_seconds`, `props` (must equal #3's, else `trial_aborted`) | yes |
| 7 | `arrival_ready` | `arrival`, `epoch`, `task_uid`, `benchmark`, `phase`, `inflight` [{arrival, arm, started_mono_ns}] | no |
| 8 | `coin_drawn` | `arrival`, `entropy_source`, `raw_hex` (16 hex chars), `bit`, `arm` | **yes, before dispatch** |
| 9 | `arm_assigned_by_decision` | `arrival`, `arm`, `decision_seq` | yes |
| 10 | `episode_started` | `arrival`, `attempt`, `arm`, `workflow`, `server_id`, `worker`, `worker_pid`, `task_uid`, `assignment_seq` (seq of #8 or #9) | no |
| 11 | `llm_request` | `arrival`, `attempt`, `call_index`, `kind` (code/tests/repair), `try`, `request_id` (client uuid), `server_id`, `body_sha256`, `sampling_sent` {temperature, top_p, top_k, min_p, max_tokens, seed, cache_prompt, verbose}, `messages_sha256`, `n_messages`, `prompt_chars`, `t_send_wall_ns`, `inflight_other` [{arrival, arm}] | no |
| 12 | `llm_response` | keys of #11 that identify the call + `http_status`, `response_id`, `model` (server-side alias), `system_fingerprint`, `finish_reason`, `usage` {prompt_tokens, completion_tokens, total_tokens, cached_tokens}, `timings` {cache_n, prompt_n, prompt_ms, predicted_n, predicted_ms, predicted_per_second}, `receipt` = `__verbose.generation_settings` (whole object), `id_slot`, `stop_type`, `truncated`, `tokens_cached`, `tokens_evaluated`, `tokens_predicted`, `rendered_prompt_sha256`, `content_sha256`, `client_seconds`, `receipt_mismatch` (list, empty when equal) | no |
| 13 | `llm_error` | identifying keys + `error_class` (timeout / connection / http_4xx / http_5xx / malformed), `http_status`, `error` (repr, 300 chars), `client_seconds`, `will_retry`, `usage_known: false`, `server_metrics_delta` (if a scrape brackets the call) | no |
| 14 | `episode_revealed` | `arrival`, `attempt`, `arm`, `reveal_index`, `outcome` {success, latency_s, completion_tokens, prompt_tokens, n_llm_calls, n_failed_calls, n_executions, repair_rounds, timed_out, truncated_any, error_class, infra_flag}, `record_sha256`, `worker_t_start_wall_ns`, `worker_t_end_wall_ns`, `verify_seconds`, `overlap` {max_concurrent, seconds_with_incumbent, seconds_with_candidate, mean_predicted_per_second}, `post_decision_inflight`, `recovered_orphan` | yes |
| 15 | `attempt_aborted` | `arrival`, `attempt`, `reason` (worker_died / orchestrator_restart / operator_stop), `calls_seen` (seqs of #11-13), `usage_known_tokens`, `calls_with_unknown_usage`, `rule: "rerun_same_arm"` | yes |
| 16 | `monitor_update` | `reveal_index`, `unit_n`, `unit` {incumbent_arrival, candidate_arrival}, `z`, `d`, `decisive_tier`, `S_z`, `S_d`, `nb_hat`, `d_hat`, `radius`, `nb_lo`, `nb_hi`, `d_lo`, `d_hi`, `flags` {win, gate, harm, min_n_ok} | no |
| 17 | `decision` | `kind` (deploy_candidate / harm_keep_incumbent / horizon_no_decision), `reveal_index`, `unit_n`, `monitor_seq`, `inflight` [{arrival, arm}], `next_unassigned_arrival`, `rule_id` | yes + anchor |
| 18 | `traffic_switch` | `decision_seq`, `arm`, `effective_from_arrival` | yes |
| 19 | `anchor` | `upto_seq`, `upto_h`, `log_bytes`, `log_sha256`, `n_revealed`, `records_manifest_sha256`, `trigger` (start / periodic / decision / amendment / end) | yes |
| 20 | `anchor_receipt` / `anchor_failed` | `anchor_seq`, `git_commit`, `branch`, `pushed`, `remote`, `external` {kind, url, server_created_at}, or `error` | no |
| 21 | `amendment` / `amendment_effective` | `id`, `text_sha256`, `path`, `reason`, `what_was_known` (counts of revealed outcomes by arm at this seq, computed by the harness, not typed), `applies_from_arrival`; `amendment_effective` requires the `anchor_receipt` of the anchor that covers the `amendment` event | yes |
| 22 | `log_recovery` | `torn_offset`, `torn_len`, `torn_sha256` | yes |
| 23 | `invocation_ended` | `status`, counts | yes |
| 24 | `usage_reconciliation` | per server: counter deltas vs the sum of `usage` over #12 in the same window, `unaccounted_prompt_tokens`, `unaccounted_predicted_tokens`, `windows_with_lost_counters` | yes |
| 25 | `trial_ended` / `trial_aborted` | `phase`, exposure ledger by phase x arm, reconciliation totals, `n_torn_recoveries`, `n_aborted_attempts`, `final_head` | yes + anchor |

Side files (all append-only / write-once): `records/<sha256>.json` (full `run_episode` record, including code and
tracebacks), `requests/<request_id>.json.gz` (full request and response bodies, referenced by `body_sha256` /
`content_sha256`; optional but cheap), `anchors/anchor_<seq>.json`, `logs/llama_<port>.log`.

### B.2 Hash-chain rule

- `canon(x)` = `json.dumps(x, sort_keys=True, separators=(',',':'), ensure_ascii=False)` (identical to
  `LS/common.py:25-26`); floats are written by Python `repr`; no NaN/inf allowed.
- `h_i = SHA256(canon(event_i without key "h"))`, with `event_i.prev = h_{i-1}` and
  `event_0.prev = SHA256("live_ab/eventlog-v1|" + freeze_bundle_sha256)`.
- Line i is exactly `canon(event_i with "h")` + `\n`; the verifier also checks that re-canonicalising the parsed line
  reproduces the bytes, that `seq` is gapless and that `t_wall_ns` never decreases by more than a tolerance within an
  `inv` (clock steps are reported, not fatal).
- Single writer (the orchestrator), descriptor opened `O_WRONLY|O_APPEND|O_CREAT`, one `os.write` per line; durable
  events call `fcntl(fd, F_FULLFSYNC)` before anything depends on them.
- The file is never truncated or rewritten. A byte run that fails verification is legal only (i) as the last line of a
  file being opened for resume, or (ii) when the next valid event is a `log_recovery` committing to exactly those
  bytes (offset, length, sha256) with `prev` = the last valid `h`. Two invalid runs in a row, or an invalid run not so
  committed, fail verification. (Prototype: tampering, deletion and a wrong genesis are all detected.)
- Ordering invariants checked by `lab_verify_log.py`: every `episode_started` points to an earlier durable assignment
  event of the same arrival; at most one `coin_drawn` and one `episode_revealed` per arrival; no `coin_drawn` after a
  `decision`; every `llm_request` has exactly one terminal event unless its attempt was aborted; `monitor_update` n
  increases by 1; `decision` equals the replayed monitor.

### B.3 Anchoring

- Anchor triggers: `trial_started`, every 25 reveals or 10 minutes (whichever first), every `decision`, every
  `amendment`, `trial_ended`. The anchor file holds `upto_seq`, `upto_h`, byte length and sha256 of the log prefix.
- `lab_anchor.py` commits log + records + anchor file on the trial branch; the commit id comes back as
  `anchor_receipt` (it cannot be inside the event it anchors). Local commit times are client-side; the externally
  timestamped evidence is the push and/or an issue comment containing `upto_h` (server-side `created_at`). This is the
  repair for "decision time had no immutable record": the freeze bundle hash and every amendment hash are posted
  BEFORE they take effect (`amendment_effective` is refused without the receipt), and each live decision's head is
  posted within minutes of the switch.
- Anchoring failure never stops the trial (`anchor_failed`), but the final report must list the longest unanchored span.

---

## C. Serving concurrency on one Apple M5 / 32 GB

| question | `mlx_lm.server` 0.31.3 | `llama-server` (build at `4fea119`) |
|---|---|---|
| accepts concurrent HTTP | yes, `ThreadingHTTPServer` (`MLX/server.py:14, 1706`); one generation thread consumes a queue (`:444-452`) | yes (`--threads-http`), slot scheduler |
| actually decodes in parallel | only for requests WITHOUT `seed` and without a draft model (`:370-381, 685-686`): continuous batching via `BatchGenerator`, `--decode-concurrency` 32, `--prompt-concurrency` 8; a seeded request drains the batch and runs alone (`:813-815, 831-836`) | `-np N` slots + continuous batching, on by default (`_llama_server_help.txt:448-452`); with explicit `-np` and `--no-kv-unified` each slot owns `ctx/N` tokens (`:430-433`) |
| per-request seed | global `mx.random.seed` in the single path only (`:955-957`); none in batched mode | per-slot sampler seed from the request; echoed in the receipt |
| sampler receipt | none; `model` is the request echoed (`:1163, 1307`) | `verbose: true` -> `__verbose.generation_settings` (section 0.3); `model` is server-side |
| usage | `usage.prompt_tokens/completion_tokens/total_tokens`, `prompt_tokens_details.cached_tokens` (`:1339-1347`) | same + `timings` per request + global `/metrics` counters (needs `--metrics`) |
| per-request timings | none | `prompt_ms`, `predicted_ms`, tokens/s, `cache_n` |
| health / introspection | `/health`, `/v1/models` (`:1620-1640`) | `/health`, `/props`, `/slots`, `/metrics` (`LCPP/server.cpp:246-250, 285`) |
| stop-token leak | leaves `<|im_end|>` in content (handled by `LS/agent.py:44, 83`) | not expected; `extract_code` is harmless either way |
| model swap (T3) | loads whatever `model` the request names, draining the batch: an accidental swap is one typo away | one process per model/port, pattern already used in `T2/run_tau2_open.py:483-486` |

**Recommendation: llama-server, one process per model, `-np W` with W equal to the number of workers** (so a request
never waits for a slot; every B-type episode has at most one request in flight), `--no-kv-unified`, `-c W*8192`
(delivered data: max prompt tokens summed over a B episode 3,934, max completion 1,474 summed, 1,024 cap per call;
8,192 per slot leaves a wide margin and `--no-context-shift` turns an overflow into a visible `truncated`/error instead
of silent shifting), `cache_prompt: false` per request (slot-dependent prefix reuse would make latency and
`cached_tokens` depend on which slot an episode's next call lands in; the README itself warns about nondeterminism,
`LCPP/README.md:587`; prompts are short so the cost is small). Memory: Q4_K_M 7B about 4.7 GB + KV for 16k tokens about
0.9 GB (28 layers x 4 KV heads x 128 x 2 x 2 bytes = 57 KB/token) per server; two servers for T3 fit easily in 32 GB.
W = 2 is the minimum that produces out-of-order reveals; W = 3-4 raises throughput but also the share of each
episode's latency that is contention. Recommend W = 2 unless the power analysis needs the throughput.

Cost of the switch from the pilot's stack: GGUF Q4_K_M is a different quantization and kernel path than MLX 4-bit, so
success rates, token counts and speeds of the pilot (433/591 both arms; 2.80 s vs 12.48 s mean latency, sequential) are
planning numbers only. A short out-of-design calibration (the 6 `mbpp_full/*` pilot tasks of
`results/local_stream/timing_pilot/pilot_tasks.json`, or hand-written prompts) at concurrency 1, 2, 4 must be run and
logged BEFORE freeze to size W, the timeout and the horizon; it is serving calibration, never outcome data.

**What overlap does to latency as an outcome.**
1. With one server and continuous batching every decode step serves all active slots, and another request's prefill
   chunk delays everyone's next token. An episode's wall latency therefore depends on what runs next to it: the other
   unit's arm (a self_test_repair neighbour keeps the second slot busy about 4.5 times longer than a single_shot
   neighbour) and, after a decision, on the fact that ALL neighbours now have the decided arm. Latency is a unit-level
   outcome with interference.
2. Validity of the root's band does not need no-interference (it bounds the running mean of history-conditional means
   of a [-1,1] score), but the interpretation changes: the latency tier compares "latency under a 50/50 mixed load at
   concurrency W on this machine", not the latency either arm would have when deployed alone. Post-decision latencies
   are a different regime and must not be pooled with pre-decision ones in any contrast.
3. The neighbour's arm is randomized by independent coins, so pre-decision contention is balanced across arms in
   expectation; it adds noise, not a designed bias. For T1/T2 the arm ratio (about 4.5x) dwarfs plausible contention
   (at W = 2 at most about 2x), so the 10% tolerance tier will almost always be decided the same way. For T3/T4 (same
   workflow, similar latencies) the latency tier would be contention-dominated noise: for T4 that is harmless (symmetric
   null), for T3 it argues for a contention-free second tier (completion tokens, or prompt+completion tokens processed)
   with latency reported descriptively (Q3).
4. Reveal order is itself latency-driven: at any instant the revealed set over-represents fast episodes of each arm
   (at most W-1 units are hidden). This matters for the unit rule (Q1) and is the reason every reveal carries
   `reveal_index`, both clocks and the in-flight list.
5. Logged so the effect can be measured rather than argued: per call `timings.predicted_per_second` and `id_slot`;
   per request the in-flight list; per episode the overlap seconds by neighbour arm; `/slots` busy count in
   `server_health`.
6. `latency_s` keeps the frozen scope of `LS/agent.py:247` (dispatch to final candidate, excludes hidden-test
   verification). With W = slots there is no server-side queueing inside it; time spent waiting for a server restart
   IS inside it (E, row 5).

---

## D. Task data

- `LS/data.py:23-32` downloads two files once and caches them under `work/local_stream/data/` (git-ignored):
  `sanitized-mbpp.json` (255,053 bytes, sha256 `ca95deaa...`) and `HumanEval.jsonl.gz` (44,877 bytes, sha256
  `b796127e...`); `prepare()` (`:65-92`) asserts 427 + 164 (`:73-74`), writes the canonical `tasks.json` (602,791 bytes;
  list sha256 `23727895...`). All four files are present locally; pinned upstream revisions, licences (MBPP CC-BY-4.0,
  HumanEval MIT) and hashes are in `results/local_stream/data_manifest.json`.
- The full MBPP release (974 problems, `mbpp.jsonl`, 563,743 bytes, sha256 `ccf64cea...a9f`, pinned revision
  `f82046ba5aabbbb427dbfd38a254d26bff08b533`) is **not on disk**: `LS/timing_pilot.py:39-53` fetched it into memory and
  kept only the 6 pilot tasks (`results/local_stream/timing_pilot/pilot_tasks.json`); the manifest says "no local copy
  was kept". Spotlight and a search of the repo, `work/`, the scratchpad and the HF cache found no `mbpp.jsonl`; the HF
  datasets cache is empty (`datasets` is installed, `evalplus`/`human_eval` are not).
- Distinct tasks available to a trial: **591 now, with no download**. With the pinned 564 KB file: at most 974 + 164 =
  1,138 task ids, i.e. up to 547 extra MBPP problems minus (a) prompt-normalised duplicates of sanitized tasks
  (`LS/timing_pilot.py:56-61`), (b) the 6 pilot tasks if one wants them to stay out-of-design, (c) problems whose
  reference solution fails `verify()` under the Seatbelt sandbox or whose entry point cannot be resolved
  (`mbpp_entry_point`, `LS/data.py:35-44`). The exact count exists only after the file is fetched and the sweep is
  run; both must happen before freeze and before any model call, and the exclusion list with reasons is frozen in the
  roster. The unsanitized problems are noisier (pilot: 1/6 and 2/6 successes versus 73% on the 591), so they form their
  own stratum and contribute fewer both-succeed units to the lower tiers. EvalPlus adds tests, not tasks.
- Reuse across T1-T4 and across epochs is a design decision (each trial is separately randomized, so validity per
  trial does not need disjoint rosters, but the four trials are then not independent replicates and the pilot already
  exposed all 591 tasks to both workflows on the MLX stack). `lab_design.py` supports: one roster for all trials with
  a fresh order per trial; disjoint partitions; and E epochs per trial. Every arrival is still a single exposure.
- `lab_data.py` must use the pinned URLs of `results/local_stream/data_manifest.json`, never the `master` URLs in
  `LS/config.json:29-30` and `LS/timing_pilot.py:29`, and must refuse a byte/sha mismatch.

---

## E. Failure modes and prespecified handling

E.1 Principle (goes into the protocol verbatim): every arrival that received a durable assignment yields exactly one
revealed outcome under that assignment (intention to treat). A completed episode is never re-run, whatever its
outcome. An attempt is re-run only when it never returned to the orchestrator; the rerun keeps the logged arm, never
a new coin. All usage of every attempt and every try is logged; usage that cannot be known is counted as such and
bounded by the server counters.

| # | failure | detection | outcome rule (fixed in advance) | accounting |
|---|---|---|---|---|
| 1 | request timeout (`request_timeout_s`; with `max_tokens` 1,024 and W = slots this needs a hung server) | `requests.Timeout` in the client | retry up to `max_connection_retries` with backoff (as `LS/agent.py:142-146`); after the last try the call raises, `run_episode` records `error` and grades the last candidate that exists (`:242-249`); success = False if none | `llm_error` per try, `usage_known: false`; server cancels the generation on disconnect (`LCPP/server-http.cpp:595-659`); tokens bounded by the `/metrics` delta |
| 2 | HTTP 4xx/5xx | status code | not retried (as `LS/agent.py:147-148`); same consequence as row 1 | `llm_error` with status and body head |
| 3 | 200 without `usage`, without `timings`, or non-JSON | client | treated as row 2 (`malformed`); no token estimation | `llm_error` |
| 4 | truncated generation (`finish_reason == "length"` or `truncated`) | response | NOT an error: the text is used as is, `extract_code` runs, the episode continues; `truncated_any` recorded | full usage known |
| 5 | server crash / hang | supervisor (`/health`, exit code) and client connection errors | supervisor restarts with the identical argv; the client's retry loop waits up to a frozen `server_recovery_s` (suggest 180 s) so an in-flight call usually survives; the waiting time stays inside `latency_s`; if recovery fails in time the call fails as row 1; `infra_flag = true` on every episode in flight during the outage; primary analysis keeps them; a sensitivity analysis without them is labelled secondary in advance | `server_down` / `server_restarted`; counters lost across a crash are reported as an unreconciled window |
| 6 | restarted server differs (props, slots, alias, build) | `server_restarted.props` vs `server_started.props` | `trial_aborted`; nothing is dispatched; revealed data stay valid up to that seq | anchor |
| 7 | sandbox wall-clock or CPU kill, fork refusal, PermissionError | `LS/sandbox.py:170-181`, rlimits | in a self-test: counts as a failed self-test and triggers repair (`LS/agent.py:231-241`); in verification: success = False, `timed_out` recorded | `execution_seconds`, `verify_seconds` |
| 8 | sentinel missing with exit 0 (early exit) | `LS/verify.py:81-82` | success = False (1 such episode in the pilot) | `sentinel_seen` |
| 9 | empty / unextractable code | `LS/verify.py:72-76` | success = False | record |
| 10 | worker process dies (segfault, OOM kill, operator kill) | pipe EOF / exit code | `attempt_aborted(worker_died)`; new worker; same arrival, same arm, `attempt+1`; after `max_attempts` (suggest 3) the arrival is revealed as failure with `error_class = harness_abort` (keeps the one-outcome-per-assignment rule and stops infinite loops) | calls seen so far are already in the log; unknown tail bounded by `/metrics` |
| 11 | orchestrator crash / power loss / Ctrl-C | next invocation | E.2 | `invocation_started.resumed`, `attempt_aborted(orchestrator_restart)` for every open attempt |
| 12 | receipt mismatch (server used a setting different from the request) | client compares `__verbose.generation_settings` with `sampling_sent` | the episode completes and is revealed (ITT), then `trial_aborted(receipt_mismatch)` before the next dispatch; the log up to that point is reportable, the trial cannot claim its sampler | `receipt_mismatch` list |
| 13 | served `model` alias differs | every `llm_response` | same as row 12 (the delivered harness silently dropped such an episode, `LS/run_stream.py:320-323`; here nothing is dropped) | |
| 14 | clock step / sleep (lid closed) | `t_wall_ns` vs `t_mono_ns` drift between events | logged `clock_anomaly` in `server_health`; episodes overlapping a sleep get `infra_flag`; the run machine is kept awake by the operator (caffeinate) | |
| 15 | disk full / log write error | `OSError` on append | orchestrator stops dispatching immediately (an unloggable coin may not be used); workers finish; their results are held in `records/` and recovered as orphans on resume | |
| 16 | memory pressure from a runaway candidate (no cap on macOS) | RSS sampling in `server_health` | none automatic beyond the 10 s kill; disclosed; W kept small | |
| 17 | monitor exception (bug) | try/except around `lab_monitor` | dispatch pauses, `trial_paused(monitor_error)` is logged; no decision is taken by hand; after a fix (an `amendment` with external receipt) the monitor is replayed from the log, which is legitimate because it is a pure function of logged events | |

E.2 Resume (implemented as a pure function of the verified log; prototype `state_from_log` / `next_action`):

1. Verify the chain; commit a torn tail with `log_recovery`; refuse if the freeze bundle, config or harness hashes
   differ from `trial_started`.
2. For each arrival in frozen order: no durable assignment -> it is simply the next arrival (a torn `coin_drawn` line
   never reached `F_FULLFSYNC`, so dispatch cannot have happened; the torn bytes stay in the file and
   `n_torn_recoveries` is reported, expected 0); durable assignment + `episode_revealed` -> skip forever; durable
   assignment without reveal -> if `records/` holds a content-addressed record for (arrival, attempt) that no event
   references, emit `episode_revealed(recovered_orphan: true)` from it (the outcome already exists; re-running would be
   a second draw that an observer could suspect of being outcome-dependent), else `attempt_aborted` + rerun under the
   same arm.
3. Rebuild the monitor state by replay; if a `decision` exists the phase is restored and no coin is ever drawn again.
4. Reveal order after a resume is the order of the new `episode_revealed` events; recovered orphans are revealed
   first, in arrival order (frozen tie rule).

---

## F. Test plan without any model

F.1 Unit tests (`tests_live_ab.py`, stdlib `unittest`, target < 60 s):

| group | tests |
|---|---|
| event log | chain verifies; tamper / delete / reorder / truncate-middle / wrong-genesis detected; torn tail -> `log_recovery`, file never shrinks; canonical bytes round-trip; seq gapless; durable append uses `F_FULLFSYNC` when available |
| coin | `coin_drawn` is durable before any worker message (spy on the pipe: assert log fsync count increased first); one coin per arrival; none after a decision; bit map; with `os.urandom` monkeypatched to a fixed stream the arms follow the stream (proves no other randomness enters); 10,000 real draws within binomial limits |
| seeds | all per-call seeds distinct over the full (arrival, attempt, call, try) grid of the frozen horizon; never 0xFFFFFFFF; regression test that the old formula collides (2,960 / 4,728) |
| monitor | band equals `winstats.normal_mixture_radius` to the last bit; min_n respected; deploy needs both bands; harm rule; tie rule; unit builder never reads outcomes before the unit is fixed (outcome objects raise on early access); replay from a log reproduces every `monitor_update` and `decision` |
| scheduler / switch | scripted fake workers with chosen latencies: reveals out of arrival order; in-flight episodes at the decision are revealed with `post_decision_inflight` and not fed to the monitor; every later arrival is `arm_assigned_by_decision`; `traffic_switch.effective_from_arrival` correct; horizon exhaustion |
| resume | kill points injected after each of: `arrival_ready`, `coin_drawn`, `episode_started`, first `llm_request`, record file written, `episode_revealed`, `monitor_update`, `decision`; after each kill a resume yields a log that passes `lab_verify_log.py`, never a second coin, never a second reveal, orphan recovery where a record exists; double-resume is idempotent; two orchestrators -> `RunLock` refusal |
| client | for each mock behaviour below: exactly one terminal event per `llm_request`; failed tries logged with `usage_known: false`; receipt comparison catches a changed temperature/top_k/seed; no estimation path |
| accounting | sum of `usage` over `llm_response` + mock-declared lost tokens == mock `/metrics` deltas; exposure ledger totals equal a recomputation from events |
| reused code | run `LS/tests_local_stream.py` classes `SandboxTests`, `VerifyTests`, `AgentTests` unchanged; hidden-test leak sweep over the frozen roster (and over the extended roster if adopted) |
| freeze | any byte change in a bundled file changes the genesis and makes resume refuse |

F.2 Mock server (`lab_mock_server.py`, stdlib `ThreadingHTTPServer`, no model): implements `/health`, `/props`,
`/v1/models`, `/slots`, `/metrics`, `/v1/chat/completions` with the llama-server response shape of section 0.3
(`usage`, `timings`, `__verbose.generation_settings` echoing the request, `id_slot`, `model` = alias). Text comes from
the deterministic logic of `LS/agent.py:151-188` (`MockModel`: reference solution or stub by a hash of task / arm),
with arm-specific success probabilities set per scenario. Latency is simulated as `tokens / (rate / active_slots)`
so overlapping requests slow each other like continuous batching. Fault injection by request counter: timeout (sleep
past the client timeout), 500, connection reset, malformed JSON, missing `usage`, `finish_reason = "length"`, a
receipt that differs from the request, a changed alias, process exit (to exercise the supervisor and restart path).

F.3 Dry-run scenarios (each writes to a scratch results dir and must end with `lab_verify_log.py` PASS and monitor
replay equality; a MOCK banner on every derived file, as `LS/analysis.py` does for dry runs):

1. T1-like: equal success, candidate 4.5x faster -> expect win band to cross early, gate band not (documents finding
   0.5 on mock numbers); horizon exhaustion path.
2. T1-like with a wide margin (e.g. 0.25) -> full deploy path, live switch, post-decision exposure ledger.
3. T2-like: harmful candidate -> harm crossing near 60-75 units, switch to incumbent.
4. T4 A/A, 200 seeds of the mock -> no crossing in the large majority (a smoke check of wiring, not a coverage study; the
   coverage claim is the root's theorem).
5. Chaos run: random kills of workers, the mock server and the orchestrator every 20-60 s until the horizon; final log
   verifies; zero double coins / double reveals; all attempts accounted.
6. Anchor drill in a throwaway git repository under the scratchpad (never the project repo): anchors committed,
   `git show <commit>:events.jsonl` prefix hashes equal the `anchor` events.

F.4 What still needs a model and therefore belongs to the run phase, not to this plan: the receipt smoke test against
the real llama-server build; the concurrency calibration (C); the full-MBPP reference sweep needs only the dataset
download, not a model.

---

## G. Open questions for the coordinator / statistical readers

- Q1. Unit rule under per-arrival coins and reveal-order monitoring. Options the harness can implement: (a) FIFO
  matching of the j-th revealed incumbent episode with the j-th revealed candidate episode (uses every episode, but
  the second member's partner is already in the history, so mu_n is a history-conditional "new episode versus a revealed
  opposite-arm episode" mean, and unit formation is driven by latency); (b) arrival-order matching with in-order commit
  (clean of latency-driven selection, delays decisions by up to W-1 reveals); (c) one coin per block of two consecutive
  arrivals (balanced, natural units, both members overlap each other, but the second arrival's arm is not a fresh coin,
  which departs from the coordinator's wording; it is, however, the randomization unit of the root's paper according
  to `R1_accepted_method.md` section 0.4). The harness cost of switching between (a), (b), (c) is one config value
  (`assignment_unit` in {arrival, block2}, `unit_rule`) plus the `coin_drawn` body gaining `block` and `position`
  fields; the write-ahead, resume and switch logic are identical. The root must accept the choice before freeze.
- Q2. Gate margin / horizon given finding 0.5 (0.03 needs about 12,094 units under the accepted band).
- Q3. Second tier for T3/T4 under contention: wall latency, or tokens with latency descriptive?
- Q4. Closed-loop arrivals (default) or an open-loop clock?
- Q5. Are tasks reused across T1-T4 and across epochs, given that the pilot already exposed all 591 tasks?
- Q6. Sampler fields for llama.cpp that the pilot never had (`top_k`, `min_p`): mirror MLX (0 / 0.0) or llama.cpp
  defaults? Must be in the frozen config either way.
- Q7. External anchor channel (push only, or push + issue comment); both act on the user's GitHub account.
