# Independent fine-power scientific review

Exact snapshot `2c09a167afd3bdfa404512d668aa1b2b5502fe1b`. Read all committed fine-panel primary blobs through `git show`; no simulation, model, native-reference calculation, or mutable worker output was used. This review concerns numerical reproduction and interpretation, not authorization history or full execution provenance.

## Independently reproduced observations

There are **24 primary files, 144,000 unique construction records, 48,000 trial paths, and 12,000 programs**. No duplicate `(cell, construction, program, trial)` was found; every program/construction contains trial indices `{0,1,2,3}`. Each fine cell has 4,000 trials per construction. All 12 fine ADAPTER deployment counts and Wilson intervals in `COMBINED_CURVE.json` reproduce independently (interval tolerance `1e-12`).

| Hierarchy mean | N deploy / 4,000 | A deploy / 4,000 |
|---:|---:|---:|
| .06 | 66 (.01650) | 556 (.13900) |
| .07 | 231 (.05775) | 1,147 (.28675) |
| .08 | 639 (.15975) | 1,885 (.47125) |
| .09 | 1,284 (.32100) | 2,681 (.67025) |
| .11 | 2,918 (.72950) | 3,751 (.93775) |
| .12 | 3,501 (.87525) | 3,911 (.97775) |

The per-rung denominators are correctly kept distinct from the coarse panel's 8,000 trials per cell. Comparing cell-specific probabilities across matching laws/horizon is meaningful; adding counts from different effects or namespaces into one denominator would not be. The emitted ADAPTER flags include one hierarchy miscoverage in P12A and none in the other fine cells; no success miscoverage is recorded. These are reproduced flags, not regenerated latent-band coverage checks.

## What the 50% statement supports

Adjacent **observed grid estimates** straddle 50% at N `.09/.10` and A `.08/.09`. The relevant marginal Wilson 95% intervals are:

| Point | Estimate | Marginal MC interval |
|---|---:|---:|
| N .09, fine | .32100 | [.30671, .33563] |
| N .10, coarse | .52650 | [.51555, .53743] |
| A .08, fine | .47125 | [.45582, .48674] |
| A .09, fine | .67025 | [.65552, .68465] |

Thus the empirical straddling is not merely caused by a point estimate sitting infinitesimally either side of 50%. It is reasonable to report: **“The sampled estimates crossed 50% between .09 and .10 under N, and between .08 and .09 under A.”** The observed estimates are nondecreasing over the displayed combined grid.

The stronger assertion that the *true continuous first 50% crossing* lies in `( .09, .10 ]` or `( .08, .09 ]` needs qualifications:

- Monotonicity of estimated values at the sampled points is not a proof that the true decision-probability function is monotone between or before them. If a true minimum crossing is intended, state the monotonicity assumption or establish it for this full joint-law/monitor family. The paper can avoid that claim by using the observed-grid wording above.
- These are **marginal** Monte Carlo intervals, not a jointly constructed confidence set for a crossing. Do not label the reported brackets “95% confidence brackets,” exact thresholds, or MDEs.
- Fine locations were chosen after observing the coarse transition. The new namespace separates random streams; it does not make the combined design a pre-specified confirmatory threshold study. Report it as an exploratory refinement, and preserve the coarse/fine stages and selection rationale. Pointwise fine-stage estimation is still useful under its fixed collection rule; selection does not invalidate the counts.

The same distinction applies to “maximum advantage at .09”: `.34925` is the **largest observed A−N difference among the evaluated rungs**, not an identified global maximum over the continuum. Saturation at the larger sampled effects explains why the observed rate difference is small there; it does not resolve the causal source of the intermediate advantage. The prior review's cost-narrowing and CPREFIX limitations remain unchanged.

## Provenance addendum: bounded checks

The coarse-panel `PROVENANCE_ADDENDUM.json` correctly labels the added source binding as retrospective. I independently recomputed the two listed hashes from the stated `35ab9d1` blobs: both `run_powercurve.py` and `vpowercurve.py` match. Every supplied coarse atom table sums to 10,000 and yields the claimed hierarchy mean (.05/.10/.15/.20/.30) and success mean +.20. These checks make the recovered definitions inspectable; they do **not** prove those bytes were contemporaneously frozen.

The addendum explicitly acknowledges deletion of the first failed coarse attempt and leaves its original ID, timestamps, failed-state hashes, usage and row counts unknown. Retain those unknowns. They cannot be replaced with zero counts or repaired by the later successful panel; this scientific review does not infer missing first-attempt observations or verify the author's account of the deletion. The preserved fine failure is a separate record, not a reconstruction of the missing coarse attempt.

## Disposition

Accept the **independently reproduced fine-panel counts, marginal uncertainty, and descriptive sampled-grid straddling**, subject to root's separate provenance assessment. Narrow continuous-threshold and global-maximum wording as above. No extra experiment is needed for that limited acceptance, and this report neither authorizes nor requests another ladder. The study remains a synthetic, adaptively refined power illustration; it is not proof of causal cost-narrowing benefit, live production performance, or universal calibration.

Evidence: outer workspace `work/fine_scientific_1550/check.py` and `result.json`. All primary counts and the provenance hash/law checks derive from immutable committed material.

Archived [scripts and machine-readable evidence](fine_validation_evidence_20260921_1550/).
