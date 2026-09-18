# Round 3: independent empirical audit of asynchronous monitoring

Audit date: 2026-09-18 UTC. Scope: the frozen asynchronous experiment, its implementation and numerical outputs, and their agreement with the asynchronous theory and manuscript. This reviewer did not design or write the experiment implementation, but **did author the asynchronous theory appendix**. This is therefore an independent implementation and results audit, not an independent review of that theory's originality or proof development. No shared source, data, results, or manuscript files were edited during this audit.

## Decision

**Implementation and numerical reporting pass, subject to the explicitly narrow simulation scope.** I found no material mismatch between the frozen protocol, simulated latent model, partial-score construction, deployment rules, numerical summaries, and the corresponding theorem. The study demonstrates an informative-telemetry failure mechanism and an instance of earlier valid decisions. It does not by itself establish operational benefit in a real agent service, calibrated performance across a broad asynchronous model class, or methodological novelty sufficient for ICLR.

One minor manuscript correction remains: the main-text limitations paragraph refers to “two deliberately simple measurement pipelines.” There is **one** fixed asymmetric measurement pipeline and **two outcome scenarios**. Suggested replacement: “one deliberately simple measurement pipeline and two outcome scenarios.” This does not affect any result.

## Snapshot and verification performed

Read `experiments/run_async_experiment.py`, the reused score/betting implementation, `evidence/async_experiment_protocol.md`, `paper/asynchronous.tex`, `paper/async_results.tex`, `paper/async_appendix.tex`, the relevant main-text claims, and all asynchronous CSV/manifests.

Source hashes at the audited snapshot:

- Experiment: `4436abe428bf4b00c896c2f3b4682a0399d793039818ea20e919a97bb56d0599`.
- Core implementation: `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9`.
- Frozen protocol: `6a6e2a3c5ef832e954af992e7602692a2f326ae608f78bf5dfbdafae2367ff72`.

The recorded source/core/protocol hashes and every recorded asynchronous output hash matched the supplied files. I reran all 2,000 repetitions **in memory**, using the recorded seed and batch size, without invoking the output-writing entry point. All six deployment counts, capped-time means and Monte Carlo standard errors, initiated-execution summaries, every calendar deployment-curve count, and paired gain summaries reproduced exactly. The complete rerun took approximately 26 seconds in the audit environment; this timing is not a performance benchmark.

I also performed checks separate from the implementation's own assertions:

- Enumerated feasible final success bits and cost signs for 1,614 sampled partially revealed pair states; every independently computed bound matched the implemented interval.
- Compared direct multiplication of the fixed-stake factors against the histogram-based mixture calculation across sampled prefixes. The maximum absolute log-wealth discrepancy was `1.1368683772161603e-13`.
- Confirmed that the implementation's 96 exhaustive finite-state checks pass, along with its full simulation checks for interval containment, exact collapse at completion, partial/full wealth domination, pathwise non-later decisions, and identical final decisions.

These checks establish reproducibility and implementation consistency for the frozen configuration. Reusing the simulation generator in the full rerun is not, on its own, independent validation of the statistical design; the design checks below address that separate question.

## Statistical and design audit

### 1. Null symmetry and the target

Under `identical_outcomes`, the A and B success bits are independent Bernoulli(0.90), their costs are independent and identically distributed lognormal variables, and success is independent of cost. The complete oriented hierarchical score is antisymmetric, so its population net benefit is exactly zero. The success-difference target is also zero. The tiny negative numerical null value from subtracting normal distribution functions is floating-point cancellation, not a negative population target.

The analytic net-benefit expression correctly accounts for success discordances cancelling, both-failure ties, cost comparisons occurring only for two successful episodes, and the 5% maximum-cost tolerance. It gives approximately 0.5272416288 under the scale-ratio-0.55 alternative.

The asymmetric reveal mechanism does not break the **complete-score** null symmetry. It deliberately breaks the symmetry of the set completed early. Thus the completed-only failure is correctly interpreted as outcome-dependent selection, not as failure of a valid full-data e-process.

The implementation directly samples the balanced, oriented pair-score law. It does not simulate an AB/BA assignment coin, execute agents, or randomize production users. This is sufficient for the stated iid score experiment; the current manuscript correctly labels that scope.

### 2. Enrollment filtration, revelation, and possible leakage

The latent full records are independent across pairs; enrollment is deterministic; systems, scoring rules, thresholds, stake grids, and reveal rules are fixed. Consequently the complete scores satisfy the stationary conditional-mean assumptions in enrollment order. Outcome-dependent delays do not invalidate this latent model. The experiment does not cover interference, data-dependent candidate updates, adaptive workload selection, or arbitrary asynchronous allocation policies.

The code uses hidden simulated values when generating reveal times and checking results, as a simulator must. The decision calculation reads each latent endpoint only under its observed/revealed mask. A missing success bit remains feasible as either zero or one, even when the known simulation mechanism would make timing informative. An unknown cost comparison admits every ternary sign. No unobserved endpoint is used to tighten the actual decision bound.

The complete-prefix comparator is allowed to use a pair once both gate scores are determined. It does not unnecessarily wait for a cost after a failure. The code's completion indicator agrees with interval collapse, making the intended information criterion checkable from observed records.

### 3. Interval containment and partial evidence

The lower success score is the minimum feasible A success minus the maximum feasible B success. The hierarchical interval enumerates all possible success completions, uses success discordance immediately, assigns a tie to joint failure, and permits all cost signs on joint success until cost comparison is known. These are valid, deliberately broad bounds. A more informative production trace could narrow them further, but doing so would require guaranteed endpoint constraints.

