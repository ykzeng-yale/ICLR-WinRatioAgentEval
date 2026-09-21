# Live repair delta review — 2026-09-21 19:29 UTC

Reviewed exact live commit `19e93cce07f8f3b6ed46e6d4142f5aafa814b3c7` against `22f3fbc`; main context `f42f4a5`. Scope: D2 verifier wiring/tests, D1 retention, D3 timeout reasons and D6 duplicate rule. No reference sweep, models, serving action, or experimental rerun. One deterministic AST-isolated check of the exact `attempt_record` and `classify_attempt` functions was executed.

**Disposition: D2 implementation and D3/D6 logic are accepted at source level. D2's requested refusal test is not yet delivered. D1 has a concrete diagnostic-field error and provides a persistence callback, not an already-connected durable retention path.** Finish the specific checks below as ordinary authorized offline repairs; no new scientific design or permission loop is needed.

## D2: repaired production path, insufficient regression test

`lab_verify_log.py:195-230` extracts slots from dictionary documents, checks list shape and integer count consistency, and returns refusal for unsupported inputs. The real enrollment block now invokes it (`:460-487`) and compares pair, arrivals, uid list and stratum against every observed enrollment. A legitimate enrollment prefix is allowed. The original production-dict bypass is repaired in source.

However, `tests_lab_chain.py:2135-2166` does **not** execute the verifier or assert a refusal. The UID, stratum, order and arrival mutations merely assert that `_order_slots` returns different values. Those tests would still pass if the enrollment comparison were removed after parsing. Even the purported writer roundtrip tests hand-construct documents instead of invoking the production writer. The tests establish extraction, not production verifier behavior.

Minimal closure: take the existing valid deterministic chain fixture with a production-writer dictionary arrival order, call the actual `verify_trial`, and assert no `order.enrollment` finding. Then plant each named mismatch and assert an `order.enrollment` finding/refusal specifically, so an unrelated hash mismatch cannot be mistaken for proof that the enrollment comparison ran. Include the malformed/count mismatch case. Existing chain infrastructure already provides the needed path; no model or sandbox sweep is required.

## D1: exact remaining field bug and persistence boundary

The new detail construction is byte-compatible with the old `run{i}:stdout_tail|stderr` join; retaining those fields enables reconstruction of the digest. The optional callback is invoked for each attempted verification before classification (`lab_data.py:667-675`), including successful attempts. This is useful progress and preserves the intended early-stop semantics.

**Concrete defect:** `attempt_record` writes `sentinel_seen = bool(run.get('passed'))` at `lab_data.py:502`. The verifier's actual sentinel indicator is `result['sentinel_seen']`; a process can exit successfully without printing the sentinel. Independent deterministic witness using the exact function:

- Input: `success=False`, `sentinel_seen=False`, nested `run.passed=True`, `returncode=0`, no timeout.
- Output: retained `sentinel_seen=True`.

Thus the stored diagnostic falsely reports a sentinel for a missing-sentinel verification failure. Use the actual top-level flag; preserve process-pass and sentinel-pass as distinct fields if both are useful. The new test `tests_lab_design.py:1823-1827` checks only its own handcrafted `_rec` dictionary, never `attempt_record`, so it cannot detect this defect. Replace/extend it with the exact contrasting process-pass/sentinel-fail witness.

The record is described as “COMPLETE” but stores a projection, omitting such verifier fields as `entry_point_defined`, `sandbox_flag`, `hack_flags`, and nested execution/sandbox/profile metadata. Keep the actual verifier result as a nested immutable payload if complete per-attempt evidence is the declared contract, with the current digest-preimage view and typed summaries derived from it. Alternatively state the restricted retention contract precisely; do not claim a complete record when it is not preserved.

At this exact tree, no production caller supplies `on_attempt`; searches find its definition, callback invocation and test/signature discussion only. With the default `None`, successful and failed attempt records are still transient and only exclusions are returned. Therefore mark **retention API implemented, durable preparation-driver integration pending**. Connect the finite sweep/deposit driver to an append-only durable attempt sink before running it; exercise that path with a stub verifier, reload the saved attempts and reproduce each exclusion digest. A callback helper unit test alone is not evidence of persistence. This is an existing preservation obligation, not a new experiment gate.

The statement that old digests can now reconstruct is conditional: the old raw preimages must still exist. Byte-compatible code cannot recover observations already discarded. No prior live sweep is claimed here, so this does not invalidate an existing trial result.

## D3: accepted explicit precedence

The new classification is: actual timeout flag first, unsuccessful non-timeout verification second, otherwise elapsed threshold. AST-isolated checks produced:

| Input | Classification |
|---|---|
| timed out, unsuccessful, 10 s | reference_timeout |
| non-timeout failure, 0.1 s | reference_fails_verify |
| successful, 3 s | reference_timeout |
| successful, 0.1 s | no exclusion |
| non-timeout failure, 3 s | reference_fails_verify |

The last row follows the declared precedence and preserves the exclusion set; its elapsed time must remain available separately so reporting can distinguish timing-threshold exceedances from the mutually exclusive primary reason. The 2.5 s threshold and 10 s execution cap are unchanged. No demand to reorder these already explicit primary labels or rerun prior science is warranted.

## D6: accepted scope correction

`prospective_exclusions` now indexes every S1 normalized prompt, including HumanEval. The synthetic HumanEval/S2 duplicate test reaches the production duplicate function and asserts the correct excluded uid. This repairs the narrower-than-protocol implementation.

The stage-1 fixture is now tied to the known source identities and calls the actual loading/building/exclusion path. It records the stated 1,138 candidates, eight blind exclusions, 1,130 survivors and 564-pair ceiling. This source review does not rerun that unchanged dataset census or elevate the ceiling to a final loaded-sweep horizon.

## Finite handoff

1. Correct the sentinel flag and exercise the real record constructor.
2. Complete production-dictionary verifier refusal fixtures, checking the enrollment finding rather than mutation visibility alone.
3. Connect the existing attempt callback to the preparation driver's durable ledger and show a stub save/reload/digest reconstruction, retaining raw result fields under the stated contract.
4. Refresh changed source pins and synchronized interface documentation; preserve original records. No unfreeze is required because no freeze exists.

The added test classes occur after the files' `unittest.main()` blocks. Module discovery or explicit class loading includes them; direct script execution reaches `unittest.main()` before they are defined. Record a test invocation that actually discovers the new classes. This is a reporting/invocation point, not evidence that the owner's reported module-discovery runs failed.

Root separately reviews the prefreeze budget and throughput/median arithmetic. This review awards no readiness credit or model-execution authorization.
