# Reproducing the EB1+EB5 subset suites

Written 2026-09-25 by session 60 for root's 22:08 and 01:10 requests
(`reviews/eb1_eb5_summary_repair_interim_20260924_2208.md`, main 76f5e71;
`reviews/eb1_eb5_v3_pin_interim_20260925_0110.md`, main bb093d7), and retargeted the same day for root's 10:10
request (`reviews/eb1_eb5_reproduction_path_interim_20260925_1010.md`, main `161966e`: state the final subset's
checkout head, receipt, expected counts and input requirements, so a reader does not reproduce only `c001354` and
the `…_0027` receipt by mistake).

**Current target.** Tag `session60-eb1-eb5-subset-v1` (peeled commit `c7750a3`, on branch `session60/repair-eb1`),
which root 22:20 (`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`, main `e37ed01`) accepted as the bounded model-free subset, or
its doc-only successor (the commit that adds this sentence, correcting section 2); both have the same harness bytes. Its harness bytes are the `98ce004` pin of receipt
`results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_2009.json` (commit `c12e19f`; section 8), which supersedes the
`…_0027` receipt below. Receipt R omits the delivery step's own runs before it was written; those are in the
write-once companion `results/live_ab/DELIVERY_STEP_RUNS_20260925_2014.json` (commit `eee9287`) instead — see
`results/SESSION60_RESULTS_INDEX.md`. The input requirements are exactly those of sections 2-6 below, unchanged by
the retarget.

**History kept below, labelled by commit.** Sections 1-6, 9-12 and most of section 7 describe runs R01-R23 (UTC,
listed in section 11) against the earlier checkout heads `9f0aff6` and `c001354`, pinned by the now-superseded
receipt `results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_0027.json` (`79e60d4`). Nothing in those sections changed:
the mechanisms, the untracked inputs, the interpreter and the host gate are the same at the current target, and the
runs remain what session 60 actually did. Section 8 is retargeted to R; a new run confirming the current head
against R is appended there. Every statement below is something session 60 ran (runs R01-R25, UTC, listed in
section 11) or read (file and line at `c001354` unless said otherwise; for `tests_eb1_entry.py`, at the commit that
adds this file). What was not verified is said where it matters and collected in section 12.

## 1. Why root's sparse run refused

Root ran the seven summary controls (`tests_invalid_decision_summary`) in a 31 MiB sparse
worktree at `9f0aff6` with Python 3.14. `setUpClass` died before any assertion; the program chain
held `preflight_refused` with `harness_file_sha`, `preflight_rule_failed` and drift on
`reused_file_sha256` and `sandbox_profile_sha256`.

Reproduced (R01, R02) in a fresh clone at `9f0aff6` with the sparse set
`/experiments/live_ab/ /experiments/live_ab_controls/ /src/` (root's exact pattern is not known
here; this one omits `experiments/local_stream/`). R01:

    ERROR: setUpClass (tests_invalid_decision_summary.SummaryPathControls)
      File ".../tests_invalid_decision_summary.py", line 234, in setUpClass
        look = crossing(refused)
    StopIteration
    Ran 0 tests in 0.141s
    FAILED (errors=1)

R02 read the program chain of the same run: `checks_failed = ["harness_file_sha",
"preflight_rule_failed"]`; drift `reused_file_sha256` expected `44136fa3...` found `0000...0000`,
`sandbox_profile_sha256` expected `64df95f2...` found `0000...0000`. `44136fa3...` is
`sha256_canonical({})` and `64df95f2...` is `sha256_text('mock-sandbox-profile')` (recomputed).

The mechanism, all tracked code:

- The mock freeze is built from the SAME checkout at test time. Its bundle pins the reused pilot
  files it can see (`experiments/live_ab/dryrun_live_ab.py:286`: `{}` when
  `experiments/local_stream/` is absent) and the sandbox profile it can observe, else a literal
  (`dryrun_live_ab.py:204-205`).
- Preflight recomputes both (`experiments/live_ab/lab_orchestrator.py:1713`, `:1762-1765`): with
  no pilot files the reused member is absent, and `sandbox.py` cannot be imported, so the profile
  is absent too (`experiments/live_ab/lab_data.py:205-232`).
- An absent member is drift (`experiments/live_ab/lab_common.py:809-811`), refused as
  `harness_file_sha` (reused) and `preflight_rule_failed` (profile, no specific code)
  (`lab_orchestrator.py:1516-1530`, `:1912`). The trial never starts, so `crossing()` finds no
  `monitor_update`.

The five files are TRACKED (`experiments/local_stream/{agent,sandbox,verify,data,common}.py`,
`lab_common.py:660`). Adding `/experiments/local_stream/` to the same sparse clone was enough:
R03 found no drift and a normal chain; R04 `Ran 7 tests in 78.177s OK`. A full clone without any
untracked data passed: R05 (`9f0aff6`) `Ran 7 tests in 79.114s OK`, R06 (`c001354`)
`Ran 7 tests in 79.475s OK`.

Python 3.14 was not tested (not installed here; uv has 3.12 and 3.13). The mock tree observes the
profile in the same process that preflights it, so an interpreter change alone does not create
this drift (read: `dryrun_live_ab.py:204`, `lab_orchestrator.py:1713`).

