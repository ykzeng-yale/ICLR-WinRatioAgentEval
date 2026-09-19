# Round 13: owner report-only inference corrections

**Verdict: PASS for the named Round 12 mathematical/interpretive corrections and all five required late verifier fixes at the committed head.** Accept these as corrected owner-report documentation. The model-dependent intervals remain excluded from the root paper; this review does not recommend importing them. Remaining owner-report precision items below do not expose a retained-paper defect or require a model run, numerical rerun, manuscript change, or archive rebuild.

Frozen head: **`01f2381940fcf5bc57129f1498382cb40f3ea741`**, inspected September 19, 2026. Scope: the two `protocol_addendum_round12.md` files, coding `report_v4.md`, airline `report_final_v2.md`, their report-generation replacement logic, and `reviews/session60_round12_report_corrections_verification.md`, compared with the Round 12 findings. This reviewer previously contributed project theory and the Round 12 airline inference review, but did not write the owner corrections. This is model-assisted review, not human peer review.

All inputs were read as exact Git blobs into outer `work/round13_report_inference/`. No owner branch, source, report, analysis or observation was modified. No model, generated benchmark program, full analysis runner, report generator or Monte Carlo was executed. Checks comprised text inspection and small scalar arithmetic. Only this review and assigned outer scratch were written. Root separately owns the source/result/archive-preservation audit.

## 1. Named Round 12 findings are closed

| Finding | Exact corrected location | Disposition |
|---|---|---|
| Coding mixed a full-coin filtration with a fair-current-coin conditional mean | `experiments/local_stream/protocol_addendum_round12.md` §1; `results/local_stream/report_v4.md:49,52` | **Closed.** F contains the complete orientation schedule; its conditional mean is for the realized orientation. G leaves the current/future coins unrevealed. The symmetric formula is attached only to G, conditional fairness and a stable conditional joint episode law. No stability assumption is said to restore randomness to a coin already known under F. |
| Information fixed before outcomes was asserted independent of them | Coding addendum §1; report:52 | **Closed.** The phrase is expressly withdrawn. Adaptedness and boundedness suffice for the general history-conditional-mean construction. |
| Approximate cluster-t inference lacked cluster CLT assumptions | Coding addendum §2; report:92–98 and interval-status rows | **Closed.** Variance growth/nondegeneracy, Lindeberg/no-dominant-cluster and variance-estimator consistency are stated. The independent-cluster Hoeffding bound is kept separate and does not require a CLT. Independence across clusters remains unestablished for the actual shared-machine collection. |
| Pass differences attributed mainly to task composition | Coding addendum §3; report:110 | **Closed.** The report now says the table mixes composition and possible workflow-specific period effects and cannot separate them. |
| Airline history-conditional inference incorrectly required common means/independent episodes | `experiments/tau2_open/protocol_addendum_round12.md` §1; `results/tau2_open/report_final_v2.md` §12.1 | **Closed.** Any adapted bounded score supports the stated running conditional mean. Task reuse means constancy is not guaranteed, not that nonconstancy is logically inevitable. This alternative remains unused for airline. |
| Airline final success error copied from the NB error | Airline addendum §2; report §12.1 | **Closed.** NB error is 1/98=.01020408; success error is 1/49=.02040816. Known target means remain 1/98 and zero, respectively. |
| Separate airline bands risked a joint 95% interpretation | Airline addendum §3; report §§0,12.1 | **Closed.** Each band is marginal 95%; the generic simultaneous lower guarantee is 90% unless error is allocated. Coinciding observed paths do not make their targets equal. Neither success noninferiority nor guarded deployment is certified. |
| Unqualified resource significance, universal noncertifiability and finite-roster t conservatism | Airline addendum §4; report:24,42,75,258–261 | **Closed for the named claims.** The significance and universal impossibility claims are withdrawn; t intervals are model-dependent and approximate with additional regularity conditions. Canonical resources are descriptive and omit discarded work. A residual method-specific rhetorical phrase is listed below. |
| Descriptive observations, replay illustration and excluded model decisions were mixed | Airline report §0 and six local status pointers; addendum §5 | **Closed for the requested separation.** Model-dependent intervals and their sensitivity/verdict outputs are explicitly excluded from root integration. The known-array illustration is distinct from both descriptive counts and fresh-run/population inference. |

