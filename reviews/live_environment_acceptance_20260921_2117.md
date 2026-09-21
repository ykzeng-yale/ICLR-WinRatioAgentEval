# Environment acceptance and preparation handoff — September21, 21:17 UTC

Full-project readiness70%, change0; bounded-v190%. Last seen maincfcab48/live9202829. Independently checked the newly deposited bytes at9202829 and reviewed the c4ce4bb preparation delta. No model calls, serving changes, reference sweep or containment rerun by root.

## Environment question resolved

**Keep the promoted whole-environment digest and preserve both package-list representations.** Root independently read the622bytes of `environment_lock_preimage.json`: SHA256 is `842a7a19d738604fbe665231a593a11f12cc02abfe9b1dc4034bc3817a9081ac`, exactly the configuration value. Its parsed object equals the original preparation manifest's environment_lock object. Sorting the deposited83 name/version entries by `(Name, version)`, joining with newlines and NO trailing newline independently gives `08c1de5ae33d1fdd45424be7956c88471b8a8e47971608ac866aa6cb5247b053`, exactly that object's package component.

The existing case-insensitive-sorted, newline-terminated `environment_lock.txt` still validly hashes to40a9d196…; it is another representation of the same saved package multiset. This is a documented serialization difference, not evidence of altered installed packages. The whole object uses Python default JSON separators; retain and state this versioned legacy convention for this value. Do not rehash or amend three config copies solely for cosmetic canonicalization. Future fields should declare their serialization explicitly.

Owner action: add a separately named exact package-component preimage file using the now verified tuple ordering/no-terminal-newline convention, preserving existing `environment_lock.txt` unchanged. Add a tiny offline checker that verifies both component and whole hashes from the saved bytes, plus equality of their package multisets. The whole hash and package component are independently reproduced now; this last deposit makes reproduction convenient and explicit. No fresh host measurement needed. Acceptance proves saved-byte consistency, not installed-host identity, wheel/build provenance or that the current host remains unchanged.

## Preparation disposition

See [independent delta review](live_prepare_acceptance_20260921_2117.md). Raw-attempt-first retention and preparation TMPDIR calls are received; invalid-load observations now prevent a completed receipt. Retain the distinction between eventual refusal and **immediate stop**: the new sink accumulates invalid_coverage and returns, allowing more verifier attempts before the post-sweep refusal. Persist the raw attempt and observer failure/invalid observation, then raise from that sink so no next attempt starts. This was already required by the load-gap rule; do not run a whole invalid sweep to learn it is invalid.

The prior source-acquisition mode/integrity findings and missing trial-worker startup TMPDIR enforcement remain outstanding at this delivery; they were not changed by the new preparation-entry calls. Do not label the entire three-item repair list closed. Carry their existing exact witnesses forward without repeating unchanged tests. The owner is authorized to repair these entry points, the injected fixture rejection, anchor drill and finite pre-execution specification without another design-permission question.

## Containment and evidence boundary

Owner reports a two-worker probe PASS,15/15 protected-target operations denied,16 denials overall, and a negative control with15 breaches. Record it as a deposited probe result, not an independently executed live-worker episode or a general security proof. Root has not rerun the probe on the shared host. Independent source inspection finds one sandbox process under the lock, not a second worker attempting entry: an empty peer-directory glob does not establish two-worker exclusion. Accept only the deposited15 protected-target denials as a bounded owner result. Complete the already-required two-worker fixture with an actual contender blocked while the first holds the lock, and retain per-attempt negative-control evidence rather than a summary count alone. No trial-profile key is promoted from this probe summary.

Latest owner GitHub status21:17:16UTC: zero live episodes, nothing running, foreign servers present,11/26 freeze inventory. T1112000/coarse80000/fine48000, ablation32000unique coordinates/64000evaluations unchanged. T1 accepted/integrated/packaged; qualified power/ablation accepted but awaiting root integration. No paper/PDF/package change or readiness credit.

Next milestone: Session60 completes immediate-stop/entry-point repairs and the finite serving/load/rehearsal plan; root reviews exact execution/freeze receipts. Remaining30points: prospective10(Session60/root acceptance), expanded integration/finalQA10(root), author scientific/account/rights10(Yukang). This is progress on execution correctness, not new empirical support for the method.
