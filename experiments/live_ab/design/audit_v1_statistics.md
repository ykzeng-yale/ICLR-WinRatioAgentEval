# Audit v1 of `protocol_draft_v1.md` — lens: STATISTICAL VALIDITY

Auditor: adversarial pre-registration auditor (statistics), session 60, 2026-09-19.
Read in full: `protocol_draft_v1.md` (844 lines), `R1_accepted_method.md`, `R2_constraints_checklist.md`,
`R3_harness_plan.md`, `R4_power_analysis.md`; consulted `paper/theory.tex:179-563`, `paper/asynchronous.tex:55-84, 369-400`,
`src/winstats.py`, `EXPERIMENT_QUEUE.md`, `P5_supp_power.py/.md`. No git state change, no model call, no download.
One CPU check (< 2 s) with `.venv/bin/python` and `src/winstats.py`; its numbers are quoted in F8 and F6.

## Verdict: **FIX-THEN-FREEZE**

The core error-control argument (fresh pair coin drawn after the previous pair is fully revealed; scores adapted and in
[-1, 1]; fixed 40-stake grid; `prop:bet_running` per gate; union bound over NB, S, H at one current prefix; first
crossing acts; no retention) has no hole that I could construct a counterexample against. The freeze is nevertheless
not allowed yet: two paths that the draft itself opens lose either the "frozen before outcomes" property (F1) or the
definition of the primary result (F2), and eleven further items misstate an estimand, a theorem's coverage, the
multiplicity accounting, an endpoint rule or a claim. None requires a redesign of the randomization or of the monitor.

Severity scale used here. BLOCKER: as written, a permitted path loses the central guarantee, the "fixed before
outcomes" property, or leaves the primary result undefined. MAJOR: error control survives, but an estimand, theorem
coverage, multiplicity statement, endpoint rule or claim is wrong, ambiguous or overstated. MINOR: arithmetic, wording,
verifier invariants.

---

## BLOCKERS

### F1 (BLOCKER). The freeze does not bind across trials; the T4-first "defect" path and between-trial amendments re-open every parameter after design-task outcomes of the same systems on the same tasks

Passages.
- 1.1: "It consists of four **separately frozen** trials" versus 12.1 title "Freeze procedure (**one freeze for all four trials**)".
- 12.4: "T4 first, so that a plumbing defect is found where it costs no claim".
- 12.2: "Monitoring parameters (...) cannot be amended **within a trial**; changing any of them (...) ends the trial".
- 12.1 step 3: "The freeze waits for the root's answers" (nothing about answers that arrive after T4 has started).
- 3.4 item 2: "No outcome of the new trials is known".

Why it fails. T4 executes `single_shot` on the new stack on every paired task of the roster (both "arms"), and the
post-decision phase of T2 executes `single_shot` on all remaining arrivals plus about 50 to 65 `self_test_repair`
episodes. Before T1 starts, the operator therefore holds the new-stack success label of the T1 candidate for essentially
every task and a sample of the T1 incumbent. Scenario: T4 exposes a harness defect (the stated purpose of running it
first). Fixing it changes a `lab_*.py` hash, hence the freeze bundle (12.1 step 5), hence a new freeze is needed for T2,
T1, T3. Nothing in the draft forbids changing `delta`, the level split, the strata, `N_P`, the hierarchy or the driver
in that second freeze; 12.2 only forbids it "within a trial". The second freeze is then "frozen before any design-task
outcome" of T1 only in the trial-local sense, while 1,000+ outcomes of the same two systems on the same tasks are
known. That is criticism no. 1 of Rounds 9 to 15 (parameters fixed after outcomes) re-created by the protocol's own
contingency plan. The same hole exists without any defect: a root answer to C3/C4/C5 that arrives after T4, or a plain
between-trial amendment, is not excluded. There is also no rule that T2, T1, T3 must be started whatever T4 and T2
showed; "not starting T1 because T4 showed 64% single_shot success" is a selective-reporting path.

Required change.
1. Replace "separately frozen" in 1.1. State one program freeze and the sentence: "All statistical parameters of all
   four trials (levels, thresholds, delta, grid, `n_min`, hierarchy, tolerances, strata, arrival orders, `N_P`, driver,
   harm rule, secondary levels, failure-to-outcome rules, execution parameters of 5.5) are immutable from the first
   design-task outcome of the **program** (first T4 episode)."