### Mathematical check

For either valid coding filtration H=F or H=G, let μ_k=E[Z_k|H_(k−1)]. Because Z_k lies in [−1,1] and is adapted, conditional Hoeffding gives

```
E[exp{λ(Z_k−μ_k)} | H_(k−1)] ≤ exp(λ²/2).
```

The established normal-mixture bound therefore covers the running average of μ_k with V_n=n. The two filtrations produce different targets for the same observed interval; coverage for one does not imply a joint statement about both. Under G, the symmetric formula follows from conditional probability 1/2 for each current orientation and the stipulated conditional **joint** law of the two pair episodes. A pseudorandom seed alone does not establish conditional fairness after past outcomes; that is an explicit assumption here. The report does not adopt the stronger interpretation for its actual latency-bearing experiment.

The cluster counterexample remains correct: with 296 independent Bernoulli(1/296) cluster variables and sizes 2 except one singleton, all totals vanish with probability **0.3672571469723**, producing a zero-width t interval that misses the positive target. The stated independent-cluster final-time Hoeffding radius is **0.1579427507649**. These are mathematical boundary checks, not new evidence about the empirical law or its coverage.

For airline, the full observed-array construction still conditions on the retained array and matching, leaves future replay coins outside the filtration, and assumes nominal independent fair coins independent of collection/amendment/retention. Its target is already computable. The scalar n=49 radius remains **0.6297318533794**, with band [−0.6093236901,0.6501400166] around 1/49. No running-mean, full-array, fixed-roster or fresh-run target has been silently substituted. The correction adds no success certificate or operational stopping claim.

## 2. All five late owner-verifier requirements are present

The owner verification report initially recorded PARTIAL and later appended an owner disposition explicitly saying its final edits were not independently rechecked there. I checked the committed final files directly; the earlier PARTIAL must not be presented as their final mathematical verdict.

| Late requirement | Direct final-file check |
|---|---|
| 1. Replace “Resolved secondary facts,” remove interval-cell emphasis and neutralize component/sensitivity significance language | Airline report:261 is descriptive with no significance claim; the two specified component cells at:86,89 are plain; sections 3.3 and 7.2 use model-dependent interval wording and a status pointer. |
| 2. Remove “Forty-nine pairs cannot resolve” and “whatever the truth” | The report's:42 now restricts the statement to the stated rule/interval and these data. Both phrases are absent from final report text and included in the generator's banned-phrase assertions (`make_report_final_v2.py:149–151`). |
| 3. Add six local status pointers and repair checklist/provenance ratings | Pointers occur at report:79,101,144,204,255,315. The section-0 location map includes 7.2,8,10. At:329,350 uncertainty is not established for the model-dependent intervals. At:327 the append-only run manifest is explicitly distinguished from unverified amendment-decision chronology. |
| 4. Withdraw finite-roster conservatism and state regularity conditions | Report:75 explicitly withdraws it, adds variance growth, Lindeberg/no-dominant-task and consistent variance estimation, and marks the intervals excluded. Airline addendum §4 records the withdrawal. |
| 5. Repair the coding sentence boundary | Coding report:52 reads “it is not the conditional identity. Thermal state…” and names the stable assignment/episode-law model. |

The optional conditional-joint-law clarification also appears in the coding addendum. Coding Figure 2 now embeds the v3 path (`report_v4.md:65`), and its caption distinguishes the task-t and cluster-Hoeffding bands. This review checked the reference and caption, not image bytes or the figure/source manifest; root owns that preservation check. All seven bounded Boolean checks in outer `bounded_checks.json` passed.

