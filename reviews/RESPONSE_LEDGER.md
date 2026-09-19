# Scientific review and revision ledger

These are model-assisted project reviews, not external human peer review. Scope and any reviewer/developer overlap are disclosed in each report.

**Current technical disposition (Round 12 release, reaffirmed in Round 13):** the retained technical package has passed scoped scientific/integration/release checks (90% fixed-rubric readiness). Actual author verification and declarations remain pending. Earlier table states and narratives below are historical; current concern-by-concern resolutions and explicit exclusions are in `round12_integration_ledger.md`. Scientific competitiveness remains a judgment, not a passed test.

| Concern | Response and evidence | Status |
|---|---|---|
| Generic GPC plus sequential inference may be incremental | Broad first-use claims removed. Closest sequential, deployment, and delayed-outcome methods explicitly compared. Partial-evidence protocol now proved, implemented and independently reproduced; closest worst-case completion/lifting precedents credited. | Scientific contribution remains open |
| Invalid tolerance silently changes comparator | Finite nonnegative tolerances and nonempty valid inputs now enforced; tests pass. | Corrected |
| Manual simulator differs from library | Independent reviewer compared 300,000 fresh pairs and found exact agreement. Analytic targets separately checked. | Verified within stated scope |
| Boundary guardrail nulls absent | Reproducible post-review stress suite adds both boundaries; all 17 stress rows independently replayed. | Corrected |
| No adaptive or dependence examples | Added adaptive-order inverse weighting and shared-task/reused-run experiments, with the exact target and failure mechanism labeled. | Addressed for those models |
| No informative-delay experiment | Two frozen scenarios, 1,000 repetitions each, executed and independently reproduced exactly. Enclosure and prefix-dominance invariants verified. | Addressed for the stated telemetry model |
| Conservative normal-mixture baseline | Main text explicitly reports radius 0.033 versus margin 0.01. No state-of-the-art efficiency claim; stronger U-statistic comparator queued. | Claim restricted; comparison open |
| Win-only detection mislabeled Type I error | Harmful deployment distinguished from a correct test of positive composite preference. | Corrected |
| Sample use confused with dollar cost | Capped mean pair count, two executions per pair, and conditional stopping times distinguished. Commercial spend tracked separately. | Corrected |
| Retained versus current crossing mismatch | Reported same-look rule and optional retained rule separated in appendix. Independent focused recheck passed. | Corrected and rechecked |
| Missing complete-record independence | Independence of complete task/replication records explicit; studentized CLT assumes iid complete records. Independent recheck passed. | Corrected and rechecked |
| Same-seed diagonal changes estimand | Twelve off-diagonal pairs primary; U/V decomposition proved; diagonal and all-pairs sensitivities retained. Pre-results amendment recorded. | Corrected |
| Shared four-seed suite limits inference | Historical-seed conditional task-resampling interpretation added. No coverage over new seeds claimed. | Limitation retained |
| SWE repository dependence | Deletion is a stability diagnostic, not a corrected cluster CI. Inference restricted. | Limitation retained |
| Tier win/loss outputs absent | Added tier wins, losses and signed contributions; all configuration sums reconcile. | Corrected |
| Protocol suggestions exceed executed analyses | Executed configurations enumerated; unexecuted exploratory alternatives identified. | Reporting corrected |
| Multiplicity and sensitivity selection | All configurations retained; intervals called pointwise; no simultaneous leaderboard or production claim. | Claim restricted |
| Code hashes changed after input validation | Original commit preserves initial run; reviewer replayed all 36 initial and 17 stress rows exactly. Current scripts rerun and manifests refreshed. | Verified |
| Prospective API unavailable | Initial exhausted-quota attempt is preserved. Frozen Haiku standard/verification amendment completed 18 trajectories/9 pairs with full monetary accounting and explicit capped-task failures. Full 12-task missing-outcome bounds retained. | Completed feasibility pilot; limitation retained |

