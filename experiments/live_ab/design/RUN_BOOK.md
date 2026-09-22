# Run book: ordered commands, prerequisites, refusals, resume and authority

**Version 1, 2026-09-22.** Authored under root's 2026-09-21 18:17 ruling: *"The run book states the
existing ordered commands, prerequisites, refusal/resume/failure-accounting rules and authority
boundaries."*

**This book describes what EXISTS.** Where a step has no implementation, it says so rather than
describing an intended one.

---

## 1. Authority boundaries — read before anything else

| action | who authorizes |
|---|---|
| offline preparation (roster stages 1–3, fixtures, documents) | **already authorized**; no permission cycle |
| **prefreeze model execution** (any server start or model call) | **explicit root review**, not yet granted |
| **trial episodes** | separate explicit root clearance, after the freeze |
| touching foreign processes (ports 8191/8193) | **never** — observe with `ps`/`lsof` only |
| disabling the production lock or weakening the sandbox profile | **never**, under any circumstance |
| write-once deposits (roster, arrival orders) | pending root's ruling on D1/D2/D4 |

## 2. Prerequisites

```bash
export TMPDIR=/private/tmp/labsbx     # protocol 5.7 item 2; ENFORCED, see §4
```

- Python: `.venv/bin/python`, CPython 3.12.13, numpy 2.4.1 (load-bearing: the arrival order is
  `Generator.permutation`).
- Sources present and hash-verified at `work/live_ab/sources/` (roster mode **EXT**).
- Host quiescence: **fails on presence** of foreign accelerator consumers. Check, do not wait for
  a quiet sample.

## 3. Ordered commands that exist today

```bash
# offline preparation status (read-only; outside the pinned harness by design)
.venv/bin/python experiments/live_ab_tools/freeze_status.py

# saved-environment digest verification (reads deposited bytes only)
.venv/bin/python experiments/live_ab_tools/check_environment_digests.py

# the test suites
.venv/bin/python -m unittest discover -s experiments/live_ab -p 'tests_lab_*.py'

# end-to-end dry run against the mock server (no real model)
cd experiments/live_ab && ../../.venv/bin/python dryrun_live_ab.py --scenario all
```

**Not yet implemented, stated as absent rather than described:** the anchor drill against the real
remote (only `--local-only` exists, which by its own docstring does not push or comment), and the
injected-decision rejection fixture.

## 4. Refusal conditions — every one fails closed

| refusal | trigger |
|---|---|
| TMPDIR mismatch | effective resolved temp dir ≠ `config.sandbox.tmpdir`; checked at the preparation entry point before the ledger |
| no retention sink | ledger cannot be created, or a prior ledger has an unresolved malformed tail |
| failed durable append | short or non-progressing write; the incomplete tail is **retained as evidence** |
| unloaded sweep | no explicit load observer supplied |
| invalid load coverage | observation does not evidence active load over the **verifier interval**; stops **immediately**, excludes no task |
| schema error | a v2 record with missing/null/nonfinite named endpoints; legacy aliases may **not** rescue it |
| acquisition mode | explicit or persisted `EXT` cannot resolve to S1, even when S2 is legitimately absent |
| acquisition integrity | a required source absent or off its pinned sha256, in **either** mode |
| write-once violation | any attempt to overwrite a deposited receipt |
| plumbing verdict | `receipt_mismatch`, `reconciliation_defect`, `chain_check_fail`, `reference_rule_disagreement`, `t4_payload_non_identity` |
| cap breach | wall-clock, RSS or output-byte cap exceeded |

## 5. Resume and failure accounting

- **Attempts.** `max_attempts = 1`; hard-cap outcome is terminal failure. Interruption is terminal
  failure unless orphan checks pass.
- **Auto-abort.** 10 consecutive infrastructure failures, counted in reveal order.
- **Shard contract.** Attempt-specific partial directory → reconcile counts, coverage and hashes →
  atomic rename. A completed receipt is **never** overwritten; an incomplete attempt is **never**
  deleted or reused.
- **Failed attempts are retained**, never deleted. Move aside as `<dir>_failed_attemptN`; `rm -rf`
  of a failed attempt destroyed two irrecoverable records earlier in this project.
- **Lock-acquisition failure** is an infrastructure/preparation event with its wait and error
  retained — **not** a task reference failure.
- **Load gaps.** A gap *between* attempts is a scheduling rule: stop dispatching, let load restart,
  resume once activity is evidenced. A gap *intersecting* a check invalidates that check, which is
  retained for diagnosis and never becomes a scientific exclusion.

## 6. Evidence conventions

- Cite the **deposited receipt**, never an uncommitted terminal run. This rule was stated once and
  then broken in the next cycle; it is in the run book so it is not a memory.
- Unavailable raw detail is labelled **unavailable**, never reconstructed. A narrative is not an
  all-attempt ledger.
- A check that cannot be performed is a **refusal**, never a pass.
