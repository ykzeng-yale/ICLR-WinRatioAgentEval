# PREREG_CHECK: adversarial audit of the #12 pre-registration, before the protocol commit

Adversarial checker, session `session60/live-ab-validation`, 2026-09-19. Repository state
`de31b6cf124b3723eb9986a03318f1ae4f935353`. Scope: (A) the independence claim behind
`vband.py` / `vfixtures.py`, (B) `PROTOCOL.md` against the root's frozen acceptance design,
(C) the quiescence gate `experiments/live_ab/lab_hostcheck.py`.

This checker is **not** bound by the independence constraint and read the #11 monitor in full,
which is what makes section (A) possible. Everything asserted below as "verified" was executed;
commands and their true output are named at the point of use. No git state was changed.

| section | verdict |
|---|---|
| **A. Independence of `vband.py` / `vfixtures.py`** | **READY** (no evidence of breach; the limits of this verdict are stated in A.5) |
| **B. `PROTOCOL.md` vs the root's frozen acceptance design** | **FIX-FIRST** — 6 blocking items before the freeze commit |
| **C. Quiescence gate `lab_hostcheck.py`** | **BLOCK** — the gate is wired to nothing and has a silent fail-open path |

---

## What was executed

| command | true result |
|---|---|
| `.venv/bin/python experiments/live_ab_validation/vfixtures.py` | `13/13 fixtures passed` (F01…F13) |
| `.venv/bin/python experiments/live_ab_validation/tests_validation.py` | `ran=35 failures=0 errors=0 skipped=0`, 0.72 s, peak RSS 58.5 MB |
| `.venv/bin/python experiments/live_ab/tests_lab_hostcheck.py` | `Ran 42 tests … OK` |
| independent recomputation of `LOCKED_RADII` from `sqrt((n+100)*log((n+100)/(100*0.00625**2)))/n` | all 8 values reproduce bit-for-bit |
| `literal_radius` vs `winstats.normal_mixture_radius` over `n = 1…20 000` | max relative difference **`0.0`** |
| independent recomputation of every number in PROTOCOL §6.1 (32 values) | **all 32 reproduce exactly** |
| differential band comparison, 4 000 random enrollment ledgers, `n ∈ [1, 600]` | `max |L_v − L_11| = 0.0`, `max |U_v − U_11| = 0.0` |
| differential decision comparison, 500 programs, `n ∈ [95, 350]` | `decision comparisons=500 mismatches=0` |
| replay of the commit-`5776877` incident through `preflight_host_quiescent` | 2 findings, `clean=False`, raises |
| `preflight_host_quiescent` with `lsof` raising `OSError` | **PASSED — no exception** (see C2) |
| renamed non-python GPU binary through `enumerate_foreign_consumers` | `findings: 0 degraded: [] clean: True` (see C3) |

The two differential results are this checker's own probe, not a substitute for the frozen
200-stream comparison of PROTOCOL §12.2. They are reported here because §12.3 item 6 is right:
agreement between two implementations of the same misreading proves nothing, and agreement found
by an auditor proves less still.

---

## A. Independence — verdict READY

### A.1 The declared source list

`vband.py` lines 8–26 declare what was read and what was not:

> Read (the only sources used):
>   * reviews/arxiv_live_design_guidance.md   -- the design/formula document
>   * src/winstats.py                         -- the pinned primitives
>
> Deliberately NOT read, opened, grepped or imported (independence constraint):
>   * experiments/live_ab/lab_monitor.py
>   * experiments/live_ab/lab_enclosure.py
>   * experiments/live_ab/lab_reference_rule.py

`vfixtures.py` lines 4–11 carry the same declaration. A declaration is not evidence. What
follows is.

### A.2 Mechanical overlap: essentially none

Automated comparison of `{vband.py, vfixtures.py}` against `{lab_monitor.py, lab_enclosure.py}`:

- **Shared string literals of ≥12 characters: zero.** Not one error message, docstring fragment
  or label is common to the two sides. The #11 code is dense with quotable strings
  (`"pair {pair} enrolled out of order at prefix {self.n}"`, `"the clip is frozen at [-1.0, 1.0]"`,
  `"enclosure endpoints must be real numbers, not bool"`); none appears in #12.
- **Shared class names: `Band`, `Enclosure`.** Both are vocabulary of the task text
  ("Unresolved pairs contribute an **enclosure** that starts at [-1,1]") and of guidance item 3
  ("two-sided **bands**"). Neither is a distinctive choice.
- **Shared function names: `band`, `decide`, `enroll`, `full`, `contains`, `pending`, `replay`,
  `__init__`, `__post_init__`.** All generic; `decide`, `enroll` and `band` are forced by the
  guidance's own nouns.

### A.3 #11's distinctive vocabulary is entirely absent from #12

Grep of `vband.py` and `vfixtures.py` for every identifier that a copier would have carried
across returns **no hit** for any of:

`latency_s`, `collapsed`, `PairEnclosure`, `EpisodeView`, `narrows_to`, `is_point`,
`assert_monotone`, `certified_elapsed`, `tiers_from_config`, `CERTIFICATE_EPS`, `TIER_NAMES`,
`ARMS`, `RULE_ID` / `nm_guarded_v3`, `EXPLORATORY_MARGINS`, `decision_order`, `MonitorConfig`,
`MonitorState`, `FrozenMismatch`, `MonitorError`, `_completed_prefix`, `s1_restricted`.

The only occurrences of the string `live_ab/` in either file are inside the "NOT read" lists.

### A.4 Six places where the two implementations visibly disagree in approach

These are the positive evidence. A paraphrase does not invent divergences; it inherits them.

1. **Cost tier identity.** #12 writes `Tier("cost", higher_better=False, relative_tolerance=0.05)`
   — verbatim from guidance item 5. #11 binds the tier to a concrete field:
   `TIER_NAMES = ("success", "latency_s")` with `{"name": "cost", "field": "latency_s"}`.
   A reader of `lab_enclosure.py` would almost certainly have carried `latency_s` over.
2. **Band signature.** #12: `normal_mixture_band(lowers, uppers, n, alpha_gate, rho, name)` taking
   the *sequences* and slicing the prefix itself, returning
   `Band(name, n, sum_lower, sum_upper, mean_lower, mean_upper, radius, lower, upper)`.
   #11: `band(n, s_lower, s_upper, mc)` taking *precomputed sums* and a config object, returning
   `Band(n, radius, s_lower, s_upper, lo, hi)`. Different decomposition, different field names
   (`lower`/`upper` vs `lo`/`hi`), different ownership of the summation.
3. **Behaviour at `n = 0`.** #12 returns `Band(n=0, radius=math.inf, lower=-1, upper=+1)`. #11
   raises: `raise MonitorError("band() requires n >= 1; at n == 0 the full range is displayed")`.
4. **Clipping.** #12: `min(max(s_lo / n - r, SCORE_LOW), SCORE_HIGH)` — a two-sided clamp. #11:
   `lo = max(mc.clip_lo, s_lower / n - r)` — one-sided. Numerically equivalent, structurally not.
5. **Decision order.** #12's `decide` tests DEPLOY first, then RETAIN. #11 freezes the opposite
   and enforces it in config: `monitor.decision_order is frozen at [harm_keep_incumbent,
   deploy_candidate]`. (Both are correct, since `L_h ≤ U_h` makes the branches disjoint — but a
   copier would have copied the frozen order.)
6. **A genuine semantic disagreement about collapse.** `vband.Enclosure` docstring:

   > A degenerate interval reached by enumeration is logically just as tight but is deliberately
   > NOT marked certified.

   `lab_enclosure.PairEnclosure` requires the opposite and raises otherwise:
   `EnclosureError("collapsed must be true exactly when both scores are points")`. This checker
   hit that exception while constructing the differential test. The two sides hold *incompatible*
   definitions of the same flag. A copier does not introduce a contradiction with the source.

Further: #12 has no horizon concept at all (`n_max`, `horizon_no_decision`, `_all_collapsed` are
#11-only), and #11's monitor carries read-outs #12 has never heard of (`EXPLORATORY_MARGINS`,
`readouts.completed_prefix`, `readouts.s1_restricted`).

### A.5 Confidence, and what this verdict cannot mean

**Stated plainly: I find no evidence that the constraint was broken, and several affirmative
signs that it was not.** Confidence that `lab_monitor.py` / `lab_enclosure.py` were not read:
**moderately high**, not certain.

What this audit **cannot** distinguish, and nobody should claim it can:

- The two authors are sessions of the same model. Shared priors produce convergent choices with no
  contact at all. Both reached for `math.fsum` over `sum` (a non-obvious numerics choice), both
  chose `1e-9`-scale epsilons, both used "narrow / collapse / certificate" language — every one of
  which is explainable by guidance item 5's own wording ("enumerate feasible completions to narrow
  them, and collapse only with a valid final-score certificate") plus a shared prior. Convergence
  here is **not** evidence of breach, and its absence would not have been evidence of compliance.
- Nothing in the artifact record proves the *order* of reading. Both `.py` files and the protocol
  are untracked at the time of this audit (`git status`: `?? experiments/live_ab_validation/`), so
  there is no commit chronology to inspect.
- A verdict of READY on procedural independence is a statement about the code, not about the
  session. The protocol's own §12.1 disclosure — "procedural, not organizational … sessions of the
  same model directed by the same coordinator" — remains the honest framing and must stay in.

No finding in this section requires a change before the commit.

---

## B. PROTOCOL.md against the root's frozen acceptance design — verdict FIX-FIRST

### B.0 Item-by-item conformance

