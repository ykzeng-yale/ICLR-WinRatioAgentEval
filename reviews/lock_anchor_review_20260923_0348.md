# Host-wide execution lock and production anchor review — 2026-09-23

Reviewed exact delivery: `334f12109babc6d35d0bf9dae0298c60d1c1dbad`.
Independent scope: path topology, shared-inode exclusion contract, and the named production anchor blockers. Read-only production inspection plus bounded offline witnesses; no model, sandbox program, actual lock acquisition, remote call, repository mutation, or transaction executed.

## Decision and accepted subset

The lock defect is real and should be repaired, not skipped: the reference sweep and four trial workers resolve five lock files. Both workers inside one trial do share their trial lock; the existing containment fixture therefore remains evidence for the file it tested, not host-wide exclusion across every production path. Two different Python wrappers are not inherently a problem when they hold the same physical file with `flock` for the whole creation/execution/deletion interval.

Use the existing owner-host physical work location as the canonical lock:

`/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/work/live_ab/sandbox.lock`

This path comes from `results/live_ab/LOCK_TOPOLOGY_v2.json`; it is a recommendation for that owner host, not an assertion that this root checkout can execute there. All cooperating execution paths on that host must bind to this same resolved file: `lab_common.trial_paths`, `lab_orchestrator._trial_paths`, worker job path and fallback, `lab_data.sweep_references`, and both containment entry points. A relative `work/live_ab/sandbox.lock` in each clone would still create one lock per clone and would not satisfy the contract.

Production trial anchors already have the correct public location: `results/live_ab/<trial>/anchors/anchor_<seq>.json`, in both `lab_common.trial_paths` and `lab_orchestrator._trial_paths`. Retain those paths. The ignored-path problem is the special `production_anchor_transaction` constructor, which overrides `anchors` under `work/`. Its exact public drill path should be:

`<drill-clone>/results/live_ab/anchor_drills/<run_id>/anchors/anchor_1.json`

Keep synthetic segment bytes, private receipts, spool, requests and logs under ignored `work/`. No `git add -f`, blanket exception for `work/`, or private receipt publication is required.

## Focused evidence

1. Ran `python3 -m unittest experiments.live_ab.tests_lab_isolation.ExecutionLockConformanceTests -v`: **3 tests, 2 passes, 1 failure**, in approximately 0.5 seconds. The failing assertion independently resolves **5 != 1** files; intra-trial sharing and the presence of two wrappers pass. No sandbox or lock is opened by these tests.
2. An offline token round-trip shows why fixing only the trial suffix is insufficient across worktrees. With canonical work `/tmp/owner-main/work/live_ab`, serialization yields `<WORK>/sandbox.lock`; resolving that token in a second checkout with work `/tmp/owner-other/work/live_ab` yields a different physical pathname. Use one frozen host-root resolver/token (for example `<HOST_WORK>`) consistently in serialization and resolution, or otherwise preserve the exact canonical path in private runtime state. Do not allow ordinary checkout-local `<WORK>` resolution to remap the host lock.
3. `git check-ignore -v` confirms `work/_production_anchor/SYNTHETIC/anchors/anchor_1.json` matches `.gitignore:26:work/`; the recommended `results/live_ab/anchor_drills/SYNTHETIC/anchors/anchor_1.json` is not ignored.
4. Direct source inspection confirms all T1–T4 production anchor paths are already in `results/live_ab/<trial>/anchors`. The pending decision note's broader wording that “the harness puts anchors under work” is too broad; the special drill constructor is the affected code.

## Finite anchor repairs required before the authorized transaction

The public-path repair alone is insufficient. These are concrete defects in the inspected path, not new study design requirements:

- **Wrong push destination.** `production_anchor_transaction.py:79` clones the local `REPO` with `--shared`. Its default `origin` is therefore the local source repository, while `lab_anchor.commit_and_push` runs `git push origin <branch>` (`lab_anchor.py:202`). The script never repoints that origin. Configure and verify the original GitHub remote explicitly in the isolated clone before the transaction. The current claim that the clone “pushes to the SAME remote” is unsupported by its implementation.
- **Wrong issue API base.** `production_anchor_transaction.py:131` supplies `https://api.github.com`, and `lab_anchor.post_comment` appends `/issues/13/comments`. A stubbed network call records the resulting URL as `https://api.github.com/issues/13/comments`. Supply `https://api.github.com/repos/ykzeng-yale/ICLR-WinRatioAgentEval` as the base, yielding the repository-specific issue13 endpoint. No real request was made by this review.
- **Success-response exception.** With a stubbed HTTP201 response, `lab_anchor.post_comment` raises `NameError: name 'sha256_bytes' is not defined` at line239. The function calls this name without importing or defining it. Qualify it as `lab_common.sha256_bytes` or import the function. Verify the successful response reaches the actual spool/private receipt path in an offline stub before any real posting. Because a real POST could succeed before this exception, any uncertain past or future posting must be reconciled against issue13 before retrying.

Start the fixed drill branch from its current remote tip if it exists, preserving previous drill history and using only a fast-forward push. If the remote branch does not exist, use the reviewed source base. Record both the execution code pin and branch parent. Maintain an isolated single writer, exact explicit file staging and a clean index. Do not silently reset, force push, or automatically repeat an uncertain transaction. No new PR is involved.

## Lock migration and completion evidence

The owner reports no active jobs, but that report is not a current migration lease. Before changing lock routing, check that no old worker/reference process is running or holds any old lock; do not interrupt an active valid job for a status snapshot. Update all launchers together and prevent old serialized job paths or an unconstrained `execution_lock_path` override from bypassing the canonical production path. Preserve old artifacts; rebuild only undispatched job payloads with their new exact configuration pins, or refuse stale jobs explicitly. Never unlink, replace, or “clean up” the canonical lock file while any process can hold/open it: `flock` protects the inode, and replacement can split the exclusion domain.

The next bounded owner evidence should show one canonical resolved path across T1–T4, sweep, containment and worker fallback **and across two different checkout work roots**, followed by a two-process lock-only positive/negative control using the actual wrapper paths. This needs no model or generated-program execution. Reject alternate paths before execution; isolated unit fixtures may inject their own temporary lock explicitly. The host-wide claim remains about cooperating validated entry points on the authorized host; legacy or unrelated launchers that bypass the lock must be excluded by the existing capacity/ownership checks.

This review closes the root design ambiguity and diagnoses implementation failures. It does not validate a prospective-study result, authorize trial episodes, change the scientific margin, or earn readiness credit. Full-project readiness remains **75% (change 0)**; bounded-v1 remains **90%**. Remaining: prospective study 10 points (Session60, root acceptance), final expanded package QA 5 (root), and author checks 10 (Yukang Zeng).