Outstanding limitations are not closed merely because a PDF compiles. Human verification, a credible contribution, and final submission declarations remain required before the active goal can be marked complete.

## Round 3: asynchronous methods

The theory reviewer checked full proofs against the actual latent filtration and close published precedents. All fixed-range enclosures now explicitly remain inside the known score range; ongoing-enrollment consistency states n tends to infinity. Choe–Ramdas lifting and Henzi–Ziegel pending-outcome stopping/correction are credited as direct structural precedents. Threshold-crossing error control is distinguished from calendar-time e-process validity.

The empirical reviewer independently reproduced every aggregate result and calendar curve over 2,000 repetitions, checked 1,614 feasible-completion cases, and compared histogram wealth to direct products. The simulation has one telemetry mechanism and two outcome scenarios. Its final decision equality is a construction property, not universal power. Both reviews disclose developer/reviewer role overlap.

## External contribution audit

A separately contributed multinomial projection module was preserved during repository synchronization. Independent checks found a deterministic-boundary numerical defect; GitHub issue4 records the reproducer. It is not used in reported main-paper results. The separately audited complete-data ternary likelihood-ratio reference was subsequently integrated and reproduced; see the Round 4 and Round 5 entries below. No partial-score plug-in is authorized for that reference because it lacks the positive-betting monotonicity used by our asynchronous proof.

## Round 4: fresh integrated review and standalone reproduction

A reviewer uninvolved in development found no fatal error in the inspected probability arguments or grader-error proof, but judged ICLR competitiveness borderline to weak reject. The incremental nature of the contribution remains a disclosed scientific concern. The specific empirical gap around actual trace-derived certificates is receiving a separate frozen public-trace audit.

Resolved: distinguishes per-episode caps from study-level missing outcomes; states every bound-aware grader case is a null case and no corrective power was demonstrated; directs Pareto/objective details to actual supplied tables; describes the shared-formula DM exercise as isolated reproduction. The appendix includes the full pilot cohort and explicit lack of a superiority claim.

The archive reviewer independently matched all principal numeric outputs and the rebuilt PDF text. Two standalone defects were found: three generated prospective text files referenced by the QA manifest were missing, and DM provenance incorrectly required a Git checkout. The builder now includes those files and Git metadata is optional; source hashes remain available. The corrected archive passed a fresh extraction, exact default verification, complete numerical reproduction, and PDF rebuild with identical extracted text. No scientific result was altered to repair those packaging problems. See round4_release_reproduction.md.

## Round 5: actual archived trace certificates

The frozen ordinal replay passed an independent reconstruction from all nine hashed raw archives using a separate closed-form completion rule. All 10,008 pair results, 3,426 earliest certificate times, and 195,171 prefix-containment/nesting checks agreed. The audit reconciled 3,336 episodes and 51,247 actual assistant messages. Root added all nine contrast/domain rows and the reviewer-requested split: 2,595 comparisons resolve while actual messages remain unseen, while 831 lead only the artificial terminal marker. Every early certificate establishes the sign while leaving its eventual deciding tier ambiguous.

The empirical feasibility gap from Round 4 is addressed for this fixed archive. The updated independent assessment is a credible focused methodology submission with borderline ICLR strength. This does not establish concurrent timing, grader validity, prospective deployment gains, or methodological novelty beyond the explicitly credited synthesis. The main text and appendix retain these limits. See round5_trace_certificates_independent.md.

The final extended archive passed a fresh extraction and the exact full reproduction entrypoint, including the trace engine and independent verifier. All 23 CSVs, prospective aggregate JSON, generated TeX and rebuilt PDF text match the delivered baseline. All 141 payload files are present with verified hashes; all 43 LaTeX-source archive files match. The final PDF has 31 pages, main content ending on page 9, no overfull boxes or undefined references, and all pages were visually inspected. See round5_final_release_reproduction.md and final_visual_and_archive_qa.json.

## Separate contributed-code PR 5

