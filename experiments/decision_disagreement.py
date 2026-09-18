"""Decision-disagreement matrix on released agent trajectories.

For every ordered system pair (A vs B) and domain we record the decision of
several rules that practitioners use, all computed from the same runs:
  * success_only: task-clustered paired test on the success-rate difference
    (two-sided 95% CI excludes 0 -> A better / B better / undecided)
  * pareto: A dominates B on (success, cost) marginals, B dominates A, or neither
  * linear_utility(lambda): sign of [success - lambda*cost] difference for a
    grid of lambda (success-rate units per USD), with task-clustered CI
  * hierarchical_nb: primary hierarchy (success > cost 5% > steps, absorbing
    failure) net benefit with task-clustered 95% CI
  * guarded: hierarchical NB lower bound > 0 AND success difference lower
    bound > -0.03 (illustrative margin) -> deploy A over B
Also: within-task (tau_star, 12 off-diagonal pairs) vs cross-task (tau_pop:
all runs of A against all runs of B across different tasks) net benefit, and
the prevalence of priority inversions (sign(NB) != sign(success difference)).
Historical offline runs; not live experiments. Costs at historical prices.
"""
import json, sys, itertools, hashlib
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import t as student_t
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'experiments'))
from winstats import Tier, compare
from wincs import task_level_scores, clustered_summary
from analyze_benchmarks import hierarchy, absorbing, runs_dict, SRC, OUT

LAMBDAS = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
MARGIN = 0.03


def clustered_diff(dA, dB, col, weights=None):
    a = dA.groupby('task_id')[col].mean(); b = dB.groupby('task_id')[col].mean()
    idx = a.index.intersection(b.index); d = (a.loc[idx] - b.loc[idx]).to_numpy(float)
    m = d.mean(); se = d.std(ddof=1) / np.sqrt(len(d)); q = student_t.ppf(.975, len(d) - 1)
    return m, m - q * se, m + q * se


def decide(lo, hi):
    return 'A' if lo > 0 else ('B' if hi < 0 else 'undecided')


def cross_task_nb(dA, dB, cols, tiers):
    """tau_pop: all runs of A vs all runs of B, including different tasks."""
    A = dA[cols].to_numpy(float); B = dB[cols].to_numpy(float)
    sign, _ = compare(A[:, None, :], B[None, :, :], tiers, absorbing(A[:, None, :], B[None, :, :]))
    # exclude same-task pairs to make it a pure cross-task contrast
    ta = dA.task_id.to_numpy(); tb = dB.task_id.to_numpy(); mask = ta[:, None] != tb[None, :]
    s = sign[mask]
    nb = float((s > 0).mean() - (s < 0).mean())
    # cluster bootstrap over tasks for uncertainty (resample tasks in both arms jointly)
    rng = np.random.default_rng(0); tasks = np.unique(ta); boots = []
    for _ in range(500):
        samp = rng.choice(tasks, len(tasks), replace=True)
        ia = np.concatenate([np.where(ta == t)[0] for t in samp]); ib = np.concatenate([np.where(tb == t)[0] for t in samp])
        sb = sign[np.ix_(ia, ib)]; mb = ta[ia][:, None] != tb[ib][None, :]
        sb = sb[mb]; boots.append((sb > 0).mean() - (sb < 0).mean())
    return nb, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def pair_rows(dA, dB, a, b, dom, source, cols):
    tiers = hierarchy()
    Ar = runs_dict(dA, cols); Br = runs_dict(dB, cols)
    pairing = 'offdiagonal' if all(len(v) > 1 for v in Ar.values()) else 'all'
    s = task_level_scores(Ar, Br, tiers, eligible=absorbing, pairing=pairing)
    cs = clustered_summary(s['win'], s['loss'])
    ds, ds_lo, ds_hi = clustered_diff(dA, dB, 'success')
    row = dict(source=source, domain=dom, A=a, B=b, n_tasks=cs['n_tasks'], pairing=pairing,
               nb=cs['net_benefit'], nb_lo=cs['nb_ci'][0], nb_hi=cs['nb_ci'][1], p_tie=cs['p_tie'],
               success_diff=ds, success_lo=ds_lo, success_hi=ds_hi,
               cost_diff=float(dA.cost.mean() - dB.cost.mean()), steps_diff=float(dA.steps.mean() - dB.steps.mean()))
    row['dec_success_only'] = decide(ds_lo, ds_hi)
    row['dec_hierarchical'] = decide(cs['nb_ci'][0], cs['nb_ci'][1])
    row['dec_guarded'] = 'A' if (cs['nb_ci'][0] > 0 and ds_lo > -MARGIN) else ('B' if (cs['nb_ci'][1] < 0 and ds_hi < MARGIN) else 'undecided')
    sa, sb = dA.success.mean(), dB.success.mean(); ca, cb = dA.cost.mean(), dB.cost.mean()
    row['dec_pareto'] = 'A' if (sa >= sb and ca <= cb and (sa > sb or ca < cb)) else ('B' if (sb >= sa and cb <= ca and (sb > sa or cb < ca)) else 'neither')
    for lam in LAMBDAS:
        dA2 = dA.assign(util=dA.success - lam * dA.cost); dB2 = dB.assign(util=dB.success - lam * dB.cost)
        m, lo, hi = clustered_diff(dA2, dB2, 'util'); row[f'dec_utility_lambda{lam}'] = decide(lo, hi); row[f'util_diff_lambda{lam}'] = m
    row['priority_inversion'] = bool(np.sign(cs['net_benefit']) != np.sign(ds)) and abs(ds) > 1e-12
    row['inversion_type'] = ('hierarchy_prefers_lower_success' if cs['net_benefit'] > 0 > ds or cs['net_benefit'] < 0 < ds else 'none') if row['priority_inversion'] else 'none'
    nbp, plo, phi = cross_task_nb(dA, dB, cols, tiers)
    row.update(tau_pop_nb=nbp, tau_pop_lo=plo, tau_pop_hi=phi, tau_star_minus_tau_pop=cs['net_benefit'] - nbp,
               sign_differs_star_vs_pop=bool(np.sign(cs['net_benefit']) != np.sign(nbp)))
    return row


