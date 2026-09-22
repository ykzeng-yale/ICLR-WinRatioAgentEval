# Local stream: analysis report (skeleton)

> **MOCK DATA - DRY RUN.** These numbers come from the deterministic MockModel (`model=mock-deterministic-v1`). They test the pipeline only and must never be copied into the paper.

Generated 2026-09-18T14:54:26Z from `results/local_stream/dryrun`. Fill the interpretation sections after the frozen analysis; do not edit numbers by hand.

## Accounting

- Episodes: 24 (trial(s) [1]); dry_run=True; model=mock-deterministic-v1
- Failure accounting: {"single_shot": {"n": 12, "timed_out": 0, "sandbox_flag": 0, "api_error": 0, "empty_code": 0, "tokens_estimated": 0, "connection_retries": 0, "entry_point_missing": 0, "sentinel_missing_rc0": 0, "hack_flagged": 0, "hack_flagged_success": 0, "static_flagged": 0, "verify_seconds_mean": 0.015953947867577273}, "self_test_repair": {"n": 12, "timed_out": 0, "sandbox_flag": 0, "api_error": 0, "empty_code": 0, "tokens_estimated": 0, "connection_retries": 0, "entry_point_missing": 0, "sentinel_missing_rc0": 0, "hack_flagged": 0, "hack_flagged_success": 0, "static_flagged": 0, "verify_seconds_mean": 0.015653114377831418}}

## (a) Online cross-arrival design

- Pairs: 6; NB=0.1667, NB CS=[-1.0, 1.0]; WR=1.5000, WR CS=[0.0, None]
- Success diff (B-A) = 0.3333, CS [-1.0, 1.0]; guarded decision: inconclusive; first deploy index: None; first harm index: None
- Tier decomposition: {"success": {"wins": 3, "losses": 1, "contribution": 0.3333333333333333}, "latency_s": {"wins": 0, "losses": 1, "contribution": -0.16666666666666666}, "completion_tokens": {"wins": 0, "losses": 0, "contribution": 0.0}}

## (b) Same-task shadow design

- Tasks: 12; NB=0.0000 CI=[-0.6636219950149342, 0.6636219950149342]; WR=1.0000 CI=[0.2652071686227626, 3.7706371407419432]; decision: inconclusive
- By benchmark: {"mbpp": {"n_tasks": 7, "net_benefit": -0.1429, "nb_ci": [-1.1315588359487672, 0.8458445502344816]}, "humaneval": {"n_tasks": 5, "net_benefit": 0.2, "nb_ci": [-1.1601747613165112, 1.5601747613165116]}}

## (c) Component effects (B - A)

| component | same-task mean diff | CI | cross-arrival diff | CI |
|---|---|---|---|---|
| success | 0.2500 | [-0.3002, 0.8002] | 0.3333 | [-0.3310, 0.9976] |
| latency_s | 0.0382 | [0.0252, 0.0511] | 0.0417 | [0.0181, 0.0654] |
| completion_tokens | 71.7500 | [40.4879, 103.0121] | 58.1667 | [6.0343, 110.2990] |

## (d) Decision rules

| rule | data | estimate | CI | decision |
|---|---|---|---|---|
| success_only | shadow | 0.2500 | [-0.3002, 0.8002] | none |
| pareto_means | shadow | NA | NA | tradeoff |
| utility_w=1.00/0.00/0.00 | shadow | 0.2500 | NA | B |
| utility_w=0.80/0.10/0.10 | shadow | -31.9719 | NA | A |
| utility_w=0.60/0.20/0.20 | shadow | -64.1938 | NA | A |
| utility_w=0.50/0.25/0.25 | shadow | -80.3047 | NA | A |
| utility_w=0.34/0.33/0.33 | shadow | -106.0822 | NA | A |
| utility_w=0.20/0.40/0.40 | shadow | -128.6375 | NA | A |
| hierarchical_nb | shadow | 0.0000 | [-0.6636, 0.6636] | none |
| guarded_hierarchical | shadow | 0.0000 | [-0.6636, 0.6636] | none |
| conjunction_all_components | shadow | NA | NA | none |
| hierarchical_nb_betting_cs | online | 0.1667 | [-1.0000, 1.0000] | none |
| guarded_anytime | online | 0.1667 | [-1.0000, 1.0000] | none |
| success_only_betting_cs | online | 0.3333 | [-1.0000, 1.0000] | none |

## (e) Sensitivity (tolerance x tier order; H4 = resource-first rows with eligibility "none")

| tol | order | eligibility | shadow NB [CI] | shadow dec | online NB [CS] | online guarded |
|---|---|---|---|---|---|---|
| 0.0 | success>latency_s>completion_tokens | absorbing | 0.0000 [-0.6636, 0.6636] | inconclusive | 0.1667 [-1.0000, 1.0000] | inconclusive |
| 0.0 | success>completion_tokens>latency_s | absorbing | 0.0000 [-0.6636, 0.6636] | inconclusive | 0.1667 [-1.0000, 1.0000] | inconclusive |
| 0.0 | latency_s>success>completion_tokens | none | -1.0000 [-1.0000, -1.0000] | A | -1.0000 [-1.0000, 1.0000] | inconclusive |
| 0.0 | completion_tokens>success>latency_s | none | -0.8333 [-1.2002, -0.4665] | A | -0.6667 [-1.0000, 1.0000] | inconclusive |
| 0.1 | success>latency_s>completion_tokens | absorbing | 0.0000 [-0.6636, 0.6636] | inconclusive | 0.1667 [-1.0000, 1.0000] | inconclusive |
| 0.1 | success>completion_tokens>latency_s | absorbing | 0.0000 [-0.6636, 0.6636] | inconclusive | 0.1667 [-1.0000, 1.0000] | inconclusive |
| 0.1 | latency_s>success>completion_tokens | none | -1.0000 [-1.0000, -1.0000] | A | -1.0000 [-1.0000, 1.0000] | inconclusive |
| 0.1 | completion_tokens>success>latency_s | none | -0.8333 [-1.2002, -0.4665] | A | -0.6667 [-1.0000, 1.0000] | inconclusive |
| 0.2 | success>latency_s>completion_tokens | absorbing | 0.0000 [-0.6636, 0.6636] | inconclusive | 0.1667 [-1.0000, 1.0000] | inconclusive |
| 0.2 | success>completion_tokens>latency_s | absorbing | 0.0000 [-0.6636, 0.6636] | inconclusive | 0.1667 [-1.0000, 1.0000] | inconclusive |
| 0.2 | latency_s>success>completion_tokens | none | -1.0000 [-1.0000, -1.0000] | A | -1.0000 [-1.0000, 1.0000] | inconclusive |
| 0.2 | completion_tokens>success>latency_s | none | -1.0000 [-1.0000, -1.0000] | A | -1.0000 [-1.0000, 1.0000] | inconclusive |

## Interpretation (to be written after unblinding; see protocol.md section 12)

_pending_

## Deviations from protocol

_none recorded yet; see protocol.md deviations log_