2. Defect path, written out: after the program has started, harness code may change only by an amendment (12.2) that
   touches no item of the list above; the verifier must show that the amended harness reproduces every earlier
   `monitor_update`; T4 is not rerun (or a rerun is "T4b", a new trial with its own level, reported next to T4).
   If a listed item must change, every not-yet-started trial is relabelled "parameters fixed after N program outcomes
   of the same systems on the same tasks" and loses claim 1.3(1)-(2) wording.
3. Unconditional execution: each trial starts when the previous one ends; the only admissible reasons for not starting
   are the operational reason codes of 12.4, none of which may refer to an outcome; a trial not started is reported
   under its own heading.
4. Root answers received after the first T4 episode cannot change any trial; the fallback in force at the freeze governs.
5. Correct 3.4 item 2: outcomes of T4 and T2 are known before T1 and are outcomes of T1's systems on T1's tasks; the
   defence is the program freeze, not ignorance.

### F2 (BLOCKER). The primary result is undefined when the live monitor and the frozen rule disagree; the replay rule after a monitor failure collides with "no retained crossing"

Passages.
- 9.2: "The primary result of a trial is the logged decision (...) the recomputation must reproduce every `monitor_update` and the `decision` exactly."
- 6.4 row 17: "monitor exception | dispatch pauses (...) after an amendment (12.2) the monitor is replayed from the log, which is legitimate because it is a pure function of logged events".
- 8.2: "No retained crossing: only the current prefix counts".

Why it fails. "Must reproduce" is an acceptance test without a consequence. Two silent-defect scenarios (no exception,
so row 17 never triggers):
(a) the live S gate is evaluated with a sign slip; T1 runs to `N_P` and logs `ABSTAIN_AT_HORIZON`; the verifier's
replay of the frozen rule crosses at pair 263 and, because the wealth is not monotone (pilot: above threshold at pairs
14 and 24, below until 48), is below threshold again at pair 300. Is the primary result ABSTAIN (what happened),
DEPLOY at 263 (what the frozen rule says; a retained crossing relative to every later prefix), or nothing?
(b) a defect makes the live monitor deploy at pair 180 where the frozen rule does not cross. Randomization has stopped;
the frozen rule can never be evaluated beyond 180.
Whichever reading is chosen afterwards is a post hoc choice of the primary analysis. With an exception (row 17) the
same question appears if the defect is older than the exception: replay may find a first crossing at n* earlier than
the pause prefix n, with pairs n*+1..n randomized after the frozen rule had already decided.

Required change. Add to 9.2 a disagreement rule fixed now: (i) the statistical claim of a trial is always the frozen
rule replayed by the independent verifier, at its **first** crossing prefix n* >= `n_min` (time-uniform validity covers
that prefix; say explicitly that this is the first crossing, not a retained one, and that pairs after n* are reported
as "randomized after the rule's decision", outside monitoring); (ii) if the live decision differs from the replay in
kind or prefix, the trial is reported as "rule-execution failure": claims 1.3(3), (4), (5) (live switch, exposures
avoided, timing) are dropped for that trial, and no statistical claim is made for a live decision that the replay does
not reproduce; (iii) the verifier's reference implementation of 8.1 to 8.3 is part of the freeze bundle and cannot be
amended; row 17 amendments may change only the live monitor so that it equals the reference.

---

## MAJOR

### F3 (MAJOR). Attempts that do not return are redrawn; this contradicts "no early termination", "no episode-level retry" and the paper's "timeout is an endpoint", and the trigger is arm-differential

Passages.
- D15 / 8.7: "No episode is ever terminated early"; 6.1: "nothing terminates it early"; 5.5: "There is **no episode-level retry**".
- 5.5: "`episode_hard_cap_s` | 1,800 | watchdog; exceeding it is handled as a dead worker"; 6.4 row 10: "worker dies, or `episode_hard_cap_s` exceeded (worker killed) | `attempt_aborted`; new worker; same arrival, same arm, `attempt + 1`"; 5.5: "the canonical record of an arrival is the first attempt that returns".
- 6.4 row 11 lists "operator stop" as a cause of re-runs, while 12.4 says "A trial may be paused only between pairs".

