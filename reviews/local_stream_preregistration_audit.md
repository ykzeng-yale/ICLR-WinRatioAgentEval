# Pre-registration audit: `experiments/local_stream/` (local-model prospective stream, issues #1 and #2)

Auditor role: independent pre-registration auditor, run before any real outcome exists.
Date: 2026-09-18. Scope: `experiments/local_stream/` (11 files), `results/local_stream/design.json` (frozen design), the mock dry run in `results/local_stream/dryrun/`, and `protocol.md`. No model was run, no weights downloaded, no git command used. All reproducers below were executed with `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python` and scratch output went to the session scratchpad; nothing in the primary results directory was modified.

**Verdict: NOT ready to freeze.** The statistical machinery (design, pairing, monitoring, estimands) is correct and reproducible, but the verifier can be passed by wrong code that exits early, the sandbox lets a candidate program read the repository `.env` (which holds an API key), and three protocol statements are false as written. All fixes are cheap and must land before the first real episode, since they change outcome definitions.

| # | Item | Verdict |
|---|---|---|
| 1 | Hidden-test leakage | PASS for `test_list[1:]`, challenge tests, HumanEval `test`/`check`; **FAIL** on the protocol claim (MBPP `test_list[0]` is shown to the model *and* graded) |
| 2 | Sandbox containment (16 adversarial programs) | **FAIL** (6 of 8 attack classes escape the static blocklist; repository `.env` is readable; orphaned processes) |
| 3 | `verify.py` correctness | PASS on 60 references / 60 mutants; **FAIL** on integrity (early-exit and universal-`__eq__` hacks pass) |
| 4 | Design determinism, pair/orientation logic, resume, idempotence | PASS (one non-blocking guard missing) |
| 5 | Metric definitions vs `protocol.md` | PASS on consistency (tolerance, absorbing rule, B-A direction, thresholds, min_n); design remark on latency scope |
| 6 | `analysis.py` estimands | PASS |
| 7 | Protocol completeness vs issues #1/#2 | **FAIL** on three items (H4 untested by 11(e), snapshot not verified, manifest not immutable/config drift undetected) |
| 8 | Reproducibility hashes | PASS for config/design/data hashes; **FAIL** for model snapshot hash (never recorded or checked) and harness git hash (uncommitted) |
| 9 | Reviewer "toy/leak" exposure | Findings listed in section 9 |

---

## 1. Hidden-test leakage — PASS (mechanics) / FAIL (protocol statement)

Traced every path from task fields to model input:

