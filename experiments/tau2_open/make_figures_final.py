"""Figures and supplementary numbers for results/tau2_open/report_final.md (POST HOC reporting script).

Nothing frozen is edited and nothing is re-run: the script READS episodes.csv, monitor_pass1.csv, monitor_state.json,
summary.json, design.json and the two canonical raw tau2 JSONs, IMPORTS the frozen analysis.py functions (unchanged) for
the sensitivity re-computations, and WRITES
  results/tau2_open/figures/f1_monitoring.{pdf,png}     e-process paths over the 49 prespecified pairs (descriptive)
  results/tau2_open/figures/f2_components.{pdf,png}     paired component differences B - A with 95% intervals
  results/tau2_open/figures/f3_terminations.{pdf,png}   termination reasons per arm + truncated responses
  results/tau2_open/report_final_numbers.json           every number of report_final.md that is not already in summary.json

No model call, no network, no git command.
Usage: .venv/bin/python experiments/tau2_open/make_figures_final.py [--results-dir results/tau2_open]
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'src')); sys.path.insert(0, str(HERE))

import analysis as AN  # frozen, imported read-only
from common import load_config, sha256_file
from design import load_design
from winstats import normal_mixture_radius

# Categorical palette in fixed order (dataviz validator: adjacent-pair CVD dE >= 9.2, normal-vision dE >= 27 on the light surface).
BLUE, ORANGE, AQUA, YELLOW, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#8c8b87'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e6e5e1'
WIDTH = 5.5
plt.rcParams.update({
    'font.size': 8, 'axes.titlesize': 8, 'axes.labelsize': 8, 'legend.fontsize': 7, 'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'axes.axisbelow': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
    'legend.frameon': False, 'pdf.fonttype': 42, 'savefig.dpi': 200, 'lines.linewidth': 1.6, 'hatch.linewidth': 0.5,
})
AMENDMENT_LOCAL = '2026-09-18T16:33'  # invocation 2 started 2026-09-18T20:33:06Z = 16:33:06 local (tau2 timestamps are local, UTC-4)
COMP_LABEL = collections.OrderedDict([
    ('success', 'success (proportion)'), ('agent_tokens_completion', 'agent completion tokens'), ('agent_tokens_prompt', 'agent prompt tokens (thousands)'),
    ('n_assistant_tool_calls', 'assistant tool calls'), ('duration', 'simulation duration (s)'), ('agent_generation_seconds', 'agent generation time (s)')])


def save(fig, out_dir: Path, name: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ('pdf', 'png'):
        fig.savefig(out_dir / f'{name}.{ext}', bbox_inches='tight')
    plt.close(fig)
    print('wrote', out_dir / f'{name}.{{pdf,png}}')


# ------------------------------------------------------------------ raw accounting

def raw_accounting(path: Path) -> dict:
    d = json.loads(path.read_text()); sims = d['simulations']
    succ = {(s['task_id'], s['trial']): (s.get('reward_info') or {}).get('reward') == 1.0 for s in sims}
    o = dict(raw_file=str(path), raw_sha256=sha256_file(path), n_units=len(sims), n_success=int(sum(succ.values())),
             success_by_trial={str(t): int(sum(v for k, v in succ.items() if k[1] == t)) for t in (0, 1)},
             termination_reasons=dict(collections.Counter(s['termination_reason'] for s in sims)),
             n_timeout_terminations=int(sum(s['termination_reason'] == 'timeout' for s in sims)),
             per_trial_seed_field={'%d:%s' % k: v for k, v in collections.Counter((s['trial'], s['seed']) for s in sims).items()},
             info_block=dict(agent_llm=d['info']['agent_info']['llm'], agent_llm_args=d['info']['agent_info']['llm_args'],
                             user_llm=d['info']['user_info']['llm'], user_llm_args=d['info']['user_info']['llm_args'], seed=d['info'].get('seed'),
                             git_commit=d['info'].get('git_commit')))
    o['infrastructure_error_units'] = [dict(task=s['task_id'], trial=s['trial'], seed=s['seed'], n_messages=len(s.get('messages') or []), duration=s.get('duration'),
                                            reward_info_is_null=s.get('reward_info') is None, error_type=(s.get('info') or {}).get('error_type'),
                                            error=(s.get('info') or {}).get('error')) for s in sims if s['termination_reason'] == 'infrastructure_error']
    o['units_with_missing_reward'] = [[s['task_id'], s['trial']] for s in sims if (s.get('reward_info') or {}).get('reward') is None]
    fin = collections.Counter(); served = collections.Counter(); tok = collections.Counter(); calls = collections.Counter(); maxc = collections.Counter()
    no_usage = collections.Counter(); trunc_units = collections.defaultdict(int); keys = set(); gen = 0.0
    for s in sims:
        for m in s.get('messages') or []:
            r = m['role']
            if r not in ('assistant', 'user'):
                continue
            if not m.get('usage'):
                no_usage[r] += 1; continue
            calls[r] += 1; tok[r + '_prompt'] += m['usage']['prompt_tokens']; tok[r + '_completion'] += m['usage']['completion_tokens']
            maxc[r] = max(maxc[r], m['usage']['completion_tokens'])
            rd = m.get('raw_data') or {}
            keys |= set(rd.keys()); served['%s:%s' % (r, rd.get('model'))] += 1
            f = (rd.get('choices') or [{}])[0].get('finish_reason'); fin['%s:%s' % (r, f)] += 1
            if f == 'length':
                trunc_units[(s['task_id'], s['trial'], r)] += 1
            if r == 'assistant' and m.get('generation_time_seconds'):
                gen += m['generation_time_seconds']
    term = {(s['task_id'], s['trial']): s['termination_reason'] for s in sims}
    tu = sorted({k[:2] for k in trunc_units}, key=lambda k: (int(k[0]), k[1]))
    o.update(finish_reasons=dict(fin), served_model_ids=dict(served), llm_calls=dict(calls), messages_without_usage=dict(no_usage), tokens=dict(tok),
             max_completion_tokens_per_response=dict(maxc), response_raw_data_keys=sorted(keys),
             truncated_responses_length={'agent': int(fin.get('assistant:length', 0)), 'user': int(fin.get('user:length', 0))},
             units_with_truncated_response=[dict(task=k[0], trial=k[1], success=bool(succ[k]), termination=term[k]) for k in tu],
             agent_generation_seconds_total=gen, duration_total_s=float(sum(s['duration'] or 0 for s in sims)),
             duration_min_median_max=[float(np.min([s['duration'] for s in sims])), float(np.median([s['duration'] for s in sims])), float(np.max([s['duration'] for s in sims]))],
             n_units_duration_over_1800s=int(sum((s['duration'] or 0) > 1800 for s in sims)),
             first_start_local=min(s['start_time'] for s in sims), last_end_local=max(s['end_time'] for s in sims))
    o['pre_amendment_units'] = [dict(task=s['task_id'], trial=s['trial'], start_local=s['start_time'], duration=round(s['duration'], 1), termination=s['termination_reason'],
                                     reward=(s.get('reward_info') or {}).get('reward'),
                                     max_agent_completion=max([m['usage']['completion_tokens'] for m in s['messages'] if m['role'] == 'assistant' and m.get('usage')] or [0]),
                                     max_user_completion=max([m['usage']['completion_tokens'] for m in s['messages'] if m['role'] == 'user' and m.get('usage')] or [0]))
                                for s in sims if s['start_time'] < AMENDMENT_LOCAL]
    # replicate identity: are the trial-0 and trial-1 trajectories of a task identical (role, content, tool name + arguments; ids ignored)?
    by = collections.defaultdict(dict)
    for s in sims:
        by[s['task_id']][s['trial']] = [(m['role'], m.get('content'), json.dumps([[tc.get('name'), tc.get('arguments')] for tc in (m.get('tool_calls') or [])], sort_keys=True))
                                        for m in s.get('messages') or []]
    full = [t for t, v in by.items() if len(v.get(0, [])) > 2 and len(v.get(1, [])) > 2]
    o['replicates'] = dict(n_tasks=len(by), n_tasks_both_trials_nonempty=len(full), n_identical_trajectories=int(sum(by[t][0] == by[t][1] for t in by)),
                           n_identical_first_user_message=int(sum(by[t][0][1] == by[t][1][1] for t in full)),
                           n_identical_first_agent_reply=int(sum(by[t][0][:3] == by[t][1][:3] for t in full)),
                           n_tasks_success_both_trials=int(sum(succ[(t, 0)] and succ[(t, 1)] for t in by)),
                           n_tasks_success_exactly_one_trial=int(sum(succ[(t, 0)] != succ[(t, 1)] for t in by)),
                           tasks_with_any_success=sorted([t for t in by if succ[(t, 0)] or succ[(t, 1)]], key=int))
    return o


def log_accounting(log_dir: Path) -> dict:
    out = {}
    for arm in 'AB':
        p = log_dir / f'tau2_arm{arm}.log'
        L = p.read_text(errors='replace').splitlines() if p.exists() else []
        out[arm] = dict(log=str(p), n_token_limit_warnings=sum('Output might be incomplete due to token limit' in x for x in L),
                        n_context_overflow_errors=sum('llm_utils:generate' in x and 'exceeds the available context size' in x for x in L),
                        retry_lines=[x[:23] + ' | ' + x.split(' - ', 1)[-1][:150] for x in L if 'run_with_retry' in x],
                        other=[x.strip()[:160] for x in L if 'succeeded on retry' in x or 'failed permanently' in x])
    return out


# ------------------------------------------------------------------ statistics

def t_ci(x):
    r = AN.t_ci(np.asarray(x, float), 0.05)
    return dict(n=int(r['n']), mean=float(r['mean']), se=float(r['se']), ci=[float(r['ci'][0]), float(r['ci'][1])])


def pair_level_components(design, episodes):
    """Cross-arrival component differences d_k = X_B,k - X_A,k over the prespecified pass-1 pairs (addendum (b): pair-level
    differences, approximate t interval; NOT an independent-arm Welch interval)."""
    out = {}
    for label, keep in (('all_49', None), ('block1_24', {1})):
        idx, eA, eB, blocks = AN.completed_pairs(design, episodes)
        sel = [i for i, b in enumerate(blocks) if keep is None or b in keep]
        out[label] = {}
        for c in COMP_LABEL:
            xa = np.array([float(eA[i][c]) if eA[i][c] is not None else np.nan for i in sel]); xb = np.array([float(eB[i][c]) if eB[i][c] is not None else np.nan for i in sel])
            d = xb - xa; d = d[np.isfinite(d)]
            r = t_ci(d); r.update(mean_A=float(np.nanmean(xa)), mean_B=float(np.nanmean(xb))); out[label][c] = r
    return out


def summarise(o):
    keys = ('n_pairs', 'n_tasks', 'p_win', 'p_loss', 'p_tie', 'net_benefit', 'nb_cs', 'nb_ci', 'success_diff_hat', 'success_diff_cs', 'guarded_decision', 'decision_hierarchical')
    return {k: o[k] for k in keys if k in o}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(REPO / 'results' / 'tau2_open'))
    args = ap.parse_args(argv)
    R = Path(args.results_dir); FIG = R / 'figures'
    cfg = load_config(None); design = load_design(R)
    episodes = AN.load_episodes(R / 'episodes.csv'); summary = json.loads((R / 'summary.json').read_text())
    mon = pd.read_csv(R / 'monitor_pass1.csv'); state = json.loads((R / 'monitor_state.json').read_text())
    N = dict(generated_by='experiments/tau2_open/make_figures_final.py', inputs={p: sha256_file(R / p) for p in ('episodes.csv', 'summary.json', 'monitor_pass1.csv', 'design.json', 'run_manifest.json')})

    # raw accounting + logs
    N['raw'] = {arm: raw_accounting(R / 'raw' / f'tau2_open_arm{arm}.json') for arm in 'AB'}
    N['logs'] = log_accounting(R / 'logs')

    # consistency of the frozen outputs with this script's re-computation
    on = AN.online_analysis(design, episodes, cfg); sh = AN.shadow_analysis(episodes, cfg)
    assert abs(on['net_benefit'] - summary['online']['net_benefit']) < 1e-12 and abs(sh['net_benefit'] - summary['shadow']['net_benefit']) < 1e-12
    assert np.allclose(on['nb_cs'], summary['online']['nb_cs']) and np.allclose(sh['nb_ci'], summary['shadow']['nb_ci'])
    for arm in 'AB':
        assert N['raw'][arm]['n_success'] == summary['components']['failure_accounting'][arm]['success']

    # R1 normal-mixture CS (V_n = n, rho = 100, alpha = 0.05, no running intersection); NB and success difference live in [-1, 1]
    N['R1'] = {}
    for label, o in (('all_49', summary['online']), ('block1_24', summary['online_block1'])):
        n = o['n_pairs']; rad = float(normal_mixture_radius(n, 0.05, 100.0))
        assert abs(rad - np.sqrt((n + 100) * np.log((n + 100) / (100 * 0.05 ** 2))) / n) < 1e-12
        N['R1'][label] = dict(n=n, rho=100, alpha=0.05, radius=rad, nb_hat=o['net_benefit'], nb_cs_unclipped=[o['net_benefit'] - rad, o['net_benefit'] + rad],
                              nb_cs_clipped=[max(-1.0, o['net_benefit'] - rad), min(1.0, o['net_benefit'] + rad)],
                              success_diff_hat=o['success_diff_hat'], success_diff_cs_clipped=[max(-1.0, o['success_diff_hat'] - rad), min(1.0, o['success_diff_hat'] + rad)],
                              wider_than_half_parameter_range=bool(rad > 0.5), covers_whole_parameter_range=bool(o['net_benefit'] - rad <= -1 and o['net_benefit'] + rad >= 1))
    N['R1']['n_needed_for_radius_0.03'] = int(next(n for n in range(10, 10 ** 6) if normal_mixture_radius(n, 0.05, 100.0) <= 0.03))

    # power arithmetic for the guardrail
    st = summary['components']['same_task_paired']['success']
    N['guardrail_arithmetic'] = dict(margin=cfg['success_margin'], same_task_success_diff_se=st['se'], same_task_ci_halfwidth=(st['ci'][1] - st['ci'][0]) / 2,
                                     tasks_needed_for_halfwidth_003_same_sd=float((1.96 * st['se'] * np.sqrt(st['n']) / 0.03) ** 2), shadow_p_tie=summary['shadow']['p_tie'],
                                     online_p_tie=summary['online']['p_tie'], pooled_success_rate=(N['raw']['A']['n_success'] + N['raw']['B']['n_success']) / 196,
                                     independence_tie_probability_at_pooled_rate=float(1 - 2 * (30 / 196) * (1 - 30 / 196)))

    # same-task discordance of successes (unit level, same trial)
    sa = {(e['task_id'], e['trial']): bool(e['success']) for e in episodes if e['arm'] == 'A'}; sb = {(e['task_id'], e['trial']): bool(e['success']) for e in episodes if e['arm'] == 'B'}
    N['same_unit_success_table'] = dict(both=int(sum(sa[k] and sb[k] for k in sa)), A_only=int(sum(sa[k] and not sb[k] for k in sa)), B_only=int(sum(sb[k] and not sa[k] for k in sa)),
                                        neither=int(sum(not sa[k] and not sb[k] for k in sa)))
    ta = collections.Counter(); tb = collections.Counter()
    for k, v in sa.items():
        ta[k[0]] += v; tb[k[0]] += sb[k]
    N['task_level_success'] = dict(tasks_any_success_A=int(sum(v > 0 for v in ta.values())), tasks_any_success_B=int(sum(v > 0 for v in tb.values())),
                                   tasks_any_success_either=int(sum((ta[t] + tb[t]) > 0 for t in ta)), tasks_never_solved=int(sum((ta[t] + tb[t]) == 0 for t in ta)))

    # sensitivity: the two infrastructure_error units (retained as failures by the frozen pipeline) EXCLUDED instead
    infra = {(e['arm'], e['task_id'], e['trial']) for e in episodes if e['termination_reason'] == 'infrastructure_error'}
    ep_x = [e for e in episodes if (e['arm'], e['task_id'], e['trial']) not in infra]
    comp_x = AN.component_effects(ep_x, design, cfg)['same_task_paired']
    N['infrastructure_sensitivity'] = dict(
        units=sorted(map(list, infra)), frozen_treatment='retained as failures: success=False, reward missing, 0 messages, 0 tokens, 0 tool calls, duration 0.0, agent_generation_seconds missing',
        pass_of_units={'%s:%s:%s' % (e['arm'], e['task_id'], e['trial']): e['pass'] for e in episodes if (e['arm'], e['task_id'], e['trial']) in infra},
        excluded=dict(success_A='%d/%d' % (sum(e['success'] for e in ep_x if e['arm'] == 'A'), sum(e['arm'] == 'A' for e in ep_x)),
                      online=summarise(AN.online_analysis(design, ep_x, cfg)), shadow=summarise(AN.shadow_analysis(ep_x, cfg)),
                      components_same_task={c: {k: comp_x[c][k] for k in ('n', 'mean', 'ci', 'mean_A', 'mean_B')} for c in COMP_LABEL}),
        as_failures_frozen=dict(online=summarise(summary['online']), shadow=summarise(summary['shadow'])))
    N['pair_level_components'] = pair_level_components(design, episodes)

    # amendment: success-tier results without the five pre-amendment arm-A units' tasks is NOT computed (they are retained by protocol); only counts
    N['amendment'] = dict(sha256_config_amendment_1=sha256_file(HERE / 'config_amendment_1.json'), sha256_deviation_1=sha256_file(HERE / 'deviation_1_runaway_generation.md'),
                          n_pre_amendment_units=len(N['raw']['A']['pre_amendment_units']) + len(N['raw']['B']['pre_amendment_units']))

    (R / 'report_final_numbers.json').write_text(json.dumps(AN._clean(N), indent=1, default=str) + '\n')
    print('wrote', R / 'report_final_numbers.json')

    # ------------------------------------------------------------------ f1 monitoring
    thr = float(np.log(1 / state['alpha'])); min_n = state['min_n_pairs']
    fig, (ax, axz) = plt.subplots(1, 2, figsize=(WIDTH, 2.5), gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.34))
    series = [('win: H0 E[Z] <= 0', 'log_e_win', BLUE, '-'), ('guardrail: H0 E[D] <= -0.03', 'log_e_gate', AQUA, '--'), ('harm: H0 E[Z] >= 0', 'log_e_harm', ORANGE, '-.')]
    for a in (ax, axz):
        a.axvspan(0.5, min_n - 0.5, color=GRAY, alpha=0.18, lw=0)
        for lab, col, c, ls in series:
            a.plot(mon['n'], mon[col], color=c, ls=ls, label=lab)
        a.axvline(24.5, color=INK2, lw=0.7, ls=':'); a.set_xlim(0.5, 49.5); a.set_xlabel('prespecified pair index n')
    ax.axhline(thr, color=INK, lw=0.9, ls=':'); ax.text(49, thr + 0.06, 'threshold log(1/0.05) = %.2f' % thr, ha='right', va='bottom', fontsize=7, color=INK2)
    ax.text(min_n / 2, thr - 0.25, 'n < 20\nnot read', ha='center', va='top', fontsize=7, color=INK2)
    ax.text(25.2, -0.62, 'block 1 | block 2', fontsize=6.5, color=INK2, va='bottom')
    ax.set_ylim(-0.7, thr + 0.5); ax.set_ylabel('log e-value'); ax.set_title('full scale', loc='left')
    fig.legend(*ax.get_legend_handles_labels(), loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.12), handlelength=2.6)
    lo = float(mon[['log_e_win', 'log_e_gate', 'log_e_harm']].min().min()); hi = float(mon[['log_e_win', 'log_e_gate', 'log_e_harm']].max().max())
    axz.set_ylim(lo - 0.05, hi + 0.05); axz.axhline(0, color=INK2, lw=0.7); axz.set_title('zoom (same paths)', loc='left')
    fig.suptitle('Descriptive monitoring replay over the 49 prespecified pairs (batch collection; no live stopping)', fontsize=8, x=0.02, ha='left', y=1.04)
    save(fig, FIG, 'f1_monitoring')

    # ------------------------------------------------------------------ f2 components
    same = summary['components']['same_task_paired']; cross = N['pair_level_components']['all_49']
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH, 3.1), gridspec_kw=dict(wspace=0.28, hspace=0.95))
    for a, (c, lab) in zip(axes.ravel(), COMP_LABEL.items()):
        sc = 1e-3 if c == 'agent_tokens_prompt' else 1.0
        for y, (src, col, mk) in enumerate(((same[c], BLUE, 'o'), (cross[c], ORANGE, 's'))):
            m, (l, h) = src['mean'] * sc, [v * sc for v in src['ci']]
            a.errorbar([m], [1 - y], xerr=[[m - l], [h - m]], fmt=mk, color=col, ms=4.5, capsize=2.5, lw=1.4, mec='white', mew=0.6)
        a.axvline(0, color=INK, lw=0.8); a.set_ylim(-0.6, 1.6); a.set_yticks([]); a.grid(axis='y', visible=False); a.set_title(lab, loc='left', fontsize=7.5)
        xl = max(abs(v) for v in a.get_xlim()); a.set_xlim(-xl, xl); a.spines['left'].set_visible(False); a.locator_params(axis='x', nbins=5)
    h = [plt.Line2D([], [], marker='o', color=BLUE, ms=4.5, lw=1.4, label='same-task (49 tasks, trials averaged; t, 48 df)'),
         plt.Line2D([], [], marker='s', color=ORANGE, ms=4.5, lw=1.4, label='cross-arrival (49 prespecified pairs; approximate t)')]
    fig.legend(handles=h, loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle('Component differences B - A (Qwen3-4B minus Qwen2.5-7B), mean and 95% interval; left of 0 = B lower', fontsize=8, x=0.02, ha='left', y=1.0)
    save(fig, FIG, 'f2_components')

    # ------------------------------------------------------------------ f3 terminations + truncation
    reasons = [('user_stop', BLUE, ''), ('max_steps', ORANGE, '///'), ('too_many_errors', AQUA, '...'), ('infrastructure_error', YELLOW, 'xxx')]
    seen = set(N['raw']['A']['termination_reasons']) | set(N['raw']['B']['termination_reasons'])
    assert seen <= {r for r, _, _ in reasons}, seen
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.3), gridspec_kw=dict(width_ratios=[1.7, 1], wspace=0.42))
    for y, arm in ((1, 'A'), (0, 'B')):
        left = 0; tr = N['raw'][arm]['termination_reasons']
        for r, col, hatch in reasons:
            v = tr.get(r, 0)
            if v:
                ax.barh(y, v, left=left, color=col, edgecolor='white', linewidth=1.5, height=0.55, hatch=hatch, label=r if arm == 'A' else None)
                big = v >= 5
                ax.text(left + v / 2 if big else left + v + 1.2, y, str(v), ha='center' if big else 'left', va='center', fontsize=7, color=INK, bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.85) if big else None)
            left += v
    ax.set_yticks([1, 0]); ax.set_yticklabels(['A  Qwen2.5-7B\n(15/98 success)', 'B  Qwen3-4B\n(15/98 success)']); ax.set_xlim(0, 104); ax.set_xlabel('units (of 98 per arm)')
    ax.grid(axis='y', visible=False); ax.set_title('termination reason (timeout: 0 in both arms)', loc='left')
    ax.legend(loc='upper center', bbox_to_anchor=(0.45, -0.3), ncol=2, handlelength=1.4, columnspacing=1.0)
    cats = ['A agent', 'A user', 'B agent', 'B user']
    kept = [N['raw']['A']['truncated_responses_length']['agent'], N['raw']['A']['truncated_responses_length']['user'], N['raw']['B']['truncated_responses_length']['agent'], N['raw']['B']['truncated_responses_length']['user']]
    disc = [N['logs']['A']['n_token_limit_warnings'] - sum(kept[:2]), 0, N['logs']['B']['n_token_limit_warnings'] - sum(kept[2:]), 0]
    x = np.arange(4)
    ax2.bar(x, kept, color=BLUE, width=0.6, edgecolor='white', linewidth=1.5, label='in retained trajectories')
    ax2.bar(x, disc, bottom=kept, color=ORANGE, width=0.6, edgecolor='white', linewidth=1.5, hatch='///', label='in discarded attempts (log only)')
    for i in range(4):
        ax2.text(x[i], kept[i] + disc[i] + 0.2, '%d + %d' % (kept[i], disc[i]) if disc[i] else str(kept[i]), ha='center', va='bottom', fontsize=7)
    ax2.set_xticks(x); ax2.set_xticklabels(cats, rotation=30, ha='right'); ax2.set_ylim(0, max(np.add(kept, disc)) + 2.5); ax2.grid(axis='x', visible=False)
    ax2.set_title('responses cut at 1,024 tokens', loc='left'); ax2.set_ylabel('responses'); ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.3), fontsize=6.5, handlelength=1.4)
    save(fig, FIG, 'f3_terminations')


if __name__ == '__main__':
    main()
