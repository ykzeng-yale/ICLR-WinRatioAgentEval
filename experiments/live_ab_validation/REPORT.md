# REPORT: `live_ab_validation` (issue #12) - independent CPU validation of the #11 monitor

**Study:** `experiments/live_ab_validation/`, protocol version `v1-cpu-validation`, the frozen pre-registration `PROTOCOL.md` and its machine-readable twin `cells.json`, both committed **before any simulation outcome existed**.

**This report is deliverable 6 of `PROTOCOL.md` section 13.3.** It reports every quantity section 9 requires, with its Wilson interval, for all eight cells and all three constructions, **including every unfavourable and every inconclusive row**. No row is omitted for brevity and no row is omitted because it is unfavourable (section 13.4).

---

## 0. The headline, stated first

| | |
|---|---|
| fixture gate (section 11), at the grid run and at the comparison | **18/18 passed** |
| unit and property tests, at the grid run | **88 ran, 0 failures, 0 errors, 0 skipped** |
| fixture gate **now**, after this file was written | **17/18** - `F15` reports `13.0 REPORT.md is listed as not written but exists`; see section 14 item 2 |
| unit and property tests **now** | **88 ran, 2 failures, 0 errors, 0 skipped** - both failures are that same one `F15` message and nothing else |
| budget tier selected by the section 8.2 ladder | **T1** (28,000 programs, `N_max = 2,000`) |
| grid | **ran to completion**, reported namespace 0 |
| determinism re-run | **byte-identical** (154,912 bytes compared) |
| **positive control (section 9.4)** | **PASSED** - `NAIVE` hierarchy ever-miscoverage is FLAGGED in **`C2`, `C4`, `C6`**, and the precommitment required at least one of `C2`, `C4`, `C6` |
| `ADAPTER` exceedance flags | **none, in any cell, on any gate, at any horizon** - which is reported below as *no exceedance was detected at this resolution*, and never as *the bound holds* |
| **comparison against the pinned #11 monitor (section 12)** | **DISAGREEMENT = DEFECT.** 122,786 of 400,203 compared looks, over 926 streams, failed at least one frozen criterion |
| consequence, in the protocol's own words | **until a disagreement is adjudicated, #11's results do not count as validated**, which is the whole purpose of this study (section 12.3 item 4) |

**The two results above must be read together.** The measuring apparatus validated itself (the positive control fired, in all three precommitted cells). The `ADAPTER` construction - the #12 re-implementation - produced no exceedance flag anywhere. And the #12 and #11 implementations **do not compute the same enclosure**, so this run does **not** validate #11. Which side is wrong is **not decided here** (section 12.3 item 3).

---

## 1. The adapter commit under test (section 13.3 item 6)

The object this study set out to validate is the #11 monitor as deposited, read-only, in `experiments/live_ab_validation/pinned/`:

| | |
|---|---|
| `live_ab` source commit | `577687799e8588077c036b4d94f1afc839d78e4f` |
| source branch | `session60/live-ab` |
| `pinned/lab_enclosure.py` SHA-256 | `47c523128b0abf91165670772940ee096827e12d533556ef1fd26c60dc578d0a` |
| `pinned/lab_monitor.py` SHA-256 | `8c20e07205748e59dad4224420e7804103d1d73e41733ccc2a91df5f8aebeced` |
| `pinned/lab_reference_rule.py` SHA-256 | `6219cc64f439e7bf64b4da20e4076429ccf7ea9f3d5655090f27b4a20ae360b1` |
| manifest verified at comparison time | `True` |

> **This commit is NOT validated by this run.** Section 13.3 item 6 asks this report to name the validated adapter commit. The honest answer this run produces is that there is none: the comparison of section 12 found a disagreement, and section 12.3 item 4 fixes what that means - *until a disagreement is adjudicated, #11's results do not count as validated*. The commit is named here as the commit **under test**, with its hashes, so that the adjudication has an exact object.

---

## 2. Provenance and exact reproduction

| | |
|---|---|
| repository commit at run time | `02b94103bb9798c906967b27031ba6b38b94eb74` |
| master seed | `1220260919` |
| namespace of the reported grid | `0` |
| Python | `3.12.13` |
| numpy | `2.4.1` |
| platform | `macOS-26.5.2-arm64-arm-64bit` |
| execution | CPU only. No model call, no API call, no network, no download, no new dependency. |

Source hashes recorded in `manifest.json`:

| file | SHA-256 |
|---|---|
| `experiments/live_ab_validation/PROTOCOL.md` | `bcef5e825d31d87463fcda597ae4f2223e02d62943ab4342c94886b2c829fad6` |
| `experiments/live_ab_validation/cells.json` | `17f544b34ab1b83be773c4e8517a8a281a90ad5278932ba1b64d01db0babb0f7` |
| `reviews/arxiv_live_design_guidance.md` | `a71965986165d56915a557a1a43998d9eb76a4e800dba670281c93720037ad1b` |
| `src/winstats.py` | `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` |
| `tests_validation.py` | `b5349609cd411164d857d9e22e91d380c0648d344cb847a485ebda3bec451c43` |
| `vband.py` | `55a9894ff5694099c05cedbdf695ecdad3ac4bd5025328cd445e0b1d3df8cd9c` |
| `vcompare.py` | `299ff652725a5549ae55e3de42b11e67335fa4a103bb4ce6d22d46946c5fe7e3` |
| `vfixtures.py` | `a5b98a6622e5c357634a63fc03e7cd1b03895ae5f89595f7672805618791b10d` |
| `vgen.py` | `2d0e2756b5e28b3af256b657953532ecb1849a404a1761952fae8a287e2745cd` |
| `vrun.py` | `8b735cfe994b2dddbc240ba5568ca680ccb37cc171ff024d0002230db65d862b` |

The two commands, exactly as section 13.1 fixes them:

```
.venv/bin/python experiments/live_ab_validation/vrun.py --out results/live_ab_validation
.venv/bin/python experiments/live_ab_validation/vcompare.py --out results/live_ab_validation
```

---

## 3. What changed between the freeze and this run, and what did not

Two post-freeze corrections were applied under `experiments/live_ab/design/COORDINATOR_DECISIONS.md` revision 9. Both are recorded with their before/after text in `PROTOCOL.md` section 14.1. **Neither changes a value.**

1. **Status correction (ruling 34).** Section 13.0's status column asserted that `vgen.py`, `vrun.py` and `vcompare.py` do not exist. Writing them - which is what 13.0 instructs - made that false, `F15` failed on the contradiction, and `vrun.py` aborted before the grid. The status column and the corresponding `cells.json` module map were corrected. No cell, parameter, seed, grid, estimator, reported quantity, flag rule or positive control moved.
2. **Withdrawal of a false sentence (ruling 35(b)).** Section 2.5's claim that sections 6.3 and 6.4 were computed with the governing predicate was false and is withdrawn. They were computed with the closed-form paraphrase, which differs from the predicate in exactly the 128 boundary states 2.5 itself names. **The frozen 6.3 and 6.4 values were NOT edited** (ruling 35(a)); the predicate-reading recomputation is deposited beside them in `ADDENDUM_SECTION6.md` (ruling 35(c)), with both readings side by side and every differing entry named with both values - 13 entries at `N_max = 2,000` and 14 at `N_max = 1,000`, each of `0.0001`.

**Nothing operative moved** (ruling 35(d)). The predicate is what `vband`, `vgen`, `vcompare` and `F17` implement, so the grid, the decision rule and every quantity reported below are unaffected by which reading built two descriptive expectation tables.

The three provenance pins of `cells.json` and the three `pinned/PINNED.json` digests were recomputed against the files as they now stand, after the edits: **all six match**, and `F18` passes. Editing `PROTOCOL.md` and `cells.json` broke no pin, because neither file is hashed by any pin - the pins cover `reviews/arxiv_live_design_guidance.md`, `src/winstats.py`, `experiments/live_ab/design/protocol_FINAL.md` and the three pinned monitor sources.

---

## 4. What ran (sections 8 and 11)

### 4.1 The fixture gate

`18/18` of `F01`-`F18` passed. The gate is **fail-closed** for the reported grid (`fail_closed_for_the_reported_grid = true`), with `0` exemptions and `0` failing cases. Per-case results are in `fixtures_report.json`.

### 4.2 The smoke run and the budget ladder (section 8, deliverable 7)

Measured on this host at namespace 1, whose seeds are discarded and never reused, **before** the reported grid ran, and written to `budget.json` before it ran:

| | |
|---|---|
| smoke `C1` at `N_max = 2,000` | 10 programs in 0.02876 s (0.002876 s/program) |
| smoke `C2` at `N_max = 1,000` | 10 programs in 0.01875 s (0.001875 s/program) |
| smoke peak RSS | 74,104,832 bytes (70.7 MiB) |
| scaling exponent `beta` | `0.617648` (an incremental implementation gives `beta` near 1) |
| incremental property asserted | `true`, 2.8869 enclosure updates per pair against a bound of 5 |

The ladder, with the selection rule *the highest tier whose projection satisfies all three limits*:

| tier | `N_max` | programs | projected seconds | projected peak RSS | projected bytes | admissible |
|---|---|---|---|---|---|---|
| `T1` | 2,000 | 28,000 | 80.5 | 74,104,832 | 3,693,200 | true |
| `T2` | 2,000 | 16,000 | 46.0 | 74,104,832 | 2,110,400 | true |
| `T3` | 2,000 | 8,000 | 23.0 | 74,104,832 | 1,055,200 | true |
| `T4` | 1,000 | 8,000 | 15.0 | 74,104,832 | 1,055,200 | true |

Hard limits: `5,400` s, `2,147,483,648` bytes peak RSS (2 GiB), `209,715,200` bytes output (200 MiB). **Selected tier: `T1`** - the full grid. No reduced grid, no pause-and-report branch, and no forfeited horizon summary.

### 4.3 Determinism

One cell block (`C1`, programs 0-99) was re-run from its seed coordinates and its per-trial records compared byte for byte: **identical = `true`**, 154,912 bytes. Files asserted byte-identical between runs: `trials.csv.gz`, `miscoverage.csv`, `decisions.csv`, `decision_time.csv`, `unresolved.csv`, `horizon_summaries.csv`, `manifest.json`, `fixtures_report.json`. Files that cannot be: `compute.json (its timing fields)`, `budget.json (it IS the smoke measurement and the projection)`, `smoke/timing.json (the same measurement)`.

---

## 5. Measured compute, timing and resolution (section 9.5)

| measured quantity | value |
|---|---|
| wall clock, reported grid | **86.44 s** against a cap of 5,400 s |
| peak RSS, reported grid | **94,208,000 bytes (89.8 MiB)** against a cap of 2 GiB |
| output bytes recorded in `compute.json` | 29,685,812 (28.3 MiB) - **see the caveat below** |
| programs | 28,000 |
| trials | 112,000 |
| enrolled pairs | 224,000,000 |
| looks | 224,112,000 |
| band evaluations | 1,344,672,000 |
| enclosure updates | 645,705,730 |

