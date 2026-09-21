# Ablation interval delta review — 2026-09-21 18:17 UTC

Exact change reviewed: `4a9f70423b6abb6e954cd15ee39301f6025ba392`, available in remote main `069c2f5`. Scope is the interval/reporting delta and explicit grid assertion. No simulation or repeated whole-ablation aggregation was run. The independent immutable-row audit at `7b4d17f` remains the underlying numerical validation.

**Disposition: accept the numerical interval changes and strengthened grid check; correct the explanatory overclaims before manuscript integration.** No new experiment is needed.

## Bounded checks

- Independently recomputed all eight marginal Wilson intervals directly from saved event counts and sample sizes using the score formula, rather than calling the owner's `wilson`. All endpoints agree within 1e-14.
- Independently recomputed all four A-minus-N within-arm intervals using the Newcombe hybrid-score formula. For a difference a−b, the lower uncertainty combines (a−L_a) and (U_b−b); the upper combines (U_a−a) and (b−L_b). The source and all saved endpoints have the correct directions and agree within 1e-14.
- Compared the previous and new saved analysis objects: all previous numeric values in the four paired deployment summaries, joint/discordant counts, all timing summaries, and both gap-change summaries are unchanged, with zero mismatches at 1e-12 tolerance. The headline gap changes remain +0.00125 at effect 0.05 and −0.13250 at 0.10, with the previously accepted paired-variance MC uncertainty.
- Loaded the immutable analysis module without invoking its analysis entry point. Injected coordinate dictionaries with the same missing coordinate in both arms and the same extra coordinate in both arms. Both fail the new absolute 2,000×4 grid check before outcome access. The prior independent row audit already established that the delivered grids are complete; this test confirms the strengthened code rejects the intended counterexample.
- Confirmed `_combine` rejects the new marginal-rate objects. Its paired-variance formula remains appropriate for the difference of independent cell-specific paired means. The guard checks for MCSE availability; it is a practical separation of the module's current output types, not a universal semantic type proof.

Preserved evidence: `reviews/ablation_interval_evidence_20260921_1817/check.py` and `result.json` (original scratch in the outer project work/ablation_delta1817 directory). These inspect exact Git objects and run only deterministic arithmetic/coordinate stubs.

## Wording corrections

1. **Convention inconsistency is not proof of statistical invalidity.** `ablation_analysis.py:36-45` and `:135-142`, the commit explanation, and `ABLATION_FINDING.json/CORRECTIONS_v2` describe the earlier normal intervals as simply wrong and imply that two stated interval methods for the same count are inherently a defect. Wilson is a sensible choice for marginal proportions, particularly at low counts, and standardizing it improves this package. Newcombe is likewise a defensible convention for independent proportions. But a normal approximation is not inherently erroneous merely because another section used Wilson/Newcombe, and symmetry alone does not establish miscoverage. The former intervals were labelled normal approximations; no finite-sample coverage study of them is supplied by this delta. Recommended description: “Standardized marginal intervals to Wilson and independent-proportion contrasts to Newcombe, matching the other panel reports; paired estimates and their MC uncertainty are unchanged.” Do not call a confidence interval “the true interval.”

2. **One new label is broader than its input warrants.** `_mc` now always emits `interval_method = "normal on the paired mean"` (`:129`), but it also receives the original-arm and disabled-arm capped tick values separately (`:265-266`). Those two summaries are single-arm means. Their arithmetic is unchanged and valid as an approximate mean interval; use “normal approximation for a sample mean” in the generic helper, or parameterize the label so only paired differences say paired. This is metadata repair, not a numerical defect.

3. Retain the earlier scientific scope: curve-position heterogeneity remains a possible explanation, not a tested one. The ablation's positive within-cell deployment effects do not by themselves explain the A-minus-N advantage; their difference nevertheless determines the gap-change estimator. The current interval convention change adds no evidence for either causal claim.

## Accepted interpretation

Use the updated Wilson and Newcombe secondary intervals consistently. Keep the accepted paired means, sample-variance MCSE, and independent-cell gap-change uncertainty unchanged. These are pointwise Monte Carlo uncertainty summaries of the selected synthetic design, not proof of universal method validity or real-agent performance. The reporting corrections do not require a rerun or change the earlier bounded acceptance of the experimental records.
