# RESOURCE_CHECK: the balanced 20-program check for the amended all-look runner

Root disposition `reviews/cpu_v1_delivery_root_disposition.md` section C keeps the v1 smoke receipts but rules
that their `C1`/2,000 versus `C2`/1,000 comparison **confounds cell with horizon**, and specifies the
replacement: a balanced 20-program check over `C1` and `C2` crossed with horizons 1,000 and 2,000, five
programs per group, for the **amended all-look runner**. This file is that check.

| field | value |
|---|---|
| authority | `reviews/cpu_v1_delivery_root_disposition.md` section C; schedule requirement from section B; coordinator `COORDINATOR_DECISIONS.md` revision 14 ruling 68 |
| script | `experiments/live_ab_validation/vresource_check.py` (writes only under `results/live_ab_validation_v2/resource_check/`) |
| receipts | `results/live_ab_validation_v2/resource_check/balanced_timing.json`, `balanced_analysis.json` |
| measured bytes | pinned commit **`db930d7dc3bac0ae1644170433f769b5d3875e84`**, exported read-only with `git archive`; `vgen.py` `2d0e2756…`, `vrun.py` `8b735cfe…`, `vband.py` `55a9894f…`, `cells.json` `96ebf7e4…`, `src/winstats.py` `56955ce0…` |
| design | balanced 2 x 2: `C1`, `C2` x `N_max` 1,000, 2,000; **5 programs per group, 20 programs total**; 4 trials per program; all three constructions |
| coordinates | namespace **1** (resource namespace: seeds discarded, never reused in any reported grid), program indices **1000-1004**, disjoint from the v1 smoke's 0-9 |
| replication | 8 outer repetitions, each group in its **own subprocess**, x 20 inner repetitions; 96 subprocess measurements; the same 20 programs throughout, never a twenty-first |
| environment | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1, macOS 26.5.2, arm64, 10 cores. CPU only; no model call, no API call, no network, no new dependency |
| harness wall clock | 44.5 s for the whole check |
| what left the measurement | seconds, peak resident memory, bytes and counts, and nothing else: `assert_resource_only` walks every emitted record and aborts on any key that is not a timing, memory, byte or count field |

**The v1 smoke receipts are untouched.** `results/live_ab_validation/smoke/timing.json` and
`results/live_ab_validation/budget.json` are read here and reported beside these numbers; nothing under
`results/live_ab_validation/` is edited, moved or overwritten. This check deposits into a **new** directory,
`results/live_ab_validation_v2/resource_check/`, under PROTOCOL section 14's versioned-amendment rule.

**No grid was run.** Twenty programs, plus deterministic fixtures and witnesses. Nothing here is clearance for
a re-run.

---

## 0. Verdict, in the terms the root asked for

**No. The corrected all-look schedule does not cost materially more than v1's sampled schedule.** Under the
batched declaration it costs **slightly less**: a paired factor of **x0.943, 95% CI [0.938, 0.949]** over 32
paired group-repetitions, despite taking 10-20% more looks per trial. Under the strictest one-event-at-a-time
declaration it costs **x1.911, 95% CI [1.880, 1.943]** - about double, and still 31x inside the runtime cap.

| question the root asked | answer |
|---|---|
| does the corrected schedule cost materially more? | **No.** Batched: **x0.943 [0.938, 0.949]**, i.e. 5.7% *cheaper*. Finest: **x1.911 [1.880, 1.943]**. Both are paired on identical seed coordinates; the interval is 1.96 SEM over 32 paired observations, not a point estimate. |
| why can adding looks make it cheaper? | v1 buys its finalization look with a **separate `O(N_max)` `state_at_age` call**; the amended schedule gets the whole drain window by extending `adapter_prefix_sums`' difference array along the tick axis, which is `O(W)` and returns the finalization state for free. The extra looks are cheaper than the call they replace. |
| marginal effect of **cell**, now that the design is balanced | **+0.0093 +- 0.0057** in log seconds per program (x**1.0094**), 95% CI [-0.0019, +0.0205] - **not separable from zero**. |
| marginal effect of **horizon** | **+0.4053 +- 0.0054** (x**1.4997**), 95% CI [+0.3948, +0.4158] - large and precisely measured. |
| does the projection breach a cap? | **No cap is breached, at any tier, for any of the three schedules.** The amended batched runner projects **76.9 s** at `T1` against a **5,400 s** cap (1.4%), 4.83 MiB against 200 MiB, 69.8 MiB peak against 2.0 GiB. Nothing is paused and the study is **not** shrunk. |
| did the confounded v1 ratio change anything? | **No, and this is exact rather than reassuring.** `T1`'s projection is `s_2000 * programs * (2000/2000)**beta`, in which **beta does not appear**. `beta` could only have mattered had `T1`, `T2` and `T3` all breached and `T4` been the candidate. The confound was a real measurement defect; it was not a decision defect. |

