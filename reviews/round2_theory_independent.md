# Round 2: independent mathematical and numerical review

Review completed: 2026-09-18 UTC. Reviewer: a separate model-assisted reviewer that did not author the reviewed theory or experiment code. This is an internal adversarial check, not human peer review, formal proof verification, or certification of submission readiness. The Fan paper-review skill informed the focus on verified, actionable claims and explicit scope.

**Assessment.** The central conditional-randomization identity, normal-mixture confidence sequence, bounded-mean betting test, stationary intersection–union argument, drifting simultaneous-confidence argument, seed-coupling identity, and information lower bound are mathematically sound under the assumptions identified below. I found two material specification issues: the offline theorem does not explicitly state the full cross-task independence it uses, and the theoretical betting deployment rule retains historical crossings while the empirical implementation requires simultaneous current crossings. Neither finding shows that the reported stationary simulations violate their error guarantee. Both should be reconciled before submission.

All 36 initial simulation result rows and all 17 stress-test result rows were reproduced in memory using the current code, without changing source files or result artifacts. Additional independent invariant and martingale stress checks passed. These checks establish numerical reproducibility and targeted agreement, not universal empirical calibration.

## 1. Material findings sent to the integrating author

### R2.1 — State independence of complete task records, and scope the CLT accordingly

**Location:** `paper/theory.tex`, originally lines 533–575, Theorem “Task-level estimation and inference.”

The setup explicitly calls the task contexts `X_i` i.i.d. and describes independent arm replicate sets conditional on each task. The variance proof then uses independence of the complete task scores `T_i`; the CLT uses i.i.d. complete records. I.i.d. contexts alone do not ensure either condition. The sentence requiring the complete records to be “identically distributed” does not itself require their independence, and the later CLT condition should explicitly retain that identical-distribution condition.

**Counterexample to the incomplete interpretation:** Let every context be constant, hence i.i.d. Let all A-task outcomes share the same fair Rademacher variable `H`, and let every B outcome be zero, with a single sign comparator. Within each task the A and constant B outcomes are independent, but every `T_i=H`. The unconditional target is zero and `Var(mean(T_i))=1`, not `1/n`. At 10,000 tasks the reported normal-mixture radius is approximately 0.03273, and the interval centered at `H` never covers zero. The bounded-score theorem remains valid for the *conditional* running target; what fails is identifying that target with the unconditional task population mean under cross-task dependence.

**Required correction:** Explicitly require independence of the complete task-and-replication records across `i`. Counts determined from baseline task information may vary if the unbiasedness and conditional-mean conditions are retained. State the variance simplification and ordinary studentized CLT under i.i.d. complete records; otherwise use the unsimplified sum of task variances and do not assert the displayed i.i.d. limit without additional conditions. Keep the existing larger-cluster and fixed-benchmark cautions.

**Priority:** Material assumption clarification; the intended independent-task design is repairable by precise wording. No contrary result was found under that intended design.

### R2.2 — Align the empirical gate rule with the theory

**Location:** `paper/theory.tex`, originally lines 419–421; `experiments/run_simulations.py`, lines 73 and 82.

The appendix defines stationary betting deployment by requiring each process to have crossed at some past time, using `sup_{t<=n} E_jt`. The code uses `logical_and.reduce(all_e)` at the current look, then asks whether this conjunction was ever true. Thus a gate whose e-value previously crossed but later fell below the threshold is not retained in the simulation.

Both rules have the stated stationary intersection–union type-I guarantee: a false deployment necessarily entails a crossing of one fixed true component null. They can nevertheless have different power and stopping-time distributions. The retained-crossing version can deploy earlier and more often, so the distinction matters to empirical interpretation.

**Required correction:** Describe current-look conjunction as the rule used for all reported simulation numbers. The retained-crossing rule may be stated separately as an optional stationary variant with the same validity guarantee. Do not silently replace the code with the retained rule while keeping the old results.

