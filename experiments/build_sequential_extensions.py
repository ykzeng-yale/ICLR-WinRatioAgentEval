"""Build audited comparator/drift manuscript summaries from retained CSVs only."""
from pathlib import Path
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def rows(name):
    with (ROOT / name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def lookup(data, **keys):
    selected = [r for r in data if all(r[k] == v for k, v in keys.items())]
    if len(selected) != 1:
        raise ValueError(f'Expected one row: {keys}; found {len(selected)}')
    return selected[0]


def rate(row, prefix='rate_ci', field='deployment_rate'):
    lo, hi = (prefix + '_lower', prefix + '_upper') if prefix == 'rate_ci' else (prefix + '_lo', prefix + '_hi')
    return f"{100*float(row[field]):.2f} [{100*float(row[lo]):.2f}, {100*float(row[hi]):.2f}]"


def main():
    inputs = ['results/ustat_reference/null_calibration.csv',
              'results/ustat_reference/ustat_reference_results.csv',
              'results/ustat_reference/ustat_reference_efficiency.csv',
              'results/drift_panel/results.csv', 'results/drift_panel/permutation_results.csv',
              'results/ustat_reference/rare_event_diagnostic.csv']
    calibration, comparison, efficiency, drift, permutation, diagnostic = map(rows, inputs)
    assert len(calibration) == 164 and len(comparison) == 160 and len(drift) == 108
    assert len(permutation) == 9
    gaussian_crossings = [r for r in diagnostic if r['rule'] == 'allpairs_asympcs_projection_gaussian']
    assert len(gaussian_crossings) == 725
    assert sum(int(r['first_crossing_runs_per_arm']) <= 500 for r in gaussian_crossings) == 410
    assert sum(int(r['noncompliant_a']) == 0 for r in gaussian_crossings) == 239
    methods = [('All-pairs fixed Wald', 'allpairs_fixed_wald'),
               ('All-pairs OBF', 'allpairs_gs_obf'),
               ('All-pairs Pocock', 'allpairs_gs_pocock'),
               ('All-pairs HSD', 'allpairs_gs_hsd'),
               ('Projection Gaussian', 'allpairs_asympcs_projection_gaussian'),
               ('Disjoint OBF', 'disjoint_gs_obf'),
               ('Disjoint betting', 'disjoint_betting')]
    calibration_lines = []
    for label, method in methods:
        gate = lookup(calibration, scenario='compliance_boundary', method='gate_compliance_' + method)
        simultaneous = lookup(calibration, scenario='compliance_boundary', method='guarded_' + method + ('' if 'fixed' in method else '_simultaneous'))
        retained = lookup(calibration, scenario='compliance_boundary', method='guarded_' + method + ('' if 'fixed' in method else '_retained'))
        for row in (gate, simultaneous, retained):
            assert int(row['replicates']) == 10000
            assert abs(float(row['deployment_rate']) - int(row['deployments']) / 10000) < 1e-12
        calibration_lines.append(label + ' & ' + ' & '.join(map(rate, (gate, simultaneous, retained))) + r' \\')
    power_lines = []
    for label, method in methods:
        method = 'guarded_' + method + ('' if 'fixed' in method else '_simultaneous')
        out = []
        for scenario in ('efficiency_gain', 'joint_gain'):
            row = lookup(comparison, scenario=scenario, method=method)
            out += [f"{100*float(row['deployment_rate']):.2f}",
                    f"{float(row['mean_runs_per_arm_used']):.0f} ({float(row['mean_runs_mcse']):.0f})"]
        power_lines.append(label + ' & ' + ' & '.join(out) + r' \\')
    normal = lookup(drift, scenario='A1_identical_null', rule='guarded_betting')
    naive = lookup(drift, scenario='A1_identical_null', rule='guarded_repeated_wald')
    assert int(normal['ever_deploy_count']) == 55 and int(naive['ever_deploy_count']) == 2686
    drift_lines = []
    for scenario, label in [('A1_identical_null','Common drift: identical'),
                            ('A2_success_boundary','Common drift: success boundary'),
                            ('A3_compliance_boundary','Common drift: compliance boundary'),
                            ('B3a_alternating_violator','Alternating running violation'),
                            ('B3b_cycling_violator','Cycling running violation'),
                            ('C1_unequal_law_null','Unequal-law mean-win null'),
                            ('C2_unequal_law_null_tie_heavy','Unequal-law, many ties')]:
        values=[]
        for method in ['guarded_betting','guarded_normal_mixture_split','guarded_repeated_wald']:
            row=lookup(drift,scenario=scenario,rule=method)
            assert int(row['replicates']) == 10000
            values.append(rate(row,prefix='E_running_any',field='E_running_any_rate'))
        drift_lines.append(label+' & '+' & '.join(values)+r' \\')

    main_text = r'''\paragraph{Competitive sequential comparison and drift.}
A separate equal-execution-budget comparison includes all-pairs Wald,
three alpha-spending designs, and projection-Gaussian monitoring.
At the rare-compliance boundary, the last method rejected the component
gate in 7.25\% of 10,000 repetitions but deployed under the simultaneous
guarded rule in 1.83\%; those are different error events. Its asymptotic
guarantee does not promise finite-sample 5\% control from the first look.
In an independently reproduced drift extension, guarded betting falsely
deployed in 0.55\% of 10,000 common-drift null streams, versus 26.86\%
for repeated Wald. Appendices~\ref{app:ustat_extension}--\ref{app:drift_extension}
report the matched comparisons, uncertainty, moving targets and power costs.
'''
    ustat_text = r'''\section{Equal-budget sequential all-pairs comparison}
\label{app:ustat_extension}
This extension uses the same compliance--success--cost generator and
three component thresholds as the primary study, but a separate seed
suite: seed 20260918 rather than the primary 20260917. It includes eight
scenarios with 2,000 repetitions each, plus four null/boundary scenarios
with 10,000 repetitions each. The main comparison uses 199 looks from
100 to 10,000 records per arm; group-sequential rules use ten planned
looks at equally spaced information fractions. A look with $n$ records
per arm costs $2n$ executions for either the disjoint or all-pairs method.
The saved disjoint-betting rows reproduce the separate online-comparator
pipeline exactly, not the primary table's different random seed stream.

\paragraph{Procedures and validity classes.}
The all-pairs estimate is $U_n=n^{-2}\sum_{i,j}h(A_i,B_j)$, with
row/column projection variance estimate
$(\widehat\sigma_A^2+\widehat\sigma_B^2)/n$.
Fixed Wald and the O'Brien--Fleming (OBF), Pocock, and Hwang--Shih--DeCani
(HSD, parameter $-3$) spending comparisons use the Gaussian-limit
covariance at nested looks, following the sequential win-statistic
frameworks of \citet{zhang2024sequential,bergemann2026group}.
The information fraction $n/N$ is a first-order approximation; the
nonlinear statistic does not have exactly independent Gaussian increments
at finite sample sizes. At the first look $n=100$, saved Monte Carlo
estimates of population variance components put the omitted residual term between
$5.94\times10^{-6}$ and $2.49\times10^{-5}$, or 0.13--0.41\% of the
first-order term. This is not a bound on plug-in variance-estimation error.

The projection-Gaussian reference subtracts a one-sided normal-mixture
boundary multiplied by the estimated projection standard deviation.
Its justification is asymptotic, using the time-uniform Gaussian
approximation perspective of \citet{waudbysmith2024timeuniform}.
For $X_i=(A_i,B_i)$ and
$k(X_i,X_j)=\{h(A_i,B_j)+h(A_j,B_i)\}/2$, its one-sample U-statistic
$U_n^*$ obeys $|U_n-U_n^*|\leq2/n$. Its linear projection term has
asymptotic variance $\sigma_A^2+\sigma_B^2$ under independent arms;
the first Hoeffding projection of $k$ itself has one quarter of that
variance. Bounded kernels,
nondegenerate projection variance and a consistent variance estimate
support the asymptotic comparison. This is not a finite-sample
5\% crossing guarantee from $n=100$, nor an implementation of the
delayed-start family in \citet{cai2026ustatistics}.
Disjoint betting retains its stated finite-sample guarantee.

\paragraph{Compare the same decision event.}
The primary comparator requires every gate to pass at the same look.
A separately reported retained-crossing rule remembers each gate's
first crossing. These are distinct procedures even under stationarity;
retention is not used to certify a current drifting conjunction.
Table~\ref{tab:ustat_calibration} separates component rejection from
the two guarded events at the compliance boundary $\Delta_C=-0.01$,
with the other targets favorable. All intervals are pointwise 95\%
Wilson Monte Carlo intervals. A rate compatible with 5\% at this
precision is not a proof of uniform calibration.

\begin{table}[h]\centering\scriptsize
\caption{Rare-compliance boundary: rates (\%) and Monte Carlo intervals,
10,000 repetitions. The three columns concern different events.}
\label{tab:ustat_calibration}
\begin{tabular}{lrrr}\toprule
Rule & Component gate & Guarded, same look & Guarded, retained\\\midrule
''' + '\n'.join(calibration_lines) + r'''
\bottomrule\end{tabular}\end{table}

The projection-Gaussian component excess does not contradict its
asymptotic validity statement, and the low guarded rate does not certify
the underlying component test. An independently reproduced diagnostic
finds that 410 of its 725 component rejections first occur by 500 records
per arm, with 239 having no observed noncompliant A records at crossing.
These conditional-on-rejection summaries are consistent with unstable
rare-event variance estimation, but do not prove the mechanism or a remedy.

\begin{table}[h]\centering\small
\caption{Same-look guarded decisions, separate 2,000-repetition comparison.
Use is mean capped records per arm, with its Monte Carlo standard error
in parentheses; multiply by two for executions. Full rate intervals and
all eight scenarios are in the supplied CSV.}
\label{tab:ustat_power}
\begin{tabular}{lrrrr}\toprule
 & \multicolumn{2}{c}{Efficiency gain} & \multicolumn{2}{c}{Joint gain}\\
Rule & Deploy (\%) & Use (MCSE) & Deploy (\%) & Use (MCSE)\\\midrule
''' + '\n'.join(power_lines) + r'''
\bottomrule\end{tabular}\end{table}

All-pairs estimation reduces asymptotic variance in these settings,
but differences in boundaries, looks and calibration also affect stopping
and power. Identical raw component point estimates do not imply identical
estimated variances or stopping times. Table~\ref{tab:ustat_power} is a
descriptive comparison, not a paired significance or equivalence test.
All four calibration scenarios, all seven component procedures and both
crossing conventions are retained in the numerical supplement.
'''
    drift_text = r'''\section{Drift and unequal-law nulls}
\label{app:drift_extension}
This CPU-only extension uses seed 20260919 and twelve synthetic scenarios:
common difficulty/resource drift, treatment-by-time changes, switching
violated components, and equal-mean-win nulls with unequal outcome laws.
Null/boundary/drift scenarios use 10,000 repetitions each; three power
scenarios use 2,000. Nine rules share the same streams and 199 candidate
evaluation times, with at most 10,000 pairs (20,000 executions).
Group-sequential rules use only their ten allowed looks and fixed rules
only the final look. The scenarios have
independent pairs and deterministic parameter paths, not adaptive
candidate changes or production users. Exact target paths were checked
by separate enumeration/quadrature and Monte Carlo; an independent full
rerun reproduced both numerical CSVs byte-for-byte.

We distinguish an erroneous first decision from an erroneous decision
at any scheduled look. Table~\ref{tab:drift_extension} reports the latter:
some look has deployment while at least one claimed running-average
component is at or below its threshold. It is a finite-grid Monte Carlo
assessment; continuous monitoring guarantees come from the theory, not
from this grid. Program-wide error across repeated experiments is a
separate multiplicity question. Only the criteria claimed by a rule
define its error: a win-only deployment in a component-regression scenario
is not a false rejection of a favorable composite mean.

\begin{table}[h]\centering\scriptsize
\caption{False running-target deployment at any scheduled look (\%),
with pointwise 95\% Wilson intervals, over 10,000 repetitions per row.
Betting uses level 0.05 per gate; the normal-mixture rule splits 0.05
across the three gates. These allocations have different guarantees.}
\label{tab:drift_extension}
\begin{tabular}{lrrr}\toprule
Scenario & Guarded betting & Split normal mixture & Repeated Wald\\\midrule
''' + '\n'.join(drift_lines) + r'''
\bottomrule\end{tabular}\end{table}

When one fixed claimed gate violates its threshold at every prefix,
the fixed-gate argument controls deployment at level 0.05, even if
other components drift. Under switching violations, splitting alpha
controls the current-prefix conjunction; Proposition~\ref{prop:bet_running}
also supplies that conclusion for split fixed-stake betting.
Per-gate 0.05 allocation alone gives at most the three-gate union bound
in that setting. Low observed betting error is not proof of a 0.05
conjunction guarantee without the split. The split betting rule's
switching-violation rates were 0.08\% and 0.15\%.

Both versions of the range-only normal-mixture rule made no deployments
in the switching-violation cells. Thus these cells do not empirically
demonstrate a need to split alpha. Wide intervals may contribute to the
rule's conservatism, but these null configurations do not identify that
mechanism.
In the strong-all-components power scenario, splitting alpha increased
its mean capped use from 1,481 to 1,868 pairs; this is an observed
precision/power cost, not a universal ratio.

In a positive-then-negative preference path, every sequential method
deployed before the reversal, while the final running net benefit was
$-0.08$. Its earlier decision was valid for the then-running target;
neither running-target inference nor a correct first decision ensures
future effectiveness. The unequal-law nulls separately show that equality
of outcome distributions and zero prioritized mean are different nulls.
A label-permutation test of distributional equality rejected in 94.3\%
and 100\% of two unequal-law cells, while guarded betting false-deployment
rates for its mean-win claim were 0.64\% and 0.73\%.

\paragraph{Protocol and audit scope.}
The contributed extension records an internally frozen protocol and a
post-run correction to a descriptive win-only diagnostic. The first
uncorrected run was not retained, so its asserted single-field change
and exact first-run chronology cannot be independently reconstructed;
the current outputs and targets were independently reproduced. The
original broad protocol also proposed more tie, Pareto-cost and grader
panels and larger power replication counts than the principal studies
executed here. Those panels remain deferred; the tables and manifests
state the actual scenarios and Monte Carlo counts. No completion claim
is based on unexecuted protocol items.
'''
    outputs={'paper/sequential_extension_results.tex': main_text,
             'paper/ustat_extension_appendix.tex': ustat_text,
             'paper/drift_extension_appendix.tex': drift_text}
    for name,text in outputs.items():
        (ROOT/name).write_text(text)
    manifest={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'inputs':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in inputs},
              'outputs':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in outputs},
              'interpretation':'Separate matched-comparison seed suite and drift extension; no new model inference.'}
    (ROOT/'results/sequential_extension_paper_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Generated three manuscript sections from accepted comparator and drift records.')


if __name__=='__main__':
    main()
