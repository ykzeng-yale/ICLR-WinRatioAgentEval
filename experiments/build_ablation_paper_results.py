#!/usr/bin/env python3
from pathlib import Path
import csv
R=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((R/'results/decision_ablation_results.csv').open()))
def row(s,m):return next(r for r in rows if r['scenario']==s and r['method']==m)
# Fail instead of emitting stale fixed-protocol prose if the source cohort changes.
for key, expected in {("null","guardrails_only"):392,("null","guarded_win"):1,("safety_regression","weighted_utility"):163,("safety_regression","guarded_weighted_utility"):0,("harm_favorable_labels","measured_guarded_win"):489,("harm_favorable_labels","oracle_true_guarded_win"):0}.items():
    assert int(row(*key)['positive_decisions'])==expected, key
for scenario in ['efficiency_gain','joint_gain']:
    for field in ['positive_decisions','mean_pairs_capped']:
        assert row(scenario,'guarded_win')[field]==row(scenario,'guarded_efficiency')[field], (scenario,field)
# Names come from the archived results, whose complete tables remain supplied.
print('Methods:', sorted({x['method'] for x in rows}))
main=r'''\paragraph{Decision objectives and grader errors.}
A separate 500-repetition ablation on each of six scenarios compares
success-only, component-only, guarded-win, and fixed weighted-utility
rules. These test different objectives. With identical agents,
component-only noninferiority qualifies 78.4\% of streams while guarded
win qualifies 0.2\%: satisfying component margins does not establish a
preference improvement. The fixed utility $0.8S+0.1C+0.1/(1+\mathrm{cost})$
approves the compliance-regression scenario in 32.6\% of runs, correctly
reflecting its positive utility target; adding component requirements
reduces this to zero. No rule is uniformly more powerful across different
objectives. Guarded bounded-efficiency superiority matches guarded win
in both deployment rate and mean capped pair count in the efficiency-gain
and joint-gain cases; these cases show no decision-speed advantage for
the hierarchical objective over that component-based rule.
Appendix~\ref{app:ablations} explains the objectives; the supplementary
CSV tables retain all comparisons and population Pareto descriptions.

Four additional cases perturb success grading. With 5\% false-positive
errors for $A$ and 5\% false-negative errors for $B$, a true success
contrast of $-0.04$ becomes $+0.012$ measured. Measured-label guarded
inference approves 489/500 streams (97.8\%), while true-label inference
approves none. A conservative rule using the specified error bounds also
approves none. Conversely, adverse differential grading prevents detection
of a genuine efficiency gain. Optional-stopping validity for measured
outcomes cannot repair a biased definition of success. The error bounds
are known simulation inputs, not empirically validated grader guarantees.
'''
(R/'paper/decision_ablations.tex').write_text(main)
appendix=r'''\section{Decision objectives and success-grader sensitivity}
\label{app:ablations}
The protocol was frozen before execution of this additional study, after
the original simulation study had been inspected. All ten cases use 500
independent repetitions, 6,000 pairs, master seed 2026091804, and looks
at 100 and every 100 pairs thereafter. The same 40 positive bets and
same-look conjunction are used. Fixed weighted utility is
$0.8S+0.1C+0.1/(1+\mathrm{cost})$; bounded efficiency is
$1/(1+\mathrm{cost})$. Both are in $[0,1]$, so their pair differences
use the same bounded-score betting construction. Their cost scale and
weights are illustrative preferences, fixed before seeing this study.
Giving utility to cost on unsuccessful episodes differs from the
hierarchical resource-eligibility rule.

The six compared decisions require respectively: success superiority;
only success/compliance noninferiority; guarded hierarchical preference;
utility superiority; guarded utility superiority; or guarded efficiency.
An approval is not labeled a statistical error solely because another
method's different deployment region fails. Population Pareto labels use
true success, compliance and raw mean cost; they are descriptive facts of
the generating laws, not estimated confidence regions. Mean lognormal
cost is analytic, and bounded-efficiency means use Gauss--Hermite
quadrature with 80/160-node agreement checked.

\paragraph{What can a known label-error guarantee protect?}
For an iid episode-pair law let $\widetilde S$ be a measured success bit
and suppose $P(\widetilde S^a\ne S^a)\leq\epsilon_a$ for $a=A,B$.
All other metrics and the frozen comparison rule agree. Put
$\epsilon=\epsilon_A+\epsilon_B$. A union bound and bounded scores give
\[
 |\widetilde\Delta_S-\Delta_S|\leq\epsilon,\qquad
 |\widetilde\theta-\theta|\leq2\epsilon.
\]
Indeed a success difference can change by at most the sum of its two
label-error indicators, and the hierarchical sign changes by at most
two on the event that at least one label is wrong. Taking expectations
proves both bounds. Hence measured superiority thresholds
$2\epsilon$ for net benefit and $-0.03+\epsilon$ for success,
with unchanged compliance threshold, suffice for the true deployment
region. For the iid study, the corresponding fixed conditional nulls
and intersection--union proof give the same anytime false-deployment
bound. Under temporal adaptation, analogous conditional error bounds
would need independent justification. Uncertainty in estimated grader
error rates is not covered by treating those estimates as known constants.

The four noise cases use conditional false-positive/false-negative rates
(FP,FN): identical agents with (.05,.05) in both arms; a true success
harm (.71 versus .75) with $A=(.05,0)$ and $B=(0,.05)$; an efficiency
gain (.75 versus .75, cost ratio .55) with the adverse reverse pattern;
and larger true harm (.65 versus .75) with (.05,.05) in both arms.
For the harm cases the cost ratio is .4. All compliance probabilities
are .995. Noise is independent of cost and compliance conditional on
true success and arm. The measured success probability is
$p(1-\mathrm{FN})+(1-p)\mathrm{FP}$, which gives the analytic measured
hierarchical target after substitution in the original target formula.
The conservative armwise error bound is $\max(\mathrm{FP},\mathrm{FN})$;
it may exceed the actual unconditional error frequency.

For favorable differential grading of the smaller harm,
the 97.8\% measured approval rate has Wilson 95\% Monte Carlo interval
$[96.10\%,98.77\%]$. True-label and conservative-bound approvals are
zero in 500 repetitions. With adverse differential labels on a real
efficiency gain, true-label approval is 73.8\% and measured approval is
zero. These results concern the four stated noise laws. They do not
validate a real judge, recover latent truth without assumptions, or
establish power of the conservative correction. In all four cases, the
assumed summed error bound is 0.10, making its measured-success threshold
$0.07$; every measured contrast is below that threshold. Thus all four
are null cases for this sufficient rule, and no bound-aware alternative
was studied. Zero approvals are not evidence of corrective power.

\begin{figure}[h]
\centering\includegraphics[width=\linewidth]{../results/decision_ablation_grading.pdf}
\caption{Success-grader sensitivity under four fixed noise laws. Oracle
labels exist only in simulation; the bound-aware rule assumes externally
valid error limits. Rates are Monte Carlo decisions about the indicated
measured or true target, not evidence about an actual deployed grader.}
\end{figure}
'''
(R/'paper/decision_ablation_appendix.tex').write_text(appendix)
