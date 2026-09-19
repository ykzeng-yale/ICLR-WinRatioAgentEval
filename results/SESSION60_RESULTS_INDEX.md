# Session 60 results index (aggregated; updated by the 30-minute coordination loop)

Last updated: 2026-09-19T09:20Z. Owner: session `iclr-winratioagentevals-60`. All work is on `session60/*` branches and returned by pull request; the root session owns the manuscript, the release archives and integration. No commercial or proprietary model was called by this session; all fresh executions use open-weight models only (EXPERIMENT_POLICY.md on main).

**How to read this index.** "Integrated" means the root session copied or re-derived the material into its own files and reviewed it; it never means a pull request was merged wholesale. Numbers marked *descriptive* are counts and means of retained records. Numbers marked *model-dependent* are owner intervals whose assumptions the designs do not establish; the root paper **excludes** them. Current root state: main `410b158` (Round 14: owner-report cleanup accepted and closed), validated technical release `45e8ee2`, root-reported readiness 90%, remaining items author-only.

## Deliverables and their disposition

| # | Deliverable | Where | Last delivery head | Root disposition |
|---|---|---|---|---|
| 1 | Library fix for issue #4 in `src/wincs.py` (exact boundary laws, shift-invariant certified bounds, hedged betting CS, robust inversion, zero-count endpoint normalization) | PR #5, `session60/wincs-fix` | 5e91fcd | Root verification is limited to the zero-count betting endpoint arithmetic (Round 12: 3,465 ternary and 1,911 Bernoulli endpoint cases). The generic projection and width methods of the library remain separately unapproved and excluded from the paper, and the root does not import this interval implementation. PR open, not merged. |
| 2 | Sequential all-pairs U-statistic reference baseline (issue #3) | PR #7, `session60/contrib` | 88d6434 (accepted subset from ac17f59) | **Integrated (subset) in Round 10; issue #3 closed.** The other material on the branch (decision evidence on archived trajectories, replay, positioning notes, issue #6 fixes) is delivered but not integrated. |
| 3 | Open-model coding stream (issues #1/#2) | PR #8, `session60/local-stream` | c1da1c3 (Round 10 repair); report corrections 01f2381 | **Observations integrated in Rounds 11-12 with the root's own running-conditional-mean analysis and a descriptive same-task comparison.** Owner intervals excluded. Round 12 report corrections accepted in Round 13. |
| 4 | Open-model tau2-bench airline collection (issues #1/#2) | PR #8, same branch | 55fb1e5 (owner handoff); report corrections 01f2381 | **Integrated in Round 12 as descriptive batch-collection results plus an optional observed-array replay illustration.** Owner intervals and sensitivity-derived decisions excluded. Round 12 report corrections accepted in Round 13. |
| 5 | Drift / treatment-by-time / unequal-law null panel (issue #9) | PR #10, `session60/drift-panel` | e0f7dab (accepted files from ae3f0a5) | **Integrated in Round 10 (byte-for-byte reproduction); issue #9 closed.** |
| 6 | Round 13 owner-document cleanup (optional precision items) | PR #8 | be4b8e4 | **Accepted and closed by the root in Round 14** (both generators and manifests reproduced exactly); no effect on the paper. |

Issues #1 and #2 were **closed by the root on 2026-09-19 with an explicitly narrowed acceptance**: delivered collections and reviewed root analyses; broader confirmatory, live randomized-exposure and second-party / other-hardware replication ambitions are deferred optional extensions. The branch `session60/local-stream` follows main by merge commits (never rebased), so every recorded freeze and delivery commit stays reachable.

## Open-model coding stream

Design frozen at d9793d5; Qwen2.5-Coder-7B-Instruct 4-bit served locally; 591 MBPP-sanitized + HumanEval tasks; A single-shot versus B self-test-and-repair; 1,182 episodes, all retained.

Current owner report: `results/local_stream/report_v5.md` (= `report_v4.md` with one pointer corrected; v4 is the version the root reviewed). Governing wording: `experiments/local_stream/protocol_addendum_round12.md`. Superseded and preserved: `report_v3.md`, `v2_pre_round10/`, `v1_pre_round9/`. Data: `episodes.jsonl`, `monitor_pass1.csv`, `summary_v3.json`, `e2_cluster_v3.csv`, `pass_effects_v3.csv`, `data_manifest.json`, `release_anon/`. Figure: `figures_v3/fig2_running_nb.png`.

- *Descriptive.* Pre-registered H1 (B has higher success) is **not supported**: 433/591 successes in both arms (40 B-only, 40 A-only). B used 4.46x the latency (12.48 s versus 2.80 s), 4.46x the completion tokens, 7.4x the prompt tokens and 1,748 versus 591 model calls. Cross-arrival replay over 295 prespecified pairs: 69 wins / 18 ties / 208 losses, net benefit -0.471. Same-task net benefit -0.657.
- *Post hoc, conditional-mean reading (the kind of analysis the root retains, in its own implementation).* 95% normal-mixture band for the running conditional mean given the full frozen schedule: [-0.654, -0.288], below 0 from pair 60. This normal-mixture running-mean analysis and its pair-60 crossing are what the root retains. The harm e-process reading above threshold at pair 24 is **descriptive** under this reading; its anytime guarantee holds only under the iid-roster model (R2), which is excluded from the paper. Label of that reading: composite harm signal for B, incumbent A retained. The success guardrail of 0.03 is **not certified** by any interval or e-process.
- *Model-dependent owner intervals, excluded from the paper.* Betting CS under an iid-roster model [-0.628, -0.288]; task-level t [-0.705, -0.608]; cluster-robust t over 296 orientation-pair clusters [-0.7055, -0.6076] (needs cluster-level CLT conditions); exact cluster Hoeffding [-0.8145, -0.4986] (needs independent clusters).

## Open-model tau2-bench airline collection

A = Qwen2.5-7B-Instruct, B = Qwen3-4B-Instruct-2507, user simulator Qwen2.5-7B in both arms; llama.cpp; tasks 1-49 x 2 trials x 2 arms = 196 units; design frozen at 696fe57. Evidence type: **prospectively specified batch collection (all A, then all B) with a prespecified replay analysis**; shared trial seeds; one documented post-freeze operational amendment (deviation 1 with erratum). Not a live randomized exposure.

Current owner report: `results/tau2_open/report_final_v3.md` (= `report_final_v2.md`, the version the root reviewed, with nine precision replacements). Governing wording: `experiments/tau2_open/protocol_addendum_round12.md` and `protocol_addendum_round13.md`. Superseded and preserved: `report_final.md`, `report.md`. Data and accounting: `raw_gz/`, `episodes.csv`, `run_manifest.json`, `all_attempt_accounting.{md,csv}`, `unit_policy_flags.csv`, `round10_handoff_numbers.json`, `analysis_consistency_check*.json`, `release_anon/` (the deposited arm-A `logs_gz` and `raw_gz` archives contain account paths; an anonymous package must use `release_anon/`).

- *Descriptive.* 196 canonical units: 194 saved trajectories and 2 infrastructure placeholders scored as failures. 15/98 successes in each arm. Replay over 49 prespecified pairs: 10 wins / 30 ties / 9 losses, net benefit 0.020. Same-task: 28 / 141 / 27 over 196 comparisons, net benefit 0.005. Mean assistant tool calls 5.3 (B) versus 10.0 (A); mean agent generation time 84 s versus 128 s. No significance claim. 206 attempts, 12 discarded (all in the A collection); canonical totals omit at least 246,284 A-collection generated tokens (root reconstruction; role split unavailable). Equal observed success is not equivalence and not non-inferiority.
- *Optional observed-array replay illustration.* Conditional on the full retained array and the matching, under nominal independent fair replay coins: marginal 95% band [-0.609, 0.650] beside the known target 0.0102; final errors 0.010204 (net benefit) and 0.020408 (success difference). Marginal, not joint. No new-task, fresh-run or production inference.
- *Replay of the prespecified monitoring rule.* No e-process moved; abstention on the primary-rule comparisons.
- *Model-dependent owner intervals and sensitivity decisions, excluded from the paper.* Betting CS [-0.366, 0.406]; task-clustered t intervals; win-ratio CS; Welch intervals; hierarchy / tolerance, infrastructure-exclusion and omit-five sensitivities.
- *Unverified.* The actual sampler receipt inside the servers, an immutable decision chronology for deviation 1, complete failed-attempt usage.

## CPU-only studies

**U-statistic reference baseline (integrated subset).** `evidence/ustat_reference_report.md`, `results/ustat_reference/`. 8 scenarios x 2,000 replicates; 4 boundary nulls x 10,000. Asymptotic relative efficiency of all-pairs over disjoint pairs 1.13-1.41 for net benefit and 1.0 for the component gates. Monte Carlo false-rejection rates at the compliance-gate boundary: projection-Gaussian component rule 7.25% [6.76, 7.77]; simultaneous guarded deployment 1.83%; retained-crossing convention 7.11% (three distinct events); exact betting rule 0.76%.

**Drift / unequal-law null panel (integrated).** `evidence/drift_panel_report.md`, `results/drift_panel/`; protocol sha256 bb497cbb... 12 scenarios x 9 rules. Guarded betting ever-false-deployment under common drift 0.55% [0.42, 0.72] at the identical null and 0.38% at each guardrail boundary; repeated Wald 27-31%. Limitation: the normal-mixture rules never deploy in the alternating-component cells, so the alpha split is not demonstrated empirically there.

**Decision evidence on archived public trajectories (delivered on PR #7, not integrated).** `results/benchmarks/decision_matrix.csv`, `tau2_contrasts.csv`, `label_noise_sensitivity.csv`, `results/replay/`. 25 ordered contrasts; the compared rules disagree on 19; 9 priority inversions. These use archived third-party model outputs, not fresh executions, and their intervals carry the same model-dependence caveats as above.

## Open requests

None from the root. Root-side open items: disposition of PR #5 and of the non-integrated parts of PR #7 and PR #8 (no whole-PR approval is implied by any integration). Author-only items, which no agent can do: abstract submission on OpenReview (deadline 2026-09-18 23:59 AoE = 2026-09-19 11:59 UTC = 07:59 EDT), OpenReview profile and reciprocal-review eligibility, human scientific review, AI-use disclosure, originality and concurrent-submission declarations.
