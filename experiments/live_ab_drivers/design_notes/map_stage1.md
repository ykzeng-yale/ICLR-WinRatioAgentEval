# Stage-1 driver map (live_ab prospective trial harness)

Read-only mapping. Repo: `ykzeng-yale/ICLR-WinRatioAgentEval`, worktree
`<worktree at c62b59b>`,
HEAD `c62b59b` on `session60/repair-eb1`. Tag `session60-eb1-eb5-subset-v1` = `c7750a3` (accepted base).
Nothing in the worktree was modified; nothing was run. All citations are `path:line at c62b59b` unless
marked `origin/main:` (a ref read with `git show`).

## 0. There are THREE different things called "stage 1" in this repo — disambiguated first

This matters because the task and the reviews use "stage 1" to mean only one of these, and the other
two are easy to mis-cite.

1. **Protocol §5.8 pre-freeze phase, item 1** — "serving receipt/golden/template/conformance". This is
   the "stage 1" the NO-GO and bounded reviews mean by "stages 1, 2, 4–6" (EB2–EB4 missing drivers).
   This is the AREA of this map.
2. **The plan sheet's `stage: 1` row** (`results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json`,
   `finite_feasibility_sheet.stage_rows[2]`) — `"section_5_8": "item 1"`, `"name": "serving
   receipt/golden/template/conformance"`. This is the SAME thing as (1); the plan sheet is the
   authoritative stage-numbering table (protocol item numbers ≠ plan-sheet stage numbers in general —
   see §1 below).
3. **The offline roster-build step**, informally called "Stage 1" only in
   `results/SESSION60_RESULTS_INDEX.md:813` and in the file name
   `results/live_ab/ROSTER_STAGE1_20260921_1830.json` (cited by
   `experiments/live_ab/design/DERIVATION.md:15`). This is protocol §3.1–3.3 (roster/exclusions/horizon
   arithmetic), is **already executed offline, no model call**, and is **not** on the plan sheet's
   `stage_rows` list at all (that list starts at protocol §5.8 item 1). `Stage1RegressionFixtureTests`
   in `experiments/live_ab/tests_lab_design.py:1971-2010` binds to THIS "stage 1", not to (1)/(2).
   Its own docstring (`tests_lab_design.py:1972-1981`) quotes root: "Keep the actual stage1 receipt as a
   regression fixture bound to its source digests." It skips (does not fail) when
   `lab_common.WORK_ROOT / 'sources' / 'sources.json'` is absent or the pinned source hashes differ
   (`tests_lab_design.py:1987-2000`), and otherwise asserts the exact counts 1,138 candidates / 8
   exclusions / 1,130 survivors / n_S1=591 / n_S2=539 / n_pairs_ceiling=564
   (`tests_lab_design.py:1983-1984, 2009-2010`), matching `DERIVATION.md:17-29`.

**This map's AREA is (1)/(2): protocol §5.8 item 1.** Relationship to `lab_prepare.py` and `run_smoke.py`
is in §4.

## 1. The stage table (plan sheet is the authoritative numbering; protocol §5.8 is the content)

Protocol §5.8's own list (`experiments/live_ab/design/protocol_FINAL.md:1354-1374`) is numbered 1–8 with
no heading called "stage table"; it is a plain enumerated list under "5.8 Pre-freeze out-of-design
phase" (heading at `protocol_FINAL.md:1327`). The plan sheet
(`results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json`, `finite_feasibility_sheet.stage_rows`,
an 11-row array) is what actually assigns integer "stage" ids and is what the reviews' stage numbers
refer to:

