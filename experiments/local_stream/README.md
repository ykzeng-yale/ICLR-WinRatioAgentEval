# Local stream: small local-model replication and prospective randomized stream

Harness for GitHub issues #1 (larger prospective randomized agent stream) and #2
(small local-model replication) using one local open-weight code model, two
inexpensive coding-workflow variants, and 591 public verifiable tasks (MBPP
sanitized 427 + HumanEval 164). The frozen pre-registration is `protocol.md`.
Everything here runs on one machine with no paid API.

Layout

| file | role |
|---|---|
| `config.json` | frozen run configuration; its sha256 is stamped on every episode |
| `common.py` | paths, hashing, provenance (git hash read from `.git` files; no git command) |
| `data.py` | download + cache MBPP/HumanEval to `work/local_stream/data/` (git-ignored), manifest with URL/bytes/sha256, canonical task list + sha256 |
| `sandbox.py` | macOS Seatbelt (`sandbox-exec`: no network, no $HOME reads/writes except the interpreter prefix, writes only in the program's temp cwd, no exec of system binaries) + process-group kill on timeout + RLIMIT_CPU/RLIMIT_NPROC; base interpreter from `pyvenv.cfg`; static regex list recorded as flags only |
| `verify.py` | hidden-test verification (never shown to the model): all asserts + per-run nonce sentinel; success = exit 0 AND sentinel printed; `hack_flags`, `verify_seconds` |
| `agent.py` | variants A `single_shot` and B `self_test_repair`; OpenAI-compatible client; deterministic mock for dry runs |
| `design.py` | frozen design generator (seed 20260918): arrival permutation, disjoint pairs, per-pair orientation |
| `run_stream.py` | pass 1 then pass 2 in arrival order; guarded e-process monitoring after every pass-1 pair; idempotent resume; pre-flight refusals (config drift, snapshot revision, served model id, lock, `--only-pass 2` before pass 1); append-only manifest |
| `analysis.py` | online cross-arrival analysis, same-task shadow analysis, component effects, decision-rule table, sensitivity (incl. H4 resource-first rows), report skeleton (MOCK banner on dry runs) |
| `timing_pilot.py` | both variants on 6 full-MBPP tasks outside the design (disjoint by task_id and prompt); writes `results/local_stream/timing_pilot/` only; prints mean latency/tokens per variant for runtime projection |
| `tests_local_stream.py` | unit tests (stdlib unittest) |
| `protocol.md` | frozen pre-registration and requirement checklist |

## Commands

All commands from the repository root; `PY` is the project interpreter.

```bash
PY=/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python
cd /Users/yukangzengcmac/ICLR-WinRatioAgentEvals

# 0. Data (once; ~300 KB download; writes work/local_stream/data/{sanitized-mbpp.json,HumanEval.jsonl.gz,tasks.json,data_manifest.json})
$PY experiments/local_stream/data.py

# 1. Freeze the design BEFORE any model call (refuses to overwrite; already generated: results/local_stream/design.json)
$PY experiments/local_stream/design.py
cat results/local_stream/design.sha256

# 2. Unit tests (about 15 s; includes mock dry runs in temp dirs and the sandbox containment suite; no model call)
$PY -m unittest experiments/local_stream/tests_local_stream.py -v

# 3. Dry run with the deterministic mock model (never report these numbers)
$PY experiments/local_stream/run_stream.py --dry-run --limit 12 --results-dir results/local_stream/dryrun
$PY experiments/local_stream/analysis.py --results-dir results/local_stream/dryrun

# 4. Start the local model server (separate terminal; weights are cached by huggingface_hub under
#    ~/.cache/huggingface/hub, outside the repository). First start downloads ~4.3 GB.
$PY -m mlx_lm.server --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --port 8080
#    (mlx_lm 0.31 prints a deprecation note for this spelling; the equivalent non-deprecated form is
#     `$PY -m mlx_lm server --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --port 8080`)
curl -s http://127.0.0.1:8080/v1/models

# 4b. Timing pilot on 6 out-of-design tasks (downloads the full mbpp.jsonl, ~560 KB, into memory; ~12 episodes)
$PY experiments/local_stream/timing_pilot.py
cat results/local_stream/timing_pilot/summary.json

# 5. Full run (resumable: re-running the same command skips completed episodes; Ctrl-C is safe).
#    Pre-flight: refuses if config.json's hash differs from design.json or any recorded episode, if the cached
#    snapshot revision != model_revision_expected, if the served model id does not name the configured model,
#    if results/local_stream/run.lock is held by a live process, or if --only-pass 2 is requested before pass 1 is complete.
$PY experiments/local_stream/run_stream.py --results-dir results/local_stream
#    pass 1 only / pass 2 only:  --only-pass 1  /  --only-pass 2
#    optional trial 2 (both variants again; set "trial2_enabled": true in config.json first): --trial 2

# 6. Analysis (writes summary.json, decision_rules.csv, sensitivity.csv, task_scores.csv, episodes_flat.csv, report.md)
$PY experiments/local_stream/analysis.py --results-dir results/local_stream
```

Sampling parameters (temperature 0.7, top_p 0.95, max_tokens 1024) are sent
per request and override the server defaults (`mlx_lm.server` reads
`temperature`/`top_p`/`max_tokens`/`seed` from the request body and returns
`usage.prompt_tokens`/`usage.completion_tokens`). Per-call seeds are recorded
but Metal sampling is not guaranteed bit-reproducible; the frozen design, not
the sampler, carries the reproducibility claim.

## Outputs (results/local_stream/)

`design.json` + `design.sha256` (frozen before outcomes), `run_manifest.json`
(append-only: one record per invocation with config, hashes, model snapshot
revision/files/sha256, server `/v1/models` reply, smoke-completion model id,
sandbox profile + sha256, hardware, package versions, server RSS, summary),
`episodes.jsonl` (one record per enrolled episode including
failures), `monitor_pass1.csv` (e-values after every pass-1 pair),
`monitor_state.json` (first-crossing indices), then the analysis files above.
The `dryrun/` subdirectory holds mock-model output for pipeline testing only (its `report.md` carries a MOCK DATA banner); `timing_pilot/` holds the out-of-design timing pilot, which never enters the analysis.

## Resource estimates (to be replaced by measured values in the run manifest)

- Model snapshot: `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, revision `019cc73c45c770444708a6dd8690c66243cc5c80`, 4,295,890,004 bytes (11 files; `model.safetensors` 4.28 GB), license apache-2.0 (HF metadata). Cache location: `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-Coder-7B-Instruct-4bit`.
- Memory: about 4.5 GB weights + KV cache; expect 6-8 GB resident for the server on a 32 GB Apple M5 (this machine). Disk free at planning time: 280 GB.
- Throughput (planning assumption, not measured): 40-80 completion tokens/s for a 7B 4-bit model on Apple silicon; prompt processing several hundred tokens/s.
- Episode cost: A = 1 call, roughly 100-400 completion tokens (5-10 s); B = 2-4 calls plus 1-3 sandbox executions (about 15-45 s). Sandbox execution about 0.02-0.1 s per program when the tests are fast; timeouts cost up to 10 s each. Measured values: `results/local_stream/timing_pilot/summary.json` (`per_variant`, `projection`).
- Full run: 591 arrivals x 2 passes = 1,182 episodes; planning estimate 4-8 hours wall-clock, sequential, no concurrency. Trial 2 doubles this.
- Result size: about 5-10 MB for `episodes.jsonl` (final code and truncated tracebacks included); no model weights or caches enter the repository.
- Data cache: 300 KB under `work/local_stream/data/` (git-ignored).
