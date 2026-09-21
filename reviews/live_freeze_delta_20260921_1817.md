# Bounded live-freeze preparation review — 2026-09-21 18:17 cycle

Reviewed exact owner head `aa7eded`, capacity delivery `85f6d16`, and `FREEZE_STATUS_20260921_1815.json` (actual generation 18:17:43 UTC). Compared statistical-core source bytes with accepted main `7b4d17f` and its `pinned_v2/PINNED_V2.json`. Read-only review: no simulations, model calls, probes, weight hashing/downloads, server operations, or broad test suite. Only this reviewer report is written.

## Decision

Accept the status as a useful structural inventory and accept the exact statistical-core identity reconciliation below. It does **not** establish a completed freeze or authorize live/calibration episodes. The status itself correctly reports no trial or calibration episodes and no completed freeze. The next useful work is the existing offline roster, evidence, and consolidated planning package; it need not wait for foreign DTR servers.

## Statistical-core identity is closed for this delivery

Independent SHA-256 over Git blobs at `aa7eded` gives:

| Live source | SHA-256 | Comparison |
|---|---|---|
| `experiments/live_ab/lab_enclosure.py` | `42f1b57dff684988cc0725bc0e64d982cd4b8b24f7ff68198c77d8d8a53966c6` | Exact main bytes and accepted CPU v2 manifest pin |
| `experiments/live_ab/lab_monitor.py` | `94d70b8d766376a697271087a1879de32170d4827bb25211c33f550232c2af91` | Exact main bytes and accepted CPU v2 manifest pin |
| `experiments/live_ab/lab_reference_rule.py` | `8f8b69f01e09a92ca77a665e19bbd8f8eeba0ceef1ddab0bc3cb09b0fb9ee6fd` | Exact main bytes and accepted CPU v2 manifest pin |

The CPU manifest records source commit `ddebb68c0571d02d9fac8f1ea55cab22857b882c`. No new semantic mismatch in these three files is found, and their unchanged CPU review should not be reopened. This is the operational live adapter, not the experimental no-certificate ablation. Its accepted qualifications still apply: epsilon-based conservative enclosures, running conditional-mean target rather than a fixed-roster effect at an outcome-selected stop, and separate full-information comparison scope. Byte identity does not independently validate the serving/worker/event-provenance path. `lab_orchestrator.py:1320–1388` supplies the live replay/reference wiring, whose real-server evidence remains part of the existing prefreeze rehearsal.

## What 9/26 actually measures

`lab_common.py:307–357` checks the required key set and recursively rejects `None` or the literal string `unknown`. It does not inspect the semantics of referenced documents, validate the evidence behind their hashes, or reconcile a hashed config with its remaining null values. Therefore 9/26 means **nine structurally supplied components**, not 34.6% scientific readiness and not a replacement for the project readiness rubric. The 17 absent components and the incomplete gate are accurately exposed. A later 26/26 structural result will still require review of the concrete artifacts and internal consistency.

The 240-episode status wording is incomplete: the JSON describes the calibration dimensions as “MODEL CALLS,” whereas `protocol_FINAL.md:1198–1204` explicitly specifies **episodes**, with a repair episode containing 2–4 calls. Do not use 240 as a total request/usage budget.

## Ranked remaining work within the existing protocol

1. **Complete the offline design inputs now.** Deposit pinned dataset/content evidence and prospective exclusions; perform the prescribed twice-per-reference sandbox sweep with all attempts/errors retained; finalize the task/stratum roster, actual pair horizon and immutable arrival order. The pair horizon is derived from the final roster, not the loose pre-exclusion bound. Freeze the AB/BA assignment algorithm and write-ahead coin procedure; do not pre-draw realized dispatch coins merely to fill a status field.
2. **Deposit the offline environment and execution evidence.** Record the sandbox profile, containment result, installed interpreter/package lock, permitted host identity and license evidence. Prepare the installed serving executable/build/flags inventory offline; live golden properties and actual process manifest remain dependent on the owned servers. CPU-only work should respect current CPU/RAM capacity and log contention, but does not require a foreign model endpoint.
3. **Consolidate the already specified prefreeze work into one finite run plan and ledger before model execution.** Reuse the protocol and config in compact indexed derivation/planning/run-book artifacts rather than inventing another study. In addition to the fixed 240-episode duration calibration, protocol §5.8 requires serving/receipt/template checks, non-streamed and streamed counter probes, solo and side-by-side calibration for **all four contrasts**, the full real-server fault/recovery rehearsal, verifier/builder evidence, and a real-remote anchor drill. State the full intended episode/request coordinates, any justified reuse between calibration records, effect-independent limits and abort rules, all attempts/failures/unknown usage, and resource accounting. The 240 grid alone does not close the prefreeze chain.
4. **Use the owned serving configuration when the existing gate permits it.** Capture actual serving manifests and golden objects, execute the bounded prefreeze plan, derive timeouts/caps from its fixed formulas, close and hash the prefreeze chain, then submit the complete internally consistent freeze bundle before any design outcome. Preserve the already fixed scientific margins/error allocation, task exclusions and trial-order/deferral rules; a null or abstention remains a legitimate result.

## Capacity and server interpretation

The capacity receipt is one observation at **17:49:46 UTC**, not evidence of a continuously quiescent window. The prospective config uses owned ports **8091/8092**. DTR ports **8191/8193** are foreign competing processes, not a serving identity that this experiment needs to adopt or probe.

Protocol §5.7.2 rejects nonbaseline foreign model servers on their **presence**, even at zero sampled CPU; a proposed low-load window does not itself satisfy that gate. Do not signal or alter those processes. The receipt's inference from 0.0% sampled CPU to “not currently serving” is unsupported: sampled CPU does not establish accelerator inactivity or serving status. Correct the description to the observed CPU sample with serving/accelerator activity unknown. This does not reverse its reported nonquiescent verdict.

No new collection or safety architecture is requested by this review. Close the existing offline artifacts and full prefreeze accounting first; keep the accepted CPU core identity closed, and review one concrete completed freeze package rather than treating successive status counts as scientific progress.
