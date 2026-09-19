# Round 12: contributed coding correction and accepted-baseline delta audit

Reviewed September 19, 2026. Frozen coding correction: PR8 `c1da1c3fc4e8c90644388e8b47e2e15574fe5215`. This is an AI scientific/code audit, not human peer review. Only this review and outer-workspace `work/round12_coding_delta/` were written. No source/Git mutation, model call, generated-program execution, collector execution, or heavy Monte Carlo occurred. The root's accepted coding analysis was not changed.

**Verdict: PASS for the endpoint repair, reported numerical calculations, and accepted-baseline preservation; substantial closure of the excluded contributor defects.** Three remaining qualifications concern the contributor's optional interpretation/approximation text, below. They do not invalidate the unchanged root R1 analysis or descriptive same-task results and do not warrant another coding experiment. Do not automatically import the new cluster intervals or the contributed generic inference module.

## Closure of prior findings

| Prior finding | Round 12 disposition |
|---|---|
| Zero-count endpoint terms dropped a valid stake through `0*log(0)` | **Resolved for the repaired constructions and checked domain.** Zero counts now contribute zero; positive counts on zero factors still kill that stake. The new regression test passes, and independent `xlogy` calculations agree. This is not certification of arbitrary custom stake grids or all other contributed functions. |
| E2 task-level intervals described as assumption-free/design-conservative | **Withdrawn and appropriately narrowed.** V3 labels them model-based under independent task scores and stable/no relevant period-effect laws. The actual shared orientation-coin counterexample is retained. |
| Boundedness alone invoked as a CLT | **Resolved for the original task-level t claim.** The owner now names variance-growth/Lindeberg and variance-estimator conditions. The newly added cluster-t statement needs the analogous qualification; see finding 2. |
| Fixed-roster and iid interpretations blurred | **Substantially resolved.** R1 is explicitly post-hoc and targets a moving conditional mean; R2 uses an unconditional hypothetical iid-roster model and a coarse filtration. One optional R1 assignment-average sentence still conflicts with its stated filtration; see finding 1. |
| Missing anonymized data-manifest target | **Resolved.** The formerly missing content is committed at `results/local_stream/release_anon/local_data_manifest.anon.json`; all 14 mapped targets exist and match their listed hashes. This does not endorse releasing all full raw/program-bearing records; the root's minimal projection remains the accepted release. |
| Stale PR body | **Resolved at the live read.** PR8's body now points to v3, withdraws old intervals/claims, and retains post-hoc, model, margin and E1/E2 limits. The live head was `04989e88efd548e4f40a12366b6534a5aad18ed8`; this code audit remains frozen to `c1da1c3`. Airline claims in that body belong to the separate airline audit. |

## Independent bounded checks

I extracted only read-only Git blobs into scratch. For code checks, AST extraction evaluated the inspected pure capital/inversion functions and only the new endpoint regression test, excluding module mains and older heavy tests. No collection or contributed aggregate runner was executed.

- The new `test_endpoint_normalization_round10` passes, including empty/degenerate endpoint capital 1, scalar/vector consistency, support endpoints and conservative outside inversion iterates.
- Independent `scipy.special.xlogy` formulas agree on **3,465 ternary** small-count/candidate-mean combinations and **1,911 Bernoulli** combinations, including endpoints and zero counts. Maximum log-capital discrepancies are 1.89e-15 and 1.78e-15, respectively.
- Recalculation with the repaired pure functions matches **all 1,770 R2 interval endpoints** in the 295-row archived path exactly: net benefit, success difference and decided-pair win ratio, both endpoints, maximum discrepancy zero. This verifies numerical preservation, not empirical validation of the iid-roster model.
- All **296 orientation-cluster rows** were reconstructed directly from the unchanged raw same-task outcomes and design: 295 two-task pairs plus the singleton. Score/success totals, task membership and component scores match. The estimator correctly remains total score divided by 591; it does not incorrectly average unequal-sized cluster means.
- Independently calculated cluster standard errors and both intervals match `summary_v3.json`; the common final-time Hoeffding radius is **0.1579427508**. Pair totals have range length 4 and the singleton length 2, so `sqrt{2(4*295+1)log(40)}/591` is correct under independent clusters.
- Both descriptive pass-table rows match raw-record counts, success rates, mean/median latency, completion-token means and between-pass differences.
- All **81 scoped manifest hashes** resolve to the frozen source/output blobs. The six original raw evidence files are byte-identical to the preceding `c89b525` head. Four v2 numerical CSVs remain byte-identical; `summary_v2.json` is unchanged after removing only its generation timestamp and source-code hash.

