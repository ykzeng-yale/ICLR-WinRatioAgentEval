# Independent review of the new power diagnostics

Reviewed pin: `57482e317c42e971e33871e7d879e6ca61c8eac0` (2026-09-20). All line references below are to that pin. This is a bounded mathematical and source review, not a rerun of the CPU grid or a clearance of the prospective trial. No models, network calls, random simulations, owner-source edits, or Git mutations were performed. The directional-betting argument also received a separate read-only review from `host_gate_edges`.

**Disposition:** retain the useful correction that the paper already documents the range-only rule's conservatism, and retain the proposed directional secondary as a candidate with explicit specifications. Do not integrate the new universal power, optimal sample-size, or irreducible-cost claims as established results. Several numbers can be recovered, but they represent different quantities and require assumptions absent from the delivered diagnostic text.

## 1. Evidence boundary

The new claims are in `experiments/live_ab/design/COORDINATOR_DECISIONS.md:387–451`, revision 11. Commit `9e5c85c` changes only that file, adding 66 lines; it does not deliver a new diagnostic `REPORT.md`. At the reviewed pin, `experiments/live_ab_validation/REPORT.md` ends with section 15 and expressly says the CPU study is not a power study of the live program (`:1143–1145`) and uses i.i.d. pair laws (`:1136–1142`). Its existing grid cannot substantiate the newly reported drift diagnostics, 7,878 monotonicity checks, or KL projection.

The older `experiments/live_ab/design/R4_power_analysis.md` has different planning settings and is not a replacement for the missing new derivations and input laws. Revision 12 acknowledges the comparison-contract mismatch and makes the completed-data baseline results provisional pending the schedule witness (`COORDINATOR_DECISIONS.md:453–488`). That withdrawal must accompany any citation of the still-present report; this audit does not re-adjudicate that separate empirical issue.

## 2. The KL calculation is a conditional bound, not the claimed universal result

Revision 11 calls 3,099 an information floor that “NO procedure whatsoever can beat” and 0.2351 the maximum attainable power at 568 (`:400–405`). These numbers are recognizable and conditionally sensible. If the entire observed experiment has i.i.d. laws (P^n,Q^n), (Q) is an admissible null, a rejection-by-horizon event has null probability at most (\alpha), and its alternative probability is (\beta>\alpha), data processing gives

\[
 \operatorname{kl}(\beta\Vert\alpha)\le n\,D(P\Vert Q).
\]

For the *reported* (D=0.001149011), (\alpha=0.00625), and a specified **80% power** target, the necessary horizon is 3099.1788, hence at least **3,100 integer pairs**. Inverting the same inequality gives upper bounds 0.23510898 at 568 and 0.14851646 at 295. Thus the rounded arithmetic is supported; “maximum attainable” should be “upper bound,” since attainability was not shown.

The delivered text must identify the alternative and null probability tables, KL orientation, error allocation, target power, information available to the procedure, and sampling law. A score-marginal KL does not automatically bound procedures observing task identities, both outcomes, delays, or traces: an admissible joint null extension and its information must be supplied. A fixed roster paired without replacement does not automatically have the product-law information (nD); a justified conditional-information calculation is needed. An 80%-power necessary horizon also cannot be compared as though it were an expected stopping time or a sufficient horizon.

Independent plug-in calculations illustrate why the law matters. With the reported pilot success rate (p=433/591), independent cross-task Bernoulli outcomes give ternary probabilities (q=p(1-p)=0.1958709463) on each nonzero score. Reverse-KL projection onto mean (-0.03) gives **0.00114799168**, not exactly the reported KL. Restricting to ordered distinct pilot tasks gives **0.00114672418**; same-task discordance (40/591) per direction gives **0.00326800625** and an 80%-power lower bound **1089.65**, rather than 1,079. These are explicitly illustrative laws, not a claim that the owner's undisclosed law is numerically wrong. They establish the need to deliver the exact input recipe.

Equal observed success counts in two pilot arms do not establish identical true success probabilities (`:424–426`). Nor does a power upper bound prove “THE NULLS ARE REAL”: failure to certify non-inferiority is not evidence of equality. Same-task and cross-arrival comparisons have different dependence and estimands; pilot resampling is a conditional planning exercise, not proof about the prospective roster or future workloads.

## 3. The 6,697 and 17,097 values do not establish sufficient powered sample sizes

At `src/winstats.py:64–85`, the fixed 40-stake mixture accepts fractional counts. Substituting (nq) positive and (nq) negative counts from the independent-task plug-in law above, threshold (-0.03), and threshold capital (1/0.00625) produces a first crossing at **6,697 exactly**. This calculation evaluates

\[
 \log\!\sum_k w_k\exp\{n E_P\log(1+\lambda_k(Z+0.03))\},
\]

on deterministic expected counts. It is **not** actual 80% power, an expected stopping time, or even the expectation of log mixture wealth. This exact recovery does not prove which unpublished calculation the owner used; it shows that the value alone cannot support the proposed “needs about 6,700 randomized pairs” sizing sentence (`:440–446`). A delivered definition and power calculation are necessary. “Best valid” also requires an optimality result absent here; the paper itself limits its finite-grid power guarantee (`paper/theory.tex:364–399`). Use “this specified construction” or “best among the evaluated constructions” when supported.

