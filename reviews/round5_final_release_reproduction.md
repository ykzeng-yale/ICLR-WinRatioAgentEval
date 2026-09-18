# Round 5: final trace-extended release reproduction

**PASS for the frozen archive identified below.** The exact default verification command and the exact full numerical reproduction command both exit successfully in a fresh extraction, without source edits, a Git checkout, new downloads, or commercial API calls. All regenerated numerical tables and manuscript text match the archived versions.

## Artifact and audit scope

- Archive: `submission/anonymous_code.zip`.
- SHA256: **`9ef791870c48f72b03a637f9f7d120cd1cad4beeea8a6a9b217f0305c041bb61`**.
- Inventory: **143 ZIP members; 141 manifest-listed payload files**.
- Isolated extraction and evidence: `work/release_reproduction_check_v3/`. The exact original archive, LaTeX source archive, and submitted PDF were copied into this directory before execution.
- Environment: Python 3.14.4 with the supplied numerical dependencies and the installed TeX toolchain. Existing pinned public source files were supplied through `--public-raw-dir`.
- Root source files stayed read-only. This report is the only file written by the reviewer in the deliverable tree. Earlier failed and corrected release-candidate evidence remains intact.

The reviewer previously authored the public reanalysis and prospective adapter/results. This is disclosed authorship overlap: the audit is an isolated package execution and comparison, not an independent commercial-agent replication or independent certification of every scientific argument. The new trace verifier was written by another reviewer and is executed here through the released entry point.

## Exact entry-point outcomes

`python3 reproduce.py` passed the six analytic scientific checks and matched **73 archived-output hashes**.

`python3 reproduce.py --mode full --public-raw-dir <existing-pinned-public-source-directory> --build-pdf` exited with **code 0**. It executed the principal simulations, stress tests, delayed-feedback experiment, multinomial baseline, decision/grading ablations, historical reanalysis, trace-certificate replay, independent trace reconstruction, result builders, prospective aggregate postprocessing, and PDF build. No analysis component was invoked separately to bypass a failed entry point.

The command never invoked either prospective commercial runner. Its three prospective CSVs remain archived observations; their aggregate postprocessing is reproduced without inference calls.

## Numerical comparisons

All **23 CSV files are byte-identical** to the archive after the run: **20 regenerated numerical tables and three retained prospective observation tables**. Pandas exact-value comparisons also pass. The regenerated `prospective_final_cohort_summary.json` is exactly equal to its archived object.

| Study | CSV files | Principal row counts |
|---|---:|---|
| Principal simulations | 1 | 36 |
| Stress tests | 1 | 17 |
| Delayed feedback | 3 | 6 results; 2 paired comparisons; 480 calendar paths |
| Multinomial baseline | 2 | 64 results; 8 paired comparisons |
| Decision/grading ablations | 4 | 48 results; 24,000 trials; 6 populations; 4 grader truths |
| Historical public analysis | 5 | 68 comparisons; 11 summaries; 3,936 trajectories; 1,134 task scores; 12 repository omissions |
| Trace-certificate replay | 4 | 9 cost audits; 27 examples; 10,008 pairs; 9 summaries |
| Prospective observations retained | 3 | 24 original planned records; 24 amended planned records; 9 complete pairs |

The independent trace verifier reported **PASS**, reconstructing 3,336 episodes and 51,247 assistant messages from nine hash-verified source files. It checked all **10,008 comparisons and 195,171 prefixes**, reproducing **3,426 early certificates**, including **2,595 with an actual message remaining**, and every recorded first-certificate time. It also passed 57,919 exact rational threshold-product checks. The maximum decimal cumulative-cost discrepancy was `3.565E-16`. These results describe the specified fixed-archive ordinal replay; the audit does not interpret ordinal lead as wall-clock latency or savings in a live deployment.

## Source, supplement, document, and anonymity checks

- Every manifest-listed payload file is present with the correct hash. No nested integrity-manifest reference points to an omitted file.
- All **43 files** in `latex_source.zip` are included byte-for-byte in the code archive. Every explicit TeX input, include, and figure reference resolves inside that source archive. There are no observed source or supplement omissions.
- The submitted `paper.pdf` is byte-identical to the PDF packaged in the code archive.
- Every archived `.tex` file remains byte-identical after regeneration. The rebuilt PDF's extracted text exactly matches the submitted PDF.
- The rebuilt paper has **31 total pages**, with main scientific content ending on **page 9** and statements beginning later on **page 9**. The Limitations paragraph occupies the top of page 9 before the statements. The TeX log contains **zero overfull boxes and zero undefined references or citations**. This corrects the initial report's page-8 boundary; it does not change the exact source, numerical, or PDF-text reproduction results.
- Author metadata in the rebuilt PDF is blank. Identifier scans across **124 text artifacts** and PDF text passed. Exact credential-value scans over every archive member passed; credentials were never printed. No identifying repository link or personal local path was found.
- The archive's core modules are `winstats.py`, `ternary_dm.py`, and the scientific invariant checks. The separately reviewed contributed `wincs.py` projection module is not included in this submission archive.

## Allowed metadata differences and limits

The observed differences are elapsed times, public/trace-manifest generation timestamps, metadata-dependent figure PDF hashes, the optional Git revision being `null` in a standalone archive, and the optional DM development-reference check being unavailable. The latter does not prevent reproduction: the reviewer independently compared all 64 DM result rows and its paired CSV with the archived baseline, exactly. The regenerated public manifest's timestamp changes its hash, and the trace manifest correctly records that new public-manifest hash. No CSV or TeX discrepancy was observed.

The audit uses existing raw files and therefore does not establish current remote download availability. The prospective aggregate audit does not rerun stochastic commercial models or verify provider invoices. Passing reproduction and formatting checks does not establish production effectiveness, novelty, theorem correctness beyond the stated checks, or conference acceptance.

**Release disposition: PASS for archive SHA256 `9ef791870c48f72b03a637f9f7d120cd1cad4beeea8a6a9b217f0305c041bb61`.** Logs and machine-readable evidence are preserved as `reproduction_default.log`, `reproduction_full.log`, `static_release_checks.json`, and `final_reproduction_comparison.json` under `work/release_reproduction_check_v3/`. Subsequent payload changes require a new integrity check and any affected reproduction checks.
