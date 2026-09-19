# Session 60, Round 12: verification of the report-only corrections (coding stream and tau2 airline)

Date: 2026-09-19. **This is a model-assisted check, not human peer review.** The verifier did not write the corrections. No git command was run, no existing file was edited or deleted, no language model or network call was made; only small CPU-only Python checks (`.venv/bin/python`) and `shasum`/`diff` were used. This report is the only file written. (Two `__pycache__/*.pyc` files that an in-memory regeneration check created as a side effect were removed again; nothing else was touched.)

Objects verified (all new, untracked): `experiments/local_stream/protocol_addendum_round12.md`, `experiments/local_stream/make_report_v4.py`, `results/local_stream/report_v4.md`, `results/local_stream/report_v4_manifest.json`, `experiments/tau2_open/protocol_addendum_round12.md`, `experiments/tau2_open/make_report_final_v2.py`, `results/tau2_open/report_final_v2.md`, `results/tau2_open/report_final_v2_manifest.json`. Reference reviews: `reviews/round12_coding_correction_and_baseline_delta.md`, `reviews/round12_airline_inference_review.md`, `reviews/round12_integration_ledger.md`.

## Verdict

Every sentence that the root named in its four-point request has been corrected, the new mathematics is right, all recomputed numbers reproduce, and the originals are byte-preserved with correct manifests (both scripts regenerate the deposited outputs bit-for-bit). The corrections are, however, **narrowly targeted string replacements**, and the airline report `report_final_v2.md` still contains, in passages that were not touched, (i) a significance-equivalent resource claim ("Resolved secondary facts", line 251) that contradicts the new "no significance claim" status, (ii) a second unqualified impossibility statement ("Forty-nine pairs cannot resolve a 0.03 guardrail", line 42) of the same kind as the one that was withdrawn in section 8, and (iii) sections 3.3, 4, 5, 7.2, 8 and 10 that present excluded model-dependent intervals, verdicts and "met" ratings with no local qualifier and no pointer to the new status section. The coding corrections are complete apart from one broken sentence boundary introduced by a replacement. Overall: **PASS on correctness and preservation; PARTIAL on completeness of the airline report** (five required wording fixes below; no rerun and no number change is needed).

## Table of checks

| Check | Scope | Verdict |
|---|---|---|
| A | Root's four points addressed (11 sub-points) | **PARTIAL**: 10 of 11 PASS; 4a (separation of statement kinds) PARTIAL |
| B | Mathematical correctness of the new wording and recomputation | **PASS** (two optional precision notes on the coding assumptions) |
| C | Preservation: hashes, diffs, only wording changed | **PASS** |
| D | Residual problems (a)-(f) in the four new documents | **PARTIAL**: (a) residuals, (b) one residual, (c) PASS, (d) PASS, (e) PARTIAL, (f) PASS |
| E | Other errors, inconsistencies, conflicts with the root reviews | **PARTIAL**: one introduced grammar defect, one unsupported "conservative" claim left from root P2, several minor documentation inconsistencies |

## A. Are the root's four points addressed?

Line numbers refer to the new files.

**1a Filtration (PASS).** `experiments/local_stream/protocol_addendum_round12.md:31-35`: "Under `F_(k-1)` the orientation of pair k is already known. `E[Z_k | F_(k-1)]` is therefore the conditional mean of the score **in the realized orientation**. A filtration that contains every realized coin cannot also give the coin of pair k conditional probability 1/2, and no stability assumption restores that randomness." Coarser filtration, lines 37-47: "`G_k = sigma( arrival order, pairing ; orientations and revealed pair data of pairs 1..k )`, which leaves the orientation of pair k unrevealed at time k - 1", with assumptions 1 (fair coin independent of `G_(k-1)`) and 2 (stable assignment / episode-law model). The unnecessary phrase is withdrawn at lines 27-29 ("information fixed before the outcomes existed is not thereby independent of them"). The same correction appears in `results/local_stream/report_v4.md:13` (summary item 5), `:49` (R1 table row) and `:52` (caption). The unconditional identity is kept distinct from the conditional one (addendum lines 52-54; report line 52).

