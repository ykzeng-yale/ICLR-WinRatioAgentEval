# Drift and unequal-law-null panel

Synthetic, CPU-only Monte Carlo for the guarded monitoring rules (EXPERIMENT_QUEUE: "Focused common-drift, treatment-by-time drift, and unequal-law null panel"). No model or API calls. Extension designed after the first simulations; internally frozen, not publicly preregistered.

- `protocol.md`: frozen plan (sha256 `bb497cbb7c58fd1578530748c9d5ef834dc079e8b14973bc0bee348ca5c276cc`, stored in the manifest; the runner refuses to start on a mismatch).
- `run_drift_panel.py`: scenarios, exact targets, rules, events, MC target verification through `winstats.compare`, permutation contrast.
- `make_figures.py`: figures from `results/drift_panel/results.csv` (no simulation).

Reproduce (about 1 minute with 5 workers; results do not depend on the worker count):

    python experiments/drift_panel/run_drift_panel.py --design-check        # deterministic target paths only
    python experiments/drift_panel/run_drift_panel.py --workers 5 --protocol-sha256 <sha256 of protocol.md>
    python experiments/drift_panel/make_figures.py

Outputs in `results/drift_panel/`: `results.csv` (12 scenarios x 9 rules), `permutation_results.csv`, `manifest.json`, `run.log`, `figures/`. Interpretation: `evidence/drift_panel_report.md`.

`--smoke` with `DRIFT_SMOKE_DIR=<scratch dir>` runs a tiny crash test on a different seed and never writes into `results/`.
