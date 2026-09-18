# Round 10: independent audit of the drift and unequal-law-null panel

Audited frozen PR 10 head `ae3f0a5d4936855fc0b81f4a327254e932ea729b`, September 18, 2026. This is an AI scientific/code review, not human peer review. Only this report and `work/round10_pr10_audit/` were written. No model/API calls, model downloads, Git mutations, or airline-job operations occurred.

## Verdict

**PASS for numerical correctness and bounded scientific integration.** The entire CPU study reproduced exactly. The final implementation correctly defines per-step and running-average targets, applies nine rules to shared streams, and distinguishes false deployment at the first crossing from a false deployment condition at any scheduled look. No code correction or further simulation is required for the restricted claims below.

Three documentation conditions remain: scope fixed-null language to the rule's **claimed** gates; distinguish verified final provenance from the unretained first-run history; and keep the betting wealth-dominance remark outside the paper's established guarantees unless separately proved and reviewed. The panel supplies the common-drift, treatment-by-time and unequal-law experiments previously deferred in Round 9. It does not supply live online data, concurrent latency evidence, universal empirical calibration, or a demonstration that splitting alpha is necessary in practice.

## Reproduction and independent checks

I extracted the frozen Git blobs into an isolated scratch snapshot, inspected the runner before execution, then ran the unmodified full study with five workers and its required protocol hash. It completed successfully in **53.982 seconds**. This comprises 96,000 sequential replicates (12 scenarios, nine shared-stream rules), 14,000 permutation replicates, and 44 one-million-draw target checks. Both numerical CSVs were byte-identical to the contribution:

| Artifact | Rows | SHA256 |
|---|---:|---|
| `results/drift_panel/results.csv` | 108 | `c230d940e7de1526a744add5b45f35bb16381ccf1bcafd27847ce83d0320af95` |
| `results/drift_panel/permutation_results.csv` | 9 | `cd8e472dbe6efc5c0d0a7c17d8e58ccf585ac8b2588ea6d76c1d53139769fb36` |

The regenerated manifest differs only in runtime, Python and OS metadata: my Python 3.14.4 versus the builder's 3.12.13, with identical NumPy 2.4.1 and SciPy 1.17.0. All design, target-verification, seed and numerical metadata match.

Additional independently written checks—not just rerunning the worker—gave:

- Enumeration of all 16 compliance/success configurations at all 10,000 steps in each scenario: maximum target discrepancy 1.11e-16.
- Numerical quadrature for the resource-preference probability at all 44 verification parameter sets: maximum discrepancy 5.55e-16.
- Forty-eight reconstructed trajectories using explicit costs and independently calculated betting, normal-mixture and Wald decisions: all **85,968 rule/look decisions** match. Maximum log-wealth rounding discrepancy was 8.07e-13 with no changed decisions.
- All **441 Wilson intervals** independently recalculated, maximum discrepancy 2.22e-16; event counts obey first-running-error <= any-running-error <= ever-deploy. Executions equal twice capped pair use in every row.
- Running violation masks match independently enumerated targets. In B3a/B3b every scheduled look has some violated gate but no single gate is violated at every look. Boundary roundoff is far below the 1e-9 classification tolerance; the smallest genuinely nonboundary distance across the four B designs exceeds 5e-4.

Retained audit evidence: `work/round10_pr10_audit/independent_checks.py`, `independent_check_results.json`, `snapshot_manifest.json`, original expected artifacts, complete rerun outputs and `full_reproduction_stdout.log`. The checker reruns without model calls after the snapshot reproduction exists.

## Target, rule and error-event assessment

The independent-arm Bernoulli/lognormal construction and deterministic parameter paths imply that per-step expectations equal conditional means. The cost-scale drift cancels under the relative-cost tolerance, as intended. C1/C2 genuinely have unequal arm laws with exactly zero net benefit: the success gain offsets the worse resource distribution. Their permutation comparison tests equality in distribution, a different null.

