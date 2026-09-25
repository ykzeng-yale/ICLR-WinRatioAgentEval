# Stage 4, 5, 6 driver map (live_ab prospective trial)

READ-ONLY mapping. Repo `ykzeng-yale/ICLR-WinRatioAgentEval`, worktree
`<session work area>/wt-eb1`, HEAD **c62b59b** on
`session60/repair-eb1`. Accepted base tag `session60-eb1-eb5-subset-v1` = `c7750a3`
(peels to the same tree area; nothing in stages 4-6 changed between the tag and HEAD —
the two head commits after the tag are doc-only, verified with `git diff c7750a3 c62b59b
--stat`, which touches only `experiments/live_ab_controls/REPRODUCE_EB1_EB5_SUBSET.md` and
`results/SESSION60_RESULTS_INDEX.md`, matching the bounded review's own description,
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`, "Make a doc-only successor
commit... Preserve the receipt and companion unchanged").

Abbreviations: **P** = `experiments/live_ab/design/protocol_FINAL.md`; **A** =
`experiments/live_ab/design/ARCHITECTURE_FINAL.md`; **C** = `experiments/live_ab/config.json`;
**S** = `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json` (owner-produced plan
sheet, byte-identical between the old map's base `b049307` and `c62b59b` — verified with
`git diff b049307 c62b59b -- results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json`,
empty output). All line numbers below were re-read at `c62b59b`; none are carried over
unverified from the stale map at `b049307`.

Numbering: the protocol's own stage list is §5.8 items 1-8 (`P:1327` heading, items at
`P:1351`-`P:1382`). "Stage 4/5/6" in the task and in the go/no-go review's item 2
(`reviews/prerun_bundle_go_nogo_20260923_2040.md`, "stages 1, 2, 4-6, the stage-3
two-stream loaded sweep") map: **stage 4 = §5.8 item 3** (duration calibration, `P:1362`-`1366`),
**stage 5 = §5.8 item 4** (side-by-side calibration, `P:1368`-`1376`), **stage 6 = §5.8 item 6**
(real-server dress rehearsal, `P:1378`-`1386`). This is unchanged from the stale map's
numbering and is confirmed against the plan sheet's own `id: 4/5/6` entries (`S:2164`,
`:2172`(name), `:2274`(id 5 purpose), `:2402`-`2404`(id 6 name/status)).

---

## Stage 4 — duration calibration (`P:1362`-`1366`, plan `S` id 4 around line 2164)

### Protocol requires
- Fixed **240-episode** plan: 5 repetitions x 6 smoke tasks x 2 workflows x 2 models x 2
  concurrency levels, at concurrency 1 and 2, both workflows, both models (`P:1362`-`1364`).
- `c_max` = the maximum single-call duration over that fixed sample; sets
  `request_timeout_s` and hence `episode_hard_cap_s` by 5.6's rules; checks memory
  (`P:1364`-`1366`).
- Root's unit correction: "240 means episodes," 360-600 logical calls implied, not an
  HTTP-attempt ceiling (`reviews/live_prefreeze_root_decisions_20260921_1929.md:13`, read
  on `origin/main`).
- `episode_hard_cap_s` is **computed from the formula and the pinned `request_timeout_s`;
  it never reads a typed literal** — `config.json` carries `episode_hard_cap_s: null` until
  the function runs (`experiments/live_ab/lab_worker.py:106`-`108`, docstring of
  `episode_hard_cap_s`).

### Exists now
- `request_timeout_s(c_max)` — pure function, `max(180, 30*ceil(4*c_max/30))`
  (`experiments/live_ab/lab_worker.py:95`-`98`).
- `episode_hard_cap_s(execution)` — pure function implementing 5.6's worst case
  (`experiments/live_ab/lab_worker.py:101`-`115`).
- `Job` TypedDict (`trial`, `arm`, `workflow`, `server`, `sampling`, `limits`, `paths`,
  etc., `total=False`) and `run_job`/`main` — the one-episode subprocess entry point
  (`experiments/live_ab/lab_worker.py:73`-`90` for `Job`; `:473` `run_job`; `:641`-`686`
  `main`). Unchanged byte-for-byte since the old map's base (`git diff b049307 c62b59b --
  experiments/live_ab/lab_worker.py` is empty).
- `World.build_job` / `World.spawn` on the orchestrator — the only existing
  pair-synchronous job builder/launcher, but they are orchestrator-trial-loop methods, not
  a standalone calibration driver (`experiments/live_ab/lab_orchestrator.py:3649`
  `build_job`, `:3743` `spawn`; class `World` at `:2620`). (Old map cited `:1801`/`:1894`;
  those line numbers moved because `lab_orchestrator.py` grew by ~2,830 lines between
  `b049307` and `c62b59b`, entirely EB1/EB5 work — `git diff --stat b049307 c62b59b --
  experiments/live_ab/lab_orchestrator.py` = "2830 insertions(+), 201 deletions(-)".)
- `config.json:prefreeze.calibration_plan` = `{"repetitions":5,"smoke_tasks":6,"workflows":2,
  "models":2,"concurrency_levels":2,"episodes":240}` (`experiments/live_ab/config.json:219`,
  re-grepped at c62b59b — content unchanged from before, only earlier lines in the same
  file shifted because the 4 out-of-design prompts were inserted above it, see Stage-1 note
  below).
- New since the stale map: `config.json:"server_supervision"` =
  `{"max_supervised_restarts_per_server_per_trial":3,"on_exceeding":"abort_trial_incomplete"}`
  (`experiments/live_ab/config.json:225`, added by EB1 work per
  `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 4 and the restart-cap ruling). Any
  stage-4/5/6 driver that starts/restarts a server must now read and respect this cap and
  the `server_start_failed` event schema (`P:2572` row 28) — this is a real, live
  constraint that did not exist when the stale map was written.

