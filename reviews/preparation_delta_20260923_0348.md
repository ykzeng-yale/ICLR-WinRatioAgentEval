# Independent preparation delta review — September 23, 03:48 UTC cycle

**Full-project arXiv readiness 75% (change 0); bounded-v1 90%.** Remaining: prospective collection and independent acceptance 10 (Session60/root), final expanded release QA 5 (root), author checks 10 (Yukang). This bounded review accepts implementation subsets, not prospective outcomes or execution clearance.

Reviewed repository head `334f12109babc6d35d0bf9dae0298c60d1c1dbad`, delta from root `2b8350b5a5a262b800e2d330a7440422de287b62`. Exact deliveries:

- [Production clock](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/94edd0cfe7fc0f475bac87952ea917611c26a073).
- [Shared worker TMPDIR](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/b7940a464e399ab5ce67cdf72087bedc8a3a1273).
- [Initial timing report](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/07fc1384b5d8142f65dc79217afbc74bd7cafa0c), [vocabulary repair](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/9b6c5938196a185cae775272d22aa4864148bdce), [identity pairing](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/ad7d3b8d047bff939fba2a0d41741eccb28f71fb), and [acceptance/log tables](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/090461737cfb0123a74171cb521bf5c54e4368f8).

## Accepted subset and verification scope

**50 focused changed-method tests passed**, selecting methods defined directly in ProductionClockWindowRefusalTests, RuntimeCopySweepTests, TmpdirPolicyTests, SandwichAuditAndLabelTests, GapReportVocabularyTests, GapCoverageIdentityTests, and AcceptanceLatencyAndLogPrefixTests. Separate small witnesses exercised actual preflight/refusal serialization and reporting consumers. No model, network, native runtime, full simulation, trial collection or actual ten-second clock measurement was run.

The normal declared production worker job is now checked before its spool opens: World.build_job carries the frozen `sandbox` block; run_job delegates that block to the shared lab_common TMPDIR policy. Wrong ambient TMPDIR refuses and the prescribed path proceeds. Preparation delegates to that same policy. Accept this normal-path wiring; this does not certify a newly measured sandbox profile.

Accept the default ten-second window, ordinary short-window detection, and repair of the temporary runtime-copy write. The metadata now survives within ctx.cfg, but that is not a durable receipt; the actual persistence defects below remain.

Accept use of request IDs for request/terminal gap pairing, both response and error closure, explicit unmatched identities, and disclosure that sandbox/scrape intervals are not actually represented. These are restricted reporting checks; an entire open episode is only an envelope, not proof that every enclosed gap was covered by active sandbox or model execution. Do not describe this proxy as complete protocol 12.6 coverage certification.

Accept the acceptance-latency arithmetic on two chain-envelope nanosecond timestamps divided by 1e9, assignment-to-arrival matching, nearest-rank quantile convention, and separate negative/unmatched output. This is writer-observed acceptance timing; it does not establish a legal reveal look or validate the stopped estimand by itself. It does not subtract worker-local timestamps. Accept the stated distinction between checking log size/hash summaries and checking actual raw-byte prefixes, subject to the real-schema defect below.

## Ranked finite corrections

### 1. Finish the existing production clock contract through durable refusal

At lab_orchestrator.py:867–912, time.sleep(window_s) still executes before the short-window check, and there is no finite-value check. The mode is arbitrary runtime text rather than tied to an offline invocation.

Executed witnesses using the actual preflight and temporary freeze fixture:

| Input/path | Observed result |
|---|---|
| Production window 0.01, sleep stubbed | sleep called once, then PreflightError(clock_equivalence) |
| Production window -1, actual sleep | bare ValueError("sleep length must be non-negative"), no clock metadata or ordinary refusal evidence |
| Production NaN or infinity, sleep stubbed | no refusal; production_receipt=true |
| Window 0.01, offline_fixture, sim=false/mock=false | preflight returns without clock refusal |
| Window 0.01, unrecognized mode `typo`, sim=false/mock=false | preflight returns without clock refusal |

The NaN/infinity witness isolates the missing guard; it is not a claim that real sleep accepts nonfinite arguments. Actual invalid sleep fails before the ordinary PreflightError path, as the negative-window witness demonstrates.