The lower values for different gates need not be simultaneously attained by the same hypothetical completion. Coordinatewise lower bounds suffice for coordinatewise domination and the conjunction rule.

Every stake is nonnegative and below its factor-positivity limit. Hence replacing a full score by its lower bound decreases every positive factor and its product, and then decreases the nonnegative weighted mixture. The simulated procedure therefore implements the appendix's **threshold-valid lower wealth**. It does not require, and should not be described as proving, a martingale or e-process in the observed calendar-time filtration. Current manuscript wording preserves this distinction.

### 4. Prefix-envelope fairness and conjunction validity

Both valid procedures use the same grid `100,150,...,6000`, fixed bets, calendar looks, and requirement that **one common prefix** passes both gates. The completed comparator evaluates every fully completed candidate prefix, not merely the most recent one. This prevents an artificial loss of opportunities when completion jumps over several grid points.

The partial procedure evaluates all enrolled prefixes on that same grid, including every completed candidate. It can therefore never decide later than the matched completed-prefix comparator. At complete revelation their candidate evidence agrees, so final deployment decisions must agree. These are design/theorem consequences; the assertions are useful implementation checks, not independent evidence of generic power or generic speed superiority over all possible valid delayed-data methods.

For the identical-outcome null, the fixed win gate is true at threshold zero. Any conjunction deployment entails crossing of that latent null gate at some enrollment prefix. The stationary intersection–union argument controls the entire deployment event at alpha 0.05 without splitting alpha over the two gates or the prefix grid. The grid maximum is dominated by the all-prefix crossing event of the same latent process; it is not a maximum of unrelated tests. No independence of gates is needed.

This null scenario tests a win-boundary case while the success gate has an interior noninferiority margin. It does not empirically explore a success-guardrail boundary, rare safety outcomes, changing null components under drift, or multiple candidate systems. Those settings need the separate assumptions/error allocation already discussed in the theory, and are outside this simulation.

### 5. Stopping summaries and false deployment accounting

The deployment indicator records **ever deploying** by the final look, with stopping at the first qualifying look. It is not a test only at the last look. All 1,000 identical-outcome deployments from completed-only selection are therefore false deployments for the frozen superiority gate.

Nondeployments receive the prespecified cap of 80 ticks and 12,000 initiated executions. Means are correctly described as **capped** decision times, and the separately reported median is conditional on deploying. The paired time-gain standard error uses paired replication-level differences; it is not incorrectly calculated as if the two methods used independent samples. Wilson intervals are appropriate summaries of Monte Carlo deployment uncertainty.

Generating a common complete trajectory beyond each hypothetical stopping point allows paired comparison of rules in this fixed iid/no-interference simulation. Execution counts charge only the enrollment up to that procedure's hypothetical stopping point. This is a valid counterfactual simulation accounting convention, but does not demonstrate cancellation of running agents or resource savings on actual infrastructure. Revealed cost totals measure observed telemetry completeness; they are not total paid expenditure or dollar savings. The current appendix states this correctly.

## Independently reproduced main numbers

| Scenario | Procedure | Deployments / 1,000 | Mean capped ticks | Mean initiated executions |
|---|---|---:|---:|---:|
| Identical outcomes | Completed-only selection | 1,000 | 4.155 | 831.0 |
| Identical outcomes | Complete prefixes | 6 | 79.763 | 11,976.6 |
| Identical outcomes | Partial prefix envelope | 6 | 79.763 | 11,976.6 |
| Cheaper, equally successful A | Completed-only selection | 1,000 | 3.958 | 791.6 |
| Cheaper, equally successful A | Complete prefixes | 997 | 41.285 | 8,130.8 |
| Cheaper, equally successful A | Partial prefix envelope | 997 | 22.363 | 4,459.6 |

The null valid-procedure deployment fraction is 0.006, with Wilson 95% interval approximately [0.0027527, 0.0130282]. It is below the nominal bound; it is not evidence that the true error rate is exactly 0.006. Under the alternative, the paired mean capped-time gain is 18.922 ticks with Monte Carlo standard error 0.0331514. The partial method is strictly earlier on the 997 deploying paths and later on none. The mean initiated-execution difference is 3,671.2. All null paired gains are zero.

## Remaining scope limits for submission

1. The benefit is specific to a strong cost alternative and an engineered asymmetric reporting pipeline with a 20-tick delay. Retain the explicit statement that magnitude and even strict gain depend on the reveal mechanism. A production-effect claim would require real trace-enclosure and delay evidence.
2. The study checks finite-horizon operation only. It does not empirically verify the infinite-enrollment consistency propositions or robustness to permanently unresolved outcomes.
3. The naive baseline is deliberately invalid in this mechanism. The completed-prefix baseline is a fair valid comparator, but the experiment does not establish superiority over every delayed-feedback method in the literature or over optimized model-assisted partial bounds.
4. Bounds are exact by construction in the simulator. Their practical correctness with fallible graders, mutable resources, reversals, or shared infrastructure is not established by the Monte Carlo run.
5. Full reproduction should retain the recorded **batch size 25**, as random-number consumption depends on batching. It is already specified in the protocol and manifest; using only the seed with a different batch size need not reproduce identical rows.
6. This empirical audit does not certify the novelty of the asynchronous construction. Direct prior work on worst-case pending outcomes and filtration transfer remains relevant, as acknowledged in the manuscript and evidence ledger.

No numerical correction or source-code change is requested. The single remaining wording correction above should be applied by the integrating author. Independent external statistical and agent-evaluation review remains useful because this reviewer shares authorship of the mathematical appendix.
