# live_ab_validation: frozen pre-registration for issue #12 (independent CPU validation of the #11 monitor)

Version string `v1-cpu-validation`. **This document is written and committed before any simulation outcome of this
study exists.** No cell, parameter, seed, horizon, estimator or reported quantity in it may be changed after the first
simulated outcome is produced. Every number in sections 4, 6 and 9 is either an exact arithmetic consequence of the
frozen radius formula, an exact enumeration over a finite outcome table, or an exact expectation under a frozen law;
none of them is a simulation result, and none of them is a prediction of a reported rate.

| field | value |
|---|---|
| owner | issue #12, procedural-independence author (an AI agent session) |
| purpose | validate the #11 live monitor's decision arithmetic on synthetic known-truth streams **before** #11's results count as evidence |
| binding design | the root's frozen acceptance design in GitHub issue #12, items 1-6, reproduced and implemented here item for item |
| binding formula source | `reviews/arxiv_live_design_guidance.md` item 3, SHA-256 `a71965986165d56915a557a1a43998d9eb76a4e800dba670281c93720037ad1b` |
| pinned primitive | `src/winstats.py`, SHA-256 `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` (the same file hash the #11 protocol pins) |
| vocabulary alignment | `experiments/live_ab/design/protocol_FINAL.md` sections 1, 3 and 11 only, SHA-256 `3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2` |
| how the three pins above are checked | `F18_pinned_file_hashes` **opens each of those files, hashes it, and compares** the digest against `cells.json` and against the string printed here, and does the same for the three sources in `pinned/` against `pinned/PINNED.json`. The three pins are the files **as they stand at the freeze commit**, not as they stood at the repository state below: the `protocol_FINAL.md` pin moved when the #11 quiescence gate added its section 5.7.1, and the check exists because the previous one - a string-to-string comparison of two documents - could not see that (section 0.2b). If any of these six files changes again, `F18` fails and the pin must be recomputed before the commit. |
| machine-readable twin | `experiments/live_ab_validation/cells.json` (normative for every numeric value; this document and that file must agree, and fixture `F15_protocol_config_agreement` asserts it over the tables listed in section 11) |
| repository state at writing | `de31b6cf124b3723eb9986a03318f1ae4f935353` |
| pre-freeze revision | revised **twice**, after the adversarial pre-registration audits `PREREG_CHECK.md` and `PREREG_CHECK_2.md`, and **before any simulation outcome of this study existed**; see sections 0.1, 0.2 and 0.2b |
| environment | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1, macOS arm64. CPU only. No model call, no API call, no network, no new dependency. |

---

## 0. Protocol at a glance

Eight fixed cells = four outcome laws x two delay rules. Per cell, independent simulated *programs*; each program is
four independent *trials*; each trial enrolls at most 2,000 pairs and is monitored at every enrollment prefix by three
constructions (the partial-data adapter under test, a matched completed-prefix construction, and an intentionally
naive completed-only rule that is invalid under informative delay). The truth of every cell is known by exact
enumeration over a six-atom table, so every coverage and decision error is checkable without simulation. The study
reports per-gate ever-miscoverage, trial-level false deploy and false harm, family-level any-erroneous-decision,
no-decision fraction, capped decision prefix, unresolved fraction and compute counts, each with a Wilson Monte Carlo
interval, and retains every unfavourable or inconclusive row.

### 0.1 What had already been executed when this document was frozen

Root item 2 requires the protocol commit to precede **any** simulation outcome. No cell of section 4 has ever been
run, at any horizon, with any seed, and no grid, coverage, decision or timing number exists. Four things *had* been
executed before the freeze, and are named here so that a reader reconstructing the freeze from this document alone
is not misled:

1. **The deterministic fixtures of section 11** (`vfixtures.py`), which are hand-derived acceptance cases, not cells.
2. **The randomized property tests in `tests_validation.py`** - `TestRandomisedContainment` over 300 seeds,
   `TestLargeProgramSmoke` with a 400-pair program, and `TestCostEnclosurePath` over eight 45-pair programs. These
   are correctness property tests of the enclosure arithmetic. They use `random.Random` with fixed integer seeds,
   they touch **no namespace-0 `SeedSequence` stream**, they compute no rate, and their streams are not the cells of
   section 4 - `TestCostEnclosurePath` is shaped like the section 4 generator but shortens the long delay block, so
   it is not a cell at any horizon. They establish no operating characteristic and none is claimed from them.
3. **Three deterministic checks run while writing this protocol**, all re-checked at fixture time: the radius
   agreement of section 2.2, the `winstats.compare` grid check of section 4.1, and the `2,878,680`-state enclosure
   sweep of section 2.5 that located the `128` tolerance-boundary states.
4. **The exact expected-path arithmetic of section 6**, which is enumeration over a finite outcome table and contains
   no random draw.

Nothing in that list is a result of this study, and the report repeats this section in full.

### 0.2 The pre-freeze revision

This document and `cells.json` were revised after the adversarial pre-registration audit in `PREREG_CHECK.md`
and **before any simulation outcome existed**. The audit was commissioned for exactly that purpose. Because neither
file had been committed or frozen when the audit was written, section 14's change control had not yet attached, so
this is not a version bump; it is recorded here rather than absorbed silently. A **second** audit followed, and the
second revision is recorded separately in section 0.2b.

**The scientifically substantive change is section 4.4: the eight cells did not exercise the cost/latency enclosure
path at all** - the tier that carries almost the whole composite effect in the live trial this monitor is built for.
The cells were changed to exercise it, now, before any outcome exists.
`cells.json` -> `pre_freeze_revision` lists every change and everything it left alone. The atom weights, `mu_h`,
`mu_s`, the delay rules, the seeding, the reveal schedule, the estimators, the flag rule and the precommitted
positive control are unchanged; section 6.1 is unchanged and was reproduced exactly by the recomputation.

**The revision also carried a one-directional leak of #11 detail into this document, and concealing it would be
worse than the leak.** The adversarial checker was not bound by the independence constraint and read the #11 monitor
in full; its report quotes #11's decision-label alphabet, its `n = 0` and horizon branches, its collapsed-flag rule
and its cost certificate. The author of this protocol read that report. Section 12.1 states what follows from that
and, more importantly, what does not.

### 0.2b The second pre-freeze revision, and the one wrong line it fixed

A second adversarial pass, `PREREG_CHECK_2.md`, re-tested every finding of the first audit against the revised files
and raised four findings against this pre-registration. All four were closed here, again **before any simulation
outcome of this study existed** and again without touching a cell, a weight, a delay rule, a seed, an estimator, the
flag rule, the positive control, or any value in sections 4, 6 or 9. `cells.json` ->
`pre_freeze_revision.second_revision` lists them. Three deserve to be stated in the body of this protocol:

1. **The `protocol_FINAL.md` pin was stale, and nothing could have caught it.** `03028374...` was that file at the
   repository state in the header table; the #11 host-quiescence work then added its section 5.7.1 and the file's
   digest became `dc681784...`. The check that was supposed to guard the pin asserted only that the same 64-hex
   string appeared in this document and in `cells.json`. **It never hashed a file**, so two documents could agree
   with each other while both disagreed with reality. That is the same shape of defect as a gate that always
   passes, and it is the second one this study's audits have found. `F18_pinned_file_hashes` now opens and hashes
   all six pinned files. A pre-registration whose provenance pin is stale at the moment of commit is not pinned.
2. **`F15` guarded about two thirds of what sections 11 and 13 claimed for it.** A mutation sweep over every numeric
   token of every table row of this document showed whole frozen tables compared against nothing - including the
   section 2.5 enclosure-row table, which decides ground truth for the whole cost-path design, and over which
   `cells.json` was declared normative. The check was extended to them and the claim was narrowed to the list of
   tables the code actually walks; section 11 now states that list and states that anything outside it is outside
   the fixture's reach. **The sweep is now in the repository**, as
   `tests_validation.f15_mutation_coverage` and `TestF15MutationCoverage`, so this paragraph is a number rather
   than a promise: it perturbs every numeric token of every table row of this document, one at a time, and asserts
   that `F15` reports each one. On the files as frozen it reports **`656` of `773`** mutations (84.9%), with
   **zero** missed in sections 2.2, 2.5, 4.2, 5, 6.1, 6.3, 6.4, 7.1, 8.2, 9.1 and 9.3, which the test asserts
   section by section. The `117` it still misses are cross-references and labels rather than frozen values -
   "guidance item 4", "section 9.5", `Q1`/`Q3`, `#11`, the `P(Z=+1)` column headings and digits inside a commit id -
   and no claim is made about them. Before this revision the same sweep reported `516` of `760`, with `44` of the
   `44` numbers in the section 2.5 table unguarded.
3. **Two sentences attributed to `F17` an assertion it does not make** - that it asserts the full `128`-state
   disagreement set of section 2.5. It asserts `28` boundary states over the `47,484`-state subgrid it sweeps.
   Section 2.5 said this correctly; the machine-readable twin and the section 11 register row did not, and a reader
   quotes the register row. Both were corrected to match section 2.5, which is the older and the true statement.

What this revision did **not** do is also on the record: `PREREG_CHECK_2` raises a confounding of the measured
scaling exponent `beta` in section 8.1 (its two horizon points sit in different cells, so `beta` absorbs the
`N` -> `A` delay branch as well as the horizon). That finding is **open**, is not closed here, and section 8.1
still reads as it did.

---

## 1. Purpose, and what this can and cannot establish

### 1.1 Purpose

The #11 program (`experiments/live_ab/`) monitors a prospective randomized live-stopped A/B trial with a decision rule
fixed by the root's guidance. That rule is arithmetic: at an evaluation trigger it reduces a stream of partially
revealed pair outcomes to four numbers and a label. **This study validates that arithmetic**, and only that
arithmetic, on synthetic streams whose truth is known in closed form, so that a defect in the monitor is found before
#11's numbers are read as evidence about anything.

### 1.2 What a successful run of this study CAN establish

1. That the #12 implementation of the guidance formula, applied to the frozen partial-data adapter, produced
   two-sided bands whose **simultaneous ever-miscoverage of the bounded arbitrary-running-mean target** did not
   detectably exceed `alpha_gate = 0.00625` per band, on these eight laws, at this Monte Carlo resolution.
2. That the trial-level false-deploy and false-harm event rates and the family-level any-erroneous-decision rate did
   not detectably exceed `0.0125` and `0.05` respectively, on these eight laws, at this resolution.
3. That an intentionally naive completed-only rule, which is invalid under informative delay, **does** exceed its
   nominal rate in the outcome-dependent-delay cells - i.e. that the measuring apparatus can detect a real violation
   and is not returning zeros because of a bug (section 9.4, the positive control).
4. That the #12 band arithmetic and the pinned #11 monitor agree numerically on a frozen fixture set, or that they do
   not (section 12).
5. Deterministic behaviour of the adapter on the seventeen fixture scenarios of section 11, including that **every
   ultimately resolved score lies inside every prior bound on its own path**.
6. That the **cost/latency enclosure path** - the narrowing of an unresolved pair's hierarchy enclosure from the
   elapsed cost of a still-running episode - carries the containment and coverage properties above, on these eight
   laws. This is the tier that carries almost the whole composite effect in the live trial, and section 6.4 prices
   how much of each cell exercises it.

### 1.3 What it CANNOT establish, stated before any outcome exists

1. **It establishes nothing causal.** Coverage here is coverage of `mubar_n = (1/n) sum_{i<=n} E[Z_i | F_{i-1}]`, a
   bounded arbitrary-running-mean target of a synthetic stream. It does **not** establish the assumptions needed for
   a causal pair-orientation interpretation of `mubar_n` in the live study - pre-enrolled nonoverlapping arrival
   positions, one fresh coin per pair logged before either episode is dispatched, no dependence of a task's record on
   a later coin, no cross-pair interference, an operator who does not act on coins, and a fixed scheduling and
   resource policy. Those are properties of the live apparatus of `protocol_FINAL.md` sections 4, 5 and 7.4. **No
   simulation can supply them**, and this study does not attempt to. Section 10 states the boundary again in full.
2. It says nothing about the #11 harness outside the monitor arithmetic: not the orchestrator, the coin path, the
   event log, the serving stack, the verifier, the sandbox, the usage accounting or the anchoring.
3. It says nothing about laws outside the eight frozen cells. In particular **all four outcome laws are i.i.d. across
   enrolled pairs, so `mubar_n = mu` is constant in `n`**; drift in the conditional mean is *not* exercised. This is a
   declared gap, not an oversight: a drifting target is the case the guidance's item 4 warns about
   ("the stationary no-split conjunction result is not the default for the proposed running-mean target under drift"),
   and it is outside the root's eight-cell design. Observe that the *observed* process is nevertheless far from
   i.i.d., because the enclosure sequence at a fixed pair changes over looks and, in the asymmetric-delay cells,
   changes in a way that depends on that pair's own outcome.
4. It is not a power study of the live program, and it is **not** evidence that partial-information monitoring is
   faster, better or preferable. **No pathwise speed dominance is claimed for the latest-enrolled-prefix
   normal-mixture monitor** (section 8.4).
5. Absence of an exceedance flag is not proof that a bound holds. At 2,000 programs the design can only flag a
   per-gate rate at or above 1.280x its nominal value, and at 5,000 programs at or above 1.176x (section 9.3). A
   violation smaller than that would pass unflagged.
6. Nothing here licenses any sentence forbidden by `protocol_FINAL.md` section 1.5. In particular this study is
   **not** empirical type-I calibration of the live trials, and the live program's own A/A trial (T4) remains an
   implementation check and not a calibration, whatever this study reports.
7. **The cost meter and the reveal clock are not tied to each other** (section 4.3). An episode's final cost is
   fixed by its atom while its duration comes from the delay rule, so a cheap episode may reveal second. A
   latency-coupled model - where the cheaper arm tends to finish first - would put the *expensive* arm in the
   pending position more often and would therefore narrow the cost enclosure **more** often than this study does.
   This is a declared simplification in the conservative direction for exercising the path, and it is not a claim
   about the live apparatus, where cost is `latency_s` and the two clocks are the same clock.
8. **`certified` is not compared against #11** (section 12.2). The two implementations hold incompatible
   definitions of the collapse flag, so this study compares enclosure endpoints and leaves the flag out of scope,
   as a named and reported difference rather than a silent one.

---

## 2. The rule under test: exact adapter and parameters

### 2.1 Frozen parameters

| symbol | value | source |
|---|---|---|
| `alpha_gate` | `0.00625` per band | guidance item 4; program `.05` / four trials = `.0125` per trial / two monitored scores |
| `rho` | `100.` | guidance item 4, fixed reproducible specification |
| `variance_process` | `V_n = n` | guidance item 3; scores lie in `[-1,1]` under balanced orientation |
| `delta` | `0.03` | guidance item 6, the success margin |
| `n_min` | `100` | guidance item 6, minimum enrolled pairs before any decision |
| `N_max` | `2,000` enrolled pairs per trial | root item 4, the resource cap |
| `W` (drain) | `200` enrollment ticks | section 7.3, the cap endpoint rule |
| trials per program | `4` | root item 2 / the #11 allocation |
| program budget | `0.05` = 4 x `0.0125` | guidance item 4, union bound |
| positive direction | candidate favourable, matching the live candidate label | root item 2 |

### 2.2 The radius

```
r(n) = sqrt((n + rho) * log((n + rho) / (rho * alpha_gate**2))) / n
     = sqrt((n + 100) * log((n + 100) / 0.00390625)) / n
```

**What actually computes this radius, stated exactly.** `vband.radius_from_formula` **calls the pinned primitive**:
it returns `winstats.normal_mixture_radius(n, alpha=alpha_gate, rho=rho, variance_process=n)`, and
`vband.normal_mixture_band` calls it, so **every `L` and `U` this study reports comes from `src/winstats.py`**. That
is the guidance's own instruction - item 3 names that primitive - and it is the right choice, because the point of
this study is an independent reading of the *rule*, not a second implementation of a library function.

The independent transcription lives beside it, not underneath it: `vfixtures.literal_radius` writes
`sqrt((n+rho)*log((n+rho)/(rho*alpha**2)))/n` out by hand from the guidance text and is used **only** to cross-check
the pinned call. What that cross-check establishes is narrow and worth stating narrowly: that `vband` passes the
intended arguments - in particular `variance_process = n`, i.e. `V_n = n` for scores bounded in `[-1,1]`. It is not
independent evidence about the primitive itself.

Fixture `F14_radius_sweep` asserts the two agree at **strict float equality** for **every** `n = 1 ... 20,000` - not
at a tolerance, and not at a sample of points. That sweep was run while writing this protocol and the number of
mismatches was `0`; the fixture re-runs it, in 0.05 s.

**Where the two-sided level comes from.** The `1 - alpha_gate` level used throughout section 9 is *simultaneous over
all `n` and two-sided*, from `paper/theory.tex`, Theorem *Normal-mixture confidence sequence* (`thm:normal_cs`):
with `B_alpha(v) = sqrt((v+rho) log((v+rho)/(rho alpha^2)))` and `C_n = [muhat_n -+ B_alpha(V_n)/n]`,
`P{mubar_n in C_n for every n >= 1} >= 1 - alpha`, and `C_n` may be intersected with `[-1,1]`, with `V_n = n` for
balanced pair scores. It is **not** a per-tail level, so section 9's nominal bounds are not off by a factor of two;
each one-sided component is separately bounded by the same `alpha` because its event is contained in the two-sided
one. The partial-information form this study actually monitors is `paper/asynchronous.tex`, Theorem *Pathwise
transfer of the full-score confidence sequence* (`thm:async_cs`), which gives the same `1 - alpha` simultaneously
over every `(n, t)` when the enclosures are certain.

| `n` | `r(n)` | `n` | `r(n)` | `n` | `r(n)` |
|---|---|---|---|---|---|
| 100 | 0.465693 | 500 | 0.169296 | 1,000 | 0.117486 |
| 200 | 0.290460 | 566 | 0.158252 | 1,500 | 0.095863 |
| 300 | 0.226438 | 695 | 0.141839 | 2,000 | 0.083230 |
| 398 | 0.192246 | 864 | 0.126625 | | |

Smallest `n` with `r(n) < x`: `x = 0.45` -> 105; `0.40` -> 124; `0.30` -> 191; `0.28` -> 212; `0.23` -> 293;
`0.03` -> 17,097.

### 2.3 The adapter (construction 1, the object under test)

At an evaluation trigger, let `n = N(t)` be the **current full enrolled prefix**. Every enrolled pair `j <= n` keeps
its immutable enrollment position and contributes an enclosure `[lower_j, upper_j]` for each of the two scores. Then,
for each score `j` in {hierarchy, success}:

```
r    = r(n)
L_j  = clip(sum(lower_j[:n]) / n - r, -1, +1)
U_j  = clip(sum(upper_j[:n]) / n + r, -1, +1)
```

No prefix other than the current full enrolled prefix is used; no lower bound is maximized over prefixes; nothing is
appended as a new observation; nothing is divided by the number completed; nothing is sorted by reveal time; no slow
pair is dropped and no pending outcome is imputed.

### 2.4 The decision conditions

Evaluated only at looks with `n >= n_min = 100`:

- **DEPLOY** iff `L_hierarchy > 0` **and** `L_success > -delta`, **both at the same look** (the same-look conjunction).
- **RETAIN_INCUMBENT** (harm) iff `U_hierarchy < 0`.
- Otherwise no decision at that look.

**The decision is the first crossing. The simulated path is nevertheless carried on to the finalization look**, so
that the all-`n` ever-miscoverage read-out of section 9.1 can be taken; `tau` and the decision are whatever the first
crossing said and are never revised by a later look. Continuing past the decision is a **bookkeeping device of this
simulation** and is not what the live trial does: there, the first crossing stops enrollment and the trial. The two
readings are separated here because they were in tension in the pre-audit draft, and because they have different
compute profiles - under this rule every trial runs to tick 2,200, so runtime is close to cell-independent and the
section 8.1 projection does not depend on which cells decide early.

There is no retention of earlier crossings and no intersection over looks. If neither
condition has fired by the finalization look of section 7.3, the trial ends in **NO_DECISION**. The two conditions are
checked in the order above; if both were to hold at the same look the trial is recorded as `CONFLICT` and the path is
retained and reported (it cannot occur when `L_h > 0` and `U_h < 0` are both required, since `L_h <= U_h` always, but
the branch is implemented and asserted rather than assumed).

### 2.5 Scores and enclosures

Per enrolled pair `i`, two bounded scores, both in `[-1,1]`:

- **hierarchy** `Z_i`: the signed preference of candidate over incumbent under the two-tier hierarchy
  `success > cost`, cost eligible only when both episodes succeed, joint failures tie.
- **success** `D_i = s_candidate - s_incumbent` in `{-1, 0, +1}`.

Enclosures start at `[-1, +1]` and narrow **only on logically certain facts**. A revealed episode is final: both its
success and its final cost are known. A pending episode has success in `{0,1}` and cost in `[ell, cost_cap]`, where
`ell` is its elapsed-cost lower bound (section 4.3) and `cost_cap = 100` is the frozen resource cap.

| state of pair `i` at the look | hierarchy enclosure | success enclosure |
|---|---|---|
| enrolled, neither episode revealed | `[-1, +1]` | `[-1, +1]` |
| candidate revealed, `s_C = 0` | `[-1, 0]` | `[-1, 0]` |
| candidate revealed, `s_C = 1`, cost tie and incumbent-cheaper both still feasible | `[-1, +1]` | `[0, +1]` |
| candidate revealed, `s_C = 1`, incumbent-cheaper infeasible, tie feasible | `[0, +1]` | `[0, +1]` |
| candidate revealed, `s_C = 1`, both infeasible | `[+1, +1]` | `[0, +1]` |
| incumbent revealed, `s_I = 0` | `[0, +1]` | `[0, +1]` |
| incumbent revealed, `s_I = 1`, cost tie and candidate-cheaper both still feasible | `[-1, +1]` | `[-1, 0]` |
| incumbent revealed, `s_I = 1`, candidate-cheaper infeasible, tie feasible | `[-1, 0]` | `[-1, 0]` |
| incumbent revealed, `s_I = 1`, both infeasible | `[-1, -1]` | `[-1, 0]` |
| both revealed | `[Z_i, Z_i]` | `[D_i, D_i]` |

**The feasibility test is the frozen predicate, evaluated exactly as `compare` evaluates it**, with `c` the revealed
arm's known cost, `ell` the pending arm's elapsed lower bound, `rtol = 0.05` and `atol = 0`:

```
pending arm cheaper is feasible  iff  c - ell   > atol + rtol * max(c, ell)
tie is feasible                  iff  ell <= c  or  ell - c > atol + rtol * max(c, ell) is FALSE
revealed arm cheaper is feasible iff  cost_cap - c > atol + rtol * max(c, cost_cap)   (true for every atom here)
```

Each row is a logical consequence and nothing more. `s_C = 0` forces `Z_i in {0, -1}` because the candidate cannot win
a success-first hierarchy while failing, and `D_i in {-1, 0}`; the cost tier can then never become eligible, so no
elapsed cost narrows those rows further. `s_C = 1` permits `Z_i = +1` (incumbent failed), `0` or `-1` (both succeed,
cost decides), so the hierarchy enclosure does not narrow **on the success tier** - and the three `s_C = 1` rows are
exactly what the **cost** tier can still add. Symmetrically for the incumbent. Absence of failure so far is never read
as success; nothing is imputed. Reveal order updates the existing enrollment-indexed record and never appends.

Nothing is assumed about which arm will win; each row is what remains after the impossible completions are removed.
Fixture `F17_atom_cost_table` checks these states against `vband`'s own enumeration and against the true score.

**In exact arithmetic the two conditions are thresholds on the elapsed cost**: the branch favouring the pending arm
dies at `ell >= (1 - rtol) c`, and the tie dies at `ell > c / (1 - rtol)` - for a `(10, 40)` cost pair, elapsed
fractions `0.2375` and `0.26316` of the pending arm's own duration. That closed form is the right way to read the
table, and it is **not** bit-identical to the predicate, because `c / (1 - rtol) - c` and `rtol * (c / (1 - rtol))`
round differently in IEEE double. Over the whole frozen state grid - every `(atom, revealed arm, d, age)` with `d`
in the section 4.2 delay blocks, `2,878,680` states in all - the two readings disagree on exactly **128** states, all
of them the single boundary point `ell = c / (1 - rtol) = 200/19` reached at elapsed fraction `5/19`, where the
predicate calls the tie infeasible and the closed form calls it feasible.

**The predicate governs, there and everywhere.** It is what `vband` computes and what `compare` itself uses.
**The claim that stood here, that "this study's numbers in sections 6.3 and 6.4 are computed with it", is FALSE and
is withdrawn** (coordinator ruling 35(b), 2026-09-20; recorded with its before/after text in section 14.1
correction 2). The fact: sections 6.3 and 6.4 were computed with the **closed-form paraphrase** of the preceding
paragraph, which differs from the governing predicate in exactly the `128` named boundary states. The frozen 6.3 and
6.4 values are **not** edited (ruling 35(a)); the predicate-reading recomputation is deposited beside them in
`ADDENDUM_SECTION6.md` (ruling 35(c)), and nothing operative moves, because the predicate is what `vband`, `vgen`,
`vcompare` and `F17` implement (ruling 35(d)). The `2,878,680`-state sweep was run once while
writing this protocol (section 0.1 item 3); `F17_atom_cost_table` re-checks `47,484` of those states at run time,
asserts that every disagreement it finds lies at elapsed fraction `5/19`, and asserts that it finds exactly the `28`
boundary states that grid reaches - a count, so that the check cannot pass by failing to reach the boundary at all.
Stated now because it decides ground truth: had it been found after the first outcome, it would have been a choice
between two answers rather than a fact about one.
It also means the grid does reach an exact tolerance boundary - the enclosure one - even though section 4.1 keeps the
`|delta| = tol` *final-score* boundary in the fixtures.

**A point is not a certificate.** A hierarchy enclosure that the cost tier narrows to a point while an episode is
still running is logically as tight as a resolved one, but it has no final-score certificate, so it is **not** marked
certified and `n_certified` does not count it. Both counts are reported (section 9.5). Section 12.2 fixes what this
study does and does not compare about that flag.

---

## 3. The three compared constructions (root item 5)

All three use identical `alpha_gate`, `rho`, `V = index`, `delta`, `n_min` and the same-look conjunction. They differ
only in which index and which observations enter the mean.

| id | construction | index used | status |
|---|---|---|---|
| `ADAPTER` | the partial-data adapter of section 2.3 on the current full enrolled prefix `n` | `n` = enrolled pairs | **the object under test** |
| `CPREFIX` | the matched completed-prefix construction: `k(t) = max{k : every pair 1..k is fully resolved}`; band `= mean(score[1..k]) -+ r(k)`, decisions gated at `k >= n_min` | `k` = longest fully resolved prefix | valid for **its own** running target |
| `NAIVE` | completed-only: `C(t) = {j <= n : pair j fully resolved}`, `m = card(C)`; band `= mean(score over C) -+ r(m)`, decisions gated at `m >= n_min` | `m` = count completed | **INVALID under informative delay**; reported only to exhibit the failure mode |

**`NAIVE` is labelled invalid, by construction and in every table, caption and file.** `C(t)` is an outcome-selected
subset, not a prefix of the enrollment filtration, so no martingale argument applies to it and its nominal level is
not a guarantee. It is included because root item 5 requires the contrast, and because it is the positive control of
section 9.4.

**`CPREFIX` refers to its own running target.** `CPREFIX` at index `k` is a band for `mubar_k`, the running
conditional mean over the first `k` enrolled pairs. **It is not a bound on the current all-enrolled mean `mubar_n`,
and this study never says or implies that it is.** Under the four i.i.d. outcome laws of section 4 the two targets are
numerically equal (`mubar_k = mubar_n = mu` for every `k` and `n`), which is why one ground-truth value suffices for
all three constructions in the reported tables. **That equality is a property of these particular data-generating
processes, not of the constructions**, so this study cannot and does not distinguish the two targets empirically;
it compares operating characteristics at a common numerical truth and nothing more.

**No speed claim.** Decision prefixes are reported for all three constructions as marginal distributions. **No
pathwise dominance of any construction over any other is claimed**, in either direction. The adapter's band at prefix
`n` can be *wider* than `CPREFIX`'s band at `k < n`, because the enclosure slack contributed by unresolved pairs can
exceed the radius gained from the larger index; the reachability arithmetic of section 6.3 shows this happening in
every cell at `n = 100`. The three constructions are also evaluated at different indices on the same path, so their
decision prefixes are not comparable as a paired speed statistic and are never presented as one.

---

## 4. The eight cells

Four outcome laws x two delay rules. Cell ids `C1 ... C8` and cell indices `0 ... 7` are frozen and are the seeding
coordinate of section 5.

| cell | index | outcome law | delay rule | `mu_h` | `mu_s` | escalation-eligible (section 7.2) |
|---|---|---|---|---|---|---|
| `C1` | 0 | `L1` aa_null | `N` noninformative | `0.00` | `0.00` | no |
| `C2` | 1 | `L1` aa_null | `A` outcome-dependent asymmetric | `0.00` | `0.00` | no |
| `C3` | 2 | `L2` pref_boundary | `N` | `0.00` | `+0.25` | **yes** |
| `C4` | 3 | `L2` pref_boundary | `A` | `0.00` | `+0.25` | **yes** |
| `C5` | 4 | `L3` success_boundary | `N` | `+0.40` | `-0.03` | **yes** |
| `C6` | 5 | `L3` success_boundary | `A` | `+0.40` | `-0.03` | **yes** |
| `C7` | 6 | `L4` favorable_alt | `N` | `+0.45` | `+0.20` | no |
| `C8` | 7 | `L4` favorable_alt | `A` | `+0.45` | `+0.20` | no |

**No ninth cell exists and none may be added.** No cell may be added, removed, reweighted or re-parameterized after
any simulated outcome of this study exists, and in particular not after inspecting whether results are favourable.

**The cells were revised once, before any simulation was run.** The revision followed the adversarial
pre-registration audit `PREREG_CHECK.md`, which found that the eight cells never exercised the cost/latency
enclosure path. Sections 4.1, 4.3 and 4.4 carry that revision. It changed the atom cost columns and added an
elapsed-cost accrual rule; it did **not** change the eight cells themselves, the atom weights, `mu_h`, `mu_s`, the
delay rules, the seeding or the reveal schedule, and the ground truth is still exact enumeration over the same six
atoms. **No simulated outcome of this study existed when it was made, and none exists now.**

### 4.1 The outcome laws: a six-atom table, drawn by exact integer arithmetic

Each enrolled pair draws one atom. An atom fixes the candidate's success `s_C`, the incumbent's success `s_I`, **and
the two episodes' final costs `c_C` and `c_I`**, from which the cost tier follows. Weights are integers out of
`10,000`; sampling is `k = rng.integers(0, 10000)` followed by a frozen cumulative-threshold lookup in the atom order
below, so the law is exact in integer arithmetic and carries no floating-point rounding.

| atom | `s_C` | `s_I` | `c_C` | `c_I` | cost tier | `Z` | `D` | meaning |
|---|---|---|---|---|---|---|---|---|
| `BB+` | 1 | 1 | 10 | 40 | candidate faster beyond tolerance | `+1` | `0` | both succeed, candidate preferred |
| `BB0` | 1 | 1 | 40 | 40 | equal costs, a tie | `0` | `0` | both succeed, cost tie |
| `BB-` | 1 | 1 | 40 | 10 | incumbent faster beyond tolerance | `-1` | `0` | both succeed, incumbent preferred |
| `C>I` | 1 | 0 | 10 | 40 | ineligible | `+1` | `+1` | candidate succeeds, incumbent fails after consuming 40 |
| `I>C` | 0 | 1 | 40 | 10 | ineligible | `-1` | `-1` | incumbent succeeds, candidate fails after consuming 40 |
| `FF` | 0 | 0 | 40 | 40 | ineligible | `0` | `0` | joint failure, ties, cost never eligible |

The `Z` column is exactly the two-tier hierarchy `success > cost` with cost eligible only when both succeed, and it
is **unchanged by the cost columns**: with `tol = 0.05 * max(c_C, c_I) = 2.0`, `|10 - 40| = 30 > 2` is decisive in
the stated direction and `|40 - 40| = 0` ties. `F17_atom_cost_table` asserts that every row reproduces its `Z` and
`D` through `src/winstats.compare`, so the ground truth below is not affected by the cost columns at all.

**Why these cost magnitudes, fixed now.** The pair `(10, 40)` puts the pending arm's enclosure thresholds
(section 2.5) at elapsed fractions `0.2375` and `0.26316` of its own duration, so the cost enclosure path is
exercised over most of a pending episode's life rather than in a sliver at its end; the pair `(40, 40)` exercises the
tie branch, whose first threshold sits at `0.95`. Section 6.4 prices exactly how much of each cell this reaches.

**Why exact threshold equality is not in the grid.** A `BB0` cost pair such as `(38, 40)`, where
`|delta| = tol = 2.0` exactly, would exercise the strict-inequality boundary in the grid - but the arm swap would
then map `BB0` to `(40, 38)`, which is **not** `BB0`, and `L1` would stop being exactly arm-exchangeable. Exact
symmetry of the A/A null is worth more than moving a boundary case out of the fixtures, so the `|delta| = tol`
boundary stays in fixtures `F07` and `F17`. The arm swap maps `BB+ <-> BB-` and `C>I <-> I>C` with their cost pairs
swapped and fixes `BB0` and `FF`, so `L1` is exactly exchangeable and its expected band is exactly symmetric
(section 6.3, row `C1`).

Fixture F07 re-derives the `Z` column from `src/winstats.compare` with
`[Tier('success'), Tier('cost', higher_better=False, relative_tolerance=0.05)]` on a deterministic outcome grid that
includes **exact threshold equality** (`cost 95.0` vs `cost 100.0`, where `|delta| = tol = 5.0` exactly, which ties
because the decisive test is the strict `|delta| > tol`) and joint failures; that check has been run once while
writing this protocol and agreed on all eight of its cases.

**Weights, and the ground truth derived by enumeration (not by simulation).**

| law | `BB+` | `BB0` | `BB-` | `C>I` | `I>C` | `FF` | `mu_h = E[Z]` | `mu_s = E[D]` |
|---|---|---|---|---|---|---|---|---|
| `L1` aa_null | 2250 | 500 | 2250 | 1500 | 1500 | 2000 | `+0.0000` | `+0.0000` |
| `L2` pref_boundary | 1500 | 500 | 4000 | 3000 | 500 | 500 | `+0.0000` | `+0.2500` |
| `L3` success_boundary | 5000 | 300 | 700 | 1200 | 1500 | 1300 | `+0.4000` | `-0.0300` |
| `L4` favorable_alt | 4000 | 1000 | 1500 | 2500 | 500 | 500 | `+0.4500` | `+0.2000` |

```
mu_h = ( w[BB+] + w[C>I] - w[BB-] - w[I>C] ) / 10000
mu_s = ( w[C>I] - w[I>C] ) / 10000
```

Both are exact rationals with denominator 10,000. Because atoms are i.i.d. across enrolled pairs,
`mubar_n = mu_h` and `nubar_n = mu_s` for every `n >= 1`, exactly, on every path. **This is the ground truth against
which every coverage and decision-error event in this study is defined.** It is derived by enumerating six atoms; no
simulation enters its derivation.

Induced score distributions, also exact:

| law | `P(Z=+1)/P(Z=0)/P(Z=-1)` | `P(D=+1)/P(D=0)/P(D=-1)` |
|---|---|---|
| `L1` | 0.3750 / 0.2500 / 0.3750 | 0.1500 / 0.7000 / 0.1500 |
| `L2` | 0.4500 / 0.1000 / 0.4500 | 0.3000 / 0.6500 / 0.0500 |
| `L3` | 0.6200 / 0.1600 / 0.2200 | 0.1200 / 0.7300 / 0.1500 |
| `L4` | 0.6500 / 0.1500 / 0.2000 | 0.2500 / 0.7000 / 0.0500 |

**Why each law is where it is, fixed now.**

- **`L1`, A/A symmetric null.** The atom table is invariant under exchanging the two arms (`w[BB+] = w[BB-]`,
  `w[C>I] = w[I>C]`), so this is an exact null in both gates by construction and not merely in expectation. It is the
  analogue of the live T4 control (`protocol_FINAL.md` 1.2). Both `mu_h = 0` and `mu_s = 0` sit exactly on the
  boundary, so **every** DEPLOY and **every** RETAIN_INCUMBENT in this cell is an erroneous decision.
- **`L2`, preference boundary with success favorable.** `mu_h = 0` exactly - the least favourable point for both the
  deploy gate's hierarchy condition and the harm gate - while `mu_s = +0.25` makes the success guardrail genuinely
  true. This is a coherent scenario: a candidate that succeeds distinctly more often (`P(D=+1) = 0.30` against
  `P(D=-1) = 0.05`) but is slower when both succeed, so that the composite preference is exactly neutral. Every
  DEPLOY and every RETAIN_INCUMBENT here is erroneous.
- **`L3`, success boundary with preference favorable.** `mu_s = -delta = -0.03` exactly - the least favourable point
  for the guardrail - while `mu_h = +0.40` opens the hierarchy condition early, so a DEPLOY in this cell is governed
  entirely by a one-sided error of the **success** band at its exact boundary. Every DEPLOY and every
  RETAIN_INCUMBENT here is erroneous (`mu_s <= -delta`, and `mu_h > 0`).
- **`L4`, the scientifically prespecified favorable alternative.** A candidate that is both more successful
  (`mu_s = +0.20`) and faster when both succeed (`mu_h = +0.45`). This is the only scenario in which the live study's
  T3 could deploy (`protocol_FINAL.md` 11.4), and it is chosen for that reason and not for its rates. Here DEPLOY is
  the **correct** decision; false deploy is impossible by construction and its reported rate is `0` by definition,
  while every RETAIN_INCUMBENT is still erroneous because `mu_h > 0`.

Note that `mu_h >= 0` in all four laws, so **every RETAIN_INCUMBENT issued anywhere in this study is an erroneous
decision**, and the harm gate's type-I probe is live in all eight cells.

### 4.2 The delay rules, stated exactly

Delay is measured in **enrollment ticks**: pair `i` is enrolled at tick `i`, and a pair with full-resolution offset
`d_i` is fully resolved at every look with prefix `n >= i + d_i`. Two building-block distributions are used, and only
these two:

```
SHORT  ~ DiscreteUniform{0, 1, ..., 19}        mean  9.5
LONG   ~ DiscreteUniform{100, 101, ..., 699}   mean 399.5
```

**Delay rule `N` (noninformative).** `d_i` is drawn independently of `(Z_i, D_i)` and of everything else:

```
d_i = LONG  with probability p_long(law) = 3 * w_neg / 40000,   otherwise  d_i = SHORT
```

where `w_neg = w[BB-] + w[I>C]` is the integer weight of `Z = -1` under that law. Sampling is exact integer
arithmetic: `u = rng.integers(0, 40000)`, long iff `u < 3 * w_neg`.

**Delay rule `A` (outcome-dependent asymmetric).** `d_i` depends on the pair's own realized hierarchy score:

```
Z_i = +1  ->  d_i = SHORT                                       (favourable pairs always resolve fast)
Z_i =  0  ->  d_i = SHORT
Z_i = -1  ->  d_i = LONG with probability 3/4, else SHORT
```

Sampling is exact: for `Z_i = -1`, `u = rng.integers(0, 4)`, long iff `u < 3`. Given `Z_i`, `d_i` is conditionally
independent of `D_i` and of every other pair.

**The two rules are marginal-delay-matched by construction.** `p_long(law) = (3/4) * P(Z = -1)` is exactly the
unconditional long-branch probability of rule `A` under the same law, so for each outcome law the `N` and `A` cells
have the **identical marginal delay distribution**, the identical `E[d]`, and - because the enrollment schedule is
deterministic - the identical expected unresolved and unrevealed fractions at every look. They differ in one thing
only: **which** pairs are slow. This is the controlled contrast the root's item 3 asks for, and it is what isolates
informativeness of the delay from its magnitude.

| law | `w_neg` | `p_long` under rule `N` | `E[d]` (both rules) |
|---|---|---|---|
| `L1` | 3750 | `11250 / 40000 = 0.28125` | `119.19` |
| `L2` | 4500 | `13500 / 40000 = 0.33750` | `141.12` |
| `L3` | 2200 | `6600 / 40000 = 0.16500` | `73.85` |
| `L4` | 2000 | `6000 / 40000 = 0.15000` | `68.00` |

Rule `A` is deliberately the strongest informative coupling representable in this family: under it the unresolved set
is almost purely `Z = -1`. It was chosen **before any outcome existed**, to make a failure of the completed-only rule
detectable rather than to flatter the adapter; it is adversarial to `NAIVE` and, through the enclosure slack it puts
on the upper band, adversarial to the adapter's own harm gate.

### 4.3 Partial revelation within a pair, and the elapsed-cost accrual

Each pair has two episodes, both dispatched at the pair's enrollment tick. Given `d_i`, the **first** reveal offset is
`f_i ~ DiscreteUniform{0, 1, ..., d_i}` and the arm revealed first is the candidate with probability `1/2`, both
independent of the outcome given `d_i`. The first-revealed episode therefore has duration `f_i` and the second `d_i`.
A revealed episode is **final**: its success and its final cost are both known. At a look with prefix `n`, pair
`j <= n` is:

- **fully resolved** iff `d_j <= n - j`;
- **partially revealed** iff `f_j <= n - j < d_j`, with the enclosure row of section 2.5 for the arm revealed first
  and for the pending arm's current elapsed cost;
- **unrevealed** iff `n - j < f_j`, with enclosure `[-1, +1]` on both scores.

**The elapsed-cost accrual, stated exactly.** An episode with final cost `c` and duration `D` holds, at age `a`, the
elapsed lower bound

```
ell(a) = (c * a) / D        for a < D          (evaluated in this order: c * a first)
ell(a) = c                  for a >= D
```

so `ell(a) < c` strictly while the episode is pending, and `ell` is nondecreasing in `a`. This is what a resource
meter reports when cost accrues over the episode's own duration, and it is a *valid* lower bound by construction,
which is the only property the enclosure rule of section 2.5 uses (guidance item 5: "elapsed cost is a lower bound
only if it cannot decrease"). A pending episode's cost upper bound is the frozen cap `cost_cap = 100` and never
narrows; no other cost information is ever observed.

The evaluation order is frozen because it is the difference between reproducible and irreproducible tie behaviour: with
integer `c` and `a` the product is exact, so a threshold such as `ell = 0.95 * c_revealed` is hit exactly when
`a / d` hits it exactly, on every machine.

**This adds no draw.** `ell` is a deterministic function of `(atom, d_i, f_i, b_i, a)`, so the five-array draw order
of section 5 is unchanged and every stream is bit-identical to what it would have been.

**Two declared simplifications, both stated before any outcome exists.**

1. **The fair first-reveal coin.** In the live apparatus the faster arm tends to reveal first, which correlates with
   the cost tier; here the first-reveal identity is independent of the outcome given `d_i`.
2. **Two clocks.** The cost meter and the reveal schedule are not tied to each other: an episode's final cost is
   fixed by its atom while its duration comes from the delay rule, so a cheap episode may reveal second. In the live
   trial cost **is** `latency_s` and the two clocks are one clock.

Both simplifications push the same way, and it is the conservative way for this study's purpose: a latency-coupled
model would put the *expensive* arm in the pending position more often, and the pending arm's elapsed cost is what
overtakes the revealed arm's, so coupling would narrow the cost enclosure **more** often than this model does. The
adversarial content of these cells is carried by the pair-level delay rule instead. Section 6.4 prices exactly how
much of each cell this model does exercise, so the reader does not have to take the word "enough" on trust.

### 4.4 Why the cost path is in the cells at all, and where the idea came from

In the pre-audit draft of this protocol the enclosure narrowed on **success information only**: a pair moved
unrevealed -> one arm revealed -> both revealed, and no partial cost information ever entered. The adversarial
pre-registration audit `PREREG_CHECK.md` B.6 found that this left the entire cost/latency enclosure path unexercised
by all eight cells - **the tier that carries almost the whole composite effect in the live trial**, whose frozen
hierarchy is `success > cost` with `cost = latency_s` and whose pilot arms tie on success. A validation study that
never exercises the tier the real effect rides on validates the wrong half of the arithmetic.

The fix is sections 4.1 and 4.3: atom cost columns plus an elapsed-cost accrual rule. It stays inside the frozen
structure - same eight cells, same six atoms, same weights, same `mu_h` and `mu_s`, same delay rules, same seeding,
same reveal schedule, ground truth still by enumeration and never by simulation - and it makes pairs resolve at the
cost tier with unresolved cost enclosures that narrow as elapsed time accrues.

**Provenance, stated rather than implied.** The *gap* was found by the audit, not by this author, and the audit
quotes the #11 monitor's cost certificate while naming it. The #12 narrowing thresholds in section 2.5 are re-derived
from the guidance's own tolerance rule through `vband.cost_order_possibilities`, which was written before the audit
and is unchanged by it - but the coincidence between the two is now a *known* coincidence and is therefore no longer
independent evidence of agreement. Section 12.1 records this and section 12.2 says what the comparison may still
claim.

---

## 5. Seeding

**Master seed, frozen: `1220260919`.** One independent stream per `(cell, program, trial)`:

```python
ss  = numpy.random.SeedSequence(entropy=1220260919, spawn_key=(namespace, cell_index, program_index, trial_index))
rng = numpy.random.Generator(numpy.random.PCG64(ss))
```

with `cell_index in 0..7` (section 4), `program_index in 0..P-1`, `trial_index in 0..3`, and three **disjoint
namespaces**:

| namespace | use | seeds reused later? |
|---|---|---|
| `0` | the reported grid of section 7 | yes, this is the study |
| `1` | the smoke run of section 8.1 | **no - discarded, never reused** |
| `2` | the frozen fixture and comparison streams of sections 11 and 12 | yes, fixed and small |

`SeedSequence` spawn keys are the documented non-overlapping mechanism: distinct keys give distinct 128-bit states,
and no stream is derived from another's output. The full key of every trial is therefore recoverable from its four
coordinates alone, and any single trial can be replayed in isolation.

**Draw order inside a trial is frozen** (it is part of the seed's meaning; changing it changes every stream):

```python
u_atom  = rng.integers(0, 10000, size=N_max)         # 1. the outcome atom of each pair
u_delay = rng.integers(0, 40000, size=N_max)         # 2. the long/short branch selector
u_len   = rng.random(size=N_max)                     # 3. position inside the selected uniform block
u_first = rng.random(size=N_max)                     # 4. the first-reveal offset f_i
u_coin  = rng.random(size=N_max)                     # 5. which arm reveals first
```

All five arrays are drawn unconditionally and at full length, so the stream advances identically whichever branch a
pair takes. Derivations:

```
long_i  = (u_delay[i] < 3 * w_neg)                           for rule N
long_i  = (Z_i == -1) and (u_delay[i] < 30000)               for rule A   # 30000/40000 = 3/4
d_i     = 100 + floor(u_len[i] * 600)  if long_i  else  floor(u_len[i] * 20)
f_i     = floor(u_first[i] * (d_i + 1))
b_i     = 1 (candidate revealed first)  iff  u_coin[i] < 0.5
```

---

## 6. Analytic reachability (root's planning object; no simulation)

Everything in this section is an **exact expectation** under the frozen law, computed by summing over the six atoms
and the delay distribution at each pair age. It is the analogue of `protocol_FINAL.md` 11.3, and it carries the same
wording rule: these are plug-in expected-value calculations for **this rule, this allocation and this grid**. They
**ignore sampling variability entirely and are not predictions of any reported rate.** They are published here so
that no property of the design can be claimed to have been discovered after the fact.

**Method, so that the arithmetic can be redone independently.** For each pair age `a` the enclosure state is
enumerated over `(atom, long/short branch, d, f, which arm revealed first)` with its exact probability, using
`P(f <= a | d) = (a+1)/(d+1)`; that gives `E[lower]` and `E[upper]` per age. The expected sum over a prefix is their
partial sum, and the expected-path endpoint is that mean `-+ r(n)`, clipped to `[-1,1]`. The finalization look takes
ages `W ... W + N_max - 1`. **No random number is drawn anywhere in this section.** The per-state enclosure used by
this enumeration was checked against `vband`'s own enumeration over 21,312 `(atom, arm, d, a)` states with zero
mismatches, and the true `Z` lies inside every one of them.

**Sections 6.2, 6.3 and 6.4 were recomputed in the pre-freeze revision** (section 4.4) and 6.1 was not, because 6.1
depends only on the reveal schedule. Running the recomputation with the cost accrual switched off reproduces the
pre-audit 6.2 and 6.3 tables exactly, value for value, which is how the machinery was checked before being trusted
with new numbers.

### 6.1 Expected unresolved and unrevealed fractions of the enrolled prefix

Identical for the `N` and `A` cells of the same law (section 4.2).

| law | `n=100` unresolved / unrevealed | `n=500` | `n=2000` | finalization look |
|---|---|---|---|---|
| `L1` | 34.95% / 26.94% | 21.97% / 11.73% | 5.96% / 2.98% | 2.92% / 0.88% |
| `L2` | 40.04% / 31.38% | 25.99% / 13.88% | 7.06% / 3.53% | 3.51% / 1.06% |
| `L3` | 24.43% / 17.77% | 13.68% / 7.27% | 3.69% / 1.85% | 1.72% / 0.52% |
| `L4` | 23.08% / 16.59% | 12.61% / 6.70% | 3.40% / 1.70% | 1.56% / 0.47% |

The enclosure path is therefore genuinely exercised: between a quarter and two fifths of the enrolled prefix is
unresolved at the first admissible look, and a nonzero fraction is still unresolved at the cap endpoint, which is what
makes the finalization rule of section 7.3 a live rule rather than a formality. *(These entries are the exact values
rounded half-up at two decimal places; `L4`'s `23.08%` and `12.61%` are exactly `23.075%` and `12.605%`.)*

### 6.2 Expected-path gate opening prefixes

The smallest `n >= n_min` at which each condition holds **on the expected path**.

| cell | `L_h > 0` at | `L_s > -delta` at | `U_h < 0` at | DEPLOY at |
|---|---|---|---|---|
| `C1` `L1/N` | never | never | never | never |
| `C2` `L1/A` | never | never | never | never |
| `C3` `L2/N` | never | 864 | never | never |
| `C4` `L2/A` | never | 698 | never | never |
| `C5` `L3/N` | 335 | never | never | never |
| `C6` `L3/A` | 160 | never | never | never |
| `C7` `L4/N` | 258 | 695 | never | **695** |
| `C8` `L4/A` | 137 | 566 | never | **566** |

**What the cost path changed here.** The `L_h > 0` column opens earlier than in the pre-audit draft (`C5` 398 -> 335,
`C6` 169 -> 160, `C7` 300 -> 258, `C8` 145 -> 137), because the cost tier now removes part of the enclosure slack.
The `L_s > -delta` column is **identical**, because the success enclosure is untouched by the cost tier - which is a
check on the recomputation as much as a fact about the design. The `U_h < 0` column is still never, and that one is
true a priori: `E[upper] >= E[Z] = mu_h >= 0` in every law, so `E[U_h] >= mu_h + r(n) > 0` at every prefix.

Reading, fixed now:

1. **`C7`/`C8` decide correctly on the expected path, well inside the cap.** These are the cells in which correct
   DEPLOY rates and decision prefixes carry information.
2. **`C3`/`C4` have a wide live false-deploy window.** The guardrail opens on the expected path at `n = 864` and
   `n = 698`, so the false-deploy route is open over roughly 1,140 and 1,300 of the 1,902 decision-eligible looks, and
   whether it fires is governed by the hierarchy band's one-sided error at `mu_h = 0`.
3. **`C5`/`C6` have a very wide live false-deploy window** (from `n = 335` and `n = 160`), governed entirely by the
   success band's one-sided error at the exact boundary `mu_s = -delta`.
4. **In `C1`/`C2` the DEPLOY route is unreachable within the cap**, because `mu_s = 0` and `r(n) < delta = 0.03`
   first holds at `n = 17,097`. This is the same structure the live study declares for T1 in `protocol_FINAL.md` 1.3.
   It is a **pre-specified near-certain abstention on the deploy route of those two cells, not a logical
   impossibility**; if a DEPLOY occurs there it is reported as the rare event it is and never described as impossible.
   The decision-level probe of `C1`/`C2` is the **harm** gate.
5. **`U_h < 0` never opens on the expected path in any cell**, because `mu_h >= 0` everywhere. Every RETAIN_INCUMBENT
   observed in this study is therefore a pure tail event and a pure error, which is exactly what makes it the
   cleanest decision-level type-I probe in the design.
6. Because several decision-level probes are cap-limited or tail-limited, **the primary evidence for each gate is the
   band-level one-sided ever-miscoverage of section 9.1**, not the decision-level rate. This ordering is fixed now, so
   that a near-zero decision-level table cannot later be presented as if it were the strong result.

### 6.3 Expected-path band endpoints (the conservatism of the guaranteed enclosure, priced now)

| cell | `n=100` `L_h`/`U_h`/`L_s` | `n=500` | `n=2000` | finalization |
|---|---|---|---|---|
| `C1` | -0.7818 / +0.7818 / -0.7752 | -0.3355 / +0.3355 / -0.3378 | -0.1271 / +0.1271 / -0.1279 | -0.1012 / +0.1012 / -0.1022 |
| `C2` | -0.5366 / +1.0000 / -0.6799 | -0.1835 / +0.4802 / -0.2761 | -0.0868 / +0.1653 / -0.1115 | -0.0832 / +0.1172 / -0.0946 |
| `C3` | -0.8268 / +0.8377 / -0.6621 | -0.3575 / +0.3727 / -0.1685 | -0.1327 / +0.1371 / +0.1006 | -0.1029 / +0.1060 / +0.1382 |
| `C4` | -0.5334 / +1.0000 / -0.5589 | -0.1828 / +0.5563 / -0.1016 | -0.0866 / +0.1859 / +0.1184 | -0.0832 / +0.1275 / +0.1465 |
| `C5` | -0.3698 / +0.9925 / -0.7004 | +0.0838 / +0.6294 / -0.3009 | +0.2781 / +0.4990 / -0.1401 | +0.3017 / +0.4892 / -0.1241 |
| `C6` | -0.1667 / +1.0000 / -0.6093 | +0.2105 / +0.7439 / -0.2419 | +0.3117 / +0.5291 / -0.1244 | +0.3168 / +0.5015 / -0.1168 |
| `C7` | -0.3099 / +1.0000 / -0.5037 | +0.1423 / +0.6747 / -0.0851 | +0.3304 / +0.5478 / +0.0862 | +0.3529 / +0.5390 / +0.1046 |
| `C8` | -0.1190 / +1.0000 / -0.4465 | +0.2601 / +0.7896 / -0.0481 | +0.3616 / +0.5783 / +0.0960 | +0.3668 / +0.5522 / +0.1092 |

The `L_s` column is unchanged from the pre-audit draft; every `L_h` and `U_h` entry moved inward, because the cost
tier resolves slack the success tier could not.

The asymmetry in the `A` cells is the price of a guaranteed enclosure under informative delay: the unresolved pairs
are the `Z = -1` pairs, whose `lower_j = -1` is tight, so `L_h` is barely affected, while `upper_j = +1` is maximally
loose, so `U_h` is inflated and the harm gate is much harder to reach. **This is a correct and expected consequence
of never imputing a pending outcome, and it is stated here before any outcome exists so it cannot later be reported
as a discovery or as a defect.** The cost tier relieves part of that inflation and does not remove it: `C2`'s
expected `U_h` at `n = 500` is `+0.4802` with the cost path and was `+0.5695` without it, against a truth of
`mu_h = 0`.

### 6.4 How much of each cell exercises the cost enclosure path (priced now)

Each entry is `[E fraction of the enrolled prefix that is not fully resolved and whose hierarchy enclosure the cost
tier has collapsed to a **point**] / [the same for any cost-attributable **narrowing**]`. The second contains the
first. **Both are exactly zero under the pre-audit enclosure model**, by construction: no partial state there could
be narrowed by cost at all. That is what `PREREG_CHECK` B.6 found, and this table is the arithmetic that answers it.

| cell | `n=100` point / narrowed | `n=500` | `n=2000` | finalization |
|---|---|---|---|---|
| `C1` | 1.89% / 1.99% | 3.51% / 3.60% | 1.04% / 1.06% | 0.77% / 0.78% |
| `C2` | 1.99% / 2.13% | 4.58% / 4.66% | 1.35% / 1.37% | 1.02% / 1.02% |
| `C3` | 2.34% / 2.49% | 4.99% / 5.10% | 1.47% / 1.51% | 1.10% / 1.12% |
| `C4` | 2.39% / 2.55% | 5.50% / 5.59% | 1.63% / 1.65% | 1.23% / 1.23% |
| `C5` | 1.96% / 2.05% | 2.45% / 2.51% | 0.72% / 0.73% | 0.50% / 0.51% |
| `C6` | 2.00% / 2.10% | 2.85% / 2.90% | 0.84% / 0.85% | 0.60% / 0.60% |
| `C7` | 1.97% / 2.05% | 2.29% / 2.36% | 0.67% / 0.69% | 0.46% / 0.48% |
| `C8` | 2.00% / 2.09% | 2.63% / 2.68% | 0.77% / 0.78% | 0.55% / 0.55% |

Reading, fixed now:

1. **The path is live in all eight cells at every horizon.** At `n = 500` in `C4`, `5.50%` of the whole enrolled
   prefix is a pair no episode has finished resolving and whose hierarchy score the cost tier has nevertheless pinned
   to a point - about a fifth of that cell's `25.99%` unresolved fraction. At the finalization look of `C1` the cost
   tier has pinned `0.77%` out of `2.92%` still unresolved.
2. **The fractions peak around `n = 500`**, not at `n = 100`, because at the earliest looks most unresolved pairs are
   still *unrevealed* (nothing is known, so nothing can narrow), while at large `n` most pairs are fully resolved.
   The cost path is therefore best exercised exactly where the decision windows of section 6.2 are widest.
3. **The gap between the two columns is small**, because the intermediate state `[0, +1]` is passed through quickly:
   the two thresholds of section 2.5 are `0.2375` and `0.26316` of the pending arm's duration for a `(10, 40)` cost
   pair. The tie atoms `BB0` and the `(40, 40)` failures contribute the narrow band near `0.95`.
4. **The path is one-sided by construction**, and this is priced rather than hidden: the cost tier can only narrow a
   pair when the **revealed** arm is the cheap one, since only then can the pending arm's elapsed cost overtake it.
   With the fair first-reveal coin of section 4.3 that is about half of the cost-decisive pairs and never the other
   half. That is a property of the frozen reveal model, not a defect of either implementation.
5. These are expectations and **not predictions of any measured fraction**; section 9.5 reports the measured
   counterparts with their own quantiles, and a discrepancy between the two is a defect to investigate, not a result.

---

## 7. The grid, the escalation rule, and the cap endpoint

### 7.1 The bounded grid (root item 4)

| quantity | value |
|---|---|
| programs per cell | **2,000** |
| trials per program | **4** |
| enrolled pairs per trial | at most **2,000** |
| looks per trial | 2,001 - one at every enrollment prefix `n = 1 ... 2,000`, plus one finalization look |
| decision-eligible looks | 1,902 (`n >= 100`, plus the finalization look) |
| fixed-horizon summaries | at `n = 100`, `n = 500`, `n = 2,000` |
| constructions per trial | 3 (`ADAPTER`, `CPREFIX`, `NAIVE`), all on the same simulated path, no extra draws |

**Why one look per enrollment prefix is the exact reduction, not a shortcut.** Within a fixed prefix `n`, each further
fact - a reveal, a resolution, **or an increase in a pending episode's elapsed cost** - replaces an enclosure by a
subinterval of itself, so the band at that prefix is nested-shrinking over the looks that share it. The cost accrual
of section 4.3 preserves this because `ell(a)` is nondecreasing in `a` and the enclosure rule of section 2.5 is
monotone in `ell`; without that monotonicity the reduction would be an approximation rather than an identity. Consequently (i) miscoverage at any look at prefix `n` implies miscoverage at the **last** look
at prefix `n`, and (ii) a decision that fires at any look at prefix `n` also fires at the last look at prefix `n`.
Taking exactly one look per prefix, **at the state immediately before the next enrollment** (maximal information at
that prefix), therefore captures the full ever-miscoverage event and the exact decision prefix `tau` of the
all-triggers rule. What it does **not** reproduce is the wall-clock instant of a decision, so decision time in this
study is reported in **enrolled pairs**, never in simulated wall clock, and never as a latency.

### 7.2 The precommitted escalation rule

Root item 4 permits 5,000 programs in the four boundary/delay cells. **The four escalation-eligible cells are
`C3`, `C4`, `C5`, `C6`** - the two boundary outcome laws under both delay rules. This reading is fixed here: it is
the only reading under which exactly four cells are both at a decision boundary and present under both delay rules,
and the alternative reading (two boundary cells plus two delay cells) was considered and rejected **while writing this
protocol, before any outcome existed**.

Escalation is decided by the budget ladder of section 8.2 **from runtime and memory measurements alone**. It is never
decided by, or after seeing, any effect comparison, coverage number or decision rate.

### 7.3 The resource-cap endpoint rule (root item 3)

Enrollment stops unconditionally at `N_max = 2,000`. The trial then runs a **finalization drain of `W = 200`
enrollment ticks**: the finalization look is taken at tick `N_max + W = 2,200`, with prefix still `n = N_max`, and a
pair `j` is fully resolved there iff `d_j <= 2200 - j`.

- Pairs still unresolved at the finalization look **keep the enclosure they have** and enter `L` and `U` through it.
- **Nothing is censored, dropped, imputed or deleted**, at the cap or anywhere else. The denominator is always
  `n = N_max`, never the number completed.
- The finalization look is a full decision look: a DEPLOY or RETAIN_INCUMBENT may fire there and is recorded with
  `tau = N_max` and the flag `decided_at_finalization = true`.
- If no decision has fired by then, the trial's endpoint is **NO_DECISION**, recorded with the unresolved fraction at
  that look.

The drain is shorter than the maximum delay (`max(LONG) = 699`) precisely so that the endpoint genuinely carries
unresolved pairs (section 6.1 gives 1.56% to 3.51% in expectation). The cap changes the endpoint by this explicit
rule and by no other mechanism.

---

## 8. Budget, the smoke run, and the pause-and-report rule

### 8.1 The smoke run (root item 4: runtime and RAM only)

Exactly **one** 20-program smoke run, drawing from **namespace 1** of section 5, all three constructions and all four
trials, split into **two horizon points**: 10 programs in `C1` at `N_max = 2,000` and 10 programs in `C2` at
`N_max = 1,000`. It writes only `results/live_ab_validation/smoke/`.

**Why those cells.** `C1` and `C2` share the outcome law with the largest expected unresolved fraction among the
non-escalating cells and differ only in the delay rule, so the pair measures both delay branches. Under the section
9.1 all-looks reading every trial runs to the finalization look whatever it decides, so runtime is close to
cell-independent and splitting the budget across two cells costs nothing.

**Why two horizon points.** The projection below is a power law in `N_max`, and one measurement at one horizon cannot
measure its exponent. Per-look cost is `O(1)` only if the band is maintained incrementally; a recompute-the-sum-per-look
implementation is quadratic in `N_max`, under which the `T4` row would be over-projected by a factor of two and the
tier choice could be wrong. So the exponent is **measured, not assumed**.

- Recorded: wall-clock seconds, peak resident set size (`resource.getrusage(RUSAGE_SELF).ru_maxrss`), bytes written,
  and the counts of programs, trials, pairs and looks.
- **Its seeds are discarded and are never reused in the reported grid** (different namespace).
- **Its effect columns are not read, are not inspected, and play no part in choosing the horizon, the cap, the cells
  or anything else.** The only quantities permitted to leave the smoke run are seconds, bytes and memory. `vrun.py`
  asserts, before the grid starts, that the smoke output directory contains no per-trial effect record. (`vrun.py`
  does not exist at the freeze commit; this is a requirement on it, not a claim that the check runs today.)

Projection, computed from the smoke numbers alone, with `s_H` the measured seconds per program at horizon `H`:

```
beta               = log(s_2000 / s_1000) / log(2)       # the measured scaling exponent
seconds_projected  = s_2000 * programs_total * (N_max_tier / 2000) ** beta
bytes_projected    = (smoke_bytes / 20) * programs_total
peak_rss_projected = smoke_peak_rss                      (the run is batched; peak does not grow with the grid)
```

`beta` is written to `budget.json` beside the two measurements. An implementation that maintains the running
enclosure sums incrementally gives `beta` near 1; a recompute-per-look implementation gives `beta` near 2. `vrun.py`
carries an operation counter and asserts the incremental property on the smoke run, before the grid starts; the count
goes into `budget.json` too.

### 8.2 The budget ladder, fixed now

| tier | grid | programs total |
|---|---|---|
| **T1** (preferred) | `C3`,`C4`,`C5`,`C6` at 5,000 programs; `C1`,`C2`,`C7`,`C8` at 2,000; `N_max = 2,000` | 28,000 |
| **T2** | all eight cells at 2,000 programs; `N_max = 2,000` | 16,000 |
| **T3** | all eight cells at 1,000 programs; `N_max = 2,000` | 8,000 |
| **T4** | all eight cells at 1,000 programs; `N_max = 1,000`; fixed-horizon summaries become 100 / 500 / 1,000 | 8,000 |

**`T4`'s section 6 is already frozen.** The `N_max = 1,000` variant of 6.1, 6.2, 6.3 and 6.4 is computed and
deposited **now**, in `cells.json` -> `analytic_reachability.T4_variant_N_max_1000`, not recomputed after the smoke
run. Section 14 exempts the *tier choice* from change control; it does not exempt section 6's values, and a table
written after a measurement is not a pre-registered table.

**`T4` forfeits the `n = 2,000` fixed-horizon summary required by root item 4; if `T4` is selected, the report states
this as a reduction of the root's design**, not as a budget consequence. Every expected-path opening prefix of
section 6.2 is below 1,000, so no decision window is lost - only the third horizon summary is.

**Selection rule: the highest tier whose projection satisfies all three of** `seconds_projected <= 5,400`,
`peak_rss_projected <= 2.0 GiB`, `bytes_projected <= 200 MiB`. The selected tier, the smoke measurements and the
projection are written to `results/live_ab_validation/budget.json` **before the reported grid starts**, and the report
states which tier ran. A reduced fixed grid is thus reported **before** execution, as root item 4 requires.

**If even T4 fails any of the three limits, the run PAUSES and reports** - it does not silently shrink further, does
not drop a cell, and does not reduce the number of constructions.

### 8.3 Hard resource rules during execution

- Batched by `(cell, block of 100 programs)`; per-trial records are appended to a gzip CSV incrementally and never
  held in memory in full. No per-look path is ever written to disk.
- A runtime assertion checks peak RSS after every batch; on exceeding 2.0 GiB the run stops, writes what it has, and
  reports.
- A runtime assertion checks cumulative output bytes after every batch; on exceeding 200 MiB the run stops and
  reports.
- CPU only. No model call, no API call, no network, no download, no new dependency.

---

## 9. Reported quantities, exact estimators, and the flag rule (root item 6)

Every rate below is reported with a **Wilson score 95% interval** at `z = 1.959963984540054`:

```
center = (x + z^2/2) / (N + z^2)
half   = z / (N + z^2) * sqrt( x*(N-x)/N + z^2/4 )
[lo, hi] = [max(0, center - half), min(1, center + half)]
```

**These intervals quantify Monte Carlo error of this simulation only.** They are not confidence intervals for the
statistical guarantee, and a Wilson interval lying below a nominal level is not a proof that the level holds.

Every quantity is reported **per cell, per construction, and per gate where a gate applies**, for all eight cells and
all three constructions, including `NAIVE`, and including every unfavourable or inconclusive row. **No row is omitted
for brevity and no row is omitted because it is unfavourable.**

### 9.1 Per-gate simultaneous ever-miscoverage (unit: trial; `N = programs x 4`)

For gate `g in {hierarchy, success}` with truth `mu_g`, over **all** looks of the trial to the finalization look:

| quantity | event |
|---|---|
| `ever_miscover_g` | `exists look : mu_g < L_g(look) or mu_g > U_g(look)` |
| `ever_below_g` | `exists look : mu_g < L_g(look)` (the lower band excludes the truth from below) |
| `ever_above_g` | `exists look : mu_g > U_g(look)` |
| nominal bound | `alpha_gate = 0.00625` for `ever_miscover_g`, and each one-sided component is separately bounded by it |

Coverage is measured over the **whole path**, to the finalization look, not only up to a decision, because the
confidence-sequence guarantee of section 2.2 is a statement for all `n`. Section 2.4 fixes the other half of this:
the decision is still the first crossing, and carrying the path further is a bookkeeping device of this simulation,
not a description of the live trial. Both read-outs come from the same simulated path and cost no extra draws. `ever_miscover_g` is also reported **restricted to `n >= n_min`** as a
secondary column, since only those looks can decide.

For `CPREFIX` the same events are evaluated at its own index `k`; for `NAIVE` at its own count `m`. In all three the
numerical truth is the same `mu_g` (section 3), and the report repeats the target caveat in the table caption.

### 9.2 Decision-level quantities

| quantity | unit | definition | nominal bound |
|---|---|---|---|
| `false_deploy` | trial | trial issues DEPLOY and `not (mu_h > 0 and mu_s > -delta)` | `0.00625` via the deciding gate |
| `false_harm` | trial | trial issues RETAIN_INCUMBENT and `mu_h >= 0` | `0.00625` |
| `any_erroneous_trial` | trial | `false_deploy or false_harm` | `0.0125` |
| `family_any_erroneous` | **program** | at least one of the program's four trials has `any_erroneous_trial` | `0.05` |
| `correct_deploy` | trial | DEPLOY and `(mu_h > 0 and mu_s > -delta)` - possible only in `C7`/`C8` | - |
| `no_decision` | trial | endpoint reached with no decision | - |
| `conflict` | trial | both conditions at one look (section 2.4) | - |
| `never_conjunct` | trial | `L_h > 0` held at some look **and** `L_s > -delta` held at some look, but never at the same look | - |

`never_conjunct` is the direct read-out of the same-look conjunction requirement: a nonzero value proves the
conjunction is doing work rather than being a restatement of the two marginal conditions.

Under these four laws `mu_h >= 0` always, so `false_harm` is exactly the RETAIN_INCUMBENT rate in every cell; and
`false_deploy` is exactly the DEPLOY rate in `C1`-`C6` and exactly `0` in `C7`/`C8`. Both identities are asserted by
`vrun.py` as it tabulates, so that a nonzero `false_deploy` in `C7`/`C8` is caught as a bug rather than reported.
(`vrun.py` does not exist at the freeze commit; this is a requirement on it.)

### 9.3 The exceedance flag, and its resolution

A cell/construction/quantity is **FLAGGED as an exceedance** iff the **lower** Wilson limit of its measured rate
exceeds its nominal bound. Smallest flagging counts, fixed now:

| quantity | `N` at 2,000 programs | flag at | smallest detectable | `N` at 5,000 programs | flag at | smallest detectable |
|---|---|---|---|---|---|---|
| per-gate ever-miscoverage (bound 0.00625) | 8,000 | `x >= 64` | `1.280x` nominal | 20,000 | `x >= 147` | `1.176x` nominal |
| trial-level any-erroneous (bound 0.0125) | 8,000 | `x >= 120` | `1.200x` nominal | 20,000 | `x >= 281` | `1.124x` nominal |
| family-level any-erroneous (bound 0.05) | 2,000 | `x >= 120` | `1.200x` nominal | 5,000 | `x >= 281` | `1.124x` nominal |

With `x = 0` events the Wilson interval is `[0, 0.000480]` at `N = 8,000` and `[0, 0.000192]` at `N = 20,000`.
**An unflagged result is reported as "no exceedance was detected at this resolution", never as "the bound holds".**
A flag on `ADAPTER` is a **defect of the validated construction** and is reported under section 12's disagreement
procedure. A flag on `NAIVE` in an `A` cell is the **expected** behaviour of an invalid rule and is reported as the
positive control, not as a defect.

### 9.4 The positive control, precommitted

The measuring apparatus is only trustworthy if it can detect a real violation. Section 6.2's arithmetic shows the
completed-only rule's hierarchy band failing to contain the truth **on the expected path** from `n = 202` in `C2`,
`n = 159` in `C4` and `n = 365` in `C6`, and never in the `N` cells or in `C7`/`C8`. Therefore:

> **Precommitted positive control.** `NAIVE`'s hierarchy ever-miscoverage must be FLAGGED (section 9.3) in at least
> one of `C2`, `C4`, `C6`. If it is not, the **measurement apparatus itself is reported as unvalidated**, the
> `ADAPTER` results of this run are reported as uninterpretable, and the cause is investigated before any of them is
> cited. This sentence is frozen text and applies whatever the `ADAPTER` numbers turn out to be.

These three prefixes are **unaffected by the pre-freeze revision**: `NAIVE` and `CPREFIX` read only fully resolved
scores, so the cost enclosure path of section 4.3 cannot touch either of them. The positive control is the same
control it was before the audit.

The control is stated on the hierarchy gate only. The same arithmetic shows the completed-only **success** band is
much less disturbed by this delay coupling (the omitted pairs have `D in {-1, 0}` rather than a pure `-1`), so no
success-gate positive control is precommitted; its row is reported without a pass/fail attached.

### 9.5 Timing, resolution and compute

| quantity | definition |
|---|---|
| `tau` | the decision prefix: the enrolled prefix `n` at the first look whose condition fired |
| capped decision prefix | `tau` with `tau := N_max` for every non-deciding trial, by this explicit rule; reported as Q1 / median / Q3 over **all** trials, always printed together with the capped fraction |
| conditional decision prefix | Q1 / median / Q3 of `tau` over deciding trials only, always printed together with the deciding fraction |
| `unresolved_fraction` | at the deciding look, or at the finalization look for non-deciding trials: `(n - #fully resolved) / n`; reported as mean and Q1 / median / Q3 |
| `unrevealed_fraction` | the same with "neither episode revealed" in the numerator |
| `cost_collapsed_fraction` | the same with "not fully resolved, and the hierarchy enclosure is a point" in the numerator: the **measured counterpart of section 6.4**, and the read-out that makes the cost/latency enclosure path visible in the results rather than only in the design |
| `cost_narrowed_fraction` | the same with "not fully resolved, and the hierarchy enclosure is narrower than the success information alone would give" in the numerator |
| `certified` vs `point` counts | both, always together. A hierarchy enclosure narrowed to a point by the cost tier carries no final-score certificate, so the two counts differ by exactly the cost-collapsed pairs (section 2.5) |
| compute counts | programs, trials, enrolled pairs, looks, band evaluations, wall-clock seconds, peak RSS, output bytes, per cell and in total |

Decision prefixes are never reported as wall-clock, latency, throughput or saving, and never as a paired comparison
between constructions (section 3).

### 9.6 Fixed-horizon summaries

At `n = 100`, `n = 500` and `n = 2,000`, per cell and construction: mean and Q1/median/Q3 of `L_h`, `U_h`, `L_s`,
`U_s`; the cumulative miscoverage-so-far rate of each gate with its Wilson interval; the cumulative DEPLOY and
RETAIN_INCUMBENT rates by that prefix; and the unresolved and unrevealed fractions.

---

## 10. Boundary: bounded running-mean coverage is not a causal interpretation

**Stated plainly, and repeated in the report, in every table caption that mentions coverage, and in `cells.json`:**

> The coverage validated here is coverage of a **bounded arbitrary-running-mean target**: the band is checked against
> `mubar_n = (1/n) sum_{i<=n} E[Z_i | F_{i-1}]` of a synthetic stream whose law is written down in section 4. This
> establishes **nothing** about the assumptions needed for a causal pair-orientation interpretation of the live
> study's `mubar_n`. Those assumptions are properties of the physical apparatus - two fixed nonoverlapping arrival
> positions selected without their outcomes, one fresh fair coin per pre-enrolled pair logged and fsynced before
> either episode is dispatched, single exposure, no cross-pair interference, no dependence of a task's record on a
> later coin, an operator who does not act on coins, a fixed scheduling and resource policy, and the frozen
> outcome/missingness rule. **A simulation assumes them; it cannot supply them.** A clean result here means the
> monitor's arithmetic is sound. It does not mean the live estimand is causal, does not license any deployment,
> latency, saving or population statement, and does not convert `protocol_FINAL.md` section 1.5's forbidden sentences
> into permitted ones.

Nor is anything here empirical calibration of the live trials: a small number of physical A/A runs is not empirical
type-I calibration, and neither is a synthetic study of a different apparatus.

---

## 11. Deterministic fixtures (root item 1)

Fixtures use hand-written streams or **namespace 2** seeds, are asserted exactly, run in seconds, and are deposited to
`results/live_ab_validation/fixtures_report.json` with pass/fail per case. None of them consults the #11
implementation (section 12).

**What the fixtures do and do not recompute, stated precisely.** `F01`-`F11` and `F17` derive every expected
*enclosure* and every expected *sum, mean and decision* by hand from the frozen definitions, and call
`vband.normal_mixture_band` to assemble the band. Every expected **radius** is cross-checked against
`vfixtures.literal_radius`, an independent literal transcription of the guidance closed form - at the locked values
in `F12` and over the whole range `n = 1..20,000` in `F14` - and `F12` additionally assembles an interior band by
hand as `sum/n -+ literal_radius(n)` and compares it endpoint for endpoint. The pre-audit draft of this section
claimed more than that, and the claim is now what the code does.

**This register is machine-checked.** `F15` asserts that the ids below, the list in `cells.json` and
`vfixtures.ALL_FIXTURES` are the same ids in the same order. The pre-audit register listed `F0 ... F12` while the
code implemented `F01 ... F13`; that divergence is what the check exists to prevent.

**What `F15` compares, exactly, and what it does not.** `F15` walks the markdown tables of this document and
compares them to `cells.json` value by value. The tables it walks are: the header provenance block (the three hash
strings, the repository commit, the interpreter and numpy versions); section 2.1's parameters and the alpha ladder
`0.05 = 4 x 0.0125 = 8 x 0.00625`; section 2.2's radius reference values and its `smallest n with r(n) < x`
sentence; **section 2.5's enclosure-row table**; section 4's cells; section 4.1's atom cost columns, weights, ground
truth and induced distributions; section 4.2's delay table including its `40,000` denominator; **section 5's seed
namespaces and master seed**; sections 6.1, 6.2, 6.3 and 6.4 including their horizon column headers, their
law-and-delay row labels and the `T4` variant; section 7.1's grid, including the arithmetic of `looks per trial` and
`decision-eligible looks`; **section 8.2's budget ladder including its per-cell grid column**; **sections 9.1 and
9.2's nominal bounds** and the numbers inside their definition cells; section 9.3's flag thresholds; this register,
together with every `F01 ... Fnn` range printed anywhere in this document; and section 13.0's module map. **Prose is
outside its reach, and so is any table not in that list** - it parses tables, not sentences. The pre-audit draft of
this paragraph said "every numeric table", which a mutation sweep showed to be false by about a third, with the
section 2.5 table among the unguarded ones (section 0.2b item 2).

**Last pre-freeze run**, on the environment in the header table:
`.venv/bin/python experiments/live_ab_validation/vfixtures.py` -> **`18/18 fixtures passed`**, 0.56 s;
`.venv/bin/python experiments/live_ab_validation/tests_validation.py` -> **`ran=88 failures=0 errors=0 skipped=0`**, 4.11 s
(up from 58 tests and 1.3 s: the mutation sweep of section 0.2b item 2 runs `F15` 773 times and costs most of
the difference).
`F14` sweeps 20,000 radii, `F17` exercises 47,484 enclosure states, `F18` hashes six files on disk, and `F16`
imports every module of this directory in a subprocess. Section 0.1 discloses both runs as pre-freeze executions
that are not results of this study.

| id | assertion |
|---|---|
| `F01_pre_enrolled_orientation` | identical physical arrivals with opposite pre-enrolled coins give opposite oriented scores; `arm_slots` follows the coin and not the arrival order; an outcome for an unenrolled position and an invalid coin are both rejected |
| `F02_enrollment_denominator` | at every look the divisor is exactly the enrolled prefix `n`, never the completed count, checked against a hand-computed four-pair table with resolved and unrevealed pairs; at `n = 0` the full range is displayed and nothing decides |
| `F03_repeated_update_idempotence` | replaying every reveal three times leaves the state signature, the enclosures and the band endpoints bit-identical; a stale elapsed-cost report is an exact no-op; a conflicting second certificate raises |
| `F04_nonoverlapping_pair_ids` | duplicate pair ids, reused arrival positions, self-overlapping pairs and facts for unowned positions are all rejected; enrollment positions are immutable and sequential |
| `F05_completion_order_permutations` | over all `720` reveal orders of the six episodes of a fixed three-pair stream the state signature and both bands are identical; the hand-derived sums, means and `r(3)` are reproduced |
| `F06_joint_failures` | `s_C = s_I = 0` gives `Z = 0` and `D = 0` with the cost tier never eligible even at a cost ratio that would be decisive; two observed failures pin both scores to `0` **without** a certificate, so `certified` stays false |
| `F07_strict_tolerance_equality` | with `relative_tolerance = 0.05`, `cost 95.0` vs `100.0` has `abs(delta) = tol = 5.0` exactly and **ties** (the decisive test is the strict `abs(delta) > tol`); `94.9` vs `100.0` is decisive; both directions; the same boundary in the enclosure enumeration |
| `F08_unknown_outcomes` | an enrolled pair with neither episode revealed contributes exactly `[-1, +1]` to both scores; a single-arm reveal plus an elapsed-cost lower bound narrows exactly to its row of section 2.5 and no further; a point reached without a certificate is **not** certified; nothing is imputed |
| `F09_cap_timeout_finalization` | the cap is an explicit finalisation rule (failure at full cap), never a silent censor or drop; the capped pair stays in the ledger and in `n`; a timeout contradicting an observed success and a final cost above the cap are both rejected |
| `F10_switch_phase_exclusion` | at the traffic switch randomisation stops, in-flight pairs are still finished under their original assignment, post-switch single-arm traffic is logged as a follow-up cohort and never enters `n`, and the switch is idempotent |
| `F11_containment_audit` | **enclosure containment.** On a multi-look eight-look stream, every pair's ultimately certified score lies inside **every** bound that pair contributed at **every** prior look, no enclosure ever widens, and the running-sum interval brackets the realised running mean at every look after enrollment closed |
| `F12_band_formula` | the alpha allocation, `rho`, `delta` and `n_min`; every locked radius against both `vband.radius_from_formula` and the independent literal transcription; an interior band at `n = 2,000` assembled by hand as `sum/n -+ r`; the clip; that the prefix is a prefix; that a prefix beyond the ledger and a radius at `n = 0` raise |
| `F13_decision_rule` | DEPLOY iff `L_h > 0` and `L_s > -delta`, RETAIN_INCUMBENT iff `U_h < 0`, both strict, both read at one look on one prefix, nothing below `n_min`; mismatched prefixes raise; deploy and harm never fire together |
| `F14_radius_sweep` | `vband.radius_from_formula(n)` equals the independent literal transcription at **strict float equality** for every `n = 1..20,000`, and equals `src/winstats.normal_mixture_radius(n, alpha=0.00625, rho=100., variance_process=n)` likewise |
| `F15_protocol_config_agreement` | the tables of this document named in the paragraph above are parsed and compared to `cells.json` value by value; tables and prose outside that list are outside its reach and it claims nothing about them |
| `F16_import_graph_independence` | importing `vband`, `vfixtures` and `tests_validation` in a fresh interpreter loads **no** module whose `__file__` is under `experiments/live_ab/` or `experiments/live_ab_validation/pinned/`, and no source file of this directory except `vcompare.py` names either path |
| `F17_atom_cost_table` | every atom's cost pair reproduces the frozen `Z` and `D` columns through `src/winstats.compare`; over **47,484 of** the `(atom, revealed arm, d, elapsed age)` states - the fixture's own delay grid, not the `2,878,680`-state sweep of section 2.5 - the cost enclosure narrows monotonically, never widens, always contains the true `Z`, and collapses to a point exactly at the thresholds of section 2.5, with the `28` boundary states that grid reaches asserted as a count |
| `F18_pinned_file_hashes` | every provenance pin is recomputed **from the file**: `src/winstats.py`, the guidance document and the #11 vocabulary document named in `cells.json` are opened, hashed, and compared against `cells.json` **and** against the hash strings printed in the header table of this document; the three sources in `pinned/` are hashed and compared against `pinned/PINNED.json`, whose file list must be exactly the Python sources present there. A pin that no longer matches the file it names fails loudly |

---

## 12. Independence, the comparison step, and what a disagreement means

### 12.1 Procedural independence

The independence of this validation is **procedural, not organizational**: the #12 author and the #11 author are
sessions of the same model directed by the same coordinator, and this is disclosed rather than described as
independent verification. What is enforced is the procedure:

1. The #12 band module, enclosure module, generator and fixtures are written **from the formula in
   `reviews/arxiv_live_design_guidance.md` alone**, together with the pinned `src/winstats.py` primitives the guidance
   itself names.
2. **`experiments/live_ab/lab_monitor.py` and `experiments/live_ab/lab_enclosure.py` were not read while this
   protocol was written**, and must not be read or imported while the #12 band, enclosure, generator or fixture code
   is written.
3. A **pinned read-only copy** of the #11 monitor is taken by the coordinator into
   `experiments/live_ab_validation/pinned/`, with each file's SHA-256 recorded in `pinned/PINNED.json` together with
   the `live_ab` commit it came from. It is loaded **only** by `vcompare.py`, and only after `vrun.py` has finished.
   **It exists as of the freeze commit**: the coordinator deposited `lab_enclosure.py`, `lab_monitor.py` and
   `lab_reference_rule.py`, mode `444`, from `live_ab` commit `5776877`, with their hashes in `pinned/PINNED.json`.
   The author of this protocol has **not opened any of those three files** - only the manifest, which carries hashes
   and a commit id and no monitor code. Their presence in this directory is exactly why item 4 below is a test and
   not a promise.
   `F18_pinned_file_hashes` (section 11) **hashes** those three files at fixture time. Hashing is not loading and is
   not reading: `F18` opens them in binary mode, feeds the bytes to `hashlib`, and never decodes, parses, imports,
   prints or otherwise inspects them; the only value that leaves the file is a 64-hex digest compared against
   `PINNED.json`. That is the whole of this directory's contact with the pinned copy before `vcompare.py` exists,
   and it is stated here rather than left for a reader to infer from the code.
4. **A test asserts the import graph**, and it exists: `F16_import_graph_independence` and
   `tests_validation.TestImportGraphIndependence`. It imports each #12 module in a **fresh interpreter** and asserts
   that no entry of `sys.modules` has a `__file__` under `experiments/live_ab/` or
   `experiments/live_ab_validation/pinned/`, and it scans every source file in this directory for either path.
   `vcompare.py` is the single declared exception, by name. This is the only *mechanical* guard on the constraint;
   without it, independence rests entirely on the docstring declarations, which is where it rested in the pre-audit
   draft.

### 12.1a What the pre-registration audit disclosed, and what it costs the independence claim

The adversarial checker who wrote `PREREG_CHECK.md` was **not** bound by the independence constraint and read the
#11 monitor in full. Its report quotes #11's decision-label alphabet, its `n = 0` and horizon branches, its
`collapsed`-flag rule and its cost certificate. **The author of this protocol read that report**, at the
pre-registration stage, after `vband.py` and fixtures `F01`-`F13` were already written. Stated plainly:

1. **`vband.py` is unchanged by the audit** and was written before it. Its cost-order enumeration is an independent
   derivation from the guidance's tolerance rule. Nothing in this revision edits it. (Had a fixture proved a defect
   in it, that would have been reported, not quietly fixed.)
2. **The section 2.5 cost thresholds are re-derived**, not copied: they are what `vband.cost_order_possibilities`
   already computed. But the coincidence between them and the #11 certificate quoted in the audit is now a **known**
   coincidence. It is therefore **not** independent evidence of agreement, and section 12.2 may not be read as
   confirming it.
3. **The decision to put the cost path in the cells came from the audit** (section 4.4). This study does not present
   that as foresight.
4. **The label bijection and the exception rule in section 12.2 are written with knowledge of #11's label
   alphabet.** That is unavoidable - a bijection cannot be frozen in advance without knowing both alphabets - and it
   is exactly why freezing it *now*, before any stream is replayed, is worth more than pretending it could have been
   written blind.
5. What this does **not** contaminate: the atom weights, `mu_h`, `mu_s`, the delay rules, the seeding, the estimators,
   the flag rule, the positive control, and every fixture expectation, all of which predate the audit or are derived
   from the guidance text alone.

The honest summary is the one section 12.1 already gives: the independence here is **procedural, not
organizational**, and after this audit it is procedural with one documented leak.

### 12.2 The comparison

`vcompare.py` replays **200 frozen streams** from namespace 2 - 25 per cell, plus every fixture stream of
section 11 - through both implementations, and compares, at **every** look:

| compared | criterion |
|---|---|
| `L_h`, `U_h`, `L_s`, `U_s` | absolute difference `<= 1e-12` (endpoints lie in `[-1,1]`, so an absolute criterion is the meaningful one) |
| decision label | **exactly** equal under the bijection below |
| `tau` in enrolled pairs | **exactly** equal |
| per-pair enclosure endpoints | absolute difference `<= 1e-12` |

**The look set.** Looks at prefixes `n = 1 ... N_max`, plus the finalization look. **No look is taken at `n = 0` on
either side**: #12 displays the full range there and, per the audit, #11 raises. That structural difference is named
here and excluded by construction, rather than discovered and adjudicated later.

**The decision-label bijection, frozen before any stream is replayed.** The two sides do not share a label alphabet,
so the mapping is fixed now rather than chosen by whoever writes `vcompare.py` after seeing the streams:

| #11 label | #12 label | note |
|---|---|---|
| no decision returned | `CONTINUE` | |
| `deploy_candidate` | `DEPLOY` | |
| `harm_keep_incumbent` | `RETAIN_INCUMBENT` | |
| `horizon_no_decision` | `CONTINUE` | **and** the #12 trial must end in `NO_DECISION`; a #11 `horizon_no_decision` at a look where #12 returns `DEPLOY` or `RETAIN_INCUMBENT` **is** a disagreement |
| anything else | - | a disagreement, not an unmapped case |

#12 has no horizon concept at all, so the #11 horizon branch has no #12 counterpart at the look level; mapping it to
`CONTINUE` at the look level and to the `NO_DECISION` trial endpoint is the only mapping under which both sides
describe the same trial.

**The exception rule.** **An exception raised by either side at a look where the other returns a value IS a
disagreement.** It is written to `comparison_defects.csv` with the exception type, its message, which side raised it,
and the seed coordinates needed to replay it alone. It is never treated as a skip, a filter, or a harness detail.

**The `certified` / `collapsed` flag is out of scope, and here is why.** The comparison covers the per-pair enclosure
**endpoints** on both scores at every look, and **not** the collapse flag. The two implementations hold incompatible
definitions: #12 marks `certified` only on a valid final-score certificate, so a hierarchy enclosure the cost tier
has narrowed to a point while an episode is still running is a point that is **not** certified, while the audit
reports that #11 requires the flag to be true exactly when both scores are points and raises otherwise. Section 6.4
says such pairs are common in every cell, not exotic, so comparing the flag would report one definitional difference
thousands of times as if it were a numerical defect. Out of scope is **not** silence: the report states the
difference, states that section 4.4's cost path is what makes it common, states that **neither reading is declared
correct here**, and escalates it under 12.3 with the rest. `vcompare.py` drives both implementations from the same
event stream and never builds one side's objects out of the other side's state, so neither constructor is fed a
state its own rules forbid.

The tolerance covers floating-point summation order only. Every comparison, agreeing or not, is written to
`results/live_ab_validation/comparison_vs_live_ab.csv`; disagreements are additionally written to
`comparison_defects.csv` with the minimal reproducing stream (cell, program, trial, look, the four endpoints from each
side, and the seed coordinates needed to replay it alone).

### 12.3 What a disagreement means, and how it is handled

> **A disagreement is a DEFECT and is reported as one. It is never reconciled by editing either side.**

Specifically, and fixed now:

1. Neither the #12 code nor the #11 code may be changed to make the two agree. Not the band module, not the enclosure
   rules, not the tolerance, not the fixture streams, not this protocol.
2. The defect is reported with its minimal reproducing stream, the two disagreeing values, and the **guidance clause**
   each side appears to implement. Both readings are stated; neither is declared correct by this author.
3. **Which side is wrong is not decided here.** The disagreement is escalated to the coordinator and the root with the
   reproducer; a change on either side afterwards is that side's owner's decision, recorded in that side's own freeze,
   and requires this comparison to be re-run and re-reported.
4. Until a disagreement is adjudicated, **#11's results do not count as validated**, which is the whole purpose of
   this study; the report says so in those words.
5. The tolerance `1e-12` is itself frozen. If a disagreement is *within* tolerance but systematic (a consistent sign
   or drift across looks), it is reported as a **noted numerical difference** with its magnitude, not silently
   accepted, even though it does not trip the criterion.
6. Agreement is reported as "the two implementations agree on these 200 streams to `1e-12`", never as "the monitor is
   correct". Two implementations of the same misreading of the guidance agree perfectly, and this comparison cannot
   detect that; the fixtures of section 11, which are derived from the guidance text rather than from either
   implementation, are the only check that addresses it, and they are weaker than a proof.
7. **Agreement on the cost-tier narrowing specifically is worth less than the rest**, and the report says so where
   it reports it. Section 12.1a item 2: the audit disclosed #11's cost certificate to this author before the
   comparison was specified, so agreement there is agreement between two readings that are known to coincide, not
   two readings that arrived independently. Disagreement there would still be informative; agreement is not.

---

## 13. Deliverables, outputs, and the one reproducible command

### 13.0 Which file provides what, and which files do not exist yet

**As of the freeze commit, `vgen.py`, `vrun.py`, `vcompare.py` and `REPORT.md` do not exist. This section specifies
them.** The names `run_validation.py` and `compare_to_live_ab.py` used in the pre-audit draft are replaced by
`vrun.py` and `vcompare.py`, so that every module in this directory shares the `v` prefix and no name in this
document refers to a file that will never be created under that name.

| file | status | provides |
|---|---|---|
| `PROTOCOL.md` | exists | this frozen pre-registration |
| `cells.json` | exists | the machine-readable twin; normative for every numeric value |
| `vband.py` | exists | the #12 enclosure, episode, band, decision rule and monitor - the object under test |
| `vfixtures.py` | exists | fixtures `F01`-`F18` and the event-replay helper. Entry point: `python vfixtures.py` |
| `tests_validation.py` | exists | unit and randomised property tests, including the import-graph guard. Entry point: `python tests_validation.py` |
| `PREREG_CHECK.md` | exists | the adversarial pre-registration audit the first revision answers |
| `PREREG_CHECK_2.md` | exists | the second adversarial pass, which re-tested the first audit's findings and raised the four the second revision answers (section 0.2b) |
| `pinned/` | exists | the coordinator's read-only copy of the #11 monitor from `live_ab` commit `5776877`, with `pinned/PINNED.json`. Nothing in this directory may load it until `vcompare.py` exists (section 12.1) |
| `vgen.py` | exists | the data-generating process of sections 4 and 5: atoms, delays, reveal schedule, elapsed-cost accrual |
| `vrun.py` | exists | the grid runner of sections 7-9; writes only `results/live_ab_validation/` |
| `vcompare.py` | exists | the pinned comparison of section 12; the only module permitted to load `pinned/` |
| `REPORT.md` | **specified, not written** | the study report of 13.3 item 6 |

### 13.1 The commands

Today, and at the freeze commit, these two run:

```
.venv/bin/python experiments/live_ab_validation/vfixtures.py
.venv/bin/python experiments/live_ab_validation/tests_validation.py
```

The grid run is specified here and its module does not exist yet:

```
.venv/bin/python experiments/live_ab_validation/vrun.py --out results/live_ab_validation
```

It writes **only** inside `results/live_ab_validation/`; a guard refuses any path outside that directory and the run
aborts rather than writing elsewhere. It is deterministic given the master seed and the frozen config: two runs
produce byte-identical outputs apart from the timing fields of `compute.json`, which is asserted by re-running one
cell block.

The comparison step is a second, separate command, run afterwards, and its module does not exist yet either:

```
.venv/bin/python experiments/live_ab_validation/vcompare.py --out results/live_ab_validation
```

### 13.2 Output files (all under `results/live_ab_validation/`)

| file | content |
|---|---|
| `manifest.json` | SHA-256 of every #12 source file, of `cells.json`, of this protocol, of `src/winstats.py`, of the guidance document; the master seed; numpy and CPython versions; platform; the repository commit; the selected budget tier |
| `budget.json` | smoke measurements, the projection, the selected tier - written **before** the reported grid runs |
| `smoke/` | the smoke run's timing and memory record only |
| `fixtures_report.json` | per-case pass/fail for `F01 ... F18` (section 11) |
| `miscoverage.csv` | section 9.1, per cell x construction x gate, with Wilson intervals and flags |
| `decisions.csv` | section 9.2, per cell x construction, with Wilson intervals and flags |
| `decision_time.csv` | section 9.5, capped and conditional decision-prefix quantiles |
| `unresolved.csv` | section 9.5 resolution quantities |
| `horizon_summaries.csv` | section 9.6, at `n = 100 / 500 / 2,000` |
| `trials.csv.gz` | one compact record per (cell, program, trial, construction): decision, `tau`, the miscoverage flags, the unresolved fractions, `never_conjunct`, `decided_at_finalization` |
| `compute.json` | section 9.5 compute counts, seconds, peak RSS, output bytes |
| `comparison_vs_live_ab.csv`, `comparison_defects.csv` | section 12 |

### 13.3 Deliverables of the study

1. This frozen protocol and `cells.json`, committed **before any simulation outcome exists**.
2. The synthetic data-generating-process definitions of section 4 with their ground truth derived by enumeration
   (section 4.1), not by simulation.
3. Immutable seed, config and code hashes in `manifest.json`.
4. One reproducible command writing only its own directory (section 13.1).
5. Tables, manifests and the fixture report (section 13.2).
6. A concise report `experiments/live_ab_validation/REPORT.md` naming **the validated adapter commit** - the exact
   `live_ab` commit and file hashes recorded in `pinned/PINNED.json` - and its limitations, which are section 1.3
   repeated in full and not summarized away.
7. Measured smoke-run seconds, peak memory and projected CPU time, deposited in `budget.json` **before** full
   execution (section 8).

### 13.4 Retention

**Every unfavourable or inconclusive result is retained and reported.** No cell, construction, gate or row is dropped,
and no run is repeated to obtain a different answer. If a result is unfavourable to the `ADAPTER`, it is reported
under section 12.3 as a defect. If a result is inconclusive, it is reported as inconclusive, with the resolution
limits of section 9.3 beside it.

---

## 14. Change control

This protocol and `cells.json` are frozen on commit. Any change to a cell, a parameter, a seed, the grid, an
estimator, a reported quantity, the flag rule or the positive control is a **new protocol version with its own
freeze**, and every result produced under the old version keeps the old version's label and is reported beside the
new one rather than replaced. Typographical corrections that change no value are recorded as such with the
before/after text. The budget tier selected by section 8.2 is not a change to this protocol: it is an output of a rule
this protocol fixes, and it is recorded in `budget.json`. Section 8.2's `T4` variant of section 6 is deposited in
`cells.json` before execution for the same reason: a table written after a measurement is not a pre-registered table.

**The one pre-freeze revision is on the record, not inside the freeze.** Sections 0.2 and 4.4 and
`cells.json` -> `pre_freeze_revision` describe the single revision made after the adversarial audit and before any
simulation outcome existed. It is not a version bump, because nothing had been committed or frozen when it was made
and no result exists under any earlier version - there is nothing to report beside. **From the freeze commit onward
this clause has no successor: the next change of any value in this document is a new version, whatever it is, and
whoever asks for it.**

### 14.1 Post-freeze corrections that change no value

Each entry below is a correction made **after** the freeze commit under the clause above that permits
"typographical corrections that change no value ... recorded as such with the before/after text". Each carries its
authority, its before text and its after text. **No entry here moves a cell, a parameter, a seed, the grid, an
estimator, a reported quantity, the flag rule or the positive control.** Anything that did would be a new version.

---

**Correction 1 - 2026-09-20 - STATUS CORRECTION, CHANGES NO VALUE.**
Authority: `experiments/live_ab/design/COORDINATOR_DECISIONS.md` revision 9, item 34.

Cause: section 13.0's status column asserted that `vgen.py`, `vrun.py` and `vcompare.py` do not exist. Writing them
to this frozen specification - which is exactly what 13.0 instructs - made that assertion false, and fixture `F15`
failed on the contradiction, so `vrun.py` aborted before the grid. The pre-registration was working as designed: a
frozen document refusing to run while it describes a world that no longer holds.

Scope: the status column of the 13.0 table for those three rows, and the corresponding module map in `cells.json`,
which `F15` compares against it value for value. **Nothing else in 13.0 changed, and no value anywhere changed.**
Section 13.0's preamble sentence, "As of the freeze commit, `vgen.py`, `vrun.py`, `vcompare.py` and `REPORT.md` do
not exist", is a statement about the freeze commit, is still true, and is deliberately left standing.

BEFORE (`PROTOCOL.md` section 13.0, three rows, status column only):

```
| `vgen.py` | **specified, not written** | the data-generating process of sections 4 and 5: atoms, delays, reveal schedule, elapsed-cost accrual |
| `vrun.py` | **specified, not written** | the grid runner of sections 7-9; writes only `results/live_ab_validation/` |
| `vcompare.py` | **specified, not written** | the pinned comparison of section 12; the only module permitted to load `pinned/` |
```

AFTER:

```
| `vgen.py` | exists | the data-generating process of sections 4 and 5: atoms, delays, reveal schedule, elapsed-cost accrual |
| `vrun.py` | exists | the grid runner of sections 7-9; writes only `results/live_ab_validation/` |
| `vcompare.py` | exists | the pinned comparison of section 12; the only module permitted to load `pinned/` |
```

BEFORE (`cells.json` -> `modules`): `vgen.py`, `vrun.py` and `vcompare.py` were keys of
`specified_here_but_do_not_exist_at_the_freeze_commit`.
AFTER: they are keys of `exist_at_the_freeze_commit` - the set `F15` maps the `exists` status onto - each with
"WRITTEN AFTER THE FREEZE COMMIT, NOT AT IT" prefixed to its own description so the key name cannot be read as a
claim that they existed at the freeze, and with a new `modules.status_correction_2026_09_20` block recording what
moved, from where, to where and why. `REPORT.md` remains in
`specified_here_but_do_not_exist_at_the_freeze_commit`; this correction does not cover it.

---

**Correction 2 - 2026-09-20 - WITHDRAWAL OF A FALSE SENTENCE, CHANGES NO VALUE.**
Authority: `experiments/live_ab/design/COORDINATOR_DECISIONS.md` revision 9, item 35(b).

Cause: section 2.5's closing paragraph claimed that sections 6.3 and 6.4 were computed with the governing predicate.
They were not: recomputing section 6 under the predicate disagrees with the frozen 6.3/6.4 tables in 13 entries at
`N_max = 2,000` and 14 at `N_max = 1,000`, each by one unit in the fourth decimal, while recomputing under 2.5's own
closed-form paraphrase reproduces all of 6.1-6.4 with zero disagreements. The tables were therefore built with the
paraphrase, in exactly the 128 boundary states 2.5 itself names.

Scope: **the sentence only.** The frozen values in 6.3 and 6.4 are NOT edited - see ruling 35(a) and (d): the
predicate still governs, and it is what `vband`, `vgen`, `vcompare` and `F17` implement, so the grid, the decision
rule and every reported quantity are unaffected. The predicate-reading recomputation is deposited **beside** the
frozen tables, not in place of them, in `ADDENDUM_SECTION6.md` under ruling 35(c).

BEFORE (`PROTOCOL.md` section 2.5):

```
**The predicate governs, there and everywhere.** It is what `vband` computes and what `compare` itself uses, and
this study's numbers in sections 6.3 and 6.4 are computed with it.
```

AFTER:

```
**The predicate governs, there and everywhere.** It is what `vband` computes and what `compare` itself uses.
**The claim that stood here, that "this study's numbers in sections 6.3 and 6.4 are computed with it", is FALSE
and is withdrawn** (coordinator ruling 35(b), 2026-09-20). The fact: sections 6.3 and 6.4 were computed with the
closed-form paraphrase of the preceding paragraph, which differs from the governing predicate in exactly the 128
named boundary states.
```