def main():
    rows = []
    df = pd.read_csv(SRC / 'tau2_runs.csv')
    main_df = df[(df.config == 'default') & df.domain.isin(['airline', 'retail', 'telecom'])].copy()
    main_df['success'] = (main_df.reward >= 1 - 1e-9).astype(float)
    main_df = main_df.rename(columns={'agent_cost': 'cost', 'n_assistant_tool_calls': 'steps'})
    models = ['gpt-4.1-2025-04-14', 'o4-mini-2025-04-16', 'claude-3-7-sonnet-20250219']
    cols = ['success', 'cost', 'steps']
    for dom in ['airline', 'retail', 'telecom']:
        for a, b in itertools.combinations(models, 2):
            rows.append(pair_rows(main_df[(main_df.model == a) & (main_df.domain == dom)], main_df[(main_df.model == b) & (main_df.domain == dom)], a, b, dom, 'tau2', cols))
    swe = pd.read_csv(SRC / 'swe_lite_runs.csv'); swe['success'] = swe.resolved.astype(float)
    swe = swe.rename(columns={'instance_cost': 'cost', 'api_calls': 'steps', 'instance_id': 'task_id'})
    rows.append(pair_rows(swe[swe.run == '20240402_sweagent_claude3opus'], swe[swe.run == '20240402_sweagent_gpt4'], 'sweagent_claude3opus', 'sweagent_gpt4', 'swe_lite', 'swe', cols))
    hal = pd.read_csv(SRC / 'hal_taubench_airline_runs.csv'); hal['success'] = hal.success.astype(float)
    hal = hal.rename(columns={'est_agent_cost': 'cost', 'n_taken_actions': 'steps'}); hal['steps'] = hal.steps.fillna(0)
    for a, b in itertools.combinations(sorted(hal.agent_name.unique()), 2):
        rows.append(pair_rows(hal[hal.agent_name == a], hal[hal.agent_name == b], a, b, 'hal_airline', 'hal', cols))
    out = pd.DataFrame(rows); out.to_csv(OUT / 'decision_matrix.csv', index=False)
    dec_cols = ['dec_success_only', 'dec_pareto', 'dec_hierarchical', 'dec_guarded'] + [f'dec_utility_lambda{l}' for l in LAMBDAS]
    summary = dict(n_pairs=len(out),
                   pairs_where_rules_disagree=int((out[dec_cols].nunique(axis=1) > 1).sum()),
                   pairs_success_vs_hierarchical_disagree=int((out.dec_success_only != out.dec_hierarchical).sum()),
                   pairs_success_decided=int((out.dec_success_only != 'undecided').sum()),
                   pairs_hierarchical_decided=int((out.dec_hierarchical != 'undecided').sum()),
                   pairs_guarded_decided=int((out.dec_guarded != 'undecided').sum()),
                   pairs_pareto_neither=int((out.dec_pareto == 'neither').sum()),
                   priority_inversions=int(out.priority_inversion.sum()),
                   inversions_with_nb_ci_excluding_zero=int((out.priority_inversion & (out.dec_hierarchical != 'undecided')).sum()),
                   sign_differs_star_vs_pop=int(out.sign_differs_star_vs_pop.sum()),
                   mean_abs_star_minus_pop=float(out.tau_star_minus_tau_pop.abs().mean()),
                   utility_flips_across_lambda=int((out[[f'dec_utility_lambda{l}' for l in LAMBDAS]].nunique(axis=1) > 1).sum()))
    (OUT / 'decision_matrix_summary.json').write_text(json.dumps(summary, indent=2))
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
    print(out[['source', 'domain', 'A', 'B', 'nb', 'nb_lo', 'nb_hi', 'success_diff', 'dec_success_only', 'dec_pareto', 'dec_hierarchical', 'dec_guarded', 'dec_utility_lambda0.1', 'dec_utility_lambda1.0', 'priority_inversion', 'tau_pop_nb', 'sign_differs_star_vs_pop']].to_string(index=False))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
