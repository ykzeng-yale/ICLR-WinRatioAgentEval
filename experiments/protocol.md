# Experiment and analysis protocol

Version: 2026-09-18 UTC. Status: prospective analysis specification written after source/schema inspection and before analysis of hierarchical pairwise results. This is not an external preregistration. Implemented scenarios, deviations, seeds, run counts, and actual results must be recorded separately; a proposed scenario is not an executed experiment.

## Protocol amendment: independent replicate target

The initial coordination decision was to use all 4×4 within-task pairs as primary. Before either the coordinating author or empirical analyst inspected computed hierarchical comparison values, independent theory review identified that its four same-seed diagonal pairs can be coupled. On 2026-09-18 UTC, the primary τ² estimator was changed to the **12 off-diagonal pairs** per task. The 16-pair empirical V-statistic and four paired-seed comparisons are retained as sensitivity estimands. Distinct-seed independence remains an assumption. An initial analysis process had been dispatched; any resulting preliminary numerical files were preserved privately under `work/empirical_sources/pre_amendment_unreviewed`, and final artifacts were regenerated after this amendment. This is a transparent design correction, not an external preregistration. SWE has only one run per task/system and retains a historical task-paired target.

## Objectives and estimands

Primary objective: evaluate whether a formally specified hierarchical comparison supports interpretable, statistically calibrated continuous evaluation of agent systems under optional stopping. Secondary objective: show what success, cost, and trace-efficiency disagreements the framework exposes in real agent logs. Do not assume that a new metric automatically improves system quality or that a novel name establishes a methodological contribution.

Define the unit and target before every experiment:

- **Matched benchmark target:** draw a task from a stated task distribution, then compare independent runs of A and B conditional on that task, or explicitly compare a common-seed coupling. These are distinct if model/run randomness is coupled.
- **Randomized online population target:** compare independent outcomes drawn from the two assigned-system populations under the specified incoming-context distribution. If matching/stratification is used, define the stratum distribution and matching rule.
- **Paired shadow-execution target:** both systems execute against a replicated task/environment; this observes a paired comparison at approximately double evaluation cost. It requires no interference between copies and cannot be described as ordinary single-exposure production A/B testing.

The paper must state which target the theorem and the empirical estimator address. Same-user potential-outcome preference is not identified by observing only one randomly assigned system unless additional assumptions or paired execution are supplied.

## Hierarchy and fixed choices

Analysis choices finalized by the coordinating author before computed win outcomes: primary cost margin 5%, absorbing joint failure, 12 off-diagonal within-task comparisons, same-seed and 16-pair sensitivities (amended as documented above), and 3-percentage-point illustrative success noninferiority margin.

Primary benchmark hierarchy: (1) recorded task success, (2) historical agent inference cost, (3) assistant tool-call count. Use an absorbing failure rule in the primary version: when both systems fail, record a tie rather than reward a cheaper failure. Report ordinary lexicographic comparison, which can rank two failures by cost, as sensitivity. If the implemented theory uses ordinary lexicographic comparison as primary, reverse these labels explicitly before computing results and explain why.

For successful pairs tied on success, cost is decisive only if `abs(cost_A-cost_B) > 0.05*max(cost_A,cost_B)`; exact threshold equality is a tie. A cost of zero versus positive is cheaper; both zero tie. Tool calls use an absolute zero-call tolerance: any strict count difference is decisive. Sensitivity grids: relative cost margins 0%, 10%, 20%; the same 5% margin with resource order reversed. These definitions match the shared comparator implementation. Duration belongs in sensitivity because τ² simulation duration includes the user simulator. Full priority-order sensitivity should cover success→cost→steps and success→steps→cost, with duration as an additional exploratory version.

Report wins, losses, ties, net win probability, win ratio, and the fraction decided at every level. If the loss probability is zero or its interval includes zero, report the ratio as undefined/unbounded as appropriate; do not conceal this with arbitrary pseudocounts. Net win is the stable primary inferential scale. Use an independent success noninferiority gate for any proposed deployment decision; an illustrative margin of 3 percentage points is a design example, not an externally validated business tolerance.

## Simulation design

