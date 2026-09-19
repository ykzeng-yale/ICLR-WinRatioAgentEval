# Session-60 figures

Produced by `experiments/session60_figures.py` (run with `.venv/bin/python experiments/session60_figures.py`;
about 10 s). Each figure is written as PDF (vector, Type-42 fonts) and PNG (300 dpi) at ICLR single-column
width (5.5 in), 6-8.5 pt sans text, colourblind-safe categorical palette (blue `#2a78d6`, orange `#eb6834`,
aqua `#1baf7a`, validated with the dataviz palette checker: worst adjacent CVD dE 9.1, normal-vision dE 22.9).
`figure_numbers.json` records the SHA-256 of every input file used and the key numbers below.
All inputs are read-only; the script only re-reads them at the end and regenerates if they changed
(the replay CSVs were rewritten by a background job during this session with byte-identical content).

`fig_decision_matrix.*` and `fig_sensitivity.*` in this folder are NOT produced by this script (another agent).

## fig_replay_stopping (paired vs cross-arrival stopping times)
* Data: `results/replay/replay_results.csv`, rows `tau2_o4mini_vs_gpt41_all` (o4-mini vs GPT-4.1, airline+retail+telecom,
  500 random orders, cap 2000 pairs, guarded betting e-process: net benefit > 0 AND success non-inferiority at margin 0.03, alpha 0.05).
  The CSV stores only summary quantiles, so the plotted cumulative "fraction deployed by n" curves come from an
  independent re-run of the same replay (functions imported from `experiments/run_replay.py`, same pools/scoring/rule,
  fresh seeds `[60, k]`); the canonical CSV numbers are printed under the plot.
* Canonical CSV: paired design deploys in 97.6% of orders, median stop 838 pairs (IQR 563-1198), harm flags 0.0%;
  cross-arrival design deploys in 36.8%, median stop 1157 (IQR 759-1639), harm flags 0.2%.
  Re-run (curves): 95.2% / median 804 (paired) and 36.0% / median 1208.5 (cross-arrival); consistent within Monte-Carlo error
  (binomial SE ~1-2 points at 500 replicates).
* Takeaway: pairing on the same task roughly triples the deployment rate (96% vs 33%) and shortens the median stopping time
  by ~300 pairs, because cross-arrival pairs add between-task noise to the same true effect.

## fig_example_stream (running estimates with betting CS)
* Data: `results/replay/example_stream_cs.csv` (one paired stream, seed 123, looks every 25 pairs up to 2000).
* Final (n = 2000): net benefit +0.097, 95% betting CS [+0.037, +0.156]; success difference +0.029, CS [-0.010, +0.068].
  The net-benefit CS excludes 0 from n = 425 onward; the success-difference CS clears the -0.03 guardrail from n = 775 onward.
* Takeaway: the hierarchical net benefit is established (lower bound > 0) about 350 pairs before the success guardrail is cleared,
  so the guardrail, not the primary win statistic, is what governs the deployment time in this stream.

## fig_ranking_disagreement (bump chart of per-domain ranks)
* Data: `results/benchmarks/tau2_rankings.csv` (three models, three tau2 domains, criteria: success rate, pass-all-4,
  hierarchical net-benefit sum, success - 1*cost, success - 0.3*cost).
* Top model by criterion: airline -> o4-mini / GPT-4.1 / o4-mini / o4-mini / o4-mini;
  retail -> Claude 3.7 / Claude 3.7 / o4-mini / GPT-4.1 / GPT-4.1; telecom -> Claude 3.7 / o4-mini / o4-mini / o4-mini / o4-mini.
  No domain has a single #1 across all five criteria; retail has three different #1s.
* Takeaway: the "best" model on tau2-bench is a property of the criterion, not of the data: Claude 3.7 tops raw success in
  retail and telecom but is last under the hierarchical net benefit because of ~6x higher cost
  (e.g. retail cost 0.335 vs 0.058 for GPT-4.1 in `tau2_marginals.csv`).

## fig_hal_latency (15 HAL contrasts under two hierarchies)
* Data: `results/benchmarks/hal_contrasts.csv`, labels `primary` (success > cost > steps) and `success_latency_cost`
  (success > latency > cost); 6 HAL taubench-airline agent configurations, 50 tasks each, net benefit with 95% CI.
