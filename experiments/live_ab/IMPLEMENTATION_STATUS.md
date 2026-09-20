# `live_ab` — implementation status

**Status: 304/304 passing, dry run PASS on all four scenarios — but not "clean".**
Outstanding: one unreproduced flake (§6), two tests that check spelling rather than behaviour
(§6.1), ten dormant skip-guards that would fail silently (§3), three documentary deviations
(§5.1–5.2), and four open defects implemented as written rather than worked around (§5.3).
Five items need a coordinator ruling before the protocol can be frozen (§7).

Written by the integration / test-runner pass. Everything in this file was produced by running
the code, not by reading it. Where a number is quoted, the command that produced it is given.

Python is `<REPO>/.venv/bin/python` (3.12). No test
starts a model, opens a non-loopback socket, downloads anything, or changes git state.

---

## 1. The command that runs the whole suite

```
cd <REPO> && \
  ./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'
```

and, separately, the end-to-end dry run against the mock server:

```
cd <REPO>/experiments/live_ab && \
  ../../.venv/bin/python dryrun_live_ab.py --scenario all
```

The suite takes ~210 s wall clock, dominated by `tests_lab_e2e.py` (a whole trial per kill
point in the resume matrix). The dry run takes ~35 s.

---

## 2. Modules and line counts

`wc -l` on 2026-09-19, after the integration pass.

### Implementation

| module | lines | group | what it is |
|---|---:|---|---|
| `lab_common.py` | 460 | G1 | path tokenisation, canonical JSON, digests, exception taxonomy |
| `lab_eventlog.py` | 996 | G1 | the append-only hash-chained event log, segments, schema |
| `lab_verify_log.py` | 1016 | G1 | the offline verifier: 32 checks, severities, verdict |
| `lab_reference_rule.py` | 432 | G1 | the independent shadow rule (imports no `lab_monitor`/`lab_enclosure`) |
| `lab_data.py` | 661 | G2 | roster build, exclusions, task content hashes |
| `lab_design.py` | 251 | G2 | stratified arrival orders, write-once roster/order files |
| `lab_coin.py` | 276 | G2 | the fair coin, drawn and `F_FULLFSYNC`ed before dispatch |
| `lab_monitor.py` | 796 | G3 | band, `MonitorState`, `decide`, `replay` — the decision code |
| `lab_enclosure.py` | 537 | G3 | pair enclosures, the cost certificate, `certified_elapsed` |
| `lab_client.py` | 804 | G4 | the llama.cpp HTTP client, receipts, retry/backoff |
| `lab_server.py` | 497 | G4 | server start/stop/restart/health, identity assertion, smoke |
| `lab_mock_server.py` | 551 | G4 | the local mock server (stdlib `http.server`, loopback only) |
| `lab_worker.py` | 630 | G4 | one episode per process, the spool contract, sandboxed verify |
| `lab_orchestrator.py` | 2611 | G5 | the state machine of ARCHITECTURE §7, looks, decisions, anchors |
| `lab_anchor.py` | 447 | G5 | anchor requests and receipts (mock receipt in the dry runs) |
| `dryrun_live_ab.py` | 607 | G5 | D1–D5, D7; the simulated worker; the radius table |
| `build_live_ab_results.py` | 430 | G5 | the results/ledger builder |
| `config.json` | — | G5 | ARCHITECTURE §6.1 verbatim = protocol Appendix B |
| **implementation total** | **12 002** | | |

### Tests

| test module | lines | group | scope |
|---|---:|---|---|
| `tests_lab_chain.py` | 2054 | G1 | chain, schema, verifier, reference rule, the `testdata/chains/` generator |
| `tests_lab_isolation.py` | 565 | G1 | import isolation, the §3 signature gate |
| `tests_lab_design.py` | 1302 | G2 | roster, strata, order, coin, seeds |
| `tests_lab_stats.py` | 1615 | G3 | the statistical core; regenerates `radius_table.csv`, `monitor_fixtures.json` |
| `tests_lab_serving.py` | 1322 | G4 | client, server, mock server, worker, spools, sandbox |
| `tests_lab_e2e.py` | 1245 | G5 | whole trials, resume matrix, cadence agreement, config verbatim |
| **test total** | **8 103** | | |

