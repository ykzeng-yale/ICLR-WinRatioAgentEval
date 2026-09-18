# Theory design and source audit

Prepared September 17, 2026. This is an internal methodological record, not a claim of completed external peer review.

## Scientific target

The core design is disjoint pairs of online arrivals, optionally in a prespecified baseline stratum, randomized AB versus BA. It identifies a symmetric cross-arrival potential-outcome contrast. Conditional independent identically distributed arrivals identify an independent-draw stratum win net benefit. It does not identify the individual live-episode cross-world hierarchical preference. This is distinct from the same-observed-task independent-copy functional, which is identified by conditional arm laws under overlap and is directly measurable with independent offline clone runs. Component difference scores do identify the pair average component treatment effect by algebra.

Default: q=1/2, one episode per system per pair. Hierarchy and component scores lie in [-1,1]. Adaptive orientation probabilities have an inverse-probability score with known bound 1/(2 epsilon). This is not arbitrary adaptive traffic routing: the design still forces one A and one B per pair.

Offline target: task-weighted average preference of independent replicate sets conditional on the same task. The entire task record is the independent unit. All RA times RB comparisons within task reuse runs and cannot be treated as independent.

## Results supplied in paper/theory.tex

1. Definitions: measurable antisymmetric tiers, meaningful tie thresholds, symmetric eligibility rules, tier decomposition, net benefit, win ratio, win odds.
2. Population-priority obstruction: B always succeeds, A fails with epsilon and otherwise wins on cost. Success difference is -epsilon but hierarchical NB is 1-2 epsilon. Near-perfect preference is compatible with a strictly worse primary component.
3. Identification obstruction: uniform {0,1,2} arm marginals permit cyclic live-episode latent potential-outcome couplings with NB +1/3 and -1/3, while both the same-observed-context independent-copy target and cross-arrival NB are zero. This is an instructional example of an established identification obstruction, not a novelty claim.
4. Pair-randomization unbiasedness, including adaptive orientation HT extension and exact component-effect identity.
5. Complete normal-mixture CS proof with predictable bounds: V_n=sum(range_i squared)/4; radius sqrt((V+rho) log((V+rho)/(rho alpha squared)))/n. Under drift it covers a running average conditional effect. For balanced ternary scores V=n. Fixed rho is precommitted. Its rate is sqrt(log n/n), not LIL-optimal.
6. Complete finite-mixture betting validity proof and explicit finite-grid power limitation. Positive stakes must satisfy lambda<1/(1+c) for score range [-1,1] and gate threshold c. A fixed finite positive grid is not universally consistent arbitrarily close to the null. A countable positive-weight grid accumulating at zero is consistent for iid alternatives with positive mean gap.
7. Stationary conjunction: alpha for each of m required gates gives alpha false-deployment control because the null is a union and deployment requires every gate. It does not give simultaneous component coverage.
8. Drift conjunction: for an error defined as ever deploying when any current running-average gate is false, split alpha over components unless one fixed component is violated at every time. The identity of the false gate can otherwise change with time.
9. Delay: displaying only fully observed enrollment prefixes preserves the integer-time simultaneous coverage event, even for a data-dependent displayed index. The original filtration/conditional mean assumptions remain necessary. Completion-order selection and discarding timeouts are not justified.
10. Fixed target stratum weights: independent within-stratum CSs with summed error budgets combine by nonnegative weighting at arbitrary sample counts.
11. Offline unbiased task statistic, task-level variance/CLT and finite-sample CS. Ratio uncertainty only bounded above when the loss-probability lower bound is positive.
12. Gate stopping tail bound plus elementary sequential information lower bound: a narrow guardrail margin can dominate sample size.
13. Comparator sensitivity bound |theta_h-theta_g| <= E|h-g| <= 2 P(h differs from g). Prespecified sensitivity families require simultaneous inference if selected.
14. Shared-seed replication lemma: for R conditionally iid seed clusters (A_r,B_r), off-diagonal comparisons estimate independent-copy preference; all R squared pairs target (1-1/R) theta_ind + (1/R) theta_coupled, with bias bounded by 2/R. For R=4, the diagonal contributes one quarter. The primary empirical contrast was amended to the 12 off-diagonal comparisons per task before the parent inspected the resulting estimates; four diagonal and all 16 comparisons remain sensitivity analyses. This amendment addresses the design assumption, not an observed favorable result.

## Theorems versus novelty

None of the normal-mixture, betting, intersection-union, Horvitz-Thompson, bounded task mean, or information lower-bound arguments is new general statistical machinery. They are supplied to make the proposed application mathematically complete and inspectable. The identification examples and deployment-policy distinction are useful constructions but may not by themselves clear the ICLR methodological novelty bar. The strongest defensible claim is a coherent protocol that reconciles what offline and online designs identify, what a hierarchy means, and what deployment gates actually guarantee, coupled with persuasive real agent evidence. Submission readiness depends on independent review of contribution strength and actual agent experiments.