`run_drift_panel.py:133–190` implements the stated hierarchy, score ranges, shared looks, fixed betting grid, same-look conjunction and per-gate versus split thresholds. `:191–217` correctly evaluates error using deterministic true-target masks rather than estimates. In particular, its `E_running_any` evaluates all 199 prescribed looks even after a first deployment; `E_running_first` concerns only that first deployment. `E_current_first` is descriptive and has no asserted error guarantee. Fixed-horizon and planned-look Wald methods are correctly not granted finite-sample anytime guarantees.

The valid theorem interpretation is rule-specific. In A1–A3/C1/C2, guarded decisions have one fixed conditional-null gate, so the fixed-null proof works despite other means drifting. Win-only rules have this null property only in A1/C1/C2. For B1/B2 the normal-mixture running-target error can occur only through the net-benefit confidence sequence. B3 needs simultaneous component coverage for the stated general bound; per-gate alpha supports the union bound, not a claimed 5% conjunction guarantee. No inference is supplied for present/future effects, multiple candidate revisions, or a program-wide family of deployments.

## Integration-safe numerical tables

All entries below are percentages for **E_running_any**, with pointwise 95% Wilson Monte Carlo intervals and 10,000 replicates per cell. They describe the specified 199-look schedule, not an empirical audit of every arrival or simultaneous inference over the entire table.

| Scenario | Guarded betting | Guarded normal mixture, split | Repeated Wald |
|---|---:|---:|---:|
| A1_identical_null | 0.55% [0.42, 0.72] | 0.00% [0.00, 0.04] | 26.86% [26.00, 27.74] |
| A2_success_boundary | 0.38% [0.28, 0.52] | 0.00% [0.00, 0.04] | 30.52% [29.63, 31.43] |
| A3_compliance_boundary | 0.38% [0.28, 0.52] | 0.00% [0.00, 0.04] | 29.77% [28.88, 30.67] |
| C1_unequal_law_null | 0.64% [0.50, 0.82] | 0.00% [0.00, 0.04] | 31.50% [30.60, 32.42] |
| C2_unequal_law_null_tie_heavy | 0.73% [0.58, 0.92] | 0.00% [0.00, 0.04] | 32.12% [31.21, 33.04] |

For these guarded null cells, any-running error, first-running error and ever-deployment coincide. The observed betting rates are consistent with the applicable guarantee; low estimated rates do not prove uniform calibration. Repeated Wald has large errors in these designs.

| Scenario | Normal mixture, per-gate alpha | Normal mixture, split | Betting, per-gate alpha (descriptive here) |
|---|---:|---:|---:|
| B1_nb_pos_then_neg | 0.01% [0.00, 0.06] | 0.01% [0.00, 0.06] | 0.01% [0.00, 0.06] |
| B2_nb_neg_then_pos | 0.01% [0.00, 0.06] | 0.00% [0.00, 0.04] | 0.01% [0.00, 0.06] |
| B3a_alternating_violator | 0.00% [0.00, 0.04] | 0.00% [0.00, 0.04] | 0.37% [0.27, 0.51] |
| B3b_cycling_violator | 0.00% [0.00, 0.04] | 0.00% [0.00, 0.04] | 0.48% [0.36, 0.64] |

For B3a/B3b the normal-mixture forms both make zero deployments. Therefore this panel **does not empirically show the necessity of alpha splitting** or distinguish their error rates. The small betting rates are descriptive under the manuscript's presently stated theorems. For B1, every sequential rule first deploys before the effect reversal; the final running net benefit is negative. That demonstrates the difference between a correct early running-target decision and a guarantee about future benefit.

Additional useful facts: the equality-in-law permutation maximum test rejects 4.29% [3.91%,4.71%] in its equal-law calibration cell and 94.30% [93.20%,95.23%] / 100% [99.81%,100%] in C1/C2. These are correct rejections of a different null, not false positives against mean win. In A6, the split normal-mixture rule uses about 1,868 capped pairs versus 1,481 without splitting; both deploy in all 2,000 repetitions. This is one scenario's sample-use cost, not a general efficiency ordering.

