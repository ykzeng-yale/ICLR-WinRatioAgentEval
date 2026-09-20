# R2 — Constraint checklist for the prospective live A/B trial (from root reviews, Rounds 9–15)

Reader R2, 2026-09-19. Read-only pass over the repository on branch `session60/local-stream` (HEAD `ce8b506`, contains root `410b158`); Round 15 files exist only on `origin/main` (`955579d`) and were read with `git show` (copies: `_ref_round15_*.md` next to this file). No git state change, no model call, no download. One small CPU check was run (`R2_margin_feasibility.py`/`.json`, < 1 s).

Every item gives: **source (file:line)** → **objection/requirement in one sentence** → **measure by which the NEW trial avoids it from the start**.

Source abbreviations (all under `reviews/` unless stated):

| Abbrev. | File |
|---|---|
| R9-GAP | `round9_experiment_gap_assessment.md` |
| R9-AUD | `round9_open_model_evidence_audit.md` |
| R9-SEQ | `round9_sequential_results_audit.md` |
| R10-REP | `round10_open_model_repair_audit.md` |
| R10-DISP | `round10_integration_disposition.md` |
| R10-SEQ | `round10_sequential_corrections_audit.md` |
| R10-DRIFT | `round10_drift_panel_audit.md` |
| R10-REL | `round10_release_delta_audit.md` |
| R11-AIR | `round11_airline_incoming_scope.md` |
| R11-EVID | `round11_coding_integration_evidence.md` |
| R11-TGT | `round11_coding_target_scope.md` |
| R11-INT | `round11_coding_integrated_review.md` |
| R11-LED | `round11_integration_ledger.md` |
| R11-REL | `round11_release_audit.md` |
| R12-EVID | `round12_airline_evidence_review.md` |
| R12-INF | `round12_airline_inference_review.md` |
| R12-INTG | `round12_airline_integrated_review.md` |
| R12-COD | `round12_coding_correction_and_baseline_delta.md` |
| R12-SCOPE | `round12_completion_scope_review.md` |
| R12-LED | `round12_integration_ledger.md` |
| R13-DISP / R13-INF / R13-PROV | `round13_integration_disposition.md` / `round13_owner_report_inference_review.md` / `round13_report_provenance_review.md` |
| R14-DISP / R14-REV | `round14_integration_disposition.md` / `round14_report_cleanup_review.md` |
| R15-REV / R15-DISP | `origin/main:reviews/round15_index_scope_review.md` / `round15_integration_disposition.md` |
| POLICY / QUEUE / ALLOC / COORD | `EXPERIMENT_POLICY.md` / `EXPERIMENT_QUEUE.md` / `WORK_ALLOCATION.md` / `COORDINATION.md` (repo root) |
| THEORY / ASYNC / WINSTATS | `paper/theory.tex` / `paper/asynchronous.tex` / `src/winstats.py` (root-owned, read-only) |
| OWN-LS / OWN-T2 / OWN-T2V | owner-side audits `local_stream_preregistration_audit.md` / `tau2_open_preregistration_audit.md` / `tau2_open_final_verification.md` (not root reviews; supplementary) |

---

## 0. Eight places where the coordinator's design intent collides with the root's accepted construction (resolve BEFORE freezing)

These are not past objections but predictable next-round objections; each is derived from root text.

- **K1. "A fresh coin at each arrival assigns ONE arm" is not the root's score construction.** The accepted score (THEORY:185–225, `thm:pair_id`) is defined on a *pair of positions* with ONE orientation coin `R_i` (q = 1/2) so that every pair has exactly one A and one B episode and `Z_i ∈ {−1,0,1}`. Independent per-arrival coins produce AA/BB pairs for which no accepted score exists, and q ≠ 1/2 HT scores leave `[−1,1]` (R10-SEQ:127). **Resolution:** the unit of randomization is the *disjoint pair of consecutive arrivals*; one fresh OS-entropy coin per pair, drawn and logged when the pair is enrolled, before either episode is dispatched. Each task is still exposed to exactly one arm. The odd leftover arrival is prespecified as unpaired (precedent `mbpp/256`, R9-AUD:25).
- **K2. "The monitor consumes outcomes in reveal order" contradicts the enrollment-order filtration.** ASYNC:22–50 requires `X_i` adapted to the *enrollment* filtration and explicitly allows outcome-dependent delay only because pending pairs are replaced by simultaneous enclosures `ℓ_i(t) ≤ X_i ≤ u_i(t)`; ASYNC:79–82 says the transfer "does not establish a calendar-time e-process". Feeding completed scores to the e-process in reveal order (the fast arm and quick failures reveal first) is a selection the theory does not cover. **Resolution:** the event log is in reveal order, but the statistic at calendar time t is computed on an *enrolled prefix*: primary = completed enrollment prefix `N(t)` (THEORY:535–536, `prop:delay`); secondary (logged side by side, never deciding unless prespecified) = enclosure version `thm:async_betting` (ASYNC:170) with pending pairs at their worst case. This is exactly the "matched completed-prefix comparator" the root asked for (R9-GAP:35).
- **K3. Concurrency on one GPU is cross-pair interference in the latency tier.** THEORY:185 ("no interference between the two positions"), ASYNC:59–61 ("no cross-pair interference"), ASYNC:75–76 ("Shared infrastructure effects, interference … require their own justification"), R9-GAP:35 ("Specify the target and shared-resource assumptions first"), R10-REP:60 (thermal state/order/caching affect latency). With two workers the wall-clock of an episode depends on which arm the *other* worker is running, i.e. on other pairs' coins. **Resolution:** (a) state the primary guarantee only for the running average of history-conditional means under the declared 2-worker serving regime (valid for any adapted bounded score); (b) give the causal assignment-average reading only under an explicitly listed no-interference assumption; (c) prespecify a co-load-invariant sensitivity hierarchy (success > model calls/completion tokens) as descriptive robustness; (d) record, for every episode, which other episode(s) overlapped it and their arms.
- **K4. "Realized savings" must be split into an exact design quantity and a projection.** QUEUE:35 demands *measured* savings; R12-EVID:70 forbids per-task averages presented as "fully measured operational costs"; R11-TGT:58 forbids savings from a replay crossing. After a live decision the exact, model-free saving is the **number of inferior-arm exposures avoided** relative to the prespecified fixed-horizon design (= half of the remaining pairs); wall-clock/tokens "saved" require a counterfactual and must be labelled a *projection from pre-decision means*, reported next to the measured totals of the run.
- **K5. The success guardrail is not certifiable at 0.03 with 295 pairs.** R9-AUD:85,117 ("plan a valid target and sample size for the 0.03 guardrail before another generation run"), R12-INF:70 (normal-mixture radius reaches .03 only at n = 12,094). R2 side-check on pilot data with the root betting e-process, α split .025/.025, same-prefix conjunction, 400 re-randomized streams: P(guarded deploy within 295 pairs) = 0.01 (δ=.03), 0.04 (δ=.05), 0.32 (δ=.10), 0.81 (δ=.15), 0.98 (δ=.20); the net-benefit gate alone crosses at median pair 39 in 100% of streams (`R2_margin_feasibility.json`; planning approximation, static pilot outcomes). **Resolution:** either a margin with a documented application rationale at which the power analysis gives an acceptable deploy probability, or a larger roster, or preregister "abstention on the guardrail is the expected result at δ=.03" (R9-GAP:33: abstention may be the scientifically correct result; never adjust margin/hierarchy after outcomes).
- **K6. Four trials at level α each is a program-wide error of up to 4α; deploy + harm in one trial is up to 2α.** THEORY:478–486 (no α-each across experiments; use Σα_e ≤ α_program), R10-DRIFT:38 (no inference for "a program-wide family of deployments"), R9-AUD:50–63 (max of two one-sided capitals = 2α). **Resolution:** the protocol states the per-trial α_e, the within-trial split between gates (Σα_j ≤ α_e, `thm:drift_gate`) and between the deploy and harm directions, and the resulting program-wide bound; T4 (A/A) is included in that budget.
- **K7. T1/T2 reuse a roster whose outcomes under both arms are already known from the pilot.** Precedent: task 0 was excluded from tau2 because its outcome was known before the protocol was written (OWN-T2:328–341); R11-TGT:90 (no retrospective selection of hierarchy/tolerance/ρ); R9-AUD:97 (public benchmark exposure). Validity of the e-process rests on fresh coins and fresh generations, so this is allowed, but the protocol must say that hierarchy, tolerance, margin and hypothesis direction were chosen with pilot knowledge of the *same tasks*, that T1/T2 are confirmatory live-operation demonstrations, and that only T3 has an unknown outcome. Also decide and state whether T1–T4 share the 591-task roster (each task exposed once *per trial*) or use disjoint prespecified blocks.
- **K8. Stopping randomization after a decision ends inference.** R10-DRIFT:61 and THEORY:533–536: a correct early running-target decision is not a guarantee about future benefit. Post-decision arrivals are single-arm, so they are operational/descriptive records only; point estimates at the stopping time are descriptive (optional-stopping bias), the anytime-valid band/e-value is the inferential statement.

