# V2_BINDINGS_2 — the three ranked repairs, what closed and what did not

**Cycle.** 2026-09-21. Authority: root disposition
`reviews/v2_bindings_root_disposition_20260921_0343.md` (ranked actions 1, 2, 3), the independent
[resource](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/blob/25e018d/reviews/v2_resource_audit_20260921_0343.md)
and [reference](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/blob/25e018d/reviews/v2_reference_audit_20260921_0343.md)
audits, issue 12 comments `5755130541` and `5755101250`, and `COORDINATOR_DECISIONS.md` revisions 16 and 17.
Both issue threads were read before anything below was decided, per revision 16 item 75.

**Environment.** `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1,
macOS arm64. **CPU only. No model call, no API call, no network, no download, no new dependency, no Git state
changed.** No v2 grid, no full frozen comparison set, no broad sweep.

**Test counts, taken after all edits below.**

| command | result |
|---|---|
| `.venv/bin/python experiments/live_ab_validation/tests_validation.py` | **156 tests, 0 failures, 0 errors, 0 skipped, 2 expected failures** (was 130 before this work) |
| `.venv/bin/python experiments/live_ab_validation/vfixtures.py` | **18/18 fixtures passed** |
| `git status --porcelain results/live_ab_validation/` | **empty** — v1 is byte-identical |

---

## 1. TASK 1 — the v2 bindings

### 1.1 The comparison now binds the v2 snapshot

**The defect.** `vcompare.py` loaded `pinned/PINNED.json`, `PROTOCOL.md` and `results/live_ab_validation/`
unconditionally. Nothing it emitted said which `#11` rule it had targeted, and no v2 comparison entry existed.

**The repair.** A `--snapshot {v1,v2}` selector. `v1` is the default and resolves to exactly the old paths, so
every deposited v1 comparison stays reproducible by the command that produced it. `v2` resolves to `pinned_v2/`,
`PROTOCOL_V2.md` and `results/live_ab_validation_v2/`. The write guard follows the selector, so **a v2 comparison
cannot write into the v1 results tree** — asserted by
`TestV2ComparisonBinding.test_the_v2_write_guard_refuses_the_v1_results_tree`.

Every summary now carries `snapshot_binding`, in which the per-file digests are **recomputed at run time** rather
than copied out of the manifest:

| binding | value |
|---|---|
| snapshot | `experiments/live_ab_validation/pinned_v2`, manifest `PINNED_V2.json` |
| manifest sha256 | `a4a614d143643652a2405fa9337999d65755d475f62b7f16b14993d13cc49654` |
| `#11` source commit | `a266c6201e3c94fc50c6646ca741e5e1da9b409b` |
| `lab_monitor.py` | `94d70b8d766376a697271087a1879de32170d4827bb25211c33f550232c2af91` |
| `lab_enclosure.py` | `da1b300d0fc99608f3b4c919d33ed546d20f2547c9339bd03e6ce6c7b9290d74` |
| `lab_reference_rule.py` | `8f8b69f01e09a92ca77a665e19bbd8f8eeba0ceef1ddab0bc3cb09b0fb9ee6fd` |
| operative document | `PROTOCOL_V2.md`, sha256 `7a5d1f3d40e49d4942428a3c47952684f2c908e192ace25cbb5927746cf00815` |
| parent v1 snapshot | preserved, source commit `577687799e8588077c036b4d94f1afc839d78e4f` |

The per-defect `replay_command` now names the snapshot. It previously emitted
`--out results/live_ab_validation --only-stream ...` for **v2** rows, which would have reproduced the wrong rule
into the frozen tree; it now emits `--snapshot v2 --out results/live_ab_validation_v2 --only-stream ...`.

**The bounded run.** Explicitly PARTIAL: one stream per cell.

```
.venv/bin/python experiments/live_ab_validation/vcompare.py --snapshot v2 \
    --streams-per-cell 1 --out results/live_ab_validation_v2/comparison_v2
```

734 streams (8 cell + 726 comparable fixture), 16,011 looks compared, **15,912 agreeing, 99 disagreeing**, 19.01 s.

On the **identical eight streams**, against v1's deposited summary:

| | v1 snapshot (deposited) | v2 snapshot (this run) |
|---|---|---|
| looks compared | 16,008 | 16,008 |
| looks disagreeing | **4,891 (30.55%)** | **99 (0.62%)** |

