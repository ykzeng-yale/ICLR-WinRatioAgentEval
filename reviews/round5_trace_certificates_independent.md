# Round 5: independent audit of archived trace certificates

Reviewed September 17, 2026, America/New_York. This is an AI scientific review, not human peer review or an acceptance prediction. This report is the only file created or changed by this follow-up reviewer. No paid model requests, repository mutations, original-source edits, or experiment-output overwrites were made.

## Verdict

**The reported archived-prefix feasibility result passes this independent audit.** I independently reconstructed all 10,008 comparisons directly from the retained source files using a separate closed-form interval calculation. All 3,426 first certificate times reproduced exactly, and all 195,171 prefix intervals contained the final recorded score and were nested. This is substantive evidence that useful conservative score certificates can be constructed from actual archived agent-message prefixes under the stated replay convention.

The result materially addresses the principal empirical gap in Round 4. The paper no longer relies only on artificially masked final endpoints to demonstrate that accrued resource information can certify a hierarchical comparison. It still does not measure concurrent execution latency, realized deployment savings, online randomized error control, safety, or the correctness of the source success grader. Those are appropriate scope limits, not reasons to discard a valid fixed-archive feasibility result.

My updated ICLR assessment is **a credible focused evaluation-methodology submission with borderline scientific strength**, stronger than the previous borderline-to-weak-reject assessment. The principal residual uncertainty is whether the protocol synthesis and practical evidence are sufficiently original and useful for ICLR. The probability machinery remains largely established. I do not infer likely acceptance from this audit.

## Audited version and independent checks

The stable audited sources are:

- `experiments/run_trace_certificates.py`: SHA256 `a9cc6db2c1c388876d68addb2728c27fd62997daeb37d6591d7bcf1166849695`.
- `evidence/trace_certificate_protocol.md`: SHA256 `1eeb845fa203bbd4f03de61a01b7878541598d4dadb6009e0a14901ee5916e25`.
- Existing comparator SHA256 `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9`.
- Public-source manifest SHA256 `c272cba7fda65458d131666fc29f81fcfcc917540827c91fb38e2f11a7a318a5`.

I checked those hashes and all four output hashes against `results/trace_certificate_manifest.json`. All matched. I independently verified the hashes of the nine retained raw archives, parsed their actual assistant messages and recorded final outcomes, and reconstructed costs, issued tool-call counts, episode lengths, task identifiers, trial indices, and source seeds.

The independent reconstruction found:

| Check | Result |
|---|---:|
| Source files checked | 9 |
| Episodes reconstructed | 3,336 |
| Actual assistant messages | 51,247 |
| Off-diagonal comparisons | 10,008 |
| Prefixes independently checked | 195,171 |
| Early certificates reproduced | 3,426 |
| Fraction of recorded comparisons | 34.2326% |
| First certificate times differing from supplied CSV | 0 |
| Maximum absolute Decimal message-sum/final-cost discrepancy | 3.565e-16 |
| Actual threshold products checked against exact rational arithmetic | 57,919 |

These were not merely a rerun of the worker's certificate function. My principal reproduction used an independently written interval formula and the raw archives. A second bounded check used the worker's functions to test exact threshold equality, neighboring values, hidden-field perturbation, and interval completion coverage. It checked 28,224 finite endpoint/count completions against rational arithmetic. Sixteen changes to unrevealed labels, final costs, and future message suffixes left the tested pending revealed state unchanged.

## Nonanticipation and episode mapping

**Locations:** `experiments/run_trace_certificates.py:61–103, 158–225, 228–287`; protocol sections “Ordinal replay schedule” and “Mandatory cost and count audit.”

The implementation correctly separates scheduling and validation from the certificate engine. The scheduling layer necessarily knows the archived trajectory length to emit messages and the terminal marker. A pending state contains only the exposed cumulative cost/count, an unknown success label, no finite upper resource bound, and the exposed message count. The engine at lines 127–141 receives those revealed states, not the complete `Episode` objects.

The pending branch at lines 102–103 does not inspect the episode's final success or cost to tighten its interval. The final label and exact final cost become available only when `tick >= terminal`. For an episode containing L assistant messages, `terminal = L + 1`; tick L exposes the final assistant message but still leaves the label unrevealed. The added terminal tick is explicit in the protocol. Trailing tool/user messages and verifier completion are represented by that convention rather than assigned their actual timestamps.

Cost increments are taken from actual assistant messages and verified finite and nonnegative. Tool-call increments count issued assistant calls, including multiple calls within a message. They are not counts of successfully executed actions. Non-assistant messages do not contribute a fictitious agent cost; the assistant sums reconcile to the archived agent totals. Zero-cost initial assistant messages remain in the ordinal schedule, consistently with the stated protocol.