| Cluster calculation | Same-task net benefit | Same-task success difference |
|---|---:|---:|
| Estimate | −0.6565143824 | 0 |
| Cluster-robust SE | 0.02487695893 | 0.01496906479 |
| Approximate t interval | [−0.7054731858, −0.6075555790] | [−0.0294596900, 0.0294596900] |
| Independent-cluster final-time Hoeffding interval | [−0.8144571332, −0.4985716316] | [−0.1579427508, 0.1579427508] |

These are reproduced contributor calculations, **not new accepted manuscript intervals**. The cluster Hoeffding guarantee is mathematically correct for the assignment-averaged same-task target under the stated independent-cluster law, conditionally on the fixed roster/pairing as appropriate. The actual two-pass experiment does not establish independence across clusters; shared machine history remains an explicitly acknowledged limitation.

## Remaining contributor-only qualifications

### 1. R1's optional symmetric assignment mean needs a different filtration

**Pointers at frozen head:** `experiments/local_stream/protocol_addendum_round10.md:18–21,36–39`; `analysis_v3.py:51–53`; corresponding R1 caption in `results/local_stream/report_v3.md`.

The addendum puts the entire realized orientation sequence in F0, then says a stable episode-law model permits `mu_k = {m(s_k,t_k)+m(t_k,s_k)}/2`, with the coin fair conditional on the past. Stability alone cannot restore randomness to a coin already included in that conditioning information. Also, information collected before outcomes is not automatically independent of future observed outcomes.

Exact counterexample: task s always succeeds and task t always fails under either workflow, with completely stable deterministic episode laws. If A is assigned s and B t, the score is −1; with the reversed orientation it is +1. Given the full orientation in F0, the conditional mean is the realized ±1, whereas the symmetric assignment average is 0.

**Correction:** retain the general running conditional-mean guarantee after conditioning on the full schedule, dropping the unnecessary independence-of-design-and-future-outcomes phrase. State the symmetric formula only under a separate, coarser filtration that leaves the current orientation unrevealed and fair, plus the stable assignment/episode-law assumptions. The unconditional identity averaged over assignment can still hold under its additional model; it must not be confused with the conditional identity. Root's accepted appendix already distinguishes these cases correctly.

### 2. Add cluster-level CLT conditions to the new t approximation

**Pointers:** `analysis_v3.py:49–50,92–101`; addendum `:116–123`; report's cluster-t table and discussion.

The new cluster-t output says “approximate” and “valid under independent orientation-pair clusters,” but omits the variance-growth/Lindeberg and suitable variance-estimator conditions it correctly adds to the old task-level t interval. Independence and bounded cluster totals alone do not establish its approximation.

A direct small counterexample uses G=296 independent cluster variables B_g ~ Bernoulli(1/G), cluster sizes n_g=2 except one singleton, and T_g=n_g B_g. The target is 1/G > 0. With probability `(1−1/296)^296 = 0.367257147`, all totals are zero, the stated cluster variance and t width are zero, and the interval misses the target. This is a limitation of a blanket coverage claim, not evidence that the current observed sample has that law.