Similarly, the normal-mixture radius at 568 is **0.1579515125**, and its first integer crossing below 0.03 is **17,097** for an exactly zero observed mean (`src/winstats.py:51–62`). These are path-specific algebraic benchmarks. A true zero mean does not force every realized mean to zero, so they do not give a sufficient powered horizon or guarantee that an equal candidate can certify a 0.158 margin. State the observed-mean condition and strict gate inequality. For a guarded deployment claim, guardrail power is only a necessary component; the joint hierarchy gate, partial observations, legal looks, and common-prefix decision also matter.

The 27.5%, 22.6%, and 49.8% shares (`:420–426`) reproduce exactly as log differences among 17,097, 6,697, 3,099, and 568. **Their causal interpretations do not follow.** In particular, the middle log gap is not a proved “irreducible price of anytime validity”: it mixes a planning crossing of a particular mixture with an information lower bound at 80% power. Grid choice, mixture penalty, and non-attainment of the lower bound can contribute. Moreover, without additional requirements for early-look power, a fixed-horizon test that can reject only at that horizon is itself anytime valid, so no universal positive monitoring penalty follows merely from demanding anytime validity. Retain these only as labeled arithmetic gaps between distinct benchmarks, or remove the apportionment.

## 4. Variance and reported stress tests require calibrated scope

The correction to keep (V_n=n) is justified **within the current predictable-range normal-mixture proof** for scores in ([-1,1]): `paper/theory.tex:274–331` constructs (V_n=\sum_i(b_i-a_i)^2/4). Substituting an observed empirical variance without a suitable new bound is unsupported. “Forced” is too broad if applied to every valid method; different, properly proved variance-adaptive methods or narrower predictable ranges are separate possibilities.

The reported 0.189 miscoverage, WSR-EB 10x/28x failures, 1,164/4,919 violations, and probability “at most 0.0057” (`COORDINATOR_DECISIONS.md:409–438`) have no reproduced diagnostic inputs, seeds, output tables, or uncertainty bounds in this review. Do not turn an empirical frequency into an upper bound without a valid argument. A procedure failing when applied to an unsupported drifting running-mean target is not evidence that its established guarantee under different assumptions is false. The negative-stake hedged capital is not monotone in the lower endpoint (`src/wincs.py:529–546`), which defeats this particular enclosure substitution argument; it does not invalidate its complete-data confidence sequence.

## 5. Directional secondary: argument sound, specification still required

No mathematical defect was found in the proposed **directional fixed-stake lower-wealth** construction. For (c=-\delta), stakes fixed before the prospective stream with (0\le\lambda<1/(1+c)), fixed nonnegative mixture weights, and simultaneously valid lower enclosures clipped to ([-1,1]), each positive factor (1+\lambda(\ell_i-c)) increases with \(\ell_i\) and is bounded above by its full-score factor. Products and mixtures preserve that ordering (`paper/asynchronous.tex:145–198`). Combining this pathwise domination with `paper/theory.tex:408–435` controls false crossings at enrollment prefixes whose running conditional mean is at most (c). Possible simultaneous enclosure failure adds its error probability.

Before prospective execution, the secondary specification must define:

- The threshold, grid, weights, clipping, valid input support, and how old factors are recomputed when enclosures improve. The ternary-count function is appropriate only when the substituted endpoints are ternary; general real endpoints require the corresponding factor product.
- The exact current enrollment-prefix target and legal looks. Monotonicity is for improving enclosures at a **fixed prefix**, not for increasing prefix size. Adding unresolved pairs can reduce evidence; an old crossing cannot certify a new drifting target (`paper/asynchronous.tex:232–245`; `paper/theory.tex:503–531`). The argument establishes threshold validity, not a calendar-time e-process.
- A secondary alpha and its across-trial/reporting family. Saying it has “no claim on the primary alpha” (`COORDINATOR_DECISIONS.md:435–437`) does not specify its own error control or produce joint primary-plus-secondary control. A guardrail-only result is not by itself a guarded deployment decision.

This could be prespecified for a genuinely unexecuted prospective trial, with its pilot-driven development disclosed. It is a post hoc diagnostic relative to existing pilot/CPU results and is not validated by the current normal-mixture CPU grid.

## Reproduction and handoff

Executed only `python3 work/power_diagnostic_theory_review/check_arithmetic.py`; it imports the exported exact-pin `winstats.py` and performs deterministic optimization and vectorized arithmetic. **Zero Monte Carlo trials, full-grid reruns, or model calls.** The script and `work/power_diagnostic_theory_review/arithmetic_results.json` preserve all calculations above. The archive export and source inspection are isolated under the same owned scratch directory. After handback, root preserved an equivalent snapshot-argument script at `experiments/audit_power_diagnostics.py` and regenerated `reviews/evidence/power_diagnostic_arithmetic.json`; see the root disposition for portable reproduction.

Required next delivery is narrow: exact diagnostic laws and information assumptions; definitions distinguishing necessary power bounds, deterministic planning crossings, actual crossing probabilities, and expected stopping times; reproducible outputs for numerical stress-test assertions; and the secondary's explicit inferential specification. No new broad grid or change to the frozen margin/horizon is requested by this review. These findings do not alter already accepted paper evidence or authorize a prospective freeze.
