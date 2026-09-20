# CPU package and live repairs: root acceptance disposition

September 20, 2026; review begun at the 06:24 UTC check and updated at the 08:05 UTC check. **Full-project readiness: 60% (change 0); bounded-v1 package: 90%.** Substantive implementation and preregistration work has arrived. Completed-study and accepted-design milestones remain pending; passing fixtures alone do not close them.

## Exact delivery and ownership

Main before this review is `69ff05818e40f69300c6e29e88a940a8b7de5239`. The `session60/live-ab` branch remains `577687799e8588077c036b4d94f1afc839d78e4f`. New work is on `session60/live-ab-validation`:

- `035a93458f8371a81eb06eae67048ca1f1580f76`: first host-check implementation and CPU preregistration package, following policy-only `c746e32`.
- `ddef3c83bb8a85f93aa27ee938c84fc32c1ccc78`: live-candidate repairs and a refreshed CPU vocabulary-document pin. This is the latest bounded-review source for this disposition, not a fully accepted study freeze.

The [06:33:52 UTC owner report](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5748153422) explicitly says **zero trial episodes, zero simulation cells run, nothing frozen, and continued host contention**. Root has not inspected the serving host. The owner retains all collection/repair directories; reviewers use separate scratch exports and root integrates only review/status records. No new PR, whole-branch merge or overlapping owner-source edit is made.

## What independent checking establishes

| Evidence | Independently checked result and limit |
|---|---|
| CPU package at `035a934` | 18/18 fixtures and 88/88 tests passed on root's Python 3.14.4 / NumPy 2.4.1; 88 tests took 6.413 seconds. These are deterministic/property checks, not simulation operating characteristics. |
| CPU package at `ddef3c8` | 18/18 fixtures and 88/88 tests passed again after the pin update; 88 tests took 6.450 seconds. Parsed `cells.json` has only one semantic change from the predecessor: the live protocol digest. No statistical finding is closed by that refresh. |
| CPU provenance | F18 hashes the three declared source files and three pinned modules. Root additionally matched each pinned module byte-for-byte to its named `5776877` source. That remains an old live pin; a claim about the eventual repaired live implementation requires its own explicit versioned comparison. |
| Statistical review | [Separate review](arxiv_cpu_prereg_statistics_review.md): 22 bounded checks, including finite-law means, allocation, Wilson thresholds and 14,400 cost combinations. Two checks deliberately reproduce scientific counterexamples; their passing does not mean the preregistration passes review. |
| Freeze-member repairs at `ddef3c8` | 15/15 targeted `FreezeBundleBindingTests` passed in 0.956 seconds, with temporary mock freezes and no serving. The unchanged-bundle/changed-margin witness now refuses. Config, roster/order, code, hardware-class and canonical-bundle checks improve the prior implementation. |
| Host repairs at `ddef3c8` | [Host review](arxiv_host_gate_delivery_review.md): 115 mocked tests passed; two real-host/account checks excluded. Separate injected cases still demonstrate false-clean parsing, missing randomized-phase scans/records, degraded CLI success, and baseline-activity interpretation/verification gaps. |
| Ledger repairs at `ddef3c8` | [Ledger review](arxiv_live_repair_ledger_review.md): ten selected owner tests and four independent fixtures passed. Interrupted unknown-usage accounting, persistent seed bookkeeping on readable chains and T4 invocation exclusion are confirmed within scope. An opened trial with an unreadable chain can still be silently omitted by program verification. No actual host was inspected or cleared. |

Root reproduction used clean Git-blob exports under `work/cpu_prereg_root/` and `work/live_repair_root/`. Commands were `python3 experiments/live_ab_validation/vfixtures.py`, `python3 experiments/live_ab_validation/tests_validation.py`, and `python3 -m unittest discover -s experiments/live_ab -p tests_lab_design.py -k FreezeBundleBindingTests -v`, from the respective exported roots. Logs and the root receipt remain in those ignored directories. No model, calibration cell or baseline full simulation ran.

The provenance check closes the actual stale CPU pin at the delivered commit; the owner's interim response table describes an earlier uncommitted tree and still prints the pre-repin failure. Preserve that historical table, but identify the final committed version and later receipt explicitly. Likewise, current source inspection, not a stale table, determines whether the active withdrawal and clip repair landed. Procedural separation and a shared radius primitive do not imply organizationally independent replication or independently implemented primitive arithmetic.

