# ARCHITECTURE_FINAL.md — implementation specification for `experiments/live_ab/`

Session 60 software architect, 2026-09-19, **FINAL** (supersedes `ARCHITECTURE.md`). Target: five engineers
(G1..G5) implement disjoint module groups in parallel, without talking to each other. **This document is the
interface contract for everything the protocol does not fix.**
Anything not written here is a defect, not a choice: if an implementer finds a gap, the gap is listed in
section 11 (`PROTOCOL-GAP`) with its resolution, and everything else must be raised with the
coordinator rather than invented. **Every `PROTOCOL-GAP` in section 11 is now resolved, the resolution is a
concrete rule, and that rule also appears in `protocol_FINAL.md`; none is left "coordinator".**

**Subordination, stated once and binding.** `protocol_FINAL.md` **sections 6.2, 6.3, 6.4, 7 and 8 are the rule
block; where this document differs from them, this document is defective** and the protocol governs. The freeze
test `lab_common.rule_block_sha256(config)` == the rule-block hash computed from the protocol's own tables makes
a disagreement impossible to freeze (protocol Appendix C).

Binding inputs, in precedence order:

1. `reviews/arxiv_live_design_guidance.md` (root guidance; the decision rule, the alpha table, the
   enclosure rule, the switch semantics, the A/A status, the freeze deliverable).
2. `<scratch>/live_ab_design/COORDINATOR_DECISIONS.md`, **REVISION 2** (adopts the guidance; supersedes
   revision 1 where they differ; keeps pair-synchronous execution, `delta = 0.03`, `n_min = 100`,
   horizon = full roster, no betting driver).
3. `<scratch>/live_ab_design/protocol_FINAL.md` — the whole of it, machinery included (execution, failure
   rules, event chain, freeze/resume, Appendix C). **`protocol_draft_v2.md` and `protocol_v3.md` have no
   residual force and must not be cited by any module, test, docstring or report.** Every section number in
   this document refers to `protocol_FINAL.md`.
4. `<scratch>/live_ab_design/critic_v2.md` (N1-N22), `audit_v3.md` (B1-B7, M1-M20, m1-m11) and
   `R3_harness_plan.md` (module map, llama-server facts, failure table).

Read-only references that this code may import or hash but never edit: `src/winstats.py`,
`experiments/local_stream/{agent,sandbox,verify,data,common}.py`, `paper/`, `reviews/`,
`EXPERIMENT_QUEUE.md`.

---

## 0. The program in one page (what the code has to do)

Four trials in the fixed order **T4, T2, T1, T3**. A trial is a sequence of **enrolled pairs**. Pair `i`
occupies arrivals `2i-1` and `2i` of a frozen arrival order; one fresh OS-entropy coin `R_i` orients the
pair (`R_i = 1`: candidate at position 1, incumbent at position 2; `R_i = 0`: reversed). Both episodes of
pair `i` run concurrently as two subprocesses; pair `i+1` is enrolled only after both episodes of pair `i`
are revealed. At most one pair is pending, ever.

A **look** is taken at the current full enrolled prefix `n = N(t)` (number of pairs enrolled so far, including
a pair whose episodes are still running) at exactly the evaluation triggers of protocol 8.3, and at no other
event: every `pair_enrolled`; every `episode_revealed` of the randomized phase; every ingested `llm_request`,
`llm_response` or `llm_error` that **raises the certified elapsed `ell`** of a still-pending episode of an
enrolled pair; and once per resume. A `metrics_scrape` is **never** a trigger. A drain reveal after a decision
writes a `monitor_update` with `trigger='drain'` and calls no decision function. For each
monitored score `j` in `{h (hierarchy), s (success difference)}`:

```python
r    = winstats.normal_mixture_radius(n, alpha=alpha_gate, rho=100., variance_process=n)
L_j  = max(-1.0, sum(lower_j[:n]) / n - r)
U_j  = min( 1.0, sum(upper_j[:n]) / n + r)
```

with `alpha_gate = 0.00625` (program 0.05 / 4 trials / 2 scores per trial), `rho = 100.0`,
`delta = 0.03`, `n_min = 100`. Decision at a look, evaluated in this order:

| order | name | condition | action |
|---|---|---|---|
| 1 | `harm_keep_incumbent` | `n >= n_min` and `U_h < 0` | stop randomizing; route the rest to the incumbent |
| 2 | `deploy_candidate` | `n >= n_min` and `L_h > 0` and `L_s > -delta` | stop randomizing; route the rest to the candidate |
| 3 | — | otherwise | continue; at `n = N_P`: `horizon_no_decision` |

No prefix envelope, no maximization over prefixes, no retained crossing, no running intersection, no
betting statistic anywhere in the decision path.

**Computed before any data (this is not a defect, it is the study):** with these constants,
`r(92) = 0.495026`, `r(100) = 0.465693`, `r(295) = 0.228707`, `r(568) = 0.157952`. These are **conditional
threshold calculations**: at a *hypothetical constant* observed value equal to the pilot's (hierarchy net
benefit about ±0.497, success difference about 0) the hierarchy gates could cross from `n >= 92` and
therefore, under `n_min = 100`, at the first admissible look, while the success guardrail at `delta = 0.03`
would need `n >= 17,097` against a roster of at most **568** pairs (protocol 3.3: pairs are formed inside a
stratum, `N_P = floor(n_S1/2) + floor(n_S2/2)`; 569 is the unstratified count and is **not** a horizon of
this program). **A DEPLOY decision therefore requires an observed running success difference above
`r(N_P) - 0.03`, which is `+0.1279515` at `n = 568`; if the observed difference stays at zero the gate cannot
pass within this horizon. This is a condition on the DATA, not a fixed sample-size requirement: no outcome is
excluded by arithmetic, and at `n = 100` with every resolved pair favouring the candidate both lower
endpoints are `1 - r(100) = 0.534307` and both gates pass. No probability of deployment or abstention is
claimed, and the pilot's same-task paired standard error does not describe this trial's one-task-per-arm
pairs and is never used as a rationale. The words "unreachable by construction", "guaranteed abstention" and
"near-certain abstention" must not appear in any output, test name or comment.** The
horizon, the margin and the rule are never changed to make it more reachable. The code must be correct on the
abstention and harm paths first; the deploy path is exercised by mock dry runs with a mock-only wide margin,
and `test_deploy_threshold_at_scale` (9.2 G3) asserts the *conditional* statement, not an impossibility.

> **Fixture note for the freeze bundle (verified by this architect against `src/winstats.py`):** the
> literal call above returns `r(92) = 0.4950264429325317`. The value `0.4966` circulating in
> `COORDINATOR_DECISIONS.md` §5 is stale by 0.0016. The *conclusion* is unaffected — `r(91) = 0.499041 >
> 0.497 >= r(92)`, so the crossing index 92 is right — but every radius printed in the protocol must be
> regenerated by `experiments/live_ab/dryrun_live_ab.py --radius-table` (G3, section 9) and the generated
> table, not a hand-typed one, goes into the freeze bundle. `PROTOCOL-GAP PG-20` is closed this way, and
> protocol 1.3 records the same correction; the stale constant survives only in the coordinator's own file,
> which no code reads.

---

## 1. Architecture decisions (rationale, so that no implementer re-litigates them)

**AD-1. One OS process per episode; no threads; no pipes.** The v2 draft and `R3_harness_plan.md` §A.3
specified long-lived `multiprocessing` workers with duplex pipes. This architecture replaces them with `subprocess.Popen([python, lab_worker.py, --job <job file>])`, one process
per episode, because (a) the fsynced spool is already the source of truth and the pipe carried only a
wake-up, (b) `sandbox.run_program` uses `preexec_fn`, which CPython documents as unsafe with threads, so a
worker had to be single-threaded anyway, (c) crash isolation, resume and orphan recovery become "look at
the pid and the spool" instead of pipe-state reasoning, and (d) process spawn (~0.3 s) is negligible
against episodes of seconds to minutes. `PROTOCOL-GAP PG-6`, **now also written into protocol 5.1**, which
specifies one OS process per episode, the per-episode spool `spools/ep_<arrival>_<attempt>.jsonl`, no pipe,
and the orchestrator-death behaviour.

**AD-2. Exactly one writer of each chain.** The orchestrator writes the trial chain and the program chain.
Workers and the anchor process write **spools**; the orchestrator ingests spool lines and turns them into
chain events. Nothing else opens a chain file for writing, ever.

**AD-3. The statistical core is pure.** `lab_monitor` and `lab_enclosure` take already-parsed data
structures and return values. No file I/O, no clock, no randomness, no logging, no numpy global state.
This is what makes the verifier's replay meaningful and what lets G3 work with zero knowledge of G4/G5.

**AD-7. The decision rule exists twice, in two modules written by two groups.** Protocol 8.9 requires a
**reference rule that is a different code path** from the live monitor, evaluated as a shadow at every
evaluation, and names `lab_reference_rule` in the freeze deliverable (protocol 14.2 row 10) and in the
immutable list (protocol 14.3). This document therefore specifies `lab_reference_rule.py` (3.8b) as a real
module: **owned by G1, not by G3**, stdlib + numpy + `winstats` only, importing nothing from `lab_monitor` or
`lab_enclosure`, re-deriving the enclosures and the bands from the chain alone. Collapsing the two paths into
one call site would make `monitor_mismatch` unreachable and `trial_paused(monitor_mismatch)` dead code, which
is exactly what critic N19 closed and audit **B2** reopened. The replay and `_band_independent` of
`lab_verify_log` remain, as the *post hoc* check; they are not a substitute for the live shadow.

**AD-4. Import isolation is a test, not a convention.** `tests_lab_isolation.py` parses every module with
`ast` and compares its import set against the table in section 3.16. A violation fails the suite.

**AD-5. No new dependencies.** Standard library, `numpy`, `pandas`, `requests`, `scipy` (only transitively
through `winstats`). Nothing else. No `pytest`, no `pydantic`, no `jsonschema`: schema validation is a
hand-written dict walk in `lab_eventlog` (~120 lines).

**AD-6. Prefer a dumb loop.** The orchestrator is one single-threaded `while True:` with a 50 ms poll. No
async, no selectors, no state stored anywhere but the chain and the frozen files.

---

## 2. File layout

### 2.1 `experiments/live_ab/` (tracked; flat modules, no package)

Modules are imported by bare name, exactly as `experiments/local_stream/` does. Every entry point does
`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` through `lab_common.add_import_paths()`;
`unittest discover -s experiments/live_ab` already puts the directory on `sys.path[0]`.

| file | group | role |
|---|---|---|
| `lab_common.py` | G1 | paths, tokens, canonical JSON, hashing, exception taxonomy, freeze bundle |
| `lab_eventlog.py` | G1 | segmented hash chain, schema validator, chain reader |
| `lab_verify_log.py` | G1 | independent verifier + CLI (`plumbing` and `full` modes) |
| `lab_reference_rule.py` | G1 | **the reference rule of protocol 8.9**: a second, independent implementation of the enclosures, the bands and the decision, from the chain alone (3.8b). Decision-defining code, immutable |
| `lab_data.py` | G2 | roster build, reference sweep, exclusions, task-content hash |
| `lab_design.py` | G2 | arrival order and pairing (no assignment anywhere in this file) |
| `lab_coin.py` | G2 | OS-entropy coin, write-ahead commit, orientation map |
| `lab_monitor.py` | G3 | normal-mixture band, monitor state, decision function, replay |
| `lab_enclosure.py` | G3 | enclosure arithmetic, pair scores, certificates |
| `lab_client.py` | G4 | spooling llama.cpp client with the pilot's `chat()` interface |
| `lab_server.py` | G4 | llama-server start / identity / health / `/metrics` |
| `lab_serving_manifest.py` | G4 | *(Amendment 2026-09-24, pre-outcome; root `reviews/serving_manifest_binding_ruling_20260924_0153.md`)* the serving manifest of protocol 2.2 item 2: the one write-once artifact `results/live_ab/freeze/serving_manifest.json`, its assembly from the durable build and its re-verification against the runtime at every invocation, start and restart; the dependency closure of `experiments/live_ab_serving/dependency_closure.py` transcribed verbatim (3.16) |
| `lab_hostcheck.py` | G5 | **the host quiescence gate of protocol 5.7**: enumerates foreign accelerator consumers, refuses trial start on a contended host, and reports in-trial foreign load. Observes only — it never signals, kills or throttles anything (3.17) |
| `lab_mock_server.py` | G4 | scripted stand-in for llama-server (no model) |
| `lab_worker.py` | G4 | one-episode worker process, spool writer, execution lock |
| `lab_orchestrator.py` | G5 | state machine, single chain writer, scheduler, switch, resume |
| `lab_anchor.py` | G5 | anchor process: git commit/push/comment, receipt spool |
| `build_live_ab_results.py` | G5 | tables and figures from chain + records, after the last trial |
| `dryrun_live_ab.py` | G5 | end-to-end mock scenarios + `--radius-table` |
| `config.json` | G5 (assembled) | the frozen configuration (section 6) |
| `tests_lab_chain.py` | G1 | tests for `lab_common`, `lab_eventlog`, `lab_verify_log`, `lab_reference_rule` |
| `tests_lab_isolation.py` | G1 | AST import-isolation test over all modules |
| `tests_lab_design.py` | G2 | tests for `lab_data`, `lab_design`, `lab_coin` |
| `tests_lab_stats.py` | G3 | tests for `lab_monitor`, `lab_enclosure` |
| `tests_lab_serving.py` | G4 | tests for `lab_client`, `lab_server`, `lab_mock_server`, `lab_worker` |
| `tests_lab_hostcheck.py` | G5 | tests for `lab_hostcheck` and for the orchestrator's two call sites into it |
| `tests_lab_e2e.py` | G5 | orchestrator, resume, switch, anchor, builder, dry runs |
| `testdata/` | mixed | golden fixtures, owner named per file in section 9.3 |
| `protocol.md`, `run_book.md` | — | frozen text, not code; hashed into the bundle |

### 2.2 `results/live_ab/` (tracked; no free text, no absolute paths, no URLs, no commit ids)

```
results/live_ab/
  freeze/
    freeze_bundle.json           # the canonical object whose sha256 is the genesis input
    config.json                  # byte copy of the frozen configuration
    roster.json                  # {tasks:[...], exclusions:[...], sha256 fields}
    arrival_order_T1.json ... arrival_order_T4.json
    golden_props_coder.json, golden_props_t3.json
    golden_generation_settings_coder.json, golden_generation_settings_t3.json
    serving_manifest.json        # protocol 2.2 item 2: written once (amendment 2026-09-24, root 01:53)
    radius_table.csv             # generated, never hand-typed
    derivation.json              # every pre-freeze-decided value with its rule and inputs
  _prefreeze/events/seg_0000.jsonl ...        # smoke, calibration, rehearsal chain
  _program/events/seg_0000.jsonl ...          # the program chain (N1 fix)
  _program/anchors/anchor_<seq>.json
  T4/  T2/  T1/  T3/
    events/seg_0000.jsonl ...    # the trial chain, closed segments only
    anchors/anchor_<seq>.json
    status.json                  # arm-blind live status (protocol 14.7); overwritten, never hashed
    exposure_ledger.json         # written once at trial end, recomputable from the chain
```

### 2.3 `work/live_ab/` (git-ignored; the private evidence that the archive seals)

```
work/live_ab/<trial>/
  jobs/job_<arrival>_<attempt>.json           # orchestrator -> worker, fsynced before spawn
  spools/ep_<arrival>_<attempt>.jsonl         # worker -> orchestrator, append-only, fsynced
  records/<record_sha256>.json                # full run_episode record, content-addressed, write-once
  requests/<request_id>.json.gz               # full request and response bodies
  anchor_spool/requests.jsonl                 # orchestrator -> anchor process
  anchor_spool/receipts.jsonl                 # anchor process -> orchestrator
  anchors_private/receipts.jsonl              # identified receipts (comment ids, URLs, commit ids)
  logs/llama_<port>.log
  run.lock                                    # exclusive; holds pid, inv, argv
  sandbox.lock                                # host-wide execution lock (flock)
```

Rule enforced by `lab_eventlog`'s validator and re-checked by the verifier: **a tracked file never
contains a URL, an absolute path, an account name, a commit id, or free text.** Private paths appear in
tracked artifacts only as `<WORK>/...` tokens and sha256 digests.

---

## 3. Modules

Conventions that apply to every module below:

* Python 3.12; `from __future__ import annotations` at the top of every file.
* Type hints on every public function. `TypedDict` for JSON-shaped dicts, `@dataclass(frozen=True)` for
  value objects. No `Any` in a public signature except where stated.
* Every public function is either **pure** (marked `[pure]`: no I/O, no clock, no randomness, no global
  mutation) or has its side effects listed explicitly.
* Exceptions come from the taxonomy in 3.1. A module never raises a bare `Exception`, never catches one
  without re-raising a taxonomy exception, and never calls `sys.exit()` except in a `main()`.
