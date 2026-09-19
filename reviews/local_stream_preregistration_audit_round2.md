# Pre-registration audit, round 2: `experiments/local_stream/`

Auditor role: fresh, independent pre-registration auditor (did not write any of this
code). Re-audit from scratch of the nine items in
`reviews/local_stream_preregistration_audit.md` after the fixer applied all 8 must-fix
items plus coordinator decisions (a)-(i).

Date: 2026-09-18. Scope: `experiments/local_stream/` (13 files),
`results/local_stream/design.json` (frozen), `results/local_stream/dryrun/`,
`results/local_stream/timing_pilot/`, `protocol.md`. No git command, no paid API. All
reproducers run with `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`;
scratch output stayed in the session scratchpad; nothing in the primary results
directory was modified. `design.json` was NOT regenerated. The local server was
touched only with one non-task smoke completion ("Reply with the single word: pong");
no task from `work/local_stream/data/tasks.json` was sent to the model.

**Verdict: READY TO FREEZE.** Every finding of round 1 has been fixed and the fix
holds under independent re-execution. The one remaining action is not a harness defect:
the coordinator must commit the harness and fill `<FREEZE_COMMIT_ID>` in protocol
section 16 before the first design episode. That step is already documented and guarded
in the protocol and cannot be performed in this no-git sandbox.

