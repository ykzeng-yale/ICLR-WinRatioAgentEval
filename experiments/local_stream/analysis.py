"""Post-run analysis for the local stream (pre-specified in protocol.md).

(a) online cross-arrival design: pass-1 pairs (disjoint arrivals, one exposure
    each) -> NB, WR, tier decomposition, betting CS, guarded decision + stopping index;
(b) shadow same-task design: pass 1 + pass 2 give both variants per task ->
    task-level scores, task-clustered CI (wincs.clustered_summary), by benchmark;
(c) component marginal effects (success, latency, tokens) with CIs;
(d) decision-rules table (success-only, Pareto, utility grid, hierarchical,
    guarded, conjunction);
(e) sensitivity to tolerance (0/10/20%) and tier order: success-first orders
    (latency <-> tokens, absorbing rule) and, for H4, the naive resource-first
    orders latency_s > success > completion_tokens and completion_tokens >
    success > latency_s with NO eligibility mask (every tier compared for
    every pair).
Writes summary.json, CSVs and report.md into the results directory. A dry-run
(mock) results directory gets a MOCK DATA banner in report.md.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import RESULTS_DIR, load_config, read_jsonl, iso, now_ts
from design import load_design
from run_stream import A, B, first_index, monitor_table, pair_scores, tiers_from_config, completed_pairs
from winstats import summary as win_summary
from wincs import betting_cs_ternary, clustered_summary, task_level_scores, win_ratio_cs_decided, cells_from_comparison, cell_counts

UTILITY_GRID = [(1.0, 0.0, 0.0), (0.8, 0.1, 0.1), (0.6, 0.2, 0.2), (0.5, 0.25, 0.25), (0.34, 0.33, 0.33), (0.2, 0.4, 0.4)]


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and (math.isnan(o) or math.isinf(o))) or (isinstance(o, np.floating) and not np.isfinite(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


def t_ci(x, alpha=0.05):
    x = np.asarray(x, float); n = x.size
    if n < 2:
        return dict(n=int(n), mean=float(x.mean()) if n else None, se=None, ci=(None, None))
    se = x.std(ddof=1) / np.sqrt(n); q = stats.t.ppf(1 - alpha / 2, n - 1)
    return dict(n=int(n), mean=float(x.mean()), se=float(se), ci=(float(x.mean() - q * se), float(x.mean() + q * se)))


def welch_ci(x, y, alpha=0.05):
    """CI for mean(y) - mean(x), independent samples."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if x.size < 2 or y.size < 2:
        return dict(diff=None, ci=(None, None))
    vx, vy = x.var(ddof=1) / x.size, y.var(ddof=1) / y.size
    df = (vx + vy) ** 2 / (vx ** 2 / (x.size - 1) + vy ** 2 / (y.size - 1)) if vx + vy > 0 else 1
    q = stats.t.ppf(1 - alpha / 2, df); d = y.mean() - x.mean(); se = np.sqrt(vx + vy)
    return dict(diff=float(d), se=float(se), ci=(float(d - q * se), float(d + q * se)), mean_A=float(x.mean()), mean_B=float(y.mean()))


# ---------------------------------------------------------------- (a) online

