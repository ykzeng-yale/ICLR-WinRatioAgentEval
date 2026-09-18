# ICLR 2027 review standard, exemplar analysis, and internal review rubric

Prepared 2026-09-17 (America/New_York; some tool timestamps read 2026-09-18 UTC). Extends `evidence/venue_and_novelty.md`, `evidence/theory_design.md` and `evidence/empirical_feasibility.md`; it does not repeat their novelty audit. Every factual statement below comes from a page that was opened during this pass unless it is explicitly marked UNVERIFIED. Third-party aggregations (Paper Copilot dumps, arXiv analyses of OpenReview) are labelled as such.

Access limitation that shapes this document: OpenReview forum pages and both OpenReview API endpoints returned a "Verifying your browser" human-verification challenge for every request (curl, WebFetch and the browser pane). Bypassing bot-detection is prohibited, so no OpenReview review text was read. Numeric scores were instead taken from the Paper Copilot `paperlists` JSON dumps on GitHub (`iclr2024.json`, `iclr2025.json`, `iclr2026.json`, fetched 2026-09-17), which scrape the public OpenReview API. Reviewer criticisms for individual papers are therefore UNVERIFIED here; only score patterns are reported.

---

## 1. Official ICLR 2027 rules (primary sources opened 2026-09-17)

Sources: `iclr.cc/Conferences/2027/CallForPapers`, `/AuthorGuidelines`, `/ReviewerGuidelines`, `/AIPolicyForAuthors`, `/AIPolicyForReviewers`, `/Dates`, `/FAQ` (the FAQ page is only a directory pointing to the Author/Reviewer/AC guides), the ICLR blog post "Submission policies for ICLR 2027" (2026-09-02), and the official style-file zip `media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip`.

### 1.1 Dates (Anywhere on Earth)

| Milestone | Date |
|---|---|
| Abstract deadline | Sep 18, 2026, 11:59 PM AoE |
| Full paper deadline | Sep 25, 2026, 11:59 PM AoE |
| Reviewer bidding | Sep 18 - Sep 25 |
| Reviews written | Oct 1 - Oct 21 |
| Reviews released; author-reviewer discussion | Nov 5 - Nov 18 |
| CoE flags due | Nov 18 |
| Reviewer-AC discussion, final recommendations | Nov 19 - Nov 25 (borderline meetings Nov 26 - Dec 2) |
| Decisions | Dec 16, 2026 |
| Conference / workshops | Apr 26-28, 2027 / Apr 29-30, 2027 (Dates page; location not stated on the pages opened) |

### 1.2 Format and page limits (Author Guidelines; confirmed in `iclr2027_conference.tex` line 131)

- Main text: at most **9 pages** at submission; **10 pages** for rebuttal revisions and camera-ready. "Papers with main text beyond the page limit will be desk-rejected."
- References: unlimited. Appendices: unlimited, but "reviewers are not required to read the appendix."
- Must use the ICLR 2027 LaTeX style files.
- Titles/abstracts editable until the paper deadline; no title changes after the deadline until the end of discussion. No author additions/removals after the abstract deadline; order may change until the paper deadline. All authors need OpenReview profiles (non-institutional-email profiles can take up to two weeks to moderate).

### 1.3 Required and recommended statements (Author Guidelines + template `\subsection*` headings)

The template places three unnumbered subsections after the main text, all excluded from the page limit:

1. **AI use statement (required).** Template heading `\subsection*{AI use statement}`; "(This section is required and does not count toward the page limit.)" and "should not be more than 1 page." Template boilerplate (verbatim from the .tex):

   > In this work, we used generative AI tools for [tasks with required disclosure]. We have not used generative AI tools for [other tasks with required disclosure], and [the rest of the required disclosure tasks] are not applicable to this work. Additionally, we used generative AI tools for [tasks with recommended disclosure]. We have reviewed all AI-assisted work. [Elaborate. For example, "we checked LLM-generated research ideas for potential plagiarism through a manual literature survey", "LLM-generated code was verified and tested for correctness by 2 authors", etc.]. We take responsibility for the final content of this work, including text, claims or artifacts produced with the aid of generative AI.

   The same disclosure is also solicited on the OpenReview submission form.

2. **Ethics statement (recommended).** At most 1 page, placed at the end of the main text before references; topics listed include human subjects, dataset release practices, potentially harmful insights, conflicts of interest and sponsorship, bias/fairness, privacy/security, legal compliance, research integrity (IRB, documentation).

3. **Reproducibility statement (recommended, "strongly encouraged").** Paragraph-long; should not itself contain the details but point to the parts of the paper/appendix/supplement that enable reproduction: anonymous code link for algorithms, "clear explanations of any assumptions and a complete proof of the claims" in the appendix for theory, complete data-processing description for datasets.

### 1.4 AI Policy for Authors (page opened; wording condensed, key lists verbatim)

- Authors must state LLM use "both in the paper's text as well as in the paper submission form." Authors "are responsible for the contents of their submissions"; "a substantial falsehood, instance of plagiarism, or misrepresentation produced by an LLM would be considered a Code of Ethics violation ... and might lead to desk rejection."
- **Required disclosure** tasks: "Generate synthetic data sets, help develop theoretical models or conceptual frameworks, formulate mathematical claims, provide critical ingredients for proving mathematical claims, assist in the writing of proofs, propose or refine hypotheses, design or provide feedback on research methodology or experiments, implement methods, assist with translation, clean and reformat dataset, support qualitative and thematic data analysis, interpret results."
- **Recommended disclosure** tasks: "Formulate questions for surveys or interviews, create or modify scientific figures or images, suggest experimental parameters, create or edit software code, creation of artifacts, draft parts of a research paper, transcribe recordings of research material, summarize or analyse existing literature, discover research topics or identify gaps, brainstorming, sourcing/searching for information, edit a research paper to improve readability, identify relevant literature, format references, suggest a structure for a research paper, propose a title or keywords for a research paper."
- Implication for this project: our workflow uses LLM agents for theory drafting, proofs, experiment design, implementation, data cleaning and result interpretation. Every one of those is in the **required** list; the statement must name them explicitly and describe the human verification performed (who checked which proofs, which code was tested, how citations were verified). The ICLR 2026 retrospective (blog, 2026-03-31) reports that submissions were desk-rejected for hallucinated references, so citation verification must be documented.

