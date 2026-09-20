# Host-gate delivery review — issue #11

**Reviewed delta:** `c746e320920b83c453e02c1cde19b32f4a9d03e9` → `035a93458f8371a81eb06eae67048ca1f1580f76`, limited to the new host gate, its orchestrator/schema/verifier wiring, tests, and accompanying policy changes. Prepared using the `fan-paper-review` workflow, with an additional independent static edge-case reviewer. AI-assisted review; not human sign-off, actual host clearance, or prospective-study freeze approval.

**Disposition:** this pin delivers executable gate code and useful passing mocked tests, but does not yet implement its own revision-8 OS-daemon policy and has a reproducible false-clean parser case. The required mid-run observation coverage and missing-record checks also need completion. No readiness milestone or earlier repair is closed by this review alone.

## Independently reproduced checks

The exact candidate's `experiments/live_ab/`, `experiments/local_stream/`, and `src/` blobs were exported with `git archive` into `work/host_gate_delivery/snapshot/`. Source files were not edited. Python 3.14.4 was used, rather than assuming the owner's environment.

Command from the audit scratch directory:

```sh
env -u PYTHONPATH /opt/homebrew/bin/python3 run_targeted.py > targeted_verbose.log 2>&1
```

The unchanged host-check module contains **76 tests**. **74 targeted tests passed in 0.648 seconds**, with no failures, errors, or unittest skips. Two cases were explicitly excluded: the live-host process scan and the host-account-name inspection. The runner replaces actual subprocess/process-table readers with a prohibiting stub; injected per-test process results are permitted. It recorded **zero unexpected reader calls**. The refusal-wiring fixture uses a synthetic process table, mock freeze, `anchor=False`, and an injected refusal; no model/server is launched. No actual host or foreign process was inspected, no networking was performed, and no process was controlled.

The owner's **380-pass** claim remains owner-reported. This review did **not** rerun the unchanged full suite or promote these 74 passes into a full-suite result. Four additional small injected witnesses are in `probe_host_gate.py` and `probe_host_gate.json`; they exercise the observed defects without reading the host.

## Findings and necessary corrections

### H1 — The new activity policy is documentation, not implemented behavior

The same commit adds coordinator revision 8 (`design/COORDINATOR_DECISIONS.md:269–296`). It withdraws both the identity-only exemption and the unconditional OS-context refusal. Its replacement says non-baseline consumers refuse on presence; OS-owned consumers use cumulative CPU time over **10 seconds**, with activity defined by a delta **strictly greater than 0.5 CPU-seconds**; baseline measurements and overlap windows are recorded and thresholds are freeze-bound.

None of those policy fields or measurements exists in this pin's executable gate. `PS_ARGV` reads only PID, PPID, elapsed time, RSS and command text (`lab_hostcheck.py:198`); `ProcRow` has no UID, resolved executable, cumulative CPU value, or process-identity binding (`:205–214`). Allowlisting is caller-supplied PIDs plus descendant closure (`:265–293`). The scanner reports any matching Metal-holding process without a baseline/activity distinction (`:647–730`), and the public event schema has no CPU samples/delta, interval, baseline identity, activity flag, or overlap window (`lab_eventlog.py:309–325`). The hard gate consequently still refuses an idle OS process that matches the compute-resource rule.

**Required before clearance:** reconcile the binding protocol, architecture and coordinator policy, then deliver their implementation and deterministic fixtures. A `/System/...` string in command text alone does not establish OS ownership or executable identity. Specify and validate the intended exact resolved executable/ownership rule, ambiguous identities, PID reuse, sample timing/actual interval, units, equality at the threshold, process exit/restart, counter reset, and unreadable measurements. Freeze the policy values and matching algorithm; an unavailable delta must remain unknown, not idle. Do not silently expand an exemption after observing outcomes or a refusal. The previous identity-only allowance was expressly withdrawn; this review does not reinstate it.

The policy statement that an unchanged CPU counter means the daemon “CONSUMES NOTHING” (`COORDINATOR_DECISIONS.md:279`) is unsupported as a statement about GPU activity. CPU time can define a prespecified **CPU-activity** rule; it cannot establish accelerator inactivity. Retain that limitation beside latency results.

### H2 — A filename can be mistaken for proof that an unobserved process exited

`_LSOF_NOT_LOCATED_RE` is an unanchored `not located: PID` search (`lab_hostcheck.py:561`). The parser applies it before processing `p`/`n` field records (`:591–600`). It then treats the resulting PID as covered and allows a nonzero return code whenever any absent PID was recorded (`:609–616`).