**Caveat on the output-bytes figure, reported rather than tidied away.** `compute.json`'s `output_bytes = 29,685,812` measures the whole output directory at the moment the grid finished, and that directory still held `comparison_*` files (about 25 MiB) left by an earlier, superseded comparison run. **`vrun.py`'s own outputs for this grid total 4,619,878 bytes (4.41 MiB)**, against the `T1` projection of 3,693,200 bytes - a 25% under-projection, far inside the 200 MiB cap either way. The 200 MiB cap was never approached by the grid.

**A second measured fact worth stating: the comparison step is the large writer.** After `vcompare.py` rewrote them, the `comparison_*` files total 204,237,211 bytes (194.78 MiB) - 282,384 defect rows - and the output directory now stands at 199.18 MiB. Section 8.3's 200 MiB rule governs the grid run, not the comparison step, so no rule was breached; the number is reported because a reader sizing this study's disk footprint should see it rather than discover it.

### 5.1 Per-cell compute

| cell | programs | trials | enrolled pairs | looks | band evaluations | enclosure updates |
|---|---|---|---|---|---|---|
| `C1` | 2,000 | 8,000 | 16,000,000 | 16,008,000 | 96,048,000 | 46,209,242 |
| `C2` | 2,000 | 8,000 | 16,000,000 | 16,008,000 | 96,048,000 | 46,101,225 |
| `C3` | 5,000 | 20,000 | 40,000,000 | 40,020,000 | 240,120,000 | 117,702,201 |
| `C4` | 5,000 | 20,000 | 40,000,000 | 40,020,000 | 240,120,000 | 117,195,542 |
| `C5` | 5,000 | 20,000 | 40,000,000 | 40,020,000 | 240,120,000 | 113,795,553 |
| `C6` | 5,000 | 20,000 | 40,000,000 | 40,020,000 | 240,120,000 | 113,708,702 |
| `C7` | 2,000 | 8,000 | 16,000,000 | 16,008,000 | 96,048,000 | 45,592,532 |
| `C8` | 2,000 | 8,000 | 16,000,000 | 16,008,000 | 96,048,000 | 45,400,733 |

Wall-clock seconds are **never** reported as a decision prefix, a latency, a throughput or a saving, and never as a paired comparison between constructions (sections 3 and 9.5).

---

## 6. Section 9.1 - per-gate simultaneous ever-miscoverage

Unit: trial. `N = programs x 4`. Nominal bound `alpha_gate = 0.00625` for `ever_miscover`, and each one-sided component is separately bounded by it. Wilson score 95% intervals at `z = 1.959963984540054`.

> **These intervals quantify Monte Carlo error of this simulation only.** They are not confidence intervals for the statistical guarantee, and a Wilson interval lying below a nominal level is not a proof that the level holds. Coverage here is coverage of a **bounded arbitrary-running-mean target of a synthetic stream** and establishes nothing causal. `NAIVE` is **invalid** under informative delay and is reported only to exhibit the failure mode. **An unflagged row means no exceedance was detected at this resolution, never that the bound holds.**

### 6.1 Look set: all looks to the finalization look

| cell | law | delay | construction | gate | `mu_g` | event | `x` | `N` | rate | Wilson 95% | nominal | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `C1` | `L1` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `ADAPTER` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `ADAPTER` | `success` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `ADAPTER` | `success` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_below` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_above` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `success` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `success` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_above` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `success` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `success` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_below` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `success` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `success` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_below` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `success` | +0.000 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `success` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 | **FLAGGED** |
| `C2` | `L1` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_below` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 | **FLAGGED** |
| `C2` | `L1` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `NAIVE` | `success` | +0.000 | `ever_miscover` | 10 | 8,000 | 0.001250 | [0.000679, 0.002300] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `NAIVE` | `success` | +0.000 | `ever_below` | 10 | 8,000 | 0.001250 | [0.000679, 0.002300] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `NAIVE` | `success` | +0.000 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `success` | +0.250 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `success` | +0.250 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 11 | 20,000 | 0.000550 | [0.000307, 0.000985] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_below` | 2 | 20,000 | 0.000100 | [0.000027, 0.000365] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_above` | 9 | 20,000 | 0.000450 | [0.000237, 0.000855] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `success` | +0.250 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `success` | +0.250 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 23 | 20,000 | 0.001150 | [0.000766, 0.001725] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_below` | 11 | 20,000 | 0.000550 | [0.000307, 0.000985] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_above` | 12 | 20,000 | 0.000600 | [0.000343, 0.001049] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `success` | +0.250 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `success` | +0.250 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 7 | 20,000 | 0.000350 | [0.000170, 0.000722] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_below` | 7 | 20,000 | 0.000350 | [0.000170, 0.000722] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `success` | +0.250 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `success` | +0.250 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 14 | 20,000 | 0.000700 | [0.000417, 0.001175] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_below` | 10 | 20,000 | 0.000500 | [0.000272, 0.000920] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_above` | 4 | 20,000 | 0.000200 | [0.000078, 0.000514] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `success` | +0.250 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `success` | +0.250 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 | **FLAGGED** |
| `C4` | `L2` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_below` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 | **FLAGGED** |
| `C4` | `L2` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `NAIVE` | `success` | +0.250 | `ever_miscover` | 126 | 20,000 | 0.006300 | [0.005294, 0.007495] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `NAIVE` | `success` | +0.250 | `ever_below` | 126 | 20,000 | 0.006300 | [0.005294, 0.007495] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `NAIVE` | `success` | +0.250 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `hierarchy` | +0.400 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `hierarchy` | +0.400 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `success` | -0.030 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `success` | -0.030 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `hierarchy` | +0.400 | `ever_miscover` | 1 | 20,000 | 0.000050 | [0.000009, 0.000283] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `hierarchy` | +0.400 | `ever_below` | 1 | 20,000 | 0.000050 | [0.000009, 0.000283] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `hierarchy` | +0.400 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `success` | -0.030 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `success` | -0.030 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `hierarchy` | +0.400 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `hierarchy` | +0.400 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `success` | -0.030 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `success` | -0.030 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `hierarchy` | +0.400 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `hierarchy` | +0.400 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `success` | -0.030 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `success` | -0.030 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `hierarchy` | +0.400 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `hierarchy` | +0.400 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `success` | -0.030 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `success` | -0.030 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `NAIVE` | `hierarchy` | +0.400 | `ever_miscover` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 | **FLAGGED** |
| `C6` | `L3` | `A` | `NAIVE` | `hierarchy` | +0.400 | `ever_below` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 | **FLAGGED** |
| `C6` | `L3` | `A` | `NAIVE` | `hierarchy` | +0.400 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `NAIVE` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `NAIVE` | `success` | -0.030 | `ever_below` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `NAIVE` | `success` | -0.030 | `ever_above` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `hierarchy` | +0.450 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `hierarchy` | +0.450 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `hierarchy` | +0.450 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `success` | +0.200 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `success` | +0.200 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `hierarchy` | +0.450 | `ever_miscover` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `hierarchy` | +0.450 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `hierarchy` | +0.450 | `ever_above` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `success` | +0.200 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `success` | +0.200 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `hierarchy` | +0.450 | `ever_miscover` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `hierarchy` | +0.450 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `hierarchy` | +0.450 | `ever_above` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `success` | +0.200 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `success` | +0.200 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `hierarchy` | +0.450 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `hierarchy` | +0.450 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `hierarchy` | +0.450 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `success` | +0.200 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `success` | +0.200 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `hierarchy` | +0.450 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `hierarchy` | +0.450 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `hierarchy` | +0.450 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `success` | +0.200 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `success` | +0.200 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `NAIVE` | `hierarchy` | +0.450 | `ever_miscover` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 | **FLAGGED** |
| `C8` | `L4` | `A` | `NAIVE` | `hierarchy` | +0.450 | `ever_below` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 | **FLAGGED** |
| `C8` | `L4` | `A` | `NAIVE` | `hierarchy` | +0.450 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `NAIVE` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `NAIVE` | `success` | +0.200 | `ever_below` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `NAIVE` | `success` | +0.200 | `ever_above` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |

### 6.2 Look set: restricted to `n >= n_min` (the secondary column of 9.1)

| cell | law | delay | construction | gate | `mu_g` | event | `x` | `N` | rate | Wilson 95% | nominal | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `C1` | `L1` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `ADAPTER` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `CPREFIX` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `L1` | `N` | `NAIVE` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `ADAPTER` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `CPREFIX` | `success` | +0.000 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `L1` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 | **FLAGGED** |
| `C2` | `L1` | `A` | `NAIVE` | `success` | +0.000 | `ever_miscover` | 10 | 8,000 | 0.001250 | [0.000679, 0.002300] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `ADAPTER` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 11 | 20,000 | 0.000550 | [0.000307, 0.000985] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `CPREFIX` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 23 | 20,000 | 0.001150 | [0.000766, 0.001725] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `L2` | `N` | `NAIVE` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `hierarchy` | +0.000 | `ever_miscover` | 7 | 20,000 | 0.000350 | [0.000170, 0.000722] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `ADAPTER` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `hierarchy` | +0.000 | `ever_miscover` | 14 | 20,000 | 0.000700 | [0.000417, 0.001175] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `CPREFIX` | `success` | +0.250 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `L2` | `A` | `NAIVE` | `hierarchy` | +0.000 | `ever_miscover` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 | **FLAGGED** |
| `C4` | `L2` | `A` | `NAIVE` | `success` | +0.250 | `ever_miscover` | 126 | 20,000 | 0.006300 | [0.005294, 0.007495] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `ADAPTER` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `hierarchy` | +0.400 | `ever_miscover` | 1 | 20,000 | 0.000050 | [0.000009, 0.000283] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `CPREFIX` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `L3` | `N` | `NAIVE` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `ADAPTER` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `hierarchy` | +0.400 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `CPREFIX` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `L3` | `A` | `NAIVE` | `hierarchy` | +0.400 | `ever_miscover` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 | **FLAGGED** |
| `C6` | `L3` | `A` | `NAIVE` | `success` | -0.030 | `ever_miscover` | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `hierarchy` | +0.450 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `ADAPTER` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `hierarchy` | +0.450 | `ever_miscover` | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `CPREFIX` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `hierarchy` | +0.450 | `ever_miscover` | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `L4` | `N` | `NAIVE` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `hierarchy` | +0.450 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `ADAPTER` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `hierarchy` | +0.450 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `CPREFIX` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `L4` | `A` | `NAIVE` | `hierarchy` | +0.450 | `ever_miscover` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 | **FLAGGED** |
| `C8` | `L4` | `A` | `NAIVE` | `success` | +0.200 | `ever_miscover` | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |

---

## 7. Section 9.2 - decision-level quantities

Every quantity, every cell, every construction. Unfavourable and inconclusive rows retained.

| cell | construction | quantity | unit | `x` | `N` | rate | Wilson 95% | nominal | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `C1` | `ADAPTER` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `ADAPTER` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C1` | `ADAPTER` | `correct_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `no_decision` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `ADAPTER` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C1` | `CPREFIX` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `CPREFIX` | `false_harm` | trial | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `CPREFIX` | `any_erroneous_trial` | trial | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | 0.0125 | no exceedance detected at this resolution |
| `C1` | `CPREFIX` | `correct_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `retain_incumbent` | trial | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `no_decision` | trial | 7,999 | 8,000 | 0.999875 | [0.999292, 0.999978] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `decided_at_finalization` | trial | 1 | 8,000 | 0.000125 | [0.000022, 0.000708] | - | (no bound; descriptive) |
| `C1` | `CPREFIX` | `family_any_erroneous` | program | 1 | 2,000 | 0.000500 | [0.000088, 0.002827] | 0.05 | no exceedance detected at this resolution |
| `C1` | `NAIVE` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `NAIVE` | `false_harm` | trial | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.00625 | no exceedance detected at this resolution |
| `C1` | `NAIVE` | `any_erroneous_trial` | trial | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | 0.0125 | no exceedance detected at this resolution |
| `C1` | `NAIVE` | `correct_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `retain_incumbent` | trial | 2 | 8,000 | 0.000250 | [0.000069, 0.000911] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `no_decision` | trial | 7,998 | 8,000 | 0.999750 | [0.999089, 0.999931] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C1` | `NAIVE` | `family_any_erroneous` | program | 2 | 2,000 | 0.001000 | [0.000274, 0.003639] | 0.05 | no exceedance detected at this resolution |
| `C2` | `ADAPTER` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `ADAPTER` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C2` | `ADAPTER` | `correct_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `no_decision` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `ADAPTER` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C2` | `CPREFIX` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `CPREFIX` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `CPREFIX` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C2` | `CPREFIX` | `correct_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `no_decision` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `CPREFIX` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C2` | `NAIVE` | `false_deploy` | trial | 404 | 8,000 | 0.050500 | [0.045914, 0.055518] | 0.00625 | **FLAGGED** |
| `C2` | `NAIVE` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C2` | `NAIVE` | `any_erroneous_trial` | trial | 404 | 8,000 | 0.050500 | [0.045914, 0.055518] | 0.0125 | **FLAGGED** |
| `C2` | `NAIVE` | `correct_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `deploy` | trial | 404 | 8,000 | 0.050500 | [0.045914, 0.055518] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `no_decision` | trial | 7,596 | 8,000 | 0.949500 | [0.944482, 0.954086] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `never_conjunct` | trial | 4 | 8,000 | 0.000500 | [0.000194, 0.001285] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `never_conjunct_all_looks` | trial | 4 | 8,000 | 0.000500 | [0.000194, 0.001285] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C2` | `NAIVE` | `family_any_erroneous` | program | 376 | 2,000 | 0.188000 | [0.171481, 0.205716] | 0.05 | **FLAGGED** |
| `C3` | `ADAPTER` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `ADAPTER` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C3` | `ADAPTER` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `ADAPTER` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C3` | `CPREFIX` | `false_deploy` | trial | 2 | 20,000 | 0.000100 | [0.000027, 0.000365] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `CPREFIX` | `false_harm` | trial | 9 | 20,000 | 0.000450 | [0.000237, 0.000855] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `CPREFIX` | `any_erroneous_trial` | trial | 11 | 20,000 | 0.000550 | [0.000307, 0.000985] | 0.0125 | no exceedance detected at this resolution |
| `C3` | `CPREFIX` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `deploy` | trial | 2 | 20,000 | 0.000100 | [0.000027, 0.000365] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `retain_incumbent` | trial | 9 | 20,000 | 0.000450 | [0.000237, 0.000855] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `no_decision` | trial | 19,989 | 20,000 | 0.999450 | [0.999015, 0.999693] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `decided_at_finalization` | trial | 1 | 20,000 | 0.000050 | [0.000009, 0.000283] | - | (no bound; descriptive) |
| `C3` | `CPREFIX` | `family_any_erroneous` | program | 11 | 5,000 | 0.002200 | [0.001229, 0.003935] | 0.05 | no exceedance detected at this resolution |
| `C3` | `NAIVE` | `false_deploy` | trial | 11 | 20,000 | 0.000550 | [0.000307, 0.000985] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `NAIVE` | `false_harm` | trial | 12 | 20,000 | 0.000600 | [0.000343, 0.001049] | 0.00625 | no exceedance detected at this resolution |
| `C3` | `NAIVE` | `any_erroneous_trial` | trial | 23 | 20,000 | 0.001150 | [0.000766, 0.001725] | 0.0125 | no exceedance detected at this resolution |
| `C3` | `NAIVE` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `deploy` | trial | 11 | 20,000 | 0.000550 | [0.000307, 0.000985] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `retain_incumbent` | trial | 12 | 20,000 | 0.000600 | [0.000343, 0.001049] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `no_decision` | trial | 19,977 | 20,000 | 0.998850 | [0.998275, 0.999234] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C3` | `NAIVE` | `family_any_erroneous` | program | 23 | 5,000 | 0.004600 | [0.003067, 0.006893] | 0.05 | no exceedance detected at this resolution |
| `C4` | `ADAPTER` | `false_deploy` | trial | 5 | 20,000 | 0.000250 | [0.000107, 0.000585] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `ADAPTER` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `ADAPTER` | `any_erroneous_trial` | trial | 5 | 20,000 | 0.000250 | [0.000107, 0.000585] | 0.0125 | no exceedance detected at this resolution |
| `C4` | `ADAPTER` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `deploy` | trial | 5 | 20,000 | 0.000250 | [0.000107, 0.000585] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `no_decision` | trial | 19,995 | 20,000 | 0.999750 | [0.999415, 0.999893] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `never_conjunct` | trial | 2 | 20,000 | 0.000100 | [0.000027, 0.000365] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `never_conjunct_all_looks` | trial | 2 | 20,000 | 0.000100 | [0.000027, 0.000365] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `ADAPTER` | `family_any_erroneous` | program | 5 | 5,000 | 0.001000 | [0.000427, 0.002339] | 0.05 | no exceedance detected at this resolution |
| `C4` | `CPREFIX` | `false_deploy` | trial | 10 | 20,000 | 0.000500 | [0.000272, 0.000920] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `CPREFIX` | `false_harm` | trial | 4 | 20,000 | 0.000200 | [0.000078, 0.000514] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `CPREFIX` | `any_erroneous_trial` | trial | 14 | 20,000 | 0.000700 | [0.000417, 0.001175] | 0.0125 | no exceedance detected at this resolution |
| `C4` | `CPREFIX` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `deploy` | trial | 10 | 20,000 | 0.000500 | [0.000272, 0.000920] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `retain_incumbent` | trial | 4 | 20,000 | 0.000200 | [0.000078, 0.000514] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `no_decision` | trial | 19,986 | 20,000 | 0.999300 | [0.998825, 0.999583] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `CPREFIX` | `family_any_erroneous` | program | 14 | 5,000 | 0.002800 | [0.001669, 0.004695] | 0.05 | no exceedance detected at this resolution |
| `C4` | `NAIVE` | `false_deploy` | trial | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 | **FLAGGED** |
| `C4` | `NAIVE` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C4` | `NAIVE` | `any_erroneous_trial` | trial | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.0125 | **FLAGGED** |
| `C4` | `NAIVE` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `deploy` | trial | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `no_decision` | trial | 2 | 20,000 | 0.000100 | [0.000027, 0.000365] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C4` | `NAIVE` | `family_any_erroneous` | program | 5,000 | 5,000 | 1.000000 | [0.999232, 1.000000] | 0.05 | **FLAGGED** |
| `C5` | `ADAPTER` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `ADAPTER` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C5` | `ADAPTER` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `ADAPTER` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C5` | `CPREFIX` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `CPREFIX` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `CPREFIX` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C5` | `CPREFIX` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `CPREFIX` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C5` | `NAIVE` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `NAIVE` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C5` | `NAIVE` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C5` | `NAIVE` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C5` | `NAIVE` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C6` | `ADAPTER` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `ADAPTER` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C6` | `ADAPTER` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `ADAPTER` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C6` | `CPREFIX` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `CPREFIX` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `CPREFIX` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C6` | `CPREFIX` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `CPREFIX` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C6` | `NAIVE` | `false_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `NAIVE` | `false_harm` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.00625 | no exceedance detected at this resolution |
| `C6` | `NAIVE` | `any_erroneous_trial` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | 0.0125 | no exceedance detected at this resolution |
| `C6` | `NAIVE` | `correct_deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `deploy` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `retain_incumbent` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `no_decision` | trial | 20,000 | 20,000 | 1.000000 | [0.999808, 1.000000] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `conflict` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `never_conjunct` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `decided_at_finalization` | trial | 0 | 20,000 | 0.000000 | [0.000000, 0.000192] | - | (no bound; descriptive) |
| `C6` | `NAIVE` | `family_any_erroneous` | program | 0 | 5,000 | 0.000000 | [0.000000, 0.000768] | 0.05 | no exceedance detected at this resolution |
| `C7` | `ADAPTER` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `ADAPTER` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C7` | `ADAPTER` | `correct_deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `no_decision` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `ADAPTER` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C7` | `CPREFIX` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `CPREFIX` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `CPREFIX` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C7` | `CPREFIX` | `correct_deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `no_decision` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `CPREFIX` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C7` | `NAIVE` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `NAIVE` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C7` | `NAIVE` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C7` | `NAIVE` | `correct_deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `no_decision` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C7` | `NAIVE` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C8` | `ADAPTER` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `ADAPTER` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `ADAPTER` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C8` | `ADAPTER` | `correct_deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `no_decision` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `ADAPTER` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C8` | `CPREFIX` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `CPREFIX` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `CPREFIX` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C8` | `CPREFIX` | `correct_deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `no_decision` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `CPREFIX` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |
| `C8` | `NAIVE` | `false_deploy` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `NAIVE` | `false_harm` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.00625 | no exceedance detected at this resolution |
| `C8` | `NAIVE` | `any_erroneous_trial` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | 0.0125 | no exceedance detected at this resolution |
| `C8` | `NAIVE` | `correct_deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `deploy` | trial | 8,000 | 8,000 | 1.000000 | [0.999520, 1.000000] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `retain_incumbent` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `no_decision` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `conflict` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `never_conjunct` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `never_conjunct_all_looks` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `decided_at_finalization` | trial | 0 | 8,000 | 0.000000 | [0.000000, 0.000480] | - | (no bound; descriptive) |
| `C8` | `NAIVE` | `family_any_erroneous` | program | 0 | 2,000 | 0.000000 | [0.000000, 0.001917] | 0.05 | no exceedance detected at this resolution |

**Identities asserted by `vrun.py` as it tabulated** (section 9.2): under these four laws `mu_h >= 0` always, so `false_harm` is exactly the `RETAIN_INCUMBENT` rate in every cell; `false_deploy` is exactly the `DEPLOY` rate in `C1`-`C6` and exactly `0` in `C7`/`C8`. The run completed without tripping either assertion.

**`never_conjunct` is nonzero**, which is the point of reporting it: `C4`/`ADAPTER` has `x = 2` of 20,000 and `C2`/`NAIVE` has `x = 4` of 8,000. The same-look conjunction requirement is therefore doing work rather than restating the two marginal conditions.

**`conflict` is zero in every cell and every construction** - no look ever satisfied both decision conditions at once.

---

## 8. Section 9.3 - the exceedance flags, and section 9.4 - the positive control

### 8.1 Every flag raised in this run

| cell | construction | table | quantity / gate | `x` | `N` | rate | Wilson 95% | nominal |
|---|---|---|---|---|---|---|---|---|
| `C2` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_miscover` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 |
| `C2` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_below` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 |
| `C2` | `NAIVE` | 9.1 (`looks=decision_eligible`) | `hierarchy` / `ever_miscover` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 |
| `C4` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_miscover` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 |
| `C4` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_below` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 |
| `C4` | `NAIVE` | 9.1 (`looks=decision_eligible`) | `hierarchy` / `ever_miscover` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 |
| `C6` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_miscover` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 |
| `C6` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_below` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 |
| `C6` | `NAIVE` | 9.1 (`looks=decision_eligible`) | `hierarchy` / `ever_miscover` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 |
| `C8` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_miscover` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 |
| `C8` | `NAIVE` | 9.1 (`looks=all`) | `hierarchy` / `ever_below` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 |
| `C8` | `NAIVE` | 9.1 (`looks=decision_eligible`) | `hierarchy` / `ever_miscover` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 |
| `C2` | `NAIVE` | 9.2 | `false_deploy` | 404 | 8,000 | 0.050500 | [0.045914, 0.055518] | 0.00625 |
| `C2` | `NAIVE` | 9.2 | `any_erroneous_trial` | 404 | 8,000 | 0.050500 | [0.045914, 0.055518] | 0.0125 |
| `C2` | `NAIVE` | 9.2 | `family_any_erroneous` | 376 | 2,000 | 0.188000 | [0.171481, 0.205716] | 0.05 |
| `C4` | `NAIVE` | 9.2 | `false_deploy` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 |
| `C4` | `NAIVE` | 9.2 | `any_erroneous_trial` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.0125 |
| `C4` | `NAIVE` | 9.2 | `family_any_erroneous` | 5,000 | 5,000 | 1.000000 | [0.999232, 1.000000] | 0.05 |
| `C2` | `NAIVE` | 9.6 (`n=500`) | `miscover_h_so_far` | 7,861 | 8,000 | 0.982625 | [0.979521, 0.985265] | 0.00625 |
| `C2` | `NAIVE` | 9.6 (`n=2000`) | `miscover_h_so_far` | 7,910 | 8,000 | 0.988750 | [0.986193, 0.990838] | 0.00625 |
| `C4` | `NAIVE` | 9.6 (`n=100`) | `miscover_h_so_far` | 857 | 20,000 | 0.042850 | [0.040130, 0.045746] | 0.00625 |
| `C4` | `NAIVE` | 9.6 (`n=500`) | `miscover_h_so_far` | 19,996 | 20,000 | 0.999800 | [0.999486, 0.999922] | 0.00625 |
| `C4` | `NAIVE` | 9.6 (`n=2000`) | `miscover_h_so_far` | 19,998 | 20,000 | 0.999900 | [0.999635, 0.999973] | 0.00625 |
| `C6` | `NAIVE` | 9.6 (`n=500`) | `miscover_h_so_far` | 15,215 | 20,000 | 0.760750 | [0.754788, 0.766612] | 0.00625 |
| `C6` | `NAIVE` | 9.6 (`n=2000`) | `miscover_h_so_far` | 16,272 | 20,000 | 0.813600 | [0.808143, 0.818937] | 0.00625 |
| `C8` | `NAIVE` | 9.6 (`n=500`) | `miscover_h_so_far` | 4,986 | 8,000 | 0.623250 | [0.612575, 0.633807] | 0.00625 |
| `C8` | `NAIVE` | 9.6 (`n=2000`) | `miscover_h_so_far` | 5,550 | 8,000 | 0.693750 | [0.683559, 0.703756] | 0.00625 |

