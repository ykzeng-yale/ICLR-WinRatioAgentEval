# V2 adapter, all-look comparison, frozen workload and fail-closed gate — receipt

**Cycle:** 2026-09-21, independent CPU validation (#12) of the #11 live A/B monitor.
**Read first, and binding here:** `experiments/live_ab/design/COORDINATOR_DECISIONS.md` revisions 16, 17 and 18;
`reviews/v2_comparison_root_disposition_20260921_0453.md` and the two reviews it links
(`v2_resource_delta_20260921_0453.md`, `v2_reference_delta_20260921_0453.md`), all on `origin/main`; and issue
#12 comments **5755619766** (05:00 UTC) and **5755854498** (05:32 UTC). Both issue comments were read; the
second carries two wording corrections that the first does not, which is the failure mode the root has named
repeatedly.

Every number below is output from a command in this file. Nothing is projected from a number that was not run.

**Preserved absolutely, and verified by `git status` at the end of the work:** nothing under
`results/live_ab_validation/` changed; `PROTOCOL.md`, `cells.json` and `pinned/` are untouched; the previous
`results/live_ab_validation_v2/comparison_v2/` receipt is untouched and keeps its bytes. No scientific rule
moved: scoring, `alpha_gate = 0.00625`, `rho = 100`, `delta = 0.03`, `n_min = 100`, margins, gates, seeds,
stopping, deadline and finalization are all unchanged. No calibration grid, no sweep, no live trial, no model
call, no paid compute.

---

## 0. Test and fixture counts, true

```
$ ./.venv/bin/python experiments/live_ab_validation/tests_validation.py
Ran 175 tests in 11.292s
OK (expected failures=2)
ran=175 failures=0 errors=0 skipped=0
```

Baseline before this work was **156** tests. **19 new tests** were added and one existing test was **amended**
(see §3). Separately:

```
$ ./.venv/bin/python -c "import vfixtures; ..."   # vfixtures.run_all()
fixtures run: 18 failing: 0
```

The F16 import-graph guard's dynamic probe now also imports `vpolicy`, so the new adapter is covered by the same
mechanical independence check as every other module here rather than by a promise.

---

## 1. TASK 1 — the matched operational-policy adapter

### What was built

`experiments/live_ab_validation/vpolicy.py` — a **separately versioned** CPU implementation of #11's declared
operational observation policy. `policy_id = "cpu-operational-policy-adapter"`, `policy_version = "1.0.0"`,
`sha256 = 210956feb1c5831c…`.

It imports **nothing** from the monitored tree. It imports `vband` — this validation's own code — for the
episode state machine, the band arithmetic and the final-score rule, because those are **shared and unchanged**
and only the *observation policy* is supposed to differ. What it re-implements is the certificate-gated
narrowing, transcribed from the shared mathematical contract:

| case | rule |
|---|---|
| both revealed | the exact final score, a point |
| neither revealed | `[-1, +1]` |
| one revealed, `s_r = 0` | `{-sgn, 0}` |
| one revealed, `s_r = 1`, **forward** | `(1 - tol) * ell > L_r + eps` → `{sgn}` |
| one revealed, `s_r = 1`, **reverse** | `ell > (1 - tol) * L_r + eps` → `{0, sgn}` |
| otherwise | `{-1, 0, +1}` |

`tol = 0.05`, `eps = 1e-9`. These are the **executed float expressions**, not the division form
`ell > L_r/(1 - tol)`, which is explanatory only — the root's 05:32 correction, and a test
(`test_the_executed_predicates_are_not_the_division_form`) asserts the source text against it so the mislabel
cannot come back.

`OperationalMonitor` subclasses `vband.ValidationMonitor` and overrides **`_refresh` and nothing else**. A test
asserts that `enroll`, `finalize`, `observe_elapsed_cost`, `band`, `look` and `score_bounds` are the *identical
function objects* as on the base class, so the adapter cannot drift on anything except the one thing it is meant
to differ on.

### The oracle is kept, separately

`vband`'s ideal enclosure enumeration is **unchanged, un-wrapped and un-shadowed**, and its deposited results
keep their bytes. `vcompare` gained `--policy {auto,oracle,operational}`; the default is `auto`, which resolves
to `oracle` under v1 (so v1 reproduces) and `operational` under v2 (so calibration claims are matched). When the
operational policy is compared, the oracle is driven over the **same event stream as a shadow** and its
containment is checked as **its own check**, never as a disagreement count.

### TRUE output — the six states of the root's ledger

```
$ ./.venv/bin/python -c "import vband, vpolicy; ..."
                   ell   cost   revealed |    ADAPTER(op) |    ORACLE(cpu)
      10.5263157894737   10.0  incumbent |    [-1.0, 0.0] |   [-1.0, -1.0]  fwd_margin=0.0 rev_margin=1.026315789473685
      10.5263157894737   10.0  candidate |     [0.0, 1.0] |     [1.0, 1.0]  fwd_margin=0.0 rev_margin=1.026315789473685
                   9.5   10.0  incumbent |    [-1.0, 1.0] |    [-1.0, 0.0]  fwd_margin=-0.9749999999999996 rev_margin=0.0
                   9.5   10.0  candidate |    [-1.0, 1.0] |     [0.0, 1.0]  fwd_margin=-0.9749999999999996 rev_margin=0.0
                    38   40.0  incumbent |    [-1.0, 1.0] |    [-1.0, 0.0]  fwd_margin=-3.8999999999999986 rev_margin=0.0
                    38   40.0  candidate |    [-1.0, 1.0] |     [0.0, 1.0]  fwd_margin=-3.8999999999999986 rev_margin=0.0
```

The adapter column reproduces the **live** column of the root's six-state table exactly, in all six. Both
boundary margins are **exactly `0.0`**, which independently confirms the root's finding that the difference
survives `eps = 0`: it is a difference of algebraic **form**, and the reverse boundary's strict `>` at equality
is a second, distinct source of conservativeness.

---

## 2. TASK 2 — every v2 tick compared

### The defect and the repair

`vcompare.py:1219–1221` read `if t > n_max and not is_final: continue`, unconditionally. Every non-final drain
look was skipped and the emitted CSV contained **zero** of them — confirmed directly on the old receipt:

```
OLD v2 receipt: rows=22523 has_drain_column=False drain_rows=0
```

The skip is now guarded by `compare_drain_looks`, resolved from `SNAPSHOT_DEFAULTS`: **False under v1**
(byte-for-byte reproduction) and **True under v2**. The denominator is fixed at `N` through the whole drain by
`n = min(t, n_max)`, which is unchanged. A `drain_look` column was added to the look CSV so the repair is
checkable from the CSV alone rather than from the summary's word for it. Mismatches are **preserved**, never
suppressed: `--max-defect-rows` still defaults to 0, meaning write every disagreement.

### TRUE output — the SAME bounded partial comparison, re-run

8 of 200 cell streams (one per cell, `C1..C8`, namespace 2, program 0, trial 0) plus the fixtures; 726 of 730
captured fixture scripts comparable, 4 retained as explicit exclusions.

**(a) Unchanged oracle policy, repaired schedule.** This isolates the *drain-look* effect from the *policy*
change, which is the question as literally posed.

```
$ vcompare.py --snapshot v2 --policy oracle --drain-looks all --streams-per-cell 1 \
      --out results/live_ab_validation_v2/comparison_v2_alllook_oracle
The two implementations DISAGREE: 102 of 17603 compared looks, over 734 streams, failed at least one frozen criterion.
drain looks: 1592 compared, 3 disagreeing (schedule: all ticks through N+W)
  per_pair_enclosure_endpoint                  103 rows, 8 streams
  band_endpoint                                101 rows, 8 streams
```

| quantity | before (skip) | after (all ticks) | delta |
|---|---:|---:|---:|
| total compared looks | 16,011 | **17,603** | +1,592 |
| disagreeing looks | 99 | **102** | +3 |
| defect rows | 198 | **204** | +6 |
| — per-pair enclosure endpoint | 100 | **103** | +3 |
| — aggregate band endpoint | 98 | **101** | +3 |
| non-final drain looks in the CSV | 0 | **1,592** | +1,592 |
| of those, disagreeing | — | **3** | — |

**Three of the 1,592 newly included drain looks disagree.** They are new: the v1 schedule concealed them. This
is a count on 8 of 200 streams and **no rate is extrapolated from it**.

**(b) Matched operational policies, repaired schedule** — the comparison the root ordered for calibration.

```
$ vcompare.py --snapshot v2 --streams-per-cell 1 \
      --out results/live_ab_validation_v2/comparison_v2_alllook
The two implementations agree on 734 streams (17603 of 17603 compared looks) to 1e-12.
observation policy compared: operational (MATCHED operational policies)
drain looks: 1592 compared, 0 disagreeing (schedule: all ticks through N+W)
oracle containment (SEPARATE check): 19208000 pair-state checks, 0 containment violations,
                                     103 pair states where the oracle is strictly narrower
```

| quantity | matched run |
|---|---:|
| compared looks | 17,603 |
| disagreeing looks | **0** |
| defect rows | **0** |
| drain looks compared / disagreeing | 1,592 / **0** |
| oracle-containment pair-state checks | 19,208,000 |
| oracle-containment **violations** | **0** |
| pair states where the oracle is strictly narrower | **103** |
| per-pair endpoint comparisons | 76,901,400 |
| wall clock / peak RSS | 28.99 s / 95,813,632 B |

**Read this honestly.** The 99 disagreements were not bugs that got fixed. They were **reclassified** — from a
disagreement count into the separate oracle-versus-operational diagnostic, which is what they always were. The
count that moved from 99 → 102 → 0 did so because (i) the schedule repair added 3 and (ii) the policy match
moved all 103 per-pair states into the containment check. Nothing was suppressed: the 103 are still counted, in
the column where they belong.

### v1 reproduction, checked

Running the old policy and old schedule on `C1:0:0` gives **12 `per_pair_enclosure_endpoint` rows**, matching the
old receipt's per-stream count for `C1` exactly (12 disagreeing of 2,001 looks). The v1 path is preserved. v1's
own results directory was never opened for writing.

---

## 3. TASK 3 — frozen reference workload and the fail-closed resource gate

### The frozen amendment, before and after

Recorded in executable form as `vrun.REFERENCE_WORKLOAD` and `vrun.REFERENCE_WORKLOAD_AMENDMENT`. Kind:
**post-development, pre-full-calibration amendment**, frozen before execution.

> **BEFORE** (`reference_workload_costs()['workload_declaration_status']`):
> "NOT YET DECLARED. How many reference calls the primary grid will actually make is not fixed by any frozen
> document. The totals below assume ONE reference evaluation per program at the tier's horizon, which is stated
> as an ASSUMPTION and is not a prespecified workload. It must be predeclared before any tier is relied on."

> **AFTER:**
> "DECLARED AND FROZEN. One complete-path reference call per score per trial, for BOTH the hierarchy score H and
> the success-difference score D, on the shared latent arrays and the fixed prefix grid. Four trials per program
> therefore mean EIGHT reference calls per program. Each full path is computed once and its bands are indexed; it
> is not rerun at each look or separately for each baseline. The reference keeps its complete-information status
> and has no primary decision authority."

> **WHY:** the old text was not merely imprecise, it was numerically wrong in two directions at once. The
> receipt behind it already contained **four** trial calls per program, not one, and each was **one score stream
> (H only)**. A two-score panel doubles that again. "One evaluation per program" understated the executed
> workload by a factor of **eight**.

Unchanged by the amendment: the scientific design and the outcome-independent primary tier; alpha, margins,
seeds, scoring, stopping, deadline, finalization; the reference's zero decision authority; and every previously
deposited receipt, all of which are preserved unedited. `may_be_silently_dropped` is `False` and is asserted by a
test.

One existing test was **amended, not deleted**: `test_the_reference_receipts_provenance_limits_are_recorded`
asserted `"NOT YET DECLARED"`, which was correct while it was true. It now asserts `"DECLARED AND FROZEN"`, and
three new tests check the *numbers* (8 calls/program, H and D, 4 trials) rather than the prose.

### The fail-closed total-workload guard

`vrun.total_workload_guard()` (pure) and `vrun.enforce_total_workload_guard()` (raises
`vrun.TotalResourceRefusal`, a `SystemExit`). It is **separate** from the frozen scientific tier selection, which
is untouched and still reads the primary projection only. It carries an empty `exemptions` list. It is called in
`main()` **before the grid runs** and its verdict is written into `budget.json`; `grid_may_start` now also
requires it.

Refusal classes: `unresolved_total_cost`, `total_over_cap`, `no_tier_selected`.

### TRUE output — the guard actually refuses

```
$ ./.venv/bin/python experiments/live_ab_validation/vtotalguard.py
{
  "selected_tier_on_primary_only": "T1",
  "guard_as_projected_authorized": true,
  "guard_as_projected_total_seconds": 2043.91353209503,
  "tripped": [
    {"unresolved_reference_cost": "PASS: the guard refused and execution could not proceed"},
    {"total_over_cap_with_admissible_primary": "PASS: the guard refused and execution could not proceed"},
    {"no_tier_selected": "PASS: the guard refused and execution could not proceed"}
  ],
  "demonstration_result": "PASS: every way of tripping the guard refused and raised"
}

--- unresolved_reference_cost ---
TOTAL-WORKLOAD RESOURCE GUARD REFUSED (unresolved_total_cost): the declared reference workload has NO resolved
cost at this tier, so the TOTAL is unresolved. Unresolved is not zero and is not a pass: execution is REFUSED
until the cost is measured or the workload is rescoped by a decision on the record. This guard is separate from
the frozen scientific tier selection and carries no exemption.

--- total_over_cap_with_admissible_primary ---
TOTAL-WORKLOAD RESOURCE GUARD REFUSED (total_over_cap): the projected TOTAL workload is 10894.0 s against a cap
of 5400.0 s. The primary-only tier is admissible, which does not matter here: the total is what is being
authorized. Execution is REFUSED. ...

--- no_tier_selected ---
TOTAL-WORKLOAD RESOURCE GUARD REFUSED (no_tier_selected): no tier was selected by the frozen primary rule, so
there is no total workload to authorize. REFUSED. ...
```

The over-cap case is the important one: the **primary-only tier is admissible** and the guard refuses anyway,
which is exactly the separation the resource review asked for. Five unit tests assert the same four behaviours
in the suite, so this is a permanent gate and not a one-off script.

Ladder under the declared two-score workload (seconds; the frozen primary selection did not move, T1):

| tier | primary | reference | total | ref share |
|---|---:|---:|---:|---:|
| T1 | 94.05 | 1949.86 | **2043.91** | 95.4% |
| T2 | 53.74 | 1114.21 | 1167.95 | 95.4% |
| T3 | 26.87 | 557.10 | 583.98 | 95.4% |
| T4 | 16.96 | 266.36 | 283.32 | 94.0% |

Cap is 5,400 s, so the guard **authorizes at the current projection**. That is an authorization of a projection,
not a resource clearance.

---

## 4. TASK 4 — the authorized bounded timing, and only this

`experiments/live_ab_validation/reference/combined_workload.py`. It lives on the **reference** side because the
one-way rule (reference → primary, never the reverse) is mechanically enforced: a test asserts
`vresource_check.py` does not contain the reference's name at all.

**Design:** the existing namespace-1 balanced 20 units — cells C1/C2 crossed with horizons 1,000/2,000, five
programs per group, program indices **1000–1004**. Ten distinct `(namespace, cell, program)` seed identities, not
20 independent programs, because the RNG key excludes the horizon; the receipt says so.

**Two scopes, measured contemporaneously in one process on the same draws**, so the difference is a *paired*
measurement and not a subtraction of two receipts from different machines:

* `primary_only` — `vgen.draw_trial` + `vrun.evaluate_trial` + `vrun.trial_rows` into a discard `RowSink`.
* `combined` — the same, **plus** the frozen workload: one complete-path call on H (`draw.z`) and one on D
  (`draw.dsc`) per trial, on the shared latent arrays. Each path computed once.

**Command and true output** (`--inner 20 --reps 3 --write`; medians over 3 repetitions of the 20-rep inner loop):

| cell | N_max | primary_only (s) | combined (s) | missing scope (s) | missing share | combined s/program | missing s/program |
|---|---:|---:|---:|---:|---:|---:|---:|
| C1 | 1000 | 0.010411 | 0.176885 | 0.166474 | 94.1% | 0.035377 | 0.033295 |
| C2 | 1000 | 0.010479 | 0.176077 | 0.164826 | 94.1% | 0.035215 | 0.032965 |
| C1 | 2000 | 0.016475 | 0.360054 | 0.343579 | 95.4% | 0.072011 | 0.068716 |
| C2 | 2000 | 0.016497 | 0.363880 | 0.347383 | 95.5% | 0.072776 | 0.069477 |

**Attempts: 13 total, 0 failed** (1 reference-import attempt + 12 group measurements = 4 groups × 3 reps). Every
attempt is recorded in the receipt with its status; a failure would carry its exception type, message and
traceback tail. Group order rotates each repetition so drift cannot land on one group.

**Raw times are retained**, 20 per scope per group per rep. First group, `combined`:

```
0.169857 0.169454 0.168997 0.168652 0.169422 0.170064 0.170146 0.169495 0.169882 0.169892
0.169799 0.169829 0.169133 0.168957 0.169290 0.169106 0.169161 0.169177 0.169161 0.169261
```

**CALL COUNTS, per group of 5 programs / 20 trials** (counted in the timed region, not assumed):

| counter | `primary_only` | `combined` |
|---|---:|---:|
| generation_calls | 20 | 20 |
| primary_trial_calls | 20 | 20 |
| serialization_calls | 20 | 20 |
| reference_calls_h | 0 | **20** |
| reference_calls_d | 0 | **20** |
| reference_calls_total | 0 | **40** |
| **reference_calls_per_program** | 0 | **8** |
| looks | 72,000 | 72,000 |
| band_evaluations | 144,000 | 144,000 |
| enclosure_updates | 57,599 | 57,599 |

Eight reference calls per program, executed and counted, matching the frozen declaration exactly.

**Output sizes:** 199.2 / 201.4 / 226.8 / 216.6 record bytes per program (C1·1000, C1·2000, C2·1000, C2·2000).
Identical between scopes, as expected: the reference writes no rows in this scope.

**Memory, with the correct platform unit:** `ru_maxrss` is **bytes on darwin** and **kibibytes on linux**; this
harness converts and records which branch ran (`darwin: bytes`). Baseline RSS 69,730,304 – 72,007,680 B across
groups; peak 70,123,520 – 72,007,680 B; the largest single-group delta is 393,216 B. The four groups share one
process, so the peak is a cumulative high-water mark — stated, not hidden. (`reference/panel.py:200–202` still
multiplies by 1 on both platforms; that defect is **not** inherited here and is **not** fixed there — see §6.)

**Exact pins recorded in the receipt:** `vrun.py` `a8c0e9f57752…`, `vgen.py` `513ac967c0d2…`, `vband.py`
`55a9894ff569…`, `vresource_check.py` `fb071eb0d616…`, harness `f4d18981785b…`, `eb_reference.py`
`41498a28e67f…`; config `cells.json` `96ebf7e47f79…`, `PROTOCOL_V2.md` `259863aa4fc0…`; **compiled binary**
`reference/_build/boundaries.cpython-312-darwin.so` `f1c65419fd9785be…`, 356,208 bytes; loaded module origins for
`comparecast` / `confseq` / `eb_reference`; Python 3.12.13, NumPy 2.4.1, macOS-26.5.2-arm64, 10 CPUs.

### The two things the root corrected, and how they are handled

**The 91.2% figure is NOT reused.** It is not reproduced, not scaled, not repaired. The claim was withdrawn from
`V2_BINDINGS_2.md` and replaced by the surviving point only — a reference excluded from every ladder hides real
cost. Instead, two *independent* routes to the reference-attributable per-program cost are reported side by side:

| horizon | route A: H-only receipt × 2 (arithmetic) | route B: measured missing scope | ratio B/A | used |
|---|---:|---:|---:|---|
| 1,000 | 0.032405 | **0.033295** | 1.0275 | route B |
| 2,000 | **0.069638** | 0.069477 | 0.9977 | route A |

They agree to **2.7%** at horizon 1,000 and **0.23%** at horizon 2,000, and **neither dominates**. The guard uses
the **larger per horizon** — a conservative resource rule, applied per horizon, discarding neither route. (My
first draft of this reconciliation asserted route A was larger at every horizon. That was false at horizon 1,000;
I caught it against the printed numbers and corrected it rather than leaving it.)

**The lower-bound explanation is withdrawn**, from both `reference_workload_costs()`'s provenance limits and
`V2_BINDINGS_2.md` item 5. The premise was false: the accepted primary measurement's timed region already called
`vgen.draw_trial`, `vrun.evaluate_trial` and `sink.write(vrun.trial_rows(...))` (`vresource_check.py:739–760`).
There is no certified inequality between two noisy timings. What replaces it is a list of *named* remaining
scope differences: the grid's block accumulator, output path and per-batch summary work; a disk-backed sink
versus a discard sink; warm-up and process context. A test fails the file if the phrase "lower bound" returns to
those limits.

---

## 5. ALSO — the mislabelled variance column and the reversed alpha history

**Realized variance.** `eb_width_diagnostic.py` reported `cumsum((z - mus)**2)` as `realized_variance_sum`. Each
term is centred by a **different contemporaneous running mean**, so it is not the ordinary prefix sum of squares.
The module now computes and emits **both**, each named for what it is:
`contemporaneously_centered_squared_residual_sum` and `prefix_centered_sum_of_squares`
(`cumsum(z*z) - n*mus*mus`), with a clock gap against each.

The saved receipt was **not rerun and not edited**. `reference/eb_descriptive_correction.py` regenerates **only**
the affected descriptive columns from the same eight declared latent paths, **without calling the reference at
all**, and deposits a separate file. True output:

```
$ ./.venv/bin/python experiments/live_ab_validation/reference/eb_descriptive_correction.py
{
  "prefix_centered_sum_of_squares": 1332.8875,
  "contemporaneously_centered_squared_residual_sum": 1328.0053387752139,
  "reference_clock_V_n": 1338.369549643862
}
reconciled 48 saved values, 0 mismatches
```

All three values match the reference-delta review's independently computed C8 `n = 2000` figures (1332.8875,
1328.0053387752, 1338.3695496439), and **all 48 saved means/clocks reproduce with 0 mismatches**, so the
correction is a relabel plus an addition and **no saved mixture width, ratio, running mean or clock changes**.
The consequential `V2_BINDINGS_2.md` sentence is repaired too: the "roughly 10–14 units" gap was measured against
the wrong object and is withdrawn; the two real gaps at C8 `n = 2000` are **10.364** (contemporaneously centred)
and **5.482** (prefix centred).

