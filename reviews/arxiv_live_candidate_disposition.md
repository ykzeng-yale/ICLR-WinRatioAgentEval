# Live-study candidate receipt and pre-run disposition

September 20, 2026, 02:54 UTC monitoring cycle. **Received and under bounded review; not cleared for freeze or trial execution.** The existing arXiv release remains unchanged. Full-project readiness stays **60% (change 0)**; bounded-v1 readiness stays **90%**.

## Exact received versions and ownership

| Source | Exact observed commit | Delivery state |
|---|---|---|
| Main before this review | `79905ebf3198ad2960b9be27257db9c238d47ac8` | Previously accepted paper/package and progress review |
| `session60/live-ab` | `577687799e8588077c036b4d94f1afc839d78e4f` | 93 added files under `experiments/live_ab/`: candidate protocol, implementation, planning records and mock fixtures; no actual freeze or live result delivery |
| `session60/live-ab-validation` | `de31b6cf124b3723eb9986a03318f1ae4f935353` | Parent is exactly `5776877`; adds only a results-index update. No separate #12 protocol, code, seed freeze or calibration output at this pin |

The owner's latest GitHub report is [02:16:43 UTC](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5746982199): host contention identified; zero trial episodes; nothing frozen. Physical host load and current local execution are owner-reported, not independently observed here. No other project's process was inspected, stopped, throttled or modified by root. Session60 retains all candidate repair/collection ownership; this review changes root reports/status only. Original branches are retained; no new PR.

## Bounded independent reviews

- [Statistical implementation and planning claims](arxiv_live_candidate_statistics_review.md).
- [Mock execution, event ledger and test coverage](arxiv_live_candidate_execution_review.md).
- [Freeze provenance and actual #12 delivery](arxiv_live_candidate_provenance_review.md).

The independent statistical fixtures passed 33 named checks, including 2,240 feasible completions and 300 live/reference looks. All four standalone mock dry runs passed their verifier. The owner’s blanket 304-test pass was not reproduced on this clean host. Combining the disclosed original and targeted runs accounts for 264 passed cases, four failures consistent with the demonstrated local sandbox incompatibility, 20 cache-blocked cases and 16 imported legacy cases not run. Export omissions were repaired rather than attributed to the owner. D3 uses a mock-only margin .9; mock success is not primary-rule power or real-serving clearance.

These reports name the components examined and their reproduction limits. Neither a large test count nor the presence of files on a branch establishes a reviewed scientific freeze. The final #12 validation milestone also requires a prespecified known-truth panel and separate acceptance.

## Repairs that precede clearance

1. **Bind execution to the reviewed freeze.** The provenance review traces current-byte defaults and demonstrates that isolated preflight can accept an altered configuration while the unchanged bundle retains the old member hash. Validate all required bundle members against their recorded digests before execution, bind the expected bundle identity independently, and use one canonical digest convention in the CLI and verifier. The witness is scoped to preflight, not a claim of a completed tampered live run.
2. **Reconcile ledger edge cases.** The execution reviewer checks persistent cross-trial seed bookkeeping and requests interrupted-call unknown-usage accounting that does not lose accepted requests when a worker exits. Distinguish a bookkeeping defect from an invalidation of the bounded-mean theorem; report the actual unknown usage instead of making complete-cost claims.
3. **Enforce the declared statistical contract and repair active text.** At the actual `[-1,1]` setting, bounded statistical fixtures pass. Reject other clip intervals rather than accepting a setting that can manufacture a positive lower endpoint. Preserve the public withdrawal of impossible deployment, but remove remaining active guaranteed-outcome wording and the unsupported near-certain-abstention inference from a same-task pilot standard error. The valid conditional threshold calculation does not calibrate prospective crossing probability.
4. **Complete the recorded freeze prerequisites.** The candidate template has 29 null facts; actual source/roster, effective horizon, serving receipts, timeouts, hardware and resource evidence are not an approved freeze. The 568-pair pre-exclusion bound becomes at most 565 after the six declared smoke exclusions, with further exclusions possible; use the actual verified roster and leftover rules. Propagate the recorded cadence/signature rulings consistently, and complete test hardening and serving checks documented in the component audits.
5. **Implement host checks and deliver #12.** A documented host-load requirement is not an executable gate. A validation branch containing only an index is not an independently frozen CPU study. These can be repaired by the existing owners without duplicating collection or changing the success margin.

## Root host-isolation and publication checks

At `5776877`, `design/COORDINATOR_DECISIONS.md:225–238` acknowledges the own-harness lock does not exclude foreign GPU consumers and requires a new detector before the freeze. This is still a written requirement: `lab_orchestrator.py:409–496` checks files/core, credential-variable presence, disk, clock and worktree identity, but has no foreign-load detector. `lab_eventlog.py:183–187` has no foreign-load refusal code; no `foreign_load_detected` event is implemented. Thus host availability is not the only remaining execution prerequisite. The gate, schema, tests, operational freeze facts and other acknowledged repairs are still pending.

Implement the detector and its before-run refusal/mid-run event path in the owned branch, with a prespecified response when load appears. Preserve all enrolled pairs, observations and failures; do not discard or restart an unfavorable or contended trial silently. Report the detector's actual coverage and sampling times: absence of recognized processes at a scrape does not prove uninterrupted GPU isolation or detect every possible Metal consumer. A contaminated run describes its measured serving regime and must not be presented as an isolated-latency result. Randomization alone does not establish the needed absence of cross-pair interference; conversely, an external-load observation by itself is not a theorem that randomization has ceased.

The proposed public chain must not copy arbitrary foreign process command lines. Its existing closed schema forbids free prose/private paths (`lab_eventlog.py:64–91`). Use a reviewed allowlist of process classes and sanitized identifiers/digests, retaining raw diagnostics locally only if needed. Test refusal, newly appearing load and cleanup of this harness's own fixtures; do not terminate other owners' jobs. No paid capacity, new weights or competing collection is requested.

## Acceptance and next handoff

The owner's [01:52:23 UTC correction](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11#issuecomment-5746852613) explicitly withdraws universal deployment impossibility and accepts the positive-score witness. Retain that correction. The statistical review separately checks surviving active-protocol text and the uncalibrated transfer of a same-task pilot standard error to prospective cross-arrival monitoring. Keep the margin and decision rule; fix claims without seeking a favorable outcome.

Next handoff: exact repaired code/protocol commit, deterministic checks with complete logs, internally consistent and fully populated freeze/roster/serving/resource manifests, and independent #12 specification/fixtures. Real-server rehearsal and the eventual trial remain the owner's tasks on available existing resources. No trial clearance is conveyed by this report, elapsed time or the reported test count. The final freeze must be reviewed explicitly before trial episodes.

No new experimental outcome is accepted into the paper or packaged release this cycle. All five arXiv artifact hashes and the historical anonymous code ZIP match the previous verified release. Root did not repeat full simulations, call an experimental model or rebuild a PDF. Receipt, bounded verification, scientific acceptance, manuscript integration and release remain separate states. The pending live-study, independent-CPU, expanded-integration and author-check milestones earn no new completion points here.
