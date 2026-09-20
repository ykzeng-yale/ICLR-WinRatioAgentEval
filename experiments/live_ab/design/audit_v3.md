# audit_v3.md — adversarial audit of `protocol_v3.md` and `ARCHITECTURE.md` (live_ab)

Auditor: hostile root reviewer, session 60, 2026-09-19.
Read in full: `reviews/arxiv_live_design_guidance.md`, `protocol_v3.md` (2,602 lines), `ARCHITECTURE.md`
(2,046 lines, including all 25 `PROTOCOL-GAP` entries), `critic_v2.md` (N1-N22),
`COORDINATOR_DECISIONS.md` (revisions 1 and 2). Consulted read-only: `src/winstats.py`,
`experiments/local_stream/agent.py:215-265`, `results/local_stream/episodes_flat.csv`.
CPU checks with `.venv/bin/python` against `src/winstats.py`; every number quoted below was recomputed.
No git state change, no server, no model call, no download, nothing written outside `live_ab_design/`.

## VERDICT: **BLOCK**

Not "fix then freeze". Seven blockers, and six of them are cases where the two documents that are
*jointly* binding on the implementers state **different decision-defining rules**. `ARCHITECTURE.md`
declares itself "the only interface contract" for five engineers who do not talk to each other
(§0, line 4), and `protocol_v3.md` declares its sections 6.2-6.4, 7 and 8 a **rule block** with its own
hash that "can never be amended" (14.1 item 7, 14.3). Those two documents disagree on the hierarchy, on
the cost tolerance, on the enclosure certificate constant, on the seed rule, on the coin body, on the
look cadence, on the number of randomization units, and on whether the object that produces the normative
decision exists at all. A freeze bundle assembled from this pair would freeze a contradiction, and every
one of the contradictions falls inside the list that 14.3 makes **immutable** — i.e. inside the list whose
defects 6.4 row 24 says are "**not repairable**" and cost claims 2 to 5 and 7 for every affected trial.

What is *not* wrong, stated once so the rest of this file can be read as defect-only: every radius,
every reachability threshold, the `rho` sensitivity table, the first-crossing table, the alpha arithmetic
and every pilot effect size in `protocol_v3.md` §1.3, §11.2 and §11.3 reproduce **exactly** (section 2
below). The coverage-inheritance argument of 8.6 item 1 and the union-bound argument of 8.6 item 3 are
correct. The cost certificate of 7.5 item 5 is mathematically sound, and I could not construct a
containment counterexample against it (section 2.5). The A/A exactness claim `mu_i = 0` is correct
*given* a coupling the protocol never states (finding M8).

---

## 1. Compliance with the root guidance, clause by clause

Legend: **F** fully implemented, **P** partly, **N** not. Two columns, because `protocol_v3.md` and
`ARCHITECTURE.md` are both binding on execution and diverge.

| guidance item | protocol passage that implements it | protocol | architecture |
|---|---|---|---|
| **1.** one randomized orientation per pre-enrolled pair | 4.1 "**One fresh fair coin from OS entropy per PRE-ENROLLED pair**"; 4.2 code path (`pair_enrolled` durable, then `raw = os.urandom(8)`, then `coin_drawn` durable, "Only after that return may EITHER job of pair i be sent"); 3.4 "**Both positions of a pair are fixed before the orientation is randomized**"; 7.1 "**Matching by completion order is never used**"; 7.4 "**Primary target** ... the **enrollment-running symmetrized cross-arrival preference** `mubar_n` ... **Ordinary same-task preference is not identified by this design**" | **F** | **P** — `lab_design.arrival_order` (3.5) forms "at most one **'mixed'** pair [that] absorbs the two odd remainders", which is a pair across strata; protocol 3.4 pairs "**inside a stratum**" and sends leftovers to "the arrival numbers after `2 * N_P`". See **B5** |
| **2.** reveal order updates enrollment-indexed records | 7.3 items 1-8 ("A reveal-order event ... **updates the existing score enclosure of the pair at its own enrollment position** and nothing else"; "**never appends a new observation, never reorders, never drops**"; "The denominator is always `n` ... **never** the number completed"; "**At `n = 0` the full range `[-1, 1]` is displayed and no decision is possible**"); 5.2 "**Fixed policy, non-amendable**" + concurrent-load record; 7.2 "**The latent enrollment-order model**" | **P** — 7.3 item 3 lists `metrics_scrape` as an enclosure-updating reveal-order event (**B6**); 7.2's bare "**There is no cross-pair interference**" contradicts 7.4's "Carry-over from earlier pairs is allowed" (**m2**) | **P** — same cadence defect from the other side (**B3**) |
| **3.** normal-mixture primitive, current full enrolled prefix, no envelope | 8.2 verbatim code block with `alpha_gate = 0.00625, rho = 100., variance_process=n`, clip to `[-1,1]`; 8.2 "**Prohibited, by name** ... no prefix envelope; no maximization of lower bounds over different prefixes; no retained crossing; no running intersection ...; no substitution of the number of completed pairs for `n`"; Appendix B `"retention": false, "running_intersection": false, "prefix_envelope": false, "maximize_over_prefixes": false` | **F** | **P** — `lab_monitor.band()` and `decide()` are correct, but the state machine 7.1 never looks at a call-level event while `lab_monitor.replay()` consumes them (**B3**); PG-1 is still flagged "**coordinator**", i.e. unresolved |
| **4.** concrete conservative error allocation | 8.5 table (program 0.05 / trial 0.0125 / `alpha_gate` 0.00625, `rho` 100.); "**The same two-sided band serves both the deploy tail and the harm tail; there is no extra split**"; 2.4 "A deferred T3 does not release its 0.0125 ... the alpha table is frozen for four trials and is **not re-allocated**"; power check of `rho` at 11.2 | **F** (arithmetic verified, §2.2) | **F** |
| **5.** endpoints and gates not fitted to desired results; enclosures | 6.2 `tiers = [Tier('success'), Tier('cost', higher_better=False, relative_tolerance=.05)]`, "eligible **only when both episodes succeeded**; a joint failure is a tie"; 7.5 items 1-7 (start at `[-1,1]`, success formula `[sA_low - sB_high, sA_high - sB_low]`, "**Absence of failure is not success**", "**Elapsed cost is a lower bound only if it cannot decrease**", containment audit "at **every recorded evaluation**", "**`compare` is never fed a partial outcome**"); 6.4 "**Infrastructure loss is treated by this frozen outcome rule, never by deletion**" | **P** — 7.5 item 1 ("collapsed to a point **only** ... when **both episodes** of the pair are revealed") contradicts 7.5 item 5 (the cost certificate collapses with one episode pending) — **M4** | **N** — `lab_enclosure` (3.7) and `config.json` (6.1) implement **three** tiers with `relative_tolerance` **0.10** and the certificate `0.9 * ell > L_r + 1e-9`. This is the v2 hierarchy the guidance replaced. See **B1** |
| **6.** finite policy, preserved abstention | 8.4 table (`U_h < 0` -> `HARM_RETAIN_INCUMBENT`; `L_h > 0` **and** `L_s > -delta` at the **same** prefix -> `DEPLOY_CANDIDATE`); 8.3 "`n_min = 100` ... *'a reproducible screening choice, not a guarantee of adequate power'*"; 1.3 feasibility declaration; 11.4 "**No horizon extension, no margin loosening, no model replacement**"; 10.3 "hypotheses, not known truths" | **P** — 1.3's bolded "**A DEPLOY decision is therefore unreachable by construction at this scale, whatever the outcomes**" is **false** (**B4**); guidance item 6's "the reverse contrast uses **new disjoint tasks**/assignments" is **not** met and 10.3 redefines the word instead of declaring the deviation (**M9**) | **P** — §0 repeats the same false sentence; `test_deploy_unreachable_at_scale` is correctly conditioned on `Dbar = 0`, so the test and the prose disagree |
| **7.** a traffic switch creates a new observation phase | 9.1 items 1-6; 9.2 in-flight exposure; 9.3 "**outside all inference**: no pair score is computed, no band is updated, `n` does not grow"; 9.4 boundary statement quoted as a block quote; 9.5 "`M` is determined by the prespecified roster length `N_P`; **it is not a saving rate**" | **F** (one factual slip, **m1**) | **F** |
| **8.** A/A is an implementation/null check | 11.4 T4 bullet ("same model revision, same prompts and workflow, same decoding law, same verifier, same caps and same serving policy on both labels, **no label-specific seed or worker advantage**"; "**One non-crossing A/A run does not establish a 5% false-decision rate and does not demonstrate equivalence**"; "A crossing is reported and investigated, never silently discarded"); 1.5 item 3; 8.7 item 3 | **F** | **F** |
| **9.** reviewable freeze before execution | 14.2, item-for-item against guidance item 9 (15 rows); 12.5 "**They do not prove** ... that events happened at their logged client times"; Appendix C "*Guidance item 9 tests*" | **P** — row 10 promises "`lab_reference_rule`" as a delivered interval/decision artifact; it does not exist (**B2**). Row 13's reorder-invariance test is mis-stated (**M17**) | **P** — module list (2.1, 10) has no `lab_reference_rule` |
| **primitive and theorem boundary** | 8.8 item 5 (`betting_log_e_ternary` "computed **only after the trial has ended**, **only on final complete scores**, **never on partial scores** ... no error-control claim and no adapter"); 8.7 item 5 "**Not a bandit-router analysis**"; 8.7 item 6; Appendix B `"betting_readout": {"when": "after trial end", "input": "final complete scores only", "error_control_claim": false}`; 1.5 item 7 | **F** | **F** — 3.8 "What is NOT in this module, by instruction", PG-16, and `test_no_betting_in_decision_path` |