**Alpha-error history.** The saved `supersedes.why_it_failed` read "alpha pre-halved against a wrapper that
halves internally", which **reverses** the error. The withdrawn document declared a **direct** stitched-boundary
call at the **full** `alpha = 0.00625` with **no** internal split, compared against a wrapper that splits
`alpha/2` internally. Corrected in `eb_width_diagnostic.py` with an explicit `correction_history` block, and in
`V2_BINDINGS_2.md`'s closure table. `affects_any_current_number: false` — the executable comparison in the module
was already correct (its own docstring item (b) always described it correctly).

---

## 6. BLUNT LIST — what did NOT close

1. **This is still 8 of 200 cell streams.** The full frozen set has not been replayed against the v2 snapshot
   under either policy. No rate is extrapolated from 8 streams, and nothing here is a calibration.
2. **The full calibration grid was not run and live clearance is not given.** Both remain pending, as instructed.
3. **`experiments/live_ab/` source prose is still unrepaired.** The root's ranked action 1 also asks for the live
   source's exactness and stopped-roster wording to be corrected and the snapshot regenerated. That is outside
   this session's declared write scope (`experiments/live_ab_validation/` and `results/live_ab_validation_v2/`
   only), so `lab_data.py`'s stopped-roster claim and `pinned_v2/lab_enclosure.py`'s "exact"/"never a relaxation"
   wording remain **disclosed, not repaired**, and the snapshot was **not** regenerated. This is the single
   largest piece of ranked action 1 left open.