**Injected witness, reproduced:** request PIDs `[20, 21]`; supply lsof stdout `p20\nn/tmp/not located: 21\n`, return code 1. PID 21 has never been listed, yet `covered == {20, 21}`, `failure is None`, and the hard preflight returns `clean=True`. This is an ordinary `n` filename being interpreted as a process-exit diagnostic, not an actual observation of a process exit.

**Required repair:** recognize only an exact diagnostic-record format from the appropriate output stream, never a pathname field; distinguish exhausted/vanished PIDs from permission failures and partial output. Do not suppress an otherwise unexplained nonzero exit just because one absent PID occurs somewhere in the output. Test the filename witness, mixed exited/inaccessible processes, and unexpected diagnostics. Those cases should fail closed. Existing tests correctly cover absent binaries, timeouts, unreadable/unlisted PIDs and probe-budget exhaustion, but miss this edge case.

### H3 — Required observation coverage is not auditable across the randomized phase

The hard gate is now called before opening the trial (`lab_orchestrator.py:2466–2476`), which is a substantive improvement. During execution, however, `World.host_scan` accepts only points named `trial_start` and `quiescent` (`:1163–1169`). Randomized-phase pair boundaries call `scrape('pair_boundary')` (`:1673`), so no host scan occurs there. The only `scrape('quiescent')` call is in post-decision dispatch, every 50 follow-up arrivals (`:2035–2059`); trial-end scans are skipped too. Thus a trial that remains randomized until its horizon can have only its startup scan and no subsequent in-trial host observation. This cannot reveal the baseline process that “wakes during a trial” as the new policy promises.

The injected sequence `trial_start, pair_boundary, pair_boundary, trial_end` produces exactly one host record, at startup. This is a code-path witness, not a live-trial experiment.

Two additional audit gaps occur in the same path:

- A successful hard-preflight scan is returned and discarded (`:532–534,2467–2470`); the later trial-start scan is a separate observation. Refusal reconstruction keeps findings/degraded markers but resets the original `scanned`/`allowlisted` counts to zero (`:537–548`), so not every completed scan retains its full result.
- `_check_host_scans` checks only records already present and unconditionally marks both checks seen afterward (`lab_verify_log.py:205–262`). An empty list yields no finding and marks `host.record` and `host.quiescence` as okay, as the pure witness demonstrates. No required-count/cadence check establishes that the scans happened. A schema failure in `World.host_scan` also becomes only an in-memory finding (`lab_orchestrator.py:1170–1171`).

**Required repair:** freeze a cadence that observes the randomized phase at defined safe points and records the actual measurement/overlap interval; preserve complete clean, dirty and degraded scan records. Verify required occurrence/order/count for the applicable non-simulated protocol version, including the preflight and any defined terminal/resume scans. A missing required record must not look equivalent to an empty clean scan. Retain enrolled outcomes and do not retrospectively censor pairs or adjust latency when activity is observed. The action on detected/unknown mid-run load must be explicit and consistent with the frozen policy; it need not imply discarding a trial.

### H4 — The operator CLI returns success for a degraded scan

`lab_hostcheck._main` returns `1 if scan.findings else 0` (`:830`). Injecting `ScanResult(degraded=['ps-unavailable'])` therefore prints the degradation but exits **0**. The callable hard preflight correctly refuses this state; the CLI does not, so automation that relies on its exit status can mistake an unreadable host for a successful check.

**Required repair:** determine successful exit from `scan.clean`, optionally separating detected contention from unavailable evidence with distinct nonzero codes. Add a CLI fixture for both dirty and degraded results. No actual CLI host scan was run here; the witness injects the result.

## Checks that are supported, and limits that remain

The gate observes rather than controls discovered processes. Standard-library timeouts may terminate only the gate's own `ps`/`lsof` helper; that distinction is documented. Recognized runner names use token matching, and the generalized Metal probe detects an above-floor renamed compute process. Known probe errors and malformed process-table lines generally become degraded rather than empty clean results; H2 is the concrete exception found here.

For each scan that reaches the in-trial writer, both empty and degraded results are logged. The two public event types use closed detector/degraded vocabularies and retain command/summary **hashes**, not arbitrary command summaries (`lab_hostcheck.py:748–779`; `lab_eventlog.py:307–325`). Schema and internal clean-versus-findings consistency tests passed. The verifier correctly distinguishes an in-trial contention DEFECT from an INFO record that the initial gate refused the trial. These are useful properties but do not establish scan completeness.

