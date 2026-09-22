# Bounded startup and fixture delta review — 2026-09-22 01:44 UTC

Exact reviewed commit: `47b6a05672615e51afd918a186abbbebaf6141da`. Sources and tests were exported immutably to outer scratch `work/startup0144`. No sandbox, model, real fixture process, or full suite was run. This reviewer changes only this report.

## Accepted repairs

`lab_combined_fixture.py:135–142` now resolves the sandbox base and scans for the nonce marker before holder creation. This closes the false-negative race identified in the prior review. Its source-order test passes.

`lab_combined_fixture.py:172–185` now returns an invalid receipt before contender launch when readiness is false. It retains parsed holder outcome and stderr. Beyond the source-order test, an independent mock of holder/Popen/subprocess.run exercised the false-readiness path: `valid=False`, `contender=None`, retained stderr, and **zero contender calls**. No real subprocess was launched. This closes the previous missing-readiness gate. Existing successful v2 evidence remains accepted in its prior scope; no new saved success was independently reproduced here.

`lab_prepare.py:622–642` constructs a child environment with prescribed TMPDIR after validating configuration and directory existence. `:645–672` delegates worker validation to the shared prescribed-directory helper and additionally rejects a disagreement between the environment and Python's resolved temporary directory. It does not change Python's cache to force agreement. These are suitable helper-level checks, including the explicit startup/restart phase and redacted refusal diagnostic.

## Actual caller status remains incomplete

At this exact commit, repository-wide Python search for `launch_environment` and `assert_worker_startup` returns their definitions and calls only in `tests_lab_design.py`. There are **no production supervisor or worker callers**. Accordingly, wording that these checks are already “called at startup and after restart” is not established. The tests call helpers directly; their names “before any worker” and “before dispatch” do not demonstrate real orchestration ordering. Root's existing next action should wire the supervisor's returned environment into the actual spawn, and call the worker check before dispatch in direct startup and restarted processes. This is the remaining previously requested implementation obligation, not a request for another empirical study.

## Narrow test evidence and portability limitation

Ran only `WorkerStartupEnforcementTests` (6 methods) and `CombinedFixtureControlFlowTests` (2 methods): **7 passed; 1 errored**. The valid-launch test assumes `/private/tmp/labsbx` already exists; it does not on the independent review host. The helper correctly refused. This is a test setup dependency, not evidence of invalid production acceptance. Repeated only that method with `Path.is_dir` stubbed true: **passed**. The immutable owner test should explicitly stub a valid prescribed-directory condition rather than silently depend on that host path. No actual prescribed directory was created or changed for this review.

Disposition: accept the two bounded fixture corrections and startup helper behavior. Production startup/restart enforcement is still helper-only at this commit. Complete the already requested caller wiring and make the valid-launch offline fixture self-contained. No project readiness points or live preparation/collection completion are asserted by this review.