**Priority:** Material theory-to-implementation mismatch; not an error-control failure.

### R2.3 — Preserve source provenance after validation changes

Both original numerical manifests record core hash `f0e4a78d1c316184acb7f762b9ebb29cff7a4ace4d23412a3f84a255c7813072`; the current core reviewed here has hash `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9`. The difference follows subsequent comparator validation edits. The exact numerical replays reported below show that current code reproduces both saved studies. Preserve original generation hashes and record subsequent validation/amendment separately, or regenerate artifacts and their manifests together. Do not rewrite an original generation hash as though the old run used new source.

**Priority:** Reproducibility bookkeeping. Numerically cleared by the independent replay; provenance documentation remains an integration task.

## 2. Proof-by-proof audit

| Result | Check and conclusion |
|---|---|
| Hierarchical kernel | Measurable, antisymmetric tier rules and symmetric eligibility give an antisymmetric ternary kernel. The first nonzero tier property is correct. Operational ties are properly separated from statistical equivalence. |
| Relations among WR, WO, and net benefit | Algebra is correct with positive denominators. Net benefit determines win odds, not win ratio when tie mass varies. The manuscript correctly avoids a ratio claim when losses vanish. |
| Compensation counterexample | Correct: constant successful reference, candidate failure probability epsilon and cheaper successes give success difference `-epsilon` and net benefit `1-2 epsilon`. Preference approaching one coexists with strictly negative success effects approaching zero; this does **not** imply arbitrarily large fixed harm can coexist with preference approaching one. The current wording respects that distinction. |
| Individual-episode nonidentification | The two modulo-three couplings have identical randomized observed-data laws and opposite individual preference. Their independent-copy preference is zero. The treatment of observed-context independent-copy identification now correctly credits Even and Josse and does not confuse it with the unobserved cross-world coupling. |
| Randomized pair identity | Conditioning on pair information and all four current potential outcomes gives exactly half of each oriented comparison. Iterated expectation is valid if the previous inference filtration is included in the conditioning information. Both positions must be fixed before orientation, randomization must be conditionally independent of current potential outcomes, probabilities must be recorded and positive, and consistency/no within-pair interference are essential. Exchangeability is unnecessary for the symmetric finite-pair target and is invoked only for the population product-law interpretation. |
| Component contrast | The half-sum identity for `g(A)-g(B)` is correct and explains why component effects differ from a general hierarchical preference target. An absolute A score can use the same randomized-score construction, as stated. |
| Gaussian-mixture CS | Conditional Hoeffding uses width squared divided by eight; defining `V=sum(width^2)/4` gives the stated exponential supermartingale. Gaussian integration with precision rho gives the displayed mixture and boundary. Conditional Tonelli, Ville, and the pathwise inversion are correct. Random widths are allowed only when predictable. The warning against substituting a post-context narrow range without changing the filtration/centering is necessary and correct. |
| Drift interpretation | The CS covers the running average of conditional means, potentially a random predictable target. It does not cover instantaneous or future performance. The manuscript makes that limitation explicit. |
| Finite-grid betting | Factors are strictly positive for the stated stake bound; conditional expectations are at most one under a stepwise conditional-mean null. Mixture validity follows. SLLN divergence requires a selected stake with positive expected log growth. The finite-grid counterexample is correct; a countable positive-weight grid approaching zero repairs universal i.i.d. consistency. No power theorem from the corrected Shekhar–Ramdas paper is imported. |
| Stationary intersection–union gate | Correct for one conjunction when at least one fixed component has a null conditional mean throughout the stream. Dependence between components is irrelevant to the single-null inclusion argument. Alpha splitting is unnecessary for this claim, but simultaneous component confidence statements or repeated candidate selection require additional control. Both current and retained crossings satisfy validity, subject to R2.2. |
| Drifting gate | The simultaneous-CS/union-bound proof is correct. A changing violating component prevents reuse of the stationary fixed-index proof. A fixed uniformly violating component remains a valid special case. This is a sufficient control strategy; the proof does not establish that Bonferroni allocation is the unique or optimal strategy. |
| Completed-prefix delay | Correct as a pathwise display result: the all-integer coverage event includes coverage at every completed-prefix index, even if that index is not a stopping time. Crucially, this result does not establish that an asynchronously adaptive collection process satisfies the enrollment-order conditional-randomization and predictability assumptions. Those assumptions must be justified separately; the appendix appropriately states this premise. |
| Fixed strata | Simultaneous within-stratum coverage and nonnegative fixed weights give the stated weighted coverage. Adaptive counts are allowed only while each within-stratum theorem remains applicable. A fixed target mixture must not be replaced by favorable data-chosen weights. The initial mean range `[-1,1]` remains legitimate for the symmetric kernel target even if individual HT scores have a larger range. |
| Offline task inference | Unbiasedness, boundedness, variance, and studentization are correct under independent complete records and, for the simplified variance/ordinary CLT, identical complete-record distributions. R2.1 requests making these assumptions explicit. Pair count is correctly rejected as independent sample size. |
| Shared-seed decomposition | For i.i.d. paired seed records conditional on the task, every off-diagonal comparison has the independent-copy expectation. Counting diagonal and off-diagonal terms proves the mixture identity and `2/R` bias bound. Removing a diagonal does not cure cross-seed dependence; the appendix says so. |
| Finite-time deployment bound | Under fixed positive gaps and positive fixed range widths, Hoeffding plus a union bound proves the displayed tail bound. The right side tends to zero; decreasing events then prove almost-sure finite deployment. For a zero-width deterministic component, state the trivial deterministic case separately or restrict displayed denominators to positive widths. This is a minor edge-case clarification. |
| Guardrail KL lower bound | Correct for the expressly restricted submodel and an a.s.-finite stopping/decision time under both laws with finite alternative expectation. Bounded likelihood increments justify summation/Wald's identity; data processing and the binary-KL monotonicity give the bound. The expansion around an interior delta is correct. This is a standard information argument, as credited. It does not automatically describe the pure deploy-only rule that can run forever under the null; the proposition's stopping assumptions are substantive. Explicitly writing that T is a stopping time and D is measurable at T would make the standard sequential-procedure meaning formal. |
| Comparator disagreement | The triangle inequality and bounded pointwise difference give the bound; the factor two example is sharp. The sensitivity claim needs inference for estimated disagreement, and post-hoc comparator selection needs separate control, as already stated. |

