# Round 4: isolated release and reproduction audit

**Assessment: the numerical and document results reproduce, but this original release candidate has two entry-point defects requiring repair and a fresh archive check.** This audit does not independently certify novelty, all proofs, production validity, or conference acceptance.

## Scope and independence

The reviewer extracted `submission/anonymous_code.zip` into the new workspace directory `work/release_reproduction_check/`, without a Git checkout, and used Python 3.14.4 and the installed numerical dependencies. All analysis and build outputs were written inside that isolated extraction. Development source files remained read-only; this report is the only file written into the deliverable tree. No prospective execution, credential-bearing request, paid API call, or model inference was performed.

This reviewer previously authored the public reanalysis and prospective pilot adapter/results, which limits reviewer independence for those methods. The present checks are independent **release execution and comparison** against immutable archive contents; they are not an independent replication of the commercial experiment. The reviewer did not author the principal simulation, delayed-feedback, decision-ablation, or Dirichlet–multinomial baseline analyses.

## Observed release defects

1. **Missing files prevent the default integrity check.** In the untouched extraction, `python3 reproduce.py --mode verify` passed the scientific invariant tests, then failed on the absent `experiments/prospective_final_results.tex`. Exhaustive manifest inspection identified exactly three omitted files referenced by `results/prospective_final_qa_manifest.json`: `experiments/prospective_final_results.tex`, `experiments/prospective_results.tex`, and `experiments/prospective_v2_results.tex`. Include all three in the anonymous code archive so the integrity manifest is self-contained. Do not remove these validation requirements merely to suppress the error.

2. **Unconditional Git metadata prevents the advertised full command.** The requested `python3 reproduce.py --mode full --public-raw-dir <existing-public-source-directory> --build-pdf` exited in `experiments/reproduce_dm_baseline.py`, original line 160, because `git rev-parse HEAD` failed in the ordinary unpacked archive. The baseline's numerical CSVs had been written before this provenance failure. Repository metadata must be optional when `.git` is unavailable. A standalone archive must not require initializing a synthetic Git repository.

The integration owner reported fixes to both issues while this audit was running. Those changes are **not yet certified by this original-candidate audit**: the owner had not overwritten the archive during comparisons. A repaired archive needs an untouched-extraction integrity check and a successful full entry-point run. Later trace-certificate additions also require checking their own outputs and package integration.

## Reproduction results

After the original full command stopped at its Git metadata call, the reviewer continued the remaining original scripts individually, without modifying source: decision ablations, historical reanalysis, all four paper-result builders, prospective aggregate postprocessing, and the manuscript build. The preceding principal simulations, stress tests, delayed-feedback study, and multinomial baseline had already generated their numerical tables.

All **16 regenerated numerical CSVs match the archived originals byte-for-byte**. The three prospective CSVs remain identical archived observations; they were deliberately not regenerated through paid inference. The prospective aggregate JSON was recomputed from those observations and is exactly equal to its archived version.

| Component | Compared CSVs and row counts | Result |
|---|---|---|
| Principal simulations | `simulation_results.csv`: 36 | Exact byte match |
| Stress tests | `stress_results.csv`: 17 | Exact byte match |
| Delayed feedback | `async_results.csv`: 6; `async_paired_gains.csv`: 2; `async_calendar_paths.csv`: 480 | Exact byte matches |
| Multinomial baseline | `dm_baseline_results.csv`: 64; `dm_baseline_paired.csv`: 8 | Exact byte matches; original provenance step failed as described above |
| Decision and grading ablations | Results: 48; trial rows: 24,000; populations: 6; grader truths: 4 | Exact byte matches |
| Historical public analysis | Comparisons: 68; model summaries: 11; trajectories: 3,936; task scores: 1,134; leave-repository-out rows: 12 | Exact byte matches |
| Prospective observations | Original planned-run records: 24; amended planned-run records: 24; complete pairs: 9 | Archived observations retained exactly |
| Prospective aggregate postprocessing | `prospective_final_cohort_summary.json` | Exact object match after regeneration |

The public reanalysis read the original local sources and covered 3,336 tau2 and 600 SWE trajectories. Download behavior was not exercised because the requested existing source directory was supplied. Therefore this audit establishes local-data reanalysis, not current network availability of every remote artifact.

The reproduced prospective aggregate preserves the incomplete cohort: 18/24 completed trajectories, 9/12 complete pairs, and 12 completed trajectories reaching the step cap. It retains the all-12-task net-preference bounds of [−0.4167, 0.0833] and success-difference bounds of [−0.25, 0.25]. These are deterministic missing-outcome bounds, not confidence intervals. Accounted pilot cost is $3.9456258; separate provider diagnostics are $0.002035; project accounting totals $3.9476608. These amounts are list-price usage accounting plus retained reservations, not independently verified invoices.

## Source, PDF, and anonymity checks