### 1.5 AI Policy for Reviewers and ACs (page opened)

- "Limited and responsible use of AI tools to assist human writing of peer reviews and meta-reviews" is permitted, with mandatory disclosure. Reviewers must record their "original, self-written paper assessment, and any LM interactions, in an accompanying textbox"; multi-turn LLM use requires sharing the input across all turns.
- Violations: LLM-generated "falsehoods, hallucinations, or misrepresentations"; low-quality reviews; using AI to write the self-report; "substantial mismatches between the content of the original self-report and final reviews." Penalties range up to desk-rejecting all of the violating reviewer's papers and future-submission restrictions; ICLR may use AI-detection tools.
- Consequence for us as reviewers (reciprocal duty) and for our internal review rounds: each internal review should keep a human-written core assessment separate from any LLM-assisted expansion.

### 1.6 Anonymity, code, dual submission, withdrawal

- Double blind. "Any paper where author identity is revealed in either the main text or the supplementary material will be desk rejected." Own arXiv papers may be cited in the third person.
- Code: "We encourage all authors to submit code as part of their submission"; reviewers "are encouraged, but not required to review supplementary material." Supplementary text goes after the references, clearly marked as appendix.
- Dual submission: identical or substantially similar work previously published/accepted or under parallel review is prohibited; arXiv and non-archival workshops are fine; posting to arXiv during review is allowed.
- Withdrawal after the paper deadline leaves the paper publicly visible and immediately de-anonymized; all submissions (including rejects) are de-anonymized at decision time.

### 1.7 Reciprocal reviewing and quotas (Author Guidelines; blog post 2026-09-02)

- Authors on **3 or more** papers must review **at least 6** papers; failure to deliver "complete, high-quality reviews by the rebuttal stage" may desk-reject their submissions.
- Every submission needs at least one author registered to review at least 3 papers who is "qualified": at least one accepted primary-track paper at ICLR/NeurIPS/ICML/UAI/AISTATS/JMLR/TMLR (incl. Datasets & Benchmarks), ACL/EMNLP/EACL/NAACL/IJCNLP-AACL/CL/TACL (incl. Findings), COLM, CVPR/ICCV/ECCV/PAMI/3DV, AAAI/IJCAI/JAIR, ICRA/IROS/RSS/CoRL, KDD, COLT. Position papers, tiny papers, blog posts, demos, industry and workshop papers do not count. Eligibility is fixed by papers **accepted by the abstract deadline** (an accepted NeurIPS 2026 paper does not count).
- Quotas: at most 20 papers per author; at most one paper per author on which no co-author is an eligible reciprocal reviewer. Excess submissions are randomly desk-rejected at the paper deadline. "Incorrect information on your profile will be grounds for desk rejection."
- Blog context: at ICLR 2026 about 20% of submissions had no reciprocal reviewer; those were desk-rejected at roughly 25% and accepted at about half the rate of the others.
- The reviewer guide's own FAQ still carries 2026 text ("I have more than 3 submissions to ICLR 2026 ...") and a contemporaneous-work cutoff computed from a "September 16" deadline ("on or after July 17, 2026"); the actual 2027 paper deadline is Sep 25, so the operative two-month cutoff is probably ~Jul 25, 2026. Treat the July 17 date as the published-but-inconsistent text.

### 1.8 Reviewer Guide: what reviewers are told to do (2027 page opened; identical structure to the 2026 guide)

Reviewer virtues asked for: "Be rigorous", "Be open-minded" ("not all work needs to compete on an established leaderboard, or work in an established theoretical framework"), and new emphasis "Be concise" ("Longer reviews aren't always better! Please only discuss points that are actually likely to influence your final accept / reject decision").

The **four key questions** every reviewer must answer:

1. "What is the specific question and/or problem tackled by the paper?"
2. "Is the approach well motivated, including being well-placed in the literature?"
3. "Does the paper support the claims? This includes determining if results, whether theoretical or empirical, are correct and if they are scientifically rigorous."
4. "What is the significance of the work? Does it contribute new knowledge and sufficient value to the community? Note, this does not necessarily require state-of-the-art results."

The prescribed **written-review organization** (this is what the text fields of the form correspond to):

1. Summary of the claimed contribution ("Be positive and constructive").
2. Strong and weak points ("clear, technically correct, experimentally rigorous, reproducible, does it present novel findings").
3. Initial recommendation (accept/reject) "with one or two key reasons."
4. Supporting arguments.
5. Questions for the authors.
6. Additional feedback explicitly marked as not part of the decision.
7. Code-of-Ethics report: two questions (is there a potential violation; if so, why).

FAQ rules that matter for us: reviewers "can ask for additional experiments" but they "should be limited in scope and serve to more thoroughly validate existing results"; "a lack of state-of-the-art results does not by itself constitute grounds for rejection"; supplementary material need not be read; contemporaneous (published within two months) and arXiv-only work "cannot be a basis for rejection" if not compared, though citing it is strongly encouraged.

---

## 2. The numeric review form

