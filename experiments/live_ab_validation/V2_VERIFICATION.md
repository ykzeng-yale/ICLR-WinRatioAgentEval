# V2_VERIFICATION: the `v2` amendment, checked by running it

This file is a **verification pass over someone else's delivery**, not a second delivery and **not independent
verification**. It re-executes the author's own suites on the author's own working tree, adds mutation tests and
cross-implementation comparisons that the delivery does not contain, and reports true output. Where a number here
comes from the author's script, it is labelled as such.

| field | value |
|---|---|
| interpreter | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, **CPython 3.12.13**, numpy **2.4.1**, scipy **1.17.0** |
| data prerequisites | the deposited `v1` grid under `results/live_ab_validation/` (present, 15 files); `experiments/live_ab_validation/pinned/`; `src/winstats.py`; the `#11` tree at `experiments/live_ab/`. **No** benchmark cache, model, API, network or new dependency was used |
| tree under test | branch `session60/live-ab-validation`, `HEAD = db930d7`, with `REPORT.md`, `tests_validation.py`, `vgen.py`, `vrun.py` modified and `PROTOCOL_V2.md`, `RESOURCE_CHECK.md`, `vresource_check.py` untracked |
| written by this pass | **this file only.** No `v1` result, no protocol, no `cells.json` entry, no Git state was touched; no state-changing Git command was run |
| what was NOT run | the `v2` grid. Only deterministic fixtures, witnesses, mutation tests and the authorised balanced 20-program resource check |

**Verdict: AMBER, leaning green.** The four checks the root will care about most - the witness, `v1` preservation,
prefix-versus-elapsed, and rule drift - all **close**, and they close under adversarial tests rather than by
reading the code. What does **not** close is the **resource check**: it costs an implementation that is not the
delivered runner, its headline sign is wrong for the delivered runner, and it still asserts in its own text that
the runner "has not been written". Details in section 8.

---

## 1. The table

