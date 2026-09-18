# Reproducing the reported research

The paper combines synthetic score streams, historical public agent traces, and a small prospectively specified laboratory pilot. None is a production-user randomized trial. Independent model-assisted reviews and limitations are recorded in the development repository.

## Environment

Install Python 3.11 or later with `python -m pip install -r requirements.txt` in a fresh virtual environment. The numerical outputs were generated on Python 3.14.4 with the four exact dependency versions in requirements.txt. PDF building requires a current TeX installation, pdflatex, bibtex, and latexmk; the official ICLR style dependencies are supplied in paper/. No GPU is needed for simulation or historical reanalysis. The prospective tau2 runner uses a separate pinned Python 3.13.11 environment; its runtime manifest accompanies its records.

## One-command entry points

From this directory, `python reproduce.py` runs the core scientific checks and verifies available archived-output hashes. `python reproduce.py --mode simulate --build-pdf` reruns all synthetic studies and regenerates their paper outputs and the manuscript. `python reproduce.py --mode full --fetch-public --build-pdf` additionally downloads pinned public source files into work/empirical_sources and repeats historical analyses. An existing source folder can be supplied with `--public-raw-dir /path/to/sources`. These commands never call commercial models. Use a fresh unpacked copy for exact reproduction so regenerated manifests do not replace your only record of the delivered baseline.

## Expected resource use

The principal simulations and delayed-feedback experiment run on CPU in minutes. Historical analysis includes 10,000 task-bootstrap resamples for 68 comparison/configuration rows. Downloaded historical sources require approximately 0.4 GB; retain at least 2 GB free for the environment and intermediates. No model weights are required. Run time varies with CPU and numerical-library versions. The prospective environment has additional dependencies and is not installed by the numerical requirements file.

## Provenance and regeneration

`results/*manifest.json` records seeds, parameter settings, code hashes, output hashes, and/or original artifact URLs. A manifest generated on a later replay legitimately has a different timestamp. Numerical result tables, rather than PDF byte identity or elapsed time, are the deterministic comparison target. Public source downloads fail on hash mismatch. No source file is silently substituted. The historical bootstrap is conditional on the archived seed suite and is not a simultaneous ranking guarantee.

`experiments/build_paper_results.py` regenerates the synthetic tables/figure; `experiments/build_async_paper_results.py` regenerates the delayed-feedback text/table from recorded results. Historical manuscript summaries are checked against results/public_comparisons.csv. Full proofs are in paper/theory.tex and paper/asynchronous.tex.

## Prospective model records

The prospective runner is deliberately separate from reproduce.py. It requires explicitly supplied credential and private-output paths and may incur cost. Its frozen protocol, model, task order, token/step caps, amendments, sanitized trace summaries, and ledger are retained. The original OpenAI attempt returned exhausted quota before any completed run; a Haiku workflow amendment preserves that record. The combined pilot cap is USD4, within an overall project allocation of USD5. Repeating an API experiment can produce different model outputs and incurs a new bill; it is not required to inspect or reproduce the published aggregate calculations. No credentials or raw private transcripts are included.

## Reuse and scope

Retain third_party notices when using upstream task material. Anonymous submission materials exclude project-owner identifiers and identifying repository links. An executable package and passing internal checks do not establish acceptance, human proof certification, production safety, or transport to a new workload.
