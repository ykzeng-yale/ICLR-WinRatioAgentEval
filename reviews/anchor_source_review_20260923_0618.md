# Independent anchor source review — September 23, 06:18 cycle

**Full-project readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective collection/acceptance 10 (Session60/root), final expanded release QA 5 (root), author checks 10 (Yukang). This is a bounded implementation check, not a study result.

Reviewed source [8ec53277641a1949052a5210ab03f505baadaecc](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/8ec53277641a1949052a5210ab03f505baadaecc), delivered unchanged in `9db77f5ae6ce1cfe27ac75caece2d025b5d44359`, against `79e5827`. Scope: lab_anchor.py, production_anchor_transaction.py and the four new immutable offline/reconciliation/mock/real receipts. The [03:48 anchor handoff](lock_anchor_review_20260923_0348.md) supplies the acceptance criteria. Exact source/receipt hashes and check results are in [the evidence JSON](evidence/anchor_source_review_20260923_0618.json).

## Accepted repairs

**Five focused checks pass**, without a real POST, push, commit, drill rerun, model or broad suite: one intercepted source-path check, one bare-base refusal, public-path acceptance, ignored-path refusal, and one retained-receipt reconstruction. Their accepted findings are:

- Drove the real transaction constructor, serve, _handle, commit_and_push, post_comment and private/spool persistence in temporary files. All 14 subprocess calls on that path were intercepted; requests.post was patched directly, and the underlying requests transport was separately disabled. A synthetic HTTP201 response produced one successful receipt in each private/spool file; the files were byte-identical and the response digest was independently correct. The name-resolution exception is closed by importing sha256_bytes.
- The configured/default endpoint composed exactly `https://api.github.com/repos/ykzeng-yale/ICLR-WinRatioAgentEval/issues/13/comments`. The previous bare API base raises before any attempted POST. The configured repository URL defect is closed.
- The constructor reads the source GitHub origin, sets that origin explicitly on the isolated clone and reads it back before proceeding. The intercepted execution verified that ordering and identity. This closes the prior accidental local-clone destination; it does not independently observe a remote push.
- Read-only git checks accepted the prescribed public drill path and rejected its former ignored work/ location. The intercepted actual commit path staged exactly one relative path, `results/live_ab/anchor_drills/<run_id>/anchors/anchor_1.json`, with explicit `git add --`. Synthetic segments, requests, private receipt and spool remained in the temporary work directory. No private payload was staged.
- Reconstructed the deterministic synthetic segment and reconciled the deposited real and mock receipts. The segment is **996 bytes**, SHA-256 `704fb68465052633dd0b826d838c8038fa54fe5c30e9fb772ab4399509ada512`, final hash `740d4bd0bd888800bcd52e0f316c732d93327fef4703486fa3719a744b7ed20e`. The public anchor is **301 bytes**, SHA-256 `ca71eddf2c8b74d4d8d6255f6ab1ce6917762346e1005dccce7b5069fdcd3b5d`. All agree with the deposited objects. The real receipt contains exactly one equal private/spooled object.

The count is five bounded acceptance checks, not five full test classes. The endpoint success, remote-configuration and persistence assertions were exercised together in the intercepted real-mode source path; public accepted/ignored refused are two separately observed path outcomes.

## Receipt scope and one labeling correction

The saved real receipt was generated **06:15:37 UTC** and reports comment creation **06:15:41 UTC**, comment **5790044051**, commit **deadd9648ef1f0d1396620afab13254b4c303659**, one request handled, one successful private/spooled receipt, and no error. Root separately checks the remote comment, commit, parent and payload. This subreview independently establishes source behavior and deposited-object consistency; the original ignored private files and raw HTTP response are not separately retrieved here.

The preceding reconciliation receipt records the pre-transaction absence of a production-anchor comment/branch and the 20 earlier timing-drill comments. That is retained owner evidence about its reported observation time, not a claim that the branch is still absent after the successful transaction. The real transaction has spent the one authorized attempt. No repeat is requested.

The helper named `mocked_success_reaches_persistence` actually calls only post_comment; its name/docstring overstates its scope. Its returned what_this_shows correctly limits the result to the HTTP201 branch. The independent intercepted serve-path check above supplies the missing source-level persistence check. Similarly, the saved mode=mock transaction has no private receipt, commit or comment even though its generic exercises list names those functions. Narrow those descriptions on the next ordinary source edit; preserve the original receipts. This labeling repair does not invalidate or require repeating the completed real transaction.

The script still does not automatically select a preexisting remote drill-branch tip or record the execution source/parent itself. That is a reuse limitation, not a defect in the already reconciled first-branch transaction. Its branch was reported absent beforehand; root separately reconciles the actual parent. Do not infer permission to reuse the script or run another drill.

## Disposition

Close the named wrong-origin, wrong-API, missing-hash-import and ignored-public-path findings for this delivered source and its bounded transaction scope. Accept the private/spool success-path implementation. No new prospective freeze or scientific claim follows: the data are synthetic, no trial outcome exists, and the separate 20-post timing study was not repeated.

Owner status **06:16:56 UTC** remains trial 0, calibration 0, 14/26 preparation components, nothing running; this is a timestamped owner report, not a new local process observation. Continue the existing remaining preparation handoff. Accepted CPU evidence and the current arXiv/historical ICLR artifacts are unchanged; no readiness credit is awarded.
