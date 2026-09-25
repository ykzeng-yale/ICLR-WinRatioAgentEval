# Stage-2 driver — read-only map at c62b59b (worktree wt-eb1, branch session60/repair-eb1)

Tag `session60-eb1-eb5-subset-v1` = `c7750a3` is the accepted base. `c62b59b` is one doc-only commit on top
(`git diff --stat c7750a3 c62b59b`: only `experiments/live_ab_controls/REPRODUCE_EB1_EB5_SUBSET.md` and
`results/SESSION60_RESULTS_INDEX.md` changed — the two corrections named in
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`). So every finding below about stage 2 also
describes the accepted-tag state: nothing production-relevant moved between the two.

## What "stage 2" is (protocol identity)

`experiments/live_ab/design/protocol_FINAL.md:1357-1361` (§5.8 item 2):

> 2. **Counter-semantics test on the production path** (finding N14): start a 1,024-token generation over a
> **non-streamed** POST with a short client timeout, let the client time out, scrape `/metrics` before and after,
> and record whether and how many prompt and predicted tokens of the abandoned task are counted. A streamed probe
> is run **in addition**, only to learn how many tokens had been generated at the cut. The non-streamed result
> fixes the accounting wording of 13.1.

§5.8's chain framing (`protocol_FINAL.md:1328-1335`): stage 2 belongs to the `_prefreeze` chain, phase vocabulary
`{SMOKE, TIMING_PILOT, SERVER_SMOKE, REHEARSAL}` (protocol calls this a "counter-semantics test," not literally
"TIMING_PILOT" — that phase word is used loosely by the go/no-go review's stage numbering; the protocol text itself
does not name a phase per item). Success outcomes of this run are never used for a design choice
(`protocol_FINAL.md:1334`); only durations, memory, receipt equality, template facts and code-block extractability
are used.

The go/no-go review's numbering that calls this "stage 2" is
`reviews/prerun_bundle_go_nogo_20260923_2040.md` item 2 ("EB2–EB4: complete only the missing executable drivers
for stages 1, 2, 4–6, the stage-3 two-stream loaded sweep, and the §11.5 extended CPU replay/seed"). This is the
authority naming "stage 2" as a still-missing driver, confirmed unresolved by
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md` ("Session60 may then advance its already assigned
EB2–EB4 model-free drivers... The loaded phase still needs named server/capacity evidence...").

## What the frozen protocol REQUIRES (stage 2 specifically)

- One non-streamed 1,024-token POST per server, client-side short timeout, client abandons; `/metrics` scraped
  immediately before and after (`protocol_FINAL.md:1357-1361`, `:2821-2845` §13.1).
- One streamed probe in addition, same cut point, only to learn tokens generated at the cut
  (`protocol_FINAL.md:1358-1359`).
- The **non-streamed** result (not the streamed one) fixes the §13.1 accounting wording — i.e. whether abandoned
  generations are counted server-side (`protocol_FINAL.md:1361`, and the §13.1 text at `:2864-2868`: "What a
  request without a response cost is therefore bounded, not measured... by the counter delta of its window if the
  pre-freeze counter test (5.8 item 2, run on the non-streamed production path) shows that abandoned generations
  are counted... If the test shows that abandoned tokens are not counted, claim 6 of 1.4 reads..." — the wording of
  a manuscript claim is conditioned on this stage's own result).
- Every `/metrics` scrape: 5 s timeout, at most 3 tries (`protocol_FINAL.md:2843`, `config.json:163` —
  `"metrics_timeout_s": 5, "metrics_tries": 3"`, confirmed present verbatim at c62b59b).
- No success/conformance/latency outcome may be used to choose or gate anything about this stage
  (`protocol_FINAL.md:1334`, `:1350`).

## The owner's plan sheet for stage 2 (not code, not authorized)

`results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:1864-1943` (id 2, "counter-semantics test on the
production path"):
- `status`: `"NOT AUTHORIZED; runs in the stage-1 server session (same blockers as stage 1)"`.
- 4 logical calls (2 per server: one non-streamed abandon, one streamed abandon), 8 non-generation GETs (one
  `/metrics` before/after each), never retried by design (a retry after a deliberate timeout would confound the
  counter delta) — `:1867-1892`.
- `short_client_timeout_s`: value 10, `status: "PENDING_ROOT"`, `open_decision: "OD11"` (`:1899-1904`).
- Wall budget cap 1200 s (`:1917-1921`). Reuses stage 1's two resident servers, 0 new starts/restarts
  (`:1908-1916`).
- Stop rules: a scrape failing after 3 tries leaves the probe unreconciled and stops the stage; abandoned work
  stays in the all-attempt ledger (`:1932-1936`).

**OD11 status, re-verified now:** `results/live_ab/FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:4402-4409` records
OD11 ("Value of the 'short client timeout'... default 10 s... adopted only on explicit root acceptance of this
plan; root silence adopts nothing"). I grepped every review file under `reviews/` on `origin/main` (including all
2026-09-24 and 2026-09-25 ones) for `OD11` — **no hit**. OD11 is still unresolved; no root ruling has adopted the
10 s default or any other value. No newer plan draft exists (`ls results/live_ab/ | grep -i PLAN` shows only
`FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json` and the older `PREFREEZE_EXECUTION_PLAN_20260921_1910.json`).

## What the code DOES today (re-verified at c62b59b, not from the stale map)

Building blocks stage 2 would use all exist, but purely as generic primitives — no stage-2-specific caller wires
them together:

- `parse_metrics` at `experiments/live_ab/lab_server.py:349`, `metrics(base_url, *, timeout=5.0, tries=3)` at
  `lab_server.py:367` — matches the config's `metrics_timeout_s`/`metrics_tries` defaults but is a generic scrape
  helper, not a stage-2 driver. (Old stale map at
  `an older owner note written at b049307 (not committed)` cited these at `lab_server.py:234-279`; line numbers
  have shifted to `:349`/`:367` but the functions and signatures are unchanged — re-verified, not stale in
  substance.)
- `classify_stream_chunk` at `experiments/live_ab/lab_load.py:384` and `class StreamingHttpLoad` at
  `lab_load.py:624` (stale map cited `:243`/`:469`; shifted but present) — these classify/count **stream events**,
  not tokens (no token-count derivation here), and belong to the diagnostic client-stream tooling, not a
  non-streamed-abandon probe.
- `lab_mock_server.py:355`: `if not st.scenario.get('count_cancelled_tokens'):` — the mock server can simulate
  both counting and non-counting behavior for cancelled/abandoned generations, which is the fixture a stage-2
  control would exercise (mock `count_cancelled_tokens` true vs false to get both accounting wordings
  model-free). Confirmed present, unchanged in substance from the stale map's `lab_mock_server.py:350` citation.
- No function named anything like `probe_abandoned`, `probe_streamed`, or `derive_wording` exists anywhere in the
  repo (`grep -rln "probe_abandoned\|probe_streamed\|derive_wording\|stage2\|stage_2\|lab_prefreeze" experiments/`
  → no hits).
- No `lab_prefreeze.py` (or any shared prefreeze-stage runner module) exists. `PREFREEZE_CHAIN_ID = '_prefreeze'`
  is defined at `experiments/live_ab/lab_common.py:35`, but `grep -rln "PREFREEZE_CHAIN_ID" experiments/live_ab/*.py`
  shows it is referenced only by `lab_common.py` itself and by two test files
  (`tests_lab_design.py`, `tests_lab_isolation.py`) — **no non-test module opens or writes the `_prefreeze`
  chain**. This matches the stale map's claim and I re-confirmed it is still true at c62b59b.
- `E_PHASE` at `experiments/live_ab/lab_eventlog.py:166-167`:
  `E_PHASE = _E('prefreeze', 'smoke', 'server_smoke', 'randomizing', 'draining', 'post_decision', 'paused', 'ended', 'aborted')`
  — there is no `timing_pilot` or `rehearsal` enum value. So even if a stage-2 driver were written today, the
  closed event schema has no phase value it could legally tag its events with, other than the generic
  `'prefreeze'`/`'smoke'`/`'server_smoke'` ones. This is a harness-level gap, re-confirmed unchanged from the
  stale map.
- Harness pin (`experiments/live_ab/lab_common.py:653`: `names = sorted(p.name for p in HERE.glob('*.py'))`) is
  non-recursive over `experiments/live_ab/*.py` — any new stage-2 driver file placed there is automatically pinned
  at next preflight; placing it elsewhere is not automatically pinned.
- `tests_lab_isolation.py:36-67` `MATRIX` (the import-isolation allowlist) has no entry for a stage-2/prefreeze
  driver module (no `lab_prepare`, `lab_load`, `lab_lifecycle`, or `lab_prefreeze` key) — re-confirmed unchanged
  from the stale map; adding such a module requires a MATRIX entry too.

## What is MISSING for stage 2 (driver code)

1. A stage-2 driver module/function that: reuses the stage-1 servers (no new start), issues the non-streamed
   1,024-token POST with a short client-side timeout, aborts client-side at that timeout, scrapes `/metrics`
   before/after via the existing `metrics()` helper, then issues the streamed probe and scrapes again, and records
   whether/how many tokens were counted for the abandoned request. **Not found anywhere in the tree.**
2. The write-ahead/ledger wiring so every one of the 4 logical calls is durably intent-logged before dispatch and
   terminally resolved after (the `run_smoke`/`AttemptLedger` pattern the stale map described as reusable
   primitives — `lab_data.py`'s `AttemptLedger`, `lab_common.py`'s `write_json_atomic`/`append_line_durable` — still
   exist as generic primitives but nothing calls them for this probe).
3. A `_prefreeze`-chain phase value (or explicit root ruling that stage 2 is tagged under the existing `'smoke'`/
   `'server_smoke'` enum values instead of a new one) — currently undecided; **needs a root/harness decision**,
   not just code.
4. The §13.1 wording derivation itself: a small function/report step that reads the counter-delta result and
   emits the correct claim-6 wording branch (`protocol_FINAL.md:2864-2868`) — not present.
5. **OD11 resolution** (the short client timeout value) — a pure protocol/plan open decision, not a coding gap,
   but it blocks writing the driver's timeout constant with authority; still unresolved as of this read.

## MODEL-FREE buildable pieces (can proceed without root, without a server, without a model)

- The driver's control-flow skeleton and its ledger/intent-logging wiring, tested end-to-end against
  `lab_mock_server.py` with `count_cancelled_tokens` toggled true/false (`lab_mock_server.py:355`) to exercise both
  the "abandoned tokens are counted" and "abandoned tokens are not counted" branches and confirm both produce the
  correct §13.1 wording deterministically — this needs no live model server, no network beyond what mock-serving
  already uses in tests, and no root decision beyond a placeholder timeout constant (parameterizable, swapped once
  OD11 resolves).
- A scrape-retry/failure-path control: force the mock's `/metrics` to fail 3 times and confirm the probe is marked
  unreconciled and the stage stops, per the plan's stop rule (`FINITE_COSTED_PLAN_DRAFT_v2r3_20260923.json:1932-
  1933`).
- Adding the MATRIX entry and confirming the harness pin glob picks up the new file (pure static/test-time check,
  no execution against a real server).

## Needs a ROOT / model / server / capacity decision before this can run for real

- **OD11** (short client timeout value) — open, unresolved, cited above.
- Whether stage 2 needs its own `_prefreeze` phase enum value or reuses an existing one — a schema decision, not
  purely an implementation one, since `E_PHASE` is described elsewhere in the protocol as closed/frozen.
- Actually running stage 2 requires the stage-1 servers already up (real llama-server), which per
  `reviews/prerun_bundle_go_nogo_20260923_2040.md` item 1/EB1 is not yet a trustworthy production path (EB1 is the
  gating item, separately tracked, not itself part of stage 2 but a hard prerequisite to running it for real). No
  loaded/model-serving run is authorized regardless (root: "No loaded/design/trial episode is approved",
  `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`).
- Named server/capacity evidence and a real host window — required before *any* loaded episode
  (`eb1_eb5_final_subset_bounded_review_20260925_2220.md`, ranked item 3), which stage 2's real (non-mock) run
  would be.

## Citation notes on the stale map

The older read-only map at `<session work area>/repair/an older owner note (not committed)` (written at
`b049307`) gave line numbers for `lab_server.py`, `lab_load.py`, `lab_mock_server.py` that no longer match
c62b59b exactly (files have grown/shifted). I re-verified every citation I reused above against c62b59b directly
and give the current line numbers; the substance (which functions exist, what they do, what's missing) is
unchanged. I did not find any new stage-2-specific code, tests, or driver file added between `b049307` and
`c62b59b` — `grep -rln "probe_abandoned\|probe_streamed\|derive_wording\|stage2\|stage_2\|lab_prefreeze"
experiments/` returns nothing, and the `c7750a3..c62b59b` diff is doc-only (2 files). So the stale map's stage-2
assessment ("Missing: the abandon-probe driver, the wait for slot release, and the wording derivation") still
holds at HEAD.
