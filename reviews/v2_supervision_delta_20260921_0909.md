# Independent resource review: supervised preflight measurement

Reviewed owner head `3341f2107b9ff9a5d67c9a09c3c27e9a4fe74d7d` against `0281eb21d1890cb58eeb1af3ee71cf352400df67`, using immutable export `work/v2_review_0909`. Scope: supervisor, measurement resource receipts, byte/hash identity, arithmetic, and append-only prior-attempt accounting. No effect values inspected; no scientific, model, reference, timing or grid reruns. This is independent acceptance of the resource evidence, not scientific acceptance or launch authorization. Root separately reviews immutable pins, configuration, preflight policy and reference provenance.

## Decision

**The previous timing obstacle is resolved conditionally.** The measured preflight-only workload supports a bounded T1 attempt with the existing 5,400-second, 2-GiB process-tree RSS and 200-MiB output limits. It does not guarantee every cell of a 28,000-program grid will complete inside those limits. No new broad timing sweep is justified. The remaining blocking work is a single execution-wiring repair: bind the accepted ledger and exact full-grid configuration to the actual parent-supervised launch, repair monitoring failure behavior, and retain all stopped/partial artifacts if a cap is reached. Do not launch the current direct full-grid CLI.

## Independently reconciled delivered evidence

The new directory is `results/live_ab_validation_v2/measurement_preflight_20260921/`.

- One parent-supervised job contains two horizon evaluations: 20 cell/horizon units, ten distinct seed-program identities, 80 trials and 160 fullpath H/D reference calls. These are development coordinates, not full-grid outcomes.
- Parent receipt: 2026-09-21 08:51:06–08:51:08 UTC; wall 1.7469734997 seconds, eleven polling samples, sampled peak simultaneous child-tree RSS 72,597,504 bytes, successful exit, no breach. This is a real parent window encompassing child startup, imports, execution, output close and child receipt writing.
- Child total wall is 1.4676726665 seconds; horizon walls sum to 1.4676434593 seconds. N=1000 uses 0.5117910421 seconds and N=2000 uses 0.9558524173 seconds. Each horizon contains 40 trials and 80 reference calls. Preflight checks process 3,501 and 7,001 states, respectively.
- Independently summing the directory gives 115,131 bytes after the parent and finding receipts. Excluding `SUPERVISION.json`, `PARENT_RECEIPT.json` and `FINDING.json` gives exactly the 103,713 child-output bytes recorded at child exit. Thus the receipt scope is reconcilable; final parent metadata is an additional 11,418 bytes, not silently part of that observed child total.
- Both primary gzip file hashes match their receipts. Decompressed primary bytes exactly match the previous delivery at each horizon; reference CSV bytes also exactly match. There are 120 primary data rows and 240 reference data rows per horizon. Comparisons used whole byte sequences, lengths and newline counts only, without decoding scientific outcome fields.

| Horizon | Primary gzip bytes | Decompressed primary bytes | Reference bytes | Decompressed primary SHA-256 | Reference SHA-256 |
|---|---:|---:|---:|---|---|
| 1000 | 1671 | 23727 | 31007 | `9dd82799d8df7e74b187e30795be14192e3726617d76a3126652646ff2ec6e44` | `6509398c88a658a1f9aa173a0ac2021ea3a007116a0f10b75d2fc21d25edef60` |
| 2000 | 1620 | 24535 | 31105 | `d9fd343f7153acf0fd1b34c8bcb1dc057c2b8923f1ecf5b20e999792b18d425a` | `779828779853dbfbdca0e62f493078e22b31ab03e68f26cf651ab4fa123e3108` |

The fixed T1 arithmetic is `0.9558524172753096 / 10 * 28000 = 2676.386768370867` seconds (44.6064 minutes), below 5,400 seconds. The historical cost ratio is not a paired causal speedup estimate: these were separate passes under different host load. Parent startup/poll overhead is additional, but should be reserved once per job rather than multiplied as though a new parent were launched for each ten-program block. The projection already repeats the measured per-horizon setup/preflight cost every ten programs.