A second actual-path witness caught the short-window PreflightError and called write_preflight_refused with its drift. **The saved program event was `checks_failed=["worktree_identity"], drift=[]`**, not clock_equivalence. DRIFT_LIST requires SHA-256 expected/found fields, whereas the new clock drift rows contain plaintext. The serializer's SchemaError fallback replaces the real reason. The same shape is used for a measured clock disagreement. Merely testing the exception string missed this.

Finite repair: validate conversion, finiteness, allowed mode and production minimum before sleeping; apply the shared rule at freeze validation and every production preflight; permit shortened mode only on an explicitly offline fixture path that cannot dispatch production work. Save effective window, tolerance, actual deltas, mode and disposition in a durable receipt on ordinary pass/refusal paths, with schema-valid event linkage. Preserve the existing clock_equivalence reason rather than misreporting worktree drift. Add focused tests that read back the actual saved event/receipt, not only ctx.cfg. Production_receipt must describe a valid completed production check rather than merely a requested long window.

### 2. Join the sandwich to its matching anchor events

Protocol_FINAL §12.6 item 4 explicitly compares consecutive receipts' server created_at differences with **the t_wall_ns of their two anchor events**. sandwich_audit currently uses the receipt event's own t_wall_ns and never joins anchor_seq. This changes the defined statistic and can change the integrity-qualified label.

Executed ordered-envelope witness (seconds shown for readability): anchor0 at 0, its receipt at 1; anchor1 at 10, its receipt at 100. The two receipts have server created_at separated by 10 seconds. With base30+p95=1, the protocol statistic is |10−10|=0, no violation. Current code uses |10−99|=89 and reports a violation. These are synthetic input records, not observed experiment timings.

Finite repair: map each receipt to exactly its anchor_seq, use that anchor's timestamp, and retain all identities in the output. Missing, duplicate or unusable pairing cannot establish a clean negative label. Existing tests use receipt timestamps, so add the unequal-posting-delay witness through integrity_object. Keep the accepted fixed-offset cancellation arithmetic and the unknown-p95 refusal.

Related same-path witness: a nullable created_at (allowed by ANCHOR_RECEIPT_FIELDS) causes a skipped sandwich row, but current output still sets computable=true, pairs_compared=1 and integrity_label_determined=true with a false label when no other limb fires. Count evaluated and skipped pairs separately; unresolved required pairs cannot establish a clean label. A positive finding from another limb can still establish the label.

### 3. Use the production map shape for log-summary checks

lab_eventlog.py ANCHOR_FIELDS defines server_log_bytes as INT_MAP and server_log_sha256 as HASH_MAP. server_log_prefix instead checks whether the entire byte field is an int. The existing tests use scalar invented shapes, so real anchor maps never enter the size or same-size-digest checks.

Executed witness: consecutive anchor bodies carry `server_log_bytes={"coder":100}` then `{"coder":50}` and respective coder hashes. Current result is violation_count=0 while `established` asserts byte-count monotonicity. This is an implementation failure on the actual schema, not empirical evidence of an edited experiment log.

Finite repair: evaluate each expected server ID's byte/hash pair, retain missing or changing key sets explicitly, and test shrinking/same-length-changed-hash/growing cases using schema-valid anchor bodies. This closes the summary-table check only. Full prefix certification still requires the preserved raw log bytes; keep that limitation explicit rather than claiming protocol item6 is complete.

## Next finite preparation milestone and disposition

Session60 should finish the clock guard/receipt and the two reporting identity/schema corrections in one bounded batch, using actual consumer paths and schema-valid fixtures. These are existing implementation obligations, not additional model experiments. The shared TMPDIR normal-path repair is accepted and need not be repeated. Root separately owns the current resource, lock, production-anchor and scientific execution decisions; this review does not add another approval gate to already authorized instrument-only work.

The prospective freeze remains a separate reviewed deliverable: named effective runtime guards, retained preparation receipts, actual serving/load evidence, complete usage and all attempts, legal reveal looks, AB/BA enrollment and frozen inference must agree before trial clearance. The new report code alone supplies none of those outcomes. The package, accepted CPU panel and score remain unchanged; no paper claim or readiness credit follows from these tests.
