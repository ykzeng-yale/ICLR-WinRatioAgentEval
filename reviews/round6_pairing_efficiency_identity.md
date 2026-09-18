# Round 6: equal-budget pairing efficiency identity

Date: 2026-09-18 UTC. Scope: an independent algebraic audit of the all-pairs versus disjoint-pairs comparison under the current primary simulation generator. Read `experiments/run_simulations.py`, the corresponding manuscript scope statements, and `evidence/lit_winstats.md:136`. No simulation was run, no external comparator-worker files were accessed or changed, and no source or manuscript edits were made. The final section records the additional requested PSNB algebra check.

## Conclusion and actual normalization error

With **N independent A records and N independent B records**, both methods use **2N executions**. There are N disjoint A/B pairs, not N/2. The all-pairs estimator has weakly smaller finite-sample variance for the common independent-draw target:

\[
\operatorname{Var}(U_N)=\frac{\sigma_A^2+\sigma_B^2}{N}
 +\frac{\sigma_R^2}{N^2},\qquad
\operatorname{Var}(D_N)=\frac{\sigma_A^2+\sigma_B^2+\sigma_R^2}{N}.
\]

Thus the expression in `evidence/lit_winstats.md:136` mixes two budget conventions: it begins with n units **per arm**, but assigns only n/2 disjoint pairs to that budget. This incorrectly introduces a factor of two into the paired estimator's variance. If n means total executions, both all-pairs arm sizes are n/2 instead.

An important implication for this paper is that the raw success and safety **difference** kernels are additive. Their all-pairs and disjoint-pair point estimators are exactly equal on the same arm records. Only the nonlinear hierarchical score can obtain the variance improvement in this comparison. This does not settle the relative stopping times of guarded sequential procedures.

The projection decomposition is established U-statistic machinery, not a new generic result. Hoeffding's original paper develops variance and projection theory; Zhang and Wu give the directly corresponding finite two-sample win-statistic covariance formula in equations (2.4)–(2.5). [Hoeffding, 1948](https://doi.org/10.1214/aoms/1177730196), [Zhang and Wu, Section 2](https://arxiv.org/html/2410.06281v1#S2).

## 1. Sampling model, target, and estimators

Let `A_1,...,A_N` be iid from `F_A` and `B_1,...,B_N` iid from `F_B`, with the two samples independent. Each record contains the episode's complete frozen-horizon outcomes. Let `h(a,b)` be a fixed measurable comparison score with finite second moment; the paper's hierarchical ternary score is bounded and therefore satisfies this requirement. Both estimators target

\[
\theta=E\{h(A,B)\},\qquad A\sim F_A,\ B\sim F_B,
\quad A\perp B.
\]

Using the same records, define

\[
D_N=\frac1N\sum_{i=1}^Nh(A_i,B_i),\qquad
U_N=\frac1{N^2}\sum_{i=1}^N\sum_{j=1}^Nh(A_i,B_j).
\]

Both are unbiased for theta. The N² summands in `U_N` are **not N² independent observations**. Recombining already measured outcomes creates more kernel evaluations but no additional agent executions. A literal implementation has N versus N² kernel evaluations; execution efficiency and statistical-computation cost are different quantities.

This model holds for the current synthetic generator: the safety, success, and cost draws are independent across arm records, and their distributions are fixed within each scenario. It is not automatically the model for shared-seed benchmark trials, adaptively changing candidates, arbitrary predictable strata, or HT-weighted adaptive orientation. Recombining across strata can also change the target. A fair stratified comparison must recombine within the same strata and retain the same prespecified weighting.

## 2. Exact orthogonal decomposition and variance proof

Set

\[
a(A)=E\{h(A,B)\mid A\}-\theta,\qquad
b(B)=E\{h(A,B)\mid B\}-\theta,
\]

\[
r(A,B)=h(A,B)-\theta-a(A)-b(B).
\]

Then `Ea=Eb=0`, and

\[
E(r\mid A)=E(r\mid B)=0.
\]