**Every flag in this run is on `NAIVE`.** No `ADAPTER` row and no `CPREFIX` row is flagged in any table, in any cell, on any gate, at any horizon. A flag on `NAIVE` in an `A` cell is the **expected** behaviour of an invalid rule and is the positive control, not a defect (section 9.3).

### 8.2 The positive control verdict

> **Precommitted positive control (section 9.4, frozen text).** `NAIVE`'s hierarchy ever-miscoverage must be FLAGGED in at least one of `C2`, `C4`, `C6`. If it is not, the **measurement apparatus itself is reported as unvalidated**, the `ADAPTER` results of this run are reported as uninterpretable, and the cause is investigated before any of them is cited.

**VERDICT: PASSED.** `NAIVE`'s hierarchy ever-miscoverage is FLAGGED in **`C2`, `C4`, `C6`** - all three of the precommitted cells, not merely one - and additionally in `C8`. The measuring apparatus can detect a real violation, so the `ADAPTER` results of this run are interpretable under the limits of section 1.3.

The magnitudes, for the record: `C2` 0.988750 [0.986193, 0.990838], `C4` 0.999900 [0.999635, 0.999973], `C6` 0.813600 [0.808143, 0.818937], against a nominal `0.00625`. The exceedance is not marginal; it is two to three orders of magnitude.

The control is stated on the **hierarchy gate only**. No success-gate positive control is precommitted, and the success rows are reported without a pass/fail attached (section 9.4).

### 8.3 What the absence of an `ADAPTER` flag does and does not mean

Every unflagged `ADAPTER` and `CPREFIX` row above is reported as **no exceedance was detected at this resolution**. It is **not** reported as *the bound holds*, and this report does not say the bound holds anywhere. Section 9.3 fixes the resolution: with `x = 0` events the Wilson interval is `[0, 0.000480]` at `N = 8,000` and `[0, 0.000192]` at `N = 20,000`; the design can only flag a per-gate rate at or above `1.280x` nominal at 2,000 programs and `1.176x` nominal at 5,000. **A violation smaller than that would pass unflagged** (section 1.3 item 5).

---

## 9. Section 9.5 - decision prefixes and resolution quantities

### 9.1 Decision prefixes, in enrolled pairs

Never wall clock, never a throughput or a saving, and never a paired comparison between constructions.

