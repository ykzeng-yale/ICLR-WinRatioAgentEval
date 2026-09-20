# `experiments/live_ab/` — the prospective randomized live-stopped A/B harness

Integrator's file (G5).  The binding documents are `protocol_FINAL.md` (scientific rules)
and `ARCHITECTURE_FINAL.md` (interfaces); where they disagree the protocol governs the rule
and the architecture governs the interface, and every disagreement found during integration
is listed below rather than silently resolved.

*Prepared and checked by AI agent sessions; not human peer review or author sign-off*
(protocol 14.7).

---

## 1. What runs what

```
lab_orchestrator.py --trial T4 --config results/live_ab/freeze/config.json [--resume]
lab_anchor.py       --trial T4 --config ...            # separate process, spool only
lab_verify_log.py   --trial T4 [--mode plumbing|full]  # after every trial
build_live_ab_results.py --bundle <sha> --out ...      # after the LAST trial
dryrun_live_ab.py   --scenario D1|D2|D3|D4|all         # mock, no model
dryrun_live_ab.py   --radius-table --out <path>        # D7
```

The orchestrator is the **only writer of a chain** (AD-2).  Workers and the anchor process
write spools; the orchestrator ingests them and turns them into chain events.  One OS
process per episode, no pipe, no threads (AD-1).

Three properties are structural rather than asserted afterwards:

1. **The look cadence is not re-implemented in the orchestrator.**  After every appended
   event of a type `lab_monitor.replay` consumes, the orchestrator replays the in-memory
   chain and writes the looks the replay produced that the chain does not yet carry, using
   the replay's own snapshots as the bodies.  `monitor.replay` therefore cannot fail on
   cadence or on a float.  The live `MonitorState` is maintained in parallel only so that
   the frozen `lab_monitor.decide` runs on a real state, and its snapshot is compared with
   the replay's at every look: a difference raises `MonitorError` and pauses the trial.
2. **The shadow is a second code path.**  `lab_reference_rule.looks_from_chain` is evaluated
   on the same chain at every look and its values fill `monitor_update.shadow`.  A mismatch
   takes `trial_paused(monitor_mismatch)` before any decision is acted on (protocol 8.9).
3. **Resume is a pure function.**  `plan_resume` reads nothing and writes nothing; the
   resume path is `read_chain` → `plan_resume` → apply the plan as durable appends.

`cfg['_runtime']` is a **runtime overlay** (result roots, mock ports, the worker command,
dry-run limits).  It is never part of the frozen file, never hashed into the bundle and
never read by a rule: every hash and every statistical call goes through
`lab_orchestrator.frozen_cfg(cfg)`, which strips every key beginning with `_`.

---

## 2. `config.json`

The committed `config.json` is the JSON block of `ARCHITECTURE_FINAL.md` §6.1 **verbatim**,
which is byte-identical to protocol Appendix B (checked by
`tests_lab_e2e.ConfigTests.test_config_is_appendix_b_verbatim`).  `results/live_ab/freeze/config.json`
is a byte copy of it.

Every `null` below is pinned in the pre-freeze phase **by the rule named here** (protocol
Appendix A) and no `null` may survive into the freeze bundle.  Nothing in this table is
invented; each entry is the rule, not a value.