Suggested manuscript claim: “In a post-primary, internally specified synthetic extension with deterministic drift and independent pairs, the split normal-mixture rule had 0–1 running-target false deployments per 10,000 repetitions in four treatment-by-time designs. Unequal-law zero-net-benefit cases also separated the weak preference null from equality in distribution. The alternating-violation cases were too conservative to demonstrate an empirical need for splitting.”

## Documentation corrections and boundaries

1. **Fixed-null scope (minor, required for precise integration).** `protocol.md` sections 4–5 and the report's event definitions must read “one fixed **claimed** gate.” The CSV's `fixed_gate_conditional_null_every_step` is scenario-level metadata, not automatic validity certification for every listed rule. Win-only rules in A2/A3 deploy with probability one because their net-benefit alternative is true; their own running-target error is zero. The numerical code handles this correctly. Add an explicit qualification/erratum rather than silently altering the frozen protocol hash.
2. **Freeze and overwritten first run (provenance limitation).** I verified the final protocol, code and core hashes against the final log/manifest and exact reproduction. The runner enforces the supplied protocol hash before sampling. However, Git first records the protocol together with final results at this commit; the earlier full-run outputs are not retained. Thus I cannot independently confirm the pre-first-run freeze chronology or the asserted field-by-field claim that only win-only `E_current_first` changed. The internal filesystem-timestamp audit is supporting testimony, not preserved original-run evidence. Keep the declared internal-freeze/deviation wording and do not call it independently verified public preregistration. This does not invalidate the reproduced final numbers and does not warrant fresh simulations.
3. **Betting wealth-dominance remark (separate theory dependency).** The protocol/report explicitly label this outside the manuscript's proved guarantees. Observed low rates cannot establish it. Any adoption must supply an explicit pathwise domination proof with the positive denominators, fixed nonnegative bets and fixed mixture weights, the precise conditional means and the running-average rejection event. Do not extend it to arbitrary adaptive bets or call the betting wealth itself a calendar-time e-process. The drift panel can be integrated without adopting this extension.
4. **Avoid deterministic claims about true effects from zero observed deployments.** The normal-mixture statement about needing roughly +0.023 compliance at n=10,000 is a requirement on the **observed mean difference** for that boundary, not an impossibility theorem at smaller true means. Likewise, write “zero observed errors gives an upper Wilson limit of 0.000384,” rather than describing the unknown true error rate as zero. Pointwise Monte Carlo intervals are not familywise confidence statements over the panel.

## Exact dependencies and handoff

- Protocol SHA256: `bb497cbb7c58fd1578530748c9d5ef834dc079e8b14973bc0bee348ca5c276cc`.
- Runner SHA256: `1bc0a113e98bd3b83dffba041d3763c93c450cd1a5e6542982a19bd659823a41`.
- `src/winstats.py` SHA256: `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9`, identical to scientific release `f806aba`.

This contribution uses the stable `winstats` core, not PR 8's disputed `wincs` two-sided construction, and does not depend on merging PR 7/8. Root can integrate the frozen `experiments/drift_panel/`, `results/drift_panel/` and appropriately qualified report, add accepted outputs to release hash/reproduction verification, then rebuild and inspect the final manuscript. Figure-generation mappings read the appropriate CSV events; final manuscript layout still needs release QA. No further commercial/proprietary or open-model inference is needed to close this panel.


# ROOT INTEGRATION REVIEW

This is an AI scientific/code audit of root's manuscript integration, not human peer review. It supplements the frozen PR 10 audit above. Scope: `experiments/build_sequential_extensions.py`, its three generated manuscript sections, the accepted PR 7/10 numerical files, and the relevant fixed-stake statements in `paper/theory.tex`. I made no source/result edits and ran no additional simulations or model calls for this integration check.

**Verdict: numerical and scientific PASS after the two wording corrections described below.** All selected numerical displays agree with the accepted records. The remaining handoff dependency at this writing is root's regeneration of the builder outputs/manifest after its latest provenance/text edits; this is a mechanical package dependency, not a demand for new experiments.

## Independent numerical checks