At 112,000 trials, there are 224,000 H/D calls and 672,000 reference rows. Scaling the larger observed reference bytes per trial gives approximately 87,094,000 bytes. Adding the larger observed compressed-primary bytes per trial gives approximately 91,772,800 bytes for the two data streams. Even scaling the larger **uncompressed** primary size plus the larger reference size gives 155,792,000 bytes, below 209,715,200 bytes by approximately 53.9 MB before metadata. These are conservative relative to the two observed horizons, **not an upper bound on all grid cells, formatting lengths or failures**. They support the bounded attempt and an explicit metadata reserve. Streaming reference persistence avoids retaining all rows in memory. Actual parent monitoring remains necessary.

## Blocking before a full-grid attempt

1. **Use the accepted ledger in the actual capped launch.** `vpanel.py:651–669` still invokes `run_panel` directly; full-grid resource admission still requires root's new-ledger binding. The full attempt must be an explicitly supervised child with fixed T1 arguments and caps 5400 seconds / 2147483648 RSS bytes / 209715200 output bytes. Root should bind `vmeasure.py` and `vsupervise.py` alongside the execution sources. Do not infer launch clearance from a successful measurement mode. This repair requires source/fixture verification, not repeated development timings.
2. **Fail closed when memory monitoring fails.** `vsupervise.py:71–74,106–117` returns the leader alone or zero RSS on monitor errors and does not check nonzero `ps` status. For a still-running child, a missing or failed resource observation must produce a monitoring-failure receipt and stop only this job, rather than report zero usage. Distinguish the ordinary child-exited race from failed live monitoring. The delivered successful measurement is not invalidated by this source defect; the long-run admission claim requires its repair.
3. **Finish cleanup of the owned group.** `vsupervise.py:249–267` returns when the group leader exits, even if descendants ignore SIGTERM. Retain the created group ID and ensure the remaining owned group receives bounded escalation. Do not enumerate or signal foreign groups. This is a small cleanup correction within the existing design, not a request for a new supervisor architecture.

## Nonblocking for this delivered measurement

- Supervision is sampled at 0.15 seconds; its RSS is not a mathematical continuous maximum. Its output/window excludes later parent receipts and hash comparison. Label this scope and reserve/check final metadata bytes; the measured artifacts are far below caps, so no remeasurement is needed.
- `vmeasure.py:149–151` treats an absent baseline reference file as a successful reference match, and its final status at line217 ignores `all_identical`. Baseline files were present and equality was independently verified for this delivery. Make future comparisons fail closed without changing the accepted observation.
- `vpanel.py:623` still labels the compressed primary file size `uncompressed_bytes`. The correct new decompressed lengths are in the table above; append a metadata correction without replacing originals or rerunning data.
- Available RAM was not measured as a free-capacity field. The observed child-tree footprint is approximately 69.24 MiB, with a 2-GiB process-tree limit. Check current available capacity before the actual launch and record contention; no inference of available RAM should be made from total system RAM.

## Prior-attempt accounting

`measurement_20260921/ACCOUNTING_CORRECTION.json` preserves the old receipts and records six prior measurement-mode executions, including the tiny cap test, two discarded first-pass horizon evaluations, the leak-verification control and the two retained horizon evaluations. Known trial counts sum to 165; do not invent missing reference-call counts or missing resource totals for deleted attempts. The two new horizon evaluations are separate current observations within one new supervised parent job. Do not conflate two delivered horizons with the entire historical execution count.

The correction reconciles old data bytes 65,403, old complete directory bytes 99,631 and old uncompressed primary bytes 48,262. It properly distinguishes a self/reaped-child maximum from simultaneous process-tree RSS, and marks unavailable historical measurements unknown. Deleted-attempt irrecoverability and absence of decision influence remain owner reports, not independently demonstrated facts. Retain this disclosure with the study provenance. These historical limitations do not require rerunning the new, hash-identical resource observation.

## Smallest completion route

Accept this resource measurement and conditional T1 projection; root completes exact source/ledger binding and scientific clearance. Owner repairs the three launch items, corrects metadata append-only, and supplies one exact parent-supervised T1 invocation plus bounded synthetic checks of failure handling. Preserve the fixed design and caps; start only after explicit root acceptance. A cap stop is an execution finding with preserved partial artifacts, not a completed grid or a reason to silently choose another tier.
