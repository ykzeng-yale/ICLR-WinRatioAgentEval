# Named-clock producer/consumer review — 2026-09-22 04:02 UTC

Reviewed exact `fad54350e0a8caf675d75fd28d76b05fd961ca12` from immutable export `work/named0402`. Read prior clock-domain decisions. Ran only11 `NamedClockDomainTests` and bounded deterministic stubs; no servers, models, sandbox, native verifier, drill or clock-duration probe. Read local availability of `kern.bootsessionuuid`, printing only availability/format length, never the raw identifier. Only this report is changed in the repository.

## Accepted subset

All **11** delivered named-clock test methods pass (commit text says12). Producer retains legacy fields/latency semantics and adds separate integer POSIX endpoints. Source order is POSIX-start, legacy-start, verifier call, legacy-end, POSIX-end, inside the lock (`lab_data.py:879–890`). It brackets the physical call conservatively. It does **not** mean the numerical POSIX interval encloses a legacy-coordinate interval: the coordinate systems may have different epochs/rates. Replace the cross-domain numerical “strictly harder” assertion with that physical ordering statement.

A declared v3 record with malformed/missing POSIX endpoint is refused by the v3 branch rather than rescued using legacy endpoints. The ordinary producer-declared POSIX versus legacy mismatch is refused. No694-second subtraction is implemented. A deterministic call through real `run_reference_sweep` with a stub attempt and mismatched boot preserved the raw attempt, raw load observation and invalid coverage verdict, then raised `PreparationRefused` before later processing. This closes retention for that detected failure path; helper-only refusal tests alone would not have shown it.

## Actual acceptance counterexamples

Using the delivered constructor/consumer and otherwise valid two-lifetime observation:

| Input delta | Actual result |
|---|---|
| v3 record and observation both `boot_id=None` | coverage valid |
| both `boot_id='unknown'` | coverage valid |
| record `host_id='hostA'`, observation `host_id='hostB'`, same boot string | coverage valid; host fields ignored |
| v3 record `clock_domain_posix='time.monotonic'` and observation same legacy label | coverage valid |

`lab_prepare.py:565–589` tests metadata equality, which permits two equally absent/unknown identities and two equally wrong domain labels. It must require the **actual POSIX constant**, a supported provenance schema, and nonempty/non-placeholder matching host and boot identities, rather than treating equality as proof of either validity or origin. These are concrete defects in the stated acceptance boundary, not a proposed general tamper framework.

**Unsupported-clock production fallback is also real.** With actual `lab_data.sweep_references`, injected verifier/result/lock readers only, `_posix_monotonic_ns=None` produces a fresh v2 record. Feeding it a legacy-domain lifecycle observation yields valid coverage. Thus current source can silently turn unavailable new instrumentation into accepted legacy production (`attempt_record` schema selection and `_coverage_verdict` v2 branch). Preserve legacy parsing for an explicit historical audit route, but require v3/named POSIX evidence for **new production**. Do not cure it by relabelling incomplete records as v3 without declaring the missing data. Prefer to reject unavailable required readers/provenance before verifier dispatch; if failure occurs after a real attempt starts, retain its result, partial endpoints and clock failure, then refuse preparation without converting the failure into task exclusion.

## Boot identity is not verified provenance

`lab_data.boot_identity` derives a second-truncated wall-minus-clock value, not a kernel boot-session identity. The test named “changes when the clock restarts” does not simulate a reboot: it merely calls the current helper twice and checks equality. It establishes neither reboot discrimination nor host identity. A deterministic same-POSIX-time/different-wall witness returns `boot:900` then `boot:901`; no stable identity follows from this arithmetic without additional clock-coupling assumptions. The preceding review already rejected interpreting differences between clock families as an immutable offset.

Use the available kernel boot-session source, e.g. macOS `kern.bootsessionuuid`, and retain its cryptographic digest plus a declared source, not its raw value in shared artifacts. A read-only check found that API available on the **review host** with a36-character value; this is not verification of the owner's host. Owner producer and server observer must obtain matching verified boot provenance and an explicit matching host identity. Unsupported sources refuse; do not fall back to wall-minus-clock or `unknown`. Read/prove the provenance in the actual worker/server contexts; no real model execution is needed to test the schema and refusal paths.

## Finite closure recommendation

Keep accepted dual-read order and raw-first retention. Complete just these existing obligations: (1) strict v3/exact-POSIX/new-production selection, leaving historical audit explicit; (2) actual host/boot provenance with missing/unknown/cross-host refusal; (3) unsupported clock refusal before dispatch or retained partial-attempt failure; (4) real server lifecycle producer carrying that same domain/provenance and complete distinct request lifetimes. Existing operational clocks/thresholds stay unchanged. Add targeted stubs for the counterexamples above and a matching producer/consumer case with a changing legacy/POSIX offset; the delivered offset test moves windows but does not exercise changing reader offsets through the actual sweep.

The server lifecycle producer remains a separate missing implementation; naming a clock in a synthetic observation does not certify a server or binary. Finish the already authorized server instrumentation and finite guards, rather than performing additional client-arrival/jitter studies. This review accepts bounded software behavior only, not live coverage, roster validity, trial freeze or readiness points.
