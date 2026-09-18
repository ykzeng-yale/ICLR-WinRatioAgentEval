# PR 5 projection-fix review

**Recommendation: request changes; do not merge the current certification claim.** The patch fixes the reported deterministic boundary cases, but its default `certify=True` path can still return a nonconservative outer bound for valid finite coefficients. An explicit feasible-point counterexample below establishes the defect without relying on an optimizer.

Reviewed [PR 5](https://github.com/ykzeng-yale/ICLR-WinRatioAgentEval/pull/5), head **`30fda6006a04895a61a785bd415481dac2e64e91`**, using read-only snapshots of `origin/session60/wincs-fix` under `work/pr5_review/`. No checkout, merge, root-source edit, paid API call, or GitHub comment was made. This review concerns `linear_bound`, its changed numerical certificate, and relevant boundary tests. Other contributed confidence-width or asynchronous issues are outside its scope; this report does not endorse their use in the paper.

## Blocking finding: coefficient tie approximation invalidates the outer bound

**Location:** `src/wincs.py`, reviewed lines 154 and 160, with the false outer-bound conclusion and certificate at lines 207–214.

The definition

```python
top = c >= cmax - 1e-12 * max(1.0, abs(cmax))
d = np.where(top, 0.0, cmax - c)
```

replaces distinct sufficiently close coefficients by a tied surrogate in the Lagrangian solution. Yet `point(lam)` evaluates the objective with the original `c` at line 184. Consequently, an iterate outside the likelihood set is a maximizer for a different objective, and its original-objective value need not exceed the original problem's supremum. Normalizing its probabilities does not restore that missing implication. Checking a small gap to an inside iterate on the same surrogate solution path cannot certify a global outer bound for the original objective.

The tolerance also depends on an arbitrary common coefficient offset. A linear functional on the simplex must satisfy shift equivariance: adding a constant to every coefficient adds that same constant to both bounds. Here, a shift changes which coefficients are treated as tied and changes the substantive answer.

### Deterministic reproducer

```python
import numpy as np
from wincs import linear_bound, cs_threshold, loglik

x = np.array([2., 3., 4.])
c = 1e12 + np.array([0., 1., 2.])
prior = np.ones(3)
p = np.array([.04, .12, .84])
upper = linear_bound(x, c, prior, .05)  # default certify=True

assert p.sum() == 1.0
assert loglik(x, p) > cs_threshold(x, prior, .05)
assert c @ p > upper                 # a feasible point exceeds the upper bound
```

Observed values on Python 3.14.4:

| Quantity | Value |
|---|---:|
| Reported upper bound | 1,000,000,000,001.5563 |
| Objective at explicit feasible point | 1,000,000,000,001.7999 |
| Feasible point minus reported bound | 0.24365234375 |
| Feasible-point log likelihood | −13.495955806915786 |
| Confidence-set threshold | −14.141932458731985 |
| Strict likelihood feasibility slack | 0.6459766518161985 |

This discrepancy is materially larger than floating-point spacing at the coefficient scale and does not depend on a point barely meeting the likelihood constraint. The coefficients `[1e12, 1e12 + 1, 1e12 + 2]` are distinct and exactly representable. The unshifted call with coefficients `[0, 1, 2]` returns `1.8280385880679983`, whereas subtracting `1e12` from the shifted call returns `1.5562744140625`. An independently optimized feasible solution from a suitable interior start reaches `1.8280385880679553` for the unshifted objective.

The certificate's relative gap tolerance, `1e-7 * max(1, abs(obj_out))`, is also sensitive to irrelevant common offsets. However, simply tightening that tolerance does not fix the counterexample: both inner and outer iterates can converge to the same suboptimal point of the rounded-coefficient surrogate.

## Checks that passed and their limits

- The new `test_boundary_laws_issue4` passed, including exact all-win/all-loss endpoints, constant functionals, all-tie laws, boundary win-ratio cases, and its 200 sparse-count comparisons against a 601-point-per-axis grid.
- The existing six-case linear/ratio grid comparison passed.
- An independent bounded experiment generated 80 three- or five-cell laws, including sparse counts, random coefficients, varying positive priors, and significance levels 0.01, 0.05 and 0.2. Maximization and minimization produced 160 projection calls. Separate SLSQP searches produced 148 likelihood-feasible candidates under a `1e-8` feasibility tolerance; 146 optimizer runs reported success. No feasible candidate exceeded its reported outer bound by more than `1e-7` for these ordinary-scale coefficients. The maximum recorded excess was approximately `4.6e-12`.
- SLSQP success and grid containment do not prove global optimality or an exact conservative numerical certificate. Failed or infeasible optimizer runs were recorded rather than counted as successful validation. The explicit counterexample above is stronger evidence because it supplies a strictly feasible probability vector directly.
- Shift and scale probes expose the large-offset failure; they are diagnostic checks of equivariance, not new scientific experiments. Cases where input differences themselves fall below floating-point spacing are not used as counterexamples.

The bounded script, output, checked source hashes, all optimizer records, and the counterexample are preserved in `work/pr5_review/run_projection_checks.py`, `checks.log`, `independent_projection_checks.json`, and `snapshot.json`.

## Required correction and validation

1. **Preserve the original objective.** Use exact coefficient equality for genuinely tied maximizers, or explicitly propagate a proved coefficient-approximation error into the returned outer bound. Center and scale a nonconstant coefficient vector using its spread before numerical optimization, then transform the bound back. Handle exactly constant vectors separately. Tolerances must not grow with an irrelevant common offset.
2. **Certify an upper bound, not only proximity of two points.** A primal feasible point certifies a lower bound for a maximization problem. Pair it with a valid dual upper bound for the original coefficients and report a scale-aware primal–dual gap. For example, for positive `lambda` and a dual `nu` satisfying `nu >= max(c)` and strict inequality on positive-count coordinates, the simplex Lagrangian gives an analytic dual upper bound; this can remain valid even if the candidate probabilities do not normalize exactly. If the implementation instead relies on the exact Lagrangian path, it must preserve the coefficients and bound numerical error before claiming conservative reporting.
3. **Add this strictly feasible counterexample as a containment test**, and add shift/positive-scale equivariance tests for both minimization and maximization, sparse counts, genuinely tied faces, and distinct near-tied coefficients. Keep the deterministic boundary regressions. A certificate must either return a conservative value within its documented numerical tolerance or fail closed; it must not silently certify this violated bound.

The patch is a useful improvement for the original boundary-law failure. Its current general-purpose outer-bound guarantee is nevertheless false, so the merge recommendation remains **request changes** until the reproducer is corrected and the strengthened certificate is reviewed.
