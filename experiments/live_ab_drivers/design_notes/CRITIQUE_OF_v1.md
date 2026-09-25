# Completeness critique of DESIGN_PROPOSAL.md

Read-only review. Nothing edited/committed/checked-out/reset/stashed in `wt-eb1` or any repo
checkout (verified `git status --porcelain` clean before and after, including after a
`git merge-tree` dry run used only to check a claim in finding 1 — `merge-tree` writes no ref and
touches no working tree). All citations below are `path:line at c62b59b` unless marked
`ref:path:line`. I independently re-verified more than 10 of the proposal's citations by reading
the cited bytes directly (listed under each finding, plus a "spot checks that held" section at the
end); the majority of the proposal's ~35 citations I checked were accurate. Two findings below are
substantive; the rest are lower-severity precision/completeness gaps.

---

## Finding 1 (substantive — citation asserts the opposite of its own source; unsupported risk claim)

**Where:** DESIGN_PROPOSAL.md §7, the parenthetical justification for discarding
`session60/repair-replay` (`72230b8`) as a merge candidate:

> "Its versions of `lab_orchestrator.py`, `lab_serving_manifest.py`, `protocol_FINAL.md` and
> `config.json` predate the EB1 fix and the 21:14 restart-cap ruling (`git diff c62b59b 72230b8
> --stat` shows exactly these files differing at the fork point, per `map_held_branch.md`)."

**What I found:**

- `git -C wt-eb1 diff c62b59b 72230b8 --stat -- 'experiments/live_ab/*.py' 'experiments/live_ab/design/*' 'experiments/live_ab/config.json'`
  shows **20 files** differing, not the 4 named — including `lab_common.py`, `lab_eventlog.py`,
  `lab_server.py`, `lab_anchor.py`, `lab_verify_log.py`, `dryrun_live_ab.py`,
  `build_live_ab_results.py`, `ARCHITECTURE_FINAL.md`, and five `tests_*.py` files, on top of the
  4 the proposal names. "Exactly these files" is false as a literal reading of the diff.
