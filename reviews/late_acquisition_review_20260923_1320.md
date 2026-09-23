# Late acquisition delta: five repairs and incomplete manifest validation

Full-project arXiv readiness remains **75% (Δ0)**; bounded-v1 remains **90%**. Remaining: prospective-study owner completes preparation, explicit freeze review and the study with root acceptance (10 points); root completes final release QA (5); Yukang Zeng completes author checks (10). Accepted CPU validation and its paper/package integration remain complete and unchanged.

Reviewed source [3befd1507362904aaef8d3424983ae145b7a1480](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/3befd1507362904aaef8d3424983ae145b7a1480), delivered in [4ccfbbc71d7c14259b340ae5de6d030997ce4751](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/4ccfbbc71d7c14259b340ae5de6d030997ce4751). This is a bounded source/fixture review, not a live experiment or freeze approval. Exact hashes, observations and the reproduction script are retained in [the evidence JSON](evidence/late_acquisition_review_20260923_1320.json).

## Accepted subset

Independently executed only the **five new owner test methods: 5 passed, 0 skipped**. Four run the real `main()` under the supplied mocks; the fifth invokes the production drain with one expressly authorized real quiet local pipe. Independent guards denied any unexpected process/socket/system/signal call; none fired. No native child, HTTP, server, model, build or simulation ran. Temporary files were real and inspected before cleanup.

- `{}` now produces one terminal refusal receipt before launch, naming missing fields.
- The delivered port=99999, boolean max_tokens and non-string server argument case names all three problems and persists a refusal before launch.
- Invalid UTF-8 lifecycle bytes now produce an observation refusal and reach raw-byte retention instead of escaping from the reader. The 19 original bytes remain undecodable rather than being replaced.
- Moving the mocked clock past cutoff during the barrier results in zero POST calls and one terminal receipt.
- The quiet pipe exits after **0.4092 seconds** for the configured 0.4-second deadline, with nonblocking reads, `deadline_exhausted=true`, EOF=false and capture_complete=false. The zero-byte artifact size/hash agree with the empty-byte SHA-256. This is a successful bounded refusal, not a completed capture.

Source inspection confirms the new deadline check after artifact verification/before launch, bounded health GET/sleep, the post-barrier check and the final pre-POST check. These finite checks do **not** establish a blanket 600-second wall-clock guarantee. In particular, the stream helper still records and permits blocking fallback when nonblocking setup is unavailable; that is outside the tested quiet-descriptor path and remains within the existing deadline task.

## Four actual-main counterexamples

The claim in `ACQUISITION_FINALIZATION_AND_DEADLINE.json` that validation checks every subsequently dereferenced field is not supported. Starting from the harness's usable pinned fixture, delete just the named field. All four are accepted by `validate_manifest` with an empty problem list, then raise an uncaught `KeyError`; none writes a terminal receipt.

| Omitted field | Fake POSTs | Reap calls / exit code | Durable request files | Observed failure |
|---|---:|---|---|---|
| `request.temperature` | 0 | 0 / None | no intent or response | KeyError after fake launch, drain and health check; cleanup was never reached |
| `host_id` | 2 | 1 / 0 | one intent, two responses | KeyError constructing expected provenance after shutdown |
| `boot_id` | 2 | 1 / 0 | one intent, two responses | same failure boundary |
| `patch_sha256` | 2 | 1 / 0 | one intent, two responses | same failure boundary |

For the temperature witness the fake process was polled once and its 21 diagnostic bytes were consumed, establishing that the failure occurred after the launcher path. No actual process existed or was left running. For the identity/patch witnesses the retained intent/responses are preserved; absence of the final receipt does not imply those request bytes disappeared.

Next bounded owner action: validate the complete required manifest before launch, including temperature and host/boot/patch fields with the agreed domains; route later exceptions through guaranteed cleanup and terminal finalization. Add these four entry-point cases, requiring zero launch/transport for invalid manifests and exactly one terminal refusal receipt. Preserve the five accepted repairs. Root separately decides the remaining acquisition ordering, full artifact/source binding, cap/plan agreement and deadline acceptance; no new build or real acquisition is requested by this report.

## Pins

- `run_smoke.py`: `1be7ff7fd208859d916512fa829b11f908cdcf5894c411fc93e30fa40710e2d8`
- `lab_lifecycle.py`: `604556893fb5d381049756f765251bc45bd1f57ea632630d68fe2ee5610ac0b2`
- Owner entry-point tests: `a178b49afbef6537db13d79231afc5674c34c209e4978aaab30a5942a3dba779`

The evidence JSON also pins both historical input fixtures and the delivery receipt. Historical evidence remains readable; it does not exempt a new launch from the current contract.