This is a bounded binding check on **8 of the frozen 200 cell streams**. It is not a freeze, not a calibration and
not clearance, and no rate from it is presented as the rate of the full set.

### 1.2 The epsilon binding — completed with a measurement, and it is not what I expected

The comparison now records an `epsilon_policy` block and a `certificate_boundary_analysis` computed from the
disagreeing rows of the run itself. The measured classification of all **100** per-pair enclosure disagreements:

| bucket | count |
|---|---|
| certificate margin **exactly zero** | **100** |
| margin inside `CERTIFICATE_EPS = 1e-9` | **0** |
| margin outside epsilon | **0** |
| `#11` enclosure strictly **contains** `#12`'s | **100 of 100** |
| `#12` enclosure contains `#11`'s | **0** |

**I had written that the epsilon band was the cause. The measurement says it is not.** Every one of the 100 rows
sits exactly on a certificate threshold, so `#11`'s certificate cannot fire **at any `eps >= 0`**; setting the
constant to zero would remove none of them. The real difference is of **algebraic form**: `#11` narrows only when
a sufficient certificate `(1-tol)*ell > L_r + eps` fires, while `#12` asks whether a tier outcome is achievable
anywhere in the feasible cost box, `(x-L_r) > tol*max(x,L_r)`. Those are the same threshold and different
floating-point expressions. I corrected my own binding text to match the measurement before publishing it.
`#11` is uniformly the wider, more conservative side at these rows. **Which side is right is not decided here**
and neither side was edited (`PROTOCOL.md` 12.3 item 1).

### 1.3 The stopped-target binding — bound and disclosed, not repaired

`experiments/live_ab/lab_data.py:15-24` still states the refuted stopped-roster reading. That file is outside
`experiments/live_ab_validation/` and outside this session's write scope, so it is **disclosed in the artifact**
rather than silently inherited: the comparison records the target it is actually under (the running conditional
mean over the enrolled prefix `n`) and records the unrepaired claim beside it. It moves no compared number here,
because both sides are driven over the same event stream at the same prefix.

The same treatment applies to `pinned_v2/lab_enclosure.py`'s "exact / never a relaxation" wording: with a strictly
positive `CERTIFICATE_EPS` that holds everywhere except inside the epsilon band at each threshold, where the
computed set is a **superset** of the exact feasible set. Conservative direction, overstated wording. The snapshot
is read-only and `#11` owns the source, so it is bound and disclosed, not edited.

### 1.4 The six PROTOCOL_V2.md prose corrections — before and after

The coordinator's decision to HOLD these is reversed by the root (revision 17 item 84; issue 12 comment
`5755101250`). All six are **narrowings**. The version string stays `v2-cpu-validation` because it is bound in
`vrun.V2_VERSION_STRING` and `PINNED_V2.json`; `PROTOCOL_V2.md` section 11 is the revision record instead.

**R1 — "every affected ADAPTER number", section 1.2.**

> BEFORE: `**Not one deposited `ADAPTER` number moves under any reading.**`

> AFTER: `**No deposited `ADAPTER` number moved under either of the two readings of section 1.2, on the quantities and the 16,000 trials that check actually covered.** That is the scope of the evidence and this sentence does not exceed it: it is not a statement about every possible reading, nor about trials that were not run (correction **R1**, section 11).`

**R2 — "the exact union over every admissible tie order", section 1.2 item 2.**

> BEFORE: `One asymmetry must accompany any ruling here: for `CPREFIX` the finest set is a function of the completed count `k` alone and is therefore the exact union over **every** admissible tie order, so its column is order-independent; for `NAIVE` the intra-tick partial sums depend on the order, so its finest column is **one admissible schedule and not a bound over all of them**.`

> AFTER: the same asymmetry, restated as a statement about the **constructions** — true for `CPREFIX`, false for `NAIVE` — plus: `The claim is therefore true for one construction and not the other, and it **must not be read as a property of the delivered finest iterator**: that iterator inserts completed-prefix states no tie order ever reaches — with resolution ticks `(3,2,3)` the prefix jumps `0 -> 2` and the code inserts a prefix `1` that does not exist (`COORDINATOR_DECISIONS.md` revision 16 item 78). **As implemented, the `CPREFIX` finest column is neither the exact union over every admissible tie order nor one admissible schedule**, and the finest sensitivity is consequently **deferred and disabled** from the next approved primary panel, with its code and its failed check preserved as development evidence (correction **R2**, section 11).`

