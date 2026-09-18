# Independent audit of the contributed `wincs.py` module

Audit date: 2026-09-18 UTC. Source SHA-256: `9455b476b403d9bb2e5caea85c1109660d0864b136f3773b31c822a9e67c0475`.

The reviewer did not author this contributed module or its tests. This is a read-only integration audit; no source changes, output changes, or git operations were performed. The manuscript did not use this module at the audited snapshot.

## Integration decision

**Do not use the general `MultinomialCS` functional bounds as valid confidence sequences in their present implementation.** A reproducible numerical defect excludes a deterministic true distribution with probability one. The underlying Dirichlet-multinomial construction is standard and mathematically appropriate for iid categorical data; its optimization implementation is the issue.

The separate `ternary_log_eprocess_nb` implementation does not call that faulty optimizer. Its formula and tested numerical behavior support considering it as an additional **complete-data, iid ternary** comparator, with frozen positive prior and correctly specified counts. That is a narrower recommendation than endorsing the whole module or calling it a uniformly stronger simultaneous-CS baseline. It cannot be inserted into the asynchronous lower-score product argument by direct substitution.

## Primary-source verification

Lindon and Malek's *Anytime-Valid Inference for Multinomial Count Data*, NeurIPS 2022, gives the Dirichlet-mixture likelihood ratio, its time-uniform inversion, and simultaneous coordinate projections in Section 2, Theorem 2.4 and Corollary 2.5. The formula for `log_mixture_martingale`, the sign of `cs_threshold`, and the convex likelihood constraint in this module agree with that construction. The source uses a common categorical probability vector; independence alone is insufficient for multinomial counts. Its later time-varying applications impose additional structure, rather than automatically allowing arbitrary changing outcome laws. [Published paper](https://papers.neurips.cc/paper_files/paper/2022/file/12f3bd5d2b7d93eadc1bf508a0872dc2-Paper-Conference.pdf), [official proceedings record](https://proceedings.neurips.cc/paper_files/paper/2022/hash/12f3bd5d2b7d93eadc1bf508a0872dc2-Abstract-Conference.html).

## Findings affecting integration

### P1: near-vertex numerical optimization invalidates advertised coverage

Location: `src/wincs.py:149`, `src/wincs.py:171`, and `src/wincs.py:180`.

Minimal reproduction, with cells ordered **tie, win, loss**:

```python
cs = MultinomialCS(1, delta=0.05, prior=1.0)
cs.contains([0, 3, 0], [0, 1, 0])
# True
cs.net_benefit([0, 3, 0])
# (-0.658004810664131, 0.9997631258037212)
cs.p_win([0, 3, 0])
# (0.17099759467291437, 0.9997631258037212)
```

If the true cell law is `(0,1,0)`, these counts occur deterministically at the third observation. Both the true net benefit and win probability equal one, yet both returned intervals exclude one. Therefore the actual functional-CS routine has time-uniform noncoverage probability **one**, despite the raw confidence set containing the truth. This is not a Monte Carlo fluctuation or an interpretive objection.

The routine evaluates an almost-vertex solution with multiplier `1e-12`, solves for a root using absolute tolerance `1e-14`, and returns the resulting objective without guaranteeing that the pseudo-probability vector sums to one. At this scale, subtraction and root tolerance introduce appreciable relative error. The early return treats this approximation as the exact vertex optimum.

A second check shows the broader numerical symptom:

```python
linear_bound([2,3,4], [1,1,1], [1,1,1], .05, False)
# 0.9998987738540442
linear_bound([2,3,4], [1,1,1], [1,1,1], .05, True)
# 0.9998864406920706
```

The functional is identically one on the simplex, but the reported lower bound exceeds the reported upper bound and neither equals one. Other vertex examples produce values above the support boundary. Merely clipping to the known support does not repair an upper bound that is already too small.

Required repair before integration: handle exact constant/vertex faces analytically; use numerically stable normalized solutions elsewhere; return conservative outward bounds, ideally with a feasible/dual certificate or a justified numerical error allowance. Include deterministic boundary laws and constant objectives in regression checks. The existing random interior/grid tests permit errors of roughly `1e-3` and do not establish coverage at simplex boundaries. Ratio bounds depend on `linear_bound` and inherit this qualification.

### P1 integration restriction: ternary DM evidence is not monotone in the score

Location: `src/wincs.py:319`.

The positive-stake asynchronous theorem relies on coordinatewise monotonicity of each factor. The Dirichlet-mixture numerator changes when cells change, so that argument does not transfer. A concrete threshold-crossing counterexample uses counts ordered **win, tie, loss**:

```python
ternary_log_eprocess_nb(10, 0, 0, threshold=0)
# 2.741817063573026  < log(20)
ternary_log_eprocess_nb(9, 1, 0, threshold=0)
# 2.9969145239335155 > log(20)
```

