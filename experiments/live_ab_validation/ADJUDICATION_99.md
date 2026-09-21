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

- **90 rows at the FORWARD boundary** `ell = L_r/(1 - tol)`: `10.52631578947368496` equals the float64 value of
  `10/0.95` exactly, so `#11`'s strict `x > L_r/(1-tol)` test fails while the comparator predicate
  `|x - L_r| > tol*max(|x|,|L_r|)` is strictly satisfied (`0.52631578947368496` against `0.52631578947368429`).
- **10 rows at the REVERSE boundary** `ell = (1 - tol)*L_r`, i.e. 9.5 for `L_r = 10` and 38.0 for `L_r = 40`.
  **This is a second and distinct source of conservativeness**, which my first version missed entirely: strict
  equality at the reverse certificate leaves `#11` unable to exclude the partner's win, so it keeps the full
  `[-1, 1]` where the feasible set is only half of it.

## Verdict, unchanged in direction and now actually checked across all six

`#12` is tight in **all six** states. `#11` is wider in all six and narrower in none, in 100 of 100 rows. No
validity consequence.

## What I am NOT entitled to conclude, and said wrongly before

I wrote that no `#11` decision or stopping summary is affected. **That does not follow from these rows** and the
root is right to say so. Conservative enclosures can change *when* a gate fires, and I have not measured that.
The honest statement is: no `#11` result is *invalid*, and the effect on decisions and stopping times is
**unmeasured**.

Scope: 100 rows from a bounded partial run of 8 of 200 cell streams, and the v2 comparison currently **skips
every non-final drain look**, so this is not even a complete view of the streams it did run. Not a rate.
