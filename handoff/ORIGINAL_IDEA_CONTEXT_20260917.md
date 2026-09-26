**Yes—your proposed connection is methodologically sound, and there are already some direct precedents. But the precise distinction is important: using “wins and losses” to compare AI systems is not the same as using a prespecified hierarchy of outcomes to determine those wins and losses.** I found examples of both, including a genuinely hierarchical win-ratio analysis of an AI-supported workflow.

My assessment is that **“the first application of win statistics to AI evaluation” would be too broad a novelty claim**. A more defensible research direction is **task-matched, prioritized evaluation of stochastic AI agents**, combining final outcomes, selected trajectory outcomes, resource use, and appropriate statistical inference. I did not identify a general-purpose paper or public evaluation product that fully develops that combination.

## 1. The closest existing applications

### MAPS-LLM / RECTIFIER: a genuinely hierarchical win-ratio evaluation of an AI-supported workflow

The strongest direct precedent I found is **Unlu et al., “Manual vs AI-Assisted Prescreening for Trial Eligibility Using Large Language Models—A Randomized Clinical Trial,” JAMA, 2025**. The MAPS-LLM trial randomized 4,476 patients to manual screening or screening assisted by RECTIFIER, an LLM-based system for assessing clinical-trial eligibility. Importantly for your broader analogy, the main publication analyzed **time to eligibility determination, with ineligibility determination treated as a competing risk**. ([JAMA Network][1])

The investigators’ presentation explicitly specifies a secondary endpoint:

> “Hierarchical win ratio prioritizing enrollments over eligibility determinations.”

It reports a hierarchical win ratio of **1.90, with a 95% confidence interval of 1.64–2.21**, favoring AI-assisted screening. The presentation also separates wins contributed by enrollment from those contributed by eligibility determination. **The win-ratio result is documented in the investigators’ slides; it is not reported in the main text of the JAMA research letter I inspected.**

This is very close to your underlying idea: prioritize the ultimate workflow objective—enrollment—above an intermediate achievement—eligibility determination. It is **not** a generic benchmark of autonomous agents, but it establishes that hierarchical win statistics have already been used to evaluate an AI-enabled process.

There is also a commercial connection: Mass General Brigham subsequently announced **AIwithCare**, a company built around the RECTIFIER technology. That is a company whose underlying technology has been evaluated with this approach—not evidence that it sells a general-purpose win-ratio evaluation platform. ([Mass General Brigham News][2])

### Real-POCQi: explicit use of win statistics for head-to-head AI-system evaluation

A particularly relevant recent paper is **Feng et al., “Expert Evaluation of Clinical AI Tools on Real Point-of-Care Clinical Queries,” June 2026 preprint**. It compares OpenEvidence with general-purpose models using physician judgments on accuracy, clinical utility, source quality, verifiability, and completeness. Its prespecified primary measure is a **win difference**, \((W-L)/N\). Crucially, the dimensions are evaluated **separately**, rather than combined into one sequential hierarchy. The paper releases its benchmark and statistical-analysis code. ([arXiv][3])

**There is a direct connection to your methodological network:** the paper cites *Statistical inference with win statistics in cluster-randomized trials with composite outcomes*, by **Xi Fang, Guangyu Tong, Yuan Huang, F. Perry Wilson, Patrick Heagerty, and Fan Li**. Thus, this is not merely AI researchers independently using the word “win”; there is an explicit citation bridge to the biostatistical literature. ([arXiv][3])

For interpreting its performance claims, the preprint discloses that OpenEvidence helped develop and implement data collection and paid respondents; the authors report prespecified, identity-blinded statistical analysis. ([arXiv][3])

### GAPS-Agent: an explicit “Win Ratio” endpoint, but not a demonstrated outcome hierarchy

The registered study **NCT07654036**, *Preliminary Evaluation of a Large Language Model-Based Tool for Complex Surgical Decision Support in Lung Cancer*, compares GAPS-Agent with a general-purpose LLM. Its primary endpoint is an **overall-plan win ratio**, based on blinded experts assigning win/tie/loss judgments. The registration defines the ratio as wins divided by losses and specifies physician-by-case clustered bootstrap inference. ([ClinicalTrials.gov][4])

This is directly relevant to **agent-versus-model comparison**, but the stated primary endpoint is a judgment of overall plan quality. It does **not establish the particular “safety first, then correctness, then latency, then cost” construction you propose**. I found a study registration, not a results publication demonstrating that full framework.

**Taken together:** there are precedents for hierarchical AI-workflow evaluation, separate-axis AI win statistics, and agent-evaluation win ratios. The remaining opportunity is more specific than simply transferring the term “win ratio” into AI.

