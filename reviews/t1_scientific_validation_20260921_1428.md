# Independent scientific validation of committed T1 primary records

Exact reviewed snapshot: `35ab9d111123382db8997d4a0ccf4d5e36dbc876`, including corrected `t1_analysis.py` and `results/live_ab_validation_v2/t1_run_20260921/`. All primary bytes were read with `git show` at that immutable commit. No simulation, latent-path regeneration, native-reference computation, or model call was run. Root separately audits provenance, manifests, and resource/terminal receipts.

## Bounded acceptance

**Accept the reproduced primary-record calibration summaries, conditional on root's independent provenance acceptance.** The delivered study is executed, and its principal error/coverage summaries are independently reproducible from the committed observations. This is stronger than merely accepting a delivery, but it is not independent regeneration of every band or truth flag from latent paths. Existing prior scientific-code checks supply that separate evidence layer; this review does not replace them.

The independent standard-library aggregator read 56 primary files and 336,000 rows, corresponding to 112,000 trial paths represented once for each of three constructions and 28,000 programs. It found **zero duplicate `(cell, construction, program, trial)` coordinates** and verified trials `{0,1,2,3}` for every program/construction. C1/C2/C7/C8 have 8,000 trials/2,000 programs each; C3–C6 have 20,000/5,000. Independently calculated false-deploy, false-harm, trial-any-error, family-any-error, hierarchy/success two-sided miscoverage counts and Wilson intervals match the saved analysis, with **no discrepancies** (interval tolerance `1e-12`).

Reproduction code and detailed evidence are outside the repository at `work/t1_scientific_1428/check.py` and `result.json`. The aggregator does not import the owner's analysis or statistical runner.

## Principal reproduced findings

| Cell | ADAPTER hierarchy miscoverage | NAIVE hierarchy miscoverage | ADAPTER trial any-error | NAIVE trial any-error |
|---|---:|---:|---:|---:|
| C2 | 1/8,000 | 7,910/8,000 | 0/8,000 | 404/8,000 |
| C4 | 7/20,000 | 19,998/20,000 | 5/20,000 | 19,998/20,000 |
| C6 | 0/20,000 | 16,272/20,000 | 0/20,000 | 0/20,000 |
| C8 | 0/8,000 | 5,550/8,000 | 0/8,000 | 0/8,000 |

- All 29 `RETAIN_INCUMBENT` records are now visible and counted as false harms: CPREFIX has 1 in C1, 10 in C3, and 4 in C4; NAIVE has 2 in C1 and 12 in C3. ADAPTER has none.
- NAIVE family-any-error is 376/2,000 in C2 and 5,000/5,000 in C4. ADAPTER has five distinct erroneous programs in C4 and none elsewhere.
- ADAPTER has zero success-band miscoverage flags across this grid. It abstains throughout C1/C2/C3/C5/C6, abstains in 19,995/20,000 C4 trials, and deploys in all 8,000 trials of each favourable C7/C8 cell. These are cell-specific empirical readouts, not universal power statements.
- The eight saved alerts, drawn from the script's four selected alert readouts, reproduce and are all NAIVE. The frozen hierarchy positive control is detected in all C2/C4/C6. This demonstrates sensitivity to these large violations; it does not certify all theoretical or implementation assumptions.

C6 and C8 illustrate why decision errors and band coverage must be reported separately: NAIVE can have severe hierarchy miscoverage without a wrong deployment decision (C6 does not pass the success guardrail; C8 has genuinely favourable truth). Low decision-error rates alone cannot validate a band.

## The five C4 ADAPTER errors

Committed coordinates `(program,trial)` and first-crossing ticks are:

| Program | Trial | Prefix = tick |
|---:|---:|---:|
| 330 | 0 | 590 |
| 1677 | 3 | 1824 |
| 2365 | 2 | 1456 |
| 2561 | 2 | 733 |
| 2732 | 3 | 760 |

All five are DEPLOY under hierarchy truth zero, with `ever_below_h=1`, eligible-look hierarchy miscoverage, no success miscoverage, and no drain/finalization decision. Thus the exported records classify them consistently as hierarchy-driven false deployments. There are seven hierarchy-miscoverage trials in C4, so not every hierarchy exclusion caused a deploy.

The false-deploy rate is `5/20,000 = 0.00025`; independently computed marginal Wilson 95% interval is `[0.0001067896, 0.0005851504]`. Its lower limit does not trigger the frozen `0.00625` false-deploy alert. Five errors are not evidence of a theorem violation: the guarantee permits a nonzero error probability, and demanding zero would be scientifically wrong. Conversely, this empirical interval does not prove universal validity, remove prior-development exposure, or identify the exact rare-path mechanism. This review verifies the saved flags and first-crossing metadata, not the latent numerical boundary path at those coordinates.

## Prior corrections and residual analysis repairs

1. **Retention label and error definitions closed.** `RETAIN_INCUMBENT`, the full deployment conjunction (including C5/C6), and program unions of false deploy OR false harm are now correct and reproduce. Construction pairing and trial/program denominators remain appropriate under the frozen independent-trial generator.
2. **Monte Carlo summaries substantially closed.** Rate denominators and Wilson intervals now exist for all core error/coverage quantities. The selected eight alerts are correct. The alert loop still omits the separately prespecified false-deploy/false-harm component thresholds; including those adds false-deploy alerts for NAIVE C2 and C4. Label “eight” as selected-readout alerts or complete the component reporting. Marginal intervals are neither simultaneous across the table nor anytime-valid across repeated interim inspections.
3. **Power overstatement closed.** The script now correctly limits the claim to a finite-grid estimate of cell-specific performance, without claiming that intermediate power is impossible or that a power curve/MDE is identified.
4. **CLI remains stale.** `main()` accesses removed `complete_panel`, `program_deploy_rate`, and old contrast fields. It will fail after writing the new JSON output, rather than printing the schema-2 result. Repair the CLI using the new schema; this is a reproducibility-packaging defect, not invalidation of the independently matched saved JSON.
5. **Final reporting remains narrower than the full timing/resolution plan.** Present code reports a decision-conditional prefix median and some final fractions; it does not yet provide the full capped/conditional prefix and elapsed-tick summaries. Keep those omissions visible during paper integration. Any later timing summary must distinguish prefix from elapsed tick and from actual runtime savings. No new trial collection is requested here.

## Scope of the evidence

The strongest supported empirical result is that, for these fixed synthetic laws and this declared delay mechanism, ADAPTER's exported coverage/error events show no detected nominal exceedance while the completed-only NAIVE construction shows severe informative-delay failure. The large-effect favourable cells demonstrate that ADAPTER can reach a correct decision at this horizon. They do not establish power near practically small effects, production usefulness, causal validity of a live apparatus, or superiority to every valid comparator. CPREFIX also has low error rates here; a comparison with that valid baseline needs its own timing/information/readout interpretation.

This is namespace-0 replay with prior development exposure, not a fresh confirmatory holdout. H/D reference-band files were outside this review; no reference-width, reference-power or reference-calibration conclusion is added. With provenance accepted, these reproduced summaries support acceptance of the bounded executed CPU-calibration milestone. CLI/report completion belongs to subsequent integration and final QA; no zero-error criterion or full-grid rerun is warranted by this review.

Audit scripts and machine-readable evidence are also archived in [t1_validation_evidence_20260921_1428](t1_validation_evidence_20260921_1428/) for this exact snapshot.
