# PROTOCOL_V2: versioned amendment to `live_ab_validation` under `PROTOCOL.md` section 14

Version string **`v2-cpu-validation`**. This document is an **amendment**, not a replacement. `PROTOCOL.md`
(`v1-cpu-validation`) and `cells.json` stay frozen exactly as they are, on disk and in the history, and **this
document changes no value in either of them**. Read the two together: `PROTOCOL.md` is the base text and everything
it says still governs except where a numbered clause below supersedes it for `v2` only.

| field | value |
|---|---|
| status | **NOT FROZEN. NOT CLEARED TO RUN.** This is the amendment prepared for review; see section 9 |
| authority | root disposition `reviews/cpu_v1_delivery_root_disposition.md`, sections A, B, C, D and E; coordinator `experiments/live_ab/design/COORDINATOR_DECISIONS.md` revisions 12, 13 and 14 |
| change-control clause invoked | `PROTOCOL.md` section 14, first sentence: a change to an estimator or a reported quantity is "a **new protocol version with its own freeze**, and every result produced under the old version keeps the old version's label and is reported beside the new one rather than replaced" |
| supersedes | nothing. `v1` is preserved entire, is still cited as `v1`, and is reported **beside** `v2` |
| substantive changes | **three**, listed in section 1, and no others |
| prespecification status | **post-`v1`-CPU-result development, pre-live amendment.** Not globally outcome-free prespecification. Section 4.3 states this at length and does not soften it |
| environment | `/Users/yukangzengcmac/ICLR-WinRatioAgentEvals/.venv/bin/python`, CPython 3.12.13, numpy 2.4.1, macOS arm64. CPU only. No model call, no API call, no network, no download, no new dependency |
| measured while writing this document | `#12` `vfixtures.py`: **18/18**, three times. `#12` `tests_validation.py`: **0 failures** three times, at **88**, **106** and **107** tests - **the count moved under this document while it was being written**, see section 10. `#11` `tests_lab_*.py`: **474 tests, OK**, in 243.195 s. Every arithmetic value quoted below was recomputed here; section 10 lists what was run |

---

## 0. What this amendment is, and what it is not

**It is** the written form of the one substantive change the root authorized, plus the measurement-contract repair
the root's open witness forces, plus the wording corrections the root required in sections C, D and E of the
disposition.

**It is not** a re-run, a clearance to re-run, a new scientific question, a new cell, a larger horizon, a relaxed
margin, a changed threshold, a new seed, a new model call, or a reopening of any accepted baseline result. The root
asked for "no duplicate full-grid job, larger horizon, extra cell, model change or new model call now", and none is
requested here.

**It does not decide anything the root reserved.** Which of the two look-schedule readings of section 1.2 is the
legal one is a coordinator ruling; this document states both, states the consequence of each, and recommends one
with its reason.

---

## 1. The three substantive changes, and there are only three

### 1.1 The tighter feasible-completion enclosure becomes the `v2` primary

**What changes.** `v1` compared an adapter built from `reviews/arxiv_live_design_guidance.md` item 3 against the
`#11` monitor as it stood at `577687799e8588077c036b4d94f1afc839d78e4f`, whose `protocol_FINAL.md` item 5 carried a
**forward** cost certificate only and fell back to `[-1, 1]` otherwise. `#11`'s item 5 has since been **completed**
(coordinator ruling 54, discharged by ruling 58; recorded at `protocol_FINAL.md` section 7.5a) with the **reverse**
certificate `ell > (1 - tol) * L_r + eps`, which removes a partner win that the already-spent elapsed cost has made
infeasible. The root's disposition section A "**now permits the tighter feasible-completion rule to be the proposed
v2 live primary**, superseding the earlier requirement to retain the conservative rule as primary."

`v2` therefore monitors the **completed** enumeration as its primary object, on both sides of the comparison.

