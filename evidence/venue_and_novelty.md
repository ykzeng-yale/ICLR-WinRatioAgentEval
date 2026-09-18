# Venue, novelty and evidence audit

Audit date: 2026-09-17 (America/New_York). Scope: the supplied idea and pasted literature summary; official ICLR 2027 rules; a targeted primary-source search of win statistics, agent evaluation and sequential inference. This is a first research audit, not an exhaustive novelty certificate or acceptance forecast. The Fan paper-review skill informed the distinction between verified defects, plausible concerns and unresolved questions.

## Overall assessment

The motivating decision problem is credible. The broad transfer claim is already anticipated: hierarchical win comparisons, meaningful ties, resource tie-breakers, same-covariate comparisons, clustered inference, sequential win statistics, and anytime deployment gates all have substantial prior art. A framework that merely applies a standard bounded-mean confidence sequence to prespecified win scores would have a serious incremental-contribution objection.

A stronger paper would explain precisely which online observation design identifies which comparison, supply a genuinely useful method for a remaining obstacle, and demonstrate consequential deployment decisions on actual agent outputs. The most promising practical distinction is between observable paired shadow evaluation and ordinary randomized A/B exposure, where only one outcome vector is observed for each live request. That distinction itself is not new causal theory; its agent-specific implications and a useful inferential or design solution must be established.

## Verified closest prior work

Each factual description below is limited to the inspected source. The final column is our assessment, not the source authors' claim.

