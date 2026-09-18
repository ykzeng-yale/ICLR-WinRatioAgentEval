# Multi-agent coordination (read before editing)

Several agents (and the human author) work on this repository. Rules:

1. `git pull --rebase origin main` before every push. Commit small and often. Never force-push.
2. Prefer adding new files/modules over rewriting someone else's file. If you must edit a shared file, keep the edit minimal and describe it in the commit message.
3. Credentials live only in a local, gitignored `.env`. Never commit keys, never print them in logs.
4. Raw third-party data stays under `work/` (gitignored). Commit only derived tables, manifests (URLs + hashes) and scripts.
5. Every result table/figure in `results/` must be regenerable by a script in `experiments/` with a manifest (seed, config, code hash).

## Experiment queue (for agents without enough compute)

If you cannot run an experiment, add a row here with a self-contained spec (script path, command, expected outputs, approximate CPU-hours/RAM, API budget if any). Another agent claims it by writing its session name in `Claimed by`, commits, then runs it and commits the outputs and sets status `done`.

| ID | Status | Claimed by | Spec (script / command / outputs / resources) | Requested by | Notes |
|----|--------|-----------|-----------------------------------------------|--------------|-------|
| (none yet) | | | | | |

Compute available to session `iclr-winratioagentevals-60`: Apple Silicon 10 cores, 32 GB RAM, Python 3.12 venv at `.venv`, TinyTeX (pdflatex/bibtex). Cheap-model API access (Anthropic Haiku, OpenAI mini/nano tier) with a small budget.

## Session log

| Date (UTC) | Session | What |
|---|---|---|
| 2026-09-18 | prior session (`Adapt Codebase for Biostatistics Research Project`) | Protocol, literature audit, simulation baseline, ICLR checklist (commit a29e18f). Local `paper/theory.tex` and `work/empirical_sources/` were referenced but not pushed. |
| 2026-09-18 | `iclr-winratioagentevals-60` | Tooling (venv, TinyTeX), this coordination file, literature/standards/data research workflow, abstract draft, core inference library, experiments, paper draft, reviewer rounds. |
