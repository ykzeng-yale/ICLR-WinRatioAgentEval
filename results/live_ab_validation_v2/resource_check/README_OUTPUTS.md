# results/live_ab_validation_v2/resource_check/

The balanced 20-program resource check of root disposition section C, for the **amended all-look runner**.
This directory is a **versioned amendment that sits beside v1** (PROTOCOL section 14): nothing under
`results/live_ab_validation/` is edited, moved or replaced by it, and the v1 smoke receipts
(`results/live_ab_validation/smoke/timing.json`, `results/live_ab_validation/budget.json`) remain the record of
what v1 measured.

| file | what it is |
|---|---|
| `balanced_timing.json` | the raw measurement: 96 subprocess records (3 schedules x 4 balanced groups x 8 repetitions), each carrying its seconds, peak RSS, record bytes, counts, and the SHA-256 of every module timed |
| `balanced_analysis.json` | the derived quantities: per-group means and standard errors, the separated cell and horizon marginal effects, the balanced and v1-style-confounded scaling exponents, the paired cost factors with intervals, and the projection against PROTOCOL 8.2's caps |

**Measures only.** Seconds, peak resident memory, bytes and counts. No effect column is written and none is
read: `vresource_check.assert_resource_only` walks both files and aborts on any key that is not a timing,
memory, byte or count field.

**Coordinates.** Namespace 1, program indices 1000-1004 — the resource namespace, whose seeds are discarded
and never reused in any reported grid, at indices disjoint from the v1 smoke's 0-9.

Narrative, verdict, limitations and reproduction commands:
`experiments/live_ab_validation/RESOURCE_CHECK.md`.
Generator: `experiments/live_ab_validation/vresource_check.py`.
