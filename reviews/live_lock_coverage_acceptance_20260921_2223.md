# Lock and coverage delta acceptance — 2026-09-21 22:23 UTC

Reviewed exact `8801c2f037185594b53818969b8fb39a91469729` (main context `f0441a9`). Only the new numeric helper was executed with small deterministic inputs; the lock fixture source and committed receipt were inspected without launching any process, sandbox, model or server.

**Accept the three prior numeric repairs and the saved two-process lock-implementation contention evidence. One numeric fallback remains wrong. The receipt does not establish a combined production-lock/sandbox execution path.**

## Numeric repairs

The exact new helper rejects all three previously reproduced cases: negative window error/resolution, reversed attempt endpoints, and NaN attempt start. A finite ordinary spanning interval passes. A positive verifier endpoint error expands the attempted interval as required; the tested two-second error correctly makes the otherwise covering window insufficient. The returned conditional interpretation correctly distinguishes interval arithmetic from evidence that an observer has established continuous activity.

Remaining exact defect: `v_err = _finite(record.get('endpoint_error_s')) or 0.0` collapses an explicitly invalid value to the same zero used for absence. With an otherwise valid attempt [100,100.5] and covering window [99,101], each of these **provided** verifier error bounds returns valid:

- NaN;
- positive infinity;
- the string `invalid`.

This fails the stated finite-error-domain contract and can certify coverage without a usable verifier uncertainty bound. Distinguish the documented absent-field default from a present but malformed/nonfinite value; refuse the latter. Keep zero valid and retain expansion for positive finite bounds. A small regression test of that branch completes this numeric repair; no new measurements are needed.

Root separately resolves the meaning/location of verifier endpoints and the observer's continuous-activity contract. This review does not infer an implemented valid observer from the helper's `conditional_on` field.

## Saved lock receipt: timings support the bounded result

Recomputed directly from `results/live_ab/LOCK_CONTENDER_RECEIPT.json`:

- Holder PID 42056 acquired at 5176532.724385458.
- Distinct contender PID 42057 attempted at 5176532.762389916 and gave up at 5176533.815590041, a wait of **1.053200125 seconds**, with the recorded one-second lock-timeout error.
- Holder's recorded release boundary was 5176534.231407208, after the contender's timeout. Thus the contender's entire attempt/timeout occurred while the holder's recorded critical section remained active.
- In the isolated no-lock control, holder PID 42069 entered at 5176534.263146 and the contender PID 42070 entered at 5176534.291283125, before holder release at 5176535.766370125. The saved times establish observable overlap in that control.
- The receipt records the readiness handshake and distinct control lock path. The source removes/bypasses locking only for the synthetic control; it does not disable the production configuration.

These observations establish the exercised production `_ExecutionLock` implementation's one-holder/one-contender behavior on the fixture lock. They are materially stronger than the earlier empty-peer-glob observation. No lock timing experiment needs repeating merely to reconfirm these saved calculations.

## Exact source/label limitation

`lab_lockfixture.py` invokes ordinary Python subprocesses using `subprocess.Popen` and `subprocess.run`. The child imports and enters `lab_data._ExecutionLock`; it never invokes the sandbox execution function. The normal fixture lock path is `<WORK>/_lockfixture/sandbox.lock`, while the actual reference sweep resolves its configured lock or defaults to `<WORK>/sandbox.lock`. The same lock **implementation** is exercised, with matching lock identity for both fixture children; the actual production lock file and sandbox route are not exercised together.

Consequently “PRODUCTION-LOCK/SANDBOX FIXTURE” and the receipt's assertion about holding “the production lock” overstate this source/receipt. Label it a **two-process fixture of the production lock implementation on an isolated lock file**. Keep sandbox-profile containment separate, as the fifteen accepted repository-target denials already do. Source comments quoting authorization to use the combined route are not evidence that it was implemented.

If the existing required milestone is the combined two-probe lock/sandbox path, it remains pending that exact integration. Preserve this useful lock-only receipt and the prior denial receipt; do not discard them or rerun the same lock-only measurement to improve its label. Root owns the already authorized bounded remaining integration and any final milestone decision.

No broad suites or unchanged witnesses were run. No readiness credit or additional execution authority is granted here.