---

## 3. True pass / fail counts

Counted programmatically from the `unittest` result objects, per file, on a clean tree
(`__pycache__` removed first):

| test file | run | passed | failed | errors | skipped |
|---|---:|---:|---:|---:|---:|
| `tests_lab_stats.py` | 58 | 58 | 0 | 0 | 0 |
| `tests_lab_design.py` | 58 | 58 | 0 | 0 | 0 |
| `tests_lab_chain.py` | 58 | 58 | 0 | 0 | 0 |
| `tests_lab_serving.py` | 77 | 77 | 0 | 0 | 0 |
| `tests_lab_isolation.py` | 12 | 12 | 0 | 0 | 0 |
| `tests_lab_e2e.py` | 41 | 41 | 0 | 0 | 0 |
| **total** | **304** | **304** | **0** | **0** | **0** |

`unittest discover` over the whole directory agrees: `Ran 304 tests ... OK`.

Dry run, from a clean tree:

```
[MOCK] D1 status=ended verifier=PASS decision=harm_keep_incumbent@39
[MOCK] D2 status=ended verifier=PASS decision=horizon_no_decision@40
[MOCK] D3 status=ended verifier=PASS decision=deploy_candidate@44
[MOCK] D4 status=ended verifier=PASS decision=horizon_no_decision@40
```

exit status 0. D5 (chaos/resume) runs inside `tests_lab_e2e.py`; D6 is not executed here
(see §7). D7 is `dryrun_live_ab.py --radius-table`.

**Why the dry runs decide at `n = 39` and `n = 44`, far below `n_min = 100`.** A reviewer will
ask this first. The dry runs write a *mock* freeze tree with a reduced screening prefix, and
the reduction is recorded in that tree rather than applied silently. Read back from a real
probe run:

```
results/freeze/config.json:  n_min=6  delta=0.03  alpha_gate=0.00625  rho=100.0
                             mock=true   mock_overrides={"monitor.n_min": 6}
```

`alpha_gate`, `rho` and `delta` are untouched by the `n_min` override; D3 additionally records
`{"monitor.delta": 0.9}`. The committed `experiments/live_ab/config.json` is **unmodified** —
`n_min=100, delta=0.03, alpha_gate=0.00625, rho=100.0`, and it carries no `mock_overrides` key
at all. `decide()` reaches `harm_keep_incumbent` and `deploy_candidate` only after the
`n < n_min` guard, so no real trial can deploy or stop for harm below 100; the one decision
kind reachable below `n_min` is `horizon_no_decision`, which is the abstention.

**No test is skipped. No test is disabled, deleted, or weakened.** There are ten dormant
`skipTest` guards of the form "module X has not landed yet" / "fixture Y is not present",
left from the parallel-group build. All ten are inactive — the programmatic count above
reports `skipped = 0` for every file — but they are a real hazard: if a module or fixture
were ever removed, the corresponding tests would go *quiet* instead of red. They are at
`tests_lab_design.py:1258`, `tests_lab_e2e.py:230,1128`, `tests_lab_chain.py:1653,1729`,
`tests_lab_isolation.py:140,159,511,517`, `tests_lab_stats.py:1466`. Recommend the
coordinator convert them to hard failures before the freeze.

---

## 4. What this pass fixed

**29 failing subtests in `tests_lab_chain.FixtureTests.test_committed_fixtures_match_the_generator`**
(all 28 `defect_*.jsonl` plus `good_T4.jsonl`). This was the only failure in the suite.

*Cause.* G5's integration finding 3 (README §4) corrected `lab_reference_rule` to emit the
`enroll` look at the **coin**, not at `pair_enrolled`, because protocol 7.3 item 2 defines `n`
as "the count of chain-valid `coin_drawn` events" and says it "changes only at a `coin_drawn`".
`lab_orchestrator._w_draw_coin` already agreed — it calls `evaluate()` immediately after the
coin, with the comment "the coin is a consumed event: the enroll look". The fixture generator
in `tests_lab_chain.write_fixtures` was not updated with it: it still called `sync(i)`
immediately after appending `pair_enrolled`, where no look is due any more, so the enroll
`monitor_update` drifted to wherever the next `sync()` happened to fall — after the first
`llm_request`, six events too late.

