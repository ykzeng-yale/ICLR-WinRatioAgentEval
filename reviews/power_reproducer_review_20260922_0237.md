# Saved-record power reproducer — 2026-09-22 02:37 cycle

## Delivered scope and disposition

Delivered `arxiv/additions/reproduce_power.py` and `arxiv/additions/power_manifest_spec.json`. The latter is a complete package manifest, ready to copy as `power_diagnostics/manifest.json`. Copy the script beside it and copy each `primary_files[].source_path` byte-for-byte to `power_diagnostics/<path>`. The script uses only Python's standard library, defaults to its own directory, imports no project module, and does not invoke Git, a model, a simulator, or a network service. Python 3.9 or later is required (`Path.is_relative_to`). Root owns builder/manuscript integration; neither was edited here.

**Saved-record reconstruction passes.** This verifies deposited bytes and summary arithmetic; it is not an independent regeneration of trial outcomes or a repair of historical execution provenance. The accepted coarse/fine retrospective source-binding and lost coarse-attempt qualifications remain. Ablation uses the original coarse coordinates, not an independent sample. Only corrected disabled-arm files enter reconstruction; this choice does not erase the first attempt or the accepted accounting of 64,000 evaluations across two disabled attempts.

## Pins and package contract

| Panel | Exact primary-record pin | Files | Construction records |
|---|---|---:|---:|
| Coarse | `0c17857f6b0eb6a37f222a264294cfc9fe65b7e7` | 40 | 240,000 |
| Fine | `2c09a167afd3bdfa404512d668aa1b2b5502fe1b` | 24 | 144,000 |
| Corrected disabled arm | `6bdefd1c052a178654e237d931de9fe1964a697e` | 16 | 96,000 |

All 80 current primary gzip files were compared byte-for-byte with their exact accepted Git blobs before creating the manifest and isolated scratch package. Their compressed payload totals 15,946,346 bytes. Counts/interval expectations come from the coarse `PC_ANALYSIS.json`, fine `COMBINED_CURVE.json` at the listed pins, and the accepted interval update's `ABLATION_ANALYSIS.json` at `4a9f70423b6abb6e954cd15ee39301f6025ba392`. These summary-source hashes are recorded separately as provenance; expected numeric subsets are embedded in the manifest, so the standalone reader does not need to import the original analysis code.

Manifest keys: `schema_version`, `panels`, `primary_files`, `expected`, `expected_summary_sources`, and `scope`. Each primary entry contains `panel`, `path`, `source_path`, `source_commit`, and `sha256`. Plotting can read `expected.panels.coarse[cell]` and `.fine[cell]`, each with `trials`, `deploy`, `retain`, `abstain`, `rate`, and `wilson95`. Cell names encode effect rung and delay (for example P05N/P05A). Paired summaries are under `expected.ablation.cells`; contrast keys are `mu_h=0.05` and `mu_h=0.10`.

## Validation performed

Executed from an isolated copied package with Python 3.14.4 and interpreter isolation:

```text
python3 -I work/power_reproducer_20260922_0237/package/reproduce_power.py --output work/power_reproducer_20260922_0237/reproduction.json
```

The reader verifies hashes before reading outcomes; validates schedule, cell/law/delay, finalization look horizon, unique construction/program/trial identities, bounded coordinates and complete per-cell grids; and then pairs original/disabled ADAPTER decisions using exact cell/program/trial coordinates. All three construction grids are validated, while numerical deployment reporting is restricted to ADAPTER.

Reproduced all 26 per-cell ADAPTER deployment summaries (10 coarse, 12 fine, 4 disabled), Wilson marginal intervals, four joint/discordant decision tables, within-cell paired means and sample-variance MCSE, four independent-cell Newcombe contrasts, and both paired gap-change intervals. Every embedded accepted numeric expectation agrees at absolute/relative tolerance 1e-12. The 32,000 paired ADAPTER coordinates yield gap changes +0.00125, interval [-0.0002975250, 0.0027975250], and -0.13250, interval [-0.1401766466, -0.1248233534]. Intervals remain nominal pointwise Monte Carlo summaries of the selected synthetic design, not simultaneous or post-selection guarantees.

Three deterministic failure checks also passed: altered SHA-256 rejected before outcomes, missing shard rejected at file-count validation, and altered expected deployment count rejected after reconstruction. Receipts are `work/power_reproducer_20260922_0237/reproduction.json` and `negative_results.json`; the scratch package contains copies only. The first development attempt exposed my manifest's incorrect assumption that disabled gzip files contain ADAPTER alone; the manifest was corrected to the actual three-construction inventory before the successful final run. No experimental files changed.

Final SHA-256 values:

- Script: `0c13a24f47d2fc70665a02a8566eccc3da110495b8537921bea9b3e38684a9e3`.
- Manifest: `a3c1d0cb930c764d2c80ea555142dcfbe20447b95720b7bbab6aa802be669d27`.

Ownership released. No simulations, model calls, source-branch mutations, shared-status edits, or commits were performed.