## 3. Code and numerical checks actually executed

1. Ran the documented invariant entrypoint, `python3 outputs/agent_win_eval/src/test_winstats.py`. All checks passed, including six analytic simulation truth checks. The file is a direct script, not a unittest test-case module; generic unittest discovery reports zero tests and is not the documented verification command.
2. Independently reconstructed raw compliance, success, and cost draws and sent them through the exported comparator, including resource eligibility. Across all six scenarios and 50,000 pairs per scenario, exported comparator signs matched the simulation's manually coded signs exactly. This closes the original concern about two potentially divergent comparator implementations for the tested configuration.
3. Checked the expected betting factor algebra numerically over five thresholds (`-0.99, -0.03, 0, 0.3, 0.99`) and seven admissible ternary boundary-null laws per threshold. Every stake had expectation one to numerical tolerance.
4. Ran an additional independent CS experiment with seed 271828, 3,000 repetitions and 2,000 monitored observations. Predictable range widths alternated based on prior centered cumulative outcomes; success probabilities drifted between 0.25 and 0.75 in 100-observation blocks. The correct running conditional target and predictable variance process were used. There were 8/3,000 ever-noncoverage events (0.267%). This probes both random predictable widths and drift; conservative observed coverage is not a proof or a power comparison.
5. Replayed the full initial generator/evaluator using the saved seed, child-seed construction, look schedule, batch size, and 2,000 repetitions. All 36 rows matched the saved deployment counts and mean capped sample sizes exactly.
6. Replayed all boundary, dependence, and adaptive-order stress tests in memory, retaining the original shared RNG order. All 17 saved event counts matched exactly: boundary guarded betting 15 and 9; task-cluster/naive coverage 1,905 and 1,113; adaptive unweighted/weighted-normal/weighted-betting crossings 930, 0, and 11.
7. Checked adaptive score algebra: the raw conditional mean is `0.8*(2q-1)`, the inverse-probability weighted mean is zero, the global weighted range is `[-5,5]`, and the normal-mixture predictable variance increment is `1/(4 min(q,1-q)^2)`. The implementation uses these values correctly. The unweighted failure is estimand bias relative to the symmetric target, not failure of a CS for its own biased raw-score conditional mean; the manuscript's interpretation is appropriate.