Independence of A and B gives `E(ab)=0`; conditional centering gives `E(ar)=E(br)=0`. Define

\[
\sigma_A^2=E(a^2),\quad \sigma_B^2=E(b^2),\quad
\sigma_R^2=E(r^2),\quad
\sigma_h^2=\operatorname{Var}\{h(A,B)\}.
\]

Consequently

\[
\sigma_h^2=\sigma_A^2+\sigma_B^2+\sigma_R^2.
\tag{1}
\]

The disjoint scores are iid, so

\[
\operatorname{Var}(D_N)=\sigma_h^2/N.
\tag{2}
\]

For the all-pairs mean,

\[
U_N-\theta=\frac1N\sum_i a(A_i)
+\frac1N\sum_j b(B_j)
+\frac1{N^2}\sum_{i,j}r(A_i,B_j).
\tag{3}
\]

The three terms are pairwise uncorrelated. Distinct residual summands are uncorrelated even when they share one record. For example, conditioning on `A_i` and using independent `B_j,B_k` gives

\[
E\{r(A_i,B_j)r(A_i,B_k)\mid A_i\}
=E\{r(A_i,B_j)\mid A_i\}E\{r(A_i,B_k)\mid A_i\}=0
\]

when `j != k`. The same argument applies to a shared B record; with neither record shared, independence applies directly. Only N² diagonal covariance terms remain. Therefore the residual mean has variance `sigma_R²/N²`, giving

\[
\boxed{\operatorname{Var}(U_N)
=\frac{\sigma_A^2+\sigma_B^2}{N}+\frac{\sigma_R^2}{N^2}.}
\tag{4}
\]

Subtracting (4) from (2),

\[
\boxed{\operatorname{Var}(D_N)-\operatorname{Var}(U_N)
=\frac{N-1}{N^2}\sigma_R^2\ge0.}
\tag{5}
\]

This is an exact finite-N identity, not just an asymptotic order statement.

An equivalent covariance-counting expression uses

\[
\zeta_{10}=\operatorname{Cov}\{h(A_1,B_1),h(A_1,B_2)\}=\sigma_A^2,
\]

\[
\zeta_{01}=\operatorname{Cov}\{h(A_1,B_1),h(A_2,B_1)\}=\sigma_B^2,
\quad \zeta_{11}=\operatorname{Var}(h)=\sigma_h^2.
\]

There are N² identical-cell terms, N²(N−1) ordered pairs sharing only A, and N²(N−1) sharing only B. Dividing their sum by N⁴ yields

\[
\operatorname{Var}(U_N)
=\frac{(N-1)(\zeta_{10}+\zeta_{01})+\zeta_{11}}{N^2}.
\tag{6}
\]

Here `zeta_11` is the **full kernel variance**, not the residual variance. Confusing these conventions causes another possible finite-N error. For unequal arm sizes M and N, the same derivation gives

\[
\operatorname{Var}(U_{M,N})=
\frac{\sigma_A^2}{M}+\frac{\sigma_B^2}{N}+\frac{\sigma_R^2}{MN}.
\tag{7}
\]

## 3. Budget conversion, ratios, and edge cases

If `T=2N` denotes the total execution budget, then

\[
\operatorname{Var}(D)=\frac{2\sigma_h^2}{T},\qquad
\operatorname{Var}(U)=\frac{2(\sigma_A^2+\sigma_B^2)}{T}
+\frac{4\sigma_R^2}{T^2}.
\tag{8}
\]

When `sigma_h²>0`, write

\[
\kappa=\frac{\sigma_A^2+\sigma_B^2}{\sigma_h^2}\in[0,1].
\]

Then

\[
\frac{\operatorname{Var}(U_N)}{\operatorname{Var}(D_N)}
=\kappa+\frac{1-\kappa}{N}.
\tag{9}
\]

