# tau2 open-model stream: analysis report (skeleton)

> **MOCK DATA - DRY RUN.** These numbers come from the deterministic mock generator in `run_tau2_open.py --dry-run`. They test the pipeline only and must never be copied into the paper.

Generated 2026-09-18T16:56:41Z from `results/tau2_open/dryrun`. Scores are B (agent qwen3-4b-instruct-2507) vs A (agent qwen2.5-7b-instruct); user simulator qwen2.5-7b-instruct for both. Fill the interpretation after the frozen analysis; do not edit numbers by hand.

## Accounting

- Episodes: 196; arms: {'A': 98, 'B': 98}; dry_run=True
- Failure accounting: {"A": {"n": 98, "success": 29, "max_steps": 16, "errors": 0, "termination_reasons": {"user_stop": 82, "max_steps": 16}, "tokens_estimated_episodes": 0, "tokens_estimated_calls": 0, "zero_tool_call_episodes": 0, "served_models": ["qwen2.5-7b-instruct"], "duration_total_s": 16303.610803384963}, "B": {"n": 98, "success": 31, "max_steps": 11, "errors": 0, "termination_reasons": {"user_stop": 87, "max_steps": 11}, "tokens_estimated_episodes": 0, "tokens_estimated_calls": 0, "zero_tool_call_episodes": 6, "served_models": ["qwen3-4b-instruct-2507"], "duration_total_s": 16788.416727195086}}

## (a) Online cross-arrival design (prespecified pass-1 pairs)

- Pairs: 49; NB=0.0816, NB CS=[-0.28893188476562504, 0.44760925292968745]; WR=1.4000, WR CS=[0.25113351520485366, 20.48819945833584]
- Success diff (B-A) = 0.0612, CS [-0.288787841796875, 0.40968078613281234]; guarded decision: inconclusive; first deploy index: None; first harm index: None
- Tier decomposition: {"success": {"wins": 11, "losses": 8, "contribution": 0.061224489795918366}, "agent_tokens_completion": {"wins": 2, "losses": 2, "contribution": 0.0}, "n_assistant_tool_calls": {"wins": 1, "losses": 0, "contribution": 0.02040816326530612}}
- Tier decomposition: success tier determines the sign of NB (H3): True
- Block-1 subset (pairs with both arrivals in block 1 = pairs 1-24, distinct tasks; 24 pairs): NB=0.2500 CS=[-0.41897155761718763, 0.9097686767578127] guarded=inconclusive

## (b) Same-task shadow design

- Tasks: 49; NB=0.0204 CI=[-0.12383312815500042, 0.1646494546856127]; WR=1.0784 CI=[0.6319833175144534, 1.8402609579506264]; decision: inconclusive; replicate-identical fraction: {'A': 0.0, 'B': 0.0}
- Pairing sensitivity (NB, CI): {"all": [0.0204, [-0.12383312815500042, 0.1646494546856127]], "offdiagonal": [0.0306, [-0.1171577182631652, 0.17838220805908353]], "diagonal": [0.0102, [-0.1378030726332319, 0.15821123589853817]]}

## (c) Component effects (B - A)

| component | same-task mean diff | CI | cross-arrival diff | CI |
|---|---|---|---|---|
| success | 0.0204 | [-0.1231, 0.1639] | 0.0612 | [-0.1233, 0.2458] |
| agent_tokens_completion | -210.3673 | [-261.7026, -159.0321] | -233.4490 | [-306.7026, -160.1953] |
| agent_tokens_prompt | 1341.9592 | [-3090.2247, 5774.1431] | 409.1429 | [-5907.0588, 6725.3445] |
| n_assistant_tool_calls | -1.3673 | [-1.7919, -0.9427] | -1.4082 | [-2.0780, -0.7383] |
| n_agent_llm_calls | 0.2245 | [-0.5528, 1.0018] | 0.0612 | [-1.0383, 1.1608] |
| duration | 4.9470 | [-18.3901, 28.2841] | 2.6422 | [-26.9791, 32.2634] |
| agent_generation_seconds | 2.4712 | [-1.3039, 6.2463] | 2.7665 | [-2.8023, 8.3353] |

## (d) Decision rules

| rule | data | estimate | CI | decision |
|---|---|---|---|---|
| success_only | shadow | 0.0204 | [-0.1231, 0.1639] | none |
| pareto_means | shadow | NA | NA | B |
| utility_w=1.00/0.00/0.00 | shadow | 0.0204 | NA | B |
| utility_w=0.80/0.10/0.10 | shadow | 0.0853 | NA | B |
| utility_w=0.60/0.20/0.20 | shadow | 0.1503 | NA | B |
| utility_w=0.50/0.25/0.25 | shadow | 0.1827 | NA | B |
| utility_w=0.34/0.33/0.33 | shadow | 0.2347 | NA | B |
| utility_w=0.20/0.40/0.40 | shadow | 0.2801 | NA | B |
| hierarchical_nb | shadow | 0.0204 | [-0.1238, 0.1646] | none |
| guarded_hierarchical | shadow | 0.0204 | [-0.1238, 0.1646] | none |
| conjunction_all_components | shadow | NA | NA | none |
| hierarchical_nb_betting_cs | online | 0.0816 | [-0.2889, 0.4476] | none |
| guarded_anytime | online | 0.0816 | [-0.2889, 0.4476] | none |
| success_only_betting_cs | online | 0.0612 | [-0.2888, 0.4097] | none |