- Reconstructed every displayed calibration row by scenario, method, and crossing convention: 21 rate/interval cells across seven procedures. Counts divided by 10,000 agree with rates; all pointwise 95% Wilson limits were recomputed independently, and the two-decimal percentage displays match.
- Reconstructed all 14 selected power rows (seven methods, two scenarios), each with 2,000 repetitions. All displayed deployment percentages, rounded mean capped records per arm, and rounded Monte Carlo standard errors match `ustat_reference_results.csv`. These are capped resource means, not means conditional on deployment; the two-execution conversion is correct. This check verifies the archived MCSE selection and display, not a fresh rerun of unretained individual stopping histories.
- Reconstructed all 21 displayed drift rate/interval cells. They select `E_running_any`, with 10,000 repetitions each, rather than silently substituting first-decision or current-effect error. Independently calculated Wilson intervals match all displayed limits. The main paragraph's 0.55% versus 26.86% and 7.25% versus 1.83% come from the correct, explicitly distinguished events.
- From the diagnostic CSV, the projection-Gaussian component has 725 first rejections; 410 occur by 500 records per arm; 239 have zero observed noncompliant A records at crossing. All 239 also fall within those early 410. The diagnostic interpretation remains conditional on rejection and does not establish the mechanism or a remedy.
- Independently calculated the residual variance contribution from the saved Monte Carlo components: minimum 0.00000593692304279, maximum 0.00002492399584636; relative to the first-order term, 0.132473%–0.406306%. These round to the stated 5.94e-6–2.49e-5 and 0.13%–0.41%. They are estimates of population variance components, not exact analytic constants or bounds on estimated-variance error.
- Confirmed the non-table drift values: split-betting switching-error rates 0.08%/0.15%; A6 normal-mixture capped means 1481.05 versus 1868.15 pairs; B1 final running net benefit −0.08000000000000448. All eight sequential rules in B1 deploy in every replicate before reversal; fixed Wald makes no deployment. The permutation maximum test rejects 1886/2000 and 2000/2000 in C1/C2, giving 94.3%/100%, against its different equality-in-law null.

## Claim scope and seed separation

The primary seed is 20260917; the matched PR 7 comparison uses 20260918, with separately indexed calibration streams; the PR 10 drift extension uses 20260919. The PR 7 disjoint-betting reproduction matches the separate online-comparator pipeline, not the primary table's seed stream. No integrated wording treats these as identical original replications.

The integrated text correctly distinguishes finite-grid Monte Carlo evidence from time-uniform theory, individual-gate rejection from simultaneous guarded deployment, retained crossings from a current-prefix conjunction, and win-only from guarded claims. It does not label a rejection of unequal outcome laws as a false rejection of the weak mean-win null. It does not claim that a correct early running-target decision guarantees future effectiveness or that a single-experiment alpha controls repeated candidate deployments.

The new fixed-stake result in `paper/theory.tex`, Proposition `prop:bet_running`, supplies the formerly missing domination argument: fixed nonnegative stakes and fixed weights admit a normalized martingale dominating the observed wealth at running-null prefixes. Its scope is the average of conditional means and same-prefix crossings; it does not make arbitrary adaptive-stake wealth a supermartingale. The integrated references and split-alpha discussion are consistent with that statement. The earlier report's unresolved wealth-dominance dependency is therefore superseded by this explicitly scoped new theorem and the separate theory audit. Low simulated error remains supporting evidence, not its proof.

## Corrections raised during integration