| # | claim | command | true output | verdict |
|---|---|---|---|---|
| 1a | the witness regression PASSES against `v2` | `python -m unittest tests_validation.TestMissedCrossingWitness -v` | `Ran 10 tests in 0.016s / OK` | **CLOSED** |
| 1b | the witness regression FAILS against the `v1` schedule | scratch mutation harness: `vrun.build_series_v2` and `build_series_for` monkeypatched to return `build_series` (the `v1` look set), then the same class run | `RAN 10 FAILURES 5 ERRORS 1` - 6 of 10 fail | **CLOSED** |
| 1c | the witness numbers are the root's, to every digit | `python vrun.py --witness` | tick **1,010**, index **600**, `L_h = L_s = +0.013302716411` for **both** baselines; `v1` returns `NO_DECISION` for both; `v2` returns `DEPLOY` with `miscover_h = miscover_s = True` | **CLOSED** |
| 2a | no `v1` result changed | `sha256` of each of the 15 tracked files under `results/live_ab_validation/` against its blob at the deposit commit `90595bc` | **15/15 SAME**; `git diff --stat 90595bc HEAD -- results/live_ab_validation/` empty; working tree clean against `HEAD` | **CLOSED** |
| 2b | no `v1` file moved, was added or removed | `git ls-tree -r --name-only` at `90595bc` vs `HEAD`, diffed | lists identical; `git status --untracked-files=all results/live_ab_validation/` returns **0** lines | **CLOSED** |
| 2c | `PROTOCOL.md` and `cells.json` frozen values untouched by `v2` | `git diff HEAD -- PROTOCOL.md cells.json` | empty. The only post-deposit edits are at commit `3db00ba` (a prior task): a `REPORT.md` status-column correction and a `superseded_by` record. **The pin `3c76e8eb…` is retained, not replaced** | **CLOSED** |
| 2d | the `v1` code path still produces the deposited bytes | scratch harness re-derives deposited `trials.csv.gz` rows with the **working-tree** runner under `SCHEDULE_V1` and compares text | **48,000 rows re-derived, 0 mismatches**; `trial_header(SCHEDULE_V1)` equals the deposited header | **CLOSED** |
| 3a | prefix and elapsed time are two separate records | `vrun.trial_header(SCHEDULE_V2)`; `vrun.DECISION_COORDINATES` | trials header carries `tau_prefix,tau_tick` and `look_prefix,look_tick`; `decision_time.csv` emits one row per coordinate with its own `unit` string; the witness reporter prints both. `horizon_rows`/`unresolved_rows`/`decision_rows` emit no decision time at all | **CLOSED** |
| 3b | they can differ - constructed case | `python vrun.py --witness` | `CPREFIX` and `NAIVE`: `tau_prefix = 1,000`, `tau_tick = 1,010`, `decided_in_drain = True` | **CLOSED** |
| 3c | they can differ - **drawn** trials | scratch scan, smoke namespace, `N_max = 300`, 25 programs x 8 cells x 4 trials | 2,400 records, 256 decisions, **22 decided in the drain, and all 22 have `tau != tau_tick`** (e.g. `C7`/`ADAPTER` `tau=300`, `tau_tick=461`) | **CLOSED** |
| 4a | no scientific constant moved | module-level scalar diff of `vgen`/`vrun`, committed `v1` vs working tree | `vgen`: 23 scalars, **0 changed, 0 removed**. `vrun`: **0 changed except `TRIAL_FIELDS`** (which gains fields, drops none), 12 added, 0 removed | **CLOSED** |
| 4b | `alpha`, `rho`, `delta`, `n_min`, the radius and the gates are byte-identical | `git status experiments/live_ab_validation/vband.py` | **empty** - `vband.py` (which defines `ALPHA_GATE = .00625`, `RHO = 100.0`, `DELTA = 0.03`, `N_MIN = 100`, the radius and `decide()`) is byte-identical to `HEAD`, **and** `HEAD` is byte-identical to the deposit `90595bc` | **CLOSED** |
| 4c | `RunConfig` unchanged | scratch comparison at `N_max` 1,000 and 2,000 | `delta`, `n_max`, `n_min`, `namespace`, `trials_per_program` SAME; the 1,001- and 2,001-element `radius` arrays **bitwise equal**; one field added (`schedule`) | **CLOSED** |
| 4d | no `v1` function body moved | AST-level source-hash diff of every top-level def/class | `vgen.py`: **38 of 38 v1 defs byte-identical**, 6 added, 0 removed, 0 changed. `vrun.py`: 40 unchanged, **22 changed, 0 removed**, 12 added | see 4e |
| 4e | the 22 changed `vrun` bodies changed nothing scientific | behavioural equivalence: working tree under `SCHEDULE_V1` vs the committed `v1` runner, 96 trials x 3 constructions at `N_max = 2,000` | **5,472 `TrialRecord` field comparisons, 0 mismatches; 1,728 `Series` array comparisons, bitwise, 0 mismatches.** Plus 2d's 48,000 deposited rows | **CLOSED** |
| 4f | the gate predicate itself | read at `vrun.py:719-721` | `deploy_cond = s.l_h > 0.0`, `guard_cond = s.l_s > -cfg.delta`, `harm_cond = s.u_h < 0.0`, `eligible = s.index >= cfg.n_min`, same-look conjunction - unchanged in substance and proved unchanged in effect by 4e | **CLOSED** |
| 4g | the drain looks compute the same arithmetic as the reference monitor | `python vrun.py --selfcheck` | `v2 drain: 3,680 ticks cross-checked against vband.ValidationMonitor at strict float equality, of which 3,200 are drain ticks v1 never evaluated: 0 mismatch(es)` | **CLOSED** |
| 5a | withdrawn claims are not asserted anywhere live | grep for `guarantee`, `unreachab`, `near-certain`, `the bound holds`, `irreducible`, `22.6`, `27.5`, `49.8`, `apportion`, `11x`, `validated itself`, `would pass unflagged`, `DISAGREEMENT = DEFECT` across `PROTOCOL_V2.md`, `RESOURCE_CHECK.md`, `REPORT.md`, `vrun.py`, `vgen.py`, `vresource_check.py`, `tests_validation.py` | `unreachab`: **0 hits anywhere**. `near-certain`: **0**. `11x`: **0**. Every hit for `validated itself`, `would pass unflagged`, `DISAGREEMENT = DEFECT` and the `27.5/22.6/49.8` apportionment is inside a `BEFORE` block of `REPORT.md` section 16 (line 1253+) with an `AFTER` attached, or inside an explicit withdrawal sentence. `awk 'NR<1290 && /validated itself/'` on `REPORT.md` returns **nothing** | **CLOSED** |
| 5b | no flag is read as proof | read `PROTOCOL_V2.md` 6.2/6.3; grep `is a DEFECT` | 6.3 rules 1-6 are explicit ("do not convert the absence of a flag into a bound on the true rate, and do not convert a flag into a demonstrated violation"). The only surviving `is a DEFECT` sentence is the `BEFORE` block at `REPORT.md:1355`. `vrun.positive_control`'s `consequence_if_failed` string still carries `PROTOCOL.md` 9.4's frozen sentence - **deliberate**, listed as unchanged in `PROTOCOL_V2.md` section 2, and superseded in interpretation by 6.3 | **CLOSED**, note in 9.2 |
| 5c | the Monte Carlo table is arithmetic, not rhetoric | `scipy.stats.binom.sf` on the eight cells of `PROTOCOL_V2.md` 6.2 | all eight reproduce exactly: `.00625/8000 -> 0.0314151088`, `.007/8000 -> 0.1571523834`, `.008/8000 -> 0.5168241304`, `.010/8000 -> 0.9715571681`, `.00625/20000 -> 0.0292396037`, `.007/20000 -> 0.2874093726`, `.008/20000 -> 0.8585531745`, `.010/20000 -> 0.9999655074` | **CLOSED** |
| 6a | the `#11` suite | `./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'` | **`Ran 474 tests in 219.270s / OK`** - matches the stated baseline exactly | **CLOSED** |
| 6b | the `#12` fixtures | `.venv/bin/python experiments/live_ab_validation/vfixtures.py` | **`18/18 fixtures passed`**, 0.58 s, including `F18_pinned_file_hashes` | **CLOSED** |
| 6c | the `#12` tests | `.venv/bin/python experiments/live_ab_validation/tests_validation.py` | **`ran=108 failures=0 errors=0 skipped=0`**, 5.87 s. **Not 88** - the stated baseline is `v1`'s and the amendment adds 20 | **CLOSED**, see 9.3 |
| 6d | `vgen`/`vband` self-checks | `python vgen.py`, `python vband.py` | both exit **0**. `vgen` prints `predicate: 13 disagreement(s)` - this is the **expected frozen output** documented at `PROTOCOL.md:1462` and `REPORT.md:113`, not a new breakage | **CLOSED** |
| 7a | the balanced 20-program resource check runs | `python vresource_check.py --part all` | exit 0, 96 subprocess measurements, no cap breached at any tier for any of the three schedules; highest admissible tier **T1** for all three | **CLOSED** |
| 7b | its deterministic part reproduces the witness | `python vresource_check.py --part check` | `amended == v1 on the shared looks: 24 trials, True`; both baselines `NO_DECISION -> DEPLOY at prefix 1000, tick 1010`, `L_h = L_s = 0.0133027164` | **CLOSED** |
| 7c | its headline cost factor reproduces | same command, compared to `RESOURCE_CHECK.md` section 0 | **it does not.** Reported `x0.943 [0.938, 0.949]`; my run of the same script gives **`x0.960 [0.947, 0.973]`**. The reported interval does not contain my point estimate | **OPEN**, 8.3 |
| 7d | the resource check costs the DELIVERED runner | cross-implementation comparison, plus paired timing of `vrun.evaluate_trial` | **it does not.** See 8.1 and 8.2 | **OPEN** |