| Source and inspected scope | Supported result | Consequence for this paper |
|---|---|---|
| [Buyse (2010), Generalized pairwise comparisons of prioritized outcomes](https://hedwig.mgh.harvard.edu/biostatistics/sites/default/files/seminar_files/Stat%20Med%2029%203245-3257%202010.pdf), paper | Extends the Wilcoxon–Mann–Whitney U-statistic to prioritized outcomes of mixed types, including repeated measurements; defines a net-benefit-type effect. | Hierarchical aggregation of heterogeneous agent metrics is an application of established GPC, not a new statistical definition. |
| [Pocock et al. (2012), The win ratio](https://pubmed.ncbi.nlm.nih.gov/21900289/), bibliographic reference independently cross-checked through inspected papers | Foundational clinically prioritized WR analysis. | Cite explicitly; do not rebrand established WR mathematics. Full original-paper inspection remains on the literature completion list. |
| [Evans et al. (2015), DOOR/RADAR](https://hsrc.himmelfarb.gwu.edu/smhs_medicine_facpubs/607/) and [Evans/Follmann exposition](https://pmc.ncbi.nlm.nih.gov/articles/PMC5394932/) | Rank overall outcomes and, within appropriate clinical categories, account for exposure duration. | Quality before resource use has a close precedent. The agent interpretation is our adaptation. |
| [Even & Josse, Rethinking the Win Ratio, v4 (March 2026)](https://arxiv.org/html/2501.16933v4), latest full text located; relevant estimand sections and abstract examined | Contrasts population comparisons with nonidentifiable individual potential-outcome comparisons; gives an identifiable same-covariate independent-copy target, nearest-neighbor and distributional-regression methods, and semiparametric efficient estimation. | Same-task/same-context interpretation and the identification warning cannot be claimed as newly discovered. New online results must be compared theorem by theorem. |
| [Fang et al., v2 (September 16, 2026)](https://arxiv.org/abs/2604.18341v2), latest abstract | Unified WR, win odds, net benefit and DOOR testing in parallel-arm CRTs, six inference procedures, simulations and WinsCRT software. | Cluster-aware WR inference already exists; paired benchmark clusters differ from treatment-assigned CRT clusters. Use the current title, which includes “hierarchical composite outcomes.” |
| [Zhang & Wu (2024), Sequential Design with Derived Win Statistics](https://arxiv.org/abs/2410.06281), abstract | Sequential WR/net-benefit designs with canonical joint-distribution proofs, sample-size planning, simulations and clinical illustration. | No “first sequential win-statistics” claim. Include a group-sequential baseline or clearly explain why it targets a different regime. |
| [Bergemann & Hanson (2026), Group Sequential Methods for the Win Ratio](https://arxiv.org/abs/2601.22525), abstract | Derives incremental U-statistic covariance and asymptotic independent increments supporting alpha spending. | “Allows interim monitoring” is not sufficient novelty. Distinguish finite-sample unlimited monitoring from asymptotic scheduled looks. |
| [Cai, Hu & Li (2026), Asymptotic Anytime-Valid Inference for U-statistics](https://arxiv.org/abs/2605.14692), abstract | Degree-two U-statistic confidence sequences for nondegenerate and degenerate regimes, with plug-in implementation and time-uniform rates. | No first U-statistic confidence-sequence claim; this result needs full technical comparison before asserting superior assumptions or rates. |
| [Howard et al., Time-uniform, nonparametric, nonasymptotic confidence sequences](https://arxiv.org/abs/1810.08240), abstract and journal metadata | General time-uniform nonparametric concentration and confidence sequences, including martingale settings. | A bounded-score application is standard machinery. Attribute and distinguish it from new agent-specific theory. |
| [Waudby-Smith & Ramdas, Estimating means of bounded random variables by betting](https://academic.oup.com/jrsssb/article/86/1/1/7043257), introduction/results overview | Variance-adaptive bounded-mean confidence sequences, including sampling without replacement. | A loose Hoeffding union bound alone is a weak practical comparator; use a strong betting/empirical-Bernstein baseline. |
| [Karampatziakis, Mineiro & Ramdas, ICML 2021, Off-Policy Confidence Sequences](https://proceedings.mlr.press/v139/karampatziakis21a.html), proceedings abstract and paper introduction | Finite-sample nonparametric confidence sequences for contextual-bandit OPE at arbitrary stopping times; explicitly studies gated deployment. | An anytime deployment gate is established in ML. This is a mandatory close baseline and framing reference. |
| [Waudby-Smith et al., Anytime-valid off-policy inference for contextual bandits](https://jds.acm.org/files/JDS_Issue3_Paper1.pdf), abstract/introduction | Adaptive logging, drifting/dependent contexts, time-varying values, doubly robust mean inference and distribution-function bands. | Adaptive routing, drift and OPE in themselves are not new. Identify the extra difficulty caused by the pairwise functional or measurement design. |
| [Skalse et al., Lexicographic Multi-Objective Reinforcement Learning](https://arxiv.org/abs/2212.13769), abstract | Priority-ordered multiobjective optimization in RL. | Priorities are not novel in AI. Expected-reward lexicographic optimization and average pairwise hierarchical preference are different targets. |
| [Kapoor et al., AI Agents That Matter](https://arxiv.org/abs/2407.01502), abstract plus author's [Holistic Agent Leaderboard description](https://hal.cs.princeton.edu/about) | Motivates credible agent benchmarking including cost and accuracy. | Show value beyond a Pareto plot and report the component metrics. The paper is not an ICLR acceptance exemplar; bibliographic records identify TMLR. |
| [Kotawala (2026), Resolution Diagnostics for Paired LLM Evaluation](https://arxiv.org/abs/2605.30315), abstract | Paired-evaluation sample-size/resolution diagnostics, clustering and sequential sensitivity analyses. | Paired uncertainty and unresolved leaderboard orderings already attract direct LLM-evaluation work; inspect before claiming first paired-resolution treatment. |

### Direct AI applications in the supplied summary

**Real-POCQi is verified, not a fabricated citation.** [Feng et al., arXiv:2606.28960v1](https://arxiv.org/html/2606.28960v1), June 27, 2026, compares clinical AI systems using separate-axis win differences. Section 5.6 defines the net win probability, reweighting for unequal pair sampling, and question-clustered bootstrap confidence intervals; it cites Pocock and Fang et al. The reported dimensions are not combined into a sequential hierarchy. Section 5.9 discloses the evaluated vendor's role in data collection and payments and the authors' blinded analysis. Section 5.10 links public [data](https://huggingface.co/datasets/jjfenglab/Real-POCQi) and [analysis code](https://github.com/jjfenglab/Real-POCQi-statistics). These links establish a release claim; the actual data completeness and licensing require separate inspection. This is relevant reanalysis material, but it is not a longitudinal agent trace or online randomized trial.

**MAPS-LLM/RECTIFIER is also a genuine close precedent.** The [JAMA research letter](https://jamanetwork.com/journals/jama/fullarticle/2830514) reports a 4,476-patient randomized AI-assisted screening trial and competing-risk time-to-eligibility analysis. Its inspected main text does not report the claimed WR=1.90. An investigator's [Duke-hosted March 2025 presentation](https://dcricollab.dcri.duke.edu/sites/NIHKR/KR/GR-Slides-03-21-25.pdf), PDF page 16, explicitly lists a secondary hierarchy putting enrollment above eligibility; PDF page 20 is labeled as the WR result. The numerical graphic was not successfully verified through text extraction in this audit, so **1.90 (1.64–2.21) remains unverified here**. The hierarchy alone is sufficient to defeat a broad first-use-in-AI claim. Do not cite the JAMA main text as support for that numerical WR result.

**GAPS-Agent is a registered direct WR comparison.** [ClinicalTrials.gov NCT07654036](https://clinicaltrials.gov/study/NCT07654036), checked against its [live API record](https://clinicaltrials.gov/api/v2/studies/NCT07654036), prespecifies overall-plan wins/losses and physician-by-case clustered bootstrap intervals. Separate safety/completeness/resource outcomes do not establish a lexicographic composite. The live API lists COMPLETED, last posted July 30, 2026; the search index still displayed an earlier enrolling status. A completed registry status is not published numerical results, and the analysis plan is not proof that its proposed inference is valid.

## What remains genuinely open to demonstrate

These are candidate contributions, not claims of priority:

1. **Observation-design theorem and useful decision protocol.** Characterize when paired shadow outcomes are available, what single-arm A/B data identify, and how a prespecified reference distribution or randomized paired-probe design supports the desired comparison. Any changed estimand must be explicit.
2. **Efficient online pairwise inference beyond a generic reduction.** For example, a proven treatment of within-task output reuse, delayed outcome revelation, or adaptive selection that improves a meaningful cost/variance tradeoff while preserving the stated target. Establish why existing OPE/CS results do not already imply it immediately.
3. **Decision relevance.** Demonstrate real cases where naïve composites, correctness-only rankings, and valid guarded prioritized decisions disagree, and show which decision satisfies the prespecified operational objective.
4. **Measurement discipline.** Distinguish validated functional outcomes from noisy human/LLM judgments, and establish the target under grading noise rather than silently claiming inference about latent correctness.

The pairwise-priority-versus-population-constraint counterexample is valuable exposition. It becomes a research contribution only if its prevalence, decision consequences, or a new remedy are established beyond an illustrative construction.

## Accepted and award examples: what to learn

| Verified example | Evidence | Transferable lesson (our interpretation) |
|---|---|---|
| [τ-bench, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/1b126cc38b8638e07bef37e7b2bb72bf-Paper-Conference.pdf) | Official proceedings; 115 retail/50 airline tasks, repeated agent/user simulations, policy and database outcomes, reliability-oriented pass-hat-k. The paper acknowledges that final-state success can miss policy violations. | Preserve task pairing and repeated trials; independently measure policy compliance. Do not confuse repeated attempts with new tasks, nor benchmark users with real production users. |
| [WildBench, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/771155abaae744e08576f1f3b4b7ac0d-Abstract-Conference.html) | Official proceedings; 1,024 real-user tasks, task-specific checklists, fine-grained pairwise judgments, explanations and comparison to human-voted rankings. | Pairwise scores need credible measurement and external validity evidence, beyond statistical elegance. |
| [LLMs Get Lost In Multi-Turn Conversation](https://arxiv.org/abs/2505.06120), ICLR 2026 Outstanding Paper | Award verified by the [official announcement](https://blog.iclr.cc/2026/04/23/announcing-the-iclr-2026-outstanding-papers/); paper describes over 200,000 simulated conversations over six tasks, isolating performance/reliability degradation. | A crisp diagnosis of an important real-use mismatch, controlled experiments and a scalable measurement method can matter more than a new model. The scale is an example, not a required quota. |
| Transformers are Inherently Succinct; The Polar Express | The same official announcement lists the former as Outstanding Paper and the latter as Honorable Mention. | The committee recognized both conceptual theory and principled methods with practical relevance. There is no single mandatory empirical recipe or award guarantee. |

The 2026 award committee emphasized experimental methodology for the multi-turn evaluation paper and conceptual significance for the theory paper. Award selection is exceptional and partly subjective; it cannot be reverse-engineered into a guaranteed acceptance checklist.

## Realistic empirical bar for this particular claim

The following is our assessment, not a formal venue minimum:

- A small synthetic simulation plus one repackaged clinical comparison is insufficient evidence for a broad agentic-online-evaluation claim.
- Include at least two distinct workflow families with genuine agent outputs, differing task difficulty and realistic failure/cost tradeoffs. Three to five system or orchestration variants can distinguish model capability from workflow design; determine run counts by precision/power rather than those illustrative numbers.
- Online evidence should include a prospectively specified stream experiment with randomized routing or a paired shadow design. If only old traces are available, call it randomized stream replay; it tests statistical operation under the replay scheme, not real live intervention outcomes.
- Compare to a valid fixed-horizon method, a competitive anytime method, a group-sequential method where applicable, marginal guardrails, task-weighted GPC, scalarized scores and Pareto summaries. Do not claim power superiority by comparing different null hypotheses.
- Evaluate Type I error/coverage, power, stopping time, computation, collected-agent-run cost, false deployment probability, and abstention. Report Monte Carlo intervals and all prespecified settings, including no-effect and harmful-primary-outcome cases.
- Report component effects and tier contributions, plus uncertainty and unresolved choices. Sensitivity to priorities, tolerances, workload shifts and grading errors is scientifically central.
- Retain full prompts, model snapshots, seed/configuration records, raw results, traces, judge versions and outcome definitions. Missing latency/cost cannot be silently filled with invented values.

## Review objections to resolve before claiming readiness

| Likely substantive objection | Evidence needed to close it |
|---|---|
| “This is old GPC plus standard CS.” | Exact closest-result comparison and a nontrivial technical result or an unusually strong new empirical finding. |
| “Your online experiment cannot observe both potential workflows.” | An explicit identification argument matched to the actual data-collection design; avoid unverifiable same-request counterfactual outcomes. |
| “The win score sacrifices primary quality for small cost gains.” | Population-level guardrails, valid joint error control, and counterexamples/experiments showing the distinction. |
| “You chose the hierarchy after seeing the results.” | Timestamped protocol or held-out calibration/evaluation separation; exploratory alternatives labeled clearly. |
| “The sample size is inflated by reused trajectories.” | Correct independent unit and variance analysis; sensitivity to repeated tasks and shared environments. |
| “Slow failures are excluded during live monitoring.” | Precisely defined completion/missingness protocol and a proof or defensible restriction for delayed feedback. |
| “The grader is biased or inaccurate.” | Blinding, order balancing, human/code validation where appropriate, and graded-outcome rather than latent-truth estimand if needed. |
| “Offline replay is marketed as live A/B validation.” | Honest labels and bounded claims; actual prospective experiment if production conclusions are central. |
| “The experiments favor the proposed null.” | Comparable operating characteristics under shared targets, explicitly separate incomparable decision objectives. |

## Search limitations and next literature steps

The source list is targeted and must be extended before a final novelty statement. Full theorem-level reading remains necessary for the sequential WR papers, Cai et al., latest Even–Josse, modern OPE confidence sequences, causal U-statistics (Lu Mao, Biometrika 2018), and delayed-feedback/online multiple-testing literature. The supplied LangSmith, TRAIL, LLM Comparator and Anthropic links are useful context but were not all independently re-audited in this bounded pass. No claim is made that no company or unpublished group already implements the combination.

See `submission/requirements.md` for the current official dates, format, AI disclosure and completion gates. Neither an AI reviewer consensus nor a cleanly compiled PDF certifies acceptance, novelty, human scientific review, or actual submission.