* No function silently repairs bad input. A refusal is an exception; the orchestrator maps it to an event.
* Timestamps: `t_wall_ns = time.time_ns()`, `t_mono_ns = time.monotonic_ns()`. `time.monotonic_ns()` is
  comparable only inside one process; the chain records which process produced it (`inv` for the
  orchestrator, the worker's `pid` in spool lines).
### 3.1 `lab_common.py` — G1

Permitted imports: **standard library only** (`dataclasses, hashlib, json, os, platform, subprocess, sys,
time, pathlib, typing`). Deliberately *not* `experiments/local_stream/common.py`: G1 must be importable by
the monitor, the verifier and the builder without dragging the pilot's path shim into them.

```python
# ---- paths (module constants, all absolute, computed once) -----------------
HERE: Path                      # experiments/live_ab
REPO_ROOT: Path                 # HERE.parents[1]
SRC_DIR: Path                   # REPO_ROOT/'src'
LS_DIR: Path                    # REPO_ROOT/'experiments'/'local_stream'
RESULTS_ROOT: Path              # REPO_ROOT/'results'/'live_ab'
WORK_ROOT: Path                 # REPO_ROOT/'work'/'live_ab'
FREEZE_DIR: Path                # RESULTS_ROOT/'freeze'
PROGRAM_CHAIN_ID: str = '_program'
PREFREEZE_CHAIN_ID: str = '_prefreeze'
TRIALS: tuple[str, ...] = ('T4', 'T2', 'T1', 'T3')     # execution order, frozen
ARMS: tuple[str, str] = ('incumbent', 'candidate')

def add_import_paths() -> None:
    """Insert LS_DIR and SRC_DIR at the front of sys.path (idempotent).
    Side effect: mutates sys.path. ONLY lab_data, lab_worker and lab_client may call it."""

@dataclass(frozen=True)
class TrialPaths:
    trial: str
    results: Path      # RESULTS_ROOT/trial
    events: Path       # .../events
    anchors: Path      # .../anchors
    work: Path         # WORK_ROOT/trial
    jobs: Path; spools: Path; records: Path; requests: Path
    anchor_spool: Path; anchors_private: Path; logs: Path
    run_lock: Path; sandbox_lock: Path
    def mkdirs(self) -> None: ...          # side effect: creates every directory, mode 0o755

def trial_paths(trial: str, *, execution_lock: Path | str | None = None) -> TrialPaths: ...
                                                                    # [pure] except for the object
                                                                    # execution_lock: ISOLATED TREES ONLY.
                                                                    # Production passes nothing and gets the
                                                                    # canonical host-wide sandbox.lock of
                                                                    # protocol 5.7 item 1. run_lock stays
                                                                    # per trial.
def tokenize_path(p: str | Path) -> str:
    """'/Users/x/ICLR.../work/live_ab/T1/records/ab.json' -> '<WORK>/T1/records/ab.json'.
    Replaces, longest prefix first: WORK_ROOT -> '<WORK>', RESULTS_ROOT -> '<RESULTS>',
    REPO_ROOT -> '<REPO>', Path.home() -> '<HOME>', tempfile.gettempdir() -> '<TMP>'.
    A path that matches none of these raises UntokenizablePath."""

# ---- canonical JSON and hashing -------------------------------------------
def canonical_json(obj: object) -> str:
    """json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).
    Raises ValueError (from json) on NaN/Inf. Floats serialize through repr() as CPython does."""
def sha256_bytes(b: bytes) -> str: ...
def sha256_text(s: str) -> str: ...
def sha256_file(p: str | Path) -> str: ...            # 1 MiB chunks
def sha256_canonical(obj: object) -> str: ...         # sha256_text(canonical_json(obj))

# ---- durable writes --------------------------------------------------------
def fullsync(fd: int) -> None:
    """fcntl.fcntl(fd, fcntl.F_FULLFSYNC) on darwin when available, else os.fsync(fd).
    macOS os.fsync() does NOT flush the drive cache; F_FULLFSYNC does."""
def write_json_atomic(path: Path, obj: object, *, durable: bool = True) -> str:
    """Write canonical_json(obj) to <path>.tmp, fullsync, os.replace, fullsync the directory.
    Returns the sha256 of the bytes written. Raises WriteOnceViolation if path exists and its
    bytes differ."""
def append_line_durable(fd: int, line: str, *, durable: bool) -> int:
    """One os.write of (line + '\\n').encode('utf-8') on an O_APPEND descriptor; fullsync when
    durable. Returns bytes written. Partial writes raise TornWrite (they cannot happen for
    lines below PIPE_BUF-sized writes to a regular file, but the check is one line)."""

# ---- environment provenance ------------------------------------------------
def hardware_info() -> dict: ...        # platform, machine, cpu brand, memsize, ncpu, os_version
def package_versions() -> dict: ...     # numpy, scipy, pandas, requests, python
def boottime_hash() -> str: ...         # sha256 of `sysctl -n kern.boottime` output; '' off darwin
def process_rss_bytes(pattern: str) -> list[dict]: ...

# ---- freeze bundle ---------------------------------------------------------
FREEZE_BUNDLE_KEYS: tuple[str, ...] = (
    'protocol_version', 'config_sha256', 'rule_block_sha256', 'roster_sha256',
    'task_content_sha256', 'arrival_order_sha256', 'protocol_sha256', 'run_book_sha256',
    'harness_file_sha256', 'reused_file_sha256', 'winstats_sha256', 'gguf_sha256',
    'license_evidence_sha256', 'serving_manifest_sha256', 'golden_props_sha256',
    'golden_generation_settings_sha256', 'receipt_mask_sha256', 'sandbox_profile_sha256',
    'containment_probe_sha256', 'prefreeze_head', 'prefreeze_bytes', 'prefreeze_file_sha256',
    'derivation_sha256', 'planning_sha256', 'environment_lock_sha256', 'hardware_allowlist')
HARNESS_FILES: tuple[str, ...]      # every *.py and config.json under experiments/live_ab
REUSED_FILES: tuple[str, ...]       # ('agent.py','sandbox.py','verify.py','data.py','common.py')

def build_freeze_bundle(parts: dict) -> dict:
    """[pure] Validate that parts.keys() == set(FREEZE_BUNDLE_KEYS) exactly (no extras, no
    missing, no None, no 'unknown' anywhere in the tree) and return the canonicalised object.
    Raises FreezeIncomplete naming every offending key."""
def freeze_bundle_sha256(bundle: dict) -> str: ...        # [pure]
def harness_file_hashes() -> dict[str, str]: ...          # sha256 of every HARNESS_FILES entry
def rule_block_sha256(config: dict) -> str:
    """[pure] sha256 over the canonical JSON of the decision-defining subset of the config
    (section 6.2 'rule block'), so that the hash survives the pre-freeze pinning of operational
    values. (critic N11.) A freeze test asserts that this equals the rule-block hash computed from
    the frozen tables of protocol_FINAL.md sections 6.2-6.4, 7 and 8 (audit B1): the two documents
    cannot be frozen in disagreement about the hierarchy, the tolerance, the certificate constant,
    the coin or the seed rule."""

# ---- exception taxonomy (every module raises only from this tree) ----------
class LabError(Exception): ...
class FreezeIncomplete(LabError): ...
class FrozenMismatch(LabError): ...         # a hash differs from the bundle
class UntokenizablePath(LabError): ...
class WriteOnceViolation(LabError): ...
class TornWrite(LabError): ...
class ChainError(LabError): ...             # any hash-chain / ordering violation
class SchemaError(LabError): ...            # event body violates the schema or the string rule
class SpoolError(LabError): ...
class EnclosureError(LabError): ...         # an enclosure widened, or is empty, or is outside [-1,1]
class MonitorError(LabError): ...
class ReceiptMismatch(LabError): ...        # server receipt != golden object
class ServerIdentityError(LabError): ...
class PreflightError(LabError): ...
class VerifyFailure(LabError): ...          # the verifier's own FAIL, carries a list of findings
class AbortTrial(LabError):                 # carries a reason code from the closed list
    reason: str
class PauseTrial(LabError):
    reason: str
```

**PROTOCOL-GAP PG-11 (critic N12, audit M13) — "free text" made operational.** The earlier draft forbade
free text while embedding the full config, which contains prose labels. Resolution, now also in protocol
12.2: every string-valued field of every event body must satisfy one of
`{enum member of the schema, lowercase hex of fixed length (16/32/40/64), a '<TOKEN>/...' path, an ISO-8601
UTC instant, a bare integer as string, a reason code from the closed list, a task uid matching
'^(mbpp|mbpp_full|humaneval)/[0-9]+$' that is present in roster.json}`. The full config is **not**
embedded: `trial_started` carries `config_sha256` and `rule_block_sha256`, and `results/live_ab/freeze/config.json`
is the tracked sibling. The validator enforces this per field, per event type.

---

### 3.2 `lab_eventlog.py` — G1

Permitted imports: stdlib + `lab_common`. **Never** numpy, never any other `lab_*` module.

```python
CHAIN_DOMAIN: str = 'live_ab/eventlog-v3'
SEGMENT_FMT: str = 'seg_%04d.jsonl'

class Event(TypedDict):
    seq: int; type: str; t_wall_ns: int; t_mono_ns: int
    inv: str; chain: str; prev: str; body: dict; h: str

def genesis_prev(anchor_value: str, chain_id: str) -> str:
    """[pure] sha256(CHAIN_DOMAIN + '|' + anchor_value + '|' + chain_id), the ONE genesis rule for all
    three kinds of chain (protocol 12.1). `anchor_value` is the freeze-bundle sha256 for the program
    chain ('_program') and the four trial chains, and the literal token 'prefreeze' for the
    pre-freeze chain, which is written before the bundle exists. There is no second domain string."""

def event_hash(ev: Mapping) -> str:
    """[pure] sha256 of canonical_json({k: v for k, v in ev.items() if k != 'h'})."""

class EventLog:
    """Single-writer, append-only, segmented hash chain. One instance per chain per process.

    Opening an existing chain re-verifies it in full (read_chain) and refuses to append on any
    violation except a single torn region at the end of the last segment, which is committed by a
    log_recovery event (the file is NEVER truncated).
    """
    def __init__(self, events_dir: Path, chain_id: str, freeze_bundle_sha256: str,
                 inv: str, *, create: bool = False) -> None:
        """Side effects: reads every segment; opens the last segment O_WRONLY|O_APPEND|O_CREAT;
        may append one log_recovery (durable). Raises ChainError on any other violation.
        create=True refuses if any segment already exists."""
    @property
    def head(self) -> str: ...            # h of the last event, or genesis_prev
    @property
    def seq(self) -> int: ...             # next seq to be written
    @property
    def events(self) -> list[Event]: ...  # the verified in-memory chain (read-only view)
    def append(self, etype: str, body: dict, *, durable: bool = False) -> Event:
        """Validate the body (validate_event), build the envelope, one os.write, fullsync when
        durable, append to self.events, return the event. Raises SchemaError before any byte is
        written. A durable append returns only after fullsync() has returned."""
    def close_segment(self, *, anchor_body: dict) -> Event:
        """Append the `anchor` event (durable), close the descriptor, open segment k+1.
        The anchor event is by definition the last line of its segment."""
    def close(self) -> None: ...

@dataclass(frozen=True)
class TornRegion:
    segment: int; offset: int; length: int; sha256: str; is_event_prefix: bool

@dataclass(frozen=True)
class ChainRead:
    events: list[Event]; torn: TornRegion | None; segments: list[Path]
    segment_bytes: list[int]; segment_sha256: list[str]

def read_chain(events_dir: Path, chain_id: str, freeze_bundle_sha256: str) -> ChainRead:
    """[pure-ish: reads files, writes nothing] Verify and return the whole chain.

    Rules, all fatal (ChainError) unless stated:
      * segments are seg_0000..seg_NNNN with no gaps; every segment but the last ends with an
        `anchor` event; a closed segment is never reopened.
      * per line: json.loads succeeds; event_hash(ev) == ev['h']; ev['prev'] == previous h (across
        segment boundaries); ev['seq'] == len(events); ev['chain'] == chain_id;
        canonical_json(ev).encode('utf-8') == the raw line bytes (byte-identity round trip).
      * torn region: ALL bytes from the first invalid byte to the end of the LAST segment form one
        opaque region regardless of newlines inside it. It is legal only (a) as the unterminated
        tail when the caller is EventLog.__init__, or (b) when the next valid event is
        `log_recovery` committing to exactly (offset, length, sha256). Two committed regions in a
        row, or a region not at the end, is a ChainError.
      * `t_wall_ns` decreasing by more than 1e9 ns inside one `inv` is recorded as a
        `clock_anomaly` finding, NOT a ChainError.
    """

def validate_event(etype: str, body: Mapping) -> None:
    """[pure] Raise SchemaError unless body matches EVENT_SCHEMA[etype] exactly: every required
    key present, no unknown key, every value of the declared type, every string satisfying the
    string discipline of PG-11, every int a real int (bool is not an int here), every float finite."""

EVENT_SCHEMA: dict[str, dict[str, FieldSpec]]     # section 4; G1 transcribes it verbatim

@dataclass(frozen=True)
class FieldSpec:
    kind: Literal['int','float','bool','hex64','hex40','hex32','hex16','enum','token_path',
                  'iso8601','list','obj','null_or']
    required: bool = True
    enum: tuple[str, ...] = ()
    item: 'FieldSpec | None' = None      # for 'list'
    fields: 'dict[str, FieldSpec] | None' = None    # for 'obj'
    inner: 'FieldSpec | None' = None     # for 'null_or'
```

Notes for the implementer:

* `append` builds the envelope in this exact key order in the source (irrelevant to the bytes, since
  `sort_keys=True`, but keep it readable): `seq, type, t_wall_ns, t_mono_ns, inv, chain, prev, body`, then
  computes `h`, then writes.
* One `os.write` per line. Never `io.TextIOWrapper`, never `print`, never buffered `open(..., 'a')`.
* `durable=True` means: the drive has the bytes before the call returns. Everything the protocol calls
  write-ahead depends on this and nothing else.

---

### 3.3 `lab_verify_log.py` — G1

Permitted imports: stdlib + `lab_common` + `lab_eventlog` + `lab_monitor` + `lab_enclosure` + `numpy` +
`winstats`. **Forbidden:** `lab_orchestrator`, `lab_worker`, `lab_client`, `lab_server`, `lab_anchor`,
`lab_mock_server`, `build_live_ab_results`.

```python
@dataclass(frozen=True)
class Finding:
    check: str           # stable identifier, e.g. 'chain.byte_identity'
    severity: Literal['FAIL', 'DEFECT', 'INFO']
    trial: str; seq: int | None; detail: dict        # detail holds only JSON scalars

@dataclass(frozen=True)
class VerifyReport:
    trial: str; mode: Literal['plumbing', 'full']; verdict: Literal['PASS', 'FAIL']
    findings: list[Finding]; counts: dict[str, int]
    def to_json(self) -> dict: ...

def verify_trial(trial: str, freeze_bundle_sha256: str, *, mode: str = 'full',
                 results_root: Path | None = None, work_root: Path | None = None) -> VerifyReport: ...
def verify_program(freeze_bundle_sha256: str, *, results_root: Path | None = None) -> VerifyReport: ...
def main(argv: list[str] | None = None) -> int:
    """CLI: --trial T1 [--mode plumbing|full] [--results DIR] [--work DIR] [--json OUT].
    Exit code 0 on PASS, 1 on FAIL, 2 on a usage error. Writes nothing but --json."""
```

The check list, each an identifier that appears in `Finding.check` (G1 implements all of them; the
severity column is frozen here so the plumbing gate of PG-13 is machine-checkable):

| check | severity | what it asserts |
|---|---|---|
| `chain.read` | FAIL | `read_chain` succeeds for the program chain and every trial chain |
| `chain.byte_identity` | FAIL | re-canonicalising each parsed line reproduces the raw bytes |
| `chain.genesis` | FAIL | `prev` of seq 0 equals `genesis_prev(bundle, chain_id)` |
| `chain.segments` | FAIL | segment numbering gapless; every non-final segment ends with `anchor` |
| `chain.torn` | DEFECT | a committed torn region exists; `is_event_prefix` and `boottime` change recorded |
| `schema.all` | FAIL | every event revalidates against `EVENT_SCHEMA` |
| `order.freeze_hashes` | FAIL | `trial_started` hashes equal the freeze bundle's |
| `order.enrollment` | FAIL | the `pair_enrolled` sequence equals `arrival_order_<trial>.json` in pair index, both uids and both positions, with no gaps |
| `coin.one_per_pair` | FAIL | at most one chain-valid `coin_drawn` per pair; none after a `decision`; none before the start receipt |
| `coin.write_ahead` | FAIL | every `episode_started` references an earlier durable assignment event of its arrival |
| `coin.balance` | INFO | count of `bit == 1` with the exact binomial two-sided p-value |
| `episode.one_reveal` | FAIL | exactly one `episode_revealed` per assigned arrival |
| `episode.record_match` | FAIL | outcome fields of `episode_revealed` equal the hashed record file |
| `episode.job_accepted` | DEFECT | every `episode_started` has a `job_accepted` spool line, or is flagged `started_after_resume` |
| `calls.one_terminal` | FAIL | exactly one `llm_response`/`llm_error` per `llm_request` unless the attempt is terminal |
| `seeds.unique` | DEFECT | all drawn seeds distinct across the program; never `0xFFFFFFFF` (PG-8) |
| `monitor.replay` | FAIL | every `monitor_update` and `decision` is reproduced from the chain alone, **element-wise over the evaluation triggers of protocol 8.3** (enroll, reveal, call-that-raises-`ell`, resume, drain) — the replay and the live monitor consume the same trigger set, so a length mismatch is a real defect and never a cadence disagreement (audit B3) |
| `monitor.cadence` | FAIL | exactly one `monitor_update` per evaluation trigger of protocol 8.3; **no `monitor_update` at a `metrics_scrape`, at any other non-triggering event of protocol 7.3 item 3, or anywhere in the follow-up cohort** (audit B6) |
| `monitor.shadow` | FAIL | every `monitor_update` carries the `shadow` object; where `shadow.mismatch` is true, a `trial_paused(monitor_mismatch)` follows before any decision is acted on |
| `monitor.independent_band` | FAIL | `_band_independent` equals `lab_monitor.band` to 1e-12 at every look |
| `reference_rule.agreement` | FAIL | `lab_reference_rule.decide_from_chain` agrees with the logged `decision` in kind and prefix (protocol 8.9); a disagreement is `LIVE_DECISION_INVALID` and, between trials, condition list B of protocol 6.4 row 22b |
| `monitor.first_crossing` | FAIL | the decision is the FIRST look at which the rule holds; no retained crossing |
| `enclosure.containment` | FAIL | every ultimately revealed score lies inside every enclosure recorded for its pair at every look. **A violation is a proven defect of decision-defining code: protocol 6.4 row 24 applies to that trial** (claims 2-5 and 7 dropped); there is no lighter path |
| `enclosure.monotone` | FAIL | enclosures never widen |
| `worktree.integrity` | FAIL | every `worktree_drift` pause (protocol 6.4 row 27) carries the observed and expected digests, the resume follows a match, and no `worktree_drift` event is counted in the integrity label or reported as evidence of editing (protocol 12.6) |
| `switch.phase` | FAIL | no `coin_drawn` after `decision`; every later arrival has `arm_assigned_by_decision`; post-decision reveals are excluded from the monitor |
| `usage.reconciliation` | DEFECT | per-window counter deltas vs summed `usage` (PG-10) |
| `exposure.ledger` | FAIL | `exposure_ledger.json` equals a recount from the chain |
| `anchor.prefix` | FAIL | each `anchor`'s `upto_h` and `segment_sha256` match the committed segment bytes |
| `anchor.receipts` | DEFECT | every `anchor` has a receipt or an `anchor_failed`; longest unreceipted span reported |
| `integrity.table` | INFO | the six tables of **protocol 12.6** (including the `posting_latency_p95_s` term of the sandwich tolerance, the covered-gap rule, the `job_accepted` column, the randomized-phase / follow-up split, and the environment-event column for `worktree_drift`) |
| `t4.payload_identity` | FAIL | in T4, the two job payloads of every pair are byte-identical after removing exactly the keys of PG-14: `arm`, `arrival`, `inv`, `pair`, `position`, `task_uid`, `worker_index`, `paths`, `assignment_seq`, `payload_sha256` |
| `program.order` | FAIL | the program chain opens and closes the four trials in the frozen order and contains every re-freeze authorization any `invocation_started` relied on |
| `host.record` | FAIL | every `host_quiescence_refused` (P6b) and `foreign_load_detected` (T6b) is internally honest: `clean` is true **exactly** when the record carries no finding and no degraded cause, the counts are non-negative, and every `detector` and every degraded `cause` is inside the closed vocabularies of `lab_hostcheck.DETECTOR_LABELS` / `DEGRADED_CAUSES`. A chain that claims a clean host while carrying offenders is worse than one carrying no scan at all, so this is a FAIL and not an INFO |
| `host.quiescence` | DEFECT | what the scan actually saw: the detectors, the count and the longest elapsed time of any foreign consumer, and separately any scan that could not establish quiescence. A foreign load observed **during** a trial is a fact the analysis must carry; what to do about it is the operator's decision, not the verifier's. **In the program chain the same rows are emitted at `INFO`**, because a trial-start refusal carries offenders by construction — that is why the event exists — and the gate refusing a trial is the gate working, not a defect in a trial's chain. The consistency half (`host.record`) still applies in full |

`_band_independent` is a **third, deliberately naive implementation** of the band written inside
`lab_verify_log.py`, calling `winstats.normal_mixture_radius` directly in a Python loop, never importing
`lab_monitor`'s band code. The **second** implementation is the live shadow, `lab_reference_rule` (3.8b);
see `PROTOCOL-GAP PG-3`.

**Which verifier FAILs mean what between trials** (protocol 6.4 rows 22a/22b, audit M5): `chain.*`,
`reference_rule.agreement` and `t4.payload_identity` are **condition list B** — they implicate
decision-defining code, so protocol row 24 applies to the affected trial and continuation needs a new
protocol version; a harness-only re-freeze may **never** close them. `usage.reconciliation`,
receipt-mismatch counts and a completeness FAIL caused by the verifier's own bookkeeping are **condition
list A** — repairable by a reporting-code re-freeze, and a second occurrence of the same condition id stops
the program. `lab_verify_log` prints the list letter next to every FAIL so the operator has no choice to
make after outcomes exist.

Plumbing mode (`--mode plumbing`, run between trials) emits **only** the rows above whose check id starts
with `chain.`, `schema.`, `order.`, `coin.`, `episode.`, `calls.`, `switch.`, `usage.`, `anchor.`,
`program.`, `worktree.`, `t4.`, `host.` and the `monitor.replay`, `monitor.cadence`, `monitor.shadow` and
`reference_rule.agreement` verdict flags — never a score, never a count by arm, never a
table. `verify_trial` asserts this by construction: in plumbing mode the report object is built from a
whitelist of check ids, and a test feeds it a chain with an extreme outcome imbalance and asserts the two
reports are identical.

---

### 3.4 `lab_data.py` — G2

Permitted imports: stdlib + `lab_common` + (via `add_import_paths()`) the pilot's `data`, `verify`,
`sandbox`. Not numpy.

```python
class Task(TypedDict):
    uid: str                 # 'mbpp/2', 'mbpp_full/39', 'humaneval/0'
    benchmark: Literal['mbpp', 'mbpp_full', 'humaneval']
    stratum: Literal['S1', 'S2']       # S1 = sanitized MBPP + HumanEval, S2 = unsanitized MBPP
    prompt: str; entry_point: str; reference: str
    test_imports: list[str]; test_list: list[str]; challenge_test_list: list[str]
    test: str                # humaneval only, '' otherwise

class Exclusion(TypedDict):
    uid: str
    reason: Literal['duplicate_prompt', 'no_entry_point', 'reference_fails_verify',
                    'reference_timeout', 'out_of_design_smoke_task', 'unparsable']
    detail_sha256: str       # sha256 of the captured stderr/stdout, never the text itself

SOURCES: dict[str, dict]     # pinned url, bytes, sha256 for sanitized-mbpp.json, HumanEval.jsonl.gz,
                             # mbpp.jsonl @ f82046ba5aabbbb427dbfd38a254d26bff08b533

def fetch_sources(dest: Path, *, offline: bool = False) -> dict:
    """Download (or reuse the cached copy of) every pinned source; verify bytes and sha256 against
    SOURCES; raise FrozenMismatch on any difference. offline=True refuses to use the network and
    requires every file to be present. Side effect: writes dest/<name> and dest/sources.json."""

def build_candidate_tasks(raw: dict) -> list[Task]:
    """[pure] Canonicalise all three sources into Task records. Ordering is frozen:
    mbpp (sanitized) by numeric id, then mbpp_full by numeric id, then humaneval by numeric index.
    A mbpp_full task whose normalised prompt equals a sanitized task's is dropped here with
    reason 'duplicate_prompt' (normalisation = lowercase, collapse whitespace)."""

def sweep_references(tasks: list[Task], cfg: dict, *, on_progress=None) -> list[Exclusion]:
    """Run verify(task, task['reference']) under the sandbox for every candidate task, one at a
    time, holding the host-wide execution lock. Side effects: sandbox subprocesses, temp dirs.
    NO model call. Returns the exclusions; never mutates `tasks`."""

def build_roster(tasks: list[Task], exclusions: list[Exclusion], cfg: dict) -> dict:
    """[pure] Returns {'tasks': [...surviving Task uids in frozen order...],
    'exclusions': [...], 'n_S1': int, 'n_S2': int, 'n_total': int,
    'n_pairs': n_S1 // 2 + n_S2 // 2,          # protocol 3.3; NEVER n_total // 2
    'roster_sha256': ..., 'task_content_sha256': ...}.
    task_content_sha256 hashes the canonical JSON of the full task objects (prompt, tests, entry
    point, reference) so that a silently changed benchmark file is caught."""

def write_roster(roster: dict, path: Path) -> str: ...   # write-once; raises WriteOnceViolation
def load_roster(path: Path) -> dict: ...
def load_tasks_by_uid(roster: dict, sources_dir: Path) -> dict[str, Task]: ...
```

`n_pairs = n_S1 // 2 + n_S2 // 2` is the horizon `N_P` (protocol 3.3). Pairs are formed **inside a stratum**,
so **each stratum contributes its own leftover** and a pair never crosses the strata. With the extended
roster this is at most **568** before any exclusion (`floor(591/2) + floor(547/2) = 295 + 273`) and at most
565 after the six smoke exclusions; with S1 only it is 295. `n_total // 2` would be 569 and is **wrong**; the
number 569 must not appear as a horizon anywhere in the code, the config or a test (audit B5). A leftover
task is never enrolled.

---

### 3.5 `lab_design.py` — G2

Permitted imports: stdlib + `numpy` + `lab_common`. **This file contains no coin, no arm, no assignment,
and no import of `lab_coin`; a test greps its AST for the identifiers `urandom`, `arm`, `incumbent`,
`candidate`, `coin` and fails if any appears.**

```python
class PairSlot(TypedDict):
    pair: int                # 1-based
    stratum: Literal['S1', 'S2']      # there is no 'mixed' stratum: a pair never crosses the strata
    arrivals: tuple[int, int]     # (2*pair-1, 2*pair)
    uids: tuple[str, str]         # task at position 1, task at position 2

def arrival_order(roster: dict, trial: str, design_seed_base: int) -> list[PairSlot]:
    """[pure] Permute each stratum with numpy.random.Generator(numpy.random.PCG64(
    numpy.random.SeedSequence([design_seed_base, TRIAL_NO[trial]]))), cut each stratum into
    consecutive disjoint pairs, then permute the whole pairs (protocol 3.4).

    Pairing is stratified: S1 tasks pair with S1 tasks and S2 with S2; **the odd remainder of each
    stratum is a leftover and is never enrolled**. There is NO mixed pair: a pair across the strata
    would be the one pair whose two positions have systematically different difficulty, and
    thm:pair_id is invoked through the stratified statement of paper/main.tex:171-172 (audit B5).
    Leftovers receive the arrival numbers after 2 * N_P in list order.

    This is a deterministic function of frozen constants only and carries no assignment (root
    guidance 1; protocol 4.4)."""

def write_order(order: list[PairSlot], path: Path) -> str: ...   # write-once, returns sha256
def load_order(path: Path) -> list[PairSlot]: ...
def order_sha256(order: list[PairSlot]) -> str: ...              # [pure]
def assert_disjoint(orders: dict[str, list[PairSlot]]) -> None:
    """[pure] Every trial's order is a permutation of the same roster; within a trial every uid
    occurs exactly once. Raises ValueError naming the first offender. Tasks ARE reused across
    trials (COORDINATOR rev1 / R3 Q5); this function only proves within-trial disjointness."""
```

---

### 3.6 `lab_coin.py` — G2

Permitted imports: `os`, `lab_common`, `lab_eventlog`. Nothing else — in particular not `random`, not
`numpy`, not `secrets`.

```python
@dataclass(frozen=True)
class Coin:
    raw_hex: str          # 16 hex chars = the 8 bytes actually drawn
    bit: int              # raw[0] & 1
    source: str = 'os.urandom(8)'

ORIENTATION: dict[int, tuple[str, str]] = {
    1: ('candidate', 'incumbent'),      # bit 1 -> candidate at position 1
    0: ('incumbent', 'candidate'),
}

def draw() -> Coin:
    """The ONLY call to os.urandom(8) in the assignment path. No other randomness enters an arm."""

def assignment(pair: PairSlot, coin: Coin) -> dict[int, str]:
    """[pure] {arrival_at_position_1: arm, arrival_at_position_2: arm} from ORIENTATION[coin.bit]."""

def draw_and_commit(log: EventLog, pair: PairSlot) -> tuple[Coin, dict[int, str], Event]:
    """Write-ahead rule, normative. Draws the coin, appends `coin_drawn` with durable=True, and
    returns ONLY after fullsync() has returned. The caller may not dispatch either episode of the
    pair before this function returns. Side effects: one os.urandom call, one durable append."""

def selftest_entropy(n: int = 10_000, lo: int = 4_850, hi: int = 5_150) -> dict:
    """Pre-freeze plumbing check on NON-design coins (phase=SMOKE). Returns
    {'n': n, 'ones': k, 'ok': lo <= k <= hi}. Never repeated silently on failure."""
```

**Binding-on-resume rule (protocol 4.2 invariant v), implemented in `lab_orchestrator.plan_resume` and
re-checked by the verifier:** every chain-valid `coin_drawn` line present in the file binds, whether or not
its fsync had returned. A coin is void only if its line fails chain verification (i.e. it is inside the
torn region). There is no redraw, ever.
### 3.7 `lab_enclosure.py` — G3 (statistical core, part 1)

Permitted imports: stdlib + `numpy` + `winstats` + `lab_common`. **Forbidden:** every other `lab_*`
module. No I/O, no clock, no randomness: every function is `[pure]`.

```python
TIER_NAMES: tuple[str, ...] = ('success', 'latency_s')
# TWO tiers, identical for all four trials (protocol 6.2). `completion_tokens` is RECORDED, NEVER
# SCORED: it is not a tier, there is no third tier anywhere, and T3 uses the SAME kernel as T1/T2/T4.
# The v2 three-tier hierarchy at relative tolerance 0.10 is superseded and must not be implemented
# (audit B1).

@dataclass(frozen=True)
class Enclosure:
    lo: float
    hi: float
    def __post_init__(self):
        """Raise EnclosureError unless -1.0 <= lo <= hi <= 1.0 and both are finite."""
    def narrows_to(self, other: 'Enclosure', *, tol: float = 1e-12) -> bool:
        """[pure] True iff other.lo >= self.lo - tol and other.hi <= self.hi + tol."""
    def contains(self, x: float, *, tol: float = 1e-12) -> bool: ...
    @staticmethod
    def full() -> 'Enclosure': return Enclosure(-1.0, 1.0)

@dataclass(frozen=True)
class EpisodeView:
    """What is known about ONE episode of a pair at a look. Either revealed or pending."""
    arm: Literal['incumbent', 'candidate']
    revealed: bool
    success: int | None              # 0/1 when revealed, None when pending
    latency_s: float | None          # exact when revealed
    completion_tokens: int | None    # exact when revealed
    ell: float                       # certified elapsed LOWER bound (0.0 when nothing was spooled)
    tokens_known: int                # completion tokens already receipted (lower bound)

@dataclass(frozen=True)
class PairEnclosure:
    h: Enclosure           # hierarchy score Z_i, positive favours the candidate
    s: Enclosure           # success difference D_i = s_candidate - s_incumbent
    collapsed: bool        # True iff lo == hi for both scores (both revealed, or the certificate bound)
    decisive_tier: int     # 0 or 1 when a tier decided, -1 for a tie or while open

def tiers_from_config(cfg: dict) -> list[winstats.Tier]:
    """[pure] Build the frozen hierarchy from cfg['hierarchy'], which is the same two-row array for
    ALL FOUR trials (protocol 6.2, Appendix B):

        [winstats.Tier('success'),
         winstats.Tier('cost', higher_better=False, relative_tolerance=0.05)]

    There is no per-trial tier count, no `n_tiers` key, and no token tier. Raises FrozenMismatch if
    cfg['hierarchy'] is not exactly the frozen two-row array (audit B1)."""

def outcome_vector(view: EpisodeView, names: Sequence[str]) -> list[float]:
    """[pure] Revealed episode -> [success, latency_s] as floats, in TIER_NAMES order.
    `completion_tokens` is recorded on the view and in the record file but is never passed to
    `compare` (protocol 6.1, 6.2).
    Raises EnclosureError if the view is pending (compare() requires complete finite outcomes)."""

def final_scores(candidate: EpisodeView, incumbent: EpisodeView,
                 tiers: list[winstats.Tier]) -> tuple[int, int, int]:
    """[pure] The COLLAPSE CERTIFICATE. Both views must be revealed. Returns (z, decisive_tier, d):
        elig = [True, both_succeeded]
        z, tier = winstats.compare(vals(candidate), vals(incumbent), tiers, elig)
        d      = int(candidate.success) - int(incumbent.success)
    Direction is fixed by argument order: +1 favours the candidate. Joint failure is a tie (elig
    False on the lower tiers). Exact threshold equality is a tie (winstats.compare uses a strict >)."""

def certified_elapsed(call_stamps: Sequence[tuple[int, int]]) -> float:
    """[pure] ell = max over spooled stamps of (t_e - t_c1) in seconds, where t_c1 is the worker's
    monotonic stamp at entry into the first chat() call and t_e runs over every send and receive
    stamp. Input is [(t_c1_ns, t_e_ns), ...] already extracted from the chain. Returns 0.0 for an
    empty sequence (critic N5: a worker that died before its first request)."""

def success_enclosure(candidate: EpisodeView, incumbent: EpisodeView) -> Enclosure:
    """[pure] Root guidance 5, literally:
        lo = s_cand_low - s_inc_high ;  hi = s_cand_high - s_inc_low
    with s_low = s_high = success for a revealed episode and (0, 1) for a pending one."""

def hierarchy_enclosure(candidate: EpisodeView, incumbent: EpisodeView,
                        tiers: list[winstats.Tier]) -> Enclosure:
    """[pure] Root guidance 5: start at [-1, 1] and narrow ONLY by enumerating feasible
    completions. Implemented as an explicit enumeration over the closed list of cases below; the
    result is [min(feasible z), max(feasible z)]. No other narrowing exists.

      (a) both revealed                      -> [z, z] with z = final_scores(...)[0]
      (b) neither revealed                   -> [-1, 1]
      (c) one revealed (arm r, sign sgn = +1 if r is the candidate else -1), partner pending with
          certified ell and tokens_known:
            * s_r == 0: partner succeeds -> partner wins tier 0 (z = -sgn);
                        partner fails    -> joint failure, tie (z = 0).
              feasible = {-sgn, 0} -> Enclosure(min, max)
            * s_r == 1: partner fails    -> revealed wins tier 0 (z = +sgn);
                        partner succeeds -> both succeed, tier 1 with relative tolerance 0.05 on
                        latency; the partner's final latency L_p >= ell, so
                            if 0.95 * ell > L_r + 1e-9:  L_p - L_r > 0.05 * L_p  ==> z = +sgn
                            otherwise: every outcome in {-1, 0, +1} stays feasible
              feasible = {+sgn} when the certificate binds, else {-1, 0, +1}.

      The certificate constant is **0.95**, which is `1 - relative_tolerance` at the frozen tolerance
      0.05 (protocol 7.5 item 5; protocol 14.3 lists "the 0.95 certificate constant" by name as
      non-amendable). The 0.9 of the v2 hierarchy is superseded (audit B1).

      This certificate is a COLLAPSE, with the partner still pending, and it is legitimate: protocol
      7.5 item 1 defines a valid final-score certificate as "both episodes revealed with complete
      finite outcomes" OR "the enumeration leaves exactly one feasible value" (audit M4). When it
      binds at an ingested call event it produces a look and can decide (protocol 8.3, PG-1/PG-2).

      No certificate is ever derived from tokens: tokens are not a tier at all."""

def pair_enclosure(candidate: EpisodeView, incumbent: EpisodeView,
                   tiers: list[winstats.Tier]) -> PairEnclosure: ...

def assert_monotone(old: PairEnclosure, new: PairEnclosure) -> None:
    """[pure] Raise EnclosureError unless old.h.narrows_to(new.h) and old.s.narrows_to(new.s).
    Called by lab_monitor on every update and by lab_verify_log on every replayed update."""
```

Worked invariants the implementer must hold (they are the tests of 9.1 G3):

* Every enclosure is a subset of `[-1, 1]` at all times, starts at `[-1, 1]` for an unenrolled-but-pending
  pair, and only ever narrows.
* A pair whose two episodes are revealed has `lo == hi` for both scores. The **only** other collapse is the
  cost certificate above, which leaves exactly one feasible hierarchy value; the success enclosure of such a
  pair is still open until both episodes are revealed.
* A terminal failure (worker died, hard cap, interrupted) is a **reveal**, not a pending state:
  `success = 0`, `latency_s = ell`, `completion_tokens = tokens_known`. The enclosure collapses normally.
  This is why `assert_monotone` can never fail on a terminal failure: `success = 0` is inside `{0, 1}`.

---

### 3.8 `lab_monitor.py` — G3 (statistical core, part 2)

Permitted imports: stdlib + `numpy` + `winstats` + `lab_common` + `lab_enclosure`. **Forbidden:**
`lab_orchestrator`, `lab_worker`, `lab_client`, `lab_server`, `lab_eventlog`, `lab_anchor`, `pandas`.
No I/O, no clock, no randomness.

```python
@dataclass(frozen=True)
class MonitorConfig:
    # NO DEFAULTS on the five frozen statistical fields (audit m9): a config that fails to load must
    # raise, never silently install a horizon, a level or a margin.
    alpha_gate: float                  # 0.00625 = program 0.05 / 4 trials / 2 scores
    rho: float                         # 100.0
    delta: float                       # 0.03
    n_min: int                         # 100
    n_max: int                         # N_P from the roster (<= 568); the horizon
    clip_lo: float = -1.0
    clip_hi: float = 1.0
    @staticmethod
    def from_config(cfg: dict, trial: str) -> 'MonitorConfig':
        """Reads cfg['monitor'] and cfg['roster']['n_pairs']. Raises FrozenMismatch if
        monitor.n_max is null at run time, if it differs from roster.n_pairs, or if any of the five
        fields is absent."""

@dataclass(frozen=True)
class Band:
    n: int; radius: float
    s_lower: float; s_upper: float     # the sums, before dividing
    lo: float; hi: float               # L_j and U_j, already clipped

def band(n: int, s_lower: float, s_upper: float, mc: MonitorConfig) -> Band:
    """[pure] THE decision primitive. Exactly the root's guidance, no variation:

        r  = winstats.normal_mixture_radius(n, alpha=mc.alpha_gate, rho=mc.rho, variance_process=n)
        lo = max(mc.clip_lo, s_lower / n - r)
        hi = min(mc.clip_hi, s_upper / n + r)

    `variance_process=n` is passed explicitly even though it equals the default, because the
    frozen call is what the protocol quotes. n >= 1 required (MonitorError otherwise); at n == 0
    the caller displays the full range [-1, 1] and does not decide.
    NO running intersection with an earlier band. NO maximisation over prefixes. NO retention."""

class MonitorState:
    """Enrollment-indexed, append-only in the enrollment dimension, updatable in place.

    Internally four parallel lists indexed by enrollment position 0..n-1:
        _lo_h, _hi_h, _lo_s, _hi_s   (floats), plus _collapsed (bool) and _tier (int).
    """
    def __init__(self, mc: MonitorConfig) -> None: ...
    @property
    def n(self) -> int: ...                    # the CURRENT FULL ENROLLED PREFIX N(t)
    def enroll(self, pair: int) -> None:
        """Append one position at [-1, 1] for both scores. Raises MonitorError unless
        pair == self.n + 1 (pairs are enrolled in order, never created out of order)."""
    def update(self, pair: int, enc: PairEnclosure) -> None:
        """Replace the enclosure of an EXISTING enrollment position. Raises MonitorError if
        pair > self.n (a reveal never creates a pair) and EnclosureError if the enclosure widens.
        Idempotent: applying the same enclosure twice changes nothing."""
    def sums(self) -> tuple[float, float, float, float]:
        """[pure] (sum lower_h, sum upper_h, sum lower_s, sum upper_s) over the FULL prefix.
        Implemented as math.fsum over the lists, recomputed at every look — not an incremental
        accumulator — so that replay and live computation are bit-identical regardless of order."""
    def bands(self) -> tuple[Band, Band] | None:
        """(band_h, band_s) at n = self.n, or None when n == 0."""
    def snapshot(self) -> dict:
        """JSON-ready dict for the `monitor_update` body (section 4)."""

@dataclass(frozen=True)
class Decision:
    kind: Literal['deploy_candidate', 'harm_keep_incumbent', 'horizon_no_decision']
    n: int; band_h: Band; band_s: Band; rule_id: str = 'nm_guarded_v3'

def decide(state: MonitorState, mc: MonitorConfig) -> Decision | None:
    """[pure] THE decision function, evaluated on the CURRENT prefix only.

        n = state.n
        if n == 0 or n < mc.n_min:   -> None        (except the horizon check below)
        bh, bs = state.bands()
        if bh.hi < 0.0:                  -> harm_keep_incumbent          # U_h < 0
        if bh.lo > 0.0 and bs.lo > -mc.delta: -> deploy_candidate        # L_h > 0 and L_s > -delta
        if n >= mc.n_max and every pair collapsed: -> horizon_no_decision
        else -> None

    Order is frozen (harm first). The two cannot hold at one prefix (lo <= hi), the order is fixed
    anyway. Comparisons are strict, in float64, on the clipped endpoints. The harm tail is the
    HIERARCHY tail only: `U_s < -delta` is computed and logged and NEVER decides anything
    (COORDINATOR rev2 item 1)."""

def replay(events: Sequence[Mapping], cfg: dict, trial: str) -> list[dict]:
    """[pure] Rebuild every look from the chain alone and return one snapshot per look, in order.

    Consumes exactly these event types and nothing else: pair_enrolled, coin_drawn,
    arm_assigned_by_decision, llm_request, llm_response, llm_error, episode_revealed, decision,
    traffic_switch. It reconstructs each EpisodeView (including `ell` via
    lab_enclosure.certified_elapsed from the worker stamps carried in llm_request/llm_response)
    and applies enroll/update in event order.

    A look is emitted for exactly the evaluation triggers of protocol 8.3 and for nothing else:
    every pair_enrolled ('enroll'); every pre-decision episode_revealed ('reveal'); every
    llm_request/llm_response/llm_error of a PENDING episode of an enrolled pair that RAISES that
    episode's `ell` ('call'); one per resume boundary ('resume'); and a post-decision drain reveal
    of a pre-decision pair ('drain', which updates the enclosure and emits a snapshot but never a
    decision). A call event that does not raise `ell`, and every metrics_scrape, server_* and
    anchor* event, produce NO look — this is the same closed trigger set the orchestrator uses, so
    the element-wise comparison below can never fail on cadence alone (audit B3/B6).

    Post-decision reveals (`post_decision: true` on episode_revealed) are IGNORED: the decision
    prefix is closed at the crossing. A pre-decision pair that resolves after the decision DOES
    update its enclosure (guidance 7: every enrolled pair is finished under its original
    assignment) but produces no new look and cannot create a second decision.

    The caller (lab_verify_log) compares this list element-wise with the logged monitor_update
    bodies: ints exactly, floats by repr() on the same platform and by 1e-12 elsewhere."""

def radius_table(ns: Sequence[int], mc: MonitorConfig) -> list[dict]:
    """[pure] [{'n': n, 'radius': r, 'alpha_gate': ..., 'rho': ...}, ...] for the freeze bundle."""
```

**Float determinism.** `sums()` uses `math.fsum` over the enrollment-ordered list and is recomputed from
scratch at every look. This makes the live value and the replayed value identical bit for bit, which is
what `monitor.replay` asserts exactly rather than within a tolerance. Never keep a running `+=`
accumulator.

**What is NOT in this module, by instruction:** `winstats.betting_log_e_ternary` (root guidance:
"betting gates are not used as the decision rule and are never fed partial scores"). The betting read-out
exists only in `build_live_ab_results.py`, computed once on the final completed scores, labelled post hoc,
with no error-control claim. A test greps `lab_monitor.py`, `lab_reference_rule.py` and
`lab_orchestrator.py` for `betting` and fails on a hit.

---

### 3.8b `lab_reference_rule.py` — G1 (the second code path; protocol 8.9)

Permitted imports: **stdlib + `numpy` + `winstats` only.** **Forbidden: every `lab_*` module**, including
`lab_common`, `lab_monitor` and `lab_enclosure` — the point of this file is that a defect in G3's core
cannot reach it. It re-implements the enclosure enumeration, the sums, the band and the decision from the
protocol text, reading a list of already-parsed chain events. Owned by **G1**, written against protocol
sections 6.2, 6.3, 7.5 and 8.1-8.4 and against nothing else. It is **decision-defining code**: it is in the
freeze bundle with its own SHA-256 (`monitor.reference_rule_sha256`), it can never be amended, and a proven
defect in it is protocol 6.4 row 24 (claims 2-5 and 7 dropped for every affected trial).

```python
@dataclass(frozen=True)
class RefLook:
    trigger: str            # 'enroll' | 'reveal' | 'call' | 'resume' | 'drain'
    n: int
    sum_lower_h: float; sum_upper_h: float
    sum_lower_s: float; sum_upper_s: float
    radius: float
    L_h: float; U_h: float; L_s: float; U_s: float
    action: str             # 'none' | 'harm_keep_incumbent' | 'deploy_candidate' | 'horizon_no_decision'

def looks_from_chain(events: Sequence[Mapping], cfg: Mapping, trial: str) -> list[RefLook]:
    """[pure] The whole rule, rebuilt independently: enrollment-indexed records, the enclosure
    enumeration of protocol 7.5 (including the 0.95 cost certificate), math.fsum over the full
    prefix, winstats.normal_mixture_radius(n, alpha, rho, variance_process=n), the clip to [-1, 1],
    and the decision order harm-then-deploy at n >= n_min. Scores of resolved pairs are computed
    ONLY through winstats.compare. No import of lab_monitor, lab_enclosure or lab_common."""

def shadow_step(events: Sequence[Mapping], cfg: Mapping, trial: str) -> RefLook:
    """[pure] The last look of looks_from_chain(...) — what the orchestrator calls at every
    evaluation to fill `monitor_update.shadow` and to set `shadow.mismatch` (protocol 8.9)."""

def decide_from_chain(events: Sequence[Mapping], cfg: Mapping, trial: str) -> dict:
    """[pure] The NORMATIVE decision of a trial (protocol 8.9): the FIRST prefix n* >= n_min at
    which a condition of 8.4 holds, or abstention. Returns
    {'kind': str, 'n': int|None, 'L_h': float, 'U_h': float, 'L_s': float, 'U_s': float}."""
```

**How the shadow is wired without breaking purity.** `lab_orchestrator` imports `lab_reference_rule` and
calls `shadow_step` on its in-memory copy of the chain after every `monitor.update`/`enroll`, before writing
the `monitor_update`. A difference in `n`, in a sum, in a band endpoint beyond 1e-9 or in the action sets
`shadow.mismatch = true` in that event and takes the `trial_paused(monitor_mismatch)` transition (7.1 row
22b) **before any decision is acted on**. `lab_verify_log` calls `decide_from_chain` after the trial for
`reference_rule.agreement`. An **exception** raised inside `lab_reference_rule` is protocol 6.4 row 17 and
is not repairable by a re-freeze (protocol 6.4 row 24).

---

### 3.9 `lab_client.py` — G4

Permitted imports: stdlib + `requests` + `lab_common` + `lab_worker`'s `Spool` type (imported from
`lab_worker`? no — see below). To avoid a cycle, `Spool` lives in `lab_client` and `lab_worker` imports it.

