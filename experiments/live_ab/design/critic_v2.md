# Completeness critique of `protocol_draft_v2.md` (live_ab)

Critic: session 60 completeness critic, 2026-09-19.
Read in full: `protocol_draft_v2.md` (1,135 lines, SHA-256 prefix `ffd6791e5e8dc94f`), `audit_response_v1.md`, `audit_v1_statistics.md`, `audit_v1_provenance.md`, `audit_v1_claims.md`, `R2_constraints_checklist.md`. Consulted read-only: `src/winstats.py` (SHA-256 `56955ce0...`, equal to `origin/main`), `experiments/local_stream/{sandbox,verify,agent}.py`, `experiments/build_open_coding_results.py:135-150`, `paper/open_coding_appendix.tex:75-106`, `paper/theory.tex:183-187`, `EXPERIMENT_QUEUE.md:37` at `origin/main` (`955579d`), `_llama_server_help.txt`, `P6_v2_planning.md`. No git state change, no server, no LLM or API call, no download, nothing written outside `live_ab_design/`. One CPU check (< 2 s) with `.venv/bin/python` and `src/winstats.py`; its numbers are quoted in sections 1.1 and 2.

## Verdict: NEEDS-ANOTHER-ROUND (short, targeted; no redesign)

Every BLOCKER and MAJOR of the three audits has a real text change in v2; none is "claimed only" in the response table. The statistical rule (section 8) is complete and numeric, and I could not construct a counterexample against 8.5. v2 can nevertheless not be posted as the root issue or frozen yet, for three reasons:

1. The defect path that lifted three BLOCKERs (S-F1, C-F2, P14) is **executable only inside a running trial**. Between trials there is no chain in which a `refreeze_authorization`, an `invocation_refused` or a "not started" statement can live (N1), no rule says what happens when the plumbing verifier FAILS after T4 (N2), and verifier and builder are frozen for ever with no defect path although the builder runs on real data for the first time after the last trial (N3). These are exactly the "post-freeze improvisation" pattern of Rounds 11 to 12.
2. Four failure modes have no outcome (N4 to N6, N9): a binding coin whose attempt never started, an undefined `latency_s` when no request was spooled, a seed collision between two uncoordinated workers, a failed or hanging `/metrics` scrape at a pair boundary.
3. Two irreversible auto-aborts hang on server behaviour that the pre-freeze phase, as written, does not exercise on the production path (N7, N8, N14), and T4-first cannot find any `self_test_repair` plumbing defect, so the first real end-to-end `self_test_repair` run under the full harness is the claim-bearing T2.

All of this is repairable by text (about fifteen edits, listed in section 7) and one added pre-freeze step. Harness modules that none of the open items touch (`lab_eventlog`, `lab_coin`, `lab_reference_rule`, `lab_client` spool, `lab_mock_server`, the unit tests for chain, coin, betting capital, monitor) can be implemented now, in parallel with the v2.1 text round.

Counts: 7 BLOCKER and 40 MAJOR findings checked. 35 are resolved in the text (R or R+); 7 are resolved in the text with a pre-freeze fact or an approval pending (RP); 5 are PARTIAL (S-F1, C-F2 and P14 through N1 to N3; C-F8 through N10; C-F12 through N14). 22 new findings (N1 to N22): 8 HIGH, 10 MEDIUM, 4 LOW.

---

## 1. Finding-by-finding verification (BLOCKER and MAJOR only)

Status codes. R = resolved in the v2 text. R+ = resolved, and v2 is stricter than the auditor asked. RP = resolved in text, a fact is pending in the pre-freeze phase or an approval (named). PARTIAL = text exists, but a residual named N-k keeps the finding open.

### 1.1 Statistics audit

| id | sev | where in v2 (checked passage) | status | residual |
|---|---|---|---|---|
| S-F1 | BLOCKER | 12.1 item 7 ("immutable for every trial, including the trials that have not started"); 12.2 (closed list, relabelling rule, T4b); 12.4 ("Each trial starts when the previous one has ended"); 12.1 step 3 ("Answers that arrive after the cut-off ... change nothing"); 3.4 item 3 | PARTIAL | N1, N2, N3: the between-trial mechanics are missing |
| S-F2 | BLOCKER | 9.2 (reference rule "can **never** be amended"; first crossing `n*`; `LIVE_DECISION_INVALID`; decision on resume); 6.4 row 17; 12.2 item 3 | R | N3 (defect in the reference rule itself unmapped), N18, N19 |
| S-F3 | MAJOR | 5.5 (`max_attempts` 1); 6.4 rows 10, 10b, 11, 11b; D15, D19; 6.1 last paragraph | R+ | N4, N17 |
| S-F4 | MAJOR | 12.1 item 7; 12.2 first sentence; 6.4 "Automatic, deterministic aborts"; 11.4 item 5; 12.5 | R | N16 (label and abort thresholds are outside the non-amendable list) |
| S-F5 | MAJOR | 7.2 (`F_0` rewritten); 7.4 ("pair-level analogue with a modified assumption"; `nu_i` definition); 9.1; 3.5 | R | none |
| S-F6 | MAJOR | 5.8 item 4; 6.2 "T3, stated before any data" (i) to (v); 8.3 label suffix; 1.4 item 8 | R | N21 (compression statistic not defined) |
| S-F7 | MAJOR | 8.4 table and first bullet; 1.2; 1.3 claim 9; 1.4 item 20 | R+ | none |
| S-F8 | MAJOR | 8.9; 9.3 first paragraph; 10.3 "Secondary bands under A"; RA1 in 12.1 | R | none (radius values re-computed: `r(280, .0125)` = 0.2212, `r(565, .0125)` = 0.1490) |
| S-F9 | MAJOR | 3.3 ("No rule parameter depends on the roster"); 8.1 (`delta = 0.10`); 10.4 | R | the rejected part (a rationale without power) is argued honestly; consequence under B is stated (T1 expected to abstain) |
| S-F10 | MAJOR | 9.4 items 1 to 4; 1.4 item 10 | R | none |
| S-F11 | MAJOR | 1.1 "does **not** deliver"; 1.3 claim 5; 8.6; 1.4 item 18; RB1 | R | none |
| S-F12 | MAJOR | D9; 8.3 "Status with respect to the root"; 12.1 step 3 Block I | R | N11 |

