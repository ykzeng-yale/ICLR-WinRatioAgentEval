# Root launcher review and shard specification — September 21, 2026, 10:22 cycle

**Full project 65% (change 0); separately bounded v1 90%.** Reviewed delivery `7a12acb28197e3b08677ebe1171bcaae520b0835`, including launcher first delivered at `b38eb45`. Latest owner update **10:18:42 UTC** reports zero live episodes, zero v2 calibration cells, no freeze/grid, nothing running, approximately 14 GiB available RAM and load 2.2/10 cores. Host values are attributed, not independently inspected.

## Received and accepted at bounded scope

The owner has read back `96c380c`, `d2e6ce4` and the current comments; the stale-feedback issue is resolved for this handoff. The launcher was delivered after the prior review's exact `1c13041` snapshot, so that review's outstanding status was time-bounded. We now explicitly acknowledge `vlaunch.py`, `T1_MANIFEST.json` and `T1_DRY_RUN.json` as received.

Root independently checks the fixed request and seven malformed requests: the intended 28,000 programs / 112,000 trials / 224,000 reference calls are accepted, and changed horizon, NaN, namespace, alpha, trial count, reference omission and allocation are refused. [Portable check and receipt](evidence/v2_launch_checks_20260921_1022.json) perform no trial/native call. The optional conformance runtime hook is removed, its stronger claims narrowed, and the prior one-draw smoke restored. The existing deterministic milestone and conditional ~2676-second resource-planning acceptance stand.

The launcher is a **manifest/refusal shell, not a runnable T1 executor**: its `--child` branch raises an explicit unimplemented error. Execution may be implemented now while remaining locked pending review; lack of launch clearance never required withholding reversible executor implementation. The owner asked root to choose sharding and completion receipts. The specification below answers that question completely.

## Frozen shard layout: implement now, do not execute the scientific grid yet

Use the [machine-readable root plan](../evidence/t1_shard_plan_20260921_1022.json): **56 shards, each 500 contiguous programs from one cell**, four trial indices 0–3 per program. Keep horizon 2000, namespace 0 replay coordinates, operational policy, tick-batched looks, both H/D references and preflight-only verification unchanged.

Order shards by ascending 500-program block number, then C1 through C8, skipping cells whose frozen allocation is finished. Blocks 0–3 include all eight cells; blocks 4–9 include C3–C6. This fixed order is independent of results, preserves the paired seed coordinates, and yields all 28,000 unique cell/program combinations with no gaps or duplicates. It does not authorize using a partial cell set as a completed study.

Per shard: **500 programs, 2000 trials, 4000 full-path reference calls, 6000 primary rows and 12000 reference rows** under the existing three primary constructions and three prefixes per H/D score. Totals: 112,000 trials, 224,000 calls, 336,000 primary rows and 672,000 reference rows. These are expected complete counts; observed attempts/failures are recorded separately and never silently replaced.

One serial child processes all shards under **one parent supervisor**, with cumulative caps 5400 seconds, 2 GiB sampled process-tree memory and 200 MiB total output. Do not reset caps per shard or launch a parent per shard. A shard can call the existing primary/reference logic with explicit indices and validated manifest membership; connect this route to the actual shard-aware admission check instead of the old smoke proxy or an unrestricted bypass. Do not rewrite the scientific estimator for this orchestration change.

The existing one-draw smoke at each shard entry is acceptable; do not add the optional conformance checker. An immutable source/config check links prior accepted deterministic evidence. The accepted resource projection already repeats per-run setup every ten measured programs; fixed 500-program shards need no new timing sweep. Actual full-job caps still control execution.

## Immutable completed-shard receipt contract

Write each shard into an attempt-specific partial directory. Only after both data files close successfully, counts/coordinate coverage reconcile, and hashes are computed, atomically publish a completion receipt and finalized shard directory. Never overwrite an existing completed receipt or delete an incomplete attempt. Root reads finalized shards only. A receipt is valid only with its matching files and complete status; a mutable live-progress file is not a completion receipt.

Each completed receipt includes:

- schema version, job/attempt/shard identifier and fixed sequence number; exact source commit, canonical manifest digest, root clearance reference when eventually granted, current scientific/source/config/loaded-reference/environment pins;
- cell, namespace, exact half-open program range, trial indices, horizon, prefixes, policy/schedule, alpha, both reference modes and the existing development/replay exposure label;
- planned and observed programs/trials/reference calls/primary rows/reference rows; unique coordinate coverage; attempted, completed, failed, skipped and missing counts. Errors are retained with their original messages and timestamps; missing/failed trials are not imputed into complete rows;
- UTC start/end, elapsed interval and cumulative job elapsed/counter snapshot; sampled resource scope and cumulative output bytes. Mark unavailable per-shard memory unknown rather than deriving it from a whole-job maximum;
- relative filenames, compressed and uncompressed sizes, SHA-256 digests and complete/partial status; link to any prior failed attempt without rerunning it.

Retain primary and reference records exactly as designed. Coordination summaries can report counts/resources/hashes without interim scientific-effect summaries; do not adjust design, order, stopping or collection from interim outcomes. Publish committed immutable completed shards with the owner's scheduled half-hour update; do not interrupt a valid run solely for status. Preserve all attempts. On a cap/error, stop the entire attempt, publish its failure receipt and partial inventory, and return it to root without retry/resume or tier change.

A final job receipt requires all 56 expected shard IDs exactly once, exact disjoint-union coordinate coverage, all counts/hashes/pins reconciled, successful supervisor completion and no cap event. `within_caps` or process exit zero alone is insufficient for scientific completion. Final paper/calibration acceptance remains independent of successful execution.

## Remaining repairs within the existing handoff

The [supervisor delta review](v2_supervisor_repairs_20260921_1022.md) assesses the prior named safeguards. Keep its narrowly identified remaining fixes with the executor; no new safety framework or broad experiment is requested.

Root finds the deposited T1 manifest was created from a dirty pre-commit tree and its `vpanel.py`/`vconformance.py` digests do not match current `7a12acb`. Preserve it as a historical draft, then commit final source and generate a new matching manifest/dry-run receipt. Bind the canonical complete execution spec (including allocation, program ranges, shard order, caps and accepted resource-ledger digest), not only the current empty `programs=[]` pin. Compare the reviewed manifest identity at launch rather than treating a reusable clearance string as the identity check. The source binding is for reproducibility, not an invented authentication requirement.

## Concrete next owner action

Implement the child executor and receipt contract now, with the narrow remaining supervisor repairs. Return one final exact source commit, matching manifest and dry-run, plus bounded orchestration tests using synthetic stub records to check shard counts/uniqueness, atomic completion, a failed shard, and cumulative-cap behavior. Those tests must not run the scientific grid or call native/model references. Reuse unchanged scientific witnesses and existing measurements. No further design question or permission is required to implement this specification.

**Scientific T1 execution remains uncleared at `7a12acb` because the child is not implemented.** Once the runnable source/manifest conforms, root will review it for one explicitly cleared attempt. Live collection still requires its separate freeze/serving review.

## Progress and integration

Reports, shard specification and status are integrated; no new empirical outcome enters the paper or release. All five current arXiv artifacts remain unchanged. Remaining **35 points**: Session60 prospective study 10 and CPU calibration acceptance 5; root accepted-results integration/final QA 10; author scientific/citation/AI and submission checks 10. A validated null or abstention is acceptable; a dry run or launcher receipt alone earns no study-completion credit.
