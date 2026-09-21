# V2_BINDINGS — what the root's revision-16 rulings bound to actual code, and what did not close

Written 2026-09-20 by the #12 CPU validation session, against
`experiments/live_ab/design/COORDINATOR_DECISIONS.md` **revision 16**, the root
disposition `reviews/v2_batched_schedule_root_disposition_20260921_0226.md`, the
two bounded reviews beside it, `evidence/literature_sequential_design_20260921.md`,
and issue-12 comments **5754149408**, **5754257942**, **5754619899**, **5754667289**
(all four read; the root's rule "read every open thread the decision could live
on" is what this file is organised around).

Working tree at the time of writing: branch `session60/live-ab-validation`,
`HEAD = a266c6201e3c94fc50c6646ca741e5e1da9b409b`. **No Git state was changed by
this session**: no commit, no branch, no tag, no push. Every number below was
produced by a command that is quoted beside it.

**Status in one line.** Tasks 1, 2, 3, 4 and 6 closed; task 5 ran and produced a
delivered-runner receipt. **No calibration, freeze, grid, live clearance or
resource-gate discharge is claimed.** Section 8 is the blunt list of what did
not close.

---

## 0. Test and execution totals

```
.venv/bin/python experiments/live_ab_validation/tests_validation.py
```

| quantity | value |
|---|---|
| tests run | **130** |
| failures | **0** |
| errors | **0** |
| skipped | **0** |
| expected failures | **2** (the permanent deferred-sensitivity checks, section 1) |

Previous owner-reported total at the prior head was 108 CPU tests + 18 fixtures.
The 18 fixtures still run inside this total (`TestFixtures`), and 22 tests are
new here: 6 for the deferred sensitivity, 11 for the vendored reference and
cross-check, 5 for the v2 snapshot.

The only execution beyond tests: the authorized balanced resource measurement
(section 5) and the reference's own timing. **No grid, no sweep, no live trial,
no model call, no paid compute.**

---

## 1. TASK 1 — the finest sensitivity is deferred and disabled, and its defect is permanently recorded

Ruling: root disposition decision 1; revision 16 item 78.

**Disabled in the primary panel.** `vrun.py` now carries `DEFERRED_SCHEDULES`,
`PRIMARY_PANEL_SCHEDULES`, `is_deferred()`, `check_primary_panel_schedule()` and
`DEFERRAL_REASON`. `--schedule` offers only `('v1_reduced', 'v2_tick_batched')`,
and `main()` calls `check_primary_panel_schedule` as defence in depth because
`main` is also called programmatically. `vresource_check.RUNNERS` drops
`v2_finest` from the design (it stays in `ALL_RUNNERS`, hand-selectable for
development evidence only).

**Preserved, not deleted.** `vgen.completion_event_states` is untouched, the
schedule constant remains in `SCHEDULES`, and `build_series_for` /
`evaluate_trial` still build it so the failing checks can keep demonstrating the
defect. `--witness` still prints all three schedules, with the deferral stated
in the label.

**The permanent failing-or-skipped check.** `TestDeferredFinestSensitivityDefect`
in `tests_validation.py`, six tests, on the root's own `(3,2,3)` witness built
from delays `d = (2,0,0)`:

| test | result | what it records |
|---|---|---|
| `..._is_deferred_and_cannot_be_selected_for_a_run` | pass | the disabling holds on every route |
| `..._code_is_preserved_not_deleted` | pass | deferral did not become deletion |
| `..._defect_is_present_and_this_is_what_it_looks_like` | pass | `(tick 3, k=1)` **is** emitted |
| `..._reachable_prefix_never_takes_the_value_the_iterator_emits` | pass | attainable prefixes are `{0, 3}`; 1 is not among them |
| `test_PERMANENT_FAILING_CHECK_finest_states_must_all_be_reachable` | **expected failure** | the contract "exact union over every admissible order" that the code does not meet |
| `test_PERMANENT_FAILING_CHECK_finest_fractions_must_be_sub_tick` | **expected failure** | `_look_fractions` caches by tick alone, so sub-tick decision state is not representable |

Both permanent checks are `unittest.expectedFailure`, so they are reported for
as long as the defect stands and turn into an **unexpected success** the moment
anyone repairs the iterator — which is the correct alarm, since the recorded
evidence would then be stale. **Nothing here repairs the sensitivity** and it
must not be described as repaired or validated.

Reproduce: `.venv/bin/python -m unittest tests_validation.TestDeferredFinestSensitivityDefect -v`

---

## 2. TASK 2 — the authors' empirical-Bernstein reference is vendored, and it imports and runs

Ruling: root disposition decision 4; revision 16 item 74; issue 12 comment 5754619899.

**It imported and it ran.** This is the headline the root asked for, and it is a
success rather than the reported failure the instruction also allowed for.

### Provenance

`experiments/live_ab_validation/reference/`, built by `vendor.py`, which fetches
over HTTPS and **refuses anything whose SHA-256 does not match a table frozen in
its own source**. Command actually run:

```
.venv/bin/python experiments/live_ab_validation/reference/vendor.py \
  --boost-include <scratch>/boost_1_87_0 \
  --pybind11-include <scratch>/builddeps/pybind11/include \
  --boost-archive <scratch>/boost_1_87_0.tar.gz
# -> vendored 9 files, verified-not-vendored 2, built boundaries.cpython-312-darwin.so
```

| upstream | commit | vendored path | sha256 |
|---|---|---|---|
| `yjchoe/ComparingForecasters` | `52748c86e0429a9612dc79892c3be6156a524132` | `upstream/comparecast/confseq.py` | `8ea07278…8baef4` |
| same | same | `upstream/comparecast/utils.py` | `5bc239e1…de37838` |
| same | same | `licenses/ComparingForecasters-LICENSE.txt` | `11be31df…088dc1` |
| `gostevehoward/confseq` | `5ffe733ca2447a2e28c2c91f3b00086173f2ab2c` | `upstream/confseq/__init__.py` | `e3b0c442…852b855` (empty, verbatim) |
| same | same | `upstream/confseq/boundaries.cpp` | `75818453…f45d7b` |
| same | same | `upstream/confseq/uniform_boundaries.h` | `2dd72cbf…685e21e` |
| same | same | `upstream/confseq/CMakeLists.txt` | `d8cd3a95…fa43db` |
| same | same | `licenses/confseq-LICENSE` | `2462eb28…9fbbd5` |
| — | — | `upstream/comparecast/__init__.py` | **OUR shim**, marked `vendor_shim` |

**Two of these hashes independently confirm the pin table**: `comparecast/confseq.py`
`8ea07278…` and `confseq/src/confseq/betting.py` `c75ee344…` are quoted verbatim
in the root's own `evidence/literature_sequential_design_20260921.md` under "Key
source hashes", and both matched on fetch.

**MIT notices retained verbatim**, both files, asserted by
`test_the_mit_notices_are_retained_verbatim`.

**Deliberately not vendored**, recorded in `MANIFEST.json` under
`verified_not_vendored` with reasons:
- upstream `comparecast/__init__.py` (`64380b84…`) — star-imports eleven sibling
  modules and would pull in pandas/matplotlib/seaborn on import, exactly the
  hazard the literature document warns about. Replaced by our shim.
- `confseq/src/confseq/betting.py` (`c75ee344…`) — hash-verified for provenance,
  kept **out of the importable tree** so `betting_cs`/`hedged_cs` cannot be
  substituted. `test_the_forbidden_constructions_are_not_in_the_importable_tree`
  enforces it.

### The build, and the resource cost of getting there

`confseq.boundaries` is a **C++ pybind11 extension**, and `uniform_boundaries.h`
includes `boost/math`. No prebuilt wheel exists for CPython 3.12 on arm64 (PyPI
`confseq` 0.0.11 ships cp37–cp310 only), so the module was compiled from the
authors' unmodified sources:

- **Boost 1.87.0 headers**, 154,912,292 bytes, sha256 `f55c340a…c741d`, from
  `archives.boost.io`. Build-time only, not vendored, not a runtime dependency.
- **pybind11 2.13.6**, installed with `uv pip install --target` into an
  **isolated directory**, never into `.venv`. The project environment is
  unchanged.
- `clang++ -O3 -std=c++14 -shared -undefined dynamic_lookup -fPIC -fvisibility=hidden`,
  ~2 s, producing `_build/boundaries.cpython-312-darwin.so` (356,208 bytes).

Everything about this is recorded in `MANIFEST.json`, including **every fetch,
install and build attempt** with status and duration.

### Isolation and powerlessness

- **`v_opt = 10.0`, `lo = -1.0`, `hi = +1.0`, `boundary_type = "mixture"`**, frozen in
  `eb_reference.py` and asserted by `test_the_frozen_tuning_cannot_drift`.
- `v_opt=None` (which tunes at the observed final variance), one-sided use without
  an explicit `c`, and out-of-range scores all **raise**.
- `alpha` is the existing two-sided per-gate allocation `vband.ALPHA_GATE = .00625`,
  passed unhalved because `confseq_eb` performs its own `alpha/2` split.
- **The primary does not import it.** `test_the_primary_does_not_import_the_reference`
  reads the source of all seven primary modules and fails on any occurrence of
  `eb_reference`, `eb_crosscheck`, `confseq_eb` or `comparecast`.
- **It cannot decide anything.** `reference_bands` returns two float arrays and
  nothing else. `panel.py` computes reference columns into a separate `ref_`
  namespace, and `assert_panel_cannot_decide` refuses any undeclared `ref_`
  column — it fired during development on `ref_role` and had to be told
  explicitly that role metadata is not an outcome.

### It runs

```
.venv/bin/python experiments/live_ab_validation/reference/panel.py --demo
```
Cell C1, `N_max=1000`, schedule `v2_tick_batched`, 3,600 panel rows, all three
primary constructions plus the declared reference. At the final look
(prefix 1,000, tick 1,200), reference band width **0.2584953308** against
ADAPTER **0.3139729107** (ratio 0.823), CPREFIX **0.3307112510** (0.782),
NAIVE **0.2430444363** (1.064).

**This is one trial on one cell and is not a width claim.** Whether the
reference is tighter at our n and our tie mass is unmeasured, and the
coordinator's own narrowing stands: adaptive betting constructions do not all
assume a common mean, and superiority at our sample size is unproved.

---

## 3. TASK 3 — my implementation is a separately labelled cross-check, and it disagrees

`reference/eb_crosscheck.py`. It is labelled `CROSS-CHECK (mine, from the theorem
statement) … NOT the author reference`, asserted by
`test_the_crosscheck_is_labelled_as_a_crosscheck_not_the_reference`. It did not
exist before, so it was written here.

I implemented Theorem 2's four parts from the statement: predictable centres
(running mean lagged by one, `gamma_1 = 0`), the intrinsic-time clock
`V_t = max(1, sum (z_i - gamma_i)^2)`, scale `c = hi - lo = 2`, and a
closed-form **polynomial-stitched** sub-exponential boundary from Howard et al.
Theorem 1.

```
.venv/bin/python experiments/live_ab_validation/reference/eb_crosscheck.py
```

**AGREEMENT — exact, to machine precision.**

| quantity | max abs difference vs the authors' code |
|---|---|
| centre (running mean) | **6.94e-17** |
| intrinsic-time clock, round-tripped through the authors' own boundary | **1.11e-16** |

That is the Theorem-2-specific machinery — lagged centre and squared-residual
clock — independently reproduced.

**DISAGREEMENT 1, not reconciled.** My stitched boundary does **not** reproduce
the authors' `poly_stitching_bound`, which computes the same published object,
at `alpha/2 = .003125`, `v_min = 10`, `c = 2`, `s = 1.4`, `eta = 2`:

| v | mine | theirs | relative |
|---|---|---|---|
| 10 | 28.587185 | 37.151466 | **−2.305e-01** |
| 50 | 50.455912 | 56.962414 | −1.142e-01 |
| 200 | 84.029110 | 87.938563 | −4.446e-02 |
| 1000 | 165.272913 | 167.213768 | −1.161e-02 |
| 5000 | 347.345667 | 348.268675 | −2.650e-03 |

The gap shrinks with `v`, so the leading `sqrt(v·ell)` term is right and the
discrepancy is in the constant inside `ell`. **My values are smaller**, i.e. my
stitched radius is narrower for the same nominal alpha — the unsafe direction.
I tried the one natural variant of the epoch term and it is algebraically
identical, so this is a real, open discrepancy. **I did not reconcile it**, per
instruction. Consequence, stated plainly: **the cross-check is not a validated
bound and nothing may rely on it for coverage.**

**DISAGREEMENT 2, expected and also not reconciled.** Full-CS width, mine
(stitched) over theirs (mixture): **1.151 at n = 1,000**, ranging to **1.946**
over the path. The authors' conjugate mixture is tighter than any stitched
boundary near the tuning point, by more than my stitching error. So "my boundary
constant is too small" and "my intervals come out wider" are both true, **of
different objects**, and neither licenses using the cross-check as a bound.

---

## 4. TASK 4 — the execution bindings

Ruling: root disposition decision 3; revision 16 item 79; protocol/resource review sections 2 and 3.

**(a) `write_manifest` reported the frozen cell version and the old protocol.**
Fixed by the new `vrun.v2_bindings(cfg)`. Base and amended identities are now
**separate fields**, so the parent v1 identity is preserved rather than
overwritten:

```
.venv/bin/python -c "... vrun.v2_bindings(vrun.make_config(1000,0,schedule=s))"
```
| field | `v1_reduced` | `v2_tick_batched` |
|---|---|---|
| `base_protocol_version` | `v1-cpu-validation` | `v1-cpu-validation` |
| `amended` | False | **True** |
| `amendment_version` | None | **`v2-cpu-validation`** |
| `amendment_sha256` | None | **`7a5d1f3d40e49d49…`** (`PROTOCOL_V2.md`) |
| `operative_protocol_version` | `v1-cpu-validation` | **`v2-cpu-validation`** |
| `external_reference` | present, 9 vendored files | present, 9 vendored files |

`PROTOCOL_V2.md` is now hashed into `sources` as well. A missing binding is
reported as `None` **with a reason string**, never omitted.

**(b) `run_smoke` still used the old confounded split.** Now schedule-dependent:

```
vrun.run_smoke(guard, 20, schedule=...)
```
| schedule | design | groups | unique programs |
|---|---|---|---|
| `v1_reduced` | **original confounded**, preserved | C1@2000×10, C2@1000×10 | 20 |
| `v2_tick_batched` | **balanced 2×2** | C1@1000×5, C1@2000×5, C2@1000×5, C2@2000×5 | 20 |

Distinct program bases per group, so the balanced design visits 20 distinct
programs rather than timing the same streams twice. v1's path is byte-for-byte
the old one, so v1's deposited budget selection stays reproducible.

**(c) Tick and prefix names and captions.** `decision_time.csv`'s caption now
names **three** distinct coordinates — enrolled prefix `tau`, elapsed calendar
tick `tau_tick`, and the completed baseline sample index (`k` for CPREFIX, `m`
for NAIVE) — and says v1 emitted one number for all three. `DECISION_COORDINATES`
descriptions now state that `tau` is pinned at `N_max` through the drain and is
neither the baseline sample size nor elapsed time.

**(d) A new explicit v2 output location.** `WriteGuard` accepts
`results/live_ab_validation_v2/…` for development **and refuses to let the
reported grid write there at all**; the reported grid's only destination is
still `CANONICAL_OUT`.

**(e) The measurement harness is bound.** `write_manifest` takes a `harness`
argument carrying the design, the schedule measured, and SHA-256 of `vrun.py`,
`vgen.py`, `vband.py`. `vresource_check` records `harness_sha256` of **itself**,
which the protocol/resource review found missing.

---

## 5. TASK 5 — the one authorized execution, against the actual delivered runner

### How I verified I am timing the delivered code path

The root was explicit that passing `--pin` while still timing my own helper is
not enough. Three independent controls, and one of them changed the answer:

1. **Static rewiring.** `measure_group` no longer calls
   `evaluate_trial_amended`. Every runner calls `vrun.evaluate_trial(draw, cfg,
   schedule)` and writes through `vrun.trial_rows(..., schedule)`.
   `RUNNER_SCHEDULE` maps runner names onto `vrun`'s own schedule constants.
2. **Provenance by inspection**, recorded in every receipt as `delivered_path`:
   resolved via `inspect.getsourcefile` / `getsourcelines`. The deposited
   receipt reports `timed_callable = vrun.evaluate_trial`,
   `timed_callable_file = …/experiments/live_ab_validation/vrun.py`,
   `timed_callable_first_line = 756`,
   `timed_callable_is_the_measured_vrun = true`,
   `schedule_measured = v2_tick_batched`,
   `vrun_sha256 = 2bc37fa697e709dbe59ee7ec18498c269cf34cc82d23ae7171a100b901f3e417`.
3. **Proof by execution.** For the duration of every timed region
   `evaluate_trial_amended` is replaced by a **raising sentinel**
   (`AmendedHelperCalled`). A silent fall-back aborts the measurement instead of
   returning a plausible wrong number. All 64 workers completed, so it never fired.

**The control that changed the answer.** The default `--pin HEAD` imports the
measured modules from a `git archive` export of a **commit**, not the working
tree. My delivered changes are uncommitted (no Git state may be changed), so
under the default the first provenance probe returned
`timed_callable_is_the_measured_vrun = false` and pointed at
`/var/folders/…/vresource_pin_a266c6201e3c/…`. **The measurement was therefore
run with `--pin tree`**, and the receipt records
`measured_source_rev = "WORKING TREE (not pinned)"`, `is_working_tree = true`.
A commit-pinned receipt now carries an explicit `working_tree_warning`.

### The command

```
.venv/bin/python experiments/live_ab_validation/vresource_check.py \
  --part measure --pin tree --reps 8 --inner 20 --write \
  --out results/live_ab_validation_v2/resource_check_delivered
```
Balanced 2×2, 20 programs (namespace 1, indices 1000–1004), 8 outer repetitions
× 20 inner, each group in its own subprocess. Harness time **24.2 s**.
**64 worker subprocesses, 64 succeeded, 0 failed, 0 retried.**
The prior prototype receipt in `results/live_ab_validation_v2/resource_check/`
is **preserved untouched** — the new deposit is a sibling directory.

### Seconds and peak memory per cell and per horizon

`v1_reduced` (preserved, for the paired contrast):

| group | ms/program | peak RSS | looks/trial | bytes/prog |
|---|---|---|---|---|
| C1/1000 | 1.8504 ± 0.0109 | 69.3 MiB | 3,003 | 166.0 |
| C1/2000 | 2.7692 ± 0.0138 | 69.8 MiB | 6,003 | 168.4 |
| C2/1000 | 1.8861 ± 0.0222 | 69.4 MiB | 3,003 | 192.0 |
| C2/2000 | 2.7738 ± 0.0080 | 69.8 MiB | 6,003 | 181.8 |

**`v2_all_ticks` — THE DELIVERED BATCHED PRIMARY:**

| group | ms/program | peak RSS | looks/trial | bytes/prog |
|---|---|---|---|---|
| **C1/1000** | **2.0274 ± 0.0052** | 69.5 MiB | 3,600 | 199.2 |
| **C1/2000** | **3.2207 ± 0.0129** | 70.3 MiB | 6,600 | 201.4 |
| **C2/1000** | **2.0506 ± 0.0076** | 69.8 MiB | 3,600 | 226.8 |
| **C2/2000** | **3.2656 ± 0.0132** | 70.2 MiB | 6,600 | 216.6 |

Errors are ± 1 standard error over the 8 outer repetitions. Peak RSS is a
process high-water mark from `getrusage`; it is dominated by interpreter and
NumPy baseline (~69 MiB) and the **attributable delta is ~0.5–0.6 MiB**, so the
RSS column separates cells and horizons far less than the timing column does.

### Separated marginal effects (log seconds per program)

Because the design is balanced, cell and horizon are orthogonal and separately
estimable — which the old confounded split could not do:

| effect | `v1_reduced` | `v2_all_ticks` |
|---|---|---|
| **cell** (C2 − C1) | +0.010232 ± 0.006110 | **+0.012600 ± 0.003345** (×1.0127) |
| **horizon** (2000 − 1000) | +0.394685 ± 0.006006 | **+0.464062 ± 0.002646** (×1.5905) |
| interaction | −0.017027 ± 0.011662 | **+0.002491 ± 0.008180** |
| beta (horizon effect / log 2) | 0.569410 ± 0.008665 | **0.669500 ± 0.003817** |
| beta, v1-style confounded contrast | 0.554648 ± 0.016695 | 0.651300 ± 0.006500 |

**The cell effect is not separable from zero at 2 SE for either runner**
(+0.0126 ± 0.0033 is ~3.8 SE for v2, so it is *weakly* separated, but the
implied ×1.013 is operationally negligible). The horizon effect is large and
sharply estimated. The interaction is not separable from zero for either.
Note the confounded contrast **understates** beta by ~0.018 for v2, which is
exactly the bias the balanced design was ordered to remove.

### The honest factor against v1's sampled schedule, with its measurement error

Paired on the same coordinates, geometric mean over 4 groups × 8 reps:

| contrast | factor | 95% CI |
|---|---|---|
| **v2 over v1, overall** | **×1.1302** | **[1.1144, 1.1463]** |
| v2 over v1, N_max = 1,000 | ×1.0917 | [1.0779, 1.1057] |
| v2 over v1, N_max = 2,000 | ×1.1701 | [1.1628, 1.1775] |

Looks per trial rise by ×1.20 at N_max 1,000 and ×1.10 at 2,000, so **the
corrected all-look schedule costs materially less than its extra looks**: 20%
more looks buy 9% more time.

**Boundaries on reading this.** The CI is the spread of *this* harness on *this*
host across 8 repetitions; it is not a guarantee about a different executable,
a different host, or a contended host. Repeated-run variability and within-run
timing interval are different uncertainty scopes. The host was reported
contended in the owner's 02:16 update. **No tier admissibility or resource-gate
discharge is claimed from these numbers**, and the projection block the tool
prints is development output, not clearance.

### The vendored author reference, timed on the same coordinates

```
.venv/bin/python experiments/live_ab_validation/reference/panel.py --resource --inner 20
# -> results/live_ab_validation_v2/resource_check_delivered/reference_timing.json
```

| group | ms/program (median of 20) | peak RSS |
|---|---|---|
| C1/1000 | 15.889 | 70.0 MiB |
| C1/2000 | 34.362 | 72.5 MiB |
| C2/1000 | 16.018 | 72.6 MiB |
| C2/2000 | 34.586 | 72.6 MiB |

**The reference is roughly 7.8× the delivered primary at N_max 1,000 and 10.6× at
2,000.** It is a per-element root-find through a C++ boundary called from a
Python loop. This cost is **reported beside** the primary's and is deliberately
**not** in any budget ladder or tier decision: the reference decides nothing, so
it gates nothing. It lives in `reference/` rather than in `vresource_check.py` so
the harness keeps no dependency on it.

---

## 6. TASK 6 — the v2 actual-live snapshot, with v1 preserved

Ruling: root disposition decision 2; revision 16 item 75; issue 12 comments 5754149408 and 5754619899.

```
.venv/bin/python experiments/live_ab_validation/vsnapshot_v2.py --write
.venv/bin/python experiments/live_ab_validation/vsnapshot_v2.py --verify
```

New `experiments/live_ab_validation/pinned_v2/`, read-only (mode 444), with
`PINNED_V2.json`. Source commit **`a266c6201e3c94fc50c6646ca741e5e1da9b409b`**,
refusing to build if `experiments/live_ab/` has uncommitted changes (it did not).

| module | v2 sha256 | v1 sha256 | changed |
|---|---|---|---|
| `lab_monitor.py` | `94d70b8d…2c2af91` | `8c20e072…7aebeced` | **yes** |
| `lab_enclosure.py` | `da1b300d…9290d74` | `47c52312…dc578d0a` | **yes** |
| `lab_reference_rule.py` | `8f8b69f0…fb9ee6fd` | `6219cc64…20ae360b1` | **yes** |

**All three changed since v1's pin at `5776877…`**, so the re-snapshot was not a
formality — v1's snapshot is genuinely not the current live rule.

`--verify` reports **6/6 OK** (3 v2 + 3 v1). v1's `pinned/` is byte-identical and
`git status --porcelain experiments/live_ab_validation/pinned/` is empty.

`PINNED_V2.json` carries forward the wording corrections verbatim:
`stopped_roster` (proportional ordering does **not** identify a fixed-roster
effect at an outcome-selected stopping time; the two-order (+1,−1) witness has
roster mean 0 and expected stopped-prefix mean .5), `exact_feasible_set`
(epsilon supersets are **conservative enclosures**, not exact feasible sets at
every boundary), `v1_did_not_validate_11` (v1 **compared against and tested
against** the #11 pin; it did not validate it), and
`timing_summaries_not_invariant`. It also states what **paired** means: replaying
the same seed coordinates and latent draws across versioned algorithms, not
reusing the old snapshot as v2's only reference.

**The comparison grid was not run**, per instruction. `vsnapshot_v2.py` builds
the snapshot and nothing else.

A second exemption was needed in `vfixtures.scan_sources_for_forbidden_paths`:
`vsnapshot_v2.py` must **name** the three live-rule modules to copy their bytes.
The exemption is **static-scan only** — the dynamic half of F16 still applies to
every module — and `test_the_snapshot_builder_never_imports_the_forbidden_tree`
parses the AST to confirm it never imports them or uses a dynamic-import call.
The guard caught this correctly on first run; it was not silently widened.

---

## 7. Scientific rules: unchanged

No margin, no alpha (`.00625`), no rho (100), no delta (0.03), no `n_min` (100),
no gate, no episode stopping, deadline or finalization rule, no cell, no weight,
no delay rule, no seed, no estimator, no flag rule, no positive control.
`tests_validation.TestV2EventSchedule.test_no_scientific_rule_moved_with_the_schedule`
still passes. v1's frozen values in `PROTOCOL.md` and `cells.json` are untouched,
and nothing under `results/live_ab_validation/` was read for writing, moved or
deleted.

---

## 8. BLUNT LIST — what did not close

1. **My cross-check's stitching constant is wrong and I did not fix it.**
   −23% at v=10 shrinking to −0.27% at v=5,000, in the **narrower** (unsafe)
   direction, against the authors' `poly_stitching_bound` for the same published
   object. Per instruction I reported rather than reconciled. Until it is
   resolved the cross-check validates only the centre and the clock.
2. **The finest sensitivity is deferred, not repaired.** Both defects stand:
   unreachable completed-prefix states, and tick-keyed `_look_fractions` that
   cannot represent sub-tick decision state. Two permanent expected failures
   record this. `PROTOCOL_V2.md:114–116` still contains the false "exact union
   over every admissible order" claim, and `PROTOCOL_V2.md:95` still carries the
   blanket "Not one deposited ADAPTER number…" wording. **I did not edit
   `PROTOCOL_V2.md`.**
3. **Prose corrections not yet applied to `PROTOCOL_V2.md`.** The root's list —
   "every affected deposited number was understated" (lines 134–135, too broad),
   "v1 validated #11" (261–265), the prototype speed ratios and the
   "resource item discharged" label (559–575, 601–602), and the
   "all methods receive precisely the same looks" claim (119–120) — are
   **recorded in `PINNED_V2.json`'s carried-forward corrections but are still
   present in `PROTOCOL_V2.md` itself.** That document needs its own version
   bump and I did not make one.
4. **`lab_data.py`'s stopped-roster target claim and `lab_enclosure.py`/`vcompare.py`'s
   epsilon-scope problem are unrepaired.** Both are outside
   `experiments/live_ab_validation/`, which I was scoped out of.
5. **The reference is measured on one demo trial only.** No width claim at our n
   or our tie mass. The comparison grid was not run and is not cleared.
6. **The resource receipt is `--pin tree`, i.e. uncommitted bytes.** It is
   reproducible only from this working tree until the coordinator commits. After
   the commit it should be re-run with `--pin <that commit>` to obtain a
   commit-anchored receipt; the two should agree, but that has not been checked.
7. **Peak RSS barely separates the conditions.** The ~0.5 MiB attributable delta
   sits inside interpreter noise, so the memory column supports "nothing grew"
   and not much more.
8. **The build is host-specific, and a decision is owed on the binary.**
   `_build/boundaries.cpython-312-darwin.so` is CPython 3.12 / macOS arm64 only,
   and rebuilding needs a 155 MB Boost download plus a C++ toolchain. On any
   other interpreter `eb_reference` raises `ReferenceUnavailable` and the
   reference tests **skip** rather than fail. No Boost or pybind11 byte is
   vendored into the repository.
   **It is not gitignored**, so as things stand the coordinator's commit would
   include a 356,208-byte platform-specific binary. Its SHA-256 and the exact
   sources and flags it was built from are in `MANIFEST.json`, so ignoring it
   and rebuilding via `vendor.py` loses no provenance. **I left the choice to
   the coordinator rather than adding a `.gitignore` rule**, since that file is
   outside my scope.
9. **No resource-gate discharge, no calibration, no freeze, no live clearance.**
   The owner's prior withdrawal and both earlier receipts stand. The prototype
   receipt in `resource_check/` is preserved and is still the wrong measurement
   for the delivered runner; it must not be quoted for it.
10. **I could not verify the two "not vendored" upstream files against anything
    but their own hashes**, since only `confseq.py` and `betting.py` appear in
    the root's key-hash list. `comparecast/__init__.py`'s hash rests on this
    session's fetch alone.
11. **Nothing was committed.** All work is uncommitted in the working tree, per
    the hard rule. The coordinator commits as `Yukang Zeng <ykzeng2019@gmail.com>`
    with no Claude trailer.
