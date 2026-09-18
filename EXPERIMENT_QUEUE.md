# Experiments available for independent workers

This is a work queue, not a list of completed results. Claim a GitHub issue before starting. Use a separate branch or worktree. Never edit the primary agent's active files or push directly to `main`. Return a pull request with exact inputs, commands, code revision, provenance, estimates, uncertainty, limitations, and cost/disk usage. Do not include credentials, model caches, private transcripts, or large raw artifacts in git.

The initial commercial-model budget is USD 5 across this project. The active small pilot has a separately reserved USD 4 maximum. Other queued jobs currently have **zero additional commercial allocation**; an independent worker must obtain an explicit allocation from the project owner before paid calls. A local model does not consume commercial API budget but still requires an up-front free-space check. Never delete unrelated user files to make room.

| Job | State | Resources and boundary | Exclusive outputs |
|---|---|---|---|
| Twelve-task Haiku standard/verification telecom pilot | Active locally, assigned | USD 4 cap including simulator and uncertain reservations; no production users | `experiments/run_prospective_tau*.py`, `results/prospective_*`, prospective protocols and manuscript summaries |
| Informative-delay partial-evidence experiment | Completed and independently reproduced | CPU simulation, no commercial calls | `experiments/run_async_experiment.py`, `results/async_*` |
| Larger prospective randomized stream experiment | Queued; resource/cost estimate first | Requires fresh seed/task sampling, predeclared design and a separately allocated budget; shared disk was temporarily exhausted during initial setup | New `experiments/large_stream/`, `results/large_stream/`; do not overwrite pilot |
| Independent small local-model workflow replication | Queued; external disk/compute worker preferred | Check model/license/hardware and space; no API calls; save weights outside repo | New `experiments/local_replication/`, `results/local_replication/` |
| Competitive sequential U-statistic reference baseline | Queued; ready for a statistical-methods worker | CPU only; faithfully reproduce a cited method under its assumptions; distinguish aligned from different estimands | New `experiments/ustat_reference/`, `results/ustat_reference/` |

None of the queued experiments is needed to repair a fabricated result: the existing synthetic and historical outputs are real executed analyses. The queued studies address current scientific limitations, especially prospective precision and comparison with efficient prior methods. The readiness decision must continue to list them as unresolved where their absence limits a claim.

Live issues: [large stream](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/1), [local model](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/2), [U-statistic reference](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/3), and [contributed projection correction](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/4).
