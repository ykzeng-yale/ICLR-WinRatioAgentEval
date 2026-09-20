# live_ab: coordinator decisions on protocol_draft_v2.md (2026-09-19, session 60 coordinator)

These decisions are final inputs for v2.1. Where they simplify v2, the simplification is deliberate: every extra
mechanism is a possible post-freeze defect, and the root's past objections were about unclear or improvised rules,
not about missing machinery.

## A. Design decisions
- C1 ACCEPTED: one OS-entropy coin per arrival PAIR (orientation design of thm:pair_id), not per arrival.
- C2 ACCEPTED: pair-synchronous execution. The two arms of pair i run concurrently (two workers); pair i+1 is enrolled
  only after both episodes of pair i are revealed and the look at prefix i is evaluated. Real timestamps, out-of-order
  reveals inside a pair, at most one pending pair. No sliding window. The narrow scope of the "concurrent" element is
  stated plainly.
- C22 ACCEPTED: contrast-level error budget as in 8.4 (T1, T2, T4 at 0.025; T3 at 0.05; program bound 0.125).
- C23 ACCEPTED: max_attempts = 1, no re-run of any kind; forced failures reported by arm; "integrity-qualified" label rule kept.
- C24 ACCEPTED: T3 candidate = ibm-granite/granite-3.3-8b-instruct-GGUF, file granite-3.3-8b-instruct-Q4_K_M.gguf
  (verified 2026-09-19: repository exists, Apache-2.0, not gated, exactly one non-split Q4_K_M file). No fallback; T3 is deferred if a preflight rule fails.
- D12/C6 ACCEPTED: one success margin 0.10 everywhere, labelled "laboratory margin, not application-justified".
- C18 ACCEPTED: OS entropy coin, described as operator-attested. No beacon.
- CONFIGURATION: configuration A (betting gates, bet_split_v2) DRIVES TRAFFIC; configuration B (normal-mixture bands,
  nm_split_v2) is computed at every look as the prespecified secondary construction of 8.9 and never drives traffic.
  Reason: A rests on prop:bet_running and thm:drift_gate, which are in the paper; B is the construction the root
  retained for the coding stream, so both readings are available to the root whatever it prefers. The root can veto A
  before the freeze (then B drives traffic and A becomes the secondary); after the freeze nothing changes.
- C21 CHANGED: the cut-off for root answers is the freeze itself, and the freeze happens no earlier than 24 hours after
  the questions were posted on issue #11 (posted 2026-09-19 ~17:35 UTC; harness construction and the pre-freeze phase
  take at least that long). Silence = the defaults above.
- C27: no fixed-sample comparator, no relative-efficiency sentence.
- C26: no anonymous hand-off deliverable (arXiv, not double-blind). Tracked artifacts still contain no absolute paths,
  account names or host names (relative paths and placeholders), because that is cheap and avoids a later repair.

## B. Approvals (the user has given standing authorization for open-weight model downloads, for pushes and comments
##    on this repository, and for autonomous operation; recorded here so that the protocol does not wait for them)
- C9 APPROVED: downloads of mbpp.jsonl at a pinned revision, the Granite GGUF, LICENSE files.
- C10 APPROVED WITH SIMPLIFICATION: anchoring = pushed commits on the dedicated branch session60/live-ab-anchors
  (chain-head hash file) at trial start, every 25 completed pairs, at the decision, at every pause/resume and at trial
  end; plus exactly three issue comments per trial on issue #11 (start, decision, end) carrying the chain-head hash.
  No 30-comment stream. A trial blocks on the push at start, at the decision and at pause/resume only; a failed
  periodic push is logged and retried at the next anchor point (it never blocks and never changes an outcome).
  One anchor drill against the real remote on a drill branch before the freeze.
- C17 REJECTED: no RFC 3161 timestamp authority (extra external dependency). The chronology wording therefore says:
  commit and comment timestamps are assigned by GitHub's servers; comments are editable by the account owner and
  GitHub shows an edit history; a push cannot be back-dated but a force-push could rewrite the anchor branch, so the
  anchor branch is never force-pushed and its reflog-equivalent is the public events feed (90 days retention).
- C19 FACT: the repository and issue #11 are PUBLIC (checked via the GitHub API 2026-09-19).
- C20 SIMPLIFIED: no private evidence archive. Everything needed to audit every reported number is deposited in the
  repository (gzip where large): event chain, worker spools with full request/response bodies, server logs, sandbox
  results. Model-generated programs for public benchmark tasks are not sensitive.
- C13: harness code is released under the repository's licence (the repository currently has none; the author decides;
  not blocking).
- C11, C14, C15 FACTS: Qwen coder GGUF = official repo Qwen/Qwen2.5-Coder-7B-Instruct-GGUF, revision 13fb94bfda8c8cf22497dc57b78f391a9acb426a,
  file qwen2.5-coder-7b-instruct-q4_k_m.gguf, 4,683,073,536 bytes, sha256 509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c.
  Working location: the main clone, branch session60/live-ab (created from session60/local-stream at ce8b506 plus a merge of main 955579d);
  no second clone. llama.cpp: rebuild at a pinned commit into a directory outside the repository; record commit and build flags.
- C12 MANDATORY, KEPT: re-run the planning simulator on the frozen configuration (A drives, B secondary) with the cells of 10.5 before the freeze.

## C. Critic findings N1-N22
All HIGH and MEDIUM findings must be resolved in v2.1 by text, preferring the SIMPLEST rule that closes the gap:
- N1-N3 (between-trial mechanics): one program-level chain file `program_chain.jsonl` that exists from the freeze to
  the end of the last trial; every trial chain starts with the program chain's head hash; refusals, "not started",
  plumbing-verifier failures and harness re-freeze authorizations are program-chain events. If the plumbing verifier
  fails after T4: the program stops, the failure is reported, and later trials need a new protocol version. Verifier
  and report builder have the same defect path as the harness (harness-only re-freeze: outcome-blind diff, logged, anchored, never touching sections 3-9).
