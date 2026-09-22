# Historical wincs provenance and unexpected payload delta — September 22, 04:22 cycle

Scope: read-only adjudication of owner `1155ca8e18236e233e672e30b5c7073558a0d663` / head `0524083`, historical source/report pins, current arXiv membership, and the nine newly tracked airline raw/log duplicates. No model, simulation or scientific-suite rerun; no owner files changed. Root separately handles the live protocol vocabulary pin.

## Decision

**A historical source hash need not equal HEAD. The `601865d9…` hash is real, recoverable, and appropriate for the explicitly dated historical reanalysis/verification. Do not repin old receipts to `69d2cb11…`.** The owner's implication that both deposited reports assert a false identity simply because the live file changed is too broad. There is a real, already disclosed airline original-import provenance gap; it is not newly established by comparing a later HEAD.

This finding does not reopen accepted paper statistics: root coding/airline builders use `winstats`, independently recompute the retained analysis, and exclude the contributed `wincs` implementation. No readiness change: full75%, bounded-v1 90%.

## Independently recovered source identities

SHA-256 was recomputed from exact Git file bytes; Git blob IDs are separate identifiers.

| Exact source | SHA-256 of `src/wincs.py` | Git blob |
|---|---|---|
| `e0610088bd7772916d25c84b94eeef40ca2fc0a9` | `6a6a0b51bf46d64079614af3aefc364800c1862fd7635728c2949be7f2907a3b` | `92ad0dbfab7820bfce8992ca231503f6f257b668` |
| `c1da1c3fc4e8c90644388e8b47e2e15574fe5215` and `5e91fcd9afe69a60d4376e5ac370e4865f099f57` | `601865d9adf0a9f1a0f20c44ef78cb18dffe33fdc3beb5d98a47d6c5199b8754` | `6e236ff8ab819040cae5f58ad8d488657d623ec9` |
| `3db00bad951b879b7aa14a15bf44fc47f1b12833` and owner `1155ca8` / `0524083` | `69d2cb1123565ebaf5470bb1d46046a70be00746742dfb7d0349cdc2c36074bd` | `60e3c4c3b208714517889233cc0687f0bf7c9889` |

`3db00ba` (September20,20:49:28-04:00) changed the prior `601865…` file by adding guardrail sizing helpers/imports and updating `pairs_for_power`. This is a substantive later version, not proof that the September19 records are false. The complete historical source is retrievable directly at:

https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/blob/c1da1c3fc4e8c90644388e8b47e2e15574fe5215/src/wincs.py

A baseline commit alone is not a universal source pin: `45e8ee2:src/wincs.py` has the earlier `714b21fe…` SHA-256. Root explicitly excluded that module from its accepted release; use the actual contributor correction commit for the historical `601865…` blob, not whichever tree carries the paper release.

## Report semantics and residual uncertainty

1. **Coding v3 is explicitly bound.** `results/local_stream/analysis_v3_manifest.json:1–24` calls this a post-hoc reanalysis, records05:28:23–05:29:05Z on September19, and pins `601865…`. `summary_v3.json:14` repeats that identity. `report_v5.md:16,29` describes the endpoint correction carried through v3/v5 rather than claiming the file will always match future HEAD. `reviews/round12_coding_correction_and_baseline_delta.md:76–88` explicitly calls its hashes source/report anchors identifying the reviewed correction **independently of the later live PR head**. That independent audit accepted only endpoint arithmetic, not generic projection/width methods.
2. **Airline original execution remains unbound, but the verification snapshot is bound.** `report_final_v3.md:309–311` preserves the registered addendum identity `6a6a…` and explicitly says which bytes generated the original05:01:30Z summary cannot be confirmed. Its `601865…` is the later verification version. `analysis_consistency_check.json:2–16` records the post-hoc05:32:25Z check, source hashes, and that limitation. `report_final_v3.md:434` describes exact reproduction of703 leaves (438 numeric) and selected files at that check, not proof of the original imported bytes. Do not convert this historical consistency check into original-execution provenance.
3. **Time-relative wording can be improved finitely.** Phrases such as “now on disk”/“current wincs” in the historical report should be clarified in an additive provenance note as “at the recorded September19 verification,” with the exact commit/blob link above. Preserve original reports and receipts. No new data collection or rerun is needed merely to establish these historical file identities.
4. **Accepted paper/release is independent of this excluded source.** `experiments/build_open_coding_results.py:18` and `experiments/build_open_airline_results.py:19` import root `winstats`; both record its source hash. The current `arxiv/reproducibility_code.zip` has no `wincs` path and includes both root builders. Round11/12 acceptance explicitly excluded contributed interval code and recomputed restricted results. No manuscript numeric defect follows from this HEAD mismatch.

