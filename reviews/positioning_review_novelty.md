# Adversarial novelty review of `submission/positioning_memo.md`

Reviewer role: senior statistician (win statistics, GPC, anytime-valid inference). Date: 2026-09-17. Scope: the positioning memo, `evidence/{venue_and_novelty,theory_design,empirical_feasibility,lit_winstats,lit_sequential,lit_agenteval,asynchronous_novelty}.md`, `reviews/{RESPONSE_LEDGER,round2_theory_independent,round2_empirical_independent}.md`, the conjunction theorems in `paper/theory.tex`, `results/{online_methods_results,cs_width}.csv`, `results/benchmarks/tau2_rankings.csv`, and the source-verification log in Section 8. This is a model-assisted internal review, not human peer review.

Prior belief going in: "old GPC plus a standard confidence sequence." Belief after review: for the theory, that is essentially correct and the memo already concedes it; the memo's one claimed new theorem (3(b)) is mis-stated; the strongest material is the empirical decision-disagreement evidence, which is partially pre-empted by a paper posted ten days ago on the same data. The plan as written is a borderline-reject methodology paper. It is convertible into a borderline-accept evaluation-methodology paper by demoting the theorems, adding two missing comparators, and making the decision evidence carry the paper.

---

## 1. Verdict in one paragraph

The memo is honest to a fault about labels (restatement / corollary / adaptation) and that honesty will be read by reviewers exactly as written: two propositions and three theorems in the main text, of which every part except Theorem 3(b) is labelled a restatement, corollary or adaptation, and 3(b) as stated is false (Section 3.1). The multinomial "one set for every win statistic" result is a projection of Lindon and Malek's convex set, which their own Corollaries 2.5 and 3.2 already perform for coordinates and contrasts. The disjoint-pair bounded-score CS is Waudby-Smith and Ramdas (or Howard et al.) on a [-1,1] score, an instance of Ham et al.'s design-based CS, and there exists an unmentioned finite-sample, all-pairs, anytime-valid alternative (Manole and Ramdas 2023) under the same i.i.d. assumption the memo's Theorem 1 imposes. The estimand map (C1) is Mao 2018 / Even and Josse 2026 with task as the covariate. What is left that is genuinely the authors' is (i) the reversal and rule-disagreement evidence on released tau2-bench, SWE-bench Lite and HAL trajectories with task-clustered uncertainty, (ii) the paired-versus-cross-arrival sign flip in replay, and (iii) a protocol that couples a hierarchical preference to sequential component guardrails. Huang (arXiv 2609.07785, 2026-09-07) already reports on the same tau2-bench and SWE-bench data that "proxy labels and utility rules can also change which system is selected", so (i) needs a sharper delta than "three rules, three winners".

---

## 2. Fatal flaws (would cause rejection if the paper delivers exactly this plan)

### F1. The paper's only "new" theorem (Theorem 3(b)) cannot be true as stated

Memo, Section 3, Theorem 3(b): "Drifting: a sequence of distributions exists under which per-gate alpha deploys while some gate is currently false with probability -> 1; budgets summing to alpha restore control."

For the confidence-sequence rule this contradicts a one-line union bound. Let gate j deploy only when its lower bound satisfies L_{jn} > c_j, and let each gate's CS be a valid level-alpha sequence for its running conditional average mu-bar_{jn}. The error event E = {exists n: rule deploys at n and exists j: mu-bar_{jn} <= c_j} satisfies, on E, L_{jn} > c_j >= mu-bar_{jn}, i.e., gate j's CS fails at time n. Hence E is contained in the union over j of {CS_j ever fails}, and P(E) <= sum_j alpha_j = m*alpha under per-gate alpha. With m gates and alpha < 1/m no sequence of distributions drives P(E) to 1. `paper/theory.tex` (Theorem `thm:drift_gate`) states only the sufficient direction (split budget gives alpha) and is correct; the memo's promised counterexample is new text and is wrong.