| root item | status | passage |
|---|---|---|
| **1** deterministic fixtures, independent recomputation, containment | **partly** | §11 table `F0…F12`; F11 states "each pair's ultimately resolved score lies inside **every** bound that pair contributed at **every** prior look". Three defects: **B2, B3, B4** |
| **2** protocol commit before any outcome; exact adapter/parameters/seeds/cells/errors/budget; positive direction; bounded-running-mean vs causal boundary distinguished | **partly** | §2.1 parameter table; §5 seeding; §10 boundary ("A simulation assumes them; it cannot supply them"). Defects: **B1, B10** |
| **3** eight cells, four laws × two delays, ground truth exact or enumerated, delays specified before drawing, no cell added after inspection, explicit cap rule | **fully** (arithmetic verified) | §4.1 six-atom table; §4.2 delay rules; §7.3 drain rule; §4 "No ninth cell exists and none may be added." Ground truth verified independently: all `mu_h`, `mu_s`, `p_long`, `E[d]`, `P(Z)`, `P(D)` and all 32 §6.1 values reproduce exactly |
| **4** 2 000 programs × 4 trials × ≤2 000 pairs; summaries at 100/500/2 000; escalation to 5 000 precommitted; reduced grid reported before execution; smoke measures runtime/RAM only, seeds discarded | **partly** | §7.1, §7.2, §8.1, §8.2. Defects: **B7, B8, B11** |
| **5** three constructions; prefixes refer to their own targets; no pathwise speed dominance | **fully** | §3: "**`CPREFIX` refers to its own running target** … It is not a bound on the current all-enrolled mean `mubar_n`"; "**No pathwise dominance of any construction over any other is claimed**, in either direction"; `NAIVE` labelled invalid in every table |
| **6** per-gate simultaneous ever-miscoverage, trial/family error definitions, Wilson intervals, no-decision fraction, capped decision time, unresolved fraction, compute counts, same-look conjunction, retain unfavourable, A/A is not calibration | **fully**, one contradiction | §9.1–§9.6 with exact estimators and an explicit Wilson formula; `never_conjunct` is a real read-out; §13.4 retention. Defect: **B9** |
| **deliverables** frozen protocol, DGP + ground truth, immutable hashes, one command writing only its own directory, tables/manifests/fixtures, report naming the validated adapter commit, smoke seconds/RAM/projection before full execution | **partly** | §13.1–§13.3. Three pinned hashes independently verified correct. Defects: **B5, B6, B12** |

The three pinned SHA-256 values in the header table were recomputed and all three match:
`src/winstats.py` `56955ce0…`, `reviews/arxiv_live_design_guidance.md` `a7196598…`,
`experiments/live_ab/design/protocol_FINAL.md` `03028374…`.

### B.1 — SEVERITY HIGH. §2.2 states a falsehood about the shipped code.

§2.2, "Independence rule":

> The #12 band module implements this closed form **directly from the guidance text**, in its own
> code. **It does not call `src/winstats.normal_mixture_radius` to produce any reported number.**

`vband.py` does exactly that. `radius_from_formula` (line 505) is
`return float(normal_mixture_radius(int(n), alpha=alpha_gate, rho=rho, variance_process=int(n)))`,
and `normal_mixture_band` — the function that produces every reported `L` and `U` — calls it. The
hand-written closed form (`literal_radius`) lives only in `vfixtures.py` and is used only as a
cross-check. So **every reported number does come from `winstats`**.

**Required change:** either (a) rewrite §2.2 to say that the band module calls the pinned
primitive and that `vfixtures.literal_radius` is an independent second transcription used to
cross-check it, or (b) move `literal_radius` into `vband.py` and make it the production path. (a)
is the honest and cheaper fix, and is also defensible — the guidance itself names
`normal_mixture_radius` as the pinned primitive to use. Do not leave the sentence as written.

### B.2 — SEVERITY HIGH. The fixture register does not match the fixtures.

`PROTOCOL.md` §11 and `cells.json` both enumerate **`F0 … F12`**. The code implements
**`F01 … F13`**. Tail mapping diverges:

| id | PROTOCOL.md / cells.json | vfixtures.py |
|---|---|---|
| `F0` | radius closed form, `n = 1…20 000`, rel. diff `0` | *(no such id)* |
| `F12` | **protocol/config agreement**: every numeric value in PROTOCOL that also appears in `cells.json` is equal to it | `F12_band_formula` |
| `F13` | *(no such id)* | `F13_decision_rule` |

Consequences: `fixtures_report.json` is specified (§13.2) to carry "per-case pass/fail for
`F0 … F12`", which the code cannot produce; and the header table's claim about `cells.json` —

> machine-readable twin … normative for every numeric value; this document and that file must
> agree, **and a fixture asserts it**

— is **false**. Grep of `vfixtures.py` and `tests_validation.py` for `cells.json` returns nothing.
`cells.json` is currently normative by assertion only.

**Required change:** renumber the code to `F0…F12`, *and* implement the protocol/config agreement
fixture (parse the PROTOCOL tables, compare against `cells.json`, fail on any mismatch), *and*
give the two currently unlisted code fixtures (`band_formula`, `decision_rule`) their own ids in
both PROTOCOL §11 and `cells.json`. A protocol whose own consistency check does not exist is not
frozen in the sense root item 2 asks for.

### B.3 — SEVERITY HIGH. The import-graph test does not exist.

§12.1 item 4 and `cells.json` `comparison_to_live_ab.import_graph_test`:

> A test asserts the import graph: no module reachable from the #12 band, enclosure, generator or
> fixtures imports anything under `experiments/live_ab/` or
> `experiments/live_ab_validation/pinned/`.

No such test is present in `tests_validation.py`. This is the **only mechanical enforcement** of
the independence constraint that the design proposes; without it, independence rests entirely on
the docstring declarations audited in section A.

**Required change:** implement it before the freeze. Minimum form: import each #12 module in a
fresh interpreter, then assert that no entry of `sys.modules` has a `__file__` under
`experiments/live_ab/` or `…/pinned/`. Add it to the §11 register with an id.

### B.4 — SEVERITY MEDIUM. F0's stated range is not the range that is checked.

§11 `F0` and §2.2 claim the agreement holds "for `n = 1..20,000` at relative difference `0`" and
that "the fixture re-checks it at run time". The code checks **eight** values
(`LOCKED_RADII` keys `{1,2,3,4,6,100,500,2000}`) at tolerance `_REL = _ABS = 1e-12`, and
`tests_validation.py` checks seven values at 12 decimal places. Neither is `1…20 000`, and neither
is "relative difference 0".

The claim itself is **true** — this checker ran the full sweep and measured a maximum relative
difference of exactly `0.0` over `n = 1…20 000` — but nothing in the repository establishes it.

**Required change:** make `F0` sweep `n = 1…20 000` with a strict `==` on the float, or weaken
§2.2 and §11 to state the eight-point check at `1e-12` that is actually performed. Do not ship a
claim the fixture does not make.

### B.5 — SEVERITY HIGH. The comparison step leaves the disagreement verdict to later judgement.

§12.2 compares "decision label — **exactly** equal". The two sides do not share a label alphabet:

- #11 `decide` returns `None` or `Decision(kind ∈ {"deploy_candidate", "harm_keep_incumbent",
  "horizon_no_decision"})`.
- #12 `decide` returns `{"DEPLOY", "RETAIN_INCUMBENT", "CONTINUE"}`, and `NO_DECISION` exists only
  as a trial endpoint in the protocol, not in `vband`.

Three further gaps the protocol does not close:

1. **No mapping is frozen.** `horizon_no_decision` has no #12 counterpart; #12 has no `n_max` at
   all, so the #11 horizon branch (`n >= mc.n_max and state._all_collapsed()`) is unreachable from
   the #12 side. Whoever writes `compare_to_live_ab.py` will choose the mapping — after seeing the
   streams. That is precisely what §12.3 forbids.
2. **No rule for a raised exception.** #11 raises where #12 returns: `band()` raises `MonitorError`
   at `n = 0` where #12 returns `[-1, +1]`; `PairEnclosure` raises `EnclosureError` on a
   point-valued non-`collapsed` enclosure, which #12 produces by design (A.4 item 6). The protocol
   does not say whether an exception on one side is a disagreement, a skip, or a defect.
3. **"per-pair enclosure endpoints" compares endpoints only**, so the `certified` / `collapsed`
   contradiction of A.4 item 6 is invisible to the comparison even though it is a real
   disagreement between the two readings of guidance item 5.

**Required change:** freeze, in §12.2, (i) the exact label bijection including the `n = 0` and
horizon cases, (ii) "an exception raised by either side at a look where the other returns a value
is a disagreement and is written to `comparison_defects.csv`", and (iii) whether the
`certified`/`collapsed` flag is in or out of scope, with the reason.

### B.6 — SEVERITY HIGH. The eight cells never exercise the cost/latency enclosure path.

§4.3 models a pair as *unrevealed → one episode revealed → both revealed*, and §2.5's enclosure
table narrows on **success only**. Nothing in the grid ever narrows an enclosure from a *pending*
episode's partial cost information.

The #11 monitor does exactly that. `lab_enclosure.py` carries a cost certificate —

> protocol 7.5 item 5 / config 'enclosure.cost_certificate': `(1 - tol) * ell > L_r + 1e-9`.
> `CERTIFICATE_EPS: float = 1e-9`

— with `certified_elapsed`, an `ell` lower bound and a `tokens_known` field on every
`EpisodeView`. That path will be live in the real trial and is validated by **no cell in this
study**. (`vband` has the matching machinery — `Episode.with_elapsed_cost`, `with_cost_upper`,
`cost_order_possibilities` — exercised by fixtures F06/F07/F09 but by nothing in the grid.)

Because §4 forbids adding a cell after outcomes exist, this must be settled now.

**Required change:** either add the pending-cost narrowing mechanism to §4.3 and the §2.5 table
**before** the freeze, or add it verbatim to §1.3 as a declared gap, in the same register as §1.3
item 3: *"the cost-certificate narrowing path of the #11 enclosure (`(1-tol)*ell > L_r + 1e-9`) is
not exercised by any cell of this study; the comparison of §12 therefore does not test it."*
Silence is not an option — §1.3 is the section the report is required to repeat in full.

### B.7 — SEVERITY MEDIUM. The budget projection assumes a scaling exponent it cannot measure.

§8.1: `seconds_projected = (smoke_seconds / 20) * programs_total * (N_max_tier / 2000)` — linear
in `N_max`. One smoke run at a single `N_max = 2 000` cannot measure that exponent. Per-look cost
is `O(1)` only if the band is maintained incrementally (two enclosure changes per pair); a
recompute-the-sum-per-look implementation is `O(N_max²)` per trial, under which the T4 row
(`N_max = 1 000`) would be over-projected by a factor of 2 and the tier choice could be wrong.

**Required change:** either add a second smoke point at `N_max = 1 000` in the same 20-program
budget and fit the exponent from the two measurements, or state the linearity as a frozen
assumption in §8.1 together with the implementation property it depends on ("the band is
maintained incrementally; the per-look cost does not grow with `N_max`") and have a fixture assert
that property.

### B.8 — SEVERITY MEDIUM. Tier T4 defers frozen numbers and silently drops a root-required horizon.

`cells.json` T4 note: *"fixed-horizon summaries become 100/500/1000 and the analytic reachability
section is recomputed and redeposited before execution."*

Two problems. First, root item 4 names summaries "at 100, 500 and 2,000"; T4 forfeits the 2 000
horizon, which is a reduction of the root's design and must be labelled as one rather than as a
budget consequence. Second, "recomputed and redeposited before execution" means §6's tables are
*not* frozen for T4 — they are written after the smoke run. §14 exempts the tier choice from
change control, but it does not exempt §6's values.

**Required change:** compute and deposit the T4 variant of §6.1/§6.2/§6.3 **now**, in `cells.json`,
alongside the `N_max = 2 000` tables; and add one sentence to §8.2: *"T4 forfeits the `n = 2 000`
fixed-horizon summary required by root item 4; if T4 is selected, the report states this as a
reduction of the root's design."*

### B.9 — SEVERITY MEDIUM. §2.4 and §9.1 contradict each other on whether the path continues.

§2.4: "**First crossing ends the trial**". §9.1: "Coverage is measured over the **whole path**, not
only up to a decision, because the confidence-sequence guarantee is a statement for all `n`".

These cannot both be operational. §9.1's reading is the correct one for the ever-miscoverage
estimator, and it also changes the compute model: under §9.1 *every* trial runs to tick 2 200, so
runtime is roughly cell-independent and the §8.1 C1 smoke projection is sound. Under §2.4's reading
deciding trials are short, C1 (which never decides) is the slowest cell, and the projection is
conservative for a different reason.

**Required change:** rewrite §2.4 as *"the decision is the first crossing; the simulated path is
nevertheless carried to the finalization look so that the all-`n` coverage read-out of §9.1 can be
taken. Continuing past the decision is a bookkeeping device of this simulation and is not what the
live trial does."*

### B.10 — SEVERITY MEDIUM. Randomized runs already exist and are not disclosed in the protocol.

Root item 2 requires the protocol commit before **any** simulation outcome exists. `tests_validation.py`
already runs randomized programs — `TestRandomisedContainment` over many seeds, and
`TestLargeProgramSmoke.test_four_hundred_pairs` with `Program(seed=31337, n_pairs=400)` — and they
were run (35 tests, 0.72 s). The test module disclaims them:

> The randomised programs here are a correctness property test for the monitor. They are NOT the
> issue-#12 simulation grid and they establish no operating characteristic.

That disclaimer is in the right place and this checker judges the substance compliant: they use
`random.Random`, touch no namespace-0 `SeedSequence` stream, and report no rate. But **PROTOCOL.md
nowhere mentions them**, and a reader reconstructing the freeze from the protocol alone would
believe nothing had been run.

**Required change:** add a short §0.1 to PROTOCOL.md naming `tests_validation.py`'s randomized
property runs, stating that they used a different RNG and no namespace-0 seed, that no rate was
computed from them, and that they are not results of this study. Same for the two pre-freeze checks
already disclosed in §2.2 and §4.1 — keep those sentences, they are the correct pattern.

### B.11 — SEVERITY LOW. The smoke cell is unjustified.

§8.1 places the smoke run "in cell `C1`" with no reason given. Under the §9.1 reading (B.9) all
trials are full-length, so `C1` is not obviously the worst case, and the rule-`A` cells run a
different delay branch whose cost is unmeasured.

**Required change:** state why `C1` (one sentence), or split the 20 programs across one `N` and one
`A` cell and take the max.

### B.12 — SEVERITY LOW. §11's blanket claim overstates what the fixtures do.

§11: "**Every fixture independently recomputes the score intervals and the normal-mixture bands
from the formula in the guidance document**". In fact F01–F11 call `vband.normal_mixture_band`;
only radius values are cross-checked against `literal_radius`, at three points
(`LOCKED_RADII[4]`, `[3]`, `[6]`) plus the F12 sweep.

**Required change:** either route every fixture's expected band endpoints through `literal_radius`
and a hand-written `sum/n ± r` (this is cheap and is what root item 1 asks for), or weaken the
sentence to "every fixture's *expected radius* is cross-checked against an independent literal
transcription of the guidance formula".

### B.13 — SEVERITY LOW. Artifacts described in the present tense do not exist.

§13.1 presents `run_validation.py` and `compare_to_live_ab.py` as existing commands; §12.1 item 3
describes `pinned/PINNED.json`. None of the three is present. This is normal for a pre-registration
but the freeze commit must not read as a description of a built system.

**Required change:** one line in §13: *"as of the freeze commit, `run_validation.py`,
`compare_to_live_ab.py` and `pinned/` do not yet exist; this section specifies them."*

### B.14 — SEVERITY LOW. The two-sided level is assumed, not cited.

§9.1's entire error budget rests on `normal_mixture_radius(·, alpha)` delivering a **two-sided**
`1−alpha` confidence sequence. `winstats.py`'s docstring says "Two-sided normal-mixture CS for
scores in [-1,1]", which is an assertion in a source file, not a citation.

**Required change:** cite the `paper/theory.tex` proposition the two-sided level comes from, in
§2.2 or §9.1. If the level is per-tail rather than simultaneous, every nominal bound in §9 is off
by a factor of two and must be recomputed before the freeze.

---

## C. Quiescence gate `experiments/live_ab/lab_hostcheck.py` — verdict BLOCK

### C.1 Does it ever send a signal or otherwise interfere? — **No, to any discovered process.**

Verified three ways:

- Grep for `kill`, `signal`, `SIGTERM`, `SIGKILL`, `terminate`, `renice`, `nice`, `pkill`,
  `killpg`, `Popen` over the file: **no hit**. The only two matches are the two `subprocess.run`
  call sites.
- Those two sites are `PS_ARGV = ('ps', '-axo', 'pid=,ppid=,etime=,rss=,command=')` and
  `['lsof', '-n', '-P', '-p', …]`. Both read-only, both `capture_output=True`, both timeout-bounded.
  Discovered pids are used only as integers, for an `lsof -p` query and for the finding record.
- `tests_lab_hostcheck.py` enforces it: `test_the_signal_module_is_never_imported`,
  `test_no_banned_call_or_attribute_in_the_syntax_tree`,
  `test_the_only_external_programs_named_are_ps_and_lsof`. All 42 tests pass.

**One precise caveat the docstring should carry.** `subprocess.run(..., timeout=…)` kills *its own
child* on timeout: CPython's implementation calls `process.kill()` in the `TimeoutExpired` path.
So the module can send `SIGKILL` to the `ps` or `lsof` process **it spawned**, after
`PS_TIMEOUT_S = 20` / `LSOF_TIMEOUT_S = 30`. That is not interference with a process it found, and
the docstring's claim — "It never sends a control instruction of any kind to any process **it
finds**" — is literally correct. Adding "(the `ps`/`lsof` readers it starts are killed by the
standard-library timeout path; no discovered process is ever signalled)" removes the last
ambiguity. **Severity: informational.**

### C.2 — SEVERITY HIGH (BLOCKING). `lsof` failure is a silent fail-open.

The module's stated contract, from `ScanResult`:

> `degraded` is non-empty when the scan could not establish quiescence … An empty `findings` with a
> non-empty `degraded` means **NOT PROVEN, never PROVEN CLEAN**, and the preflight gate treats it
> accordingly.

`metal_context_pids` violates it:

```python
try:
    done = subprocess.run(argv, capture_output=True, timeout=timeout_s)