| cell | construction | trials | deciding fraction | capped fraction | capped Q1/median/Q3 | conditional Q1/median/Q3 |
|---|---|---|---|---|---|---|
| `C1` | `ADAPTER` | 8,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C1` | `CPREFIX` | 8,000 | 0.000125 | 0.999875 | 2000 / 2000 / 2000 | 2000 / 2000 / 2000 |
| `C1` | `NAIVE` | 8,000 | 0.00025 | 0.99975 | 2000 / 2000 / 2000 | 664.75 / 916.5 / 1168.25 |
| `C2` | `ADAPTER` | 8,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C2` | `CPREFIX` | 8,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C2` | `NAIVE` | 8,000 | 0.0505 | 0.9495 | 2000 / 2000 / 2000 | 463 / 598 / 912.5 |
| `C3` | `ADAPTER` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C3` | `CPREFIX` | 20,000 | 0.00055 | 0.99945 | 2000 / 2000 / 2000 | 1144 / 1291 / 1699 |
| `C3` | `NAIVE` | 20,000 | 0.00115 | 0.99885 | 2000 / 2000 / 2000 | 414 / 720 / 1446 |
| `C4` | `ADAPTER` | 20,000 | 0.00025 | 0.99975 | 2000 / 2000 / 2000 | 733 / 760 / 1456 |
| `C4` | `CPREFIX` | 20,000 | 0.0007 | 0.9993 | 2000 / 2000 / 2000 | 1162 / 1310 / 1445.25 |
| `C4` | `NAIVE` | 20,000 | 0.9999 | 9.999999999998899e-05 | 159 / 169 / 187 | 159 / 169 / 187 |
| `C5` | `ADAPTER` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C5` | `CPREFIX` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C5` | `NAIVE` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C6` | `ADAPTER` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C6` | `CPREFIX` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C6` | `NAIVE` | 20,000 | 0 | 1 | 2000 / 2000 / 2000 | NA / NA / NA |
| `C7` | `ADAPTER` | 8,000 | 1 | 0 | 621 / 683 / 745 | 621 / 683 / 745 |
| `C7` | `CPREFIX` | 8,000 | 1 | 0 | 868 / 917 / 968 | 868 / 917 / 968 |
| `C7` | `NAIVE` | 8,000 | 1 | 0 | 297 / 340 / 391 | 297 / 340 / 391 |
| `C8` | `ADAPTER` | 8,000 | 1 | 0 | 485 / 550 / 615 | 485 / 550 / 615 |
| `C8` | `CPREFIX` | 8,000 | 1 | 0 | 865 / 915 / 965 | 865 / 915 / 965 |
| `C8` | `NAIVE` | 8,000 | 1 | 0 | 199 / 225 / 254 | 199 / 225 / 254 |

`NA` in the conditional columns means the cell/construction produced **no deciding trial at all**; the capped column is always printed beside it, as section 9.5 requires.

### 9.2 Resolution quantities, all constructions

At the deciding look, or at the finalization look for non-deciding trials.

| cell | construction | quantity | `N` | mean | Q1 | median | Q3 |
|---|---|---|---|---|---|---|---|
| `C1` | `ADAPTER` | `unresolved_fraction` | 8,000 | 0.0292343125 | 0.027 | 0.029 | 0.0315 |
| `C1` | `ADAPTER` | `unrevealed_fraction` | 8,000 | 0.008799125 | 0.0075 | 0.0085 | 0.01 |
| `C1` | `ADAPTER` | `cost_collapsed_fraction` | 8,000 | 0.007651937500000001 | 0.0065 | 0.0075 | 0.009 |
| `C1` | `ADAPTER` | `cost_narrowed_fraction` | 8,000 | 0.007780312500000001 | 0.0065 | 0.0075 | 0.009 |
| `C1` | `ADAPTER` | `n_certified` | 8,000 | 1941.531375 | 1937 | 1942 | 1946 |
| `C1` | `ADAPTER` | `n_point_resolved` | 8,000 | 1956.83525 | 1953 | 1957 | 1961 |
| `C1` | `ADAPTER` | `look_prefix` | 8,000 | 2000 | 2000 | 2000 | 2000 |
| `C1` | `CPREFIX` | `unresolved_fraction` | 8,000 | 0.0292343125 | 0.027 | 0.029 | 0.0315 |
| `C1` | `CPREFIX` | `unrevealed_fraction` | 8,000 | 0.008799125 | 0.0075 | 0.0085 | 0.01 |
| `C1` | `CPREFIX` | `cost_collapsed_fraction` | 8,000 | 0.007651937500000001 | 0.0065 | 0.0075 | 0.009 |
| `C1` | `CPREFIX` | `cost_narrowed_fraction` | 8,000 | 0.007780312500000001 | 0.0065 | 0.0075 | 0.009 |
| `C1` | `CPREFIX` | `n_certified` | 8,000 | 1941.531375 | 1937 | 1942 | 1946 |
| `C1` | `CPREFIX` | `n_point_resolved` | 8,000 | 1956.83525 | 1953 | 1957 | 1961 |
| `C1` | `CPREFIX` | `look_prefix` | 8,000 | 2000 | 2000 | 2000 | 2000 |
| `C1` | `NAIVE` | `unresolved_fraction` | 8,000 | 0.029267662737015313 | 0.027 | 0.029 | 0.0315 |
| `C1` | `NAIVE` | `unrevealed_fraction` | 8,000 | 0.00881925958505269 | 0.0075 | 0.0085 | 0.01 |
| `C1` | `NAIVE` | `cost_collapsed_fraction` | 8,000 | 0.0076556103741090625 | 0.0065 | 0.0075 | 0.009 |
| `C1` | `NAIVE` | `cost_narrowed_fraction` | 8,000 | 0.007783985374109062 | 0.0065 | 0.0075 | 0.009 |
| `C1` | `NAIVE` | `n_certified` | 8,000 | 1941.249625 | 1937 | 1942 | 1946 |
| `C1` | `NAIVE` | `n_point_resolved` | 8,000 | 1956.552875 | 1953 | 1957 | 1961 |
| `C1` | `NAIVE` | `look_prefix` | 8,000 | 1999.729125 | 2000 | 2000 | 2000 |
| `C2` | `ADAPTER` | `unresolved_fraction` | 8,000 | 0.029179250000000007 | 0.027 | 0.029 | 0.0315 |
| `C2` | `ADAPTER` | `unrevealed_fraction` | 8,000 | 0.008757437500000001 | 0.0075 | 0.0085 | 0.01 |
| `C2` | `ADAPTER` | `cost_collapsed_fraction` | 8,000 | 0.010219250000000003 | 0.0085 | 0.01 | 0.0115 |
| `C2` | `ADAPTER` | `cost_narrowed_fraction` | 8,000 | 0.010219250000000003 | 0.0085 | 0.01 | 0.0115 |
| `C2` | `ADAPTER` | `n_certified` | 8,000 | 1941.6415 | 1937 | 1942 | 1946 |
| `C2` | `ADAPTER` | `n_point_resolved` | 8,000 | 1962.08 | 1958 | 1962 | 1966 |
| `C2` | `ADAPTER` | `look_prefix` | 8,000 | 2000 | 2000 | 2000 | 2000 |
| `C2` | `CPREFIX` | `unresolved_fraction` | 8,000 | 0.029179250000000007 | 0.027 | 0.029 | 0.0315 |
| `C2` | `CPREFIX` | `unrevealed_fraction` | 8,000 | 0.008757437500000001 | 0.0075 | 0.0085 | 0.01 |
| `C2` | `CPREFIX` | `cost_collapsed_fraction` | 8,000 | 0.010219250000000003 | 0.0085 | 0.01 | 0.0115 |
| `C2` | `CPREFIX` | `cost_narrowed_fraction` | 8,000 | 0.010219250000000003 | 0.0085 | 0.01 | 0.0115 |
| `C2` | `CPREFIX` | `n_certified` | 8,000 | 1941.6415 | 1937 | 1942 | 1946 |
| `C2` | `CPREFIX` | `n_point_resolved` | 8,000 | 1962.08 | 1958 | 1962 | 1966 |
| `C2` | `CPREFIX` | `look_prefix` | 8,000 | 2000 | 2000 | 2000 | 2000 |
| `C2` | `NAIVE` | `unresolved_fraction` | 8,000 | 0.036729022357932066 | 0.027 | 0.0295 | 0.032 |
| `C2` | `NAIVE` | `unrevealed_fraction` | 8,000 | 0.013130589368271476 | 0.0075 | 0.009 | 0.0105 |
| `C2` | `NAIVE` | `cost_collapsed_fraction` | 8,000 | 0.011550848103811087 | 0.009 | 0.0105 | 0.012 |
| `C2` | `NAIVE` | `cost_narrowed_fraction` | 8,000 | 0.011580218908612641 | 0.009 | 0.0105 | 0.012 |
| `C2` | `NAIVE` | `n_certified` | 8,000 | 1875.34325 | 1936 | 1941 | 1946 |
| `C2` | `NAIVE` | `n_point_resolved` | 8,000 | 1895.93225 | 1958 | 1962 | 1966 |
| `C2` | `NAIVE` | `look_prefix` | 8,000 | 1936.288125 | 2000 | 2000 | 2000 |
| `C3` | `ADAPTER` | `unresolved_fraction` | 20,000 | 0.035100525 | 0.0325 | 0.035 | 0.0375 |
| `C3` | `ADAPTER` | `unrevealed_fraction` | 20,000 | 0.010559125 | 0.009 | 0.0105 | 0.012 |
| `C3` | `ADAPTER` | `cost_collapsed_fraction` | 20,000 | 0.011050174999999999 | 0.0095 | 0.011 | 0.0125 |
| `C3` | `ADAPTER` | `cost_narrowed_fraction` | 20,000 | 0.01120185 | 0.0095 | 0.011 | 0.0125 |
| `C3` | `ADAPTER` | `n_certified` | 20,000 | 1929.79895 | 1925 | 1930 | 1935 |
| `C3` | `ADAPTER` | `n_point_resolved` | 20,000 | 1951.8993 | 1948 | 1952 | 1956 |
| `C3` | `ADAPTER` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C3` | `CPREFIX` | `unresolved_fraction` | 20,000 | 0.035139329393500666 | 0.0325 | 0.035 | 0.0375 |
| `C3` | `CPREFIX` | `unrevealed_fraction` | 20,000 | 0.010581496534240486 | 0.009 | 0.0105 | 0.012 |
| `C3` | `CPREFIX` | `cost_collapsed_fraction` | 20,000 | 0.011055922496633327 | 0.0095 | 0.011 | 0.0125 |
| `C3` | `CPREFIX` | `cost_narrowed_fraction` | 20,000 | 0.011207731947503649 | 0.0095 | 0.011 | 0.0125 |
| `C3` | `CPREFIX` | `n_certified` | 20,000 | 1929.43125 | 1925 | 1930 | 1935 |
| `C3` | `CPREFIX` | `n_point_resolved` | 20,000 | 1951.535 | 1948 | 1952 | 1956 |
| `C3` | `CPREFIX` | `look_prefix` | 20,000 | 1999.669 | 2000 | 2000 | 2000 |
| `C3` | `NAIVE` | `unresolved_fraction` | 20,000 | 0.035281958931741554 | 0.0325 | 0.035 | 0.0375 |
| `C3` | `NAIVE` | `unrevealed_fraction` | 20,000 | 0.010665089338339739 | 0.009 | 0.0105 | 0.012 |
| `C3` | `NAIVE` | `cost_collapsed_fraction` | 20,000 | 0.01108243368436084 | 0.0095 | 0.011 | 0.0125 |
| `C3` | `NAIVE` | `cost_narrowed_fraction` | 20,000 | 0.011235096935459338 | 0.0095 | 0.011 | 0.0125 |
| `C3` | `NAIVE` | `n_certified` | 20,000 | 1928.46285 | 1925 | 1930 | 1935 |
| `C3` | `NAIVE` | `n_point_resolved` | 20,000 | 1950.5688 | 1948 | 1952 | 1956 |
| `C3` | `NAIVE` | `look_prefix` | 20,000 | 1998.7321 | 2000 | 2000 | 2000 |
| `C4` | `ADAPTER` | `unresolved_fraction` | 20,000 | 0.03511992283951667 | 0.0325 | 0.035 | 0.0375 |
| `C4` | `ADAPTER` | `unrevealed_fraction` | 20,000 | 0.01055913623297738 | 0.009 | 0.0105 | 0.012 |
| `C4` | `ADAPTER` | `cost_collapsed_fraction` | 20,000 | 0.012265819386688992 | 0.0105 | 0.012 | 0.014 |
| `C4` | `ADAPTER` | `cost_narrowed_fraction` | 20,000 | 0.01226594692910272 | 0.0105 | 0.012 | 0.014 |
| `C4` | `ADAPTER` | `n_certified` | 20,000 | 1929.5635 | 1925 | 1930 | 1935 |
| `C4` | `ADAPTER` | `n_point_resolved` | 20,000 | 1954.0857 | 1950 | 1954 | 1959 |
| `C4` | `ADAPTER` | `look_prefix` | 20,000 | 1999.76815 | 2000 | 2000 | 2000 |
| `C4` | `CPREFIX` | `unresolved_fraction` | 20,000 | 0.0351526391265268 | 0.0325 | 0.035 | 0.0375 |
| `C4` | `CPREFIX` | `unrevealed_fraction` | 20,000 | 0.010579368281952774 | 0.009 | 0.0105 | 0.012 |
| `C4` | `CPREFIX` | `cost_collapsed_fraction` | 20,000 | 0.012271358259230213 | 0.0105 | 0.012 | 0.014 |
| `C4` | `CPREFIX` | `cost_narrowed_fraction` | 20,000 | 0.012271611040268277 | 0.0105 | 0.012 | 0.014 |
| `C4` | `CPREFIX` | `n_certified` | 20,000 | 1929.281 | 1925 | 1930 | 1935 |
| `C4` | `CPREFIX` | `n_point_resolved` | 20,000 | 1953.8089 | 1950 | 1954 | 1959 |
| `C4` | `CPREFIX` | `look_prefix` | 20,000 | 1999.52405 | 2000 | 2000 | 2000 |
| `C4` | `NAIVE` | `unresolved_fraction` | 20,000 | 0.35981860017435346 | 0.33774834437086093 | 0.36 | 0.38271604938271603 |
| `C4` | `NAIVE` | `unrevealed_fraction` | 20,000 | 0.25754023341469096 | 0.23626373626373626 | 0.2578947368421053 | 0.2795031055900621 |
| `C4` | `NAIVE` | `cost_collapsed_fraction` | 20,000 | 0.035731277659490475 | 0.025252525252525252 | 0.03494976639081443 | 0.045204837748062346 |
| `C4` | `NAIVE` | `cost_narrowed_fraction` | 20,000 | 0.038059393452076325 | 0.026881720430107527 | 0.0374331550802139 | 0.04790419161676647 |
| `C4` | `NAIVE` | `n_certified` | 20,000 | 113.22505 | 100 | 106 | 120 |
| `C4` | `NAIVE` | `n_point_resolved` | 20,000 | 119.67815 | 106 | 112 | 127 |
| `C4` | `NAIVE` | `look_prefix` | 20,000 | 176.85615 | 159 | 169 | 187 |
| `C5` | `ADAPTER` | `unresolved_fraction` | 20,000 | 0.01716145 | 0.015 | 0.017 | 0.019 |
| `C5` | `ADAPTER` | `unrevealed_fraction` | 20,000 | 0.005161025 | 0.004 | 0.005 | 0.006 |
| `C5` | `ADAPTER` | `cost_collapsed_fraction` | 20,000 | 0.0050396 | 0.004 | 0.005 | 0.006 |
| `C5` | `ADAPTER` | `cost_narrowed_fraction` | 20,000 | 0.0050837 | 0.004 | 0.005 | 0.006 |
| `C5` | `ADAPTER` | `n_certified` | 20,000 | 1965.6771 | 1962 | 1966 | 1970 |
| `C5` | `ADAPTER` | `n_point_resolved` | 20,000 | 1975.7563 | 1973 | 1976 | 1979 |
| `C5` | `ADAPTER` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C5` | `CPREFIX` | `unresolved_fraction` | 20,000 | 0.01716145 | 0.015 | 0.017 | 0.019 |
| `C5` | `CPREFIX` | `unrevealed_fraction` | 20,000 | 0.005161025 | 0.004 | 0.005 | 0.006 |
| `C5` | `CPREFIX` | `cost_collapsed_fraction` | 20,000 | 0.0050396 | 0.004 | 0.005 | 0.006 |
| `C5` | `CPREFIX` | `cost_narrowed_fraction` | 20,000 | 0.0050837 | 0.004 | 0.005 | 0.006 |
| `C5` | `CPREFIX` | `n_certified` | 20,000 | 1965.6771 | 1962 | 1966 | 1970 |
| `C5` | `CPREFIX` | `n_point_resolved` | 20,000 | 1975.7563 | 1973 | 1976 | 1979 |
| `C5` | `CPREFIX` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C5` | `NAIVE` | `unresolved_fraction` | 20,000 | 0.01716145 | 0.015 | 0.017 | 0.019 |
| `C5` | `NAIVE` | `unrevealed_fraction` | 20,000 | 0.005161025 | 0.004 | 0.005 | 0.006 |
| `C5` | `NAIVE` | `cost_collapsed_fraction` | 20,000 | 0.0050396 | 0.004 | 0.005 | 0.006 |
| `C5` | `NAIVE` | `cost_narrowed_fraction` | 20,000 | 0.0050837 | 0.004 | 0.005 | 0.006 |
| `C5` | `NAIVE` | `n_certified` | 20,000 | 1965.6771 | 1962 | 1966 | 1970 |
| `C5` | `NAIVE` | `n_point_resolved` | 20,000 | 1975.7563 | 1973 | 1976 | 1979 |
| `C5` | `NAIVE` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C6` | `ADAPTER` | `unresolved_fraction` | 20,000 | 0.017150625000000003 | 0.015 | 0.017 | 0.019 |
| `C6` | `ADAPTER` | `unrevealed_fraction` | 20,000 | 0.005157225 | 0.004 | 0.005 | 0.006 |
| `C6` | `ADAPTER` | `cost_collapsed_fraction` | 20,000 | 0.0059991 | 0.005 | 0.006 | 0.007 |
| `C6` | `ADAPTER` | `cost_narrowed_fraction` | 20,000 | 0.0059991 | 0.005 | 0.006 | 0.007 |
| `C6` | `ADAPTER` | `n_certified` | 20,000 | 1965.69875 | 1962 | 1966 | 1970 |
| `C6` | `ADAPTER` | `n_point_resolved` | 20,000 | 1977.69695 | 1975 | 1978 | 1981 |
| `C6` | `ADAPTER` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C6` | `CPREFIX` | `unresolved_fraction` | 20,000 | 0.017150625000000003 | 0.015 | 0.017 | 0.019 |
| `C6` | `CPREFIX` | `unrevealed_fraction` | 20,000 | 0.005157225 | 0.004 | 0.005 | 0.006 |
| `C6` | `CPREFIX` | `cost_collapsed_fraction` | 20,000 | 0.0059991 | 0.005 | 0.006 | 0.007 |
| `C6` | `CPREFIX` | `cost_narrowed_fraction` | 20,000 | 0.0059991 | 0.005 | 0.006 | 0.007 |
| `C6` | `CPREFIX` | `n_certified` | 20,000 | 1965.69875 | 1962 | 1966 | 1970 |
| `C6` | `CPREFIX` | `n_point_resolved` | 20,000 | 1977.69695 | 1975 | 1978 | 1981 |
| `C6` | `CPREFIX` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C6` | `NAIVE` | `unresolved_fraction` | 20,000 | 0.017150625000000003 | 0.015 | 0.017 | 0.019 |
| `C6` | `NAIVE` | `unrevealed_fraction` | 20,000 | 0.005157225 | 0.004 | 0.005 | 0.006 |
| `C6` | `NAIVE` | `cost_collapsed_fraction` | 20,000 | 0.0059991 | 0.005 | 0.006 | 0.007 |
| `C6` | `NAIVE` | `cost_narrowed_fraction` | 20,000 | 0.0059991 | 0.005 | 0.006 | 0.007 |
| `C6` | `NAIVE` | `n_certified` | 20,000 | 1965.69875 | 1962 | 1966 | 1970 |
| `C6` | `NAIVE` | `n_point_resolved` | 20,000 | 1977.69695 | 1975 | 1978 | 1981 |
| `C6` | `NAIVE` | `look_prefix` | 20,000 | 2000 | 2000 | 2000 | 2000 |
| `C7` | `ADAPTER` | `unresolved_fraction` | 8,000 | 0.09777227707814555 | 0.0891238670694864 | 0.09717868338557993 | 0.10600706713780919 |
| `C7` | `ADAPTER` | `unrevealed_fraction` | 8,000 | 0.04736352596526486 | 0.04184704184704185 | 0.04692556634304207 | 0.05247485586652738 |
| `C7` | `ADAPTER` | `cost_collapsed_fraction` | 8,000 | 0.019954221996908376 | 0.01592356687898089 | 0.01943198804185351 | 0.02358490566037736 |
| `C7` | `ADAPTER` | `cost_narrowed_fraction` | 8,000 | 0.020618444444644262 | 0.01653944020356234 | 0.020114942528735632 | 0.024320457796852647 |
| `C7` | `ADAPTER` | `n_certified` | 8,000 | 618.465375 | 558 | 616 | 677 |
| `C7` | `ADAPTER` | `n_point_resolved` | 8,000 | 631.96675 | 571 | 630 | 690 |
| `C7` | `ADAPTER` | `look_prefix` | 8,000 | 684.721875 | 621 | 683 | 745 |
| `C7` | `CPREFIX` | `unresolved_fraction` | 8,000 | 0.07337956204821705 | 0.06666666666666667 | 0.07288805552910615 | 0.07965476881628235 |
| `C7` | `CPREFIX` | `unrevealed_fraction` | 8,000 | 0.037238724046863306 | 0.03275109170305677 | 0.03699551569506727 | 0.04152637485970819 |
| `C7` | `CPREFIX` | `cost_collapsed_fraction` | 8,000 | 0.01416558619676125 | 0.011339621759356664 | 0.013921113689095127 | 0.01671978695966702 |
| `C7` | `CPREFIX` | `cost_narrowed_fraction` | 8,000 | 0.014633019398226192 | 0.011752921553362296 | 0.014388489208633094 | 0.017220172201722016 |
| `C7` | `CPREFIX` | `n_certified` | 8,000 | 852.323875 | 802 | 850 | 900 |
| `C7` | `CPREFIX` | `n_point_resolved` | 8,000 | 865.272625 | 814 | 862 | 913.25 |
| `C7` | `CPREFIX` | `look_prefix` | 8,000 | 919.36475 | 868 | 917 | 968 |
| `C7` | `NAIVE` | `unresolved_fraction` | 8,000 | 0.15065296141568646 | 0.13541666666666666 | 0.14925373134328357 | 0.16412213740458015 |
| `C7` | `NAIVE` | `unrevealed_fraction` | 8,000 | 0.08976157604127234 | 0.07638474542561655 | 0.08847184986595175 | 0.10149534283469869 |
| `C7` | `NAIVE` | `cost_collapsed_fraction` | 8,000 | 0.022514136697486635 | 0.016908212560386472 | 0.022151898734177215 | 0.027649769585253458 |
| `C7` | `NAIVE` | `cost_narrowed_fraction` | 8,000 | 0.023300909744120843 | 0.017626440189766182 | 0.02292920795983281 | 0.028498947731160698 |
| `C7` | `NAIVE` | `n_certified` | 8,000 | 294.547375 | 250 | 289 | 333.25 |
| `C7` | `NAIVE` | `n_point_resolved` | 8,000 | 302.401875 | 256 | 297 | 343 |
| `C7` | `NAIVE` | `look_prefix` | 8,000 | 345.893875 | 297 | 340 | 391 |
| `C8` | `ADAPTER` | `unresolved_fraction` | 8,000 | 0.11485241587222186 | 0.10605552165954851 | 0.11455108359133127 | 0.12314486523799065 |
| `C8` | `ADAPTER` | `unrevealed_fraction` | 8,000 | 0.05784486916533304 | 0.050966608084358524 | 0.05719557195571956 | 0.0640651816361556 |
| `C8` | `ADAPTER` | `cost_collapsed_fraction` | 8,000 | 0.025413575387476798 | 0.020958083832335328 | 0.025071692097846363 | 0.029641185647425898 |
| `C8` | `ADAPTER` | `cost_narrowed_fraction` | 8,000 | 0.025843222037398108 | 0.021376765607151273 | 0.02564102564102564 | 0.030120481927710843 |
| `C8` | `ADAPTER` | `n_certified` | 8,000 | 489.3315 | 428 | 487 | 548 |
| `C8` | `ADAPTER` | `n_point_resolved` | 8,000 | 503.392125 | 440 | 501 | 563 |
| `C8` | `ADAPTER` | `look_prefix` | 8,000 | 552.1295 | 485 | 550 | 615 |
| `C8` | `CPREFIX` | `unresolved_fraction` | 8,000 | 0.07368488207566182 | 0.0670198841483792 | 0.07309322033898305 | 0.0799141746893687 |
| `C8` | `CPREFIX` | `unrevealed_fraction` | 8,000 | 0.03737580815274684 | 0.0327313769751693 | 0.03699551569506727 | 0.04157303370786517 |
| `C8` | `CPREFIX` | `cost_collapsed_fraction` | 8,000 | 0.016386101841297438 | 0.01344831352212115 | 0.01607878621402834 | 0.019140103021681967 |
| `C8` | `CPREFIX` | `cost_narrowed_fraction` | 8,000 | 0.016628761524746856 | 0.013666718544404986 | 0.016339869281045753 | 0.019400579744805992 |
| `C8` | `CPREFIX` | `n_certified` | 8,000 | 848.5695 | 798 | 847 | 897 |
| `C8` | `CPREFIX` | `n_point_resolved` | 8,000 | 863.4905 | 813 | 862 | 913 |
| `C8` | `CPREFIX` | `look_prefix` | 8,000 | 915.5995 | 865 | 915 | 965 |
| `C8` | `NAIVE` | `unresolved_fraction` | 8,000 | 0.17400641745486486 | 0.1569767441860465 | 0.17307692307692307 | 0.1895734597156398 |
| `C8` | `NAIVE` | `unrevealed_fraction` | 8,000 | 0.11384565162243873 | 0.09870538739552745 | 0.11267605633802817 | 0.12778822055137845 |
| `C8` | `NAIVE` | `cost_collapsed_fraction` | 8,000 | 0.0230648453699354 | 0.016 | 0.02247191011235955 | 0.029556650246305417 |
| `C8` | `NAIVE` | `cost_narrowed_fraction` | 8,000 | 0.023992091565285995 | 0.016853932584269662 | 0.02336448598130841 | 0.030456852791878174 |
| `C8` | `NAIVE` | `n_certified` | 8,000 | 189.092875 | 164 | 185 | 211 |
| `C8` | `NAIVE` | `n_point_resolved` | 8,000 | 194.446875 | 168 | 191 | 217 |
| `C8` | `NAIVE` | `look_prefix` | 8,000 | 228.580375 | 199 | 225 | 254 |

**`cost_collapsed_fraction` and `cost_narrowed_fraction` are the measured counterparts of section 6.4**, and they are nonzero in every cell: the cost/latency enclosure path is exercised in the results, not only in the design. **`n_certified` and `n_point_resolved` are reported together and they differ**, by exactly the cost-collapsed pairs - a hierarchy enclosure the cost tier narrowed to a point while an episode was still running is logically as tight as a resolved one but carries no final-score certificate, so it is not counted as certified (section 2.5).

Section 6.4 published expectations for `cost_collapsed_fraction` before any outcome existed and section 9.5 says a discrepancy between the two is *a defect to investigate, not a result*. The measured means are conditioned on the look each trial actually reached (the deciding look, or the finalization look), which is not the fixed prefix the 6.4 table prices, so the two are not the same conditioning and are not compared numerically here. The fixed-prefix comparison a reader would need for that is not among the quantities section 9 requires; it is named here as an open item rather than left unsaid.

---

## 10. Section 9.6 - fixed-horizon summaries

At `n = 100`, `n = 500` and `n = 2,000`, per cell and construction: mean and Q1/median/Q3 of `L_h`, `U_h`, `L_s`, `U_s`; the cumulative miscoverage-so-far rate of each gate with its Wilson interval; the cumulative `DEPLOY` and `RETAIN_INCUMBENT` rates by that prefix; and the unresolved and unrevealed fractions. **All 720 rows** are in `results/live_ab_validation/horizon_summaries.csv`; `T1` was selected, so no horizon summary was forfeited.

The flagged rows of that table are listed in section 8.1 above: **nine rows, all `NAIVE`, all `miscover_h_so_far`**, in `C2`, `C4`, `C6` and `C8`. No `ADAPTER` or `CPREFIX` row is flagged at any horizon.

Cumulative `ADAPTER` hierarchy miscoverage-so-far, for orientation:

| cell | `n=100` | `n=500` | `n=2000` |
|---|---|---|---|
| `C1` | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] |
| `C2` | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] | 0.000125 [0.000022, 0.000708] |
| `C3` | 0.000000 [0.000000, 0.000192] | 0.000000 [0.000000, 0.000192] | 0.000000 [0.000000, 0.000192] |
| `C4` | 0.000000 [0.000000, 0.000192] | 0.000100 [0.000027, 0.000365] | 0.000350 [0.000170, 0.000722] |
| `C5` | 0.000000 [0.000000, 0.000192] | 0.000000 [0.000000, 0.000192] | 0.000000 [0.000000, 0.000192] |
| `C6` | 0.000000 [0.000000, 0.000192] | 0.000000 [0.000000, 0.000192] | 0.000000 [0.000000, 0.000192] |
| `C7` | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] |
| `C8` | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] | 0.000000 [0.000000, 0.000480] |

Every entry above is *no exceedance detected at this resolution*, not *the bound holds*.

---

## 11. Section 12 - the comparison against the pinned #11 monitor

### 11.1 The result, in the protocol's required wording

> The two implementations DISAGREE: 122786 of 400203 compared looks, over 926 streams, failed at least one frozen criterion.

**This is a DEFECT and is reported as one. It is not reconciled by editing either side, and neither side was edited.**

| | |
|---|---|
| streams replayed | 926 (200 frozen cell streams, 25 per cell, namespace 2, plus 726 comparable fixture scripts) |
| looks compared | 400,203 |
| looks agreeing | 277,417 |
| looks disagreeing | **122,786** |
| per-pair endpoint comparisons | 1,602,469,400 |
| defect rows written | 282,384 (truncated: 0) |
| comparison wall clock | 536.2 s |
| comparison peak RSS | 453,246,976 bytes (432 MiB) |

Criteria, all frozen before any stream was replayed: band endpoints `L_h`, `U_h`, `L_s`, `U_s` to absolute `1e-12`; per-pair enclosure endpoints to absolute `1e-12`; decision label exactly equal under the frozen bijection; `tau` exactly equal.

### 11.2 Defect classes

| class | rows | streams affected | disposition |
|---|---|---|---|
| `per_pair_enclosure_endpoint` | 151,032 | 200 | DEFECT -- escalated, never reconciled by editing either side |
| `band_endpoint` | 131,352 | 200 | DEFECT -- escalated, never reconciled by editing either side |

**Value-pair histogram, `per_pair_enclosure_endpoint`:**

| observed pair | count |
|---|---|
| `hierarchy_hi: #12=0.0 #11=1.0` | 96,117 |
| `hierarchy_lo: #12=0.0 #11=-1.0` | 52,525 |
| `hierarchy_lo: #12=1.0 #11=-1.0` | 1,551 |
| `hierarchy_hi: #12=-1.0 #11=1.0` | 839 |

