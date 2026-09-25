# Design proposal v2: EB2-EB4 model-free drivers + EB5 loaded-phase preparation

Read-only synthesis for root. Revises `DESIGN_PROPOSAL.md` (v1) in response to `CRITIQUE_OF_v1.md`'s four
findings. Base: worktree `wt-eb1` at HEAD `c62b59b71cf6caa468069575b6c488ae2995330d`
(branch `session60/repair-eb1`), fetched clean, nothing edited/committed/checked-out/reset/stashed
here or in any repo checkout (`git status --porcelain` empty before and after, including after the
read-only `git merge-tree` re-run below). Accepted base tag `session60-eb1-eb5-subset-v1` = `c7750a3`.
Built from the six area maps in `experiments/live_ab_drivers/design_notes/` plus fresh re-reads of `map_replay.md` in full
(the synthesizer's structured result for the replay area was empty — see §7 and §11.5's row in §2,
both re-verified directly against `map_replay.md` this pass) and direct re-reads of the three named
`origin/main` review files for exact quotes. Nothing in this file has been executed, built, or run; it
is a proposal only, for root to accept, amend, or reject. A "Changes from v1" list is at the end,
followed by a <=40-line issue-comment-ready summary.

---

## 1. What root's 20:40 / 21:14 / 22:20 reviews require for "action (2)"

**20:40 go/no-go, ranked item 2** (`reviews/prerun_bundle_go_nogo_20260923_2040.md:17`, origin/main,
re-verified this pass):

> "**EB2–EB4: complete only the missing executable drivers** for stages 1, 2, 4–6, the stage-3
> two-stream loaded sweep, and the §11.5 extended CPU replay/seed. Show each driver consumes the
> frozen schedule and writes immutable attempts, failures, missingness, usage and actual timestamps.
> Do not run the loaded stages or repeat the accepted CPU grid while implementing them. The four
> absent conformance prompts must be fixed in a synchronized pre-outcome config/protocol/architecture
> amendment before stage 1..."

(The conformance-prompt amendment is already done — `config.json` has `oodp/1..4` populated at
`config.json:209-218`, re-verified this pass byte-for-byte, per `map_stage1.md` — so only the driver
work remains open from this item.)

**21:14 restart-cap ruling, items 2 and 3** (`reviews/restart_cap_estimand_ruling_20260923_2114.md:18-19`,
origin/main, re-verified this pass):

> "2. **Deliver reviewable increments.** ... first send exact immutable EB1 lifecycle and EB5
> resolution code/controls on the owned branch, with old/new hashes and no loaded run. Root will
> review that subset promptly; then deliver the missing prefreeze drivers and four prospectively
> fixed, distinct out-of-design conformance prompts. A review of an interim subset is not trial
> clearance. Keep all execution-affecting drivers in the harness pin and controls outside its glob."
>
> "3. **Do not hide unresolved design choices behind `PROPOSED` schedules.** Such drivers may be
> built model-free as parameterized scaffolds, but no stage executes and no freeze is accepted until
> root explicitly resolves the named ODs, golden reference request, §11.5 outcome model, rehearsal
> chain, versioned config/protocol/architecture and actual host window. Rehearsal evidence belongs to
> `_prefreeze` per §5.8/§12.1 and must remain outside trial inference. Maintain owner responsibility
> for execution and immutable completed-shard receipts."

**22:20 bounded EB1+EB5 subset review, "Disposition and next work"**
(`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:19`, origin/main, re-verified this pass):

> "Session60 may then advance its already assigned EB2–EB4 model-free drivers and EB5 loaded-phase
> preparation, with exact code/config/seed pins and incremental immutable completed-shard receipts. The
> loaded phase still needs named server/capacity evidence and actual production-path EB5 worker
> resolution; **the complete paired AB/BA assignment, enrollment-indexed partial bounds, simultaneous
> error allocation, scientific guardrails, stopping/estimand rules, serving/usage provenance and freeze
> inputs still need explicit root review.** No loaded/design/trial episode is approved."

The seven items in bold are cross-walked individually into §6's blocked table this pass (CRITIQUE
finding 4) rather than left inside the block quote only.

