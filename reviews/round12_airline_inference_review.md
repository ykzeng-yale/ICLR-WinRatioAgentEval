# Round 12 airline correction: inference and integration scope

**Verdict: PASS for limited, explicitly descriptive integration and an optional observed-array orientation illustration. Do not integrate the owner's inferential report wholesale.** The corrected orientation construction is mathematically sound under its stated nominal coin-randomization model. Its target is already exactly computable from the retained array, so the band illustrates a masked replay; it does not establish fresh-run, new-task, production, or deployment performance. Several residual sentences in the owner report remain incorrect or overbroad. Explicit exclusions below close those issues for the proposed narrow root integration without changing observations or running another model.

Frozen source reviewed: **`55fb1e51234ad712c56799455bd704b829ed1d26`**, 2026-09-19. This reviewer previously developed project theory and conducted the Round 11 incoming-airline review, but did not collect airline outcomes or write the owner correction. Git blobs were read into outer `work/round12_airline_theory/`; only this report and that scratch were written. No model, benchmark, Monte Carlo, full owner analysis runner, or Git mutation was executed. This is a bounded inference audit, not a complete re-audit of attempt logs, licenses, anonymization, or release packaging.

## 1. Corrected conditional target and proof

The correction at `experiments/tau2_open/protocol_addendum_round10.md:19–34` repairs the main Round 11 conditioning error: it conditions on the **complete retained outcome array**, rather than merely on its law. Let Y contain the A and B records of all 98 task–trial units, and P contain the ordered matching into 49 pairs. For pair k with ordered units u₁,u₂, define

```
a_k = h(B(u₂), A(u₁))     [orientation R_k = 1]
b_k = h(B(u₁), A(u₂))     [orientation R_k = 0]
Z_k = R_k a_k + (1 − R_k)b_k
m_k = (a_k + b_k)/2.
```

The hierarchy is success, then agent completion tokens with 5% relative-max tolerance, then assistant tool calls with zero tolerance; the resource tiers are used only after joint success. This orientation agrees with the deposited code and all 49 reconstructed rows.

**Required randomization conditions.** Conditional on (Y,P), the R_k must have their modeled independent fair-coin law. Collection, amendment, retry/canonical-retention decisions, and any score/procedure selection used for the guarantee must not depend on these coins in a way that changes that law or selects a favorable reported path. The addendum explicitly uses the nominal randomization law of a documented pseudorandom design. A literal fixed seed is not a source of repeated physical randomness; the statement is the usual modeled rerandomization statement. Do not condition on the realized orientations, or on a fixed seed that determines them, and then also treat those orientations as random. The runner's command construction is consistent with collection ignoring orientation (`run_tau2_open.py:182–207,440–472`); human orientation-independence remains an assumption, not something the outcome table proves.

For the filtration G₀ = σ(Y,P), G_n = G₀ joined with σ(R₁,…,R_n), the conditional mean of Z_k is m_k. With d_k = (a_k−b_k)/2, the centered score is a symmetric two-point variable ±d_k and |d_k|≤1. Consequently,

```
E[exp(λ(Z_k − m_k)) | G_(k−1)]
  = cosh(λd_k) ≤ exp(λ²d_k²/2) ≤ exp(λ²/2).
```

Thus the project normal-mixture boundary applies with V_n=n. At fixed ρ=100 and α=.05, writing

```
r_n = sqrt((n+ρ) log((n+ρ)/(ρ α²)))/n,
```

the conditional probability that any n≤49 has |mean(Z₁,…,Z_n)−mean(m₁,…,m_n)|>r_n is at most .05. Clipping to [−1,1] preserves coverage. The proof requires no independence of the originally collected records after conditioning them out. Globally reused seeds, repeated tasks, and shared batch states therefore do not invalidate **this particular observed-array target**. They remain relevant to broader targets.

The same argument applies separately to the success-difference score. The two displayed .05 bands are **marginal time-uniform bands**, not a joint 95% confidence statement. A generic simultaneous guarantee for both needs error allocation; using .05 for each only yields at least .90 by the union bound. Neither the coinciding observed paths nor their coinciding endpoints makes their targets equal. No success noninferiority or guarded deployment is certified here.

This is a post-hoc construction evaluated on a prespecified replay. The complete array already gives every m_k exactly. State the conditional theorem and the descriptive replay, without presenting the post-hoc displayed analysis as a prospectively collected randomized deployment experiment or claiming that analysis selection has been adjusted for. Physical collection remained batches, all A then all B. The abstract “one exposure per arrival” is a masking device on those batches, not an observed randomized exposure stream.

