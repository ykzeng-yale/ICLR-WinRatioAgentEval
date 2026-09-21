# LASTLOOK_CHECK: the root's last-look witness, verified

Coordinator ruling 56 (`experiments/live_ab/design/COORDINATOR_DECISIONS.md` revision 12) took the root's second
CPU finding seriously and marked every baseline number in the grid report PROVISIONAL "until I have reproduced
the witness myself". This file is that reproduction.

| field | value |
|---|---|
| finding under test | `reviews/arxiv_cpu_prereg_statistics_review.md` section 2 (read at `origin/main`) |
| claim under test | `PROTOCOL.md:835-843` / `cells.json` `grid.one_look_per_enrollment_prefix`: keeping only the final look at each enrolled prefix is an **exact reduction** of the all-triggers rule for ever-miscoverage and for the decision prefix |
| script | `experiments/live_ab_validation/vlastlook_check.py` (writes nothing; every number below is its stdout) |
| commands | `.venv/bin/python experiments/live_ab_validation/vlastlook_check.py --part witness` (0.4 s), `--part adapter --adapter-programs 500` (70 s), `--part grid` (181 s) |
| environment | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1. CPU only; no model call, no API call, no network, no new dependency. |
| grid swept | the **whole** reported grid as deposited: tier `T1`, `N_max = 2,000`, drain `W = 200`, namespace 0, 28,000 programs / 112,000 trials |

---

## 0. Verdict

**The witness reproduces, exactly, to every digit the root printed. The claim of exact preservation is FALSE and
the root is right. The damage is bounded, it is confined to the two completed-data baselines, and it does not reach
the object under test or the positive control.**

| question | answer |
|---|---|
| (a) does the reduction fail for `CPREFIX`, for `NAIVE`, or both? | **Both.** The mechanism is identical for the two, and in the root's own witness they are not merely both wrong, they are the *same* wrong: the completed set there is `{1..600}`, which is a prefix, so `k = m = 600` and the two constructions coincide state for state. On the frozen grid the realized damage is mostly `CPREFIX`'s. |
| (b) does it fail for the `ADAPTER`? | **No.** Proven by the protocol's own monotonicity argument, which is valid for the adapter, and checked by brute force over **every** drain tick of 16,000 real grid trials: 0 non-monotone, 0 events at a drain tick that the finalization look does not also carry. **Not one `ADAPTER` number in the deposited results moves, under any reading.** |
| (c) which reported numbers are affected? | **12** deposited rows under the batched reading (3 in `miscoverage.csv`, 8 in `decisions.csv`, 1 in `decision_time.csv`), **77** under the finest reading (35 / 32 / 10), plus a few `unresolved.csv` rows. Full list in section 4. Every one of them is **understated** in the deposited files. |
| (d) does the positive control survive? | **Yes, decisively.** It survives by a monotonicity argument that needs no recomputation, and the recomputation agrees: flagged in all three of `C2`, `C4`, `C6` under all three schedules, with Wilson lower limits of 0.8098-0.9996 against a nominal of 0.00625. **The apparatus is not unvalidated and the `ADAPTER` results are not uninterpretable.** |

**One correction to the finding's framing, which does not touch its substance.** The root's witness is stated
inside the `T4` horizon. `T4` never ran: the budget ladder selected **`T1`**, `N_max = 2,000`
(`results/live_ab_validation/budget.json`). The witness is a statement about the reduction, not about the tier, so
it transfers - but a reader checking it against the deposited numbers would be checking a horizon that does not
exist there. Both horizons are reproduced below.

---

## 1. The reproduction at `T4`, as the root stated it

Cell `C1` = `L1`/`N`, `N_max = 1,000`, finalization tick 1,200. Four blocks, all with first reveal equal to full
reveal (`f = d`, which has probability `1/(d+1) > 0` under PROTOCOL 4.3), built through the frozen `vgen` code path
rather than by hand:

| enrollment positions | atom | `Z` | `D` | full-reveal tick | offset `d` |
|---|---|---:|---:|---|---|
| 1-500 | `BB0` | 0 | 0 | at enrollment | 0 (SHORT) |
| 501-600 | `C>I` | +1 | +1 | 1,010 | 410-509 (LONG) |
| 601-700 | `I>C` | -1 | -1 | 1,100 | 400-499 (LONG) |
| 701-1,000 | `BB0` | 0 | 0 | 1,200 | 200-499 (LONG) |