**Synthesis of the ask.** Build, as separately reviewable increments on a new branch, the missing
*executable* drivers for: §5.8 stage 1 (golden capture + conformance), stage 2 (counter-semantics),
the stage-3 two-stream loaded sweep and EB5 worker-resolution preparation, stages 4-5 (calibration),
stage 6 (dress rehearsal + injected-decision fixture — see §2's corrected split below), and §11.5
(extended CPU replay/seed) — model-free wherever the driver can be exercised against
`lab_mock_server`/fixtures, each carrying exact code, config, seed and data-digest pins and a
write-once, incremental, per-shard receipt. No stage may execute for real, no loaded/design/trial
episode may run, and no PROPOSED value may be silently treated as adopted.

---

## 2. Per-driver table: requires / exists / missing / model-free? / controls

| Driver (§5.8 item) | Protocol requires | Exists at c62b59b | Missing | Model-free buildable | Controls, incl. a required negative control |
|---|---|---|---|---|---|
| **Stage 1** — serving receipt/golden/template/conformance | Serving build+manifest, then receipt smoke + golden-object capture per server; template + format-conformance rule (>=9/10 of 10 fixed prompts contain a code block); all writes go to the `_prefreeze` chain, never used for design (`protocol_FINAL.md:1355-1356`; `ARCHITECTURE_FINAL.md:190-192`; `protocol_FINAL.md:1337-1356,3018,3773`) | `lab_server.start(mode='capture')` (the real EB1-repaired capture path, `lab_server.py:403-479`); `tokenized_props` (`lab_server.py:212-244`); `load_golden_objects`/`observed_bundle_members` as read-only consumers (`lab_orchestrator.py:1567-1610,1670-1699`); conformance prompts populated in config (`config.json:209-218`) | The golden-request driver (chicken-and-egg: `LlamaClient.__init__` requires a `golden: GoldenReceipt` already, `lab_client.py:399-410,247-257`); the writer for `golden_props_<server>.json`/`golden_generation_settings_<server>.json`; the conformance counter over the 10 prompts; any orchestrated stage-1 entry point (`map_stage1.md:149-179`, "Still MISSING at c62b59b") | Yes — against `lab_mock_server`'s non-streaming `/v1/chat/completions`, exercising client/writer/counter logic and the write-once golden files, with no real model. **Design note (new this pass, see §3 item 4 and §9):** the bootstrap request should be issued by a *new* module that calls the server's HTTP surface directly, not by editing `LlamaClient.__init__`'s mandatory-golden contract in the existing, already-accepted `lab_client.py` — this keeps the golden-capture path from moving an already-pinned file's bytes without cause | Positive: capture on the mock produces byte-identical golden files across two independent captures given the same fixed mock responses. **Negative (must refuse):** feeding the writer a `model_path` that is not the tokenized/canonicalized golden path must raise, mirroring `load_golden_objects`'s existing untokenized-path rejection (`lab_orchestrator.py:1598-1603`); a mock response missing a code block on >=2/10 prompts must make the counter report FAIL, never silently round up to pass |
| **Stage 2** — counter-semantics test (finding N14) | One non-streamed 1,024-token POST with short client timeout, abandoned; `/metrics` scraped immediately before/after (5s timeout, 3 tries); a streamed probe at the same cut point only to learn tokens-generated; the non-streamed result fixes §13.1 claim-6 wording (`protocol_FINAL.md:1357-1361,2864-2868`; `config.json:163`) | Generic `/metrics` helpers `parse_metrics`/`metrics()` (`lab_server.py:349,367`); stream-classification helpers for a *different* diagnostic (`lab_load.py:384,624`); mock scenario flag `count_cancelled_tokens` (`lab_mock_server.py:355`) | The stage-2 driver itself (probe sequence + ledger wiring); a `_prefreeze`-chain runner/writer any driver could share; an `E_PHASE` value for this stage; the §13.1 wording-derivation step (`map_stage2.md:111-126`, "What is MISSING for stage 2") | Yes — toggle `count_cancelled_tokens` true/false on the mock to exercise both counted/not-counted branches and confirm correct §13.1 wording is emitted, no live model | Positive: with `count_cancelled_tokens=true`, driver reports the abandoned tokens as counted and emits the "counted" wording branch. **Negative (must refuse):** force the mock's `/metrics` to fail 3/3 scrapes — driver must mark the probe unreconciled and stop per the plan's stop rule, never guess a delta from one successful scrape |
| **Stage 3 / EB5 prep** — two-stream loaded sweep, worker resolution | Coverage certified only by two distinct server-acknowledged decoding requests/slots over the verifier interval, via pinned server-side lifecycle events on one host monotonic clock — client POST-arrival timing does **not** certify (`reviews/live_load_root_decision_20260922_0237.md`; enforced `lab_prepare.py:472-473,586-600`); every worker resolved before terminal acceptance, unresolved stays unresolved forever (`protocol_FINAL.md:3128-3171,2573`; `ARCHITECTURE_FINAL.md:1764,1777-1783,2213-2215`) | `lab_prepare.run_reference_sweep` gating/refusal logic (`lab_prepare.py:77-155`); `lab_orchestrator.phase_resolution_verdict` pure function, all 4 FAIL branches (`lab_orchestrator.py:706-820,4824-4833`); `lab_lifecycle.observe()` fixture reader, self-flagged incomplete on seq/seal (`lab_lifecycle.py:808-940`); `lab_load.StreamingHttpLoad` ledger (superseded evidence kind, `lab_load.py:624-993`) | The stage-3 two-stream (`stream:false`) load driver itself — both `lab_prepare.py:119` and `lab_load.py:91` state verbatim it "does not exist yet"; a `/slots` endpoint on `lab_mock_server` to exercise the server-busy branch end-to-end (**verified anchor**: `map_stage3_eb5.md:47`, "No `/slots` endpoint... not found by grep"); sequence-number/seal validation in `lab_lifecycle` (**verified anchor**: `lab_lifecycle.py:887-895`, root's own comment: "sequence/seal validation is not yet implemented in the reader") | Partially — `phase_resolution_verdict`, `lab_lifecycle.observe()`, `run_reference_sweep`'s refusal paths, and `start_servers`/`stop_servers` are fully model-free testable now; the driver's *dispatch* scaffolding is model-free buildable but cannot *certify* real concurrent decoding-slot occupancy without the real patched server | Positive: two fixture load sources that both report `resolution()==RESOLVED` with >=1 tracked POST each are accepted by `run_reference_sweep`. **Negative (must refuse):** a `scripted_fixture`/zero-intent source, or any source still unresolved, must be rejected by `run_reference_sweep` exactly as it already does (`lab_prepare.py:126-155`); a hand-built `events`/`server_obs` dict with one live/unaccounted worker must force `phase_resolution_verdict` to FAIL, never PASS, even if every other field looks clean |
| **Stage 4** — duration calibration | Fixed 240-episode plan (5 reps x 6 tasks x 2 workflows x 2 models x 2 concurrency); `c_max` -> `request_timeout_s`/`episode_hard_cap_s` (`protocol_FINAL.md:1362-1367`) | `request_timeout_s`/`episode_hard_cap_s` pure functions, `Job`/`run_job`/`main` (`lab_worker.py:95-115,73-90,473,641-686`); `config.json:219-220` calibration_plan (240 episodes) | 240-row schedule generator; pair-synchronous launcher; `c_max` reducer with OD1-style censoring; no orchestrated entry point anywhere (`map_stages456.md:78-101`, "Missing (still, confirmed at c62b59b)") | Yes — mock latencies + a timeout fault exercise the censored path; assert 240/240 schedule-row-to-episode mapping against `lab_mock_server`, no real server | Positive: schedule generator emits exactly 240 rows covering all 5x6x2x2x2 cells with no duplicates. **Negative (must refuse):** a mock episode that never returns (simulated hang) must be censored into the timeout branch, not silently dropped from the 240-row count |
| **Stage 5** — side-by-side calibration | Per 4 contrasts: solo vs side-by-side latency; `C` = median-ratio/median-ratio over 6x5; 30 pairs/contrast, orientation balanced 15/15, fixed in advance; starts only after uncensored `c_max` (OD1) (`protocol_FINAL.md:1368-1376`; `reviews/live_prefreeze_root_decisions_20260921_1929.md:15,17`) | `config.json:221` `side_by_side_compression_C` still null for T1-T4 (unchanged) | 15/15 orientation schedule generator (seeded, deterministic); pair runner skeleton; `C`-from-medians computation (`map_stages456.md:132-146`, "Missing (still, confirmed at c62b59b)") | Yes — fixed-latency mock gives a hand-computable `C`; verify generator balance/determinism from its seed alone, no server | Positive: generator reproduces the identical 30-pair schedule from the same seed on repeated runs. **Negative (must refuse):** must refuse to start before an uncensored `c_max` (OD1) is on record — a censored/null `c_max` input must raise, not silently substitute a default |
| **Stage 6** — dress rehearsal + injected-decision fixture | Full production path under rehearsal-only config, <=16 pairs/32 episodes, 4 named faults each at least once, deterministic injected-decision fixture, freeze needs verifier PASS + clean builder + 100% receipt match (`protocol_FINAL.md:1378-1388`, re-verified this pass line-by-line, titled "**Real-server dress rehearsal**"; `reviews/live_prefreeze_root_decisions_20260921_1929.md:23`) | `World.build_job`/`World.spawn` on the trial loop (`lab_orchestrator.py:3649,3743,2620`); `lab_injected_decision.inject_decision` (refuses without `rehearsal_only`, `lab_injected_decision.py:98,101,108`); `--max-pairs` explicitly mock-only (`lab_orchestrator.py:5854,5876-5879`); `dryrun_live_ab.py` mock freeze-tree builder | Rehearsal schedule/fault-plan generator; fault-injector interface; coverage/receipt report; resolution of `_prefreeze`-subtree-vs-chain placement ambiguity (unresolved in all ~19 amendment blocks scanned, `map_stages456.md:225-232`) | **Partially — corrected this pass (CRITIQUE finding 2).** What is model-free: the fault-injector *interface*, the coverage-report tooling, and dry wiring of all 4 injected-fault types against the existing mock dry-run (`dryrun_live_ab.py`), asserting the coverage report flags every required cell. What is **not** model-free, and stays in §6's blocked table as its own row: the dress rehearsal itself — "real anchors on a drill branch," the frozen receipt comparison on 100% of real responses, and the full production path under a real server, none of which any mock can satisfy (`protocol_FINAL.md:1378-1388`) | Positive: coverage report shows all 4 faults hit at least once and both models/workflows/orientations covered in a <=16-pair mock schedule. **Negative (must refuse):** a coverage report with any required cell (model x workflow x orientation x fault) unhit must block "rehearsal complete," never round up to complete on partial coverage |
| **§11.5** — extended CPU replay/seed | Reuse §3.4 arrival-order algorithm exactly, fresh seed per replicate, 432 cells x 4,000 (20,000 for T4) = 3,456,000 replicates, exhaustive Wilson-interval output, script+seed+output-hash into freeze bundle, cannot change any rule parameter (`protocol_FINAL.md:2440-2477,2944,2995,2997,3367`) | **Nothing at c62b59b** — no `lab_replay.py`, no replay code anywhere reachable from this HEAD (`map_replay.md` §3, re-read in full this pass). A candidate exists only on the never-merged branch `session60/repair-replay` (commits `11fd781`,`90edaa8`; tip `72230b8`), diverged at `b049307`: `lab_replay.py` (983 lines) with a concrete seed rule `SeedSequence([design_seed_base, 1105, c, r])`, grid-size self-check, and two protocol gaps left as explicit `PROPOSED`/`NOT_SIMULABLE`, never defaulted | A hand-port of that branch's `lab_replay.py` logic onto `c62b59b` (see §7 for why hand-port, not merge or rebase); the real 3,456,000-replicate grid has **never been run** even on the branch (`map_replay.md:153-156`, "the real grid was NOT run") | Yes — entirely CPU-only, no model, no server; the branch's own design already refuses to run without `open_model` and flags `NOT_SIMULABLE` horizons rather than guessing | Positive: `check_grid` recomputes exactly 432 cells / 3,456,000 replicates from the literal protocol item-5 spec. **Negative (must refuse):** running any cell without an explicit `open_model` argument for the T3/T4 outcome-model gap must raise (`check_open_model`, `ref:session60-repair-replay:lab_replay.py:418-439`), never silently pick a default `w`/`q`/`s` |

---

## 3. Proposed commit order on `session60/drivers-eb2-eb4` (from `c62b59b`) — rechecked this pass

**Rechecked and unchanged from v1.** Neither CRITIQUE finding requires resequencing: finding 1 changes
*why* §11.5/schedules are hand-ported (§7), not *when*; finding 2 only reclassifies what stage 6's
commit (item 8) may claim as done; finding 4's cross-walk adds rows to §6, not new commits. Each commit
is its own commit/review unit per the 21:14 "deliver reviewable increments" rule, with its own shard
receipt (§5) and, new this pass, an explicit **harness-byte-impact** note (full table in §9) — every
commit below adds at least one new `experiments/live_ab/*.py` file, which by itself moves the harness
pin (`lab_common.py:652-656`, `_harness_files()` = `HERE.glob('*.py')` plus `config.json`) and needs a
successor receipt in the style of `results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_2009.json`; some
commits also touch an *existing* pinned file, which is flagged individually.

1. **Shared write-once shard-receipt primitives** (new `lab_shard_receipt.py`, thin wrapper over the
   existing `write_json_atomic`/`append_line_durable`/`WriteOnceViolation` in `lab_common.py:509-550,920`
   and the `AttemptLedger` pattern in `lab_data.py:748`). No protocol dependency; every later driver
   needs this to emit a legal receipt, so it goes first. **Harness bytes:** new file only.
2. **§11.5 extended CPU replay/seed, hand-ported** (port `lab_replay.py`'s logic from
   `ref:session60-repair-replay` onto `c62b59b`, using (1) for its receipt; keep the two PROPOSED/
   NOT_SIMULABLE gaps exactly as flagged, do not resolve them — see §7 for why this is a hand-port of
   logic in a fresh commit, never a `git merge` or `git rebase` of the branch itself). Chosen second
   because it is CPU-only, self-contained, needs no `_prefreeze` chain integration, and directly answers
   the explicit "§11.5" clause of item 2. **Harness bytes:** new file (`lab_replay.py`); the branch's own
   commit `11fd781` also touched `tests_lab_isolation.py` (an *existing* pinned file, since it lives at
   `experiments/live_ab/tests_lab_isolation.py`) to add a MATRIX import-isolation entry — expect the same
   edit here, so this commit's receipt must carry `tests_lab_isolation.py`'s old/new hash too, not just
   the new file's.
3. **`_prefreeze` chain runner scaffold** (a shared driver-facing module that opens/writes/closes the
   `_prefreeze` chain using only the phase values that already exist in `E_PHASE`
   (`lab_eventlog.py:166-167`); it must refuse, with a clear named error, to write any not-yet-defined
   phase such as `timing_pilot`/`rehearsal` until root names that value — see OD in §6). This unblocks
   stages 1, 2, 4-6 without pre-empting root's schema decision. **Harness bytes:** new file; likely also a
   `tests_lab_isolation.py` MATRIX entry (existing pinned file) once any other driver imports it under the
   isolation harness — confirm before landing.
4. **Stage 1 driver** (golden-request bootstrap, golden-file writer, format-conformance counter), built
   and tested against `lab_mock_server` and using (1) and (3). **Design choice, new this pass:** build the
   bootstrap request as its own new module issuing the reference HTTP call directly, rather than editing
   `LlamaClient.__init__`'s mandatory-`golden` contract in the already-accepted `lab_client.py`
   (`lab_client.py:399-410`) — this is a design *recommendation*, not a certainty; if a reviewer judges the
   bootstrap genuinely belongs inside `lab_client.py`, that is an edit to an existing pinned, EB1-adjacent
   file and should get its own explicit root sign-off separate from "just a new file landed." **Harness
   bytes:** new file(s), plus a `tests_lab_isolation.py` MATRIX entry (existing pinned file).
5. **Stage 2 driver** (counter-semantics probe + §13.1 wording derivation), built on (1),(3),(4)'s
   server-start pattern; OD11 timeout kept as an explicit parameter, never adopted as a constant.
   **Harness bytes:** new file(s), plus a `tests_lab_isolation.py` MATRIX entry.
6. **Stage 4/5 schedule generator, hand-ported** (port `lab_schedules.py`'s logic from
   `ref:session60-repair-replay` onto `c62b59b`; pure, deterministic, seeded schedule emission only —
   no execution). Placed after stage 1/2 because it shares the write-once schedule pattern those
   drivers establish, but it does not depend on them directly. **Harness bytes:** new file
   (`lab_schedules.py`); the branch's own commit `d2fe284` also touched `tests_lab_isolation.py` for the
   same MATRIX reason as item 2 — expect the same here, old/new hash both in the receipt.
7. **Stage 4 and Stage 5 execution scaffolds** (consume (6)'s schedule; `c_max` reducer with explicit
   OD1 gate; both built/tested only against `lab_mock_server`, refusing any real dispatch until root
   authorizes execution). **Harness bytes:** new file(s), plus a `tests_lab_isolation.py` MATRIX entry. No
   edit to `lab_worker.py` expected — `request_timeout_s`/`episode_hard_cap_s` are consumed read-only.
8. **Stage 6 rehearsal/fault-plan generator and fault-injector scaffold** (model-free half only, per
   §2's corrected split), using (1) and (3); last of the stage drivers because it is the most complex,
   most root-decision-dependent (`_prefreeze` placement ambiguity, OD4/OD10/OD16), and exercises the
   widest surface of the others. **Harness bytes and an open design question (new this pass):** "extend
   the existing mock dry-run with all 4 injected-fault types" can mean either (a) a new module that wraps
   `dryrun_live_ab.py`'s mock builder from outside, touching no existing file, or (b) editing
   `dryrun_live_ab.py` itself (an existing pinned file) to add the fault types in place. Default if root
   is silent: (a), new-file-only, for the same pin-hygiene reason as item 4's stage-1 design choice — see
   §8. Either way, a `tests_lab_isolation.py` MATRIX entry is expected.
9. **EB5 loaded-phase preparation extensions not already covered above** — fixture-driven
   `lab_lifecycle` sequence-number/seal validation tests, and a *proposal* (not an implementation) for
   a `lab_mock_server` `/slots` stub, submitted as its own reviewable amendment rather than silently
   added to the mock. Last, because both explicitly require their own root-reviewed pin/amendment
   before being relied on for acceptance evidence (`map_stage3_eb5.md:59-66`, "§7. Needs the real server
   / real capacity"). **Harness bytes:** the *tests* belong in `experiments/live_ab_controls/` (outside
   the pin, per the 21:14 rule "controls outside its glob"); implementing the sequence/seal check itself
   (pure logic, model-free per `map_stage3_eb5.md:64`) inside `lab_lifecycle.py` would be an edit to an
   *existing* pinned production file, and should ship as its own separately reviewed sub-commit distinct
   from the test-only fixtures, so root can evaluate the production-code change on its own.

Nothing in this order runs a loaded stage, repeats the accepted CPU grid, or starts a real model/server.

---

## 4. Exact pins each driver records

Every driver's receipt (§5) carries all four of the following, not a subset:

- **Code pin**: the driver's own file path + git blob SHA-256 (or commit hash once landed), plus the
  harness-pin recomputation trigger — any new `experiments/live_ab/*.py` file, or any edit to an
  existing one, moves the pin at next preflight via `HERE.glob('*.py')` (`lab_common.py:652-656`,
  verified this pass at those exact lines). §9 below itemizes which of §3's nine commits touch an
  *existing* pinned file versus adding only new ones.
- **Config pin**: the exact `config.json` byte range/canonical digest the driver reads —
  e.g. stage 1 reads `config.receipt.golden_props_sha256`/`golden_generation_settings_sha256`
  (`config.json:131-132`, both `null` pre-capture); stage 2 reads `metrics_timeout_s`/`metrics_tries`
  (`config.json:163`); stage 3/EB5 reads `server_supervision`
  (`config.json:225`, `{"max_supervised_restarts_per_server_per_trial": 3, "on_exceeding":
  "abort_trial_incomplete"}`); stage 4/5 reads `prefreeze.calibration_plan`/`side_by_side_compression_C`
  (`config.json:219-221`); §11.5 reads `design_seed_base` (`config.json:93`, value `60260919`). Any
  driver that needs a **new** config key not listed here (e.g. a placeholder stage-2 timeout, a
  rehearsal-config subtree) is itself a harness-byte change to `config.json` and needs the same kind of
  synchronized pre-outcome amendment already used for the four `oodp` prompts, not a silent addition.
- **Seed pin**: `design_seed_base = 60260919` is the one frozen constant every seeded driver must read
  from config, never hardcode. Downstream formulas differ per driver and must each be recorded
  verbatim in the receipt: the live-trial arrival order uses
  `SeedSequence([design_seed_base, trial_no])` (`lab_design.py:70`); §11.5's replicate seed uses
  `SeedSequence([design_seed_base, 1105, c, r])` with stream tag `1105` chosen precisely so it cannot
  collide with the live-trial seed (`ref:session60-repair-replay:lab_replay.py:55-63,184-187,325-332`);
  the worker/model-call `seed_rule` (`config.json:100`, implemented `lab_coin.py:132-145`) is a
  *different* mechanism entirely and must not be confused with either of the above in any receipt.
- **Data digest pin**: once produced, the sha256 of each output artifact enters the receipt and, at
  freeze, the freeze bundle — `golden_props_<server>.json`/`golden_generation_settings_<server>.json`
  (stage 1); the schedule file (stage 4/5); the rehearsal fault-plan file (stage 6); the §11.5 output
  table (`protocol_FINAL.md:2467-2469,2995,2997`: "script, seed and output SHA-256 enter the freeze
  bundle... every cell... deposited; no row is omitted for brevity").

---

## 5. Shape of the incremental immutable completed-shard receipt

Unchanged from v1 (CRITIQUE raised no finding against this section).

**What is a shard.** The smallest unit of one driver's work that can be independently verified without
rerunning the whole driver: one stage-1 golden capture (one server), one stage-2 probe pair, one
stage-4 calibration episode, one stage-5 pair, one stage-6 rehearsal episode, one §11.5 grid cell (or,
for very cheap cells, a batch of cells sharing one write). Each shard has a stable **shard id**
determined by the pre-committed schedule row it fulfills (episode/pair/cell index), never by wall-clock
order.

**Write-once.** Each shard's receipt is written exactly once via the existing
`write_json_atomic(path, obj, durable=True)` (`lab_common.py:509-548`), which already raises
`WriteOnceViolation` (`lab_common.py:920`) if the path exists with different bytes — reused verbatim,
not reimplemented. A receipt file, once written, is never edited or deleted by any driver; a
correction requires a new, separately reviewed amendment commit, exactly as protocol/config amendments
already work in this repo.

**Receipt contents (per shard).** Shard id; the four pins from §4 (code/config/seed/data-digest,
scoped to what that shard actually touched); the exact schedule row it fulfills; inputs consumed; the
sha256 of every output byte it produced; wall-clock start/end (actual timestamps, per the 20:40
review's "writes ... actual timestamps," `reviews/prerun_bundle_go_nogo_20260923_2040.md:17`); and an
explicit outcome — `success` / `failure` / `unresolved` — never omitted, mirroring
`phase_resolution_verdict`'s rule that an unfinished call is listed with `usage:null`, never dropped
(`lab_orchestrator.py:706-820`). **New this pass:** the receipt also carries a `harness_pin_delta`
field naming every existing pinned file the shard's *driver* (not the shard itself) touched relative to
the previous accepted pin, per §9 — this makes the harness-byte impact of each increment checkable from
the receipt alone, without root having to re-derive it from a diff.

**Resuming a partial run without rewriting a receipt.** On restart, the driver first lists every shard
id already present on disk (its receipt directory) and treats each as immutable and done — this is
exactly the `AttemptLedger` pattern already in `lab_data.py:748` and the same discipline
`StreamingHttpLoad`'s durable ledger already applies (`lab_load.py:624-993`). It then attempts only
the schedule rows whose shard id has no receipt yet, appending new receipts one at a time. A crash
mid-shard leaves that one shard's receipt absent (never partially written, since `write_json_atomic`
writes to a temp path and renames), so resumption is simply "re-attempt every schedule row with no
receipt," with no risk of double-counting or silently skipping.

**Verification.** A separate, read-only verifier (i) recomputes each receipt's declared output hash
from the actual output file on disk and flags any mismatch; (ii) recomputes the bijection between
schedule rows and shard receipts — every row has exactly one receipt, every receipt maps to exactly
one row, per `map_stages456.md`'s proposed "schedule-row-to-terminal-row bijection test"; (iii) reruns
the flipped-schedule-byte and mock-kill-mid-row refusal tests already scoped as model-free controls in
§2, confirming the driver would have refused rather than silently produced a wrong receipt.

---

## 6. What stays blocked on a model, server, capacity evidence, or a named root decision

### 6a. Original blocked items (pseudo-anchors replaced with verified path:line citations — CRITIQUE finding 3)

| # | Item | Blocked on | Cited as open at |
|---|---|---|---|
| OD11 | Stage-2 client timeout value | Root ruling; plan sheet's 10s is a default, "adopted only on explicit root acceptance" | `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:1899-1904,4402-4409`; re-checked absent from every 2026-09-24/25 review on origin/main |
| — | New `E_PHASE` value(s) for stage-2/4/5/6 events (`timing_pilot`/`rehearsal`) | Schema decision on a closed/frozen event schema | `lab_eventlog.py:166-167` (no such value exists) |
| OD1 | Stage 5 may not start before an uncensored `c_max` | Requires stage 4 to actually run | `reviews/live_prefreeze_root_decisions_20260921_1929.md:17` |
| OD2, OD14 | Stage 4/5 plan parameters | Not resolved in any reviewed doc since `b049307` | `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:2276,2404,2427` |
| OD4, OD10 | Stage 6 rehearsal config / drill-branch anchor postings | Root ruling | same plan sheet, stage-6 rows |
| OD16 | Stage 6 orientation-coin ~13.2% coverage gap | Root ruling | same plan sheet |
| — | Stage 6's `_prefreeze` chain writes under a subtree vs the chain itself | Protocol wording ambiguous; scanned ~19 amendment blocks, none resolves it | `protocol_FINAL.md` amendment scan, `map_stages456.md:225-232` |
| — | §11.5 outcome model for T3's pilot-less candidate and the T3/T4 cost pair | Named explicitly by root as unresolved | `reviews/restart_cap_estimand_ruling_20260923_2114.md:19` ("...the §11.5 outcome model...") |
| — | Whether `lab_mock_server` may grow a `/slots` endpoint | Itself a design decision root has not authorized; needed only to test `phase_resolution_verdict`'s server-busy branch through the real HTTP path rather than a synthetic dict | **Verified anchor (was `§needs_model_or_server_or_root_decision`):** `map_stage3_eb5.md:47,63` |
| — | Building the patched llama.cpp binary and running it against the real GGUF to produce genuine `slot_lifecycle-v1` records | Real compiled server + real model weights; nothing fixture-based can certify the patch itself | **Verified anchor:** `map_stage3_eb5.md:61`; patch pin `4fea119de30f6a923992780f6fd5ccb0bee5d47d` |
| — | Verifying two decoding slots genuinely occupied concurrently | Real serving-host-backed concurrent decoding; a mock's `active_slots` counter is scripted, not observed contention | **Verified anchor:** `map_stage3_eb5.md:62` |
| — | Any actual stage-3 §5.8-item-3 240-episode calibration run | Named server/capacity evidence and freeze inputs required first; no loaded episode approved | `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:19` ("**No loaded/design/trial episode is approved**") |
| OD18/OD19 | Actual reserved host window / capacity gate | Root/owner coordination, not code; plan estimates ~7.42 days combined prefreeze+trial | `reviews/prerun_bundle_go_nogo_20260923_2040.md:19` |
| — | Whether new stage drivers live inside `experiments/live_ab/` (auto-pinned by `HERE.glob`) or a separate directory | Open tradeoff, not re-litigated since `b049307` | `map_stages456.md`, `map_held_branch.md` |

### 6b. New row (CRITIQUE finding 2) — the real-server rehearsal itself, distinct from its scaffold

| # | Item | Blocked on | Cited as open at |
|---|---|---|---|
| — | **Stage 6's real-server dress rehearsal itself** (as opposed to the fault-injector/coverage-report scaffold in §2/§3 item 8, which *is* model-free) — "real anchors on a drill branch," the full production path (orchestrator, scheduler, both models, execution lock, live monitor), and the frozen receipt comparison passing on 100% of real rehearsal responses | Real, patched, running server; a real drill branch; none of it satisfiable by `lab_mock_server` or `dryrun_live_ab.py`'s mock freeze-tree builder | `protocol_FINAL.md:1378-1388` (re-verified this pass, full item-6 text, titled "Real-server dress rehearsal"); `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:19` ("No loaded/design/trial episode is approved") |

### 6c. Cross-walk of root 22:20 item (3)'s seven named prerequisites (CRITIQUE finding 4)

Root's 22:20 review names these seven as "still need[ing] explicit root review" (§1 above,
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:19`). Unlike the OD rows above, these are
**not** drivers this proposal is scoped to build — each already has a specified form in the frozen
protocol/config that predates this proposal (confirmed by the 20:40 review's own line 11: "The current
committed design metadata still states paired AB/BA, delta 0.03, program/trial/band alpha
0.05/0.0125/0.00625, enrollment-indexed partial bounds, both guardrails and the fixed
first-crossing/horizon rule," `reviews/prerun_bundle_go_nogo_20260923_2040.md:11`). What is missing is
root's own explicit sign-off pass, which is not something session60's code can produce. Owner for every
row below is **root** (review/ruling), not session60 (build); session60's obligation is only to not
silently touch any of these while building §3's drivers.

| Prerequisite (root 22:20 item 3) | Owner | Status at c62b59b |
|---|---|---|
| Paired AB/BA assignment | Root (sign-off) | Already specified: "One fresh fair coin per pre-enrolled pair from OS entropy fixes the orientation (AB or BA)" (`protocol_FINAL.md:75`); durable coin logging at `protocol_FINAL.md:146`. Not touched by any commit in §3. |
| Enrollment-indexed partial bounds | Root (sign-off) | Already specified: §7 "Pairing, the filtration, enrollment-indexed records, and enclosures" (`protocol_FINAL.md:1625` heading); reorder-invariance/repeated-update invariants at `protocol_FINAL.md:2644`. Not touched by any commit in §3. |
| Simultaneous error allocation | Root (sign-off) | Already specified: program alpha `0.05` -> four trials `0.0125` each -> `alpha_gate=0.00625` per band, "same two-sided band serves the deploy tail and the harm tail; no extra split" (`protocol_FINAL.md:85`). Not touched by any commit in §3. |
| Scientific guardrails | Root (sign-off) | Already specified: success guardrail `L_s > -0.03` and the hierarchy condition `L_h > 0` (`protocol_FINAL.md:236,270,317`); named "both guardrails" in the 20:40 review (`reviews/prerun_bundle_go_nogo_20260923_2040.md:11`). Not touched by any commit in §3. |
| Stopping/estimand rules | Root (sign-off) | Already specified: fixed first-crossing/horizon rule, no retention, no intersection (`protocol_FINAL.md:1006`); per-contrast estimand text (`protocol_FINAL.md:1372,1444,1467`). Not touched by any commit in §3. |
| Serving/usage provenance | Root (sign-off); partially built by session60 | Partially exists in code today — `lab_serving_manifest.py` (write-once serving manifest, `ARCHITECTURE_FINAL.md:163`), `parse_usage()`'s null-not-zero discipline (`lab_load.py:163-183`). §3's stage 1/2/4-6 drivers will *produce more* of this provenance (golden files, schedule files, shard receipts) but assembling/accepting it as sufficient for freeze is explicitly out of this proposal's scope and stays with root. |
| Freeze inputs | Root (sign-off); partially built by session60 | The freeze-bundle contract is specified (`protocol_FINAL.md:93` "the freeze bundle of section 14.2, root guidance item 9 item-for-item"; provenance item 7 at `protocol_FINAL.md:2467-2469`). §3's drivers are exactly what will populate several freeze-bundle fields (golden hashes, schedule hashes, §11.5's script/seed/output hash), but freeze acceptance itself needs explicit root review per the 22:20 wording and is not something any commit in §3 does on its own. |

Root can rule on any subset of the rows in 6a-6c independently; none blocks the model-free work in §3
items 1-9, which is scoped to avoid every row above.

---

## 7. Reuse or discard of `72230b8` (`session60/repair-replay`) — REWRITTEN this pass (CRITIQUE finding 1)

v1's justification for discarding the branch as a merge candidate was independently re-verified this
pass and found to overstate the danger, exactly as CRITIQUE finding 1 says. This section replaces it
with the actual evidence and a recommendation that follows from that evidence rather than from the old,
incorrect claim.

**What the raw stat hides, and what it doesn't (re-derived this pass).**
`git -C wt-eb1 diff --stat c62b59b 72230b8` reports **144 files changed, 8350 insertions(+), 113504
deletions(-)**. Every file in that stat is a large SM8-diagnosis/receipt/results dump
(`results/live_ab/SM8_DIAGNOSIS_20260925_1503.json`, `REPAIR_AMENDMENT_V3/V4_RECEIPT_*.json`,
`sm8_diagnosis/` tarballs, etc.) that exists at `c62b59b` and simply is **absent** on the 38-commits-
behind branch tip — i.e. the raw stat is dominated by content the accepted line *added after the fork*,
not by anything the branch touched, confirming `map_held_branch.md`'s claim.

**The branch's own six commits, and exactly what they touch (re-derived this pass with
`git log --oneline c62b59b..72230b8` and `git log --name-only --pretty=format:'--- %H %s'
c62b59b..72230b8`):**

```
72230b8 EB5: a loaded sweep is accepted only on tracked, observed load; a control per resolution guard
3d37c7e lab_schedules: consumption order bound to seq, a control per guard, resolvable RULED sources
90edaa8 lab_replay: control the 11.5 outcome model, check the grid against the protocol, T4-only null rows
c26a592 EB5 for loaded background streams: durable load ledger, stop never forgets, sweep acceptance gated
d2fe284 lab_schedules: deterministic write-once schedules for pre-freeze stages 4 and 5
11fd781 lab_replay: protocol 11.5 extended CPU replay and its seed
```

Across all six, the only files touched are: `experiments/live_ab/lab_load.py`,
`experiments/live_ab/lab_prepare.py`, `experiments/live_ab/lab_schedules.py` (new),
`experiments/live_ab/lab_replay.py` (new), `experiments/live_ab/tests_lab_design.py`,
`experiments/live_ab/tests_lab_isolation.py`, and four `experiments/live_ab_controls/` control files
(`tests_delta_citations.py`, `tests_lab_load_resolution.py`, `tests_lab_schedules.py`,
`tests_lab_replay.py`). **`lab_orchestrator.py`, `lab_server.py`, `lab_eventlog.py`, `lab_anchor.py`,
`lab_verify_log.py`, `config.json`, `protocol_FINAL.md` and `ARCHITECTURE_FINAL.md` are not in this
list** — the branch's own commits never edit them, confirming `map_held_branch.md:20-30` and directly
contradicting v1's claim that these files were among what the branch "differs" on.

**What each touched production file's diff actually contains (re-derived this pass):**

- `experiments/live_ab/lab_load.py`: `git diff c62b59b 72230b8 -- experiments/live_ab/lab_load.py` is
  **empty** — byte-identical. This EB5 durable-ledger work already reached the accepted line
  independently (matching `map_held_branch.md`'s §1a finding); nothing to reuse or conflict here.
- `experiments/live_ab/lab_prepare.py`: a **5-line, cosmetic docstring diff.** The branch's version says
  "the contract's `phase_resolution_verdict` does not exist on this branch and is not called here"; the
  `c62b59b` version instead says it "(`lab_orchestrator`, the verdict over a trial chain before its
  terminal record) is not called here" — i.e. `c62b59b` updated the same sentence once
  `phase_resolution_verdict` landed on main, and the branch's stale wording is simply out of date. Purely
  textual; no logic differs.
- `experiments/live_ab/tests_lab_design.py`: a 12-line diff (1 insertion, 11 deletions) — small.
- `experiments/live_ab/tests_lab_isolation.py`: a larger diff against `c62b59b` because both lines of
  development extended the same MATRIX table independently (main for its own new files, the branch for
  `lab_replay`/`lab_schedules`); not inspected line-by-line this pass, but not part of either
  `merge-tree` conflict below.

**Read-only `git merge-tree c62b59b 72230b8` (re-run this pass; writes nothing, touches no ref or
working tree; `git status --porcelain` on `wt-eb1` empty before and after):**

```
merge-base: b049307
CONFLICT (content): Merge conflict in experiments/live_ab/lab_prepare.py
CONFLICT (add/add): Merge conflict in experiments/live_ab_controls/tests_delta_citations.py
```

**Exactly two conflicts, confirming CRITIQUE finding 1's own re-run.** Neither touches
`lab_orchestrator.py`, `lab_server.py`, or any other EB1-fixed file — because, as shown above, the
branch's own commits never edited them, so a genuine 3-way merge keeps `c62b59b`'s post-EB1 versions
automatically, with no conflict there. **This directly falsifies v1's central claim that "merging the
branch wholesale would reintroduce the class of defect the 20:40 review named as EB1."** That claim is
withdrawn.

- The `lab_prepare.py` conflict is exactly the 5-line docstring difference described above — a trivial,
  mechanical resolution (keep `c62b59b`'s phrasing, since `phase_resolution_verdict` does now exist).
- The `tests_delta_citations.py` add/add conflict is a **genuine, non-mechanical divergence**, not noise:
  both lines of development rewrote this control file independently for different purposes. Main's
  current version scans every line the *whole* EB1+EB5 subset added since a reviewed base revision
  (tracked via `git diff BASE..PRE_FIX` bookkeeping removed from the branch's own version) for untracked
  session-note citations across the orchestrator/eventlog/EB5 surface. The branch's version instead adds
  `lab_replay.py`/`lab_schedules.py` to its `PRODUCTION` tuple and a `PLAN` quotation check for the
  §11.5 plan-sheet text and the protocol 11.5 line range. **Which citation-scanning strategy should
  govern once `lab_replay.py`/`lab_schedules.py` land is itself a small design decision**, not something
  a merge tool can pick correctly — see the open question in §8.

**Corrected recommendation (follows from the evidence above, not from the withdrawn EB1-reintroduction
claim):**

**Still hand-port the logic of `lab_replay.py` and `lab_schedules.py` into fresh commits on `c62b59b`
(§3 items 2 and 6) rather than `git merge` the branch — but for different, verified reasons:**

1. **Reviewability granularity (root's own stated preference).** Root's 21:14 ruling item 2 explicitly
   asks for small, separately reviewable increments with old/new hashes, not one large delivery
   (`reviews/restart_cap_estimand_ruling_20260923_2114.md:18`). A single `git merge` of `72230b8` would
   bundle `lab_replay.py`, `lab_schedules.py`, the no-op `lab_load.py`/`lab_prepare.py` content, and the
   resolution of two conflicts into one commit that mixes an unrelated module (EB5 ledger, already on
   main) with the two genuinely new ones — the opposite of what root asked for. Two hand-ported commits
   (§3 items 2 and 6) let root review each module and its receipt independently, exactly matching §3's
   existing order.
2. **The `tests_delta_citations.py` divergence needs a deliberate decision, not a merge tool's pick.**
   As shown above, this is a real content conflict about which citation-scanning strategy survives, not
   a mechanical one. Folding its resolution silently into a merge commit would make that decision look
   like a side effect of a `git merge` rather than what it is: a small, separately-statable design choice
   (§8 gives a default).
3. **`tests_lab_load_resolution.py` has never been diffed against the already-merged EB5 controls on
   main** (flagged unresolved by `map_held_branch.md:103-112,171-174`). Reusing it via a hand-port forces
   that diff to happen as part of preparing the port; a `git merge` would not force it and risks landing
   a duplicate or conflicting test silently.
4. **The two protocol gaps (`PROPOSED`/`NOT_SIMULABLE`) must be carried over exactly as flagged**, and a
   fresh, reviewed commit makes that an explicit, checkable claim in the new commit's own message and
   receipt, rather than something to verify by re-reading an old commit's diff after a merge.
5. **`session60/repair-amend` (`ff152e9`) remains separately confirmed not reusable at all**, unrelated
   to this correction: its orchestrator still sets `props_matches_golden = True` unconditionally
   (`lab_orchestrator.py:1628` at `ff152e9`), and its restart-cap text is self-labelled "Provisional,
   pending root's ruling ... not final" (`protocol_FINAL.md:942-948` at `ff152e9`), predating the 21:14
   ruling the accepted line already implements differently (`map_held_branch.md §2`).

**If root instead prefers to bring `72230b8` in as a real merge** (e.g. to preserve the branch's own
commit history/hashes for `lab_replay.py`/`lab_schedules.py` rather than re-authoring them), that must be
a **`git merge`** (recording both parents, keeping the six commits' own hashes intact) — **never a `git
rebase`** of the branch onto `c62b59b`, since a rebase would rewrite those hashes and break the "old/new
hashes" provenance chain root's own 21:14 ruling asks every delivery to carry
(`reviews/restart_cap_estimand_ruling_20260923_2114.md:18`). Either way, the two conflicts above must be
resolved by a human/reviewed decision, not defaulted.

---

## 8. Risks and open questions — phrased so silence is safe, with a default

- **Q: What `E_PHASE` value do stage-2/4/5/6 events use?** *Default if root is silent:* the shared
  `_prefreeze` runner (§3 item 3) ships now using only existing `E_PHASE` values, and refuses with a
  named error to write any stage-2/4/5/6 event until root names the new value(s) — it never guesses an
  enum string. No stage's real execution is blocked by this; only its ability to log is, which is the
  safe direction to fail in.
- **Q: Stage 6's `_prefreeze` chain — subtree or the chain itself?** *Default:* write under a
  segregated subtree (e.g. `_prefreeze/rehearsal/`) with every event still tagged with a `_prefreeze`
  phase, since that is the more conservative, easily-relocated choice and can never be mistaken for
  trial inference. Never default to writing into the trial chain itself.
- **Q: OD11's stage-2 timeout value?** *Default:* use the plan sheet's own stated 10s **only** inside
  mock-server tests and scaffold code; the real driver refuses to run for a live server without an
  explicit, root-accepted value recorded in config, per the plan sheet's own "PENDING_ROOT... adopted
  only on explicit root acceptance" wording.
- **Q: Should `lab_mock_server` grow a `/slots` endpoint?** *Default:* no — do not extend the mock
  without a separate, pre-outcome, root-reviewed amendment (following the same pattern already used
  for the four out-of-design conformance prompts). Until then, `phase_resolution_verdict`'s
  server-busy/unobserved branch stays tested only at the pure-function level with synthetic
  `server_obs` dicts, which is already fully covered model-free.
- **Q: Is any part of `72230b8` or `ff152e9` merged as-is?** *Default:* no — `ff152e9` is discarded
  entirely (§7); `72230b8`'s own commits are not merged or rebased wholesale (§7's corrected
  recommendation) — only hand-ported, freshly reviewed logic from `lab_replay.py`/`lab_schedules.py`
  enters `session60/drivers-eb2-eb4`, unless root explicitly asks for a real `git merge` instead (§7).
- **Q: Where do new stage-driver files live?** *Default:* inside `experiments/live_ab/`, matching
  where §5.8 items are already described and where the harness-pin glob already looks
  (`lab_common.py:652-656`), so the pin auto-updates at next preflight with no separate wiring. A
  separate directory is used only if root says otherwise.
- **Q: Where do shard receipts live?** *Default:* `results/live_ab/shards/<driver_name>/<shard_id>.json`,
  one write-once file per shard, mirroring the existing `results/live_ab/` receipt convention
  (e.g. `HARNESS_PIN_SUCCESSOR_20260925_2009.json`, `DELIVERY_STEP_RUNS_20260925_2014.json`) rather
  than inventing a new location or format.
- **Q: Does the stage-1 golden bootstrap edit `lab_client.py`, or live in a new file? (new this pass)**
  *Default:* a new file issues the reference HTTP request directly and hands the result to a
  `GoldenReceipt`; `lab_client.py:399-410`'s mandatory-`golden` constructor is left byte-identical. If a
  reviewer later judges the bootstrap belongs inside `lab_client.py`, that edit gets its own explicit
  sign-off separate from "just a new file landed," since `lab_client.py` is already part of the accepted
  EB1+EB5 subset.
- **Q: Does the stage-6 fault-injector edit `dryrun_live_ab.py` in place, or wrap it from a new file?
  (new this pass)** *Default:* wrap it from a new file, same reasoning as the stage-1 question above —
  `dryrun_live_ab.py` stays byte-identical unless root asks otherwise.
- **Q: Which `tests_delta_citations.py` citation-scanning strategy governs once `lab_replay.py`/
  `lab_schedules.py` land? (new this pass, from §7)** *Default:* keep main's current, independently-
  evolved version (the one that scans every line added since a reviewed base revision across the whole
  subset) and extend it with the two new modules' citation patterns as a small follow-up diff, rather
  than reintroducing the branch's alternate `PRODUCTION`/`PLAN`-tuple version wholesale.
- **Risk:** this proposal itself has not been executed, built, or tested — it is a synthesis of six
  read-only maps (with `map_replay.md` re-read in full this pass) plus a re-read of the three authority
  reviews and a fresh re-run of the git commands in §7, not a fresh line-by-line re-audit of every
  citation those maps carried. Where a map flagged its own citation as unverified or carried from the
  stale `b049307` map, that flag is preserved here rather than resolved.
- **Risk:** the reviews directory (200+ files) was not fully swept for a ruling on OD1/OD2/OD14/OD16
  beyond the three named authority docs; absence of a ruling there is not proof none exists elsewhere.
  *Default if this remains unchecked:* treat all four as still open and do not execute stage 4/5/6 for
  real.
- **Risk:** large all-at-once delivery is explicitly disfavored by root ("Deliver reviewable
  increments," "one review of an interim subset is not trial clearance"). *Default:* ship §3's nine
  commits as nine separate reviewable increments, each with its own shard receipt and harness-byte-impact
  note (§9), never as one bundled commit.

---

## 9. Harness-byte impact of §3's nine commits (new this pass, cross-referenced from §3/§4)

| Commit (§3 item) | New harness file(s) | Existing pinned file(s) touched | Needs new harness-pin-successor receipt |
|---|---|---|---|
| 1. Shard-receipt primitives | `lab_shard_receipt.py` | none identified | Yes — new-file pin move only |
| 2. §11.5 replay (hand-port) | `lab_replay.py` | `tests_lab_isolation.py` (MATRIX entry, per branch precedent `11fd781`) | Yes — new file + one existing-file edit |
| 3. `_prefreeze` runner scaffold | new module | possibly `tests_lab_isolation.py` (confirm before landing) | Yes |
| 4. Stage 1 driver | new module(s) | none, **if** built per §8's default (no edit to `lab_client.py`); `tests_lab_isolation.py` MATRIX entry expected | Yes |
| 5. Stage 2 driver | new module(s) | `tests_lab_isolation.py` MATRIX entry expected | Yes |
| 6. Stage 4/5 schedule generator (hand-port) | `lab_schedules.py` | `tests_lab_isolation.py` (MATRIX entry, per branch precedent `d2fe284`) | Yes — new file + one existing-file edit |
| 7. Stage 4/5 execution scaffolds | new module(s) | `tests_lab_isolation.py` MATRIX entry expected; no edit to `lab_worker.py` expected (read-only use) | Yes |
| 8. Stage 6 rehearsal/fault-injector scaffold | new module(s) | `tests_lab_isolation.py` MATRIX entry expected; `dryrun_live_ab.py` only if root rejects §8's wrap-not-edit default | Yes (and possibly two existing-file edits if the default is rejected) |
| 9. EB5 extensions | tests in `experiments/live_ab_controls/` (outside the pin) | `lab_lifecycle.py`, **only** if the sequence/seal validation logic itself is implemented now (separate sub-commit recommended) | Tests: no. Production sub-commit, if done: yes |

Every "Yes" above means: before that commit lands, compute the new `HARNESS_FILES` tuple
(`lab_common.py:652-659`), diff it against the previous accepted pin, and record both in a successor
receipt in the style of `results/live_ab/HARNESS_PIN_SUCCESSOR_20260925_2009.json` — the same pattern
root's 22:20 review already independently re-verified for the EB1+EB5 subset
(`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:8`). No commit in §3 is proposed to edit
`config.json`; any driver that later turns out to need a new config key must get its own synchronized
pre-outcome amendment first (§4), which is itself a harness-byte change and a separate root-reviewable
item, not folded into a driver commit.

---

## Changes from v1

1. **§7 rewritten (finding 1).** v1's claim that merging `72230b8` would "reintroduce the class of
   defect... named as EB1" is withdrawn — independently re-verified this pass with
   `git log c62b59b..72230b8` (6 commits, 10 files touched total, never including `lab_orchestrator.py`/
   `lab_server.py`/`config.json`/`protocol_FINAL.md`) and a fresh read-only `git merge-tree c62b59b
   72230b8` (exactly 2 conflicts: `lab_prepare.py` cosmetic docstring, `tests_delta_citations.py`
   add/add). The recommendation to hand-port `lab_replay.py`/`lab_schedules.py` rather than merge is
   kept, but now grounded in root's own reviewable-increments preference and the two files' real,
   non-mechanical divergences, not a false regression risk. Added: if root prefers a merge anyway, it
   must be a `git merge`, never a `git rebase`.
2. **Stage 6 downgraded from unqualified "Yes" to "Partially" (finding 2).** §2's table and §3 item 8
   now separate the model-free fault-injector/coverage-report scaffold from the real-server dress
   rehearsal itself. A new blocked-table row (§6b) names the real-server gap explicitly, mirroring how
   Stage 3 was already treated, backed by a verified re-read of `protocol_FINAL.md:1378-1388`.
3. **Three pseudo-anchors replaced with verified path:line citations (finding 3).**
   `map_stage3_eb5.md §missing` -> `map_stage3_eb5.md:47` / `lab_lifecycle.py:887-895`;
   `map_stage3_eb5.md §needs_model_or_server_or_root_decision` -> `map_stage3_eb5.md:47,63` /
   `map_stage3_eb5.md:61` / `map_stage3_eb5.md:62` (three separate rows); `map_stage1.md §risks` ->
   `map_stage1.md:249-260`. Several other citations were tightened to their exact verified line ranges
   in passing (e.g. `config.json:209-218` for the four `oodp` prompts, was `209-217`).
4. **Root 22:20 item (3)'s seven prerequisites cross-walked into §6c as individual rows (finding 4)**,
   each with an owner (root, for sign-off; session60 partially for two of the seven) and a status citing
   where the item is already specified in the frozen protocol, rather than living only inside the §1
   block quote.
5. **New §9, harness-byte impact table**, added per this revision's task instructions: every one of
   §3's nine commits is marked for whether it adds only new `experiments/live_ab/*.py` files (routine
   pin move) or also edits an existing pinned file (`tests_lab_isolation.py`'s MATRIX table, and
   possibly `lab_client.py`/`dryrun_live_ab.py`/`lab_lifecycle.py` depending on design choices flagged
   as new open questions in §8). §5's shard-receipt shape gained one new field,
   `harness_pin_delta`, to carry this per-shard.
6. **§3's commit order rechecked, found unchanged.** No finding required resequencing; a note says so
   explicitly and explains why, per this revision's task instructions.
7. **Three new open questions added to §8** (stage-1 bootstrap placement, stage-6 fault-injector
   placement, `tests_delta_citations.py` strategy choice), each phrased so root's silence has a stated,
   safe default, consistent with the rest of §8.
8. Citations throughout §1-§6 were re-verified against the actual files this pass (not merely carried
   over from v1) wherever they touch a finding above; unrelated citations already spot-checked as
   accurate by CRITIQUE_OF_v1.md's own review were left unchanged.

---

## Issue-comment-ready summary for root (<=40 lines)

**Session60 — EB2-EB4 model-free drivers + EB5 prep, design v2 (fixes completeness critique)**
**Order** (9 commits on `session60/drivers-eb2-eb4` from c62b59b, each its own commit + receipt, unchanged after
critique): 1 shard-receipt primitives, 2 §11.5 replay hand-port, 3 `_prefreeze` runner scaffold,
4 stage-1 golden/conformance driver, 5 stage-2 counter-semantics driver, 6 stage-4/5 schedule generator
hand-port, 7 stage-4/5 execution scaffolds, 8 stage-6 fault-injector/coverage scaffold (model-free half
only), 9 EB5 lifecycle-validation extensions + a `/slots` amendment *proposal* (not code).
**Model-free now:** stage 1 (golden capture/writer/conformance counter vs `lab_mock_server`); stage 2
(probe+ledger vs mock `count_cancelled_tokens`); stage 3/EB5 dispatch scaffold plus
`phase_resolution_verdict`/`lab_lifecycle.observe()` unit coverage; stage 4/5 schedule generators and
scaffolds; stage 6's fault-injector *interface* and coverage report only (not the rehearsal itself);
§11.5's full 432-cell CPU grid logic (no model, ever).
**Blocked, and on whom:** stage 6's real-server dress rehearsal itself — root, needs a real server and
drill branch (corrected this pass; was previously conflated with its model-free scaffold). Stage-3
certified concurrent decoding slots — root/owner, needs the patched llama.cpp binary and the real serving
host. OD11 (stage-2 timeout), OD1/OD2/OD14/OD16/OD4/OD10, new `E_PHASE` values, §11.5 outcome model,
host window/capacity — all root rulings, none blocking the model-free work. Root 22:20's seven named
prerequisites (paired AB/BA, enrollment-indexed bounds, error allocation, guardrails, stopping/estimand,
serving/usage provenance, freeze inputs) are already specified in the frozen protocol; owner is root's
sign-off pass, not new code from this proposal.
**Shard receipt:** one per schedule row, write-once via existing `write_json_atomic`/`WriteOnceViolation`;
carries code/config/seed/data-digest pins, the schedule row, output hashes, actual start/end timestamps,
an explicit success/failure/unresolved outcome (never dropped), plus a new `harness_pin_delta` field
naming any existing pinned file the driver touched.
**72230b8 recommendation:** v1's reason for discarding it was wrong. Verified this pass: its 6 commits
never touch `lab_orchestrator.py`/`lab_server.py`/`config.json`; a read-only `git merge-tree` finds only
2 conflicts (cosmetic `lab_prepare.py` docstring; a genuine `tests_delta_citations.py` add/add
divergence) — merging would *not* reintroduce EB1. Outcome unchanged — hand-port `lab_replay.py`/
`lab_schedules.py` logic into commits 2/6 — but now because root wants small reviewable increments and
two control files need a deliberate decision, not a false regression risk. If root wants a real merge
instead, it must be `git merge`, never `git rebase`.
**Open questions (silence is safe, default stated):** new `E_PHASE` values → refuse to log until named.
`_prefreeze` subtree vs chain for stage 6 → segregated subtree. OD11 timeout → 10s in mock/tests only.
Mock `/slots` endpoint → no, needs its own amendment. Stage-1 bootstrap location → new file,
`lab_client.py` untouched. Stage-6 fault injector → wraps `dryrun_live_ab.py`, doesn't edit it.
`tests_delta_citations.py` strategy → keep main's version, extend later.
Full doc: `experiments/live_ab_drivers/design_notes/DESIGN_PROPOSAL.md`.

---

**File:** `experiments/live_ab_drivers/design_notes/DESIGN_PROPOSAL.md`