## 2. What companies already provide—and what would still need to be added

### LangSmith is a practical place to implement your approach

LangSmith documents **custom pairwise evaluators** that receive the outputs of two experiments on the **same dataset example**. The evaluator can also access the full run objects, including intermediate steps and metadata. That is almost exactly the input interface needed for your comparator: two task-matched runs, their final outcomes, their traces, and their resource measurements. ([Docs by LangChain][5])

My proposed addition would be a deterministic comparison layer that applies the prespecified hierarchy, records which tier decided the comparison, and then performs task-level statistical analysis. **I did not find documentation that LangSmith already provides this as a native biostatistical win-statistics method.** Its existing functionality is infrastructure on which the method could be built.

### Google, Patronus, and Anthropic address adjacent pieces

Google’s **LLM Comparator**, described by Kahng et al. in *LLM Comparator: Visual Analytics for Side-by-Side Evaluation of Large Language Models*, supports inspecting pairwise comparisons and understanding when and why one model differs from another. It is relevant to the **comparison interface and diagnostic visualization**, but the documented method is not a prespecified hierarchical composite with win-ratio inference. ([arXiv][6])

Patronus’s **TRAIL: Trace Reasoning and Agentic Issue Localization** evaluates reasoning about agent traces and localization of errors. Its associated tooling addresses failures involving orchestration, tool use, context handling, and related workflow issues. This is relevant to **constructing and validating trajectory-level outcomes**, rather than deciding how to aggregate those outcomes into one prioritized system comparison. ([arXiv][7])

Anthropic’s *Demystifying evals for AI agents* describes combining code-based, model-based, and human graders, and using weighted, all-pass binary, or hybrid scoring. This documents the practical multimetric problem you are targeting, but the article does not present a win-statistics framework. ([Anthropic][8])

The useful distinction is:

**An evaluation harness produces trustworthy measurements. Your proposed statistical layer determines what those measurements imply about which system is preferable.**

Those are complementary components, not competing products.

## 3. Which methodological literature is most useful?

**Buyse’s 2010 paper, “Generalized pairwise comparisons of prioritized outcomes in the two-sample problem,” is the broad foundation.** It explicitly allows multiple outcome types, including discrete, continuous, and time-to-event measurements. Pocock et al.’s 2012 paper, *The win ratio: a new approach to the analysis of composite endpoints in clinical trials based on clinical priorities*, provides the familiar clinically prioritized win-ratio construction, including matched and unmatched comparisons. Your application is therefore better framed around **generalized pairwise comparisons and win statistics**, not restricted to survival-based win ratios. ([PubMed][9])

**DOOR/RADAR is another unusually close analogy.** Evans et al.’s 2015 *Desirability of Outcome Ranking and Response Adjusted for Duration of Antibiotic Risk* first distinguishes overall clinical outcomes, then favors shorter antibiotic exposure among comparable clinical outcomes. The corresponding agent-evaluation proposal would be: first distinguish outcome quality, then prefer lower resource use among sufficiently comparable outcomes. The clinical method is established; that agent interpretation is my proposed adaptation. ([OUP Academic][10])

**AI already has lexicographic multi-objective methods.** Skalse et al.’s *Lexicographic Multi-Objective Reinforcement Learning* optimizes objectives in priority order. This limits another possible novelty claim: priorities themselves are not new to AI. But **optimizing a hierarchy of expected rewards** and **averaging pairwise comparisons made using a hierarchy** are different mathematical operations; they need not produce the same preferred system. ([arXiv][11])

**Pairing and dependence are where more recent statistical work becomes important.** Even and Josse’s *Rethinking the Win Ratio: A Causal Framework for Hierarchical Outcome Analysis* emphasizes that marginal and covariate-conditional comparisons can answer different questions. Fang et al.’s clustered win-statistics paper studies inference under dependence and provides the **WinsCRT** R package. Neither is already a complete solution to the agent setting, but both are substantially closer to the statistical problems than a simple leaderboard win-rate calculation. ([arXiv][12])

## 4. How I would formulate your agent-evaluation framework

The following is a **proposed adaptation**, rather than a claim about an existing implementation.

### Start with the task—not the individual tool call—as the comparison unit

Let task \(i\) be evaluated by systems \(A\) and \(B\), yielding vectors

$$
Y_i^A=(S_i^A,Q_i^A,R_i^A,L_i^A,C_i^A),
\qquad
Y_i^B=(S_i^B,Q_i^B,R_i^B,L_i^B,C_i^B),
$$

