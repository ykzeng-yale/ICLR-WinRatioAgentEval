# Load-coverage delta review — 2026-09-21 21:50 UTC

Exact commit `9e1777f6b10786dccd7411c3fb8b1a6c89d3cac3`. Scope: new immediate-stop behavior and interval arithmetic only. Executed bounded deterministic witnesses against an immutable export in outer `work/coverage2150/`; no unchanged suites, sandbox probe, model, serving action, or reference sweep.

**Accept immediate stop with preserved raw/error evidence. Accept the ordinary interval-union arithmetic conditionally on valid continuous-active windows and an actual endpoint-error bound. Fix numeric input validation, and retain root's separate observer-semantics requirement.**

## Immediate stop: closed

A three-attempt stub exercised each first-attempt failure through the real `run_reference_sweep` entry point:

| First observation | Attempts started | Driver result | Retained record schemas |
|---|---:|---|---|
| observer raises | 1 | refused | reference_attempt-v1; load_coverage_failure-v1 |
| metadata only, no windows | 1 | refused | reference_attempt-v1; load_coverage-v1 |

Both preserve the first raw verifier record and structured failure/invalid observation, raise before a second attempt starts, and return no accepted exclusion list. The prior delayed-refusal and observer-error retention defects are closed for this exact path. No repeat of those witnesses is required unless affected code changes.

## Interval arithmetic: bounded accepted cases

With attempt interval [100,100.5] and resolution/error quantity 50 ms:

- metadata only is rejected;
- window [99,101] is accepted;
- overlapping windows [99,100.3] and [100.2,101] jointly cover after inward contraction and are accepted;
- windows [99,100.2] and [100.3,101] leave a contracted gap and are rejected.

The sorted cursor-union procedure handles these ordinary coverage cases correctly. Its reported “0.350 s uncovered” in the last case is the distance from the first uncovered point to attempt end, not necessarily the total uncovered length; do not interpret that diagnostic as measured total gap duration.

## Concrete residual: validate the arithmetic domain

The helper currently accepts these invalid inputs:

1. `resolution_ms=-500` with window [100.2,100.3] certifies attempt [100,100.5], because negative resolution expands rather than contracts the interval.
2. A reversed attempt [100.5,100] returns valid with a spanning window.
3. A NaN attempt start also returns valid because comparisons do not establish the intended order.

Require finite numeric endpoints, end >= start for attempts/windows, and a finite nonnegative endpoint-error bound before computing coverage. Reject malformed numeric inputs explicitly. These are small domain checks on the existing computation; they need only deterministic fixtures, not another measurement campaign.

The recorded `_t0` currently precedes acquisition of the execution lock and `_t1` follows its release (`lab_data.sweep_references`), so the interval includes lock wait/overhead as well as verification. This is conservative for coverage and is not a false-validity defect. If the intended contract is the verifier's own execution interval, capture its start after lock acquisition and document precisely which interval is certified.

## Scientific meaning remains conditional

Inward contraction is justified only if each reported window independently establishes continuous active load over that window, with the stated quantity bounding endpoint uncertainty on the same clock. A sampling cadence by itself does not bound unobserved interior inactivity. The implementation's phrase “a coarse sampler cannot certify a gap it could not have seen” therefore overstates what endpoint contraction establishes. A series of active samples cannot become proof of continuous activity merely by shrinking the ends.

Root owns the finite observer contract and serving/load policy. Record the basis for continuous activity and the meaning of the error bound; do not treat this accepted union calculation as acceptance of an unimplemented observer or its measurements. Existing acquisition/trial startup and containment items are outside this delta and are not reopened here.

No new scientific result, readiness credit, or execution authorization is granted by this review.
