# Independent ablation provenance and attempt-ledger review — 2026-09-21 17:37

Reviewed main `7b4d17ffe8c60b7738a9fd9d4e5cede2d95ba123`, raw ablation delivery `6bdefd1`, and discarded-measurement clarification `03dc070`. Scope: both disabled executions, hashes/coordinates, source/config/runtime evidence, resource ledger and the historical mapping. No simulations, model/native calls or outcome estimates were run. Root owns scientific interpretation, paper and readiness status.

## Acceptance recommendation

**Accept the independently verified disabled-arm artifacts and two-attempt row reproducibility for this explicitly post-hoc paired mechanism analysis.** The complete disabled runtime binding now includes the actual driver, variant and runtime laws with consistent namespace3, repairing the omission found in the earlier power deliveries for this new execution. The original coarse arm retains its previously disclosed retrospective binding limitation.

Keep both attempts in the resource/history ledger but use only one 32,000-trial coordinate set for inference. First-attempt output monitoring was pointed at the wrong directory; the retained completed child data are valid saved evidence, but its `within_caps` does not establish monitored actual-output containment. No recollection is recommended.

## Independent hashes and coordinates — both complete attempts

The audit hashes every primary gzip and reference file against its own receipt in **all16 shards of each attempt**, checks decompressed lengths, and separately compares whole decompressed primary bytes and container bytes between attempts. It does not rely on the owner's `ATTEMPT_ROW_EQUALITY.json`.

All32 shard receipts and64 file hashes/sizes pass. Within each attempt, 8,000 disjoint `(cell,program)` coordinates exactly cover P05N/P05A/P10N/P10A programs0–1999; each has trials0–3. There are96,000 unique primary identifiers and32,000 distinct trial coordinates. Reference files contain headers only, with zero recorded reference calls/rows. Attempt counts report2,000 completed per shard with no failed/missing/skipped trial. Every shard carries its attempt's preflight pins and correct namespace3/horizon2000.

**All16 corresponding primary gzip files are byte-identical, and their decompressed bytes are also identical.** This independently substantiates the row-equality claim and corrects the earlier inadequate inference from matching counters. It is192,000 stored primary rows across two executions of the same96,000-row dataset; it is not64,000 independent trials. Per-shard independent hashes are in the evidence JSON.

## Source, config and actual runtime binding

For corrected attempt `20260921T165632Z`, all22 pinned source files and both configuration files match their immutable `6bdefd1` Git blobs. Included files are `run_ablation.py`, `vablation.py`, `vpowercurve.py`, `run_powercurve.py`, the generator/evaluator, pin utility and supervisor. The source head is a disclosed dirty working tree based on `3faca125`; the recorded whole-file hashes, rather than that base commit alone, bind the changed execution source.

For first attempt `20260921T165412Z`, the same files/configurations match except `run_ablation.py`: its recorded SHA-256 is `d776a2cd26ae7f0cfcb5587b5f11086b069188d7c20fc55db6b7009b050a4b33`, while the corrected delivered driver is `33a5bc008efca0aba5c582ed03d8d4cb2f95ba33fbb6cde413ad42f7e7b76bae`. The delivered code explicitly documents the relative-output-directory repair. This review did not recover an immutable blob matching the first driver's exact hash. Preserve that qualification; independent byte equality of all outputs supports numerical reproducibility without pretending the two driver sources were identical.

Both attempts' preflight pin run identities explicitly name `variant=ADAPTER_NOCERT`, namespace3, zero reference calls and the complete P05/P10 atom weights. These equal the preflight law table, plan namespace and every shard's context. This is more informative than an unchanged `vgen.py` hash alone. The preflight timestamps precede or share the same recorded second as the child job start; source writes the preflight before its shard loop.

Static source tracing confirms the operator is installed around the actual `vgen.state_at_age` module global read by `adapter_tick_sums`, with the driver loop inside `with vablation.installed()`. Each deposited shard witness reports installation throughout,2,000 completed trials and positive operator entries. The recorded branch witness names the real evaluator path and a namespace3 coordinate. These are runtime receipts supported by inspected source, not fresh independent executions of those invariants.

