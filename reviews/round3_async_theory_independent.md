# Round 3: asynchronous theory and novelty audit

Date: 2026-09-18 UTC. Scope: all proofs in `paper/asynchronous.tex`, the new partial-score section of `paper/main.tex`, and `evidence/asynchronous_novelty.md`, checked against the primary references below.

**Role disclosure.** This reviewer did not author the asynchronous proofs but did author the associated informative-delay simulation and its protocol in an earlier assignment. Thus this is an independent check of another agent's mathematical exposition, with disclosed overlap in empirical development; it is not an independent empirical replication or a blinded review. It is model-assisted review, not human peer review or formal proof certification. Only this review report was edited in this round.

**Assessment.** The pathwise confidence-sequence transfer and positive-factor lower-wealth argument are valid under the explicit full-score filtration, score-range, and simultaneous enclosure assumptions. Prefix selection does not require an alpha split because every candidate is compared with the same latent all-prefix process. Stationary conjunctions are valid; drifting means require prefix-specific targets and simultaneous component control. The method does not establish a calendar-time e-process, universal power, or a new general filtration-transfer principle. One score-range assumption gap was identified and corrected during review. The main text also needed explicit ongoing-enrollment wording for consistency, as documented below.

## 1. Findings and author responses

### A. Clipping is required for the bounded specializations — resolved in appendix

The initial text stated that the latent score lies in `[-B,B]`, but the earlier general enclosures were only required to lie inside `[a_i,b_i]`. This did not explicitly ensure that the enclosures, or the range used in the CS, were themselves inside `[-B,B]`. Four later arguments use this stronger condition: positivity of partial betting factors, the `2BM/n` unresolved-width bound, the log-wealth derivative bound, and `V_n <= n B^2` in the consistency proof.

This is a substantive assumption, not merely notation. For example, take null scores `X_1=X_2=0`, valid but loose lower bounds `-100`, `B=1`, `c=0`, and stake `1/2`. The alleged lower wealth would be `(-49)^2=2401`, while full wealth is one. Multiplying negative factors destroys the monotonicity argument. Clipping the lower bounds to the known score range repairs the problem.

**Verified response:** The revised appendix explicitly requires `-B <= a_i <= lower_i(t) <= X_i <= upper_i(t) <= b_i <= B` for every fixed-B result and requires clipping in the preceding unresolved-width statement. This resolves the positivity, width, and consistency-range issues. The simulation's ternary enclosures already obeyed these constraints, so this finding does not invalidate its results.

### B. The consistency claim requires unbounded enrollment — main-text precision correction requested

The appendix correctly assumes `n_k=N(t_k) -> infinity`, vanishing average enclosure width almost surely, and positive stationary gaps. The first main-text summary omitted the growing-sample condition and said that vanishing average unresolved width eventually resolves stationary positive gaps. With a fixed finite enrollment cap, all endpoints eventually becoming known also makes unresolved width zero, but does not make sampling error disappear or power equal one.

**Requested response:** State “as the number enrolled tends to infinity” in the main-text consistency summary, and retain the distinction between the finite simulation and the asymptotic proposition. Also state that the main-text enclosures lie within the known score range, so its positive-factor equation inherits the appendix assumption. These are local precision edits; the full appendix proposition itself is correct after clipping.

### C. Choe–Ramdas is a structural novelty precedent — resolved in manuscript

The initial novelty memo treated Choe–Ramdas mainly as a warning about exchanging filtrations. Its free p-process/CS lifting results and delayed-forecast discussion are materially closer to the proof architecture here. They should be credited as structural precedents, alongside the worst-case pending-outcome method and correction of Henzi–Ziegel.

**Verified response:** The revised appendix and main section now expressly credit time-uniform event transfer, free confidence-sequence/p-process lifting, and delayed forecasting as precedents. This is the appropriate framing. The evidence memo's narrower “warning” description should be read together with this stronger source audit, or updated by the integrating author.

Do not characterize the current result as a strict generalization of Henzi–Ziegel without mapping assumptions. Their forecasting-time conditional null need not remain true when a mathematical filtration reveals all earlier final records. The settings therefore need not contain one another. “A protocol specialization using established completion and time-uniform transfer principles” is defensible; “first anytime inference under informative delays” is not.

## 2. Mathematical audit

### Latent filtration and informative revelation

The full-score process must satisfy its conditional-mean and predictable-range assumptions in one explicitly chosen enrollment filtration before any transfer is attempted. No assumption that calendar observations form that filtration is needed for the pathwise proof. In particular, independence between a final score and its reveal time is unnecessary.

A sufficient construction is independent complete potential-record/reveal-path pairs and fresh orientation coins, with a filtration containing the first `i` full pair records and their assignment coins. Past partial observations and logged propensities are then functions of those full records and coins. This supports the claimed randomization identity when there is no interference and pair membership is fixed before orientation. Independence is sufficient, not necessary; an appropriate conditional-mean model would also suffice.