where, for example, \(S\) records safety or hard-constraint compliance, \(Q\) validated task success, \(R\) reproducibility or another required quality dimension, \(L\) latency, and \(C\) cost.

For a coding agent, an illustrative ordering could be

$$
\text{hard constraints}
\succ
\text{functional correctness}
\succ
\text{reproducibility}
\succ
\text{latency}
\succ
\text{cost}.
$$

That is **not a universal hierarchy**. A time-critical application may treat latency as a hard constraint. A scientific coding agent may prioritize reproducibility above small improvements in partial task completion. Modularity might matter for production software but be irrelevant for a disposable analysis script.

The comparator should then ask: **What is the highest-priority dimension on which these two runs differ meaningfully?**

Define

$$
h(Y_i^A,Y_i^B)=
\begin{cases}
+1,& A\text{ wins at the first decisive tier},\\
-1,& B\text{ wins at the first decisive tier},\\
0,& \text{the comparison remains tied}.
\end{cases}
$$

The key advantage is interpretability. A task-level decision can say:

> Both systems produced correct, reproducible outputs. Their latency difference was below the prespecified tolerance. System A won because its cost was meaningfully lower.

That is more explicit than an opaque weighted score.

### Define meaningful ties before evaluating the systems

For continuous metrics, exact equality is usually the wrong definition of a tie. A one-millisecond difference should not automatically prevent cost from ever entering the comparison.

For example, the protocol might treat latency differences below a specified absolute or relative tolerance as neutral. That tolerance should reflect the application, not be chosen after seeing which threshold favors a preferred agent.

**Operational equivalence is not the same as a nonsignificant hypothesis test.** The comparator needs a prespecified practical tolerance; it should not decide that two individual runs are equivalent merely because a noisy comparison lacks statistical significance.

Thresholds of minimum important difference are already supported in GPC software such as **BuyseTest**, so this part of the proposal has an established methodological basis. ([CRAN][13])

### Report more than the win ratio

For complete comparisons, let \(W,L,T\) denote wins, losses, and ties, with \(N=W+L+T\). Then report

$$
\widehat p_W=\frac{W}{N},\qquad
\widehat p_L=\frac{L}{N},\qquad
\widehat p_T=\frac{T}{N},
$$

along with

$$
\widehat{\mathrm{WR}}=\frac{W}{L},
\qquad
\widehat{\mathrm{NB}}=\frac{W-L}{N},
\qquad
\widehat{\mathrm{WO}}=
\frac{W+\tfrac12T}{L+\tfrac12T}.
$$

Win ratio, net benefit, and win odds provide complementary interpretations; this is explicitly discussed by Dong et al. in *Win statistics … can complement one another to show the strength of the treatment effect*. ([PubMed][14])

For a **hypothetical** result of 60 wins, 30 losses, and 10 ties:

$$
\mathrm{WR}=2,\qquad
\mathrm{NB}=0.30,\qquad
\mathrm{WO}=\frac{65}{35}\approx1.86.
$$

“WR = 2” means **twice as many prioritized wins as losses**. It does not mean twice the task-success rate. Here, A wins 60% of all comparisons and two-thirds of decisive comparisons.

I would also report **which tier generated each win and loss**. A ratio driven mostly by cost is materially different from the same ratio driven mostly by correctness—even when both follow the same formal hierarchy.

## 5. The most important caveat: pairwise priority does not ensure population-level priority

This is the issue I would make central to the research.

Suppose we compare two agents on 100 tasks using

$$
\text{success}\succ\text{cost},
$$

and define both-failed tasks as ties.

In a hypothetical experiment, both agents succeed on 89 tasks, with B cheaper on every one. A alone succeeds on one additional task. Both fail on the remaining ten.

A therefore has a **90% success rate**, versus **89% for B**. Yet the prioritized comparison produces

$$
W_A=1,\qquad L_A=89,\qquad T=10.
$$

The win ratio overwhelmingly favors B.

There is no mathematical contradiction: **correctness received priority within every individual task pair**, but the many cost-based wins outweighed the one correctness-based loss across tasks.

Consequently, these two policies are different:

> “On each task, correctness takes priority over cost.”

and

> “We will not deploy a system whose population-level correctness is meaningfully worse, regardless of cost savings.”

Your proposed win-statistics framework directly expresses the first policy. To express the second, I would add a **separate deployment gate**, such as a prespecified success-rate noninferiority requirement, followed by prioritized comparisons among eligible systems.

This matters even more for safety. **A favorable aggregate win ratio cannot, by itself, certify acceptable safety.** Rare severe failures should not be allowed to disappear behind numerous small efficiency wins.

