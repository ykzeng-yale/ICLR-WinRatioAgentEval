# BUDGET_NOTE: the PROTOCOL 8.1 smoke measurement and the 8.2 tier selection

Companion to `results/live_ab_validation/budget.json` and
`results/live_ab_validation/smoke/timing.json`, which are the machine outputs of the one permitted run and
are **not** hand-edited. This note explains the measurement, the projection, and the rung the frozen ladder
selects from them.

| field | value |
|---|---|
| protocol | `PROTOCOL.md` v1-cpu-validation, sections 8.1 and 8.2, frozen |
| run | **exactly one** 20-program smoke run, namespace 1, seeds discarded |
| command | `.venv/bin/python experiments/live_ab_validation/vrun.py --smoke 20 --out results/live_ab_validation` |
| date | 2026-09-20 |
| environment | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1, macOS arm64, 10 cores, 32 GiB |
| selected tier | **T1** (the preferred rung) |
| any cap breached | **no** |
| grid started by this session | **no** — and it is additionally blocked, see section 6 |

---

## 1. What was measured, and what was deliberately not looked at

PROTOCOL 8.1 permits **one** 20-program smoke run and permits **only** seconds, bytes, memory and counts to
leave it. That is what was taken, and it was taken once. The split is the frozen one: **10 programs in `C1`
at `N_max = 2,000`** and **10 programs in `C2` at `N_max = 1,000`**, all four trials and all three
constructions, drawing from **namespace 1**, whose seeds are discarded and are never reused by the reported
grid (namespace 0).

**I did not look at the smoke run's effect comparisons.** No coverage number, no decision rate, no band
endpoint and no miscoverage flag from the smoke run was inspected, printed, or used to choose the horizon,
the tier, the cells, or anything else. That restriction is the point of the rule, so it is stated plainly
rather than implied: the only quantities I read out of the run are the seconds, bytes, memory and counts
tabulated below. This is enforced mechanically as well as by discipline —
`vrun.run_smoke` passes `accum=None` and a `discard=True` sink, so **no per-trial effect record is ever
formed**, and `assert_smoke_holds_no_effect_record` re-opens the smoke directory after the run and fails if
it holds any file other than `timing.json` or any key outside a frozen whitelist of timing, memory, byte and
count fields. Both checks passed.

**Host state.** The machine was contended when I first approached the measurement (5 CPU-saturated
sandboxed processes from an unrelated workload, load average 5.5 on 10 cores). Because the protocol allows
only one run, I waited for the churn to stop rather than spend it under contention. At the moment of the
run there were **zero** processes above 50% CPU and the decaying 1-minute load average was 3.33; the same
was true immediately after. The measurement is therefore not contention-inflated.

## 2. The measurements

| point | cell | `N_max` | programs | trials | enrolled pairs | looks | band evaluations | seconds | **s / program** |
|---|---|---|---|---|---|---|---|---|---|
| high horizon | `C1` | 2,000 | 10 | 40 | 80,000 | 80,040 | 480,240 | 0.029621 | **0.00296214** |
| low horizon | `C2` | 1,000 | 10 | 40 | 40,000 | 40,040 | 240,240 | 0.019145 | **0.00191453** |

| quantity | measured |
|---|---|
| **peak RSS** (`ru_maxrss`, RUSAGE_SELF) | **73,957,376 B = 70.53 MiB** |
| record bytes (gzip, measured not written) | 2,638 B over 20 programs = **131.9 B / program** |
| total smoke wall clock | 0.048767 s |
| **measured scaling exponent `beta`** | **0.62965** |
| enclosure updates per pair (max over points) | **2.8869**, against the logical bound of 5 |

`beta = log(s_2000 / s_1000) / log 2 = 0.6297`. PROTOCOL 8.1 requires this to be **measured, not assumed**,
because a recompute-the-sum-per-look implementation would be quadratic in `N_max` (`beta` near 2) and would
misprice the `T4` row. The measured `beta` is **below 1**, and the independent operation counter agrees:
2.89 enclosure updates per pair, i.e. each pair's enclosure changes about three times over the whole trial
(enroll, reveal, the cost thresholds, resolve) rather than once per look. `assert_incremental` passed. The
band is maintained incrementally, as 8.1 requires.