**R3 — "all methods receive precisely the same looks", section 1.2 item 4.**

> BEFORE: `4. **The same declared schedule applies to all three constructions.** Full and partial observations are compared at the **same prefix**. No construction gets a look another does not.`

> AFTER: `4. **The same declared schedule applies to all three constructions, and that means the same TICKS — not the same index and not the same information.** Every construction is evaluated at exactly the same set of calendar ticks; **no construction gets a look another does not**, and that part of the claim stands. What does **not** stand is the reading that all three are therefore "compared at the same prefix": at a shared tick the `ADAPTER` reports at the enrolled prefix `n`, `CPREFIX` at its completed count `k`, and `NAIVE` at its own count `m`, and these are different indexes over different sample counts. **Equal calendar time is not equal information and, under a changing conditional mean, not even the same target.** Any cross-construction width or ratio must therefore carry its own index and target label; a column headed "the same prefix" across all three is a calendar-aligned display, not a like-for-like comparison (correction **R3**, section 11).`

**R4 — "every affected deposited number was understated", section 1.2 closing.**

> BEFORE: `it does not select a favourable outcome: every affected deposited number is **understated** in `v1`, which is the direction that flatters the baselines rather than the object under test (`LASTLOOK_CHECK.md` section 4).`

> AFTER: `on the evidence available it does not appear to select a favourable outcome: **every affected deposited number that `LASTLOOK_CHECK.md` section 4 actually checked moved in the understating direction**, which is the direction that flatters the baselines rather than the object under test. The earlier wording here — "every affected deposited number is understated" — was a **blanket claim over numbers that were never examined**, and it is withdrawn in favour of the measured one. Numbers outside that check's scope are **unknown in direction**, not known to be understated (correction **R4**, section 11).`

**R5 — "v1 validated #11", section 4.2.**

> BEFORE: `which is the pin doing its job: the honest statement is that `v1` validated `#11` as it stood at commit `5776877` against `protocol_FINAL.md` at `3c76e8eb...`, and re-pinning now would assert that the completed run covered a version of `#11` that did not exist when it ran.`

> AFTER: `which is the pin doing its job. The honest statement is **not** that `v1` validated `#11`: `v1` **compared** `#12`'s band arithmetic against `#11` as it stood at commit `5776877`, under `protocol_FINAL.md` at `3c76e8eb...`, **and that comparison DISAGREED**. Its own deposited summary records **122,786 of 400,203 compared looks disagreeing over 926 streams**, in two defect classes — `per_pair_enclosure_endpoint` (151,032 rows) and `band_endpoint` (131,352 rows) — **affecting all 200 cell streams**. A comparison that disagrees on roughly **31%** of its looks does not validate either side, and `vcompare.py`'s own frozen wording is that even total agreement would be reported as agreement and never as correctness.` A new paragraph then records the `--snapshot` repair as what addresses condition 2, instead of a re-pin.

Command for those numbers: `python -c "import json; d=json.load(open('results/live_ab_validation/comparison_summary.json'))"` — read only, no re-run.

**R6 — prototype speed ratios and the "resource item discharged" label, sections 9, 9.1, 9.3 item 9.**

> BEFORE (9.1): `**This check has been delivered.** ... Its headline results are that the corrected all-look schedule does **not** cost materially more — a paired factor of **x0.943, 95% CI [0.938, 0.949]** under the batched declaration of section 1.2 and **x1.911, 95% CI [1.880, 1.943]** under the finest — that the cell effect is **not separable from zero** (`+0.0093 +- 0.0057` in log seconds per program) while the horizon effect is large and precise (`+0.4053 +- 0.0054`), and that **no cap is breached at any tier for any of the three schedules**.`