### 1.1 Superseded revision-1 decisions: where they survive

I checked by name for each of the six the task names. In `protocol_v3.md`:

* **betting driving traffic** — absent. 8.8 item 5 and Appendix B are compliant.
* **margin 0.10** — appears only at 8.8 item 1 as an exploratory read-out with the mandated label, and at
  1.3/11.3 as a reachability row. Compliant.
* **extra alpha split for the harm tail** — absent; 8.5 states the opposite explicitly.
* **prefix envelopes / retained crossings / running intersections** — prohibited by name in 8.2, set
  `false` in Appendix B, and each has a named test in Appendix C.

In `ARCHITECTURE.md` the revision-1 rule block **does** survive, in the one place that matters most:

* the **hierarchy** is the v2 three-tier, `relative_tolerance = 0.10` hierarchy (`TIER_NAMES` in 3.7,
  `tiers_from_config`, `hierarchy_enclosure`, `config.json` §6.1 `hierarchy`, the per-trial `"n_tiers": 3`
  / `"n_tiers": 2` keys, and `test_equality_is_tie` "in `success`, `latency_s` **and**
  `completion_tokens`"), and the enclosure certificate constant is therefore **0.9**, not 0.95.
  This is **B1**.
* the **seed rule** is the pre-N6 rule (`& 0x7FFFFFFF`, no worker partition) — **M1**.
* the pause reason enum still carries **`thermal`** — **M15**.
* the normative citation for the integrity tables is still **`protocol_draft_v2.md` §11.6** — **M16**.
---

## 2. The statistical rule: what I recomputed, and what survives attack

Scripts `_audit3_check.py`, `_audit3_pilot.py`, `_audit3_misc.py` in this session's scratchpad root (not in
`live_ab_design/`, which this audit does not add files to beyond `audit_v3.md`).
`r(n) = normal_mixture_radius(n, alpha=0.00625, rho=100., variance_process=n)` from
`src/winstats.py:51-61`.

### 2.1 Radius and reachability — all confirmed

| quantity | protocol value | recomputed | verdict |
|---|---|---|---|
| `r(91)` | 0.499041 | 0.4990406345814646 | exact |
| `r(92)` | 0.495026 | 0.4950264429325317 | exact (and the `0.4966` of `COORDINATOR_DECISIONS.md` rev 2 item 5 is indeed wrong; see **m10**) |
| `r(100)`, `r(295)`, `r(569)` | 0.465693 / 0.228707 / 0.157802 | identical to 6 d.p. | exact |
| every other row of 1.3 (120, 150, 200, 250, 350, 400, 450, 500, 565, 626) | — | identical | exact |
| smallest `n` with `r(n) < 0.03` / 0.05 / 0.10 / 0.15 / 0.20 | 17,097 / 5,789 / 1,378 / 626 / 372 | 17,097 / 5,789 / 1,378 / 626 / 372 | exact |
| `rho` sensitivity table (11.2), all five rows including `n(r<0.03)` 19,719 / 18,445 / 17,097 / 16,013 / 15,320 | — | identical | exact |
| first-crossing table (11.3) for `|Zbar|` 0.55 … 0.15 -> 100,100,100,100,105,124,151,191,255,372,none | — | identical | exact |
| minimum-observed-value table (11.3), `minDbar = r(n) - 0.03` | +0.4357 … +0.1278 | identical | exact |

Pilot effect sizes over all 591x591 ordered cross-task pairs (diagonal excluded), from
`results/local_stream/episodes_flat.csv`:

| quantity | protocol 1.3 | recomputed | verdict |
|---|---|---|---|
| T1 P(win)/P(tie)/P(loss), two-tier, tol .05 | 0.7115 / 0.0762 / 0.2122 | 0.7115 / 0.0762 / 0.2122 | exact |
| `Zbar` | +0.4993 | +0.499295 | exact |
| tier 0 / tier 1 share | 0.3922 / 0.5316 | 0.3922 / 0.5316 | exact |
| `Dbar`, P(+1)/P(0)/P(-1) | 0.000000, .1961/.6078/.1961 | 0.000000, .1961/.6078/.1961 | exact |
| T4 A/A | 0.4510 / 0.0979 / 0.4510 | 0.4510 / 0.0979 / 0.4510 | exact |
| three-tier check at tol .10 | 0.7090 / 0.0788 / 0.2122, `NB = +0.4968`, token tier 0.30% | identical | exact |
| paired same-task success s.e. (1.3) | 0.015 | 0.0151 (80 discordant of 591) | exact |
| T1 "candidate about 4.46x faster" (1.2) | 4.46 | 4.456 (mean), 4.911 (median per-task) | exact for the mean |

**Alpha arithmetic.** `0.05 / 4 = 0.0125`; `0.0125 / 2 = 0.00625`; `8 x 0.00625 = 0.05`. The per-trial
bound in 8.6 item 3 is the union of the two band failures, `0.00625 + 0.00625 = 0.0125`, and the program
bound in 8.6 item 4 is the union over four trials, `4 x 0.0125 = 0.05`. Correct, and correctly tied to
guidance item 4.

### 2.2 Same-prefix requirement — satisfied

8.4 condition 2 reads "`L_h > 0` **and** `L_s > -delta`, both at this same current prefix", and 8.1
defines a single `n = N(t)` used by both bands. `ARCHITECTURE` `decide()` reads `bh, bs = state.bands()`,
one call, one `n`. PG-5 pins the harm tail to `U_h < 0` only and states `U_s` "is computed and logged and
**never decides**", matching revision 2 item 1. No finding.

### 2.3 Coverage inheritance and the decision bound — correct

The claim at 8.6 item 1, "Because the enclosures satisfy
`sum(lower_j[:n]) <= sum(true scores) <= sum(upper_j[:n])` **pathwise**, the enclosure band contains the
complete-data band at the same `n`", is right: `sum(lower)/n - r <= Sbar_n - r` and
`sum(upper)/n + r >= Sbar_n + r`, so `[L,U] ⊇ [Sbar - r, Sbar + r]` and a coverage failure of the
enclosure band at any evaluation implies a coverage failure of the complete-data band at that `n`.
Because `thm:normal_cs` is uniform over `n`, no stopping-time property is needed, which is exactly what
`prop:delay` supplies and what 7.2 and 8.6 item 2 assert. The false-decision implications in 8.6 item 3
are each a strict inequality against a band endpoint, so the union bound is tight and honest.

One consequence the protocol does not state but that matters for the reader: within a fixed prefix `n`,
enclosures only narrow, so `U_j(n)` is non-increasing and `L_j(n)` is non-decreasing across the several
looks at that prefix. "The **first** prefix `n*`" in 8.9 is therefore well defined and the live/reference
agreement on the prefix is not sensitive to which look inside the prefix fired. Worth one sentence in 8.9.

### 2.4 Filtration and the pair-coin argument — one real hole

The martingale construction needs nothing but adaptedness and boundedness, and 8.6's last paragraph says
so correctly ("**The error guarantee of 8.6 needs none of this**"). The attack therefore has to go at the
**causal** layer, and there it lands.

7.2 states: "Potential records are **not** elements of `F_0`: ... The design-based object is the
collection, indexed by pair, orientation and history, of the **conditional laws** of the pair's record".
Two paragraphs later, 7.4 writes

> `E(Z_i | H_i, W_i(1), W_i(0)) = (U_i + V_i) / 2`

which **conditions on both potential records as random variables on one probability space**. If only the
conditional laws exist, that conditional expectation is undefined, and with it `mu_i`, the identification
result of 7.4, the T4 exactness claim, and the assumption list in 10.2 item 1. This is **M8**.

The pair-synchrony argument itself is sound and is the best part of the document: 5.1's "Under the
pair-synchronous rule **`R_i` does not exist while pair `i-1` runs**, so cross-pair interference through
the coin is excluded **physically**, not by assumption" is a real physical guarantee, and 4.2 invariants
(ii) and (vii) enforce it. `H_i = F_{i-1} ∨ σ(stratum, task ids)` adds nothing, since the arrival order is
in `F_0`; harmless.

`F_0` legitimately contains `N_P` and the roster even though exclusion rule 3.2 item 4 is a **timing**
criterion measured under load: nothing about it is a design-task outcome, and it is fixed before the
freeze. But it selects tasks on the *cost* dimension, and the cost tier decides ~53% of pairs — see **M19**.

### 2.5 The enclosure arithmetic — I could not break it; the *text* is what breaks

I checked the closed case list of 7.5 item 5 against `winstats.compare` line by line
(`src/winstats.py:41-46`, `tol = absolute_tolerance + relative_tolerance * max(|a|,|b|)`, strict `>`).

* **`s_r = 0`, partner pending.** Partner succeeds -> tier 0 decisive, `sign = -sgn`; partner fails ->
  tier 0 ties and tier 1 is ineligible -> `0`. Feasible set `{-sgn, 0}`; enclosure `[-1,0]` for `sgn=+1`
  and `[0,1]` for `sgn=-1`. **Correct.**
* **`s_r = 1`, partner pending, no certificate.** Feasible set `{-sgn, 0, +sgn}` -> `[-1,1]`. **Correct.**
* **`s_r = 1`, certificate.** With `x >= ell` and `0.95 ell > L_r`, we get `x > L_r`, hence
  `max(x, L_r) = x`, hence `x - L_r > 0.05 x = tol` for every feasible `x`; and the partner-fails branch
  also gives `+sgn`. Collapse to `[sgn, sgn]` is **correct**, including the `1e-9` guard.
