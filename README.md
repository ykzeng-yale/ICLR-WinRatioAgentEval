# Guarded win statistics for continuous agent evaluation

The active target is a named **arXiv preprint**, prepared at **90% checklist readiness**. Start with [the arXiv handoff](arxiv/READ_ME.md): full paper, separate main/supplement reading copies, source upload and reproducibility archive. The author selected arXiv’s non-exclusive license. Actual scientific review and arXiv account/declarations remain outstanding; nothing has been uploaded or attested. See [READINESS_TRACKER.md](READINESS_TRACKER.md) for the explicitly migrated fixed rubric and 90-minute GitHub/progress updates.

This project studies prespecified hierarchical agent comparisons, the distinction between task-matched offline evaluation and cross-arrival online A/B evaluation, and continuously monitored deployment decisions that also require component safeguards. Established win-statistic and martingale methods are credited explicitly. The latest independent AI review describes a credible focused methodology submission with borderline ICLR strength; it does not predict acceptance.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for completion criteria, [evidence/venue_and_novelty.md](evidence/venue_and_novelty.md) for the current literature audit, and [evidence/arxiv_requirements.md](evidence/arxiv_requirements.md) for current arXiv preparation requirements. ICLR rules and archives remain historical.

## Reproduce the results

Use the exact numerical dependency versions in requirements.txt; see REPRODUCIBILITY.md for the one-command entrypoint and standalone archive instructions.

```sh
python src/test_winstats.py
python experiments/run_simulations.py --replicates 2000 --pairs 10000
python experiments/run_stress_tests.py
```

The first study comprises six synthetic stationary scenarios. The separate stress tests examine boundary nulls, reused-run dependence, and adaptive randomized order. Monte Carlo rates and uncertainty are in `results/`; manifests record seeds, assumptions and source hashes. The executed package also includes 3,936 public agent trajectories, a 2,000-repetition delay study, decision/grader ablations, a complete-data Dirichlet-mixture reference, and an 18-trajectory prospective Haiku workflow pilot with three planned task pairs unobserved. An independently reconstructed ordinal replay certifies 3,426 of 10,008 archived comparisons before the later terminal marker; 2,595 certify while actual assistant messages remain unseen. No synthetic stream or historical replay is a live production A/B experiment.

The package also includes 1,182 open-weight coding episodes and all 196 planned interactive airline records: 194 saved trajectories and two failure placeholders, reconciled to 206 attempts. Their accepted analyses distinguish post-hoc running means, descriptive batch outcomes and conditional replay from live deployment. All earlier numerical results remain unchanged.

The current [arXiv package](arxiv/) contains a 45-page combined PDF, 13-page main/statements/reference extract, 32-page supplement, 35-file source upload, and a code archive with 246 hashed payload files. Independent clean compilation, six analytic checks and 127 retained-result checks pass; layouts were visually inspected. All old data and the original anonymous [ICLR release](submission/) remain unchanged. [Issue 11](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11) continues prospective open-weight work in separately owned directories; [issue 12](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/12) requests its CPU validation. New results require review before integration.

## Experiment execution policy

**No further commercial/proprietary-model experimental calls are authorized**, including agents, simulators, judges and fallback models. Use open weights/open-source systems under [EXPERIMENT_POLICY.md](EXPERIMENT_POLICY.md); earlier cheap-model allowances are superseded. Historical commercial observations remain preserved, with collection scripts excluded from authorized execution. No production users or external actions are involved in these local benchmark environments.

## Scientific review and publication status

The `reviews/` directory contains multiple model-assisted scientific reviews and the response ledger. These are internal quality checks, not external peer review or human proof certification. The arXiv article identifies the sole author and public repository. The preserved historical ICLR package remains anonymous. Internal reviews are not an arXiv moderation decision, acceptance, or author certification.

The public work queue is [EXPERIMENT_QUEUE.md](EXPERIMENT_QUEUE.md). Check [COORDINATION.md](COORDINATION.md) before contributing. Root integrates the paper and releases; workers own separate files. All paid requests have stopped. Total accounted cost is USD3.9476608, including retained reservations, under the initial USD5 cap. This is usage-based accounting, not a reconciled provider invoice.