- N4-N6, N9 (unmapped failure modes): give each an explicit outcome row in 6.4.
- N7, N8, N14 (auto-aborts on unexercised server behaviour; T4-first cannot exercise self_test_repair): add a pre-freeze
  END-TO-END rehearsal on out-of-design tasks (tasks not in the roster) that runs the production path with BOTH
  workflows and BOTH models, including a forced pause/resume and a forced server kill, and freeze only after it passes.
  Trial order stays T4, T2, T1, T3.
- Drop anything the critic or auditors marked optional that needs a new external dependency (thermal probe, TSA).

# ===== REVISION 2, 2026-09-19 20:30 UTC: adoption of the root's design guidance =====
Source: reviews/arxiv_live_design_guidance.md at main 4fe6d17 (+ issue #11 comments 17:45-17:52 UTC).
The root answered every question posted at 17:35 UTC. Its guidance OVERRIDES the decisions of revision 1
wherever they differ. All of the following are adopted literally; none is negotiated.

1. PRIMARY RULE = NORMAL-MIXTURE BANDS (revision 1 decision "A drives traffic" is WITHDRAWN).
   At every look, on the CURRENT FULL ENROLLED PREFIX n = N(t), for each score j in {hierarchy h, success s}:
       r = normal_mixture_radius(n, alpha=alpha_gate, rho=100., variance_process=n)
       L_j = sum(lower_j[:n])/n - r ;  U_j = sum(upper_j[:n])/n + r ; both intersected with [-1,1]
   DEPLOY candidate iff L_h > 0 AND L_s > -delta at the same current prefix.
   HARM/RETAIN iff U_h < 0 (prespecified: the hierarchy tail only; NOT "either").
   No prefix envelope, no maximization over prefixes, no retained crossing, no running intersection.
2. ALPHA: program 0.05; four prespecified trials -> 0.0125 per trial; two monitored scores per trial ->
   alpha_gate = 0.00625 per band. The two-sided band serves BOTH the deploy tail and the harm tail;
   no extra split for the harm direction. Frozen before collection. rho = 100.
3. BETTING GATES ARE NOT USED AS THE DECISION RULE and are never fed partial scores. They may appear only as a
   clearly labelled post hoc descriptive computation on the final completed scores, with no error-control claim
   and no adapter. Revision 1 decisions 3-5 on betting are withdrawn.
4. MARGIN delta = 0.03 PRIMARY (the root refused a margin chosen for certifiability). 0.10 and 0.15 appear only
   as explicitly exploratory sensitivity read-outs, never described as preserving success and never as a decision.
5. CONSEQUENCE, COMPUTED BEFORE ANY DATA AND STATED IN THE PROTOCOL (radius alpha=0.00625, rho=100, V=n):
       r(92) = 0.4966   r(295) = 0.2287   r(569) = 0.1578
   - T2 harm gate (pilot NB = -0.497): crosses at n >= 92 pairs. FEASIBLE.
   - T1 hierarchy gate (pilot NB = +0.497): crosses at n >= 92 pairs. FEASIBLE.
   - T1 success gate at delta = 0.03 with Dbar = 0: needs n >= 17,097 pairs. The roster gives at most 569.
     => [WITHDRAWN 2026-09-20, SEE REVISION 5. The sentence that stood here, "A DEPLOY DECISION IS UNREACHABLE BY
        CONSTRUCTION AT THIS SCALE, whatever the outcomes", IS FALSE and must not be relied on. The 17,097 figure is
        conditional on an OBSERVED success difference of 0; it is not a statement about all outcomes.]
     (delta 0.10 needs 1,378; delta 0.15 needs 626; delta 0.20 needs 372, all at an observed difference of 0.)
   The protocol states this correctly as a PRE-SPECIFIED NEAR-CERTAIN ABSTENTION, not an impossibility.
   It is not a defect of the design: T1 is expected to show the composite gate crossing while the success
   guardrail refuses, which is the guarded rule behaving as specified. No horizon extension, no margin loosening
   and no model replacement after unfavourable monitoring (root guidance 6).
6. TRAFFIC SWITCH = A NEW OBSERVATION PHASE. At a crossing: stop randomizing new pairs, finish every already
   enrolled pair under its original assignment, log the exact switch time and all in-flight exposure. Post-switch
   single-arm traffic is an operational follow-up cohort, never additional pairs for the A/B estimator. No causal
   resource/latency-saving claim; the comparator is descriptive and coupled.
7. ENCLOSURES: unresolved hierarchy score starts at [-1,1] and is narrowed only by enumerating feasible
   completions; success enclosure [sA_low - sB_high, sA_high - sB_low]; collapse only on a valid final-score
   certificate; elapsed cost is a lower bound only if it cannot decrease; absence of failure is not success.
   Containment audited against every ultimately revealed score at every recorded look.
8. A/A (T4) is an implementation/null check only. One non-crossing run does not establish a 5% false-decision
   rate and does not demonstrate equivalence. A crossing is reported and investigated, never discarded.
9. n_min: 100 enrolled pairs (the root's reproducible screening choice). Horizon: the full roster.
10. FREEZE DELIVERABLE (root guidance 9): task/pair manifest hashes, the four exact contrasts, model revisions and
    licenses, scheduler/isolation model, alpha table, margins, rho, minimum/horizon/caps, seeds and seed receipt,
    all interval/decision code, the append-only event schema, CPU planning results (exhaustive, not selected), and
    deterministic tests of enrollment/reveal reorder invariance, repeated-update idempotence, enclosure
    containment, equality ties, joint failures and switch-phase exclusion.
11. Pair-synchronous execution (revision 1 decision C2) is KEPT and is compatible with the guidance; reveal-order
    events update the enrollment-indexed record of an existing pair and never create, reorder or drop one.
12. HOST CAPACITY (measured 2026-09-19 20:28 UTC on the serving host): Apple M5, 10 cores, 32 GiB RAM,
    262 GiB free disk; model cache 59 GiB already present. No further weight downloads are needed for T1/T2/T4;
    the T3 Granite weights are already on this host. The root host is not used for any execution.

# ===== REVISION 3, 2026-09-19 22:10 UTC: corrections and two frozen choices =====
13. CORRECTION OF MY OWN REPORTED NUMBERS (both were posted to the root on #11 at 20:30 UTC and are wrong):
    - r(92) = 0.495026, NOT 0.4966. I transposed the radius with the pilot net benefit (0.4968).
      No conclusion changes; n_min = 100 binds before either value.
    - The horizon is 568 pairs, NOT 569: pairs are formed WITHIN strata, so it is
      floor(591/2) + floor(547/2) = 295 + 273 = 568.
    Both corrections are posted on #11 rather than silently changed.
14. HIERARCHY (frozen): the root's literal two tiers,
      [Tier('success'), Tier('cost', higher_better=False, relative_tolerance=0.05)], cost = latency_s,
      eligible only when both episodes succeed, joint failures tie.
    This DROPS the pilot's three tiers (success > latency 10% > completion_tokens 10%). Verified on all
    591x591 pilot cross-task pairs: 2-tier net benefit +0.4993 (win/tie/loss .7115/.0762/.2122) versus
    3-tier +0.4968 (.7090/.0788/.2122, which reproduces the earlier planning number exactly). Both readings
    were computed; only the 2-tier one is frozen. Side effect: T3 no longer needs a different kernel.
15. ROSTER (frozen), stratified so that fresh tasks are distinguishable as the root asked:
      S1 = the 591 tasks the pilot observed (427 MBPP-sanitized + 164 HumanEval) -> 295 pairs
      S2 = the 547 MBPP-full tasks that are NOT in the sanitized set and were never observed -> 273 pairs
      TOTAL 1,138 tasks, 568 pairs. Verified: sanitized (427) is a strict subset of MBPP full (974).
    Pairs never cross a stratum. S1 and S2 results are reported separately as well as pooled.
    mbpp.jsonl is downloaded at a pinned revision and hashed into the freeze bundle.
16. AUDIT STATUS: audit_v3.md returned BLOCK with 7 blockers, six of them cases where protocol_v3.md and
    ARCHITECTURE.md stated DIFFERENT decision-defining rules. protocol_FINAL.md + ARCHITECTURE_FINAL.md are
    the resolved pair; both now state the two-tier hierarchy at tolerance 0.05 and the corrected horizon 568.

# ===== REVISION 4, 2026-09-20: rulings on the implementation's open items =====
17. RULING on D-1, where the prefix grows (the three-way disagreement between protocol 8.3 trigger 1,
    protocol 7.3 item 2 and ARCHITECTURE 7.1 rows 5-6). The root guidance defines n as "the number of fully
    enrolled/RANDOMIZED pairs" (reviews/arxiv_live_design_guidance.md:11). A pair whose coin has not been drawn
    and fsynced is not randomized. THEREFORE: n grows at `coin_drawn`, never at `pair_enrolled`; a staged pair
    holds no position until its coin. Protocol 8.3 trigger 1 is corrected in place; 7.3 item 2 and the
    architecture were already right. The alternative (counting at pair_enrolled with the pair at [-1,1]) is only
    "conservative" for the band; it is NOT safe for the chain, because a crash between pair_enrolled and
    coin_drawn puts the decision code and the independent reference rule in different orders about the
    re-enrolled pair, which no valid chain can then satisfy.
18. RATIFIED, all three of G5's cadence corrections to decision-defining code (protocol 14.3 requires explicit
    ratification, not a silent merge). Each is derived from protocol text and proved by a test in tests_lab_e2e.py:
    (a) no `call` look after a decision (only the drain reveal): protocol 9.1 item 4, ARCHITECTURE 7.1 row 12;
    (b) the `resume` look happens after the orphan reveals and just before the next enrollment, not at
        `invocation_started`: protocol 8.3 trigger 4 with 14.5 items 3, 4 and 6;
    (c) the `enroll` look happens at the coin, per ruling 17.
    Without these the verifier FAILS on a correct run, because it compares the logged trigger sequence against
    lab_reference_rule and the logged values against lab_monitor.replay, and the two modules disagreed.
19. RULING on D-3 (lab_server.start/restart carry keyword-only parameters beyond ARCHITECTURE section 3):
    the extra parameters are accepted and ARCHITECTURE section 3 is to be updated to document them. They are
    serving-layer plumbing, not decision-defining code, and the signature gate must print no deviation at freeze
    time, so the document is corrected rather than the code.
20. Test hardening required before the freeze (none of it touches a scientific rule): the three wall-clock loops
    must raise an explicit TimeoutError; the ten dormant skipTest guards must become hard failures; the two
    spelling-based PG-16 greps must become behavioural assertions. A skip that passes silently is a test that
    does not exist.


# ===== REVISION 5, 2026-09-20: I was wrong about unreachability. Correction. =====
21. WITHDRAWN: "a deploy decision is unreachable by construction, whatever the outcomes", and with it
    "guaranteed abstention" and the deterministic "the hierarchy gate will cross at 92 pairs".
    The root caught this (reviews/arxiv_live_feasibility_claim_correction.md on main) and it is right.
    MY ERROR: I computed the pairs needed for the success gate ASSUMING the observed running success difference
    stays at the pilot value of 0, then reported the result as if it held for every possible outcome. The gate is
    `mean_success_difference - r(n) > -delta`, i.e. the observed difference must exceed `r(n) - 0.03`. That is a
    condition on the DATA, not a fixed sample-size requirement.
    VERIFIED COUNTEREXAMPLE (recomputed here): at n = 100, if every one of the 100 resolved pairs has the candidate
    succeeding and the incumbent failing, both running means are 1.0, both lower bounds are 1 - r(100) = 0.534307,
    and BOTH GATES PASS. A deploy fires at the first permitted look.
    CORRECT STATEMENT, which is what the protocol already says (sections 1.4, 1.5 item 13, 11):
      at 568 completely observed pairs the declared success gate requires an observed running success difference
      strictly above r(568) - 0.03 = 0.1279515124940428; IF the observed difference stays at zero the gate cannot
      pass within this horizon. That is the whole of the statement. It is a conditional threshold calculation and
      it does NOT calibrate the probability of a deployment or of an abstention.
    SECOND WITHDRAWAL, 2026-09-20, after the root's statistics review: the replacement I wrote above originally
    read "PRE-SPECIFIED NEAR-CERTAIN ABSTENTION" and justified it by the same-task pilot difference of 0.000000
    with a paired standard error of 0.0151, "about 8.5 standard errors away". BOTH ARE WITHDRAWN. "Near-certain"
    is still a probability claim I have not calibrated, and the 8.5-standard-error rationale uses the WRONG SCALE:
    the same-task paired standard error describes paired comparisons on ONE task, whereas this trial pairs two
    DIFFERENT tasks with one arm on each, so that quantity does not describe this design's variability at all and
    must not appear as a rationale. No replacement scale is substituted, because I do not have a calibrated one.
    The forbidden list below therefore also covers "near-certain" and the 8.5-standard-error argument.
    Likewise "the gate crosses at 92 pairs" is only the first n at which the radius falls below the PILOT effect
    magnitude 0.497, and the first permitted look is n_min = 100, so no decision can occur at 92 under this
    schedule. Whether any gate crosses is an outcome, not a plan.
    The phrases "unreachable by construction", "impossible whatever the outcomes", "guaranteed abstention",
    "near-certain abstention" and the 8.5-standard-error rationale are forbidden in every artifact of this program. delta = 0.03 and the frozen rule are unchanged.
22. DISCLOSURE, correcting my own merge statement of 2026-09-19 ~21:00 UTC. I said the direct merge modified
    "0 root-owned files". My filter covered paper/, arxiv/, src/winstats, reviews/, and the status files; it did
    NOT cover results/. The merge did change three tracked CSVs that the root treats as frozen baselines:
      results/benchmarks/tau2_contrasts.csv and tau2_rankings.csv: main held the version from da7ad17; the merge
        brought the LATER version from 84773e1, "Align benchmark analysis and replay with the amended protocol
        (12 off-diagonal within-task pairs)". The newer file is the corrected one.
      results/cs_width.csv: main held da7ad17's version; the merge brought 6e53db4's, from the audit-driven wincs
        fixes. The differences are in the 11th decimal place, consistent with the corrected betting capital.
    All three are session-60-owned files, and in each case the merge moved main FORWARD to the corrected version
    rather than reverting anything. That is still a change I failed to disclose, and the root found it first.

# ===== REVISION 6, 2026-09-20 02:20 UTC: host contention is real, and it blocks trial execution =====
23. FINDING (measured, not hypothetical). Two `llama-server` processes have been running on the serving host for
    8h34m (PIDs 63657, 63658; started 2026-09-19 13:41:11), serving Qwen2.5-3B-Instruct on port 8193 and
    Qwen2.5-7B-Instruct on port 8191, both with `-ngl 99 -np 4 -c 32768`, together holding about 7.7 GB RSS and
    actively processing (`/slots` shows `is_processing: true`). They are NOT mine and NOT part of this program.
    They are driven by a python client (PID 15720) whose working directory is
    `/Users/yukangzengcmac/DTR-AgentEvals/experiments/code_routing`, running `run.py --stage branch
    --allow-contention` under a different Claude Code session on a DIFFERENT project.
24. CONSEQUENCE FOR live_ab, and it is material. The frozen hierarchy is success > cost, and cost is `latency_s`.
    The pilot shows the two arms tie on success (433/591 each), so essentially the whole composite effect is
    carried by the LATENCY tier. Latency measured while another project saturates the same GPU is not a
    measurement of the two workflows; it is a measurement of whatever that project happened to be doing. The root
    guidance anticipated exactly this: "Shared serving contention or adaptive schedulers do not disappear merely
    because assignment coins are fair: isolate resources where feasible and log the fixed scheduling/resource
    policy and all concurrent load." Protocol 5.7 already requires "no other GPU job", but the harness's exclusive
    lock file only excludes a SECOND INSTANCE OF THIS HARNESS; nothing detects a FOREIGN GPU consumer.
25. REQUIRED BEFORE THE FREEZE (new pre-freeze item, added to the hardening list of ruling 20):
    (a) a preflight HOST QUIESCENCE GATE that enumerates foreign GPU consumers (any `llama-server`, `mlx_lm`,
        `ollama`, `python` holding a Metal context that this harness did not start) and REFUSES to start a trial
        while one is present, naming it in the refusal;
    (b) the same check repeated at every quiescent scrape during a trial, emitting a logged
        `foreign_load_detected` event with the offending command line; contention that appears mid-trial does not
        void the randomization, but it is disclosed per trial and per arm, and the latency tier is reported with
        that caveat attached;
    (c) the refusal and the mid-trial event are both chain events, so a reader can see that the host was clean.
26. WHAT I WILL NOT DO: I will not kill or throttle the other project's processes. They belong to a different
    repository and a different session, that session passed `--allow-contention` deliberately, and terminating
    another agent's multi-hour job to free my GPU is not a decision this session gets to make. The live trial
    WAITS for a quiescent host instead. This is now the binding constraint on when T4/T2/T1/T3 can run, not the
    harness, which is finished and green.

# ===== REVISION 7, 2026-09-20: the gate works, and it forces a baseline-load ruling =====
27. THE GATE WORKS AND ITS FIRST ANSWER IS "NO". Run against this host at 2026-09-20 ~04:00 UTC it reports
    clean = False, 1,037 processes scanned, 0 degraded, and three findings:
      pid 63657  detector llama-server   elapsed 38,839 s   the other project's 3B server
      pid 63658  detector llama-server   elapsed 38,839 s   the other project's 7B server
      pid 39197  detector metal-process  elapsed 31,310 s   /System/Library/PrivateFrameworks/
                                                            MediaAnalysis.framework/.../mediaanalysisd
    The first two are the foreign experiment the gate was built to catch. The third is an Apple SYSTEM DAEMON.
28. RULING, made now because it must not be made after it blocks something. `mediaanalysisd` and processes like it
    are part of the host's BASELINE, not a competing experiment, and they restart on their own, so a gate that
    refuses on them can never pass on a normal macOS host and would quietly become a gate nobody runs.
    THEREFORE:
    (a) a CLOSED, frozen allowlist of OS-owned baseline daemons, identified by their absolute `/System/...` path
        prefix and NOT by name alone, is exempt from REFUSAL. The list is frozen in the freeze bundle before any
        trial and is never extended during or after a trial. Anything not on that list refuses, as before.
    (b) Exemption from refusal is NOT exemption from the record. Every baseline daemon found is still written into
        the chain at every scan, with its elapsed time and resident size, so a reader sees exactly what shared the
        host rather than taking a bare "clean" on trust.
    (c) Because `mediaanalysisd` does intermittent on-device machine learning, its presence is not constant-cost.
        The scan therefore records its CPU time delta between consecutive scrapes, and any trial whose window
        overlaps a materially active baseline daemon carries that fact beside its latency tier. This is a
        disclosure, not a correction: no latency number is adjusted for it.
    (d) What the gate proves is therefore: no non-baseline accelerator consumer above the resident-size floor was
        detectable, and the baseline that was present is recorded. It does NOT prove an idle machine, and protocol
        5.7.1 must say so in those words.
29. CONSEQUENCE TODAY: the host is still NOT quiescent. The two foreign llama-servers have now been running
    10 h 47 m. The live trial stays blocked on them, exactly as ruling 26 says, and I am still not killing them.

# ===== REVISION 8, 2026-09-20: ruling 28 is WITHDRAWN and replaced. Measure activity, not possession. =====
30. Two incompatible rules were produced for the OS-owned case, and I am replacing BOTH.
    - MY ruling 28 (revision 7) exempted a frozen allowlist of OS daemons from refusal regardless of what they
      were doing. WITHDRAWN. An allowlist that exempts on identity alone is exactly the kind of thing that gets
      quietly extended to unblock a trial, and it would have let a BUSY daemon through.
    - The implementer's option (b) (ARCHITECTURE_FINAL 3.17.1) keeps a hard refusal with no override and tells the
      operator to wait for three clean scans. ALSO NOT ADOPTED AS WRITTEN, because it refuses on mere possession
      of a Metal context.
    MEASUREMENT THAT DECIDES IT, taken 2026-09-20 ~04:20 UTC on `mediaanalysisd` (pid 39197, resident 9 h 12 m):
      %CPU 0.0, cumulative CPU 18:24.25, UNCHANGED across three samples 4 s apart.
    The daemon HOLDS a compute-class Metal context and CONSUMES NOTHING. A rule that refuses on possession would
    block this host indefinitely on a process doing no work; a rule that exempts on identity would admit the same
    process while it was doing a lot of work. Both are wrong, in opposite directions.
31. THE RULE, frozen before any trial:
    (a) A NON-BASELINE accelerator consumer (anything not OS-owned: another experiment, another project, a user's
        model server) REFUSES ON PRESENCE. No activity test, no override. A loaded model server exists to be used.
    (b) An OS-OWNED process, identified by absolute `/System/...` path prefix and never by name alone, refuses
        only if it is ACTIVE by a test fixed in advance: cumulative CPU time sampled at t and t+10 s, active iff
        the delta exceeds 0.5 CPU-seconds. Idle-but-resident is recorded and does not refuse.
    (c) The activity test runs at trial start AND at every quiescent scrape. A baseline daemon that WAKES during
        a trial does not abort it (aborting on an OS daemon would make trials unfinishable) but is recorded, and
        the affected window is named beside the latency tier as a disclosure. No latency number is ever adjusted.
    (d) Every OS-owned process found is written to the chain at every scan whether active or not, with its
        elapsed time, resident size and CPU delta, so "clean" is never a bare assertion.
    (e) The 5.7.1 wording stands as narrowed: the gate proves that no non-baseline accelerator consumer above the
        resident floor was detectable and that the baseline present is recorded. It does not prove an idle host.
    (f) The thresholds in (b) are frozen in the freeze bundle. They are NOT tuned after a refusal. If this rule
        ever blocks a trial, the trial waits; the rule does not move.
32. STATUS UNCHANGED FOR #11: the two foreign llama-servers are still present, so the gate still refuses and the
    trial is still blocked. Ruling 31(a) is why, and it is the correct reason.

# ===== REVISION 9, 2026-09-20: two adjudications on the frozen #12 protocol, before any outcome =====
33. CONTEXT. Implementing the modules the frozen #12 protocol SPECIFIES BUT DOES NOT CONTAIN surfaced two facts.
    No simulation outcome of the reported grid exists: every number below came from namespace 1 (the measurement
    namespace whose seeds are discarded), and the reported namespace 0 has never been drawn.
34. BLOCKER 2 — the protocol's own fixture refuses to let the grid run, and it is RIGHT to.
    Section 13.0 asserts "vgen.py, vrun.py and vcompare.py do not exist". Writing them, which is exactly what the
    protocol instructs, makes that sentence false, so F15 fails and vrun aborts before the grid. This is the
    pre-registration working: a frozen document that refuses to run while it describes a world that no longer holds.
    RULING: this is a STATUS CORRECTION THAT CHANGES NO VALUE, which section 14 permits explicitly
    ("Typographical corrections that change no value are recorded as such with the before/after text"). Record the
    before/after text of 13.0's status column and nothing else. It is NOT a version bump: no cell, parameter, seed,
    grid, estimator, reported quantity, flag rule or positive control moves.
35. FINDING 1 — sections 6.3 and 6.4 were computed under the reading that section 2.5 says does NOT govern.
    Recomputing section 6 under the FROZEN PREDICATE disagrees with the frozen 6.3/6.4 tables in 13 entries at
    N_max = 2000 and 14 at N_max = 1000, each by one unit in the fourth decimal, confined to exactly the 128
    boundary states that 2.5 itself names. Recomputing under 2.5's closed-form paraphrase reproduces all of
    6.1-6.4 with zero disagreements. So the tables were built with the paraphrase while the predicate governs.
    RULING, and I am deliberately choosing the more conservative of the two available fixes:
    (a) DO NOT EDIT THE FROZEN VALUES. Section 14's last clause says the next change of any value is a new version
        "whatever it is, and whoever asks for it". Quietly recomputing 13 numbers in a pre-registration because
        they turned out to be slightly wrong is precisely the habit pre-registration exists to prevent, and the
        fact that it would be harmless here is not a reason to acquire the habit.
    (b) CORRECT THE SENTENCE, which changes no value: 2.5's claim that "this study's numbers in sections 6.3 and
        6.4 are computed with it" is FALSE and is withdrawn. Replace it with the fact: 6.3 and 6.4 were computed
        with the closed-form paraphrase, which differs from the governing predicate in exactly the 128 named
        boundary states.
    (c) DEPOSIT THE CORRECTED TABLE BESIDE THE FROZEN ONE, not in place of it: an addendum carrying the
        predicate-reading recomputation, both readings shown, every differing entry named with both values, and
        labelled as a post-freeze recomputation. A reader then sees what was frozen, what is right, and the gap.
    (d) NOTHING OPERATIVE MOVES. The predicate is what vband, vcompare, F17 and vgen implement, so the grid, the
        decision rule and every reported quantity are unaffected. 6.3 and 6.4 are descriptive expectation tables.
    The root may overturn (a) and require a version bump instead; if it does, v1 carries no results, so there would
    be nothing to report beside and the bump costs nothing but a label.
36. BUDGET. Measured on this host at namespace 1: 3.15 ms per program, 0.79 ms per trial, peak RSS 79.8 MB. The
    protocol's own ladder therefore selects T1, the full grid: 28,000 programs, projected about 88 s, about 6 MB of
    output and about 115 MB peak RSS, against caps of 5,400 s, 200 MiB and 2 GiB. Every cap passes by two orders of
    magnitude, so there is no reduced grid to report and no pause-and-report branch to take.

# ===== REVISION 10, 2026-09-20: adjudication of the #12 comparison defect =====
37. THE VALIDATION STUDY FOUND A REAL DEFECT IN THE LIVE MONITOR, and 380 passing tests had not.
    vcompare reports 122,786 of 400,203 compared looks disagreeing across 926 streams, in two classes
    (151,032 per-pair enclosure endpoints and 131,352 band endpoints, the second being the first summed).
38. ADJUDICATION, from first principles rather than by preferring either implementation.
    Reproducer: incumbent revealed, success 1, cost 10.0; candidate pending with elapsed 9.6.
      #11 reports [-1, +1].   #12 reports [-1, 0].
    Enumerating the feasible completions: if the candidate fails, the incumbent wins the success tier, Z = -1.
    If it succeeds, both succeed and the cost tier decides; to WIN there the candidate needs final cost below
    10.0 - 0.05*10.0 = 9.5, but its elapsed time is ALREADY 9.6 and cost cannot decrease. A candidate win is
    therefore impossible from this state, and the tight enclosure is [-1, 0].
    => #12 IS CORRECT AND TIGHT. #11 IS LOOSE: it retains an outcome that the state has already excluded.
39. DIRECTION, which decides whether this is a bug or a cost. Measured over every disagreeing row:
      per-pair enclosures: #11 contains #12 in 151,032 of 151,032 rows -- 100.00%, never narrower.
      band endpoints:      #11 wider in 131,352 of 131,352 -- never tighter.
    => #11 NEVER EXCLUDES THE TRUTH. This is NOT a validity defect and no #11 result would have been wrong.
    It is a POWER defect: the live monitor carries impossible outcomes in its enclosures, so its bands are
    wider than the data warrant, on every partially revealed pair, at every look.
40. WHY THIS MATTERS MORE THAN IT LOOKS. It is the SECOND independent source of conservatism found in the same
    rule. The first is the variance proxy: the normal-mixture radius uses variance_process = n, a proxy of 1 per
    observation, while the measured variance of the success difference is 0.135 same-task and 0.392 cross-task.
    Both defects push the same way, toward abstention, and every experiment so far has abstained. A method that
    is conservative in two compounding ways, on the gate that decides whether anything may ever deploy, will
    abstain whether or not the systems differ. That is the hypothesis the "why every experiment nulls"
    investigation is testing, and this adjudication is the first hard evidence for it.
41. ACTION. Tighten #11's enclosure to the full feasible-completion enumeration that #12 implements.
    THIS IS NOT A POST-HOC CHANGE MADE BECAUSE RESULTS WERE UNFAVOURABLE, and the defense is written down in
    advance by someone else: the root's own guidance item 5 says "Start unresolved hierarchy scores at [-1,1],
    ENUMERATE FEASIBLE COMPLETIONS TO NARROW THEM, and collapse only with a valid final-score certificate."
    #12 does that; #11 does it only partially. Tightening #11 is CONFORMANCE TO THE PRE-EXISTING WRITTEN
    SPECIFICATION, not a new choice. It is also free of outcome bias in the strictest sense: no trial episode has
    ever run, nothing is frozen, and there is no live data whose analysis could be moved by it.
    The change must be made BEFORE the freeze, verified by re-running vcompare to agreement, and disclosed.
42. WHAT IS NOT CLAIMED. Agreement after the fix would mean the two implementations agree, NOT that the monitor
    is correct: two implementations of the same misreading agree perfectly, which is the protocol's own wording
    and remains binding.
43. Ruling 34 is EXTENDED to REPORT.md, on the same grounds and for the same reason: section 13.0 lists it as not
    written, writing it is required by section 13.3 item 6, and the status column is a statement of fact about
    the freeze commit that writing the file falsifies. A status correction that changes no value, recorded with
    before/after text. The implementing agent was right to refuse to widen a ruling on a frozen pre-registration
    without being told; that refusal is the behaviour I want and it should not be discouraged.

# ===== REVISION 11, 2026-09-20: my "why everything nulls" hypothesis, adversarially tested and MOSTLY REFUTED =====
44. I ran five independent diagnostic lines and three adversaries against my own hypothesis, which was that the
    three null results are largely an artifact of a loose variance proxy and that "the method as published would
    tell practitioners they need ten thousand comparisons when one thousand would do". VERDICT: wrong in its
    premise, wrong in its number, right in one term, and the term it is right about did not produce the nulls.
45. WHERE I WAS WRONG, each checked rather than conceded.
    (a) THE PREMISE. "The method as published" says nothing of the kind. `grep -rn "17,097|17097" paper/` and
        `grep -rn "0\.1279" paper/` both return NOTHING. That figure exists only in the pre-registration of a
        trial that has never run. The paper's headline method is guarded BETTING, and paper/results_main.tex
        already publishes the estimator comparison in its own voice, at 13x the scale any diagnostic line
        reproduced: the range-only normal-mixture rule made no deployments in any initial scenario, a documented
        conservatism cost, against 96.85% for the directional betting gate. I raised an alarm about a claim the
        paper does not make, and presenting this as news would be wrong.
    (b) THE NUMBER. My 1,527 was wrong twice over: it fed a SAME-TASK paired variance into a FIXED-N formula for
        a CROSS-TASK design. The information floor -- what NO procedure whatsoever can beat -- is 3,099 pairs
        cross-task (KL 0.001149011 per pair, I-projection recomputed independently), and 1,079 even paired. The
        best valid, enclosure-compatible construction needs 6,697. Nothing reaches 1,000.
    (c) THE NULLS ARE REAL and survive every attack. At n = 568 the maximum power attainable by ANY level-alpha
        procedure is 0.2351; at the S1-only roster, 0.1485. No estimator rescues this.
    (d) MY INSTINCT TO SWAP THE VARIANCE PROCESS WAS INVALID. `variance_process = n` is FORCED, not chosen:
        thm:normal_cs builds V_n from PREDICTABLE ranges, and for a ternary score nothing in the past rules out
        any of the three values, so c_i = 2 and V_n = n. There is no free slot. Feeding it an empirical variance
        measures 0.189 miscoverage against a 0.10 nominal -- roughly twice -- and at rho = 100 that violation is
        MASKED by the rho floor, which is a trap rather than a defence. Had I acted on my instinct I would have
        broken validity and the masking would have hidden it.
    (e) MY OWN LIBRARY'S FUNCTION IS THE WRONG ONE. I would have reached for `wincs.betting_cs_ternary`. It is
        NOT enclosure-compatible: 1,164 monotonicity violations in 4,919 trials, and degrading a pair can RAISE
        its capital by 1.15 and switch a gate on. The correct object is `winstats.betting_log_e_ternary`, which
        is what prop:bet_running covers, has 0 violations in 7,878 plus an analytic argument, and is tighter
        anyway (6,697 vs 7,274 pairs).
46. WHERE I WAS RIGHT, and it is worth keeping. The frozen boundary IS loose on the guardrail -- by 2.55x in
    required n, not the 11x I claimed. That is a genuine defect of the frozen live specification. But 2.55x of a
    30.10x shortfall rescues nothing.
47. THE APPORTIONMENT, which is the answer to the question I should have asked first. Of the deploy-route
    shortfall from 17,097 pairs to the 568 available, as shares of the log-shortfall:
        estimator / variance proxy .............. 27.5%   (fixable, worth 2.55x)
        irreducible price of anytime validity ... 22.6%   (mostly not fixable; this is what monitoring costs)
        genuine no-difference, against budget ... 49.8%   (NOT FIXABLE BY ANYTHING)
    Half of it is simply that the two systems are identical on the top tier, 433/591 in both arms, and the roster
    is too small to certify that they are.
48. A CORRECTION THAT CHANGES THE FRAMING: EXPERIMENT 1 IS NOT A NULL. The RETAIN route FIRED at n = 100, the
    first look n_min permits, under every construction and both pairings. That is a successful guarded decision
    at the earliest legal opportunity. Only the DEPLOY route nulled. I have been calling the whole thing a null
    and that was sloppy. The adversary's deflation is kept: it fired because the latency gap is 4.46x, and a
    candidate at a true net benefit of -0.44, still plainly harmful, would not have fired at n = 100 at all.
49. ACTIONS. Keep `variance_process = n` (forced, and it changes no decision: probability that swapping the band
    alters any realised decision in the frozen trial set is at most 0.0057). Do NOT move delta, do NOT extend the
    horizon, do NOT switch to same-task pairing, do NOT add a contrast chosen because it could deploy. Promote
    the existing `monitor.betting_readout` to a PRESPECIFIED SECONDARY using `winstats.betting_log_e_ternary`,
    on the GUARDRAIL only, with its own reported decisions and no claim on the primary alpha, declared before
    execution and with the two-line monotonicity argument written down and reviewed. Never add WSR-EB: it
    false-certifies at 10x nominal alone and 28x on the joint gate under a legal drift. Free fixes: separate MBPP
    from HumanEval in the strata, and correct the horizon from 568 to at most 565 in every table.
50. WHAT THE PAPER SHOULD GAIN, and this is the real deliverable of the whole investigation: a SIZING statement,
    which main.tex currently lacks entirely. For a 3-point success non-inferiority margin against an equally
    accurate candidate, a guarded cross-arrival trial needs about 6,700 randomized pairs with the paper's own
    betting gate and about 17,100 with the range-only band, against an information floor of about 3,100 for any
    procedure whatsoever; a 10-point margin needs about 280 to 900. Plus the certifiable-margin inversion, which
    is the practitioner's actual question: at n = 568 an equal candidate can certify delta = 0.158 frozen or
    0.104 with the best valid band. A guardrail that certifies "not more than 15 points worse" is not a
    deployment guardrail, and saying so plainly is the honest content of a feasibility study.
51. ONE SHIPPED TRAP TO FIX: `wincs.pairs_for_power` sizes on the hierarchy net benefit alone, with no delta and
    no anytime-validity penalty. A guarded trial is bound by the GUARDRAIL, which depends on delta and the tie
    mass and not on the composite effect size at all. It is the one place this repository hands a practitioner a
    wrong number, and it is mine.

# ===== REVISION 12, 2026-09-20: my revision-10 adjudication was imprecise. The root has the better framing. =====
52. Revision 10 said the #11 monitor "is LOOSE: it retains an outcome the state has already excluded", which reads
    as an implementation defect. That is not what it is, and the root's CPU statistics review
    (reviews/arxiv_cpu_prereg_statistics_review.md section 1) is right: the comparison contract asked two
    differently-declared adapters to agree numerically and then called the difference a defect of one of them.
53. WHAT IS ACTUALLY TRUE, checked line by line against protocol_FINAL.md item 5 rather than assumed:
    (a) Item 5's `s_r = 1` branch has exactly two outcomes. If the certificate `(1-tol)*ell > L_r + 1e-9` fires,
        collapse to `[sgn, sgn]`; "Otherwise the enclosure stays `[-1, 1]`." On the reproducer the certificate is
        0.95 * 9.6 = 9.120 > 10.0, which is FALSE, so item 5 PRESCRIBES [-1, 1] and the code emitted [-1, 1].
        => THE #11 CODE CONFORMS TO ITS OWN DECLARED RULE. It is not an implementation defect and I should not
        have implied it was.
    (b) Item 5 is nevertheless INCOMPLETE RELATIVE TO ITEM 1 of the same protocol, which promises that an
        unresolved score is "narrowed ONLY BY ENUMERATING FEASIBLE COMPLETIONS". A two-case rule with an explicit
        "otherwise [-1,1]" is not an enumeration. The protocol contradicts itself, and item 1 is the promise.
    (c) THE MISSING CASE IS NAMEABLE, which is what makes this fixable rather than a matter of taste. Item 5
        carries a certificate for the REVEALED episode winning tier 1 and NONE for the PENDING partner being
        unable to win it. On the reproducer the pending partner needs a final cost below L_r*(1-tol) = 9.50 to
        win, and its elapsed is already 9.60, so a candidate win is infeasible and item 5 cannot see it.
    => THE DEFECT IS IN THE SPECIFICATION, NOT THE CODE AND NOT THE THEORY.
54. RULING. Complete item 5 with the reverse certificate, so that item 5 delivers what item 1 promises:
    if the pending partner's certified elapsed cost already exceeds what winning tier 1 would require, the
    partner's win is infeasible and that value is removed from the enclosure. This is conformance to item 1 and
    to the root's guidance item 5, it is a power improvement rather than a validity fix (the direction
    measurement stands: #11 was wider in 151,032 of 151,032 rows and never narrower, so nothing it produced was
    wrong), and it is outcome-free because no trial episode has ever run.
55. AND THE VALIDATION CONTRACT MUST BE RESTATED, which is the root's actual point and the more important half.
    Demanding exact numerical agreement to 1e-12 between an adapter built from the guidance formula and an
    adapter built from protocol item 5 validates nothing while the two policies differ: every disagreement is
    guaranteed and none of them is evidence. After item 5 is completed the two policies coincide and the equality
    contract becomes meaningful. Until then the 122,786 disagreeing looks are a CONTRACT MISMATCH, not 122,786
    findings, and I will describe them that way.
56. SECOND ROOT FINDING, taken seriously and NOT yet verified by me: the review says the last-look reduction
    (keep only the final look at each enrolled prefix) FAILS for the completed-data baselines, with an exact
    witness inside the T4 horizon. If that holds, the CPREFIX and NAIVE miscoverage numbers I reported are
    affected; the ADAPTER numbers may not be. Until I have reproduced the witness myself, every baseline number
    in the grid report is PROVISIONAL and is to be cited that way. The positive control's conclusion does not
    obviously survive unexamined either, since it is a statement about NAIVE.
57. Pattern worth naming, because it is the second time in two days. Both defects found this week were checks or
    rules that LOOKED complete and were not: a hash fixture that never hashed a file, a host gate that never
    detected a foreign process, and now an enclosure rule that promises enumeration and delivers two cases. The
    common signature is a specification asserting a general property while the implementation satisfies a
    special case, with tests written against the special case. Tests written from the IMPLEMENTATION cannot catch
    this; only a second implementation from the PROMISE can, which is exactly what #12 did.