---

## 1. What the v1 smoke measured, and exactly why it cannot attribute cost

PROTOCOL 8.1 ran ten programs in `C1` at `N_max = 2,000` and ten in `C2` at `N_max = 1,000`, and estimated the
scaling exponent from their ratio. Those two deposited points are:

```
smoke/timing.json   C1 / N_max 2000   10 programs   0.028764417 s   2.8764 ms/program
                    C2 / N_max 1000   10 programs   0.018746709 s   1.8747 ms/program
budget.json         beta = log(s_2000 / s_1000) / log 2 = 0.6176479350549632
```

Write the four cells of the balanced design as `y(c, h) = log s(c, h)`, with the cell effect
`A = mean_h[y(C2,h) - y(C1,h)]` and the horizon effect `B = mean_c[y(c,2000) - y(c,1000)]`. The single v1
contrast is

```
log( s(C1,2000) / s(C2,1000) )  =  B - A
```

so the deposited `beta` is `(B - A) / log 2`, not `B / log 2`. **It is the horizon effect minus the cell effect,
and one number cannot be split into two.** That is the defect, stated as an identity rather than as a
suspicion. The script computes this same confounded contrast from the balanced data so the two designs can be
compared on equal footing (section 5).

`C1` and `C2` **share the outcome law** `L1` and differ only in the delay rule (`N` versus `A`), by PROTOCOL
8.1's own cell-choice reasoning. So what this balanced design separates from horizon is the **delay-rule**
effect. It does not measure the outcome-law effect; see section 8.

---

## 2. What "the amended all-look runner" is here, and what it is not

Disposition section B requires the v2 runner to (1) declare the legal event schedule and its simultaneous-event
batching, (2) include **every** required completion-index change through the fixed finalization window, and
(3) record **both** the enrollment prefix **and** the elapsed decision time as separate quantities.

**The v2 runner has not been written.** What is costed here is a faithful implementation of the two candidate
*declarations* on the frozen `vgen`/`vrun` arithmetic, so that the coordinator can choose the declaration on
the science rather than have the budget choose it. All three arms below record `tau` (enrollment prefix) and
`tau_tick` (elapsed decision time) as separate columns, so requirement (3)'s byte cost is measured rather than
assumed.

| arm | schedule | looks per trial per construction |
|---|---|---|
| `v1_reduced` | the v1 reduced schedule: one look per enrollment prefix plus the finalization look | `N_max + 1` |
| `v2_all_ticks` | **batched declaration**: every tick `1 .. N_max + W`, all three constructions, simultaneous events batched to the end of their tick | `N_max + W` |
| `v2_finest` | **one-event-at-a-time declaration**: `v2_all_ticks` plus every distinct intra-tick state - every completion-index change of `CPREFIX` and `NAIVE`, and every enclosure change of the `ADAPTER` - in enrollment-position tie order | ~`2.63 x (N_max + 1)` |

Two properties of the arms matter for reading the factor:

- **`v1_reduced` is the v1 SCHEDULE on the current enclosure arithmetic**, at pinned commit `db930d7`, which
  already carries the item-5 completion of coordinator revision 13. It is **not** the deposited v1 binary at
  `02b9410`, and its milliseconds must **not** be differenced against the deposited smoke receipts: different
  bytes, different machine, different program indices. Holding the enclosure rule fixed across arms is
  deliberate - it is what isolates the *schedule's* cost, which is the question.
- **`v2_finest` is measured as a strict superset** (all ticks **union** all distinct intra-tick states), so
  duplicated states are timed. Its cost is therefore an **upper bound** on a non-redundant implementation of
  that declaration, not a tight estimate.