Why it fails. The watchdog does terminate an episode early, and the arrival then receives a fresh draw (new seed via
`attempt`). "First attempt that returns" is the airline study's "first non-exception trajectory" rule (R2 item 52) in
prespecified form. `paper/theory.tex:555-563` says failure to reach the outcome by the horizon "is an endpoint, not an
observation to discard". Only one arm can plausibly hit the cap or kill a worker during its own workflow
(`self_test_repair`: four model calls plus sandboxed self-tests; `single_shot` runs no sandbox inside the workflow), so
in T1 and T2 the redraw privilege belongs to one arm. Error control survives (adapted, bounded, arm-blind rule), but
the scored system silently becomes "workflow + up to three draws on hang", the success gate is moved in favour of the
arm that hangs, and three internally contradictory sentences are frozen. A mid-pair operator stop (allowed by row 11,
forbidden by 12.4) is a redraw that a human can trigger while seeing the partner's revealed outcome.

Required change. (i) An attempt that ends for a cause inside the episode (hard cap, worker death during `run_episode`,
sandbox or client fault) is terminal: `success = 0`, `latency_s` = certified elapsed time (or the cap), tokens = known
tokens, no re-run. (ii) Re-run only after events that kill every in-flight episode regardless of arm (orchestrator
crash, power loss), with the existing orphan rule. (iii) Operator stops drain: in-flight episodes finish before the
process exits; a hard kill is a logged protocol deviation and the pair gets `infra_flag`. (iv) Delete or reword D15,
6.1 and 5.5 so that one rule remains. (v) State in 6.1 that request-level timeout retries (new `try_index` seed) are
part of the system definition, and report their count by arm. If the coordinator keeps the redraw, then the estimand
text must name "workflow plus three-attempt harness", redraw counts by arm go into 14, and a sensitivity that scores
every aborted first attempt as failure is prespecified.

### F4 (MAJOR). Endpoint-defining execution parameters stay amendable inside a trial while gate statistics are public to the operator; the ten-abort clause grants discretion

Passages.
- 12.2 non-amendable list: "levels, thresholds, delta, grid, `n_min`, hierarchy, tolerances, horizon, driver, harm rule" and "any system version (model file, server build, prompts, sampling)". Not listed: `request_timeout_s`, `max_connection_retries`, `server_recovery_s`, sandbox limits, `max_repair_rounds`, `episode_hard_cap_s`, `max_attempts`, `W`, server argv.
- 12.4: "ten consecutive `harness_abort` outcomes (pause, then amendment **or** abort)".
- 12.4: "The operator console shows (...) no gate statistic before the decision event" versus 11.4: the anchor process "commits `events.jsonl`" and pushes every 25 pairs; `events.jsonl` contains every coin, every outcome by arm and every `monitor_update` with the three log E.

Why it fails. Success includes timeouts and sandbox kills, so these parameters define the endpoint. Scenario: T1 at
pair 300, S-gate log E 2.9 against 3.22; several incumbent episodes failed by request timeout (each such pair is
D = +1 for the candidate). Amending the timeout upward removes those wins, not amending keeps them; either choice is
made by someone who can read the statistic in the pushed log. `prop:bet_running` tolerates a predictably changing law,
so the 0.05 bound is not the casualty; the casualty is the frozen system (`theory.tex:334-338`: a changed version
"should ordinarily start a separately specified experiment") and the root's Round 10/12 objection to cap and timeout
amendments made with outcome knowledge. "Amendment or abort" after ten aborts is an unguided choice with the same
information. The console blinding is nominal as long as the full log is pushed.

Required change. (i) Add all parameters of 5.5, `W`, and the server argv to the non-amendable list; a needed change
ends the trial. (ii) Replace "amendment or abort" by a deterministic consequence (`trial_aborted(operational)`).
(iii) During the randomized phase the anchor commit contains only the anchor file (`upto_seq`, `upto_h`, log length,
log SHA-256); `events.jsonl` is committed at `decision` and at `trial_ended`. The timestamp evidence is unchanged and
the blinding sentence becomes true; otherwise delete the blinding sentence and list "operator can read gate statistics"
among the assumptions. (iv) Keep the statement that an abort can only remove decisions, never create one, and add that
program-level reporting lists every abort with the gate statistics at abort.