### Missing (still, confirmed at c62b59b)
- **No stage-4 driver exists anywhere in `experiments/live_ab/*.py` (tests excluded).**
  Re-verified: `grep -liE "calibrat|rehears|conformance|golden_captur|capture_golden"` over
  the 26 non-test `.py` files in `experiments/live_ab/` returns only incidental hits — a
  `rehearsal_only` config-flag check in `lab_injected_decision.py:98,101` and the word
  "calibration" inside a docstring in `lab_worker.py:97`. No entry point. This matches the
  plan sheet's own claim, still true: `S:357` ("the stage's driver is not identified at
  HEAD: ... no calibration, rehearsal, conformance or golden-capture entry point and no
  prefreeze-phase support in `lab_orchestrator.py`").
- No 240-row schedule file exists anywhere in the repo (`find` for `*calib*`/`*schedule*`
  under `experiments/live_ab*` found nothing but `design/SERVING_LOAD_REHEARSAL.md`, which
  is a spec, not a schedule).
- No pair-synchronous launcher outside the orchestrator's trial loop; no calibration job
  shape distinct from a trial `Job`.
- No `c_max` reducer with censoring, and no memory check driver.
- `lab_eventlog.E_PHASE` still has **no** `timing_pilot` or `rehearsal` value — only
  `('prefreeze','smoke','server_smoke','randomizing','draining','post_decision','paused',
  'ended','aborted')` (`experiments/live_ab/lab_eventlog.py:166`-`167`, re-verified at
  c62b59b; this constant tuple is unchanged even though the file grew ~738 lines
  elsewhere).
- The plan sheet's own status line for stage 4 (id 4): **"NOT AUTHORIZED"**, proposed to
  run on "the stage-10 durable build," blocked "like stage 1 plus root clearance of this
  component" (`S:2166`). No later review on `origin/main` (checked full `reviews/` log
  between `b049307` and `e37ed01`, 18 commits, all EB1/EB5-titled) lifts this.

---

## Stage 5 — side-by-side calibration of every contrast (`P:1368`-`1376`, plan `S` id 5 around line 2272)

### Protocol requires
- For **each of the four contrasts** (T1-T4), latency of each arm on the out-of-design
  prompts (i) solo and (ii) beside the other arm of that contrast, exactly as a pair runs
  (`P:1368`-`1370`).
- Compression statistic `C = (median side-by-side latency ratio candidate/incumbent) /
  (median solo latency ratio candidate/incumbent)` over 6 smoke tasks x 5 repetitions; one
  `C` per contrast, frozen into that contrast's estimand text (6.2) and printed in
  section 16 item 6 and Appendix E (`P:1370`-`1373`).
- Root: 30 pairs per contrast (hence 240 new episodes), orientation balanced **15/15**
  within each contrast, fixed before measurement by a deterministic prospective
  assignment, reusing item-3 (stage 4) solo measurements by explicit
  task/model/workflow/replicate links; concurrency-2 stage-4 cells are **not** reusable as
  stage-5 pairs (`reviews/live_prefreeze_root_decisions_20260921_1929.md:15`, `:17`, read on
  `origin/main` — lines re-confirmed against the live file, unchanged since it is a fixed
  historical review).
