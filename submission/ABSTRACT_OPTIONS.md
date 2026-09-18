# Title and abstract options for the ICLR 2027 abstract deadline

**Deadline:** September 18, 2026, 23:59 AoE = **September 19, 2026, 07:59 EDT** (New York). Verified against the official author guidelines on 2026-09-17.
**What is frozen at this deadline:** the author list (no additions or removals afterwards). Title and abstract must be genuine but can be revised until the full-paper deadline (September 25, 2026, 23:59 AoE); re-check this on the live OpenReview form.
**Where to submit:** https://openreview.net/group?id=ICLR.cc/2027/Conference (every author needs a complete OpenReview profile; check reciprocal-reviewing eligibility on the form).

Two options are below. Option 1 is the abstract currently in the manuscript owned by the root session (paper/main.tex, commit 9fcb613). Option 2 is the decision-layer framing recommended by the positioning memo (submission/positioning_memo.md) with numbers filled from this session's decision-disagreement analysis (results/benchmarks/decision_matrix_summary.json). Either is genuine; both describe the same project. If in doubt, submit Option 1 verbatim now (it matches the current PDF) and revise toward Option 2 before September 25 once the integration PRs are merged.

---

## Option 1 (current manuscript, paper/main.tex)

**Title:** Guarded Win Statistics for Continuous Agent Evaluation

**Abstract:**
Agent evaluation combines verified completion, policy compliance, and resource use, often while trajectories are still arriving. A hierarchical win statistic makes outcome priorities explicit, but a favorable aggregate can conceal a decline in a higher-priority population outcome. We develop a guarded evaluation protocol that combines prioritized comparisons with separate component requirements. It distinguishes same-task benchmark repetitions from randomized cross-arrival online comparisons and gives finite-sample continuous-monitoring guarantees. For delayed outcomes, feasible completions of partial traces bound the final pair score. A prefix envelope transfers established full-data guarantees to these partial scores and cannot decide later than its matched completed-prefix comparator. Complete proofs identify the required enrollment-order assumptions and distinguish threshold error control from a calendar-time e-process. In 2,000-repetition stationary simulations, guarded betting made false deployments in 0.45% of identical-agent runs versus 31.05% for repeated ordinary Wald tests. In a separate informative-delay study, partial evidence reduced mean capped decision time from 41.285 to 22.363 ticks for an equally successful, cheaper alternative; both valid methods deployed in 99.7% of runs and had 0.6% null false deployments. Historical agent traces show why success-first aggregate wins still need success guardrails. These results support explicit decisions for a specified workload and preference rule, with unresolved outcomes retained in the analysis.

---

## Option 2 (decision-layer framing; numbers from results/benchmarks/decision_matrix.csv and results/replay/replay_results.csv)

**Title:** Which Agent Should Ship? Prioritized Pairwise Comparison with Anytime-Valid Guardrails

**Abstract:**
Teams comparing two versions of an AI agent already record prioritized, heterogeneous outcomes per run (task success, policy violations, tool calls, latency, cost), already compare candidates pairwise on the same inputs, and already monitor rollouts continuously. What they lack is a decision rule whose error guarantees survive both the prioritization and the monitoring. We adapt hierarchical win statistics from clinical trials (net benefit, win ratio, win odds) to agent comparison and join them with anytime-valid inference. First, we show which win estimand each evaluation design identifies: offline task-matched replicates identify a same-task preference, pair-randomized single-exposure A/B tests identify only a cross-request contrast, and shadow execution identifies the same-request preference at double cost. Second, we give finite-sample confidence sequences and e-processes for net benefit, win ratio and tier contributions of a randomized paired stream, valid under optional stopping, adaptive orientation and drift. Third, because lower tiers are consulted only when higher tiers tie, a hierarchical winner can be strictly worse on task success; we give a guarded sequential deployment rule with intersection-union error control and show why drifting traffic requires a split error budget. On released tau2-bench, SWE-bench Lite and HAL trajectories, success-only tests, Pareto membership, linear cost-utility rules and the guarded hierarchical decision disagree on 19 of 25 system pairs once task-clustered uncertainty is respected, and 9 pairs prefer the system with lower marginal success. In randomized stream replay, paired shadow evaluation reaches guarded decisions with roughly 30% fewer runs than cross-arrival A/B exposure while keeping false deployments below the nominal rate.

(Word count about 250. The 19/25, 9 and roughly-30% figures are computed in this session and should be re-checked after the root session integrates the analysis; keep them only if the integrated paper reports them.)

---

## OpenReview form checklist (fill by the abstract deadline)

- Title, abstract (one of the options above), TL;DR (one sentence, e.g. "A guarded, anytime-valid hierarchical win-statistics protocol for comparing AI agents offline and in online A/B tests").
- Authors: complete list with OpenReview profiles; order can change until the paper deadline; no additions/removals after the abstract deadline.
- Keywords: agent evaluation; win ratio; generalized pairwise comparisons; anytime-valid inference; confidence sequences; A/B testing; guardrails.
- Primary area: choose the evaluation/benchmarking or probabilistic-methods area offered by the form (the 2027 list is only visible on the form).
- Reciprocal reviewing: nominate at least one qualified author reviewer, or claim the one-paper exemption if no author qualifies.
- AI-use disclosure on the form: substantial AI assistance (literature, theory and proofs, code, experiments, drafting, internal review); human verification status must be stated truthfully.
- Conflicts of interest and Code of Ethics acknowledgment.
