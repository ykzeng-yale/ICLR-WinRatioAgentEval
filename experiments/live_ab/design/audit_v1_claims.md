# Audit v1 of `protocol_draft_v1.md` — lens: claims, scope, reproducibility

Auditor: adversarial pre-registration auditor (root-reviewer stance of Rounds 9-15), 2026-09-19.
Read in full: `protocol_draft_v1.md` (844 lines), `R1_accepted_method.md`, `R2_constraints_checklist.md`, `R3_harness_plan.md`, `R4_power_analysis.md`; consulted `P5_supp_power.md`, `EXPERIMENT_QUEUE.md`, `EXPERIMENT_POLICY.md`, `reviews/round9_experiment_gap_assessment.md:35`, `paper/main.tex:160-167`, `experiments/local_stream/sandbox.py:74-93`, `experiments/tau2_open/config.json`, `results/local_stream/{episodes_flat.csv,data_manifest.json,timing_pilot/summary.json}`. No git state change, no model call, no download; two CPU computations (< 5 s). Line numbers `L…` refer to `protocol_draft_v1.md`.

## Verdict: BLOCK

v1 cannot be frozen. Three findings (F1-F3) each make a post-freeze repair or an unverifiable release unavoidable under the protocol's own rules; thirteen further findings are MAJOR. All blockers are repairable by text and small design changes (no re-architecture); a v2 and a re-audit are required before the GitHub issue of 12.1 step 3 is posted, because the issue text fixes the fallbacks.

Counts: 3 BLOCKER, 13 MAJOR, 10 MINOR. Section B lists every R2 item that is missing or only partially met. Section C gives the wall-clock estimate.

---

## A. Findings

### F1 — BLOCKER. The hash-chained log is required to contain strings that the release scanner forbids; the anchor process then withholds every commit, and no sanitized copy can verify.

Passages.
- L645, event 1 `trial_started`: "... freeze commit, external freeze anchor (URL and server timestamp) ...".
- L664, event 20 `anchor_receipt`: "anchor seq, commit id, branch, pushed (bool), external {kind, URL, server `created_at`}".
- L679: "Before each commit the anchor process scans the files to be committed for forbidden patterns (13.2); on a hit it withholds the commit and logs `anchor_failed(forbidden_pattern)`."
- L733-734: "No tracked artifact contains ... a repository URL with an account name. ... scans ... for: the local account name, the GitHub account name, the institution name, the repository name ...".
- L735-736: "a sanitized copy is released with an original-to-release hash map"; "Two variants of the hand-off are produced (with and without researcher repository URLs and commit ids)".

Why it fails. The only external-timestamp channel is a GitHub issue comment. Its URL is `https://github.com/<account>/<repository>/issues/<n>#issuecomment-<id>`; for this repository the URL contains the GitHub account name, the institution string inside it, and the repository name (see the issue links in `EXPERIMENT_QUEUE.md`). That URL is written into `events.jsonl` at seq 0 and again in every `anchor_receipt`. Concrete run: T4 starts, `trial_started` carries the freeze-anchor URL, the first anchor fires, the scanner hits three forbidden patterns in `events.jsonl`, the commit is withheld, and the same happens at every later anchor. Result: zero run-time anchors, "longest unanchored span" = the whole trial, every "publicly timestamped" run-time claim is dead, and because "an amendment cannot take effect without its external receipt" (L679, L705) no amendment can ever become effective. The Appendix C "anchor drill in a throwaway repository outside the project" cannot detect this, because a throwaway repository has neither the account nor the repository name in its URLs; the defect would first appear in the live T4.
Second failure: `h_i` is a hash of the canonical event, so a "sanitized copy" of `events.jsonl` has a broken chain by construction, and the "variant without commit ids" cannot exist while seq 0 carries `freeze commit` and each receipt carries `commit id`. The released log would be unverifiable against the anchors, which removes the point of the chain (R2 items 42, 85, 87).

Required change. (a) Decide and state whether an anonymous variant is a deliverable at all now that the target is arXiv; if it is, the chain must be identifier-free by construction. (b) In-chain fields carry only tokenized locators (`<REMOTE>`, numeric issue and comment ids, server `created_at`), never a URL; commit ids either stay in the chain and the "without commit ids" variant is dropped, or go to a side file `anchors/receipts_private.json` that is hashed into the chain. (c) State that the released `events.jsonl` is byte-identical to the raw chain; delete the sanitized-copy path for this file. (d) The anchor drill must run against a remote whose URL contains the real forbidden strings (a scratch repository under the same account), and the scanner must be run on a mock `events.jsonl` produced with the real freeze-anchor locator before the freeze.

### F2 — BLOCKER. No rule exists for a harness or protocol defect found after the single freeze, although the protocol plans to find one; the chronology claim for later trials is then false.

Passages.
- L74: "It consists of four separately frozen trials"; L39 (D21): "one freeze for all four; no trial is repeated"; L693: "Freeze procedure (one freeze for all four trials)". These contradict each other.
- L716: "T4 first, so that a plumbing defect is found where it costs no claim".
- L646: "any drift in config, harness, weights, binary = refusal"; L700: "The runner refuses to start on any hash mismatch".
- L418 (row 17): "after an amendment (12.2) the monitor is replayed from the log"; L705: amendments cannot change "any system version"; nothing says how changed harness bytes pass the drift refusal.
- L5: "frozen before any design-task outcome".

