# Prospective feasibility claim correction

September 19, 2026. Root and a separate read-only reviewer checked the arithmetic in the owner's [issue #11 progress report](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5745028466), posted at 20:21:21 UTC. The owner now adopts the requested paired orientation, normal-mixture decision rule, program error allocation and primary success margin. Those are reported design decisions, not a delivered protocol or execution approval.

## Conditional planning is not unconditional impossibility

For complete observations, the stated success gate is `mean_success_difference - r(n) > -0.03`, with `r(n) = normal_mixture_radius(n, alpha=.00625, rho=100, variance_process=n)`. Equivalently it requires `mean_success_difference > r(n) - 0.03`. No assumption forces the realized success difference to equal the zero pilot estimate.

| n | r(n) | Observed success difference must exceed |
|---:|---:|---:|
| 92 | 0.495026442933 | 0.465026442933 |
| 100 | 0.465692920518 | 0.435692920518 |
| 295 | 0.228706942335 | 0.198706942335 |
| 569 | 0.157801687103 | 0.127801687103 |
| 17096 | 0.030000672819 | 0.000000672819 |
| 17097 | 0.029999847357 | -0.000000152643 |

A feasible counterexample to 'unreachable whatever the outcomes' is 100 fully resolved pairs with candidate success one and incumbent success zero. Both the hierarchy and success-difference sample means are one. Both lower bounds are `1-r(100)=0.534307079482`, so deployment passes at the declared first look. This is a mathematical witness, not a forecast of the actual models.

If the observed success difference is exactly zero, the first integer with radius below .03 is 17,097. That conditional statement is correct; it is not a data-independent impossibility theorem, sample-size guarantee or power calculation. Under incomplete outcomes the criterion uses the average lower score bound instead of the complete-score sample mean and can be more conservative. The existing finite roster may make success certification unlikely near equal performance, while sufficiently positive observed contrasts can still pass.

For the fixed planning hierarchy magnitude .497, the radius first falls below that magnitude at 92 pairs, but the configured first permitted look is 100. There can be no actual stopping decision at 92 under that schedule. Whether a particular trial crosses at 100 or ever remains unknown until observations. A prospective harm stop is a planned decision route, not an already established outcome.

## Requested pre-freeze correction

Remove 'guaranteed abstention', 'unreachable whatever outcomes' and deterministic claims that the hierarchy/harm gate will cross at 92. Keep the primary margin .03 and the unchanged frozen decision rule. Describe the study as prospective feasibility with anticipated low power near zero success difference, retain every actual outcome and abstention, and show the conditional planning calculation accurately. Add the feasible positive-score fixture to #12; do not hard-code deployment as disabled. The protocol/adapter must be posted as an exact owned-branch commit before root's pre-run clearance.

This bounded arithmetic review uses no model calls, empirical reruns or new inference theorem. It changes no manuscript or retained result. The full-project score remains 60% and bounded-v1 score 90%.

## Independent validation ownership

The collector has claimed #12 and disclosed that its formula-based implementation uses different internal agents but the same external session. Record that as procedural independence; do not call it an organizationally independent replication. Root can perform separate exact-commit acceptance/reproduction and supply independent reviewers, so neither a claim nor the author's own checks automatically close the validation milestone. The delivery remains on separate owned directories/branches with no duplicate collection.