- Runs only after stage 4 yields an **uncensored** `c_max` (plan sheet `S:2276`, citing OD1).

### Exists now
- Nothing stage-5-specific. `config.json:prefreeze.side_by_side_compression_C` =
  `{"T1": null, "T2": null, "T3": null, "T4": null}` — still all null
  (`experiments/live_ab/config.json:221`, re-verified; unchanged from before — confirmed
  the only change to `config.json` between `b049307` and `c62b59b` is the 4 conformance
  prompts and `server_supervision`, per `git diff b049307 c62b59b --
  experiments/live_ab/config.json`, shown in full above).

### Missing (still, confirmed at c62b59b)
- No orientation schedule file; the plan sheet itself says "NOT YET WRITTEN" language
  applies (the stale map's citation `S:214, :622` for that literal phrase belongs to a
  different, superseded plan doc lineage the old map conflated — re-checked: in the
  current `FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json` the id-5 status field instead reads
  **"NOT AUTHORIZED ... blocked like stage 1 plus root clearance ... starts only after
  stage 4 yields an uncensored `c_max` (OD1)"**, `S:2276`). Either way: no orientation
  schedule exists as a committed artifact anywhere in the repo.
- No runner for mixed-arm/mixed-model pairs; no code computing `C` from medians. `C` stays
  `null` in the pinned config (above).
- Same "driver not identified at HEAD" finding applies (`S:420`, `S:556`, `S:623` are the
  repeated instances of that exact sentence across the stage entries; re-verified present
  and unchanged in the byte-identical plan file).
- OD1 (the start-condition dependency on an uncensored stage-4 `c_max`) is unresolved —
  it presupposes stage 4 exists and has run, which it has not.

---

## Stage 6 — real-server dress rehearsal + injected-decision fixture (`P:1378`-`1386`, plan `S` id 6 at `S:2402`-`2404`)

### Protocol requires
- Full production path: orchestrator, pair-synchronous scheduler, program chain, both
  workflows in both orientations, both models, spools, execution lock, per-pair `/metrics`
  scrapes, live monitor and reference rule, real anchors on a drill branch, the verifier
  and one builder run — under a rehearsal-only config with small `n_min`/wide margin so a
  decision, its blocking receipt, the switch and a post-switch phase all occur
  (`P:1378`-`1382`).
- Four injected faults, each at least once: orchestrator kill, worker kill, forced server
  kill with supervised restart, forced pause/resume (`P:1382`-`1384`).
- Freeze conditions: verifier PASS, builder run without error, and the frozen receipt
  comparison passes on **100%** of rehearsal responses, including complete
  `self_test_repair` episodes with repair rounds on both slots and two consecutive
  episodes with an identical prefix on the same slot (`P:1384`-`1386`). Rehearsal success
  outcomes are never used/reported as observations (`P:1386`, citing 1.5 item 17).
- Root's finite cap: **at most 16 pairs / 32 episodes**, covering both models/workflows/
  orientations and the four named fault drills in a prospectively written schedule, plus a
  separate deterministic injected-decision fixture at the monitor/router interface
  (`reviews/live_prefreeze_root_decisions_20260921_1929.md:23`, read on `origin/main`,
  re-confirmed unchanged).
- Plan sheet's concrete schedule proposal (status **PROPOSED**, not committed): segments
  T4, T2, T1, T3, 4 pairs each, fixed fault positions — T4 pair 3 = coder server kill +
  supervised restart, T2 pair 2 = worker kill, T1 pair 2 = orchestrator kill then resume,
  T3 pair 2 = forced pause/resume; orientation by "production per-pair OS coin" (OD16,
  "~13.2% chance an orientation path is uncovered") (`S:2415`-`2431`).

### Exists now
- The orchestrator itself (`experiments/live_ab/lab_orchestrator.py`), but its CLI accepts
  only `--trial`, and `--max-pairs` is explicitly **mock-only** — passing it against a real
  run raises `SystemExit('--max-pairs is a mock-only option')`
  (`experiments/live_ab/lab_orchestrator.py:5854`, `:5876`-`5879`). (Old map cited
  `:3239`/`:3257`-`3260`; those lines moved with the file's growth, content re-verified
  identical in substance.)
- `dryrun_live_ab.py` — mock-only kill hooks and a mock freeze-tree builder
  (`build_mock_freeze`, `experiments/live_ab/dryrun_live_ab.py:173`; `make_mock_roster`
  `:87`; `mock_serving_manifest` `:138`). No real fault injector.
- `lab_injected_decision.py` — `inject_decision(kind='DEPLOY')`
  (`experiments/live_ab/lab_injected_decision.py:108`), the standalone deterministic
  fixture the protocol separately calls for; unchanged byte-for-byte since `b049307`
  (`git diff` empty). It refuses to arm against a real trial unless
  `cfg.get('rehearsal_only')` is set (`:98`, `:101`).
- `lab_anchor.py --local-only` — commits without pushing/commenting, for mock dry runs only
  (`experiments/live_ab/lab_anchor.py:13` doc comment, `:462` `add_argument('--local-only')`,
  `:475` branch). Line numbers shifted (file grew 48 insertions/28 deletions) but the flag
  and its "mock dry run only" restriction are unchanged.
- `lab_verify_log.verify_trial` (`experiments/live_ab/lab_verify_log.py:738`, moved from the
  stale map's `:325` because the file grew by 663 lines — that growth is EB1/EB5 receipt
  verification work, not stage-6 driver code).
- `design/SERVING_LOAD_REHEARSAL.md` is a **specification**, not code: its own §4 sequence
  table explicitly marks "steps 3-7 are model execution" and "no step is authorized to run
  yet" (`experiments/live_ab/design/SERVING_LOAD_REHEARSAL.md:106`-`107`), and step 7 of
  that table is calibration (stage 4, 240 episodes), not the dress rehearsal; the doc's own
  §5 lists what it does *not* cover (anchor drill, any number in its §3, execution
  authority) and never claims to cover stage 6's fault-injection rehearsal
  (`:126`-`129`). This is a pre-existing doc (2026-09-22, commit `ce106af`), unrelated to
  the recent EB1/EB5 commits.

### Missing (still, confirmed at c62b59b)
- **No rehearsal freeze-tree builder outside the mock path.** `build_mock_freeze` in
  `dryrun_live_ab.py` is explicitly mock (writes `'mock': True` markers throughout, e.g.
  `experiments/live_ab/dryrun_live_ab.py:106`, `:145`, `:155`, `:169`).
- **No real fault injector** (orchestrator kill / worker kill / server kill+restart / pause
  resume) wired to any driver. `grep -rln "inject"` across non-test `.py` files in
  `experiments/live_ab/` also hits `dryrun_live_ab.py` (`:320`, a comment about "the crash
  injector" ordinals, used only by the mock dry-run tests), `lab_common.py` (`:1013`-`1053`,
  the `injected_decision_fixture` activation-key guard/refusal policy, not a fault
  injector), `lab_prepare.py` (`:165`-`169`, delegates to that same guard), and
  `lab_hostcheck.py` (`:1027`-`1107`, unit-test injection points for the host-quiescence
  probe, unrelated to stage 6). None of these is a real orchestrator/worker/server/pause
  fault injector for a live rehearsal.
- **No path-coverage / 100%-receipt report** module.
- It remains **undecided** whether the rehearsal writes trial-id chains under a
  `_prefreeze` subtree or to the `_prefreeze` chain itself — the protocol's own wording is
  ambiguous ("chained under `_prefreeze`", `P:1378`) and no later amendment resolves this.
  `grep -n "Amendment" experiments/live_ab/design/protocol_FINAL.md` lists every amendment
  block in the file (lines 443, 466, 590, 962, 1044, 1337, 1567, 1585, 2572-2592 region,
  2721, 2752, 2876, 2887, 3020, 3126, 3154, 3287, 3294, 3310); reading each one, exactly
  one (`P:1337`) is the stage-1 out-of-design-conformance-prompt amendment and every other
  one is EB1/EB5/server-supervision/decision-reporting related (dated 2026-09-24 or
  2026-09-25, tied to the go-nogo, restart-cap, serving-manifest, decision-eligibility or
  predecision-abort reviews). None touches §5.8 item 6, the rehearsal chain placement, or
  any stage-4/5/6 driver.
- Same "driver not identified at HEAD" plan-sheet language applies to stage 6 as well
  (`S:693`, part of the repeated sentence block, re-verified present).
- Blocked (per plan sheet, unchanged): **OD4** (rehearsal config) and **OD10** (drill-branch
  anchor postings), plus "the stage-1 blockers" (`S:2404`). OD16 (orientation-coin coverage
  gap, ~13.2%) is also unresolved (`S:2427`).
- The go/no-go review's EB1 finding (that the *production* orchestrator server-start path
  was fabricating success receipts) is now addressed by the EB1+EB5 subset per the bounded
  review — but the bounded review is explicit that this is "an engineering-preparation
  subset, not a prospective-study freeze, scientific outcome" and that "the loaded phase
  still needs named server/capacity evidence and actual production-path EB5 worker
  resolution" before any loaded episode, which stage 6 (a real-server rehearsal) is
  (`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`, disposition section,
  read on `origin/main`). **No loaded/design/trial episode is approved** — the review's own
  words, verbatim.

