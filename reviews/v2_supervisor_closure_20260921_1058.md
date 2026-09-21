# Supervisor closure check: 2026-09-21 10:58

Exact owner head `4f65c54ea95ec85e8fb384bc79e0f1802260cd6f` versus `7a12acb28197e3b08677ebe1171bcaae520b0835`; inspected immutable export `work/v2_review_1058`. Scope is only the two previously open supervisor findings. Root owns shard/launcher/manifest review. No scientific, native, model or process jobs ran; isolated Python mocks intercepted subprocess queries, signals and time. No outcomes inspected.

## Closed

**Owned-group escalation:** `_terminate_own_job` now checks existence of the saved owned group rather than the leader's exit status (`vsupervise.py:383–407`). Repeating the exited-leader/persistent-group fixture emitted both SIGTERM and SIGKILL to the same saved group. The previous early-return counterexample is repaired. No unrelated process or group was queried/signalled by the fixture.

**Enumeration exception and handler placement:** `_descendant_pids` now raises `MeasurementFailure` on command exceptions (`vsupervise.py:71–85`), and the enumeration call is inside the main monitoring exception handler (`vsupervise.py:250–258`). The previous synthetic command exception now raises instead of returning a leader-only subset. This portion of the monitoring finding is closed.

## One residual part of the existing monitoring finding

**Partial RSS coverage still passes in the actual caller.** The helper now rejects one RSS row for two requested PIDs by default, but `supervise` unconditionally passes `allow_missing=True` at `vsupervise.py:256`. No intervening check verifies that a requested process exited. The existing fixture—return code 1, one numeric RSS row, two requested PIDs—therefore still returns 125,952 bytes with the actual caller's arguments. The default-argument helper test correctly raises, but does not exercise production behavior.

Smallest repair: do not pass `allow_missing=True` unconditionally. A conservative failure on incomplete observation is sufficient; if retaining a process-exit race allowance, establish that race before allowing it. The same fail-closed intent applies to enumeration's nonzero status with partial stdout (`vsupervise.py:86`), which is still accepted: unavailable live-tree coverage must not be treated as complete. This is the remaining portion of the prior monitoring request, not a new monitoring architecture requirement.

## Reproduction and consequence

Mock evidence is `work/supervisor_closure_1058/synthetic_findings.json`: enumeration exception raises; partial-RSS default raises; partial-RSS actual caller flag returns 125,952; persistent owned group receives signals 15 then 9 despite leader exit. Source was imported without running its entrypoint.

Keep the previously accepted resource observations and conditional T1 projection unchanged. These source-only repairs require no new timing or scientific rerun. Complete the small monitoring-call correction and root's separate launch wiring before the full attempt.