1. **Resolved in generated text:** the drift appendix initially said all nine methods shared 199 monitoring looks. It now states that the 199 times are candidate evaluation times, with the group rule restricted to ten planned looks and fixed rules to the final look. This prevents an incorrect equal-look comparison claim.
2. **Resolved in generated text:** the U-statistic appendix initially attributed the full linear asymptotic variance to the first Hoeffding projection. It now distinguishes the linear term's asymptotic variance sigma_A^2 + sigma_B^2 from the projection variance, one quarter as large for the displayed symmetrized kernel.
3. **Root builder update observed; regeneration pending at this writing:** the diagnostic CSV was initially absent from the builder's declared hash inputs despite the hardcoded 725/410/239 paragraph. The edited builder now loads and hashes that CSV. Its edited prose also labels the residual components as Monte Carlo estimates and records drift seed 20260919. Regenerate the three sections and `sequential_extension_paper_manifest.json` together, then verify that source/input/output hashes match. These prose numbers were independently checked above even where they remain text literals.
4. **Minor interpretation refinement advised:** saying normal-mixture width is “too large to resolve” the switching cells can sound like a demonstrated cause. Those cells have a null conjunction at every look, so zero deployments alone does not establish the mechanism. Prefer that wide bounds are consistent with conservatism in these configurations, and retain the explicit statement that these cells do not empirically demonstrate a need to split alpha. The A6 sample-use contrast is a descriptive comparison under one alternative, not a universal power ranking.

## Audited integration versions

The regenerated manuscript versions containing corrections 1–2 had these SHA256 values:

- `paper/sequential_extension_results.tex`: `d36c2712da2d0fc267a2c2312921ceadeb90d2b0b966eed09dcdc9d15c74cfdf`.
- `paper/ustat_extension_appendix.tex`: `c697780685306f5e6f811c19cc9100f332894ce0b8d213bdf152ddc2e68155dc`.
- `paper/drift_extension_appendix.tex`: `0e8ca2b1531ccbe9818176d539f25b75ab8c8b968368e2b8e375e488908308fd`.
- `paper/theory.tex`: `ddaebf17e6e9b72822ff945d37475bdb176cba37b27f78fee3c8505e1881445f`.

Their builder/manifest source hash was `9c2d2539b3a2eb5fe3e2aa42504f404561169cec06090c9f3cc2e0644fb587e4`, and all then-declared input/output hashes passed. The subsequently inspected, not-yet-regenerated builder with correction 3 has SHA256 `997064157c7c11483e8e32f21b8ba0cf033e30dff2a64a7c5a49294a0f346e79`. Do not mistake that temporary source/manifest mismatch during concurrent integration for changed experiment rows.

No new scientific or numerical blocker, comparison simulation, open-model inference, or commercial call is required by this integration audit. Final regenerated hash verification and manuscript layout QA remain root's release responsibilities.


## Final frozen integration verification — PASS

Root regenerated the builder outputs after the foregoing corrections. I independently verified the frozen builder SHA256, all six input hashes, and all three generated output hashes against `results/sequential_extension_paper_manifest.json`; all match. The diagnostic CSV is now included in the declared inputs, and the builder explicitly checks the 725/410/239 diagnostic counts. The generated text contains the corrected monitoring-look and projection-variance statements, labels the residual components as Monte Carlo estimates, records drift seed 20260919, and qualifies the width explanation as consistent with conservatism without identifying its cause from null configurations.

This closes the temporary regeneration dependency and the minor interpretation refinement above. **Final verdict: PASS for this bounded numerical, scientific, and provenance integration review.** No additional experiments were run or are required by this audit. This remains an AI review, not human peer review or an acceptance prediction; final whole-package layout/submission checks are outside this bounded handoff.

Frozen SHA256 values:

- `experiments/build_sequential_extensions.py`: `48769df354d904016b213fc58cd2601739a26e9d4fdeb1bdbded64629d33996c`.
- `paper/sequential_extension_results.tex`: `d36c2712da2d0fc267a2c2312921ceadeb90d2b0b966eed09dcdc9d15c74cfdf`.
- `paper/ustat_extension_appendix.tex`: `570ee8ea1586e8cee8cfcc311bc8c1304db65feeb3fe0df10c2eaad07c58fb8f`.
- `paper/drift_extension_appendix.tex`: `00e728cca72b2c79289b3f03ee1b9911c4fb2063422aa7afc94367de2980daef`.
- `results/sequential_extension_paper_manifest.json`: `1b75d594cc2df096caa9bfd97b1bf832745bf900b971f597830c0b7d217d21b5`.