def online_analysis(design, episodes, cfg, trial=1, tiers=None, absorbing=True):
    tiers = tiers or tiers_from_config(cfg)
    idx, eA, eB = completed_pairs(design, episodes, trial)
    out = dict(n_pairs=len(idx), design='cross-arrival: pass-1 pairs, disjoint arrivals, one exposure per arrival', absorbing_rule=absorbing)
    if not idx:
        return out
    z, tier, dq = pair_scores(eA, eB, tiers, absorbing=absorbing)
    n = len(z); pos = int((z > 0).sum()); neg = int((z < 0).sum()); tie = n - pos - neg
    out.update(win_summary(z))
    lo, hi = betting_cs_ternary(np.array([pos]), np.array([tie]), np.array([neg]), cfg['alpha'])
    wlo, whi = win_ratio_cs_decided(np.array([pos]), np.array([neg]), cfg['alpha'])
    out.update(nb_cs=(float(lo[0]), float(hi[0])), wr_cs=(float(wlo[0]), float(whi[0]) if np.isfinite(whi[0]) else None))
    qp = int((dq > 0).sum()); qn = int((dq < 0).sum())
    glo, ghi = betting_cs_ternary(np.array([qp]), np.array([n - qp - qn]), np.array([qn]), cfg['alpha'])
    out.update(success_diff_hat=float((qp - qn) / n), success_diff_cs=(float(glo[0]), float(ghi[0])))
    cells = cell_counts(cells_from_comparison(z, tier), len(tiers))
    out['tier_decomposition'] = {t.name: dict(wins=int(cells[2 * k + 1]), losses=int(cells[2 * k + 2]),
                                              contribution=float((cells[2 * k + 1] - cells[2 * k + 2]) / n)) for k, t in enumerate(tiers)}
    out['ties'] = tie
    rows = monitor_table(z, dq, cfg)
    out['monitoring'] = dict(first_win_cross=first_index(rows, 'win_cross'), first_gate_cross=first_index(rows, 'gate_cross'),
                             first_deploy=first_index(rows, 'deploy'), first_harm=first_index(rows, 'harm'),
                             final_log_e_win=rows[-1]['log_e_win'], final_log_e_gate=rows[-1]['log_e_gate'], final_log_e_harm=rows[-1]['log_e_harm'])
    dep = out['monitoring']['first_deploy'] is not None; harm = out['monitoring']['first_harm'] is not None
    out['guarded_decision'] = 'deploy_B' if dep else ('B_harmful' if harm else 'inconclusive')
    out['fixed_horizon_decision'] = 'B' if lo[0] > 0 and glo[0] > -cfg['success_margin'] else ('A' if hi[0] < 0 else 'inconclusive')
    out['by_benchmark'] = {}
    for bm in cfg['benchmarks']:
        m = np.array([e['benchmark'] == bm for e in eA]) & np.array([e['benchmark'] == bm for e in eB])
        out['by_benchmark'][bm + '_both'] = dict(n_pairs=int(m.sum()), **(win_summary(z[m]) if m.any() else {}))
    return out


# ---------------------------------------------------------------- (b) shadow

def runs_by_task(episodes, variant, names, trial=None):
    d = {}
    for e in episodes:
        if e['variant'] != variant or (trial is not None and e['trial'] != trial):
            continue
        d.setdefault(e['task_id'], []).append([float(bool(e['success'])) if nm == 'success' else float(e[nm]) for nm in names])
    return {k: np.array(v) for k, v in d.items()}


def eligible_fn(names, absorbing=True):
    """Absorbing rule (frozen): non-success tiers only when both succeeded. absorbing=False: no mask (H4 rows)."""
    si = names.index('success')

    def f(Xa, Xb):
        e = np.ones(np.broadcast(Xa, Xb).shape, bool)
        if absorbing:
            both = (Xa[..., si] > .5) & (Xb[..., si] > .5)
            for k, nm in enumerate(names):
                if nm != 'success':
                    e[..., k] = both
        return e
    return f


def shadow_analysis(episodes, cfg, tasks_by_uid, tiers=None, absorbing=True):
    tiers = tiers or tiers_from_config(cfg); names = [t.name for t in tiers]
    RA = runs_by_task(episodes, A, names); RB = runs_by_task(episodes, B, names)
    common = sorted(set(RA) & set(RB))
    out = dict(design='same-task shadow: both variants per task (pass 1 + pass 2; all trials as replicates)', n_tasks=len(common), absorbing_rule=absorbing)
    if len(common) < 2:
        return out
    tl = task_level_scores({k: RB[k] for k in common}, {k: RA[k] for k in common}, tiers, eligible=eligible_fn(names, absorbing), pairing='all')
    cs = clustered_summary(tl['win'], tl['loss'], alpha=cfg['alpha'])
    out.update(_summ(cs)); out['tier_contribution_mean'] = {t.name: float(tl['tier_contribution'][:, k].mean()) for k, t in enumerate(tiers)}
    out['by_benchmark'] = {}
    bms = np.array([tasks_by_uid[t]['benchmark'] for t in tl['tasks']])
    for bm in cfg['benchmarks']:
        m = bms == bm
        if m.sum() >= 2:
            out['by_benchmark'][bm] = _summ(clustered_summary(tl['win'][m], tl['loss'][m], alpha=cfg['alpha']))
    # equal-weight stratified combination across benchmarks (fixed weights)
    if len(out['by_benchmark']) == 2:
        w = np.where(bms == cfg['benchmarks'][0], 0.5 / (bms == cfg['benchmarks'][0]).sum(), 0.5 / (bms == cfg['benchmarks'][1]).sum())
        out['stratified_equal_weight'] = _summ(clustered_summary(tl['win'], tl['loss'], weights=w, alpha=cfg['alpha']))
    out['task_scores'] = dict(tasks=tl['tasks'], win=tl['win'].tolist(), loss=tl['loss'].tolist(), tie=tl['tie'].tolist())
    out['decision_hierarchical'] = 'B' if cs['nb_ci'][0] > 0 else ('A' if cs['nb_ci'][1] < 0 else 'inconclusive')
    return out