What is true and provable: under drift with the CS rule, per-gate alpha gives at most m*alpha rather than alpha, and there exist alternating-block constructions in which the m failure events are nearly disjoint so that P(E) approaches m*alpha. That is a remark, not a theorem, and it is the standard "IUT needs a fixed false null; a time-varying null needs simultaneous coverage" observation. For the betting rule, the drift theorem in `theory.tex` does not apply at all (a betting gate is a test supermartingale under the stepwise null mu_{ij} <= c_j for all i, not under a running-average null), and no alpha allocation repairs that; the memo must not extend 3(b) to betting without a separate proof.

Resolution: delete the "probability -> 1" claim; state 3(b) as "per-gate alpha controls the drifting error only at level m*alpha; splitting restores alpha; the stationary IUT proof does not transfer because the violating index may change with n", with a small simulation (E2b) showing the excess. Label it a remark. Do not present it as the paper's novel theorem, because it will not survive a competent reviewer and its failure would taint the sound results around it.

### F2. As planned, the main text has no result a reviewer will accept as a contribution

By the memo's own labels: Prop 1 adaptation/restatement; Prop 2 restatement; Thm 1 corollary; Thm 2 adaptation; Thm 3(a),(c) adaptation; 3(b) see F1. The ICLR analysis the memo itself cites (Kargaran et al., arXiv 2511.15462; verified) finds "Novelty & Contribution" the dominant weakness for low-rated papers, with "overlap with prior work, lack of originality, and lack of clear contribution" the most frequent subcategories. A theorem-forward paper whose theorems are all instances of cited machinery lands in that bucket.

Resolution: do not lead with theorems. Restructure as an evaluation-methodology paper (the genre of Kapoor et al. and HAL, which the field accepts) whose contribution is the decision protocol plus evidence that current practice reaches different, sometimes unsafe, decisions. Collapse Theorems 1-3 into one "Guarantees" section with propositions stated in two lines each and proofs in the appendix; spend the recovered space on Section 6.

### F3. The online estimand the paper proposes to monitor is one the paper's own evidence shows to be decision-irrelevant

The cross-arrival design compares system A on request i with system B on request i+1 through a hierarchy whose lower tiers are cost and tool calls. Comparing A's cost on an easy request with B's cost on a hard request is not a comparison of systems; it is a comparison of systems confounded with request difficulty, and the retail replay (paired NB +0.067 vs cross-arrival NB -0.014, memo Section 0.1) demonstrates exactly that. The memo frames the sign flip as "Hand's paradox on real data"; a reviewer will read it as "the quantity your online gate monitors can have the opposite sign from the quantity you care about, so what does a green light from your gate mean?" Even and Josse make this point about tau_pop versus tau_* in the clinical setting; here the mechanism is more damaging because the tie-breaking tiers are resource metrics that vary more across tasks than across systems.

Resolution: either (a) make prespecified request strata (Lemma A5) mandatory in the online protocol and show in replay that within-stratum cross-arrival NB recovers the paired sign, or (b) restrict the online claims to the shadow design (same request, both systems) for outcomes computable without user interaction, and present single-exposure A/B only as a guardrail stream for component metrics (success, safety), not for the hierarchy. Either way, say explicitly which agent settings admit which design; (b) is closest to what Statsig-style shadow evaluation actually does.

---

## 3. Major concerns (each would cost a point or two; each has a fix)

### M1. Theorem 1 overclaims relative to Lindon and Malek

Verified from the arXiv HTML of Lindon and Malek (NeurIPS 2022): Theorem 2.4 gives the convex CS for theta; Corollary 2.5 projects onto coordinates by a convex program; Corollary 3.2 projects onto all contrasts sum a_i delta_i by convex optimization; the Poisson section handles intensity ratios. The memo's sentence "the functional step and simultaneity are ours" is therefore not accurate; simultaneity over all functionals of one confidence set is a tautology and the projection device is in the source. The WR bound by level sets (p_W - r p_L <= 0 is linear) is a one-line remark. What is the authors' is only the modelling choice that each randomized disjoint pair is one draw from a 3^T-cell multinomial.

