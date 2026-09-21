# Power-panel provenance review — 2026-09-21 15:14

Reviewed delivery `0c17857` in `results/live_ab_validation_v2/powercurve_20260921`. Local checkout was `97ad9562e68305d6b668630fb512d9d2eafc6bef`; Git comparison confirms no changes to this delivery or its power source between the requested revision and that checkout. Scope: deposited hashes, identifiers, source binding, retry disclosure and resource accounting. Root reviews science/design. No simulations, native reference calls or model runs were performed, and scientific effect fields were not analyzed.

## Decision

**Accept the deposited row counts, coordinate coverage and byte integrity as independently verified descriptive records. Full execution-source provenance remains incomplete.** The omitted power driver/runtime-law registration pins and the missing disclosed first-failure receipt are material documentation gaps. Obtain contemporaneous source/attempt records or retain an explicit retrospective/unverified qualification; do not collect another panel merely to repair historical provenance, and do not present a later source hash as a contemporaneous pin.

## Independently verified delivered subset

- Forty completed shards, sequences/ranges matching the deposited plan: ten cells, each programs 0–1999, four trials, namespace 3 and horizon 2000. The cell/program coordinate sets are disjoint and cover all 20,000 planned coordinates.
- All 80 raw file hashes and compressed/decompressed byte sizes match the individual receipts. All 240,000 primary identifiers `(cell,program,trial,construction)` and 480,000 reference identifiers `(cell,program,trial,score,prefix)` are unique and lie in the correct shard. Constructions are ADAPTER/CPREFIX/NAIVE; references are H/D at 100/500/2000. Row law/delay labels agree with their power-cell identifiers.
- Receipt totals independently reconcile to 80,000 trials and 160,000 trial-score reference identities. The latter confirms saved records, not independent observation of native calls. Child and job totals agree. Every deposited shard belongs to corrected attempt `20260921T141823Z`, reports 2,000 completed attempts and zero failed/missing/skipped, and carries the same source/receipt pins.
- All 18 recorded source and two configuration hashes match immutable blobs at `35ab9d1` and `0c17857`. Seventeen source files and both configurations also match recorded base commit `3b14a4477cbc4c054e7e5eb81bf856abacd40cae`; `vprod.py` does not match that base commit but **does** match its corrected blob in `35ab9d1`. The dirty-tree metadata expressly records this modification, so the discrepancy has a recoverable explanation rather than an unexplained source substitution.

## Material source-binding gap

The pin record calls its method `whole_file_pins_of_complete_entry_point`, but its source map omits both `run_powercurve.py` (actual supervised entrypoint) and `vpowercurve.py` (runtime law registration and cell construction). Both were untracked at the recorded execution base, as explicitly disclosed in `pins.detail.repo.dirty_paths`.

This omission matters scientifically: `vpowercurve.py:106–115` mutates `vgen.LAW_WEIGHTS`, vectors, cumulative weights and related runtime tables; lines124–140 construct new cells with indices starting at100. An unchanged, pinned `vgen.py` does not pin these runtime definitions. Namespace3 appears consistently in saved receipts and the recoverable driver, but exact source binding for the runtime cell indices and laws is not established by that receipt. The plan records the mean ladder and allocation, not the complete atom table and source hashes.

Recoverable retrospective blobs at `35ab9d1` are:

- `run_powercurve.py`: `3d940161be18abd57403214fddcca540e3d1b4cda5ee8dce779a26133e78055c`
- `vpowercurve.py`: `d3d7f28d8fbdf5df6728e4fd18f448bf3a597a246b2705a4fc72a384c083baae`

These let reviewers inspect a concrete implementation, but do not prove those bytes were frozen before the observed outcomes. Request any preserved execution-time copies/hash logs and the explicit runtime law/cell/seed mapping; where unavailable, describe the binding as retrospective. The worker native binary and bytecode hashes are recorded but were not independently rehashed/executed on this host, as in the preceding T1 audit.

## First failed attempt is disclosed but not delivered

Owner comments [14:20](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/12#issuecomment-5762014114) and [14:49](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/12#issuecomment-5762463807), supplied in root's handoff, disclose a first-shard `KeyError: P05N`, retained failure receipt/partial data and an injectable-cell correction before retry. The corrected `vprod.py:76–88` documents that failure and the cell-set fix.

No corresponding first-attempt failure receipt, supervision record or partial directory is deposited with the reviewed power delivery; a targeted tracked-result-path search found no named power failure/retry artifact. Every delivered completed-shard receipt instead has `prior_failed_attempt=null` and `prior_attempt_rerun=false`. Those fields describe the corrected output directory's local history and cannot establish that this panel had no earlier execution attempt.

Request the already reportedly retained first-attempt receipt, original attempt ID/timestamps, failed source state and resource/row counts, linked to corrected attempt `20260921T141823Z`. Do not invent zero first-attempt observations or usage. If unavailable, preserve the disclosed failure and mark its numerical ledger unknown. This is an archival repair, not a request to rerun or invalidate the verified corrected-attempt rows.

## Resource reconciliation

Raw primary gzip files total **9,541,006 bytes**; reference CSVs total **62,664,463 bytes**; their sum **72,205,469** exactly matches child cumulative output bytes. The supervisor's child-directory snapshot **72,669,336 bytes** is exactly reproduced by subtracting the later supervisor/job/analysis/mechanism files from the current deposit. The complete 126-file deposit is **72,693,479 bytes (69.326 MiB)**, below the 200-MiB cap.

The saved supervisor records 14:18:22–14:46:12 UTC, **1,669.136960 seconds**, 9,393 samples, sampled peak tree RSS **72,138,752 bytes (68.796875 MiB)**, exit0 and no breach, under 5,400 seconds/2GiB. The job embeds this supervisor object exactly. Its final receipt timestamp is also14:46:12. These are corrected-attempt observations, not cumulative resource totals across the missing failed attempt. The parent stage and later analysis are outside the supervisor's stated child window; current deposited byte totals still comfortably satisfy the cap. Do not describe sampled RSS as a continuous bound.

## Reproduction and next action

Independent audit script/output: `work/power_provenance_1514/audit.py` and `audit_results.json`, outside the repository. It hashes bytes, parses identifiers, and compares Git blobs without importing experiment modules. Descriptive artifact integrity is verified; retrospective runtime-law binding and incomplete retry history should accompany any accepted scientific use. Root can request those records as one bounded provenance addendum, preserving all existing observations and without a new collection gate.

Archived scripts and machine-readable outputs: [audit evidence](power_validation_evidence_20260921_1514/).
