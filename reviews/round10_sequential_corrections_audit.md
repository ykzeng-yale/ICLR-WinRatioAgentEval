# Round 10: PR 7 correction closure and fixed-stake drift note

Reviewed frozen head: `ac17f5901bcf4efba6c71e970d3a4c1cf1ed06cb`, against `cfc1850ce9cb0e4ec3e83e4b75836e284f421217`. Scope: round-9 corrections, archived compliance diagnostic, and the separately requested algebra check below. This reviewer contributed earlier project theory and reviews. No contributed/manuscript source, baseline result, or Git state was modified. No model/API calls were made.

**PASS: all four round-9 corrections are substantively closed.** The archived diagnostic was independently rerun with frozen dependencies and reproduced byte-for-byte. There is no required additional experiment for the existing descriptive claims. The 56,000-replicate main/calibration studies were not rerun.

## Closure evidence

| Round-9 issue | Verified correction | Status |
|---|---|---|
| Binary calibration verdicts and multiplicity | Report and README now give observed rates, pointwise Wilson intervals, and Monte Carlo precision; the 28-cell binomial adjustment is explicitly exploratory. Modest OBF/Wald deviations are not presented as established failures. | Closed |
| Component versus guarded error events | Three separate columns identify component rejection, simultaneous guarded deployment, and retained-crossing guarded deployment; the text explicitly distinguishes 725, 183, and 711 events out of 10,000 for the projection-Gaussian rule. | Closed |
| Residual variance magnitude and exact guardrail equivalence | The finite-N correction and its scale are corrected. Component point estimates remain identical, while finite-sample variance estimates and stopping times are correctly allowed to differ. | Closed |
| Unarchived first-crossing diagnostics and mechanism claims | New diagnostic script, 3,653-row CSV, and manifest are present; the unsafe-regression details without archived diagnostics were removed. Variance underestimation is described as consistent with the data, not as proven causation or a tested remedy. | Closed |

The only changes from the previous head are the two documentation files and three new diagnostic artifacts. **All 19 pre-existing result artifacts under `results/ustat_reference/` are byte-identical to the prior head**, including the preserved `previous_e1ea314/` baseline. The main runner, core U-statistic implementation, and existing simulation/calibration outputs are unchanged.

### Independent bounded rerun

I extracted the exact committed diagnostic and its dependencies into an isolated directory under `work/round10_pr7_audit/frozen/`, copied the frozen calibration CSV there, and ran the archived script without modification. It used the prescribed 10,000 replicates, 10,000 records per arm, batch size 25, and seed entropy `[20260918,109]`, computing only the additive compliance gate. The rerun took approximately 11 seconds using Python 3.14.4, NumPy 2.4.1, and SciPy 1.17.0. The contributed run used Python 3.12.13; that version difference did not change the CSV.

**Rerun and committed CSV SHA-256 both equal** `017d47dbab2813e91f59c52c3810adfb2bcc1e448b7010581e574aef34616199`.

All seven component-gate counts match the frozen calibration table: projection-Gaussian 725, fixed Wald 551, all-pairs OBF 546, Pocock 643, HSD 567, disjoint OBF 545, and betting 76. All 3,653 `(rule, replicate)` keys are unique. Every archived first-crossing quantile, early-crossing count/share, zero-event count, arm-count median, and median variance estimate recomputes exactly from the CSV. All three source hashes, the core dependency hash, and the output hash match their manifest.

For the 725 projection-Gaussian rejections, the audit independently confirmed:

- 410 first cross by 500 records per arm; 540 by 1,000; median first crossing is 400.
- 239 have zero noncompliant A records at first crossing.
- 675 have estimated variance below the true fixed-n variance evaluated at their crossing n; variance-ratio quartiles are 0.2532, 0.5431, and 0.8004.

These are descriptions conditional on rejection. Selection at a rejection time is itself relevant to the variance-ratio pattern; the diagnostic does not establish an unconditional variance bias or a causal attribution. The revised text's qualified interpretation is appropriate.

### Residual variance calculation

From the unchanged saved Monte Carlo components, the population-form residual term

\[
\{\operatorname{Var}(h)-\sigma_A^2-\sigma_B^2\}/n^2
\]

at n=100 ranges from **5.936923e−6 to 2.492400e−5**. The retained first-order variance ranges from **0.004407307 to 0.006910433**. The omitted term is **0.13247%–0.40631%** of that first-order term. The revised 0.13%–0.41% statement is correct. At n=1,000 the absolute residual is 100 times smaller and its relative size ten times smaller. These calculations describe population-form variance components estimated by the separate efficiency Monte Carlo; they are not a claim that the empirical projection variance estimator has that exact finite-sample bias.

