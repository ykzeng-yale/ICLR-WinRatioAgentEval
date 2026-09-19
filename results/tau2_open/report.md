# tau2 open-model stream: analysis report (skeleton)

Generated 2026-09-19T05:01:30Z from `results/tau2_open`. Scores are B (agent qwen3-4b-instruct-2507) vs A (agent qwen2.5-7b-instruct); user simulator qwen2.5-7b-instruct for both. Fill the interpretation after the frozen analysis; do not edit numbers by hand.

## Accounting

- Episodes: 196; arms: {'A': 98, 'B': 98}; dry_run=False
- Failure accounting: {"A": {"n": 98, "success": 15, "max_steps": 27, "errors": 16, "termination_reasons": {"user_stop": 55, "too_many_errors": 14, "infrastructure_error": 2, "max_steps": 27}, "tokens_estimated_episodes": 0, "tokens_estimated_calls": 0, "zero_tool_call_episodes": 2, "served_models": ["qwen2.5-7b-instruct"], "duration_total_s": 15851.15660412237}, "B": {"n": 98, "success": 15, "max_steps": 29, "errors": 0, "termination_reasons": {"user_stop": 69, "max_steps": 29}, "tokens_estimated_episodes": 0, "tokens_estimated_calls": 0, "zero_tool_call_episodes": 1, "served_models": ["qwen3-4b-instruct-2507"], "duration_total_s": 12096.15234420728}}

## (a) Online cross-arrival design (prespecified pass-1 pairs)

- Pairs: 49; NB=0.0204, NB CS=[-0.3660352820036362, 0.40631790063819107]; WR=1.1111, WR CS=[0.0070957024535648425, None]
- Success diff (B-A) = 0.0204, CS [-0.3660352820036362, 0.40631790063819107]; guarded decision: inconclusive; first deploy index: None; first harm index: None
- Tier decomposition: {"success": {"wins": 10, "losses": 9, "contribution": 0.02040816326530612}, "agent_tokens_completion": {"wins": 0, "losses": 0, "contribution": 0.0}, "n_assistant_tool_calls": {"wins": 0, "losses": 0, "contribution": 0.0}}
- Tier decomposition: success tier determines the sign of NB (H3): True
- Block-1 subset (pairs with both arrivals in block 1 = pairs 1-24, distinct tasks; 24 pairs): NB=0.0833 CS=[-0.6451344949503739, 0.8115299791097641] guarded=inconclusive

## (b) Same-task shadow design

- Tasks: 49; NB=0.0051 CI=[-0.1107687809027074, 0.12097286253536048]; WR=1.0370 CI=[0.4544472559362854, 2.366492045310836]; decision: inconclusive; replicate-identical fraction: {'A': 0.0, 'B': 0.0}
- Pairing sensitivity (NB, CI): {"all": [0.0051, [-0.1107687809027074, 0.12097286253536048]], "offdiagonal": [0.0, [-0.11353902458559234, 0.11353902458559234]], "diagonal": [0.0102, [-0.1123963220854153, 0.13280448535072142]]}

## (c) Component effects (B - A)

| component | same-task mean diff | CI | cross-arrival diff | CI |
|---|---|---|---|---|
| success | 0.0000 | [-0.1135, 0.1135] | 0.0204 | [-0.1397, 0.1805] |
| agent_tokens_completion | -261.7449 | [-881.9539, 358.4641] | -906.3265 | [-1654.5921, -158.0610] |
| agent_tokens_prompt | -12995.9184 | [-69131.6462, 43139.8094] | -68683.4082 | [-139158.5346, 1791.7183] |
| n_assistant_tool_calls | -4.6837 | [-6.8688, -2.4986] | -5.9184 | [-9.0397, -2.7970] |
| n_agent_llm_calls | -2.2653 | [-7.9529, 3.4222] | -7.4898 | [-14.3060, -0.6736] |
| duration | -38.3164 | [-77.0970, 0.4643] | -78.8610 | [-128.5687, -29.1533] |
| agent_generation_seconds | -44.1037 | [-75.2993, -12.9082] | -62.7207 | [-96.8774, -28.5641] |

## (d) Decision rules

