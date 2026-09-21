# Independent live-roster defect review — 2026-09-21 18:54 UTC

Reviewed the exact owner report `results/live_ab/FREEZE_PATH_DEFECTS_20260921_1840.json` and implementation at live commit `22f3fbc`, against root guidance at main `b081ed4`. This was a bounded source review: no reference sweep, model call, server action, dataset download, or trial execution. The report records that no roster/order/freeze bundle has been deposited. There is no existing freeze to revoke.

## Disposition and finite repair order

Repair the production enrollment verifier and timeout classification, make source reuse idempotent, apply the literal S1 duplicate rule, and make the intended source mode explicit in the deposit driver. Preserve raw observations and refresh the changed preparation-source pins. These are bounded prefreeze implementation repairs, not a request for another scientific redesign or permission round. The existing serving/load restriction remains separate; none of these offline repairs authorizes the rule-4 loaded sweep or trial execution.

### D1 — distinguish frozen artifact verification from fresh sweep reproducibility

The mechanism is real but the severity claim is overstated. `lab_data.py:558-569` hashes stdout-tail/stderr details into exclusion records; `:629-664` includes those records in the roster hash. `local_stream/verify.py:78` creates a fresh success sentinel; `sandbox.py:154-155` uses a fresh temporary program path, which may appear in error output. Thus two sweeps with the same scientific pass/fail classification **can** produce different exclusion-detail and roster hashes.

This does not make a saved roster's hash unverifiable or permanently unreproducible: canonical hashing the preserved object reproduces the same identity exactly. It is a run-specific artifact hash. Nor must every excluded task carry random text: a timeout with no printed traceback may have stable detail, and deterministic blind exclusions already do. Timing-threshold classification can also differ across fresh runs even after text normalization, so promising identical fresh-sweep rosters would be scientifically unjustified.

Finite repair: explicitly distinguish a deterministic membership/exclusion-class identity from the run-evidence identity, or retain the existing run-specific identity with that contract clearly stated. If stable scientific identity is needed, derive it from task/source pins, ordered membership and exclusion uid/reason fields; retain raw stdout/stderr, per-attempt timing and their hashes in a separate immutable diagnostic ledger. Do not replace raw evidence with normalized-only text, delete attempts, or make the security sentinel deterministic. Do not feed the random diagnostic ledger hash back into the supposedly stable identity and then claim fresh-run equality. Test the declared identity contract with two artificial diagnostic strings; no live sweep is needed for that test.

### D2 — confirmed production-schema enrollment gap

`lab_design.py:137-155` writes dictionary documents containing `pairs`. `lab_verify_log.py:410-424` compares expected uid/arrival/stratum only if the loaded order is a bare list. Production dictionary orders therefore skip those comparisons. The unconditional `ok` at `:429` can report successful order verification despite their absence. A sequential pair-number check at `:425-428` still executes, so the report's statement that it checks nothing at all is too broad; the material gap is the frozen-pair content/order comparison.

Repair by extracting and validating `pairs` from the recognized document schema, retaining legacy list handling only if deliberately supported, and failing closed for malformed/unknown shapes. Verify the observed enrollment prefix against the frozen order, including pair number, task uids, arrivals and stratum. Do not require enrollment of the entire roster after a legitimate early stop. Add one production-dictionary positive fixture and planted uid/arrival/stratum mismatch refusals. This is the highest-priority actual verifier repair.

### D3 — confirmed timeout-reason misclassification

`verify.py:82-83` exposes `timed_out`, and `sandbox.py:196` marks a wall timeout unsuccessful. In `lab_data.py:562-567`, unsuccessful returns are classified as `reference_fails_verify` before elapsed-time evaluation. Real wall timeouts therefore take the failure label. Slow failed returns likewise never reach the elapsed-time reason. The 2.5-second threshold is explicit protocol arithmetic, distinct from the current 10-second execution cap; do not silently harmonize these values by changing the threshold.

