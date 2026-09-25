# Map of held branches session60/repair-replay (72230b8) and session60/repair-amend (ff152e9)

Read-only mapping. Repo read at worktree wt-eb1, HEAD c62b59b (session60/repair-eb1). All citations
are `path:line at <ref>` unless marked `ref:path:line`. "not found" is stated rather than guessed.

## 0. Topology (the load-bearing fact for everything below)

`git merge-base 72230b8 c62b59b` = `git merge-base ff152e9 c62b59b` = `b049307` (the older map's base).
Both held branches fork from **b049307**, not from the accepted tag `session60-eb1-eb5-subset-v1` (c7750a3)
or from c62b59b. Between b049307 and c62b59b there are **38 commits** on the accepted line
(`git log --oneline b049307..c62b59b at c62b59b`), including the entire EB1a-c real-server-lifecycle
repair, the EB1 restart-cap 3-case ruling implementation, EB1 receipt attribution, the harness-pin
successor chain, and the SM8 diagnosis. Neither held branch contains any of these 38 commits.

Consequence: a naive `git diff c62b59b 72230b8 --stat` (or vs ff152e9) is dominated by files the held
branch simply **never had**, not by anything the branch deleted or edited. This report separates that
noise from the branches' actual, real content (verified via `git log --oneline b049307..c62b59b -- <path>`
plus `git show --stat` of each held-branch commit individually).

## 1. session60/repair-replay (72230b8) — actual content

Six commits on top of b049307, verified individually with `git show --stat <sha>` at c62b59b's worktree:
`11fd781`, `d2fe284`, `c26a592`, `90edaa8`, `3d37c7e`, `72230b8`. Between them they touch exactly:
`experiments/live_ab/lab_replay.py` (new), `experiments/live_ab/lab_schedules.py` (new),
`experiments/live_ab/lab_load.py`, `experiments/live_ab/lab_prepare.py`, `tests_lab_isolation.py`,
`tests_lab_design.py`, and three new control files (`tests_lab_replay.py`, `tests_lab_schedules.py`,
`tests_lab_load_resolution.py`) plus `tests_delta_citations.py`. They do **not** touch
`lab_orchestrator.py`, `lab_server.py`, `lab_eventlog.py`, `lab_anchor.py`, `lab_verify_log.py`,
`config.json`, `protocol_FINAL.md`, or `ARCHITECTURE_FINAL.md` — the large diffs against those files in
the raw `c62b59b..72230b8` stat are entirely fork-point staleness (item 0), not branch edits.

### 1a. lab_load.py / lab_prepare.py (c26a592, 72230b8) — ALREADY MERGED, not distinct content

`git diff c62b59b 72230b8 -- experiments/live_ab/lab_load.py` is **empty** (byte-identical). The
main-line commits `9c48512` and `c9310b5` (`b049307..c62b59b at c62b59b`) carry the **identical commit
messages** as the branch's `c26a592`/`72230b8` ("EB5 for loaded background streams: durable load
ledger…" / "EB5: a loaded sweep is accepted only on tracked, observed load…"), and `79bb1ab`
("Integration fix: two statements the merge and the cherry-picks made false") sits between them on
main — this is the same EB5 durable-load-ledger work, already cherry-picked/merged onto the accepted
line via `7730e7f` ("Merge session60/repair-eb5 into session60/repair-eb1…", per `git log`). **Verdict:
not reusable as new work — it is already in the accepted base.** `lab_prepare.py` differs by only 5
lines (`git diff c62b59b 72230b8 -- experiments/live_ab/lab_prepare.py`), a documentation sentence
about `phase_resolution_verdict` not existing "on this branch" (true for 72230b8, false for c62b59b,
which has `lab_orchestrator.phase_resolution_verdict`) — cosmetic only.

### 1b. lab_replay.py (11fd781, 90edaa8) — NEW, not on the accepted line, appears reusable after rebase