The freeze-member result is scoped. `lab_orchestrator.py:629–661` reads several declared digests from the bound configuration, rather than hashing the actual external serving/environment/sandbox artifacts. The serving-manifest test changes its configuration digest, not an on-disk manifest. `lab_common.py:240–247` checks only the coarse architecture/OS hardware identity; it does not uniquely attest a physical host. Code/roster/config/order bytes are recomputed, while declared historical members are explicitly excluded from runtime recomputation (`lab_common.py:413–427`). Do not turn these useful checks into a claim that every external artifact or serving condition has been independently verified. Populate and reconcile the actual final manifest and serving receipts before clearance.

## Required CPU design correction before acceptance

The first five CPU points require accepted deterministic adapter checks **and** an accepted known-truth specification. They remain unearned because the delivered specification still contains these substantive inconsistencies:

1. **Name the actual adapter being validated.** The independent feasible-set enclosure can give `[0,1]` where the live conservative certificate gives `[-1,1]`, on a state supported by the planned cells. Both can be valid bounds; requiring exact numerical agreement between them is incorrect. For this study, validate the actual live enclosure policy as the primary object, preserving its declared conservatism independently in the comparator. A tighter alternative may remain a separately labeled construction, but must not substitute for validation of the live rule or be hidden by a larger tolerance.
2. **Retain baseline event crossings.** The last-look reduction is valid for a fixed-prefix narrowing adapter, but not generally for completed-prefix or completion-order baselines whose effective denominator changes. The review supplies an in-support drain example with a real intermediate crossing that disappears by the final look. Specify all required baseline completion-index looks, simultaneous-event order and drain behavior before writing the runner.
3. **Use Monte Carlo flags as investigation alerts.** Keep the prespecified critical counts and outcomes, but distinguish approximate pointwise Monte Carlo uncertainty from proof of a defect. Observed count thresholds are not minimum detectable true rates or power guarantees. Keep the reduced-horizon scope explicit: expected-path crossings before 1,000 do not rule out realized crossings at 1,001–2,000.
4. **Resolve the acknowledged smoke confounding prospectively.** The concrete root instruction below retains the existing 20-program allowance. It changes the resource-design specification before measurements, not the scientific cells after their results.

## Concrete smoke/budget instruction to the existing owner

Use **five programs in each of the four combinations** `{C1,C2} × {N_max=1000,2000}`, for 20 programs total, with all four trials and three constructions per program. Specify the namespace-1 keys and fixed execution order before timing. Preserve the separation from the reported grid and record only resource measurements, counts and budget decisions from this smoke run.

For each cell `c` and measured horizon `H`, define `s(c,H)` as total elapsed seconds divided by five. For a candidate tier at that same measured horizon, project `programs_total × max_c s(c,H)`. Use horizon-matched output-byte measurements and the maximum measured peak RSS for the other resource checks. Both allowed horizons are measured directly, so no estimated exponent is needed to select a tier. Within-cell exponent estimates may be diagnostic only; do not use a cross-cell ratio as a horizon exponent.

These are practical projections, **not upper-bound theorems** for other cells or future load. Implement the specified observed resource limits, including the elapsed-time budget, and preserve/report any partial output when a limit is reached. Do not extend, drop cells or change tiers based on effects. If even the lowest tier is infeasible, pause and report under the existing rule. The shorter tier also shortens the observed decision and coverage horizon; disclose that loss.

Commit this revision, matching protocol/config, exact adapter pin and regenerated deterministic evidence before the grid. The current files call themselves frozen-on-commit, while owner comments say nothing is frozen: resolve this by an explicit versioned amendment and a named final freeze state, preserving earlier commits and the zero-outcome declaration. This instruction resolves the open smoke-design choice; it is **not clearance to start the calibration grid or live trial before the remaining scientific prerequisites are reviewed**. No new author permission or added model study is needed for this bounded correction.

## Remaining work and integration boundary

Before live clearance, repair the explicit host parser/activity/cadence/record cases and make missing or unreadable opened-trial chains visible to program verification. Preserve the confirmed normal-path seed/usage/T4 repairs; the residual chain-coverage finding is not a claim that those fixes failed. Keep the actual-roster horizon threshold and historical-withdrawal wording accurate in final templates. The unchanged success margin, bounded-mean formula and alpha allocation are not being retuned.

Session60 supplies the corrected CPU design/comparison and runner, completes the live host/ledger/manifest repairs, and presents the actual pre-run freeze for review. Root then accepts completed evidence and updates the expanded paper, supplement and release. Yukang retains final human scientific and arXiv submission checks. A null or abstention result can complete the study; a favorable effect is never required.

No new experiment outcome is accepted, incorporated into the paper or packaged in this cycle. All five arXiv artifact hashes and the historical anonymous code ZIP remain unchanged; there is no PDF-content change to rebuild. New reports record real review progress but close no five-point milestone, so the full project stays **60%**, with **40 checklist points remaining**, and bounded v1 stays **90%**.
