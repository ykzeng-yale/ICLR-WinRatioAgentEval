# Supervisor repair delta: 2026-09-21 10:22 review

Exact owner head `7a12acb28197e3b08677ebe1171bcaae520b0835`, immutable export `work/v2_review_1022`; reviewed safety/metadata changes since `3341f2107b9ff9a5d67c9a09c3c27e9a4fe74d7d`. Root owns launch manifest, shard design and scientific acceptance. No scientific outcomes inspected and no model, native reference, timing or grid calls executed. Only isolated Python mocks of supervisor helpers were run; those mocks created/signalled no actual child processes.

## Decision

The accepted historical measurement and conditional 2,676.3868-second T1 projection remain accepted within their previously documented scope. No remeasurement is requested. Two requested supervisor repairs remain incomplete before a full attempt: fail closed on unavailable process-tree enumeration, and finish escalation for the owned process group after its leader exits. These are continuations of the existing repair request, not new architecture or experimental requirements.

## Closed or substantially repaired

- `vmeasure.py:153–159` now rejects a missing baseline reference file instead of treating it as a match. `vmeasure.py:213–231` records a mismatch and returns status 4. These close the previous baseline/mismatch findings; they do not alter the already independently verified byte identity of the delivered measurement.
- `vsupervise.py:149–155,224–231` converts RSS command exceptions/no-data failures into a `MeasurementFailure`, records a breach and invokes owned-job cleanup. A synthetic RSS-command `OSError` was independently confirmed to raise rather than return zero.
- `vsupervise.py:233–237` adds a default 256-KiB reserve to the directory bytes at each poll. This exceeds the 11,418-byte difference between the accepted child snapshot (103,713 bytes) and the deposited directory (115,131 bytes). The new sampled-RSS scope text correctly disclaims a continuous hard memory bound. The old receipt remains historical evidence; no new measurement was delivered by these source changes.
- Available-RAM observation and a fail-closed optional threshold are added at `vsupervise.py:101–132,190–201`; `vlaunch.py:290` supplies the T1 RSS threshold. Thus the intended launch now requests a capacity check beyond total RAM. `vmeasure.py:208–210` does not supply this optional threshold, so it records availability without enforcing it; this is not a reason to repeat the accepted measurement.

## Still open before the full attempt

1. **Owned-group escalation still returns when the leader exits.** Although the group ID is now saved at startup, `vsupervise.py:351–352` retains the exact old early return. With a mocked already-exited leader and a saved group ID, `_terminate_own_job` issued SIGTERM only, never SIGKILL. A descendant ignoring SIGTERM can survive; saving its group ID alone does not repair this. Remove the leader-only completion condition and use bounded group-existence/escalation logic for that saved owned group. Do not signal unrelated processes.
2. **Tree enumeration still silently degrades.** `_descendant_pids` at `vsupervise.py:71–74` still returns only the leader after a `ps` exception, and ignores command return status. A synthetic exception independently returned `[123456]`. RSS sampling of that subset can then succeed and undercount descendants. Raise a monitoring failure and route it into the same cleanup/failure-receipt path; presently the descendant call at line223 sits outside the RSS exception handler. Retain a narrow exception for a verified child-exited race. Also handle the RSS command's nonzero status explicitly: line153 currently accepts nonzero status when stdout is nonempty. A fixture with rc=1 and one numeric line for two requested PIDs returned 125,952 bytes. This is not proof that every partially missing process is a failure—some processes can legitimately exit—but unavailable live-tree coverage cannot count as a passing complete observation.

## Scope details, not new timing blockers

The reserve is admission headroom, not observed bytes: `peak_output_bytes` now includes the reserve during polling while `final_output_bytes` remains the actual child directory size before parent metadata. Label those two quantities accordingly and perform/report the final artifact total as part of launch finalization. The 256-KiB reserve comfortably covers the accepted measurement's metadata; it is not itself evidence that an unimplemented shard launcher will never produce more metadata. Root's exact launch/shard review should retain the common 200-MiB total budget, without requesting another development timing run solely for this label.

The RAM helper is a `vm_stat`-derived capacity estimate and should be named as such rather than asserted to be an exact OS guarantee of allocatable memory. The actual measured workload remains far below the process-tree cap. This review did not test host capacity or change any running process.

## Reproduction and disposition

Mock evidence: [retained synthetic findings](evidence/v2_supervisor_mock_checks_20260921_1022.json): descendant command exception returned leader-only; RSS exception raised; rc=1 with partial numeric stdout passed; exited-leader cleanup emitted SIGTERM only. Source was imported without invoking the program entrypoint. No effect values or experiments were opened.

Smallest next action: finish the two existing supervisor fixes, verify them with mocks/controlled tiny children, and complete root's exact capped launch wiring. Preserve the accepted measurement, original receipt scope and conditional T1 resource decision. Do not introduce another timing sweep or silently alter T1 scientific coordinates.