| key | pinned by |
|---|---|
| `monitor.n_max` | `roster.n_pairs` at freeze time, and never later; a mismatch between them raises `FrozenMismatch` (PG-21) |
| `monitor.reference_rule_sha256` | `sha256(lab_reference_rule.py)` when the freeze bundle is assembled (protocol 14.2 row 10) |
| `roster.n_S1`, `roster.n_S2`, `roster.n_total`, `roster.n_pairs` | `lab_data.build_roster` after the exclusions of protocol 3.2 (rules 1–3 blind, rule 4 the reference sweep of 5.8 item 5); `n_pairs = floor(n_S1/2) + floor(n_S2/2)` (protocol 3.3) |
| `roster.roster_sha256`, `roster.task_content_sha256` | the canonical hashes of the built roster and of the full task objects (protocol 3.1, 14.2 row 1) |
| `servers.coder.sha256_recomputed`, `servers.t3.sha256_recomputed` | recomputation of the GGUF digest at preflight; the `sha256_expected` values are expectations (protocol 2.3, Appendix A) |
| `servers.coder.license_evidence_sha256`, `servers.t3.license_evidence_sha256` | the LICENSE downloads of protocol 5.8 item 8 |
| `llama_cpp.build_flags_sha256`, `llama_cpp.serving_manifest_sha256` | the serving build of protocol 2.2 (5.8 item 1) |
| `receipt.golden_props_sha256.coder`, `receipt.golden_props_sha256.t3` | the `/props` capture of protocol 13.2, validated at 100 % on the rehearsal (5.8 item 6) |
| `receipt.golden_generation_settings_sha256.coder`, `receipt.golden_generation_settings_sha256.t3` | the `__verbose.generation_settings` capture of protocol 13.2 |
| `execution.request_timeout_s` | `max(180, 30*ceil(4*c_max/30))` from the fixed calibration plan of protocol 5.8 item 3 (protocol 5.6) |
| `execution.episode_hard_cap_s` | `4*(3*T + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60`, **computed from the formula and the pinned `request_timeout_s`, never typed** (PG-15); implemented by `lab_orchestrator.episode_hard_cap_s` |
| `sandbox.profile_sha256` | the Seatbelt profile text resulting from the trial's `TMPDIR` (protocol 5.7 item 2) |
| `sandbox.containment_probe_sha256` | the two-worker containment probe of protocol 5.7 item 3 |
| `anchor.posting_latency_p95_s` | the 95th-percentile posting latency measured in the anchor drill of protocol 12.4 item 10 (12.6 item 4) |
| `prefreeze.side_by_side_compression_C.T1`, `prefreeze.side_by_side_compression_C.T2`, `prefreeze.side_by_side_compression_C.T3`, `prefreeze.side_by_side_compression_C.T4` | the compression statistic of protocol 5.8 item 4, one per contrast |
| `hardware_allowlist` | the host identity recorded in the pre-freeze phase (protocol 2.1) |
| `environment_lock_sha256` | the package lock of the invocation environment (protocol 14.2) |

`rule_block_sha256` covers only the 19 dotted keys of §6.2, so pinning any of the rows above
leaves it unchanged — **except** `monitor.n_max` and `monitor.reference_rule_sha256`, which
are inside the `monitor` subtree.  That is a defect of §6.2's own sentence, not of the key
list; it is reported below.

---

## 3. What the dry runs are, and what they are not

`dryrun_live_ab.py` exercises the **whole program** with no model: the chain, the coin, the
monitor, the shadow, the decision, the blocking anchors, the traffic switch, the follow-up
cohort, the resume path and the verifier are the production code.  Only two things are
doubles:

* the **simulated worker** (`run_sim_episode`), which writes the section-5 spool contract
  and a record file.  Its `latency_s` is forced to dominate the certified elapsed time built
  from its own stamps, because an episode whose reported latency fell below its own
  certificate would make a cost certificate false — the containment audit catches exactly
  that, and it did during integration;
* the **mock anchor receipt** (`lab_anchor --mock-receipt`), which is a hash of the local
  anchor file and carries **no external evidence of any kind**.  A trial's blocking anchors
  require real receipts.

Every derived file of a dry run carries `"mock": true` and a `MOCK` banner, and the mock
freeze tree records any mock-only override (D3's wide margin, the dry runs' small screening
prefix) under `mock_overrides`.

| id | what it shows |
|---|---|
| D1 | the candidate clearly worse → `harm_keep_incumbent`, with a drain and a follow-up cohort |
| D2 | equal success, the candidate faster, the **frozen** margin refuses → `horizon_no_decision` |
| D3 | as D2 with a mock-only wide margin → decision, blocking anchor, switch, follow-up ledger |
| D4 | A/A; one run establishes no error rate and demonstrates no equivalence, and a crossing would be printed and investigated, never discarded |
| D5 | chaos: crashes at several points, each resumed; verifier PASS, no second coin, no second reveal, no re-run |
| D6 | **not executed here.**  The anchor drill commits to a git repository, and this session is forbidden to run a state-changing git command.  The property it checks — the anchor commits to the segment **prefix** preceding its own line — is asserted directly against the bytes by `test_anchor_prefix`.  The real drill against the real remote remains a pre-freeze operator step (protocol 12.4 item 10) |
| D7 | `--radius-table`: every radius regenerated from `src/winstats.py`; no radius is hand-typed |

---

## 4. Integration findings

Three cadence corrections were made to other groups' modules.  Each is derived from the
protocol text, each is proven by a test in `tests_lab_e2e.py`, and each must be ratified by
the coordinator before the freeze, because `lab_monitor` and `lab_reference_rule` are
decision-defining code (protocol 14.3).

The reason they could not be worked around: `lab_verify_log` compares the logged **trigger
sequence** with `lab_reference_rule` (`monitor.cadence`) and the logged **values** with
`lab_monitor.replay` (`monitor.replay`), both element for element.  When the two modules
disagree about the look list, **no chain whatever can satisfy both**, so the verifier FAILs
on a correct run.  The orchestrator cannot choose a shape that pleases both.

