# Local-model prospective stream: final report

Pre-registered experiment `experiments/local_stream/protocol.md` (frozen 2026-09-18 before any model call); run 2026-09-18 15:05:50Z to 17:37:01Z; analysis `analysis.py` output generated 2026-09-18T17:38:20Z. Every number below is copied from the files named in each table (`results/local_stream/`): `summary.json`, `decision_rules.csv`, `sensitivity.csv`, `task_scores.csv`, `episodes_flat.csv`, `monitor_pass1.csv`, `monitor_state.json`, `run_manifest.json`, `timing_pilot/summary.json`. Figures: `figures/` (made by `experiments/local_stream/make_figures.py` from the same files).

## 1. Summary

Two inexpensive coding workflows built on one local open-weight model (`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`) were compared on all 591 MBPP-sanitized and HumanEval tasks: A `single_shot` (one call) versus B `self_test_repair` (write code, write own asserts, execute, repair up to twice; at most 4 calls). The stream ran 1,182 episodes (2,339 model calls) in 2 h 32 min on one Apple M5 at zero API cost. The pre-registered primary hypothesis H1 (B has higher hidden-test success) was **not supported**: both variants succeeded on exactly 433/591 tasks (same-task success difference 0.000, 95% CI [-0.030, 0.030]; cross-arrival +0.051, betting CS [-0.070, 0.171]). H2 was supported: B took 4.46x the latency (+9.68 s per task, CI [9.09, 10.26]) and 4.46x the completion tokens (+243, CI [229, 257]). Under the frozen hierarchy (success > latency at 10% tolerance > completion tokens, absorbing rule), the net benefit of B is therefore negative on both pre-specified estimands: **E1 cross-arrival NB = -0.471** (betting CS [-0.618, -0.301], 295 independent pairs; WR 0.332, CS [0.208, 0.514]) and **E2 same-task NB = -0.657** (task-clustered CI [-0.705, -0.608], 591 tasks; WR 0.096, CI [0.069, 0.132]). The guarded anytime monitor never crossed the win or the success-guardrail e-process; the harm e-process crossed at pair 24, so the pre-specified online decision is **B_harmful** (retain A), and the fixed-horizon and shadow decisions are also A. All 14 decision rules and all 12 sensitivity rows that reach a decision choose A; the success-only rules return no decision. The two estimands differ by 0.19 for a structural reason (section 6): cross-task difficulty variation turns 40% of E1 pairs into success-tier decisions that are absent within task, where 66% of tasks are decided at the latency tier.

## 2. Design recap

- Protocol frozen 2026-09-18 before any model call; harness amended after the pre-registration audit, still before any design-task model call (deviations, section 10). Freeze record (protocol section 16): `design.json` sha256 `6175b81562efe1b1c87b113050f70c5daab2143e272cba39fb9a796f0d645457` (content-only `da84ff558deb2baf19d8728e3c50aea9e01e2411a5855cf07a2fac3594b8d4ad`), task-list sha256 `23727895971fa4a040198d8770173a4f0c3263a63a9cb1479abc4203bb01c2ce`, config sha256 `2dfb51966780698be326a8897c9e384a5513a7c1a47505c42b8a15c6c5baaf5b`, harness commit `d9793d56430e65c600e241f325a7cd540d23a668` (see section 10 on the commit id actually recorded by the run).
- Model snapshot revision `019cc73c45c770444708a6dd8690c66243cc5c80` (11 files, 4,295,890,004 bytes), served by `mlx_lm.server` 0.31.3 at `http://127.0.0.1:8080/v1`; the served model id was checked on the smoke completion and is identical on all 2,339 calls (`response_models`). Sampling temperature 0.7, top_p 0.95, max_tokens 1024; every call finished with `finish_reason = stop` (no truncation).
- Tasks: 427 MBPP-sanitized + 164 HumanEval = 591, no selection. Design seed 20260918 -> random arrival permutation -> 295 disjoint pass-1 pairs (arrivals 2k-1, 2k) with per-pair orientation R_k ~ Bernoulli(1/2) (realised: 127 pairs R=1, 168 pairs R=0); arrival 591 (`mbpp/256`) is unpaired and enters E2 only. Pass 1 (15:05:50Z to 16:21:35Z) exposed each arrival once to its pass-1 variant; pass 2 (16:21:35Z to 17:37:01Z) ran the complementary variant on every task. Single sequential stream, one episode at a time. Trial 2 was disabled in the frozen config and not run.
- Outcomes: success = hidden tests pass AND verifier sentinel printed; latency_s = model calls + the agent's own sandbox executions (excludes hidden-test verification, section 7); completion_tokens from server `usage`, summed over the episode's calls. Sandbox: macOS Seatbelt profile sha256 `6370c169267c3f31d3df6321b8acd6b3a363619634835c70854a9bf3952ed900`, RLIMIT_CPU 10 s, RLIMIT_NPROC 64, 10 s wall clock, recorded on every episode (`sandbox_kind = seatbelt` on all 1,182).