---

## 2. Check 1, the witness, in full

The regression is not a guard that cannot fail. I reverted the schedule - monkeypatching `vrun.build_series_v2`
and `vrun.build_series_for` to return the `v1` look set - and re-ran `TestMissedCrossingWitness`. **Six of ten
tests fail:**

```
test_v2_evaluates_the_missed_tick_and_both_gates_cross          AssertionError: 1001 not greater than 1001
test_v2_records_the_decision_and_both_miscoverages              AssertionError: 1001 != 1200
test_enrollment_prefix_and_elapsed_time_are_two_separate_records
test_the_finest_reading_also_sees_it_and_sees_more
test_the_regression_discriminates_the_two_schedules             AssertionError: 0 == 0 : CPREFIX
test_the_witness_is_frozen_at_the_horizon_that_actually_ran     AssertionError: 0 != 1 : CPREFIX
```

The four that still pass are the four that describe `v1`'s defect and the legality of the path
(`..._is_a_permitted_path_...`, `..._lies_in_the_drain_interior`, `v1_schedule_misses_the_crossing_entirely`,
`..._adapter_is_untouched_...`). They **should** pass under both, and one of them - the adapter invariance test -
is trivially satisfied when all three schedules are the same object, so it carries no discriminating weight under
this mutation. That is a note, not a fault.