## 2. Independent numerical reconstruction

I reconstructed the hierarchy directly from `episodes.csv` and `design.json`, without importing `analysis.py` or `src/wincs.py`. Both orientation scores and the realized assignments match `make_round10_handoff.py:248–291` and its JSON for every pair. The radius was also checked against the root core normal-mixture function, extracted without importing contributed analysis code.

| Quantity, n=49 | Hierarchical net benefit | Success difference |
|---|---:|---:|
| Observed replay mean | 0.0204081633 | 0.0204081633 |
| Exact observed-array orientation target | 0.0102040816 | 0 |
| Radius | 0.6297318534 | 0.6297318534 |
| Marginal running-mean band | [−0.6093236901, 0.6501400166] | [−0.6093236901, 0.6501400166] |
| Final absolute observed-minus-target error | 0.0102040816 | 0.0204081633 |
| Orientations with unequal scores | 24/49 | 24/49 |

Both known target paths lie within the specified bands at every prefix. The largest error is .375 at n=4 for each score. At n=24, both observed means are .0833333333, both orientation targets .0416666667, and r₂₄=1.1559143018, giving [−1,1] after clipping. The radius first drops below 1 at n=29. These are direct checks of this realized array, not estimates of coverage from repeated trials.

The canonical counts and direct-score observations checked in Round 11 are unchanged: **196 canonical records, comprising 194 saved trajectories and two infrastructure-failure placeholders; 15 successes among 98 records in each arm; 49 replay pairs with 10 B wins, 30 ties and 9 B losses.** All 19 realized non-ties are decided by success. The same-task descriptive all/diagonal/off-diagonal net benefits are .00510204/.01020408/0. These have different pairing definitions; no independent-draw interpretation is supplied by different trial indices alone.

The new attempt CSV has 206 rows: A108/B98, invocation 1 eight and invocation 2 198. The report's reconciliation is 194 retained-trajectory attempts plus 12 discarded attempts, producing 196 canonical records once the two failure placeholders are included. Therefore **12 discarded attempts** is consistent with only **10 attempts beyond the 196 planned units**; do not conflate these quantities. Full log-to-ledger and resource-bound verification is outside this inference audit. Canonical resource totals exclude discarded work, and a placeholder's zero recorded messages does not mean zero operational cost.

## 3. Residual claims to correct or explicitly exclude

| Priority | Frozen source | Finding and integration action |
|---|---|---|
| P1 | `results/tau2_open/report_final.md:11`; model-CI tables in §§3, 12.4 | The summary still reports unqualified betting/model intervals and “significantly fewer” resource use. The binding later addendum does not make those summary sentences safe to copy. Exclude owner E1 fixed-mean/ratio CIs, E2/component CIs, interval-derived sensitivity decisions, and significance claims. Root may retain labeled counts and means. |
| P1 | `report_final.md:236` | “Not certifiable … whatever the method” is an unsupported method-independent impossibility assertion. The observed intervals and a variance-based sample-size heuristic cannot prove it. Exclude this sentence and its universal interpretation. Say the specified replay rule did not certify the stated margin on these data. |
| P2 | `protocol_addendum_round10.md:49`; `report_final.md` §12.1 final sentence | The history-conditional alternative does **not** require a common mean or independent episodes for the root bounded-score normal-mixture theorem. Any adapted bounded score admits its history-conditional-mean construction. Reused tasks mean that a constant conditional mean is not guaranteed, not that nonconstancy is inevitable in every model. This unused alternative should be omitted or corrected; it does not undermine the explicit observed-array proof above. |
| P2 | `protocol_addendum_round10.md:13`; `report_final.md:62` | Between-task independence alone does not establish a finite-sample conservative t interval. Appropriate variance/nondegeneracy and asymptotic regularity conditions are still needed for the approximate claim. The globally reused seeds/batches are not automatically absorbed by task clustering. Excluding all E2/component inference closes this issue for root integration. |
| P2 | `protocol_addendum_round10.md:9,14`; `report_final.md:345` | Mere exchangeability is not interchangeable with iid sampling or a common conditional mean. The report expressly says its stronger conditions are unestablished; preserve that boundary and exclude R2 inference instead of treating the block-1 row as automatically valid. |
| P3 | `protocol_addendum_round10.md:43` | The final-error sentence incorrectly assigns .0102 to both scores. NB error is .0102; success error is .0204. The table's targets and band are correct. The handoff JSON stores a NB path check, not a separate success-path check; this audit independently checked both. |
| P2 | `report_final.md:44`; addendum:43–45 | The arithmetic that this specific radius reaches .03 at n=12,094 is correct. It is not a lower bound for every method, an empirical power calculation, or a sample-size requirement for the actual 49-pair archive. Omit this extrapolation from a concise manuscript illustration. Avoid “assumption-free” without specifying the nominal independent-coin model. |