Side effect: a `setUpClass` failure skips `tearDownClass`, so R01 left its five mock trees
(`eb1b_*`) under `/private/tmp/labsbx`; they were removed by hand. With the hook of section 9 the
module fails in `setUpModule` before any tree exists (R23a left none).

## 2. Checkout

A FULL clone; not sparse, not shallow, not a tarball. **Current checkout:** the tag `session60-eb1-eb5-subset-v1`
(peeled commit `c7750a3721eda5ba1dcdb18df17065015d6db1e3`) or its doc-only successor on `session60/repair-eb1`; section 8
checks that the harness bytes equal receipt R's pin:

    git clone <repository> repo
    cd repo
    git checkout --detach session60-eb1-eb5-subset-v1
    git sparse-checkout list                 # prints nothing (else: git sparse-checkout disable)
    git rev-parse --is-shallow-repository    # prints false

A shallow clone passes with a silent skip: R07 (`git clone --depth 1`, c001354)
`Ran 7 tests in 75.767s OK (skipped=1)`, the skip being the negative control
`test_negative_control_the_7ebffad_builder_publishes_the_invalid_decision` ("git history is not
available", `tests_invalid_decision_summary.py:318`). That is not a reproduction. The controls
read four commits (`repro_inputs.HISTORY`): `7ebffad`, `159e747`, `b049307`, `988baf7`.

**Historical, not the current target:** runs R01-R23 below used
`git checkout --detach c0013548e9c0fbf02489065b856f11e3918e8b05` (`c001354`, pinned by the superseded `…_0027`
receipt). The command is kept as their record only (root 22:20 asked for this label).

## 3. Untracked inputs (`work/` is git-ignored)

Only the `live_ab` suite needs them. Without `work/`, the seven summary controls (R05, R06) and
the serving, tools and validation suites (R19) pass; tools then skips one test, as on the owner
host. The complete controls suite was run only with `work/` present (R15); no control module
reads these files (read: only `lab_data`, the pilot's `data.py` and `tests_local_stream` do).

| input | bytes | sha256 | read by |
|---|---|---|---|
| `work/local_stream/data/sanitized-mbpp.json` | 255053 | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` | `lab_data` (stratum S1) |
| `work/local_stream/data/HumanEval.jsonl.gz` | 44877 | `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef` | `lab_data` (stratum S1) |
| `mbpp.jsonl`, placed in `work/local_stream/data/` | 563743 | `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` | `lab_data` (stratum S2) |
| `work/local_stream/data/tasks.json` | 602791 | `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce` | `experiments/local_stream/tests_local_stream.py:27`, at import |

Obtaining them byte-exactly:

- The three sources are pinned by bytes and sha256 in `experiments/live_ab/lab_data.py:107-143`,
  with URLs at fixed revisions (google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533`,
  human-eval `463c980b59e818ace59f6f9803cd92c749ceae61`). No download was made in this step, so
  that those URLs serve these bytes is NOT verified here. Whatever the source, compare
  `shasum -a 256` with the table; `lab_data` refuses other bytes.
- On the owner host `mbpp.jsonl` is not under `work/`: `lab_data.CACHE_SEARCH_DIRS`
  (`lab_data.py:146-150`) also searches `/tmp/claude-501` and the TMPDIR of import time, and the
  owner copy is `/tmp/claude-501/mbpp.jsonl` (its sha256 checked). Elsewhere put it in
  `work/local_stream/data/`.
- `tasks.json` is derived and regenerates byte-exactly offline once the two S1 files are in
  place: `python experiments/local_stream/data.py` (`_download` returns a present file and fetches
  only an absent one, `experiments/local_stream/data.py:23-33`). R10 ran `prepare()` with
  `requests.get` replaced by a function that raises: `n_tasks 591 task_list_sha256 23727895...
  cached [True, True]`, and the file is `cmp`-identical to the owner copy. It also writes
  `data_manifest.json` (timestamps, absolute paths), which no suite reads (read; R11, R14, R15
  ran without it).

What each absence looks like (full clone at c001354, `-v` discover of `experiments/live_ab`):

- none of the four (R09): `Ran 678 tests in 207.034s FAILED (errors=28, skipped=1)`: 25 x
  `PreflightError: pinned source 'mbpp_sanitized' not found under <REPO>/work/local_stream/data`,
  2 x `offline=True and no cached copy of pinned source 'mbpp_sanitized'`, and
  `ImportError: Failed to import test module: tests_lab_serving` from
  `FileNotFoundError: run data.py first to build <CLONE>/work/local_stream/data/tasks.json`
  (the 89 tests that module brings, 73 own and 16 pilot tests it imports per the 0027 plan,
  become one error: 766 - 89 + 1 = 678).
- the two S1 files and `tasks.json` present, `mbpp.jsonl` only at `/tmp/claude-501` (R11):
  `Ran 766 tests in 224.230s OK (skipped=1)`; the skip is `pinned sources not present on this
  host` (`work/live_ab/sources/`), as in both receipts.
- `mbpp.jsonl` unreachable (R12: `tests_lab_design` with `CACHE_SEARCH_DIRS` restricted to the
  clone's `work/local_stream/data`, which simulates a host without the `/tmp` copy; no file was
  moved): `Ran 345 tests FAILED (failures=14, errors=2, skipped=1)`, e.g.
  `AssertionError: 'S1' != 'EXT'`: the roster silently drops stratum S2, which production treats
  as optional. With `mbpp.jsonl` copied into that directory (R13): `Ran 345 tests OK (skipped=1)`.

## 4. Interpreter, packages, platform

Owner host, read with the owner interpreter `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`:

- Python 3.12.13 (uv `cpython-3.12.13-macos-aarch64-none`, venv made by uv 0.11.17); numpy
  2.4.1, pandas 3.0.6, scipy 1.17.0, requests 2.34.2 (the full list:
  `importlib.metadata.distributions()` of that venv).
- Imported unconditionally by the suites: numpy (`lab_design`, `lab_verify_log`,
  `lab_reference_rule`, `build_live_ab_results`), pandas (`build_live_ab_results`), requests
  (`lab_client`, `lab_server`), scipy (`src/winstats.py`).
- macOS 26.5.2 (25F84), arm64 (10 CPUs per the 0027 receipt's host record). macOS is REQUIRED:
  off macOS or without `/usr/bin/sandbox-exec`, `sandbox_info()` returns no profile digest
  (`experiments/local_stream/sandbox.py:100-104`) and every mock-tree preflight refuses as in
  section 1 (read; `tests_repro_inputs.ProfileTests` simulates it; no other OS was run).
- The frozen `config.json` pins `sandbox.profile_sha256 = 527d267e...`, stated to resolve only
  under TMPDIR `<TMP>/labsbx` and cpython 3.12.13 (`experiments/live_ab/config.json:175`). On the
  owner host under `/private/tmp/labsbx` the observed profile is exactly `527d267e...` (R03). Mock
  trees pin whatever the host observes (`dryrun_live_ab.py:195-205`), so the suites do not need
  that value; a real freeze does.
- No other interpreter version was run.

## 5. The C test double (`live_ab_controls` only)

`sm_fixture.compiled()` (`experiments/live_ab_controls/sm_fixture.py:224-281`) compiles three C
string constants with `clang` into a cache under the TMPDIR of the call (`/private/tmp/labsbx` in
the suites) and uses a cache only when its compile-time manifest verifies (`cache_problems`,
`sm_fixture.py:174-201`). Owner toolchain: Apple clang version 21.0.0 (clang-2100.1.1.101),
target arm64-apple-darwin25.5.0, ld-1267, Xcode at `/Applications/Xcode.app`. R15 and R18 used
the verified cache 116 times, outputs launcher `1ec41938...`, core `85653080...`, base
`1da59ce4...` (the digests the 0027 receipt records). Consumers (0027 receipt):
`tests_eb1_entry`, `tests_eb1_server`, `tests_sm_entry`, `tests_sm_manifest`,
`tests_subset_review_fixes`, and five modules through them.

Without a compiler and without a verified cache the failure is visible: R20 ran `compiled()` with
an empty TMPDIR and a `PATH` holding only `ln`:
`RAISED FileNotFoundError: [Errno 2] No such file or directory: 'clang'` (the compile directory
was removed). The 0027 receipt's own missing-cache control `B_no_compiler` records the other form,
`sm_fixture: clang failed: ...`, for a `clang` that exits non-zero. A compile from scratch was
not run in this step (the receipts' `A_rebuild` control records one).

## 6. The host-quiescence gate

`lab_hostcheck.preflight_host_quiescent` (`experiments/live_ab/lab_hostcheck.py:1236-1254`)
refuses when it finds a foreign accelerator consumer (runner tokens `llama-server`, `llama-cli`,
`mlx-lm`, `ollama`, `vllm`, `lab_hostcheck.py:141-147`; a Python process holding a Metal
resource, or another process of at least 128 MiB RSS mapping a Metal compute library,
`lab_hostcheck.py:236-269`; the frozen baseline daemon `mediaanalysisd` when ACTIVE, i.e. more than
500 ms CPU in 10 s, label `baseline-active`) or when its scan is degraded (`ps`/`lsof` missing,
unparsed or timed out); its message names them. The entry controls run the real gate: a refusal
fails the control at once with `host_not_quiescent` and the offending detectors or degraded causes
(`tests_eb1_entry.host_refusal`, `tests_eb1_entry.py:550`); a degraded-only refusal is retried
twice (`DEGRADED_RETRIES`, `tests_eb1_entry.py:133`). The summary controls patch the gate out
(`tests_eb1_supervision.py:361`). Run one suite at a time: another suite's servers and workers are
foreign consumers to the entry controls (`tests_eb1_entry.py` module docstring).

Observed:

- R08 (07:10:28Z), the gate alone: `findings [] degraded []`, while two pytest process trees of
  another project were running (plain Python without Metal is not a consumer).
- R15 (the complete controls suite in the clone): 5 of 442 failed, all in `tests_eb1_entry`
  (C10, C1, C2b, C4, C4b, 07:35-07:45Z), each with
  `AssertionError: host_not_quiescent: the real host gate refused this control before seq 0
  (offending detectors: baseline-active; 1 host refusal(s) in the program chain) -- run it alone
  on a quiescent host`.
- R18 (08:17-08:23Z), `tests_eb1_entry` alone in the same clone: `Ran 32 tests in 386.373s OK`;
  a 10-second sampler of `mediaanalysisd`'s CPU time saw it rise by 0.01 s in the whole window.
- R08b (07:46:14Z), a gate probe run DURING R15, was refused naming a `llama-server` 45 s old:
  a mock server of the running suite (foreign to the probe, not to the suite). Probing while a
  suite runs proves nothing.

The pin tool's `solo` flag is a different, stricter process sampler; the 0027 receipt is
`solo=false`, which root 01:10 accepted as disclosed.

## 7. Commands, counts, wall times

From the repository root, with `PY` the Python 3.12 venv of section 4:

    $PY experiments/live_ab_controls/repro_inputs.py --suite all            # section 9
    $PY -m unittest discover -v -s experiments/live_ab -p 'tests_*.py'
    $PY -m unittest discover -v -s experiments/live_ab_controls -p 'tests_*.py'
    $PY -m unittest discover -v -s experiments/live_ab_serving -p 'tests_*.py'
    $PY -m unittest discover -v -s experiments/live_ab_tools -p 'tests_*.py'
    $PY experiments/live_ab_validation/tests_validation.py
    $PY -m unittest discover -v -s experiments/live_ab_controls -p tests_invalid_decision_summary.py

| suite | latest solo receipt `..._1732` (solo=true, 591ebcd) | receipt `..._0027` (solo=false, 79e60d4) | c001354 commit message | fresh full clone at c001354 | **receipt R** (`..._2009`, solo=false, 98ce004) |
|---|---|---|---|---|---|
| live_ab | 766 OK (skipped=1), 222.332 s | 766 OK (skipped=1), 227.248 s | 766 OK (skipped=1) | R11: 766 OK (skipped=1), 224.230 s | **766 OK (skipped=1), 222.976 s** |
| live_ab_controls | 393 OK, 2888.837 s | 426 OK, 2065.791 s | 442 OK, 3184.690 s (at 2113dbd) | R15: 442, FAILED (failures=5, the host gate, section 6), 3146.396 s; R18: the 32 of `tests_eb1_entry` OK, 386.373 s | **476 OK, 3540.075 s** |
| live_ab_serving | 193 OK, 2.136 s | 193 OK, 2.239 s | 193 OK | R14: 193 OK, 2.265 s | **193 OK, 2.145 s** |
| live_ab_tools | 137 OK (skipped=1), 66.760 s | 186 OK (skipped=1), 124.871 s | 187 OK (skipped=1) | R14: 187 OK, 122.574 s; R19 (no `work/`): 187 OK (skipped=1), 121.989 s | **239 OK (skipped=2), 166.319 s** |
| validation | 207 OK (skipped=6, expected failures=2), 12.833 s | 211 OK (skipped=6, expected failures=2), 12.260 s | 211 OK (skipped=6, expected failures=2) | R14: same, 12.288 s | **215 OK (skipped=6, expected failures=2), 14.429 s** |
| seven summary controls | - | - | - | R06: 7 OK, 79.475 s | (folded into the 476 of `live_ab_controls` above) |
| **total** | | | | | **1889 planned = completed, all 5 suites green** |

Counts grew with the subset (the 1732 receipt predates `7ebffad`, `9f0aff6`, `2113dbd`,
`c001354`); the commit that adds this file adds 16 controls (its message has their runs).

**Update 2026-09-25, the R step.** Receipt R's column above is one run of every suite at the clean, committed
`98ce004` (`results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_2009.json`, commit `c12e19f`); it is the **planned =
completed count a reproduction of the current target should expect**, superseding both the `..._0027` column and
the v4-step guidance below for anything at or after `98ce004`. Counts moved again since the v4 step: `86e6e27`
strengthens the SM8 precondition and its no-flip control (test-control file only), and `98ce004` fixes the pin
tool's own `DIFF_ARGV` (the delivery step's D1t run of `tests_harness_pin_successor.py` alone, with an uncommitted
predecessor of that fix applied, found 51 tests, OK skipped=1; see `results/SESSION60_RESULTS_INDEX.md` for the
delivery-step runs). `live_ab_tools`' skip count is now 2, not 1: the owner's `RealSourcesTests` skip is
still there ("the three pinned roster sources are not on this host"), plus a new one from the mutation-partition
test the pin tool's own suite added (`MUTATION_LOGS_8F0B4AE`, the verifier's log directory, an owner-session
environment variable this reproduction does not set). `live_ab_validation`'s 6 skips are still the unbuilt compiled
author reference.

**Update 2026-09-25, the v4 step (root 07:10, `reviews/predecision_abort_reporting_ruling_20260925_0710.md`).**
The counts in this table are observations at the receipts and commits each column names, not the
counts a reproduction of the delivered subset should expect: the v4 step added controls
(`tests_predecision_abort_reporting`, in `bdee21b`), the amendment-v4 witnesses
(`tests_repair_amendment_v4`) and validation pin tests (in the amendment-v4 commit), so the
`live_ab_controls`, `live_ab_tools` and validation counts moved. The expected count of each suite
is the planned = completed count the delivery pin receipt records (the write-once receipt that
supersedes `HARNESS_PIN_SUCCESSOR_20260925_0027.json`); compare with that receipt, not with this
table. Likewise section 8 recomputes the `0027` receipt at `c001354`: `bdee21b` moved
`build_live_ab_results.py`, so at a later head recompute the delivery receipt instead.
The owner's tools skip is `RealSourcesTests` ("the three pinned roster sources are not on this
host (set LIVE_AB_SOURCES_DIR)"); it looks in `LIVE_AB_SOURCES_DIR`, `work/local_stream/data` and
`work/live_ab/sources`, not in `/tmp`
(`experiments/live_ab_tools/tests_repair_amendment_v2.py:1781-1791`). With all three sources in
`work/local_stream/data` it runs and passed (R14). The six validation skips are the compiled
author reference not built on this host (both receipts, R14, R19).

`live_ab_tools` also reads the owner's durable llama.cpp build in the main checkout, at a
hard-coded path (`tests_repair_amendment_v2.py:89-90`, read-only `otool`/`nm`); on a host without
it those classes SKIP ("the durable build of the main checkout ... is not on this host"). No such
host was run, so the skip count there is not verified.

`live_ab` runs print a benign traceback, `KeyError: 'arm'` from `lab_worker.run_job`, inside
`tests_lab_isolation ... test_entry_accepts_the_canonical_spelling ... ok`: the test drives the
real worker entry past its lock check and ignores any later failure
(`experiments/live_ab/tests_lab_isolation.py:943-958`). It is not a failure.

## 8. Recomputing the pin receipt's hashes from git blobs

Needs only `git` and a stock `python3`; neither the pin tool nor harness code. The script is unchanged between the
current target and the history below: only `RECEIPT` changes.

### Current: retargeted to receipt R at the tag

From the root of a full clone at tag `session60-eb1-eb5-subset-v1` (`c7750a3`) or its doc-only successor:

    /usr/bin/python3 - <<'EOF'
    import hashlib, json, subprocess, sys
    RECEIPT = 'results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_2009.json'
    def git(*args):
        return subprocess.run(('git',) + args, capture_output=True, check=True).stdout
    def sha(data):
        return hashlib.sha256(data).hexdigest()
    def canonical(obj):  # lab_common.sha256_canonical, restated
        return sha(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                              allow_nan=False).encode('utf-8'))
    def blob(rev, path):
        return git('cat-file', 'blob', '%s:%s' % (rev, path))
    def harness_map(rev):  # lab_common.HARNESS_FILES: top-level experiments/live_ab/*.py + config.json
        paths = git('ls-tree', '--name-only', rev, 'experiments/live_ab/').decode().splitlines()
        names = [p.rsplit('/', 1)[1] for p in paths if p.endswith('.py') or p.endswith('/config.json')]
        return {n: sha(blob(rev, 'experiments/live_ab/' + n)) for n in names}
    raw = git('show', 'HEAD:' + RECEIPT)
    print('receipt sha256', sha(raw))
    r = json.loads(raw)
    ok = True
    for side in ('predecessor', 'successor'):
        pin = r['harness_pin'][side]
        got = harness_map(pin['rev'])
        same = got == pin['map'] and canonical(got) == pin['canonical_sha256']
        ok &= same
        print(side, pin['rev'][:7], len(got), 'entries, canonical', canonical(got), 'matches' if same else 'DIFFERS')
    head = harness_map('HEAD')
    same = head == r['harness_pin']['successor']['map']
    ok &= same
    print('HEAD', git('rev-parse', '--short', 'HEAD').decode().strip(), 'harness map equals the successor pin:', same)
    revs = {'b049307': r['repository']['predecessor'], 'head': r['repository']['head']}
    for label, doc in sorted(r['documents'].items()):
        for side, rev in revs.items():
            got = sha(blob(rev, doc['path']))
            ok &= got == doc[side]
            print('document', label, side, got[:12], 'matches' if got == doc[side] else 'DIFFERS')
    reused = r['reused_files']
    for side, rev in revs.items():
        got = {n: sha(blob(rev, reused['dir'] + '/' + n)) for n in reused[side]}
        ok &= got == reused[side]
        print('reused', side, 'matches' if got == reused[side] else 'DIFFERS', canonical(got)[:12])
    print('ALL MATCH' if ok else 'SOMETHING DIFFERS')
    sys.exit(0 if ok else 1)
    EOF

