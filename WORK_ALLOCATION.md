# Shared workspace ownership

Only the primary agent integrates source changes, stages files, commits, or pushes. No worker may reset, clean, rebase, change branches, or alter another worker's files. A completed file is handed back explicitly before integration.

| Worker | Current write ownership | Read-only scope |
|---|---|---|
| Primary | main manuscript, public-results manuscript sections, core library fixes, result-generation script, project status, integration and review-response ledger | All worker deliverables until handoff |
| Prospective experiment worker | `experiments/run_prospective_tau.py`, prospective protocol, prospective spend ledger/results, `paper/prospective_results.tex`, isolated runtime under external `work/` | Core library, existing historical results, other paper files, git state |
| Delayed-feedback experiment worker (former theory reviewer) | `experiments/run_async_experiment.py`, `results/async_*`, `evidence/async_experiment_protocol.md` | Existing theory, source, manuscript, and results |
| Asynchronous theory worker (former empirical reviewer) | `paper/asynchronous.tex`, `evidence/asynchronous_novelty.md` | Existing theory, source, manuscript, and results |

Earlier literature, theory-development, and historical-data tasks have been handed back. Required changes discovered by a reviewer are sent to the primary agent instead of edited concurrently. Before each commit the primary agent checks the staged-file inventory, worker handoff status, credential exclusion, and repository status. Scientific assumptions and rejected claims are recorded in the review response ledger, not silently removed.

## Latest handoffs

The prospective pilot, grader/decision ablations, and isolated DM comparison have been handed back. Root owns their integration. The release reviewer writes only reviews/round4_release_reproduction.md and a separate work/ extraction; the trace-certificate worker owns only experiments/run_trace_certificates.py, evidence/trace_certificate_protocol.md, and results/trace_certificate_* until handoff. The fresh integrated reviewer writes only its review report.

Contributed general wincs projections and width results are excluded from submission claims pending issue4. The isolated src/ternary_dm.py uses only audited complete-data formulas; it is not an asynchronous plug-in.

## Release handoffs

The trace worker handed back the frozen protocol, implementation and all four output tables. The independent reviewer reconstructed every certificate and owns only its report and a separately saved verifier until final handoff. Root owns both generated trace manuscript sections and integration. The empirical reviewer handed back the PR5 report; the patch remains unmerged after a concrete feasible-point counterexample. A release worker may extract and test the finished archive only under a separate work/ directory and write its release report; it must not edit research sources or outputs. All commercial calls are halted.
