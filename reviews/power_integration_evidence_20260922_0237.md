# Evidence for power/ablation integration — 2026-09-22 02:37 cycle

## Acceptance and reproduction scope

This is a bounded integration audit of saved summaries and earlier independent raw-record reviews through `402d3f7`, with corrected ablation interval labels at `94c62f7`. No simulation, reference-band regeneration, model call or scientific recollection was performed. Root owns manuscript changes and final release acceptance.

Exact numerical inputs read from Git at `94c62f7`:

- `results/live_ab_validation_v2/powercurve_fine_20260921/COMBINED_CURVE.json`; SHA-256 `4ef67baa419716425661fd61d30f564d8348e1fda932c3c505d49417ce84a2d6`.
- `results/live_ab_validation_v2/ablation_20260921/ABLATION_ANALYSIS.json`; SHA-256 `3498a31bddd7db0005da95efa43fe080e4d6f8483c48f847d98f863c3edc11c7`.

The underlying accepted evidence is: coarse delivery `0c17857`, independently aggregated in `reviews/power_scientific_review_20260921_1514.md`; fine `2c09a16`, independently aggregated in `reviews/fine_power_scientific_review_20260921_1550.md`; ablation data `6bdefd1`, analysis/readback `c88ab08`, accepted descriptively in `reviews/ablation_root_disposition_20260921_1737.md`; interval changes reviewed in `reviews/ablation_interval_delta_20260921_1817.md`. `94c62f7` distinguishes single-arm timing means from paired differences. None of these converts the exploratory studies into confirmatory evidence.

In this audit, all 22 marginal power Wilson intervals independently reproduce from saved counts using z=Phi^{-1}(.975), maximum endpoint error 1.11e-16. Four ablation paired means and sample-variance MCSE independently reproduce from saved discordant counts; both difference-of-gap estimates and MCSE reproduce by adding independent cell-specific paired variances. This uses saved summaries; the prior reviews, not a repeated raw-row pass this cycle, supply independent coordinate/hash/row validation.

## Suggested supplementary Table P1: exploratory deployment probabilities

Setting: hierarchy effect mu_h varied, success effect held at +0.20, N=2,000 enrolled pairs per trial. N and A denote non-informative and informative delay cells with distinct random streams. Each table entry is deploy count/trials; percentage [pointwise 95% Wilson Monte Carlo interval]. Coarse: namespace3, 2,000 programs x4 trials per cell; fine: namespace4, 1,000 programs x4. Fine rungs were chosen after coarse results. Do not pool stage denominators, append T1 nulls as if they were this same law family, or call the sampled grid a continuous MDE estimate.

| mu_h | Stage | N: count; percent [95% MC interval] | A: count; percent [95% MC interval] |
|---:|---|---|---|
| 0.05 | coarse(ns3) | 26/8,000; 0.3250 [0.2219, 0.4758] | 406/8,000; 5.0750 [4.6152, 5.5779] |
| 0.06 | fine(ns4) | 66/4,000; 1.6500 [1.2991, 2.0937] | 556/4,000; 13.9000 [12.8625, 15.0068] |
| 0.07 | fine(ns4) | 231/4,000; 5.7750 [5.0936, 6.5412] | 1,147/4,000; 28.6750 [27.2945, 30.0964] |
| 0.08 | fine(ns4) | 639/4,000; 15.9750 [14.8723, 17.1430] | 1,885/4,000; 47.1250 [45.5816, 48.6739] |
| 0.09 | fine(ns4) | 1,284/4,000; 32.1000 [30.6710, 33.5634] | 2,681/4,000; 67.0250 [65.5524, 68.4650] |
| 0.10 | coarse(ns3) | 4,212/8,000; 52.6500 [51.5549, 53.7426] | 6,762/8,000; 84.5250 [83.7159, 85.3009] |
| 0.11 | fine(ns4) | 2,918/4,000; 72.9500 [71.5518, 74.3041] | 3,751/4,000; 93.7750 [92.9834, 94.4826] |
| 0.12 | fine(ns4) | 3,501/4,000; 87.5250 [86.4648, 88.5131] | 3,911/4,000; 97.7750 [97.2700, 98.1883] |
| 0.15 | coarse(ns3) | 7,969/8,000; 99.6125 [99.4505, 99.7269] | 7,999/8,000; 99.9875 [99.9292, 99.9978] |
| 0.20 | coarse(ns3) | 8,000/8,000; 100.0000 [99.9520, 100.0000] | 8,000/8,000; 100.0000 [99.9520, 100.0000] |
| 0.30 | coarse(ns3) | 8,000/8,000; 100.0000 [99.9520, 100.0000] | 8,000/8,000; 100.0000 [99.9520, 100.0000] |

