# live_ab: prospective, OS-entropy randomized, single-exposure, live-stopped laboratory A/B trials with open-weight models

**Protocol draft v2 (2026-09-19). Status: DRAFT, not frozen. No design episode has been run. v2 replaces v1 completely; it is not a diff.**
Intended location after review: `experiments/live_ab/protocol.md` on branch `session60/live-ab`; results under `results/live_ab/<trial>/`.
This document becomes binding only through the program freeze of section 12.1. The accurate chronology phrases are "internally frozen, externally timestamped" (never "preregistered" without that qualifier, never "publicly" unless the repository is public, section 11.4) and "frozen before any design-task outcome of the program" (never "before any model call": out-of-design smoke and calibration calls happen before the freeze and are tagged as such, section 5.8).

Inputs: the v1 draft, the four reader reports `R1_accepted_method.md`, `R2_constraints_checklist.md`, `R3_harness_plan.md`, `R4_power_analysis.md`, the three audits `audit_v1_statistics.md` (S-F1 to S-F22), `audit_v1_provenance.md` (P1 to P25), `audit_v1_claims.md` (C-F1 to C-F26 and its section B), R4's `power_sim.py` and `power_results.csv`, the v1 drafter's `P5_supp_power.*`, and the reviser's interim planning simulation `P6_v2_planning.py` with outputs `P6_v2_planning.json` and `P6_v2_planning.md` (SHA-256 prefixes in Appendix F). The disposition of every audit finding is in `audit_response_v1.md`. Root references are cited as `file:line` at root main `955579d` (paper and `src/winstats.py` byte-identical to the merged `410b158`; `src/winstats.py` SHA-256 `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69`).

Label convention: **incumbent** and **candidate** (never the letters A/B for arms, because `paper/main.tex` calls the candidate A while `paper/open_coding_appendix.tex` calls it B). Scores are always computed as `compare(candidate, incumbent)`: positive favours the candidate. The letters **A** and **B** are used in this protocol only for the two complete monitoring configurations of section 8.

The operator of the trials is an **AI agent session** (session 60) working under the repository owner's account, with read access to every file of the run. Every procedural safeguard below is written with that fact in view, and the reports say so (section 12.5).

---

## 0. Register of decisions and of items needing confirmation

### 0.1 DECISIONS taken in this draft (each is argued where it is used; "v2" marks a change against v1)

