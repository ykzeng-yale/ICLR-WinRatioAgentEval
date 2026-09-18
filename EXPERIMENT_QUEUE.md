# Experiment delivery and remaining work

**Round 10, September 18, 2026, approximately 23:15 UTC: verified package readiness is 70%.** The accepted sequential-comparison and drift studies are integrated into the revised 36-page review package. The open-weight coding records are reproduced, but their uncertainty repair remains incomplete. The airline study is awaiting final delivery. See [READINESS_TRACKER.md](READINESS_TRACKER.md) for the unchanged 20-milestone rubric; partial progress is not an entire completed milestone.

**No further commercial/proprietary-model calls are authorized.** All new experimental agents, simulators, graders and fallbacks must use open weights/open-source systems under [EXPERIMENT_POLICY.md](EXPERIMENT_POLICY.md). Older USD5/4 allowances are historical and superseded. Closed-pilot accounted cost remains USD3.9476608 including retained reservations; this review added no model calls or spending.

Claim an issue before new work. Use a separate branch/worktree and preserve the named owner's files. Return exact inputs, commands, revisions, provenance, uncertainty, limitations and resource use. Do not commit credentials, model caches or private transcripts. Root selectively integrates reviewed files; an accepted subset does not approve an entire contributor branch.

## Verified delivery status

| Study | Current evidence | Remaining boundary / owner |
|---|---|---|
| Core stationary/stress/delay/grader simulations; isolated DM reference | Executed, reviewed and included; original release preserved at `f806aba` | No blanket rerun required. Executed panels/counts define the evidence, not every item in the original protocol. |
| Historical trajectories and actual archived trace prefixes | Included: 3,936 trajectories; 10,008 comparisons and 195,171 prefix checks | Historical/ordinal replay; no production latency claim. |
| Closed commercial telecom pilot | 18 episodes / 9 complete pairs; 3 planned pairs unobserved | Historical evidence only. Do not restart. |
| Competitive sequential U-statistic reference, [PR 7](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/7), `ac17f5901bcf4efba6c71e970d3a4c1cf1ed06cb` | Eight scenarios × 2,000 repetitions plus four boundary scenarios × 10,000. Corrections closed; diagnostic rerun byte-identical; original outputs preserved; accepted subset integrated. | This audit does not claim an independent rerun of all 56,000 comparator replicates. Original session60/contrib owner retains source ownership. Other branch changes are not approved by this integration. |
| Drift/unequal-law study, [PR 10](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/10), `ae3f0a5d4936855fc0b81f4a327254e932ea729b` | All 96,000 sequential and 14,000 permutation repetitions independently rerun; both numerical CSVs byte-identical; exact targets separately checked; accepted and integrated. | CPU synthetic evidence. Initial uncorrected diagnostic run was not retained; freeze chronology cannot be independently reconstructed. No universal power or production claim. Do not duplicate. |
| Open-weight coding workflow, [PR 8](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/8), `c89b525cd8e51564ca8c23399201d9cfdf0431a3` | Complete collection: 591 tasks, 1,182 Qwen2.5-Coder episodes. Raw preservation, pinned benchmark sources and version-2 aggregate reconstruction passed. Same observed successes, 433/591 per workflow. | Excluded from current paper/archives pending shared-orientation/pass dependence, endpoint and claim/provenance repairs. CPU analysis only; preserve all observations. Owned by session60/local-stream. |
| Open-weight interactive tau2 airline, same PR 8 | Design: 49 tasks × 2 trials × 2 arms = 196 planned. Owner's last posted report: 21:44 UTC, A27/98, B0/98 saved under invocation 2 with amended settings. | No final real invocation artifacts delivered at checked head; only design and explicitly MOCK dry-run files. Old owner report is not a current process check. Same owner retains exclusive execution. |

## Remaining required repairs and integration

1. **PR 8 same-task uncertainty:** shared orientation assigns complementary collection-pass positions to two tasks. Task-specific period effects can therefore induce dependence even with separate model calls. The task-level t/Hoeffding results require a stable independent task-outcome model, or replacement with justified cluster/design-based uncertainty that handles the singleton and pass effects. State nondegeneracy/variance-growth conditions for asymptotic normality. Keep the R1 running conditional-mean target separate from a fixed roster or superpopulation target.
2. **PR 8 endpoint arithmetic:** the corrected two-sided hedge is appropriate, but `0*log(0)` drops a zero-count term. Empty/all-one endpoint checks should return exact capital 1, not 0.9875. The identified examples are conservative; they are not evidence of undercoverage. Correct masked log terms and regenerate versioned aggregates without model inference.
3. **PR 8 provenance and labels:** fix the anonymous map entry pointing to an absent release data manifest; reconcile the stale PR-body intervals. Preserve prior analyses and all source hashes. A composite harm signal retaining the incumbent is not reverse guarded approval; the success result is not robust noninferiority. Label R2 as an explicit modeling assumption, not proven roster randomization.
4. **Airline final delivery:** retain original and amended invocation files, all failures/truncations, configuration/token-cap changes and missingness. Audit all-A-then-all-B collection, replay order, shared-seed/repeated-task dependence, the first five uncapped episodes and all execution deviations. No physical randomized-arrival or measured online stopping claim follows from batch replay.
5. **Final package:** after corrected analyses are reviewed, integrate only retained claims, revise the protocol ledger and abstract if needed, rebuild and independently inspect the final archives/PDF. Human scientific signoff and actual author/profile/declaration inputs remain separate.

The owner handoff is the [Round 10 PR 8 comment](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/8#issuecomment-5737168893). Independent findings are in [coding audit](reviews/round10_open_model_repair_audit.md), [sequential audit](reviews/round10_sequential_corrections_audit.md), and [drift audit](reviews/round10_drift_panel_audit.md). No additional full simulation or repeated model collection is needed to repair the coding claims.

## Additional experiments by scientific priority

| Priority | Work | Acceptance condition |
|---|---|---|
| High value; already owned | Finish/audit the existing airline design | Interactive tool-use evidence with every enrolled failure retained; no post-outcome hierarchy/margin change. Await owner delivery, no duplicate runner. |
| Completed and integrated | Focused drift/unequal-law panel and rare-compliance diagnostic | Round 10 reviews establish current numerical validity and bounded interpretations. No repeat required. |
| Conditional requirement | Actual concurrent open-model prefix experiment with reveal timestamps | Required only for measured operational latency-saving claims. Existing synthetic/ordinal evidence supports the narrower current claims. |
| Optional / deferred | Additional model sizes/hardware, full original tie/Pareto-cost/grader grids, larger power panels and production workloads | Broaden generalization; not prerequisites to correct current bounded claims. A favorable result is never a completion criterion. |

The broad original protocol proposed additional panels and 5,000 repetitions for some power studies; principal delivered power studies use 2,000. The paper now explicitly records these deferred items and actual counts.

## Existing issue ownership

[Issue 1](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/1) and [issue 2](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/2) are served by PR 8; [issue 3](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/3) by PR 7. [Issue 4](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/4)/PR 5 generic projections and [issue 6](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/6) replay corrections retain their owner and need separate validation before any retained use. Generic contributed projections remain excluded from submission claims and archives.