The witness itself, printed by `python vrun.py --witness`, matches the root's disposition digit for digit:

```
v1_reduced        CPREFIX looks=1,001  NO_DECISION  tau_prefix=1,000 tau_tick=1,200  miscover_h=False
v2_tick_batched   CPREFIX looks=1,200  DEPLOY       tau_prefix=1,000 tau_tick=1,010  miscover_h=True
                  first firing tick 1,010  L_h=+0.013302716411  L_s=+0.013302716411  firing looks 90
```

and the same for `NAIVE`; `ADAPTER` is `NO_DECISION` under all three schedules, as `LASTLOOK_CHECK` (b) requires.
The legality line prints `SHORT offsets [0,0] in support [0,19]: True; LONG offsets [200,509] in support
[100,699]: True`, `f == d: True`, all three atoms positive weight, realised `sum Z = sum D = 0` against
`mu_h = mu_s = 0`, so the crossing **is** a miscoverage and not an artefact.

The same construction at `N_max = 2,000`, the horizon that actually ran, is asserted in
`test_the_witness_is_frozen_at_the_horizon_that_actually_ran` and fires at tick **2,010** with `tau = 2,000`.

---

## 3. Check 2, preservation, in full

```
results/live_ab_validation/README_OUTPUTS.md               3e7d176bf825aaaf SAME
results/live_ab_validation/budget.json                     56e32b7d663bb69f SAME
results/live_ab_validation/comparison_defects.csv.gz       97c27b66a45185df SAME
results/live_ab_validation/comparison_summary.json         65b063cadf9fcf4c SAME
results/live_ab_validation/comparison_vs_live_ab.csv.gz    3c0e7d395a385135 SAME
results/live_ab_validation/compute.json                    1c66cdae2e04f34c SAME
results/live_ab_validation/decision_time.csv               75a6d4b04758c13c SAME
results/live_ab_validation/decisions.csv                   923f05abe8d9ad4d SAME
results/live_ab_validation/fixtures_report.json            40e1c1f442641814 SAME
results/live_ab_validation/horizon_summaries.csv           1377fc60350e3a76 SAME
results/live_ab_validation/manifest.json                   0ba8b7b2fb7212b5 SAME
results/live_ab_validation/miscoverage.csv                 746e383e683f8654 SAME
results/live_ab_validation/smoke/timing.json               a3e24df11d6a0dac SAME
results/live_ab_validation/trials.csv.gz                   5ecedd82ef5e1d35 SAME
results/live_ab_validation/unresolved.csv                  281d2b905910267e SAME
```

**No file moved.** The tracked file lists at `90595bc` and `HEAD` are identical, and
`git status --untracked-files=all results/live_ab_validation/` returns zero lines, so nothing was added beside the
deposited set either. `v2` writes only to `results/live_ab_validation_v2/resource_check/` (3 files).

