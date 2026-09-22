# Clock repair delta acceptance — September 22, 04:22 UTC

Reviewed exact source `1155ca8e18236e233e672e30b5c7073558a0d663`, received via owner head `05240833a8354839ae3705f45376f46cb0d19265`. Used immutable Python exports in outer scratch `work/clock0422`; shared owner files and root's working document edits were untouched. This review covers only the previously identified clock acceptance holes and kernel identity replacement. It does not review the unrelated protocol pin or historical source discrepancies also disclosed in that delivery.

## Bounded acceptance

All **six targeted delivered test methods passed**, including a valid matched-clock control, host mismatch, missing/placeholder identities, wrong clock, v2 production refusal and unavailable POSIX reader refusal above the task loop. Additional independent deterministic witnesses passed for (i) a forcibly v3-labelled record and observation both carrying `boot_id=None`, (ii) both carrying `unknown`, (iii) both relabelled to the legacy clock, (iv) stable digested identity from a mocked kernel response, and (v) refusal on failed kernel response. The first dependency-incomplete scratch import failed before any test; exact pinned Python dependencies were then exported and the six-test run succeeded. No full suite, real kernel query, sandbox, verifier, server or model execution was performed.

| Previous demonstrated defect | Current disposition |
|---|---|
| Equal absent/unknown boot identities certified | Closed: `_provenance_mismatch` requires non-placeholder string identities on both sides. Forced-v3 witnesses refuse too, independently of the constructor's downgrade selection. |
| Different host identities ignored | Closed: host identity is required and must match. The delivered mismatch test refuses. |
| v3 producer and observer agreeing on a legacy label certified | Closed: `_coverage_verdict` requires the exact POSIX constant on both sides; the mutually relabelled independent witness refuses. |
| Unsupported POSIX reader silently emitted a production-acceptable v2 record | Closed: new production rejects v2 unless explicitly invoking historical audit, and `sweep_references` checks POSIX availability before its task loop. The unsupported-reader test raises `ProvenanceUnavailable` without an attempt. |
| Wall-minus-clock arithmetic represented as boot identity | Replaced: `boot_identity` reads `sysctl -n kern.bootsessionuuid`, hashes it, declares the source and refuses unavailable/placeholder responses. Mocked response checks support these code properties; they are not a measurement of the owner's running process. |

Source anchors at this commit: `lab_data.py:532–598` kernel/host identity and provenance, `lab_data.py:945–962` pre-dispatch requirements; `lab_prepare.py:565–623` exact-domain and v2 refusal branches, `lab_prepare.py:774–804` identity validation. Existing dual endpoints, legacy operational timeout meanings and physical outer-call ordering remain unchanged. No fixed clock-offset conversion is introduced.

## Scope and finite remainder

These concrete producer/consumer defects can be closed without repeating a broad suite. This acceptance does not establish actual server lifecycle collection: the future real observer still must supply two distinct complete server-acknowledged lifetimes on the same named clock and matching real host/boot provenance, with justified endpoint-error treatment. The new producer derives host identity from `platform.node`; binding that digest to the declared isolated owner host belongs in the preparation receipt alongside the actual observer. Equal metadata alone is not experimental evidence that real measurements were taken.

The source comment at `lab_data.py:975–978` still says the POSIX interval “encloses” the legacy one and is numerically harder to satisfy. Different clock coordinates cannot support that numerical comparison. The correct established claim is only physical call order: POSIX start precedes legacy start, and POSIX end follows legacy end. This is a small wording repair, not another collection or acceptance gate for the four closed counterexamples.

No additional demonstrated acceptance defect was found in this bounded delta. This report does not change readiness, accept other delivered suites, or resolve the separately reported protocol-pin issue. Full-project readiness remains **75% (change 0)** and bounded-v1 **90%**; the prospective study and final author/release work remain outstanding.