The paper correctly warns that revealing earlier final records can change a conditional null. An unconditional zero mean, independent-looking marginals, or validity in the calendar observation filtration alone does not establish the needed latent conditional mean. Under design-based conditioning, full potential records can give pair-varying conditional effects; the running-average CS remains relevant, but stationary betting requires its stated fixed/stepwise null and cannot be justified merely by a zero terminal average.

The endpoints must remain the same frozen complete outcomes after enrollment stops. If deployment cancels pending episodes, the continuation target is hypothetical unless cancellation was part of the prespecified outcome protocol. The appendix explicitly addresses this distinction.

### Confidence-sequence transfer and interval width

On the event that the full-score CS covers every integer prefix, replacing each full sum by lower/upper sums preserves inclusion for every available `(n,t)`. Random enrollment counts, random inspection times, and informative revelation do not change this pathwise implication. The stated measurability qualification covers the continuous-time supremum issue. A common enclosure-failure event of probability at most eta adds eta by a union bound, without independence.

The width decomposition is exact. With clipped enclosures, only unresolved scores contribute to the additional average width and each contributes at most `2B`. The statement about one unresolved early pair is meaningful with continued enrollment and controlled total unresolved width; it is not a claim that the interval is always narrower than the interval from a smaller complete prefix.

### Lower wealth, threshold validity, and p-values

After clipping, every partial factor is positive and no larger than its corresponding full factor for a nonnegative fixed stake. Products and fixed nonnegative mixtures preserve the inequality. A partial threshold crossing at any time/prefix therefore entails a crossing of the latent full process at some prefix, and Ville controls that event. Recomputing a past factor when information arrives does not create a new observation.

The probability guarantee is distinct from an expectation guarantee. For a concrete check, take two independent fair Rademacher scores, `c=0`, and stake `1/2`. Both full-data wealth values arise from a valid martingale, but the expected maximum of the first two wealth values is **1.25**, not at most one. Thus the unadjusted prefix envelope is not even generally an e-value at a deterministic fully observed endpoint. The manuscript correctly avoids calling that envelope or the reciprocal running p-value an e-process.

The displayed p-value construction is valid because its crossing event equals a partial-wealth threshold event. That statement is restricted to exact enclosures, as required. An eta-failure enclosure would need corresponding adjustment before claiming an ordinary superuniform p-value.

### Prefix envelopes and deployment conjunctions

All candidate prefixes use the same latent full process, frozen weights/stakes, hierarchy, thresholds, and endpoint definition. Therefore inspecting more prefixes does not create a family of separately initialized tests requiring an alpha split. Selecting multiple hierarchies or candidates would be a different issue and is not covered by this argument.

The scalar envelope corollary is correct. Its same-prefix multigate extension is immediate: if one completed candidate prefix passes every gate, the partial lower and full scores coincide on that prefix for every gate, so the partial envelope includes the same successful conjunction. This proves non-later stopping against the stronger comparator that inspects **all** completed candidate prefixes with the same candidate grid and calendar looks. Merely multiplying lower factors for the latest enrolled count does not enjoy this ordering.

For stationary conditional means, deployment at different prefixes or times for different gates can also be valid by the fixed true-null intersection–union argument. The implemented experiment uses the more restrictive same-prefix conjunction. These are distinct algorithms; the paper's current same-prefix description matches the reported experiment.

Under drift, different prefixes have different running conditional targets. A maximum of their lower confidence bounds is not a lower bound for the current enrollment-average effect. The paper correctly requires retaining the stated prefix/target and simultaneous component control. Independent lower bounds for the hierarchy and components need not be jointly attainable by one hypothetical completion: each is below its own true score, which is sufficient for conservative gate evidence.

### Consistency, log penalty, and scope

With fixed conditional mean and globally bounded scores, the martingale strong law follows from summable fixed-time Hoeffding tails and Borel–Cantelli. Vanishing average enclosure width transfers that limit to the lower and upper empirical means. Clipped predictable ranges make the fixed-rho radius vanish. The finite number of positive-gap gates then eventually pass along the increasing enrollment sequence. All steps are correct.

The single-stake log-wealth bound follows from the derivative of `log(1+lambda(x-c))`, bounded by `lambda/[1-lambda(B+c)]` on the clipped range. With i.i.d. full scores, positive expected log growth, and vanishing average unresolved width, its normalized partial log wealth has the same positive limit. A fixed mixture must assign positive weight to that stake. These assumptions do not imply universal consistency for an arbitrary finite bet grid; the separate finite-grid qualification remains essential.

