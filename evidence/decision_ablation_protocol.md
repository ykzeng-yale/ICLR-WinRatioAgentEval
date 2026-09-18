# Frozen decision-objective and grader-error ablations

Frozen 2026-09-18 UTC before executing or inspecting this study's outputs. This compact CPU-only extension is an internal prospective specification, not a public preregistration or a production experiment. No model calls are required. It addresses decision objectives and measurement sensitivity rather than claiming optimal power.

## A. Different decision objectives on the same latent outcomes

Reuse the six frozen stationary independent-pair laws in `experiments/run_simulations.py`, without modifying that source or its results. Compliance and success are independent Bernoulli draws; costs are independent lognormal with log standard deviation 0.45. Hierarchy: compliance, success, then cost when both comply and succeed; cost differences within 5% of the larger cost tie.

Compare the following six level-0.05 directional betting decisions. Each fixed conjunction uses alpha 0.05 per gate under stationary intersection–union validity. All methods see identical pairs and have identical monitoring opportunities.

| Rule | Its own objective |
|---|---|
| Success superiority only | Success-rate difference >0 |
| Component guardrails only | Success difference >-0.03 and compliance difference >-0.01 |
| Guarded win | Hierarchical net benefit >0 and both component guardrails |
| Weighted utility superiority | Mean utility difference >0 |
| Guarded weighted utility | Mean utility difference >0 and both component guardrails |
| Guarded efficiency | Mean bounded cost-efficiency difference >0 and both component guardrails |

The fixed per-episode utility is `0.8*success + 0.1*compliance + 0.1/(1+cost)`. All three component weights are nonnegative and sum to one. Efficiency is `1/(1+cost)`. These choices fix an illustrative value system and a synthetic cost scale of one; they are not learned, optimized, or claimed universally meaningful. The utility gives resource value even to failed episodes, unlike the hierarchy's resource eligibility. Each contrast lies in [-1,1], so the same fixed-stake bounded-mean construction applies. An ordinary weighted utility is a different estimand, not an inferior estimator of net wins.

Report each decision's population target, whether its own objective is true, and whether the distinct guarded-win deployment region is true. Calling a component-only or weighted decision positive outside the guarded-win region does not by itself show a statistical type-I error for that rule. Compare interpretability and operational consequences explicitly, not as if all six tested the same null.

Provide a descriptive population Pareto table on success probability, compliance probability, and mean untransformed cost. Label dominance, equivalence, or tradeoff from exact DGP quantities. This is not a data-estimated Pareto-front confidence procedure. Compute expected bounded efficiency by deterministic Gauss–Hermite quadrature and check 80 versus 160 nodes; raw mean lognormal cost is analytic.

## B. Grader noise changes the measured target

Compliance and cost remain correctly recorded. A success grader independently flips true failures to successes with a false-positive probability and true successes to failures with a false-negative probability, conditional on arm and true success. The probabilities below are frozen; conditional flip rates differ from overall error prevalence.

| Scenario | True (success A, success B, cost scale A/B) | A (FP,FN) | B (FP,FN) |
|---|---|---|---|
| Identical agents, nondifferential noise | (.75,.75,1) | (.05,.05) | (.05,.05) |
| Success harm, favorable differential grading | (.71,.75,.4) | (.05,0) | (0,.05) |
| Efficiency gain, adverse differential grading | (.75,.75,.55) | (0,.05) | (.05,0) |
| Larger success harm, nondifferential noise | (.65,.75,.4) | (.05,.05) | (.05,.05) |

Compliance is .995 in both arms for all four cases. Measured success probability is `p*(1-FN)+(1-p)*FP`. Because noise and costs are conditionally independent by construction, substitute measured probabilities into the existing exact hierarchical target formula. Report true and measured component differences/net benefits separately.

Compare (i) oracle guarded win using the latent true labels, (ii) guarded win using measured labels, and (iii) a conservative bound-aware measured-label rule. The oracle is available only in simulation and is not a deployable real-world baseline.

For the bound-aware rule, suppose an external guarantee bounds each arm's unconditional misclassification probability by `epsilon_a=max(FP_a,FN_a)`. Put `epsilon=epsilon_A+epsilon_B`. Then the absolute success-difference bias is at most epsilon, and the absolute hierarchical net-benefit bias is at most `2*epsilon`, since a pair's sign changes only if a success label is wrong. Use measured thresholds `net benefit >2*epsilon`, `success difference >-0.03+epsilon`, and unchanged compliance >-0.01. These are sufficient conditions for the true guarded region under the stated error bounds, not necessary conditions, and may be very conservative. The known error envelope is a simulation assumption, not an estimated or validated grader guarantee.

A calibrated test for the measured-label target can make operationally wrong decisions about true task success when the grader is differential. This is a measurement problem, not a failure of optional-stopping validity for the measured target. No claim of correction for arbitrary adversarial or dependent grading is made.

## Execution, output, and limits

Use 500 independent repetitions per scenario, at most 6,000 pairs, monitor at 100 and every 100 pairs thereafter, 40 geometric stakes from 1e-4 to `0.99/(1+c)`, and seed 2026091804 with distinct deterministic scenario child streams. Every conjunction must pass at the same current look; no retained crossing or prefix envelope is used in this study. All rules share the same observation budget and look schedule. This is a decision ablation, not a high-precision error-calibration study.

Report rates with 95% Wilson Monte Carlo intervals, mean capped pair use with Monte Carlo standard errors, and conditional median pair use among positive decisions. Nondecisions receive the 6,000-pair cap. Resource savings across different objectives must not be treated as a matched-power efficiency comparison.

Run from the project directory:

```sh
python experiments/run_decision_ablations.py
```

The standalone script writes only `results/decision_ablation_*` artifacts. It records analytic/quadrature truths, grading parameters, seed, software versions, source/core/protocol hashes, and numerical checks. All ten scenarios remain in the output. Figure descriptions must label the different objectives and measured-versus-true distinction. Any later broader sensitivity or tuning analysis must be marked as a separate extension.