- **N=1:** the estimators are identical.
- **Additive kernel:** if `h=theta+a(A)+b(B)`, then `sigma_R²=0`, and the estimators are identical for every N.
- **Nondegenerate projections:** if `sigma_A²+sigma_B²>0`, the large-N paired/all-pairs variance ratio tends to `sigma_h²/(sigma_A²+sigma_B²)`.
- **Degenerate projections:** if both projection variances vanish but the kernel variance is positive, the all-pairs variance is order N⁻² and the paired variance order N⁻¹; the ratio is N. This is a general-kernel edge case, not a claimed property of the paper's six scenarios, and the ordinary nondegenerate normal approximation is then unsuitable.
- **Constant score:** if `sigma_h²=0`, both variances are zero and their ratio is undefined; do not report an efficiency ratio from `0/0`.
- **Ties:** for a ternary score, `sigma_h²=1-p_tie-theta²`. This does not determine kappa. A tie rate and net benefit alone cannot quantify the pairing-efficiency gap.

There is also a useful symmetrization interpretation. Conditional on all arm records, average the disjoint mean over a uniformly random permutation of the B indices. Its conditional mean is exactly `U_N`, and the randomly permuted disjoint mean has the same unconditional distribution as `D_N`. The law of total variance gives the same weak variance improvement. This argument is about a fixed sample size; it does not turn arbitrary stopped procedures into Rao–Blackwell equivalents.

## 4. Exact specialization to the current generator

Write an arm record as `(S,Q,C)`, with binary safety S, binary success Q and positive cost C. Let

\[
P(S_A=1)=s_A,\quad P(S_B=1)=s_B,\quad
P(Q_A=1)=p_A,\quad P(Q_B=1)=p_B,
\]

and let each record's components be independent, as in the current generator. Costs satisfy `log C_A ~ Normal(log rho, v²)` and `log C_B ~ Normal(0,v²)`, with `v=.45` and `rho` the scenario's cost ratio. Define gamma=.95 and

\[
g(c,d)=\mathbf1\{c<\gamma d\}-\mathbf1\{d<\gamma c\}.
\]

The code's exact hierarchical score is

\[
h(A,B)=S_A-S_B
+\mathbf1\{S_A=S_B\}(Q_A-Q_B)
+S_AS_BQ_AQ_B\,g(C_A,C_B).
\tag{10}
\]

This formula respects the implementation's resource eligibility: cost compares only two safe, successful episodes. If both safety indicators are zero, their success indicators can still decide, exactly as the current code specifies.

Let `F_A,F_B` be the cost CDFs. The conditional cost scores are

\[
G_B(c)=1-F_B(c/\gamma)-F_B(\gamma c),\qquad
H_A(d)=F_A(\gamma d)+F_A(d/\gamma)-1.
\]

For a realized A record `(s,q,c)` and B record `(t,r,d)`, respectively,

\[
m_A(s,q,c)=E_Bh((s,q,c),B)
=s-s_B+v_B(s)(q-p_B)+s q s_Bp_B G_B(c),
\tag{11}
\]

\[
m_B(t,r,d)=E_Ah(A,(t,r,d))
=s_A-t+v_A(t)(p_A-r)+t r s_Ap_A H_A(d),
\tag{12}
\]

where `v_B(s)=s*s_B+(1-s)*(1-s_B)` and `v_A(t)=t*s_A+(1-t)*(1-s_A)`. Thus `sigma_A²=E(m_A²)-theta²`, `sigma_B²=E(m_B²)-theta²`, and (1) supplies the nonnegative residual variance.

These moments can be obtained from four binary states per arm and one-dimensional normal integrals; no all-pairs Monte Carlo approximation is mathematically necessary for this generator. For example, set

\[
\mu_g=E\{g(C_A,C_B)\},\qquad
\nu_A=E\{G_B(C_A)^2\},\qquad
\nu_B=E\{H_A(C_B)^2\}.
\]

For each `(s,q)`, let `d_A=s-s_B+v_B(s)(q-p_B)` and `e_A=s*q*s_B*p_B`. Then