---

## Shared facts across stages 4-6 (re-verified at c62b59b, not just carried from the stale map)

- All three stages write to one `_prefreeze` chain (phases `SMOKE`, `TIMING_PILOT`,
  `SERVER_SMOKE`, `REHEARSAL`), closed by `prefreeze_closed`; success outcomes are never
  used for design choices; every try is logged, unknown usage recorded as null
  (`P:1330`-`1335`).
- The pin is `HERE.glob('*.py')` plus `config.json`, non-recursive, tests included
  (`experiments/live_ab/lab_common.py:653`, `names = sorted(p.name for p in
  HERE.glob('*.py'))` — re-confirmed present at c62b59b, unchanged in mechanism though the
  file grew 93 lines, all EB1-related additions per the diff).
- Root ruling still in force: "required execution/containment code must still be pinned
  even if added now" and "do not move execution-relevant code outside the pin set just to
  avoid changing a hash" (cited in the stale map from
  `reviews/live_roster_root_decisions_20260921_1854.md:25` and
  `reviews/live_load_coverage_decision_20260921_2005.md:13` — not re-read in this pass
  since they predate `b049307` and are unrelated to the recent EB1/EB5 commit range; flagging
  as **not re-verified in this session**, carried over from the prior map).
- New since the stale map, and directly relevant to any stage-4/5/6 driver's future pin
  plan: `lab_serving_manifest.py` was added (`experiments/live_ab/lab_serving_manifest.py`,
  new file per `git diff --name-status b049307 c62b59b`) as the one write-once serving
  manifest artifact, re-verified at every invocation/start/restart
  (`experiments/live_ab/design/ARCHITECTURE_FINAL.md:163`, module table row). Any stage
  4/5/6 driver that starts a server will need to go through this manifest-binding path,
  not the old bare `lab_server.start`.
