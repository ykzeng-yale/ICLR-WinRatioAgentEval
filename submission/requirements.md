# ICLR 2027 submission requirements and release gates

Verified 2026-09-17 (America/New_York). This is a preparation checklist, not a record of submission or acceptance. Recheck the live submission form before uploading.

## Dates that govern this project

| Event | Official date | New York conversion |
|---|---|---|
| Genuine abstract; complete author set | September 18, 2026, 23:59 AoE | September 19, 2026, 07:59 EDT |
| Full paper and supplementary material | September 25, 2026, 23:59 AoE | September 26, 2026, 07:59 EDT |
| Reviews released | November 5, 2026 | — |
| Author–reviewer discussion | November 5–18, 2026 | — |
| Decisions | December 16, 2026 | — |

Dates are supported by the [2027 call for papers](https://www.iclr.cc/Conferences/2027/CallForPapers); supplementary timing is also explicit in the author FAQ. AoE is UTC−12; the local conversions above are calculated, not quoted. The deadline is imminent relative to the idea-stage starting point. A placeholder abstract is not an acceptable way to reserve a place.

## Format and administrative checklist

The following summarizes the [2027 author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines):

- [ ] At submission: maximum **9 main-text pages**; references and appendices excluded. Rebuttal/camera-ready: 10 pages.
- [ ] Use the [official 2027 LaTeX template](https://media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip).
- [ ] Anonymous manuscript, appendix, code, metadata and demonstration links; cite own related work in third person.
- [ ] Final author set by abstract deadline: no subsequent additions or removals. Verify OpenReview profiles.
- [ ] Genuine abstract; full-paper revisions remain consistent with it.
- [ ] Anonymous code supplement encouraged; appendices may follow references. Reviewers need not read supplementary material.
- [ ] Required AI-use section; ethics and reproducibility statements recommended and excluded from page limit. Ethics statement: at most one page.
- [ ] Check reciprocal-reviewer eligibility and registration; exemptions apply when no author qualifies. At most 20 submissions per author; at most one submission with no eligible reciprocal reviewer.
- [ ] Check dual-submission rules; arXiv is allowed.
- [ ] Understand public retention/de-anonymization of submissions, including rejection or post-deadline withdrawal.
- [ ] Submit through [ICLR 2027 OpenReview](https://openreview.net/group?id=ICLR.cc/2027/Conference).

**Source inconsistency:** The reviewer FAQ retains an older September 16 deadline, and some FAQ page-limit wording is inconsistent. The updated CFP and author submission instructions agree on September 25 and 9 initial pages. Those explicit submission instructions govern this checklist; confirm against the live form before submission.

## AI disclosure specific to this project

The [2027 author AI policy](https://iclr.cc/Conferences/2027/AIPolicyForAuthors) requires disclosure both in the paper and submission form. Required categories include synthetic data generation, conceptual or theoretical development, mathematical claims/proofs, hypotheses, methodology/experiment design, methods implementation, data preparation, and interpretation. It recommends disclosing writing, literature work, figures and other code assistance. Authors retain responsibility for correctness and attribution.

Our eventual statement must describe what actually happened: AI-supported literature research, theorem development, proof review, simulation and software creation, manuscript drafting, and simulated reviewer critiques. It must distinguish AI checking from author checking. Do not state that human authors verified everything until they have done so. Preserve a dated AI-assistance log as the project proceeds.

## Scientific release gates proposed for this paper

These are project-specific quality criteria, not extra formal ICLR rules:

1. **Contribution:** Every claimed advance has a closest-prior-work comparison, especially sequential win-statistics and off-policy confidence sequences. Generic concentration corollaries are labeled as such.
2. **Estimand:** The paper distinguishes offline paired runs, online shadow pairs, and one-arm-per-request randomized A/B data. Any transport or identifiability assumption is explicit.
3. **Theory:** Full proofs, assumptions, edge cases and implementation correspondence are independently audited; no unresolved major proof defects remain.
4. **Simulation:** Reproducible executed runs report Monte Carlo uncertainty; include null, near-null, heterogeneous tasks, repeated runs, informative completion, adaptive allocation and guardrail-failure scenarios. Label synthetic results clearly.
5. **Agent evidence:** At least two meaningfully different workflow families, prespecified outcomes and priorities, real model executions or fully documented public traces, and an online experiment or accurately labeled stream replay. Trace replay is not production deployment evidence.
6. **Comparisons:** Include valid existing sequential methods, success-only/componentwise testing, weighted-score and Pareto analyses. Match estimands where possible and explain otherwise.
7. **Robustness:** Evaluate hierarchy/tolerance sensitivity, judge measurement error, task clustering, benchmark composition, and cost/latency measurement.
8. **Reproducibility:** One-command clean reproduction, locked dependencies, immutable raw outputs, seeds, configurations, licenses and generated tables linked to logs.
9. **Review:** Independent AI reviewer rounds address substantive novelty, theory, empirical and reproducibility objections; human scientific approval remains outstanding until performed.
10. **Final artifact:** Render the exact anonymous PDF, inspect every page, audit references and supplement, and assemble the upload archive. No result placeholder or unexecuted experiment is presented as evidence.

The [reviewer guidelines](https://iclr.cc/Conferences/2027/ReviewerGuidelines) assess clarity, correctness, experimental rigor, reproducibility, motivation, novelty and community value. State-of-the-art leaderboard performance is not necessary. Our gate should therefore be a convincing new scientific result with appropriate evidence, rather than an arbitrary number of theorems or models.

## Inputs only authors can supply

- Final authors/order, affiliation information and reciprocal-reviewer qualification.
- The intended deployment workload and scientifically defensible hierarchy/noninferiority margins.
- Authorized model/API access and an experiment spending ceiling if paid runs become necessary.
- Permission to use any private production data; applicable human-subject review if human evaluators are recruited.
- Human validation and submission-form attestations.

These inputs need not halt independent theory, public-data work or simulation. They do prevent honestly calling the entire package ready to upload if still unresolved.