\[
E(m_A^2)=\sum_{s,q\in\{0,1\}}P(S_A=s)P(Q_A=q)
\{d_A^2+2d_Ae_A\mu_g+e_A^2\nu_A\}.
\tag{13}
\]

The B formula replaces these by `d_B=s_A-t+v_A(t)(p_A-r)` and `e_B=t*r*s_A*p_A`, using nu_B. For instance,

\[
\nu_A=\int_{-\infty}^{\infty}
G_B\{\exp(\log\rho+vz)\}^2\varphi(z)\,dz.
\tag{14}
\]

For the full kernel variance, the nonzero score regions are disjoint. Write

\[
D_S=s_A(1-s_B)+(1-s_A)s_B,\quad
K_S=s_As_B+(1-s_A)(1-s_B),
\]

\[
D_Q=p_A(1-p_B)+(1-p_A)p_B.
\]

Then

\[
E(h^2)=D_S+K_SD_Q+s_As_Bp_Ap_B\eta_g,\qquad
\sigma_h^2=E(h^2)-\theta^2,
\tag{15}
\]

where eta_g is the probability that the cost difference is meaningful. If

\[
u=\frac{\log\gamma-\log\rho}{\sqrt2v},\qquad
w=\frac{-\log\gamma-\log\rho}{\sqrt2v},
\]

then `mu_g=Phi(u)-1+Phi(w)`, `eta_g=Phi(u)+1-Phi(w)`, and

\[
\theta=(s_A-s_B)+K_S(p_A-p_B)+s_As_Bp_Ap_B\mu_g,
\tag{16}
\]

agreeing with the existing analytic target. Equations (11)–(16) provide an exact specification for evaluating the identity if the independent comparator worker needs a numerical reference. **No numerical evaluation or scenario-specific efficiency table was performed in this audit.**

For the raw success guardrail, a stronger finite-record statement holds:

\[
\frac1{N^2}\sum_{i,j}(Q_{Ai}-Q_{Bj})
=\overline Q_A-\overline Q_B
=\frac1N\sum_i(Q_{Ai}-Q_{Bi}).
\tag{17}
\]

The same identity holds for raw safety differences. Under independent arms their variances are `[p_A(1-p_A)+p_B(1-p_B)]/N` and `[s_A(1-s_A)+s_B(1-s_B)]/N`, respectively. Equation (17) itself is algebraic and does not need independence. An all-pairs sequential guardrail may still use a different variance estimator or boundary, but its sample mean is not improved by recombination.

## 5. What this establishes, and what remains open sequentially

Equations (4)–(5) establish weakly smaller variance and squared-error risk at a **common fixed N**, for the common independent-draw target. They identify exactly the part of score variability removed by recombination. They also support an ordinary asymptotic information comparison when projections are nondegenerate and both methods use the same fixed-horizon normal-theory criterion.

They do not establish a pathwise ordering of estimates, confidence bounds, or stopping times; a uniform ordering of power; a ratio of expected sequential sample sizes; or superiority after accounting for computation. Different sequential boundaries, nuisance-variance estimates, early-look behavior, stopping/continuation rules, and component requirements affect those quantities. In particular, rare-safety or success noninferiority gates can determine the guarded decision even when the hierarchical net-benefit estimator becomes much more precise.

For deterministic nested balanced sample sizes `N <= M`, the same decomposition does give the exact covariance identity

\[
\operatorname{Cov}(U_N,U_M)=
\frac{\sigma_A^2+\sigma_B^2}{M}+\frac{\sigma_R^2}{M^2}
=\operatorname{Var}(U_M).
\tag{18}
\]

This follows because N shared projection terms contribute their variance divided by NM, and N² matched residual terms contribute their variance divided by N²M². The analogous identity holds for `D_N,D_M`. Canonical-looking covariance is not joint Gaussianity or finite-sample independent increments. It does not justify applying a product e-process to the N² dependent scores or automatically validate a repeated Wald test. Zhang and Wu's sequential work addresses additional asymptotic joint-distribution requirements, rather than deriving arbitrary-time exact validity from a variance ordering alone. [Sequential design framework](https://arxiv.org/html/2410.06281v1#S3).

