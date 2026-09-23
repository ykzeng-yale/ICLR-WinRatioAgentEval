# Independent actual-main request-path review — 2026-09-23 11:16 cycle

**Full-project arXiv readiness: 75%, change 0 points. Bounded-v1: 90%.** Remaining 25 points: prospective study 10 (Session60 collection and root acceptance), expanded final QA 5 (root), and author checks 10 (Yukang). This implementation review earns no scientific-result credit.

Reviewed immutable main [`a9efa754541c3f588660d82c88c091a3448f8021`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/a9efa754541c3f588660d82c88c091a3448f8021), request repair [`84d60562e1bb420d6e09d86c011dbb8dac2cd0c0`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/84d60562e1bb420d6e09d86c011dbb8dac2cd0c0), against `e314260b49cf7137a80413c9182679f10330118e`. Owner delivery: `results/live_ab/REQUEST_INTENT_AND_USAGE.json`, timestamp `2026-09-23T11:17:32Z`.

## Disposition

**Accept the bounded request-cutoff and missing-usage closures below. Do not accept request acquisition as complete.** Intent still is not durable before dispatch, response bytes still are not retained in full, and timeout accounting still confuses an attempted request with no submission. The broken-barrier path can still return success.

Seven invocations exercised the actual `run_smoke.main()` with fake process, HTTP, signals, clock and thread scheduling; the reader, capture helper, finalizer and closed synthetic files were real. Deadline used an explicitly injected clock, avoiding its import-time default-clock binding. Artifact verification was stubbed because root owns that review. No real process, model, HTTP, native build, sandbox job or full suite was run. All seven cases returned normally and wrote exactly one final receipt. Evidence is in [`evidence/request_path_review_20260923_1116.json`](evidence/request_path_review_20260923_1116.json).

## Accepted subset

1. **Prior cutoff witness closes.** The mock health check began with 509 seconds elapsed and returned at 511, after the 510-second dispatch cutoff. Both worker records now report not dispatched, no POST was invoked, and main returned 1 with one receipt. This establishes the new post-barrier guard for this path, not enforcement of all startup/health/cleanup deadlines.
2. **Missing response usage is no longer measured zero.** Two timeout exceptions, two responses without usage, and two unparsable responses each produced `generated_tokens_total=null`, `token_cap_respected=null`, and refusal status 1. A positive control with explicitly reported zero completion tokens produced measured zero, cap true and status 0.
3. **Request descriptions and response diagnostics survive ordinary parsing failure through finalization.** Both planned payload digests independently matched the canonical payloads. Unparsable responses kept byte counts, matching SHA-256 values, labeled 4,000-character previews and parse-error fields. This is diagnostic retention only; it does not establish full raw retention or pre-dispatch durability.

## Material remaining defects and next owner action

| Priority | Actual-main witness | Required repair |
| --- | --- | --- |
| 1 | Every barrier and POST entry observed zero durable JSON writes and an empty results directory. `out['planned_request_intent']` at line 569 remains memory until finalization. | Deposit immutable per-attempt/request intent, including IDs, payloads and pins, before threads/barrier/HTTP. Refuse dispatch if deposit fails. The final receipt can remain a separate write-once artifact. |
| 1 | Two successful 9,137-byte HTTP responses returned status 0, yet their unique tail marker was absent from **every** persisted file. Their hashes were correct but only 4,000-character previews remained. The 9,038-byte unparsable responses had the same loss. | Retain full raw response bytes within a declared finite acquisition budget in immutable artifacts, with measured byte counts, hash and reference before parsing. Persist available bytes and explicit incomplete/overflow status on failure; a digest of discarded bytes is not raw retention. |
| 1 | Two actual mock transport invocations that raised response timeouts yielded `submitted_requests=0` and “2 request(s) were planned but never submitted.” The increment occurs only after `requests.post` returns (lines 597–602). | Preserve distinct planned, dispatch-attempted, response-received and unknown-delivery states. Record attempt before invoking transport; a timeout does not establish that the server received nothing. Do not rename response-return counts as actual submissions. |
| 2 | With clock 0 and a barrier exception, both POSTs still executed, main returned 0, and final problems were empty even though each request retained `barrier_error`. | End the affected worker without dispatch after barrier failure, and make synchronization failure explicit in the final refusal. A still-positive time budget does not repair a failed required barrier. |

The timeout witness proves the current accounting loses dispatch attempts; with mocked transport it does not claim actual server acceptance. The long-response witness tests persistence independently by checking all closed temporary files, not merely reading the receipt's own retention assertions. Successful payload hashes certify the declared canonical payload, not transport-level wire serialization.

Root separately owns pure helper/domain cases (including negative token counts and empty-result reconciliation), overall cap/contract decisions, and standing launch/finalization/capture gaps. Those are neither re-tested nor implicitly cleared here. No owner/shared files were changed, no new experiment was launched, and no paper or package integration occurred.