An independent review of head 30fda600 found that the attempted boundary fix still underestimates an upper bound by 0.24365234375 for an explicitly feasible probability vector with a common coefficient offset. The exact reproducer and remedy were posted to PR 5. The patch is not merged, and the generic projection/width modules remain outside the submission archive and reported scientific results. This defect does not affect the isolated complete-data ternary DM reference. See pr5_projection_fix_review.md.


## Round 6: close prior work and equal-budget comparison

An independent source audit verified the original metadata and full HTML for Li, Fan and Yang (2026) and McCoy et al. (2026). Both are now explicitly cited: the former for fixed-sample asymptotic intersection–union inference over allowed comparison rules, the latter for replacing reach weights with a charter on stage-conditional effects. Mao (2018) is directly cited for marginal potential-outcome contrasts and IPW/doubly robust estimation. The manuscript no longer leaves these close connections implicit. The PSNB example establishes a difference in population requirements, not an invalid competing test or a comparative-power result.

A separate theory review found a factor-of-two budget convention error in the development literature note, which began with N records per arm but assigned only N/2 disjoint pairs. The corrected comparison has N pairs for 2N executions. New Appendix J gives the complete standard projection proof and shows that raw component-difference point estimators are exactly equal on the same arm records, while the hierarchical score can benefit from all-pairs reuse. The report verifies the proof, degenerate cases and PSNB algebra. No simulation result used the erroneous literature-note expression. No new generic-method novelty or sequential stopping advantage is inferred from this identity.

The Round 6 archive audit compared against the preserved Round 5 baseline: only main text, bibliography, the new appendix and manuscript PDF changed. All 23 numerical CSVs and other scientific payloads are unchanged. Default integrity verification plus PDF rebuild passed; all 44 LaTeX-source members match, the rebuilt 33-page PDF text matches, and all pages were visually checked with no overfull boxes or undefined references. The main text still ends on page 9. See round6_close_prior_source_audit.md, round6_pairing_efficiency_identity.md, round6_release_delta_audit.md and round6_visual_and_archive_qa.json.

## Round 7: incoming external positioning critiques

The new branch critiques were compared with the current paper rather than treated as instructions to revive an obsolete memo. Two material omissions survived: Huang's estimand-aware, utility-sensitive agent comparisons and Manole–Ramdas's finite-sample U-statistic route. Root verified the original metadata and full HTML, cited both with bounded claims, and directly credited the product-guardrail precedent of Schultzberg et al. The separate theory source check distinguishes the symmetric one-sample U-statistic statement from the current two-arm kernel; no generic sequential novelty is claimed. The development sequential-literature ledger's claim of no finite-sample net-benefit CS was corrected.

The practitioner comparator concern also prompted an explicit disclosure from existing results: guarded bounded-efficiency matches guarded win's decision rate and mean capped pairs in the efficiency-gain and joint-gain ablations. Their objectives remain different, and no decision-speed advantage is claimed from those scenarios. The result builder now verifies these equalities. This is a reporting change, not a new experiment. The external alternative abstract's proposed all-pairs comparisons remain unexecuted and were not integrated. Its ownership is preserved in issue 3.

The final Round 7 archive delta audit passed against committed `6dfc095`: exactly five expected payload changes, all 73 result files and 23 CSVs byte-identical, modified text builder output identical, 73 integrity hashes matched, and rebuilt PDF text identical. All 44 LaTeX-source members resolve. The current 33-page PDF was visually inspected, with main content ending on page 9 and statements continuing onto page 10; no overfull text, undefined citations or detected identifier/credential leaks were found.

## Round 8: pre-integration review of new external code

Two reviewers inspected external commit `e1ea314` without editing its owned files or running the claimed full experiment. The all-pairs estimator/projection and small Gaussian-boundary checks passed, with requested clarification of the AsympCS reduction, retained-crossing versus same-look comparisons, and missing guardrail-boundary calibration. A supported symmetric-vector reduction is documented for the owner. The replay reviewer supplied tiny counterexamples for process-dependent seed construction and mismatched task/replicate indexing, while carefully distinguishing those general defects from unproved bias of balanced-pool output. A bidirectional launch-label conflict is possible but absent in the 25 committed rows. These findings must be resolved or scoped before importing the external results. The anonymous package at `f806aba` does not depend on this code and remains unchanged.

