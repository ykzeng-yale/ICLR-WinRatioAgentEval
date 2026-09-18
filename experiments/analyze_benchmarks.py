"""Offline benchmark reanalysis with hierarchical win statistics.

Sources (raw files under work/empirical_sources/, see evidence/data_acquisition.md):
  * tau2-bench released trajectories (3 models x 3 domains x 4 trials/task)
  * SWE-bench Lite SWE-agent runs (GPT-4 vs Claude 3 Opus, 300 tasks, 1 run)
  * HAL taubench_airline runs (6 agent/model configurations, 50 tasks, latency)
Primary hierarchy (experiments/protocol.md, including the 2026-09-18 amendment
making the 12 off-diagonal within-task pairs primary for tau2):
  success > agent cost (5% relative tolerance) > assistant tool calls,
  absorbing failure (both fail => tie). Sensitivities: lexicographic (non-
  absorbing), margins 0/10/20%, order success>steps>cost, diagonal pairing,
  duration tier (tau2, exploratory), latency tier (HAL).
Inference: task is the cluster; all K_A x K_B cross-run comparisons are
averaged within task; t-based delta-method CIs and task bootstrap.
"""
import json, sys, itertools, hashlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import Tier, compare
from wincs import task_level_scores, clustered_summary, task_bootstrap, stratified_combine
SRC = ROOT / 'work' / 'empirical_sources'
OUT = ROOT / 'results' / 'benchmarks'
OUT.mkdir(parents=True, exist_ok=True)


def absorbing(A, B):
    """Eligibility mask: lower tiers only compared when both succeeded."""
    e = np.ones(np.broadcast(A, B).shape, bool)
    both = (A[..., 0] > 0.5) & (B[..., 0] > 0.5)
    e[..., 1:] = both[..., None]
    return e


def hierarchy(order=('success', 'cost', 'steps'), cost_margin=0.05, extra=None):
    spec = {'success': Tier('success'), 'cost': Tier('cost', False, relative_tolerance=cost_margin),
            'steps': Tier('steps', False), 'duration': Tier('duration', False, relative_tolerance=cost_margin),
            'latency': Tier('latency', False, relative_tolerance=cost_margin)}
    return [spec[k] for k in order]


def runs_dict(df, cols, key='task_id'):
    return {t: g[cols].to_numpy(float) for t, g in df.groupby(key)}


def contrast(dfA, dfB, cols, tiers, absorbing_rule=True, pairing='all', weights=None, n_boot=5000, seed=0, label=''):
    A = runs_dict(dfA, cols); B = runs_dict(dfB, cols)
    s = task_level_scores(A, B, tiers, eligible=absorbing if absorbing_rule else None, pairing=pairing)
    w = None if weights is None else np.array([weights[t] for t in s['tasks']])
    cs = clustered_summary(s['win'], s['loss'], weights=w)
    bs = task_bootstrap(s['win'], s['loss'], n_boot=n_boot, seed=seed, weights=w)
    row = dict(label=label, n_tasks=cs['n_tasks'], p_win=cs['p_win'], p_loss=cs['p_loss'], p_tie=cs['p_tie'],
               net_benefit=cs['net_benefit'], nb_se=cs['nb_se'], nb_lo=cs['nb_ci'][0], nb_hi=cs['nb_ci'][1],
               nb_boot_lo=bs['nb_ci'][0], nb_boot_hi=bs['nb_ci'][1],
               win_ratio=cs['win_ratio'], wr_lo=cs['wr_ci'][0], wr_hi=cs['wr_ci'][1],
               wr_boot_lo=bs['wr_ci'][0], wr_boot_hi=bs['wr_ci'][1], frac_wr_undefined=bs['frac_wr_undefined'],
               win_odds=cs['win_odds'], wo_lo=cs['wo_ci'][0], wo_hi=cs['wo_ci'][1])
    for k, t in enumerate(tiers):
        row[f'contrib_{t.name}'] = float(np.average(s['tier_contribution'][:, k], weights=w))
        row[f'decided_{t.name}'] = float(np.average(s['tier_decided'][:, k], weights=w))
    # component (marginal) differences with task-clustered CI
    dA = dfA.groupby('task_id')[cols].mean(); dB = dfB.groupby('task_id')[cols].mean()
    common = dA.index.intersection(dB.index)
    for j, c in enumerate(cols):
        d = (dA.loc[common, c] - dB.loc[common, c]).to_numpy(float)
        m = float(np.average(d, weights=w)); se = float(np.sqrt(np.average((d - m)**2, weights=w) / (len(d) - 1))) if w is None else float(np.sqrt(np.sum((w / w.sum())**2 * (d - m)**2) * len(d) / (len(d) - 1)))
        row[f'diff_{c}'] = m; row[f'diff_{c}_se'] = se
    return row, s


