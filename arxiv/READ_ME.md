# arXiv preprint handoff

**Prepared September 19, 2026. Technical preparation verified; not uploaded, announced, accepted or certified by the author.** The active target is arXiv. The historical ICLR release remains unchanged in `submission/` at scientific baseline `45e8ee2`.

## Files and their use

| File | Use |
|---|---|
| `paper.pdf` | Canonical 45-page preprint, including references and all supplementary proofs/results. |
| `main_paper.pdf` | 13-page reading copy: main text, statements and references. |
| `supplement.pdf` | 32-page reading copy: appendices, retaining pages 14–45 and original numbering. Read with the main paper. |
| `arxiv_source.tar.gz` | Upload this source archive to arXiv; select `main.tex` and pdfLaTeX. It builds the entire paper and supplement as one article. |
| `reproducibility_code.zip` | Audited code/results and the named paper sources; available from this repository. It is not the arXiv TeX upload archive. |
| `abstract.txt` | Plain-text metadata abstract matching the PDF. |
| `submission_metadata.json` | Prepared fields and explicit unresolved author choices. |
| `package_manifest.json` | Artifact SHA-256 values and source-conversion provenance. |

The separate main/supplement PDFs are convenience extracts, with cross-document links removed. All internal references remain live in the combined PDF. Upload the source archive, not those three PDFs or the entire repository. All proofs/results are included in the article itself, so no ancillary file is required for this package. Code is linked from the article to the public repository; the versioned code archive is committed here.

## Author steps

1. Review the complete science, citations, limitations and AI-use statement. The draft accurately says that agent checks do not establish completed human verification. If you complete that review, record it and revise the statement truthfully before rebuilding; no signoff has been inferred.
2. Confirm the prepared title, sole author **Yukang Zeng**, and contact **yukang.zeng@yale.edu**. No institutional affiliation or ORCID has been invented. Suggested primary category is **cs.AI**, with **stat.ME** as an optional cross-list because the paper develops evaluation/inference methods. Category suitability remains subject to author choice and moderation.
3. Select **arXiv.org perpetual, non-exclusive license 1.0** in the submission form, as you explicitly chose on September 19, 2026. This selection is recorded in the metadata. Verify your distribution rights and the actual submission agreement; recording the choice is not an attestation or an upload.
4. Sign in to your arXiv account, complete any category-specific endorsement, upload `arxiv_source.tar.gz`, choose `main.tex` and pdfLaTeX, and inspect arXiv's generated PDF. The local clean build used TeX Live 2026; arXiv currently defaults to TeX Live 2025. Its server build has not been tested by this agent.
5. Paste the metadata, review the actual submission agreements, and submit only after you are satisfied. Leave journal reference, DOI and arXiv identifier blank unless genuine values exist. This preparation does not assert prior publication or conference acceptance.

Official requirements and checked sources are summarized in [the arXiv requirements audit](../evidence/arxiv_requirements.md). The ICLR deadline, anonymous formatting and reciprocal-review requirements are historical; they do not govern this preprint package.

## Evidence and checks

The scientific content preserves the reviewed baseline. Conversion changes are the article layout, author/title metadata, figure paths, a layout break, an abstract summary of already included open-weight studies, and the public reproducibility pointer. No new experimental outcome was added. Independent clean compilation reproduced all 45 pages of text; six analytic checks and 127 saved-result checks passed. All 47 packaged CSVs and all 55 repository CSVs at the frozen baseline were preserved. Root inspected all 45 pages in contact sheets and enlarged selected equation/table/reference pages. See [release audit](../reviews/arxiv_release_audit.md) and [visual QA](../reviews/arxiv_visual_qa.md).

The fixed checklist is **90/100**: technical science/empirical/manuscript/release items verified, ten author-only points pending. This is not an acceptance probability or a claim that all conceivable experiments have been performed. See [readiness](../READINESS_TRACKER.md).

## Continued experiments

The current bounded v1 paper does not depend on a new study. A new prospective randomized open-weight study is claimed in [issue 11](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/issues/11). Its evidence may strengthen a later revision after protocol and independent result checks. Realized counts alone do not establish counterfactual savings. Use [the current queue](../EXPERIMENT_QUEUE.md) and [ownership rules](../COORDINATION.md). No new commercial model, paid compute or duplicate model collection is authorized. Historical commercial observations remain identified and preserved.

## Rebuild

Run `python3 arxiv/build_arxiv_package.py` from the repository root with PyMuPDF and pdfLaTeX/latexmk installed. The builder reads the frozen original paper and anonymous code package, writes only the arXiv output and ignored scratch, and makes no network/model call. Rebuilding may alter PDF byte hashes through TeX metadata; recheck the newly generated manifest and PDF before publishing. The standalone code archive's default `python reproduce.py` runs analytic tests and validates retained saved results; it does not collect new model episodes.
