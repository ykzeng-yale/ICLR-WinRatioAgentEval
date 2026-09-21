# Supervisor terminal closure: 2026-09-21 12:13

Reviewed owner head `00478fcc8c3b590f5931b5b4bbb21444248facce` in immutable export `work/v2_review_1213`. Scope: previous supervisor final-elapsed defect and parent terminal accounting shape. Root owns parent launch behavior and its reproduction. No scientific/native/model/grid calls, actual processes or signals were used. Prior closed RSS/enumeration/cleanup findings are not reopened.

## Closed: final supervisor elapsed

`vsupervise.py:310–314` checks the final recomputed elapsed time before acceptance, preserving any earlier breach. The exact prior whole-function fixture—terminal poll at 0.5 seconds, terminal elapsed 2 seconds, cap 1 second, successful child exit—now returns `within_caps=False` with a seconds breach detected at the terminal recheck. The previous acceptance counterexample is closed. No timing rerun is required.

The synthetic returned receipt includes top-level `started_perf=0` and `deadline_monotonic=1`, with no `started_perf` inside `observed`. This confirms the shape relevant to root's parent launcher finding.

## Parent accounting handoff

- `vlaunch.py:449–450` tests whether `started_perf` exists at the top level, then attempts to read `sup["observed"]["started_perf"]`. That does not match the actual supervisor receipt. Root is independently reproducing this launch-path error; it must be repaired before the production launch.
- `vlaunch.py:451–452` sums the directory **before** writing `T1_JOB_RECEIPT.json` at lines473–474. The field called `all_artifact_bytes` therefore excludes that final parent receipt for a fresh attempt. Likewise the elapsed sample precedes serialization and final writing, despite the nearby statement that the budget covers parent metadata writing. This is a concrete scope mismatch, not evidence that the measured workload breached a cap.
- The existing 256-KiB metadata reserve provides practical headroom for ordinary final receipts. No new resource measurement is warranted. For exact terminal accounting, include the serialized final receipt in the byte calculation/reserve reconciliation and ensure terminal acceptance checks elapsed time after finalization. Preserve a failure result if the common cap is exceeded; do not reset the deadline or present the pre-write sum as the final all-artifact total.

## Evidence and disposition

Isolated mocked receipt and concise findings are in `work/supervisor_closure_1213/terminal_wall/` and `work/supervisor_closure_1213/synthetic_findings.json`, outside the repository. Subprocess creation, process-group lookup and clock reads were replaced with fixtures. No experiment outputs were inspected.

Close the supervisor final-elapsed gate. Parent receipt-shape and finalization accounting are root's remaining launch-integration work. The accepted historical measurement and conditional T1 resource projection remain unchanged; source/fixture fixes suffice without scientific or timing reruns.
