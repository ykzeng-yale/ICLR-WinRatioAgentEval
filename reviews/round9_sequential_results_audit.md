# PR 7 sequential-results audit

Reviewed head: `cfc1850ce9cb0e4ec3e83e4b75836e284f421217`; comparison head: `0b382a9`. Review uses committed blobs, not a checkout. This reviewer contributed the manuscript's theory and round-8 review. No full study was rerun, no model/API calls were made, and no source or Git state was changed. Only this report was written.

**Verdict: PASS for the previously missing experiment execution and comparator alignment; NEEDS WORDING CORRECTIONS before publication.** No additional full simulation is required to support the narrow, descriptive comparison now available. The new results resolve the margin-boundary gap and reveal finite-sample limitations of the asymptotic rules. They do not establish uniform calibration across outcome laws.

## What is now verified

- The calibration source contains four scenarios, each with **10,000 replicates and 10,000 records per arm**: the two net-benefit boundary nulls, success difference −0.03, and compliance difference −0.01. Parameters, seed indices 100/106/108/109, completion logs, and manifest timing agree. The other two targets are favorable in each guardrail-boundary scenario. The retained artifacts support that these runs were executed; this audit did not independently regenerate their random trajectories.
- The main results have **160 rows: 20 methods/conventions × 8 scenarios**, each with 2,000 replicates. Calibration has **164 rows: 41 × 4**, including 21 component-gate rows per scenario. The main gate table has **168 rows: 7 procedures × 3 gates × 8 scenarios**. There are no duplicate scenario/method keys.
- Every saved main/calibration deployment rate and Wilson interval recomputes **exactly** from the integer count and denominator. At a true probability near 0.05, 10,000 replicates give a Monte Carlo standard error of about **0.00218**, or 0.218 percentage points. These are pointwise intervals.
- Both main and calibration source hashes match the reviewed blobs. All four upstream hashes in the main manifest also match: core betting code, generator, online-method runner, and original result CSV. All nine preserved files in `previous_e1ea314/` are byte-identical to the corresponding files at `0b382a9`. The executable AST of `ustat.py` is unchanged; its revisions are documentation. The efficiency and fixed-horizon estimator-check outputs are unchanged.
- Every multi-look method now has explicit **simultaneous** and **retained** guarded rows, including disjoint OBF. The runner implements the advertised conjunctions correctly. Independently comparing six saved fields confirms **16/16 exact reproductions** of the existing win-only and simultaneous guarded betting rows. Retained rows are correctly excluded from that claim. Aggregate retained deployment counts never decrease, and capped mean stopping times never increase, relative to their simultaneous counterparts.
- Both methods consume **2n executions** at a look containing n records per arm. The 10-look group-sequential versus 199-look monitoring distinction is stated. The projection-Gaussian row now states the symmetric-kernel reduction, nondegeneracy, variance consistency, and asymptotic-equivalence interpretation; it explicitly disclaims a finite-sample 5% guarantee starting at n=100 and does not claim to implement Cai et al.'s delayed-start family.

## What the new boundary results actually show

At the success boundary, component-gate rejection rates are 4.83–5.10% for the five Wald/group-sequential procedures, 2.57% for the projection-Gaussian procedure, and 0.81% for betting. The first group is compatible with 5% at this Monte Carlo precision; that is not proof of calibration for all sample sizes or distributions.

At the compliance boundary:

| Procedure | Boundary-gate rejections / 10,000 | Gate rate, pointwise 95% Wilson CI | Simultaneous guarded rate | Retained guarded rate |
|---|---:|---:|---:|---:|
| All-pairs fixed Wald | 551 | 5.51% [5.08%, 5.97%] | 5.50% | Same single look |
| All-pairs OBF | 546 | 5.46% [5.03%, 5.92%] | 5.40% | 5.45% |
| All-pairs Pocock | 643 | 6.43% [5.97%, 6.93%] | 5.09% | 6.43% |
| All-pairs HSD | 567 | 5.67% [5.23%, 6.14%] | 5.23% | 5.66% |
| Projection-Gaussian | 725 | 7.25% [6.76%, 7.77%] | 1.83% | 7.11% |
| Disjoint OBF | 545 | 5.45% [5.02%, 5.91%] | 5.39% | 5.44% |
| Disjoint betting | 76 | 0.76% [0.61%, 0.95%] | 0.31% | 0.72% |

