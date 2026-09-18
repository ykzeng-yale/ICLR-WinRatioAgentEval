#!/usr/bin/env python3
"""Generate manuscript text from the frozen delay study's executed results."""
from pathlib import Path
import csv
R=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((R/'results/async_results.csv').open()))
def row(s,m):return next(x for x in rows if x['scenario']==s and x['method']==m)
c=row('cheaper_equal_success','complete_prefix');p=row('cheaper_equal_success','partial_prefix_envelope');n=row('identical_outcomes','partial_prefix_envelope');bad=row('identical_outcomes','naive_completed_only')
gains=list(csv.DictReader((R/'results/async_paired_gains.csv').open()));g=next(x for x in gains if x['scenario']=='cheaper_equal_success')
text=r'''\subsection{Informative delays and partial outcomes}
\label{sec:async_exp}
A separate frozen simulation isolates an asymmetric measurement pipeline.
Both systems succeed with probability 0.90; their lognormal cost scales
are equal under the null and have ratio 0.55 under the alternative.
Failures and expensive traces from $A$ are reported late, even when the
systems have identical outcome distributions. We enroll 100 pairs per
tick, up to 6,000, and reveal all outcomes within 20 ticks of enrollment.
This directly simulates the balanced oriented score law, without running
agents or assigning production users. Each of 1,000 repetitions per
scenario is shared by three methods: completed-only selection, completed
prefixes, and partial-score prefix inference. The two valid methods use
the same candidate prefixes, positive bets, and same-prefix conjunction
of preference superiority and success noninferiority at margin 0.03.
Missing bits admit both outcomes; unrevealed cost signs admit all signs.
The bounds do not infer hidden values from the informative reveal clock.
'''
text+=f'''\nUnder identical outcomes, completed-only selection falsely deployed in
{int(bad['deployments'])} of 1,000 repetitions, whereas each valid method
deployed in {int(n['deployments'])} (0.6\\%; Wilson 95\\% interval,
{100*float(n['rate_ci_lower']):.3f}--{100*float(n['rate_ci_upper']):.3f}\\%).
Under the cheaper alternative, both valid methods deployed in
{int(p['deployments'])} of 1,000 repetitions.
Partial evidence reduced mean capped decision time from
{float(c['mean_calendar_time_capped']):.3f} to {float(p['mean_calendar_time_capped']):.3f} ticks;
the paired gain was {float(g['mean_capped_calendar_gain']):.3f}
(Monte Carlo standard error {float(g['gain_mcse']):.3f}).
Mean initiated executions fell from
{float(c['mean_agent_executions_initiated']):.1f} to {float(p['mean_agent_executions_initiated']):.1f}.
No partial decision occurred later than its comparator, and all
{int(g['partial_strictly_earlier_count'])} deployment paths were strictly earlier.
Identical final decisions after complete revelation are guaranteed by
the matched prefix construction, not evidence of universally high power.
The magnitude of the gain depends on this particular reveal mechanism.\n'''
text+=r'''
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{../results/async_operating.pdf}
\caption{Informative-delay score simulation. Partial-score prefix
inference retains the complete-data threshold guarantee while using
incomplete episodes. Completed-only selection targets a biased subset.
Calendar ticks and cost units are synthetic. Curves show the fraction
that has deployed, using the same latent draws for all methods.}
\label{fig:async}
\end{figure}
'''
(R/'paper/async_results.tex').write_text(text)
appendix=r'''\section{Delayed-feedback experiment details}
\label{app:async_exp}
The master seed is 2026091803, with independent scenario child seeds.
Success bits are independent Bernoulli(0.90), and positive costs are
independent lognormal variables with log standard deviation 0.45,
independent of success. The $A/B$ scale ratio is $r=1$ or $0.55$.
The analytic success difference is zero and net benefit is
\[
 0.9^2\left[\Phi\!\left(\frac{\log(0.95)-\log r}{\sqrt2(0.45)}\right)
 -1+\Phi\!\left(\frac{-\log(0.95)-\log r}{\sqrt2(0.45)}\right)\right].
\]
The null value is exactly zero; the alternative is approximately 0.52724.
The hierarchy compares success first, then cost with 5\% relative
maximum-cost tolerance when both succeed; joint failures tie.

Pairs enroll at ticks 1--60 in batches of 100. $A$'s success grade arrives
one tick after enrollment if successful and 20 ticks later otherwise;
$B$'s grade always arrives after one tick. $A$'s cost arrives after two
ticks if at most 1 and after 20 ticks otherwise; $B$'s cost arrives after
two ticks. This outcome-dependent telemetry is identical across scenarios.
The construction deliberately favors early favorable $A$ measurements.
No record remains permanently missing. The last look is tick 80.

A complete pair has both success grades and, only when both succeed,
both costs. Thus irrelevant pending costs do not hold up the completed
baseline. At each tick the valid methods consider the same deterministic
prefix grid $100,150,\ldots,6000$. Both gates must cross 20 at one common
prefix. Complete-prefix inference considers every grid prefix with all
required scores determined, not just the latest prefix. The partial
method additionally considers enrolled prefixes with unresolved scores.
Each gate uses 40 equal-weight geometric bets from $10^{-4}$ to
$0.99/(1+c)$, where $c=0$ or $-0.03$. All choices were recorded before
execution; this was an internal dated protocol, not public preregistration.

For each missing success bit, enumerate both possible values. Component
lower bounds are the smallest feasible success difference. The hierarchy
lower bound is the minimum over these possible success pairs: discordant
success determines the sign, joint failure ties, and joint success permits
all three cost signs unless both costs are observed. These deliberately
broad sets remain valid without using a model for the delay distribution.
Observed timing is not treated as a perfect classifier of a hidden bit.
The score bounds are ternary and are checked by exhaustive finite-state
cases and samplewise containment against simulated complete outcomes.

Nondeployments receive the cap of 80 ticks and 12,000 initiated executions.
Execution counts are twice the number enrolled before the hypothetical
procedure stops; generated latent values after that stopping point are
used solely for paired method comparison. The reported observed cost
sums measure telemetry completeness, not dollars paid or expenditure
saved. The source, configuration, protocol and result hashes, numerical
tables, paired gains, and complete deployment curves are supplied.
The verification checks include partial-wealth domination, same-prefix
gating, non-later stopping, and equal final decisions after full reveal.
The finite simulation does not test the ongoing-enrollment consistency
propositions, which require $n\to\infty$ and vanishing unresolved width.

\begin{table}[h]
\centering\small
\caption{Frozen delay study, 1,000 repetitions per row. Means cap
nondeployments at 80 ticks and 12,000 initiated executions.}
\begin{tabular}{llrrr}
\toprule
Scenario & Procedure & Deployments & Mean ticks & Executions\\
\midrule
'''
for x in rows:
    scenario='Equal outcomes' if x['scenario']=='identical_outcomes' else 'Cheaper $A$'
    method={'naive_completed_only':'Completed only (invalid)','complete_prefix':'Complete prefixes','partial_prefix_envelope':'Partial prefixes'}[x['method']]
    appendix+=f"{scenario} & {method} & {int(x['deployments'])} & {float(x['mean_calendar_time_capped']):.3f} & {float(x['mean_agent_executions_initiated']):.1f}\\\\\n"
appendix+=r'''\bottomrule
\end{tabular}
\end{table}
'''
(R/'paper/async_appendix.tex').write_text(appendix)
print('Generated delay-study main text and appendix from six result rows.')
