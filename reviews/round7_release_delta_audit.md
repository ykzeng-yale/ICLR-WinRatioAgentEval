# Round 7: final release delta audit

**PASS for the final frozen archive.** The five expected payload changes are confirmed against the committed Round 6 package. Default verification and PDF reconstruction pass, the modified ablation builder reproduces the supplied TeX exactly, and every numerical result remains unchanged.

## Frozen artifact and comparison baseline

- Final archive SHA256: **`c2e8b7417fdb0c143046140268bd34036f6c461517b6cedab411253aa20f9235`**.
- Submitted PDF SHA256: **`d7585b5fa7f75b174e9860eae35b618e5680c53a2dff6b40c29d8ba963498599`**.
- Inventory: **144 ZIP members; 142 manifest-listed payload files**.
- Baseline: `submission/anonymous_code.zip` read directly from commit **`6dfc095`**; its SHA256 is `fc38286414a642d9145891c909c6f459a628e239902237ec3f2862e5a20e7a92`.
- Final isolated extraction and evidence: `work/v5/final/`. The provisional Round 7 snapshot is retained separately under `work/v5/` and is not the certified final hash.

The final snapshot includes the added word “bounded” in the U-statistic attribution sentence. Root source files stayed read-only; the reviewer performed no Git mutation, scientific-study rerun, agent inference, commercial request, or download. This report is the only file written by the reviewer into the deliverable tree. Citation substance and proof mathematics are outside this bounded package audit and have separate reviewers.

## Exact payload changes

Relative to the committed Round 6 archive, exactly these five payload paths changed:

1. `paper/main.tex`
2. `paper/references.bib`
3. `paper/manuscript.pdf`
4. `paper/decision_ablations.tex`
5. `experiments/build_ablation_paper_results.py`

The package manifest also changed to record the payload. No file was added or removed. All other payload bytes are identical, including the simulation engines, protocols, numerical results, figures, prospective records, and main reproduction entry point. In particular, all **73 files under `results/`**, including all **23 CSV tables**, match the committed Round 6 archive byte-for-byte. The prior complete numerical reproduction therefore continues to cover the unchanged scientific computations.

## Modified builder and comparator parity

The changed builder adds assertions against existing rows and prose reporting comparator parity. It does not change a scientific estimator, simulation, or observed result. Executing `python3 experiments/build_ablation_paper_results.py` in the final extraction exits with code 0 and produces TeX identical to the supplied files. All archived TeX and result bytes remain identical after execution.

The newly asserted equality was also checked directly against the archived CSV:

| Scenario | Positive decisions for both methods | Mean capped pairs for both methods |
|---|---:|---:|
| Efficiency gain | 386 | 4,078.4 |
| Joint gain | 500 | 1,485.0 |

The two methods are `guarded_win` and `guarded_efficiency`. Thus the added sentence correctly reports equality on both recorded quantities in those two cases. This supports the specific parity statement; it does not establish equality outside the reported scenarios.

## Verification, PDF, sources, and anonymity

The exact command `python3 reproduce.py --build-pdf` exits with **code 0**, passes the six analytic checks, verifies **73 output hashes**, and rebuilds the PDF. No full scientific studies were rerun.

- The rebuilt PDF text is exactly equal to the final submitted PDF text; the submitted PDF also matches the copy inside the code archive.
- The paper has **33 total pages**, with main scientific content ending on **page 9** and statements beginning later on **page 9**. The page-9 main text and Limitations paragraph were checked directly.
- The TeX log contains **zero overfull boxes and zero undefined references or citations**.
- All **44 LaTeX source-archive files** occur byte-for-byte in the code archive. All **23 explicit TeX input/include/figure references** resolve. Every manifest payload is present with its correct hash; no dependency or supplement omission was found.
- Anonymity scans pass across **125 text artifacts** and PDF text. PDF Author metadata is blank. Exact credential-value scans over every archive member pass; no secret value was printed.

The reviewer previously authored the public reanalysis and prospective adapter/results; this is disclosed overlap. This isolated release comparison does not constitute a new commercial replication, proof certification, citation-substance review, or acceptance prediction.

**Disposition: PASS for archive `c2e8b7417fdb0c143046140268bd34036f6c461517b6cedab411253aa20f9235`.** Evidence is retained under `work/v5/final/` in `archive_delta.json`, `static_audit.json`, `execution_audit.json`, `default_verify_build.log`, and `modified_builder.log`. Earlier release snapshots and audit evidence remain intact.
