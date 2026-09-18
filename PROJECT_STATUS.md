# Research status

Active objective: a complete, reproducible ICLR submission package for hierarchical win statistics in agent evaluation, with online continuously monitored randomized comparisons as the main setting.

This directory is a development package, not a certified submission-ready paper. Goal completion remains unproven until the scientific and submission checks below are satisfied. No paper has been submitted. The user has specified a single author; private submission metadata records the supplied details, while review materials remain anonymous.

## Completion criteria

1. Current ICLR rules and closest methodological/agent-evaluation literature verified against primary sources; scope and novelty claims reconciled.
2. Online and offline estimands separated; every theorem has stated assumptions and a complete proof; independent reviews resolved or openly retained as limitations.
3. Reproducible simulations executed with uncertainty, honest baselines, stress tests, and provenance; simulated streams never labeled live experiments.
4. Real-agent empirical evidence analyzed with task-level dependence, metric provenance, sensitivity analyses, and appropriate limits on generalization.
5. Anonymous main paper within the official nine-page limit, full appendix, verified references, reproducibility/ethics/AI-use statements, code and results archive.
6. Multiple independent critical review rounds, a concern-by-concern response ledger, a clean rebuild, and visual inspection of the exact output PDF.
7. Final human authorship, disclosure, originality, profile, and submission-form inputs supplied by the actual authors; no unverified human signoff represented as completed.

## Working research contract

- Online target: cross-arrival prioritized preference under a prespecified block-randomized comparison, subject to separate population compliance and success constraints.
- Offline target: equal-task average preference over repeated runs on a common resettable task. Same-task pairing is not silently transported to single-exposure online A/B tests.
- Statistical contribution must be distinguished from established win statistics, e-processes, and gated deployment. Standard probability inequalities are credited as such.
- Primary simulation scenario definitions and the primary public-data hierarchy are fixed before inspection of their numerical results. This is a dated internal analysis plan, not a public preregistration.
- New empirical resources default to public data and local compute. The capped Haiku pilot completed 18 trajectories across 9 task pairs, with 3 planned task pairs unobserved; no production users were involved. All paid calls have stopped.

## ICLR 2027 time constraint

Official author guidelines verified 2026-09-17: abstract deadline September 18, 2026 23:59 AoE; full paper September 25, 2026 23:59 AoE. New York conversions: September 19 and September 26 at 07:59 EDT. Author additions and removals are forbidden after the abstract deadline. An informative genuine abstract is required. See submission/requirements.md for the source-led checklist.

## Scientific readiness blockers under investigation

- The narrow protocol has rigorous derivations, but incremental combination of established methods may not meet the desired contribution standard. Independent novelty review remains consequential.
- Existing runs support retrospective benchmark analysis. A prospectively specified laboratory pilot is complete and supports feasibility only; production-online performance is not established.
- Empirical tolerances/noninferiority margins are illustrative engineering choices and require application-owner justification for an actual deployment.
- The author list is supplied. OpenReview profile status, reciprocal-review eligibility, and human verification remain unverified.

## Current verified checkpoint

The integrated PDF has 33 pages, with main content ending on page 9 and designated statements, references, full proofs and experiment details following. Multiple independent model-assisted reviews found and corrected implementation, assumption, interpretation and packaging defects. The complete-data DM reference is isolated from defective externally contributed projection/width routines. After independently reconstructing the real trace-prefix audit, the fresh reviewer updated the assessment to a credible focused methodology submission with borderline ICLR strength; no acceptance likelihood is promised.

A clean unpacked reproduction matched 16 regenerated numerical CSVs and 3 retained prospective observation CSVs byte-for-byte, reproduced prospective aggregate JSON exactly, and rebuilt the pre-trace 29-page PDF with identical extracted text. Initial standalone entrypoint defects (missing 3 generated prospective text files and mandatory Git metadata) were corrected and the repaired archive passed fresh retesting. The final trace-extended package also passed: exact full reproduction matched all 23 CSVs (20 regenerated and 3 retained observations), the prospective aggregate JSON, all generated TeX and all extracted PDF text. Its default check verified 73 output hashes, both trace implementations agreed, and all 43 LaTeX-source archive files matched. The Round 5 31-page PDF was visually inspected with no overfull boxes or undefined references. Manuscript formatting and factual package readiness are separate from the still uncertain ICLR competitiveness and required author attestations.