def tau2():
    df = pd.read_csv(SRC / 'tau2_runs.csv')
    main = df[(df.config == 'default') & df.domain.isin(['airline', 'retail', 'telecom'])
              & df.model.isin(['gpt-4.1-2025-04-14', 'o4-mini-2025-04-16', 'claude-3-7-sonnet-20250219'])].copy()
    main['success'] = (main.reward >= 1 - 1e-9).astype(float)
    main = main.rename(columns={'agent_cost': 'cost', 'n_assistant_tool_calls': 'steps'})
    cols = ['success', 'cost', 'steps']
    rows = []; task_scores = {}
    pairs = [('o4-mini-2025-04-16', 'gpt-4.1-2025-04-14'), ('claude-3-7-sonnet-20250219', 'gpt-4.1-2025-04-14'), ('claude-3-7-sonnet-20250219', 'o4-mini-2025-04-16')]
    for a, b in pairs:
        for dom in ['airline', 'retail', 'telecom']:
            dA = main[(main.model == a) & (main.domain == dom)]; dB = main[(main.model == b) & (main.domain == dom)]
            # primary
            r, s = contrast(dA, dB, cols, hierarchy(), True, 'offdiagonal', label='primary'); r.update(A=a, B=b, domain=dom, source='tau2'); rows.append(r)
            task_scores[(a, b, dom)] = s
            # sensitivities
            for lab, tiers, absorb, pairing in [
                ('lexicographic_nonabsorbing', hierarchy(), False, 'offdiagonal'),
                ('margin_0', hierarchy(cost_margin=0.0), True, 'offdiagonal'),
                ('margin_10', hierarchy(cost_margin=0.10), True, 'offdiagonal'),
                ('margin_20', hierarchy(cost_margin=0.20), True, 'offdiagonal'),
                ('order_success_steps_cost', hierarchy(('success', 'steps', 'cost')), True, 'offdiagonal'),
                ('success_only', hierarchy(('success',)), True, 'offdiagonal'),
                ('diagonal_shared_seed', hierarchy(), True, 'diagonal'),
                ('all_16_pairs', hierarchy(), True, 'all'),
                ('with_duration_4th', hierarchy(('success', 'cost', 'steps', 'duration')), True, 'offdiagonal'),
            ]:
                cc = [t.name for t in tiers]
                r, _ = contrast(dA, dB, cc, tiers, absorb, pairing, n_boot=2000, label=lab); r.update(A=a, B=b, domain=dom, source='tau2'); rows.append(r)
        # pooled across domains: equal-task weights and equal-domain weights
        for lab, wmode in [('pooled_equal_task', 'task'), ('pooled_equal_domain', 'domain')]:
            dA = main[main.model == a].copy(); dB = main[main.model == b].copy()
            dA['task_id'] = dA.domain + ':' + dA.task_id.astype(str); dB['task_id'] = dB.domain + ':' + dB.task_id.astype(str)
            if wmode == 'domain':
                cnt = dA.groupby('domain').task_id.nunique()
                weights = {t: 1.0 / cnt[t.split(':')[0]] for t in dA.task_id.unique()}
            else:
                weights = None
            r, _ = contrast(dA, dB, cols, hierarchy(), True, 'offdiagonal', weights=weights, n_boot=2000, label=lab); r.update(A=a, B=b, domain='all', source='tau2'); rows.append(r)
    out = pd.DataFrame(rows); out.to_csv(OUT / 'tau2_contrasts.csv', index=False)
    # Per-model marginal summaries (Pareto display)
    summ = main.groupby(['domain', 'model']).agg(n_tasks=('task_id', 'nunique'), n_runs=('task_id', 'size'), success=('success', 'mean'),
                                                  cost=('cost', 'mean'), steps=('steps', 'mean'), duration=('duration', 'mean')).reset_index()
    # pass^4 style reliability: fraction of tasks with all 4 trials successful
    allk = main.groupby(['domain', 'model', 'task_id']).success.agg(['mean', 'size']).reset_index()
    allk['all4'] = (allk['mean'] >= 1 - 1e-9).astype(float)
    summ = summ.merge(allk.groupby(['domain', 'model']).all4.mean().rename('pass_all4').reset_index(), on=['domain', 'model'])
    summ.to_csv(OUT / 'tau2_marginals.csv', index=False)
    # Ranking disagreement: per domain rank by success, by pairwise NB (Copeland-like sum), by scalarized success - lambda*cost
    ranks = []
    for dom in ['airline', 'retail', 'telecom']:
        models = ['gpt-4.1-2025-04-14', 'o4-mini-2025-04-16', 'claude-3-7-sonnet-20250219']
        nbsum = {m: 0.0 for m in models}
        for a, b in itertools.permutations(models, 2):
            dA = main[(main.model == a) & (main.domain == dom)]; dB = main[(main.model == b) & (main.domain == dom)]
            r, _ = contrast(dA, dB, cols, hierarchy(), True, 'offdiagonal', n_boot=200, label='rank'); nbsum[a] += r['net_benefit']
        sm = summ[summ.domain == dom].set_index('model')
        for m in models:
            ranks.append(dict(domain=dom, model=m, success=sm.loc[m, 'success'], cost=sm.loc[m, 'cost'], pass_all4=sm.loc[m, 'pass_all4'],
                              nb_sum=nbsum[m], scalar_lambda1=sm.loc[m, 'success'] - 1.0 * sm.loc[m, 'cost'], scalar_lambda0p3=sm.loc[m, 'success'] - 0.3 * sm.loc[m, 'cost']))
    rk = pd.DataFrame(ranks)
    for c in ['success', 'nb_sum', 'scalar_lambda1', 'scalar_lambda0p3', 'pass_all4']:
        rk[f'rank_{c}'] = rk.groupby('domain')[c].rank(ascending=False, method='min')
    rk.to_csv(OUT / 'tau2_rankings.csv', index=False)
    return out, summ, rk, task_scores


