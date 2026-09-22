# Lifecycle binding and seal review — September 22, 06:16 UTC

Exact snapshot `3f6cc56e4f889870920ea37e294a7b455f799fa7`, changes `99e18054edc59e3462c8b39db6ceb9c0701dd03c` and `479cd86eede41fd07521c036bee69597213e8796`. Reviewed immutable exports in outer `work/lifecycle0616`. Ran only four affected focused classes: 9 producer/consumer-contract, 7 reader-witness, 4 manifest-binding and 8 acquisition-seal tests: **28/28 passed**. Four additional bounded synthetic-file witnesses were executed; their exact input construction and output are retained in [the evidence file](evidence/lifecycle_seal_witnesses_20260922_0616.json). No native build, binary invocation, server, model, sandbox or full-suite run.

## Closed findings and accepted subset

The foreign-records plus matching foreign-manifest/local-observer hole is closed: manifest host/boot must now match independently supplied observer provenance; foreign and placeholder cases refuse. The existing observation-to-verifier check completes that link. This is not a reason to repeat earlier clock-domain tests.

The reader recognizes the delivered native `--help` seal schema; the saved 178-byte receipt's zero-record seal is the same case exercised by the focused test. Missing seal, a missing expected sequence value, two seals, a wrong seal token, positive write-failure count in the seal and an error record inserted into the main log refuse. Correctly sealed synthetic two-slot control still passes. These are real improvements; the native receipt establishes only the destructor seal path, not nonempty C++ slot-record interoperability or loaded lifecycle collection.

## Remaining concrete defects

| Bounded case | Actual result | Required finite correction |
|---|---|---|
| Two otherwise valid records shaped like the actual C++ producer: `run_token`/`instance_id` present, no host/boot fields | Both refused: `record host_id None does not match ...`; seal otherwise valid | Align the reader with root's approved trusted-launch echo contract. Validate echoed record and seal token against the persisted manifest, bind that manifest to measured observer/verifier provenance, and obtain host/boot from that bound manifest. Do not invent another host-digest implementation in C++. |
| Two distinct-slot records with sequences `[0,0]`, seal declares `records=1` | `lifecycle_complete=true`, coverage valid | Require unique sequence numbers and exact record-count/range agreement. Missing-values-only set subtraction permits duplicate sequence identities. |
| Sequences `[0,1]`, seal declares `records=1` | Complete and coverage valid | Reject extra/out-of-range sequence values too. The accepted multiset must be exactly one copy of every integer in `0..records-1`. |
| Valid two-record main log/seal, plus the actual separate `<log>.error` file containing `stage=seal_write`, `failures=1` | Complete, coverage valid, `writer_errors=[]` | Read and retain the producer's actual side channel before accepting the closed acquisition; any producer error refuses it. Recognizing this schema only when inserted into the main log does not consume the emitted error file. |

The first case is an immediate interoperability failure, not optional hardening: `window_from_record` still requires record-level host/boot, whereas the delivered emitter deliberately only echoes a supervisor token. Python fixtures contain fields absent from that producer. `instance_id` is checked, but the per-record `run_token` is currently ignored. One coherent token-to-manifest binding must be used end to end.

The sequence correction must **not** require file order to be sorted. The delivered producer obtains sequence numbers before its write mutex, so legitimate concurrent writes can arrive out of numeric order. Exact uniqueness/range/count is the existing completeness requirement; no new ordering contract is requested.

The sidecar defect is particularly relevant at final seal flush/close: the seal serializes the then-current failure count, and a later seal-write failure increments it only afterward. A readable seal declaring zero cannot supersede a subsequently written error. Source also uses `fflush(f) != 0 || fclose(f) != 0`, which skips close when flush fails; both operations should be attempted and checked. This is the same final-write failure accounting obligation already authorized, not a new experiment gate.

## Limits and disposition

The seal currently counts emitted release records. It does not itself prove every dispatched request completed: that link requires the already-planned supervisor manifest/request accounting. The snapshot still includes stale `pending_not_yet_validated` wording that sequence/seal are not emitted or validated, although partial validation now exists. Correct that label without upgrading it to complete validation until these specific gaps close.

Accept the foreign-manifest repair and the focused seal-parser/refusal improvements. Keep nonempty producer/reader interoperability, exact sequence accounting and sidecar/final-write handling pending. The owner-reported successful build and zero-record native fixture do not need repetition solely for this review. After these local contract repairs, root can proceed with its finite instrument smoke plan under the existing capacity rules; this report does not request a broad suite or another scientific simulation.

Only this report and its evidence file were written. Full-project readiness **75% (change 0)**; bounded-v1 **90%**. Prospective study acceptance, final expanded-release QA and author checks remain pending.