*Fix.* Moved the `sync(i)` call in `tests_lab_chain.py` from after `pair_enrolled` to
immediately after `coin_drawn`, with a comment recording why, and regenerated the fixtures:

```
./.venv/bin/python experiments/live_ab/tests_lab_chain.py --write-fixtures
```

The generated chains now read `pair_enrolled → coin_drawn → monitor_update(enroll) →
episode_started ×2 → …`, which is byte-for-byte the shape a real orchestrator run produces
(verified against a live `run_dry` chain). No scientific rule was touched: the band formula,
`alpha_gate`, `rho`, `delta`, `n_min`, the hierarchy, the tolerance, the coin rule, the
enclosure rules and `max_attempts` are all unchanged, and the *number* of looks per pair is
unchanged — only the position of one non-score-bearing event in the chain.

The 29 defect fixtures still each trip their intended verifier check after regeneration
(`test_every_defect_fixture_is_caught`, with `assertEqual(report.verdict, 'FAIL')` for every
FAIL-severity check), and the good fixture still verifies
(`test_committed_chain_fixtures_still_verify`, `T4 plumbing: PASS`, 32 checks, 0 DEFECT, 0 FAIL).

Also corrected: README §4's closing paragraph, which stated as present-tense fact that the
fixture test "now fails for all 29 fixtures". That is no longer true; the paragraph now
records the resolution.

### 4.1 Exactly what this pass changed

40 files, all under `experiments/live_ab/`:

| file(s) | change |
|---|---|
| `tests_lab_chain.py` | one `sync(i)` call moved from after `pair_enrolled` to after `coin_drawn`, plus a six-line comment citing protocol 7.3 item 2 and `_w_draw_coin` |
| `testdata/chains/` (37 files) | regenerated by `tests_lab_chain.py --write-fixtures`; not hand-edited |
| `README.md` | one stale paragraph (§4 closing) corrected |
| `IMPLEMENTATION_STATUS.md` | this file, new |

**Nothing else was touched.** The other 30 files in the directory — all 17 implementation
modules, `config.json`, and the other five `tests_*.py` — are byte-identical to what the
groups delivered. No implementation module was edited to make a test pass, no assertion was
weakened, no test was deleted or skipped, and no scientific rule (band formula, `alpha_gate`,
`rho`, `delta`, `n_min`, the hierarchy, the tolerance, the coin rule, the enclosure rules,
`max_attempts`) was changed. No git command that changes state was run.

---

## 5. Known deviations from the two binding documents

### 5.1 Where the two documents disagree (reported, not silently resolved)

**D-1. Where the `enroll` look is evaluated.** This is a genuine three-way disagreement and
the coordinator should rule on the wording before the freeze.

| source | says |
|---|---|
| protocol 8.3, trigger 1 | the trigger is "every **`pair_enrolled`** (the prefix grows…)" |
| protocol 7.3, item 2 | `n` is "the count of chain-valid `coin_drawn` events"; it "changes only at a `coin_drawn`" |
| ARCHITECTURE 7.1 row 5 | `coin_drawn` is written in state `ENROLLED` |
| ARCHITECTURE 7.1 row 6 | in state `COMMITTED`: job files; `Popen`; `episode_started` ×2; `monitor.enroll`; `shadow_step`; `monitor_update(trigger='enroll')` |
| the implementation | `lab_orchestrator._w_draw_coin` evaluates on the coin, so the order is `coin_drawn → monitor_update(enroll) → episode_started ×2` |

protocol 8.3 taken literally (evaluate at `pair_enrolled`) contradicts protocol 7.3 item 2
(`n` has not grown yet at `pair_enrolled`), and would mis-handle a crash between
`pair_enrolled` and `coin_drawn`: a pre-enrolled but never-randomized pair would hold a
position it was never assigned. Per the precedence rule (protocol wins on science), 7.3 item 2
is the scientific statement and 8.3 trigger 1 is loose naming of the same single look —
**the count of looks is identical under either reading**, one per enrolled-and-randomized
pair. The implementation follows 7.3 item 2.

