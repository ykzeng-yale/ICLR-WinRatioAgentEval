# Late native v7 receipt review — September 23, 09:19 cycle

Exact received head: `ad9d58f0014d14e9c10e47e73cce9472a380e02d`. Application receipt: `52ae99a387d436cace354b6f811e955d568632c6`; native build/injection receipt: `9bd1675b2a94c081c5dba7c221a7521d3a249629`; index update `fbcbd19`. Root's v7 source/application acceptance earlier in this cycle remains in force.

**Disposition:** acknowledge the newly delivered, internally consistent native results; do not conflate receipt reconciliation with independent native reproduction or complete artifact/provenance acceptance. The earlier “v7 is unbuilt” status is superseded by this **owner-reported build**. No build, native binary, model, sandbox, server or network operation was repeated here.

## Received versus independently checked

The owner reports a **262/262-target build at -j2**, exit0, **09:18:45–09:20:07 UTC**; those times independently reconcile to **82 seconds**. The receipt pins a **33,472-byte launcher**, SHA-256 `5260887866c85a07750ebc71349e13c985c17b4983f0619f10b4c355180a6bd6`, and v7 patch `88975d3790fd831d219b4e2a558184cb8cfa2e9e18b6c620edba33a23b79e184`.

Four model-free native `--help` cases are reported:

| Owner-reported case | Result |
|---|---|
| Writable control directory | Exit0, seal written, no sidecar |
| Unwritable directory | Exit93, neither log nor sidecar written |
| Writable control with full stderr pipe | Exit0 in 0.08s |
| Unwritable directory with full undrained stderr pipe | Exit93 in 0.08s, 65,536 queued bytes |

I independently verified agreement between the deposited patch bytes, application receipt and native build receipt. Both owner preimage hashes match the existing exact source bytes independently checked by root. The saved control **seal object** has integer non-boolean zero values for records, write failures and sidecar failures, consistent with the declared no-record native control. This validates internal/source consistency; it does not reproduce native execution.

The native receipt contains the parsed seal object, **not its original log bytes**. It also reports successful passage through the repaired reader but does not deposit the exact invocation/manifest used there. Therefore I have not independently reconciled an original native log byte stream, parser invocation or its selected artifact identities. No inference about slot lifecycle records, loaded reference coverage or scientific outcomes follows from these seal-only cases.

## One ranked next action: deposit the available immutable execution evidence now

The new commits supply summary JSON only. They do not include the exact configure/build commands and logs, injection script/argv/environment and per-case raw outputs, original control log, or a manifest binding the selected launcher to the current resolved implementation-library closure. The repository's earlier serving build uses a small launcher plus shared implementation libraries; the launcher digest alone does not identify the v7 code that was loaded. A digest appearing in this summary is a partial artifact pin, not an absence of all pins, but it is not a complete execution manifest.

**Session60 should deposit an additive immutable build/injection manifest now, before any loaded use, rather than waiting for a new study run.** Bind the exact base/patch/source and configuration, build commands/tool versions/logs, selected launcher path/bytes/hash, resolved non-system libraries including `libllama-server-impl.dylib`, injection script and per-case argv/relevant non-secret environment, working directory, actual timestamps, exit/timeout outcomes, directory mode and pipe setup, original control log and available stdout/stderr/sidecar state. Retain all four attempts and distinguish missing material explicitly. The existing evidence should be preserved; do not rerun a model to fill provenance gaps.

If the manifest is assembled now, label it honestly as a post-execution artifact inventory/reconciliation. Do not claim that today's artifact hash or reconstructed script was captured before the reported attempts. Raw artifacts already retained at execution can still be deposited and independently validated without a repeat. No additional source/application approval round is needed.

## Owner timestamps and monitoring correction

The latest supplied owner report is **09:23 UTC**. Capacity receipt `HOST_CAPACITY_OBSERVATION_20260923T091625Z.json` records an owner observation at **09:16:25 UTC**: 1,286 processes scanned, zero findings/degraded readings, no watched listeners. This precedes the reported build and is not a reservation or continuously validated capacity interval.

`CHECK_MARKER_DEFECT.json`, timestamped **09:19:11 UTC**, discloses a future-dated `since` marker that made prior empty comment queries uninformative. The owner reports replacing the assumed clock with `date -u` and reviewing 12 comments, including three previously unread mirrors of already-merged review commits. That reconciliation is owner-reported here; I did not re-query the comment stream. The explicit correction and retained old evidence are useful, but previous empty queries must not be presented as independent observations of no change.

Evidence: `reviews/evidence/native_v7_receipt_review_20260923_0919.json`. Full-project readiness remains **75% (change 0)**; bounded-v1 **90%**. Native engineering evidence does not earn study-completion credit. Remaining: Session60 prospective study and root acceptance (10 points), root final expanded package QA (5), Yukang Zeng's author checks (10).