### 1.2 Provenance audit

| id | sev | where in v2 | status | residual |
|---|---|---|---|---|
| P1 | BLOCKER | 11.4 "Proves / Does not prove", mechanics 1 to 9; 4.2 invariant (iv); 11.6 item 4; 4.3 | R+ (a to f); (g) = C17 pending | N13 (who writes anchor events; "or" in item 2), N21 (TSA failure unmapped) |
| P2 | BLOCKER | 5.5; 6.4 rows 10 to 11b; 12.3 step 3; 11.2 #14 | R+ (option d) | N4, N15, N17 |
| P3 | MAJOR | 1.3 claim 1; 4.2 (no `raw_hex`); 4.3 "What (d) proves"; 11.6 items 1, 2, 5, 6; C18 | R | N4: the pair behind a coin-adjacent boundary has no outcome rule |
| P4 | MAJOR | 4.2 (v); 11.3 torn region and unopenable chain; Appendix C kill points | R | N1 ("closing stub" has no definition) |
| P5 | MAJOR | 12.3 steps 3 to 6; 9.2 third bullet; 11.3 invariants | R | N4 |
| P6 | MAJOR | 9.2; 12.2 item 2; 11.2 #2 and #21 | R | N3 |
| P7 | MAJOR | 5.1 spool; 12.3 step 3 orphan checks; 11.2 #15 | R | N21 (`episode_started` is non-durable but the orphan check matches against it) |
| P8 | MAJOR | 11.5 second paragraph; 5.2; D34 | R | N9 |
| P9 | MAJOR | 5.7; 2.3 identity checks; 5.2 first-start comparison; claim 6 wording | RP (golden objects pre-freeze) | N7 |
| P10 | MAJOR | 2.2 items 1 to 3; 2.1 `<LLAMA_BUILD>` | RP (build pre-freeze) | none |
| P11 | MAJOR | 5.6 items 1 to 4 | R+ | none. I checked the reviser's open doubt (response section 6, last bullet): `agent.py:32` and `verify.py:21` both use `from sandbox import run_program`, and `run_program` creates and removes its `p_*` directory inside the call (`sandbox.py:154-190`), so wrapping `sandbox.run_program` before importing `agent` and `verify` does put program creation, execution and deletion under the lock. |
| P12 | MAJOR | 5.4; 4.4; D18 | R | N6 |
| P13 | MAJOR | 12.1 step 5; 5.8 last paragraph | R | N9 ("must equal ... exactly" has no consequence) |
| P14 | MAJOR | 12.2; 11.2 #1 (link to previous trial) | PARTIAL | N1 |
| P15 | MAJOR | 4.5; 6.4 `infra_flag` closed list | R | none |
| P16 | MAJOR | 11.7; 11.2 #14, #26; 11.4 items 6 to 8 | RP (C17, C19, C20) | none |
| P17 | MAJOR | 11.1 segments; 11.4 item 5 | R | N12 |
| P18 | MAJOR | 11.3 verifier list; 9.2 import isolation; Appendix C | R | N3 |
| P19 | MAJOR | 12.4 decision table; 11.2 #23, #27 | R | N2, N21 (thermal probe undefined) |

### 1.3 Claims audit