Detection remains conditional on recognized runner tokens or sampled open-resource markers. The non-Python general probe floor is **128 MiB**; Python interpreters are probed at any RSS, so blanket statements that *every* below-floor process is invisible are too broad. The budget is **96 probed PIDs**; exceeding it degrades the scan. Raw-Metal workloads without the selected compute markers and activity between scans remain blind spots. Holding a library does not prove current accelerator work, and absence of a recognized holder is not universal GPU isolation. The policy's baseline population below the floor and what is recorded there must be specified when H1 is implemented. Harness-owned PID/descendant exclusions also rely on caller identity assumptions; they presently have no executable/start-time binding against PID reuse.

Appropriate claim: **“At the recorded scans, no recognized, non-exempt process met the frozen detection criteria; baseline observations, unreadable checks, resident-size limits and between-scan blind spots are reported.”** Do not describe the gate as proof of continuously exclusive accelerator use. Treat owner-reported host scans and activity observations as owner evidence until their records are delivered; this review did not reproduce them.

## Handoff boundary

Deliver a new exact pin addressing H1–H4, with only changed-path tests and the frozen policy/schema values. Then independently recheck those changes and the required actual-host clearance evidence before prospective enrollment. Previously identified preflight, seed, interrupted-usage, clip-contract and other repairs remain under the owner's separate work; this bounded host-gate review neither reopens nor closes them. No actual study outcome, manuscript result, arXiv artifact, or submission state changes here. Root retains Git/status/coordination ownership; this report and its ignored audit scratch are the reviewer's only writes.

---

## Repair delivery recheck — `ddef3c83bb8a85f93aa27ee938c84fc32c1ccc78`

This append-only section reviews **only** the host-gate delta from `035a934` to the exact `ddef3c8` delivery reported at 06:33:52 UTC on September 20, 2026. The initial findings above are preserved as the historical review. Later changes, actual host conditions, freeze contents and unrelated repairs are outside this recheck. **Disposition: H1 is partially implemented; H2, H3 and H4 remain open. The host gate is not cleared for the prospective freeze.**

### Reproduced evidence and positive changes

An exact export is retained under `work/host_gate_delivery/repair_ddef/snapshot/`. The same guarded runner, extended to prohibit the real baseline-activity sampler, discovered **117 host tests** and executed **115**: **all passed in 0.735 seconds**, with zero unexpected process-reader calls. The two live-host/account cases remain explicitly excluded. This is a bounded host-module result, not reproduction of the owner's reported 461 full-suite passes. No real host/process inspection, timed CPU sampling, networking, model execution, Git mutation or unrelated suite was performed.

The new code materially advances H1: an exact first-command-token list replaces the blanket prefix proposal; the activity rule has named 10-second/500-millisecond constants, strict `>` comparison, raw CPU-delta units, and idle/active/exited/unknown states; baseline records and the overlap flag have schema support. Tests cover matching alternatives, threshold equality, failed whole-sample reads, negative CPU deltas, short intervals, RSS/probe limits and public-field sanitization. The documentation now correctly distinguishes measured CPU activity from accelerator activity/inactivity. These are implemented improvements, not merely new prose.

Both sets of small witnesses were run from the new audit directory:

```sh
env -u PYTHONPATH /opt/homebrew/bin/python3 probe_host_gate.py > probe_host_gate.json
env -u PYTHONPATH /opt/homebrew/bin/python3 probe_baseline.py > probe_baseline.json
```

### Status of the four original findings

| Finding | Status at `ddef3c8` | Exact evidence |
|---|---|---|
| H1: baseline identity/activity policy | **Partly implemented, not closed** | New executable activity handling exists, but missing per-PID samples can be admitted as exited; claimed resolved/OS-owned identity is still only a command-token comparison; activity evidence and verifier consistency remain incomplete, as detailed below. |
| H2: false-clean lsof parser | **Unchanged; reproduced** | `lab_hostcheck.py:916,948–952,964–971` still searches `not located: PID` inside pathname fields. The same `[20,21]` witness reports both covered and passes preflight clean. Only the fixture's process-table CPU column was added for the new format. |
| H3: cadence and missing/full records | **Unchanged; reproduced** | `lab_orchestrator.py:1562–1570` still skips `pair_boundary` and `trial_end`; randomized boundaries are at `:2089`, and the follow-up-only quiescent scan is at `:2483`. The witness still produces only a startup record. Empty host-event input still yields no verifier findings and both checks marked okay (`lab_verify_log.py:207–263`). Successful hard-preflight output is discarded (`lab_orchestrator.py:2894`), and refusal reconstruction remains lossy (`:889–918`). |
| H4: degraded CLI success | **Unchanged; reproduced** | `lab_hostcheck.py:1278` still returns zero for an injected degraded scan with no findings. |