Reachability, checked rather than asserted: every long offset used lies in 200-509, inside `LONG`'s 100-699 support
(the root said "200 to 509"; the script prints `200-509`); every short offset is inside 0-19; all three atoms carry
positive weight under `L1` (`BB0` 500, `C>I` 1,500, `I>C` 1,500 out of 10,000). The realized path sums to
`sum Z = 0` and `sum D = 0` against the truth `mu_h = mu_s = 0`.

**What the frozen runner sees.** `vrun.evaluate_trial` on this trial returns, for all three constructions,
`NO_DECISION`, `ever_miscover_h = False`, `ever_miscover_s = False`.

**What the all-triggers rule sees.** At tick 1,010 both baselines stand at index 600 with score mean `1/6`:

```
index   = 600
mean_h  = 0.166666666667
r(600)  = 0.153363950255          <- the root printed .153363950255
L_h     = +0.013302716411         <- the root printed +.013302716411
U_h     = +0.320030616922
L_s     = +0.013302716411
DEPLOY = True   RETAIN = False   miscover_h = True   miscover_s = True
```

`L_h > 0` and `L_s > -0.03` hold at the same look, so the deploy gate fires; `mu_h = 0 < L_h`, so the hierarchy
band excludes the truth; the same for success. The condition then holds at **90 of the 199 drain ticks**, from 1,010
until the `-1` block lands at 1,100. At the finalization tick 1,200 every pair is resolved, the mean is back to
zero, and both bands contain the truth. **The reduction sees none of it.** Every digit the review printed is
reproduced; nothing in its section 2 had to be corrected.

## 2. The same construction at `T1`, the horizon that actually ran

`N_max = 2,000`, finalization tick 2,200. The block sizes have to change, because the radius falls with the index
and 100 favourable pairs in 1,600 no longer clear it: 1-1,400 `BB0`, 1,401-1,600 `C>I`, 1,601-1,800 `I>C`,
1,801-2,000 `BB0`, resolving at enrollment / 2,010 / 2,100 / 2,200. Long offsets 200-609, all inside support.

```
tick 2,010:  index = 1,600   mean_h = 0.125000000000   r(1600) = 0.092854165010
             L_h = +0.032145834990   L_s = +0.032145834990   DEPLOY = True
             hierarchy and success both miscover;  90 of 199 drain ticks fire
reduced schedule:  NO_DECISION, no miscoverage, for all three constructions
```

The defect is therefore live at the horizon the deposited results were produced at, not only at the horizon the
review used.

## 3. Why it fails for the baselines and not for the adapter

**The mechanism, stated exactly, because it bounds the defect.** `CPREFIX`'s band is a function of `k` alone and
`NAIVE`'s of the completed set alone; **neither depends on the enrolled prefix `n`**. Between the end of tick `t`
and the end of tick `t+1` the only thing that can change either is a resolution. So the states those two
constructions can ever occupy are exactly the prefixes of the completion order, and the reduction keeps the
end-of-tick state at ticks `1..N_max` plus the state at tick `N_max + W`. The looks it drops are therefore exactly:

1. **the interior of the drain**, ticks `N_max+1 .. N_max+W-1` (2,001-2,199 here), where completions keep arriving
   while the enrolled prefix is pinned at `N_max` and the reduction takes no look at all; and
2. **intra-tick intermediate states**, when several pairs complete at one tick and the all-triggers rule is read
   one event at a time rather than batched.

Nothing else is missing. That is the whole of it, and the second item is precisely the "atomic batching / tie order
for simultaneous events" the review asks to be frozen - the protocol does not fix it, so both readings are
reported below and neither is asserted to be the right one.

**The adapter is different, and the protocol's argument for it is sound.** At a fixed prefix `n` the adapter's
denominator and radius are frozen and each pair's enclosure can only be replaced by a subinterval of itself, so
`sum(lower)` is nondecreasing and `sum(upper)` nonincreasing over the looks that share that prefix. `L_h`, `L_s`
are then nondecreasing and `U_h` nonincreasing, so `mu < L` and `mu > U` and `L_h > 0` and `L_s > -delta` and
`U_h < 0` all persist to the last look at that prefix. The last look at prefix `N_max` **is** the finalization look,
so the drain cannot hide anything from the adapter. Checked rather than trusted, over every drain tick of
500 programs x 4 trials x 8 cells:

```
TOTAL 16,000 trials, 0 non-monotone, 0 adapter events at a drain tick that the
finalization look does not also carry
```

and on the witness trial itself (`L_h` climbs -0.383230443864 -> -0.083230443864 across the drain, `U_h` falls
+0.383230443864 -> +0.083230443864, monotonically).

## 4. The exact list of affected numbers

