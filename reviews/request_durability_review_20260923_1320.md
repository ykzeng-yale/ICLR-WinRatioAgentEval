# Independent request durability and transport review — 2026-09-23 13:20

**Full-project arXiv readiness: 75%, change 0 points. Bounded-v1: 90%.** Remaining 25 points: prospective study 10 (Session60 collection and root acceptance), expanded final QA 5 (root), author checks 10 (Yukang). These acquisition repairs earn no scientific-result credit.

Reviewed main [`0a3e64d6b8627eb3b70d8531391c91f528a1429a`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/0a3e64d6b8627eb3b70d8531391c91f528a1429a), request delivery [`60e85489768e60297210904859d01463522fb472`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/60e85489768e60297210904859d01463522fb472). The late delivery `3befd1507362904aaef8d3424983ae145b7a1480` was **not** executed or accepted in this review; root handles any carry-forward assessment separately.

## Disposition

**Accept ordinary request-intent persistence before barrier/POST, full response persistence before parsing on the normal path, preservation on serial collisions, and the newly recorded transport-attempt state. The acquisition contract remains incomplete.** Intent persistence failure skips cleanup of an already started child; byte completeness compares lengths rather than actual byte agreement; and transport/response states remain contradictory on several failure paths.

Nine changed-path actual-main scenarios were examined with child/process, HTTP, signal, monotonic-clock and scheduling interactions mocked. Receipt `_now` fields were synthetic; filename/attempt-stamp wall-clock formatting was unchanged and no elapsed-time boundary was claimed. The real reader, response writer, atomic intent writer and finalizer operated on closed synthetic temporary fixtures; artifact verification was stubbed because another reviewer owns it. One shape-error fixture was refined once so the raw body `[]` exactly matched the decoded list (10 main invocations total, same nine scenarios). All invocations returned normally with one terminal receipt. No real child, HTTP, network, model, build, full suite or real wait ran. No live owner file was opened while being written.

Evidence: [`evidence/request_durability_review_20260923_1320.json`](evidence/request_durability_review_20260923_1320.json). Reviewed code SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `experiments/live_ab_serving/run_smoke.py` | `845102536cacbb6910032ee25c900eddc28c9b54c4296c567a04acc750acbda7` |
| `experiments/live_ab/lab_common.py` | `aa32c13a0f3c6895f6a4d7936cc2b883930e5f4db9491a7f3aa444c8e1c3bb1c` |
| `experiments/live_ab/lab_lifecycle.py` | `96748320661b0cff2deec7550022f30e1a0615e8215df4b9e8e6218cdc992398` |

## Accepted subset

- **Request intent is now an on-disk artifact before the barrier and POST.** Both barrier and transport-entry spies found it present; both canonical payload hashes independently matched. Terminal finalization did not overwrite it. This is request intent deposited after Popen/readiness, not the still-required pre-Popen launch intent.
- **The ordinary long-response path retains exact bytes before parsing.** Both 12,124-byte successful responses were present in full when `.json()` began, with independently matching incoming/persisted SHA-256 values. Main returned 0 despite preview truncation, appropriately. Both 12,025-byte unparsable responses were likewise retained exactly before the parser raised; main refused unknown usage and preserved the parse failure.
- **Serial collisions preserve original evidence.** A pre-existing differing intent was not overwritten, and no POST occurred. Existing response artifacts were preserved under `xb` refusal; main returned 1 with incomplete-retention problems and performed stop/reap. This checks ordinary no-clobber behavior, not concurrent writers or power-loss durability.
- **A raised transport call now has an attempted state.** Two mocked POST calls that raised timeouts produced `transport_attempted_requests=2`, `requests_with_unknown_delivery=2`, and per-row `unknown_server_receipt`. This repairs the missing attempt field, but does not close the contradictory aggregate wording below.

## Ranked remaining defects

### 1. Intent failure returns before cleanup of the child already started

Both the injected intent-write failure and a real serial intent collision occur after the mocked Popen succeeds. At `run_smoke.py:739-745`, the failure branch immediately finalizes and returns 1. The event trace has **zero stop signals, zero wait/reap calls and zero drain joins**. `child_started=true` is persisted; the mock process still has `returncode=None` when main returns. No POST is sent, which is correct, but the owned child and drain are left unresolved.