Use a fixed master seed and deterministic child seeds keyed by scenario, method, repetition, and horizon. All methods see the same generated trajectories/random assignments in each repetition. Save the full configuration and software environment. Analytic truth or independently computed high-precision truth must be separate from the datasets used to estimate performance.

### Core scenarios required

| Scenario | Purpose | Truth/assumption requirement |
|---|---|---|
| Exact exchangeable null | Optional-stopping type I error | Same joint outcome law in both systems; include 0%, 50%, and 90% pairwise ties |
| Weak mean-win null with unequal laws | Test the stated null rather than only identical distributions | Construct unequal distributions with exact mean win zero; a permutation test may not test this null |
| Success improvement only | Power for the most important tier | Increase success probability while leaving conditional cost law equal |
| Efficiency improvement only | Power when success ties dominate | Equal success law; shift log-cost location and preserve heavy tails |
| Success–cost conflict | Guardrail necessity and estimand clarity | Slightly lower success with much cheaper successful outcomes; demonstrate when net wins are positive |
| Common context drift | Robustness allowed by the theorem | Evolve task difficulty and cost for both systems; maintain the required conditional null at every update |
| Treatment-by-time drift | Show limitation or valid adapted target | Distinguish conditional-null validity from a merely time-average null; do not label an assumption violation a valid-null failure |
| Adaptive randomization | Online A/B relevance | Prespecified/predictable assignment probabilities, logged at decision time and bounded away from 0/1; include a fixed-allocation benchmark |
| Delayed outcomes | Completion-order selection | Fast successes and slow failures; compare assignment-order analysis with naive completion-order analysis |
| Repeated tasks/users | Cluster dependence | Correlated repeated evaluations; compare cluster-valid versus naive individual-run inference |
| Heavy-tailed cost and timeout | Agent-workflow realism | Lognormal and finite-mean Pareto cost; cap counted as failure/terminal outcome, not dropped |
| Judge/label error | Robustness to verifier mistakes | Differential and nondifferential 0%, 1%, 5% label contamination; compare contamination bounds to actual label flips |

Scope the claims to the scenarios actually executed. If adaptive allocation, delayed outcomes, or repeated users are not covered by the theorem, show them only as clearly labeled stress tests or future design extensions.

### A transparent analytic calibration family

For independent-arm runs with success probabilities p_A,p_B, independent log-costs `L_A~N(mu_A,sigma_A²)` and `L_B~N(mu_B,sigma_B²)`, and no lower-tier comparison for joint failures, let `q=p_A*p_B`, `s²=sigma_A²+sigma_B²`, and `d=mu_A-mu_B`. With log-cost margin δ and no tertiary endpoint,

`theta = p_A - p_B + q * [Phi((-δ-d)/s) - 1 + Phi((δ-d)/s)]`.

For ordinary lexicographic comparison, replace q by `p_A*p_B+(1-p_A)*(1-p_B)`. This gives exact truth, tie probability, and counterexamples without Monte Carlo ground-truth error. It requires the displayed independence assumptions; do not reuse it when costs depend on success or shared context without conditioning and integration. Add a discrete cost distribution for exact ties. Use a separate correlated latent-difficulty family for realism.

### Horizons, repetitions, and uncertainty

Recommended primary horizons: 100, 250, 500, 1,000, 2,000 evaluable units/pairs; monitor at every valid update after the prespecified minimum sample size. Counts must clearly distinguish pairs from total agent calls. Use 10,000 repetitions for core null scenarios and at least 5,000 for power scenarios. At p=0.05, 10,000 repetitions give Monte Carlo SE ≈0.00218 (0.218 percentage points); at p=0.5, 5,000 give SE ≈0.00707. Report Monte Carlo confidence intervals rather than precision implied by extra decimal places. An early pilot with fewer repetitions is development evidence; final tables should identify it as such or rerun to the specified precision.

Report cumulative type I error (ever crossing by horizon), fixed-horizon coverage, simultaneous/anytime coverage if claimed, power, median and restricted mean stopping time, never-stop fraction, allocation imbalance, agent-call expenditure, and confidence-interval width. Do not report mean stopping time only among discoveries. For a desired false-positive precision narrower than these values, increase repetitions before interpretation.