---

## 3. The amended arms are v1 plus looks, and they see the crossing v1 omits

A cost ratio between two programs means nothing unless they are doing the same arithmetic on different
schedules. Both checks below are deterministic and run before any timing
(`vresource_check.py --part check`).

**(a) Identity on the shared looks.** For every construction of 24 trials across `C1` and `C2` at
`N_max = 1,000`, the amended tick schedule restricted to `tick <= N_max` plus the finalization tick reproduces
`vrun.build_series`' own `L_h`, `U_h`, `L_s`, `U_s` and index arrays **bit for bit**, and the incremental
update count is unchanged:

```
amended == v1 on the shared looks: 24 trials, True
```

**(b) The root's open witness fires.** Disposition section B's missed crossing, rebuilt through the frozen
`vlastlook_check.build_witness` code path at horizon 1,000:

| construction | deposited v1 runner | amended schedule |
|---|---|---|
| `CPREFIX` | `NO_DECISION`, `ever_miscover_h = False` | **`DEPLOY`**, `ever_miscover_h = True`, **prefix 1,000**, **elapsed tick 1,010** |
| `NAIVE` | `NO_DECISION`, `ever_miscover_h = False` | **`DEPLOY`**, `ever_miscover_h = True`, **prefix 1,000**, **elapsed tick 1,010** |

```
index at tick 1010 = 600   L_h = 0.0133027164   L_s = 0.0133027164   (both baselines)
```

Every digit the root printed is reproduced, and the two quantities disposition B asks to be separated **are**
separated: the prefix is 1,000 and the elapsed decision time is 1,010. The thing being costed is the thing
that repairs the defect.

---

## 4. Measured seconds and peak resident memory, per cell and per horizon

Milliseconds per program; `+-` is one standard error over the 8 outer repetitions. Peak RSS is the
**subprocess's own** high-water mark: `getrusage` never falls, so a group can only own a memory number if it
owns a process, and each group therefore runs in its own subprocess, in a rotated order so that no group sits
in a fixed position.

### 4.1 `v1_reduced` (the v1 schedule)

| group | ms/program | peak RSS | looks/trial | bytes/program |
|---|---:|---:|---:|---:|
| `C1`/1,000 | 1.9224 +- 0.0117 | 68.83 MiB | 3,003 | 166.0 |
| `C1`/2,000 | 2.8988 +- 0.0130 | 69.25 MiB | 6,003 | 168.4 |
| `C2`/1,000 | 1.9511 +- 0.0103 | 68.81 MiB | 3,003 | 192.0 |
| `C2`/2,000 | 2.9099 +- 0.0152 | 69.29 MiB | 6,003 | 181.8 |

### 4.2 `v2_all_ticks` (batched declaration)

| group | ms/program | peak RSS | looks/trial | bytes/program |
|---|---:|---:|---:|---:|
| `C1`/1,000 | 1.8171 +- 0.0072 | 68.83 MiB | 3,600 | 170.4 |
| `C1`/2,000 | 2.7303 +- 0.0063 | 69.58 MiB | 6,600 | 171.4 |
| `C2`/1,000 | 1.8275 +- 0.0022 | 68.93 MiB | 3,600 | 196.2 |
| `C2`/2,000 | 2.7620 +- 0.0112 | 69.84 MiB | 6,600 | 184.8 |

### 4.3 `v2_finest` (one-event-at-a-time declaration)

| group | ms/program | peak RSS | looks/trial | bytes/program |
|---|---:|---:|---:|---:|
| `C1`/1,000 | 3.5402 +- 0.0311 | 70.72 MiB | 7,915.45 | 170.4 |
| `C1`/2,000 | 5.7933 +- 0.0275 | 70.96 MiB | 15,806.75 | 171.4 |
| `C2`/1,000 | 3.5506 +- 0.0128 | 70.65 MiB | 7,910.05 | 196.2 |
| `C2`/2,000 | 5.7971 +- 0.0232 | 70.59 MiB | 15,763.90 | 184.8 |

**Memory is flat.** The spread across all twelve group-by-arm cells is 68.81 to 70.96 MiB - a range of 2.15
MiB, of which ~2 MiB is the finest arm's extra event arrays. Against the 2.0 GiB cap that is 3.4% at worst.
The run is batched and nothing is held per-trial, so peak does not grow with the grid; that is PROTOCOL 8.1's
own projection rule and this check does not disturb it.