| plan `stage` | row name | maps to protocol | row index |
|---|---|---|---|
| 0 | "spent instrument smoke, 2026-09-22" | not in §5.8 | 0 |
| 10 | "serving build of protocol 2.2 (precondition of item 1)" | precondes item 1 | 1 |
| **1** | **"serving receipt/golden/template/conformance"** | **§5.8 item 1** | **2** |
| 2 | "counter-semantics test" | §5.8 item 2 | 3 |
| 3 | "loaded reference sweep" | §5.8 item 5 (+ containment probe, stage 7) | 4 |
| 4 | "duration calibration" | §5.8 item 3 | 5 |
| 5 | "side-by-side calibration" | §5.8 item 4 | 6 |
| 6 | "real-server dress rehearsal" | §5.8 item 6 | 7 |
| 7 | "model-free checks and freeze inputs" | §5.8 items 5(containment),7,8 | 8 |
| 8 | "extended CPU replay (protocol 11.5)" | not in §5.8; mandatory pre-freeze | 9 |
| 11 | "conditional engineering acquisition under the six caps" (root's "stage-0") | not in §5.8 | 10 |

Cite: `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json` → `finite_feasibility_sheet.stage_rows[0..10].stage/.name/.section_5_8` (read via `python3 -c "json.load(...)"`, field values transcribed above; this JSON is dated 2026-09-23 and is **not necessarily current** — see §5 for a place it is stale).

Note the numbering trap the old map already avoided but is worth restating: plan-`stage 3` = protocol
item 5 = "loaded reference sweep", the thing the NO-GO review calls "the stage-3 two-stream loaded
sweep" — the "two-stream" description is not a stage number, it is `lab_load`'s two concurrent HTTP
streams (see `lab_load.py`), separate from this map's stage 1.

**Plan `stage: 0` = "spent instrument smoke" is `experiments/live_ab_serving/run_smoke.py`** (see §4) —
already executed and closed, listed as `completed` on that row, and it is a *precondition-style*
one-off acquisition instrument, not part of the §5.8 numbered sequence and not reusable as stage 1's
driver itself (different purpose: observing real overlap of two threads on one server, not producing
golden objects).

## 2. What the frozen protocol REQUIRES for stage 1 (§5.8 item 1)

- `protocol_FINAL.md:1354-1356`: "**Serving build and manifest** (2.2), then the receipt smoke test and
  golden-object capture per server; the template rule and the format-conformance rule of 2.4 for both
  models."
- Golden objects definition: `protocol_FINAL.md:2586-2589` (not directly re-quoted here; old map's line
  numbers for this shifted in the current file layout — re-locate before citing exact line numbers for
  the golden-object definition; the ARCHITECTURE file gives the concrete file-naming contract instead,
  see below).
- Freeze-tree file names for the golden objects: `experiments/live_ab/design/ARCHITECTURE_FINAL.md:190-191`
  — `golden_props_coder.json`, `golden_props_t3.json`, `golden_generation_settings_coder.json`,
  `golden_generation_settings_t3.json`, alongside `serving_manifest.json` (`ARCHITECTURE_FINAL.md:192`,
  "protocol 2.2 item 2: written once").
- Format-conformance rule: at least 9 of 10 responses per model must contain a code block; the ten
  prompts are the six smoke tasks plus four out-of-design prompts (`protocol_FINAL.md:1337-1352`,
  `protocol_FINAL.md:1352`: "With the six smoke tasks they are the ten prompts of the format-conformance
  rule of 2.4"). Threshold `format_conformance_min = 9` is named non-amendable in
  `protocol_FINAL.md:3018` and `protocol_FINAL.md:3773` (N16).
- Conformance prompts are pinned by Amendment 2026-09-24 to
  `prefreeze.conformance_prompts` in `config.json`, byte-identical across config/ARCHITECTURE
  6.1/protocol Appendix B (`protocol_FINAL.md:1341-1352`), with the selection-rule provenance in
  `experiments/live_ab_tools/repair_amendment_v2.py` and receipt
  `results/live_ab/REPAIR_AMENDMENT_V2_RECEIPT_<UTC>.json` (named at `protocol_FINAL.md:1341-1345`).
- If the receipt cannot be proven on the coder, the program does not start:
  `protocol_FINAL.md:2612-2613` (old map's line numbers; not re-verified byte-for-byte in this pass —
  re-check before citing precisely, the surrounding numbered-list text at 1354-1374 was re-verified and
  is current).
- Everything in stage 1 goes on the `_prefreeze` chain, phases `SMOKE`, `TIMING_PILOT`, `SERVER_SMOKE`,
  `REHEARSAL`, closed by `prefreeze_closed`; success outcomes never used for design choices
  (`protocol_FINAL.md:1329-1335`).

## 3. What the code DOES (verified at c62b59b) — building blocks that exist, and what is still missing

**Exists (verified this pass):**

- `experiments/live_ab/lab_server.py:403-479` `start(spec, mode='capture', ...)`: explicitly documented
  (`lab_server.py:464-467`) as "the pre-freeze capture of protocol 5.8 item 1, where the golden objects
  are being made: it may omit [golden_props/golden/sampling], and then returns
  `props_matches_golden: None` / `smoke: None` ... plus `props_tokenized`, the object stage 1 deposits."
  This is the EB1-repaired real lifecycle (`lab_server.py:403-479` docstring documents real `gguf`,
  `serving_manifest`, `launch`, `health`, `identity`, `smoke` stage checks, matching the accepted
  EB1 subset in `origin/main:reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`). It is
  **not** the fabricated placeholder path the 2026-09-23 20:40 NO-GO review found (`origin/main:
  reviews/prerun_bundle_go_nogo_20260923_2040.md`, "EB1 is independently confirmed in source" —
  that finding is about the pre-repair `lab_orchestrator.py`, and does not describe the current
  `lab_server.py`). So `lab_server.start(mode='capture')` gives a stage-1 driver the tokenized
  `/props` object for one server, on request.
- `experiments/live_ab/lab_server.py:212-244` `tokenized_props`: the pure tokenization function that
  produces the same form used for both the golden digest and future observations
  (`lab_server.py:222-224`: "The pre-freeze capture (stage 1) and every later comparison go through
  this one function").
- `experiments/live_ab/lab_orchestrator.py:1567-1610` `load_golden_objects(freeze_dir, cfg,
  server_ids)`: **reads** `golden_props_<server>.json` / `golden_generation_settings_<server>.json`
  from the freeze tree, canonical-digest-compares each against `config.receipt.<member>.<server>`,
  and rejects a golden `/props` whose `model_path` is not tokenized (`lab_orchestrator.py:1598-1603`).
  This is a **consumer** of stage 1's output (used later, at trial freeze / trial start), not the
  stage-1 driver itself — nothing calls it during a capture run, and it never writes anything.
- `experiments/live_ab/lab_orchestrator.py:1670-1699` (`observed_bundle_members`, GOLDEN_FILES loop):
  also only reads/hashes the golden files if present; comment at `lab_orchestrator.py:1680-1684`
  explains this was changed under "repair contract EB1 item 7" so the digest is read from the actual
  file bytes, not copied from config (closing a self-comparison hole) — again read-only.
- `experiments/live_ab/lab_data.py:394` `normalize_prompt` and `experiments/local_stream/agent.py:69,77`
  `build_user_prompt` / `extract_code`: reusable pieces for the conformance/template check, but nothing
  wires them into a stage-1 conformance counter.
- `experiments/live_ab/config.json:209-217`: `prefreeze.format_conformance_min = 9` and
  `prefreeze.conformance_prompts` **now populated** with `oodp/1..oodp/4` (`entry_point`s
  `interleave_words`, `covered_length`, `most_named`, `rotate_digits`). **This corrects the older,
  stale map** at `an older owner note written at b049307 (not committed)`, which said "all four
  prompts are absent" — that was true at the older mapped commit (`b049307`) but is **not** true at
  `c62b59b`: the Amendment 2026-09-24 text describing this pool-and-seed selection is present in
  `protocol_FINAL.md:1338-1352`, and the prompts are committed in config.

**Still MISSING at c62b59b (re-verified, not carried over blind from the old map):**

- **The golden-request driver.** Golden objects need "the full `/props` plus
  `__verbose.generation_settings` of a reference request" (per protocol wording paraphrased at
  `protocol_FINAL.md` and matching `ARCHITECTURE_FINAL.md:190-191`'s file pair). No code sends that
  reference generation request and writes `generation_settings`. `LlamaClient.__init__`
  (`experiments/live_ab/lab_client.py:399-410`) has a **mandatory** `golden: GoldenReceipt` constructor
  argument (`GoldenReceipt` defined `lab_client.py:247-257`), so `LlamaClient` cannot be used to make
  the very first reference request that would produce the golden receipt — this is a real
  chicken-and-egg gap in the existing client, re-verified at current line numbers (not merely inherited
  from the stale map, whose citations for this were `lab_client.py:407-408, 689-691` under a possibly
  different line count).
- **The writer.** Nothing under `experiments/live_ab/*.py` (excluding tests) writes
  `golden_props_<server>.json` or `golden_generation_settings_<server>.json` into a freeze tree.
  `grep -rn "golden_props_\|golden_generation_settings_" experiments/live_ab/*.py` (excluding
  `tests_*`) shows only: `lab_common.py` (schema key lists), `lab_eventlog.py` (schema field decls),
  `lab_verify_log.py` (verifier reads these keys from an opened chain / from config, does not write
  them), and `lab_orchestrator.py` (read-only, as above). `dryrun_live_ab.py:229-295` uses
  `mock_golden_props(...)` — a **mock-only** stand-in for the dry-run harness, not a production
  capture path.
- **The template-rule / conformance-counter driver.** No function or entry point counts "≥9 of 10
  responses contain a code block" against the ten format-conformance prompts, or checks the "template
  rule" of `protocol_FINAL.md:1354-1356`. `grep -rn "run_stage\|conformance_counter\|template_rule"
  experiments/live_ab/*.py experiments/live_ab_controls/*.py` returns nothing.
- **No orchestrated stage-1 entry point at all.** `grep -rn "def run_stage\|stage1"
  experiments/live_ab/*.py experiments/live_ab_controls/*.py` (excluding the roster-stage-1 test/file
  names already covered in §0.3) returns nothing; `lab_orchestrator.py` has no prefreeze-phase driver —
  the phase names (`prefreeze`, `smoke`, `server_smoke`, ... — `experiments/live_ab/lab_eventlog.py:166-167`,
  `E_PHASE = _E('prefreeze', 'smoke', 'server_smoke', 'randomizing', 'draining', 'post_decision',
  'paused', 'ended', 'aborted')`) exist only as the closed vocabulary the chain schema accepts, not as
  code that drives a capture run. Re-verified: no `timing_pilot` or `rehearsal` value is in `E_PHASE`
  either (the old map's same observation about missing `E_PHASE` values still holds, re-checked at the
  current line numbers above).
- **The 2026-09-23 plan sheet's own `failures_and_missingness` list for stage 1**
  (`results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json` →
  `finite_feasibility_sheet.stage_rows[2].failures_and_missingness`) says: "golden objects not
  captured: `experiments/live_ab/config.json:131-132` are null" (**still true**, re-verified: those two
  lines are `receipt.golden_props_sha256` / `receipt.golden_generation_settings_sha256`, both
  `{"coder": null, "t3": null}` at c62b59b) and "the stage's driver is not identified at HEAD: a grep of
  `experiments/live_ab/*.py` (tests excluded) finds no calibration, rehearsal, conformance or
  golden-capture entry point" (**still true**, re-verified independently above). The same
  `failures_and_missingness` entry "four hand-written conformance prompts ABSENT from config" is
  **now stale relative to c62b59b** — see the config.json citation above; the plan-sheet JSON itself was
  not updated after the Amendment 2026-09-24 commit that populated `conformance_prompts`.

## 4. Relation to `lab_prepare.py`, `run_smoke.py`, and the stage-1 regression fixtures

- **`experiments/live_ab/lab_prepare.py`** (1,075 lines) is the entry point for **plan-`stage 3`**
  (protocol §5.8 item 5, "loaded reference sweep"), not stage 1. Its own module docstring
  (`lab_prepare.py:1-27`) says it exists only to wire `AttemptLedger`/`on_attempt=ledger.append` into
  the real sweep entry point, and explicitly: "It does not start a server, call a model, or provide the
  protocol 3.2 rule 4 load regime" (`lab_prepare.py:21-26`) — `run_reference_sweep` refuses without an
  externally supplied, already-authorized load-coverage observer. There is **no** golden/stage-1 code
  in this file (`grep -n "golden" lab_prepare.py` → no hits); its only "stage" mentions are about the
  stage-3 two-stream diagnostic (`lab_prepare.py:119,122`) and a generic `stage=` kwarg used for error
  labeling (`lab_prepare.py:170,519`, values `'reference sweep startup'` / `'preparation'`). The
  relationship to stage 1 is only sequencing: protocol order puts item 1 (serving build/golden capture)
  before item 5 (loaded sweep), because the sweep needs a running, identity-verified server — but no
  code enforces or encodes that ordering today; nothing in `lab_prepare.py` calls
  `lab_server.start(mode='capture')` or reads a golden file.
- **`experiments/live_ab_serving/run_smoke.py`** (2,462 lines) is **plan-`stage 0`**, "spent instrument
  smoke, 2026-09-22" — already run and closed. Its own header says it is "INSTRUMENT ONLY. Not a trial
  episode, roster or reference sweep, calibration, rehearsal grid or deployment decision"
  (`run_smoke.py:1-5`) and it is a one-server, two-thread, capped overlap-observation acquisition, not
  a golden-object capture. It lives in `experiments/live_ab_serving/`, **outside** the harness pin glob
  `experiments/live_ab/*.py` (per the pin definition the old map cites at `lab_common.py:621-628`, not
  re-verified byte-for-byte this pass but the directory boundary itself is unchanged: `run_smoke.py` is
  a sibling directory, not inside `experiments/live_ab/`). Its relevance to stage 1 is as a **design
  pattern**, not code reuse: it demonstrates the write-ahead-permit / terminal-resolution shape (intent
  persisted before any transport, refusal if not persisted, one finalize path — `run_smoke.py:1546-1586,
  1602-1620` per the old map, not re-walked line-by-line this pass) that root's EB5 ruling
  (`origin/main:reviews/restart_cap_estimand_ruling_20260923_2114.md`, item 1: "Every worker is
  resolved before a terminal record") requires any new stage driver to follow. A future stage-1 driver
  would be expected to follow this same shape, but no code currently connects `run_smoke.py` to stage 1.
- **`Stage1RegressionFixtureTests`** (`experiments/live_ab/tests_lab_design.py:1971-2010`) is unrelated
  to the protocol §5.8 item-1 driver this map is about — see §0.3. It is a completed, passing-when-
  sources-present regression check on the **roster** build, and its existence should not be read as
  evidence that any part of the golden-capture/conformance stage-1 driver has test coverage. A targeted
  search (`grep -n "golden\|conformance\|smoke" tests_lab_design.py`) beyond this class was not
  exhaustively re-walked this pass; no golden-capture-specific test class name was found in the earlier
  full-file scan used to build this map.

## 5. Summary — protocol REQUIRES vs. code DOES, for stage 1

| | requires (protocol §5.8 item 1) | code does (c62b59b) |
|---|---|---|
| Serving build + manifest | `protocol_FINAL.md:1354-1355` | manifest verified only inside `lab_server.start`'s `serving_manifest` stage at every start (`lab_server.py:415-420`); no separate stage-1 "serving build" driver identified (plan sheet's `stage 10` row, precondition, also has no driver identified per `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json` `stage_rows[1]`, not individually re-dumped this pass) |
| Receipt smoke test | `protocol_FINAL.md:1355` | `lab_server.smoke` / `_smoke_attempt` exist (`lab_server.py:645-727`) and run inside `start(mode='trial')`; capture mode explicitly returns `smoke: None` (`lab_server.py:465-466`) — the receipt smoke as a **stage-1 deliverable** (proving the receipt on the coder before the program starts, `protocol_FINAL.md:2612-2613` per old map) has no dedicated driver call site found |
| Golden-object capture | `protocol_FINAL.md:1355-1356`; file contract `ARCHITECTURE_FINAL.md:190-191` | `lab_server.start(mode='capture')` gives tokenized `/props` (`lab_server.py:464-467`); no code sends the reference generation request for `generation_settings`, and no code writes either golden file. `config.json:131-132` still null |
| Template rule | `protocol_FINAL.md:1356` | no driver found |
| Format-conformance rule (2.4) | `protocol_FINAL.md:1356`, `1337-1352`; threshold `config.json:209` | prompts now pinned (`config.json:210-217`); no counter/driver wired to them |

## Pins referenced

- Worktree HEAD: `c62b59b71cf6caa468069575b6c488ae2995330d` (`git rev-parse HEAD` in the worktree).
- Accepted base tag: `session60-eb1-eb5-subset-v1` = `c7750a3721eda5ba1dcdb18df17065015d6db1e3` (per
  `origin/main:reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`).
- `origin/main` HEAD at fetch time: `e37ed01` ("Correct bounded review timestamp"); `c62b59b` is
  described by that same review as "Doc-only successor of the v1 tag: root 22:20's two corrections" and
  changes only the reproduction guide / results index (no production or harness byte changed since
  `98ce004`).

## Caveats / not independently re-verified this pass

- Exact line numbers for `protocol_FINAL.md:2586-2589` (golden-object definition) and
  `:2612-2613` (no-receipt-no-start rule) are carried from the older map at `b049307` and were **not**
  re-opened at those exact lines this pass (the surrounding §5.8 numbered list at 1327-1450 WAS
  re-verified and matches). Re-open those exact spans before citing them as load-bearing.
- The harness-pin glob mechanics (`lab_common.py:621-628`, `764-767`) were not re-read this pass; only
  the directory-boundary fact (run_smoke.py lives outside `experiments/live_ab/`) was used, which does
  not depend on those line numbers.
- `tests_lab_design.py` was not exhaustively scanned end-to-end for every golden/conformance-adjacent
  test; the negative claim "no stage-1 driver test exists" rests on the `grep` calls shown above plus
  the targeted read of `Stage1RegressionFixtureTests`, not a full-file read.
