# Adjudication of the residual comparison disagreements — CORRECTED 2026-09-21

**My first version of this file was wrong about its own scope.** It said "Every one of the 100 per-pair rows is
the same shape", described a single incumbent state, and generalised. The root caught it: there are **six
distinct states, 90 forward and 10 reverse**. I verified that before accepting it. I had read row 0 and
described the population — the same over-generalisation I have now made repeatedly, and the fact that the
verdict survives does not excuse the method.

## The six states, each adjudicated by enumeration rather than by inspecting one

`tol = 0.05`. `sgn = +1` when the revealed arm is the candidate. Tight enclosure computed by enumerating the
pending partner's success in {0,1} and its final cost over `x >= ell`.

| rows | revealed | `L_r` | `ell` | tight | `#12` | `#11` | `#12` tight? | `#11` wider? |
|---|---|---|---|---|---|---|---|---|
| 54 | candidate | 10.0 | 10.526315789473685 | `[1, 1]` | `[1, 1]` | `[0, 1]` | yes | yes |
| 36 | incumbent | 10.0 | 10.526315789473685 | `[-1, -1]` | `[-1, -1]` | `[-1, 0]` | yes | yes |
| 4 | incumbent | 10.0 | 9.5 | `[-1, 0]` | `[-1, 0]` | `[-1, 1]` | yes | yes |
| 3 | candidate | 10.0 | 9.5 | `[0, 1]` | `[0, 1]` | `[-1, 1]` | yes | yes |
| 2 | candidate | 40.0 | 38.0 | `[0, 1]` | `[0, 1]` | `[-1, 1]` | yes | yes |
| 1 | incumbent | 40.0 | 38.0 | `[-1, 0]` | `[-1, 0]` | `[-1, 1]` | yes | yes |

## TWO distinct boundaries, not one

- **90 rows at the FORWARD boundary** `ell = L_r/(1 - tol)` (that division is the EXPLANATORY threshold; the
  executed float expression is `(1-tol)*ell > L_r + CERTIFICATE_EPS`, and I described a rearrangement while
  criticising `#11` for testing one, which the root corrected): `10.52631578947368496` equals the float64 value of
  `10/0.95` exactly, so `#11`'s executed certificate `(1-tol)*ell > L_r + CERTIFICATE_EPS` fails while the comparator predicate
  `|x - L_r| > tol*max(|x|,|L_r|)` is strictly satisfied (`0.52631578947368496` against `0.52631578947368429`).
- **10 rows at the REVERSE boundary** `ell = (1 - tol)*L_r`, i.e. 9.5 for `L_r = 10` and 38.0 for `L_r = 40`.
  **This is a second and distinct source of conservativeness**, which my first version missed entirely: strict
  equality at the reverse certificate leaves `#11` unable to exclude the partner's win, so it keeps the full
  `[-1, 1]` where the feasible set is only half of it.

## Verdict, unchanged in direction and now actually checked across all six

`#12` is tight in **all six** states. `#11` is wider in all six and narrower in none, in 100 of 100 rows.
**These six reproduced states show conservative containment and do not demonstrate an undercoverage defect; they
do not certify all `#11` results.**

## What I am NOT entitled to conclude, and said wrongly before

I wrote that no `#11` decision or stopping summary is affected. **That does not follow from these rows** and the
root is right to say so. Conservative enclosures can change *when* a gate fires, and I have not measured that.
The honest statement is the one the root supplied and I am adopting verbatim: these six reproduced states show
conservative containment and do not demonstrate an undercoverage defect, and they do not certify all `#11`
results. The effect on decisions and stopping times is **unmeasured**.

Scope: 100 rows from a bounded partial run of 8 of 200 cell streams, and the v2 comparison at the time this file
was written **skipped every non-final drain look**, so it was not even a complete view of the streams it did run.
Not a rate.

## UPDATE 2026-09-21 — the skip is repaired and the comparison is now matched

Two things changed after the paragraph above was written, both on the root's ranked instruction, and the numbers
below supersede the 100-row count as *the* view of these eight streams.

**The drain-look skip is repaired.** `vcompare` now compares every declared tick through `N + W` with the
enrolled denominator fixed at `N`; the skip survives only in v1 reproduction mode. Re-running the *same* bounded
partial comparison with the *unchanged* ideal-enclosure oracle and the repaired schedule gives **17,603 compared
looks** (was 16,011), **102 disagreeing** (was 99), **204 defect rows** (was 198: 103 per-pair endpoint rows and
101 aggregate-band rows). Of the **1,592 newly included drain looks, 3 disagree** — three disagreements the old
schedule concealed. So the 100-row ledger above was, as suspected, incomplete; it is now 103 rows.

**The comparison is now between matched operational policies.** The root's decision is to keep the conservative
live numeric policy and *not* tighten it to force agreement; instead the declared policy is implemented
independently as a versioned CPU adapter (`vpolicy.py`), and the ideal oracle is retained separately as a
diagnostic. Under the matched comparison the same eight streams give **17,603 compared looks, 0 disagreeing, 0
defect rows**. Oracle containment is then its own check, not a disagreement count: **0 containment violations in
19,208,000 pair-state checks**, with **103 pair states where the oracle is strictly narrower**.

**What that does and does not mean.** The disagreements did not turn out to be arithmetic errors that were
fixed; they were **reclassified** from a disagreement count into the separate oracle-versus-operational
diagnostic, which is what they always were. The adapter reproduces all six states of the table above on the
`#11` side exactly, and both boundary margins are exactly `0.0`, so the difference survives `eps = 0` and is a
difference of algebraic form, not of epsilon. The verdict of this file is unchanged: `#12`'s oracle is tight in
all six states, `#11` is wider in all six and narrower in none, and **the effect on decisions and stopping times
remains unmeasured**.
