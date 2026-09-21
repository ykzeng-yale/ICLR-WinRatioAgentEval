# Resource and executable-guard delta — September 21, 2026, 06:35 cycle

**Reviewed head:** `63be271af3e01bf7743efd23e2bfddce47a2016c` against `7f795`. Independent inspection used the root's immutable export in outer `work/v2_review_0635`, plus pure AST-extracted budget/guard functions, synthetic adverse ledgers, saved timing vectors and SHA-256 checks. Portable reproduction: `python reviews/evidence/v2_resource_checks_20260921_0635.py EXPORTED_REPO`. No timing, native reference execution, simulation/model/grid, installation or Git mutation was performed. Only this report is edited in the repository.

**Disposition:** The declared two-score call count and bounded timing arithmetic are supported. Three elementary guard refusal cases are implemented, and the guard is called before the grid. The complete workload is still not implemented in the grid and the guard is not fail-closed with respect to ledger absence/provenance, memory, bytes or nonfinite costs. Do not equate its current `authorized: true` with clearance to run the requested full experiment.

## Accepted bounded evidence

- `REFERENCE_WORKLOAD` declares H and D once each per trial, four trials/program, eight calls/program. In `reference/combined_workload.py:192–225`, the reference receives the same latent `draw.z` and `draw.dsc` as the primary; it is not recomputed per baseline or look.
- The deposit has 12 completed group records: four balanced cell/horizon units × three outer repetitions, each with 20 inner timing repetitions and five programs. It preserves 13 attempt entries (one import plus 12 groups), with zero **recorded** failures. Coordinates are namespace 1, C1/C2, horizons 1000/2000, indices 1000–1004: 20 design units, ten distinct seed-program identities. Each combined repetition records 20 H calls and 20 D calls, 40/5 = eight reference calls/program. The call-count field describes one inner repetition, not the sum over all repeated execution; the timed workload totals 9,600 reference calls across the 12 × 20 repetitions, plus 24 warm-up calls.
- Independent reconstruction of all 24 timing vectors' medians, means and standard deviations, the differences of medians, and per-program costs is exact. Maximum across cells of the median outer combined cost is 0.0353769958 seconds/program at 1000 and 0.0727760251 at 2000. These are observations of the declared harness scope on the owner's host, not a full-grid measurement or a new scientific result.
- The new harness fixes the Linux RSS conversion. Reference bridge, reference manifest, harness, generator, band module and previous resource-harness hashes match the incoming files. The binary hash/origin is recorded but not independently loaded or rebuilt. The new receipt does not carry a generation timestamp or exact measured Git commit.
- The saved guard demonstration is independently reproduced exactly using the new pure code and saved primary inputs: T1 total 2043.91353209503 seconds against 5400. The current `vrun.py` hash matches that demonstration. Synthetic unresolved reference seconds and an over-cap total both refuse and `enforce_total_workload_guard` raises. Main calls that enforcement before its grid loop (`vrun.py:2990–3028`), so this is more than an advisory printout.

## 1. Declared comparator work is still absent from the actual grid

The combined measurement computes the two full reference paths and discards their return values (`combined_workload.py:211–219`); its sink contains only `vrun.trial_rows` for the primary. Thus equal primary/combined output-byte counts do **not** measure serialization/output of the reference diagnostic. The actual grid calls the unchanged `run_block` (`vrun.py:1187–1208,3081–3095`), which contains no reference invocation or reference output path. The newly declared workload therefore exists in a timing helper and budget dictionary, not an executable full calibration panel. It also does not route through the new operational-policy CPU adapter; root's separate scientific review owns that issue, but resource timing must follow whichever primary the final panel actually executes.

Keep the primary core independent of the reference. A reference-side orchestration wrapper can run the accepted operational primary and H/D diagnostics on shared draws, retaining outputs and indexing returned bands without introducing a reverse dependency. Bind the resource receipt to that intended callable, output schema and workload. Do not launch a nominally combined full grid that actually omits its comparator.

## 2. The resource gate remains open in unresolved/invalid states

`total_workload_guard` (`vrun.py:2054–2150`) checks only projected seconds and a `reference_cost_unresolved` boolean. Independent pure-function counterexamples establish:

| Input | Actual result |
|---|---|
| Reference explicitly unresolved | refuses and raises |
| Primary admissible, reference makes total >5400 | refuses and raises |
| Projected bytes and RSS both far above caps | **authorizes** |
| Reference projected seconds is NaN | **authorizes**, because NaN >5400 is false |
| Combined-workload receipt absent, old weak H-only receipt remains | **authorizes** using scaled old arithmetic |

The last case was tested by pointing `COMBINED_TIMING` to a nonexistent scratch path and invoking the actual pure selector/guard. There is no gate on a verified complete receipt, successful planned groups, matching executable/config/workload pins, actual loaded-reference availability, or independent acceptance. A stale/malformed ledger can similarly supply finite totals without matching what will execute. Merely listing output and memory in `covers` is not checking them. Existing primary-only byte/RSS selection and runtime aborts do not substitute for a complete combined ledger.

Require finite nonnegative complete inputs; validate receipt schema, expected design/counts/failures, code/config/workload identity and available comparator; check total seconds, total output bytes and combined peak RSS. Absent or unresolved complete evidence must refuse; retain the old arithmetic as descriptive history only. For ad-hoc overrides, construct the actual proposed workload **before** guarding it: the current check precedes `args.tier`, `args.n_max`, `args.cells` and `args.programs` resolution (`3028–3045`), so it prices the automatically selected tier even when the execution arguments differ. This can be repaired without changing the frozen scientific primary tier or any inferential parameter.

## 3. Receipt provenance and scope need a narrow final reconciliation

The combined timing declares `vrun.py` hash `a8c0e9f5775219366fca15ee9d63c1d5b59c7601e8f7deeb0e49d2f3698fe3f1`, which does **not** match incoming `vrun.py`. The harness records hashes only when constructing its final report (`combined_workload.py:395`), not as a pinned source snapshot checked before/after execution. Preserve the exact measured source or identify the matching immutable commit, explain subsequent executable changes, and bind any necessary bounded follow-up to the finalized orchestration. A differing whole-file hash is not by itself proof that the timed core changed; it is a missing provenance reconciliation, not a reason to erase or blanket-repeat the receipt.

The receipt appropriately discloses that its accumulator, grid output/summary path and disk-backed sink remain outside both scopes. It does not include reference output accumulation at all. Its RSS is one process-wide high-water mark across groups; that is useful for the bounded process peak but cannot establish memory scaling of a full-grid accumulator. `vtotalguard.smoke_from_saved_projection` inserts a constant 96 MiB rather than reading combined peak usage (`vtotalguard.py:70`); the seconds-only guard then ignores even that field. Supply the actual combined storage strategy and measured or deterministically bounded bytes/memory for it.

The phrase “paired difference” is too strong for the timing design: the source runs all 20 primary-only repetitions, then all 20 combined repetitions (`combined_workload.py:247–264`). It reports a **difference of medians**, not the median of interleaved paired differences. The same deterministic design coordinates support a useful matched workload comparison, but temporal drift is not eliminated. Preserve raw observations and relabel this scope; do not claim a controlled causal overhead estimate or rigorous upper bound.

The guard's T1 projection uses old primary timing plus the maximum of scaled H-only arithmetic and new measured difference. Its 2043.91 seconds (about 34.1 minutes) is below the 90-minute cap, which is an encouraging planning observation. It remains a projection of incomplete scope. Taking the larger of two noisy estimates is a conservative heuristic, not a confidence bound or proof that all future combined runs fit.

## Actionable next handoff

1. Finish the reference-side full-panel orchestration and persist the declared H/D diagnostics, using the scientifically accepted primary policy. Freeze exact workload/output identities.
2. Make the separate total guard fail closed on complete-ledger absence, hash/workload mismatch, nonfinite/negative values, missing/failed groups and every hard resource cap; bind it to actual execution arguments. Retain current passing unresolved/over-seconds tests and add these bounded adverse fixtures.
3. Preserve current measurements and resolve the measured `vrun` identity. Complete only the missing orchestration/output/memory scope on the same authorized bounded design, with source/config/environment/binary pins, actual timestamps, attempts, raw timings and total call/output counts. No broad timing sweep or full calibration/live execution is justified yet.

The two-score workload is now declared and partially measured; it is not fully integrated, independently accepted or packaged. This review grants no full-grid/live clearance or readiness increment.