## Primary sources checked

| Source | Verified content relevant to this paper | Consequence |
|---|---|---|
| Howard, Ramdas, McAuliffe, Sekhon. *Time-uniform, nonparametric, nonasymptotic confidence sequences*. Annals of Statistics (2021). https://arxiv.org/abs/1810.08240 ; HTML https://arxiv.org/html/1810.08240v5 | General nonparametric time-uniform confidence sequences, normal-mixture boundaries, bounded-variable specializations. | Cite as the source of the CS machinery, not a new probability theorem. |
| Waudby-Smith, Ramdas. *Estimating means of bounded random variables by betting*. JRSS B (2024). https://arxiv.org/abs/2010.09686 ; https://academic.oup.com/jrsssb/article/86/1/1/7043257 | Betting constructions for bounded-mean confidence sequences and predictable stakes. | Cite for direct bounded-score tests and CS alternatives. |
| Zhang, Wu. *Sequential Design with Derived Win Statistics*. (2024 preprint). https://arxiv.org/abs/2410.06281 | Sequential win ratio/net benefit, canonical joint distributions, interim analysis/sample-size work. Abstract inspected. | Cannot claim first sequential win-statistic design. |
| Bergemann, Hanson. *Group Sequential Methods for the Win Ratio*. (2026 preprint). https://arxiv.org/abs/2601.22525 ; full HTML https://arxiv.org/html/2601.22525v1 | Group-sequential U-statistic covariance derivation and alpha spending, primarily complete fixed-horizon endpoints. Full text inspected. | Distinguish exact arbitrary-time disjoint-pair bounds from asymptotic all-pairs planned-look methods; compare efficiency fairly. |
| Cai, Hu, Li. *Asymptotic Anytime-Valid Inference for U-statistics*. (May 2026 preprint, v2). https://arxiv.org/abs/2605.14692 | Nondegenerate/degenerate degree-two U-statistic asymptotic CSs, jackknife and spectral methods. Abstract inspected. | Do not claim generic first anytime U-statistic inference. Ours is finite-sample on disjoint scores with potential efficiency cost. |
| Karampatziakis, Mineiro, Ramdas. *Off-Policy Confidence Sequences*. ICML 2021. https://proceedings.mlr.press/v139/karampatziakis21a.html | Nonparametric, nonasymptotic arbitrary-stopping CSs and explicitly a gated deployment application. Proceedings page/abstract inspected. | Guarded deployment with confidence sequences is already in ML literature. |
| Shekhar, Ramdas. *Nonparametric Two-Sample Testing by Betting*. IEEE Transactions on Information Theory (2024). https://arxiv.org/abs/2112.09162 | General sequential two-sample betting, nonexchangeable/time-varying extensions, regret/power links. Abstract inspected. | Distinguish testing distributional equality from estimating a prespecified hierarchy preference, while acknowledging sequential comparison machinery. |
| Podkopaev, Ramdas. *Sequential Predictive Two-Sample and Independence Testing*. NeurIPS 2023. https://arxiv.org/abs/2305.00143 | Predictive betting two-sample tests with drift applications. Abstract inspected. | Adaptive sequential comparison and drift are not new themselves. |
| Even, Josse. *Rethinking the Win Ratio: A Causal Framework for Hierarchical Outcome Analysis*. (2025 preprint, v4 March 23, 2026). https://arxiv.org/abs/2501.16933 ; HTML https://arxiv.org/html/2501.16933v4 | Individual-counterfactual nonidentifiability; identified same-covariate independent-copy and population-copy win targets; matching, distributional regression and semiparametric efficient estimation. Latest HTML inspected after initial v2 access. | Explicitly cite the causal estimand predecessor. The nonidentification example is explanatory, not a newly discovered boundary. |

BibTeX keys expected by theory.tex: howard2021confidence; waudbysmith2024betting; zhang2024sequential; bergemann2026group; cai2026ustatistics; karampatziakis2021offpolicy; shekhar2024betting; podkopaev2023predictive; even2025rethinking.

## Proof-review checklist

- Pairing, assignments, outcome horizon, and eligibility rules are fixed before comparative outcomes.
- Randomization probability conditions on pair context and potential outcomes, not merely a marginal probability.
- Filtration makes score bounds predictable; a context-adaptive propensity cannot silently supply a post hoc narrower range.
- HT signs are oriented A first in both AB and BA cases.
- For changing workload, estimand is a running conditional average; no statement about latest or future effect.
- Use stationary IUT versus drifting simultaneous budgets as separate guarantees.
- Finite-grid betting has validity but only conditionally claimed power; no universal finite-grid consistency claim.
- Repeated experiments and candidate selection require program-level control beyond a single gate conjunction.
- Scalar outcome success difference differs from tier contribution when higher-priority tiers filter comparisons.
- Quantitative results in the manuscript must match the exact implemented boundary, score scaling, stakes, alpha allocation, and sampling unit.
