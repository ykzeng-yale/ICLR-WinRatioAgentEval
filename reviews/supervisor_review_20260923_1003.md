# Independent supervisor delta review — September 23, 10:03 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), author checks 10 (Yukang). No study result or readiness credit arises from this source repair.

Exact reviewed head `b3c4f4a4abe05f39ed8716ee91743c59201f2b87`; substantive [58ad9435fc1d08624b4bb859db83f68ba10c412e](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/58ad9435fc1d08624b4bb859db83f68ba10c412e). This bounded delta review repeats only the changed failed-reap/read gate, diagnostic error/completion/truncation disposition, and raw-byte preview-versus-real-decode route. Six calls to the actual `run_smoke.main()` used mocked HTTP, child process, signal, clock and thread interactions, while the real observer and write-once receipt sink operated on synthetic closed temporary files. No real child, network call, model, sandbox, native build or full suite was used.

## Accepted closures

**The unconfirmed-child no-read gate now works.** When both simulated waits time out, the actual main function makes **zero observer calls and zero lifecycle/sidecar raw-read calls**. It preserves the paths as unread/unresolved and writes exactly one receipt containing `child_confirmed_stopped=false`, `observation=null`, `acquisition_not_analyzed` and the supervisor problems. This closes the unsafe-read finding. It does not yet close the intended return-status path because of the post-write summary defect below.

**Drain errors and unfinished drainage no longer produce success.** The actual main cases with a throwing diagnostic iterator and with a still-alive drain each return **1**, with exactly one retained receipt and structured incomplete-capture fields. A positive ordinary diagnostic/control case returns zero with one receipt. The corresponding changed helper test passes.

**Characters removed from a retained diagnostic line are now counted.** A 900-character line with a 400-character preview produces `truncated_lines=1`, `dropped_chars=500`, and the actual main currently refuses with one receipt. The narrowly changed trimming test passes. This accepts accounting and its implemented conservative disposition; root separately decides when a bounded preview can coexist with independently retained complete raw output. The unchanged line-based stream iteration still receives a complete line before truncating it, so this does not establish a strict peak-memory bound for arbitrarily long lines.

**The new raw-byte helper safely handles invalid UTF-8 in isolation.** For bytes `ff 0a`, `_retain_bytes` records two bytes, a matching full SHA-256 (`e4688624e5f1ad0629505e6768e3bb36244f2f3e33e751215afa820334a76ed3`), `decodes_as_utf8=false`, the decode error and a labeled replacement-character preview. This accepts helper behavior only; actual main still reaches the reader before this helper, as already acknowledged by the owner.

## Actual-main delta table

| Case | Result | Receipts | Key observation |
| --- | --- | --- | --- |
| Ordinary positive control | returns 0 | 1 | Reads occur only after confirmed stop |
| Both reaps fail | post-write `KeyError: raw_log_bytes` | 1 | **No observer or raw-file read**; unresolved receipt retained |
| Drain exception | returns 1 | 1 | Structured incomplete diagnostic capture |
| Drain unfinished | returns 1 | 1 | Incomplete capture now affects disposition |
| Retained diagnostic line trimmed | returns 1 | 1 | 500 lost characters counted |
| Invalid UTF-8 lifecycle log | `UnicodeDecodeError` | 0 | Actual reader runs before safe raw-byte helper |

Two focused changed tests pass. [Independent evidence JSON](evidence/supervisor_review_20260923_1003.json) records all six actual-main cases plus the helper's byte/hash check.

## Small remaining correction and standing pending work

The failed-reap receipt is durable, but the console-summary code after that write still indexes `out['raw_log_bytes']`, which is correctly absent on the no-read branch. It raises `KeyError`; the next `obs.get(...)` would also be invalid because `obs` is deliberately `None`. Make the summary use only present fields/nullable observation, then return the already-computed failure status. Do **not** create a fictitious zero-byte measurement or reopen files merely to supply the summary. This is a small integration follow-through; the no-read closure above remains accepted.

The invalid-UTF8 main-log case still exits before any receipt because `lab_lifecycle.observe` decodes first. This is the already acknowledged actual-main exception/finalization obligation; a safe helper located later does not close it. The owner also acknowledges remaining startup/finalization, one-absolute-deadline, pin/selected-artifact and request/raw-usage work. Those unchanged matters are not re-tested or reintroduced here. Root owns the complete raw-output versus preview policy and the consolidated remaining supervisor contract.

Accept the new no-read gate, diagnostic error/incompletion refusal, corrected truncation accounting and safe raw helper within their demonstrated scopes. Keep failed-reap return-status handling and the known actual-route finalization unfinished. No additional loaded smoke is requested. Session60 owns implementation; root owns acceptance and the next prospective preparation/freeze milestone. Owner files, shared trackers, paper and release were not edited. Full readiness remains unchanged.