Ongoing enrollment and finite enrollment have different conclusions. For finite enrollment, exact full revelation eventually makes complete and partial prefix envelopes identical, yielding identical eventual deployment decisions with matched candidates/gates. It does not guarantee deployment under every alternative. For ongoing enrollment, bounded delay plus a regular constant arrival rate makes the pending fraction vanish, but rapidly growing enrollment can leave a nonvanishing pending fraction. The appendix conditions, not simply the word “continuous,” determine whether its all-enrolled consistency statement applies.

## 3. Primary-source novelty verification

All sources were reopened on 2026-09-18. The summaries below distinguish verified prior results from this reviewer's comparison.

- **Henzi and Ziegel (2022), Section 3.2.** Their sequential forecast method stops only when the terminal evidence threshold will hold for every pending binary outcome. This is a direct conceptual antecedent to evaluating worst-case completions. The current hierarchy/component construction is a different protocol and null model, not the first pending-outcome strategy. Verified in [arXiv v3, Section 3.2](https://arxiv.org/html/2103.08402v3); the version already incorporates the corrected stopping discussion.
- **Henzi and Ziegel correction (2022).** The original general supermartingale/optional-stopping claim fails for lag greater than one. The corrected stopping rule retains type-I control, while unrestricted inversion of the original process does not supply the originally claimed anytime p-value. This supports the manuscript's distinction between valid threshold events and calendar-time expectation guarantees. Verified directly in the [published correction](https://academic.oup.com/biomet/article/109/4/1181/6696629).
- **Choe and Ramdas, latest v5 (2026; first posted 2024).** Section 3.1, Lemma 1/Theorem 1, establishes free p-process lifting using time-uniform/random-time equivalence and explicitly notes the CS analogue. Section 5.2 discusses delayed forecasting and the difference from expectation-valid e-process lifting. This is a structural precedent for the transfer argument, although the two time indices and feasible completion sets here are not literally the same theorem statement. Verified in [Sections 3.1 and 5.2](https://arxiv.org/html/2402.09698v5). The current arXiv record says accepted in JRSS B; no unverified volume/pages are asserted here.
- **Lindon and Kallus (2026), v2.** Their target is sample cumulative reward by calendar time under design-based randomization. Section 4 constructs asymptotic CSs and explains the generic failure of a direct treatment-effect error martingale across asynchronously realized arm outcomes. Their setting differs from inference about a bounded eventual fixed-horizon enrollment score. The new manuscript does not refute that obstruction or establish general new delay-robust inference. Verified in [v2, Sections 3–4](https://arxiv.org/html/2603.25971v2).

The current narrow novelty framing is appropriate. The transfer, product monotonicity, prefix inclusion, width accounting, and mean-value bound are elementary consequences of established principles. Their usefulness for hierarchical agent traces can be a contribution, but theorem correctness alone does not establish strong ICLR novelty. A persuasive evaluation must demonstrate the value of feasible hierarchy information and explicit guardrails under a plausible observation protocol, rather than only defeat selection-biased monitoring.

## 4. Checks, limitations, and disposition

In this round I independently evaluated the prefix-envelope expectation counterexample, the out-of-range enclosure counterexample, and 1,000 random clipped-range instances of the log-wealth inequality; all agreed with the analytical conclusions. I read every asynchronous proof and the new main section. The original simulation's exhaustive 96-state enclosure checks and full-run assertions were authored by me in the earlier implementation task and should not be relabeled as an independent replication here.

No source or manuscript was edited by this reviewer. No existing simulation was rerun or changed in this review round. The empirical comparison uses a deliberately informative asymmetric synthetic validation pipeline; it does not validate real grader certificates, indefinite production operation, cross-pair interference, version changes, or the actual validity of bounds emitted by a live agent harness. Those remain empirical/modeling questions beyond the algebraic proof.

Reviewed corrected appendix SHA-256: `18cbd8c234f0b5aa7b81af5e91ce42ce0aa6aafc9b33a4f61cb5db3fec1992da`.

Main-text snapshot before the final precision requests: `d44c521efdfa723b6a237b475c5ef5a5cab716e72ff15f5af9ec9f1a281e2812`.

Evidence-memo SHA-256: `b26f7d2ac1c4135a2c5cc8e4d082582a4294d3ecb2fd2d7c6565bff42db73b6e`.

**Disposition:** No remaining material flaw identified in the corrected asynchronous appendix under its explicit assumptions. The main-text sample-growth/range precision edits and conservative novelty positioning must be retained during final integration. This disposition is a scoped model-assisted mathematical assessment, not submission-readiness or acceptance certification.

**Final response recheck:** Both main-text precision requests were subsequently applied and verified: its enclosures are explicitly within the known score range, and its consistency summary requires the number enrolled to tend to infinity. Verified main SHA-256: `8ad6c16e38086ce731ddd53032d398294212a5d4dadb347a20fbffc62a5f28a9`. All mathematical wording corrections raised in this round are therefore resolved in the inspected sources.