## 3. Results

### 3.1 E1: online cross-arrival contrast (295 pass-1 pairs; `summary.json` -> `online`, `monitor_pass1.csv`, `monitor_state.json`)

| quantity | estimate | 95% time-uniform CS |
|---|---|---|
| wins / ties / losses (B vs A) | 69 / 18 / 208 (p_win 0.234, p_tie 0.061, p_loss 0.705) | |
| net benefit NB | -0.471 | [-0.618, -0.301] |
| win ratio WR | 0.332 | [0.208, 0.514] (decided pairs) |
| win odds WO | 0.359 | |
| success difference D (B - A) | +0.051 (success A 0.715, B 0.766) | [-0.070, 0.171] |

Tier decomposition (contribution = (wins - losses)/295): success 67 wins / 52 losses (+0.051); latency 2 wins / 156 losses (-0.522); completion tokens 0 / 0 (0.000); ties 18 (17 both-failed, 1 within latency tolerance). Per-benchmark E1 (pairs whose two arrivals share a benchmark): MBPP-MBPP 156 pairs NB -0.474 (p_win 0.231, p_loss 0.705); HumanEval-HumanEval 25 pairs NB -0.680; 114 pairs mixed benchmarks.

Monitoring (alpha 0.05, threshold log 20 = 2.996, decisions read from pair 20): the **harm** e-process (H0: E[Z] >= 0) crossed at **pair 24** (log e 3.209; it had already exceeded the threshold at pair 14 with log e 3.107, before min_n, which is not read under the pre-specified rule), and ended at log e 32.94. The **win** e-process never rose above 0 (maximum -0.125, final -0.904) and the **guardrail** e-process (H0: E[D] <= -0.03) never crossed (maximum and final 0.812). Guarded decision: **B_harmful**; fixed-horizon decision at n = 295: **A** (CS upper bound < 0; the CS first excluded 0 at pair 32). Figure 1 shows the three trajectories; Figure 2 the running NB with its CS.

![fig1](figures/fig1_monitoring.png)

*Figure 1. Log e-values of the win, guardrail (gate) and harm e-processes after each pass-1 pair (`monitor_pass1.csv`); dotted line log(1/alpha); shaded region n < 20 is not read. (b) zoom: harm crossing at pair 24. PDF: `figures/fig1_monitoring.pdf`.*

![fig2](figures/fig2_running_nb.png)

*Figure 2. Running cross-arrival net benefit with its 95% betting CS (`wincs.betting_cs_ternary` on the cumulative counts of `monitor_pass1.csv`), and the same-task NB with its 95% task-clustered CI as a horizontal reference (`summary.json`). PDF: `figures/fig2_running_nb.pdf`.*

### 3.2 E2: same-task shadow contrast (591 tasks, one A and one B episode each; `summary.json` -> `shadow`, `components.same_task_paired`, `task_scores.csv`)

| scope | n tasks | p_win / p_tie / p_loss | NB [95% CI] | WR [95% CI] | WO [95% CI] |
|---|---|---|---|---|---|
| pooled (task-weighted) | 591 | 0.069 / 0.205 / 0.726 | **-0.657 [-0.705, -0.608]** | 0.096 [0.069, 0.132] | 0.207 [0.175, 0.246] |
| MBPP | 427 | 0.070 / 0.239 / 0.691 | -0.621 [-0.679, -0.562] | 0.102 [0.070, 0.148] | 0.234 [0.194, 0.283] |
| HumanEval | 164 | 0.067 / 0.116 / 0.817 | -0.750 [-0.838, -0.662] | 0.082 [0.044, 0.153] | 0.143 [0.096, 0.213] |
| stratified, equal benchmark weight | 591 | 0.069 / 0.177 / 0.754 | -0.685 [-0.738, -0.633] | 0.091 [0.064, 0.130] | 0.187 [0.153, 0.228] |

Tier contribution means: success 0.000 (40 tasks B-only success, 40 tasks A-only), latency -0.655 (1 win / 388 losses), completion tokens -0.002 (0 / 1); ties 121 = 118 both-failed + 3 both-succeeded within both tolerances (`task_scores.csv`; the decomposition reconstructed from `episodes_flat.csv` agrees with the frozen scores on every task). Decision (hierarchical, CI excludes 0): **A**.

