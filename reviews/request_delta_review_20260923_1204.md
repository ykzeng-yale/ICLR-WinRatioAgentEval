# Independent actual-main request delta review — 2026-09-23 12:04

**Full-project arXiv readiness: 75%, change 0 points. Bounded-v1: 90%.** Remaining 25 points: prospective study 10 (Session60 collection and root acceptance), expanded final QA 5 (root), and author checks 10 (Yukang). These implementation closures earn no scientific-result credit.

Reviewed main [`9f2658b849d4f3d2fd2ce8fc9680b4e6b85454c9`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/9f2658b849d4f3d2fd2ce8fc9680b4e6b85454c9), delivery [`d208bfa990edac64bfb7acdc3235d02bb5553855`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/d208bfa990edac64bfb7acdc3235d02bb5553855), relative to `1bd5cd0bd11ffac5ab367f8b1e4f30b5c4c40e9d`.

## Disposition

Accept the broken-barrier no-dispatch closure, actual-main expected-denominator repair, aggregate negative-usage refusal, known-zero distinction, and Popen-failure loaded-state repair. One changed-path inconsistency remains: **a negative completion-token row still says `usage_known=true`, even though the aggregate correctly excludes it and refuses the attempt.** Request acquisition remains subject to the separate standing handoff; these bounded closures do not accept the whole supervisor or authorize another model run.

Six scenarios exercised real `run_smoke.main()`, its real reader, capture helper, finalizer and closed synthetic filesystem artifacts. Processes, transport, signals, clock and thread scheduling were mocked. The real Deadline received an explicit mock clock. Launch artifact verification was stubbed as root's separate scope. No real child, model, HTTP, native build or full suite ran. The zero/one-record cases deliberately left mock workers unfinished; no actual live worker or growing file was involved. All six cases returned normally and wrote exactly one receipt. Its six scenarios were rerun once after preserving the harness and once after repairing its output interface (18 mocked main invocations total; no additional scenarios). The final output-interface run reproduced the existing evidence exactly except for the updated harness hash.

| Case | POST calls | Worker records / expected | Aggregate usage / cap | Return | Independent disposition |
| --- | ---: | ---: | --- | ---: | --- |
| Broken barrier with ample budget | 0 | 2 / 2 | Unknown / unknown | 1 | Closed: both rows retain barrier error and explicit not-dispatched reason. |
| No worker records after bounded joins | 0 | 0 / 2 | Unknown / unknown | 1 | Closed for actual main: two unaccounted requests remain in the denominator. |
| One completed worker, one missing | 1 | 1 / 2 | Unknown / unknown; known-only sum 1,024 | 1 | Closed for actual main: one missing record cannot turn partial usage into the total. |
| Two reported token counts of -1 | 2 | 2 / 2 | Unknown / unknown; aggregate known count 0 | 1 | Aggregate refusal closed; row label remains inconsistent. |
| Two explicitly reported zero counts | 2 | 2 / 2 | Measured 0 / true | 0 | Accepted positive control: observed zero remains distinct from missing usage. |
| Popen raises before child exists | 0 | Not reached | Not reached | 1 | Closed: receipt has `child_started=false`, `loaded_a_model=null`, and the startup error. |

Evidence, selected receipts and event traces: [`evidence/request_delta_review_20260923_1204.json`](evidence/request_delta_review_20260923_1204.json). The evidence contains exact reviewed pins, four source-file SHA-256 checks and the preserved harness hash. The helper's public `expected` argument semantics are root's separate review; this review establishes only that actual main passes its two planned requests.

## Remaining delta issue and owner action

At `experiments/live_ab_serving/run_smoke.py:663-665`, the worker retains its old integer/non-boolean predicate without the new nonnegative check. Both `completion_tokens=-1` rows therefore persist `usage_known=true`. `summarize_usage` correctly rechecks with `usable_token_count`, yielding zero known and two unknown rows, total/cap null, and refusal. This is an evidence-label inconsistency, **not an aggregate false pass**. Use the same `usable_token_count` predicate for the worker flag and aggregate, retaining the original negative observation and an explicit unusable-usage reason.

The next bounded owner harness should assert these actual-entrypoint outcomes and receipt consistency while completing the existing acquisition repairs in the authoritative root handoff. This report does not repeat unchanged intent durability, response retention, timeout-attempt accounting, deadline, manifest or artifact-closure tests. Capture-field forwarding is another reviewer's exclusive scope. No owner/shared files were edited, no commit was made, and no paper/package integration or new experiment occurred.

## Reproduction fixture

The self-contained independent harness is [`evidence/request_delta_harness_20260923_1204.py`](evidence/request_delta_harness_20260923_1204.py). It resolves the repository from its own location, checks exact SHA-256 values for `run_smoke.py`, `lab_lifecycle.py`, `lab_common.py` and `lab_data.py`, then refuses source drift. It uses the committed immutable smoke receipt/manifest only as synthetic fixture templates. It requires an explicit `--output PATH`, refuses an existing output before running cases, and creates the final JSON with exclusive mode. There is no fixed report-output path. Other writes are closed temporary files; owner production files are untouched.

Verified once after the output-interface repair, using a fresh output, with:

```text
python3 reviews/evidence/request_delta_harness_20260923_1204.py --output /private/tmp/request_delta_review_1204_iofix_20260923.json
```

The recorded temporary output now exists; choose a fresh path for a later invocation. The owner can adapt this all-mocked entrypoint fixture into its own tests while intentionally updating pins for the repaired source. Do not remove the process/HTTP/signal mocks or use this fixture as authorization to repeat a live smoke.