Repair using an explicit timeout/threshold predicate before assigning the primary verification-failure reason, while retaining both raw component flags and actual duration in the attempt ledger. Preserve every attempted verification and the existing stop-on-first-exclusion behavior; no extra run is needed merely to label an already-excluded task. Stub outcomes covering a hang, slow success, slow failure, and quick failure suffice to test precedence. The failure report's exact upper-window wording is too strong because measured wall duration is not guaranteed to be bounded sharply by the nominal process timeout.

### D4 — source-mode visibility and durable availability, not a universal EXT requirement

The implementation does omit unavailable optional `mbpp_full` and then yields S1 mode (`lab_data.py:271-277`, `:323-332`, `:641-649`). However, protocol_FINAL.md **explicitly permits** S1 fallback at `:590` and `:620-622`, and explicitly keeps raw third-party data outside git at `:594-596`. Absence from git is therefore not itself a protocol defect. The source already has a pinned URL/revision/hash/size at `lab_data.py:128-138`; the defect report should not imply no provenance pin exists.

For the current EXT preparation intent, record `expected_mode=EXT` in the deposit driver and reject a preparation whose resolved mode differs, with the missing-source reason shown. Verify the present bytes against the existing pins and retain them in a durable external cache/artifact location with a retrievable provenance record. Do not demand that the raw dataset be committed to this repository, and do not globally change `check_roster` to prohibit all S1 rosters: that would contradict the retained protocol. A source-presence expectation is also distinct from requiring positive post-sweep S2 survivors; legitimate prospective exclusions must remain visible rather than being overridden to satisfy a minimum stratum count.

This review did not inspect the remote cache, so the two reported file locations/availability are owner observations, not independently verified remote facts.

### D5 — confirmed manifest idempotence issue; preserve first provenance

The first call can discover a cache path, copy to the destination and write that original `origin`; the second searches the destination first (`:229-239`, `:265-302`) and attempts different manifest bytes. The existing write-once rule properly refuses that change. Reading an existing manifest is a reasonable resolution, provided its source identities and actual local file hashes are verified rather than blindly trusting its presence. Keep the original origin as historical acquisition provenance; record a later local path as a new use/availability receipt if necessary. A repeat call with the same verified bytes should return the existing manifest, and mismatched/missing required bytes should refuse explicitly. No prior artifact needs deletion or rewriting.

### D6 — confirmed mismatch with the duplicate rule

Protocol rule 2 refers to all S1 tasks (`protocol_FINAL.md:608-609`), but `lab_data.py:467-469` includes only the MBPP subset of S1. Include every S1 normalized prompt in the duplicate map. A synthetic HumanEval/S2 duplicate tests the previously omitted branch without any reference execution. The owner's statement that the correction adds zero exclusions on these data is a delivered finding, not independently recomputed in this source-only pass; retain its evidence link or have the ordinary deterministic stage-1 rebuild confirm it.

### D7 — strengthen the right oracle, without fixing the future roster to a pre-sweep count

The tests do contain exact real-data pre-exclusion and smoke-only counts (`tests_lab_design.py:474-479`, `:1334-1354`); “no test pins any real roster value” is too broad. The genuine gap is that post-blind deterministic membership is checked only loosely and production-schema/run-evidence integration is insufficiently exercised. The stage-1 counts 1,138 candidates, eight blind exclusions, 1,130 survivors and a 564-pair ceiling can be pinned together with source identity and the exact deterministic exclusion list. A total alone is not a membership oracle.

Do not assert 564 as the final rule-4 horizon: loaded reference checks have not run and can exclude further tasks from either stratum. Final deposition should derive and reconcile the actual survivor/exclusion ledger, content hashes, parity leftovers, stratum-specific floor counts, and arrival-order length under the unchanged formulas. The verifier fixtures above cover the concrete new defects; no broad rerun or generic expansion is needed.

## Handoff summary

Proceed with the finite offline repairs and their targeted deterministic fixtures, preserve raw receipts, commit the changed source and recompute preparation pins. Keep stage-1 artifacts explicitly provisional and derive the final roster only after the separately authorized, capacity-compliant rule-4 execution. The absence of a freeze means no unfreeze or write-once overwrite is warranted. Root retains final scientific and execution decisions; this source review supplies no model-execution authorization and no readiness credit.