**Correction:** add cluster-level nondegeneracy/variance-growth, Lindeberg or no-dominant-cluster conditions and appropriate variance-estimator behavior to the approximate t status. Keep the exact independent-cluster Hoeffding bound separately; it does not need the CLT. No new simulation is needed for this wording repair.

### 3. Do not attribute descriptive pass differences primarily to task composition

**Pointer:** `results/local_stream/report_v3.md:108` and its generating text in `experiments/local_stream/make_report_v3.py`.

The report first correctly states that pass differences mix task composition with period effects, then says they “therefore largely track which half of the roster was exposed.” The displayed split does not identify how much comes from either cause; workflow-specific period effects can produce the same pattern. Replace this with “These descriptive differences mix task composition with possible period effects; the table does not separate them.” This does not change any number or support broader inference.

## Accepted-baseline deltas

| Accepted component | Old accepted head | New branch head | Result |
|---|---|---|---|
| PR7 all-pairs sequential source/results/report | `ac17f5901bcf4efba6c71e970d3a4c1cf1ed06cb` | `88d64343ab5b8a5448f3bd238d4befa54ee86acc` | **All 26 accepted files have identical Git blob IDs.** The whole-branch delta changes only `src/wincs.py` and `src/test_wincs.py`; neither is part of the accepted all-pairs subset. |
| PR10 drift source/results/report | `ae3f0a5d4936855fc0b81f4a327254e932ea729b` | `e0f7dab374399bdb173f7a5f675347b11078f878` | **All 12 accepted files have identical Git blob IDs.** The newer commit is based directly on root `1001b23`; relative to that root it adds only `reviews/drift_panel_audit_session60.md`. It contains no new drift experiment/result change. |
| Root accepted coding builder, analytical data and three manuscript files | `1001b23a89bc67a345766d432d90541d7e75ccd2` | initial Round 12 audit checkpoint | **All 13 files matched the accepted commit bytes at that checkpoint.** |

After that initial checkpoint, root reported intentionally shortening `paper/open_coding_results.tex` and adding an airline input during Round 12 integration. The 13-file byte-equality finding is historical to the recorded checkpoint, not a claim that the later manuscript summary remains byte-identical. That subsequent integration is outside this contributed-correction audit.

The ownership decision remains unchanged: retain root's separately audited observation projection, post-hoc R1 calculation and descriptive E2 estimates. The repaired contributed endpoint routines and optional cluster intervals are excluded unless separately requested and reviewed for integration. This audit supplies no reason to regenerate the accepted coding model outputs, PR7 simulations or PR10 drift panel.

## Audit records

Outer-workspace scratch `work/round12_coding_delta/` contains the selected frozen snapshot, `verify_delta.py`, `independent_results.json`, and `baseline_and_manifest_check.json`. The checker performs small deterministic arithmetic and selected unit tests only. The source/report hash anchors below identify the reviewed correction, independently of the later live PR head.

- `src/wincs.py`: `601865d9adf0a9f1a0f20c44ef78cb18dffe33fdc3beb5d98a47d6c5199b8754`.
- `src/test_wincs.py`: `87e3be85e1cc24f3a993d677548a2ba1f4b03673c2e146f1bec93cef58412e21`.
- `experiments/local_stream/analysis_v3.py`: `c40bb3fc0304e36a745976872f852736a06e9f60466b197b78d740503ff638a0`.
- `experiments/local_stream/protocol_addendum_round10.md`: `790cd549f2f6d365cdcd3a8eed21ce96108e129e114e9901cc38ec9ac2fdd6d6`.
- `results/local_stream/summary_v3.json`: `35880a11628088c8f9b836f2b954c72d3cc11fe9147d1960516b5a7eaaa05ab5`.
- `results/local_stream/report_v3.md`: `0a534fd6bacf10e1e28e01e0aa06f57966cb0f6aa5b0d1fdcc2fa07e11a8e378`.
- `results/local_stream/analysis_v3_manifest.json`: `82b73608267148794a31e2e9f7603af7c80a88770a99347d00a83d0b812e9624`.