## Integration-safe numerical claims and table

**Keep the studies separate.** PR 7 is the matched-budget comparison using seed **20260918**. Its 16/16 reproduction matches are against **`results/online_methods_results.csv`**, not the primary **`results/simulation_results.csv`** generated with seed **20260917**. For example, the matched-comparison simultaneous betting null/efficiency rates are 0.0060/0.9660, while the primary study reports 0.0045/0.9685. Both can stand with explicit study labels; do not silently substitute rows across them.

For a compact rare-compliance table, the following rows are safe to integrate; every denominator is 10,000 replicates, and intervals are pointwise 95% Wilson intervals. All methods use the same execution budget, with n records per arm meaning 2n executions.

| Rule and looks | Component compliance-gate error | Simultaneous guarded deployment | Retained guarded deployment |
|---|---:|---:|---:|
| All-pairs OBF, 10 planned looks | 5.46% [5.03%, 5.92%] | 5.40% [4.97%, 5.86%] | 5.45% [5.02%, 5.91%] |
| Projection-Gaussian AsympCS, 199 looks | 7.25% [6.76%, 7.77%] | 1.83% [1.59%, 2.11%] | 7.11% [6.62%, 7.63%] |
| Fixed-grid disjoint betting, 199 looks | 0.76% [0.61%, 0.95%] | 0.31% [0.22%, 0.44%] | 0.72% [0.57%, 0.91%] |

Suggested claim: “At the rare-compliance boundary, projection-Gaussian monitoring produced a 7.25% component-gate rejection rate, while simultaneous guarded deployment occurred in 1.83% of replicates. The corresponding betting rates were 0.76% and 0.31%; the Gaussian procedure has an asymptotic guarantee, so its finite-sample component excess does not contradict that guarantee.” The full appendix can retain all seven rules, including the Pocock component rate of 6.43% [5.97%, 6.93%].

For the efficiency comparison, it is safe to report the **estimated asymptotic variance ratio of approximately 1.13–1.41** in these eight scenarios at equal execution budgets, and the observed same-OBF stopping means in the named scenarios. Avoid general stopping-time equivalence, statistical equivalence claims, or an attribution of the entire power gap to pairing: the boundaries and validity guarantees also differ.

### Exact integration files and dependencies

All paths below are repository-relative at the reviewed frozen commit:

- Main matched-comparison rows: `results/ustat_reference/ustat_reference_results.csv`; scenario/seed/look/source metadata: `results/ustat_reference/manifest.json`.
- Boundary table: `results/ustat_reference/null_calibration.csv`; its metadata: `results/ustat_reference/calibration_manifest.json`.
- Existing-row reproduction: `results/ustat_reference/ustat_reference_reproduction_check.json`, whose comparison source is `results/online_methods_results.csv`.
- Efficiency and estimator checks: `results/ustat_reference/ustat_reference_efficiency.csv`, `results/ustat_reference/ustat_reference_estimator_check.csv`, and `results/ustat_reference/ustat_reference_gate_rates.csv`.
- Diagnostic records and provenance: `results/ustat_reference/rare_event_diagnostic.csv`, `results/ustat_reference/rare_event_diagnostic_manifest.json`.
- Reproduction entry points: `experiments/ustat_reference/run_ustat_reference.py` and `experiments/ustat_reference/rare_event_diagnostic.py`, with `experiments/ustat_reference/ustat.py` and `src/winstats.py`. The main runner additionally imports `experiments/run_simulations.py` and `experiments/run_online_methods.py`; the narrow diagnostic does not import either, but reads/hashes the frozen main runner and checks `null_calibration.csv` in its output directory. Dependencies are Python, NumPy, and SciPy; no external model service is involved.
- Corrected interpretation: `evidence/ustat_reference_report.md` and `experiments/ustat_reference/README.md`.

Audit scratch evidence: `work/round10_pr7_audit/rerun_check.json`, `artifact_checks.json`, `diagnostic_stdout.log`, `diagnostic_stderr.log`, and the isolated frozen tree. These are audit intermediates, not required paper deliverables.

**Remaining requirements for these claims:** none beyond ordinary manuscript/table integration and preserving these distinctions. A delayed-start or oracle-variance experiment is needed only if a remedy or stronger mechanism claim is newly proposed. A paired stopping-time inference requires paired summaries only if an inferential comparison is newly proposed.

## Separate requested check: fixed-stake running-mean guarantee

This is an algebraic verification of the root's conjecture, not a novelty claim or an edit to PR 10.