- The original code archive contains 129 members. All 127 file entries in its package manifest are present and have correct hashes. The three missing references occur in the nested prospective QA manifest, explaining why the outer inventory alone did not catch the defect.
- All 41 files in `latex_source.zip` also occur in the code archive and match exactly. All 20 explicit TeX input/include/figure references resolve inside the supplied source archive.
- `submission/paper.pdf` is byte-identical to the PDF included in the code archive.
- Every paper `.tex` file remains byte-identical after the result builders run. The independently rebuilt PDF has **29 pages**, and its extracted text exactly matches the submitted PDF. Its byte count differs slightly, which is allowed for regenerated PDF metadata and is not a numerical or text discrepancy.
- Main scientific content ends on **page 8**; reproducibility, ethics and AI-use statements begin on **page 9**. The regenerated TeX log has **zero overfull boxes and zero undefined references or citations**. This verifies the supplied pagination boundary, not a new independent interpretation of every conference rule.
- No project-owner identifiers, personal local filesystem paths, identifying repository name, or secret-shaped credential strings were found across 110 archive text files. An exact credential-value scan over every archive member also passed; secret values were never printed. Submitted PDF text passed the identifier scan and its Author metadata is blank.
- The numerical entry point is separate from prospective commercial execution. The reviewer never invoked either prospective runner. Private credentials and raw private conversation transcripts are absent from the anonymous archive.

## Reproducibility limits and release disposition

Numerical CSV values required no tolerance: they matched exactly in this environment. Regenerated timestamps, elapsed times, optional Git metadata, source hashes after a source correction, and PDF bytes are not the deterministic scientific comparison target. A `reproduction_reference_present` change can legitimately occur when a baseline has an existing reference table; it must not substitute for an actual numerical comparison.

The package requires the four pinned numerical Python dependencies, a TeX installation including `latexmk`, and either the original downloaded public data or successful network retrieval. It does not require a Git checkout or commercial credentials for the advertised numerical reproduction; the original Git dependency is the verified defect requiring correction.

**Release disposition for the examined archive:** scientific numerical comparisons and document reconstruction pass; the default integrity command and full one-command interface fail for the two concrete packaging/provenance reasons above. Retest the corrected archive before describing the release entry point as passing. The evidence for this audit, including execution logs, the original archive inventory and checksum, the complete table-by-table comparison, and the extracted-PDF comparison, remains under `work/release_reproduction_check/`.

## Corrected archive retest: both entry points pass

The integration owner rebuilt the archive after correcting the three omitted TeX files and making Git provenance optional. The reviewer extracted this new archive into **`work/release_reproduction_check_v2/`**, preserving an exact copy as `original_archive.zip` and retaining all first-candidate failure evidence. The corrected archive SHA256 is **`9525c779b495f8deb23729a166aa6469af7ebbcb4f0285e9e85fdd02b5cdccdd`**. It contains 132 ZIP members. This checksum defines the scope of this retest; later additions are not covered automatically.

The explicit verification command exited successfully with all six analytic truth checks and **69 archived-output hashes matched**. The exact default `python3 reproduce.py` command was also run in an untouched second extraction of that same snapshot and passed. The exact requested full command, `python3 reproduce.py --mode full --public-raw-dir <existing-public-source-directory> --build-pdf`, then completed with **exit code 0**, without any source modification, Git initialization, commercial request, or separately invoked analysis component. The absent Git revision is correctly recorded as JSON `null`.

After that complete entry-point run, all **19 CSVs** still match the corrected archive byte-for-byte: 16 regenerated numerical tables and three retained prospective observation tables. The prospective aggregate JSON matches exactly. No paper TeX file changed after the builders; the rebuilt PDF has 29 pages and extracted text identical to the corrected archived PDF, with main scientific content ending on page 8 and statements beginning on page 9. The TeX log again has zero overfull boxes and zero undefined references or citations. Exact credential-value and author-identifier scans of the corrected archive passed.

All observed nonnumerical differences are accounted for: elapsed times and the public-manifest generation timestamp; metadata-dependent PDF hashes for the asynchronous and decision-ablation figures; a missing optional Git revision; and the optional internal DM-reference comparison record. In the standalone archive, that latter comparison reports `Nonreference configuration or reference absent`, because its separate development reference is not supplied. This does **not** affect the executed baseline results: this reviewer independently compared all 64 reproduced baseline rows and the paired table with the archived tables and found exact byte equality. The originally described numerical reproduction is therefore supported without the optional development reference.

**Updated disposition: the two verified release defects are resolved for the corrected archive identified above. Default verification, the complete numerical reproduction entry point, public-data reanalysis, prospective aggregate postprocessing, and PDF reconstruction all pass.** Evidence is recorded in `work/release_reproduction_check_v2/reproduction_default.log`, `reproduction_verify.log`, `reproduction_full.log`, and `reproduction_final_comparison.json`. The earlier failure findings remain in this report as the release audit trail. This retest does not cover the proposed later trace-certificate replay or any subsequent scientific changes.
