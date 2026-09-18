# Independent methodology review — round 1

Date: 2026-09-17. Reviewer: an independent AI subagent, not an external human referee. Scope: `src/winstats.py`, `src/test_winstats.py`, `experiments/run_simulations.py`, `experiments/simulation_protocol.md`, and the initial six-scenario results CSV. This review does not certify a manuscript not yet examined.

## Assessment

The ternary betting implementation and analytic simulation target are coherent for the explicitly stated stationary independent-pair design. The separate safety and success gates remedy the illustrated population-level composite failure. I found no substantive validity defect in that restricted construction. The experiments are useful initial validation, but the existing comparisons do not support state-of-the-art efficiency claims, nor empirical generality to adaptive routing, task reuse, delayed feedback or production A/B testing.

### Correctness checks

- For threshold `c`, bets lie below `1/(1+c)`, so `1+lambda*(Z-c)` remains nonnegative for all ternary observations. Under the stated conditional null, its conditional expectation is at most one. The constant-bet mixture is therefore a valid e-process. The count formula reproduces the product for a fixed bet.
- At one specified conjunction of benefit/success/safety requirements, alpha=0.05 per gate is appropriate intersection-union testing. One false null component is enough to bound the probability of ever passing the entire conjunction by 0.05. This is not simultaneous 95% confidence for all reported components and does not extend without correction to multiple candidate deployments.
- `exact_targets` correctly accounts for binary safety ties, success differences at that tier, and efficiency only among pairs with both safe successes. Its lognormal threshold calculation is correct: an A cost win requires `log(C_A/C_B) < log(.95)`.
- The pointwise conditional-null restriction on the betting method is correctly documented. It must remain explicit whenever a running-average drift target is discussed.

## Required changes or claim restrictions

### M1 — High: the normal-mixture comparison is intentionally conservative, not a strong competing sequential method

Location: `experiments/run_simulations.py`, line 74; `src/winstats.py`, lines 41–51 in the examined version.

The normal-mixture baseline uses a two-sided confidence sequence and worst-case variance process `V=n`; betting is directional and adapts implicitly to the ternary event counts. At 10,000 pairs its radius is **0.0327302**, over three times the allowed 0.01 safety loss. Thus its near-zero deployment power is largely built into the chosen bound and horizon, even for equally safe systems. This is not evidence that modern confidence sequences generally fail in this setting.

Remedy: name it a conservative worst-case normal-mixture baseline; add an appropriately matched one-sided empirical-Bernstein or published betting confidence-sequence method. Include the relevant published group-sequential win-statistic approach where estimands/designs align. If these additions remain pending, restrict the manuscript to illustrating calibration and a known variance-adaptation advantage, without proposing a competitive new monitoring inequality.

### M2 — High: no implemented experiment currently exercises the difficult online claims

Location: `generate`, lines 26–44 and `SCENARIOS`, lines 16–23.

The mechanism makes all arms, outcomes, costs and arrivals independent with fixed parameters. It does not simulate actual AB/BA randomization, adaptive assignment, propensity correction, changing task mix, clustered repeated runs, delayed completion, or selective trace sampling. Exchangeability explains why explicit order is unnecessary for this stationary baseline, but cannot validate the more general design.

Remedy: retain this as a stationary calibration study. Add separately labeled extension experiments for the claimed online features, with the estimand and filtration made explicit. At minimum include an adaptive-order example and an informative-completion counterexample. Do not present synthetic independent pairs as real online exposure data.

### M3 — Medium: guardrail boundary calibration should be part of the reproducible study

Location: `SCENARIOS` and thresholds `[0,-.03,-.01]`.

The initial harmful success/safety settings lie beyond the null boundaries. Those are easy rejection-avoidance cases and do not stress the least favorable guardrail boundary. Independent reviewer probes below found no problem, but the scientific package should include boundary settings in its maintained experiment suite.

Remedy: append, as a post-review extension, success difference exactly −0.03 and safety difference exactly −0.01, with positive composite benefit and the remaining gate comfortably satisfied. Report rates and Monte Carlo intervals. Do not retroactively call these probes prespecified.

### M4 — Medium: invalid hierarchy tolerances silently change the comparison

Location: `Tier`, lines 11–16 and `compare`, lines 30–37.