4. **The 3 new drain-look disagreements are characterised but not adjudicated.** They are recorded in
   `comparison_v2_alllook_oracle/comparison_defects.csv` with their reproducers. Which side is right is a
   coordinator/root ruling; neither side was edited.
5. **Oracle containment is verified only at the states these 8 streams visited.** 19,208,000 pair-state checks
   with 0 violations is evidence about *those* states. It does not certify all feasible states, all operational
   decisions or all future stopping summaries.
6. **The effect of the conservative policy on decision timing is still UNMEASURED.** A wider band can delay when
   a gate fires. No `tau` differed in this partial run, but that is 8 streams, not a measurement of the effect.
7. **The guard authorizes a projection, not a run.** The T1 total of 2,043.91 s is projected from re-expressed
   measurements on 20 development units with ten distinct seed identities. It is not observed full-run compute
   and must not be read as resource clearance.
8. **The combined timing's scope is still narrower than a grid.** The block accumulator, the real output path,
   the per-batch summary and a disk-backed sink are in none of the measured scopes. Named, not bounded.
9. **`reference/panel.py:200–202` still multiplies `ru_maxrss` by 1 on both platforms** — correct on macOS,
   wrong by 1024 on Linux. `combined_workload.py` does it correctly; `panel.py` was **not** changed, because its
   deposited receipt would then no longer be reproducible from its own code.
