#!/usr/bin/env python3
"""Build descriptive trace-replay text from the complete archived result tables."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with (ROOT / 'results/trace_certificate_pairs.csv').open() as stream:
        pairs = list(csv.DictReader(stream))
    with (ROOT / 'results/trace_certificate_summary.csv').open() as stream:
        summaries = list(csv.DictReader(stream))
    total = len(pairs)
    early = sum(int(p['ordinal_resolution_lead']) > 0 for p in pairs)
    before_messages = sum(int(p['ordinal_resolution_lead']) >= 2 for p in pairs)
    marker_only = early - before_messages
    rows = []
    for summary in summaries:
        group = [p for p in pairs if all(p[k] == summary[k] for k in ('domain', 'model_a', 'model_b'))]
        n = len(group)
        e = sum(int(p['ordinal_resolution_lead']) > 0 for p in group)
        m = sum(int(p['ordinal_resolution_lead']) >= 2 for p in group)
        assert n == int(summary['comparisons']) and e == int(summary['early_certificates'])
        rows.append(f"{summary['domain'].capitalize()} & {summary['model_a']} / {summary['model_b']} & {n:,} & {100*e/n:.1f} & {100*m/n:.1f} \\\\")
    prefixes = sum(int(p['prefixes_checked']) for p in pairs)
    tier_two = sum(p['certificate_possible_decisive_tiers'] == 'success|cost' for p in pairs if int(p['ordinal_resolution_lead']) > 0)
    tier_three = sum(p['certificate_possible_decisive_tiers'] == 'success|cost|tools' for p in pairs if int(p['ordinal_resolution_lead']) > 0)
    assert tier_two + tier_three == early
    text = r"""\paragraph{Certificates from actual archived prefixes.}
We replayed all nine retained $\tau^2$ source files, comprising 3,336
episodes and 51,247 assistant messages. With final labels hidden until
a terminal marker and pending resources bounded only by accrued values,
%EARLY% of %TOTAL% off-diagonal comparisons (%PCT%\%) had a guaranteed
sign before the later terminal marker. Of all comparisons, %MPCT%\% resolved
while at least one actual assistant message remained unseen; the rest of
the early cases preceded only the artificial terminal marker. Every
one of %PREFIXES% prefix intervals contained the archived final sign.
The replay uses ordinal message ticks, not observed concurrent time, and
does not test a sequential deployment rule or estimate execution savings.
Appendix~\ref{app:trace_certificates} reports every contrast and the
completion-set audit.
"""
    replacements = {'%EARLY%': f'{early:,}', '%TOTAL%': f'{total:,}', '%PCT%': f'{100*early/total:.1f}',
                    '%MPCT%': f'{100*before_messages/total:.1f}', '%PREFIXES%': f'{prefixes:,}'}
    for key, value in replacements.items():
        text = text.replace(key, value)
    (ROOT / 'paper/trace_certificate_results.tex').write_text(text)
    appendix = r"""\section{Feasible certificates from archived agent trajectories}
\label{app:trace_certificates}
\paragraph{Design and information boundary.}
This descriptive audit uses the same nine hashed $\tau^2$ archives as
the historical comparison: three models, 278 tasks, four trials, and all
three fixed model contrasts. Twelve off-diagonal seed-index comparisons
per task and contrast give %TOTAL% dependent comparisons. The analysis
specification was frozen before the replay aggregates were computed,
after the archive and its complete-outcome analysis were known. It is
an internal protocol, not external preregistration or a newly sampled
benchmark. We retain every domain/contrast combination.

At integer tick $k$, expose the $k$th actual assistant message of each
arm, including its accrued cost and issued tool calls. Zero-cost initial
messages remain in the sequence. The final success label, cost, and
tool-call total become available at a terminal marker one tick after
that arm's last assistant message. This accommodates trailing records
and final verification by convention; it is not an observed grading
delay. The rule receives only revealed values. It never uses a pending
episode's final label, length, cost, or future messages to tighten bounds.