Component effects, B - A (`components`):

| component | same-task paired mean diff [95% CI], n = 591 tasks | mean A / mean B (median A / B) | cross-arrival Welch diff [95% CI] (pass 1, 295 vs 295) |
|---|---|---|---|
| success | 0.000 [-0.030, 0.030] | 0.733 / 0.733 (433/591 each) | +0.051 [-0.020, 0.122] |
| latency_s | +9.68 [9.09, 10.26]; ratio of means 4.46 | 2.80 / 12.48 s (2.08 / 10.13) | +9.94 [8.95, 10.94] |
| completion_tokens | +243.0 [228.5, 257.4]; ratio 4.46 | 70.2 / 313.2 (51 / 250) | +250.9 [225.7, 276.2] |
| prompt_tokens | +773.2 [723.5, 823.0] | 120.5 / 893.7 | +760.5 [687.5, 833.5] |
| n_llm_calls (= n_executions) | +1.96 [1.88, 2.04] | 1.00 / 2.96 | +1.91 [1.80, 2.02] |

Per-benchmark success (`episodes_flat.csv`): HumanEval A 0.841, B 0.848; MBPP A 0.691, B 0.689. By pass: pass 1 A 0.715 vs B 0.767 (this is the E1 data), pass 2 A 0.750 vs B 0.698, so the +0.05 seen online reversed in the second exposure and nets to exactly zero. Inside variant B: self-tests passed on the final candidate in 318/591 episodes (299 without repair, 18 after one repair, 1 after two); hidden-test success was 0.840 when the self-tests passed and 0.608 when they did not, so the self-tests are informative about correctness, but the repair loop did not convert that information into a higher success rate (0 repairs: 254/299 succeed; 2 repairs: 167/274). This is a descriptive split, not a causal estimate of repair (tasks that trigger repair are harder).

## 4. Decision-rule table and H4 sensitivity rows

All rules were applied to the same episodes (`decision_rules.csv`; rule definitions in `analysis.py`). In the paper's vocabulary (`paper/decision_ablations.tex`, `paper/results_main.tex`): `success_only` = success-only; `conjunction_all_components` = component-only rule (here success non-inferior AND latency lower AND tokens lower); `utility_w=*` = fixed weighted-utility; `hierarchical_nb` / `hierarchical_nb_betting_cs` = win-only preference (NB CI / CS); `guarded_hierarchical` / `guarded_anytime` = guarded win (NB > 0 AND success non-inferiority at margin 0.03); `pareto_means` = population Pareto description.

| rule | data | estimate | 95% CI / CS | decision |
|---|---|---|---|---|
| success_only (paired) | shadow | 0.000 | [-0.030, 0.030] | none |
| pareto_means (d_success 0.000, d_latency +9.68 s, d_tokens +243) | shadow | - | - | A (A dominates) |
| utility w = 1.00/0.00/0.00 | shadow | 0.000 | point est. | none |
| utility w = 0.80/0.10/0.10 | shadow | -0.692 | point est. | A |
| utility w = 0.60/0.20/0.20 | shadow | -1.383 | point est. | A |
| utility w = 0.50/0.25/0.25 | shadow | -1.729 | point est. | A |
| utility w = 0.34/0.33/0.33 | shadow | -2.283 | point est. | A |
| utility w = 0.20/0.40/0.40 | shadow | -2.767 | point est. | A |
| hierarchical_nb (task-clustered) | shadow | -0.657 | [-0.705, -0.608] | A |
| guarded_hierarchical | shadow | -0.657 | [-0.705, -0.608] | A |
| conjunction_all_components | shadow | - | - | none |
| hierarchical_nb_betting_cs | online | -0.471 | [-0.618, -0.301] | A |
| guarded_anytime (first_deploy none, first_harm 24) | online | -0.471 | [-0.618, -0.301] | A |
| success_only_betting_cs | online | +0.051 | [-0.070, 0.171] | none |

Sensitivity (`sensitivity.csv`; 3 tolerances x 4 tier orders). The two success-first orders keep the frozen absorbing rule; the two resource-first orders (H4) use no eligibility mask, so every tier is compared for every pair.

