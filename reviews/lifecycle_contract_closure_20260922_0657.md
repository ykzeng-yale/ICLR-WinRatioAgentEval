# Lifecycle reader contract delta — September 22, 06:57 UTC

Reviewed exact `31c22fd3df9d0d74593c727f55487490e0b7bc42`, received on main `f3061b68a7a0c1684b51411deb11f3406d131942`. Immutable export in outer `work/lifecycle0657`. Ran only `LifecycleReaderWitnessTests`, `SequenceMultisetAndSidecarTests` and `AcquisitionSealTests`: **19/19 passed**. Independently exercised the four prior witnesses plus two bounded token-binding cases. [Exact input construction and outputs](evidence/lifecycle_contract_witnesses_20260922_0657.json). No unchanged clock tests, full suites, native builds, models, server starts or real lifecycle collection.

## Four prior findings closed

| Prior 06:16 witness | Current independent result |
|---|---|
| Actual producer-shaped records, with token/instance and without host/boot fields | Valid two-slot sealed control certifies, observed concurrency 2. The reader no longer requires fields absent from the emitter. |
| Sequences `[0,0]`, count 1 | Refuses duplicate sequence. |
| Sequences `[0,1]`, count 1 | Refuses extra/out-of-range sequence. |
| Valid main log plus actual `<log>.error` terminal-write failure | Refuses the acquisition and retains the sidecar stage in the reported reason. |

The targeted multiset tests also establish refusal of boolean sequence/count values and negative counts, while accepting a valid out-of-order sequence multiset. No new sorted-file-order requirement is introduced. The existing manifest-to-observer check is preserved, so this does not re-open the closed foreign-manifest issue. C++ build/flush/receipt review is assigned separately and not claimed as independently executed here.

## Remaining finite binding defect

`window_from_record` selects `token = _typed_id(rec.get('run_token'), 'run_token') or inst` and compares only that selected value against the expected manifest. Two concrete consequences remain:

1. Delete `run_token` from otherwise valid current-format records. Both records still certify by falling back to `instance_id`. No explicit production schema authorizes this legacy substitution.
2. Keep the valid expected token on both records, but set both slot IDs to 0 and instance IDs to `other_instance_0` and `other_instance_1`. The record-token check passes; concurrency identity uses the unvalidated instance strings. Actual result: **complete=true, coverage valid=true, observed concurrency=2**, with identities `other_instance_0/slot0` and `other_instance_1/slot0`.

The second case makes the reader count two instances that the expected single launched instance does not identify. This is the same slot/instance acquisition contract, not a new adversarial framework or additional experiment requirement.

Minimal correction: require explicit, non-placeholder `run_token` and `instance_id`, and require **both** to match the expected launched instance/token (with the seal agreeing as already required). Remove the fallback for the current production schema. If historical tokenless records are retained, they remain non-certifying in this production path. Update the positive fixtures to include the actual emitted token rather than preserving a fallback solely to satisfy old hand-written fixtures.

## Disposition

Accept the four repaired paths and exact sequence/sidecar improvements. Hold complete token/instance-binding acceptance for the one finite correction above. Existing missing loaded evidence, launcher manifest preparation and request completion accounting remain the previously scoped implementation work, not new gates introduced here. A source fixture reproduces the actual emitted field shape but is not a loaded producer receipt.

Only this report and its evidence file were written. Full-project readiness **75% (change 0)**; bounded-v1 **90%**. Prospective study acceptance, final expanded-release QA and author checks remain pending.