The trace extension independently reproduced 3,426 early certificates among 10,008 comparisons and all 195,171 prefixes from nine hashed archives. Of all comparisons, 2,595 resolve while actual assistant messages remain unseen. The main and appendix report all contrasts, the terminal-marker sensitivity, and the artificial ordinal schedule. No production latency, deployment saving, or independent-pair inference is asserted.

The author handoff is submission/READ_ME_FOR_AUTHOR.md. Paid calls are halted at USD3.9476608 accounted project cost. The GitHub queue specifies unexecuted larger/local/comparator studies with separate branches and zero additional paid allocation. Goal completion awaits actual author scientific verification, profile/reciprocal-review checks and submission attestations; no agent claims those steps are done.

## Round 6 close-prior and normalization audit

Two verified close preprints are now explicitly cited for hierarchy-family intersection–union inference and stage-standardized net benefit; Mao2018 is cited for the marginal potential-outcome contrast framework. The new appendix gives a standard exact variance identity under independent arm records at the same 2N execution budget and an illustrative PSNB/component-guardrail distinction. Separate source and theory reviewers found no correction needed. A factor-of-two budget-convention error in the development literature ledger was corrected; no numerical result used that expression. The previous 31-page release and its full reproduction are preserved at commit `6267012`. The updated 33-page paper keeps the 9-page main limit. See submission/COMPLETION_AUDIT.md for requirement-level evidence and outstanding author-only inputs.

The Round 6 archive delta audit passed with 142 payload files and 44 LaTeX-source members. Only main text, references, the new pairing appendix and the paper PDF differ from the previous numerical release. All 23 CSVs are byte-identical; 73 archived hashes and the rebuilt 33-page PDF text match. The updated PDF has been visually checked on every page.

## Round 7 external-review integration

The external positioning critiques at `8c95ead` were read against current main, without checking out or editing their branch. Most fatal points concerned an obsolete memo; the surviving citation gaps were independently verified and corrected. Current related work cites Huang's estimand-aware agent comparisons, Manole–Ramdas's finite-sample symmetric U-statistic route, and Schultzberg et al.'s superiority/guardrail decision logic. The existing ablation now explicitly reports that guarded bounded-efficiency and guarded win have equal deployment rates and mean capped sample use in two improvement scenarios; the result builder checks that equality against the archived CSV. No simulated output, raw observation, or scientific engine changed. The PDF remains 33 pages, main content through page 9. Issue 3 retains its external owner; its proposed unexecuted comparisons were not adopted into the released abstract.

The final Round 7 archive delta audit passed against committed `6dfc095`: exactly five expected payload changes, all 73 result files and 23 CSVs byte-identical, modified text builder output identical, 73 integrity hashes matched, and rebuilt PDF text identical. All 44 LaTeX-source members resolve. The current 33-page PDF was visually inspected, with main content ending on page 9 and statements continuing onto page 10; no overfull text, undefined citations or detected identifier/credential leaks were found.

## Round 8 incoming-code audit and completion boundary

New external commit `e1ea314` supplies the claimed all-pairs comparator implementation and additional replay results. These were reviewed read-only before integration. The replay audit found a reproducibility defect in process-dependent hash seeding and a stratified sampler that can index one task using another task's replicate count; a toy example fails, although the balanced current tau2 pool is not shown wrong by that example. The bidirectional launch-rule label also needs explicit handling when both orientations qualify. The separate U-statistic audit addresses inferential assumptions and same-look versus retained-crossing semantics. These external artifacts are excluded from the frozen paper/supplement at `f806aba`; current scientific outputs are unchanged. The existing issue owner receives the reports and retains implementation ownership.

The current requirement audit still lacks author scientific verification, a verified OpenReview profile, reciprocal-review qualification, and truthful originality/concurrent-submission declarations. These same author-only conditions were recorded at the earlier 31-page release, at the Round 6/7 release, and again now. No qualifying live local experiment process was found; a claim comment and committed code do not establish active execution. Further integration awaits a corrected, executed external handoff. The paper is prepared for author review, not declared ready for submission.
