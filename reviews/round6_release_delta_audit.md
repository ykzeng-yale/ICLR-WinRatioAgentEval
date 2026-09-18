# Round 6: bounded final release delta audit

**PASS.** The new archive contains only the four expected paper payload changes relative to the fully reproduced Round 5 archive. The exact default verification-plus-build command passes; all numerical artifacts remain identical, and the rebuilt paper exactly preserves the submitted text.

## Frozen artifact and scope

- Archive SHA256: **`fc38286414a642d9145891c909c6f459a628e239902237ec3f2862e5a20e7a92`**.
- Inventory: **144 ZIP members; 142 manifest-listed payload files**.
- New extraction: `work/release_reproduction_check_v4/`.
- Preserved comparison baseline: the Round 5 archive in `work/release_reproduction_check_v3/original_archive.zip`, SHA256 `9ef791870c48f72b03a637f9f7d120cd1cad4beeea8a6a9b217f0305c041bb61`.

Root source files remained read-only. This report is the only deliverable-tree file written by the reviewer. No simulations, agent runs, commercial API calls, downloads, Git checkout, or merge were performed. Attribution and proof correctness are outside this bounded release audit and are reviewed separately.

## Exact payload delta

The archive comparison found one added and three changed payload files, exactly as expected:

| Path | Change |
|---|---|
| `paper/pairing_efficiency.tex` | Added |
| `paper/main.tex` | Changed |
| `paper/references.bib` | Changed |
| `paper/manuscript.pdf` | Changed |

`package_manifest.json` also changed to describe the new payload. No archive member was removed. **Every other payload byte is unchanged**, including all numerical engines, data derivatives, protocols, figures, prospective records and aggregate summaries, result builders, and reproducibility entry point. This justifies carrying forward the Round 5 complete numerical reproduction instead of repeating unchanged simulations.

## Verification and document reconstruction

The reviewer ran exactly `python3 reproduce.py --build-pdf` with the extraction as the working directory. It exited with **code 0**, passed the six analytic scientific checks, matched **73 archived-output hashes**, and rebuilt the manuscript without source modification or Git metadata.

- All **23 CSV files** are byte-identical to both the Round 5 baseline and the newly archived versions. The build leaves their bytes unchanged.
- All **44 LaTeX source-archive members** occur byte-for-byte in the code archive. Every explicit TeX input, include, and figure reference resolves within the supplied source archive.
- Every manifest-listed payload exists with the correct hash. No missing source or supplement dependency was observed.
- The current submitted PDF equals the PDF in the code archive. The rebuilt PDF's extracted text matches that submitted PDF exactly, and no archived TeX file changes during the build.
- The rebuilt PDF has **33 total pages**. Main scientific content ends on **page 9**, with statements beginning later on **page 9**. The main text and Limitations paragraph on page 9 were inspected directly; this boundary is not inferred from the last section heading.
- The TeX log contains **zero overfull boxes and zero undefined references or citations**.
- Anonymity scans pass across **125 text artifacts** and the rebuilt PDF text. PDF Author metadata is blank. Exact credential-value scans over every archive member pass; no credential value was printed.

The reviewer previously authored the public reanalysis and prospective adapter/results. This is an isolated release comparison with that overlap disclosed, not an independent commercial replication. The unchanged numerical package inherits the scope and limitations of the Round 5 full reproduction pass; the new theoretical and attribution text does not inherit a mathematical correctness judgment from this build audit.

**Disposition: PASS for the stated archive hash.** Machine-readable evidence and execution logs are preserved under `work/release_reproduction_check_v4/` as `archive_delta.json`, `static_delta_audit.json`, `reproduction_default_build.log`, and `rebuild_comparison.json`. The previous release snapshots remain intact. Subsequent payload edits require a new affected-file audit.
