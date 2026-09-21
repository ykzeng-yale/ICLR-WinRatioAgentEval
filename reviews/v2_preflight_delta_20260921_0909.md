# Independent preflight/streaming delta review

September21 09:09 UTC cycle. Exact candidate **3341f2107b9ff9a5d67c9a09c3c27e9a4fe74d7d**, compared with0281eb21d1890cb58eeb1af3ee71cf352400df67. Scope: scientific equivalence of changed verification/output orchestration and the actual preflight gate. Root reviews reference pins/full-grid routing; the resource reviewer assesses supervisor/receipts. No scientific effects or new resource-run decisions were inspected; no panel, native reference, simulation, timing workload or full grid was executed.

## Accepted change and continuity

Independent byte comparisons confirm **vgen.py, vrun.py, vpolicy.py, vband.py and cells.json unchanged**. AST comparisons confirm `reference_rows`, `_ref_row_text` and `assert_reference_call_budget` unchanged. The previously accepted operational implementation, known-truth specification, constructed drain-decision witness and fixed fixture evidence therefore remain applicable to these same scientific functions. There is no reason to repeat all those witnesses or revoke the completed CPU deterministic five-point milestone.

The new named `verification_mode` is validated and recorded. Targeted constructor tests accept and record `preflight_only`, and refuse an unknown mode, non-frozen alpha and three trials/program. Source inspection shows that the preflight adds one call to the existing independent-policy checker on the first declared cell/program/trial path, before the primary trial loop. That checker returns only conformance counts; its results do not change primary records, reference inputs, margins or decision rules. The generator uses a fresh local seed sequence per coordinate, so preflight generation does not advance a shared RNG used by the subsequent run.

The changed reference output loop writes the same header and unchanged per-trial formatted chunks in the same deterministic order, then flushes/closes the file. This removes accumulation across trials while keeping successful-run scientific CSV content structurally identical. It retains only the current trial's arrays/rows and the ordinary bounded file buffer, rather than all panel rows. The new owner tests explicitly compare persisted primary/reference scientific bytes between per-trial and preflight modes. Those tests were **inspected, not independently run**, because this bounded assignment excludes native/scientific execution. No empirical runtime or memory claim is accepted by this source review.

## What the runtime preflight actually checks

At `vpanel.py:493–505`, it selects `cells[0]`, `cfg.indices[0]`, trial0 and calls `assert_operational_matches_policy` at that function's default five ticks. It does **not** rerun the previously constructed crossing witness or exhaustively compare every breakpoint. That is not a new mathematical defect: the stronger witnesses were independently checked on the unchanged scientific files already. Record the distinction as **one runtime conformance probe plus the exact-commit accepted witness evidence**, not a claim that the runtime function itself reruns the full accepted review suite. Root explicitly selects retaining this one-draw runtime smoke and linking the accepted deterministic witness/configuration receipts to the exact unchanged scientific source digests. No broader random preflight or repeat of a closed witness is required unless an affected scientific source changes.

## One narrow gate loophole to close

`run_panel(cfg,out_dir,verify_policy=True)` still exposes an unrecorded boolean override (`vpanel.py:383`). Both preflight and per-trial verifier branches test this flag (`:493,557`). Calling it with `verify_policy=False` therefore runs **no** verification even when the receipt/pins declare `verification_mode='preflight_only'` or `'per_trial'`; `_pin_kw` includes only the named mode, not the boolean. Default `vmeasure` use leaves it true, so this does not demonstrate that the reported measurement skipped verification. It is an executable identity/precondition gap, not evidence of a scientific result change.

Minimal correction before claiming the named pre-calibration gate cannot be bypassed: remove the unrecorded override, or reject `verify_policy=False` in measurement/full-grid modes (and name/pin an explicit disabled mode if ever needed for a narrowly scoped fixture). Test refusal without launching a panel. Do not respond by adding new randomized studies or repeatedly rerunning unchanged mathematical witnesses. Root may coordinate this item with its execution-identity audit to avoid duplicate requests.

## Disposition

Accept the verification scheduling/streaming amendment as **scientifically unchanged by source inspection**, with named mode tests passing and prior deterministic evidence preserved. The completed deterministic-specification milestone stays complete. Full calibration execution remains subject to the separately reviewed exact-pins/resource gates and the narrowly identified unrecorded verifier override. No new empirical calibration credit, runtime authorization or manuscript integration is implied.

Evidence: [portable script](evidence/v2_preflight_checks_20260921_0909.py) and [receipt](evidence/v2_preflight_checks_20260921_0909.json). The script compares source/AST identity and constructs configurations only; it executes no panel or reference and writes no owner outputs.
