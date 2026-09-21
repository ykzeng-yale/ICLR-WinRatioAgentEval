# Resource guard and panel integration delta — September 21, 2026, 07:50 cycle

**Exact review:** `5336f8b0124b9aef0133e7facef268b8608b1e8c` against `08b4aa2`. Used root's immutable export at outer `work/v2_review_0750`. Scope: new guard behavior, its actual call sites, persisted panel outputs, memory/timing scope and smallest remaining measurement route. Root separately owns source/identity reconciliation. Independent checks extracted only pure guard functions through AST and applied synthetic inputs; static AST established actual call sites. Portable reproduction: `python reviews/evidence/resource_guard_checks_20260921_0750.py EXPORTED_REPO`. No native reference calls, models, timing, simulations, grid or Git mutation.

**Disposition:** Accept bounded repairs to the guard helper and delivery of a panel wrapper that persists H/D reference outputs. Do not accept the claim that the actual panel entry point is resource-gated or bounded as a fixture. It is not. The absence of a qualifying resource ledger is honestly disclosed; a bounded CPU measurement can close that absence after the actual entry-point/configuration issues below are repaired, without waiting for a GPU live-serving window.

## Supported progress

The new pure guard refuses nonfinite/negative projected costs, excess bytes, excess RSS, an absent combined receipt, a short recorded group count and a proposal with ten times the priced programs. Independent synthetic controls reproduced those new refusal classes and verified enforcement raises. A fully populated **synthetic** control passes, as it should. These checks support logic for supplied fields; the `control` identities used in the demonstration are not an actual experiment ledger or independent scientific acceptance.

`vpanel.run_panel` now evaluates a configured primary and computes H and D once each per trial on shared draws, then saves reference rows separately. The small deposited integration fixture has 12 trials, 12 H calls, 12 D calls and 48 retained rows. This closes the earlier absence of a persisted reference output path at fixture scope. It is not the full calibration result or a resource receipt.

## 1. The new panel bypasses the improved guard entirely

Static call inspection finds **zero** guard/enforcement calls in both `vpanel.run_panel` and `vpanel.main`. `PanelConfig` only checks positivity and limited policy/schedule compatibility (`vpanel.py:140–163`); `main` accepts arbitrary `--programs` and `--n-max`, plus `--no-reference`, without a fixture-size limit or a cleared-ledger argument (`373–387`). The docstring's claim that a full grid refuses without an explicit cleared receipt is therefore false. This is an integration defect even though no unauthorized full run is reported.

The legacy `vrun.main` also still calls `total_workload_guard(budget, cfg_json)` **without** `proposed`; it resolves `args.tier`, `args.n_max`, `args.cells` and `args.programs` afterward. Thus improved override logic exists in the helper but is not wired into that caller. With current missing identities this path refuses, which is safe, but it is not a working actual-argument-priced execution route.

Resolve one explicit proposed panel configuration first, construct/bind its ledger, and call the guard before drawing trial streams. Require the operational primary and H/D reference in the scientific panel mode; do not permit a mode label or `--no-reference` to bypass the declared workload. Development fixtures/resource measurements need a separately explicit, tightly bounded entry point, not an unlimited unguarded library function presented as a fixture. The historical v1 reproduction path remains separately identified.

## 2. Actual-argument pricing and group checks still have narrow holes

On a synthetic otherwise passing ledger, the exact new helper:

- Authorizes `proposed.n_max=20000` against a priced horizon 2000: the numeric horizon is never read.
- Authorizes `proposed.programs_total=NaN`: `_proposed_scale` returns 1 because `max(1.0, NaN)` returns 1 (`vrun.py:2350–2367`). Invalid counts must fail, not normalize to the priced tier.
- Authorizes a receipt declaring zero planned and zero completed groups; group accounting checks only whether completed is less than planned (`2431–2453`). It does not validate the fixed expected coordinates, uniqueness or positive complete counts.
- Does not examine `attempts_failed`; a synthetic receipt with failures and unchanged group counts passes. Historical failed attempts need not invalidate repaired, complete evidence forever, but each attempt and successful replacement must reconcile by exact design coordinate. A count alone is insufficient.

