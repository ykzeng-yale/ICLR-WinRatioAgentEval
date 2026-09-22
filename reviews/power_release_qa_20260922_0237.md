# Accepted power/ablation release integration and QA

Full-project readiness **75% (+5)**; separately bounded-v1 **90%**. The documented integration milestone earns5points: accepted findings, figure, tables and limitations are now in the preprint and reproducibility release. The remaining final-expanded-release audit5 is held until the prospective evidence has been integrated. Remaining25: prospective10(Session60/root), final expanded QA5(root), author10(Yukang).

## What changed

AppendixP adds80,000coarse and48,000fine synthetic paths, separate stage/sample-size/provenance labels, Tables11–12 and Figure7, plus32,000matched certificate-ablation coordinates. Two disabled executions total64,000evaluations but add no independent coordinates. T1 cross-refers to the new appendix; baseline main text remains unchanged. Core result: disabling certificates widens the A-minus-N deployment gap at hierarchy mean0.10; the proposed mechanism is not supported by the two tested diagnostic rungs. All historical failure/retrospective-source limitations remain explicit. No live outcome, new theorem or author signoff is added.

## Completed verification

- Independent scientific source/claim audit: `power_integration_evidence_20260922_0237.md`. All22power Wilson intervals and paired/gap uncertainty checked against accepted records; manuscript claims reviewed and two wording refinements applied.
- Standalone new saved-record reproduction from the FINAL extracted ZIP:80unchanged pinned primary files,480,000construction records (240000coarse/144000fine/96000disabled),32000paired ADAPTER coordinates; counts, Wilson/Newcombe and paired Monte Carlo summaries PASS. No latent simulations/reference regeneration/model calls. Reproducer's bounded negative controls and scope documented in `power_reproducer_review_20260922_0237.md`.
- Existing packaged T1 check:336,000primary records,56shards,8cells PASS. Baseline reproduce.py:6analytic checks and127archived output hashes PASS.
- Clean extraction of arxiv_source.tar.gz compiled independently with latexmk. All49page texts exactly match the canonical paper. No undefined reference/citation or overfull-box messages in new build log.
- Current PDFs:49pages full,13main,36supplement. Compared previous canonical text: only pages46–49 changed (T1 cross-reference/reflow plus new appendix); pages1–45 unchanged. Root rendered and visually inspected46–49 at enlarged resolution: tables, Figure7, mathematical notation and provenance text readable with no clipping/overlap.
- Final391code-payload sizes/hashes and5top-level artifact hashes match manifests. All80new primary files equal exact accepted Git objects. Seven exact-commit provenance links resolve later addenda, erratum, surviving failed-attempt directories and reviews.
- Independent release audit `power_release_independent_20260922_0237.md`:38source entries, complete TeX inputs/figures, package/provenance verification PASS. Its initial critical-value concern was independently disproved and explicitly retracted; no unnecessary numerical change made.
- `git diff --name-only -- paper submission` empty: historical ICLR source/release untouched. Source-only additions and reproduction helpers are owned by root; owner experiment files are unchanged by this integration.

Artifacts: arxiv/paper.pdf, main_paper.pdf, supplement.pdf, arxiv_source.tar.gz, reproducibility_code.zip and package_manifest.json. The archive preserves the previously documented dependency-only runner repair. It remains an interim expanded preprint for the author to review and submit, not a publication or a completed prospective study.