* **The lower-bound premise `x >= ell`.** I verified it against the pilot code rather than accepting it.
  `experiments/local_stream/agent.py` sets `rec['latency_s'] = time.perf_counter() - tw0` **after** the
  `try/except`, i.e. after every call including a failed final repair call. So `t_final >= max_e t_e` even
  on the `agent.py:242-249` path that grades the pre-repair program, and `t_0 = tw0 <= t_c1`. `ell` is a
  valid lower bound. **No counterexample exists.** (One residual: `latency_s` uses `perf_counter` while
  `ell` uses `monotonic_ns`. On CPython/darwin both are `mach_absolute_time`, so the bound holds, but the
  protocol never says so and the containment audit is decision-defining code — see **m11** in section 5.)
* **Terminal failures.** Rows 10, 10b, 11, 18 all set `success = 0`, so tier 1 is ineligible and the
  certificate's `+sgn` conclusion survives; row 18's `latency_s = 0.0` cannot contradict an earlier
  certificate for the same reason. **Correct.**

So the arithmetic is right. What is wrong is that **7.5 item 1 forbids what 7.5 item 5 does**
(finding **M4**), and that the implementation contract computes it at the wrong tolerance
(finding **B1**), which changes the certificate constant from `0.95` to `0.9` — a constant that 14.3 lists
by name as non-amendable ("the enclosure rules and the **0.95 certificate constant**").

### 2.6 Latency measured under concurrency — not handled honestly

