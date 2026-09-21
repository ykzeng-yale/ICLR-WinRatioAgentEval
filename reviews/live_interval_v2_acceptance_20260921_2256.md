# Verifier interval v2 delta review — 2026-09-21 22:56 UTC

Reviewed exact `dbea39d4a66ead149ab09c1458d3fbdaabc7e478`. Only the exact pure numeric helpers were loaded through AST extraction and exercised on nine fixed input records; no imports of execution modules, processes, lock fixture, sandbox, model, or sweep were run.

**Accept rejection of the three previously demonstrated malformed verifier-error values and the new verifier-call timing capture. Two small schema/absence branches remain inconsistent with the root contract.**

## Closed subset

Explicit verifier `endpoint_error_s` equal to NaN, positive infinity or the string `invalid` is now rejected. A valid finite v2 verifier interval with absent uncertainty remains accepted as intended. The source captures verification start/end inside the acquired lock, retaining lock request/acquisition/release separately, so the coverage target is now the verifier call rather than time spent waiting for the lock. No live timing behavior was inferred or rerun by this review.

## Remaining exact branches

1. **Explicit null still becomes zero.** The branch `if 'endpoint_error_s' not in record or record.get('endpoint_error_s') is None` accepts a present null as if the key were absent. A valid v2 interval with `endpoint_error_s=None` returns valid. The agreed rule is absent-only default zero, present unusable value refuse. Remove the second clause for new production records; do not substitute a new uncertainty value or reinterpret old saved records.

2. **Invalid or missing v2 endpoints fall back to aliases.** `_coverage_verdict` does not inspect `interval_schema`; if either named verifier endpoint is unusable, it parses `started_monotonic`/`ended_monotonic` instead. A record explicitly labelled `live_ab/attempt_interval-v2` with a NaN named start and valid aliases returns valid. A v2-labelled record missing both named endpoints also returns valid from aliases. Production v2 should refuse missing, null, malformed or nonfinite named verifier endpoints, regardless of whether legacy aliases exist.

Use schema-directed parsing. Keep genuine legacy parsing as an explicitly identified audit path; it must neither produce a new production-v2 acceptance nor relabel historical observations. If an unknown schema is encountered, do not silently choose an interval merely from available field names.

## Legacy safety distinction

A genuine old interval [99,101] includes the wait and surrounds a new verifier-call interval [100,100.5]. An active window [99.9,100.6] covers the latter but fails the old wider interval, as reproduced. Certifying a genuinely wider legacy interval is therefore stricter, not automatically an unsafe relaxation. The defect is silent schema substitution and accepting a malformed new record, not the mathematical idea of requiring coverage of a wider valid interval.

The new constructor always marks `interval_schema` v2 even when invoked with only legacy positional endpoints. Update intended test fixtures/callers or explicitly label their legacy audit mode when enforcing the new branch; do not retain silent fallback merely to preserve a misleading fixture label. The production sweep itself supplies the named v2 endpoints.

## Handoff

Close the NaN/infinity/text error-bound defect and the verifier-call timing definition. Make only the two branch repairs above with small pure-function fixtures. Root controls schema policy and final acceptance; no new experiment, lock-only rerun, or permission cycle is needed. Observer continuous-activity evidence remains a separate pre-existing requirement, not established by these arithmetic checks.