| id | decision | section |
|---|---|---|
| D1 | Randomization unit = disjoint pair of consecutive arrivals; ONE fair OS-entropy orientation coin per pair; every task is still executed under exactly one arm. Departs from the coordinator's wording "coin per arrival". | 4.1 |
| D2 | Live OS entropy with a write-ahead, hash-chained, externally receipted log; NO pre-drawn tape, NO seed, NO commit-reveal key. v2: the coin is described everywhere as "operator-attested; not independently verifiable". | 4.3 |
| D3 | Two concurrent workers, **pair-synchronous** in the randomized phase. Work-conserving two-worker loop after a decision. v2: the sliding-window fallback of v1 is deleted; if pair-synchronous execution is declined, nothing is frozen and a new protocol version is written and audited. | 5.1, 7.5 |
| D4 | Serving = `llama-server` (llama.cpp commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d`), GGUF Q4_K_M, one process per model, `-np 2`. v2: the freeze pins the launcher **and every linked library** by a manifest; the build lives in a durable directory. | 2.2 |
| D5 | T3 candidate model = IBM Granite 3.3 8B Instruct (Apache-2.0). v2: **no fallback model**. If the candidate fails any preflight rule of 2.4, T3 is not run and is reported as deferred. | 2.4 |
| D6 | Hierarchy: T1, T2, T4 use the accepted coding hierarchy success > latency (10%) > completion tokens (10%); T3 uses success > latency (10%). v2: every T3 composite statement carries the regime label "latency under cross-process GPU sharing on this host" and is shown beside the success-only composite with equal prominence. | 6.2 |
| D7 | v2: roster = S1 (591 pilot-roster tasks) plus every S2 task (MBPP-full-only) that survives the outcome-blind rules of 3.2, if the download is approved; else S1. No size threshold and no dependence of any rule parameter on the roster. | 3.3 |
| D8 | Pairs are formed inside outcome-blind baseline strata. v2: configuration A uses four strata (pilot pattern k2 / k1 / k0, and S2); configuration B uses the two source strata (S1, S2) only. | 3.5 |
| D9 | v2: exactly two complete monitoring configurations exist. **A** = split fixed-grid betting gates (`winstats.betting_log_e_ternary`, `prop:bet_running` + `thm:drift_gate`). **B** = split normal-mixture confidence sequences (`winstats.normal_mixture_radius`, `thm:normal_cs` + `thm:drift_gate`), which is the root's retained coding analysis made prospective and joint. A is frozen only if the root confirms it literally and in writing before the cut-off; any refusal, partial answer or silence freezes B. | 8, 12.1 |
| D10 | A prespecified **unfavourable-composite gate** (v1 name "harm gate"; renamed because 1.4 forbids harm language). A: betting on `-Z` at level `alpha_U`. B: upper endpoint of the two-sided net-benefit band below 0. Action label `RETAIN_INCUMBENT (unfavourable composite signal)`. | 8.3 |
| D11 | v2 error budget. T1 and T2 test one contrast with the roles exchanged and share 0.05: 0.025 per trial. T4 is the control of that same rule and uses the same levels (0.025). T3: 0.05. Program-wide union bound over the four decisions: 0.125. The secondary construction is a separate family with its own level; the union over both families is stated wherever both appear. | 8.4 |
| D12 | v2: one success margin `delta = 0.10` in every configuration and on every roster, labelled "laboratory demonstration margin, chosen with knowledge of the pilot and of the planning power; not application-justified". The paper's 0.03 is logged beside every S-gate statement. | 8.1, 10.4 |
| D13 | `n_min = 20` pairs; one look per completed pair; no retained crossings; no running intersection. | 8.2 |
| D14 | The live decision uses the **completed enrollment prefix** (`prop:delay`). The partial-information enclosure statistic is recorded as a measured timing comparator; it never drives traffic and carries no error-control claim. | 7.3, 8.6 |
| D15 | v2: the workflow of an episode is never cut short by a decision, a pause or an operator. The only event that ends an attempt before its workflow ends is the frozen episode hard cap, which is a terminal endpoint (failure), never a re-run. | 5.5, 6.4, 8.7 |
| D16 | After a decision every remaining arrival of the frozen order is executed under the decided arm; this phase is an operational record, outside all inference. | 8.7 |
| D17 | Sampling: temperature 0.7, top_p 0.95, top_k 0, min_p 0.0, max_tokens 1024 per call, `cache_prompt: false`, `stream: false`; neutrality of every other sampler is proven by the frozen golden receipt object, not asserted. | 5.3, 5.7 |
| D18 | v2: per-request seeds are **drawn from OS entropy at request time**, unique across the program, logged before the POST. Index-determined seeds (v1) are dropped because they make potential outcomes rehearsable from the frozen bundle. | 5.4 |
| D19 | v2: `max_attempts = 1`. **No re-run of any kind**: no episode retry, no attempt re-run, no fresh sampling of any call. An attempt that does not return is revealed as a failure endpoint. A finished but unrevealed episode is recovered only under the strict orphan rule. HTTP connection retries (2) are part of the system definition and are reported by arm. | 5.5, 6.4, 12.3 |
| D20 | v2 anchoring: every anchor obtains a server-side receipt that is chained back into the log; anchors at trial start, decision, pause, resume, amendment and trial end **block**; during the randomized phase only anchor files (no coins, no outcomes) are committed; log segments are published at the decision and at the trial end. RFC 3161 timestamp tokens for the critical heads if approved. | 11.4 |
| D21 | Execution order T4, T2, T1, T3. v2: **one program freeze**; all statistical and execution parameters of all four trials are immutable from the first design-task outcome of the program; every trial is started unconditionally; no trial is repeated. | 12.1, 12.4 |
| D22 | Closed-loop arrivals; no arrival clock. | 5.1 |
| D23 | T2 is described as "costly candidate with equal pilot success", not "harmful candidate". | 1.2 |
| D24 | v2 operational quantities: the decision prefix `tau`, the switch latency, and the count `M` of pairs not enrolled (always with the sentence that `M` is determined by the prespecified roster length). `M / N_P` and every percentage of exposures avoided are not computed. The time/token projection is a labelled descriptive item. | 9.4 |
| D25 | Arrivals are a fixed permutation of a finite roster, so the targets are running averages and the split-level, same-prefix, no-retention rule of `thm:drift_gate` applies. | 8.5 |
| D26 | v2: a host-wide execution lock lets at most one generated program run at any time, which restores the one-program-at-a-time regime for which the sandbox and the verifier were audited; a containment probe under two workers is part of the freeze bundle. | 5.6 |
| D27 | v2: every worker keeps an fsynced append-only spool (request line before the POST, response line before use); the orchestrator ingests the spools; the spools are the recovery source for accounting. | 5.1, 11.5 |
| D28 | v2: the decision rule exists twice: the live monitor and a frozen **reference rule** (used by verifier and builder, never amendable). If the two disagree in kind or prefix, the trial result is `LIVE_DECISION_INVALID (harness defect)`. | 9.2 |
| D29 | v2: the event chain is identifier-free by construction (numeric ids and hashes only; identified receipts in a private side file that is hashed into the chain). The released chain is byte-identical to the raw chain; no sanitized copy of the chain is ever produced. | 11.2, 13.2 |
| D30 | v2: trials and anchors run from a dedicated clone that nothing else uses. | 11.4 |
| D31 | v2: root consultation with a dated cut-off (72 hours after the issue is posted); Block I selects A or B; a written objection to a Block II item stops the freeze. | 12.1 |
| D32 | v2: the list of non-amendable items covers every statistical parameter, every execution parameter of 5.5, `W`, server arguments and sampling; a defect is repaired only through the harness-only re-freeze of 12.2. | 12.2 |
| D33 | v2: after T4 (and after every trial) only the plumbing inspection list is produced; the builder and every outcome table are run after the last trial has ended. | 12.4 |
| D34 | v2: `stream: false` is kept (deviation from R2 item 50, justified in 11.5); counter windows are one pair wide; the counter semantics for cancelled requests are tested before the freeze and fix the accounting wording. | 11.5 |
| D35 | v2: integrity events are tabulated by the verifier; a trial with a coin-adjacent integrity event, or with three or more pairs containing an interrupted episode, is labelled "integrity-qualified" in every table. | 11.6 |

### 0.2 Items marked CONFIRM (all are collected again, with what is needed from whom, in the final section "Items for the coordinator")

| id | who | item | default if confirmed | consequence otherwise |
|---|---|---|---|---|
| C1 | coordinator | D1: pair-orientation coin instead of per-arrival coin | pair coin | none available: per-arrival coins have no accepted score (`thm:pair_id` does not cover them) |
| C2 | coordinator and root (Block II) | D3: pair-synchronous two-worker execution, with the narrowed claim of 1.3(5) and the statement that this is not a study of monitoring under delay | accepted | no freeze; a sliding-window design needs its own protocol version, power analysis and audit |
| C3 | root (Block I, RA1) | configuration A: split same-prefix fixed-grid betting gates as the live driver | A | B |
| C4 | root (Block I, RA2) | A's unfavourable-composite gate = `prop:bet_running` applied to `-Z` at `alpha_U`, used as a stopping action | A | B |
| C5 | root (Block I, RA3) | A's levels: 0.025 per trial for T1, T2, T4 split (0.0025, 0.02, 0.0025); 0.05 for T3 in equal thirds; bounds 0.05 for the T1/T2 contrast and 0.125 for the program | A | B |
| C6 | root (Block II), user, coordinator | D12: `delta = 0.10` as a labelled laboratory demonstration margin | 0.10 | written root objection: no freeze |
| C7 | root (Block I, RA4) | A's pairing within pilot-pattern strata (baseline covariate; `paper/main.tex:171-172`, `paper/theory.tex:238-245`) | A | B (source strata only) |
| C8 | root (Block I, RA5) | the pair-level analogue of `thm:pair_id` under concurrent within-pair execution (7.4) | reading stated as confirmed by the root | B; the reading is then printed as "session-60 reading, not confirmed by the root" |
| C9 | user | downloads in the pre-freeze phase: pinned `mbpp.jsonl` (expected 563,743 bytes), Granite GGUF (about 5 GB), LICENSE files of the model repositories | approved | roster S1; T3 deferred |
| C10 | user | `git push` of anchor commits, commit or issue comments through `gh` from the user's account during runs, and an anchor drill against the real remote (drill branch and drill issue) before the freeze | approved | local-only mode: no external chronology after the freeze, no amendment can take effect (any event that needs one aborts the trial), claims narrowed as listed in 11.4 |
| C11 | coordinator | provenance of the cached `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` file (appeared in the cache on 2026-09-19); hash recomputed at preflight | as recorded in 2.3 | re-download at the pinned revision |
| C12 | coordinator | **mandatory, no fallback**: re-run of R4's simulator on the exact frozen configuration (10.5) | done before the freeze | no freeze |
| C13 | root / author | code licence of the harness for the arXiv release | decided by author | release without a licence statement, which means all rights reserved, and the release note says so |
| C14 | coordinator | branch `session60/live-ab` created from current root main by merge, never rebase; a dedicated clone for the run | done | - |
| C15 | coordinator | exact Hugging Face repository id, file name, revision and SHA-256 of the Granite GGUF (pinned at download; file-selection rule in 2.4) | pinned pre-freeze | T3 deferred |
| C16 | root (information item) | error control of the partial-information betting statistic under the running-average null is an unwritten one-line corollary | - | none: the comparator is a measured timing comparison without error-control claim in every case |
| C17 | user | RFC 3161 timestamp tokens for the freeze bundle hash and for the start, decision and end heads of every trial (network call to a public timestamp authority that receives a SHA-256 only; `openssl ts` and `curl`, no installation) | approved | the chronology wording carries the sentence "timestamped by GitHub comments that the account owner can edit or delete; `updated_at` was recorded" wherever it appears |
| C18 | coordinator | coin source: OS entropy is the fixed design intent and the default. A public randomness beacon would remove reliance on the operator only if every enrollment were externally timestamped before its beacon round (one blocking receipt per pair). Offered as an option, not adopted (4.3). | OS entropy | new protocol version |
| C19 | user | visibility of the GitHub repository and of the issue (public or private), recorded in the freeze record | stated | - |
| C20 | user / coordinator | retention of the private evidence archive (proposal: at least three years after the arXiv posting; given to the root and to reviewers on request); archiving of the operator session transcript (hash only in the delivery) | approved | the report states that success labels cannot be re-verified by third parties |
| C21 | coordinator | cut-off of the root consultation: 72 hours after posting | 72 h | other fixed duration, set before posting |
| C22 | coordinator | D11: contrast-level budget (0.025 per trial for T1, T2, T4) instead of 0.05 per trial with a stated 0.10 contrast bound | 0.025 | new protocol version (both were acceptable to the auditor; the more conservative one was taken) |
| C23 | coordinator | D19: `max_attempts = 1` instead of a byte-identical replay continuation after a harness interruption | 1 | new protocol version |
| C24 | coordinator | D5: no T3 fallback model | none | new protocol version |
| C25 | root (Block II, RB4) | D6: T3 hierarchy with side-by-side latency as the only resource tier | accepted | written objection: T3 deferred (the other trials are unaffected) |
| C26 | coordinator | whether an anonymous variant of the hand-off is still a deliverable now that the target is arXiv (13.2); the chain itself is the same in either case | one identified variant plus an identifier-free chain | - |
| C27 | coordinator | a prespecified fixed-sample comparator `n_fixed` for a relative efficiency statement was suggested by the statistics auditor as optional; it is NOT included (9.4) | not included | new protocol version |

---

## 1. Purpose, scope and claims

### 1.1 Purpose and scope

The root's `EXPERIMENT_QUEUE.md` (line 37 at `955579d`) lists, in full: "Conditional experiment | Concurrent open-model prefix study with actual reveal timestamps; prospective randomized exposure trial | Required for measured operational savings or live-deployment claims, which this paper does not make." The root's gap assessment (`reviews/round9_experiment_gap_assessment.md:35`) says, for an operational latency claim: "A future open-model concurrent run with actual reveal timestamps, nonanticipating certificates, fixed endpoint horizons and the matched completed-prefix comparator could address this gap. Specify the target and shared-resource assumptions first. Until then, retain the present 'feasibility, not operational latency savings' limitation."

What `live_ab` delivers against that entry:

1. a **prospective randomized exposure trial**: four trials on one Apple M5 (32 GB) with open-weight models on the loopback interface, one program freeze before the first design-task outcome, a fresh operating-system-entropy coin per arrival pair, single exposure, a monitoring rule that is fixed in advance and that changes the traffic of a laboratory dispatcher when it crosses;
2. **actual reveal timestamps** with two concurrent workers and out-of-order reveals inside a pair, the nonanticipating certificates of 7.6, fixed endpoint horizons, and the matched completed-prefix comparator, with **at most one pending pair** at any time.

What it does **not** deliver, stated before any data exist:

- no evidence about the value of partial-information monitoring under substantial delay: by construction the comparator and the live rule differ by at most the remaining duration of one episode (8.6); this is not a study of monitoring under delay;
- no measured time or token saving: the only exact operational quantities are the decision prefix, the switch latency and exposure counts; every time or token "saving" is a labelled projection (9.4);
- no deployment claim of any kind: the "deployment" is a switch inside a laboratory dispatcher on benchmark tasks.

Therefore, even after a fully successful program, the manuscript still may not say "measured operational savings", "operational latency savings" or "live deployment", and **the paper's limitation "feasibility, not operational latency savings" is retained**. The exact sentences the trials could add to the manuscript are listed per outcome in Appendix E.

In each trial:

1. tasks arrive in a prespecified order; consecutive arrivals form disjoint pairs;
2. when a pair is enrolled, a fresh fair coin from operating-system entropy fixes which arrival receives the candidate; the coin is durably logged before either episode is dispatched; each task is executed under exactly one arm, once;
3. the two episodes of the pair run concurrently on two workers; their outcomes are revealed out of arrival order with recorded timestamps;
4. a monitoring rule that was fixed before the first design-task outcome of the program is evaluated at every completed pair on the enrollment-order prefix;
5. when the rule crosses, the dispatcher changes the traffic: all remaining arrivals run under the decided arm; nothing is replayed.

The 1,182 delivered coding episodes (`results/local_stream/`) are **pilot data**. **Every one of the following was chosen with knowledge of pilot outcomes of the same tasks:** the hierarchy, the tolerances, the margin `delta`, the strata of configuration A, the unequal level allocation of configuration A, the hypothesis directions, `n_min`, the execution order of the trials, the label of T2, and the decision to run T1 and T2 at all. This sentence accompanies every result of every trial. No pilot episode enters any trial table.

### 1.2 The four trials

| trial | incumbent | candidate | what is known in advance | planning expectation (section 10; configuration A / B) |
|---|---|---|---|---|
| T1 "cheap candidate" | `self_test_repair` on Qwen2.5-Coder-7B | `single_shot` on the same model | pilot on the same 591 tasks (MLX stack): equal success 433/591, candidate 4.46 times faster | the net-benefit gate crosses early; a `DEPLOY_CANDIDATE` decision needs the S gate as well: planning probability under A at pilot predictiveness 0.7: 0.61 to 0.79 on EXT and 0.44 on S1 (lower if the candidate is truly worse); under B 0.06 or less, so that T1 is then expected to abstain (10.3) |
| T2 "costly candidate with equal pilot success" | `single_shot` | `self_test_repair` | mirror image of T1: the same two systems with the roles exchanged | the unfavourable-composite gate crosses, incumbent retained; T2 adds a live switch, **not a second estimate** of the T1 contrast |
| T3 "model swap" | `single_shot` on Qwen2.5-Coder-7B | `single_shot` on Granite 3.3 8B Instruct | nothing produced by this harness; published aggregate benchmark pass rates were used to choose the model (2.4) | unknown; abstention is likely unless the composite effect is large (10.3) |
| T4 "A/A control" | `single_shot` on Qwen2.5-Coder-7B | the identical system | exact null by construction | no decision; a decision has probability at most 0.005 (A) or 0.0125 (B) under the exact null |

T1 and T2 are confirmatory demonstrations of live operation of a frozen rule on a contrast whose pilot answer is known on the same tasks; this is disclosed wherever they are reported. **T1 and T2 are never cited as two confirmations or as a replication**; the bound for any false decision statement about their common contrast is 0.05 (8.4) and is printed next to every joint mention. Scope of T4: because the two arms are one system and nothing in the harness depends on the arm label, T4 checks the coin path and label blindness only; it cannot reveal any arm-dependent defect (retry, timeout, routing), because there is no arm difference to depend on.

### 1.3 Claims the trials MAY support (each only if literally true at the end; "N" is always the computed count of executed arrivals)

1. "An internally frozen, externally timestamped [on a public / private GitHub repository, as recorded], single-exposure, live-stopped laboratory A/B trial on N fixed benchmark tasks with open-weight models on one Apple M5; the arm of each arrival pair was assigned by the operating-system CSPRNG at enrollment and logged before execution (no stored seed; operator-attested, not independently verifiable)."
2. "The monitoring rule was configuration [A: the fixed-stake betting construction / B: the split normal-mixture confidence sequences] of `src/winstats.py` at SHA-256 56955ce0..., with all levels, thresholds, the hierarchy, the margin and the horizon frozen before the first design-task outcome of the program. Under adaptedness and boundedness of the scores, the probability that the rule issues a deploy decision at any enrolled prefix at which a running conditional-mean criterion is false, or a retain decision at a prefix at which the running conditional-mean net benefit is nonnegative, is at most [0.025 / 0.05] in that trial." If the trial ran after a harness-only re-freeze, the sentence adds "harness files were changed after N program outcomes by the procedure of 12.2; no rule parameter changed".
3. "In trial Tk the rule crossed at enrolled pair n; the decision event was externally receipted at server time t; the dispatcher switched; the remaining M arrivals ran under the decided arm in the laboratory dispatcher, on this host and under this serving regime." A measured event, not a replay. Restricted to the arrivals that actually ran (11.3).
4. "The decision was taken at enrolled pair tau; M pairs of the prespecified roster were not enrolled (M is determined by the prespecified roster length N_P); measured wall-clock and token totals of the run on this host under this serving regime were ...". Any time or token "saving" is outside this claim and is labelled a projection (9.4).
5. "Outcomes were revealed out of arrival order with recorded timestamps; with at most one pending pair, the completed-prefix rule and the partial-information enclosure statistic reached their crossings at times t1 and t2; by construction the two differ by at most the remaining duration of one episode; this is not evidence about the value of partial-information monitoring."
6. "Failure-inclusive usage accounting reconciles client and server counters to within X tokens [wording fixed by the pre-freeze counter test, 11.5]; the sampling parameters as parsed by the server were recorded for every request and equalled the frozen golden object."
7. T2: "the prespecified rule rejected the candidate (unfavourable composite signal); the incumbent was retained". T4: "in one A/A control path no gate crossed" (or, if one did, it is reported as the rare event it is). T3: whatever happens, including abstention and deferral.
8. "The success-difference gate at the laboratory demonstration margin 0.10 (chosen for feasibility with knowledge of a zero same-task pilot difference; not application-justified) crossed / did not cross; at the paper's margin 0.03 the statistic was ... and did / did not cross"; non-crossing is abstention.
9. Wherever two or more trials appear in one table, abstract or paragraph: "each trial has its own error budget; the union bound over the four decisions is 0.125 (0.05 for the T1/T2 contrast)".

### 1.4 Claims that are FORBIDDEN in any report, index, PR text or manuscript sentence derived from these trials

1. Production A/B evidence, user benefit, deployment safety, or "deployed" without "in the laboratory dispatcher"; "measured operational savings", "operational latency savings", "live deployment".
2. A population, fixed-roster (theta_N), superpopulation or fresh-task effect; iid-task inference; the word "independent" for pairs or episodes.
3. Empirical calibration or type-I-error control from one or four streams; "holds its level"; "error rate is zero".
4. Equivalence or non-inferiority from equal or similar success counts. Only a crossing of the S gate at the frozen margin is called non-inferiority, and then always "at the laboratory demonstration margin 0.10 for the running target". A crossing of a side margin (8.10) is never reported as non-inferiority at that margin.
5. "Approval of the incumbent", "the incumbent satisfies the guardrail", success harm or safety harm from an unfavourable-composite crossing. The words "harm gate" do not appear in any tracked artifact.
6. Joint 95% coverage from marginal bands; a "two-sided 95%" object from two one-sided processes; a program-wide alpha when each trial used its own; a simultaneous statement over the decision and the secondary family without the stated union.
7. Significance of resource differences; t, Welch, cluster-t, bootstrap or delta-method intervals; win-ratio confidence sequences; anything from `src/wincs.py`.
8. Hardware-, model-, workload- or tokenizer-invariant rankings; dollars, energy or "compute" from token counts; cross-model token comparisons as cost. For T3: any statement about either model's latency when served alone or beside itself.
9. A causal assignment-average reading without naming the coin model, the filtration, the concurrency regime and the assumptions listed in 7.4 (including "no dependence of a task's record on later coins" and "operator does not act on coins").
10. Measured time or token savings derived from counterfactual or replayed paths; per-task "operational cost" from retained-only totals; `M / N_P` or any percentage of exposures avoided, anywhere; any wall-clock, throughput or per-episode latency comparison across the two phases of a trial (they use different schedulers).
11. "Preregistered" without "internally frozen, externally timestamped"; "publicly timestamped" if the repository is private; "before any model call".
12. Bit-reproducible generation; independent re-adjudication of success labels; exhaustive correctness. Success is the archived verifier label.
13. "Assumption-free", "impossible for any method", "not certifiable", "cannot be certified at this sample size", "conservative" without conditions, mechanism claims from post-crossing diagnostics. The permitted sentences are "this prespecified rule did not certify margin delta on these data" and, for planning, "for this rule, this allocation and this roster the planning probability of a crossing is about p".
14. That post-decision single-arm data validate, contradict or refute the decision, or predict future benefit. Post-decision rates are not compared with pre-decision rates of either arm.
15. That the hierarchical rule is generally better than component rules.
16. That the root "approved" the trial, the PR or the methods beyond what a root disposition literally states. Owner-side verification is AI review by a separate code path of the same session, not human peer review, not independent verification, not author sign-off, and says so.
17. Mock or dry-run outputs cited as observations.
18. Asynchronous-monitoring gains; "early certificates" as a benefit; any reading of `t_dec - t_enc` beyond "bounded by one episode by construction".
19. The word "guarded" (guarded deployment, guardrail passed) without the margin in the same sentence.
20. T1 and T2 as two confirmations, a replication, or two estimates.
21. "Physically randomized" without the qualifier of claim 1; "verifiable coin"; "tamper-proof log". The permitted description of the log is in 11.4 ("what the anchors prove and what they do not").
22. Differences between strata, phases or periods attributed to one cause; the permitted wording is "mixes ... and cannot separate them".

---
## 2. Systems

### 2.1 Hardware, host and working locations

One Apple M5 laptop, 32 GB unified memory (34,359,738,368 bytes), macOS 26.5.2 (build 25F84) at drafting time. The exact chip string, memory, OS build and power state are read from an allowlist at every invocation and logged; nothing else about the host is recorded (no user name, no host name, no process listing). During a trial: mains power, `caffeinate` active, no other GPU job, exclusive lock file, preflight scan of the two service ports; the harness refuses to attach to a server it did not start. Hardware and runtime are printed next to every resource table; no hardware-invariant statement is made.

Locations (tokens in every tracked artifact): `<CLONE>` = a dedicated clone of the repository used by nothing but the trials and their anchor process (D30); `<WORK>` = a git-ignored directory inside `<CLONE>` for private evidence, weights links and the serving build; `<HF_CACHE>`; `<LLAMA_BUILD>` = `<WORK>/llama.cpp-build`. Preflight asserts that the real paths of `<WORK>`, `results/`, the task files (including the future `mbpp.jsonl`), records, request bodies, spools, server logs and `<LLAMA_BUILD>` lie under the home directory, because the Seatbelt profile of the sandbox is allow-default and denies reads and writes only under the home directory and the temp trees (5.6). Preflight also checks free disk space (at least 20 GB) and that `<WORK>` is git-ignored.

### 2.2 Serving software (D4)

`llama-server` built from llama.cpp commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d` (the commit already frozen in `experiments/tau2_open/config.json`). On this host `build/bin/llama-server` is a 33 KB launcher that links through `@rpath` to nine libraries (`libllama-server-impl`, `libllama-common`, `libmtmd`, `libllama`, `libggml`, `libggml-cpu`, `libggml-blas`, `libggml-metal`, `libggml-base`), which hold all sampling, scheduling and Metal code; the existing build sits in a session temp directory that does not survive a reboot. Therefore, before the freeze:

1. the checkout is built (or rebuilt) into `<LLAMA_BUILD>`; `git status --porcelain` of the checkout must be empty and is recorded; the cmake options, compiler version, SDK version and the SHA-256 of the configure and build logs are recorded;
2. the **serving manifest** = SHA-256 of the launcher, of every non-system library that `otool -L` resolves recursively, and of the Metal library (embedded or external), together with the resolved rpath; the manifest is part of the freeze bundle and is re-verified at every invocation and at every server start and restart;
3. `/props.build_info` must contain the commit prefix.

Wherever v1 said "binary hash", this protocol means "launcher and libraries (serving manifest)".

Reasons for not using the pilot's `mlx_lm.server` 0.31.3 (R3, section 0): it routes every request that carries a seed to a single-request path and drains running batches, so two workers would only queue; it returns no sampler settings; its `model` response field is an echo of the request. `llama-server` returns, with the request field `"verbose": true`, the object `__verbose.generation_settings`, `id_slot`, token counts and the rendered prompt; `usage` and `timings` are returned in the non-streamed response; `model` is the server-side alias; `/metrics` exposes cumulative token counters. All of this was read from source by R3 and the provenance auditor; it is **proven on the real server in the pre-freeze phase** (5.8), and the consequence of a failed proof is fixed there.

Frozen launch line, one process per model:

```
llama-server -m <HF_CACHE>/<gguf file> --alias <alias> --host 127.0.0.1 --port <port>
  -np 2 -c 16384 --no-kv-unified -ngl 99 --jinja --metrics --no-context-shift --offline
  --log-file <WORK>/live_ab/<trial>/logs/llama_<port>.log --log-timestamps
```

`-np 2` equals the number of workers, so no request waits for a slot; `--no-kv-unified -c 16384` gives each slot 8,192 tokens (pilot maximum summed over a `self_test_repair` episode: 3,934 prompt and 1,474 completion tokens); `--no-context-shift` turns an overflow into a visible truncation; `--offline` forbids network access. Ports: 8091 (Qwen2.5-Coder), 8092 (T3 candidate). T1, T2, T4: one resident server for the whole trial. T3: both servers resident for the whole trial including the post-decision phase (serving arrangement identical for both arms). Because GGUF Q4_K_M under llama.cpp is a different quantization and kernel path from the pilot's MLX 4-bit build, all pilot numbers are planning numbers only.

### 2.3 Models

| role | base model (licence) | GGUF repository, revision | file | bytes | SHA-256 |
|---|---|---|---|---|---|
| T1, T2, T4 both arms; T3 incumbent | `Qwen/Qwen2.5-Coder-7B-Instruct` (Apache-2.0) | `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` @ `13fb94bfda8c8cf22497dc57b78f391a9acb426a` | `qwen2.5-coder-7b-instruct-q4_k_m.gguf` | 4,683,073,536 | `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c` (content-addressed cache blob name; recomputed at every preflight) CONFIRM C11 |
| T3 candidate | `ibm-granite/granite-3.3-8b-instruct` (Apache-2.0) | `ibm-granite/granite-3.3-8b-instruct-GGUF` @ revision pinned at download (repository existence not yet checked: the drafter and the reviser had no network access) | selected by the file rule of 2.4 | pinned at download | pinned at download CONFIRM C15, C9 |

Aliases: `qwen2.5-coder-7b-instruct-q4km`, `t3-candidate`. The alias is a name the harness gives on the command line, so an alias check alone proves only that the process answers under its given name. Model identity is therefore checked at every server start and restart by: the real path of `/props.model_path` equals the hashed GGUF; the GGUF SHA-256 is recomputed; the GGUF metadata reported by the server (`general.name`, parameter count, vocabulary size) equal the golden `/props` object (5.7). The `model` field of every response must still equal the arm's alias.

Licence evidence ("open weights alone do not establish an unrestricted licence"): for every model the freeze bundle records repository id, revision, and the SHA-256 of the LICENSE file at that revision, or, where the repository has only a model card, the literal statement "licence declared on the model card only" plus the base-model repository, its revision and its LICENSE hash. Models under a Qwen research, Llama, Gemma, OpenRAIL or "research/non-production" licence are not eligible. No API key is read; the HTTP client hard-asserts a loopback base URL; preflight fails if an API-key environment variable is present; there is no LLM judge (success is the executable verifier). The live runner shares no entry point and no import with the historical commercial collection scripts of the repository, which are provenance only.

Memory: 4.7 GB (coder) + about 5 GB (Granite Q4_K_M) + KV caches of at most 2.6 GB per server at 16k context; inside 32 GB.

### 2.4 Choice of the T3 model (D5, CONFIRM C24)

Requirements: (i) Apache-2.0 or MIT weights; (ii) a different model family from Qwen (vendor, tokenizer, training data); (iii) parameter count close to the incumbent's 7.6 B, so that the latency tier is not decided by size alone; (iv) a GGUF published by the licensor, so that licence evidence is first-party; (v) a dense transformer supported by the pinned llama.cpp commit with its embedded chat template under `--jinja`; (vi) instruction-tuned, with vendor-published code-generation pass rates of the same order as the incumbent's.

**Honest status of (vi):** published code-generation ability of instruction models is reported as HumanEval and MBPP pass rates, and those benchmarks are the design roster. Criterion (vi) is therefore **outcome-informed at the aggregate level**. The correct statement is: "no outcome produced by this harness was used; vendor-published aggregate pass rates on the same public benchmarks were used for criterion (vi)". The numbers and their sources are recorded in the freeze bundle during the pre-freeze phase (the reviser quotes none, having no network access). Granite 3.3 8B Instruct meets (i) to (v) on the information available (8.2 B parameters, Apache-2.0, IBM-published GGUF; to be verified at download). Models that were considered and fail a non-outcome criterion: `microsoft/phi-4` (14 B, criterion iii), `microsoft/Phi-4-mini-instruct` (3.8 B, criterion iii), `01-ai/Yi-Coder-9B-Chat` (no first-party GGUF, criterion iv), DeepSeek-Coder, Code Llama, StarCoder2, Gemma (criterion i). `mistralai/Mistral-7B-Instruct-v0.3` fails only the outcome-informed criterion (vi) and is listed as such.

Preflight rules for the candidate (all evaluated before the freeze from preflight facts only):

1. **File rule.** The repository at the pinned revision must contain exactly one file whose name matches `*[Qq]4_[Kk]_[Mm]*.gguf` and is not a split part (`-0000N-of-`); zero or several matches fail the rule.
2. **Licence rule.** Licence evidence as in 2.3 can be recorded.
3. **Template rule.** The server starts with `--jinja` without a template error or warning in its log; `/props.chat_template` is non-empty; for the reference request the rendered prompt (`__verbose.prompt`) contains the system text and the user text exactly once each, in that order, and ends with the template's assistant generation prefix; the response content contains no template control token.
4. **Receipt rule.** The receipt smoke test (5.7) passes.
5. **Format-conformance rule (outcome-blind).** On the ten out-of-design prompts of 5.8, at least 9 of 10 responses of each model must contain a code block that `extract_code` extracts to a non-empty program. Correctness of the program is neither computed nor looked at. The prompts and the extractor were developed on the incumbent's model family and are not changed.

If any rule fails, **T3 is not run**; it is reported under its own heading as "deferred: candidate failed preflight rule k". There is no fallback model (v1's same-vendor 4 B fallback violated criteria ii, iii and iv and would have decided the latency tier by size). Both T3 arms use `single_shot`. Every T3 statement carries: "prompts and the code extractor were developed on the incumbent's model family; the two model families may differ in their exposure to these public benchmarks, and this contrast cannot separate ability from contamination".

### 2.5 Arms

| trial | incumbent | candidate | servers |
|---|---|---|---|
| T1 | workflow `self_test_repair`, coder model | workflow `single_shot`, coder model | 8091 |
| T2 | `single_shot`, coder | `self_test_repair`, coder | 8091 |
| T3 | `single_shot`, coder | `single_shot`, T3 candidate model | 8091 + 8092 |
| T4 | `single_shot`, coder | `single_shot`, coder (identical system; the arm label is the only difference; the verifier confirms that the job payloads of the two arms are byte-identical apart from the label) | 8091 |

Workflows are the delivered, audited ones: `experiments/local_stream/agent.py` (SHA-256 `3cf2056330c72ebd5d2884f48d6ec2daa706fcc685ad67e3c2609d809ff75b64`), `sandbox.py` (`d461570937ddbe1fb241288721a1a06b44bd41dd72ccdc2e2ffa2f144184c6ff`), `verify.py` (`7473678b1990ca2a5a1900b45251fddcd2882f2b371d76d3a59fe669a607dbb6`), reused byte-identically through an injected model object; any byte change requires a new leakage and sandbox audit before the freeze. `single_shot` = one model call. `self_test_repair` = code call, test-writing call, execution of the agent's own tests in the Seatbelt sandbox, at most 2 repair calls; hidden tests never enter a prompt and the verifier gives no feedback to the agent. The legacy field `variant_letter` inside the reused record is ignored; the harness carries its own `arm` field in {`incumbent`, `candidate`}.

---

## 3. Task pool

### 3.1 Sources (pinned; mutable `master` URLs are never used)

| stratum family | source | pinned revision | file | bytes | SHA-256 | licence evidence |
|---|---|---|---|---|---|---|
| S1 | MBPP sanitized, all 427 problems (not a test split) | google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533` | `mbpp/sanitized-mbpp.json` | 255,053 | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` | the pinned file comes from the Apache-2.0 `google-research` repository; the CC-BY-4.0 statement comes from the dataset card, as recorded in `results/local_stream/data_manifest.json`; both facts are recorded literally |
| S1 | HumanEval, all 164 problems | openai/human-eval `463c980b59e818ace59f6f9803cd92c749ceae61` | `data/HumanEval.jsonl.gz` | 44,877 | `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef` | MIT (licence provenance recorded separately from the data revision) |
| S2 | MBPP full, problems not in the sanitized subset | google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533` | `mbpp/mbpp.jsonl` | **expected** 563,743 | **expected** `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` (measured once on the mutable `master` URL, never at the pinned revision; verified at download; a mismatch means roster S1) | as for S1 MBPP |

The S1 canonical task list is the delivered one (list SHA-256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`). The S2 file is not on disk; fetching it (one pinned URL, byte and hash check, refusal on mismatch) is a pre-freeze step that needs approval (CONFIRM C9). Raw third-party data stay outside git; `roster.json` holds uids, strata and exclusion reasons only, no task text (so no CC-BY change notice is triggered). `SOURCE_NOTICES.md` carries the attributions (Austin et al. 2021; Chen et al. 2021), llama.cpp (MIT) and the Python dependencies with their licences. A check asserts that every path named in any tracked mapping or manifest exists in the git tree.

### 3.2 Exclusions (all prospective and blind to every model output; the list with reasons is frozen in `roster.json`)

**Rule:** a task is excluded if any outcome of it on the **trial serving stack** exists before the freeze; pilot outcomes on the MLX stack do not exclude a task, they are disclosed and, in configuration A, used as baseline covariates (3.4).

1. The six timing-pilot tasks `mbpp_full/39, 122, 522, 547, 869, 966` (the out-of-design smoke and calibration tasks, 5.8).
2. S2 problems whose normalized prompt duplicates an S1 task (normalization of `experiments/local_stream/timing_pilot.py:35-36`); the S1 version is kept.
3. S2 problems whose entry point cannot be resolved by `mbpp_entry_point` (`experiments/local_stream/data.py:35-44`).
4. Any task whose reference solution does not pass `verify()` twice in a row inside the Seatbelt sandbox on the trial machine **under the load regime of the trial** (a generation of 1,024 tokens running on the coder server during the sweep), or whose reference verification takes more than half of the verifier wall limit (5 s) in either run. No model output about the task is involved.
5. Nothing else. No task is excluded for difficulty, length, or any model output.

### 3.3 Roster rule (D7; evaluated once, before the freeze)

If the download is approved and the file verifies, the roster is **EXT** = S1 plus every S2 task that survives 3.2; otherwise the roster is **S1**. No rule parameter depends on the roster: `delta`, the levels, `n_min` and the hierarchy are the same on EXT and on S1 (v1's switch of the margin at `n_S2 = 400` is removed). Arithmetic: MBPP-full-only = 974 - 427 = 547 problems; minus the six smoke tasks = 541; so `n_S2 <= 541` and EXT has at most 1,132 tasks before duplicates and sweep failures.

### 3.4 Why tasks that were used in the pilot are kept, stated without euphemism

1. Validity of every guarantee in section 8 rests on the scores being adapted, bounded and produced by a frozen rule, and the causal reading rests on fresh coins. Neither rests on task novelty. The pilot influences the trials only through design choices, which are frozen and disclosed (1.1).
2. **The reason for keeping the 591 pilot tasks while excluding the six smoke tasks is the rule of 3.2 (trial-stack outcomes exclude, MLX-stack outcomes are covariates), and the reason that rule was chosen is sample size:** holding out every pilot task would leave only S2 (at most 270 pairs). This is a power argument and is printed as one.
3. **Outcome knowledge inside the program.** T4 executes `single_shot` on the new stack on every paired task; T2's post-decision phase adds more. Before T1 starts, the operator therefore can hold new-stack outcomes of T1's candidate for essentially every task and a sample of T1's incumbent. The defence is not ignorance; it is the program freeze (12.1): nothing that defines any trial can change after the first design-task outcome of the program, every trial is started unconditionally (12.4), and between trials only the plumbing inspection list is produced (D33).
4. The claims are about this laboratory stream (1.3), not about fresh tasks; public-benchmark exposure of the models is disclosed and no contamination-free claim is made.
5. The disclosure of 1.1 (every pilot-informed parameter) accompanies every result of all four trials; in configuration A the strata are built from pilot outcomes and that sentence accompanies **every S-gate statement**; the S2 stratum is pilot-naive and its read-out is printed next to every S-gate statement. An unstratified-order counterfactual is not available and the report says so.

A task is executed at most once per trial and up to four times in the program. "Each trial uses the roster once" is true only of the paired arrivals up to the decision plus the post-decision phase; under `ABSTAIN_AT_HORIZON` the unpaired leftovers are not executed; N in every claim is the computed count of executed arrivals. The four trials are not independent replicates and are never pooled or described as such.

### 3.5 Strata and pairing (D8)

Configuration A (four strata; baseline covariates derived from `results/local_stream/episodes_flat.csv`, SHA-256 `1237b82f99c5ea8ad1e319e0ec45873ba85a2ff13d670d508d78ae06547bd540`):

| stratum | definition | tasks | pairs | unpaired |
|---|---|---|---|---|
| `S1_k2` | S1 task solved by both workflows in the pilot | 393 | 196 | 1 |
| `S1_k1` | solved by exactly one workflow | 80 | 40 | 0 |
| `S1_k0` | solved by neither | 118 | 59 | 0 |
| `S2` | MBPP-full-only task (no pilot data) | `n_S2` | `floor(n_S2/2)` | `n_S2 mod 2` |

Configuration B (two source strata): `S1` (591 tasks, 295 pairs, 1 unpaired) and `S2`. (Counts change only if 3.2 item 4 removes a task; the frozen `roster.json` is authoritative.)

Pairs are formed inside a stratum (`paper/main.tex:171-172`: "disjoint pairs of arrivals within a prespecified stratum"; `paper/theory.tex:238-245`). What the pair targets are is stated in 7.4 and 9.1; in particular the success target equals an average same-task effect **only under the additional condition** that a task's success does not depend on the partner's arm. For the hierarchical score the target is a within-stratum cross-task preference; it is not comparable in size with the pilot's unstratified value and no such comparison is made. If the pilot pattern predicts the new stack poorly, configuration A loses efficiency, never validity.

**Dilution, disclosed.** The only observations on S2-type tasks (timing pilot: 1 of 6 and 2 of 6 successes) suggest a success rate far below S1's 0.73. On a roster where many tasks are failed by both arms, a same-task success loss on S1 appears roughly halved at roster level, and joint failures add pairs with `D = 0`; both effects make an absolute-margin S-gate crossing easier. This is the standard bias toward non-inferiority from a diluted population. Consequences: the expected roster-level success rate is printed in every T1 and T3 caption, and the S-gate statistic restricted to S1 pairs at the decision prefix is printed (descriptively) in the same sentence as every S-gate statement.

### 3.6 Arrival order (seeded, hash-committed; it is not the assignment mechanism)

For trial number `e` (T1 = 1, T2 = 2, T3 = 3, T4 = 4) and the strata list of the frozen configuration:

```python
rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([60260919, e])))
pairs, leftovers = [], []
for stratum in STRATA:            # A: ["S1_k2","S1_k1","S1_k0","S2"]; B: ["S1","S2"]; S2 absent on roster S1
    uids = sorted(roster[stratum])                            # bytewise order of uid strings
    u = [uids[j] for j in rng.permutation(len(uids))]
    pairs += [(stratum, u[2*m], u[2*m + 1]) for m in range(len(u) // 2)]
    leftovers += u[2 * (len(u) // 2):]
enrollment = [pairs[j] for j in rng.permutation(len(pairs))]  # random interleaving of whole pairs
```

Pair `i` (1-based) = `enrollment[i-1]`; its position 1 is arrival `2i-1`, its position 2 is arrival `2i`. Leftover tasks receive the arrival numbers after `2*N_P` in list order; they are never randomized and are executed only in a post-decision phase. The file `arrival_order_T<e>.json` (pairs, strata, uids, leftovers, `N_P`) is the authoritative object; its SHA-256 is in the freeze bundle. It contains no arm, no coin and nothing from which a coin can be computed. Only the files of the frozen configuration enter the bundle.

Horizon: `N_P` = number of pairs in the file. A: `295 + floor(n_S2/2)`, at most **565**; B: the same count (`295 + floor(n_S2/2)`); roster S1: 295. There is no extension, no second pass and no re-randomization of unused tasks.

---

## 4. Randomization

### 4.1 Unit and coin (D1, CONFIRM C1)

The coordinator's design text says "a fresh fair coin at each arrival". This protocol uses **one fresh fair coin per disjoint pair of consecutive arrivals**, because the only randomized online design in the root's paper is the disjoint-pair orientation design (`paper/main.tex:171-177`; `paper/theory.tex:179-236`, `thm:pair_id`): one coin `R_i` decides which position of pair `i` receives which system, so every pair contains exactly one episode per arm and, with probability 1/2, the score `Z_i` is the observed oriented kernel in {-1, 0, 1} with `V_n = n`. Independent per-arrival coins would produce pairs with two episodes of the same arm, for which neither the paper nor `src/winstats.py` defines a score; R4 found that they leave about 3% of arrivals unpaired, make the number of pairs random and cost 0.5 to 2 points of power. What the coordinator's intent requires is preserved: the coin is fresh, comes from OS entropy, is logged before execution and is never redrawn, and each task is executed under one arm only.

Definition. For pair `i` with positions 1 and 2 (arrivals `2i-1`, `2i`): `R_i = 1` assigns the candidate to position 1 and the incumbent to position 2; `R_i = 0` reverses. `P(R_i = 1) = 1/2`.

### 4.2 Code path (normative)

```python
raw = os.urandom(8)                 # macOS kernel CSPRNG; the only source of assignment randomness
bit = raw[0] & 1                    # R_i
eventlog.append("coin_drawn", {..., "bit": bit, ...}, durable=True)
# durable=True returns only after fcntl(fd, F_FULLFSYNC) succeeded.
# Only after that return may either job of pair i be sent to a worker.
```

(The 63 unused bits are not logged: logged hex would be unverifiable decoration.)

Invariants, each enforced by the orchestrator and re-checked by the log verifier: (i) at most one chain-valid `coin_drawn` per pair; (ii) `coin_drawn` for pair `i` appears after both `episode_revealed` events of pair `i-1` **and after the reveal-triggered look at prefix `i-1`**; (iii) every `episode_started` of the randomized phase points to the earlier `coin_drawn` of its pair; (iv) no `coin_drawn` after a `decision`, and none before the chained external receipt of the trial-start anchor (11.4); (v) **a coin is never redrawn: every chain-valid `coin_drawn` line that is present in the file is binding on resume, whether or not its fsync had returned; a coin is void only if its line fails verification** (a process kill between `os.write` and the return of the fsync leaves a complete, readable line, and treating it as void would be a redraw); (vi) no other randomness influences the assignment: a unit test monkeypatches `os.urandom` and checks that arms follow the patched stream exactly.

### 4.3 Live entropy versus a committed tape or a beacon (D2, CONFIRM C18)

| option | what it would prove | status |
|---|---|---|
| (a) tape of coins drawn in advance and hash-committed | coins were fixed before outcomes | Rejected. The whole orientation sequence would exist before the first episode; this is the configuration the root criticised in the pilot (`reviews/round11_coding_target_scope.md:50`; counterexample in `reviews/round12_coding_correction_and_baseline_delta.md:41-49`). |
| (b) commit-reveal key | same as (a), hidden | Rejected for the same reason: future coins exist in harness memory. |
| (c) public randomness beacon | that the operator did not choose the coin value | Not adopted. v1's reason ("needs network calls during the run") was wrong, since anchoring also uses the network. The accurate reasons: the coordinator's design intent fixes OS entropy; and a beacon removes reliance on the operator **only if** each enrollment event is externally timestamped before its beacon round is published, i.e. one blocking external receipt per pair (up to 565 per trial); without that, the operator can still choose when to enroll. Offered to the coordinator as an option (C18). |
| (d) live OS entropy, write-ahead logged, hash-chained, externally receipted | see below | **Chosen.** |

**What (d) proves and what it does not.** The hash chain is an unkeyed SHA-256 chain over a plaintext file: whoever holds the file can replace any suffix and recompute every later hash, so the chain alone proves nothing against the operator; all evidential weight sits on the external receipts of 11.4. Those prove that a log prefix with a given head existed no later than a server time, and that every later event was produced after that receipt was issued. **The coin is operator-attested and not independently verifiable**: no outsider can distinguish a genuine entropy stream from a chosen one, and an operator who kills the process after reading a coin and before dispatch, deletes the tail and restarts loses no measurable time. The protocol therefore (i) states the assumption "the operator does not act on coins; collection, retry and amendment logic is arm-blind in code and coin-independent" wherever the fair-coin reading is used; (ii) makes such acts visible after the fact through the integrity-event table and the time-sandwich audit of 11.6; (iii) removes the cheapest steering devices: no re-run of any kind (D19), drawn seeds (D18, no rehearsal of potential outcomes from the frozen bundle), blocking receipts at the irreversible points.

Preflight self-test of the entropy plumbing: 10,000 non-design coins, tagged `phase=SMOKE`, never used; the count of ones must lie in [4,850, 5,150]; outside that range the preflight stops and the event is reported; there is no silent repeat. The test says nothing about the design coins.

### 4.4 What is pseudorandom and why that is harmless

Only the arrival order (3.6) is a deterministic function of frozen constants. It is not an assignment mechanism, does not depend on the coin, and is in `F_0`. Sampling seeds are drawn (5.4) and are in no `F_j` before their request.

### 4.5 Arm-blind in code, arm-dependent in effect

Dispatcher, client, retry, timeout, cap, resume and amendment logic are identical for both arms; the only arm-dependent code is the lookup of the workflow name and server URL from the frozen arm table. **Identical code is not identical effect**, and the report says so with the two mechanisms: (1) a failed call in `single_shot` leaves no candidate program (`success = 0` with certainty), while a failed tests or repair call in `self_test_repair` grades the pre-repair program (`agent.py:242-249`); (2) `self_test_repair` issues two to four calls and holds a slot about 4.5 times longer, so it is more exposed to every infrastructure event, to connection retries (which are fresh samples of a generation) and to interruption at a crash. Reported per trial and arm: episodes with at least one failed or retried call; episodes whose outcome was fixed by rows 1 to 3 of 6.4; successes that occurred after a retried try; interrupted and hard-capped episodes. Any operator intervention is a logged `operator_action` with a reason code.

---

## 5. Execution model

### 5.1 Workers, spools and scheduling (D3, D22, D27, CONFIRM C2)

`W = 2` long-lived worker processes (`multiprocessing` spawn context, single-threaded because `sandbox.py` uses `Popen(preexec_fn=...)`, own HTTP session). The orchestrator is the only writer of the event chain. Each worker owns an **append-only, fsynced spool file**: it writes a request line (with the drawn seed and the body hash) and fsyncs **before** the POST, writes the response or error line and fsyncs **before** using the response, and writes a terminal `episode_final` line (record hash, outcome vector) after the record file is fsynced. The orchestrator reads the spools and turns their lines into chain events; a worker never blocks on the orchestrator, so orchestrator load cannot enter `latency_s` (the spool fsync time can: it is logged per call and reported per arm). The pipe carries only the job and a wake-up. On a broken pipe (orchestrator died) a worker finishes its current episode to its frozen end, completes its spool and exits; on resume the orchestrator first waits for such workers (up to the remaining hard cap) and then ingests the unlogged spool remainder with `recovered: true`.

**Randomized phase, pair-synchronous.** For `i = 1, 2, ..., N_P`: enroll pair `i`; draw and durably log `R_i`; send position 1 to worker 0 and position 2 to worker 1 (in that order, without waiting in between); both episodes run concurrently against the server(s); each is revealed when its `episode_final` line has been ingested (after hidden-test verification). Pair `i+1` is enrolled only after both episodes of pair `i` are revealed, the `/metrics` scrape of the pair boundary is logged (11.5) and the look at prefix `i` has been evaluated. There is no arrival clock (closed loop). Queue wait (enqueue to dispatch) is recorded per arrival.

Why pair-synchronous: with a sliding window on one GPU, the final record of pair `i-1` (its wall-clock latency, possibly a load-induced timeout) can depend on the coin of pair `i`, because a `self_test_repair` neighbour occupies the second slot about 4.5 times longer than a `single_shot` neighbour. The filtration `F_{i-1}` contains that final record, so conditioning on it would be informative about `R_i`; this is the warning of `paper/asynchronous.tex:72-76` and the root's request to "specify the target and shared-resource assumptions first". Under the pair-synchronous rule `R_i` does not exist while pair `i-1` runs, so cross-pair interference through the coin is excluded physically. **The price is stated plainly:** at most one pair is ever pending, reveal order and arrival order differ only by a swap inside a pair, and the asynchronous comparison of 8.6 is bounded by one episode. What is kept from the coordinator's intent: two concurrent workers, real reveal timestamps, reveals out of arrival order inside a pair. What is not claimed: a study of monitoring under delay (1.1, 1.4 item 18).

**Post-decision phase, work-conserving.** After a decision the remaining arrivals of the frozen order are taken one at a time by whichever worker is free; both run the decided arm. The two phases use different schedulers, so nothing is compared across them (1.4 item 10).

### 5.2 Server supervision

Configuration as in 2.2, identical for the whole trial. A supervisor polls `/health` every 5 s; on process exit or 3 consecutive failures it logs `server_down`, re-verifies the serving manifest and the GGUF hash, restarts with the identical argv, logs `server_restarted`, and compares the full `/props` object with the golden object (difference: `trial_aborted`, 6.4 row 6). At the first start the same comparison is made against the golden object of the freeze bundle (v1 compared restarts only). The smoke completion that follows every start or restart is tagged `phase = SERVER_SMOKE` and enters the reconciliation identity of 11.5. `/metrics` scrape points: 11.5.

### 5.3 Sampling parameters (D17)

Every request body contains exactly: `model` (alias), `messages`, `temperature: 0.7`, `top_p: 0.95`, `top_k: 0`, `min_p: 0.0`, `typical_p: 1.0`, `repeat_penalty: 1.0`, `presence_penalty: 0.0`, `frequency_penalty: 0.0`, `mirostat: 0`, `max_tokens: 1024`, `seed` (5.4), `cache_prompt: false`, `stream: false`, `verbose: true`. Temperature, top_p and the completion cap are the pilot's values; `top_k: 0` and `min_p: 0.0` disable samplers the MLX pilot did not have. Samplers that are **not sent** (DRY, XTC, top-n-sigma, dynamic temperature, sampler order, and any other sampler-affecting key of `generation_settings` at the pinned commit) are covered by the golden receipt object of 5.7: the pre-freeze derivation file lists every sampler-affecting key with the value that makes it a no-op, and preflight fails if the golden object deviates. v1's sentence "every field sent explicitly" is withdrawn. Both arms and both models use the same values. "1,024-token completion cap per call"; truncation (`finish_reason == "length"`) is counted per request and is not an error. Statements about what is sent are generated from a captured request of the frozen harness. Requests are seeded, but regeneration is not bit-identical (continuous batching); no bit-reproducibility is claimed.

### 5.4 Per-request seeds (D18)

The pilot's seed formula collided across units. v1's index-determined seeds were unique but made every potential outcome rehearsable by anyone holding the frozen bundle, which multiplies the value of the unverifiable coin and buys nothing, because bit-reproducibility is not claimed. v2: for every try of every request, `seed = int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF`, redrawn if the value was already used anywhere in the program (the used set is reconstructed from the chains) and never `0xFFFFFFFF`; the seed is written to the worker spool and to `llm_request` before the POST; the seed receipted by the server must equal the seed sent. Seeds are drawn by the worker without access to the coin and after it; they are part of an episode's internal randomness (7.2). The seed that `run_episode` computes internally is ignored by the injected client.

### 5.5 Timeouts, retries, caps (D15, D19; every row is non-amendable, 12.2)

| parameter | value | note |
|---|---|---|
| `request_timeout_s` | 180, or `30 * ceil(4 * c_max / 30)` if larger, where `c_max` is the slowest call of the out-of-design calibration (5.8) | identical for both arms |
| `max_connection_retries` | 2 (three tries), backoff `min(2 * (k + 1), 10)` s, only for connection errors and timeouts | HTTP 4xx/5xx and malformed bodies are not retried. A retried try is a **fresh sample** (new drawn seed) of a generation that may have been slow because of its own content; retries are part of the system definition of both arms and are reported by arm |
| `server_recovery_s` | 180 | how long a try may wait for a supervised restart |
| `sandbox_timeout_s`, `sandbox_cpu_s` | 10, 10 | pilot values |
| `sandbox_output_cap_bytes` | 65,536 | pilot value |
| `max_repair_rounds` | 2 | pilot value |
| `episode_hard_cap_s` | `4 * (3 * request_timeout_s + 2 * server_recovery_s + 6) + 3 * sandbox_timeout_s + 60` (= 3,714 s at the default values) | by construction larger than the longest legitimate attempt of either workflow (four calls, each with three tries, two recovery waits and the backoffs, plus three self-test executions), so it can bind only on a harness or sandbox hang. Exceeding it is a **terminal endpoint**: `success = 0`, `error_class = episode_timeout`, `latency_s = episode_hard_cap_s`. How often it bound is reported by arm |
| `max_attempts` | **1** | there is no re-run (6.4) |

A returned episode is never re-run, and an attempt that does not return is not re-run either: it is revealed as a failure endpoint (6.4 rows 10 and 11). v1's "first attempt that returns" rule is deleted; it was the airline study's "first non-exception trajectory" rule in prespecified form. Every try of every request is logged with its usage or with `usage_known: false` (11.5). Request timeout, episode timeout and verifier timeout are three separate outcome fields.

### 5.6 Sandbox under two workers (D26)

`experiments/local_stream/sandbox.py` unchanged: macOS Seatbelt profile, fresh temporary directory per execution, process-group kill, CPU and wall limits, output cap. Its containment was audited for **one program at a time**; the profile is allow-default with one writable directory shared by every run on the host, and during a verification that directory holds the hidden tests and the nonce sentinel in clear text. Two concurrent workers would let a generated program of one worker list, read or overwrite the other worker's verification program, and byte-identity of `sandbox.py` does not restore the audited property. v2 restores it by construction:

1. **Host-wide execution lock.** Each worker wraps `sandbox.run_program` (before `agent` and `verify` are imported; a unit test asserts that every call path goes through the wrapper) in an exclusive `flock` on one lock file. At most one generated program exists and runs at any time, exactly as in the audited regime. Lock waiting time is logged per execution (`sandbox_lock_wait_s`); for the agent's own tests it lies inside `latency_s` and is part of the side-by-side regime; hidden-test verification is outside `latency_s` as before. A side effect: no verification ever competes for CPU with the partner's sandboxed program.
2. `TMPDIR` is set to the neutral path `/private/tmp/labsbx` (recreated at start). This changes the profile text, so the audited profile hash does not carry over: the profile hash that results from the trial's `TMPDIR` is recorded in the freeze bundle and per episode. The profile text contains the home path and never enters a tracked artifact.
3. **Containment probe before the freeze, on the trial host, with two workers running:** a probe program in one worker tries to list, read and write the other worker's run directory, the event chain, `records/`, the spools, the task file and the server log; every result is recorded in the freeze bundle; any success of the probe other than those the audited profile already allowed for a single worker stops the freeze.
4. macOS enforces no memory cap; this is disclosed, `W` is kept at 2, RSS is sampled in `server_health`, and the config key is named `mem_bytes_requested_not_enforced_on_macos`.

Success = hidden checks exit 0 AND the per-call nonce sentinel is seen (`verify.py:78-82`). Verifier wall seconds and CPU seconds are both logged.

### 5.7 Sampler receipt, golden objects and served-model assertion

In the pre-freeze smoke, per server, the harness captures (a) the full `/props` object (with `model_path` tokenized) and (b) the full `__verbose.generation_settings` object of a reference request. Both enter the freeze bundle as **golden objects**, together with a frozen **mask list** that names the per-request fields (`seed`, and any field that the smoke test shows to vary with the prompt, each with its own comparison rule). For every response the client compares the **whole unmasked** `generation_settings` object with the golden object (exact for integers, strings and lists; 1e-6 for floats, because the server echoes float32) and `seed` with the seed sent; **any unknown or missing key is a mismatch**. `timings.cache_n == 0` and `tokens_cached == 0` are asserted on every response as the receipt for `cache_prompt: false`, which is a request field that the server does not echo. The `model` field must equal the arm's alias. A mismatch is handled by 6.4 rows 12 and 13 (episode revealed, then `trial_aborted`); never a silent continue, never a dropped episode.

What the receipt is: `generation_settings` is the request **as parsed by the server and merged with its defaults** (`task_params::to_json()` at the pinned commit); it is not read back from the sampler chain. The permitted wording is that of claim 6 in 1.3. This closes the root's "actual sampler receipt unverified" finding only in that sense and only for these trials.

If the receipt path cannot be proven on the **coder** server at the pinned build (no `__verbose` object, or no `usage`/`timings`), the program is not started; no logging proxy or other substitute path is built.

### 5.8 Pre-freeze out-of-design phase

Tasks: the six timing-pilot tasks of 3.2 and four hand-written prompts stored in the config; never a design task. Contents:

1. receipt smoke test and golden-object capture per server; template rule and format-conformance rule of 2.4 for both models;
2. **counter-semantics test:** start a 1,024-token generation, disconnect the client at about 200 received tokens (a streamed probe request is used for this test only), scrape `/metrics` before and after, and record whether and how many prompt and predicted tokens of the cancelled task are counted; the result fixes the accounting wording of 11.5;
3. calibration of call durations at concurrency 1 and 2 for both workflows and both models (sets `request_timeout_s` and hence `episode_hard_cap_s` by the rules of 5.5; checks memory);
4. **T3 side-by-side calibration:** latency of each T3 model on the out-of-design prompts when served alone and when the other model generates beside it from the other server process; the measured compression (side-by-side duration ratio against solo duration ratio) is frozen into the T3 estimand text of 6.2;
5. reference sweep (3.2 item 4) and containment probe (5.6);
6. end-to-end rehearsal of orchestrator, spools, anchor process and verifier against the mock server, and the **anchor drill against the real remote** (11.4).

All of it is written to a separate chain under `results/live_ab/_prefreeze/` with `phase` in {`SMOKE`, `TIMING_PILOT`, `SERVER_SMOKE`} and its own genesis; the chain is closed by a `prefreeze_closed` event whose head, byte length and file hash enter the freeze bundle, together with a **derivation file** that shows every value of Appendix D next to the rule and the recorded inputs that produced it. Its tokens are reported separately and excluded from every trial total. Success outcomes of these runs are not computed for any design choice; the quantities used are durations, memory, receipt equality, template facts and the yes/no extractability of a code block.

---
## 6. Outcomes, hierarchy, tolerances, failure rules

### 6.1 Episode endpoints

| field | definition |
|---|---|
| `success` in {0, 1} | archived verifier label: hidden checks exit 0 and sentinel seen; verifier timeout, missing sentinel, empty or unextractable code, and every failure path of 6.4 give 0. It is not semantic correctness and not an independent re-adjudication. |
| `latency_s` | as in `agent.py:247`: wall time (`perf_counter`) from the start of `run_episode` to the existence of the final candidate program; includes all model calls, connection retries (each a fresh sample, 5.5) and backoff, waiting for a supervised server restart, the agent's own test executions including their wait for the execution lock (5.6), and the spool fsyncs (5.1); excludes hidden-test verification and model loading. For a hard-capped attempt it is the cap; for an attempt that ended without returning (6.4 rows 10, 11) it is the certified elapsed time of 7.6. In every table the field is named `latency_s_w2sync` ("workflow latency under pair-synchronous two-worker load on this host") and is never pooled with the pilot's sequential `latency_s` nor with post-decision latencies. |
| `completion_tokens` | sum of server-reported completion tokens over all responses of the arrival; requests without a response contribute nothing and are listed under unknown usage (11.5). |
| recorded, not scored | prompt tokens; number of model calls; failed calls; retried tries; self-test executions (`n_self_test_executions`) and verifier executions (`n_verifier_executions`) as separate fields; repair rounds; `finish_reason` per request; truncation flag; verifier return code, sentinel flag, verifier wall and CPU seconds; **three separate timeout fields** (`request_timeout_any`, `episode_timeout`, `verifier_timeout`); `error_class`; `infra_flag`; queue wait; lock waits; overlap seconds with the partner episode and the partner's state at verification; per-call `predicted_per_second` and `id_slot`; SHA-256 of `final_code` and of the verification program without the nonce line; the static flags of the sandbox (`hack_flags`, `sandbox_flag`). |

The evaluation horizon of an episode is fixed: the workflow runs to its own end under the caps of 5.5. Connection retries and their fresh samples are part of the definition of both systems as evaluated here ("workflow under this client").

### 6.2 Hierarchy (D6)

| trial | tier 0 | tier 1 | tier 2 |
|---|---|---|---|
| T1, T2, T4 | `success`, higher better, tolerance 0 | `latency_s`, lower better, relative tolerance 0.10 of the larger value | `completion_tokens`, lower better, relative tolerance 0.10 of the larger value |
| T3 | same | same | none |

Rule of `winstats.compare` (`src/winstats.py:25-48`): for tier k, `tol = relative_tolerance * max(|a_k|, |b_k|)`; the tier is decisive iff it is the first with `|a_k - b_k| > tol` (strict; exact equality is a tie) and the pair is eligible for it. Eligibility: tier 0 always; tiers 1 and 2 only if both episodes succeeded. Joint failure is a tie. The 10% tolerance is an operational preference, not a significance test. T1, T2, T4 use the hierarchy the root accepted for the coding stream (`results/open_coding/collection_config.json`; `paper/open_coding_appendix.tex:42-56`). The kernel is never refitted; its code hash is in the freeze bundle and in every `monitor_update`.

**T3, stated before any data (CONFIRM C25).** T3 drops the token tier because native token counts of two tokenizers are not a common cost unit. Its only resource tier is wall-clock latency measured while the two models compete for one GPU from two server processes. How the GPU is shared between two processes on this host is not documented; under per-step alternation two episodes with equal token counts finish together whatever their solo speeds, and even under a mild equal-slowdown model the faster episode is slowed for all of its duration and the slower one only during the overlap, so the frozen 10% tolerance corresponds to a larger tolerance (the statistics auditor's estimate: 17 to 22%) on the solo latency ratio. After a T3 decision the candidate never again runs beside the incumbent, so the live action is taken for a regime that then disappears. Wall-clock latency is nevertheless kept as T3's resource tier, because it is the only resource notion common to two model families, and a tier that cannot separate them is a tie, which costs power and not validity. Consequences, all fixed now: (i) the measured side-by-side compression of 5.8 item 4 is printed in the T3 estimand text; (ii) every T3 composite statement and the T3 decision label itself carry "regime-specific: latency under cross-process GPU sharing on this host"; (iii) the share of pairs decided at tier 1 is printed next to the decision; (iv) the success-only composite (8.10) is reported with equal prominence; (v) 1.4 item 8 forbids any statement about solo latency. A written root objection to this hierarchy defers T3.

Pilot-expected share of pairs decided at each tier (planning values from the pilot's cross-task pairs, MLX stack, unstratified): T1 and T2: tier 0 39.2%, tier 1 52.6%, tier 2 0.3%, ties 7.9%; T4: tier 0 39.2%, tier 1 48.2%, tier 2 1.2%, ties 11.4%; T3: no pilot basis. The token tier decides almost nothing; this is said wherever the three-tier hierarchy is described. The realized shares are reported per trial.

### 6.3 Pair scores

With `vals(r) = [success, latency_s, completion_tokens]` (T3: first two) and `both = success_cand and success_inc`:

```python
z, tier = compare(vals(cand), vals(inc), tiers, [True, both, both])   # Z_i in {-1,0,1}; positive favours the candidate
d = int(success_cand) - int(success_inc)                              # D_i in {-1,0,1}
```

All values are finite by construction (6.4), as `compare` requires.

### 6.4 Failure-to-outcome rules (fixed in advance; intention to treat; **no re-run of any kind**)

Principle: every arrival with a chain-valid assignment yields exactly one revealed outcome under that assignment, from exactly one attempt. Failure to reach the outcome within the frozen horizon is an endpoint (`paper/theory.tex:555-563`), not an observation to discard or to redraw. All usage of every try is logged; unknown values are `null` with a reason, never 0.

| # | event | outcome rule | accounting |
|---|---|---|---|
| 1 | request timeout | connection retry per 5.5 (a fresh sample); after the last try the call raises; `run_episode` records the error and grades the last candidate that exists; `success = 0` if none | `llm_error` per try, `usage_known: false`; `/metrics` scraped before and after the failed try (11.5) |
| 2 | HTTP 4xx/5xx | not retried; same consequence as row 1 | `llm_error` with status |
| 3 | HTTP 200 without `usage` or `timings`, or non-JSON | treated as row 2 (`malformed`); no token estimation path exists | `llm_error` |
| 4 | `finish_reason == "length"` or `truncated` | not an error; text used as is; `truncated_any` recorded | full usage known |
| 5 | server crash or hang | supervised restart with identical argv; the client waits up to `server_recovery_s`; waiting time is inside `latency_s`; if recovery fails the call fails as row 1 | `server_down`, `server_restarted`; counters lost across a crash reported as an unreconciled window |
| 6 | restarted server differs from the golden `/props`, the serving manifest or the GGUF hash | `trial_aborted(server_identity)`; nothing further is dispatched; everything revealed so far stays reportable | blocking anchor |
| 7 | sandbox wall or CPU kill, fork refusal, permission error | in a self-test: a failed self-test (triggers repair); in verification: `success = 0`, `verifier_timeout` recorded with the partner's state | execution seconds |
| 8 | sentinel missing with exit 0 | `success = 0` | `sentinel_seen` |
| 9 | empty or unextractable code | `success = 0` | record |
| 10 | worker process dies during an attempt, for any reason | **terminal:** the arrival is revealed with `success = 0`, `error_class = worker_died`, `latency_s` = certified elapsed time, tokens = known tokens; a new worker is spawned for later jobs; the partner episode is not disturbed | spool lines already written are ingested; unknown tail bounded per 11.5 |
| 10b | `episode_hard_cap_s` exceeded | **terminal:** worker killed; `success = 0`, `error_class = episode_timeout`, `latency_s` = cap | as row 10 |
| 11 | orchestrator crash or power loss | resume per 12.3. An open attempt whose worker spool holds a complete terminal line that passes the orphan checks is revealed from it (`recovered_orphan: true`); **every other open attempt is revealed as `success = 0`, `error_class = interrupted`**, `latency_s` = certified elapsed time. An episode that was already revealed keeps its outcome. Nothing is re-run. | `invocation_started.resumed`; integrity table (11.6) |
| 11b | operator stop | a graceful stop **drains**: the in-flight pair finishes, is revealed and looked at, then `trial_paused`. A pause exists only between pairs. Any other stop is a crash (row 11), is labelled `protocol_deviation` and is an integrity event. `operator_stop` is not an abort reason. | `operator_action` with `what_was_known` |
| 12 | receipt differs from the golden object, or `cache_n`/`tokens_cached` nonzero | the episode completes and is revealed; then `trial_aborted(receipt_mismatch)` before the next dispatch | `receipt_mismatch` list |
| 13 | served `model` alias differs | as row 12 | |
| 14 | clock step or sleep | logged `clock_anomaly` | |
| 15 | disk full or log write error | dispatch stops at once (an unloggable coin may not be used); running episodes finish into their spools; resume per row 11 | |
| 16 | memory pressure | none beyond the sandbox kill; disclosed | RSS samples |
| 17 | live-monitor exception | dispatch pauses (`trial_paused(monitor_exception)`); no decision is taken by hand; the only permitted repair is a harness-only amendment (12.2) that makes the live monitor equal the frozen reference rule; on resume the reference rule is replayed over every completed prefix and 9.2 decides what the trial's result is | blocking anchor |

Consequences that are disclosed with every result: row 11 scores the episode that is still running at a crash as a failure, and that episode is more often the slow arm (in T1 the incumbent, in T2 the candidate); row 10 can in practice be reached only by a workflow that executes programs inside the episode (`self_test_repair`). Both are arm-dependent effects of arm-blind rules. They are rare by expectation (planning expectation: zero events), every such event is an integrity event (11.6), the per-arm table of 4.5 is **primary reporting**, and three or more pairs with an interrupted or worker-died episode label the trial "integrity-qualified" (D35).

`infra_flag` is set by a **closed machine list**: any `llm_error` of any class in the episode; any retried try; any overlap with a `server_down` interval or a restart wait; rows 10, 10b, 11 (including a recovered orphan); any `clock_anomaly` overlapping the episode; rows 12 and 13. Nothing else sets it and no person sets it. Primary analysis keeps every pair. Prespecified descriptive sensitivity read-outs (9.3): (S-infra) without pairs that contain an `infra_flag` episode; (S-int) with every pair that contains a row 10, 10b or 11 episode scored as a tie in both scores.

Automatic, deterministic aborts (no discretion): rows 6, 12, 13; ten consecutive revealed arrivals with `error_class` in {`episode_timeout`, `worker_died`, `interrupted`} or with all tries of a call failed: `trial_aborted(infrastructure)`. An abort can only remove decisions, never create one; every abort is reported with the gate statistics at the abort (12.4).

---

## 7. Pairing under out-of-order reveals, and the exact filtration

### 7.1 Pairing rule

Pairs are the consecutive arrivals `(2i-1, 2i)` of the frozen arrival order (3.6); positions are fixed before the orientation is randomized. Nothing about a pair depends on reveal order, completion time or any outcome. Matching by completion order is never used.

### 7.2 Filtrations (enrollment order)

Let `W_i` be the complete fixed-horizon records of both episodes of pair `i` (all tries, timestamps, drawn seeds, outcomes).

- `F_0` = sigma(roster, strata, arrival order and pairing, frozen protocol: hierarchy, tolerances, caps, systems and model hashes, levels, stake grid or `rho`, margin, `n_min`, `N_P`). **`F_0` contains no coin, no sampling seed and no quantity from which either can be computed.** Potential records are **not** elements of `F_0`: the record that pair `i` would produce under an orientation depends on the history (thermal state, caches, everything earlier coins caused) and on randomness drawn during the pair (sampling seeds, scheduling). The design-based object is the collection, indexed by pair, orientation and history, of the conditional laws of the pair's record; the design assumption is that none of these depends on a **later** coin, which 5.1 enforces physically.
- `H_i` = `F_{i-1}` joined with the information used to enroll pair `i` (its stratum and task identities). Given `H_i`, let `(W_i(1), W_i(0))` denote the pair's potential records under the two orientations. `R_i` is drawn from OS entropy after `H_i` is fixed and independently of `(W_i(1), W_i(0))`: `P(R_i = 1 | H_i, W_i(1), W_i(0)) = 1/2`.
- `F_i` = `F_{i-1}` joined with sigma(`R_i`, `W_i`), where `W_i = W_i(R_i)`.

Consequences, in the root's terms: the current pair's coin `R_i` is **not** in `F_{i-1}`; it enters at `F_i`. Earlier coins are in `F_{i-1}`. Later coins are in no `F_j`, `j <= i`, and do not physically exist while pair `i` runs (4.2 invariant ii). The scores `Z_i`, `D_i` are `F_i`-measurable with the predictable range [-1, 1]. Targets: `mu_i = E(Z_i | F_{i-1})`, `nu_i = E(D_i | F_{i-1})`, running averages `mubar_n = n^{-1} sum_{i<=n} mu_i` and `nubar_n` likewise.

The evaluator's real information at calendar time t (`G_t`: reveal order, timestamps, partial traces) is a different filtration. No martingale argument is made in `G_t`. Every live decision at `(n, t)` implies a statement about the enrollment-order process, where the error bound lives (`paper/asynchronous.tex:111-127`), so the live stopping time needs no stopping-time property with respect to `(F_i)`.

### 7.3 "Reveal order" made precise (D14)

The event chain is written in reveal order with real timestamps. The monitor is re-evaluated at log events, but its statistic is always a function of an **enrollment-order prefix**: the live decision uses the completed prefix `N_c(t)` = number of leading pairs whose two episodes are both revealed (`prop:delay`, `paper/theory.tex:535-563`). Scores are never accumulated in completion order and a pending pair is never skipped. This is the meaning given here to the coordinator's phrase "the monitor consumes outcomes in reveal order"; literal completion-order scoring falsely deployed in 1000 of 1000 null runs of the root's simulation (`paper/async_results.tex:18-21`).

### 7.4 Concurrency inside a pair: a pair-level analogue of `thm:pair_id`, not the theorem verbatim (CONFIRM C8)

`thm:pair_id` is stated under "no interference between the two positions" (`paper/theory.tex:185`). Under pair-synchronous execution the two episodes of a pair share the GPU, so that hypothesis does not hold and v1's sentence "the proof goes through verbatim" is withdrawn. What holds is a **pair-level analogue with a modified assumption**: *no interference across pairs; within a pair, potential records are indexed by the pair's orientation and by the history; no dependence on later coins.* With `U_i = h` evaluated on `W_i(1)` and `V_i = h` evaluated on `W_i(0)` (each oriented as candidate versus incumbent), the fair coin gives

`E(Z_i | H_i, W_i(1), W_i(0)) = (U_i + V_i) / 2`, hence `mu_i = E{ (U_i + V_i)/2 | F_{i-1} }`,

and the same with the success differences for `nu_i`. This is a different statement from the theorem: `mu_i` is "the preference between the two systems when one episode of each runs side by side on this host, averaged over the two orientations of this pair", not the preference between systems running alone or under a production load. **`nu_i` is the effect on the pair's success difference of reversing the pair's orientation; it equals the average same-task success effect of the two tasks only if a task's success does not depend on which arm its partner runs.** That condition can fail in this harness (a partner that holds the GPU or the execution lock longer can push a call or a verification over a wall-clock limit), so it is listed as an assumption, the partner's state is logged with every verifier timeout, and no same-task language is used without it. Whether the root accepts this analogue is item RA5; if it does not answer literally, configuration B is frozen and the reading is printed as "session-60 reading, not confirmed by the root". The error guarantee of 8.5 needs none of this.

Assumptions for the causal reading, all listed wherever it is used: the OS entropy bit is fair and independent of the pair's potential records; execution is nonanticipating; no dependence of any record on a later coin; systems are fixed for the whole trial; **the operator does not act on coins**; for the same-task reading of `nu_i` additionally the no-partner-dependence condition above. Carry-over from earlier pairs is allowed (it is part of the history in `H_i`). For T4 the two arms are one system and nothing depends on the label, so `mu_i = 0` exactly for any hierarchy and any load.

### 7.5 No sliding-window fallback

v1 offered a work-conserving sliding window as a fallback "with everything else unchanged". That is not true (the two positions of a pair would start at different times under different loads; decisions could occur with randomized pairs in flight, which would then be excluded by timing; the comparator would need enclosures for several pending pairs; the power changes), so it cannot be frozen as a one-paragraph variant. If pair-synchronous execution is declined by the coordinator or objected to by the root (C2), nothing is frozen; a sliding-window design is a new protocol version with its own power analysis and audit.

### 7.6 Enclosures for the pending pair (used only by the comparator of 8.6)

Enclosures are logical certainties derived from worker-stamped spool facts, never predictions, and never widen (`paper/asynchronous.tex:33-56, 247-300`).

- Pending `success` lies in {0, 1}.
- Certified elapsed time of a pending attempt: `ell = max_e (t_e - t_c1)`, where `t_c1` is the worker's monotonic time at entry into the first `chat()` call and `t_e` runs over the worker's monotonic send and receive stamps of all its spooled request events. Validity: `latency_s = t_final - t_0` with `t_0 <= t_c1` and `t_final >= t_e`. Orchestrator timers are never used. There is one attempt per arrival, so the endpoint clock never restarts. For a terminal failure (rows 10, 10b, 11) the recorded latency is at least `ell`, and the episode's `success = 0`, so no certificate issued earlier can be contradicted.
- One episode revealed (arm `r`, `sgn = +1` if `r` is the candidate, else `-1`; success `s_r`; latency `L_r`), partner pending with certified `ell`:
  - `s_r = 0`: `Z_i` and `D_i` both lie in {0, `-sgn`}.
  - `s_r = 1`: `D_i` lies in {0, `sgn`}. If `0.9 * ell > L_r + 1e-9`, then `Z_i = sgn` with certainty (if the partner fails the revealed episode wins at tier 0; if it succeeds, its latency `x >= ell` satisfies `x - L_r > 0.1 x`, so the revealed episode wins at tier 1). Otherwise `Z_i` lies in [-1, 1].
- Neither revealed: [-1, 1] for both scores. No certificate is ever derived from tokens.

---

## 8. Monitoring rule: two complete configurations, one of which is frozen

Exactly one of the configurations A and B is frozen for the whole program (12.1). Everything in 8.2, 8.5 to 8.8 and 8.10 is common to both.

### 8.1 Statistics at a completed prefix n

`P_n = #{i <= n: Z_i = +1}`, `M_n = #{i <= n: Z_i = -1}`, `Pd_n`, `Md_n` likewise for `D_i`; `Zbar_n = (P_n - M_n)/n`, `Dbar_n = (Pd_n - Md_n)/n`; `delta = 0.10`.

**Configuration A (`bet_split_v2`).** `L = winstats.betting_log_e_ternary` (grid `numpy.geomspace(1e-4, 0.99/(1 + c), 40)`, equal weights, `bets = 40`, file SHA-256 56955ce0...).

| gate | null about the running target | statistic | crossing |
|---|---|---|---|
| net benefit (NB) | `mubar_n <= 0` | `L(P_n, M_n, n, threshold=0.0)` | `>= log(1/alpha_NB)` |
| success (S) | `nubar_n <= -delta` | `L(Pd_n, Md_n, n, threshold=-delta)` | `>= log(1/alpha_S)` |
| unfavourable composite (U) | `mubar_n >= 0` | `L(M_n, P_n, n, threshold=0.0)` (the score `-Z`) | `>= log(1/alpha_U)` |

Comparisons are made in float64 as `loge >= numpy.log(1.0/alpha_j)`.

**Configuration B (`nm_split_v2`).** `r(n, a) = winstats.normal_mixture_radius(n, alpha=a, rho=100.)` with `V_n = n`; bands clipped to [-1, 1]; no running intersection. This is the construction the root retained for the coding stream (`paper/open_coding_appendix.tex:77-106`, `experiments/build_open_coding_results.py:142-149`), made prospective and joint.

| band | covers | endpoints |
|---|---|---|
| net benefit, two-sided, level `a_NB2` | `mubar_n` for all n simultaneously | `Zbar_n -/+ r(n, a_NB2)` |
| success difference, level `a_S2` (only the lower endpoint is used) | `nubar_n` | `Dbar_n - r(n, a_S2)` |

### 8.2 Looks (D13)

One look at every completed pair `n = N_c(t)` with `n >= n_min = 20`, in increasing `n`, evaluated before pair `n+1` is enrolled. A minimum is not needed for validity (the bounds are uniform over all n) but is frozen. **No retained crossing:** only the current prefix counts, and the rule acts at its **first** crossing (the pilot's unfavourable wealth was above 20 at pairs 14 and 24 and below it until pair 48). No running intersection of any band.

### 8.3 Decision rule and action map (D10)

At look n:

| | configuration A | configuration B |
|---|---|---|
| 1. `RETAIN_INCUMBENT (unfavourable composite signal)` | the U gate crosses | `Zbar_n + r(n, a_NB2) < 0` |
| 2. else `DEPLOY_CANDIDATE (laboratory, success margin 0.10)` | the NB gate and the S gate both cross at this same n | `Zbar_n - r(n, a_NB2) > 0` and `Dbar_n - r(n, a_S2) > -delta` at this same n |
| 3. else | continue; if `n = N_P`: `ABSTAIN_AT_HORIZON` | same |

(Conditions 1 and 2 cannot hold at one prefix in either configuration; the order is fixed anyway.) For T3 both labels additionally carry "regime-specific: latency under cross-process GPU sharing on this host". The action labels always carry the margin. A `RETAIN` decision is a statement about the composite only: it is not success harm, not safety harm and not an approval of the incumbent in the reverse direction. **Status with respect to the root:** the paper's rule has no unfavourable-direction test. A's U gate is `prop:bet_running` applied to the adapted score `-Z_i`; B's rule uses the upper endpoint of the same two-sided band whose "first negative upper endpoint" the root retained as a post hoc reading (`open_coding_appendix.tex:99-100`). In both cases what is new is the use as a **stopping action**, which the root has not endorsed; the reports say so unless a root disposition says otherwise.

### 8.4 Levels and multiplicity (D11, CONFIRM C22)

| trial | trial level | A: (`alpha_NB`, `alpha_S`, `alpha_U`) | A: thresholds on E | B: (`a_NB2` two-sided, `a_S2`) |
|---|---|---|---|---|
| T1, T2, T4 | 0.025 | (0.0025, 0.02, 0.0025) | 400, 50, 400 | (0.0125, 0.0125) |
| T3 | 0.05 | (0.05/3, 0.05/3, 0.05/3) | 60, 60, 60 | (0.025, 0.025) |

- **T1 and T2 test one contrast twice with the roles exchanged** (`single_shot` against `self_test_repair` on the same model and tasks); "NB gate crossed in T1" and "U gate crossed in T2" are the same scientific statement. Following `paper/theory.tex:484-492`, the 0.05 is allocated over the two trials: 0.025 each, so the bound for any false decision statement about that contrast is 0.05. T4 is the control of exactly that rule and therefore uses the same levels; a decision in T4 has probability at most 0.005 (A) or 0.0125 (B) under its exact null. T3 is its own contrast with 0.05.
- **Within a trial:** any allocation with sum at most the trial level is valid under `thm:drift_gate`. A's unequal split for T1, T2, T4 is pilot-informed (very large composite effect, success gate as the bottleneck) and disclosed as such (1.1); B uses equal halves and T3 equal shares, which need no pilot argument. In B both wrong-direction events of the net-benefit statement are non-coverage events of the one two-sided band, so they cost `a_NB2` together.
- **Across the program:** no selection among the trials is made and no combined claim is formed. By the union bound the probability of at least one false decision statement in the program is at most 0.025 + 0.025 + 0.025 + 0.05 = **0.125**; this sentence is mandatory wherever two or more trials appear together (1.3 claim 9). The statistics at the decision prefix are reported so that a reader can apply another split descriptively.
- Planning cost of the contrast-level budget (10.3): about 7 to 8 points of T1 deploy probability against v1's 0.05 per trial.

### 8.5 Guarantee claimed and the theorems it rests on

For each trial, with `(F_i)` of 7.2, scores adapted and in [-1, 1], and all constants fixed before the first design-task outcome of the program:

- A: `P{ exists n: DEPLOY at n, and (mubar_n <= 0 or nubar_n <= -delta) } <= alpha_NB + alpha_S` (`thm:drift_gate`, betting clause, `paper/theory.tex:494-521`, via `prop:bet_running`, `paper/theory.tex:408-436`); `P{ exists n: RETAIN at n, and mubar_n >= 0 } <= alpha_U`; hence `P{ any false decision statement in the trial } <=` trial level.
- B: `P{ exists n: mubar_n outside the NB band } <= a_NB2` and `P{ exists n: nubar_n below the S lower endpoint } <= a_S2` (`thm:normal_cs`, `paper/theory.tex:288-329`), and a false DEPLOY or a false RETAIN at prefix n implies one of these events at that n (`thm:drift_gate`); hence the same bound.

The arrivals are a fixed permutation of a finite roster, which does not give a constant conditional mean (`reviews/round9_open_model_evidence_audit.md:75-81`); therefore the full-level stationary rule `thm:iut` and retained crossings are not used (D25). No stationarity, independence, identical distribution or exchangeability is assumed; task composition, machine state, serial dependence and informative delay are allowed. The decision is a statement about the running average of history-conditional pair means **at the logged prefix**: not about the latest arrival, a later prefix, a future workload, the all-pairs roster functional, a task superpopulation or production traffic (`paper/theory.tex:524-531`). The interpretation of `mu_i` and `nu_i` additionally uses 7.4. The bounds are joint for the processes of one trial because the levels were split; they are not a joint confidence region for effect sizes.

### 8.6 Matched asynchronous comparator (never drives traffic; no error-control claim)

At every ingested spool event of a pending pair (request sent, response received, episode final) the monitor also evaluates the enrolled prefix `N_e(t)` (= `N_c(t)` or `N_c(t) + 1`), replacing the pending pair's scores by their enclosures (lower enclosures in the NB and S statistics, the upper enclosure in the unfavourable direction), same prefix, same constants, `N_e >= n_min`. It records the first event time `t_enc` at which this comparator would cross, the time `t_dec` of the live completed-prefix decision, and their difference. Both are measured on a path that no decision had yet altered. **By construction** `N_e - N_c <= 1` and the enclosure statistic is dominated pathwise by the complete-data statistic at the same prefix, so a comparator crossing at prefix n implies the live crossing when pair n completes: `0 <= t_dec - t_enc <=` the remaining run time of one episode (seconds to tens of seconds inside a trial of hours). The comparison is reported as a measured timing fact with this bound in the same sentence; it is not a study of monitoring under delay, and no error-control claim is made for the comparator in either configuration (C16 is an information item for the root).

### 8.7 Traffic after a decision; post-decision phase (D15, D16)

- On a crossing the orchestrator appends `decision` (durable), closes the log segment with a **blocking anchor** (11.4), and only after the chained external receipt appends `traffic_switch` and dispatches the first `arm_assigned_by_decision`. From then on no coin is drawn; every remaining arrival (both positions of pairs `n+1..N_P` in order, then the unpaired leftovers) runs under the decided arm with two work-conserving workers. Reported: switch latency from crossing detection to the `decision` event, to `traffic_switch`, and to the first dispatch, with the anchor wait shown separately.
- Under 5.1 and 7.3 no episode is in flight at a decision. No episode's workflow is ever cut short by a decision, so the endpoint definition never changes for a pending episode (`paper/asynchronous.tex:396-400`).
- The post-decision phase is an **operational record**: single-arm, outside the monitored process, no inference, never pooled with pre-decision data, never called validation or refutation (1.4 item 14). If it stops early for an operational reason, the report states how many arrivals did not run and claim 3 is restricted accordingly.
- `ABSTAIN_AT_HORIZON`: the trial ends when pair `N_P` completes; leftovers are not executed.

### 8.8 Maximum horizon

`N_P` pairs from `arrival_order_T<e>.json`. No extension, no second pass, no rerun, no reselection of model or seed. A failed, aborted or abstaining trial is reported, not repeated; a repeat would be a new trial under a new protocol version with its own level.

### 8.9 Secondary construction, its own level, and the prespecified discordance sentence

**If A is frozen**, the harness also logs at every look the bands of configuration B with B's levels for that trial. They are a **separate secondary family with its own level** (equal to the trial level): time-uniform, hence valid at the stopping prefix, and they are what is displayed as interval estimates of `mubar_n` and `nubar_n`. They do **not** share the trial level with the decision: decision and bands fail on different events, so a report that offers both as valid statements has a union bound of 0.05 per trial for T1, T2, T4, 0.10 for T3 and 0.25 for the program. No simultaneous statement over decision and bands is made without that number (1.4 item 6).

**Expected discordance, stated now.** `r(280, 0.0125)` = 0.221 and `r(565, 0.0125)` = 0.149 (computed with `winstats`), both above `delta = 0.10`, so the success band can exclude `-0.10` only if the observed difference is clearly positive, while the betting S gate can cross with an observed difference near 0. In the planning simulation (10.3) the secondary bands failed to clear both thresholds at the decision prefix in **every** replicate in which A deployed. The prespecified sentence for that case is: "The driver certified the laboratory demonstration margin 0.10; the secondary band at the same prefix does not exclude -0.10; the two constructions have different power, and the decision rests on the driver only." This information is part of question RA1 to the root (12.1), so that the root answers knowing it.

**If B is frozen**, A's three log E values are logged at every look as descriptive read-outs with no error claim (the root has so far labelled the betting reading of session-60 data descriptive), and there is no secondary family.

### 8.10 Descriptive side read-outs logged at every look (never decide anything)

The S statistic at `delta` in {0.03, 0.05, 0.15} (the nulls are nested, but the stake grids differ with the threshold, so no ordering of crossings is guaranteed; a side-margin crossing is never reported as non-inferiority at that margin); the S statistic restricted to S1 pairs; the truncated "success-only" composite (tier 0 alone) with the same NB and U rules, as the prespecified component-rule comparator; share of pairs decided at each tier; all read-outs by stratum family (S1, S2).

---

## 9. Estimands, analyses and hypotheses

### 9.1 Primary estimands (one pair of targets per trial)

`mubar_n` and `nubar_n` of 7.2: the running averages, in enrollment order, of the history-conditional means of the hierarchical pair score and of the success-difference pair score, at the decision prefix `n = tau` (or at `N_P` if no decision). Under the assumptions of 7.4, `mu_i` is the conditional expectation of the orientation-averaged side-by-side preference within the pair's stratum, and `nu_i` that of the effect of reversing the pair's orientation on the success difference (equal to the average same-task success effect only under the no-partner-dependence condition). The evaluated systems include the client's connection-retry behaviour (5.5). Every table caption names this target. Not targeted: `theta_N`, any superpopulation mean, any same-task preference, any solo-latency comparison, any future workload.

### 9.2 Primary analysis, the reference rule and the disagreement rule (D28)

The decision rule of 8.1 to 8.3 exists twice. The **live monitor** (`lab_monitor`) drives the dispatcher. The **reference rule** (`lab_reference_rule.py`: standard library, numpy and `src/winstats.py` only; it reads `coin_drawn` and `episode_revealed` events and computes scores only through `winstats.compare`; a test asserts that it, the verifier and the builder import nothing from `lab_monitor`, `lab_orchestrator` or `lab_worker`) is part of the freeze bundle and can **never** be amended. The normative decision function of a trial is the reference rule applied to the chain: its result is the **first** prefix `n* >= n_min` at which the rule of 8.3 holds (time-uniform validity covers that prefix; it is a first crossing, not a retained one, and it says nothing about later prefixes), or abstention.

- **Agreement** (the live `decision` equals the reference result in kind and prefix; integer counts and the decision must agree exactly, log E and band endpoints within 1e-9; every look with `|statistic - threshold| < 1e-9` is listed; on other platforms last-bit differences of `logsumexp` are expected and only the tolerance is required): the primary result of the trial is the logged decision, its prefix `tau`, the receipted time, and the statistics at `tau` against their frozen constants, with the guarantee of 8.5.
- **Disagreement** in kind or prefix, including a live abstention where the reference rule crosses, a live decision where it does not, and a reference crossing at `n*` with pairs beyond `n*` already randomized: the primary result of the trial is **`LIVE_DECISION_INVALID (harness defect)`**. Claims 3, 4 and 5 of 1.3 are dropped for that trial; no statistical claim is made for the live decision; the reference rule's first-crossing prefix is printed beside it as a **descriptive** reading; exposure figures are reported as measured but not as the effect of the frozen rule; pairs after `n*` are reported as "randomized after the reference rule's decision"; the trial is not repeated under its id.
- After a crash between the second reveal of look n and a durable `decision`, the resumed run evaluates the look at the last completed prefix **before any enrollment**; if the reference replay finds a first crossing `n*` equal to the last completed prefix, the `decision` is appended with `decided_on_resume: true` and both times; if `n*` is smaller than the last completed prefix, the disagreement rule applies and the trial is closed with `trial_aborted(harness_defect)`.

There is no second, post hoc primary analysis.

### 9.3 Strict separation of statements

**Design-based (valid from the coin, boundedness and the frozen rule only):** the decision and its error bound (8.5); if A is frozen, the secondary bands at `tau` or `N_P` **as a separate family with its own level and the stated union** (8.9); the orientation-average interpretation of the targets under the listed assumptions of 7.4; the count `M` (9.4); in T4, exactness of the null. Coin balance is reported as a description of the draw, not tested.

**Descriptive only (no interval, no test, never feeding a decision):** observed net benefit, success difference, win/tie/loss shares, win ratio and win odds (`winstats.summary`) at the stopping prefix, with the sentence that point values at a data-dependent stopping time are biased by optional stopping; per-arm counts, means and medians of latency, tokens, calls, truncations, failures, retries; tier shares; by-stratum read-outs (wording: "mixes task composition and ... and cannot separate them"); the sensitivity read-outs (success only; success > tokens for T1, T2, T4; S-infra; S-int); the side read-outs of 8.10; `t_enc`, `t_dec` and switch latencies; everything from the post-decision phase; the projection of 9.4; under B, A's log E values. The words "significant", "equivalent", "non-inferior" (other than for a crossed S rule at the labelled margin) do not appear.

**Not produced at all:** t, Welch, cluster-t, bootstrap or delta-method intervals; win-ratio confidence sequences; fixed-mean (iid-roster) readings; any function of `src/wincs.py`; any comparison with, or pooling of, pilot episodes; `M / N_P` or any percentage of exposures; any comparison across the two phases of a trial.

### 9.4 Operational quantities (D24, CONFIRM C27)

Let `tau` be the decision prefix and `M = N_P - tau`.

1. **Primary operational quantities:** `tau` (pairs and arrivals enrolled at the decision) and the switch latencies of 8.7.
2. **Exact count:** `M` pairs of the prespecified roster were not enrolled; under the decision all `2M` remaining paired arrivals ran the decided arm. `M` is always printed with the sentence "`M` is determined by the prespecified roster length `N_P`, which was sized for the T1 success rule; it is not a saving rate". No ratio and no percentage is computed, because with the same data a longer roster gives a larger percentage.
3. **Measured totals:** wall-clock time, busy time per worker, prompt and completion tokens (successful and failed calls, unknown-usage calls counted separately), by phase and arm, "on this host under this serving regime"; never compared across phases.
4. **Projection, a labelled descriptive item outside the claims of 1.3:** `M x (mean pre-decision latency of rejected-arm episodes - mean pre-decision latency of decided-arm episodes)`, same for tokens; caption "projection from pre-decision means; biased toward the decided arm by optional stopping; computed under side-by-side load, which the post-decision phase does not have; the two phases use different schedulers; not a measured saving".

A fixed-sample comparator for a relative efficiency statement is not included (C27).

### 9.5 Hypotheses and what counts as support

| trial | prespecified expectation | support | everything else |
|---|---|---|---|
| T1 | (a) the net-benefit rule is met at a first prefix `n0 >= n_min` (A: NB log E at or above log 400; B: NB lower endpoint above 0); the claim is "at prefix `n0` the running target was positive" and says nothing about later prefixes; (b) `DEPLOY_CANDIDATE (laboratory, success margin 0.10)` within the horizon | (a) the look at `n0`; (b) the decision event reproduced by the reference rule | `ABSTAIN_AT_HORIZON` = "this prespecified rule did not certify the margin 0.10 on this stream": a likely outcome under A and the expected outcome under B (10.3); `RETAIN` would contradict the pilot and is reported as observed |
| T2 | the rule rejects `self_test_repair` | `RETAIN_INCUMBENT` | abstention or deployment reported as observed |
| T3 | none (two-sided, outcome unknown) | not applicable | each outcome, and deferral, is reported with the same prominence |
| T4 | no decision | `ABSTAIN_AT_HORIZON` | a decision has probability at most 0.005 (A) or 0.0125 (B) under the exact null and is reported as that event; one A/A path is never described as evidence of calibration |

---
## 10. Planning analysis (power), and what is honestly expected

Wording rule for this section and everything derived from it: planning numbers are "for this rule, this allocation and this roster, from pilot-based simulation"; none is a statement about what any method can or cannot certify.

### 10.1 What was simulated, by whom

1. **R4** (`R4_power_analysis.md`, `power_sim.py`, 20,000 replicates per main cell): plug-in replay of the 1,182 pilot episodes; random arrival order; fair coin; outcome of a task under an arm = its single pilot outcome; pair scores by `winstats.compare` (the script first reproduces the root's 69/18/208 pilot counts); both constructions at same-prefix first crossing; 295 and 569 pairs; unstratified; levels `nosplit`, `bonf2`, `bonf3`.
2. **P5** (v1 drafter, `P5_supp_power.py`): latent model instead of replay: per-task success probability common to both workflows, Beta(0.386, 0.141) fitted by moments to the pilot read as two exchangeable runs per task (an approximation: the two runs are two different workflows), updated by the pilot pattern; "pilot predictiveness" w shrinks toward the mean; S2 tasks without pilot data; both-succeed pairs won / tied / lost by the cheap candidate with the pilot shares 0.957 / 0.013 / 0.030.
3. **P6** (this reviser, `P6_v2_planning.py`, seeds `[20260919, 6, cell, chunk]`, 4,000 replicates per cell, 20,000 for T4, three runs of about 5 minutes and at most 1.9 GB each): P5's model for the **v2 configurations**: A and B with the levels of 8.4, the single margin 0.10, A's four strata and B's two strata, corrected horizons (565 pairs at `n_S2 = 541`; 495 pairs at `n_S2 = 400`; 295 pairs on S1), S2 mean success in {0.25, 0.45, 0.60} (0.25 is what the only twelve observations on such tasks suggest), w in {0.3, 0.5, 0.7, 1.0}, candidate success shifts {0, -0.02, -0.03}, T2 as the mirror image, T4 under the frozen T1/T2/T4 rule, and a coarse T3 grid. Every probability is printed with its count and a pointwise Wilson 95% interval in `P6_v2_planning.md` (276 rows). w was not calibrated on anything; the planning value quoted in this protocol is the w = 0.7 cell, never the w = 1 cell.

### 10.2 R4 results that shaped the design (reworded)

- For R4's rules and rosters the planning probability of a success-gate crossing at margin 0.03 is 0.007 to 0.030 on 591 tasks and 0.022 to 0.056 on 1,138 tasks (betting, true difference 0), and at 0.05 it is 0.024 to 0.075 and 0.089 to 0.169; in R4's long-horizon run 80% power needed 6,136 to 7,537 pairs (0.03) and 2,274 to 2,740 pairs (0.05) for those rules. These margins are therefore logged descriptively and are not tested (8.10). A sharper construction is not excluded by these numbers.
- With the normal-mixture construction the planning probability of the success rule at 0.10 is at most 0.19 even on 1,138 tasks.
- The unfavourable direction of T2 is decided by the latency tier, not by success; the pilot's betting crossing was at pair 24 and the root's retained band crossing at pair 60.
- `n_min` 10 versus 20 is immaterial; per-arrival coins lose 3% of arrivals and 0.5 to 2 points of power.

### 10.3 Plain expectation per configuration (P6, interim; planning cell w = 0.7, S2 mean 0.45; `delta = 0.10`, `n_min = 20`)

**T1, P(`DEPLOY_CANDIDATE`)** as count / replicates = rate [Wilson 95%]:

| roster (pairs) | cfg | equal success | candidate -2 points | candidate -3 points | deploy prefix Q1/median/Q3 (equal success) | range at equal success over all S2 and w cells |
|---|---|---|---|---|---|---|
| EXT (565) | A | 2751/4000 = 0.688 [0.673, 0.702] | 1838/4000 = 0.460 [0.444, 0.475] | 1376/4000 = 0.344 [0.329, 0.359] | 214/326/440 | 0.629 to 0.871 |
| EXT (565) | B | 234/4000 = 0.059 [0.052, 0.066] | 65/4000 = 0.016 [0.013, 0.021] | 24/4000 = 0.006 [0.004, 0.009] | 390/472/521 | 0.039 to 0.063 |
| EXT (495) | A | 2456/4000 = 0.614 [0.599, 0.629] | 1539/4000 = 0.385 [0.370, 0.400] | 1114/4000 = 0.279 [0.265, 0.293] | 187/293/388 | 0.552 to 0.824 |
| EXT (495) | B | 119/4000 = 0.030 [0.025, 0.035] | 26/4000 = 0.006 [0.004, 0.009] | 15/4000 = 0.004 [0.002, 0.006] | 364/424/466 | 0.020 to 0.039 |
| S1 (295) | A | 1755/4000 = 0.439 [0.423, 0.454] | 881/4000 = 0.220 [0.208, 0.233] | 554/4000 = 0.139 [0.128, 0.150] | 130/193/243 | 0.332 to 0.691 |
| S1 (295) | B | 6/4000 = 0.002 [0.001, 0.003] | 1/4000 | 0/4000 | 255/270/275 | 0.000 to 0.002 |

`RETAIN` occurred in 0 of 4,000 replicates in every T1 cell. The T1 net-benefit rule is first met at median pair 35 to 125 under A and 81 to 179 under B, depending on the S2 success rate. Cost of the contrast-level budget: with v1's levels (0.005, 0.04, 0.005) the first row would be 3053/4000 = 0.763; the v2 levels cost about 7 to 8 points. Side margins under A at equal success: a crossing at 0.03 in 1 to 4% and at 0.05 in 4 to 18% of replicates. **Dilution is visible in the planning numbers:** on EXT (565) the rate rises from 0.688 to 0.791 when the assumed S2 success falls from 0.45 to 0.25, and with a candidate that is truly 3 points worse from 0.344 to 0.470. A higher deploy probability on a roster with more jointly failed tasks is the dilution mechanism of 3.5, not a merit of the design.

**Secondary bands under A:** in all 155,543 planning replicates in which A deployed (all T1 cells), the secondary bands did not clear both thresholds at the decision prefix (8.9).

**T2 (mirror image), P(`RETAIN_INCUMBENT`)** = 36,000 of 36,000 replicates on each EXT roster and 12,000 of 12,000 on S1, in both configurations; no `DEPLOY`. Decision prefix at the planning cell (Q1/median/Q3): A 61/87/117 on EXT (565), 56/78/102 on EXT (495), 33/45/59 on S1; B 109/132/162, 101/120/146, 70/82/95. Medians over all cells: A 35 to 122, B 82 to 180 (later when S2 tasks are mostly failed by both arms, because only pairs in which both succeed reach the latency tier).

**T4 (A/A, frozen T1/T2/T4 rule), any decision:** A 13/20000 (EXT 565), 14/20000 (EXT 495), 5/20000 (S1); B 10, 7 and 1 of 20,000; every Wilson upper limit is below 0.0012; bounds 0.005 (A) and 0.0125 (B). These counts are compatible with the bounds; they are not an estimate of a calibrated error rate, and one T4 path says nothing about calibration.

**T3 (coarse grid; candidate's task difficulty only half as predictable from the incumbent's pilot pattern; two tiers; A thirds of 0.05, B halves):**

| scenario on EXT (565) | A: deploy / retain / abstain | B: deploy / retain / abstain |
|---|---|---|
| equal success, candidate wins tier 1 in 60% of both-succeed pairs | 0.36 / 0.00 / 0.64 | 0.11 / 0.00 / 0.89 |
| equal success, tier 1 balanced | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| equal success, candidate loses tier 1 in 60% | 0.00 / 0.41 / 0.59 | 0.00 / 0.31 / 0.69 |
| candidate +5 points, wins tier 1 in 60% | 0.81 / 0.00 / 0.19 | 0.55 / 0.00 / 0.45 |
| candidate -5 points, loses tier 1 in 60% | 0.00 / 0.74 / 0.26 | 0.00 / 0.64 / 0.36 |
| candidate -10 points, tier 1 balanced | 0.00 / 0.15 / 0.85 | 0.00 / 0.10 / 0.90 |

**Go / no-go sentences for every cell with P(decision) below 0.5 (fixed now):**

- *T1 under configuration B (every roster):* this trial is expected to end in abstention. It is run because it is the prospective version of the only analysis the root has retained for this contrast (a prespecified net-benefit band at a logged prefix and a success band reported with its level), because abstention of a prespecified rule is a legitimate result, and because the program freeze forbids dropping a trial after the configuration is known.
- *T1 under configuration A on roster S1:* abstention is more likely than deployment (planning 0.44). It is run for the same reasons; the live switch of the program is then expected from T2 only.
- *T1 under configuration A on EXT if the candidate is truly 2 or more points worse:* abstention is more likely than deployment, and it would be the correct behaviour of a guarded rule with little power, not evidence of a difference.
- *T3 in every scenario except a candidate that is both more successful and faster side by side:* abstention is the expected result. T3 is run because it is the only contrast whose outcome is unknown; an abstention is reported with the same prominence as a decision.
- *T4:* no decision is the expected and the hoped-for result.

### 10.4 Choice of margin and horizon, honestly stated

- **Margin.** `delta = 0.10` in every configuration and on every roster. It was chosen with knowledge of a same-task pilot difference of exactly zero (433 versus 433, paired standard error 0.015) and of the planning power: it is the smallest value of the grid {0.03, 0.05, 0.10, 0.15} at which configuration A has a better-than-even planning chance of a crossing on the available single-exposure roster. It is **not application-justified** (`paper/main.tex:165-166` asks for application-specific justification, which this laboratory stream cannot supply); a 10-point success loss would rarely be acceptable in practice; a crossing does not establish non-inferiority at any practically relevant margin. Therefore: the action label carries the margin; claim 8 of 1.3 carries the sentence on how the margin was chosen; every S-gate statement prints, in the same sentence, the statistic at the paper's 0.03 and the statistic restricted to S1 pairs; the word "guarded" never appears without the margin. The margin does not depend on the roster or on the configuration (v1's 0.10 / 0.15 switch is removed), so under B the success rule is expected not to be met.
- **Horizon.** All pairs of the roster, once (at most 565 on EXT, 295 on S1).
- **Limits of these numbers.** One pilot run per task and arm on a different serving stack. Not modelled: success rates, token counts and speeds under GGUF Q4_K_M; GPU contention inside a pair; the execution lock; the true difficulty of S2 tasks; thermal drift; the Beta fit treats two workflows as exchangeable runs. Simulated stopping prefixes are expectations, never reported as measured quantities.

### 10.5 Mandatory re-run before the freeze (CONFIRM C12, no fallback)

P6 is the reviser's planning approximation. Before the freeze, **R4's simulator** (not P5 or P6) is re-run for the exact configuration that will be frozen (A or B), on the realized `N_P` and strata counts, for all four trials, with S2 success cells {0.25, 0.45, 0.60}, a fresh-run variability extension with w cells {0.3, 0.5, 0.7, 1.0}, counts and Wilson intervals, the frozen T4 rule, and the table "P(deploy), P(retain), P(abstain), median tau". Its script, seed and output hash enter the freeze bundle, and its table replaces 10.3 in the frozen protocol. **The re-run cannot change any rule parameter**: if its numbers make a trial look hopeless, the go / no-go sentences above already cover that case; changing a parameter in response would require a new protocol version and a new audit. Wall-clock planning (claims auditor, pilot latencies): 6 to 8.5 GPU hours for the program on EXT in the expected cases, 10 to 11 hours in the worst listed cases (for example a wrong-direction early decision in T1 followed by about 1,000 `self_test_repair` arrivals), plus the pre-freeze phase; central values, not bounds.

---

## 11. Event chain, anchoring, usage accounting, integrity forensics, evidence archive

### 11.1 Files per trial

Tracked (in `<CLONE>`): `results/live_ab/<trial>/events/seg_<k>.jsonl` (the chain, written as closed segments; by construction free of generated code, tracebacks, error texts, absolute paths, URLs, account names and commit ids), `anchors/anchor_<seq>.json` (integers and hex digests only), `anchors/tsa_<seq>.tsr` (RFC 3161 tokens, if approved). Private, under `<WORK>/live_ab/<trial>/`: `records/<sha256>.json` (full `run_episode` records, content-addressed, fsynced, write-once), `requests/<request_id>.json.gz`, `spools/worker_<w>_<inv>.jsonl`, `logs/llama_<port>.log`, `anchors_private/receipts.jsonl` (the **identified** receipts: commit id, branch, remote, comment URL, node id, raw API response). Only hashes of private files enter tracked artifacts.

### 11.2 Envelope and event types

Every line is one JSON object: `seq` (0-based, gapless across segments), `type`, `t_wall_ns`, `t_mono_ns` (comparable within one invocation; worker stamps come from the spools and are comparable with each other on macOS), `inv`, `trial`, `prev`, `body`, `h`. Arms are always `incumbent` / `candidate`; `pair` and `arrival` are 1-based indices of the frozen order. "D" = durable (`F_FULLFSYNC` before anything depends on the event). **No field of any event may hold free text, a path that is not tokenized, a URL or a commit id** (D29); the schema validator of the chain writer enforces this field by field.

| # | type | body (main fields) | D |
|---|---|---|---|
| 1 | `trial_started` (seq 0) | freeze bundle hash, configuration id (A or B), config hash and full config, arrival-order hash, roster hash, task-content hash, `N_P`, arms table, monitor block (rule id, function names, `winstats` hash, reference-rule hash, levels, thresholds or `rho`, delta, `n_min`, tiers, eligibility rule, secondary family and its levels), coin block (source `os.urandom(8)`, bit `byte0 & 1`, map), seed rule, failure-rule hash, harness and reused file hashes, serving manifest hash, golden-object hashes, profile hash, protocol hash, freeze receipt reference (`freeze_comment_id`, `freeze_created_at`, `freeze_receipt_sha256`), **link to the previous trial in the frozen order: its final head and the comment id of its end receipt (T4 carries those of the `_prefreeze` chain)**, list of harness-only re-freezes in force, hardware allowlist, package lock hash | yes |
| 2 | `invocation_started` / `invocation_refused` | pid, argv (tokenized), `resumed`, log head at start, reconstructed state, `kern.boottime` hash, drift list against `trial_started` and the chained re-freeze authorizations (any other drift = refusal) | yes |
| 3 | `server_started` | server id, argv, port, GGUF (bytes, sha256 recomputed now), serving manifest check, `/props` comparison with the golden object, `model_path` real-path check, GGUF metadata, load seconds, smoke (`phase = SERVER_SMOKE`, request hash, receipt comparison, usage, timings) | yes |
| 4 | `server_health` | ok, slots busy, RSS, `clock_anomaly` | no |
| 4b | `metrics_scrape` | server id, scrape point (trial start, pair boundary, before or after failed try, quiescent, restart, end), counters | yes at pair boundaries |
| 5 | `server_down` | detection, return code, in-flight list, last counters, `counters_lost` | yes |
| 6 | `server_restarted` | as #3 | yes |
| 7 | `pair_enrolled` | pair, stratum, arrivals, task uids, phase, `re_enrolled` (true only after a crash between #7 and #8) | yes |
| 8 | `coin_drawn` | pair, entropy source, `bit`, assignment {arrival: arm} | **yes, before any dispatch** |
| 9 | `arm_assigned_by_decision` | arrival, arm, `decision_seq` | yes |
| 10 | `episode_started` | arrival, pair, position, arm, workflow, server id, worker, worker pid, task uid, `assignment_seq`, enqueue and dispatch stamps | no |
| 11 | `llm_request` (ingested from the spool) | arrival, `call_index`, kind, `try_index`, client request id, server id, body hash, `sampling_sent`, **drawn seed**, messages hash, message count, prompt characters, worker stamps (`t_c1`, `t_send`), spool offset, spool fsync ms, partner in flight, `recovered` | no |
| 12 | `llm_response` (ingested) | identifying keys, HTTP status, `model`, `finish_reason`, `usage`, `timings` (with `cache_n`), whole `generation_settings` object, `id_slot`, `truncated`, tokens cached / evaluated / predicted, rendered-prompt hash, content hash, client seconds, worker receive stamp, `receipt_mismatch`, `recovered` | no |
| 13 | `llm_error` (ingested) | identifying keys, `error_class` (timeout / connection / http_4xx / http_5xx / malformed), HTTP status, SHA-256 of the error text, client seconds, `will_retry`, `usage_known: false`, seqs of the bracketing scrapes, `bound_is_joint` | no |
| 14 | `episode_revealed` | arrival, pair, position, arm, `reveal_index`, outcome (all fields of 6.1), `error_class`, record hash, `final_code` hash, verification-program hash without the nonce line, static flags, worker start and end stamps, overlap seconds and partner state, `recovered_orphan`, for a terminal failure: certified `ell`, known tokens, number of `llm_response` events already logged and whether they had determined an outcome | yes |
| 15 | `orphan_rejected` | arrival, which orphan check failed, hashes of the rejected files | yes |
| 16 | `monitor_update` | trigger (reveal / spool event), `n_completed`, `n_enrolled`; completed block (P, M, Pd, Md, observed values, the driver's statistics and constants, the other construction's statistics, flags); enclosure block; side read-outs of 8.10; kernel code hash | no |
| 17 | `decision` | kind with full label, `tau`, `monitor_seq`, statistics and constants, in-flight list (must be empty), next unassigned arrival, rule id, `decided_on_resume` | yes + blocking anchor |
| 18 | `traffic_switch` | decision seq, arm, first affected arrival, switch latencies, anchor wait | yes |
| 19 | `anchor` (last line of a segment) | `upto_seq`, `upto_h`, segment index, segment bytes and SHA-256, cumulative bytes, pairs completed, record-manifest hash, byte length and SHA-256 of each `llama_<port>.log`, trigger, `blocking` | yes |
| 20 | `anchor_receipt` / `anchor_failed` | anchor seq, `pushed`, numeric `comment_id`, server `created_at` and `updated_at`, `receipt_sha256` (hash of the identified line in `anchors_private/receipts.jsonl`), TSA token hash; or error class | yes |
| 21 | `amendment` / `amendment_effective` / `refreeze_authorization` | id, text hash, reason code, for a re-freeze: list of {file, old SHA-256, new SHA-256, diff SHA-256}; `what_was_known` | yes + blocking anchor |
| 22 | `log_recovery` | torn offset, length, SHA-256, `is_prefix_of_canonical_event` | yes |
| 23 | `trial_paused` / `trial_resumed` / `operator_action` | reason code from the closed list of 12.4 (or `operator_discretion`), `what_was_known` | yes + blocking anchor |
| 24 | `usage_reconciliation` | per server and window: counter deltas versus summed `usage`, residual, `reconciliation_defect`, windows with lost counters | yes |
| 25 | `publication_withheld` | segment index, pattern class | yes |
| 26 | `server_stopped`, `archive_sealed` | archive SHA-256 and size (11.7) | yes |
| 27 | `invocation_ended`, `trial_ended` / `trial_aborted` | status and reason; exposure ledger by phase and arm; reconciliation totals; terminal failures by arm; longest span without a receipt; `what_was_known`; final head | yes + blocking anchor |

`what_was_known` is always computed by the harness, never typed: counts of revealed outcomes by arm in this trial, the driver's statistics and their distance to each threshold, and the final heads and decisions of all earlier trials of the program.

### 11.3 Hash chain and verifier

`canon(x) = json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`; floats by Python `repr`; NaN and infinities forbidden. `h_i = SHA256(canon(event_i without "h"))`; `event_i.prev = h_{i-1}` across segment boundaries; `event_0.prev = SHA256("live_ab/eventlog-v2|" + freeze_bundle_sha256 + "|" + trial)`. Single writer; descriptor opened `O_WRONLY|O_APPEND|O_CREAT`; one `os.write` per line; no file is ever truncated or rewritten; a closed segment is never reopened.

Torn tails: on opening a segment for resume, **all bytes from the first invalid byte to the end of the file form one opaque torn region**, irrespective of newlines inside it; the next event is a `log_recovery` that commits to its offset, length and SHA-256. A chain-valid `coin_drawn` line is never part of a torn region (4.2 v). If a chain cannot be opened at all, nothing is re-run: the trial is closed by an externally receipted statement in the program's chain of the next trial (or of a closing stub), and is reported as `trial_aborted(chain_unreadable)`.

`lab_verify_log.py` is a **separate code path written by the same session** (it is not called independent). It checks: canonical round trip; gapless `seq`; chain across segments; the invariants of 4.2; **completeness against the frozen order** (the sequence of `pair_enrolled` equals `arrival_order_T<e>.json` exactly in pair index, stratum, both uids and positions; pairs 1 to `tau` (or `N_P`) each have one coin and two reveals; after a decision every remaining arrival and leftover has one assignment event and one reveal, or the count that did not run is reported); exactly one reveal-triggered `monitor_update` for every completed prefix `n >= n_min`, located before `pair_enrolled(n+1)`; at most one `pair_enrolled` per pair per invocation; one terminal event per `llm_request`; outcome fields of `episode_revealed` equal those of the hashed record; T4 job payloads byte-identical apart from the label; first coin after the start receipt, first post-decision assignment after the decision receipt; the reference-rule replay and the agreement test of 9.2; `exposure_ledger.json` equal to a recount from events; the SHA-256 of the **first `segment bytes`** of every committed segment blob against the anchor; receipts against `anchors_private/receipts.jsonl` and `git show`; the usage identities of 11.5; the integrity table of 11.6.

### 11.4 Anchoring: what it proves, what it does not, and how it is done (D20, D29, D30; CONFIRM C10, C17, C19)

**Proves:** that a chain prefix with head `upto_h` existed no later than the server time of its receipt, to anyone who can read the repository or holds the RFC 3161 token; and, because each receipt (server-assigned comment id and `created_at`) is chained into the log, that every later event was produced after that receipt was issued. **Does not prove:** that events happened at their logged client times; that this is the only log of the trial; that nothing was removed before an anchor; that coins came from OS entropy; that the producing code was the frozen harness (harness hashes in the log are self-asserted). A GitHub comment can be edited or deleted by the account owner; it is an external clock, not an immutable record, which is why `updated_at` is stored and why the owner-independent tokens of C17 are requested. v1's sentence that anchors "bound the rewrite window to 25 pairs or 10 minutes" is withdrawn; the bound that the mechanism below supports is "between two consecutive receipts", and a rewrite inside such a window is not prevented but leaves traces (11.6).

**Mechanics.**

1. The trial and its anchor process run in the dedicated clone `<CLONE>`. The anchor process stages explicit paths only, and before each commit asserts the `HEAD` branch (`session60/live-ab`), a clean index and the expected parent; on violation it writes `anchor_failed(tree_state)`.
2. **Every** anchor (periodic ones included) closes the current segment, commits the **anchor file only** (plus the closed segments at the publication points of item 5), pushes, and creates a comment (on the pushed commit, or on the trial's issue) whose body contains the trial id, `upto_seq`, `upto_h` and the segment SHA-256. The API response fields `id`, `node_id`, `created_at`, `updated_at` and the SHA-256 of the raw response go to `anchors_private/receipts.jsonl`; the numeric id, the two server times and the hash of that line are chained as `anchor_receipt`.
3. Triggers: `trial_started`; every 25 completed pairs or 10 minutes, whichever comes first; `decision`; `trial_paused`; `trial_resumed`; `amendment` and `refreeze_authorization`; `trial_ended` / `trial_aborted`.
4. **Blocking anchors.** The first `coin_drawn` of a trial requires the chained receipt of the `trial_started` anchor. The first `arm_assigned_by_decision` requires the chained receipt of the `decision` anchor. An amendment or re-freeze takes effect only after its receipt. `trial_paused` and `trial_resumed` each need a receipt. The anchor process retries for up to 30 minutes; after that the trial is paused (`trial_paused(anchor_unavailable)`; this one pause is receipted together with its resume when the channel returns). Periodic anchors do not block: a failure is logged and the report lists the longest span without a receipt.
5. **Publication of the chain.** During the randomized phase the repository receives anchor files only, which contain no coin and no outcome; this is what makes the arm-blind status file of 12.5 meaningful. The closed segments are committed at the `decision` anchor and at the end anchor. Before any commit the scanner of 13.2 runs on the files to be committed. A hit in a segment is a harness defect (the chain is identifier-free by construction): that segment is withheld (`publication_withheld`), stays in the private archive with its anchored hash, and is listed in the report; anchoring continues, and **no sanitized copy of the chain is ever produced**.
6. **Owner-independent timestamps (C17).** For the freeze bundle hash and for the start, decision and end heads of every trial, an RFC 3161 request for the SHA-256 is sent to a public timestamp authority (`openssl ts` and `curl`; the request contains a digest only); the token is committed under `anchors/` and its hash is chained. If not approved, every chronology sentence carries the fallback wording of C17.
7. **Freeze record.** The freeze comment is fetched read-only by the runner, which checks that its body contains the bundle hash and that `created_at` precedes the local clock, stores the SHA-256 of the raw response, and refuses to start otherwise. Repository and issue visibility (public or private) are recorded (C19); if private, the wording is "externally timestamped on a private GitHub repository visible to collaborators".
8. The final anchor commit of every trial is tagged (`live_ab/<trial>/end`), tags are pushed, the branch is retained, and the PR is merged with a merge commit, never squashed or rebased, so that anchor commits stay reachable. `COORDINATION.md:17` still says `pull --rebase`; the later work allocation and the user's standing instruction (merge only) supersede it, and the PR says so.
9. **Anchor drill before the freeze:** the whole path (segment close, commit, push, comment, receipt, scanner) is exercised against the **real remote** on a drill branch and a drill issue, with a mock chain that contains the real freeze-receipt fields; a throwaway repository cannot reveal identifier leaks, because its URLs lack the real account and repository names.

**Local-only mode (C10 declined).** Anchors are local commits; nothing blocks; there is **no external chronology after the freeze**; no amendment or re-freeze can take effect, so any event that needs one aborts the trial; claim 1 of 1.3 loses "externally timestamped" for everything after the freeze, claim 3 says "client clock, not externally timestamped", and the freeze comment is posted by the user by hand and verified by the runner as in item 7.

### 11.5 Usage accounting for every try (D34)

Two ledgers reconcile by construction: request level (spool lines: one request line before and exactly one response or error line after, for every try of every call, including retried, failed, terminal and post-decision ones; the spool is the recovery source after a crash, so a finishing worker's requests are never outside the ledger) and episode level (`episode_revealed`). Separate counters and tables for episodes, model requests and connection retries. Unknown usage is `null` with a reason, never 0.

Server-side counters: `/metrics` (`prompt_tokens_total`, `tokens_predicted_total`) is scraped at trial start (where it must equal the usage of that server's smoke completion exactly), **at every pair boundary of the randomized phase** (the server is idle there, so the window is one pair and, in a pair without a failed try, counter delta minus summed client usage must be exactly 0; any other value is a logged `reconciliation_defect`), immediately before and after every failed try (as a rule, not "if available"; if the partner slot was busy the bound is marked joint), after every restart, in the post-decision phase at a **quiescent point every 50 arrivals** (both workers drain, the scrape is taken, the idle time is logged; the counters are flushed only when a slot is released, so exact reconciliation exists only at quiescent points), and at the end. Windows that span a server crash are reported as unreconciled (`counters_lost`).

`stream: false` deviates from R2 item 50 (streaming with incremental counts). Reason: the receipt object and `usage` are established for the non-streamed response at the pinned commit, and the one-pair window gives a per-request bound without a second response-parsing path. What a request without a response cost is therefore **bounded, not measured**: by the counter delta of its window if the pre-freeze counter test (5.8 item 2) shows that cancelled generations are counted, and in every case by the logical bound of 1,024 completion tokens per such request. If the test shows that cancelled tokens are not counted, claim 6 reads "tokens generated for requests that ended without a response are unknown; their number by arm and the logical upper bound are reported", and the residual is never presented as a reconciliation of failed work. Unknown usage is reported per arm.

Summary fields are named literally: `requests_without_usage`, `episodes_with_terminal_failure`, `canonical_records_absent`, `episodes_with_missing_label` (0 by construction, still reported). Smoke and calibration traffic lives in its own chain and is reported separately. Trial wall-clock, per-worker busy and idle time and per-episode durations are all logged; each summary states which one it uses. Tokens are never converted into money, energy or "compute"; prompt tokens stay visible.

### 11.6 Integrity forensics (D35)

The verifier tabulates, for every trial, and the report prints the tables whether or not they are empty:

1. every invocation boundary with the last durable event before it, the open attempts, and whether a `coin_drawn` without `episode_started` was the last durable event (**coin-adjacent**);
2. every torn region: whether it is a strict byte prefix of a canonical event (if not, it is reported as evidence of editing), whether it parses as or is a prefix of a `coin_drawn` (coin-adjacent), and whether `kern.boottime` changed between the two invocations (a single `os.write` cannot be torn by a process kill, so a torn region without a reboot is an integrity event);
3. every terminal failure of rows 10, 10b, 11, every `protocol_deviation`, every `orphan_rejected`, every `reconciliation_defect`;
4. the **time-sandwich audit**: for consecutive receipts k and k+1, the difference of their server `created_at` values against the difference of the `t_wall_ns` of the two `anchor` events (frozen tolerance: 30 s plus the measured posting latency); and every gap above 5 s between consecutive events that is not covered by an open `llm_request`. A discarded and re-run window shows either as an unexplained gap (genuine clock) or as a sandwich violation (falsified clock);
5. the distribution of `episode_started - coin_drawn` on the monotonic clock, with every gap above 1 s listed;
6. the prefix property of the server logs across anchors.

Label rule: a trial with at least one coin-adjacent event, at least one sandwich violation, or three or more pairs that contain a row 10, 10b or 11 episode is labelled **"integrity-qualified"** in every table and sentence that reports it. The label is mechanical; it is neither an accusation nor an exoneration.

### 11.7 Evidence archive and re-verification of labels

`success` decides tier 0 and the whole success rule, and the tracked deposit contains labels and hashes, not programs. Therefore, at the end of every trial the servers are stopped and `records/`, `requests/`, `spools/`, the server logs and `anchors_private/` are packaged; the archive's SHA-256 and size are chained (`archive_sealed`) before `trial_ended`. Retention and access: CONFIRM C20 (proposal: at least three years after the arXiv posting; given to the root and to reviewers on request). After the last trial an **owner-side re-verification pass** re-runs `verify()` on every archived `final_code` and reports agreement with the logged labels, with timeouts listed separately; it is AI review by the same session and is described as such. What an outsider can check from the tracked deposit alone: the chain, the decisions (reference rule), the anchors against the repository and the tokens. What needs the archive: success labels. What nobody can check: the coin source (4.3).

---

## 12. Freeze, amendments, resume, order of trials, operator

### 12.1 Program freeze (one freeze for all four trials)

1. Branch `session60/live-ab` from current root main (merge only; never rebase, reset or force-push; no existing file under `experiments/{local_stream,tau2_open}`, `results/{local_stream,tau2_open}`, `paper/`, `src/`, `reviews/` is touched; the only shared file that may change is `results/SESSION60_RESULTS_INDEX.md`); dedicated clone (C14).
2. Harness, unit tests, mock-server dry runs (every derived file carries a MOCK banner and sits under a path that every builder excludes).
3. **Root consultation (D31).** A GitHub issue "Conditional experiment: prospective randomized live-stopped trial (live_ab)" is posted with this protocol's hash, the resources (one M5, 6 to 11 GPU hours), the outputs, the narrowed scope of 1.1, and two blocks of questions, each answerable by "yes" or "no" per item:
   - **Block I (selects the configuration).** RA1: split same-prefix fixed-grid betting gates as the live driver, knowing that in the planning simulation the secondary normal-mixture bands disagreed with every betting deploy (8.9). RA2: the unfavourable-composite betting gate on `-Z` as a stopping action. RA3: the levels of 8.4 for A. RA4: pairing within pilot-pattern strata. RA5: the pair-level analogue of `thm:pair_id` (7.4). **A is frozen only if all five items are answered "yes" literally, in issue comments dated before the cut-off. Any "no", partial or conditional answer, or silence on any item freezes B.**
   - **Block II (common to A and B; information and veto).** RB1: pair-synchronous execution with the narrowed claim (C2), quoting the queue entry. RB2: `delta = 0.10` as a labelled laboratory demonstration margin (C6). RB3: under B, the upper endpoint of the two-sided net-benefit band as a stopping action. RB4: the T3 hierarchy (C25). RB5: roster reuse and the disclosures of 3.4. C16 is attached as an information item. **Silence on Block II does not stop the freeze. A written objection to RB1, RB2, RB3 or RB5 before the cut-off stops it (new protocol version and audit); a written objection to RB4 defers T3 only.**
   - **Cut-off:** 72 hours after the issue is posted (C21), stated in the issue. Root replies are recorded by comment id in the freeze record. **Answers that arrive after the cut-off, and in particular after the first T4 episode, change nothing in any trial.**
4. Pre-freeze out-of-design phase (5.8): downloads (C9), reference sweep, roster rule, T3 preflight rules, timeout rule, golden objects, counter test, containment probe, anchor drill, serving build and manifest, R4 re-run (10.5).
5. **Freeze bundle** = SHA-256 over the canonical JSON of: configuration id; config hash; roster hash; **task-content hash** (canonical file of prompts, hidden tests and entry points of the whole roster); the four arrival-order hashes of the frozen configuration; protocol hash; hash of every file under `experiments/live_ab/` (harness, **reference rule, verifier, builder, tests, scanner and its pattern list**); hashes of the reused `local_stream` files and of `src/winstats.py`; GGUF hashes; LICENSE evidence; **serving manifest**; **golden `/props` and `generation_settings` objects and the mask list**; **Seatbelt profile hash and containment-probe results**; **final head, byte length and file hash of the closed `_prefreeze` chain and the derivation file**; environment lock hash; R4 re-run script, seed and output hashes; the root's replies (comment ids and text hashes). Preflight fails on any "unknown".
6. Commit, push, post the commit and the bundle hash on the issue (and request the TSA token). Only then may a design episode start. The runner refuses to start on any hash mismatch and re-verifies harness, config, serving manifest and weights at every invocation.
7. **Immutability.** From the first design-task outcome of the program (the first T4 episode), all statistical parameters of all four trials (levels, thresholds, `rho`, delta, grid, `n_min`, hierarchy, tolerances, strata, arrival orders, `N_P`, driver, unfavourable-direction rule, secondary levels, failure-to-outcome rules), all execution parameters of 5.5, `W`, the server arguments, sampling, prompts, models and the reference rule are immutable for every trial, including the trials that have not started.
8. Corrections to the frozen protocol text are errata files; the frozen bytes never change.

### 12.2 Amendments and the harness-only re-freeze (D32)

**Nothing in the list of 12.1 item 7 can be amended, within a trial or between trials.** If one of those items would have to change, every affected trial ends (`trial_aborted`) or is not started; a continuation is a new protocol version with its own audit, freeze and levels, and every trial that starts after such a change is relabelled "parameters fixed after N program outcomes of the same systems on the same tasks" and loses the wording of claims 1 and 2.

The only permitted change after the program has started is a **harness-only re-freeze**, for a plumbing defect (the stated purpose of running T4 first):

1. Closed list of files that may **not** change: `lab_coin`, `lab_reference_rule`, the verifier, the builder, the scoring path, the failure rules, the seed rule, the config, rosters and arrival orders, anything listed in 12.1 item 7, the reused pilot files, `src/winstats.py`.
2. A `refreeze_authorization` event names each changed file with old SHA-256, new SHA-256 and the SHA-256 of the diff, the reason code, and `what_was_known` (which covers all completed trials). It is followed by a blocking anchor; the diff is committed with it. The runner's drift check accepts exactly the chained authorizations and nothing else.
3. Inside a running trial (for example row 17 of 6.4) the verifier must show that the amended live monitor reproduces every earlier `monitor_update` of the reference rule; then 9.2 decides the trial's result.
4. Completed trials stand and are not repeated. A re-run of T4 would be "T4b", a new trial under a new protocol version.
5. Every trial that runs under a re-freeze carries, in claim 2, "harness files were changed after N program outcomes by the procedure of 12.2; no rule parameter changed".

An amendment in the older sense (a change of an operational detail that is in neither list, for example the anchor cadence) follows the same event sequence: `amendment` with harness-computed `what_was_known`, blocking anchor, `amendment_effective`. Times are never typed by hand. It applies to both arms, flags every unit with its regime, keeps all units in the denominator and claims no counterfactual invariance. Owner-side verification reports name the exact commit and file hashes they checked and are never edited afterwards.

### 12.3 Resume (a pure function of the verified chain and the spools)

1. Verify the chain; commit a torn region with `log_recovery` (11.3); refuse on any drift that no chained authorization covers; take the exclusive lock; wait for surviving workers of the previous invocation (5.1).
2. Ingest the unlogged remainder of every spool (`recovered: true`).
3. For every assignment event of either kind (`coin_drawn` or `arm_assigned_by_decision`) without its reveals: an open attempt is revealed from its spool's terminal line **only if** every call in the record matches spool and chain entries (request id, body hash, content hash, usage), the worker pid and invocation id match `episode_started`, and the record hash matches (`recovered_orphan: true`); otherwise the files are kept as evidence, `orphan_rejected` is logged if a record file existed, and the attempt is revealed as `interrupted` (6.4 row 11). **Nothing is re-run.** A `pair_enrolled` without a coin is re-enrolled with `re_enrolled: true` and then receives its one coin.
4. Replay the reference rule over every completed prefix from `n_min`; apply 9.2 (decision on resume, or harness-defect closure) **before any enrollment**.
5. If a `decision` exists without `traffic_switch`, continue the decision sequence (anchor, receipt, switch). If a `decision` exists, no coin is ever drawn again.
6. Recovered orphans are revealed first, in arrival order (frozen tie rule). No resume path deletes, overwrites or re-runs anything.

### 12.4 Order of trials, unconditional execution, inspection between trials, pauses and aborts (D21, D33)

Order: T4, T2, T1, T3. T4 first, so that a plumbing defect is found where it costs no claim and is repaired only through 12.2; T3 last, on the most exercised harness. **Each trial starts when the previous one has ended; the only admissible reasons for not starting a trial are the operational reason codes below (none refers to an outcome) and the T3 deferral rules of 2.4 and RB4, which are evaluated before the freeze. A trial that is not started is reported under its own heading.**

**Inspection between trials (procedural).** After each trial the verifier runs in plumbing mode and outputs only: chain and completeness checks, agreement flag of the reference rule, reconciliation residuals, receipt mismatches, arm symmetry of stamps and T4 payload identity, terminal-failure counts, integrity tables, anchor receipts. Task-level outcomes, success tables by arm or stratum and every table of the builder are neither built nor read until the last trial has ended.

**Pauses.** A pause exists only between pairs, after a drain (6.4 row 11b). Decision table:

| reason code | machine-checkable condition | single action |
|---|---|---|
| `power` / `thermal` | on battery below 20%, or a thermal-pressure event | drain, pause, resume when cleared |
| `disk` | free space below 5 GB | drain, pause, resume when cleared |
| `server_unrecoverable` | a supervised restart failed within `server_recovery_s` | in-flight calls fail by row 1; after the pair: pause; resume only with an identical serving manifest and golden `/props`; otherwise `trial_aborted(server_identity)` |
| `anchor_unavailable` | a blocking receipt not obtained within 30 minutes | pause; resume when receipts can be obtained |
| `monitor_exception` | 6.4 row 17 | pause; harness-only re-freeze; replay; 9.2 |
| `planned` | operator absence announced | allowed only as a pause whose receipt exists **before** the operator leaves; an absence without it appears as an unexplained gap in 11.6 |
| `operator_discretion` | none of the above | logged and reported under exactly that name, with `what_was_known` |

**Aborts.** The automatic aborts of 6.4 are deterministic. Every other abort is `trial_aborted(operator_discretion)` and is reported under that name. Every pause, resume, abort and operator action carries the harness-computed `what_was_known` and an external receipt, and the program-level report lists every abort with the driver's statistics at the abort. An aborted trial is reported, never restarted; no decision other than one already logged is claimed.

### 12.5 The operator is an AI agent session; blinding is procedural

The operator is an AI agent session with file access to the whole run; it could read the plaintext chain. Blinding is therefore **procedural, not enforced**, and is described so: the orchestrator writes an arm-blind `status.json` (pairs completed, elapsed time, server health, receipts, terminal-failure count; no outcome, no coin, no statistic); the run book restricts the operator to that file and to the process exit codes during the randomized phase; during that phase nothing but anchor files reaches the repository (11.4 item 5); any deliberate look at the chain is an `operator_action`. The absence of such an event proves nothing, and the reports say that. The hash of the exported operator session transcript is recorded in the delivery if the export is available (C20); the transcript itself stays private. Every session-60 document about these trials carries the sentence "prepared and checked by AI agent sessions; not human peer review or author sign-off".

---

## 13. Reproducibility and release hygiene

### 13.1 Reproducibility

- One deterministic builder `experiments/live_ab/build_live_ab_results.py` (standard library, numpy, `src/winstats.py` and the reference rule only) regenerates every table and figure input from the tracked files; it has no import path to the harness, the sandbox or an HTTP client (a test checks this), never runs a model or a generated program, and writes timestamp-free outputs (run metadata in a sidecar). It is part of the freeze bundle and is run only after the last trial. Figures: the numeric inputs are hashed; pixel identity is never claimed.
- Tracked deliverables per trial: `events/`, `anchors/`, `metrics.csv` (row-preserving projection, one row per arrival: no `final_code`, no self-test code, no stderr, no tracebacks; keeps `error_present`, error class, the three timeout fields, retry counts, `hack_flags`, `sandbox_flag`, the code hashes), `pairs.csv`, `monitor.csv`, `decision.json`, `exposure_ledger.json`, `usage_reconciliation.json`, `integrity.json`, `config.json`, `roster.json`, `arrival_order.json`, `provenance.json` with two separate hash tables (original private files; derived tracked files), `env_lock.txt` (`pip freeze`, interpreter, OS build, llama.cpp commit, serving manifest, build options, compiler and SDK versions, launch lines), non-executed `.txt` snapshots of the harness sources, `SOURCE_NOTICES.md`, `DELIVERY_LEDGER.md` (collection status, audited observations, accepted analysis, manuscript claims, excluded methods, deferred extensions), and a versioned generated report. Reports are versioned and never overwritten; exactly one governing document per trial is named first everywhere. Counts quoted in hand-off notes come from an included command. Manifest contents are described literally (digests are called digests).
- A consistency check proves reproducibility of numbers, not their sampling assumptions; the verifier report says so. Decisions and integer counts reproduce exactly on any platform; log E and band endpoints within 1e-9 (9.2).
- Generation is seeded but not bit-reproducible; success labels are archived verifier labels (11.7).

### 13.2 Identifiers, scanning and variants (D29, CONFIRM C26)

- No tracked artifact contains an absolute path, an account name, a host name, a URL or a commit id of this repository. The harness writes repository-relative paths and the tokens `<CLONE>`, `<WORK>`, `<HF_CACHE>`, `<LLAMA_BUILD>`, `<REMOTE>`; host facts and environment variables come from allowlists; error texts enter tracked files only as class plus SHA-256; server `/props` fields that hold paths are tokenized before they are logged.
- A release check scans every text member of every tracked or packaged file for: the local account name, the GitHub account name, the institution name, the repository name, `/Users/`, `/home/`, `/private/tmp/`, `/var/folders/`, `github.com`, and e-mail patterns, anywhere in a string. It is a bounded known-pattern check and is described as such, not as a proof. Exemptions are allowlisted by exact string: the pattern list itself (in this protocol and in the scanner source) and the neutral sandbox root `/private/tmp/labsbx`. Before the freeze the scanner is run on a mock chain that was produced with the real freeze-receipt fields (11.4 item 9).
- **The released chain is byte-identical to the raw chain.** Raw evidence is never rewritten; the chain has no sanitized copy (a sanitized chain could not verify). The identified receipts live in `anchors_private/receipts.jsonl`; the identified hand-off includes that file, an anonymous hand-off omits it; everything else is the same in both. Whether an anonymous hand-off is still needed now that the target is arXiv is for the coordinator (C26).
- Licensing text: dataset evidence as in 3.1; model licences as recorded in 2.3; llama.cpp MIT; the harness itself is described with no licence until the author decides (C13); "no licence statement" means all rights reserved, and the release note says so.

---

## 14. What will be reported whatever the outcome

For every trial, including aborted, abstaining, deferred, not-started, `LIVE_DECISION_INVALID` and "wrong-direction" ones, in the same format and with the same prominence:

1. the freeze record (commit, bundle hash, receipts, repository visibility, root replies by comment id, the configuration frozen and why) and every re-freeze, amendment, pause, operator action and erratum, each with its `what_was_known`;
2. enrollment: pairs enrolled, completed, flagged (`infra_flag`, `recovered_orphan`), terminal failures by cause and arm with the number of responses already logged, torn recoveries, the longest span without a receipt; unpaired leftovers; arrivals that did not run;
3. the decision or abstention with its full label, `tau`, receipted time, statistics and constants at `tau` or `N_P`, the look-by-look trajectory, the agreement result of the reference rule; under A the secondary bands as a separate family with its level, the union bound and, where applicable, the prespecified discordance sentence;
4. win/tie/loss counts, tier shares against the pilot-expected shares, per-arm success counts, observed net benefit and success difference, labelled descriptive and optional-stopping biased;
5. the comparator times `t_enc`, `t_dec` with the one-episode bound in the same sentence; switch latencies; reveal-order statistics;
6. the operational quantities of 9.4 in that order; the exposure ledger by phase and arm; the labelled projection last;
7. failure-inclusive usage accounting in the wording fixed by the counter test; residuals and defects as numbers; unknown usage by arm; receipt mismatches (expected 0); served-model checks;
8. the per-arm table of 4.5 (failed and retried calls, outcomes fixed by rows 1 to 3, successes after a retry, hard caps, interruptions) as primary reporting, and the integrity tables of 11.6 with the label if it applies;
9. by-stratum read-outs, the S1-restricted success statistic, the statistic at 0.03, the sensitivity read-outs and side margins, all labelled descriptive;
10. the planning expectation next to what happened, including "T1 abstained on the success rule", which is reported as abstention of this rule at this margin on this stream and never as evidence that the workflows differ or are equivalent;
11. for T4: whether any rule was met; if so, the statement that this event has probability at most 0.005 (A) or 0.0125 (B) under the exact null and did occur; the scope sentence of 1.2;
12. for T3: the model identity, licence evidence, the rationale of 2.4 with its outcome-informed criterion named, the preflight results, the side-by-side calibration, the regime label, the contamination sentence, or the deferral and its rule;
13. for T1 and T2 together: the sentence that they test one contrast twice and share 0.05; wherever several trials appear together: the program bound 0.125;
14. the disclosure of 1.1 (every pilot-informed parameter) and of 3.4 item 3 (outcome knowledge inside the program);
15. unsuccessful hypotheses, negative and inconclusive results are retained in the results index under their own heading; nothing is rerun to obtain a different answer; deferred items are listed as deferred.

The results index separates: observations; the prespecified live analysis; owner-side descriptive readings; excluded methods. The PR body is regenerated from the governing report at each hand-off. No statement says or implies that the root approved anything beyond the literal text of a root disposition.

---
## Appendix A. Crosswalk to R2's pre-registration checklist (v2 sections)

| checklist item | section |
|---|---|
| Trial ids; incumbent, candidate; model repo, revision, weight hash, quantization, licence evidence; serving stack, commit, launch command, serving manifest; host; workers; resident servers | 1.2, 2.1 to 2.5, 5.1 |
| Pilot disclosure (every pilot-informed parameter); T1/T2 predictable and one contrast; T3 only unknown; shared roster; outcome knowledge inside the program | 1.1, 1.2, 3.4 |
| Laboratory scope; open-weight only; loopback only; no shared entry point with the historical commercial scripts (item 95) | 1.1, 1.3, 1.4, 2.3 |
| Roster: pinned sources, task-list and task-content hashes, prospective exclusions, arrival permutation and its hash; mapping paths exist in the tree (item 68) | 3.1 to 3.6, 12.1 |
| Unit of randomization; coin q = 1/2 from OS entropy; code path; logged-before-dispatch; binding-on-resume rule; odd leftover | 4.1, 4.2, 3.6 |
| Dispatcher and concurrency rule; overlap record; queue wait (item 78) | 5.1, 6.1, 11.2 |
| Per-request seed policy (drawn, unique, logged before sending; item 34) | 5.4 |
| Sampling settings, completion cap, context limit, request / episode / verifier timeouts from an out-of-design timing pilot; three separate timeout fields (items 43, 66) | 5.3, 5.5, 5.8, 6.1 |
| Kernel: tiers, directions, tolerance, eligibility, joint failure = tie; kernel code hash; pilot-expected tier shares (item 24) | 6.2, 11.2 |
| Scores Z and D; ITT failure rule; no re-run; interruption = endpoint (items 32, 35, 52, 53) | 6.3, 6.4, 12.3 |
| Filtrations; coins >= i outside F_{i-1}; targets; assumptions per reading | 7.2, 7.4 |
| Monitoring statistic, file hash, thresholds, margin with its honest rationale, alpha per contrast / trial / gate / direction and program bound, same-prefix conjunction, no retention, no running intersection | 8.1 to 8.5, 10.4 |
| Asynchronous rule: primary completed prefix, secondary enclosure with its bound, looks, minimum n | 7.3, 7.6, 8.2, 8.6 |
| Action map with margin in the label, live switch, blocking decision anchor, horizon, ABSTAIN_AT_HORIZON | 8.3, 8.7, 8.8 |
| What is descriptive only; "mixes ... cannot separate" wording (item 103) | 9.3, 8.10, 1.4 item 22 |
| Operational quantities (tau, switch latency, M as a count) and the labelled projection | 9.4 |
| Planning analysis: scripts, seeds, output hashes; operating characteristics per trial and configuration with counts and Wilson intervals; A/A rate for the frozen rule; go / no-go sentences; mandatory R4 re-run | 10, 12.1 |
| Event schema, hash chain, fsync rule, segments, anchor cadence, receipts, blocking anchors | 11.2 to 11.4 |
| Sampler-receipt mechanism (golden object), preflight proof, consequence of a failed proof | 5.7, 5.8 |
| Usage reconciliation (one-pair windows, counter test), smoke tagging, literal summary field names including `episodes_with_missing_label` (item 56) | 11.5, 5.8 |
| Manifest: environment lock, harness hashes per invocation, model identity checks, weight hash preflight, Seatbelt profile hash, containment probe | 2.2, 2.3, 5.6, 11.2, 12.1, 13.1 |
| Exclusive-use lock, preflight server scan, disk-space and `.gitignore` checks (item 91) | 2.1 |
| Amendment procedure; non-amendable list; harness-only re-freeze | 12.2 |
| Crash and resume; no deletion or rerun of logged units | 12.3 |
| No extension, no rerun, no model or seed reselection; unconditional execution; failed hypotheses retained | 8.8, 12.4, 14 |
| Output file list, deterministic builder, metrics projection, hash tables, no sanitized chain, notices, delivery ledger | 13.1, 13.2 |
| Allowed and forbidden claim lists copied into the protocol | 1.3, 1.4 |
| Freeze record; "before any design-task outcome of the program"; root consultation with cut-off (item 121); merge-only statement in the PR (item 119) | header, 11.4, 12.1 |
| AI-review disclaimer with exact commits; operator disclosed as an AI agent session (item 108) | 1.4 item 16, 12.2, 12.5 |
| Unit tests for unit initial capital and one fair step (item 14) and for the absence of a running intersection (item 20) | Appendix C |

R2's conflicts K1 to K8 are resolved in 4.1 (K1), 7.3 and 8.6 (K2), 5.1 and 7.4 (K3), 9.4 (K4), 10 (K5), 8.4 (K6), 3.4 (K7), 8.7 and 9.3 (K8).

## Appendix B. Frozen configuration skeleton: common block and the two complete configurations (`null` = pinned in the pre-freeze phase, listed in Appendix D)

```json
{
  "experiment": "live_ab", "protocol_version": "v2-draft",
  "common": {
    "trials": {
      "T1": {"trial_no": 1, "incumbent": {"workflow": "self_test_repair", "server": "coder"}, "candidate": {"workflow": "single_shot", "server": "coder"}, "tiers": 3, "trial_level": 0.025},
      "T2": {"trial_no": 2, "incumbent": {"workflow": "single_shot", "server": "coder"}, "candidate": {"workflow": "self_test_repair", "server": "coder"}, "tiers": 3, "trial_level": 0.025},
      "T3": {"trial_no": 3, "incumbent": {"workflow": "single_shot", "server": "coder"}, "candidate": {"workflow": "single_shot", "server": "t3"}, "tiers": 2, "trial_level": 0.05, "label_suffix": "regime-specific: latency under cross-process GPU sharing on this host", "deferred_if": ["preflight_rule_failed", "root_objection_RB4"]},
      "T4": {"trial_no": 4, "incumbent": {"workflow": "single_shot", "server": "coder"}, "candidate": {"workflow": "single_shot", "server": "coder"}, "tiers": 3, "trial_level": 0.025}
    },
    "execution_order": ["T4", "T2", "T1", "T3"], "unconditional_execution": true,
    "servers": {
      "coder": {"port": 8091, "alias": "qwen2.5-coder-7b-instruct-q4km", "hf_repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "hf_revision": "13fb94bfda8c8cf22497dc57b78f391a9acb426a", "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "bytes": 4683073536, "sha256": "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c", "license": "apache-2.0", "license_evidence": null},
      "t3": {"port": 8092, "alias": "t3-candidate", "hf_repo": "ibm-granite/granite-3.3-8b-instruct-GGUF", "hf_revision": null, "file_rule": "*[Qq]4_[Kk]_[Mm]*.gguf, exactly one, not split", "file": null, "bytes": null, "sha256": null, "license": "apache-2.0", "license_evidence": null, "fallback": "none: T3 deferred"}
    },
    "llama_cpp_commit": "4fea119de30f6a923992780f6fd5ccb0bee5d47d", "serving_manifest_sha256": null, "golden_props_sha256": {"coder": null, "t3": null}, "golden_generation_settings_sha256": {"coder": null, "t3": null}, "receipt_mask": null, "receipt_float_tolerance": 1e-06, "assert_cache_n_zero": true,
    "llama_args": ["-np", "2", "-c", "16384", "--no-kv-unified", "-ngl", "99", "--jinja", "--metrics", "--no-context-shift", "--offline", "--host", "127.0.0.1", "--log-timestamps"],
    "workers": 2, "randomized_phase_schedule": "pair_synchronous", "post_decision_schedule": "work_conserving", "quiescent_scrape_every_arrivals": 50,
    "sampling": {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "typical_p": 1.0, "repeat_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0, "mirostat": 0, "max_tokens": 1024, "cache_prompt": false, "stream": false, "verbose": true},
    "seed_rule": {"source": "os.urandom(4)", "mask": "0x7FFFFFFF", "unique_across_program": true, "logged_before_post": true},
    "request_timeout_s": null, "request_timeout_rule": "max(180, 30*ceil(4*c_max/30))", "max_connection_retries": 2, "server_recovery_s": 180,
    "episode_hard_cap_rule": "4*(3*request_timeout_s + 2*server_recovery_s + 6) + 3*sandbox_timeout_s + 60", "episode_hard_cap_s": null, "max_attempts": 1, "hard_cap_outcome": "terminal_failure", "interruption_outcome": "terminal_failure_unless_orphan_checks_pass",
    "sandbox": {"timeout_s": 10.0, "cpu_s": 10, "mem_bytes_requested_not_enforced_on_macos": 2147483648, "output_cap_bytes": 65536, "tmpdir": "/private/tmp/labsbx", "host_wide_execution_lock": true, "profile_sha256": null}, "max_repair_rounds": 2,
    "hierarchy": [{"name": "success", "higher_better": true, "relative_tolerance": 0.0}, {"name": "latency_s", "higher_better": false, "relative_tolerance": 0.10}, {"name": "completion_tokens", "higher_better": false, "relative_tolerance": 0.10}],
    "eligibility_rule": "tiers after the first are compared only when both episodes succeeded; joint failure is a tie",
    "delta": 0.10, "delta_label": "laboratory demonstration margin; not application-justified", "n_min": 20, "look": "every completed pair, before the next enrollment", "retention": false, "running_intersection": false,
    "side_deltas": [0.03, 0.05, 0.15], "winstats_sha256": "56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69", "reference_rule_sha256": null,
    "coin": {"source": "os.urandom(8)", "bit": "byte0 & 1", "map": "1 -> candidate at position 1", "unit": "pair", "binding_on_resume": "every chain-valid coin_drawn line"},
    "design_seed_base": 60260919, "roster_rule": "S1 plus all surviving S2 if the pinned download verifies, else S1",
    "anchor": {"mode": null, "pairs": 25, "minutes": 10, "every_anchor_receipted": true, "blocking": ["trial_started", "decision", "trial_paused", "trial_resumed", "amendment", "refreeze_authorization", "trial_ended", "trial_aborted"], "blocking_wait_minutes": 30, "publish_segments_at": ["decision", "trial_ended", "trial_aborted"], "tsa": null, "sandwich_tolerance_s": 30, "gap_report_s": 5},
    "integrity_label_rule": {"coin_adjacent_events": 1, "sandwich_violations": 1, "pairs_with_terminal_failure": 3},
    "auto_abort": {"consecutive_infrastructure_failures": 10},
    "smoke_tasks": ["mbpp_full/39", "mbpp_full/122", "mbpp_full/522", "mbpp_full/547", "mbpp_full/869", "mbpp_full/966"], "format_conformance_min": 9,
    "root_consultation": {"cutoff_hours": 72, "silence": "B", "block_II_objection": "no freeze (RB4: T3 deferred)"}
  },
  "configurations": {
    "A": {"rule_id": "bet_split_v2", "driver": "winstats.betting_log_e_ternary", "bets": 40, "strata": ["S1_k2", "S1_k1", "S1_k0", "S2"],
          "levels": {"T1": [0.0025, 0.02, 0.0025], "T2": [0.0025, 0.02, 0.0025], "T4": [0.0025, 0.02, 0.0025], "T3": [0.016666666666666666, 0.016666666666666666, 0.016666666666666666]},
          "unfavourable_rule": "betting on -Z at alpha_U",
          "secondary_family": {"construction": "winstats.normal_mixture_radius", "rho": 100.0, "levels": {"T1": [0.0125, 0.0125], "T2": [0.0125, 0.0125], "T4": [0.0125, 0.0125], "T3": [0.025, 0.025]}, "status": "separate family with its own level; union stated"},
          "requires": "literal written yes of the root to RA1..RA5 before the cut-off"},
    "B": {"rule_id": "nm_split_v2", "driver": "winstats.normal_mixture_radius", "rho": 100.0, "strata": ["S1", "S2"],
          "levels": {"T1": [0.0125, 0.0125], "T2": [0.0125, 0.0125], "T4": [0.0125, 0.0125], "T3": [0.025, 0.025]},
          "unfavourable_rule": "upper endpoint of the two-sided net-benefit band below 0",
          "secondary_family": "none; betting log E logged as descriptive read-outs without error claim",
          "requires": "nothing (frozen on any refusal, partial answer or silence)"}
  }
}
```

## Appendix C. Harness modules and the test plan (normative for the implementer)

New code under `experiments/live_ab/` with the prefix `lab_`: `lab_common` (paths, tokens, freeze bundle), `lab_data` (roster, sweep under load, exclusions, task-content hash), `lab_design` (arrival orders for the frozen configuration only), `lab_eventlog` (segmented chain, schema validator that rejects free text, URLs, commit ids and untokenized paths), `lab_coin`, `lab_client` (spooling client, drawn seeds, golden-object receipt comparison; same interface as the pilot's client so that `agent.py` stays byte-identical), `lab_server` (start, identity checks, supervise, `/metrics`), `lab_worker` (spool, execution-lock wrapper, broken-pipe behaviour), `lab_monitor` (live monitor), `lab_reference_rule` (frozen, never amendable), `lab_orchestrator` (single chain writer, spool ingestion, pair-synchronous scheduler, blocking points, switch, exposure ledger, resume), `lab_anchor` (dedicated clone, explicit paths, receipts, TSA, scanner, publication), `lab_verify_log`, `lab_scan`, `lab_mock_server`, `tests_live_ab`, `build_live_ab_results`. Reused unchanged and hashed: `local_stream/{agent,sandbox,verify,data,common}.py`, helper functions of `run_stream.py`, `src/winstats.py`. Not reused: `local_stream/design.py`, the sequential main loop and the monitor table of `run_stream.py`, the pilot's HTTP client, the rewritable manifest, the airline amendment loader.

Tests without any model (all must pass before the freeze):

- chain: tamper, deletion, reorder, wrong genesis, segment boundaries; torn region spanning several lines; kill after write and before fsync return (the coin line stays binding); unopenable chain; schema validator rejects a URL, a commit id, an absolute path and free text in every event type;
- coin: fsync-before-dispatch spy; patched `os.urandom`; one coin per pair; none after a decision; none before the start receipt; coin of pair i+1 only after both reveals **and the look** of pair i; re-enrollment after a crash between `pair_enrolled` and `coin_drawn`;
- seeds: drawn before the POST, logged in spool and chain, unique across a simulated program, never `0xFFFFFFFF`, independent of the patched coin stream;
- betting capital: unit initial capital; expected capital after one fair +/-1 step at most 1 for every stake of the grid (R2 item 14); only the root's one-sided processes are used;
- monitor and reference rule: equality with `winstats` within 1e-9 and exact counts; `n_min`; same-prefix conjunction; unfavourable-first order; no retention (a path that crosses, dips and stays below must not decide later on the old crossing); **no running intersection anywhere in the band code** (R2 item 20); both configurations; action labels carry the margin; import isolation (verifier, builder and reference rule import nothing from `lab_monitor`, `lab_orchestrator`, `lab_worker`; scores only through `winstats.compare`); injected live-monitor defects (sign slip, swapped counts) yield `LIVE_DECISION_INVALID`;
- enclosures of 7.6 including the 0.9 rule and terminal failures; the one-episode bound of 8.6;
- scheduler and switch with scripted latencies: position 2 revealed first; decision only at pair completion; blocking decision receipt before the first post-decision dispatch; horizon exhaustion; leftovers; quiescent scrapes;
- resume: kill points after each of `pair_enrolled`, `coin_drawn`, `episode_started`, first spool request line, response line, record file written, spool terminal line, first `episode_revealed`, second `episode_revealed` (before the look), `monitor_update`, `decision`, the decision anchor, `traffic_switch`, and inside the post-decision phase; after each: verifier PASS, never a second coin, never a second reveal, never a re-run, orphan accepted only when all checks pass, orphan rejection logged, decision on resume, harness-defect closure when pairs exist beyond `n*`; double resume idempotent; two orchestrators refused;
- failure rules: every row of 6.4 by fault injection; hard cap and worker death are terminal; graceful stop drains; ten-failure abort is deterministic; `infra_flag` equals the closed list;
- client: exactly one terminal spool line per request; golden-object comparison catches a changed temperature, an unknown key, a missing key, a nonzero `cache_n`; no estimation path;
- accounting: per-pair residual exactly 0 against mock counters; defect raised otherwise; scrape before and after failed tries; smoke completion in the identity; first scrape equals smoke usage;
- sandbox: every `run_program` call path goes through the execution-lock wrapper; two workers never execute concurrently; reused pilot test classes; containment probe harness;
- anchoring: a forbidden pattern written into a mock segment withholds that segment while anchors continue; `anchor_failed(tree_state)` on a foreign staged file or a wrong branch; sandwich audit detects an inserted gap and a falsified clock; prefix comparison uses the first `segment bytes` only;
- T4: job payloads byte-identical apart from the label;
- freeze-bundle drift refusal; acceptance of exactly the chained re-freeze authorizations; refusal of a changed reference rule, verifier or builder; builder isolation; every path named in a mapping exists in the tree.

Mock-server dry runs (MOCK banner on every derived file): T1-like abstention; wide-margin deploy with switch (mock config only); T2-like unfavourable stop; A/A wiring; chaos kills of workers, mock server and orchestrator; both configurations; then the anchor drill against the real remote (11.4 item 9).

## Appendix D. What is left to the pre-freeze phase

Values marked `null` in Appendix B; `n_S2` and therefore `N_P`; whether T3 runs (rules of 2.4 and RB4); `request_timeout_s` and `episode_hard_cap_s` (rules of 5.5); golden objects and mask list (5.7); the accounting wording (counter test, 5.8); the T3 side-by-side compression (5.8); the serving manifest (2.2); the profile hash and probe results (5.6); the vendor-published pass rates used for criterion (vi) with sources (2.4); the configuration (A or B) from the root's replies under the rule of 12.1; `anchor.mode`, `tsa`, repository visibility, retention (C10, C17, C19, C20); the R4 re-run table that replaces 10.3. Each is decided by a rule written above that uses no design-task outcome, each decided value is recorded with its inputs in the derivation file, and the derivation file is in the freeze bundle.

## Appendix E. Exact manuscript sentences the trials could add, one per outcome (templates; brackets are filled from the governing report; nothing else may be derived)

Retained in every case: "These are laboratory trials on public benchmark tasks with open-weight models on one laptop; design parameters were chosen with knowledge of a pilot on the same tasks; they provide feasibility evidence, not operational latency savings, measured operational savings or a live deployment."

- **T1, DEPLOY:** "In a prospectively frozen, externally timestamped laboratory trial with OS-entropy pair randomization (operator-attested), the prespecified [configuration] rule met both its net-benefit and its success criterion at enrolled pair [tau] of [N_P], and the dispatcher routed the remaining [2M + leftovers] arrivals to `single_shot`. The success criterion used a laboratory demonstration margin of 0.10 that is not application-justified; at the paper's margin 0.03 the statistic was [value] and did not cross. [Under A: The secondary normal-mixture band at the same prefix was [interval] and does not exclude -0.10.] The statement concerns the running average of history-conditional pair means at that prefix; the per-trial error bound is 0.025 and the bound for the T1/T2 contrast is 0.05."
- **T1, ABSTAIN:** "The prespecified rule met its net-benefit criterion first at pair [n0] but did not certify the success margin 0.10 within [N_P] pairs; the trial ended in abstention, which the planning analysis had listed as [likely / expected]. This is not evidence that the workflows differ or are equivalent."
- **T1, RETAIN:** reported as observed, with the sentence that it contradicts the pilot direction.
- **T2, RETAIN:** "With the roles exchanged, the prespecified rule rejected `self_test_repair` as candidate at pair [tau] (unfavourable composite signal, carried by the latency tier); the incumbent was retained and [M] pairs of the prespecified roster were not enrolled (M is determined by the roster length). T2 repeats the T1 contrast and is not a second confirmation."
- **T2, other:** reported as observed.
- **T3, any outcome:** "[decision or abstention] ... regime-specific: latency was measured while both models shared one GPU from two server processes (measured side-by-side compression [value]); [share]% of pairs were decided at the latency tier; the success-only composite gave [result]; prompts and extractor were developed on the incumbent's family, and the contrast cannot separate ability from benchmark contamination." If deferred: "T3 was not run because [rule]."
- **T4:** "In one A/A control path no rule was met" or "one rule was met at pair [n], an event of probability at most [0.005 / 0.0125] under the exact null"; plus "T4 checks the coin path and label blindness only".
- **Asynchronous comparator:** "With at most one pending pair, the completed-prefix decision came [x] s after the first crossing of the partial-information statistic; by construction the difference is bounded by one episode, so this is not evidence about monitoring under delay."
- **LIVE_DECISION_INVALID, aborted, integrity-qualified or not-started trials:** reported under those names; no sentence from the list above is used for them.

## Appendix F. Inputs of this revision (SHA-256 prefixes, files in `<scratch>/live_ab_design/`)

`protocol_draft_v1.md` def9c2dc208b87a8; `R1_accepted_method.md` 07acd3a783cb976f; `R2_constraints_checklist.md` 728c5a1c3fd35769; `R3_harness_plan.md` fa51f7977db99995; `R4_power_analysis.md` 2d1a4eaaec9afc2b; `audit_v1_statistics.md` e13eda4d660645a2; `audit_v1_provenance.md` b0917a62de03ddf2; `audit_v1_claims.md` 8fafde1a1d18a64a; `power_sim.py` 59d87b6c82d7b0fd; `power_results.csv` d934c4530b49fd27; `P5_supp_power.py` bd6c935a05b737c4; `P5_supp_power.json` 0ec6241f465de270; `P6_v2_planning.py` ae0f9c249f145fa3; `P6_v2_planning.json` d65f26b0df3ed7e0; `P6_v2_planning.md` 26d687a858c8fe9d.

---

## Items for the coordinator

Everything below must be settled before the GitHub issue of 12.1 step 3 is posted, because the issue text fixes the fallbacks. Items are grouped by who has to act. "Default" is what this draft does if nobody objects.

**A. Decisions of the coordinator on the design (each is a DECISION of this draft that departs from the coordinator's fixed intent or chooses between auditor options)**

1. **C1 (D1): one coin per arrival pair instead of one coin per arrival.** Default: pair coin. No alternative has an accepted score.
2. **C2 (D3): pair-synchronous execution.** It keeps two workers, real timestamps and out-of-order reveals inside a pair, but reduces "the monitor consumes outcomes in reveal order" to at most one pending pair, and the asynchronous comparison to a number bounded by one episode. The queue's "concurrent prefix study" is therefore delivered only in this narrow sense, and the paper's "feasibility, not operational latency savings" limitation stays. If this is not acceptable, the alternative is a sliding-window design as a new protocol version with its own audit; it is not a switch in this one.
3. **C22 (D11): contrast-level error budget.** T1 and T2 share 0.05 (0.025 each), T4 uses the same 0.025, T3 0.05; program bound 0.125. Planning cost: about 7 to 8 points of T1 deploy probability. The statistics auditor also accepted 0.05 per trial with a printed 0.10 contrast bound; the more conservative option was taken.
4. **C23 (D19): `max_attempts = 1`, no re-run of any kind.** A crash scores the still-running episode (more often the slow arm) as a failure; this is disclosed, reported by arm, and labels the trial "integrity-qualified" from three such pairs. The alternative the provenance auditor preferred, a byte-identical replay continuation from the worker spool, is more robust against forced failures and more complex; the statistics auditor wanted in-episode causes terminal. `max_attempts = 1` is the only rule that satisfies all three auditors and R2 items 32, 52 and 53 literally.
5. **C24 (D5): no T3 fallback model.** If Granite fails a preflight rule, T3 is deferred and the program has three trials.
6. **D12 / C6: one margin 0.10 everywhere, labelled as not application-justified.** Consequence: if configuration B is frozen, T1 is expected to abstain (planning 0.06 or less), and the only expected live switch of the program is T2's. The statistics auditor's alternative (0.03 as the live margin) would make a T1 deploy switch practically unreachable under either configuration.
7. **C18: coin source.** OS entropy stays (design intent); the coin is described as operator-attested. A beacon would help only with one blocking external receipt per pair. Say so if that is wanted.
8. **C21: cut-off of 72 hours** for the root's answers; silence freezes configuration B.
9. **C26:** whether an anonymous hand-off is still a deliverable. The chain is identifier-free and identical in either case.
10. **C27:** the optional fixed-sample comparator `n_fixed` was left out. For orientation only (normal approximation, pilot net benefit 0.50, one-sided level 0.0025, 90% power): a fixed design would need about 57 pairs, which is the same order as the sequential rule's planning median for T2 (45 pairs on S1, 78 to 87 on EXT), so a relative-efficiency sentence would not flatter the sequential rule; worth knowing before anyone asks for one.
11. **C11, C14, C15:** cached Qwen GGUF provenance; branch and dedicated clone; pinning of the Granite repository, file and hash at download (the repository's existence has not been checked).
12. **C12 (mandatory):** arrange the re-run of R4's simulator on the configuration that will be frozen, with the cells of 10.5. P6's table is interim. The re-run may not change any parameter.

**B. Approvals needed from the user**

13. **C9:** downloads (`mbpp.jsonl` at the pinned revision, Granite GGUF about 5 GB, LICENSE files). Without: roster S1 (295 pairs) and no T3.
14. **C10:** pushes and comments from the user's account during runs (about 30 comments per trial), the blocking-anchor rule (a trial waits for GitHub at its start, at its decision and at pauses), and an anchor drill against the real remote on a drill branch and a drill issue. Without: local-only mode with no external chronology after the freeze and no possibility of an amendment.
15. **C17:** RFC 3161 timestamp tokens from a public timestamp authority (sends SHA-256 digests only). Without: the chronology wording says that the GitHub comments are editable by the account owner.
16. **C19:** state whether the repository and the issue are public; "publicly timestamped" is used only if they are.
17. **C20:** retention period of the private evidence archive and its availability to the root and to reviewers; whether the operator session transcript may be exported and hashed.
18. **C13:** code licence of the harness for the arXiv release (root / author).

**C. Questions that go to the root in the issue (the coordinator should check their wording)**

19. **Block I (RA1 to RA5 = C3, C4, C5, C7, C8):** five literal yes/no items that select configuration A; RA1 must carry the information that the secondary bands disagreed with every betting deploy in the planning simulation.
20. **Block II (RB1 to RB5 = C2, C6, the band's upper endpoint as a stopping action, C25, roster reuse):** information with a veto; a written objection stops the freeze (RB4: defers T3 only). C16 is attached for information.

**D. Things the coordinator should know that are not questions**

21. The purpose paragraph no longer says that `live_ab` "is" the queue's conditional experiment. After a fully successful program the manuscript still may not claim measured operational savings, operational latency savings or live deployment (1.1, Appendix E). The coordinator's phrase "realized exposure savings are measured" is delivered only as the decision prefix, the switch latency and the count `M` with its caveat; no percentage and no measured time or token saving exists in this design (9.4).
22. v2 adds engineering that v1 did not have: worker spools, segmented chain with receipts on every anchor and blocking points, a frozen reference rule, golden receipt objects, a serving manifest with a rebuilt server under the home directory, a host-wide execution lock with a containment probe, per-pair counter scrapes, an integrity table with a time-sandwich audit, an evidence archive with a label re-verification pass. Harness construction, the mock and chaos runs, the pre-freeze phase and the 72-hour wait dominate the calendar; GPU time is 6 to 11 hours.
23. The provenance auditor's BLOCK and the claims auditor's BLOCK both ask for a re-audit of the changed sections (4.3, 5.4 to 5.7, 6.4, 8, 9.2, 11, 12) before the issue is posted.
