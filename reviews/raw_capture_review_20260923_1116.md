# Raw-capture helper delta — September 23, 11:16 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation and paper/package integration remain complete and unchanged. Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), final expanded QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone remains preparation closure and a costed plan before explicit working-branch freeze review. This review adds no scientific result or readiness credit.

Reviewed head `e314260b49cf7137a80413c9182679f10330118e`; substantive repair `db27cf0ded6297d3937e233cdbc6e2dbad227b99`. Scope: prior capture collision and partial-write accounting findings, close/measurement failure behavior, and the exact receipt-field forwarding expression. Root separately owns deadline, launch, and complete `main` review. Evidence: `reviews/evidence/raw_capture_review_20260923_1116.json`.

## Accepted helper repairs

**Ordinary artifact collision no longer destroys earlier evidence.** An existing `ORIGINAL` artifact is unchanged after a capture attempt with `NEW`; no input bytes are consumed, a structured collision error is retained, and full capture is false. The source now uses exclusive `xb` creation after the existing-path check. A fresh-path control still captures its complete six-byte stream with the correct measured count and hash. No race scenario or broader concurrency audit was performed.

**The helper now measures the actual closed prefix after a failed write.** The prior exact witness persists `ab` from a six-byte write attempt and then raises. The helper refuses capture, correctly reports `measured_bytes=2`, and sets both `measured_sha256` and public `sha256` to the hash of `ab`: `fb8e20fc2e4c3f248c60c39bd652f3c1347298bb977b8b4d5903b85055620603`. The old incremental counter remains zero, and `attempted_equals_measured=false` records that disagreement. This closes the helper's former empty-hash claim about a nonempty retained file.

A finite injected close error, after the underlying file is closed, refuses full capture despite EOF and still measures the six retained bytes correctly. If the post-close measurement itself raises, measured count/hash are null, the measurement error is retained, and capture refuses. These checks do not claim filesystem durability or native stream behavior.

## One remaining forwarding correction

The actual `out['producer_diagnostics']` construction still serializes `bytes_captured` from the old incremental counter while forwarding `artifact_sha256` from the newly measured hash. It omits `measured_bytes`, `measured_sha256`, `measured_unavailable`, the comparison flag, and the separately named write-counter fields.

I evaluated that exact source expression against the completed two-byte failure fixture, without running `main`. The receipt reports **`bytes_captured=0` paired with the SHA-256 of the actual two-byte file**. The helper is truthful internally, but the externally retained receipt still lacks the measured file length and the measurement-failure distinction.

Forward the measured artifact count/hash and measurement availability/error explicitly, alongside distinctly named write counters and their comparison. Do not present the old counter as persisted length. Its exact current meaning is bytes credited after a write call returns successfully: in this fixture it is zero, although six bytes were attempted and two persisted. Names should reflect that distinction, or separately count actual attempted bytes if that field is retained. This is a small receipt-forwarding repair, not a request to redesign capture or repeat a run.

## Bounded verification and disposition

**Five finite fixtures and two changed owner tests** completed. Accept the no-clobber helper behavior, truthful closed-prefix measurement, and close/unavailable-measurement refusal. Keep the single receipt-forwarding issue open. The earlier normal preview/cap behavior and lifecycle reader matrix were not repeated.

Only temporary files, in-memory streams, injected write/close/read exceptions, and the isolated receipt expression were used. No actual `main`, native child, pipe, model, server, network request, build, full suite, owner/shared-file edit, or commit occurred. Session60 owns the forwarding correction; root combines this partial acceptance with its separate supervisor findings.