The implementation *additionally* differs from ARCHITECTURE 7.1 row 6 in the placement of
`monitor_update(enroll)` relative to the two `episode_started` events: row 6 lists it after
them, the implementation writes it before them. `episode_started` carries no score
information and never updates an enclosure (protocol 7.3 item 3), so the look's `n`, sums,
radius and endpoints are bit-identical either way. This is cosmetic, but it is an
interface-level deviation from a document that wins on interfaces, so it is recorded here
rather than fixed: fixing it would move a durable write in decision-adjacent code, which is a
coordinator decision, not a test-runner one. **No verifier check constrains this position** —
`monitor.cadence` counts one update per trigger and `monitor.replay` compares values
element-wise; neither pins where in the chain the update sits. That gap is itself worth a
ruling: it is why the stale fixtures kept verifying for as long as they did.

**D-2. ARCHITECTURE §6.2's "survives the pre-freeze pinning of operational values"** is false
as written: `rule_block_sha256` covers the whole `monitor` subtree, which includes `n_max` and
`reference_rule_sha256`, and both are pinned pre-freeze. Reported by G5 in README §5; not
repaired here because the repair is a change to the frozen §6.2 key list.

### 5.2 Where the implementation knowingly differs from ARCHITECTURE §3

**D-3. `lab_server.start` / `lab_server.restart` carry extra keyword-only parameters.**
Flagged at every run by the signature gate in `tests_lab_isolation.py`, which prints:

```
[signature gate] DEVIATION from section 3: lab_server.restart: extra keyword-only parameter(s) ['golden', 'sampling']
[signature gate] DEVIATION from section 3: lab_server.start:   extra keyword-only parameter(s) ['golden_props', 'golden', 'sampling', 'timeout_s', 'recompute_gguf_sha256']
```

Both are **additive and backward compatible**: every new parameter is keyword-only with a
default, and the §3 positional forms `start(spec)` and `restart(spec, golden_props)` still
work, so nothing written against §3 breaks. The gate reports them as INFO rather than as a
failure. I neither silenced the INFO (that would be the weakening this pass exists to prevent)
nor promoted it to a failure — whether an additive superset of a §3 signature is permitted is a
coordinator ruling, and §10's "nobody edits another group's file" puts `lab_server.py` out of
reach in any case.

### 5.3 Open defects G5 reported and did not work around

Carried forward from README §5; all still open, none of them masked by a test:

* ~~**`inv` in the T4 identity payload.**~~ **CLOSED 2026-09-20** by the repair of
  execution-review finding E3, pre-freeze. `Job` carries `inv`, and the removal list of
  PG-14 / protocol 12.3 did not remove it, so the two canonical payloads of a T4 pair
  differed whenever one position was dispatched by a later invocation — precisely the resume
  case of protocol 6.4 rows 11c–11e. `t4.payload_identity` is a FAIL on condition list B, so
  the false positive would have dropped claims 2–5 and 7 for T4 on a run in which nothing
  scientific had changed. `inv` is now in the removal list in `lab_worker.CANONICAL_JOB_DROP`,
  in `lab_orchestrator.canonical_job_payload` and in protocol 12.3, for the same reason
  `worker_index` always was: the invocation id is a property of the dispatch, not of the arm.
  The test that asserted the defect now asserts the repair on the same crash-and-resume path
  (`test_t4_payload_identity_survives_a_pair_spanning_two_invocations`), and it also checks
  that genuine configuration drift between the two arms of a pair still fails.
* **`monitor_update` at the horizon (ARCHITECTURE 7.1 row 4a)** would be a look with no
  trigger in the closed enum. Unreachable in practice: the last reveal's look already
  satisfies `decide`'s horizon condition and the decision quotes it.
* **Three names for one quantity**: the spool fsync cost is `fsync_ms` in §3.9,
  `fsync_ms_prev` in §5 and `spool_fsync_ms` in T14. The orchestrator maps §5 → T14.
* **`lab_worker.terminal_reveal` is duplicated** in `lab_orchestrator.terminal_outcome`,
  because §3.16 forbids the orchestrator to import `lab_worker`. Moving it to `lab_common`
  would remove a duplication in decision-adjacent code.

### 5.4 Test-name drift from ARCHITECTURE §9