## Round 9–10: completed external studies, scoped corrections and revised release

Round 9 reviewed the newly completed all-pairs comparison and 1,182 open-weight coding episodes without overwriting contributor branches. Round 10 closed the comparator's four interpretation/provenance findings at `ac17f590`, independently reproduced its rare-event diagnostic, and integrated only its accepted experiment/result subset. It also independently reran all 96,000 sequential and 14,000 permutation repetitions of the drift panel at `ae3f0a5`, checked exact target calculations and every selected paper table, and integrated its bounded conclusions. The paper now distinguishes different nulls/error events, asymptotic versus finite-sample guarantees, actual budgets/replicate counts, and unretained protocol chronology.

A separate proof review verified the fixed-stake normalization argument for crossings of a running-conditional-mean threshold. The precise conditions and current-prefix conjunction rule are in the paper; adaptive-stake, random-threshold and retained-old-evidence generalizations are explicitly excluded. A score-range reference requested by the reviewer was added. No executable numerical code changed in the core, only a corrected docstring.

PR 8 at `c89b525` now reproduces its raw/pinned-source and aggregate records, and fixes the original two-sided hedge. The independent reviewer found that the same-task t/Hoeffding inference still needs a stable independent-outcome model or a justified dependence-aware replacement under shared orientation/pass assignments, with nondegenerate variance assumptions. It also found conservative zero-count endpoint arithmetic and an anonymous-map path error. Concrete counterexamples and repairs went to the existing owner; no completed model collection was repeated. Final airline observations are still absent. PR 8 remains outside the revised release.

The 36-page intermediate release keeps main content through page 9. Independent clean extraction/rebuilds pass, with 188 payload hashes, 104 result checks, five anonymous-copy provenance mappings and identical PDF text from both code/source archives. The first release review found an identifying temporary-directory path in a diagnostic manifest; the anonymous-copy sanitizer was broadened and the corrected archive rechecked. All pages were visually inspected. Original records and the earlier release remain preserved. See the Round 10 scientific, integration, release and visual reports. Checklist readiness remains 70%, pending final incoming-result disposition and actual author inputs.

## Round 11: accepted coding subset and newly delivered airline evidence

Three independent evidence, target and integrated-code checks accepted the narrow coding integration from `c89b525`. Root retained all 1,182 observations as a declared metric projection, verified all 886 comparison rows, every one of 295 normal-mixture band rows, resources, source definitions and provenance. The revised manuscript labels inference post hoc and not selection-adjusted, targets running history-conditional means, distinguishes marginal from joint coverage, does not certify the success guardrail, and retains same-task results descriptively. Contributed E2/R2 uncertainty and defective endpoint routines are excluded rather than declared fixed. A reviewer-requested token-cap wording correction was applied. Details and concern-by-concern dispositions are in `round11_integration_ledger.md` and the three coding reports.

The release audit passed: 215 payload hashes, 114 result checks, byte-identical new aggregate regeneration, all 37 preexisting numerical CSVs unchanged, and identical 38-page PDF text from clean code/source builds. All pages were visually inspected; main content remains within nine pages. No further model or generated-program execution occurred.

During this work the airline owner deposited `3c70c3e`, reporting canonical coverage of all 196 planned units. This is substantive new evidence, still outside the paper. Initial review identifies unsupported task-independent/fixed-mean intervals, omitted failed-attempt resource use and inconsistent amendment timing. The existing owner retains repairs and full invocation accounting; root does not duplicate the experiment. Readiness remains 70% while final airline disposition and actual author inputs are pending.

## Round 12: final retained airline integration and technical release