R24 output (`/usr/bin/python3` 3.9.6, run at `eee9287`, the head `c7750a3` was added to; `c7750a3` and its doc-only successor
touch no `experiments/live_ab/*.py` or `config.json` byte, so the tagged commit gives the identical harness map;
exit 0):

    receipt sha256 3745631750c3913f40069185971be8b3c2bd44e4538ab2fdc07cbdc7773da101
    predecessor b049307 33 entries, canonical 5675cc5ef970328834314480ec33d0edf237f38c1a3d977d3d22e93dc71f3fee matches
    successor 98ce004 34 entries, canonical f9a7703f5e868ea925a8a4aae11825ded22dee732761fa11db66b7f42b794c43 matches
    HEAD eee9287 harness map equals the successor pin: True
    document ARCHITECTURE_FINAL.md b049307 727003c1efe2 matches
    document ARCHITECTURE_FINAL.md head 4c762f2122c3 matches
    document cells.json b049307 5c4a28f76a06 matches
    document cells.json head 4796161929f4 matches
    document config.json b049307 e4d42f5d442d matches
    document config.json head f158969ecf02 matches
    document protocol_FINAL.md b049307 64ace6d3e377 matches
    document protocol_FINAL.md head c46718faedc1 matches
    reused b049307 matches 0c1760f33c19
    reused head matches 0c1760f33c19
    ALL MATCH

