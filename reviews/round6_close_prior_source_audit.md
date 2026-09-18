# Round 6: independent source audit of two close win-statistic priors

Reviewed September 17, 2026 (America/New_York). This is an AI scientific review, not human peer review. Scope: entries 50–51 of `evidence/lit_winstats.md` (currently lines 81–82), checked against original arXiv metadata and full HTML. No manuscript edits, result changes, or git mutations were made.

**Both entries exist and their identifiers, titles, author initials, and initial submission dates match the primary records. Neither is a fabricated or mismatched citation. Both warrant explicit related-work positioning.** This audit establishes source identity and substantive overlap; it does not certify either preprint's complete proofs, publication status, or exhaustive novelty clearance.

## Entry 50: verified, with an important inference qualification

**Kexuan Li, Xue Fan, Lingli Yang. _Worst-Case Win Ratios Under Partially Specified Outcome Hierarchies_. arXiv:2608.29857v1, submitted August 30, 2026.** [Original metadata](https://arxiv.org/abs/2608.29857).

Section 2 defines the minimum net benefit across protocol-permitted comparison rules. Section 3.3, equations (17)–(21) and Theorem 4, explicitly uses an intersection–union test and an infimum of one-sided lower bounds to establish a single all-rules positivity claim without an alpha split. Its coverage is **asymptotic, fixed-sample**, using two-sample U-statistics; it is not a finite-sample anytime guarantee. [Original full text](https://arxiv.org/html/2608.29857v1).

The local summary is substantively accurate but should state that qualification. My novelty assessment: this is a direct win-statistic precedent for the conjunction-testing argument and comparator-family robustness. Cite it where those ideas are positioned. Distinguish uncertainty over permissible comparison rules from uncertainty over unfinished episode outcomes. Do not present the no-split intersection–union principle as a new contribution of this manuscript.

## Entry 51: verified, and directly relevant to the motivation

**David McCoy, John Leopold, Shirley Galbiati, Minhthien Vu, Bonnie Zhang. _Priority-Standardized Net Benefit: A Stage-Normalized Estimand for Hierarchical Composite Endpoints_. arXiv:2607.22950v1, submitted July 24, 2026.** [Original metadata](https://arxiv.org/abs/2607.22950).

Section 3.2, equation (1), decomposes ordinary net benefit into reach probabilities times stage-conditional effects. Section 4.1, Definition 1, replaces reach weights with prespecified charter weights. Proposition 1 distinguishes this estimand from fixed weighted wins; Section 5.4 supplies large-sample inference. Section 8.4 explicitly retains within-layer bias and missingness limitations. [Original full text](https://arxiv.org/html/2607.22950v1).

The local description should say **stage-conditional** effects and avoid suggesting universal prevention of lower-tier dominance. Reach probabilities are population quantities estimated from data. My novelty assessment: this is direct precedent for the aggregate-priority motivation. Charter weighting does not itself enforce this manuscript's raw success/compliance noninferiority requirements; a power comparison would concern different targets unless the decision objectives were aligned.

## Implications for the submission

The initial audit required adding both citations before making a submission-ready novelty claim; root has now added them, as checked below. The defensible contribution remains the specified continuous-evaluation protocol, explicit component requirements, incomplete-episode certificates, and supporting evidence. Neither audited source establishes that complete package; neither permits novelty claims for the underlying intersection–union logic or the general aggregate-priority problem. No additional experiments are required solely to acknowledge these two priors. The previous borderline ICLR assessment remains appropriate, with greater confidence that close-prior positioning needs precision.

## Evidence retained and access limits

Full, version-pinned HTML was downloaded into `work/round6_sources/`; `retrieval_manifest.json` records URLs, sizes, timestamps, and SHA256 checksums. `primary_metadata.json` records the separately verified official metadata. Direct PDF and direct versioned-abstract downloads returned HTTP 406; the web tool successfully displayed both official abstract records and the complete primary HTML was available. PDF download failure is not evidence against either paper's existence. No journal acceptance claim is inferred from arXiv availability.

| Archived primary full text | Bytes | SHA256 |
|---|---:|---|
| `2608.29857v1.html.html` | 227671 | `6a7eb08b2bf0f50da7c472ed0753f86baa1fdbae3b6769b16b69de9346253c19` |
| `2607.22950v1.html.html` | 470052 | `43fe7a855bea06535d23d452acbb5afac93e97054062b0b32baf27a7172832ea` |

The date above is the local review date; the download manifest uses UTC (September 18). For citation dating, use each official submission history rather than an internal manuscript date.

## Follow-up: newly integrated attribution and illustrative calculation

I inspected the additions without editing their sources. **The requested attribution passages and the PSNB calculation pass; no factual correction is required.**

- `paper/main.tex:135–137` accurately attributes the marginal-potential-outcome contrast framework and inverse-probability/doubly robust estimation to Mao. The original publisher's indexed abstract supports these particular claims. Its issue citation is Lu Mao, *On causal estimation using U-statistics*, *Biometrika* 105(1), 215–220 (2018), DOI 10.1093/biomet/asx071; the publisher records online publication December 14, 2017. The existing BibTeX issue year is therefore appropriate. [Publisher record](https://academic.oup.com/biomet/article-abstract/105/1/215/4742247). This follow-up checked that attribution, not Mao's full proof: a direct publisher-page request failed after redirection.
- `paper/main.tex:365–377` accurately positions the two audited preprints and limits the manuscript's novelty claims. The new BibTeX entries at `paper/references.bib:182–196` match the primary metadata. “Explicitly limiting lower-tier influence” is acceptable in context as a description of the charter mechanism; it should not be expanded into unconditional raw-component protection.
- `paper/pairing_efficiency.tex:4–19`: independent algebra gives stage effects −0.1 and +1, reach probabilities 1 and 0.9, ordinary net benefit 0.8, and the weighted value 0.8(−0.1)+0.2(1)=0.12. The raw success effect −0.1 fails the stated 0.03 margin. Costs 1 versus 2 are decisive at 5% tolerance. The positive reach condition is satisfied. This is a valid illustrative separation of population requirements and is correctly not described as a calibration failure or comparative-power experiment.

These edits resolve the main-paper attribution action identified above. The retained literature ledger could still adopt the precision edits described in entries 50–51. No additional comparative simulation or competitiveness reassessment was undertaken or needed for this follow-up.