The protocol does a great deal here (`latency_s_w2sync` naming in 6.1, the concurrent-load record in 5.2,
the estimand wording in 7.4, "**never** pooled with the pilot's sequential `latency_s` nor with
follow-up-cohort latencies", 1.5 items 8 and 10). Two mechanisms are nevertheless left un-named, and both
act on the tier that decides **53.16%** of pairs.

1. **The within-pair duration asymmetry is not symmetric contention.** In T1/T2 the two arms of a pair
   start together but the `self_test_repair` episode lasts ~4.46x longer (recomputed above). The
   `single_shot` episode is therefore contended for **100%** of its duration while the
   `self_test_repair` episode is contended for roughly the first 22% of its. 6.2 analyses exactly this
   effect — "under a mild equal-slowdown model the faster episode is slowed for all of its duration and
   the slower one only during the overlap, so the frozen 5% tolerance corresponds to a larger tolerance
   on the **solo** latency ratio" — but writes it **only for T3**, and 5.8 item 4 defines the compression
   statistic `C` **only for the two T3 models on out-of-design prompts**. T1 and T2 get neither the
   statistic nor the regime label. This is **M10**.
2. **The execution lock transfers cost across arms, one-directionally.** 5.7 puts
   `sandbox_lock_wait_s` **inside** `latency_s` for the agent's own tests and **outside** `latency_s` for
   hidden-test verification. In T1/T2 only `self_test_repair` runs self-tests, and its partner
   (`single_shot`) holds the same host-wide lock for its *verification*, which is not in the partner's
   own cost. So one arm's measured cost is inflated by the other arm's grading time, by up to
   `max_lock_wait_s = 120 s` per execution and up to three executions per episode. 5.7 records this as a
   logged field and calls the absence of CPU competition "a side effect"; nowhere is it named as an
   arm-dependent cost transfer. This is **M11**.

T4 cannot detect either mechanism (both arms identical), which 1.2 already concedes for arm-dependent
defects generally.

---

## 3. BLOCKERS

### B1 — `ARCHITECTURE.md` implements the superseded v2 hierarchy, at the superseded tolerance, with the superseded certificate constant

**Passages.** `protocol_v3.md` 6.2: "Guidance item 5. **Two tiers, identical for all four trials**" with
`tiers = [Tier('success'), Tier('cost', higher_better=False, relative_tolerance=.05)]`, and 7.5 item 5:
"At `tol = 0.05` the certificate is **`0.95 * ell > L_r + 1e-9`**". 14.3 makes "the hierarchy and its
tolerances, the eligibility rule, the tie rule, ... the enclosure rules and the **0.95 certificate
constant**" non-amendable. Against that, `ARCHITECTURE.md` 3.7:

> `TIER_NAMES: tuple[str, ...] = ('success', 'latency_s', 'completion_tokens')`
> `tiers_from_config` ... "T1/T2/T4: success (tol 0), latency_s (lower better, rel tol 0.10),
> completion_tokens (lower better, rel tol 0.10). T3: the first two only."
> `hierarchy_enclosure` ... "tier 1 with relative tolerance 0.10 on latency; ...
> `if 0.9 * ell > L_r + 1e-9:  L_p - L_r > 0.10 * L_p  ==> z = +sgn`"

and `ARCHITECTURE.md` 6.1 `config.json`:

> `"hierarchy": [ {"name": "success", ... 0.0}, {"name": "latency_s", ... "relative_tolerance": 0.10},
> {"name": "completion_tokens", ... "relative_tolerance": 0.10} ]`, with `"n_tiers": 3` for T1/T2/T4 and
> `"n_tiers": 2` for T3,

and 9.2 G3 `test_equality_is_tie`: "exact threshold equality ... in `success`, `latency_s` **and**
`completion_tokens`".

**Scenario.** G3 implements `lab_enclosure` and `lab_monitor` from the only document it is told is the
interface contract, and G5 assembles `config.json` from §6.1. The freeze bundle's `rule_block_sha256`
(which by `ARCHITECTURE` 6.2 hashes `hierarchy` and `eligibility_rule`) is then computed over the v2
hierarchy. Every score in every trial is then produced by a three-tier kernel at tolerance 0.10, T3 uses a
different kernel from T1/T2/T4 (exactly the defect `protocol_v3.md`'s "What v3 removes from v2" table says
was the reason to drop the token tier), the planning values of 1.3 (`Zbar = +0.4993`) no longer describe
the realized rule, and the enclosure certificate fires at `0.9 ell` instead of `0.95 ell`. Because the
hierarchy and the certificate constant are in the 14.3 immutable list, the discovery of this after the
first design-task outcome is 6.4 **row 24**: "not repairable ... Claims 2 to 5 and 7 ... are dropped for
every affected trial". The whole program's claim set is lost to a document mismatch.

**Required change.** Rewrite `ARCHITECTURE.md` 3.7, 6.1 and 9.2 so that: `TIER_NAMES = ('success',
'latency_s')`; `tiers_from_config` returns
`[Tier('success'), Tier('cost', higher_better=False, relative_tolerance=0.05)]` for **all four** trials;
`hierarchy_enclosure`'s certificate reads `if 0.95 * ell > L_r + 1e-9`; `config.json`'s `hierarchy` is the
two-row array of `protocol_v3.md` Appendix B verbatim; the per-trial `"n_tiers"` keys are deleted;
`test_equality_is_tie` names `success` and `latency_s` only. Add to `ARCHITECTURE` §0 the sentence
"`protocol_v3.md` sections 6.2-6.4, 7 and 8 are the rule block; where this document differs from them,
this document is defective", and add to Appendix C of the protocol a freeze test that
`lab_common.rule_block_sha256(config)` equals the rule-block hash computed from the protocol text's own
table.

### B2 — the object that produces the normative decision does not exist in the implementation contract

**Passages.** `protocol_v3.md` 8.9: "The rule of 8.1 to 8.4 exists **twice**. ... The **reference rule**
(`lab_reference_rule.py`: standard library, numpy and `src/winstats.py` only ...) is part of the freeze
bundle and is **decision-defining code**"; "**The normative decision of a trial** is the reference rule
applied to the chain"; "**Shadow evaluation at every evaluation** (finding N19). The reference rule is
evaluated as a shadow at **every** evaluation ... Any difference ... **pauses the trial**". 14.2 row 10
delivers "`lab_monitor`, **`lab_reference_rule`**, the verifier, the builder, the scanner ... with
per-file SHA-256". 14.3 lists `lab_reference_rule` as decision-defining and immutable. 6.4 row 24 names
"reference rule" first among decision-defining code. Against that, `ARCHITECTURE.md` PG-3:

> "§9.2 requires a `lab_reference_rule.py` that is a *different code path* from the live monitor; the
> module list for this task has one statistical core. | **One pure `lab_monitor` used by both** the
> orchestrator (live) and `lab_verify_log` (replay from the chain alone)."

and the module table (2.1) and the ownership table (10) contain no `lab_reference_rule`.

**Scenario.** N19 is reopened in full. With one module, the "shadow" of 8.9 compares `lab_monitor` with
itself and can never differ, so `monitor_mismatch` is unreachable, `trial_paused(monitor_mismatch)` is
dead code, and a sign slip or a stale-state bug in the live monitor is found only by the verifier
**after** the trial, which is precisely the situation the critic's N19 closed. Simultaneously, the freeze
bundle cannot be assembled: `lab_common.build_freeze_bundle` "raise[s] `FreezeIncomplete` naming every
offending key" and 14.2 row 10 names a file with no hash. And 6.4 row 24's consequence class has no
referent. Note that PG-3 is **not** marked "coordinator": the architecture states this as settled.

**Required change.** Either (a) add `lab_reference_rule.py` to `ARCHITECTURE` 2.1/3/10 as a G1-owned
module — stdlib + numpy + `winstats` only, no import of `lab_monitor`, `lab_enclosure`,
`lab_orchestrator`, reading the chain and computing scores only through `winstats.compare` — with its own
row in the import matrix 3.16, its own signature block, and a `tests_lab_chain.py` test that an injected
sign slip, a swapped count and a wrong denominator in `lab_monitor` are each caught **by the shadow at the
first evaluation**; or (b) amend `protocol_v3.md` 8.9, 14.2 row 10, 14.3 and 6.4 row 24 to name
`lab_verify_log._band_independent` plus the replay as the reference object, delete the word "shadow at
every evaluation", and re-open N19 as an accepted residual risk with that fact printed in every report.
(a) is the only option consistent with the freeze deliverable as written. Until one is chosen, nothing
may be implemented, because G1, G3 and G5 would each build a different thing.

### B3 — the look cadence differs between the protocol, the state machine, and the architecture's own replay

**Passages.** `protocol_v3.md` 8.3: "**Evaluated at every reveal-order event** on the current full
enrolled prefix, in the order the events are ingested." 7.3 item 3 defines a reveal-order event as
"(`llm_request`, `llm_response`, `llm_error`, `episode_revealed`, `metrics_scrape`)". 12.3 (verifier):
"**exactly one `monitor_update` per ingested reveal-order event**". Against that, `ARCHITECTURE.md` 7.1
row 7:

> "| 7 | `RUNNING` | a spool line arrives | ingest -> `job_accepted` / `llm_request` / `llm_response` /
> `llm_error` | `RUNNING` |"

— no `monitor_update`, no `decide()`; only row 8 (an `episode_final`) and row 6 (an enroll) produce looks,
and `T19 monitor_update.trigger` is the closed enum `[enroll, reveal, resume]`. Yet `ARCHITECTURE` 3.8
`replay()` says it "Consumes exactly these event types and nothing else: `pair_enrolled`, `coin_drawn`,
`arm_assigned_by_decision`, **`llm_request`, `llm_response`, `llm_error`**, `episode_revealed`, ... and
applies enroll/update **in event order**", and "The caller (`lab_verify_log`) compares this list
**element-wise** with the logged `monitor_update` bodies". PG-1 is still marked "**coordinator**".

**Scenario.** Deterministic, on pair 1 of T4. The live monitor writes one `monitor_update` per reveal;
the replay walks call-level events and produces a longer list; the element-wise comparison fails on
length; `monitor.replay` is a **FAIL**-severity check (3.3), which is in the `plumbing_fail` closed list
(6.4 row 22), so the program pauses and the operator is invited to perform a "harness-only re-freeze" of
the **live monitor**, i.e. of decision-defining code, which 14.3 forbids. This is the Round-11/12
improvisation pattern reproduced exactly. Separately, under the protocol's literal rule a decision can
fire at an `llm_response` (the cost certificate of 7.5 item 5), which is the entire reason the enclosure
machinery exists; under the state machine it cannot, so the enclosures are dead weight and every decision
is taken on a completed prefix.

**Required change.** Resolve PG-1 in the protocol, not in the architecture, and make the two agree.
Recommended resolution (it is the one that keeps guidance item 3 literal and the enclosures useful):
in `protocol_v3.md` 8.3 replace "at every reveal-order event" with "**at every ingested event that can
change an enclosure endpoint — `episode_revealed`, and any `llm_request` / `llm_response` / `llm_error`
that raises the certified elapsed `ell` of a pending episode of an enrolled pair — and at every
`pair_enrolled`; a `metrics_scrape` is never an evaluation trigger**"; amend 7.3 item 3 to drop
`metrics_scrape` (see **B6**); amend 12.3's verifier sentence to "exactly one `monitor_update` per
evaluation trigger as defined in 8.3"; add `call` to the `monitor_update.trigger` enum; and add
`ARCHITECTURE` 7.1 row 7 actions "`lab_enclosure.certified_elapsed`; if it changed, `monitor.update`,
`monitor_update(trigger='call')`, `decide()`". Add the G3 test "a certificate that binds at an
`llm_response` produces a look and can decide".

### B4 — the frozen headline declaration states a false mathematical fact, and the protocol contradicts it two sentences later

**Passages.** `protocol_v3.md` 1.3, bolded: "**The roster gives at most 569 pairs. A DEPLOY decision is
therefore unreachable by construction at this scale, whatever the outcomes.**" Immediately after:
"At the horizon the deploy route would need an observed success difference above
`r(569) - 0.03 = +0.1278`". Also `COORDINATOR_DECISIONS.md` rev 2 item 5 ("A DEPLOY DECISION IS
UNREACHABLE BY CONSTRUCTION AT THIS SCALE, whatever the outcomes"), `ARCHITECTURE` §0 ("**A deploy
decision is unreachable by construction at this scale.**"), Appendix E ("The deploy route of this program
was declared unreachable at this horizon before collection"), and 1.4 claim 8.

**Scenario.** The two sentences cannot both be true. The deploy route is reachable at `n <= 569` for any
realized success difference above `r(n) - 0.03`; at `n = 569` that is `+0.1278`, which is 8.5 paired
standard errors above the pilot's 0.000 but is not a logical impossibility — the protocol's own
Appendix E supplies a template for it ("**T1, DEPLOY (not expected; if it nevertheless occurred)**") and
`ARCHITECTURE`'s `test_deploy_unreachable_at_scale` correctly conditions the assertion on `Dbar = 0`.
If T1 or T3 deploys, the frozen pre-registration contains a statement its own data falsify, and the first
reviewer who reads 1.3 next to Appendix E will say so. It also makes claim 8 of 1.4
("This was declared unreachable at this horizon before collection") unusable, and hands an adversarial
referee the sentence "the authors claimed their own design made an outcome impossible and then reported
it".

**Required change.** In 1.3 replace the bolded sentence with: "**The roster gives at most 568 pairs
(3.3). A DEPLOY decision therefore requires an observed running success difference above
`r(N_P) - 0.03`, which is `+0.1278` at `n = 569` and `+0.1283` at `n = 568`; the same-task pilot
difference is 0.000000 with a paired standard error of 0.0151, i.e. the threshold is about 8.5 standard
errors away. The deploy route is declared, before collection, a pre-specified near-certain abstention;
it is not a logical impossibility, and if it occurs it is reported under Appendix E's DEPLOY template
without any claim that it was impossible.**" Make the same replacement in `ARCHITECTURE` §0, in the
Appendix E retained sentence ("declared unreachable" -> "declared a pre-specified near-certain
abstention"), and in 1.4 claim 8. Add to 1.5 a new forbidden phrase: "unreachable by construction",
"impossible whatever the outcomes".

### B5 — the two documents build a different number of randomization units, and the protocol's own "at most 569" is wrong under its own pairing rule

**Passages.** `protocol_v3.md` 3.4: "Pairs are formed **inside a stratum** (`paper/main.tex:171-172`,
'disjoint pairs of arrivals within a prespecified stratum') ... **Leftover** tasks receive the arrival
numbers after `2 * N_P` in list order; they are never randomized". 3.3: "`N_P` = `295 + floor(n_S2 / 2)`
pairs, **at most 565** after the smoke exclusions and **at most 569** before any exclusion". Against
that, `ARCHITECTURE` 3.5 `arrival_order`: "Pairing is stratified: S1 tasks pair with S1 tasks and S2 with
S2, **and at most one 'mixed' pair absorbs the two odd remainders**"; 3.4: "`n_pairs = n_total // 2` is
the horizon `N_P`"; 9.2 G2 `test_order_stratified`: "S1 pairs with S1, S2 with S2, **at most one mixed
pair**"; PG-21: "`N_P = n_total // 2`, at most 569".

**Scenario, arithmetic.** S1 = 427 + 164 = 591, S2 = 974 - 427 = 547. Protocol rule:
`591 // 2 + 547 // 2 = 295 + 273 = 568` pairs and two leftovers. Architecture rule:
`1138 // 2 = 569` pairs, of which one crosses the strata. So (i) the protocol's own "at most 569 before
any exclusion" is **wrong; it is 568**, and (ii) the famous number 569 — which appears in 1.3's radius
table, in claim 8, in 11.3, in 11.4, in Appendix E, in Appendix B (`"horizon": "N_P <= 569"`) and in
`MonitorConfig.n_max = 569` — is reachable **only** through the cross-stratum pair the protocol forbids.
One mixed pair is not a cosmetic difference: `thm:pair_id` is invoked at 4.1 through the *stratified*
statement of `paper/main.tex:171-172`, the S1/S2 success rates differ sharply (3.5 item 6 expects S2 far
below S1's 0.73), and a mixed pair is the one pair whose two positions have systematically different
difficulty. `N_P` and "the arrival orders" are both in the 14.3 non-amendable list, so this is discovered
as a row-24 event.

**Required change.** In `ARCHITECTURE` 3.5 delete the mixed pair: "Pairing is stratified: S1 pairs with
S1 and S2 with S2; **the odd remainder of each stratum is a leftover and is never enrolled**"; in 3.4
replace `n_pairs = n_total // 2` with `n_pairs = n_S1 // 2 + n_S2 // 2`; amend `test_order_stratified` to
"every pair's two uids share a stratum; there is no mixed pair"; amend PG-21 accordingly. In
`protocol_v3.md` 3.3 replace "at most 569 before any exclusion" with "**at most 568 before any
exclusion**", and in 1.3, 11.3, 11.4, 1.4 claim 8, Appendix B and Appendix E replace every "569" used as
a horizon with "568" (the radius table may keep an `r(569)` row, labelled as such). `MonitorConfig.n_max`
must have **no default**: make it a required field so a config-load failure cannot silently install a
horizon (see **m9**).

### B6 — `metrics_scrape` is declared an enclosure-updating event, which forces the verifier to demand looks inside the follow-up cohort

**Passages.** 7.3 item 3: "A reveal-order event (`llm_request`, `llm_response`, `llm_error`,
`episode_revealed`, **`metrics_scrape`**) **updates the existing score enclosure** of the pair at its own
enrollment position and nothing else." 8.3: "Evaluated at every reveal-order event". 12.3 verifier:
"exactly one `monitor_update` per ingested reveal-order event". 13.1: `/metrics` is scraped "at **every
pair boundary**", "immediately **before and after every failed try**", "after every **restart**", and
"in the follow-up cohort at a **quiescent point every 50 arrivals**". Against that, 9.3: the follow-up
cohort "is **outside all inference**: no pair score is computed, **no band is updated**, `n` does not
grow", and Appendix C's guidance-item-9 test "**switch-phase exclusion**: no follow-up-cohort arrival ever
enters a score, a band, `n`, or the exposure figures of the randomized phase".

**Scenario.** A `metrics_scrape` carries no information about any pair's score, so calling it an
enclosure-updating event is simply false; but the verifier rule is mechanical. In the follow-up cohort of
T2 there are quiescent scrapes every 50 arrivals; the verifier demands one `monitor_update` for each; 9.3
and the Appendix C test forbid them. The verifier therefore FAILs whichever way the orchestrator is
written. A verifier FAIL is a `plumbing_fail` condition (6.4 row 22), so the program pauses between trials
on a defect that cannot be repaired by a reporting-code erratum.

**Required change.** In 7.3 item 3 delete `metrics_scrape` from the list and add: "`metrics_scrape`,
`server_health`, `anchor` and every program-chain event are **not** reveal-order events and never trigger
an evaluation." In 12.3 replace "exactly one `monitor_update` per ingested reveal-order event" with
"exactly one `monitor_update` per evaluation trigger of 8.3, and **no `monitor_update` at any event of the
post-decision phase**". Add the Appendix C test "a quiescent `metrics_scrape` in the follow-up cohort
produces no `monitor_update` and the verifier passes".

### B7 — the working location is an open item, and a concurrent checkout in the shared clone has no outcome row

**Passages.** `protocol_v3.md` Appendix F: "during the writing of this revision the shared clone's `HEAD`
moved from `session60/live-ab` to `main` through another session's work. ... **Whether a single shared
clone (revision 1, C15) is still the right working location, given that, is a coordinator decision and is
listed as an open item.**" 14.1 item 1 fixes execution in "the main clone, branch `session60/live-ab`";
14.1 item 5: the runner "**re-verifies harness, config, serving manifest and weights at every
invocation**"; 12.4 item 2 refuses an anchor commit on the wrong branch.

**Scenario.** 12.4 item 2 protects only the *anchor commit*. A `git checkout` or a merge performed by
another session in the same clone during a multi-hour trial rewrites the working tree under the running
orchestrator: `experiments/live_ab/lab_*.py` (already imported, but re-read on the next invocation),
`src/winstats.py` (the pinned core, imported once), `results/live_ab/**` (the live chains and the freeze
directory — `results/` is tracked, and 14.1 item 1 names `results/SESSION60_RESULTS_INDEX.md` as a file
that *may* change). Between invocations nothing detects it except the invocation-start drift check; within
an invocation nothing detects it at all. A chain segment swapped or truncated by a checkout is
indistinguishable from a torn tail, and 12.6 item 2 would report it as "**evidence of editing**" against an
operator who did nothing. There is no row in 6.4 and no reason code in 14.6 for "the working tree changed
under the run". A protocol that asks to be frozen must not carry an open coordinator item about where it
executes.

**Required change.** Close the item in the text, one of two ways. Preferred: add to 14.1 item 1 "**a
dedicated worktree** `<WORK>/clone-live-ab` created with `git worktree add` and used by no other session;
no other session may check out a branch in it; the anchor process runs there", and to 12.4 item 2
"before every commit and every invocation the process asserts that the worktree path, its `HEAD` branch
and its `git rev-parse HEAD` are the frozen ones". If the single clone is kept, add a new 6.4 row:
"**27 | the working tree changed under a running invocation** (the SHA-256 of any freeze-bundle file, any
closed chain segment, or `src/winstats.py` differs from its bundle value at a periodic check every 60 s) |
`trial_paused(worktree_drift)` with the observed and expected digests; resume only after the tree is
restored and the digests match; a changed closed segment is `trial_aborted(chain_unreadable)` and is never
attributed to the operator in 12.6 | program chain, blocking anchor", add `worktree_drift` to the 14.6
table and to `config.json`, and add the Appendix C test "an out-of-band file swap during a dry run pauses
the trial and does not produce a 12.6 editing finding".
---

