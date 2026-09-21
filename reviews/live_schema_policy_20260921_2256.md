# Root interval-version policy — September21, 22:56 UTC

Full-project70%, change0; bounded-v190%. Last seen mainb9d6707/live dbea39d. Reviewed exact dbea39d. No model, lock, sandbox, serving or simulation rerun by root.

## Resolve the compatibility question once

**Retain historical parsing; require explicit v2 validation for new preparation.** The owner's statement that certifying an old wider interval is a “looser contract” is incorrect: if the wider interval genuinely contains verification, proving activity throughout it is stricter. Do not delete or reinterpret legitimate legacy evidence merely because it used the conservative wider interval.

Use a declared interval-version branch, not a fallback after failed numeric conversion:

- New production preparation accepts only the named v2 verifier endpoints, with all required values finite/ordered and the five boundary meanings documented. Missing, null or invalid v2 verifier endpoints refuse; older aliases cannot rescue a malformed v2 record.
- An explicit historical audit route may read a genuine v1 record and certify its recorded wider interval. Its report must identify that interval/version; it cannot silently call it a v2 verifier interval. Preserve prior bytes. Do not add historical support as a live collection requirement or rerun old tests/experiments just to migrate them.
- The producer currently labels timing with `interval_schema=live_ab/attempt_interval-v2`. Make the consumer honor that discriminator; a mixed or unsupported version is a schema error. A missing version in a known archived v1 artifact may be handled only by the explicit legacy audit path, not automatic production inference.

This closes the choice; no additional permission is needed. Current code instead falls back whenever either new endpoint is nonfinite, so a corrupt new field plus valid old aliases can pass. Fix that exact branch. The issue is invalid-data substitution, not the mathematical conservatism of genuinely wider coverage.

For optional verifier endpoint_error_s: absence defaults to0 by the declared contract. Explicit values must be finite and nonnegative; explicit null is unknown and must refuse, not be treated as absent. Zero and positive finite values remain valid. The owner fixed the prior NaN/infinity/text cases; close those separately rather than calling the whole repair unchanged. A compact presence/version/domain matrix can close these remaining branches together.

## Accepted scope and retained work

The new producer records lock-request/acquired/released separately and captures the verifier boundaries inside the lock, as requested; no success margin, reference threshold or verify_seconds computation changed. Owner's0.624s wait/0.060s call receipt is an attributed stub result, not independent live execution. [Independent pure-function delta review](live_interval_v2_acceptance_20260921_2256.md) records exact accepted cases and remaining fallback witnesses.

The lock fixture label now correctly says two ordinary subprocesses using the production lock implementation on an isolated file. The saved measurement remains unchanged; its invocation/PID correction is documentation, not a new run. Combined worker/sandbox evidence remains pending at its actual scope. Previously requested acquisition, worker-startup, injected-decision rejection, anchor and finite serving/load/rehearsal work remains with Session60; no new experiment grid is requested.

Latest owner22:49:57UTC: zero live episodes, nothing running, foreign servers present,11/26 inventory. T1112000/coarse80000/fine48000, ablation32000unique coordinates/64000evaluations unchanged. T1 independently accepted/integrated/packaged; qualified power/ablation accepted but still awaiting root integration. No new scientific outcome, PDF or release change.

Next milestone: version-specific validation plus the already outstanding entry-point and finite execution plan. Remaining30points: prospective10(Session60/root acceptance), expanded integration/finalQA10(root), author scientific/account/rights10(Yukang). Root owns the integration backlog; preparation repairs do not earn those points. No model/trial clearance is issued here.