---

## A. Statistical target, filtration, independence

1. **R9-GAP:21; R9-AUD:75–79.** A random permutation of a fixed roster is exchangeable, not iid, and does not imply the pointwise conditional null used by a betting process. → Target is declared as the running average of history-conditional pair means `μ̄_n` in enrollment order (R11-TGT:11–29); the monitor relies on `prop:bet_running` (THEORY:409; WINSTATS:64–73) or `thm:normal_cs`, neither of which needs constant means.
2. **R9-AUD:77,81; R10-REP:60; R11-TGT:20,48.** "Independent pairs" was asserted from disjoint tasks and separate calls; the design does not establish it. → The protocol never uses the word "independent" for pairs/episodes; the guarantee statement lists only adaptedness, boundedness, fixed stakes/weights/thresholds.
3. **R9-GAP:21; R11-TGT:86; R11-LED:8.** Coverage of `μ̄_n` was confused with coverage of the fixed-roster functional θ_N or a superpopulation mean. → One sentence in the protocol and every table caption names the target; no θ_N, no population win rate.
4. **R10-REP:68–70; R11-TGT:87; R15-REV:8.** The iid-roster model (R2) and its fixed-mean e-process guarantee are model-dependent and excluded from the paper. → No R2 reading is offered at all; if the pointwise-null reading is mentioned it is labelled "under an additional unverified model".
5. **R11-TGT:50; R12-COD:41–49; R13-INF:13.** The filtration contained the whole precomputed orientation sequence while the text treated the current coin as fair. → Coins do not exist before their pair is enrolled (OS entropy at enrollment); the protocol defines `H_i` (information used to form and randomize pair i), `F_{i−1} ⊆ H_i` (full records of pairs < i) and states that coin i and all later coins are outside `F_{i−1}`.
6. **R11-TGT:50; R12-INF:20; R13-INF:31.** A fixed pseudorandom seed is not repeated physical randomness and does not establish conditional fairness after past outcomes. → `os.urandom`/`secrets` per pair, no seed from which coins are reproducible; the coin byte, its source call and the monotonic timestamp are written to the hash-chained log *before* dispatch; a preflight statistical self-test of the entropy path is run on non-design draws only.
7. **R12-INF:20,39; R10-REP:104.** Replay coins applied to an already collected array give only an observed-array target ("a masking device on batches"). → No replay anywhere: the coin is drawn, logged, then only the assigned arm is executed for each position.
8. **R12-INF:20.** Collection, amendment, retry and retention decisions must not depend on the coins in a way that selects a favorable path; "human orientation-independence remains an assumption". → Dispatcher code path is arm-blind up to the point where the coin is read; retry/timeout/cap rules are identical for both arms and frozen; any operator intervention is a logged event with a reason code, and operator console output hides arm-level running outcomes until the decision event.
9. **R10-REP:60; R11-TGT:41–48; R13-INF:31.** The symmetric assignment-average formula needs a stable conditional joint episode law and no relevant order/position effects. → See K3: primary claim under the general history-conditional target; causal reading explicitly conditional.
10. **R10-REP:76–88; R12-COD:37; R11-LED:7.** Same-task (E2) uncertainty broke under shared orientation coins and pass/period effects. → Single exposure: there is no pass 2, no same-task estimand and no E1–E2 comparison in the new trial.
11. **R9-GAP:23; R9-AUD:87.** Estimates for different targets, sample sizes and interval constructions were compared as if commensurable. → One primary estimand per trial; every secondary quantity is tagged descriptive in the frozen analysis plan.
12. **R10-REP:90–96; R11-AIR:52–60; R12-COD:51–59; R12-INF:67.** Boundedness alone is not a CLT; task-t, Welch and cluster-t intervals were excluded. → No t/Welch/cluster-t/delta-method interval is produced by the confirmatory code; component summaries (latency, tokens) are counts, means and medians without intervals.
13. **R11-AIR:46; R12-INF:64.** The decided-pair win-ratio CS assumes a common conditional win probability. → Win ratio and win odds are printed as descriptive point values only (`winstats.summary`).
14. **R9-AUD:50–63.** The two-sided construction used max(K+,K−) at threshold 1/α (2α, not α). → Only root one-sided processes are used, each with its own prespecified α; no "two-sided 95%" object is formed from two one-sided ones without the stated allocation; a unit test asserts unit initial capital and E[capital after one fair ±1 step] ≤ 1.
15. **R10-REP:106–112; R11-AIR:116; R15-REV:7.** Contributed `src/wincs.py` endpoint inversion (0·log 0) and generic projection/width methods are unapproved. → The monitor and analysis import only `src/winstats.py` at a pinned SHA-256; `wincs` is not imported anywhere (R11-INT:42 is the accepted pattern); displayed bands use the closed-form `normal_mixture_radius`.
16. **R10-SEQ:113–114; THEORY:440–443.** The running-mean guarantee holds only for constant stakes per mixture component with fixed weights. → The frozen grid is exactly `geomspace(1e-4, .99/(1+c), 40)` with uniform weights (WINSTATS:80–85); no adaptive/predictable stakes.
17. **R10-SEQ:115; THEORY:529–532; R10-DISP:9.** Retaining an earlier gate crossing does not certify the current running target under drift. → Deployment requires all gates to exceed their `1/α_j` at the *same current enrolled prefix*; no retained-crossing variant is computed for decisions.
18. **R10-SEQ:116.** A fixed-threshold crossing guarantee is not a confidence sequence at a random or moving threshold. → Thresholds `c_0`, `−δ` are constants in the frozen config; bands are shown for description via the normal mixture, decisions come from fixed-threshold e-processes (or vice versa, but one rule is declared primary).
19. **R10-REP:58; R11-TGT:84; R12-INF:37; R13-INF:19.** Two separate 95% bands are marginal, jointly only ≥ 90%. → Σα_j ≤ α_trial is prespecified (`thm:drift_gate`, THEORY:495–511); every figure/table states each band's level and the joint guarantee.
20. **R10-REP:58; R11-TGT:29.** No running intersection may be taken for a moving target. → The band code has no intersection step; a test asserts it.
21. **R10-REP:62; R11-TGT:58,90; R11-LED:9; WINSTATS:55.** ρ, α and the analysis were fixed after outcomes (post hoc, not selection-adjusted). → α, α_j, ρ, stake grid, thresholds, hierarchy, tolerances, minimum n, look rule, horizon and action map are in a config whose hash is committed *and pushed* before the first design episode; the runner refuses to start on a hash mismatch (OWN-LS:153 item 3).
22. **R9-GAP:15.** One laboratory stream is not an empirical type-I-error experiment. → T4 (A/A) is described as one negative-control path; calibration evidence comes only from the CPU simulation in the protocol.
23. **R9-AUD:117; R12-INF:70; R13-INF:58.** A sample-size heuristic for one boundary is not a lower bound for every method. → Power/abstention probabilities are reported as "for this rule, this α split, this roster, from pilot resampling".
24. **R9-GAP:36; R12-EVID:42; R12-INTG:65.** Resource tiers decided almost nothing in airline (5 comparisons); a selection-advantage claim needs a prespecified informative comparison. → The protocol records, per trial, the pilot-expected share of pairs decided at each tier and preregisters the component-based comparator decision (success-only rule) to be reported beside the hierarchical rule, with agreement/abstention retained.
25. **R11-AIR:60; R13-INF:57.** Sensitivity rows are many correlated analyses; none may become confirmatory, and "all abstain" must be scoped to the primary rule. → Sensitivities are enumerated in the frozen plan, labelled descriptive, never feed the live decision.
26. **R10-SEQ:46; R10-DRIFT:98–100.** Different seed streams/studies must never be silently mixed. → Each trial T1–T4 has its own directory, log chain, config hash and entropy stream; pilot rows never enter a trial table.
27. **R9-SEQ:36; R9-GAP:25; R10-DRIFT:72.** "Holds its level" from a Wilson interval, or "error rate is zero" from zero observed errors, are overclaims. → Simulation tables in the protocol give counts, rates, pointwise Wilson intervals and say "compatible with".
28. **R10-DISP:11; R10-SEQ:32.** Summaries conditioned on rejection/crossing do not establish a mechanism. → Post-crossing diagnostics are labelled conditional descriptions.

