# Adjudication of the drain-window disagreements, and a reporting defect found while doing it

Enumerating ALL of them rather than inspecting one, which is the method the root corrected me on
(COORDINATOR_DECISIONS revision 18 item 87). There are exactly three per-pair drain-window
disagreements in the committed receipt, and all three are adjudicated below.

## The three, each by enumeration

`tol = 0.05`; tight enclosure computed by enumerating the pending partner's success in {0,1} and its
final cost over `x >= ell`.

| tick | revealed | `L_r` | `ell` | `#12` | `#11` | tight | verdict |
|---|---|---|---|---|---|---|---|
| 2011 | incumbent | 10.0 | 10.526315789473685 | `[-1,-1]` | `[-1,0]` | `[-1,-1]` | `#12` tight |
| 2090 | incumbent | 40.0 | 38.0 | `[-1,0]` | `[-1,1]` | `[-1,0]` | `#12` tight |
| 2160 | candidate | 40.0 | 38.0 | `[0,1]` | `[-1,1]` | `[0,1]` | `#12` tight |

**Three distinct states, not one shape.** `#12` is tight in all three; `#11` is wider in all three and
narrower in none. One sits at the forward boundary `ell = L_r/(1-tol)` and two at the reverse boundary
`ell = (1-tol)*L_r`, so both boundary families recur in the drain window. Same conclusion as the six
enrolled-window states, reached the same way, and **stated at its checked scope**: these three
reproduced states show conservative containment and do not demonstrate an undercoverage defect; they
do not certify all `#11` results.

## A REPORTING DEFECT FOUND WHILE DOING THIS

`comparison_summary.json` declares `look_schedule.csv_column = "drain_look"`, and `DEFECT_FIELDS`
(`vcompare.py:1053`) lists that field. **The emitted `comparison_defects.csv` does not contain the
column at all**, before or after a fresh run. Anyone following the summary's own instruction to find
the drain rows would filter on `drain_look`, get **zero rows**, and conclude there were none — while
three are sitting in the file, identifiable only by `tick != n`.

This is the same failure shape as the host gate that always reported clean and the hash fixture that
never opened a file: **a mechanism that names a check it does not perform.** It is a reporting defect
only — the disagreements are in the file and the summary counts them correctly — but a reader
following the documented route finds nothing. Not repaired here; `vcompare.py` belongs to the run that
produced the committed receipt and regenerating it is a separate, declarable step.

## A DEVIATION OF MINE, RECORDED

While investigating, I re-ran `vcompare` **into the same output directory as the committed receipt**,
overwriting it. The re-run used a wider scope (39,800 drain looks compared, 51 disagreeing, against
the receipt's 1,592 and 3), so it was not even the same measurement. I restored the receipt from
`HEAD` and the tree is clean. Nothing was lost because it had been committed, which is the only
reason this is a near miss rather than a destroyed receipt. **Rule for myself: never re-run into a
directory that holds a committed receipt; write to a new one and compare.**
