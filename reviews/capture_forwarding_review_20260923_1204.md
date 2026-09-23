# Capture receipt forwarding acceptance — September 23, 12:04 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation and paper/package integration remain complete and unchanged. Remaining: prospective study 10 points (Session60 collection/root acceptance), final expanded release QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone remains bounded preparation closure and the costed plan before explicit working-branch freeze review. This repair adds no scientific result or readiness credit.

Reviewed immutable head `9f2658b849d4f3d2fd2ce8fc9680b4e6b85454c9`; substantive delivery `d208bfa990edac64bfb7acdc3235d02bb5553855`; comparison base `1bd5cd0`. Exclusive scope is the changed `producer_diagnostics` receipt-construction expression in `experiments/live_ab_serving/run_smoke.py`. Root separately reviews other supervisor, usage, and launch changes. Evidence: `reviews/evidence/capture_forwarding_review_20260923_1204.json`.

## Prior forwarding defect is closed

The receipt now forwards `measured_bytes`, `measured_sha256`, and `measured_unavailable` together. `artifact_sha256` is explicitly taken from the measured hash. The old ambiguous `bytes_captured` receipt field is replaced by `bytes_credited_after_write_return`, and the incremental digest/comparison are carried separately.

I reused the independently validated closed-helper states from the 11:16 review and evaluated the actual updated receipt expression against three finite artifacts whose reconstructed bytes matched the prior recorded hashes. The drain helper was not rerun.

- **Two-byte failed-write witness:** the receipt now reports measured length **2** and SHA-256 `fb8e20fc2e4c3f248c60c39bd652f3c1347298bb977b8b4d5903b85055620603`, while separately reporting credited-write bytes **0**, `attempted_equals_measured=false`, and `raw_capture_complete=false`. The former zero-length/two-byte-hash inconsistency is gone.
- **Unavailable measurement:** measured size, measured hash, and artifact hash remain null; the actual measurement error is retained; capture remains incomplete. No unavailable value is converted to a measured zero.
- **Successful six-byte control:** measured length/hash, credited count, and complete status agree with the retained artifact.

All three resulting receipts survive JSON round-trip unchanged. The credited-byte counter name now states its actual meaning. The retained helper key `attempted_write_sha256` remains compatibility naming for the incremental digest of writes that returned successfully; it is separate from the artifact hash and must be interpreted that way. It does not reintroduce the corrected persisted-artifact inconsistency.

## Disposition

**Accept this forwarding repair.** Three bounded evaluations of the exact receipt expression close the named issue; no new gap was found in that narrow delta. This does not accept unrelated changes in the same file or establish actual supervisor execution, artifact durability, or a new acquisition result.

No unchanged capture or lifecycle matrix, owner tests, complete `main`, native child, model, network, build, or full suite was run. No owner/shared files were edited and no commit was made. Root may combine this closure with the independently reviewed remaining preparation work.