> AFTER (9.1): `**This check has been RUN; it is not discharged.** ... **The `x0.943 [0.938, 0.949]` and `x1.911 [1.880, 1.943]` ratios previously quoted here are PROTOTYPE numbers and are withdrawn from this position.** They come from the receipt under `resource_check/`, which timed an *amended helper* rather than the delivered runner, so they are **not a measurement of the runner that would execute `v2`** and must not be quoted for it. That receipt is **preserved** as development evidence and keeps its own label. The same withdrawal applies to the cell effect `+0.0093 +- 0.0057` and the horizon effect `+0.4053 +- 0.0054` **as statements about the delivered runner** ... The measurement that **does** name the delivered runner is the commit-anchored receipt at `results/live_ab_validation_v2/resource_check_committed/` ... Its geometric `v2/v1` runtime ratio is **`1.1246974`** ... The earlier working-tree receipt's ratio is **`1.1302466`**. These are **two distinct observations, not interchangeable estimates**, and both are retained.`

> BEFORE (section 9 table): `| the balanced **20-program** resource check of section 9.1 | **permitted, and DELIVERED**: `RESOURCE_CHECK.md` |`
> AFTER: `| ... | **permitted, and RUN** (`RESOURCE_CHECK.md`). **Run is not discharged**: the budget pipeline it feeds was defective and the accepted receipt is the commit-anchored one, not the prototype — see section 9.1 and correction **R6** |`

> BEFORE (9.3 item 9): `9. Section 9.1's balanced resource check run and recorded, with its effect-independent tier rule. **Discharged** by `RESOURCE_CHECK.md`, subject to the coordinator accepting it.`
> AFTER: `9. ... **NOT discharged.** The check was run, but the chain that turns it into a budget was defective: the smoke record failed the runner's own allowlist, the tier selector collapsed four balanced `(cell, horizon)` groups to two by overwriting `C1` with `C2`, and the planned reference workload was excluded from the total. ... this line is discharged only when the coordinator accepts that repaired chain, not when a measurement exists (correction **R6**).`

The cost-driven recommendation for the batched reading rested on the withdrawn ratios; it is withdrawn too, and the
original paragraph is preserved inline as a block quote.

---

## 2. TASK 2 — the smoke-to-budget pipeline

All three defects were repaired and verified with **NON-TIMED fixtures**: every second in the checks is a synthetic
constant, so nothing was re-timed while it was being fixed, and the accepted primary measurements were not
disturbed. The fixtures are permanent regression tests in `tests_validation.TestSmokeToBudgetRepairs`.

### Defect 1 — the runner rejected its own smoke metadata

`run_smoke` wrote `design`, `balanced` and `unique_programs`; `SMOKE_PERMITTED_KEYS` contained none, so
`assert_smoke_holds_no_effect_record` exited on `design`. Those three keys plus `unique_program_indices`,
`program_index_rule` and `reference_workload` are now on the allowlist **deliberately**, and all are non-outcome
metadata. The exclusion of effect columns is unchanged and is still asserted: a record carrying `coverage_rate`
is still refused. A new test reads `run_smoke`'s own literal keys by AST and fails if any is not on the allowlist,
so this class of defect cannot recur silently.

### Defect 2 — the tier selector overwrote C1 with C2

`select_tier` built `{p['N_max']: p for p in smoke['points']}`. On the balanced 2×2 that is four entries into two
keys, and C2 overwrote C1: **half the balanced timing design never reached the budget.** The root's own fixture
reproduces here — with C1 at 100/400 s and C2 at 1/2 s, the old keying keeps **C2 at both horizons**, and under
the defect multiplying both C1 costs by 1,000 changed no output.

The repair is `aggregate_horizon_costs`, implementing the root's binding rule: **retain both cell inputs at each
horizon, project from the maximum measured cell cost per horizon.** It is outcome-independent, conservative, and
it is a **resource rule only** — not an inferential guarantee, not a claim the cells differ, and not a reason to
change the scientific horizon after outcomes. A duplicated `(cell, horizon)` is now refused rather than collapsed.

### Defect 3 — v1's program indices had moved

`program_base` incremented across **both** v1 groups, so the old C2 group's indices 0–9 became 10–19; the
"preserved" v1 reproduction path was not seed-equivalent. Indexing is now schedule-specific: **v1 is group-local
(each group starts at 0)**, v2 keeps the incrementing base it needs because its balanced design visits the same
cell twice. The rule is recorded in the smoke record. `unique_programs` now counts distinct `(cell, program)` seed
identities and `unique_program_indices` counts distinct indices — two fields, because collapsing them once let a
repetition count be read as an independent experimental outcome.

The v1 selection path is branched and preserved: it does not pass through the aggregator, and a v1 fixture returns
`beta = 1.0`, `s_2000 = 2.0` (C1's) and `s_1000 = 1.0` (C2's) exactly as before.