Separate evidence, inference and integrated reviewers independently checked the airline source and every retained comparison. All 196 canonical records, 194 saved trajectories, two placeholders, 206 attempts and amendment flags reconcile. Success is derived from archived reward fields, with missingness explicit; recorded usage comes from saved messages. Both historical runner versions were recovered and matched to invocation hashes. A separately reconstructed lower bound identifies at least 246,284 omitted generated tokens; complete failed-attempt consumption and immutable decision chronology remain unavailable and are not claimed.

The root manuscript retains descriptive results and a conditional observed-array replay illustration with its known target, independent-coin assumptions and post-hoc scope stated. It excludes unsupported task-t/Welch/fixed-mean/ratio intervals, resource significance and universal impossibility claims. Minor caption and reward-provenance wording findings were corrected and rechecked. Coding endpoint/map repairs pass independently, while residual owner filtration/asymptotic/causal wording remains excluded. Accepted PR 7/10 files and all prior observations remain unchanged.

The separate final release audit verifies 241 payload hashes, 127 result checks, byte-identical airline aggregate reproduction, and clean 40-page PDF rebuilds from both archives. Root visually inspected all 40 pages and enlarged changed pages; main content ends on page 9. The completion-scope review distinguishes completed retained-claim requirements from unachieved broader live A/B ambitions. Thus S6/E4/M4/Q4 close for the defined scope, raising the fixed rubric from 70 to 90. A1/A2 remain pending; no paper submission, author signoff or acceptance is asserted. The hourly monitor remains active.

## Round 13: versioned owner reports and execution-queue disposition

The owner delivered `01f2381940fcf5bc57129f1498382cb40f3ea741` after merging the root release without rewriting frozen commits. Two separate reviewers checked the new reports/addenda and text generators. The named Round 12 requests and all five late fixes are present; reports and manifests regenerate exactly, numerical correction values agree, and originals are preserved. Root verifies all 221 preexisting coding/airline files and all 240 tracked release-payload source paths are unchanged. The paper and both archives therefore remain the exact validated Round 12 release; no redundant rebuild or model run was performed.

A few excluded-report precision/index items remain, documented in `round13_integration_disposition.md`, but no retained-paper defect was identified. This is correction acceptance, not approval of model-dependent owner intervals or a broad PR merge. Execution issues 1/2 are closed with explicit narrowed acceptance and deferred broader ambitions, following the owner's agreement. The fixed rubric remains 90/100; actual author verification/declarations and abstract-submission status remain pending. No human or venue confirmation is inferred.

## Round 14: bounded owner-report cleanup

The exact PR 8 head `be4b8e4d406c26f16225420493a900105fd20244` passes an independent bounded check of the nine airline and one coding substitutions, literal passage digests and byte-identical report/manifest regeneration. All earlier numerical tables and scope qualifications remain. Root separately verifies 229 prior owner files, 240 release-payload source paths and all three artifact hashes are unchanged. The requested report cleanup is closed; no full experiment, paper change or archive rebuild was needed.

Two index-only attribution notes remain separate: verified endpoint arithmetic is not approval of generic projections/width methods, and the owner's pair-24 e-process reading is descriptive under R1 rather than root's retained normal-mixture inference. They do not reopen the accepted report fixes or require more experiments. Execution issues 1/2 stay closed with narrowed scope and broader ambitions deferred. Readiness remains 90/100; actual author milestones and submission confirmation remain pending. See the Round 14 independent review and integration disposition.

## Round 15: index-scope notes closed

Independent text review at `ce8b5063d3bb579e1c605828ca07f0ff28d6c326` confirms both remaining index clarifications: endpoint-only verification is distinct from excluded generic projection/width methods, and the pair-24 descriptive e-process reading is distinct from root's retained pair-60 normal-mixture analysis. No broader acceptance claim was introduced. Root confirms the index-only delta and unchanged 236 owner-tree files, 240 release-payload paths and three artifact hashes. No requested PR 8 report/index repair remains, and no full study or release check was repeated. The scientific release remains `45e8ee2`, readiness 90/100, and actual author milestones/submission confirmation pending. See the Round 15 independent review and integration disposition.