Why it fails. Scenario: T4 runs to its horizon and the verifier finds that `overlap seconds` or the certified-elapsed stamp is wrong, or `lab_monitor` raises at pair 212 (row 17). Any fix changes a `lab_*.py` hash, hence the freeze bundle, hence the chain genesis; the runner refuses T2, T1 and T3. The protocol offers no path: an erratum "never changes the frozen bytes", an amendment is within-trial and may not touch code identity, and "no trial is repeated". The operator will improvise a re-freeze, which is exactly the Round 11-12 amendment finding ("no immutable record", decision taken after outcomes). Worse, after T4 the `single_shot` outcome of every roster task on the trial stack is on disk (T4 runs `single_shot` on all 2·N_P arrivals), so any re-freeze of T2/T1/T3 is a freeze after design-task outcomes of the same tasks, same model, same workflow. The header phrase (L5) and allowed claim 2 (L98) would be false for those trials, and L214 ("No outcome of the new trials is known") is false for every trial after the first even without a defect.

Required change. (a) Remove the contradiction: either four freeze bundles (one per trial, each pushed and posted before that trial's first episode, with a common harness hash) or one; say which. (b) Add a section "Defects between and within trials": closed list of permitted code changes (none that touch `lab_coin`, `lab_monitor` decision logic, scoring, failure rules, seeds, sampling); procedure = new freeze bundle version for the not-yet-started trials, pushed and posted before their first episode, with a harness-computed `what_was_known` that lists every earlier trial's revealed outcomes; the chronology wording for such a trial becomes "frozen before any outcome of this trial and after the outcomes of trials X on the same tasks". (c) State how a monitor-code fix passes the drift check (new `inv` with an `amendment_effective` that whitelists exactly the new file hash) or delete row 17's replay path and make a monitor exception a `trial_aborted`. (d) Prespecify a T4 inspection list limited to plumbing quantities (chain verification, reconciliation residual, receipt mismatches, arm symmetry of stamps, abort counts); task-level T4 outcomes and any per-stratum success table are not built or read until the last trial has ended; say so in 12.4 and in 3.4. (e) Replace L214 by a sentence that is true after T4.

### F3 — BLOCKER. The fallback space is not a set of complete rules; partial acceptance by the root yields an unspecified rule, one natural assembly exceeds the 0.05 budget, and the wait for the root has no end.

Passages.
- L51-55 (C3-C7): five independent root items, each with its own fallback; C5 has two alternative fallbacks.
- L52 (C4 fallback): "upper endpoint of the two-sided normal-mixture NB band below 0 (8.9)".
- L542-544 (8.9): only two complete parameterizations exist (betting driver with `delta = 0.10`; normal-mixture driver with `delta = 0.15`).
- L697: "The freeze waits for the root's answers; each unanswered item takes the fallback of table 0.2, and the issue records which."

Why it fails. C3 (yes/no) x C4 (yes/no) x C5 (three options) x C6 (0.10/0.15) x C7 (two options) x roster (EXT/S1) gives more than 90 possible frozen configurations; two are written down and only a handful have any power number. Scenario: the root accepts betting gates (C3) and declines the betting harm gate (C4). The rule is then betting NB at 0.005 and S at 0.04 plus "two-sided normal-mixture NB band below 0". The protocol gives that band the level `a_NB2 = 0.01` (L542); the union bound is 0.005 + 0.04 + 0.01 = 0.055 > 0.05, and nothing in the draft says which level the hybrid uses or what `delta` applies. Whoever resolves this does so after reading the root's answer and the power tables, i.e. post hoc with respect to the design record, and claim 2 (L98, "at most 0.05") may be false as assembled. "The freeze waits ... each unanswered item takes the fallback" is self-contradictory (wait or fall back?) and has no date, so the driver and the margin of the trial depend on an unbounded, undocumented event.

Required change. Collapse the fallback space to exactly two complete, fully parameterized, separately simulated configurations: A (default: betting NB/S/H, levels as in 8.4, strata, `delta` by roster) and B (8.9 in full, including levels, `delta`, strata choice). Rule: A is used only if the root confirms C3, C4, C5, C7 and C8 literally; any refusal, partial answer or silence maps to B. Put a dated cut-off in the issue (for example 72 hours after posting; silence = B). Record the root's reply by comment id. Give Appendix B for both A and B with no `null` other than the items of Appendix D.

### F4 — MAJOR. The purpose statement claims the trial is the queue's conditional experiment, but the protocol's own claim lists license neither of the two claim types the queue ties to it; the queue quote is truncated; the asynchronous part is degenerate by design.

Passages.
- L72: quote of `EXPERIMENT_QUEUE.md` ending "... Required for measured operational savings or live-deployment claims". The source continues: ", which this paper does not make."
- L74: "`live_ab` is that experiment."
- L108, L117: forbidden are "deployed" without "in the laboratory dispatcher" and "Measured time or token savings derived from counterfactual or replayed paths".
- L101 (claim 5) and L309: "With two workers a sliding window would not give a materially richer asynchronous study either".

Why it fails. The root's gap text (`round9_experiment_gap_assessment.md:35`) asks for this experiment "For an operational latency claim ... actual concurrent prefix evidence ... the matched completed-prefix comparator" and orders the limitation "feasibility, not operational latency savings" to stay until then. Under D3 at most one pair is ever pending, so `t_dec - t_enc` is bounded by the residual duration of one episode (pilot: mean 12.5 s, p99 45 s) inside a run of 1-3 hours. Claim 5 will be literally true and scientifically empty; a reader of "live_ab is that experiment" will conclude that the operational-latency gap is closed. Likewise the trial yields no measured time or token saving (9.4 item 3 is a projection) and no deployment. So after a fully successful program the manuscript still may not say "measured operational savings", "operational latency savings" or "live deployment", and the protocol never says this plainly.

Required change. Quote the queue line completely. Replace "live_ab is that experiment" by a scope paragraph: what the queue item asked for, what this design delivers (a live traffic switch in a laboratory dispatcher; exact exposure counts; reveal timestamps with at most one pending pair), and what it does not deliver (operational latency savings of partial-information monitoring under substantial delay; measured time/token savings; any deployment claim), with the explicit sentence that the paper's "feasibility, not operational latency savings" limitation is retained. Add to 1.3 claim 5: "with at most one pending pair; the difference is bounded by one episode duration and is not evidence about the value of partial-information monitoring". Add an appendix listing the exact manuscript sentences the trial could add, one per outcome.

### F5 — MAJOR. "Exposures avoided" and its percentage are functions of the arbitrary horizon, the phases use different schedulers, and the claim lacks the host qualifier.

Passages. L100 (claim 4); L574: "= `M` ... Also reported: `M / N_P`"; L622: "about 88 to 91% of the scheduled candidate exposures would be avoided"; L311 (post-decision phase work-conserving) versus L307 (randomized phase pair-synchronous); L575 "Measured totals: wall-clock time, busy time per worker ... by phase and arm".

Why it fails. `M = N_P - tau`. With the same data and the same `tau = 58`, a roster of 295 pairs gives 80%, 565 pairs gives 90%, 5,000 pairs gives 99%. The percentage measures the roster length chosen by the drafter, not the method. It is the number that will be lifted into an abstract. Second, the randomized phase deliberately idles the fast worker while the post-decision phase is work-conserving, so any wall-clock or throughput comparison between phases, or between the run and "N_P x mean pair time", mixes a scheduler change with an arm change; on a closed-loop list with no arrival clock there is no traffic whose waiting time could be saved. Third, claim 4 has no "on this host, under this serving regime" qualifier although claim 5 has one.

Required change. Primary operational quantity = `tau` (pairs and arrivals enrolled at the decision) and the switch latency. `M` may be reported only with the sentence "M is determined by the prespecified roster length N_P"; `M / N_P` and every percentage of exposures avoided are forbidden in abstract, introduction, captions and the results index (add to 1.4). Add to 1.4: no wall-clock, throughput or per-episode latency comparison across phases; add to 9.4 item 3 "the two phases use different schedulers". Add the host and regime qualifier to claim 4.

### F6 — MAJOR. The non-inferiority margin is a function of power, conditional on roster and driver, and the protocol itself calls it practically unacceptable; on EXT it is an absolute margin on a roster diluted by a low-success stratum.

Passages. L30 (D12); L209: "`n_S2 >= 400`, the roster is EXT ... and `delta = 0.10`. Otherwise ... `delta = 0.15`"; L544: normal-mixture driver "`delta = 0.15`"; L626: "laboratory demonstration margin chosen for feasibility ... a 10-point success loss would rarely be acceptable in practice"; `paper/main.tex:165-166`: "The margins delta_j require application-specific justification."

Why it fails. A margin that moves from 0.10 to 0.15 when the download is refused or when the root prefers its own construction has no application rationale; it is the smallest value at which the drafter's simulation on pilot outcomes of the same tasks gives an acceptable deploy probability. The root's standard (R9-GAP:33, R11-TGT:90) forbids choosing margin or hierarchy after outcomes; disclosure does not turn a power-selected margin into a justified one. A `DEPLOY_CANDIDATE` event at 0.10 certifies only that the running success difference is above -0.10, which the protocol says nobody would accept; the label will nevertheless read as "guarded deployment". Dilution: the only data on S2-type tasks (`timing_pilot/summary.json`: 1/6 and 2/6 successes) suggest success near 0.25 against 0.73 on S1. On a roster where half of the tasks are failed by both arms, a same-task loss of 6 points on S1 appears as about 3 points on EXT; adding such tasks mechanically moves the running difference toward 0 and makes an absolute-margin non-inferiority crossing easier. That is the standard bias toward non-inferiority from a diluted population, and it is nowhere disclosed.

Required change. (a) One margin per configuration, fixed now, with the sentence "chosen for power from pilot outcomes of the same tasks; not application-justified; a crossing does not establish non-inferiority at any practically relevant margin". (b) The action label and every mention carry the margin: `DEPLOY_CANDIDATE (laboratory, success margin 0.10)`. (c) Every report of a crossing prints, in the same sentence, the S-gate log E at the paper's 0.03 and whether it crossed, and the S-gate log E restricted to S1 pairs at the decision prefix (descriptive). (d) Disclose the expected roster-level success rate and the dilution mechanism in 10.4 and in the T1/T3 captions. (e) Add to 1.4: the word "guarded" without the margin.

### F7 — MAJOR. The protocol uses the method-independent impossibility wording it forbids.

Passages. L30: "The paper's 0.03 is declared 'not certifiable at this sample size' in advance"; L597: "Margins 0.03 and 0.05 are not certifiable at any feasible single-exposure size"; L626: "declared in advance 'not certifiable at this sample size'". Against L120 (forbidden: "'not certifiable whatever the method' ... The permitted sentence is 'this prespecified rule did not certify margin delta on these data'") and R2 items 23, 97 (R12-INF:65, R13-INF:44, R9-AUD:117).

Why it fails. "Not certifiable at this sample size" and "at any feasible size" are statements about all methods. The evidence is a simulation of two constructions with one stake grid on plug-in pilot outcomes. A sharper construction (predictable plug-in stakes, a paired same-task design, a variance-adaptive boundary) is not excluded. This is a repeat of an explicit root correction.

Required change. Replace all three by: "for this rule, this alpha allocation and this roster, the planning probability of an S-gate crossing at 0.03 (0.05) is about 0.06 (0.18) or lower; these margins are logged descriptively and are not tested". Same edit in R4-derived sentences that enter the freeze bundle.

### F8 — MAJOR. The operating characteristics in section 10 are not those of the frozen rule, and several inputs are wrong or unsupported.

Passages. L60 (C12 fallback): "freeze with 10.2 and 10.3 as they are, labelled as such"; L608: "S2 tasks have no pilot data and mean success 0.60 or 0.45"; L252: "EXT: 295 + `floor(n_S2/2)`, at most 568"; L209: "`n_S2 >= 400`"; L602-603 (T4 and T3 numbers); L599 and L544 (normal-mixture driver).

Why it fails.
1. R2 checklist (ii) requires "operating characteristics per trial ... for the frozen rule; A/A false-crossing rate with Wilson interval". For the frozen T4 rule (levels .005/.04/.005, stratified pairs) no rate, count or interval is given; L602 quotes other schemes. T3 (equal thirds, two-tier hierarchy, strata built from the incumbent family's pilot pattern, two server processes) was never simulated; L603 is an analytic table that assumes 0.39 discordance and no strata. No table in section 10 has counts or Wilson intervals (R2 item 27).
2. The chosen configuration rests on the drafter's own latent-variable simulation with an invented "pilot predictiveness" w in {1.0, 0.7}; no value below 0.7 was run, although the serving stack, quantization and sampler chain all change. The C12 fallback allows freezing on this.
3. The S2 success rates assumed (0.60, 0.45) are contradicted by the only available observations (3 of 12 on MBPP-full-only tasks). No cell near 0.25 exists.
4. Arithmetic: MBPP-full-only = 974 - 427 = 547; minus the six smoke tasks = 541; `floor(541/2) = 270`; maximum `N_P` = 295 + 270 = 565, before duplicates and sweep failures, not 568. Every EXT power number is for an unreachable horizon. At the cliff `n_S2 = 400` the horizon is 495 pairs and no power number exists, yet `delta = 0.10` applies.
5. The joint fallback (S1 roster and normal-mixture driver, `delta = 0.15`) has planning P(deploy) 0.05-0.23 (R4) or 0.01-0.13 (`P5_supp_power.md`, S1 stratified). T1 is then expected to abstain with probability above 0.8, and no go/no-go statement exists for that case.

Required change. C12 becomes mandatory with no fallback: R4's simulator (not P5) is re-run for the exact frozen configurations A and B on the actual `N_P`, for all four trials, with S2 success cells {0.25, 0.45, 0.60}, w cells {0.3, 0.5, 0.7, 1.0}, counts and Wilson intervals, and the frozen T4 rule. Add a table "plain expectation per configuration": P(deploy), P(retain), P(abstain), median tau. For every cell with P(decision) < 0.5 write the sentence "this trial is expected to end in abstention; it is run because ..." or remove the trial from that configuration. Correct 568 to the computed maximum.

### F9 — MAJOR. T3 model choice: the "no outcome" statement is false, the fallback destroys the trial's rationale, and several T3 rules are ambiguous or unverified.

Passages. L166: "(vi) instruction-tuned with published code-generation ability of the same order as the incumbent"; L168: "`mistralai/Mistral-7B-Instruct-v0.3` (Apache-2.0, weak at code, outcome predictable) ... The rationale contains no outcome of any candidate on any design task."; L170 (fallback rule: "the chat template fails under `--jinja`"); L155: "the Q4_K_M file of that repository"; L63 (C15); L357: "Success outcomes of these runs are not inspected for any design choice"; L381 (T3 tiers).

Why it fails.
1. "Published code-generation ability" of instruction models is published as HumanEval and MBPP pass rates; those benchmarks are the design roster. Criterion (vi) and the exclusion "weak at code, outcome predictable" are selections on aggregate outcomes on the design tasks. L168's last sentence is false as written, and no number or source for (vi) is given.
2. The fallback (Qwen3-4B, community conversion) violates criteria (ii), (iii) and (iv) by the protocol's own text, and a 4B model against a 7.6B model decides the latency tier by size, which is the reason phi-4 and Phi-4-mini were rejected. With the fallback, "the only trial with unknown outcome" (L90, L93) no longer exists, but T3 would still be run and reported.
3. Nothing verifies before the freeze that the candidate's answers are extractable by `extract_code`, which was developed on the incumbent family, because success outcomes of the calibration are "not inspected". Scenario: Granite answers without a fenced block under its template; T3 becomes "candidate fails 100%", RETAIN at pair 25, reported as a model swap.
4. "fails under `--jinja`" is undefined (crash, warning, wrong role rendering?). "the Q4_K_M file" is ambiguous if the repository holds several or split files; repository existence was never checked (C15).
5. The T3 contrast is confounded by differential benchmark contamination of two model families; L215 covers "no contamination-free claim" generically, not for the one contrast where it changes the reading.
6. The T3 latency tier is measured with two server processes competing for one GPU under the operating system's Metal scheduling; R3 (C.3 item 3, Q3) called this tier "contention-dominated noise" for T3/T4. The change of hierarchy for T3 (D6) is not among the items sent to the root.

Required change. (a) Rewrite L168: "no outcome produced by this harness was used; published aggregate pass rates on the same public benchmarks were used for criterion (vi)", with the numbers and sources, and drop "outcome predictable" as a criterion or admit it as outcome-informed. (b) Fallback: if Granite fails preflight, T3 is not run (deferred), or name a fallback that meets (i)-(v); never a same-vendor smaller model under the T3 label. (c) Add an outcome-blind format-conformance check on the ten out-of-design prompts (response contains an extractable code block: yes/no), with a frozen threshold and the consequence; disclose in every T3 claim "prompts and extractor were developed on the incumbent family". (d) Define the template failure test and the file-selection rule. (e) Add the contamination sentence to the T3 claim template. (f) Add D6 to the root's CONFIRM list; every T3 composite result carries "latency under cross-process GPU sharing on this host" and is accompanied by the success-only composite.

### F10 — MAJOR. Reuse of pilot tasks: the precedent is applied inconsistently and the justification is a power argument.

Passages. L213-218 (3.4 items 1-6); L216: "A split that holds out every pilot task would leave at most the S2 stratum ... too few for any success gate"; L218: "units whose outcomes were seen in smoke use are excluded ... as task 0 was in the airline study"; L214.

Why it fails. Six tasks are excluded because their outcomes were seen, 591 tasks are kept although their outcomes under both workflows were seen, and the stated reason for the difference is sample size. A hostile reader will call the precedent decorative. The strata that produce most of the S-gate power (discordance 0.19 against 0.39, L233) are built from those seen outcomes; this is legitimate as a baseline covariate but must accompany every S-gate result, not only "every T1/T2 result" (T3 and T4 use the same strata). After T4, outcome knowledge exists on the trial stack itself (F2).

Required change. State the actual rule: "excluded = tasks with any outcome on the trial serving stack before the freeze; pilot outcomes on the MLX stack are disclosed and used as baseline covariates". Extend the disclosure of 3.4 item 5 to all four trials and to the strata. Add the T4 blinding rule of F2(d). Report for every S-gate statement the unstratified-order counterfactual is not available and say so; report the S2 (pilot-naive) stratum read-out next to it.

### F11 — MAJOR. "No episode-level retry" is contradicted by the re-run rules; a hard-cap kill triggers an outcome re-draw.

Passages. L345: "There is **no episode-level retry**"; L343: "`max_attempts` 3"; L411 (row 10): "`episode_hard_cap_s` exceeded (worker killed) ... same arrival, same arm, `attempt + 1`"; L330: `attempt` enters the seed.

Why it fails. R2 item 32 asks for "a frozen hard timeout so a pending pair has a known worst-case score (timeout = failure)"; items 35, 52, 53 and R1 e.4(3) ("never re-run for a better outcome"; interrupted episodes "scored by the frozen failure rule"). Here an episode that runs into the cap is killed and re-run with new seeds up to twice. Slowness is outcome-related (repair rounds, long generations, hanging self-tests occur in failing episodes) and arm-related (`self_test_repair` has about 3 calls and sandbox executions per episode, `single_shot` one). Scenario: a T1 incumbent episode hangs in a self-test, is killed at 1,800 s, is re-run, succeeds; the archived label is "success". The rule is frozen and arm-blind in code but not neutral in effect, and the sentence at L345 is false.

Required change. Hard-cap exceedance = revealed failure (`success = 0`, `error_class = episode_timeout`, latency = certified elapsed), no re-run. Worker death and orchestrator crash: at most one re-run, justified in the text as coin- and outcome-independent, with a prespecified sensitivity that scores every re-run arrival as failure. Reword L345 to "a returned episode is never re-run". Derive `episode_hard_cap_s` from the out-of-design calibration (R2 item 43) instead of the unexplained 1,800.

### F12 — MAJOR. The usage-accounting claim rests on unverified server behaviour; the receipt mechanism has no fallback for the main server.

Passages. L402: "the server cancels generation on disconnect; tokens bounded by the `/metrics` delta"; L683; L102 (claim 6); L170 (receipt failure only handled for the T3 candidate); L319 `stream: false`.

Why it fails. R2 item 50 proposed streaming so that aborted requests have measured partial usage; the protocol silently chose non-streaming and replaces measurement by a counter bound. Whether `tokens_predicted_total` at the pinned commit includes tokens of a cancelled task was read from source by R3, never tested. If cancelled tokens are not counted, the reconciliation residual is 0 while generated tokens are missing: the Round 12 finding (246,284 omitted tokens) reproduced with a green check. The windows are anchor-to-anchor (about 50 episodes, two concurrent slots), so the bound for one request is coarse. If the `__verbose` receipt is absent on the coder server at this build, no rule applies (R2 item 59 named a loopback logging proxy as the alternative).

Required change. Add to 5.8 a pre-freeze test on the real server: start a 1,024-token generation, disconnect at about 200 tokens, scrape `/metrics`, record whether and how many tokens are counted; freeze the accounting wording accordingly ("bounded by" only if proven). Scrape `/metrics` immediately before and after every request that ends in `llm_error` when the partner slot is idle, else mark the bound as joint. State the deviation from R2 item 50 and why. Add the rule for a failed receipt on the coder server (proxy, or no trial).

### F13 — MAJOR. The serving software is not pinned: the hashed "binary" is a 33 KB launcher, the real code is in unhashed dylibs, and the build lives in a purgeable session temp directory.

Passages. L136: "The binary's SHA-256 and the commit read from the checkout's `.git` are part of the freeze bundle"; L699; L727 (`env_lock.txt`: "llama.cpp commit and binary hash, launch lines").

Why it fails. `experiments/tau2_open/config.json` points to `<scratchpad>/llama.cpp/build/bin/llama-server`: 33,472 bytes, dynamically linked (`otool -L`) to `libllama-server-impl`, `libllama-common`, `libllama`, `libggml`, `libggml-metal`, `libggml-cpu`, `libggml-blas`, `libggml-base`, `libmtmd` in the same directory. Hashing the stub pins nothing about sampling or kernels. The directory is under `/private/tmp/<session>/scratchpad`, which macOS clears at reboot and by age. Scenario: reboot between T2 and T1; the build is gone; a rebuild has different bytes (absolute rpath, timestamps); the runner refuses; the remaining trials cannot run under the freeze (F2). Build options and compiler are not recorded, so a third party cannot reproduce the server.

Required change. Build into a persistent directory outside any temp tree before the freeze; freeze a manifest of SHA-256 for the launcher and every linked non-system dylib; record cmake options, compiler and SDK versions; preflight verifies the whole manifest and the resolved rpath.

### F14 — MAJOR. "Publicly timestamped" is not established.

Passages. L5; L97 (claim 1); L679: "the comment's server-side `created_at` is the external timestamp"; L284: beacon rejected because it "needs network calls during the run; policy is loopback only"; L58 (C10 fallback).

Why it fails. The protocol never states whether the repository and its issues are public; if private, "publicly" is false. An issue comment can be edited or deleted by the account that wrote it, so it is an external clock, not an immutable record; a pushed commit carries client-side dates only (the protocol admits this), and GitHub shows no durable push time. The reason given for rejecting a public beacon is inconsistent with an anchor process that pushes and comments over the network during the run. If C10 is declined, `amendment_effective` can never be issued, which the fallback column does not say.

Required change. State repository visibility in the freeze record; if private, the wording is "externally timestamped on a private repository". Add one owner-independent timestamp for the freeze bundle hash and for each decision head (for example an RFC 3161 or OpenTimestamps proof file committed next to the anchor), or downgrade the wording to "timestamped by a GitHub issue comment that the account owner can edit; edit history was not altered" and print that sentence wherever "publicly timestamped" appears. Correct the rationale at L284. Add to C10's fallback: "no amendment can take effect; any event that needs one aborts the trial".

### F15 — MAJOR. Anchoring commits from a shared working tree.

Passage. L679: "A separate anchor process commits `events.jsonl` and the anchor file on branch `session60/live-ab` and pushes".

Why it fails. The repository working tree is shared by several agent sessions (the collaboration rules exist because of that); the tree is currently on `session60/local-stream` with untracked files. A commit every 2-10 minutes for hours assumes that nobody switches the branch, stages files or commits in that tree. Scenario: another session checks out a different branch during T1; anchors land on the wrong branch or sweep in unrelated staged files; the verifier's `git show <commit>:<path>` check fails; the anonymization scan blocks the rest.

Required change. The trial runs from a dedicated clone or `git worktree` used by nothing else; the anchor process stages explicit paths only and asserts `HEAD` branch, clean index and expected parent before each commit; on violation `anchor_failed(tree_state)`.

### F16 — MAJOR. Discretionary rules and an undisclosed operator.

Passages. L718: "ten consecutive `harness_abort` outcomes (pause, then amendment or abort)"; "A trial that cannot be completed is closed with `trial_aborted(operational)`"; "any look at the raw log by the operator is an `operator_action`"; L287 ("residual reliance on operator honesty").

Why it fails. Who chooses between amendment and abort, and on what information, is not said; "cannot be completed" has no criterion. Both choices can be made after looking at the log. The operator is an autonomous AI agent session with read access to every file; the blinding rule is unenforceable and the protocol does not disclose who the operator is (R2 item 108 requires the AI disclaimer on session-60 documents).

Required change. Decision table for every pause reason (condition -> single action). State that the operator is an AI agent session, that its blinding is procedural, and whether its transcript is archived and hashed into the delivery.

### F17 — MINOR. "Physically randomized" (title, L97) versus "macOS kernel CSPRNG" (L267). Use "assigned by the operating-system CSPRNG at enrollment; no stored seed" in claim 1 and the title; keep fairness as the listed assumption of 7.4.

### F18 — MINOR. Licensing record is incomplete. (a) L193-195 give MBPP as "CC-BY-4.0" although the pinned file comes from the Apache-2.0 `google-research` repository and the CC-BY statement comes from a Hugging Face dataset card (`data_manifest.json` says so); apply the literal-evidence rule of L160 to datasets. (b) The S2 pin (revision `f82046b`, 563,743 bytes, `ccf64cea…`) was measured on the mutable `master` URL, never at that revision; label it "expected, verified at download". (c) llama.cpp (MIT) and the Python dependencies are not in `SOURCE_NOTICES.md`. (d) C13 fallback "release without licence statement" means all rights reserved; say that. (e) CC-BY-4.0 requires indication of changes if any task text is ever shipped; state that `roster.json` holds uids only.

### F19 — MINOR. The internal names "harm gate", `alpha_H`, "H gate" will appear in `monitor.csv` and tables although 1.4 item 5 forbids harm language; rename to "unfavourable-composite gate" in every tracked artifact. T1 and T2 are mirror images on the same tasks and systems; say that T2 adds a live switch, not a second estimate.

### F20 — MINOR. L675 "independent verifier": it is written by the same session; call it "separate code path". L560 "exactly": float equality holds in the locked environment only; the builder should require exact decisions and counts and a stated tolerance for log E on other platforms.

### F21 — MINOR. L35 "all other samplers neutral ... every field sent explicitly" is not literally true: DRY, XTC, top-n-sigma, dynamic temperature and the sampler order are not sent. `receipt_keys` must cover every sampler-affecting key of `generation_settings` with its required neutral value.

### F22 — MINOR. Sandbox. Setting `TMPDIR` changes the Seatbelt profile text (`sandbox.py:80-93` derives it from the temp directory and the home directory), so the per-episode profile hash differs from the audited `6370c169…`; re-run the containment tests under the new `TMPDIR` before the freeze and record the new hash in the bundle. Appendix B carries `"mem_bytes": 2147483648` although L349 says no memory cap is enforced; remove or label "not enforced" (R2 item 114).

### F23 — MINOR. L220 "Each trial uses the whole roster once" is false under `ABSTAIN_AT_HORIZON` (L534: leftovers not executed) and for unpaired leftovers generally; claim 1's N must be the computed count of executed arrivals.

### F24 — MINOR. 1.4 item 9 is weaker than R2's must-never 9 (it drops the no-interference/stable-law assumption); add "and the assumptions listed in 7.4". 8.4's program-wide 0.20 sentence must be mandatory wherever two trials appear in one table, abstract or paragraph; add to 1.3.

### F25 — MINOR. Non-durable `llm_request`/`llm_response` events can be lost at power loss (R2 item 42 asked for fsync per event); state the consequence for usage accounting and that the gzipped request files written by workers are the recovery source, or make `llm_response` durable (4 ms).

### F26 — MINOR. `n_min`, strata and allocation are pilot-informed; L511 says so for the allocation only. One sentence in 1.2 must list every pilot-informed parameter (hierarchy, tolerances, margin, strata, allocation, hypothesis directions, `n_min`, execution order, T2 label).

---

## B. R2 checklist: items missing or only partially met

| R2 item | status | what is missing | finding |
|---|---|---|---|
| K3(c) | partial | load-invariant sensitivity exists for T1/T2/T4; for T3 only "success only"; T3 latency under cross-process sharing not flagged | F9 |
| K4 | partial | exact count present, but percentage and cross-phase totals invite the forbidden claim | F5 |
| K5 | partial | margin has no application rationale; conditional on roster and driver | F6 |
| K7 | partial | disclosure limited to T1/T2; outcomes on the trial stack known after T4 | F2, F10 |
| 14 | missing | unit test "unit initial capital, E[capital after one fair step] <= 1" not in Appendix C | — |
| 20 | missing | test asserting absence of a running intersection not in Appendix C | — |
| 22, 27 | partial | no A/A rate for the frozen rule; no counts or Wilson intervals in section 10 | F8 |
| 23, 97 | violated | impossibility wording at L30, L597, L626 | F7 |
| 24 | partial | pilot-expected share of pairs decided at each tier not tabulated per trial; none for T3 | F8 |
| 26 | partial | one config and one freeze bundle for four trials, against "own config hash"; "separately frozen" contradiction | F2 |
| 32 | partial | no first-token stamp (non-streaming); hard cap is not "timeout = failure" | F11 |
| 35, 52, 53 | partial | re-run after hard cap, worker death and crash, up to three attempts | F11 |
| 36 | partial | T3 rationale uses published benchmark outcomes; fallback model changes the trial | F9 |
| 40, 45 | partial | "publicly" depends on repository visibility; comment is editable | F14 |
| 41 | partial | amendment path deadlocks if C10 is declined or if F1 occurs; no path for code defects | F1, F2, F14 |
| 42 | partial | fsync only for durable events | F25 |
| 43 | partial | `episode_hard_cap_s` = 1,800 not derived from the timing pilot | F11 |
| 50 | deviates | non-streaming; counter semantics untested | F12 |
| 56 | partial | `episodes_with_missing_label` absent from the named summary fields | — |
| 59 | partial | receipt path proven only in the pre-freeze phase; no fallback for the coder server | F12 |
| 62, 63 | partial | launcher hash only; dylibs, build options, compiler unrecorded | F13 |
| 66 | partial | single `timed_out` flag; request, episode and verifier timeouts not separate outcome fields | — |
| 67 | partial | S2 pin never fetched at the pinned revision | F18 |
| 68 | missing | check that every path named in a mapping exists in the git tree | — |
| 75 | partial | profile hash changes with `TMPDIR`; containment not re-tested under it | F22 |
| 78 | missing | queue wait (enqueue to dispatch) not a recorded field | — |
| 83-87 | violated | account and repository name enter the chain through anchor URLs; sanitized chain unverifiable | F1 |
| 91 | missing | preflight disk-space check and `.gitignore` check for `<WORK>` | — |
| 92, 93 | partial | dataset licence evidence not literal; server and dependency licences absent | F18 |
| 95 | missing | statement that the runner shares no entry point with the historical commercial scripts | — |
| 100, 101 | partial | purpose paragraph implies the queue's claim types | F4 |
| 103 | missing | "mixes ... cannot separate" wording rule for descriptive stratum and phase differences | — |
| 108 | partial | operator not disclosed as an AI agent | F16 |
| 114 | partial | unenforced `mem_bytes` in the config | F22 |
| 119 | partial | "say so in the PR" (merge-only versus `COORDINATION.md:17`) not in 12.1 | — |
| 121 | partial | issue has no cut-off date; fallbacks not complete rules | F3 |
| (ii) power block | partial | not for the frozen rule; no T3, no frozen T4 | F8 |
| (ii) claim lists | partial | must-never 9 weakened; percentage of exposures and cross-phase comparisons not forbidden | F5, F24 |

Items not listed were found addressed in the text.

---

## C. Wall-clock estimate per trial (pilot latencies, pair-synchronous W = 2)

Inputs: `episodes_flat.csv` (MLX stack, sequential): `single_shot` mean 2.80 s (p99 10.8, max 16.7), `self_test_repair` mean 12.48 s (p99 45.2, max 57.3), verification 0.03 s; E max(SS, STR) over cross-task pairs = 12.6 s; E max(SS, SS) = 3.8 s. MBPP-full-only tasks (timing pilot, n = 6): SS 4.8 s, STR 19.4 s. Overhead assumed 0.5 s per pair (two verifications, durable appends at 4 ms, monitor, dispatch). Contention factor 1.3-1.6 on overlapped decode (llama.cpp continuous batching; unknown until 5.8).

| trial | scenario | randomized phase | post-decision phase | total |
|---|---|---|---|---|
| T4 | no decision, EXT about 565 pairs | 0.9-1.3 h | none | 0.9-1.3 h |
| T2 | RETAIN near pair 58 | 0.25-0.3 h | about 1,015 SS arrivals on two workers: 0.6-0.9 h | 0.9-1.2 h |
| T1 | DEPLOY near pair 280 | 1.3-1.5 h | about 570 SS arrivals: 0.35-0.5 h | 1.7-2.0 h |
| T1 | ABSTAIN (EXT, S2 episodes slower) | 2.6-3.3 h | none | 2.6-3.3 h |
| T1 | wrong-direction decision early | 0.3 h | about 1,000 STR arrivals: 2.8-3.5 h | 3.1-3.8 h |
| T3 | no decision, two servers | 1.0-2.0 h (candidate verbosity unknown) | none | 1.0-2.0 h |
| S1 roster only | all of the above | about 0.52 x | | |

Program total on EXT: about 6-8.5 h of GPU time in the expected cases, 10-11 h in the worst listed cases, plus weight hashing (about 15 s per invocation per model) and the pre-freeze calibration. The protocol's "about 3 hours" for a full T1 horizon (L309) and "about 8 GPU hours" (L697) are consistent with the pilot but are central values, not bounds; the issue text should give the range. Each trial fits in one attended session and the program in one to two days, so run time is realistic. What is not realistic as written is operational continuity: the serving build sits in a directory that does not survive a reboot (F13), 10 to 25 pushes per trial hour go through a shared working tree (F15), every anchor is blocked by the scanner (F1), and a defect found in T4 has no regulated path (F2). Harness construction (15 new modules, mock server, chaos runs, verifier) and the wait for the root are the dominant calendar cost and are not estimated anywhere in the protocol.

---

## D. Minimum content of v2 for re-audit

1. Identifier-free chain and a tested anchor path against the real remote (F1).
2. Freeze structure, defect procedure, T4 inspection list, corrected chronology wording (F2).
3. Two complete configurations A and B, dated cut-off, Appendix B for both (F3).
4. Rewritten purpose and claim lists: full queue quote, retained limitation, no percentage of exposures, margin in the action label, corrected impossibility wording (F4-F7).
5. R4 re-run for the frozen configurations with counts, Wilson intervals, T3 and T4, corrected `N_P`, plain-expectation table with a go/no-go sentence per cell (F8).
6. T3: truthful rationale, no same-vendor fallback under the T3 label, format-conformance check, contamination and sharing sentences, D6 sent to the root (F9).
7. Failure rules without outcome re-draws; tested counter semantics; pinned server manifest; timestamp wording; dedicated clone; decision table for pauses; operator disclosure (F11-F16).
