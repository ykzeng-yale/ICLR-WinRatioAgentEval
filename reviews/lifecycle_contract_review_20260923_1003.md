# Lifecycle reader repair acceptance — September 23, 10:03 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation and its paper/package integration remain complete and unchanged. Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone is bounded preparation closure and the costed plan before explicit working-branch freeze review. No scientific result or milestone credit is added here.

Reviewed immutable head `b3c4f4a4abe05f39ed8716ee91743c59201f2b87`, substantive repair `58ad9435fc1d08624b4bb859db83f68ba10c412e`, against the reader at `549b60f99c383cb2a9128f52f953c7a2d9d48559`. Exclusive scope: the two reader corrections requested in the 09:19 review. Evidence: `reviews/evidence/lifecycle_contract_review_20260923_1003.json`. Supervisor and actual source/binary agreement are separate root assignments.

## Both named reader corrections are accepted

**Digest identity now requires an actual string and an exact full match.** `is_digest` checks `isinstance(value, str)` and `[0-9a-f]{64}` using `fullmatch`; manifest selection validates the raw patch/binary values without coercion. The four prior consumer-level witnesses—64-digit integer and trailing-newline value, separately for patch and binary—now produce `contract=unbound`, incomplete lifecycle, and invalid coverage. The exact valid-digest control still passes. This closes the newly introduced syntax/coercion gaps; it does not turn a declared hash into verified artifact identity.

**Declared stop signals no longer excuse a failed process outcome.** The success exception and integer coercion of the signal declaration are gone. The reader preserves the raw outcome and diagnostic stop declaration. Through the actual `observe` → `_coverage_verdict` route, each former bypass now refuses: outcome/declaration pairs `(-15,15)`, `(-9,9)`, `(1,-1)`, `(-1,true)`, `(-15,15.9)`, and `(-15,"15")`. Non-numeric string and mapping declarations alongside -15 now return refused observations without the prior `ValueError`/`TypeError`. A retained non-boolean integer zero with declared SIGTERM remains successful.

The new focused tests replace the former test that endorsed declared-signal success. Their behavior now agrees with root's policy: intended stop requests are diagnostic; they cannot substitute for successful finalization. This review establishes the reader's decision, not an executed signal handler or native failure path.

## Bounded validation and handoff

**13 changed-case scenarios** reached the actual reader and actual coverage consumer: one successful control, four identity regressions, and eight signal/outcome regressions. All returned the expected decision without exceptions; raw outcomes survived JSON serialization and the closed temporary files remained unchanged. **Two selected changed owner tests passed**, also checking additional malformed digest examples at the predicate level.

The cases used temporary copies of the immutable smoke records with strict seal fields and controlled metadata/outcome mutations. Supplied historical clock/host/boot provenance was used only to exercise the reader; it is not a fresh remote observation or validation of a new producer binary.

No new reader gap was found in this bounded delta. Preserve already accepted path parity and historical v4 scope unchanged; no expansion or repeated historical matrix was performed. Root must combine this acceptance with its separate supervisor, manifest, and native-producer disposition before preparation closure. Session60 remains responsible for any outstanding caller repairs and subsequent authorized evidence delivery. No model, server, native fixture, sandbox, network request, full suite, owner/shared-file edit, or commit was performed.