The ICLR web guides do not publish the OpenReview form. The 2027 form is not yet created (the OpenReview invitation `ICLR.cc/2027/Conference/-/Official_Review` returned 404 on 2026-09-17; the 2026 one returned "InvitationExpiredError"). What is established:

**Fields (from the arXiv study "Insights from the ICLR Peer Review and Rebuttal Process", arXiv:2511.15462, which parsed 74,776 ICLR 2024-2025 reviews, and from the Paper Copilot dumps, whose per-review fields are `rating`, `confidence`, `soundness`, `presentation`, `contribution` plus word counts for `summary`, `strengths`, `weaknesses`, `questions`):**

| Field | Type | Scale |
|---|---|---|
| Summary | text | - |
| Soundness | numeric | 1-4 (observed values 1..4 in all three years) |
| Presentation | numeric | 1-4 |
| Contribution | numeric | 1-4 |
| Strengths | text | - |
| Weaknesses | text | - |
| Questions | text | - |
| Flag for ethics review / CoE report | choice + text | (Reviewer Guide: two-question CoE report) |
| Rating | numeric | 2024-2025: {1,3,5,6,8,10}; **2026: {0,2,4,6,8,10}** |
| Confidence | numeric | 1-5 (observed 1..5) |
| LLM-use disclosure by the reviewer | text | added in 2026 ("The review form will include a field to specify how you used LLMs, if at all", 2026 Reviewer Guide); 2027 policy requires the self-written assessment plus LM interactions in "an accompanying textbox" |

**Verified scale values.** Paper Copilot dump value counts across all reviews: ICLR 2025 ratings occur only at 1 (1,029), 3 (11,539), 5 (13,102), 6 (14,695), 8 (6,214), 10 (172). ICLR 2026 ratings occur only at 0 (1,319), 2 (19,865), 4 (29,765), 6 (19,712), 8 (5,010), 10 (188). arXiv:2511.15462 states the same change ("{1,3,5,6,8,10}" for 2024/2025, "{0,2,4,6,8,10}" for 2026).

**Scale labels: UNVERIFIED.** The commonly reported 2024/2025 labels (1 strong reject; 3 reject, not good enough; 5 marginally below the acceptance threshold; 6 marginally above the acceptance threshold; 8 accept, good paper; 10 strong accept, should be highlighted) appeared only in search-engine snippets during this pass, not on a page we opened. No opened source gave the 2026 labels; a substack post (randomfeatures, "Do papers submitted later receive lower review scores?") says the borderline-accept value moved from 6 to 5 for 2026, which is inconsistent with the observed even-only values and must be treated as unreliable. **Assumption for our rubric:** we use the task-specified 1/3/5/6/8/10 semantics and give an explicit mapping to the 2026 even scale (0 strong reject, 2 reject, 4 marginally below, 6 marginally above, 8 accept, 10 strong accept), flagged as an assumption.

**Calibration: what average rating gets accepted (Paper Copilot dumps; withdrawn and desk-rejected excluded).**

| Mean rating (rounded to 0.5) | ICLR 2025 accept rate (n) | ICLR 2026 accept rate (n) |
|---|---|---|
| 4.0 | 0.01 (746) | 0.12 (2,265) |
| 4.5 | 0.01 (574) | 0.29 (2,794) |
| 5.0 | 0.08 (1,462) | 0.54 (2,123) |
| 5.5 | 0.20 (1,007) | 0.79 (1,825) |
| 6.0 | 0.66 (2,044) | 0.93 (1,005) |
| 6.5 | 0.94 (887) | 0.97 (465) |
| 7.0 | 0.95 (758) | 0.99 (171) |

Mean sub-scores, accepted vs rejected: 2026 soundness 2.84 vs 2.49, presentation 2.86 vs 2.55, contribution 2.68 vs 2.27, rating 5.40 vs 3.96; 2025 soundness 2.91 vs 2.50, presentation 2.90 vs 2.54, contribution 2.72 vs 2.26, rating 6.46 vs 4.80. Confidence does not separate outcomes (3.5-3.7 in both groups). Official 2026 figures (ICLR blog retrospective, 2026-03-31): 19,525 valid submissions, 779 desk rejections for procedural/content violations plus additional ones for hallucinated references, 5,042 withdrawals, 13,763 decided, 5,355 accepted (27.4%), 76,139 reviews from 18,054 reviewers. Practical reading: on the 2026 scale a paper needs essentially all reviewers at 6 or above (mean >= 5.5) to be likely accepted; a single 2 or 4 that is not lifted in rebuttal is usually fatal. arXiv:2511.15462 reports that 75-81% of scores never change after rebuttal, 17-23% increase, and papers with an increased score were accepted 57-58% of the time versus 7-12% for unchanged scores; arXiv:2509.25701 (28,000+ ICLR 2017-2025 submissions) finds timely, substantive rebuttals and provided code/data (accept rate 43.96% vs 32.54%) are the strongest process-level correlates of acceptance.

---

## 3. Outstanding papers (official ICLR blog posts opened)

**ICLR 2026** (blog, 2026-04-23; 36 candidates -> 5 finalists -> 12-member committee vote):
- Outstanding: *Transformers are Inherently Succinct* (Bergsträßer, Cotterell, Lin) - theoretical, "conceptual contribution despite some criticisms".
- Outstanding: *LLMs Get Lost In Multi-Turn Conversation* (Laban, Hayashi, Zhou, Neville) - committee cited "exceptional experimental design and methodology" and a practically important train/deploy mismatch.
- Honorable mention: *The Polar Express* (Amsel, Persson, Musco, Gower) - "principled approach" from approximation theory; committee noted empirical gains were sometimes modest.