### The repaired budget projection, from the accepted primary measurements

Built by replaying the **commit-anchored** receipt — the one whose six source hashes match exact
`ff60527de63e17738d8102fa41a0f47f3818e0c5` — through the repaired selector. **No clock was read.**

```
.venv/bin/python <scratch>/build_budget.py
  -> results/live_ab_validation_v2/budget_projection_repaired.json
```

**Both cell inputs retained** (seconds per program, `v2_all_ticks`):

| horizon | C1 | C2 | max (used) | what the defective keying kept |
|---|---|---|---|---|
| 1,000 | 0.0020900036790408192 | **0.0021203979151323436** | C2 | C2 |
| 2,000 | **0.003358878649305552** | 0.0033424677327275275 | C1 | **C2 — C1 discarded** |

`beta = 0.663644647140228`, bytes/program `211.0`, cap 5,400 s.

| tier | N_max | programs | primary s | **reference s** | total s | admissible (primary only) |
|---|---|---|---|---|---|---|
| T1 | 2,000 | 28,000 | 94.05 | **974.93** | 1,068.98 | yes |
| T2 | 2,000 | 16,000 | 53.74 | **557.10** | 610.85 | yes |
| T3 | 2,000 | 8,000 | 26.87 | **278.55** | 305.42 | yes |
| T4 | 1,000 | 8,000 | 16.96 | **129.62** | 146.58 | yes |

### The planned reference workload is priced, and it dominates

The root's ruling — reference-only decision authority does not make its compute free — is implemented as a strict
separation. **Decision authority: unchanged and still zero**; the frozen `cells.json` selection rule still reads
`seconds_projected` on the primary alone, because changing what that gate consumes would be a change to a
scientific rule and is not authorized. **Resource accounting: counted**; the reference's measured cost is priced
into a separate total and any tier it would push over the cap is named (none, here).

**The reference is 91.2% of the projected total at T1–T3 and 88.4% at T4.** `reference/panel.py` excludes it from
every ladder because it cannot decide; on these numbers that exclusion hides roughly ten times the primary's own
cost. An absent receipt yields `resolved: false` with a reason and is **never rendered as zero**.

Receipt provenance is recorded exactly, including its weaknesses: min/median/max summaries only, no raw timing
vectors, no interpreter or environment record, no code or harness hashes — so it is **not** an exact-pin receipt
comparable to the committed primary one, and it is labelled as the weaker artifact it is.

### The manifest now binds the comparison snapshot

`write_manifest`'s source glob is top-level only, so neither it nor `v2_bindings` bound `pinned_v2/PINNED_V2.json`
or its three files. `v2_bindings` now emits a `comparison_snapshot` block with the manifest digest, the **recomputed**
file digests, an `agrees_with_manifest` flag, and the parent v1 commit. An absent snapshot is reported as absent
rather than defaulted to v1's.

---

## 3. TASK 3 — the reference diagnostic. I attempted it, and it was possible

The root's condition was: produce a replacement **only** if the actual family, scale, alpha convention and clock
can be identified and both sides evaluated at the same level; otherwise say what is missing. On this host the
vendored reference **imports and executes** (`_build/boundaries.cpython-312-darwin.so` is built for this
interpreter), so the correct comparison was constructible without any proxy. It is
`reference/eb_width_diagnostic.py`.

### How each of the three withdrawn defects is closed by construction

| withdrawn defect | closure |
|---|---|
| **wrong family** — `poly_stitching_bound`, stitched, `c=0` | the selected reference is **called**, through `eb_reference.reference_bands`, so family (`mixture`), scale (`lo=-1, hi=+1, c=2`) and tuning (`v_opt=10`) are whatever that module fixes and cannot drift. A test asserts by AST that the diagnostic **never names a stitched boundary**. |
| **wrong error budget** — alpha pre-halved | alpha is passed **unhalved**; `confseq_eb` applies `alpha/2` internally. The primary is evaluated at the same **total two-sided** `alpha_gate = 0.00625`. A test fails the file if `alpha` is ever divided in it. |
| **wrong clock** — `n × pilot variance` | **no proxy at all.** The reference runs on actual fully specified score paths and accumulates its own clock. That clock is reported beside the realized variance so the two can be seen to differ — the audit's own example is a regression test: `(+1,+1,-1,-1)` and `(+1,-1,+1,-1)` have equal terminal variance and clocks `61/9` vs `70/9`. |