`HEAD ... equals the successor pin: True` shows that no harness byte has moved between `98ce004` (R's own head) and
the current worktree head `eee9287`, so this doc-only commit (and the tag it gets) writes no new pin receipt.
**The harness map at HEAD equals R's successor map**, as required.

Negative control R25, `RECEIPT` set back to the now-superseded
`results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_0027.json` (receipt sha256 `889c36c6...`): re-running the script
above with that swap reproduces that receipt's own pins (successor `79e60d4`, canonical `b0a45e31...`, both matching)
and prints `HEAD eee9287 harness map equals the successor pin: False` and `SOMETHING DIFFERS`, exit 1 — the harness
moved again (`bdee21b` through `98ce004`) after `…_0027` was written, so that superseded receipt no longer describes
the current head. This verdict is what this H step reconfirmed directly by re-running the full script above; the
session's own R25 log digest (`819d67e8d164368b`, section 11) was captured from a narrower prior check of the same
swap and does not reproduce byte-for-byte from the full script as printed here, unlike R24's digest, which does.

### History: at `c001354`, against the superseded `…_0027` receipt

Needs only `git` and a stock `python3` (R16 used `/usr/bin/python3` 3.9.6); neither the pin tool
nor harness code. From the root of a full clone at `c001354`:

    /usr/bin/python3 - <<'EOF'
    import hashlib, json, subprocess, sys
    RECEIPT = 'results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_0027.json'
    def git(*args):
        return subprocess.run(('git',) + args, capture_output=True, check=True).stdout
    def sha(data):
        return hashlib.sha256(data).hexdigest()
    def canonical(obj):  # lab_common.sha256_canonical, restated
        return sha(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                              allow_nan=False).encode('utf-8'))
    def blob(rev, path):
        return git('cat-file', 'blob', '%s:%s' % (rev, path))
    def harness_map(rev):  # lab_common.HARNESS_FILES: top-level experiments/live_ab/*.py + config.json
        paths = git('ls-tree', '--name-only', rev, 'experiments/live_ab/').decode().splitlines()
        names = [p.rsplit('/', 1)[1] for p in paths if p.endswith('.py') or p.endswith('/config.json')]
        return {n: sha(blob(rev, 'experiments/live_ab/' + n)) for n in names}
    raw = git('show', 'HEAD:' + RECEIPT)
    print('receipt sha256', sha(raw))
    r = json.loads(raw)
    ok = True
    for side in ('predecessor', 'successor'):
        pin = r['harness_pin'][side]
        got = harness_map(pin['rev'])
        same = got == pin['map'] and canonical(got) == pin['canonical_sha256']
        ok &= same
        print(side, pin['rev'][:7], len(got), 'entries, canonical', canonical(got), 'matches' if same else 'DIFFERS')
    head = harness_map('HEAD')
    same = head == r['harness_pin']['successor']['map']
    ok &= same
    print('HEAD', git('rev-parse', '--short', 'HEAD').decode().strip(), 'harness map equals the successor pin:', same)
    revs = {'b049307': r['repository']['predecessor'], 'head': r['repository']['head']}
    for label, doc in sorted(r['documents'].items()):
        for side, rev in revs.items():
            got = sha(blob(rev, doc['path']))
            ok &= got == doc[side]
            print('document', label, side, got[:12], 'matches' if got == doc[side] else 'DIFFERS')
    reused = r['reused_files']
    for side, rev in revs.items():
        got = {n: sha(blob(rev, reused['dir'] + '/' + n)) for n in reused[side]}
        ok &= got == reused[side]
        print('reused', side, 'matches' if got == reused[side] else 'DIFFERS', canonical(got)[:12])
    print('ALL MATCH' if ok else 'SOMETHING DIFFERS')
    sys.exit(0 if ok else 1)
    EOF