## B. Randomization, exposure and live operation

29. **R9-AUD:46; R11-AIR:94–96; R12-SCOPE:38.** All-A-then-all-B batch collection carries period effects and is not randomized exposure. → Arms are interleaved by the per-pair coin inside one continuous session per trial; both arms' serving processes are resident for the whole trial.
30. **R11-AIR:96; R12-EVID:70.** Arms differed in serving arrangement (one vs two resident servers), so differences could not be attributed to the agent. → T3 keeps both model servers loaded throughout (two 4-bit ~7B models fit in 32 GB) regardless of which arm is running; T1/T2/T4 use one server for both arms; the arrangement is part of the frozen config and checked at preflight.
31. **R9-AUD:44; R10-REP:72; R11-TGT:58,120.** Crossings were recorded but never acted upon ("a decision that could have been taken"). → A crossing triggers a logged `DECISION` event that atomically switches the dispatcher; all later arrivals run the decided arm; the switch latency (crossing detected → first non-randomized dispatch) is measured. Pairs already enrolled at the decision time finish under their coin and are retained and flagged.
32. **R9-GAP:35.** Operational-latency evidence needs actual reveal timestamps, nonanticipating certificates, fixed endpoint horizons and the completed-prefix comparator. → Every episode has enqueue/dispatch/first-token/complete/verify timestamps from a monotonic clock plus UTC; each episode has a frozen hard timeout so a pending pair has a known worst-case score (timeout = failure); both the completed-prefix and enclosure statistics are logged at every event.
33. **ASYNC:77.** The hierarchy must not be refitted after a pending episode's partial outcome is seen. → Kernel code hash is in the frozen manifest; the monitor process loads it once and logs its hash in every `LOOK` event.
34. **R10-REP:98–104; R11-AIR:36,56; R12-EVID:105; R12-SCOPE:38.** Two seeds were reused across all tasks and both arms. → Every model request gets its own seed, drawn independently of the orientation coin, unique across the whole program, written into the request record before sending.
35. **R9-GAP:33; POLICY:11; R12-SCOPE:9.** Every enrolled unit, failure and unsuccessful hypothesis must be retained; excluding inconvenient observations is illegitimate. → Intention-to-treat scoring: an enrolled pair always yields a score; infrastructure failure or timeout of an assigned episode = unsuccessful for that arm (rule frozen); exclusions are only prospective and listed.
36. **R9-AUD:34,119; POLICY:11; QUEUE:36.** No reruns, extensions or model/seed selection to obtain a favorable result. → Maximum pairs, stopping rule and "abstain at horizon" are frozen; T3's model is named with its non-outcome rationale before any T3 outcome; a failed trial is reported, not repeated (a repeat would be a new registered trial with its own α).
37. **R9-GAP:15,23; R9-AUD:34; R10-REP:146; R11-TGT:85.** A harm crossing is not a symmetric guarded approval of the incumbent, nor safety/success harm. → Action labels are fixed: `DEPLOY_CANDIDATE`, `RETAIN_INCUMBENT (unfavourable composite signal)`, `ABSTAIN_AT_HORIZON`; T2 is described as "candidate rejected", never "A approved".
38. **OWN-T2:328–341; R9-AUD:93.** Units whose outcomes were seen in smoke/pilot use must be excluded or disclosed. → Smoke/warm-up uses out-of-design tasks only; pilot reuse of the roster is disclosed (K7).
39. **POLICY:21; OWN-T2:342–345.** A second concurrent model job or a stray server invalidates the frozen serving regime. → Exclusive lock file, preflight port/process scan, refusal to attach to an already running server, no other GPU job during a trial.

