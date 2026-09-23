# Independent actual-supervisor review — September 23, 09:19 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), author checks 10 (Yukang). This implementation review adds no scientific evidence or milestone credit.

Exact head `549b60f99c383cb2a9128f52f953c7a2d9d48559`; substantive deliveries `450cc0b` and `9ce153e`, compared with `42cc49f`. Reviewed `experiments/live_ab_serving/run_smoke.py` through **eight actual `main()` invocations**, with every HTTP, child-process, signal, clock and thread interaction mocked. The real lifecycle observer and real write-once receipt function consumed synthetic closed files in temporary directories. No model, native binary, sandbox, real network call, actual child process or broad suite was run. Signal-contract normalization is another reviewer's scope; artifact selection, request/raw-usage retention and absolute deadlines are root's separate static review.

## Accepted integration subset

The supplied exit outcome now reaches the actual reader. With a clean synthetic seal and exit zero, `main()` returns zero and writes exactly one complete receipt. With the same otherwise valid bytes and process exit **93**, it returns one and writes exactly one receipt recording the reader's refusal. The problems list exists before that single write. The previously unconditional return-zero defect therefore closes on this tested failure branch.

The forced-kill branch now performs its second wait. In the independent first-wait-timeout/second-wait-returns-9 case, the child is confirmed stopped before the reader and raw-file accesses; the final status is one and exactly one receipt is retained. This accepts the added reap attempt, not the still-missing gate described below.

A separate drain is started before health/request processing, and ordinary producer diagnostic lines reach the final receipt. One newly changed owner drain-helper test passes. That test and the following actual-main cases establish selected behavior, not the advertised universal memory/deadline guarantee.

## Actual-main results

| Case | Main result | Receipt writes | Observed behavior |
| --- | --- | --- | --- |
| Exit-zero control | 0 | 1 | Reader sees zero; child confirmed stopped before reads |
| Producer exit 93 | 1 | 1 | Reader sees 93; process refusal retained before write |
| First wait times out, forced kill reaped as -9 | 1 | 1 | Second wait occurs; no log read before known exit |
| Both waits time out | 1 | 1 | **Child unconfirmed, but observer and three direct/parser log-read calls still run** |
| Diagnostic iterator raises after one line | **0** | 1 | Receipt contains a drain-failed text line; final problems ignore it |
| Drain still alive after bounded join | **0** | 1 | `drain_finished=false`; final problems ignore it |
| Closed main log contains invalid UTF-8 | exception | **0** | Reader raises before durable supervisor receipt |
| Process creation raises | exception | **0** | Startup failure leaves no durable receipt |

All eight cases use the same controlled actual supervisor entry point. Synthetic files remain unchanged while read. The failed-reap case tests the unsafe access path without creating or touching an actual growing file.

## Ranked finite corrections

**1. Gate all acquisition-file reads on confirmed termination.** `child_confirmed_stopped` is presently a recorded fact and a late verdict input, not a control-flow gate. After both waits fail, the function calls `observe`, reads/stat's the log and sidecar, and only then returns failure. Persist the unresolved process/cleanup refusal without analyzing those acquisition files. Continue only the already authorized bounded cleanup; do not describe a still-unconfirmed acquisition as closed. The existing no-analysis-while-writing requirement is not satisfied by a later nonzero status.

**2. Make diagnostic completion/failure part of the actual terminal disposition.** The newly drained pipe can still fail or remain unfinished, but both cases return success when the lifecycle observation passes. Represent drain failure as structured state, distinguish EOF/completed from interrupted or failed, and include an incomplete required diagnostic channel in the supervisor refusal/retention outcome. The existing absolute deadline must govern this work; a daemon thread is not itself an absolute deadline or completed acquisition. The raw child exit and available diagnostic prefix must remain retained even when the drain cannot finish.

The bounded-memory/accounting comment is also too strong. `for line in stream` obtains a whole line before truncating it, so an unterminated/very large line is not bounded by the 400-character preview cap. In a finite independent example, a 900-character line plus a one-character line retains 401 characters but reports `dropped_chars=0`, losing **500 characters** from the accounting. A bounded chunk drain can preserve a capped preview and accurate truncation counters without first allocating an arbitrarily long line. This is a repair to the newly claimed diagnostic bound; no new experiment is needed.

**3. Retain startup/read failures through the same single receipt path.** A process-creation exception and an invalid-encoding closed log each escape before `write_json_atomic`; no receipt remains. Wrap the actual main execution/cleanup/diagnosis stages so ordinary failures enter one final durable refusal receipt with stage, error, available process status and cleanup state. Do not retry a model request or substitute a new attempt to obtain a readable log. Hash/retain closed raw bytes without requiring them to decode; if the process is unconfirmed, preserve the unresolved state without reading potentially active files. Verify the new path through the actual entry point with mocked external interactions, not only helper tests.

These corrections are the existing process-closure, error-retention and finite-supervisor obligations. Root separately consolidates the unchanged absolute-deadline, launch-pin and request/usage requirements; this report does not duplicate or broaden them. No further loaded smoke is requested.

## Evidence and scope

[Machine-readable evidence](evidence/supervisor_review_20260923_0919.json) contains the eight actual-main cases, call ordering, reader outcome arguments, receipt counts, problems present before write, and the finite diagnostic truncation example. The owner receipts describe source-only/mock evidence; none establishes native execution of the repaired producer. Accept the exit-to-reader wiring, tested exit-93 nonzero result, added second reap attempt, and ordinary pipe draining/receipt recording. Keep the three concrete actual-main failure paths above open. Session60 owns repairs; root owns acceptance and the next prospective preparation milestone. Owner files, shared status, paper and release were not edited. Full readiness remains unchanged.