except (OSError, subprocess.SubprocessError):
    return set()
```

An absent `lsof`, a permission failure, or a 30-second timeout all return "no Metal holders", and
`enumerate_foreign_consumers` appends nothing to `degraded`. `done.returncode` is never inspected
either — unlike `read_process_table`, which does check it. **Verified by injection:** with `lsof`
raising `OSError` and a foreign python GPU process in the table,
`preflight_host_quiescent` **passed with no exception**, `degraded: []`, `clean: True`. Same result
with `lsof` exiting non-zero.

This is the fail-open case in the one arm of the gate that catches anything not on the name list.

**Required change:** `metal_context_pids` must report failure distinguishably (return
`set() | None`, or raise). `enumerate_foreign_consumers` must append
`'lsof-unavailable'` / `f'lsof-exit-{rc}'` / `'lsof-timeout'` to `result.degraded` whenever the
Metal probe could not run and `python_rows` was non-empty. Add a test that asserts
`preflight_host_quiescent` raises in that situation.

### C.3 — SEVERITY HIGH (BLOCKING). A renamed binary defeats the gate and is reported CLEAN.

`match_consumer` matches only exact basename tokens from `RUNNER_TOKENS`
(`llama-server`, `llama-cli`, `mlx_lm`, `ollama`, `vllm` and spelling variants). The Metal/`lsof`
fallback is applied **only to rows that pass `is_python_command`**:

```python
elif is_python_command(row.command):
    python_rows.append(row)