- The bounded review's ranked next work (item 2) is exactly this area: "EB2-EB4 model-free
  drivers and EB5 loaded-phase preparation, with exact code/config/seed pins and
  incremental immutable completed-shard receipts" — i.e. root wants the stage 1/2/4-6
  drivers built **model-free** (no server, no model call) with shard-by-shard immutable
  receipts, not one large delivery (`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`,
  "Session session60 may then advance..." paragraph). The go-nogo review's original item 2
  said the same about reviewable increments (`reviews/prerun_bundle_go_nogo_20260923_2040.md`
  item 2; `reviews/restart_cap_estimand_ruling_20260923_2114.md` item 2, "Deliver reviewable
  increments").

## Not found / could not confirm in this pass
- No stage-6-specific protocol amendment text exists in `protocol_FINAL.md` at c62b59b —
  not found, despite the bounded review's forward-looking mention of a future EB2-EB4
  amendment; only the stage-1 conformance-prompt amendment (2026-09-24) and the v2/v3/v4
  EB1/EB5 amendments exist today.
- No orientation-schedule artifact, no calibration-schedule artifact, no rehearsal
  freeze-tree artifact — not found anywhere under `experiments/live_ab*` or `results/live_ab/`
  (searched by name pattern and by grep for driver entry-point names).
- Root decisions specifically resolving OD1, OD2, OD4, OD6, OD9, OD10, OD14, OD16, OD17 —
  not found in any review commit between `b049307` and `e37ed01` on `origin/main` (all 18
  intervening review commits are titled around EB1/EB5/SM8/decision-eligibility, none
  mention resolving these OD numbers by number; said explicitly as still open by the
  25 Sept 22:20 bounded review's own "still need explicit root review" language).