**ICLR 2025** (blog, 2025-04-22; 36-paper pool, ranking on "theoretical insights, practical impacts, exceptional writing, and experimental rigor"):
- Outstanding: *Safety Alignment Should be Made More Than Just a Few Tokens Deep*; *Learning Dynamics of LLM Finetuning*; *AlphaEdit: Null-Space Constrained Model Editing*.
- Honorable mentions: *Data Shapley in One Training Run*; *SAM 2*; *Faster Cascades via Speculative Decoding*.

Lesson: none of the six 2025 awards is an evaluation-methodology paper; the 2026 award to *LLMs Get Lost* was for a diagnosis established by a controlled, large-scale, reproducible experimental design, not for a new statistic. The stated award criteria (theory insight, practical impact, writing, experimental rigor) are the same four axes our rubric weights.

---

## 4. Accepted ICLR 2024-2026 exemplars in evaluation / statistical methodology

Scores are the final listed per-reviewer values from the Paper Copilot dumps (order: rating / soundness / presentation / contribution / confidence). Structure facts come from the official proceedings PDFs (parsed locally with pypdf) or arXiv HTML, as noted. Reviewer criticisms are UNVERIFIED (OpenReview inaccessible); the score pattern is reported instead.

### 4.1 Conformal Risk Control - ICLR 2024 Spotlight (OpenReview 33XGfHLtZg)
- Source: proceedings PDF (21 pages; references begin p.10, so 9 main pages).
- Contribution: extends split conformal prediction to control the expectation of any bounded monotone loss; finite-sample guarantee plus tight lower bound; extensions to distribution shift, quantile risk, multiple risks, adversarial risk, U-statistic risk.
- Structure: 1 Introduction (1.1 algorithm and preview, 1.2 related work); 2 Theory (2.1 risk control, 2.2 tight lower bound, 2.3 general losses); 3 Examples (four applied tasks: tumor segmentation FNR, multilabel FNR, hierarchical classification graph distance, open-domain QA F1); 4 Extensions (five subsections); 5 Conclusion. Roughly 2.5 pages theory, 3.5 pages examples, 1.5 pages extensions. The string "Theorem" appears 33 times across main text and appendix (proofs included); the main text states a small number of theorems and a lower-bound proposition (exact count not established here).
- Statistics reporting: no confidence intervals, bootstrap or p-values in the text; guarantees are demonstrated by empirical risk histograms over random splits.
- Scores: 6,6,6,8,8,8 (mean 7.0) / soundness 3,3,3,4,3,4 / presentation 3,3,3,4,3,4 / contribution 3,2,3,4,3,4 / confidence 3,4,3,4,3,4. Six reviewers, no score below 6.
- Lesson: a short general theorem with one-line algorithm, four real tasks each showing the guarantee holds, and a compact extensions section. Theory-first papers succeed at ICLR when the theorem is simple to state, the algorithm is one line, and each example is a concrete ML task.

### 4.2 SWE-bench - ICLR 2024 Oral (OpenReview VTF8yNQM66)
- Source: arXiv HTML v3 (comment field: ICLR 2024); Paper Copilot dump.
- Contribution: 2,294 real GitHub-issue tasks across 12 repositories, execution-based grading; SWE-Llama fine-tunes; best model resolved 1.96%.
- Structure (arXiv v3): 1 Introduction; 2 SWE-bench (construction, task formulation, features, Lite); 3 SWE-Llama; 4 Experimental setup (retrieval, input format, models); 5 Results (+ qualitative analysis); 6 Related work; 7 Discussion; Ethics and Reproducibility statements. Zero theorems. Resolution and patch-apply rates reported as percentages without error bars or significance tests.
- Scores: 5,6,6,8 (mean 6.25) / soundness 2,3,3,3 / presentation 3,3,4,4 / contribution 2,3,3,4 / confidence 3,4,2,4. An Oral with a 5 and soundness 2 from one reviewer: impact and the resource carried it.

### 4.3 τ-bench - ICLR 2025 Poster, primary area "datasets and benchmarks" (OpenReview roNSXZpUDN)
- Source: proceedings PDF (53 pages; references begin p.10, so 9 main pages).
- Contribution: simulated-user + tool + policy benchmark (retail, airline); database-state grading; pass^k reliability metric; finding that gpt-4o succeeds on <50% of tasks and pass^8 < 25% in retail.
- Structure: 1 Introduction; 2 Related work; 3 (benchmark/metric definition, heading not captured by the parser); 4 Benchmark construction (domains, key characteristics); 5 Experiments (main results, research-challenge analysis, user-simulation methods); 6 Discussion. Zero theorems; no confidence intervals or bootstrap; "significan*" appears six times.
- Scores: 6,6,6,8 (mean 6.5) / soundness 3,3,2,4 / presentation 3,3,4,4 / contribution 3,3,2,4 / confidence 3,4,4,4.

### 4.4 WildBench - ICLR 2025 Spotlight (OpenReview MKEHCx25xp)
- Source: iclr.cc virtual page and proceedings listing (opened); Paper Copilot dump.
- Contribution: 1,024 real-user tasks; checklist-guided LLM judging; WB-Reward with five-level pairwise outcomes and a length-bias correction; WB-Score; validation by correlation with Chatbot Arena human rankings (Pearson 0.98 for top models per the abstract).
- Scores: 6,8,8 (mean 7.33) / soundness 3,3,3 / presentation 3,3,3 / contribution 3,4,3 / confidence 4,4,5. Only three reviewers; the external-validity evidence (agreement with humans) is the paper's statistical core.

