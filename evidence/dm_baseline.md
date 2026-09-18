# Isolated complete-data Dirichlet-mixture reference comparison

Prepared 2026-09-18 UTC. This is an audited reproduction of a contributed comparison whose results already existed and had been inspected. It is **not a new preregistration**, and its additional scenarios were not part of the original six-scenario study. Original contribution and baseline results are preserved.

## Purpose and release boundary

The comparison adds an established likelihood-mixture reference to the existing positive-betting, normal-mixture, and Wald procedures on the **same complete iid pair scores, estimands, guardrail thresholds, candidate systems, and looks**. It does not compare confidence widths or claim that one method uniformly dominates another. It is a score simulation, not an agent API experiment or a randomized intervention among production users.

The audited isolation contains:

- `src/ternary_dm.py`: only the complete-data ternary likelihood routines, plus input validation.
- `experiments/reproduce_dm_baseline.py`: a rerun of eight contributed complete-data scenarios, using the existing audited generator and baseline evaluator.
- `results/dm_baseline_results.csv`: all method/scenario rows.
- `results/dm_baseline_paired.csv`: paired differences in capped stopping sample size between guarded DM and guarded betting.
- `results/dm_baseline_reproduction_check.json`: comparison with every corresponding original result field.
- `results/dm_baseline_manifest.json`: exact configuration, software, source and output hashes, provenance, and comparison status.

The full contributed `wincs.py` is not imported. Its generic linear projection, ratio projection, two-sided betting inversion, and offline routines are not endorsed by this extraction. The contributed `cs_width.csv` is excluded: its projection solver and two-sided betting construction have unresolved correctness defects documented in `reviews/contributed_wincs_audit.md` and repository issue 4.

## Model, target, and known construction

For each gate, the complete score takes values in `{+1,0,-1}` and has a fixed categorical probability vector `p=(p_win,p_tie,p_loss)`. Records are iid across disjoint pairs; components within a pair may be dependent. The gate mean is `p_win-p_loss`. The prior has three fixed positive parameters, here `(1,1,1)`.

The Dirichlet-mixture construction and time-uniform inversion are established in Lindon and Malek (NeurIPS 2022), Section 2. The paper's simultaneous projections concern functionals of one common categorical vector; its general categorical result assumes constant cell probabilities. [Official proceedings record](https://proceedings.neurips.cc/paper_files/paper/2022/hash/12f3bd5d2b7d93eadc1bf508a0872dc2-Abstract-Conference.html), [published paper](https://papers.neurips.cc/paper_files/paper/2022/file/12f3bd5d2b7d93eadc1bf508a0872dc2-Paper-Conference.pdf).

```bibtex
@inproceedings{lindon2022multinomial,
  author = {Lindon, Michael and Malek, Alan},
  title = {Anytime-Valid Inference For Multinomial Count Data},
  booktitle = {Advances in Neural Information Processing Systems},
  volume = {35},
  pages = {2817--2831},
  year = {2022},
  url = {https://proceedings.neurips.cc/paper_files/paper/2022/hash/12f3bd5d2b7d93eadc1bf508a0872dc2-Abstract-Conference.html}
}
```

Independence with changing cell probabilities does not, by itself, satisfy this likelihood model. A fixed conditional score mean also does not imply a fixed categorical vector. This comparator is restricted to the iid simulation; no adaptive importance weighting or mean-only drift guarantee is claimed. The simulator produces separate raw success/safety contrast scores, so guardrails are not incorrectly inferred from decisive hierarchy cells.

## Exact composite-null derivation

Let `x_n=(w_n,t_n,l_n)` be the cumulative counts, `a` the prior, and `B` the multivariate beta function. Define

\[
q_n = B(a+x_n)/B(a),\qquad
M_n(p)=q_n/\{p_w^{w_n}p_t^{t_n}p_l^{l_n}\}.
\]

