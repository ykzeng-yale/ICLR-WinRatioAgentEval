# live_ab: pre-registration protocol, FINAL (version string `v3-nm-guarded`)

**Prospective, physically randomized, pair-synchronous, live-stopped online A/B trials with open-weight models on one host.**

**Status: FINAL text for the freeze of section 14.1. Not frozen. No design episode has been run.**
**This file supersedes `protocol_v3.md` and `protocol_draft_v2.md` completely. It is not a diff and neither draft has
any residual force.** It resolves every BLOCKER and MAJOR of `audit_v3.md`, the MINORs of that audit, and the 25
`PROTOCOL-GAP` entries of the implementation specification; the disposition of each is in `audit_response_v3.md`.
The frozen configuration carries `"protocol_version": "v3-nm-guarded"` and `"rule_id": "nm_guarded_v3"`; those two
strings are the only version tokens that appear in any event, and they are identical in this file and in
`ARCHITECTURE_FINAL.md`.

**Relation to the implementation specification.** `ARCHITECTURE_FINAL.md` is the interface contract for the
implementers. **Sections 6.2, 6.3, 6.4, 7 and 8 of this file are the rule block (14.1 item 7); where
`ARCHITECTURE_FINAL.md` differs from them, `ARCHITECTURE_FINAL.md` is defective and this file governs.** A freeze test
(Appendix C) asserts that `lab_common.rule_block_sha256(config)` equals the rule-block hash computed from the frozen
tables of this file, so the two documents cannot be frozen in disagreement.

Intended location after review: `experiments/live_ab/protocol.md` on branch `session60/live-ab`; results under `results/live_ab/`.
This document becomes binding only through the program freeze of section 14.1. The accurate chronology phrase is
**"internally frozen, externally timestamped"** (never "preregistered" without that qualifier) and
**"frozen before any design-task outcome of the program"** (never "before any model call": out-of-design smoke,
calibration and rehearsal calls happen before the freeze and are tagged as such, section 5.8).

### Binding inputs, in order of authority

1. **`reviews/arxiv_live_design_guidance.md`** (root session, bounded independent review, 2026-09-19; SHA-256
   `a71965986165d56915a557a1a43998d9eb76a4e800dba670281c93720037ad1b`, at root main `4fe6d17`). Its nine numbered items
   and its "Primitive and theorem boundary" paragraph are adopted **literally**. Where this protocol and that file
   differ, that file wins and the difference is a defect of this protocol.
2. **`COORDINATOR_DECISIONS.md`, REVISION 2** (2026-09-19 20:30 UTC), which adopts the guidance and supersedes its own
   revision 1 wherever they differ. Revision 1 survives only where revision 2 is silent.
3. `critic_v2.md` findings N1-N22 on `protocol_draft_v2.md`. Every HIGH and MEDIUM finding is closed in the text below;
   the disposition of all 22 is in Appendix D.
4. The three audits `audit_v1_{statistics,provenance,claims}.md` and `audit_response_v1.md`; the reader reports
   `R1_accepted_method.md`, `R2_constraints_checklist.md`, `R3_harness_plan.md`, `R4_power_analysis.md`.

Root references are cited as `file:line` **by content digest, not by branch**: `src/winstats.py` SHA-256
`56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` and `paper/theory.tex` SHA-256
`ddaebf17e6e9b72822ff945d37475bdb176cba37b27f78fee3c8505e1881445f`. Both blobs are identical at
`session60/live-ab` (`b3f1122`) and at root `main` (`1c3e9f3`), verified by `git rev-parse` at writing time. A branch
name is not a citation: the shared clone is used concurrently by more than one session, so every reference in this
protocol resolves through a digest (see also the operational note in 12.4 item 2 on asserting `HEAD` before an anchor
commit).

### What v3 removes from v2, and why

| removed | reason |
|---|---|
| Configuration A (betting gates) as a traffic driver, and the whole two-configuration freeze | Guidance item 3 and revision 2 item 1: the normal-mixture band **is** the decision rule. `betting_log_e_ternary` is not used as a decision rule, is never fed partial scores, and appears only as a labelled post hoc computation on final complete scores with no error-control claim (revision 2 item 3). |
| The root-consultation block (RA1-RA5, RB1-RB5), its cut-off and its A/B branch | The root answered. Its answers are the guidance file; there is nothing left to ask before the freeze. |
| RFC 3161 timestamp authority | Revision 1, C17 REJECTED: an extra external dependency. |
| Private evidence archive | Revision 1, C20 SIMPLIFIED: everything needed to audit every reported number is deposited in the repository, gzip where large. |
| Anonymous hand-off variant | Revision 1, C26: the target is arXiv, not a double-blind venue. |
| Thermal probe and the `thermal` pause reason | Revision 1: no mechanism that needs a new external dependency. `power` (battery) survives; it is machine-checkable. |
| The 30-comment-per-trial anchor stream | Revision 1, C10 SIMPLIFIED: pushed commits on `session60/live-ab-anchors` plus exactly three issue comments per trial. |
| The token tier of the hierarchy | Guidance item 5 states the hierarchy as success > cost. The token tier decided 0.30% of pilot cross-task pairs and is not a common unit across two tokenizers (it forced T3 to use a different kernel from T1/T2/T4). |
| Margin 0.10 as the primary margin | Guidance item 6 and revision 2 item 4: `delta = 0.03` primary; the root refused a margin chosen for certifiability. |
| The separate "matched asynchronous comparator" of v2 section 8.6 | The enclosure-based band on the current full enrolled prefix **is** the rule (guidance items 3 and 5), so there is no second object to compare against. A completed-prefix read-out survives as a *coupled descriptive* monitor comparison (guidance item 7), never as evidence about monitoring under delay. |

**Label convention.** **incumbent** and **candidate**, never the letters A/B for arms (`paper/main.tex` calls the
candidate A while `paper/open_coding_appendix.tex` calls it B). Scores are always `compare(candidate, incumbent)`:
positive favours the candidate.

**Operator.** The operator of the trials is an **AI agent session** (session 60) working under the repository owner's
account, with read access to every file of the run. Every procedural safeguard below is written with that fact in view,
and the reports say so (section 14.7).

---

## 0. Protocol at a glance

| item | value |
|---|---|
| **Design** | Prospective online A/B. Disjoint pairs of consecutive arrivals from a frozen order. One fresh fair coin per **pre-enrolled** pair from OS entropy fixes the orientation (AB or BA). Each task runs under exactly one arm, once per trial. |
| **Trials, in execution order** | **T4** A/A control (`single_shot` vs itself) -> **T2** incumbent `single_shot`, candidate `self_test_repair` -> **T1** the reverse -> **T3** `single_shot` on Qwen2.5-Coder-7B-Instruct vs `single_shot` on IBM Granite 3.3 8B Instruct. |
| **Host** | One Apple M5, 10 cores, 32 GiB RAM, 262 GiB free disk (measured 2026-09-19 20:28 UTC). `llama.cpp` `llama-server`, GGUF Q4_K_M, loopback only. |
| **Roster** | MBPP-sanitized (427) + HumanEval (164) = 591 tasks (stratum S1), plus MBPP-full-only tasks that survive the prospective exclusions of 3.2 (stratum S2). Horizon `N_P` = all pairs of the frozen arrival order, formed **inside a stratum**, **at most 568** (3.3). |
| **Scores per pair** | `Z_i` (hierarchy, in {-1,0,+1}) and `D_i` (success difference, in {-1,0,+1}) from `winstats.compare`. |
| **Hierarchy** | Tier 0 `success`, higher better, tolerance 0. Tier 1 `cost` = episode wall-clock `latency_s`, lower better, **relative tolerance 0.05**. Tier 1 is eligible **only when both episodes succeeded**; a joint failure is a tie. Exact threshold equality is a tie. |
| **Monitoring rule (the decision rule)** | At every **evaluation trigger of 8.3**, on the **current full enrolled prefix** `n = N(t)`, for each score `j` in {`h`, `s`}: `r = normal_mixture_radius(n, alpha=0.00625, rho=100., variance_process=n)`; `L_j = sum(lower_j[:n])/n - r`; `U_j = sum(upper_j[:n])/n + r`; both intersected with `[-1, 1]`. |
| **DEPLOY candidate** | iff `L_h > 0` **and** `L_s > -delta`, at the **same** current prefix. |
| **HARM / RETAIN incumbent** | iff `U_h < 0`. Prespecified: the **hierarchy tail only**, not "either". |
| **Margin** | `delta = 0.03` (primary and only decision margin). `0.10` and `0.15` are exploratory read-outs, never a decision, never described as preserving success. |
| **Alpha** | Program `0.05`; four prespecified trials -> `0.0125` per trial; two monitored scores per trial -> `alpha_gate = 0.00625` per band. The same two-sided band serves the deploy tail and the harm tail; no extra split. `rho = 100.` |
| **Minimum / horizon** | `n_min = 100` enrolled pairs; no decision below it, no display at `n = 0`. Horizon = the full roster. No extension, ever. |
| **Guarantee** | Per trial, `P{any false decision statement} <= 0.0125`; program union bound over four trials `<= 0.05`. Rests on `thm:normal_cs` (`paper/theory.tex:288-304`) and `thm:drift_gate` (`paper/theory.tex:494-521`), with `prop:delay` (`paper/theory.tex:535-552`) for calendar-time display. |
| **Declared in advance** | The deploy route is a **pre-specified near-certain abstention**: it requires an observed running success difference above `r(N_P) - 0.03` (`+0.1280` at `n = 568`), about 8.5 paired standard errors above the pilot's 0.000000, and with the pilot effect sizes the T1 success gate at `delta = 0.03` first becomes reachable at **17,097** pairs against a roster of at most 568. It is **not a logical impossibility** and is reported under Appendix E if it occurs. This is a **prospective feasibility study** (section 1.3). |
| **Traffic switch** | A crossing stops randomization, finishes every already enrolled pair under its original assignment, logs the switch time and all in-flight exposure. Post-switch single-arm traffic is an **operational follow-up cohort**, never additional pairs for the A/B estimator. **No causal resource or latency saving is identified** (section 9.4). |
| **Not used as a rule** | `betting_log_e_ternary` (post hoc descriptive only, final complete scores only); prefix envelopes; maximization over prefixes; retained crossings; running intersections. |
| **Anchoring** | Pushed commits carrying the chain-head hash on `session60/live-ab-anchors`, plus exactly three comments per trial on issue #11 (start, decision, end). Never force-pushed. No timestamp authority. |
| **Evidence** | Everything needed to audit every reported number is in the repository (gzip where large): program chain, trial chains, worker spools with full request and response bodies, server logs, sandbox results, records. |
| **Deliverable before execution** | The freeze bundle of section 14.2, which is root guidance item 9 item-for-item. |

---

## 1. Purpose, scope, the feasibility declaration, and the claim lists

### 1.1 Purpose and scope

`EXPERIMENT_QUEUE.md:37` at root main lists, in full: "Conditional experiment | Concurrent open-model prefix study
with actual reveal timestamps; prospective randomized exposure trial | Required for measured operational savings or
live-deployment claims, which this paper does not make."

**What `live_ab` delivers against that entry:**

1. a **prospective randomized exposure trial**: four trials on one Apple M5 with open-weight models on the loopback
   interface, one program freeze before the first design-task outcome, a fresh operating-system-entropy coin per
   **pre-enrolled** pair, single exposure, and a monitoring rule fixed in advance that changes the traffic of a
   laboratory dispatcher when it crosses;
2. **actual reveal timestamps** with two concurrent workers and out-of-order reveals inside a pair, enrollment-indexed
   records updated by reveal-order events, nonanticipating enclosures (7.5), a fixed endpoint horizon, and at most one
   unresolved pair at any time.

**What it does not deliver, stated before any data exist:**

- **No deployment claim of any kind.** The "deployment" is a switch inside a laboratory dispatcher on public benchmark
  tasks on one laptop.
- **No measured operational time or token saving, and no causal resource or latency saving.** A single switched trial
  does not identify the counterfactual of continued A/B or of another stopping policy (guidance item 7; section 9.4).
- **No evidence about the value of partial-information monitoring under substantial delay.** Under pair-synchronous
  execution at most one pair is unresolved, so the enclosure content of the rule is bounded by the remaining duration
  of one episode. This is not a study of monitoring under delay.
- **No calibration evidence.** One A/A run is an implementation check, not an operating-characteristic estimate
  (guidance item 8).
- **No arm-symmetric cost measurement.** The cost tier is measured under two mechanisms that act unequally on the two
  arms of a pair: the within-pair duration asymmetry (in T1/T2 the faster arm is contended for essentially all of its
  duration and the slower one only during the overlap, 6.2) and the host-wide execution lock, which puts one arm's
  self-test wait inside its own cost while the partner's hidden-test verification holds the same lock outside the
  partner's cost (6.2, 5.7). Measured cost is therefore partly a **transfer between the arms of a pair**, in the tier
  that decided 53.16% of pilot pairs. It is disclosed, reported by arm, and given a prespecified descriptive read-out
  (S-lock, 8.8 item 8); it is not corrected, and no solo-latency statement is made.
- **No task disjointness across trials.** All four trials draw from the same roster (3.5 item 5); guidance item 6's
  "the reverse contrast uses new disjoint tasks" is **not met** and is declared as a deviation (10.3, 13.1).
- **No cost-neutral roster.** Exclusion rule 3.2 item 4 removes tasks whose *reference* solution verifies slowly under
  the trial load, so the roster is pre-filtered on the very dimension the cost tier measures (3.5 item 7).

Therefore, even after a fully successful program, the manuscript still may not say "measured operational savings",
"operational latency savings" or "live deployment", and **the paper's limitation "feasibility, not operational latency
savings" is retained**. The exact sentences the trials could add are in Appendix E.

In each trial:

1. tasks arrive in a prespecified order; consecutive arrivals form disjoint pairs;
2. a pair is **pre-enrolled** (its two arrival positions and its stratum are fixed and logged) and only then does a
   fresh fair coin from OS entropy fix which position receives the candidate; the coin is durably logged and fsynced
   **before either episode is dispatched**; each task is executed under exactly one arm, once;
3. the two episodes of the pair run concurrently on two workers; their outcomes are revealed out of arrival order with
   recorded timestamps, and each reveal updates the **existing enrollment-indexed record** of that pair;
4. the monitoring rule of section 8, fixed before the first design-task outcome of the program, is evaluated at every
   evaluation trigger of 8.3 on the current full enrolled prefix;
5. when the rule crosses, the dispatcher stops randomizing and a new observation phase begins; nothing is replayed.

**Pilot disclosure, repeated with every result of every trial.** The 1,182 delivered coding episodes
(`results/local_stream/`) are **pilot data on a different serving stack (MLX 4-bit, not GGUF Q4_K_M)**. Every one of the
following was chosen with knowledge of pilot outcomes of the same tasks: the hierarchy and its tolerance, the cost
unit, the hypothesis directions, the execution order of the trials, the label of T2, and the decision to run T1 and T2
at all. `delta`, `alpha`, `rho`, `n_min` and the horizon were **not** chosen by session 60: they are the root's values
(guidance items 4 and 6, revision 2 items 2, 4 and 9). No pilot episode enters any trial table, and no trial table is
pooled with a pilot table.

### 1.2 The four trials

| trial | incumbent | candidate | what is known in advance | prespecified expectation (section 11) |
|---|---|---|---|---|
| **T4** "A/A control" | `single_shot` on Qwen2.5-Coder-7B | the identical system | exact null by construction: `mu_i = 0` for any hierarchy and any load | no decision. A decision has probability at most 0.0125 under the exact null and is reported and investigated, never discarded |
| **T2** "costly candidate with equal pilot success" | `single_shot` | `self_test_repair` | mirror image of T1 on the same model and tasks | **HARM / RETAIN_INCUMBENT**, expected at the first look (`n = n_min = 100`): pilot `Zbar = -0.4993`, `r(100) = 0.4657` |
| **T1** "cheap candidate" | `self_test_repair` | `single_shot` | pilot on the same 591 tasks (MLX stack): equal success 433/591 and 433/591, candidate about 4.46x faster | the **hierarchy** condition `L_h > 0` is expected to be met at `n = 100`, and the **success guardrail** `L_s > -0.03` is expected never to be met, so the trial is expected to end in `ABSTAIN_AT_HORIZON`. This is the scientific content of T1 (section 1.3) |
| **T3** "model swap" | `single_shot` on Qwen2.5-Coder-7B | `single_shot` on Granite 3.3 8B Instruct | nothing produced by this harness; vendor-published aggregate benchmark pass rates were used to choose the model (2.4), which is an **outcome-informed criterion at the aggregate level** | unknown; abstention is likely unless the composite effect is large |

T1 and T2 test **one contrast with the roles exchanged**. "The hierarchy band excluded 0 upward in T1" and "the
hierarchy band excluded 0 downward in T2" are the same scientific statement. **T1 and T2 are never cited as two
confirmations, as a replication, or as two estimates.** The program union bound 0.05 is printed next to every joint
mention (1.4 item 9). Scope of T4: because the two arms are one system and nothing in the harness depends on the arm
label, T4 checks the coin path and label blindness only; it cannot reveal any arm-dependent defect (retry, timeout,
routing), because there is no arm difference to depend on.

### 1.3 Declaration: this is a prospective feasibility study with a guaranteed-abstention deploy route

This section is computed **before any data** and is part of the frozen text. It is not a post hoc explanation.

**The radius.** `r(n) = normal_mixture_radius(n, alpha=0.00625, rho=100., variance_process=n)`
`= sqrt((n + 100) * log((n + 100) / (100 * 0.00625**2))) / n` (`src/winstats.py:51-61`).

| `n` | `r(n)` | `n` | `r(n)` | `n` | `r(n)` |
|---|---|---|---|---|---|
| 92 | 0.495026 | 250 | 0.252700 | 450 | 0.179441 |
| 100 | 0.465693 | 295 | 0.228707 | 500 | 0.169296 |
| 120 | 0.408804 | 350 | 0.206911 | 565 | 0.158404 |
| 150 | 0.350660 | 400 | 0.191701 | **568 (the horizon ceiling)** | **0.157952** |
| 200 | 0.290460 | | | 569 (reference row only) | 0.157802 |
| | | | | 626 | 0.149925 |

**No radius in this protocol is hand-typed.** Every row above, and every row of 11.2 and 11.3, is regenerated from
`src/winstats.py` by `dryrun_live_ab.py --radius-table` into `results/live_ab/freeze/radius_table.csv`, which is the
freeze-bundle artifact; the text is checked against that file by the freeze test of Appendix C (this closes
`PROTOCOL-GAP PG-20`). The `n = 569` row is retained only because earlier notes quote it; the **horizon of this
program is `N_P <= 568`** (3.3).

*Correction of record, stated openly.* `COORDINATOR_DECISIONS.md` revision 2 item 5 reports `r(92) = 0.4966`. The
recomputed value is **`r(92) = 0.495026`**; `0.4966` is close to the pilot net benefit, not the radius, and the two
appear to have been transposed in that note. `r(295) = 0.2287` and `r(569) = 0.1578` are confirmed exactly.
**No conclusion changes.** The coordinator's "about 92 pairs" follows from the three-tier pilot value `0.4968`
(`r(92) = 0.495026 < 0.4968 <= r(91) = 0.499041`); the frozen two-tier value `0.4993` gives `n = 91` instead. Either
way the binding constraint is `n_min = 100`, which is larger than both, so the first admissible evaluation is
unchanged and the unreachability result below is untouched. Both values were recomputed with `.venv/bin/python` against
`src/winstats.py` at SHA-256 `56955ce0...` before this protocol was written.

**The pilot effect sizes, recomputed for the frozen two-tier hierarchy.** Over all 591 x 591 ordered cross-task pairs
of the pilot roster (diagonal excluded), with tier 0 `success` at tolerance 0 and tier 1 `cost` = `latency_s` at
relative tolerance 0.05, eligibility only when both succeed:

| quantity | T1 orientation (candidate `single_shot`) | T2 orientation (candidate `self_test_repair`) | T4 (A/A) |
|---|---|---|---|
| P(win) / P(tie) / P(loss) | 0.7115 / 0.0762 / 0.2122 | 0.2122 / 0.0762 / 0.7115 | 0.4510 / 0.0979 / 0.4510 |
| hierarchy net benefit `Zbar` | **+0.4993** | **-0.4993** | 0.000000 |
| share decided at tier 0 / tier 1 | 0.3922 / 0.5316 | 0.3922 / 0.5316 | - |
| success difference `Dbar` | **0.000000** (P(+1) = P(-1) = 0.1961, P(0) = 0.6078) | 0.000000 | 0.000000 |

(For comparison, v2's three-tier hierarchy at tolerance 0.10 gives `Zbar = +0.4968` and reproduces R4's published
0.709/0.079/0.212 exactly; the token tier decided 0.30% of pairs. Dropping it moves the planning value by 0.0025.)

**The consequence, which is the reason for this section.** A gate crosses when the observed running average beats the
radius. With a constant observed value:

| condition | requirement | smallest `n` that can satisfy it |
|---|---|---|
| T2 harm, `U_h < 0`, at `Zbar = -0.4993` | `r(n) < 0.4993` | `n = 91`; first admissible look `n = n_min = 100` |
| T1 hierarchy, `L_h > 0`, at `Zbar = +0.4993` | `r(n) < 0.4993` | `n = 91`; first admissible look `n = n_min = 100` |
| **T1 success guardrail, `L_s > -0.03`, at `Dbar = 0`** | `r(n) < 0.03` | **`n = 17,097`** |
| the same at `delta = 0.05` | `r(n) < 0.05` | `n = 5,789` |
| the same at `delta = 0.10` | `r(n) < 0.10` | `n = 1,378` |
| the same at `delta = 0.15` | `r(n) < 0.15` | `n = 626` |
| the same at `delta = 0.20` | `r(n) < 0.20` | `n = 372` |

**The roster gives at most 568 pairs (3.3). A DEPLOY decision therefore requires an observed running success
difference above `r(N_P) - 0.03`, which is `+0.1280` at `n = 568` and `+0.1278` at `n = 569`; the same-task pilot
difference is `0.000000` with a paired standard error of `0.0151`, i.e. the threshold is about 8.5 standard errors
away. The deploy route is declared, before collection, a PRE-SPECIFIED NEAR-CERTAIN ABSTENTION; it is NOT a logical
impossibility, and if it occurs it is reported under Appendix E's DEPLOY template without any claim that it was
impossible.** The phrases "unreachable by construction" and "impossible whatever the outcomes" are forbidden
(1.5 item 13).

**What follows from that, and what does not.**

- The program is declared, before collection, a **PROSPECTIVE FEASIBILITY STUDY whose deploy route is a pre-specified
  near-certain abstention**. Its scientific content in T1 is that **the composite gate crosses while the success
  guardrail refuses**:
  the guarded rule behaving exactly as specified, live, on real randomized traffic.
- **The horizon, the margin and the rule are not changed to make a deploy reachable.** No horizon extension, no margin
  loosening, no model replacement after unfavourable monitoring (guidance item 6; revision 2 item 5). Any such change
  would be a new protocol version with its own freeze, its own alpha and its own audit, and every trial started after
  it would lose the wording of claims 1 and 2 (14.3).
- This is **not a defect of the design and not a defect of the method**. The permitted sentence is "this prespecified
  rule did not certify margin `delta = 0.03` on these data at this horizon". The forbidden sentences are
  "not certifiable", "cannot be certified at this sample size", "impossible for any method" (1.5 item 13).
- T2's harm route and T1's hierarchy route are **reachable and are the live content of the program**: a real crossing,
  a real traffic switch, a real receipted decision time.

### 1.4 Claims the trials MAY support (each only if literally true at the end)

`N` is always the computed count of executed arrivals; `tau` the decision prefix; `n` an enrolled prefix.

1. "An internally frozen, externally timestamped, single-exposure, live-stopped prospective A/B trial on `N` fixed
   public benchmark tasks with open-weight models served over the loopback OpenAI-compatible interface on one Apple M5;
   the orientation of each **pre-enrolled** arrival pair was assigned by the operating-system CSPRNG and durably logged
   before either episode was dispatched (no stored seed; **operator-attested, not independently verifiable**)."
2. "The monitoring rule was the split normal-mixture confidence sequence of `src/winstats.py` at SHA-256 `56955ce0...`
   with `rho = 100.`, `V_n = n`, `alpha_gate = 0.00625` per band, margin `delta = 0.03`, minimum 100 enrolled pairs and
   horizon `N_P`, all frozen before the first design-task outcome of the program. Under adaptedness and boundedness of
   the scores in `[-1,1]`, the probability that the rule issues a deploy decision at any enrolled prefix at which the
   running conditional-mean criteria are false, or a harm decision at a prefix at which the running conditional-mean
   hierarchy net benefit is nonnegative, is at most **0.0125** in that trial." If the trial ran after a harness-only
   re-freeze, the sentence adds "harness files were changed after `N` program outcomes by the procedure of 14.4; no
   rule parameter changed".
3. "In trial Tk the rule crossed at enrolled pair `tau`; the decision event was externally receipted at server time t;
   randomization stopped; every already enrolled pair was finished under its original assignment; the remaining
   arrivals ran under the decided arm in the laboratory dispatcher, on this host and under this serving regime."
   A measured event, not a replay, restricted to the arrivals that actually ran.
4. "The decision was taken at enrolled pair `tau`; `M = N_P - tau` pairs of the prespecified roster were not enrolled
   (`M` is determined by the prespecified roster length `N_P`); measured wall-clock and token totals of the run on this
   host under this serving regime were ...". Any time or token "saving" is outside this claim and is a labelled
   projection (9.5).
5. "Outcomes were revealed out of arrival order with recorded timestamps; each reveal updated the enrollment-indexed
   record of its pair; at most one pair was unresolved at any time, and the enclosure content of the rule at the
   decision was [exact enumeration]. This is not evidence about the value of monitoring under delay."
6. "Failure-inclusive usage accounting reconciles client and server counters to within X tokens [wording fixed by the
   pre-freeze counter test, 13.1]; the sampling parameters as parsed by the server were recorded for every request and
   equalled the frozen golden object."
7. T2: "the prespecified rule rejected the candidate on the composite (hierarchy upper endpoint below 0); the incumbent
   was retained". T4: "in one A/A control path no band crossed" (or, if one did, it is reported as the rare event it
   is, investigated, and never discarded). T3: whatever happens, including abstention and deferral.
8. "The success guardrail at the margin `delta = 0.03` was **not** met at any enrolled prefix; the lower endpoint
   `L_s` at the reported prefix was [value] against the threshold `-0.03`. Before collection this route was declared a
   **pre-specified near-certain abstention** at this horizon (1.3): meeting it requires an observed running success
   difference above `r(n) - 0.03` (`+0.1280` at the horizon `n = 568`), `r(n) < 0.03` first holds at `n = 17,097`, and
   the roster gives at most 568 pairs." Non-crossing is abstention on the deploy route. **The sentence never says the
   outcome was impossible.**
9. Wherever two or more trials appear in one table, abstract or paragraph: "each trial has its own error budget of
   0.0125 and the union bound over the four decisions is 0.05".
10. "A composite that crossed while the prespecified success guardrail refused" is the **specified** behaviour of a
    guarded rule at a margin the data cannot reach at this horizon, and is reported as such.

### 1.5 Claims that are FORBIDDEN in any report, index, PR text, issue comment or manuscript sentence

1. Production A/B evidence, user benefit, deployment safety, or "deployed" without "in the laboratory dispatcher";
   "measured operational savings", "operational latency savings", "live deployment".
2. A population, fixed-roster (`theta_N`), superpopulation or fresh-task effect; iid-task inference; the word
   "independent" for pairs or episodes.
3. Empirical calibration or type-I-error control from one or four streams; "holds its level"; "error rate is zero";
   any operating-characteristic statement derived from T4.
4. Equivalence or non-inferiority from equal or similar success counts. Only a crossing of the success guardrail at
   `delta = 0.03` could be called non-inferiority at that margin, and it is declared a pre-specified near-certain abstention (1.3). A crossing of
   an exploratory read-out at 0.10 or 0.15 is **never** reported as non-inferiority at that margin and never as
   "success was preserved".
5. "Approval of the incumbent", "the incumbent satisfies the guardrail", success harm or safety harm from a hierarchy
   upper-endpoint crossing. A harm decision is a statement about the **composite only**.
6. Joint 95% coverage from marginal bands; a "two-sided 95%" object from two one-sided processes; a program-wide alpha
   where each trial used its own; any simultaneous statement without the stated union bound.
7. Significance of resource differences; t, Welch, cluster-t, bootstrap or delta-method intervals; win-ratio confidence
   sequences; anything from `src/wincs.py`; any error-control claim for the post hoc betting read-out of 8.8.
8. Hardware-, model-, workload- or tokenizer-invariant rankings; dollars, energy or "compute" from token counts;
   cross-model token comparisons as cost. For T3: any statement about either model's latency when served alone.
