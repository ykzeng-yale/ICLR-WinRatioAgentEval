# Author handoff: ICLR 2027

**The updated review package is prepared; verified readiness remains 70%.** The project is not yet declared submission-ready. Actual abstract-submission status is unknown; this agent has neither submitted nor attested for you. Your supplied sole-author details remain in excluded local metadata; review artifacts are anonymous.

Round 11 adds independently reviewed open-weight coding observations: 1,182 episodes across 591 tasks. Each workflow succeeded on 433 tasks, while repair used 4.46 times the mean measured workflow latency and 6.33 times the total tokens. The retained post-hoc running-mean analysis is narrowly qualified; the same-task result is descriptive, the success guardrail is uncertified, and contributed E2/R2 uncertainty and endpoint routines are excluded. No new model calls occurred. Comparator/drift evidence and all original results remain preserved.

New airline results arrived at PR 8 head `3c70c3e` during this integration. The owner reports 196/196 completed units with 15/98 successes per arm. The deposit requires independent validation and repair of inference/deviation reporting before inclusion. It is not included in these archives. See the [current queue](../EXPERIMENT_QUEUE.md).

## Files to review and upload when finalized

- **paper.pdf**: official ICLR 2027 anonymous review format, 38 pages total, main content through page 9; full proofs, studies, limitations and disclosure statements included.
- **anonymous_code.zip**: 215 hashed payload files plus README/package manifest, including all accepted numerical results, protocols, analytical code and source provenance. Default verification checks 114 output hashes; `python reproduce.py --coding` rebuilds the new coding summaries from metrics without model or candidate-code execution.
- **latex_source.zip**: editable LaTeX with required figures/style files.
- **abstract.txt** and **form_draft.md**: genuine abstract and submission-form preparation materials.
- **requirements.md**: official rules, source links and author-only inputs.
- **package_manifest.json**: exact payload hashes.

The anonymous supplement deliberately omits candidate programs, self-tests and verifier stderr. It reproduces analysis of archived success labels, not model generations or independent hidden-test adjudication. Historical collection definitions are retained as nonexecuted text. Do not link the identifying public development repository in anonymous review materials.

Current SHA-256 identifiers:

- paper.pdf: `d471f6f01f52a565ef0387fe1fb6eb9a7e9275e2a0dc242ba1e522e907a19021`
- anonymous_code.zip: `624c1694574d21be534a1a5bfe5648893dc9aee2ab387e761a09ade54eff04e5`
- latex_source.zip: `2c6a64b28b1730d7b1daac4efb292d8b51abf915e07bf6c289ee23c0baca2088`

The exact release audit is `../reviews/round11_release_audit.md`; three independent coding evidence/target/integrated reviews and the integration ledger document scientific acceptance. All 38 PDF pages were rendered and visually inspected. The nine-page main-content boundary is unchanged. This remains an intermediate package while airline disposition and actual author review/declarations remain unresolved.

## Before you submit

1. Read the paper and independently check the scientific claims, citations, proofs and interpretations to the degree required for accepting authorship responsibility. The current AI-use statement explicitly does not assert that your verification is complete. Update that sentence only to reflect review you actually performed; retain the substantial-AI-use disclosure in both paper and submission form.
2. Verify your OpenReview profile using your institutional email, the final sole-author entry, and reciprocal-review eligibility. Eligibility is based on the venue's specified accepted-publication list. Affiliation or seniority alone does not establish it. If no author qualifies, inspect the official exemption and one-submission limit.
3. Confirm originality, concurrent-submission status and all live-form attestations yourself. No agent has attested or submitted on your behalf.
4. Submit the genuine abstract and final author set by the abstract deadline; then upload the paper and anonymous supplement by the full-paper deadline. Inspect the actual uploaded PDF and confirmation in OpenReview.

The [official author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines) and [call for papers](https://iclr.cc/Conferences/2027/CallForPapers) specify **September 18, 2026, 23:59 AoE** for the abstract and **September 25, 2026, 23:59 AoE** for the full paper and supplement. These correspond to **September 19 and September 26 at 07:59 EDT in New York**. Author additions/removals are locked after the abstract deadline. Verify the live form before entry; an older FAQ contains inconsistent timing.

## Cost and work available to other agents

All further commercial/proprietary-model experiment calls are now **prohibited by your explicit instruction**, including simulator, judge and fallback calls. The [current execution policy](../EXPERIMENT_POLICY.md) supersedes all earlier cheap-model budget allowances. Historical total accounted project cost is **USD 3.9476608**, including uncertain reservations; this is usage-based accounting rather than a reconciled provider invoice. No new spending or model calls occurred in the Round 9–11 audits.

Open-weight coding and the competitive sequential U-statistic reference have now been delivered in PRs 8 and 7; the interactive airline extension has now been delivered at `3c70c3e` and is pending independent acceptance. The [GitHub experiment queue](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/blob/main/EXPERIMENT_QUEUE.md) records independent audit findings and integration conditions. Existing workers retain ownership, use separate branches/worktrees and return reviewed pull requests. Generic contributed projections remain excluded from this frozen submission and do not affect its isolated reference results. Previously collected commercial observations are retained as historical evidence; their collection scripts are not authorized to run again.

## Optional ICLR automated feedback

ICLR's [official PAT announcement](https://blog.iclr.cc/2026/09/10/making-googles-paper-assistant-tool-pat-available-to-iclr-submitters/) offers free private automated feedback through September 18, 2026, 23:59 AoE. It requires a valid OpenReview account and an uploaded submission PDF, followed by the feedback checkbox on the submission form. Each author has one voucher and each paper may be processed once. Feedback is separate from conference peer review and can take up to 12 hours. No voucher has been used and no PDF has been submitted by this agent.