The numerator is the probability of the observed ordered categorical sequence after integrating its fixed probability vector over the Dirichlet prior. Under a fixed interior null vector `p`, the likelihood ratio for each alternative vector is a nonnegative mean-one martingale. Integrating alternatives preserves this property. If a true cell probability is zero, the analogous ratio on the true support is a nonnegative supermartingale, which is enough for the same upper error control. Use `0 log 0 = 0` for zero-count cells; an observed positive count at an impossible null cell has zero null likelihood.

For the one-sided composite null

\[
\mathcal P_c=\{p\in\Delta_3:p_w-p_l\le c\},
\]

define

\[
E_n(c)=\inf_{p\in\mathcal P_c}M_n(p)
=\exp\left\{\log B(a+x_n)-\log B(a)
-\sup_{p\in\mathcal P_c}\sum_jx_{n,j}\log p_j\right\}.
\]

For every true iid null vector `p0` in this set, `E_n(c) <= M_n(p0)` pathwise. Thus, for every stopping time, its expectation is at most one, and a crossing at any prefix is included in the crossing event of `M_n(p0)`. Ville's inequality gives

\[
P_{p_0}\{\exists n:E_n(c)\ge1/\alpha\}\le\alpha.
\]

The infimum need not itself be a martingale. It is a valid composite-null e-process by domination. Checking a fixed subset of prefixes preserves the bound.

Concavity of the log likelihood gives a simple constrained optimizer. If the MLE satisfies the mean null, use its likelihood. Otherwise the optimum lies on `p_w-p_l=c`. Write `p_l=u`, `p_w=u+c`, and `p_t=1-2u-c`, with

\[
\max(0,-c)\le u\le(1-c)/2.
\]

Multiplying the score equation by its denominators gives

\[
-2n u^2+\{w(1-c)+l(1-3c)-2tc\}u+lc(1-c)=0.
\]

The code evaluates the feasible roots and endpoints with the zero-count convention and takes the largest log likelihood. At zero observations `E_0(c)=1`. The input-checked entry point rejects fractional or negative counts, invalid thresholds, and nonpositive prior parameters. Counts are ordered **win, tie, loss**, whereas the contributed general hierarchy-cell module orders its first three cells **tie, win, loss**.

## Deployment rule and what “simultaneous” means here

Each pair supplies three scores: hierarchical net benefit, raw success difference, and raw safety difference. Thresholds are `(0,-0.03,-0.01)`. The guarded rule requires all three one-sided processes to reach `1/0.05=20` at the same monitored prefix. An inadmissible stationary model has at least one fixed true-null gate. Any false conjunction deployment entails a crossing of that gate, so the intersection–union argument controls the entire false-deployment probability by 0.05. Gate independence is unnecessary.

This rule is **not** a single simultaneous 95% confidence region for all effects. Separate per-gate tests at 0.05 give the conjunction guarantee just described. Simultaneous estimation of all component targets would require an additional joint representation or allocated confidence error. Win-only procedures intentionally omit component constraints; their deployment of component-regressing systems is a failure relative to the guarded deployment objective, not necessarily a Type I error for their narrower win-only null.

## Asynchronous exclusion

This DM statistic is not coordinatewise increasing in the observed scores. At threshold zero, complete counts `(10,0,0)` give log evidence `2.741817`, while lowering one win to a tie gives `(9,1,0)` and log evidence `2.996915`, crossing `log(20)`. Therefore a plug-in of lower partial scores need not lower DM evidence. Only complete iid prefixes are used here. An asynchronous DM extension would need a separately justified infimum over feasible completed categorical counts, not the existing positive-factor shortcut.

## Frozen reproduction configuration

The first six scenarios are unchanged from the original generator: identical systems, cost efficiency, success regression, safety regression, joint gain, and weak gain. The two contributed extensions lower success probabilities to 0.30 in both arms, yielding more failure ties; their cost ratios are 1 and 0.55. They are labeled `tie_heavy_null` and `tie_heavy_efficiency` and were added after the original six-scenario run.

