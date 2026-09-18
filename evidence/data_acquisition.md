# Data acquisition report: real agent-trajectory sources

Acquisition date: 2026-09-17 (America/New_York), 2026-09-18 UTC. All raw third-party files live under `work/empirical_sources/` (to be git-ignored); provenance (URL, bytes, sha256, UTC download time) for every file is in `work/empirical_sources/manifest.json`. Nothing here was produced by paid API calls. This report extends `evidence/empirical_feasibility.md`; where that document described local files, note that `work/empirical_sources/` did not exist at the start of this session, so everything below was (re)acquired now and hashed.

Total downloaded: 1.003 GB (tau2 604 MB, SWE-bench Lite 95 MB, HAL 304 MB encrypted plus decrypted copies).

## A. tau2-bench released trajectories

**Source and pin.** Repository `sierra-research/tau2-bench`, commit `b7ea9074c1cba482b30687fecdb5c8425fd6f619` (GitHub API commit author date 2026-09-17T21:57:12Z; this is the current head and the repository is now branded τ³-bench). The folder `data/tau2/results/final` exists at that commit: 26 result JSON files plus a `figs/` subfolder (26 PDFs, two CSVs, one `cost_info.txt`). Listing: `https://api.github.com/repos/sierra-research/tau2-bench/contents/data/tau2/results/final?ref=b7ea9074…`. All 26 JSON files were downloaded from `raw.githubusercontent.com/sierra-research/tau2-bench/b7ea9074…/data/tau2/results/final/<name>`; every received byte count equals the GitHub-reported blob size; sha256 per file in the manifest. `LICENSE` at the same commit was downloaded (MIT, "Copyright (c) 2025 Sierra Research", sha256 `e67c5aa0…52fe`). Also kept: `figs/cost_info.txt` (the authors' own mean/sum cost per LLM) and the two `action_success_rates_*.csv`.

**Schema (verified on the files).** Top level `timestamp, info, tasks, simulations`. `info` carries `git_commit`, `num_trials` (4), `max_steps` (200), `max_errors` (10), `user_info.llm` = `gpt-4.1-2025-04-14` with `{"temperature": 0.0}` in every file, `agent_info.llm` and `agent_info.llm_args` (`{"temperature": 0.0}`, or `{"reasoning_effort": "high"}` for o4-mini), and `environment_info.policy`. Each simulation has `id, task_id, timestamp, start_time, end_time, duration, termination_reason, agent_cost, user_cost, reward_info, messages, trial, seed`. `reward_info.reward` is binary (0/1) in all 10,832 records; `reward_basis` and `reward_breakdown` (DB, COMMUNICATE, NL_ASSERTION, ...) are present. Messages have `role` (assistant/user/tool), `tool_calls`, `cost`, `usage` (populated for ~94% of LLM messages; e.g., 3,251 of 3,451 airline GPT-4.1 messages), `turn_idx`, `timestamp`. `agent_cost` equals the sum of assistant-message `cost` to 6e-17.

**Derived table.** `work/empirical_sources/tau2_runs.csv` (10,832 rows; one per simulation) with columns `model, domain, domain_env, config, user_llm, task_id, trial, seed, reward, agent_cost, user_cost, duration, n_assistant_tool_calls, n_user_tool_calls, n_messages, termination_reason, git_commit, sim_id, start_time, source_file, agent_llm_args`. `domain`/`config` are parsed from the file name (`<agent>_<domain>_<config>_<user>_4trials.json`); `domain_env` is `info.environment_info.domain_name`. Per-file metadata is in `tau2_files_summary.csv`; per model×domain×config summary in `tau2_summary.csv`.

**Summary of the strict-comparability set (config `default`, and `base` for GPT-4.1-mini; user simulator identical everywhere):**

| model | domain | tasks | runs | success | mean agent cost ($) | mean user cost ($) | mean asst. tool calls | mean duration (s) | max_steps terminations |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| claude-3-7-sonnet-20250219 | airline | 50 | 200 | 0.500 | 0.349 | 0.012 | 8.39 | 63.9 | 0 |
| gpt-4.1-2025-04-14 | airline | 50 | 200 | 0.560 | 0.054 | 0.013 | 7.66 | 65.3 | 0 |
| gpt-4.1-mini-2025-04-14 | airline | 50 | 200 | 0.505 | 0.013 | 0.016 | 7.94 | 70.4 | 0 |
| o4-mini-2025-04-16 (high) | airline | 50 | 200 | 0.590 | 0.051 | 0.011 | 5.17 | 75.2 | 0 |
| claude-3-7-sonnet-20250219 | retail | 114 | 456 | 0.787 | 0.335 | 0.014 | 7.88 | 61.3 | 0 |
| gpt-4.1-2025-04-14 | retail | 114 | 456 | 0.741 | 0.058 | 0.013 | 7.68 | 63.3 | 0 |
| gpt-4.1-mini-2025-04-14 | retail | 114 | 456 | 0.660 | 0.014 | 0.016 | 7.99 | 68.8 | 0 |
| o4-mini-2025-04-16 (high) | retail | 114 | 456 | 0.715 | 0.057 | 0.014 | 6.87 | 79.0 | 0 |
| claude-3-7-sonnet-20250219 | telecom | 114 | 456 | 0.493 | 0.582 | 0.097 | 6.84 | 117.7 | 1 |
| gpt-4.1-2025-04-14 | telecom | 114 | 456 | 0.342 | 0.110 | 0.086 | 6.67 | 118.6 | 3 |
| gpt-4.1-mini-2025-04-14 | telecom | 114 | 456 | 0.439 | 0.046 | 0.085 | 18.25 | 204.0 | 32 |
| o4-mini-2025-04-16 (high) | telecom | 114 | 456 | 0.421 | 0.092 | 0.073 | 8.89 | 191.2 | 0 |

That is 3,336 runs for the three `default` models plus 1,112 for GPT-4.1-mini (4,448), as the earlier audit stated. The remaining 6,384 rows are telecom ablations (`telecom`/`telecom-workflow` × `no-user`, `no-user-op`, `op`) for GPT-4.1 and o4-mini only (456 runs each); these use different environment configurations (no-user variants terminate with `agent_stop` and have zero user cost) and must not be pooled with `default`. Embedded harness commits: airline/retail `c30d59aa…`, telecom `f125e68a…`, GPT-4.1-mini (all domains) `ade39493…`. The authors' `cost_info.txt` mean agent cost per LLM (0.4385, 0.0852, 0.0268, 0.0667 for Claude 3.7, GPT-4.1, GPT-4.1-mini, o4-mini) is a pooled average over more files than the `default` set and is reproduced only when all 26 files are pooled.

**Checks.** Within each domain the (task_id, trial, seed) sets are identical across the four models (airline, retail, telecom), so task-and-trial pairing is exact. Termination reasons overall: `user_stop` 7,148, `agent_stop` 3,648 (all in `no-user*` ablations), `max_steps` 36. Reward values are exactly {0, 1}. No missing cost/duration fields.

## B. SWE-bench Lite SWE-agent trajectories

**Metadata.** From `SWE-bench/experiments` (main head at fetch: `40f164d5b8f1d249bf95a6df8b74b577fd8e519d`, 2026-09-03), for `evaluation/lite/20240402_sweagent_gpt4` and `evaluation/lite/20240402_sweagent_claude3opus`: `results/results.json`, `metadata.yaml`, `README.md` downloaded and hashed. `metadata.yaml` points `assets.trajs` at `s3://swe-bench-submissions/lite/<run>/trajs` (GPT-4 run model tag `gpt-4-1106-preview`; the Opus run has no model tag but `model_display: Claude 3 Opus`). The last metadata commit for the GPT-4 folder is 2026-08-09 ("Update metadata"); the S3 rename commit is 2026-01-06. The repository has **no LICENSE file** (`/LICENSE` returns 404 on main); the README asks that SWE-bench be cited and says entries "hold entries, not artifacts". Rights to redistribute trajectories remain UNVERIFIED; keep them under `work/`.

**Trajectories.** The bucket is publicly listable (`?list-type=2&prefix=lite/<run>/trajs/`): exactly 300 objects per run. All 600 `.traj` files were downloaded (6 threads), every size matches the S3 listing, and every S3 ETag (single-part MD5) matches the MD5 of the received file; sha256 per file in `work/empirical_sources/swe_lite/_download_records.json` and the manifest. Totals: GPT-4 run 55.5 MB, Opus run 39.8 MB.

**Schema (verified).** `environment` (`swe_main`), `trajectory` (list of steps with `action, observation, response, state, thought`), `history`, `info` with `exit_status`, `submission` (patch), and `model_stats` = `{total_cost, instance_cost, tokens_sent, tokens_received, api_calls}`. `total_cost` is cumulative across the batch (e.g., 459.67 on the first astropy instance of the GPT-4 run) and is kept in the table only as `total_cost_cumulative_DO_NOT_USE`.

**Derived table.** `work/empirical_sources/swe_lite_runs.csv` (600 rows) with `run, instance_id, repo, resolved, in_generated, in_no_generation, instance_cost, api_calls, tokens_sent, tokens_received, n_trajectory_steps, n_history, exit_status, has_submission, total_cost_cumulative_DO_NOT_USE`.

| run | n | repos | resolved | resolved rate | mean instance_cost ($) | median | mean api_calls | mean steps | exit statuses |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20240402_sweagent_gpt4 | 300 | 12 | 54 | 0.180 | 2.51 | 2.29 | 21.5 | 21.4 | submitted 203, submitted (exit_cost) 95, exit_cost 2 |
| 20240402_sweagent_claude3opus | 300 | 12 | 35 | 0.117 | 3.42 | 4.02 | 17.1 | 17.1 | submitted 133, submitted (exit_cost) 156, exit_cost 11 |

Paired outcome table (rows GPT-4, columns Opus): both fail 236, GPT-4 only 29, Opus only 10, both resolve 25. Repository composition: django 114, sympy 77, matplotlib 23, scikit-learn 23, pytest 17, sphinx 16, astropy 6, requests 6, pylint 6, xarray 5, seaborn 4, flask 3.

**Anomalies in the official `results.json`.** GPT-4 run: `no_generation` lists `psf__requests-863` twice (18 entries, 17 unique); `sympy__sympy-14817` appears in neither `generated` nor `no_generation` although its trajectory has a submission and cost $1.17; `reset_failed` = [`sphinx-doc__sphinx-11445`]. Both runs: a few instances listed under `no_generation` nonetheless have a non-empty `submission` in the trajectory (4 for GPT-4, 3 for Opus). Use `resolved` membership as the success label and treat these bookkeeping oddities as fixed features of the historical release. Cost is present for all 600 instances (min 0.42, max 4.75; the ~$4 ceiling reflects SWE-agent's per-instance budget, visible as `exit_cost`).

## C. Holistic Agent Leaderboard (HAL)

**What is public.** The HAL paper (Kapoor et al., arXiv:2510.11977, submitted 2025-10-13; listed in the ICLR 2026 proceedings and by mlanthology as ICLR 2026, 31 authors; the OpenReview page was behind a bot check) states that all agent traces are on `https://huggingface.co/datasets/agent-evals/hal_traces`. That dataset is public and ungated (no login needed), has **no dataset card and no license statement**, and the HF tree API lists 381 files totalling ~113 GB: 66 corebench, 47 taubench (all `taubench_airline_*`), 45 swebench_verified_mini, 38 scicode, 37 gaia, 36 colbench, 34 assistantbench, 25 scienceagentbench, 19 browser-use, 18 seeact, 15 usaco. `taubench_airline` archives are 30–144 MB each; usaco 93 MB–3.5 GB; swebench_verified_mini 7 MB–1.6 GB. The harness repo `princeton-pli/hal-harness` is archived (GitHub API `archived: true`, last push 2026-07-01, no license field) and says the leaderboard is no longer updated through it.

**Encryption.** Every file is a zip containing one `<run>.json.encrypted` JSON with `salt` and `encrypted_data`. HAL's own public script `https://hal.cs.princeton.edu/static/downloads/hal-decrypt.sh` documents the scheme (PBKDF2-HMAC-SHA256, 480,000 iterations, Fernet) and embeds the passphrase; `hal/utils/json_encryption.py` in the harness matches. I re-implemented it in `work/empirical_sources/hal_decrypt.py` (passphrase read from `hal/_hal_passphrase.txt`, extracted from the published script) because the project venv lacks `cryptography`; a scratch `uv` venv was used for decryption only. The original script is kept as `hal/hal-decrypt.sh.orig`.

**Downloaded (6 taubench_airline runs, 304 MB, sha256 equal to the HF LFS oid for all six):**

| run_id | agent | HAL accuracy | HAL total_cost ($) | dedup-priced total ($) | harness errors |
|---|---|---:|---:|---:|---:|
| taubench_airline_hal_generalist_agent_gpt4120250414_1745167124 | HAL Generalist (gpt-4.1-2025-04-14), 2025-04-20 | 0.16 | 17.85 | 5.74 | 0 |
| taubench_airline_hal_generalist_agent_o4mini20250416_high_1745167079 | HAL Generalist (o4-mini high), 2025-04-20 | 0.18 | 20.57 | 8.66 | 0 |
| taubench_airline_hal_generalist_agent_claude37sonnet20250219_1746038671 | HAL Generalist (claude-3-7-sonnet), 2025-04-30 | 0.56 | 42.11 | 41.06 | 2 |
| taubench_airline_taubench_toolcalling_gpt4120250414_1760371184 | Taubench ToolCalling (gpt-4.1), 2025-10-13 | 0.36 | 8.18 | 3.69 | 0 |
| taubench_airline_taubench_toolcalling_claude37sonnet_1760379497 | Taubench ToolCalling (claude-3.7-sonnet), 2025-10-13 | 0.44 | 15.45 | 16.10 | 3 |
| taubench_airline_taubench_toolcalling_o4mini20250416_high_1760993011 | Taubench ToolCalling (o4-mini high), 2025-10-20 | 0.56 | 8.38 | 4.11 | 0 |

**Schema (verified on decrypted files).** Top level `config` (agent_name, benchmark_name, date, run_id, agent_args incl. `model_name`, `run_command`), `results` = `{accuracy, successful_tasks, failed_tasks, total_cost, latencies}` where `latencies[task_id] = {first_call_timestamp, last_call_timestamp, total_time}` is per task, `raw_eval_results[task_id] = {reward, taken_actions, ...}` (binary reward; a task can instead hold an `"ERROR: Traceback…"` string when the harness crashed, counted by HAL as failed), `raw_logging_results` = list of Weave call records (`id, parent_id, trace_id, op_name, started_at, ended_at, inputs, output, summary.usage[model]{prompt_tokens, completion_tokens, …}, summary.weave.latency_ms, weave_task_id`), `total_usage` (per model tokens), `total_cost`, `git_info` (harness commit). All six runs cover the same 50 task ids (`0`–`49`), one trial each; the HAL taubench implementation (`hal/benchmarks/taubench.py`) fixes `user_model: "gpt-4o"`, `user_strategy: "llm"`, 50 airline tasks.

**Per-task cost is not a HAL field.** HAL stores cost only at run level. I derived per-task cost by grouping Weave records by `weave_task_id` and pricing tokens with litellm's `model_prices_and_context_window.json` (main branch, fetched today). Two important observations:

1. `total_usage` (and therefore HAL's `total_cost`) equals the sum over **all** Weave records including nested parent/child duplicates: when a `litellm.completion` span wraps an `openai.chat.completions.create` span, both carry the same usage. For the three HAL-generalist runs and the o4-mini tool-calling run the leaf-only token count is exactly 50% of `total_usage` for the agent model (and 50% for the gpt-4o user simulator in all six runs). Pricing `total_usage` reproduces HAL's `total_cost` exactly for four runs (17.85, 20.57, 42.11, 8.18), so the leaderboard cost for those runs appears inflated ~2× relative to deduplicated leaf calls. Whether HAL corrects this on the website is UNVERIFIED; the observation is about the released files. The table `hal_taubench_airline_runs.csv` therefore has both `est_agent_cost`/`est_user_cost` (leaf-only, deduplicated) and `halstyle_agent_cost`/`halstyle_user_cost` (all records, sums to HAL's number).
2. For the two runs where prices do not reproduce HAL's number (Claude tool-calling 16.93 vs 15.45; o4-mini tool-calling 11.36 vs 8.38), HAL evidently used a different price table; the difference is not explained by the data.

Per-task table: `work/empirical_sources/hal_taubench_airline_runs.csv` (300 rows: `run_id, agent_name, agent_model, benchmark, task_id, reward, success, harness_error, error_text, n_taken_actions, latency_total_time_s, n_llm_calls, agent_prompt_tokens, agent_completion_tokens, agent_cached_tokens, user_prompt_tokens, user_completion_tokens, est_agent_cost, est_user_cost, unpriced_calls, models, halstyle_agent_cost, halstyle_user_cost, n_logging_entries`). Deduplicated mean agent cost per task: 0.108 (GPT-4.1 generalist), 0.164 (o4-mini generalist), 0.805 (Claude 3.7 generalist), 0.058 (GPT-4.1 tool-calling), 0.309 (Claude tool-calling), 0.070 (o4-mini tool-calling); latency is available for all 300 tasks.

**Caveats for use.** HAL airline is the 50-task tau-bench airline split with a `gpt-4o` user simulator and one trial (vs. tau2's `gpt-4.1` simulator, 4 trials, and its own reward code); do not merge HAL and tau2 outcomes as one benchmark. Two scaffolds × three models give a 2×3 factorial on the same 50 tasks, which is useful for the scaffold-vs-model contrast, but with one trial per task the reward is a single Bernoulli draw. The harness-error tasks (2 and 3 in the Claude runs) are failures by HAL's rule and should be kept as such, with a sensitivity analysis excluding them. usaco and swebench_verified_mini were not downloaded (multi-GB archives; usaco per-agent files are 0.1–3.5 GB), but the same decryption and per-task derivation applies.

## D. Running tau2-bench locally with cheap models (not executed)

**Installation.** Not on PyPI: `pip index`/PyPI JSON show `tau2` is an unrelated package (magnetic relaxation), and `tau2-bench`, `tau3`, `tau3-bench`, `hal-eval`, `hal-harness` return 404. The repository installs from source with `uv` (`pyproject.toml`: name `tau2` 1.0.1, `requires-python >=3.12,<3.14`, MIT, `litellm>=1.80.15,<1.82.7`):

```bash
git clone https://github.com/sierra-research/tau2-bench && cd tau2-bench
git checkout b7ea9074c1cba482b30687fecdb5c8425fd6f619   # or an earlier tag if the June-2025 task set is wanted
uv sync                      # core text domains: airline, retail, telecom, mock
cp .env.example .env         # add OPENAI_API_KEY / ANTHROPIC_API_KEY
uv run tau2 check-data
```

`uv` is present on this machine (`~/.local/bin/uv`); the project venv is Python 3.12 but has no `pip`, so use a separate `uv` environment.

**Defaults and flags (from `docs/cli-reference.md` and `src/tau2/config.py` at the pinned commit).** `--agent-llm`, `--user-llm`, `--agent-llm-args '{"temperature":0.0}'`, `--user-llm-args`, `--num-trials` (default 1), `--num-tasks`, `--max-steps` (200), `--max-concurrency` (3), `--seed` (300), `--save-to` (under `data/simulations/`). Defaults: agent and user simulator `gpt-4.1-2025-04-14` at temperature 0; NL-assertion grader `gpt-4.1-2025-04-14`; env-interface LLM `gpt-4.1-2025-04-14`. The released 2025 runs used exactly `--user-llm gpt-4.1-2025-04-14`; the current leaderboard guide instead "recommends `gpt-5.2` as the user simulator" and requires ≥4 trials per domain. Model names go straight to `litellm.completion(model=...)` and cost comes from `litellm.completion_cost`, so any litellm-registered name works, e.g. `--agent-llm claude-haiku-4-5-20251001` (or `anthropic/claude-haiku-4-5-20251001`), `--agent-llm gpt-4.1-nano-2025-04-14`, `--agent-llm gpt-4o-mini-2024-07-18` (litellm price table entries verified: haiku-4.5 $1/$5 per M in/out, gpt-4.1-nano $0.10/$0.40, gpt-4o-mini $0.15/$0.60, gpt-4.1-mini $0.40/$1.60, gpt-5-nano $0.05/$0.40, gpt-5-mini $0.25/$2.00). Note the pinned litellm range (<1.82.7) must contain these entries; the fetched table is from litellm main and is UNVERIFIED for that exact version. A cheap-run example:

```bash
uv run tau2 run --domain airline --agent-llm gpt-4.1-nano-2025-04-14 --user-llm gpt-4.1-2025-04-14 \
  --num-trials 4 --max-concurrency 4 --save-to nano_airline
uv run tau2 run --domain airline --agent-llm claude-haiku-4-5-20251001 --user-llm gpt-4.1-2025-04-14 \
  --num-trials 4 --max-concurrency 4 --save-to haiku45_airline
```

**Cost per airline task (estimate, not measured).** From the released data the user simulator (`gpt-4.1`) costs about $0.011–0.016 per airline run regardless of agent, and the GPT-4.1-mini agent about $0.0126 per run (implying roughly 25–28k input and 1–2k output tokens per run at $0.40/$1.60). Scaling those tokens by list prices: gpt-4.1-nano ≈ $0.003/run, gpt-4o-mini ≈ $0.005, gpt-5-nano ≈ $0.002, gpt-5-mini ≈ $0.009, claude-haiku-4-5 ≈ $0.03/run (agent only). Adding the simulator, a 50-task × 4-trial airline sweep is roughly $3 (nano) to $9 (haiku) per agent, plus the NL-assertion grader calls (gpt-4.1, small, only for tasks with NL assertions). Weaker agents produce longer conversations, so treat these as lower-end estimates; the released o4-mini/GPT-4.1 costs ($0.05/run) bound a stronger agent. Retail (114 tasks) is ~2.3× and telecom ~4–8× airline per the released per-run costs.

## Problems encountered and open items

- The earlier evidence document referred to local files and a `swe_lite_manifest.json` that did not exist in the workspace; everything was re-fetched and the single `manifest.json` now covers all three sources.
- HAL cost double counting (see C.1) means HAL leaderboard `total_cost` values should not be quoted as agent cost without the deduplication caveat.
- No license for SWE-bench `experiments` trajectories or for `agent-evals/hal_traces`; tau2 files are MIT with the Sierra notice retained.
- OpenReview blocked automated access; the ICLR 2026 venue for HAL rests on the proceedings.iclr.cc file listing and mlanthology.
- Not done: usaco/swebench_verified_mini HAL archives (size), AgentBoard archive, any new paid runs.

## Files created

- `evidence/data_acquisition.md` (this file)
- `work/empirical_sources/manifest.json`, `tau2_runs.csv`, `tau2_summary.csv`, `tau2_files_summary.csv`, `swe_lite_runs.csv`, `hal_taubench_airline_runs.csv`, `hal_taubench_airline_summary.csv`
- `work/empirical_sources/{download_tau2,download_swe,download_hal,hal_decrypt,build_tau2_runs,build_swe_runs,build_hal_runs,build_manifest}.py`, `README.md`
- Raw: `work/empirical_sources/tau2/` (26 JSON + LICENSE + figs/), `work/empirical_sources/swe_lite/<run>/{trajs/*.traj, results.json, metadata.yaml, README.md}`, `work/empirical_sources/hal/*_UPLOAD.{zip,json}`
