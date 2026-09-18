"""Generate manuscript tables and figures solely from executed result files."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
def main():
    d=pd.read_csv(ROOT/'results'/'simulation_results.csv',keep_default_na=False)
    names={'null':'Identical agents','efficiency_gain':'Efficiency gain','success_regression':'Success regression',
           'safety_regression':'Compliance regression','joint_gain':'Joint gain','weak_gain':'Weak gain'}
    methods=['win_only_betting','guarded_betting','guarded_repeated_wald','guarded_group_bonferroni_wald','guarded_fixed_wald']
    rows=[]
    for s,label in names.items():
        rates=[d[(d.scenario==s)&(d.method==m)].iloc[0].deployment_rate*100 for m in methods]
        rows.append(label+' & '+' & '.join(f'{x:.2f}' for x in rates)+r' \\')
    table='\n'.join(rows)
    text=r'''\paragraph{Synthetic online streams.}
We generated six stationary independent-arrival scenarios, each with
2,000 independent repetitions and at most 10,000 pairs (20,000 agent
executions). Compliance and success are Bernoulli outcomes; cost is
lognormal. The primary hierarchy is compliance, success, then cost among
jointly compliant successful pairs. The guarded rule requires positive
net benefit, a success difference above $-0.03$, and a compliance
difference above $-0.01$. These illustrative margins were fixed before
viewing the initial numerical results. Alpha is 0.05. Monitoring begins
at 100 pairs and occurs every 50 pairs, additionally including the ten
prespecified group looks. Analytic net-benefit targets are independently
checked in the code.

\begin{table}[t]
\centering\small
\caption{Deployment probability (\%) over 2,000 synthetic repetitions.
Win-only betting addresses composite preference; guarded methods require
the same three gates. Repeated Wald is unadjusted; group Wald uses ten
planned looks with Bonferroni allocation. Wald validity is asymptotic.
The normal-mixture guarded baseline made no deployments in these settings.}
\label{tab:simulation}
\begin{tabular}{lrrrrr}\toprule
 & Win only & Guarded & Repeated & Group & Fixed\\
 & betting & betting & Wald & Wald & Wald\\\midrule
''' +table+r'''
\bottomrule\end{tabular}
\end{table}

Under identical agents, guarded betting made 9/2,000 deployments
(0.45\%; 95\% Wilson interval 0.24--0.85\%), while unadjusted repeated
Wald inspection made 621/2,000 (31.05\%; 29.06--33.11\%). The valid
guarded betting procedure deployed the cheaper, equally effective agent
in 96.85\% of repetitions. Win-only betting favored the cheaper agent in
every success-regression and compliance-regression repetition; guarded
betting made no deployments in either scenario (0/2,000; upper Wilson
limit 0.192\%). These are failures of a preference-only deployment rule,
not false rejections of the composite-preference null, which is false
in those scenarios.

The range-only normal-mixture rule made no deployments in any initial
scenario. Its width at 10,000 balanced pairs is about 0.033, too large to
resolve the 0.01 compliance margin when the compliance difference is
near zero. This is a documented conservatism cost of that baseline, not
evidence that anytime-valid inference generally lacks power. Directional
betting uses the observed score distribution and is materially more
useful here. We do not infer uniform power superiority over competitive
empirical-Bernstein or sequential U-statistic methods.

\paragraph{Targeted stress tests.}
Extensions designed after the initial run placed each guardrail exactly
on its null boundary. Guarded betting deployed in 0.75\% of
success-boundary and 0.45\% of compliance-boundary repetitions; repeated
Wald deployed in 32.40\% and 30.45\%. A separate repeated-run experiment
with 40 task clusters and four runs per arm gave 95.25\% coverage for a
task-level $t$ interval, versus 55.65\% when all 16 within-task comparisons
were incorrectly treated as independent. In a nonexchangeable-pair
stress model with adaptive order probabilities and zero symmetric
preference, unweighted normal-mixture monitoring rejected in 93.0\%
of 1,000 repetitions. Correctly weighted betting rejected in 1.1\%
and the conservative weighted normal-mixture rule in 0\%. This abstract
bounded-score experiment isolates weighting bias; it does not simulate
full agent traces.

\IfFileExists{public_results.tex}{\input{public_results.tex}}{}
\IfFileExists{prospective_results.tex}{\input{prospective_results.tex}}{}
'''
    (ROOT/'paper'/'results_main.tex').write_text(text)
    app=r'''\section{Experimental details and full numerical outputs}
\label{app:experiments}
The executable sources and CSV files accompanying this paper are the
canonical numerical record. The primary synthetic data-generating
parameters are listed below. Each pair independently draws two agents'
compliance and success indicators; costs have log standard deviation
0.45, with the indicated A/B scale ratio. The cost tie threshold is 5\%
of the larger cost. Success and compliance are distinct measurements:
an episode can complete the task while violating policy.
\begin{center}\small
\begin{tabular}{lrrrrr}\toprule
Scenario & Compliance A & Compliance B & Success A & Success B & Cost A/B\\\midrule
Identical & .995 & .995 & .75 & .75 & 1.00\\
Efficiency gain & .995 & .995 & .75 & .75 & .55\\
Success regression & .995 & .995 & .65 & .75 & .40\\
Compliance regression & .975 & .995 & .75 & .75 & .45\\
Joint gain & .995 & .995 & .84 & .75 & .75\\
Weak gain & .995 & .995 & .76 & .75 & 1.00\\\bottomrule
\end{tabular}\end{center}
The initial simulation uses seed 20260917 with separate scenario streams.
Each gate uses an equal mixture of 40 bets geometrically spaced from
$10^{-4}$ to $0.99/(1+c)$, where $c$ is its threshold; no bet is selected
by looking at the results. Normal-mixture bounds fix $\rho=100$.
Unadjusted and fixed-horizon Wald comparisons use one-sided 0.05 cutoffs.
The ten-look group comparator uses a one-sided 0.005 cutoff at each
look. It is a simple multiplicity-adjusted asymptotic baseline, not an
implementation of a particular published group-sequential win-ratio
covariance estimator. A capped stopping time equals 10,000 when no
deployment occurs; conditional stopping times among deployments are
reported separately in the CSV and must not be conflated with expected
sample use.

The boundary, dependence, and adaptive-order extensions use seed
20260918. Boundary compliance and success are set to 0.985 versus 0.995
and 0.72 versus 0.75, respectively, with cost ratio 0.4. The dependence
experiment generates a normal task-specific A--B contrast with standard
deviation 1.2 and four independent unit-normal run errors per arm; its
unconditional signed preference is zero by symmetry. Task-level standard
errors use 39 degrees of freedom; the naive comparator divides the
standard deviation of all pair scores by the square root of 640.

The adaptive-order experiment sets potential score means to 0.8 and
$-0.8$ for the two assignment orientations. At pair $i$, the order
probability is $0.1+0.8\operatorname{expit}(1+S_{i-1}/\sqrt i)$, where
$S_{i-1}$ sums past unweighted scores. This is predictable and obeys
positivity. The inverse-probability score has symmetric target zero and
lies in $[-5,5]$; betting and normal-mixture bounds use the appropriate
range. It has 1,000 repetitions, at most 3,000 pairs, and looks every ten
pairs after pair 100.

\begin{figure}[h]\centering
\includegraphics[width=\linewidth]{../results/simulation_operating.pdf}
\caption{Observed deployment rates and capped mean sample use. Bars are
Monte Carlo summaries, not evidence of universal ordering. Error bars
are 95\% Wilson intervals for rates and 1.96 Monte Carlo standard errors
for mean pair counts. The nominal horizontal line applies to false
deployment under the composite deployment null.}
\end{figure}
\IfFileExists{public_appendix.tex}{\input{public_appendix.tex}}{}
'''
    (ROOT/'paper'/'experiments_appendix.tex').write_text(app)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(10,3.4))
    selected=['guarded_betting','guarded_repeated_wald','guarded_group_bonferroni_wald','guarded_fixed_wald']
    colors=['#1c6e8c','#b7463a','#bd923d','#69776e']
    x=np.arange(len(names)); width=.18
    for j,(method,color) in enumerate(zip(selected,colors)):
        sub=d[d.method==method].set_index('scenario').loc[list(names)]
        dx=x+(j-1.5)*width
        y=sub.deployment_rate.values
        err=np.maximum(np.stack([y-sub.rate_ci_lower.values,sub.rate_ci_upper.values-y]),0)
        axes[0].bar(dx,y,width,color=color,label=method.replace('guarded_','').replace('_',' '))
        axes[0].errorbar(dx,y,yerr=err,fmt='none',ecolor='#222222',lw=.6,capsize=1)
        axes[1].bar(dx,sub.mean_pairs_used/1000,width,color=color)
        axes[1].errorbar(dx,sub.mean_pairs_used/1000,yerr=1.96*sub.mean_pairs_mcse/1000,fmt='none',ecolor='#222222',lw=.6,capsize=1)
    axes[0].axhline(.05,color='#444',ls='--',lw=.7); axes[0].set_ylabel('Deployment probability')
    axes[1].set_ylabel('Mean pairs used (thousands)')
    for ax in axes:
        ax.set_xticks(x,[v.replace(' ','\n',1) for v in names.values()],fontsize=7)
    axes[0].legend(fontsize=7,loc='upper left',bbox_to_anchor=(0,1.3),ncol=2,frameon=False)
    fig.tight_layout()
    fig.savefig(ROOT/'results'/'simulation_operating.pdf',bbox_inches='tight')
    fig.savefig(ROOT/'results'/'simulation_operating.png',dpi=170,bbox_inches='tight')
    plt.close(fig)
    public=pd.read_csv(ROOT/'results'/'public_comparisons.csv')
    cases=public[(public.configuration=='primary')&(public.model_a=='o4-mini')&(public.model_b=='Claude-3.7')&public.domain.isin(['retail','telecom'])]
    fig,axes=plt.subplots(1,2,figsize=(6.7,2.5),sharey=True)
    yy=np.arange(len(cases))
    for ax,key,lo,hi,title in [(axes[0],'net_benefit','nb_ci_low','nb_ci_high','Prioritized net benefit'),(axes[1],'success_diff','success_ci_low','success_ci_high','Task-success difference')]:
        xx=cases[key].to_numpy(); low=cases[lo].to_numpy(); high=cases[hi].to_numpy()
        ax.errorbar(xx,yy,xerr=np.stack([xx-low,high-xx]),fmt='o',color='#1c6e8c',capsize=4)
        ax.axvline(0,color='#888888',lw=.8); ax.set_title(title,fontsize=10)
        ax.grid(axis='x',alpha=.15); ax.set_ylim(1.6,-.6)
    axes[0].set_yticks(yy,[x.capitalize() for x in cases.domain])
    axes[1].axvline(-.03,color='#b7463a',linestyle='--',label='Illustrative -3 pp limit')
    axes[1].legend(fontsize=7.5,loc='lower left',frameon=False)
    fig.suptitle('o4-mini versus Claude-3.7: historical task-matched comparisons',fontsize=10)
    fig.tight_layout()
    fig.savefig(ROOT/'results'/'public_guardrail_reversal.pdf',bbox_inches='tight')
    fig.savefig(ROOT/'results'/'public_guardrail_reversal.png',dpi=170,bbox_inches='tight')
    plt.close(fig)

if __name__=='__main__': main()