`vlastlook_check.py --part grid` re-derives every trial of the reported grid from its own seed coordinates and
evaluates three schedules on each: `reduced` (the frozen one), `all_ticks` (`reduced` + every drain tick, the
batched reading), `finest` (+ every distinct completion-index state, the one-event-at-a-time reading, with
enrollment-position tie order).

**The harness is the frozen arithmetic, not a paraphrase of it.** Its `reduced` column was checked against the
deposited CSVs: **384 deposited `(x, N)` pairs re-derived, 0 mismatches**, covering every `ever_miscover` /
`ever_below` / `ever_above` row of `miscoverage.csv` and the `deploy`, `retain_incumbent`, `no_decision`,
`conflict`, `decided_at_finalization`, `false_deploy`, `false_harm`, `any_erroneous_trial`, `family_any_erroneous`
and `never_conjunct` rows of `decisions.csv`.

**The added looks are live, not vacuous** (a zero here would make a "nothing moves" verdict worthless): the drain
adds 1,592,000-3,980,000 baseline looks per cell, and in `C4` alone a drain look fires a `NAIVE` decision in 4,893
trials and miscovers in 4,893 - they simply were not *new* events in most trials.

### 4.1 `results/live_ab_validation/miscoverage.csv`

Columns affected: `x`, and `rate`, `wilson_lo`, `wilson_hi` derived from it. `flagged` never changes (section 5).
`ADAPTER` rows: **none affected.** Direction: **every one is understated** in the deposited file.

| cell | constr | gate | event (rows `all` and `decision_eligible`) | deposited | + drain ticks | + finest |
|---|---|---|---|---:|---:|---:|
| `C1` | `CPREFIX` | hierarchy | `ever_miscover` | 2 | 2 | **3** |
| `C1` | `CPREFIX` | hierarchy | `ever_above` | 1 | 1 | **2** |
| `C2` | `NAIVE` | hierarchy | `ever_miscover`, `ever_below` | 7,910 | 7,910 | **7,913** |
| `C3` | `CPREFIX` | hierarchy | `ever_miscover` | 11 | **12** | **20** |
| `C3` | `CPREFIX` | hierarchy | `ever_below` | 2 | 2 | **7** |
| `C3` | `CPREFIX` | hierarchy | `ever_above` | 9 | **10** | **13** |
| `C3` | `NAIVE` | hierarchy | `ever_miscover` | 23 | 23 | **24** |
| `C3` | `NAIVE` | hierarchy | `ever_below` | 11 | 11 | **12** |
| `C4` | `CPREFIX` | hierarchy | `ever_miscover` | 14 | 14 | **22** |
| `C4` | `CPREFIX` | hierarchy | `ever_below` | 10 | 10 | **13** |
| `C4` | `CPREFIX` | hierarchy | `ever_above` | 4 | 4 | **9** |
| `C4` | `NAIVE` | success | `ever_miscover`, `ever_below` | 126 | 126 | **128** |
| `C5` | `CPREFIX` | hierarchy | `ever_miscover` | 1 | 1 | **2** |
| `C5` | `CPREFIX` | hierarchy | `ever_above` | 0 | 0 | **1** |
| `C6` | `CPREFIX` | hierarchy | `ever_miscover`, `ever_above` | 0 | 0 | **4** |
| `C6` | `NAIVE` | hierarchy | `ever_miscover`, `ever_below` | 16,272 | 16,272 | **16,304** |
| `C8` | `CPREFIX` | hierarchy | `ever_miscover`, `ever_above` | 0 | 0 | **1** |
| `C8` | `NAIVE` | hierarchy | `ever_miscover`, `ever_below` | 5,550 | 5,550 | **5,566** |

The `decision_eligible` variant of each `ever_miscover` row moves by exactly the same amount (every added look has
index >= `n_min = 100`).

Worked example of the effect on the printed interval, `C3`/`CPREFIX`/hierarchy/`ever_miscover`, `N = 20,000`:
deposited `11`, rate 0.000550, `[0.000307, 0.000985]`; batched `12`, rate 0.000600, `[0.000343, 0.001049]`; finest
`20`, rate 0.001000, `[0.000647, 0.001544]`. Nominal 0.00625 throughout: unflagged in all three.

### 4.2 `results/live_ab_validation/decisions.csv`

