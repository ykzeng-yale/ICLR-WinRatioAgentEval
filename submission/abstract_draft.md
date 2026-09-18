# Title

Which Agent Should Ship? Prioritized Pairwise Comparison of AI Agents with Sequential Guardrails

# Abstract

Teams comparing two AI agent versions record several outcomes per run (success, cost, tool calls, latency) and must decide which to ship. Leaderboards rank by success, cost-aware evaluations draw Pareto frontiers, and experimentation platforms gate rollouts on per-metric guardrails; none says what a prioritized pairwise preference estimates or when acting on it is safe. We adapt clinical-trial hierarchical win statistics (net benefit, win ratio) to agent comparison as an evaluation protocol. First, we map which estimand each design identifies: offline task-matched replicates identify a same-task preference (with quantified shared-seed bias), pair-randomized single-exposure A/B streams identify only a stratified cross-request contrast, and shadow execution identifies the same-request preference only for outcomes computable without a user. Second, we name and measure priority inversion: lower tiers are consulted only when higher tiers tie, so a hierarchical winner can have significantly lower success. On released tau2-bench, SWE-bench Lite and HAL trajectories, 9 of 25 contrasts invert; in tau2-bench retail one system is preferred with net benefit 0.53 (95% interval 0.42–0.63) despite 7 points lower success, and marginal decisions flip under 1% label noise. Third, we give a guarded sequential decision rule based on confidence sequences, state its error control under stationary and drifting traffic, and measure its price against all-pairs group-sequential and per-metric conjunction rules. It never deployed a success-regressing system in simulation and resolved a pooled contrast after a median of 838 paired runs in randomized stream replay. A partial-score envelope certifies pair outcomes before slow episodes complete, halving decision time.

# Number provenance

- 9 of 25 contrasts invert: `results/benchmarks/decision_matrix_summary.json` (`priority_inversions`: 9, `n_pairs`: 25; 4 with NB interval excluding zero).
- Retail net benefit 0.53 (0.42–0.63), success difference −0.07 (−0.14 to −0.00): `results/benchmarks/decision_matrix.csv`, row tau2/retail/o4-mini vs claude-3-7-sonnet (nb 0.5278, nb_lo 0.4248, nb_hi 0.6307; success_diff −0.0724, lo −0.1410, hi −0.0037). Exploratory contrast; pointwise task-bootstrap interval conditional on four shared seeds.
- Flip under 1% label noise: `results/benchmarks/label_noise_sensitivity.csv`, airline o4-mini vs gpt-4.1, nondifferential, flip_rate 0.01, frac_decision_changed 0.275.
- Never deployed a success-regressing system: `results/online_methods_results.csv`, success_regression / guarded_betting, 0 of 2,000 (win_only_betting 2,000 of 2,000).
- Median 846 paired runs: `results/replay/replay_results.csv`, tau2_o4mini_vs_gpt41_all / paired, median_deploy_time 838.5, deploy_rate 0.976.
- Halving decision time: `results/async_results.csv`, cheaper_equal_success, complete_prefix 41.285 vs partial_prefix_envelope 22.363 mean calendar ticks, deployment 0.997 both.
- "Measure its price against all-pairs group-sequential and per-metric conjunction rules": promised from E8 (`experiments/ustat_reference/`, coded, not yet run) and E2a (to implement); the sentence must be checked against results before the paper deadline.