- More importantly, `map_held_branch.md:15-18,28-30` — the very file the proposal cites — says the
  **opposite** of what the proposal's parenthetical implies: "a naive `git diff c62b59b 72230b8
  --stat` ... is dominated by files the held branch simply **never had**, not by anything the
  branch deleted or edited" and explicitly lists `lab_orchestrator.py`, `lab_server.py`,
  `lab_eventlog.py`, `lab_anchor.py`, `lab_verify_log.py`, `config.json`, `protocol_FINAL.md` and
  `ARCHITECTURE_FINAL.md` as files the branch's own six commits **do not touch at all**
  (`map_held_branch.md:20-30`, verified per-commit with `git show --stat <sha>` for `11fd781`,
  `d2fe284`, `c26a592`, `90edaa8`, `3d37c7e`, `72230b8`). The large diffs against those files are
  attributed to 38 accepted-line commits the branch lacks (fork-point staleness), not to branch
  edits.
- I independently tested the practical claim that follows this citation — "merging the branch
  wholesale would reintroduce the class of defect the 20:40 review named as EB1" — with a read-only
  `git merge-tree c62b59b 72230b8` (writes nothing, touches no working tree or ref;
  `git status --porcelain` on `wt-eb1` was empty before and after). The simulated 3-way merge
  produces exactly **two** conflicts: `experiments/live_ab/lab_prepare.py` and
  `experiments/live_ab_controls/tests_delta_citations.py`. It does **not** touch
  `lab_orchestrator.py`, `lab_server.py`, or `lab_serving_manifest.py` — because the branch's own
  commits never edited them, so a genuine 3-way merge keeps `c62b59b`'s (post-EB1) versions
  automatically, with no conflict. This directly contradicts the "reintroduce EB1" claim as stated.

**Why it matters:** the proposal's bottom-line recommendation in §7 — hand-port
`lab_replay.py`/`lab_schedules.py` rather than merge or cherry-pick the branch — may still be the
right call for other reasons already in the same section (stale test-file duplication risk,
`tests_lab_load_resolution.py` not diffed, keeping the two `PROPOSED`/`NOT_SIMULABLE` gaps intact
under fresh review rather than inside an old commit). But the specific justification given, and its
citation, overstate the danger and misreport what `map_held_branch.md` actually says. Root should
not accept "merging would reintroduce EB1" as a verified fact; the real, verifiable reasons to
hand-port are the other bullets already in §7 (stale six-commits-behind orchestrator/protocol
content in the branch tree as a *historical artifact* worth never touching, and the undiffed test
file), not this one.

---

## Finding 2 (substantive — Stage 6 "model-free buildable: Yes" is unqualified where Stage 3's is not, and no blocked-item row names the real-server gap)

**Where:** DESIGN_PROPOSAL.md §2 table, Stage 6 row, "Model-free buildable" column: "Yes — extend
the existing mock dry-run with all 4 injected-fault types; assert the coverage report flags every
required path, entirely against `lab_mock_server`."

**What I found:** the same row's own "Protocol requires" cell correctly quotes
`protocol_FINAL.md:1378-1386`, which titles this item "**Real-server dress rehearsal**" and
requires "the **full production path** — orchestrator, pair-synchronous scheduler, program chain,
both workflows in both orientations, **both models**, spools, execution lock, per-pair `/metrics`
scrapes, live monitor and reference rule, real anchors on a drill branch, the verifier and one
builder run" (confirmed by direct read of `protocol_FINAL.md:1378-1386` at `c62b59b`). Nothing
fixture-based can satisfy "real anchors on a drill branch" or the real-server receipt-comparison
freeze condition.

Contrast with the Stage 3 row in the same table, which is careful to say "**Partially**" and adds
an explicit caveat ("cannot *certify* real concurrent decoding-slot occupancy without the real
patched server"), and which is backed by two dedicated rows in §6's blocked-items table
("Building the patched llama.cpp binary...", "Verifying two decoding slots genuinely occupied
concurrently..."). Stage 6 gets no equivalent treatment: §6's table has rows for OD4/OD10 (rehearsal
config / drill-branch anchor postings) and OD16 (orientation-coin gap), but none states in terms
parallel to Stage 3's that **the rehearsal itself, as opposed to its fault-injector/coverage-report
scaffold, is a real-server requirement that no amount of mock-only work can satisfy**.

**Why it matters:** what is genuinely model-free here is the fault-injector interface and coverage
report *tooling* (testing that the tooling correctly flags every required cell) — not protocol
item 6 itself. A reader skimming only the §2 table's "Yes" could conclude Stage 6's dress rehearsal
is now coverable without real servers, which is not true and is not what the rest of the row's own
text says. This should either be downgraded to "Partially" with the same style of caveat Stage 3
got, or §6 should gain an explicit row naming the real-server dependency the way it does for Stage 3.

---

## Finding 3 (citation-precision defect — pseudo-section anchors that do not exist as headers)

**Where:** three recurring anchor-style citations in DESIGN_PROPOSAL.md:

- `` `map_stage3_eb5.md` §missing `` (§2 table, Stage 3 row, "Missing" column)
- `` `map_stage3_eb5.md` §needs_model_or_server_or_root_decision `` (§6 table, three rows)
- `` `map_stage1.md` §risks `` (§8, last risk bullet)

**What I found:** `grep -n "pins_needed\|needs_model_or_server_or_root_decision\|§missing\|§risks"`
against the actual map files returns **no matches** for any of these anchor names as literal
headings. The real headings in `map_stage3_eb5.md` are numbered (`## 1. Authority...` through
`## 8. Bottom line for AREA`); the closest in substance to
`§needs_model_or_server_or_root_decision` is `## 7. Needs the real server / real capacity (cannot
be prepared model-free)`, and there is no heading resembling `§missing` anywhere in that file at
all. `map_stage1.md`'s closest heading to `§risks` is `## Caveats / not independently re-verified
this pass`. (By contrast, `map_stages456.md §missing` and `map_replay.md §3` *do* correspond to
real headings — `### Missing (still, confirmed at c62b59b)` appears three times in that file, and
`## 3. What EXISTS at c62b59b` is a real numbered section — so this is not a blanket problem with
every such citation, only the three named above.)

**Why it matters:** the task's own hard rule requires citations of the form `path:line`. These
three do not meet that bar and are not mechanically checkable the way the rest of the document's
citations are (I could verify essentially every `file.py:NNN` citation I sampled by reading the
exact line; I cannot verify what "§missing" or "§risks" point to in a file that has no such
heading). This does not appear to make the underlying factual claims wrong — in each case I found
a separately, correctly line-cited fact nearby in the same row/paragraph that supports the
substance (e.g., the Stage-3 "does not exist yet" claim is independently and correctly cited at
`lab_prepare.py:119-122` and `lab_load.py:91-92`, both verified) — but the anchors themselves should
be replaced with real line numbers or removed before root treats them as citations.

---

## Finding 4 (minor completeness gap — 22:20 item (3)'s seven named prerequisites are quoted but not cross-walked)

**Where:** DESIGN_PROPOSAL.md §1 quotes root's 22:20 review in full:

> "...the complete paired AB/BA assignment, enrollment-indexed partial bounds, simultaneous error
> allocation, scientific guardrails, stopping/estimand rules, serving/usage provenance and freeze
> inputs still need explicit root review."