Additionally, the executed width comparison used a 3-cell uniform prior (`experiments/run_online_methods.py`, `PRIOR = (1., 1., 1.)`), not the 3^T-cell set that Theorem 1 advertises. With T = 3 tiers that is 27 cells, and a uniform Dirichlet over 27 cells will be far wider at n = 100-1,000 than the 15-55 percent penalty already measured for 3 cells.

Fix: phrase as "we apply Lindon and Malek's CS to the comparison-cell vector and note that NB, WR, WO, DOOR and all tier contributions are projections of one set" in a remark; measure the width of the 3^T-cell set (uniform and informative prior) before claiming it as a reporting device; if it is unusable at realistic n, say so and keep only the 3-cell version for the top-level win statistics.

### M2. A finite-sample, all-pairs, anytime-valid competitor exists and is not cited

Manole and Ramdas, "Martingale Methods for Sequential Estimation of Convex Functionals and Divergences", IEEE Trans. Inf. Theory 2023 (arXiv 2103.09267; PDF text extracted and read, Section 4.2): for a symmetric integrable kernel h, the U-statistic U_t is a reverse martingale with respect to the exchangeable filtration, and "a straightforward generalization of Theorem 7 can be used to derive two-sided confidence sequences for Phi(P) centered at U_t for all symmetric h"; their bounds pay an iterated-logarithm price over the fixed-time bound (rate sqrt(log log t / t)). For a paired i.i.d. stream Z_i = (X_i, Y_i) and the pair-symmetrized kernel h(Z_i, Z_j) = [k(X_i, Y_j) + k(X_j, Y_i)]/2 with k the bounded hierarchical score, this yields a nonasymptotic time-uniform CS for the all-pairs net benefit under exactly the i.i.d. assumption Theorem 1 imposes. It is therefore strictly more efficient than the disjoint-pair estimator (Hoeffding: Var(k) = zeta_10 + zeta_01 + zeta_11 versus zeta_10 + zeta_01 for the U-statistic; the loss is the interaction term, which is zero for a pure success kernel and up to one third of the variance for a pure Mann-Whitney cost kernel) and it has the LIL rate the normal-mixture route lacks. `lit_sequential.md` states "no published finite-sample CS for ... net benefit of a ternary stream"; that statement is now false in spirit, because Manole-Ramdas plus a one-line kernel construction gives one.

Fix: cite it; add it to E1/E8 as the i.i.d. all-pairs baseline; then the honest positioning of the disjoint-pair route is "it survives adaptive orientation and drift and gives a design-based running-average target (Ham et al.), at a measured efficiency price relative to Manole-Ramdas under i.i.d." That is a defensible, quantified statement; the current "finite-sample vs asymptotic (Cai-Hu-Li)" framing is not the relevant comparison.

### M3. C4 is partially pre-empted by Huang (arXiv 2609.07785)

Verified from the arXiv HTML: Huang analyzes tau2-bench ("four system configurations with common support over airline, retail, and telecom") and SWE-bench with paired/task-resampling bootstrap, a 2-percentage-point margin, a linear utility "success minus lambda times agent-side cost", reports lambda = 0.0514 as "the first point-estimate cost-only switch between Claude 3.7 Sonnet and o4-mini on tau2-bench", and concludes that "utility rules can also change which system is selected". The memo's "three rules, three winners" in retail is a different instance of the same finding on the same data. Huang does not mention win ratio, net benefit, hierarchical outcomes or sequential inference (verified), so the delta exists, but it is narrower than the memo implies.