R16 output (exit 0):

    receipt sha256 889c36c6f7b419f39d20f292bef2186f30b5f745a1202ffd9fcced05151c9300
    predecessor b049307 33 entries, canonical 5675cc5ef970328834314480ec33d0edf237f38c1a3d977d3d22e93dc71f3fee matches
    successor 79e60d4 34 entries, canonical b0a45e3191e6f1bbddbfbcb1fee92620d9f5a641d3f5eecfe044eb4648bb11ee matches
    HEAD c001354 harness map equals the successor pin: True
    document ARCHITECTURE_FINAL.md b049307 727003c1efe2 matches
    document ARCHITECTURE_FINAL.md head 2ec71980de5b matches
    document cells.json b049307 5c4a28f76a06 matches
    document cells.json head 192804a4c153 matches
    document config.json b049307 e4d42f5d442d matches
    document config.json head f158969ecf02 matches
    document protocol_FINAL.md b049307 64ace6d3e377 matches
    document protocol_FINAL.md head 73dd0573955b matches
    reused b049307 matches 0c1760f33c19
    reused head matches 0c1760f33c19
    ALL MATCH

`HEAD ... equals the successor pin: True` shows that no harness byte moved after the receipt, so
the commit adding this file writes no new receipt. Negative control R17: the same script with
`RECEIPT` set to the superseded `results/live_ab/HARNESS_PIN_SUCCESSOR_20260924_1732.json`
(receipt sha256 `198eae6a...`) reproduces that receipt's own pins (successor `591ebcd`, canonical
`0f20e087...`), then prints `HEAD c001354 harness map equals the successor pin: False` and
`SOMETHING DIFFERS`, exit 1.