`PROTOCOL.md` and `cells.json` are **clean against `HEAD`**, so this amendment edited neither. For completeness:
they did move at `3db00ba`, a prior task, by `+11/-1` and `+20/-7` lines. I read that diff in full. It is (a) the
`REPORT.md` status-column correction authorised by coordinator rulings 43/61, with before/after text, and (b) a
`superseded_by` block recording `b1ff97cc…` **beside** the retained pin `3c76e8eb…`. **No cell, parameter, seed,
grid, estimator, reported quantity, flag rule or positive control moved.** The pin is not re-pinned, which is
ruling 60.

`F18` consequently passes rather than failing as ruling 60 anticipated, because the fixture was changed to accept a
**recorded** supersession whose successor hash is itself verified against the file on disk. I checked the new
branch: a pin that simply drifted with no record still fails, and mutating either `sha256` or `supersedes` breaks
the binding. That is fail-closed, not papered over.

---

## 4. Check 3, prefix versus elapsed

Both quantities exist and are emitted together everywhere a decision time is emitted:

```
V2 trials header: ... ,decision,tau_prefix,tau_tick,decided_at_finalization,decided_in_drain, ...
                  ... ,look_prefix,look_tick,n_looks, ...
DECISION_COORDINATES = (('tau',      'enrollment prefix, in enrolled pairs (never wall clock)'),
                        ('tau_tick', 'elapsed decision time, in enrollment ticks (a simulation clock,
                                      never wall clock, never a latency)'))
```

`decision_time.csv` emits one row per coordinate under `v2` and, under `v1`, only the first - so a `v1` re-run
still writes `v1`'s layout. `horizon_rows`, `unresolved_rows` and `decision_rows` emit no decision time at all, so
there is no third place that could carry one alone.

**They differ, on drawn trials and not only on the constructed witness.** Smoke namespace, `N_max = 300`, 25
programs x 8 cells x 4 trials, `SCHEDULE_V2`: 2,400 records, 256 decisions, **22 of them decided in the drain, and
every one of those 22 has `tau != tau_tick`** - `tau` pinned at 300, `tau_tick` between 305 and 490, across both
`ADAPTER` and `NAIVE`.

One thing the root should know, because it bounds the "not one `ADAPTER` number moves" claim. That claim is
correctly scoped in both `LASTLOOK_CHECK.md` and `PROTOCOL_V2.md` to the **deposited** results, and it is true
there for a checkable reason: `ADAPTER`'s `decided_at_finalization` is **0 in all eight cells** of the deposited
`decisions.csv`, so no adapter trial fires anywhere in the drain at `N_max = 2,000` and no adapter decision time
can move. **It is not a theorem.** At `N_max = 300`, 7 `ADAPTER` records flip `decided_at_finalization` from
`True` to `False` between `v1` and `v2` while the decision and both miscoverage flags stay put. If a `v2` run is
ever taken at a shorter horizon, adapter decision-time columns will move.

---

## 5. Check 4, rule drift, done properly

This is the check the root will run first, so it was run four ways rather than by reading.

1. **Constants.** Every module-level scalar of `vgen` and `vrun` compared between the committed `v1` and the
   working tree. `vgen`: 23 scalars, nothing changed, nothing removed (the apparent `CELLS` difference is two
   copies of the same dataclass in two module objects - `repr(hgen.CELLS) == repr(wgen.CELLS)` is `True`).
   `vrun`: nothing changed but `TRIAL_FIELDS`, which gains `tau_tick`, `decided_in_drain`, `look_tick` and six
   `final_*` fields and **drops none**; 12 names added, 0 removed.
2. **The rule module.** `alpha_gate = .00625`, `ALPHA_PER_TRIAL = .0125`, `PROGRAM_ALPHA = .05`, `RHO = 100.0`,
   `DELTA = 0.03`, `N_MIN = 100`, `radius_from_formula`, `decide()` all live in `vband.py`, which is **byte
   -identical to `HEAD`, and `HEAD` is byte-identical to the deposit `90595bc`**. `vcompare.py` likewise.
3. **Source bodies.** AST source-hash diff: `vgen.py` has **38 of 38 `v1` definitions byte-identical**, 6 added, 0
   changed, 0 removed. `vrun.py` has 40 unchanged, 22 changed, 0 removed, 12 added.