...
holders = metal_context_pids([r.pid for r in python_rows])
```

**Verified:** `cp llama-server srv; ./srv -m /x/m.gguf -ngl 99` →
`findings: 0 degraded: [] clean: True`. And a non-python pid that is *known* to hold Metal is still
ignored, because `metal_pids` is only intersected against `python_rows` —
`enumerate_foreign_consumers(…, metal_pids={778})` on a non-python row returned `0` findings.

So the gate proves absence of *named runners* and of *Metal-holding python*, and nothing else. It
reports that as `clean = True`, not as `degraded`.

**The limitation is stated nowhere.** Grep for `rename`, `false negative`, `limitation`,
`cannot detect`, `does not detect`, `blind` over `lab_hostcheck.py` and its tests returns nothing.
`match_consumer`'s docstring discusses only the false-*positive* direction
("A bare argument that happens to equal a runner name (`grep vllm README`) is still reported").

**Required change, pick one and state it either way:**
(a) run the `lsof` Metal probe over *every* non-allowlisted row above an RSS threshold rather than
over python rows only — with `MAX_LSOF_PIDS` raised and a `degraded` marker when the budget binds;
or (b) leave the scope as is and add to the module docstring and to the protocol's 5.7 language:
*"this gate establishes the absence of the named runners and of Metal-holding python interpreters.
A renamed or statically-linked accelerator binary is not detected and the scan will report
`clean`."* Option (b) without (a) means `protocol_FINAL.md` 5.7's "no other GPU job" is still not
enforced, and the protocol must say so.

### C.4 — SEVERITY HIGH (BLOCKING). Nothing calls the gate.

`grep -rn "hostcheck|preflight_host_quiescent|soft_host_check|HostNotQuiescent|foreign_load_detected"`
over `experiments/live_ab/`, excluding the module and its own tests, returns **one** hit: a prose
line in `design/COORDINATOR_DECISIONS.md:231`. No orchestrator, worker, client or config invokes
either entry point. No `foreign_load_detected` event type exists anywhere in the codebase, although
commit `5776877` requires one:

> Required before the freeze: a preflight host-quiescence gate that refuses to start while a
> foreign GPU consumer is present and names it; the same check at every quiescent scrape, emitting
> a logged `foreign_load_detected` event; both as chain events so a reader can see the host was
> clean.

Both files are also untracked (`?? experiments/live_ab/lab_hostcheck.py`,
`?? experiments/live_ab/tests_lab_hostcheck.py`).

As shipped, the gate would not have blocked the trial described in `5776877`, because nothing would
have run it.

**Required change:** call `preflight_host_quiescent` from the trial-start path with the harness's
own pids as `own_pids`, call `soft_host_check` at each quiescent scrape, emit
`foreign_load_detected` into the event chain from both, add the event type to the log schema and
its validator, and commit both files. Until then #11 remains blocked on the ground `5776877`
itself states.

### C.5 Does the tokenizer really remove the account name and home directory? — **Yes, on realistic paths.**

Executed on this host (`account_names() -> ('yukangzengcmac',)`):

| input | output |
|---|---|
| `python /private/tmp/claude-501/-Users-yukangzengcmac-ICLR-WinRatioAgentEvals/35a3/scratch/run.py` | `('python', '<TMP>/*.py')` |
| `python /Users/yukangzengcmac/proj/train.py --out /Users/yukangzengcmac/x.csv` | `('python', '<HOME>/*.py', '--out', '<HOME>/*.csv')` |
| `ollama serve yukangzengcmac` | `('ollama', 'serve', '<USER>')` |

The first case is the one the docstring singles out — the account name inside a *single* path
segment, where no home-prefix rewrite matches — and it is handled, because `summarize_path` keeps
only the root class and the extension and drops every intermediate segment. `_scrub_accounts` uses
a global case-insensitive `re.sub`, not a prefix rewrite. This part of the design works.

### C.6 — SEVERITY MEDIUM. The "closed vocabulary" claim is not true of non-path tokens.

The docstring promises "a short summary whose every token is either a conservative label or a
placeholder drawn from a closed vocabulary". A "conservative label" is
`_SAFE_LABEL_RE = ^[A-Za-z0-9][A-Za-z0-9_.+-]{0,47}$` — any 48-character alphanumeric string.
Verified leaks, all of which pass `summary_is_identifier_safe`:

| input | published summary |
|---|---|
| `python -m acmecorp_secret_router.server` | `('python', '-m', 'acmecorp_secret_router.server')` |
| `llama-server -m Qwen2.5-Coder-7B-Instruct.gguf` (relative path, no `/`) | `('llama-server', '-m', 'Qwen2.5-Coder-7B-Instruct.gguf')` |
| `ollama run deadbeefdeadbeefdeadbeefdeadbeef` (32 hex) | passes through verbatim |
| `ollama run deadbeefdeadbeef` (16 hex) | passes through verbatim |
| `ollama run aaaa…` (40 hex) | `<REDACTED>` |

The 16/32 carve-out is explicit and unexplained:
`if _HEXISH_RE.match(tok) and 7 <= len(tok) <= 40 and len(tok) not in (16, 32)`. A full MD5 and a
16-hex job id are published; a 40-hex commit id is not.

A foreign project's *module* name and a foreign model's *relative* filename are exactly the
"foreign project's directory names" the docstring undertakes to suppress.

**Required change:** document the carve-out's reason inline (or remove it), and either restrict
non-flag, non-path tokens to a real allowlist or amend the docstring to
*"flags and short literals survive verbatim; a bare token that is neither a path nor an address is
published as-is, so a foreign module or model name can appear in a finding."* Also decide
deliberately about ports — `--port 8191` survived in the replayed real incident (C.7) and is a weak
identifier of a foreign service.

### C.7 — SEVERITY LOW. Account names shorter than three characters are never scrubbed.

`account_names()` ends with `return tuple(sorted(n for n in out if len(n) >= 3))`. The threshold is
unexplained. On a host whose account is one or two characters, `account_names()` returns `()`,
`_scrub_accounts` is a no-op, and `summary_is_identifier_safe` — which iterates the same empty
tuple — returns `True`. The predicate would certify a leak. (Paths still collapse to `<HOME>/*`, so
the exposure is limited to a bare token equal to the account name.)

**Required change:** state the reason for the threshold in the docstring (presumably to avoid
mangling common substrings), and lower it to 1 with word-boundary matching, or accept it and record
it as a known limitation.

### C.8 Would the preflight have caught the real incident? — **Yes, if it were called.**

Reconstructed from commit `5776877` ("two `llama-server` processes … `-ngl 99 -np 4`, ~7.7 GB RSS
… 8h34m … client in `/Users/yukangzengcmac/DTR-AgentEvals/experiments/code_routing`") and replayed
through `enumerate_foreign_consumers`:

```
REAL INCIDENT caught: 2 findings; clean = False
    llama-server 501 30851 ['llama-server','-m','<HOME>/*.gguf','--port','8191',
                            '-ngl','99','-np','4','--host','127.0.0.1','--allow-contention']
    identifier_safe: True
    llama-server 502 30662 ['llama-server','-m','<HOME>/*.gguf','--port','8193',
                            '-ngl','99','-np','4']
    identifier_safe: True
```

`preflight_host_quiescent` raises `HostNotQuiescent` on this table. The foreign project path
`DTR-AgentEvals/experiments/code_routing` and the model name
`Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf` do **not** survive into the summary; `-ngl 99 -np 4` — the
evidence that the offender holds the accelerator — does. `elapsed_s = 30851` (8h34m) and
`rss_bytes` are carried, and `argv_sha256` lets an operator confirm the match locally.

Three qualifications: this works because `llama-server` is on the name list (C.3 — a renamed copy
would not have been caught); it does not depend on `lsof`, so C.2 does not affect this particular
incident; and it is contingent on C.4 — nothing currently calls the gate.

---

## Must change before the #12 protocol commit is published

Blocking. In order.

1. **C.4** — wire `preflight_host_quiescent` into the trial-start path and `soft_host_check` into
   the quiescent scrapes, emit `foreign_load_detected` into the event chain, add the event to the
   log schema, commit `lab_hostcheck.py` and `tests_lab_hostcheck.py`. Until this is done the gate
   that `5776877` made a precondition for #11 does not exist in any executable sense.
2. **C.2** — make the `lsof` failure path set `degraded` so the gate fails closed; add the test
   that asserts `preflight_host_quiescent` raises when the Metal probe could not run.
3. **C.3** — either extend the Metal probe beyond python rows, or state the renamed-binary blind
   spot in the module docstring *and* in the protocol's 5.7 language.
4. **B.1** — delete or correct §2.2's false claim that the #12 band module does not call
   `winstats.normal_mixture_radius`.
5. **B.6** — decide now whether the cost-certificate narrowing path enters §4.3, or add it to §1.3
   as a declared gap. It cannot be added after the first outcome.
6. **B.5** — freeze the label bijection, the exception rule and the `certified`/`collapsed` scope
   in §12.2, so that the agreement/disagreement verdict is not a later judgement call.
7. **B.2** — reconcile the fixture register (`F0…F12` in PROTOCOL and `cells.json`) with the code
   (`F01…F13`), and implement the protocol/config agreement fixture the header already claims
   exists.
8. **B.3** — implement the import-graph test. It is the only mechanical guard on the independence
   constraint.

Should change before the commit, in the same pass.

9. **B.8** — deposit the T4 variant of §6 now; state that T4 forfeits the root's `n = 2 000`
   summary.
10. **B.9** — resolve the §2.4 / §9.1 contradiction about whether the path continues past the
    decision.
11. **B.10** — disclose the already-executed randomized property runs in PROTOCOL.md.
12. **B.7** — measure the `N_max` scaling exponent, or freeze it as a stated assumption with a
    fixture behind it.
13. **B.4**, **B.12** — make the fixtures do what §11 and §2.2 say they do, or say what they do.
14. **B.14** — cite the two-sided level; if it is per-tail, every §9 nominal bound is wrong by 2.
15. **C.6**, **C.7** — correct the "closed vocabulary" claim; document the 16/32-hex carve-out and
    the 3-character account-name threshold.
16. **B.11**, **B.13** — justify the smoke cell; say that the three named scripts do not yet exist.

Section A requires no change. The independence constraint appears to have been honoured; that
verdict rests on the absence of mechanical overlap and on six substantive divergences, and it
cannot be stronger than that, for the reasons in A.5.