## (e) Sensitivity (tolerance x tier order; H4 = token-first row with eligibility "none")

| tol | order | eligibility | shadow NB [CI] | shadow dec | online NB [CS] | online guarded |
|---|---|---|---|---|---|---|
| 0.0 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0102 [-0.1341, 0.1545] | inconclusive | 0.0816 [-0.2889, 0.4476] | inconclusive |
| 0.0 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0306 [-0.1135, 0.1747] | inconclusive | 0.1224 [-0.2476, 0.4858] | inconclusive |
| 0.0 | success>duration>agent_tokens_completion | absorbing | 0.0408 [-0.1045, 0.1862] | inconclusive | 0.0408 [-0.3296, 0.4089] | inconclusive |
| 0.0 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.2755 [0.1044, 0.4466] | B | 0.4286 [-0.0384, 0.8279] | inconclusive |
| 0.0 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.5918 [0.4522, 0.7314] | B | 0.6735 [0.2396, 1.0000] | inconclusive |
| 0.05 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0204 [-0.1238, 0.1646] | inconclusive | 0.0816 [-0.2889, 0.4476] | inconclusive |
| 0.05 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0306 [-0.1135, 0.1747] | inconclusive | 0.1224 [-0.2476, 0.4858] | inconclusive |
| 0.05 | success>duration>agent_tokens_completion | absorbing | 0.0408 [-0.1045, 0.1862] | inconclusive | 0.0408 [-0.3296, 0.4089] | inconclusive |
| 0.05 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.3061 [0.1408, 0.4715] | B | 0.4286 [-0.0384, 0.8279] | inconclusive |
| 0.05 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.6327 [0.5162, 0.7491] | B | 0.6735 [0.2396, 1.0000] | inconclusive |
| 0.1 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0204 [-0.1238, 0.1646] | inconclusive | 0.1224 [-0.2476, 0.4858] | inconclusive |
| 0.1 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0306 [-0.1135, 0.1747] | inconclusive | 0.1224 [-0.2476, 0.4858] | inconclusive |
| 0.1 | success>duration>agent_tokens_completion | absorbing | 0.0408 [-0.1045, 0.1862] | inconclusive | 0.0408 [-0.3296, 0.4089] | inconclusive |
| 0.1 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.3061 [0.1408, 0.4715] | B | 0.4694 [0.0055, 0.8611] | inconclusive |
| 0.1 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.6122 [0.4904, 0.7341] | B | 0.7143 [0.2903, 1.0000] | inconclusive |
| 0.2 | success>agent_tokens_completion>n_assistant_tool_calls | absorbing | 0.0204 [-0.1238, 0.1646] | inconclusive | 0.1224 [-0.2476, 0.4858] | inconclusive |
| 0.2 | success>n_assistant_tool_calls>agent_tokens_completion | absorbing | 0.0306 [-0.1135, 0.1747] | inconclusive | 0.1224 [-0.2476, 0.4858] | inconclusive |
| 0.2 | success>duration>agent_tokens_completion | absorbing | 0.0561 [-0.0884, 0.2007] | inconclusive | 0.0612 [-0.3053, 0.4246] | inconclusive |
| 0.2 | success>agent_tokens_completion>n_assistant_tool_calls | none | 0.3163 [0.1468, 0.4859] | B | 0.4490 [-0.0119, 0.8419] | inconclusive |
| 0.2 | agent_tokens_completion>success>n_assistant_tool_calls | none | 0.5918 [0.4594, 0.7243] | B | 0.7755 [0.3770, 1.0000] | inconclusive |

## Hypotheses (protocol.md section 1)

| hypothesis | pre-specified test | result |
|---|---|---|
| H1 success differs between arms (direction NOT pre-specified; deployment question: can candidate B replace incumbent A under the guarded rule?) | same-task success diff (B-A) CI excludes 0; guarded decision | CI [-0.1231, 0.1639]; guarded inconclusive |
| H2 B uses fewer agent completion tokens per episode | same-task token diff (B-A) CI < 0 | [-261.7026, -159.0321] |
| H3 the hierarchical decision is determined by success first | success-tier contribution has the sign of NB and dominates lower tiers (shadow, online) | shadow True; online True |
| H4 a token-first rule prefers B if H2 holds | sensitivity row tokens>success>calls (eligibility none) NB > 0 with CI/CS lower bound > 0 | see (e) |
| H5 absolute success levels not comparable to the paper's archived commercial-model runs (weaker user simulator) | success rates reported per arm, never compared with archived levels | {"A": 29, "B": 31} |

## Interpretation (to be written after unblinding; protocol.md section 12)

_pending_

## Deviations from protocol

_none recorded yet; see protocol.md deviations log_
