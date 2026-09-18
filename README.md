# Guarded win statistics for continuous agent evaluation

Research in progress toward an ICLR submission. **Not yet submission-ready.**

This project studies prespecified hierarchical agent comparisons, the distinction between task-matched offline evaluation and cross-arrival online A/B evaluation, and continuously monitored deployment decisions that also require component safeguards. Established win-statistic and martingale methods are credited explicitly; scientific novelty remains under independent review.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for completion criteria, [evidence/venue_and_novelty.md](evidence/venue_and_novelty.md) for the current literature audit, and [submission/requirements.md](submission/requirements.md) for ICLR 2027 rules.

## Reproduce the initial results

Requires Python 3.11+ and NumPy, SciPy, pandas, matplotlib.

```sh
python src/test_winstats.py
python experiments/run_simulations.py --replicates 2000 --pairs 10000
python experiments/run_stress_tests.py
```

The first study comprises six synthetic stationary scenarios. The separate stress tests examine boundary nulls, reused-run dependence, and adaptive randomized order. Monte Carlo rates and uncertainty are in `results/`; manifests record seeds, assumptions and source hashes. Public-agent benchmark reanalyses are being added with original-source provenance. No synthetic stream or historical replay is a live production A/B experiment.

## Commercial model experiments

Only inexpensive authorized models may be used. The initial total project budget is capped at USD 5, with usage tracked before any expansion. Credentials are held outside this repository and must never be committed. No production users or external actions are involved in local benchmark environments.

## Scientific review and anonymity

The `reviews/` directory will contain independent model-assisted scientific reviews and the response ledger. These are internal quality checks, not external peer review or human proof certification. The final submission PDF and supplementary archive must be anonymous even though this development repository is public. Public author-identifying repository links must not appear in anonymous submission materials.
