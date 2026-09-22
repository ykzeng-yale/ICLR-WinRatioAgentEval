# Root nonce diagnosis and acquisition-test decision — September22, 00:34 UTC

Full-project70%, change0; bounded-v190%. Last seen maind21208f/livebddbdd3. Reviewed bddbdd3; no sandbox/model/process fixture or collection rerun by root.

## Concrete handshake failure, reproduced without a sandbox

The generated inner program is:

```python
import time
open('sandbox_active_TEST_NONCE', 'w').write(NONCE)
time.sleep(2.000000)
print('SANDBOX_DONE')
```

The supervisor interpolates NONCE into the filename, but emits its name literally in `.write(NONCE)`. The sandbox program has a separate global namespace and never defines that name. Root extracted only the source-construction function and its `prog` assignment via AST; executed the generated payload with an in-memory fake open, no filesystem writes: **NameError: name 'NONCE' is not defined**. The failure occurs before the sleep. This explains the missing marker; the printed filename being correct did not establish the separate write argument was bound.

Owner repair: construct the inner payload with the nonce as an explicitly quoted literal, e.g. a first statement `NONCE = <repr(nonce)>`, then use it for both marker filename and contents; or substitute separately quoted literals for both. Use repr/structured serialization rather than hand-escaping nested quotes. Add a small no-sandbox payload-construction witness with in-memory open and a no-sleep test stub so both marker path and content equal the intended nonce and the code has no unresolved free name. Then run only the already authorized bounded combined fixture with the original profile/lock contract and retain every attempt/error. Do not weaken containment. A success receipt is not expected until that fixture actually succeeds; unsuccessful repair attempts remain evidence too.

## Acquisition fixtures: no benchmark copies and no production bypass

Do NOT deposit860KB of actual benchmark bytes merely to test refusal. Use tiny synthetic files in a temporary test directory and patch the source specification/expected SHA256 values within the test to those fixture bytes. Call acquisition with verification enabled (the production default). Corrupt/remove one file or change the expected mode and assert the real common gate refuses. This tests the integrity branch as well as the mode branch and has no network dependency.

Remove the caller-visible integrity bypass from the production acquisition API, migrating affected synthetic fixtures to the test-scoped source pins. Alternatively isolate a test-only helper entirely outside the production invocation path; do not allow a normal production configuration/entry point to clear required-byte validation. The compact patched-pin approach is the recommended implementation; no real-source re-acquisition or rerun of the dataset census is requested.

See [independent acquisition delta](live_acquisition_closure_20260922_0034.md) for the default-enabled gate's exact accepted subset: five tiny-file calls pass the expected fresh/reuse controls and refuse explicitEXT+priorS1, corrupt required bytes and missing required bytes. The two original acquisition defects are closed under default validation. The acquisition expectation decision remains unchanged: explicitEXT and persistedEXT are binding; required sources must be intact in either mode. No further permission question is needed for this existing repair.

## State and next milestone

Latest owner00:18:35UTC: zero live episodes, nothing running, foreign servers present,11/26 inventory. The handshake repair is honestly reported as failing with no successful v2 receipt; root accepts that status rather than treating attempted code as a result. Prior combined-route acceptance remains limited by its marker-attribution caveat.

T1112000/coarse80000/fine48000, ablation32000unique coordinates/64000evaluations unchanged. T1 independently accepted/integrated/packaged; qualified power/ablation accepted but awaiting root integration. No new scientific outcome or PDF/package change.

Next: owner fixes the diagnosed payload and finishes acquisition-test migration, then trial-worker TMPDIR enforcement, injected-decision rejection, anchor and finite serving/load/rehearsal specification with an actual observer. Remaining30points: prospective10(Session60/root acceptance), expanded integration/finalQA10(root), author science/account/rights10(Yukang). Root retains integration responsibility. No model/trial clearance yet.
