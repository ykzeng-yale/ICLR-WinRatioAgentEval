# Pin successor amendment review — September 22, 2026, 04:59 cycle

Reviewed owner amendment `690317e63ee9ad118db1178e0139198843db6965` and index head `f9c1137` against root `reviews/protocol_pin_disposition_20260922_0422.md`. Bounded JSON/source/document comparison and six focused pin tests only. No full190-test suite, simulations, models, owner edits or repeated raw/log duplicate checks.

**Disposition: accept the administrative successor mapping; one small test-entrypoint/count repair remains.** This neither changes the scientific study nor grants live execution clearance. Full readiness75% unchanged; bounded-v1 90%. Remaining25: prospective study10(Session60/root), final expanded release QA5(root), author checks10(Yukang).

## Closed: original identity and history are preserved

- Original `provenance.vocabulary_alignment.sha256` remains `3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2`.
- Current successor becomes `d63717a5519f650394db8aca7eb33d7a15ccfedbaffe78600d9ea3fb7b76294d`, with `supersedes` still bound to the original. It records04:45:38Z, both changing commits `869317f` and `7a17f06`, full current snapshot `7a17f064f3f15a1944e88803982e3847915c35ce`, Appendix B-only reason and the root ruling.
- `prior_successors[0]` is **exactly equal as a parsed JSON object** to the prior `superseded_by` object, including its substantive enclosure explanation and ruling60. The original-to-prior and prior-to-current transitions are correctly distinguished.
- Outside the replaced successor object, **all parsed `cells.json` fields are identical** to the parent. The large4,587-line diff is predominantly indentation; it does not change a scientific cell, law, seed, horizon or estimand.
- The separate dated amendment and appended `PROTOCOL.md` section preserve the original tested snapshot, deny new preregistration/current-live validation, and avoid modifying the pinned `protocol_FINAL.md` object. `vfixtures.py` is unchanged in this delivery.
- Six focused tests independently pass in0.015s: original identity retained; prior history preserved; correct successor passes; incorrect successor fails; mutation of original pin to current digest fails; stale previous successor fails. These exercise the real `check_pinned_file_hashes` on copies of the inputs.

The full current successor digest is deliberately absent from the protocol's64-hex-token set, so the existing original-pin document check still rejects replacing the original with the successor. This is the existing finite mechanism, not a claim of general tamper resistance across jointly modified files.

## Remaining finite repair: direct test invocation skips the six new tests

`experiments/live_ab_validation/tests_validation.py:2895–2896` executes `_run()` and raises `SystemExit` before `PinSuccessorAmendmentTests` is defined at line2899. Consequently the documented direct script invocation discovers **184**, not190 tests. Import-based unittest discovery does see the new class, and its six tests pass.

I reproduced discovery alone by replacing `unittest.TextTestRunner.run` with a mock that counts the suite and executes no tests, then loading the actual script through `runpy.run_path(..., run_name='__main__')`: **184 discovered**. This is an execution-order defect, not a failing scientific test or a reason to rerun the whole suite.

**Owner action:** move the existing `if __name__ == '__main__'` block to the end of the file, after all test classes. Verify discovery count without running190 tests, retain the six focused passing checks, and clarify the exact command associated with the claimed190 run. The amendment currently says184 while the commit/index say190; distinguish direct-script discovery from import-based discovery or correct the record additively. No unrelated full-suite rerun required.

A minor text-only mismatch: `PROTOCOL.md` says full successor digests are in both `cells.json` and the amendment document; the amendment table actually truncates them. `cells.json` contains the full identities, so no binding gap follows. Correct the sentence to point to `cells.json`, or put full exact identities in the separate amendment (not the token-scanned protocol).

## Earlier provenance/duplicate requests: no owner delivery yet

Read-only diff from `1155ca8` through `f9c1137` has **no changes** under the nine newly added `results/tau2_open/raw/` and `logs/` paths, or the historical coding/airline owner reports. No new owner historical-wincs source map was found in the incoming delta. The prior root review remains the adjudication; do not repeat the68,998,994-byte comparison.

Thus the already finite requests remain: preserve historical `601865…` receipts and link exact old source/verification timestamps; narrowly untrack the nine proven duplicate raw/log paths while retaining compressed evidence/history. These are provenance/storage follow-ups, not missing experiments. They do not require delaying the already prioritized lifecycle producer work. The twelve mock dry-run files remain separately labeled; this review does not authorize their removal.