## C. Chronology, freeze and amendments

40. **R10-DRIFT:70.** Git first recorded the protocol together with final results, so freeze chronology could not be verified. → Protocol, config, harness and power analysis are committed and pushed (remote timestamp) before the first design episode; the pushed commit id and config hash are posted on the GitHub issue before starting.
41. **R11-AIR:72–76; R12-EVID:74; R12-LED:23; QUEUE:21.** The amendment's "decided" time was later than the amended invocation; no immutable record of decision time. → An amendment is a hash-chained `AMENDMENT` event (what, why, what had been seen per arm) followed by a pushed commit; the runner will not resume until the amendment hash it reads equals the one in the pushed commit; times are never typed by hand.
42. **R12-EVID:74.** File modification times are not tamper-evident; content ordering is. → Append-only JSONL with `prev_hash`, fsync per event; chain head committed and pushed at a fixed cadence (e.g. every 25 pairs and at every decision/amendment/resume).
43. **R10-REP:130; R12-EVID:76.** The cap/timeout amendment was made after seeing one arm's operational outcomes and was not outcome-blind. → Caps, timeouts and context limits are fixed from an out-of-design timing pilot and applied to both arms from episode 1; an emergency amendment applies to both arms, flags every unit with its regime, keeps all units in the denominator, and claims no counterfactual invariance.
44. **R9-AUD:93; R10-REP:124.** "Before any model call" was false; the accurate phrase is "before any design-task outcome". → The log has explicit phases `SMOKE`, `TIMING_PILOT`, `DESIGN`; the protocol uses the narrow phrase.
45. **R9-AUD:93; R10-DRIFT:70.** An internal timestamped freeze is not external registration. → Wording: "internally frozen protocol, publicly timestamped by a pushed commit and issue comment"; never "preregistered" without that qualifier.
46. **OWN-T2V:50; R12-EVID:80–85.** A file listed as frozen was edited post-freeze; both versions had to be recovered from git. → Harness file hashes are verified at every invocation and written to the manifest; any change = amendment (item 41).
47. **R13-INF:39; R13-PROV:64; R14-REV:29.** A verifier's PARTIAL verdict and pre-edit hashes were at risk of being presented as the final verdict. → Any owner-side verification report names the exact commit and file hashes it checked and is never edited after later changes; later checks are new files.
48. **R10-DRIFT:69.** Corrections to a frozen protocol must be errata, not silent edits that change the frozen hash. → Errata files; the frozen protocol bytes never change.

## D. Accounting for every attempt and all usage

49. **R11-AIR:62–70; R12-EVID:25–27; R12-LED:20.** Planned-unit completeness was not all-attempt completeness. → A request-level ledger (one row per HTTP request: `REQUEST_SENT` before, `RESPONSE`/`ABORT`/`TIMEOUT` after) and an episode-level ledger; both reconcile to the enrolled pairs by construction.
50. **R12-EVID:64–70; R12-INTG:51; R12-LED:22.** ≥ 246,284 generated tokens from failed/cancelled requests were missing, role split unknown. → Streaming responses with incremental token counts so an aborted request still has measured partial usage; server-side counters (requests, prompt/generated tokens) are snapshotted at trial start/end and reconciled with the client ledger; any residual is reported as a number.
51. **R11-AIR:22,68; R12-EVID:21.** Zero-duration placeholder records are not measurements of zero work. → Failure records carry measured elapsed time and usage; unknown = `null` with a reason, never 0.
52. **R10-REP:137; R12-EVID:87.** The canonical-outcome rule among retries was implicit (upstream returned the first non-exception trajectory and dropped placeholders on resume). → No episode-level retry (or exactly one, frozen, arm-blind); the canonical record is the first attempt; resume never deletes or reruns a logged unit.
53. **R10-REP:132; R11-AIR:9,66.** An interrupted invocation left no raw snapshot. → Because every event is fsynced before the next action, a crash leaves a valid chain; `RESUME` is an event; in-flight episodes at a crash are recorded as `INTERRUPTED` and scored by the frozen failure rule.
54. **R12-EVID:25.** Simulation-level attempts must not be conflated with model-request retries. → Separate counters and tables for episodes, model requests, connection retries.
55. **R12-EVID:68.** Smoke tokens are neither enrolled episodes nor failed-attempt usage. → Same ledger, `phase=SMOKE`, excluded from every trial total by phase, reported separately.
56. **R12-EVID:27.** `missing_outcomes: 0` hid missing rewards and discarded trajectories. → Summary fields are named precisely (`canonical_records_absent`, `episodes_with_missing_label`, `requests_without_usage`).
57. **R11-AIR:68.** Whole-run timing differed from the sum of retained durations. → Trial wall-clock, per-worker busy/idle time and per-episode durations are all logged; exposure/time summaries state which one they use.
58. **R11-EVID:39.** Future non-empty error fields must not be silently dropped by a projection. → The metrics projection keeps `error_present`, an error class code and retry counts for every row.