There are 2,000 repetitions per scenario, 10,000 maximum pairs, batch size 25, and master seed `20260918`. Scenario `j` uses `SeedSequence([20260918,j])`. Keeping batch size fixed matters for exact RNG consumption. Looks are `100,150,...,10000`, plus the ten planned group looks already contained in that grid. Both models' successes, safety indicators, and costs are simulated independently as in `run_simulations.py`; each score law is stationary. Both methods use exactly the same draws within a repetition.

The original primary six-scenario study used a different seed (`20260917`). The new rows must be called a separate reproduced reference comparison; do not silently replace one study's Monte Carlo numbers with the other's.

The eight methods are win-only betting, win-only DM, guarded betting, guarded DM, guarded normal mixture, guarded repeated Wald, guarded ten-look Bonferroni Wald, and guarded fixed-horizon Wald. Wald procedures remain asymptotic comparators; the repeated ordinary Wald procedure is deliberately unsuitable for unrestricted repeated inspection. No new exact finite-sample claim is made for the Wald comparators.

Every method stops at its first current-look gate conjunction. Nondeployment is assigned the cap of 10,000 pairs. Reported means are capped sample sizes, and the median is conditional on deployment. Original row-level Monte Carlo standard errors use the empirical second moment with divisor R for exact reproduction; the difference from a sample-variance divisor R-1 is a factor `sqrt((R-1)/R)`, approximately 0.99975 at R=2000. New paired-difference standard errors use R-1.

## Verification and reproducibility

Run from the project root:

```sh
python experiments/reproduce_dm_baseline.py
```

This command writes only `results/dm_baseline_*` artifacts and never invokes the width study. It compares all 64 complete-data result rows with the preserved contributed CSV when the original default configuration is used, recording each field-level difference and failing if discrepancies exceed rounding tolerance. Source and output hashes identify the exact implementation and inputs.

Before this rerun, the isolated formulas matched the contributed ternary routines exactly on 25,000 arrays' entries across five thresholds, including -1 and 1. The full eight-method evaluator also matched on a shared test batch. An earlier independent audit checked 4,395 constrained likelihood cases against numerical optimization and enumerated exact first-crossing probabilities in several small iid null models. These checks validate the extracted implementation for the tested use, rather than the quarantined general projection/inversion code.

The final execution and comparison status is recorded in `results/dm_baseline_reproduction_check.json`. No universal superiority conclusion should be drawn from the finite scenarios or from zero observed false deployments.

## Completed reproduction result

The default 16,000-repetition run completed successfully. **All 64 complete-data rows reproduced exactly across every compared field**, with maximum absolute numeric difference zero. Every recorded source and output hash was rechecked after execution. The isolated run took 22.26 seconds in the recorded local environment; runtime is not a benchmark result.

| Scenario | Guarded DM deployment rate | Guarded betting deployment rate | DM mean capped pairs | Betting mean capped pairs |
|---|---:|---:|---:|---:|
| Identical systems | 0 | 0.006 | 10,000 | 9,965.325 |
| Cost efficiency | 0.601 | 0.966 | 8,090.825 | 4,361.825 |
| Success regression | 0 | 0 | 10,000 | 10,000 |
| Safety regression | 0 | 0 | 10,000 | 10,000 |
| Joint gain | 1 | 1 | 3,608.375 | 1,426.8 |
| Weak gain | 0.0005 | 0.035 | 9,997.475 | 9,837.75 |
| Tie-heavy identical systems | 0 | 0.0075 | 10,000 | 9,954.15 |
| Tie-heavy cost efficiency | 0.513 | 0.9375 | 8,377.55 | 4,790.7 |

For cost efficiency, the mean paired increase in capped sample size from guarded betting to guarded DM was 3,729 pairs (Monte Carlo standard error 45.81); for the tie-heavy efficiency extension it was 3,586.85 (46.90). In these scenarios and at this fixed prior, DM was more conservative. These observations justify including an established reference comparison; they do not establish a universal method ordering or mean that zero observed false deployments implies zero true error probability. Both win-only procedures deployed all success- and safety-regressing alternatives, reinforcing that evidence calibration alone does not replace component requirements.