4. **Behaviour, which is what actually matters for the 22.** The working-tree runner under `SCHEDULE_V1` against
   the committed `v1` runner: 96 trials x 3 constructions at `N_max = 2,000` gives **5,472 record-field
   comparisons with 0 mismatches and 1,728 bitwise `Series` array comparisons with 0 mismatches**. Then, against
   the **deposited bytes** rather than against a second code copy: **48,000 rows of `trials.csv.gz` re-derived
   with the working-tree runner, 0 mismatches**, with `trial_header(SCHEDULE_V1)` equal to the deposited header.

The 22 changed bodies are the tick-axis plumbing. `build_series` gains a `tick` column and nothing else;
`_look_fractions` is rekeyed from look index to tick, which is the identity on the `v1` axis because
`prefix = min(tick, N_max)` recovers `v1`'s two branches exactly; `evaluate_trial` gains the second coordinate and
the `v2` dispatch. The gate predicate reads, verbatim:

```python
deploy_cond = s.l_h > 0.0
guard_cond  = s.l_s > -cfg.delta
harm_cond   = s.u_h < 0.0
eligible    = s.index >= cfg.n_min
```

and `--selfcheck` drives the new drain looks against the untouched reference monitor: **3,680 ticks at strict float
equality, 3,200 of them drain ticks `v1` never evaluated, 0 mismatches.**

---

## 6. Check 5, wording

Nothing withdrawn is asserted live. `unreachab`, `near-certain` and `11x` have **zero** hits in any file. Every hit
for `validated itself`, `would pass unflagged`, `DISAGREEMENT = DEFECT`, `is a DEFECT and is reported as one` and
the `27.5% / 22.6% / 49.8%` apportionment sits inside a `BEFORE` block of `REPORT.md` section 16 - which begins at
line 1253 - with an `AFTER` attached, or inside an explicit withdrawal sentence in `PROTOCOL_V2.md` section 7.
`awk 'NR<1290 && /validated itself/' REPORT.md` returns nothing, so section 0 no longer carries it.