def _summ(cs):
    keys = ('n_tasks', 'p_win', 'p_loss', 'p_tie', 'net_benefit', 'nb_se', 'nb_ci', 'win_ratio', 'wr_ci', 'win_odds', 'wo_ci')
    return {k: cs.get(k) for k in keys}


# ---------------------------------------------------------------- (c) components

def component_effects(episodes, design, cfg, trial=1):
    out = {}
    eA = [e for e in episodes if e['variant'] == A]; eB = [e for e in episodes if e['variant'] == B]
    comps = ['success', 'latency_s', 'completion_tokens', 'prompt_tokens', 'n_llm_calls', 'n_executions']
    # same-task paired (task-clustered): mean over replicates per task then paired t over tasks
    def per_task(eps, comp):
        d = {}
        for e in eps:
            d.setdefault(e['task_id'], []).append(float(bool(e[comp])) if comp == 'success' else float(e[comp]))
        return {k: np.mean(v) for k, v in d.items()}
    out['same_task_paired'] = {}
    for c in comps:
        ta, tb = per_task(eA, c), per_task(eB, c); common = sorted(set(ta) & set(tb))
        if len(common) >= 2:
            diff = np.array([tb[t] - ta[t] for t in common])
            r = t_ci(diff, cfg['alpha']); r.update(mean_A=float(np.mean([ta[t] for t in common])), mean_B=float(np.mean([tb[t] for t in common])))
            if c in ('latency_s', 'completion_tokens'):
                r['median_A'] = float(np.median([ta[t] for t in common])); r['median_B'] = float(np.median([tb[t] for t in common]))
                r['ratio_of_means_B_over_A'] = float(r['mean_B'] / r['mean_A']) if r['mean_A'] > 0 else None
            out['same_task_paired'][c] = r
    # online cross-arrival: independent arms (pass 1 only)
    idx, pA, pB = completed_pairs(design, episodes, trial)
    out['cross_arrival_independent'] = {}
    for c in comps:
        xa = [float(bool(e[c])) if c == 'success' else float(e[c]) for e in pA]; xb = [float(bool(e[c])) if c == 'success' else float(e[c]) for e in pB]
        out['cross_arrival_independent'][c] = welch_ci(xa, xb, cfg['alpha'])
    # failure accounting (outcomes, never exclusions)
    out['failure_accounting'] = {v: dict(n=len(eps), timed_out=int(sum(e['timed_out'] for e in eps)), sandbox_flag=int(sum(e['sandbox_flag'] for e in eps)),
                                         api_error=int(sum(e['error'] is not None for e in eps)), empty_code=int(sum(not e['final_code'].strip() for e in eps)),
                                         tokens_estimated=int(sum(bool(e.get('tokens_estimated')) for e in eps)),
                                         connection_retries=int(sum(e.get('connection_retries', 0) for e in eps)),
                                         entry_point_missing=int(sum(e.get('entry_point_defined') is False for e in eps)),
                                         sentinel_missing_rc0=int(sum((e.get('verify_returncode') == 0 and not e.get('sentinel_seen', True)) for e in eps)),
                                         hack_flagged=int(sum(bool(e.get('hack_flags')) for e in eps)),
                                         hack_flagged_success=int(sum(bool(e.get('hack_flags')) and bool(e['success']) for e in eps)),
                                         static_flagged=int(sum(bool(e.get('static_flags')) for e in eps)),
                                         verify_seconds_mean=(float(np.mean([e.get('verify_seconds', 0.0) for e in eps])) if eps else None))
                                 for v, eps in (('single_shot', eA), ('self_test_repair', eB))}
    return out


# ---------------------------------------------------------------- (d) decision rules

