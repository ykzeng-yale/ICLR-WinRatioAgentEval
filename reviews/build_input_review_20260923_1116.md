# Build input provenance review — September 23, 11:16 cycle

**Full-project readiness: 75% (change 0); bounded-v1: 90%.** Remaining: Session60 prospective study and root acceptance (10 points), root expanded package QA (5), and Yukang Zeng's author checks (10). This provenance closure earns no study-completion credit.

Reviewed head `e314260b49cf7137a80413c9182679f10330118e`, substantive delivery `899201d0f0e1b6131385d597e2a88a9badbe53cd`. The additive owner correction `results/live_ab/BUILD_NETWORK_PROVENANCE_CORRECTION.json` is timestamped **2026-09-23 10:49:57 UTC**.

**Disposition: accept the bounded provenance corrections and exact deposited metadata bytes. No new defect within this scope.** The previous build-network and reader-code wording findings are closed at the disclosure level; no historical execution has been independently rerun or retroactively frozen.

## Exact deposited checks

All **15 byte/document checks passed**, including preservation of both earlier receipts and the original build log, three files' byte counts/digests/content, and agreement between the correction and log.

| Deposited file under `evidence_session60/candidate_v7/build_inputs/` | Bytes | SHA-256 of the actual deposited file |
|---|---:|---|
| `dist.tar.gz.sha256` | 78 | `71b6ab5125f483f38298ac4883f1b066fbfb08e8048c914d89164b07d6ef0055` |
| `ui-embed.sha256` | 64 | `2640135169d7faf20c039ec8535d9c7fd8985313645d261c82926be22c915244` |
| `ui-stamp` | 20 | `8c03eb6b0d5a3894322252cd30a526fd3af5bd94866bd79698eb51e9ebd3dcb4` |

The checksum file names archive digest `3de85ed97697c04e1614e95021eef6b668dc089eb66e7f0db1f83cbef1121a89`, matching the correction's declaration for an external **3,085,391-byte** archive. The archive is explicitly **not deposited**, is owner-reported preserved in place, and was not accessed here. Checking checksum-file bytes is not an independent check of archive bytes.

The embedding metadata contains digest `2b5941122d67ce4c5abc62a56333c429630fba4784ff8e46bcd9c1f59d668c5d`; only that metadata file was hashed, not the underlying generated inputs or embedded binary content. The stamp records `ggml-org/llama-ui|b1`. As the retained log explicitly says the fallback resolved **latest**, this stamp is a requested-ref/cache marker and must not be interpreted as proof that immutable `b1` bytes were used.

## Closed findings and retained limits

The new correction accurately withdraws the old blanket no-network claim for the build. It matches log lines 331–338: the `b1` checksum fetch failed, `latest` fallback succeeded, and 70 UI assets were embedded. It expressly acknowledges the additional mutable input and that the correction does not itself make the historical build reproducible. The correction distinguishes source-copy and build phases. The source-copy claim remains owner-reported; this review neither proved nor expanded no-network claims for other phases.

The residual reader wording now correctly says the retained material is a **summary assertion and parsed seal object**, while the original reader invocation and producing code are unavailable. That resolves the inaccurate earlier statement without inventing a recovered transcript. The original inaccurate receipts are preserved and corrected additively.

The archive may remain preserved externally under root's disposition. **No present requirement to commit the 3 MB third-party archive before provenance/distribution rights are known, and no fetch or replacement build is requested.** Any future build must freeze its inputs or disable optional fetching before execution. Existing candidate runtime inventory/launch-boundary and lifecycle obligations remain; these three metadata files do not prove a transitive runtime dependency closure or authorize an experiment.

The four prior native outcomes remain owner-reported, with the original successful-control seal and build-log bytes independently reconciled in the preceding review. This task does not change that acceptance level or imply loaded-model coverage.

Evidence: `reviews/evidence/build_input_review_20260923_1116.json`. Scope counts: **3 deposited metadata byte streams checked; 0 archive bytes checked; 0 builds, native/model executions, network calls, owner-current-artifact accesses or suite runs.** Root owns the separate inventory of broader `nothing_executed` claims; it was not duplicated here.