**1b Cluster-t conditions (PASS).** Addendum lines 63-68: "Independent clusters with bounded totals do not by themselves justify the t approximation. It additionally needs - variance growth / nondegeneracy of the cluster totals, - a Lindeberg or no-dominant-cluster condition, and - a consistent cluster variance estimator." Propagated to `report_v4.md:10`, `:92` (with the counterexample), `:94` (table header), `:124`, `:157`, `:159`. The exact cluster Hoeffding bound is kept separate (addendum lines 75-77).

**1c Pass/roster (PASS).** `report_v4.md:110`: "these descriptive differences mix task composition with possible period effects (including workflow-specific period effects); the table does not separate them (Round 12 correction: the earlier wording that the differences "largely track which half of the roster was exposed" is withdrawn, because the split does not identify how much comes from either source)." Addendum lines 81-84 say the same.

**2a Resource significance (PASS for the named sentence; residuals under D(a)).** `results/tau2_open/report_final_v2.md:24`: "On canonical records B made fewer assistant tool calls per episode (5.3 versus 10.0; same-task mean difference -4.68) and had less agent generation time (84 s versus 128 s; -44.1 s) ... **No statistical-significance claim is made for any resource difference**, and canonical totals omit discarded attempts ... so no operational-efficiency, total-cost or elapsed-saving claim is made either." Airline addendum lines 50-55 withdraw "B used significantly fewer assistant tool calls".

**2b Impossibility claim (PASS for the named sentence; residual under D(b)).** `report_final_v2.md:249`: "The specified replay rule and the reported intervals did not certify the 0.03 margin on these data. That is a statement about these rules and these data. The retained records and a sample-size heuristic do not prove that no method could certify the margin on these tasks, and no such method-independent claim is made." Addendum lines 56-59 withdraw the "whatever the method" sentence.

**3a History-conditional construction (PASS).** Airline addendum lines 18-23: "For any score `Z_k` in [-1, 1] adapted to a filtration `F_k`, `Z_k - E[Z_k | F_(k-1)]` is a bounded martingale difference, and the normal-mixture boundary covers the running mean of `E[Z_k | F_(k-1)]` uniformly in n. This needs **no common mean and no independent episodes**. Reuse of the 49 tasks across the two trial blocks means that a constant conditional mean is **not guaranteed**; it does not mean that the conditional mean must vary in every model." Same content at `report_final_v2.md:367`. The two withdrawn Round 10 phrases are quoted accurately (checked against `protocol_addendum_round10.md:49`).

**3b Final errors (PASS).** `report_final_v2.md:367`: "net benefit |0.020408 - 0.010204| = **0.010204**; success difference |0.020408 - 0.000000| = **0.020408**." Addendum table lines 30-33 gives the same values.

**3c Target and coin assumptions preserved (PASS).** `report_final_v2.md:367`: "The target and its guarantee are as stated above: the orientation average of the observed array, under nominal independent fair coins, with collection, amendment and retention independent of those coins." Addendum lines 35-39 add "the pre-pair history excludes future coins" and "the band is an illustration of a masked replay, not an inference about new tasks, fresh runs or production."

**3d Marginal, not joint (PASS).** Addendum lines 43-46: "Together they do **not** form a joint 95% statement; the union bound gives at least 90% simultaneous coverage, and a joint 95% statement would need the error budget to be split. Their observed paths and endpoints coincide in this data set; their targets do not (0.010204 and 0)." Same at `report_final_v2.md:367`.

