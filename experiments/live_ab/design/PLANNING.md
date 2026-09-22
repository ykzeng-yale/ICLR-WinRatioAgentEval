# Planning: accepted CPU evidence and the bounded prefreeze/trial resource plan

**Version 1, 2026-09-22.** Authored under root's 2026-09-21 18:17 ruling: *"The planning artifact
records accepted CPU evidence and the bounded prefreeze/trial resource-and-attempt plan."*

---

## 1. Accepted CPU evidence this study rests on

Bound by digest, not restated. All independently accepted by root.

| evidence | scope | acceptance |
|---|---|---|
| T1 calibration, 112,000 trials | namespace 0; coverage and error behaviour | accepted, **integrated and packaged** (Appendix O / Table 10) |
| Coarse power curve, 80,000 trials | namespace 3; five μ_h rungs | accepted as **descriptive**, provenance-qualified, **not integrated** |
| Fine ladder, 48,000 trials | namespace 4; six rungs, outcome-informed | accepted as **exploratory**, **not integrated** |
| Certificate ablation | 32,000 **unique paired coordinates**, 64,000 evaluations | accepted **post-hoc exploratory**, not integrated |

**Carried limitations.** The coarse and fine panels have retrospective source binding. The
ablation re-evaluates the *same* draws and is never pooled with its original arm. None of this
transfers to the live study: it is CPU-simulation evidence about the estimator, not evidence about
agents.

## 2. Prefreeze resource plan

The operative plan is `results/live_ab/PREFREEZE_EXECUTION_PLAN_20260921_1910.json`
(`EFFECTIVE_PLAN`); superseded figures are quarantined there under `NONOPERATIVE_HISTORY`.

| item | episodes | logical calls | status |
|---|---:|---:|---|
| 1 serving build, manifest, golden capture, format conformance | — | 10–24 | request list **pending** |
| 2 counter semantics | — | **4** | fixed (both servers, non-streamed + streamed) |
| 3 duration calibration | **240** | 360–600 | fixed grid 5×6×2×2×2 |
| 4 side-by-side, 30 pairs × 4 contrasts | **240** | 300–420 | fixed; no paired reuse |
| 5 loaded reference sweep | — | **pending cadence** | ≤ 2,260 verifier attempts |
| 6 dress rehearsal | ≤ **32** (≤16 pairs) | — | capped; plus an injected-decision fixture |
| 7 anchor drill | 0 | 0 | offline |
| 8 downloads | 0 | 0 | no weight download needed |
| **items 3+4 subtotal** | **480** | **660–1020** | consistency-checked at file generation |

**240 means EPISODES.** Protocol 5.8(3) and the fixed grid determine the unit; finding N21's word
"calls" is a documented **unit erratum**. Logical calls are **not** wire requests — retries,
recovery, failures and unknown usage are accounted separately.

**No grand total is stated**, because items 1 and 5 have pending counts. Stating one would be
false precision.

## 3. Attempt and usage accounting

- **All-attempt ledger.** Every attempt is recorded including discarded work: item 2's
  deliberately abandoned non-streamed generation, its streamed probe, every rehearsal episode
  whose success outcome is never used, and the rule-4 load generations.
- **Prefreeze tokens are reported separately** and excluded from every trial total (protocol 5.8).
- **Retention is enforced, not promised.** `lab_data.AttemptLedger` writes durably, refuses short
  writes, and `lab_prepare` refuses to start without a sink or to continue past a malformed tail.
- **Immediate stop.** A failed or invalid load observation stops preparation before the next
  attempt; the raw attempt is retained and **no task is excluded** on its account.

## 4. Trial resource plan

| quantity | value |
|---|---|
| workers | 2, one OS process per episode |
| servers | 8091 (Qwen2.5-Coder-7B q4_k_m), 8092 (Granite-3.3-8B Q4_K_M) |
| model bytes verified | 4,683,073,536 and 4,942,873,344, both matching frozen sha256 |
| weight download needed | **none** — both installed and verified |
| max attempts per episode | 1; hard-cap outcome is terminal failure |
| auto-abort | 10 consecutive infrastructure failures, counted in reveal order |
| host | arm64-darwin, Apple M5, 10 logical cores, 32 GiB |

## 5. Capacity, and why nothing is running

Protocol **5.7.2 rejects non-baseline foreign accelerator consumers on PRESENCE**, regardless of
an instantaneous 0% CPU reading. Foreign DTR-AgentEvals servers hold ports 8191/8193 on this host.
The gate therefore fails on presence and **no quiet sample can clear it**. Latest capacity
observation: `results/live_ab/CAPACITY_RECEIPT_20260921_1749.json`.

**Live episodes executed: 0.** No model call, server startup or fault injection has occurred.

## 6. What this document does not do

It grants no clearance and claims no readiness. Prefreeze model execution and trial execution each
require their own explicit root review; this artifact only records what the plan costs and what
evidence it rests on.
