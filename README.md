# Guarded win statistics for continuous agent evaluation

Research in progress toward an ICLR submission. **Not yet submission-ready.**

This project studies prespecified hierarchical agent comparisons, the distinction between task-matched offline evaluation and cross-arrival online A/B evaluation, and continuously monitored deployment decisions that also require component safeguards. Established win-statistic and martingale methods are credited explicitly; scientific novelty remains under independent review.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for completion criteria, [evidence/venue_and_novelty.md](evidence/venue_and_novelty.md) for the current literature audit, and [submission/requirements.md](submission/requirements.md) for ICLR 2027 rules.

## Reproduce the results

Use the exact numerical dependency versions in requirements.txt; see REPRODUCIBILITY.md for the one-command entrypoint and standalone archive instructions.

```sh
python src/test_winstats.py
python experiments/run_simulations.py --replicates 2000 --pairs 10000
python experiments/run_stress_tests.py
```

The first study comprises six synthetic stationary scenarios. The separate stress tests examine boundary nulls, reused-run dependence, and adaptive randomized order. Monte Carlo rates and uncertainty are in `results/`; manifests record seeds, assumptions and source hashes. The executed package also includes 3,936 public agent trajectories, a 2,000-repetition delay study, decision/grader ablations, a complete-data Dirichlet-mixture reference, and an 18-trajectory prospective Haiku workflow pilot with three planned task pairs unobserved. No synthetic stream or historical replay is a live production A/B experiment.

## Commercial model experiments

Only inexpensive authorized models may be used. The initial total project budget is capped at USD 5, with usage tracked before any expansion. Credentials are held outside this repository and must never be committed. No production users or external actions are involved in local benchmark environments.

## Scientific review and anonymity

The `reviews/` directory contains multiple model-assisted scientific reviews and the response ledger. These are internal quality checks, not external peer review or human proof certification. The final submission PDF and supplementary archive must be anonymous even though this development repository is public. Public author-identifying repository links must not appear in anonymous submission materials.

The public work queue is [EXPERIMENT_QUEUE.md](EXPERIMENT_QUEUE.md). Check [COORDINATION.md](COORDINATION.md) before contributing. Root integrates the paper and releases; workers own separate files. All paid requests have stopped. Total accounted cost is USD3.9476608, including retained reservations, under the initial USD5 cap. This is usage-based accounting, not a reconciled provider invoice.