This also explains why I would retain the component metrics and an accuracy–cost display. *AI Agents That Matter*, by Kapoor et al., already argues for joint accuracy–cost evaluation and uses Pareto comparisons. Win statistics can add an explicit preference-based summary; they should not erase the tradeoff information that a Pareto analysis preserves. ([arXiv][15])

## 6. Same-task pairing, repeated runs, and trajectory evaluation

### Same-task comparisons should usually be the default

For an offline agent benchmark, I would generally compare

$$
A\text{ on task }i
\quad\text{against}\quad
B\text{ on task }i,
$$

not A on an arbitrary task against B on a different task.

The distinction is not merely statistical efficiency. Comparing outputs across different task difficulties can answer a different question from comparing systems on the same task. This is closely related to the estimand concerns raised by Even and Josse, although the proposed agent design is an adaptation rather than a direct result of their paper. ([arXiv][12])

Resettable agent environments offer a useful opportunity: both systems can be evaluated on cloned initial states, with the same task specification, permissions, and resource limits. Execution order and infrastructure conditions should also be controlled when latency is an endpoint.

### Repeated runs do not create independent new tasks

For stochastic agents, the target should include both **variation across tasks** and **variation across runs of the same task**.

With independently generated replicate sets, one possible task-weighted win-probability estimator is

$$
\widehat p_W
=
\frac1n\sum_{i=1}^{n}
\left[
\frac{1}{R_A R_B}
\sum_{r=1}^{R_A}\sum_{s=1}^{R_B}
\mathbf 1\{h(Y_{ir}^{A},Y_{is}^{B})=1\}
\right].
$$

Each task receives equal weight here, regardless of the number of pairwise replicate comparisons. Different workload weights could be specified when they represent the intended deployment population.

But the \(R_AR_B\) comparisons within a task are **dependent**, because they reuse runs. Treating them as independent observations would exaggerate precision.

For this proposed design, I would ordinarily resample **tasks**, preserving both systems and all repeated runs together. Where tasks share repositories, users, or scenarios, the highest relevant independent cluster may be the appropriate resampling unit. Generalization beyond a fixed benchmark also needs a clear argument about what task population that benchmark represents.

Clustered win-statistics methods provide relevant precedents, but the default analysis for a parallel-arm clinical CRT should not be copied into a task-matched benchmark without checking its assumptions. ([arXiv][16])

### A priority hierarchy is not a chronology of agent steps

I would not automatically define

$$
\text{step 1}\succ\text{step 2}\succ\text{step 3}.
$$

A later failure can be more consequential than an earlier recoverable mistake. Moreover, two agent architectures may reach the same outcome through different numbers and types of steps.

Instead, I would distinguish **task-aligned outcomes** from **diagnostic trajectory measurements**. Examples of candidate trajectory outcomes are unrecovered tool errors, unauthorized external actions, failed verification checkpoints, and reproducibility failures. Raw step count or tool-call count is not automatically a quality measure: an extra verification step may be beneficial.

AgentBoard’s progress-based evaluation and TRAIL’s trace-error localization provide existing approaches to measuring intermediate behavior. They could supply inputs or diagnostics for the proposed framework; neither makes the aggregation problem disappear. ([arXiv][17])

A useful architecture would therefore retain both a **system-comparison summary** and a **failure-diagnostic view**. A win ratio tells us which system is preferred under a rule; it does not, by itself, identify which module caused the difference.

## 7. Where competing risks and multistate models fit

Your competing-risk analogy is useful, but **having several metrics does not itself create a competing-risk problem**. Cost, latency, and correctness can all be observed for the same run.

For the proposed agent setting, competing risks become relevant when terminal events are mutually exclusive under the evaluation protocol. For example, the target event might be **verified autonomous success**, while irreversible failure or human takeover prevents that event from occurring within the autonomous episode.

By contrast, a recoverable tool error followed by a retry is better represented as part of a **multistate or recurrent-event process**:

$$
\text{attempt}
\rightarrow
\text{tool error}
\rightarrow
\text{repair}
\rightarrow
\text{verified success}.
$$

The MAPS-LLM publication is an actual AI-workflow example of making this distinction operational: eligibility determination was analyzed with ineligibility determination as a competing event. ([JAMA Network][1])

For agents, I would also distinguish **budget exhaustion** from missing follow-up. Under a fixed-budget benchmark, a timeout generally means the system did not succeed within the allowed budget. It should not automatically be treated as innocuous censoring and excluded.

These methods answer complementary questions:

**Win statistics:** Which system is preferable under a specified ordering of outcomes?

