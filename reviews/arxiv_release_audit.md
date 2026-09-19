# Independent arXiv conversion and release audit

Date: September 19, 2026. Reviewer: independent release-audit agent.

**Disposition: PASS for the bounded local conversion and release checks below.** No change to the scientific evidence was identified. This is not human author signoff, an arXiv submission, or server-side compilation/moderation confirmation.

## Scope and examined snapshot

The review compares the new named preprint with frozen scientific commit `45e8ee2715f148c81db7f6510d66677f57e03f0a`. It examines `arxiv/build_arxiv_package.py`, all generated TeX changes, the 35-file source archive, reproducibility archive, their manifests, and the full and split PDFs. The integrator separately owns visual page review and official arXiv requirements/metadata. No models, full simulations or contributed experiments were run.

| Artifact | Reviewed SHA-256 |
|---|---|
| `arxiv/paper.pdf` | `8d75610e9e2183a63ab9e64b4e4b697da6aea4ebe343a9ee11d0363bf8777399` |
| `arxiv/main_paper.pdf` | `5e37e7744c79dcc76e4afa872f47000162e538349a3d4ae9083725d9dcaae3b5` |
| `arxiv/supplement.pdf` | `0ceaf58a0fcb90c9440e14d3e6c9445f9d11feba2b16365ee4d7ddcfa5bb128d` |
| `arxiv/arxiv_source.tar.gz` | `fd82e3e117a855c7a3f968ecb42e1022148bc8f37804018b2394e961afb43a9d` |
| `arxiv/reproducibility_code.zip` | `be3cec50e4d46a53889948400072b72bab36f2d5afe0b64ba7fc38836b10c17b` |

## Conversion and preservation

- All 27 TeX source transformation records match the original and generated file hashes. Literal source comparison finds format/author/date/PDF metadata changes, the public code link and reproducibility wording, figure-path relocation, a layout break after the asynchronous-corollary heading, and the stated abstract update. Equations, proofs, result tables and detailed inferential qualifications remain unchanged.
- The abstract now mentions the already recorded 1,182 coding episodes and 196 planned airline records and qualifies their descriptive/replay interpretation. It does not convert these into randomized production evidence or conceal the two planned-record placeholders.
- All 37 original `paper/` files are byte-identical to the frozen scientific commit. All 55 CSVs present in that commit are byte-identical in the repository. This count includes retained and excluded records; it is not the number of independent studies.
- All 208 non-paper payload files other than the explicitly replaced package README/manifest are byte-identical to the historical anonymous code archive. All 47 CSVs in that archived release are retained byte-for-byte. The new reproducibility archive contains 246 manifest-listed payload files plus its manifest; all hashes and sizes match, with no unlisted entries.
- Historical `submission/paper.pdf`, `anonymous_code.zip`, `latex_source.zip`, `package_manifest.json` and `abstract.txt` remain byte-identical to the frozen scientific commit. Later ICLR deadline/author handoff text changes are documentation history and are outside this frozen-artifact assertion.
- All five new artifact hashes/sizes match the outer manifest. Source-archive members and the reproducibility archive's `paper/` source files agree byte-for-byte with the generated source tree. The embedded `paper/manuscript.pdf` agrees with the full preprint.
- Text and extracted-PDF scans found no `/Users/` paths or tested API-key patterns. Author name and supplied institutional email are intentional public author information. This targeted scan is not a general secret-detection guarantee.

## Independent clean reproduction

The source archive was extracted to an isolated audit directory with no repository-relative dependencies. Archive names are unique, relative and free of parent traversal; every member is a regular file. Only `main.tex` declares a document. Its TeX inputs, six figure PDFs, BibTeX database and matching `main.bbl` are present.

Three independent `pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex` passes using the supplied bibliography produced 45 pages. Every page's extracted text matches the canonical full preprint exactly (combined page-text SHA-256 `5867e1031902676b52540d166681c6dfcf76cf33bee31e9aecb05aab7dc32e1b`). There are no undefined reference/citation, multiply defined label or overfull-box warnings. Underfull boxes and automatic `h`-to-`ht` float adjustments remain nonfatal layout diagnostics for the integrator's separate visual review.

The 13-page main-paper extract and 32-page supplement extract concatenate to the 45-page canonical paper with exact page-text and page-size agreement. Their internal links are intentionally omitted to avoid dangling destinations into the omitted part; the complete PDF remains the canonical document with cross-references.

The freshly extracted code archive's default `python reproduce.py` passed the six analytic truth checks and matched all 127 archived output hashes. It made no commercial requests and did not run full simulation, model or generated-candidate-code experiments. This validates release integrity and the prescribed default entry point, not a new independent replication of every numerical study.

## Remaining boundary

The local engine is pdfTeX 1.40.29 / **TeX Live 2026**. Compatibility with arXiv's target TeX Live 2025 processing is not server-confirmed. The submitter must inspect the actual arXiv-generated PDF and fulfill account, endorsement, license, scientific review and submission declarations. The audit supplies no publication or authorship attestation.

Machine-readable audit checks, the complete TeX diff and clean build log are retained in the isolated task scratch directory `work/arxiv_release_audit/` outside the release repository. This report is the tracked audit record; no original sources or artifacts were edited by the reviewer.