## 4. MAJORS

**M1 — the N6 seed fix is absent from the implementation contract, and `seed_rule` is inside the rule-block hash.**
`protocol_v3.md` 5.5: "`seed = (int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFE) | worker_index` ...
**The low bit carries the worker index** (finding N6), which partitions the space between the two
uncoordinated workers and makes a cross-worker collision **impossible**"; Appendix B
`"mask": "0x7FFFFFFE", "low_bit": "worker_index"`. `ARCHITECTURE` 3.9 step 1:
"`seed = int.from_bytes(os.urandom(4), 'big') & 0x7FFFFFFF`", and 6.1
`"seed_rule": {"mask": "0x7FFFFFFF", "forbidden": [...]}`, with no partition; PG-8 restates the
unpartitioned draw. *Scenario:* with several thousand requests per worker over four trials, the
cross-worker birthday collision probability is the 1-2% the critic computed; the verifier's
`seeds.unique` fires as a DEFECT, `seed_collision` counts appear in the plumbing report, and the two
documents disagree about a key inside `rule_block_sha256` (`ARCHITECTURE` 6.2 hashes `seed_rule`), so the
rule-block hash recorded at the freeze does not correspond to the protocol text. *Fix:* replace
`ARCHITECTURE` 3.9 step 1 and 6.1 `seed_rule` with the protocol's masked-plus-worker-index rule and add
the G4 test "the low bit equals the worker index; a worker only ever draws from its own half".

**M2 — the structural half of the N7 fix is missing from the launch line the code will build.**
`protocol_v3.md` 2.2 frozen launch line contains `--no-cache-prompt --cache-ram 0
--slot-prompt-similarity 0.0`, and 13.2 says "Finding N7 is closed twice over. (i) **Structurally**:
`--no-cache-prompt`, `--cache-ram 0` and **`--slot-prompt-similarity 0.0`** are in the frozen launch line
and are checked in the golden `/props`". `ARCHITECTURE` 3.10 `server_argv` docstring and 6.1
`llama_args` list `--no-cache-prompt --cache-ram 0` and **omit** `--slot-prompt-similarity`. *Scenario:*
`self_test_repair` sends up to four calls sharing a long prefix to the same slot; with slot-prompt
similarity active the server may reuse a slot's prefix, `timings.cache_n != 0` fires on a repair call, and
6.4 row 12 **irreversibly aborts T2 or T1** — the exact irreversible loss N7 was raised about. *Fix:* add
`"--slot-prompt-similarity", "0.0"` to `ARCHITECTURE` 6.1 `llama_args` and to 3.10 `server_argv`, and add
to `lab_server.start` the assertion that the golden `/props` reports it.

