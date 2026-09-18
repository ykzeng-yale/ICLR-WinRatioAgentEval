# Frozen informative-delay experiment

Frozen on 2026-09-18 UTC before running or viewing results for this experiment. This is an internal prospective specification, not an external preregistration. The experiment is a synthetic laboratory study; no agent API calls or production users are involved.

## Question and fixed scenarios

Compare naive monitoring of whichever pair scores have completed, valid monitoring of complete enrollment prefixes, and valid worst-case partial-evidence monitoring across enrollment prefixes. The third method is a lower envelope calculation on the latent complete-data betting process; it is **not** claimed to be a calendar-time martingale.

Independent pairs contain one A run and one B run. For both systems, success is independent Bernoulli(0.90). Costs are independent lognormal with log standard deviation 0.45, independent of success. The null uses A/B cost scale ratio 1; the alternative uses ratio 0.55. These are the only two primary scenarios. The comparison uses success first, then lower cost only when both succeed; both failures tie. Cost is decisive when its absolute difference exceeds 5% of the larger cost. Gates require net benefit above zero and success difference above -0.03. Alpha is 0.05 per gate for the single stationary conjunction.

The population targets are success difference zero and net benefit

`theta = 0.90^2 * [Phi((log(.95)-log(r))/(sqrt(2)*.45)) - 1 + Phi((-log(.95)-log(r))/(sqrt(2)*.45))]`,

where `r` is the A/B scale ratio. The null therefore has exactly zero net benefit. Positive costs are measured in synthetic units, not dollars or current prices.

## Enrollment, revelation, and horizon

Enroll 100 pairs at each integer calendar tick 1 through 60, for at most 6,000 pairs and 12,000 initiated agent executions. Each pair's latent outcomes are drawn once and never revised. Outcomes are independent across pairs. Reveal clocks are deterministic functions of the latent outcomes and enrollment time:

| Record | Delay from enrollment |
|---|---|
| A success grade, if successful | 1 tick |
| A success grade, if unsuccessful | 20 ticks |
| B success grade | 1 tick |
| A cost trace, if cost is at most 1 | 2 ticks |
| A cost trace, if cost exceeds 1 | 20 ticks |
| B cost trace | 2 ticks |

This deliberately asymmetric validation pipeline makes failures and expensive A traces slower, even when the two systems have identical outcome laws. The same delay mechanism applies in both scenarios. The fixed endpoint-revelation horizon is 20 ticks; everything is available by tick 80. Calendar ticks are abstract laboratory time units. There are no permanently missing records, timeouts dropped from analysis, or outcome-dependent enrollment rules.

A pair is complete for inference when both success grades are known and, if both succeeded, both cost records are known. Irrelevant costs after a failure do not hold up the complete-prefix baseline. All methods inspect at every integer tick through 80 and require at least 100 scored/enrolled pairs.

## Three frozen decision rules

Each gate uses the same equal mixture of 40 fixed bets from `1e-4` to `0.99/(1+c)`, as in the existing ternary betting implementation. Both gates must pass at the same calendar look. No stake is fitted to results.

1. **Naive completed-only:** Pool all currently complete pair scores, irrespective of enrollment order, and apply the ordinary complete-data betting formula at that selected sample size. This is intentionally invalid for the enrollment-population target under these informative delays.
2. **Complete enrollment prefixes:** Find all fully complete enrollment prefixes on the fixed candidate grid `100,150,...,6000`. Deploy if there exists **one same prefix** where both complete-data betting processes reach 20. This strengthens the latest-completed-prefix baseline by preserving every candidate opportunity when maturity jumps across grid points; it was chosen before the first run to match the partial method's prefix opportunities.
3. **Partial prefix envelope:** For every candidate prefix on that grid that has enrolled, evaluate a worst-case lower e-value for each gate using the outcomes revealed so far. Deploy if there exists **one same prefix** where both lower e-values reach 20. The envelope includes every complete-prefix candidate, hence with these same bets/looks it cannot deploy later than the complete-prefix rule on any sample path. It may be equally slow, and no strict gain is guaranteed. Once every endpoint is revealed, the two valid methods have identical eventual deployment decisions on every repetition; this is also checked.

For a missing success bit enumerate both 0 and 1. The lower success-difference score is `min(A success)-max(B success)`. The hierarchical lower score is the minimum over all success-bit completions: a success discordance determines the sign, two failures tie, and two successes use the known cost sign if both costs are revealed, otherwise allow every sign in {-1,0,1}. These bounds do not exploit a model for informative timing; knowing the DGP does not authorize inferring an unrevealed bit from its delay. Coordinatewise lower bounds suffice even if the two minima do not correspond to the same latent completion.

For nonnegative bets, every partial lower-score factor is no larger than its true full-score factor, all factors are positive, and the weighted product mixture therefore lower-bounds the latent complete-data e-value at that prefix. False partial-envelope deployment entails crossing of a fixed true-null latent gate at some prefix; stationary intersection–union validity controls that event. Neither optional stopping of a partial calendar-time process nor independence between revelation times and outcomes is assumed. General asynchronous adaptive enrollment, interference, or changing agent versions is outside this experiment.

## Fixed execution and reported outcomes

Use 1,000 independent repetitions per scenario, master seed 2026091803 with scenario-specific child seeds. Batch size 25. All methods see the same draws and revelations within a repetition. The code may be optimized without changing these choices; any scientific deviation must be recorded before interpreting results. No scenario is dropped or chosen based on results.

Report deployment probability with 95% Wilson Monte Carlo intervals, cumulative deployment by calendar time, mean capped calendar stopping time and its Monte Carlo standard error, conditional median time among deployments, initiated execution count at stopping (twice the number enrolled), complete pairs, revealed success grades, and revealed cost totals. Nondeployments receive calendar cap 80 and full 12,000-call initiation budget. Known cost at a decision is only a reporting-completeness measure, not total expenditure. Latent outcomes generated after hypothetical stopping are used only to compare procedures fairly, not counted as executions that the stopped procedure would initiate.

Also report paired calendar-time gain of partial versus complete-prefix monitoring, including the fraction of paths with a strict gain; assert the pathwise non-later property. Include an all-enrolled-latest-prefix dilution diagnostic only if separately labeled; it is not one of the three primary methods.

## Verification and reproduction

Run from the project directory:

```sh
python experiments/run_async_experiment.py
```

The standalone script writes only `results/async_*` artifacts. It checks score interval containment, complete-record collapse, cumulative partial e-value domination, shared-prefix gating, and pathwise stopping-time domination. It saves source/core/protocol hashes, software versions, exact parameter values, elapsed runtime, analytic truths, row-level summaries and plot sources. A timing or power result is evidence for this frozen simulation only, not a guarantee of operational savings in an arbitrary agent system.
