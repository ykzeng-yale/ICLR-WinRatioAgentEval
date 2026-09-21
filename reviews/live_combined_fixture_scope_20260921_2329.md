# Root combined-fixture scope and schema closure — September21, 23:29 UTC

Full-project readiness70%, change0; bounded-v190%. Last seen main0e649ff/live1d1f342. Reviewed1d1f342; no model, sandbox or lock-fixture execution by root. See [independent schema closure](live_schema_closure_20260921_2329.md).

## Answer both owner questions without adding work

**No production caller is needed for the legacy audit option when there is no legacy artifact to consume.** Keeping that capability tested and explicitly labelled is sufficient. An optional historical audit helper differs from a required preparation/TMPDIR guard that must execute on the production path. Do not manufacture a consumer or another experiment to satisfy a superficial “has callers” rule. New preparation continues to require v2 records.

**For combined lock/sandbox evidence, follow the real execution topology: trusted supervisor acquires the lock OUTSIDE the sandbox and holds it throughout sandbox execution.** Do not ask sandboxed candidate code to open or acquire the supervisor lock itself. That would test a different architecture, could be denied by intended containment, and is not required.

Use two independent supervisor processes through the existing production lock-plus-sandbox route. The holder acquires the shared fixture lock and launches a bounded, synthetic sandbox program; establish a trusted readiness/timing record showing that this program is active before the contender tries. The contender tries the same lock through the same wrapper. Its expected blocked outcome means its sandbox program does NOT start during the holder's protected execution. This is the required exclusion demonstration, not a reason to insist both payloads run concurrently.

Use a fresh isolated fixture directory and an explicit configuration pointing both supervisors to the same lock file; retain path identity, monotonic acquire/release and sandbox start/end events. A bounded contender timeout is sufficient. If using the wait-then-enter variant, also record that the second sandbox starts only after the first releases. Preserve failure/timeout observations; no third contention pattern is requested. Existing lock-only negative-control evidence remains useful and need not be rerun just to change wording. Do not disable the real production lock or weaken the sandbox profile. No model/server is needed for this offline fixture.

This scope settles the choice: a holder genuinely inside sandbox execution plus a contender prevented from entering that same protected route is sufficient. The first code inside a sandbox need not know the lock exists. Label the result as a synthetic integration check of this path, not live model evidence or a general concurrency/security theorem.

## Scientific and execution boundaries

The intended version-directed validation is received: malformed v2 cannot fall back to legacy aliases, legacy use is explicit audit-only, unknown schemas refuse and explicit null uncertainty refuses. Preserve declared absent-value defaults. Independent execution of CoverageSchemaDomainMatrixTests passed10 methods with no skips, closing the named schema/domain findings. The owner reported11; correct that test count without rerunning. Do not keep expanding parsing cases absent a concrete remaining defect.

Owner still owes acquisition source-mode/integrity fixes, trial-worker startup TMPDIR enforcement, injected-decision rejection, anchor drill and the finite serving/load/rehearsal specification including an actual observer. These already-authorized tasks are the next critical path. Full-window arithmetic is not an actual observer and neither is a configuration declaration. No live/model clearance until the relevant finite plan and capacity prerequisites are met.

Latest owner23:20:11UTC: zero live episodes, nothing running, foreign servers present,11/26 structural inventory. T1112000/coarse80000/fine48000, ablation32000unique coordinates/64000evaluations unchanged. T1 independently accepted/integrated/packaged; qualified power/ablation accepted but awaiting root integration. No PDF/package or new scientific-outcome change this cycle.

Remaining30points: prospective10(Session60/root acceptance), expanded integration/finalQA10(root), author scientific/account/rights10(Yukang). Root retains the integration backlog; completing a parsing repair is not completion of that milestone. Next milestone: the combined route fixture and the already requested entry-point/finite-plan delivery.
