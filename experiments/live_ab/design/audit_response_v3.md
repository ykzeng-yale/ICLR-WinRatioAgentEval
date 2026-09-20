# audit_response_v3.md — disposition of every finding of `audit_v3.md` and of every `PROTOCOL-GAP`

Final editor, session 60, 2026-09-19. Outputs: `protocol_FINAL.md` (supersedes `protocol_v3.md`) and
`ARCHITECTURE_FINAL.md` (supersedes `ARCHITECTURE.md`). Inputs read in full before editing:
`reviews/arxiv_live_design_guidance.md`, `COORDINATOR_DECISIONS.md` (revisions 1 and 2), `protocol_v3.md`
(2,602 lines), `ARCHITECTURE.md` (2,046 lines, including all 25 `PROTOCOL-GAP` entries), `audit_v3.md`
(880 lines). Nothing outside `live_ab_design/` was written; no existing file was edited or deleted; no git
state was changed; no model call, server or download.

**Editing rule followed throughout.** Where the auditor demanded new machinery, the claim was narrowed or a
limitation was declared instead, unless the machinery was the only way to make two binding documents state
one rule. New machinery was added exactly three times: `lab_reference_rule.py` (B2 — the freeze deliverable
and protocol 8.9 already named the file, so the alternative was to delete a promise the root will check),
the call-event evaluation trigger (B3 — without it the enclosure machinery is dead weight and the two
documents disagree at pair 1 of T4), and the 60-second worktree check (B7 — the alternative was to reopen
coordinator decision C15, which is forbidden). **No coordinator decision and no root-guidance clause was
reopened.** The rule block (protocol 6.2-6.4, 7, 8) changed only where the audit proved it was internally
contradictory (M4, M6) or arithmetically wrong (M12, B5).

**Numbers recomputed with `.venv/bin/python` against `src/winstats.py` before writing:** `r(568) =
0.1579515124940428`, so the deploy threshold at the horizon is `r(568) - 0.03 = +0.1280` (the audit's
"+0.1283" in B4 was a rounding slip and is not used); `r(569) = 0.157802`; the `rho` sensitivity at
`n = 568` (0.1595 / 0.1561 / 0.1580 / 0.1737 / 0.2270); the first-crossing table (unchanged); the
reachability thresholds 17,097 / 5,789 / 1,378 / 626 / 372 (unchanged); `floor(591/2) + floor(547/2) = 568`.

---

## 1. Blockers