### What the two sides are, at the same level

Both are two-sided anytime-valid confidence sequences for the running mean of the **same** bounded scores, at the
**same** `n`, on the **same** path, at the **same** total two-sided `alpha_gate = 0.00625`.

* **Primary** — `winstats.normal_mixture_radius`, normal mixture on the **predictable worst-case** clock `V_n = n`,
  tuned at `rho = 100`. Its clock does not depend on the data.
* **Reference** — `comparecast.confseq.confseq_eb`, gamma-exponential **mixture** on the **empirical** residual
  clock, tuned at `v_opt = 10`, scale `c = 2`.

So exactly one difference is priced: a fixed clock against an adaptive one, under each construction's own tuning.

**Provenance hardening applied.** The audit flagged that `_load_package` returns a same-named `sys.modules`
package without checking its origin. The diagnostic now verifies, after import, that every loaded reference module
resolves inside `reference/upstream/` or `reference/_build/`, and **refuses to emit a width otherwise**. All four
verified: `confseq`, `comparecast`, `comparecast.confseq`, and `confseq.boundaries` (the compiled `.so`).

### The result — and it reverses the direction of the withdrawn claim

```
.venv/bin/python experiments/live_ab_validation/reference/eb_width_diagnostic.py
  -> results/live_ab_validation_v2/reference_width_diagnostic.json
```

Eight declared streams (`C1`–`C8`, namespace 2, program 0, trial 0 — the same streams the bound comparison
replays, so nothing was chosen after seeing a width) and a six-point `n` grid declared before any width was
computed. Unclipped widths:

| n | primary W | reference W min | reference W max | ratio min | ratio max | reference narrower |
|---|---|---|---|---|---|---|
| 100 | 0.931386 | 0.887574 | 1.025296 | 0.9530 | 1.1008 | **3 of 8** |
| 200 | 0.580921 | 0.589563 | 0.686562 | 1.0149 | 1.1819 | 0 of 8 |
| 500 | 0.338592 | 0.363053 | 0.413054 | 1.0722 | 1.2199 | 0 of 8 |
| 1,000 | 0.234973 | 0.249281 | 0.287860 | 1.0609 | 1.2251 | 0 of 8 |
| 1,500 | 0.191725 | 0.197691 | 0.232883 | 1.0311 | 1.2147 | 0 of 8 |
| 2,000 | 0.166461 | 0.171185 | 0.200947 | 1.0284 | 1.2072 | 0 of 8 |

**The reference is WIDER than the primary at 45 of the 48 evaluated (path, n) points**, and narrower only at
`n = 100` on 3 of 8 paths. **A crossover exists within the evaluated grid.** The withdrawn note claimed the
reference was tighter at every `n` with no crossover; on the correctly specified comparison the direction is the
other way at this operating point, and the crossover it denied is present.

The mechanism is visible in the clock: the reference's `V_n / n` runs about **0.66 to 0.95**, so its adaptivity
does buy it a smaller clock than the primary's worst-case `V_n = n` — but at our `n` its boundary constant, tuned
at `v_opt = 10` with scale `c = 2`, costs more than the adaptivity saves. The clock also differs from the realized
variance by roughly 10–14 units at `n = 2,000`, which is the concrete reason a variance proxy could not have
identified it.

**What this does not establish, and none of these is a hedge.** It is complete-data only — the ADAPTER never sees
`z_true`, it sees enclosures, so this prices boundary constructions and says nothing about partial-information
handling. It is hierarchy score `z` only, so it says nothing about success-guard power. It is not power, not an
expected stopping time, not a required sample size, and not evidence that any two systems are genuinely equal.
**No ordering over all `n`, all paths or the two families is asserted**, and no pair count is derived from it.

### The cross-check repair — from the theorem, verified afterwards

The defect is the omitted nonnegative `B²` inside `sqrt(A + B²)`, with `A = k1²·v·ell` and `B = k2·c·ell`. It is
**not** a constant inside `ell`; my earlier diagnosis is withdrawn in the module docstring, together with the
reason I misread the evidence (the gap shrinking with `v` is consistent with the real fault, because `B²` is second
order in log terms while `A` grows linearly in `v`).