The old owner implementation is not made valid for the desired scientific targets by its corrected endpoint arithmetic. `check_analysis_consistency.py` establishes reproducibility of deposited numerical outputs under specified current bytes; it does not establish their sampling assumptions. Likewise, the omit-five routine at `make_round10_handoff.py:293–331` calls the full contributed online/shadow/component analyses. Do not import or rerun that handoff module as the root inferential analysis. A small root-owned direct reconstruction from the original array is sufficient for the limited descriptive and orientation quantities.

## 4. Integration recommendation

Use a root-authored paragraph or small table giving the canonical denominator, two placeholders, equal observed success counts, 49 replay W/T/L, and clearly labeled same-task point estimates if useful. State batch collection, the mixed amendment history, shared trial seeds, and canonical-versus-all-attempt resource accounting. Equal observed success is not equivalence or noninferiority; the comparison does not isolate model architecture from serving arrangement, period, or amendment history.

An optional appendix illustration may state that nominal independent replay orientations, conditional on the complete retained array and fixed matching, yield the bounded-score running-mean result above. Display the **known target beside each band**, label the analysis **post-hoc observed-array replay**, and call the bands **marginal**. Its conclusion is that this specified band is broad on the recorded 49-pair replay. Do not describe it as estimating unknown fresh-run performance, validating calibration empirically, identifying an independent-task population effect, or providing operational stopping savings.

No additional model execution or heavy simulation is needed to make this limited integration mathematically defensible. The remaining owner prose issues should still be returned to the owner; root can close the immediate integration risk by the explicit exclusions above. Acceptance of source observations is separate from the independent accounting/anonymity/reproduction audit and from overall submission readiness.

## 5. Evidence identifiers

| Frozen object | SHA-256 |
|---|---|
| `experiments/tau2_open/protocol_addendum_round10.md` | `c6053533bd0b3fd01af158317830df12f8b2b1a20dfb47448474fa59e068fecf` |
| `experiments/tau2_open/make_round10_handoff.py` | `4b200d12207578c7d90d76ffc32177a8e7f5da013cd76a6e900f415456a8be57` |
| `results/tau2_open/report_final.md` | `1ae93f5bff68d57eb879c37fb5069b3fc6595c41e18fdce209ec7e1eb86505d0` |
| `results/tau2_open/round10_handoff_numbers.json` | `a6937828fbf82aabbacda3863f18dd3c0111aa786a9b3448f3282d8739754124` |
| `results/tau2_open/episodes.csv` | `5abbc1ce1acdc248ecf049276621a07449228ea3d8954e5af978559f3e11922f` |
| `results/tau2_open/design.json` | `c8fa5728e8a9602813ffac10ea4ef88642ef3550aa9d5a5b7028c25586186597` |
| Root `src/winstats.py` used for the isolated radius check | `56955ce09a8ac7afb15f2bd251048537eabcc04ea75e7579bdb825594f41fc69` |

Outer scratch `work/round12_airline_theory/independent_orientation_check.json` records the direct numerical checks; `snapshot_hashes.json` records the read-only incoming snapshots. The prior raw-array audit is `reviews/round11_airline_incoming_scope.md`. No original owner source, data, output, or Git state was altered by this review.

## 6. Root manuscript integration check

After completing the incoming-source audit, I read the root-authored `paper/open_airline_results.tex` and `paper/open_airline_appendix.tex` in the working tree. **PASS on inferential scope.** They use descriptive canonical outcomes, disclose batch collection and the amendment, distinguish attempt counts and resource denominators, and omit the unsupported owner intervals. The optional paragraph defines the full observed-array orientation target, specifies the nominal independent-coin model and coin-independent collection/amendment/retention, states the appropriate filtration, displays the known target beside the band, and explicitly labels the construction post hoc without selection adjustment. It makes no success-band, success-guardrail, new-task, fresh-run, deployment, or stopping-savings claim. The displayed final target and band agree with this audit.

One small resource-scope wording correction was sent to root: the accounting-table caption should say **“Complete failed-attempt token usage is unavailable”**, rather than categorically saying token usage is unavailable, because the owner supplied partial log-derived lower bounds. This does not require importing those bounds or changing the canonical totals. No other necessary inferential correction was found in these two TeX files. Their factual model/runtime and packaging assertions remain subject to the separate empirical and release audits.