No review script overwrote the saved results, manifests, code, bibliography, or manuscript. Tests were executed directly in memory; this report is the sole authored file in this round.

## 4. Resolved prior concerns and remaining evidential limits

The new text adequately distinguishes intentionally invalid repeated Wald inspection from valid bounded-score monitoring; admits range-only normal-mixture conservatism; labels harmful positive-win outcomes as operational deployment failures rather than false composite-null rejections; and reports capped versus conditional stopping summaries separately. Boundary nulls and a nonexchangeable adaptive-order stress test now provide relevant evidence missing from round 1. Tier tolerance validation was repaired.

The empirical evidence still does not establish efficiency against a strong variance-adaptive confidence sequence or a compatible sequential all-pairs U-statistic method. No theorem proves novelty of the elementary concentration/betting pieces, and the manuscript appropriately credits prior work. Contribution strength remains an ML/research judgment rather than a mathematical pass/fail result.

No full delayed-arrival/adaptive-collection simulator, changing-null-component drift deployment experiment, differential judge-error study, or correlated realistic agent-trajectory generator was independently reviewed here. The additional random-width/drift check validates a narrow martingale setting only. The completed-prefix theorem should not be advertised as validation of every asynchronous production scheduler. The KL lower bound is not a proved sample-optimality guarantee for the reported betting implementation.

The publicly sourced benchmark extraction, bootstrap computation, source licenses, new prospective model calls, and any subsequently added `public_results.tex` or `prospective_results.tex` were outside this mathematical review's completed audit. I read the existing main manuscript and current synthetic experiment sections, but those new sections were being authored concurrently. Their data provenance and source-to-number correspondence need the empirical reviewer/integrator's separate check. I did not inspect the compiled PDF or certify ICLR formatting in this round.

## 5. Reviewed snapshots and disposition

Line references above refer to the source snapshot initially read in this round. Other authors were revising separate files concurrently; an amended proof is not automatically covered by this snapshot review.

| File | SHA-256 at review |
|---|---|
| `paper/theory.tex` | `3757f774c8dea290eb05cbf2ccfaec2bd02910db73aa13c545f6ac9dc1351d1e` |
| `paper/main.tex` | `1a1884614541c611087ec90d09f69912ecb6332891897bb4b7df4302f983fa58` |
| `src/winstats.py` | `3053f8a14e033b02b514135d7043624ca34c1a1f9da9c622365d35aa7f927fd9` |
| `experiments/run_simulations.py` | `b3d51d15f707855db19b52f206b7b3362fb8f9a3f4a42df138b4a18840f63c9c` |
| `experiments/run_stress_tests.py` | `92b668753bef59415a87cabbcc13ec61212e4f5cdf63a377293329e3ffb0a041` |

Disposition at handoff: R2.1 and R2.2 require author integration; R2.3 requires an explicit provenance record, with numerical equivalence already verified. All other displayed central proof arguments have passed this model-assisted check within the stated scope. No external acceptance, production-safety, universal-power, or human-verification claim follows from this review.