\paragraph{Cost reconciliation and completion sets.}
All 3,336 episodes and 51,247 assistant messages had finite nonnegative
costs; 3,336 zero-cost initial messages were retained. Summed message
costs agreed with final recorded agent cost within the specified
tolerance; the largest absolute discrepancy was
$3.565\times10^{-16}$. Decimal arithmetic uses the archived numeric
strings. From every pending cumulative cost we subtract the same
conservative allowance, $7.446604\times10^{-10}$, clipping at zero.
This archive-wide maximum reconciliation allowance is fixed by the
initial audit; it widens the sets and does not disclose a pending
episode's own final value. Cost and tool counts have no inferred upper
bound. Pending success remains in $\{0,1\}$.

Enumerating feasible success bits and resource signs gives a conservative
interval for success first, then cost with 5\% relative tolerance among
joint successes, then issued tool calls. Two failures tie. There is no
independent safety label or safety tier. If $A$ has completed successfully
and $B$'s certified cost lower bound exceeds $c_A/0.95$, every
completion favors $A$: $B$ either fails, or succeeds at a losing cost.
Such a certificate determines the sign without determining the eventual
deciding tier. All %EARLY% early certificates retained this ambiguity:
%TWO% allowed success or cost, and %THREE% also allowed the tools tier.
We do not report these as early verified successes or as known cost-tier
wins. The supplied diagnostic examples contain only revealed values;
retrospective pair records separately contain final tiers and lead times.

\begin{table}[t]
\centering\small
\caption{All archived trace-certificate comparisons. Percentages use
the full row denominator. ``Before last marker'' means before the later terminal
marker; ``Before messages'' additionally requires at least one actual
assistant message to remain unseen. The difference measures sensitivity
to the added terminal-marker convention. These are descriptive,
dependent comparisons, not binomial trials.}
\label{tab:trace_certificates}
\begin{tabular}{llrrr}
\toprule
Domain & Models $A/B$ & Pairs & Before last marker (\%) & Before messages (\%)\\
\midrule
%ROWS%
\midrule
All & All three contrasts & %TOTAL% & %PCT% & %MPCT% \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Validation and interpretation.}
All %PREFIXES% prefix intervals contained the archived final sign, were
nested, and collapsed after completion. Final Decimal signs matched
the existing floating-point comparator on all %TOTAL% comparisons.
A separate implementation reconstructed every prefix from the raw
archives with a closed-form completion rule and reproduced all early
resolution times. Independent perturbation checks confirmed that hidden
final values and future suffixes do not alter a pending revealed state.
Among the %EARLY% early resolutions, %MARKER% led only the terminal
marker by one tick; %MESSAGES% occurred while actual messages remained.
This secondary descriptive split was added during independent review,
without changing the frozen replay or selecting contrasts.

The completion-only comparator resolves at the later terminal marker,
when both final labels and resources are known. Table~\ref{tab:trace_certificates}
shows that useful completion bounds occur in real archived records,
including the motivating retail and telecom contrasts. However, the
ordinal schedule is artificial, original grader labels may be imperfect,
and cross-run comparisons share tasks and trajectories. We perform no
population confidence interval, sequential hypothesis test, deployment
decision, or wall-clock saving calculation from these counts. A live
evaluation must validate its own terminal semantics, irrevocable costs,
grader errors, enrollment assumptions, and information available at each
decision. These observations establish archival certificate feasibility,
not operational latency or deployment benefit.
"""
    replacements.update({'%ROWS%': '\n'.join(rows), '%TWO%': f'{tier_two:,}', '%THREE%': f'{tier_three:,}',
                         '%MARKER%': f'{marker_only:,}', '%MESSAGES%': f'{before_messages:,}'})
    for key, value in replacements.items():
        appendix = appendix.replace(key, value)
    (ROOT / 'paper/trace_certificate_appendix.tex').write_text(appendix)
    print(f'Trace manuscript: {early}/{total} before markers; {before_messages}/{total} before remaining messages.')


if __name__ == '__main__':
    main()