## Comparators and fairness

At a minimum compare:

1. An established fixed-horizon estimator/test for the same net-win or win-ratio target with correct pairing/clustering; this anchors offline performance.
2. The same fixed-horizon test naively repeated at every look; label this an intentionally invalid optional-stopping baseline.
3. A valid prespecified alpha-spending or Bonferroni-at-fixed-looks baseline on the same target.
4. A recognized betting/e-process or mixture confidence-sequence implementation applicable to the same bounded observations and assumptions, not only a weak custom boundary.
5. Success-only inference and a prespecified normalized weighted utility, reported as **different decision criteria** rather than as competing estimators of the win estimand.
6. A cost–success Pareto display and success noninferiority plus efficiency improvement decision rule; neither should be claimed inferior solely because it answers a different question.

Every method must have the same one-sided/two-sided error budget, opportunities to inspect data, observation/call budget, direction of superiority, and delay handling. Show power against valid alternatives at matched error control. Do not tune a betting strategy on the evaluation repetitions and then report it as prespecified.

## Real-agent analyses

### τ²-bench primary

Use GPT-4.1, o4-mini, and Claude 3.7 Sonnet with exact source provenance from the feasibility report. Analyze three domains separately. The main contrast is o4-mini versus GPT-4.1, fixed for its interpretable reasoning-versus-general-model comparison; Claude comparisons are additional, with multiplicity adjustment if inferential claims are made. Task-weighted pooling across domains must state weights; equal-domain weighting differs from weighting all 278 tasks equally.

For each task with four runs per system, the primary statistic averages the 12 off-diagonal comparisons and targets independent within-task run draws under independence of distinct-seed runs. The four same-seed pairs estimate a coupled preference and are a distinct sensitivity estimand. The all-16 V-statistic combines three quarters off-diagonal and one quarter same-seed comparisons and is another sensitivity, not an unbiased substitute for the independent-run target. Do not treat these comparisons as independent; summarize at task level, then bootstrap tasks within domain. Use 10,000 bootstrap replicates for descriptive percentile intervals; report the interval method and finite-task limitation. Report raw per-model success/cost/call summaries alongside win statistics. Include GPT-4.1-mini only as explicitly marked harness-version sensitivity until audited.

### SWE-bench Lite supplementary

Use GPT-4 and Claude 3 Opus official 2024 SWE-agent runs on all 300 shared tasks. Map success from official resolved IDs; use `instance_cost`, not cumulative `total_cost`; retain unsuccessful and budget-capped attempts. Cost and tool/step counts are observed; latency is unverified and excluded. Show repository-stratified counts and leave-one-repository-out sensitivity. The available one-run-per-model/task comparison includes run stochasticity; it does not estimate each model's success probability for an individual task.

### Sequential replay

Replay task clusters in random, easy-to-hard, and hard-to-easy orders; add an explicitly synthetic context-drift mixture only if described as simulated. Primary valid evaluation observes all needed outcomes in assignment/task order, never whichever model finishes first. Reuse finite logs only with an explicit empirical-distribution target. If sampling with replacement, resample an entire task/run unit consistent with the chosen estimand; repeated resampling does not generate new real agent runs. Report separate uncertainty from replay ordering and uncertainty about unseen tasks. Do not count each replay as an independent real-world experiment.

## Submission-readiness evidence required from the executed work

- Exact configurations, seeds, source snapshots/hashes, data dictionaries, run logs, numerical result tables, plotting scripts, and a single-command reproduction path.
- A manifest matching every manuscript number/figure to a generated artifact; no hand-entered placeholders presented as results.
- A theorem-to-simulation table naming the assumptions each valid-null scenario satisfies and each stress test violates.
- An analysis-deviation log covering hierarchy, endpoint, threshold, exclusion, baseline, or scenario changes after comparative inspection.
- At least two independent empirical/statistical reviews followed by documented responses, plus a reviewer able to challenge the ML contribution and strongest baselines.
- Claims scaled to completed evidence. Historical benchmark reanalysis plus simulated streams can support a statistical framework paper; it cannot be described as a completed live-production online evaluation.
