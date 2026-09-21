# Independent power-panel and mechanism review

Snapshot: `0c17857f6b0eb6a37f222a264294cfc9fe65b7e7`. Independently read all 40 committed `powercurve_20260921/shard_*/primary_rows.csv.gz` blobs using `git show`. No simulation, model, native reference, or mutable worker output was used. Root separately reviews the design chronology/provenance and integration.

## Accepted empirical subset

The committed rows contain **240,000 unique construction records**, representing 80,000 trial paths, 20,000 programs, and ten cells. Each cell/construction has 8,000 trials; every program has trial indices `{0,1,2,3}`. No duplicate coordinate was found. All construction-specific deployment counts in `MECHANISM_TEST.json` reproduce exactly.

ADAPTER correct-deployment counts, at the recorded horizon and success mean +0.20:

| Hierarchy mean | N: deploy / 8,000 | A: deploy / 8,000 |
|---:|---:|---:|
| .05 | 26 (.00325) | 406 (.05075) |
| .10 | 4,212 (.52650) | 6,762 (.84525) |
| .15 | 7,969 (.996125) | 7,999 (.999875) |
| .20 | 8,000 (1.00000) | 8,000 (1.00000) |
| .30 | 8,000 (1.00000) | 8,000 (1.00000) |

This establishes intermediate detection probabilities in this synthetic law family and stronger observed ADAPTER detection under A at the intermediate rungs. It does not identify a continuous curve, a precise minimum detectable effect, production performance, or causal attribution to a particular enclosure component. Distinct cell stream keys mean A-versus-N is an **unpaired Monte Carlo contrast**, even though constructions within each trial are paired. These namespace-3 data must remain distinct from T1's namespace-0 calibration panel.

## CPREFIX does not establish “no advantage”

At hierarchy mean .10:

- CPREFIX A: `5,462/8,000 = .68275`.
- CPREFIX N: `5,344/8,000 = .66800`.
- Difference A−N: **.01475** (1.475 percentage points).
- Independent-binomial Monte Carlo SE: **.00740252**.
- Nominal marginal 95% Newcombe interval (Wilson-component unpaired difference): **[.00023953, .02925187]**.

For comparison, ADAPTER A−N is **.31875**, with marginal Newcombe interval **[.30515466, .33217151]**. The CPREFIX contrast is much smaller, but “CPREFIX confirms cleanly—no advantage” is unsupported. Overlapping armwise Wilson intervals do not imply that the difference is zero. This is also a post-hoc, multiple-comparison mechanism assessment: the nominal CPREFIX interval is not a multiplicity-adjusted finding or an equivalence test. It warrants the precise descriptive statement, not either a definitive positive mechanism claim or a definitive no-effect claim.

Accordingly, retract `MECHANISM_TEST.json`'s “CPREFIX rules out a generic delay effect.” A construction that ignores pending outcomes can still have delay-dependent stopping-time information and completed-prefix evolution. It is not a negative control known to be invariant under changing the delay/outcome association. The data do not establish that only the pending-cost pathway can respond.

## Cost narrowing remains a hypothesis

The higher recorded final cost-narrowed fraction is real: at .05 the ADAPTER means are A `.008834625` and N `.0063989375`, approximately 38% higher under A. Final unresolved fractions are close (A `.02533175`, N `.0253426875`). This is consistent with the proposed explanation but cannot identify it.

Three corrections are necessary:

1. Similar marginal fractions at the finalization tick do not establish equal information trajectories at earlier deciding ticks, equal identity of resolved pairs, or equal score composition among those pairs. The A/N cells use separate random streams, so “the same pairs resolve either way” is not a fact established by these records. Even mean certified counts are not literally identical to four decimal places: at .05 they are `1949.3365` versus `1949.314625`.
2. The reported cost-narrowing average is measured at finalization, while the deployment outcome is determined at first crossing. A final average is not a demonstrated mediator of an earlier crossing; nor does a count of narrowed intervals quantify the total amount/direction of bound tightening.
3. Changing the delay/outcome association changes the observable information process. The panel does not hold that process fixed while changing only cost narrowing. Thus the strong prose asserting that the information gain explains the deployment increase goes beyond what the experiment isolates. Keep “consistent with a cost-narrowing contribution; causal contribution not identified.”

No additional experiment is required to retain the valid descriptive power findings. A causal mechanism claim would require a separately justified analysis/design that actually isolates that component; this review does not authorize or request a new run.

## NAIVE and cross-panel comparison

T1 independently demonstrates that NAIVE can make false deployments under the specified informative-delay null. That remains a valid warning against interpreting high alternative deployment rates alone as calibrated power. However, concatenating T1 C4 at hierarchy mean zero with this power ladder is **not a same-family curve**: C4 has success mean +.25, whereas this ladder has +.20 and different atom weights. The N-side zero point taken from C1 is even less comparable (success mean zero). The namespaces are not the sole difference. Report T1 as a separate invalid-null example, not a “decisive zero-to-positive curve” or proof that the entire A−N alternative difference is bias. In favourable cells a deployment is substantively correct even if the inference procedure fails null control elsewhere; the latter limits its interpretation as reliable power, not the arithmetic deployment probability.

The source statement that T1's null cells “establish coverage or validity” also needs the previously agreed qualification: the finite synthetic panel supplies calibration evidence under its tested laws; it does not prove universal validity or certify the added family automatically.

## Disposition

Accept the independently reproduced **limited empirical power counts and contrasts**, conditional on root provenance/design acceptance. Do not accept the report's strong mechanism-confirmation, CPREFIX-no-effect, generic-delay-exclusion, or cross-family zero-effect-curve claims. Repair those interpretations before paper integration; do not interrupt, repeat, or expand experimentation merely to obtain a preferred result.

Independent evidence: outer workspace `work/power_scientific_1514/check.py` and `result.json`. Wilson intervals and Newcombe contrasts were recomputed from committed counts. Latent bands and reference files were not regenerated or independently validated in this review.

Archived scripts and machine-readable outputs: [audit evidence](power_validation_evidence_20260921_1514/).