def decision_rules(shadow, comps, online, cfg):
    """Rules applied to the same data; each returns a decision B / A / none / tradeoff.

    success_only: paired success difference CI excludes 0.
    pareto: means of (success up, latency down, tokens down); dominance = no worse on all, better on one.
    utility_w: sign of w1*d_success - w2*rel_latency - w3*rel_tokens (relative differences of means, B vs A).
    hierarchical: task-clustered NB CI excludes 0 (shadow) / betting CS excludes 0 (online).
    guarded: hierarchical NB > 0 AND success non-inferiority (lower CI/CS bound > -margin).
    conjunction: success CI lower > -margin AND latency CI upper < 0 AND tokens CI upper < 0 (all components better or non-inferior).
    """
    rows = []
    sp = comps.get('same_task_paired', {})
    def dec_from_ci(ci):
        lo, hi = ci
        if lo is None:
            return 'none'
        return 'B' if lo > 0 else ('A' if hi < 0 else 'none')
    if 'success' in sp:
        rows.append(dict(rule='success_only', data='shadow', estimate=sp['success']['mean'], ci=sp['success']['ci'], decision=dec_from_ci(sp['success']['ci'])))
    if all(k in sp for k in ('success', 'latency_s', 'completion_tokens')):
        ds, dl, dt = sp['success']['mean'], sp['latency_s']['mean'], sp['completion_tokens']['mean']
        b_no_worse = ds >= 0 and dl <= 0 and dt <= 0; a_no_worse = ds <= 0 and dl >= 0 and dt >= 0
        par = 'B' if b_no_worse and (ds > 0 or dl < 0 or dt < 0) else ('A' if a_no_worse and (ds < 0 or dl > 0 or dt > 0) else 'tradeoff')
        rows.append(dict(rule='pareto_means', data='shadow', estimate=None, ci=(None, None), decision=par,
                         detail='d_success=%.4f d_latency=%.3f d_tokens=%.1f' % (ds, dl, dt)))
        rl = dl / sp['latency_s']['mean_A'] if sp['latency_s']['mean_A'] else 0.0
        rt = dt / sp['completion_tokens']['mean_A'] if sp['completion_tokens']['mean_A'] else 0.0
        for w in UTILITY_GRID:
            u = w[0] * ds - w[1] * rl - w[2] * rt
            rows.append(dict(rule='utility_w=%.2f/%.2f/%.2f' % w, data='shadow', estimate=float(u), ci=(None, None),
                             decision='B' if u > 0 else ('A' if u < 0 else 'none'), detail='u = w1*d_success - w2*rel_d_latency - w3*rel_d_tokens (point estimate only)'))
    if shadow.get('nb_ci'):
        rows.append(dict(rule='hierarchical_nb', data='shadow', estimate=shadow['net_benefit'], ci=shadow['nb_ci'], decision=dec_from_ci(shadow['nb_ci'])))
        if 'success' in sp:
            g = shadow['nb_ci'][0] > 0 and sp['success']['ci'][0] is not None and sp['success']['ci'][0] > -cfg['success_margin']
            rows.append(dict(rule='guarded_hierarchical', data='shadow', estimate=shadow['net_benefit'], ci=shadow['nb_ci'],
                             decision='B' if g else ('A' if shadow['nb_ci'][1] < 0 else 'none'), detail='NB CI > 0 and success CI lower > -%.2f' % cfg['success_margin']))
    if all(k in sp for k in ('success', 'latency_s', 'completion_tokens')) and sp['success']['ci'][0] is not None:
        c = sp['success']['ci'][0] > -cfg['success_margin'] and sp['latency_s']['ci'][1] < 0 and sp['completion_tokens']['ci'][1] < 0
        rows.append(dict(rule='conjunction_all_components', data='shadow', estimate=None, ci=(None, None), decision='B' if c else 'none',
                         detail='success non-inferior AND latency lower AND tokens lower (all CIs)'))
    if online.get('nb_cs'):
        rows.append(dict(rule='hierarchical_nb_betting_cs', data='online', estimate=online['net_benefit'], ci=online['nb_cs'], decision=dec_from_ci(online['nb_cs'])))
        rows.append(dict(rule='guarded_anytime', data='online', estimate=online['net_benefit'], ci=online['nb_cs'],
                         decision={'deploy_B': 'B', 'B_harmful': 'A', 'inconclusive': 'none'}[online['guarded_decision']],
                         detail='first_deploy=%s first_harm=%s' % (online['monitoring']['first_deploy'], online['monitoring']['first_harm'])))
        if online.get('success_diff_cs'):
            rows.append(dict(rule='success_only_betting_cs', data='online', estimate=online['success_diff_hat'], ci=online['success_diff_cs'], decision=dec_from_ci(online['success_diff_cs'])))
    return rows


# ---------------------------------------------------------------- (e) sensitivity