## E. Provenance, sampler receipt, reproducibility

59. **R12-EVID:105; R12-LED:24; QUEUE:21; OWN-T2V:54.** Request bodies and the server's sampler settings were not saved: "actual sampler receipt unverified". → For every request the log stores the exact JSON body sent (prompt by hash + length if large) and a server-side receipt of temperature, top-p, max tokens, seed and model id — either the server's echoed generation settings or a loopback logging proxy that records the bytes the server socket received; a preflight test proves the receipt path with a stub before the freeze.
60. **R9-AUD:109; OWN-T2:542–560.** The protocol said no seed was sent while the code forwarded one. → Every statement about what is sent is generated from a captured request of the frozen harness, not from reading documentation.
61. **R9-AUD:91; R11-EVID:132.** Per-call seeds were derivable but not explicit fields; Metal sampling is not bit-reproducible. → Seed is an explicit field of each request record; the protocol says "seeded requests; regeneration not bit-identical".
62. **R11-EVID:132; R12-EVID:99.** `mlx` version "unknown"; no complete environment lock deposited. → `pip freeze`, interpreter hash, OS build, server binary/commit and launch command line are in the manifest; preflight fails on any "unknown".
63. **POLICY:10; R12-EVID:91.** Model/tokenizer ids and revisions, quantization, runtime, hardware, endpoint config, seeds, manifest, completion counts, missingness and inference resources must be recorded; manifest consistency is not weight verification. → Weight file SHA-256 is recomputed at each invocation's preflight and compared with the frozen value.
64. **OWN-T2:346–349; R12-EVID:91; R11-AIR:36.** The served model id was checked for one role only. → Every response's `model` field is asserted against the arm's expected id; a mismatch aborts the trial with a logged event.
65. **R11-AIR:78.** Top-level run metadata showed the pre-amendment settings for a mixed file. → Settings are recorded per request, never only once per file.
66. **R11-AIR:80; R12-EVID:78; R11-INT:34.** Truncation (`finish_reason=length`) must be counted, request timeouts distinguished from episode timeouts, and the cap worded "1,024-token completion cap per call". → `finish_reason` per request; separate fields for request timeout, episode timeout, verifier timeout.
67. **R9-AUD:105; R11-EVID:134.** Benchmark URLs were mutable; pinned bytes were matched only retrospectively. → Task sources are pinned by commit and raw-byte SHA-256 before the freeze (already available: MBPP `f82046b…`, HumanEval `463c980…`, canonical task-list hash `2372789…`); note "all 427 sanitized MBPP tasks, not a test split".
68. **R9-AUD:105; R10-REP:114–120; R12-COD:15.** A manifest lived under a git-ignored `work/` path and a mapped anonymous copy was missing from the tree. → All manifests live under `results/<trial>/`; a check asserts every path named in any mapping exists in the git tree (COORD:20 still keeps raw third-party data itself out of git).
69. **R11-EVID:56–65; R11-LED:12.** Raw episodes contain generated programs, reference-solution overlaps, assertion text and user paths. → Deliver a deterministic row-preserving *metrics projection* (no `final_code`, `self_test_code`, `verify_stderr`, tracebacks) plus original/derived hashes; raw file kept privately with its hash.
70. **R11-EVID:54.** Original and derived hashes must not be interchanged, nor a projection called raw. → Two separate hash tables in `provenance.json`.
71. **R11-EVID:65; R10-REP:9; R11-REL:30.** An aggregate reproduction entry point must never execute generated programs, collectors or models. → `analysis/` has no import path to harness, sandbox or HTTP client; a test greps for it.
72. **R10-REP:29; R11-REL:38.** Outputs with embedded timestamps needed exceptions for byte-identity. → Analysis outputs are deterministic and timestamp-free; run metadata goes to a sidecar.
73. **R10-REP:33; R10-REL:34.** Figure/PDF bytes differ across environments. → Hash the numeric inputs of figures; never claim pixel identity.
74. **R12-INF:72.** A consistency checker proves reproducibility of numbers, not their sampling assumptions. → The owner-side verifier report says exactly that.
75. **OWN-LS:153–160; R9-AUD:97; R11-INT:38.** Hidden-test leakage, sandbox containment, verifier sentinel and absence of verifier feedback in repairs were audited for the existing harness. → Reuse `agent.py`, `verify.py`, `sandbox.py` byte-identically (hash-pinned to the audited versions); any change needs a new leakage/sandbox audit before the freeze; record the seatbelt profile hash per episode.
76. **R9-AUD:97; R12-LED:21.** Success is the archived verifier label, not semantic correctness or an independent re-adjudication. → Wording; keep verifier return code, sentinel flag and verifier time per episode.
77. **R11-INT:24.** "Subtract one verifier execution per row" was valid only for that frozen dataset. → `n_self_test_executions` and `n_verifier_executions` are separate fields from the start.

## F. Metric definitions and resource claims

78. **R9-AUD:98,100; R11-EVID:130; R11-TGT:89.** Workflow latency ends when the final candidate exists and excludes hidden verification and model loading; `n_executions` included the verifier. → Same definitions frozen; additionally record queue wait (enqueue → dispatch) separately, since concurrency introduces it.
79. **R11-AIR:96.** Latency labels of different experiments (agent workflow time vs whole-dialogue duration) must not be merged. → The new metric gets its own name (e.g. `service_latency_s` under 2-worker load) and is never pooled with pilot `latency_s`.
80. **R9-AUD:99; R11-EVID:94; R12-EVID:70.** Tokens are not dollars, energy or compute; prompt tokens must stay visible; native token counts are not comparable across tokenizers/models. → Report prompt/completion/total separately; for T3 (different model family) the token tier is either dropped from the decision hierarchy or replaced by a tokenizer-neutral unit (generated characters/bytes) — decided and justified before the freeze.
81. **R9-AUD:101; R11-TGT:89.** Ratios (4.46×) are for this host and workload; no hardware-invariant ordering. → Wording; hardware/runtime block beside every resource table.
82. **R12-EVID:70; QUEUE:17.** No "operational efficiency" claim from saved-trajectory totals that omit failed work. → Efficiency statements use failure-inclusive totals from item 49–50 only.