| id | finding | resolution | sections changed |
|---|---|---|---|
| **B1** | `ARCHITECTURE` implemented the superseded v2 hierarchy: three tiers, `relative_tolerance` 0.10, certificate constant 0.9, per-trial `n_tiers` | **Architecture corrected to the protocol, and a freeze test added so the pair cannot be frozen in disagreement.** `TIER_NAMES = ('success', 'latency_s')`; `tiers_from_config` returns `[Tier('success'), Tier('cost', higher_better=False, relative_tolerance=0.05)]` for **all four** trials and raises `FrozenMismatch` on anything else; the certificate reads `0.95 * ell > L_r + 1e-9`; `n_tiers` deleted; `completion_tokens` is recorded, never scored; `test_equality_is_tie` names two tiers; new `test_two_tiers_only`. The subordination sentence is in `ARCHITECTURE_FINAL.md` §0 and in the protocol header; the freeze test `rule_block_sha256(config) == rule-block hash of the protocol's own tables` is in protocol Appendix C and ARCH 3.1/6.2/9.2 | ARCH §0, 3.1, 3.7, 6.1, 6.2, 9.2 (G1, G3); protocol header, Appendix B, Appendix C |
| **B2** | `lab_reference_rule` — named in protocol 8.9, 14.2 row 10, 14.3 and 6.4 row 24 — did not exist in the implementation contract, so the "shadow" compared `lab_monitor` with itself, `monitor_mismatch` was unreachable and the freeze bundle could not be assembled | **Option (a): the module is real.** New `ARCHITECTURE_FINAL.md` §3.8b `lab_reference_rule.py`, **owned by G1, not G3**, stdlib + numpy + `winstats` only, importing **no** `lab_*` module at all (strictest row of the import matrix), written from the protocol text without reading `lab_monitor.py` or `lab_enclosure.py`. It is called as the live shadow at rows 6, 7 and 8 of the state machine; its values and `mismatch` flag are written into every `monitor_update`; `lab_verify_log.reference_rule.agreement` calls `decide_from_chain` after the trial; a new test requires an injected sign slip, swapped count and wrong denominator each to be caught by the shadow at the first evaluation at which it changes anything. N19 is closed again rather than re-opened as residual risk | ARCH §0 AD-7, 2.1, 3.3, 3.8b, 3.13, 3.16, 4.4 T19, 7.1, 9.2, 10, 11 PG-3, 12; protocol 8.9, Appendix C, Appendix D (N19) |
| **B3** | The look cadence differed three ways: protocol 8.3 "every reveal-order event", state-machine row 7 (no look at call events), `replay()` (consumes call events). A `plumbing_fail` would have invited a harness-only re-freeze of the **live monitor** | **The cadence is settled in the protocol, as a closed trigger list, and every other document follows it.** Protocol 8.3: triggers are `pair_enrolled`; pre-decision `episode_revealed`; any `llm_request`/`llm_response`/`llm_error` that **raises the certified `ell`** of a pending episode of an enrolled pair; one per resume; plus a non-deciding `drain` update after a decision. `monitor_update.trigger` enum gains `call` and `drain`. 12.3's verifier rule becomes "exactly one `monitor_update` per evaluation trigger of 8.3". ARCH state machine gains rows 7 (certified-elapsed recompute, update, `monitor_update(trigger='call')`, `decide()`), 7a (a decision at a call event) and 7b (events that trigger nothing); `replay()` documents the same trigger set; new verifier check `monitor.cadence`; new G3/G5 tests including "a certificate that binds at an `llm_response` produces a look and can decide" | protocol 0, 1.1, 5.1, 8.1, 8.3, 9.1, 12.2 #16, 12.3, Appendix C; ARCH §0, 3.3, 3.8, 4.4 T19, 4.6, 7.1, 9.2, 11 PG-1/PG-2 |
| **B4** | 1.3's bolded "A DEPLOY decision is unreachable by construction at this scale, whatever the outcomes" is false, and the next sentence contradicts it | **The false sentence is replaced everywhere by the true conditional one**, and the two phrases are added to the forbidden list. New wording: the roster gives at most 568 pairs; a DEPLOY requires an observed running success difference above `r(N_P) - 0.03` = `+0.1280` at `n = 568` (`+0.1278` at 569); the pilot difference is 0.000000 with paired s.e. 0.0151, i.e. about 8.5 s.e. away; the route is a **pre-specified near-certain abstention**, **not a logical impossibility**, and if it occurs it is reported under Appendix E's DEPLOY template with no claim that it was impossible. `test_deploy_unreachable_at_scale` is renamed `test_deploy_threshold_at_scale` and now asserts both directions | protocol 0, 1.3, 1.4 claim 8, 1.5 item 13, 10.2, 11.4, 16 item 10, Appendix E; ARCH §0, 9.2 G3, 3.16 (no test name may contain "unreachable") |
| **B5** | The two documents built a different number of randomization units (`n_total // 2` with one **mixed** pair vs stratified pairing), and the protocol's own "at most 569" was wrong under its own rule | **Stratified pairing only, `N_P = floor(n_S1/2) + floor(n_S2/2) <= 568`, no mixed pair, each stratum keeps its own leftover.** `PairSlot.stratum` loses `'mixed'`; `build_roster` returns `n_S1 // 2 + n_S2 // 2`; `test_order_stratified` asserts "no mixed pair"; PG-21 rewritten; `MonitorConfig.n_max` becomes a **required field with no default** and must equal `roster.n_pairs`. Every horizon use of 569 became 568 (at-a-glance table, 1.3, 1.4 claim 8, 8.5, 11.3, 11.4, Appendix B, Appendix E, D2 dry run, radius fixtures); the radius tables keep an `r(569)` row explicitly labelled a reference row | protocol 0, 1.3, 3.3, 3.4, 4.3, 8.5, 11.2, 11.3, 11.4, Appendix B, Appendix E; ARCH §0, 3.4, 3.5, 6.1, 9.2 G2/G3, 9.3 D2, 10, 11 PG-21 |
| **B6** | `metrics_scrape` was declared an enclosure-updating reveal-order event, so the verifier would demand looks inside the follow-up cohort, which 9.3 forbids — a FAIL whichever way the orchestrator is written | **`metrics_scrape` is removed from the reveal-order list**, and 7.3 item 3 now names every event class that is *not* one (`metrics_scrape`, `server_*`, `anchor*`, every program-chain event). 12.3 reads "exactly one `monitor_update` per evaluation trigger of 8.3, and no `monitor_update` at any event of the follow-up cohort". New Appendix C test: a quiescent `metrics_scrape` in the follow-up cohort produces no `monitor_update` and the verifier passes. ARCH adds the `monitor.cadence` check and state-machine row 7b | protocol 7.3, 8.3, 12.3, Appendix C; ARCH 3.3, 3.8, 4.6, 7.1, 9.2 |
| **B7** | The working location was an open coordinator item, and a concurrent checkout in the shared clone had no outcome row — it would be reported as "evidence of editing" against the operator | **Closed in the text without reopening C15** (the audit's second option, because its preferred option — a dedicated worktree — would reopen a coordinator decision). Two guards: (1) the worktree identity assertion (real path, `HEAD` branch, `rev-parse HEAD`, clean index, expected parent) **before every commit and at every invocation start**, mapping to `anchor_failed(tree_state)` / `preflight_refused(worktree_identity)`; (2) **new 6.4 row 27 `worktree_drift`**: every `worktree_check_s = 60` s the digests of freeze-bundle files, closed chain segments and `src/winstats.py` are recompared, a difference pauses the trial with the observed and expected digests, a changed closed segment is `trial_aborted(chain_unreadable)`, and **none of it is ever attributed to the operator in 12.6**. `worktree_drift` added to the 14.6 pause table, to the 14.3 threshold list, to `config.json`, to the `program_paused`/`trial_paused` enums, to the state machine (row 24b), to the verifier (`worktree.integrity`) and to the tests. Appendix F's open item is declared closed | protocol 2.1, 6.4 row 27, 12.4 item 2, 12.6, 14.1, 14.3, 14.6, Appendix B, Appendix C, Appendix F; ARCH 3.3, 3.13, 3.14, 4.3 P7, 4.4 T26, 6.1, 6.3, 7.1, 9.2 G5, 11 PG-26 |

---

## 2. Majors

| id | finding | resolution | sections changed |
|---|---|---|---|
| **M1** | The N6 seed fix was absent from the implementation contract (`& 0x7FFFFFFF`, no partition), and `seed_rule` is inside the rule-block hash | Architecture adopts the protocol's rule verbatim: `(os.urandom(4) & 0x7FFFFFFE) \| worker_index`, the low bit carrying the worker index; `worker_index` added to `Job` and to `LlamaClient.__init__`; `config.seed_rule.mask = "0x7FFFFFFE"`, `low_bit = "worker_index"`; new G4 test `test_seed_partition`. The protocol defines `worker_index` as the **slot** (position 1 → slot 0), not the arm, and puts it in the T4 canonical-payload removal list so the partition cannot advantage an arm | ARCH 3.9, 3.12, 6.1, 9.2 G4, 11 PG-8; protocol 5.1, 5.5, 12.3 |
| **M2** | `--slot-prompt-similarity 0.0` was missing from `server_argv` and `llama_args`, so the structural half of the N7 fix would not be built | Added to `ARCHITECTURE_FINAL.md` 3.10 `server_argv` and to `config.llama_args`, with an explicit assertion in `lab_server.start` that the golden `/props` reports it (`receipt.assert_props_reports_slot_prompt_similarity_zero`), plus test `test_slot_prompt_similarity_asserted`. The docstring names the consequence it prevents: an irreversible T2/T1 abort under 6.4 row 12 | ARCH 3.10, 6.1, 9.2 G4 |
| **M3** | The two documents disagreed on the `coin_drawn` body (`raw_hex` present / "the 63 unused bits are not logged"), and the disagreement reversed a declared R2 deviation | **`raw_hex` is kept** (the audit's recommendation: it costs nothing and is strictly more evidence). The "63 unused bits" sentence is deleted from 4.2, the code path logs `raw.hex()`, 12.2 #8 carries `raw_hex`, `config.coin.raw_hex_logged = true`, and the R2 item-6 row of 13.1 changes from "partial, argued" to **"met"**, with the explicit caveat that logging the bytes says nothing about the entropy source | protocol 4.2, 12.2 #8, 13.1, Appendix B; ARCH 3.6, 4.4 T10 (already correct) |
| **M4** | 7.5 item 1 ("collapse only when **both episodes** are revealed") forbade what 7.5 item 5 (the cost certificate) does — in immutable text | 7.5 item 1 rewritten: a valid final-score certificate is **either** both episodes revealed with complete finite outcomes and `compare` returning, **or** the enumeration of item 5 leaving exactly one feasible value. "No other collapse exists." The architecture's `hierarchy_enclosure` and `PairEnclosure.collapsed` say the same, and a new test `test_certificate_collapses_mid_pair` pins it | protocol 7.5 item 1; ARCH 3.7 |
| **M5** | `plumbing_fail` prescribed a harness-only re-freeze for conditions that are defects of decision-defining code, handing the operator a choice between two frozen consequences after outcomes exist | Row 22 **split**. **22a** (receipt mismatches, reconciliation defects, verifier-bookkeeping completeness FAIL): pause, reporting-code re-freeze, next trial — and **a second occurrence of the same condition id stops the program** (this also closes M20 i). **22b** (chain check FAIL, reference-rule disagreement, T4 payload non-identity): **row 24 applies to the affected trial; continuation requires a new protocol version.** "A `plumbing_fail` may never be closed by changing anything in the 14.3 list." `config.plumbing_fail_conditions` carries the two lists; `refreeze_authorization.scope` stays the single-member enum `[reporting_code]`; the verifier prints the list letter next to every FAIL, so the machine chooses, not the operator | protocol 6.4 rows 22a/22b, 14.6, Appendix B, Appendix D (N2); ARCH 3.3, 4.3 P4/P5/P11, 6.1, 11 PG-13 |
| **M6** | A containment violation had two different frozen consequences (7.5 item 6 → 8.9; 14.3 → 6.4 row 24) | 7.5 item 6 now reads: a violation is a **proven defect of decision-defining code** with the consequence of **6.4 row 24** for every trial in which it occurred; `LIVE_DECISION_INVALID` applies **in addition** if the live and reference decisions also differ. "There is no lighter consequence anywhere in this protocol." The verifier's `enclosure.containment` row says the same | protocol 7.5 item 6; ARCH 3.3 |
| **M7** | Three incompatible statements of which anchors block | **One list, written once in `config.json` and referenced by both documents**: `anchor.blocking` = trial_started, decision, trial_paused, trial_resumed, refreeze_authorization, trial_ended, trial_aborted, operator_action, program_paused, program_resumed, preflight_refused, plumbing_verdict_fail, erratum, chain_unreadable. `anchor.push_triggers` = that list plus `every_25_completed_pairs`, which is the only non-blocking trigger. 12.4 item 5 now references the list instead of enumerating three cases; `AnchorRequest.trigger` is the same enum | protocol 12.4 items 4-5, Appendix B; ARCH 3.14, 6.1 |
| **M8** | 7.4 conditioned on `(W_i(1), W_i(0))` as random variables while 7.2 said only conditional laws exist, leaving `mu_i` undefined | The **coupling is stated** in 7.2: an internal-randomness variable `xi_i` (seeds, scheduling, machine state), drawn independently of `R_i` given `H_i`, with `W_i = f_i(H_i, R_i, xi_i)` and `W_i(r) = f_i(H_i, r, xi_i)`, so both potential records live on one space. 7.4 gains the T4 paragraph: under the coupling `f_i` does not depend on `r`, the kernel is antisymmetric in the two positions, so `U_i = -V_i` pathwise and `mu_i = 0` exactly; and the coupling is named as what 5.5's seed rule and 5.1's position-to-slot mapping protect. The coupling is added to the assumption list of 7.4 and therefore to 10.2 item 1 | protocol 7.2, 7.4 |
| **M9** | Guidance item 6's "new disjoint tasks" was not met, and 10.3 redefined the word instead of declaring the deviation | 10.3 now declares it: "**NOT met and declared as a deviation:** all four trials draw from the same roster (3.5 item 5), for the power reason of 3.5 item 2. What is new in each trial is the arrival order and the coins." The same row is added to the deviation table of 13.1 (a new sub-table "Declared deviation from the root guidance", which has exactly one row), to 1.1's "what it does not deliver" list, and to the retained sentence of Appendix E. PG-22 rewritten | protocol 1.1, 10.3, 13.1, Appendix E; ARCH 11 PG-22 |
| **M10** | The side-by-side compression caveat and its statistic existed only for T3, although the within-pair duration asymmetry is larger in T1/T2 | 5.8 item 4 now calibrates **every contrast** solo and side by side and freezes **one `C` per contrast**; 6.2 gains "**Named mechanism 1: the within-pair duration asymmetry, in every trial**" with the 4.456 ratio, the ~100% / ~22% contention shares and the consequence that the frozen 5% tolerance corresponds to a larger tolerance on the solo ratio; `C` is added to section 16 item 6, to Appendix A, to `config.prefreeze.side_by_side_compression_C` and to the Appendix E T1/T2 templates | protocol 1.1, 5.8 item 4, 6.2, 16, Appendix A, Appendix B, Appendix E |
| **M11** | The host-wide execution lock transfers cost from one arm to the other, one-directionally, and was disclosed only as a logged field | 6.2 gains "**Named mechanism 2: the host-wide execution lock transfers cost between the arms**", with the 120 s × 3 executions bound and the sentence that measured cost is **partly a transfer between the arms of a pair**. `sandbox_lock_wait_s` is reported **by arm next to every cost-tier statement** (16 item 9); a prespecified descriptive read-out **S-lock** (8.8 item 8) recomputes the hierarchy with `sandbox_lock_wait_s` subtracted; 7.4's assumption list states that `mu_i` includes the transfer; 1.1 lists it under what the program does not deliver; the builder writes `sensitivity.json` | protocol 1.1, 6.2, 6.4 (S-lock in the read-out list), 7.4, 8.8 item 8, 10.2, 16 item 9; ARCH 3.15 |
| **M12** | `episode_hard_cap_s` was arithmetically wrong (3,306 vs 3,354) in a non-amendable row, and the constant-coverage test would block the freeze either way | The value is corrected to **3,354 s** in 5.6 and in Appendix D's N15 row, **and the row now says the harness computes it from the formula and the pinned `request_timeout_s` and never types it**; `config.execution.episode_hard_cap_s` stays `null` until that computation, with `episode_hard_cap_is_computed_never_typed: true`. The constant-coverage test of Appendix C is narrowed so it can pass: it covers the rule block and the frozen parameter tables, compares formula-derived values against the formula's output, and compares generated tables against `radius_table.csv`. ARCH's third, different cap formula is replaced by the protocol's | protocol 5.6, Appendix B, Appendix C, Appendix D (N15); ARCH 6.1, 11 PG-15 |
| **M13** | The string discipline as written rejects `pair_enrolled`, whose `task_uids` are none of the four declared forms | A **fifth form (e)** is added to 12.2: a task uid matching `^(mbpp\|mbpp_full\|humaneval)/[0-9]+$` **that is present in `roster.json`**, which the validator checks (membership, not merely shape). `config.roster.uid_pattern` carries the regex; Appendix C gains "the validator accepts `pair_enrolled` with roster uids and rejects a uid that is not in `roster.json`"; ARCH T9 and PG-11 are rewritten to the same rule instead of the parenthetical excuse | protocol 12.2, Appendix B, Appendix C, Appendix D (N12); ARCH 3.1 PG-11, 4.2 rule 7, 4.4 T9, 9.2 G1 |
| **M14** | The `monitor_update` body differed between the documents, and the validator rejects unknown and missing keys, so every such event would fail against one of them | The body is written **once**, in `ARCHITECTURE_FINAL.md` §4.4 T19, as the union: the trigger enum, `n`, `n_collapsed`, the four sums, `radius`, the four endpoints, `pair_updated`, `pair_enclosure`, `flags`, **`shadow`** {n, L_h, U_h, L_s, U_s, action, mismatch} and **`readouts`** {L_s_vs_010, L_s_vs_015, s1_restricted, completed_prefix}, plus `sums_fsum` and `monitor_code_sha256`. Protocol 12.2 #16 lists what the body must contain and **cites that row as the normative key set** | protocol 12.2 #16; ARCH 4.4 T19 |
| **M15** | `ARCHITECTURE` retained the `thermal` reason code the protocol removed | Deleted from `program_paused` (P7), from `trial_paused`/`trial_resumed` (T26) and from state-machine row 24, each with a note naming the reason (the probe was removed with the code). `worktree_drift` and `monitor_mismatch` are added to the same enums so the closed list matches protocol 14.6 exactly | ARCH 4.3 P7, 4.4 T26, 7.1 row 24 |
| **M16** | The implementation contract cited the superseded protocol as normative (`protocol_draft_v2.md` §11.6, "protocol 12.5", "protocol 5.7", "protocol 11.4") | Every citation is repointed at `protocol_FINAL.md`: integrity tables → **12.6**, `status.json` → **14.7**, receipt comparison → **13.2**, `--local-only` → 12.4 item 10 and the dry runs. Binding-inputs item 3 now names `protocol_FINAL.md` and states that the two drafts have **no residual force and must not be cited**; `tests_lab_isolation.py` greps every module for `protocol_draft_v2` / `protocol_v3` and fails on a hit | ARCH §0, 1 AD-1, 3.3, 3.9, 3.13, 3.14, 3.15, 3.16, 11 PG-16 |
| **M17** | The guidance-mandated reorder-invariance test was stated in a form that cannot hold once enclosures depend on `ell` | Restated in Appendix C: for any admissible permutation of a set of reveal-order events, the records, both enclosure sums and both band endpoints **after the whole set has been applied** are identical, and the decision (kind and prefix) is identical; **the intermediate sequence of looks is order-dependent by construction and is not compared**. 8.9 supplies the reason the decision prefix is nevertheless order-insensitive (within a prefix, enclosures only narrow, so `U_j` is non-increasing and `L_j` non-decreasing). ARCH adds `test_reorder_invariance` in the same words | protocol 8.9, Appendix C; ARCH 4.6 invariant 6b, 9.2 G3 |
| **M18** | 8.8 item 3 "the success-only composite (tier 0 alone)" duplicates the monitored success score | Item 3 is **redefined as a non-object, not deleted** (deleting it would renumber cross-references in 6.2, 12.2 #16 and 16): "With the frozen two-tier hierarchy, tier 0 alone **is** `D_i`, the score already monitored as the success band; no separate statistic is computed. Wherever this protocol says 'the success-only composite is reported', that means the success band and `Dbar_n` reported with equal prominence." The two genuinely distinct component read-outs are named (items 2 and 4) | protocol 8.8 item 3 |
| **M19** | The roster exclusion selects tasks on the cost dimension and this was not disclosed | New 3.5 item 7, "**Timing-based exclusion, disclosed**": rule 3.2 item 4 removes tasks whose reference verifies slowly under load, so the roster is pre-filtered on the dimension the cost tier mostly measures; validity is untouched (the exclusion is in `F_0` and uses no model output) but the estimand's subject changes. The count and the reference verification times are reported in the freeze bundle and **beside every cost-tier statement** (16 item 9), and the fact is added to 1.1 and to Appendix A | protocol 1.1, 3.5 item 7, 16 item 9, Appendix A |
| **M20** | Three unmapped failure modes | (i) **Repeated `plumbing_fail`**: 6.4 row 22a — "a second `plumbing_fail` with the same condition id stops the program; later trials need a new protocol version". (ii) **Exception in the shadow reference rule**: 6.4 row 17 extended to "live-monitor **or shadow reference-rule** exception", with the addition that an exception inside the reference rule is itself a defect of decision-defining code (row 24) and cannot be re-frozen away. (iii) **Abort inside the follow-up cohort**: a new paragraph in 6.4 — an abort there truncates the follow-up cohort only; the logged decision, `tau` and claims 2 and 3 stand; the number of arrivals that did not run is reported (9.3) | protocol 6.4 rows 17, 22a and the post-decision-abort paragraph; ARCH 7.1 row 22 |

---

## 3. Minors

| id | finding | resolution | sections changed |
|---|---|---|---|
| **m1** | 9.1 item 4 asserted that both episodes of the deciding pair are already resolved, then contradicted itself | The first clause is deleted. The item now states that a decision **can** be taken with one episode pending (that is what the certificate and the call trigger are for), that the pair runs to its frozen end under its original coin, and that its reveal is a `monitor_update(trigger='drain')` with no second decision | protocol 9.1 item 4 |
| **m2** | "There is no cross-pair interference" overstated, against 7.4's "carry-over is allowed" | Replaced with "**No pair's record depends on a later coin** — which is what the design needs — because the coin of pair `i+1` does not exist while pair `i` runs ... **Carry-over from earlier pairs is allowed** and is absorbed into `F_{i-1}`; the protocol does not claim that pairs are independent" | protocol 7.2 |
| **m3** | "240 calls" is 240 episodes; `c_max` is the slowest **call** | "= **240 episodes** (a `self_test_repair` episode is 2 to 4 calls, so the number of calls is larger and is recorded); **`c_max` is the maximum single-call duration** over that fixed sample" | protocol 5.8 item 3 |
| **m4** | 15.2 forbids foreign commit ids while `config.json` carries `llama_cpp_commit` and two `hf_revision` values | 15.2 now exempts **three keys by name** (`llama_cpp.commit`, `servers.coder.hf_revision`, `servers.t3.hf_revision`) as upstream revision identifiers of pinned third-party sources, required to reproduce the build and the weights and containing no account or host name; **inside the event chain even these appear only as digests** (`llama_cpp_commit_sha256`). The exemption is by key, not by pattern | protocol 15.2 |
| **m5** | Enum divergence: `nm_enclosure_v3` vs `nm_guarded_v3`; `"v3"` vs `"v3-nm-guarded"` | One value each, in both documents and in the single `config.json`: **`rule_id = "nm_guarded_v3"`**, **`protocol_version = "v3-nm-guarded"`**. The protocol header states that these two strings are the only version tokens that appear in any event | protocol header, Appendix B; ARCH 6.1 |
| **m6** | `<TMP>/labsbx` vs `/private/tmp/labsbx`; `anchor.minutes: 10` introduced a time-based trigger the protocol does not have | The config carries the token **`<TMP>/labsbx`**; protocol 5.7 says `TMPDIR` is that token, which on this host resolves to `/private/tmp/labsbx`, and names that literal string once, as the one path the scanner allowlists by exact string. `anchor.minutes` is **deleted**: 12.4 item 4 states "there is no time-based anchor trigger: an idle trial produces no anchor" | protocol 5.7, 12.4 item 4, Appendix B; ARCH 6.1 |
| **m7** | `status.json` cited "protocol 12.5" | Repointed to **protocol 14.7** (12.5 is "What the anchors prove") | ARCH 2.2, 3.13 |
| **m8** | S-int scores row 11e as a tie, which is the wrong neutralization when position 2 ran **solo** | The S-int definition gains: "for a pair whose only flag is `started_after_resume` with `partner_concurrent: false`, the pair is **additionally reported as scored**, so the reader sees both the neutralized and the realized value". The builder writes both in `sensitivity.json` | protocol 6.4 (S-int); ARCH 3.15 |
| **m9** | `MonitorConfig` code defaults for non-amendable constants | `alpha_gate`, `rho`, `delta`, `n_min` and `n_max` have **no defaults**; `from_config` raises `FrozenMismatch` when `n_max` is null at run time, when it differs from `roster.n_pairs`, or when any field is absent | ARCH 3.8 |
| **m10** | `COORDINATOR_DECISIONS.md` rev 2 still records `r(92) = 0.4966` | **This session may not edit that file** (hard rule), so the correction is made where it can be: protocol 1.3 records it openly, states that **no radius in the protocol is hand-typed**, and pins the generated `radius_table.csv` as the single source checked by a freeze test; ARCH §0 repeats it. **The coordinator must still record the correction in its own file before the freeze bundle is assembled** — listed in section 6 below as an open item, because otherwise the bundle's inputs carry two values of one constant | protocol 1.3, Appendix A, Appendix C; ARCH §0, 11 PG-20 |
| **m11** | 7.5 item 4 mixes `perf_counter` (`latency_s`) and `monotonic_ns` (`ell`) in decision-defining code | 7.5 item 4 now states that both are `mach_absolute_time` on this host **and does not rely on it silently**: a preflight assertion records the two deltas over a 10 s interval and **refuses to start** (`preflight_refused(clock_equivalence)`) if they differ by more than `clock_equivalence_tolerance_ms = 1`. The key is in `config.enclosure`, in the 14.3 threshold list, in `preflight()` and in Appendix C | protocol 7.5 item 4, 14.3, Appendix A, Appendix B, Appendix C; ARCH 3.13, 6.1, 6.3 |

**Audit section 2.3 (not numbered as a finding).** The observation that enclosures only narrow within a fixed
prefix, so "the first prefix `n*`" is well defined and insensitive to which look inside the prefix fired, is
added as a paragraph to 8.9 and as ordering invariant 6b in `ARCHITECTURE_FINAL.md` §4.6.

**Audit section 7 (missing limitations).** All four are now in 1.1's "what it does not deliver" list: the
arm-asymmetric contention (M10), the execution-lock transfer (M11), the timing-based roster filter (M19)
and the absence of task disjointness across trials (M9).

---

## 4. `PROTOCOL-GAP` register: every entry resolved, with the protocol rule that resolves it

Two entries were added while making the documents agree (PG-26, PG-27). **No entry is marked "coordinator"
any more, and every resolution is a rule that now appears in `protocol_FINAL.md`.**

| id | resolution | the rule, in the protocol |
|---|---|---|
| **PG-1** | Look cadence settled as a closed trigger list | **8.3** (triggers), 7.3 item 3 (what is not a trigger), 12.3 (verifier), 12.2 #16 (`trigger` enum) |
| **PG-2** | A decision may be taken with the partner pending; the episode is drained before the switch | **9.1 item 4**, 7.5 items 1 and 5, 8.3 |
| **PG-3** | `lab_reference_rule` is a real second module, G1-owned, importing no `lab_*` module | **8.9** (the module, its imports, the shadow at every evaluation, the three injected-defect tests), 14.2 row 10, 14.3 |
| **PG-4** | `n_min` applies to the enrolled prefix, so the earliest decision is `n = 100`, not 92 | **8.3**, 1.3, 11.3 |
| **PG-5** | Harm tail is `U_h < 0` only; `U_s` is logged and never decides | **8.4** condition 1, 8.8, 12.2 #16 |
| **PG-6** | One OS process per episode, per-episode spool, no pipe | **5.1** (the whole scheduling paragraph and the spool table), 12.1 (deposit paths), 14.5 |
| **PG-7** | "An attempt began" = a fsynced `job_accepted` spool line; an assignment without one is dispatched on resume | **6.4 rows 11, 11c, 11d, 11e**, 12.3, 14.5 item 3 |
| **PG-8** | Seed partition by worker index; a duplicate is a reporting defect | **5.5**, 6.4 row 19 |
| **PG-9** | `ell = 0.0`, `tokens_known = 0` when nothing was spooled | **6.1**, 6.4 row 18, 7.5 item 4 |
| **PG-10** | `/metrics`: 5 s timeout, 3 tries, then `unreconciled`; enrollment continues | **6.4 row 20**, 13.1 |
| **PG-11** | Operational string discipline, now with form (e) for task uids | **12.2** |
| **PG-12** | The anchor process owns a spool; the orchestrator is the sole chain writer | **12.4 items 1-3** |
| **PG-13** | Program chain; `plumbing_verdict` with two condition lists; two code classes | **12.1**, 6.4 rows 22a/22b, 23, 24; 14.3, 14.4 |
| **PG-14** | The T4 canonical-payload removal list, `worker_index` included | **12.3** (the list is now in the protocol, not only in the architecture) |
| **PG-15** | `max_recovery_waits_per_call = 1`; the cap is computed from the formula, never typed; 3,354 s at `T = 180` | **5.6** |
| **PG-16** | Betting only as a post hoc read-out on final complete scores | **8.8 item 5**, 1.5 item 7, 8.7 item 6 |
| **PG-17** | `delta = 0.03` is the only value `decide` sees; the exploratory margins cannot decide | **8.8 item 1**, 8.4, Appendix B (`exploratory_margins_decide: false`) |
| **PG-18** | Enclosures are inside `[-1,1]` by construction; the clip applies to `L` and `U` | **8.2**, 7.5 |
| **PG-19** | `variance_process=n` passed explicitly | **8.2** (the verbatim code block) |
| **PG-20** | No radius is hand-typed; `radius_table.csv` is generated and is the freeze artifact | **1.3**, Appendix A, Appendix C |
| **PG-21** | `N_P = floor(n_S1/2) + floor(n_S2/2) <= 568`; `n_max` required, equal to `roster.n_pairs` | **3.3**, 3.4, 8.5 |
| **PG-22** | Task reuse is permitted and **declared as a deviation** from guidance item 6 | **10.3**, 3.5 item 5, 13.1, 1.1 |
| **PG-23** | The orphan check matches the durable `job_accepted`, not `episode_started` | **12.3**, 14.5 item 3 |
| **PG-24** | The ten-failure abort counts in reveal order | **6.4** (automatic aborts), Appendix B |
| **PG-25** | The integrity label covers both phases for terminal failures and torn regions; coin adjacency is randomized-phase only | **12.6** (label rule) |
| **PG-26** *(new)* | The working location is settled: the shared clone stays (C15), with the identity assertion and the 60-second worktree check | **2.1**, 6.4 row 27, 12.4 item 2, 14.1 item 1, Appendix F |
| **PG-27** *(new)* | One name per event type across both documents | **12.2** (trial table and the new program-chain table): `deposit_sealed`, `server_stopped`, `publication_withheld`, `erratum`, `decision_code_defect`, `plumbing_verdict`, `preflight_refused` (before seq 0) vs `invocation_refused` (later invocation) |

---

## 5. Consistency repairs the audit did not list, made because the two documents are jointly binding

These were found while checking that every event type, configuration key, module name and failure row
agrees. Each is a case where the two documents said different things; none changes a decision rule.

| # | divergence | resolution |
|---|---|---|
| 1 | **`config.json` had two different shapes** (protocol Appendix B's `rule` block vs the architecture's `monitor` block, different key names, different nesting) | One canonical block, **byte-identical** in protocol Appendix B and `ARCHITECTURE_FINAL.md` §6.1, verified programmatically; a freeze test compares the two blocks after stripping the fences. The rule-block key list is stated identically in both (it now also covers `tie_rule`, `enclosure`, `roster.pairing`, `roster.n_pairs_rule` and `plumbing_fail_conditions`) |
| 2 | **Two genesis rules** (`live_ab/program-v3\|bundle` for the program chain vs one domain with a `chain_id` suffix) | One rule: `SHA256("live_ab/eventlog-v3\|" + x + "\|" + chain_id)`, with `x` = the freeze-bundle hash for the program and trial chains and the literal `prefreeze` for the pre-freeze chain, which is written before the bundle exists |
| 3 | **Program chain path and first event** (`_program/program_chain.jsonl` vs `_program/events/seg_<k>.jsonl`) | The segmented path, with `program_opened` as seq 0 carrying the closed `_prefreeze` head |
| 4 | **Spool naming** (`spools/worker_<w>_<inv>.jsonl` vs `spools/ep_<arrival>_<attempt>.jsonl`) and spool line names (`llm_request` vs `call_started`) | Per-episode spools `ep_<arrival>_<attempt>.jsonl`; the protocol's 5.1 table now has two columns, the spool kind and the chain event it becomes |
| 5 | **Event types missing from one side**: `publication_withheld`, `server_stopped`, `deposit_sealed` (`archive_sealed`), `erratum`, `decision_code_defect`, `plumbing_verdict`, `program_opened`/`program_closed` | All present in both, with bodies; the protocol gains a program-chain event table (P1-P12) that mirrors `ARCHITECTURE_FINAL.md` §4.3 |
| 6 | **Module list** (`lab_program_chain` and `lab_scan` existed only in the protocol) | The protocol's Appendix C list is now the architecture's module set name for name: the program chain is `lab_eventlog` with `chain_id = "_program"`, and the scanner is `lab_anchor.scan_for_identifiers` |
| 7 | **`monitor.csv` / `monitor_table.csv` columns** | Both now carry the trigger and the shadow-mismatch flag; the builder also writes `sensitivity.json` (S-infra, S-int with the row-11e variant, S-lock) |
| 8 | **`rho` sensitivity table and the minimum-observed table still quoted `n = 569`** | Recomputed at `n = 568` (0.1595 / 0.1561 / 0.1580 / 0.1737 / 0.2270; minimum `Dbar` +0.1280) |

---

## 6. What was deliberately **not** added, and what is left for the parent session

1. **No dedicated git worktree.** The audit's preferred B7 fix would reopen coordinator decision C15. The
   text closes the risk instead (PG-26). If the coordinator prefers the worktree, that is a coordinator
   decision, not an editor's.
2. **No correction inside `COORDINATOR_DECISIONS.md`** (`r(92) = 0.4966`, m10). This session may not edit
   existing files. **Open item for the coordinator:** record the corrected `r(92) = 0.495026` — or, better,
   simply cite the generated `radius_table.csv` — before the freeze bundle is assembled, otherwise the
   bundle's inputs carry two values of one constant. No conclusion depends on it (`n_min = 100` binds).
3. **No new external dependency** of any kind: no timestamp authority, no thermal probe, no second clone.
4. **No re-run of the extended replay (11.5).** The audit's item 9 is right that every cell assumed the
   two-tier 0.05 kernel; that is now the only kernel, so the specification is consistent — but the replay
   itself is a **pre-freeze deliverable** and is listed below, not performed here (no model calls, and the
   cells depend on the realized `N_P`).
5. **No change to any decision rule, margin, level, horizon or trial order.**

---

## 7. Facts still to be pinned in the pre-freeze phase, each with the rule that determines it

Every value below is `null` in the frozen `config.json` or blank in the freeze bundle until the rule named
beside it produces it; **none is a judgement call, and no design-task outcome enters any of them.** The
derivation file records each value next to its rule and its recorded inputs, and `build_freeze_bundle`
raises `FreezeIncomplete` if any is still `null` or `"unknown"`.

| fact | rule that determines it | where |
|---|---|---|
| `n_S1`, `n_S2`, `n_total`, and therefore **`N_P` = `floor(n_S1/2) + floor(n_S2/2)`** (≤ 568) | the four prospective exclusions of 3.2 applied to the verified `mbpp.jsonl`, then the arithmetic of 3.3 | protocol 3.2, 3.3; `roster.n_pairs` |
| `monitor.n_max` | set equal to `roster.n_pairs` at freeze time; required field, no default; a mismatch raises `FrozenMismatch` | protocol 8.5; ARCH 3.8 |
| `roster_sha256`, `task_content_sha256`, the four `arrival_order_T<e>.json` hashes | `lab_data.build_roster` and `lab_design.arrival_order` on the frozen sources | protocol 3.1-3.4 |
| the number of tasks excluded by rule 3.2 item 4 and their reference verification times | the reference sweep **under the trial load regime** of 5.8 item 5 | protocol 3.5 item 7, 16 item 9 |
| whether **T3 runs at all** | the six preflight rules of 2.4, all evaluated from preflight facts only; failure ⇒ deferral, and the 0.0125 is **not** re-allocated | protocol 2.4, 8.5 |
| recomputed SHA-256 of both GGUF files | recomputation at preflight; the values in 2.3 are expectations, not facts | protocol 2.3 |
| `serving_manifest_sha256` and every manifest field | the pinned-commit build of 2.2, with `git status --porcelain` empty | protocol 2.2 |
| `c_max`, hence `request_timeout_s`, hence **`episode_hard_cap_s`** | the fixed calibration plan of 5.8 item 3 (240 episodes; `c_max` = the maximum single-call duration) and the formulas of 5.6; **the cap is computed from the formula, never typed** | protocol 5.6, 5.8 |
| the golden `/props` and `generation_settings` objects and the receipt **mask list** | the smoke capture of 13.2, which must then pass on **100%** of the dress-rehearsal responses | protocol 5.8 item 1, 13.2 |
| the accounting wording for abandoned requests | the **non-streamed** counter test on the production path, 5.8 item 2 | protocol 13.1 |
| the exact `/metrics` start identity, or the fallback wording "residual reported" | the rehearsal of 5.8 item 6 | protocol 6.4 row 20, 13.1 |
| the side-by-side compression **`C`, one per contrast** (T1, T2, T3, T4) | the solo-vs-side-by-side calibration of 5.8 item 4, on out-of-design prompts only | protocol 6.2, 16 item 6 |
| Seatbelt `profile_sha256` and the containment-probe results | 5.7 item 3, with two workers running; any new success stops the freeze | protocol 5.7 |
| `posting_latency_p95_s` (the second term of the sandwich tolerance) | the anchor drill of 12.4 item 10 against the real remote | protocol 12.6 item 4 |
| the measured `perf_counter` / `monotonic` difference over 10 s | the preflight assertion of 7.5 item 4; refusal above `clock_equivalence_tolerance_ms = 1` | protocol 7.5 item 4 |
| vendor-published pass rates used for criterion (vi), with sources | 2.4, recorded literally and labelled outcome-informed at the aggregate level | protocol 2.4 |
| the **extended-replay table** (script, seed, output hash; every cell deposited) | 11.5, mandatory before the freeze, on the realized `N_P` and roster; it cannot change any parameter | protocol 11.5, 14.2 row 12 |
| the generated `radius_table.csv` | `dryrun_live_ab.py --radius-table` against `src/winstats.py`; every radius in the protocol is checked against it | protocol 1.3, Appendix C |
| licence-evidence hashes for both models and both datasets | 2.3 and 3.1 | protocol 2.3, 3.1 |
| `monitor.reference_rule_sha256`, `harness_file_sha256`, `rule_block_sha256`, `config_sha256` | computed at freeze assembly; `rule_block_sha256` is **compared with the rule-block hash computed from the protocol's own frozen tables** and the freeze fails on a difference | protocol 14.1 items 6-7, 14.2, Appendix C |
| the run book (14.7), the derivation-file template (Appendix A) and the narrowed constant-coverage test | listed as freeze conditions; the freeze cannot proceed without them | protocol Appendix C |

---

## 8. Verification performed on the two output files

* The `config.json` blocks of protocol Appendix B and `ARCHITECTURE_FINAL.md` §6.1 are **byte-identical**
  (checked programmatically) and the block parses as JSON: 33 top-level keys, two hierarchy tiers at
  tolerances 0.0 and 0.05, `enclosure.certificate_constant = 0.95`, `seed_rule.mask = "0x7FFFFFFE"` with
  `low_bit = "worker_index"`, `--slot-prompt-similarity` present in `llama_args`, `monitor.n_max = null`,
  `anchor.blocking` of 14 entries and `push_triggers` = that list plus `every_25_completed_pairs`.
* **Event types**: the type columns of the protocol's trial and program-chain tables and of
  `ARCHITECTURE_FINAL.md` §4.3/§4.4 contain the same 46 names; neither document has one the other lacks.
* **Module names**: the `lab_*` set of protocol Appendix C equals the set of `ARCHITECTURE_FINAL.md` §2.1
  and §3 (17 modules); `lab_program_chain` and `lab_scan` are gone from the protocol, `lab_reference_rule`
  is in both.
* **Failure rows**: every `6.4 row N` referenced anywhere in `ARCHITECTURE_FINAL.md` (10, 12, 17, 21, 22a,
  22b, 23, 24, 27) exists in the protocol's 6.4 table, which now runs 1-27 with 22 split; no reference to
  the old undivided row 22 survives in either file.
* **Stale tokens**: no occurrence of `thermal`, `archive_sealed`, `protocol_draft_v2`, `n_tiers`,
  `0x7FFFFFFF` (as the seed mask), `program_chain.jsonl`, "guaranteed abstention" or "unreachable by
  construction" remains in either file except where a sentence explicitly records the correction; `569`
  appears only as a labelled reference row, in the audit-history note and in the beacon arithmetic.

*Prepared and checked by an AI agent session; not human peer review or author sign-off.*