**Why this is a power change and not a validity change, stated as a measurement rather than an opinion.** The `v1`
comparison found the old rule **wider in 151,032 of 151,032 disagreeing per-pair endpoint rows and never narrower**
(`REPORT.md` section 11.2; root disposition, "All 151,032 pair-endpoint disagreement rows show the old live interval
containing the tighter interval"). Nothing the old rule produced was wrong. The root's boundary on that evidence is
adopted verbatim and not widened: "Distinct intervals can both be valid; row containment is not a proof for every
reachable state."

**What makes the enumeration closed rather than asserted.** With both episodes successful the revealed episode wins
tier 1 iff `x > L_r / (1 - tol)`, the pending partner wins iff `x < (1 - tol) * L_r`, and between them the pair ties;
six exhaustive rows result. Every feasible set is a **contiguous** run of `{-1, 0, +1}`, so `[min F, max F]` **is**
the feasible set and not a relaxation. Verified by `#11` at 16,000 states in exact rational arithmetic with 0
mismatches, equality against brute force at 1,120 of 1,140 grid states with the other 20 inside the declared `1e-9`
band where the enclosure is wider by at most one value and **never narrower**, and both invariants over 21,784
completion chains (ruling 58). `v2`'s acceptance of this rule is conditional on section 4.1, which is the root's
condition and not a formality.

**What this does to the `v1` comparison verdict.** `v1`'s `122,786` disagreeing looks are **a contract mismatch
between two differently-declared policies, not 122,786 findings** (coordinator ruling 55). `REPORT.md` is corrected
accordingly in its errata section 16. The equality contract becomes meaningful only in `v2`, after the two policies
coincide **and** after the pins are matched (section 4.2). Agreement in `v2` will mean the two implementations
agree - never that the rule is correct (`PROTOCOL.md` section 12.3 item 6, which still governs).

### 1.2 The corrected event schedule: declare the legal looks, batch simultaneous events, and include every required completion-index change

**The defect being repaired.** The deposited `v1` runner builds `n + 1` states per trial - one per enrollment prefix
`n = 1 ... N_max`, plus the finalization look - and **omits every intermediate look during the drain window at which
a completed-data baseline's completion index changes**. The root's witness is exact and it reproduces here:

| field | value |
|---|---|
| construction | horizon `N_max = 1,000`, cell `C1` support atoms, finalization tick 1,200, all first reveals simultaneous with completion |
| blocks | pairs 1-500 neutral, resolving at enrollment; 501-600 with `H = D = +1`, resolving at tick 1,010; 601-700 with `H = D = -1`, resolving at 1,100; 701-1,000 neutral, resolving at 1,200 |
| legality | every long offset used lies in 200-509, inside `LONG`'s declared 100-699 support; every short offset in 0-19; all three atoms carry positive weight under `L1` |
| at the omitted tick 1,010 | both baselines stand at index 600, both means are `1/6`, `r(600) = 0.153363950255`, and **both lower bounds are `+0.013302716411`** |
| consequence | `L_h > 0` and `L_s > -delta` hold at the **same** look, so the deploy gate fires for both baselines, and `mu_h = mu_s = 0` lies outside both bands - a decision **and** a double miscoverage |
| what the `v1` runner records | `NO_DECISION`, `ever_miscover_h = False`, `ever_miscover_s = False`, for both baselines |
| independently reproduced | `LASTLOOK_CHECK.md` sections 1 and 2, to every digit, at `T4` **and** at `T1`, the horizon that actually ran |

`PROTOCOL.md` section 7.1's claim that one look per enrollment prefix is an **exact** reduction is **withdrawn for
the two completed-data baselines**. It survives for the `ADAPTER`: at a fixed prefix the adapter's denominator and
radius are frozen and each pair's enclosure can only be replaced by a subinterval of itself, so `L` is nondecreasing
and `U` nonincreasing over the looks sharing that prefix, and the last look at prefix `N_max` **is** the finalization
look. Checked over every drain tick of 16,000 real grid trials: **0 non-monotone, 0 adapter events at a drain tick
the finalization look does not also carry** (`LASTLOOK_CHECK.md` section 3). **Not one deposited `ADAPTER` number
moves under any reading.**

**What `v2` declares. This is the amendment's operative text for the look schedule.**

1. **The legal event schedule.** A look is taken at the end of every tick `t = 1 ... N_max + W` at which **any** of
   the following changed since the previous look: the enrolled prefix `n`; any pair's completion status; any
   construction's completion index; any pending episode's certified elapsed cost. The drain window `t = N_max+1 ...
   N_max+W` is included in full and is **not** collapsed to its final tick. The finalization look at
   `t = N_max + W = 2,200` is always taken, whether or not anything changed there.
2. **Simultaneous-event batching, declared rather than left open.** When several pairs complete at one tick, `v2`
   evaluates the look **once, after all events of that tick are applied** - the *batched* reading. The *finest*
   reading, one event at a time under enrollment-position tie order, is **also computed and reported beside it**, as
   a declared sensitivity, because `PROTOCOL.md` section 7.1's own phrase "each further fact - a reveal, a
   resolution, or an increase in a pending episode's elapsed cost" is arguably the more literal reading and it is the
   larger effect. Neither is asserted to be the unique right one; both are reported, and the batched one is primary.
   **Reason for that choice, stated so it can be overruled:** the batched reading is the one a live monitor can
   actually execute, because a live drain delivers completions in batches and the intra-batch order is a property of
   the serving stack rather than of the design. One asymmetry must accompany any ruling here: for `CPREFIX` the
   finest set is a function of the completed count `k` alone and is therefore the exact union over **every**
   admissible tie order, so its column is order-independent; for `NAIVE` the intra-tick partial sums depend on the
   order, so its finest column is **one admissible schedule and not a bound over all of them**.
3. **Every required completion-index change through the fixed finalization window is included**, for every
   construction, with no exception for the drain interior.
4. **The same declared schedule applies to all three constructions.** Full and partial observations are compared at
   the **same prefix**. No construction gets a look another does not.
5. **Unresolved units are retained at finalization**, exactly as `PROTOCOL.md` section 7.3 already requires: pairs
   still unresolved keep the enclosure they have and enter `L` and `U` through it; nothing is censored, dropped,
   imputed or deleted; the denominator is always `n = N_max`.
6. **The root's witness becomes a regression fixture** of `v2` and is asserted to produce a decision and a double
   miscoverage for both baselines under both readings. A `v2` runner that returns `NO_DECISION` on it fails the
   fixture gate.
7. **Component-gate, decisive-tier and width summaries are retained** so that abstention can be explained rather
   than only reported, per the root's disposition section B - which notes these "are not all present in these
   summary fields and should not be claimed delivered" for `v1`. `PROTOCOL.md` section 9.5's list of reported
   quantities is extended by these and by nothing else; **no existing quantity is dropped**, and `v1`'s existing
   `cost_collapsed_fraction` and `cost_narrowed_fraction` already carry part of the width story.

**What this repairs and what it does not.** It repairs a **measurement contract**. It changes no theorem, no
estimand and no gate, and it does not select a favourable outcome: every affected deposited number is **understated**
in `v1`, which is the direction that flatters the baselines rather than the object under test
(`LASTLOOK_CHECK.md` section 4). The fixed-prefix nesting argument still supports a coverage reduction for the
partial-enclosure adapter; it never established a **first calendar-time** decision, and changing a completed-data
baseline's index invalidates the reduction for that baseline's crossing events.

### 1.3 The enrollment prefix and the elapsed decision time are recorded as two separate quantities

`v1` recorded a single `tau`, defined at `PROTOCOL.md` section 9.5 as "the enrolled prefix `n` at the first look
whose condition fired". That is an **enrolled-prefix** quantity. It is **not** an elapsed time and it is **not** a
saving, and `v1` correctly refused to report it as one; but one number cannot carry both meanings, and the corrected
schedule of section 1.2 creates looks whose prefix is pinned at `N_max` while the tick advances.

`v2` records **both**, separately and always together:

| name | definition | units |
|---|---|---|
| `tau_prefix` | the enrolled prefix `n` at the first look whose condition fired | enrolled pairs |
| `tau_tick` | the tick `t` at the first look whose condition fired | enrollment ticks of the simulated schedule |

`tau_prefix` is `v1`'s `tau` under a new name, so the two versions can be compared term for term. `tau_tick` is new
and exists only because section 1.2's schedule makes it well defined. Neither is ever reported as wall clock,
latency, throughput, a saving, or a paired comparison between constructions; `PROTOCOL.md` section 3's prohibition is
carried into `v2` unchanged and applies to both columns.

**One measured fact about the relation between them**, so that nobody reads `tau_tick` as free information: under the
batched reading every decision the drain adds carries `tau_prefix = N_max = 2,000`, which is exactly what
`PROTOCOL.md` section 9.5's capped rule had **already** assigned that trial, and the summed capped `tau` is
**identical** between the reduced and the all-ticks schedules in all 24 cell/construction rows. The reduction lost
the *fact* of the decision, not its *prefix* (`LASTLOOK_CHECK.md` section 4.3). Under the finest reading the summed
capped `tau` does fall, because intra-tick states fire during enrollment.

---

## 2. What does NOT change

**Nothing in this list may move in `v2`, and no clause of this document moves any of it.**

| frozen in `v1`, unchanged in `v2` | value | where `v1` fixes it |
|---|---|---|
| `alpha_gate` | `0.00625` per band | `PROTOCOL.md` 2.1 |
| alpha allocation | `.05` program / 4 trials = `.0125` per trial / 2 monitored scores | `PROTOCOL.md` 2.1 |
| `rho` | `100.` | `PROTOCOL.md` 2.1 |
| `variance_process` | `V_n = n` | `PROTOCOL.md` 2.1 |
| `delta`, the success margin | `0.03` | `PROTOCOL.md` 2.1 |
| `n_min` | `100` | `PROTOCOL.md` 2.1 |
| the radius formula and its pinned primitive | `r(n) = sqrt((n+rho) log((n+rho)/(rho alpha^2)))/n` via `src/winstats.py` | `PROTOCOL.md` 2.2 |
| the two gates and the **same-look conjunction** requirement | `L_h > 0` **and** `L_s > -delta` at one look | `PROTOCOL.md` 2.4 |
| episode stopping, the deadline rule, and the finalization rule | `N_max = 2,000`, drain `W = 200`, finalization look at tick 2,200, nothing censored | `PROTOCOL.md` 7.3 |
| the eight cells, their atom weights, `mu_h`, `mu_s`, the delay rules | unchanged | `PROTOCOL.md` 4 |
| the seeding and the fixed five-array draw order | unchanged | `PROTOCOL.md` 5 |
| the exceedance flag **rule** (Wilson lower limit above nominal) | unchanged | `PROTOCOL.md` 9.3 |
| the precommitted positive control and its frozen sentence | unchanged | `PROTOCOL.md` 9.4 |
| the hierarchy, the eligibility rule, the tie rule, `tol = 0.05`, the `0.95` certificate constant, the `1e-9` margin | unchanged | `protocol_FINAL.md` 7.5a |
| the retention rule: every unfavourable and inconclusive row is reported | unchanged | `PROTOCOL.md` 13.4 |
| every limitation of `PROTOCOL.md` section 1.3 | unchanged, and repeated in full in the `v2` report | `PROTOCOL.md` 1.3 |

The *interpretation* of the flag rule is corrected in section 6 below. **The rule itself does not move**: the same
Wilson limit, the same nominal, the same comparison. What changes is what a flag and the absence of one are allowed
to be said to mean.

---

## 3. `v1` is preserved, and is reported beside `v2`

This is `PROTOCOL.md` section 14's own clause and it is the operative constraint on every deliverable of `v2`.

1. **No `v1` result is edited, moved, overwritten or deleted.** Everything under
   `results/live_ab_validation/` stays byte-identical and keeps the label `v1-cpu-validation`. `v2` writes only to
   **`results/live_ab_validation_v2/`**, which the delivered resource check of section 9.1 has already established,
   and to no other directory.
2. **No frozen value in `PROTOCOL.md` or `cells.json` is edited by this amendment.** The three post-freeze
   corrections already recorded in `PROTOCOL.md` section 14.1 remain the only edits to that file, and each of them
   changes no value.
3. **Every `v2` table that has a `v1` counterpart prints both**, side by side, with both version labels, and the
   `v1` column is never replaced by the `v2` column. Where a number moves, both numbers are shown and the
   difference is attributed to the specific clause of section 1 that caused it.
4. **`REPORT.md` is not erased.** It keeps its `v1` findings and gains a versioned errata section (its section 16)
   recording, with before/after text, every sentence corrected under this amendment. A reader who cites the old
   sentence must meet the correction in the same file.
5. **The `v1` pin stands.** See section 4.2: it is deliberately not re-pinned, and its supersession is recorded in
   `cells.json` rather than applied.

---

## 4. The root's conditions on the `v2` primary

The root's permission in disposition section A is explicitly **"conditional on explicit review of the entire rule,
equality/tie boundaries, clipping/support, updates at a fixed enrolled prefix, usage semantics, and shared
live/validation pins"**, and it is "permission to prepare the amendment, **not trial clearance**." The three
conditions are restated here as gates on the `v2` freeze, not as aspirations.

### 4.1 Condition 1: the ENTIRE rule block is reviewed, not only the completed certificate

The reviewed object is `#11`'s **rule block** as `lab_common.rule_block_sha256` defines it - the decision-defining
subset of `config.json` named by `ARCHITECTURE_FINAL.md` 6.2 and protocol Appendix B - and not merely the changed
bullet. The block is these **19** keys:

```
rule_id, trials, execution_order, monitor, hierarchy, eligibility_rule, tie_rule,
enclosure, coin, seed_rule, roster.strata, roster.exclusion_rules, roster.pairing,
roster.n_pairs_rule, design_seed_base, execution.max_attempts, execution.auto_abort,
plumbing_fail_conditions, integrity_label_rule
```

Its hash on the working tree at the time this document was written, computed here rather than quoted:
**`cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607`**. The `v2` freeze must record the hash of the
block it actually reviewed, and the review must cover, one by one and in writing:

- **Equality and tie boundaries.** The two tier-1 thresholds `x > L_r/(1-tol)` and `x < (1-tol) L_r`, the tie
  interval between them, strictness at each endpoint, and the `1e-9` margin's direction. The 20 grid states inside
  the `eps` band where the enclosure is wider by at most one value and never narrower are named individually, not
  summarised.
- **Clipping and support.** That every enclosure endpoint lies in `[-1, 1]`, that the intersection with `[-1, 1]`
  is applied where the theorem permits it, and that no substituted endpoint leaves the declared ternary support
  where a ternary-count function is used.
- **Updates at a fixed enrolled prefix.** That improving an enclosure at a fixed prefix replaces an interval by a
  subinterval of itself, that old factors are recomputed rather than retained, and that monotonicity is claimed
  **only** at a fixed prefix - never across an increasing prefix, where adding unresolved pairs can reduce evidence.
- **Usage semantics.** What the cost meter measures, that elapsed cost is already spent and cannot be un-spent,
  and that the cost meter and the reveal clock are **not** tied to each other in this study
  (`PROTOCOL.md` 1.3 item 7), which is a declared simplification in the conservative direction.

A `v2` freeze that records only "item 5 was completed" does not discharge this condition.

### 4.2 Condition 2: the live and CPU pins must be MATCHED, and they currently are not

The `v1` pin is **deliberately not updated**, under coordinator ruling 60, and its supersession is recorded in
`cells.json -> vocabulary_alignment.superseded_by` rather than applied. `F18_pinned_file_hashes` passes on that
record, and **18/18 fixtures pass**, which is the pin doing its job: the honest statement is that `v1` validated
`#11` as it stood at commit `5776877` against `protocol_FINAL.md` at `3c76e8eb...`, and re-pinning now would assert
that the completed run covered a version of `#11` that did not exist when it ran.

The mismatch is concrete, and it is measured here rather than assumed:

| pinned file | `v1` pin (frozen, do not edit) | the file as it now stands |
|---|---|---|
| `experiments/live_ab/design/protocol_FINAL.md` | `3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2` | `b1ff97cc163ce7ea121ebd578a4c37de09d5ed7223f2029e5d56118cdc790822` |
| `pinned/lab_enclosure.py` vs `experiments/live_ab/lab_enclosure.py` | `47c523128b0abf91165670772940ee096827e12d533556ef1fd26c60dc578d0a` | `da1b300d0fc99608f3b4c919d33ed546d20f2547c9339bd03e6ce6c7b9290d74` |
| `pinned/lab_monitor.py` vs `experiments/live_ab/lab_monitor.py` | `8c20e07205748e59dad4224420e7804103d1d73e41733ccc2a91df5f8aebeced` | `94d70b8d766376a697271087a1879de32170d4827bb25211c33f550232c2af91` |
| `pinned/lab_reference_rule.py` vs `experiments/live_ab/lab_reference_rule.py` | `6219cc64f439e7bf64b4da20e4076429ccf7ea9f3d5655090f27b4a20ae360b1` | `8f8b69f01e09a92ca77a665e19bbd8f8eeba0ceef1ddab0bc3cb09b0fb9ee6fd` |

*(The `v1` column is `cells.json`, `pinned/PINNED.json` and `REPORT.md` section 1; the current column is
`shasum -a 256` on the working tree at repository commit `db930d7dc3bac0ae1644170433f769b5d3875e84`, where
`experiments/live_ab/` is clean, so those three digests are also the blobs at that commit. **All four rows differ.**
Every digest here is printed as a single unbroken 64-character token on purpose: a first draft of this table broke
them into spaced groups for legibility and silently dropped two characters from two of them, which a machine check
caught. A provenance table that a reader cannot paste into `shasum` is not a provenance table.)*

**Therefore, before any `v2` comparison means anything:** re-pin `protocol_FINAL.md` to the completed text, take a
**fresh** read-only snapshot of `pinned/` from the `#11` commit that carries the completed enclosure, record that
commit and the three new digests in the `v2` manifest, and state the `v1` pin beside it as the superseded one. Until
that is done, the `v1` equality contract remains **unmeasured** and the `122,786` disagreements remain a contract
mismatch between two declared policies rather than findings.

### 4.3 Condition 3: the post-`v1`-CPU, pre-live development is disclosed, in these words

**The tighter enclosure is not outcome-free prespecification and this document does not describe it as one.** The
incompleteness of item 5 was surfaced **by the `v1` CPU grid comparison**. Completing it is therefore
**post-`v1`-CPU-result development** and a **pre-live amendment**. The precise and only sense in which it is
outcome-free is this one: **no trial episode has ever run**, so there is no live outcome it could have been selected
to favour. That is the sense claimed, and nothing broader.

Two further disclosures belong with it, because omitting either would make the first one misleading:

1. **A replay of the original seed coordinates is a paired comparison after development, not a fresh independent
   calibration sample.** Root disposition section C: "Treat that replay as paired comparison/reproduction after
   development, not fresh independent calibration." `v2` reports it as such wherever it reports it.
2. **The `v1` pre-registration already carried a one-directional leak of `#11` detail** into its author's hands
   through the adversarial checker's report (`PROTOCOL.md` section 0.2), and `PROTOCOL.md` section 12.3 item 7
   already fixes the consequence: agreement on the cost-tier narrowing is agreement between two readings **known to
   coincide**, not two that arrived independently. That remains true in `v2` and is strengthened by it, because `v2`
   deliberately aligns the two policies. `v2` therefore reports **disagreement** as informative and **agreement** as
   uninformative on that tier specifically.

---

## 5. The horizon is a RULE, not a number, and this document quotes no single number as the horizon

**The rule, which is the only thing frozen.** From `protocol_FINAL.md` section 3.3:

```
N_P = floor(n_S1 / 2) + floor(n_S2 / 2)
```

where `n_S1` and `n_S2` are the counts of the **verified roster after every exclusion of section 3.2** - the six
declared smoke tasks and rules 2-4 (duplicates, sweep failures, and the remaining prospective exclusions). Pairs are
formed **inside** a stratum, so each stratum keeps its own leftover `(n_S1 % 2) + (n_S2 % 2)` and no pair crosses the
strata. `N_P` is never `n_total // 2`. `N_P` is the number of pairs in the frozen `arrival_order_T<e>.json` and that
file is the authoritative value; `monitor.n_max` is set from `roster.n_pairs` at freeze time and never later.

**Under the proposed metadata-based stratum refinement** - pilot-exposed MBPP, pilot-exposed HumanEval, previously
unobserved MBPP - the same rule applies **within each group** and the horizon is the sum of the three group floors.
The root permits preparing this refinement, as an explicit pre-live amendment and not a cosmetic fix; it changes
pairing, and therefore the design-specific target distribution, so the pooling weights, the ordering and the actual
enrollment-indexed target must be stated explicitly rather than claiming the estimand is unchanged.

**Why no single number is quoted as the horizon.** The root's disposition is explicit: "The actual horizon must be
computed from the verified roster after all exclusions; **565 is an upper ceiling, not a guaranteed final count**."
The documented allocation of the six smoke exclusions to previously unobserved MBPP gives upper group counts
`427 / 164 / 541` and floors `213 + 82 + 270 = 565`. Two things follow, and the second is the one that is usually
dropped:

1. **`565` depends on that documented allocation.** Computed here over all 28 allocations of six exclusions among
   the three groups, `N_P` is **565 or 566** under the two-stratum rule and **565 or 566** under the three-group
   rule; the documented allocation gives exactly **565** under both. Six *unspecified* exclusions would therefore
   not justify the grouped ceiling by themselves, which is the root's point.
2. **Rules 2-4 of section 3.2 have not been applied yet**, so the verified count can only go **down** from there.

**`568` is retained only as a labelled historical pre-exclusion example**: `floor(591/2) + floor(547/2) = 295 + 273`,
the same rule applied to the candidate lists before any exclusion. It is not a horizon. `569` is `1138 // 2`, the
unstratified count, is not a horizon of this program under any reading, and survives only as a labelled reference row
in the radius table.

**Operative instruction for `v2` and for every document that cites a horizon.** Cite the rule. Where a number is
needed for an illustration, print it with its qualifier attached in the same sentence - "at most 565 under the
documented allocation of the six smoke exclusions, before rules 2-4 of 3.2" - and never as "the horizon". The `v2`
report carries the realized `N_P` from the verified roster when and only when that roster exists.

---

## 6. Monte Carlo wording: a flag is an ALERT

This section supersedes, **for `v2` and for the interpretation of `v1`**, every sentence in `PROTOCOL.md` sections
9.3 and 1.3 item 5, and in `REPORT.md`, that reads a flag or the absence of one as more than an alert. It changes no
flag rule and no threshold. `REPORT.md` section 16 records the corrected sentences with their before/after text.

### 6.1 The arithmetic is correct and is not in question

The Wilson calculation is correct and the critical counts are correct **observed-count thresholds**. Recomputed here
from the frozen rule (flag iff the Wilson lower limit exceeds the nominal `0.00625`):

| `N` | smallest flagging count | its rate | ratio to nominal | Wilson interval at that count |
|---|---|---|---|---|
| 8,000 | **64** | `0.008000` | `1.280x` | `[0.006270262846, 0.010202009812]` |
| 20,000 | **147** | `0.007350` | `1.176x` | `[0.006257155029, 0.008632058097]` |

With `x = 0` the interval is `[0, 0.000479951888]` at `N = 8,000` and `[0, 0.000192036056]` at `N = 20,000`.

### 6.2 What a flag is, and what the absence of one is

**A flag is a sampling alert requiring diagnosis. It is not proof of a defect, and the count at which it fires is not
a minimum detectable true rate.** The root's own illustration, recomputed here exactly with `scipy.stats.binom.sf`:

> **At a true event rate of `.007` and `N = 8,000` trials, the probability of reaching the 64-event flag threshold is
> `0.1571523834`** - even though `.007` **exceeds** the nominal `.00625`.

So a true rate that genuinely violates the nominal bound goes unflagged about **84%** of the time at this resolution.
Three further values, computed here, close both directions of the error:

| true rate | relation to the nominal `.00625` | `P(X >= 64 | N = 8,000)` | `P(X >= 147 | N = 20,000)` |
|---|---|---|---|
| `.00625` | equal to it | **`0.0314151088`** | **`0.0292396037`** |
| `.007` | above it, below the `1.280x` ratio | `0.1571523834` | `0.2874093726` |
| `.008` | **exactly** the `1.280x` ratio | **`0.5168241304`** | `0.8585531745` |
| `.010` | `1.6x` it | `0.9715571681` | `0.9999655074` |

**Read the first and third rows together, because they are the two halves of the correction.** A flag can fire at a
rate exactly **equal** to the nominal, with probability about 3%. And at a rate exactly **at** the `1.280x` ratio the
flag fires only about **52%** of the time. The familiar sentence "the design can only flag a per-gate rate at or
above `1.280x` nominal, and a violation smaller than that would pass unflagged" is therefore wrong in **both**
directions: smaller violations do sometimes flag, and violations at or above that ratio frequently do not. The ratio
is the point at which the **observed** rate would have to land to produce a flag; it is not a property of the true
rate and it is not a detection guarantee.

### 6.3 The rules that follow, and they are binding on `v2`

1. **Do not require zero errors, all cells unflagged, or a favourable decision as a success criterion.** No such
   criterion exists in `v1` and none is added in `v2`.
2. **Investigate every alert on four axes** - truth, assumptions, implementation, and Monte Carlo uncertainty -
   before calling it a defect or dismissing it.
3. **An unflagged result is reported as "no exceedance was detected at this resolution", never as "the bound
   holds".** `PROTOCOL.md` 9.3 already says this and `v2` keeps it verbatim.
4. **Do not convert the absence of a flag into a bound on the true rate**, and do not convert a flag into a
   demonstrated violation.
5. **Positive-control sensitivity does not validate the whole apparatus.** The `v1` control **PASSED** and that
   verdict stands and is preserved; what it establishes is that the apparatus detects a violation *of that size, on
   that gate, in those cells*. It does not audit truth construction, event completeness, or the implemented primary
   object - and section 1.2 has now shown event completeness to have been defective while the control was passing.
6. **Multiple inspected flags are not a simultaneous Monte Carlo theorem.** Each interval is marginal.

### 6.4 One consequence for `v1`'s own numbers, stated where it belongs

The positive control could not have been broken by the event-schedule defect, and this needs no recomputation: the
reduced look set is a **subset** of the all-triggers set, ever-miscoverage is a **union** over looks, `N` is the
trial count and does not change, and the Wilson lower limit is increasing in `x` at fixed `N`. A row flagged under
the reduction is flagged under any superset of it, so **the defect can only ever make the positive control fire
harder**. The direction that could have mattered is the reverse one - rows reported as *unflagged* - and that is
exactly the list in `LASTLOOK_CHECK.md` section 4. Across the whole grid, over every cell, construction and
nominal-bearing quantity, **no Wilson flag changes state under any of the three schedules**.

---

## 7. Planning quantities: every term carries its convention, and terms of different conventions are never combined

This section is binding wording for `v2`, for `REPORT.md`, and for any document that cites these numbers. Each value
below was **recomputed here** against the pinned `src/winstats.py` before being written down; section 10 gives the
command.

### 7.1 The four conventions, named

| convention | what a number of this kind is | what it is **not** |
|---|---|---|
| **deterministic path** | the `n` at which a stated quantity crosses a stated threshold along **one** stipulated outcome path or one stipulated fixed-count substitution | a probability, a power level, an expected stopping time, or a statement about other paths |
| **powered** | an `n` derived with an explicit power target and an explicit error level | a path calculation, and never comparable with one |
| **oracle / upper bound** | a bound derived from an information inequality, attained by no exhibited procedure | an attainable maximum |
| **observed** | a quantity measured on realized data | a property of the law that generated it |

### 7.2 The values, each with its convention attached

**`17,097` - DETERMINISTIC PATH.** The first integer `n` at which the normal-mixture radius falls below `delta`:
`r(17,097) = 0.029999847357` and `r(17,096) = 0.030000672819`, at `alpha = .00625`, `rho = 100`, `V_n = n`.
Reproduced here exactly. It involves **no distribution over outcomes and no power level**: it is the `n` at which the
band is narrow enough **assuming the observed difference stays exactly zero**. A true zero mean does not force every
realized mean to zero, so this is **not** a sufficient powered horizon and **not** a guarantee over all outcomes.

**`6,697` - DETERMINISTIC PATH.** The first integer `n` at which the fixed 40-stake ternary mixture
`betting_log_e_ternary(n*q, n*q, n, threshold = -0.03, bets = 40)` exceeds `log(1/0.00625) = 5.075173815234`, with
`q = p(1-p) = 0.195870946315` from the illustrative independent-task plug-in law at the pilot success rate
`p = 433/591 = 0.732656514382`. Reproduced here exactly. It is evaluated on **fractional expected pilot counts under
ONE illustrative law**. It is **neither demonstrated 80% power nor an expected stopping time nor the expectation of
log mixture wealth**, and the exact recovery of the value does not prove which calculation produced it originally.

**`3,100` - POWERED (and an ORACLE bound).** With the reported `D(P||Q) = 0.001149011`, `alpha = .00625`, an
admissible i.i.d. joint-law model and an **80% power target**, binary-KL data processing gives
`kl(0.8 || 0.00625) = 3.560990551252` and a necessary real-valued horizon `3099.178817`, hence **at least 3,100
integer pairs**. Reproduced here exactly. Inverting the same inequality gives **upper bounds** on power:
`0.235108980920` at `n = 568` and `0.148516462122` at `n = 295`. These are **upper bounds, not demonstrated
attainable maxima**, and the bound may not be used at all until the exact null and alternative laws, the KL
orientation, the error allocation, the target power, **the information available to the procedure**, and the sampling
law are delivered: a score-marginal KL does not automatically bound a procedure that observes task identities, both
outcomes, delays or traces, and a fixed roster paired **without replacement** does not automatically carry the
product-law information `nD`.

### 7.3 What may and may not be combined

**Permitted, because it compares like with like:** `17,097` against `6,697`. Both are deterministic path
calculations under the same convention, so their ratio **`2.552934149619`** is meaningful as a comparison of two
path benchmarks - and it must be labelled as exactly that, a ratio of two deterministic path crossings, never as a
power ratio and never as a claim about the published method.

**Forbidden:** dividing `17,097` by `3,099`, or forming any percentage share from terms of different conventions.
**The percentage apportionment - "estimator `27.5%`, anytime-validity price `22.6%`, genuine no-difference `49.8%`" -
is WITHDRAWN and must not reappear**, in this document, in `REPORT.md`, in `COORDINATOR_DECISIONS.md`, in the paper,
or anywhere else (coordinator revision 14 ruling 64; root disposition section D). The middle term in particular was
offered as an irreducible price of anytime validity and is not one: it compares a planning crossing of a particular
mixture against an information lower bound at 80% power, grid choice and mixture penalty and non-attainment of the
bound can all contribute, and - decisively - a fixed-horizon test that can reject only at its horizon is itself
anytime valid, so **no universal positive monitoring penalty follows merely from demanding anytime validity**.

### 7.4 Four further statements that do not follow, and are not to be made

1. **Equal observed pilot success counts do not establish equal true success probabilities.** "The nulls are real"
   does not follow from a power upper bound: failure to certify non-inferiority is not evidence of equality.
2. **A necessary 80%-power horizon is not an expected stopping time and not a sufficient horizon.**
3. **"Best valid" requires an optimality result that does not exist here.** Write "this specified construction" or
   "best among the evaluated constructions".
4. **Historical retrospective RETAIN calculations are not prospective decisions made during collection.**

**None of the quantities in this section enters the paper as established evidence.** The reported drift
miscoverage, the generic hedged-capital diagnostics and the numeric success probabilities lack deposited inputs,
code and outputs; if they are retained, their exact calculations must be supplied, and no new broad grid is to be
launched to rescue them. The predictable-range normal-mixture proof with `V_n = n` stands as it is; an
empirical-variance substitution needs its own valid argument, and its absence does not invalidate every
variance-adaptive method.

---

## 8. The optional secondary is descriptive sensitivity FIRST, and is not promoted here

Root disposition section E. The fixed positive-stake lower-wealth domination argument is **sound** under the stated
bounded-support and enclosure assumptions, and no mathematical defect was found in it. **Its implementation and
inferential specifications remain incomplete**, and this amendment does not promote it.

`v2`'s position, which is the root's current choice and not a placeholder: **an optional exploratory lower-wealth
curve at the existing primary looks, with no extra deployment trigger and no jointly calibrated secondary claim.**
It is descriptive sensitivity. It is **not** a prerequisite for the agreed live study and **not** a reason to
enlarge its sample.

Before it may be used prospectively at all, these must be frozen and are not: its threshold, its stake grid, its
fixed nonnegative weights, its clipping and valid input support, the endpoint-product calculation, and the rule for
recomputing old factors when enclosures improve - the ternary-count function is appropriate only when the substituted
endpoints are ternary, and general real endpoints need the corresponding factor product. The exact current
enrollment-prefix target and the legal looks must be stated: monotonicity holds for improving enclosures **at a fixed
prefix**, not for an increasing prefix, so an old crossing cannot certify a new drifting target, and the argument
establishes **threshold validity, not a calendar-time e-process**. A secondary alpha and its across-trial and
reporting family must be specified: saying it has "no claim on the primary alpha" specifies neither its own error
control nor joint primary-plus-secondary control, and a guardrail-only result is not by itself a guarded deployment
decision. It uses the **current** enrolled prefix, never a retained past crossing under drift, and its pilot- and
CPU-driven development is disclosed.

A later formal secondary needs its own explicit alpha and family accounting and its own review. **Until then it is
reported as descriptive and is not promoted.**

---

## 9. The run gate: what `v2` may do now, and what it may not

**`v2` MAY NOT RUN THE GRID.** The root requires deterministic and specification review **before** any re-run, and
**explicit clearance** for a corrected replay. That clearance has not been given and this document does not assume
it.

| activity | status |
|---|---|
| deterministic fixtures, including the root's witness as a regression | **permitted now** |
| the witness and boundary witnesses | **permitted now** |
| the balanced **20-program** resource check of section 9.1 | **permitted, and DELIVERED**: `RESOURCE_CHECK.md` |
| the `v2` stochastic grid, at any tier or horizon | **BLOCKED** pending explicit clearance |
| a corrected replay of the original seed coordinates | **BLOCKED** pending explicit clearance; and when cleared, reported as a **paired comparison after development**, not fresh independent calibration |
| any new cell, larger horizon, model change, model call, network access or new dependency | **not requested and not permitted** |
| live trial episodes | **BLOCKED**; the prior review's host, ledger and freeze gaps also remain prerequisites |

### 9.1 The balanced 20-program resource check replaces the confounded smoke

`v1`'s smoke split ten programs into `C1` at horizon 2,000 and ten into `C2` at horizon 1,000, and estimated a
horizon exponent from their ratio. **That ratio confounds cell with horizon**: it absorbs the `N -> A` delay branch
as well as the horizon, which `PREREG_CHECK_2` raised against `PROTOCOL.md` section 8.1 and which section 8.1 still
reads as it did. The measured `beta = 0.617648` is therefore not an identified horizon exponent.

`v2`'s check is the balanced design the root already specified: **`C1` and `C2` x horizons 1,000 and 2,000, five
programs per group, 20 programs total**, with **separate recorded resource-only coordinates**. It is a **bounded
resource check run after code and specification review**. It does **not** license outcome-based tier changes, and it
does not license repeated timing until a preferred tier appears: the tier rule is effect-independent, fixed before
the check, and the final run manifest must identify the **executable committed bytes** and that rule.

**This check has been delivered.** It is `experiments/live_ab_validation/RESOURCE_CHECK.md`, with
`vresource_check.py` and receipts under `results/live_ab_validation_v2/resource_check/`; it is a **sibling
session's** measurement in this workflow, not this document's, and it is cited here rather than restated. Its
headline results are that the corrected all-look schedule does **not** cost materially more - a paired factor of
**x0.943, 95% CI [0.938, 0.949]** under the batched declaration of section 1.2 and **x1.911, 95% CI [1.880, 1.943]**
under the finest - that the cell effect is **not separable from zero** (`+0.0093 +- 0.0057` in log seconds per
program) while the horizon effect is large and precise (`+0.4053 +- 0.0054`), and that **no cap is breached at any
tier for any of the three schedules**. Two boundaries on reading it, which that file states and this one adopts:
twenty programs plus fixtures is **not** a grid and is **not** clearance for one; and the confounded `v1` `beta` was
a real **measurement** defect that turned out not to be a **decision** defect, because `T1`'s projection is
`s_2000 * programs * (2000/2000)**beta`, in which `beta` does not appear.

**Consequence for section 1.2's open choice.** The batched reading is the cheaper one as well as the primary one, so
the recommendation there is **not** a cost-driven choice and does not become one. If the coordinator rules for the
finest reading instead, that file reports it at about double the cost and still at roughly 3% of the runtime cap, so
**cost does not constrain that ruling in either direction** and the ruling should be made on the meaning of "each
further fact", not on seconds. Those projections are that file's measurements and are not re-derived here.

### 9.2 Receipt chronology is preserved, not rewritten

`v1`'s manifest records runtime commit `02b94103bb9798c906967b27031ba6b38b94eb74`, which **precedes** the commit of
the runner files; the per-file hashes identify the delivered runnable bytes but do **not** provide a committed
executable pre-run anchor. That is the actual chronology and `v2` preserves it rather than tidying it. The older
decision-only timing note and the later smoke receipts differ; **both attempts are retained and identified**, and
neither is rewritten as the other. One unexplained flaky full-suite failure was reported at 474 tests and did not
recur in six subsequent runs; it overlapped a sibling session's writes, it is recorded rather than omitted, and it
is **NOT closed**.

### 9.3 The `v2` freeze checklist

`v2` is frozen only when every line below is discharged in writing, and not before:

1. Section 4.1's rule-block review, key by key, with the reviewed block's hash recorded.
2. Section 4.2's matched pins: `protocol_FINAL.md` re-pinned, `pinned/` re-snapshotted, the `#11` commit recorded,
   the `v1` pin stated beside it as superseded.
3. Section 1.2's event schedule declared in the runner and asserted by fixtures, with the root's witness as a
   regression case and both readings computed.
4. Section 1.3's two decision quantities recorded separately.
5. Section 5's horizon rule in place of every bare horizon number.
6. Section 6's Monte Carlo wording applied everywhere, including `REPORT.md`'s errata.
7. Section 7's convention labels on every planning quantity, and the withdrawn apportionment absent.
8. Section 8's secondary left descriptive.
9. Section 9.1's balanced resource check run and recorded, with its effect-independent tier rule. **Discharged**
   by `RESOURCE_CHECK.md`, subject to the coordinator accepting it.
10. `v1` preserved byte-identical, reported beside `v2`, and its errata pointer in place. **Discharged** by
    `REPORT.md` section 16, subject to the same acceptance.
11. All three test and fixture counts re-taken on a **quiescent** tree, with quiescence recorded (section 10).

---

## 10. What was executed while writing this document

CPU only. No model call, no API call, no network, no download, no new dependency. **No `v2` grid, no re-run of the
`v1` grid, no stochastic simulation of any kind, and no Git state changed.**

| what | result |
|---|---|
| `.venv/bin/python experiments/live_ab_validation/tests_validation.py`, run **three** times across this work | **88** tests in 4.531 s, then **106** in 6.028 s, then **107** - **0 failures, 0 errors, 0 skipped** every time |
| `.venv/bin/python experiments/live_ab_validation/vfixtures.py`, run three times | **18/18 fixtures passed**, `F01`-`F18`, including `F15` and `F18`, all three times |
| `.venv/bin/python -m unittest discover -s experiments/live_ab -p "tests_lab_*.py"` | **474 tests, OK**, in 243.195 s, on a tree where `experiments/live_ab/` was clean at `db930d7` |
| `git status --porcelain results/live_ab_validation/` after every edit | **empty** - no `v1` result was modified, and section 3 item 1 holds |

> **Why the `#12` count moved, recorded rather than reconciled to one number.** A sibling agent in this same
> workflow owns `vrun.py`, `vgen.py` and the event-schedule work of section 1.2, and was adding tests to
> `tests_validation.py` **while this document was being written**: 88, then 106, then 107, in the time it took to
> write it. **The tree was not quiescent, so the `#12` count is a moving target and not a baseline**, and this
> document will not pick one of the three and call it the answer.
>
> Coordinator ruling 62(b) named this exact failure once already - a `#11` "461 passing" baseline that did not
> reproduce, for the same reason - and its remedy is the one applied here: **a baseline count must be taken on a
> quiescent tree or not quoted at all.** All three measurements are printed. **0 failures at all three**, which is
> the part that does not depend on the count, and **18/18 fixtures at all three**, which does not move either. The
> `v2` freeze must re-take every count on a quiescent tree and **record that it was quiescent**; freeze-checklist
> item 11 exists for that.
| Wilson flag thresholds, from the frozen rule | `64` at `N = 8,000` (`1.280x`), `147` at `N = 20,000` (`1.176x`); intervals in section 6.1 |
| binomial tail probabilities, `scipy.stats.binom.sf` | the four rows of section 6.2, including `P(X >= 64 | 8,000, .007) = 0.1571523834` |
| `winstats.normal_mixture_radius` sweep to `n = 30,000` | first `n` with `r(n) < 0.03` is **17,097**; `r(568) = 0.157951512494`, `r(565) = 0.158403632559`, `r(295) = 0.228706942335` |
| `winstats.betting_log_e_ternary` sweep to `n = 30,000` | first crossing of `log(1/alpha)` at **6,697**, at `q = 0.195870946315` |
| binary-KL inversion | `kl(.8 || .00625) = 3.560990551252`, necessary `n = 3099.178817` -> **3,100**; power upper bounds `0.235108980920` at 568 and `0.148516462122` at 295 |
| `lab_common.rule_block_sha256(config)` | `cbfd1792d09c43754eeeab3b282e92e99c76e4f878cd82d00c827f6a90fa7607` |
| `shasum -a 256` on the three pinned monitor sources and their live counterparts | the mismatch table of section 4.2; `experiments/live_ab/` is clean at `db930d7` |
| horizon-rule enumeration over all 28 allocations of the six smoke exclusions | `N_P` in `{565, 566}` under both the two-stratum and the three-group rule; the documented allocation gives **565** under both |

**Files this amendment writes:** this file, and `experiments/live_ab_validation/REPORT.md` (its errata section 16,
its banner, and the nine sentences that section 16 records with before/after text). **No frozen value, no `v1`
measured number, no deposited `v1` result, no `PROTOCOL.md` clause, no `cells.json` entry, no `#11` source, no
sibling-owned module and no Git state was touched.** `RESOURCE_CHECK.md`, `vresource_check.py`, `vrun.py`,
`vgen.py` and `tests_validation.py` belong to a sibling session in this workflow and are cited, never edited.
