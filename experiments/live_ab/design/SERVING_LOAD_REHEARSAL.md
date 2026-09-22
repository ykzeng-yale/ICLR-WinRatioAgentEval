# Serving, load and rehearsal: the finite specification

**Version 1, 2026-09-22.** Written for root's standing critical-path item: *a finite
serving/load/rehearsal specification with an actual continuous-load observer.* The observer now
exists (`experiments/live_ab/lab_load.py`); this document is the specification it serves.

**Finite means every count is a number here.** Where a number is not yet pre-registered in
`config.json`, this document says so and says whose call it is. Nothing here authorizes execution:
prefreeze model execution still requires explicit root review, and none has been granted.

---

## 1. Serving — exactly what runs

| | coder | T3 |
|---|---|---|
| port | 8091 | 8092 |
| alias | `qwen2.5-coder-7b-instruct-q4km` | `t3-candidate` (granite-3.3-8b-instruct) |
| args | `config.json:llama_args`, verbatim | same |
| processes | **1** | **1** |

Total server processes for a run: **2**. Start attempts per server per run: **1**. Restarts on
failure: **0** — a server that does not reach readiness ends the run; it is not retried into a
different warm state.

**Readiness** is three conditions, all required, in this order:

1. `/health` returns ok.
2. The served model identity matches the pinned alias, repo, revision, file and `sha256_expected`
   (`config.json:servers`). A mismatch is a refusal, never a warning.
3. `assert_worker_startup` passes (`lab_prepare`), and `TMPDIR` is the prescribed
   `<TMP>/labsbx` (protocol 5.7 item 2, enforced at both real entry points).

**Before any of that**: the host quiescence gate of protocol 5.7.2, which **fails on the presence**
of a non-baseline foreign accelerator consumer, regardless of its CPU percentage. It is not a wait
loop and there is no quiet-sample override.

## 2. Load — the regime the reference sweep runs under

Protocol 3.2 rule 4: the reference sweep must run **under the trial's load regime** — a 1,024-token
generation on the coder server. The sweep itself makes no model call; its work is sandboxed verifier
execution. So the contention it must be measured under has to be **offered deliberately**, by a
generator that exists for that purpose.

| parameter | value | why this and not the alternative |
|---|---|---|
| concurrent load generations | **2** | equals `execution.workers = 2` and the server's `-np 2`. **Rejected: 1 generator** — it understates contention, and a reference threshold calibrated under half the real load excludes fewer tasks than the trial will, in the direction that looks successful. |
| tokens per generation | **1,024** | protocol 3.2 rule 4 names this figure. |
| target | coder, 8091 | the server the trial's episodes contend for. |
| sampling | `temperature 0`, `seed 0` | the load must be reproducible work, not a source of variation. |
| cadence | back-to-back, no idle between generations | a gap between generations is unobserved time (§3), and the trial does not pause between episodes either. |
| transport | `stream: true` | **a declared deviation** — see below. |

**The declared deviation.** Load requests stream; the trial's own client (`lab_client`) sends
`stream: false`. The *work* offered to the server is identical — same prompt, same 1,024 decode
tokens, same model, same slots. The *reply transport* is not. Streaming is what makes activity
observable at all (§3), so the choice is between a load regime that differs from the trial in reply
transport and one whose continuity cannot be evidenced. **This is root's ruling to make**, and it is
recorded here rather than buried in the module.

## 3. The observer — what an observation means

`lab_load.ContinuousLoadObserver` produces the observation `lab_prepare.run_reference_sweep`
requires, and `_coverage_verdict` decides whether its windows contain the attempt.

**A window means:** an interval throughout which the server is *evidenced* to have produced output,
never idle for longer than the window's own `max_interior_gap_s`. The evidence is token arrivals
from a streamed generation: each arrival is production at that instant; between two arrivals the
state is unobserved.

**Why sampling is not used.** Polling `/slots` or `/metrics` every 200 ms yields instants at which
the server was busy and says nothing about the 199 ms between them. Root, 2026-09-21 21:50: *"A
series of active samples cannot become proof of continuous activity merely by shrinking the ends."*
No arithmetic applied afterwards repairs a sampled series, so none is applied.

| tolerance | value | status |
|---|---|---|
| `max_interior_gap_s` | **0.5 s** | **not pre-registered.** `config.json` is under the three-way verbatim contract and this module does not touch it. Pre-registering it is root's call. |
| endpoint error floor | **0.010 s** | same status. |
| jitter probe interval / minimum samples | 0.010 s / **20** | same status. |

**Splitting, not smoothing.** An interior gap larger than the tolerance splits the window in two. An
attempt straddling the gap is then **not covered**, the sweep stops immediately, and the raw attempt
is retained — the correct outcome, because during that gap we do not know what the server was doing.

**Partition by generation first.** With two concurrent generations the arrivals interleave
(`g0, g1, g0, g1, …`). Splitting at every change of generation id would end every window after one
arrival and report **no active load at the moment the server is busiest** — silently, and in the
direction that looks safe. Windows are therefore built per generation and unioned by the consumer.
This was a live defect in the first version of this module, found by writing the two-worker case
down; a single-generator fixture passes either way.

**The endpoint bound is measured, and its limit is stated.** A probe thread wakes on a fixed schedule
throughout the run and records its worst lateness; the bound is `max(floor, worst observed)`. That is
an **empirical maximum under concurrent load plus a floor — not a proof**. It does not bound a kernel
stall longer than any sampled, and it does not bound socket buffering at all. Offered as the
justification the contract asks for; accepting it, replacing it with a declared constant, or
pre-registering it is root's ruling.

**Refusals are observations of absence, not silence.** No arrivals, an unhealthy source, or fewer
than 20 probe samples all yield `active: false` with a reason. A malformed arrival series raises
instead — a broken instrument is not a quiet server.

## 4. Rehearsal — the finite sequence before the freeze

Each step has a pass criterion and a failure consequence. **No step is authorized to run yet**;
steps 3–7 are model execution.

| # | step | pass criterion | on failure |
|---|---|---|---|
| 1 | host quiescence (5.7.2) | no foreign accelerator consumer **present** | stop; do not wait |
| 2 | containment probe (5.7 item 3) | 15/15 repo-resident attempts denied; no concurrent peer run dir | **stops the freeze** |
| 3 | start 2 servers | readiness §1, all three conditions | stop; no retry |
| 4 | load-up | ≥ 20 jitter samples **and** ≥ 1 window, both generators healthy | stop; diagnose |
| 5 | rehearsal sweep, **6 smoke tasks** | every attempt covered; digests reconstruct from the ledger | stop; the sweep is not usable |
| 6 | reference sweep, **the full roster** | 568 attempted (pre-exclusion) → 565 after the 6 smoke → **564** after smoke and 2 duplicates (protocol 3.3 line 630, staged bounds) | retained, refused, diagnosed |
| 7 | calibration | `config.json:prefreeze.calibration_plan` — 5 repetitions × 6 smoke tasks × 2 workflows × 2 models × 2 concurrency levels = **240 episodes** | stop; recorded |
| 8 | freeze | all **26** bundle keys present, no null and no `unknown` | `build_freeze_bundle` fails closed and names every hole |

Steps 5 and 6 both run under §2's load; step 4 is what establishes that the load exists before either
of them starts. A sweep that begins without a live observer is refused at the entry point, by
construction and not by discipline.

## 5. What this specification does not cover

* **The anchor drill** — still open on root's critical path, unaddressed here.
* **Any number in §3** — described, justified, and *not* pre-registered.
* **Execution authority** — unchanged: prefreeze model execution needs explicit root review, and the
  host is currently treated as occupied.
