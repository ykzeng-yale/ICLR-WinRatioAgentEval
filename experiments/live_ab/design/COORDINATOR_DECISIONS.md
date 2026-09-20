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
      the deploy route requires an observed running success difference above r(N_P) - 0.03 = +0.1280 at n = 568;
      the same-task pilot difference is 0.000000 with a paired standard error of 0.0151, so the threshold is about
      8.5 standard errors away; the deploy route is therefore a PRE-SPECIFIED NEAR-CERTAIN ABSTENTION under
      pilot-like outcomes, NOT a logical impossibility. If a deploy occurs it is reported normally, with no claim
      that it was impossible.
    Likewise "the gate crosses at 92 pairs" is only the first n at which the radius falls below the PILOT effect
    magnitude 0.497, and the first permitted look is n_min = 100, so no decision can occur at 92 under this
    schedule. Whether any gate crosses is an outcome, not a plan.
    The phrases "unreachable by construction", "impossible whatever the outcomes" and "guaranteed abstention" are
    forbidden in every artifact of this program. delta = 0.03 and the frozen rule are unchanged.
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