### 4.5 A Statistical Framework for Ranking LLM-based Chatbots - ICLR 2025 Poster (OpenReview rAoEub6Nw2)
- Source: arXiv HTML 2412.18407v2; Paper Copilot dump.
- Contribution: factored tie model generalizing Rao-Kupper/Davidson; Thurstonian covariance between competitors; identifiability constraints; open-source `leaderbot` package; fit to Chatbot Arena data (129 competitors, 1,374,996 comparisons; 20.4% ties).
- Structure: 1 Introduction; 2 Statistical model (problem, probabilistic models, ties, covariance, symmetry constraints); 3 Empirical evaluation of statistical models (win/loss/tie matrix prediction); 4 Ranking and comparison (ranking, correlations); 5 Conclusion; appendices A-G. Three formal statements, all in the appendix (Theorem B.1 on Fisher-information singularity, Propositions B.1 and C.1). Experiments: 30 model configurations compared by RMSE, KL/JS divergence, Kendall tau, bump charts, kernel PCA.
- Scores: 5,6,6 (mean 5.67) / soundness 3,3,4 / **presentation 1,2,2** / **contribution 1,3,3** / confidence 3,4,3. This is the closest analogue to our paper (pairwise comparisons, ties, ranking) and it was accepted at the margin with the lowest presentation scores of any exemplar: sound but judged hard to read and, by one reviewer, of low contribution. Concrete warning for us.

### 4.6 LLMs Get Lost In Multi-Turn Conversation - ICLR 2026 Oral, Outstanding Paper (OpenReview VKGTGGcwl6)
- Source: proceedings PDF (41 pages; references begin p.11, so 10 main pages at camera-ready).
- Contribution: sharded-instruction simulation isolating single- vs multi-turn performance; 200,000+ simulated conversations, six generation tasks, 15 LLMs (per abstract); decomposition of the 39% average drop into aptitude loss vs unreliability.
- Structure: 1 Introduction; 2 Background and related work; 3 Simulating underspecified multi-turn conversation (sharding process, simulation, simulation types); 4 Experiment (task selection, simulation metrics, scale and parameters); 5 Results (average performance, ..., gradual sharding experiment); 6 Implications summary; 7 Conclusion; 8 Ethics statement; 9 Reproducibility statement. Zero theorems; one definition. No confidence intervals, bootstrap or p-values found in the text; "significan*" appears 9 times.
- Scores: 6,8,8,10 (mean 8.0) / soundness 2,3,4,4 / presentation 3,3,4,4 / contribution 3,3,4,4 / confidence 4,3,4,5.
- Lesson: an evaluation paper with zero theorems won the top award on the strength of a clean experimental design, a two-component decomposition metric, scale, and a crisp practical message. Note the soundness 2 from one reviewer despite the award: uncertainty reporting is a recurring gap even in celebrated evaluation papers, which is an opening for us.

### 4.7 How Reliable is Language Model Micro-Benchmarking? - ICLR 2026 Oral (OpenReview cReExMQLiK)
- Source: arXiv HTML 2510.08730v2; mlanthology page (venue ICLR 2026); Paper Copilot dump.
- Contribution: MDAD (minimum detectable ability difference), the smallest full-benchmark accuracy gap at which a micro-benchmark preserves pairwise rankings at least 80% of the time; finding that no method reliably ranks pairs 3.5 points apart on MMLU-Pro or 4 points apart on BBH, and that ~250 examples are often needed, where random sampling is competitive.
- Structure: Introduction; Micro-benchmarking preliminaries; MDAD meta-evaluation; Experimental design; Results (5 subsections); Discussion and conclusion. Zero theorems. Experiments: MMLU (10,631 ex.), MMLU-Pro (12,032), BBH (5,761), GPQA (448); roughly 366-470 models; six selection methods; 50 trials with 95% bootstrap CIs.
- Scores: 4,6,8,8 (mean 6.5) / soundness 3,3,4,4 / presentation 3,2,4,4 / contribution 3,2,3,3 / confidence 4,3,3,5. Accepted as an Oral despite one 4: purely empirical statistics-of-evaluation work with a simple, decision-relevant quantity.

### 4.8 Noisy but Valid: Robust Statistical Evaluation of LLMs with Imperfect Judges - ICLR 2026 Poster (OpenReview hEhxreaLdU)
- Source: arXiv HTML 2601.20913; Paper Copilot dump.
- Contribution: hypothesis-testing certification of an LLM's failure rate using an imperfect LLM judge; TPR/FPR estimated on a small human-labelled calibration set; variance-corrected threshold with finite-sample Type-I control; conditions under which noisy testing beats direct testing; comparison against prediction-powered inference variants.
- Structure: 1 Introduction; 2 Related work; 3 Certification setting; 4 Procedure; 5 Guarantees (Theorems 5.1-5.4: Type-I control, Type-II characterization, noisy vs oracle, noisy vs direct); 6 Experiments (Jigsaw, Hate Speech, SafeRLHF; two LLaMA judges; three evaluated models; Type-I/Type-II error and estimation stability); 7 Conclusion.
- Scores: 2,4,8,8 (mean 5.5) / soundness 2,3,3,3 / **presentation 1,1,3,3** / contribution 2,3,3,3 / confidence 3,3,3,3. The most polarized exemplar: two reviewers strongly positive, two negative with presentation 1. It is the paper most similar in flavour to ours (finite-sample validity, calibration, judge noise) and it barely got in. Same warning as 4.5.

### 4.9 Cross-exemplar pattern