## Unexpected nine-file airline delivery: exact duplicates, not new experiments

The `1155ca8` addition includes **nine raw/log files totaling68,998,994 bytes**. I compared every newly added file byte-for-byte with the decompressed already tracked gzip at the same owner commit, including both UUID-named aliases. All nine comparisons pass.

| New file(s), under `results/tau2_open/` | Bytes per file | Preserved counterpart / decompressed SHA-256 |
|---|---:|---|
| `raw/tau2_open_armA.json`; `raw/tau2_open_armA.0bf28fc9101f442a806c625dbdbe47c7.json` |14,835,545 each| `raw_gz/tau2_open_armA.json.gz`; `887c66a23c2c1c2188279ce658efb15436648a9e26251b62f569521df4845fd8` |
| `raw/tau2_open_armB.json`; `raw/tau2_open_armB.0bf28fc9101f442a806c625dbdbe47c7.json` |14,208,179 each| `raw_gz/tau2_open_armB.json.gz`; `39a49567936fb14f5444ae6e406c43abd1cfbb21198540c8b8df585d8fa1c8f6` |
| `logs/llama_server_8081.log` |5,892,421| `logs_gz/llama_server_8081.log.gz`; `9c2eeca8a8f49183a0bf61a29c8e559394b49acbf34f542e28f67b1bfc400d13` |
| `logs/llama_server_8082.log` |2,035,343| `logs_gz/llama_server_8082.log.gz`; `f693ccaa977dff310bdf4af37ddb9403b7363cf3b3c282bcec0517ce086b4dc6` |
| `logs/tau2_armA.invocation1_preamendment.log` |93,466| `logs_gz/tau2_armA.invocation1_preamendment.log.gz`; `838b082f78dce04a71ccec2c98ff1394e95e54bb75f03a3cd4bb07bc7159073c` |
| `logs/tau2_armA.log` |1,536,109| `logs_gz/tau2_armA.log.gz`; `e2cb454b254c1bfc4cbebee5777cd9e3504ee399eec234081a4cb414217f95ef` |
| `logs/tau2_armB.log` |1,354,207| `logs_gz/tau2_armB.log.gz`; `fa95ab70d88e2a279535f8bccdb7651b2ca930188b45484a8ceb9eec249e0677` |

The12 new `results/local_stream/dryrun/` files total201,368 bytes. Their report explicitly says **MOCK DATA—DRY RUN**, generated September18 at14:54:26Z,24 mock episodes from `mock-deterministic-v1`; no new empirical outcomes. I have not established byte-identical prior counterparts for these12 files and do not recommend removing them under the nine-file duplicate finding.

## Finite owner action

- Add a short historical-source map with exact old/new commit/blob links, verification timestamps and the already disclosed original airline import uncertainty; correct the broad “source identity false” interpretation. **Preserve historical hashes; do not repin or overwrite prior records.** No blanket scientific rerun.
- After root review, owner may remove **only the nine newly added duplicate raw/log paths listed above from current tracking**, retaining gzip counterparts and Git history, and prevent accidental re-addition. No force push/history rewrite or deletion of canonical compressed evidence. These additions change repository size, not experiment counts or paper acceptance.
- Keep the12 mock dry-run files clearly labeled and separate from empirical counts. No release change is required solely for this delivery; it adds no evidence to accepted root projections.
