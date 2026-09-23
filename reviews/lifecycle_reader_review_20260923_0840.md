# Independent reader and receipt closure — September 23, 08:40 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), author checks 10 (Yukang). This implementation review adds no scientific result or readiness credit.

Reviewed exact head `5841d6ed28f1e8dfc038f6ec7b8da8e304b5c4c1`; substantive [11837b770583f85c6dbea2c4d5f3604935019622](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/11837b770583f85c6dbea2c4d5f3604935019622), against `6676b5c`. Owner receipt `results/live_ab/LIFECYCLE_CONTRACT_BATCH.json` is timestamped **September 23, 08:33:27 UTC**. This exclusive review covers the actual seal-only receipt predicate and diagnostic/raw-file retention; producer patch application, version compatibility and process-exit contracts are separately reviewed.

## Accepted closures

**The prior actual-function seal-only counterexamples close.** I invoked `build_receipt.native_seal_fixture` with only its child-process call mocked to write controlled closed bytes. Exact non-boolean integer-zero records/failures passes. `records=2`, `records=true`, `write_failures=false` and `write_failures=0.0` all now return an explicit non-success verdict. The prior newline-truncated seal remains refused by the actual parser. This verifies the repaired function rather than merely exercising the helper predicate. No native binary ran.

**The parser-error and manifest-error diagnostic-retention gaps close for Path input.** Using the retained smoke's saved lines plus a 5,000-byte non-UTF8 sidecar, the actual observer retains sidecar existence, byte count, entries and preview labels on the ordinary path, on a truncated-main-log return and on a foreign-manifest return. All three remain appropriately incomplete. The unchanged source files' full byte counts and SHA-256 digests independently match the new `raw_artifacts` records. The hexadecimal preview stays bounded at 256 bytes and is now explicitly labeled a preview, not the whole artifact. All returned observations serialize to JSON.

The full sidecar SHA-256 in this independent witness is `9b03ef62d0d8c511781c7b7ef609f2bfc792cd3c5fd1edd406eb1d88bec59859`; it covers all 5,000 bytes, not the preview. The main log hashes differ appropriately between complete 1,073-byte and truncated 1,072-byte forms. These are bound local-file references, not proof that a remote supervisor has durably archived the original files; actual caller retention remains root's existing integration scope. No new archive or experiment requirement is introduced.

Three narrowly changed owner tests pass: exact-zero predicate, sidecar diagnosis on truncated-main return, and full-file digest binding of bounded previews. Independent evidence covers six actual receipt-function cases and four closed-file diagnostic cases. No full suite, model, native build, server or sandbox execution was run.

## One narrow remaining issue

**Normalize the documented string-path input before hashing.** `observe(path: str | Path)` passes its original `path` unchanged into `_raw_artifacts`; `_file_evidence` then calls `.exists()` and `.read_bytes()` directly. With an otherwise identical closed file, `observe(str(path), ...)` parses successfully but emits `raw_artifacts.lifecycle_log = {present: true, unreadable: "AttributeError: 'str' object has no attribute 'exists'", ...}` and omits the main log's byte count/hash. `observe(Path(path), ...)` produces both correctly. The sidecar has already been converted to a Path and hashes correctly in both cases.

This is a provenance-record defect in the new helper, not a file-access failure or statistical finding. The known saved smoke runner supplies a Path, so no claim is made that this defect changes its prior result. Owner action: normalize `path = Path(path)` once at the observer boundary (or normalize in the file-evidence helper), and add one string-versus-Path actual-observer check asserting identical raw-file counts/hashes. No new model or native test is needed. Accept the other closures now rather than reopening them with this API repair.

## Evidence and disposition

[Machine-readable independent evidence](evidence/lifecycle_reader_review_20260923_0840.json) records all ten cases, original-file preservation and JSON serializability. The original owner receipt was not edited. Accept the exact seal-only typed-zero predicate, early-return diagnostic retention for Path inputs, explicit preview labeling and matching closed-file byte/hash references. Keep only the string-path normalization defect open within this assigned reader scope. Contract selection, process outcome and native producer execution are not accepted by this report and belong to the other bounded review/root disposition. Session60 owns the repair; root owns acceptance and the prospective preparation/freeze milestone. Paper, release and scientific readiness are unchanged.