### F5 (MAJOR). `thm:pair_id` does not cover the design "verbatim"; the stated interpretation of `nu_i` is false under within-pair interference; the description of `F_0` contradicts the carry-over sentence

Passages.
- 7.4: "Consistency therefore holds, the proof of `thm:pair_id` goes through verbatim".
- 9.1: "`nu_i` that of the average same-task success effect of the two tasks of pair `i`"; 3.5: "the pair target is the average same-task success effect (...) so over the full roster the success target does not depend on how pairs are formed".
- 7.2: "`F_0` also contains, for every pair and each of its two orientations, the potential records" versus 7.4: "Carry-over from earlier pairs (...) may change the potential records of pair `i`".

Why it fails. The theorem's hypothesis is "There is no interference between the two positions" (`theory.tex:185`). The
draft replaces it by orientation-indexed potential outcomes. That gives `E(Z_i | H_i) = (U_i + V_i)/2` with `U_i`, `V_i`
the two orientation scores, which is a different statement from the theorem, not the same one. The identity
`eq:component_pair_effect` then reads `g(Y_i1 | cand, partner inc) - g(Y_i1 | inc, partner cand)`: two things change at
once, so it is not a same-task effect of the candidate. Counterexample inside this harness: `sandbox_timeout_s = 10`
wall seconds for hidden-test verification; an arm whose partner runs CPU-heavy sandboxed self-tests and long GPU
generations can lose verifications to wall-clock timeouts that it passes alone. Take solo success 1.0 for both arms on
both tasks and let the heavy arm time out its partner: `D_i = -1` (candidate light) in both orientations, `nu_i = -1`,
true same-task effect 0. With the 180 s request timeout this is remote for model calls, but the sentence in 9.1 is the
estimand definition and it is wrong as written. Separately, two potential records per pair in `F_0` cannot coexist
with records that depend on the history (thermal state after a long incumbent run depends on `R_{i-1}`): the object in
`F_0` has to be the whole history-indexed tree of records with no dependence on later coins.