## 3. The projection, against the three frozen caps

Using the frozen formulas of 8.1 exactly as written —
`seconds = s_2000 * programs_total * (N_max_tier / 2000)**beta`,
`bytes = (smoke_bytes / 20) * programs_total`,
`peak_rss = smoke_peak_rss`:

| tier | grid | programs | `N_max` | seconds (cap 5,400) | output (cap 200 MiB) | peak RSS (cap 2 GiB) | admissible |
|---|---|---|---|---|---|---|---|
| **T1** | `C3`-`C6` at 5,000; `C1`,`C2`,`C7`,`C8` at 2,000 | 28,000 | 2,000 | **82.94 s** | **3.52 MiB** | **70.53 MiB** | **yes** |
| T2 | all eight at 2,000 | 16,000 | 2,000 | 47.39 s | 2.01 MiB | 70.53 MiB | yes |
| T3 | all eight at 1,000 | 8,000 | 2,000 | 23.70 s | 1.01 MiB | 70.53 MiB | yes |
| T4 | all eight at 1,000, `N_max = 1,000` | 8,000 | 1,000 | 15.32 s | 1.01 MiB | 70.53 MiB | yes |

**Selection rule (8.2): the highest tier satisfying all three limits. Every rung is admissible, so the
ladder selects `T1`** — the preferred rung, which carries the precommitted escalation to 5,000 programs in
the four boundary/delay cells `C3`, `C4`, `C5`, `C6`.

Headroom at `T1`: **65x** on wall clock, **57x** on output bytes, **29x** on memory. **No cap is breached,
so the pause-and-report branch of 8.2 does not fire** and no reduced fixed grid is required. Nothing was
shrunk, no cell was dropped, and the number of constructions is unchanged at three.

At `T1` the reported grid is 112,000 trials, 224,000,000 enrolled pairs, 224,112,000 looks and
1,344,672,000 band evaluations.

## 4. Where the frozen formulas understate, priced rather than hidden

Two of the three frozen projection formulas are optimistic. Neither changes the selected tier, and both are
bounded here in closed form rather than left for a reader to discover.

1. **The peak-RSS formula understates, because the smoke run allocates no accumulator.** 8.1 says
   `peak_rss_projected = smoke_peak_rss` on the grounds that the run is batched. That is right about the
   per-trial path — records stream to a gzip sink and no per-look path is ever held — but `run_smoke` passes
   `accum=None`, so the smoke run never allocates the `CellAccumulator` arrays that the reported grid
   allocates one cell at a time. Measured directly from the array shapes: **22.89 MiB** for a 5,000-program
   cell (20,000 trials) and 9.16 MiB for a 2,000-program cell. The accumulator is freed between cells, so
   the true worst-case grid peak is **70.53 + 22.89 = 93.42 MiB against a 2,048 MiB cap — still 22x of
   headroom**. The conclusion is unchanged; the formula's gap is recorded because a projection that
   structurally omits a term should say so.
2. **The bytes formula is conservative, in the safe direction.** Gzip's ratio improves with volume (a warm
   dictionary, an amortized header), so scaling 2,638 bytes from 20 programs linearly to 28,000
   **over**-estimates the real output. The projected 3.52 MiB is an upper bound, not an estimate.
3. **`beta` is timer-noise-dominated, and it does not matter here.** The two points are 30 ms and 19 ms, so
   fixed per-trial overhead, not per-look work, dominates both, and `beta = 0.63` should not be read as a
   precise complexity exponent. It is load-bearing for exactly one row: `(N_max_tier / 2000)**beta` equals 1
   for `T1`, `T2` and `T3`, which all run at `N_max = 2,000`, so **`beta` can only move the `T4` projection
   and cannot change a selection in which every rung is admissible.** The property 8.1 actually needs from
   it — that the implementation is not quadratic — is established independently by the operation counter.
