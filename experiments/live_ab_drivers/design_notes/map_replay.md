# Map: protocol §11.5 (extended CPU replay) and its seed — REQUIRES vs EXISTS

Read-only mapping. Worktree read: `wt-eb1` at HEAD `c62b59b71cf6caa468069575b6c488ae2995330d`
(branch `session60/repair-eb1`), fetched clean, nothing modified. Accepted base tag
`session60-eb1-eb5-subset-v1` = `c7750a3`. Authority docs read on `origin/main`. All citations are
`path:line at c62b59b` unless a `ref:` prefix names a different commit/branch.

## 1. What the frozen protocol REQUIRES (§11.5, `experiments/live_ab/design/protocol_FINAL.md`)

- Heading and status: `protocol_FINAL.md:2350` marks "The extended replay (11.5)" **mandatory before
  the freeze, no fallback (revision 1, C12); it cannot change any rule parameter**. Heading itself at
  `protocol_FINAL.md:2440`.
- Purpose (`protocol_FINAL.md:2442-2447`): a model-dependent check of the crossing-prefix distribution
  and the A/A rate for the **frozen** rule on the **realized** `N_P` and roster. It cannot change any
  rule parameter; a discouraging result does not license a parameter change (would need a new protocol
  version and new audit).
- Item 1, tasks/strata/arrival order/seed (`protocol_FINAL.md:2449-2450`): "Tasks and strata as in the
  realized `roster.json`; arrival order drawn **exactly as in 3.4** with a **fresh seed per replicate**;
  whole-pair interleaving; fresh fair coin per pair."
  - §3.4 itself (`protocol_FINAL.md:696-719`, code block `protocol_FINAL.md:701-707`) is the algorithm
    the replay must reuse: `rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([60260919, e])))`,
    stratified permutation within S1/S2, pairs formed inside a stratum, then whole-pair interleaving.
    For the **live trial** `e` is the trial number (T1=1..T4=4) and `60260919` is the frozen
    `design_seed_base` — one arrival order per trial, not per replicate.
  - §11.5 item 1 explicitly does NOT reuse that single frozen `(design_seed_base, e)` seed for every
    replicate — it requires a fresh seed per replicate while reusing the same generation algorithm.
    The protocol text itself does not spell out the fresh-seed's numeric provenance (no formula in
    §11.5 item 1); item 7 below is the only other seed-related protocol text.
- Item 2, success model (`protocol_FINAL.md:2451-2454`): S1 task — probability `w` reuse the pilot
  outcome for that task/arm, else fresh Bernoulli at the arm's pilot stratum rate; S2 task — Bernoulli
  at cell rate `q`; candidate probability gets shift `s`, clipped to [0,1].
- Item 3, cost model (`protocol_FINAL.md:2455-2457`): for a both-succeed pair, resample
  `(latency_candidate, latency_incumbent)` **jointly** from pilot both-succeed tasks (preserves
  within-task correlation), then the frozen cost-tier rule at `relative_tolerance = 0.05`.
- Item 4, rule (`protocol_FINAL.md:2458-2461`): exact frozen §8.1-8.4 rule, `alpha_gate=0.00625`,
  `rho=100.`, `V_n=n`, `delta=0.03`, `n_min=100`, horizon `N_P`, first crossing, no retention, no
  intersection.
- Item 5, cells, exhaustive (`protocol_FINAL.md:2462-2463`): `w in {0.3,0.5,0.7,1.0} x q in
  {0.25,0.45,0.60} x s in {0,-0.02,-0.03} x N_P in {295,495,realized} x trial in {T1,T2,T3,T4}`;
  4,000 replicates per cell, 20,000 for T4. (This is 4x3x3x3x4 = 432 cells.)
- Item 6, output, exhaustive (`protocol_FINAL.md:2464-2466`): every cell's DEPLOY/HARM_RETAIN/ABSTAIN
  counts and rates with pointwise Wilson 95% intervals, plus crossing-prefix Q1/median/Q3. No row may
  be omitted for brevity.
