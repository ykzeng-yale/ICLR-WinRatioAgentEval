# Combined fixture review — 2026-09-22 00:01 UTC

Read-only audit of exact `902121319d810a495c7ef1e3146527c0a9760b3c`, its `lab_combined_fixture.py`, and `COMBINED_LOCK_SANDBOX_RECEIPT.json`. Recomputed only saved timestamp differences and order relations. No process, sandbox, reference, model, or serving execution was launched.

**Accept the implemented supervisor-outside/sandbox-inside topology and the saved same-lock contention timeline. The claim that the observed liveness marker belongs specifically to this holder is not fully bound by the current handshake.** Preserve the successful record; do not relabel this synthetic check as live evidence or a general security result.

## Accepted source route and saved timings

Both trusted supervisors use the same explicit isolated fixture lock through `lab_data._ExecutionLock`. Inside that critical section, the holder invokes the actual `sandbox.run_program`; the candidate program never opens or acquires the supervisor lock. This corrects the previous lock-only fixture's missing sandbox route. A blocked contender does not need to launch a concurrent sandbox program: preventing its entry is the intended architecture.

The committed receipt, rather than the GitHub/commit summary, records:

- holder PID **53113** and contender PID **53117**;
- holder lock-acquired to lock-released duration **2.0327934995 s**;
- holder sandbox-call duration **2.0327771679 s**;
- contender wait to reported lock-timeout **1.0277468329 s**;
- identical lock path in both supervisor records;
- contender `sandbox_started = null` and the specific lock-acquisition timeout error.

The following saved timestamp chain holds:

`lock_acquired <= sandbox_started <= marker_observed < contender_requested < contender_gave_up < sandbox_ended <= lock_released`.

Thus the recorded contender timeout occurred within the holder's protected sandbox-call interval. The recorded holder reports `sandbox_kind=seatbelt`, `sandbox_ok=true`. These are useful bounded integration observations, not just a quote of the authorized topology.

## Exact remaining handshake attribution gap

The parent waits for **any** `base/p_*/sandbox_active` file. The marker name is generic, and the receipt does not retain the selected marker path, holder sandbox-run identity, or a fresh per-invocation nonce. The `ready` and `active` paths passed to `_supervisor_source` are not used by its payload; deleting those fixture-work paths does not remove or disambiguate sandbox-base markers.

Consequently a stale marker from a prior interrupted sandbox run or a marker from another run could release the contender before this holder's payload becomes active. The saved timestamp ordering is internally consistent, but it does not independently attribute the observed marker to this holder. This is a missing handshake identity, not evidence that such contamination actually occurred in the delivered run.

For the existing explicit holder-active-before-contender requirement, bind the marker to a fresh invocation identifier and the actual holder sandbox run, record the matching marker/run identity and observation timestamp, and refuse readiness when the holder exits or no matching marker appears. There is no need to change the lock topology or make sandboxed code acquire the supervisor lock. This reviewer did not rerun the fixture; root determines the bounded final closure after the identity repair. Until then, accept the saved combined-route/supervisor-time contention subset and qualify the stronger holder-specific active-payload claim.

## Receipt precision and retained attempts

The GitHub/commit wording quoted PIDs 53004/53006 and approximately 2.029 s; those are not the deposited successful receipt's values. Correct references to the committed values above and retain other invocations under separate attempt identities, rather than mixing them into one reported run.

The initial denied-marker placement attempt is mentioned only as a narrative summary in this receipt. It is appropriately described as a fixture-path error; the successful probe did not require relaxing the sandbox profile. This summary is not a full raw receipt for that earlier attempt. Preserve any original available attempt evidence separately and do not imply it was independently reconstructed in this review.

The prior lock-only negative control and the fifteen repository-target denial observations remain separately bounded evidence. They are neither erased nor automatically expanded by this integration receipt. No broader concurrency sweep, model episode, or repeated unchanged test is requested here.

No readiness credit or execution authorization is granted by this report. Root separately handles source-acquisition mode intent and final project integration.