The second data vector is obtained by lowering one score from `+1` to `0`, yet evidence increases and crosses the threshold. Thus substituting lower partial scores can falsely claim domination by the corresponding full-data evidence. This example refutes the domination step; it does not assert that every such plug-in rule necessarily violates an alpha bound for every model.

For an asynchronous DM comparator, use complete enrollment prefixes or derive an actual infimum over every feasible completed count vector. Do not label a simple lower-score plug-in as an application of the existing partial-betting theorem.

### P2: decisive hierarchy cells do not contain all component guardrails

The `2T+1` cell vector determines net benefit, win/loss/tie probabilities, and signed **decisive-tier** contributions. It generally does not determine the marginal success or safety contrasts needed for component guardrails. For example, when safety is the first tier and A wins on safety, A can either succeed or fail relative to B without changing the decisive hierarchy cell. The same cell law can therefore accompany different success-difference targets.

One confidence set over these cells is simultaneous for functionals of these cells only. A simultaneous set for all required guardrails needs a categorical representation retaining the whole joint score vector, or separate confidence sequences with explicitly allocated simultaneous error. Separate ternary tests at alpha can instead control a stationary conjunction by intersection–union reasoning, but that is a different guarantee from a single simultaneous confidence region.

### P2: model assumptions must remain narrower than the existing mean-only betting guarantee

The checked DM argument assumes iid categorical records, or another explicitly proved condition giving the same likelihood-ratio control for a fixed categorical probability vector. The module introduction's statement that independent pairs imply multinomial counts omits the identical-distribution condition. A constant conditional **mean** score does not imply a constant win/tie/loss probability vector. No proof in this module extends the DM comparator to the existing manuscript's entire mean-only conditional-null class, adaptive HT scores, or drift targets.

This audit did not establish a counterexample to every possible broader DM validity claim; it found that such a broader claim is unsupported by the supplied proof and cited construction. Restricting a baseline to the explicitly iid simulation is sufficient. In particular, do not enter fractional HT weights into these categorical counts and retain the same proof.

At simplex boundaries, a positive full-support Dirichlet mixture divided by a boundary-null likelihood is generally a nonnegative **supermartingale**, not a mean-one martingale: prior alternatives can assign mass to impossible null categories. That still supplies the required upper error bound, with the usual zero-count conventions. The documentation can state this carefully rather than excluding deterministic laws.

### P2: contributed offline routines should not replace the audited public-data analysis

Location: `src/wincs.py:342` and `src/wincs.py:409`.

`task_level_scores(..., pairing='all')` describes all cross-comparisons as unbiased for an independent-run target. This requires independence between the systems' replicate sets. With common coupled seeds, the diagonal terms target the coupled law and the all-pairs mean has the finite-R mixture already proved in the manuscript. Off-diagonal eligibility also requires at least two usable seed clusters and a verified matching of seed identities; positional indices alone are not seed provenance.

The ratio bootstrap removes all infinite log ratios before taking percentiles. That is a conditional bootstrap among defined finite ratios, not the advertised ordinary percentile interval. For example:

```python
task_bootstrap([.5,.5,.5], [0,.5,0], n_boot=10000, seed=0)
# wr_ci: (1.0, 3.0); frac_wr_undefined: 0.2914
```

Here 29.14% of bootstrap draws have positive wins and zero losses, hence infinite win ratios. An extended-real upper 97.5th percentile is infinite, whereas the returned upper endpoint is three. Reporting the omitted fraction is useful but does not turn the conditional finite interval into an unconditional percentile interval. Weighted bootstrap/cluster covariance also needs its own target and sampling-design justification before use with fixed domain weights.

The point-functionals helper additionally reports an infinite win ratio for all ties, where the ratio is `0/0` and should be marked undefined. None of these offline issues affects the separately audited public analysis unless this contributed implementation replaces it.

## Independent checks of the isolated ternary path

The constrained likelihood uses `pl=u`, `pw=u+c`, `pt=1-2u-c`, with feasible interval `max(0,-c) <= u <= (1-c)/2`. Differentiation gives the quadratic coefficients implemented in the source. The routine checks both roots and endpoints; the composite null uses the unconstrained MLE if feasible and the boundary otherwise. Consequently its mathematical value is the mixture likelihood divided by the maximum null likelihood. Under each fixed iid null probability vector, it is pointwise bounded by that vector's mixture likelihood ratio. This supplies the standard composite-null e-process guarantee without requiring the infimum itself to be a martingale.

I compared the closed form against an independent one-dimensional constrained optimization with explicit endpoint evaluation in **4,395 cases**. These included every count vector up to total count 12 at nine thresholds spanning `[-1,1]`, plus 300 random sparse/interior vectors with counts up to 100,000. There were no discrepancies above `1e-5`; the largest absolute log-likelihood difference was `5.56e-7`, at a case with nearly 100,000 observations where the numerical reference itself has finite precision. Zero observations and all-win, all-tie, and all-loss boundaries behaved as expected in the isolated ternary calculation.

