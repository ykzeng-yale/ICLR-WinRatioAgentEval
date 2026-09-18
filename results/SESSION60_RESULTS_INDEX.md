# Session 60 results index (aggregated; updated by the 30-minute coordination loop)

Last updated: 2026-09-18T21:50Z. Owner: session `iclr-winratioagentevals-60`. All work is on `session60/*` branches and returned by pull request; the root session owns the manuscript, the release archives and integration. No commercial or proprietary model was called by this session; since 2026-09-18 all fresh executions use open-weight models only (EXPERIMENT_POLICY.md on main).

## Deliverables

| # | Deliverable | Where | Head | Status |
|---|---|---|---|---|
| 1 | Library fix for issue #4 (exact boundary laws, shift-invariant certified bounds, hedged betting CS, robust inversion) | PR #5, branch `session60/wincs-fix` | b14e820 | Delivered; all root review points and independent-audit defects answered; awaiting root merge |
| 2 | U-statistic sequential reference baseline (issue #3) + Round 8 and Round 9 corrections; real-data decision evidence; replay; online-method study; reviews; positioning; abstract options | PR #7, branch `session60/contrib` | ac17f59 | Delivered; Round 9 corrections answered; awaiting root integration |
| 3 | Open-model prospective coding stream (issues #1/#2), Round 9 analysis/provenance repair | PR #8, branch `session60/local-stream` | e061008 | Collection complete (1,182 episodes); repair delivered and independently verified 7/7 |
| 4 | Open-model tau2-bench airline stream (issues #1/#2) | PR #8, same branch | design frozen 696fe57; deviation 1 at 4f01206 | RUNNING (invocation 2 under the documented amendment) |
| 5 | Drift / treatment-by-time / unequal-law null panel (issue #9) | PR #10, branch `session60/drift-panel` | ae3f0a5 | Delivered; independent audit 13/13 PASS; awaiting root review |
| 6 | Issue #6 replay fixes (single task draw, process-independent seeds, conflict policy) | PR #7 | ac17f59 | Delivered with acceptance tests |

## Headline numbers and where they live

**Open-model coding stream (frozen design d9793d5; Qwen2.5-Coder-7B-Instruct 4-bit, local; 591 MBPP-sanitized + HumanEval tasks; A single-shot vs B self-test-and-repair).** Files: `results/local_stream/report_v2.md`, `summary_v2.json`, `episodes.jsonl`, `monitor_pass1.csv`, `analysis_v2_manifest.json`; v1 outputs preserved in `v1_pre_round9/`.
- Pre-registered H1 (B has higher success) not supported: 433/591 successes in both arms; same-task difference 0.000 (t interval [-0.0297, 0.0297]; clears the -0.03 margin by 0.00025 only, not a robust non-inferiority result).
- B uses 4.46x latency (12.48 s vs 2.80 s), 4.46x completion tokens and 7.4x prompt tokens; 1,748 vs 591 model calls.
- Cross-arrival contrast (295 prespecified pairs): net benefit -0.471; corrected betting CS [-0.628, -0.288] under the iid-roster assumption (R2); design-based running-average CS [-0.654, -0.288] with no sampling assumption (R1). Same-task contrast: -0.657 (t interval [-0.705, -0.608]; Hoeffding [-0.768, -0.545]).
- Monitoring: harm e-process first read crossing at pair 24; win and success-gate e-processes never crossed. Label: composite harm signal for B; incumbent A retained (not a success or safety harm, not a reverse approval).

**Open-model tau2-bench airline (A = Qwen2.5-7B-Instruct, B = Qwen3-4B-Instruct-2507, user simulator Qwen2.5-7B; llama.cpp; tasks 1-49 x 2 trials x 2 arms = 196 planned units).** Files: `experiments/tau2_open/{protocol.md,protocol_addendum_round9.md,deviation_1_runaway_generation.md,config_amendment_1.json}`, `results/tau2_open/`. Status at 21:44Z: arm A 27/98 units saved (4 successes; 17 user_stop, 5 too_many_errors, 4 max_steps, 1 infrastructure_error retained), arm B not started. Description to be used: prospectively specified batch collection with a prespecified replay analysis.

**U-statistic reference baseline (8 scenarios x 2,000 reps; 4 boundary nulls x 10,000 reps).** Files: `evidence/ustat_reference_report.md`, `results/ustat_reference/` (incl. `rare_event_diagnostic.csv`). All-pairs vs disjoint-pair asymptotic relative efficiency 1.13-1.41 for net benefit, exactly 1.0 for the component gates; projection-Gaussian component compliance-gate false rejections 7.25% [6.76, 7.77] vs simultaneous guarded deployment 1.83% vs retained-crossing 7.11% (three distinct events); exact betting rule 0.76% at the compliance gate; simultaneous disjoint betting rows reproduce the paper's rows exactly.

**Drift / unequal-law null panel (12 scenarios x 9 rules; protocol sha256 bb497cbb...).** Files: `evidence/drift_panel_report.md`, `results/drift_panel/`. Guarded betting ever-false-deployment under common drift: 0.55% [0.42, 0.72] identical null, 0.38% at each guardrail boundary; repeated Wald 27-31%; running-average false deployments under treatment-by-time drift at most 0.01% for betting and normal-mixture rules; unequal-law nulls have net benefit 0 to machine precision and are controlled while a permutation test of equality rejects. Limitation: the normal-mixture rules never deploy in the alternating-component cells, so the alpha split is not demonstrated empirically.

**Real-data decision evidence on archived trajectories (tau2-bench, SWE-bench Lite, HAL airline).** Files: `results/benchmarks/decision_matrix.csv`, `decision_matrix_summary.json`, `tau2_contrasts.csv`, `label_noise_sensitivity.csv`, `results/replay/`. 25 ordered contrasts; rules disagree on 19; 9 priority inversions (4 with net-benefit interval excluding 0); guarded rule decides 10, incumbent per-metric conjunction 6; the guarded rule never changes the winner named by success-only inference at archived sample sizes; marginal decisions flip in 27.5% of replicates under 1% label noise.

## Open requests from the root session

None unanswered as of the last update. Pending on the root side: review/merge of PRs #5, #7, #8, #10 and manuscript integration. Pending on this side: completion, deposit, analysis and report of the tau2 airline run.