**What I found:** unlike OD1/OD2/OD14/OD16/OD18/OD19, which each get their own row in §6's
"what stays blocked" table with a citation, none of these seven named items (paired AB/BA
assignment, enrollment-indexed partial bounds, simultaneous error allocation, scientific
guardrails, stopping/estimand rules, serving/usage provenance, freeze inputs) gets an individual
row. They appear only inside the block quote in §1 and once more, folded into a single generic row
("Any actual stage-3 §5.8-item-3 240-episode calibration run" → "Named server/capacity evidence and
freeze inputs required first").

**Why it matters:** this is lower severity because these seven items look like pre-existing,
already-implemented protocol/design elements awaiting a root sign-off pass, not new drivers the
proposal is scoped to build (the proposal's own §1 "Synthesis of the ask" frames the ask as building
*missing executable drivers*, and these seven are not obviously drivers). Still, root cannot tell
from §6 alone which of the seven the proposal considers already built-and-pending-review versus
untouched, and the document applies exactly this kind of explicit per-item tracking everywhere
else. Recommend either an explicit "not this proposal's scope, tracked here only for
completeness" row per item, or a one-line disclaimer up front in §6.

---

## Spot checks that held (citations verified accurate, included for calibration)

Read directly at `c62b59b` in `wt-eb1` unless noted:

- `lab_server.py:403-479` — `start()` docstring and `mode='capture'` behavior (stage-1 capture path,
  no golden required) match the proposal's description exactly.
- `lab_client.py:399-410` — `LlamaClient.__init__` requires `golden: GoldenReceipt` as claimed.
- `experiments/live_ab/lab_replay.py` confirmed absent at `c62b59b` (`git cat-file -e` fails); only
  unrelated `experiments/run_replay.py` exists, a different experiment stream.
- `ref:session60-repair-replay` (`72230b8`): `lab_replay.py` confirmed 983 lines; merge-base with
  `c62b59b` confirmed `b049307`; `lab_load.py` diff between the two refs confirmed empty (byte
  identical), matching the proposal's "already merged, not reusable as new work" claim.
- `lab_orchestrator.py:706-820` — `phase_resolution_verdict` signature, docstring citing "root 20:40
  item 3," and the four-branch FAIL structure match; `lab_orchestrator.py:4818-4836` confirms the
  verdict gates `invocation_ended` / forces `status='aborted'` on non-PASS, matching the proposal.
- `lab_common.py:509-547,920` — `write_json_atomic` / `WriteOnceViolation` behavior (raises only on
  differing bytes at an existing path; idempotent on identical bytes; atomic temp-then-rename)
  matches the proposal's write-once receipt design exactly; no rewrite-with-different-bytes path
  exists.
- `lab_data.py:748` — `AttemptLedger` class and docstring match the proposal's citation.
- `lab_eventlog.py:166-167` — `E_PHASE` closed vocabulary confirmed to lack any
  `timing_pilot`/`rehearsal` value, matching the proposal's OD row in §6.
- `lab_prepare.py:119-122`, `lab_load.py:91-95` — both confirmed to state, in the code's own
  docstrings, that the stage-3 two-stream (`stream:false`) driver "does not exist yet," matching
  the proposal verbatim.
- `lab_injected_decision.py:98,101,108` — `arm()`'s refusal without `rehearsal_only` and
  `inject_decision()`'s signature match exactly.
- `config.json:93,100,163,209-221,225` — `design_seed_base`, `seed_rule`, `metrics_timeout_s`/
  `metrics_tries`, the four `oodp/1..4` conformance prompts plus `calibration_plan`/
  `side_by_side_compression_C`, and `server_supervision` all match the proposal's quoted values and
  line ranges (the `oodp` block citation `209-217` is off by one line at the tail — `oodp/4` actually
  starts at line 217, ends 218 — immaterial).
- `lab_design.py:70`, `lab_coin.py:131-145`, `lab_common.py:652-656` — the three distinct seed
  mechanisms (trial arrival-order seed, worker/model-call `seed_rule`, harness-pin glob) all match
  the proposal's careful three-way distinction in §4.
- `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:1899-1904` — OD11's exact "adopted
  only on explicit root acceptance" wording confirmed present at the cited lines.

---

## What I did not do (declared, not silently skipped)

- Did not re-sweep the full `reviews/` directory (200+ files) for a ruling on OD1/OD2/OD14/OD16
  beyond the three named authority docs — same limitation the proposal itself already discloses in
  §8, and I have no new evidence either way.
- Did not diff `tests_lab_replay.py`/`tests_lab_schedules.py`/`tests_lab_load_resolution.py`
  against main's controls tree — out of scope for a completeness critic and already flagged as
  unverified by `map_held_branch.md` and carried into the proposal's §7.
- No test run, no build, no model, no server, no network beyond the one `git fetch` already done
  before this pass, per the hard rules.