There is no finite/nonnegative tolerance validation. A NaN tolerance turns a genuine single-tier difference into a tie. A negative tolerance at an exactly tied upper tier marks it decisive with score zero and blocks a real lower-tier difference. This is a software defect, although the current simulation uses valid constants and is unaffected.

Reproductions:

```python
compare([[1]], [[0]], [Tier('success', absolute_tolerance=np.nan)])
# returns score 0, tier -1
compare([[1,1]], [[1,0]],
        [Tier('safety', absolute_tolerance=-1), Tier('success')])
# returns score 0, tier 0 instead of rejecting the invalid protocol
```

Remedy: validate both tolerance parameters as finite and nonnegative during `Tier` construction. Reject an empty hierarchy or malformed outcome dimension explicitly. Document that eligibility rules must preserve pair-exchange symmetry if antisymmetry is claimed.

### M5 — Medium: the simulation does not use the exported comparator

Location: `generate` manually constructs signed scores rather than calling `compare`.

The implementation currently agrees with the described protocol, but changing one comparison implementation can leave the other stale. The current test suite verifies generic comparator invariants and the simulator's analytic mean separately; it does not verify the same generated outcomes produce identical scores through both paths.

Remedy: expose generated outcome arrays or construct a representative outcome fixture and assert exact comparator agreement under the simulation's eligibility masks. This is a meaningful implementation-theory correspondence check, not a duplicated formula test.

### M6 — Medium: distinguish deployment false positives from a win-only test's statistical error

Location: the `win_only_betting` row and global `admissible` field.

For success/safety regressions, true composite benefit is positive, so win-only betting is correctly detecting its own target. Calling the near-100% rate its statistical Type I error would be false. The protocol already makes this distinction; maintain it in figures, captions and main text. Describe these as unacceptable deployments under the separate component requirements.

### M7 — Medium: current spending and efficiency metrics are deliberately narrow

Location: `mean_pairs_used`, lines 110–124.

The number is a capped sample-count measure, not actual agent dollars, wall-clock latency, or compute used by the monitor. There is no futility rule, so all nondeployments consume the full horizon. Conditional median stopping times exclude nondeployments and can reward low-power procedures if quoted alone.

Remedy: emphasize capped mean sample count and power jointly. One pair corresponds to two run outcomes in this design. Add actual resource consumption when real traces are used; use paired Monte Carlo differences and their standard errors if claiming small efficiency gains.

## Reviewer-run boundary probes

These are independent, post-review diagnostics, not additions to the initial results CSV. Run on the examined implementation, using NumPy default generators with seeds 872100 and 872101, 1,000 replications each, batches of 25, maximum 10,000 pairs, looks every 50 from 100 plus ten equally spaced group looks. Parameters below use `(safe_A,safe_B,success_A,success_B,cost_ratio)`.

- Success boundary: `(.995,.995,.72,.75,.4)`, exact net benefit 0.4240552, success difference −0.03, safety difference 0.
- Safety boundary: `(.985,.995,.75,.75,.4)`, exact net benefit 0.4579129, success difference 0, safety difference −0.01.

| Method | Success-boundary deployment rate, 95% Wilson interval | Safety-boundary deployment rate, 95% Wilson interval |
|---|---|---|
| Win-only betting | 1.000 [0.9962,1.0000] | 1.000 [0.9962,1.0000] |
| Guarded betting | 0.006 [0.0027,0.0130] | 0.006 [0.0027,0.0130] |
| Guarded normal-mixture | 0.000 [0.0000,0.0038] | 0.000 [0.0000,0.0038] |
| Guarded repeated Wald | 0.319 [0.2909,0.3485] | 0.279 [0.2521,0.3076] |
| Guarded ten-look Bonferroni Wald | 0.019 [0.0122,0.0295] | 0.022 [0.0146,0.0331] |
| Guarded fixed Wald | 0.042 [0.0312,0.0563] | 0.046 [0.0347,0.0608] |

These results corroborate the expected repeated-peeking failure and conservative valid procedures under two more null configurations. They do not establish validity for all distributions, and the win-only row is a different null/decision target.

## Recommendation

Keep the current results as an honestly labeled initial calibration experiment. Correct M4 and verify M5, incorporate the boundary extension, and avoid superiority claims until stronger valid baselines and meaningful online stress tests are implemented. The main remaining ICLR risk is the scientific contribution, not a discovered failure of the basic stationary e-process.