**Bytes.** The two columns disposition B requires (`tau_tick`, `look_tick`) cost **+2.1%** of the compressed
per-trial record stream: a 4-group mean of 177.05 bytes/program for v1's header against 180.70 for the amended
header.

---

## 5. The marginal effects, separated

All effects are on **log seconds per program**, estimated per repetition from the four balanced cells and then
averaged over the 8 repetitions; `+-` is one standard error over repetitions.

| arm | cell (`C2` - `C1`) | horizon (2,000 - 1,000) | interaction |
|---|---|---|---|
| `v1_reduced` | **+0.0093 +- 0.0057**  (x1.0094)  CI [-0.0019, +0.0205] | **+0.4053 +- 0.0054**  (x1.4997)  CI [+0.3948, +0.4158] | -0.0110 +- 0.0087 |
| `v2_all_ticks` | **+0.0087 +- 0.0036**  (x1.0087)  CI [+0.0016, +0.0157] | **+0.4101 +- 0.0024**  (x1.5069)  CI [+0.4053, +0.4148] | +0.0057 +- 0.0055 |
| `v2_finest` | **+0.0019 +- 0.0045**  (x1.0019)  CI [-0.0070, +0.0108] | **+0.4915 +- 0.0034**  (x1.6347)  CI [+0.4848, +0.4981] | -0.0025 +- 0.0143 |

**The separation is the deliverable.** Cost is driven by horizon, by a factor of about **1.50** per doubling
under either v1's or the batched schedule and about **1.63** under the finest one. Cell - here specifically
the **delay rule** at law `L1` - moves cost by **under 1%**, and under two of the three arms its interval
covers zero. Interaction is negligible under all three, so the two-factor reading is adequate.

### 5.1 The scaling exponent, balanced against confounded

| arm | `beta` **balanced** = horizon effect / log 2 | `beta` **v1-style confounded** = (horizon - cell) / log 2 |
|---|---|---|
| `v1_reduced` | **0.5847 +- 0.0077**  [0.5695, 0.5998] | 0.5712 +- 0.0096 |
| `v2_all_ticks` | **0.5916 +- 0.0035**  [0.5848, 0.5985] | 0.5791 +- 0.0041 |
| `v2_finest` | **0.7090 +- 0.0049**  [0.6994, 0.7187] | 0.7063 +- 0.0079 |

The confounded contrast is **biased low by exactly the cell effect over log 2**: 0.5847 - 0.5712 = 0.0135, and
0.0093 / log 2 = 0.0134. That is the systematic part, and the balanced design removes it.

The deposited `beta = 0.6177` differs from this check's confounded contrast (0.5712) by 0.047, which is **more
than the confound accounts for**. The arithmetic locates the remainder without speculation: the deposited
`C1`/2,000 point (2.8764 ms) agrees with this check's (2.8988 ms) to 0.8%, while the deposited `C2`/1,000 point
(1.8747 ms) is 3.9% faster than this check's (1.9511 ms), and `log(1.039)/log 2 = 0.055` covers the gap. **The
deposited beta was a single unreplicated measurement with no error bar**; it carried both a systematic error the
balanced design removes and a sampling error only replication removes. This is a statement about one
measurement's precision, not a claim that the v1 receipt is wrong, and the receipt stands as deposited.

**And it changed nothing.** `T1`'s projection is `s_2000 * programs_total * (2000/2000)**beta`, in which the
exponent cancels. `beta` enters only the `T4` row. `T1` was admissible by a wide margin, so `beta` was never
on the path to the tier decision.

---

## 6. The cost of the corrected schedule, paired on identical coordinates

Each factor is the ratio of amended to v1 seconds per program **at the same cell, horizon and repetition**, so
ambient machine load is differenced out. Intervals are `exp` of the mean `+- 1.96 SEM` of the log ratio over
`4 groups x 8 repetitions = 32` paired observations.

