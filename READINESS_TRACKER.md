# Bounded-v1 arXiv package readiness tracker

Current full-project review remains60% (change0); bounded v190%. See [September21 root disposition](reviews/v2_bindings_root_disposition_20260921_0343.md). New source/resource provenance is bounded-verified; successor experiments and release integration remain pending.

**For overall progress, report [FULL_PROJECT_PROGRESS.md](FULL_PROJECT_PROGRESS.md) first: 60% across the expanded project, including issues #11/#12 and their final integration. This file retains the separate existing-package score of 90%.**

**September 19, 2026: 90/100 verified checklist points (90%).** The author redirected the project to arXiv after the ICLR deadline. This score applies to the technically verified, scientifically bounded v1 preprint, not a future stronger experiment program. It is not an acceptance probability, human scientific signoff, submission confirmation or a measure of hours spent.

## Explicit target migration

The denominator and weights remain fixed: science 30, empirical evidence 20, manuscript 20, release 20, author inputs 10. Each milestone is five points. We replaced the obsolete ICLR format/eligibility conditions with arXiv format/metadata/license/account conditions, and independently rechecked the new technical artifacts before re-closing M2/Q4. No points were awarded merely because the venue changed. Original ICLR definitions and history are preserved in [the snapshot](submission/ICLR_READINESS_SNAPSHOT.md).

| Area | Weight | Verified credit |
|---|---:|---:|
| Scientific validation | 30 | 30 |
| Empirical validation | 20 | 20 |
| Manuscript integration | 20 | 20 |
| Release verification | 20 | 20 |
| Author-only inputs | 10 | 0 |
| **Total** | **100** | **90** |

| ID | Five-point acceptance milestone | Status / current evidence |
|---|---|---|
| S1 | Online/offline estimands and observation designs distinguished | Complete in frozen `f806aba` methods and reviewed theory. |
| S2 | Core hierarchical comparison and fixed-sample derivations reviewed | Complete for the explicitly stated scope. |
| S3 | Core sequential guarantees, assumptions and guardrails reviewed | Complete; incoming claims are separately disposed under S6. |
| S4 | Partial-outcome/asynchronous theory and limitations reviewed | Complete; no operational production-latency claim. |
| S5 | Closest-prior attribution and novelty boundaries reviewed | Complete through Round 7; competitiveness and acceptance remain uncertain. |
| S6 | Incoming inference corrections and all critical scientific comments closed for the final retained claims | Complete: PR 7/10 and fixed-stake proof passed; root coding running-mean analysis and descriptive airline/conditional observed-array replay passed. Unsupported contributed intervals and residual owner prose are explicitly excluded. See Round 12 integration and completion-scope reviews. |
| E1 | Core simulations and key stress/delay/grader results executed and checked | Complete in frozen results and reproduction audits. |
| E2 | Historical trajectories and actual archived trace prefixes independently checked | Complete: 3,936 trajectories; 10,008 comparisons and 195,171 prefixes. |
| E3 | New open-weight coding collection and raw aggregate integrity independently verified | Complete: 1,182 episodes, 591 tasks, all 295 monitor scores. |
| E4 | Final retained empirical analyses/provenance reproduced; unresolved data and protocol deviations explicitly disposed | Complete: PR 7 diagnostic, full PR 10 panel and coding subset reproduced; airline 196 canonical records, 194 saved trajectories, two placeholders, 206 attempts, amendment and incomplete-usage bounds independently reconciled. See Round 12 evidence/integrated reviews. |
| M1 | Full methods-paper review draft with complete appendices exists | Complete. |
| M2 | Target-format structure, metadata and statement drafts checked | Complete for named arXiv article: 45 pages, main/statements/references 13, supplementary appendices 32. Official arXiv requirements checked September 19. No conference page limit or anonymity rule is applied. |
| M3 | Frozen claims, citations, tables and limitations reconciled with the evidence then included | Complete; later integration covered under M4. |
| M4 | Accepted incoming results and review corrections integrated into the final paper and protocol ledger | Complete: accepted PR 7/10, scoped proof, coding and airline observations integrated. Scope/deviations/exclusions documented in the Round 12 integration ledger. |
| Q1 | Earlier frozen anonymous code/source package passes clean extraction and reproduction | Complete under earlier release/delta audits. |
| Q2 | Earlier frozen PDF inspected and anonymity/layout checked | Complete; final revised-PDF check covered under Q4. |
| Q3 | Frozen artifacts, hashes, source provenance and reproducibility instructions preserved | Complete, including Round 11 baseline `1001b23` and unchanged observations. |
| Q4 | Final revised paper/code/source archives rebuilt, independently checked and visually inspected | Complete for arXiv package: 35 source files, 246 code payloads, 127 result checks, clean 45-page text-identical build, exact 13+32 split, all-page visual survey and selected enlarged pages. See arXiv release/visual reports. Server preview remains a separate author submission step. |
| A1 | Author actually verifies the final science and accurate AI-use disclosure | Pending actual human confirmation; never inferred from agent review. |
| A2 | Author selects arXiv license/category and confirms account/endorsement, distribution rights and truthful submission agreements | License selected by author: arXiv perpetual, non-exclusive 1.0. Category, account/endorsement, rights and agreements remain pending; no partial milestone credit. Upload, server preview and announcement are separate states. |