The global child operator counter is109,515 while per-shard counted intervals sum108,860 in each attempt. They are not the same scope: the global counter also includes calls outside the per-shard measured intervals, including preflight. Neither is an independent-trial count. The no-drift check reports both before/after code/config/policy/workload/receipt equality; the full second pin object is not separately deposited, so this audit verifies the initial pins and the recorded drift result rather than independently replaying a historical end-of-run snapshot.

## Attempt and resource accounting

| Observation | First attempt, misplaced directory | Corrected attempt |
|---|---:|---:|
| Child completed trials | 32,000 | 32,000 |
| Data bytes, including empty reference headers | 1,884,074 | 1,884,074 |
| Current complete attempt-directory bytes | 2,122,881 | 2,123,820 |
| Supervisor wall seconds | 53.251615125 | 52.974734542 |
| Sampled peak treeRSS bytes | 79,331,328 | 80,248,832 |
| Supervisor actual-child-directory byte field | 0 | 2,118,377 |
| Parent completion | false | true |
| Retained child completion | true | true |

Combined observed supervisor time is **106.226349667 seconds**; retained attempt directories total **4,246,701 bytes**. The ledger must count64,000 trial evaluations in compute usage but32,000 unique trial coordinates for the paired scientific analysis. Both executions are retained, so neither should be erased as a mere failed parent invocation.

First attempt passed a relative `--out` while the supervisor changed the child's working directory. The parent monitored/reconciled an empty directory while the child completed elsewhere. This explains its zero observed bytes and incomplete parent receipt; those fields are not evidence of zero work or zero disk usage. Current retained bytes establish a small final footprint, not a continuously enforced first-attempt output budget.

The corrected attempt passes an absolute path. Subtracting its supervisor and final job receipts from the present directory reproduces the2,118,377-byte child snapshot exactly. Its observed time, sampled RSS and output are well within3,600seconds/2GiB/200MiB. No claim is made of continuous RSS bounds or monitoring of later copying/analysis. The original coarse records are reused for comparison; no new reference evaluation is implied by the retained native dependency pins.

## Discarded T1 pass clarification

`DISCARDED_T1_PASS_MAPPING.json` identifies the ambiguous phrase as the already-enumerated **measurement-mode** executions2/3, not a newly disclosed discarded112,000-trial calibration run. All ten supplied known fields for those two passes exactly match `measurement_20260921/ACCOUNTING_CORRECTION.json`, including40 trials/80 references each, pass2 timing/bytes/RSS and pass3 approximate resource fields. The same ledger already enumerates six executions in that historical measurement phase, two retained and four discarded. Commit `41c5991871c04393e81167d2d5567fe746ae7eaf` independently documents the measurement-receipt decision-count leak and its repair at the stated timestamp.

The mapping appropriately keeps lost artifacts and effect-exposure influence unknown, and expressly states that delivered local attempt IDs cannot prove no unrecorded earlier calibration attempt existed. This is supported identification and clarification, not restored provenance or evidence that accepted T1 calibration rows changed.

One concrete textual correction remains: the mapping describes `results/t1_run_stdout.log` as **two identical tracebacks**. The deposited11-line file contains **one** `Traceback (most recent call last)` block and one terminal `KeyError: 'started_perf'`. It supports the known parent-finalization crash but cannot establish two parent invocations. Correct that count or supply the second surviving log without altering the first. The known56-shard child and later recovered finalization are already independently reconciled; this log-count correction does not reopen collection.

## Reproduction

Committed-review evidence is restricted to `reviews/ablation_validation_evidence_20260921_1737/provenance_audit.py` and `provenance_results.json`. The script independently hashes/decompresses all deposited disabled files, verifies identifiers/pins, compares corresponding bytes, reconciles resources and checks mapping fields. It uses no experiment imports and performs no simulation. Root may integrate the verified provenance claims with the scientific review while retaining the first-output-monitoring and original-coarse-binding qualifications.