The surviving uses of `guarantee` are all negations ("not a guaranteed final count", "not a guarantee over all
outcomes", "not a detection guarantee"). `irreducible` appears twice, both times in the sentence denying it.

`PROTOCOL_V2.md` 6.2's binomial table is arithmetic, and it reproduces exactly on all eight cells.

---

## 7. Check 6, counts

| suite | command | true output | note |
|---|---|---|---|
| `#11` | `./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'` | `Ran 474 tests in 219.270s` `OK` | matches the stated baseline. The run also prints three `[signature gate] DEVIATION from section 3` lines for `lab_hostcheck.enumerate_foreign_consumers`, `lab_server.restart` and `lab_server.start`; these are pre-existing informational lines, the suite is `OK` |
| `#12` fixtures | `.venv/bin/python experiments/live_ab_validation/vfixtures.py` | `18/18 fixtures passed`, 0.58 s | `F01`-`F18` all `ok` |
| `#12` tests | `.venv/bin/python experiments/live_ab_validation/tests_validation.py` | `ran=108 failures=0 errors=0 skipped=0`, 5.87 s | **108, not the stated 88.** The amendment adds `TestMissedCrossingWitness` (10) and `TestV2EventSchedule` (10) |

**This is re-execution of the author's own suite on the author's own tree. It is not independent verification.** The
only parts of this pass that are not the author's own assertions are the mutation test in section 2, the
equivalence harnesses in section 5, and the cross-implementation work in section 8.

---

## 8. What is OPEN

### 8.1 The resource check costs an implementation that is not the delivered runner, and its headline sign is wrong for the delivered one

`vresource_check.py` states, in its module docstring and at `RESOURCE_CHECK.md:85`:

> **The v2 runner has not been written.** What is costed here is a faithful implementation of the two candidate
> declarations on the frozen `vgen`/`vrun` arithmetic...

**That is now false.** The `v2` runner exists in `vrun.py` (`build_series_v2`, `build_series_for`,
`evaluate_trial(..., SCHEDULE_V2)`); the resource check was written at 21:26 and the runner at 21:39. The check
pins `db930d7`, at which the runner is not committed, so it measures its own `build_series_all_ticks` /
`build_series_finest` / `evaluate_trial_amended` instead.

For the **primary** (batched) declaration that is harmless on the science and is in fact a useful second
implementation: I compared the two state for state over 128 trials at `N_max` 300 and 1,000, all eight cells, all
three constructions, seven arrays each - **2,688 comparisons, 0 mismatches, bitwise.** Two independently written
implementations of the amended primary agree exactly. That is worth more than the timing.

It is **not** harmless on the cost number. Paired timing of the **delivered** `vrun.evaluate_trial` on the same 20
resource-check programs (5 reps, best of):

```
N_max=1000   v1_reduced 0.0180 s   v2_tick_batched 0.0196 s (x1.088)   v2_event_finest 0.0250 s (x1.383)
N_max=2000   v1_reduced 0.0276 s   v2_tick_batched 0.0318 s (x1.152)   v2_event_finest 0.0398 s (x1.439)
```

`RESOURCE_CHECK.md` section 0 answers the root's question "does the corrected schedule cost materially more?" with
"**No.** Batched: **x0.943**, i.e. 5.7% *cheaper*", and explains the speed-up by an implementation detail
(`v1` "buys its finalization look with a separate `O(N_max)` `state_at_age` call"). **The delivered runner does not
have that property: it is 9-15% more expensive, not 5.7% cheaper.** The explanatory paragraph is about
`vresource_check.build_series_all_ticks`, not about `vrun.build_series_v2`.

My timing is a crude in-process paired measurement, not the check's subprocess protocol, so treat the factor as
indicative. The **operative** conclusion is unaffected and I want to be clear about that: `v1` projects 82.3 s at
`T1` against a 5,400 s cap, so even at x1.15 the amended runner is under 2% of the cap and `T1` stays admissible.
**No cap is breached and nothing needs to be shrunk.** What needs correcting is the claim of a free lunch and the
false sentence about the runner not existing.

### 8.2 The two deliverables declare DIFFERENT "finest" schedules, and the resource check's version contains states the process is never in

Under the batched primary the two implementations agree bitwise. Under the **finest** sensitivity they do not, and
the difference is the `ADAPTER`:

| | `vresource_check` | delivered `vrun` |
|---|---:|---:|
| looks/trial, `C1`, `N_max = 2,000` | **15,807** | **8,777** |
| adapter looks on one `C7` trial, `N_max = 1,000` | 3,993 | 1,200 |
| adapter given intra-tick states? | **yes** | **no**, by the domination argument |

`vrun.build_series_v2(finest=True)` leaves the adapter's look set at the tick-batched one, justified by a fixed
-prefix domination argument that `vrun.assert_adapter_intratick_domination` drives through `vgen.state_at_age`
directly - and that assertion passes, non-vacuously, over **6,253** intra-tick states on the test suite's own
draws (the test itself only asserts `> 500`; 6,253 is the true count).

`vresource_check.build_series_finest` adds intra-tick adapter states, and **they are not consistent with that
argument.** On one `C7` trial at `N_max = 1,000`, tick 510 carries four adapter states:

```
end-of-tick (vrun, and vresource's first and last):  L_h=+0.177628597645  U_h=+0.681194931767  L_s=-0.030214539610
vresource's two extra states:                        L_h=+0.179589381959  U_h=+0.679234147453  L_s=-0.028253755296
```

The extra states are **strictly tighter** than the end-of-tick state at the same tick - tighter, in fact, than the
end-of-tick states at 511, 512 and 513 as well. Across that one trial, **793 of the 1,060 ticks carrying more than
one state carry a state strictly tighter than that tick's end state.** Either those states belong to a later tick
or they mix one prefix's sums with another prefix's radius; either way they are not states the declared process
occupies at that tick, and they make the resource check's finest runner "decide" earlier than the real one (first
fire at tick 510 with `L_h = 0.1796` versus tick 614 with `L_h = 0.1726`). Over 576 trial-by-construction records I
found **12 disagreements between the two finest implementations, all `ADAPTER`, all in the decision time; no
decision and no miscoverage flag disagrees anywhere.**