The common numerical allowance, `7.446604e-10`, is derived during the complete-archive audit and passed identically to every replay. It uses archive-wide final information solely to widen pending cost sets; it is not an episode-specific hidden-cost feature. This is acceptable for the stated fixed-archive validation. It should not be presented as a prospective stream procedure whose constants were chosen without inspecting the archive. An operational implementation would need a separately justified accounting allowance or fixed resource cap.

Computing the final truth before replay is not itself leakage: those values are used for validation and final descriptive fields. The certificate calculation does not consume them. The final diagnostic example file now omits future terminal/lead metadata and unrevealed final tiers; its 27 examples disclose pending success and final cost as `unknown`.

## Completion sets and the independent derivation

**Locations:** `experiments/run_trace_certificates.py:106–155, 243–258`.

The resource-score conditions correctly form an outer set of possible scores over the stated rectangular intervals. An A cost win is feasible if its lower possible cost is strictly below .95 times B's upper possible cost, allowing infinity. A B cost win has the symmetric condition. Cost equivalence is feasible exactly when each lower endpoint, multiplied by .95, is no greater than the opposite upper endpoint. If cost equivalence remains possible, the code includes every feasible sign of the issued-call comparison. Ignoring cost/call dependence enlarges the feasible set and therefore remains conservative.

The success hierarchy enumerates both labels for every pending episode. Discordant labels decide on success; two failures tie; two successes enter resource comparison. This covers all feasible future labels and resources under the chosen fixed archived endpoint. It does not infer success from the absence of a failure or from a long/short unfinished trace.

For the independent reconstruction, both pending episodes immediately imply interval [-1,1]. When one episode is complete and failed, the interval is [-1,0] in complete-minus-pending orientation. When it is complete and successful, let c and k be its final cost and call count, and d and m the pending episode's cost/count lower bounds. The interval's upper endpoint is +1 because the pending episode may fail. Its lower endpoint is:

- -1 if `d < .95*c`, or if `.95*d <= c` and `m < k`;
- otherwise 0 if `.95*d <= c` and `m <= k`;
- otherwise +1.

Reverse the signs when the completed episode is B. When both finish, use the exact final hierarchy. This independently derived rule produced the supplied earliest singleton time for every comparison. It also verifies that an early sign requires one completed successful episode and one still-pending episode; early ties do not occur under this disclosure convention.

## Numerical thresholds

**Locations:** `experiments/run_trace_certificates.py:27–31, 109–122, 149–154, 184–199`.

The strict cost-win inequalities and non-strict cost-equivalence inequalities correctly retain equality at the 5% threshold as a cost tie, permitting the tool tier. Tests at costs 95 and 100 returned a tie with equal tool counts and a tool win with unequal counts; a nearby cost below 95 gave a cost win.

All actual archive-derived cost bounds have at most 20 significant Decimal digits. I checked every relevant multiplication by .95 against exact `Fraction` arithmetic: all 57,919 products were exact. The initial independent final-score calculation used `abs(cA-cB) > .05*max(cA,cB)` rather than the worker's equivalent ratio inequalities; every recorded final sign agreed. The common allowance is far larger than the largest observed cost reconciliation discrepancy and preserves every pending lower bound.

One out-of-scope numerical probe with more than 28 significant digits encountered default-Decimal rounding at a threshold. This does **not** affect the audited archive: the exact rational checks above establish that its actual threshold products do not round. It means the script should remain described as a checked fixed-archive implementation, not an exact arbitrary-precision interval library. If generalized to higher-precision or differently scaled inputs, set sufficient Decimal precision or use exact rational comparisons and retain boundary tests.

## Counts, weighting, and the terminal-marker sensitivity

**Locations:** `experiments/run_trace_certificates.py:290–310, 324–341`; `results/trace_certificate_pairs.csv`; `results/trace_certificate_summary.csv`.

Every task/model-contrast combination contributes exactly 12 off-diagonal trial comparisons. Same-index seeds are excluded and the retained seed values differ. Three contrasts times 278 tasks times 12 gives 10,008. Airline contributes 50 tasks and each other domain contributes 114, so the pooled rate weights tasks equally and does not weight domains equally. Dependence from reused runs, shared tasks, contrasts, and seeds remains; 10,008 is a descriptive comparison count, not an independent statistical sample size. The current protocol correctly avoids confidence intervals and deployment tests.

All nine domain/contrast early counts reproduced: airline 235, 218, 250; retail 548, 739, 448; telecom 431, 287, 270, in the fixed contrast order o4-mini–GPT-4.1, Claude-3.7–GPT-4.1, o4-mini–Claude-3.7. The highlighted retail and telecom o4-mini–Claude comparisons have 448/1,368 = 32.75% and 270/1,368 = 19.74% early certificates.

The extra terminal marker warrants one additional descriptive distinction. An ordinal lead of one tick means all assistant messages in both arms have already been exposed, but one terminal label remains hidden. A lead of at least two means at least one actual assistant message remains unrevealed. From the existing pair CSV:

| Scope | All early certificates | Early while an actual assistant message remains | Fraction of all comparisons for the latter |
|---|---:|---:|---:|
| Entire archive | 3,426 | 2,595 | 25.93% |
| Retail, o4-mini versus Claude-3.7 | 448 | 291 | 21.27% |
| Telecom, o4-mini versus Claude-3.7 | 270 | 236 | 17.25% |

The remaining 831 early certificates precede only the added terminal marker. Reporting this distinction prevents an artificial-marker interpretation from inflating the perceived amount of unrevealed trajectory information. It also shows that the feasibility result is not solely a consequence of adding that marker. This sensitivity requires no new data or modified experiment.

The completion-only comparator at the later terminal marker is appropriate under the chosen disclosure rule. It is not a universally fastest verifier or a measured production comparator. Ordinal lead describes how much later that replay marker arrives, not seconds, calls avoided, monetary savings, or a sequential deployment-time reduction.

## Early sign versus eventual tier

Every early certificate remains ambiguous about its eventual deciding tier. Of the 3,426 certificates, 3,163 permit `success|cost` and 263 permit `success|cost|tools`. The summaries' `early_final_success_tier`, `early_final_cost_tier`, and `early_final_tools_tier` are retrospective classifications after both episodes finish. They are not facts known at certification.

The manuscript may say that the **final sign** was guaranteed under every permitted completion. It must not call these “early verified successes,” “early known cost-tier wins,” or evidence that the pending episode's final failure was predicted correctly. A successful completed winner defeats the pending counterpart under either of its possible success labels, potentially for different reasons.

## Required interpretation and updated integrated conclusion

No scientific correction to the recorded certificate counts or first-certificate times is required. The independent reconstruction, source reconciliation, and exact numerical checks support the stated result. The manuscript should include the terminal-marker sensitivity, preserve the distinction between known sign and eventual tier, and retain the artificial replay and fixed-archive limitations. The lead agent was sent those findings during integration; this reviewer has not certified the final typeset manuscript or package.

Round 4's statement that actual trace-based certificate feasibility was entirely unvalidated should now be retired. A narrower remaining statement is appropriate: **archived-prefix feasibility is demonstrated; prospective concurrent timing, deployment gains, source-grader validity, and transport to a new workload remain unvalidated.** The new analysis is a post-primary-study, internally specified replay on already known historical data. It is not an independent new benchmark sample or external preregistration.

This materially strengthens the paper's agent-specific empirical contribution without changing the novelty attribution of the underlying statistical tools. The appropriate next step is to finish accurate integration and reproducibility of this bounded result, rather than demand arbitrary additional runs. Whether the combined protocol, theory exposition, historical reversals, and prefix feasibility constitute a sufficiently substantial ICLR contribution remains a judgment for human reviewers.

## Final manuscript wording check

I subsequently read the generated `paper/trace_certificate_results.tex`, `paper/trace_certificate_appendix.tex`, and the updated abstract and limitations paragraph. The numbers and interpretations agree with this audit. The appendix includes the added terminal-marker sensitivity, distinguishes known sign from eventual tier, labels the comparison counts dependent, and makes the artificial disclosure schedule and lack of deployment/latency evidence explicit. There is no blocking factual correction in the inspected wording.

Two small precision edits were sent to the lead agent. First, “before the later terminal marker” is less ambiguous than “before both terminal markers”: every early certificate already has one completed successful episode. Second, the example at `paper/trace_certificate_appendix.tex:39` should refer to B's **certified cost lower bound** exceeding c_A/.95, matching the numerical allowance, rather than merely its raw accrued record. In the abstract, “demonstrating archived certificate feasibility” would be slightly more precise than “validating completion bounds,” although the existing sentence is already qualified by its ordinal historical replay context.

The independent reconstruction was executed as an inline read-only Python program during this review, not originally saved as a standalone script. Its inputs were the manifest and pair CSV plus the nine retained raw archives listed above. The successful execution and exact code remain in the review task's tool transcript. The report's explicit closed-form interval derivation describes the independent calculation; it does not imply that an executable independent verifier had already been packaged.

The lead agent subsequently authorized packaging that existing calculation. It is now saved as `experiments/verify_trace_certificates_independent.py`, with no personal paths, no imports from the original certificate engine, and no output mutation. Run from the supplementary package root with `python experiments/verify_trace_certificates_independent.py --raw-dir /path/to/empirical_sources`. The saved version was executed successfully once and again reproduced 3,426 early certificates, all 10,008 first-certificate times, 195,171 prefix checks, 2,595 certificates with an actual message remaining, and 57,919 exact rational threshold-product checks. It also checks the source/output hashes, raw source hashes, task comparison denominators, and supplied summary counts. The supplementary verifier packages the completed audit; it does not run new agent experiments.