**Value-pair histogram, `band_endpoint`:** `U_h` 83,598, `L_h` 47,754. The band is the same formula on both sides, so a band-endpoint difference is the per-pair enclosure difference summed over the prefix and divided by `n`. It is reported as its own class because the protocol fixes the classes, and it is **the consequence of the first class, not an independent defect**.

### 11.3 The minimal reproducer

One pair state, nothing else in play, reproduced by `vcompare.py` itself (`reproduced = true`):

| | |
|---|---|
| `atom` | `I>C` |
| `revealed_arm` | `incumbent` |
| `revealed_success` | `1` |
| `revealed_cost` | `10.0` |
| `pending_arm` | `candidate` |
| `pending_elapsed_ell` | `9.6` |
| `pair_age` | `90` |
| `d` | `375` |
| `f` | `30` |
| `cost_cap` | `100.0` |
| #11 hierarchy enclosure | `[-1.0, 1.0]` |
| #12 hierarchy enclosure | `[-1.0, 0.0]` |
| #11 success enclosure | `[-1.0, 0.0]` |
| #12 success enclosure | `[-1.0, 0.0]` |

```python
# both sides, on the one pair state, with nothing else in play
rev = EpisodeView.reveal('incumbent', 1, 10.0, 0)
pen = EpisodeView.pending('candidate', ell=9.6)
h11 = lab_enclosure.hierarchy_enclosure(candidate, incumbent, tiers)
# -> [-1.0, 1.0]
rev12 = vband.Episode.pending('rev', 100.0).finalized(1, 10.0)
pen12 = vband.Episode.pending('pend', 100.0).with_elapsed_cost(9.6)
h12 = vband.hierarchy_bounds(candidate, incumbent)
# -> [-1.0, 0.0]
```

