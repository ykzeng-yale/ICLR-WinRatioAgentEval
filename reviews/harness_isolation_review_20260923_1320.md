# Harness isolation review — September 23, 13:20 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: prospective study and root acceptance (10 points, Session60/root), expanded release QA (5, root), and author checks (10, Yukang Zeng). These fixture improvements do not earn scientific milestone credit.

Reviewed **only** `de9ca8b116c7c82b5bc231de96c910fd35a71040` at working-tree head `0a3e64d6b8627eb3b70d8531391c91f528a1429a`. Later delivered harness changes are outside this report. Exclusive scope: `tests_supervisor_entry.py` isolation changes and `HARNESS_ISOLATION_CORRECTIONS.json`, owner timestamp **12:50:26 UTC**. No owner/shared file was changed.

**Disposition: accept removal of the unrestricted process fallback, explicit fake-clock injection and observed read-gate checks. One narrow test-enforcement completion remains: denied unexpected process attempts do not necessarily fail the harness.** The old 26-receipt audit remains closed.

## Independently executed scope

Only these changed/relevant owner tests were rerun:

1. `test_an_unreapable_child_reads_NOTHING_and_refuses`
2. `test_the_read_spy_DOES_see_reads_on_the_healthy_path`

**2 tests passed; 0 failures, errors or skips.** The saved fixture dependency was available. An extra bounded mocked-transport negative control was also run as described below. The remaining 12 owner cases were not rerun. All work used an outer Python audit deny guard for real subprocess/exec/fork, socket and signal operations, plus outer fallback guards for Popen, real sleep and real `time.monotonic`. The harness's expected launcher, HTTP calls, process/group operations and threads remained mocks. **No external deny guard was reached, and no actual child, HTTP/network operation, signal, server, model, build or real wait executed.** Temporary serialization and closed-file reads were real.

The unreapable-child case recorded **zero lifecycle/sidecar read-spy events and zero observer calls**, rather than inferring absence from receipt fields. The healthy positive control recorded six intercepted lifecycle read/open API events and one observer call; the six include nested interception of the same reads, not six separate acquisitions. Both cases recorded zero unexpected process attempts. This demonstrates that the current read spy observes the actual relevant path and that the closed-child gate avoids it on the unreapable case.

The explicit fake clock remains at `1000.0`, is passed into the real Deadline constructor, and also replaces the module's monotonic function. Both cases pass while the outer real-monotonic fallback raises on use. This closes the bound-default injection defect for these paths. It is not elapsed-time boundary coverage, which the new receipt appropriately disclaims.

## Narrow remaining harness defect

`fake_popen` now records and raises `AssertionError` on an unexpected command; **it no longer delegates to real Popen**. That isolation repair is accepted. But `_run` returns from `rs.main()` without asserting that `self.denied` stayed empty. Actual-main has legitimate exception handling around transport, so the guard exception can be swallowed as a normal request error.

Exact bounded witness: instantiate the existing fixture, then call `_run(post_hook=unexpected)` where `unexpected` invokes the patched `rs.subprocess.Popen(['unexpected-review-command'])`. Both attempted calls are denied in memory. Actual-main catches their `AssertionError`, writes a normal refusal receipt and returns status1; `_run` returns without raising, with **two entries in `self.denied`**. The errors are retained in the two request rows. No process reaches the outer OS-level guard or executes. This is a test-enforcement gap, not a surviving real-process fallback.

The docstring's statement that unexpected attempts “fail the test” is therefore too strong. Add a final assertion that the recorded denied-attempt list is empty, including paths whose production exceptions are handled, or use an outer isolation violation ledger checked after each case. Add one bounded negative control proving a deliberately denied unexpected command causes harness failure, even when the production path catches the immediate exception. Do not rerun the entire unchanged suite or invoke sysctl to demonstrate it.

## Receipt and historical claim limits

The deposited harness hash **`b80485fba28447b54bb6e019449f27aec49c90fb431e657e4c7f4f61937d47e8`** matches the receipt. The listed 14 case names exactly match 14 test methods. The reported full **14-case OK** remains owner-reported; this review independently ran only the two named cases plus its single extra negative-control scenario. No skip was counted as a pass.

The additive correction preserves the distinction between the old unrestricted fallback, the owner's reported historical sysctl behavior, and the independently observed guarded run here. Old no-child/no-clock claims are expressly withdrawn; no historical process was replayed. The observed read-spy acceptance is scoped to the existing Path/observer call sites; it is not a general guarantee against arbitrary future I/O paths.

Evidence: `reviews/evidence/harness_isolation_review_20260923_1320.json`. Root and other reviewers own response/intent, dependency-inventory and late deadline/schema changes. Next owner action in this scope is the small denied-attempt assertion/control, then continue the existing finite preparation/lifecycle work under current authorization.