## 9. The named preflight (`repro_inputs.py`)

`experiments/live_ab_controls/repro_inputs.py` names every missing input of sections 1-5:
`reused_file_missing`, `sandbox_profile_unobservable`, `pinned_source_missing`,
`pinned_source_digest`, `pilot_tasks_missing`, `pilot_tasks_digest`, `git_history_missing`,
`c_compiler_missing`, each with its fix. `--suite` is `summary`, `live_ab_controls`, `live_ab`,
`mock_preflight` or `all`; `--repo` defaults to its own checkout; it exits 1 with the list when
anything is missing and prints the interpreter and package versions either way (R23b: a sparse
clone, 9 inputs named; the shallow clone, the 4 commits; the full clone, none).

- In the suite: `tests_eb1_entry.setUpModule` (`tests_eb1_entry.py:141-162`), shared by the
  summary module and seven other control modules, requires `mock_preflight` (the five reused files
  and an observable profile) and fails the module with `MissingReproductionInputs` naming them,
  the ambient TMPDIR restored. R23a, the summary module in a sparse clone of c001354 with this
  commit's three control files copied in:
  `ERROR: setUpModule (tests_invalid_decision_summary)` ...
  `MISSING REPRODUCTION INPUTS (6) for mock_preflight`, then `reused_file_missing
  experiments/local_stream/agent.py: tracked at the subset commit but absent here ... Fix: a FULL
  clone at the subset commit (git sparse-checkout disable).` for each of the five files and
  `sandbox_profile_unobservable`, `Ran 0 tests`.
