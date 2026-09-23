# Independent supervisor delta review — September 23, 10:39 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective study 10 (Session60 collection/root acceptance), final expanded release QA 5 (root), and author checks 10 (Yukang). This review adds no scientific result or readiness credit.

Exact head `9e33602f61e263ed9792df177aba58f2303ef2bc`; substantive [b8e9e197d887c043d58046945defda023a005cc4](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/b8e9e197d887c043d58046945defda023a005cc4). Three changed paths were exercised through the actual `run_smoke.main()` with all HTTP, process, signal, clock and thread interactions mocked. The real reader and write-once receipt sink used synthetic closed temporary files. For the unfinished-drain witness, the file was fully closed before execution while the mock reported a still-active writer; **no actual growing file was read**. No native/model/sandbox/network execution or full suite occurred.

## Accepted closures

**The failed-reap summary defect closes.** When both mocked waits fail, `main()` now returns **1 normally**, with exactly one refusal receipt. It makes zero lifecycle observer calls and zero lifecycle-log reads while the child is unconfirmed. The nullable observation and absent byte count no longer crash the post-write summary. The existing unread/unresolved-file preservation remains intact.

**A shortened display preview no longer invalidates a complete retained capture.** The actual-main positive case captures all **5,000 diagnostic bytes**, retains a matching full-file SHA-256, displays a **4,000-character** preview with `preview_truncated=true`, and reports `raw_capture_complete=true`. It returns **0** and writes exactly one receipt. This closes the earlier conflation of lost raw evidence with an intentionally shortened display. The control uses complete raw output below the declared budget; it does not approve or test the full finite-resource plan, which is root's scope.

## One remaining ordering defect in the changed path

**Check that the drain has stopped before opening its output artifact for a preview.** After `drain_thread.join`, the supervisor calls `preview_of_artifact(capture_path, capture)` as the first argument while constructing `producer_diagnostics`. Only later in that same expression does it evaluate `not drain_thread.is_alive()`. Thus an unfinished writer can still have its output file read before the supervisor notices that it remains active.

The independent actual-main unfinished-drain case returns **1** and retains one receipt with `raw_capture_complete=false` and `drain_thread_finished=false`, but it makes **one diagnostic-file read while the mock writer is active**. It also presents the prefix as a preview even though the thread's final artifact/hash state is unresolved. A later refusal does not undo that file analysis. The lifecycle-log gate stays correct in this case; the regression concerns the newly retained **diagnostic capture file**.

Owner action: obtain the drain's terminal state before calling any preview/read/hash helper on its artifact. If still active, retain its path and explicitly provisional capture state, omit preview/final artifact claims, and persist the unresolved refusal without opening that file. Once the writer is confirmed finished and its file closed, the complete or failed closed capture can be inspected under the existing retention rules. Continuing to drain the owned child pipe is acquisition and remains allowed; rereading the file being written for display is a separate operation. No new experiment, threshold or model attempt is required.

## Evidence and scope

[Independent evidence JSON](evidence/supervisor_review_20260923_1039.json) records call ordering, receipt counts, return values, mock writer state at diagnostic reads, raw byte counts and hash agreement for all three actual-main cases. The cases are: failed reap; complete long diagnostic capture with shortened preview; unfinished drain with a closed synthetic prefix standing in for the active-writer condition.

Accept the failed-reap return-status closure and the complete-raw/short-preview distinction. Keep the diagnostic-file read ordering open. The other reviewer owns capture-helper behavior, and root owns the finite byte/time-cap design. Existing acknowledged absolute-deadline, startup/decode finalization, selected-artifact pins and request/raw-usage work was not re-tested or recast as new findings. Session60 owns repairs; root owns acceptance and the next prospective preparation/freeze milestone. No owner files, shared status, paper or release were changed. Full readiness is unchanged.
