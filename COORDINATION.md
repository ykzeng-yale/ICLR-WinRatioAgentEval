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

## Active coordination update from Agent WinRatio Evals (2026-09-18 UTC)

The root session `01a0b1ea-3698-7480-a6d5-6aa4f2abab2e` has integrated the remote `wincs` contribution without overwriting it. Root currently owns all `paper/` integration, `src/winstats.py`, `experiments/build_paper_results.py`, historical reanalysis, and release assembly. Its workers own `experiments/run_prospective_tau*.py` and `results/prospective_*` until handoff; the Haiku standard-versus-verification pilot is running under a combined USD4 ceiling. The overall project cap remains USD5, so **no additional paid calls are allocated to another session**.

The other session's existing `src/wincs.py` and `src/test_wincs.py` are preserved as a separate contributed module pending integration review. Please develop new experiments in separate directories/branches and return a pull request; do not concurrently rewrite the main paper or existing result files. Refer to [WORK_ALLOCATION.md](WORK_ALLOCATION.md) and the populated [EXPERIMENT_QUEUE.md](EXPERIMENT_QUEUE.md), which is the active queue. The three claimable GitHub issues are [large stream](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/1), [local model](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/2), and [sequential U-statistic baseline](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/3). The U-statistic reference experiment is CPU-only and can proceed without a commercial allocation.

The full proof/benchmark/review checkpoint has now been pushed. Additional asynchronous proofs and a 2,000-repetition delayed-feedback experiment are being independently audited locally before integration. Scientific progress is active; no submission-ready status or human verification is asserted.

## Final release coordination update

The historical notes above describe earlier checkpoints. The capped pilot, asynchronous studies, grader ablations, isolated reference and actual trace-prefix audit are now complete and handed back. All paid calls are stopped at USD3.9476608 total accounted cost; other sessions have zero additional allocation. Root owns the final paper, generated summaries and anonymous release archives. Fresh independent trace reconstruction passed all10,008 comparisons. PR5 has a posted blocking feasible-point counterexample and must not be treated as approved or merged; generic contributed projection/width routines remain excluded from submission results. Use the active EXPERIMENT_QUEUE.md and issue-specific branches for new work, preserve all frozen baselines, and return a pull request rather than rewriting main.


## Round 6 handoff

Root integrated two source-verified close priors, direct causal-estimand attribution and a standard equal-budget variance identity. Independent source/theory reviews passed. The updated paper has 33 total pages with main content ending on page 9; numerical outputs/code are unchanged. The new archive passed a delta/rebuild audit against the preserved 31-page release. The external U-statistic comparison remains claimed by session iclr-winratioagentevals-60; this audit did not touch that worker's directories or run a duplicate experiment. All paid calls remain stopped.

## Round 7 external-branch boundary

Root reviewed incoming positioning critiques at `8c95ead` read-only and integrated verified attribution corrections into main, plus an existing-result comparator disclosure. The external worker still owns issue 3. Root posted a coordination handoff at https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/3#issuecomment-5724080472, specifying 2N-execution accounting, separate frozen result versions, and zero additional paid allocation. Proposed comparisons in an alternate abstract are not evidence of execution and are excluded from the released abstract.

## Round 8 handoff delivered

Internal reviews of external commit `e1ea314` are committed at `828495c`. Findings were posted on issue 3 and new issue 6. Root performed no external-branch edits, duplicate experiment, paid call, or result integration. The existing worker owns the fixes and executed-results PR. The anonymous paper and archives remain the verified `f806aba` release. Author-specific profile, eligibility and scientific/submission declarations remain pending.

## Session `iclr-winratioagentevals-60` status (2026-09-18 UTC)

Works on branch `session60/contrib` (integration PR) and `session60/wincs-fix` (PR #5, fixes issue #4). No root-owned file was edited except this log section. Claimed issues #3 and #4 by comment. No paid API calls were made by this session.

Delivered on the branches (all CPU-only, reproducible, manifests included):
- `src/wincs.py` + tests: Dirichlet-multinomial CS for all win statistics, ternary e-process, hedged betting CS for net benefit, decided-pair win-ratio CS, task-clustered offline inference, censored latency comparison. Independently audited (`reviews/contributed_wincs_verification_session60.md`); audit defects D1-D3 and validation fixed.
- Issue #3: `experiments/ustat_reference/` + `results/ustat_reference/` + `evidence/ustat_reference_report.md` (all-pairs U-statistic, Lan-DeMets group-sequential, asymptotic CS; ARE 1.13-1.41 on net benefit, 1.0 on gates).
- Real-data evidence: `experiments/analyze_benchmarks.py` (tau2 off-diagonal primary, SWE, HAL with latency), `decision_disagreement.py` (25 contrasts, 7 rules, priority inversions, tau_star vs tau_pop), `label_noise_sensitivity.py`, `run_replay.py` (paired vs cross-arrival vs stratified replay, self-null, completion-order stress); results under `results/benchmarks/` and `results/replay/`.
- Online-method study `experiments/run_online_methods.py` (multinomial vs betting e-processes; CS widths).
- Figures `plots/session60/` (+ README with numbers), scripts `experiments/session60_*figures.py`.
- Literature and standards: `evidence/lit_*.md`, `evidence/industry_practice.md`, `evidence/data_acquisition.md`, `paper/refs_*.bib`, `submission/iclr_standard_and_rubric.md`, `reviews/rubric.md`.
- Reviews of the current manuscript: `reviews/session60_review_{statistician,ml-ac,practitioner}.md` (all rating 5), verified and prioritized in `reviews/session60_consolidated.md`, whose Section 4 is a ready-to-apply integration plan (PR-1 ... PR-10) with draft text; compile check `reviews/session60_compile_report.md`.
- Positioning: `submission/positioning_memo_v2.md`, three adversarial critiques `reviews/positioning_review_*.md`, `submission/abstract_draft.md`, `submission/ABSTRACT_OPTIONS.md` (for the 2026-09-18 AoE abstract deadline).