## G. Paths, anonymization, release hygiene

83. **R9-AUD:107; R11-AIR:90; R11-EVID:67.** Manifests, configs, logs and tracebacks contained personal absolute paths and host metadata. → The runner writes repo-relative paths, sets a neutral `TMPDIR`/sandbox root, records host facts from an allowlist (chip, RAM, OS build) and never dumps process listings; tracebacks are stored as class + hashed text in the public record.
84. **R10-REL:19–21; R10-DISP:17.** A sanitizer that only matched `/Users/` missed a username inside a temp path. → Release check scans for the username, repo name and every absolute path pattern in *all* text members, not a prefix.
85. **R9-AUD:107.** "Do not rewrite raw evidence merely to conceal provenance." → Raw log is immutable; sanitized copies are separate files with an original→release hash map.
86. **R10-REP:34,120.** Anonymized-copy regeneration depended on the executing account/location. → Sanitizer operates on relative paths and fixed replacement tokens, so it is location-independent; still no byte-identity claim across machines unless tested.
87. **R11-EVID:16,67.** Anonymous copies must omit researcher repo URLs/commit ids (kept in the private record). → Still produce both variants even though the target is now arXiv, because the root's package is built as `anonymous_code.zip`.
88. **R11-AIR:90.** Benchmark-internal synthetic names/emails are not author identifiers and must not be blindly deleted. → Not relevant for coding tasks; noted for any future interactive arm.
89. **R11-REL:74–76; R12 release audit:81.** Anonymity scans are bounded known-pattern checks, not proofs. → Wording in any release note.

## H. Licensing and execution policy

90. **POLICY:7,9.** No commercial/proprietary model call of any kind (agent, simulator, judge, fallback), no stored API credentials, no silent fallback. → HTTP client hard-asserts a loopback base URL, no API-key environment variables are read, preflight fails if one is present in the process environment; no LLM judge — success is the executable verifier.
91. **POLICY:8.** No new cloud/hardware purchases; check disk before installs; weights outside git; never delete unrelated user files. → Preflight disk check; weights under the HF cache; `.gitignore` check.
92. **POLICY:10; R12-EVID:101.** "Open weights alone do not establish an unrestricted license"; for one GGUF repo the card pointed to the base-model license and no LICENSE file existed at the pinned revision. → For the T3 model family (Apache-2.0/MIT) record: repo id, revision, the LICENSE file's SHA-256 *at that revision* (or the explicit statement that only the card declares it, plus the base-model license link), and the quantizer's repo if it is a community conversion.
93. **R11-EVID:136.** MBPP is CC-BY-4.0, HumanEval MIT, and the HumanEval data-file revision predates the LICENSE path. → `SOURCE_NOTICES.md` with attribution (Austin et al.; Chen et al.), license provenance recorded separately from the data revision.
94. **R11-EVID:138.** The research harness has no top-level LICENSE; model/dependency licenses do not confer one. → Do not describe the harness as MIT/Apache; raise the code-license question for the arXiv code release with the root/author.
95. **POLICY:15.** Historical commercial collection scripts are provenance only and not authorized for execution. → The new runner shares no entry point with them.

## I. Wording and claims (each was an explicit root correction)

96. **R12-INF:64; R13-INF:20.** "Significantly fewer" resources without a valid test. → Banned phrase.
97. **R12-INF:65; R13-INF:44.** "Not certifiable whatever the method" / "cannot resolve" — method-independent impossibility. → Say "this prespecified rule did not certify margin δ on these data".
98. **R10-REP:84; R12-INF:70; R11-TGT:96.** "Assumption-free", "Neyman-conservative", "conservative" without conditions. → Name the coin model and the filtration instead.
99. **R11-AIR:60; R12-INTG:57; R11-EVID:128.** Equal observed success is not equivalence or non-inferiority. → Only a gate crossing at the frozen margin is called non-inferiority, and then "at margin δ for the running target".
100. **R9-AUD:44; R12-SCOPE:38; R13-DISP:49.** Laboratory stream ≠ production A/B; no production users. → "Live-stopped laboratory A/B trial on a fixed benchmark roster"; never "production", "deployment to users".
101. **R11-TGT:96.** Avoid "prospective CS stopping", "live savings", "population win rate", "joint 95% certification", "A approved by the success guardrail" when not literally true. → In the new trial "prospective stopping" becomes true only if items 21, 31, 40 hold; the other phrases stay banned.
102. **R9-AUD:38.** Dry-run/MOCK outputs must never be cited as observations. → Dry-run directories carry a MOCK banner and are excluded from every builder by path.
103. **R12-COD:61–65.** Descriptive period/composition differences were attributed to one cause. → "mixes … cannot separate".
104. **R12-INF:100.** "Token usage is unavailable" vs "complete failed-attempt token usage is unavailable". → Precise scope words in captions.
105. **R13-PROV:65.** "Generated arm-A tokens" was less clear than "A-collection generated tokens; role partition unavailable". → Name the collection and the role.
106. **R9-AUD:9.** An OpenAI-compatible local endpoint is not a commercial call, and the text must make that unmistakable. → "loopback OpenAI-compatible interface to a local open-weight model".
107. **R10-DRIFT:61; THEORY:533–536.** An early correct decision is not a statement about future effectiveness after workload shift. → Post-decision section is titled "operational record", not "validation".
108. **Every review header (e.g. R11-INT:3; R12-INTG:5).** AI review is not human peer review or author sign-off. → Same disclaimer on all session-60 verification files.

## J. Versioning and preservation