```python
@dataclass
class Spool:
    """Append-only, fsynced worker spool. The worker's only output channel besides the record file."""
    path: Path
    def __init__(self, path: Path) -> None:
        """Opens O_WRONLY|O_APPEND|O_CREAT. Refuses (SpoolError) if the file already contains a
        terminal `episode_final` line."""
    def write(self, kind: str, body: dict, *, durable: bool = True) -> int:
        """One canonical JSON line {spool_seq, kind, t_wall_ns, t_mono_ns, pid, body}; one
        os.write; fullsync when durable. Returns the byte offset at which the line starts.
        Side effect: file grows. Records the fsync cost in the NEXT line's body['fsync_ms']."""
    def close(self) -> None: ...

@dataclass(frozen=True)
class GoldenReceipt:
    props: dict                    # the whole /props object captured pre-freeze
    generation_settings: dict      # the whole __verbose.generation_settings object
    mask: tuple[str, ...]          # per-request keys compared by their own rule (at least 'seed')
    float_tolerance: float = 1e-6

class LlamaClient:
    """Drop-in replacement for experiments/local_stream/agent.py:OpenAICompatModel.

    `experiments/local_stream/agent.py` stays BYTE-IDENTICAL: run_episode only needs
    `.chat(messages, ctx) -> dict`, `.model` and `.name`.
    """
    name: str = 'llama_cpp'
    model: str                    # the server-side alias; run_episode records it

    def __init__(self, *, base_url: str, alias: str, sampling: dict, spool: Spool,
                 golden: GoldenReceipt, request_timeout_s: float, max_connection_retries: int,
                 server_recovery_s: float, arrival: int, attempt: int, trial: str,
                 worker_index: int,                     # 0 or 1; the seed partition of protocol 5.5
                 session: requests.Session | None = None) -> None: ...

    def chat(self, messages: list[dict], ctx: dict) -> dict:
        """One logical call (possibly several tries). Returns EXACTLY the pilot's dict:
        {'text', 'prompt_tokens', 'completion_tokens', 'tokens_estimated': None, 'call_seconds',
         'retries', 'retry_log', 'finish_reason', 'response_model'}.

        Per try, in this order:
          1. seed = (int.from_bytes(os.urandom(4), 'big') & 0x7FFFFFFE) | worker_index, with
             worker_index in {0, 1} taken from the job (protocol 5.5, finding N6): **the low bit
             carries the worker index**, which partitions the seed space between the two
             uncoordinated worker processes and makes a cross-worker collision impossible. The
             worker checks only its own half of the used-seed set and redraws a value already used;
             0xFFFFFFFF is never produced (the mask makes it unreachable; the check is belt and
             braces). `worker_index` is the SLOT, not the arm, and it is removed from the canonical
             job payload before the T4 identity check (3.12), so the partition can give no arm an
             advantage — PG-8, audit M1.
          2. body = {model: alias, messages, **sampling, seed, stream: False, verbose: True,
             cache_prompt: False}. Every sampler key comes from the frozen `sampling` block; the
             client adds nothing and drops nothing.
          3. spool.write('call_started', {...body_sha256, messages_sha256, seed, call_index, kind,
             try_index, t_c1_ns, t_send_ns...}, durable=True)  <-- BEFORE the POST.
          4. POST base_url + '/chat/completions', timeout=request_timeout_s.
          5. On 200: parse; assert 'usage' and 'timings' present, else raise MalformedResponse;
             compare the receipt (below); write the full request+response body to
             requests/<request_id>.json.gz; spool.write('call_response', {...}, durable=True)
             BEFORE returning.
          6. On requests.ConnectionError / requests.Timeout: spool.write('call_error', ...,
             durable=True); wait min(2*(k+1), 10) s; retry up to max_connection_retries; after the
             last try raise ConnectionFailure. While a server restart is in progress the client may
             wait up to server_recovery_s in total across tries (the wait is inside latency_s).
          7. On any HTTP 4xx/5xx: spool.write('call_error', ...); raise HttpError (NOT retried).
        There is NO token-estimation path: a 200 without `usage` is an error, never an estimate.

        Receipt comparison (protocol 13.2): the WHOLE `__verbose.generation_settings` object is
        compared with golden.generation_settings — exact for ints, strings, bools and lists, within
        golden.float_tolerance for floats, with every key in `mask` compared by its own rule (seed
        must equal the seed sent). Any unknown or missing key is a mismatch. `timings.cache_n == 0`
        and `tokens_cached == 0` are asserted (the receipt for cache_prompt: false). `model` must
        equal the alias. A mismatch raises ReceiptMismatch AFTER the response has been spooled, so
        the episode still completes under intention-to-treat and the orchestrator aborts the trial
        before the next dispatch."""

class ConnectionFailure(LabError): ...
class HttpError(LabError): ...
class MalformedResponse(LabError): ...
```

`ctx['seed']` computed inside `agent.run_episode` is **ignored**; the pilot's colliding formula never
reaches a request.

---

### 3.10 `lab_server.py` — G4

Permitted imports: stdlib + `requests` + `lab_common`. No threads: health is polled by the orchestrator's
loop.

```python
@dataclass(frozen=True)
class ServerSpec:
    server_id: Literal['coder', 't3']
    port: int; alias: str; gguf_path: Path; gguf_bytes: int; gguf_sha256: str
    llama_bin: Path; llama_commit: str; args: tuple[str, ...]; log_path: Path
    n_slots: int; n_ctx: int

def server_argv(spec: ServerSpec) -> list[str]:
    """[pure] The frozen command line (protocol 2.2, verbatim):
      <llama_bin> -m <gguf> --alias <alias> --host 127.0.0.1 --port <p> -np <W>
      -c <W*ctx_slot> --no-kv-unified -ngl 99 --jinja --metrics --no-context-shift --offline
      --no-cache-prompt --cache-ram 0 --slot-prompt-similarity 0.0
      --log-file <log> --log-timestamps
    THREE cache switches, not two: `--no-cache-prompt`, `--cache-ram 0` and
    `--slot-prompt-similarity 0.0` are all structural (critic N7, audit M2). The request field
    cache_prompt is not echoed by the server, so cache deactivation must also be in the argv and
    visible in /props; and without `--slot-prompt-similarity 0.0` the server may reuse a slot's
    prefix for the up-to-four calls of a `self_test_repair` episode, which fires
    `timings.cache_n != 0` and **irreversibly aborts T2 or T1** under protocol 6.4 row 12."""

def start(spec: ServerSpec) -> dict:
    """Popen(server_argv(spec), start_new_session=True, stdout/stderr -> log_path). Poll /health
    until ok or the process exits, up to 600 s. Returns the `server_started` body (section 4).
    Raises ServerIdentityError when any of these differ from the frozen values: alias,
    total_slots, per-slot n_ctx, realpath(model_path), build commit, GGUF bytes+sha256, the
    /props object against the golden one, **or a /props report that slot-prompt similarity is not
    0.0** (the assertion that the third cache switch actually took effect, audit M2).
    Side effects: a child process, a log file."""

def probe(base_url: str, *, timeout: float = 5.0) -> dict: ...      # /props + /v1/models
def health(base_url: str, *, timeout: float = 5.0) -> dict: ...     # /health + /slots busy count
def metrics(base_url: str, *, timeout: float = 5.0, tries: int = 3) -> dict:
    """Scrape /metrics and parse the Prometheus text into
    {'prompt_tokens_total': int, 'tokens_predicted_total': int, 'n_decode_total': int,
     'requests_processing': int, 'requests_deferred': int, 'ok': bool}.
    On timeout/parse failure after `tries`, returns {'ok': False, ...} instead of raising: the
    window is then logged as unreconciled and enrollment continues (PG-10, critic N9)."""

def smoke(base_url: str, spec: ServerSpec, golden: GoldenReceipt, sampling: dict) -> dict:
    """One non-task completion ('Reply with the single word: pong'). Returns the `smoke` sub-object
    of `server_started`. Raises ReceiptMismatch / ServerIdentityError on any deviation."""

def stop(pid: int, *, grace_s: float = 10.0) -> dict:
    """SIGTERM the process group, then SIGKILL after grace_s. Returns {'returncode', 'seconds'}."""

def restart(spec: ServerSpec, golden_props: dict) -> dict:
    """start() again with the identical argv, then compare the full /props with golden_props;
    a difference raises ServerIdentityError (the orchestrator maps it to trial_aborted)."""
```

---

### 3.11 `lab_mock_server.py` — G4

Permitted imports: stdlib only (`http.server`, `json`, `time`, `threading`, `argparse`, `hashlib`).
`ThreadingHTTPServer` is the **one permitted use of threads** in the whole harness: a single-threaded
server cannot exhibit the concurrency the tests need. It is a test double and never runs during a trial.
Specified in full in section 8.

```python
def make_server(scenario: dict, *, port: int = 0) -> tuple[ThreadingHTTPServer, int]: ...
def main(argv: list[str] | None = None) -> int:
    """CLI: --scenario FILE --port N [--alias A] [--state-out FILE]. Runs until SIGTERM.
    --state-out receives the final counter state so tests can assert reconciliation."""
```

---

### 3.12 `lab_worker.py` — G4

Permitted imports: stdlib + `lab_common` + `lab_client` + (via `add_import_paths()`) the pilot's `agent`,
`sandbox`, `verify`. **Forbidden:** `lab_eventlog`, `lab_monitor`, `lab_orchestrator`, `lab_coin`.
A worker never writes the chain and never learns the monitor state.

```python
class Job(TypedDict):
    trial: str; inv: str; arrival: int; attempt: int; pair: int; position: int
    arm: Literal['incumbent', 'candidate']; workflow: Literal['single_shot', 'self_test_repair']
    task_uid: str; server: dict          # {'server_id','base_url','alias'}
    worker_index: int                    # 0 or 1: the SLOT (position 1 -> 0, position 2 -> 1 in the
                                         # randomized phase; the free slot in the follow-up cohort).
                                         # Drives the seed partition of protocol 5.5 and nothing else.
    sampling: dict; limits: dict         # request_timeout_s, max_connection_retries, ...
    paths: dict                          # tokenized: spool, record_dir, request_dir, sandbox_lock
    assignment_seq: int                  # seq of the coin_drawn / arm_assigned_by_decision event
    payload_sha256: str                  # sha256 of this object with the T4-identity keys removed

def canonical_job_payload(job: Job) -> dict:
    """[pure] The job with {'arm','arrival','inv','pair','position','task_uid','worker_index',
    'paths','assignment_seq','payload_sha256'} removed. In T4 the two jobs of a pair must have
    byte-identical canonical payloads; the verifier checks it (PG-14, protocol 12.3). `worker_index`
    is in the removal list because the two jobs of a pair necessarily run in different slots."""

def run_job(job: Job, *, sandbox_lock_path: Path) -> dict:
    """The whole episode, in one process. Steps, in this exact order:

      1. Spool line `job_accepted` {arrival, attempt, arm, pid, inv, t_wall_ns}, durable.
         THIS LINE, not `episode_started`, is the evidence that an attempt began (critic N4).
      2. Build LlamaClient with a Spool on job['paths']['spool'].
      3. Install the host-wide execution lock wrapper: monkeypatch `agent.run_program` with a
         wrapper that takes an exclusive flock on sandbox_lock_path around every call, records
         sandbox_lock_wait_s, and spools a `sandbox_exec` line. The wrapper is installed BEFORE
         `agent` is imported in a way that can be bypassed — a unit test asserts every call path
         goes through it by patching sandbox.run_program with a sentinel that raises if the lock
         is not held.
      4. rec = agent.run_episode(task, job['workflow'], client, cfg_for_agent, meta)  (unchanged
         pilot code; `variant_letter` in the record is legacy and is ignored by everything here).
      5. Write records/<sha256(canonical_json(rec))>.json, fsynced, write-once.
      6. Spool `episode_final` {record_sha256, outcome: {...}, t_start/t_end, n_calls, ...}, durable.
      7. Return the outcome dict. Exit code 0.

    Every exception inside run_episode is already an outcome (the pilot records it and grades the
    last candidate). An exception OUTSIDE run_episode (record write failure, lock failure) is
    spooled as `worker_error` and the process exits 3; the orchestrator treats it as a worker death."""

def main(argv: list[str] | None = None) -> int:
    """CLI: --job <path to job json>. Reads the job, calls run_job, exits 0 / 3.
    stdout and stderr go to the job's log file; nothing is printed to a pipe."""
```

**Episode hard cap.** The orchestrator, not the worker, enforces `episode_hard_cap_s`: it kills the
process group and records the terminal failure. A worker has no timer of its own beyond the client's
per-request timeout.
### 3.13 `lab_orchestrator.py` — G5

Permitted imports: stdlib + `lab_common`, `lab_eventlog`, `lab_coin`, `lab_design`, `lab_data`,
`lab_monitor`, `lab_enclosure`, `lab_reference_rule`, `lab_server`. **Forbidden:** `lab_client` (the worker owns the client),
`lab_verify_log`, `build_live_ab_results`, `numpy` beyond what `lab_monitor` uses internally.
The orchestrator spawns `lab_worker` as a **subprocess**; it does not import it (a test asserts this, so
that a worker crash can never take the orchestrator with it).

