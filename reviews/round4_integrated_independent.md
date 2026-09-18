# Round 4: independent integrated scientific review

Reviewed September 17, 2026, America/New_York. This is a fresh AI scientific review, not human peer review, proof certification, or an acceptance prediction. The reviewer did not develop the manuscript and made no manuscript, analysis, repository, or API-experiment changes. This report is the only review output created.

**Closeout status:** I rechecked the latest integrated sources after sending findings to the lead agent. The manuscript now explicitly discloses that accrued-cost early certificates have not been validated in real traces; states that all four corrected-grader cases are null cases with no corrected-rule alternative; points readers to the supplied objective/Pareto CSVs; and distinguishes per-episode endpoint caps from study-level monetary interruption. The prospective and DM main/appendix sources are now included. Those four wording/reporting items are **resolved**, and are retained below as the audit trail, not as outstanding repair demands. The remaining concern is scientific contribution and empirical scope. Final packaged reproducibility and visual/page-limit certification remain the lead agent's release checks.

## Overall assessment

The paper now gives a coherent and largely technically defensible evaluation protocol. Its strongest features are the clear distinction among comparison populations, the separation of pairwise priority from component noninferiority, and the careful treatment of incomplete outcomes without selecting fast completions. I did not find a fatal error in the stated core probability arguments or in the new grader-error bound. The stationary intersection–union argument, drifting-target qualification, positive-factor partial-wealth construction, and distinction between a threshold guarantee and a calendar-time e-process are all important and appropriately qualified.

My simulated ICLR assessment is **borderline to weak reject in its present scientific form**, primarily for incremental contribution and limited evidence for the most agent-specific mechanism, rather than an identified false theorem. The paper is plausible as a focused evaluation-methodology submission. It is much less persuasive as a substantial new statistical-methods contribution: win aggregation, identification distinctions, bounded-mean monitoring, conjunctive gates, and worst-case pending-outcome reasoning have close precedents. The current manuscript acknowledges this honestly. Completing the submission artifacts can make it a submission-ready document; doing so does not resolve that scientific competitiveness question.

No arbitrary experiment count is required to make this judgment. The consequential missing evidence is specific: the usefulness and reliability of early score certificates derived from actual agent traces. Another large batch of the existing synthetic streams would not fill that gap. A carefully scoped paper can instead state that this utility remains unvalidated and rely on its protocol synthesis and historical findings, accepting the resulting novelty risk.

## Scope and verification

Read the current `paper/main.tex`, `theory.tex`, `asynchronous.tex`, the synthetic/public/asynchronous/ablation result and appendix sources, the related-work audit evidence, the new grader code, core score and betting implementation, principal simulation generator, asynchronous generator, the isolated complete-data DM implementation and reproduction script, prospective protocols and postprocessor, final cohort summary, result CSVs, and reproduction/package entrypoints. Line pointers below refer to the inspected sources; concurrent manuscript integration may shift them.

The prospective paragraph and DM comparison were being integrated by the lead agent. I reviewed their recorded results directly instead of treating a missing inclusion during integration as a scientific defect. I did not independently rerun every large simulation, re-download every historical source, audit every original trace, or visually certify the final PDF. I reran the ablation's implementation consistency checks read-only, recomputed its four true/measured population contrasts, and checked the recorded ablation source, core, reused-generator, and protocol hashes; all matched. The DM archive records exact reproduction of all 64 reference rows, with zero numeric difference; this review inspected that record and formulas, rather than claiming a second full independent reproduction.