First occurrence in the frozen stream set, with the coordinates needed to replay it alone:

| | |
|---|---|
| `stream_id` | `C1:ns2:p0:t0` |
| `cell` | `C1` |
| `namespace` | `2` |
| `program` | `0` |
| `trial` | `0` |
| `tick` | `113` |
| `n` | `113` |
| `quantity` | `hierarchy_hi` |
| `value_12` | `0.0` |
| `value_11` | `1.0` |
| `abs_diff` | `1.0` |
| `pair_position` | `23` |
| `atom` | `4` |
| `revealed_arm` | `incumbent` |
| `d` | `375` |
| `f` | `30` |
| `age` | `90` |
| `ell` | `9.6` |
| `revealed_cost` | `10.0` |

```
.venv/bin/python experiments/live_ab_validation/vcompare.py --out results/live_ab_validation --only-stream C1:0:0
```

### 11.4 The guidance clause each side appears to implement

**Shared clause.** Start unresolved hierarchy scores at [-1,1], enumerate feasible completions to narrow them, and collapse only with a valid final-score certificate.

**#12's reading.** vband.cost_order_possibilities enumerates the feasible signed cost-tier preferences separately: the pending arm's 'cheaper' branch dies when c - ell is no longer greater than rtol*max(c, ell), and the TIE branch dies later, at ell - c > rtol*max(c, ell). Between those two thresholds the feasible set is {0, +1} (for a revealed candidate), so the hierarchy enclosure is [0, +1]. #12 reads 'enumerate feasible completions' as an exhaustive enumeration whose result may be any subinterval.

**#11's reading.** lab_enclosure.hierarchy_enclosure implements a closed case list (its docstring cites protocol_FINAL 7.5 item 5): with one arm revealed and successful, the feasible set is the SINGLETON {sgn} when the cost certificate (1 - tol)*ell > L_r + 1e-9 holds, and the FULL set {-1, 0, +1} otherwise. There is no intermediate case, so the enclosure is either a point or [-1, +1].