def swe():
    df = pd.read_csv(SRC / 'swe_lite_runs.csv')
    df['success'] = df.resolved.astype(float); df = df.rename(columns={'instance_cost': 'cost', 'api_calls': 'steps', 'instance_id': 'task_id'})
    cols = ['success', 'cost', 'steps']
    A = df[df.run == '20240402_sweagent_claude3opus']; B = df[df.run == '20240402_sweagent_gpt4']
    rows = []
    for lab, tiers, absorb in [('primary', hierarchy(), True), ('lexicographic_nonabsorbing', hierarchy(), False), ('margin_0', hierarchy(cost_margin=0.0), True),
                               ('margin_20', hierarchy(cost_margin=0.20), True), ('order_success_steps_cost', hierarchy(('success', 'steps', 'cost')), True), ('success_only', hierarchy(('success',)), True)]:
        r, s = contrast(A, B, [t.name for t in tiers], tiers, absorb, 'all', n_boot=5000, label=lab); r.update(A='sweagent_claude3opus', B='sweagent_gpt4', domain='swe_lite', source='swe'); rows.append(r)
    # repository-stratified and leave-one-repo-out
    repos = sorted(df.repo.unique())
    for rp in repos:
        r, _ = contrast(A[A.repo != rp], B[B.repo != rp], cols, hierarchy(), True, 'all', n_boot=1000, label=f'leave_out_{rp}'); r.update(A='sweagent_claude3opus', B='sweagent_gpt4', domain='swe_lite', source='swe'); rows.append(r)
        if (A.repo == rp).sum() >= 10:
            r, _ = contrast(A[A.repo == rp], B[B.repo == rp], cols, hierarchy(), True, 'all', n_boot=1000, label=f'only_{rp}'); r.update(A='sweagent_claude3opus', B='sweagent_gpt4', domain='swe_lite', source='swe'); rows.append(r)
    out = pd.DataFrame(rows); out.to_csv(OUT / 'swe_contrasts.csv', index=False)
    summ = df.groupby('run').agg(n_tasks=('task_id', 'nunique'), success=('success', 'mean'), cost=('cost', 'mean'), steps=('steps', 'mean')).reset_index()
    summ.to_csv(OUT / 'swe_marginals.csv', index=False)
    return out, summ


