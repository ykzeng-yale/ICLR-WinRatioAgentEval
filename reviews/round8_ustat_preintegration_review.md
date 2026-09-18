# All-pairs comparator: pre-integration scientific review

Audited commit: `e1ea314578a6f15dd2ee48ba64ed95a15a426354`. Files were read using `git show`; no checkout, source edit, Git mutation, or claimed experiment was performed. Only this report was written. This reviewer contributed the manuscript's theory and earlier comparator reviews, so this is an independent review of the contributed implementation, not an independent review of the whole paper.

**Verdict:** the core all-pairs estimator and projection variance appear suitable for an explicitly asymptotic, complete-data reference comparison under the frozen independent-arm generator. No blocking estimator formula error was found. Before treating its rows as validated paper results, resolve the inference-description and comparison-semantic issues below and obtain the missing results/provenance. The present review does not certify the claimed Monte Carlo findings.

## Prioritized findings

### P2 — State the actual AsympCS guarantee and supply the two-arm reduction

Locations: `ustat.py:37–43,351`; `run_ustat_reference.py:96–103`; `README.md:41–46`.

The current explanation jumps from a first-order Hoeffding representation to an asymptotic confidence-sequence claim. A fixed-time CLT and consistency in probability alone do not justify uniform monitoring. [Waudby-Smith et al., Theorem 2.4](https://arxiv.org/html/2103.06476v9#S2.SS3) requires a suitable strong approximation and compatible almost-sure boundary approximation. Its basic AsympCS definition concerns asymptotic equivalence to an exact CS, not a 5% finite-sample crossing bound from the first implemented look. The runner's fixed tuning and monitoring from 100 also are not literally the delayed-start family in [Cai, Hu, and Li, Theorems 1–3](https://arxiv.org/html/2605.14692#S3).

A concrete repair is available without changing the simulated statistic. Let independent arm records form iid vectors \(X_i=(A_i,B_i)\), and define the symmetric kernel

\[
k(X_i,X_j)=\{h(A_i,B_j)+h(A_j,B_i)\}/2.
\]

Its one-sample order-two statistic \(U_n^*\) has the product-law target. With \(D_n=n^{-1}\sum_i h(A_i,B_i)\),

\[
U_n=(1-1/n)U_n^*+D_n/n,\qquad |U_n-U_n^*|\le 2/n.
\]

Writing \(a(A)=E_Bh(A,B)-\theta\) and \(b(B)=E_Ah(A,B)-\theta\), the first projection of \(k\) is \(\{a(A)+b(B)\}/2\). Independent arms therefore give linear-term variance \(\sigma_A^2+\sigma_B^2\), as implemented. Boundedness supplies the moment conditions in Cai et al.'s strong approximation; positive projection variance is also necessary for that nondegenerate route. The implemented row/column variance estimator must be identified as strongly consistent; its component second moments are bounded multi-sample averages with repeated-index terms of vanishing order. These facts, together with the general Gaussian-boundary recipe, support the weaker fixed-tuning AsympCS interpretation. This is a repair route assessed here, not a full new theorem or a verification of the present README's abbreviated argument.

The frozen scenarios are nondegenerate. Do not extend the label to arbitrary degenerate kernels, dependent paired seeds, drifting arm laws, or adaptively selected records. The `V>0` check is a conservative numerical convention, not a theorem for degenerate U-statistics. Either provide the reduction and precise guarantee or label this row as a projection-based Gaussian monitoring reference pending justification. This finding is not a counterexample showing that the frozen implementation is mathematically invalid.

### P2 — The primary guarded betting row is a different decision rule from the existing paper row

Locations: `run_ustat_reference.py:90,102,115,117–121`; `README.md:50`.

The primary rules retain each gate's first crossing, then deploy once all three gates have crossed, possibly at different looks. The original paper requires all three gates to cross at the same look. Thus the blanket claim that the recomputed guarded betting row is bit-identical to existing results is not established by generator identity. The explicitly named `guarded_disjoint_betting_simultaneous` is the appropriate row for that reproduction check. A simple gate pattern—one gate passes only at look 1, another only at look 2—distinguishes the rules.

Both conventions admit the stationary intersection-union argument: under a fixed violating gate, any deployment requires that gate's erroneous rejection. The discrepancy is comparison scope, not an automatic type-I error violation. The all-pairs and disjoint OBF primary rows both retain previous gate crossings and therefore do isolate pairing design under that convention. For comparisons against the original paper, use matching simultaneous rows and explain the 10-look versus 199-look monitoring difference. There is no simultaneous disjoint OBF row in this commit.

### P2 — The provided calibration mode does not examine guardrail-boundary nulls

Location: `run_ustat_reference.py:169–172`.

`--calibration-only` includes `null` and `tie_heavy_null`. Their net-benefit null is relevant, but raw success and compliance differences are zero, strictly above their negative noninferiority thresholds. Consequently those runs cannot validate finite-sample approximation quality at either guardrail boundary. The existing regression scenarios are strictly beyond the respective boundary and do not replace a boundary check. Before a claim about calibrated guarded deployment, examine or explicitly leave unresolved cases with success difference −0.03 or compliance difference −0.01 while the remaining gates are comfortably satisfied. No new experiment was run in this review.

### P3 — Qualify “independent increments” as a Gaussian-limit statement

Locations: `ustat.py:35–36`; `README.md:39–40`.

[Bergemann and Hanson, Proposition 1](https://arxiv.org/html/2601.22525#S3.SS1) establishes the nested win-difference covariance identity with unchanged subject-level endpoints. [Zhang and Wu, §3.1](https://arxiv.org/html/2410.06281v1#S3.SS1) establishes joint asymptotic normality via projection under growing stage sample sizes. Covariance structure alone does not imply independent Gaussian increments for the finite-sample nonlinear statistic. The current global asymptotic disclaimer is helpful; the local sentence should state canonical covariance/asymptotic independent increments.

For the frozen iid balanced design with positive projection variance and fixed 10-look proportions, information fraction \(n_k/N\) is the correct first-order limit. It is not an exact finite-sample information fraction including the residual \(1/n^2\) term. The implementation is consistent with the asymptotic interpretation.

## Checks that passed

- **Target and execution budget.** The copied generator has the same outcome draws and score construction as the existing generator. Independent arm records make every cross pair target \(F_A\otimes F_B\), including the diagonal. Each look uses \(n\) observations per arm, or \(2n\) executions, for both methods. There is no factor-of-two efficiency normalization error here. This argument does not transfer to paired-seed public archives.
- **Hierarchy and score orientation.** Categories preserve compliance, then success; cost is used only for two compliant successful records. Joint noncompliance can still be separated by success, as in the original generator. The column conditional mean reverses the B-oriented sign correctly. Sorting all costs is a computational index; prefix masks remove later observations' contributions.
- **Projection variance.** `zeta10/n + zeta01/n` is the correct first-order variance. It is not the exact finite-N variance, which also contains the residual component. Calling it a projection estimate is accurate. Raw success/compliance all-pairs means equal arm-mean differences, as required.
- **Small deterministic oracle.** Sixteen fixed records per arm spanning every binary outcome category, checked at prefixes 2, 3, 5, 8, and 16, gave exactly zero discrepancies for U, win/loss probabilities, and both sample projection variances against the explicit kernel matrix. This is not a Monte Carlo performance study or an exhaustive floating-point boundary audit.
- **Normal-mixture algebra.** At variance indices 100, 1000, and 10000, substituting the computed boundary into its half-normal mixture gave 20 with absolute error below \(2.0\times10^{-12}\). This verifies the Gaussian boundary calculation; replacing Gaussian scores by estimated-variance U-statistics still needs the asymptotic argument above.
- **Spending recursion.** For two planned looks at fractions 0.5 and 1, independent one-dimensional adaptive quadrature of the bivariate-normal crossing probability agreed with 0.05 within \(7.4\times10^{-13}\) for OBF-type, Pocock-type, and HSD spending. Each spending function ends at alpha. This supports the recurrence on a small case; the full 10-look grid accuracy and reported external boundary vector were not independently source-verified here.

## Provenance and unresolved verification

SHA-256 of the exact reviewed blobs:

| File | SHA-256 |
|---|---|
| `ustat.py` | `8be5638fb709992a4fd44f4eb4f9053296b57ce1348cec7e5a6ba2c22a35fd0a` |
| `run_ustat_reference.py` | `aaa91835f377ac54d2e4256c34ea42dd49272ead89c4e4d3faf05ded7dc6a392` |
| `README.md` | `14435174f61bed35b6eaee8fd4435c264b34ab6928128f93962b331d55b502d7` |

No result table, full-study log, boundary-validation output, or asserted bit-identical result reproduction was certified. The original Bebu–Lachin, Sen, Lan–DeMets, and Armitage–McPherson–Rowe source texts were not reopened in this bounded review; projection scaling and recursion were checked directly, while the sequential and AsympCS claims were checked against the primary sources linked above. Reported CPU/memory costs, all-eight-scenario calibration, and finite-sample stopping performance remain unverified.
