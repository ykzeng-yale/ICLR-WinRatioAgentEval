# Live retention and enrollment acceptance — 2026-09-21 20:05 UTC

Exact source: `869317f1dddf703db312e72994956d29fb3673aa` (main context `f35512a`). Independent export: outer `work/retention2005/`. Only the two new test classes and bounded injected checks were run; no models, server actions, reference sweep, or sandbox execution.

## Acceptance

**Close the D1 sentinel/raw-payload correction and D2 production-dictionary enrollment comparison. Accept the ordinary save/reload and sink-exception plumbing. Remaining: handle short writes correctly and connect the sink to the actual preparation driver.** These are finite offline completion steps under existing authorization, not new design or permission gates.

The exact command `python3 -m unittest tests_lab_chain.OrderEnrollmentRefusalFixtureTests tests_lab_design.AttemptLedgerRetentionTests -v` in the immutable export ran **seven tests, all passing**, with no skips. An initial reviewer invocation from the repository root failed to locate the test modules; rerunning from the exported module directory corrected that reviewer invocation error. It was not a source/test failure.

## D1 correction: accepted

The record now reads top-level `sentinel_seen` and preserves `clean_exit` separately, together with the complete raw verifier result. An independent constructor witness with `run.passed=True` but top-level `success=False` and `sentinel_seen=False` returns `clean_exit=True`, `sentinel_seen=False`, and the unchanged raw payload. This closes the concrete field error from the prior review.

The new save/reload test executes `sweep_references` with a stub verifier and the real `AttemptLedger.append`; the saved records are reloaded from disk and reconstruct the exclusion digest. Its sink-failure test confirms an exception propagates out of the sweep. These are real plumbing tests, not comparison of two in-memory helper outputs. They establish the ordinary successful write and raised-error paths only.

## D2: independently close actual production-dict comparison

The four delivered tests call the actual verifier and assert enrollment findings. However, the existing fixture's deposited order is a **bare list**: therefore the owner's baseline and perturbed-uid tests do not themselves establish successful production-dictionary comparison. The unreadable and count-mismatch dictionary cases do establish actual refusal behavior.

I closed the remaining bounded question directly, using the same materialized deterministic chain, replacing its order with a valid dictionary containing `schema`, `n_pairs`, and `pairs`, and calling the actual `verify_trial` in plumbing mode. Number of findings specifically tagged `order.enrollment`:

| Dictionary case | Enrollment findings |
|---|---:|
| Valid dictionary | 0 |
| Changed expected uid | 1 |
| Changed expected stratum | 1 |
| Changed expected arrivals | 1 |
| Swapped first two expected pairs | 2 |

These checks distinguish the enrollment comparison from unrelated hash findings. Together with the delivered refusal tests and source review, this closes D2 for the reviewed dictionary path. Preserve these as a regression fixture when convenient, but do not require another scientific run or repeat this already closed witness for unchanged source.

## Confirmed remaining durability defect: short writes silently succeed

`AttemptLedger.append` performs one `os.write`, ignores the returned byte count, calls file sync, closes, and increments `count`. `os.write` can legally report a positive short write without raising. An injected deterministic witness used the actual append method with `os.write` constrained to write half its input:

- append returned normally;
- ledger count became 1;
- retained file had 30 bytes and no trailing newline;
- subsequent `load()` raised `JSONDecodeError`.

Thus loss of part of an attempt record can be reported as a successful append, contrary to the stated fail-closed retention contract. This is a directly reproduced defect, not speculation about a future model run.

Finite repair: encode once, write until every byte has been accepted, fail on zero/no-progress or an exception, sync, and only then increment the completed-record count. A positive short write should either complete through the loop or fail visibly; it must not be silently accepted. Keep any incomplete original tail as failure evidence and refuse a continuation that would append onto malformed JSON without an explicit preserved-tail recovery rule. For initial file creation, sync the containing directory as appropriate to the project's existing durable-file convention; file sync alone does not establish durable directory-entry creation after a power loss. Reuse existing directory-sync helpers rather than introducing a new persistence framework.

A test of an injected positive short write and a failing/non-progress write suffices; no resource failure experiment or real reference run is needed.

## Production wiring is still pending

At this exact tree, `AttemptLedger` construction and `on_attempt=ledger.append` appear only in `tests_lab_design.py`; `sweep_references` still permits `on_attempt=None`. The tests demonstrate that the **production sink implementation can be connected**, not that the **production preparation entry point already connects it**. Label this state accurately.

Connect the actual finite preparation/sweep entry point to a ledger created before the first verifier attempt, and make a missing sink or failed durable append stop that entry point. A stubbed driver-level call can establish wiring without running task references. Do not claim full production retention from helper tests or silently run the real sweep through the default no-sink path. Root separately controls load coverage, capacity and execution authorization.

No prior raw evidence was changed. No readiness points or model-execution authorization are granted by this review.