```python
@dataclass(frozen=True)
class RunContext:
    trial: str; inv: str; cfg: dict; bundle_sha: str
    paths: TrialPaths; order: list[PairSlot]; tasks: dict[str, Task]
    mc: MonitorConfig; servers: dict[str, ServerSpec]; golden: dict[str, GoldenReceipt]

class RunLock:
    """Exclusive O_CREAT|O_EXCL lock on paths.run_lock holding {pid, inv, argv, t_wall_ns}.
    A lock whose pid is dead is stale and is removed; a live pid raises PreflightError."""

# ---- state machine ---------------------------------------------------------
State = Literal['PREFLIGHT','OPENING','IDLE','ENROLLED','COMMITTED','RUNNING','PARTIAL',
                'LOOK','DECIDED','ANCHOR_BLOCK','SWITCHING','POST_DECISION','DRAINING',
                'PAUSED','CLOSING','ENDED','ABORTED']

def preflight(ctx: RunContext) -> dict:
    """Every refusal before seq 0. Returns the `invocation_started.drift` payload.
    Checks: freeze bundle recomputed from disk == bundle_sha; config sha; roster sha; order sha;
    winstats sha; every harness file sha; GGUF bytes+sha256; llama.cpp commit; hardware allowlist;
    package lock; no ANTHROPIC/OPENAI key variables in the environment; the run lock; free disk
    above the configured floor; **the worktree identity** (real path, HEAD branch and
    `git rev-parse HEAD` equal to the frozen ones — protocol 2.1 guard 1, reason code
    `worktree_identity`); and **clock equivalence** (`perf_counter` and `monotonic` deltas over a
    10 s interval differ by at most `enclosure.clock_equivalence_tolerance_ms` — protocol 7.5
    item 4, reason code `clock_equivalence`).
    A failure raises PreflightError; **before a trial's seq 0** the caller writes
    `preflight_refused` to the PROGRAM chain (the trial chain may not exist yet, critic N1); **at a
    later invocation of an open trial** the same closed reason list is written as
    `invocation_refused` in the trial chain (protocol 6.4 row 21)."""

def run_trial(ctx: RunContext, *, resume: bool = True) -> str:
    """The whole trial. Returns the terminal status ('ended' | 'aborted' | 'paused').
    Single-threaded. Opens the chain, appends trial_started (first invocation only) or
    invocation_started, then loops until a terminal state."""

def step(state: State, ctx: RunContext, world: 'World') -> tuple[State, list[Event]]:
    """[pure-ish] One transition of the table in section 7. `World` is a thin object holding the
    live handles (chain, subprocess objects, monitor state, server handles) so that the transition
    table can be unit-tested with a fake World. Every side effect is performed through World
    methods, never through module-level calls."""

# ---- resume, as a pure function -------------------------------------------
@dataclass(frozen=True)
class ResumePlan:
    phase: Literal['randomizing', 'post_decision', 'ended', 'aborted']
    next_pair: int | None                       # the next pair to enroll, or None
    reenroll_pair: int | None                   # a pair_enrolled without a coin (re_enrolled: true)
    bound_assignments: dict[int, str]           # arrival -> arm, from chain-valid assignment events
    orphan_reveals: list[dict]                  # arrivals revealed from a complete spool
    orphan_rejections: list[dict]               # arrivals whose spool failed an orphan check
    interrupted: list[int]                      # arrivals revealed as terminal failures
    dispatch_after_resume: list[int]            # assigned arrivals with NO job_accepted line (PG-7)
    decision_seq: int | None
    pending_decision_steps: list[str]           # e.g. ['anchor','receipt','traffic_switch']
    monitor_prefix: int
    findings: list[str]

def plan_resume(events: Sequence[Mapping], spools: Mapping[str, list[Mapping]],
                order: Sequence[PairSlot], cfg: dict) -> ResumePlan:
    """[pure] No I/O, no clock, no process inspection. `events` is the verified chain;
    `spools` maps 'ep_<arrival>_<attempt>' to the parsed spool lines (complete lines only).

    Rules, in order:
      1. Every chain-valid `coin_drawn` / `arm_assigned_by_decision` binds. Never a redraw.
      2. A `pair_enrolled` with no coin -> reenroll_pair (re_enrolled: true), then one coin.
      3. Assignment + `episode_revealed`               -> nothing to do, ever.
      4. Assignment + a spool with a complete `episode_final` line whose record hash, request ids,
         body hashes, content hashes, usage, worker pid and inv all match the chain
                                                        -> orphan_reveals (recovered_orphan: true)
      5. Assignment + a spool that exists but fails any check in 4
                                                        -> orphan_rejections + interrupted
      6. Assignment + a spool with a `job_accepted` line but no usable terminal line
                                                        -> interrupted (success 0, error_class
                                                           'interrupted', latency_s = certified ell,
                                                           tokens = tokens_known)
      7. Assignment + NO `job_accepted` line at all     -> dispatch_after_resume: the episode never
         started, so it is dispatched now as its one and only attempt, flagged
         `started_after_resume` with `partner_concurrent` recorded (critic N4; PG-7). This is the
         only case in which a dispatch follows a crash, and it is NOT a re-run: nothing had run.
      8. Orphan reveals are emitted first, in arrival order (frozen tie rule), before any new look.
      9. If a `decision` exists: phase = post_decision, no coin is ever drawn again, and
         pending_decision_steps lists whichever of anchor / receipt / traffic_switch is missing.
     10. monitor_prefix = number of `pair_enrolled` events (NOT the number of reveals).
    """

def worktree_check(ctx: RunContext, world: 'World') -> dict | None:
    """Every `execution.worktree_check_s` seconds (60): recompute the sha256 of every readable
    freeze-bundle file, of every CLOSED chain segment and of `src/winstats.py`, and re-assert the
    worktree path, HEAD branch and HEAD commit. Returns None when everything matches, else the
    observed/expected digest list, which the caller turns into `trial_paused(worktree_drift)`
    (protocol 6.4 row 27, audit B7). A changed CLOSED segment is `trial_aborted(chain_unreadable)`
    and is recorded as an environment event, never as a 12.6 editing finding against the operator."""

def status_snapshot(ctx: RunContext, world: 'World') -> dict:
    """The arm-blind status.json (protocol 14.7): pairs_enrolled, pairs_completed, elapsed_s,
    server ok flags, receipts obtained, terminal_failure_count, phase. NO outcome, NO coin,
    NO statistic, NO band. A test asserts the key set is exactly the frozen list."""

def main(argv: list[str] | None = None) -> int:
    """CLI: --trial T4 --config results/live_ab/freeze/config.json [--resume] [--mock URL]
    [--max-pairs N (mock only)] [--results DIR] [--work DIR]. Exit 0 ended, 1 aborted, 2 paused,
    3 preflight refusal."""
```

### 3.14 `lab_anchor.py` — G5

Permitted imports: stdlib + `requests` + `lab_common`. **Forbidden:** every other `lab_*` module — the
anchor process never reads the chain's meaning, only its bytes.

Critic N13 resolution (`PROTOCOL-GAP PG-12`): the anchor process is a **separate process with a spool**,
exactly like a worker. It never appends to the chain. The orchestrator writes `anchor_spool/requests.jsonl`
and reads `anchor_spool/receipts.jsonl`, and it alone appends `anchor`, `anchor_receipt` and
`anchor_failed`.

```python
class AnchorRequest(TypedDict):
    request_id: str; trial: str; anchor_seq: int; upto_seq: int; upto_h: str
    segment_index: int; segment_bytes: int; segment_sha256: str
    # The trigger enum is exactly config['anchor']['push_triggers'] (6.1), which is
    # config['anchor']['blocking'] plus the one periodic trigger (protocol 12.4 items 4 and 5).
    trigger: Literal['trial_started','every_25_completed_pairs','decision','trial_paused',
                     'trial_resumed','refreeze_authorization','trial_ended','trial_aborted',
                     'operator_action','program_paused','program_resumed','preflight_refused',
                     'plumbing_verdict_fail','erratum','chain_unreadable']
    blocking: bool            # True iff trigger in config['anchor']['blocking']
    publish_segments: bool

class AnchorReceipt(TypedDict):
    request_id: str; ok: bool
    commit: str | None; branch: str | None; pushed: bool
    comment_id: int | None; created_at: str | None; updated_at: str | None
    receipt_sha256: str | None          # sha256 of the identified line in anchors_private
    error_class: str | None             # 'tree_state'|'push'|'api'|'scanner'|'timeout'

def write_anchor_file(paths: TrialPaths, req: AnchorRequest) -> Path:
    """anchors/anchor_<anchor_seq>.json — integers and hex digests only, no URL, no commit id."""

def scan_for_identifiers(paths: Sequence[Path], patterns: Sequence[str]) -> list[dict]:
    """Release-hygiene scanner. Returns hits as {'path': tokenized, 'pattern_class': str,
    'line': int} — never the matched text."""

def commit_and_push(repo: Path, files: Sequence[Path], message_id: str, *,
                    expect_branch: str, expect_parent: str, push: bool) -> dict:
    """git add of EXPLICIT paths only; **assert the worktree real path, the HEAD branch, the
    expected parent commit and a clean index before committing** (protocol 12.4 item 2, the first of
    the two shared-clone guards of protocol 2.1); `git commit`, optional `git push`. Never
    `git add -A`, never a rebase, never a force push, never a reset. A violated assertion returns
    {'ok': False, 'error_class': 'tree_state'} — it does not raise, so the caller can spool the
    failure; on a blocking anchor that becomes `trial_paused(anchor_unavailable)`."""

def post_comment(api: str, issue: int, body: str, token_env: str) -> dict: ...
def serve(paths: TrialPaths, cfg: dict, *, once: bool = False) -> int:
    """The loop: read new lines of anchor_spool/requests.jsonl; for each, write the anchor file,
    run the scanner over the files to be committed, commit/push/comment, append an AnchorReceipt
    line to anchor_spool/receipts.jsonl (durable). Retries a blocking request for up to
    cfg['anchor']['blocking_wait_minutes']; a periodic request is attempted once and its failure
    is spooled immediately. --once processes the backlog and exits (used by tests)."""

def main(argv: list[str] | None = None) -> int:
    """CLI: --trial T1 --config ... [--once] [--local-only] [--dry-run].
    --local-only commits without pushing or commenting; it exists ONLY for the mock dry runs and the
    anchor drill of protocol 12.4 item 10 and is never used in a trial (a trial's blocking anchors
    require real receipts). --dry-run writes receipts with ok=False, error_class='dry_run'."""
```

### 3.15 `build_live_ab_results.py` — G5

Permitted imports: stdlib + `numpy` + `pandas` + `winstats` + `lab_common`, `lab_eventlog`,
`lab_monitor`, `lab_enclosure`. **Forbidden:** `lab_orchestrator`, `lab_worker`, `lab_client`,
`lab_server`, `lab_anchor`, `lab_coin`, `lab_mock_server`. Runs only after the last trial has ended.

```python
def build(trials: Sequence[str], bundle_sha: str, *, results_root: Path, work_root: Path,
          out_dir: Path, mock: bool = False) -> dict:
    """Reads the chains and the record files; writes, per trial:
      monitor_table.csv     one row per look: trigger, n, sums, radius, L_h, U_h, L_s, U_s, flags,
                            shadow mismatch flag
      pairs.csv             one row per enrolled pair: pair, arrivals, uids, stratum, coin bit and
                            raw_hex, arms, z, decisive_tier, d, both timestamps, infra flags,
                            sandbox_lock_wait_s by arm
      episodes.csv          one row per episode: outcome fields, usage, error_class, infra_flag,
                            sandbox_lock_wait_s
      exposure_ledger.json  per phase x arm: episodes, wall seconds, prompt/completion tokens,
                            unknown-usage calls
      decision.json         kind, n, bands, rule_id, receipted times, agreement with
                            lab_reference_rule.decide_from_chain and with the replay
      sensitivity.json      the prespecified descriptive read-outs S-infra, S-int (with the row-11e
                            as-scored variant) and S-lock (protocol 6.4, 8.8 item 8)
      integrity.json        the six tables of protocol 12.6
      posthoc_betting.json  winstats.betting_log_e_ternary on the FINAL completed scores only,
                            labelled 'post hoc descriptive, no error-control claim, not the
                            decision rule' (root guidance; COORDINATOR rev2 item 3)
    and, across trials, program_summary.json. Every file carries 'mock': true and a MOCK banner
    when mock=True or when any input chain's config marks it a dry run."""

def main(argv: list[str] | None = None) -> int: ...
```

The builder never recomputes a decision: it prints the logged `decision` and the verifier's agreement
flag. A defect found in the builder after the freeze is repaired by a **versioned erratum through the
program chain** (`erratum`, program-chain row P10), with both outputs deposited (critic N3 resolution,
`PROTOCOL-GAP PG-13`); a defect in the decision-defining code (`lab_coin`, `lab_monitor`, `lab_enclosure`,
**`lab_reference_rule`**, the failure rules, the config) is **not repairable**, is recorded as
`decision_code_defect` (P11) and drops claims 2-5 and 7 of the affected trials (protocol 6.4 row 24).

### 3.16 Import isolation matrix (enforced by `tests_lab_isolation.py`)

Rows are modules, columns are permitted imports. `.` = forbidden, `x` = permitted, `(s)` = permitted only
through `lab_common.add_import_paths()`.

| module \ may import | stdlib | numpy | pandas | requests | winstats | LS pilot | common | eventlog | data | design | coin | monitor | enclosure | ref_rule | client | server | hostcheck | worker | orch | anchor |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lab_common | x | . | . | . | . | . | — | . | . | . | . | . | . | . | . | . | . | . | . | . |
| lab_eventlog | x | . | . | . | . | . | x | — | . | . | . | . | . | . | . | . | . | . | . | . |
| lab_verify_log | x | x | . | . | x | . | x | x | . | x | . | x | x | x | . | . | . | . | . | . |
| lab_reference_rule | x | x | . | . | x | . | . | . | . | . | . | . | . | — | . | . | . | . | . | . |
| lab_data | x | . | . | x | . | (s) | x | . | — | . | . | . | . | . | . | . | . | . | . | . |
| lab_design | x | x | . | . | . | . | x | . | . | — | . | . | . | . | . | . | . | . | . | . |
| lab_coin | x | . | . | . | . | . | x | x | . | . | — | . | . | . | . | . | . | . | . | . |
| lab_monitor | x | x | . | . | x | . | x | . | . | . | . | — | x | . | . | . | . | . | . | . |
| lab_enclosure | x | x | . | . | x | . | x | . | . | . | . | . | — | . | . | . | . | . | . | . |
| lab_client | x | . | . | x | . | . | x | . | . | . | . | . | . | . | — | . | . | . | . | . |
| lab_server | x | . | . | x | . | . | x | . | . | . | . | . | . | . | . | — | . | . | . | . |
| lab_serving_manifest | x | . | . | . | . | . | x | . | . | . | . | . | . | . | . | . | . | . | . | . |
| lab_hostcheck | x | . | . | . | . | . | x | . | . | . | . | . | . | . | . | . | — | . | . | . |
| lab_mock_server | x | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . |
| lab_worker | x | . | . | x | . | (s) | x | . | x | . | . | . | . | . | x | . | . | — | . | . |
| lab_orchestrator | x | . | . | x | . | . | x | x | x | x | x | x | x | x | . | x | x | . | — | . |
| lab_anchor | x | . | . | x | . | . | x | . | . | . | . | . | . | . | . | . | . | . | . | — |
| build_live_ab_results | x | x | x | . | x | . | x | x | . | . | . | x | x | x | . | . | . | . | . | . |

*Amendment 2026-09-24 (pre-outcome; root `reviews/serving_manifest_binding_ruling_20260924_0153.md`):
the row `lab_serving_manifest`.*
The module holds the serving manifest of protocol 2.2 item 2 (2.1). It may import the standard library and
`lab_common` only. `lab_server` and `lab_orchestrator` may import it (the matrix has no column for it;
`tests_lab_isolation.py` names both edges), and `dryrun_live_ab` imports it to deposit a mock manifest. The
dependency closure it carries is transcribed verbatim from `experiments/live_ab_serving/dependency_closure.py`,
which it does not import; `experiments/live_ab_controls/tests_sm_manifest.py` keeps the two equal statement by
statement.

`lab_hostcheck`'s row is deliberately as narrow as `lab_server`'s: standard library plus `lab_common`,
nothing else. It is imported by the orchestrator and by nothing below it, so the gate cannot see a monitor
state, a coin, a decision or a task, and no defect in it can reach decision-defining code. It is not a
section-3 module, but its public contract is pinned by a signature table in `tests_lab_isolation.py` all
the same, so the orchestrator's two call sites and the event schema's two vocabularies cannot drift away
from it silently.

The isolation statements the protocol requires are consequences of this table and are asserted by name
in `tests_lab_isolation.py`:

* `lab_monitor` imports neither `lab_orchestrator` nor `lab_worker` (nor any I/O module).
* `lab_verify_log` imports neither `lab_orchestrator` nor `lab_worker` (nor `lab_client`/`lab_server`).
* `build_live_ab_results` imports neither `lab_orchestrator` nor `lab_worker`.
* **`lab_reference_rule` imports NOTHING from the `lab_*` namespace at all** — not `lab_monitor`, not
  `lab_enclosure`, not even `lab_common` — so no defect of the live statistical core can reach the shadow
  (protocol 8.9, `AD-7`). Its row is the strictest in the matrix, and that is the point.

Additional asserted facts in the same test: `lab_design` contains none of the identifiers
`urandom|coin|arm|incumbent|candidate`; `lab_monitor`, `lab_reference_rule` and `lab_orchestrator` contain
no `betting`; `lab_orchestrator` does not import `lab_worker`; no module outside `lab_coin` calls
`os.urandom` except `lab_client` (seeds) — and the test whitelists exactly those two call sites; no module
contains the strings `protocol_draft_v2` or `protocol_v3` (audit M16: the superseded drafts must not be
cited by any file), and no module or test name contains `unreachable` (audit B4).

### 3.17 `lab_hostcheck.py` — G5, the host quiescence gate (protocol 5.7)

Protocol 5.7 requires "no other GPU job" for the duration of a trial. The exclusive lock file only ever
excluded a second copy of **this** harness; a model server belonging to another project on the same
machine was invisible to it. That gap is not cosmetic: the frozen hierarchy is `success > cost` with
`cost = latency_s`, so whenever the two arms tie on success the whole composite effect rides on the latency
tier, and a foreign accelerator load corrupts the primary endpoint silently.

**Two halves, deliberately asymmetric.**

* **A hard gate at trial start.** `host_quiescence_gate` runs inside `run_trial` **after** `preflight` and
  **before** `lock.acquire()`. On a finding or a degraded marker it writes `preflight_refused` with
  `checks_failed = ['host_not_quiescent']` **and** `host_quiescence_refused` (P6b) to the **program**
  chain, and returns `aborted`. **The trial chain is never opened.**
* **An observing half inside the trial.** `World.host_scan` emits `foreign_load_detected` (T6b) and never
  raises: a mid-trial refusal would throw away the pairs already enrolled, and the decision about
  contention belongs to the operator and to the analysis, not to a scanner.

**It observes only.** The module never sends a control instruction of any kind to any process it finds —
no termination, no suspension, no priority change. `tests_lab_hostcheck.py` asserts that against the
module's own source at the syntax-tree **and** token level, and asserts that the only external programs it
names anywhere are `ps` and `lsof`. There is deliberately **no configuration key that disables the gate**,
and a test greps for one: the whole point of 5.7 is that the primary endpoint rides on the latency tier,
and a gate an operator can switch off is a gate that will be off.

#### 3.17.1 When the only offender is an OS-owned process (`PREREG_CHECK_2` N.7)

The gate is a hard refusal with no override, and `mediaanalysisd` — Apple's media-analysis daemon — is a
genuine compute-class Metal consumer that appears and disappears without the operator asking it to. It was
absent from one scan on the serving host and present twenty minutes later, at 392 MiB and 8.5 h elapsed.
Every property of the design is individually right and together they had no exit, so the exit is written
down here rather than improvised at 2 a.m. on the night of the first trial.

**The decision: the hard refusal stays.** A daemon that holds a compute-class Metal resource is contending
for the accelerator whether or not Apple owns it, and the trial's primary endpoint cannot tell the
difference. The alternative — a frozen by-detector allowlist of system daemons, admitted below some duty
cycle — was considered and **not** taken: it would add decision-affecting behaviour and a new threshold to
a module whose refusals are the only thing standing between a contended host and a corrupted latency tier,
and the duty-cycle threshold would itself need justifying before any outcome exists.

**The operator procedure, when a scan's only findings are OS-owned:**

1. **Do not bypass, and do not signal it.** There is no override and this document does not create one.
   The operator never terminates, suspends or renices an OS daemon to open a trial; the module may not,
   and neither may the person.
2. **Read the finding.** `elapsed_s` and `rss_bytes` distinguish a short indexing burst from a daemon that
   has been holding the accelerator for hours.
3. **Let it finish.** `mediaanalysisd` is work-driven, not continuous: it runs when there is media to
   analyse and stops when there is not. Waiting is the remedy.
4. **Remove the work that feeds it** before the pre-trial window: no media import, no new content in a
   photo library, no re-index, and no capture or conferencing application running on the serving host.
5. **Re-scan, and require three consecutive clean scans**, each at least 5 minutes apart, inside a
   60-minute window, before opening a trial chain. One clean scan is not evidence of quiescence for an
   intermittent consumer — it is the evidence that produced this finding's absence from the first scan.
   This is an operator requirement introduced by this document; it is not enforced by code.
6. **If it recurs across that window**, the run is **deferred** or moved to a host where the daemon does
   not run. The refusals are already in the program chain as `host_quiescence_refused`; the operator adds
   nothing but the decision, and the coordinator is told.

**What this does not cover.** Item 5 is a pre-trial rule, so it says nothing about a daemon that starts
**during** a trial. Under the current emit set that case is not merely unhandled, it is largely invisible —
see item 2 below.

#### 3.17.2 Open items against this gate, stated rather than closed

None of the following is fixed by this document, and each is named so that the next reader does not
mistake silence for absence.

1. **The resident-size floor reaches only part of what it claims** (`PREREG_CHECK_2` N.8). The module's
   lead sentence says a renamed `llama-server` is detected "at all", qualified two paragraphs later by
   `PROBE_RSS_FLOOR_BYTES = 128 MiB`. On the serving host one of the two real `llama-server` processes was
   resident at **68 MiB**, below the floor, and a reconstruction with both binaries renamed and the Metal
   probe given its best case returned **one** finding rather than two. Either the floor drops or the lead
   sentence narrows; the 68 MiB measurement is the evidence and belongs beside whichever is chosen.
2. **The in-trial half never looks during enrollment** (`PREREG_CHECK_2` N.9). `host_scan` emits at
   `trial_start` and `quiescent` only, and the single `quiescent` scrape site sits inside the
   **post-decision** follow-up dispatch. Across the entire enrollment phase — the phase whose `latency_s`
   measurements are the primary endpoint — the host is observed **once, at tick 0**. A foreign server that
   starts ten minutes into a multi-hour enrollment is invisible until after the decision. Cost is not the
   obstacle: a full scan measured 0.09–0.11 s on a 1,034-process host, against a `pair_boundary` cadence of
   one per pair.
3. **The 16/32-hex carve-out in the summary scrubber is undocumented** (`PREREG_CHECK` C.6). A 16- or
   32-hex token passes through a command summary verbatim while a 40-hex token is redacted, which is the
   inverse of the chain's own string discipline. One inline comment is owed.
4. **A short account name disables the account scrubber silently** (`PREREG_CHECK` C.7). `account_names()`
   drops names shorter than three characters, so on such a host the scrubber is a no-op **and**
   `summary_is_identifier_safe` returns true on the leaked token. The reason for the length rule is
   recorded nowhere.
5. **The dry runs do not exercise the gate at all** (`PREREG_CHECK_2` N.10). `host_scan_is_required`
   returns false for every `sim` invocation, which is right — a simulated run measures no latency — but it
   means `D1`–`D4` contain no `foreign_load_detected` and would not catch a wiring regression. The gate's
   only executable evidence is `tests_lab_hostcheck.py`.
6. **The Metal census is quoted from one unrecorded measurement.** The docstring's "956 processes … 16 at
   or above 128 MiB" no longer matches the serving host (1,034 and 26), and no artifact of the census
   exists in the repository. Re-take and deposit it, or stop quoting counts.

`protocol_FINAL.md` 5.7.1 does not yet point at this subsection, and items 1–6 are not reflected there.
Those edits belong to whoever owns that document.

---

## 4. Event schema (JSON lines)

### 4.1 Envelope

Every line of every chain is one JSON object with exactly these nine keys:

| key | type | meaning |
|---|---|---|
| `seq` | int >= 0 | position in the chain, gapless across segments |
| `type` | enum | one of the event types of 4.3 / 4.4 |
| `t_wall_ns` | int | `time.time_ns()` at append. Client clock; proves nothing by itself |
| `t_mono_ns` | int | `time.monotonic_ns()` at append; comparable only inside one `inv` |
| `inv` | hex32 | invocation id, `uuid4().hex`, constant for one orchestrator process |
| `chain` | enum | `_program`, `_prefreeze`, `T1`, `T2`, `T3`, `T4` |
| `prev` | hex64 | `h` of event `seq-1`; for `seq == 0`, `genesis_prev(bundle, chain)` |
| `body` | object | per-type, section 4.3 / 4.4 |
| `h` | hex64 | `sha256(canonical_json(event without "h"))` |

### 4.2 Canonical serialization and the chain rule

```python
canon(x) = json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
h_i      = sha256(canon({k: v for k, v in event_i.items() if k != 'h'}).encode('utf-8')).hexdigest()
prev_0   = sha256(('live_ab/eventlog-v3|' + anchor_value + '|' + chain_id).encode()).hexdigest()
#          anchor_value = freeze_bundle_sha256 for '_program' and the four trials,
#                       = 'prefreeze' for the '_prefreeze' chain (protocol 12.1)
line_i   = canon(event_i including 'h') + '\n'          # written with ONE os.write
```

Rules, all verified by `read_chain`:

1. **Byte identity.** Re-canonicalising a parsed line must reproduce the raw bytes exactly. This forbids
   any whitespace, key order or unicode-escaping variation and makes the file the canonical object.
2. **Floats** serialize through CPython's `repr` (shortest round-tripping form). NaN and ±Inf are
   forbidden (`allow_nan=False` raises). Integers must be `int`, never `1.0`; `bool` is never accepted
   where an int is declared.
3. **Single writer, append only.** The descriptor is `O_WRONLY|O_APPEND|O_CREAT`; one `os.write` per line;
   no file is ever truncated or rewritten; a closed segment is never reopened.
4. **Durability.** `durable=True` calls `fcntl(fd, F_FULLFSYNC)` before returning. Nothing that the
   protocol calls write-ahead may proceed before that return.
5. **Segments.** `events/seg_%04d.jsonl`. A segment is closed by an `anchor` event, which is by definition
   its last line. The chain continues across segments (`prev` links through the boundary).
6. **Torn regions.** All bytes from the first invalid byte to the end of the last segment form one opaque
   torn region, regardless of newlines inside it. It is legal only when the next valid event is
   `log_recovery` committing to exactly `(offset, length, sha256)`. A chain-valid `coin_drawn` line is
   never part of a torn region, so a coin is void only if its line is inside one.
7. **String discipline** (`PG-11`, protocol 12.2): every string field is an enum member, a lowercase hex
   digest of the declared length (16/32/40/64), a `<TOKEN>/...` path, an ISO-8601 UTC instant, a numeric
   string, a reason code from a closed list, **or a task uid matching
   `^(mbpp|mbpp_full|humaneval)/[0-9]+$` that is present in `roster.json`** (form (e), audit M13 — this is
   what makes `pair_enrolled` valid; the validator checks membership in the roster, not merely the shape).
   No URLs, no commit ids, no account names, no prose. `sha256` digests of texts carry what the text
   itself may not.

Field-type shorthand used below: `int`, `float`, `bool`, `hex64`/`hex40`/`hex32`/`hex16` (lowercase hex of
that many characters), `enum[...]`, `tok` (tokenized path), `iso` (ISO-8601 UTC), `[T]` (list of T),
`{...}` (object with the listed keys), `T?` (that type or `null`). **D** marks a durable append.