**Competing-risk or multistate analysis:** How quickly, and through which paths, does a system reach success, failure, or escalation?

A strong evaluation framework could use both without forcing every measurement into one composite.

## 8. Where I think the research contribution lies

I would frame the project as:

### **Task-Matched Prioritized Pairwise Evaluation of AI Agents**

The contribution should not be “we calculated a win ratio.” It should be a coherent answer to three problems.

**First, define the decision being supported.** Is the objective task-level preference, deployment subject to correctness and safety constraints, or selection of the best agent for a particular task class? The hierarchy, task distribution, tolerances, and run-randomness convention jointly define the estimand.

**Second, develop inference that matches how agent data are produced.** Repeated runs, shared tasks, reused outputs, multiple judges, missing traces, and heterogeneous task families create dependence and uncertainty that a naïve count of pairwise wins does not address.

**Third, demonstrate that the framework improves real decisions.** I would compare it with correctness-only rankings, weighted scores, Pareto comparisons, and holistic judge preferences. The empirical test is whether its recommendations are more stable, interpretable, and aligned with prespecified user priorities—not merely whether it yields a statistically significant ratio.

A particularly useful study would show when **pairwise prioritization and population-level constraints disagree**, using both simulations and agent benchmarks. That would turn the caveat above into a substantive methodological contribution rather than hiding it.

For a first empirical starting point, **Real-POCQi is unusually relevant because it releases multiaxis pairwise judgments and analysis code**; for agent-specific development, a controlled benchmark with repeated task-matched runs would be needed to add latency, cost, and trajectory endpoints. ([arXiv][3])

**My bottom line:** your central insight is valuable, but there is already meaningful prior art. The strongest opportunity is to move from loosely aggregated agent metrics to **explicit, task-matched statistical decision rules—with meaningful ties, dependence-aware inference, and safeguards against a favorable composite concealing a worse primary outcome**. That is a much sharper contribution than simply introducing clinical win-ratio terminology to AI.

[1]: https://jamanetwork.com/journals/jama/fullarticle/2830514 "Manual vs AI-Assisted Prescreening for Trial Eligibility Using Large Language Models—A Randomized Clinical Trial | Trials | JAMA | JAMA Network"
[2]: https://news.massgeneralbrigham.org/en/ai-tool-useful-in-array-of-use-cases?utm_source=chatgpt.com "AI Tool Proves Useful in an Array of Use Cases | Mass General ..."
[3]: https://arxiv.org/html/2606.28960v1 "Expert Evaluation of Clinical AI Tools on Real Point-of-Care Clinical Queries"
[4]: https://clinicaltrials.gov/study/NCT07654036?utm_source=chatgpt.com "NCT07654036 | Preliminary Evaluation of a Large Language Model ..."
[5]: https://docs.langchain.com/langsmith/evaluate-pairwise "How to run a pairwise evaluation - Docs by LangChain"
[6]: https://arxiv.org/abs/2402.10524 "[2402.10524] LLM Comparator: Visual Analytics for Side-by-Side Evaluation of Large Language Models"
[7]: https://arxiv.org/abs/2505.08638?utm_source=chatgpt.com "TRAIL: Trace Reasoning and Agentic Issue Localization"
[8]: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents "Demystifying evals for AI agents \ Anthropic"
[9]: https://pubmed.ncbi.nlm.nih.gov/21170918/ "Generalized pairwise comparisons of prioritized outcomes in the two-sample problem - PubMed"
[10]: https://academic.oup.com/cid/article-abstract/61/5/800/304719?utm_source=chatgpt.com "Desirability of Outcome Ranking (DOOR) and Response Adjusted ..."
[11]: https://arxiv.org/abs/2212.13769 "[2212.13769] Lexicographic Multi-Objective Reinforcement Learning"
[12]: https://arxiv.org/abs/2501.16933 "[2501.16933] Rethinking the Win Ratio: A Causal Framework for Hierarchical Outcome Analysis"
[13]: https://cran.r-project.org/package%3DBuyseTest "CRAN: Package BuyseTest"
[14]: https://pubmed.ncbi.nlm.nih.gov/35757986/ "Win statistics (win ratio, win odds, and net benefit) can complement one another to show the strength of the treatment effect on time-to-event outcomes - PubMed"
[15]: https://arxiv.org/html/2407.01502v1 "AI Agents That Matter"
[16]: https://arxiv.org/abs/2604.18341?utm_source=chatgpt.com "Statistical inference with win statistics in cluster-randomized trials with composite outcomes"
[17]: https://arxiv.org/abs/2401.13178?utm_source=chatgpt.com "AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents"