§9 lists **97** tests (one row each). All 97 are implemented, but **24** of them under longer
identifiers — e.g. §9's `test_monitor_cadence` is `test_looks_match_the_cadence_of_protocol_8_3`,
and `test_worker_terminal_states` is split across `test_worker_death_is_terminal`,
`test_hard_cap_is_computed_and_terminal` and `test_worker_error_exits_three`. No §9 entry is
missing. A reviewer grepping §9's names verbatim will get 24 false misses; the mapping is
mechanical and worth pinning in §9 before the freeze. (The suite has 304 tests against §9's 97
because the groups split many §9 rows into several cases, and because `subTest` fan-out —
29 chain fixtures, 9 enclosure combinations — is counted once per §9 row.)

---

## 6. What is not green: an unreproduced flake

Of the **eight** whole-suite `unittest discover` runs made after the fix, **seven** reported
`OK (304 tests)` and **one** reported `FAILED (failures=1)`. I did not capture which test
failed — that run was piped through `grep` for the summary line and the failure block was
lost — and **I could not reproduce it in 20 subsequent runs**:

| re-run | result |
|---|---|
| whole-suite `unittest discover` | **5 more, all `OK (304)`** — including a final clean-tree run, `exit=0`, 0 `FAIL:`/`ERROR:` lines |
| per-file sweep of all six files | **2 sweeps, 304/304 each** |
| `tests_lab_serving.py` alone | **6 runs, all OK** |
| `tests_lab_e2e.py` alone | **6 runs, all OK** |

I am recording it rather than calling the suite clean, because a flake that appears once in
eight runs and then hides for twenty is exactly the kind of thing a pre-registered harness
cannot afford to discover during the live trial. The most likely candidates are the wall-clock-bounded
polling loops in `tests_lab_serving.py` (`tests_lab_serving.py:1132`, `:1188`, `:1258` — 30 s,
30 s and 180 s deadlines around `spawn`/`killpg` of real subprocesses) and the resume matrix in
`tests_lab_e2e.py`. Those loops `break` on success but fall through to the assertions on
timeout, so under load they fail on an incomplete spool rather than reporting a timeout.

**Recommended before the freeze:** convert those three loops to raise an explicit
`TimeoutError` naming the deadline instead of falling through to the assertion, so the next
occurrence identifies itself. That is a test-infrastructure change with no effect on any
scientific rule, but it changes another group's test file and I have left it to the owner.

### 6.1 Two tests that are weaker than they look

Not failures, and not mine to rewrite, but a hostile reviewer will find them, so they are
recorded rather than left to be discovered:

* **`test_no_certificate_from_tokens_and_no_betting`** (`tests_lab_chain.py:1648`) and
  **`test_no_betting_in_the_decision_path`** (`tests_lab_isolation.py:167`) enforce PG-16 by
  grepping the source text for the literal strings `'betting'` and `'completion_tokens'`.
  A token-based prediction under any other variable name would pass both. The underlying
  property does hold on inspection — `lab_enclosure` declares exactly two tiers, `success` and
  `latency_s`, with the comment "`completion_tokens` is RECORDED and NEVER SCORED", and
  `certified_elapsed` narrows an enclosure only from observed monotonic stamps (refusing, not
  repairing, a clock anomaly) — but the *tests* check spelling, not behaviour.
* The first of the two greps only `lab_reference_rule.py`; `lab_enclosure.py`, which is where
  the cost certificate actually lives and which legitimately mentions `completion_tokens`
  13 times, is not covered by an equivalent behavioural assertion.

---

## 7. Facts still to be pinned in the pre-freeze phase

Every `null` in `config.json`, with the rule that pins it (the rules are from protocol
Appendix A and README §2 — none of these is a value to be invented):