**4a Separation of statement kinds (PARTIAL).** Done at document level: new section 0 (`report_final_v2.md:11-20`) classifies six kinds of statement, e.g. row 3: "**Model-dependent; assumptions not established by the design; excluded from the root integration.** Kept here for the record of the prespecified analysis. They are not to be read as supporting any conclusion beyond the descriptive rows above." The summary (line 24) is restructured into "Descriptive observations", "Observed-array replay illustration" and "Model-dependent intervals". Addendum section 5 (lines 63-73) mirrors this. Not done inside the body: sections 3.3, 4, 5, 7.2, 8 and 10 are unchanged and mix the kinds (details under D(a), D(e)); the section-0 "where" column omits 7.2, 8 and 10, and places the infrastructure-exclusion sensitivity in "sections 4, 12.4" although it is in section 7.2 (line 209).

**4b Unverified items and no-conclusion list (PASS).** `report_final_v2.md:20`: "The actual sampler receipt, an immutable decision chronology for deviation 1 and complete failed-attempt usage remain **unverified**. No fresh-run, production, equivalence or operational-saving conclusion follows from this report." Addendum lines 75-77 identical in substance.

## B. Mathematical correctness

**(i) Two filtrations (PASS).** `F_k` (full schedule including all coins, plus revealed data of pairs 1..k) and `G_k` (order, pairing, orientations and data of pairs 1..k only) are both increasing, `G_k` is contained in `F_k`, and `Z_k` is a function of pair k's orientation and records, hence measurable with respect to both. For either filtration `Z_k - E[Z_k | .]` is a martingale difference with conditional range 2 (variance proxy 1 by Hoeffding's lemma), so the normal-mixture boundary with `V_n = n` covers each running conditional mean. The claim "the same boundary also covers the running mean of `E[Z_k | G_(k-1)]` because `Z_k` is adapted to `G_k`" is **correct**, and it needs neither assumption 1 nor 2. "Two different targets for one realized interval; each statement is valid separately and neither implies the other" is correct. Under assumptions 1-2, `E[Z_k | G_(k-1)] = (1/2) E[Z_k | G_(k-1), R_k = 1] + (1/2) E[Z_k | G_(k-1), R_k = 0] = [m(s_k,t_k) + m(t_k,s_k)]/2`: **correct**, provided assumption 2 is read as a statement about the conditional joint law of the two pair-k episodes given `G_(k-1)` and `R_k`. The root's deterministic counterexample is consistent with the new text (under `F` the conditional mean is the realized +/-1; under `G` with a fair coin it is 0). Nothing is overstated; the symmetric reading is explicitly "not assumed in any report". Two precision notes (optional, listed below): assumption 2 is phrased for "the law of each episode" (marginals), whereas `m(s,t) = E h(Y_B(s), Y_A(t))` needs the joint law of the pair (conditional independence of the two episodes or a stable joint law); and the parenthesis "(the nominal model of the seeded design)" on assumption 1 slightly undersells it, because `G_(k-1)` contains outcomes, so independence of coin k from `G_(k-1)` also needs that the collection of pairs 1..k-1 did not use coin k.

**(ii) Cluster counterexample (PASS).** Target: `(1/591) sum_g n_g E[B_g] = (2*295 + 1)/(591*296) = 1/296 > 0`. If every `T_g = 0` then `NB_hat = 0`, all linearized residuals are 0, the cluster variance and t width are 0, and the interval {0} misses 1/296. Recomputed with 40-digit decimals: `(1 - 1/296)^296 = 0.36725714697230...`, float `0.36725714697229994`; the reports' `0.367257147` and the manifest value agree. (The task-level analogue already in v3, `(1-1/591)^591 = 0.367568`, also reproduces.)

**(iii) History-conditional statement (PASS).** Any adapted score bounded in [-1, 1] has a conditionally sub-Gaussian centred increment with variance proxy 1, so the boundary covers the running mean of `E[Z_k | F_(k-1)]` with no common mean and no independence of episodes. "Not guaranteed" versus "must vary in every model" is the correct logical distinction and matches root P2.

**(iv) Union bound (PASS).** Each band fails with probability at most 0.05 under the same coin model, so both hold simultaneously with probability at least `1 - 0.05 - 0.05 = 0.90`; a joint 95% statement needs a split budget (for example 0.025 each). Correct.