**Nothing reported is wrong because of this.** `vresource_check.assert_resource_only` walks every emitted record
and aborts on any key that is not a timing, memory, byte or count field, so no decision from that module has ever
left it. But two consequences stand: the `x1.911` / `x1.920` finest cost is the cost of a heavier and internally
inconsistent schedule (1.80x the delivered runner's look count), and **the finest declaration is not currently
single-valued across the deliverables.** `PROTOCOL_V2.md` 1.2 item 2 does not say whether the adapter is in or out
of the finest reading; `vrun` says out and proves it; `vresource_check` says in. The coordinator should rule.

### 8.3 The reported resource interval does not cover a repeat run

`RESOURCE_CHECK.md` reports `x0.943, 95% CI [0.938, 0.949]` batched and `x1.911 [1.880, 1.943]` finest. I re-ran
the same script, unchanged, on the same machine: **`x0.960 [0.947, 0.973]`** and **`x1.920 [1.887, 1.953]`**. The
batched interval does not contain my point estimate. The interval is `1.96 SEM` over 32 paired within-run
observations and therefore measures within-run jitter, not between-run variation on a shared laptop. Either widen
it, or report it as a within-run interval and quote the two runs side by side. The sign and the order of magnitude
are stable; the third digit is not.

### 8.4 Smaller, but they are emitted labels

- **`tau_prefix` versus `tau`.** `PROTOCOL_V2.md` 1.3 declares the name **`tau_prefix`**, and `trials.csv` uses it.
  But `DECISION_COORDINATES[0][0]` is `"tau"`, so `decision_time.csv`'s `coordinate` column will emit **`tau`**.
  One name, two spellings, in two deposited files. Pick one.
- **The `#12` test count.** The root's baseline is 88; the true count is **108**. `PROTOCOL.md:1130` still records
  88, correctly - it is frozen `v1` text and must not be edited - so the `v2` report needs to print 108 beside it,
  or the root's first check will look like a discrepancy.
- **`vrun.positive_control`'s `consequence_if_failed`** still carries `PROTOCOL.md` 9.4's automatic-verdict
  sentence verbatim. That is deliberate (`PROTOCOL_V2.md` section 2 lists the frozen sentence as unchanged) and
  the interpretation is superseded in 6.3, but the string is what a reader of `fixtures_report.json` sees first.
  Worth a pointer in the emitted record rather than only in the protocol.
- **Coordinator ruling 63's flaky full-suite failure at 474 tests is still not closed.** My run of the `#11` suite
  was clean at 474, on a quiescent tree, in 219 s. One clean run does not close it.

---

## 9. Bottom line for the coordinator

**Ship the schedule repair.** The witness closes under mutation, `v1` is preserved by hash and reproduces byte for
byte through the amended code, the two decision coordinates are genuinely separate and genuinely differ on drawn
trials, and no scientific rule moved by any of four independent measurements. A second, independently written
implementation of the amended primary agrees with the delivered one bitwise over 2,688 array comparisons.

**Do not ship the resource section as written.** Fix the false "the v2 runner has not been written" sentence, rule
on whether the finest reading includes the adapter, re-cost against `vrun` rather than against
`vresource_check`'s own runner, and correct the "5.7% cheaper" headline - the delivered runner is 9-15% *more*
expensive, which changes no decision but should not be reported backwards.

**Commands, for re-execution.** Everything above is reproducible with:

```
./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'
.venv/bin/python experiments/live_ab_validation/vfixtures.py
.venv/bin/python experiments/live_ab_validation/tests_validation.py
.venv/bin/python experiments/live_ab_validation/vrun.py --witness
.venv/bin/python experiments/live_ab_validation/vrun.py --selfcheck
.venv/bin/python experiments/live_ab_validation/vresource_check.py --part check
.venv/bin/python experiments/live_ab_validation/vresource_check.py --part all
```

The mutation harness, the `v1` equivalence harness, the deposited-row reproduction, the cross-implementation
comparison and the paired timing were written for this pass and live in this session's scratch directory; each is
under 60 lines and is described completely enough above to be rewritten. None of them writes to the repository.
