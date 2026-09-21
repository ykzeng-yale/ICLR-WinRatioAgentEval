# SPEC_REPAIR_VERIFICATION: independent check of the protocol 7.5 item 5 completion

Verifier's file. Written 2026-09-20 against the working tree of `session60/live-ab-validation` at
`57482e3` plus uncommitted changes. This file is the **only** file this task wrote; no source, no
frozen value, no deposited result, no `cells.json` entry, no pin and no Git state was touched.

| field | value |
|---|---|
| interpreter | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1, scipy 1.17.0, macOS-26.5.2-arm64 |
| authority | `COORDINATOR_DECISIONS.md` revision 12 rulings 52-57 (revision 12 supersedes revision 10's framing), revision 11 rulings 50-51, revision 9 rulings 34-35, ruling 43, ruling 56 |
| root reviews read | `git show origin/main:reviews/{arxiv_cpu_prereg_statistics_review.md, arxiv_cpu_delivery_and_repair_disposition.md, arxiv_host_gate_delivery_review.md, arxiv_live_repair_ledger_review.md}` |
| data prerequisites | the benchmark caches under `results/`; the deposited #12 grid outputs under `results/live_ab_validation/`; `experiments/live_ab/testdata/`. Nothing was downloaded, no model or API was called, no dependency was added. |
| **what these runs are NOT** | **This is the repository's own code run in the repository's own environment by the same program family. It is a re-run and a cross-check, not independent verification.** Only section 1's oracles are written from the protocol text rather than from either implementation. |

---

## 0. Verdict table

| # | claim | evidence command | true output | status |
|---|---|---|---|---|
| 1a | the repaired `lab_enclosure.hierarchy_enclosure` returns **exactly** the feasible set | `scratchpad/verify_enclosure.py` (independent exact-rational oracle + brute force through `winstats.compare`) | equality at **10,510 / 10,580** production-faithful states and **11,780 / 12,176** raw-float states; **0 defects**; the remainder is the declared 1e-9 band, where it is a strict **superset** by one value | **CLOSED with a stated exception** (section 1.3) |
| 1b | `lab_reference_rule._hierarchy_enclosure` returns the same set | same script | **0** off-band mismatches; **0** bitwise disagreements with `lab_enclosure` over both grids | **CLOSED** |
| 1c | the two paths are independent | import grep + fresh-subprocess import test both ways | 0 real cross-import statements (one docstring mention only); each module imported alone leaves the other absent from `sys.modules` | **CLOSED** |
| 1d | the worked reproducer now gives `[-1, 0]` | same script | `lab_enclosure -> (-1.0, 0.0)`, `lab_reference_rule -> (-1.0, 0.0)`, exact feasible set `[-1, 0]`, superseded rule `(-1.0, 1.0)` | **CLOSED** |
| 1e | the enclosure never widens as `ell` rises | same script | **0** violations over 36 `ell` ladders | **CLOSED** |
| 2a | re-running `vcompare.py` shows the disagreements collapse | `vcompare.py --out …` with the repository's **own** `pinned/` | **122,786 of 400,203** — bit-identical to the pre-repair number. The repo's pin is **stale**: it still names `5776877`, which has no reverse certificate | **OPEN — the repair is invisible to `vcompare` until `pinned/` is re-pinned** |
| 2b | after re-pinning the repaired #11, the two policies coincide | same command, scratch mirror with `pinned/` = the repaired working-tree modules | **2,577 of 400,203** disagreeing (down 97.90%), **not zero**. The frozen 1e-12 equality contract still **FAILS** | **OPEN — collapse, not coincidence** |
| 2c | the residual is characterized, not explained away | classification of all 5,104 residual rows | 2,583 per-pair + 2,521 band rows, **0** decision-label and **0** `tau` disagreements; **#11 contains #12 in 2,583 of 2,583**, never narrower; **0 rows outside the frozen 1e-9 band**; all of it from **three** `(L_r, ell)` states | **CLOSED as a finding** (section 2.3) |
| 3a | task B reproduced the root's last-look witness | `vlastlook_check.py --part witness` | reproduces the root's digits exactly: `r(600)=0.153363950255`, `L_h=+0.013302716411`, DEPLOY fires, truth excluded | **CLOSED — the root is right** |
| 3b | the ADAPTER is untouched | `vlastlook_check.py --part adapter --adapter-programs 500` | **16,000 trials, 0 non-monotone, 0** adapter events at a drain tick the finalization look does not also carry | **CLOSED** |
| 3c | the positive control survives | `vlastlook_check.py --part grid` | PASSES under all three schedules; `C2`/`C4`/`C6` flagged, Wilson lower limits 0.808143-0.999635 against nominal 0.00625; **no Wilson flag changes state anywhere** | **CLOSED — survives** |
| 4a | the sizing companion reproduces the established figures | `wincs.pairs_for_guardrail`, `guardrail_certifiable_margin` | 17,097 **exact**; delta ladder 1,378 / 626 / 372 **exact**; `margin(568) = 0.1579515124940`, i.e. `r(568)-delta = 0.1279515124940` to 1e-13 | **CLOSED** |
| 4b | `pairs_for_power`'s docstring now warns | `wincs.pairs_for_power.__doc__` | carries `DO NOT SIZE A GUARDED TRIAL WITH THIS FUNCTION` and names both companions | **CLOSED** |
| 4c | the companion's own docstring figures reproduce | direct calls at the docstring's stated inputs | **they do not.** `guardrail_information_floor` claims 3,100 at `.392` (**true: 3,104**) and 3,099 at `.39139` (**true: 3,100**) | **OPEN — docstring defect** |
| 5a | #11 suite | `./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'` | **`Ran 474 tests in 223.307s` / `OK`** — 474 passed, 0 failed, 0 errors (stated baseline 461; the diff adds 14 test methods) | **CLOSED** |
| 5b | #11 dry run | `dryrun_live_ab.py --scenario all`; `--radius-table` | D1 `harm_keep_incumbent@39`, D2 `horizon_no_decision@40`, D3 `deploy_candidate@44`, D4 `horizon_no_decision@40`, all `verifier=PASS`; D7 radius table byte-identical to `testdata/` | **CLOSED** |
| 5c | #12 fixtures | `vfixtures.py` | **16/18** (baseline 18/18). `F15` and `F18` FAIL | **OPEN** |
| 5d | #12 tests | `tests_validation.py` | **`Ran 88 tests` / `FAILED (failures=5)`** — 83 passed, 5 failed, 0 errors (baseline 88 passing). The 5 reduce to the same two causes as 5c | **OPEN** |
| 5e | `src/test_wincs.py` | `cd src && ../.venv/bin/python test_wincs.py` | all four ruling-51 sizing tests pass | **CLOSED** |

**Nothing in section 2 or section 5 is closed.** Read sections 2.1, 2.2 and 5.2 before treating the
item-5 completion as delivered.

---

## 1. ENCLOSURE

### 1.1 How this was checked, and why it is not a restatement of the code

Two oracles, both written from `protocol_FINAL.md` **item 1's promise** and the frozen hierarchy of
6.2, neither read off either implementation:

* **ORACLE-E**, exact rational arithmetic over the **exact reals**. The pending partner's final cost
  `x` ranges over `[ell, inf)` and nothing else is known (item 4). Tier 1 is eligible only on joint
  success and decides iff `|x - L_r| > tol * max(x, L_r)`, so the revealed episode wins iff
  `x > L_r/(1-tol)`, the partner wins iff `x < (1-tol)*L_r`, and between them the pair ties. The
  feasible set follows by asking which of those three ranges meets `[ell, inf)`.
* **ORACLE-B**, brute force. For each state, the pending episode's success over `{0,1}` and a
  per-state sample of `x` that straddles **both** breakpoints (the score is piecewise constant in `x`
  with breakpoints exactly there), each completion scored by the **frozen kernel**
  `winstats.compare`. The enclosure is `min`/`max` over the scored completions.

**ORACLE-E and ORACLE-B agree at every state on both grids: 0 mismatches.** That is the check that
makes the exact oracle trustworthy without trusting my reading of `compare`.

Grid: both orientations (`sgn = ±1`), both revealed successes, 18 values of `L_r` from `0.0` to
`1e6` including `200/19`, and `ell` swept over 161 ratios of `L_r` — dense around both thresholds
`0.95` and `1/0.95`, with offsets down to 1e-16 — plus absolute values.

Two passes, because the two modules derive `ell` differently in production:

* **PASS 1, production-faithful.** `ell` quantized to integer nanoseconds, which is what both
  `lab_enclosure.certified_elapsed` and `lab_reference_rule._Episode.ell` actually produce.
  **10,580 states.**
* **PASS 2, raw float** fed identically to both paths through a duck-typed pending episode, so the
  1e-9 band can be probed below one nanosecond. **12,176 states.**

An earlier draft of this check reported 18 disagreements between the two paths. **Those were my
harness's fault, not the code's**: I had fed `lab_enclosure` a raw float `ell` and
`lab_reference_rule` the same value rounded to nanoseconds. Corrected, the disagreement count is 0.
It is recorded here because a verifier who silently deletes a false alarm teaches nobody anything.

### 1.2 Results

```
PASS 1  ell quantized to integer nanoseconds (production path)
states: 10580
ORACLE-E vs ORACLE-B mismatches                     : 0
[min,max] of the exact set containing an infeasible : 0
lab_enclosure EXACT EQUALITY with the feasible set  : 10510 / 10580
  inside the frozen 1e-9 band (conservative superset): 70
  DEFECTS                                           : 0
lab_reference_rule off-band mismatches              : 0
the two code paths, bitwise disagreements           : 0
vs the superseded two-case rule: narrower at 738, wider at 0
band states by kind: {'reverse': 38, 'forward': 32}

PASS 2  raw float ell, identical to both paths (sub-nanosecond probe)
states: 12176
ORACLE-E vs ORACLE-B mismatches                     : 0
lab_enclosure EXACT EQUALITY with the feasible set  : 11780 / 12176
  inside the frozen 1e-9 band (conservative superset): 396
  DEFECTS                                           : 0
lab_reference_rule off-band mismatches              : 0
the two code paths, bitwise disagreements           : 0
vs the superseded two-case rule: narrower at 934, wider at 0

never-widens invariant: 0 violations over 36 ell-ladders
```

Reproducer, as revision 12 item 53c states it:

```
revealed INCUMBENT success=1 cost=10.0, pending CANDIDATE ell=9.6, tol=0.05
  lab_enclosure          -> (-1.0, 0.0)
  lab_reference_rule     -> (-1.0, 0.0)
  exact feasible set     -> [-1, 0]
  superseded two-case    -> (-1.0, 1.0)
  forward certificate (1-tol)*ell > L_r + eps : 9.120000 > 10.000000001  -> False
  reverse certificate ell > (1-tol)*L_r + eps : 9.6 > 9.500000001        -> True
```

### 1.3 The exception, stated plainly

The task asked me to confirm the code returns **exactly** the feasible set, **not merely a
superset**. It does — **everywhere except inside the frozen `eps = 1e-9` certificate band**, which
is **70 of 10,580 production-faithful states** and **396 of 12,176** at sub-nanosecond resolution.
At those states the exact reals permit an exclusion by a margin below `1e-9`, both certificates
demand that margin, and the enclosure therefore keeps **exactly one value it could have removed**.

This is not a defect I am declining to call one. It is one-directional (it can only ever fail to
exclude, never exclude something feasible: **0 non-superset states**), it is what
`protocol_FINAL.md` 7.5a already declares in words, and it is the difference the root's statistics
review section 1 already named. But "equality on the whole grid" would be false, and the coordinator
should not carry that sentence forward. The honest claim is: **equality outside the declared band,
strict one-value conservatism inside it, zero defects anywhere.**

### 1.4 Independence

`grep` over both files finds **no** import statement naming the other (the one match is a docstring
sentence). A fresh subprocess importing each module alone leaves the other absent from `sys.modules`
in both directions. #12's own `F16_import_graph_independence` fixture also passes. The two paths do
share `winstats` for the radius and for the both-revealed score, which is intended: `winstats` is
the frozen kernel, not either module's enclosure logic.

---

## 2. COMPARISON: the true new disagreement count

### 2.1 Re-running `vcompare.py` as the repository stands: **122,786. Nothing collapsed.**

`experiments/live_ab_validation/pinned/` still holds the **superseded** #11 modules, pinned by
`PINNED.json` to `source_commit 577687799e8588077c036b4d94f1afc839d78e4f`, and `vcompare` refuses to
run against anything else. Re-running it therefore compares #12 against the **old** policy:

```
pinned: 577687799e8588077c036b4d94f1afc839d78e4f
streams_run 926 · looks_compared 400203 · looks_agreeing 277417 · looks_disagreeing 122786
per_pair_enclosure_endpoint 151032 · band_endpoint 131352 · 536.2 s
```

**122,786 of 400,203 — identical to the pre-repair number, to the digit.** That is a useful
reproducibility result and a blunt one: **the item-5 completion changes nothing that `vcompare`
can see until `pinned/` and `PINNED.json` are re-pinned to the repaired modules.** Re-pinning is a
coordinator action (it also moves `F18`, section 5.2), and I did not do it in the repository.

### 2.2 With the repaired #11 pinned: **2,577. A collapse, not a coincidence.**

Run in a scratch mirror of the validation tree whose `pinned/` holds the repaired working-tree
`lab_enclosure.py`, `lab_reference_rule.py` and `lab_monitor.py`, with `PINNED.json` regenerated to
match. Nothing in the repository was modified.

```
pinned: WORKING-TREE-UNCOMMITTED
streams_run 926 · looks_compared 400203 · looks_agreeing 397626 · looks_disagreeing 2577
per_pair_enclosure_endpoint 2583 · band_endpoint 2521 · 535.5 s
```

**122,786 -> 2,577, a 97.90% reduction. It did not collapse to zero, and the coordinator's
expectation that "the two policies coincide" is not met.** `vcompare`'s own disposition still reads
*"The two implementations DISAGREE"*, and the frozen 1e-12 equality criterion of PROTOCOL 12.2 still
fails. Reporting this as "the contract is now meaningful and satisfied" would be wrong.

### 2.3 What the residual is, measured rather than assumed

All 5,104 residual defect rows classified:

| property | measured |
|---|---|
| decision-label disagreements | **0** |
| `tau` (stopping-prefix) disagreements | **0** |
| per-pair enclosure endpoint rows | 2,583 |
| band endpoint rows (the same thing summed over the prefix) | 2,521; **#11 wider in 2,521 of 2,521**; max abs diff 0.0278 |
| containment direction on per-pair rows | **#11 contains #12 in 2,583 of 2,583.** 0 the other way, 0 incomparable |
| rows **outside** the frozen 1e-9 certificate band | **0** |
| forward-threshold band / reverse-threshold band | 2,390 / 193 |

Every one of the 2,583 rows comes from exactly **three** `(L_r, ell)` states:

| `L_r` | `ell` | what it is | rows |
|---|---|---|---:|
| `10.0` | `10.526315789473685` = `200/19` = `L_r/(1-tol)` | **the exact state the root's statistics review section 1 already named** | 2,390 |
| `10.0` | `9.5` = `(1-tol)*L_r` exactly | the mirror-image boundary of the reverse certificate | 111 |
| `40.0` | `38.0` = `(1-tol)*L_r` exactly | the same, at a second cost scale | 82 |

Adjudicated with the section-1 oracle rather than by preferring a side, at all three states and both
orientations: **#12 is tight and correct; #11 is a strict superset by exactly the frozen margin.**
The exact-real exclusion margins are `6.8e-16`, `2.8e-17` and `1.1e-16`, all far below `eps = 1e-9`.

So the residual is **one class, not several**: the frozen `1e-9` certificate margin, which #11
carries and #12 does not. It is the class the root already identified. **It is not a new finding,
and it is not evidence that either side is wrong.** What it does mean is concrete: **PROTOCOL 12.2's
"absolute difference <= 1e-12" criterion cannot be satisfied while the two adapters differ by a
declared `1e-9` margin.** Either #12 adopts the margin, or the criterion is restated as *equality
outside the declared band and containment inside it, with counts*. That is a coordinator ruling;
revision 12 item 55 restated the contract in words but PROTOCOL 12.2's frozen criterion still says
exact equality.

### 2.4 What agreement would and would not mean

**Agreement between #11 and #12 means the two implementations agree. It does not mean the monitor is
correct.** Two implementations of the same misreading of the guidance agree perfectly, and this
comparison cannot detect that — PROTOCOL 12.3 item 6, revision 10 item 42 and revision 12 item 55,
all still binding. Two further limits, both already on the record and neither weakened here:
agreement on the cost-tier narrowing is agreement between two readings **known in advance to
coincide** (the certificate was disclosed to the #12 author before the comparison was specified), and
`vcompare`'s 726 comparable section-11 fixture streams, derived from the guidance text rather than
from either implementation, are the only check that addresses the shared-misreading risk at all —
and they are weaker than a proof.

---

## 3. LAST-LOOK

### 3.1 Did task B reproduce the root's witness? **Yes, and the root is right.**

Re-run here, not taken on trust. `vlastlook_check.py --part witness` prints, at the root's own cell
and horizon:

```
CPREFIX first event at tick 1,010: index=600  mean_h=0.166666666667  r(index)=0.153363950255
        L_h=+0.013302716411  U_h=+0.320030616922
        DEPLOY=True  RETAIN=False  miscover_h=True  miscover_s=True
        drain ticks with a decision: 90 of 199
reduced schedule: NO_DECISION, no miscoverage, for all three constructions
```

`r(600) = .153363950255` and `L_h = +.013302716411` are the digits the root printed. The same
construction at `T1`/`N_max = 2,000`, the horizon that actually ran, fires identically
(`r(1600) = 0.092854165010`, `L_h = +0.032145834990`, 90 of 199 drain ticks). The claim of an
**exact** reduction is false as written.

### 3.2 What is now provisional, and what is withdrawn

Ruling 56 marked *every* baseline number provisional pending this reproduction. The reproduction
narrows that:

* **WITHDRAWN.** `PROTOCOL.md:829-838` and `cells.json`'s `grid.one_look_per_enrollment_prefix`
  claim of exact preservation, **for `CPREFIX` and `NAIVE` only**. The reduction drops the drain
  interior (ticks `N_max+1 .. N_max+W-1`) and intra-tick intermediate states, and both baselines'
  bands depend on the completed index rather than on the enrolled prefix, so they are not nested at
  a fixed prefix.
* **RETAINED for the `ADAPTER`.** The protocol's monotonicity argument is valid there and was
  checked by brute force: **16,000 trials, 0 non-monotone, 0 adapter events at a drain tick that the
  finalization look does not also carry.** **Not one `ADAPTER` number in the deposited results
  moves under any schedule.**
* **PROVISIONAL, as lower bounds.** The specific `CPREFIX`/`NAIVE` rows listed in
  `experiments/live_ab_validation/LASTLOOK_CHECK.md` section 4: **12** deposited rows under the
  batched reading (3 in `miscoverage.csv`, 8 in `decisions.csv`, 1 in `decision_time.csv`), **77**
  under the finest reading. Every one is **understated** in the deposited files. `ever_miscover` and
  "decides at all" are guaranteed monotone; the `deploy`/`retain` split is not, and no swap was
  observed anywhere in this grid.
* **NOT provisional.** Every `ADAPTER` row of every file; `horizon_summaries.csv` under the batched
  reading; the comparison and provenance files.
* **NOT decided, and not this file's call.** Which of the two readings (batched or finest) governs.
  The protocol fixes no tie order for simultaneous events; the root asked for one to be frozen and
  it has not been.

### 3.3 Does the positive control survive? **Yes.**

```
reduced    C2 x=7,910/8,000  wilson_lo=0.986193   C4 19,998/20,000 0.999635   C6 16,272/20,000 0.808143  -> PASSES
all_ticks  C2 x=7,910/8,000  wilson_lo=0.986193   C4 19,998/20,000 0.999635   C6 16,272/20,000 0.808143  -> PASSES
finest     C2 x=7,913/8,000  wilson_lo=0.986606   C4 19,998/20,000 0.999635   C6 16,304/20,000 0.809760  -> PASSES
no flag changes state under any schedule.
```

Against a nominal of 0.00625, a margin of 129x to 160x. It survives for a structural reason as well
as an empirical one: the reduced look set is a **subset** of the all-triggers set and
ever-miscoverage is a union over looks, so restoring the missing looks can only raise `x`, and the
Wilson lower limit rises with `x` at fixed `N`. **The defect can only make the positive control fire
harder.** Ruling 56's contingency — apparatus unvalidated, `ADAPTER` results uninterpretable — does
**not** trigger.

**One procedural note.** `LASTLOOK_CHECK.md` and `vlastlook_check.py` are both **untracked** in the
working tree. The reproduction that discharges ruling 56 is not committed.

---

## 4. SIZING

### 4.1 The companion against the established figures

| quantity | established | `wincs` returns | verdict |
|---|---|---|---|
| range-only anytime guardrail, `delta=.03`, `alpha=.00625` | 17,097 (rev 5 item 21) | **17,097** | exact. Independently re-derived from the primitive: `r(17096)=0.030000672819 >= .03`, `r(17097)=0.029999847357 < .03` |
| delta ladder at an observed difference of 0 | 1,378 / 626 / 372 (rev 2 item 5) | **1,378 / 626 / 372** | exact |
| `guardrail_certifiable_margin(568)` | 0.158 (ruling 50) | **0.1579515124940** | exact; and `margin - delta = 0.1279515124940` reproduces rev 5's `0.1279515124940428` to 1e-13 |
| betting gate, cross-arrival | 6,697 (rev 11 item 45b) | **6,701** at `.392`, **6,691** at `.3914` | brackets the figure; equals it at neither. The docstring's "about 6,700" is fair; "matching … 6,697" is generous |
| information floor, cross-arrival | 3,099 (rev 11 item 45b) | **3,104** at `.392`, **3,100** at `.39139`, **3,100** at `.39139313` | see 4.3 |
| information floor, paired | 1,079 (rev 11 item 45b) | **1,087** at `.135`, **1,079** at `.13398650` | see 4.3 |

The floor's optimizer is sound: an independent high-precision solve of the stationarity condition by
`brentq` reproduces the function's `L-BFGS-B` answer **to the integer at every discordance tested**
(e.g. `lam* = 0.076553163`, `KL = 0.001149020160` at `.39139`, against rev 11's quoted
`KL = 0.001149011`, whose implied discordance is `0.3913931312`). The arithmetic is right.

### 4.2 The old function's docstring: **it warns. CLOSED.**

`pairs_for_power.__doc__` now opens with **`DO NOT SIZE A GUARDED TRIAL WITH THIS FUNCTION.`**,
states that a guarded trial is bound by the guardrail and not by the composite effect size, names
both `pairs_for_guardrail` and `guardrail_information_floor`, gives the contrast (a few hundred
pairs against 17,097 and about 6,700), and lists its four assumptions. It also now raises on
`net_benefit == 0` and on a negative implied variance instead of returning a number. This closes the
one shipped trap ruling 51 named.

### 4.3 OPEN: `guardrail_information_floor`'s own docstring states outputs it does not produce

> "At delta = .03, alpha = .00625, power = .8 it returns 3,100 at the cross-arrival discordance .392
> and 3,099 at the unrounded .39139; at the same-task discordance it returns about 1,079-1,087"

Measured at exactly those inputs: **3,104** at `.392`, **3,100** at `.39139`, **1,087** at `.135`.
The two named numbers are shifted by one input each — `3,100` is what `.39139` gives, not `.392` —
and `3,099` is not returned at any discordance, because revision 11's 3,099 is `d/KL = 3099.15`
**floored** while the function correctly **ceils** (you cannot reach the bound with 3,099 pairs).
The `1,079` end of the paired range needs `.13398650`, not `.135`.

**The tests are not wrong; only the docstring is.** `src/test_wincs.py` uses the precise
discordances `0.39139313` and `0.13398650`, asserts `guardrail_information_floor(.03, .392, …) ==
3104` explicitly, and brackets the betting figure at 6,600-6,800. A reader who checks the docstring
against the function will conclude the function is broken when it is not. This is a one-paragraph
fix in `src/wincs.py`, and it is **not** mine: I may write only this file.

---

## 5. SUITES, DRY RUN, AND WHAT BROKE

### 5.1 What passes

| suite | command | true output |
|---|---|---|
| #11, whole | `./.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'` | **`Ran 474 tests in 223.307s` … `OK`** |
| #11, per file | same, one pattern at a time | chain 58, design 86, e2e 42, hostcheck 117, isolation 12, serving 89, stats 70 = **474** |
| #11 dry run | `../../.venv/bin/python dryrun_live_ab.py --scenario all` | `D1 ended verifier=PASS harm_keep_incumbent@39` · `D2 … horizon_no_decision@40` · `D3 … deploy_candidate@44` · `D4 … horizon_no_decision@40` |
| #11 D7 | `dryrun_live_ab.py --radius-table --out …` | `testdata/radius_table.csv agrees: True`; byte-identical |
| `wincs` | `cd src && ../.venv/bin/python test_wincs.py` | all four ruling-51 sizing tests pass |

The stated #11 baseline was 461; the run is 474, and the working-tree diff adds **14** test methods
(9 roster/stratum tests in `tests_lab_design.py`, 5 enclosure tests in `tests_lab_stats.py`,
including `test_enclosure_equals_the_brute_force_feasible_set` and
`test_reference_rule_enumerates_identically`). The count moves the right way by the right amount.
The suite still prints three known `[signature gate] DEVIATION` lines (`lab_hostcheck`,
`lab_server.start`, `lab_server.restart`), which ruling 19 accepted and which do not fail a test.

### 5.2 What is broken — #12 is NOT at its baseline

Baseline: 88 tests and 18/18 fixtures. **True output now: `16/18 fixtures passed` and `Ran 88 tests
… FAILED (failures=5)`** (83 passed, 5 failed, 0 errors). The five test failures reduce to the two
fixture failures.

**`F18_pinned_file_hashes` — a DIRECT consequence of this repair.** `cells.json`'s
`provenance.vocabulary_alignment` pins `sha256(experiments/live_ab/design/protocol_FINAL.md)` at
`3c76e8eb…`, which is the value at `HEAD`. Completing item 5 changed that file, which now hashes
`b1ff97cc…`:

```
provenance.vocabulary_alignment: experiments/live_ab/design/protocol_FINAL.md hashes to b1ff97cc…,
but cells.json pins 3c76e8eb…. The pin is stale: recompute it before the freeze commit
```

Closing it means editing `cells.json`, a frozen pre-registration artifact whose every change is
governed by revision 9 rulings 34-35 and PROTOCOL section 14. **Not a trivial breakage and not mine
to fix.** It is the same class of action as re-pinning `pinned/` (section 2.1), and the two should be
done together, with the before/after text recorded.

**`F15_protocol_config_agreement` — pre-dates this repair.** `13.0 REPORT.md is listed as not
written but exists`. `PROTOCOL.md:1325` still carries `| REPORT.md | **specified, not written** |`,
and the status-correction block at `PROTOCOL.md:1452-1453` says in terms: *"`REPORT.md` remains in
`specified_here_but_do_not_exist_at_the_freeze_commit`; this correction does not cover it."*
Ruling 43 **extended** ruling 34 to `REPORT.md` precisely so that it would be covered, and that
extension was never applied. `PROTOCOL.md`, `cells.json` and `REPORT.md` are all unmodified in this
working tree, so this fixture has been failing since `REPORT.md` was committed at `90595bc` — it is
**not** caused by the item-5 completion, and it means the "18/18" baseline has been stale for two
commits.

Both are **OPEN**. Neither is a trivial breakage a verifier may quietly repair, because both require
edits to the frozen #12 pre-registration recorded with before/after text under rulings 34 and 43.

### 5.3 The standing caveat

These are the repository's own suites, run by the repository's own runner, in the repository's own
virtual environment, on the host that produced the code. Passing counts are an owner check. They are
**not** independent verification, and they are not scientific acceptance. The only part of this file
written from the protocol text rather than from the implementation is section 1's pair of oracles.

---

## 6. Open items, blunt list

1. **`pinned/` and `PINNED.json` are stale.** `vcompare.py` as the repository stands still reports
   **122,786** disagreements and cannot see the repair. Until re-pinned, no #12 number reflects the
   completed item 5.
2. **Agreement is not reached: 2,577 disagreeing looks remain.** PROTOCOL 12.2's 1e-12 equality
   criterion is unsatisfiable while #11 carries a declared `1e-9` margin and #12 does not. Adopt the
   margin in #12, or restate the criterion as equality-outside-the-band plus containment-inside-it
   with counts. Coordinator's call.
3. **`F18` fails** because `cells.json` pins the pre-repair `protocol_FINAL.md`. Needs a recorded
   pre-registration amendment.
4. **`F15` fails** and has since `90595bc`: ruling 43's extension of the `REPORT.md` status
   correction was never applied to `PROTOCOL.md` 13.0.
5. **`guardrail_information_floor`'s docstring prints numbers the function does not return**
   (3,100/3,099 claimed at `.392`/`.39139`; 3,104/3,100 actual).
6. **The enclosure is a one-value superset at 70 of 10,580 production-faithful states**, inside the
   frozen `eps` band. Declared, one-directional, zero defects — but "exact equality everywhere" is
   not a sentence the coordinator may carry forward.
7. **`LASTLOOK_CHECK.md` and `vlastlook_check.py` are untracked.** The artifact discharging ruling 56
   is not committed.
8. **The batched-vs-finest tie order for simultaneous completion events is still unfrozen**, so the
   size of the last-look defect has two admissible readings (12 rows vs 77) and neither is
   authoritative.
