# PREREG_CHECK_2: re-audit of the fixes to PREREG_CHECK.md

Second adversarial pass, session `session60/live-ab-validation`, 2026-09-20. `HEAD` is still
`de31b6cf124b3723eb9986a03318f1ae4f935353`; every file under audit is **uncommitted** (six `M`
files under `experiments/live_ab/`, plus `?? experiments/live_ab/lab_hostcheck.py`,
`?? experiments/live_ab/tests_lab_hostcheck.py`, `?? experiments/live_ab_validation/`). No git
state was changed by this audit. Scope: every finding of `PREREG_CHECK.md`, blocking or not,
re-tested against the current files, plus whatever the fixes introduced.

| section | first verdict | **this verdict** |
|---|---|---|
| **A. Independence of `vband.py` / `vfixtures.py`** | READY | **READY** — and now machine-checked, not declared. One residual gap (N.6) |
| **B. `PROTOCOL.md` vs the root's frozen acceptance design** | FIX-FIRST, 6 blocking | **FIX-FIRST** — every prior blocking item is closed; **one new blocking item, N.1** |
| **C. Quiescence gate `lab_hostcheck.py`** | BLOCK | **FIX-FIRST** — C.2/C.3/C.4 are genuinely closed; C.6 partly, C.7 open, **one new blocking operational item, N.7** |

**The #12 protocol may not be committed as it stands** — one line is wrong (N.1) and three
sentences claim checks that do not exist (N.2, N.3, N.4). **The #11 freeze may not proceed** —
not because of the gate, which now works, but because the gate says so: the serving host is
**not quiescent right now** (section C.8b).

---

## What was executed, and its true output

