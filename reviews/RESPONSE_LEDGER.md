# Scientific review and revision ledger

These are model-assisted project reviews, not external human peer review. Scope and any reviewer/developer overlap are disclosed in each report.

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