**Note.** Both readings agree on the point-collapse threshold and differ on whether the intermediate state exists. PROTOCOL 6.4 prices that intermediate state: it is the gap between the 'point' and 'narrowed' columns, which is nonzero in every cell at every horizon. Which side is wrong is NOT decided here (PROTOCOL 12.3 item 3).

**Both readings are stated; neither is declared correct by this author** (section 12.3 item 2). **Which side is wrong is not decided here** (item 3). The disagreement is escalated to the coordinator and the root with the reproducer above; a change on either side afterwards is that side's owner's decision, recorded in that side's own freeze, and requires this comparison to be re-run and re-reported.

### 11.5 Consequence

> Until a disagreement is adjudicated, #11's results do not count as validated, which is the whole purpose of this study.

### 11.6 Differences within tolerance, and what is out of scope

Section 12.3 item 5 requires a difference *within* tolerance but systematic to be reported with its magnitude rather than silently accepted. Band-endpoint differences within tolerance: **0**, maximum magnitude **0.0**. There are none to report.

Named as out of scope, not passed over in silence:

- **`certified_collapsed_flag`.** NOT compared (PROTOCOL 1.3 item 8, 12.2). #12 marks certified only on a valid final-score certificate; #11 requires its collapsed flag to be true exactly when both scores are points. The two definitions are incompatible and PROTOCOL 6.4 says the difference is common rather than exotic. NEITHER READING IS DECLARED CORRECT HERE; it is escalated with the rest under 12.3.
- **`look_at_n_equals_0`.** No look is taken at n = 0 on either side: #12 displays the full range and #11 raises. Excluded by construction, not adjudicated.

Four of the 730 captured fixture scripts were **not comparable**, and they are named rather than dropped:

| script | reason |
|---|---|
| `fixture_script_003` | succeed: a #11 EpisodeView carries no outcome field while pending, so 'success known, cost unknown' has no #11 representation |
| `fixture_script_004` | succeed: a #11 EpisodeView carries no outcome field while pending, so 'success known, cost unknown' has no #11 representation |
| `fixture_script_726` | fail: same: a bare failure without a final cost has no #11 pending representation |
| `fixture_script_730` | succeed: a #11 EpisodeView carries no outcome field while pending, so 'success known, cost unknown' has no #11 representation |

### 11.7 Two things this comparison cannot do, stated where the result is

1. Agreement is reported as agreement and never as 'the monitor is correct': two implementations of the same misreading of the guidance agree perfectly and this comparison cannot detect that (PROTOCOL 12.3 item 6). The section 11 fixtures, derived from the guidance text rather than from either implementation, are the only check that addresses it, and they are weaker than a proof.
2. PROTOCOL 12.3 item 7: the pre-registration audit disclosed #11's cost certificate to the #12 author before this comparison was specified, so AGREEMENT on the cost-tier narrowing is agreement between two readings known to coincide, not two that arrived independently. Disagreement there would still be informative; agreement is not.

---

## 12. Retention (section 13.4)

**Every unfavourable and every inconclusive result above is retained and reported.** No cell, construction, gate or row was dropped, and no run was repeated to obtain a different answer. Specifically retained:

- The **comparison defect**, which is unfavourable to the whole point of the study, reported in full in section 11 with its minimal reproducer.
- Every `NAIVE` row, including the catastrophic ones, which are the positive control and not a defect.
- Every cell/construction with **no deciding trial at all** (`NA` conditional quantiles in `C1`, `C2`, `C3`, `C5`, `C6`), which is inconclusive at the decision level and is reported as inconclusive.
- The `ADAPTER` nonzero counts that did not reach a flag: `C2` hierarchy ever-miscoverage `x = 1`, `C4` hierarchy ever-miscoverage `x = 7`, `C4` `false_deploy` `x = 5`. These are reported with their Wilson intervals and are **not** described as *within the bound*.
- The output-bytes and disk-footprint facts of section 5, including the inflated `compute.json` figure.

---

## 13. Limitations - `PROTOCOL.md` section 1.3, repeated in full

Section 13.3 item 6 requires this section to be repeated **in full and not summarized away**. It is reproduced verbatim below.

> ### 1.3 What it CANNOT establish, stated before any outcome exists
> 1. **It establishes nothing causal.** Coverage here is coverage of `mubar_n = (1/n) sum_{i<=n} E[Z_i | F_{i-1}]`, a
>    bounded arbitrary-running-mean target of a synthetic stream. It does **not** establish the assumptions needed for
>    a causal pair-orientation interpretation of `mubar_n` in the live study - pre-enrolled nonoverlapping arrival
>    positions, one fresh coin per pair logged before either episode is dispatched, no dependence of a task's record on
>    a later coin, no cross-pair interference, an operator who does not act on coins, and a fixed scheduling and
>    resource policy. Those are properties of the live apparatus of `protocol_FINAL.md` sections 4, 5 and 7.4. **No
>    simulation can supply them**, and this study does not attempt to. Section 10 states the boundary again in full.
> 2. It says nothing about the #11 harness outside the monitor arithmetic: not the orchestrator, the coin path, the
>    event log, the serving stack, the verifier, the sandbox, the usage accounting or the anchoring.
> 3. It says nothing about laws outside the eight frozen cells. In particular **all four outcome laws are i.i.d. across
>    enrolled pairs, so `mubar_n = mu` is constant in `n`**; drift in the conditional mean is *not* exercised. This is a
>    declared gap, not an oversight: a drifting target is the case the guidance's item 4 warns about
>    ("the stationary no-split conjunction result is not the default for the proposed running-mean target under drift"),
>    and it is outside the root's eight-cell design. Observe that the *observed* process is nevertheless far from
>    i.i.d., because the enclosure sequence at a fixed pair changes over looks and, in the asymmetric-delay cells,
>    changes in a way that depends on that pair's own outcome.
> 4. It is not a power study of the live program, and it is **not** evidence that partial-information monitoring is
>    faster, better or preferable. **No pathwise speed dominance is claimed for the latest-enrolled-prefix
>    normal-mixture monitor** (section 8.4).
> 5. Absence of an exceedance flag is not proof that a bound holds. At 2,000 programs the design can only flag a
>    per-gate rate at or above 1.280x its nominal value, and at 5,000 programs at or above 1.176x (section 9.3). A
>    violation smaller than that would pass unflagged.
> 6. Nothing here licenses any sentence forbidden by `protocol_FINAL.md` section 1.5. In particular this study is
>    **not** empirical type-I calibration of the live trials, and the live program's own A/A trial (T4) remains an
>    implementation check and not a calibration, whatever this study reports.
> 7. **The cost meter and the reveal clock are not tied to each other** (section 4.3). An episode's final cost is
>    fixed by its atom while its duration comes from the delay rule, so a cheap episode may reveal second. A
>    latency-coupled model - where the cheaper arm tends to finish first - would put the *expensive* arm in the
>    pending position more often and would therefore narrow the cost enclosure **more** often than this study does.
>    This is a declared simplification in the conservative direction for exercising the path, and it is not a claim
>    about the live apparatus, where cost is `latency_s` and the two clocks are the same clock.
> 8. **`certified` is not compared against #11** (section 12.2). The two implementations hold incompatible
>    definitions of the collapse flag, so this study compares enclosure endpoints and leaves the flag out of scope,
>    as a named and reported difference rather than a silent one.

---

## 14. What did not close

1. **The comparison defect is open.** It is escalated, not resolved, and neither side was edited. Until it is adjudicated, #11's results do not count as validated.
2. **`F15` fails on this file, and this is the one thing left open in the repository.** Measured after writing it: `vfixtures.py` reports **17/18**, with the single message `13.0 REPORT.md is listed as not written but exists`, and `tests_validation.py` reports **88 ran, 2 failures, 0 errors, 0 skipped**, both failures carrying that same one message (`TestFixtures.test_every_fixture_passes` and `TestProtocolConfigAgreement.test_the_two_documents_agree`). `cells.json` still lists `REPORT.md` under `specified_here_but_do_not_exist_at_the_freeze_commit`, and `PROTOCOL.md` section 13.0 still gives it the status `specified, not written`. Writing this report - which section 13.3 item 6 requires - therefore reintroduces exactly the contradiction coordinator ruling 34 resolved for `vgen.py`, `vrun.py` and `vcompare.py`. **The same status correction has deliberately NOT been extended to `REPORT.md` here**, because ruling 34 names three files and this author does not get to widen a ruling on a frozen document. It needs the coordinator's decision, and it is the one-line change of moving `REPORT.md`'s status the same way. Every result in this report was produced while the fixture gate was green: `18/18` at the grid run and `18/18` at the comparison.
3. **The section 6.4 expectation versus the measured `cost_collapsed_fraction`** is not compared numerically here, for the conditioning reason given in section 9.2 above. Section 9.5 calls such a discrepancy a defect to investigate; no discrepancy is asserted either way, because the comparison a reader would need was not made.
4. **The `N_max = 1,000` (`T4`) grid was not run**, and was not required to be: the ladder selected `T1`. The `T4` variant of section 6 remains a pre-registered table in `cells.json`, recomputed under both readings in `ADDENDUM_SECTION6.md`.

---

## 15. Files

| file | content |
|---|---|
| `experiments/live_ab_validation/PROTOCOL.md` | the frozen pre-registration, with section 14.1 recording both post-freeze status corrections with their before/after text |
| `experiments/live_ab_validation/cells.json` | the machine-readable twin, normative for every numeric value |
| `experiments/live_ab_validation/ADDENDUM_SECTION6.md` | the post-freeze predicate-reading recomputation of 6.3 and 6.4, deposited beside the frozen tables and replacing nothing |
| `results/live_ab_validation/manifest.json` | seed, hashes, platform, commit, selected tier |
| `results/live_ab_validation/budget.json` | smoke measurements, projection and selected tier, written before the grid |
| `results/live_ab_validation/fixtures_report.json` | per-case `F01`-`F18` |
| `results/live_ab_validation/miscoverage.csv` | section 9.1 |
| `results/live_ab_validation/decisions.csv` | section 9.2 |
| `results/live_ab_validation/decision_time.csv` | section 9.5 decision prefixes |
| `results/live_ab_validation/unresolved.csv` | section 9.5 resolution quantities |
| `results/live_ab_validation/horizon_summaries.csv` | section 9.6 |
| `results/live_ab_validation/trials.csv.gz` | one record per (cell, program, trial, construction) |
| `results/live_ab_validation/compute.json` | section 9.5 compute counts, seconds, peak RSS, output bytes |
| `results/live_ab_validation/comparison_vs_live_ab.csv`, `comparison_defects.csv`, `comparison_summary.json` | section 12 |