Exact enumeration of first-crossing probability through 20 observations, at alpha 0.05, gave:

| iid probabilities (win, tie, loss) | Null threshold | Exact crossing probability |
|---|---:|---:|
| (0.1, 0.8, 0.1) | 0 | 0.00000272777 |
| (0, 1, 0) | 0 | 0 |
| (0.2, 0.5, 0.3) | -0.1 | 0.00167484 |
| (0, 0, 1) | -1 | 0 |
| (0.5, 0, 0.5) | 0 | 0.000761032 |

These are implementation checks, not a substitute for the likelihood-ratio proof or an exhaustive power/coverage study. The existing contributed tests were read; the root had already run them, so this audit concentrated on untested boundaries and integration assumptions rather than repeating the same test suite.

## Recommended integration path

1. Keep the generic projected bounds out of inferential results until the P1 optimizer defect is repaired and reviewed.
2. If an additional complete-data iid comparator is scientifically useful, freeze its prior and use the isolated ternary composite test with verified integer counts, explicitly stating its narrower model and error guarantee.
3. For simultaneous guardrail inference, decide first whether to construct one augmented joint categorical set or several separately budgeted sets. Do not identify component effects from decisive-tier cells.
4. For asynchronous comparison, preserve complete prefixes or implement a separately proved feasible-completion infimum; the existing positive-betting lower-score shortcut is invalid for this DM statistic.
5. Describe this as an established likelihood-mixture comparator. No uniform improvement in interval width, power, or stopping time over the current betting method has been proved or measured by this audit.

Until those decisions are resolved, this module is useful contributed development code, not a validated stronger simultaneous-CS baseline for the submission.

## Addendum: upstream additions at commit `168e7be`

After the initial audit, a nonoverlapping upstream update added betting-capital and inversion helpers. The current `wincs.py` SHA-256 is `714b21fe041b7fbe62b21f6a91c301e22e9fe4c1b492161505ecdf4b3ea292a4`, at git revision `168e7be434ca9116906448645f8e31e867dc9215`. The original four ternary numerical routines and the faulty `linear_bound` are unchanged. The deterministic three-win exclusion was reproduced again after the update.

For an exact function-level pin, the AST hashes, excluding source-position metadata but retaining docstrings, are:

- `linear_bound`: `5ba659b2543cac9225231b98f8fefd51eeee10e4c4af609ae4c2d4c69934cafb`.
- `ternary_constrained_loglik`: `4d86c8fdd52eff96887ffee839db8974ab5bce7f2e04d3c5595d0dae448d6752`.
- `ternary_log_eprocess_nb`: `2bdef5c8764e138f6a5c18991590c2e827f15a6e8a2acb34d24444e459a08dbd`.

**Exclude the contributed confidence-width results.** `experiments/run_online_methods.py` uses the defective generic projection in `width_study`. Its local two-sided betting routine computes `max(logKplus,logKminus) + log(.5) + log(2)`, cancelling the allocation factor. The new `wincs.py` helpers likewise return the unweighted maximum. A maximum of two unit-initialized e-processes is not generally a unit-initialized e-process: with one fair ternary ±1 observation and a single stake 0.5, its expected capital is 1.5. Standard two-sided hedging needs, for example, half the maximum with its associated alpha bound or the average of the two capitals. The present construction gives at best the elementary two-alpha union bound, not the claimed alpha guarantee.

The local width routine also returns the first and last **inside** grid points, making a discrete inner approximation rather than a conservative enclosure of the continuous confidence set. Endpoint terms can evaluate as `0 * log(0)` and propagate NaNs into its mixture. The newly added general inversion refines boundaries but still returns inner-side endpoints and can miss a narrow nonempty interval between coarse grid points. These are additional reasons to quarantine `cs_width.csv`; fixing only the generic DM projector would not validate that table.

The **complete-data decision path** in `run_online_methods.py` is separate. It uses the already checked generator, existing one-sided positive-betting implementation, and the isolated ternary DM composite test, with current-look conjunction across raw success/safety component scores. It does not call the projector or the width functions. The eight scenarios use the six original mechanisms plus two explicitly retrospective tie-heavy extensions. Their comparison is suitable for a separate reproduction under their stated iid model, not a simultaneous-CS width claim.

On the root's subsequent request, only the validated numerical formulas were extracted into a new `src/ternary_dm.py`, with an additional input-checked entry point. A new `experiments/reproduce_dm_baseline.py` reproduces the eight complete-data scenarios without importing `wincs.py` or the width routine. Before the full rerun, 25,000 isolated ternary outputs matched the contributed routine exactly across five boundary/interior thresholds, input validation checks passed, and all eight methods' decision arrays matched the contributed evaluator on a shared test batch. The original source and its existing results remain untouched. See `evidence/dm_baseline.md` and `results/dm_baseline_reproduction_check.json` for the final execution status; extraction is not blanket approval of the contributed module.