10. **The old reference receipt remains weak.** Min/median/max only, no raw vectors, no environment, no hashes.
    It is still an input to route A. The new combined receipt is an exact-pin receipt; the old one is not, and
    replacing it would destroy the comparison base.
11. **The `certified` / `collapsed` flag is still not compared**, and no look is taken at `n = 0` on either side.
    Both remain excluded by construction and escalated, unchanged from v1.
12. **Four captured fixture scripts remain non-comparable** (no corresponding live pending-state representation).
    Retained as explicit exclusions, not silently dropped.

---

## 7. Files written or changed

**New:** `vpolicy.py`, `vtotalguard.py`, `reference/combined_workload.py`,
`reference/eb_descriptive_correction.py`, this receipt.

**Changed:** `vcompare.py` (policy selector, drain-look repair, oracle-containment check, `drain_look` column,
summary blocks), `vrun.py` (frozen workload, amendment, reference cost routes, fail-closed guard and its
enforcement in `main`), `vfixtures.py` (F16 probe now imports `vpolicy`), `tests_validation.py` (+19 tests, 1
amended), `reference/eb_width_diagnostic.py` (column names, alpha history), `V2_BINDINGS_2.md` (91.2%,
lower-bound, variance and alpha corrections), `ADJUDICATION_99.md` (drain-look update).

**Deposited under `results/live_ab_validation_v2/`:** `comparison_v2_alllook/`,
`comparison_v2_alllook_oracle/`, `total_workload_guard_demonstration.json`,
`reference_width_diagnostic_descriptive_correction.json`,
`resource_check_delivered/combined_workload_timing.json`.

**Untouched, verified:** everything under `results/live_ab_validation/`; `PROTOCOL.md`; `cells.json`; `pinned/`;
`results/live_ab_validation_v2/comparison_v2/`; `reference_width_diagnostic.json`.
