# Submission-package readiness tracker

Initialized September 18, 2026, after the author's request for hourly GitHub checks and percentage updates in the existing Codex task.

**Current verified readiness: 70/100 points (70%).** This is a checklist-based project measure, not an acceptance probability, percent of elapsed effort, or evidence that the paper has been submitted. The score reflects the Round 10 checkpoint: accepted PR 7/10 contributions are integrated, while PR 8 correction/final empirical disposition prevents closure of the remaining whole milestones.

## Fixed rubric

Each milestone is worth five points. Award a milestone only when its evidence and acceptance condition are recorded; no fractional credit for a claim comment or an active process. The denominator remains 100. Optional additional experiments do not enlarge it. Scores may decrease if verified defects reopen a completed milestone. A scope amendment must be explicit and scientifically justified, not made merely to raise the percentage.

| Area | Weight | Verified credit |
|---|---:|---:|
| Scientific validation | 30 | 25 |
| Empirical validation | 20 | 15 |
| Manuscript integration | 20 | 15 |
| Release verification | 20 | 15 |
| Author-only inputs | 10 | 0 |
| **Total** | **100** | **70** |

| ID | Five-point acceptance milestone | Status / current evidence |
|---|---|---|
| S1 | Online/offline estimands and observation designs distinguished | Complete in frozen `f806aba` methods and reviewed theory. |
| S2 | Core hierarchical comparison and fixed-sample derivations reviewed | Complete for the frozen release's explicitly stated scope. |
| S3 | Core sequential guarantees, assumptions and guardrails reviewed | Complete for the frozen core; contributed PR 8 inference is separately pending under S6. |
| S4 | Partial-outcome/asynchronous theory and limitations reviewed | Complete for the frozen release; no operational production-latency claim. |
| S5 | Closest-prior attribution and novelty boundaries reviewed | Complete through Round 7; acceptance/competitiveness is not certified. |
| S6 | Incoming inference corrections and all critical scientific comments closed for the final retained claims | PR 7/10 and the new fixed-stake proof passed. Pending PR 8 uncertainty/endpoint repairs and any retained airline analysis. |
| E1 | Core simulations and key stress/delay/grader results executed and checked | Complete in the frozen release and reproduction audits. |
| E2 | Historical trajectories and actual prefix comparisons independently checked | Complete: 3,936 trajectories; 10,008 comparisons and 195,171 prefixes. |
| E3 | New open-weight coding collection and raw aggregate integrity independently verified | Complete: Round 9 reconstructed 1,182 episodes, 591 tasks and all 295 monitor scores; this does not credit its pending inference repair. |
| E4 | Final retained empirical analyses/provenance reproduced; unresolved data and protocol deviations explicitly disposed | PR 7 diagnostic and full PR 10 study reproduced; PR 8 raw/aggregate provenance reproduced. Pending PR 8 corrected uncertainty and final airline delivery/disposition. Optional unfinished studies may be excluded explicitly; no mock results may be used. |
| M1 | Full methods-paper review draft with complete appendices exists | Complete in `f806aba`. |
| M2 | Venue-format structure, main-text length and required statement drafts checked | Complete for the 36-page Round 10 draft, main content through page 9. |
| M3 | Frozen claims, citations, tables and limitations reconciled with the evidence then included | Complete through Round 7; excludes unintegrated new contributions. |
| M4 | Accepted incoming results and review corrections integrated into the final paper and protocol ledger | PR 7/10 and scoped running-mean proof integrated; final retained PR 8 findings/disposition pending. |
| Q1 | Earlier frozen anonymous code/source package passes clean extraction and reproduction | Complete under the documented release/delta audits. |
| Q2 | Earlier frozen PDF inspected and anonymity/layout checked | Complete for `f806aba`; this is not final revised-PDF signoff. |
| Q3 | Frozen artifacts, hashes, source provenance and reproducibility instructions preserved | Complete; new release copies need their own checks under Q4. |
| Q4 | Final revised paper/code/source archives rebuilt, independently checked and visually inspected | Round 10 intermediate archives passed independent 188-payload/104-result checks, identical-text rebuilds and 36-page visual inspection. Final retained-result package remains pending PR 8 disposition. |
| A1 | Author actually verifies the final science and accurate AI-use disclosure | Pending actual human confirmation; never inferred from agent review. |
| A2 | Author confirms OpenReview/profile/eligibility and truthful originality/concurrent-submission declarations | Pending actual human inputs. The final package can be ready before upload; upload/acceptance remain separate statuses. |

## Observed, validated and integrated contributions

Latest GitHub check: September 19, 2026, approximately 03:00 UTC. Exact heads below are unchanged from the Round 10 audit; no new owner delivery or review response arrived. Completed execution issues 3 and 9 were closed after acceptance-scope reconciliation, without changing the score or scientific release. A new commit must be reviewed before inheriting these statuses.

| Contribution | Exact head | Verified disposition |
|---|---|---|
| PR 7 sequential-comparison subset | `ac17f5901bcf4efba6c71e970d3a4c1cf1ed06cb` | Round 9 corrections closed; rare-event diagnostic reproduced exactly; accepted subset integrated. This is not approval of every other file on the broad branch. |
| PR 10 drift/unequal-law panel | `ae3f0a5d4936855fc0b81f4a327254e932ea729b` | Full CPU study and independent target calculations passed; accepted results integrated. |
| PR 8 open-weight coding | `c89b525cd8e51564ca8c23399201d9cfdf0431a3` | Raw records, source provenance and version-2 aggregates reproduced. Shared orientation/pass dependence, endpoint arithmetic and claim/provenance wording need correction; excluded from current archives. |
| PR 8 airline | Same head | Design and mock artifacts only. Last owner report: 21:44 UTC, 27/196 saved under amended invocation 2; not a current process check or final result. |
| PR 5 generic projections | `b14e820f3009058473bddf9aba30eac1e855fd97` | Separately unapproved and excluded; no retained claim depends on them. |

See `reviews/round10_sequential_corrections_audit.md`, `reviews/round10_drift_panel_audit.md`, `reviews/round10_open_model_repair_audit.md` and the Round 10 release audit. Unchanged GitHub heads with pending findings remain work to track; do not silently skip them.

## Hourly reporting and continuation

The scheduled follow-up returns to the existing task. Every run reports the overall percentage and change, validated versus merely delivered updates, active/pending experiments with timestamped evidence, remaining blockers, and the next action. If nothing changed, report the same percentage and a short unchanged status. Commit/push meaningful research or tracker changes; do not create no-op hourly Git commits. Keep detailed polling timestamps and observed/validated head checkpoints in ignored `work/hourly_monitor_state.json` if useful.

Read [EXPERIMENT_POLICY.md](EXPERIMENT_POLICY.md) and ownership instructions before acting. No commercial/proprietary experimental calls, no duplicated owner jobs, no blind result integration, and no fabricated human declarations. Preserve immutable observations and distinguish synthetic, historical, prospective laboratory, replay and production evidence. At 100%, provide the exact verified final package and pause the recurring task; 100% does not mean submitted or accepted.