The present paper's statements that disjoint pairs trade information for a simple randomized score and that relative sequential efficiency is not established are appropriately cautious (`paper/main.tex`, related-work paragraph and limitations; `paper/theory.tex`, concluding scope). The exact identity can sharpen these statements, but **does not close the open sequential all-pairs comparator gap**. The existing DM comparison remains a different inferential method on the same disjoint score stream, not an all-pairs comparison.

Suggested correction for the literature ledger:

> With N observations per arm, both approaches use 2N executions. The N disjoint-pair mean has variance Var(h)/N; the all-pairs mean has variance (sigma_A²+sigma_B²)/N + sigma_R²/N². The all-pairs advantage is the reduction of the degenerate residual variance. This exact fixed-sample identity does not determine relative stopping efficiency of sequential deployment procedures, and additive success/safety difference estimators are unchanged by recombination.

## 6. Additional bounded check: PSNB versus a raw-success guardrail

McCoy et al. define reach as ties on all previous stages and PSNB as a fixed charter-weighted average of the corresponding stage-conditional effects. Definition 1 uses nonnegative weights summing to one; Assumption 3 requires positive reach for weighted stages. [Definitions and reach](https://arxiv.org/html/2607.22950#S3), [PSNB definition](https://arxiv.org/html/2607.22950#S4), [positive-reach condition](https://arxiv.org/html/2607.22950#S5.SS2).

Consider two stages, success followed by lower cost among two successes. B always succeeds at cost 2. A fails with probability epsilon and otherwise succeeds at cost 1. Fix `epsilon=.1`; any cost for failed A episodes is irrelevant. The 5% cost tolerance does not change the strict cost win at 1 versus 2.

- Stage 1 is always reached: `r_1=1`. Its score is -1 if A fails and 0 otherwise, so `Delta_1=-epsilon`.
- Stage 2 is reached exactly when success ties. Because B always succeeds, this is exactly the event that A succeeds: `r_2=1-epsilon=.9>0`. All reached pairs are two successes, and A wins on cost, so `Delta_2=1`.
- Ordinary hierarchical net benefit is `r_1*Delta_1+r_2*Delta_2=-epsilon+(1-epsilon)=1-2epsilon=.8`.
- With the fixed admissible charter `(alpha_1,alpha_2)=(.8,.2)`, PSNB is `.8*(-.1)+.2*(1)=.12>0`.
- Raw success difference is -.1, which violates a required success noninferiority margin of .03 because `-.1 < -.03`.

All positive-reach requirements are satisfied, and there is no need to define a conditional stage effect on an event of probability zero. The example shows that a positive PSNB under this charter and a raw-success noninferiority requirement define **different decision regions**. It does not show an invalid PSNB test, does not contradict its stated aggregation target, and does not claim a new generic paradox. A statistically correct PSNB test can support positive PSNB while the guarded deployment protocol correctly declines deployment for a different objective. Selecting or altering the charter after observing such a comparison would be a separate design issue, not part of this frozen algebraic example.

## 7. Read-only check of the integrated appendix

After the derivation was communicated, the integrating author created `paper/pairing_efficiency.tex`. I read the full file. **No mathematical correction is required.** The appendix correctly uses N records per arm and 2N executions, gives the exact finite-N projection variance and residual covariance proof, handles zero-variance and degenerate cases, states the exact equality for additive component means, and explicitly limits what follows for sequential stopping and inference. Its PSNB example agrees with the checked stage-reach definitions, charter conditions, arithmetic and raw-success margin.

The proposition is a fixed deterministic-N statement, as its heading and surrounding discussion indicate; its variance formula should not later be substituted at a random stopping sample size without another argument. A direct citation to the standard projection/finite two-sample variance source beside the proposition would improve attribution, but this is an editorial refinement, not a mathematical repair. No new derivations, simulations, or source edits were needed for this integration check.
