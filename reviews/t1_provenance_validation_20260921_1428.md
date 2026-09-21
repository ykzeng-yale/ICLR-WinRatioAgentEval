# Independent T1 artifact and resource validation — 2026-09-21 14:28

Reviewed main `35ab9d111123382db8997d4a0ccf4d5e36dbc876`, directory `results/live_ab_validation_v2/t1_run_20260921`. The raw evidence was published in `68b91c1`; `70727f1` preceded that full artifact delivery, and `f0052ad` corrected its analysis. This review independently hashes and parses deposited records; it does not execute the simulator/reference, inspect scientific effect values, or review the new power study. No owner files were changed. Root and the scientific reviewer separately determine scientific acceptance and manuscript integration.

## Acceptance recommendation

**Accept the delivered T1 panel as a completed, independently reconciled bounded CPU evidence package.** Its files, observation identifiers, planned coordinate coverage, source pins and resource byte totals reconcile. Preserve the disclosed parent crash and retrospective finalization, previously exposed namespace-0 design, and the distinction between owner-reported execution authorization and root scientific clearance. These limitations require accurate provenance language; they do not require new collection or invalidate the delivered rows.

Do not interpret the receipt field `scientific_completion=true` as independent scientific review, paper integration, a fresh confirmatory holdout, or continuous monitoring of the later recovery operation.

## Independent artifact reconciliation

All assertions below passed in a separate read-only audit script, without importing experiment modules:

- Exactly 56 shard directories and completed receipts; sequence numbers 1–56 each once, with exact IDs and ranges matching the frozen manifest order.
- Exactly 28,000 disjoint and complete `(cell, program)` coordinates: C1/C2/C7/C8 each 2,000; C3/C4/C5/C6 each 5,000. Namespace 0, horizon 2,000, and trial indices 0–3 are consistent in every receipt.
- All 112 raw data-file SHA-256 values match the shard receipts. Compressed and decompressed lengths match their individual labels. Shard observed/planned counts and per-shard resource byte sums reconcile.
- All 336,000 primary row identifiers are unique over `(cell, program, trial, construction)`, with constructions ADAPTER, CPREFIX and NAIVE. All 672,000 reference row identifiers are unique over `(cell, program, trial, score, prefix)`, with H/D and prefixes 100/500/2000. Every row belongs to the shard's planned coordinates and one of its four trial indices. This confirms 112,000 trial identities and 224,000 distinct trial-score reference identities; it is a saved-record audit, not independent observation of native invocations.
- Every shard reports 2,000 attempted/completed trials, zero failed/missing/skipped, complete status and a common attempt `a1`. Summed receipt totals agree with the child and recovered job receipts: 112,000 trials, 224,000 reference calls, 336,000 primary rows and 672,000 reference rows. Absence of unreported execution attempts cannot be established from saved completed records alone.
- All shards carry exactly the manifest's pins, execution digest and job identity. Independently recomputing the canonical execution specification yields `18ad539884566215ff106ddfa6fdb6170a245e4ba2fa3d7946c3f8062155fd98`, agreeing with the launch argv, every shard, and job ID `T1-18ad53988456`.
- All 18 source-file and two configuration hashes match their Git blobs at recorded execution commit `051714b4326b9ef1ee116cb863dcedc7eda9ab23`. Four available reference Python source files independently match their loaded-module hashes. The worker's native binary and four cached bytecode files are not present locally: their deposited hashes are internally consistent but were not independently rehashed or executed here.
- Git comparison from raw delivery `68b91c1` to audited head changes only `T1_ANALYSIS.json` in the delivery directory. Raw shards, manifests, supervision and recovery receipt are unchanged across that interval.

## Resource accounting

| Layer | Independently reconciled bytes |
|---|---:|
| 56 compressed primary files | 5,266,998 |
| 56 reference CSV files | 86,120,326 |
| All data files | 91,387,324 |
| 56 completed-shard receipts | 607,086 |
| Child-exit directory snapshot | 92,021,998 |
| Snapshot plus supervisor receipt | 92,023,926 |
| Current complete deposited directory, 174 files | 92,126,182 |

The reported terminal `all_artifact_bytes=92,023,926` equals the directory before the 4,440-byte recovered final receipt and the 97,816-byte corrected analysis file. The label is therefore not the current all-artifact total, but the difference is fully explained. Current storage is **87.858 MiB**, below the 200-MiB cap; data bytes exactly equal cumulative child `output_bytes`. No actual output-cap breach is evidenced. Preserve the old number as its historical snapshot and report the current total separately.

The supervisor records one child window from 12:47:03 to 13:26:58 UTC, wall **2,395.188561 seconds**, 13,367 samples, sampled peak simultaneous child-tree RSS **79,446,016 bytes (75.765625 MiB)**, exit zero and no breach. The copied supervisor object inside the recovered final receipt equals `SUPERVISION.json` exactly. These observations are below the original 5,400-second/2-GiB limits. RSS is sampled; it is not a continuous maximum or a per-shard peak.

## Recovery and authority limitations

The job receipt explicitly states that the parent crashed on `KeyError` after the child completed, and finalization was rerun against the immutable shards. Its terminal seconds field reuses **child-supervisor wall time**. It does not measure or continuously supervise the recovery/finalization operation. Recorded UTC start to recovered final receipt at 13:58:24 is **4,281 seconds**, also below 5,400; this timestamp cross-check supports that the recovery occurred within the original nominal deadline, but is not a replacement for an original continuous monotonic terminal accounting record. The rounded/restored cumulative elapsed figure is likewise not a new direct whole-job measurement.

`AUTHORIZATION.json` states that Yukang Zeng authorized execution in a separate session while root had not cleared it. Every shard still records `root_clearance_reference="NOT CLEARED"`; the added authorization record explains rather than edits that history. This review does not independently authenticate the reported separate-session instruction. Root should retain the attribution as owner-reported authorization and must not rewrite it as contemporaneous root clearance. The artifact integrity conclusions do not depend on deciding that attribution.

The manifest/shards expressly label namespace 0 as previously exposed development/replay coordinates. Keep that designation in scientific claims and downstream integration. Later analysis corrections and prospective power-study plans do not change the provenance classification of this completed panel.

## Reproduction scope

Audit script and machine-readable output: `work/t1_provenance_1428/audit.py` and `audit_results.json`, outside the repository. The audit streams CSV identifiers, hashes bytes, compares Git source blobs and reconciles metadata; it computes no effect estimates and runs no scientific simulation. Scientific metrics, theory/assumption validity and subsequent manuscript acceptance belong to the separate root/scientific review. No new collection gate is recommended by this provenance audit.

Audit scripts and machine-readable evidence are also archived in [t1_validation_evidence_20260921_1428](t1_validation_evidence_20260921_1428/) for this exact snapshot.
