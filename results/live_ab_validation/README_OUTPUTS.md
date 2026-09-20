# Deposited outputs of the #12 validation study

Produced by `vrun.py` (the grid) and `vcompare.py` (the pinned comparison), per the frozen
`experiments/live_ab_validation/PROTOCOL.md`. Regenerate with:

    .venv/bin/python experiments/live_ab_validation/vrun.py     --out results/live_ab_validation
    .venv/bin/python experiments/live_ab_validation/vcompare.py --out results/live_ab_validation

## Compression, and why

`comparison_defects.csv` (87.3 MB) and `comparison_vs_live_ab.csv` (107.2 MB) exceed GitHub's
100 MB hard limit, so they are deposited as deterministic gzip (`gzip -9 -n`, no timestamp, so the
bytes are reproducible) at 6.8 MB and 21.3 MB. **No row was dropped, sampled or summarised away.**
Read them with `pandas.read_csv(path)` or `gzip.open(path, 'rt')`; every analysis in `REPORT.md` and
in the coordinator's adjudication was computed from the full uncompressed content before compression.

The protocol's 200 MiB output cap in section 8.3 governs the grid run, whose own outputs are
4.41 MiB. The comparison step is separate and is not covered by that cap; its size is recorded here
so that nobody discovers it by accident.

## What the comparison found

A DEFECT, not agreement: 122,786 of 400,203 compared looks disagree, in two classes
(151,032 per-pair enclosure endpoints, and 131,352 band endpoints, the second being the first summed
over the prefix and therefore not independent evidence).

Direction, computed over every disagreeing row: the live monitor's enclosure CONTAINS the
independent one in 151,032 of 151,032 rows, and its band is wider in 131,352 of 131,352. It is
never narrower. So it never excludes the truth: this is a power defect, not a validity defect.

Adjudication, reproducer and the resulting action are in
`experiments/live_ab/design/COORDINATOR_DECISIONS.md` revision 10.
