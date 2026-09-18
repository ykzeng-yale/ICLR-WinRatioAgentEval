# Title and abstract options for the ICLR 2027 abstract deadline

**Deadline:** September 18, 2026, 23:59 AoE = **September 19, 2026, 07:59 EDT** (New York). Verified against the official author guidelines on 2026-09-17.
**What is frozen at this deadline:** the author list (no additions or removals afterwards). Title and abstract must be genuine but can be revised until the full-paper deadline (September 25, 2026, 23:59 AoE); re-check this on the live OpenReview form.
**Where to submit:** https://openreview.net/group?id=ICLR.cc/2027/Conference (every author needs a complete OpenReview profile; check reciprocal-reviewing eligibility on the form).

Two options are below. Option 1 is the abstract currently in the manuscript owned by the root session (paper/main.tex, commit 9fcb613). Option 2 is the decision-layer framing recommended by the positioning memo (submission/positioning_memo_v2.md, revised after three adversarial critiques in reviews/positioning_review_*.md), with every number traced to a committed result file. Either is genuine; both describe the same project. If in doubt, submit Option 1 verbatim now (it matches the current PDF) and revise toward Option 2 before September 25 once the integration PRs are merged.

---

## Option 1 (current manuscript, paper/main.tex)

**Title:** Guarded Win Statistics for Continuous Agent Evaluation

**Abstract:**
Agent evaluation combines verified completion, policy compliance, and resource use, often while trajectories are still arriving. A hierarchical win statistic makes outcome priorities explicit, but a favorable aggregate can conceal a decline in a higher-priority population outcome. We develop a guarded evaluation protocol that combines prioritized comparisons with separate component requirements. It distinguishes same-task benchmark repetitions from randomized cross-arrival online comparisons and gives finite-sample continuous-monitoring guarantees. For delayed outcomes, feasible completions of partial traces bound the final pair score. A prefix envelope transfers established full-data guarantees to these partial scores and cannot decide later than its matched completed-prefix comparator. Complete proofs identify the required enrollment-order assumptions and distinguish threshold error control from a calendar-time e-process. In 2,000-repetition stationary simulations, guarded betting made false deployments in 0.45% of identical-agent runs versus 31.05% for repeated ordinary Wald tests. In a separate informative-delay study, partial evidence reduced mean capped decision time from 41.285 to 22.363 ticks for an equally successful, cheaper alternative; both valid methods deployed in 99.7% of runs and had 0.6% null false deployments. Historical agent traces show why success-first aggregate wins still need success guardrails. These results support explicit decisions for a specified workload and preference rule, with unresolved outcomes retained in the analysis.

---

## Option 2 (decision-layer framing, revised after three adversarial critiques; every number traced to a result file)

**Title:** Which Agent Should Ship? Prioritized Pairwise Comparison of AI Agents with Sequential Guardrails

**Abstract:**
Teams comparing two AI agent versions record several outcomes per run (success, cost, tool calls, latency) and must decide which to ship. Leaderboards rank by success, cost-aware evaluations draw Pareto frontiers, and experimentation platforms gate rollouts on per-metric guardrails; none says what a prioritized pairwise preference estimates or when acting on it is safe. We adapt clinical-trial hierarchical win statistics (net benefit, win ratio) to agent comparison as an evaluation protocol. First, we map which estimand each design identifies: offline task-matched replicates identify a same-task preference (with quantified shared-seed bias), pair-randomized single-exposure A/B streams identify only a stratified cross-request contrast, and shadow execution identifies the same-request preference only for outcomes computable without a user. Second, we name and measure priority inversion: lower tiers are consulted only when higher tiers tie, so a hierarchical winner can have significantly lower success. On released tau2-bench, SWE-bench Lite and HAL trajectories, 9 of 25 contrasts invert; in tau2-bench retail one system is preferred with net benefit 0.53 (95% interval 0.42–0.63) despite 7 points lower success, and marginal decisions flip under 1% label noise. Third, we give a guarded sequential decision rule based on confidence sequences, state its error control under stationary and drifting traffic, and measure its price against all-pairs group-sequential and per-metric conjunction rules. It never deployed a success-regressing system in simulation and resolved a pooled contrast after a median of 846 paired runs in randomized stream replay. A partial-score envelope certifies pair outcomes before slow episodes complete, halving decision time.

Number provenance (from submission/abstract_draft.md):
- 9 of 25 contrasts invert: `results/benchmarks/decision_matrix_summary.json` (`priority_inversions`: 9, `n_pairs`: 25; 4 with NB interval excluding zero).
- Retail net benefit 0.53 (0.42–0.63), success difference −0.07 (−0.14 to −0.00): `results/benchmarks/decision_matrix.csv`, row tau2/retail/o4-mini vs claude-3-7-sonnet (nb 0.5278, nb_lo 0.4248, nb_hi 0.6307; success_diff −0.0724, lo −0.1410, hi −0.0037). Exploratory contrast; pointwise task-bootstrap interval conditional on four shared seeds.
- Flip under 1% label noise: `results/benchmarks/label_noise_sensitivity.csv`, airline o4-mini vs gpt-4.1, nondifferential, flip_rate 0.01, frac_decision_changed 0.275.
- Never deployed a success-regressing system: `results/online_methods_results.csv`, success_regression / guarded_betting, 0 of 2,000 (win_only_betting 2,000 of 2,000).
- Median 846 paired runs: `results/replay/replay_results.csv`, tau2_o4mini_vs_gpt41_all / paired, median_deploy_time 846, deploy_rate 0.962.
- Halving decision time: `results/async_results.csv`, cheaper_equal_success, complete_prefix 41.285 vs partial_prefix_envelope 22.363 mean calendar ticks, deployment 0.997 both.
- "Measure its price against all-pairs group-sequential and per-metric conjunction rules": promised from E8 (`experiments/ustat_reference/`, coded, not yet run) and E2a (to implement); the sentence must be checked against results before the paper deadline.

---

## OpenReview form checklist (fill by the abstract deadline)

- Title, abstract (one of the options above), TL;DR (one sentence, e.g. "A guarded, anytime-valid hierarchical win-statistics protocol for comparing AI agents offline and in online A/B tests").
- Authors: complete list with OpenReview profiles; order can change until the paper deadline; no additions/removals after the abstract deadline.
- Keywords: agent evaluation; win ratio; generalized pairwise comparisons; anytime-valid inference; confidence sequences; A/B testing; guardrails.
- Primary area: choose the evaluation/benchmarking or probabilistic-methods area offered by the form (the 2027 list is only visible on the form).
- Reciprocal reviewing: nominate at least one qualified author reviewer, or claim the one-paper exemption if no author qualifies.
- AI-use disclosure on the form: substantial AI assistance (literature, theory and proofs, code, experiments, drafting, internal review); human verification status must be stated truthfully.
- Conflicts of interest and Code of Ethics acknowledgment.