| | Theorems in main text | Real ML tasks / datasets | Uncertainty reporting | Outcome |
|---|---|---|---|---|
| Conformal Risk Control | few, simple | 4 | histograms of realized risk | Spotlight, 7.0 |
| SWE-bench | 0 | 1 benchmark, 12 repos | none | Oral, 6.25 |
| τ-bench | 0 | 2 domains | pass^k, no CIs | Poster, 6.5 |
| WildBench | 0 | 1,024 tasks | correlation with humans | Spotlight, 7.33 |
| Statistical Framework | 0 (3 in appendix) | 1 dataset, 30 model configs | fit metrics | Poster, 5.67 |
| LLMs Get Lost | 0 | 6 tasks, 15 models, 200k sims | none found | Oral + award, 8.0 |
| Micro-benchmarking | 0 | 4 benchmarks, ~400 models | bootstrap CIs, 50 trials | Oral, 6.5 |
| Noisy but Valid | 4 | 3 datasets | Type-I/II curves | Poster, 5.5 |

Observations: (i) ICLR accepts evaluation-statistics work; the ones that scored highest either had a one-line method with a crisp guarantee applied to several real tasks, or a large well-designed experiment with a memorable finding. (ii) The two papers most like ours (4.5, 4.8) were accepted at the threshold with presentation scores of 1-2: statistics papers at ICLR lose points on readability and perceived contribution, not soundness. (iii) Nine or ten main pages are used by all; theory papers keep proofs in the appendix and spend more than half the main text on examples.

---

## 5. Why statistics-flavoured papers get rejected at ICLR (evidence and inference)

Evidence base (opened): the 2027 Reviewer Guide (four key questions, "Be open-minded"), arXiv:2511.15462 (taxonomy over 74,776 ICLR 2024-25 reviews), arXiv:2509.25701 (process-centric analysis), the Paper Copilot dumps (score patterns in Sec. 4), the ICLR 2026 retrospective blog. Direct meta-review quotes could not be retrieved (OpenReview blocked); the specific phrases in the task prompt are therefore not attributed to particular papers.

arXiv:2511.15462 taxonomy (10 categories) with the subcategories most relevant to us:
- Novelty & Contribution (the top-ranked feature for rejection): lack of originality; incremental improvement; lack of clear contribution; overclaiming novelty; overlapping with prior work; work not mature enough.
- Methodology & Technical Soundness: weak theoretical justification; incorrect/unrealistic assumptions; overly complicated model; cherry-picked design choices; unclear algorithmic description; scalability.
- Experiments & Evaluation: insufficient baselines; limited datasets/domain coverage; small-scale experiments; poor generalizability; missing ablations; reproducibility issues; **missing statistical tests**.
- Motivation: weak/missing motivation; problem not justified as important; no clear real-world/theoretical relevance.
- Venue Fit: a distinct category (subcategories not enumerated in the text we opened).
- Low-rated papers are "dominated by writing flaws ... and experimental flaws"; high-rated papers are praised for novelty and methodology. Rejected papers get longer Weaknesses sections; accepted ones get longer Summary/Strengths/Questions.

Mapped to our manuscript, the failure modes a reviewer is most likely to invoke:

1. **"Application of a known method" / incremental.** GPC/win statistics (Buyse 2010, Pocock 2012), sequential win statistics (Zhang & Wu 2024; Bergemann & Hanson 2026), U-statistic confidence sequences (Cai, Hu & Li 2026), bounded-mean betting CSs (Waudby-Smith & Ramdas 2024) and gated deployment with CSs (Karampatziakis et al., ICML 2021) all exist; `evidence/theory_design.md` already concedes none of our probabilistic machinery is new. A reviewer who knows any two of these will write "incremental" unless the paper leads with the identification/design result and the agent-specific decision evidence.
2. **"Unclear relevance to the ML community" (Venue Fit).** Clinical win-ratio language, alpha-spending, DOOR terminology. The 2027 guide tells reviewers to be open-minded, but the Statistical Framework and Noisy-but-Valid presentation scores show the cost of statistics-native exposition. Every result must be stated in terms of agent systems, benchmarks, deployment decisions.
3. **"Limited empirical evaluation."** Simulation plus one reanalysed dataset triggers "small-scale experiments" and "limited datasets"; the 2026 micro-benchmarking oral used four benchmarks and ~400 models; LLMs Get Lost used 200k simulations. Our τ²-bench (3 domains, 4 models, 4,448 runs) plus SWE-bench Lite (300 tasks, 2 models) is adequate only if the analyses are decision-relevant and the replay is honestly labelled.
4. **"Missing statistical tests" turned against us.** A paper about statistical validity that reports Monte Carlo results without Monte Carlo standard errors, or compares power across different null hypotheses, will be caught.
5. **Overclaiming.** "First", "novel framework", "guarantees" without matching theorem scope. Reviewer 2 of Conformal Risk Control gave contribution 2 even to that paper; anticipate a reviewer who accepts the math and still scores contribution 2.
6. **Presentation.** Dense notation, many definitions before any example, guarantees stated at generality the experiments never use. The Reviewer Guide's "Be concise" applies to authors too: reviewers now are told to focus on decision-relevant points, so clarity of the main claim decides the score.
7. **Desk-rejection risks specific to 2027:** page overflow (strict 9 pages), missing AI-use statement, hallucinated references (the 2026 retrospective explicitly desk-rejected for these), anonymity leaks in appendix/code, no qualified reciprocal reviewer registered by the abstract deadline, incorrect OpenReview profile data.

Process findings to exploit (arXiv:2509.25701; arXiv:2511.15462): providing code/data is a strong acceptance signal; rebuttals that are timely, substantive and interactive move borderline scores (5->6, 6->8 in the old scale); only ~1% of scores go down.

---

## 6. Implications for our paper's design (assessment, not venue rules)

