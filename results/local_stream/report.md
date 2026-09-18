# Local stream: analysis report (skeleton)

Generated 2026-09-18T17:38:20Z from `results/local_stream`. Fill the interpretation sections after the frozen analysis; do not edit numbers by hand.

## Accounting

- Episodes: 1182 (trial(s) [1]); dry_run=False; model=mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
- Failure accounting: {"single_shot": {"n": 591, "timed_out": 2, "sandbox_flag": 0, "api_error": 0, "empty_code": 0, "tokens_estimated": 0, "connection_retries": 0, "entry_point_missing": 1, "sentinel_missing_rc0": 0, "hack_flagged": 0, "hack_flagged_success": 0, "static_flagged": 0, "verify_seconds_mean": 0.05307188500727443}, "self_test_repair": {"n": 591, "timed_out": 0, "sandbox_flag": 0, "api_error": 0, "empty_code": 0, "tokens_estimated": 0, "connection_retries": 0, "entry_point_missing": 2, "sentinel_missing_rc0": 1, "hack_flagged": 0, "hack_flagged_success": 0, "static_flagged": 0, "verify_seconds_mean": 0.016365169032197917}}

## (a) Online cross-arrival design

- Pairs: 295; NB=-0.4712, NB CS=[-0.6183721923828126, -0.30083068847656247]; WR=0.3317, WR CS=[0.20827072520948756, 0.5140544898821995]
- Success diff (B-A) = 0.0508, CS [-0.06980529785156246, 0.1707092285156249]; guarded decision: B_harmful; first deploy index: None; first harm index: 24
- Tier decomposition: {"success": {"wins": 67, "losses": 52, "contribution": 0.05084745762711865}, "latency_s": {"wins": 2, "losses": 156, "contribution": -0.5220338983050847}, "completion_tokens": {"wins": 0, "losses": 0, "contribution": 0.0}}

## (b) Same-task shadow design

- Tasks: 591; NB=-0.6565 CI=[-0.7053137691326692, -0.607714995672745]; WR=0.0956 CI=[0.06930740294520975, 0.1317872827507351]; decision: A
- By benchmark: {"mbpp": {"n_tasks": 427, "net_benefit": -0.6206, "nb_ci": [-0.6790010903285494, -0.5622167082662982]}, "humaneval": {"n_tasks": 164, "net_benefit": -0.75, "nb_ci": [-0.8377162493703504, -0.6622837506296496]}}

## (c) Component effects (B - A)

| component | same-task mean diff | CI | cross-arrival diff | CI |
|---|---|---|---|---|
| success | 0.0000 | [-0.0297, 0.0297] | 0.0508 | [-0.0200, 0.1217] |
| latency_s | 9.6764 | [9.0904, 10.2625] | 9.9424 | [8.9473, 10.9375] |
| completion_tokens | 242.9729 | [228.5064, 257.4395] | 250.9458 | [225.6560, 276.2356] |

## (d) Decision rules

| rule | data | estimate | CI | decision |
|---|---|---|---|---|
| success_only | shadow | 0.0000 | [-0.0297, 0.0297] | none |
| pareto_means | shadow | NA | NA | A |
| utility_w=1.00/0.00/0.00 | shadow | 0.0000 | NA | none |
| utility_w=0.80/0.10/0.10 | shadow | -0.6917 | NA | A |
| utility_w=0.60/0.20/0.20 | shadow | -1.3834 | NA | A |
| utility_w=0.50/0.25/0.25 | shadow | -1.7293 | NA | A |
| utility_w=0.34/0.33/0.33 | shadow | -2.2827 | NA | A |
| utility_w=0.20/0.40/0.40 | shadow | -2.7669 | NA | A |
| hierarchical_nb | shadow | -0.6565 | [-0.7053, -0.6077] | A |
| guarded_hierarchical | shadow | -0.6565 | [-0.7053, -0.6077] | A |
| conjunction_all_components | shadow | NA | NA | none |
| hierarchical_nb_betting_cs | online | -0.4712 | [-0.6184, -0.3008] | A |
| guarded_anytime | online | -0.4712 | [-0.6184, -0.3008] | A |
| success_only_betting_cs | online | 0.0508 | [-0.0698, 0.1707] | none |

## (e) Sensitivity (tolerance x tier order; H4 = resource-first rows with eligibility "none")

| tol | order | eligibility | shadow NB [CI] | shadow dec | online NB [CS] | online guarded |
|---|---|---|---|---|---|---|
| 0.0 | success>latency_s>completion_tokens | absorbing | -0.6616 [-0.7103, -0.6129] | A | -0.4746 [-0.6217, -0.3041] | B_harmful |
| 0.0 | success>completion_tokens>latency_s | absorbing | -0.6616 [-0.7103, -0.6129] | A | -0.4746 [-0.6217, -0.3041] | B_harmful |
| 0.0 | latency_s>success>completion_tokens | none | -0.9966 [-1.0033, -0.9900] | A | -0.9593 [-1.0000, -0.8784] | B_harmful |
| 0.0 | completion_tokens>success>latency_s | none | -0.9966 [-1.0033, -0.9900] | A | -0.9593 [-1.0000, -0.8784] | B_harmful |
| 0.1 | success>latency_s>completion_tokens | absorbing | -0.6565 [-0.7053, -0.6077] | A | -0.4712 [-0.6184, -0.3008] | B_harmful |
| 0.1 | success>completion_tokens>latency_s | absorbing | -0.6565 [-0.7053, -0.6077] | A | -0.4712 [-0.6184, -0.3008] | B_harmful |
| 0.1 | latency_s>success>completion_tokens | none | -0.9915 [-1.0003, -0.9828] | A | -0.9559 [-1.0000, -0.8745] | B_harmful |
| 0.1 | completion_tokens>success>latency_s | none | -0.9915 [-1.0003, -0.9828] | A | -0.9559 [-1.0000, -0.8745] | B_harmful |
| 0.2 | success>latency_s>completion_tokens | absorbing | -0.6582 [-0.7067, -0.6097] | A | -0.4610 [-0.6085, -0.2911] | B_harmful |
| 0.2 | success>completion_tokens>latency_s | absorbing | -0.6582 [-0.7067, -0.6097] | A | -0.4610 [-0.6085, -0.2911] | B_harmful |
| 0.2 | latency_s>success>completion_tokens | none | -0.9915 [-0.9989, -0.9841] | A | -0.9254 [-0.9872, -0.8325] | B_harmful |
| 0.2 | completion_tokens>success>latency_s | none | -0.9915 [-0.9989, -0.9841] | A | -0.9186 [-0.9823, -0.8228] | B_harmful |

## Interpretation (to be written after unblinding; see protocol.md section 12)

_pending_

## Deviations from protocol

_none recorded yet; see protocol.md deviations log_