| cell | constr | quantity | deposited | + drain ticks | + finest |
|---|---|---|---:|---:|---:|
| `C1` | `CPREFIX` | `decided_at_finalization` | 1 | **0** | **0** |
| `C1` | `CPREFIX` | `retain_incumbent`, `false_harm`, `any_erroneous_trial` | 1 | 1 | **2** |
| `C1` | `CPREFIX` | `no_decision` | 7,999 | 7,999 | **7,998** |
| `C1` | `CPREFIX` | `family_any_erroneous` (`N` = 2,000) | 1 | 1 | **2** |
| `C2` | `NAIVE` | `never_conjunct` | 4 | **5** | **5** |
| `C2` | `NAIVE` | `deploy`, `false_deploy`, `any_erroneous_trial` | 404 | 404 | **406** |
| `C2` | `NAIVE` | `no_decision` | 7,596 | 7,596 | **7,594** |
| `C2` | `NAIVE` | `family_any_erroneous` (`N` = 2,000) | 376 | 376 | **378** |
| `C3` | `CPREFIX` | `decided_at_finalization` | 1 | **0** | **0** |
| `C3` | `CPREFIX` | `retain_incumbent`, `false_harm` | 9 | **10** | **13** |
| `C3` | `CPREFIX` | `deploy`, `false_deploy` | 2 | 2 | **7** |
| `C3` | `CPREFIX` | `no_decision` | 19,989 | **19,988** | **19,980** |
| `C3` | `CPREFIX` | `any_erroneous_trial` | 11 | **12** | **20** |
| `C3` | `CPREFIX` | `family_any_erroneous` (`N` = 5,000) | 11 | **12** | **20** |
| `C3` | `NAIVE` | `deploy`, `false_deploy` | 11 | 11 | **12** |
| `C3` | `NAIVE` | `no_decision` | 19,977 | 19,977 | **19,976** |
| `C3` | `NAIVE` | `any_erroneous_trial`, `family_any_erroneous` | 23 | 23 | **24** |
| `C4` | `CPREFIX` | `deploy`, `false_deploy` | 10 | 10 | **13** |
| `C4` | `CPREFIX` | `retain_incumbent`, `false_harm` | 4 | 4 | **9** |
| `C4` | `CPREFIX` | `no_decision` | 19,986 | 19,986 | **19,978** |
| `C4` | `CPREFIX` | `any_erroneous_trial`, `family_any_erroneous` | 14 | 14 | **22** |

`correct_deploy` and `conflict` do not move anywhere; `never_conjunct_all_looks` was not recomputed (it is the only
reported column outside the decision-eligible reading and its two components are not exposed by the frozen record).

**A direction caveat, stated rather than swept up.** For ever-miscoverage and for "decides at all" the reduced look
set is a *subset* of the all-triggers set, so the deposited number is a lower bound and the direction is guaranteed.
The split between `deploy` and `retain_incumbent` is **not** guaranteed monotone - an added earlier look could
pre-empt a finalization `DEPLOY` with a `RETAIN_INCUMBENT` and lower a count. Measured: **no such swap occurs
anywhere in this grid**; in every cell the increase in `deploy` plus `retain_incumbent` exactly equals the decrease
in `no_decision`. `never_conjunct` is likewise not monotone in either direction, and its one move (`C2`/`NAIVE`,
4 -> 5) happens to be upward.

### 4.3 `results/live_ab_validation/decision_time.csv`

Affected columns: `n_deciding`, `deciding_fraction`, `capped_fraction`, `conditional_q1/median/q3`, for the same
`CPREFIX`/`NAIVE` rows whose decision counts move above (`C3`/`CPREFIX` under the batched reading; `C1`, `C2`,
`C3`, `C4` baselines under the finest reading).

**`capped_q1/median/q3` do not move under the batched reading**, and this is exact rather than lucky: the summed
capped `tau` is **identical** between `reduced` and `all_ticks` in all 24 cell/construction rows. Every decision the
drain adds carries `tau = N_max = 2,000`, which is exactly the value PROTOCOL 9.5's capped rule had already assigned
that trial. So the reduction loses the *fact* of a decision there but not its *prefix*. Under the finest reading the
summed capped `tau` does fall (e.g. `C7`/`CPREFIX` 7,354,918 -> 7,322,100, `C8`/`CPREFIX` 7,324,796 -> 7,295,674),
because intra-tick states fire during enrollment, so the capped quartiles move there too - and `C7`/`C8` baselines,
which appear nowhere else in this section, are affected in this one way.

### 4.4 Files that are NOT affected