- Lead with the decision problem and the identification result (what paired shadow vs. single-exposure A/B identifies), not with the CS machinery. State one main theorem in the main text with a one-line procedure; put the mixture/betting proofs in the appendix and cite Howard et al. and Waudby-Smith & Ramdas for them.
- Spend at least half of the 9 pages on agent evidence: τ²-bench three domains, SWE-bench Lite, one prospective or clearly-labelled replay stream, with Type I error, power, stopping time, false-deployment probability, and Monte Carlo standard errors. Use the "population-priority obstruction" and "identification obstruction" examples as figures, not prose.
- Include the baselines reviewers will name: fixed-horizon Wilcoxon/GPC test, group-sequential WR (Bergemann & Hanson), betting CS on the bounded score, marginal guardrails, scalarized score, Pareto plot. Compare only under a shared target.
- Presentation: define the hierarchy with an agent example on page 2; every theorem gets a one-sentence "what this means for a deployment gate"; all clinical terminology appears once with an ML gloss.
- Reproducibility statement pointing to the source manifests (`work/empirical_sources/manifest.json`), seeds, judge versions; anonymous code link; retained licences (MIT for τ²-bench).
- AI-use statement enumerating every required-disclosure task actually performed and the human verification of proofs, code and citations.

---

## 7. Internal reviewer rubric (mirrors the ICLR form)

Use for every internal review round. Each review is written by one reviewer (human or agent) in the form below; the self-written core assessment must be produced before any LLM-assisted expansion and kept in the "LLM use" field, mirroring the 2027 reviewer policy. A machine-usable copy is in `reviews/rubric.md`.

### 7.1 Form fields (in order)

1. **Summary** - what the paper claims to contribute, in the reviewer's own words; state the main theorem(s) and main experiment(s) as the reviewer understood them. If the summary cannot be written in five sentences, record that as a presentation defect.
2. **Soundness (1-4)** - are the theoretical and empirical claims correct and rigorously supported?
3. **Presentation (1-4)** - clarity, organization, figures, notation, honesty of claims.
4. **Contribution (1-4)** - importance and novelty relative to the closest prior work, for the ICLR audience.
5. **Strengths** - bullet list, each tied to one of the four key questions.
6. **Weaknesses** - bullet list; each item must name the section/equation/figure, say why it affects the decision, and (if novelty) cite the closest prior work with the specific overlap.
7. **Questions** - things whose answers could change the score; each labelled with the score change it could cause.
8. **Flag for ethics review** - yes/no; if yes, which CoE topic (human subjects, data licence, conflict of interest, misrepresentation, undisclosed AI use).
9. **Rating (1-10)** - overall recommendation (semantics below).
10. **Confidence (1-5)**.
11. **Reproducibility check** - pass/fail on the checklist in 7.6.
12. **LLM use by the reviewer** - self-written core assessment, then a note on any LLM assistance.

### 7.2 Rating semantics (internal; task-specified 2025-style scale, with 2026 mapping)

| Internal | Meaning | 2026 form equivalent (assumed) |
|---|---|---|
| 1 | Strong reject: fundamental flaw (incorrect main theorem, invalid inference, fabricated/unsupported data) or out of scope. | 0 |
| 3 | Reject: not good enough; major unresolved soundness or novelty problem that a rebuttal cannot fix. | 2 |
| 5 | Marginally below threshold: sound but contribution or evidence insufficient; would need new experiments or a reframed contribution. | 4 |
| 6 | Marginally above threshold: accept if the identified fixes are made in rebuttal; no fatal issue. | 6 |
| 8 | Accept, good paper: clear contribution, correct, convincing experiments, well written. | 8 |
| 10 | Strong accept: should be highlighted; would defend as an oral. | 10 |

Decision calibration from Sec. 2: an internal round is "ready" only when all internal reviewers give >= 6 and the mean is >= 6.5, which corresponds to a >= 0.94 (2025) / 0.97 (2026) empirical acceptance rate. A single 5 must be resolved by a concrete change, not argued away.

### 7.3 Soundness / Presentation / Contribution (1-4)

1 = poor, 2 = fair, 3 = good, 4 = excellent (label wording assumed; values verified). Anchors:

- **Soundness 4**: every theorem checked line by line by the reviewer, assumptions match the experiments, error control verified numerically with Monte Carlo SEs, baselines compared under the same null. **3**: minor gaps (a constant, a missing regularity condition) with no effect on conclusions. **2**: a claim is stated more generally than proved, or an experiment cannot support the stated conclusion (e.g., replay described as live A/B). **1**: a main result is wrong or the inference is invalid (e.g., optional stopping without a time-uniform guarantee; reused trajectories counted as independent).
- **Presentation 4**: main claim, hierarchy example and decision rule understood by page 2; each theorem has a plain-language consequence; figures readable in grayscale; no undefined notation. **3**: readable with effort. **2**: key definitions buried, clinical jargon without ML gloss, results only in tables. **1**: a competent ML reviewer cannot reconstruct the method from the main text.
- **Contribution 4**: changes how practitioners will compare agents or gate deployments, with a result not implied by Buyse/Pocock + Howard/Waudby-Smith + Karampatziakis. **3**: clear, useful, agent-specific advance beyond the closest prior work. **2**: correct application of known tools with modest new insight. **1**: restates known results.

### 7.4 Confidence (1-5)

5 = checked all proofs and re-ran or inspected the code/data; 4 = checked the main proofs and read the appendix; 3 = read the paper carefully but did not verify proofs or code; 2 = outside expertise on some part; 1 = educated guess.

### 7.5 Concrete checks (each answered yes/no with a pointer)