### 4.3 Program chain (`results/live_ab/_program/`)

Purpose (critic N1-N3): a chain that exists from the freeze to the end of the last trial, so that
between-trial events have somewhere to live.

| # | type | D | body |
|---|---|---|---|
| P1 | `program_opened` (seq 0) | D | `freeze_bundle_sha256` hex64; `config_sha256` hex64; `rule_block_sha256` hex64; `protocol_sha256` hex64; `prefreeze_head` hex64; `prefreeze_bytes` int; `prefreeze_file_sha256` hex64; `trial_order` [enum]; `n_pairs_max` int; `alpha` {`program` float, `trial` float, `gate` float}; `rho` float; `delta` float; `n_min` int; `rule_id` enum[`nm_guarded_v3`]; `harness_file_sha256` {name: hex64}; `reused_file_sha256` {name: hex64}; `winstats_sha256` hex64; `hardware` obj; `packages` obj; `freeze_receipt` {`comment_id` int?, `created_at` iso?, `receipt_sha256` hex64?} |
| P2 | `trial_opened` | D | `trial` enum; `genesis_prev` hex64; `order_sha256` hex64; `roster_sha256` hex64; `refreezes_in_force` [hex64] |
| P3 | `trial_closed` | D | `trial` enum; `status` enum[`ended`,`aborted`,`not_started`,`chain_unreadable`]; `final_head` hex64?; `final_seq` int?; `end_receipt_id` int?; `reason` enum? |
| P4 | `plumbing_verdict` | D | `trial` enum; `verdict` enum[`PASS`,`FAIL`]; `checks` {check_id: enum[`PASS`,`FAIL`,`DEFECT`,`INFO`]}; `report_sha256` hex64 |
| P5 | `refreeze_authorization` | D | `reason_code` enum (closed list); `files` [{`file` tok, `old_sha256` hex64, `new_sha256` hex64, `diff_sha256` hex64}]; `what_was_known` obj (4.5); `scope` enum[`reporting_code`] — decision-defining code can never appear here (PG-13) |
| P6 | `preflight_refused` | D | `trial` enum; `checks_failed` [enum]; `drift` [{`item` enum, `expected` hex64, `found` hex64}] |
| P6b | `host_quiescence_refused` | D | **protocol 5.7, the trial-start quiescence gate.** `trial` enum; `point` enum (the `metrics_scrape` scrape-point vocabulary); `clean` bool; `scanned` int; `allowlisted` int; `findings` [{`pid` int, `ppid` int, `detector` enum (`lab_hostcheck.DETECTOR_LABELS`), `start_utc` iso, `elapsed_s` int, `rss_bytes` int, `argv_sha256` hex64, `summary_sha256` hex64}]; `degraded` [{`cause` enum (`lab_hostcheck.DEGRADED_CAUSES`), `count` int}]. Written to the **program** chain, beside the `preflight_refused` that carries the reason code `host_not_quiescent`, because the refusal happens before the trial chain's seq 0 and so has nowhere else to live. A finding names its offender by a **closed-vocabulary detector label** and a **digest of its argv**; the command text and the token summary derived from it are never published, because that summary's vocabulary is closed for paths and addresses but not for bare literals. `clean` is redundant with the two lists by construction and `host.record` asserts the agreement, so a body that claims a clean host while carrying findings is a verifier FAIL rather than a reader's problem |
| P7 | `program_paused` / `program_resumed` | D | `reason_code` enum[`plumbing_fail`,`power`,`disk`,`anchor_unavailable`,`worktree_drift`,`operator_discretion`] (**no `thermal`**: the probe was removed with the reason code, protocol 14.6, audit M15); `what_was_known` obj |
| P8 | `anchor` / `anchor_receipt` / `anchor_failed` | D | as T22/T23/T24 below |
| P9 | `log_recovery` | D | as T25 below |
| P10 | `erratum` | D | `scope` enum[`reporting_code`]; `files` [{`file` tok, `old_sha256`, `new_sha256`, `diff_sha256`}]; `output_sha256_before` hex64; `output_sha256_after` hex64; `what_was_known` obj — protocol 6.4 row 23; **no erratum can alter a decision** |
| P11 | `decision_code_defect` | D | `component` enum[`lab_coin`,`lab_monitor`,`lab_enclosure`,`lab_reference_rule`,`failure_rules`,`seed_rule`,`config`]; `trials_affected` [enum]; `claims_dropped` [int]; `what_was_known` obj — protocol 6.4 row 24, **not repairable** |
| P12 | `program_closed` | D | `trials` [{`trial`, `status`, `final_head`}]; `final_head` hex64 |

`plumbing_verdict = FAIL` (critic N2, audit M5) has **two** actions, chosen by the machine, not by the
operator, from the condition list the failing check belongs to (protocol 6.4 rows 22a/22b and
`config['plumbing_fail_conditions']`):

* **list A** (`receipt_mismatch_count_gt_0`, `reconciliation_defect_count_gt_0`,
  `completeness_check_fail_verifier_bookkeeping`): `program_paused(plumbing_fail)`, then a harness-only
  re-freeze of **reporting code only**, then the next trial. A **second FAIL with the same condition id
  stops the program**: later trials need a new protocol version.
* **list B** (`chain_check_fail`, `reference_rule_disagreement`, `t4_payload_non_identity`):
  `program_paused(plumbing_fail)` **and** a `decision_code_defect` (P11) for the affected trial — protocol
  6.4 row 24 applies, claims 2-5 and 7 are dropped for it, and continuation requires a new protocol
  version. A re-freeze may never close a list-B condition, and `refreeze_authorization.scope` cannot
  express one.

Integrity labels and terminal-failure counts are `INFO` and never stop the program.

### 4.4 Trial chain (`results/live_ab/<trial>/`)