| id | sev | where in v2 | status | residual |
|---|---|---|---|---|
| C-F1 | BLOCKER | D29; 11.1; 11.2 preamble; 11.4 items 2, 5, 9; 13.2 | RP (drill needs C10) | N12: the validator rule contradicts `trial_started` |
| C-F2 | BLOCKER | 12.1; 12.2; 12.4 inspection list; 3.4 item 3; claim 2 suffix | PARTIAL | N1, N2, N3, N8 |
| C-F3 | BLOCKER | section 8 (A and B complete); 12.1 step 3; Appendix B | R | N11 |
| C-F4 | MAJOR | 1.1 (full quote verified against `origin/main:EXPERIMENT_QUEUE.md:37`); Appendix E | R | none |
| C-F5 | MAJOR | 9.4; 1.3 claims 3, 4; 1.4 item 10 | R | none |
| C-F6 | MAJOR | 8.3 labels; 10.4; 3.5 "Dilution, disclosed"; 1.4 item 19 | R | N20 (10.3 uses "guarded" without the margin) |
| C-F7 | MAJOR | grep: "not certifiable", "cannot be certified", "impossible" occur only in 1.4 item 13 | R | none |
| C-F8 | MAJOR | 10.1 to 10.5; C12 | PARTIAL | N10: the numbers the root will read are still the latent-variable model the finding criticised |
| C-F9 | MAJOR | 2.4; 5.8; 6.2; RB4 | RP (repository, file, pass-rate sources; C15) | none |
| C-F10 | MAJOR | 3.2 rule; 3.4 items 2, 3, 5 | R | none |
| C-F11 | MAJOR | 5.5; 6.4 | R+ | N15 |
| C-F12 | MAJOR | 5.8 item 2; 11.5 third paragraph; 5.7 last paragraph | PARTIAL | N14: the test does not exercise the production path |
| C-F13 | MAJOR | 2.2; 13.1 `env_lock.txt` | RP | none |
| C-F14 | MAJOR | header; 11.4 items 6, 7; C10 fallback text | RP (C17, C19) | none |
| C-F15 | MAJOR | 2.1; 11.4 item 1; D30 | R | none |
| C-F16 | MAJOR | 12.4 table; 12.5; header | R | N2 |

Conflicts between auditors (response section 1): all ten were decided for the stricter option and the decision is visible in the text. One of these creates a new exposure that the text discloses but does not close (N17).

---

## 2. Is every parameter of the monitoring rule numeric? Yes, with four rule-derived exceptions

| parameter | value in v2 | where | verdict |
|---|---|---|---|
| A: stake grid | `geomspace(1e-4, 0.99/(1 + c), 40)`, equal weights, `bets = 40` | 8.1, App. B | numeric; equals `winstats.betting_log_e_ternary` |
| A: levels T1, T2, T4 | (0.0025, 0.02, 0.0025); thresholds 400, 50, 400 | 8.4 | numeric; sums to 0.025 |
| A: levels T3 | 0.05/3 each; threshold 60 | 8.4, App. B (`0.016666666666666666`) | numeric |
| A: comparison | `loge >= numpy.log(1.0/alpha_j)` in float64 | 8.1 | exact |
| B: radius | `normal_mixture_radius(n, alpha=a, rho=100.)`, `V_n = n`, no intersection | 8.1 | numeric; `rho = 100`, `V_n = n` verified against the root's retained analysis (`build_open_coding_results.py:143`, `open_coding_appendix.tex:91-95`) |
| B: levels | (0.0125, 0.0125) T1, T2, T4; (0.025, 0.025) T3; strict inequalities | 8.3, 8.4 | numeric |
| margin, `n_min`, looks, retention | 0.10; 20; every completed pair; none | 8.1, 8.2 | numeric |
| hierarchy | success tol 0; latency rel. 0.10; tokens rel. 0.10 (T3: two tiers) | 6.2 | numeric |
| enclosure certificate | `0.9 * ell > L_r + 1e-9` | 7.6 | numeric |
| agreement tolerance | exact counts and decision; 1e-9 for log E and endpoints | 9.2 | numeric (see N18) |
| secondary family (A) | B's levels per trial | 8.9, App. B | numeric |
| side read-outs | 0.03, 0.05, 0.15; S1-restricted; success-only | 8.10 | numeric; the level used for "did / did not cross at 0.03" is not stated (presumably `alpha_S`; say so) |
| `N_P` | rule: 295 + floor(`n_S2`/2), at most 565 | 3.6 | rule-derived, pre-freeze; acceptable |
| `request_timeout_s`, `episode_hard_cap_s` | rules in 5.5 | 5.5 | rule-derived; see N15 and N21 (size of the calibration not fixed) |
| receipt mask list | "any field that the smoke test shows to vary" | 5.7 | rule-derived; see N7 |
| sandwich tolerance | "30 s plus the measured posting latency" | 11.6 | second term undefined; LOW |

Consequences computed with `winstats` (context for the coordinator, not defects): under A the NB gate at 0.0025 cannot cross before pair 14 and the S gate with all ties cannot cross before pair 70; under B no decision is possible before pair 35, and with an observed success difference of 0 the S band clears `-0.10` only from pair 1,228, so on at most 565 pairs a B deploy needs an observed difference above about +0.05. This agrees with 10.3 (B: 0.06 or less).

---

## 3. Is every failure mode mapped to an outcome? No: six gaps

Mapped and checked: request timeout, HTTP error, malformed body, truncation, server crash, changed server identity, sandbox kill, missing sentinel, empty code, worker death, hard cap, orchestrator crash, operator stop, receipt or alias mismatch, clock anomaly, disk full, memory pressure, live-monitor exception, blocking anchor unavailable, scanner hit, torn tail, unopenable chain, live/reference disagreement, ten consecutive infrastructure failures, T3 preflight failure, download mismatch.

