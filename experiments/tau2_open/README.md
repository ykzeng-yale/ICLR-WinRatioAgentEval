# tau2 open-model stream: 7B incumbent vs Qwen3-4B candidate agent on tau2-bench airline, open user simulator

Harness for GitHub issues #1 (prospective randomized stream) and #2 (open/local-model
replication) on the paper's own benchmark, tau2-bench (airline, tasks 1-49; task 0 excluded because
the coordinator's smoke runs used it), with open weights only: agent A `qwen2.5-7b-instruct`
(incumbent), agent B `qwen3-4b-instruct-2507` (candidate: newer, smaller), user simulator
`qwen2.5-7b-instruct` for both arms, served by llama.cpp on one machine. Agent temperature 0.3 in
both arms, user simulator 0.0. No paid API; the whole stack is Apache-2.0 (weights) and MIT
(tau2-bench, llama.cpp). The frozen pre-registration is `protocol.md` (revision 2).

Layout

| file | role |
|---|---|
| `config.json` | frozen run configuration (models + GGUF hashes, ports, llama-server and tau2 flags, per-role temperatures, hierarchy, alpha, margin, min_n); its sha256 is stamped on the design and every episode |
| `common.py` | paths, hashing, provenance (git hash read from `.git` files; no git command), GGUF check |
| `design.py` | frozen design generator (seed 20260918): per-trial-block arrival permutation, 49 disjoint pairs, per-pair orientation; writes `results/tau2_open/design.json` + `.sha256` |
| `run_tau2_open.py` | orchestrates llama-server processes (7B on 8081 for user + agent A, Qwen3-4B on 8082 for agent B; started by the harness with the frozen flags), pre-flight refusals, smoke completion per server, `tau2 run` per arm with per-role `api_base` and temperature, copies `results.json` into `results/tau2_open/raw/` (canonical + per-invocation copy), append-only manifest, resumable (`--auto-resume`) |
| `build_episodes.py` | parses the tau2 JSONs into `results/tau2_open/episodes.csv` (success, agent tokens from `usage`, tool calls, duration, termination, errors), joined with the design |
| `analysis.py` | online pass-1 stream analysis with post-hoc monitoring log over the prespecified sequence (all 49 pairs and the block-1 subset = pairs 1-24), same-task shadow analysis (task clusters), component effects, decision-rule table, sensitivity (tolerance x tier order, incl. token-first H4 and duration tier), H1/H3 flags, report skeleton |
| `tests_tau2_open.py` | unit tests (stdlib unittest): design determinism across PYTHONHASHSEED, pairing invariants (98/49/24), parser on the smoke JSONs (incl. the Qwen3-4B retail tool-call smoke), orchestrator dry run + per-invocation raw copies, served-model/temperature checks, analysis on mock episodes |
| `protocol.md` | frozen pre-registration, deviations log, revision history and requirement checklist |

## Commands

All commands from the repository root; `PY` is the project interpreter.

```bash
PY=/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python
cd /Users/yukangzengcmac/ICLR-WinRatioAgentEvals

# 1. Freeze the design BEFORE any episode (refuses to overwrite; already generated, revision 2)
$PY experiments/tau2_open/design.py
cat results/tau2_open/design.sha256

# 2. Unit tests (a few seconds; no server, no tau2 call)
$PY -m unittest experiments/tau2_open/tests_tau2_open.py -v

# 3. Dry run with the deterministic mock generator (tau2 schema; never report these numbers)
$PY experiments/tau2_open/run_tau2_open.py --dry-run --results-dir results/tau2_open/dryrun
$PY experiments/tau2_open/analysis.py --results-dir results/tau2_open/dryrun

# 4. Full run (both arms; starts the servers it needs with the frozen flags and stops the ones it started; resumable).
#    Stop any temporary llama-server on 8081/8082 first: pre-flight refuses a running server whose alias, model path,
#    context size or slot count differ from the config (do not use --accept-running-server for the design run).
#    Pre-flight also refuses config drift, wrong tau2/llama.cpp commit, GGUF size/sha256 mismatch, airline data
#    drift, or a concurrent run. Nothing else may use the GPU while it runs (single inference stream; durations are an outcome).
$PY experiments/tau2_open/run_tau2_open.py
#    one arm at a time:  --arm A   /  --arm B     (arm B needs the 7B server for the user simulator: it is started if absent)
#    re-running the same command resumes: tau2 skips completed (trial, task, seed) units and re-runs infrastructure_error units;
#    complete arms are skipped; every invocation leaves raw/tau2_open_arm<X>.<invocation_id>.json untouched

# 5. Rebuild episodes.csv from the raw copies (done automatically when both arms are complete)
$PY experiments/tau2_open/build_episodes.py            # optional: --tokenize-url http://127.0.0.1:8081 for calls without usage

# 6. Analysis (writes monitor_pass1.csv, monitor_state.json, summary.json, decision_rules.csv, sensitivity.csv, task_scores.csv, report.md)
$PY experiments/tau2_open/analysis.py
```