| arm | factor vs `v1_reduced` | 95% CI | `N_max` = 1,000 | `N_max` = 2,000 | looks/trial vs v1 |
|---|---:|---|---:|---:|---|
| `v2_all_ticks` | **x0.943** | [0.938, 0.949] | x0.941 [0.932, 0.951] | x0.946 [0.939, 0.952] | x1.199 at 1,000; x1.099 at 2,000 |
| `v2_finest` | **x1.911** | [1.880, 1.943] | x1.831 [1.814, 1.847] | x1.995 [1.976, 2.015] | x2.63 at both |

log-ratio dispersion: `v2_all_ticks` sd 0.0173, sem 0.0031; `v2_finest` sd 0.0477, sem 0.0084 (n = 32).

**Read plainly.** The batched correction is **free**: it evaluates 10-20% more looks and finishes 5.7%
sooner, because extending the difference array's tick axis through the drain is `O(W)` and supersedes v1's
separate `O(N_max)` `state_at_age` call for the finalization state. The strictest declaration roughly
**doubles** cost, rising with horizon (x1.83 at 1,000, x2.00 at 2,000) because the number of distinct
intra-tick states grows with the number of enrolled pairs. Neither is anywhere near a budget constraint, so
**the choice between the batched and the finest declaration is free to be made on the science.** That is the
practical finding.

---

## 7. Projection against PROTOCOL 8.2's caps

Caps: **5,400 s**, **2.0 GiB** peak RSS, **200 MiB** output. Projection formula unchanged from PROTOCOL 8.1:
`seconds = s_2000 * programs_total * (N_max_tier / 2000)**beta`, with `s_2000` the **balanced** mean over `C1`
and `C2` and `beta` the **balanced** exponent of section 5.1.

| arm | `s_2000` | `beta` | `T1` 28,000 | `T2` 16,000 | `T3` 8,000 | `T4` 8,000 @1,000 |
|---|---:|---:|---:|---:|---:|---:|
| `v1_reduced` | 2.9044 ms | 0.5847 | **81.3 s** | 46.5 s | 23.2 s | 15.5 s |
| `v2_all_ticks` | 2.7461 ms | 0.5916 | **76.9 s** | 43.9 s | 22.0 s | 14.6 s |
| `v2_finest` | 5.7952 ms | 0.7090 | **162.3 s** | 92.7 s | 46.4 s | 28.4 s |

`T1` detail for the amended arms, with every allowance stacked:

| quantity | `v2_all_ticks` | `v2_finest` | cap | worst-case share of cap |
|---|---:|---:|---:|---:|
| seconds, balanced point | 76.9 | 162.3 | 5,400 | |
| seconds, upper 95% on `s_2000` | 77.2 | 163.3 | | |
| seconds, slower measured cell | 77.3 | 162.3 | | |
| seconds, slower cell **x1.020 worst-cell envelope** (section 8) | 78.9 | 165.6 | | |
| seconds, that **x1.073 v1 calibration** (below) | 84.7 | 177.7 | 5,400 | **3.3%** |
| output bytes | 4.83 MiB | 4.83 MiB | 200 MiB | 2.4% |
| peak RSS | 69.8 MiB | 71.0 MiB | 2.0 GiB | 3.5% |

**The one available calibration of this formula is v1's own, and it under-predicted.** `budget.json` projected
80.54 s for `T1`; `compute.json` records the realized grid at 86.44 s, a ratio of **1.0733**. Applying that same
correction is the honest way to use a 20-program projection for a 28,000-program grid, and it is the row above.
Even so the amended batched runner sits at **1.6%** of the runtime cap and the finest at **3.3%**.

**No cap is breached at any tier, for any arm.** The pause-and-report rule of PROTOCOL 8.2 is not triggered,
and nothing in this check is a reason to shrink the study, drop a cell or reduce the number of constructions.
`T1` remains admissible with roughly **60x** runtime headroom under the batched declaration and **30x** under
the finest.

---

## 8. What this establishes, and four things it does not

**Establishes.** On pinned bytes `db930d7`, with a balanced design and 8 replications: the delay-rule effect on
cost is under 1% and the horizon effect is a factor of ~1.50 per doubling; the batched all-look correction is
cost-free (x0.943 [0.938, 0.949]); the strictest declaration costs x1.911 [1.880, 1.943]; every tier of the
budget ladder is admissible for every arm with one to two orders of magnitude of headroom.

**Does not establish, and each of these is a real limit, not a hedge.**

