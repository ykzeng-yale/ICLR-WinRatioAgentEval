# Root decision: worker startup and bounded repair disposition

Full-project readiness **70% (change 0)**; bounded-v1 **90%**.

Reviewed delivery: `c88e231230e52f61edfb8197396a7b3b31b85ee2`; observed main `6197ec2`. Owner receipt: September22 00:50:00 UTC, issue11 comment5769686791. Independent review is in `live_nonce_integrity_review_20260922_0107.md`.

## Startup decision — BOTH

The supervisor must set and validate the child environment before launching workers. Each actual worker must use the shared prescribed-directory check at startup and after restart, before any model or sandbox dispatch. This also covers direct invocation. The worker's resolved directory is authoritative: an environment string alone does not establish Python's resolved/cached temporary directory. Do not change a running process's cache to force a pass. Use the same expected path/config and shared helper. Offline stubs should show invalid launch refusal and invalid direct/restarted worker refusal before dispatch; valid prescribed setup passes. This was already authorized, so proceed without another permission round.

## Fixture scope

The deposited v2 receipt records a successful synthetic two-supervisor lock/sandbox interaction: holder59864, contender59873, 2.031346209-second protected interval, bound nonce marker, contender blocked before sandbox start. It is not live evidence or a general concurrency/security theorem. The original receipt remains preserved. The literal-binding source fixes the diagnosed undefined NONCE. Required acquisition integrity no longer has the caller-visible bypass.

One narrow implementation correction remains: the preexisting-marker scan is currently after holder creation. Move it before Popen so a fast valid holder cannot be misclassified as preexisting. This is a false-negative race, not a reason to discard the saved successful zero-preexisting receipt or rerun it. A mocked ordering check suffices. Do not claim readiness on an unsuccessful handshake.

## Ranked next actions and ownership

1. Session60: implement BOTH startup checks, and the small scan-order repair together; deliver exact checked commit.
2. Session60: finish existing injected-decision production-refusal witness and anchor drill; deposit the finite serving/load/rehearsal specification including the actual continuous-load observer. Do not reopen closed schema/environment/acquisition findings or repeat completed suites solely for status.
3. Root: integrate accepted qualified power/ablation evidence with retrospective provenance and unsupported-mechanism limitations, then rebuild/inspect the release. This remains root's pending work and is not an owner blocker.

No live execution clearance: owner reports zero live episodes, no owned run active, foreign servers present, structural freeze inventory11/26. CPU totals unchanged: T1112000, coarse80000, fine48000, ablation32000unique coordinates/64000evaluations. T1 is accepted/integrated/packaged. Qualified coarse/fine/ablation evidence is accepted but not integrated or packaged. This review changes no manuscript, result or release artifact.

Remaining rubric points: prospective10(Session60/root acceptance), expanded integration/finalQA10(root), author checks10(Yukang). Repairs are not new study milestone credits.

## Late delivery received at 01:12:22 UTC

`6763346ec14e509d3760ed0db9c854fe0ce7761f` adds DERIVATION, PLANNING and RUN_BOOK. Read as an interim document delivery, not final freeze acceptance. Owner inventory rises11 to14/26; full readiness stays70%. New owner status: zero live episodes, nothing running, foreign servers present.

**License question: proceed.** Fetching the two public license texts from the exact model repositories/revisions is authorized prefreeze evidence collection. Save source URL, revision, retrieval time, exact bytes/hash and any access failure. No weights or model execution is involved; do not treat this as capacity-blocked or seek another permission. A deposited license is evidence for author review, not root attestation of distribution rights.

The new freeze-status snapshot still describes final roster construction as offline/no-quiescence and containment as not run, contradicting the loaded-sweep requirement and the existing bounded containment receipt. Refresh those status explanations from current evidence; do not rerun containment. Preserve the prior timestamped status snapshot (deleted in this delivery) as historical evidence instead of replacing history. The three documents remain an interim transcription pending complete source/formula review; their presence is not a scientific milestone. Continue the already authorized startup/fixture/finite-plan work in parallel with document corrections.