**(v) Recomputation from `results/tau2_open/round10_handoff_numbers.json` (PASS).** Independent script (exact rational arithmetic; does not import the owner's code), 49 pairs, fields `z_obs, z_R1, z_R0, dq_obs, dq_R1, dq_R0`:

| score | observed mean | target | final abs. error | max path error | at n | target inside band at every n (unclipped and clipped) |
|---|---|---|---|---|---|---|
| net benefit | 1/49 = 0.020408 | 1/98 = 0.010204 | 1/98 = **0.010204** | 3/8 = 0.375 | 4 (unique) | yes |
| success difference | 1/49 = 0.020408 | 0 | 1/49 = **0.020408** | 3/8 = 0.375 | 4 (unique) | yes |

Radius `sqrt((n+100) log((n+100)/(100*0.05^2)))/n`: r_49 = 0.6297318534, band [-0.6093236901, 0.6501400166]; r_24 = 1.1559143018; first n with r_n < 1 is 29; first n with r_n <= 0.03 is 12,094. `z_obs`/`dq_obs` equal the orientation score selected by the recorded `R` in all 49 rows; W/T/L = 10/30/9; 24 pairs have unequal orientation scores. All agree with the root table (`round12_airline_inference_review.md:45-54`) and with `report_final_v2_manifest.json -> observed_array_replay_numbers`.

## C. Preservation

| file | sha256 on disk | manifest field | match |
|---|---|---|---|
| `results/local_stream/report_v3.md` | `0a534fd6bacf10e1e28e01e0aa06f57966cb0f6aa5b0d1fdcc2fa07e11a8e378` | `source_sha256` (v4 manifest) | yes; also equals the root's anchor |
| `results/local_stream/report_v4.md` | `c86b40fdb863c1f10827c1720264a0c2a100837750097b9658ea7e24af7be444` | `output_sha256` | yes |
| `results/tau2_open/report_final.md` | `1ae93f5bff68d57eb879c37fb5069b3fc6595c41e18fdce209ec7e1eb86505d0` | `source_sha256` (final_v2 manifest) | yes; also equals the root's anchor |
| `results/tau2_open/report_final_v2.md` | `53a26a88d930c24e73fc390776a05cdec94d5d5decfe812c8a5370618f160781` | `output_sha256` | yes |
| `results/tau2_open/round10_handoff_numbers.json` | `a6937828fbf82aabbacda3863f18dd3c0111aa786a9b3448f3282d8739754124` | `numbers_source_sha256` | yes; equals the root's anchor |

Also unchanged against the root's anchors: `experiments/local_stream/protocol_addendum_round10.md` (`790cd549...`), `experiments/tau2_open/protocol_addendum_round10.md` (`c6053533...`), `results/local_stream/summary_v3.json` (`35880a11...`). Both generator scripts were executed with their output paths redirected to a scratch directory; the regenerated reports are byte-identical to the deposited `report_v4.md` and `report_final_v2.md`. The cited root integration commit `45e8ee2715f148c81db7f6510d66677f57e03f0a` equals the value stored in `.git/refs/remotes/origin/main` (file read, no git command).

**`diff report_v3.md report_v4.md`: 1 insertion + 10 changed lines, wording only.**
1. after line 2: Round 12 banner (new lines 3-4).
2. line 8 -> 10 (Round 10 change 2): cluster-level CLT conditions appended.
3. line 11 -> 13 (change 5): full-schedule conditioning; symmetric formula only under coarser filtration plus model.
4. line 47 -> 49 (R1 table row): filtration and conditions cells reworded; numeric cells `0.1828`, `[-0.6540, -0.2883]`, `60`, `[-0.1320, 0.2337]` identical.
5. line 50 -> 52 (caption): two replacements (filtration; symmetric formula).
6. line 90 -> 92 (cluster analysis): CLT conditions and the counterexample; **only new number 0.367257147** (plus 296, 1/G inside the example).
7. line 92 -> 94 (table header text only).
8. line 108 -> 110 (pass/roster reading aid).
9. line 122 -> 124 (cluster-t label in section 5; `-0.029460`, `0.000540` unchanged).
10. lines 155 -> 157 and 157 -> 159 (decision-table status text; estimates and intervals unchanged).

**`diff report_final.md report_final_v2.md`: 1 insertion + 3 changed lines, wording only.**
1. after line 8: banner and new section 0 (new lines 9-21).
2. line 11 -> 24 (summary): restructured; every estimate and interval of the old sentence is retained (`[-0.114, 0.114]`, `[-0.366, 0.406]`, `[-0.111, 0.121]`, `[-6.87, -2.50]`, `[-75.3, -12.9]`, `[-882, 358]`, 0.020, 0.005, -4.68, -44.1, -262, 0.91, 0.22, 3.00); dropped: "indistinguishable from 0", "significantly", "not resolved", "guarded decision is".
3. line 236 -> 249 (section 8 margin sentence).
4. line 354 -> 367 (section 12.1 tail).

A token-level comparison of all numerals in the changed lines shows **no estimate, interval, count or table number removed or altered** in either report. Numbers that are new in `report_final_v2.md` beyond the two errors and the path check: `28 / 141 / 27` and "196 comparisons" (equal to `p_win, p_tie, p_loss` of `summary.json` times 196: 28.0, 141.0, 27.0), `124 / 70 / 2` (equals 55+69, 27+29+14, 2 of section 7.1), `246,284` (equals 198,280 + 1,428 + 46,576 of section 12.3 and the root ledger's 198,280 + 48,004), `[-0.609, 0.650]` and `0.0102` (already in 12.1). All are consistent with existing sources; none is a new estimate. See E.4 for the documentation mismatch.

## D. Residual problems in the new documents

**(a) Significance claims for a resource difference: residuals in `report_final_v2.md` (not in the addenda, not in `report_v4.md`).**
- Line 251 (section 8, "Adds"): "Resolved secondary facts: B makes about half as many tool calls and spends about two thirds of the agent generation time; ...". "Resolved" is this report's word for "interval excludes 0"; this directly contradicts lines 19 and 24 ("No significance claim"). **Must change.**
- Lines 84 and 87 (section 3.3 table): the same-task entries `**-4.68 [-6.87, -2.50]**` and `**-44.1 [-75.3, -12.9]**` are the only bolded cells; the bolding marks the intervals that exclude 0.
- Line 91: "the two pairings disagree on whether the completion-token difference is resolved, and the same-task pairing is the prespecified test for H2."
- Line 209 (section 7.2): "The duration interval then excludes 0 where the frozen one ([-77.1, 0.5]) just includes it; H2 remains unresolved either way."
- Lines 143, 145 (section 5): "Not resolved ...", "its premise H2 is itself unresolved", "the same-task interval is above 0" (these are verdicts on excluded intervals; see (e)).

**(b) Method-independent impossibility: one residual.** `report_final_v2.md:42` (section 2, "Power, stated honestly"): "the interval's lower end, -0.114, cannot clear -0.03 whatever the truth. ... **Forty-nine pairs cannot resolve a 0.03 guardrail**; the protocol anticipated this". The second sentence is the withdrawn section-8 claim in other words and is false as a method-independent statement (for example 49 B wins out of 49 would certify the margin with a valid bounded-score test). The generator's banned-phrase check looks only for "whatever the method" and does not catch it. Lower priority, same family: line 57 "With this rho the R1 radius reaches 0.03 only at n = 12,094 pairs (N). That is the honest price of the assumption-free reading here" and line 367 "would reach 0.03 at n = 12,094" are method-specific and arithmetically right, but root P2 asked that the extrapolation not be read as a bound for other methods.

**(c) Symmetric formula under a coin-containing filtration: PASS.** Every occurrence of the formula in `report_v4.md` (lines 3, 13, 49, 52) and in the coding addendum (lines 37-50) is tied to the coarser filtration; line 52 states that the formula "is therefore **not** a statement about the filtration above". No residual found (search terms: `m(s`, symmetric, theta_N, coin, fair, filtration).

**(d) Attribution of pass differences to roster composition: PASS.** Only the quoted, withdrawn wording remains (`report_v4.md:110`, addendum line 81). Line 103 ("a difference mixes task composition with any period effect") is neutral.

**(e) Excluded model-dependent intervals presented without a local qualifier or pointer: PARTIAL.** `report_v4.md`: every interval carries a status label in its table or paragraph; the only unlabeled mention is line 19, "orientation-pair cluster-robust interval [-0.705, -0.608]" (no "approximate", but "section 4" is cited). `report_final_v2.md`: the only pointer to section 0 is in line 24. No qualifier and no pointer in:
- section 4 (lines 97-136): decision-rule table with interval-based outcomes and the sensitivity table with outcome "B" at tolerances 0.10 and 0.20 ("only the token-first order at the two widest tolerances gives a same-task interval above 0");
- section 5 (lines 140-146): H1-H5 verdicts built on the excluded intervals;
- section 3.3 (lines 79-91) and section 7.2 (line 209): component intervals; 3.3 says "approximate" for the cross-arrival column only;
- section 8 (lines 248, 250, 255): 'returns "no decision" on all interval-based rules', "uncertainty-aware rules (all abstain)", "An interval of [-0.114, 0.114] is compatible with ...";
- section 10 (lines 317, 338): "correct independent-unit uncertainty | met with stated limits", "uncertainty appropriate for repeated tasks | met with stated limits"; with the root exclusion and addendum section 6 these "met" ratings are overstated. Line 315 "immutable run manifest | met" sits beside the new statement that an immutable decision chronology is unverified; the two refer to different things, but the row should say so.
Sections 3.1 and 3.2 do carry in-paragraph qualifiers (Round 10). Section 12.4 is labelled POST HOC.

**(f) Identifying paths or account names: PASS.** Zero matches for the three patterns named in the verification task (absolute home-directory prefix, private temp prefix, account name), and for generic home, temp-folder, e-mail-domain and surname patterns, in the two reports, two addenda, two scripts and two manifests. The only "claude" hit is the public model name `claude-3-7-sonnet` in the unchanged H5 row.

## E. Other findings

1. **Introduced defect, `report_v4.md:52`.** The replacement ended a sentence where the original had a semicolon, leaving: "it is not the conditional identity. thermal state, execution order and caching can affect latency, so that model is not assumed and ..." (lower-case sentence start; the antecedent of "that model" is now two sentences back).
2. **Root P2 not covered by the four-point request but still in the new report, `report_final_v2.md:75`:** "The intervals are conservative for the finite-roster average and conventional task-clustered intervals under a task-superpopulation model. (Round 10 wording correction: both statements assume independence between tasks. ...)". Root P2 (`round12_airline_inference_review.md:67`): between-task independence alone does not establish a finite-sample conservative t interval; variance/nondegeneracy and asymptotic regularity are also needed. This is the same error as coding point 1b, which was fixed in `report_v4.md` but not here; the airline addendum (section 4) says "normal approximation" but does not withdraw "conservative".
3. **Root P2, "assumption-free".** `report_final_v2.md:34` ("valid for that target with no sampling assumption"), `:57` ("assumption-free reading"), `:317` ("the only reading free of a sampling model") and `:367` ("by design alone") do not name the nominal independent-coin model in the same sentence. The Round 12 sentence later in line 367 does, so this is a wording inconsistency, not an error.
4. **Generator docstring versus content.** `make_report_final_v2.py:10-12` says the only new numbers are the final errors and the success-difference path check. The output also introduces 28/141/27, "196 comparisons", 124/70/2 and 246,284 (all verified consistent, see C). The banner's "hashes and the replaced passages: `report_final_v2_manifest.json`" is also inexact: the manifest stores only sha256 values of the passages; the text is in the script.
5. **Figure 2 of `report_v4.md`.** The banner (line 3) points to "Figure 2 with the corrected legend: `figures_v3/fig2_running_nb.png`", but the body (line 65) still embeds `figures_v2/fig2_running_nb.png`, whose legend says "design-based", and the caption (line 67) describes only one orange band whereas the v3 figure draws two. `figures_v3/` and `make_figures_v3.py` (written 01:55, before the Round 12 files) are in no manifest and are not mentioned in the Round 12 addendum. The figure itself was inspected: legend "R1: 95% normal-mixture CS, running conditional mean"; no identifier.
6. **Precedence pointers.** `report_final_v2.md:3` still lists `protocol_addendum_round10.md` first "in order of precedence", and `report_v4.md:52` ends with "Definitions: `protocol_addendum_round10.md`"; only the banners name the Round 12 addenda as governing. `results/SESSION60_RESULTS_INDEX.md` does not yet point to `report_v4.md` / `report_final_v2.md`.
7. **Token wording.** `report_final_v2.md:24` and addendum line 54 call the 246,284 tokens "generated arm-A tokens". The root ledger calls them "A-collection generated tokens" and notes that the role partition is unavailable (the A server also served the user simulator). Not wrong, but "arm-A collection" is the safer phrase.
8. **No contradiction with the root reviews was found in the two Round 12 addenda themselves.** Their numbers (NB -0.4712, [-0.6540, -0.2883], pair 60, [-0.1320, 0.2337], Hoeffding [-0.8145, -0.4986], radius 0.15794; airline 0.6297, [-0.609, 0.650]) agree with the root's tables.

## Required fixes

All are wording-only, need no rerun and change no number. The new files are still untracked, so regenerating `report_final_v2.md` / `report_v4.md` (and their manifests) in place through the scripts is acceptable; after they are committed, any further change should be a new version.

1. `results/tau2_open/report_final_v2.md:251`: replace "Resolved secondary facts: B makes about half as many tool calls and spends about two thirds of the agent generation time" by a descriptive statement (for example "Descriptive secondary observations on canonical records: B's mean tool calls were about half and its mean agent generation time about two thirds of A's; no significance claim; canonical totals omit discarded attempts"). In the same pass remove the bold from the two interval cells of section 3.3 (lines 84, 87) and replace "resolved / unresolved / excludes 0" in lines 91 and 209 by neutral wording or add "(model-dependent interval; section 0)".
2. `results/tau2_open/report_final_v2.md:42`: qualify or remove "Forty-nine pairs cannot resolve a 0.03 guardrail" and "cannot clear -0.03 whatever the truth" (for example "With this task-clustered t interval at the observed spread, 49 tasks did not resolve a 0.03 margin; this is a statement about this interval and these data, not about every method"). Add both phrases to the banned-phrase assertions of `make_report_final_v2.py`.
3. `results/tau2_open/report_final_v2.md`, sections 3.3, 4, 5, 7.2, 8 and 10: add a one-line status pointer at the head of each ("Model-dependent; excluded from the root integration; see section 0") or an equivalent in-paragraph qualifier; change the section-10 ratings at lines 317 and 338 from "met with stated limits" to wording that does not claim the requirement is satisfied by excluded intervals, and make line 315 distinguish the append-only run manifest from the unverified decision chronology. Correct the "where" column of section 0: the infrastructure-exclusion sensitivity is in section 7.2 (not 4 / 12.4), and sections 7.2, 8 and 10 should be listed.
4. `results/tau2_open/report_final_v2.md:75`: withdraw or qualify "The intervals are conservative for the finite-roster average" (root P2): independence between tasks is not sufficient; state the variance-growth / nondegeneracy, Lindeberg-type and variance-estimator conditions as was done for the coding cluster t interval, and record the withdrawal in `experiments/tau2_open/protocol_addendum_round12.md`.
5. `results/local_stream/report_v4.md:52` (via `make_report_v4.py`, replacement "R1 caption: symmetric formula"): repair the sentence boundary, for example "... it is not the conditional identity. Thermal state, execution order and caching can affect latency, so the stable episode-law model is not assumed and ...".

## Optional improvements

1. Coding addendum lines 43-45: state assumption 2 as a conditional joint law ("conditional on `G_(k-1)` and `R_k`, the two episodes of pair k are independent draws from fixed task- and workflow-specific laws"), since `m(s,t)` is an expectation over the pair; and extend the parenthesis of assumption 1 to "nominal coin model, and collection of pairs 1..k-1 did not use coin k".
2. `report_v4.md:19`: label the cluster-robust interval "approximate" in the summary sentence.
3. `report_v4.md`: either embed `figures_v3/fig2_running_nb.png` with a caption that describes both orange bands, or drop the banner sentence; record the sha256 of the figure files and of `make_figures_v3.py` in `report_v4_manifest.json` and mention them in the Round 12 addendum.
4. `report_final_v2.md:34, 57, 317, 367`: add "under the nominal independent-coin model" next to "no sampling assumption", "assumption-free", "free of a sampling model" and "by design alone"; next to "n = 12,094" add "for this boundary and rho; not a bound for other methods" (root P2).
5. `make_report_final_v2.py` docstring and manifest: list all numbers that are new in the text (28/141/27, 196, 124/70/2, 246,284) with their sources; correct the banner phrase "the replaced passages" (the manifest holds hashes only) or store the old/new text in the manifest.
6. Add the Round 12 addenda to the precedence sentence of `report_final_v2.md:3` and to the "Definitions" pointer of `report_v4.md:52`; add a section 12.8 (airline) listing the Round 12 replacements, parallel to 12.7; point `results/SESSION60_RESULTS_INDEX.md` to the new versions in a later, versioned edit.
7. Use "A-collection generated tokens (role partition unavailable)" instead of "generated arm-A tokens" (`report_final_v2.md:24`, airline addendum line 54).
8. `report_v4.md` section 8: the verdict words "H2 supported", "H3 refuted on both contrasts" rest on model-based intervals; a pointer to the section-4 status paragraph would pre-empt an objection.

---

## Owner disposition after this verification (added by the session-60 coordinator, 2026-09-19)

The files had not been committed when the verification ran, so the five required fixes were applied by extending the
two generator scripts and regenerating `report_final_v2.md`, `report_v4.md` and their manifests in place. The
sources `report_final.md` and `report_v3.md` remain byte-unchanged.

1. Applied: section 8 now says "Descriptive secondary observations on canonical records ... no significance claim";
   the two emphasized interval cells of section 3.3 are plain; "resolved / excludes 0" wording in sections 3.3 and 7.2
   is neutral and points to section 0.
2. Applied: both section 3.1 phrases are replaced by statements about this interval, this rule and these data; both
   are in the banned-phrase assertions of `make_report_final_v2.py`.
3. Applied: status pointers at the head of sections 3.3, 4, 5, 7.2, 8 and 10; the section 10 ratings no longer claim
   that excluded intervals satisfy a requirement; the run-manifest row separates the append-only manifest from the
   unverified decision chronology; the "where" column of section 0 is corrected.
4. Applied: the "conservative for the finite-roster average" sentence is withdrawn with the CLT-type conditions
   stated, and the withdrawal is recorded in `experiments/tau2_open/protocol_addendum_round12.md` section 4.
5. Applied: the sentence boundary in the R1 caption of `report_v4.md` is repaired.

Optional items applied: assumption 2 of the coding addendum is phrased as a conditional joint law of the two episodes
of a pair; the coverage statement for the coarser filtration says that it needs neither assumption; `report_v4.md`
embeds `figures_v3/fig2_running_nb.png` and its manifest records the figure hashes; "by design alone" in section 12.1
of the airline report now names the nominal coin model; the generator docstring lists the numbers that are newly
quoted. Not re-verified by the independent agent after these edits; the generator assertions (exact match counts and
banned phrases) passed.