The saved data comprise 80,000 coarse and 48,000 fine trial paths, represented by 240,000 and 144,000 construction records respectively; these construction counts are not additional independent trials. At the sampled settings the observed probabilities straddle 50% between .09/.10 for N and .08/.09 for A. This is not a 95% confidence bracket for a continuous first crossing. The largest observed A−N difference among the sampled rungs is at .09; it is a selected descriptive maximum, not a global optimum.

## Suggested supplementary Table P2: matched certificate ablation

Same namespace3 coordinates P05N/P05A/P10N/P10A as the original coarse arm, 8,000 pairs of algorithm outputs per cell. Disable only the two elapsed-cost certificate branches in exactly-one-revealed-success states; preserve the specified failure constraints, both-final scores, pending bounds and success intervals. Report original-minus-disabled differences. Rates below are percentages; differences and their intervals are **percentage points**, using pointwise normal MC uncertainty of the paired mean.

| Cell | Original deploys/8,000 | Disabled deploys/8,000 | Original−disabled pp [95% MC interval] |
|---|---:|---:|---:|
| P05N | 26 | 11 | 0.1875 [0.0927, 0.2823] |
| P05A | 406 | 381 | 0.3125 [0.1902, 0.4348] |
| P10N | 4,212 | 3,116 | 13.7000 [12.9465, 14.4535] |
| P10A | 6,762 | 6,726 | 0.4500 [0.3033, 0.5967] |

| mu_h | Original A−N pp [Newcombe 95%] | Disabled A−N pp [Newcombe 95%] | Original gap−disabled gap pp [paired-variance 95%] |
|---:|---:|---:|---:|
| 0.05 | 4.7500 [4.2661, 5.2634] | 4.6250 [4.1666, 5.1175] | 0.1250 [-0.0298, 0.2798] |
| 0.10 | 31.8750 [30.5155, 33.2172] | 45.1250 [43.7752, 46.4467] | -13.2500 [-14.0177, -12.4823] |

Within-cell contrasts are paired; the A/N cell contrast is unpaired because those seed streams are distinct. The gap-change uncertainty combines independent cell-specific paired variances, not two independent armwise errors. There are 32,000 unique matched coordinates, not 64,000 independent ablation samples. Both disabled attempts nevertheless count toward execution accounting (64,000 evaluations); their 16 shard payloads are identical, independently checked in the prior provenance review. No reverse discordance or retention was observed, but that does not prove first-decision monotonicity generally.

## Minimal accurate interpretation

The synthetic power panel shows nonzero intermediate detection and saturation at larger effects in this finite family. In the matched diagnostic, retaining certificates increased observed deployments in all four cells. However, at mu_h=.10 disabling them widened the informative-minus-non-informative gap from 31.875 to 45.125 percentage points; the original-minus-disabled gap change was −13.250 pp [−14.0177,−12.4823]. Thus the proposed explanation that these certificates account for the A>N advantage is not supported by the two diagnostic rungs. At .05 the gap-change estimate is +0.125 pp [−0.0298,0.2798], so its direction remains unresolved. The result concerns a selected synthetic diagnostic, not live-agent performance, universal harmfulness or usefulness of delay, or a failure of the enclosure theorem. Curve-position heterogeneity is a possible explanation, not a tested mechanism.

If mentioning CPREFIX: at .10 its A−N difference is 1.475 pp, nominal Newcombe95%[0.023953,2.925187]. “No advantage,” “equivalence,” or “rules out a generic delay effect” are unsupported. Final marginal unresolved fractions do not establish identical information histories. Timing differences are simulated capped ticks, influenced by both decision probability and decision speed; they are not measured wall-clock savings. Omitting timing from the minimal table avoids the extra conditioning/units burden.