| key | pinned by |
|---|---|
| `monitor.n_max` | `roster.n_pairs` at freeze time, never later; a mismatch raises `FrozenMismatch` (PG-21) |
| `monitor.reference_rule_sha256` | `sha256(lab_reference_rule.py)` when the freeze bundle is assembled (protocol 14.2 row 10) |
| `roster.n_S1`, `n_S2`, `n_total`, `n_pairs` | `lab_data.build_roster` after the exclusions of protocol 3.2; `n_pairs = floor(n_S1/2) + floor(n_S2/2)` (3.3) |
| `roster.roster_sha256`, `roster.task_content_sha256` | canonical hashes of the built roster and the full task objects (3.1, 14.2 row 1) |
| `servers.coder.sha256_recomputed`, `servers.t3.sha256_recomputed` | recomputation of the GGUF digest at preflight (2.3, Appendix A) |
| `servers.*.license_evidence_sha256` | the LICENSE downloads of protocol 5.8 item 8 |
| `llama_cpp.build_flags_sha256`, `llama_cpp.serving_manifest_sha256` | the serving build of protocol 2.2 (5.8 item 1) |
| `receipt.golden_props_sha256.{coder,t3}` | the `/props` capture of protocol 13.2, validated at 100 % on the rehearsal (5.8 item 6) |
| `receipt.golden_generation_settings_sha256.{coder,t3}` | the `__verbose.generation_settings` capture of protocol 13.2 |
| `execution.request_timeout_s` | `max(180, 30*ceil(4*c_max/30))` from the calibration plan of 5.8 item 3 (5.6) |
| `execution.episode_hard_cap_s` | `4*(3*T + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60`, **computed, never typed** (PG-15); `lab_orchestrator.episode_hard_cap_s` |
| `sandbox.profile_sha256` | the Seatbelt profile text resulting from the trial's `TMPDIR` (5.7 item 2) |
| `sandbox.containment_probe_sha256` | the two-worker containment probe of 5.7 item 3 |
| `anchor.posting_latency_p95_s` | the 95th-percentile posting latency from the anchor drill of 12.4 item 10 (12.6 item 4) |
| `prefreeze.side_by_side_compression_C.{T1,T2,T3,T4}` | the compression statistic of 5.8 item 4, one per contrast |
| `hardware_allowlist` | the host identity recorded pre-freeze (2.1) |
| `environment_lock_sha256` | the package lock of the invocation environment (14.2) |

Operator steps that cannot be done from this session:

1. **D6, the anchor drill** (protocol 12.4 item 10) — it commits to a git repository and this
   session is forbidden to run a state-changing git command. The property it checks (the
   anchor commits to the segment **prefix** preceding its own line) is asserted directly
   against the bytes by `test_anchor_prefix`; the drill against the real remote, and the
   `posting_latency_p95_s` it yields, remain a pre-freeze operator step.
2. **The rehearsal** that validates `golden_props` at 100 % (5.8 item 6) and the calibration
   that yields `c_max` (5.8 item 3) — both need the real models running.
3. **Coordinator ratification of G5's three cadence corrections** to `lab_monitor` and
   `lab_reference_rule` (README §4). These are decision-defining code (protocol 14.3) and must
   be ratified, not merely merged.
4. **Test hardening** (none of it touches a scientific rule, all of it is in another group's
   file): raise an explicit `TimeoutError` in the three wall-clock loops of §6; turn the ten
   dormant `skipTest` guards of §3 into hard failures; replace the two spelling-based PG-16
   greps of §6.1 with behavioural assertions.
5. **A ruling on D-1 and D-3 above**, and on whether the verifier should pin the chain position
   of `monitor_update(enroll)` rather than only its count and values.

---

## 8. Independent checks run by this pass (not via the suite)

These were computed from the raw bytes of a real `run_dry` chain and from `src/winstats.py`
directly, deliberately bypassing `lab_monitor`, `lab_verify_log` and the tests, so that a bug
shared between the implementation and its own tests would still show up.

| check | result |
|---|---|
| `winstats.normal_mixture_radius` vs. the **closed form typed straight from protocol_FINAL.md line 183**, `r(n) = sqrt((n+100)·log((n+100)/(100·0.00625²)))/n`, at all 12 pinned table rows | **0.0 worst difference** (bit-identical) |
| the alpha budget: program `0.05` / 4 trials / 2 scores | `= 0.00625` = `config.monitor.alpha_gate` ✓ |
| `band()` vs. the protocol formula recomputed from `winstats.normal_mixture_radius(n, alpha=0.00625, rho=100., variance_process=n)`, over 2004 cases incl. `n = 1, 100, 150, 568` | **0 mismatches** |
| `dryrun_live_ab.py --radius-table` (D7) regenerated and compared to `testdata/radius_table.csv` | **agrees: True** |
| the chain-fixture generator is deterministic: two independent `write_fixtures()` runs, then both against the committed tree | **byte-identical**, and the committed tree matches a fresh regeneration |
| D4 (A/A) on three further seeds beyond the committed one | all four abstain: `horizon_no_decision`, bands straddling zero (`L_h ≈ -1.0…-0.96`, `U_h ≈ +0.76…+0.96`) |