Let \(X_i\) be adapted and integrable with \(\mu_i=E[X_i\mid\mathcal F_{i-1}]\). Fix a threshold c, nonnegative stakes \(\lambda_k\), and fixed weights \(w_k\ge0\), \(\sum_k w_k=1\). Assume all factors below are strictly positive. For the actual bounded scores \(X_i\in[-1,1]\), \(-1<c<1\) and \(0\le\lambda_k<1/(1+c)\) suffice. Define

\[
E_n=\sum_k w_k\prod_{i=1}^n\{1+\lambda_k(X_i-c)\},\quad
M_{k,n}=\prod_{i=1}^n\frac{1+\lambda_k(X_i-c)}{1+\lambda_k(\mu_i-c)}.
\]

Each \(M_{k,n}\) is a nonnegative martingale starting at one, since its next multiplicative factor has conditional expectation one. Thus \(M_n=\sum_k w_kM_{k,n}\) is also such a martingale. With

\[
D_{k,n}=\prod_{i=1}^n\{1+\lambda_k(\mu_i-c)\},
\]

the inequality \(\log(1+x)\le x\) gives

\[
\sum_{i=1}^n(\mu_i-c)\le0
\quad\Longrightarrow\quad
D_{k,n}\le\exp\!\left\{\lambda_k\sum_{i=1}^n(\mu_i-c)\right\}\le1.
\]

On those running-null times, \(E_n\le M_n\). Pathwise event containment and Ville's inequality therefore yield the precise finite-sample statement

\[
\Pr\!\left\{\exists n\ge1:\frac1n\sum_{i=1}^n\mu_i\le c, E_n\ge1/\alpha\right\}\le\alpha.
\]

**The conjecture is valid and adds a useful guarantee for the existing fixed-grid betting rule.** No constant-mean assumption or pointwise condition \(\mu_i\le c\) is needed. The observed wealth need not itself be a supermartingale under drifting means; domination is required only at running-null times.

For J+1 current-prefix gates, allocate levels \(\alpha_j\) with \(\sum_j\alpha_j\le\alpha\). A deployment at a prefix where any running target violates its fixed threshold requires one of those gate-specific false crossings; the union bound therefore handles a switching violated gate. The same argument covers selection among multiple candidate prefixes if all gates certify the **same selected prefix**, and valid partial lower-wealth bounds may be substituted by their established pathwise domination.

Caveats:

- Stakes must remain constant over observations within each mixture component. Predictably changing stakes only bound a **stake-weighted** drift sum, whose sign need not match the unweighted running mean. Even deterministic time-varying stakes can break the asserted argument.
- Mixture weights and thresholds are fixed in advance (or fixed conditional on initial information included in the filtration). Post hoc threshold or weight selection is not covered.
- Retaining a gate's earlier crossing does not certify that gate's **current** running target under drift. Use same-current-prefix evidence for the switching-violation guarantee.
- This is a fixed-threshold error guarantee. It does not automatically establish an inverted confidence sequence evaluated at a random or time-varying threshold.
- Conditional means refer to the specified full-score filtration. Adaptive sampling, interference, or delayed observations must still satisfy the score/filtration assumptions; the calculation does not create identification or repair invalid completion bounds.

The actual frozen implementation at `src/winstats.py:64–81` uses constant positive stakes and uniform weights, so the argument applies to its valid ternary score streams. Its old lines 68–69 disclaim drifting running-average testing too broadly; if the new result is integrated, that wording needs a scoped update by the source owner. No source was changed in this review.

### Check of the root's integrated TeX

After the preceding audit, the root added `prop:bet_running` and extended `thm:drift_gate` in the working `paper/theory.tex`. I read the exact statements, proof, preceding stake/threshold definitions, and retention caveat. The checked file's SHA-256 was `5c26b6718fad6fb951f89bb2506d470b3ba125be44ab17c65b53ced65363f99c`.

The proposition, normalization proof, fixed-threshold event, and current-prefix union argument match the verified result. The fixed-violating-index alternative is also correct. No random/time-varying-threshold confidence-sequence claim is introduced, and retained historical evidence is correctly excluded from the drifting conjunction.

One scope clarification was sent to the root: the betting sentence in `thm:drift_gate` should explicitly invoke the assumptions of `prop:bet_running`. The generic gate setup earlier permits HT scores whose range can exceed [-1,1] when allocation probabilities differ from one half; the proposition's displayed stake range is calibrated for [-1,1]. Adding “under Proposition~\ref{prop:bet_running}” prevents an unintended reading that the same unscaled stakes apply to every such HT score. No other mathematical correction was identified. This clarification concerns the new root integration, not the already closed PR 7 corrections.