## Current artifacts and evidence

Start with [the arXiv handoff](arxiv/READ_ME.md). The canonical `arxiv/paper.pdf` is 45 pages; convenience reading copies are 13 pages plus 32 supplementary pages. Independent extraction/reproduction and root visual checks are in [release audit](reviews/arxiv_release_audit.md) and [visual QA](reviews/arxiv_visual_qa.md). All 47 packaged scientific CSVs and historical ICLR source/artifacts are unchanged. Three excluded derived CSVs in the broader main tree changed during the direct merges, as recorded in the dependency/merge audit. The artifact hashes, source transformations and explicit dependency-only code repair are in `arxiv/package_manifest.json`.

The scientific baseline remains `45e8ee2`. Accepted PR 7/10 subsets and PR 8 coding/airline observations retain their documented assumptions and exclusions. PR 8 remains at reviewed `ce8b506`; index/report repairs are closed. Generic projection/width methods and the excluded contributor intervals remain outside the paper. All original collections and issue #1/#2 narrowed closures are preserved; this target change does not approve an entire contributor branch.

The optional-extension import defect found after the direct merges was repaired in the current arXiv code archive and independently checked; see [dependency audit](reviews/arxiv_extension_dependency_audit.md). The historical ICLR ZIP remains preserved. This repair retains the existing release credit and introduces no new outcome or readiness points.

## New experiment program, reported separately

[Issue 11](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11) is claimed by session60 for a new prospective randomized open-weight study. Design/adapter review and the protocol freeze precede trial execution. Root posted pairing, partial-information and stopping guidance. [Issue 12](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/12) requests independent CPU validation/calibration of that adapter. It is claimed by the same external session, with procedural independence disclosed. The latest repair head is `d8b2a4d` on the validation branch; the original live branch remains `5776877`. The v1 CPU grid is delivered and partly reconciled, but actual-live/all-look validation remains unaccepted. The primary scheduler repair passes bounded deterministic checks; the optional finest sensitivity is deferred. See [the current disposition](reviews/v2_batched_schedule_root_disposition_20260921_0226.md) and [design addendum](evidence/literature_design_audit_20260921.md). No new freeze, outcome integration or readiness milestone is certified. See [the scoped plan](evidence/arxiv_experiment_plan.md).

These are authorized successor studies, not missing evidence for a claim made by the bounded v1. Their delivered/validated/integrated states will be tracked separately. New strong claims require their own acceptance conditions. Favorable results are never a completion criterion; a verified defect can reopen a current milestone and lower the score. No new scientific result is included merely because an issue is claimed or a process is running.

## Every-30-minute continuation

The existing task checks arXiv package progress and GitHub updates every 30 minutes, following the author's September21 instruction to align with the experiment worker's more frequent reports. This replaces the90-minute schedule, not adds another monitor. Per the author's standing reporting request, every run posts a timestamped GitHub coordination comment with theory findings, received versus validated/integrated experiments, the full-project percentage/change and remaining work first, the separate bounded-v1 percentage, owner status, blockers and concrete next requests; it also reports progress in the existing Codex task. Read both issue11 and issue12 before choosing defaults; acknowledge exact feedback IDs and review only newly delivered changes. Follow the half-hour exchange in [COORDINATION.md](COORDINATION.md). Use issue11 as the current coordination thread, with detailed requests on the relevant issue and exact commit links; no new PRs. Even an unchanged cycle gets a brief GitHub comment; do not invent findings or repeat requests merely to fill the report. It must retain ownership, no-commercial-model/no-paid-compute restrictions and original data. Do not rerun unchanged baselines or make no-op commits. Continue meaningful authorized successor coordination even if the v1 author-input score reaches100; do not stop just because one package is ready. Submission and announcement require separate actual evidence.