Does not exist at c62b59b (`git show c62b59b:experiments/live_ab/lab_replay.py` → does not exist) or
anywhere reachable from it (`git log --all --oneline -- experiments/live_ab/lab_replay.py` lists only
the two branch commits). It is the driver for **protocol §11.5 / plan stage 8**, which
`results/SESSION60_RESULTS_INDEX.md:3362,3856` at c62b59b still lists as missing — i.e. this is exactly
the still-open "EB2–EB4 model-free drivers" work that
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md` (origin/main) item (2) authorizes
Session60 to advance next.

- Module docstring (`experiments/live_ab/lab_replay.py:1-117 at 72230b8`) states it is a **pure CPU
  simulator**: no model, no server, no network, no clock; reads the realized roster, the pilot table,
  frozen config and an explicit outcome-model choice, writes a write-once table/manifest. This is
  model-free and reproduces the frozen §8.1-8.4 band/decide path (`lab_monitor.radius_table`,
  vectorised `band`+`decide`) with a per-cell crosscheck against the scalar `MonitorState` path,
  matching root's requirement (`reviews/restart_cap_estimand_ruling_20260923_2114.md` item 3) that such
  scaffolds be "parameterized" and never hide open decisions.
- It correctly refuses to run silently on the open outcome-model gap: `lab_replay.py:68-116 at 72230b8`
  states, honestly, "PROPOSED, NEEDS ROOT — the outcome model protocol 11.5 does not define" (T3's
  candidate has no pilot; T3/T4 cost pairs have no independent joint-latency source), names
  `open_outcome_model` keys the caller must supply explicitly with no default
  (`lab_replay.py:200-230 at 72230b8`: `PROPOSED_OPEN_MODEL`, `check_ruling_citation`), and requires a
  real `reviews/<file>.md:<line>` citation to mark an entry `RULED` instead of `PROPOSED`
  (`lab_replay.py:855,887 at 72230b8`). It also marks the fixed horizons 295/495 `NOT_SIMULABLE` when the
  roster can't support them rather than bootstrapping — again refusing to silently paper over a gap.
  **This is exactly the "do not hide unresolved design choices behind PROPOSED schedules" discipline
  root asked for** (`reviews/restart_cap_estimand_ruling_20260923_2114.md` item 3), not a violation of
  it — but the outcome-model choice is still genuinely unresolved and needs root's ruling before any
  cell is treated as anything but PROPOSED.
- Imports only `lab_common`, `lab_design`, `lab_enclosure`, `lab_monitor`
  (`lab_replay.py:140-143 at 72230b8`) — none reference `lab_orchestrator` or
  `phase_resolution_verdict`. `lab_design.py`, `lab_monitor.py`, `src/winstats.py` are untouched by any
  of the 38 accepted-line commits (`git log --oneline b049307..c62b59b -- <those paths>` is empty), so
  they are byte-identical between the branch and c62b59b — no merge conflict surface there.
  `lab_common.py` differs, but only by **pure addition** on the accepted side: diffing
  `git show c62b59b:experiments/live_ab/lab_common.py` against `git show 72230b8:...` shows every
  differing line is present-only-in-c62b59b (added by main: `anchor_file_object`/`anchor_comment_body`
  for EB1 receipt attribution, `SERVER_SUPERVISION_KEY`/`server_supervision_cap` for the accepted
  3-case restart cap, and the `ServerStartFailed` exception) — nothing lab_replay.py relies on was
  removed or renamed. **This module looks mechanically rebasable onto c62b59b/c7750a3 without needing
  to touch its own logic.**

### 1c. lab_schedules.py (d2fe284, 3d37c7e) — NEW, not on the accepted line, same caveats as 1b

Same non-existence check as lab_replay.py: absent from c62b59b and from `git log --all` outside the two
branch commits. Serves plan stages 4 and 5 (write-once execution-order schedules), also still listed
missing at `results/SESSION60_RESULTS_INDEX.md:3856 at c62b59b` ("the missing executable drivers for
stages 1, 2 and 4–6"). Same honesty pattern as lab_replay.py: entries are labelled `PROPOSED` or
`RULED` with a mandatory `reviews/<file>.md:<line>` source for `RULED`
(`lab_schedules.py:49-52,131-165 at 72230b8`), and `PLAN_PROPOSED_OPEN_DECISIONS` carries OD1, OD2,
OD14 explicitly as `PROPOSED`, never silently adopted (`lab_schedules.py:108-113 at 72230b8`). I could
not find a root ruling on OD1/OD2/OD14 specifically in the reviews read for this task (checked the
three named authority docs only) — **not found**, so their PROPOSED status may still be current; this
needs a targeted check of the full `reviews/` index before trusting it either way. Imports only
`lab_common` (`lab_schedules.py:84 at 72230b8`) — same "pure addition, nothing removed" relationship to
main's `lab_common.py` as above. Also mechanically rebasable on the same reasoning.

### 1d. Controls (tests_lab_replay.py, tests_lab_schedules.py, tests_lab_load_resolution.py)

New/extended alongside 1b/1c. Given HARD RULES forbid running tests, I did not execute them; based on
commit messages and diff stats they are the reproduction/adversarial controls for the two new modules
(`90edaa8`, `3d37c7e`, `72230b8` messages describe fixing findings from an "adversarial review" with
new negative controls per guard). `tests_lab_load_resolution.py` belongs to the EB5 lab_load.py work
that is already merged (1a) — since lab_load.py is identical to main, these controls are very likely
already-superseded duplicates of whatever controls exist on the accepted EB5 line, but I did not diff
this file against main's controls tree (out of scope budget for this pass); flag for re-check before
reuse.

## 2. session60/repair-amend (ff152e9) — withdrawn, and correctly so

Two commits on b049307: `1349619` ("synchronized pre-outcome repair amendment: conformance prompts and
restart cap (root 20:40 items 2, 4)") and `ff152e9` ("correction run: fix the seven review findings").
Same fork-point staleness as above — the raw diff stat vs c62b59b is dominated by the 38 missing
accepted-line commits (confirmed: `git diff c62b59b ff152e9 --stat` shows the same
lab_orchestrator.py/lab_serving_manifest.py/tests_eb1_*/harness-pin-receipt churn as the 72230b8 diff,
plus its own `experiments/live_ab_tools/repair_amendment.py` / `verify_repair_amendment.py` /
`tests_repair_amendment.py`, none of which are reachable from c62b59b:
`git log --oneline --all -- experiments/live_ab_tools/repair_amendment.py` lists only `1349619`/`ff152e9`).

Two independent reasons this branch is not reusable as-is, both verified in code/text, not from its
commit messages:

1. **It still carries the exact EB1 fabrication bug the 20:40 NO-GO named.**
   `git show ff152e9:experiments/live_ab/lab_orchestrator.py` line 1628 still sets
   `'props_matches_golden': True` unconditionally on the **non-simulated** path inside
   `server_started_body()` (mirrors the sim-path line 1610, which is fine since sim is allowed to be
   trivially true) — i.e. `experiments/live_ab/lab_orchestrator.py:1628 at ff152e9`, the same defect
   `reviews/prerun_bundle_go_nogo_20260923_2040.md` cited verbatim ("`server_started_body()` sets
   `props_matches_golden` and `receipt_matches_golden` to true … without comparison"). This branch never
   received the EB1a-c fix (`11ba426`..`8f0b4ae` on the accepted line); it only added the restart-cap and
   conformance-prompt text on top of the broken orchestrator.
2. **Its restart-cap reportability rule is the version root's later ruling explicitly corrected, and
   says so itself.** `experiments/live_ab/design/protocol_FINAL.md:942-948 at ff152e9`: "**Provisional,
   pending root's ruling** (question (i) of the session-60 repair contract) … It is not final until
   root's ruling is recorded by a further pre-outcome amendment … no freeze may be made while it is
   pending." Root's ruling came at `reviews/restart_cap_estimand_ruling_20260923_2114.md` (21:14, after
   `1349619`'s 20:40-only citation), which called the earlier "no deployment/harm decision" framing "too
   broad" and imposed the **phase-aware 3-case rule** (predecision / post-decision-with-receipt /
   provisional-decision). That 3-case rule is what actually landed on the accepted line — verified at
   `experiments/live_ab/design/protocol_FINAL.md:1579-1583,3301-3317 at c62b59b` (three cases spelled
   out, citing `reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md` and
   `reviews/predecision_abort_reporting_ruling_20260925_0710.md`) and in code at
   `experiments/live_ab/lab_common.py` (`SERVER_SUPERVISION_KEY`/`server_supervision_cap`, present at
   c62b59b, absent from both held branches' `lab_common.py`). ff152e9's cap text is therefore superseded
   by name, by its own admission.

The four out-of-design conformance prompts ff152e9 introduced
(`experiments/live_ab/design/protocol_FINAL.md:3287-3295 at ff152e9`, ids `oodp/1..4`) are **byte-identical**
to what is already in the accepted `config.json` at c62b59b (`prefreeze.conformance_prompts`, diffed via
`python3 -m json` against both revisions) — but ff152e9 itself is not an ancestor of c62b59b, so this
identical content reached main through a different, already-integrated amendment on the accepted line,
not through this branch. **Nothing in ff152e9 is missing from main or safely reusable; withdrawing it
was correct given the current state of both EB1 and the restart-cap ruling.**

## 3. Bottom line for whoever picks this up next

- **Reusable, pending a real rebase (not a merge of the stale tree):** the *logic* of
  `lab_replay.py` and `lab_schedules.py` from `session60/repair-replay` — they are new, model-free,
  currently-missing drivers for exactly the work item
  `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md` item (2) names, they import nothing
  that changed incompatibly on the accepted line, and they already self-report their open decisions
  (outcome model, OD1/OD2/OD14) as PROPOSED rather than silently deciding them. They must be re-applied
  on top of c7750a3/c62b59b (not merged as a diff against b049307), and their controls
  (`tests_lab_replay.py`, `tests_lab_schedules.py`) re-verified in that context — I did not run anything
  per the HARD RULES, so "appears reusable" is a static-reading judgment, not a tested one.
- **Not reusable / already superseded:** `lab_load.py`/`lab_prepare.py`'s EB5 durable-ledger changes
  from the same branch (already merged into the accepted line under different commits) and
  `tests_lab_load_resolution.py` (needs a diff against main's EB5 controls before assuming it adds
  anything).
- **Correctly withdrawn:** all of `session60/repair-amend` (ff152e9) — its orchestrator still fabricates
  `props_matches_golden`, and its restart-cap reportability rule is the pre-21:14-ruling version, which
  the ruling itself and the accepted line both superseded.
- **Not found in the docs I read:** an explicit root ruling on OD1/OD2/OD14 (lab_schedules.py's open
  decisions) — only the three named authority reviews were checked; a full `reviews/` sweep would be
  needed before treating those as either ruled or still open.
