# Experiment delivery and remaining work

**Hourly-monitor update, September 18, 2026, 21:46 UTC:** new heads PR 7 `ac17f590`, PR 8 `e0610088`, and the CPU drift panel PR 10 `ae3f0a5` have been received and await independent root validation. The airline owner reports 27/196 episodes saved at 21:44 UTC under an amended second invocation. These newer deliveries supersede the receipt status below, but do not close the outstanding validation conditions. See [READINESS_TRACKER.md](READINESS_TRACKER.md) for the fixed readiness rubric (currently 70%), exact pending heads and hourly follow-up instructions. Do not duplicate the now-delivered drift panel.

Last checked September 18, 2026, approximately 19:50 UTC. This is a delivery/validation ledger, not a claim that all original planned experiments or paper integration are complete.

**No further commercial/proprietary-model calls are authorized.** All new experimental agents, simulators, graders and fallbacks must use open weights/open-source systems under [EXPERIMENT_POLICY.md](EXPERIMENT_POLICY.md). Earlier USD 5/4 allowances are historical and superseded. The closed pilot's accounted cost remains USD 3.9476608, including retained reservations; no spending was added by this audit.

Claim an issue before new work. Use a separate branch/worktree and preserve the named owner's files. Return exact inputs, commands, code revisions, provenance, estimates, uncertainty, limitations, and resource use. Do not commit credentials, model caches, private transcripts, or large raw artifacts.

## Verified delivery status

| Study | Current evidence | Remaining boundary / owner |
|---|---|---|
| Core stationary/stress/delay/grader simulations; isolated DM reference | Executed, reviewed and included in scientific release `f806aba` | No blanket rerun required. Executed panels and counts, not the entire original protocol, define the evidence. |
| Historical trajectories and actual archived trace prefixes | Included: 3,936 trajectories; 10,008 comparisons and 195,171 prefix checks | Historical/ordinal replay; no production latency claim. |
| Closed commercial telecom pilot | 18 episodes / 9 complete pairs; 3 planned pairs unobserved | Historical evidence only. Do not restart; frozen baseline retained. |
| Competitive sequential U-statistic reference, [PR 7](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/7) at `cfc1850` | Eight scenarios × 2,000 repetitions, plus four boundary scenarios × 10,000 repetitions delivered. Round 9 verified table counts/intervals, hashes, matching conventions and 16/16 existing betting rows. | Correct interpretation/diagnostic provenance before integration. No additional full simulation is required for the narrow descriptive comparison. Existing session60/contrib owner retains code ownership. |
| Open-weight coding workflow experiment, [PR 8](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/8) at `ab24f1b` | **Complete collection:** 591 MBPP/HumanEval tasks, 1,182 local Qwen2.5-Coder episodes; two workflows. Same observed successes (433 each); repair workflow's measured mean latency/token ratio approximately 4.46. | Raw evidence delivered; integration blocked on two-sided CS construction and sampling/target interpretation. Preserve data; regenerate corrected analysis without new model calls. Owned by session60/local-stream. |
| Open-weight interactive tau2 airline, same PR 8 | Frozen design: 49 tasks × 2 trials × 2 arms = 196 planned episodes. Owner reported running at 18:00 UTC. | At audited head, only design + explicitly MOCK dry-run artifacts were deposited; final real outcomes absent. Live execution is not independently verified. Same owner retains the job. |

PR 8 fills the previously unexecuted local-model/coding-stream slot. Its airline extension is a separate pending study. A design, claim comment, or dry run is not completed experimental evidence.

## Required before integrating incoming results

1. **PR 8 analysis repair, no new inference calls:** its imported two-sided betting code uses `max(K+, K-)` at `1/alpha` without splitting the tail error budget. Correct the construction, check boundaries, and regenerate affected intervals/plots. Separately resolve fixed-roster sampling without replacement versus the claimed stationary conditional-mean assumptions. A corrected tail budget alone does not repair that sampling mismatch. Use justified inference for the actual target or report monitor paths/crossings descriptively.
2. **PR 8 execution and decision labels:** coding collection and airline collection have different schedules. Airline runs all A then all B and constructs its prespecified stream afterward; do not label this physically randomized arrival-order execution. Address repeated-task/shared-seed dependence, and distinguish retaining an incumbent after a harm signal from proving reverse guarded approval.
3. **PR 7 interpretation:** preserve finite-sample versus asymptotic status, same-look versus retained rules, equal 2N execution budgets, and component-error versus guarded-deployment-error distinctions. Correct residual-variance prose and archive the precise diagnostic behind any retained mechanism claim. See [sequential audit](reviews/round9_sequential_results_audit.md).
4. **Integration/release:** independently reproduce accepted aggregate analyses, map claims to outputs, update the paper, rebuild anonymous artifacts, and inspect the exact PDF. PRs remain unmerged and excluded from the current frozen release until then.

The concrete owner handoff is [PR 8 review comment](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/8#issuecomment-5735373522). It asks for a timestamped job status and completion/missingness counts, not a duplicate run or a restart. The [independent empirical audit](reviews/round9_open_model_evidence_audit.md) also specifies pinned benchmark-source provenance, the missing data-manifest handoff, and anonymous release path cleanup.

## Additional experiments by scientific priority

| Priority | Work | When needed / acceptance criterion |
|---|---|---|
| High value; already owned | Finish and audit the existing open-weight airline design | Extends fresh evidence to interactive tool use. Retain every enrolled unit and failure; abstention is acceptable. Do not change the hierarchy/margin after outcomes. |
| High value; CPU only, not yet claimed | Focused common-drift, treatment-by-time drift, and unequal-law null panel | Useful for a stronger empirical online-monitoring claim. Prespecify the target/null and false-deployment event; separate stationary conditional-null guarantees from running-average targets. Report Monte Carlo intervals and matched budgets. |
| Conditional requirement | Actual concurrent open-model prefix experiment with reveal timestamps | Required if claiming measured operational latency savings. Current synthetic/ordinal evidence supports only the narrower claims already stated. No production-user study is needed to retain those limited claims. |
| Conditional requirement | Archive existing PR 7 rare-compliance diagnostic, or run only that narrow CPU diagnostic | Required to retain its precise unarchived diagnostic numbers; qualify/remove the mechanism claim instead if not retained. A proposed remedy would need an independently seeded test. |
| Optional / deferred | More model sizes/hardware, full original tie/Pareto-cost/grader grids, larger replication counts, production workloads | Broaden robustness/generalization; not a requirement to repair current bounded results. No favorable finding or arbitrary experiment count is a completion criterion. |

The original protocol proposed additional panels and 5,000 repetitions for some power studies; the principal delivered studies use 2,000. These deviations must be explicit, not silently labeled complete. See [independent gap assessment](reviews/round9_experiment_gap_assessment.md).

## Existing issue ownership

[Issue 1](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/1) and [issue 2](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/2) are served by PR 8; [issue 3](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/3) by PR 7. [Issue 4](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/4)/PR 5 generic projections and [issue 6](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/6) replay corrections retain their existing owner and need separate disposition before any use. The generic contributed projection module remains excluded from the frozen submission package.