1. **The outcome-law effect is not measured.** `C1` and `C2` share law `L1`; the root's specified design crosses
   only those two cells, so the "cell" contrast here is the **delay rule**, not the law. The `T1` grid puts
   5,000 programs each into `C3`-`C6`, which carry the boundary laws. The best available bound on that gap is a
   **count already deposited** by the v1 grid, not a new measurement: per-pair enclosure updates by cell in
   `compute.json` run 2.8375 (`C8`) to 2.9426 (`C3`), the `C1`/`C2` mean is 2.8847, the **`T1`
   program-weighted mean is 2.8826 - 0.9993x the `C1`/`C2` mean** - and the worst single cell is 1.0201x. The
   x1.020 envelope in section 7 is that worst cell. This bounds the dominant per-pair work; it is not a timing
   of `C3`-`C6`, and only an authorized balanced extension over the laws would be.
2. **The v2 runner does not exist yet.** These are the costs of *this* implementation of the two declarations,
   proved identical to v1 on the shared looks (section 3). A v2 runner that recomputed sums per look instead of
   maintaining them incrementally would be quadratic in `N_max` and none of this transfers - which is exactly
   the failure mode PROTOCOL 8.1 wrote the exponent measurement to catch. **When the v2 runner is committed,
   re-run this check against it**: `vresource_check.py --pin <that commit>` measures whatever bytes that commit
   holds and records their hashes. At the time of writing a sibling agent is landing an all-look schedule in
   `vrun.py` in this shared working tree (coordinator revision 62: parallel agents share one tree and observe
   each other); pinning to a commit is why that in-flight work could not perturb these numbers.
3. **`v2_finest` is an upper bound**, measured as all ticks **union** all distinct intra-tick states, so
   duplicated states are timed. A non-redundant implementation of that declaration would cost less than x1.911.
4. **The machine was not quiescent.** Sibling agents were running in the same tree throughout. The rotation
   removes systematic position effects and the paired factor differences out shared load, but the per-group
   standard errors include it; they are honest dispersion, not instrument precision.

**Nothing here is clearance to run anything.** The root requires deterministic and specification review before
any re-run and explicit clearance for a corrected replay. This is a bounded resource check after code review,
and it licenses no tier change, no repeated timing until a preferred tier appears, and no outcome-based choice.
The arms differ only in look schedule; no margin, alpha, `rho`, `delta`, `n_min`, gate, or episode
stopping/deadline/finalization rule was touched.

---

## 9. Suite state at the time of this check

Run on the working tree, which was **not quiescent** (see limitation 4); coordinator revision 62(b) warns that
a test count taken on a live tree is a moving target and should be quoted with that caveat.

| suite | result |
|---|---|
| #12 `tests_validation.py` | **88 tests, 88 passed**, 0 failures, 0 errors, 0 skipped (4.4 s) |
| #12 `vfixtures.py` | **18/18 fixtures passed**, including `F18_pinned_file_hashes` |
| #11 `tests_lab_chain` / `design` / `e2e` / `hostcheck` / `isolation` / `serving` / `stats` | 58 / 86 / 42 / 117 / 12 / 89 / 70 = **474 tests, all OK** |

Both baselines reproduce exactly. `vresource_check.py` is standalone and imports its measured modules from a
read-only snapshot, so it cannot affect either suite.

---

## 10. Reproduce

```bash
cd /Users/yukangzengcmac/ICLR-WinRatioAgentEvals

# deterministic only: the v1-equivalence check and the root's witness (no timing)
.venv/bin/python experiments/live_ab_validation/vresource_check.py --part check

# the full balanced check, pinned to committed bytes, depositing the receipts
VRESOURCE_SNAPSHOT_ROOT=/tmp \
  .venv/bin/python experiments/live_ab_validation/vresource_check.py \
  --part all --reps 8 --inner 20 --write

# once the v2 runner is committed, re-run against ITS bytes
.venv/bin/python experiments/live_ab_validation/vresource_check.py --part all --pin <commit>
```

`--pin` defaults to `HEAD`; `--pin tree` times the live working tree and labels the receipt
`WORKING TREE (not pinned)`. The receipts land in `results/live_ab_validation_v2/resource_check/` and carry the
measured commit and the SHA-256 of every module timed.
