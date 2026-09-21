# Independent ablation numerical review — 2026-09-21 17:37 UTC

Reviewed immutable commit `7b4d17ffe8c60b7738a9fd9d4e5cede2d95ba123`, containing delivery `6bdefd1` and corrected analysis `c88ab08`. Scope: independently aggregate committed primary records; inspect seed independence and estimator definitions. No simulation, latent-stream regeneration, band recomputation, model execution, or mutable worker output was used.

## Disposition

**Accept the corrected numerical aggregation and its bounded paired-ablation interpretation.** The independent standard-library reproducer found zero numerical mismatches (tolerance 1e-9) with `ABLATION_ANALYSIS.json`, including paired deployment differences, all observed joint categories, all capped/deciding-both timing summaries, and both A-minus-N contrast changes. This is numerical acceptance of the saved records, conditional on the separately reviewed runtime/provenance identity; it is not an independent regeneration of the experimental paths or a new calibration theorem.

Sixteen coarse original primary files and sixteen completed disabled-arm primary files contain exactly 32,000 matching ADAPTER coordinates: four cells, each 2,000 programs times four trials. There are no duplicate keys, missing or extra expected coordinates, or nondecision-cap inconsistencies. The retained first attempt is not pooled and contributes no extra observations. The original and disabled arms are deliberately paired, not independent replicates.

## Independently reproduced deployment results

Each cell has 8,000 paired trials. Differences below are original minus disabled deployment probability. Intervals are nominal 95% normal-approximation Monte Carlo intervals.

| Cell | Original deploys | Disabled deploys | Paired difference | MCSE | 95% interval |
|---|---:|---:|---:|---:|---:|
| P05N | 26 | 11 | 0.001875 | 0.00048370 | [0.00092697, 0.00282303] |
| P05A | 406 | 381 | 0.003125 | 0.00062406 | [0.00190186, 0.00434814] |
| P10N | 4,212 | 3,116 | 0.137000 | 0.00384457 | [0.12946478, 0.14453522] |
| P10A | 6,762 | 6,726 | 0.004500 | 0.00074836 | [0.00303325, 0.00596675] |

The only nonzero joint categories are DEPLOY/DEPLOY, DEPLOY/NO_DECISION, and NO_DECISION/NO_DECISION. Their counts in that order are P05N (11,15,7974), P05A (381,25,7594), P10N (3116,1096,3788), and P10A (6726,36,1238). There are no disabled-only deployments, retain decisions, or conflicts in these four delivered cells. These observed nested decisions do not by themselves establish universal nesting for other policies or designs.

## The delay-gap question

Define the gap as deployment probability A minus N and its change as original gap minus disabled gap. Independent-cell uncertainty combines the two **paired within-cell difference** variances; it does not treat all four arm means as independent.

| Hierarchy effect | Original gap | Disabled gap | Change | MCSE | 95% interval |
|---|---:|---:|---:|---:|---:|
| 0.05 | 0.04750 | 0.04625 | +0.00125 | 0.00078957 | [-0.00029753, 0.00279753] |
| 0.10 | 0.31875 | 0.45125 | -0.13250 | 0.00391673 | [-0.14017665, -0.12482335] |

At 0.10 disabling these certificate branches **widens**, rather than removes, the A-minus-N gap: the branch intervention changes N deployment much more than A deployment. This contradicts the simple proposed explanation that these branches generate the positive gap at this operating point. At 0.05 the estimated gap change is small and its interval includes zero; this is not evidence of exact equality or absence of a mechanism. Positivity of the within-cell effects alone is insufficient to determine the gap change, but their difference does determine it algebraically. Neither a generic delay explanation nor a particular curve-position explanation has been separately tested by this ablation.

## Timing estimands

Both timing analyses reproduce exactly, including prefix-index versions retained in the JSON evidence. All-trial tick summaries cap nondecision at 2,200; corresponding prefix summaries cap at 2,000. These summarize a decision-time/abstention composite, not observed latency among all eventual deployers.

| Cell | Capped tick difference | MCSE | Both-deciding count | Both-deciding tick difference | MCSE |
|---|---:|---:|---:|---:|---:|
| P05N | -0.200875 | 0.057611 | 11 | -86.727273 | 30.059363 |
| P05A | -3.966125 | 0.588134 | 381 | -33.404199 | 5.391625 |
| P10N | -54.242875 | 1.026519 | 3,116 | -122.784981 | 2.036096 |
| P10A | -26.748250 | 0.852860 | 6,726 | -29.414957 | 0.914095 |

The deciding-both subset is selected jointly by both policy outcomes. It supports a conditional descriptive timing comparison, not an unconditional latency effect. In particular the P05N subset has only eleven observations; its normal-approximation interval must not be presented as a precise inferential result. All saved timing confidence endpoints were reproduced and are available in `numerical_results.json`.

## Monte Carlo sampling unit

Trial-level MCSE is appropriate for this frozen simulation design. `vgen.py:375-386` constructs a separate `SeedSequence` key `(namespace, cell_index, program_index, trial_index)` for every trial, and `vgen.py:421-434` obtains each trial's five arrays from that stream. There is no sampled program-level latent parameter shared across its four trials. `run_ablation.py:282-290` passes both indices separately on every draw. `run_ablation.py:77-90` filters the original coarse cell objects, preserving their original cell indices rather than renumbering the four selected cells. A and N cells have distinct indices and streams, so their paired-difference means use independent-cell variance addition. This relies on the specified independent pseudorandom-stream model; it is not empirical proof of randomness. Grouping independent trials into programs for the familywise error allocation does not itself induce Monte Carlo dependence.

## Acceptance limits and handoff

1. The four operating points were chosen after inspecting the coarse results. Report this as a focused exploratory mechanism intervention on those existing streams, with pointwise Monte Carlo uncertainty; do not present post-selection intervals as simultaneous confirmatory evidence for a whole response surface.
2. The intervention tests the selected partial certificate branches within the synthetic generator and frozen policy. It does not identify a universal cause of informative-delay performance, nor establish transfer to real live agents.
3. The corrected paired analysis, joint table, contrast uncertainties, and timing denominators are accepted. No additional experiment is required to repair their arithmetic. Separate source/provenance review remains authoritative for whether the operator actually executed on these streams; this review does not duplicate it.
4. Full-project readiness is controlled by the root tracker; this report alone awards no additional milestone credit.

Evidence: `reviews/ablation_validation_evidence_20260921_1737/numerical.py` and `numerical_results.json`. The reproducer reads exact Git objects, imports no owner scientific modules, and reconstructs means and sample-standard-deviation MCSE independently.
