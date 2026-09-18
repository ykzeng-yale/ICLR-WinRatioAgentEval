# Round 10 release delta audit

**Verdict: PASS for the corrected frozen PR7/PR10 intermediate review package.** One identifying output path was found in the first archive, reported immediately, corrected by the package owner, and independently rechecked. No remaining release blocker was found within the checks below. This is not a declaration of submission readiness, acceptance, or completion of pending PR8 work.

Audited 2026-09-18. Scope: the release archives, result/source integrity, anonymous provenance, safe reproduction entry point, table generation, and clean PDF builds. The reviewer previously contributed theory and earlier statistical reviews; this is an independent extraction/reproduction audit, not independent authorship of the method. No source, result, manuscript, or Git state was modified by this audit. Only this report and isolated outer-workspace scratch artifacts were written. No heavy simulations or model/API calls were run.

## Exact frozen release

| Artifact | SHA-256 |
|---|---|
| `submission/anonymous_code.zip` | `ae5edbd74eb81d2363685b633a3dc18d3ad023d0d8fa00c6ab499485a59edcf0` |
| `submission/latex_source.zip` | `fc7e4804426add437aba3f7201bce5d1916c16b09f15ce6e9cf4e361904d67fa` |
| `submission/paper.pdf` | `24db7d5d24d59d92b81359b72877b2583dc9064b0d01b574d882a6c3a42db95c` |

The code archive contains 190 entries: 188 payload files plus the release README and embedded package manifest. Every payload byte count and SHA-256 matches the manifest, and the embedded manifest equals the outer manifest. The source archive has 50 entries, each byte-identical to its corresponding code-archive payload. Neither archive has duplicate or traversal/absolute entry names.

## Identifying-path defect and closure

The initial code archive (SHA-256 `f6011f40da7c5f81cdc4fea8c29a7cbdece970518735d3e61cd5aebd95c51df9`) retained an identifying absolute `arguments.out` path in `results/ustat_reference/rare_event_diagnostic_manifest.json`. The earlier sanitizer only recognized paths beginning with `/Users/`; the diagnostic path began under a temporary directory and contained a personal username farther inside it.

The owner changed the sanitizer to recognize every absolute output path and broadened its identifier scan. The corrected code archive differs only in four metadata entries: the diagnostic manifest, anonymous provenance map, sequential-extension integrity manifest, and package manifest. No numerical output, executable source, TeX, or PDF changed in that repair. The source ZIP has a different container hash because it was regenerated, but all its entry payloads are unchanged.

All five mappings in `results/anonymous_provenance_map.json` were independently checked against the original working-tree manifests and the released copies. Every original/release SHA-256 is correct; parsed JSON differs only at `arguments.out`, now `results/ustat_reference`. The derived integrity manifest correctly hashes the anonymous copies. Original contributed manifests remain unchanged in the author tree.

The final archives passed a separate scan for known author usernames, repository-identifying strings, user-directory/temporary paths, and common live-credential formats. No credentials, `.env`, Git history, author-metadata file, or identifying paths were found. All ten included PDFs were checked for identifying text, metadata, and links; the manuscript Author field is empty. Metadata of the twelve included PNGs also passed. These are concrete scan results, not a claim that arbitrary unknown identifiers can be exhaustively detected.

## Clean reproduction and PDF equivalence

Two fresh extractions were used, without development checkout files:

1. In the corrected code extraction, `python3 reproduce.py --build-pdf` exited successfully. The scientific invariant checks passed, and **104 distinct archived result paths passed all 104 output-hash checks**.
2. In the separate source-only extraction, `latexmk -pdf -jobname=manuscript -interaction=nonstopmode -halt-on-error main.tex` also exited successfully.

Both rebuilt PDFs have **36 pages**. Their complete layout-preserving extracted text is byte-identical to the frozen submission PDF. All three extracted-text SHA-256 values are `b78c14f7597c679582f0219e87ab936bbf853f3dc7c542b2fd4579b948929d85`. PDF container bytes differ on rebuild because creation/modification metadata changes; byte-identical PDFs are not claimed. Final LaTeX logs have no unresolved citations/references, multiply defined labels, fatal errors, or overfull boxes. Ordinary float/underfull notices remain.

The environment was Python 3.14.4 with NumPy 2.4.1, SciPy 1.17.0, pandas 2.3.3, and Matplotlib 3.10.8; the four package versions match the pinned requirements. Latexmk 4.88 and pdfTeX 1.40.29 were used. This verifies local clean extraction on macOS, not an unperformed cross-platform container build.

## New table-builder integrity

The released `experiments/build_sequential_extensions.py` hash equals its recorded source hash:

`48769df354d904016b213fc58cd2601739a26e9d4fdeb1bdbded64629d33996c`.

All six recorded input hashes match the released data: U-statistic null calibration, main results, efficiency components, drift results, permutation results, and **rare-event diagnostic records**. In particular, the diagnostic CSV hash is `017d47dbab2813e91f59c52c3810adfb2bcc1e448b7010581e574aef34616199`; it is an explicit builder input rather than an untracked source for the diagnostic prose.

Running only this inexpensive builder in the isolated extraction reproduced all three generated TeX files and `results/sequential_extension_paper_manifest.json` byte-for-byte:

| Output | SHA-256 |
|---|---|
| `paper/sequential_extension_results.tex` | `d36c2712da2d0fc267a2c2312921ceadeb90d2b0b966eed09dcdc9d15c74cfdf` |
| `paper/ustat_extension_appendix.tex` | `570ee8ea1586e8cee8cfcc311bc8c1304db65feeb3fe0df10c2eaad07c58fb8f` |
| `paper/drift_extension_appendix.tex` | `00e728cca72b2c79289b3f03ee1b9911c4fb2063422aa7afc94367de2980daef` |
| `results/sequential_extension_paper_manifest.json` | `1b75d594cc2df096caa9bfd97b1bf832745bf900b971f597830c0b7d217d21b5` |

All packaged `.tex` files remain byte-identical after table regeneration and compilation. Other result builders and full simulation studies were not rerun in this release audit.

## Baseline preservation and executable code

Compared directly with Git revision `f806aba`, all **32 original result CSVs remain byte-identical in the author tree**. Of these, 24 are included in this release and are also unchanged. Eight historical/unintegrated CSVs are intentionally absent from the allowlisted release: seven under `results/benchmarks/` and `results/cs_width.csv`. Their exclusion is not deletion or replacement of the original baseline.

The preserved `results/source_baselines/reproducibility_manifest_pre_round10.json` is byte-identical to `f806aba:results/reproducibility_manifest.json`; SHA-256 `9693d60cbe78f4b31c23e0f86ae17b4d298ce93d2d4c6413664dde52d9a06a74`.

The released `src/winstats.py` has an identical executable AST to `f806aba` after removing module/class/function docstrings. Original hash: `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9`; integrated hash: `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69`. The documented extension of the fixed-stake running-mean interpretation therefore did not change the numerical algorithm used by the archived studies.

## Reproduction entry point and study boundary

The default mode verifies results and runs small invariant checks. `--build-pdf` compiles the supplied paper. Neither invokes an API collector. Historical commercial collection scripts are retained for provenance, but the entry point has no path that invokes them; this audit did not execute them.

The explicit `--extensions` branch uses sensible frozen CPU-study settings: the main all-pairs comparison at 2,000 replicates and 10,000 records per arm; the four boundary calibrations at 10,000 replicates; the separate rare-event diagnostic at its frozen defaults; and the drift panel with four workers. The runner accepts the specified worker counts. Main comparison/diagnostic seed 20260918 and drift seed 20260919 remain separate from the original primary simulation seed. The drift protocol hash passed by the entry point exactly matches the released `experiments/drift_panel/protocol.md`: `bb497cbb7c58fd1578530748c9d5ef834dc079e8b14973bc0bee348ca5c276cc`.

These argument checks are source-level verification, not a claim that the heavy extension reruns were executed in this audit. Runtime/platform/output-directory manifest fields may naturally differ in a fresh rerun; original frozen manifests and released anonymized mappings document the historical runs.

The audited package contains the accepted PR7 all-pairs comparison and PR10 drift extension, with a 36-page manuscript. **Pending PR8 local/open-model experiments are not part of this frozen package.** This audit does not resolve that experiment’s review/integration status, broader scientific readiness, author attestations, or venue submission requirements. Author-facing status sheets are outside the anonymous payload and were being updated separately by the package owner.

## Reproducible audit evidence

All scratch evidence is under the outer workspace `work/round10_release_audit/`, separate from the project/release tree: frozen and corrected archive copies; initial/delta inventory JSON; full result-hash checks; provenance mappings; new-builder checks; code and source build logs; extracted PDF text; final-log and PDF/PNG metadata checks. The decisive logs are `final_verify_build.log` and `final_latex_build.log`; machine-readable summaries are `delta_checks.json`, `builder_and_scan_checks.json`, `result_hash_checks.json`, `pdf_checks.json`, `final_log_metadata_checks.json`, and `media_scan.json`.

**Remaining actions for this audited release delta: none.** Any later PR8 integration or substantive archive change needs a new scoped release check.