9. A causal assignment-average reading without naming the coin model, the filtration, the concurrency regime and the
   assumptions of 7.4 (including "no dependence of a task's record on a later coin" and "the operator does not act on
   coins").
10. Measured time or token savings derived from counterfactual or replayed paths; per-task "operational cost" from
    retained-only totals; `M / N_P` or any percentage of exposures avoided, anywhere; any wall-clock, throughput or
    per-episode latency comparison across the two observation phases of a trial (they use different schedulers).
11. "Preregistered" without "internally frozen, externally timestamped"; "before any model call"; "publicly
    timestamped" without naming the public repository and issue.
12. Bit-reproducible generation; independent re-adjudication of success labels; exhaustive correctness. Success is the
    archived verifier label.
13. "Assumption-free", "impossible for any method", "not certifiable", "cannot be certified at this sample size",
    **"unreachable by construction"**, **"impossible whatever the outcomes"**, **"a deploy decision was impossible"**,
    "conservative" without conditions, mechanism claims from post-crossing diagnostics. The permitted sentences are
    "this prespecified rule did not certify margin `delta` on these data at this horizon" and, for planning, "for this
    rule, this allocation and this roster the reachability threshold is `n = ...`".
14. That post-switch single-arm data validate, contradict or refute the decision, or predict future benefit.
    Post-switch rates are not compared with pre-switch rates of either arm.
15. That the hierarchical rule is generally better than component rules.
16. That the root "approved" the trial, the PR or the methods beyond what the guidance file literally states.
    Owner-side verification is AI review by a separate code path of the same session: not human peer review, not
    independent verification, not author sign-off, and it says so.
17. Mock, dry-run or rehearsal outputs cited as observations.
18. Asynchronous-monitoring gains; "early certificates" as a benefit; any causal reading of the completed-prefix
    comparator of 9.4, which is coupled and descriptive.
19. The word "guarded" (guarded deployment, guardrail passed) without the margin in the same sentence.
20. T1 and T2 as two confirmations, a replication, or two estimates.
21. "Physically randomized" without the qualifier of claim 1; "verifiable coin"; "tamper-proof log". The permitted
    description of the log is in 12.5.
22. Differences between strata, phases or periods attributed to one cause; the permitted wording is
    "mixes ... and cannot separate them".
23. Any causal statement about resources, latency or cost **saved by stopping**, or about this monitoring policy
    against another monitoring policy (9.4).
---

## 2. Systems

### 2.1 Hardware, host, working locations

One Apple M5 laptop, **10 cores, 32 GiB RAM (34,359,738,368 bytes), 262 GiB free disk** (measured on the serving host
2026-09-19 20:28 UTC; Hugging Face model cache 59 GiB already present), macOS 26.5.2 (build 25F84) at drafting time.
The exact chip string, core count, memory, OS build, `kern.boottime` hash and power state are read from an **allowlist**
at every invocation and logged; nothing else about the host is recorded (no user name, no host name, no process
listing). **The root session's host is not used for any execution.**

During a trial: mains power, `caffeinate` active, no other GPU job (checked by the host quiescence gate of 5.7.1,
whose limits are stated there), exclusive lock file, preflight scan of the service
ports; the harness refuses to attach to a server it did not start. Hardware and runtime are printed next to every
resource table; no hardware-invariant statement is made.

**Working locations (tokens in every tracked artifact).** Execution happens in **the main clone**, branch
`session60/live-ab` (revision 1, C15: no second clone; **this is a coordinator decision and is not reopened here, so
the former open item of Appendix F is closed by the two guards below, not by moving the working location**).

**The two guards that make the shared clone safe, both non-amendable:**

1. **Identity assertion at every invocation and before every commit** (12.4 item 2): the process asserts that the real
   path of the working tree, its `HEAD` branch and its `git rev-parse HEAD` are the frozen ones. A violation before a
   commit is `anchor_failed(tree_state)`; a violation at invocation start is `preflight_refused(worktree_identity)`.
2. **A periodic worktree-integrity check while an invocation runs** (6.4 row 27, `worktree_drift`): every 60 seconds
   the orchestrator recomputes the SHA-256 of every freeze-bundle file it can read, of every closed chain segment and
   of `src/winstats.py`, and compares them with their bundle values. This is what detects another session checking out
   a branch or merging in the same clone **during** a multi-hour trial, which nothing else in this protocol would see.

`<WORK>` = a git-ignored directory inside the clone holding
weights links, the serving build and uncompressed intermediates; `<HF_CACHE>`; `<LLAMA_BUILD>` = `<WORK>/llama.cpp-build`,
outside the repository tree but under the home directory. Preflight asserts that the real paths of `<WORK>`,
`results/`, the task files, records, request bodies, spools, server logs and `<LLAMA_BUILD>` lie under the home
directory, because the Seatbelt profile of the sandbox is allow-default and denies reads and writes only under the
home directory and the temp trees (5.7). Preflight also checks at least 20 GiB free disk and that `<WORK>` is
git-ignored.

**Anchors are pushed to a dedicated branch `session60/live-ab-anchors`** (12.4); no run ever force-pushes any branch.

### 2.2 Serving software and the manifest fields that are pinned

`llama-server` built from llama.cpp commit `4fea119de30f6a923992780f6fd5ccb0bee5d47d` (already pinned in
`experiments/tau2_open/config.json`). On this host `build/bin/llama-server` is a 33 KB launcher that links through
`@rpath` to nine libraries (`libllama-server-impl`, `libllama-common`, `libmtmd`, `libllama`, `libggml`,
`libggml-cpu`, `libggml-blas`, `libggml-metal`, `libggml-base`), which hold all sampling, scheduling and Metal code.
"Binary hash" therefore always means **launcher and libraries**. Before the freeze:

1. the checkout is built into `<LLAMA_BUILD>`, a durable directory; `git status --porcelain` of the checkout must be
   empty and is recorded; cmake options, compiler version, SDK version and the SHA-256 of the configure and build logs
   are recorded;
2. the **serving manifest** is assembled and is part of the freeze bundle; it is re-verified at every invocation and at
   every server start and restart. **Manifest fields, all pinned:**

   | field | content |
   |---|---|
   | `llama_cpp_commit` | `4fea119de30f6a923992780f6fd5ccb0bee5d47d` |
   | `launcher_sha256` | SHA-256 of `build/bin/llama-server` |
   | `libraries[]` | for every non-system library that `otool -L` resolves **recursively**: tokenized name and SHA-256 |
   | `metal_library` | SHA-256 of the Metal library (embedded or external) and which of the two it is |
   | `resolved_rpath` | the resolved `@rpath`, tokenized |
   | `cmake_options`, `compiler_version`, `sdk_version` | literal strings |
   | `build_log_sha256`, `configure_log_sha256` | SHA-256 |
   | `props_build_info` | `/props.build_info`, which must contain the commit prefix |

**Frozen launch line, one process per model** (the three cache switches are structural, see 13.2 and finding N7):

```
llama-server -m <HF_CACHE>/<gguf file> --alias <alias> --host 127.0.0.1 --port <port>
  -np 2 -c 16384 --no-kv-unified -ngl 99 --jinja --metrics --no-context-shift --offline
  --no-cache-prompt --cache-ram 0 --slot-prompt-similarity 0.0
  --log-file <WORK>/live_ab/<trial>/logs/llama_<port>.log --log-timestamps
```

`-np 2` equals the number of workers, so no request ever waits for a slot; `--no-kv-unified -c 16384` gives each slot
8,192 tokens (pilot maximum summed over a `self_test_repair` episode: 3,934 prompt and 1,474 completion tokens);
`--no-context-shift` turns an overflow into a visible truncation; `--offline` forbids network access;
`--no-cache-prompt`, `--cache-ram 0` and `--slot-prompt-similarity 0.0` remove every server-side prompt-reuse path
(`_llama_server_help.txt:426, 590, 694`), which is what makes the per-response assertion `timings.cache_n == 0` a
receipt rather than a hope. Ports: 8091 (Qwen2.5-Coder), 8092 (T3 candidate). T1, T2, T4: one resident server for the
whole trial. T3: **both servers resident for the whole trial including the follow-up cohort**, so the serving
arrangement is identical for both arms and does not change at the switch.

Reasons for not using the pilot's `mlx_lm.server` 0.31.3 (R3 section 0): it routes every seeded request to a
single-request path and drains running batches, so two workers would only queue; it returns no sampler settings; its
`model` response field echoes the request. `llama-server` with `"verbose": true` returns
`__verbose.generation_settings`, `id_slot`, token counts and the rendered prompt; `usage` and `timings` are in the
non-streamed response; `model` is the server-side alias; `/metrics` exposes cumulative token counters. All of this is
**proven on the real server in the pre-freeze phase** (5.8); a failed proof stops the program (13.2).

Because GGUF Q4_K_M under llama.cpp is a different quantization and kernel path from the pilot's MLX 4-bit build,
**all pilot numbers are planning numbers only** and are never pooled with trial numbers.

### 2.3 Models

| role | base model (licence) | GGUF repository @ revision | file | bytes | SHA-256 |
|---|---|---|---|---|---|
| T1, T2, T4 both arms; T3 incumbent | `Qwen/Qwen2.5-Coder-7B-Instruct` (Apache-2.0) | `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` @ `13fb94bfda8c8cf22497dc57b78f391a9acb426a` | `qwen2.5-coder-7b-instruct-q4_k_m.gguf` | 4,683,073,536 | `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c` |
| T3 candidate | `ibm-granite/granite-3.3-8b-instruct` (Apache-2.0) | `ibm-granite/granite-3.3-8b-instruct-GGUF` @ `e40e9dd739c7be00fa965c16ce167088190ce114` | `granite-3.3-8b-instruct-Q4_K_M.gguf` | 4,942,873,344 | `77bcee066a76dcdd10d0d123c87e32c8ec2c74e31b6ffd87ebee49c9ac215dca` |

Both files are already present in `<HF_CACHE>` on the serving host (revision 2 item 12); **no weight download is
needed for any trial**. The SHA-256 values above are the Hugging Face content-addressed blob names as found in the
cache. **They are treated as expectations, not as facts**: the preflight of every invocation recomputes the SHA-256 of
the real file and compares, because on this host the cache blob is itself a symlink into a second content-addressed
store, so the name alone does not prove the content. A mismatch is `invocation_refused(weights_hash)` (6.4 row 21) and
the exact recomputed digests are pinned into the freeze bundle in the pre-freeze phase (Appendix A).

Aliases: `qwen2.5-coder-7b-instruct-q4km`, `t3-candidate`. An alias check alone proves only that the process answers
under the name the harness gave it, so model identity is checked at every server start and restart by: the real path
of `/props.model_path` equals the hashed GGUF; the GGUF SHA-256 is recomputed; the GGUF metadata reported by the server
(`general.name`, parameter count, vocabulary size) equal the golden `/props` object (13.2). The `model` field of every
response must equal the arm's alias.

**Licence evidence** ("open weights alone do not establish an unrestricted licence"): for each model the freeze bundle
records repository id, revision, and the SHA-256 of the `LICENSE` file at that revision, or, where the repository has
only a model card, the literal statement "licence declared on the model card only" plus the base-model repository, its
revision and its LICENSE hash. Both models are declared Apache-2.0. Models under a Qwen research, Llama, Gemma,
OpenRAIL or "research/non-production" licence are not eligible. No API key is read; the HTTP client hard-asserts a
loopback base URL; preflight fails if an API-key environment variable is present; there is no LLM judge (success is the
executable verifier). The live runner shares no entry point and no import with the repository's historical commercial
collection scripts.

Memory: 4.7 GB (coder) + 4.9 GB (Granite) + at most 2.6 GB KV cache per server at 16k context; inside 32 GiB with the
two T3 servers resident simultaneously.

### 2.4 T3 candidate: selection criteria and preflight rules

Requirements used to pick the model: (i) Apache-2.0 or MIT weights; (ii) a different model family from Qwen (vendor,
tokenizer, training data); (iii) parameter count close to the incumbent's 7.6 B, so the cost tier is not decided by
size alone; (iv) a GGUF published by the licensor, so licence evidence is first-party; (v) a dense transformer
supported by the pinned llama.cpp commit with its embedded chat template under `--jinja`; (vi) instruction-tuned, with
vendor-published code-generation pass rates of the same order as the incumbent's.

**Honest status of (vi):** published code-generation ability of instruction models is reported as HumanEval and MBPP
pass rates, and those benchmarks are the design roster. Criterion (vi) is therefore **outcome-informed at the aggregate
level**. The correct statement, printed with every T3 result, is: "no outcome produced by this harness was used;
vendor-published aggregate pass rates on the same public benchmarks were used for criterion (vi)". The numbers and
their sources are recorded in the freeze bundle during the pre-freeze phase. Granite 3.3 8B Instruct meets (i) to (v)
(8.2 B parameters, Apache-2.0, IBM-published GGUF, exactly one non-split Q4_K_M file, not gated; verified 2026-09-19).
Considered and failing a non-outcome criterion: `microsoft/phi-4` (14 B, iii), `microsoft/Phi-4-mini-instruct`
(3.8 B, iii), `01-ai/Yi-Coder-9B-Chat` (no first-party GGUF, iv), DeepSeek-Coder, Code Llama, StarCoder2, Gemma (i).
`mistralai/Mistral-7B-Instruct-v0.3` fails only the outcome-informed criterion (vi) and is listed as such.

**Preflight rules (all evaluated before the freeze from preflight facts only; no design-task outcome is involved):**

1. **File rule.** The repository at the pinned revision contains exactly one file matching `*[Qq]4_[Kk]_[Mm]*.gguf`
   that is not a split part (`-0000N-of-`). Zero or several matches fail.
2. **Hash rule.** The recomputed SHA-256 and byte size of the local file equal the pinned values of 2.3.
3. **Licence rule.** Licence evidence as in 2.3 can be recorded.
4. **Template rule.** The server starts with `--jinja` with no template error or warning in its log;
   `/props.chat_template` is non-empty; for the reference request the rendered prompt (`__verbose.prompt`) contains the
   system text and the user text exactly once each, in that order, and ends with the template's assistant generation
   prefix; the response content contains no template control token.
5. **Receipt rule.** The receipt smoke test of 13.2 passes, including `timings.cache_n == 0` on every response.
6. **Format-conformance rule (outcome-blind).** On the ten out-of-design prompts of 5.8, at least 9 of 10 responses of
   **each** model contain a code block that `extract_code` turns into a non-empty program. Correctness of the program is
   neither computed nor looked at. The prompts and the extractor were developed on the incumbent's model family and are
   not changed.

**There is no fallback model.** If any rule fails, **T3 is not run** and is reported under its own heading as
"deferred: candidate failed preflight rule k". A deferred T3 does not release its 0.0125 to any other trial: the alpha
table is frozen for four trials and is not re-allocated (guidance item 4, "Freeze trial count and allocation before
collection").

Every T3 statement carries: "prompts and the code extractor were developed on the incumbent's model family; the two
model families may differ in their exposure to these public benchmarks, and this contrast cannot separate ability from
contamination."

### 2.5 Arms

| trial | incumbent | candidate | servers |
|---|---|---|---|
| T4 | `single_shot`, coder | `single_shot`, coder (identical system; the arm label is the only difference; the verifier confirms the two arms' job payloads are byte-identical apart from the label) | 8091 |
| T2 | `single_shot`, coder | `self_test_repair`, coder | 8091 |
| T1 | `self_test_repair`, coder | `single_shot`, coder | 8091 |
| T3 | `single_shot`, coder | `single_shot`, T3 candidate | 8091 + 8092 |

Workflows are the delivered, audited ones, reused **byte-identically** through an injected model object:
`experiments/local_stream/agent.py` (SHA-256 `3cf2056330c72ebd5d2884f48d6ec2daa706fcc685ad67e3c2609d809ff75b64`),
`sandbox.py` (`d461570937ddbe1fb241288721a1a06b44bd41dd72ccdc2e2ffa2f144184c6ff`),
`verify.py` (`7473678b1990ca2a5a1900b45251fddcd2882f2b371d76d3a59fe669a607dbb6`). Any byte change requires a new leakage
and sandbox audit before the freeze. `single_shot` = one model call. `self_test_repair` = code call, test-writing call,
execution of the agent's own tests in the Seatbelt sandbox, at most 2 repair calls; hidden tests never enter a prompt
and the verifier gives no feedback to the agent. The legacy field `variant_letter` inside the reused record is ignored;
the harness carries its own `arm` field in {`incumbent`, `candidate`}.

**Both systems and both protocols are fixed for the whole trial** (guidance item 2). No version, prompt, template,
sampler, cap or serving argument changes inside a trial or between trials.

---

## 3. Task roster, exclusions, arrival order, and the reuse statement

### 3.1 Sources (pinned; mutable `master` URLs are never used)

| stratum | source | pinned revision | file | bytes | SHA-256 | licence evidence |
|---|---|---|---|---|---|---|
| S1 | MBPP **sanitized**, all 427 problems (not a test split) | google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533` | `mbpp/sanitized-mbpp.json` | 255,053 | `ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9` | pinned file from the Apache-2.0 `google-research` repository; the CC-BY-4.0 statement comes from the dataset card, as recorded in `results/local_stream/data_manifest.json`; both facts recorded literally |
| S1 | **HumanEval**, all 164 problems | openai/human-eval `463c980b59e818ace59f6f9803cd92c749ceae61` | `data/HumanEval.jsonl.gz` | 44,877 | `b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef` | MIT |
| S2 | MBPP **full**, problems not in the sanitized subset | google-research `f82046ba5aabbbb427dbfd38a254d26bff08b533` | `mbpp/mbpp.jsonl` | expected 563,743 | expected `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f` (measured once on the mutable `master` URL, never at the pinned revision; verified at download; **a mismatch means roster S1**) | as for S1 MBPP |

The S1 canonical task list is the delivered one (list SHA-256
`23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`). The S2 file is not on disk; fetching it (one
pinned URL, byte and hash check, refusal on mismatch) is a pre-freeze step, approved under revision 1 C9. Raw
third-party data stay outside git; `roster.json` holds uids, strata and exclusion reasons only, no task text (so no
CC-BY change notice is triggered). `SOURCE_NOTICES.md` carries the attributions (Austin et al. 2021; Chen et al. 2021),
llama.cpp (MIT) and the Python dependencies with their licences. A check asserts that every path named in any tracked
mapping or manifest exists in the git tree.

### 3.2 Prospective exclusions (all blind to every model output; the list with reasons is frozen in `roster.json`)

**Rule:** a task is excluded if any outcome of it **on the trial serving stack** exists before the freeze. Pilot
outcomes on the MLX stack do **not** exclude a task; they are disclosed (3.5) and are not used as covariates, because
the stratification of v2 configuration A is withdrawn with configuration A.

1. The six timing-pilot tasks `mbpp_full/39, 122, 522, 547, 869, 966` (the out-of-design smoke, calibration and
   rehearsal tasks, 5.8).
2. S2 problems whose normalized prompt duplicates an S1 task (normalization of
   `experiments/local_stream/timing_pilot.py:35-36`); the S1 version is kept.
3. S2 problems whose entry point cannot be resolved by `mbpp_entry_point`
   (`experiments/local_stream/data.py:35-44`).
4. Any task whose reference solution does not pass `verify()` twice in a row inside the Seatbelt sandbox on the trial
   machine **under the load regime of the trial** (a 1,024-token generation running on the coder server during the
   sweep), or whose reference verification takes more than half of the 5 s verifier wall limit in either run. No model
   output about the task is involved.
5. **Nothing else.** No task is excluded for difficulty, length, or any model output, before or during the program.

### 3.3 Roster rule and horizon arithmetic (evaluated once, before the freeze)

If the S2 download verifies, the roster is **EXT** = S1 + every surviving S2 task; otherwise the roster is **S1**.
**No rule parameter depends on the roster**: `delta`, `alpha`, `rho`, `n_min` and the hierarchy are identical on EXT
and on S1.

| quantity | value |
|---|---|
| S1 tasks | 427 (MBPP sanitized) + 164 (HumanEval) = **591** -> `floor(591 / 2)` = 295 pairs, 1 unpaired leftover |
| S2 candidate tasks | 974 - 427 = 547 MBPP-full-only problems |
| S2 after excluding the six smoke tasks | 541 |
| S2 after rules 2-4 of 3.2 | `n_S2 <= 541`, pinned in the pre-freeze phase |
| **Horizon `N_P`** | **`floor(n_S1 / 2) + floor(n_S2 / 2)`** = `295 + floor(n_S2 / 2)` pairs, **at most 565** after the smoke exclusions and **at most 568** before any exclusion (`floor(591/2) + floor(547/2) = 295 + 273`). Roster S1: `N_P = 295`. |
| unpaired leftovers | **one per stratum**, never enrolled, executed only in a follow-up cohort |

**`N_P` is never `n_total // 2`.** Pairs are formed inside a stratum (3.4), so the odd remainder of each stratum is a
leftover and **no pair ever crosses the strata**. The number 569 that appears in earlier notes came from the
unstratified count `1138 // 2` and is **not** a horizon of this program; it survives only as a reference row in the
radius table of 1.3.

`N_P` is the number of pairs in the frozen `arrival_order_T<e>.json` and is the authoritative value.
**There is no extension, no second pass and no re-randomization of unused tasks**, whatever the monitoring shows.

### 3.4 Arrival-order generation (seeded and hash-committed; it is not the assignment mechanism)

For trial number `e` (T1 = 1, T2 = 2, T3 = 3, T4 = 4) and the two source strata:

```python
rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([60260919, e])))
pairs, leftovers = [], []
for stratum in ["S1", "S2"]:                 # S2 absent on roster S1
    uids = sorted(roster[stratum])                            # bytewise order of uid strings
    u = [uids[j] for j in rng.permutation(len(uids))]
    pairs += [(stratum, u[2*m], u[2*m + 1]) for m in range(len(u) // 2)]
    leftovers += u[2 * (len(u) // 2):]
enrollment = [pairs[j] for j in rng.permutation(len(pairs))]  # random interleaving of whole pairs
```

Pair `i` (1-based) = `enrollment[i-1]`; its position 1 is arrival `2i-1`, its position 2 is arrival `2i`. Pairs are
formed **inside a stratum** (`paper/main.tex:171-172`, "disjoint pairs of arrivals within a prespecified stratum";
`paper/theory.tex:238-245`). **Every pair's two uids share a stratum; there is no mixed pair, and the odd remainder of
each stratum is a leftover** - a pair across the strata would be the one pair whose two positions have systematically
different difficulty (3.5 item 6 expects S2 success far below S1's 0.73), and `thm:pair_id` is invoked at 4.1 through
the *stratified* statement. Leftover tasks receive the arrival numbers after `2 * N_P` in list order; they are never
randomized and are executed only in a follow-up cohort. The file `arrival_order_T<e>.json` (pairs, strata, uids,
leftovers, `N_P`) is authoritative; its SHA-256 is in the freeze bundle. **It contains no arm, no coin and nothing
from which a coin can be computed.**

**Both positions of a pair are fixed before the orientation is randomized**, which is the condition of
`paper/theory.tex:179-190`. Pairs are never formed by completion order and never by searching for favourable or
opposite-arm outcomes (guidance item 1).

### 3.5 Tasks used in the pilot are kept: the reason, without euphemism

1. Validity of every guarantee in section 8 rests on the scores being **adapted, bounded and produced by a frozen
   rule**, and the causal reading rests on **fresh coins**. Neither rests on task novelty. The pilot influences the
   trials only through the design choices listed in 1.1, which are frozen and disclosed.
2. **The reason for keeping the 591 pilot tasks while excluding the six smoke tasks is the rule of 3.2, and the reason
   that rule was chosen is sample size:** holding out every pilot task would leave at most 270 S2 pairs, which is below
   `n_min` plus any useful horizon. **This is a power argument and is printed as one**, not as a methodological claim.
3. **Outcome knowledge inside the program is real and is not denied.** T4 executes `single_shot` on the new stack on
   every paired task; T2's follow-up cohort adds more. Before T1 starts, the operator can therefore hold new-stack
   outcomes of T1's candidate for essentially every task and a sample of T1's incumbent. The defence is **not
   ignorance**; it is the program freeze (14.1): nothing that defines any trial can change after the first design-task
   outcome of the program, every trial is started unconditionally (14.6), and between trials only the plumbing
   inspection list is produced (14.6).
4. The claims are about **this laboratory stream** (1.4), not about fresh tasks. Public-benchmark exposure of the models
   is disclosed and no contamination-free claim is made.
5. A task is executed at most once per trial and up to four times in the program. "Each trial uses the roster once" is
   true only of the paired arrivals up to the decision plus the follow-up cohort; under `ABSTAIN_AT_HORIZON` the
   unpaired leftovers are not executed. `N` in every claim is the computed count of executed arrivals.
   **The four trials are not independent replicates and are never pooled or described as such.**
6. **Dilution, disclosed.** The only observations on S2-type tasks (timing pilot: 1 of 6 and 2 of 6 successes) suggest
   a success rate far below S1's 0.73. On a roster where many tasks are failed by both arms, joint failures add pairs
   with `D_i = 0` and `Z_i = 0`, which shrinks `|Dbar_n|` toward 0 and makes an **absolute**-margin success statement
   easier while making the hierarchy net benefit smaller in magnitude. Both effects are reported: the expected
   roster-level success rate is printed in every T1 and T3 caption, and the success statistic **restricted to S1 pairs**
   at the reported prefix is printed descriptively in the same sentence as every success statement.
7. **Timing-based exclusion, disclosed.** Rule 3.2 item 4 removes tasks whose **reference** solution does not verify
   twice in a row under the trial load, or whose reference verification takes more than half of the 5 s verifier wall
   limit. The excluded set is therefore exactly the set of tasks that execute slowly on this host under load. Because
   tier 1 decided 53.16% of pilot pairs, **the roster is pre-filtered on the dimension the cost tier mostly measures**.
   This does not threaten validity - the exclusion is in `F_0`, is fixed before the freeze and uses no model output -
   but it changes what `mubar_n` is about, and it is not denied: the number of tasks excluded by rule 4, and their
   reference verification times, are reported in the freeze bundle and **beside every cost-tier statement** (1.1).

---

## 4. Randomization

### 4.1 Unit and coin

**One fresh fair coin from OS entropy per PRE-ENROLLED pair** (guidance item 1; revision 1 C1). The only randomized
online design in the root's paper is the disjoint-pair orientation design (`paper/main.tex:171-177`;
`paper/theory.tex:179-236`, `thm:pair_id`): one coin `R_i` decides which **position** of pair `i` receives which
system, so every pair contains exactly one episode per arm and, with `q_i = 1/2`, the score `Z_i` is the observed
oriented kernel in {-1, 0, +1} with `V_n = n` (`eq:pair_ht`, `paper/theory.tex:200-206`; the bound
`|Z_i| <= 1/(2 eps)` with `eps = 1/2` gives `|Z_i| <= 1`).

**Independent fair coins for individual arrivals followed by retrospective matching are a different design and do not
implement this theorem** (guidance item 1). They produce pairs with two episodes of the same arm, for which neither
the paper nor `src/winstats.py` defines a score; R4 found they leave about 3% of arrivals unpaired, make the number of
pairs random, and cost 0.5 to 2 points of power. What the per-arrival intent requires is preserved: the coin is fresh,
comes from OS entropy, is logged before execution, is never redrawn, and each task is executed under one arm only.

**Definition.** For pair `i` with positions 1 and 2 (arrivals `2i-1`, `2i`): `R_i = 1` assigns the candidate to
position 1 and the incumbent to position 2; `R_i = 0` reverses. `P(R_i = 1) = 1/2`, known and `H_i`-measurable.

### 4.2 Code path (normative) and invariants

```python
# pair i is PRE-ENROLLED first: positions, stratum and task uids are fixed and durably logged
eventlog.append("pair_enrolled", {"pair": i, "stratum": s, "arrivals": [2*i-1, 2*i],
                                  "task_uids": [u1, u2], "phase": "RANDOMIZED"}, durable=True)
raw = os.urandom(8)                 # macOS kernel CSPRNG; the only source of assignment randomness
bit = raw[0] & 1                    # R_i
eventlog.append("coin_drawn", {"pair": i, "raw_hex": raw.hex(), "bit": bit,
                               "assignment": {...}}, durable=True)
# durable=True returns only after fcntl(fd, F_FULLFSYNC) succeeded.
# Only after that return may EITHER job of pair i be sent to a worker.
```

**All eight drawn bytes are logged** as `raw_hex` (16 lowercase hex characters, event schema T10). They cost nothing,
they are strictly more evidence than the bit alone, and R2 checklist item 6 is therefore **met** rather than argued
(13.1). Logging them proves nothing about the entropy source - that limit is 4.3, not this line.

**Invariants, enforced by the orchestrator and re-checked by the log verifier.**

(i) at most one chain-valid `coin_drawn` per pair;
(ii) `coin_drawn` for pair `i` appears **after** its own `pair_enrolled` and after both `episode_revealed` events of
pair `i-1` and after the reveal-triggered evaluation at prefix `i-1`;
(iii) every `episode_started` of the randomized phase points to the earlier `coin_drawn` of its pair;
(iv) no `coin_drawn` after a `decision`, and none before the chained external receipt of the trial-start anchor (12.4);
(v) **a coin is never redrawn: every chain-valid `coin_drawn` line present in the file is binding on resume, whether
or not its fsync had returned.** A coin is void only if its line fails chain verification. (A process kill between
`os.write` and the return of the fsync leaves a complete, readable line; treating it as void would be a redraw.)
(vi) no other randomness influences the assignment: a unit test monkeypatches `os.urandom` and checks that arms follow
the patched stream exactly;
(vii) the coin of pair `i` does not physically exist while pair `i-1` is running (5.1), so no record can depend on a
later coin.

### 4.3 What the coin proves, and what it does not

| option | what it would prove | status |
|---|---|---|
| (a) tape of coins drawn in advance and hash-committed | coins fixed before outcomes | **Rejected.** The whole orientation sequence would exist before the first episode; this is the configuration the root criticised in the pilot (`reviews/round11_coding_target_scope.md:50`; counterexample in `reviews/round12_coding_correction_and_baseline_delta.md:41-49`). |
| (b) commit-reveal key | same as (a), hidden | **Rejected** for the same reason: future coins exist in harness memory. |
| (c) public randomness beacon | that the operator did not choose the coin value | **Not adopted** (revision 1 C18). A beacon removes reliance on the operator **only if** each enrollment is externally timestamped before its beacon round is published, i.e. one blocking external receipt per pair (up to `N_P` <= 568 per trial). Without that the operator can still choose when to enroll. |
| (d) live OS entropy, write-ahead logged, hash-chained, externally receipted | see below | **Chosen.** |

**What (d) proves and what it does not.** The hash chain is an unkeyed SHA-256 chain over a plaintext file: whoever
holds the file can replace any suffix and recompute every later hash, so **the chain alone proves nothing against the
operator**; all evidential weight sits on the external receipts of 12.4. Those prove that a log prefix with a given
head existed no later than a server time, and that every later event was produced after that receipt was issued.
**The coin is operator-attested and not independently verifiable**: no outsider can distinguish a genuine entropy
stream from a chosen one, and an operator who kills the process after reading a coin and before dispatch, deletes the
tail and restarts loses no measurable time. The protocol therefore

(i) states the assumption "**the operator does not act on coins**; collection, retry and amendment logic is arm-blind
in code and coin-independent" wherever the fair-coin reading is used;
(ii) makes such acts visible after the fact through the integrity-event table and the time-sandwich audit (12.6);
(iii) removes the cheapest steering devices: no re-run of any kind (5.6), drawn per-request seeds so that potential
outcomes are not rehearsable from the frozen bundle (5.5), blocking receipts at the irreversible points (12.4), and
the `job_accepted` rule of 6.4 row 11c that closes the "kill between coin and dispatch" gap (finding N4).

**Preflight self-test of the entropy plumbing:** 10,000 non-design coins, tagged `phase = SMOKE`, never used; the count
of ones must lie in [4,850, 5,150]; outside that range the preflight stops and the event is reported; there is no
silent repeat. **The test says nothing about the design coins.**

### 4.4 What is pseudorandom, and why that is harmless

Only the **arrival order** (3.4) is a deterministic function of frozen constants. It is not an assignment mechanism,
does not depend on any coin, and is in `F_0`. Per-request sampling seeds are drawn at request time (5.5) and are in no
`F_j` before their request.

### 4.5 Arm-blind in code, arm-dependent in effect

Dispatcher, client, retry, timeout, cap, resume and re-freeze logic are identical for both arms; the only arm-dependent
code is the lookup of the workflow name and server URL from the frozen arm table. **Identical code is not identical
effect**, and the report says so with the two mechanisms:

1. a failed call in `single_shot` leaves no candidate program (`success = 0` with certainty), while a failed tests or
   repair call in `self_test_repair` grades the pre-repair program (`agent.py:242-249`);
2. `self_test_repair` issues two to four calls and holds a slot about 4.5 times longer, so it is more exposed to every
   infrastructure event, to connection retries (each a fresh sample of a generation) and to interruption at a crash.

**Reported per trial and arm as primary reporting:** episodes with at least one failed or retried call; episodes whose
outcome was fixed by rows 1 to 3 of 6.4; successes that occurred after a retried try; interrupted, hard-capped and
`started_after_resume` episodes. Any operator intervention is a logged `operator_action` with a reason code.

---

## 5. Execution model

### 5.1 Pair-synchronous scheduling, workers and spools

**`W = 2` concurrent worker slots, and exactly one operating-system process per episode**
(`subprocess.Popen([python, lab_worker.py, --job <job file>])`, single-threaded because `sandbox.py` uses
`Popen(preexec_fn=...)`, own HTTP session, no pipe). The job file is written and fsynced before the process is
spawned. **There is no long-lived worker and no duplex pipe**: the fsynced spool is the only channel from an episode
to the orchestrator, which is what makes crash isolation, resume and orphan recovery a question of "which spool lines
exist" instead of pipe-state reasoning (this closes `PROTOCOL-GAP PG-6`). **The orchestrator is the only writer of the
event chain.** `worker_index` in {0, 1} is the **slot** the episode runs in, carried in the job file: in the
randomized phase position 1 always runs in slot 0 and position 2 in slot 1 (5.5, 7.4); in the follow-up cohort it is
the index of the free slot.

Each episode owns an **append-only, fsynced spool file** `spools/ep_<arrival>_<attempt>.jsonl` and writes, in order:

| spool line | becomes the chain event | when | why |
|---|---|---|---|
| `job_accepted` (arrival, arm, worker pid, invocation id, monotonic stamp) | `job_accepted` | fsynced **before** `run_episode` is entered | this line, and only this line, defines "**the attempt started**" (finding N4) |
| `call_started` (drawn seed, body hash, `t_c1`, `t_send`) | `llm_request` | fsynced **before** the POST | |
| `call_response` / `call_error` | `llm_response` / `llm_error` | fsynced **before** the response is used | |
| `sandbox_exec` (purpose, lock wait, seconds) | (not a chain event; folded into `episode_revealed`) | after each sandboxed execution | |
| `episode_final` (record hash, outcome vector) | `episode_revealed` | after the record file is fsynced | |
| `worker_error` (stage, error digest) | worker death, 6.4 row 10 | on a failure **outside** `run_episode` | |

The orchestrator ingests the spools and turns their lines into chain events; **a worker process never blocks on the
orchestrator**, so orchestrator load cannot enter `latency_s` (the spool fsync time can: it is logged per call and
reported per arm). If the orchestrator dies, the worker process is unaffected: it finishes its episode to its frozen
end, completes its spool and exits. On resume the orchestrator first waits for surviving worker processes of the
previous invocation (up to the remaining hard cap) and then ingests the unlogged spool remainder with
`recovered: true`.

**Randomized phase, pair-synchronous.** For `i = 1, 2, ..., N_P`:

1. **pre-enroll** pair `i` (`pair_enrolled`, durable): positions, stratum, task uids fixed;
2. draw and durably log `R_i` (4.2);
3. send position 1 to worker 0 and position 2 to worker 1, in that order, without waiting in between;
4. both episodes run concurrently against the server(s); each is revealed when its `episode_final` line has been
   ingested (after hidden-test verification), and each reveal **updates the existing enrollment-indexed record of pair
   `i`** and triggers an evaluation of the rule (8.3). Every ingested call line of a **pending** episode that raises
   that episode's certified elapsed time `ell` is also an evaluation trigger (8.3), because it can narrow the pair's
   hierarchy enclosure through the cost certificate of 7.5 item 5;
5. pair `i+1` is pre-enrolled only after both episodes of pair `i` are revealed, the `/metrics` scrape of the pair
   boundary is logged or timed out (13.1), and the evaluation at the prefix containing pair `i` has been made.

There is no arrival clock (closed loop). Queue wait (enqueue to dispatch) is recorded per arrival.

**Why pair-synchronous.** With a sliding window on one GPU, the final record of pair `i-1` (its wall-clock latency,
possibly a load-induced timeout) can depend on the coin of pair `i`, because a `self_test_repair` neighbour occupies
the second slot about 4.5 times longer than a `single_shot` neighbour. The filtration `F_{i-1}` contains that final
record, so conditioning on it would be informative about `R_i`; this is the warning of `paper/asynchronous.tex:72-76`
and the guidance's "Shared serving contention or adaptive schedulers do not disappear merely because assignment coins
are fair". Under the pair-synchronous rule **`R_i` does not exist while pair `i-1` runs**, so cross-pair interference
through the coin is excluded **physically**, not by assumption.

**The price is stated plainly:** at most one pair is ever unresolved, reveal order and arrival order differ only by a
swap inside a pair, and the enclosure content of the rule is bounded by the remaining duration of one episode.
**What is not claimed: a study of monitoring under delay** (1.1, 1.5 item 18).

**Follow-up cohort, work-conserving.** After a decision the remaining arrivals of the frozen order are taken one at a
time by whichever worker is free; both run the decided arm. The two phases use different schedulers, so **nothing is
compared across them** (1.5 item 10).

### 5.2 The fixed scheduling and resource policy, and the concurrent-load record

Guidance item 2 requires the scheduling and resource policy to be fixed and all concurrent load to be logged.

**Fixed policy, non-amendable (14.3).** Exactly two workers; `-np 2` server slots so no request queues for a slot;
one host-wide execution lock so at most one generated program runs at any instant (5.7); pair-synchronous dispatch in
the randomized phase and work-conserving dispatch in the follow-up cohort; both T3 servers resident for the whole
trial; `caffeinate` on and mains power required; no other GPU job — **required of the operator and checked, within the
stated limits of 5.7.1, by the host quiescence gate; the exclusive lock file and the preflight port scan exclude only a
second instance of this harness and see no other project's model server**; the harness refuses to attach to a server it
did not start.

**Isolation, as far as this host allows, stated honestly.** The two arms of a pair deliberately share one GPU and one
server process: that is the regime the estimand refers to (7.4). What is isolated is everything the protocol can
isolate: slots (one per worker), program execution (the lock), and other jobs (exclusivity). macOS enforces no memory
cap; this is disclosed, `W` stays at 2, RSS is sampled, and the config key is literally named
`mem_bytes_requested_not_enforced_on_macos`.

**Concurrent-load record, logged per episode and reported per arm:**
partner arrival id, partner arm, partner workflow, **overlap seconds** with the partner episode, the partner's state at
this episode's verification, `id_slot`, per-call `predicted_per_second`, `sandbox_lock_wait_s` per execution, queue
wait, server `slots busy` samples, RSS samples, and, for T3, which model the partner was using. Every resource table
prints "measured under pair-synchronous two-worker load on this host".

### 5.3 Server supervision

Configuration as in 2.2, identical for the whole trial. A supervisor polls `/health` every 5 s; on process exit or
3 consecutive failures it logs `server_down`, re-verifies the serving manifest and the GGUF hash, restarts with the
identical argv, logs `server_restarted`, and compares the **full** `/props` object with the golden object (difference:
`trial_aborted(server_identity)`, 6.4 row 6). At the **first** start the same comparison is made against the golden
object of the freeze bundle. The smoke completion after every start or restart is tagged `phase = SERVER_SMOKE` and
enters the reconciliation identity of 13.1. `/metrics` scrape points: 13.1.

### 5.4 Sampling parameters

Every request body contains exactly: `model` (alias), `messages`, `temperature: 0.7`, `top_p: 0.95`, `top_k: 0`,
`min_p: 0.0`, `typical_p: 1.0`, `repeat_penalty: 1.0`, `presence_penalty: 0.0`, `frequency_penalty: 0.0`,
`mirostat: 0`, `max_tokens: 1024`, `seed` (5.5), `cache_prompt: false`, `stream: false`, `verbose: true`.

Temperature, top_p and the completion cap are the pilot's values; `top_k: 0` and `min_p: 0.0` disable samplers the MLX
pilot did not have. Samplers that are **not sent** (DRY, XTC, top-n-sigma, dynamic temperature, sampler order, and any
other sampler-affecting key of `generation_settings` at the pinned commit) are covered by the golden receipt object of
13.2: the pre-freeze derivation file lists every sampler-affecting key with the value that makes it a no-op, and
preflight fails if the golden object deviates. **Both arms and both models use the same values.** Truncation
(`finish_reason == "length"`) is counted per request and is not an error. Statements about what is sent are generated
from a captured request of the frozen harness. **Requests are seeded but regeneration is not bit-identical**
(continuous batching); no bit-reproducibility is claimed.

### 5.5 Per-request seeds

The pilot's seed formula collided across units. Index-determined seeds would be unique but would make every potential
outcome rehearsable by anyone holding the frozen bundle, which multiplies the value of an unverifiable coin and buys
nothing, because bit-reproducibility is not claimed. Therefore, for every try of every request:

```python
seed = (int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFE) | worker_index   # worker_index in {0, 1}
```

**The low bit carries the worker index** (finding N6), which partitions the space between the two uncoordinated
workers and makes a cross-worker collision impossible. `worker_index` is the **slot** of 5.1 (0 for position 1, 1 for
position 2 in the randomized phase; the free slot in the follow-up cohort); it is carried in the job file, it is
**not** a function of the arm, and it is removed from the canonical job payload before the T4 byte-identity check
(12.3), so the partition can never give one arm an advantage. Each worker loads the used-seed set of earlier trials of
the program at start and checks only its own half; a value already used is redrawn; `0xFFFFFFFF` is never used. The seed is
written to the worker spool and to `llm_request` **before** the POST, and the seed receipted by the server must equal
the seed sent (13.2). Seeds are drawn by the worker **independently of the coin** (the worker knows its arm but the
seed draw does not read it; a unit test asserts the drawn stream is independent of a patched coin stream); they are
part of an episode's internal randomness (7.2). The seed that `run_episode` computes internally is ignored by the
injected client. **A detected duplicate is a logged defect (`seed_collision`) with no effect on any outcome**; it never
invalidates a trial, because seeds are not part of any guarantee.

### 5.6 Timeouts, retries, caps; `max_attempts = 1`

Every row is non-amendable (14.3).

| parameter | value | note |
|---|---|---|
| `request_timeout_s` | `max(180, 30 * ceil(4 * c_max / 30))`, where `c_max` is the slowest call of the out-of-design calibration (5.8) | identical for both arms |
| `max_connection_retries` | 2 (three tries), backoff `min(2 * (k + 1), 10)` s, only for connection errors and timeouts | HTTP 4xx/5xx and malformed bodies are not retried. A retried try is a **fresh sample** (new drawn seed) of a generation that may have been slow because of its own content; retries are part of the system definition of both arms and are reported by arm |
| `server_recovery_s` | 180 | how long a try may wait for a supervised restart |
| `max_recovery_waits_per_call` | **1** | a call may wait for at most one supervised restart; a second `server_down` inside the same call fails the call by row 1 (finding N15) |
| `sandbox_timeout_s`, `sandbox_cpu_s` | 10, 10 | pilot values |
| `sandbox_output_cap_bytes` | 65,536 | pilot value |
| `max_repair_rounds` | 2 | pilot value |
| `max_lock_wait_s` | 120 per execution | a longer wait fails that execution as a sandbox kill (row 7) and is logged |
| `episode_hard_cap_s` | `4 * (3 * request_timeout_s + server_recovery_s + 6) + 3 * (sandbox_timeout_s + max_lock_wait_s) + 60` (**= 3,354 s** at `request_timeout_s = 180`: `4 * (540 + 180 + 6) = 2904`, `3 * (10 + 120) = 390`, `+ 60`). **The value is computed by the harness from this formula and the pinned `request_timeout_s`; it is never typed into `config.json` by hand**, and the freeze test of Appendix C compares the stored value with the formula's output, not with a literal | **derived from the corrected worst case** (finding N15): four calls, each with three tries, **one** recovery wait and its backoffs, plus three self-test executions each with its bounded lock wait. Exceeding the cap is a **terminal endpoint**: `success = 0`, `error_class = episode_timeout`, `latency_s = episode_hard_cap_s`. The wording in every report is "**the cap can bind on a legitimate `self_test_repair` attempt only after at least four failed tries and one server restart; how often it bound is reported by arm**" - never "by construction it cannot bind". |
| `max_attempts` | **1** | there is no re-run of any kind (6.4) |

A returned episode is never re-run, and an attempt that does not return is not re-run either: it is revealed as a
failure endpoint (6.4 rows 10, 11). Request timeout, episode timeout and verifier timeout are **three separate outcome
fields**. Every try of every request is logged with its usage or with `usage_known: false` (13.1).

### 5.7 Sandbox under two workers: the host-wide execution lock

`experiments/local_stream/sandbox.py` is unchanged: macOS Seatbelt profile, fresh temporary directory per execution,
process-group kill, CPU and wall limits, output cap. Its containment was audited for **one program at a time**; the
profile is allow-default with one writable directory shared by every run on the host, and during a verification that
directory holds the hidden tests and the nonce sentinel in clear text. Two concurrent workers would let a generated
program of one worker list, read or overwrite the other worker's verification program, and byte-identity of
`sandbox.py` does not restore the audited property. v3 restores it by construction:

1. **Host-wide execution lock.** Each worker wraps `sandbox.run_program` **before** `agent` and `verify` are imported
   (a unit test asserts every call path goes through the wrapper) in an exclusive `flock` on one lock file. At most one
   generated program exists and runs at any instant, exactly as in the audited regime. `agent.py:32` and `verify.py:21`
   both use `from sandbox import run_program`, and `run_program` creates and removes its `p_*` directory inside the
   call (`sandbox.py:154-190`), so wrapping `sandbox.run_program` before those imports puts creation, execution and
   deletion under the lock. Lock waiting time is logged per execution (`sandbox_lock_wait_s`); for the agent's own
   tests it lies **inside** `latency_s` and is part of the side-by-side regime; hidden-test verification is outside
   `latency_s` as in the pilot. A side effect: no verification ever competes for CPU with the partner's sandboxed
   program.
2. `TMPDIR` is set to the neutral path carried in `config.json` as the token **`<TMP>/labsbx`**, which on this host
   resolves to `/private/tmp/labsbx` (recreated at start; that literal string is the one path allowlisted by exact
   string in the scanner of 15.2, and it is the only place in this protocol where it is written out). This changes the profile text, so
   the audited profile hash does not carry over: the profile hash resulting from the trial's `TMPDIR` is recorded in
   the freeze bundle and per episode. The profile text contains the home path and never enters a tracked artifact.
3. **Containment probe before the freeze, on the trial host, with two workers running:** a probe program in one worker
   tries to list, read and write the other worker's run directory, the event chain, `records/`, the spools, the task
   file and the server log; every result is recorded in the freeze bundle; **any success of the probe other than those
   the audited profile already allowed for a single worker stops the freeze.**

Success = hidden checks exit 0 **and** the per-call nonce sentinel is seen (`verify.py:78-82`). Verifier wall seconds
and CPU seconds are both logged.

#### 5.7.1 Host quiescence: what the gate proves, and what it does not

The execution lock of item 1 excludes a second instance of **this harness**. It does not see a model server belonging
to a different project on the same machine, and on 2026-09-19 two such `llama-server` processes held this host's GPU
for 8 h 34 m while the harness believed the host was exclusive. That gap is not cosmetic: the frozen hierarchy is
success > cost with `cost = latency_s`, the two arms tie on success in the pilot, so nearly the whole composite effect
rides on the latency tier and a foreign accelerator load silently corrupts the primary endpoint.

`experiments/live_ab/lab_hostcheck.py` is therefore run as a **hard gate before a trial may open its chain** and as an
**observing check at the trial-start and quiescent scrape points**. It reads `ps` and `lsof` and nothing else. It
**observes only**: it never terminates, suspends or reprioritises any process it finds, and the operator decides what
to do about an offender. A refusal is written to the program chain as `host_quiescence_refused` beside
`preflight_refused(host_not_quiescent)`; every in-trial scan is written to the trial chain as `foreign_load_detected`
whether or not anything was found, so that a reader can see positively that the host was scanned and what was seen.
Findings carry the detector label, the pid, the age, the resident size and the SHA-256 of the offending `argv`; the
command text and the token summary derived from it are **not** published, because that summary's vocabulary is closed
for paths and addresses but not for bare literals, and a foreign project's module or model name could otherwise enter
an immutable chain.

**A scan reports a foreign accelerator consumer when, and only when, one of these holds.**

1. The command names a known runner by exact token (`llama-server`, `llama-cli`, `mlx_lm`, `ollama`, `vllm` and
   spelling variants), including behind a wrapper shell.
2. The process is a python interpreter, at any size, and holds **any** open Metal resource.
3. The process is at or above `PROBE_RSS_FLOOR_BYTES` (128 MiB) and holds a **compute-class** Metal resource: the ggml
   Metal backend, Metal Performance Shaders, or MLX.

Rule 3 is what defeats a **rename**: copying `llama-server` to another name does not change which Metal libraries the
process opens. It is deliberately narrower than rule 2, because a bare display-class marker is mapped by any
window-drawing application as well — measured on the serving host, two ordinary desktop applications map `AGXMetal`
while doing no accelerator work — and a gate that reports a text editor is a gate an operator learns to bypass.

**What this gate does NOT detect, stated so that no sentence of this protocol claims more than it delivers.**

- An accelerator job whose resident size is **below 128 MiB** and whose command matches no runner name. It is not
  probed at all and the scan reports the host clean.
- A job that drives the GPU through **raw Metal only**, linking neither ggml, MPS nor MLX. By open files alone such a
  process is indistinguishable from a window-drawing application.
- Anything on a host whose process table or Metal probe could not be read. That case is never silence: it is recorded
  as a `degraded` cause and **the preflight refuses**, because an unprovable host is not a clean host. A scan that
  fails open would be worse than no scan at all, since it would produce a clean-looking audit trail over contaminated
  numbers.

Accordingly, **"no other GPU job" is a requirement of this protocol and an operator responsibility; it is checked, not
enforced, and checked only to the extent set out above.** Any report of a trial states that the gate ran, and states
these limits with it.

### 5.8 Pre-freeze out-of-design phase

Tasks: the six timing-pilot tasks of 3.2 and four hand-written prompts stored in the config; **never a design task**.
All of it is written to a separate chain under `results/live_ab/_prefreeze/` with `phase` in
{`SMOKE`, `TIMING_PILOT`, `SERVER_SMOKE`, `REHEARSAL`} and its own genesis; the chain is closed by a `prefreeze_closed`
event whose head, byte length and file hash enter the freeze bundle, together with a **derivation file** showing every
value of Appendix A next to the rule and the recorded inputs that produced it. Its tokens are reported separately and
excluded from every trial total. **Success outcomes of these runs are never used for any design choice**; the
quantities used are durations, memory, receipt equality, template facts and the yes/no extractability of a code block.

1. **Serving build and manifest** (2.2), then the receipt smoke test and golden-object capture per server; the template
   rule and the format-conformance rule of 2.4 for both models.
2. **Counter-semantics test on the production path** (finding N14): start a 1,024-token generation over a
   **non-streamed** POST with a short client timeout, let the client time out, scrape `/metrics` before and after, and
   record whether and how many prompt and predicted tokens of the abandoned task are counted. A streamed probe is run
   **in addition**, only to learn how many tokens had been generated at the cut. The non-streamed result fixes the
   accounting wording of 13.1.
3. **Calibration of call durations** at concurrency 1 and 2 for both workflows and both models. **Fixed plan**
   (finding N21): 5 repetitions x 6 smoke tasks x 2 workflows x 2 models x 2 concurrency levels = **240 episodes**
   (a `self_test_repair` episode is 2 to 4 calls, so the number of calls is larger and is recorded); **`c_max` is the
   maximum single-call duration over that fixed sample**; the plan is frozen before the calibration runs and the
   operator has no choice in its size. Sets `request_timeout_s` and hence `episode_hard_cap_s`
   by the rules of 5.6; checks memory.
4. **Side-by-side calibration of every contrast, not only T3.** For **each** of the four contrasts, the latency of
   each arm on the out-of-design prompts (i) when run **solo** and (ii) when run **beside the other arm of that
   contrast**, exactly as a pair runs. The **compression statistic** is defined (finding N21) as
   `C = (median side-by-side latency ratio candidate/incumbent) / (median solo latency ratio candidate/incumbent)`
   over the 6 smoke tasks x 5 repetitions; **one `C` per contrast** is frozen into that contrast's estimand text in
   6.2 and printed in section 16 item 6 and in the Appendix E template of that trial. The reason it is not a T3-only
   quantity: in T1/T2 the pilot mean latency ratio is 4.456, so the `single_shot` arm is contended for about 100% of
   its duration and the `self_test_repair` arm for about 22% of its - a **larger** within-pair duration asymmetry than
   T3's, in the tier that decided 53.16% of pilot pairs.
5. **Reference sweep** (3.2 item 4) and **containment probe** (5.7).
6. **Real-server dress rehearsal on out-of-design tasks only** (finding N8), tagged `phase = REHEARSAL`, chained under
   `_prefreeze`: the **full production path** - orchestrator, pair-synchronous scheduler, program chain, both workflows
   in both orientations, **both models**, spools, execution lock, per-pair `/metrics` scrapes, live monitor and
   reference rule, real anchors on a drill branch, the verifier and one builder run - under a rehearsal-only config
   with a small `n_min` and a wide margin so that a **decision**, its blocking receipt, the **switch** and a
   post-switch phase all occur. Injected faults, each at least once: one orchestrator kill, one worker kill, one forced
   server kill with supervised restart, one forced pause and resume. **Freeze conditions:** verifier PASS, builder run
   without error, and **the frozen receipt comparison (golden object, mask list, `cache_n`, alias, seed) passes on
   100% of the responses of the rehearsal** (finding N7), which must include complete `self_test_repair` episodes with
   repair rounds on both slots and two consecutive episodes with an identical prefix on the same slot. Any failure
   means no freeze. Rehearsal success outcomes are never used and never reported as observations (1.5 item 17).
7. **Anchor drill against the real remote** on a drill branch and the real issue thread (12.4).
8. Downloads: `mbpp.jsonl` at the pinned revision and the two LICENSE files (revision 1, C9). **No weight download is
   needed** (revision 2 item 12).
---

## 6. Outcomes, the hierarchy, and the complete failure-to-outcome table

### 6.1 Episode endpoints

| field | definition |
|---|---|
| `success` in {0, 1} | archived verifier label: hidden checks exit 0 **and** sentinel seen. Verifier timeout, missing sentinel, empty or unextractable code, and every failure path of 6.4 give 0. It is **not** semantic correctness and **not** an independent re-adjudication. |
| `latency_s` (the **cost** unit) | as in `agent.py:247`: wall time (`perf_counter`) from the start of `run_episode` to the existence of the final candidate program. **Includes** all model calls, connection retries (each a fresh sample), backoff, waiting for one supervised server restart, the agent's own test executions **including their wait for the execution lock**, and the spool fsyncs. **Excludes** hidden-test verification and model loading. For a hard-capped attempt it is the cap; for an attempt that ended without returning (rows 10, 11) it is the certified elapsed time of 7.5; **when no request was ever spooled it is `0.0`** (finding N5). In every table the field is named `latency_s_w2sync` ("episode wall-clock cost under pair-synchronous two-worker load on this host") and is **never** pooled with the pilot's sequential `latency_s` nor with follow-up-cohort latencies. |
| `completion_tokens` | sum of server-reported completion tokens over all responses of the arrival; requests without a response contribute nothing and are listed under unknown usage (13.1). **Recorded, not scored** - it is not a tier (see 6.2). When no request was ever spooled it is `0` with `usage_known: false`. |
| recorded, not scored | prompt tokens; number of model calls; failed calls; retried tries; self-test executions (`n_self_test_executions`) and verifier executions (`n_verifier_executions`) as separate fields; repair rounds; `finish_reason` per request; truncation flag; verifier return code, sentinel flag, verifier wall and CPU seconds; **three separate timeout fields** (`request_timeout_any`, `episode_timeout`, `verifier_timeout`); `error_class`; `infra_flag`; queue wait; `sandbox_lock_wait_s`; the concurrent-load record of 5.2; SHA-256 of `final_code` and of the verification program without the nonce line; the static flags of the sandbox (`hack_flags`, `sandbox_flag`); `started_after_resume`; `recovered_orphan`. |

**All values are finite by construction** (6.4 maps every failure mode to a finite endpoint), as `winstats.compare`
requires (`src/winstats.py:34`: it raises on a non-finite outcome). The evaluation horizon of an episode is fixed: the
workflow runs to its own end under the caps of 5.6. Connection retries and their fresh samples are part of the
definition of both systems as evaluated here ("workflow under this client").

### 6.2 The hierarchy: success > cost

Guidance item 5. Two tiers, **identical for all four trials**:

| tier | field | direction | tolerance | eligibility |
|---|---|---|---|---|
| 0 | `success` | higher better | absolute 0, relative 0 | always |
| 1 | `cost` = `latency_s` (wall-clock seconds) | **lower better** | **relative 0.05**, absolute 0 | **only when both episodes succeeded** |

```python
tiers = [Tier('success'), Tier('cost', higher_better=False, relative_tolerance=.05)]
z, tier = compare(vals(candidate), vals(incumbent), tiers, eligible=[True, both_succeeded])
```

Rule of `winstats.compare` (`src/winstats.py:25-48`): for tier k, `tol = relative_tolerance * max(|a_k|, |b_k|)`; the
tier is decisive iff it is the first with `|a_k - b_k| > tol` (**strict**; exact threshold equality is a tie) and the
pair is eligible for it. **A joint failure is a tie** (`Z_i = 0`), because tier 0 ties and tier 1 is ineligible. The
kernel is never refitted; its code hash is in the freeze bundle and in every `monitor_update`.

**Why two tiers and why this cost unit, stated before any data.** The root's guidance writes the hierarchy as
`[Tier('success'), Tier('cost', higher_better=False, relative_tolerance=.05)]` and requires the cost unit and its
tolerance to be frozen. `completion_tokens` is dropped as a tier because (a) in the pilot it decided **0.30%** of
cross-task pairs, and (b) native token counts of two tokenizers are not a common cost unit, which had forced T3 to use
a different kernel from T1/T2/T4. Wall-clock seconds is the only resource notion common to two model families. The
frozen tolerance moves the planning value of the hierarchy net benefit from `+0.4968` (three tiers, tolerance 0.10) to
`+0.4993` (this hierarchy) - a change of 0.0025 (1.3).

**Named mechanism 1: the within-pair duration asymmetry, in every trial.** The two arms of a pair start together, but
in T1/T2 the `self_test_repair` episode lasts about **4.46x** longer (pilot mean; median per-task 4.911). The
`single_shot` episode is therefore contended by its partner for essentially **100%** of its duration while the
`self_test_repair` episode is contended for roughly the first **22%** of its. "Side by side" in 7.4 therefore does not
mean symmetric co-running for most of the slow arm's duration. Under a mild equal-slowdown model the faster episode is
slowed for all of its duration and the slower one only during the overlap, so **the frozen 5% tolerance corresponds to
a larger tolerance on the solo latency ratio**. Consequences, fixed now and applying to **all four trials**: the
measured side-by-side compression `C` of 5.8 item 4 is computed **per contrast** and printed in that trial's estimand
text, in section 16 item 6 and in the Appendix E template; the share of pairs decided at tier 1 is printed next to
every decision; and no statement about either arm's solo latency is permitted (1.5 item 8).

**Named mechanism 2: the host-wide execution lock transfers cost between the arms, one-directionally.** 5.7 puts
`sandbox_lock_wait_s` **inside** `latency_s` for the agent's own tests and **outside** `latency_s` for hidden-test
verification. In T1/T2 only `self_test_repair` runs self-tests, while its partner `single_shot` holds the same
host-wide lock for its **verification**, which is not in the partner's own cost. Up to `max_lock_wait_s = 120 s` per
execution and up to three executions per episode of one arm's grading time can therefore be charged to the other
arm's cost tier - **an arm-dependent effect of an arm-blind rule, in the tier that decides most pairs**. It is named
here rather than left as a logged field: `sandbox_lock_wait_s` is **reported by arm next to every cost-tier
statement**, a prespecified descriptive read-out **S-lock** (8.8 item 8) recomputes the hierarchy with
`sandbox_lock_wait_s` subtracted from `latency_s`, and 7.4 lists the transfer as part of what `mu_i` includes.
S-lock is descriptive: it never decides, and the primary analysis is the frozen hierarchy of the table above.

**T3 regime label, stated before any data.** T3's cost tier is wall-clock latency measured while the two models compete
for one GPU from two server processes. How the GPU is shared between two processes on this host is not documented;
under per-step alternation two episodes with equal token counts finish together whatever their solo speeds, and even
under a mild equal-slowdown model the faster episode is slowed for all of its duration and the slower one only during
the overlap, so the frozen 5% tolerance corresponds to a larger tolerance on the **solo** latency ratio. After a T3
decision the candidate never again runs beside the incumbent, so the live action is taken for a regime that then
disappears. Wall-clock latency is nevertheless kept, because a tier that cannot separate two families is a tie, which
costs power and not validity. Consequences, all fixed now: (i) T3's measured side-by-side compression `C` of 5.8
item 4 is printed in the T3 estimand text; (ii) every T3 composite statement and the T3 decision label itself carry
"**regime-specific: cost measured as latency under cross-process GPU sharing on this host**"; (iii) the share of pairs
decided at tier 1 is printed next to the decision; (iv) the success-only composite (8.8) is reported with equal
prominence; (v) 1.5 item 8 forbids any statement about solo latency.

**Pilot-expected shares of pairs decided at each tier** (planning values, MLX stack, cross-task pairs, this hierarchy):
tier 0 39.22%, tier 1 53.16%, ties 7.62% for T1 and T2; for T4 tier 0 + tier 1 = 90.21%, ties 9.79%. The realized
shares are reported per trial.

### 6.3 Pair scores

With `vals(r) = [success, latency_s]` and `both = success_candidate and success_incumbent`:

```python
z, tier = compare(vals(cand), vals(inc), tiers, [True, both])   # Z_i in {-1, 0, +1}; positive favours the candidate
d = int(success_cand) - int(success_inc)                        # D_i in {-1, 0, +1}
```

Both scores are bounded in `[-1, 1]` with balanced orientation, so `V_n = n` (`thm:normal_cs`,
`paper/theory.tex:303-304`: "For balanced pair scores in [-1,1], `V_n = n`").

### 6.4 Failure-to-outcome table: every mode, one outcome

**Principle** (`paper/theory.tex:555-563`): every arrival with a chain-valid assignment yields **exactly one revealed
outcome under that assignment, from exactly one attempt**. Failure to reach the outcome within the frozen horizon is an
**endpoint**, not an observation to discard or to redraw. All usage of every try is logged; unknown values are `null`
with a reason, **never 0 by default**. **Infrastructure loss is treated by this frozen outcome rule, never by deletion**
(guidance item 5).

| # | event | outcome rule | accounting |
|---|---|---|---|
| 1 | request timeout | connection retry per 5.6 (a fresh sample); after the last try the call raises; `run_episode` records the error and grades the last candidate that exists; `success = 0` if none | `llm_error` per try, `usage_known: false`; `/metrics` scraped before and after the failed try (13.1) |
| 2 | HTTP 4xx/5xx | not retried; same consequence as row 1 | `llm_error` with status |
| 3 | HTTP 200 without `usage` or `timings`, or non-JSON | treated as row 2 (`malformed`); **no token-estimation path exists** | `llm_error` |
| 4 | `finish_reason == "length"` or `truncated` | **not an error**; text used as is; `truncated_any` recorded | full usage known |
| 5 | server crash or hang | supervised restart with identical argv; the client waits up to `server_recovery_s`, **at most once per call** (5.6); waiting time is inside `latency_s`; if recovery fails, or a second `server_down` occurs in the same call, the call fails as row 1 | `server_down`, `server_restarted`; counters lost across a crash reported as an unreconciled window |
| 6 | restarted (or first-started) server differs from the golden `/props`, the serving manifest or the GGUF hash | **`trial_aborted(server_identity)`**; nothing further is dispatched; everything revealed so far stays reportable | blocking anchor |
| 7 | sandbox wall or CPU kill, fork refusal, permission error, or `max_lock_wait_s` exceeded | in a **self-test**: a failed self-test (which triggers repair, as in the pilot); in **verification**: `success = 0`, `verifier_timeout` recorded with the partner's state | execution seconds, `sandbox_lock_wait_s` |
| 8 | sentinel missing although exit code 0 | `success = 0` | `sentinel_seen: false` |
| 9 | empty or unextractable code | `success = 0` | record |
| 10 | worker process dies during an attempt, for any reason | **terminal:** the arrival is revealed with `success = 0`, `error_class = worker_died`, `latency_s` = certified elapsed time (7.5), tokens = known tokens; a new worker is spawned for later jobs; **the partner episode is not disturbed** | spool lines already written are ingested; unknown tail bounded per 13.1 |
| 10b | `episode_hard_cap_s` exceeded | **terminal:** worker killed; `success = 0`, `error_class = episode_timeout`, `latency_s` = cap | as row 10 |
| 11 | orchestrator crash or power loss, **attempt had started** (a fsynced `job_accepted` spool line exists) | resume per 14.5. An open attempt whose spool holds a complete terminal line passing the orphan checks is revealed from it (`recovered_orphan: true`); **every other started attempt is revealed as `success = 0`, `error_class = interrupted`**, `latency_s` = certified elapsed time. An already revealed episode keeps its outcome. **Nothing is re-run.** | `invocation_started.resumed`; integrity table (12.6) |
| **11c** | **crash after a chain-valid `coin_drawn`, attempt NOT started** (no `job_accepted` line for that arrival) - finding N4 | the arrival is **dispatched on resume as its one and only attempt**, flagged `started_after_resume: true`, with `partner_concurrent` recorded (true iff the partner is dispatched in the same window). **This is not a re-run**: nothing had run. The coin stays binding (4.2 invariant v). | the pair's solo/concurrent regime is recorded and enters the sensitivity read-out S-int |
| **11d** | crash between `coin_drawn` and **both** dispatches (neither arrival has `job_accepted`) | both arrivals are dispatched on resume, concurrently, as their one and only attempts, both `started_after_resume: true`, `partner_concurrent: true` | as row 11c |
| **11e** | crash after position 1 started and before position 2 was dispatched | position 1 follows row 11 (interrupted or recovered orphan); position 2 follows row 11c with `partner_concurrent: false` (it runs **solo**, which is a different load regime and is recorded as such) | both kill points are in the Appendix C resume test list |
| 11b | operator stop | a **graceful** stop **drains**: the in-flight pair finishes, is revealed and evaluated, then `trial_paused`. A pause exists only between pairs. Any other stop is a crash (row 11), is labelled `protocol_deviation` and is an integrity event. `operator_stop` is never an abort reason. | `operator_action` with harness-computed `what_was_known` |
| 12 | response receipt differs from the golden object, or `timings.cache_n != 0`, or `tokens_cached != 0` | the episode **completes and is revealed**; then `trial_aborted(receipt_mismatch)` before the next dispatch | `receipt_mismatch` list |
| 13 | served `model` alias differs from the arm's alias | as row 12 | |
| 14 | clock step or sleep (monotonic and wall clocks disagree beyond tolerance) | logged `clock_anomaly`; no outcome changes; the episode is `infra_flag`ged | 12.6 item 4 |
| 15 | disk full or log write error | **dispatch stops at once** (an unloggable coin may not be used); running episodes finish into their spools; resume per row 11 | pause reason `disk` |
| 16 | memory pressure | none beyond the sandbox kill; disclosed | RSS samples |
| 17 | **live-monitor exception, or an exception raised by the shadow reference rule of 8.9** | dispatch pauses (`trial_paused(monitor_exception)`); **no decision is taken by hand**; the only permitted repair is a harness-only re-freeze (14.4) that makes the live monitor equal the frozen reference rule; on resume the reference rule is replayed over every prefix and 8.9 decides the trial's result. **An exception in the reference rule itself is a defect of decision-defining code: row 24 applies and no re-freeze can repair it** | blocking anchor |
| **18** | **an attempt produced no spooled request at all** (worker died before its first POST) - finding N5 | `success = 0`, `error_class` as in rows 10/11, **`latency_s = 0.0`**, `completion_tokens = 0`, `usage_known: false`. All fields finite, so `compare` cannot raise. The pair's cost tier is ineligible anyway (the episode failed). | listed in the terminal-failure table by arm |
| **19** | **per-request seed already used** - finding N6 | the worker redraws from its own half of the seed space (5.5). A duplicate that nevertheless reaches the chain is logged as `seed_collision` and is **a reporting defect with no effect on any outcome, any score or any decision**; it never refuses, pauses or aborts a trial. | `seed_collision` count per trial |
| **20** | **`/metrics` scrape fails, hangs, or violates the start identity** - finding N9 | each scrape has a **5 s timeout and at most 3 tries**. On exhaustion the window is logged `unreconciled: true` and **enrollment continues**; a scrape never blocks a pair boundary beyond 15 s. A violated start identity (first scrape != that server's smoke completion usage) is a **`reconciliation_defect`**, logged and reported, **not** a refusal and **not** an abort. The exact token-level identity (BOS and template tokens) is established in the rehearsal of 5.8 item 6 and recorded in Appendix A; if it does not hold exactly, the frozen wording is "**residual reported**" and the residual is printed. | `metrics_scrape` with `ok`, `tries`, `unreconciled` |
| **21** | **preflight refusal** (weights hash mismatch, serving-manifest mismatch, port busy, API-key environment variable present, disk below 20 GiB, uncovered freeze-bundle drift, **worktree identity mismatch**) - finding N1 | **Before a trial's seq 0** (the trial chain may not exist yet): `preflight_refused(<reason>)` is written to the **program chain** (12.1) with harness-computed `what_was_known` and a blocking receipt; the trial does not start and is reported under its own heading as "not started: `<reason>`". **At a later invocation of an open trial**: the same closed reason list produces `invocation_refused(<reason>)` in the **trial chain** (event T3) and the invocation stops. **No outcome-dependent reason exists in either closed list.** | program chain / trial chain |
| **22a** | **plumbing verifier FAIL between trials, on a condition repairable by reporting code** - finding N2 | reason code **`plumbing_fail`**, closed machine-checkable condition list **A**: *receipt-mismatch count > 0, `reconciliation_defect` count > 0, or a completeness-check FAIL caused by the verifier's own bookkeeping*. Single action: the `plumbing_verdict(FAIL)` and **`program_paused(plumbing_fail)`** are written to the program chain; a harness-only re-freeze (14.4) of **reporting code only** may be performed; then the next trial starts. **A second `plumbing_fail` with the same condition id stops the program: later trials need a new protocol version.** | program chain, blocking anchor |
| **22b** | **plumbing verifier FAIL between trials, on a condition that implicates decision-defining code** | closed machine-checkable condition list **B**: *chain check FAIL, reference-rule disagreement, or T4 payload non-identity*. Single action: **row 24 applies to the affected trial; the program is paused (`program_paused(plumbing_fail)`); continuation requires a new protocol version.** | program chain, blocking anchor |
| | **common to 22a and 22b** | **A `plumbing_fail` may never be closed by changing anything in the 14.3 list**, and no re-freeze may touch decision-defining code (14.4 item 1). Results that do **not** stop the program, stated explicitly: the integrity label, terminal-failure counts, `seed_collision` counts, unreconciled windows, abstention, and any outcome whatever. | |
| **23** | **defect in reporting code (verifier or builder) discovered after outcomes exist** - finding N3 | permitted, through a **versioned erratum in the program chain**: old hash, new hash, diff hash, `what_was_known` = everything known at that moment; **both** outputs (old and new) are deposited; the list and definitions of the tables of section 16 cannot change; **no erratum can alter a decision**, because decisions come only from decision-defining code. | program chain, blocking anchor |
| **24** | **proven defect in decision-defining code (reference rule, coin, scoring path, failure rules, seed rule, config)** - finding N3 | **not repairable.** Claims 2 to 5 and 7 of 1.4 are **dropped for every affected trial**; a corrected rule may be computed and printed but is **descriptive only**; the affected trials are relabelled and are never repeated under their ids. | program chain, blocking anchor |
| **25** | **a trial chain cannot be opened at all** | nothing is re-run: the trial is closed by an externally receipted statement **in the program chain** and is reported as `trial_aborted(chain_unreadable)`. (This is the referent that v2's undefined "closing stub" lacked.) | program chain |
| **26** | a **blocking** receipt cannot be obtained within 30 minutes | `trial_paused(anchor_unavailable)`; this one pause is receipted together with its resume when the channel returns. `anchor_failed(tree_state)` on a blocking anchor maps to the same pause (finding N13). | 12.4 |
| **27** | **the working tree changed under a running invocation** (audit B7): at the periodic check every `worktree_check_s = 60` seconds, the SHA-256 of any freeze-bundle file, of any closed chain segment or of `src/winstats.py` differs from its bundle value, or the worktree path, `HEAD` branch or `HEAD` commit differs from the frozen one | **`trial_paused(worktree_drift)`** with the observed and expected digests; dispatch stops at once and running episodes finish into their spools; **resume only after the tree is restored and every digest matches**. A **changed or truncated closed chain segment** is `trial_aborted(chain_unreadable)` and is **never attributed to the operator in 12.6**: a drift detected by this rule is recorded as an environment event, not as evidence of editing. | program chain, blocking anchor |

**Consequences that are disclosed with every result.** Row 11 scores the episode still running at a crash as a failure,
and that episode is more often the **slow** arm (in T1 the incumbent, in T2 the candidate); row 10 can in practice be
reached only by a workflow that executes programs inside the episode (`self_test_repair`). Both are **arm-dependent
effects of arm-blind rules**. They are rare by expectation, every such event is an integrity event (12.6), the per-arm
table of 4.5 is **primary reporting**, and **three or more pairs containing a row 10, 10b or 11 episode label the trial
"integrity-qualified"** in every table and sentence that reports it.

**`infra_flag` is set by a closed machine list and by nothing else and nobody else:** any `llm_error` of any class in
the episode; any retried try; any overlap with a `server_down` interval or a restart wait; rows 10, 10b, 11, 11c, 11d,
11e, 18 (including a recovered orphan); any `clock_anomaly` overlapping the episode; rows 12 and 13.

**Primary analysis keeps every pair.** Prespecified descriptive sensitivity read-outs (10.3):
**(S-infra)** without pairs containing an `infra_flag` episode;
**(S-int)** with every pair containing a row 10, 10b, 11, 11c, 11d or 11e episode scored as a **tie in both scores**.
**Exception, stated because a tie is the wrong neutralization there:** for a pair whose only flag is
`started_after_resume` with `partner_concurrent: false` (row 11e, where position 2 runs **solo** and may succeed
faster than it would have under load), the pair is **additionally reported as scored**, so the reader sees both the
neutralized and the realized value.
**(S-lock)** the hierarchy recomputed with `sandbox_lock_wait_s` subtracted from `latency_s` (6.2, 8.8 item 8).
**Finding N17, frozen wording:** whenever any such episode lies at or before the reported prefix `tau`, the decision
sentence itself carries "*under S-int the rule also crossed at pair n / did not cross*", and Appendix E gets that
clause. This is the reporting answer to the fact that `max_attempts = 1` leaves a forced-failure device with a small
number of free uses; the device is disclosed, not denied.

**Aborts in the post-decision phase.** In the follow-up cohort an abort (rows 6, 12, 13, the ten-failure rule, or
row 27) **truncates the follow-up cohort only**: the logged `decision`, its prefix `tau` and claims 2 and 3 of 1.4
stand, the number of arrivals that did not run is reported (9.3), and no band, score or `n` changes, because the
follow-up cohort is outside all inference.

**Automatic, deterministic aborts (no discretion):** rows 6, 12, 13; and **ten consecutive revealed arrivals**
(counted in **reveal order**, finding N21) with `error_class` in {`episode_timeout`, `worker_died`, `interrupted`} or
with all tries of a call failed: `trial_aborted(infrastructure)`. **An abort can only remove decisions, never create
one**; every abort is reported with the band endpoints at the abort (14.6).

---

## 7. Pairing, the filtration, enrollment-indexed records, and enclosures

### 7.1 Pairing rule

Pairs are the consecutive arrivals `(2i-1, 2i)` of the frozen arrival order (3.4); **both positions are fixed and
durably logged before the orientation is randomized**. Nothing about a pair depends on reveal order, completion time or
any outcome. **Matching by completion order is never used, and no pair is ever formed by searching for favourable or
opposite-arm outcomes** (guidance item 1).

### 7.2 The exact filtration

Let `W_i` be the complete fixed-horizon records of both episodes of pair `i` (all tries, timestamps, drawn seeds,
outcomes).

- **`F_0`** = sigma(roster, strata, arrival order and pairing, and the frozen protocol: hierarchy, tolerances, caps,
  systems and model hashes, `alpha`, `rho`, `delta`, `n_min`, `N_P`). **`F_0` contains no coin, no sampling seed and no
  quantity from which either can be computed.** Potential records are **not** elements of `F_0`: the record that pair
  `i` would produce under an orientation depends on the history (thermal state, caches, everything earlier coins
  caused) and on randomness drawn during the pair (sampling seeds, scheduling). The design-based object is the
  collection, indexed by pair, orientation and history, of the **conditional laws** of the pair's record; the design
  assumption is that none of these depends on a **later** coin, which 5.1 enforces physically.
  **Formally, and this is what every display below conditions on:** there is an internal-randomness variable `xi_i`
  (sampling seeds, scheduling, machine state during the pair), drawn independently of `R_i` given `H_i`, such that the
  pair's record is `W_i = f_i(H_i, R_i, xi_i)`. Write `W_i(r) = f_i(H_i, r, xi_i)`. The two potential records are then
  **random variables on one probability space, coupled through `xi_i`**, so the conditional expectations written in
  7.4 are defined. Without this coupling the display `E(Z_i | H_i, W_i(1), W_i(0))` would have no meaning, and with it
  `mu_i`, the identification of 7.4, the T4 exactness statement and the assumption list of 10.2 item 1 are all
  well defined. The coupling is a **modelling assumption about this harness**, listed with the others in 7.4.
- **`H_i`** = `F_{i-1}` joined with the information used to **pre-enroll** pair `i` (its stratum and task identities).
  Given `H_i`, let `(W_i(1), W_i(0))` denote the pair's potential records under the two orientations. `R_i` is drawn
  from OS entropy after `H_i` is fixed and independently of `(W_i(1), W_i(0))`:
  `P(R_i = 1 | H_i, W_i(1), W_i(0)) = 1/2`. This is exactly the condition of `paper/theory.tex:190-196`
  ("satisfied by a fresh randomization coin with its recorded probability ... excludes assignments driven by
  unrecorded current outcomes").
- **`F_i`** = `F_{i-1}` joined with sigma(`R_i`, `W_i`), where `W_i = W_i(R_i)`.

**Consequences, stated in the root's terms.** The current pair's coin `R_i` is **not** in `F_{i-1}`; it enters at
`F_i`. Earlier coins are in `F_{i-1}`. Later coins are in no `F_j` for `j <= i` and **do not physically exist** while
pair `i` runs (4.2 invariant vii). The scores `Z_i`, `D_i` are `F_i`-measurable with predictable range `[-1, 1]`.
Targets: `mu_i = E(Z_i | F_{i-1})`, `nu_i = E(D_i | F_{i-1})`, and the **running averages**
`mubar_n = n^{-1} sum_{i<=n} mu_i` and `nubar_n` likewise. These running averages are the estimands (10.1).

**The evaluator's real information at calendar time `t`** (reveal order, timestamps, partial traces) is a different
filtration `G_t`. **No martingale argument is made in `G_t`.** Every decision at `(n, t)` is a statement about the
**enrollment-order** process, where the error bound lives (`paper/asynchronous.tex:111-127`), so the live stopping
time needs no stopping-time property with respect to `(F_i)` (`prop:delay`, `paper/theory.tex:535-552`: "No stopping-
time property of `N(t)` is needed for this pathwise inclusion").

**The latent enrollment-order model, stated plainly** (guidance item 2). Pairs are indexed by enrollment position, not
by the time their outcomes arrive. The inferential object is a sequence indexed by that fixed position. A reveal
supplies information about the pair that already occupies position `i`; it never creates a position, never moves one
and never removes one. **No pair's record depends on a later coin** - which is exactly what the design needs -
because the coin of pair `i+1` does not exist while pair `i` runs and the two pairs share no task, no episode and no
in-flight state (5.1). **Carry-over from earlier pairs is allowed** (thermal state, caches, everything earlier coins
caused) and is absorbed into `F_{i-1}`; the protocol does not claim that pairs are independent. What the two
**positions of one pair** share is the host, and that is inside the estimand (7.4), including the two asymmetric
mechanisms named in 6.2.

### 7.3 Enrollment-indexed records: what a reveal-order event may and may not do

This section is normative and is checked by the verifier.

1. A pair occupies an **immutable enrollment position** from its `pair_enrolled` event to the end of the trial.
2. `n = N(t)` is the number of **fully enrolled (pre-enrolled and randomized)** pairs at event time `t`: the count of
   chain-valid `coin_drawn` events. It is **non-decreasing** and changes only at a `coin_drawn`.
3. A reveal-order event (`llm_request`, `llm_response`, `llm_error`, `episode_revealed`) **updates the existing score
   enclosure of the pair at its own enrollment position** and nothing else. **`metrics_scrape`, `server_health`,
   `server_started`, `server_down`, `server_restarted`, `anchor`, `anchor_receipt`, `anchor_failed` and every
   program-chain event are NOT reveal-order events**: they carry no information about any pair's score, they never
   update an enclosure, and they never trigger an evaluation (8.3).
4. **A reveal-order event never appends a new observation, never reorders, never drops and never re-creates a pair.**
   Scores are never sorted by reveal time. A slow pair is never skipped and never divided out.
5. The denominator is always `n`, the number of fully enrolled pairs, **never** the number completed
   (guidance item 2: "never ... divide by the number completed").
6. **Repeated updates are idempotent**: applying the same reveal twice leaves every enclosure and every band endpoint
   unchanged (deterministic test, Appendix C).
7. **At `n = 0` the full range `[-1, 1]` is displayed and no decision is possible.** No decision is possible below
   `n_min` either (8.3).
8. An enclosure **never widens** (7.5). The verifier audits containment of every recorded enclosure against the
   ultimately revealed score of that pair, at **every recorded evaluation**, not only at the decision.

### 7.4 Pair-level identification: what `mu_i` and `nu_i` mean here

`thm:pair_id` (`paper/theory.tex:213-222`) is stated under "There is no interference between the two positions"
(`paper/theory.tex:186-187`). Under pair-synchronous execution the two episodes of a pair **share the GPU**, so that
hypothesis does not hold verbatim. What holds is a **pair-level analogue with a modified assumption**:

> *no interference across pairs; within a pair, potential records are indexed by the pair's orientation and by the
> history; no record depends on a later coin.*

With `U_i` = the kernel evaluated on `W_i(1)` and `V_i` = the kernel evaluated on `W_i(0)` (each oriented candidate
versus incumbent), the fair coin gives

`E(Z_i | H_i, W_i(1), W_i(0)) = (U_i + V_i) / 2`, hence `mu_i = E{ (U_i + V_i)/2 | F_{i-1} }`,

which is `eq:finite_pair_target` (`paper/theory.tex:208-212`) with the interference hypothesis replaced by the one
above, and the same construction with success differences gives `nu_i`.

**What this is and is not.** `mu_i` is "the preference between the two systems **when one episode of each runs side by
side on this host**, averaged over the two orientations of this pair, within the pair's stratum". It is **not** the
preference between systems running alone, and **not** a preference under a production load.
**`nu_i` is the effect on the pair's success difference of reversing the pair's orientation; it equals the average
same-task success effect of the two tasks only if a task's success does not depend on which arm its partner runs.**
That condition can fail in this harness (a partner holding the GPU or the execution lock longer can push a call or a
verification over a wall-clock limit), so it is listed as an assumption, the partner's state is logged with every
verifier timeout (5.2), and **no same-task language is used without it**.

**Primary target, as the guidance requires it to be stated** (item 1): the **enrollment-running symmetrized
cross-arrival preference** `mubar_n` and its success component `nubar_n`. **Ordinary same-task preference is not
identified by this design** and is never reported as the target.

**Assumptions for the causal reading, listed wherever it is used:** the **coupling of 7.2** (one internal-randomness
variable `xi_i` per pair, drawn independently of `R_i` given `H_i`, so that both potential records live on one space);
the OS entropy bit is fair and independent of the pair's potential records; execution is nonanticipating; no record
depends on a later coin; both systems and protocols are fixed for the whole trial; **the operator does not act on
coins**; and, for the same-task reading of `nu_i`, the no-partner-dependence condition above. Carry-over from earlier
pairs is allowed (it is part of the history in `H_i`). **`mu_i` includes the two asymmetric cost mechanisms of 6.2**:
the within-pair duration asymmetry and the execution-lock transfer, so a preference driven by tier 1 is a preference
*including* those mechanisms, not net of them.

**T4, under the coupling.** In T4 `f_i` does not depend on `r` (the two arms are one system and nothing in the harness
depends on the label) and the kernel is antisymmetric in the two positions, so `U_i = -V_i` **pathwise** and
`mu_i = 0` **exactly**, for any hierarchy and any load. The coupling is what 5.5's seed rule and 5.1's
position-to-slot mapping protect: seeds are drawn independently of the coin, and position 1 always runs in slot 0.

**The error guarantee of 8.6 needs none of this** - it needs only adaptedness, boundedness and the frozen rule.

### 7.5 Enclosures (guidance item 5)

Enclosures are **logical certainties derived from worker-stamped spool facts, never predictions**, and they
**never widen** (`paper/asynchronous.tex:33-56, 247-300`). Every score of every fully enrolled pair carries an
enclosure `[lower_j, upper_j]` at every event; a resolved pair's enclosure is the point `[z, z]`.

1. **Start at `[-1, 1]`.** An unresolved hierarchy score starts at `[-1, 1]` and is narrowed **only by enumerating
   feasible completions**. It is collapsed to a point **only on a valid final-score certificate**, which means
   exactly one of two things: **either** both episodes of the pair are revealed with complete finite outcomes and
   `compare` returns, **or** the enumeration of item 5 leaves exactly one feasible value of the score (the cost
   certificate, which can bind while the partner is still pending). **No other collapse exists**, and in particular
   nothing collapses on a guess, a prediction or an imputed outcome. The guidance's own words - "collapse only with a
   valid final-score certificate" - cover both cases, and item 5 is the enumeration that produces the second one.
2. **Success enclosure, the exact formula:**
   `[lower_s, upper_s] = [sA_low - sB_high, sA_high - sB_low]`,
   where A = candidate, B = incumbent; a revealed episode has `s_low = s_high = s`; an unresolved episode has
   `s_low = 0`, `s_high = 1`.
3. **"Absence of failure is not success."** A pending episode has `s_low = 0` **whatever** its trace shows: all model
   calls returned, a program exists, the agent's own tests passed - none of it moves `s_low` above 0. `s_high` drops to
   0 only on a certificate of failure (a terminal row of 6.4, or a returned verifier with exit != 0 or a missing
   sentinel).
4. **"Elapsed cost is a lower bound only if it cannot decrease."** The certified elapsed time of a pending attempt is
   `ell = max_e (t_e - t_c1)`, where `t_c1` is the worker's monotonic time at entry into the first `chat()` call and
   `t_e` runs over the worker's monotonic send and receive stamps of all its spooled request events. It is a valid
   lower bound on `latency_s` because `latency_s = t_final - t_0` with `t_0 <= t_c1` and `t_final >= t_e`, and because
   **there is exactly one attempt per arrival, so the endpoint clock never restarts** (`max_attempts = 1`, 5.6).
   Orchestrator timers are never used. For a terminal failure the recorded latency is the cap or the certified elapsed
   time, both `>= ell`, so no certificate issued earlier can be contradicted. **No certificate is ever derived from
   tokens** (tokens are not a tier).
   **The two clocks, stated because this is decision-defining code.** `latency_s` is produced by the pilot's
   `time.perf_counter()` (`agent.py:247`) while `ell` is built from `time.monotonic_ns()` worker stamps. On
   CPython/darwin both resolve to `mach_absolute_time`, so `ell <= latency_s` holds; the protocol does not rely on
   that silently. A **preflight assertion** records the `perf_counter` and `monotonic` deltas over a 10 s interval and
   **refuses to start** (`preflight_refused(clock_equivalence)`) if they differ by more than
   `clock_equivalence_tolerance_ms = 1`.
5. **Hierarchy enclosure by enumeration.** Let the revealed episode of the pair have arm `r`, `sgn = +1` if `r` is the
   candidate and `-1` otherwise, success `s_r` and latency `L_r`; let the partner be pending with certified elapsed
   `ell`. Write `tol = 0.05` (the frozen cost tolerance).
   - **Neither revealed:** `[-1, 1]` for both scores.
   - **`s_r = 0`:** the partner either succeeds (it wins at tier 0: `Z_i = -sgn`) or fails (joint failure: tie,
     `Z_i = 0`). So `Z_i` lies in `{0, -sgn}` and the enclosure is `[-1, 0]` if `sgn = +1`, `[0, 1]` if `sgn = -1`.
   - **`s_r = 1`:** if the partner fails, `Z_i = +sgn`. If the partner succeeds, its latency `x >= ell` and tier 1
     decides iff `|x - L_r| > tol * max(x, L_r)`.
     **Certificate:** if `(1 - tol) * ell > L_r + 1e-9` then, for every feasible `x >= ell > L_r`,
     `x - L_r > tol * x = tol * max(x, L_r)`, so the revealed episode wins at tier 1 and `Z_i = +sgn` in **every**
     feasible completion; the enclosure collapses to `[sgn, sgn]`. At `tol = 0.05` the certificate is
     **`0.95 * ell > L_r + 1e-9`**. Otherwise the enclosure stays `[-1, 1]`.
   - **Both revealed:** the point value from `compare`.
6. **Containment audit.** The verifier checks, for every pair and **every recorded evaluation**, that the ultimately
   revealed score lies inside the enclosure recorded at that evaluation, and that no enclosure ever widened between
   consecutive evaluations. **A violation is a proven defect of decision-defining code** (the enclosure kernel is in
   the 14.3 list), so it has the consequence of **6.4 row 24** for every trial in which any containment violation
   occurred: claims 2 to 5 and 7 are dropped for that trial and a corrected computation is descriptive only.
   `LIVE_DECISION_INVALID` (8.9) applies **in addition** if the live and reference decisions also differ. There is no
   lighter consequence for a containment violation anywhere in this protocol.
7. **`compare` is never fed a partial outcome.** It requires complete finite outcomes (`src/winstats.py:34`); pending
   success and pending resources are **never imputed**. Enclosures are computed by the enumeration above, not by
   calling `compare` on a guess.

---

## 8. The monitoring rule

This section is the decision rule. Every numeric value in it is frozen before the first design-task outcome of the
program and none may be changed afterwards (14.3).

### 8.1 Inputs at an evaluation

At an evaluation triggered by an event of 8.3 at calendar time `t`, let `n = N(t)` be the **current full enrolled
prefix** (7.3 item 2), and for each score `j` in {`h` (hierarchy `Z`), `s` (success difference `D`)} let
`lower_j[1..n]` and `upper_j[1..n]` be the enclosure endpoints of 7.5 for the pairs at enrollment positions `1..n`.

### 8.2 The band

```python
r = normal_mixture_radius(n, alpha=alpha_gate, rho=100., variance_process=n)
L_j = sum(lower_j[:n]) / n - r
U_j = sum(upper_j[:n]) / n + r
L_j, U_j = max(L_j, -1.0), min(U_j, 1.0)     # intersection with the known range [-1, 1]
```

with `alpha_gate = 0.00625`, `rho = 100.`, `V_n = n` (valid because balanced orientation keeps both scores in
`[-1, 1]`, `paper/theory.tex:303-304`). Comparisons are made in float64. These are **two-sided bands for the running
conditional-mean target** `mubar_n` and `nubar_n`.

**Prohibited, by name** (guidance item 3; revision 2 item 1): no prefix envelope; no maximization of lower bounds over
different prefixes; no retained crossing; no running intersection of bands across looks; no use of a prefix other than
the current full enrolled prefix; no substitution of the number of completed pairs for `n`.

### 8.3 When the rule is evaluated; `n_min`; the horizon

- **Evaluation triggers, the closed list** (this is the look cadence; it is normative and identical in
  `ARCHITECTURE_FINAL.md` §7.1 and in the verifier check of 12.3):
  1. every **`coin_drawn`** (the prefix grows by exactly one; the newly randomized pair enters at `[-1, 1]`).
     COORDINATOR RULING, 2026-09-20: the root guidance defines `n` as "the number of fully enrolled/**randomized**
     pairs" (`reviews/arxiv_live_design_guidance.md:11`), and a pair that has been enrolled but whose coin has not
     yet been drawn and fsynced is not randomized. The prefix therefore grows at the `coin_drawn`, in agreement with
     7.3 item 2, and a pair staged by `pair_enrolled` holds no position until its coin. The earlier wording of this
     line, which grew the prefix at `pair_enrolled`, is WITHDRAWN: it contradicted 7.3 item 2, and after a crash
     between `pair_enrolled` and `coin_drawn` it put the decision code and the independent reference rule in
     different orders about the re-enrolled pair;
  2. every **`episode_revealed`** of a pair of the randomized phase;
  3. every ingested **`llm_request`, `llm_response` or `llm_error`** that **raises the certified elapsed `ell`** of a
     still-pending episode of an enrolled pair - because that is exactly when the cost certificate of 7.5 item 5 can
     bind and collapse the pair's hierarchy enclosure mid-pair. This trigger is the reason the enclosure machinery
     exists; without it every decision would be taken on a completed prefix and the enclosures would be dead weight.
  4. every **resume**, once, at the last fully enrolled prefix before any new enrollment (14.5 item 4);
  5. every **drain reveal** after a decision (9.1 item 4) updates the enclosure and is recorded as a `monitor_update`
     with `trigger = 'drain'`, but **no decision is evaluated at it**: the decision prefix is closed at the crossing.

  A **`metrics_scrape` is never an evaluation trigger**, nor is any other event excluded by 7.3 item 3. Evaluations
  happen on the current full enrolled prefix, in the order the events are ingested. Under pair-synchronous execution
  (5.1) at most one pair is unresolved, so at most one enclosure in the sum is not a point.
  A decision may therefore be taken at a **call** event, with the partner episode still pending (9.1 item 4); the
  in-flight episode is then drained under its original assignment before the traffic switch.
- **`n_min = 100` enrolled pairs.** No decision is possible at `n < 100`. This is *"a reproducible screening choice,
  not a guarantee of adequate power"* (guidance item 6) and is printed as that sentence wherever `n_min` appears.
  At `n = 0` the full range is displayed and nothing is decided.
- **Horizon = the full roster**: `N_P` pairs (3.3). When pair `N_P` is resolved and no condition of 8.4 has held, the
  trial ends with **`ABSTAIN_AT_HORIZON`**. Leftover unpaired tasks are then not executed.
- **No extension, no second pass, no re-randomization, no repeat.** A failed, aborted or abstaining trial is reported,
  never repeated; a repeat would be a new trial under a new protocol version with its own alpha.

### 8.4 The decision conditions

At an evaluation with `n >= n_min`, in this fixed order:

| | condition | action label |
|---|---|---|
| 1 | **`U_h < 0`** | **`HARM_RETAIN_INCUMBENT`** (the prespecified harm tail is the **hierarchy tail only**, not "either"; revision 2 item 1) |
| 2 | **`L_h > 0` and `L_s > -delta`**, both at this same current prefix | **`DEPLOY_CANDIDATE (success margin delta = 0.03)`** |
| 3 | otherwise | continue; if `n = N_P` and pair `N_P` is resolved: **`ABSTAIN_AT_HORIZON`** |

`delta = 0.03`. Conditions 1 and 2 cannot hold at one prefix (they would require `U_h < 0 < L_h`); the order is fixed
anyway. **The action label always carries the margin.** For T3 both labels additionally carry "regime-specific: cost
measured as latency under cross-process GPU sharing on this host".

**A `HARM_RETAIN_INCUMBENT` decision is a statement about the composite only.** It is not success harm, not safety
harm, and not an approval of the incumbent in the reverse direction (1.5 item 5).

**Status with respect to the root.** The two-sided band and its use for a lower-bound deploy decision are the root's
guidance item 6 verbatim. The use of the **upper** endpoint as a **stopping action** is the reading the root retained
for the coding stream (`paper/open_coding_appendix.tex:99-100`) made prospective; the guidance item 4 states that "the
same simultaneous two-sided bands can support prespecified lower-bound deployment and upper-bound harm decisions; no
extra split is needed merely for those two tails", which is the authority for using one band for both tails. **No
additional candidate, primary hierarchy or confirmatory decision route exists**, so no further allocation is needed
(guidance item 4).

### 8.5 The alpha table

| level | value | source |
|---|---|---|
| program | **0.05** | guidance item 4 |
| per trial (four prespecified trials: T1, T2, T3, T4) | **0.0125** | guidance item 4 |
| **`alpha_gate` per band** (two monitored scores per trial: hierarchy, success) | **0.00625** | guidance item 4 |
| `rho` | **100.** | guidance item 4, "a fixed reproducible starting specification, with its power checked before the freeze" (section 11) |
| `delta` (primary and only decision margin) | **0.03** | guidance item 6; revision 2 item 4 |
| `n_min` | **100** | guidance item 6; revision 2 item 9 |
| horizon | full roster, `N_P <= 568` (3.3) | revision 2 item 9 |

**The same two-sided band serves both the deploy tail and the harm tail; there is no extra split for the harm
direction.** The trial count and the allocation are frozen before collection and **are not re-allocated** if a trial is
deferred or aborted (2.4). Every trial, including T4 and T3, carries exactly 0.0125.

### 8.6 The guarantee that is claimed, and the theorems it rests on

For each trial, with the filtration `(F_i)` of 7.2, scores adapted and bounded in `[-1, 1]`, and every constant fixed
before the first design-task outcome of the program:

1. **Band coverage.** `P{ exists n >= 1: mubar_n not in [L_h(n), U_h(n)] } <= 0.00625` and
   `P{ exists n >= 1: nubar_n not in [L_s(n), U_s(n)] } <= 0.00625`.
   *Source:* `thm:normal_cs`, **`paper/theory.tex:288-304`** (statement, with the displayed bound
   `B_alpha(v) = sqrt((v + rho) log((v + rho)/(rho alpha^2)))` at lines 291-297, the coverage display at lines
   300-302, the permission to intersect with a known range at line 303, and `V_n = n` for balanced pair scores in
   `[-1,1]` at line 304); proof at lines 306 onward. The implementation is `src/winstats.py:51-61`.
   Because the enclosures satisfy `sum(lower_j[:n]) <= sum(true scores) <= sum(upper_j[:n])` **pathwise**, the
   enclosure band contains the complete-data band at the same `n`, so coverage is inherited with no extra assumption.
2. **Calendar-time display.** Evaluating the band at any calendar time on the current full enrolled prefix is covered
   by the same event. *Source:* `prop:delay`, **`paper/theory.tex:535-552`**: "the same simultaneous coverage guarantee
   holds over all calendar display times ... No stopping-time property of `N(t)` is needed for this pathwise
   inclusion." Its premise is substantive and is met here by 7.2 and 7.3.
3. **The decision bound.** A false `DEPLOY_CANDIDATE` at prefix `n` (i.e. `mubar_n <= 0` or `nubar_n <= -delta` while
   the rule deploys) implies a coverage failure of at least one of the two bands at that `n`; a false
   `HARM_RETAIN_INCUMBENT` at prefix `n` (i.e. `mubar_n >= 0` while `U_h(n) < 0`) implies a coverage failure of the
   hierarchy band at that `n`. By the union bound,
   **`P{ any false decision statement in this trial } <= 0.00625 + 0.00625 = 0.0125`.**
   *Source:* `thm:drift_gate`, **`paper/theory.tex:494-521`** (statement at 494-510: "If `sum_j alpha_j <= alpha`, the
   confidence-sequence rule satisfies `P{exists n: the rule deploys at n and some mubar_jn <= c_j} <= alpha`"; proof at
   511-521: "The union bound and Theorem `thm:normal_cs` give probability at least `1 - sum_j alpha_j` that all lower
   bounds are valid for all indices and times").
4. **Program level.** No selection among the trials is made and no combined claim is formed, so by the union bound over
   four trials **`P{ at least one false decision statement in the program } <= 0.05`**. This sentence is mandatory
   wherever two or more trials appear together (1.4 claim 9).

**Why the drift gate and not the stationary rule.** The arrivals are a fixed permutation of a finite roster, which does
not give a constant conditional mean (`reviews/round9_open_model_evidence_audit.md:75-81`); therefore the full-level
stationary conjunction `thm:iut` (`paper/theory.tex:466-476`) and retained crossings are **not** used
(`paper/theory.tex:523-525`: "Without a fixed violating component, a time-varying conjunction cannot use the stationary
proof"). The guidance says the same: "The stationary no-split conjunction result is not the default for the proposed
running-mean target under drift" (item 4).

**Nothing is assumed about** stationarity, independence, identical distribution or exchangeability; task composition,
machine state, serial dependence and informative delay are all allowed.

### 8.7 What is explicitly NOT claimed

1. **Not a statement about the latest arrival, a later prefix, a future workload, the all-pairs roster functional
   `theta_N`, a task superpopulation, or production traffic.** The decision certifies **the running average of
   history-conditional pair means at the logged prefix** and nothing else (`paper/theory.tex:524-531`).
2. **Not a joint confidence region for effect sizes.** The two bands are jointly valid for the two running targets
   because the levels were split; they are not a two-dimensional region and no contour is drawn.
3. **Not a calibrated error rate.** One A/A run does not establish a 5% false-decision rate and does not demonstrate
   equivalence (guidance item 8). Calibrated operating characteristics would need repeated prespecified CPU null
   simulations with Monte Carlo uncertainty, which are planning objects only (section 11).
4. **Not evidence about monitoring under delay** (1.1, 1.5 item 18).
5. **Not a bandit-router analysis.** The accepted randomized disjoint-pair design is not one (guidance, "Primitive and
   theorem boundary").
6. **Not a claim that the enclosure extension of any betting statistic is a calendar-time e-process**: no such
   statistic is used as a rule here (8.8).
7. **Not a same-task preference** (7.4).
8. **Not an identification of any causal resource or latency saving** (9.4).

### 8.8 Read-outs logged at every evaluation that decide nothing

All of these are **descriptive**, carry **no error-control claim**, and **never** drive traffic. They are logged so that
a reader can see the trajectory, not so that anyone can choose among them afterwards.

1. **Exploratory success margins 0.10 and 0.15** (revision 2 item 4): the value of `L_s` against `-0.10` and `-0.15`.
   They are printed as "exploratory read-out at margin x; not a decision; **never** described as preserving success;
   **never** reported as non-inferiority at that margin" (1.5 item 4). The reachability of each is in 1.3.
2. **The success statistic restricted to S1 pairs** at the reported prefix (3.5 item 6).
3. **The success-only composite is not a separate object, and nothing extra is computed for it.** With the frozen
   two-tier hierarchy, "the hierarchy with the cost tier removed" is `sign(success_candidate - success_incumbent)`,
   which **is** `D_i`, the score already monitored as the success band. Wherever this protocol says "the success-only
   composite is reported" (6.2, 16, Appendix E), that means the **success band `L_s`, `U_s` and the observed `Dbar_n`
   reported with equal prominence** to the hierarchy. The two genuinely distinct component read-outs are item 2 (the
   S1-restricted success statistic) and item 4 (the tier shares).
4. **Share of pairs decided at each tier**, and all read-outs by stratum family (S1, S2), with the mandatory wording
   "mixes task composition and ... and cannot separate them".
5. **`winstats.betting_log_e_ternary`**, computed **only after the trial has ended**, **only on final complete
   scores**, **never on partial scores**, and reported as "a post hoc descriptive computation with no error-control
   claim and no adapter" (revision 2 item 3; guidance, "Primitive and theorem boundary": it "must not be fed
   weighted/nonternary scores or substituted silently for the declared normal-mixture rule"). It is not computed
   during a trial, is not visible to the live monitor, and no decision, label or sentence depends on it.
6. **The completed-prefix read-out** (9.4): the band recomputed on the completed prefix instead of the enrolled
   prefix, reported as a **coupled descriptive monitor comparison**.
7. **Observed values** `Zbar_n`, `Dbar_n`, win/tie/loss shares, win ratio and win odds (`winstats.summary`), each with
   the sentence that point values at a data-dependent stopping time are biased by optional stopping.
8. **S-lock** (6.2): the hierarchy recomputed with `sandbox_lock_wait_s` subtracted from `latency_s`, reported per arm
   beside every cost-tier statement, with the label "descriptive read-out of the execution-lock transfer; not a
   decision, not a correction of the frozen hierarchy".

### 8.9 The reference rule, the shadow check, and the disagreement rule

The rule of 8.1 to 8.4 exists twice.

- The **live monitor** (`lab_monitor`) drives the dispatcher.
- The **reference rule** (`lab_reference_rule.py`: standard library, numpy and `src/winstats.py` only; it reads
  `coin_drawn`, the spool-derived events and `episode_revealed` from the chain and computes scores only through
  `winstats.compare`; a test asserts that it, the verifier and the builder import nothing from `lab_monitor`,
  `lab_orchestrator` or `lab_worker`) is part of the freeze bundle and is **decision-defining code**: it can never be
  amended, and a proven defect in it has the consequence of 6.4 row 24.

**The reference rule is a real second code path, not a second call into the same code.** `lab_reference_rule.py` is a
separate module, owned by a different implementer group from `lab_monitor` (`ARCHITECTURE_FINAL.md` §3.8b and §10),
importing **only** the standard library, numpy and `src/winstats.py`, and importing **nothing** from `lab_monitor`,
`lab_enclosure`, `lab_orchestrator` or `lab_worker`. It rebuilds the enclosures and the bands from the chain alone and
computes scores only through `winstats.compare`. A test asserts the import isolation, and three injected defects in
the live monitor - a sign slip, a swapped count and a wrong denominator - must each be caught **by the shadow at the
first evaluation at which they change anything** (Appendix C).

**Shadow evaluation at every evaluation** (finding N19). The reference rule is evaluated as a shadow at **every**
evaluation of 8.3, not only on resume and after the trial. Any difference in `n`, in a score, in an enclosure
endpoint, in a band endpoint beyond 1e-9, or in the action **pauses the trial**
(`trial_paused(monitor_mismatch)`, the path of 6.4 row 17) **before any decision is acted on**. The shadow's `n`,
`L_h`, `U_h`, `L_s`, `U_s`, action and mismatch flag are recorded in the `monitor_update` body (12.2 #16), so a
mismatch is evidenced in the chain and not only in a log. Import isolation is unaffected: the shadow runs in the
orchestrator process from the frozen module, reading only the chain.

**The normative decision of a trial** is the reference rule applied to the chain: the **first** prefix `n* >= n_min` at
which a condition of 8.4 holds (a first crossing, not a retained one; it says nothing about later prefixes), or
abstention.

**Why "the first prefix" is well defined even though a prefix has several looks.** Within a fixed prefix `n` the
enclosures only narrow, so `U_j(n)` is non-increasing and `L_j(n)` is non-decreasing across the several evaluations at
that `n`. The set of prefixes at which a condition of 8.4 holds is therefore determined by the **last** evaluation at
each prefix, `n*` does not depend on which evaluation inside the prefix fired, and live/reference agreement on the
prefix is insensitive to the ingestion order of the events at that prefix (this is also why the reorder-invariance
test of Appendix C compares states after a whole set of events, not the intermediate sequence of looks).

- **Agreement** (live `decision` equals the reference result in kind and prefix; integer counts and the action agree
  exactly, band endpoints within 1e-9): the primary result of the trial is the logged decision, its prefix `tau`, the
  receipted time, and the band endpoints at `tau` against their frozen constants, with the guarantee of 8.6.
  **Finding N18, frozen wording:** *any* mismatch at *any* evaluation - in counts, enclosures, statistics or action -
  is **listed** in the report; only a mismatch in **kind or prefix of the decision** changes the result.
- **Disagreement in kind or prefix**, including a live abstention where the reference rule crosses, a live decision
  where it does not, and a reference crossing at `n*` with pairs beyond `n*` already randomized: the primary result is
  **`LIVE_DECISION_INVALID (harness defect)`**. Claims 3, 4, 5 and 7 of 1.4 are dropped for that trial; no statistical
  claim is made for the live decision; the reference rule's first-crossing prefix is printed beside it as
  **descriptive**; exposure figures are reported as measured but not as the effect of the frozen rule; pairs after `n*`
  are reported as "randomized after the reference rule's decision"; the trial is not repeated under its id.
- **After a crash between the resolution of pair `n` and a durable `decision`,** the resumed run evaluates at the last
  fully enrolled prefix **before any new enrollment**; if the reference replay finds its first crossing at that prefix,
  the `decision` is appended with `decided_on_resume: true` and both times; if the first crossing is at a smaller
  prefix, the disagreement rule applies and the trial is closed with `trial_aborted(harness_defect)`.

**There is no second, post hoc primary analysis.**
---

## 9. The traffic switch is a new observation phase

This section is guidance item 7, adopted literally.

### 9.1 What happens at a crossing

1. The orchestrator appends `decision` (durable), closes the log segment, and takes a **blocking anchor** (12.4).
2. Only after the chained external receipt does it append `traffic_switch` and dispatch the first
   `arm_assigned_by_decision`.
3. **Randomization stops.** No coin is ever drawn again in that trial (4.2 invariant iv).
4. **Every already enrolled pair is retained and finished or resolved under its original assignment and under the
   frozen horizon.** A decision **can** be taken while one episode of the deciding pair is still running - that is
   exactly what the cost certificate of 7.5 item 5 and the call trigger of 8.3 make possible. That pair then runs to
   its own frozen end under its original coin, and its reveal updates its enrollment-indexed record as usual
   (`monitor_update` with `trigger = 'drain'`, no second decision). **No episode's workflow is ever cut short by a decision, a pause or an operator**
   (`paper/asynchronous.tex:396-400`), so no endpoint definition changes for a pending episode.
5. **The exact switch time is logged**, three times over: crossing detection, the `decision` event, and
   `traffic_switch`, with the anchor wait shown separately.
6. From then on every remaining arrival of the frozen order (both positions of pairs `tau+1 .. N_P` in order, then the
   unpaired leftovers) runs under the **decided arm**, taken one at a time by whichever worker is free.

### 9.2 In-flight exposure, logged in full

At the switch the harness logs, and the report prints: the list of episodes in flight at the crossing (empty under 9.1
step 4 in the normal case) with their arrival ids, arms and certified elapsed times; the number of enrolled pairs not
yet resolved; the arrivals already dispatched but not yet revealed; the arm exposure counts of the randomized phase by
arm and by stratum; and the first arrival index of the new phase. **Nothing in flight is cancelled, discarded or
re-run.**

### 9.3 The follow-up cohort

Post-switch, all-one-arm traffic is an **operational follow-up cohort**, **not additional pairs for the original A/B
estimator**: positivity and the paired randomization have ended. Therefore:

- it is **outside all inference**: no pair score is computed, no band is updated, `n` does not grow;
- it is **never pooled** with pre-switch data and **never compared** with it (the two phases also use different
  schedulers, 1.5 item 10);
- it is **never called validation or refutation** of the decision and never used to predict future benefit
  (1.5 item 14);
- if it stops early for an operational reason, the report states how many arrivals did not run and claim 3 of 1.4 is
  restricted accordingly.

**What can honestly be measured in it:** actual switches, calls, elapsed time and arm exposures. That is the whole
list.

**What the decision certifies:** "a past enrollment-running target". It does **not** certify the most recent effect or
any future effect without stronger stability assumptions that this design does not supply (guidance item 7).

### 9.4 Boundary statement: no causal resource or latency saving is identified

**Stated now, in the protocol, before any data** (guidance item 7, last three sentences):

> A single switched trial does **not** identify causal resource or latency savings versus continued A/B or versus
> another stopping policy. Those are unobserved counterfactuals. This program runs one trial per contrast under one
> monitoring policy, and no randomized comparison of monitoring policies is designed, so no such comparison is
> identified by these data.

Consequences, all frozen:

1. **The completed-prefix read-out of 8.8 item 6 is a coupled descriptive monitor comparison.** It is computed on this
   run's available records, on the same path, under the same coins; it is not a randomized comparison of monitoring
   policies and is never described as one, never as "the value of early information", and never as evidence that one
   monitoring rule beats another.
2. **No ratio and no percentage of exposures avoided is computed anywhere** (1.5 item 10), because with the same data a
   longer roster gives a larger percentage.
3. Any time or token "saving" is a **labelled projection** (9.5 item 4), explicitly outside the claims of 1.4.
4. No fixed-sample comparator and no relative-efficiency sentence exists in this protocol (revision 1, C27).

### 9.5 Operational quantities, in the order they are reported

Let `tau` be the decision prefix and `M = N_P - tau`.

1. **Primary:** `tau` (pairs and arrivals enrolled at the decision) and the three switch latencies of 9.1 item 5.
2. **Exact count:** `M` pairs of the prespecified roster were not enrolled; under the decision all `2M` remaining
   paired arrivals ran the decided arm. `M` is always printed with the sentence "**`M` is determined by the
   prespecified roster length `N_P`; it is not a saving rate**". No ratio, no percentage.
3. **Measured totals:** wall-clock time, busy time per worker, prompt and completion tokens (successful calls, failed
   calls and unknown-usage calls counted separately), **by phase and by arm**, always "on this host under this serving
   regime"; **never compared across phases**.
4. **Projection, a labelled descriptive item outside the claims of 1.4:**
   `M x (mean pre-switch latency of the rejected-arm episodes - mean pre-switch latency of the decided-arm episodes)`,
   and the same for tokens, with the caption "projection from pre-switch means; biased toward the decided arm by
   optional stopping; computed under side-by-side load, which the follow-up cohort does not have; the two phases use
   different schedulers; **not a measured saving and not a causal saving**".

---

## 10. Estimands, analyses, hypotheses

### 10.1 Primary estimands (one pair of targets per trial)

`mubar_n` and `nubar_n` of 7.2: the **running averages, in enrollment order, of the history-conditional means** of the
hierarchical pair score and of the success-difference pair score, at the decision prefix `n = tau` (or at `N_P` if no
decision). Under the assumptions of 7.4, `mu_i` is the conditional expectation of the orientation-averaged
side-by-side preference within the pair's stratum, and `nu_i` that of the effect of reversing the pair's orientation on
the success difference (equal to an average same-task success effect **only** under the no-partner-dependence
condition). The evaluated systems include the client's connection-retry behaviour (5.6). **Every table caption names
this target.**

**Not targeted:** `theta_N`, any superpopulation mean, any same-task preference, any solo-latency comparison, any
future workload, any production traffic.

### 10.2 Strict separation of design-based from model-dependent statements

**Design-based** - valid from the coin, boundedness of the scores in `[-1,1]`, and the frozen rule alone; no model of
the tasks, the machine or the delay is used:

1. the decision (or abstention), its prefix, and its error bound (8.6);
2. the two bands at the reported prefix, jointly valid at level 0.0125 for the two running targets;
3. the count `M` and the exact operational quantities of 9.5 items 1 to 3;
4. in T4, exactness of the null `mu_i = 0` (7.4);
5. the containment of every recorded enclosure (7.5 item 6).

Coin balance is **reported as a description of the draw, not tested**.

**Model-dependent, and labelled as such wherever it appears** - each names the assumption it needs:

1. the **causal orientation-average reading** of `mu_i` and `nu_i` (7.4): needs the fair-coin model, nonanticipation,
   no dependence on a later coin, fixed systems, and "the operator does not act on coins";
2. the **same-task** reading of `nu_i`: needs, in addition, the no-partner-dependence condition, which this harness can
   violate;
3. every number in the **planning study** (section 11): needs the replay/latent model and pilot predictiveness `w`,
   neither of which is calibrated on anything;
4. the T3 **side-by-side compression** `C` and every statement about what it implies for solo latency: forbidden
   (1.5 item 8), so `C` is printed as a measured ratio of this regime only.

**Descriptive only** - no interval, no test, never feeding a decision: everything in 8.8; per-arm counts, means and
medians of latency, tokens, calls, truncations, failures, retries; tier shares; by-stratum read-outs (wording: "mixes
task composition and ... and cannot separate them"); the sensitivity read-outs S-infra, S-int and **S-lock**; the
per-contrast side-by-side compression `C` (5.8 item 4); `t`-values of the
completed-prefix read-out; switch latencies; everything from the follow-up cohort; the projection of 9.5 item 4. The
words "significant", "equivalent" and "non-inferior" do not appear at all, because the only margin at which
non-inferiority could be claimed (`delta = 0.03`) is a pre-specified near-certain abstention (1.3).

**Not produced at all:** t, Welch, cluster-t, bootstrap or delta-method intervals; win-ratio confidence sequences;
fixed-mean (iid-roster) readings; any function of `src/wincs.py`; any comparison with, or pooling of, pilot episodes;
`M / N_P` or any percentage of exposures; any comparison across the two phases of a trial; any error-control statement
for the post hoc betting read-out.

### 10.3 Hypotheses and what counts as support

The purported deployable and harmful directions are **hypotheses, not known truths** (guidance item 6).

**Declared deviation from guidance item 6.** Guidance item 6 requires that "the reverse contrast uses new disjoint
tasks/assignments". **That requirement is NOT met and is declared as a deviation, not redefined:** all four trials
draw from the same roster (3.5 item 5; a task is executed at most once per trial and up to four times in the program),
for the power reason of 3.5 item 2. What is new in each trial is **the arrival order and the coins**, and nothing
else. T1 and T2 are therefore **not two estimates and not two confirmations** (1.2), no statement anywhere treats
them as independent, and the same row appears in the deviation table of 13.1.

| trial | prespecified expectation | what would support it | everything else |
|---|---|---|---|
| **T4** | no decision | `ABSTAIN_AT_HORIZON` | a decision has probability at most 0.0125 under the exact null; it is **reported and investigated, never discarded** (guidance item 8), and one A/A path is never described as evidence of calibration |
| **T2** | `HARM_RETAIN_INCUMBENT`, expected at the first admissible evaluation `n = 100` | the decision event reproduced by the reference rule, with `U_h < 0` at `tau` | abstention or deployment reported as observed |
| **T1** | (a) the hierarchy condition `L_h > 0` is met at a first prefix `n0 >= 100`; the claim is "at prefix `n0` the running hierarchy target was positive" and says nothing about later prefixes. (b) the success guardrail `L_s > -0.03` is **never** met, so the trial ends in `ABSTAIN_AT_HORIZON` | (a) the evaluation at `n0`; (b) the horizon reached with no deploy | this **is** the prespecified outcome, declared in 1.3, and it is reported as "the composite crossed while the success guardrail refused", never as evidence that the workflows differ or are equivalent. A `HARM_RETAIN` in T1 would contradict the pilot direction and is reported as observed |
| **T3** | none (two-sided, outcome unknown) | not applicable | each outcome, and deferral, is reported with the same prominence |

---

## 11. The planning study

**Wording rule for this section and everything derived from it:** planning numbers are "for this rule, this allocation
and this roster"; the analytic numbers are exact consequences of the frozen radius; the simulated numbers are
model-dependent (10.2). **None of them is a statement about what any method can or cannot certify** (1.5 item 13).

### 11.1 What was computed, by whom, and what is decisive

| object | status |
|---|---|
| **The analytic reachability table (11.3)** | **decisive and model-free.** It follows from the frozen radius and arithmetic alone. It is what establishes the feasibility-study declaration of 1.3. |
| The radius table and its `rho` sensitivity (11.2) | exact, model-free |
| The pilot cross-task effect sizes (1.3) | exact recomputation over all 591x591 ordered cross-task pairs of the pilot, under the frozen two-tier hierarchy; model-free given the pilot records, but the pilot ran on a **different serving stack** |
| R4's replay simulation (`R4_power_analysis.md`, `power_sim.py`, 20,000 replicates per main cell) | superseded in its decision-rule cells (it used v1/v2 rules, levels and margins) and retained for its design facts: per-arrival coins lose about 3% of arrivals and 0.5 to 2 points of power; `n_min` 10 versus 20 is immaterial; the unfavourable direction of T2 is carried by the cost tier, not by success |
| P5 and P6 (`P5_supp_power.*`, `P6_v2_planning.*`) | **superseded entirely.** They planned configurations A and B at `delta = 0.10` with the v2 alpha table. No number from them appears in this protocol. |
| **The extended replay (11.5)** | **mandatory before the freeze**, no fallback (revision 1, C12). It cannot change any rule parameter. |

### 11.2 The radius, and its sensitivity to `rho`

`r(n) = sqrt((n + rho) * log((n + rho) / (rho * alpha_gate^2))) / n`, `alpha_gate = 0.00625`.

| `rho` | `r(100)` | `r(295)` | `r(568)` | smallest `n` with `r(n) < 0.03` |
|---|---|---|---|---|
| 10 | 0.3715 | 0.2181 | 0.1595 | 19,719 |
| 30 | 0.3886 | 0.2163 | 0.1561 | 18,445 |
| **100 (frozen)** | **0.4657** | **0.2287** | **0.1580** | **17,097** |
| 300 | 0.6462 | 0.2722 | 0.1737 | 16,013 |
| 1,000 | 1.0616 | 0.3936 | 0.2270 | 15,320 |

**Reading, honest in both directions.** `rho = 100` is the root's fixed reproducible specification (guidance item 4)
and is frozen; it is **not** the value that minimises the radius at `n = 100` (`rho = 10` would be tighter there, and
`rho = 1000` makes the band the full range at `n = 100`). **No choice of `rho` makes the deploy route reachable**:
every row needs more than 15,000 pairs at `delta = 0.03`. The unreachability of 1.3 is therefore **not an artefact of
`rho`**, and `rho` is not tuned after seeing anything.

### 11.3 The reachability table (the decisive planning object)

A gate can cross at prefix `n` only if the observed running average beats the radius. With a constant observed value:

| gate | threshold on the observed value at prefix `n` | pilot value | first `n` that can satisfy it | within the horizon `N_P <= 568`? |
|---|---|---|---|---|
| T2 harm `U_h < 0` | `Zbar_n < -r(n)` | `-0.4993` | `n = 91`; first admissible evaluation `n = n_min = 100` | **yes** |
| T1 hierarchy `L_h > 0` | `Zbar_n > +r(n)` | `+0.4993` | `n = 91`; first admissible evaluation `n = n_min = 100` | **yes** |
| T1/T2 success guardrail `L_s > -0.03` | `Dbar_n > r(n) - 0.03` | `0.0000` | `n = 17,097` at `Dbar = 0` | **no, by a factor of 30** |
| T4 any decision | `|Zbar_n| > r(n)` | `0.0000` | - | only by chance, bounded by 0.0125 |

**Minimum observed value required at a given prefix** (this is what a reader should use to judge any realized run):

| `n` | `r(n)` | minimum `|Zbar_n|` for a hierarchy or harm decision | minimum `Dbar_n` for the success guardrail at `delta = 0.03` |
|---|---|---|---|
| 100 | 0.4657 | 0.4657 | +0.4357 |
| 120 | 0.4088 | 0.4088 | +0.3788 |
| 150 | 0.3507 | 0.3507 | +0.3207 |
| 200 | 0.2905 | 0.2905 | +0.2605 |
| 250 | 0.2527 | 0.2527 | +0.2227 |
| 295 | 0.2287 | 0.2287 | +0.1987 |
| 350 | 0.2069 | 0.2069 | +0.1769 |
| 400 | 0.1917 | 0.1917 | +0.1617 |
| 450 | 0.1794 | 0.1794 | +0.1494 |
| 500 | 0.1693 | 0.1693 | +0.1393 |
| 565 | 0.1584 | 0.1584 | +0.1284 |
| **568 (horizon ceiling)** | **0.1580** | **0.1580** | **+0.1280** |

**First crossing prefix as a function of a constant realized `|Zbar|`** (the sensitivity that matters most, because the
pilot value 0.4993 sits only 0.0336 above `r(100)`):

| realized `|Zbar|` | 0.55 | 0.50 | 0.4993 | 0.48 | 0.45 | 0.40 | 0.35 | 0.30 | 0.25 | 0.20 | 0.15 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first crossing `n` (with `n_min = 100`) | 100 | 100 | 100 | 100 | 105 | 124 | 151 | 191 | 255 | 372 | none within 568 |

**Frozen consequence:** a realized hierarchy effect about 10% smaller than the pilot's still decides inside the
horizon; an effect below about 0.16 does not decide at all. Both outcomes are reported in the same format.

### 11.4 The honest expectation per trial, fixed now

- **T4 (runs first).** No decision expected; a decision has probability at most 0.0125 under the exact null. **It is
  the implementation/null check only** (guidance item 8): same model revision, same prompts and workflow, same decoding
  law, same verifier, same caps and same serving policy on both labels, **no label-specific seed or worker advantage**
  (the verifier proves the job payloads are byte-identical apart from the label, and the seed rule's worker partition
  is by worker index, not by arm). Its alpha allocation is reserved and every result is retained. **One non-crossing
  A/A run does not establish a 5% false-decision rate and does not demonstrate equivalence.** A crossing is reported
  and investigated, never silently discarded, and the run is not repeated to obtain a different answer.
- **T2.** `HARM_RETAIN_INCUMBENT` expected at the first admissible evaluation, `n = 100`, because `|{-0.4993}| >
  r(100) = 0.4657`. This is the **one live traffic switch the program expects**. Its margin over the radius is 0.0336,
  so a realized effect more than about 7% weaker moves the crossing later (11.3), and an effect below 0.16 gives
  abstention. All three outcomes are pre-written (Appendix E).
- **T1.** The **hierarchy** condition is expected to be met at `n = 100` and the **success guardrail is expected never
  to be met**: with `Dbar` near 0 it needs 17,097 pairs. The expected outcome is therefore **`ABSTAIN_AT_HORIZON`
  after `N_P` (at most 568) pairs, with the composite condition satisfied throughout**. *This is the scientific content of T1 and it is
  declared before collection* (1.3). It is run because a prespecified rule that refuses is a legitimate and reportable
  result, and because the program freeze forbids dropping a trial after its expectation is known.
- **T3.** Abstention is the expected result in every scenario except a candidate that is both more successful and
  faster side by side. T3 is run because it is the only contrast whose outcome is unknown to the operator; an
  abstention is reported with the same prominence as a decision; a deferral under 2.4 is reported under its own
  heading.

**No horizon extension, no margin loosening, no model replacement, and no change of the rule after unfavourable
monitoring** (guidance item 6; revision 2 item 5). Every go/no-go sentence above is frozen text, so an unfavourable run
cannot be reinterpreted afterwards.

### 11.5 The extended replay, specified; mandatory before the freeze

Purpose: a model-dependent check of the crossing-prefix distribution and of the A/A rate for **the frozen rule** on the
**realized** `N_P` and roster. It **cannot change any rule parameter**; if its numbers make a trial look hopeless, the
go/no-go sentences of 11.4 already cover that case, and changing a parameter in response would require a new protocol
version and a new audit.

**Specification** (this closes finding N10, which objected that "R4's simulator" could not do what was asked of it):

1. **Tasks and strata** as in the realized `roster.json`; arrival order drawn exactly as in 3.4 with a fresh seed per
   replicate; whole-pair interleaving; fresh fair coin per pair.
2. **Success.** For an **S1** task under an arm: with probability `w` reuse that task's pilot outcome under that arm;
   otherwise draw a fresh Bernoulli at the arm's pilot **stratum** rate (S1 overall 433/591 for both arms). For an
   **S2** task: draw Bernoulli at the cell rate `q`. A candidate success shift `s` is applied to the candidate's
   probability, clipped to `[0, 1]`.
3. **Cost.** For a both-succeed pair, draw the `(latency_candidate, latency_incumbent)` pair by resampling **jointly**
   from the pilot tasks in which both workflows succeeded (preserving the within-task correlation), then apply the
   frozen tier rule with `relative_tolerance = 0.05`. Pairs that are not both-succeed never reach tier 1.
4. **Rule.** The exact frozen rule of 8.1 to 8.4 with `alpha_gate = 0.00625`, `rho = 100.`, `V_n = n`, `delta = 0.03`,
   `n_min = 100`, horizon `N_P`, first crossing, no retention, no intersection. Scores are complete at each pair
   resolution, so enclosures are degenerate; the enclosure code path is exercised separately by the deterministic tests
   of Appendix C.
5. **Cells, exhaustive:** `w` in {0.3, 0.5, 0.7, 1.0} x `q` in {0.25, 0.45, 0.60} x `s` in {0, -0.02, -0.03} x
   `N_P` in {295, 495, the realized value} x trial in {T1, T2, T3, T4}. 4,000 replicates per cell; 20,000 for T4.
6. **Output, exhaustive and not selected:** for every cell, the counts and rates of `DEPLOY`, `HARM_RETAIN` and
   `ABSTAIN`, each with a pointwise Wilson 95% interval, and the Q1/median/Q3 of the crossing prefix. Every row is
   deposited; no row is omitted for brevity.
7. **Provenance:** script, seed and output SHA-256 enter the freeze bundle; the table is deposited beside this
   protocol and is referenced, not summarised selectively.

**What it cannot show.** It has one pilot run per task and arm on a **different serving stack**; `w` is not calibrated
on anything; it does not model success rates, token counts or speeds under GGUF Q4_K_M, GPU contention inside a pair,
the execution lock, the true difficulty of S2 tasks, or thermal drift. Simulated crossing prefixes are expectations and
are never reported as measured quantities.

**Wall-clock planning** (from pilot latencies, central values and not bounds): 6 to 8.5 GPU hours for the program in
the expected cases, 10 to 11 hours in the worst listed cases, plus the pre-freeze phase. Host budget: 262 GiB free
disk, of which the weights already occupy their share; the evidence deposit is gzip-compressed (12.1).

---

## 12. The event chain and anchoring

### 12.1 One program chain and four trial chains

**Finding N1 is closed by a program chain that exists from the freeze to the end of the last trial.**

**One genesis rule for all three kinds of chain** (identical in `ARCHITECTURE_FINAL.md` §3.2 and §4.2):
`genesis_prev(x, chain_id) = SHA256("live_ab/eventlog-v3|" + x + "|" + chain_id)`, where `chain_id` is `_prefreeze`,
`_program`, `T1`, `T2`, `T3` or `T4`, and `x` is the freeze-bundle SHA-256 for the program and trial chains and the
literal token `prefreeze` for the pre-freeze chain, which is written before the bundle exists.

| chain | path | `chain_id`, `x` | lifetime |
|---|---|---|---|
| pre-freeze | `results/live_ab/_prefreeze/events/seg_<k>.jsonl` | `_prefreeze`, `prefreeze` | closed by `prefreeze_closed` before the freeze; its head, byte length and file hash enter the freeze bundle |
| **program** | `results/live_ab/_program/events/seg_<k>.jsonl` | `_program`, freeze-bundle hash; **its first event, `program_opened`, carries the closed `_prefreeze` chain's head** | from the freeze to the end of the last trial |
| trial (x4) | `results/live_ab/<trial>/events/seg_<k>.jsonl` | the trial id, freeze-bundle hash | one trial |

**The program chain receives** (and nothing else does): `program_opened` and `program_closed`; `trial_opened` and
`trial_closed` (carrying the trial's final head, its status in {`ended`, `aborted`, `not_started`,
`chain_unreadable`} and the comment id of its end receipt, which is how a "trial not started" statement and a
`chain_unreadable` closure (row 25) are recorded); every `refreeze_authorization`; every `preflight_refused`
(6.4 row 21); every `plumbing_verdict` and, on FAIL, its `program_paused(plumbing_fail)` (rows 22a/22b); every
reporting-code `erratum` (row 23); every `decision_code_defect` (row 24); every `trial_paused(worktree_drift)`
escalation (row 27); and every program-level pause and resume. Each carries a harness-computed `what_was_known` and a
**blocking receipt**.

**`trial_started` (seq 0 of a trial chain) quotes the program-chain head**, not the previous trial's head. One verifier
check: *the program chain orders the four trials and contains every authorization that any `invocation_started`
relied on.*

**Evidence deposit.** Everything needed to audit every reported number is deposited **in the repository**, gzip where
large (revision 1, C20; there is no private archive): the program chain, the trial chains, `records/<sha256>.json.gz`
(full `run_episode` records, content-addressed, write-once), `requests/<request_id>.json.gz` (full request and response
bodies), `spools/ep_<arrival>_<attempt>.jsonl.gz` (one per episode, 5.1), `logs/llama_<port>.log.gz`, sandbox results,
and `anchors/anchor_<seq>.json`. Model-generated programs for public benchmark tasks are not sensitive. **What an outsider
can check from the deposit alone:** the chains, the decisions (by re-running the reference rule), the anchors against
the repository, the usage identities, and the success labels (by re-running `verify()` on the archived `final_code`).
**What nobody can check: the coin source** (4.3).

### 12.2 Event schema

Every line is one JSON object with `seq` (0-based, gapless across segments), `type`, `t_wall_ns`, `t_mono_ns`
(comparable within one invocation; worker stamps come from the spools and are comparable with each other on macOS),
`inv`, `trial`, `prev`, `body`, `h`. Arms are always `incumbent` / `candidate`; `pair` and `arrival` are 1-based
indices of the frozen order. "D" = durable (`F_FULLFSYNC` returns before anything depends on the event).

**Field discipline (finding N12, operational definition).** Every string field of every event must be exactly one of:
(a) a value from a **declared enum**; (b) a **hex digest of fixed length** (16, 32, 40 or 64; 16 is the `raw_hex` of a
coin); (c) a **token** from the closed list `<WORK>`, `<HF_CACHE>`, `<LLAMA_BUILD>`, `<RESULTS>`, `<REPO>`, `<HOME>`,
`<TMP>`, `<REMOTE>` optionally followed by a repository-relative path; (d) a **numeric string** or an **ISO-8601 UTC
instant**; (e) a **task uid** matching `^(mbpp|mbpp_full|humaneval)/[0-9]+$`, which is a declared closed form and
**must be present in `roster.json`** - this is what makes `pair_enrolled`, whose `task_uids` are values such as
`mbpp/278` and `humaneval/0`, schema-valid without stretching "declared enum" over a 1,138-member roster.
**Free text is any string that is none of these, and the schema validator rejects it, field by
field, in every event type.** "A commit id" in the prohibition means a commit id **of a foreign repository**; this
repository's own commit ids are permitted in `anchor` and `anchor_receipt` bodies only (form (b)), which is what makes
`trial_started` schema-valid. **The full config is not embedded in an event**: `trial_started` carries the config
**hash** only, and `config.json` is a tracked sibling file whose hash is in the freeze bundle. Descriptive labels that
used to be free text (`delta_label`, `roster_rule`) live in `config.json`, not in the chain.

| # | type | body (main fields) | D |
|---|---|---|---|
| 1 | `trial_started` (seq 0) | freeze-bundle hash; **program-chain head**; config hash; arrival-order hash; roster hash; task-content hash; `N_P`; arms table; monitor block (rule id, function names, `winstats` hash, reference-rule hash, `alpha_gate`, `rho`, `delta`, `n_min`, tiers, tolerances, eligibility rule); coin block (source, bit map, unit); seed rule; failure-rule hash; harness and reused-file hashes; serving-manifest hash; golden-object hashes; profile hash; protocol hash; freeze receipt reference; list of harness-only re-freezes in force; hardware allowlist; package lock hash | yes |
| 2 | `invocation_started` / `invocation_refused` | pid, argv (tokenized), `resumed`, log head at start, reconstructed state, `kern.boottime` hash, drift list against `trial_started` and the chained re-freeze authorizations (any other drift = refusal, 6.4 row 21) | yes |
| 3 | `server_started` | server id, argv, port, GGUF bytes and recomputed sha256, serving-manifest check, full `/props` comparison with the golden object, `model_path` real-path check, GGUF metadata, load seconds, smoke completion (`phase = SERVER_SMOKE`, request hash, receipt comparison, usage, timings) | yes |
| 4 | `server_health` | ok, slots busy, RSS, `clock_anomaly` | no |
| 4b | `metrics_scrape` | server id, scrape point, counters, `ok`, `tries`, `unreconciled` (6.4 row 20) | yes at pair boundaries |
| 5 | `server_down` | detection, return code, in-flight list, last counters, `counters_lost` | yes |
| 6 | `server_restarted` | as #3 | yes |
| 7 | `pair_enrolled` | pair, stratum, arrivals, task uids, phase, `re_enrolled` (true only after a crash between #7 and #8) | yes |
| 8 | `coin_drawn` | pair, entropy source, **`raw_hex` (the 8 drawn bytes, 16 hex characters)**, `bit`, assignment {arrival: arm} | **yes, before any dispatch** |
| 9 | `arm_assigned_by_decision` | arrival, arm, `decision_seq` | yes |
| 10 | `job_accepted` (ingested from the spool) | arrival, arm, worker, worker pid, invocation, worker monotonic stamp | no (its **spool** line is fsynced; that line is the durable fact, 5.1) |
| 10b | `episode_started` | arrival, pair, position, arm, workflow, server id, worker, task uid, `assignment_seq`, enqueue and dispatch stamps, `started_after_resume`, `partner_concurrent` | no |
| 11 | `llm_request` (ingested) | arrival, `call_index`, kind, `try_index`, client request id, server id, body hash, `sampling_sent`, **drawn seed**, messages hash, message count, prompt characters, worker stamps (`t_c1`, `t_send`), spool offset, spool fsync ms, partner in flight, `recovered` | no |
| 12 | `llm_response` (ingested) | identifying keys, HTTP status, `model`, `finish_reason`, `usage`, `timings` (with `cache_n`), whole `generation_settings` object, `id_slot`, `truncated`, tokens cached/evaluated/predicted, rendered-prompt hash, content hash, client seconds, worker receive stamp, `receipt_mismatch`, `recovered` | no |
| 13 | `llm_error` (ingested) | identifying keys, `error_class` (timeout / connection / http_4xx / http_5xx / malformed), HTTP status, SHA-256 of the error text, client seconds, `will_retry`, `usage_known: false`, seqs of the bracketing scrapes, `bound_is_joint` | no |
| 14 | `episode_revealed` | arrival, pair, position, arm, `reveal_index`, every outcome field of 6.1, `error_class`, record hash, `final_code` hash, verification-program hash without the nonce line, static flags, worker start and end stamps, the concurrent-load record of 5.2, `recovered_orphan`, `started_after_resume`; for a terminal failure: certified `ell`, known tokens, number of `llm_response` events already logged and whether they had determined an outcome | yes |
| 15 | `orphan_rejected` | arrival, which orphan check failed, hashes of the rejected files | yes |
| 16 | `monitor_update` | `trigger` from the closed enum {`enroll`, `reveal`, **`call`**, `resume`, `drain`} (8.3); **`n`** (the full enrolled prefix) and `n_collapsed`; per score: `sum(lower)`, `sum(upper)`, `r`, `L`, `U`, clip flags, the enclosure of the unresolved pair if any; the action taken; the **`shadow`** object (the reference rule's `n`, `L_h`, `U_h`, `L_s`, `U_s`, `action` and `mismatch` flag, 8.9); the **`readouts`** object (8.8 items 1 to 4 and 6); kernel code hash. **The exact key set is written once, in `ARCHITECTURE_FINAL.md` §4.4 T19, and this row is the list of what it must contain**; the validator rejects an unknown or a missing key, so the two documents may not diverge | no |
| 17 | `decision` | kind with full label including the margin, `tau`, `monitor_seq`, band endpoints and constants, in-flight list, next unassigned arrival, rule id, `decided_on_resume` | yes + blocking anchor |
| 18 | `traffic_switch` | decision seq, arm, first affected arrival, the three switch latencies, anchor wait, in-flight exposure record (9.2) | yes |
| 19 | `anchor` (last line of a segment) | `upto_seq`, `upto_h`, segment index, segment bytes and SHA-256, cumulative bytes, pairs enrolled and resolved, record-manifest hash, byte length and SHA-256 of each server log, trigger, `blocking` | yes |
| 20 | `anchor_receipt` / `anchor_failed` | anchor seq, `pushed`, commit id on the anchor branch, numeric `comment_id` where a comment was made, server `created_at` and `updated_at`, `receipt_sha256`; or error class | yes |
| 21 | `refreeze_authorization` (**program chain only**, P5) | id, reason code, `scope` (closed enum: `reporting_code` - decision-defining code can never appear here), list of {file, old SHA-256, new SHA-256, diff SHA-256}, `what_was_known` | yes + blocking anchor |
| 22 | `log_recovery` | torn offset, length, SHA-256, `is_prefix_of_canonical_event` | yes |
| 23 | `trial_paused` / `trial_resumed` / `operator_action` | reason code from the closed list of 14.6, `what_was_known` | yes + blocking anchor |
| 24 | `usage_reconciliation` | per server and window: counter deltas versus summed `usage`, residual, `reconciliation_defect`, `seed_collision` count, windows with lost counters | yes |
| 25 | `publication_withheld` | segment index, pattern class | yes |
| 26 | `server_stopped`, `deposit_sealed` | server id and return code; deposit SHA-256, deposit bytes, number of records and spools (12.1) | yes |
| 27 | `invocation_ended`, `trial_ended` / `trial_aborted` | status and reason; exposure ledger by phase and arm; reconciliation totals; terminal failures by arm; longest span without a receipt; `what_was_known`; final head | yes + blocking anchor |

**Program-chain event types** (12.1; bodies in `ARCHITECTURE_FINAL.md` §4.3, rows P1-P12). All are durable and all
carry a blocking receipt:

| # | type | what it records |
|---|---|---|
| P1 | `program_opened` (seq 0) | freeze-bundle, config, rule-block and protocol hashes; the closed `_prefreeze` head, bytes and file hash; trial order; the alpha table, `rho`, `delta`, `n_min`, `rule_id`; harness, reused-file and `winstats` hashes; the freeze receipt |
| P2 / P3 | `trial_opened` / `trial_closed` | trial id, genesis, order and roster hashes, re-freezes in force / status in {`ended`, `aborted`, `not_started`, `chain_unreadable`}, final head, end-receipt id, reason |
| P4 | `plumbing_verdict` | trial, verdict, per-check results, report hash (6.4 rows 22a/22b) |
| P5 | `refreeze_authorization` | as row 21 above |
| P6 | `preflight_refused` | trial, failed checks, drift list (6.4 row 21, before seq 0) |
| P7 | `program_paused` / `program_resumed` | reason code from the closed list of 14.6, `what_was_known` |
| P8 / P9 | `anchor`, `anchor_receipt`, `anchor_failed`, `log_recovery` | as rows 19, 20, 22 above |
| P10 | `erratum` | reporting-code erratum (6.4 row 23): old, new and diff hashes, both output hashes, `what_was_known` |
| P11 | `decision_code_defect` | a proven defect in decision-defining code (6.4 row 24): the affected trials and the claims dropped |
| P12 | `program_closed` | every trial with its status and final head; the program's final head |

`what_was_known` is **always computed by the harness, never typed**: counts of revealed outcomes by arm in this trial,
the current band endpoints and their distance to each threshold, and the final heads and decisions of all earlier
trials of the program.

### 12.3 The hash rule

`canon(x) = json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`; floats by Python `repr`; NaN and
infinities forbidden. `h_i = SHA256(canon(event_i without "h"))`; `event_i.prev = h_{i-1}` **across segment
boundaries**; genesis as in 12.1. Single writer; descriptor opened `O_WRONLY|O_APPEND|O_CREAT`; **one `os.write` per
line**; no file is ever truncated or rewritten; a closed segment is never reopened.

**Torn tails.** On opening a segment for resume, **all bytes from the first invalid byte to the end of the file form
one opaque torn region**, irrespective of newlines inside it; the next event is a `log_recovery` committing to its
offset, length and SHA-256. A chain-valid `coin_drawn` line is never part of a torn region (4.2 invariant v). A chain
that cannot be opened at all is closed through the program chain (6.4 row 25).

**The verifier** `lab_verify_log.py` is a **separate code path written by the same session** (it is **not** called
independent). It checks: canonical round trip; gapless `seq`; chain across segments and into the program chain; the
invariants of 4.2; the enrollment-indexed invariants of 7.3 including **reorder invariance and repeated-update
idempotence**; **enclosure containment at every recorded evaluation** (7.5 item 6); **completeness against the frozen
order** (the sequence of `pair_enrolled` equals `arrival_order_T<e>.json` exactly in pair index, stratum, both uids and
positions; pairs 1 to `tau` (or `N_P`) each have one coin and two reveals; after a decision every remaining arrival and
leftover has one assignment event and one reveal, or the count that did not run is reported); **exactly one
`monitor_update` per evaluation trigger of 8.3, and no `monitor_update` at any event of the follow-up cohort**
(a quiescent `metrics_scrape` there must produce none, and the verifier must pass on such a chain);
one terminal event per `llm_request`; the orphan check matched against
**`job_accepted`** (not against the non-durable `episode_started`, finding N4/N21); outcome fields of `episode_revealed`
equal those of the hashed record; **T4 job payloads byte-identical apart from the label** - operationally: the two job
objects of a T4 pair are compared after removing exactly `arm`, `arrival`, `pair`, `position`, `task_uid`,
`worker_index`, `paths`, `assignment_seq` and `payload_sha256`, and what remains must be byte-identical
(`canonical_job_payload`, `ARCHITECTURE_FINAL.md` §3.12); first coin after the start
receipt and first post-decision assignment after the decision receipt; **equality ties and joint failures** score as
specified; **switch-phase exclusion** (no follow-up-cohort arrival enters any score, any band or `n`); the reference-rule
replay and the agreement test of 8.9; `exposure_ledger.json` equal to a recount from events; the SHA-256 of the first
`segment bytes` of every committed segment blob against its anchor; receipts against `git show` on the anchor branch;
the usage identities of 13.1; the integrity table of 12.6.

### 12.4 Anchoring: mechanics

Revision 1, C10, as simplified. **There is no timestamp authority** (C17 rejected).

1. Trials and the anchor process run **in the main clone** on branch `session60/live-ab` (2.1, revision 1 C15). The
   anchor process owns an **fsynced spool** exactly like a worker (finding N13); the **orchestrator remains the only
   writer of the chain** and appends `anchor`, `anchor_receipt` and `anchor_failed` from that spool.
2. **Anchor commits go to the dedicated branch `session60/live-ab-anchors`.** Each anchor closes the current segment,
   writes a **chain-head hash file** (`anchors/anchor_<seq>.json`: integers and hex digests only), commits **that file
   only** (plus the closed segments at the publication points of item 6), and pushes. **Before every commit, and at
   the start of every invocation, the process asserts that the real path of the working tree, its `HEAD` branch and
   its `git rev-parse HEAD` are the frozen ones, and that the index is clean and the parent is the expected one**
   (2.1 guard 1). On violation before a commit it writes `anchor_failed(tree_state)`, which on a **blocking** anchor
   maps to `trial_paused(anchor_unavailable)` (6.4 row 26); on violation at invocation start it is
   `preflight_refused(worktree_identity)` (6.4 row 21). A change detected **between** these points, while an
   invocation runs, is 6.4 row 27 (`worktree_drift`).
3. **Exactly three issue comments per trial** on issue **#11** (public repository and public issue, checked via the
   GitHub API 2026-09-19, revision 1 C19): at **trial start**, at the **decision**, and at **trial end**. Each comment
   body carries the trial id, `upto_seq`, `upto_h` and the segment SHA-256. The API response fields `id`, `node_id`,
   `created_at`, `updated_at` and the SHA-256 of the raw response are recorded; the numeric id, the two server times
   and that hash are chained as `anchor_receipt`. **There is no 30-comment stream.**
4. **Triggers for a push anchor:** every entry of the `anchor.blocking` list of item 5, plus the periodic
   **every 25 completed pairs**. There is no time-based anchor trigger: an idle trial produces no anchor.
5. **Blocking anchors.** A trial or the program blocks on the push (and, where item 3 applies, the comment) at
   **every trigger listed in `config.json` under `anchor.blocking`**, and at no other trigger. That list is written
   once, in `config.json` (Appendix B), and is reproduced verbatim in `ARCHITECTURE_FINAL.md` §6.1; it is the
   superset that 12.2, 6.4 rows 6, 21, 22a, 22b, 23, 24, 25, 27 and 14.6 actually require:
   `["trial_started", "decision", "trial_paused", "trial_resumed", "refreeze_authorization", "trial_ended",
   "trial_aborted", "operator_action", "program_paused", "program_resumed", "preflight_refused",
   "plumbing_verdict_fail", "erratum", "chain_unreadable"]`. The only non-blocking trigger is the periodic
   `every_25_completed_pairs` anchor. The first `coin_drawn` of a trial requires the chained receipt of the
   start anchor; the first `arm_assigned_by_decision` requires the chained receipt of the decision anchor; a re-freeze
   takes effect only after its receipt. The anchor process retries for up to 30 minutes; after that the trial pauses
   (6.4 row 26). **A failed periodic push is logged and retried at the next anchor point: it never blocks and never
   changes an outcome.**
6. **Publication of the chain.** During the randomized phase the anchor branch receives **anchor files only**, which
   contain no coin and no outcome; this is what makes the arm-blind status file of 14.7 meaningful. The closed segments
   are committed at the `decision` anchor and at the end anchor. Before any commit the scanner of 15.2 runs on the
   files to be committed. A hit in a segment is a harness defect (the chain is identifier-free by construction): that
   segment is withheld (`publication_withheld`), stays in the deposit with its anchored hash, and is listed in the
   report; anchoring continues, and **no sanitized copy of the chain is ever produced**.
7. **The anchor branch is never force-pushed.** Its public events feed (90 days retention) is the only reflog-equivalent
   an outsider has.
8. **Freeze record.** The freeze comment is fetched read-only by the runner, which checks that its body contains the
   bundle hash and that `created_at` precedes the local clock, stores the SHA-256 of the raw response, and refuses to
   start otherwise.
9. The final anchor commit of every trial is tagged (`live_ab/<trial>/end`); tags are pushed; both branches are
   retained; the PR is merged with a **merge commit, never squashed or rebased**, so anchor commits stay reachable.
10. **One anchor drill before the freeze** against the real remote on a drill branch and the real issue thread, with a
    mock chain carrying the real freeze-receipt fields (a throwaway repository could not reveal identifier leaks,
    because its URLs lack the real account and repository names).

### 12.5 What the anchors prove, and what they do not

**They prove:** that a chain prefix with head `upto_h` existed **no later than** the server time of its receipt, to
anyone who can read the public repository and issue #11; and, because each receipt (server-assigned commit id or
comment id with `created_at`) is chained into the log, that every later event was produced **after** that receipt was
issued.

**They do not prove:** that events happened at their logged client times; that this is the only log of the trial; that
nothing was removed before an anchor; that the coins came from OS entropy; or that the producing code was the frozen
harness (harness hashes in the log are self-asserted).

**The precise chronology wording, frozen** (revision 1, C17): *commit and comment timestamps are assigned by GitHub's
servers; comments are editable by the account owner and GitHub shows an edit history; a push cannot be back-dated, but
a force-push could rewrite the anchor branch, so the anchor branch is never force-pushed and its reflog-equivalent is
the public events feed with 90 days retention.* `updated_at` is stored for every comment so that an edit is visible.

**The bound the mechanism supports is "between two consecutive receipts."** A rewrite inside such a window is not
prevented; it leaves traces (12.6). The phrases "tamper-proof log" and "verifiable coin" are forbidden (1.5 item 21).

### 12.6 Integrity forensics

The verifier tabulates, for every trial, and the report prints the tables **whether or not they are empty**:

1. every invocation boundary with the last durable event before it, the open attempts, whether each open attempt had a
   fsynced `job_accepted`, and whether a `coin_drawn` without any `job_accepted` was the last durable event
   (**coin-adjacent**);
2. every torn region: whether it is a strict byte prefix of a canonical event (if not, it is reported as evidence of
   editing), whether it parses as or is a prefix of a `coin_drawn` (coin-adjacent), and whether `kern.boottime` changed
   between the two invocations (a single `os.write` cannot be torn by a process kill, so a torn region without a reboot
   is an integrity event);
3. every terminal failure of rows 10, 10b, 11, 11c, 11d, 11e, 18; every `protocol_deviation`; every `orphan_rejected`;
   every `reconciliation_defect`; every `seed_collision`; and, in a separate column headed **environment events, not
   attributed to the operator**, every `worktree_drift` pause of row 27 with its observed and expected digests;
4. the **time-sandwich audit**: for consecutive receipts k and k+1, the difference of their server `created_at` values
   against the difference of the `t_wall_ns` of the two `anchor` events, with the frozen tolerance
   **`sandwich_tolerance_s = 30` plus `posting_latency_p95_s`**, where the second term is the 95th percentile posting
   latency measured in the anchor drill and pinned in Appendix A (this closes v2's undefined second term); and every gap
   above `gap_report_s = 5` between consecutive events that is not covered by an open `llm_request`, an open sandbox
   execution or an open `/metrics` scrape (finding N3's false-FAIL case: a 10 s sandbox run is a covered gap);
5. the distribution of `job_accepted - coin_drawn` on the monotonic clock, with every gap above 1 s listed;
6. the prefix property of the server logs across anchors.

**Label rule (mechanical, neither an accusation nor an exoneration):** a trial with at least one coin-adjacent event,
at least one sandwich violation, or **three or more pairs containing a row 10, 10b, 11, 11c, 11d or 11e episode** is
labelled **"integrity-qualified"** in every table and sentence that reports it. The label applies to the **randomized
phase and the follow-up cohort alike** for terminal failures and torn regions, and the two are counted separately
(finding N21); the **coin-adjacency** test is computed over the **randomized phase only**, because there is no coin
after the decision and the test would otherwise be vacuous (`PROTOCOL-GAP PG-25`). A `worktree_drift` pause (row 27)
is reported in the same tables but **never contributes to the label**: it is an environment event.

---

## 13. All-attempt usage accounting, and the sampler receipt

### 13.1 Usage accounting for every try

**Two ledgers reconcile by construction.** Request level: the spool holds one request line before, and exactly one
response or error line after, **every try of every call** - retried, failed, terminal, pre-freeze and follow-up-cohort
ones included; the spool is the recovery source after a crash, so a finishing worker's requests are never outside the
ledger. Episode level: `episode_revealed`. Separate counters and tables for episodes, model requests and connection
retries. **Unknown usage is `null` with a reason, never 0.**

**Server-side counters.** `/metrics` (`prompt_tokens_total`, `tokens_predicted_total`) is scraped:

- at **trial start**, where it is compared with the usage of that server's smoke completion; a violation is a
  `reconciliation_defect`, not a refusal (6.4 row 20);
- at **every pair boundary of the randomized phase** (the server is idle there, so the window is one pair; in a pair
  without a failed try the counter delta minus the summed client usage must be exactly 0, and any other value is a
  logged `reconciliation_defect`);
- immediately **before and after every failed try**, as a rule and not "if available"; if the partner slot was busy the
  bound is marked **joint**;
- after every **restart**;
- in the follow-up cohort at a **quiescent point every 50 arrivals** (both workers drain, the scrape is taken, the idle
  time is logged; counters are flushed only when a slot is released, so exact reconciliation exists only at quiescent
  points);
- at the **end**.

Every scrape has a 5 s timeout and at most 3 tries (6.4 row 20). Windows spanning a server crash are reported as
unreconciled (`counters_lost`).

**Declared deviations from R2's checklist, labelled as deviations:**

| R2 item | deviation | wording |
|---|---|---|
| 50 (streaming usage) | `stream: false` is kept | the receipt object and `usage` are established for the non-streamed response at the pinned commit, and the one-pair window gives a per-request bound without a second response-parsing path |
| 32 (first-token timestamp) | **not met, declared** (finding, R2 section 5) | `stream: false` gives no client-side first-token stamp; the **server-side substitute `timings.prompt_ms`** is recorded per response and is named as the substitute wherever a first-token quantity would be expected |
| 42 (fsync per event) | **partial, declared** | only **durable** events are fsynced in the chain; the **spool** is fsynced per request and per response, so every model call is covered by a durable record before it is used |
| 6 (the coin byte is written) | **met** | the eight drawn bytes are logged as `raw_hex` in every `coin_drawn` (4.2). This is evidence of what was drawn, not of where it came from; the entropy source stays operator-attested (4.3) |
| 106 (loopback interface) | met, and the phrase is used | "open-weight models served over the **loopback OpenAI-compatible interface**" appears in 2.2 and in claim 1 of 1.4 |

**Declared deviation from the root guidance** (there is exactly one, and it is not hidden inside a redefinition):

| guidance item | deviation | wording used everywhere |
|---|---|---|
| item 6, "the reverse contrast uses new disjoint tasks/assignments" | **not met for tasks** | "All four trials draw from the same roster (3.5 item 5), for the power reason of 3.5 item 2. What is new in each trial is the arrival order and the coins. T1 and T2 are therefore not two estimates and not two confirmations, and no statement treats them as independent." (10.3) |

**What a request without a response cost is therefore bounded, not measured**: by the counter delta of its window if
the pre-freeze counter test (5.8 item 2, run on the **non-streamed production path**) shows that abandoned generations
are counted, and in every case by the logical bound of 1,024 completion tokens per such request. **If the test shows
that abandoned tokens are not counted**, claim 6 of 1.4 reads "tokens generated for requests that ended without a
response are unknown; their number by arm and the logical upper bound are reported", and the residual is never
presented as a reconciliation of failed work.

**Summary fields are named literally:** `requests_without_usage`, `episodes_with_terminal_failure`,
`canonical_records_absent`, `episodes_with_missing_label` (0 by construction, still reported), `seed_collisions`,
`unreconciled_windows`. Pre-freeze and rehearsal traffic lives in its own chain and is reported separately. Trial
wall-clock, per-worker busy and idle time and per-episode durations are all logged; **each summary states which one it
uses**. **Tokens are never converted into money, energy or "compute"**; prompt tokens stay visible.

### 13.2 The sampler receipt and the golden objects

In the pre-freeze smoke, per server, the harness captures (a) the full `/props` object (with `model_path` tokenized)
and (b) the full `__verbose.generation_settings` object of a reference request. Both enter the freeze bundle as
**golden objects**, together with a frozen **mask list** naming the per-request fields (`seed`, and any field the smoke
test shows to vary with the prompt, each with its own comparison rule).

For **every** response the client compares the **whole unmasked** `generation_settings` object with the golden object
(exact for integers, strings and lists; 1e-6 for floats, because the server echoes float32) and `seed` with the seed
sent; **any unknown or missing key is a mismatch**. `timings.cache_n == 0` and `tokens_cached == 0` are asserted on
every response as the receipt for `cache_prompt: false`, which is a request field the server does not echo. The `model`
field must equal the arm's alias. A mismatch is handled by 6.4 rows 12 and 13 (episode revealed, then `trial_aborted`);
**never a silent continue, never a dropped episode**.

**Finding N7 is closed twice over.** (i) **Structurally**: `--no-cache-prompt`, `--cache-ram 0` and
`--slot-prompt-similarity 0.0` are in the frozen launch line (2.2) and are checked in the golden `/props`, so no
server-side prompt-reuse path is enabled - which matters because `self_test_repair` sends up to four calls sharing a
long prefix to the same slot, which is exactly the situation a prompt cache answers, and because the host-memory cache
is on by default (`_llama_server_help.txt:426, 590`). (ii) **Empirically**: the frozen comparison must pass on **100%
of the responses of the real-server dress rehearsal** (5.8 item 6), which must include complete `self_test_repair`
episodes with repair rounds on both slots and two consecutive episodes with an identical prefix on the same slot.
**Otherwise there is no freeze.**

**What the receipt is.** `generation_settings` is the request **as parsed by the server and merged with its defaults**
(`task_params::to_json()` at the pinned commit); it is **not** read back from the sampler chain. The permitted wording
is that of claim 6 in 1.4. This closes the "actual sampler receipt unverified" finding **only in that sense and only
for these trials**.

If the receipt path cannot be proven on the **coder** server at the pinned build (no `__verbose` object, or no `usage`
or `timings`), **the program is not started**; no logging proxy or other substitute path is built.
---

## 14. Freeze, deliverables, immutability, resume, trial order, operator

### 14.1 The program freeze (one freeze for all four trials)

1. Branch `session60/live-ab`, created from `session60/local-stream` at `ce8b506` plus merges of root main
   (**merge only; never rebase, reset or force-push**). No existing file under `experiments/{local_stream,tau2_open}`,
   `results/{local_stream,tau2_open}`, `paper/`, `src/` or `reviews/` is touched; the only shared file that may change
   is `results/SESSION60_RESULTS_INDEX.md`. Execution stays in the new directories `experiments/live_ab/` and
   `results/live_ab/`, and `src/winstats.py` is a **pinned read-only core dependency**, so the root can review the
   freeze without overwriting owner work (guidance item 9, last sentence). **The working location is settled, not an
   open item:** the shared clone of revision 1 C15 is kept, and the two guards of 2.1 - the identity assertion at
   every invocation and before every commit (12.4 item 2) and the 60-second worktree-integrity check of 6.4 row 27 -
   are what make a concurrent checkout or merge by another session a detected, receipted pause instead of a silent
   corruption or a false integrity finding against the operator.
2. Harness, unit tests, mock-server dry runs (every derived file carries a MOCK banner and sits under a path that every
   builder excludes).
3. **Pre-freeze out-of-design phase** (5.8), in this order: serving build and manifest; the `mbpp.jsonl` and LICENSE
   downloads; roster and reference sweep; golden objects and mask list; counter test on the production path;
   calibration with the fixed plan; the real-server dress rehearsal with its four injected faults; the containment
   probe; the T3 preflight rules; the anchor drill; the extended replay on the realized `N_P` (11.5); the derivation
   file. **Every freeze condition of 5.8 item 6 must hold.**
4. **Assemble and post the freeze bundle** (14.2). Commit, push, and post the commit and the bundle hash on issue #11.
   Only then may a design episode start.
5. The runner refuses to start on any hash mismatch and **re-verifies harness, config, serving manifest and weights at
   every invocation**.
6. **The `winstats` pin** (finding N11). If `src/winstats.py` is not at SHA-256 `56955ce0...` at the moment the freeze
   bundle is assembled, **the freeze is refused** and the change is escalated; no trial runs against a different core.
7. **The rule-block hash** (finding N11, retained even though no consultation remains). Sections 6.2, 6.3, 6.4, 7, 8
   and the statistical keys of `config.json` form a **rule block** with its own SHA-256, recorded separately in the
   freeze record. Any later erratum to the protocol text must show that the rule-block hash is unchanged and must list
   every other difference as a diff.
8. **Immutability.** From the **first design-task outcome of the program** (the first T4 episode), every item of
   14.3 is immutable for every trial, **including the trials that have not started**.
9. Corrections to the frozen protocol text are **errata files**; the frozen bytes never change.

### 14.2 The freeze deliverable (root guidance item 9, item for item)

| # | guidance item 9 requires | delivered as |
|---|---|---|
| 1 | task/pair manifest hashes | `roster.json` hash, **task-content hash** (canonical file of prompts, hidden tests and entry points of the whole roster), the four `arrival_order_T<e>.json` hashes |
| 2 | all four exact contrasts | the arms table of 2.5, reproduced in `config.json` |
| 3 | open model revisions and licences | 2.3: repository, revision, file, bytes, recomputed SHA-256, licence evidence hash for both models |
| 4 | scheduler / isolation model | 5.1, 5.2, 5.7: pair-synchronous dispatch, `-np 2`, host-wide execution lock, exclusivity, Seatbelt profile hash and containment-probe results |
| 5 | alpha table | 8.5, reproduced in `config.json` |
| 6 | margins | `delta = 0.03`; exploratory read-outs 0.10 and 0.15 declared as non-decisions |
| 7 | `rho` | `100.`, with the sensitivity table of 11.2 |
| 8 | minimum / horizon / caps | `n_min = 100`; horizon `N_P`; every row of 5.6 |
| 9 | seeds and seed receipt | the arrival-order seed rule (3.4); the drawn per-request seed rule with the worker partition (5.5); the **golden objects and mask list** and the per-response receipt comparison (13.2) |
| 10 | all interval/decision code | `lab_monitor`, **`lab_reference_rule`**, the verifier, the builder, the scanner and its pattern list, with per-file SHA-256 |
| 11 | sample append-only event schema | 12.2 and 12.3, plus a sample chain from the rehearsal |
| 12 | CPU planning results | 11.2, 11.3 (analytic, decisive) and the **exhaustive** output of the extended replay (11.5), with script, seed and output hash |
| 13 | deterministic tests of **enrollment/reveal reorder invariance, repeated-update idempotence, enclosure containment, equality ties, joint failures, switch-phase exclusion** | Appendix C, section "guidance item 9 tests"; all must pass before the freeze |
| 14 | exhaustive rather than selected planning outputs | every cell of 11.5 is deposited; no row is omitted for brevity |
| 15 | execution in the claimed new directories; pinned read-only core | 14.1 item 1 |

The bundle hash is the SHA-256 over the canonical JSON of all of the above plus: the protocol hash; the rule-block
hash; the hash of every file under `experiments/live_ab/`; the hashes of the reused `local_stream` files and of
`src/winstats.py`; the serving manifest; the environment lock hash; and the **final head, byte length and file hash of
the closed `_prefreeze` chain together with the derivation file**. **Preflight fails on any "unknown".**

### 14.3 Immutability, and the two classes of code

**Nothing in this list can be amended, within a trial or between trials.** If one of these would have to change, every
affected trial ends (`trial_aborted`) or is not started; a continuation is a **new protocol version** with its own
audit, freeze and alpha, and every trial that starts after such a change is relabelled "parameters fixed after `N`
program outcomes of the same systems on the same tasks" and loses the wording of claims 1 and 2.

**Non-amendable, by name** (finding N16 adds the last row):

| group | items |
|---|---|
| statistical | `alpha_gate`, the trial and program levels, `rho`, `V_n = n`, `delta`, the exploratory margin list, `n_min`, the horizon `N_P`, the arrival orders, the hierarchy and its tolerances, the eligibility rule, the tie rule, the decision and harm conditions, the enclosure rules and the 0.95 certificate constant, the reference rule |
| execution | every row of 5.6, `W = 2`, the server arguments and launch line, every sampling parameter, the seed rule, the prompts, the models, the roster and its exclusion rules, the failure-to-outcome rules of 6.4 |
| **reporting thresholds (N16)** | `integrity_label_rule` (coin-adjacent 1, sandwich violations 1, pairs with terminal failure 3), `auto_abort.consecutive_infrastructure_failures = 10`, `sandwich_tolerance_s = 30`, `posting_latency_p95_s`, `gap_report_s = 5`, `blocking_wait_minutes = 30`, the pause thresholds (`battery < 20%`, `free disk < 5 GB`), the `/health` thresholds (5 s, 3 failures), the coin self-test limits (4,850 to 5,150), the format-conformance minimum (9 of 10), **`worktree_check_s = 60`** (6.4 row 27) and **`clock_equivalence_tolerance_ms = 1`** (7.5 item 4) |

**Two classes of code** (finding N3):

- **Decision-defining code** - `lab_coin`, `lab_reference_rule`, the scoring path, the failure rules, the seed rule,
  `config.json`, the rosters and arrival orders, the reused pilot files, `src/winstats.py`: **immutable**. A proven
  defect has the consequence of 6.4 row 24 (claims dropped for every affected trial; a corrected rule is descriptive
  only).
- **Reporting code** - the verifier, the builder, the scanner: **versioned erratum** through the program chain
  (6.4 row 23), with old hash, new hash, diff hash, `what_was_known` = everything, **both** outputs deposited, the
  frozen constraint that the list and definitions of the tables of section 16 cannot change, and the frozen fact that
  **no erratum can alter a decision**, because decisions come only from decision-defining code.

### 14.4 The harness-only re-freeze

The only permitted change after the program has started, for a **plumbing** defect (the stated purpose of running T4
first):

1. The closed list of 14.3 may not change.
2. A **`refreeze_authorization`** event in the **program chain** names each changed file with old SHA-256, new SHA-256
   and the SHA-256 of the diff, the reason code, and the harness-computed `what_was_known` (which covers all completed
   trials). It is followed by a **blocking anchor**; the diff is committed with it. The runner's drift check accepts
   **exactly the chained authorizations and nothing else**. Because the authorization lives in the program chain, it
   has a home **between** trials, which is where it is most likely needed (finding N1).
3. Inside a running trial (for example 6.4 row 17) the verifier must show that the amended live monitor reproduces
   **every earlier `monitor_update`** of the reference rule; then 8.9 decides the trial's result.
4. **Completed trials stand and are never repeated.** A re-run of T4 would be "T4b", a new trial under a new protocol
   version.
5. Every trial that runs under a re-freeze carries, in claim 2, "harness files were changed after `N` program outcomes
   by the procedure of 14.4; no rule parameter changed".
6. A change of an operational detail that is in **neither** list (for example the anchor cadence) follows the same
   event sequence with reason code `operational`. Times are never typed by hand. It applies to both arms, flags every
   unit with its regime, keeps all units in the denominator and claims no counterfactual invariance.

### 14.5 Resume (a pure function of the verified chains and the spools)

1. Verify the program chain and the trial chain; commit a torn region with `log_recovery` (12.3); **refuse on any drift
   that no chained authorization covers** (6.4 row 21); take the exclusive lock; wait for surviving workers of the
   previous invocation (5.1).
2. Ingest the unlogged remainder of every spool (`recovered: true`).
3. For every assignment event of either kind (`coin_drawn`, `arm_assigned_by_decision`) without its reveals:
   - if the arrival has a fsynced **`job_accepted`** line, an open attempt is revealed from its spool's terminal line
     **only if** every call in the record matches spool and chain entries (request id, body hash, content hash, usage),
     the worker pid and invocation id match `job_accepted`, and the record hash matches (`recovered_orphan: true`);
     otherwise the files are kept as evidence, `orphan_rejected` is logged if a record file existed, and the attempt is
     revealed as `interrupted` (6.4 row 11). **Nothing is re-run.**
   - if the arrival has **no** `job_accepted` line, it is **dispatched now** as its one and only attempt, per 6.4 rows
     11c to 11e. This is not a re-run; nothing had run.
   - a `pair_enrolled` without a coin is re-enrolled with `re_enrolled: true` and then receives its one coin.
4. Replay the reference rule over every prefix from `n_min`; apply 8.9 (decision on resume, or harness-defect closure)
   **before any new enrollment**.
5. If a `decision` exists without `traffic_switch`, continue the decision sequence (anchor, receipt, switch). **If a
   `decision` exists, no coin is ever drawn again.**
6. Recovered orphans are revealed first, in arrival order (frozen tie rule). **No resume path deletes, overwrites or
   re-runs anything.** A double resume is idempotent; two orchestrators are refused.

### 14.6 Trial order, unconditional execution, inspection between trials, pauses and aborts

**Order: T4, T2, T1, T3** (revision 1, kept). T4 first, so that a plumbing defect is found where it costs no claim and
is repaired only through 14.4; T3 last, on the most exercised harness. The residual risk that T4 cannot exercise
`self_test_repair` is closed **before** the freeze by the dress rehearsal of 5.8 item 6, which runs both workflows and
both models on the production path (finding N8).

**Each trial starts when the previous one has ended.** The only admissible reasons for not starting a trial are the
operational reason codes below (**none refers to an outcome**) and the T3 deferral rules of 2.4, which are evaluated
before the freeze. **A trial that is not started is reported under its own heading**, with its `invocation_refused` or
`trial_opened`/`trial_closed` pair in the program chain.

**Inspection between trials (procedural).** After each trial the verifier runs in **plumbing mode** and outputs only:
chain and completeness checks, the reference-rule agreement flag, reconciliation residuals, receipt mismatches, arm
symmetry of stamps and T4 payload identity, terminal-failure counts, `seed_collision` counts, integrity tables, anchor
receipts. **Task-level outcomes, success tables by arm or stratum and every table of the builder are neither built nor
read until the last trial has ended.**

**Pauses.** A pause exists only between pairs, after a drain (6.4 row 11b). Closed decision table:

| reason code | machine-checkable condition | single action |
|---|---|---|
| `power` | on battery below 20% | drain, pause, resume when cleared |
| `disk` | free space below 5 GB | drain, pause, resume when cleared |
| `server_unrecoverable` | a supervised restart failed within `server_recovery_s` | in-flight calls fail by row 1; after the pair: pause; resume only with an identical serving manifest and golden `/props`; otherwise `trial_aborted(server_identity)` |
| `anchor_unavailable` | a blocking receipt not obtained within 30 minutes, or `anchor_failed(tree_state)` on a blocking anchor | pause; resume when receipts can be obtained |
| `monitor_exception` | 6.4 row 17 | pause; harness-only re-freeze; replay; 8.9 |
| `monitor_mismatch` | the shadow reference rule differs at any evaluation (8.9) | pause **before any decision is acted on**; same path as `monitor_exception` |
| **`worktree_drift`** | 6.4 row 27: a freeze-bundle file, a closed chain segment or `src/winstats.py` differs from its bundle digest at the 60 s check, or the worktree path / `HEAD` branch / `HEAD` commit differs from the frozen one | drain, pause, resume only after the tree is restored and every digest matches; a changed closed segment is `trial_aborted(chain_unreadable)` and is never attributed to the operator |
| **`plumbing_fail`** | **between trials only**, on the closed condition list **A** of 6.4 row 22a | program paused in the program chain; harness-only re-freeze of **reporting code only**; next trial. A second occurrence with the same condition id stops the program |
| **`plumbing_fail`** (list B) | **between trials only**, on the closed condition list **B** of 6.4 row 22b | program paused in the program chain; **6.4 row 24 applies to the affected trial; continuation requires a new protocol version** |
| `planned` | operator absence announced | allowed **only** as a pause whose receipt exists **before** the operator leaves; an absence without it appears as an unexplained gap in 12.6 |
| `operator_discretion` | none of the above | logged and reported under exactly that name, with `what_was_known` |

(The v2 reason code `thermal` is **removed**: it named no probe and a thermal probe is a new external dependency.)

**Aborts.** The automatic aborts of 6.4 are deterministic. Every other abort is `trial_aborted(operator_discretion)`
and is reported under that name. Every pause, resume, abort and operator action carries the harness-computed
`what_was_known` and an external receipt, and the program-level report lists every abort with the band endpoints at the
abort. **An aborted trial is reported, never restarted**; no decision other than one already logged is claimed.

### 14.7 The operator is an AI agent session; blinding is procedural

The operator is an AI agent session with file access to the whole run; it **could** read the plaintext chain. Blinding
is therefore **procedural, not enforced**, and is described that way: the orchestrator writes an arm-blind
`status.json` (pairs enrolled and resolved, elapsed time, server health, receipts, terminal-failure count;
**no outcome, no coin, no band endpoint**); the run book restricts the operator to that file and to process exit codes
during the randomized phase; during that phase nothing but anchor files reaches the repository (12.4 item 6); any
deliberate look at a chain is an `operator_action`. **The absence of such an event proves nothing, and the reports say
that.** The hash of the exported operator session transcript is recorded in the delivery if the export is available.

Every session-60 document about these trials carries the sentence "**prepared and checked by AI agent sessions; not
human peer review or author sign-off**".

---

## 15. Reproducibility and release hygiene

### 15.1 Reproducibility

- One deterministic builder `experiments/live_ab/build_live_ab_results.py` (standard library, numpy, `src/winstats.py`
  and the reference rule only) regenerates every table and figure input from the tracked files; it has **no import
  path** to the harness, the sandbox or an HTTP client (a test checks this), never runs a model or a generated
  program, and writes timestamp-free outputs (run metadata in a sidecar). It is **reporting code** (14.3), so a defect
  found after outcomes exist is repaired by the versioned erratum of 6.4 row 23, and **no erratum can alter a
  decision**. It is run only after the last trial has ended.
- **Tracked deliverables per trial:** `events/`, `anchors/`, `metrics.csv` (row-preserving projection, one row per
  arrival: no `final_code`, no self-test code, no stderr, no tracebacks; keeps `error_present`, error class, the three
  timeout fields, retry counts, `hack_flags`, `sandbox_flag`, the code hashes, the concurrent-load record),
  `pairs.csv`, `monitor.csv` (one row per evaluation with `n_enrolled`, both enclosure sums, `r`, `L`, `U`, the action,
  and the shadow-mismatch flag), `decision.json`, `exposure_ledger.json`, `usage_reconciliation.json`,
  `integrity.json`, `config.json`, `roster.json`, `arrival_order.json`, `provenance.json` with two separate hash tables
  (original private inputs; derived tracked files), `env_lock.txt` (`pip freeze`, interpreter, OS build, llama.cpp
  commit, serving manifest, build options, compiler and SDK versions, launch lines), non-executed `.txt` snapshots of
  the harness sources, `SOURCE_NOTICES.md`, `DELIVERY_LEDGER.md`, and a versioned generated report. Reports are
  versioned and never overwritten; exactly one governing document per trial is named first everywhere. Counts quoted
  in hand-off notes come from an included command. Digests are called digests.
- A consistency check proves **reproducibility of numbers, not their sampling assumptions**; the verifier report says
  so. **Decisions and integer counts reproduce exactly on any platform**; band endpoints within 1e-9 (last-bit
  differences of `log` and `sqrt` are expected across platforms and only the tolerance is required).
- **Generation is seeded but not bit-reproducible** (continuous batching); success labels are archived verifier labels.
  After the last trial an **owner-side re-verification pass** re-runs `verify()` on every archived `final_code` and
  reports agreement with the logged labels, with timeouts listed separately; it is **AI review by the same session** and
  is described as such.
- The harness code licence is decided by the author; "no licence statement" means all rights reserved and the release
  note says so (revision 1, C13).

### 15.2 Identifiers and scanning

- **No tracked artifact contains an absolute path, an account name, a host name, a URL or a foreign commit id, with
  three exemptions named here by key** - `config.json`'s `llama_cpp.commit` and the two `servers.*.hf_revision`
  values, which are **upstream revision identifiers of the pinned third-party sources**, are required to reproduce
  the build and the weights, and contain no account or host name. They are allowlisted **by key**, not by pattern.
  Inside the **event chain** even these appear only as digests (`llama_cpp_commit_sha256`). The
  harness writes repository-relative paths and the tokens `<WORK>`, `<HF_CACHE>`, `<LLAMA_BUILD>`, `<RESULTS>`,
  `<REPO>`, `<HOME>`, `<TMP>`, `<REMOTE>`; host
  facts and environment variables come from allowlists; error texts enter tracked files only as class plus SHA-256;
  `/props` fields holding paths are tokenized before they are logged.
- A release check scans every text member of every tracked or packaged file for: the local account name, the GitHub
  account name, the institution name, `/Users/`, `/home/`, `/private/tmp/`, `/var/folders/`, and e-mail patterns,
  anywhere in a string. It is a **bounded known-pattern check** and is described as such, not as a proof. Exemptions
  are allowlisted by exact string: the pattern list itself and the neutral sandbox root `/private/tmp/labsbx`. Before
  the freeze the scanner is run on a mock chain produced with the real freeze-receipt fields (12.4 item 10).
- **The released chain is byte-identical to the raw chain.** Raw evidence is never rewritten; there is no sanitized
  copy (a sanitized chain could not verify). Because the repository and issue #11 are public and the target is arXiv,
  **there is no anonymous variant** (revision 1, C26): there is one deposit.

---

## 16. What is reported whatever the outcome

For every trial - including aborted, abstaining, deferred, not-started, `LIVE_DECISION_INVALID`, integrity-qualified
and "wrong-direction" ones - **in the same format and with the same prominence**:

1. the **freeze record** (commit, bundle hash, rule-block hash, receipts, repository and issue visibility, the
   guidance file hash that this protocol adopts) and every re-freeze, erratum, pause, operator action and reason code,
   each with its `what_was_known`;
2. **enrollment:** pairs pre-enrolled, fully enrolled, resolved, flagged (`infra_flag`, `recovered_orphan`,
   `started_after_resume`); terminal failures by cause and arm with the number of responses already logged; torn
   recoveries; the longest span without a receipt; unpaired leftovers; arrivals that did not run;
3. the **decision or abstention** with its full label including the margin, `tau`, the receipted time, the band
   endpoints and constants at `tau` or `N_P`, the evaluation-by-evaluation trajectory, and the reference-rule agreement
   result together with **every** listed mismatch at any evaluation (8.9);
4. win/tie/loss counts, tier shares against the pilot-expected shares, per-arm success counts, observed `Zbar` and
   `Dbar`, all labelled descriptive and optional-stopping biased;
5. the **enclosure content** at the decision (which pairs were unresolved and what their enclosures were), the
   completed-prefix read-out with its "coupled descriptive" label, the switch latencies, and the reveal-order
   statistics;
6. the operational quantities of 9.5 **in that order**; the exposure ledger by phase and arm; **the per-contrast
   side-by-side compression `C` of 5.8 item 4 and the regime label of 6.2**; **the labelled projection last**; and the
   boundary statement of 9.4 in the same section;
7. failure-inclusive usage accounting in the wording fixed by the counter test; residuals and defects as numbers;
   unknown usage by arm; `seed_collision` counts; receipt mismatches (expected 0); served-model checks;
8. the per-arm table of 4.5 as **primary reporting**, and the integrity tables of 12.6 with the label if it applies;
9. by-stratum read-outs, the S1-restricted success statistic, the exploratory margins 0.10 and 0.15 with their
   non-decision label, the sensitivity read-outs S-infra, S-int (and the **N17 clause in the decision sentence**) and
   **S-lock**, `sandbox_lock_wait_s` **by arm next to every cost-tier statement**, the number of tasks excluded by
   rule 3.2 item 4 with their reference verification times (3.5 item 7), and the post hoc betting read-out with its
   no-error-control label, all labelled descriptive;
10. the **planning expectation next to what happened**, including the frozen sentence "the composite crossed while the
    success guardrail refused", reported as the prespecified behaviour of the rule at a margin declared before
    collection to be a near-certain abstention at this horizon (1.3) and **never** as evidence that the workflows differ or are equivalent;
11. for **T4**: whether any band crossed; if so, the statement that this event has probability at most 0.0125 under the
    exact null and did occur, that it is investigated and not discarded, and the scope sentence of 1.2;
12. for **T3**: the model identity, licence evidence, the rationale of 2.4 with its outcome-informed criterion named,
    the preflight results, the side-by-side compression `C`, the regime label, the contamination sentence - or the
    deferral and the rule that caused it;
13. for **T1 and T2 together**: the sentence that they test one contrast with the roles exchanged and are not two
    confirmations; wherever several trials appear together: the program bound **0.05**;
14. the disclosure of 1.1 (every pilot-informed parameter) and of 3.5 item 3 (outcome knowledge inside the program);
15. unsuccessful hypotheses, negative and inconclusive results retained in the results index under their own heading;
    **nothing is rerun to obtain a different answer**; deferred items listed as deferred.

The results index separates: **observations; the prespecified live analysis; owner-side descriptive readings; excluded
methods.** The PR body is regenerated from the governing report at each hand-off. **No statement says or implies that
the root approved anything beyond the literal text of `reviews/arxiv_live_design_guidance.md`.**

---

## Appendix A. Pre-freeze appendix: values determined by a rule, pinned before the freeze

Each value below is decided by a rule written above that uses **no design-task outcome**; each decided value is
recorded with its inputs in the **derivation file**, and the derivation file is in the freeze bundle.

| value | rule that determines it | section |
|---|---|---|
| `n_S2` and therefore `N_P` | the exclusions of 3.2 applied to the verified `mbpp.jsonl` | 3.2, 3.3 |
| whether T3 runs | the six preflight rules of 2.4 | 2.4 |
| recomputed SHA-256 of both GGUF files | recomputation at preflight; the values of 2.3 are expectations | 2.3 |
| `serving_manifest_sha256` and all its fields | the build of 2.2 | 2.2 |
| `c_max`, hence `request_timeout_s`, hence `episode_hard_cap_s` | the fixed calibration plan of 5.8 item 3 and the formulas of 5.6 | 5.6, 5.8 |
| golden `/props` and `generation_settings` objects; the receipt **mask list** | the smoke capture of 13.2, validated at 100% on the rehearsal | 5.8, 13.2 |
| the accounting wording for abandoned requests | the non-streamed counter test of 5.8 item 2 | 13.1 |
| the exact `/metrics` start identity, or the fallback wording "residual reported" | the rehearsal of 5.8 item 6 | 6.4 row 20, 13.1 |
| the side-by-side compression `C`, **one per contrast** (T1, T2, T3, T4) | the defined statistic of 5.8 item 4 | 6.2 |
| the generated `radius_table.csv` | `dryrun_live_ab.py --radius-table` against `src/winstats.py`; every radius printed in this protocol is checked against it | 1.3, 11.2, 11.3 |
| the number of tasks excluded by rule 3.2 item 4 and their reference verification times | the reference sweep under load of 5.8 item 5 | 3.5 item 7 |
| the measured `perf_counter` / `monotonic` difference over 10 s | the preflight assertion of 7.5 item 4, tolerance `clock_equivalence_tolerance_ms = 1` | 7.5 |
| Seatbelt `profile_sha256` and the containment-probe results | 5.7 item 3 | 5.7 |
| `posting_latency_p95_s` (the second term of the sandwich tolerance) | the anchor drill of 12.4 item 10 | 12.6 item 4 |
| vendor-published pass rates used for criterion (vi), with sources | 2.4 | 2.4 |
| the extended-replay table (script, seed, output hash) | 11.5 | 11.5 |
| licence-evidence hashes for both models and both datasets | 2.3, 3.1 | 2.3, 3.1 |

**Nothing else is left open.** Every other constant in this protocol is numeric now.

## Appendix B. The frozen configuration `config.json` (`null` = pinned in the pre-freeze phase, Appendix A)

This is the **single** canonical key list. `ARCHITECTURE_FINAL.md` §6.1 carries the identical block, and a
freeze test compares the two byte for byte after stripping the fences. The **rule block** whose SHA-256 is recorded
separately (14.1 item 7) is, by name: `rule_id`, `trials`, `execution_order`, `monitor`, `hierarchy`,
`eligibility_rule`, `tie_rule`, `enclosure`, `coin`, `seed_rule`, `roster.strata`, `roster.exclusion_rules`,
`roster.pairing`, `roster.n_pairs_rule`, `design_seed_base`, `execution.max_attempts`, `execution.auto_abort`,
`plumbing_fail_conditions` and `integrity_label_rule` - and nothing else, so pinning an operational `null` after the
freeze cannot change it.

```json
{
  "experiment": "live_ab",
  "protocol_version": "v3-nm-guarded",
  "rule_id": "nm_guarded_v3",
  "adopts": {"guidance_file": "reviews/arxiv_live_design_guidance.md",
             "guidance_sha256": "a71965986165d56915a557a1a43998d9eb76a4e800dba670281c93720037ad1b"},

  "trials": {
    "T4": {"trial_no": 4, "order": 1, "incumbent": {"workflow": "single_shot", "server": "coder"},
           "candidate": {"workflow": "single_shot", "server": "coder"}},
    "T2": {"trial_no": 2, "order": 2, "incumbent": {"workflow": "single_shot", "server": "coder"},
           "candidate": {"workflow": "self_test_repair", "server": "coder"}},
    "T1": {"trial_no": 1, "order": 3, "incumbent": {"workflow": "self_test_repair", "server": "coder"},
           "candidate": {"workflow": "single_shot", "server": "coder"}},
    "T3": {"trial_no": 3, "order": 4, "incumbent": {"workflow": "single_shot", "server": "coder"},
           "candidate": {"workflow": "single_shot", "server": "t3"},
           "label_suffix": "regime_specific_cross_process_gpu_sharing",
           "deferred_if": ["preflight_rule_failed"]}
  },
  "execution_order": ["T4", "T2", "T1", "T3"],
  "unconditional_execution": true,
  "alpha_not_reallocated_on_deferral": true,

  "monitor": {
    "construction": "winstats.normal_mixture_radius",
    "variance_process": "n",
    "alpha_program": 0.05, "alpha_trial": 0.0125, "alpha_gate": 0.00625,
    "rho": 100.0,
    "delta": 0.03,
    "exploratory_margins": [0.10, 0.15], "exploratory_margins_decide": false,
    "n_min": 100,
    "n_max": null,
    "prefix": "current_full_enrolled",
    "evaluation_triggers": ["pair_enrolled", "episode_revealed", "call_raises_ell", "resume"],
    "non_triggering_events": ["metrics_scrape", "server_health", "server_started", "server_down",
                              "server_restarted", "anchor", "anchor_receipt", "anchor_failed",
                              "program_chain_event"],
    "drain_update_trigger": "drain",
    "clip": [-1.0, 1.0],
    "retention": false, "running_intersection": false, "prefix_envelope": false,
    "maximize_over_prefixes": false,
    "harm_tail": "hierarchy_upper_only",
    "decision_order": ["harm_keep_incumbent", "deploy_candidate"],
    "deploy_if": "L_h_gt_0_and_L_s_gt_minus_delta_at_same_prefix",
    "harm_if": "U_h_lt_0",
    "betting_in_decision_path": false,
    "betting_readout": {"when": "after_trial_end", "input": "final_complete_scores_only",
                        "error_control_claim": false},
    "winstats_sha256": "56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69",
    "reference_rule_sha256": null,
    "shadow_reference_every_evaluation": true
  },

  "hierarchy": [
    {"name": "success", "field": "success",   "higher_better": true,
     "absolute_tolerance": 0.0, "relative_tolerance": 0.0},
    {"name": "cost",    "field": "latency_s", "higher_better": false,
     "absolute_tolerance": 0.0, "relative_tolerance": 0.05}
  ],
  "eligibility_rule": "lower_tiers_require_both_success",
  "tie_rule": "strict_gt_tolerance_so_exact_equality_is_a_tie",

  "enclosure": {
    "start": [-1.0, 1.0],
    "success_formula": "sA_low_minus_sB_high__sA_high_minus_sB_low",
    "cost_certificate": "(1 - 0.05) * ell > L_r + 1e-9",
    "certificate_constant": 0.95,
    "absence_of_failure_is_not_success": true,
    "elapsed_cost_lower_bound_requires_monotonicity": true,
    "collapse_only_on_final_certificate": true,
    "collapse_cases": ["both_episodes_revealed", "enumeration_leaves_one_feasible_value"],
    "clock_equivalence_tolerance_ms": 1
  },

  "roster": {
    "sources": {"mbpp_sanitized": {"bytes": 255053, "sha256": "ca95deaa9a01ef0a6f439f88bcf0dd3db3563d22f22aad6cae04ebb9a8d8c8e9",
                                   "revision": "f82046ba5aabbbb427dbfd38a254d26bff08b533"},
                "humaneval":      {"bytes": 44877,  "sha256": "b796127e635a67f93fb35c04f4cb03cf06f38c8072ee7cee8833d7bee06979ef",
                                   "revision": "463c980b59e818ace59f6f9803cd92c749ceae61"},
                "mbpp_full":      {"bytes": 563743, "sha256": "ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f",
                                   "revision": "f82046ba5aabbbb427dbfd38a254d26bff08b533"}},
    "strata": ["S1", "S2"],
    "pairing": "stratified_no_mixed_pair",
    "n_pairs_rule": "floor(n_S1 / 2) + floor(n_S2 / 2)",
    "exclusion_rules": ["out_of_design_smoke_task", "duplicate_prompt", "no_entry_point",
                        "reference_fails_verify", "reference_timeout", "unparsable"],
    "smoke_tasks": ["mbpp_full/39", "mbpp_full/122", "mbpp_full/522", "mbpp_full/547",
                    "mbpp_full/869", "mbpp_full/966"],
    "uid_pattern": "^(mbpp|mbpp_full|humaneval)/[0-9]+$",
    "n_S1": null, "n_S2": null, "n_total": null, "n_pairs": null,
    "roster_sha256": null, "task_content_sha256": null
  },
  "design_seed_base": 60260919,

  "coin": {"source": "os.urandom(8)", "bit": "byte0&1", "raw_hex_logged": true,
           "map": "1->candidate_at_position_1", "unit": "pre_enrolled_pair",
           "binding_on_resume": "every_chain_valid_line", "never_redrawn": true,
           "selftest": {"n": 10000, "lo": 4850, "hi": 5150}},

  "seed_rule": {"source": "os.urandom(4)", "mask": "0x7FFFFFFE", "low_bit": "worker_index",
                "forbidden": ["0xFFFFFFFF"], "unique_within_worker_half": true,
                "unique_across_program": true, "logged_before_post": true,
                "duplicate_is": "logged_defect_no_outcome_effect"},

  "servers": {
    "coder": {"port": 8091, "alias": "qwen2.5-coder-7b-instruct-q4km",
              "hf_repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
              "hf_revision": "13fb94bfda8c8cf22497dc57b78f391a9acb426a",
              "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "bytes": 4683073536,
              "sha256_expected": "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c",
              "sha256_recomputed": null, "license": "apache-2.0", "license_evidence_sha256": null},
    "t3":    {"port": 8092, "alias": "t3-candidate",
              "hf_repo": "ibm-granite/granite-3.3-8b-instruct-GGUF",
              "hf_revision": "e40e9dd739c7be00fa965c16ce167088190ce114",
              "file_rule": "exactly_one_non_split_Q4_K_M",
              "file": "granite-3.3-8b-instruct-Q4_K_M.gguf", "bytes": 4942873344,
              "sha256_expected": "77bcee066a76dcdd10d0d123c87e32c8ec2c74e31b6ffd87ebee49c9ac215dca",
              "sha256_recomputed": null, "license": "apache-2.0", "license_evidence_sha256": null,
              "fallback": "none_T3_deferred"}
  },
  "llama_cpp": {"commit": "4fea119de30f6a923992780f6fd5ccb0bee5d47d",
                "build_flags_sha256": null, "serving_manifest_sha256": null},
  "llama_args": ["-np", "2", "-c", "16384", "--no-kv-unified", "-ngl", "99", "--jinja", "--metrics",
                 "--no-context-shift", "--offline", "--no-cache-prompt", "--cache-ram", "0",
                 "--slot-prompt-similarity", "0.0", "--host", "127.0.0.1", "--log-timestamps"],
  "receipt": {"golden_props_sha256": {"coder": null, "t3": null},
              "golden_generation_settings_sha256": {"coder": null, "t3": null},
              "mask": ["seed"], "float_tolerance": 1e-06,
              "assert_cache_n_zero": true, "assert_tokens_cached_zero": true,
              "assert_model_equals_alias": true,
              "assert_props_reports_slot_prompt_similarity_zero": true},

  "sampling": {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "typical_p": 1.0,
               "repeat_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
               "mirostat": 0, "max_tokens": 1024, "cache_prompt": false, "stream": false,
               "verbose": true},

  "execution": {
    "workers": 2,
    "process_model": "one_os_process_per_episode",
    "worker_index_rule": "slot_index_position1_to_slot0",
    "randomized_phase_schedule": "pair_synchronous",
    "post_decision_schedule": "work_conserving",
    "poll_interval_ms": 50,
    "request_timeout_s": null, "request_timeout_rule": "max(180, 30*ceil(4*c_max/30))",
    "max_connection_retries": 2, "retry_backoff_rule": "min(2*(k+1),10)",
    "server_recovery_s": 180, "max_recovery_waits_per_call": 1,
    "sandbox_timeout_s": 10.0, "max_lock_wait_s": 120,
    "episode_hard_cap_rule": "4*(3*request_timeout_s + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60",
    "episode_hard_cap_s": null,
    "episode_hard_cap_is_computed_never_typed": true,
    "max_attempts": 1,
    "hard_cap_outcome": "terminal_failure",
    "interruption_outcome": "terminal_failure_unless_orphan_checks_pass",
    "unstarted_assigned_arrival": "dispatched_on_resume_started_after_resume",
    "health_poll_s": 5, "health_failures_to_down": 3,
    "quiescent_scrape_every_arrivals": 50,
    "metrics_timeout_s": 5, "metrics_tries": 3,
    "worktree_check_s": 60,
    "auto_abort": {"consecutive_infrastructure_failures": 10, "counted_in": "reveal_order"}
  },

  "sandbox": {"timeout_s": 10.0, "cpu_s": 10, "output_cap_bytes": 65536,
              "mem_bytes_requested_not_enforced_on_macos": 2147483648,
              "tmpdir": "<TMP>/labsbx", "host_wide_execution_lock": true,
              "profile_sha256": null, "containment_probe_sha256": null},
  "max_repair_rounds": 2,

  "anchor": {"branch": "session60/live-ab-anchors", "issue": 11, "comments_per_trial": 3,
             "comment_triggers": ["trial_started", "decision", "trial_ended"],
             "push_triggers": ["trial_started", "every_25_completed_pairs", "decision",
                               "trial_paused", "trial_resumed", "refreeze_authorization",
                               "trial_ended", "trial_aborted", "operator_action", "program_paused",
                               "program_resumed", "preflight_refused", "plumbing_verdict_fail",
                               "erratum", "chain_unreadable"],
             "blocking": ["trial_started", "decision", "trial_paused", "trial_resumed",
                          "refreeze_authorization", "trial_ended", "trial_aborted",
                          "operator_action", "program_paused", "program_resumed",
                          "preflight_refused", "plumbing_verdict_fail", "erratum",
                          "chain_unreadable"],
             "blocking_wait_minutes": 30, "force_push": false, "timestamp_authority": false,
             "publish_segments_at": ["decision", "trial_ended", "trial_aborted"],
             "sandwich_tolerance_s": 30, "posting_latency_p95_s": null, "gap_report_s": 5},

  "integrity_label_rule": {"coin_adjacent_events": 1, "sandwich_violations": 1,
                           "pairs_with_terminal_failure": 3,
                           "coin_adjacency_scope": "randomized_phase_only"},
  "pause_thresholds": {"battery_percent": 20, "free_disk_gb": 5},
  "refreeze": {"scope": ["reporting_code"]},
  "plumbing_fail_conditions": {
    "reporting_code": ["receipt_mismatch_count_gt_0", "reconciliation_defect_count_gt_0",
                       "completeness_check_fail_verifier_bookkeeping"],
    "decision_defining": ["chain_check_fail", "reference_rule_disagreement",
                          "t4_payload_non_identity"],
    "repeat_same_condition_stops_program": true},
  "prefreeze": {"format_conformance_min": 9,
                "calibration_plan": {"repetitions": 5, "smoke_tasks": 6, "workflows": 2,
                                     "models": 2, "concurrency_levels": 2, "episodes": 240},
                "side_by_side_compression_C": {"T1": null, "T2": null, "T3": null, "T4": null}},
  "hardware_allowlist": null, "environment_lock_sha256": null
}
```

## Appendix C. Harness modules and the test plan (normative for the implementer)

New code under `experiments/live_ab/` with the prefix `lab_`. **This list is the module set of
`ARCHITECTURE_FINAL.md` §2.1 and agrees with it name for name:** `lab_common` (paths, tokens, canonical JSON,
hashing, exception taxonomy, freeze bundle), `lab_eventlog` (segmented chain and the schema validator of 12.2; the
**program chain is the same class** with `chain_id = "_program"`, not a separate module), `lab_verify_log`,
**`lab_reference_rule`** (the second code path of 8.9: standard library, numpy and `src/winstats.py` only, importing
no `lab_*` module at all; frozen, never amendable), `lab_data` (roster, sweep under load, exclusions, task-content
hash), `lab_design` (arrival orders, stratified, no mixed pair), `lab_coin`, `lab_monitor`, `lab_enclosure`,
`lab_client` (spooling client, drawn seeds with the worker-index partition, golden-object receipt comparison; same
interface as the pilot's client so that `agent.py` stays byte-identical), `lab_server` (start, identity checks,
supervise, `/metrics`), `lab_mock_server`, `lab_worker` (one process per episode, spool with `job_accepted`,
execution-lock wrapper), `lab_orchestrator` (single chain writer, spool ingestion, pair-synchronous scheduler,
enclosure bookkeeping, the shadow call into `lab_reference_rule`, the 60-second worktree check, blocking points,
switch, exposure ledger, resume), `lab_anchor` (anchor branch, spool, receipts, **the identifier scanner
`scan_for_identifiers` of 15.2**, publication), `build_live_ab_results`, `dryrun_live_ab`, `config.json`, and the six
test files `tests_lab_chain`, `tests_lab_isolation`, `tests_lab_design`, `tests_lab_stats`, `tests_lab_serving`,
`tests_lab_e2e`. Reused unchanged and hashed:
`local_stream/{agent,sandbox,verify,data,common}.py`, helper functions of `run_stream.py`, `src/winstats.py`.
**Not reused:** `local_stream/design.py`, the sequential main loop and monitor table of `run_stream.py`, the pilot's
HTTP client, the rewritable manifest.

**Tests without any model (all must pass before the freeze).**

*Guidance item 9 tests (named explicitly, because the guidance names them):*
- **enrollment/reveal reorder invariance**: for any admissible permutation of a set of reveal-order events, the
  enrollment-indexed records, both enclosure sums and both band endpoints **after the whole set has been applied** are
  identical, and the decision (kind and prefix) is identical. The **intermediate** sequence of looks is order-dependent
  by construction (a certificate that binds at a call event produces a look that a different order produces later) and
  is **not** compared; what the guidance asks for is the state, and that is what is asserted (8.9 gives the reason the
  decision prefix is nevertheless order-insensitive);
- **repeated-update idempotence**: applying any reveal twice changes nothing (7.3 item 6);
- **enclosure containment**: for randomized traces, every recorded enclosure contains the ultimately revealed score,
  and no enclosure widens (7.5 item 6);
- **equality ties**: exact threshold equality at either tier scores 0, at `tol = 0` and at `tol = 0.05`;
- **joint failures**: both episodes failing scores `Z = 0` and `D = 0`, with tier 1 ineligible;
- **switch-phase exclusion**: no follow-up-cohort arrival ever enters a score, a band, `n`, or the exposure figures of
  the randomized phase; and **a quiescent `metrics_scrape` in the follow-up cohort produces no `monitor_update` and
  the verifier passes on that chain**.

*Chain and schema:* tamper, deletion, reorder, wrong genesis, segment boundaries; torn region spanning several lines;
kill after write and before fsync return (the coin line stays binding); unopenable chain closed through the program
chain; the validator rejects free text, a foreign commit id and an untokenized absolute path in **every** event type,
and **accepts** `trial_started` (finding N12) and **accepts `pair_enrolled` with roster uids while rejecting a uid
that is not in `roster.json`** (form (e) of 12.2).

*Program chain:* a `refreeze_authorization` between two trials is accepted and is the only accepted drift; a
`plumbing_fail` pause and its resume; an `invocation_refused` before a trial's seq 0; a "not started" trial; a
`chain_unreadable` closure; the verifier check that the program chain orders the four trials.

*Coin:* fsync-before-dispatch spy; patched `os.urandom`; one coin per pair; none after a decision; none before the
start receipt; coin of pair `i+1` only after both reveals **and the evaluation** of pair `i`; re-enrollment after a
crash between `pair_enrolled` and `coin_drawn`.

*Seeds:* drawn before the POST, logged in spool and chain, low bit equals the worker index, unique within a worker's
half, never `0xFFFFFFFF`, independent of a patched coin stream; a forced duplicate is logged and changes no outcome.

*Monitor and reference rule:* equality with `winstats` within 1e-9 and exact counts; `n_min = 100`; no decision at
`n = 0`; the same-prefix conjunction; harm-first order; **no retention** (a path that crosses, dips and stays below
must not decide later on the old crossing); **no running intersection anywhere in the band code**; **no prefix
envelope and no maximization over prefixes** (a test asserts the rule reads only `n = N(t)`); the denominator is the
number of enrolled pairs and never the number completed; action labels carry the margin; import isolation (verifier,
builder and reference rule import nothing from `lab_monitor`, `lab_enclosure`, `lab_orchestrator`, `lab_worker`;
scores only through `winstats.compare`); injected live-monitor defects (sign slip, swapped counts, wrong denominator)
are caught by the **shadow** check at the first evaluation at which they change anything, yield a pause, and are
caught by the replay as `LIVE_DECISION_INVALID`; **the evaluation-trigger set of 8.3 is exactly the implemented one**
(a `metrics_scrape` produces no look; a `pair_enrolled`, an `episode_revealed`, a resume and every call event that
raises `ell` each produce exactly one `monitor_update`); and **a certificate that binds at an `llm_response` produces
a look and can decide**, with the partner episode still pending.

*Enclosures:* the 0.95 certificate at `tol = 0.05`, including the boundary case; the success formula in all four
resolution states; "absence of failure is not success" (a trace with all calls returned and self-tests passed still has
`s_low = 0`); terminal failures; `compare` is never called with a partial outcome.

*Scheduler and switch* with scripted latencies: position 2 revealed first; the decision at a reveal; a decision at an
event with one pair unresolved (enclosure path); blocking decision receipt before the first post-switch dispatch;
horizon exhaustion; leftovers; quiescent scrapes; in-flight exposure logged.

*Resume:* kill points after each of `pair_enrolled`, `coin_drawn`, **before any dispatch (row 11d)**, **after position
1's `job_accepted` and before position 2's dispatch (row 11e)**, `job_accepted`, first spool request line, response
line, record file written, spool terminal line, first `episode_revealed`, second `episode_revealed` (before the
evaluation), `monitor_update`, `decision`, the decision anchor, `traffic_switch`, and inside the follow-up cohort.
After each: verifier PASS, never a second coin, never a second reveal, never a re-run, orphan accepted only when all
checks pass, orphan rejection logged, decision on resume, harness-defect closure when pairs exist beyond `n*`; double
resume idempotent; two orchestrators refused.

*Failure rules:* every row of 6.4 by fault injection, including rows 11c, 11d, 11e, 18, 19, 20; hard cap and worker
death are terminal; a graceful stop drains; the ten-failure abort is deterministic and counts in reveal order;
`infra_flag` equals the closed list exactly.

*Client:* exactly one terminal spool line per request; the golden-object comparison catches a changed temperature, an
unknown key, a missing key and a nonzero `cache_n`; no estimation path exists.

*Accounting:* per-pair residual exactly 0 against mock counters; defect raised otherwise; scrapes before and after
failed tries; the smoke completion in the identity; a scrape that hangs times out and enrollment continues.

*Sandbox:* every `run_program` call path goes through the execution-lock wrapper; two workers never execute
concurrently; reused pilot test classes; the containment-probe harness.

*Anchoring:* a forbidden pattern written into a mock segment withholds that segment while anchors continue;
`anchor_failed(tree_state)` on a foreign staged file or a wrong branch maps to the `anchor_unavailable` pause; the
sandwich audit detects an inserted gap and a falsified clock and does **not** flag a gap covered by a 10 s sandbox run;
the prefix comparison uses the first `segment bytes` only; the anchor spool is the source and the orchestrator is the
writer.

*T4:* job payloads byte-identical apart from the label; no label-specific seed or worker advantage.

*Freeze:* bundle drift refusal; acceptance of exactly the chained re-freeze authorizations; refusal of a changed
reference rule or coin; refusal if `src/winstats.py` is not at `56955ce0...`; builder isolation; every path named in a
mapping exists in the tree; **`lab_common.rule_block_sha256(config)` equals the rule-block hash computed from the
frozen tables of this protocol's own text** (audit B1: the two documents cannot be frozen in disagreement about the
hierarchy, the tolerance, the certificate constant, the coin or the seed rule); the `config.json` block of Appendix B
and the block of `ARCHITECTURE_FINAL.md` §6.1 are byte-identical; **and the constant-coverage test** (finding N22),
narrowed so that it can pass: *every numeric constant appearing in the rule block (sections 6.2, 6.3, 6.4, 7, 8) and
in the frozen parameter tables of 5.6, 8.5, 12.6 and 14.3 appears in `config.json` with the same value, and every such
value in `config.json` appears in this text; values the harness derives from a formula (`request_timeout_s`,
`episode_hard_cap_s`) are compared against the formula's output and never against a typed literal; generated tables
(the radius tables) are compared against `radius_table.csv`.*

*Working location:* an out-of-band file swap during a dry run (a freeze-bundle file, a closed segment or a copy of
`src/winstats.py` changed under the running orchestrator) **pauses the trial with `worktree_drift` within
`worktree_check_s`, produces no 12.6 editing finding against the operator, and resumes only after the digests match**
(6.4 row 27); a wrong `HEAD` branch or worktree path at invocation start is `preflight_refused(worktree_identity)`.

*Clocks:* the preflight assertion of 7.5 item 4 refuses when `perf_counter` and `monotonic` differ by more than
`clock_equivalence_tolerance_ms` over 10 s.

**Mock-server dry runs** (MOCK banner on every derived file): a T1-like abstention at the horizon; a wide-margin deploy
with switch (mock config only); a T2-like harm stop at `n_min`; A/A wiring; chaos kills of workers, mock server and
orchestrator; then the real-server dress rehearsal (5.8 item 6) and the anchor drill (12.4 item 10).

**Deliverables that do not exist yet and are freeze conditions** (finding N22): the run book of 14.7; the template of
the derivation file of Appendix A; the constant-coverage test above.
## Appendix D. Disposition of the critic findings N1-N22

"Closed by" cites the section of this protocol that contains the rule. Every HIGH and MEDIUM finding is closed by
text; the LOW ones are closed as well, except where revision 2 removed the mechanism the finding was about.

| id | sev | the gap | closed by | the rule adopted |
|---|---|---|---|---|
| **N1** | HIGH | between trials there is no chain, so `refreeze_authorization`, `invocation_refused`, "not started" and the undefined "closing stub" have nowhere to live | **12.1**, 6.4 rows 21-25, 14.4 item 2 | one **program chain** `results/live_ab/_program/events/seg_<k>.jsonl`, genesis from the freeze-bundle hash under the single genesis rule of 12.1, first event `program_opened` carrying the closed `_prefreeze` head; it receives `trial_opened`/`trial_closed`, every re-freeze authorization, every refusal, every "not started" and every `chain_unreadable` closure. `trial_started` quotes the **program-chain head**. Verifier check: the program chain orders the four trials and contains every authorization any `invocation_started` relied on. |
| **N2** | HIGH | no rule for a plumbing-verifier FAIL between trials | **6.4 rows 22a and 22b**, 14.6 | reason code **`plumbing_fail`** with **two** closed machine-checkable condition lists, because the single list of the earlier draft prescribed a harness-only re-freeze for conditions that are defects of decision-defining code (audit M5). **List A** (receipt mismatches > 0, reconciliation defects > 0, a completeness FAIL caused by the verifier's own bookkeeping) keeps the action "program paused in the program chain; harness-only re-freeze of **reporting code only**; next trial", and a **second occurrence with the same condition id stops the program**. **List B** (chain check FAIL, reference-rule disagreement, T4 payload non-identity) has the single action "**6.4 row 24 applies to the affected trial; program paused; continuation requires a new protocol version**". A `plumbing_fail` may never be closed by changing anything in the 14.3 list. The results that do **not** stop the program are listed by name. |
| **N3** | HIGH | verifier, builder and reference rule can never change, and a defect in one has no exit | **14.3**, 6.4 rows 23-24, 12.6 item 4 | the closed list is **split**. *Decision-defining code* is immutable; a proven defect drops claims 2-5 and 7 for every affected trial and a corrected rule is descriptive only. *Reporting code* (verifier, builder, scanner) gets a **versioned erratum** through the program chain with both outputs deposited, the table list frozen, and the rule that no erratum can alter a decision. The false-FAIL case the finding named is also removed: a gap covered by a sandbox execution or a `/metrics` scrape is not reported as an unexplained gap. |
| **N4** | HIGH | a binding coin whose attempt never started has no outcome; the natural reading is a cost-free steering device | **5.1**, **6.4 rows 11c/11d/11e**, 12.3, 12.6, 14.5, Appendix C | "**the attempt started**" is defined by evidence the worker owns: a **fsynced `job_accepted` spool line** written before `run_episode`. An assigned arrival **without** `job_accepted` is dispatched on resume as its one and only attempt, `started_after_resume: true`, with `partner_concurrent` recorded and the solo/concurrent regime fed into S-int. An arrival **with** `job_accepted` follows row 11. Both kill points (and the position-1/position-2 asymmetry) are in the resume test list, and the orphan check matches against `job_accepted`, not the non-durable `episode_started`. |
| **N5** | MED | `latency_s` and `ell` undefined when nothing was spooled; `compare` would raise | **6.1**, **6.4 row 18** | `latency_s = 0.0`, `completion_tokens = 0`, `usage_known: false`. All outcome fields are finite by construction, so `compare` cannot raise; the case is in the fault-injection tests. |
| **N6** | MED | seed uniqueness unenforceable across two uncoordinated workers; a collision has no consequence | **5.5**, **6.4 row 19** | the seed space is **partitioned by the low bit = worker index**, so a cross-worker collision is impossible; each worker loads the program's used set at start and checks its own half. A detected duplicate is a logged **reporting defect with no effect on any outcome**; it never refuses, pauses or aborts. |
| **N7** | HIGH | two irreversible auto-aborts hang on server behaviour the pre-freeze phase does not exercise; the prompt cache is on by default | **2.2**, **13.2**, 5.8 item 6 | (i) **structural**: `--no-cache-prompt`, `--cache-ram 0`, `--slot-prompt-similarity 0.0` in the frozen launch line and checked in the golden `/props`; (ii) **empirical**: the frozen receipt comparison must pass on **100%** of the dress-rehearsal responses, which must include `self_test_repair` episodes with repair rounds on both slots and two consecutive identical-prefix episodes on one slot. Otherwise no freeze. |
| **N8** | HIGH | T4-first cannot find `self_test_repair` defects, and the only end-to-end rehearsal is against the mock server | **5.8 item 6**, 14.6 | a **real-server dress rehearsal on out-of-design tasks only**, `phase = REHEARSAL`, chained under `_prefreeze`: full production path, both workflows in both orientations, both models, pair-synchronous scheduling, real anchors on a drill branch, a rehearsal-only config with small `n_min` and wide margin so a decision, its blocking receipt, the switch and a post-switch phase occur; injected orchestrator kill, worker kill, server kill and pause/resume; then verifier PASS and a builder run. Rehearsal outcomes are never used and never reported as observations. Trial order stays T4, T2, T1, T3. |
| **N9** | MED | the counter identities have no failure consequence and a scrape can block enrollment | **6.4 row 20**, 13.1 | every scrape: **5 s timeout, at most 3 tries**; on exhaustion the window is `unreconciled` and **enrollment continues**; a start-identity violation is a **`reconciliation_defect`**, not a refusal; the exact token-level identity is established in the rehearsal and, if it does not hold exactly, the frozen wording is "residual reported". |
| **N10** | HIGH | the planning numbers the root would read are a latent model, and "R4's simulator" cannot do what was asked | **11.1-11.5** | the **decisive** planning object is now the **analytic reachability table** (11.3), which is model-free. P5 and P6 are superseded entirely and no number from them appears. The **extended replay** is specified in full (11.5: outcome model, cost resampling, cells, replicate counts, Wilson intervals, exhaustive output, script/seed/output hash) and is mandatory before the freeze, with the explicit rule that it cannot change any parameter. |
| **N11** | HIGH | the protocol hash the root is consulted on is not the hash that is frozen | **14.1 items 6-7** | the consultation is gone (the root answered; its answer is the guidance file, whose hash is recorded). The two durable parts of the finding are kept: a **rule-block hash** over sections 6.2-6.4, 7, 8 and the statistical keys of `config.json`, recorded separately so any later erratum must show it unchanged; and the **`winstats` pin**: if `src/winstats.py` is not at `56955ce0...` when the bundle is assembled, **the freeze is refused**. |
| **N12** | MED | the schema rule ("no free text, no commit id") rejects `trial_started` - and, as the audit found (M13), also `pair_enrolled`, whose `task_uids` are none of the four declared forms | **12.2** | "free text" is defined **operationally**: every string field is an enum value, a fixed-length hex digest, a token plus repository-relative path, a numeric string or an ISO-8601 instant, **or a task uid matching `^(mbpp|mbpp_full|humaneval)/[0-9]+$` that is present in `roster.json`** (form (e)). "Commit id" in the prohibition means a **foreign** repository's; this repository's own ids are permitted in `anchor` and `anchor_receipt` bodies. The **config is embedded by hash only**, with `config.json` as a tracked sibling; descriptive labels live there, not in the chain. A test asserts the validator accepts `trial_started`. |
| **N13** | MED | who writes anchor events, and where the comment goes, is undefined | **12.4 items 1-3**, 6.4 row 26 | the anchor process owns an **fsynced spool** like a worker; the **orchestrator remains the only chain writer** and appends `anchor`, `anchor_receipt`, `anchor_failed`. The comment target is chosen: **issue #11**, exactly three comments per trial, and that is the path the drill exercises. `anchor_failed(tree_state)` on a blocking anchor maps to `trial_paused(anchor_unavailable)`. |
| **N14** | MED | the counter-semantics test does not exercise the production path | **5.8 item 2** | the test runs on a **non-streamed** POST with a short client timeout, exactly as a trial request dies; the streamed probe is kept only to learn how many tokens had been generated at the cut. |
| **N15** | MED | the hard cap is not "by construction" above the longest legitimate attempt; the formula omits lock waits | **5.6** | a call may wait for **at most one** supervised restart (`max_recovery_waits_per_call = 1`); lock waits are bounded (`max_lock_wait_s = 120`) and are **in** the formula; the cap is recomputed as `4*(3*T + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60` (**3,354 s** at `T = 180`; the 3,306 of the earlier draft was an arithmetic slip, audit M12, and the value is now computed by the harness from the formula and never typed); and the false sentence is replaced by "**the cap can bind on a legitimate `self_test_repair` attempt only after at least four failed tries and one server restart; how often it bound is reported by arm**". |
| **N16** | MED | thresholds that label or end a trial were amendable | **14.3**, third row of the non-amendable table | `integrity_label_rule`, `auto_abort.consecutive_...= 10`, `sandwich_tolerance_s`, `posting_latency_p95_s`, `gap_report_s`, `blocking_wait_minutes`, the pause thresholds, the `/health` thresholds, the coin self-test limits and the format-conformance minimum are named and non-amendable. |
| **N17** | MED | `max_attempts = 1` leaves a forced-failure device with a few free uses; S-int is only descriptive | **6.4**, 16 item 9, Appendix E | frozen wording: whenever a row 10/10b/11/11c/11d/11e episode lies at or before `tau`, **the decision sentence itself carries** "under S-int the rule also crossed at pair n / did not cross", and the Appendix E templates contain that clause. The device is disclosed, not denied. |
| **N18** | LOW | "agreement" was defined only on the decision | **8.9** | **any** mismatch at **any** evaluation - counts, enclosures, statistics or action - is listed in the report; only a mismatch in the **kind or prefix of the decision** changes the result. |
| **N19** | MED | the reference rule runs only on resume and after the trial, so a silent live defect is found too late | **8.9**, Appendix C, `ARCHITECTURE_FINAL.md` 3.8b | the reference rule is a **separate module** (`lab_reference_rule.py`, a different implementer group, stdlib + numpy + `winstats` only, importing nothing from `lab_monitor` or `lab_enclosure`) evaluated as a **shadow at every evaluation of 8.3**; any difference pauses the trial (`monitor_mismatch`) **before any decision is acted on**, and the shadow's values and mismatch flag are written into every `monitor_update`. The audit reopened this finding because the implementation contract had collapsed the two code paths into one (**B2**); it is closed by making the second path real and by requiring three injected defects to be caught by the shadow. |
| **N20** | LOW | wording slips against the protocol's own lists | **1.5 items 4, 5, 19**, 5.5 | "guarded" never appears without the margin (1.5 item 19). "seeds are drawn **independently of** the coin" replaces "without access to the coin" (5.5). The **"harm gate" clause is superseded**: the root's own guidance and revision 2 use "HARM/RETAIN", so the word `harm` is the frozen name of the prespecified tail and appears in the action label `HARM_RETAIN_INCUMBENT`; what stays forbidden is the *interpretation* - success harm, safety harm, approval of the incumbent (1.5 item 5). |
| **N21** | LOW | small unmapped or undefined items | various | `thermal`: **removed** with the probe (14.6). "ten consecutive revealed arrivals": **reveal order**, stated (6.4). Integrity label: applies to the randomized phase **and** the follow-up cohort, counted separately (12.6). Timestamp-authority failure: **moot**, no authority (12.4). OS build change: `kern.boottime` hash and the OS build are in the invocation drift list (12.2 #2), so a change is a refusal unless a chained authorization covers it. Calibration size: **fixed plan**, 5 x 6 x 2 x 2 x 2 = 240 calls (5.8 item 3). T3 "compression": **defined** as `C` (5.8 item 4). `episode_started` non-durable: the orphan check now matches `job_accepted` (12.3). Sandwich tolerance second term: `posting_latency_p95_s`, measured in the drill and pinned (12.6 item 4, Appendix A). |
| **N22** | LOW | deliverables the protocol relies on that do not exist yet | Appendix C, last paragraph | the issue text with RA/RB wording is **moot** (no consultation). Remaining and listed as freeze conditions: the **run book** (14.7), the **derivation-file template** (Appendix A), and a **test that every numeric constant in this protocol's text appears in `config.json` with the same value**. |

**Findings the critic listed as PARTIAL against the three audits** (S-F1, C-F2, P14 through N1-N3; C-F8 through N10;
C-F12 through N14) are closed by the rows above. **R2 checklist items that remained open** are closed as follows:
item 32 and item 42 are **declared deviations** with named substitutes (13.1); item 50 stays a declared deviation and
now depends on a production-path test (N14); item 59 is met by the 100%-pass freeze condition (N7); item 87 (anonymous
variant) is **withdrawn** (revision 1, C26); item 106's phrase appears in 2.2 and claim 1; item 41 now works between
trials (N1); item 121 is met by the freeze comment on issue #11 carrying the bundle hash; item 6 and item 26 remain
argued deviations, labelled as such.

## Appendix E. Manuscript sentences the trials could add, one per outcome

Templates. Brackets are filled from the governing report; **nothing else may be derived**.

**Retained in every case, without exception:** "These are laboratory trials on public benchmark tasks with open-weight
models on one laptop; design parameters were chosen with knowledge of a pilot on the same tasks on a different serving
stack; they provide feasibility evidence, not operational latency savings, measured operational savings or a live
deployment. The deploy route of this program was declared **a pre-specified near-certain abstention** at this horizon
before collection; the four trials reuse one task roster, so they are not independent replicates; and the cost tier is
measured under the two arm-asymmetric mechanisms named in the protocol (within-pair duration asymmetry and the
execution-lock transfer)."

- **T1, the expected outcome (composite met, guardrail refuses, abstention at the horizon):**
  "In a prospectively frozen, externally timestamped A/B trial with OS-entropy pair randomization (operator-attested),
  the prespecified normal-mixture rule first met its hierarchy condition `L_h > 0` at enrolled pair [n0] of [N_P] and
  held it through the horizon, while the prespecified success guardrail at margin 0.03 was never met (`L_s` = [value]
  at [N_P] against the threshold -0.03). The trial therefore ended in abstention on the deploy route, which was
  declared a pre-specified near-certain abstention before collection: at `alpha_gate` = 0.00625 and `rho` = 100 the
  guardrail requires an observed running success difference above `r(n) - 0.03` (`+0.1280` at the horizon), needs
  17,097 pairs at a zero observed success difference, and the roster provides at most 568. This is the specified
  behaviour of a guarded rule at a margin this horizon was not expected to reach; it is not evidence that the
  workflows differ or are equivalent. Cost was measured side by side; the measured compression for this contrast was
  [C], and `sandbox_lock_wait_s` by arm was [values].
  [N17 clause where applicable: Under the prespecified S-int sensitivity the rule [also met / did not meet] the
  hierarchy condition at pair [n].] The per-trial error bound is 0.0125 and the program bound over four trials is
  0.05."
- **T1, DEPLOY (not expected; if it nevertheless occurred):** "... the rule met both conditions at enrolled pair [tau],
  which requires an observed success difference above [r(tau) - 0.03]; randomization stopped and the remaining
  [2M + leftovers] arrivals ran under `single_shot`. The margin 0.03 is the root's prespecified value and was not
  chosen for certifiability. This outcome was declared before collection to be a near-certain abstention, about 8.5
  paired standard errors from the pilot value; **it was never declared impossible**, and it is reported here under the
  same error bound (0.0125) as any other decision of this trial."
- **T1, HARM_RETAIN:** reported as observed, with the sentence that it contradicts the pilot direction.
- **T2, HARM_RETAIN (the expected outcome):** "With the roles exchanged, the prespecified rule's hierarchy upper
  endpoint fell below 0 at enrolled pair [tau] (`U_h` = [value]); randomization stopped, every already enrolled pair
  was finished under its original assignment, the exact switch time was [t], and [M] pairs of the prespecified roster
  were not enrolled (`M` is determined by the roster length `N_P`; it is not a saving rate). The signal is carried by
  the cost tier and is a statement about the composite only: it is not success harm, not safety harm and not an
  approval of the incumbent. Cost was measured side by side (measured compression [C]; `sandbox_lock_wait_s` by arm
  [values]; under the S-lock read-out the hierarchy was [result]). T2 repeats the T1 contrast with the roles exchanged,
  on the same roster, and is not a second confirmation. [N17 clause where applicable.]"
- **T2, other:** reported as observed.
- **T3, any outcome:** "[decision or abstention] ... regime-specific: cost was measured as wall-clock latency while
  both models shared one GPU from two server processes (measured side-by-side compression [C]); [share]% of pairs were
  decided at the cost tier; the success-only composite gave [result]; prompts and the code extractor were developed on
  the incumbent's model family, and this contrast cannot separate ability from benchmark contamination."
  If deferred: "T3 was not run because [preflight rule k failed]; its 0.0125 allocation was not re-allocated."
- **T4:** "In one A/A control path no band crossed" or "one band crossed at pair [n], an event of probability at most
  0.0125 under the exact null; it is reported and was investigated, and the run was not discarded"; plus "T4 checks the
  coin path and label blindness only, and one A/A path establishes no false-decision rate and no equivalence".
- **The switch, wherever it is mentioned:** "The decision certifies a past enrollment-running target at the logged
  prefix. Post-switch single-arm traffic is an operational follow-up cohort, not additional pairs for the A/B
  estimator. A single switched trial does not identify causal resource or latency savings against continued A/B or
  against another stopping policy."
- **`LIVE_DECISION_INVALID`, aborted, integrity-qualified, chain-unreadable or not-started trials:** reported under
  those names; **no sentence from the list above is used for them**.

## Appendix F. Inputs of this revision (SHA-256 prefixes)

Binding inputs, repository: `reviews/arxiv_live_design_guidance.md`
`a71965986165d56915a557a1a43998d9eb76a4e800dba670281c93720037ad1b` (full digest);
`src/winstats.py` `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` (full digest);
`paper/theory.tex` `ddaebf17e6e9b72822ff945d37475bdb176cba37b27f78fee3c8505e1881445f` (full digest).
All three blobs are identical at `session60/live-ab` (`b3f1122`) and at root `main` (`1c3e9f3`); the digests, not the
branch names, are the citation. **Operational note, now closed:** during the writing of the v3 draft the shared
clone's `HEAD` moved from `session60/live-ab` to `main` through another session's work. Nothing in this protocol
depends on the working-tree branch, but a concurrent checkout or merge during a multi-hour trial could put an anchor
commit on the wrong branch or rewrite files under a running invocation. **This is no longer an open item.** The
coordinator decision C15 (one shared clone, no second clone) stands and is not reopened; the residual risk is closed
in the text by the two guards of 2.1: the identity assertion before every commit and at every invocation start
(12.4 item 2; `anchor_failed(tree_state)` -> `anchor_unavailable`, or `preflight_refused(worktree_identity)`), and the
60-second worktree-integrity check of **6.4 row 27** (`worktree_drift`), which is the only rule in this protocol that
can see a change made *between* those points and which explicitly forbids attributing it to the operator in 12.6.

Scratchpad inputs: `COORDINATOR_DECISIONS.md` `358d3708d488f92a`; `protocol_draft_v2.md` `ffd6791e5e8dc94f`;
`critic_v2.md` `f0fb97e566400676`; `audit_v1_statistics.md` `e13eda4d660645a2`; `audit_v1_provenance.md`
`b0917a62de03ddf2`; `audit_v1_claims.md` `8fafde1a1d18a64a`; `audit_response_v1.md` `2169d8cdfcc6ffa0`;
`R1_accepted_method.md` `07acd3a783cb976f`; `R2_constraints_checklist.md` `728c5a1c3fd35769`; `R3_harness_plan.md`
`fa51f7977db99995`; `R4_power_analysis.md` `2d1a4eaaec9afc2b`.

**Numbers recomputed for this protocol before it was written**, with `.venv/bin/python` against `src/winstats.py` at
the digest above and `results/local_stream/episodes_flat.csv` (SHA-256
`1237b82f99c5ea8ad1e319e0ec45873ba85a2ff13d670d508d78ae06547bd540`):

- the radius table and the `rho` sensitivity of 11.2;
- the reachability thresholds of 1.3 and 11.3 (17,097 at 0.03; 5,789 at 0.05; 1,378 at 0.10; 626 at 0.15; 372 at 0.20);
- the first-crossing table of 11.3;
- the pilot cross-task effect sizes of 1.3 under the frozen two-tier hierarchy (`Zbar = +0.4993`, `Dbar = 0.000000`,
  tier shares 0.3922 / 0.5316), and the three-tier check that reproduces R4's published 0.7090 / 0.0788 / 0.2122 and
  `NB = +0.4968` exactly;
- the correction of `r(92)` recorded in 1.3.

The model facts of 2.3 (Granite revision `e40e9dd7...`, 4,942,873,344 bytes, blob digest `77bcee06...`; Qwen
4,683,073,536 bytes, blob digest `509287f7...`) were read from the local Hugging Face cache; they are **expectations
verified by recomputation at preflight**, not yet facts of this protocol (Appendix A).

---

*Prepared and checked by AI agent sessions; not human peer review or author sign-off.*
