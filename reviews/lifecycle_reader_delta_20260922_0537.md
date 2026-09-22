# Lifecycle reader delta — September 22, 05:37 UTC

Reviewed exact `7c9818edfdecabad4756e4cd228582f5a2d3be87`, received at head `5759c7f`. Immutable Python export: outer `work/lifecycle0537`. Only the two focused classes were executed: nine `ServerLifecycleProducerConsumerTests` and seven `LifecycleReaderWitnessTests`, **16/16 passed**. Also ran one independent foreign-manifest witness through the real `observe` and `_coverage_verdict`. No full suite, model, server, kernel probe, sandbox, native build or experimental rerun.

## Accepted repairs

For the tested declared expected manifest, records with foreign provenance are refused; absent/placeholder identifiers no longer become synthetic identifiers. All four transitions must be integers and ordered. Occupancy identity now counts the instance/slot rather than inflating concurrency through task labels, and overlapping same-slot inner windows refuse. Missing expected metadata no longer produces a certifying observation. The one-microsecond inward start shift addresses the earlier exact microsecond-boundary witness while retaining the valid two-slot control.

These are reader-contract repairs. The producer patch has not gained these fields or a seal in this delivery. The fixture now inserts host/boot fields the currently delivered C++ emitter does not emit, so its “exact bytes emitted by the patched server” docstring is no longer accurate. Passing this fixture is not compiled producer/consumer interoperability.

## Remaining demonstrated provenance hole

The reader checks `record -> expected` but not `expected -> observer/verifier`. Its output still takes host/boot from the separate `provenance` argument.

[Pinned reproducible witness and recorded output](evidence/lifecycle_foreign_manifest_20260922_0537.py). The source is exported from immutable `7c9818edfdecabad4756e4cd228582f5a2d3be87`; the evidence script records the already-executed body and output and was not itself rerun.

Independent witness:

1. Emit two otherwise valid distinct-slot records with `host_id='host:FOREIGN'`, `boot_id='boot:FOREIGN'`.
2. Supply an expected manifest matching those foreign values.
3. Supply the ordinary local provenance (`host:bb`, `boot:aa`) and a local v3 verifier interval `[100,100.5]` seconds.
4. Actual result: **`producer_bound=true`, `lifecycle_complete=true`, `coverage_valid=true`**. The observation reports `host:bb` while its own embedded expected manifest reports `host:FOREIGN`.

Thus the earlier copied/foreign log issue is only partially closed. This is not a new adversarial threat model: it exercises the same production-to-observation clock identity chain required by the prior disposition. Minimal repair is to require expected host/boot identity agreement with the observer's verified current provenance before constructing any certifying observation. The existing verifier comparison can then close the final link. Preserve the file and refusal reason on mismatch; do not convert it into task exclusion.

The same witness omitted binary and patch pins and still certified. In the delivered code those pins are merely copied into output metadata, never required or verified. This supports the owner's stated partial-delivery boundary, not a claim of complete run-manifest binding. Root's chosen manifest/run-token mechanism should supply the already-required binary/patch/run identity linkage; no alternative architecture or additional experiment is requested here.

## Completeness and numeric scope

`lifecycle_complete` currently means all parsed lines passed, a manifest argument was supplied, and no overlapping inner windows were detected. There is no acquisition seal, sequence/count accounting, or producer-write failure evidence. A newline-terminated subset is therefore still accepted as complete by this reader; the owner acknowledges the producer/seal work is not implemented. Treat this state as reader preparation, not acceptance of a finished finite acquisition.

Integer microsecond ordering and the one-microsecond start allowance are accepted for the focused witness. Comparisons still convert both clock families to floating seconds; no general outward-rounding guarantee is established by these tests. Keep the already-requested integer comparison or conservative numeric-conversion treatment in the finite producer/consumer completion, without launching a new timing study.

## Disposition

Accept the listed local validation fixes and 16 passing focused tests. Keep the foreign-manifest bridge and manifest/seal/write-failure binding pending as concrete existing obligations. Do not re-open the separately closed v3 clock-domain/identity checks in `lab_prepare` or repeat unchanged suites. Root retains producer/build design ownership and the authorized next handoff.

Only this report was written in the repository. Full readiness **75% (change 0)**; bounded-v1 **90%**. No experiment, paper or release change is implied.