4. **Runtime is not exactly cell-independent.** PROTOCOL 2.4 argues it is close to cell-independent because
   every trial runs to tick 2,200 whatever it decides. The residual dependence is that `_look_fractions` is
   cached per look, so a cell whose three constructions decide at three different looks pays up to three
   resolution passes per trial instead of one. The smoke cells `C1`/`C2` are near-abstaining, so they sit at
   the cheap end. The effect is bounded by a small constant factor and is irrelevant against 65x headroom.

## 5. What this measurement does not establish

It is a measurement of seconds, bytes and memory. It establishes nothing about coverage, decisions, the
adapter, the positive control, or the agreement with the pinned #11 monitor, and no such quantity was
looked at. The tier selection is an output of a rule the protocol fixes (section 14), not a change to the
protocol.

## 6. BLOCKER: the reported grid must not start yet

`budget.json` records `grid_may_start: false`. The budget is not the reason — every rung is admissible. The
reason is the **fixture gate**, which is now at **17/18**:

```
FAIL F15_protocol_config_agreement
       13.0 vgen.py is listed as not written but exists
       13.0 vrun.py is listed as not written but exists
       13.0 vcompare.py is listed as not written but exists
```

This is a defect in the fixture, not in the pre-registration, and it is not something this session may
repair on its own initiative:

- PROTOCOL 13.0 says "**As of the freeze commit**, `vgen.py`, `vrun.py`, `vcompare.py` and `REPORT.md` do
  not exist. This section specifies them." That is a statement about the freeze commit and stays true.
- `cells.json` carries them under the key
  `modules.specified_here_but_do_not_exist_at_the_freeze_commit` — a key whose own name scopes it to the
  freeze commit.
- `F15` nevertheless reads it as a **live invariant on the working tree**: it fails if any file listed there
  exists on disk. So the fixture fails the moment anyone writes the four modules the protocol instructs them
  to write, which makes the specified deliverables unreachable through a passing gate.

`PROTOCOL.md` and `cells.json` are frozen and were not touched. `vfixtures.py` is a committed file that this
session does not own, so `F15` was **not** edited either: the failure is reported, not repaired. This is the
same shape of finding the study's own audits have twice recorded (a gate that asserts the wrong thing), and
it is left for the coordinator to adjudicate.

**What changed in `vrun.py`, and why it is not an exemption.** The gate is still fail-closed for the
reported grid and carries no exemption for any case: `vrun.py` raises `SystemExit` immediately before the
grid draws its first namespace-0 stream if any fixture case failed. What it no longer does is abort *before*
the measurement-only steps, because PROTOCOL 8.2 requires `budget.json` to exist **before** the grid starts,
and the smoke run produces no reported quantity. No failing case can let the grid run;
`budget.json` records the gate as closed, names the failing case, and carries an empty `exemptions` list.

**Sequence the coordinator needs:** adjudicate `F15` -> gate returns to 18/18 -> then start the reported
grid at `T1`. The tier selection above is already frozen in `budget.json` and does not need to be recomputed;
the one permitted smoke run has been spent.

## 7. One coordination point on the canonical command

PROTOCOL 13.1's single reproducible command,
`.venv/bin/python experiments/live_ab_validation/vrun.py --out results/live_ab_validation`, runs the whole
sequence in one shot: fixture gate -> smoke -> `budget.json` -> grid. It therefore **re-takes the 8.1
measurement and overwrites the `budget.json` deposited here** before it starts the grid, which is what 8.2's
"written before the reported grid starts" asks for. Flagged so that nobody reads the overwrite as a second
bite at the tier:

- the re-measurement is a timing measurement only, on the same discarded namespace-1 seeds, and no effect
  column is formed or read in it either;
- at 65x headroom the selection is not close, so a re-measurement will select `T1` unless the host is
  roughly 65x slower than it was here;
- if a future re-measurement ever selected a **different** tier, that is a material discrepancy and should
  be reported under 12.3 rather than silently accepted, with this note's numbers as the comparison point.

The copy of `budget.json` deposited by this session is the deliverable of 13.3 item 7 — "measured smoke-run
seconds, peak memory and projected CPU time, deposited in `budget.json` **before** full execution".