## Provenance qualifications that must accompany integration

- **Coarse:** `powercurve_20260921/PROVENANCE_ADDENDUM.json` supplies retrospective driver/law hashes and atom definitions; original receipts omit the then-untracked execution driver and runtime law module. Their historical executed bytes are not contemporaneously established. The first failed coarse attempt was deleted; attempt identity, exact timestamps, failed-state source hashes, resource use and row counts remain unknown. Successful-record validation does not recover that history.
- **Fine:** `powercurve_fine_20260921/ERRATUM_v1.json` preserves the original namespace contradiction: data/plan use4 while pin/exposure fields said3. Driver/law binding is retrospective here too. The retained first failed fine attempt is distinct from the missing coarse failure. Rungs are outcome-informed, even though the fine-stage draws are separate.
- **Ablation:** the original arm inherits the coarse qualifications. The corrected disabled attempt contemporaneously pins its 22 sources/two configs; the earlier attempt's exact driver blob is not recovered, and its output monitor watched the wrong directory, so continuous first-attempt output-cap compliance is not established. Both attempts remain archived and count in resources; no independent sample is gained by rerunning identical coordinates.
- Numerical acceptance is descriptive and bounded. The above provenance limits need not trigger another collection, but they must not be hidden under “fully prospectively pinned/reproduced.” Neither paper integration nor these summaries establish a live feasibility study.

The minimum package is these two tables, a short interpretation paragraph, and an explicit provenance paragraph referring to the archived addendum/erratum and attempt ledgers. No new scientific experiment or reviewer gate is requested by this audit.

## Independent manuscript claim review — completed integration draft

Read `arxiv/additions/power_diagnostics.tex` and the current `t1_validation.tex` diff against the accepted evidence above. No paper or builder edits and no simulations performed. Reviewed source SHA-256:

- `arxiv/additions/power_diagnostics.tex`: `41ed6414c7434c1ab13bd7a6c13635dd00dfacbd0e55fa4ac9055aa0c388ba96`.
- `arxiv/additions/t1_validation.tex`: `41be3398b04b30a1768f06dc45355a53242544db539c44532802083763b5515d`.

**Disposition: no blocking numerical, scope, or causal-interpretation error found in this draft.** The five coarse count rows and four ablation rows agree with saved accepted counts. The two fine proportions and four reported Wilson endpoints round correctly. The gap changes +0.125 and −13.25 percentage points and their reported intervals round correctly and retain the correct original-minus-disabled sign. The text correctly distinguishes 32,000 unique matched trial coordinates from 64,000 disabled-arm execution evaluations across two attempts, without doubling the independent sample.

The independent A/N versus within-trial pairing distinctions, outcome-informed fine stage, separate T1 law family, absence of a continuous-MDE/confidence-bracket claim, pointwise MC interval scope, and measured-gap widening interpretation are appropriate. It does not claim that the certificate diagnostic refutes the enclosure theorem, supports a universal delay benefit, or provides new live evidence. The T1 cross-reference edit is accurate and leaves its accepted calibration statements intact. The provenance paragraph explicitly preserves the missing coarse attempt and retrospective coarse/fine source binding; paper inclusion does not repair these facts.

Two small precision improvements are recommended, without reopening acceptance:

1. In the ablation definition, specify “the two elapsed-cost narrowing branches for exactly-one-revealed successful states,” and add that revealed-failure constraints, both-pending bounds and both-final scores are unchanged. The current wording is not false but is less precise about the isolated intervention than the underlying accepted design.
2. Replace “Original failed-attempt/provenance records remain linked” with “Surviving failed-attempt records and provenance addenda remain linked.” This avoids any implication that the deleted coarse failure record was recovered. The immediately preceding paragraph already reports its loss correctly.

The all-22-point figure is consistent with the saved combined-curve inventory specified by root; visual/layout and packaging validation are root's separate checks. The prose's release-content claims depend on final package inspection, which was outside this claim-only review. No new experiment or additional scientific gate follows from these editorial suggestions.