**M3 — the two documents disagree on what a `coin_drawn` body contains, and the disagreement reverses a declared R2 deviation.**
`protocol_v3.md` 4.2: "**The 63 unused bits are not logged: logged hex would be unverifiable
decoration**"; 13.1 declares R2 item 6 a deviation on exactly that ground ("only the bit is logged");
Appendix B's `coin` block has no raw field. `ARCHITECTURE` 3.6 `Coin.raw_hex: str  # 16 hex chars = the
8 bytes actually drawn` and event schema T10 `coin_drawn` body: "`raw_hex` hex16; `bit` int". *Scenario:*
the schema validator "reject[s] ... an unknown key [and] a missing key ... in every event type"
(`ARCHITECTURE` 9.2), so one of the two documents makes every `coin_drawn` invalid; and if `raw_hex` is
logged, 13.1's declared deviation and 4.2's sentence are both false in the frozen text. *Fix:* choose one
and make both documents say it. Recommended: keep `raw_hex` (it costs nothing and is strictly more
evidence), delete the "63 unused bits" sentence from 4.2, and change the R2 item-6 row of 13.1 from
"partial, argued" to "met: the drawn bytes are logged as `raw_hex`".

**M4 — the enclosure collapse rule contradicts itself, in immutable code.**
7.5 item 1: "It is collapsed to a point **only on a valid final-score certificate**, i.e. **when both
episodes of the pair are revealed** with complete finite outcomes and `compare` returns." 7.5 item 5:
"**Certificate:** if `(1 - tol) * ell > L_r + 1e-9` then ... the enclosure **collapses to `[sgn, sgn]`**"
— with the partner still pending. *Scenario:* an implementer who reads item 1 as normative never
implements the cost certificate, so no decision ever fires mid-pair and the enclosures are inert; one who
reads item 5 does. Both are defensible readings of a rule 14.3 makes non-amendable, and the divergence
changes `tau` and therefore `M`, the switch time and the whole operational section. *Fix:* rewrite 7.5
item 1's gloss: "It is collapsed to a point **only on a valid final-score certificate**: either both
episodes are revealed with complete finite outcomes and `compare` returns, **or the enumeration of item 5
leaves exactly one feasible value of the score**. No other collapse exists." The guidance's own words
("collapse only with a valid final-score certificate") already admit the second case.

**M5 — `plumbing_fail` prescribes a harness-only re-freeze for conditions that are decision-defining defects.**
6.4 row 22: "`plumbing_fail`, with the closed machine-checkable condition: *chain check FAIL, completeness
check FAIL, **reference-rule disagreement**, receipt-mismatch count > 0, reconciliation_defect count > 0,
or **T4 payload non-identity***. Single action: **the program is paused ...; a harness-only re-freeze
(14.4) may be performed; then the next trial starts.**" But 14.4 item 1 says "The closed list of 14.3 may
not change", `ARCHITECTURE` P5 restricts `refreeze_authorization.scope` to the enum `[reporting_code]`,
and 6.4 row 24 says a proven defect in the reference rule is "**not repairable**" and drops claims 2 to 5
and 7. *Scenario:* the T4 plumbing report shows a reference-rule disagreement. Row 22 tells the operator
to re-freeze and start T2. Row 24 tells him claims 2-5 and 7 are gone for T4 and that the reference rule
may never change. Both are frozen text; the operator chooses, after outcomes exist. *Fix:* split row 22's
condition list. Conditions repairable by reporting code (receipt-mismatch count, reconciliation defects,
completeness FAIL caused by the verifier's own bookkeeping) keep the current action. Conditions that
implicate decision-defining code (**reference-rule disagreement, chain check FAIL, T4 payload
non-identity**) get the single action "**6.4 row 24 applies to the affected trial; the program is paused;
continuation requires a new protocol version**". State in row 22 that a `plumbing_fail` may never be
closed by changing anything in the 14.3 list.

**M6 — a containment violation has two different frozen consequences.**
7.5 item 6: "A violation is a harness defect and **triggers 8.9**." 8.9's disagreement rule drops claims
3, 4, 5 and 7 and labels the trial `LIVE_DECISION_INVALID`. But a containment violation is by
construction a defect of `lab_enclosure`, which 14.3 lists under **decision-defining code**, so 6.4 row 24
applies and claims **2** to 5 and 7 are dropped. *Scenario:* the verifier reports one containment
violation at look 3,412 of T1; the operator can choose the lighter of two frozen consequences after
seeing the outcome. *Fix:* replace 7.5 item 6's last sentence with "A violation is a **proven defect of
decision-defining code** and has the consequence of **6.4 row 24** for every trial in which any
containment violation occurred; `LIVE_DECISION_INVALID` (8.9) applies in addition if the live and
reference decisions also differ."

**M7 — three incompatible statements of which anchors block.**
12.4 item 5: "A trial blocks on the push ... at **trial start**, at the **decision**, and at
**pause/resume only**." 12.2 marks `decision` (#17), `refreeze_authorization` (#21),
`trial_paused`/`trial_resumed`/`operator_action` (#23) **and `trial_ended`/`trial_aborted` (#27)** as
"yes + blocking anchor"; 6.4 rows 6, 22, 23, 24 each say "blocking anchor"; 12.1 says every program-chain
event carries "a **blocking receipt**". Appendix B lists
`"blocking": ["trial_started","decision","trial_paused","trial_resumed","refreeze_authorization"]` —
without `trial_ended`. `ARCHITECTURE` 6.1 adds `trial_ended` and `trial_aborted` to the list.
*Scenario:* `anchor.blocking` is a frozen key; a trial that blocks on its end anchor can pause for 30
minutes at the end of T4 (row 26) where the config says it should not, or fail to block where 12.2 says it
must. *Fix:* pick the superset, which is what 12.2 and 6.4 actually require, and write it once:
`"blocking": ["trial_started","decision","trial_paused","trial_resumed","refreeze_authorization",
"trial_ended","trial_aborted","operator_action","program_paused","program_resumed","preflight_refused",
"plumbing_verdict_fail","erratum","chain_unreadable"]`. Rewrite 12.4 item 5's first sentence to reference
that list rather than enumerating three cases, and copy it verbatim into `ARCHITECTURE` 6.1.

**M8 — the causal identification in 7.4 conditions on objects 7.2 says do not exist.**
7.2: "**Potential records are not elements of `F_0`** ... The design-based object is the collection,
indexed by pair, orientation and history, of the **conditional laws** of the pair's record". 7.4:
"`E(Z_i | H_i, W_i(1), W_i(0)) = (U_i + V_i) / 2`". *Scenario:* if only conditional laws are posited,
`(W_i(1), W_i(0))` is not a random vector and the displayed conditional expectation, `mu_i`, the whole of
7.4, the assumption list of 10.2 item 1, and the T4 statement "`mu_i = 0` **exactly**, for any hierarchy
and any load" are all undefined. A referee who reads 7.2 and 7.4 in order will say the identification is
not stated. *Fix:* state the coupling. Add to 7.2, after the "conditional laws" sentence: "**Formally:
there is an internal-randomness variable `xi_i` (sampling seeds, scheduling, machine state during the
pair), drawn independently of `R_i` given `H_i`, such that the pair's record is
`W_i = f_i(H_i, R_i, xi_i)`. Write `W_i(r) = f_i(H_i, r, xi_i)`. The two potential records are then random
variables on one space, coupled through `xi_i`, and every display below conditions on them in that
sense.**" Then add to 7.4, after the T4 sentence: "**Under this coupling, in T4 `f_i` does not depend on
`r` and the kernel is antisymmetric in the two positions, so `U_i = -V_i` pathwise and `mu_i = 0`
exactly. The coupling is what 5.5's seed rule and 5.1's position-to-worker mapping protect: seeds are
drawn independently of the coin and position 1 always goes to worker 0.**"

**M9 — guidance item 6's "new disjoint tasks" is not met, and 10.3 redefines the word instead of declaring the deviation.**
Guidance item 6: "the reverse contrast uses **new disjoint tasks/assignments**." 10.3: "the T1/T2 reverse
contrast uses **new disjoint tasks and assignments** *in the sense that* each trial draws its own arrival
order and its own fresh coins". But 3.5 item 5 says "A task is executed at most once per trial and **up to
four times in the program**", and `ARCHITECTURE` PG-22 confirms "Tasks are reused across the four trials".
*Scenario:* the guidance clause is about *tasks*, and it is not met; the protocol's "in the sense that"
converts a deviation into an apparent compliance, which is the one move the root will check for. *Fix:*
replace the 10.3 phrase with: "**Guidance item 6's requirement that the reverse contrast use new disjoint
tasks is NOT met and is declared as a deviation: all four trials draw from the same roster (3.5 item 5),
for the power reason of 3.5 item 2. What is new in each trial is the arrival order and the coins. T1 and
T2 are therefore not two estimates and not two confirmations (1.2), and no statement anywhere treats them
as independent.**" Add the same row to the deviation table of 13.1.

**M10 — the side-by-side compression caveat and its statistic exist only for T3, although the within-pair duration asymmetry is larger in T1/T2.**
6.2's "**T3 regime label, stated before any data**" contains the correct analysis ("the faster episode is
slowed for all of its duration and the slower one only during the overlap, so the frozen 5% tolerance
corresponds to a larger tolerance on the **solo** latency ratio"), and 5.8 item 4 defines `C` only over
"the 6 smoke tasks x 5 repetitions" for the two **T3 models**. In T1/T2 the pilot mean latency ratio is
**4.456** (recomputed), so the `single_shot` arm is contended for ~100% of its duration and the
`self_test_repair` arm for ~22% of its. *Scenario:* the cost tier decides 53.16% of pairs; the protocol
claims `mu_i` is "the preference between the two systems **when one episode of each runs side by side**",
which reads as symmetric co-running and is not what is measured; nothing in section 16 prints a
compression number for T1/T2. *Fix:* extend 5.8 item 4 to "**T1/T2 and T3 side-by-side calibration**: for
each contrast, the latency of each arm on the out-of-design prompts when run solo and when run beside the
other arm of the contrast; `C = (median side-by-side latency ratio candidate/incumbent) / (median solo
latency ratio candidate/incumbent)` over the 6 smoke tasks x 5 repetitions, frozen into the estimand text
of 6.2 **for every trial**". Extend 6.2's regime label to all four trials, and add `C` to section 16
item 6 and to the Appendix E T1/T2 templates.

**M11 — the host-wide execution lock transfers cost from one arm to the other, one-directionally, and is never named as such.**
5.7: `sandbox_lock_wait_s` "for the agent's own tests it lies **inside** `latency_s` ...; hidden-test
verification is outside `latency_s` as in the pilot", and "A side effect: no verification ever competes
for CPU with the partner's sandboxed program." 5.6 caps a single lock wait at `max_lock_wait_s = 120`, up
to three executions per episode. *Scenario:* in T1/T2 only `self_test_repair` takes the lock for
self-tests; its partner `single_shot` takes the same lock for hidden-test **verification**, which is not
in the partner's own cost. So up to 360 s per episode of the incumbent's grading time is charged to the
candidate's cost tier (or vice versa depending on orientation) — an arm-dependent effect of an arm-blind
rule, in the tier that decides most pairs, disclosed only as a logged field. *Fix:* add to 6.2, next to
the tolerance row: "**Named mechanism: the host-wide execution lock (5.7) puts one arm's self-test wait
inside its own `latency_s` while the partner's hidden-test verification, which holds the same lock, is
outside the partner's `latency_s`. Measured cost is therefore partly a transfer between the arms of a
pair. `sandbox_lock_wait_s` is reported by arm next to every cost-tier statement, and a prespecified
descriptive read-out (S-lock) recomputes the hierarchy with `sandbox_lock_wait_s` subtracted from
`latency_s`.**" Add S-lock to 8.8, to 10.2's descriptive list and to section 16 item 9. Add to 7.4's
assumption list that `mu_i` includes this transfer.

**M12 — `episode_hard_cap_s` is arithmetically wrong in a non-amendable row.**
5.6: "`4 * (3 * request_timeout_s + server_recovery_s + 6) + 3 * (sandbox_timeout_s + max_lock_wait_s) +
60` (**= 3,306 s** at `request_timeout_s = 180`)", repeated in Appendix D's N15 row. Recomputed:
`4 * (540 + 180 + 6) = 2904`, `3 * (10 + 120) = 390`, `+ 60` -> **3,354 s**, not 3,306.
*Scenario:* Appendix C requires "a test that **every numeric constant appearing in this protocol's text
appears in `config.json` with the same value**". Whichever number goes into `config.json`, that test fails
against the other, and the freeze is blocked on a typo in an immutable row; or the typo is propagated and
the frozen cap is 48 s away from its own formula. *Fix:* replace "3,306" with "**3,354**" in 5.6 and in
Appendix D's N15 row, and state that `episode_hard_cap_s` is computed by the harness from the formula and
the pinned `request_timeout_s`, never typed.

**M13 — N12 is only partly closed: the string discipline as written rejects `pair_enrolled`.**
12.2: "Every string field of every event must be exactly one of: (a) a value from a **declared enum**;
(b) a **hex digest of fixed length** (32, 40 or 64); (c) a **token** from the closed list ...; (d) a
**numeric string**. **Free text is any string that is none of these, and the schema validator rejects
it**". 12.2 #7 `pair_enrolled` carries `task_uids`, whose values are `"mbpp/278"`, `"mbpp_full/39"`,
`"humaneval/0"` — none of (a) to (d) unless "declared enum" is stretched to a 1,138-member roster.
`ARCHITECTURE` T9 papers over it in a parenthesis: "`task_uids` [str,str] (**uids are enum-shaped ids,
allowed**)". *Scenario:* exactly N12's failure, moved from `trial_started` to `pair_enrolled`: the
validator as specified raises `SchemaError` before the first coin, and `ARCHITECTURE`'s test
`test_schema_rejects` ("prose ... in every event type") and the protocol's Appendix C test ("the validator
rejects free text ... and **accepts** `trial_started`") disagree about whether uids pass. *Fix:* add a
fifth form to 12.2: "(e) a **task uid** matching `^(mbpp|mbpp_full|humaneval)/[0-9]+$`, which is a
declared closed form and must be present in `roster.json`." Add to Appendix C "the validator accepts
`pair_enrolled` with roster uids and rejects a uid that is not in `roster.json`".

**M14 — the `monitor_update` body differs between the two documents, and the validator rejects unknown and missing keys.**
12.2 #16 requires `monitor_update` to carry "the **shadow reference-rule values and the mismatch flag**
(8.9); the **read-outs of 8.8 items 1 to 4 and 6**". `ARCHITECTURE` T19 carries none of them (no shadow
fields, no `side_deltas` values, no S1-restricted statistic, no completed-prefix read-out) and adds
`sums_fsum` and `monitor_code_sha256`, which the protocol does not list. *Scenario:* `validate_event`
"Raise SchemaError unless body matches `EVENT_SCHEMA[etype]` exactly: every required key present, **no
unknown key**". Every `monitor_update` fails against one document or the other, and the shadow check of
8.9 has nowhere to record its result, so `monitor_mismatch` cannot be evidenced in the chain. *Fix:*
write the `monitor_update` body once, in `ARCHITECTURE` §4.4 T19, as the union of both lists (add
`shadow` {`n`, `L_h`, `U_h`, `L_s`, `U_s`, `action`, `mismatch` bool}, `readouts` {`L_s_vs_010`,
`L_s_vs_015`, `s1_restricted`, `completed_prefix`}) and have `protocol_v3.md` 12.2 #16 cite it rather
than re-listing.

**M15 — `ARCHITECTURE` retains the `thermal` reason code the protocol removed.**
`protocol_v3.md` 14.6: "(The v2 reason code **`thermal`** is **removed**: it named no probe and a thermal
probe is a new external dependency.)"; the "What v3 removes from v2" table says the same.
`ARCHITECTURE` P7 `program_paused` reason enum `[plumbing_fail, power, **thermal**, disk,
anchor_unavailable, operator_discretion]`, T26 the same, and state-machine row 24 "battery < 20%,
**thermal event**, or disk < 5 GB". *Fix:* delete `thermal` from P7, T26 and row 24 of `ARCHITECTURE`.
The pause reason list is in the non-amendable 14.3 "reporting thresholds" group, so this cannot be left to
the implementer.

**M16 — the implementation contract cites the superseded protocol as normative.**
`protocol_v3.md` header: "**v3 supersedes `protocol_draft_v2.md` completely. It is not a diff and v2 has
no residual force.**" `ARCHITECTURE` 3.3 verifier check `integrity.table`: "the six tables of
**`protocol_draft_v2.md` §11.6**"; 3.15 builder: "`integrity.json`  the six tables of **protocol 11.6**";
3.13 `status_snapshot`: "the arm-blind `status.json` (**protocol 12.5**)". In v3 the integrity forensics
are **12.6** and the arm-blind status file is **14.7**. *Scenario:* G1 and G5 implement the verifier and
the builder against a document with no force, whose §11.6 differs from v3's 12.6 (v3 adds the
`posting_latency_p95_s` term, the covered-gap rule, the `job_accepted` column and the
randomized-phase/follow-up split). *Fix:* replace every `protocol_draft_v2.md` reference in
`ARCHITECTURE` with the v3 section, and add to `ARCHITECTURE` §0 binding-inputs item 3
"`protocol_v3.md`; `protocol_draft_v2.md` has no residual force and must not be cited".

**M17 — the guidance-mandated reorder-invariance test is stated in a form that cannot hold.**
Appendix C: "**enrollment/reveal reorder invariance**: applying the same set of reveal-order events in any
admissible order gives the identical sequence of enrollment-indexed records, **the identical band
endpoints at each `n`**, and the identical decision." With `ell`-dependent enclosures there are many looks
at each `n`, and their endpoints depend on *which* events have been applied, not only on the set; only the
state after a given set is order-invariant. *Scenario:* G3 writes the test literally, it fails, and the
group either weakens a guidance-item-9 freeze test or spends the pre-freeze window on a non-defect.
*Fix:* "**enrollment/reveal reorder invariance**: for any admissible permutation of a set of reveal-order
events, the enrollment-indexed records, both enclosure sums and both band endpoints **after the whole set
has been applied** are identical, and the decision (kind and prefix) is identical; the *intermediate*
sequence of looks is order-dependent by construction and is not compared."

**M18 — a prespecified read-out that duplicates a monitored score.**
8.8 item 3: "**The success-only composite** (tier 0 alone) with the same band rules, as the prespecified
component-rule comparator." With `tiers = [Tier('success'), ...]`, tier 0 alone gives
`sign(success_cand - success_inc)`, which is `D_i` — the score already monitored as the success band.
*Fix:* either delete item 3 as redundant, or define what was meant ("the hierarchy with the cost tier
removed **and** the S1-restricted variant") and say which. As written it is an undefined instruction to an
implementer inside the frozen read-out list.

**M19 — the roster exclusion selects tasks on the cost dimension and this is not disclosed.**
3.2 item 4 excludes any task "whose reference solution does not pass `verify()` twice in a row ...
**under the load regime of the trial** ..., or whose reference verification **takes more than half of the
5 s verifier wall limit** in either run". 3.5 discloses task reuse and dilution but not this. *Scenario:*
the excluded set is exactly the tasks whose execution is slow on this host under load; the cost tier
decides 53.16% of pairs; the estimand is therefore defined on a roster pre-filtered on the dimension the
rule mostly measures. It does not threaten validity (the exclusion is in `F_0` and uses no model output),
but it changes what `mubar_n` is about, and an adversarial reader will find it. *Fix:* add to 3.5 a new
item 7: "**Timing-based exclusion, disclosed.** Rule 3.2 item 4 removes tasks whose *reference* solution
verifies slowly under the trial load. Because tier 1 decides most pairs in the pilot, the roster is
pre-filtered on the dimension the cost tier measures. The number of tasks excluded by rule 4, and their
reference verification times, are reported in the freeze bundle and beside every cost-tier statement."

**M20 — three unmapped failure modes remain.**
(i) **A repeated `plumbing_fail`.** 6.4 row 22's single action ends "then the next trial starts"; nothing
says what happens if the same condition recurs after the re-freeze. *Fix:* "a second `plumbing_fail` with
the same condition id stops the program; later trials need a new protocol version."
(ii) **An exception in the shadow reference rule.** 6.4 row 17 maps a **live-monitor** exception to
`trial_paused(monitor_exception)`; 8.9 introduces a second evaluator and gives no rule for its failure.
*Fix:* extend row 17 to "live-monitor **or shadow reference-rule** exception".
(iii) **A `receipt_mismatch` or a ten-failure abort inside the follow-up cohort.** 6.4 rows 12/13 and the
auto-abort say "trial_aborted ... before the next dispatch"; 9.3 says only that an early stop restricts
claim 3. *Fix:* add to 6.4 a sentence: "In the post-decision phase an abort truncates the follow-up cohort
only; the logged decision, `tau` and claims 2 and 3 stand, and the number of arrivals that did not run is
reported (9.3)."

---

## 5. MINORS

**m1.** 9.1 item 4 asserts "Under pair-synchronous execution **both episodes of the deciding pair are
already resolved** when the decision is taken at a reveal" and then contradicts it in the next sentence.
Under the 7.5 item 5 certificate a decision can be taken with one episode pending (`ARCHITECTURE` PG-2
says so). Delete the first clause; keep the conditional sentence.

**m2.** 7.2: "**There is no cross-pair interference**" against 7.4: "Carry-over from earlier pairs is
allowed (it is part of the history in `H_i`)". Replace with "no pair's record depends on a **later** coin,
which is what the design needs; carry-over from earlier pairs is allowed and is absorbed into `F_{i-1}`".

**m3.** 5.8 item 3: "5 repetitions x 6 smoke tasks x 2 workflows x 2 models x 2 concurrency levels = **240
calls**" — that is 240 *episodes*; a `self_test_repair` episode is 2 to 4 calls, and `c_max` is defined as
"the slowest **call**". Say "240 episodes, from which `c_max` is the maximum single-call duration".

**m4.** 15.2: "**No tracked artifact contains an absolute path, an account name, a host name, a URL or a
foreign commit id**", but the tracked `config.json` (Appendix B) holds
`"llama_cpp_commit": "4fea119de30f6a923992780f6fd5ccb0bee5d47d"` and two `hf_revision` values. Either
exempt the manifest fields by name in 15.2 or carry them as `*_sha256` as `ARCHITECTURE` T1 already does
for the chain.

**m5.** Enum divergence: protocol Appendix B `"id": "nm_enclosure_v3"` versus `ARCHITECTURE`
`rule_id = 'nm_guarded_v3'` (a *declared enum* in T1/T20/P1); `"protocol_version": "v3"` versus
`"v3-nm-guarded"`. One value, both documents.

**m6.** `ARCHITECTURE` 6.1 `sandbox.tmpdir = "<TMP>/labsbx"` versus protocol 5.7 `/private/tmp/labsbx`
(which 15.2 allowlists by exact string); `ARCHITECTURE` `anchor.minutes: 10` introduces a time-based
periodic anchor trigger that the protocol's 12.4 item 4 does not have.

**m7.** `ARCHITECTURE` 3.13 cites "protocol 12.5" for `status.json`; in v3 that is 14.7 (12.5 is "What the
anchors prove").

**m8.** 6.4's S-int scores every row 10/10b/11/11c/11d/11e pair "as a **tie in both scores**". That is the
right neutralization for a *forced failure*; it is the wrong one for row 11e, where position 2 runs
**solo** (`partner_concurrent: false`) and may succeed faster than it would have under load. Add to the
S-int definition: "for pairs whose only flag is `started_after_resume` with `partner_concurrent: false`,
the pair is additionally reported **as scored**, so the reader can see both."

**m9.** `ARCHITECTURE` `MonitorConfig.n_max: int = 569` is a code default for a non-amendable horizon.
Make it required (no default) so a config-load failure cannot install a horizon silently. Same for
`alpha_gate`, `rho`, `delta`, `n_min`.

**m10.** `COORDINATOR_DECISIONS.md` revision 2 item 5 still reads `r(92) = 0.4966`. The correct value is
`0.4950264429325317`. `protocol_v3.md` 1.3 records the correction; the coordinator file does not, and it
is cited as binding input 2 by both documents. Correct it there too, or the freeze bundle carries two
values of the same constant.

**m11.** 7.5 item 4's lower-bound premise mixes clocks: `latency_s` is `time.perf_counter()` (the pilot's
`agent.py:247`) while `ell` is built from `time.monotonic_ns()` worker stamps. On CPython/darwin both are
`mach_absolute_time`, so `ell <= latency_s` holds, but the containment audit is decision-defining code.
Add to 7.5 item 4: "both clocks are `mach_absolute_time` on this host; a preflight assertion records
`perf_counter` and `monotonic` deltas over a 10 s interval and refuses if they differ by more than 1 ms."

---

## 6. Disposition of critic findings N1-N22 as of v3

| id | sev | status in `protocol_v3.md` | status in `ARCHITECTURE.md` |
|---|---|---|---|
| N1 | HIGH | **closed** — program chain 12.1, rows 21-25, 14.4 item 2 | closed (4.3, PG-13) |
| N2 | HIGH | **partly** — row 22 exists but prescribes an unlawful repair for three of its six conditions (**M5**) | same defect (P4/P7) |
| N3 | HIGH | **closed** — 14.3 two code classes, rows 23/24 | closed, but the reporting-code list is cited from v2 §11.6 (**M16**) |
| N4 | HIGH | **closed** — `job_accepted`, rows 11c/11d/11e, 12.6, 14.5 | closed (PG-7) |
| N5 | MED | **closed** — row 18, `latency_s = 0.0` | closed (PG-9) |
| N6 | MED | **closed** — 5.5 worker partition | **not closed** (**M1**) |
| N7 | HIGH | **closed** — 2.2 three switches + 13.2 100%-pass freeze condition | **partly** — `--slot-prompt-similarity` missing (**M2**) |
| N8 | HIGH | **closed** — 5.8 item 6 dress rehearsal | closed (§12 freeze gate) |
| N9 | MED | **closed** — row 20 | closed (PG-10) |
| N10 | HIGH | **closed** — 11.3 analytic table + 11.5 specified replay | not applicable |
| N11 | HIGH | **closed** — 14.1 items 6-7 rule-block hash and `winstats` pin | closed (6.2), but the rule block it hashes is the v2 hierarchy (**B1**) |
| N12 | MED | **partly** — `task_uids` satisfy none of the four forms (**M13**) | same, papered over in a parenthesis |
| N13 | MED | **closed** — 12.4 items 1-3 | closed (PG-12) |
| N14 | MED | **closed** — 5.8 item 2 non-streamed test | not represented |
| N15 | MED | **closed in rule, wrong in arithmetic** (**M12**) | a *third*, different cap formula in 6.1 |
| N16 | MED | **closed** — 14.3 third row | `thermal` still present (**M15**) |
| N17 | MED | **closed** — frozen S-int clause in the decision sentence | not represented in the builder spec |
| N18 | LOW | **closed** — 8.9 | — |
| N19 | MED | **closed in text** — shadow at every evaluation | **reopened**: no second code path (**B2**), and no look at call events (**B3**) |
| N20 | LOW | **closed** | — |
| N21 | LOW | **closed** | `thermal` retained (**M15**) |
| N22 | LOW | **closed as freeze conditions** | the constant-coverage test will fail on **M12** |

---

## 7. Claims: what the protocol says that it cannot support

1. **"A DEPLOY decision is unreachable by construction ... whatever the outcomes"** (1.3, echoed in
   Appendix E and `ARCHITECTURE` §0) — false; **B4**.
2. **"The roster gives at most 569 pairs"** (1.3, 1.4 claim 8, 11.3, Appendix E) — under the protocol's
   own stratified pairing it is 568; **B5**.
3. **"the two positions of one pair share ... the host, and that is inside the estimand"** (7.2) — true,
   but the estimand is silent about the *asymmetric* sharing created by the 4.46x duration ratio and by
   the execution lock (**M10**, **M11**). The phrase "when one episode of each runs **side by side**"
   (7.4) is not what is measured for most of the slow arm's duration.
4. **"There is no cross-pair interference"** (7.2) — overstated; **m2**.
5. **"`mu_i = 0` exactly"** for T4 (1.2, 7.4, 10.2 item 4) — correct, but only under a coupling the
   protocol does not state; **M8**.
6. **"the reverse contrast uses new disjoint tasks and assignments"** (10.3) — the tasks are not disjoint;
   **M9**.
7. **"the cap can bind ... only after at least four failed tries and one server restart"** (5.6) — the
   sentence is fine; the number 3,306 attached to it is not (**M12**).
8. **14.2 row 10, "all interval/decision code ... `lab_reference_rule`"** — promises a file that the
   implementation contract deletes; **B2**.

Missing limitations that should be added to 1.1's "What it does not deliver" list:
the arm-asymmetric contention and lock transfer in the cost tier (**M10**, **M11**); the timing-based
roster filter (**M19**); and, explicitly, "no disjointness of tasks across trials" (**M9**).

---

## 8. What must happen before a re-audit

In this order. Items 1-7 are the blockers and none of them is a judgement call — each is two documents
stating two different rules, or a sentence that is arithmetically false.

1. Decide, in one place, whether `ARCHITECTURE.md` is subordinate to `protocol_v3.md` sections 6.2-6.4, 7
   and 8. Write that subordination into `ARCHITECTURE` §0 and add the freeze test that
   `rule_block_sha256(config.json)` matches the protocol's own rule-block table.
2. **B1**: two tiers, tolerance 0.05, certificate constant 0.95, everywhere.
3. **B2**: add `lab_reference_rule` as a real second code path, or amend 8.9/14.2/14.3/6.4 row 24 and
   re-open N19 in writing.
4. **B3** and **B6**: settle the look cadence in the protocol, delete `metrics_scrape` from the
   reveal-order list, make the state machine and `replay()` consume the same triggers, and retire PG-1
   and PG-2 from "coordinator".
5. **B4**: replace the false unreachability sentence in all four places.
6. **B5**: stratified pairing only, `N_P <= 568`, no mixed pair, and the horizon number corrected
   throughout.
7. **B7**: a dedicated worktree, or a `worktree_drift` outcome row.
8. M1-M20 as written above; M5, M6 and M7 are the ones most likely to force a post-freeze amendment,
   because each hands an operator a choice between two frozen consequences **after** outcomes exist.
9. Re-run the extended replay (11.5) only after the hierarchy is fixed: every cell of 11.5 currently
   assumes the two-tier 0.05 kernel, while the code as specified would produce three-tier 0.10 scores.

Ranked list of what will force a post-freeze amendment if frozen as is: (1) the hierarchy mismatch **B1**,
discovered at the first `pairs.csv`; (2) the shadow/replay length mismatch **B3**, at pair 1 of T4;
(3) the missing `lab_reference_rule` **B2**, at freeze-bundle assembly; (4) the `plumbing_fail` /
row-24 conflict **M5**, between T4 and T2 — which is exactly where the critic predicted the program would
improvise; (5) the containment-violation double consequence **M6**; (6) a concurrent checkout in the
shared clone **B7**.

*Prepared and checked by an AI agent session; not human peer review or author sign-off.*
