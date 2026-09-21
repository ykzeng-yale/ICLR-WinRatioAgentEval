# Supervisor closure and terminal budget check: 2026-09-21 11:36

Reviewed exact head `fda55c2d7793eb521f321f99635ec555397fc543`, using immutable export `work/v2_review_1136`. Scope: closure of existing partial-observation findings and the supervisor's whole-job terminal budget semantics. Root owns the new launcher/shard implementation. No scientific outcomes, native calls, models, grid runs, actual process launches or signals were used. Python fixtures mocked subprocesses, process-group lookup, cleanup and elapsed time.

## Closed: prior partial-observation findings

- `vsupervise.py:86–91` now rejects every nonzero enumeration status, including partial stdout. The previous partial-output fixture raises `MeasurementFailure`.
- `vsupervise.py:264` now invokes `_tree_rss_bytes(pids)` with its strict default, removing the unconditional missing-coverage allowance. The previous one-row/two-PID fixture rejects in the helper. A fixture of the **whole actual `supervise` function** also records `measurement_failed`, returns `within_caps=False`, and takes its owned-job cleanup path.
- Owned-group cleanup was already closed in the 10:58 review and is not reopened here.

The previously requested enumeration/RSS observation repair is therefore closed for its stated counterexamples.

## One terminal accounting correction

At `vsupervise.py:302`, elapsed time is recomputed after `communicate`, but the final checks at lines305–309 check only output bytes. The acceptance expression at line342 can therefore say `within_caps=True` while the recorded terminal wall time exceeds the specified time limit.

Independent whole-function fixture: first/terminal poll observes 0.5 seconds, terminal elapsed is 2 seconds, cap is 1 second, process exit code is zero, and bytes are below cap. The returned receipt has `wall_seconds=2`, `breach=None`, `within_caps=True`.

Smallest repair: check the final recomputed elapsed against `caps.seconds` before determining `within_caps`, preserving any earlier breach. The full T1 launcher must not label a terminal over-budget attempt as successful. This is a terminal receipt/acceptance correction within the existing supervisor; it does not request another execution architecture, timing sweep, scientific change, or reopening of the accepted measured cost.

## Output scope and disposition

The existing poll-time metadata reserve and actual-child-directory final byte field retain the scope accepted in the previous review. The supervisor's final receipt is written after the child-directory check; root's launcher finalization owns the final all-artifact total and the reserved parent metadata. No claim is made here about the separately reviewed launcher completion condition.

Retain the accepted historical measurement and conditional T1 projection. Close the old partial-observation gates now; repair the one final wall-clock acceptance check with an isolated fixture, then root can judge launch readiness with its independent shard/manifest review. No remeasurement is required by this finding.

Evidence: `work/supervisor_closure_1136/synthetic_findings.json`, plus mocked whole-supervisor receipts in `terminal_wall/` and `production_partial/`, outside the repository. These are synthetic validation records, not experiment deliveries.