What the runner executes (recorded in `run_manifest.json`):

```bash
# servers (llama.cpp commit 4fea119, built 2026-09-18); temperature is sent per request, so no --temp flag
llama-server -m <7B q4_k_m part 1> --alias qwen2.5-7b-instruct    --port 8081 -c 32768 -np 1 --jinja -ngl 99 --host 127.0.0.1
llama-server -m <Qwen3-4B q4_k_m>  --alias qwen3-4b-instruct-2507 --port 8082 -c 32768 -np 1 --jinja -ngl 99 --host 127.0.0.1
# tau2 (commit b7ea907), from the tau2-bench checkout, arm A then arm B
uv run tau2 run --domain airline --agent llm_agent --agent-llm openai/qwen2.5-7b-instruct \
  --agent-llm-args '{"temperature": 0.3, "api_base": "http://127.0.0.1:8081/v1"}' \
  --user user_simulator --user-llm openai/qwen2.5-7b-instruct --user-llm-args '{"temperature": 0.0, "api_base": "http://127.0.0.1:8081/v1"}' \
  --num-trials 2 --task-ids 1 2 ... 49 --max-steps 100 --max-errors 10 --max-concurrency 1 --hallucination-retries 0 \
  --seed 300 --save-to tau2_open_armA --auto-resume --log-level WARNING
# arm B: --agent-llm openai/qwen3-4b-instruct-2507 --agent-llm-args '{"temperature": 0.3, "api_base": "http://127.0.0.1:8082/v1"}' --save-to tau2_open_armB
```

Routing: tau2 forwards the llm-args dicts as `litellm.completion(**kwargs)` and litellm honours
`api_base` per call, so the agent and the user simulator reach different servers without a proxy
(verified live with litellm 1.81.11 and in dry mode with two stubs). After each batch the served model
of every assistant message (agent alias) and of every user message (user-simulator alias) and the
info block's llm_args temperatures are checked against the config. `OPENAI_API_KEY` is set to a
placeholder if unset. Sampling: tau2 forwards its per-trial seed (626729 / 373753) as `seed` in every request and
llama-server seeds its sampler with it, so agent sampling at temperature 0.3 is reproducible up to the
serving stack's nondeterminism (the design, configuration and greedy user simulator are exactly reproducible).

## Outputs (results/tau2_open/)

`design.json` + `design.sha256` (frozen before outcomes), `run_manifest.json` (append-only:
one record per invocation with config, GGUF sizes/sha256, tau2 and llama.cpp commits, server
commands and `/props`, smoke completions, tau2 commands, per-arm return codes, elapsed time,
missing units, infrastructure-error counts, info mismatches, server RSS, harness file hashes,
hardware, package versions), `raw/tau2_open_arm{A,B}.json` (verbatim copies of tau2's
`results.json`, overwritten on resume) and `raw/tau2_open_arm{A,B}.<invocation_id>.json`
(per-invocation copies, never overwritten), `logs/`, `episodes.csv` (every episode), then the
analysis files. `dryrun/` (if created) holds mock output only; its `report.md` carries a MOCK DATA
banner.

## Resource estimates (replaced by measured values in the manifest)

- Weights: 7B Q4_K_M 4,683,073,632 bytes (2 files) + Qwen3-4B Q4_K_M 2,497,281,120 bytes
  (7,180,354,752 bytes in total), in `~/.cache/huggingface/hub`.
- Memory: about 11 GB resident during arm B (both servers with 32k context); 32 GB machine.
- Time: the coordinator's 13-message airline smoke episode took 60 s on the 7B server and the
  36-message retail smoke episode 150 s on the Qwen3-4B agent + 7B user; with up to 100 steps
  expect 1-5 min per episode, roughly 4-16 h for 196 episodes, strictly sequential.
- Results: raw JSON about 5-20 MB per arm per copy.