| command | true result |
|---|---|
| `.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_*.py'` | **`Ran 380 tests in 195.672s` … `OK`**, exit 0 (was 304 before the gate's 76 tests) |
| `.venv/bin/python experiments/live_ab/tests_lab_hostcheck.py` | **`Ran 76 tests in 0.409s` … `OK`** |
| `.venv/bin/python experiments/live_ab_validation/tests_validation.py` | **`ran=58 failures=0 errors=0 skipped=0`**, 1.265 s |
| `.venv/bin/python experiments/live_ab_validation/vfixtures.py` | **`17/17 fixtures passed`** (`F01`…`F17`) |
| `.venv/bin/python experiments/live_ab/dryrun_live_ab.py --scenario all` | exit 0; `D1 ended verifier=PASS harm_keep_incumbent@39`, `D2 horizon_no_decision@40`, `D3 deploy_candidate@44`, `D4 horizon_no_decision@40` |
| injected `lsof` `OSError` / non-zero exit / timeout, foreign python present | **`preflight_host_quiescent` RAISES** in all three (was: passed silently) |
| renamed GPU binary, 7.8 GB RSS, compute-class Metal | **caught**, `detector=metal-process`, `clean=False` (was: `clean=True`) |
| the full `2,878,680`-state enclosure sweep of PROTOCOL 2.5 | **128 disagreements, all at `ell = 200/19`, 0 away from `a/d = 5/19`** — reproduces exactly |
| independent recomputation of all **32** values of PROTOCOL 6.4 | **all 32 reproduce exactly** (exact rational arithmetic, no `vband`, no `cells.json`) |
| independent recomputation of all **32** values of PROTOCOL 6.1 | **all 32 reproduce exactly** |
| 6 attacks making `live_ab_validation/` import the #11 monitor | **4 caught by both halves of `F16`, 1 by the static half only, 1 by neither** (N.6) |
| mutation coverage of `F15` over every numeric token of every PROTOCOL table | **384 of 595 caught (64.5%)**; the unguarded set includes whole frozen tables (N.2) |
| sha256 of the three files PROTOCOL.md pins | `winstats.py` ✅, guidance ✅, **`protocol_FINAL.md` ❌ STALE** (N.1) |
| `lab_hostcheck.py` run as the operator view, on this host | **3 findings, `clean=False`** — the host is contended (C.8b) |

---

## A. Independence — verdict READY

| prior finding | status | evidence |
|---|---|---|
| A.1 declared source list | **unchanged** | the declarations are still there; they are no longer the only thing |
| A.2 no mechanical overlap | **unchanged** | not re-run; nothing in the revision touched `vband.py` (PROTOCOL 12.1a item 1) |
| A.3 #11 vocabulary absent | **unchanged** | same |
| A.4 six visible divergences | **unchanged**, and one is now *used* | the `certified`/`collapsed` contradiction is now the stated reason the flag is out of scope in §12.2 |
| A.5 what the verdict cannot mean | **strengthened, correctly** | §12.1a now discloses the one-directional leak from the first audit, item by item, including that §12.2's bijection was written knowing #11's alphabet, and that agreement on the cost tier "is not independent evidence" |

The substantive change is that the constraint is now **enforced** rather than declared, and the
enforcement is real: see B.3 below. §12.1a is the right disclosure and it is unusually honest —
item 2 ("the coincidence … is now a *known* coincidence and is therefore **not** independent
evidence of agreement") and §12.3 item 7 give away more than they had to.

Two things this verdict still cannot mean, unchanged from A.5: shared model priors still explain
convergence, and no commit chronology exists, because **everything is still untracked**.

---

## B. PROTOCOL.md — every prior finding

| # | severity | status | evidence |
|---|---|---|---|
| **B.1** | HIGH | **CLOSED** | §2.2 now reads "`vband.radius_from_formula` **calls the pinned primitive** … **every `L` and `U` this study reports comes from `src/winstats.py`**", and confines `literal_radius` to a cross-check whose scope it states narrowly ("that `vband` passes the intended arguments … not independent evidence about the primitive itself"). That is option (a), the honest fix, and it is worded better than I asked for. |
| **B.2** | HIGH | **CLOSED** | The register is `F01…F17` in the code, in PROTOCOL §11, in `cells.json`, and in §13.2's `fixtures_report.json` line. `F15_protocol_config_agreement` exists and compares all three id lists (`vfixtures.py:1608-1618`), and `tests_validation.TestProtocolConfigAgreement` has 11 mutation tests including `test_a_drifting_fixture_register_is_caught` — "the exact drift the audit found". All pass. The renumbering went the other way from my recommendation, which is fine; what mattered was that one register exist. **But see N.2**: the fixture does far less than §11 says it does. |
| **B.3** | HIGH | **CLOSED — and it bites.** | `F16_import_graph_independence` + `TestImportGraphIndependence` exist, with two halves. I attacked them six ways in a throwaway copy (repo untouched): (1) `import lab_monitor` in `vband.py` → **both** halves fire, the dynamic one naming `lab_monitor`, `lab_enclosure` **and** `lab_common` by path; (2) `import lab_enclosure` from the pinned tree → both fire; (2b) `from pinned import lab_enclosure` → both fire; (3) `importlib.import_module("lab_" + "monitor")`, name assembled at run time → both fire. This is a real guard, not a decoration. **See N.6** for the two attacks that got through. |
| **B.4** | MEDIUM | **CLOSED** | `F14_radius_sweep` sweeps `n = 1…20,000` at `!=` on the float — strict equality, the whole range, exactly what §2.2 and §11 now claim. Ran in the 17/17. |
| **B.5** | HIGH | **CLOSED, thoroughly** | §12.2 now freezes (i) the full label bijection as a table, with `horizon_no_decision → CONTINUE` **plus** the requirement that the #12 trial end in `NO_DECISION`, and "anything else → a disagreement, not an unmapped case"; (ii) the `n = 0` look excluded by construction and named as a structural difference; (iii) the exception rule verbatim — "An exception raised by either side at a look where the other returns a value **IS** a disagreement", written to `comparison_defects.csv`, "never … a skip, a filter, or a harness detail"; (iv) `certified`/`collapsed` explicitly out of scope **with the reason and with the report obligation**. §12.3 item 7 then discounts agreement on the cost tier. Nothing here is left to later judgement. |
| **B.6** | HIGH | **CLOSED, and verified analytically** | The cells now carry atom cost columns (§4.1) and an elapsed-cost accrual `ell(a) = (c*a)/D` with a frozen evaluation order (§4.3), and §6.4 prices the exercise. I recomputed **all 32 values of §6.4** from §§2.5/4.1/4.2/4.3/7.3 alone, in exact rational arithmetic, without touching `vband` or `cells.json`: **all 32 reproduce exactly**. I also re-verified all 32 of §6.1 — **exact**, so the revision did not move the resolution model. `F17_atom_cost_table` exercises 47,484 enclosure states for containment, monotonicity and the point thresholds. Ground truth (`mu_h`, `mu_s`) is still enumeration over six atoms and is provably untouched by the cost columns (`|10-40| = 30 > tol = 2`). §4.4 states the provenance of the fix rather than claiming foresight. **This is a genuine fix, not a paper one.** Two qualifications in N.5b. |
| **B.7** | MEDIUM | **CLOSED** (with N.5) | §8.1 now takes **two** horizon points and *measures* `beta = log(s_2000/s_1000)/log 2` instead of assuming linearity. |
| **B.8** | MEDIUM | **CLOSED** | `cells.json → analytic_reachability.T4_variant_N_max_1000` carries the `N_max = 1,000` variant of 6.1–6.4, deposited now; §8.2 says in terms that "**`T4` forfeits the `n = 2,000` fixed-horizon summary required by root item 4** … the report states this as a reduction of the root's design"; §14 repeats why. |
| **B.9** | MEDIUM | **CLOSED** | §2.4 now reads "The decision is the first crossing. The simulated path is nevertheless carried on to the finalization look … a **bookkeeping device of this simulation** and is not what the live trial does", and §9.1 points back at §2.4. The two sections no longer contradict. |
| **B.10** | MEDIUM | **CLOSED** | New §0.1 names all four pre-freeze executions, including `TestRandomisedContainment` over 300 seeds, `TestLargeProgramSmoke`, and the new `TestCostEnclosurePath`, with the RNG, the namespace, and "they establish no operating characteristic and none is claimed from them". §0.2 discloses the revision itself. |
| **B.11** | LOW | **CLOSED** | §8.1 "Why those cells": `C1`/`C2` share the law with the largest unresolved fraction among non-escalating cells and differ only in the delay rule. |
| **B.12** | LOW | **CLOSED** at the section level | §11's opening now says exactly what the fixtures do: `F01`–`F11`/`F17` hand-derive enclosures and sums and call `vband.normal_mixture_band`; radii are cross-checked at the locked values in `F12` and over the range in `F14`; `F12` assembles one interior band by hand. "The pre-audit draft of this section claimed more than that, and the claim is now what the code does." **But see N.4** — one row of the table below it re-commits the same sin. |
| **B.13** | LOW | **CLOSED** | §13.0 is a whole new subsection: "As of the freeze commit, `vgen.py`, `vrun.py`, `vcompare.py` and `REPORT.md` do not exist. This section specifies them", with a status column per file and the rename from `run_validation.py`/`compare_to_live_ab.py` recorded. |
| **B.14** | LOW | **CLOSED** | §2.2 now cites `paper/theory.tex` Theorem *Normal-mixture confidence sequence* (`thm:normal_cs`). I read it (`paper/theory.tex:288`): `C_n = [muhat_n ∓ B_alpha(V_n)/n]`, `P{mubar_n ∈ C_n for every n ≥ 1} ≥ 1 − alpha`, intersectable with `[-1,1]`, `V_n = n` for balanced pair scores. It is **simultaneous and two-sided**, so §9's nominal bounds are not off by two. The partial-information form cites `paper/asynchronous.tex` `thm:async_cs`, which also exists. |

---

## C. The quiescence gate — every prior finding

| # | severity | status | evidence |
|---|---|---|---|
| **C.1** | informational | **CLOSED** | The module docstring now carries the caveat verbatim: "`subprocess.run(..., timeout=...)` kills the child IT STARTED … No process this module FINDS is ever signalled". The three enforcing tests still pass. |
| **C.2** | HIGH / BLOCKING | **CLOSED — re-verified by injection** | `metal_context_pids` now returns a `MetalProbe` with a distinguishable `failure`, and `enumerate_foreign_consumers` degrades when `probe.failure is not None and probe_rows`. With a foreign python GPU process in the table: `lsof` raising `OSError` → **`HostNotQuiescent`, `degraded=['lsof-unavailable']`**; `lsof` exiting non-zero with no output → **raises, `lsof-unlisted-3`**; `lsof` timing out → **raises, `lsof-timeout`**. `-V` plus `_LSOF_NOT_LOCATED_RE` correctly exempts a pid that exited between `ps` and `lsof`, which is the one benign case. `MetalProbeFailureTests` (9 tests) asserts all of it. The one silent case left is by design and stated: with **nothing** to probe there is nothing unproven (`clean=True`, verified). |
| **C.3** | HIGH / BLOCKING | **CLOSED in mechanism; the stated limitation is real and, on this host, larger than the module's lead sentence suggests** | The module took option (a) *and* (b). A third arm probes every non-python, non-allowlisted row at or above `PROBE_RSS_FLOOR_BYTES = 128 MiB` and reports it on a **compute-class** marker only. Verified: `/opt/x/srv -m … -ngl 99 -np 4` at 7.8 GB with a compute-class holder → **1 finding, `metal-process`, `clean=False`** (previously 0 findings, `clean=True`). A display-class-only GUI app above the floor → **0 findings**, as intended. The blind spots are now stated in three places as required: the module docstring ("It does NOT detect: an accelerator job whose resident size is below `PROBE_RSS_FLOOR_BYTES` …"), `tests_lab_hostcheck.RenamedBinaryTests.test_the_documented_blind_spot_below_the_floor_is_real_and_stated`, and `protocol_FINAL.md` §5.7.1 ("**'no other GPU job' is a requirement of this protocol and an operator responsibility; it is checked, not enforced**"). **See N.8** — the docstring's lead sentence is still too strong, and this host proves it. |
| **C.4** | HIGH / BLOCKING | **CLOSED in code; the commit half is outstanding and is the coordinator's** | `lab_orchestrator.py` now: imports `lab_hostcheck`; defines `host_scan_is_required`, `own_harness_pids`, `host_quiescence_gate`, `write_host_quiescence_refused`; calls the hard gate inside `run_trial` **after** `preflight` and **before** `lock.acquire()`, writing `preflight_refused('host_not_quiescent')` **and** `host_quiescence_refused` to the program chain and returning `'aborted'`; and calls `soft_host_check` from `World.host_scan`, emitting `foreign_load_detected`. `lab_eventlog.EVENT_SCHEMA` now has 49 types (asserted), both new ones with closed-vocabulary `detector` and `cause` enums transcribed from `lab_hostcheck.DETECTOR_LABELS` / `DEGRADED_CAUSES`. `lab_verify_log` reads both via `_check_host_scans`, with `host.record` (internal honesty of `clean`) and `host.quiescence` (what was seen). `OrchestratorWiringTests.test_a_non_quiescent_host_refuses_to_start_the_trial` drives the **real** `run_trial` with `sim=False` and asserts the trial chain is never opened, the program chain carries exactly one `host_quiescence_refused` naming `llama-server`, `preflight_refused` carries `['host_not_quiescent']`, the body contains no account name and no `/Users/`, and the verifier returns no `host.*` FAIL and one INFO `host.quiescence` row. All 76 pass. `test_there_is_no_configuration_key_that_disables_the_gate` greps the source for an off-switch. **Still outstanding:** both files are `??` in `git status`; I do not commit. **See N.9** for the scrape point that is excluded. |
| **C.5** | (no change asked) | **still true** | `_scrub_accounts` is still a global case-insensitive `re.sub`; `/Users/<acct>/proj/train.py → <HOME>/*.py`; a bare account token → `<USER>`. |
| **C.6** | MEDIUM | **PARTLY** | The docstring now admits the truth — "That vocabulary is closed for paths and addresses but **NOT** for bare literals (C.6): a token that is neither a path nor an address survives verbatim, so a foreign project's module name or a model's relative filename can appear in a summary" — and the structural fix is better than what I asked for: `chain_finding` **drops `command_summary` entirely** and publishes `summary_sha256` instead, so no free token can reach the immutable chain. `protocol_FINAL.md` §5.7.1 repeats it. That also disposes of the port question. **But the 16/32-hex carve-out is still undocumented.** `lab_hostcheck.py:415` and `:468` still read `and len(tok) not in (16, 32)` with no inline reason, and I re-verified the leak: `ollama run deadbeefdeadbeefdeadbeefdeadbeef` (32 hex) and the 16-hex form still pass through verbatim while 40 hex becomes `<REDACTED>`. `protocol_FINAL.md:2016` explains that the chain's string discipline admits digests of length 16/32/40/64 — which, if that is the reason, makes the carve-out *inverted* (40 is admissible there and is redacted here). The checker asked for one comment; there is none. |
| **C.7** | LOW | **OPEN** | `account_names()` still ends `return tuple(sorted(n for n in out if len(n) >= 3))`, with no reason given anywhere in the module, the tests, or `protocol_FINAL.md`. On a host with a 1- or 2-character account, `account_names()` is `()`, `_scrub_accounts` is a no-op, and `summary_is_identifier_safe` — which iterates the same empty tuple — returns `True` on the leaked token. Nothing was changed and nothing was recorded. |
| **C.8** | (evidence) | **still true, and now live** | The `5776877` incident replays through `preflight_host_quiescent` and raises; `-ngl 99 -np 4` survives into the summary, the model name and the foreign project path do not, and `identifier_safe` is `True` for both findings. |

### C.8b The host is not quiescent right now

`.venv/bin/python experiments/live_ab/lab_hostcheck.py`, on the serving host, at the time of this
audit, `scanned = 1032`, `degraded = []`:

| detector | pid | rss | elapsed | summary |
|---|---|---|---|---|
| `llama-server` | 63658 | 1,849,786,368 B | 38,051 s (10 h 34 m) | `llama-server -m <HOME>/*.gguf --alias qwen2.5-7b-instruct --port …` |
| `llama-server` | 63657 | 71,352,320 B | 38,051 s | `llama-server -m <HOME>/*.gguf --alias qwen2.5-3b-instruct --port …` |
| `metal-process` | 39197 | 411,451,392 B | 30,522 s | `mediaanalysisd` |

`preflight_host_quiescent` refuses on this table. The contention the coordinator found on
2026-09-19 has **not** been cleared; a second pair of `llama-server` processes has now been
holding the accelerator for ten and a half hours. **#11 cannot open a trial chain on this host
today**, and that is the gate working.

---

## New findings the fixes introduced

### N.1 — SEVERITY HIGH, **BLOCKING the #12 commit**. The protocol pins a hash of a file that has since changed.

PROTOCOL.md's header table pins

> | vocabulary alignment | `experiments/live_ab/design/protocol_FINAL.md` … SHA-256 `03028374e7042a22e46b8aedd44cfdf8432b29d576ffb966742c228c6ed1c78c` |

`03028374…` is that file **as of `HEAD`**. The C.3/C.4 work added section 5.7.1 to it, and
`git status` lists it as ` M`. Measured:

```
pinned in PROTOCOL.md : 03028374e7042a22e46b8aedd44cfdf8432b29d576ffb966742c228c6ed1c78c
actual worktree file  : dc681784504aaaf434b49ea8cd88fdc9a38efc438725600a773aef6ce641ce6f
```

The other two pins (`src/winstats.py`, the guidance document) still match. If the coordinator
commits the #11 gate work and the #12 freeze in the same push — which is what the sequence
requires — the #12 pre-registration will be frozen carrying a pin to a version of
`protocol_FINAL.md` that does not exist at that commit. A pre-registration whose provenance pin
is stale at the moment of commit is not pinned.

**And nothing catches it.** `F15`'s hash check is

```python
doc_hashes = set(re.findall(r"\b[0-9a-f]{64}\b", text))
...
want = cfg["provenance"][key]["sha256"]
if want not in doc_hashes: fails.append(...)
```

It asserts that the same 64-hex string appears in both documents. **It never hashes a file.**
Neither does anything else: grep for a file hash over `vfixtures.py` and `tests_validation.py`
returns nothing, and `pinned/PINNED.json`'s three hashes are verified by no test either (I
checked them by hand — all three match both the pinned copies and the live worktree files, so
the manifest is currently correct; it is just unguarded).

**Required change, before the commit:** recompute all three hashes against the files as they will
be at the freeze commit and update both documents; and extend `F15` (or add `F18`) to hash
`src/winstats.py`, the guidance document, `protocol_FINAL.md` and the three files in `pinned/`,
and compare against `cells.json` and `pinned/PINNED.json`. Two of those hashes being right by
luck is not a pin.

### N.2 — SEVERITY MEDIUM. `F15` guards about two thirds of what §11 says it guards.

§11 and §13 say `F15` compares "**every numeric table** in this document that also appears in
`cells.json` … value by value". I measured it: perturbed every numeric token of every markdown
table row in PROTOCOL.md, one at a time, and ran `check_protocol_config_agreement` on each — 595
mutations, **384 reported, 211 not**. Many of the 211 are incidental (`#11`, `section 2.3`,
`1e-12`), but whole **frozen** tables are unguarded, and their values **are** in `cells.json`:

| table | mutations caught / missed | the `cells.json` key it is not compared against |
|---|---|---|
| §2.5 the enclosure-row table | **0 / 44** | `enclosure_rules.*` |
| §9.2 decision-level quantities and their nominal bounds | **0 / 9** | `reported_quantities.decision_level.*.nominal_bound` |
| §5 the three seed namespaces | **0 / 7** | `seeding.namespaces.*` |
| §8.2 the budget ladder's grid column (only the totals column is guarded) | 4 / 12 | `budget.*` |
| §7.1 looks-per-trial / decision-eligible looks derivations | 8 / 4 | `parameters.looks_per_trial`, `parameters.decision_eligible_looks` |

§2.5 is the worst of these: it is the table that decides ground truth for the whole B.6 fix, and
`cells.json` is declared normative over it while nothing compares the two. This is the same
defect B.2 was about, one level down.

**Required change:** either extend `F15` to those five tables, or replace "every numeric table"
in §11 and §13.2 with the actual list.

### N.3 — SEVERITY MEDIUM. `cells.json` attributes to `F17` an assertion `F17` does not make.

`cells.json → parameters.cost_model.narrowing_thresholds.closed_form_is_not_bit_identical`:

> over the 2878680 (atom, revealed arm, d, age) states … the two readings disagree on exactly 128
> states … **`F17_atom_cost_table` asserts the disagreement set is exactly those states**.

It does not. `F17` sweeps `_F17_SHORT + _F17_LONG` = 32 delay values, `_expect(… "states
exercised", n_states, 47484)`, and `_expect(… "boundary states reached", len(boundary), 28)`. It
asserts **28** disagreements over **47,484** states, a 1.6% subgrid.

PROTOCOL §2.5 states this correctly — "The `2,878,680`-state sweep was run once while writing
this protocol; `F17_atom_cost_table` re-checks `47,484` of those states … and asserts that it
finds exactly the `28` boundary states **that grid reaches**". So the prose twin contradicts the
protocol, and `F15` cannot see it because `F15` parses tables, not prose.

For the record, I ran the full sweep the protocol claims and it is **true**: 2,878,680 states,
**128** disagreements, **0** away from `a/d = 5/19`, all at `ell = 200/19 = 10.526315789474`,
reached at 32 distinct `d` by exactly the four `(atom, revealed arm)` combinations
`{(BB+,C), (C>I,C), (BB-,I), (I>C,I)}`. The claim is right; the attribution is wrong.

**Required change:** correct that sentence in `cells.json` to match §2.5.

### N.4 — SEVERITY LOW. §11's `F17` register row re-commits B.12.

§11's prose says `F17` exercises 47,484 states. The register row four lines below says `F17`
asserts its properties "**over every** `(atom, revealed arm, d, elapsed age)` state". Those
cannot both be true, and the second is the one a reader quotes.

**Required change:** one word — "over 47,484 of the `(atom, revealed arm, d, elapsed age)`
states".

### N.5 — SEVERITY MEDIUM. The measured scaling exponent is confounded with the cell.

§8.1's fix to B.7 measures `beta = log(s_2000/s_1000)/log 2` from **10 programs in `C1` at
`N_max = 2,000`** and **10 programs in `C2` at `N_max = 1,000`**. The two points differ in
`N_max` **and** in the delay rule. `beta` therefore absorbs whatever `C1`→`C2` costs, and the
protocol's own §6.4 shows those cells are not identical in the work they do: at `n = 500` the
cost tier narrows 3.60% of `C1`'s prefix and 4.66% of `C2`'s, a 29% difference in the branch of
the enclosure update that the elapsed-cost path exercises.

The protocol *asserts* the confound away — "under the section 9.1 all-looks reading every trial
runs to the finalization look, so runtime is close to cell-independent and the split costs
nothing" — but the split is precisely what makes that assertion untestable from the smoke output,
because no two smoke points share a horizon. A `beta` biased by the cell can select the wrong
tier, which was the whole point of B.7.

**Required change:** put both horizon points in the **same** cell (5 + 5 programs in `C1` at
`N_max = 2,000` and `1,000`, and the `A`-branch measurement, if it is wanted, as a third point at
a fixed horizon), or state in §8.1 that `beta` is confounded with the `N`→`A` delay branch and
bound the confound.

### N.5b — SEVERITY LOW, for the record, not a defect. What §6.4's fractions are worth.

The B.6 fix is real, and it is worth saying how much weight it carries rather than leaving
"the path is live in all eight cells" to do the work. Cost-attributable narrowing moves a pair's
hierarchy enclosure by `+1` (one branch removed) or `+2` (a point) on one endpoint. Taking
`point + narrowed` as the combined endpoint displacement per unit of prefix:

| | `C4` at `n = 500` | `C1` at the finalization look |
|---|---|---|
| combined endpoint shift from the cost tier | `0.1109` | `0.0155` |
| radius `r(n)` at that look | `0.1693` (`n=500`) | `0.0832` (`n=2,000`) |

So at the looks where the decision windows are widest the cost path moves the band by roughly
two thirds of a radius, and at the cap endpoint by roughly a fifth. That is a real exercise, not
a token one — worth stating in §6.4 item 1 in place of "about a fifth of that cell's unresolved
fraction", which measures the path against the wrong denominator.

One thing §9.3 does not do: its detection floors (`1.280x` nominal at 2,000 programs) are
computed for the per-gate rate over the whole path. A defect confined to the cost-certificate
path would only perturb the ~1–5% of pairs §6.4 counts, so the study's power against *that*
defect is not the power §9.3 reports. §1.3 would be the honest place for one sentence saying so.

### N.6 — SEVERITY LOW-MEDIUM. Two ways past `F16`, one of which will matter soon.

Of my six attacks, two were not reported:

1. **A marked, deferred dynamic import.** `_GUARD_MARKER` (`IMPORT-GUARD-LITERAL`) exempts
   `ast.Call` nodes as well as string literals. A marked `importlib.import_module("lab_monitor")`
   **inside a function body** is invisible to the static half, and the dynamic half only
   *imports* the three modules, so it never executes the function: **caught by neither**. The
   module comment claims "the dynamic half of F16 still catches an actual import" — that is true
   only for imports that run at module import time. Plain `ast.Import` nodes are correctly *not*
   exemptable, so this needs a deliberate marker; it is a greppable escape hatch, not a hole an
   accident falls into. The comment should say what it does not cover.
2. **A future module.** `F16`'s dynamic probe hardcodes `import vband, vfixtures,
   tests_validation`. I added a `vgen.py` doing `import lab_monitor`: the **static** half caught
   it, the dynamic half did not. `vgen.py` and `vrun.py` are exactly the modules that will
   produce this study's numbers, and nothing in §11, §12.1 or §13.0 requires the probe's list to
   grow with them.
3. `vcompare.py` is exempt from the static half **and** absent from the dynamic list. That is by
   design (it is the one module allowed to load `pinned/`), but it means §12.1 item 3's real
   constraint — that it load the **pinned copy** and not `experiments/live_ab/` — is enforced by
   nothing at all.

**Required change:** make the dynamic probe import every `*.py` in the directory except
`vcompare.py`, discovered rather than listed; and add one line to §12.1 item 4 saying which two
cases the guard does not reach.

### N.7 — SEVERITY HIGH, **BLOCKING #11's first trial**. The hard gate refuses on an Apple OS daemon, and there is no way through it.

Measured on this host, this hour: `mediaanalysisd`, pid 39197, 392 MiB resident, holding a
**compute-class** Metal resource, is reported as a `metal-process` finding and
`preflight_host_quiescent` refuses on it. It was absent from my first scan and present twenty
minutes later, so it is intermittent and not under the operator's control.

The module knew: `lab_hostcheck.py:105-106` says "exactly the llama.cpp server and Apple's
media-analysis daemon matched this family, and **both are genuine GPU compute consumers**". As
detection that is defensible — a Vision/MPS workload does contend for the accelerator. As an
**operational design** it is unfinished, and in exactly the way the module's own comment warns
about for substring matching ("a gate that cries wolf on a text editor is a gate an operator
learns to bypass"):

- the gate is a **hard** refusal at trial start;
- `test_there_is_no_configuration_key_that_disables_the_gate` guarantees there is no off-switch,
  correctly;
- there is **no allowlist** for a system daemon — `own_pid_allowlist` covers only the harness's
  own pids and their descendants;
- the module may not signal anything, correctly;
- and neither `lab_hostcheck.py` nor `protocol_FINAL.md` §5.7.1 tells the operator what to do
  when the offender is `mediaanalysisd`.

The result is a trial that cannot be started on a schedule, by a gate whose only documented
remedy is to remove an offender the operator is not allowed to remove. Every one of those
properties is individually right; together they have no exit.

**Required change, before #11's first trial:** decide and write down what happens when the only
finding is an OS-owned compute-class process. The defensible options are (a) a frozen,
by-detector allowlist of system daemons whose members are still **recorded** in
`foreign_load_detected` and still refuse if they are above some duty-cycle, or (b) keep the hard
refusal and document the operator procedure (how to quiesce `mediaanalysisd` before a trial, and
what to do if it reappears mid-trial). What is not defensible is discovering this at 2 a.m. on
the night of the first trial. Note that (b) alone does not help against the mid-trial case, which
N.9 makes invisible anyway.

### N.8 — SEVERITY MEDIUM. The module's own host refutes its lead sentence about renames.

`lab_hostcheck.py:30-31`:

> It therefore **DOES** detect a copy of `llama-server` renamed to anything at all, because a
> rename does not change which Metal libraries the process opens.

The qualifications follow immediately, which is why this is MEDIUM and not HIGH. But the
qualification that matters is not hypothetical here. Of the **two real `llama-server` processes
on this host**, one (pid 63657, the 3B server) is resident at **71,352,320 B = 68.0 MiB** — well
below `PROBE_RSS_FLOOR_BYTES = 128 MiB`. I confirmed the consequence directly: rebuild the real
process table with those two commands renamed, give the Metal probe its **best case** (every
probed pid reported as a compute-class holder), and the scan returns **1 finding, not 2** —
pid 63658 caught, **pid 63657 missed**, because it is never probed.

So on the machine this protocol is written for, the rename arm reaches one of the two foreign
`llama-server` processes actually running. Context: 1,034 processes, 26 at or above the floor,
3 python interpreters, 28 probed, `MAX_LSOF_PIDS = 96` not binding, one full scan costing
**0.09–0.11 s**. The floor is buying very little.

**Required change:** lower `PROBE_RSS_FLOOR_BYTES` — 32 MiB would still probe well under the
budget on this host — or rewrite the lead sentence as "detects a renamed accelerator binary
**above the resident-size floor**", and record the 68 MiB measurement beside it so the next
reader knows the floor is not theoretical. The docstring's own census ("956 processes … 16 stood
at or above 128 MiB") no longer matches this host either (1,034 and 26).

### N.9 — SEVERITY MEDIUM. The in-trial half never looks during enrollment.

`World.host_scan` emits only at `point in ('trial_start', 'quiescent')`. Tracing the call sites:
`scrape('trial_start')` (once), `scrape('pair_boundary')` (every pair boundary, throughout
enrollment), `scrape('trial_end')`, and `scrape('quiescent')` at **one** site — inside the
**post-decision** follow-up dispatch, every 50 dispatches. So across the entire enrollment
phase — the phase whose `latency_s` measurements are the primary endpoint — the host is observed
**exactly once**, at tick 0.

The hazard that produced this gate was a foreign server that ran for 8 h 34 m. A foreign server
that starts ten minutes into a multi-hour enrollment phase is invisible to this harness until
after the decision. Commit `5776877` asked for "the same check at every quiescent scrape", and
the implementation matches those words; the words were the wrong ones.

Cost is not the obstacle: a full scan measured **0.09–0.11 s** on a 1,034-process host, against a
`pair_boundary` cadence of one per pair.

**Required change:** add `'pair_boundary'` to the emit set (or a time-based cadence, e.g. no more
than one scan per 60 s, recorded either way), so that a mid-trial foreign load lands in the trial
chain while the trial can still be paused on it. Until then `protocol_FINAL.md` §5.7.1's
"observing check at the trial-start and quiescent scrape points" should say, plainly, that during
enrollment there is one scan.

### N.10 — SEVERITY LOW. The dry runs do not exercise the gate at all.

`host_scan_is_required` returns `not runtime(cfg).get('sim')`, so every `sim` invocation skips
both halves. That is the right rule — a simulated run measures no latency — but it means the four
dry runs I ran (`D1`–`D4`, all `verifier=PASS`) contain **no** `foreign_load_detected` and would
not have caught a wiring regression. The gate's only executable evidence is
`tests_lab_hostcheck.py`. Worth one sentence in `experiments/live_ab/README.md` §3, which
currently lists what the dry runs do exercise.

---

## Verdicts, and what may proceed

### Section A — **READY.**
No change required. The independence constraint is now mechanically enforced and the one
documented leak is disclosed in more detail than I would have insisted on. N.6 is a hardening
item, not a blocker.

### Section B — **FIX-FIRST.**
Every one of the six blocking items (B.1, B.2, B.3, B.5, B.6) and B.4 is **closed**, and closed
substantively rather than by rewording — B.6 in particular is a real redesign of the cells whose
32 new expected values I reproduced exactly from the frozen text alone. B.7–B.14 are closed.

**One new blocking item: N.1.** Two more should be fixed in the same pass because they are the
same class of defect the first audit raised: N.2 and N.3. N.4 and N.5 are cheap. N.5b is an
improvement, not a defect.

### Section C — **FIX-FIRST** (up from BLOCK).
C.2, C.3 and C.4 — the three items that made the first verdict BLOCK — are genuinely closed, and
I re-ran the checker's own probes to confirm it rather than reading the diff. The gate fails
closed, catches a renamed binary above the floor, is wired into the real trial-start path, and
its refusal and its in-trial record both reach the chain and the verifier.

**Remaining:** C.6 partly (the hex carve-out), C.7 open, plus N.7 (blocking for a first trial),
N.8, N.9, N.10, and the commit of the two untracked files.

### May the #12 protocol be committed?

**Not as it stands.** One line is wrong and three claim checks that do not exist. The fixes are
small and none of them touches a frozen value:

1. **N.1** — recompute the `protocol_FINAL.md` pin against the file as it will be at the freeze
   commit (and add a fixture that hashes files rather than comparing two documents' strings).
2. **N.3** — correct the `F17` sentence in `cells.json`.
3. **N.4** — correct the `F17` row in §11.
4. **N.2** — extend `F15` to §2.5, §9.2, §5, §8.2 and §7.1, or narrow the claim in §11/§13.2.
5. **N.5** — un-confound `beta`, or state the confound.

With those five done, **commit it.** Nothing in this re-audit requires a change to a cell, a
weight, a delay rule, a seed, an estimator, the flag rule, the positive control or any value in
sections 4, 6 or 9, and the freeze still precedes every simulation outcome: no cell has been run,
and §0.1 discloses the four things that had been.

### May the #11 freeze proceed?

**No, and not for a reason this audit can clear.** The gate is now real, and the gate refuses:
the serving host carries two foreign `llama-server` processes at 10 h 34 m and one
compute-class OS daemon **as of this audit**. §5.7 is not satisfied, so no trial may open a
chain, and `preflight_host_quiescent` will enforce that.

Before #11 can freeze:

1. Clear the host, and confirm with `lab_hostcheck.py` returning zero findings and zero
   `degraded`.
2. **N.7** — decide and write down what happens when the only finding is an OS daemon. This is
   the item most likely to be discovered at the worst possible moment.
3. **N.9** — scan during enrollment, not only at tick 0.
4. **N.8** — lower the floor or soften the sentence; the 68 MiB `llama-server` on this host is
   the evidence.
5. **C.6 / C.7** — one comment each.
6. Commit `lab_hostcheck.py` and `tests_lab_hostcheck.py` together with the `lab_orchestrator`,
   `lab_eventlog`, `lab_verify_log`, `tests_lab_chain` and `tests_lab_isolation` changes and the
   `protocol_FINAL.md` §5.7.1 text, so that the pin in N.1 can be taken against a real commit.

### One thing that is asserted and not demonstrated

Every claim in `protocol_FINAL.md` §5.7.1 and in the `lab_hostcheck.py` docstring about what a
real accelerator job *opens* — the census "of six processes above the RSS floor holding some
Metal resource, exactly the llama.cpp server and Apple's media-analysis daemon matched this
family", and "two ordinary desktop applications map `AGXMetal` while performing no accelerator
work" — rests on a measurement taken once, on one host, with no artifact in the repository. I can
report that the mechanism does work here: of 28 probed pids, exactly **1** held a compute-class
marker and it was the genuine 1.9 GB `llama-server`, while 4 others held display-class markers
only and were correctly not reported. That is one confirming observation, on a host whose numbers
already differ from the docstring's (1,034 processes and 26 above the floor, not 956 and 16). The
census should be re-taken and deposited as a file, or the docstring should stop quoting counts.