SENSITIVITY_ORDERS = [
    # (order, absorbing) -- success-first orders keep the frozen absorbing rule; resource-first orders (H4) use no mask
    (['success', 'latency_s', 'completion_tokens'], True),
    (['success', 'completion_tokens', 'latency_s'], True),
    (['latency_s', 'success', 'completion_tokens'], False),
    (['completion_tokens', 'success', 'latency_s'], False),
]


def sensitivity(design, episodes, cfg, tasks_by_uid, trial=1):
    rows = []
    for tol in (0.0, 0.10, 0.20):
        for order, absorbing in SENSITIVITY_ORDERS:
            tiers = tiers_from_config(cfg, tolerance=tol, order=order)
            sh = shadow_analysis(episodes, cfg, tasks_by_uid, tiers, absorbing=absorbing)
            on = online_analysis(design, episodes, cfg, trial, tiers, absorbing=absorbing)
            rows.append(dict(tolerance=tol, order='>'.join(order), eligibility='absorbing' if absorbing else 'none',
                             shadow_nb=sh.get('net_benefit'), shadow_nb_lo=(sh.get('nb_ci') or (None, None))[0],
                             shadow_nb_hi=(sh.get('nb_ci') or (None, None))[1], shadow_decision=sh.get('decision_hierarchical'),
                             online_nb=on.get('net_benefit'), online_nb_lo=(on.get('nb_cs') or (None, None))[0], online_nb_hi=(on.get('nb_cs') or (None, None))[1],
                             online_guarded=on.get('guarded_decision'), online_first_deploy=(on.get('monitoring') or {}).get('first_deploy')))
    return rows


# ---------------------------------------------------------------- report

def report_md(summary, results_dir):
    o, s, c = summary['online'], summary['shadow'], summary['components']
    L = ['# Local stream: analysis report (skeleton)', '']
    if summary.get('dry_run'):
        L += ['> **MOCK DATA - DRY RUN.** These numbers come from the deterministic MockModel (`model=%s`). They test the pipeline only and must never be copied into the paper.' % summary.get('model'), '']
    L += ['Generated %s from `%s`. Fill the interpretation sections after the frozen analysis; do not edit numbers by hand.' % (summary['generated_at'], results_dir), '',
         '## Accounting', '', '- Episodes: %d (trial(s) %s); dry_run=%s; model=%s' % (summary['n_episodes'], summary['trials'], summary['dry_run'], summary['model']),
         '- Failure accounting: %s' % json.dumps(c.get('failure_accounting', {})), '',
         '## (a) Online cross-arrival design', '', '- Pairs: %s; NB=%s, NB CS=%s; WR=%s, WR CS=%s' % (o.get('n_pairs'), _f(o.get('net_benefit')), o.get('nb_cs'), _f(o.get('win_ratio')), o.get('wr_cs')),
         '- Success diff (B-A) = %s, CS %s; guarded decision: %s; first deploy index: %s; first harm index: %s' % (
             _f(o.get('success_diff_hat')), o.get('success_diff_cs'), o.get('guarded_decision'), (o.get('monitoring') or {}).get('first_deploy'), (o.get('monitoring') or {}).get('first_harm')),
         '- Tier decomposition: %s' % json.dumps(o.get('tier_decomposition', {})), '',
         '## (b) Same-task shadow design', '', '- Tasks: %s; NB=%s CI=%s; WR=%s CI=%s; decision: %s' % (s.get('n_tasks'), _f(s.get('net_benefit')), s.get('nb_ci'), _f(s.get('win_ratio')), s.get('wr_ci'), s.get('decision_hierarchical')),
         '- By benchmark: %s' % json.dumps({k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk in ('n_tasks', 'net_benefit', 'nb_ci')} for k, v in s.get('by_benchmark', {}).items()}), '',
         '## (c) Component effects (B - A)', '', '| component | same-task mean diff | CI | cross-arrival diff | CI |', '|---|---|---|---|---|']
    for comp in ('success', 'latency_s', 'completion_tokens'):
        a = c.get('same_task_paired', {}).get(comp, {}); b = c.get('cross_arrival_independent', {}).get(comp, {})
        L.append('| %s | %s | %s | %s | %s |' % (comp, _f(a.get('mean')), _ci(a.get('ci')), _f(b.get('diff')), _ci(b.get('ci'))))
    L += ['', '## (d) Decision rules', '', '| rule | data | estimate | CI | decision |', '|---|---|---|---|---|']
    for r in summary['decision_rules']:
        L.append('| %s | %s | %s | %s | %s |' % (r['rule'], r['data'], _f(r['estimate']), _ci(r['ci']), r['decision']))
    L += ['', '## (e) Sensitivity (tolerance x tier order; H4 = resource-first rows with eligibility "none")', '',
          '| tol | order | eligibility | shadow NB [CI] | shadow dec | online NB [CS] | online guarded |', '|---|---|---|---|---|---|---|']
    for r in summary['sensitivity']:
        L.append('| %s | %s | %s | %s [%s, %s] | %s | %s [%s, %s] | %s |' % (r['tolerance'], r['order'], r['eligibility'], _f(r['shadow_nb']), _f(r['shadow_nb_lo']), _f(r['shadow_nb_hi']), r['shadow_decision'],
                                                                        _f(r['online_nb']), _f(r['online_nb_lo']), _f(r['online_nb_hi']), r['online_guarded']))
    L += ['', '## Interpretation (to be written after unblinding; see protocol.md section 12)', '', '_pending_', '', '## Deviations from protocol', '', '_none recorded yet; see protocol.md deviations log_', '']
    return '\n'.join(L)