Required change. 7.4: state the modified assumption ("no interference across pairs; within a pair potential records
are indexed by the pair's orientation and by the history; no dependence on later coins, enforced by 5.1") and say the
result is the pair-level analogue of `thm:pair_id`, to be confirmed by the root under C8, not the theorem verbatim.
9.1 and 3.5: define `nu_i` as "the effect of reversing the orientation of pair i on the success difference, equal to
the average same-task effect only if a task's success does not depend on the partner's arm"; list that condition
among the assumptions of 7.4; log verifier timeouts with the partner's state. 7.2: rewrite the design-based `F_0`.

### F6 (MAJOR). T3: the only resource tier is wall-clock latency measured while the two models compete for one GPU from two server processes; the interference acts on the very contrast being scored and the regime disappears at deployment

Passages.
- D6 / 6.2: "T3 uses success > latency (10%) only"; 6.2: "the latency comparison inside a pair is made under a shared load; this is part of the endpoint definition"; 7.4: "preference between the two systems when one episode of each runs side by side on this host".
- 2.2: T3 uses two resident servers (ports 8091, 8092).

Why it fails (concrete). In T3 the two episodes of a pair run in different processes. If the GPU alternates between
the two command streams per decode step, both models emit tokens at the common rate `1/(t_A + t_B)` while both are
active. Two episodes with equal token counts then finish together, whatever the solo speeds: with the fallback
candidate (4B; judged by the weight files of 2.50 GB against 4.68 GB, roughly 1.8 times faster per decoded token than
the 7B incumbent when served alone; an estimate, not a measurement) the solo comparison is a clear tier-1 win
and the side-by-side comparison is a tie. Under time-fair sharing instead, the finish ratio is `(t_A + t_B)/(2 t_B)`
= 1.4 against 1.8 solo. Which regime holds on an M5 is unknown, so the T3 tier-1 estimand depends on an undocumented
scheduler. Even under the mildest model (equal slowdown factor kappa while both run), the faster episode is slowed for
all of its duration and the slower one only for the overlap, so a tier-1 decision needs a solo ratio above
`1 + kappa/9`: 1.111 alone, 1.167 at kappa 1.5, 1.222 at kappa 2. The frozen "10% operational tolerance" is therefore
a 17 to 22% tolerance on the quantity a deployer cares about, and what remains of tier 1 is mostly completion length,
which D6 removed from T3 as not comparable across tokenizers. After a T3 decision the candidate never again runs
beside the incumbent, so the live action is taken for a regime that was not measured. Error control is intact; the
meaning of a T3 DEPLOY or RETAIN that is decided on tier 1 is not. (T1, T2: same mechanism, but one server with
continuous batching and a 4.5-fold gap carried by call and token counts; the sign is robust. T4: symmetric.)

Required change. (i) Extend the pre-freeze calibration (5.8) to measure, on out-of-design prompts, solo and
side-by-side latency of each T3 model with the other as partner, and freeze the measured compression in the estimand
text. (ii) Add to 1.4: "T3 tier-1 results say nothing about either model's latency when served alone or beside
itself." (iii) Report in T3 the share of pairs decided at tier 1 next to the decision, and the success-only comparator
of 8.10 with equal prominence, stated now. (iv) Either justify keeping side-by-side latency as the T3 resource tier
against R3's recommendation of a contention-free tier (R3 section C, item 3), or state that a T3 decision carried by
tier 1 is "regime-specific" in the decision label itself.

### F7 (MAJOR). Multiplicity: T1 and T2 are the same contrast; "its own candidate" is false; the contrast-level bound is 0.10

Passage. 8.4: "each trial is its own experiment about its own candidate with its own 0.05; no selection among the four
is made and no combined claim is formed."

Why it fails. T1 and T2 compare the same two systems (`single_shot`, `self_test_repair` on the same model) on the same
tasks with the labels exchanged; T4 uses one of them. "NB gate crossed in T1" and "harm gate crossed in T2" are the
same scientific statement ("single_shot is preferred on the composite") tested twice, each with its own level, on
dependent data. Any reader will read them as two confirmations; the probability that at least one false statement
about this single contrast is issued is bounded by 0.10, not 0.05, and `theory.tex:484-492` asks for an allocation in
exactly this situation. The 0.20 program figure is stated, the 0.10 contrast figure is not.

Required change. Either split 0.05 over T1 and T2 (0.025 each, re-run the power table), or keep 0.05 each and
(i) replace the sentence by "T1 and T2 test one contrast twice with the roles exchanged; the bound for any false
statement about that contrast is 0.10", (ii) add to 1.4: "T1 and T2 are never cited as two confirmations or as a
replication", (iii) print the 0.10 next to every joint mention of T1 and T2.

### F8 (MAJOR). The secondary normal-mixture bands are a second 0.05 family presented as "design-based"; together with the decision the per-trial bound is 0.10, and in T1 the band will almost surely contradict a betting DEPLOY

Passages.
- 8.9: bands at "(0.01, 0.04) in T1, T2, T4 (...) are what is displayed as interval estimates of `mubar_n` and `nubar_n`".
- 9.3 lists under "Design-based": "the decision and its error bound (8.5); the secondary split normal-mixture bands (...) jointly valid at level 0.05 only because the levels were split".
- 8.5: "hence `P{ any false decision statement in the trial } <= 0.05`".

Why it fails. The decision (0.05) and the two bands (0.05) fail on different events. A report that offers both as
valid statements has a simultaneous bound of 0.10 per trial, 0.40 per program; this is the marginal-versus-joint
confusion of Rounds 10 to 13 one level up. Coherence: `normal_mixture_radius(280, alpha=.04)` = 0.194 and
`normal_mixture_radius(565, alpha=.04)` = 0.132, both above delta = 0.10, so the success band can exclude -0.10 only if
the observed difference exceeds +0.03 at the full horizon; the betting S gate at delta 0.10 crosses at n = 280 with
26 wins and 27 losses (observed difference -0.004, discordance 0.19; computed with `winstats`). In the planned T1
success case the table will therefore show "non-inferiority at 0.10 certified" beside "interval for `nubar`:
[-0.20, +0.19]", and the band is the only construction the root has so far retained. The draft prespecifies no
sentence for this.

Required change. (i) 9.3: move the bands out of the list that shares the 0.05, and state "the bands are a separate
secondary family with its own 0.05; no simultaneous statement over decision and bands is made (union 0.10)", or carve
the bands' level out of the 0.05. (ii) Prespecify the discordance sentence: "The driver certified margin delta; the
secondary band at the same prefix does not exclude -delta; the two constructions have different power, and the
decision rests on the driver only." (iii) Put the expected discordance probability into section 10 and into the C3 question
to the root, so that the root answers C3 knowing it (from 10.3: the bands ever clear both thresholds with probability
0.12 to 0.16 against a betting deploy probability of 0.86, so at least about 0.8 of T1 deploy outcomes are discordant
at the decision prefix).

### F9 (MAJOR). The non-inferiority margin is a function of roster size and of the driver; the rule has a cliff with no power computed at the cliff; the margin was picked knowing the same-task pilot difference is exactly 0

Passages. 3.3: "`n_S2 >= 400` (...) `delta = 0.10`. Otherwise (...) `delta = 0.15`"; 8.9: NM driver implies
"`delta = 0.15`"; 10.4: "the smallest value of the grid (...) at which the available single-exposure horizon gives a
realistic chance of certification".

Why it fails. A margin that moves with n and with the power of the test is "whatever can be certified": the S gate's
crossing then says little beyond "the rule had power". `paper/main.tex:165-166` requires application-specific
justification. Prespecification keeps the error bound; it does not give the claim content. The rule is also
discontinuous: `n_S2 = 399` gives 295 pairs at 0.15, `n_S2 = 400` gives 495 pairs at 0.10, and the power tables cover
only 568 and 295 pairs (R4: 0.10 needs 567 to 702 pairs for 80% without stratification). The margin was chosen after
seeing 433 versus 433 on these very tasks (paired SE 0.015).

Required change. Fix one delta for all branches with a rationale that does not mention power (for instance "0.10:
largest loss a laboratory user would accept for a 4.5-fold latency gain", or keep the paper's 0.03 as primary with
abstention declared the expected result and 0.10 as a labelled demonstration gate); if two values are kept, compute
and print the deploy probability at `N_P` = 495; add to every S-gate sentence "margin chosen for feasibility with
knowledge of a zero same-task pilot difference" (10.4 says it once; claim 1.3(8) does not).

### F10 (MAJOR). "Exposures avoided" as a share of `N_P` is an artefact of a horizon that was sized for a different trial's success gate; the projection is biased by the stopping rule

Passages. 9.4(1): "exposures to the rejected arm avoided relative to the prespecified fixed-horizon randomized design
= `M` (...) Also reported: `M / N_P`"; 10.3: "about 88 to 91% of the scheduled candidate exposures would be avoided";
9.4(3): "`M x (mean pre-decision latency of rejected-arm episodes - mean pre-decision latency of decided-arm episodes)`".

Why it fails. `N_P` (up to 565 pairs) is dictated by T1's S gate at delta 0.10. T2 needs about 50 to 65 pairs for its
harm crossing; nobody would run a 565-pair fixed design to detect a net benefit of -0.5. `M / N_P` near 0.9 in T2 is
produced by the choice of `N_P`, and doubling the roster would raise it with no change in the data. This is the
"overbroad operational savings" category of the root's criticisms with a prospective label. The projection multiplies
by a difference of means taken at a time selected because that difference was large, under side-by-side load that the
post-decision phase does not have.

Required change. Report `M` as a count with the sentence "`N_P` was set by the T1 success gate; `M / N_P` is not a
saving rate" or drop the ratio. If a relative figure is wanted, freeze now a fixed-sample comparator `n_fixed`
(smallest n giving the same level and 90% power for the pilot net benefit in a one-sided sign-type test) and report
`n_fixed - tau` beside `M`. Label the projection "biased toward the decided arm by optional stopping; computed under
side-by-side load".

### F11 (MAJOR). Pair-synchronous execution reduces the asynchronous comparison to the last pair; claim 1.3(5) and "early certificates" are bounded by construction

Passages. 5.1: "What is kept from the coordinator's intent: (...) reveals out of arrival order (...) and early
certificates (7.6)"; 8.6: "`t_enc <= t_dec` always"; 1.3(5).

Why it fails. With `N_e(t) - N_c(t) <= 1` and pathwise domination at the same prefix, a comparator crossing at prefix
n implies the live crossing at the completion of pair n. Hence `0 <= t_dec - t_enc <=` remaining run time of one
episode (in T2 about 10 s in a trial of hours). The monitor's input in reveal order and in arrival order differ only
by a swap inside a pair. The queue entry asks for a "Concurrent open-model prefix study with actual reveal timestamps";
what the design can show about prefixes under delay is one number bounded by one episode. This is a consequence of a
defensible choice (5.1's interference argument is correct), but the claim list does not say it, and C2 is addressed to
the coordinator only, although the acceptance condition is the root's.

Required change. 1.3(5) and 8.6: add "by construction the two times differ by at most the remaining duration of one
episode; this is not a study of monitoring under delay". Remove "early certificates" from the list of retained intent
or give its bound. Add to 1.4: "asynchronous-monitoring gains". Send C2 to the root as well, quoting the queue entry.

### F12 (MAJOR, claims). `D9`/`D10` invert R1's safety ordering; acceptable only because of the fallback, and the fallback has to be the state at freeze unless the root answers in writing

Passages. D9; 0.2 rows C3, C4; R1 b.5 ("Primary: split normal-mixture CS (...) literally the root's coding analysis
made prospective"); R1 b.6 (harm gate "not something the root has explicitly endorsed"; the pilot's betting harm
reading "descriptive").

Why it matters. The coordinator's fixed intent is that the rule "is the ROOT's accepted construction (so the result
can enter the paper without re-analysis)". A betting driver with a new harm gate is derivable from the paper's
results, but it is the construction the root has twice declined to retain for session-60 data. The draft handles
this correctly only through 12.1 step 3 ("each unanswered item takes the fallback").

Required change. State in D9 and 8.3 that without a written root answer the frozen driver is `nm_split_v1` with the
two-sided NB band supplying the harm direction; that a root answer counts only if it is an issue comment dated before
the freeze commit; and add F8's discordance information to the question.

---

## MINOR

### F13 (MINOR). Horizon arithmetic
3.3 and 3.6 give `N_P` "at most 568"; 3.3 also gives "at most 1,132 tasks (591 + 547 - 6)". Stratified pairing gives
196 + 40 + 59 + floor(541/2) = 565, before duplicates and sweep failures. `P5_supp_power.py:34` uses `N_S2 = 546`
(the six smoke tasks were not removed), so every "568" in 5.1, 10.3, 10.4 is a simulation value that the design cannot
reach. Correct the bound and re-run the chosen row at the realized `N_P` (C12 already requires a re-run).

### F14 (MINOR). Resume and look invariants
4.2 invariant (ii) orders `coin_drawn(i)` after the reveals of pair i-1, not after the look at prefix i-1;
`monitor_update` is not durable. A crash between the second reveal of pair n and the `decision` leaves a log from
which 12.3 step 3 "rebuilds the monitor" but no sentence obliges the resumed run to perform the look at `N_c` before
enrolling pair n+1. Add: "on resume, the look at the last completed prefix is evaluated and, if it crosses, the
decision is logged before any enrollment"; verifier invariant: exactly one reveal-triggered `monitor_update` for every
completed prefix n >= `n_min`, located before `pair_enrolled(n+1)`.

### F15 (MINOR). Hypothesis T1(a) is a retained-crossing reading unless tied to its prefix
9.5: support for T1(a) is "NB log E >= log 200 **at some look**". Valid under `prop:bet_running` only as "at prefix
n0 the running target was positive". Define n0 as the first crossing at n >= `n_min`, report the claim with that
prefix, and state that it says nothing about later prefixes (this is the Round 14/15 "pair-24" dispute in advance).

### F16 (MINOR). Scope of T4
With index-only seeds (5.4) and identical arm specifications, both orientations of a T4 pair produce the same two
records, so `Z_i` is a fixed `|h_i|` with a fair sign: the null is exact, and T4 tests the coin path and label
blindness only. It cannot reveal any arm-dependent defect (retry, timeout, server routing), because there is no arm
difference to depend on. 8.4's "T4 is the control of that same rule" and 1.2's "exact null by construction" should say
this; the verifier should confirm that the T4 job payloads of the two arms are byte-identical apart from the label.

### F17 (MINOR). Side read-outs at other margins
8.10 logs the S-gate log E at delta in {0.03, 0.05, 0.10, 0.15}. Add to 1.4: "a side-margin crossing is never reported
as non-inferiority at that margin". Note that the nulls are nested (nubar <= -0.10 implies nubar <= -0.05) but the
stake grids differ with the threshold, so no ordering of crossings is guaranteed.

### F18 (MINOR). Post-decision data: symmetric language
1.4(14) forbids "validate"; nothing forbids "contradict". Post-decision success of the decided arm is measured on
different tasks, under same-arm load, with no concurrent comparator. Add: "post-decision rates are neither validation
nor refutation of the decision and are not compared with pre-decision rates of either arm."

### F19 (MINOR). Preflight coin self-test
4.3: "checks the count against binomial limits". Limits and the consequence of a failure are not given. Freeze them
(for instance 4,850 to 5,150 of 10,000; on failure, stop and report, no silent repeat).

### F20 (MINOR). Fallback 7.5 (sliding window) cannot be frozen as written
"everything else in this protocol stays" is not true: the two positions of a pair start at different times under
different loads, decisions can occur with randomized pairs in flight (then excluded from monitoring by D15, a timing-
based exclusion of randomized units), the comparator needs enclosures for two or more pending pairs, and T-specific
power changes. If C2 is declined, 7.5 needs its own section and its own audit before a freeze.

### F21 (MINOR). Crash recovery is arm-differential
12.3 step 2 reveals an orphan record if the episode had finished and re-runs it otherwise; the episode still running
at a crash is more often the slow arm, and its re-run has no partner (faster). ITT and adaptedness hold; add
`partner_concurrent: false` pairs to the prespecified sensitivity list of 9.3 by name (it currently names only
`infra_flag`, which does cover them, but the mechanism should be stated).

### F22 (MINOR). What the pilot reuse biases and what it does not
No bias of the error bound: strata, levels, margin and directions are `F_0`-measurable once F1 is fixed. Biased or
fragile: (i) the headline "about 0.8" deploy probability rests on pilot-defined strata staying predictive on a new
quantization and runtime; P5's own sensitivity drops S1/0.10 from 0.76 to 0.53 and the chosen EXT row from 0.86 to 0.79
at w = 0.7, and w was not calibrated on anything; (ii) the Beta(0.386, 0.141) fit treats two different workflows as two
exchangeable runs of one task; (iii) margin and level split were tuned on a same-task zero difference (F9). Print the
w = 0.7 figure, not the w = 1 figure, as the planning value in 1.2 and 10.4.

---

## Examined, no finding

- Coin of the current pair: absent from `F_{i-1}`, drawn after both reveals of pair i-1 and after the look; enrollment
  of pair i depends on the past only through the stopping rule. No counterexample under the stated operator-honesty
  assumption.
- Pairing under out-of-order reveals: pairs are arrival-order positions fixed in `F_0`; completion time never enters
  pairing; no fast-episode selection. Informative delay exists only inside a pair and only in the comparator.
- `prop:bet_running` with `c = -delta`: factors positive for the grid maximum `0.99/(1 - delta)`; normalizing product
  at most 1 exactly when the running mean is at most c; applies to `-Z` for the harm gate.
- H and NB (hence DEPLOY) cannot cross at one prefix: with P <= M every stake has log wealth <= 0 (checked: maximum
  -0.29 at n = 100).
- `n_min`, first-crossing action, abort at any time: each can only remove crossings.
- D1 (pair coin instead of per-arrival coin): required by the accepted score; no statistical objection.
- Enclosure certificate `0.9 * ell > L_r + 1e-9`: implies `x - L_r > 0.1 x` for every feasible partner latency `x >= ell`.
- Seed map: bijective modulo 2^31 over the stated index ranges.
