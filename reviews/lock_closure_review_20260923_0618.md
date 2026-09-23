# Incremental lock-binding closure review — September 23, 06:18 cycle

Exact received head: `9db77f5ae6ce1cfe27ac75caece2d025b5d44359`; source repair `367bac7594391ec1438f22a8624311273bd77d1f`; reporter repair `be9540470f16ee7eca3611872a695f86fe5922d2`; base `79e5827`. Scope is the existing lock-binding and topology obligation only. Anchor code/remote transaction are reviewed separately.

**Disposition:** accept closure of the arbitrary-path and fixture-override bypasses, the shared resolver's runtime-versus-cached configuration refusal, and the topology reporter's foreign-checkout repair. One concrete production job-schema wiring defect remains. This does not reopen already accepted wrapper controls or request another lock acquisition experiment.

## Independent checks and accepted closures

Ran only `experiments.live_ab.tests_lab_isolation.ExecutionLockConformanceTests`: **10 tests passed**. The canonical-entry positive test reaches a later `KeyError: 'arm'` in its intentionally incomplete job and prints a traceback while passing; that is not an execution success. Independent positive checks below instead stub only `run_job`, proving arrival at that boundary without model, sandbox or lock acquisition.

Executed **16 bounded offline witnesses**, saved in `reviews/evidence/lock_closure_review_20260923_0618.json`:

- Actual `lab_worker.main` accepts canonical token and canonical absolute path; rejects arbitrary absolute, relative, stale trial token, and bare `<WORK>/sandbox.lock` before reaching `run_job`. The former non-token fixture exception is closed.
- Actual `sweep_references`, with provenance/task conversion stubbed and a stopping lock-constructor sentinel, rejects alternate paths with no flag, with `execution_lock_is_fixture=True`, and with `execution_lock_is_fixture="false"`, all before the lock constructor. The configuration self-label bypass is closed.
- The actual sweep rejects a supplied host root that differs from the cached audited pin before lock acquisition. The shared `resolve_execution_lock` used by both containment routes resolves matching config to the audited file and rejects a different root. No actual containment entry or probe was executed; its unchanged call sites were read directly. This closes the former split between resolver consumers when using a supplied differing runtime configuration.
- `lock_topology.resolve` runs successfully on this root host and under **two simulated distinct checkout/work/results roots**, each producing one distinct canonical path, all four worker renderings and sweep rendering equal to `<HOST_WORK>/sandbox.lock`, and route `canonical_token`. It now uses the effective production resolver and a host-aware renderer; the previous `UntokenizablePath` and checkout-local sweep reconstruction defects are closed.

The pure resolver and worker path checks involve no owner canonical lock acquisition. No wrappers/full suites were rerun; no server, model, sandbox program or network action occurred.

## One remaining blocker: worker validates the wrong job configuration shape

`World.build_job` writes `sandbox` at the job's **top level** and does not emit a `cfg` field. The repaired `lab_worker.main` calls:

```python
lab_common.assert_host_root_agreement(job.get('cfg') or {}, stage='lab_worker.main')
```

Consequently the actual produced sandbox block is never checked by this call. The new conformance test constructs a different job shape, putting its conflicting sandbox under `cfg`; that test passes without covering the production representation.

Independent producer-to-consumer witness:

1. Called the actual `World.build_job` with synthetic World state and a supplied sandbox host root different from the audited module pin. It emitted `<HOST_WORK>/sandbox.lock`, a top-level sandbox block, no `cfg` field, and a payload digest that matches the actual canonical payload function.
2. Passed that exact job through actual `lab_worker.main`, with only `run_job` stubbed. The entry returns 0 and reaches `run_job` using the cached module lock despite the disagreeing top-level pin.
3. Added the same disagreeing sandbox block under `job['cfg']`. The entry now refuses with `PreflightError` before `run_job`.

This is the existing effective-configuration consistency requirement, not an expanded adversarial-security requirement. The actual lock still stays on the cached canonical path; the defect is silent disregard of the configuration the production job says it uses. The worker and sweep therefore still have different refusal behavior for the same supplied host-root disagreement.

**Rank 1 next owner action:** validate the actual top-level production job configuration against the trusted audited pin before `run_job`/dispatch. If nested `cfg` remains supported, validate it as an additional representation rather than selecting it instead of the top-level block; conflicting representations must refuse. Keep one shared agreement function. Add a bounded test that constructs the job with actual `World.build_job` (or its exact emitted shape) and checks matching and mismatching top-level roots, plus a conflicting nested representation if supported. Preserve canonical path checks and fixture isolation in the test process. No model, sandbox, cross-wrapper rerun, or new design question is needed.

## Receipt scope and retained evidence

`LOCK_BINDING_REPAIR.json` at **05:48:08 UTC** is retained as the owner's repair report. Its claim that a “job-carried host root must AGREE” is verified only for the nested test representation, pending the production-shape repair above.

`LOCK_TOPOLOGY_v8.json` at **05:49:41 UTC** is accepted for its one-path snapshot, host-aware rendering and route-label correction. It retains the prior versions and reports a real second-clone canonical path equal to the owner path. That real-clone run is owner-delivered evidence inspected here; this review independently used two simulated checkout root sets rather than repeating the clone. Its `entry_refusals` field explicitly states it calls assertion helpers directly: it is not an end-to-end producer/job-reader check and cannot close the remaining schema mismatch.

Previously accepted `CROSS_WRAPPER_LOCK_CONTROL.json` remains evidence for two observed cross-wrapper exclusions and two no-holder acquisition controls. It was not rerun and need not be repeated for this remaining configuration check.

Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. Latest supplied owner status is **September 23 06:16:56 UTC**: zero trial/calibration episodes, 14/26 structural freeze components, nothing running. This review is implementation acceptance only and earns no study-completion credit. Remaining: Session60 prospective study plus root acceptance (10 points), root final expanded package QA (5), Yukang Zeng's author checks (10).