On that last row, the protocol's own caution applies and I am not going to overstate it: **four
A/A runs establish no error rate and demonstrate no equivalence.** They are a smoke test that
the null path does not obviously crash or obviously cross. Had one crossed, protocol guidance
item 8 requires it to be printed and investigated, never discarded — which is what D4 exists to
make possible, not to rule out.
| every `monitor_update` in a live 257-event chain: `L_j = sum(lower_j)/n - r`, `U_j = sum(upper_j)/n + r`, clipped | 84 updates recomputed, **worst absolute difference 0.0** |
| clip to `[-1, 1]` honoured at every update | **no violations** |
| `seq` contiguity and `prev == previous h` over the whole chain | 257 links, **0 defects** |
| one `coin_drawn` per pair, and no `episode_started` for a pair before its coin | 12 pairs, **0 violations** |
| each arrival executed under exactly one arm, unchanged between start and reveal | 24 started, 24 revealed, **0 arm flips**, 0 double reveals |
| each pair is exactly one `incumbent` and one `candidate` | **all 12 pairs** |
| the `decision` event immediately follows the `monitor_update` it quotes, at the same `n` | **holds** |
| every `enroll` look enters the new pair at the full enclosure `h = s = [-1, 1]`, not collapsed | 12 of 12, **no prediction** |
| no pair's enclosure ever widens, over the whole chain | **0 widening events** |
| `n` non-decreasing, `+1` at exactly the `enroll` trigger, unchanged at every other trigger | **0 violations** |
| ARCH 7.1 row 3, "no coin before the start-anchor receipt" | first receipt at index 4, first `coin_drawn` at index 7 — **holds** |
| every `anchor` commits to the segment **prefix** preceding its own line (`upto_seq == seq-1`, `upto_h == previous h`) — the D6 property, checked against the bytes | 3 anchors, **0 violations** |
| the blocking anchors are exactly `trial_started`, `decision`, `trial_ended` | **as specified** |

And the full **D1** trial (60 pairs), which actually decides, read back from its chain:

| check | result |
|---|---|
| the decision | `harm_keep_incumbent` at `n = 39`, `U_h = -0.0214` — the harm rule `U_h < 0` **holds at the quoted prefix** |
| exactly one `decision` event in the whole chain (no second crossing, no re-decision) | **1** |
| protocol 9.1 item 4 / ARCH 7.1 row 12: after the decision the only look is a `drain` | **no `monitor_update` at all** after it (nothing was in flight — the decision was taken at a reveal) |
| every reveal after the decision is flagged `post_decision = true` (ARCH 7.1 row 16, no look) | **42 of 42** |
| ARCH 7.1 row 14: no follow-up dispatch before the decision-anchor receipt and `traffic_switch` | 42 `arm_assigned_by_decision`, **all strictly after** the switch |
| the follow-up cohort is routed to the decided arm only | **`{incumbent}`** — the harm decision was acted on |

And the full **D3** trial, the other decision branch:

| check | result |
|---|---|
| the decision | `deploy_candidate` at `n = 44`, `L_h = +0.0702`, `L_s = -0.8844`, `delta = 0.90` |
| deploy rule, both conditions at the same prefix | `L_h > 0` **true**, `L_s > -delta` **true** |
| harm is tested first and does not fire | `U_h < 0` **false** |
| the `decision` quotes the immediately preceding `monitor_update`, same `n` | **holds** |
| `traffic_switch`, then 32 follow-up assignments, all after it, all to the decided arm | **`{candidate}`** |
| the mock tree records both overrides | `{"monitor.delta": 0.9, "monitor.n_min": 30}` |

**The success guard is not vacuous, and D2 is the clearest evidence in the whole harness.**
D2 is D3's scenario under the **frozen** `delta = 0.03` (its only override is `n_min`, never
`delta`), and it reads:

```
D2: kind=horizon_no_decision  n=40  L_h=+0.0421  L_s=-0.9579  delta=0.03
      L_h > 0       -> True      (the hierarchy says the candidate wins — it is much faster)
      L_s > -delta  -> False     (the frozen success margin refuses)
      => deploy needs BOTH, so the trial ABSTAINS
```

A candidate that is dramatically faster but whose success rate is not established as
non-inferior **cannot deploy**: the latency win alone never carries the decision. D3 reaches
`deploy_candidate` on the same data only because its mock `delta = 0.90` is wide enough to
swallow `L_s = -0.8844`. A reviewer who reads "D3 deploys" and stops there will draw exactly
the wrong conclusion about the frozen rule; D2 is the one that shows what it does.

And four tamper trials against a copy of that same live trial tree, to confirm the verifier's
teeth are real and not an artefact of the committed fixtures:

| mutation | verdict |
|---|---|
| none (control) | **PASS**, no FAIL/DEFECT findings |
| one `monitor_update`'s `L_h` raised by 0.5 | **FAIL** (`chain.read`) |
| one `monitor_update` deleted | **FAIL** (`chain.read`) |
| a `coin_drawn`'s two arm assignments swapped | **FAIL** (`chain.read`) |

Worth knowing: all three trip `chain.read` — the hash chain catches the edit before any
semantic check runs. That is the correct and strongest response, but it means the *semantic*
checks (`monitor.replay`, `coin.*`, `enclosure.*`) are only exercised by the committed defect
fixtures, which re-chain after mutating so that the hashes stay valid. Both layers are needed
and both are tested; a reviewer should not read a `chain.read` FAIL as evidence that the
semantic layer works.

---

## 9. What a hostile reviewer should check first

* `monitor.replay` and `monitor.cadence` agree element-wise with `lab_reference_rule`, which
  imports neither `lab_monitor` nor `lab_enclosure`
  (`test_reference_rule_imports_nothing_from_the_lab_namespace`).
* No radius anywhere is hand-typed: `testdata/radius_table.csv` and
  `testdata/monitor_fixtures.json` are asserted byte-equal to a fresh regeneration from
  `src/winstats.py` (`test_radius_table_file`, `test_monitor_fixtures_file`).
* The coin is fsynced before either episode of its pair is dispatched
  (`defect_coin_write_ahead.jsonl`, `defect_coin_one_per_pair.jsonl`).
* Enclosures never widen and always contain the ultimately revealed score, **at every recorded
  evaluation** (`defect_enclosure_monotone.jsonl`, `defect_enclosure_containment.jsonl`).
* `config.json` is protocol Appendix B verbatim (`test_config_is_appendix_b_verbatim`).
* **The denominator is the full enrolled prefix, never the completed count** (guidance item 2,
  protocol 7.3 item 5) — the trap that would silently inflate every band. `test_completed_prefix_readout`
  pins it: with 120 enrolled and 101 collapsed, `snapshot()["n"] == 120`, while the
  completed-prefix band (`n = 100`) is logged as a read-out only and is asserted to be
  *strictly higher* than the decisive `L_h`, which is the direction that would have favoured
  deploying.
* The coin is `os.urandom(8)`, `bit = raw[0] & 1`, one per pair, with **no side effect between
  the draw and the durable append** (`lab_coin.draw_and_commit`), so nothing can observe the
  coin and act on it before it is on disk.
* The four open defects in §5.3 are implemented **as written** and asserted to misbehave, not
  worked around.
* The decision rule is protocol 8.4 verbatim and in the fixed order — harm (`U_h < 0`) is
  tested before deploy (`L_h > 0` **and** `L_s > -delta`), both on the same current prefix, and
  both sit *after* the `n < n_min` guard in `lab_monitor.decide`, so the only decision kind
  reachable below 100 enrolled pairs is the abstention. The protocol's display labels
  (`HARM_RETAIN_INCUMBENT`, `DEPLOY_CANDIDATE`, `ABSTAIN_AT_HORIZON`) and the chain enum
  (`harm_keep_incumbent`, `deploy_candidate`, `horizon_no_decision`) are the same three
  outcomes under two spellings; ARCHITECTURE §3 line 893 fixes the enum, so this is not a
  deviation.
