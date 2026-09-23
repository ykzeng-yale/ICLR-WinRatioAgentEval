# Independent entry-harness review — 2026-09-23 12:42

**Full-project arXiv readiness: 75%, change 0 points. Bounded-v1: 90%.** Remaining 25 points: prospective study 10 (Session60 collection and root acceptance), expanded final QA 5 (root), and author checks 10 (Yukang). A test scaffold earns no scientific-result credit.

Reviewed main [`2c60654b0968caa7b066e5ede8e248e0430ad15f`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/2c60654b0968caa7b066e5ede8e248e0430ad15f), delivery [`9f1a02da1cdaddc6982eeecf3c7b94c636cd7c25`](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/commit/9f1a02da1cdaddc6982eeecf3c7b94c636cd7c25), relative to `ed528239b11a186e949cffaf0b1d6e03e84a6c11`. Owner artifact: `results/live_ab/SUPERVISOR_ENTRY_HARNESS.json`, timestamp `2026-09-23T12:19:22Z`; new test module: `experiments/live_ab_serving/tests_supervisor_entry.py`.

## Disposition

**Accept a useful eight-case actual-entrypoint scaffold and its eight passing outcomes under the independent guards described below. Do not accept the claim that the owner harness itself mocks all external effects or independently proves the no-read gate.** These test-isolation and assertion limits do not invalidate the already accepted production repairs and do not justify another live smoke or an unchanged full-suite run.

The owner's eight tests were executed exactly once, with 8 passes, 0 failures, 0 errors and 0 skips. No attempted real subprocess, network connection, signal or sleep reached the added denial guards. There was no actual child process, model, HTTP call, native build or full-suite execution. Evidence is [`evidence/entry_harness_review_20260923_1242.json`](evidence/entry_harness_review_20260923_1242.json).

## Independent execution controls and observations

Before loading the owner's tests, the review replaced real process creation, shell invocation, process spawning, socket connections and signals with guards that record and reject attempts. The owner's fake launcher remained its normal synthetic process. Its non-launcher fallback therefore pointed to the independent rejector instead of real `Popen`. The owner's existing `clock_provenance` mock remained in effect.

A fixed synthetic monotonic clock was installed **before** loading `run_smoke`, so `Deadline.__init__` bound that function as its default instead of the import-time real clock. Receipt `_now` fields were synthetic as well. The initial unstarted-filename formatting still read wall-clock `gmtime`; this review does not claim that every wall-clock access was removed or that any elapsed-time boundary was tested. The eight main invocations made 199 calls to the injected monotonic function. Time was held constant, not advanced through a deadline scenario.

A separate `Path.open` spy recorded reads of the closed synthetic lifecycle log and its error sidecar only while actual main was running. The unreapable-child case performed **zero** such read-opens; the valid control performed three. Thus the no-read production behavior is independently corroborated in this execution, beyond the owner's receipt assertions. No actual owner file was being written or analyzed.

| Owner case | Main return | Mock POST calls | Independent lifecycle/sidecar read-opens |
| --- | ---: | ---: | ---: |
| Valid control | 0 | 2 | 3 |
| Broken barrier | 1 | 0 | 3 |
| Popen failure | 1 | 0 | 0 |
| Missing pointer | 1 | 0 | 0 |
| Negative usage | 1 | 2 | 3 |
| Reported zero usage | 0 | 2 | 3 |
| Unreapable child | 1 | 2 | 0 |
| Producer exit 93 | 1 | 2 | 3 |

## Required harness corrections and coverage limits

1. **Remove the real-process escape route.** At lines 208–217, `fake_popen` delegates every command other than the synthetic launcher to a captured real `Popen`. The owner already patches `lab_data.clock_provenance` at line 234, so the comment requiring a real `sysctl` subprocess is not a justification for retaining that fallback. Reject unexpected process creation and provide explicit synthetic provenance. This is an unsafe capability of the current harness, **not an observed subprocess execution in this review**: the independent guards saw zero fallback attempts.
2. **Inject time explicitly and test the changed deadline path when it is repaired.** The owner's patch block at lines 234–244 contains no clock or Deadline injection despite the module/delivery claim of “no real clock.” The immediate fake threads and successful health response make these cases finish quickly, but that is not deadline coverage. Preserve an explicit synthetic clock and account for the import-time default binding; do not infer time isolation from green tests.
3. **Make no-read assertions observe reads.** The unreapable-child case at lines 329–340 checks `observation=null`, `acquisition_not_analyzed`, and absence of a `raw_log` receipt field. Reading that receipt back from disk validates persistence, but does not independently establish that a lifecycle read never occurred. Retain a spy or fail-on-read hook at the actual lifecycle/sidecar read boundary. The extra review spy supplies evidence for this cycle only; it is not part of the delivered owner test.
4. **Represent the coverage inventory accurately.** The eight owner cases preserve four of the earlier six scenarios (barrier failure, Popen failure, negative usage and known zero) and add four (valid control, missing pointer, unreapable child and exit 93). They omit both zero-worker-record and one-worker-record expected-denominator scenarios. Therefore “eight cases” must not be treated as the previous six plus two. The already accepted missing-record closure remains supported by the root's prior independent evidence; its regression witnesses should be retained in the owner harness as that request-lifecycle path changes.

No dedicated rerun of accepted repairs is requested. Fix the harness isolation/assertion gaps while extending only the witnesses needed for the existing remaining acquisition repairs. Pure expected-denominator API validation, the new per-row usage repair, and harness-freeze placement checks belong to root/other reviewers and are not re-reviewed here. Owner/source files and shared trackers were untouched; only this review and its evidence were written. No commit, experiment launch, paper integration or package update occurred.