| tol | order | eligibility | shadow NB [CI] | shadow dec. | online NB [CS] | online guarded |
|---|---|---|---|---|---|---|
| 0.0 | success > latency > tokens | absorbing | -0.662 [-0.710, -0.613] | A | -0.475 [-0.622, -0.304] | B_harmful |
| 0.0 | success > tokens > latency | absorbing | -0.662 [-0.710, -0.613] | A | -0.475 [-0.622, -0.304] | B_harmful |
| 0.0 | **latency > success > tokens** | none | -0.997 [-1.003, -0.990] | A | -0.959 [-1.000, -0.878] | B_harmful |
| 0.0 | **tokens > success > latency** | none | -0.997 [-1.003, -0.990] | A | -0.959 [-1.000, -0.878] | B_harmful |
| 0.1 | success > latency > tokens (frozen) | absorbing | -0.657 [-0.705, -0.608] | A | -0.471 [-0.618, -0.301] | B_harmful |
| 0.1 | success > tokens > latency | absorbing | -0.657 [-0.705, -0.608] | A | -0.471 [-0.618, -0.301] | B_harmful |
| 0.1 | **latency > success > tokens** | none | -0.992 [-1.000, -0.983] | A | -0.956 [-1.000, -0.874] | B_harmful |
| 0.1 | **tokens > success > latency** | none | -0.992 [-1.000, -0.983] | A | -0.956 [-1.000, -0.874] | B_harmful |
| 0.2 | success > latency > tokens | absorbing | -0.658 [-0.707, -0.610] | A | -0.461 [-0.608, -0.291] | B_harmful |
| 0.2 | success > tokens > latency | absorbing | -0.658 [-0.707, -0.610] | A | -0.461 [-0.608, -0.291] | B_harmful |
| 0.2 | **latency > success > tokens** | none | -0.992 [-0.999, -0.984] | A | -0.925 [-0.987, -0.833] | B_harmful |
| 0.2 | **tokens > success > latency** | none | -0.992 [-0.999, -0.984] | A | -0.919 [-0.982, -0.823] | B_harmful |

The decision is invariant to tolerance and to the order of the two resource tiers; swapping latency and tokens changes nothing because within task the two are almost perfectly co-directional (B uses about 4.5x of both). The resource-first rows differ in magnitude, not sign: with no eligibility mask nearly every pair is decided at the first (resource) tier, NB approaches -1, and the success tier is essentially never reached.

## 5. Hypotheses

| | hypothesis (protocol section 1) | verdict | evidence |
|---|---|---|---|
| H1 | B has higher hidden-test success than A | **not supported** | same-task difference 0.000 [-0.030, 0.030] (433/591 each); cross-arrival +0.051, CS [-0.070, 0.171], Welch CI [-0.020, 0.122]; per-benchmark differences +0.006 (HumanEval) and -0.002 (MBPP) |
| H2 | B has higher latency and more completion tokens | **supported** | +9.68 s [9.09, 10.26] (ratio 4.46); +243 tokens [229, 257] (ratio 4.46); 2.96 vs 1.00 calls |
| H3 | frozen hierarchy prefers B (NB > 0) | **refuted** | E2 NB -0.657 [-0.705, -0.608]; E1 NB -0.471 [-0.618, -0.301]; both intervals entirely below 0 |
| H4 | resource-first hierarchies prefer A, disagreeing with H3 | **directional part supported; predicted disagreement not observed** | all six resource-first rows give NB <= -0.919 with CIs excluding 0 (prefer A); but the success-first rows also prefer A, so the objectives agree on the sign here. The dependence on the objective shows up only in magnitude (-0.66 vs -0.99) and in which tier decides |
| H5 | guardrail: B not inferior on success by more than 0.03 | **met at the margin in E2; not established in E1** | same-task CI lower bound -0.0297 > -0.03 (the pre-specified test is satisfied, by 0.0003); online guardrail e-process never crossed (final log e 0.81 < 3.00) and the success CS lower bound -0.070 does not exclude -0.03 |

What the guarded rule did with H1's failure: because the win e-process never approached the threshold, the deploy conjunction (win AND guardrail) was never in play, so the marginal guardrail result was not decision-relevant. The harm e-process, a separately reported test with its own type-I control, crossed at pair 24 (about 10 minutes into the stream), and the rule returned "B harmful": deploying B would have cost 4.5x latency and tokens for no success gain, exactly the outcome the success-first hierarchy is meant to reject. Protocol section 12 anticipated this branch: "If B has lower success (H1 false), the hierarchy will prefer A and the paper reports that as the pre-specified outcome." Success was equal rather than lower, and the hierarchy prefers A on the latency tier.

## 6. Estimand comparison: cross-arrival NB -0.471 vs same-task NB -0.657