- `tests_repro_inputs.py` holds its controls: the positive (this checkout), root's refusal
  reproduced through the production `orch.preflight` beside the two codes, and a refused negative
  control per code with its positive twin (R21: 16 OK). A kill matrix of 11 mutants of the helper
  and of the hook (each check disabled, the optional source skipped, a digest check reduced to
  existence, a HISTORY entry dropped, the hook removed, the hook not restoring TMPDIR) was killed
  11 of 11 (R22).
- Gaps left open: the `live_ab` suite is harness code (`experiments/live_ab/tests_*.py`) and
  cannot call the helper, so run `--suite live_ab` first; the helper does not predict the tools or
  validation skips; it refuses a host without `clang` even when a verified cache exists; it checks
  neither interpreter nor packages; with the owner's `/tmp/claude-501/mbpp.jsonl` present it does
  not name `mbpp.jsonl` for a checkout lacking it (R23b), exactly as `lab_data` would find it.

## 10. Environment-only refusals and how to recognise them

| symptom | cause | fix |
|---|---|---|
| `setUpClass ... StopIteration` in `crossing()`; program chain `preflight_refused(harness_file_sha, preflight_rule_failed)`, drift `reused_file_sha256` expected `44136fa3...` and `sandbox_profile_sha256` expected `64df95f2...`, found zeros. With the hook: `ERROR: setUpModule ... MissingReproductionInputs ... reused_file_missing experiments/local_stream/...` | `experiments/local_stream/` absent (sparse or partial checkout) | full clone |
| the `sandbox_profile_sha256` drift alone, or `sandbox_profile_unobservable` alone | not macOS, or no `/usr/bin/sandbox-exec` | macOS |
| `OK (skipped=1)` with "git history is not available" | shallow clone or tarball | full clone |
| `live_ab`: `Ran 678 ... errors=28`, `ImportError ... tests_lab_serving`, `pinned source 'mbpp_sanitized' not found` | untracked inputs absent | section 3 |
| `live_ab`: `'S1' != 'EXT'` and 13 more failures, 2 errors, in `tests_lab_design` | `mbpp.jsonl` not reachable | put it in `work/local_stream/data/` |
| `FileNotFoundError: ... 'clang'` or `sm_fixture: clang failed` | no compiler and no verified cache | Xcode command line tools |
| `host_not_quiescent ... offending detectors: baseline-active` | `mediaanalysisd` busy | wait, re-run the module alone (R18) |
| `host_not_quiescent` naming another detector, or `degraded scan` | a foreign accelerator job, or `ps`/`lsof` trouble | stop it; one suite at a time |
| tools: "the durable build of the main checkout ... is not on this host" | not the owner host | expected skip |
| `KeyError: 'arm'` traceback followed by `... ok` | benign stderr of a passing test | none |

## 11. The runs behind this file (session 60, 2026-09-25, owner host)

Clones made with `git clone --no-hardlinks` from the owner repository (read-only) outside it;
Python the owner venv unless said. No model, llama.cpp server, build or download; loopback mocks
and the C test double only. Logs kept by the session (first 16 hex of their sha256).

