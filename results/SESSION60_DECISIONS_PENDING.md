# Session 60 — decisions pending

**One page. Every number here is read from the receipt named beside it; nothing is retyped.**
Head `1524632`. **20 commits** since the last root comment (2026-09-22 07:04:37Z).

---

## Decision 1 — the execution lock. *(open since 2026-09-22 13:23; a test is red on it)*

**Protocol 5.7 item 1:** an exclusive `flock` on **one lock file**; *"at most one generated program
exists and runs at any instant."* The hazard it names is a Seatbelt writable directory **shared by
every run on the host**, holding hidden tests and the nonce sentinel in clear text during
verification. The property is host-wide.

**Measured** (`results/live_ab/LOCK_TOPOLOGY_v2.json`): **5 distinct lock files**, `conforms=False`,
**2 implementations** (`lab_data._ExecutionLock`, `lab_worker.ExecutionLock`).

- **Covered:** the two workers *within* a trial share `ctx.paths.sandbox_lock`.
- **Not covered:** two trials concurrently; a reference sweep beside an episode worker.
- **Has it bitten?** No — 0 trial episodes and 0 calibration episodes have ever run. Latent.

| your answer | what I do | cost |
|---|---|---|
| **one host-wide file** | point `_trial_paths` and `lab_data` at `<WORK>/sandbox.lock`, deposit a receipt showing five collapse to one | one line + a receipt; `tests_lab_isolation` goes green |
| **per-trial is intended** | mark `ExecutionLockConformanceTests` `skip` citing your ruling | one line; protocol 5.7 item 1's wording is then the thing that is wrong |
| **silence** | change nothing; the test stays red | `tests_lab_isolation` 24 tests / 1 failure, by intent |

**Why I have not just done it:** it changes a production path the orchestrator serialises into every
job, and `TrialPaths.sandbox_lock` may be per-trial deliberately. Conforming to explicit protocol text
*looks* like a free call, which is exactly when I should not make it alone.

## Decision 2 — `TrialPaths.anchors`. *(open since 2026-09-22 ~09:18)*

`.gitignore` line 26 ignores `work/`; the harness puts anchors under `work/`; `git add` therefore
refuses the anchor file. This blocks the production anchor transaction **and** keeps the
time-sandwich audit from ever seeing a real receipt pair.

**Any path I pick is a design decision about where anchors live, so I will not default it.**

---

## State

- **Trial episodes 0 · calibration episodes 0 · alpha spent 0.**
- **Freeze 14 of 26 keys** (`FREEZE_REACHABILITY_v3.json`): 2 resolvable-now (pin decisions yours),
  1 offline-work-owed, 9 execution-blocked.
- **Host:** audited gate reports 0 foreign consumers at every observation; each is one instant, not an
  interval.
- **Suites:** ten pass; `tests_lab_isolation` is **red by intent** on Decision 1.
- **Nothing is running.** No server, no model, no episode, no lock held.

## What I did while waiting, newest first

Each landed as its own commit with a receipt; this is a pointer list, not a re-report.

- **index-claim audit** — 30 cited receipts present, 27 numeric claims checked, **1 real mislabel
  corrected** ("identity" vs `saved_execution_spec_digest`). `INDEX_CLAIM_AUDIT_v3.json`
- **audit self-test** — 6 positive detected, 6 negative silent; found a third `relative_to`
  display-field defect on its first run. `AUDIT_SELFTEST.json`
- **four-detector tool audit**, tools tree and production tree. `TOOL_AUDIT_v12.json`,
  `PRODUCTION_AUDIT_v7.json`
- **two-worker exclusion fixture** — verdict `PASS`, 16 attempts paired, 15 controlled denials.
  `TWO_WORKER_CONTAINMENT_20260922T141527Z.json`
- **licence evidence retrieved** under your standing authorization. `LICENSE_EVIDENCE_v2.json`
- **freeze holes priced** into resolvable-now / offline-owed / execution-blocked.
  `FREEZE_REACHABILITY_v3.json`

## Corrections I posted against my own earlier claims

- *"both trees clean on all four detectors"* — false for the production tree (27 literal checks).
- *"the production lock"* — there are five lock files; my fixture exercised one of them.
- *"over 2,102 lines"* — the receipt said 2,127; I typed it instead of reading it.

---

*This file exists because a returning reader would otherwise face ten long issue comments with the
decisions buried in them. It adds no claim that is not already in a receipt. **Say the word and I
delete it.***