For novelty, I reopened primary text for [Choe and Ramdas, Combining Evidence Across Filtrations](https://arxiv.org/html/2402.09698v5), [Even and Josse, Rethinking the Win Ratio](https://arxiv.org/html/2501.16933v4), and [Real-POCQi](https://arxiv.org/html/2606.28960v1). Choe and Ramdas explicitly distinguish probability-valid lifting from expectation-valid e-process lifting; Even and Josse distinguish individual, same-covariate, and population comparisons; Real-POCQi already uses net win differences in AI evaluation. These support the manuscript's restrained attribution. The local audit additionally identifies Henzi–Ziegel's pending-outcome construction and correction as close precedents. The correction's publisher page did not reopen successfully during this review, so I do not claim a fresh full-text verification of that correction. This remains a targeted novelty assessment, not an exhaustive priority certificate.

## Prioritized findings

### 1. The most distinctive operational claim is supported only by a constructed reveal simulation

**Priority:** high for scientific contribution; not a demonstrated theorem error.

**Status:** wording repaired in the latest `paper/main.tex` limitations paragraph. The underlying empirical scope limitation remains.

**Locations:** `paper/main.tex:269–324`; `paper/asynchronous.tex:247–300`; `experiments/run_async_experiment.py:56–104, 121–152`; `paper/async_appendix.tex:16–43`; prospective final cohort summary.

The theory permits useful certificates based on accrued cost and irreversible task-state information. The illustrative example of a successful A at cost 1 defeating a pending B already at cost 2 is convincing mathematically. The actual delay study does not implement that example or reconstruct such certificates from agent logs. It masks final success bits and final cost signs according to a synthetic reveal schedule. When cost is unrevealed it allows all three signs; it does not use a growing observed cost lower bound. The prospective pilot supplies completed outcomes and missing-cohort support bounds, but does not validate early trajectory certificates or their calendar-time savings.

The reported 41.285-to-22.363 tick reduction is a legitimate paired operating-characteristic result for the frozen mechanism. The proof also legitimately gives non-later stopping against its matched completed-prefix comparator. Neither result establishes how much useful early information an actual evaluation harness exposes, or whether apparent task success remains final after verifier and environment updates.

**Necessary wording:** “The delayed-feedback study evaluates synthetic partial endpoint disclosures. We have not established the availability or practical gains of trace-derived early certificates in an operational agent harness.” Retain the existing explanation that the magnitude depends on the reveal mechanism.

**Contribution-enhancing analysis, if pursued:** replay existing recorded trajectories under an explicit observation policy, reconstruct only information actually available at each update, verify every proposed enclosure against its final score, and report certificate availability and unresolved width before completion. No deployment crossing or predetermined large sample is needed to answer this feasibility question. If the traces do not contain sufficient intermediate verified state, report that limitation rather than fabricating an early-observation stream from final labels.

### 2. The grader correction is mathematically valid, but the experiment never includes an alternative for the corrected rule

**Priority:** high interpretive clarification; no proof repair required.

**Status:** resolved in the latest `paper/decision_ablation_appendix.tex:67–70`, which explicitly states the .07 threshold and absence of a corrected-rule alternative.

**Locations:** `paper/decision_ablation_appendix.tex:25–66`; `paper/decision_ablations.tex:14–22`; `experiments/run_decision_ablations.py:140–145, 278–311`; `results/decision_ablation_grader_truths.csv`.

The proof is correct under the stated iid pair law. A changed success difference is bounded by the sum of the two label-error indicators; a changed hierarchical sign is bounded by twice their union indicator. Hence the mean biases are bounded by epsilon and 2 epsilon. If a true deployment requirement fails, its corresponding shifted measured requirement also fails, so the fixed-null intersection–union argument applies. No independence between the two arms' label errors is needed for these union bounds. The simulation's independent noise is a sufficient stronger condition. The manuscript correctly says that unknown estimated error rates and temporally adaptive error mechanisms require additional justification.

All four cases use epsilon_A = epsilon_B = .05, giving epsilon = .10. The corrected success threshold is consequently **measured Delta_S > .07**. Every one of the four cases has a measured success difference below .07, and every `bound_aware_objective_true` entry is false. Thus the zero deployment rate is behavior under the corrected rule's own null in all four cases. This is not merely limited power from 500 repetitions or 6,000 pairs; none of these generating laws satisfies that rule's population alternative.

The favorable differential error example is a clear measurement demonstration: true Delta_S = -.04 becomes measured Delta_S = +.012, and measured-label guarded inference approves 489/500 streams. That is not a Type I error for the measured target. It is a wrong practical conclusion about true success, exactly as the paper mostly explains. The reverse example shows lost detection of a true efficiency gain.

**Necessary wording:** replace the narrower “does not establish efficacy ... at small effect sizes” qualification with “No simulated case satisfies the corrected rule's shifted deployment region; therefore these runs assess its conservatism under the stated noise laws but do not assess its power under a corrected-rule alternative.” Keep the correction framed as a sensitivity guarantee. A positive alternative is necessary only if claiming useful corrected-rule power, not to retain the valid bound or the measurement-error lesson.

### 3. The appendix does not contain the objective/Pareto results promised in the main text

**Priority:** medium; concrete reporting repair using existing results.

**Status:** resolved through the alternative remedy: the latest main paragraph now points to the supplied CSV tables rather than claiming the appendix contains all objective/Pareto results. The existing figure/table remains an optional presentation improvement.

**Locations:** `paper/decision_ablations.tex:11–12`; `paper/decision_ablation_appendix.tex`; `experiments/build_ablation_paper_results.py:12–35, 36–111`; `results/decision_ablation_population.csv`; `results/decision_ablation_objectives.pdf`.

The main text says population Pareto descriptions and all comparisons appear in the appendix. The inspected appendix contains objective definitions and the grader figure, but neither the existing objective heatmap nor a table of population objective values/Pareto classifications. Consequently the reader cannot inspect the stated success-only, utility, component-only, and efficiency comparisons there.

**Repair:** insert the existing objective heatmap and a compact table of true net benefit, component contrasts, weighted-utility contrast, and Pareto classification. Alternatively, explicitly point to the supplemental CSVs and remove the assertion that these results appear in the appendix. Update the generator as well so regeneration preserves the correction. No rerun is needed.

The code correctly uses different deployment regions, and the text correctly avoids declaring a method statistically wrong just because another method's objective fails. For example, the compliance-regression law has positive weighted-utility difference approximately .01620 while failing the compliance gate. Preserve this interpretation.

### 4. Distinguish an episode cap from exhaustion of the total study budget

**Priority:** medium; terminology/estimand repair.

**Status:** resolved in the latest `paper/main.tex:198–201`; the new prospective appendix separately accounts for the interrupted trajectory and unobserved planned records.

**Locations:** `paper/main.tex:197–206`; `experiments/prospective_protocol.md:15, 25`; `experiments/summarize_prospective_pilot.py:33–51, 67–79`; `results/prospective_final_cohort_summary.json`.

The general protocol says to count budget exhaustion as its defined outcome. The pilot correctly treats a completed run reaching its 40-step cap as a measured endpoint, but treats a monetary interruption or unstarted run as an unobserved outcome. These are different caps, and the distinction should be explicit so the pilot does not appear to violate the method's missing-outcome rule.

**Replacement:** “Prespecified per-episode limits define endpoint outcomes. Exhaustion of the study's monetary budget leaves unobserved endpoints, which remain in the planned-cohort bounds.”

The new pilot calculations are correct: 18/24 completed runs, 9/12 complete pairs, two successes per workflow, seven tied failures and two cost losses for verification. The observed sign sum is -2. Allowing each of three unknown planned pairs any score in [-1,1] gives [-5/12,1/12] = [-.417,.083]; the observed success-difference sum zero gives [-.25,.25]. These are deterministic fixed-cohort bounds, not confidence intervals, and the current postprocessor says so. The complete-pair -2/9 value should remain descriptive because completion is budget dependent. There is no workflow-superiority finding. One attempted-but-interrupted run and five unstarted runs should remain visible in the enrollment accounting.

### 5. Use the added DM comparison to calibrate the empirical claim, without overstating breadth

**Priority:** medium for presentation and contribution; mostly already handled by the new audit.

**Status:** the new DM main paragraph and appendix are integrated and correctly separate this reference study from the primary Monte Carlo study. One terminology refinement was sent to the lead agent: `paper/dm_appendix.tex:61` should call the formula-preserving shared-generator exercise an “isolated reproduction” or “exact rerun,” rather than an “independent reproduction.” Its independent constrained-optimization checks are a different verification layer from exact rerunning of extracted formulas.

**Locations:** `paper/results_main.tex:14–52`; `src/ternary_dm.py:1–14, 33–88`; `experiments/reproduce_dm_baseline.py:30–65, 95–166`; `evidence/dm_baseline.md`; `results/dm_baseline_results.csv`.

The isolated complete-data DM comparator is a worthwhile addition. It targets the same iid ternary streams and gate thresholds and preserves the same contemporaneous conjunction and looks. Its likelihood maximization and domination argument are appropriate to a fixed categorical law. The restriction to complete iid scores is essential: the DM statistic is not monotone in individual raw scores and cannot inherit the positive-factor partial-score plug-in argument.

In its separate reference study, guarded betting versus guarded DM deployed in 96.6% versus 60.1% of the efficiency streams and 93.75% versus 51.3% of the tie-heavy efficiency streams; DM used more capped pairs under this fixed prior. Those are appropriate reported comparisons. Do not replace the original 96.85% primary-study rate with 96.6% silently, because these are different Monte Carlo streams. The audit records this distinction correctly.

The unadjusted repeated-Wald comparison demonstrates a known peeking failure. The loose range-only CS and a fixed uniform-Dirichlet reference do not establish superiority to all well-tuned empirical-Bernstein, predictable-betting, or all-pairs sequential procedures. Existing disclaimers are adequate if no broad efficiency claim is introduced. An expanded competitive-method study is necessary only if the paper claims such superiority; it is not a prerequisite for stating the current protocol guarantees.

## Theory audit: conclusions to retain

- **Observation law:** the randomized AB/BA score identifies the symmetric cross-arrival target without requiring positional exchangeability. Independent exchangeable arrivals are an additional condition for the product-law interpretation. This distinction is correct, as is the fact that component differences simplify to average same-episode component effects.
- **Monitoring:** the normal-mixture bound covers the running average of conditional means, not the latest or future effect. The positive-bet process tests a per-step conditional null. The finite stake grid has the stated non-universal power limitation.
- **Conjunction:** level alpha per fixed stationary gate controls one deployment conjunction. It does not provide simultaneous component intervals or unrestricted control across candidates, versions, and selected hierarchies. The drifting alternative correctly uses joint coverage or a fixed violating criterion.
- **Partial outcomes:** simultaneous enclosures and a valid latent complete-score filtration suffice for pathwise confidence/threshold transfer despite informative reveals. Calendar-time martingale validity is not proved or needed for the stated threshold claim. The envelope's non-later decision property is relative to the same candidate prefixes, bets, and looks; the code uses that comparator. A latest-enrolled-prefix-only implementation would not share the dominance claim.
- **Repeated runs:** task-level aggregation avoids counting all within-task comparisons as independent. Removing shared-seed diagonals removes the explicitly modeled within-seed coupling contribution; it does not fix arbitrary shared cross-task seed or infrastructure effects. The historical text discloses that limitation.
- **Lower bounds and sensitivity:** the guardrail information bound and comparator-disagreement bound are valid standard specializations. Their presence improves completeness but should not be counted as separate major theoretical innovations.

I found no reason to demand a new calendar-time e-process proof, to split alpha mechanically across a stationary conjunction, or to label the historical preference reversals a calibration failure. Those would misread the current claims.

## Reproducibility and final release boundary

The project has unusually explicit result and source provenance for a rapidly developed manuscript. The preserved failed initial pilot, amended workflow protocol, full planned-cohort accounting, exact DM reference reproduction, and exclusion of unaudited general projection/width routines are strengths.

During review, the lead agent confirmed that the reproduction entrypoint was being updated to regenerate DM, ablation, and prospective summaries and to verify their final manifests. I therefore do not treat their earlier missing integration as an outstanding scientific finding. Before delivery, verify the final packaged copy, rather than relying on a development-tree pass: regenerate all manuscript inclusions, confirm the prospective bounds and every ablation count against the supplied CSV/JSON files, check that the corrected objective appendix survives regeneration, and ensure the package contains the inputs required by those commands. The quarantined `wincs.py` projection/width outputs must remain excluded from endorsed results. A reported exact reference comparison needs its reference preserved or an explicit explanation that the original contributed reference is a development-only record.

The full prospective aggregate can be recalculated from supplied outcome records, but hashed message content does not permit an independent behavioral or verifier-validity audit. That is an appropriate privacy/release boundary if stated. It does not support a claim that the real grader or interim certificates have been independently validated.

## Suggested positioning and decision

The strongest central claim is: “We give an explicit guarded protocol for prioritized agent evaluation, make its observation targets and inferential conditions transparent, and demonstrate that historical and synthetic composite preferences can disagree with protected component requirements.” The asynchronous construction is a useful specialization with a proven matched-comparator property, while its operational usefulness still needs trace evidence.

Consider making the historical retail/telecom reversals more prominent in the abstract and giving the known repeated-Wald pathology less emphasis. The current artifact has real agent-output evidence for the former; the latter is an expected consequence of established sequential-testing theory. A short protocol table or algorithm mapping each observation regime to its target, assumptions, and permitted decision would make the synthesis easier for an ICLR reader to use.

The concrete wording and reporting repairs above are now incorporated. Subject to final release checks, this can be a complete, candid submission for author consideration. My independent review still would not characterize it as a strong ICLR paper or imply likely acceptance. The residual issue is whether the integrated protocol and descriptive findings are sufficiently useful and original for that audience. It cannot be removed by stronger adjectives, additional familiar lemmas, or a nominally prospective pilot too small and incomplete to address the principal operational question.
