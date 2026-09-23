# Independent protected-path review — 2026-09-23 14:03

**Full-project arXiv readiness: 75%, change 0 points. Bounded-v1: 90%.** Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), expanded final QA 5 (root), and author checks 10 (Yukang). These implementation findings earn no scientific-result credit.

Reviewed main [`176e682f5688ee4c786d4840fb3ac7f40351a677`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/176e682f5688ee4c786d4840fb3ac7f40351a677), source [`1e58d3b041c3310c1df19aa5cefaf0cad5040af2`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/1e58d3b041c3310c1df19aa5cefaf0cad5040af2). Scope is the changed preparation/launch/cleanup path under the [13:20 root disposition](acquisition_contract_disposition_20260923_1320.md), not the whole acquisition contract.

## Disposition and method

**Accept the pre-Popen request-intent persistence ordering and zero-child refusal on intent failure/collision. Accept that exceptions during request start/join now reach child cleanup and a refusal receipt in the bounded cases below. Do not accept the claim that everything after launch follows one protected cleanup/finalization path.** Three failure witnesses still escape without a terminal receipt, and one of them leaves the started child uncleaned.

Eight actual-main cases ran once. Process creation, HTTP, signals, monotonic time and thread scheduling were mocked; `_now` fields were synthetic, while filename wall-clock formatting was unchanged. Real intent/response serialization, lifecycle reader and finalizer used closed synthetic temporary files. Launch verification was stubbed as another reviewer's scope. No actual child, server, model, HTTP, network, native build, full suite or real wait ran; no growing owner file was analyzed. Fault injection was confined to the mock process/thread interfaces, not production-source edits.

Evidence and event traces: [`evidence/protected_path_review_20260923_1403.json`](evidence/protected_path_review_20260923_1403.json). Exact SHA-256 values are recorded there, including:

- `run_smoke.py`: `2d2ec42beccc9e8b41790a6e22cba245ae7412cccba86f4b040e3b77f5b17fb1`
- `lab_common.py`: `aa32c13a0f3c6895f6a4d7936cc2b883930e5f4db9491a7f3aa444c8e1c3bb1c`
- `lab_lifecycle.py`: `604556893fb5d381049756f765251bc45bd1f57ea632630d68fe2ee5610ac0b2`

## Eight bounded outcomes

| Case | Popen / POST calls | Stop / reap calls | Terminal receipts | Outcome |
| --- | --- | --- | ---: | --- |
| Valid control | 1 / 2 | 1 / 1 | 1 | Return 0; intent already exists when Popen is invoked. |
| Intent write failure | 0 / 0 | 0 / 0 | 1 | Return 1; no child exists to clean up. |
| Existing differing intent | 0 / 0 | 0 / 0 | 1 | Return 1; original intent bytes preserved. |
| Drain thread start raises | 1 / 0 | **0 / 0** | **0** | `RuntimeError` escapes; mock child remains unreaped. |
| Initial health-loop process poll raises | 1 / 0 | 1 / 1 | **0** | Original failure is caught, then `UnboundLocalError(results)` escapes. |
| Second request-thread start raises | 1 / 1 | 1 / 1 | 1 | Return 1; dispatch error preserved, but completed request state is omitted. |
| Request-thread join raises | 1 / 2 | 1 / 1 | 1 | Return 1; dispatch error preserved, but both completed request states are omitted. |
| Drain join raises after child reap | 1 / 2 | 1 / 1 | **0** | `RuntimeError` escapes before terminal finalization. |

The valid control independently matched both intent payload digests. The collision case checked the original on-disk bytes after return. Therefore the earlier intent-failure child leak is closed for that exact failure path; the broader cleanup claim is not.

## Ranked remaining defects and repair

### 1. Protection begins after drain construction/start

Popen succeeds at the trusted boundary, but drain creation and `drain_thread.start()` remain outside the new `try` (`run_smoke.py:877-899`). A synthetic `RuntimeError` at drain start escapes immediately, with no stop signal, reap, drain join or terminal receipt. The mock child still has `returncode=None`. This is a direct counterexample to the comment that every failure once a child exists reaches shared cleanup.

Establish protected ownership immediately after successful child creation. Initialize optional cleanup resources before using them; if drain creation/start fails, preserve that failure, stop/reap the owned child, and record unfinished/unavailable capture honestly without joining an unstarted thread or reading an active writer.

### 1. Early dispatch failure leaves `results` uninitialized and defeats finalization

The health-loop `proc.poll()` fault is caught by the broad dispatch handler, and stop/reap/drain cleanup occurs. However, `results` is first initialized at line 915, after health handling. The later retention-verdict expression iterates `results`, raising `UnboundLocalError` before the terminal receipt can be written. The child is cleaned up in this witness; the terminal evidence is lost.

Initialize request ledger/results and counters before entering fallible post-launch work. At cleanup/finalization, reconcile every planned request ID from the state actually reached, even when readiness, thread construction/start or dispatch failed. Preserve the original error rather than replacing it with a secondary missing-variable exception.

### 1. Cleanup and finalization still contain unprotected failure boundaries

`drain_thread.join(...)` at line 1122 is outside the dispatch handler. Its injected exception occurs after child reap, yet still escapes with zero terminal receipts. The new protected block covers a portion of dispatch, not the complete cleanup/evidence/finalization sequence. This review does not claim that every possible failure in those later stages was tested.

Make cleanup best-effort and stage-aware: retain each cleanup error, continue the safe remaining steps, and attempt terminal persistence once with truthful resource states. Do not claim complete drain/capture when join status is unresolved. Preserve the existing closed-file gate; recording an error is not permission to analyze files whose writers may remain active.

### 2. Mid-dispatch exceptions skip reconciliation and rely on incidental refusal reasons

The second-worker-start and request-join faults now clean up and write one normal return-1 receipt, which is useful progress. But request summaries are assigned only after all joins (lines 1072–1078), so jumping to the catch at line 1082 bypasses them. The witnesses observed one and two POSTs, respectively, with complete raw response artifacts, yet receipts retained `submitted_requests=0`, no completed-request/attempt summary, “token usage was not measurable for 0 request(s),” and “2 request(s) were planned but never submitted.”

`unhandled_during_dispatch` is persisted but is not directly included in `supervisor_problems`. **No false-success witness is claimed:** both cases refused because other default/missing fields triggered problems. Reconcile partial results independently of whether dispatch finished, and make an acquisition-stage exception an explicit refusal reason rather than relying on those incidental missing-field conditions. Request count and delivery statements must reflect the observed attempts/results.

## Next owner action and limits

Complete the already requested protected launch-to-finalization structure around these exact stage boundaries, with bounded cleanup and initialized per-request state. Extend the owner harness only with changed-path failure witnesses and its positive control; no separate repeat of unchanged accepted repairs, live smoke or broad suite is requested. The pre-Popen intent ordering closure should remain closed.

Root/other reviewers own manifest-domain coverage, library/source binding, response byte/state repairs and scientific integration. This review neither duplicates nor implicitly accepts those tracks. No owner/shared file was edited, no commit was made, and no experiment, paper, figure or package result was added.