109. **R9-AUD:63; R10-REP:52; R12-EVID:85.** Old outputs must be preserved and corrections versioned (v2, v3 …), never overwritten. → New trial writes only under new directories (e.g. `experiments/live_ab/`, `results/live_ab/T1…T4/`); reports are versioned files generated by committed generators.
110. **R13-DISP:24; R14-DISP:9; R15-DISP:7.** The root verifies by Git blob identity that all prior owner files (221 → 229 → 236) are unchanged. → The new work must not touch any existing file under `experiments/{local_stream,tau2_open}` or `results/{local_stream,tau2_open}`; the only shared file that may change is `results/SESSION60_RESULTS_INDEX.md`.
111. **R10-REP:122–124; R12-COD:16.** The PR body advertised superseded numbers. → PR body is regenerated from the current report at each handoff and points to the governing report version.
112. **R13-DISP:41; R13-INF:60; R14-DISP:17–20; R15-REV:7–8.** Index headlines were stale and grouped excluded methods with verified ones. → Index rows separate: observations / retained root analysis / owner descriptive readings / excluded methods.
113. **R13-INF:55; R13-PROV:63; R14-REV:21.** Supersession pointers listed the older addendum first. → Exactly one governing document per trial, named first everywhere.
114. **R13-PROV:62.** Manifests contained passage digests, not text, but said "passages". → Describe manifest contents literally.
115. **R14-REV:11.** Counts must be actual, not assumed ("rather than an assumed 231-file denominator"). → Handoff notes quote counts produced by a command that is included.
116. **R9-GAP:27; R12-SCOPE:42.** The delivery ledger must separately record collection status, audited observations, accepted analysis, manuscript claims, excluded methods, deferred extensions; unexecuted parts are "deferred", not silently dropped. → A `DELIVERY_LEDGER.md` per trial with exactly those headings.
117. **COORD:21.** Every table/figure in `results/` must be regenerable by a script in `experiments/` with a manifest (seed, config, code hash). → One `build_live_ab_results.py`, stdlib + `winstats` only.

## K. Collaboration protocol

118. **COORD:44,50; QUEUE:42.** New experiments live in separate directories/branches and return a pull request; never rewrite main, the paper or existing result files. → New branch from current `origin/main` (e.g. `session60/live-ab`), PR to main.
119. **ALLOC:9; QUEUE:42; user memory.** No reset, clean, rebase, force-push, or branch switching in another worker's tree; merge main, never rebase. (COORD:17 still says `pull --rebase`; the later allocation and the user's standing instruction supersede it — follow merge-only and say so in the PR.)
120. **POLICY:21; ALLOC:7.** Root owns `paper/`, `src/winstats.py`, shared status/queue, `results/open_*` and builders; changes to owned code go to the owner as a concrete review request. → If the trial needs anything changed in `winstats.py` (it should not), open an issue; never patch it.
121. **COORD:25–29; QUEUE:35.** Work is claimed through the queue/issues with a self-contained spec. → Open a GitHub issue "Conditional experiment: prospective randomized live-stopped trial" containing the frozen protocol hash, resources (M5/32 GB, expected hours), outputs, and ask the root to confirm that the monitoring rule is its accepted construction *before* the first design episode.
122. **QUEUE:44; R12-LED:8; R13-DISP:49.** Issue closure or integration is never whole-PR approval; the root integrates by its own projection/builder. → Shape the handoff like the accepted ones (R11-EVID:9–41; R12-EVID:109–116): metrics projection, design/assignment log, config, provenance, attempt ledger, nonexecuted `.txt` source snapshots, hashes.
123. **COORD:19.** No credentials in the repo or logs. → Environment dump in the manifest is allowlisted.
124. **POLICY:21.** No duplicate run of an owned experiment. → The pilot collections are not repeated; the new trial is a different, registered study.

---

## (i) Claims the new trial MAY make if it succeeds — and claims it must NEVER make

**May claim (each only if the listed condition is literally true):**

1. "A prospectively frozen, physically randomized (fresh OS-entropy coin per arrival pair, logged before execution), single-exposure, live-stopped laboratory A/B trial on N fixed benchmark tasks with open-weight models on one Apple M5." (items 5–7, 21, 31, 40)
2. "The monitoring rule was the fixed-stake betting / normal-mixture construction of `src/winstats.py` at SHA … with α, α_j, ρ, thresholds, hierarchy and horizon frozen before the first design outcome; under adaptedness and boundedness, the probability that the rule deploys at any enrolled prefix at which some running conditional-mean criterion is false is at most α_trial." (items 1, 16–19)
3. "In trial Tk the rule crossed at enrolled pair n (calendar time t), the dispatcher switched at t′, and the remaining M arrivals ran under the decided arm." — a measured event, not a replay. (item 31)
4. "Relative to the prespecified fixed-horizon randomized design, the decision avoided ⌊remaining pairs⌋ exposures to the rejected arm" (exact design quantity), plus measured trial wall-clock/tokens; any time/token "saving" labelled *projection from pre-decision means*. (K4)
5. "Outcomes were revealed out of enrollment order with recorded timestamps; the completed-prefix rule and the partial-information enclosure rule reached their decisions at calendar times t₁ and t₂" — a measured comparison *for this run and serving regime*. (K2, item 32)
6. "Failure-inclusive usage accounting reconciles client and server counters to within X tokens; every request's sampler settings were recorded as received." (items 49–50, 59)
7. T2: "the prespecified rule rejected the candidate (unfavourable composite signal); the incumbent was retained". T4: "in one A/A control path no gate crossed" (or, if one did, report it as the ≤ α event it is). T3: whatever happens, including abstention. (items 22, 35–37)
8. "The success-difference gate at margin δ crossed / did not cross"; non-crossing is reported as abstention. (K5, item 99)

**Must never claim:**