### H1 completion: unreadable CPU values must not become evidence of exit

`parse_cpu_table()` drops malformed per-process CPU values (`lab_hostcheck.py:436–450`). `classify_activity()` then treats a PID absent from the resulting dictionary as **exited**, without distinguishing a dropped unreadable row from an actual process exit (`:519–528`). A nonempty second table containing some other valid PID avoids the whole-table failure path (`:503–506`).

**New injected witness:** the first sample contains the matched baseline PID 39197 with valid CPU time; the second table contains a valid PID 1 and `39197 UNREADABLE`. Parsing retains only PID 1. The baseline is classified `exited`, `degraded=[]`, and the hard preflight returns **clean=True**. This contradicts the declared unknown-is-not-idle rule. The witness does not read or depend on any process currently on the machine.

Preserve malformed/inaccessible per-PID status and classify it as unknown. Require positive exit/identity evidence before using the exited exception, with PID/start-identity matching across samples so a replacement process cannot inherit another process's cumulative CPU history. Add the malformed-present-PID fixture alongside the existing genuinely exited and whole-reader-failure cases.

### H1 completion: identity and measurement interval remain overstated

The closed list is useful, but `match_baseline()` performs string equality against the first whitespace-delimited token of the command (`lab_hostcheck.py:859–884`). The scanner does not read UID or a verified executable/start identity; `PS_ARGV` and `ProcRow` still lack them (`:334–367`). Thus “resolved absolute executable path” and “OS-owned” describe the list's intended identity, not something independently established for each observed PID. Bind the observed process to the intended executable/ownership/start identity or narrow the stated assumption; do not claim the command token itself authenticates ownership.

The first CPU count comes from the initial process-table read. Only after the Metal probe does `probe_baseline_activity()` start its monotonic timer (`:494`) and wait/read again. The recorded `interval_ms` therefore excludes the initial-read/probe delay although the CPU difference spans it (`:1050–1051,1118–1128`). It is not the actual interval between the two CPU observations. Carry the first-sample timestamp through the probe, timestamp the second sample, and record the actual interval. The code also accepts intervals as short as **8,000 ms** (`BASELINE_MIN_INTERVAL_MS`, `:209`), while the policy describes a 10-second measurement. Explicitly ratify that tolerance in the binding policy, or require the intended interval; do not silently treat an eight-second delta as the same quantity as a ten-second delta. This is a measurement-contract correction, not a request to retune the 500-ms threshold.

### H1/H3 completion: baseline records can contradict themselves or lose their measurements

The new schema accepts baseline activity, delta, interval and `baseline_active`, but `_check_host_scans()` is unchanged and does not validate their relationship. A second new witness builds a genuine active baseline record, then sets `baseline_active=False`, removes findings and sets `clean=True`. The event passes schema validation, and `_check_host_scans()` emits **zero findings**, despite the embedded baseline record saying `activity='active'`. Verify the activity/threshold/interval/status relationships and consistency among baseline records, active findings, overlap flag, degraded state and `clean`; represent unknown/exited measurements distinctly from measured zero.

Also, `HostNotQuiescent` carries only findings/degraded markers, and `write_host_quiescence_refused()` constructs a fresh scan from those two fields (`lab_hostcheck.py:321–328`; `lab_orchestrator.py:896–901`). The third new witness exercises an active-baseline refusal through this writer using an injected event log. Its public body contains a `baseline-active` finding but **zero baseline records**, `baseline_active=False`, and `scanned=0`. The CPU delta/interval that caused refusal is lost. Preserve the complete structured scan in the exception/refusal path, including activity measurements and scan counts, so failed gates are as auditable as successful scans.

### Bounded handback

H2–H4 are confirmed outstanding at this exact pin; H1's implementation progress is acknowledged without closing its remaining defects. Supply one subsequent pinned repair for these explicit cases and recheck only changed paths before deciding host clearance. The separate delegated seed/unknown-usage/T4 review is recorded in `reviews/arxiv_live_repair_ledger_review.md`; this host report does not substitute for it. Root owns the freeze/provenance and shared-status disposition. This report's ownership is released after the append; the initial historical findings and all audit logs remain intact.