Fix: state the delta precisely: (i) the reversal is not "rules disagree" but "a preference statistic with a valid interval is favorable while the primary component is significantly worse, and only a guardrail catches it" (Fu-type, tier-decomposition explained); (ii) the paired-vs-cross-arrival design flip; (iii) sequential resolution with error control; (iv) the priority-swap sign flip. Put Huang's lambda rule in the disagreement matrix as a comparator and cite it in the introduction, not only in related work.

### M4. The reversal cases are driven by a 6x cost gap; a reviewer will call them manufactured

`tau2_rankings.csv`: Claude 3.7 mean cost 0.335 (retail) and 0.582 (telecom) versus 0.057 and 0.092 for o4-mini. With success tying on most tasks, any rule that looks at cost at all will penalize Claude, and a 5 percent relative tolerance makes essentially every joint-success pair a cost win for o4-mini. The interesting decision problems are near-frontier comparisons (o4-mini vs GPT-4.1: costs 0.050 vs 0.054), where the hierarchy currently yields mostly ties plus a mild airline edge.

Fix: report the reversal, but add a prevalence analysis across all system pairs (including HAL's 15 contrasts) of how often NB and the primary component disagree in sign or in interval exclusion, as a function of the cost ratio and tolerance; and add at least one comparison where the reversal is not a cost-ratio artefact (e.g., tool-call tier or a heavy-tailed latency tier where a pairwise sign statistic and a mean-based rule diverge for robustness reasons). The robustness-to-heavy-tails argument is the strongest reason to prefer a pairwise sign statistic over a linear utility and it is absent from the memo.

### M5. It is not shown what the hierarchy adds beyond "success non-inferiority AND cost superiority"

By the tier-decomposition identity (Prop 2), with binary success first and joint failures tied, NB = (p_A - p_B) + P(both succeed) x NB_cost(both succeed). So the guarded rule is "success NI gate, plus a positive combination of the success difference and the cost preference among joint successes." In the reversal cases the guardrail does all the work; in the airline case a plain "success NI and cost lower" rule would also resolve. Reviewers from the experimentation community (the Spotify papers cited) will ask why they should adopt a composite at all.

Fix: give the decision-theoretic answer explicitly (a prespecified lexicographic preference at the pair level, data-independent priority, one interval instead of two dependent ones, robustness of the cost tier to outliers) and demonstrate a case where "NI + component superiority" and the guarded hierarchical rule disagree in a way that matters (e.g., A cheaper on the tasks both solve but more expensive overall because it attempts harder tasks; or heavy-tailed cost).

### M6. Shadow execution does not identify the same-request preference for interactive agents

C1(d) claims shadow execution "identifies the same-request preference at two runs per request". For agents whose outcome depends on a live user (the tau-bench setting the paper uses), the shadow arm has no user; only the served arm completes the conversation. Shadow identification holds only for outcomes computable without user interaction (verifiable tasks, cost, latency, policy checks). This is exactly the regime in which the offline replicate design already applies, so the "three designs identify three estimands" story has a hole.

Fix: state the scope condition; for interactive agents, say plainly that only the offline replicate design identifies tau_*(task) and that online single-exposure data identify tau_pop (per stratum) only.

### M7. Comparators that decide the paper are all "to do"

E1 lists the Kotawala paired e-process (verified: Section 6.5 and Appendix C of arXiv 2605.30315 construct a paired-Bernoulli mixture e-process; no ties, cost or hierarchy), Bergemann-Hanson GST, Cai-Hu-Li AsympCS and Matsouaka fixed-n as not run; E8 (efficiency ratio) is not computed; the drift panel E2b is not run; Manole-Ramdas (M2) is not even listed. Without these the paper cannot state the price of its route, and a reviewer will assume the worst. The executed evidence against the "repeatedly inspected Wald" baseline is not evidence of anything a 2026 reviewer does not already know.

Fix: minimum viable set by 09-24: Manole-Ramdas all-pairs CS, Kotawala paired e-process (success tier only), Bergemann-Hanson GST at K = 5, WSR betting (done), 3-cell multinomial (done); report width at n in {50, 100, 250, 1,000} and stopping time on one null and two alternatives calibrated to tau2 cell frequencies. Drop Cai-Hu-Li if time is short (it is one-sample and asymptotic; Manole-Ramdas is the right finite-sample comparison).

### M8. The empirical base is thin for a paper whose value is empirical

Three 2025 models, four shared seeds per domain (R2-E1, cross-task dependence through shared seeds not modelled), tau2 tasks since corrected (tau3 task fixes), SWE Lite with two 2024 systems and two dominant repositories (R2-E2), HAL single trial, replay from a finite pool resampled with replacement (`run_replay.py`), a USD 4 twelve-task pilot as the only prospective data. The memo says all of this honestly. Honesty limits the damage but does not remove it: the paper's claim is about deployment decisions, and none of the data are deployment data.

Fix: (i) add AgentBoard baseline logs or HAL's other suites if any can be processed in a day, to get a fourth workflow family; (ii) make the resolution-fraction curve across all system pairs (E6) the main online figure, since it is the one output that scales with what the data can support; (iii) title the online section "randomized stream replay" in the heading, not only in the text.

### M9. The 3^T-cell family and threshold grids collide with the "prespecified hierarchy" defence

Objection 5 in the memo is answered with a timestamped protocol and a sensitivity grid. But Theorem 1 then proposes simultaneous inference over a family of hierarchies and tolerance grids from one set, which invites the reviewer to ask which is the confirmatory analysis. Li-Fan-Yang (verified: min-NB over protocol-consistent rules with IUT inversion, fixed-sample) solve this by declaring the worst case the estimand.

Fix: pick one: either the primary hierarchy is confirmatory and the grid is descriptive (current), or the worst-case NB over the prespecified family is the primary estimand (Li-Fan-Yang sequentialized, Theorem 3(c)). Do not offer both as headline devices.

### M10. Positioning omits the asynchronous partial-score work entirely

`evidence/asynchronous_novelty.md` and `paper/asynchronous.tex` (round-3 reviewed) contain the one construction in the project that uses agent-trace structure specifically (certifying a pair outcome from partially resolved tiers before the slow episode completes), with the Henzi-Ziegel and Choe-Ramdas precedents credited. The positioning memo does not mention it. If it is excluded for space, the memo should say so; if included, it is a better candidate for "agent-specific method" than Theorem 3(b), though its transfer proof is elementary and its precedents are close.

Fix: decide explicitly; if included, one proposition plus the calendar-time panel (E9) and no claim beyond "threshold-crossing error control".

---

## 4. What is genuinely new versus restated (my table, not the memo's)

| Item | Status | Closest source (verified in this pass unless marked) |
|---|---|---|
| Hierarchical kernel, NB/WR/WO/DOOR relations, 3^T cells | Restatement | Buyse 2010; Dong et al. 2023; McCoy 2026 (verified abstract) |
| Compensation counterexample / tier decomposition | Restatement | Fu 2026 (verified via Europe PMC REST: "treatment has higher marginal success probabilities on both endpoints, yet the win ratio is below one"); Verbeeck 2019 (project file) |
| Cyclic-coupling non-identification | Restatement | Mao 2018; Even and Josse 2026 (project files) |
| Offline tau_*(task) with exact matching; shared-seed lemma | Adaptation (small, useful) | Even and Josse Theorem 1 (project file); the shared-seed mixture identity is the authors' |
| Pair-randomized HT score and running-average CS | Adaptation | Ham et al. 2024/2026 (project file); Howard et al.; Waudby-Smith and Ramdas |
| Multinomial CS for every win statistic | Corollary; the projection device is in the source | Lindon and Malek 2022, Theorem 2.4, Corollaries 2.5 and 3.2 (verified HTML) |
| Finite-grid betting validity | Adaptation | Waudby-Smith and Ramdas (project file) |
| Stationary IUT gate | Restatement (Berger-type IUT; Spotify papers, project file) | Schultzberg et al. |
| Drifting gate: per-gate alpha insufficient, split suffices | Remark; the memo's "-> 1" version is false | Union bound |
| Worst-case NB over a family, anytime | Trivial extension (min of simultaneous bounds) | Li-Fan-Yang 2026 (verified abstract) |
| Completed-prefix delay display | Adaptation | Lindon and Kallus 2026; Bergemann-Hanson fixed T (project files) |
| Asynchronous partial-score enclosure | Adaptation with agent-specific content | Henzi and Ziegel 2022 + correction; Choe and Ramdas (project file) |
| Reversal evidence with task-clustered intervals on released trajectories | New, partially anticipated | Huang 2609.07785 (verified: same data, linear utility, "utility rules can change which system is selected") |
| Paired vs cross-arrival sign flip in replay | New as evidence; mechanism known | Even and Josse Hand's-paradox example (project file) |
| Guarded sequential protocol as a package | New as a protocol; each piece known | Karampatziakis et al. 2021 deployment gate (project file) |

---

## 5. Suggestions, in priority order for a 2026-09-25 deadline

1. Fix F1 today: rewrite Theorem 3 as one proposition (stationary IUT at alpha; drifting needs split, per-gate gives m*alpha; worst-case family by minimum), proofs in the appendix, and run E2b to show the excess under alternating blocks. Remove "-> 1".
2. Reframe (F2): title and abstract lead with the decision problem and the empirical findings; theorems become "Guarantees" propositions with citations in their statements ("by Lindon and Malek Theorem 2.4", "an instance of Ham et al."). Abstract C is closest to this; adopt it with the Huang comparison added.
3. Add Manole-Ramdas as the i.i.d. all-pairs finite-sample baseline (M2) and Kotawala's paired e-process on the success tier (M7); compute E8 on tau2 cell frequencies. State the disjoint-pair price in one sentence in the abstract if it is material.
4. Resolve F3 by protocol: stratified cross-arrival or shadow-only for the hierarchy; single-exposure A/B for component guardrails. Show the within-stratum replay.
5. Expand the reversal evidence (M3, M4, M5): prevalence across all pairs versus cost ratio and tolerance; one non-cost-ratio reversal; the "NI + component superiority" rule in the disagreement matrix; Huang's lambda rule and PSNB as rows.
6. Measure the 3^T-cell multinomial width (M1) before it appears in a theorem; if unusable, keep the 3-cell version only.
7. Add the M6 scope condition on shadow designs to Proposition 1.
8. Cite interleaving (Chapelle et al. 2012; Kharitonov et al. 2015, both in `lit_sequential.md`) as the ancestor of online ternary paired evaluation and explain why agent episodes cannot be interleaved; an IR reviewer will otherwise raise it.
9. Remove UNVERIFIED items from the paper text (HAL cost double-counting; MAPS-LLM WR 1.90) or verify them.
10. Decide M10 (asynchronous section in or out) and M9 (confirmatory vs worst-case estimand) and write the decision into the protocol file with a timestamp.

---

## 6. Things the memo gets right that should be kept

- Refusal to claim "first sequential win statistic", "first anytime-valid LLM evaluation", "first hierarchical comparison of AI systems"; all three are correctly identified as false.
- Task as the independent unit; off-diagonal seed pairs as primary; pointwise-interval labelling; replay labelling.
- Honest reporting of the multinomial width penalty and normal-mixture conservatism.
- The reference-list corrections in `lit_winstats.md` Section 1 (Luo et al. authorship; Dong 2020 vs 2023; WINS vs WR; Wang and Pocock 2016; Gasparyan 2021), which will prevent easy reviewer catches.

---

## 7. Predicted outcome

If the paper delivers exactly the memo's plan (theorem-forward main text with the labels as given, Theorem 3(b) as stated, comparators E1/E7/E8 still "to do", replay-only online evidence): ICLR rating 4 (borderline reject), with typical reviewer text "well written and careful, but the statistical contribution is an application of known confidence sequences to a known composite; the empirical findings are interesting but limited to three archived models". If items 1-5 of Section 5 are done: 5-6, with acceptance depending on whether the area chair values the protocol-plus-evidence genre.

---

## 8. Source verification log for this review

| Source | How opened | What was verified |
|---|---|---|
| Manole and Ramdas, IEEE TIT 2023, arXiv 2103.09267 | arXiv abstract page; PDF downloaded and text extracted; Section 4.2 read | U-statistic U_t is a reverse martingale for symmetric integrable h; "a straightforward generalization of Theorem 7 can be used to derive two-sided confidence sequences for Phi(P) centered at U_t for all symmetric h"; iterated-logarithm price over fixed-time bounds; MMD corollary at rate sqrt(log log t / t) |
| Lindon and Malek, NeurIPS 2022, arXiv 2011.03567 | arXiv abstract and HTML | Theorem 2.4 CS; Corollary 2.5 coordinate projection by convex program; Corollary 3.2 all contrasts; no ties, ordinal or pairwise-comparison data |
| Huang, arXiv 2609.07785 (submitted 2026-09-07) | arXiv abstract and HTML | tau2-bench (four configurations, three domains) and SWE-bench; task-resampling bootstrap; 2-pp margin; linear utility with lambda; lambda = 0.0514 switch; "utility rules can also change which system is selected"; no win ratio / NB / sequential inference |
| Kotawala, arXiv 2605.30315 (2026-05-28) | arXiv abstract and HTML | Section 6.5 anytime-valid leaderboard testing; paired-Bernoulli mixture e-process (Appendix C); 2.15x threshold inflation at N = 12,032; no ties, cost, latency or hierarchy |
| Kargaran et al., arXiv 2511.15462 | arXiv abstract and HTML | Novelty and contribution the top weakness for low-rated ICLR papers; subcategories "overlap with prior work, lack of originality, and lack of clear contribution" |
| Fu, Statistics in Medicine 2026, doi 10.1002/sim.70580, PMID 42082167 | Europe PMC REST API record (publisher and PubMed pages returned 403 / cookie wall) | Title "When better is worse: a paradox of the win ratio and net treatment benefit"; treatment better on both binary marginals yet WR < 1 via primary-tie-stratum reweighting |
| Li, Fan and Yang, arXiv 2608.29857 (2026-08-30) | arXiv abstract | Estimand = smallest NB among protocol-allowed rules; IUT inversion; discrete hierarchies and threshold ranges; fixed-sample language |
| McCoy et al., arXiv 2607.22950 (2026-07-24) | arXiv abstract | PSNB replaces reach-probability weights with a prespecified charter |
| Shekhar and Ramdas, arXiv 2112.09162 | arXiv abstract | IPM-based sequential two-sample testing; no P(X > Y) functional |
| Even and Josse; Ham et al.; Bergemann-Hanson; Zhang-Wu; Cai-Hu-Li; Henzi-Ziegel; Choe-Ramdas; Chapelle et al.; Kharitonov et al. | NOT re-opened in this pass; statements rely on the project's evidence files | UNVERIFIED by me; treat as the previous agents' verification |
| `experiments/run_online_methods.py` | Read locally | Multinomial comparison uses `PRIOR = (1., 1., 1.)`, i.e., 3 cells, uniform |
| `experiments/run_replay.py` | Read locally | Replay draws from finite per-model pools with a random generator; it is resampling, not live traffic |

Web search budget was exhausted before this review began; all web verification above used direct fetches of known URLs. No sweep for a "hierarchical win statistic + LLM agent" paper newer than the six agents' sweeps was possible; the absence of such a paper is therefore UNVERIFIED as of today beyond what the evidence files record.
