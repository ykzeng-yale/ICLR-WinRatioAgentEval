# arXiv requirements and package decisions

Official sources checked September 19, 2026. This is a preparation audit, not server-side submission or an assurance of moderation acceptance.

| Topic | Official source and applicable requirement | Package decision / status |
|---|---|---|
| Submission format | [Submission overview](https://info.arxiv.org/help/submit/index.html): TeX is preferred; a PDF generated from TeX is not a substitute for its source. | Upload `arxiv/arxiv_source.tar.gz`, not PDF-only. |
| TeX dependencies | [TeX submission](https://info.arxiv.org/help/submit_tex.html): include used figures/styles/bibliography and remove irrelevant build products. Review the resulting server PDF. | One root `main.tex`, all referenced sources, six figures, `.bib` and matching `.bbl`; no compiled article or logs inside upload archive. |
| Compiler | [TeX Live at arXiv](https://info.arxiv.org/help/faq/texlive.html): current default is TeX Live 2025, with supported processor choices. | Standard article/pdfLaTeX; independently tested locally with TeX Live 2026. Server compatibility remains to be checked in author preview. |
| Supplement | [Ancillary files](https://info.arxiv.org/help/ancillary_files.html): ancillary material accompanies the source under `anc/`; ancillary TeX is not a second manuscript route. | All supplementary proofs/results are part of the compiled article. Separate main/supplement PDF extracts are for reading, outside the upload archive. Code stays in the linked versioned repository. |
| Metadata | [Required/optional fields](https://info.arxiv.org/help/prep.html): title, authors and abstract must accurately describe the work. | Prepared matching title/abstract and sole author; no invented affiliation, DOI, journal reference or arXiv identifier. |
| License | [Licenses](https://info.arxiv.org/help/license/index.html): authors must grant distribution permission and select a license. | Author explicitly selected arXiv.org perpetual, non-exclusive license 1.0 on September 19, 2026. Distribution-rights/submission attestation remains an author step. |
| Account/endorsement | [Endorsement](https://info.arxiv.org/help/endorsement.html): new authors/categories may require endorsement. | Account and endorsement status unknown; institutional email is not evidence of completed endorsement. |
| Scientific responsibility | [Submission overview](https://info.arxiv.org/help/submit/index.html), [moderation](https://info.arxiv.org/help/moderation/index.html): refereeable topical scholarship, author agreement, and moderation apply. | Author must review science, sources, rights and the actual agreements. The substantial AI assistance statement is retained; internal model review is not human peer review. |

Suggested primary `cs.AI`, with optional `stat.ME` cross-list, is an editorial recommendation based on the article's agent-evaluation setting and statistical inference contribution, not a confirmed category assignment. arXiv is a preprint repository; posting is not peer-reviewed acceptance. There is no ICLR-style main-text limit in the preparation requirements reviewed here. The 45-page combined article preserves all proofs and empirical caveats without an ICLR anonymous header.

The author requested an arXiv transition after the ICLR deadline. The original conference archive and its historical requirements remain intact. Package delivery, author review, server preview, submission and announcement are separate states.