The two estimands are the paper's product-law cross-arrival target (E1, theta_s in `paper/main.tex` section "What is a win": independent arrivals in a stratum, which "can mix tasks of different difficulty") and its same-task independent-run target (E2, theta_task). Both were pre-specified and both are reported; neither is reduced to the other. On this run they differ by 0.19, and the tier and tie accounting (`summary.json`, `task_scores.csv`, `episodes_flat.csv`) explains why:

| | E1 cross-arrival (295 pairs) | E2 same-task (591 tasks) |
|---|---|---|
| success patterns both / A-only / B-only / neither | 159 / 52 / 67 / 17 (53.9% / 17.6% / 22.7% / 5.8%) | 393 / 40 / 40 / 118 (66.5% / 6.8% / 6.8% / 20.0%) |
| decided at success tier | 119 (40.3%), net +15 -> +0.051 | 80 (13.5%), net 0 -> 0.000 |
| decided at latency tier | 158 (53.6%): 2 wins, 156 losses -> -0.522 | 389 (65.8%): 1 win, 388 losses -> -0.655 |
| decided at token tier | 0 | 1 (loss) -> -0.002 |
| ties | 18 (6.1%): 17 both-failed + 1 within tolerance | 121 (20.5%): 118 both-failed + 3 within tolerance |
| per-unit variance of the score; naive SE | 0.719; 0.049 | 0.365; 0.025 |

Within a task, the two variants fail together often (118 tasks, 20%) because failure is mostly a property of the task for this model; those pairs are ties under the absorbing rule. Across two different tasks, the chance that exactly one succeeds is much higher (119 pairs, 40%) even though the variants have identical success rates, because the two arrivals differ in difficulty; these success-tier decisions carry no information about the variant and split roughly evenly (67 vs 52, a chance excess for B that reversed in pass 2). They displace latency-tier decisions, which are almost deterministic losses for B (B was faster in only 2 of 158 E1 and 1 of 389 E2 latency-decided comparisons; Figure 4 shows why: nearly every task lies far above the 10% tolerance band). The same-task design therefore has more ties on success, lets the latency tier decide more often, and yields a more negative NB with about half the per-unit variance (0.365 vs 0.719). Mixing benchmarks is not the driver: 44/114 mixed-benchmark E1 pairs and 75/181 same-benchmark pairs were decided at the success tier, so within-benchmark difficulty variation alone produces the effect. The E1 CS is time-uniform and about 3.2x wider than the fixed-sample E2 CI (half-widths 0.159 vs 0.049) for half the number of units. The practical reading for the paper's estimand map: a nonlinear hierarchical kernel makes theta_s and theta_task different numbers even when the component means are identical across designs, and the difference is predictable from the tie structure, which should be reported alongside NB.

![fig3](figures/fig3_tier_decomp.png)

*Figure 3. Tier decomposition for E1 (left) and E2 (right): share of units decided at each tier as B wins (right, blue) or B losses (left, red), with counts; gray = ties. Sources: `summary.json` (E1), `episodes_flat.csv` reconstructed and checked against `task_scores.csv` (E2). PDF: `figures/fig3_tier_decomp.pdf`.*

![fig4](figures/fig4_latency_scatter.png)

*Figure 4. Per-task latency of A vs B (log axes, 591 tasks, `episodes_flat.csv`), coloured and shaped by success pattern; the shaded band is the tier-2 tie region |dL| <= 0.10 max(L_A, L_B). Only one both-success task (`humaneval/64`) lies below the band. PDF: `figures/fig4_latency_scatter.pdf`.*

## 7. Failure accounting and latency scope

Every enrolled arrival yielded a record; nothing was excluded or re-run (`components.failure_accounting`, `episodes_flat.csv`, `episodes.jsonl`):

| per variant (n = 591 each) | A single_shot | B self_test_repair |
|---|---|---|
| failures (success = False) | 158 | 158 |
| verification wall-clock timeout (10 s) | 2 (`mbpp/260`, `humaneval/129`, both pass 1) | 0 |
| entry point not defined in candidate | 1 (`mbpp/273`) | 2 (`mbpp/273`, `mbpp/773`) |
| exit status 0 without sentinel (early exit caught) | 0 | 1 (`mbpp/470`: candidate ended with `unittest.main()`, which ran its own tests and exited 0 before the hidden asserts; without the sentinel this would have been credited as a success) |
| other non-zero exit | 156 (rc 1: failed assert or exception) | 156 (rc 1) + 1 (`mbpp/614`, rc 5: `unittest.main()` with no tests, exit before hidden asserts) |
| API/HTTP error, connection retries, empty code, estimated tokens | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| sandbox_flag / static_flags / hack_flags (flagged successes) | 0 / 0 / 0 (0) | 0 / 0 / 0 (0) |
| hidden-test verification time, mean (max) | 0.053 s (10.02 s) | 0.016 s (0.035 s) |