## 3. Remaining owner-report precision items — separate from retained-paper validity

These are suitable for one consolidated optional owner-document cleanup. They do not reopen the named core corrections, authorize the excluded intervals, or require rebuilding the unchanged submission package.

1. **Superseding-document pointers are inconsistent.** Airline `report_final_v2.md:3` still lists the Round 10 addendum first “in order of precedence,” and §12 calls it governing; coding `report_v4.md:52` still ends with a Round 10 Definitions pointer. The banners and new addenda correctly make Round 12 govern, so the intended scope is recoverable. Put Round 12 first in every governing/Definitions pointer to remove this conflict.
2. **One failure-treatment invariance sentence is too broad.** Airline report:217 says “No descriptive observation of this report depends on the treatment,” immediately after giving resource means and denominators that change when placeholders are omitted. Replace it with “The planned retained-record analysis remains the primary analysis; its E1 and E2 NB are unchanged in this sensitivity, whereas resource summaries and some denominators change.” The root paper already reports the treatment and resource boundary correctly.
3. **“All abstain” needs the primary-rule scope.** Airline report:258,260 describes all interval-based/uncertainty-aware rules as abstaining, while section 4 reports positive intervals for some alternative hierarchy/tolerance rows. Say “the primary-rule interval-based comparisons abstain”; keep the sensitivity outputs explicitly separate. They remain excluded from root inference either way.
4. **Keep the radius extrapolation method-specific.** Airline report:57 still calls n=12,094 the “honest price of the assumption-free reading.” The arithmetic is for this normal-mixture boundary and ρ only. Replace the rhetoric with “For this boundary and ρ, the radius reaches .03 at n=12,094; this is not a lower bound for other methods.” Its stated coin model is an assumption, even though no task-sampling model is used.

The root separately identified stale headline intervals and an old integration-state table in `results/SESSION60_RESULTS_INDEX.md`. Those are index-disposition cleanup, not defects in the corrected addenda or evidence that new model work is required. Likewise, minor copied report-title/generation metadata should be distinguished from current banners and versioned provenance. This reviewer did not expand into a new full report or index audit.

## 4. Exact disposition

Record the named Round 12 correction requests and all five late fixes as **closed at `01f2381` for owner-report documentation**, with the above optional precision items retained for future reuse. Do not call this approval of every owner interval or a change in root scientific claims. Correct algebra and clearer assumptions do not empirically establish an iid task law, independent clusters, stable period effects or a fresh-run population target.

The root package continues to use the previously reviewed coding metric projection, root post-hoc running-mean bands, descriptive same-task results and descriptive/conditional-array airline illustration. No retained-paper defect was found in this correction audit. The separate root preservation audit controls whether old source/results and final archives are unchanged; I did not rerun it here.

Execution issues 1/2 may be disposed as delivered collections with **explicitly narrowed acceptance and deferred broader confirmatory/independent-replication ambitions**. Neither batch replay nor a single local schedule establishes all the original stronger ambitions. Such issue disposition does not itself change the fixed readiness score, supply author verification/declarations, or establish submission/acceptance.

## Evidence anchors

| Frozen document | SHA-256 |
|---|---|
| Coding `protocol_addendum_round12.md` | `cf13276cddd343231ebf19e13b5750816d1ddc56d1192499a345249eaf8dfe48` |
| Coding `report_v4.md` | `806d82ce35d55d9c573b806575d3d4176ffbb4e89cbe9d8d2281d92d80ae59bd` |
| Airline `protocol_addendum_round12.md` | `a240d6ac8db6033166a7a6825b9740af0fe237b182965bf05b77d8d7883377e7` |
| Airline `report_final_v2.md` | `11f5691e54ac2603e229a10524685b69d91035620d20fe8748e500efc257b3cc` |

The complete read-only snapshot/hash record and bounded checks are in outer `work/round13_report_inference/`. No owner files, root manuscript, archives or Git state were changed by this review.