- **Every `ADAPTER` row of every file.** Not one adapter number moves under any schedule.
- **`horizon_summaries.csv`, under the batched reading.** Every fixed-horizon summary is taken at an enrollment-tick
  look and its "so far" columns range over ticks `1..h <= N_max`, all of which the reduction keeps; the drain lies
  entirely above them. *Under the finest reading the baselines' `miscover_h_so_far` / `deploy_by` / `retain_by`
  columns can move*, since added looks fire before tick 2,000 there - inferred from the `tau` drop above, not
  separately recomputed.
- **`unresolved.csv`** moves only for the handful of baseline trials whose reporting look changes from the
  finalization look to a deciding look (PROTOCOL 9.5 reports at the deciding look, or at finalization for
  non-deciders) - at most 1 trial per affected cell under the batched reading.
- **`comparison_*.csv.gz`, `comparison_summary.json`, `compute.json`, `fixtures_report.json`, `budget.json`,
  `manifest.json`.** The comparison is an agreement check between #11 and #12 at a common look set, not an operating
  characteristic, so the reduction cannot bias it; the rest are provenance and resource records.

## 5. The positive control survives, and here is why it could not have failed

PROTOCOL 9.4: *"`NAIVE`'s hierarchy ever-miscoverage must be FLAGGED in at least one of `C2`, `C4`, `C6`. If it is
not, the measurement apparatus itself is reported as unvalidated, the `ADAPTER` results of this run are reported as
uninterpretable..."*

**The argument, which needs no recomputation.** The reduced look set is a subset of the all-triggers look set, and
ever-miscoverage is a union over looks, so the deposited `x` can only rise when the missing looks are restored. `N`
is the trial count and does not change. The Wilson lower limit is increasing in `x` at fixed `N`. A row that is
flagged under the reduction is therefore flagged under any superset of it. **The defect can only ever make the
positive control fire harder.** The one way it could have mattered is the reverse direction - a row the study
reported as *unflagged* - and that is exactly what section 4.1 lists.

**The recomputation agrees:**

| schedule | `C2` | `C4` | `C6` | control |
|---|---|---|---|---|
| reduced (deposited) | 7,910/8,000, `wilson_lo` 0.986193 | 19,998/20,000, 0.999635 | 16,272/20,000, 0.808143 | PASSES |
| + drain ticks | 7,910/8,000, 0.986193 | 19,998/20,000, 0.999635 | 16,272/20,000, 0.808143 | PASSES |
| + finest | 7,913/8,000, 0.986606 | 19,998/20,000, 0.999635 | 16,304/20,000, 0.809760 | PASSES |

against a nominal of 0.00625 - a margin of 129x to 160x. And across the whole grid, over every cell, construction
and nominal-bearing quantity: **no Wilson flag changes state under any schedule.** The `ADAPTER` is unflagged
everywhere under all three; `NAIVE`'s hierarchy gate is flagged in `C2`, `C4`, `C6`, `C8` under all three.

**So ruling 56's contingency does not trigger.** The apparatus is validated, the `ADAPTER` results are
interpretable, and the qualifier on the baseline numbers is the narrower one in section 6.

## 6. What this does and does not establish

**Established.** The protocol's and `cells.json`'s claim of an *exact* reduction is false as written; it is exact
for `ADAPTER` and not for `CPREFIX` or `NAIVE`. The root's witness is correct in every particular. The defect is
structurally bounded to the drain interior plus intra-tick ordering, and every affected deposited number is a lower
bound on its all-triggers counterpart.

**Not established, and worth saying plainly.** The witness is a single path of astronomically small probability;
it refutes the *claim of exactness*, and by itself says nothing about the size of the error. The size is the
measurement in section 4, and it is small: under the batched reading, 3 of the 192 data rows of `miscoverage.csv`
and 8 of `decisions.csv`, all in cells whose rates are two to four orders of magnitude below their nominal bounds.
That is a reason to correct the claim and the numbers, not a reason to distrust the run.

**Which of the two readings is right is not decided here.** PROTOCOL 7.1 says "each further fact - a reveal, a
resolution, or an increase in a pending episode's elapsed cost", and a resolution is one pair's, so the finest
reading is arguably the more literal one and it is the larger effect. The protocol does not fix a tie order, which
is the gap the review asks to be closed. That is a coordinator ruling, not this file's call. One asymmetry is worth
recording for whoever makes it: for `CPREFIX` the finest set is a function of `k` alone and is therefore the exact
union over *every* admissible tie order, so its column is order-independent; for `NAIVE` the intra-tick partial sums
depend on the order and the column reported here is one admissible schedule, not a bound over all of them.

**Files this check wrote:** this file and `experiments/live_ab_validation/vlastlook_check.py`. No frozen value, no
deposited result, no protocol, no `cells.json` entry and no Git state was touched.