**Novelty vs prior work**
- Does the paper name the closest result for each theorem (Even & Josse; Zhang & Wu; Bergemann & Hanson; Cai, Hu & Li; Howard et al.; Waudby-Smith & Ramdas; Karampatziakis et al.; Fang et al.; Real-POCQi; MAPS-LLM) and state precisely what differs?
- Is any "first"/"novel" claim narrower than the cited prior art permits? Flag each unsupported "first".
- Would the paper survive if the CS/betting proofs were replaced by citations? If yes, is the remaining contribution (identification result, protocol, empirical findings) stated as the contribution?
- Is contemporaneous work (published in the two months before the deadline) treated per the ICLR rule (cite if known; comparison not required)?

**Theorem correctness**
- Are pairing, assignment, outcome horizon, tie thresholds and eligibility fixed before outcomes (predictability)? Is the filtration explicit?
- Do randomization probabilities condition on pair context and potential outcomes, not just marginally?
- Are score bounds predictable (no post hoc range narrowing under adaptive orientation)?
- Does each error-control statement name the exact event (union null vs simultaneous coverage; stationary vs drift)? Is alpha allocation stated and used identically in code?
- Are betting/grid power claims limited to what is proved (finite grid: validity only)?
- Do delayed-outcome and missing-outcome rules preserve the stated coverage event, and are excluded runs (timeouts) declared as outcomes?
- Is the independent unit (task, pair, stratum) the same in theorem, variance estimate and experiment? Are within-task cross-comparisons never counted as independent?
- Does at least one internal reviewer re-derive each main-text theorem and record the check?

**Experimental rigor**
- Type I error / coverage at nominal alpha, with Monte Carlo standard errors and number of replications stated, including no-effect and harmful-primary-outcome cases.
- Power, expected stopping time, false-deployment probability and abstention reported for every method under a shared null/target; no comparison across different hypotheses.
- Baselines present: fixed-horizon GPC/Wilcoxon, group-sequential WR, betting CS, marginal guardrails, scalarized composite, Pareto summary.
- Real agent data: at least two workflow families with genuine agent outputs; task pairing preserved; clusters respected; benchmark version dependence (τ³ task fixes) disclosed; historical costs labelled as historical.
- Online claims: prospective randomized stream or explicitly labelled replay; no "live A/B" wording for replay.
- Sensitivity: hierarchy order, tie thresholds, grading noise, workload shift; prespecified vs exploratory analyses labelled.
- Every figure's uncertainty is defined (what interval, what unit, what replication count).

**Reproducibility**
- Anonymous code link or supplementary zip; seeds; model snapshots/versions; judge versions; outcome definitions; data manifests with hashes and source URLs; licences retained; exact boundary/stake/alpha settings used in reported numbers match the code.
- Reproducibility statement present and pointing to the above; ethics statement covers data provenance and any vendor/conflict issues; AI-use statement lists every required-disclosure task with verification.

**Clarity**
- Main claim in one sentence on page 1; hierarchy example with agent metrics by page 2; each theorem followed by "operationally this means ...".
- Notation table; no symbol used before definition; clinical terms glossed once.
- 9 pages at submission; statements outside the limit; appendix cross-referenced.
- Abstract numbers match the tables.

**Community relevance**
- Every section speaks about agent systems, benchmarks or deployment gates; the motivation names a decision an ML practitioner makes (ship/hold, leaderboard ranking, budget).
- The paper answers reviewer question 4 explicitly: what new knowledge does the ICLR reader take away that Buyse + Howard do not already give?
- The paper connects to ICLR-recognized evaluation work (τ-bench, WildBench, micro-benchmarking, Noisy-but-Valid, LLMs Get Lost) and says what they lack that we provide.

### 7.6 Desk-rejection preflight (all must pass before any internal round is scored)

- Main text <= 9 pages with ICLR 2027 style; AI use statement present; anonymity in text, appendix, code and metadata; every reference verified to exist (title, venue, year, URL opened); no author on >20 papers; a qualified reciprocal reviewer registered; OpenReview profiles complete; dual-submission status clean.

---

## 8. Sources opened in this pass

Official: iclr.cc 2027 CallForPapers, AuthorGuidelines, ReviewerGuidelines, AIPolicyForAuthors, AIPolicyForReviewers, Dates, FAQ; iclr.cc 2026 ReviewerGuide; ICLR blog posts 2025-04-22 (2025 awards), 2026-04-23 (2026 awards), 2026-03-31 (2026 review retrospective), 2026-09-02 (2027 submission policies); ICLR 2027 style-file zip; proceedings.iclr.cc PDFs for Conformal Risk Control (2024), τ-bench (2025), LLMs Get Lost (2026); iclr.cc virtual pages 2025/28170, 2025/29940, 2026/10009147.
Papers: arXiv 2406.12045 (τ-bench abs), 2310.06770v3 (SWE-bench), 2412.18407v2 (Statistical Framework), 2510.08730v2 (Micro-benchmarking), 2601.20913 (Noisy but Valid), 2511.15462 (Insights from the ICLR peer review), 2509.25701 (What drives paper acceptance), 2510.13201v2 (Paper Copilot), 2605.25415 (LLM-as-a-Reviewer; confirms {1,3,5,6,8,10} for 2023/2025), 2512.17950 (reciprocal-nomination analysis; no form info); mlanthology ICLR 2026 page for the micro-benchmarking paper; NeurIPS 2026 workshop page "E-Values: From Statistics to ML".
Third-party data: Paper Copilot `paperlists` GitHub JSON dumps for ICLR 2024/2025/2026; papercopilot.com ICLR 2026 statistics page (19,814 submissions; mean rating 4.21); randomfeatures substack; 36kr article (2026 mean 4.20, max 8.5, 19,631 submissions per that article; the official retrospective says 19,525 valid). berenslab/iclr-dataset README (55,906 submissions 2017-2026; no scale info).
Blocked: openreview.net forums and api/api2 endpoints (human verification), so per-paper review text is UNVERIFIED.