| # | type | D | body |
|---|---|---|---|
| T1 | `trial_started` (seq 0) | D | `freeze_bundle_sha256` hex64; `program_head` hex64 (head of the program chain at `trial_opened`); `config_sha256` hex64; `rule_block_sha256` hex64; `order_sha256` hex64; `roster_sha256` hex64; `task_content_sha256` hex64; `n_pairs_max` int; `arms` {`incumbent`: {`workflow` enum, `server_id` enum, `alias` enum, `gguf_sha256` hex64}, `candidate`: same}; `monitor` {`rule_id` enum[`nm_guarded_v3`], `construction` enum[`winstats.normal_mixture_radius`], `alpha_gate` float, `rho` float, `delta` float, `n_min` int, `variance_process` enum[`n`], `clip` [float,float], `prefix` enum[`current_full_enrolled`], `retention` bool(false), `running_intersection` bool(false), `harm_tail` enum[`hierarchy_upper_only`], `tiers` [{`name`,`higher_better`,`relative_tolerance`}], `eligibility` enum[`lower_tiers_require_both_success`]}; `coin` {`source` enum[`os.urandom(8)`], `bit` enum[`byte0&1`], `map` enum[`1->candidate_at_position_1`], `unit` enum[`pair`]}; `seed_rule` obj; `failure_rules_sha256` hex64; `harness_file_sha256` obj; `reused_file_sha256` obj; `winstats_sha256` hex64; `sandbox_profile_sha256` hex64; `golden_props_sha256` obj; `golden_generation_settings_sha256` obj; `hardware` obj; `packages` obj; `llama_cpp_commit_sha256` hex64 (the **hash** of the commit id, never the id — PG-11); `refreezes_in_force` [hex64] |
| T2 | `invocation_started` | D | `pid` int; `argv_sha256` hex64; `argv_tokens` [tok]; `resumed` bool; `head_at_start` hex64; `state` {`pairs_enrolled` int, `pairs_completed` int, `open_attempts` int, `phase` enum}; `boottime_hash` hex64; `drift` [obj] (non-empty drift not covered by a chained authorization is a refusal) |
| T3 | `invocation_refused` | D | `checks_failed` [enum]; `drift` [obj] |
| T4 | `server_started` | D | `server_id` enum; `pid` int; `port` int; `argv_sha256` hex64; `gguf` {`bytes` int, `sha256` hex64}; `props_sha256` hex64; `props_matches_golden` bool; `total_slots` int; `n_ctx` int; `load_seconds` float; `smoke` {`request_sha256` hex64, `receipt_matches_golden` bool, `usage` obj, `timings` obj, `ok` bool} |
| T5 | `server_health` | | `server_id` enum; `ok` bool; `slots_busy` int; `rss_bytes` int; `clock_anomaly` bool |
| T6 | `metrics_scrape` | D at pair boundaries | `server_id` enum; `point` enum[`trial_start`,`pair_boundary`,`before_failed_try`,`after_failed_try`,`restart`,`quiescent`,`trial_end`]; `ok` bool; `counters` {`prompt_tokens_total` int?, `tokens_predicted_total` int?, `n_decode_total` int?, `requests_processing` int?, `requests_deferred` int?} |
| T6b | `foreign_load_detected` | D | **protocol 5.7, the in-trial observing half.** Same body as P6b without `trial`: `point` enum; `clean` bool; `scanned` int; `allowlisted` int; `findings` [obj]; `degraded` [obj]. It is written **whether or not anything was found**, so that a reader can see positively that the host was scanned and was clean rather than inferring it from the absence of an event. Emitted at the `trial_start` and `quiescent` scrape points only; **during the whole enrollment phase that is exactly one scan, at tick 0**, because `quiescent` is reached only inside the post-decision follow-up dispatch. A foreign load that starts after enrollment begins is therefore not recorded until after the decision. This is a known limitation of the emit set, not of the scan, which costs about 0.1 s on a thousand-process host; widening it to `pair_boundary` is an **open** item (3.17, item 2) and is not resolved by this document |
| T7 | `server_down` | D | `server_id` enum; `detected_by` enum[`exit`,`health`]; `returncode` int?; `inflight` [{`arrival` int, `arm` enum}]; `last_counters` obj; `counters_lost` bool |
| T8 | `server_restarted` | D | as T4 plus `props_equal_previous` bool (false ⇒ `trial_aborted(server_identity)`) |
| T9 | `pair_enrolled` | D | `pair` int; `stratum` enum[`S1`,`S2`] (**no `mixed`**, audit B5); `arrivals` [int,int]; `task_uids` [uid,uid] — string form (e) of protocol 12.2: matches `^(mbpp\|mbpp_full\|humaneval)/[0-9]+$` **and** is present in `roster.json`, which the validator checks; `phase` enum[`randomizing`]; `re_enrolled` bool |
| T10 | `coin_drawn` | **D, before any dispatch** | `pair` int; `entropy_source` enum[`os.urandom(8)`]; `raw_hex` hex16; `bit` int; `assignment` {`<arrival>`: enum[`incumbent`,`candidate`]} |
| T11 | `arm_assigned_by_decision` | D | `arrival` int; `arm` enum; `decision_seq` int |
| T12 | `episode_started` | | `arrival` int; `pair` int; `position` int; `arm` enum; `workflow` enum; `server_id` enum; `worker_pid` int; `task_uid` str; `assignment_seq` int; `payload_sha256` hex64; `job_sha256` hex64; `enqueued_ns` int; `dispatched_ns` int; `started_after_resume` bool; `partner_concurrent` bool |
| T13 | `job_accepted` (ingested) | | `arrival` int; `attempt` int; `worker_pid` int; `spool_offset` int; `worker_t_wall_ns` int; `worker_t_mono_ns` int |
| T14 | `llm_request` (ingested) | | `arrival` int; `attempt` int; `call_index` int; `kind` enum[`code`,`tests`,`repair`,`smoke`]; `try_index` int; `request_id` hex32; `server_id` enum; `body_sha256` hex64; `messages_sha256` hex64; `n_messages` int; `prompt_chars` int; `seed` int; `sampling_sent` obj; `t_c1_ns` int; `t_send_ns` int; `spool_offset` int; `spool_fsync_ms` float; `partner_inflight` bool; `recovered` bool |
| T15 | `llm_response` (ingested) | | identifying keys of T14 + `http_status` int; `model_matches_alias` bool; `finish_reason` enum; `usage` {`prompt_tokens` int, `completion_tokens` int, `total_tokens` int, `cached_tokens` int}; `timings` {`cache_n` int, `prompt_n` int, `prompt_ms` float, `predicted_n` int, `predicted_ms` float, `predicted_per_second` float}; `generation_settings_sha256` hex64; `receipt_mismatch` [enum]; `id_slot` int; `truncated` bool; `tokens_cached` int; `tokens_evaluated` int; `tokens_predicted` int; `rendered_prompt_sha256` hex64; `content_sha256` hex64; `client_seconds` float; `t_recv_ns` int |
| T16 | `llm_error` (ingested) | | identifying keys of T14 + `error_class` enum[`timeout`,`connection`,`http_4xx`,`http_5xx`,`malformed`]; `http_status` int?; `error_sha256` hex64; `client_seconds` float; `will_retry` bool; `usage_known` bool(false); `bracketing_scrapes` [int]; `bound_is_joint` bool |
| T17 | `episode_revealed` | D | `arrival` int; `pair` int; `position` int; `arm` enum; `reveal_index` int; `outcome` {`success` int, `latency_s` float, `completion_tokens` int, `prompt_tokens` int, `n_llm_calls` int, `n_failed_calls` int, `connection_retries` int, `n_self_test_executions` int, `n_verifier_executions` int, `repair_rounds` int, `self_test_passed` bool?, `request_timeout_any` bool, `episode_timeout` bool, `verifier_timeout` bool, `truncated_any` bool, `sentinel_seen` bool, `entry_point_defined` bool, `error_class` enum?, `infra_flag` bool}; `record_sha256` hex64; `final_code_sha256` hex64; `verify_program_sha256` hex64; `static_flags` [enum]; `hack_flags` [enum]; `worker_t_start_ns` int; `worker_t_end_ns` int; `verify_seconds` float; `sandbox_lock_wait_s` float; `overlap` {`seconds_with_partner` float, `partner_arm` enum?, `partner_state_at_verify` enum?}; `certified_ell` float; `tokens_known` int; `recovered_orphan` bool; `post_decision` bool |
| T18 | `orphan_rejected` | D | `arrival` int; `attempt` int; `check_failed` enum; `record_sha256` hex64?; `spool_sha256` hex64 |
| T19 | `monitor_update` | | **The body is defined once, here** (protocol 12.2 #16 cites this row; audit M14). `trigger` enum[`enroll`,`reveal`,**`call`**,`resume`,**`drain`**] (the evaluation triggers of protocol 8.3; `call` = an ingested `llm_request`/`llm_response`/`llm_error` that raised a pending episode's `ell`; `drain` = a post-decision reveal of a pre-decision pair, which updates but never decides); `n` int (**the full enrolled prefix**); `n_collapsed` int; `sum_lower_h` float; `sum_upper_h` float; `sum_lower_s` float; `sum_upper_s` float; `radius` float; `L_h` float; `U_h` float; `L_s` float; `U_s` float; `pair_updated` int?; `pair_enclosure` {`h` [float,float], `s` [float,float], `collapsed` bool, `decisive_tier` int}; `flags` {`n_min_ok` bool, `harm` bool, `deploy` bool, `success_guard_ok` bool}; **`shadow`** {`n` int, `L_h` float, `U_h` float, `L_s` float, `U_s` float, `action` enum, `mismatch` bool} (the reference rule of protocol 8.9, so a mismatch is evidenced in the chain); **`readouts`** {`L_s_vs_010` float, `L_s_vs_015` float, `s1_restricted` float?, `completed_prefix` {`n` int, `L_h` float, `U_h` float, `L_s` float, `U_s` float}} (protocol 8.8 items 1, 2 and 6); `sums_fsum` bool(true); `monitor_code_sha256` hex64 |
| T20 | `decision` | **D + blocking anchor** | `kind` enum[`deploy_candidate`,`harm_keep_incumbent`,`horizon_no_decision`]; `rule_id` enum; `n` int; `monitor_seq` int; `radius` float; `L_h` float; `U_h` float; `L_s` float; `U_s` float; `delta` float; `alpha_gate` float; `inflight` [{`arrival` int, `arm` enum}]; `next_unassigned_arrival` int?; `decided_on_resume` bool |
| T21 | `traffic_switch` | D | `decision_seq` int; `arm` enum; `effective_from_arrival` int; `anchor_wait_ms` int; `switch_latency_ms` int |
| T22 | `anchor` (last line of a segment) | D | `anchor_seq` int; `upto_seq` int; `upto_h` hex64; `segment_index` int; `segment_bytes` int; `segment_sha256` hex64; `cumulative_bytes` int; `pairs_enrolled` int; `pairs_completed` int; `records_manifest_sha256` hex64; `server_log_sha256` {server_id: hex64}; `server_log_bytes` {server_id: int}; `trigger` enum; `blocking` bool |
| T23 | `anchor_receipt` | D | `anchor_seq` int; `pushed` bool; `comment_id` int?; `created_at` iso?; `updated_at` iso?; `receipt_sha256` hex64; `commit_sha256` hex64 (**hash of** the commit id) |
| T24 | `anchor_failed` | D | `anchor_seq` int; `error_class` enum[`tree_state`,`push`,`api`,`scanner`,`timeout`,`dry_run`]; `blocking` bool |
| T25 | `log_recovery` | D | `torn_offset` int; `torn_len` int; `torn_sha256` hex64; `segment_index` int; `is_event_prefix` bool; `boottime_changed` bool |
| T26 | `trial_paused` / `trial_resumed` | D + blocking anchor | `reason_code` enum[`power`,`disk`,`server_unrecoverable`,`anchor_unavailable`,`monitor_exception`,`monitor_mismatch`,`worktree_drift`,`plumbing_fail`,`planned`,`operator_discretion`] — the closed list of protocol 14.6; **`thermal` is removed** (it named no probe, audit M15) and `worktree_drift` (protocol 6.4 row 27) and `monitor_mismatch` (protocol 8.9) are named; `what_was_known` obj; for `worktree_drift` also `digests` [{`file` tok, `expected` hex64, `observed` hex64}] |
| T27 | `operator_action` | D | `action` enum; `reason_code` enum; `what_was_known` obj |
| T28 | `usage_reconciliation` | D | `server_id` enum; `window` enum; `window_from_seq` int; `window_to_seq` int; `counter_delta` obj; `client_usage_sum` obj; `residual` {`prompt` int?, `predicted` int?}; `reconciliation_defect` bool; `counters_lost` bool |
| T29 | `server_stopped` | D | `server_id` enum; `pid` int; `returncode` int?; `seconds` float |
| T29b | `deposit_sealed` | D | `deposit_sha256` hex64; `deposit_bytes` int; `n_records` int; `n_spools` int — protocol 12.2 #26. (The name `archive_sealed` is not used: revision 1 C20 removed the private archive; what is sealed is the in-repository **deposit**.) |
| T29c | `publication_withheld` | D | `segment_index` int; `pattern_class` enum — protocol 12.4 item 6: a scanner hit in a segment withholds that segment from the anchor branch while anchoring continues; the segment stays in the deposit with its anchored hash and **no sanitized copy is ever produced** |
| T30 | `invocation_ended` | D | `status` enum; `counts` obj |
| T31 | `trial_ended` / `trial_aborted` | D + blocking anchor | `status` enum; `reason` enum?; `phase` enum; `exposure_ledger` obj (per phase x arm); `reconciliation_totals` obj; `terminal_failures_by_arm` obj; `n_torn_recoveries` int; `longest_unreceipted_span_s` float; `what_was_known` obj; `final_head` hex64 |
| T32 | `server_start_failed` | D | *(Amendment 2026-09-24, pre-outcome; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 1; protocol 5.3 and 12.2 row 28)* `server_id` enum; `kind` enum[`start`,`restart`]; `stage` enum[`gguf`,`serving_manifest`,`launch`,`health`,`identity`,`smoke`]; `findings` [enum] (closed codes: `lab_server.IDENTITY_FINDINGS`, `lab_client.RECEIPT_FINDINGS`, `lab_server.START_FINDINGS`); `pid` int; `returncode` int?; `argv_sha256` hex64; `props_sha256` hex64?; `load_seconds` float; `restart_index` int (0 for a start). Trial chain only. The record is carried by `lab_common.ServerStartFailed(LabError).record`; it is written instead of, never beside, a success-valued T4 or T8 |
| T33 | `worker_resolved` | D | *(Amendment 2026-09-24, pre-outcome; same review, item 3; protocol 14.6 and 12.2 row 29)* `arrival` int; `attempt` int; `pid` int; `state` enum[`exited`,`killed_reaped`,`liveness_unknown`,`alive_unresolved`]; `returncode` int?; `spool_bytes_at_resolution` int; `spool_sha256_at_resolution` hex64. Trial chain only |
| T34 | `anchor_receipt_rejected` | D | *(Amendment 2026-09-24, pre-outcome; root `reviews/eb1_receipt_attribution_review_20260924_0254.md` and `reviews/decision_receipt_metadata_ruling_20260924_0324.md`; protocol 12.4 and 12.2 row 30)* `request_id` hex32?; `reason` enum[`unknown_request`,`stale`,`malformed`,`duplicate`,`conflict`]; `raw_sha256` hex64; `raw_bytes` int. Neither trial-only nor program-only: written wherever anchor events are (also beside P8) |

*Amendment 2026-09-24 (pre-outcome; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` items 1, 3 and 4,
and the rulings of 21:14, 02:54 and 03:24), to rows T3, T17, T22, T23, T29b and T31 and to P6.*
T17 `episode_revealed` gains
`usage_complete` bool and `unknown_usage_calls` int; T22 `anchor` gains `request_id` hex32 (optional in the
schema); T23 `anchor_receipt` gains `request_id` hex32, `anchor_file_sha256` hex64?, `comment_body_sha256` hex64?
and `node_id_sha256` hex64? (all optional; the last three non-null only on a verified decision receipt); T29b
`deposit_sealed` gains `late_unread` [obj] (optional); T31 `trial_ended` / `trial_aborted` gains `completion` obj
and `resolution` obj (optional in the schema, written on every terminal record), and its `reason` gains
`server_restart_cap` and `unresolved_worker` (automatic aborts, protocol 6.4). The preflight check enum shared by
T3 `invocation_refused` and P6 `preflight_refused` gains `golden_objects`. The pure function
`phase_resolution_verdict(...)` is evaluated before every terminal record of a trial; `lab_verify_log` mirrors
it as the FAIL-level check `workers.resolved`, checks T4, T7, T8, T32 and `completion` against protocol 5.3 as
the FAIL-level check `server.lifecycle`, and its FAIL-level check `switch.phase` counts a decision as receipted
only by `lab_eventlog.decision_receipt` (protocol 12.4).

*Amendment 2026-09-24, v3 (pre-outcome; root `reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md`,
`reviews/eb1_eb5_invalid_decision_summary_20260924_1905.md` and
`reviews/decision_receipt_metadata_ruling_20260924_0324.md`): row T35, and rows T23, T28, T29b and T33.*

| # | type | D | body fields |
|---|---|---|---|
| T35 | `abort_owed` | D | *(protocol 6.4 and 12.2 row 31)* `reason` enum (the reasons of T31 `trial_aborted`); `source` enum[`supervision`,`abort_raised`,`run_loop_backstop`,`close_with_open_work`,`resolution_verdict`,`look_guard`]; `decision_logged` bool; `open_arrivals` [int]. Trial chain only. Written by `lab_orchestrator.World.owe_abort` / `write_abort_owed`, once per reason, before the abort's drain; read by `lab_eventlog.no_decision_point` and replayed by `lab_orchestrator.supervision_state` |

T28 `usage_reconciliation` `counter_delta` values are int? (null in a lost-counter window whose counters were never
read); T33 `spool_bytes_at_resolution` int? and `spool_sha256_at_resolution` hex64? (null when the spool could not
be read at resolution); T29b `late_unread` rows carry `bytes_at_resolution` int? and `bytes_found` int?. The pure
function `lab_eventlog.decision_eligibility(...)`, over `lab_eventlog.no_decision_point(...)`, is THE
classification of every look (protocol 6.4): `lab_orchestrator.World` calls it before it writes each T19 look and
decides only at an eligible one; `lab_verify_log` calls it for the FAIL-level check `reference_rule.agreement`
(rules `decision_after_no_decision_point`, `abort_point_missing` and the missed crossing; INFO rows
`NOT_ACTED_ON_restart_cap_before_decision` and `NOT_ACTED_ON_abort_before_decision`); `build_live_ab_results`
writes it to `decision.json` (`eligibility`). A T23 receipt of a decision is chained only after
`lab_orchestrator.anchor_commit_problem` finds its pushed commit bound to its anchor in the anchor repository
(protocol 12.4).

### 4.5 `what_was_known`

Always computed by the harness, never typed by a human:

```json
{"pairs_enrolled": int, "pairs_completed": int, "revealed_by_arm": {"incumbent": int, "candidate": int},
 "L_h": float, "U_h": float, "L_s": float, "U_s": float, "distance_to_harm": float,
 "distance_to_deploy_h": float, "distance_to_deploy_s": float,
 "earlier_trials": [{"trial": str, "status": str, "decision_kind": str, "final_head": "hex64"}]}
```

### 4.6 Ordering invariants (checked by `lab_verify_log`, listed here so G5 implements them and G1 tests them)

1. `pair_enrolled` for pair `i` occurs after both `episode_revealed` of pair `i-1` **and** after the
   `monitor_update` whose `n == i-1` with `n_collapsed == i-1`.
2. `coin_drawn` for pair `i` occurs after `pair_enrolled(i)` and before any `episode_started` of its two
   arrivals; at most one per pair; none after a `decision`; none before the `anchor_receipt` of the
   `trial_started` anchor.
3. Every `episode_started` carries `assignment_seq` pointing at an earlier durable `coin_drawn` or
   `arm_assigned_by_decision` of the same arrival.
4. Exactly one `episode_revealed` per assigned arrival, ever.
5. Every `llm_request` has exactly one `llm_response` or `llm_error` with the same `request_id`, unless the
   attempt ended as a terminal failure.
6. `monitor_update.n` is non-decreasing and increases by exactly 1 at an `enroll` trigger.
6a. There is **exactly one `monitor_update` per evaluation trigger of protocol 8.3** and none anywhere
   else: none at a `metrics_scrape`, none at a `server_*` or `anchor*` event, none in the follow-up cohort.
   A `call`-triggered update exists iff that `llm_request`/`llm_response`/`llm_error` raised the certified
   `ell` of a pending episode of an enrolled pair.
6b. Within one prefix `n`, successive `monitor_update` bodies are **monotone**: `sum_lower_*` never
   decreases and `sum_upper_*` never increases, so `L_j` is non-decreasing and `U_j` non-increasing at that
   prefix (protocol 8.9). A violation is the same defect as a widened enclosure.
7. `decision` is immediately preceded by the `monitor_update` it quotes (`monitor_seq`), and no earlier
   `monitor_update` satisfies the decision rule (first crossing, no retention). A `decision` may quote a
   `call`-triggered update, with `inflight` non-empty (PG-2).
8. `traffic_switch` follows the `anchor_receipt` of the decision anchor; the first
   `arm_assigned_by_decision` follows `traffic_switch`.
9. Post-decision `episode_revealed` events carry `post_decision: true` and are excluded from the monitor.
   A **pre-decision** pair that resolves after the decision updates its enclosure, is included in the pair
   table, and writes a `monitor_update` with `trigger='drain'` — which is an update, not a look: no
   decision function is called at it and it can never create a second decision.

---

## 5. Worker spool format

One spool per attempt: `work/live_ab/<trial>/spools/ep_<arrival>_<attempt>.jsonl`. It is the worker's
only channel to the orchestrator and the recovery source after a crash. It is **not** hash-chained: the
chain is the chronology claim, the spool is evidence that the orchestrator ingests and hashes.

Line envelope (canonical JSON, one `os.write`, fsynced when `durable`):

| key | type | meaning |
|---|---|---|
| `spool_seq` | int | 0-based, gapless within the file |
| `kind` | enum | see below |
| `t_wall_ns`, `t_mono_ns` | int | the **worker's** clocks (`t_mono_ns` comparable within this pid) |
| `pid` | int | worker pid |
| `inv` | hex32 | orchestrator invocation that spawned this worker |
| `arrival`, `attempt` | int | identity, repeated on every line so a line is self-contained |
| `body` | object | per kind |

| kind | durable | body |
|---|---|---|
| `job_accepted` | yes | `arm`, `workflow`, `task_uid`, `job_sha256`, `payload_sha256` — **the evidence that an attempt began** (PG-7) |
| `call_started` | yes, **before the POST** | `call_index`, `kind`, `try_index`, `request_id`, `seed`, `body_sha256`, `messages_sha256`, `n_messages`, `prompt_chars`, `sampling_sent`, `t_c1_ns`, `t_send_ns`, `fsync_ms_prev` |
| `call_response` | yes, **before the text is used** | `request_id`, `http_status`, `usage`, `timings`, `generation_settings_sha256`, `receipt_mismatch`, `id_slot`, `finish_reason`, `truncated`, `content_sha256`, `rendered_prompt_sha256`, `client_seconds`, `t_recv_ns`, `model_matches_alias` |
| `call_error` | yes | `request_id`, `error_class`, `http_status?`, `error_sha256`, `client_seconds`, `will_retry` |
| `sandbox_exec` | no | `purpose` enum[`self_test`,`verify`], `lock_wait_s`, `seconds`, `returncode?`, `timed_out`, `profile_sha256` |
| `episode_final` | yes, **after the record file is fsynced** | `record_sha256`, `outcome` (exactly the `episode_revealed.outcome` object), `final_code_sha256`, `verify_program_sha256`, `t_start_ns`, `t_end_ns`, `verify_seconds`, `static_flags`, `hack_flags` |
| `worker_error` | yes | `stage` enum, `error_sha256` — the worker failed outside `run_episode` |

Ingest rules (orchestrator):

* Read from a stored byte offset; parse **complete lines only**; a trailing incomplete line is ignored and
  re-read next time. A spool is never rewritten or truncated.
* `spool_seq` must be gapless; a gap is a `SpoolError` and the attempt is treated as interrupted.
* `call_started` → chain `llm_request`; `call_response` → `llm_response`; `call_error` → `llm_error`;
  `job_accepted` → `job_accepted`; `episode_final` → `episode_revealed` (durable).
* Certified elapsed `ell = max over lines of (t_e - t_c1)` where `t_c1` is from the first `call_started`
  and `t_e` ranges over every `t_send_ns` and `t_recv_ns`. **No spooled request ⇒ `ell = 0.0`** (critic N5).
* Orphan checks (resume): every `call_started` has a matching chain event or is ingested now; the record
  file named by `episode_final.record_sha256` exists and re-hashes to that value; `pid` and `inv` match
  `episode_started`; `outcome` re-derived from the record equals the spooled `outcome`. Any failure →
  `orphan_rejected` + reveal as `interrupted`.

---

## 6. Frozen configuration (`results/live_ab/freeze/config.json`)

### 6.1 Full key list

This block is **byte-identical to Appendix B of `protocol_FINAL.md`** and is the single canonical key
list for the whole program. G5 assembles `config.json` from it and from nothing else; a freeze test
compares the two blocks after stripping the fences, and `rule_block_sha256` is compared with the hash
computed from the protocol's own frozen tables (audit B1). Every `null` is pinned in the pre-freeze
phase (protocol Appendix A) and no `null` may survive into the freeze bundle.

```json
{
  "experiment": "live_ab",
  "protocol_version": "v3-nm-guarded",
  "rule_id": "nm_guarded_v3",
  "adopts": {"guidance_file": "reviews/arxiv_live_design_guidance.md",
             "guidance_sha256": "a71965986165d56915a557a1a43998d9eb76a4e800dba670281c93720037ad1b"},

  "trials": {
    "T4": {"trial_no": 4, "order": 1, "incumbent": {"workflow": "single_shot", "server": "coder"},
           "candidate": {"workflow": "single_shot", "server": "coder"}},
    "T2": {"trial_no": 2, "order": 2, "incumbent": {"workflow": "single_shot", "server": "coder"},
           "candidate": {"workflow": "self_test_repair", "server": "coder"}},
    "T1": {"trial_no": 1, "order": 3, "incumbent": {"workflow": "self_test_repair", "server": "coder"},
           "candidate": {"workflow": "single_shot", "server": "coder"}},
    "T3": {"trial_no": 3, "order": 4, "incumbent": {"workflow": "single_shot", "server": "coder"},
           "candidate": {"workflow": "single_shot", "server": "t3"},
           "label_suffix": "regime_specific_cross_process_gpu_sharing",
           "deferred_if": ["preflight_rule_failed"]}
  },
  "execution_order": ["T4", "T2", "T1", "T3"],
  "unconditional_execution": true,
  "alpha_not_reallocated_on_deferral": true,

  "monitor": {
    "construction": "winstats.normal_mixture_radius",
    "variance_process": "n",
    "alpha_program": 0.05, "alpha_trial": 0.0125, "alpha_gate": 0.00625,
    "rho": 100.0,
    "delta": 0.03,
    "exploratory_margins": [0.10, 0.15], "exploratory_margins_decide": false,
    "n_min": 100,
    "n_max": null,
    "prefix": "current_full_enrolled",
    "evaluation_triggers": ["pair_enrolled", "episode_revealed", "call_raises_ell", "resume"],
    "non_triggering_events": ["metrics_scrape", "server_health", "server_started", "server_down",
                              "server_restarted", "anchor", "anchor_receipt", "anchor_failed",
                              "program_chain_event"],
    "drain_update_trigger": "drain",
    "clip": [-1.0, 1.0],
    "retention": false, "running_intersection": false, "prefix_envelope": false,
    "maximize_over_prefixes": false,
    "harm_tail": "hierarchy_upper_only",
    "decision_order": ["harm_keep_incumbent", "deploy_candidate"],
    "deploy_if": "L_h_gt_0_and_L_s_gt_minus_delta_at_same_prefix",
    "harm_if": "U_h_lt_0",
    "betting_in_decision_path": false,
    "betting_readout": {"when": "after_trial_end", "input": "final_complete_scores_only",
                        "error_control_claim": false},
    "winstats_sha256": "56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69",
    "reference_rule_sha256": null,
    "shadow_reference_every_evaluation": true
  },

  "hierarchy": [
    {"name": "success", "field": "success",   "higher_better": true,
     "absolute_tolerance": 0.0, "relative_tolerance": 0.0},
    {"name": "cost",    "field": "latency_s", "higher_better": false,
     "absolute_tolerance": 0.0, "relative_tolerance": 0.05}
  ],
  "eligibility_rule": "lower_tiers_require_both_success",
  "tie_rule": "strict_gt_tolerance_so_exact_equality_is_a_tie",

  "enclosure": {
    "start": [-1.0, 1.0],
    "success_formula": "sA_low_minus_sB_high__sA_high_minus_sB_low",
    "cost_certificate": "(1 - 0.05) * ell > L_r + 1e-9",
    "certificate_constant": 0.95,
    "absence_of_failure_is_not_success": true,
    "elapsed_cost_lower_bound_requires_monotonicity": true,
    "collapse_only_on_final_certificate": true,
    "collapse_cases": ["both_episodes_revealed", "enumeration_leaves_one_feasible_value"],
    "clock_equivalence_tolerance_ms": 1
  },

  "roster": {
    "sources": {"mbpp_sanitized": {"bytes": 255053, "sha256": "ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9",
                                   "revision": "f82046ba5aabbbb427dbfd38a254d26bff08b533"},
                "humaneval":      {"bytes": 44877,  "sha256": "b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef",
                                   "revision": "463c980b59e818ace59f6f9803cd92c749ceae61"},
                "mbpp_full":      {"bytes": 563743, "sha256": "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f",
                                   "revision": "f82046ba5aabbbb427dbfd38a254d26bff08b533"}},
    "strata": ["S1", "S2"],
    "pairing": "stratified_no_mixed_pair",
    "n_pairs_rule": "floor(n_S1 / 2) + floor(n_S2 / 2)",
    "exclusion_rules": ["out_of_design_smoke_task", "duplicate_prompt", "no_entry_point",
                        "reference_fails_verify", "reference_timeout", "unparsable"],
    "smoke_tasks": ["mbpp_full/39", "mbpp_full/122", "mbpp_full/522", "mbpp_full/547",
                    "mbpp_full/869", "mbpp_full/966"],
    "uid_pattern": "^(mbpp|mbpp_full|humaneval)/[0-9]+$",
    "n_S1": null, "n_S2": null, "n_total": null, "n_pairs": null,
    "roster_sha256": null, "task_content_sha256": null
  },
  "design_seed_base": 60260919,

  "coin": {"source": "os.urandom(8)", "bit": "byte0&1", "raw_hex_logged": true,
           "map": "1->candidate_at_position_1", "unit": "pre_enrolled_pair",
           "binding_on_resume": "every_chain_valid_line", "never_redrawn": true,
           "selftest": {"n": 10000, "lo": 4850, "hi": 5150}},

  "seed_rule": {"source": "os.urandom(4)", "mask": "0x7FFFFFFE", "low_bit": "worker_index",
                "forbidden": ["0xFFFFFFFF"], "unique_within_worker_half": true,
                "unique_across_program": true, "logged_before_post": true,
                "duplicate_is": "logged_defect_no_outcome_effect"},

  "servers": {
    "coder": {"port": 8091, "alias": "qwen2.5-coder-7b-instruct-q4km",
              "hf_repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
              "hf_revision": "13fb94bfda8c8cf22497dc57b78f391a9acb426a",
              "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "bytes": 4683073536,
              "sha256_expected": "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c",
              "sha256_recomputed": null, "license": "apache-2.0",
              "license_evidence_sha256": "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
              "license_evidence_kind": "licence_blob", "license_evidence_bytes": 11343},
    "t3":    {"port": 8092, "alias": "t3-candidate",
              "hf_repo": "ibm-granite/granite-3.3-8b-instruct-GGUF",
              "hf_revision": "e40e9dd739c7be00fa965c16ce167088190ce114",
              "file_rule": "exactly_one_non_split_Q4_K_M",
              "file": "granite-3.3-8b-instruct-Q4_K_M.gguf", "bytes": 4942873344,
              "sha256_expected": "77bcee066a76dcdd10d0d123c87e32c8ec2c74e31b6ffd87ebee49c9ac215dca",
              "sha256_recomputed": null, "license": "apache-2.0",
              "license_evidence_sha256": "3caa21957f57266158c22853e09c7d7d066cfcc9d003e31c8daacf930f9aabb9",
              "license_evidence_kind": "model_card_declaration", "license_evidence_bytes": 460,
              "license_evidence_kind_note": "NOT a licence text. The repository serves no LICENSE at the pinned revision (HTTP 404); these are the retained model-card bytes declaring apache-2.0. Typed explicitly so the pin is never read as a recovered licence file.",
              "fallback": "none_T3_deferred"}
  },
  "llama_cpp": {"commit": "4fea119de30f6a923992780f6fd5ccb0bee5d47d",
                "build_flags_sha256": null, "serving_manifest_sha256": "1edea9b072b9c87ed9d4a0b4d7ad69b8e768d0a10d09d99efc4e64324ad68b0c"},
  "llama_args": ["-np", "2", "-c", "16384", "--no-kv-unified", "-ngl", "99", "--jinja", "--metrics",
                 "--no-context-shift", "--offline", "--no-cache-prompt", "--cache-ram", "0",
                 "--slot-prompt-similarity", "0.0", "--host", "127.0.0.1", "--log-timestamps"],
  "receipt": {"golden_props_sha256": {"coder": null, "t3": null},
              "golden_generation_settings_sha256": {"coder": null, "t3": null},
              "mask": ["seed"], "float_tolerance": 1e-06,
              "assert_cache_n_zero": true, "assert_tokens_cached_zero": true,
              "assert_model_equals_alias": true,
              "assert_props_reports_slot_prompt_similarity_zero": true},

  "sampling": {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "typical_p": 1.0,
               "repeat_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
               "mirostat": 0, "max_tokens": 1024, "cache_prompt": false, "stream": false,
               "verbose": true},

  "execution": {
    "workers": 2,
    "process_model": "one_os_process_per_episode",
    "worker_index_rule": "slot_index_position1_to_slot0",
    "randomized_phase_schedule": "pair_synchronous",
    "post_decision_schedule": "work_conserving",
    "poll_interval_ms": 50,
    "request_timeout_s": null, "request_timeout_rule": "max(180, 30*ceil(4*c_max/30))",
    "max_connection_retries": 2, "retry_backoff_rule": "min(2*(k+1),10)",
    "server_recovery_s": 180, "max_recovery_waits_per_call": 1,
    "sandbox_timeout_s": 10.0, "max_lock_wait_s": 120,
    "episode_hard_cap_rule": "4*(3*request_timeout_s + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60",
    "episode_hard_cap_s": null,
    "episode_hard_cap_is_computed_never_typed": true,
    "max_attempts": 1,
    "hard_cap_outcome": "terminal_failure",
    "interruption_outcome": "terminal_failure_unless_orphan_checks_pass",
    "unstarted_assigned_arrival": "dispatched_on_resume_started_after_resume",
    "health_poll_s": 5, "health_failures_to_down": 3,
    "quiescent_scrape_every_arrivals": 50,
    "metrics_timeout_s": 5, "metrics_tries": 3,
    "worktree_check_s": 60,
    "auto_abort": {"consecutive_infrastructure_failures": 10, "counted_in": "reveal_order"}
  },

  "sandbox": {"timeout_s": 10.0, "cpu_s": 10, "output_cap_bytes": 65536,
              "mem_bytes_requested_not_enforced_on_macos": 2147483648,
              "tmpdir": "<TMP>/labsbx", "host_wide_execution_lock": true,
              "host_work_root": "/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/work/live_ab",
              "host_work_root_note": "FROZEN owner-host path, per reviews/lock_anchor_review_20260923_0348.md. Protocol 5.7 item 1 needs ONE lock inode across trials AND checkouts; a checkout-relative work root would give each clone its own file. Derived paths must never replace this pin.",
              "profile_sha256": "527d267e1c50c4f66a23312e2a836125395367ddd1398ec7f3c79117803c410b",
              "profile_bytes": 646,
              "profile_preimage_note": "TMPDIR- AND INTERPRETER-DEPENDENT BY DESIGN (protocol 5.7 item 2). These 646 bytes hold the owner home, the base-interpreter prefix and the prescribed sandbox base; they resolve only under TMPDIR=<TMP>/labsbx and base interpreter cpython-3.12.13-macos-aarch64-none. Under any other interpreter the profile text, its length and this digest all differ. An interpreter or path change needs a new environment record, not a weakened hash.",
              "profile_base_interpreter": "cpython-3.12.13-macos-aarch64-none",
              "containment_probe_sha256": null},
  "max_repair_rounds": 2,

  "anchor": {"branch": "session60/live-ab-anchors", "issue": 11, "comments_per_trial": 3,
             "comment_triggers": ["trial_started", "decision", "trial_ended"],
             "push_triggers": ["trial_started", "every_25_completed_pairs", "decision",
                               "trial_paused", "trial_resumed", "refreeze_authorization",
                               "trial_ended", "trial_aborted", "operator_action", "program_paused",
                               "program_resumed", "preflight_refused", "plumbing_verdict_fail",
                               "erratum", "chain_unreadable"],
             "blocking": ["trial_started", "decision", "trial_paused", "trial_resumed",
                          "refreeze_authorization", "trial_ended", "trial_aborted",
                          "operator_action", "program_paused", "program_resumed",
                          "preflight_refused", "plumbing_verdict_fail", "erratum",
                          "chain_unreadable"],
             "blocking_wait_minutes": 30, "force_push": false, "timestamp_authority": false,
             "publish_segments_at": ["decision", "trial_ended", "trial_aborted"],
             "sandwich_tolerance_s": 30, "posting_latency_p95_s": 0.8240070836618543,
             "posting_latency_p95_source": "root nearest-rank decision, reviews/resumption_root_disposition_20260923_0348.md: authoritative, no repeat calibration",
             "gap_report_s": 5},

  "integrity_label_rule": {"coin_adjacent_events": 1, "sandwich_violations": 1,
                           "pairs_with_terminal_failure": 3,
                           "coin_adjacency_scope": "randomized_phase_only"},
  "pause_thresholds": {"battery_percent": 20, "free_disk_gb": 5},
  "refreeze": {"scope": ["reporting_code"]},
  "plumbing_fail_conditions": {
    "reporting_code": ["receipt_mismatch_count_gt_0", "reconciliation_defect_count_gt_0",
                       "completeness_check_fail_verifier_bookkeeping"],
    "decision_defining": ["chain_check_fail", "reference_rule_disagreement",
                          "t4_payload_non_identity"],
    "repeat_same_condition_stops_program": true},
  "prefreeze": {"format_conformance_min": 9,
                "conformance_prompts": [
                  {"id": "oodp/1", "benchmark": "out_of_design", "entry_point": "interleave_words",
                   "prompt": "def interleave_words(left: str, right: str) -> str:\n    \"\"\"Return one sentence that alternates the words of two sentences.\n\n    Words are separated by single spaces, and an empty sentence has no words.\n    Take the first word of left, then the first word of right, then the second\n    word of left, and so on. When one sentence has no words left, append the\n    remaining words of the other in their original order. Join the result with\n    single spaces.\n    \"\"\"\n"},
                  {"id": "oodp/2", "benchmark": "out_of_design", "entry_point": "covered_length",
                   "prompt": "def covered_length(stretches: list) -> int:\n    \"\"\"Return the total length of a ruler covered by the given stretches.\n\n    Each item of stretches is a pair (start, end) of integers with start <= end.\n    It covers the part of the ruler from start to end, a length of end - start.\n    Parts covered by more than one stretch are counted once. An empty list\n    covers a length of 0.\n    \"\"\"\n"},
                  {"id": "oodp/3", "benchmark": "out_of_design", "entry_point": "most_named",
                   "prompt": "def most_named(ballots: list) -> str:\n    \"\"\"Return the option named on the most ballots.\n\n    Each ballot is a non-empty string naming one option. When several options\n    share the highest count, return the one whose first ballot comes earliest\n    in the list. Return an empty string when there are no ballots.\n    \"\"\"\n"},
                  {"id": "oodp/4", "benchmark": "out_of_design", "entry_point": "rotate_digits",
                   "prompt": "def rotate_digits(text: str, k: int) -> str:\n    \"\"\"Return text with every character from 0 to 9 replaced by a digit.\n\n    A digit d becomes the digit (d + k) % 10. All other characters are\n    unchanged. k is a non-negative integer.\n    \"\"\"\n"}],
                "calibration_plan": {"repetitions": 5, "smoke_tasks": 6, "workflows": 2,
                                     "models": 2, "concurrency_levels": 2, "episodes": 240},
                "side_by_side_compression_C": {"T1": null, "T2": null, "T3": null, "T4": null}},
  "engineering_acquisition": {"wall_seconds_total": 600, "cleanup_reserve_seconds": 90,
                              "dispatch_cutoff_seconds": 510, "diagnostic_byte_budget": 8388608,
                              "seconds_per_request": 120, "total_generated_tokens": 2048},
  "server_supervision": {"max_supervised_restarts_per_server_per_trial": 3, "on_exceeding": "abort_trial_incomplete"},
  "hardware_allowlist": ["arm64-darwin"], "environment_lock_sha256": "842a7a19d738604fbe665231a593a11f12cc02abfe9b1dc4034bc3817a9081ac"
}
```

### 6.2 The rule block (critic N11)

`rule_block_sha256` hashes exactly these subtrees, and nothing else — **the same list as protocol
Appendix B**: `rule_id`, `trials`, `execution_order`, `monitor`, `hierarchy`, `eligibility_rule`,
`tie_rule`, `enclosure`, `coin`, `seed_rule`, `roster.strata`, `roster.exclusion_rules`, `roster.pairing`,
`roster.n_pairs_rule`, `design_seed_base`, `execution.max_attempts`, `execution.auto_abort`,
`plumbing_fail_conditions`, `integrity_label_rule`. Everything else may be pinned in the pre-freeze phase
without changing the hash. `lab_common.rule_block_sha256` implements this key list verbatim; tests assert
that changing `anchor.blocking_wait_minutes` does not change it, that changing `monitor.delta`,
`hierarchy[1].relative_tolerance`, `enclosure.certificate_constant` or `seed_rule.mask` does, and that the
value equals the rule-block hash computed from the frozen tables of `protocol_FINAL.md` sections 6.2-6.4, 7
and 8 (audit B1).

### 6.3 Keys that may never be amended after the first design outcome

`rule_id`, everything inside `monitor`, `hierarchy`, `eligibility_rule`, `tie_rule`, `enclosure`, `coin`,
`seed_rule`, `design_seed_base`, `roster.*`, `execution.max_attempts`, `execution.auto_abort`,
`execution.worktree_check_s`, `enclosure.clock_equivalence_tolerance_ms`, `integrity_label_rule`,
`plumbing_fail_conditions`, `refreeze.scope`, `execution.request_timeout_s`,
`execution.episode_hard_cap_s`, `execution.server_recovery_s`, `execution.workers`, `sampling`,
`llama_args`, `servers`, `sandbox`, `max_repair_rounds`, `anchor.blocking`, `anchor.push_triggers`,
`anchor.sandwich_tolerance_s`, `anchor.gap_report_s`, `anchor.blocking_wait_minutes`, `pause_thresholds`
(critic N16 and protocol 14.3 add the reporting thresholds by name). A drift check
at every invocation compares the on-disk config's sha256 with `trial_started.config_sha256` and refuses on
any difference not covered by a chained `refreeze_authorization` — which can only ever cover **reporting
code** (`refreeze.scope == ["reporting_code"]`), never a config key.

*Amendment 2026-09-24 (pre-outcome; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` items 2 and 4, and
`reviews/serving_manifest_binding_ruling_20260924_0153.md`;
protocol 14.3):* this list gains `server_supervision` (top level, outside the rule block: bound by
`config_sha256` and `harness_file_sha256[config.json]`, not by `rule_block_sha256`),
`prefreeze.conformance_prompts` and `llama_cpp.serving_manifest_sha256`, the canonical digest of the write-once
artifact `results/live_ab/freeze/serving_manifest.json` (2.2).

---

## 7. Orchestrator state machine

One process, one thread, one `while True:` with a `poll_interval_ms = 50` sleep. Every iteration: (1)
reap finished worker processes, (2) ingest new spool bytes, (3) ingest anchor receipts, (4) poll health on
a 5 s timer, (5) take the transition the table below prescribes.

### 7.1 States and transitions

| # | state | trigger / guard | actions, in order | next | blocking? |
|---|---|---|---|---|---|
| 1 | `PREFLIGHT` | process start | `preflight()`; take `RunLock` | `OPENING` | — |
| 1a | `PREFLIGHT` | any check fails | append `preflight_refused` to the **program** chain (D) | `ABORTED` | — |
| 1b | `PREFLIGHT` | *(Amendment 2026-09-24, pre-outcome; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 1, and `reviews/serving_manifest_binding_ruling_20260924_0153.md`)* on a non-simulated path: a golden file is null, missing, unreadable or does not match its config digest, a golden `model_path` is not tokenized, a `--gguf` path does not tokenize to the golden `model_path`, or a runtime `golden` override is present (check `golden_objects`); the artifact `results/live_ab/freeze/serving_manifest.json` is missing, not a regular canonical file, not the file of `llama_cpp.serving_manifest_sha256` (null refuses) or does not re-verify against the runtime (check `serving_manifest`); `server_supervision` or `execution.health_failures_to_down` is absent or malformed (`preflight_rule_failed`) | before seq 0 append `preflight_refused` with the check to the **program** chain (D), at a later invocation `invocation_refused` (protocol 6.4 row 21); no server is started and nothing success-valued is written | `ABORTED` | — |
| 2 | `OPENING` | chain does not exist | `trial_started` (D); `server_started` per server (D); request `trial_started` anchor, `blocking=True` | `OPENING.wait` | — |
| 2a | `OPENING` | chain exists | `read_chain`; `log_recovery` if torn (D); `invocation_started` (D); `plan_resume`; emit orphan reveals / `orphan_rejected` / interrupted reveals (each D), in arrival order; replay the monitor to `monitor_prefix` | `IDLE`/`PARTIAL`/`POST_DECISION` per plan | — |
| 2b | `OPENING` | drift not covered by a chained authorization | `invocation_refused` (D) | `ABORTED` | — |
| 3 | `OPENING.wait` | `anchor_receipt` for the start anchor | — | `IDLE` | **yes**: no coin before this receipt |
| 3a | `OPENING.wait` | no receipt within `blocking_wait_minutes` | `trial_paused(anchor_unavailable)` (D) | `PAUSED` | — |
| 4 | `IDLE` | `pairs_enrolled < N_P` and no pair pending | `metrics_scrape(pair_boundary)` (D); `pair_enrolled` (D) | `ENROLLED` | — |
| 4a | `IDLE` | `pairs_enrolled == N_P` and all collapsed | `monitor_update`; `decision(horizon_no_decision)` (D) | `DECIDED` | — |
| 5 | `ENROLLED` | always | `lab_coin.draw_and_commit()` → `coin_drawn` (**D, returns only after `F_FULLFSYNC`**) | `COMMITTED` | **yes**: nothing is dispatched until this returns |
| 6 | `COMMITTED` | always | write both job files (`write_json_atomic`, durable; position 1 carries `worker_index: 0`, position 2 `worker_index: 1`); `Popen` both worker processes; `episode_started` ×2; `monitor.enroll(pair)`; `lab_reference_rule.shadow_step`; `monitor_update(trigger='enroll')`; `decide()` | `RUNNING` | — |
| 7 | `RUNNING` | a spool line arrives | ingest → `job_accepted` / `llm_request` / `llm_response` / `llm_error`; then `lab_enclosure.certified_elapsed` for that episode; **if `ell` rose**: rebuild the pair's `EpisodeView`s, `monitor.update(pair, enc)`, `lab_reference_rule.shadow_step`, `monitor_update(trigger='call')`, `decide()` | `RUNNING`, or `LOOK` when `decide()` was called | — |
| 7a | `RUNNING` | the `call`-triggered `decide()` returns a `Decision` | `decision` (**D**, `inflight` non-empty is normal here); request the decision anchor, `blocking=True` | `DECIDED` | — |
| 7b | `RUNNING` | a spool line arrives that does **not** raise `ell` (e.g. `sandbox_exec`), or a `metrics_scrape`, `server_health` or anchor event occurs | ingest only; **no `monitor_update`, no `decide()`** | `RUNNING` | — |
| 8 | `RUNNING` | `episode_final` ingested, or worker exited | `episode_revealed` (**D**); rebuild the pair's `EpisodeView`s; `monitor.update(pair, enc)`; `lab_reference_rule.shadow_step`; `monitor_update(trigger='reveal')`; `decide()` | `LOOK` | — |
| 8a | `RUNNING` | worker exited non-zero with no `episode_final` | `episode_revealed` with `error_class='worker_died'`, `success=0`, `latency_s=ell`, `tokens=tokens_known` (**D**) | `LOOK` | — |
| 8b | `RUNNING` | `episode_hard_cap_s` exceeded | kill the process group; `episode_revealed` with `error_class='episode_timeout'`, `latency_s=cap` (**D**) | `LOOK` | — |
| 9 | `LOOK` | `decide()` returns `None`, one episode still running | — | `PARTIAL` | — |
| 9a | `LOOK` | `decide()` returns `None`, both revealed | — | `IDLE` | — |
| 9b | `LOOK` | `decide()` returns a `Decision` | `decision` (**D**); request the decision anchor, `blocking=True` | `DECIDED` | — |
| 9c | any | *(Amendment 2026-09-24, v3; root `reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md`; protocol 6.4)* before any `monitor_update` is written (rows 2a, 4a, 7, 8, 10, 12), `lab_eventlog.decision_eligibility` over the chain so far finds the look not eligible (a decision is logged, a `drain` look, or a no-decision point precedes it) | the `monitor_update` is written exactly as without the abort; `decide()` is not called and no `decision` is appended; a crossing there is not acted on | as the row that wrote the look | — |
| 10 | `PARTIAL` | as rows 7, 7a, 7b, 8, 8a, 8b for the remaining episode | — | `LOOK` | — |
| 11 | `DECIDED` | always | stop enrolling; request anchor if not yet requested | `DRAINING` | — |
| 12 | `DRAINING` | a pre-decision episode is still in flight | let it finish under its original assignment; on its `episode_final`: `episode_revealed` (**D**, `post_decision=false`); `monitor.update` and `monitor_update(trigger='drain')` are still written, **but `decide()` is not called again** (the decision prefix is closed at the crossing) | `DRAINING` | — |
| 13 | `DRAINING` | nothing in flight | — | `ANCHOR_BLOCK` | — |
| 14 | `ANCHOR_BLOCK` | `anchor_receipt` for the decision anchor | `traffic_switch` (**D**) | `POST_DECISION` | **yes**: no post-decision dispatch before this receipt |
| 14a | `ANCHOR_BLOCK` | no receipt within `blocking_wait_minutes` | `trial_paused(anchor_unavailable)` (D) | `PAUSED` | — |
| 14b | `ANCHOR_BLOCK` | `kind == 'horizon_no_decision'` | no switch; go to `CLOSING` after the receipt | `CLOSING` | **yes** |
| 14c | `ANCHOR_BLOCK` | *(Amendment 2026-09-24, pre-outcome; root `reviews/eb1_receipt_attribution_review_20260924_0254.md` and `reviews/decision_receipt_metadata_ruling_20260924_0324.md`; protocol 12.4)* a receipt spool line arrives, or a supervision outcome is owed | exactly one chain event per line (D): `anchor_receipt` only when the line's `request_id` is bound to that anchor's durable request and, for the decision anchor, it carries the full external evidence of protocol 12.4; otherwise `anchor_failed` or `anchor_receipt_rejected`, and the anchor stays pending. The servers stay supervised. Row 14 is taken only once `lab_eventlog.decision_receipt` finds the decision receipted; a supervision outcome owed while the decision was provisional is taken then, before any switch (protocol 5.3 case (c)); a decision anchor that came back failed, or no receipt within `blocking_wait_minutes`, is row 14a with the outcome still owed | `ANCHOR_BLOCK` / `POST_DECISION` / `PAUSED` / `ABORTED` | **yes** |
| 15 | `POST_DECISION` | a worker is free and arrivals remain | `arm_assigned_by_decision` (**D**); job file; spawn; `episode_started` | `POST_DECISION` | — |
| 16 | `POST_DECISION` | `episode_final` ingested | `episode_revealed` (**D**, `post_decision=true`); **no monitor update, no look** | `POST_DECISION` | — |
| 17 | `POST_DECISION` | every 50 arrivals | drain both workers; `metrics_scrape(quiescent)` (D) | `POST_DECISION` | — |
| 18 | `POST_DECISION` | no arrivals remain and nothing in flight | — | `CLOSING` | — |
| 19 | any | `ReceiptMismatch` or served-alias mismatch | finish and reveal the episode (ITT), then `trial_aborted(receipt_mismatch)` (D) before the next dispatch | `ABORTED` | — |
| 20 | any | `server_restarted.props != golden` | `trial_aborted(server_identity)` (D) | `ABORTED` | — |
| 20a | any | *(Amendment 2026-09-24; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 1)* `lab_server.start` or `lab_server.restart` raises `ServerStartFailed` | `server_start_failed` (D) with the exception's record, never a success-valued T4 or T8; then the rule for its stage (protocol 5.3): `gguf`, `serving_manifest` or `identity` → `trial_aborted(server_identity)` (D); `smoke` → `trial_aborted(receipt_mismatch)` (D), both when the smoke receipt differs from the golden object and when none was obtained (`smoke_transport`, `smoke_no_usage`; the latter is a new automatic abort, protocol 6.4); `launch` or `health` on a supervised restart or a start at resume → `trial_paused(server_unrecoverable)` (D), on the first start → `trial_aborted(infrastructure)` (D; a new automatic abort, protocol 6.4). A refused start call or an exception the start did not convert → `trial_aborted(harness_defect)` (D). A failed restart counts towards the cap (row 21a) | `ABORTED` / `PAUSED` | — |
| 21 | any | 10 consecutive revealed arrivals with `error_class` in {`episode_timeout`,`worker_died`,`interrupted`} or all tries of a call failed, counted in **reveal order** | `trial_aborted(infrastructure)` (D) | `ABORTED` | — |
| 21a | any | *(Amendment 2026-09-24; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 4, and `reviews/restart_cap_estimand_ruling_20260923_2114.md`)* `server_down` on a server whose supervised restart attempts in this trial (`server_restarted` plus `server_start_failed` with `kind` `restart`, counted from the chain) already equal `server_supervision.max_supervised_restarts_per_server_per_trial` (3) | nothing is restarted and nothing new is dispatched; the open attempts drain (the `episode_hard_cap_s` kill still applies) and are revealed (D); every worker is resolved (row 21b); then `trial_aborted(server_restart_cap)` (D) with `completion` + blocking anchor. The case is fixed by the chain at that `server_down` (protocol 5.3): (a) no decision yet → none is taken afterwards, a crossing look is logged unchanged and not acted on; (b) a decision with its chained external receipt → it stands at its `tau`, the follow-up is truncated and counted; (c) a decision awaiting its receipt → the abort waits in `ANCHOR_BLOCK` (row 14c) and is taken only after the receipt, else row 14a pauses with the abort still owed. No replacement trial, no extra pair | `ABORTED` / `PAUSED` | **yes** |
| 21b | `CLOSING`, `ABORTED` | *(Amendment 2026-09-24; root `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 3)* before the terminal record, after the bounded drain, the idle observation of every held server and the deposit seal: `phase_resolution_verdict` does not pass (a worker not confirmed exited, a started call with no terminal event under an unresolved worker, a spool grown or changed past its resolution offset, a held server busy or unobserved) | no `trial_ended`: `trial_aborted(unresolved_worker)` (D) + blocking anchor, whose `resolution` lists every unresolved attempt and unfinished call (usage `null`) and names the reason it superseded | `ABORTED` | **yes** |
| 21c | any | *(Amendment 2026-09-24, v3; root `reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md` items 1 and 2)* a terminal abort becomes owed: supervision owes one (rows 20, 20a, 21a), an `AbortTrial` reaches the run loop, the run loop catches a server exception outside supervision, or the close of an ended trial finds an attempt open and no decision (the resolution verdict of row 21b writes its own after the drain) | `abort_owed` (D) with its `reason`, `source` and open arrivals, once per reason, BEFORE the drain reveals anything (protocol 6.4); every later look is not eligible (row 9c); a resumed invocation replays it and still owes the abort | `ABORTED` / as before | — |
| 22 | any | `MonitorError` / `EnclosureError`, **including one raised inside `lab_reference_rule`** | `trial_paused(monitor_exception)` (D); no decision is ever taken by hand. An exception from the reference rule is additionally a `decision_code_defect` candidate (protocol 6.4 rows 17 and 24) and is never closed by a re-freeze | `PAUSED` | — |
| 22b | any | `shadow.mismatch` is true at any evaluation | `trial_paused(monitor_mismatch)` (D) **before any decision is acted on** (protocol 8.9) | `PAUSED` | — |
| 23 | any | operator graceful stop | finish the pending pair, reveal, look, then `trial_paused(planned)` (D) | `PAUSED` | — |
| 24 | any | battery < 20% or disk < 5 GB (**there is no thermal condition and no `thermal` reason code**, audit M15) | drain the pending pair; `trial_paused(<code>)` (D) | `PAUSED` | — |
| 24b | any | `worktree_check()` returns a difference (every `execution.worktree_check_s` = 60 s) | stop dispatching at once; let in-flight episodes finish into their spools; `trial_paused(worktree_drift)` (D) with the observed and expected digests; a changed **closed** segment instead gives `trial_aborted(chain_unreadable)` (D). Never recorded as evidence of editing (protocol 6.4 row 27, 12.6) | `PAUSED` / `ABORTED` | — |
| 25 | `PAUSED` | pause receipt obtained and condition cleared | `trial_resumed` (D) + blocking receipt | previous state | **yes** |
| 26 | `CLOSING` | always | final `metrics_scrape(trial_end)` (D); `usage_reconciliation` per window (D); write `exposure_ledger.json`; `stop()` servers → `server_stopped` (D); seal the deposit → `deposit_sealed` (D); `invocation_ended` (D); `trial_ended` (D) + blocking anchor | `ENDED` | **yes** on the end anchor |
| 27 | `ABORTED` | always | stop dispatching; let in-flight episodes finish into their spools; `invocation_ended` (D); `trial_aborted` (D) + blocking anchor | terminal | **yes** |

### 7.2 What is fsynced, and when

| point | what | why it must be durable before the next step |
|---|---|---|
| `coin_drawn` | chain line | an unlogged coin may never be used; this is the whole write-ahead argument |
| job file | `jobs/job_<arrival>_<attempt>.json` | the worker's input must survive a crash so the orphan check can compare |
| `job_accepted` | spool line | the evidence that an attempt began (PG-7) |
| `call_started` | spool line | **before** the POST, so a request that was sent is never unrecorded |
| `call_response` / `call_error` | spool line | **before** the text is used and before the next call |
| record file | `records/<sha>.json` | before `episode_final` names it |
| `episode_final` | spool line | before the orchestrator may reveal from it |
| `episode_revealed` | chain line | before the look that consumes it |
| `decision`, `traffic_switch`, `arm_assigned_by_decision` | chain lines | before anything acts on them |
| `pair_enrolled`, `anchor`, `anchor_receipt`, `log_recovery`, pause/resume, ended/aborted | chain lines | ordering invariants and the resume rule depend on them |
| `metrics_scrape` at a pair boundary | chain line | it closes a reconciliation window |

`server_health`, `llm_request`, `llm_response`, `llm_error`, `monitor_update` and `episode_started` are
**not** durable: each is either recomputable from a durable source (the spools, the chain) or pure
telemetry. `monitor_update` is recomputable from the chain by `lab_monitor.replay` and, independently, by
`lab_reference_rule.looks_from_chain`, which is exactly what the verifier does.

### 7.3 Resume is a pure function

```
ResumePlan = plan_resume(verified_chain_events, parsed_spools, frozen_order, config)
```

`plan_resume` reads nothing and writes nothing (section 3.13). The orchestrator's resume path is
therefore: `read_chain` → `plan_resume` → apply the plan, in the plan's order, as durable appends. Two
invocations that start from the same bytes produce the same plan; a test asserts idempotence by running
resume twice and comparing the second run's plan to the empty plan.

The ten rules of `plan_resume` (3.13) resolve every crash point. The three that matter most:

* **Assignment without `job_accepted`** → the episode is *dispatched now*, flagged `started_after_resume`.
  Nothing had run, so this is not a re-run, and it removes the cost-free steering device critic N4 found
  (a killed-before-dispatch pair would otherwise become a free tie). `PROTOCOL-GAP PG-7`.
* **Assignment with `job_accepted` and no usable terminal line** → revealed as
  `interrupted`, `success = 0`, `latency_s = ell`, tokens = known. Nothing is re-run.
* **A chain-valid `coin_drawn`** always binds, whether or not its fsync returned. Only a torn line is void.

---
## 8. Mock server (`lab_mock_server.py`)

The whole program must be dry-runnable with no model and no GPU. The mock implements the llama.cpp
response shape that `lab_client` and `lab_server` depend on, plus scripted latencies, faults and counters.

### 8.1 Endpoints

| method | path | response |
|---|---|---|
| GET | `/health` | `{"status": "ok"}`; 503 `{"error": {"code": 503}}` while a scripted outage is active |
| GET | `/props` | the scenario's `props` object verbatim (so an identity mismatch can be injected): `model_alias`, `model_path`, `total_slots`, `n_ctx`, `build_info`, `chat_template_sha256`, `default_generation_settings` |
| GET | `/v1/models` | `{"object": "list", "data": [{"id": <alias>, "object": "model"}]}` |
| GET | `/slots` | `[{"id": i, "is_processing": bool}, ...]`, length `total_slots` |
| GET | `/metrics` | Prometheus text: `llamacpp:prompt_tokens_total`, `llamacpp:tokens_predicted_total`, `llamacpp:n_decode_total`, `llamacpp:requests_processing`, `llamacpp:requests_deferred` |
| POST | `/v1/chat/completions` | the full non-streamed object, below |

Chat response object (every key the client reads must be present):

```json
{"id": "chatcmpl-<hex16>", "object": "chat.completion", "created": 1758300000,
 "model": "<alias>",                                   
 "choices": [{"index": 0, "message": {"role": "assistant", "content": "```python\n...\n```"},
              "finish_reason": "stop"}],
 "usage": {"prompt_tokens": 312, "completion_tokens": 128, "total_tokens": 440,
           "prompt_tokens_details": {"cached_tokens": 0}},
 "timings": {"cache_n": 0, "prompt_n": 312, "prompt_ms": 120.0, "predicted_n": 128,
             "predicted_ms": 900.0, "prompt_per_second": 2600.0, "predicted_per_second": 142.2},
 "__verbose": {"generation_settings": {"seed": 12345, "temperature": 0.7, "top_p": 0.95,
                 "top_k": 0, "min_p": 0.0, "typical_p": 1.0, "repeat_penalty": 1.0,
                 "presence_penalty": 0.0, "frequency_penalty": 0.0, "mirostat": 0,
                 "n_predict": 1024, "samplers": ["penalties","top_k","top_p","min_p","temperature"],
                 "chat_format": "Content-only"},
               "id_slot": 0, "tokens_predicted": 128, "tokens_evaluated": 312,
               "tokens_cached": 0, "truncated": false, "stop_type": "eos",
               "prompt": "<rendered prompt>"}}
```

`generation_settings` echoes the request's sampler fields merged with the scenario's `defaults`, which is
what makes the golden-object comparison meaningful. `seed` echoes the request's seed.

### 8.2 Scenario file

```json
{
  "alias": "qwen2.5-coder-7b-instruct-q4km",
  "props": { ... },                        
  "defaults": { ... },                     
  "tasks_path": "<TMP>/dryrun/tasks.json", 
  "total_slots": 2,
  "tokens": {"prompt_per_char": 0.25, "completion_code": 180, "completion_tests": 60,
             "completion_repair": 200},
  "rate_tokens_per_s": 120.0,              
  "latency_model": "tokens / (rate / max(1, active_slots))",
  "outcomes": {"single_shot": {"p_good": 0.55}, "self_test_repair": {"p_good": 0.55,
               "p_repair_fixes": 0.25, "p_selftest_fails": 0.40}},
  "outcome_seed": 20260919,
  "count_cancelled_tokens": true,
  "faults": [
    {"match": {"uid": "mbpp/12", "kind": "code"},               "do": "timeout", "sleep_s": 400},
    {"match": {"uid": "mbpp/14", "kind": "repair", "try": 1},   "do": "http", "status": 500},
    {"match": {"uid": "mbpp/18", "kind": "code"},               "do": "reset"},
    {"match": {"uid": "mbpp/20", "kind": "code"},               "do": "malformed"},
    {"match": {"uid": "mbpp/22", "kind": "code"},               "do": "no_usage"},
    {"match": {"uid": "mbpp/24", "kind": "code"},               "do": "length"},
    {"match": {"uid": "mbpp/26", "kind": "code"},               "do": "receipt", "set": {"temperature": 0.8}},
    {"match": {"uid": "mbpp/28", "kind": "code"},               "do": "alias", "set": {"model": "other"}},
    {"match": {"uid": "mbpp/30", "kind": "code"},               "do": "cache_n", "set": {"cache_n": 7}},
    {"match": {"after_requests": 40},                            "do": "exit", "code": 1},
    {"match": {"after_requests": 60},                            "do": "outage", "seconds": 20}
  ]
}
```

Matching is deterministic under concurrency because it keys on `(uid, kind, try)`, not on a global
request index: `uid` is recovered by finding the unique task whose prompt is a substring of the first user
message; `kind` is `tests` when the message set contains the pilot's `TEST_PROMPT` stem, `repair` when it
contains the `REPAIR_PROMPT` stem, else `code`; `try` is a per-`(uid, kind)` counter. `after_requests`
faults key on the global counter and are used only for the supervisor and chaos scenarios.

Fault semantics: `timeout` sleeps past the client's timeout without responding; `reset` closes the socket
without a response; `malformed` returns 200 with `b'{not json'`; `no_usage` returns 200 without the
`usage` object; `length` returns `finish_reason: "length"` and `truncated: true`; `receipt` returns a
`generation_settings` that differs from the golden object; `alias` returns a foreign `model`; `cache_n`
returns a nonzero `timings.cache_n`; `exit` calls `os._exit(code)` (the supervisor must restart it);
`outage` answers `/health` with 503 and refuses completions for N seconds.

### 8.3 Counters

`prompt_tokens_total` and `tokens_predicted_total` increase by the same numbers the response reports, so a
correct harness reconciles to a residual of exactly 0 at a quiescent point. A `timeout` or `reset` fault
adds its generated tokens only when `count_cancelled_tokens` is true — this is the switch that exercises
both branches of the accounting wording (`PG-10`). A restart resets the counters to 0, which is what
`counters_lost` must detect.

---

## 9. Tests

### 9.1 One command

```
cd <REPO> && \
  ./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py' -v
```

`unittest discover` puts `experiments/live_ab` on `sys.path[0]`, which is exactly how the flat modules
import each other. The `lab_` prefix exists so that adding `experiments/local_stream` to `sys.path` (for
`agent`, `sandbox`, `verify`, `data`, `common`) can never shadow a live_ab module. Target runtime for the
whole suite: **under 180 s** (the mock dry runs use `--max-pairs` and a compressed latency model).

### 9.2 Test list, by module group

**G1 — `tests_lab_chain.py`** (`lab_common`, `lab_eventlog`, `lab_verify_log`) and
`tests_lab_isolation.py`:

| test | asserts |
|---|---|
| `test_canonical_bytes_roundtrip` | every written line re-canonicalises to itself, byte for byte |
| `test_float_repr_and_nan` | floats use `repr`; NaN/Inf raise at append time |
| `test_chain_verifies` | a 200-event chain over 3 segments verifies; head matches |
| `test_genesis_bound_to_bundle` | verifying under another bundle hash fails |
| `test_tamper_detected` | flipping one byte in the middle fails |
| `test_deletion_detected` | removing a middle line fails |
| `test_reorder_detected` | swapping two lines fails |
| `test_torn_tail_recovered` | an appended partial line becomes a committed `log_recovery`; the file never shrinks; a second torn region fails |
| `test_torn_region_spans_newlines` | a torn region containing `\n` is treated as one opaque region |
| `test_segment_rules` | every non-final segment ends with `anchor`; a gap in numbering fails; a reopened closed segment fails |
| `test_durable_uses_fullsync` | `durable=True` calls `F_FULLFSYNC` (monkeypatched counter) and returns after it |
| `test_schema_rejects` | a URL, a commit id, an absolute path, prose, a float where an int is declared, an unknown key, a missing key — in every event type |
| `test_schema_accepts_uids` | `pair_enrolled` with roster uids is **accepted** (string form (e)); a uid that matches the pattern but is absent from `roster.json` is **rejected**; `trial_started` is accepted (critic N12, audit M13) |
| `test_reference_rule_is_independent` | `lab_reference_rule` imports no `lab_*` module at all (AST); its `looks_from_chain` reproduces `lab_monitor.replay` on the good fixtures |
| `test_shadow_catches_injected_defects` | a sign slip, a swapped count and a wrong denominator injected into `lab_monitor` are each caught **by the shadow at the first evaluation at which they change anything**, set `shadow.mismatch`, and lead to `trial_paused(monitor_mismatch)` before any decision (protocol 8.9, audit B2) |
| `test_monitor_cadence` | exactly one `monitor_update` per evaluation trigger of protocol 8.3; a `metrics_scrape` (including a quiescent one in the follow-up cohort) produces none, and the verifier PASSes on that chain (audit B3, B6) |
| `test_rule_block_matches_protocol` | `rule_block_sha256(config)` equals the hash computed from the frozen tables of `protocol_FINAL.md` (audit B1) |
| `test_config_blocks_identical` | the JSON block of `ARCHITECTURE_FINAL.md` §6.1 and of protocol Appendix B are byte-identical after stripping the fences |
| `test_tokenize_path` | each root maps to its token; an unknown root raises |
| `test_rule_block_hash` | changing `anchor.pairs` does not change it; changing `monitor.delta` does |
| `test_freeze_bundle_complete` | a missing key, a `None` or an `"unknown"` anywhere raises `FreezeIncomplete` |
| `test_verifier_catches_*` | one test per FAIL row of 3.3, each built from a hand-made defective chain fixture |
| `test_independent_band_agrees` | `_band_independent` equals `lab_monitor.band` on 10,000 random `(n, sums)` |
| `test_plumbing_mode_is_outcome_blind` | two chains differing only in outcomes give identical plumbing reports |
| `test_import_isolation` | the matrix of 3.16, by AST |
| `test_no_betting_in_decision_path` | `lab_monitor.py`, `lab_orchestrator.py` contain no `betting` |
| `test_design_has_no_assignment` | `lab_design.py` contains no `urandom|coin|arm|incumbent|candidate` |

**G2 — `tests_lab_design.py`** (`lab_data`, `lab_design`, `lab_coin`):

| test | asserts |
|---|---|
| `test_source_hashes` | a byte change in any source raises `FrozenMismatch` |
| `test_roster_deterministic` | the same inputs give the same `roster_sha256` and `task_content_sha256` |
| `test_duplicate_prompts_excluded` | a planted duplicate is excluded with the right reason |
| `test_reference_sweep_excludes` | a task whose reference fails `verify` is excluded (uses a planted broken reference, no model) |
| `test_hidden_tests_never_in_prompt` | for every roster task, no `test_list` assert string occurs in `build_user_prompt` output (sweep over the whole roster) |
| `test_order_is_permutation` | each trial's order covers every roster uid exactly once; pairs are disjoint and consecutive |
| `test_order_stratified` | **every pair's two uids share a stratum; there is no mixed pair**; each stratum's odd remainder is a leftover; `n_pairs == n_S1 // 2 + n_S2 // 2` and never `n_total // 2` (audit B5) |
| `test_order_write_once` | rewriting with different content raises `WriteOnceViolation` |
| `test_coin_uses_only_urandom` | with `os.urandom` patched to a fixed stream, the arms follow the stream exactly |
| `test_coin_write_ahead` | a spy on `F_FULLFSYNC` proves the fsync count rose before `draw_and_commit` returned; a patched dispatcher asserts no job file exists before that |
| `test_one_coin_per_pair` | a second `coin_drawn` for one pair fails verification |
| `test_coin_balance_10k` | 10,000 real draws lie in [4850, 5150] |
| `test_orientation_map` | `bit=1` puts the candidate at position 1, `bit=0` reverses |

**G3 — `tests_lab_stats.py`** (`lab_monitor`, `lab_enclosure`) — *the group whose bugs are unrecoverable*:

| test | asserts |
|---|---|
| `test_band_matches_winstats` | `band(n, S, S, mc).lo == max(-1, S/n - winstats.normal_mixture_radius(n, alpha, rho, n))` to the last bit, over a grid of `n` and sums |
| `test_radius_fixture` | `r(92)=0.4950264429325317`, `r(100)=0.4656934...`, `r(295)=0.2287071...`, `r(568)=0.1579515...` (regenerated by `--radius-table`, committed as `testdata/radius_table.csv`; the table also carries an `r(569)` reference row, which is **not** a horizon) |
| `test_clip` | endpoints are clipped to `[-1, 1]` and never outside |
| `test_no_running_intersection` | a path that narrows then widens produces a band that widens too (no memory of an earlier tighter band) |
| `test_no_retention` | a path that crosses at n=120, dips below at n=130 and is evaluated at n=130 does **not** decide |
| `test_first_crossing_only` | `decide` returns at the first admissible look and the orchestrator never re-decides |
| `test_n_min` | no decision below `n_min = 100` however extreme the sums |
| `test_deploy_needs_both` | `L_h > 0` alone does not deploy; `L_s > -delta` alone does not deploy |
| `test_harm_is_hierarchy_only` | `U_s < -delta` with `U_h > 0` decides nothing |
| `test_harm_before_deploy` | the frozen order is applied |
| `test_deploy_threshold_at_scale` | **conditional, never an impossibility** (audit B4): with `Dbar = 0` and `n <= N_P <= 568`, `decide` never returns `deploy_candidate`; **and** with a running success difference just above `r(n) - delta` at the same `n`, it **does** — so abstention on the deploy route is a property of the data, not of the rule. The test name contains no form of the word "unreachable" |
| `test_enroll_update_order` | `enroll` only ever appends position `n+1`; `update` never creates a pair; `update` is idempotent |
| `test_enclosure_starts_full` | an enrolled, unresolved pair is `[-1, 1]` in both scores |
| `test_enclosure_never_widens` | a widening update raises `EnclosureError` |
| `test_enclosure_containment` | over 10,000 random pair histories, the final revealed `(z, d)` lies inside every intermediate enclosure |
| `test_success_enclosure_formula` | `[sA_low - sB_high, sA_high - sB_low]` for all 9 combinations of revealed/pending |
| `test_hierarchy_enumeration` | each case of `hierarchy_enclosure` by construction, including the **`0.95*ell > L_r + 1e-9`** certificate and its boundary (audit B1) |
| `test_two_tiers_only` | `tiers_from_config` returns exactly `[Tier('success'), Tier('cost', higher_better=False, relative_tolerance=0.05)]` for **all four** trials; a config with a third tier, a `n_tiers` key or tolerance 0.10 raises `FrozenMismatch` |
| `test_certificate_collapses_mid_pair` | a binding certificate collapses the hierarchy enclosure to `[sgn, sgn]` with the partner pending, the success enclosure stays open, and `assert_monotone` holds |
| `test_reorder_invariance` | for any admissible permutation of a set of reveal-order events, the records, both enclosure sums and both band endpoints **after the whole set** and the decision (kind and prefix) are identical; the intermediate look sequence is **not** compared (audit M17) |
| `test_equality_is_tie` | exact threshold equality (`|a-b| == tol`) is a tie, in `success` and `latency_s` — the only two tiers |
| `test_joint_failure_is_tie` | both episodes failing gives `z = 0`, `d = 0`, `decisive_tier = -1` |
| `test_terminal_failure_collapses` | a terminal failure reveals `success=0, latency=ell` and collapses the enclosure without widening |
| `test_replay_equals_live` | replaying a synthetic chain reproduces every `monitor_update` exactly (int equality, float `repr` equality) |
| `test_replay_excludes_post_decision` | post-decision reveals do not enter the monitor; a pre-decision pair resolving late updates its enclosure but adds no look |
| `test_fsum_order_independence` | summing in a permuted order gives the identical float |

**G4 — `tests_lab_serving.py`** (`lab_client`, `lab_server`, `lab_mock_server`, `lab_worker`):

| test | asserts |
|---|---|
| `test_one_terminal_line_per_request` | every `call_started` has exactly one `call_response`/`call_error` |
| `test_spool_before_post` | the `call_started` line is on disk (and fsynced) before the socket is written — asserted with a mock that records the file size it can see |
| `test_no_estimation_path` | a 200 without `usage` raises `MalformedResponse`; no token estimate is ever produced |
| `test_receipt_mismatch_*` | a changed temperature, an unknown key, a missing key, a nonzero `cache_n`, a nonzero `tokens_cached`, a foreign alias — each raises `ReceiptMismatch` **after** the response is spooled |
| `test_retry_policy` | timeouts and connection errors retry up to 2 times with the frozen backoff; 4xx/5xx never retry |
| `test_seed_drawn_and_logged` | the seed is in the spool before the POST, is echoed by the receipt, is never `0xFFFFFFFF`, and 100,000 draws have no duplicate above chance |
| `test_seed_partition` | **the low bit equals `worker_index`, and a worker only ever draws from its own half** of the seed space, so a cross-worker collision is impossible (protocol 5.5, audit M1) |
| `test_slot_prompt_similarity_asserted` | `server_argv` contains `--slot-prompt-similarity 0.0`, and `start()` raises `ServerIdentityError` when the golden `/props` does not report it (audit M2) |
| `test_agent_unchanged` | `experiments/local_stream/agent.py` sha256 equals the frozen value; `run_episode` runs end to end against the mock with `LlamaClient` |
| `test_execution_lock` | two workers never run a sandboxed program concurrently (a probe program writes a marker and sleeps; the second must wait); every `run_program` call path holds the lock |
| `test_worker_terminal_states` | worker death, hard cap, `worker_error` each produce the prescribed spool and exit code |
| `test_server_identity_refusals` | a wrong alias, slot count, `n_ctx`, `model_path`, GGUF hash or `/props` each raise `ServerIdentityError` |
| `test_metrics_parse_and_timeout` | the Prometheus text parses; a hanging `/metrics` returns `ok: False` after 3 tries instead of raising |
| `test_mock_scenarios` | every fault kind produces the documented client-side effect |
| reused pilot classes | `tests_local_stream.SandboxTests`, `VerifyTests`, `AgentTests` imported and run unchanged |

**G5 — `tests_lab_e2e.py`** (`lab_orchestrator`, `lab_anchor`, `build_live_ab_results`, dry runs):

| test | asserts |
|---|---|
| `test_pair_synchronous` | pair `i+1` is enrolled only after both reveals of pair `i` and the look at prefix `i`; at most one pair pending, ever |
| `test_out_of_order_reveal` | position 2 may be revealed first; enrollment indices are unaffected |
| `test_look_at_every_trigger` | a look is written at every enroll, every pre-decision reveal, every call event that raises `ell`, and at the resume boundary — and at nothing else; **a certificate that binds at an `llm_response` produces a look and can decide** with the partner still pending (audit B3, PG-1/PG-2) |
| `test_worktree_drift` | an out-of-band file swap during a dry run (a freeze-bundle file, then a closed segment, then a copy of `winstats`) pauses the trial with `worktree_drift` within `worktree_check_s`, produces **no** 12.6 editing finding, and resumes only after the digests match; a wrong `HEAD` branch at start is `preflight_refused(worktree_identity)` (audit B7) |
| `test_switch_sequence` | `decision` → blocking anchor → receipt → `traffic_switch` → first `arm_assigned_by_decision`; no coin after the decision |
| `test_drain_before_switch` | a decision taken while the partner is in flight drains it first; its reveal carries `post_decision: false` and creates no second decision |
| `test_horizon_exhaustion` | at `n = N_P` with everything collapsed, `horizon_no_decision` is logged and no leftover task is enrolled |
| `test_resume_kill_points` | a kill injected after each of `pair_enrolled`, `coin_drawn`, job file written, `job_accepted`, first `call_started`, `call_response`, record written, `episode_final`, first `episode_revealed`, second `episode_revealed`, `monitor_update`, `decision`, decision anchor, `traffic_switch`, and mid-`POST_DECISION`: after each, resume yields a chain that passes `lab_verify_log`, with never a second coin, never a second reveal, never a re-run |
| `test_resume_idempotent` | resuming twice changes nothing |
| `test_two_orchestrators_refused` | the second `RunLock` acquisition raises |
| `test_dispatch_after_resume` | an assignment without `job_accepted` is dispatched once, flagged `started_after_resume` (PG-7) |
| `test_orphan_accept_and_reject` | a complete, matching spool is revealed as `recovered_orphan`; a mismatched one is rejected and revealed as `interrupted` |
| `test_t4_payload_identity` | in a T4 dry run, the two canonical job payloads of every pair are byte-identical |
| `test_auto_aborts` | receipt mismatch, server identity, 10 consecutive infrastructure failures each abort deterministically |
| `test_anchor_spool` | the orchestrator is the only chain writer; `anchor_failed(tree_state)` is produced for a foreign staged file or a wrong branch; a blocking failure maps to `trial_paused(anchor_unavailable)` |
| `test_anchor_prefix` | `git show <commit>:<segment>` bytes hash to the `anchor` event's `segment_sha256` (throwaway git repo under the scratchpad, never the project repo) |
| `test_scanner_withholds` | a planted forbidden pattern withholds that segment while anchoring continues |
| `test_builder_isolation_and_banner` | the builder produces every named file, refuses to recompute a decision, and stamps `MOCK` on dry-run outputs |
| `test_exposure_ledger` | the ledger equals a recount from the chain |
| dry runs (below) | each ends with `lab_verify_log` PASS and an exact replay |

### 9.3 Dry-run scenarios (`dryrun_live_ab.py`, owned by G5)

Each writes to a scratch results dir, stamps `MOCK` on every derived file, and must end with
`lab_verify_log --mode full` PASS and `monitor.replay` equality.

| id | scenario | expected path |
|---|---|---|
| `D1` | T2-like, candidate clearly worse (mock `p_good` 0.55 vs 0.35, 4.5× slower) | `harm_keep_incumbent` at the first admissible look (`n = 100`) |
| `D2` | T1-like, equal success, candidate 4.5× faster, **frozen delta 0.03**, 568 pairs | `horizon_no_decision`: the composite band clears, the success guardrail refuses. This is the declared study outcome and the most important dry run |
| `D3` | T1-like with a **mock-only** `delta = 0.25` | full deploy path: decision, blocking anchor, switch, post-decision ledger. Clearly labelled mock-only; the frozen config is untouched |
| `D4` | T4 A/A, 50 mock seeds, 150 pairs each | no crossing in the large majority; a crossing is printed and investigated, never discarded |
| `D5` | chaos: random kills of workers, mock server and orchestrator every 20-60 s | verifier PASS; zero double coins; zero double reveals; every attempt accounted |
| `D6` | anchor drill in a throwaway git repo under the scratchpad | anchors committed; `git show` prefixes match |
| `D7` | `--radius-table` | writes `results/live_ab/freeze/radius_table.csv` for the freeze bundle |

---

## 10. Module groups, ownership, and how to work without talking

| group | owns (exclusive write access) | may read | depends on | delivers |
|---|---|---|---|---|
| **G1** | `lab_common.py`, `lab_eventlog.py`, `lab_verify_log.py`, **`lab_reference_rule.py`**, `tests_lab_chain.py`, `tests_lab_isolation.py`, `testdata/chains/` | everything **except `lab_monitor.py` and `lab_enclosure.py`, which the author of `lab_reference_rule.py` must not read** (they write it from `protocol_FINAL.md` sections 6.2, 6.3, 7.5 and 8.1-8.4) | nothing (starts first, stdlib only) | the chain, the schema, the verifier, the exception taxonomy, **the reference rule** |
| **G2** | `lab_data.py`, `lab_design.py`, `lab_coin.py`, `tests_lab_design.py`, `testdata/roster_small.json` | G1's interfaces | `lab_common`, `lab_eventlog` | roster, arrival orders, the coin and its write-ahead rule |
| **G3** | `lab_monitor.py`, `lab_enclosure.py`, `tests_lab_stats.py`, `testdata/radius_table.csv`, `testdata/monitor_fixtures.json` | G1's interfaces | `lab_common`, `winstats` | the statistical core: band, enclosures, decision, replay |
| **G4** | `lab_client.py`, `lab_server.py`, `lab_mock_server.py`, `lab_worker.py`, `tests_lab_serving.py`, `testdata/scenario_*.json` | G1's interfaces, the pilot | `lab_common` | serving, spools, episodes |
| **G5** | `lab_orchestrator.py`, `lab_anchor.py`, `build_live_ab_results.py`, `dryrun_live_ab.py`, `config.json`, `tests_lab_e2e.py` | everything | G1-G4 | the state machine, anchors, results, dry runs |

**Nobody edits another group's file.** A needed change to another group's interface is a change to *this
document* first, via the coordinator.

**Parallelism.** G1..G4 start simultaneously against the signatures in section 3 and never import an
unfinished module: G2, G3 and G4 write their own fakes for anything they need from G1 during the first
hours (`lab_eventlog` is ~200 lines and G1 delivers it first). G5 starts by writing `config.json`,
`dryrun_live_ab.py`'s scaffolding and the state-machine skeleton against fake Worlds, and integrates when
G1-G4 land. The integration order is G1 → G2/G3/G4 (parallel) → G5.

**Cross-group fixtures** (the only shared artifacts; each is owned by exactly one group and is
byte-frozen once committed):

| fixture | owner | consumers | content |
|---|---|---|---|
| `testdata/chains/good_T4.jsonl` + `defect_*.jsonl` | G1 | G3, G5 | a valid 400-event chain and one defective variant per FAIL check |
| `testdata/roster_small.json` | G2 | G4, G5 | 24 tasks (16 S1, 8 S2) with references and hidden tests, for dry runs |
| `testdata/radius_table.csv` | G3 | G1, G5 | `n, radius` for `n` in `{1,20,92,100,150,200,295,400,565,568,569,1000}` (568 is the horizon ceiling; 569 is a reference row) |
| `testdata/monitor_fixtures.json` | G3 | G1, G5 | 200 `(n, sums) -> (L, U, decision)` triples, hand-checked |
| `testdata/scenario_*.json` | G4 | G5 | the mock scenarios of section 8.2 |

**Definition of done for a group:** its own test file passes, `tests_lab_isolation.py` passes for its
modules, and its public signatures match section 3 exactly (a signature test in `tests_lab_isolation.py`
uses `inspect.signature` on every public name listed in this document).

---

## 11. PROTOCOL-GAP register

Each entry: the ambiguity an implementer would hit, and the resolution that is now normative. **Every entry
below is resolved by a concrete rule that also appears in `protocol_FINAL.md`, at the section named in the
resolution. Nothing is left "coordinator"; nothing is left to the implementer.**

| id | gap | resolution (and where it lives in the protocol) |
|---|---|---|
| **PG-1** | Look cadence. Guidance 3 says "the current full enrolled prefix `n = N(t)` at every event"; the v2 draft said one look per *completed* pair; the v3 draft said "every reveal-order event", which the state machine did not implement. | **Closed in protocol 8.3**, which now lists the evaluation triggers as a closed set: every `pair_enrolled`; every pre-decision `episode_revealed`; every ingested `llm_request`/`llm_response`/`llm_error` **that raises the certified `ell`** of a pending episode of an enrolled pair; one per resume; plus a non-deciding `drain` update after a decision. A `metrics_scrape` is never a trigger (protocol 7.3 item 3). The state machine (7.1 rows 6, 7, 7a, 7b, 8, 12), `lab_monitor.replay`, the `monitor_update.trigger` enum and the verifier check `monitor.cadence` all use this one set, so the replay's element-wise comparison can never fail on cadence (audit B3). |
| **PG-2** | A decision can therefore occur while the partner episode of pair `n` is still running, which the v2 draft asserted was impossible. | **Closed in protocol 9.1 item 4 and 7.5 items 1 and 5**: a decision **can** be taken with one episode pending, because that is exactly what the cost certificate is for. `decision.inflight` may be non-empty; the orchestrator **drains** the in-flight pre-decision episode (state `DRAINING`) before the traffic switch; its reveal carries `post_decision: false`, updates pair `n`'s enclosure and writes `monitor_update(trigger='drain')`; no second decision is evaluated. The containment audit checks the final score against the enclosure used at the decision. |
| **PG-3** | Protocol 8.9 requires a `lab_reference_rule.py` that is a *different code path* from the live monitor; the earlier module list had one statistical core, which made `monitor_mismatch` unreachable. | **Closed by adding the module** (3.8b, `AD-7`): `lab_reference_rule.py`, owned by **G1**, stdlib + numpy + `winstats` only, importing **no** `lab_*` module, re-deriving enclosures, sums, band and decision from the chain. It is called as the **live shadow** at every evaluation (7.1 rows 6, 7, 8), its values and mismatch flag go into every `monitor_update` (T19), and `lab_verify_log` calls `decide_from_chain` for `reference_rule.agreement`. The replay and `_band_independent` remain as additional post hoc checks. `LIVE_DECISION_INVALID` is raised when the reference decision disagrees in kind or prefix (audit B2). |
| **PG-4** | `n_min = 100` versus the computed crossing index 92. | `n_min` applies to the **enrolled** prefix and is checked before any decision, so the earliest possible decision is `n = 100` (`r(100) = 0.465693`, `L_h = 0.0313` at the pilot effect). Stated in the protocol so no one reads "crosses at 92" as a prediction of the decision index. |
| **PG-5** | The harm tail: guidance 6 allows `U_h < 0`, `U_s < -delta` or either; rev2 fixes the hierarchy tail only. | `harm_keep_incumbent` iff `U_h < 0`. `U_s` is computed and logged at every look and **never decides**. A test asserts it. |
| **PG-6** | Long-lived `multiprocessing` workers with pipes (§5.1) versus subprocess-plus-spool. | One OS process per episode (`AD-1`). The spool is unchanged and remains the recovery source; the pipe disappears. |
| **PG-7** | "Open attempt" is undefined between `coin_drawn` and the first dispatch (critic N4); the natural reading turns a kill into a free tie. | An attempt began iff a fsynced `job_accepted` spool line exists. An assigned arrival with no `job_accepted` is **dispatched on resume** as its one and only attempt, flagged `started_after_resume` with `partner_concurrent` recorded. An arrival with `job_accepted` and no terminal line is revealed as `interrupted`. |
| **PG-8** | Seed uniqueness cannot be enforced across uncoordinated workers (critic N6). | **Protocol 5.5**: draw `(os.urandom(4) & 0x7FFFFFFE) \| worker_index` per try, so **the low bit carries the worker index** and a cross-worker collision is impossible; each worker checks only its own half of the used-seed set; the seed is fsynced to the WORKER SPOOL before the POST and reaches the chain as `llm_request` when the orchestrator next ingests that spool (protocol 5.5, as narrowed by execution-review E4 -- there is no pre-POST chain handshake, and adding one would put a round trip inside the measured `latency_s`); `0xFFFFFFFF` never occurs. **The used-seed set is a real, program-wide file**: `<work root>/used_seeds.json`, written durably by `lab_orchestrator.write_seed_registry`, rebuilt from every trial's spools at each start and resume by `seed_registry_reconstruct`, and rewritten before every dispatch and whenever a pump ingests a new seed. It sits above the trial directories because protocol 5.5 promises the set of earlier TRIALS of the PROGRAM; `verify_program` therefore runs `seeds.unique` at program scope across all trial chains, which no single-chain check can do. Before the repair of execution-review E2 there was no writer at all, so uniqueness was enforced only within one episode. A duplicate within a half is still a **logged defect with no outcome effect** (`seeds.unique` is severity DEFECT, not FAIL), because no bit-reproducibility is claimed. `worker_index` is the slot, not the arm, and is removed from the canonical job payload (audit M1). |
| **PG-9** | `latency_s` and `ell` are undefined when a worker died before its first request (critic N5). | `ell = 0.0`, `tokens_known = 0`. `winstats.compare` then still receives finite values. |
| **PG-10** | `/metrics` identities have no failure consequence and a hanging scrape blocks enrollment (critic N9). | 5 s timeout, 3 tries, then `ok: False`, the window is logged as unreconciled and enrollment continues. A violated start identity is a `reconciliation_defect`, never a refusal. |
| **PG-11** | The "no free text" rule contradicts embedding the full config (critic N12). | Operational string discipline (4.2 rule 7); the config is carried by hash with the file as a tracked sibling; commit ids appear only as `*_sha256` of the id. |
| **PG-12** | Who writes anchor events (critic N13). | The anchor process owns a spool; the orchestrator is the sole chain writer and turns receipts into events. Comment target is fixed to the issue. |
| **PG-13** | No chain between trials; no rule for a plumbing FAIL; no exit for a defective verifier or builder (critic N1-N3). | The **program chain** of 4.3; `plumbing_verdict` + `program_paused(plumbing_fail)` with **two** condition lists (protocol 6.4 rows 22a/22b): list A is repairable by a reporting-code re-freeze and stops the program on a second identical occurrence, list B is a `decision_code_defect` (P11) under protocol row 24 and needs a new protocol version. `refreeze_authorization.scope` remains the single-member enum `[reporting_code]`, so a re-freeze **cannot** express a change to decision-defining code (audit M5). |
| **PG-14** | "T4 job payloads byte-identical apart from the label" is undefined. | `canonical_job_payload()` removes `arm`, `arrival`, **`inv`**, `pair`, `position`, `task_uid`, **`worker_index`**, `paths`, `assignment_seq`, `payload_sha256` (`inv` added pre-freeze by the repair of execution-review E3: the invocation id is a property of the dispatch, and 6.4 rows 11c-11e let one pair span two invocations); what remains must be byte-identical for the two jobs of a T4 pair. **The same removal list is written in protocol 12.3**, so the verifier check is defined in the frozen text and not only here. |
| **PG-15** | The hard-cap formula is arithmetically false as written (critic N15). | **Protocol 5.6**: `max_recovery_waits_per_call = 1` is an explicit key; the cap is `4*(3*T + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60` = **3,354 s** at `T = 180` (the 3,306 of the v3 draft was an arithmetic slip, audit M12); **the harness computes it from the formula and the pinned `request_timeout_s` and never reads a typed literal**, and `config.json` carries `episode_hard_cap_s: null` until that computation. The cap is terminal, so validity is untouched; the claim "can only bind on a hang" is replaced by "reported by arm". |
| **PG-16** | `betting_log_e_ternary` appeared in the v2 draft as a traffic driver. | **Protocol 8.8 item 5**: it exists only in `build_live_ab_results.posthoc_betting.json`, computed after the trial has ended, on final complete scores only, never on partial scores, labelled post hoc with no error-control claim and no adapter. Tests forbid it in `lab_monitor`, `lab_reference_rule` and `lab_orchestrator`. |
| **PG-17** | The margin: `delta = 0.03` primary, with 0.10 and 0.15 as read-outs. | `monitor.delta = 0.03` is the only value the decision function ever sees; `monitor.exploratory_margins` (0.10, 0.15) are computed into `monitor_update.readouts` for display and are **structurally incapable of deciding** — they are never passed to `decide`, and `exploratory_margins_decide` is `false` (protocol 8.8 item 1). |
| **PG-18** | Enclosure clipping: clip the individual enclosures or only the band endpoints? | Individual enclosures are already inside `[-1, 1]` by construction (`Enclosure.__post_init__` enforces it); the clip in `band()` applies to `L` and `U` only, exactly as the guidance writes it. |
| **PG-19** | `variance_process`: default or explicit? | Passed explicitly as `variance_process=n`, because the frozen call is what the protocol quotes; a test asserts the explicit and default calls agree. |
| **PG-20** | Whether the stale radius `0.4966` or the computed `0.4950264429325317` is frozen. | Neither is typed: `dryrun_live_ab.py --radius-table` regenerates `radius_table.csv` from `src/winstats.py`, the table goes into the freeze bundle, and **protocol 1.3 states that no radius in the protocol is hand-typed and is checked against that file**. The crossing index 92 is unaffected. The stale value survives only in `COORDINATOR_DECISIONS.md`, which no code reads and which this session may not edit; it is listed as a fact for the coordinator to correct in `audit_response_v3.md`. |
| **PG-21** | Roster size and therefore `N_P`. | **`N_P = n_S1 // 2 + n_S2 // 2`** (protocol 3.3), at most **568** with the extended roster (565 after the six smoke exclusions) and 295 with S1 only. Pairs never cross the strata and each stratum keeps its own leftover. `monitor.n_max` is **required, without a code default**, is set from `roster.n_pairs` at freeze time and never later, and a mismatch between them raises `FrozenMismatch` (audit B5, m9). |
| **PG-22** | Tasks are reused across the four trials (the pilot already exposed all 591). | Permitted, and **declared as a deviation from guidance item 6 rather than redefined** (protocol 10.3 and the deviation table of 13.1): each trial is separately randomized, so per-trial validity does not need disjoint rosters; what is new in each trial is the arrival order and the coins; the four trials are **not** independent replicates, T1 and T2 are never two confirmations, and no combined claim is formed. `assert_disjoint` checks within-trial disjointness only (audit M9). |
| **PG-23** | Whether `episode_started` must be durable (critic N21). | No: the orphan check matches against the **spool's** `job_accepted`, which is durable and worker-owned. `episode_started` is orchestrator telemetry. |
| **PG-24** | Auto-abort counting "ten consecutive revealed arrivals" — reveal order or arrival order? | Reveal order, stated in `execution.auto_abort.counted_in`. |
| **PG-25** | Whether the integrity label covers the post-decision phase. | Yes for terminal failures and torn regions, counted separately per phase; **the coin-adjacency test is computed over the randomized phase only** (there are no coins after the decision). Written into **protocol 12.6**, together with the rule that a `worktree_drift` event is reported in the same tables but never contributes to the label. |
| **PG-26** | Which working location the program runs in, and what happens when another session changes the tree under a running invocation (audit B7; the v3 draft left this an open coordinator item in its Appendix F). | **Closed without reopening coordinator decision C15**: execution stays in the single shared clone on `session60/live-ab`, and the residual risk is closed by two guards written into **protocol 2.1, 12.4 item 2 and 6.4 row 27** — the worktree identity assertion before every commit and at every invocation start (`anchor_failed(tree_state)` / `preflight_refused(worktree_identity)`), and `worktree_check()` every `execution.worktree_check_s = 60` s, whose failure is `trial_paused(worktree_drift)` and which is explicitly **not** attributed to the operator in the integrity forensics. |
| **PG-27** | Event-type names that differed between the two documents (`archive_sealed` vs `deposit_sealed`; a missing `publication_withheld`, `server_stopped`, `erratum` and `decision_code_defect`; `preflight_refused` vs `invocation_refused`). | **One name each, in both documents**: `deposit_sealed` (T29b) and `server_stopped` (T29) at trial close; `publication_withheld` (T29c) for a scanner hit; `erratum` (P10) and `decision_code_defect` (P11) in the program chain; `preflight_refused` (P6) **before** a trial's seq 0 and `invocation_refused` (T3) at a later invocation of an open trial, which is exactly how protocol 6.4 row 21 now reads. |

---

## 12. Order of work

1. **G1 first, alone, for the first block:** `lab_common` + `lab_eventlog` + the chain fixtures. Everyone
   else is blocked on nothing but the signatures, which are in section 3.
2. G2, G3, G4 in parallel. G3 has no dependency beyond `lab_common` and `winstats` and should be finished
   first; it is the group whose defects cannot be repaired after the freeze.
3. **`lab_reference_rule` is written by G1 from `protocol_FINAL.md` alone, after G3 has delivered and
   without reading `lab_monitor.py` or `lab_enclosure.py`.** Writing it from the protocol text is the whole
   value of the second path; copying G3's code would reproduce G3's defects and make the shadow useless.
4. G5 integrates, then runs D1-D7.
5. Freeze gate: the whole suite green, D1-D7 green, `lab_verify_log --mode full` PASS on every dry run,
   `rule_block_sha256(config)` equal to the protocol's own rule-block hash, the two `config.json` blocks
   byte-identical, the freeze bundle complete (no `null`, no `"unknown"`), and the real-server dress
   rehearsal of critic N8 (out-of-design tasks only, both workflows, both models, forced pause/resume and
   forced server kill) PASS.

---

*Prepared and checked by AI agent sessions; not human peer review or author sign-off* (protocol 14.7, which
requires this sentence on every session-60 document about these trials).
