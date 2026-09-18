# Reproducing the reported research

The paper combines synthetic score streams, historical public agent traces, an ordinal prefix-certificate replay, and a small prospectively specified laboratory pilot. None is a production-user randomized trial. Independent model-assisted reviews and limitations are recorded in the development repository.

## Environment

Install Python 3.11 or later with `python -m pip install -r requirements.txt` in a fresh virtual environment. The numerical outputs were generated on Python 3.14.4 with the four exact dependency versions in requirements.txt. PDF building requires a current TeX installation, pdflatex, bibtex, and latexmk; the official ICLR style dependencies are supplied in paper/. No GPU is needed for simulation or historical reanalysis. The prospective tau2 runner uses a separate pinned Python 3.13.11 environment; its runtime manifest accompanies its records.

## One-command entry points

From this directory, `python reproduce.py` runs the core scientific checks and verifies available archived-output hashes. `python reproduce.py --mode simulate --build-pdf` reruns the original synthetic studies and regenerates their paper outputs and the manuscript. `python reproduce.py --mode full --fetch-public --build-pdf` additionally downloads pinned public source files into work/empirical_sources and repeats historical analyses. An existing source folder can be supplied with `--public-raw-dir /path/to/sources`. These commands never call commercial models. Use a fresh unpacked copy for exact reproduction so regenerated manifests do not replace your only record of the delivered baseline.

Add `--extensions` to explicitly rerun the accepted sequential all-pairs comparison, its four 10,000-repetition boundary calibrations and rare-compliance diagnostic, and the twelve-scenario drift panel. These CPU-only runs require no model weights, benchmark inference, or API credentials. They use their documented separate seed suite, not the primary simulation table's seeds. Four workers are used by this entry point; recorded numerical CSVs are invariant to worker count. The comparator can take several minutes; the drift panel takes about a minute on the recorded machines. To rebuild only the new paper text from retained results, run `python experiments/build_sequential_extensions.py`.

## Expected resource use

The principal simulations and delayed-feedback experiment run on CPU in minutes. Historical analysis includes 10,000 task-bootstrap resamples for 68 comparison/configuration rows. Downloaded historical sources require approximately 0.4 GB; retain at least 2 GB free for the environment and intermediates. No model weights are required. Run time varies with CPU and numerical-library versions. The prospective environment has additional dependencies and is not installed by the numerical requirements file.

## Provenance and regeneration

`results/*manifest.json` records seeds, parameter settings, code hashes, output hashes, and/or original artifact URLs. A manifest generated on a later replay legitimately has a different timestamp. Numerical result tables, rather than PDF byte identity or elapsed time, are the deterministic comparison target. Public source downloads fail on hash mismatch. No source file is silently substituted. The historical bootstrap is conditional on the archived seed suite and is not a simultaneous ranking guarantee.

`experiments/build_paper_results.py` regenerates the synthetic tables/figure; `experiments/build_async_paper_results.py` regenerates the delayed-feedback text/table from recorded results. Historical manuscript summaries are checked against results/public_comparisons.csv. Full proofs are in paper/theory.tex and paper/asynchronous.tex.

Full mode also executes `experiments/run_trace_certificates.py --raw-dir /path/to/sources` and its separately implemented verifier. The trace replay audits all nine retained tau2 source files, 3,336 episodes, and 195,171 prefixes; it never calls a model. Its four CSVs and every earliest-certificate tick are deterministic. `experiments/build_trace_paper_results.py` derives the two manuscript sections, including the independently requested terminal-marker sensitivity, from the archived full comparison table. Simulation mode keeps the observed public trace results and only rebuilds their manuscript text. No replay count is interpreted as concurrent latency or an independent binomial sample.

## Prospective model records

The historical commercial-model runner is retained only for provenance and is not authorized for further execution. Its frozen protocol, model, task order, token/step caps, amendments, sanitized trace summaries, and ledger are retained. The original OpenAI attempt returned exhausted quota before any completed run; a Haiku workflow amendment preserves that record. The combined pilot cap was USD4 within the historical USD5 allocation. The author's subsequent instruction prohibits all further commercial/proprietary experimental calls, including simulators, judges and fallbacks. Reproducing published aggregate calculations uses the archived observations and never requires model calls. No credentials or raw private transcripts are included.

## Accepted extensions and immutable provenance

The original contributed comparator and drift manifests are retained unchanged in the development tree. Their recorded core hash refers to the original `winstats.py`; the integrated core changes only its docstring to describe the independently reviewed running-mean guarantee. Executable-AST equality was verified. `results/sequential_extensions_integrity.json` records the original and integrated hashes and the retained result hashes. Anonymous release copies replace identifying output-directory strings only and record that transformation; numerical CSV bytes remain unchanged. The new proof does not retroactively change the declared analysis plan or claim that its guarantee was established before the drift simulations.

## Reuse and scope

Retain third_party notices when using upstream task material. Anonymous submission materials exclude project-owner identifiers and identifying repository links. An executable package and passing internal checks do not establish acceptance, human proof certification, production safety, or transport to a new workload.
