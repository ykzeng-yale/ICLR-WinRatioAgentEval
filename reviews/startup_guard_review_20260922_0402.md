# Independent startup-guard delta review — 2026-09-22 04:02 cycle

Reviewed `51280b8714cebfb4601bcf224042db5e143b41fe` on current main `f0d29a4`. The target modules/tests have no intervening differences at that main. Exclusive review scope: shared fixture activation policy and its actual production callers; narrow readback of the prior diagnostic-wording fix. No owner files edited, no models/servers/native verifiers, no remote posts, no timing experiment or whole test suite.

## Decision

**Accept the fixture-startup implementation repair.** The policy is now reachable in the real trial preflight, real `World.spawn` and real `lab_worker.run_job` bodies. This acceptance concerns refusal before the next named side effect; it is not an end-to-end live trial or serving-readiness claim. The owner has explicitly disclosed that worker TMPDIR wiring remains unfinished. That existing implementation task needs completion under the standing instruction; it is neither a newly discovered permission blocker nor a reason to repeat the fixture review.

## Source and caller readback

- `lab_common.fixture_requested` defines one stdlib-only predicate: any top-level `injected_decision_fixture` key counts, including None/False/empty values; a truthy entry under a mapping-valued `testing` block also counts. Clean and explicitly false nested testing controls do not request activation.
- `lab_common.assert_no_fixture` raises `PreflightError` from that predicate. `lab_injected_decision.assert_no_test_fixture_active` delegates to it while preserving its existing `FixtureActivationRefused` subtype. It does not retain a second independent membership predicate.
- `lab_orchestrator.preflight` checks the invocation configuration and its frozen projection before reading frozen-file digests or accumulating drift. `run_trial` invokes this actual preflight. `frozen_cfg` removes underscore runtime overlay keys rather than nesting a second hidden configuration.
- `World.spawn` checks its context configuration before log-file creation and before `Popen`. `dispatch` can already have written a job file before entering spawn; therefore the precise verified boundary is **before process launch**, not before every filesystem write on all possible dispatch paths.
- `lab_worker.run_job` checks both the actual job and its optional `cfg` before constructing its spool. The production `build_job` path is itself protected upstream by preflight/spawn. The worker check does not rely on a check in the parent process.

## Independent targeted execution

Ran exactly `tests_lab_design.ProductionStartupGuardTests` with bytecode writes disabled: **11 tests passed in 0.013s**. Seven tests exercise the relevant production bodies under stubbed dependencies; four inspect policy/seams/source reachability. The important controls are:

- Fixture-requesting spawn: mocked Popen never called and `att.proc` remains None.
- Clean spawn: reaches one mocked Popen and returns its synthetic pid4242. No OS worker actually starts.
- Fixture at job top level or within job cfg: spool constructor never called.
- Clean worker job: reaches a stubbed spool constructor; the deliberate sentinel terminates before any request or verifier.
- Fixture preflight: refuses before the digest function is called.

Added one bounded independent clean-preflight control: mocked path existence and made the digest raise a sentinel. The clean configuration passed the guard and reached the mocked drift-accounting call exactly once. Thus refusal is not blanket failure at any of the three checked boundaries. This is a control-path check, not successful complete preflight.

## Earlier diagnostic correction

The current `lab_load.observe` emitted `means` now explicitly describes observed content-arrival traffic only, states that it cannot establish production between arrivals or bound server idle time, and denies coverage certification. The opening `windows_from_arrivals` description likewise fixes the prior continuous-production overclaim. One stale internal paragraph still says that `_coverage_verdict` unions those windows; that description is obsolete, because client-arrival observations are refused and lifecycle coverage requires concurrency. It is a minor documentation cleanup, not a coverage escape or a new collection gate. This review did not repeat the broader diagnostic suite or independently approve its other changes.

Actual server-side lifecycle instrumentation and receipts, named-clock alignment, remaining TMPDIR enforcement and the complete prospective freeze remain separate unfinished work. Fixture-startup refusal does not establish any of them, and this bounded acceptance should not be reported as a completed live experiment or as a project-readiness increment by itself.
