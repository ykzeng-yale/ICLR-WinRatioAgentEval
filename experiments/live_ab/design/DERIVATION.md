# Derivation: every Appendix A value, its rule, and the inputs that produced it

**Version 1, 2026-09-22.** Authored under root's 2026-09-21 18:17 ruling: *"The derivation
artifact must show final roster/exclusion/group counts, resulting horizon and conditional gate
arithmetic, plus timeout/cap formulas with measured inputs explicitly pending until available."*

**Nothing here is a measurement.** Every value is either (a) fixed by the frozen protocol, (b)
derived from committed offline counts, or (c) explicitly **PENDING** a measurement that has not
been authorized. No value is estimated, interpolated or carried over from a different panel.

---

## 1. Roster and exclusion counts

Source: `results/live_ab/ROSTER_STAGE1_20260921_1830.json`, executed offline, no model call.

| quantity | value | status |
|---|---:|---|
| candidate tasks | 1,138 | **final** (sources verified byte-for-byte) |
| S1 candidates | 591 | **final** |
| S2 candidates | 547 | **final** |
| roster mode | EXT | **final** (mbpp_full verified; protocol 3.1) |
| prospective exclusions, rules 1–3 | 8 | **final** |
| — out_of_design_smoke_task | 6 | final |
| — duplicate_prompt | 2 | `mbpp_full/217`, `mbpp_full/928` |
| — no_entry_point | 0 | final |
| — unparsable | 0 | final |
| rule-4 exclusions (reference sweep) | — | **PENDING**: requires the loaded sweep |
| **n_S1 final** | ≤ 591 | **PENDING rule 4** |
| **n_S2 final** | ≤ 539 | **PENDING rule 4** |

The duplicate rule is applied against **all** S1 tasks including HumanEval (protocol 3.2 item 2).
Widening it from the previous `benchmark=='mbpp'` scope changed **no count** on these sources.

## 2. Horizon arithmetic

Rule (protocol 3.3, `config.roster.n_pairs_rule`):

```
n_pairs = floor(n_S1 / 2) + floor(n_S2 / 2)
```

It is **never** `n_total // 2`: pairs form inside a stratum and each stratum keeps its own leftover.

| quantity | value | status |
|---|---:|---|
| n_pairs **ceiling** | **564** | final upper bound: `floor(591/2) + floor(539/2) = 295 + 269` |
| n_pairs final | ≤ 564 | **PENDING rule 4**, which can only remove |
| `monitor.n_max` | = n_pairs | **PENDING**; `lab_monitor` refuses unless equal |
| leftovers | `n_S1 % 2 + n_S2 % 2` | derived with the roster |

**Values that must not be asserted.** 568 and 565 appear in older test fixtures as *pre-exclusion*
and *smoke-only* figures. Neither is attainable: the ceiling from the actual sources is **564**
before rule 4 removes anything.

## 3. Conditional gate arithmetic

Fixed by the frozen protocol and **preserved unchanged**; not re-derived here.

| quantity | value |
|---|---|
| `alpha_program` | 0.05 |
| `alpha_trial` | 0.0125 |
| `alpha_gate` | 0.00625 |
| `delta` (success guardrail) | 0.03 |
| `n_min` | 100 |
| `rho` | 100.0 |
| `variance_process` | `n` (forced by thm:normal_cs) |
| deploy rule | `L_hierarchy > 0 AND L_success > −delta` **at the same look** |
| harm rule | `U_hierarchy < 0` |
| decision order | `harm_keep_incumbent`, then `deploy_candidate` |
| tie rule | strict `>` tolerance, so exact equality is a tie |

Alpha is **not reallocated on deferral** (`config.alpha_not_reallocated_on_deferral`).

## 4. Timeout and cap formulas, with measured inputs pending

Rules are predetermined (protocol 5.6, `config.execution`). Applied **once**, with no
performance-based retuning.

```
c_max              = max single-call duration over the FIXED 240-episode calibration sample
request_timeout_s  = max(180, 30 * ceil(4 * c_max / 30))
episode_hard_cap_s = 4*(3*request_timeout_s + server_recovery_s + 6)
                     + 3*(sandbox_timeout_s + max_lock_wait_s) + 60
```

| input | value | status |
|---|---:|---|
| `server_recovery_s` | 180 | fixed |
| `sandbox_timeout_s` | 10.0 | fixed |
| `max_lock_wait_s` | 120 | fixed |
| `c_max` | — | **PENDING**: the calibration has not run and is not authorized |
| `request_timeout_s` | — | **PENDING c_max** |
| `episode_hard_cap_s` | — | **PENDING c_max**; `config` marks it computed-never-typed |

The calibration sample is frozen **before** measurement (5 × 6 × 2 × 2 × 2), so `c_max` cannot be
tuned by resizing the sample.

## 5. Reference-exclusion threshold

```
reference_timeout threshold = REFERENCE_TIME_FRACTION * REFERENCE_VERIFIER_WALL_LIMIT_S
                            = 0.5 * 5.0 = 2.5 s
```

A hardcoded protocol constant, deliberately **not** `config.sandbox.timeout_s` (10.0). The
certified interval for load coverage is the **verifier call inside the lock**
(`live_ab/attempt_interval-v2`), not the lock wait.

## 6. What this document does not establish

- No roster is deposited. `roster_sha256`, `task_content_sha256` and `arrival_order_sha256`
  remain open, and the write-once artifacts are **not** written.
- Every PENDING row above is pending a measurement that is **not authorized**, not one that was
  attempted and failed.
- Values fixed by the protocol are transcribed, not re-derived; the protocol is authoritative.
