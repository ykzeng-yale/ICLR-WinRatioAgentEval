> **SUPERSEDED by [report_v3.md](report_v3.md) (Round 10).** The statements below that the E2 intervals need no assumptions or are conservative by construction, and the "design-based, no sampling assumption" wording of R1, are withdrawn; the numbers are unchanged. Original Round 9 bytes: `v2_pre_round10/report_v2.md`.

# Local-model prospective stream: report v2 (Round 9 re-analysis, POST HOC)

This report supersedes `v1_pre_round9/report.md` for every inferential statement. It was generated 2026-09-18T20:27:09Z by `experiments/local_stream/make_report_v2.py` from `summary_v2.json` (`analysis_v2.py`), which re-analyses the **unchanged** raw evidence (`episodes.jsonl`, `monitor_pass1.csv`, `monitor_state.json`, `design.json`, `run_manifest.json`; sha256 in `analysis_v2_manifest.json`). No episode was re-run and no model was called. The re-analysis is **post hoc**: it was specified in `experiments/local_stream/protocol_addendum_round9.md` after the outcomes were known, in response to the Round 9 audit of PR 8. The frozen `protocol.md` and `analysis.py` are untouched; the v1 outputs (uncorrected two-sided CS, uncorrected target wording) are preserved in `v1_pre_round9/`.

## 1. Summary

