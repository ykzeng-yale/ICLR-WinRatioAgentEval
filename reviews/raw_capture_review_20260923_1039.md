# Raw-capture helper review — September 23, 10:39 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation/integration remain complete and unchanged. Remaining: prospective study 10 points (Session60 collection/root acceptance), final expanded release QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone remains preparation closure and the costed plan before explicit working-branch freeze review. This helper audit adds no scientific result or readiness credit.

Reviewed immutable head `9e33602f61e263ed9792df177aba58f2303ef2bc`, substantive delivery `b8e9e197d887c043d58046945defda023a005cc4`. Exclusive scope: `drain_to_artifact` and `preview_of_artifact` in `experiments/live_ab_serving/run_smoke.py`; actual supervisor `main`, resource-cap selection, and native behavior are separate root assignments. Evidence: `reviews/evidence/raw_capture_review_20260923_1039.json`.

## Accepted helper behavior

The helper now retains the byte stream as an artifact instead of retaining only trimmed decoded lines. A finite payload containing a 900-character line, newline, non-UTF8 bytes, and a suffix is retained byte-for-byte with the correct byte count and SHA-256. Its 400-character preview is marked truncated, while `raw_capture_complete` remains true; preview generation does not modify capture state. Thus display truncation is correctly separated from raw-evidence loss.

A recording in-memory stream confirms fixed-size read requests. A stream ending exactly at its byte budget completes successfully. A 13-byte stream with budget 10 preserves its exact ten-byte prefix, reports three dropped bytes, and refuses full capture. A reader error after three bytes preserves that prefix and refuses. A pre-expired deadline performs no read and refuses; a finite mock read that advances the clock beyond the deadline is refused on the next iteration. An injected close error also refuses even after EOF. No real pipe, native child, blocking read, or wait was used.

`preview_of_artifact` reads the whole capture before decoding its bounded preview. Under the intended finite artifact budget, this is bounded by that artifact cap, not by the display-character limit. Root owns the cap choice; no new cap or model-based tuning is proposed here.

## Two finite retention corrections

**1. Existing artifacts are overwritten despite the immutable-artifact contract.** The helper opens the destination with `wb`. In a single finite fixture, a previously existing 26-byte artifact (`ORIGINAL immutable attempt`) is replaced by three bytes (`NEW`), and the helper reports `raw_capture_complete=true`. The prior bytes are lost. This is a directly executed temporary-file collision witness, not a hypothetical concurrency attack.

Use exclusive creation/no-clobber behavior and retain a structured refusal on collision while leaving the existing artifact unchanged. The ordinary fresh-path behavior can remain unchanged. Root may also reject collisions before starting a producer, but the capture helper must not silently destroy an existing per-attempt artifact.

**2. Failure-state count/hash can disagree with the actual retained prefix.** A bounded injected sink writes and flushes the first two bytes of `abcdef` and then raises an `OSError` from that write call. The helper correctly reports incomplete capture, but its incremental state reports `bytes_captured=0` and SHA-256 of the empty byte string. The closed retained file actually contains `ab`: two bytes with SHA-256 `fb8e20fc2e4c3f248c60c39bd652f3c1347298bb977b8b4d5903b85055620603`.

This is a mocked sink failure, not a claim that the ordinary filesystem suffered a partial write. It demonstrates that updating the digest only after `write` returns cannot establish the persisted prefix on all error paths. Preserve refusal and compute artifact count/hash from the closed file, or explicitly report that they could not be established. Distinguish those artifact facts from bytes read, attempted, accepted, or dropped. Do not present an incremental digest as the digest of a prefix that the artifact does not contain.

## Deadline scope and handoff

The helper checks its absolute deadline before each read; it cannot interrupt a read that is already blocked. This remains part of the already acknowledged global-deadline/supervisor work, not a new design request. The finite late-read fixture establishes eventual refusal after return, not hard interruption. Actual process stopping and closed-artifact ordering remain with root's `main` review.

**10 finite helper fixtures and three selected new owner tests** completed. The normal capture/preview/cap/error refusal subset is accepted. Keep immutable collision handling and truthful failed-prefix count/hash accounting open. No unchanged lifecycle reader matrix, full suite, native child, pipes, model, server, network, build, owner/shared-file edit, or commit was performed. Session60 owns the small helper repairs; root owns combined preparation acceptance and cap decisions.
