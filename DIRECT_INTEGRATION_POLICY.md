# Direct integration to main

Effective September 19, 2026, following the author's instruction: **do not open new pull requests for this project.** Verified changes are committed directly to `main`. Review continues through exact commit links, issue comments and versioned review reports; the GitHub PR form is not a prerequisite.

## Commit identity

The author requests **Yukang Zeng <ykzeng2019@gmail.com>** for both Git author and committer identity in this project (September 20, 2026). Set repository-local `user.name` and `user.email` in each separately owned checkout and verify both identities before committing; do not add OpenAI/Codex co-author trailers. This concerns Git attribution, not removal of scientific AI-use disclosures. The authenticated GitHub account currently resolves to `ykzeng-yale`; a local Git identity setting does not rename that account. `.mailmap` canonicalizes the two existing historical identity forms in tools that honor mailmaps, without rewriting immutable commits, experiment pins or existing links. Original commit metadata remains intact.

## Coordination without conflicting writes

1. Each external worker keeps its named issue, exclusive directories and isolated working branch. Completed, checked work in those owned directories may be integrated directly into `main`, with the exact hash, changed paths, manifests and reproducible command posted in the issue. Branches and timestamp-anchor commits remain useful for unfinished work; they do not require pull requests.
2. Root reviews exact scientific deliveries read-only and alone integrates accepted evidence into the manuscript and release, with an explicit provenance/disposition record. Presence on `main` is not scientific acceptance. A whole-branch merge needs its complete delta checked for ownership and preserved evidence; previously excluded statistical methods do not become approved merely through a merge.
3. Coordinate main pushes through the issue and keep each session's checkout separate. Do not push overlapping changes simultaneously. Root owns shared status, manuscript and release files; contributors retain their named directories. Run `git pull --rebase origin main` before every main push; never force-push, reset another worker's state, delete source branches or overwrite frozen observations.
4. Scientific acceptance still requires the actual protocol, inference assumptions, provenance and reproduction checks. Contributor delivery, root acceptance, manuscript integration, release and human signoff remain separate states.
5. Continue issue #11 for the live study and project coordination; issue #12 for its CPU validation. External session `iclr-winratioagentevals-60` now claims both, with disclosed procedural rather than organizational independence. Root supplies a separate bounded acceptance review at the pinned commits. Post the live-study freeze bundle on its working branch for explicit pre-run review before any trial episode; elapsed time or absence of objection is not clearance.

## Legacy pull-request disposition

Another session merged all four legacy branches while root was checking them. GitHub recorded all four PRs as **MERGED** at 20:29:22 UTC on September 19, 2026; no PR remains open. Merge commits were #5 `d4338414cd92802401b0d7f545879b0ee68fb2a9`, #10 `cacb3bcd341ed264fc0def4253f718461dd97a87`, #7 `606915d9edbcd0bdade9be70e39f6db6391dc0bf`, and #8 `1c3e9f37fb0357a2eb7f501e734a67638984da96`. Root did not close or merge them. The original branches and review histories remain available. Their broader files are now on main, but scientific exclusions remain in force.

| Legacy PR | Exact observed head | Retained disposition |
|---|---|---|
| #5 | `5e91fcd9afe69a60d4376e5ac370e4865f099f57` | Generic projection/width methods remain excluded and separately unapproved. Issue #4 stays open. Later verified zero-count endpoint arithmetic is not whole-method approval. |
| #7 | `88d64343ab5b8a5448f3bd238d4befa54ee86acc` | Accepted 26-file U-statistic subset from `ac17f590` already integrated; unrelated replay/generic methods/drafts are excluded. Issue #6 stays open for its separate unaccepted work. |
| #8 | `ce8b5063d3bb579e1c605828ca07f0ff28d6c326` | Coding/airline observations accepted through root projections and scoped inference; report/index corrections closed through Round 15. Contributor intervals/generic methods remain excluded. |
| #10 | `e0f7dab374399bdb173f7a5f675347b11078f878` | Accepted 12-file drift-panel subset from `ae3f0a5` already integrated and independently reproduced. The broader merged branch receives no blanket scientific approval. |

Evidence: `reviews/round10_integration_disposition.md`, `reviews/round11_integration_ledger.md`, `reviews/round12_integration_ledger.md`, and `reviews/round15_integration_disposition.md`. Historical instructions to return a PR are superseded by this policy. Keep all old reports intact.

The merge audit verified the original paper, arXiv artifacts and accepted comparator/drift subsets were preserved. Broader repository code and three excluded CSVs did change, so main must not be described as identical to the frozen release. Use the versioned arXiv code archive for reproducing the manuscript. A separately documented pre-existing optional-runner dependency defect was repaired in that archive; see `reviews/arxiv_extension_dependency_audit.md`.

This is a repository-workflow change, not new scientific progress: full-project readiness remains 60%, existing bounded-v1 readiness 90%.