| rule | data | estimate | CI | decision |
|---|---|---|---|---|
| success_only | shadow | 0.0000 | [-0.1135, 0.1135] | none |
| pareto_means | shadow | NA | NA | B |
| utility_w=1.00/0.00/0.00 | shadow | 0.0000 | NA | none |
| utility_w=0.80/0.10/0.10 | shadow | 0.0572 | NA | B |
| utility_w=0.60/0.20/0.20 | shadow | 0.1144 | NA | B |
| utility_w=0.50/0.25/0.25 | shadow | 0.1430 | NA | B |
| utility_w=0.34/0.33/0.33 | shadow | 0.1887 | NA | B |
| utility_w=0.20/0.40/0.40 | shadow | 0.2287 | NA | B |
| hierarchical_nb | shadow | 0.0051 | [-0.1108, 0.1210] | none |
| guarded_hierarchical | shadow | 0.0051 | [-0.1108, 0.1210] | none |
| conjunction_all_components | shadow | NA | NA | none |
| hierarchical_nb_betting_cs | online | 0.0204 | [-0.3660, 0.4063] | none |
| guarded_anytime | online | 0.0204 | [-0.3660, 0.4063] | none |
| success_only_betting_cs | online | 0.0204 | [-0.3660, 0.4063] | none |

## (e) Sensitivity (tolerance x tier order; H4 = token-first row with eligibility "none")

| tol | order | eligibility | shadow NB [CI] | shadow dec | online NB [CS] | online guarded |
|---|---|---|---|---|---|---|
| 0.0 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.0 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.0 | success>duration>agent_tokens_completion | absorbing | 0.0153 [-0.1005, 0.1311] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.0 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.1327 [-0.0823, 0.3476] | inconclusive | 0.3469 [-0.1617, 0.7974] | inconclusive |
| 0.0 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.1837 [-0.0230, 0.3903] | inconclusive | 0.4286 [-0.0764, 0.8646] | inconclusive |
| 0.05 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.05 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.05 | success>duration>agent_tokens_completion | absorbing | 0.0153 [-0.1005, 0.1311] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.05 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.1480 [-0.0654, 0.3613] | inconclusive | 0.3469 [-0.1617, 0.7974] | inconclusive |
| 0.05 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.1990 [-0.0099, 0.4078] | inconclusive | 0.4286 [-0.0764, 0.8646] | inconclusive |
| 0.1 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.1 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.1 | success>duration>agent_tokens_completion | absorbing | 0.0153 [-0.1005, 0.1311] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.1 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.1633 [-0.0494, 0.3760] | inconclusive | 0.3878 [-0.1195, 0.8311] | inconclusive |
| 0.1 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.2143 [0.0149, 0.4137] | B | 0.4694 [-0.0325, 0.8977] | inconclusive |
| 0.2 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.2 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0051 [-0.1108, 0.1210] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.2 | success>duration>agent_tokens_completion | absorbing | 0.0153 [-0.1005, 0.1311] | inconclusive | 0.0204 [-0.3660, 0.4063] | inconclusive |
| 0.2 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.1735 [-0.0416, 0.3885] | inconclusive | 0.3469 [-0.1617, 0.7974] | inconclusive |
| 0.2 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.2143 [0.0107, 0.4179] | B | 0.4694 [-0.0325, 0.8977] | inconclusive |

## Hypotheses (protocol.md section 1)

| hypothesis | pre-specified test | result |
|---|---|---|
| H1 success differs between arms (direction NOT pre-specified; deployment question: can candidate B replace incumbent A under the guarded rule?) | same-task success diff (B-A) CI excludes 0; guarded decision | CI [-0.1135, 0.1135]; guarded inconclusive |
| H2 B uses fewer agent completion tokens per episode | same-task token diff (B-A) CI < 0 | [-881.9539, 358.4641] |
| H3 the hierarchical decision is determined by success first | success-tier contribution has the sign of NB and dominates lower tiers (shadow, online) | shadow False; online True |
| H4 a token-first rule prefers B if H2 holds | sensitivity row tokens>success>calls (eligibility none) NB > 0 with CI/CS lower bound > 0 | see (e) |
| H5 absolute success levels not comparable to the paper's archived commercial-model runs (weaker user simulator) | success rates reported per arm, never compared with archived levels | {"A": 15, "B": 15} |

## Interpretation (to be written after unblinding; protocol.md section 12)

_pending_

## Deviations from protocol

_none recorded yet; see protocol.md deviations log_