| run | UTC | what | result | log |
|---|---|---|---|---|
| R01 | 07:02:50 | sparse clone 9f0aff6 (no `local_stream`), summary module | `setUpClass` StopIteration, Ran 0, FAILED (errors=1) | `797506ef4d74b60c` |
| R02 | 07:03 | same clone, program chain of the `control` run | `preflight_refused`, the two drift rows | `26c5e1e481e37cfc` |
| R03 | 07:03 | same + `local_stream` | no drift, trial ended, profile `527d267e...` | `416c7c416053211d` |
| R04 | 07:03:54 | same, summary module | Ran 7 in 78.177s, OK | `28fa966376e2c1bd` |
| R05 | 07:05:32 | full clone 9f0aff6, no `work/`, summary module | Ran 7 in 79.114s, OK | `f2501b12a38a5cf2` |
| R06 | 07:06:58 | full clone c001354, no `work/`, summary module | Ran 7 in 79.475s, OK | `a323143a97a3469d` |
| R07 | 07:08:37 | shallow clone (`--depth 1`) c001354, summary module | Ran 7 in 75.767s, OK (skipped=1) | `a6e4c5ba599ab34f` |
| R08 | 07:10:28 | host gate alone | passed, findings [] degraded [] | `b1e187083dcde776` |
| R09 | 07:12:39 | full clone c001354, `live_ab`, no `work/` | Ran 678 in 207.034s, FAILED (errors=28, skipped=1) | `3a0f80724895aa8b` |
| R10 | 07:16 | `data.prepare()`, network call replaced by a raise | tasks.json 591 tasks, `23727895...`, identical | `5e55f5870d09d3c1` |
| R11 | 07:16:46 | `live_ab`, 2 S1 files + `tasks.json` | Ran 766 in 224.230s, OK (skipped=1) | `5d24f9cd78e0f973` |
| R12 | 07:20:45 | `tests_lab_design`, `mbpp.jsonl` unreachable | Ran 345, FAILED (failures=14, errors=2, skipped=1) | `87e514c3a4b5dc19` |
| R13 | 07:20:56 | same, `mbpp.jsonl` in `work/local_stream/data` | Ran 345, OK (skipped=1) | `513d9e304417f476` |
| R14 | 07:21:10 | tools / serving / validation, `work/` complete | 187 OK in 122.574s / 193 OK in 2.265s / 211 OK (skipped=6, expected failures=2) in 12.288s | `b371321aebd7fcca` `f3d5842049aea532` `8e6b747b6dc723f4` |
| R15 | 07:23:37-08:16:04 | `live_ab_controls`, complete | Ran 442 in 3146.396s, FAILED (failures=5: host gate, baseline-active) | `b9eef8cda325f305` |
| R08b | 07:46:14 | host gate probe during R15 | refused on R15's own mock `llama-server` | `f9c67c9a5fbc5f52` |
| R16 | 07:31:05 | pin recompute (section 8), `/usr/bin/python3` | ALL MATCH, exit 0 | `0544e38c7df1af06` |
| R17 | 07:31:13 | same against the 1732 receipt | SOMETHING DIFFERS, exit 1 (expected) | `1704a76e345f5766` |
| R18 | 08:17:08-08:23:35 | `tests_eb1_entry` alone | Ran 32 in 386.373s, OK; `mediaanalysisd` idle | `961a0924a42e5042` |
| R19 | 08:23:50 | serving / tools / validation, no `work/` | 193 OK in 2.277s / 187 OK (skipped=1) in 121.989s / 211 OK (skipped=6, expected failures=2) in 12.347s | `56311bcf82e6c97f` `c24aa68fd932eb99` `58893d0afd4ef0ee` |
| R20 | 08:26:14 | `sm_fixture.compiled()`, no `clang`, empty TMPDIR | FileNotFoundError 'clang' | `1bda59ad0504ce99` |
| R21 | 08:26:21 | `tests_repro_inputs` (dev) | Ran 16 in 0.321s, OK | `b700a03d161b1157` |
| R22 | 08:26:44 | kill matrix of `repro_inputs` and the hook | 11 of 11 killed | `e8cdc7bdb7032ce3` |
| R23a | 08:27:04 | sparse clone c001354 + the three new control files, summary module | `ERROR: setUpModule`, 6 inputs named, Ran 0 | `652b855012d0f05d` |
| R23b | 08:27 | `repro_inputs.py` CLI: sparse / shallow / full | exit 1 (9 named) / exit 1 (4 commits) / exit 0 | `9c1f72aaf668756e` |
| R24 | 20:19 | pin recompute (section 8) retargeted to receipt R, in this worktree at `eee9287`, `/usr/bin/python3` 3.9.6 | ALL MATCH, exit 0 | `18942dacb81ebae3` |
| R25 | 20:19 | same worktree, negative control against the superseded `…_0027` receipt | SOMETHING DIFFERS, exit 1 (expected) | `819d67e8d164368b` |

R24 and R25 are the H step's own runs (this doc-only commit), in the `session60/repair-eb1` worktree rather than a
fresh clone; both are read-only git-object recomputes, not suite runs, so a fresh-clone re-check was not required.

## 12. Not verified

- Root's exact sparse pattern, and any interpreter but 3.12.13 (3.14 in particular).
- That the pinned URLs serve the pinned bytes (no download was made).
- Any host but the owner's: non-macOS behaviour, the tools skip count without the owner's durable
  build, a host without `/tmp/claude-501/mbpp.jsonl` (simulated in R12 only).
- A compile of the C test double from scratch in this step.
- The complete controls suite passing in one uninterrupted run in the fresh clone: R15 had five
  host-gate refusals, and only their module was re-run (R18).