| # | Item | Round 1 | Round 2 |
|---|---|---|---|
| 1 | Hidden-test leakage | FAIL (MBPP first assert shown & graded) | **PASS** (verified on all 591 tasks) |
| 2 | Verifier integrity | FAIL (early-exit / `__eq__` pass) | **PASS** (sentinel defeats all early exits; `__eq__` flagged & disclosed) |
| 3 | Sandbox containment | FAIL (6/8 classes escaped; `.env` readable; orphans) | **PASS** (8 original + 6 new classes contained; no orphans) |
| 4 | Design determinism / resume | PASS (minor gaps) | **PASS** (gaps closed: lock, `--only-pass 2` guard) |
| 5 | Metrics vs protocol | PASS (latency-scope remark) | **PASS** (latency excludes verify; `verify_seconds` separate) |
| 6 | Analysis estimands | PASS | **PASS** (E1/E2/strata/H4 12 rows) |
| 7 | Protocol completeness (#1/#2) | FAIL (H4, snapshot, manifest) | **PASS** (all three closed) |
| 8 | Reproducibility hashes | partial (model snapshot, git) | **PASS** for hashes; git commit id is a documented coordinator step |
| 9 | Timing-pilot disjointness | n/a | **PASS** (disjoint by id and prompt) |

Unit tests: `python -m unittest experiments/local_stream/tests_local_stream.py -v` =>
**27/27 OK, ~9.7 s**, no model call. Mock dry run + analysis reproduced (24 episodes,
MOCK banner, 12 sensitivity rows).

---

## 1. Hidden-test leakage — PASS

Exhaustive check over all tasks (not a sample), reconstructing every model prompt and
every graded program:

- MBPP (427): prompts containing `assert` = **0**; prompts containing any `test_list`
  or `challenge_test_list` entry verbatim = **0**; signature line present in every
  prompt = 427/427, all well-formed `^(async )?def \w+\(.*\):$`, and the signature
  names the entry point in every case. Every `test_list` assert is present in the graded
  program for all 427 tasks (0 ungraded).
- The 11 helper-first tasks (first `def` in the reference is a helper, e.g. `mbpp/6`
  `is_Power_Of_Two` before `differ_At_One_Bit_Pos`) are handled: `signature_line` emits
  the entry point's `def`, matching the function the hidden asserts call. This is decision
  (a) as refined by the fixer; it is stated in protocol section 5 and `agent.py`.
- HumanEval (164): prompts leaking `def check(` or the test string = **0**.
- `challenge_test_list` is empty for all 427 sanitized tasks (docstring "(+challenge)" is
  vacuous for this data; disclosed).

`tasks.json` is unchanged (`signature_example` retained but unused), so the design/task
hashes are preserved. The round-1 falsifiable protocol statement is now true.

## 2. Verifier integrity — PASS

`verify.py` appends a per-call nonce `print('__LS_VERIFY_OK__<16 hex>')` after all hidden
asserts; success = sandbox `passed` (rc 0, no timeout) AND raw `stdout_tail` ends with the
sentinel. Re-run on 50 tasks (25 MBPP + 25 HumanEval, seed 11):

| candidate | result |
|---|---|
| reference solution | 50/50 success |
| wrong (`return None`) | 0/50 success |
| wrong + `raise SystemExit(0)` | 50/50 **fail** (sentinel absent) |
| wrong + `os._exit(0)` | 50/50 **fail** |
| wrong + indented `sys.exit(0)` | 50/50 **fail** |
| wrong + guessed sentinel prefix, wrong nonce | 50/50 **fail** |
| universal `__eq__` object | passes 10/10, but `def __eq__` is in `hack_flags` |

The early-exit reward hack is closed. The universal-`__eq__` hack cannot be prevented by
execution alone (shared with every MBPP/HumanEval harness); it is recorded in `hack_flags`
and `hack_flagged_success` is reported per variant (protocol section 7). `verify_seconds`
is returned and recorded separately.

## 3. Sandbox containment — PASS

Seatbelt profile derived from `Path.home()`, the base interpreter prefix and `$TMPDIR`
(profile sha256 `6370c169...`, recorded per invocation). Interpreter is the venv base
(`/Users/.../uv/python/cpython-3.12.13-.../python3.12`), not the venv symlink, so
`sys.executable` does not point into the repository. I re-ran the 8 round-1 adversarial
classes AND 6 new ones of my own design:

| class | program | result |
|---|---|---|
| network | `_socket` alias `connect` | contained (PermissionError) |
| delete outside cwd | `os.remove(concat path)` | contained (PermissionError); victim intact |
| fork bomb | 20 `os.fork()` + sleep | timed out at 2 s, process group SIGKILLed, **no orphan** |
| infinite loop | `while True: pass` | timed out |
| huge memory | `bytearray(3<<30)` touched | allocates 3 GB (no mem cap on macOS; **disclosed** in section 9 + deviations) |
| shell exec | `os.popen('id')` | contained (BlockingIOError — fork refused) |
| read repo `.env` | via `sys.executable` walk | FileNotFoundError (no `.env` in repo) **and** a direct absolute read of a repo file is PermissionError |
| read `~/.zshrc` | `expanduser` | contained (PermissionError) |
| **NEW** read `~/.config` | `os.listdir` | contained (PermissionError) |
| **NEW** read venv site-packages / repo `config.json` | absolute paths | contained (PermissionError) |
| **NEW** `multiprocessing.Process` | spawn a worker | contained (BlockingIOError — fork refused) |
| **NEW** `ctypes.CDLL(None)` | load libc | libc loads, but Seatbelt still governs all syscalls (network/file/exec filtered by the kernel regardless of ctypes); no escape observed. Residual capability, same category as the disclosed no-mem-cap |
| **NEW** environment dump | `os.environ` | `{LC_CTYPE, PATH, PYTHONIOENCODING, __CF_USER_TEXT_ENCODING}` only — **no HOME, no secrets, no API key** |
| **NEW** time-bomb `time.sleep(30)` | | timed out at 2 s, group killed |
| **NEW** `importlib.import_module('os')` | | imports fine (stdlib); `os.getcwd()` only reveals the sandbox temp cwd — not an escape |

Direct verification that repo paths are denied even by absolute path (round-1's key leak):
`open('/Users/.../experiments/local_stream/config.json')` and
`open('/Users/.../reviews/local_stream_preregistration_audit.md')` both raise
PermissionError inside the sandbox, because the repository sits under `$HOME` and
`(deny file-read* (subpath $HOME))` covers it. There is no `.env` in the repo now, and
even if one were restored it would be unreadable from the sandbox.

Orphan check: the only `ps` line matching `ls_sbx`/`prog.py` after the fork test is the
auditor's own shell whose command line embeds the probe source text; no sandbox child
process survives the process-group kill (confirmed by watching at 0.2/1.0/2.0 s and by
`test_adversarial_programs_contained`). The static regex list is demoted to a recorded
flag (`static_flags`, `sandbox_flag`) and never decides success; protocol section 9 and
the deviations log describe Seatbelt + PATH-only env + process-group kill + RLIMIT_NPROC
as the guards, and disclose the no-memory-cap and `__eq__` residuals. RLIMIT_NPROC=64 on
a host already running >64 processes means any fork fails with EAGAIN — this contains
fork/popen/subprocess/multiprocessing but would also fail a legitimate multiprocessing
candidate; that outcome is counted equally for A and B and is stated in section 9.

## 4. Design determinism, pairing, resume — PASS

`design.py --print-sha-only` under `PYTHONHASHSEED` 0/7/12345 =>
`da84ff55...b8d4ad` each time = the content-only sha of the frozen `design.json`;
whole-file sha256 `6175b815...5457` = `design.sha256` = protocol section 16. 591 tasks,
295 pairs, 1 unpaired (`mbpp/256`, drew B). All 295 pairs pass the invariants: arrivals
`(2k-1, 2k)`, positions 1/2, `{A,B}` per pair, `pass1_variant==A <=> orientation==1`,
shared orientation, complementary pass-2 variant; 591 distinct tasks; 127 pairs R=1;
pass-1 exposure 295 A / 296 B; 181 same-benchmark pairs. Round-1 non-blocking gaps closed:
`--only-pass 2` refuses before pass 1 (`test_only_pass_2_requires_pass_1`), a run lock is
enforced (`test_run_lock`), resume is idempotent (`test_resume_skips_completed`).

## 5. Metrics vs protocol — PASS

`latency_s` in `agent.py` stops at the moment the final candidate exists (line 247),
before `verify()`; it includes the LLM calls and variant B's own self-test executions and
excludes hidden-test verification, which is recorded as `verify_seconds` (protocol section
8, `latency_scope` field on every record, deviations log). Tokens are the server's
`usage.completion_tokens`/`prompt_tokens` summed over every call, with an
estimated-fallback flag; source stated in protocol section 6.

## 6. Analysis estimands — PASS

E1 (`completed_pairs`) filters `pass==1` and keys on `(task_id, pass1_variant, trial)`;
pass-2 episodes cannot enter. E2 (`runs_by_task`) pools both passes per variant per task
(one A + one B per task, trial 2 disabled). Strata: per-benchmark and equal-weight
stratified reported. H4: `sensitivity()` emits 12 rows = tolerance {0,.1,.2} x 4 orders,
including the two resource-first orders `latency_s>success>completion_tokens` and
`completion_tokens>success>latency_s` with eligibility `none` (no absorbing mask); the
dry-run `sensitivity.csv` shows these rows preferring A while the frozen success-first rows
do not, which is the pre-specified H4 contrast. `test_no_absorbing_mask_scores` confirms
the no-mask rule prefers A when A failed but is faster.

## 7. Protocol completeness vs issues #1/#2 — PASS

- H4 now has a pre-specified test (12(e)/section 11(e); 12 sensitivity rows).
- Model snapshot: `hf_snapshot_record` locates the cached snapshot, records revision,
  refs/main, file list, sizes and per-file sha256, and refuses if revision
  `019cc73c...` is absent (`test_snapshot_and_model_checks`); the timing pilot exercised
  it for real (11 files, 4,295,890,004 bytes, ok=true). A pre-pass-1 smoke completion
  records the served model id and refuses a mismatch; every episode re-checks the served
  model and aborts before recording if it changes.
- Manifest is append-only (schema v2, `invocations[]`, no mutable top-level `config`);
  pre-audit-shaped manifests are refused; `complete_invocation` refuses to overwrite any
  field except `status` (`test_manifest_append_only`). Config drift is refused against the
  design hash and against any existing episode's hash (`test_config_drift_refused`).
- MOCK DATA banner present in the dry-run `report.md`.

## 8. Reproducibility hashes — PASS (git commit id is a coordinator step)

The dry-run manifest's `harness_file_sha256` matches the on-disk sha256 of all 13 harness
files, including `protocol.md`, verified byte-for-byte in this audit. Config
(`2dfb5196...`), design (whole-file and content), task-list (`23727895...`) and model-
snapshot hashes are all present and checked at run time. The one open item is
`harness_git_hash`: `.git/HEAD` currently resolves to `cb579f41...`, which does not
contain the uncommitted harness, so protocol section 16 carries `<FREEZE_COMMIT_ID>` as a
placeholder with an explicit guard ("no design task may be sent before this line is
filled"). This is a coordinator action (commit + fill), documented and gated; it is not a
harness defect and cannot be done in a no-git sandbox.

## 9. Timing-pilot disjointness — PASS

Pilot tasks `mbpp_full/{39,122,522,547,869,966}` from the full MBPP release: 0 task_id
collisions and 0 normalised-prompt collisions against the 591 frozen tasks (verified
directly, and `assert_disjoint` runs at pilot time + `test_pilot_tasks_disjoint`). The
pilot writes only to `results/local_stream/timing_pilot/` and never enters `analysis.py`.
Pilot outcomes are genuine (low absolute success is real model behaviour, e.g. the model
"corrects" the required name `rearange_string` -> NameError, and full-MBPP idiosyncratic
expected values), not harness errors. Projection: ~24.3 s/task, ~4.0 h for 1,182 episodes.

## Non-blocking notes

1. `results/local_stream/timing_pilot/summary.json` `harness_file_sha256` is now stale for
   `agent.py`, `analysis.py`, `tests_local_stream.py`, `protocol.md`, `README.md` (edited
   after the pilot ran). The fixer disclosed agent/analysis/protocol/README; `tests_local_stream.py`
   was also edited afterwards and is stale too. Cosmetic: the pilot never enters analysis,
   and the freeze manifest (dry run) carries the final hashes. Re-running the pilot would
   cost ~12 more model episodes and is not required.
2. `results/local_stream/tau2_local_feasibility.md` (a separate feasibility note, another
   party) is present and left untouched; it does not affect this experiment.
3. `stdout_tail` keeps the last 512 bytes of raw stdout for the sentinel check; a candidate
   that prints >512 bytes after the sentinel could push it out of the tail and fail a
   correct solution. In practice the sentinel is the last statement and nothing runs after
   it, so this cannot happen for honest code; noted only for completeness.
4. `harness_git_hash` in the dry-run manifest is `cb579f41...` (the branch HEAD), which
   predates the harness; this is the same placeholder situation as item 8 and is resolved
   when the coordinator commits.

## What was executed

- Full leakage sweep over all 591 tasks (asserts, hidden-test verbatim, signature, graded
  asserts, helper-first handling, HumanEval).
- `verify.py` on 50 tasks with reference / mutant / 4 early-exit variants / universal `__eq__`.
- 8 round-1 + 6 new adversarial programs through `sandbox.run_program`; orphan watch at
  0.2/1.0/2.0 s; direct absolute-path repo reads.
- `design.py --print-sha-only` x3 hashseeds; invariant sweep over `design.json`.
- `python -m unittest ... -v` (27/27); dry-run manifest hash comparison vs disk.
- Timing-pilot disjointness recomputation; pilot summary hash comparison.
- One non-task smoke completion to the live server (served model = configured model;
  stop token `<|im_end|>` present in content, which `extract_code` strips — deviations log).