Two workflows on one local open-weight model (`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, served at `127.0.0.1`; no commercial or proprietary model call) were compared on a fixed roster of 591 tasks (427 MBPP-sanitized + 164 HumanEval): A `single_shot` versus B `self_test_repair`. All 1182 planned episodes were run and retained. **The preregistered primary hypothesis H1 (B has higher hidden-test success) is not supported, and this negative result is retained as is**: both arms succeeded on 433/591 tasks (40 B-only and 40 A-only successes). B used 2.96x the model calls, 7.42x the prompt tokens, 4.46x the completion tokens and 4.46x the mean workflow latency of A. Under the frozen hierarchy (success > latency at 10% tolerance > completion tokens, absorbing rule) the net benefit of B is negative on both prespecified contrasts: E1 cross-arrival NB = -0.471 (69 wins / 18 ties / 208 losses over 295 pairs) and E2 same-task NB = -0.657 (591 tasks).

Uncertainty for E1 is given under two explicitly separated readings (section 3): **R1**, design-based and conditional on the realized pairing, 95% normal-mixture CS for the running average of pair means [-0.654, -0.288], first entirely below 0 at pair 60; **R2**, under the unverifiable assumption that the roster is an iid sample of tasks, corrected 95% betting CS [-0.628, -0.288], first below 0 at pair 42. The online monitor outcome is a **composite harm signal for B; incumbent A retained** (harm e-process read above threshold at pair 24): an unfavourable result for B on the prespecified composite, driven by the latency tier; it is not a success-rate or safety harm and not a reverse guarded approval of A. The success guardrail was **not** certified online, and the same-task non-inferiority check passes by only 0.00025 under one approximation (section 5).

## 2. What changed relative to v1

| item | v1 (preserved in `v1_pre_round9/`) | v2 |
|---|---|---|
| two-sided betting CS | `max(K+, K-)` against `1/delta` (guarantee 2 delta) | hedged capital `(K+ + K-)/2` against `1/delta` (guarantee delta); `src/wincs.py` sha256 `6a6a0b51bf46d640` |
| E1 NB interval | [-0.6184, -0.3008] | R2 [-0.6281, -0.2880]; R1 [-0.6540, -0.2883] |
| E1 success-difference interval | [-0.0698, 0.1707] | R2 [-0.0786, 0.1794]; R1 [-0.1320, 0.2337] |
| E1 win-ratio interval (decided pairs) | [0.2083, 0.5141] | R2 [0.2010, 0.5299] (no R1 analogue is claimed) |
| first pair at which the NB interval is below 0 | 32 (uncorrected CS) | R2: 42 (stays below from pair 50); R1: 60 |
| target of E1 | "295 independent pairs", population guarantee asserted | R1: running average over the pairs actually formed (no sampling assumption); R2: theta_P under an iid-roster ASSUMPTION |
| monitor crossings | "valid decision after 24 independent pairs" | descriptive under R1; anytime guarantee only under R2 |
| label `B_harmful` | "B harmful" | "composite harm signal for B; incumbent A retained" |
| pass-1 component intervals | independent-arm Welch | pair-level differences (n = 295) |
| freeze wording | "before any model call" | "before any design-task outcome" (section 8) |
| resources | completion tokens and latency | prompt, completion and total tokens, model calls, latency per arm (section 6) |

Point estimates, tier decompositions, the e-process paths and the first-crossing indices are identical to v1 (asserted in `analysis_v2.py`); `task_scores.csv` and `episodes_flat.csv` do not depend on the CS and are unchanged. Regression check of the correction (`two_sided_cs_check.json`): for one fair +/-1 observation E max(K+, K-) = 1.06370423 > 1 while E (K+ + K-)/2 = 1.000000000000; simulated time-uniform miscoverage of the corrected CS over 2000 streams of length 2000 at delta = 0.05: 0.0100, 0.0105, 0.0100 (uncorrected max rule on the same streams: 0.0285, 0.0230, 0.0245).

## 3. E1: cross-arrival contrast (295 pass-1 pairs)

Sampling facts. The 591 tasks are a FIXED roster. The design (seed 20260918) drew one uniformly random permutation and independent Bernoulli(1/2) orientations for 295 disjoint consecutive pairs; one arrival (`mbpp/256`) is unpaired by design and enters E2 only. Each episode adds model-sampling randomness. Pass 1 was physically executed in the frozen arrival order, one exposure per arrival; execution never stopped at a crossing.

Counts: 69 B wins / 18 ties / 208 B losses; NB = -0.4712; WR = 0.332; success difference D = 0.0508 (A 0.715, B 0.766 in pass 1). Tier decomposition: success 67 wins / 52 losses (0.051); latency_s 2 wins / 156 losses (-0.522); completion_tokens 0 wins / 0 losses (0.000).

| reading | target | assumption | procedure | NB, 95% | first n with upper bound < 0 | success difference, 95% | gate (lower > -0.03) |
|---|---|---|---|---|---|---|---|
| **R1** design-based | running average mu_bar_n = (1/n) sum_k mu_k, mu_k = (1/2)[m(s_k,t_k) + m(t_k,s_k)], over the pairs actually formed | none beyond the design (conditional on the matching; pair scores independent, not identically distributed) | normal-mixture CS, V_n = n, rho = 100 (radius 0.1828 at n = 295) | [-0.6540, -0.2883] | 60 | [-0.1320, 0.2337] | not established |
| **R2** superpopulation | theta_P = E m(s,t) for s, t iid from P | **roster is an iid sample from a task distribution P (unverifiable for a curated benchmark)** | corrected hedged betting CS; decided-pair WR CS [0.2010, 0.5299] | [-0.6281, -0.2880] | 42 (stays below from 50) | [-0.0786, 0.1794] | not established (first n: none) |

Under R1, because the matching is uniformly random, E_design[mu_bar_n] equals the finite-roster cross-task target theta_N = (1/(N(N-1))) sum_{s != t} m(s,t); the CS statement is nevertheless about mu_bar_n conditional on the matching, and **no without-replacement martingale or CS for theta_N is claimed**. No running intersection is applied under R1 because its target moves with n. Proofs and definitions: `protocol_addendum_round9.md` section 3.

Monitor (one-sided e-processes of `winstats.betting_log_e_ternary`, alpha 0.05, threshold log 20 = 2.996, read from pair 20; numerically unaffected by the two-sided fix): harm first read above threshold at **pair 24** (log e 3.209; it was above threshold at pair 14, log e 3.107, inside the prespecified n < 20 blackout, which is not read); final log e: harm 32.94, win -0.904, gate 0.812 (maxima -0.125 and 0.812; neither crossed). No deploy crossing.

- Under **R1** these crossings are reported **descriptively**: the e-processes test the pointwise conditional null (harm: mu_k >= 0 for every realized pair), a stronger null than mu_bar_n >= 0 or theta_N >= 0.
- Under **R2** they have the stated anytime type-I guarantee at alpha for theta_P.
- Outcome label: **composite harm signal for B; incumbent A retained**. Unfavourable result for B on the prespecified COMPOSITE (driven by the latency tier); not a success-rate or safety harm, and not a reverse guarded approval of A: A is retained as the incumbent.
- The crossing is a recorded decision that could have been taken; the run was not stopped and nothing was deployed.

![fig1](figures_v2/fig1_monitoring.png)

*Figure 1. Log e-values of the win, guardrail (gate) and harm e-processes after each pass-1 pair (`monitor_pass1.csv`); dotted line log(1/alpha); shaded region n < 20 is not read. These one-sided paths are descriptive under R1 (fixed roster, conditional on the matching) and carry their anytime guarantee only under the R2 iid-roster assumption. The marked crossing is the composite harm signal for B (incumbent A retained), not a success-rate or safety harm.*

![fig2](figures_v2/fig2_running_nb.png)

*Figure 2. Running cross-arrival net benefit with (blue) the corrected 95% hedged betting CS, valid for theta_P under the R2 iid-roster assumption, and (green, dashed) the 95% normal-mixture CS for the running average mu_bar_n, valid under R1 with no sampling assumption; orange: same-task NB with its 95% task-level interval (section 4). Source: `running_cs_v2.csv`, `summary_v2.json`.*

Pass-1 component contrasts from pair-level differences d_k = X_B,k - X_A,k (n = 295; t interval, conservative for the average of pair means under R1, iid under R2):

| component | mean A | mean B | mean difference [95%] |
|---|---|---|---|
| success | 0.715 | 0.766 | 0.051 [-0.022, 0.124] |
| latency_s | 2.666 | 12.609 | 9.942 [8.936, 10.949] |
| completion_tokens | 66.769 | 317.715 | 250.946 [225.275, 276.616] |
| prompt_tokens | 117.169 | 877.658 | 760.488 [687.377, 833.599] |
| n_llm_calls | 1.000 | 2.912 | 1.912 [1.799, 2.024] |

## 4. E2: same-task shadow contrast (all 591 roster tasks, one A and one B episode each)

| scope | n tasks | p_win / p_tie / p_loss | NB [95% task-level t interval] | WR [95%] |
|---|---|---|---|---|
| pooled | 591 | 0.069 / 0.205 / 0.726 | -0.657 [-0.705, -0.608] | 0.096 [0.069, 0.132] |
| mbpp | 427 | 0.070 / 0.239 / 0.691 | -0.621 [-0.679, -0.562] | 0.102 [0.070, 0.148] |
| humaneval | 164 | 0.067 / 0.116 / 0.817 | -0.750 [-0.838, -0.662] | 0.082 [0.044, 0.153] |
| stratified, equal benchmark weight | 591 | 0.069 / 0.177 / 0.754 | -0.685 [-0.738, -0.633] | 0.091 [0.064, 0.130] |

Targets and status of the interval (both statements are kept):

- **Finite-roster target**: theta_roster = (1/N) sum_t E h(Y_B(t), Y_A(t)) over the 591 roster tasks; the only randomness is model sampling. The task-level variance estimator is **conservative** for it (Neyman-type): E[s^2/N] = Var(mean) + (1/(N(N-1))) sum_t (tau_t - tau_bar)^2, so between-task variation of the means inflates it. Interval [-0.7053, -0.6077] (normal approximation). Assumption-free fixed-n Hoeffding interval: [-0.7682, -0.5448].
- **Superpopulation target** (iid-roster model): the same interval [-0.7053, -0.6077] is the conventional task-clustered interval (one cluster = one task).

Tier contribution means: success 0.000, latency_s -0.655, completion_tokens -0.002. Same-task paired component differences (B - A, n = 591 tasks, t interval with the same two readings):

| component | mean A | mean B | mean difference [95%] | ratio of means |
|---|---|---|---|---|
| success | 0.733 | 0.733 | 0.000 [-0.030, 0.030] | 1.00 |
| latency_s | 2.800 | 12.476 | 9.676 [9.090, 10.262] | 4.46 |
| completion_tokens | 70.205 | 313.178 | 242.973 [228.506, 257.439] | 4.46 |
| prompt_tokens | 120.504 | 893.724 | 773.220 [723.452, 822.987] | 7.42 |
| n_llm_calls | 1.000 | 2.958 | 1.958 [1.878, 2.037] | 2.96 |

## 5. Guardrail precision, and E1 versus E2

- Same-task success difference 0.000 (40 B-only, 40 A-only successes), t interval [-0.0297, 0.0297]. Its lower end -0.029748506 clears the -0.03 margin by only **0.000251**, under that single fixed-time approximation. **This is not a robust non-inferiority result**: the assumption-free interval is [-0.112, 0.112]; the online gate e-process did not cross (final log e 0.812 against 2.996); and the online success-difference intervals reach -0.070 (v1, uncorrected CS), -0.079 (R2, corrected CS) and -0.132 (R1). The data do not certify a 3-percentage-point success guardrail online.
- E1 NB -0.4712 versus E2 NB -0.6565: difference 0.185. DESCRIPTIVE ONLY: different targets, shared episodes (pass-1 episodes enter both), different unit counts and exposure passes; no joint uncertainty is claimed for the difference. The tier and tie patterns that accompany the two numbers (v1 report section 6, unchanged counts) are descriptive context, not an established population difference or an efficiency comparison.

## 6. Resources per arm (recomputed from `episodes.jsonl`; `resources_v2.csv`)

| arm | episodes | successes | model calls | prompt tokens | completion tokens | total tokens | latency sum (s) | latency mean / median (s) | executions incl. hidden verifier | agent self-test executions |
|---|---|---|---|---|---|---|---|---|---|---|
| A `single_shot` | 591 | 433 | 591 | 71,218 | 41,491 | 112,709 | 1,654.6 | 2.7997 / 2.079 | 591 | 0 |
| B `self_test_repair` | 591 | 433 | 1,748 | 528,191 | 185,088 | 713,279 | 7,373.4 | 12.4761 / 10.131 | 1,748 | 1,157 |
| total | 1182 | | 2,339 | 599,409 | 226,579 | 825,988 | | | | |

B/A ratios: model calls 2.96, prompt tokens 7.42, completion tokens 4.46, total tokens 6.33, mean latency 4.46. Completion tokens are **generation counts, not dollars, energy or total compute**; prompt tokens are shown because B consumes 7.4x as many. No token count is marked estimated. `n_executions` **includes the one hidden-verifier execution per episode**, whereas `latency_s` (model calls + the workflow's own self-tests) excludes hidden verification; verifier operations are not agent tool calls. Latency is single-host, sequential, local-server workflow latency on the recorded hardware, not queueing or production latency; these ratios are for this run only.

## 7. Decision rules and sensitivity (corrected CS; `decision_rules_v2.csv`, `sensitivity_v2.csv`)

| rule | data | reading | estimate | 95% interval | outcome |
|---|---|---|---|---|---|
| success_only | shadow | E2 (finite-roster conservative / superpopulation) | 0.000 | [-0.030, 0.030] | none |
| pareto_means | shadow | E2 (finite-roster conservative / superpopulation) | - | - | A |
| utility_w=1.00/0.00/0.00 | shadow | E2 (finite-roster conservative / superpopulation) | 0.000 | - | none |
| utility_w=0.80/0.10/0.10 | shadow | E2 (finite-roster conservative / superpopulation) | -0.692 | - | A |
| utility_w=0.60/0.20/0.20 | shadow | E2 (finite-roster conservative / superpopulation) | -1.383 | - | A |
| utility_w=0.50/0.25/0.25 | shadow | E2 (finite-roster conservative / superpopulation) | -1.729 | - | A |
| utility_w=0.34/0.33/0.33 | shadow | E2 (finite-roster conservative / superpopulation) | -2.283 | - | A |
| utility_w=0.20/0.40/0.40 | shadow | E2 (finite-roster conservative / superpopulation) | -2.767 | - | A |
| hierarchical_nb | shadow | E2 (finite-roster conservative / superpopulation) | -0.657 | [-0.705, -0.608] | A |
| guarded_hierarchical | shadow | E2 (finite-roster conservative / superpopulation) | -0.657 | [-0.705, -0.608] | A |
| conjunction_all_components | shadow | E2 (finite-roster conservative / superpopulation) | - | - | none |
| hierarchical_nb_betting_cs | online | R2 (iid-roster assumption) | -0.471 | [-0.628, -0.288] | A |
| guarded_anytime | online | R2 (iid-roster assumption) | -0.471 | [-0.628, -0.288] | retain A |
| success_only_betting_cs | online | R2 (iid-roster assumption) | 0.051 | [-0.079, 0.179] | none |
| hierarchical_nb_normal_mixture_cs | online | R1 (design-based, running average mu_bar_n) | -0.471 | [-0.654, -0.288] | A |
| success_only_normal_mixture_cs | online | R1 (design-based, running average) | 0.051 | [-0.132, 0.234] | none |

"A" in the outcome column means the rule's interval or point estimate favours A on that rule's own criterion; for `guarded_anytime` the outcome is "retain A" (composite harm signal), which is not a guarded approval of A. Success-only rules return no decision.

| tol | order | eligibility | E2 NB [95%] | E1 NB [R2 corrected CS] | online label |
|---|---|---|---|---|---|
| 0.0 | success > latency_s > completion_tokens | absorbing | -0.662 [-0.710, -0.613] | -0.475 [-0.631, -0.291] | composite harm signal for B; incumbent A retained |
| 0.0 | success > completion_tokens > latency_s | absorbing | -0.662 [-0.710, -0.613] | -0.475 [-0.631, -0.291] | composite harm signal for B; incumbent A retained |
| 0.0 | latency_s > success > completion_tokens | none | -0.997 [-1.003, -0.990] | -0.959 [-1.000, -0.871] | composite harm signal for B; incumbent A retained |
| 0.0 | completion_tokens > success > latency_s | none | -0.997 [-1.003, -0.990] | -0.959 [-1.000, -0.871] | composite harm signal for B; incumbent A retained |
| 0.1 | success > latency_s > completion_tokens | absorbing | -0.657 [-0.705, -0.608] | -0.471 [-0.628, -0.288] | composite harm signal for B; incumbent A retained |
| 0.1 | success > completion_tokens > latency_s | absorbing | -0.657 [-0.705, -0.608] | -0.471 [-0.628, -0.288] | composite harm signal for B; incumbent A retained |
| 0.1 | latency_s > success > completion_tokens | none | -0.992 [-1.000, -0.983] | -0.956 [-1.000, -0.867] | composite harm signal for B; incumbent A retained |
| 0.1 | completion_tokens > success > latency_s | none | -0.992 [-1.000, -0.983] | -0.956 [-1.000, -0.867] | composite harm signal for B; incumbent A retained |
| 0.2 | success > latency_s > completion_tokens | absorbing | -0.658 [-0.707, -0.610] | -0.461 [-0.618, -0.278] | composite harm signal for B; incumbent A retained |
| 0.2 | success > completion_tokens > latency_s | absorbing | -0.658 [-0.707, -0.610] | -0.461 [-0.618, -0.278] | composite harm signal for B; incumbent A retained |
| 0.2 | latency_s > success > completion_tokens | none | -0.992 [-0.999, -0.984] | -0.925 [-0.993, -0.824] | composite harm signal for B; incumbent A retained |
| 0.2 | completion_tokens > success > latency_s | none | -0.992 [-0.999, -0.984] | -0.919 [-0.988, -0.814] | composite harm signal for B; incumbent A retained |

## 8. Hypotheses, provenance and wording corrections

- **H1 not supported (retained negative result).** H2 (B costs more latency and tokens) supported. H3 (hierarchy prefers B) refuted on both contrasts. H4: resource-first orders also favour A; the predicted disagreement was not observed. H5: not robustly established (section 5). No new variants were run and none are proposed as a completion criterion.
- **Freeze wording.** The protocol and design were frozen **before any design-task outcome**, not "before any model call": smoke checks and the 6-task out-of-design timing pilot (full MBPP, disjoint from the design, never analysed) called the model earlier and are disclosed. This is a timestamped internal freeze, not an external registration.
- **Harness commits.** The run manifest and every episode record harness commit `526dff7b6d26f818964611b9ccbd8f61fae2e43c`; protocol section 16 names freeze commit `d9793d56430e65c600e241f325a7cd540d23a668`. Per the Round 9 audit's Git reconciliation, all 13 recorded file hashes match `526dff7b`, and at `d9793d5` only `protocol.md` differs (the other 12 files are identical); both commits precede the first episode. (This report did not run git; the reconciliation is the audit's, and it agrees with the per-file sha256 comparison in the v1 report section 10.)
- **Exposure.** Coding pass 1 is a physically executed, randomized, sequential laboratory stream with fresh generations; crossings are recorded, not acted on; there are no production users.
- **Data provenance** (`data_manifest.json`, checked by `verify_data_manifest.py --verify-pinned`): MBPP-sanitized pinned at `google-research/google-research@f82046ba5aab` (255053 bytes, sha256 `ca95deaa9a01ef0a`, CC-BY-4.0); HumanEval pinned at `openai/human-eval@463c980b59e8` (44877 bytes, sha256 `b796127e635a67f9`, MIT); full MBPP (timing pilot only) at `@f82046ba5aab` (563743 bytes, sha256 `ccf64ceae9c5403b`). Re-fetching the pinned URLs gave identical bytes (2026-09-18T20:27:08Z); the canonical task list rebuilds to sha256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`, the value stamped in `design.json`.
- **Anonymized release copies** of manifests/config/README/protocol with `<REPO>`, `<HOME>`, `<TMP>` placeholders and the sha256 of each original: `release_anon/` (`MAPPING.md`). Originals are not edited.
- Unchanged descriptive material (failure accounting, latency scope, tier/tie tables, requirement checklist) remains in `v1_pre_round9/report.md` sections 6, 7, 11; where that text says "independent pairs", "valid decision", "B harmful" or "Welch", read it with the corrections above. Scope limits are unchanged: one 7B 4-bit model, one machine, public benchmarks with likely training overlap; benchmark success is not exhaustive correctness.

## 9. Reproducibility

```
.venv/bin/python experiments/local_stream/run_v2_all.py            # regenerates every v2 output from the preserved raw files (about 4 min, CPU only, no model)
.venv/bin/python experiments/local_stream/run_v2_all.py --verify-pinned   # also re-fetches the pinned benchmark files into memory and compares bytes
```

Input, code and output hashes with timestamps: `analysis_v2_manifest.json`.