A real configuration identity could reject a changed horizon if it binds the complete normalized execution request; root's identity review owns that contract. It does not excuse a helper claiming to price actual horizons while ignoring them, nor the absent caller wiring. Require finite positive integer counts and exact supported horizon/cell coordinates. Price each intended coordinate from the appropriate measured rule; refuse unsupported horizons rather than extrapolate silently. Scaling peak memory linearly with total program count is not a demonstrated model—use the actual storage strategy's bound/measurement instead.

## 3. Persisted output changes the resource scope

`vpanel.py:274,311` retains all formatted reference rows in `ref_lines`; joining them creates another full string at the end. This is memory growth with total trials and retained prefixes, beyond the old one-path reference timing. Prefer streaming reference rows to a fresh file with incremental byte accounting, as the primary sink already does. If buffering is retained, derive and validate its full-size memory requirement; do not reuse the old small-process RSS as its bound.

`elapsed_seconds` is stopped before `sink.close()` and `ref_path.write_text()` (`vpanel.py:318–320`), so the fixture's 0.2107 seconds is not complete end-to-end persisted-output timing. Policy verification is now executed per operational trial and its cost is inside the new loop, but absent from the old combined receipt. The resource measurement must cover whichever verification policy the intended full run freezes, primary and reference execution, reference row construction, both output flushes/closes, and retained memory. Add bounded runtime checks for elapsed time, actual bytes and RSS while executing; there are currently none in `run_panel`.

No new qualifying end-to-end resource ledger is present. The old projected ~2044 seconds against 5400 remains conditional planning information, not evidence of an over-cap run or of current panel admissibility. Keep the existing scientific tier and caps pending the missing measurement; there is no basis here to reduce the tier or enlarge caps.

## 4. Development coordinates need an explicit interface

`PanelConfig.namespace` defaults to grid namespace 0 (`vpanel.py:148`), and `run_panel` loops from program index 0 (`283`). There is no `program_base` or CLI namespace argument. Consequently the new wrapper cannot yet reproduce the specifically authorized resource coordinates: namespace 1, C1/C2, indices 1000–1004 at both horizons 1000 and 2000.

The delivered fixture receipt explicitly records namespace 0, cells C2/C3/C7 and program 0 (12 trials). Preserve this receipt and inventory these development exposures; do not describe all corresponding namespace-0 streams as unseen or quietly drop them from later reporting. Root should adjudicate that disclosure against the frozen study plan; this resource review does not alter any scientific seed or selection rule.

## Smallest practical completion route

1. Bind the actual scientific entry point to the normalized execution configuration and the complete guard. Fix the count/horizon and planned-coordinate checks using non-timed fixtures.
2. Add an explicit **resource-development mode** fixed to the existing 20 units/ten seed identities: namespace 1, C1/C2, program indices 1000–1004, horizons 1000/2000, operational primary, both H/D calls and the exact persisted-output/verification strategy. This bootstrap measurement cannot require the qualifying ledger it is creating, but must enforce its own fixed development coordinates, bounded attempts, time/bytes/RSS caps and fresh-output policy. It is not a blanket guard exemption for arbitrary panels.
3. After a capacity check, authorize only the missing end-to-end CPU measurement on that mode. Root specifies one pass per design unit initially (80 trials, 160 timed reference calls), with a narrower parent-enforced 300-second development cap, 200-MiB-output and 2-GiB-RSS caps; the eventual full-study seconds cap remains 5400. Report warm-up calls separately if any, and preserve a timeout as a recorded attempt rather than silently extending it. Existing foreign GPU serving processes need not block this CPU-only development measurement: record contention and actual timing scope, do not stop foreign processes, and do not interpret the resulting timing as a quiescent-host guarantee. If available capacity or a cap prevents completion, preserve the partial attempt and report it. This does **not** authorize a live trial, models, downloads, paid compute, full calibration or another broad timing sweep.
4. Preserve all earlier timings. Deposit the exact final callable/config/source/binary/environment pins, timestamps, complete planned/completed coordinates and attempts, raw timing values, eight-call accounting, output sizes and combined memory. Root can then review the qualifying ledger without another loop of old prototype timing.

The current helper improvements and retained reference fixture are progress, but full-panel guard wiring and the newly measured output/memory scope remain the concrete completion gates. No readiness increment or full-grid/live clearance is granted here.
