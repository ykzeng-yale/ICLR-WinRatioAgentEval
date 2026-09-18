# Submission-package readiness tracker

Initialized September 18, 2026, after the author's request for hourly GitHub checks and percentage updates in the existing Codex task.

**Current verified readiness: 70/100 points (70%).** This is a checklist-based project measure, not an acceptance probability, percent of elapsed effort, or evidence that the paper has been submitted. The score reflects the Round 9 validated checkpoint; newly delivered fixes receive no extra credit until checked.

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
| S6 | Incoming inference corrections and all critical scientific comments closed for the final retained claims | Pending independent review of PR 7/8 corrections, PR 10 and any retained airline analysis. |
| E1 | Core simulations and key stress/delay/grader results executed and checked | Complete in the frozen release and reproduction audits. |
| E2 | Historical trajectories and actual prefix comparisons independently checked | Complete: 3,936 trajectories; 10,008 comparisons and 195,171 prefixes. |
| E3 | New open-weight coding collection and raw aggregate integrity independently verified | Complete: Round 9 reconstructed 1,182 episodes, 591 tasks and all 295 monitor scores; this does not credit its pending inference repair. |
| E4 | Final retained empirical analyses/provenance reproduced; unresolved data and protocol deviations explicitly disposed | Pending PR 7/8/10 validation and final airline delivery/disposition. Optional unfinished studies may be excluded explicitly; no mock results may be used. |
| M1 | Full methods-paper review draft with complete appendices exists | Complete in `f806aba`. |
| M2 | Venue-format structure, main-text length and required statement drafts checked | Complete for the 33-page frozen release, main content through page 9. |
| M3 | Frozen claims, citations, tables and limitations reconciled with the evidence then included | Complete through Round 7; excludes unintegrated new contributions. |
| M4 | Accepted incoming results and review corrections integrated into the final paper and protocol ledger | Pending. |
| Q1 | Earlier frozen anonymous code/source package passes clean extraction and reproduction | Complete under the documented release/delta audits. |
| Q2 | Earlier frozen PDF inspected and anonymity/layout checked | Complete for `f806aba`; this is not final revised-PDF signoff. |
| Q3 | Frozen artifacts, hashes, source provenance and reproducibility instructions preserved | Complete; new release copies need their own checks under Q4. |
| Q4 | Final revised paper/code/source archives rebuilt, independently checked and visually inspected | Pending after accepted-result integration. |
| A1 | Author actually verifies the final science and accurate AI-use disclosure | Pending actual human confirmation; never inferred from agent review. |
| A2 | Author confirms OpenReview/profile/eligibility and truthful originality/concurrent-submission declarations | Pending actual human inputs. The final package can be ready before upload; upload/acceptance remain separate statuses. |

## Received updates awaiting validation

GitHub checked at approximately September 18, 2026, 21:46 UTC:

- PR 7 head `ac17f5901bcf4efba6c71e970d3a4c1cf1ed06cb`: owner reports all Round 9 wording corrections and the missing rare-event diagnostic. Prior audited head: `cfc1850ce9cb0e4ec3e83e4b75836e284f421217`. New head remains pending root validation.
- PR 8 head `e0610088bd7772916d25c84b94eeef40ca2fc0a9`: owner reports corrected two-sided capital, post hoc design-based/conditional-target distinctions, preserved old results, pinned data provenance and anonymous copies. Prior audited head: `ab24f1bc2d787241b7493cf2c9f2b406908a5a74`. New formulas and assumptions must be independently checked, not accepted from the comment alone.
- Airline status reported by its owner at 21:44 UTC: invocation 2 with amended settings; arm A 27/98 units saved, arm B 0/98; total planned 196. The owner reports a live runner and approximately five hours remaining. This is a timestamped owner report, not a root-inspected process or a final result. Audit the amendment and retain every invocation/failure when artifacts arrive.
- PR 10 head `ae3f0a5d4936855fc0b81f4a327254e932ea729b`: new CPU drift/unequal-law panel delivered. The reported findings and independent-worker audit await root review.
- PR 5 head `b14e820f3009058473bddf9aba30eac1e855fd97`: generic projection fixes remain separately unapproved/excluded unless validated for a retained use.

These deliveries are work pending validation even after their hashes have been recorded as seen. Do not skip them on a later hourly run merely because their heads did not change.

## Hourly reporting and continuation

The scheduled follow-up returns to the existing task. Every run reports the overall percentage and change, validated versus merely delivered updates, active/pending experiments with timestamped evidence, remaining blockers, and the next action. If nothing changed, report the same percentage and a short unchanged status. Commit/push meaningful research or tracker changes; do not create no-op hourly Git commits. Keep detailed polling timestamps and observed/validated head checkpoints in ignored `work/hourly_monitor_state.json` if useful.

Read [EXPERIMENT_POLICY.md](EXPERIMENT_POLICY.md) and ownership instructions before acting. No commercial/proprietary experimental calls, no duplicated owner jobs, no blind result integration, and no fabricated human declarations. Preserve immutable observations and distinguish synthetic, historical, prospective laboratory, replay and production evidence. At 100%, provide the exact verified final package and pause the recurring task; 100% does not mean submitted or accepted.
