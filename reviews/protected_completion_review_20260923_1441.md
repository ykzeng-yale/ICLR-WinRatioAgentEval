# Independent protected-path completion review — 2026-09-23 14:41

**Full-project arXiv readiness: 75%, change 0 points. Bounded-v1: 90%.** Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), expanded final QA 5 (root), and author checks 10 (Yukang). No scientific milestone is earned by this repair review.

Reviewed main [`358f04d3db830d13e0600c81ce22d67499b4cb69`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/358f04d3db830d13e0600c81ce22d67499b4cb69), source [`20aada0139683d7f9bce024d48331888aece7e45`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/20aada0139683d7f9bce024d48331888aece7e45). Scope is the changed protected-path behavior against the [14:03 witnesses](protected_path_review_20260923_1403.md), with one immediately adjacent construction failure and a valid control.

## Disposition

**Close the original drain-start, early-poll and drain-join receipt-loss witnesses.** Each now cleans up the mock child, returns 1, and retains one terminal receipt with an explicit failure verdict. Preserve these closures. The path is not fully accepted: drain **construction** failure still loses its terminal receipt, and the previously observed worker-start/join summary loss remains.

Seven bounded actual-main scenarios ran once. Process creation, HTTP, signals, monotonic time and thread scheduling were mocked; `_now` fields were synthetic and filename wall-clock formatting was unchanged. Real persistence, reader and finalizer operated only on closed synthetic temporary files. Launch verification was stubbed as separate scope. No real child, HTTP, network, signal, model, native build, pipe, full suite or wait ran. The already-open unfinished-worker case was not repeated.

Evidence: [`evidence/protected_completion_review_20260923_1441.json`](evidence/protected_completion_review_20260923_1441.json). Exact source SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `run_smoke.py` | `644aaeacabc3932d3fcf78761ec8fbf882f0cde3ec51b0d72816180cedb16a30` |
| `lab_common.py` | `aa32c13a0f3c6895f6a4d7936cc2b883930e5f4db9491a7f3aa444c8e1c3bb1c` |
| `lab_lifecycle.py` | `604556893fb5d381049756f765251bc45bd1f57ea632630d68fe2ee5610ac0b2` |

## Observed outcomes

All seven cases created one mock child and performed one stop signal and one successful reap. Six returned normally with one receipt; the construction case alone still escaped with no receipt.

| Case | Mock POSTs | Return / terminal receipts | Disposition |
| --- | ---: | --- | --- |
| Valid control | 2 | 0 / 1 | Positive control preserved. |
| Drain start raises | 0 | 1 / 1 | **Closed:** cleanup and explicit dispatch-failure refusal. |
| Early health-loop process poll raises | 0 | 1 / 1 | **Closed:** initialized results prevent the former secondary exception. |
| Drain join raises after reap | 2 | 1 / 1 | **Closed:** cleanup failure appears directly in refusal problems. |
| Drain construction raises | 0 | Exception / 0 | Secondary `None.is_alive()` failure still defeats finalization. |
| Second request-thread start raises | 1 | 1 / 1 | Cleanup and diagnosis retained; partial summaries still lost. |
| Request-thread join raises | 2 | 1 / 1 | Cleanup and diagnosis retained; partial summaries still lost. |

The dispatch-failure records retain type, message, stage and bounded tracebacks (588–667 characters in these fixtures, within the 4,000-character bound). The failure is now directly included in `supervisor_problems`. This closes the earlier reliance on incidental missing-field refusal reasons for these tested dispatch exceptions. No comprehensive exception guarantee follows from these finite outcomes.

## Remaining material issues

### 1. Drain construction leaves `drain_thread=None`, then cleanup dereferences it

The thread-construction fault is now caught and the child is reaped, which is progress. The guarded join correctly skips a missing drain. However, the next completion check remains unconditional:

```text
run_smoke.py:1210 — drain_finished = not drain_thread.is_alive()
```

Since construction never assigned a thread, actual main raises `AttributeError: 'NoneType' object has no attribute 'is_alive'` and writes no terminal receipt. The earlier runtime error is replaced by this secondary failure at the receipt boundary. The later `drain_thread_finished` expression does guard `None`, but it is never reached.

Handle missing, unstarted, running and completed drain states consistently before every completion/read check. Preserve the construction failure and mark capture unavailable/incomplete; absence of a writer object must not be turned into successful capture. Keep the already accepted no-read rule for an active writer.

### 2. Real worker-start/join failures still bypass summary reconciliation

The source still assigns `submitted_requests`, attempted counts, request rows and usage summary only after all thread starts/joins complete (`run_smoke.py:1137-1143`). A supervisor-level start/join exception jumps over those assignments.

The exact earlier witnesses remain decisive. With one successfully completed POST before second-worker start fails, and with two completed POSTs before join fails, actual main writes `submitted_requests=0`, omits request/attempt/expected-count summaries, and reports “token usage was not measurable for 0 request(s)” plus “2 request(s) were planned but never submitted.” The complete raw response artifacts exist, and the new `dispatch_failure` diagnosis is correctly retained and forces refusal; request accounting is still not reconciled.

The new owner test `test_partial_dispatch_still_reports_request_state` at `tests_supervisor_entry.py:842-858` supplies `bodies=[OK_BODY, RuntimeError(...)]`. Its fake POST raises inside the second worker, where `one()` catches the exception and appends a row. Thread start/join then finishes normally and the aggregate assignments run. **That is a transport-exception test, not the previously observed worker-start/join failure.** Its passing outcome cannot close those distinct paths.

Reconcile available per-request state and the full planned denominator after the protected dispatch block regardless of how it exits, retaining original rows/attempts and explicitly unresolved identities. Test the actual second-thread-start and join boundaries rather than renaming a POST exception as an exploded worker. No new live attempt or expanded fault sweep is needed.

## Next action and scope limits

Fix the missing-drain completion check and move request reconciliation onto the common failure/finalization path; keep the three scoped cleanup closures above closed. Root retains the overall acquisition-contract and dependency-design decisions. Manifest and response-shape/byte changes are other reviewers' scope and are not duplicated here. No owner/shared file was edited, no commit was made, and no scientific result, paper or package was integrated.