- Item 7, provenance (`protocol_FINAL.md:2467-2469`): **"script, seed and output SHA-256 enter the
  freeze bundle; the table is deposited beside this protocol and is referenced, not summarised
  selectively."** This is the only place the protocol names a singular "seed" artifact (as opposed to
  "fresh seed per replicate") — i.e. whatever top-level seed specification the driver uses must itself
  be hashed/committed into the freeze bundle, not just each replicate's derived seed.
- Limits section (`protocol_FINAL.md:2470-2474`): the replay has one pilot run per task/arm on a
  **different serving stack**; `w` is not calibrated on anything; it does not model success rates,
  token counts, speed under the real GGUF stack, GPU contention, the execution lock, S2 difficulty, or
  thermal drift. Simulated crossing prefixes are expectations, never reported as measured quantities.
- Wall-clock/host budget (`protocol_FINAL.md:2475-2477`): planning numbers only (6-11 GPU hours for the
  *program*, not this CPU replay, which is explicitly CPU-only and "runs no model" per the
  cross-reference at `protocol_FINAL.md:2995,2997,3367`).
- Cross-references confirming mandatory/blocking status: `protocol_FINAL.md:2944` (extended replay
  listed among items the freeze depends on), `:2995` ("the **exhaustive** output of the extended
  replay (11.5), with script, seed and output hash" is freeze-bundle item 12), `:2997` ("every cell of
  11.5 is deposited; no row is omitted for brevity" — freeze-bundle item 14), `:3367` (evidence-map
  row: "the extended-replay table (script, seed, output hash) | 11.5 | 11.5"), `:3767` (finding N10:
  "the **decisive** planning object is now the analytic reachability table (11.3) ... The extended
  replay is specified in full (11.5: outcome model, cost resampling, cells, replicate counts, Wilson
  intervals, exhaustive output, script/seed/output hash) and is **mandatory before the freeze**, with
  the explicit rule that it cannot change any parameter").
- `experiments/live_ab/design/ARCHITECTURE_FINAL.md`: no "11.5" or "extended replay" or "CPU replay"
  hits found (`grep -n "11\.5\|CPU replay\|cpu_replay\|extended CPU"` returned nothing) — **not found**
  in the architecture document; the requirement lives only in the protocol.

## 2. Root's authority docs (on `origin/main`) that name §11.5 as outstanding

- `reviews/prerun_bundle_go_nogo_20260923_2040.md` (item 2, ranked root decisions): "EB2–EB4: complete
  only the missing executable drivers for stages 1, 2, 4–6, the stage-3 two-stream loaded sweep, **and
  the §11.5 extended CPU replay/seed**. Show each driver consumes the frozen schedule and writes
  immutable attempts, failures, missingness, usage and actual timestamps. Do not run the loaded stages
  or repeat the accepted CPU grid while implementing them."
- `reviews/restart_cap_estimand_ruling_20260923_2114.md` (item 3): PROPOSED scaffolds are allowed
  ("may be built model-free as parameterized scaffolds") but "no stage executes and no freeze is
  accepted until root explicitly resolves the named ODs ... **the §11.5 outcome model** ... Rehearsal
  evidence belongs to `_prefreeze` per §5.8/§12.1 and must remain outside trial inference."
- `reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md`: accepts only the EB1+EB5 model-free
  tagged subset at `c7750a3`; does not mention §11.5/replay by name; says next work is "Session60 may
  then advance its already assigned **EB2–EB4 model-free drivers** and EB5 loaded-phase preparation,
  with exact code/config/seed pins and incremental immutable completed-shard receipts" and that "**No
  loaded/design/trial episode is approved**." §11.5 falls under EB2-EB4 per the 20:40 review's item 2,
  and is not itself addressed or accepted in this later review.

## 3. What EXISTS at `c62b59b` (the read worktree, current accepted line)

- **No §11.5 driver file exists at `c62b59b`.** `git show c62b59b:experiments/live_ab/lab_replay.py`
  fails ("not found"). `experiments/live_ab/` at `c62b59b` has no file matching `*replay*` — listing at
  `c62b59b:experiments/live_ab/` confirms only `dryrun_live_ab.py`, `build_live_ab_results.py`,
  `lab_*.py` (common/eventlog/verify_log/reference_rule/data/design/coin/monitor/enclosure/client/
  server/mock_server/worker/orchestrator/anchor/hostcheck/lockfixture/injected_decision/containment/
  serving_manifest/load/combined_fixture), plus tests and `design/`.
- `experiments/live_ab/design/power_sim.py` (R4's simulator) exists but is explicitly **superseded**
  for decision-rule cells per `protocol_FINAL.md:2346` ("R4's replay simulation ... superseded in its
  decision-rule cells (it used v1/v2 rules, levels and margins)") — it is not, and is not claimed to
  be, the §11.5 driver. Its own header (`design/power_sim.py:1-20`) self-describes as the old
  `pair_coin`/`arrival_coin` v1/v2 comparison, not the frozen §11.5 spec.
- `experiments/live_ab/IMPLEMENTATION_STATUS.md` (dated 2026-09-19, before §11.5 was even finalized in
  the protocol revision referenced by the 20:40 review) lists only the G1-G5 modules above; no §11.5
  module, no replay grid, no Wilson-interval output is mentioned anywhere in it.
- Whole-repo search at `c62b59b` for `wilson|4000 replicates|4,000 replicates|replicates per cell|
  extended.replay|replay_11_5|cpu_replay` across `*.py` under the tree returns **no hits** outside
  design/review markdown prose — i.e. no executable §11.5 code anywhere reachable from this HEAD.
  `find experiments -iname "*replay*"` at `c62b59b` finds only pre-existing unrelated files
  `experiments/run_replay.py` and `experiments/test_replay_sampling.py` (outside `live_ab`; not
  inspected further as out of the stated AREA, but their names are a false-positive match, not a
  §11.5 driver — neither is under `experiments/live_ab/`).

### A candidate driver DOES exist, but on a different, non-ancestor branch — not part of the accepted line

- `git log --oneline --all` on this worktree surfaces two commits titled "lab_replay": `11fd781`
  ("lab_replay: protocol 11.5 extended CPU replay and its seed (root 20:40 item 2, plan stage 8)") and
  `90edaa8` ("lab_replay: control the 11.5 outcome model, check the grid against the protocol, T4-only
  null rows, resolvable rulings"). `git branch -a --contains 90edaa8` shows only
  `session60/repair-replay` / `remotes/origin/session60/repair-replay` — **not** `session60/repair-eb1`.
  `git merge-base --is-ancestor 90edaa8 c62b59b` → **NO**. `git merge-base c62b59b
  origin/session60/repair-replay` → `b049307` (the same commit the stale older map was written at),
  confirming the two branches diverged there and `repair-eb1` never picked up the replay work.
  Branch tip is `72230b8` ("EB5: a loaded sweep is accepted only on tracked, observed load...").
  This branch/file is **not** part of the accepted tag `session60-eb1-eb5-subset-v1` (`c7750a3`), not
  reviewed in any of the three authority docs on `origin/main` read above, and not visible from the
  `wt-eb1` worktree's checked-out files — cited below as `ref:session60-repair-replay:<path>:<line>`.

  At `ref:session60-repair-replay` (`experiments/live_ab/lab_replay.py`, 983 lines):
  - Docstring (`lab_replay.py:21`): confirms it reproduces `lab_design.arrival_order` when seeded with
    `SeedSequence([design_seed_base, trial_no])` — i.e. explicitly reuses the §3.4 algorithm as §11.5
    item 1 requires.
  - **Seed rule, stated explicitly** (`lab_replay.py:55-63`, restated at `:184-187` as
    `REPLAY_STREAM_TAG: int = 1105` and a format-string docstring, and implemented at
    `lab_replay.py:325-332` in `replicate_generator(design_seed_base, ordinal, replicate)`):
    replicate `r` (1-based) of grid cell `c` (1..432, cell order = `enumerate_cells()` order) draws
    from `numpy.random.Generator(PCG64(SeedSequence([design_seed_base, 1105, c, r])))`. `1105` is a
    fixed stream tag "naming protocol 11.5", chosen as a 4th/distinguishing word so that no replay seed
    can collide with a live-trial arrival-order seed `SeedSequence([design_seed_base, e])`
    (`e` in 1..4) — numpy pads short entropy with zeros, so `SeedSequence([a,b]) ==
    SeedSequence([a,b,0])`, and `1105 != 0` and `1105 != e` for any trial guards against that specific
    collision. `design_seed_base` itself is read from `cfg['design_seed_base']` at runtime
    (`lab_replay.py:861-863`), i.e. it is the same frozen `60260919` constant from
    `experiments/live_ab/config.json:93`, not a new value.
  - Grid enumeration is checked against a literal restatement of protocol item 5, not against itself:
    `PROTOCOL_11_5_ITEM_5` (`lab_replay.py:175`), `GRID_CELLS: int = 432` (`lab_replay.py:169`),
    `GRID_REPLICATES: int = 3_456_000` (`lab_replay.py:170`, literal, "3 x 108 x 4,000 + 108 x 20,000"),
    checked in `check_grid` (`lab_replay.py:284-295`).
  - **Two protocol gaps are left as explicit, unresolved, root-flagged PROPOSED items, not defaults**:
    (1) the outcome model for T3's pilot-less candidate and the T3/T4 cost pair, which "protocol 11.5
    items 2-3 do not define" (`lab_replay.py:68-109`, `PROPOSED_OPEN_MODEL` dict at `:203-209`,
    enforced/refused without an explicit `open_model` argument by `check_open_model` at
    `:418-439`); (2) a fixed horizon (295/495) that exceeds the realized roster's pair count is
    deposited with `status: NOT_SIMULABLE` and a reason rather than bootstrapped
    (`lab_replay.py:107-109`, `:229-232`, enforced in `run_cell` at `:737-753`).
  - **The real grid was never run** on this branch either: the commit message for `11fd781` states "The
    real grid was NOT run," and `git show --stat origin/session60/repair-replay -- results/` and
    `git ls-tree -r --name-only origin/session60/repair-replay -- results/live_ab | grep -i replay`
    both return **no output** — no replay result/manifest artifact exists under `results/live_ab` on
    that branch. Only tests exist: `experiments/live_ab_controls/tests_lab_replay.py` (named in the
    `11fd781`/`90edaa8` commit messages; not separately re-read here since it is out of the AREA and
    the repo's controls listing at `c62b59b` — this task's read target — does not include it, being on
    the other branch only).
  - Manifest/provenance fields intended for the freeze bundle (`lab_replay.py:895` area): `'seed':
    {'design_seed_base': design_seed_base, 'stream_tag': REPLAY_STREAM_TAG, ...}` — i.e. the seed
    record that would satisfy protocol item 7 ("script, seed and output SHA-256 enter the freeze
    bundle") is drafted but has never been produced by an actual run (no output file exists to hash).

## 4. Seed provenance summary — REQUIRES vs EXISTS

| | requires (protocol) | exists at `c62b59b` | exists on `ref:session60-repair-replay` (unmerged) |
|---|---|---|---|
| Arrival-order algorithm to reuse | §3.4 exactly (`protocol_FINAL.md:696-719`) | implemented for the **live trial** in `experiments/live_ab/lab_design.py:61-138` (`_generate` at `:61`, `numpy.random.SeedSequence([int(design_seed_base), TRIAL_NO[trial]])` at `:70`) — this is the live-trial path, not a replay driver | reused via `replicate_generator` per commit `11fd781` docstring (`lab_replay.py:21`) |
| §11.5 fresh-seed-per-replicate formula | required by item 1 (`protocol_FINAL.md:2449`); no numeric formula given in the protocol text itself | **not found** — no code implements it | `SeedSequence([design_seed_base, 1105, c, r])` (`lab_replay.py:55-63,184-187,325-332`) |
| `design_seed_base` value | frozen constant, reused (implied by "exactly as in 3.4") | `60260919` at `experiments/live_ab/config.json:93` | same value, read from config at `lab_replay.py:861-863` |
| Script+seed+output hash into freeze bundle | required, item 7 (`protocol_FINAL.md:2467-2469`); freeze-bundle item 12/14 (`protocol_FINAL.md:2995,2997`) | **not found** — no output, no manifest, nothing to hash | manifest fields drafted (`lab_replay.py:895` area, `'seed': {...}`) but never populated by a real run — no output artifact exists in `results/` on either branch |
| Worker/model-call seed (`seed_rule`, `config.json:100`) | a *different* mechanism, for live model-serving requests (`os.urandom(4)` masked, low bit = worker index) — not the §11.5 replicate seed | exists and is implemented in `lab_coin.py:132-145` | not relevant to §11.5; noted only to avoid confusing it with the replay seed |

## 5. Re-verification of the older stale map (`an older owner note written at b049307 (not committed)`, written at `b049307`)

- It stated (its line 112): "**Plan:** 3,456,000 replicates; needs stage 3 first; 86,400 s cap. **Code
  and seed are ABSENT** (S:2670-2721, :779-786)." This was accurate **at `b049307`** (the merge-base of
  both branches) but is now **stale**: code and a seed rule were subsequently written in commits
  `11fd781`/`90edaa8` on `session60/repair-replay`. It remains true, however, that **no §11.5 code or
  seed reaches `c62b59b`** (the branch this task was asked to read) — the old note's conclusion is
  still correct for the accepted/read line, just not for the repo as a whole.
  - Its line 214 guess ("It can sit outside, like `design/power_sim.py`, pinned through a planning
    manifest ... Put it inside if root wants it recomputed at preflight") and line 229's "seed pinned
    pre-outcome" as an open question are superseded by the concrete, stated seed rule in `11fd781`
    (`lab_replay.py:55-63`) — the seed is no longer an open question on that branch, though it has not
    been reviewed or accepted by root anywhere in the three authority docs read on `origin/main`.
  - Its stage/line mapping "stage 8 = §11.5 (S:1763, :1866, :1946, :2164, :2274, :2403, :2671)" uses a
    different line numbering than the current `protocol_FINAL.md` at `c62b59b` (§11.5 is at
    `2440-2477` here); not re-verified line-by-line since the old map's own line anchors do not match
    this checkout's file and the content itself (mandatory-before-freeze, exhaustive cells/output,
    script+seed+hash provenance) is corroborated directly against `c62b59b`'s `protocol_FINAL.md` above.

## 6. Bottom line for this AREA

- The frozen protocol's §11.5 requirement (algorithm reuse from §3.4, per-replicate fresh seeding,
  exhaustive 432-cell/3,456,000-replicate output with Wilson intervals, and script/seed/output-hash
  provenance into the freeze bundle) is fully specified in `experiments/live_ab/design/protocol_FINAL.md:2440-2477`
  and named as an outstanding EB2-EB4 driver in root's `reviews/prerun_bundle_go_nogo_20260923_2040.md`
  item 2.
- **At `c62b59b` (the branch this task reads), no §11.5 driver, seed implementation, or output exists.**
  Say "not found" for any claim that it does.
- A candidate implementation with a concrete, documented seed rule exists on the separate,
  never-merged branch `session60/repair-replay` (commits `11fd781`, `90edaa8`; tip `72230b8`), diverged
  from `c62b59b` at common ancestor `b049307`. It has never produced an output artifact (grid not run),
  leaves two protocol gaps as explicit root-flagged `PROPOSED`/`NOT_SIMULABLE` items rather than
  defaults, and has not been reviewed or accepted in any of the three `origin/main` authority documents
  read for this task. It should not be treated as part of the accepted EB1+EB5 subset or as satisfying
  root's item-2 request until root reviews it and it is merged/pinned into the harness line this task
  was asked to read.