1. **`lab_monitor.replay` emitted a `call` look after a decision.**  Protocol 9.1 item 4 and
   ARCHITECTURE 7.1 row 12 say that after a decision the only look is the drain reveal.
   Fixed in `lab_monitor.replay` by skipping call events once a `decision` has been seen.
   Proof: `CadenceAgreementTests.test_no_look_after_a_decision_except_the_drain_reveal`
   (before the fix a harm decision taken at the first reveal of a pair, with the partner
   still spooling, paused the trial with a false `monitor_mismatch`).
2. **`lab_reference_rule` emitted its `resume` look at `invocation_started`.**  Protocol 8.3
   trigger 4 places it "at the last fully enrolled prefix **before any new enrollment**",
   and protocol 14.5 reveals recovered orphans (items 3 and 6) *before* the resume
   evaluation (item 4).  Fixed by deferring the look to just before the next enrollment, and
   suppressing it after a decision (9.1 item 4) and when the resumed invocation produced no
   evaluation-bearing event.  Proof:
   `CadenceAgreementTests.test_resume_look_is_after_the_orphan_reveals`.
3. **`lab_reference_rule` emitted its `enroll` look at `pair_enrolled`.**  Protocol 7.3
   item 2 defines `n` as "the count of chain-valid `coin_drawn` events" and says it "changes
   only at a `coin_drawn`", and ARCHITECTURE 7.1 rows 5–6 write the enroll `monitor_update`
   in state `COMMITTED`, after the coin.  Fixed by staging a pre-enrolled pair and admitting
   it at its coin.  Proof:
   `CadenceAgreementTests.test_a_pair_enrolled_without_a_coin_holds_no_position` (a crash
   between `pair_enrolled` and `coin_drawn` otherwise puts the two modules in different
   orders about the re-enrolled pair).

**Consequence for G1's fixtures — RESOLVED by the test-runner pass.**  When finding 3 landed,
`testdata/chains/` was stale with respect to its own generator, which still placed the enroll
`monitor_update` at the `pair_enrolled`, and
`tests_lab_chain.FixtureTests.test_committed_fixtures_match_the_generator` failed for all 29
fixtures.  (The committed fixtures still **verified** throughout, asserted by
`CadenceAgreementTests.test_committed_chain_fixtures_still_verify`.)  The integration pass moved
the generator's `sync(i)` call from after `pair_enrolled` to after `coin_drawn` — matching
`lab_orchestrator._w_draw_coin`, which calls `evaluate()` on the coin — and regenerated the 29
fixtures with `./.venv/bin/python experiments/live_ab/tests_lab_chain.py --write-fixtures`.
The generated chains now place the enroll `monitor_update` immediately after `coin_drawn`,
exactly as a real orchestrator run does.  See `IMPLEMENTATION_STATUS.md` §4.

---

## 5. Open defects reported, not worked around

* **`inv` in the T4 identity payload.**  `Job` carries `inv` and the frozen removal list of
  PG-14 / protocol 12.3 does not remove it, so the two canonical payloads of a T4 pair
  differ whenever one position is dispatched by a later invocation — which is exactly
  protocol 6.4 rows 11c–11e.  `t4.payload_identity` is a FAIL on condition list B, so this
  false positive would drop claims 2–5 and 7 for T4.  Implemented verbatim and asserted by
  `test_t4_payload_identity_breaks_when_a_pair_spans_two_invocations`.  The repair is one
  word: add `inv` to the removal list, for the same reason `worker_index` is already in it.
* **§6.2's "survives the pre-freeze pinning of operational values"** is false as written: the
  rule block contains the whole `monitor` subtree, including `n_max` and
  `reference_rule_sha256`, which are pinned pre-freeze.
* **`monitor_update` at the horizon (ARCHITECTURE 7.1 row 4a)** would be a look with no
  trigger in the closed enum.  It is unreachable in practice: the last reveal's look already
  satisfies `decide`'s horizon condition, and the decision quotes it.
* **Three names for one quantity**: the spool fsync cost is `fsync_ms` in §3.9,
  `fsync_ms_prev` in §5 and `spool_fsync_ms` in T14.  The orchestrator maps §5 → T14.
* **`lab_worker.terminal_reveal` is duplicated** in `lab_orchestrator.terminal_outcome`
  because §3.16 forbids the orchestrator to import `lab_worker`.  Moving it to `lab_common`
  would remove the duplication in decision-adjacent code.

---

## 6. Running the tests

```
cd <REPO> && \
  ./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'
```

`tests_lab_e2e.py` alone takes a few minutes: the resume matrix runs a whole trial per kill
point.  Nothing in it starts a model, opens a non-loopback socket, or changes git state.