Not mapped (details in section 4): binding coin with no attempt started, and position 1 started while position 2 was never dispatched (N4); no spooled request, so `ell` and `latency_s` are undefined (N5); seed collision (N6); `/metrics` scrape fails, hangs or violates the start identity (N9); plumbing verifier FAIL between trials, preflight refusal before seq 0, defect in verifier, builder or reference rule (N1 to N3); timestamp-authority failure, `anchor_failed(tree_state)` on a blocking anchor, OS build change between trials (N21).

---

## 4. Unresolved and new findings, with the exact passages

### HIGH

**N1. Between trials there is no chain: the defect path that resolved S-F1, C-F2 and P14 cannot be executed where it is most likely needed.**
Passages. 11.2 #1: "`trial_started` (seq 0) ... list of harness-only re-freezes in force". 12.2 item 2: "A `refreeze_authorization` event names each changed file ... It is followed by a blocking anchor; the diff is committed with it. The runner's drift check accepts exactly the chained authorizations and nothing else." 11.2 #27: `trial_ended` carries the "final head", and #1 says the next `trial_started` carries "the previous trial's final head". 11.3: an unopenable chain is closed "by an externally receipted statement in the program's chain of the next trial (or of a closing stub)". 11.2 #2 lists `invocation_refused`. 12.4: "A trial that is not started is reported under its own heading."
Why it fails. The stated purpose of T4-first is a repair between T4 and T2. At that moment T4's chain is closed (any further event would change the "final head" that T2 must quote) and T2's chain does not exist (its seq 0 must already list the re-freeze "in force"). The `refreeze_authorization`, its blocking anchor and its `what_was_known` therefore have no chain to be appended to, and "accepts exactly the chained authorizations" has no referent. The same holds for an `invocation_refused` before seq 0 (weights hash mismatch, port busy, API-key variable present), for a trial that is never started, and for the "closing stub", which is named once and never defined. An operator will improvise, which is the Round 11 to 12 amendment finding.
Required change. A **program chain** `results/live_ab/_program/`: genesis from the freeze bundle hash, first event = head of the closed `_prefreeze` chain; it receives `trial_opened` / `trial_closed` (with the trial's final head and end-receipt id), every `refreeze_authorization`, every preflight refusal, every "not started" and "chain unreadable" statement, each with harness-computed `what_was_known` and a blocking receipt. `trial_started` quotes the program-chain head instead of (or in addition to) the previous trial's head. One verifier check: the program chain orders the four trials and contains every authorization that any `invocation_started` relied on.

**N2. No rule for a plumbing-verifier FAIL between trials.**
Passages. 12.4: "Each trial starts when the previous one has ended; the only admissible reasons for not starting a trial are the operational reason codes below (none refers to an outcome)"; "After each trial the verifier runs in plumbing mode and outputs only: chain and completeness checks, agreement flag ...". The decision table has the codes `power`/`thermal`, `disk`, `server_unrecoverable`, `anchor_unavailable`, `monitor_exception`, `planned`, `operator_discretion`.
Why it fails. If the T4 plumbing report shows a failed completeness check or a reconciliation defect, the text obliges the operator either to start T2 at once (unconditional execution) or to log `operator_discretion`. Neither is the intended "repair through 12.2". Whether a given plumbing result stops the program is decided after outcomes exist, by someone who can read them.
Required change. Add reason code `plumbing_fail` with a machine-checkable condition (closed list: chain or completeness FAIL, reference-rule disagreement, receipt mismatch count above 0, `reconciliation_defect` count above 0, T4 payload non-identity) and the single action "program paused in the program chain; harness-only re-freeze; next trial". State which plumbing results do **not** stop the program (for example integrity label, terminal-failure counts).

**N3. Verifier, builder and reference rule can never change, and nothing says what happens when one of them is defective.**
Passages. 12.2 item 1: "Closed list of files that may **not** change: `lab_coin`, `lab_reference_rule`, the verifier, the builder, the scoring path, the failure rules, the seed rule, the config, ...". 13.1: the builder "is part of the freeze bundle and is run only after the last trial". 9.2: the reference rule "can **never** be amended".
Why it fails. The builder meets real data for the first time when nothing may change any more; the verifier has about twenty checks written by the same session. A false FAIL of the verifier (for example a legal multi-line torn region, or a gap above 5 s caused by a 10 s sandbox run, which 11.6 item 4 would list because only open `llm_request`s cover gaps) or a crash of the builder has no regulated exit; the only available act is an unregulated edit after all outcomes are known. For the reference rule the consequence of a proven defect is also unwritten.
Required change. Split the closed list. (i) **Decision-defining code** (`lab_coin`, `lab_reference_rule`, scoring path, failure rules, seed rule, config): immutable; a proven defect of the reference rule means claims 2 to 5 are dropped for every affected trial and a corrected rule is descriptive only. (ii) **Reporting code** (verifier, builder): versioned erratum through the program chain (old hash, new hash, diff hash, `what_was_known` = everything), both outputs deposited, and the frozen constraint that the list and definitions of tables (section 14) cannot change and that no erratum can alter a decision, because decisions come from (i).

**N4. A binding coin whose attempt never started has no outcome; the natural reading is a cost-free steering device.**
Passages. 6.4 row 11: "An open attempt whose worker spool holds a complete terminal line ... is revealed from it ...; **every other open attempt is revealed as `success = 0`, `error_class = interrupted`**". 12.3 step 3: "For every assignment event of either kind ... without its reveals: an open attempt is revealed from its spool's terminal line **only if** ...; otherwise ... the attempt is revealed as `interrupted`". 5.1: "send position 1 to worker 0 and position 2 to worker 1 (in that order, without waiting in between)". 11.2 #10: `episode_started` is not durable. 11.6 item 1 only labels the boundary "coin-adjacent".
Why it fails. "Open attempt" is undefined when the crash falls between `coin_drawn` and the first dispatch, or between the two dispatches. If such arrivals are revealed as `interrupted`, the pair becomes a tie in both scores (or a forced loss of the arm that had started). The operator of 4.3 ("kills the process after reading a coin and before dispatch") then converts any disliked pair into `D = 0`, and a tie multiplies the S-gate wealth at threshold `-0.10` by `1 + 0.1 * lambda`, so the device pushes the one uncertain gate toward a crossing; it costs no measurable time and two such pairs stay below the label threshold of D35. If they are instead executed on resume, the text contradicts "Nothing is re-run" only in appearance (nothing had run), but the rule is not written.
Required change. Define "attempt started" by evidence the worker owns: a fsynced `job_accepted` spool line (arrival, arm, pid, invocation) before `run_episode`. Rule: an assigned arrival without `job_accepted` is dispatched on resume as its one and only attempt, flagged `started_after_resume`, with `partner_concurrent` recorded (this re-creates the solo-run regime that the response to S-F21 says no longer exists; add it to S-int). An arrival with `job_accepted` follows row 11. Add both kill points to Appendix C, and make the orphan check of 12.3 match against `job_accepted` instead of the non-durable `episode_started`.

**N7. Two irreversible auto-aborts depend on server behaviour that the pre-freeze phase does not exercise as the trial will.**
Passages. 5.7: "**any unknown or missing key is a mismatch**"; "`timings.cache_n == 0` and `tokens_cached == 0` are asserted on every response". 6.4 row 12: "the episode completes and is revealed; then `trial_aborted(receipt_mismatch)` before the next dispatch". 12.4: "An aborted trial is reported, never restarted". 2.2 launch line: no server-side cache switch. `_llama_server_help.txt:590`: "`--cache-prompt, --no-cache-prompt` ... (default: enabled)"; `:426`: "`-cram, --cache-ram N` ... (default: 8192 ...)".
Why it fails. `self_test_repair` sends up to four calls that share a long prefix (system prompt, task, earlier code) to the same slot; that is the situation in which a prompt cache answers. `cache_prompt: false` is a request field that the server does not echo, and the host-memory cache is on by default. If any response of T2 or T1 reports `cache_n > 0`, or if `generation_settings` holds a field that varies with message count or slot and was not seen in ten smoke prompts, the trial is lost for ever. The mask list is fixed from the smoke test, and nothing requires that the frozen comparison passed on every pre-freeze response.
Required change. (i) Make cache deactivation structural: add `--no-cache-prompt` and `--cache-ram 0` (and `--slot-prompt-similarity 0.0` if the golden `/props` shows it matters) to the frozen launch line and check them in the golden `/props`. (ii) Pre-freeze acceptance criterion, written into 5.8: the frozen comparison (golden object, mask list, `cache_n`, alias, seed) must pass on 100% of the responses of the real-server rehearsal of N8, which must include complete `self_test_repair` episodes with repair rounds on both slots and two consecutive episodes with an identical prefix on the same slot; otherwise no freeze.

**N8. T4-first cannot find `self_test_repair` plumbing defects, and the only end-to-end rehearsal is against the mock server.**
Passages. 12.4: "T4 first, so that a plumbing defect is found where it costs no claim". 1.2: T4 "cannot reveal any arm-dependent defect (retry, timeout, routing)". 5.8 item 6: "end-to-end rehearsal of orchestrator, spools, anchor process and verifier **against the mock server**". 5.8 item 3 calibrates durations on the real server, without saying that it runs through orchestrator, monitor, spools and anchors.
Why it fails. Multi-call episodes, in-episode sandbox runs under the execution lock, lock waits inside `latency_s`, repair prompts, the receipt comparison on repair calls and the 4.5-fold duration asymmetry inside a pair all occur for the first time in T2, a claim-bearing trial, under a harness whose scoring path may no longer be touched.
Required change. Add to 5.8 a **real-server dress rehearsal on out-of-design tasks only** (the six smoke tasks, reused as often as needed; chain under `_prefreeze`, tagged `phase = REHEARSAL`): full orchestrator, both workflows in both orientations, pair-synchronous scheduling, real anchors on the drill branch, a rehearsal-only config with a small `n_min` and a wide margin so that a decision, the blocking decision receipt, the switch and a post-decision phase occur, one injected orchestrator kill and one worker kill, then verifier PASS and a builder run. Its success outcomes stay unused (the rule of 5.8 already says so).

**N10. C-F8 is only partially closed: the numbers the root will read in RA1 are still the latent-variable model, and "R4's simulator" cannot do what 10.5 asks of it.**
Passages. 10.5: "**R4's simulator** (not P5 or P6) is re-run for the exact configuration that will be frozen (A or B) ... with S2 success cells {0.25, 0.45, 0.60}, a fresh-run variability extension with w cells". 10.1 item 1: R4 is a "plug-in replay ... outcome of a task under an arm = its single pilot outcome ... unstratified". 12.1 step 3: RA1 is asked "knowing that in the planning simulation the secondary normal-mixture bands disagreed with every betting deploy".
Why it fails. R4's replay has no outcome for S2 tasks, no w and no strata; with those extensions it is a new simulator that nobody has specified. And the order of 12.1 (consultation in step 3, re-run in step 4) means the root answers on P6, whose model (Beta fit over two different workflows, uncalibrated w, assumed A/A tie share 0.08) is what C-F8 item 2 objected to. Both configurations are fully specified now and the work is CPU-only.
Required change. Specify the extended replay in half a page (S1 tasks: pilot outcome with probability w, otherwise a fresh Bernoulli draw from the task's stratum rate; S2 tasks: Bernoulli at the cell rate; latency and token tiers resampled from pilot both-succeed pairs; strata of A and of B) and run it **for A and for B before the issue is posted**, at 565, 495 and 295 pairs. Put its table into the issue. After the cut-off only the realized `N_P` is re-run.

**N11. The protocol hash the root is consulted on is not the hash that is frozen.**
Passages. 12.1 step 3: the issue "is posted with this protocol's hash". 10.5: the re-run table "replaces 10.3 in the frozen protocol". Appendix D lists about fifteen values that are filled in after the consultation.
Why it fails. A literal "yes" refers to bytes that will change. Nothing states which parts may differ between the consulted and the frozen text, so "the root confirmed configuration A" is open to the objection that it confirmed another document.
Required change. Define a **rule block** (sections 6.2 to 6.4, 7, 8, 9.2, Appendix B `configurations` and the statistical keys of `common`) with its own SHA-256; the issue quotes that hash; the freeze record shows that the rule-block hash is unchanged and lists every other difference as a diff. Also state that if `src/winstats.py` on root main no longer has SHA-256 `56955ce0...` when the branch is cut, the consultation is repeated.

### MEDIUM

**N5. `latency_s` is undefined when nothing was spooled.** 7.6: "`ell = max_e (t_e - t_c1)`, where `t_c1` is the worker's monotonic time at entry into the first `chat()` call". 6.3: "All values are finite by construction (6.4), as `compare` requires." A worker that dies before its first request has no `t_c1` and no `t_e`; `winstats.compare` raises on a non-finite value, which is 6.4 row 17 (pause and re-freeze). Fix: `ell = 0.0` and tokens 0 when no request line exists; add the case to the fault-injection tests.

**N6. Seed uniqueness cannot be enforced as written, and a collision has no consequence.** 5.4: "redrawn if the value was already used anywhere in the program (the used set is reconstructed from the chains)"; "Seeds are drawn by the worker"; 5.1: "a worker never blocks on the orchestrator". Two uncoordinated workers draw from 2^31 values; with several thousand requests per worker over the program a cross-worker collision has probability of about 1 to 2%, and the verifier check "unique across the program" then fails on a rule that 12.2 puts in the closed list. Fix: partition the space (low bit = worker index; the used set of earlier trials is loaded at worker start; the worker checks its own set) and state that a detected duplicate is a logged defect with no effect on outcomes.

**N9. The counter identities have no failure consequence and the scrape can block enrollment.** 11.5: "at trial start (where it must equal the usage of that server's smoke completion exactly)"; "counter delta minus summed client usage must be exactly 0". 5.1: "Pair `i+1` is enrolled only after ... the `/metrics` scrape of the pair boundary is logged". Whether `prompt_tokens_total` equals `usage.prompt_tokens` token for token (BOS, template tokens) is unverified; a violated "must" at the start of T2 has no rule (refuse, pause, log?); a hanging `/metrics` call stops the trial with no reason code. Fix: a scrape timeout (for example 5 s, three tries) after which the window is logged as unreconciled and enrollment continues; a start-identity violation is a `reconciliation_defect`, not a refusal; the exact identity is an Appendix D item that is established in the rehearsal of N8, with the fallback wording "residual reported".

**N12. The schema rule contradicts `trial_started`.** 11.2: "**No field of any event may hold free text, a path that is not tokenized, a URL or a commit id**". 11.2 #1: "config hash and full config". Appendix B: `"llama_cpp_commit": "4fea119d..."`, `"hf_revision": "13fb94bf..."`, `"delta_label": "laboratory demonstration margin; not application-justified"`, `"roster_rule": "S1 plus all surviving S2 ..."`. Appendix C demands that the validator "rejects ... a commit id ... and free text in every event type". As written the validator rejects seq 0. Fix: define "free text" operationally (every string field is an enum, a hex digest of fixed length, a token, or a numeric string), restrict "commit id" to this repository's commits (13.2 already says so), and embed the config by hash with the config file as a tracked sibling.

**N13. Who writes anchor events, and where the comment goes, is undefined.** 5.1: "The orchestrator is the only writer of the event chain." 11.4 item 1: the anchor process "on violation ... writes `anchor_failed(tree_state)`". Item 2: "creates a comment (on the pushed commit, or on the trial's issue)". Fix: the anchor process owns a spool like a worker and the orchestrator appends `anchor`, `anchor_receipt` and `anchor_failed`; choose one comment target now (the anchor drill tests one path); map `anchor_failed(tree_state)` on a blocking anchor to the `anchor_unavailable` pause.

**N14. The counter-semantics test does not exercise the production path.** 5.8 item 2: "(a streamed probe request is used for this test only)"; 5.3: `stream: false`. In the trials a request dies by client timeout on a non-streamed POST. Whether and when the server notices the closed connection and what it counts may differ between the two paths. Fix: run the test on a non-streamed request with a short client timeout (and keep the streamed probe only to know how many tokens had been generated).

**N15. The hard cap is not "by construction" above the longest legitimate attempt.** 5.5: "by construction larger than the longest legitimate attempt of either workflow (four calls, each with three tries, two recovery waits and the backoffs, plus three self-test executions), so it can bind only on a harness or sandbox hang"; "`server_recovery_s` | 180 | how long a try may wait for a supervised restart". If each of the three tries may wait, a legitimate call lasts up to 3 x 180 + 3 x 180 + 6 = 1,086 s, and the attempt up to about 4,400 s (four calls, three self-test runs, three lock waits) against the cap of 3,714 s; execution-lock waits (5.6) are inside `latency_s` and absent from the formula. The cap is terminal, so validity is untouched, but the sentence is false, the parameter is non-amendable, and the binding case is one arm only (the point of P2 item 3). Fix: state how many recovery waits a call may have, derive the formula from that, add lock waits, or replace the sentence by "can bind on a legitimate `self_test_repair` attempt only after at least N failed tries; reported by arm".

**N16. Thresholds that label or end a trial are amendable.** 12.2: "An amendment in the older sense (a change of an operational detail that is in neither list, for example the anchor cadence)". The list of 12.1 item 7 omits `integrity_label_rule`, `auto_abort.consecutive_infrastructure_failures` (arguably inside "failure-to-outcome rules", not explicitly), `sandwich_tolerance_s`, `gap_report_s`, `blocking_wait_minutes`, the pause thresholds. Fix: add them by name.

**N17. `max_attempts = 1` leaves a forced-failure device with two free uses.** 6.4: "three or more pairs with an interrupted or worker-died episode label the trial". In T1 a killed incumbent episode that would have succeeded turns `D_i` from 0 to +1 for the bottleneck gate. v2 discloses this and defines S-int, but S-int is "descriptive". Fix (text only): whenever a row 10, 10b or 11 episode lies at or before `tau`, the decision sentence carries "under S-int the rule [also crossed at pair n / did not cross]", and Appendix E gets that clause.

**N19. The reference rule runs only on resume and after the trial.** 9.2 and 12.4. A silent defect of the live monitor is found when the trial is over and its result is already `LIVE_DECISION_INVALID`. Recommendation: evaluate the reference rule as a shadow at every look; any difference in counts, statistic or action pauses the trial (`monitor_mismatch`, same path as row 17) before any decision is acted on. Import isolation of verifier and builder is unaffected.

### LOW

**N18.** 9.2 "Agreement" is defined on the decision; whether a count or statistic mismatch at a non-decision look is a disagreement is not said. Say: any mismatch at any look is listed; only kind or prefix decides the result.

**N20. Wording slips against the protocol's own lists.** 10.3: "the correct behaviour of a guarded rule with little power" (1.4 item 19 forbids "guarded" without the margin). D10 and D23 contain "harm gate" and "harmful candidate" although 1.4 item 5 says the words "do not appear in any tracked artifact" and the protocol will be tracked. 5.4: seeds are drawn "without access to the coin", but the worker holds its arm; say "independently of the coin".

**N21. Small unmapped or undefined items.** `thermal`: "a thermal-pressure event" names no probe (12.4). "ten consecutive revealed arrivals" (6.4): reveal order or arrival order. Integrity label: randomized phase only, or post-decision too. Timestamp-authority failure at a blocking head: blocks or not (11.4 item 6). OS build change between or inside trials: not in the drift list. Size and composition of the timeout calibration (`c_max` is a maximum of a sample whose size the operator chooses, 5.5 and 5.8 item 3). Statistic for the T3 "compression" (5.8 item 4). `episode_started` non-durable although the orphan check matches against it (12.3 step 3).

**N22. Deliverables the protocol relies on and that do not exist yet.** The issue text with the literal wording of RA1 to RA5 and RB1 to RB5 (the literal-yes rule depends on it; the coordinator list, item 19, says the wording still has to be checked); the run book of 12.5; a template of the derivation file of Appendix D; a test that every numeric constant in the protocol text (battery 20%, disk 5 and 20 GB, `/health` 5 s and 3 failures, coin self-test limits 4,850 to 5,150, 9 of 10) appears in `config.json`.

---

## 5. R2 checklist items still unmet or only partially met

| R2 item | status in v2 | note |
|---|---|---|
| (ii) power block "for the frozen rule; script + seed + output hash" | pending | N10; by design a pre-freeze step, but it should precede the issue |
| 32 "enqueue/dispatch/**first-token**/complete/verify timestamps" | not met, not declared | `stream: false` gives no first-token stamp; D34 justifies the deviation from item 50 only. Declare the deviation and name `timings.prompt_ms` as the server-side substitute |
| 42 "fsync per event" | deviation, not labelled | only durable events are fsynced; the spool covers requests. Label it as a deviation the way D34 does for item 50 |
| 50 streaming usage | deviation, declared | depends on N14 |
| 59 receipt mechanism proven before the freeze | pending | N7 |
| 26 "own config hash" per trial | partial, argued | one config, per-trial chain and arrival-order hash |
| 6 "the coin byte ... written" | deviation, argued | only the bit is logged (4.2) |
| 87 anonymous variant | open | C26 |
| 106 "loopback OpenAI-compatible interface to a local open-weight model" | missing | the phrase does not occur in v2; add to 2.2 and claim 1 |
| 41 amendment path | partial | N1: works inside a trial only |
| 53 in-flight episodes `INTERRUPTED` | met, with the hole of N4 | |
| 121 issue with protocol hash | partial | N11, N22 |
| K3(c) load-invariant sensitivity for T3 | partial, argued | success-only comparator plus regime label |

All other items of the claims auditor's section B were found closed in the text (checked: 14, 20, 22, 24, 27, 35, 36, 40, 43, 45, 52, 56, 62, 63, 66, 67, 68, 75, 78, 83 to 86, 91 to 95, 100, 101, 103, 108, 114, 119).

---

## 6. What is most likely to force a post-freeze amendment (ranked)

1. A defect in the builder or verifier, first seen after outcomes (N3).
2. A `self_test_repair` plumbing defect first seen in T2 (N8), followed by a re-freeze that has no chain (N1) and no trigger rule (N2).
3. `receipt_mismatch` or `cache_n > 0` on a repair call (N7): irreversible abort of T2 or T1.
4. A crash between coin and dispatch, with two defensible readings of the rule (N4).
5. A scrape or reconciliation identity that fails for a benign reason (N9), or a seed collision flagged by the verifier (N6).
6. `compare` raising on an undefined latency (N5), which is a row 17 pause.
7. A legitimate slow `self_test_repair` attempt hitting the cap while the text says it cannot (N15).

Not a risk for validity, but for the purpose of the program (the coordinator should decide with open eyes; already item 6 of the v2 coordinator list): Block I needs five literal "yes" comments from a root that usually answers in review files; silence freezes B; under B a DEPLOY needs an observed success difference above about +0.05 at 565 pairs (section 2), so the only expected live switch of the whole program is T2's `RETAIN`.

---

## 7. Prioritized remaining work for the coordinator

**Priority 1: text fixes for a v2.1 (no redesign; one reviser pass, then the targeted re-audit of 4.3, 5.4 to 5.8, 6.4, 9.2, 11, 12 that both BLOCK verdicts ask for).**
1. Program chain and between-trial events (N1).
2. Reason code `plumbing_fail` with a closed condition list (N2).
3. Split "decision-defining code" from "reporting code"; defect path for verifier and builder; consequence of a reference-rule defect (N3).
4. `job_accepted` spool line; rule for assigned-but-never-started arrivals; two new kill points (N4).
5. Launch line with server-side cache switches; 100% pass of the frozen receipt comparison in the rehearsal as a freeze condition (N7).
6. Real-server dress rehearsal on out-of-design tasks as a new item of 5.8 (N8).
7. Rule block with its own hash for the consultation; `winstats` pin rule (N11).
8. One-line fixes: N5, N6, N9, N12, N13, N14, N15, N16, N17, N18, N20, N21; R2 deviations for items 32 and 42; the phrase of item 106.

**Priority 2: CPU work that can be done now.**
9. Specify and run the extended replay simulator for A and for B at 565, 495 and 295 pairs with counts and Wilson intervals; put the table into the issue (N10, C12).

**Priority 3: decisions and approvals (one batch to the user, one to the coordinator).**
10. User: C9 (downloads), C10 (pushes, comments, drill), C17 (RFC 3161), C19 (visibility), C20 (retention, transcript), C13 (licence).
11. Coordinator: C1, C2, C6, C18, C21, C22, C23, C24, C26, C27, plus C11, C14, C15. Decide knowingly that B, the likely configuration, makes T2 the only expected live switch.
12. Draft the issue text with the literal RA and RB items and the cut-off; draft the run book and the derivation-file template (N22).

**Priority 4: implementation, which may start now for the modules no open item touches.**
13. `lab_eventlog` (segments, validator after N12), `lab_coin`, `lab_reference_rule`, `lab_client` with spool and drawn seeds (after N6), `lab_mock_server`, and the unit tests of Appendix C for chain, coin, betting capital, monitor, enclosures. Hold `lab_orchestrator` resume logic, `lab_anchor` and the verifier until items 1 to 4 are settled. Recommended addition: shadow evaluation of the reference rule at every look (N19).

**Priority 5: pre-freeze phase, in this order.** Serving build and manifest; downloads and roster; golden objects and mask list; counter test on the production path; calibration with a fixed plan; rehearsal of N8 with real anchors; containment probe; T3 preflight rules; R4-type re-run on the realized `N_P`; derivation file; freeze.

Prepared and checked by AI agent sessions; not human peer review or author sign-off.