`stitched_boundary` is **preserved unchanged with its banner**. `stitched_boundary_repaired` restores the term as
the cited theorem's own pinned implementation writes it
(`upstream/confseq/uniform_boundaries.h:505-510`). **Nothing was tuned**: no constant fitted, no parameter
searched, and the form was not adjusted after comparing to the authors' output.

| v | original | repaired | authors' `poly_stitching_bound` | repaired − authors |
|---|---|---|---|---|
| 10 | 28.5871851682 | 37.1514662303 | 37.1514662303 | **0.0** |
| 50 | 50.4559119055 | 56.9624136766 | 56.9624136766 | **0.0** |
| 200 | 84.0291099487 | 87.9385626616 | 87.9385626616 | **0.0** |
| 1,000 | 165.2729126644 | 167.2137682063 | 167.2137682063 | **0.0** |
| 5,000 | 347.3456673770 | 348.2686745099 | 348.2686745099 | **0.0** |

Exact agreement at all five probe values, as a **consequence** of the repair. The repaired object is still a
cross-check: not the reference, not a validated bound for this study, and neither its narrowness nor its width
says anything about the primary theorem. The claim that "the mixture is tighter than any stitched boundary near
the tuning point" is also withdrawn from that docstring — one configured path does not establish an ordering over
a family.

---

## 4. BLUNT LIST — what did not close

1. **The v2 comparison is 8 of 200 cell streams.** The full frozen set has not been replayed against the v2
   snapshot and is not cleared. The 0.62% disagreement rate is this partial run's rate and nothing more.
2. **The 99 residual disagreements are unadjudicated.** They are characterized exactly — all at zero certificate
   margin, `#11` strictly wider in all 100 per-pair rows — but which side is right is a coordinator/root ruling and
   neither side was edited.
3. **`lab_data.py`'s stopped-roster claim is disclosed, not repaired.** It is outside this session's write scope.
4. **`pinned_v2/lab_enclosure.py`'s "exact" wording is disclosed, not repaired.** The snapshot is read-only and
   `#11` owns the source.
5. **The budget projection inherits an unresolved scope mismatch.** The committed receipt times
   `vrun.evaluate_trial` + `vrun.trial_rows`; `run_smoke`'s timed region is `run_block`, which also includes
   stream generation and the row sink. **Every per-program second in section 2 is therefore a lower bound**, and
   the ladder inherits that. Closing it needs a receipt whose timed region matches `run_smoke`'s. It was not
   taken, because taking it means re-timing and the instruction was to repair with non-timed fixtures.
6. **The reference workload is not predeclared.** The totals assume **one** reference evaluation per program at
   the tier's horizon. That assumption is stated in the artifact and is not a prespecified workload. A planned
   two-gate panel would execute more calls than this prices, and the receipt measures one score stream only.
7. **The reference receipt is weaker than the primary's** — min/median/max only, no raw vectors, no environment,
   no hashes. It is not an exact-pin receipt. Its numbers also differ from `V2_BINDINGS.md`'s prose table
   (JSON ms/program 16.0039/34.6289/16.2023/34.8190 versus prose 15.889/34.362/16.018/34.586); **this document
   cites the JSON receipt**, and the discrepancy between the two tables is **not resolved here**.
8. **`panel.py:200-202` still multiplies `ru_maxrss` by 1 on both platforms** — correct on macOS, wrong on Linux
   (KiB needs ×1024) — and its four groups share one process, so its RSS is a cumulative high-water mark. Not
   touched, because changing it would change a measured artifact mid-review.
9. **The finest sensitivity remains deferred and disabled**, not repaired. Its unreachable-prefix defect and its
   tick-keyed `_look_fractions` both stand, with two permanent expected failures recording them.
10. **The width diagnostic is complete-data, hierarchy-only, one host, eight paths, six `n` values.** It prices a
    boundary construction. It is not power, not a stopping time, and not a sizing result. **No pair count is
    derived from it and none should be.**
11. **No resource-gate discharge, no calibration, no freeze, no live clearance, no full grid.** The next milestone
    is the complete corrected executable specification/adapter gate, and this work does not reach it.
12. **Nothing was committed.** All work is uncommitted in the working tree, per the hard rule. The coordinator
    commits as `Yukang Zeng <ykzeng2019@gmail.com>`.