No candidate matched any static or hack heuristic, so no success is suspect on those grounds; the known universal-`__eq__` limitation was not exercised. The two verification timeouts belong to failed A candidates (infinite or very slow loops); because latency_s excludes verification (protocol section 8, decided before any outcome), they add nothing to A's latency, which the flat CSV confirms (latency 11.15 s and 7.10 s for those episodes; `verify_seconds` up to 10.02 s recorded separately).

Latency scope: `latency_s` = wall clock from the first model call to the final candidate, including all model calls, queueing in the single-request local server, the agent's own sandbox executions and harness overhead; it excludes hidden-test verification, model loading and data loading (`latency_scope` string stamped on every episode). Decomposition from `episodes.jsonl`: A 2.80 s = 2.80 s model time; B 12.48 s = 12.44 s model time + 0.056 s self-test executions. The stream was strictly sequential with no concurrency, so the two arms never contended for the accelerator. Latency is conditional on the recorded hardware (Apple M5, 32 GB, macOS 26.5.2); a different machine changes the latency tier's margins but, given a 4.5x ratio against a 10% tolerance, is unlikely to change its sign.

## 8. How this bears on the paper

Supports:
- A real prospective randomized stream with a frozen design, independently generated seeds, both passes complete, and every episode retained ran end to end on open weights at zero API cost, complementing the historical replays and the 9-pair paid pilot (`paper/prospective_results.tex`), whose incomplete pairs precluded any conclusion. Here the guarded anytime rule reached a valid decision (B harmful) after 24 independent pairs, about 10 minutes into a 2.5 h stream, without stopping the run.
- Tier decomposition is what makes the decision legible: a success-only rule returns "none" (difference exactly 0), whereas the hierarchy returns a decisive A, and the tier table shows that the entire net benefit is latency (-0.52 online, -0.65 same-task) with a success contribution of +0.05 or 0.00. The component means (4.5x latency, 4.5x tokens, equal success) are reported next to the preference, as the protocol requires.
- The estimand distinction is now quantified on real data (section 6): the same hierarchical kernel gives -0.47 across arrivals and -0.66 within task, for reasons visible in the tie structure, and the same-task design has about half the per-unit variance. This supports reporting both targets and the tie rates rather than a single "win rate".
- The guardrail's role: the guardrail e-process was the slowest of the three (never crossed in 295 pairs even though the true success difference is 0), and the paired non-inferiority test met the 0.03 margin by 0.0003. A deploy decision at this stream length would have been blocked by the guardrail even if B had won on the hierarchy; consistent with protocol section 12, a stream of 295 pairs is too short to certify non-inferiority at delta = 0.03 for a ternary success difference, and the paper should state this as a power fact rather than weaken the margin.
- Objective dependence (H4) is visible in the sensitivity table as a difference in what decides (resource tier for nearly all pairs, NB near -1) rather than in sign; the substantive point that the answer depends on the pre-specified objective is only partially exhibited, because equal success makes all sane objectives agree.

Does not show:
- Nothing about commercial or frontier agents, or about tool-using agents: one 7B 4-bit model, one hardware configuration, one serving stack. The "agentic" variant is a simple self-test-and-repair loop with sandboxed execution as its only tool; the tau2-bench feasibility check (`tau2_local_feasibility.md`) found the local stack returned zero structured tool calls, so a tau2 stream was not run.
- Absolute success rates (0.73) are optimistic because MBPP/HumanEval are in code-model training data; only the between-variant contrast is the object of interest. Function-level tasks with binary automatic verification; no long-horizon tasks, no human grading, no production traffic.
- The negative result for self-test-and-repair is specific to this model, prompt and repair budget; the paper should not generalise it to "self-repair does not help".

## 9. Reproducibility

Commands (repository root; `PY=<REPO>/.venv/bin/python`; full list in `experiments/local_stream/README.md`):

```
$PY experiments/local_stream/data.py                                   # download + hash MBPP/HumanEval (work/local_stream/data/)
$PY experiments/local_stream/design.py                                 # frozen design (refuses to overwrite results/local_stream/design.json)
$PY -m unittest experiments/local_stream/tests_local_stream.py -v      # unit tests incl. sandbox containment
$PY -m mlx_lm.server --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit --port 8080   # separate terminal
$PY experiments/local_stream/run_stream.py --results-dir results/local_stream          # pass 1 then pass 2, resumable
$PY experiments/local_stream/analysis.py --results-dir results/local_stream            # summary.json, CSVs, report skeleton
$PY experiments/local_stream/make_figures.py                                            # figures/
```

