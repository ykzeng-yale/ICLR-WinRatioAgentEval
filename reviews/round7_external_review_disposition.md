# Round 7: external positioning-review disposition

The incoming reviews at external commit `8c95ead` were assessed against root release `6dfc095`, rather than against the obsolete positioning memo that originally prompted them. A separate integrated reviewer found no new correctness defect in that release, but identified two surviving attribution gaps. Root addressed both and surfaced an already-executed comparator result. No external branch was checked out or merged.

## Verified source corrections

- **Wei-Jung Huang (2026), What Does an LLM-Agent Leaderboard Rank Actually Compare?** Version 1, September 7, 2026. The [original metadata](https://arxiv.org/abs/2609.07785v1) and [full text](https://arxiv.org/html/2609.07785v1), particularly Sections III and V-D, support attribution of estimand-aware pairwise conclusions and utility-sensitive agent selection. Current main credits this overlap and limits its additional focus to hierarchical contrasts, randomized observation, component constraints and partial-outcome monitoring. It does not claim to introduce target-dependent rankings.
- **Tudor Manole and Aaditya Ramdas (2023), Martingale Methods for Sequential Estimation of Convex Functionals and Divergences.** Version 4, March 12, 2023. The [metadata](https://arxiv.org/abs/2103.09267v4) and [Section 4.2](https://arxiv.org/html/2103.09267v4#S4.SS2) establish the reverse-martingale route to time-uniform inference for symmetric U-statistics. The bounded-kernel i.i.d. scope is explicit in the inserted sentence; the displayed generic construction is one-sample. No direct published theorem for our oriented two-arm statistic or universal efficiency superiority is asserted. A separate theory source report checks this distinction.
- **Mårten Schultzberg, Sebastian Ankargren and Mattias Frånberg (2024), Risk-aware product decisions in A/B tests with multiple metrics.** Version 1, February 18, 2024. The [metadata](https://arxiv.org/abs/2402.11609v1) and [Section 3](https://arxiv.org/html/2402.11609v1#S3) support explicit credit for combining superiority and noninferiority guardrails and the intersection–union error logic. Current main claims no novelty for this decision structure.

Primary HTML snapshots and hashes are retained in `work/round7_sources/manifest.json`. They were retrieved directly from arXiv. In identifier order above their SHA256 values are `74d4a73eb6336998529483ffd386bb20cf4a6621b8839997a5d652a5cd0e81df`, `ec22ab2f374c4608a969850f6bc228ef024b0d2c98130b8f97dda00a7c39eef4`, and `8909de6c5a90757cb691210cf1d6810d02b59f495975524daea7e4024899dbea`.

## Existing comparator disclosure

The archived `decision_ablation_results.csv` gives identical summaries for guarded win and guarded bounded-efficiency in two scenarios: 386/500 deployments and 4078.4 mean capped pairs under efficiency gain; 500/500 and 1485.0 under joint gain. The main text now states the parity and that these cases show no decision-speed advantage over that component-based rule. The result builder verifies the two reported equalities before emitting the prose. These are unchanged executed results for different deployment objectives, not a claim of universal equivalence or a substitute for issue 3's all-pairs study.

## Disposition of the remaining critiques

The incoming objections to drift error tending to one, headline sign flips, a theorem-forward multinomial construction, and unfinished ablations targeted obsolete development material. Those claims are absent from current main. The actual partial-trace audit, missing-pilot cohort accounting, and finite-sample scope remain explicitly delimited.

The alternate abstract's proposed all-pairs and additional conjunction comparisons were not integrated: its own provenance labels them unexecuted. Root retains the genuine, result-supported `submission/abstract.txt`. Larger prospective studies and further aligned comparators are useful extensions; no unexecuted result is credited to the paper. External issue 3 ownership and zero additional paid allocation were reiterated in the GitHub handoff.

All conclusions here are model-assisted internal checks. Human scientific review and author attestations remain outstanding.
