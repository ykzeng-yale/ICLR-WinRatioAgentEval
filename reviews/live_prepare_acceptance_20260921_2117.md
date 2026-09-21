# Preparation repair acceptance — 2026-09-21 21:17 UTC

Reviewed source at `9202829`, including preparation repair `c4ce4bbf4a32eed125d795bc6063fdb7bab002e0`, with main context `cfcab48`. The `c4ce4bb..9202829` changes themselves are environment evidence; preparation source was compared to the previously reviewed `1a32aa3`. Exact export: outer `work/prepare2117/`. No sandbox probe, model, server, or reference solution was executed.

**Accept raw-first retention, schema-filtered digest reconstruction, final refusal of explicitly invalid observer results, and TMPDIR enforcement at the reference-sweep entry point. The existing immediate-stop, interval-coverage, acquisition and two-worker containment obligations remain narrowly pending.** Do not reopen unchanged short-write, sentinel, D2 verifier, timeout, or duplicate-rule acceptance.

## Bounded executed checks

`python3 -m unittest tests_lab_design.PreparationWiringTests tests_lab_design.TmpdirEnforcementTests -v` ran eight tests: all passed, no skips. These include the real entry point's mismatched TMPDIR refusal and resolved-effective-directory comparison. The valid TMPDIR test calls the helper directly, so its scope should be described accurately. `run_reference_sweep` now calls the assertion by default before opening the ledger; acquisition has an opt-in `enforce_tmpdir=False` argument. This does not establish trial-worker startup enforcement, which root reviews separately.

Independent three-attempt stub checks of the exact entry point, with no task execution:

| Observer result | Driver result | Attempts started | Raw records retained | Coverage records |
|---|---|---:|---:|---:|
| `active=False` | refused | 3 | 3 | 3 |
| observer raises | refused | 3 | 3 | 0 |
| `active=True`, window id and resolution, no interval evidence | completed | 3 | 3 | 3 |

The raw-first repair genuinely closes the previous observer-exception data loss. Filtering reloaded records by attempt schema avoids mixing coverage metadata into exclusion digest reconstruction. Final invalid-coverage refusal means this call does not return an accepted exclusion list.

## Exact residuals in the same obligations

1. **Immediate stop is still missing.** Both invalid-observation and observer-exception branches append to `invalid_coverage` and return from the sink. They refuse only after `sweep_fn` finishes. The three-attempt witness above therefore starts all three attempts despite failure on the first. After preserving the raw attempt and a structured coverage/error record, raise to stop before the next attempt. This is the existing failure/stop requirement, not a new protocol design. On observer exceptions, the current error detail is only in the in-memory failure list/exception; persist it alongside the already-retained raw record.

2. **Required load coverage is still metadata presence, not interval validation.** `_coverage_is_valid` checks `active is True` and nonempty `window_id`/`resolution_ms` only. It does not compare actual verifier start/end times with active-load windows on the agreed clock. A post-attempt result containing those three fields passes, as the third witness shows. Complete the already specified attempt-endpoint/window-overlap check and refuse insufficient coverage, retaining the failed attempt. No new model call per attempt or broader study is requested by this review.

3. **Acquisition residuals are unchanged.** The prior-manifest branch still returns an existing S1 manifest despite an explicit EXT expectation when no drift is detected, and still returns required-source drift under S1 without refusing. These paths and the prior deterministic witnesses are documented in `reviews/live_prepare_delta_20260921_2043.md`; they were not rerun because the relevant code is unchanged. Apply expected-mode checks consistently and required-byte validation regardless of mode. The original protocol-permitted S1 fallback remains distinct from silently changing an EXT-selected study.

## Containment receipt: accept its observed subset only

Inspected `lab_containment.py` and `results/live_ab/CONTAINMENT_PROBE_RECEIPT.json` as committed evidence; did not execute them.

The receipt reports five repository-resident targets times three operations, all fifteen returning `PermissionError`, plus an empty peer-directory glob. These are useful bounded observations under the reported profile. The sixteenth `denied_attempts` entry is the empty enumeration, not another denied filesystem operation. The retained negative control is a summary reporting fifteen detected breaches; it does not include its full per-operation/raw execution receipt, so independent validation here is limited to that saved summary.

The source starts **one** sandbox program while holding the production lock. It does not launch a second worker attempting to acquire the lock, and the peer-directory code enumerates and may list a found peer; it does not perform the declared peer read/write attempts. Therefore the receipt's statement that all six target classes were probed with list/read/write is too broad. No peer directory being found is not an exercised demonstration that a concurrent second worker is blocked.

Accept the fifteen reported repository-target denials as that bounded containment subset. Keep the existing two-worker lock/exclusion fixture pending: a controlled second-worker contender must exercise the production lock and retain the relevant timing/refusal evidence. Do not reinterpret an absent peer as successful two-worker testing, and do not rerun or weaken the accepted fifteen-target subset merely to report a broader PASS. Root controls the finite authorized execution of any missing containment fixture.

## Handoff

Close the fixed retention and reference-sweep TMPDIR findings. Finish immediate stop after retained failure, actual interval coverage, the unchanged acquisition checks, and the already-required two-worker containment evidence. Root separately verifies whole-environment hash preimages and trial-worker startup; this review makes no independent claim about that work and grants no execution authorization or readiness credit.
