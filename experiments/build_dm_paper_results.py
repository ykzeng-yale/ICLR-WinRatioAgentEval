#!/usr/bin/env python3
from pathlib import Path
import csv
R=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((R/'results/dm_baseline_results.csv').open()))
def get(s,m):return next(x for x in rows if x['scenario']==s and x['method']==m)
main=r'''\paragraph{An established likelihood-mixture reference.}
A separate eight-scenario comparison uses the Dirichlet-mixture
construction for categorical data \citep{lindon2022multinomial}, with a
fixed uniform prior and separate tests of the three raw gate scores.
All methods share complete iid pairs, targets, thresholds and looks.
With a fresh fixed seed and 2,000 repetitions, guarded DM has zero null
deployments and 60.1\% efficiency-gain deployments, versus 0.6\% and
96.6\% for guarded betting. Both detect the joint gain in every repetition.
These are results of a separately reproduced comparison, not replacements
for the primary study. Appendix~\ref{app:dm} gives all eight scenarios,
the likelihood derivation, and the narrower iid categorical assumptions.
This reference is not substituted into partial-score betting, since its
evidence is not coordinatewise monotone in the observed scores.
'''
assert int(get('null','guarded_multinomial')['deployments'])==0
assert int(get('efficiency_gain','guarded_multinomial')['deployments'])==1202
(R/'paper/dm_results.tex').write_text(main)
a=r'''\section{Complete-data Dirichlet-mixture reference}
\label{app:dm}
For each raw gate score, let $x_n=(w_n,t_n,l_n)$ be the counts of
$+1,0,-1$ among iid pairs with fixed probability vector $p$.
For fixed positive prior $a=(1,1,1)$, the known Dirichlet-mixture
likelihood ratio is
\[
 M_n(p)=\frac{B(a+x_n)}{B(a)\prod_jp_j^{x_{n,j}}},
 \qquad
 E_n^{\mathrm{DM}}(c)=\inf_{p:\,p_w-p_l\leq c}M_n(p).
\]
Here $B$ is the multivariate beta function. These are established
categorical-inference ingredients \citep{lindon2022multinomial}.
For an interior true vector $p_0$, each alternative categorical likelihood
ratio is a mean-one nonnegative martingale. Integrating over the fixed
Dirichlet prior preserves that property. At a boundary true vector,
the likelihood ratio restricted to the true support is a nonnegative
supermartingale, which suffices. For any null $p_0$, the composite
statistic is pointwise at most $M_n(p_0)$ at every $n$. Thus an eventual
crossing of $1/\alpha$ is included in the crossing event of this true-null
supermartingale, giving probability at most $\alpha$ by Ville's inequality.
The infimum need not itself be a martingale. Applying the fixed-null
intersection--union argument to separate preference, success and compliance
scores supplies the stationary guarded-decision guarantee without
assuming independence between scores within a pair.

The logarithm uses the maximum null log likelihood. If the empirical
categorical MLE satisfies $p_w-p_l\leq c$, use that MLE; otherwise
concavity places the optimum on the boundary. Write $p_l=u$,
$p_w=u+c$, $p_t=1-2u-c$, where
$\max(0,-c)\leq u\leq(1-c)/2$. The interior score equation is
\[
 -2nu^2+\{w(1-c)+l(1-3c)-2tc\}u+lc(1-c)=0.
\]
Evaluate all feasible roots and endpoints, with zero-count terms
$0\log0=0$, and select the maximum likelihood. The isolated implementation
checks nonnegative integer counts, positive prior and valid thresholds.
Independent constrained-optimization and small-sample exact-crossing
checks accompany the code audit. General-purpose functional projection
and confidence-width routines are not used for these results.

This likelihood argument assumes a fixed categorical vector; fixed
conditional means alone are not the same assumption. It is used here
only for complete iid scores, not adaptive importance-weighted counts
or drifting targets. Decisive hierarchy cells do not recover raw success
or compliance differences, so each required raw score has its own counts.
The resulting intersection--union guarantee is for one deployment claim,
not simultaneous confidence coverage for all effects.

The statistic also cannot replace the positive-factor lower-bound rule:
at $c=0$, counts $(10,0,0)$ have log evidence 2.741817, whereas reducing
one win to a tie yields $(9,1,0)$ and log evidence 2.996915, exceeding
$\log20$. Consequently lower scores need not yield lower DM evidence.
An asynchronous DM extension would require its own feasible-completion
infimum or a completed-prefix protocol.

The reference study uses seed 20260918, batches of 25, 2,000 repetitions
per scenario and 10,000 pairs. It includes the original six laws and two
post-primary-study extensions with success 0.30 in both arms: equal cost
and cost ratio 0.55. All scenarios and methods are retained. This is an
exact isolated reproduction of an existing contributed comparison,
not a newly preregistered study. All 64 method/scenario rows reproduce
exactly; paired sample-use differences and source hashes are supplied.
Each method uses current-look conjunction, matching the original protocol.
The different seed explains small differences from the primary simulation.

\begin{table}[h]
\centering\small
\caption{Separate complete-data reference study: deployment percentages,
2,000 repetitions per row, same draws for all methods. The initial six
laws retain their original definitions; the last two are extensions.}
\begin{tabular}{lrrrr}
\toprule
Scenario & Guarded bet & Guarded DM & Win-only DM & Repeated Wald\\
\midrule
'''
names={'null':'Identical agents','efficiency_gain':'Efficiency gain','success_regression':'Success regression','safety_regression':'Compliance regression','joint_gain':'Joint gain','weak_gain':'Weak gain','tie_heavy_null':'More ties, null','tie_heavy_efficiency':'More ties, cheaper'}
for s,label in names.items():
 vals=[100*float(get(s,m)['deployment_rate']) for m in ['guarded_betting','guarded_multinomial','win_only_multinomial','guarded_repeated_wald']]
 a+=label+' & '+' & '.join(f'{v:.2f}' for v in vals)+r' \\'+'\n'
a+=r'''\bottomrule
\end{tabular}
\end{table}
'''
(R/'paper/dm_appendix.tex').write_text(a)