* 8 of 15 contrasts change point estimate when latency replaces steps; two flip sign:
  ToolCalling/GPT-4.1 vs ToolCalling/o4-mini -0.26 -> +0.02 and ToolCalling/Claude 3.7 vs ToolCalling/o4-mini -0.42 -> +0.02
  (o4-mini high is slow: 135.5 s mean latency vs 38.9 s and 54.0 s, `hal_marginals.csv`). Largest shift in magnitude:
  Generalist/Claude 3.7 vs Generalist/o4-mini +0.22 -> +0.38.
* Takeaway: the tie-breaking tier matters for close pairs; the top contrast (Generalist/Claude 3.7 vs Generalist/GPT-4.1,
  +0.28 [0.07, 0.49]) is decided at the success tier and is invariant to the hierarchy.

## fig_cs_width (CS width vs n, log-log)
* Data: `results/cs_width.csv` (200 replicates per n; mean 95% interval width for net benefit).
* At n = 10 000: betting mixture CS 0.0549, normal-mixture CS 0.0655, multinomial Dirichlet CS 0.0859,
  fixed-n Wald CI 0.0347 (not sequentially valid). At n = 100: 0.562 / 0.731 / 0.650 / 0.345.
* Takeaway: the betting CS is the tightest anytime-valid interval at every n >= 100 and is 1.56x narrower than the
  Dirichlet CS at n = 10 000, at the price of being 1.58x wider than the (invalid under continuous monitoring) fixed-n Wald CI.

## fig_simplex_price (mean log e-process vs n)
* Data: simulation inside the script (400 replicates, n up to 10 000, seed 60): Dirichlet-multinomial e-process
  (`wincs.ternary_log_eprocess_nb`, priors (1,1,1) and (0.5,0.5,0.5)) vs the 40-bet betting e-process
  (`winstats.betting_log_e_ternary`). Streams: rare-event compliance gate p(win,tie,loss) = (0.004975, 0.99005, 0.004975),
  H0: nb <= -0.01; success gate p = (0.1875, 0.625, 0.1875), H0: nb <= -0.03. Both streams have true nb = 0, i.e. the
  alternative is true by a margin of exactly 0.01 and 0.03.
* First n at which the MEAN log e-process crosses log(1/alpha) = log 20 = 3.00: rare-event gate: betting 1366,
  Dirichlet(1/2) 3101, Dirichlet(1) 3919; success gate: betting 4406, Dirichlet priors only at n = 10 000
  (values 3.63 and 3.01 at n = 10 000 vs 9.40 for betting).
* Takeaway: the Dirichlet e-process pays a "price of the simplex" (an initial dip of -4 to -7 nats that it must earn back),
  so the betting e-process crosses the alpha = 0.05 boundary 2.3-2.9x earlier on the rare-event gate and >2x earlier on
  the success gate.

## fig_online_methods (deployment rate by scenario, guarded methods)
* Data: `results/online_methods_results.csv` (2000 replicates, cap 10 000 pairs; six guarded methods; the two win-only
  methods are omitted because they ignore the guardrail). Left column = admissible scenarios (should deploy);
  right column = inadmissible (should not deploy); dashed line = nominal alpha = 5%.
* Inadmissible: guarded betting deploys 0.6% (null), 0.75% (tie-heavy null), 0% (success regression), 0% (safety regression);
  guarded Dirichlet 0% everywhere; guarded naive repeated Wald 29.9% / 31.0% / 0.3% / 1.95%; guarded fixed-n Wald 4.95% / 4.55% / 0 / 0.
* Admissible: guarded betting 96.6% (efficiency gain), 100% (joint gain), 93.8% (tie-heavy efficiency), 3.5% (weak gain nb = 0.01);
  guarded Dirichlet 60.1% / 100% / 51.3% / 0.05%; guarded normal-mixture 0% in every scenario; guarded group-Bonferroni Wald
  99.3% / 100% / 99.0% / 10.9%; naive repeated Wald 99.95% / 100% / 100% / 54.6%.
* Takeaway: only the guarded betting method combines <1% false deployment in all four inadmissible scenarios with
  >93% power in the three well-powered admissible ones; the naive repeated Wald rule reaches ~30% false deployment under the null
  and the Dirichlet guard loses 36-43 points of power in the efficiency-gain scenarios.
