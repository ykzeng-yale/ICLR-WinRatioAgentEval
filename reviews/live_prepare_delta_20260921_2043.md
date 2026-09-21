# Independent preparation delta review — 2026-09-21 20:43 UTC

Reviewed `1c08896..1a32aa3` (main context `1c5a53e`), exported immutable source to outer `work/prepare2043/`. Ran only offline tests and injected deterministic driver witnesses. No task reference, sandbox process, model, server, or network execution.

**Accept the short-write repair and the new driver-to-ledger connection. Do not yet accept the driver's claimed TMPDIR/load enforcement or complete acquisition refusal policy.** The remaining failures below are directly reproduced, finite implementation corrections; no new scientific design, model test, or permission loop is needed.

## Closed findings

`python3 -m unittest tests_lab_design.PreparationWiringTests tests_lab_design.LedgerShortWriteTests tests_lab_design.SourceAcquisitionTests -v` ran **14 tests, all passing, no skips** in the exact export.

- `AttemptLedger.append` now loops over accepted bytes, raises on nonprogress, syncs before incrementing the count, and syncs the parent directory on first file creation. The injected positive-short-write test reloads a complete record; a zero-byte write raises with count zero.
- `load` rejects a malformed/incomplete tail, and `open_ledger` calls it before the preparation sweep. The prior silent continuation concern is closed for this entry point.
- `lab_prepare.run_reference_sweep` now passes its sink to the sweep's `on_attempt`; the sink appends real attempt records, and the driver reloads exclusions' preimages to verify their digests. The failure of a durable append propagates as preparation refusal. The prior “only wired in helper tests” finding is closed at this function boundary.
- Acquisition reuses an existing manifest without rewriting historical acquisition origin and records later accesses separately. Missing/drifted files in the previously established EXT path are refused. No raw dataset commit is required.

The delivered tests do not cover the following reachable paths.

## Residual 1: the TMPDIR assertion is never invoked

`assert_prescribed_tmpdir` exists at the end of `lab_prepare.py`, but a source search finds no caller anywhere in the reviewed harness. Neither acquisition nor `run_reference_sweep` invokes it. Independent driver witness patched this helper to raise if called, then invoked `run_reference_sweep` with a stub attempt and default `require_load=True`: the driver returned `completed=True` and the assertion call count was **zero**.

Call the assertion at the actual execution-preparation entry point before the first verifier attempt, retaining its receipt. Keep the offline-test escape explicit so ordinary stub tests need not modify the host TMPDIR. Root separately determines the trial-worker enforcement boundary and resolved path policy; this review does not change that design.

## Residual 2: observer presence is treated as valid load coverage

The driver checks only whether `load_observer` is supplied. It calls that observer in `sink` **after** the verifier returns, stores its result, and performs no validation of active status, clock, interval, or overlap. Two injected, otherwise valid one-attempt driver calls returned `completed=True` under default `require_load=True` with these observations:

- `{}`;
- `{'active': False}`.

A post-attempt activity sample alone is also insufficient evidence that the entire verifier interval fell under the required load. The current observation callable receives no explicit attempt start/end interval, and the retained record contains elapsed duration but not the same-clock endpoints needed for a direct overlap check. The docstring's “attempt about to run” description does not match its call location.

Use the root-approved load-window contract: capture the verifier attempt interval on the agreed clock and validate its required coverage against recorded active windows and resolution. Reject missing, malformed, inactive or insufficient coverage before calling the run roster-eligible. A check for callable presence cannot substitute for that evidence. Keep this a bounded interval/fixture repair; no new load-sampling campaign or per-attempt model call is requested here.

## Residual 3: observer failure loses the completed raw attempt

The sink calls `load_observer()` before `ledger.append(record)`. If the observer raises, the driver refuses, but the just-completed verifier attempt is never persisted. An injected one-attempt sweep with an observer raising `RuntimeError('observer unavailable')` produced a failure receipt with `records_retained=0`, and the ledger contained **zero records**. This violates the existing all-attempt retention requirement even though refusal itself is correct.

Persist the raw verifier attempt independently of successful coverage collection, or catch observation failure solely to append the raw record plus an explicit coverage-error status before re-raising. Never convert missing coverage to valid coverage. Preserve the failure and stop eligibility/continuation as required. The same principle applies to invalid coverage: record the attempt and its failed check rather than dropping the evidence.

## Residual 4: existing-manifest acquisition bypasses its mode/required-source contract

The existing-manifest branch only raises for content drift when `expect_mode == 'EXT'`; it never directly checks that the reused manifest's mode matches an explicitly requested EXT mode. It also skips all entries recorded `present=False`, including required sources, and returns drift under S1 as a normal result.

Two deterministic witnesses used small, genuinely hashed local files and a patched three-source specification, without downloads:

1. A valid existing S1 manifest, both required source files present and hash-correct, optional S2 absent, plus `expect_mode='EXT'`, returned **S1** without refusal.
2. The same existing S1 manifest with a corrupted required source and `expect_mode='S1'` returned **S1** with a nonempty `content_drift` list instead of refusing.

The first contradicts the explicit caller mode contract; the second bypasses required-source validation that a fresh `fetch_sources` call would enforce. The current EXT-selected study normally uses a prior EXT manifest, but these are real advertised API paths, not hypothetical arbitrary corruption defenses.

Minimal repair: apply the same explicit expected-mode check to both fresh and reused manifests; validate every required source regardless of roster mode; and refuse or restore same pinned bytes for required-source drift instead of returning it as usable acquisition. Preserve original manifests/access history. Keep protocol-permitted original S1 acquisition distinct from an established EXT study's later missing cache. The source mode must not be silently inferred from whichever incomplete cache is available.

## Acceptance boundary and next step

Keep D2 enrollment verification, sentinel/raw payload retention, timeout precedence, all-S1 duplicate handling, and the short-write/ledger connection closed for unchanged source. Add only the four bounded repairs above and targeted offline refusal/retention fixtures. Root owns the finite prefreeze budget, load-coverage design decision, environment-lock validation, TMPDIR policy and actual execution clearance. No new scientific observations or readiness credit arise from this review.