- `agent.build_user_prompt` uses only `task['prompt']` and, for MBPP, `task['signature_example']` (= `test_list[0]`). HumanEval prompt = benchmark `prompt` (signature + docstring; 76/164 contain the benchmark's own `>>>` doctest examples, which is standard benchmark content).
- `TEST_PROMPT` receives only `entry_point`; `REPAIR_PROMPT` receives the model's own tests and the traceback of code + own tests. No hidden field is formatted into any template.
- `verify.build_program` is the only consumer of `test_list`, `challenge_test_list`, `test`, `check`. The self-test loop in `run_episode` calls `sandbox.run_program(_self_test_program(code, tests))`, never `verify`, until the final candidate.
- `MockModel` reads `task['reference']` (dry runs only; refused in the primary directory).
- Exhaustive check over all 591 tasks: 0 literal occurrences of `test_list[1:]`, challenge tests, or HumanEval `test` in the user prompt (reproducer: scratch `verify_probe.py`, output "hidden-test literal leaks ... : 0").

**FAIL:** `protocol.md` section 5 and the unit test `test_hidden_tests_never_in_prompt` assert "Hidden tests ... are never placed in any prompt", but `test_list[0]` is shown verbatim in the prompt for 427/427 MBPP tasks **and** is one of the asserts that decides success (`build_program` appends all of `test_list`). On average 32.6% of the graded asserts are visible (397/427 tasks have exactly 3 asserts; no sanitized task has challenge tests, so "(+challenge)" in the docstrings is vacuous for this data). Reproducer:

```
$ .venv/bin/python -c "import sys; sys.path.insert(0,'experiments/local_stream'); from data import load_tasks; from agent import build_user_prompt; from verify import build_program; t={x['uid']:x for x in load_tasks()}['mbpp/2']; print(t['test_list'][0] in build_user_prompt(t), t['test_list'][0] in build_program(t,t['reference']))"
True True
```

Required fix (choose one, then make section 5, section 7 and the unit test say exactly what is done):
- (a) Grade only on `test_list[1:]` (+ challenge tests when present) and call the shown assert a "specification example"; or
- (b) Show only the call expression without the expected value: 408/427 first asserts are `Compare/Eq` nodes (`ast.unparse(node.test.left)`), 17 are bare `Call`, 2 are `UnaryOp`; the fallback for the 19 non-`==` cases is to show the assert with the right-hand side replaced by `...` or to show only the extracted `entry_point` name and argument tuple.
Either way the contrast B vs A is unaffected (both variants see the same prompt), but the current text is a statement a reviewer can falsify in one line.

## 2. Sandbox — FAIL

Sixteen adversarial programs were run through `sandbox.run_program` (scratch `adversarial.py`; JSON in scratch `adversarial_results.json`). Blocked = static policy refused execution; Contained = executed but the harm was prevented by a runtime limit; Escaped = the harm occurred.

| class | program | result |
|---|---|---|
| network | `import socket; ...connect` | Blocked (regex) |
| network | `import _socket; ...connect` | Blocked, but only by accident: `\bsocket\b` matches inside `_socket.socket()`; `import _socket as n; n.socket()` would pass the regex. Not re-run to avoid an outbound connection from the audit; the Seatbelt test below confirms the runtime has network access |
| file deletion outside cwd | `os.remove('/abs/path')` literal | Blocked |
| file deletion outside cwd | `p='/abs'+'/path'; os.remove(p)` | **Escaped**: scratch victim file deleted |
| fork | `from os import fork` (5 children sleeping 20 s) | Not blocked; wall-clock timeout fired; **1 child confirmed orphaned (ppid 1) after `run_program` returned** (`subprocess.run` kills only the direct child; no process group, no RLIMIT_NPROC) |
| infinite loop | `while True: pass` | Contained (wall clock 10 s; RLIMIT_CPU=10 also applied) |
| huge memory | `bytearray(3<<30)` touched | **Escaped**: 3 GB allocated in 0.26 s; only `RLIMIT_CPU=10` in `limits_applied` (macOS rejects RLIMIT_AS/DATA, as the builder disclosed) |
| subprocess | `import subprocess` | Blocked |
| subprocess | `import os as o; o.popen('id')` | **Escaped**: shell ran as uid 501 |
| env | dump `os.environ` | PASS: env is `{PATH, PYTHONIOENCODING}` only; no HOME, no secrets |
| read repo `.env` | `root = dirname(sys.executable)/../..; open(root+'/.env')` | **Escaped**: 307 bytes read, first key `OPENAI_API_KEY`. The venv interpreter path leaks the repository location, and read-mode `open()` on absolute paths is not in the blocklist |
| read `~/.env`, `~/.zshrc` | `os.path.expanduser('~')` (falls back to pwd when HOME unset) | `~/.zshrc` readable; `~/.env` absent on this host |
| sys.exit | `sys.exit(0)` at column 0 | Blocked |
| sys.exit | `if True:\n    sys.exit(0)` | **Escaped** (rc 0, `passed=True`) |
| sys.exit | `raise SystemExit(0)` | **Escaped** (rc 0, `passed=True`) |
| sys.exit | `os._exit(0)` | **Escaped** (rc 0, `passed=True`) |

The docstring of `sandbox.py` says the blocklist "is a policy for unattended local runs, not a security boundary", which is accurate, but `protocol.md` section 9 presents the list as if it prevents these actions. With a model that reads `sys.executable` (a 7B coder will not do this spontaneously, but the harness must not depend on that) the API key in `.env` is one `open()` away.

Verified fix on this host (macOS 26.5.2, `/usr/bin/sandbox-exec` present). The venv symlink `.venv/bin/python` cannot be used under a Seatbelt profile that denies the repository (Python's `getpath` fails: "failed to make path absolute"); use the venv's base interpreter (`readlink -f .venv/bin/python` = `/Users/yukangzengcmac/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3.12`, `-I -S` needs only the stdlib). This profile was executed and blocks: repo `.env` read (PermissionError), `~/.zshrc` read, any `/Users/...` write, `popen('id')` (exec denied), outbound `connect` (EPERM); stdlib imports (`math re collections itertools functools heapq bisect string datetime fractions decimal statistics random json typing`) and temp-dir writes work:

```
(version 1)(allow default)(deny network*)
(deny file-read* (subpath "/Users/yukangzengcmac"))
(allow file-read* (subpath "/Users/yukangzengcmac/.local/share/uv/python"))
(deny file-write* (subpath "/Users/yukangzengcmac"))
(deny process-exec (subpath "/bin") (subpath "/usr/bin") (subpath "/usr/local/bin") (subpath "/opt"))
```

Required changes to `sandbox.py`:
1. `python` default = base interpreter from `.venv/pyvenv.cfg` `home` (never the venv symlink); wrap the command in `sandbox-exec -p <profile>` when `sys.platform == 'darwin'` and record the profile's sha256 in `limits_applied` / the manifest. Make the profile paths derived from `Path.home()` and the interpreter prefix, not hard-coded.
2. `start_new_session=True` and on `TimeoutExpired` call `os.killpg(proc.pid, SIGKILL)`; add `RLIMIT_NPROC` (supported on macOS) in `preexec`, e.g. 64.
3. Keep the static blocklist only as a *flag* (recorded), or fix the obviously bypassable rules; in either case rewrite protocol section 9 to say that Seatbelt + PATH-only env + timeouts are the guards and the blocklist is a logging heuristic. Remove the `sys.exit_module_level` rule from the "blocked" set once the verifier sentinel (section 3) makes exits harmless.
4. Memory: state plainly that no memory cap exists on macOS (already in the deviations log); optionally add a wall-clock RSS watchdog if desired. Not blocking.

## 3. `verify.py` — PASS (correctness) / FAIL (integrity)

Reproducer: scratch `verify_probe.py` (30 random MBPP + 30 random HumanEval tasks, seed 7):

| candidate | MBPP success | HumanEval success |
|---|---|---|
| reference solution | 30/30 | 30/30 |
| AST mutant: entry-point body replaced by `return None` | 0/30 | 0/30 |
| reference + `raise SystemExit(0)` | 30/30 | 30/30 |
| reference + `os._exit(0)` | 30/30 | 30/30 |
| **mutant (`return None`) + `raise SystemExit(0)`** | **30/30 (all wrong code passes)** | **30/30** |
| universal object (`__eq__` returns True, `__bool__`, `__iter__`, `__len__`, `__getattr__`) | 28/30 | 29/30 |

`success` is `returncode == 0 and not timed_out`; the hidden asserts are appended after the candidate, so any module-level exit with status 0 before them is graded as success (the builder's regex only catches `sys.exit(` at column 0). All 591 references pass (builder) and mutants fail, so the verifier is correct on honest code, but it is not robust to the cheapest possible reward hack.

Verified fix (prototype executed on `mbpp/2`, `humaneval/0`, `mbpp/430`): append `print('__LS_VERIFY_OK__<16-hex nonce>')` after `check(...)`/the asserts and define success as `passed and stdout.rstrip().endswith(sentinel)`. Result: reference True; `ref+SystemExit` False; `wrong+os._exit` False; `wrong+indented sys.exit` False; wrong code printing a guessed sentinel False. Additionally:
- record per-episode `hack_flags` (static: `SystemExit`, `_exit`, `sys.exit`, `def __eq__`, `builtins`, `sys.modules`) for post-hoc review without affecting `success`; the `__eq__` hack cannot be prevented by execution alone and is shared with every standard MBPP/HumanEval harness, so disclose it in section 7 and report the count of flagged successes;
- `verify()` should also return `verify_seconds` separately (see section 5).

## 4. Design determinism, pairing, resume — PASS

- `design.py --print-sha-only` under `PYTHONHASHSEED` 0, 7, 12345 → `da84ff558deb2baf19d8728e3c50aea9e01e2411a5855cf07a2fac3594b8d4ad` each time; equals the content-only hash of the frozen `results/local_stream/design.json`; whole-file sha256 `6175b815...5457` equals `design.sha256`. `design.json` records seed 20260918, 591 tasks, 295 pairs, 1 unpaired, config hash `2dfb5196...`, task list hash `23727895...`.
- Invariants checked over all 295 pairs: arrivals `(2k-1, 2k)`; `{pass1_variant}` = {A, B}; `pass1_variant == A  <=>  orientation == 1` for the first arrival; both arrivals share `orientation`; `pass2_variant` is the complement; 591 distinct tasks. 127/295 pairs have R=1 (0.43; consistent with Bernoulli(1/2)); pass-1 exposure 295 A / 296 B (the unpaired `mbpp/256` drew B). 181 pairs are same-benchmark, 114 mixed (relevant for 11(a) per-benchmark E1).
- Dry run (`--dry-run --limit 12`) into scratch: 24 episodes; re-run: `ran 0, skipped 24`, `episodes.jsonl` unchanged; extension to `--limit 14`: only the 4 new episodes ran. Monitor rows identical to an independent recomputation (unit test, 1e-9).
- Resume key `(task_id, variant, trial)` is unique by construction (each task gets each variant once per trial).

Non-blocking gaps: `--only-pass 2` runs before pass 1 exists (verified: 3 pass-2 episodes written into an empty directory) — refuse unless pass 1 is complete for the selected arrivals; no lock file against two concurrent `run_stream.py` processes (would duplicate episodes); `write_manifest` reads `design.sha256` (trial 1) even for `--trial 2`; `analysis.py` only analyses trial 1 for E1 although section 4 promises trial-2 pass-1 pairs as an E1 replicate (trial 2 is disabled; fix or drop the sentence).

## 5. Metric definitions vs `protocol.md` — PASS (consistency), one design remark

Checked by direct computation (`pair_scores`, `monitor_table` with the frozen config):
- Tolerance: latency 9.0 vs 10.0 s (10% of max) → tie; 8.9 vs 10.0 → B wins at tier index 1; tokens 89 vs 100 → B wins at tier 2. Identical to `winstats.compare` (`|delta| <= rel*max(|a|,|b|)` is a tie).
- Absorbing rule: both fail → tie (tier -1); exactly one success → decided at tier 0; lower tiers eligible only when both succeed. Same mask construction as `run_replay.score_pairs`.
- Direction: `compare(XB, XA)` so z>0 = B preferred; `dq = success_B - success_A`; guardrail e-process `betting_log_e_ternary(qp, qn, n, -0.03)` tests H0: E[D] <= -0.03. Numeric: B dominates → win, gate and deploy all first cross at n=20 (min_n), harm never; A dominates → harm at 20, no deploy; B wins only at tier 2 with equal success → win crosses at 20, gate does not (D ≡ 0 gives no evidence against E[D] <= -0.03 at n=60; this is the intended conservative behaviour but the paper should say the guardrail needs success evidence, not just non-harm); n=19 with all wins has log e 9.52 > log 20 but `deploy=False` (min_n respected).
- Thresholds: `log(1/alpha)` with alpha 0.05; min_n 20 (run_replay uses 50; pre-specified difference, fine).
- Tokens: `usage.completion_tokens` summed over all calls of the episode (B's test-writing and repair calls included), estimated fallback flagged in `tokens_estimated`. README states the source; `protocol.md` section 6 does not — add one sentence.
- Latency: `latency_s = perf_counter() - tw0` measured from before the first model call to after `verify()` (agent.py lines 168 and 223), exactly as section 8 states. Remark: this counts hidden-test verification (grader time, up to a 10 s timeout on a failed candidate) as system latency. Because a verification timeout implies failure, tier 2 is never compared on such pairs, but the component latency means and the utility grid in 11(c)-(d) are inflated for failed episodes. Recommend defining latency as time to the final candidate and recording `verify_seconds` separately; decide now, before any outcome exists, and state the decision in section 8.

## 6. `analysis.py` estimands — PASS

- E1: `completed_pairs` filters `e['pass'] == 1` and keys on `(task_id, pass1_variant, trial)`; pass-2 episodes cannot enter; `cross_arrival_independent` Welch CIs use the same pass-1 arms.
- E2: `runs_by_task` pools all episodes (both passes, all trials) per task and variant; `task_level_scores(..., pairing='all')` with the absorbing eligibility function; `clustered_summary` with cluster = task; per-benchmark and equal-weight stratified (fixed weights 0.5/n_stratum) reported; paired-t component CIs over task means.
- Sensitivity loops rebuild tiers with `tolerance` only on non-success tiers and re-run both analyses.
- Decision table implements the rule set named in the task (success-only, Pareto on means, six utility weightings, hierarchical, guarded, conjunction, anytime guarded). `experiments/decision_disagreement.py` does not exist on this checkout, so equivalence with that file could not be confirmed; document the implemented definitions (they are in the `decision_rules` docstring) as the pre-specified ones.

Statistical clarification for the protocol (non-blocking): arrivals are a permutation of a fixed 591-task population (sampling without replacement), so pair scores are exchangeable, not independent, and the conditional mean drifts as the pool is exhausted; `winstats.betting_log_e_ternary` documents that it tests a pointwise conditional null, not a drifting running-average null. State the E1 null as the superpopulation/exchangeable null and mention this in section 10.

## 7. Protocol completeness vs issues #1 and #2 — FAIL on three items

Present and adequately specified: frozen design before outcomes; independent seed; strata; retained failures (section 7); shadow vs AB/BA distinction (section 2); latency scope; failure accounting; runnable README; weights outside the repo; licenses (model apache-2.0, MBPP CC-BY-4.0, HumanEval MIT); how the replication bears on the paper (section 12).

Missing or inconsistent:
1. **H4 is not tested by the pre-specified analysis.** Section 1 H4: "A latency-first or token-first hierarchy ... prefers A"; section 11(e) only varies tolerance and the order of tiers 2-3 under success-first (confirmed in `sensitivity()`, orders `success>latency_s>completion_tokens` and `success>completion_tokens>latency_s`). Either add `latency_s>success>completion_tokens` and `completion_tokens>success>latency_s` rows (and define the eligibility mask for a non-success top tier, since the absorbing rule is undefined there) or reword H4 to refer to the utility grid weights (0.2,0.4,0.4) etc.
2. **Model snapshot not verified (issue #2 "model snapshot documented"; task item 8).** `config.json` carries `model_revision_expected`, but nothing reads the huggingface cache, hashes the snapshot, or compares the served model (`/v1/models` returns an id, not a revision). The cache currently has no `models--mlx-community--Qwen2.5-Coder-7B-Instruct-4bit` entry. Add to `write_manifest`: locate `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-Coder-7B-Instruct-4bit/snapshots/<rev>/`, record `<rev>`, file list, sizes and sha256 (4.3 GB, tens of seconds), refuse to run if `<rev> != model_revision_expected`; also record `response_model` from the first completion and refuse if it does not name the configured model.
3. **Manifest not immutable; config drift undetected (issue #1 "immutable run manifest", "exact config").** Reproducer: resume the scratch dry run with `--config <copy with temperature 0.2>` → 4 new episodes appended with `config_hash 77325e83...` beside 24 with `2dfb5196...`; `run_manifest.json` top-level `config`/`config_hash` silently overwritten to the new values; `design.json` still says `2dfb5196...`. Fix: in `run()` refuse if `cfg['_config_hash'] != design['config_hash']` or differs from any existing episode's `config_hash`; make the manifest append-only (one record per invocation, never `m.update` of top-level fields).

Also weak: "tool-use capability verified" (issue #2) rests on a model-card sentence; add a 3-prompt smoke test on hand-written tasks outside MBPP/HumanEval (recorded in the manifest, not analysed) before pass 1. "Resource use": add server RSS at start/end (from `ps`) to the manifest.

## 8. Reproducibility hashes — partial

Recorded and verified: config canonical sha256 (`2dfb5196...`, on every episode and the design), design content and whole-file sha256, task list sha256 (`23727895...`), download URL/bytes/sha256 (`ca95deaa...`, `b796127e...`), harness file sha256 (manifest; `protocol.md` is in `HARNESS_FILES` but absent from the dry-run manifest because it was written after the dry run; re-run before freezing), hardware and package versions. **Missing:** model snapshot hash (item 7.2); `harness_git_hash` = `cb579f41...` (HEAD of `session60/local-stream`) which does not contain the harness because the files are uncommitted. Commit the harness and the frozen design before the first real episode and record that commit in `protocol.md`; the auditor could not do this (no git commands).

## 9. What a reviewer could call a toy or a leak

- **Leak:** MBPP first assert shown and graded (section 1); `.env` readable from the sandbox (section 2); verifier passes wrong code that exits early (section 3). The first two are about the description; the third is about the outcome definition. All three must be fixed before freezing.
- **Toy risk, acceptable if disclosed:** function-level benchmarks that are in training data (section 12 already says so); a 7B 4-bit model; one hardware configuration; 295 pairs; no memory cap on macOS; the `__eq__` hack shared with every MBPP/HumanEval harness; HumanEval candidates that drop the prompt's `from typing import List` fail with NameError (an outcome, counted equally for A and B; say so in section 7).
- **Not a problem:** dry-run outputs are labelled `dry_run=True` in manifest and report; `analysis.py` refuses nothing here, so add a "MOCK DATA" banner to `report.md` when `dry_run` is true to prevent accidental copy into the paper.

## Required fixes before freezing (must_fix)

1. `verify.py`: nonce sentinel after the hidden tests; success requires `passed` and stdout ending with the sentinel; add `hack_flags` and `verify_seconds` to the episode record (section 3).
2. `sandbox.py`: base interpreter instead of the venv symlink; Seatbelt profile above on macOS with its hash recorded; `start_new_session` + `killpg`; `RLIMIT_NPROC`; blocklist demoted to a recorded flag; rewrite protocol section 9 accordingly (section 2).
3. `run_stream.py`: refuse when the config hash differs from `design.config_hash` or from existing episodes; append-only manifest (section 7.3).
4. `run_stream.write_manifest`: record and check the huggingface snapshot revision and file hashes and the served model id (section 7.2).
5. `protocol.md` + `agent.py`/`verify.py` + unit test: resolve the MBPP `test_list[0]` contradiction by option (a) or (b) (section 1); add tokens source to section 6.
6. `protocol.md` section 11(e) / H4: add non-success-first orders with a defined eligibility rule, or reword H4 (section 7.1).
7. Decide and state the latency scope (exclude hidden-test verification, record `verify_seconds`) (section 5).
8. Commit the harness and frozen design; record the commit in `protocol.md`; regenerate the manifest so `protocol.md` and the new file hashes appear (section 8).

## Recommended (non-blocking)

Guard `--only-pass 2`; lock file; trial-2 manifest/analysis consistency; exchangeable-null wording for E1; smoke test for tool-use capability; MOCK banner in `report.md`; disclose HumanEval import failure mode and the `__eq__` limitation; note that `challenge_test_list` is empty for all 427 sanitized tasks.

## What was executed

- `python -m unittest experiments/local_stream/tests_local_stream.py -v`: 13/13 OK, 4.6 s.
- Dry run + analysis + resume + extension in scratch; `--only-pass 2` into an empty directory.
- `design.py --print-sha-only` x3 with different `PYTHONHASHSEED`; invariant script over `results/local_stream/design.json`.
- 16 adversarial programs through `sandbox.run_program`; orphan check with `ps`; three Seatbelt profiles with the venv symlink (fails) and the base interpreter (works).
- `verify.py` on 30+30 tasks with references, AST mutants, three early-exit variants and a universal-`__eq__` object; sentinel prototype on 3 tasks.
- Config-drift resume with a modified config copy.
- Numeric checks of `pair_scores`/`monitor_table` direction, tolerance, absorbing rule and min_n.