1. Production A/B evidence, user benefit, deployment safety, or "deployed" without "in the laboratory dispatcher". (100)
2. A population / fixed-roster / superpopulation / fresh-task effect, or iid-task inference. (3, 4)
3. Empirical calibration or type-I-error control from one or four streams. (22, 27)
4. Equivalence or non-inferiority from equal or similar success counts. (99)
5. "Approval of A", "A satisfies the guardrail", or success/safety harm from a composite harm crossing. (37)
6. Joint 95% coverage from marginal bands; "two-sided 95%" from two one-sided level-α processes; program-wide α when each trial used α. (14, 19, K6)
7. Significance of resource differences; t/Welch/cluster intervals; win-ratio confidence sequences. (12, 13, 96)
8. Hardware-, model-, workload- or tokenizer-invariant rankings; dollars, energy or "compute" from token counts; cross-model token comparisons as cost. (80, 81)
9. Causal assignment-average interpretation without the explicit no-interference/stable-law assumption, given two workers share one GPU. (K3, 9)
10. Measured time/token savings derived from counterfactual or replayed paths; per-task "operational cost" from retained-only totals. (K4, 82)
11. "Preregistered" without "internally frozen, publicly timestamped"; "before any model call". (44, 45)
12. Bit-reproducible generation; independent re-adjudication of success labels; exhaustive correctness. (61, 76)
13. "Assumption-free", "impossible for any method", "holds its level", "error rate is zero", mechanism claims from post-crossing diagnostics. (27, 28, 97, 98)
14. That post-decision single-arm data validate the decision or future benefit. (K8, 107)
15. That the hierarchical rule is generally better than component rules, from one contrast where few pairs resolve on resource tiers or where the answer was known from the pilot. (24, K7)
16. That the root "approved" the trial, PR or methods beyond what a root disposition literally states. (122)

---

## (ii) Pre-registration content checklist (what the frozen protocol must contain so the root can accept without a repair round)

**Identity and scope**
- [ ] Trial ids T1–T4; for each: incumbent, candidate, model repo id + revision + weight SHA-256 + quantization + license evidence (92), serving stack + commit + launch command, host, number of workers, resident servers.
- [ ] Statement that the 1,182 pilot episodes informed hierarchy, tolerance, margin, hypotheses and power; that T1/T2 outcomes are predictable from the pilot on the same roster; that T3 is the only contrast with unknown outcome; whether trials share the roster or use disjoint blocks (K7).
- [ ] Laboratory scope sentence; no production users; open-weight only; loopback only (90, 100).

**Design and randomization**
- [ ] Roster: pinned sources, canonical task-list hash, prospective exclusions, arrival permutation procedure (may be seeded and frozen — it is *not* the assignment mechanism) and its hash.
- [ ] Unit of randomization = disjoint consecutive arrival pair; coin q = 1/2 from OS entropy at enrollment; exact code path; logged-before-dispatch invariant; treatment of the odd leftover arrival (K1, 5–7).
- [ ] Dispatcher/concurrency rule (work-conserving, 2 workers), what may overlap, and the overlap record per episode (K3).
- [ ] Per-request seed policy (unique, independent of coins, logged) (34).
- [ ] Sampling settings, completion cap per call, context limit, request timeout, episode hard timeout, verifier timeout — all from an out-of-design timing pilot (43, 66).

**Estimand, filtration, monitoring rule**
- [ ] Kernel: tiers, directions, relative-max tolerance with strict `>`, eligibility after joint success, joint failure = tie (R11-EVID:98); kernel code hash.
- [ ] Scores `Z_i` (hierarchical) and `D_i` (success difference); ITT failure rule for timeouts/infrastructure errors (35).
- [ ] Filtrations `H_i`, `F_i` in enrollment order; statement that coins ≥ i are outside `F_{i−1}`; target `μ̄_n`, `ν̄_n`; which assumptions are needed for which reading (general vs causal) (1–5, 9).
- [ ] Monitoring statistic: `winstats.betting_log_e_ternary` (bets = 40 grid) and/or `normal_mixture_radius` (ρ), file SHA-256; thresholds `c_0`, `−δ` with the *rationale for δ*; α_program, α per trial, α_j per gate, deploy-vs-harm allocation; same-current-prefix conjunction; no retention; no running intersection (14–20, K5, K6).
- [ ] Asynchronous rule: primary = completed enrollment prefix `N(t)`; secondary = enclosure bounds with worst-case pending scores; when looks occur (every reveal event); minimum n if any (K2, 32).
- [ ] Action map and live switch semantics; treatment of pairs in flight at the decision; horizon and `ABSTAIN_AT_HORIZON` (31, 37).
- [ ] What is descriptive only: point estimates at stopping, win ratio, component summaries, sensitivities (enumerated), post-decision records, component-rule comparator (11–13, 24–25, K8).
- [ ] Definition of "exposures avoided" (exact) and of the projected time/token saving (formula, labelled projection) (K4).

**Power analysis (CPU, from pilot)**
- [ ] Script + seed + output hash; operating characteristics per trial: P(deploy), P(harm), P(abstain), stopping-pair distribution, for the frozen rule; A/A false-crossing rate with Wilson interval; explicit statement of guardrail power at the chosen δ (K5, 23, 27).

**Logging and provenance**
- [ ] Event schema (`ENROLL`, `COIN`, `DISPATCH`, `REQUEST_SENT`, `RESPONSE|ABORT|TIMEOUT`, `EPISODE_END`, `VERIFY`, `REVEAL`, `LOOK`, `DECISION`, `SWITCH`, `AMENDMENT`, `RESUME`, `ANCHOR`), hash-chain definition, fsync rule, anchor cadence and push rule (41–42, 49–53).
- [ ] Sampler-receipt mechanism and the preflight proof that it records what the server received (59–60).
- [ ] Usage reconciliation procedure between client ledger and server counters; smoke phase tagging (50, 55).
- [ ] Manifest contents: environment lock, harness file hashes verified per invocation, model-id assertion, weight hash preflight, seatbelt profile hash (46, 62–64, 75).
- [ ] Exclusive-use lock and preflight server scan (39).

**Amendments, deviations, stopping the study**
- [ ] Amendment procedure (logged event + pushed commit before resume; both arms; unit regime flags; no invariance claim) (41, 43).
- [ ] Crash/resume procedure; no deletion or rerun of logged units (52–53).
- [ ] "No extension, no rerun, no model/seed reselection; failed hypotheses retained" clause (36).

**Deliverables and claims**
- [ ] Output file list, deterministic builder (stdlib + `winstats`), metrics projection spec, original/derived hash tables, sanitized-copy rule, `SOURCE_NOTICES.md`, `DELIVERY_LEDGER.md` (69–72, 83–87, 93, 116–117).
- [ ] The allowed/forbidden claim lists of section (i), copied into the protocol.
- [ ] Freeze record: commit id pushed before the first design episode, config hash, GitHub issue link where the root confirmed (or was asked to confirm) the monitoring construction; phrase "before any design-task outcome" (40, 44–45, 121).
- [ ] Disclaimer that owner-side verification is AI review, with exact commits checked (47, 108).
