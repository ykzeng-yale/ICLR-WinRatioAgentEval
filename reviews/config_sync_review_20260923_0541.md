# Independent configuration and protocol-pin closure — September 23, 05:41 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective collection/acceptance 10 (Session60/root), final expanded release QA 5 (root), and author checks 10 (Yukang). Configuration consistency closes an implementation finding; it earns no study or release milestone points.

## Scope and disposition

Accept the configuration synchronization and deterministic test-failure localization delivered at [2fd331201b8772d23c7e0f1e59c33ede2ab4a5f0](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/2fd331201b8772d23c7e0f1e59c33ede2ab4a5f0), with the successor commit-reference correction at reviewed head [337ab26d91513389b0f54f2c8db822d94073ac7c](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/337ab26d91513389b0f54f2c8db822d94073ac7c). Comparison base is root `8322f16f3a6d7670a9123d310cd5bf55d1b4ff83`. This follows the two finite configuration/provenance items in [the 05:02 disposition](lock_delta_disposition_20260923_0502.md); production lock routing remains separately assigned.

**Eight focused tests pass:** ConfigTests.test_config_is_appendix_b_verbatim; ConfigTests.test_rule_block_hash_is_stable_under_operational_pinning; and all six PinSuccessorAmendmentTests. The latter invoke the real pin checker and specifically assert vocabulary-alignment acceptance/refusal for the correct current successor, wrong successor, stale successor, mutated original pin, retained original pin and preserved successor history. This is not a claim that the complete 190-test suite was independently repeated.

One additional historical control ran the same verbatim test using the three immutable file blobs at the comparison base, substituted in memory without modifying the checkout. It gives **one expected AssertionError, zero execution errors**, proving the specific deterministic mismatch on those bytes. No full suite, model, simulation grid, native runtime, lock acquisition or trial was executed. [Machine-readable checks, exact hashes and test output](evidence/config_sync_review_20260923_0541.json).

## Exact-byte and scientific-rule checks

The current config.json, extracted ARCHITECTURE_FINAL §6.1 JSON block and protocol_FINAL Appendix B JSON block each contain **12,177 bytes** and have the identical SHA-256:

`8df49cf0dd69cdd21381700b247635ffcdcea27767cc02948ea52a2189b6c430`.

Both raw-byte equality and parsed-object equality hold. Config semantics have **no changes relative to 8322f16**: the owner-host path and its note were already present in that config, while the two embedded blocks had not received them. Relative to `cba87963d6d839cdeaf93ebad0f025c42213b794`, before the host-pin addition, the restored config differs by exactly **two added lines, zero deleted lines**. Removing those two host_work_root/note lines reproduces the earlier config bytes exactly. Thus the broad formatting rewrite is reversed while retaining the authorized host-path addition.

At the previous reviewed state, config SHA was `ee2a404f5b07cdbd6905e09c58f39ad99af169681406b86d50fde1f204d7b378`; both document blocks still had SHA `b41b588f632a90e6d68ba972089bc5031d4814d38ac5281a54024fe42be7df5f`. Those document blocks matched the pre-host-pin config exactly. This accounts for the deterministic test failure: the two documents agreed with one another, but neither agreed with config.json. No intermittent worker, runtime or lock failure is needed to explain this test's failure. The owner-reported three historical retries are not independently claimed here; one immutable-byte reproduction suffices.

The statistical rule-block digest is identical before and after:

`cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607`.

This agrees with full parsed-config equality across the reviewed delta. There is no changed margin, error allocation, trial contrast, horizon rule, estimand or collection rule in this configuration repair. The two-line protocol/document additions describe the selected execution-lock host path, not new scientific results.

## Additive protocol successor mapping

The exact original CPU vocabulary-alignment pin remains:

`3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2`.

The new current successor is:

`0e1bcb710ce2c13a06a243a7c3034d6bec55389d4de45dce569a7dee15af0284`.

Independent hashing confirms that this is the complete current protocol_FINAL.md, including its two new Appendix B configuration lines. The earlier enclosure successor `b1ff97cc163ce7ea121ebd578a4c37de09d5ed7223f2029e5d56118cdc790822` remains unchanged as the first prior-successor entry. The previous Appendix B successor `d63717a5519f650394db8aca7eb33d7a15ccfedbaffe78600d9ea3fb7b76294d`, its source commits, reason, timestamp and ruling are retained as the second entry. The earlier correction explaining why the enclosure transition was not merely an editorial line is also preserved.

After removing only the superseded_by object from each old/new cells.json object, the remaining objects compare equal. Thus every CPU cell, seed, parameter and other provenance field is unchanged. The added tests explicitly preserve both prior successors and retain the wrong/stale/original-pin mutation refusals.

The first repair commit contained the obsolete self-reference `2665c36f35f576442bafcfb0b49583720f2f0a3f`. The final reviewed delivery correctly points changing_commit_of_this_successor to **2fd331201b8772d23c7e0f1e59c33ede2ab4a5f0**, a resolvable ancestor whose protocol bytes independently hash to the declared new successor. The correction is recorded in a later commit and explicitly explained. Accept the final reference; do not cite the obsolete intermediate value as the protocol source.

This administrative mapping records what happened after the original freeze. It does not replace the original pin, re-register the completed CPU panel, claim the original panel covered this later live implementation, or alter the separately retained enclosure-scope restriction.

## Remaining boundary

No new defect was found in this bounded final configuration/pin delta. These two items can close without repeating their accepted tests. Matching documents are still a preparation configuration, not an approved completed freeze: required null-valued preparation pins remain explicitly listed in the evidence JSON. The already identified production lock-binding repair, anchor work and other finite preparation obligations remain under the current root handoff; this review does not re-test or approve those paths.

Owner status supplied for this cycle is **September 23, 05:30:23 UTC: live 0, calibration 0, 14/26 preparation components, nothing running**. That is an owner report, not a new local process observation. No new experimental outcome is accepted, integrated or packaged by this review. The existing arXiv package and historical ICLR release are unchanged. Root should close the configuration/test-localization findings and keep the next owner action focused on the already assigned production binding.