def _f(x):
    return 'NA' if x is None else ('%.4f' % x if isinstance(x, float) else str(x))


def _ci(ci):
    return 'NA' if not ci or ci[0] is None else '[%.4f, %.4f]' % tuple(ci)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--config', default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config); rd = Path(args.results_dir)
    from data import load_tasks
    tasks_by_uid = {t['uid']: t for t in load_tasks()}
    design = load_design(rd, 1)
    episodes = read_jsonl(rd / 'episodes.jsonl')
    if not episodes:
        raise SystemExit('no episodes in %s' % rd)
    manifest = json.loads((rd / 'run_manifest.json').read_text()) if (rd / 'run_manifest.json').exists() else {}
    invs = manifest.get('invocations') or []
    m_dry = any(i.get('dry_run') for i in invs) or bool(manifest.get('dry_run')) or any(e.get('model_kind') == 'mock' for e in episodes)
    m_model = (invs[-1].get('model') if invs else manifest.get('model')) or (episodes[-1].get('model') if episodes else None)
    m_design_sha = (invs[-1].get('design_sha256') if invs else manifest.get('design_sha256'))
    online = online_analysis(design, episodes, cfg, 1)
    shadow = shadow_analysis(episodes, cfg, tasks_by_uid)
    comps = component_effects(episodes, design, cfg, 1)
    rules = _clean(decision_rules(shadow, comps, online, cfg))
    sens = _clean(sensitivity(design, episodes, cfg, tasks_by_uid, 1))
    summary = dict(generated_at=iso(now_ts()), results_dir=str(rd), n_episodes=len(episodes), trials=sorted({e['trial'] for e in episodes}),
                   dry_run=bool(m_dry), model=m_model, config_hash=cfg['_config_hash'], design_sha256=m_design_sha, n_invocations=len(invs),
                   online=online, shadow={k: v for k, v in shadow.items() if k != 'task_scores'}, components=comps, decision_rules=rules, sensitivity=sens)
    summary = _clean(summary)
    (rd / 'summary.json').write_text(json.dumps(summary, indent=2))
    pd.DataFrame(rules).to_csv(rd / 'decision_rules.csv', index=False)
    pd.DataFrame(sens).to_csv(rd / 'sensitivity.csv', index=False)
    if shadow.get('task_scores'):
        ts = shadow['task_scores']
        pd.DataFrame(dict(task_id=ts['tasks'], benchmark=[tasks_by_uid[t]['benchmark'] for t in ts['tasks']], win=ts['win'], loss=ts['loss'], tie=ts['tie'])).to_csv(rd / 'task_scores.csv', index=False)
    pd.DataFrame([{k: v for k, v in e.items() if k not in ('final_code', 'self_test_code', 'verify_stderr', 'retry_log', 'error_traceback', 'llm_call_seconds', 'execution_seconds', 'finish_reasons', 'response_models')} for e in episodes]).to_csv(rd / 'episodes_flat.csv', index=False)
    (rd / 'report.md').write_text(report_md(summary, rd))
    print(json.dumps(dict(online={k: online.get(k) for k in ('n_pairs', 'net_benefit', 'nb_cs', 'guarded_decision')},
                          shadow={k: shadow.get(k) for k in ('n_tasks', 'net_benefit', 'nb_ci', 'decision_hierarchical')}), indent=2, default=str))


if __name__ == '__main__':
    main()
