# ADDENDUM to PROTOCOL section 6: the predicate-reading recomputation of 6.3 and 6.4

**THIS IS A POST-FREEZE RECOMPUTATION. IT REPLACES NOTHING.**

It is deposited **beside** the frozen tables of `PROTOCOL.md` sections 6.3 and 6.4, never in place of them, under
`experiments/live_ab/design/COORDINATOR_DECISIONS.md` revision 9, ruling 35(c). The frozen values in 6.3 and 6.4
stay exactly as they were frozen (ruling 35(a)), and **no operative rule moves** (ruling 35(d)). A reader who wants
the pre-registered numbers reads `PROTOCOL.md`; a reader who wants the numbers the governing predicate produces
reads this file; a reader who wants to know the size of the gap reads the difference tables below.

| | |
|---|---|
| authority | `COORDINATOR_DECISIONS.md` revision 9, ruling 35(c) |
| status | post-freeze recomputation, deposited beside the frozen table; **replaces nothing** |
| date | 2026-09-20 |
| produced by | `.venv/bin/python experiments/live_ab_validation/vgen.py --selfcheck` and `--selfcheck --n-max 1000`, whose stdout is reproduced verbatim in appendix A. No figure in this file was typed by hand. |
| what it does NOT do | it does not edit `PROTOCOL.md` 6.3 or 6.4; it does not change a cell, a parameter, a seed, the grid, an estimator, a reported quantity, the flag rule or the positive control |

---

## 1. The finding, stated plainly

`PROTOCOL.md` section 2.5 gives two readings of the same cost-feasibility test:

- the **predicate**, evaluated exactly as `compare` evaluates it, which section 2.5 says **governs**; and
- a **closed-form paraphrase** ("the branch favouring the pending arm dies at `ell >= (1 - rtol) c`, and the tie
  dies at `ell > c / (1 - rtol)`"), which section 2.5 itself already warns is *"not bit-identical to the
  predicate, because `c / (1 - rtol) - c` and `rtol * (c / (1 - rtol))` round differently in IEEE double"*.

Section 2.5 already named the size of the divergence before any outcome existed: over the whole frozen state grid
of `2,878,680` states the two readings disagree on exactly **128** states, all at the single boundary point
`ell = c / (1 - rtol) = 200/19`, reached at elapsed fraction `5/19`, where the predicate calls the tie infeasible
and the closed form calls it feasible. `vgen.boundary_state_count()` recomputes that count independently and
returns **128**, which is the number section 2.5 states.

What was **not** known until `vgen.py` was written is which of the two readings actually produced the frozen
tables. Recomputing section 6 under each reading answers it:

| reading | disagreements with frozen 6.1-6.4 at `N_max = 2,000` | at `N_max = 1,000` |
|---|---|---|
| closed-form paraphrase | **0** | **0** |
| predicate (the reading section 2.5 says governs) | **13** | **14** |

So the frozen 6.3 and 6.4 tables were built with the **paraphrase**, while the **predicate** governs. Section 2.5's
sentence claiming the opposite has been withdrawn as false (ruling 35(b); `PROTOCOL.md` section 14.1, correction 2).

**Sections 6.1 and 6.2 are unaffected.** Every disagreement below is in 6.3 or 6.4. 6.1 depends only on the reveal
schedule, and 6.2's gate-opening prefixes are integers that no fourth-decimal shift crosses.

## 2. Why this changes nothing operative

The predicate is what `vband.py` computes, what `vgen.py` generates every stream with, what `vcompare.py` compares,
and what fixture `F17_atom_cost_table` checks. Sections 6.3 and 6.4 are **descriptive expectation tables** - plug-in
expected-value calculations published so that no property of the design could be claimed to have been discovered
after the fact (`PROTOCOL.md` section 6 preamble). They are not estimators, they are not decision inputs, and no
reported quantity of section 9 reads them. Every difference below is **one unit in the fourth decimal place**.

Ruling 35(a) is why they are not simply corrected in place: *"Quietly recomputing 13 numbers in a pre-registration
because they turned out to be slightly wrong is precisely the habit pre-registration exists to prevent, and the
fact that it would be harmless here is not a reason to acquire the habit."*

---

## 3. Both readings, side by side

In every table below, the **frozen** row is the closed-form-paraphrase reading, which reproduces the frozen
`PROTOCOL.md` table entry for entry (asserted, not assumed: the generator of this file raises if any frozen row
fails to match `cells.json`). The **predicate** row is the governing reading. Entries that differ are **bold**.

### 3.1 `N_max = 2,000` (the reported grid, `T1`)

#### 6.3 at `N_max = 2000` - expected-path band endpoints `L_h` / `U_h` / `L_s`

| cell | reading | `n=100` | `n=500` | `n=2000` | finalization |
|---|---|---|---|---|---|
| `C1` | frozen 6.3 = closed-form paraphrase | -0.7818 / +0.7818 / -0.7752 | -0.3355 / +0.3355 / -0.3378 | -0.1271 / +0.1271 / -0.1279 | -0.1012 / +0.1012 / -0.1022 |
| `C1` | predicate (governing) | -0.7818 / +0.7818 / -0.7752 | -0.3355 / +0.3355 / -0.3378 | -0.1271 / +0.1271 / -0.1279 | -0.1012 / +0.1012 / -0.1022 |
| `C2` | frozen 6.3 = closed-form paraphrase | -0.5366 / +1.0000 / -0.6799 | -0.1835 / +0.4802 / -0.2761 | -0.0868 / +0.1653 / -0.1115 | -0.0832 / +0.1172 / -0.0946 |
| `C2` | predicate (governing) | -0.5366 / +1.0000 / -0.6799 | -0.1835 / +0.4802 / -0.2761 | -0.0868 / +0.1653 / -0.1115 | -0.0832 / +0.1172 / -0.0946 |
| `C3` | frozen 6.3 = closed-form paraphrase | -0.8268 / +0.8377 / -0.6621 | -0.3575 / +0.3727 / -0.1685 | -0.1327 / +0.1371 / +0.1006 | -0.1029 / +0.1060 / +0.1382 |
| `C3` | predicate (governing) | -0.8268 / **+0.8376** / -0.6621 | -0.3575 / +0.3727 / -0.1685 | -0.1327 / +0.1371 / +0.1006 | -0.1029 / +0.1060 / +0.1382 |
| `C4` | frozen 6.3 = closed-form paraphrase | -0.5334 / +1.0000 / -0.5589 | -0.1828 / +0.5563 / -0.1016 | -0.0866 / +0.1859 / +0.1184 | -0.0832 / +0.1275 / +0.1465 |
| `C4` | predicate (governing) | -0.5334 / +1.0000 / -0.5589 | -0.1828 / +0.5563 / -0.1016 | -0.0866 / +0.1859 / +0.1184 | -0.0832 / +0.1275 / +0.1465 |
| `C5` | frozen 6.3 = closed-form paraphrase | -0.3698 / +0.9925 / -0.7004 | +0.0838 / +0.6294 / -0.3009 | +0.2781 / +0.4990 / -0.1401 | +0.3017 / +0.4892 / -0.1241 |
| `C5` | predicate (governing) | -0.3698 / **+0.9924** / -0.7004 | +0.0838 / +0.6294 / -0.3009 | +0.2781 / +0.4990 / -0.1401 | +0.3017 / +0.4892 / -0.1241 |
| `C6` | frozen 6.3 = closed-form paraphrase | -0.1667 / +1.0000 / -0.6093 | +0.2105 / +0.7439 / -0.2419 | +0.3117 / +0.5291 / -0.1244 | +0.3168 / +0.5015 / -0.1168 |
| `C6` | predicate (governing) | **-0.1666** / +1.0000 / -0.6093 | +0.2105 / +0.7439 / -0.2419 | +0.3117 / +0.5291 / -0.1244 | +0.3168 / +0.5015 / -0.1168 |
| `C7` | frozen 6.3 = closed-form paraphrase | -0.3099 / +1.0000 / -0.5037 | +0.1423 / +0.6747 / -0.0851 | +0.3304 / +0.5478 / +0.0862 | +0.3529 / +0.5390 / +0.1046 |
| `C7` | predicate (governing) | **-0.3098** / +1.0000 / -0.5037 | +0.1423 / +0.6747 / -0.0851 | +0.3304 / +0.5478 / +0.0862 | +0.3529 / +0.5390 / +0.1046 |
| `C8` | frozen 6.3 = closed-form paraphrase | -0.1190 / +1.0000 / -0.4465 | +0.2601 / +0.7896 / -0.0481 | +0.3616 / +0.5783 / +0.0960 | +0.3668 / +0.5522 / +0.1092 |
| `C8` | predicate (governing) | **-0.1189** / +1.0000 / -0.4465 | +0.2601 / +0.7896 / -0.0481 | +0.3616 / +0.5783 / +0.0960 | +0.3668 / +0.5522 / +0.1092 |

#### 6.4 at `N_max = 2000` - cost-enclosure exercise, point / narrowed (fractions of the enrolled prefix)

| cell | reading | `n=100` | `n=500` | `n=2000` | finalization |
|---|---|---|---|---|---|
| `C1` | frozen 6.4 = closed-form paraphrase | 0.0189 / 0.0199 | 0.0351 / 0.0360 | 0.0104 / 0.0106 | 0.0077 / 0.0078 |
| `C1` | predicate (governing) | 0.0189 / 0.0199 | **0.0352** / 0.0360 | 0.0104 / 0.0106 | 0.0077 / 0.0078 |
| `C2` | frozen 6.4 = closed-form paraphrase | 0.0199 / 0.0213 | 0.0458 / 0.0466 | 0.0135 / 0.0137 | 0.0102 / 0.0102 |
| `C2` | predicate (governing) | **0.0200** / 0.0213 | 0.0458 / 0.0466 | 0.0135 / 0.0137 | 0.0102 / 0.0102 |
| `C3` | frozen 6.4 = closed-form paraphrase | 0.0234 / 0.0249 | 0.0499 / 0.0510 | 0.0147 / 0.0151 | 0.0110 / 0.0112 |
| `C3` | predicate (governing) | **0.0235** / 0.0249 | 0.0499 / 0.0510 | 0.0147 / 0.0151 | 0.0110 / 0.0112 |
| `C4` | frozen 6.4 = closed-form paraphrase | 0.0239 / 0.0255 | 0.0550 / 0.0559 | 0.0163 / 0.0165 | 0.0123 / 0.0123 |
| `C4` | predicate (governing) | **0.0240** / 0.0255 | 0.0550 / 0.0559 | 0.0163 / 0.0165 | 0.0123 / 0.0123 |
| `C5` | frozen 6.4 = closed-form paraphrase | 0.0196 / 0.0205 | 0.0245 / 0.0251 | 0.0072 / 0.0073 | 0.0050 / 0.0051 |
| `C5` | predicate (governing) | **0.0197** / 0.0205 | 0.0245 / 0.0251 | 0.0072 / 0.0073 | 0.0050 / 0.0051 |
| `C6` | frozen 6.4 = closed-form paraphrase | 0.0200 / 0.0210 | 0.0285 / 0.0290 | 0.0084 / 0.0085 | 0.0060 / 0.0060 |
| `C6` | predicate (governing) | **0.0201** / 0.0210 | **0.0286** / 0.0290 | 0.0084 / 0.0085 | 0.0060 / 0.0060 |
| `C7` | frozen 6.4 = closed-form paraphrase | 0.0197 / 0.0205 | 0.0229 / 0.0236 | 0.0067 / 0.0069 | 0.0046 / 0.0048 |
| `C7` | predicate (governing) | 0.0197 / 0.0205 | 0.0229 / 0.0236 | 0.0067 / 0.0069 | 0.0046 / 0.0048 |
| `C8` | frozen 6.4 = closed-form paraphrase | 0.0200 / 0.0209 | 0.0263 / 0.0268 | 0.0077 / 0.0078 | 0.0055 / 0.0055 |
| `C8` | predicate (governing) | **0.0201** / 0.0209 | 0.0263 / 0.0268 | 0.0077 / 0.0078 | 0.0055 / 0.0055 |

### 3.2 `N_max = 1,000` (the `T4` reduced-grid variant deposited in `cells.json`)

#### 6.3 at `N_max = 1000` - expected-path band endpoints `L_h` / `U_h` / `L_s`

| cell | reading | `n=100` | `n=500` | `n=1000` | finalization |
|---|---|---|---|---|---|
| `C1` | frozen 6.3 = closed-form paraphrase | -0.7818 / +0.7818 / -0.7752 | -0.3355 / +0.3355 / -0.3378 | -0.2053 / +0.2053 / -0.2069 | -0.1533 / +0.1533 / -0.1555 |
| `C1` | predicate (governing) | -0.7818 / +0.7818 / -0.7752 | -0.3355 / +0.3355 / -0.3378 | -0.2053 / +0.2053 / -0.2069 | -0.1533 / +0.1533 / -0.1555 |
| `C2` | frozen 6.3 = closed-form paraphrase | -0.5366 / +1.0000 / -0.6799 | -0.1835 / +0.4802 / -0.2761 | -0.1246 / +0.2816 / -0.1740 | -0.1175 / +0.1854 / -0.1403 |
| `C2` | predicate (governing) | -0.5366 / +1.0000 / -0.6799 | -0.1835 / +0.4802 / -0.2761 | -0.1246 / +0.2816 / -0.1740 | -0.1175 / +0.1854 / -0.1403 |
| `C3` | frozen 6.3 = closed-form paraphrase | -0.8268 / +0.8377 / -0.6621 | -0.3575 / +0.3727 / -0.1685 | -0.2165 / +0.2253 / +0.0002 | -0.1568 / +0.1630 / +0.0755 |
| `C3` | predicate (governing) | -0.8268 / **+0.8376** / -0.6621 | -0.3575 / +0.3727 / -0.1685 | **-0.2164** / +0.2253 / +0.0002 | -0.1568 / +0.1630 / +0.0755 |
| `C4` | frozen 6.3 = closed-form paraphrase | -0.5334 / +1.0000 / -0.5589 | -0.1828 / +0.5563 / -0.1016 | -0.1243 / +0.3228 / +0.0359 | -0.1175 / +0.2060 / +0.0919 |
| `C4` | predicate (governing) | -0.5334 / +1.0000 / -0.5589 | -0.1828 / +0.5563 / -0.1016 | -0.1243 / +0.3228 / +0.0359 | -0.1175 / +0.2060 / +0.0919 |
| `C5` | frozen 6.3 = closed-form paraphrase | -0.3698 / +0.9925 / -0.7004 | +0.0838 / +0.6294 / -0.3009 | +0.2051 / +0.5490 / -0.2012 | +0.2524 / +0.5294 / -0.1691 |
| `C5` | predicate (governing) | -0.3698 / **+0.9924** / -0.7004 | +0.0838 / +0.6294 / -0.3009 | +0.2051 / +0.5490 / -0.2012 | +0.2524 / +0.5294 / -0.1691 |
| `C6` | frozen 6.3 = closed-form paraphrase | -0.1667 / +1.0000 / -0.6093 | +0.2105 / +0.7439 / -0.2419 | +0.2724 / +0.6092 / -0.1698 | +0.2825 / +0.5539 / -0.1546 |
| `C6` | predicate (governing) | **-0.1666** / +1.0000 / -0.6093 | +0.2105 / +0.7439 / -0.2419 | +0.2724 / +0.6092 / -0.1698 | +0.2825 / +0.5539 / -0.1546 |
| `C7` | frozen 6.3 = closed-form paraphrase | -0.3099 / +1.0000 / -0.5037 | +0.1423 / +0.6747 / -0.0851 | +0.2597 / +0.5967 / +0.0213 | +0.3049 / +0.5791 / +0.0582 |
| `C7` | predicate (governing) | **-0.3098** / +1.0000 / -0.5037 | +0.1423 / +0.6747 / -0.0851 | +0.2597 / +0.5967 / +0.0213 | +0.3049 / +0.5791 / +0.0582 |
| `C8` | frozen 6.3 = closed-form paraphrase | -0.1190 / +1.0000 / -0.4465 | +0.2601 / +0.7896 / -0.0481 | +0.3222 / +0.6576 / +0.0411 | +0.3325 / +0.6053 / +0.0673 |
| `C8` | predicate (governing) | **-0.1189** / +1.0000 / -0.4465 | +0.2601 / +0.7896 / -0.0481 | +0.3222 / +0.6576 / +0.0411 | +0.3325 / +0.6053 / +0.0673 |

#### 6.4 at `N_max = 1000` - cost-enclosure exercise, point / narrowed (fractions of the enrolled prefix)

| cell | reading | `n=100` | `n=500` | `n=1000` | finalization |
|---|---|---|---|---|---|
| `C1` | frozen 6.4 = closed-form paraphrase | 0.0189 / 0.0199 | 0.0351 / 0.0360 | 0.0207 / 0.0213 | 0.0153 / 0.0156 |
| `C1` | predicate (governing) | 0.0189 / 0.0199 | **0.0352** / 0.0360 | 0.0207 / 0.0213 | 0.0153 / 0.0156 |
| `C2` | frozen 6.4 = closed-form paraphrase | 0.0199 / 0.0213 | 0.0458 / 0.0466 | 0.0271 / 0.0275 | 0.0204 / 0.0204 |
| `C2` | predicate (governing) | **0.0200** / 0.0213 | 0.0458 / 0.0466 | 0.0271 / 0.0275 | 0.0204 / 0.0204 |
| `C3` | frozen 6.4 = closed-form paraphrase | 0.0234 / 0.0249 | 0.0499 / 0.0510 | 0.0294 / 0.0302 | 0.0221 / 0.0224 |
| `C3` | predicate (governing) | **0.0235** / 0.0249 | 0.0499 / 0.0510 | 0.0294 / 0.0302 | 0.0221 / 0.0224 |
| `C4` | frozen 6.4 = closed-form paraphrase | 0.0239 / 0.0255 | 0.0550 / 0.0559 | 0.0325 / 0.0330 | 0.0245 / 0.0245 |
| `C4` | predicate (governing) | **0.0240** / 0.0255 | 0.0550 / 0.0559 | 0.0325 / 0.0330 | 0.0245 / 0.0245 |
| `C5` | frozen 6.4 = closed-form paraphrase | 0.0196 / 0.0205 | 0.0245 / 0.0251 | 0.0143 / 0.0146 | 0.0101 / 0.0102 |
| `C5` | predicate (governing) | **0.0197** / 0.0205 | 0.0245 / 0.0251 | 0.0143 / 0.0146 | 0.0101 / 0.0102 |
| `C6` | frozen 6.4 = closed-form paraphrase | 0.0200 / 0.0210 | 0.0285 / 0.0290 | 0.0167 / 0.0170 | 0.0120 / 0.0120 |
| `C6` | predicate (governing) | **0.0201** / 0.0210 | **0.0286** / 0.0290 | 0.0167 / 0.0170 | 0.0120 / 0.0120 |
| `C7` | frozen 6.4 = closed-form paraphrase | 0.0197 / 0.0205 | 0.0229 / 0.0236 | 0.0133 / 0.0138 | 0.0093 / 0.0095 |
| `C7` | predicate (governing) | 0.0197 / 0.0205 | 0.0229 / 0.0236 | 0.0133 / 0.0138 | 0.0093 / 0.0095 |
| `C8` | frozen 6.4 = closed-form paraphrase | 0.0200 / 0.0209 | 0.0263 / 0.0268 | 0.0154 / 0.0156 | 0.0109 / 0.0109 |
| `C8` | predicate (governing) | **0.0201** / 0.0209 | 0.0263 / 0.0268 | 0.0154 / 0.0156 | 0.0109 / 0.0109 |

---

## 4. Every differing entry, named, with both values

### 4.1 At `N_max = 2,000`

| # | section | cell | prefix | quantity | frozen value (closed-form paraphrase) | predicate value (governing) | difference |
|---|---|---|---|---|---|---|---|
| 1 | 6.3 | `C3` | n=100 | `U_h` | `+0.8377` | `+0.8376` | `-0.0001` |
| 2 | 6.3 | `C5` | n=100 | `U_h` | `+0.9925` | `+0.9924` | `-0.0001` |
| 3 | 6.3 | `C6` | n=100 | `L_h` | `-0.1667` | `-0.1666` | `+0.0001` |
| 4 | 6.3 | `C7` | n=100 | `L_h` | `-0.3099` | `-0.3098` | `+0.0001` |
| 5 | 6.3 | `C8` | n=100 | `L_h` | `-0.1190` | `-0.1189` | `+0.0001` |
| 6 | 6.4 | `C1` | n=500 | `point` | `0.0351` | `0.0352` | `+0.0001` |
| 7 | 6.4 | `C2` | n=100 | `point` | `0.0199` | `0.0200` | `+0.0001` |
| 8 | 6.4 | `C3` | n=100 | `point` | `0.0234` | `0.0235` | `+0.0001` |
| 9 | 6.4 | `C4` | n=100 | `point` | `0.0239` | `0.0240` | `+0.0001` |
| 10 | 6.4 | `C5` | n=100 | `point` | `0.0196` | `0.0197` | `+0.0001` |
| 11 | 6.4 | `C6` | n=100 | `point` | `0.0200` | `0.0201` | `+0.0001` |
| 12 | 6.4 | `C6` | n=500 | `point` | `0.0285` | `0.0286` | `+0.0001` |
| 13 | 6.4 | `C8` | n=100 | `point` | `0.0200` | `0.0201` | `+0.0001` |

**13 differing entries at `N_max = 2000`.**

### 4.2 At `N_max = 1,000`

| # | section | cell | prefix | quantity | frozen value (closed-form paraphrase) | predicate value (governing) | difference |
|---|---|---|---|---|---|---|---|
| 1 | 6.3 | `C3` | n=100 | `U_h` | `+0.8377` | `+0.8376` | `-0.0001` |
| 2 | 6.3 | `C3` | n=1000 | `L_h` | `-0.2165` | `-0.2164` | `+0.0001` |
| 3 | 6.3 | `C5` | n=100 | `U_h` | `+0.9925` | `+0.9924` | `-0.0001` |
| 4 | 6.3 | `C6` | n=100 | `L_h` | `-0.1667` | `-0.1666` | `+0.0001` |
| 5 | 6.3 | `C7` | n=100 | `L_h` | `-0.3099` | `-0.3098` | `+0.0001` |
| 6 | 6.3 | `C8` | n=100 | `L_h` | `-0.1190` | `-0.1189` | `+0.0001` |
| 7 | 6.4 | `C1` | n=500 | `point` | `0.0351` | `0.0352` | `+0.0001` |
| 8 | 6.4 | `C2` | n=100 | `point` | `0.0199` | `0.0200` | `+0.0001` |
| 9 | 6.4 | `C3` | n=100 | `point` | `0.0234` | `0.0235` | `+0.0001` |
| 10 | 6.4 | `C4` | n=100 | `point` | `0.0239` | `0.0240` | `+0.0001` |
| 11 | 6.4 | `C5` | n=100 | `point` | `0.0196` | `0.0197` | `+0.0001` |
| 12 | 6.4 | `C6` | n=100 | `point` | `0.0200` | `0.0201` | `+0.0001` |
| 13 | 6.4 | `C6` | n=500 | `point` | `0.0285` | `0.0286` | `+0.0001` |
| 14 | 6.4 | `C8` | n=100 | `point` | `0.0200` | `0.0201` | `+0.0001` |

**14 differing entries at `N_max = 1000`.**

Every difference in both tables is `+-0.0001`: one unit in the last reported decimal place. The `N_max = 1,000`
list is the `N_max = 2,000` list plus one further entry, `6.3 C3` at the `n = 1000` column, which exists only in
the reduced-grid variant because the `N_max = 2,000` grid has no `n = 1000` column.

---

## 5. What a reader should take from this

1. The frozen `PROTOCOL.md` 6.3 and 6.4 tables **stand as frozen**, and are the pre-registered tables.
2. The numbers in section 4 above are what the **governing** predicate produces for those same quantities.
3. The gap is `13` entries at `N_max = 2,000` and `14` at `N_max = 1,000`, each of `0.0001`, confined to the
   `128` boundary states section 2.5 named in advance.
4. Nothing in sections 7, 8, 9, 11 or 12 - the grid, the budget, the reported quantities, the fixtures or the
   comparison - reads 6.3 or 6.4, so no reported result of this study is affected by which reading built them.
5. This file is **not** a correction of the pre-registration. It is a deposit beside it.

---

## Appendix A - verbatim stdout of the two commands that produced every figure above

### A.1 `.venv/bin/python experiments/live_ab_validation/vgen.py --selfcheck`

exit status `2`

```
vgen: 8 cells, master seed 1220260919, N_max 2000, drain 200
frozen constants agree with cells.json

recomputing PROTOCOL 6.1-6.4 at N_max=2000 (exact enumeration, no simulation):

-- PROTOCOL 2.5 threshold reading: predicate --
  C1 L1/N: unresolved 0.0596 cost-point 0.0352 L_h(2000)=-0.1271 gates {'L_h>0': None, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C2 L1/A: unresolved 0.0596 cost-point 0.0458 L_h(2000)=-0.0868 gates {'L_h>0': None, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C3 L2/N: unresolved 0.0706 cost-point 0.0499 L_h(2000)=-0.1327 gates {'L_h>0': None, 'L_s>-delta': 864, 'U_h<0': None, 'DEPLOY': None}
  C4 L2/A: unresolved 0.0706 cost-point 0.0550 L_h(2000)=-0.0866 gates {'L_h>0': None, 'L_s>-delta': 698, 'U_h<0': None, 'DEPLOY': None}
  C5 L3/N: unresolved 0.0369 cost-point 0.0245 L_h(2000)=+0.2781 gates {'L_h>0': 335, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C6 L3/A: unresolved 0.0369 cost-point 0.0286 L_h(2000)=+0.3117 gates {'L_h>0': 160, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C7 L4/N: unresolved 0.0340 cost-point 0.0229 L_h(2000)=+0.3304 gates {'L_h>0': 258, 'L_s>-delta': 695, 'U_h<0': None, 'DEPLOY': 695}
  C8 L4/A: unresolved 0.0340 cost-point 0.0263 L_h(2000)=+0.3616 gates {'L_h>0': 137, 'L_s>-delta': 566, 'U_h<0': None, 'DEPLOY': 566}
   13 disagreement(s) with the frozen tables

-- PROTOCOL 2.5 threshold reading: closed_form --
   0 disagreement(s) with the frozen tables

PROTOCOL 2.5 boundary states between the two readings: 128 (2.5 states 128)

predicate: 13 disagreement(s)
    6.4 C1 n=500: got [0.0352, 0.036] want [0.0351, 0.036]
    6.4 C2 n=100: got [0.02, 0.0213] want [0.0199, 0.0213]
    6.4 C3 n=100: got [0.0235, 0.0249] want [0.0234, 0.0249]
    6.3 C3 n=100: got [-0.8268, 0.8376, -0.6621] want [-0.8268, 0.8377, -0.6621]
    6.4 C4 n=100: got [0.024, 0.0255] want [0.0239, 0.0255]
    6.4 C5 n=100: got [0.0197, 0.0205] want [0.0196, 0.0205]
    6.3 C5 n=100: got [-0.3698, 0.9924, -0.7004] want [-0.3698, 0.9925, -0.7004]
    6.4 C6 n=100: got [0.0201, 0.021] want [0.02, 0.021]
    6.4 C6 n=500: got [0.0286, 0.029] want [0.0285, 0.029]
    6.3 C6 n=100: got [-0.1666, 1.0, -0.6093] want [-0.1667, 1.0, -0.6093]
    6.3 C7 n=100: got [-0.3098, 1.0, -0.5037] want [-0.3099, 1.0, -0.5037]
    6.4 C8 n=100: got [0.0201, 0.0209] want [0.02, 0.0209]
    6.3 C8 n=100: got [-0.1189, 1.0, -0.4465] want [-0.119, 1.0, -0.4465]

closed_form: 0 disagreement(s)

FINDING: the frozen PROTOCOL 6.3/6.4 tables are reproduced exactly by the CLOSED-FORM reading of the 2.5 thresholds and not by the predicate that 2.5 says governs. The generator uses the PREDICATE, as 2.5 requires. Reported, not patched.
```

### A.2 `.venv/bin/python experiments/live_ab_validation/vgen.py --selfcheck --n-max 1000`

exit status `2`

```
vgen: 8 cells, master seed 1220260919, N_max 1000, drain 200
frozen constants agree with cells.json

recomputing PROTOCOL 6.1-6.4 at N_max=1000 (exact enumeration, no simulation):

-- PROTOCOL 2.5 threshold reading: predicate --
  C1 L1/N: unresolved 0.1192 cost-point 0.0352 L_h(1000)=-0.2053 gates {'L_h>0': None, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C2 L1/A: unresolved 0.1192 cost-point 0.0458 L_h(1000)=-0.1246 gates {'L_h>0': None, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C3 L2/N: unresolved 0.1411 cost-point 0.0499 L_h(1000)=-0.2164 gates {'L_h>0': None, 'L_s>-delta': 864, 'U_h<0': None, 'DEPLOY': None}
  C4 L2/A: unresolved 0.1411 cost-point 0.0550 L_h(1000)=-0.1243 gates {'L_h>0': None, 'L_s>-delta': 698, 'U_h<0': None, 'DEPLOY': None}
  C5 L3/N: unresolved 0.0739 cost-point 0.0245 L_h(1000)=+0.2051 gates {'L_h>0': 335, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C6 L3/A: unresolved 0.0739 cost-point 0.0286 L_h(1000)=+0.2724 gates {'L_h>0': 160, 'L_s>-delta': None, 'U_h<0': None, 'DEPLOY': None}
  C7 L4/N: unresolved 0.0680 cost-point 0.0229 L_h(1000)=+0.2597 gates {'L_h>0': 258, 'L_s>-delta': 695, 'U_h<0': None, 'DEPLOY': 695}
  C8 L4/A: unresolved 0.0680 cost-point 0.0263 L_h(1000)=+0.3222 gates {'L_h>0': 137, 'L_s>-delta': 566, 'U_h<0': None, 'DEPLOY': 566}
   14 disagreement(s) with the frozen tables

-- PROTOCOL 2.5 threshold reading: closed_form --
   0 disagreement(s) with the frozen tables

PROTOCOL 2.5 boundary states between the two readings: 128 (2.5 states 128)

predicate: 14 disagreement(s)
    6.4 C1 n=500: got [0.0352, 0.036] want [0.0351, 0.036]
    6.4 C2 n=100: got [0.02, 0.0213] want [0.0199, 0.0213]
    6.4 C3 n=100: got [0.0235, 0.0249] want [0.0234, 0.0249]
    6.3 C3 n=100: got [-0.8268, 0.8376, -0.6621] want [-0.8268, 0.8377, -0.6621]
    6.3 C3 n=1000: got [-0.2164, 0.2253, 0.0002] want [-0.2165, 0.2253, 0.0002]
    6.4 C4 n=100: got [0.024, 0.0255] want [0.0239, 0.0255]
    6.4 C5 n=100: got [0.0197, 0.0205] want [0.0196, 0.0205]
    6.3 C5 n=100: got [-0.3698, 0.9924, -0.7004] want [-0.3698, 0.9925, -0.7004]
    6.4 C6 n=100: got [0.0201, 0.021] want [0.02, 0.021]
    6.4 C6 n=500: got [0.0286, 0.029] want [0.0285, 0.029]
    6.3 C6 n=100: got [-0.1666, 1.0, -0.6093] want [-0.1667, 1.0, -0.6093]
    6.3 C7 n=100: got [-0.3098, 1.0, -0.5037] want [-0.3099, 1.0, -0.5037]
    6.4 C8 n=100: got [0.0201, 0.0209] want [0.02, 0.0209]
    6.3 C8 n=100: got [-0.1189, 1.0, -0.4465] want [-0.119, 1.0, -0.4465]

closed_form: 0 disagreement(s)

FINDING: the frozen PROTOCOL 6.3/6.4 tables are reproduced exactly by the CLOSED-FORM reading of the 2.5 thresholds and not by the predicate that 2.5 says governs. The generator uses the PREDICATE, as 2.5 requires. Reported, not patched.
```

*(Exit status `2` is `vgen.main`'s documented code for "the frozen tables are reproduced by the closed-form reading
and not by the predicate" - the finding this addendum records, reported rather than patched.)*
