# Root decision: wire existing production entry points

Full-project readiness70% (change0); bounded-v190%. Last seen maine49e6e4/live47b6a05; reviewed delivery47b6a05. Owner report September22 01:21:55 UTC, issue11 comment5769891678.

## Concrete implementation decision

Wire the checks now. The statement that the actual worker entry point does not exist is incorrect: `lab_orchestrator.World.spawn` calls Popen at lines1782–1795, and `lab_worker.main` loads the job and calls `run_job` at lines617–632. `World._make_job` already includes the sandbox config in each job; no new scientific job field or design change is necessary.

1. Supervisor: obtain the validated child environment before opening resources/creating the process and pass it explicitly as Popen(env=...). Use `self.cfg`. Existing spawn handles ordinary and resumed dispatch, so test that common path with Popen replaced by a stub.
2. Worker: check the actual resolved directory using the job sandbox block at the beginning of the common `run_job` path, before any lock, agent/verifier import or model dispatch. This covers CLI invocation, direct run_job invocation and a new process after restart. Preserve the existing pre-attempt versus job_accepted/worker_error accounting; a failed startup must be retained in logs and must not become a successful episode or an infinite automatic retry.
3. Keep the check dependency-light. Put the shared standard-library-only directory policy in `lab_common`, which both production modules already import, and delegate preparation helpers to it. Do not make workers import the whole preparation/data stack merely to check a directory. This is an authorized prefreeze implementation repair; update affected source pins after validation, without rewriting historical pins or weakening import isolation.
4. Test real entry paths with offline stubs: invalid launch makes zero Popen calls; valid launch passes the explicit child environment; invalid direct worker makes zero model/verifier calls; restarted worker repeats the same check. Helper-only tests do not establish these properties. Do not rerun models or the saved sandbox receipt.

This refines the previously authorized BOTH decision, not a new permission gate. Continue injected-decision rejection, anchor and finite actual-observer plan rather than waiting for another approval of this wiring.

## License answer was already posted

The explicit answer is in issue11 comment5769839241 at01:14:00UTC and the prior root report. Retrieve the two public exact-revision license texts now, retaining URL/revision/retrieval time/bytes/hash or access failure. No weights or models. Treat this as an already answered request, not silence. Depositing the texts does not replace the author's distribution-rights review.

## Evidence and unresolved failures

Helper and fixture delta independently reviewed in `live_startup_review_20260922_0144.md`. Independent narrow tests:7 pass and1 valid-launch setup error because the prescribed directory is absent on the review host; that method passes with directory-existence stubbed. Make the offline fixture self-contained. This observed portability issue is not proof of the cause of the owner's separately reported failure. Actual enforcement remains open until the production paths call the checks. The owner reports an ungated commit preceded by a failing suite followed by two passing runs. Preserve the failing output, command, environment and source revision if recoverable; otherwise mark them unavailable. Later passes do not explain the earlier failure. Do not repeatedly run unchanged full suites to manufacture certainty; use targeted reproduction if the failing test can be identified.

Owner status01:21:55UTC: live0, no owned run active, foreign servers present,14/26 structural inventory. CPU counts T1112000/coarse80000/fine48000/ablation32000unique64000evaluations unchanged. T1 accepted/integrated/packaged; qualified power/fine/ablation accepted but root integration remains pending. No new manuscript or release artifact this review.

Remaining30points: prospective10(Session60/root acceptance), expanded integration/finalQA10(root), author checks10(Yukang). Incomplete finite preparation and capacity still block execution; no live clearance.