Route every failure after child creation through the common bounded stop/reap/drain/finalization path, retaining any unresolved outcome honestly. Complete the separate pre-Popen immutable launch-intent obligation; the new request file does not satisfy it. A failure to persist request intent must prevent dispatch **and** clean up a child that already exists.

### 1. Equal-length altered response bytes are accepted as complete

`_persist_response_bytes` measures the saved hash but sets `complete` solely from equal lengths (`run_smoke.py:479-485`). A synthetic fault wrapper changed one byte during the normal `xb` write while preserving length. The helper then read the actual closed artifact; no read-back result or digest was fabricated. Incoming 12,124-byte body SHA-256 was `825392aa994e2cd58fdb0d3155d627780f8662984de95f146ab507a50c2564df`; persisted SHA-256 was `69f50c7f68344fcdc50cff8c8c32b2cece513687370a3b7822fab5e27a2472ed`. Both rows reported `retained=true`, `complete=true`, and main returned **0** with no problems.

This is an injected finite fault witness, **not a claim that real corruption occurred**. Compare measured bytes/hash against the received bytes/hash and refuse any mismatch, retaining both identities and original observations. The measured digest is accurate; the completeness predicate is not. This closes the already stated strict byte-agreement requirement rather than adding a new requirement.

### 2. Attempt/response/unknown-delivery reconciliation still contradicts observations

- **Transport timeout:** the receipt correctly records two attempted calls and two unknown deliveries, but still adds “2 request(s) were planned but never submitted.” The final predicate uses the response-return counter `submitted_requests` rather than dispatch attempts. Preserve the existing field's historical meaning explicitly or rename it; do not derive never-attempted claims from absent responses.
- **Post-response shape error:** a real synthetic HTTP 200 response with raw bytes `[]` is saved intact before its decoded list reaches `.get`. The resulting `AttributeError` enters the broad transport exception handler (`run_smoke.py:856-866`) and rewrites each row to `response_received=false`, `delivery=unknown_server_receipt`, while `submitted=true`, `status=200` and the complete raw-response artifact remain. Separate transport exceptions from parsing/usage/retention failures; observed response receipt must never be undone by later processing failure.
- **Unfinished worker after transport invocation:** two fake workers were parked immediately inside mocked POST, after the real pre-call attempt increments, without appending result rows. Their synthetic joins returned while marked alive; no real thread or growing file existed. Main retained two attempts and the already-correct expected denominator of two, refused unknown usage, but reported **zero** unknown deliveries and again “never submitted.” Reconcile states by all planned request IDs, including unfinished requests. The existing missing-usage refusal remains accepted; the new delivery summary must not count only completed rows.

## Case inventory and next action

| Scenario | POST calls | Stop/reap | Main return | Result |
| --- | ---: | --- | ---: | --- |
| Long valid responses | 2 | Yes | 0 | Exact raw retention before parse accepted. |
| Intent write failure | 0 | **No** | 1 | Dispatch refused; child cleanup missing. |
| Intent collision | 0 | **No** | 1 | Original intent preserved; child cleanup missing. |
| Transport timeouts | 2 | Yes | 1 | Attempt fields accepted; never-submitted wording remains false. |
| Long unparsable responses | 2 | Yes | 1 | Full raw bytes and parse failure retained. |
| Response collisions | 2 | Yes | 1 | Original artifacts preserved; retention refused. |
| Equal-length write alteration | 2 | Yes | **0** | False complete-retention acceptance. |
| HTTP 200 body `[]` | 2 | Yes | 1 | Response receipt incorrectly reset to unknown delivery. |
| Unfinished workers after call entry | 2 | Yes | 1 | Attempt count retained; delivery summary omits unfinished IDs. |

The owner should repair these witnesses in the existing actual-entrypoint scaffold; no repeated live smoke or unchanged broad suite is requested. Root owns aggregate/scientific acceptance and the standing deadline/finalization handoff; other reviewers own harness isolation and library inventory. No owner/shared files were changed, no commit was made, and no scientific result, paper integration or package update occurred.
