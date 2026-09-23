# Per-request usage label acceptance — September 23, 12:42 cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Accepted CPU validation and paper/package integration remain complete and unchanged. Remaining 25 points: prospective study 10 (Session60 collection/root acceptance), final expanded QA 5 (root), and author checks 10 (Yukang Zeng). Next milestone remains bounded preparation closure and the costed plan before explicit working-branch freeze review. This consistency repair adds no scientific result or milestone credit.

Reviewed head `2c60654b0968caa7b066e5ede8e248e0430ad15f`; substantive delivery `9f1a02da1cdaddc6982eeecf3c7b94c636cd7c25`. The executed `experiments/live_ab_serving/run_smoke.py` SHA-256 is **`c9d59799fe21d0a2ff44b5eb2d16d23e6debe5d7182250e8ab305d178e69cef8`**. Evidence: `reviews/evidence/usage_label_review_20260923_1242.json`.

## Accepted changed behavior

The per-request path now preserves the original usage object and derives `usage_known` from the same `usable_token_count` predicate used by the aggregate. Unusable values receive an explicit reason. The previously inconsistent negative-token row no longer claims known usage while its aggregate refuses.

Two bounded cases exercised the **actual `run_smoke.main`** through root's preserved `reviews/evidence/request_delta_harness_20260923_1204.py`, safely adapted only in a temporary directory:

| Case | Per-request evidence | Aggregate and supervisor |
|---|---|---|
| Negative pair | Both original `completion_tokens=-1` values retained; both `usage_known=false`; both reasons state the required nonnegative, non-boolean integer rule | Known requests 0, unknown requests 2; total and cap status null; one receipt; return code 1 |
| Known-zero pair | Both observed zero values retained and usable; neither carries an unusable reason | Known requests 2, unknown requests 0; measured total 0; cap respected; one receipt; return code 0 |

Neither case raised an exception. This distinguishes observed zero from invalid negative values without replacing original observations.

## Scope and disposition

**Accept the per-request labeling repair.** No gap was found in this narrow delta. Root separately owns required-denominator API validation and broader supervisor acceptance.

The temporary adaptation changed only repository location, the explicitly updated supervisor source pin, and case selection to these two cases. Other source pins were retained and verified; the original committed harness remained byte-identical. The evidence records the original/adapted harness hashes and exact adaptation diff. All process creation, HTTP, signals, clocks, and scheduling were mocked. Real capture, reader, and finalization touched only closed synthetic temporary artifacts.

No owner harness, other four original cases, complete suite, native child, model, actual HTTP/network, or build was run. Only this report and its new evidence file were written in the repository; no owner/shared files were changed and no commit was made.