Recorded provenance (`run_manifest.json`, one invocation, status `completed`, `argv --results-dir results/local_stream`, started 2026-09-18T15:05:49Z, finished 17:37:01Z, elapsed 9,071 s, ran 1,182, skipped 0):
- Hashes: config `2dfb51966780698be326a8897c9e384a5513a7c1a47505c42b8a15c6c5baaf5b` (identical in `config.json`, `design.json` and every episode); design `6175b815...0645457`; task list `23727895...bb01c2ce`; sandbox profile `6370c169267c3f31d3df6321b8acd6b3a363619634835c70854a9bf3952ed900` (identical on all episodes and in the dry-run manifest).
- Model snapshot `019cc73c45c770444708a6dd8690c66243cc5c80`, 11 files, 4,295,890,004 bytes; `model.safetensors` sha256 `56a3d94706833f753e6c6b47ea57af8ef638cd8cc1d74eca1142ba640b26060e` (all 11 per-file hashes in the manifest); cache `~/.cache/huggingface/hub`, outside the repository. `/v1/models` reply and smoke completion (`response_model` = configured model) recorded.
- Harness git hash `526dff7b6d26f818964611b9ccbd8f61fae2e43c`; harness file sha256 (12-char prefixes): common `cdee8821250c`, data `ae630675f437`, sandbox `d461570937dd`, verify `7473678b1990`, agent `3cf2056330c7`, design `3cf14e9502d3`, run_stream `3c4e0782ade9`, analysis `f1f0a05ff6d8`, timing_pilot `5e3312f67fcf`, tests `cdf1e0febdcb`, config.json `0b40e6530ff7`, protocol.md `14a5a81a62fc`, README `71d94227b472`. All 13 match the files on disk at report time.
- Environment: Apple M5 (10 CPU), 34,359,738,368 bytes RAM, macOS 26.5.2, Python 3.12.13, numpy 2.4.1, scipy 1.17.0, pandas 3.0.6, requests 2.34.2, mlx_lm 0.31.3, transformers 5.17.0. Server RSS 4.50 GB at start, 4.43 GB at end. Total tokens: 599,409 prompt, 226,579 completion.
- Timing pilot (`timing_pilot/summary.json`, 6 full-MBPP tasks disjoint from the design, never analysed): projected 3.98 h for 1,182 episodes; actual 2.52 h.
- Licenses (protocol section 14): model card `apache-2.0` (conversion of `Qwen/Qwen2.5-Coder-7B-Instruct`, Apache-2.0); MBPP CC-BY-4.0 (source repository Apache-2.0), Austin et al. 2021; HumanEval MIT, Chen et al. 2021.
- Sampler seeds are sent per call but Metal sampling is not bit-reproducible; the frozen design, not the sampler, carries the reproducibility claim.

## 10. Deviations log

Pre-outcome deviations copied from protocol section 13 (all dated 2026-09-18, before any design-task model call):

| deviation | reason | effect |
|---|---|---|
| RLIMIT_AS 2 GB cannot be set on macOS; RLIMIT_CPU 10 s and 10 s wall clock apply | kernel limitation | memory guard best-effort; applied limits recorded per episode (`RLIMIT_CPU=10,RLIMIT_NPROC=64` on all 1,182) |
| MBPP prompt changed to task text + def signature line only; all asserts graded | audit item 1 | none on B vs A; absolute MBPP success may be below convention |
| success requires the verifier sentinel | audit item 3 | tightened before any outcome (caught `mbpp/470`, section 7) |
| latency_s excludes hidden-test verification | audit section 5 | tier-2 refers to system time only |
| static blocklist demoted to a recorded flag; Seatbelt + process-group kill + RLIMIT_NPROC are the guards; base interpreter | audit item 2 | `sandbox_flag` no longer forces failure (0 flags occurred) |
| run refuses config drift, snapshot/served-model mismatch, concurrent runs, `--only-pass 2` before pass 1; manifest append-only | audit items 4, 7.2, 7.3 | provenance only |
| sensitivity extended with two resource-first hierarchies (no eligibility mask) | audit item 7.1 | H4 has a pre-specified test |
| timing pilot on 6 out-of-design full-MBPP tasks | runtime projection | none; pilot tasks never enter the analysis |
| `extract_code` strips a trailing special token in the no-code-block fallback | `mlx_lm.server` leaves the stop token in content | identical for A and B |

Post-freeze items found in the manifests and result files:

| item | finding | effect |
|---|---|---|
| harness commit id | Protocol section 16 names freeze commit `d9793d56...`; the design generator recorded `cb579f41...`, the dry-run manifest `cb579f41...`, and the real run and every episode `526dff7b6d26f818964611b9ccbd8f61fae2e43c`. Git could not be consulted for this report. The binding record is the per-file sha256: all 12 code/config files are byte-identical between the dry-run (freeze) manifest, the real-run manifest and the files on disk; only `protocol.md` changed between the dry run (`ce1872d2...`) and the real run (`14a5a81a...`, the current file), consistent with the deviation-log entries written before the first real episode. | none on estimands; the commit id in section 16 should be reconciled with the recorded one |
| resume / restarts | none: a single invocation, `skipped_completed 0`, no lock conflicts, no connection retries, no API errors | none |
| harness or config changes after the first real episode | none (hash check above) | none |
| trial 2 | not run (disabled in the frozen config; no resource decision was taken after seeing outcomes) | E1 has one replicate |
| min_n rule and the harm e-process | the harm e-process exceeded the threshold at pair 14 (log e 3.107), inside the pre-specified n < 20 blackout, fell below it at pairs 20 to 23, and is recorded as first crossing at pair 24; the pre-specified rule was followed, which is conservative | none |
| this report | replaces the `analysis.py` skeleton, as planned in the protocol; no number was edited by hand and no result file was modified | none |

## 11. Requirement checklist (GitHub issues #1 and #2)

Issue #1, larger prospective randomized stream:

| requirement | satisfied by |
|---|---|
| frozen design before outcomes | `design.json` + `design.sha256` generated 14:18:18Z, first episode 15:05:50Z; hashes in section 2 |
| independently generated seeds | seed 20260918 via `numpy.random.SeedSequence` (design.json `seed_mechanism`), unrelated to the paid pilot |
| task strata | benchmark stratum: per-benchmark and equal-weight stratified E2 (section 3.2), same-benchmark E1 subsets (section 3.1) |
| retained failures and every enrolled episode | 1,182/1,182 records incl. timeouts, entry-point and sentinel failures (section 7) |
| same-task paired shadow vs randomized AB/BA exposure | E2 vs E1 reported separately and compared (sections 3, 6) |
| exact model/config/harness versions | `run_manifest.json` (section 9); config hash stamped on each episode |
| immutable run manifest | append-only manifest, one invocation record, never modified |
| task/seed accounting | `design.json` lists all 591 arrivals with pair index, orientation, pass-1/pass-2 variant; `data_manifest.json` |
| correct independent-unit uncertainty | E1: independent pairs, betting CS and e-processes; E2: task-clustered t CI (`clustered_summary`) |
| continuous-monitoring analysis | `monitor_pass1.csv` (295 rows), `monitor_state.json`, Figures 1-2 |
| abstention/incomplete runs reported | none occurred; failure accounting per variant (section 7) |

Issue #2, local-model replication:

| requirement | satisfied by |
|---|---|
| model license and tool-use capability verified | Apache-2.0 (section 9); runnable code on the 6 out-of-design pilot tasks and 2,339 stream calls; tool use = harness-executed self-tests (tau2 tool calling not available locally, `tau2_local_feasibility.md`) |
| cache/runtime space estimated | README estimates; measured 4.30 GB snapshot, 4.5 GB server RSS |
| model snapshot documented | revision, 11 files, sizes, per-file sha256 in the manifest; run refuses a different revision |
| existing public verifiable benchmark, fixed task selection | all 427 MBPP-sanitized + 164 HumanEval, no selection |
| two meaningfully inexpensive workflow variants | 1 call vs 2-4 calls on a local 7B model; 2.8 s vs 12.5 s per task |
| weights outside the repo | huggingface cache; `work/` git-ignored |
| runnable instructions | `experiments/local_stream/README.md` (section 9) |
| hardware/config hashes | manifest hardware block, config hash, harness file sha256 |
| frozen task and seed manifest | `data_manifest.json`, `design.json` |
| retained failure records | section 7 |
| latency measurement scope | section 7 (excludes hidden-test verification; `verify_seconds` separate; `latency_scope` string on every episode) |
| resource use | manifest RSS, snapshot bytes, elapsed 9,071 s; per-episode tokens, calls, executions; totals in section 9 |
| task-level hierarchical scores and component outcomes | `task_scores.csv`, `episodes_flat.csv`, sections 3.2 and 6 |
| uncertainty appropriate for repeated tasks | task-clustered CIs (E2) |
| how the replication changes or limits conclusions | section 8 |