The 7.25% component-gate error is a substantial finite-sample excess. It must not be reported as a 7.25% error rate for the simultaneous guarded rule, whose other gates prevent most of these early deployments. Conversely, the simultaneous rate of 1.83% cannot certify the underlying compliance test as calibrated. Both distinctions are present in the detailed table and must survive manuscript integration.

## Corrections needed; no experiment required for these

1. **Replace binary declarations that methods “hold their level.”** `evidence/ustat_reference_report.md:201–205` and the README classify calibration through pointwise Wilson intervals and state that all six asymptotic procedures fail at the compliance boundary. Use observed rates and uncertainty, with “compatible with 5%” where appropriate. As an exploratory check using the saved counts, one-sided exact binomial tests with Bonferroni adjustment across 28 gate cells retain clear excess for projection-Gaussian and Pocock; HSD is borderline after adjustment (adjusted p≈0.038), while fixed Wald and both OBF estimates do not survive that adjustment. Thus the broad “all six fail” statement is stronger than the multiplicity-aware evidence. The strong Gaussian/Pocock finding does not depend on the borderline cells.
2. **Correct the residual-variance magnitude.** The Zhang–Wu source-mapping row says the omitted term is below 1e−8 at n=100. Using the saved variance components, the residual contribution \((\operatorname{Var}(h)-\sigma_A^2-\sigma_B^2)/100^2\) is approximately **5.9e−6 to 2.5e−5**, not below 1e−8. Describe its order and the actual first-order approximation. This prose error does not alter the already labeled asymptotic implementation.
3. **Separate identical component point estimates from identical estimated variances or stopping times.** At `evidence/ustat_reference_report.md:158,226`, all-pairs and disjoint raw guardrail means are indeed exactly equal. Their sample variance estimates can differ by the empirical cross-arm covariance, so stopping times need not coincide. The report's own numerical stopping means differ. State asymptotic variance equality and near-equal observed guarded stopping in the named scenarios; do not assert general or exact equality.
4. **Qualify the mechanism explanation unless its diagnostics are archived.** Section 4.7 reports first-crossing quantiles and rare-event counts, but the committed runner does not save those diagnostics and no separate diagnostic implementation/output is included in this head. They are not independently reproducible from the aggregate CSV alone. Describe variance underestimation as a plausible explanation, or archive the already-run diagnostic script and output. An oracle-variance or delayed-start ablation would be needed for a stronger attribution or a proposed remedy.

## Exact remaining experimental needs

**Required to close round 8:** none. The boundary runs, complete convention alignment, and existing-row reproduction are done. Do not rerun the eight-scenario or four-scenario studies merely to satisfy this audit.

**Conditional on retaining stronger claims:**

- For the precise diagnostic numbers in §4.7, archive their generating code and results; if unavailable, regenerate only that CPU-only additive compliance-gate diagnostic on the frozen seed stream, or remove those numbers. This is narrower than rerunning the all-pairs study.
- For a claim that a particular delayed start or variance correction fixes the observed excess, prespecify that modification and test it at both guardrail boundaries on an independent seed stream. No such remedy is currently supported or needed for reporting the present negative result.
- For inferential claims about paired differences in stopping time or power, retain per-replicate decisions/stops or paired sufficient summaries and report paired Monte Carlo uncertainty. Current marginal summaries suffice for descriptive comparisons, not significance or equivalence claims. No extra study is needed if those claims are avoided.

No commercial/proprietary-model calls are needed for any of these conditional checks.

## Audit limits and hashes

This is an artifact-consistency and scientific-interpretation audit, not an independent regeneration of 56,000 simulation replicates. Individual stopping-time distributions and their Monte Carlo standard errors cannot be recomputed independently from the saved marginal summaries; the six-field betting reproduction does check those summaries against the existing independent pipeline. Calibration manifests omit separate upstream hashes, although the identical runner hashes and checked main-manifest dependencies identify the shared source set at this commit.

| Reviewed source | SHA-256 |
|---|---|
| `ustat.py` | `ee98a9b344a628fa1dc49d4c314ef9c52252de70aee74316f8d022b93ea58f5d` |
| `run_ustat_reference.py` | `cb96f8a58577dc9980109b5ed6932a64deae1f73005e0adf5b5af703103809e8` |
| `README.md` | `a09512015c083a2182351a576a7411bc99fb5513eedfd31a1933222ccb536307` |