def hal():
    df = pd.read_csv(SRC / 'hal_taubench_airline_runs.csv')
    df['success'] = df.success.astype(float)
    df = df.rename(columns={'est_agent_cost': 'cost', 'n_taken_actions': 'steps', 'latency_total_time_s': 'latency'})
    df['steps'] = df.steps.fillna(0)
    agents = sorted(df.agent_name.unique())
    cols = ['success', 'cost', 'steps', 'latency']
    rows = []
    for a, b in itertools.combinations(agents, 2):
        A = df[df.agent_name == a]; B = df[df.agent_name == b]
        for lab, tiers, absorb, cc in [('primary', hierarchy(), True, ['success', 'cost', 'steps']),
                                       ('success_latency_cost', hierarchy(('success', 'latency', 'cost')), True, ['success', 'latency', 'cost']),
                                       ('success_only', hierarchy(('success',)), True, ['success']),
                                       ('lexicographic_nonabsorbing', hierarchy(), False, ['success', 'cost', 'steps'])]:
            r, _ = contrast(A, B, cc, tiers, absorb, 'all', n_boot=2000, label=lab); r.update(A=a, B=b, domain='hal_taubench_airline', source='hal'); rows.append(r)
    out = pd.DataFrame(rows); out.to_csv(OUT / 'hal_contrasts.csv', index=False)
    summ = df.groupby(['agent_name', 'agent_model']).agg(n_tasks=('task_id', 'nunique'), success=('success', 'mean'), cost=('cost', 'mean'), steps=('steps', 'mean'), latency=('latency', 'mean'), harness_errors=('harness_error', 'sum')).reset_index()
    summ.to_csv(OUT / 'hal_marginals.csv', index=False)
    return out, summ


def main():
    t_out, t_summ, t_rank, _ = tau2()
    print('tau2 primary contrasts:'); print(t_out[t_out.label == 'primary'][['A', 'B', 'domain', 'n_tasks', 'p_win', 'p_loss', 'p_tie', 'net_benefit', 'nb_lo', 'nb_hi', 'win_ratio', 'wr_lo', 'wr_hi', 'diff_success', 'contrib_success', 'contrib_cost', 'contrib_steps']].to_string(index=False))
    print(t_rank.to_string(index=False))
    s_out, s_summ = swe()
    print('swe:'); print(s_out[s_out.label.isin(['primary', 'success_only', 'lexicographic_nonabsorbing'])][['label', 'n_tasks', 'p_win', 'p_loss', 'p_tie', 'net_benefit', 'nb_lo', 'nb_hi', 'win_ratio', 'wr_lo', 'wr_hi', 'diff_success']].to_string(index=False))
    h_out, h_summ = hal()
    print('hal:'); print(h_summ.to_string(index=False))
    print(h_out[h_out.label == 'primary'][['A', 'B', 'net_benefit', 'nb_lo', 'nb_hi', 'win_ratio', 'diff_success']].to_string(index=False))
    manifest = dict(sources={f: hashlib.sha256((SRC / f).read_bytes()).hexdigest() for f in ['tau2_runs.csv', 'swe_lite_runs.csv', 'hal_taubench_airline_runs.csv']},
                    code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    hierarchy='success > cost(5% rel) > steps, absorbing failure; sensitivities listed in script',
                    note='Historical offline benchmark runs; costs reflect historical pricing; not live experiments.')
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
