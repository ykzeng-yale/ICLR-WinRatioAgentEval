# Shared workspace ownership

Only the primary agent integrates source changes, stages files, commits, or pushes. No worker may reset, clean, rebase, change branches, or alter another worker's files. A completed file is handed back explicitly before integration.

| Worker | Current write ownership | Read-only scope |
|---|---|---|
| Primary | main manuscript, public-results manuscript sections, core library fixes, result-generation script, project status, integration and review-response ledger | All worker deliverables until handoff |
| Prospective experiment worker | `experiments/run_prospective_tau.py`, prospective protocol, prospective spend ledger/results, `paper/prospective_results.tex`, isolated runtime under external `work/` | Core library, existing historical results, other paper files, git state |
| Delayed-feedback experiment worker (former theory reviewer) | `experiments/run_async_experiment.py`, `results/async_*`, `evidence/async_experiment_protocol.md` | Existing theory, source, manuscript, and results |
| Asynchronous theory worker (former empirical reviewer) | `paper/asynchronous.tex`, `evidence/asynchronous_novelty.md` | Existing theory, source, manuscript, and results |

Earlier literature, theory-development, and historical-data tasks have been handed back. Required changes discovered by a reviewer are sent to the primary agent instead of edited concurrently. Before each commit the primary agent checks the staged-file inventory, worker handoff status, credential exclusion, and repository status. Scientific assumptions and rejected claims are recorded in the review response ledger, not silently removed.
