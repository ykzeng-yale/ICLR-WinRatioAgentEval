"""Post-run analysis for the tau2 open-model stream (pre-specified in protocol.md).

(a) online cross-arrival design: the prespecified pass-1 pairs (disjoint arrivals, one exposure each)
    -> pair scores in arrival order, monitoring log (guarded betting e-processes, written post hoc over the
    prespecified sequence because tau2 executes arms in batches), NB, WR, tier decomposition, betting CS,
    guarded decision, first-crossing indices; the block-1 subset (pairs whose two arrivals are both in block 1 =
    pairs 1-24, distinct tasks; pair 25 straddles the two blocks because a block holds 49 units) as a prespecified subset;
(b) shadow same-task design: both arms per (task, trial) -> task-level scores over the 2 trials per arm
    (pairing 'all' primary; 'offdiagonal' and 'diagonal' sensitivity; runs are sorted by tau2 trial within a task, so
    'diagonal' = same trial = same tau2 trial seed), task-clustered CI (wincs.clustered_summary);
(c) component marginal effects (success, tokens, tool calls, duration, ...) with CIs and failure accounting;
(d) decision-rule table (success-only, Pareto, utility grid, hierarchical, guarded, conjunction);
(e) sensitivity: relative token tolerance 0/5/10/20 % x tier orders (success>tokens>calls absorbing [primary at 5 %],
    success>calls>tokens, success>duration>tokens, success>tokens>calls lexicographic non-absorbing,
    tokens>success>calls with no eligibility mask [H4]).
Scores are B vs A: +1 = arm B (candidate agent, qwen3-4b-instruct-2507) preferred over arm A (incumbent, qwen2.5-7b-instruct).
H1 (direction-uncertain success difference) and H3 (the hierarchical sign is determined by the success tier) get explicit
flags (`success_tier_determines_sign`). Writes summary.json, CSVs, monitor files and report.md
into the results directory; a dry-run (mock) directory gets a MOCK DATA banner.
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import RESULTS_DIR, iso, load_config, now_ts
from design import A, B, load_design
from winstats import Tier, betting_log_e_ternary, compare
from winstats import summary as win_summary
from wincs import betting_cs_ternary, cell_counts, cells_from_comparison, clustered_summary, task_level_scores, win_ratio_cs_decided

UTILITY_GRID = [(1.0, 0.0, 0.0), (0.8, 0.1, 0.1), (0.6, 0.2, 0.2), (0.5, 0.25, 0.25), (0.34, 0.33, 0.33), (0.2, 0.4, 0.4)]
COST_TIERS = ('agent_tokens_completion', 'duration', 'agent_tokens_prompt')  # tiers the tolerance grid applies to; tool calls keep tolerance 0
COMPONENTS = ['success', 'agent_tokens_completion', 'agent_tokens_prompt', 'n_assistant_tool_calls', 'n_agent_llm_calls', 'duration', 'agent_generation_seconds']
INT_COLS = ('trial', 'tau2_seed', 'arrival_index', 'pair_index', 'position_in_pair', 'orientation', 'pass', 'block', 'agent_tokens_completion', 'agent_tokens_prompt',
            'n_agent_llm_calls', 'n_assistant_tool_calls', 'n_assistant_messages', 'n_user_messages', 'n_tool_messages', 'n_messages', 'tokens_estimated_calls')
FLOAT_COLS = ('reward', 'duration', 'agent_generation_seconds')
BOOL_COLS = ('success', 'max_steps_hit')


def load_episodes(path) -> list:
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            e = {}
            for k, v in r.items():
                if v == '' or v is None:
                    e[k] = None
                elif k in INT_COLS:
                    e[k] = int(float(v))
                elif k in FLOAT_COLS:
                    e[k] = float(v)
                elif k in BOOL_COLS:
                    e[k] = v == 'True'
                else:
                    e[k] = v
            rows.append(e)
    return rows


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


# ---------------------------------------------------------------- tiers and scores

def tiers_from_config(cfg, tolerance=None, order=None):
    """Tiers from config; tolerance (cost tiers only) and order overrides are for sensitivity analyses."""
    spec = {t['name']: t for t in cfg['hierarchy']}
    spec.setdefault('duration', dict(name='duration', higher_better=False, relative_tolerance=spec['agent_tokens_completion']['relative_tolerance']))
    spec.setdefault('agent_tokens_prompt', dict(name='agent_tokens_prompt', higher_better=False, relative_tolerance=spec['agent_tokens_completion']['relative_tolerance']))
    names = order or [t['name'] for t in cfg['hierarchy']]
    out = []
    for nm in names:
        s = spec[nm]
        tol = s.get('relative_tolerance', 0.0) if (tolerance is None or nm not in COST_TIERS) else tolerance
        out.append(Tier(nm, bool(s['higher_better']), relative_tolerance=float(tol)))
    return out


def outcome_vector(ep: dict, names) -> list:
    out = []
    for nm in names:
        v = ep[nm]
        out.append(float(bool(v)) if nm == 'success' else float(v if v is not None else np.nan))
    return out


def pair_scores(eps_A, eps_B, tiers, absorbing=True):
    """B vs A hierarchical scores (+1 = B preferred) and success differences (B-A) for aligned episode lists."""
    names = [t.name for t in tiers]
    XA = np.array([outcome_vector(e, names) for e in eps_A], float).reshape(-1, len(names))
    XB = np.array([outcome_vector(e, names) for e in eps_B], float).reshape(-1, len(names))
    for X in (XA, XB):  # a missing duration (None) can only occur on an errored episode: treat as the worst value among the pairs
        for k in range(len(names)):
            col = X[:, k]
            if np.isnan(col).any():
                col[np.isnan(col)] = (np.nanmax(np.concatenate([XA[:, k], XB[:, k]])) if not tiers[k].higher_better else 0.0) if np.isfinite(np.nanmax(np.concatenate([XA[:, k], XB[:, k]]))) else 0.0
    elig = np.ones(XA.shape, bool)
    if absorbing:
        both = (XA[:, names.index('success')] > .5) & (XB[:, names.index('success')] > .5)
        for k, nm in enumerate(names):
            if nm != 'success':
                elig[:, k] = both
    z, tier = compare(XB, XA, tiers, elig)
    dq = (XB[:, names.index('success')] - XA[:, names.index('success')]).astype(int)
    return z.astype(int), tier.astype(int), dq


def pair_blocks(design) -> dict:
    """pair_index -> set of the blocks of its two arrivals (a pair straddles when the set has two elements)."""
    out = {}
    for a in design['arrivals']:
        if a['pair_index'] is not None:
            out.setdefault(a['pair_index'], set()).add(a['block'])
    return out


def completed_pairs(design, episodes):
    """Prespecified pass-1 pairs whose two episodes exist, in pair order. Returns (pair_indices, eps_A, eps_B, blocks).

    The block of a pair is the LARGEST block among its two arrivals, so a pair that straddles blocks 1 and 2 (pair 25 with
    49 units per block) is assigned to block 2 and the block-1 subset (`blocks_keep={1}`) contains exactly the pairs whose
    two arrivals are both in block 1 (pairs 1-24).
    """
    by_key = {(e['arm'], e['task_id'], e['trial']): e for e in episodes}
    pb = pair_blocks(design)
    pairs = {}
    for a in design['arrivals']:
        if a['pair_index'] is None:
            continue
        e = by_key.get((a['pass1_arm'], a['task_id'], a['trial']))
        if e is not None:
            pairs.setdefault(a['pair_index'], {})[a['pass1_arm']] = e
    idx = sorted(k for k, v in pairs.items() if A in v and B in v)
    return idx, [pairs[k][A] for k in idx], [pairs[k][B] for k in idx], [max(pb[k]) for k in idx]


# ---------------------------------------------------------------- monitoring (post hoc over the prespecified sequence)

def monitor_table(z, dq, cfg) -> list:
    alpha, margin, min_n = cfg['alpha'], cfg['success_margin'], cfg['min_n_pairs']
    if len(z) == 0:
        return []
    n = np.arange(1, len(z) + 1)
    z = np.asarray(z); dq = np.asarray(dq)
    pos = np.cumsum(z > 0); neg = np.cumsum(z < 0); qp = np.cumsum(dq > 0); qn = np.cumsum(dq < 0)
    le_win = betting_log_e_ternary(pos, neg, n, 0.0); le_harm = betting_log_e_ternary(neg, pos, n, 0.0); le_gate = betting_log_e_ternary(qp, qn, n, -margin)
    thr = np.log(1 / alpha)
    rows = []
    for i in range(len(z)):
        ok = n[i] >= min_n
        rows.append(dict(n=int(n[i]), z=int(z[i]), success_diff=int(dq[i]), n_win=int(pos[i]), n_loss=int(neg[i]), n_tie=int(n[i] - pos[i] - neg[i]),
                         n_succ_pos=int(qp[i]), n_succ_neg=int(qn[i]), nb_hat=float((pos[i] - neg[i]) / n[i]), succ_diff_hat=float((qp[i] - qn[i]) / n[i]),
                         log_e_win=float(le_win[i]), log_e_gate=float(le_gate[i]), log_e_harm=float(le_harm[i]),
                         win_cross=bool(le_win[i] >= thr and ok), gate_cross=bool(le_gate[i] >= thr and ok),
                         deploy=bool(le_win[i] >= thr and le_gate[i] >= thr and ok), harm=bool(le_harm[i] >= thr and ok)))
    return rows


def success_determines_sign(contrib: dict, nb) -> bool | None:
    """H3 flag: NB != 0, the success tier's contribution has the sign of NB and its magnitude is at least the combined
    magnitude of every lower tier's contribution (so the hierarchical decision is determined by success first)."""
    if nb is None or 'success' not in contrib or abs(nb) < 1e-12:
        return None
    cs = contrib['success']; rest = sum(abs(v) for k, v in contrib.items() if k != 'success')
    return bool(cs * nb > 0 and abs(cs) >= rest)


def first_index(rows, key):
    for r in rows:
        if r[key]:
            return r['n']
    return None


MONITOR_COLS = ['pair_index', 'block', 'n', 'z', 'decisive_tier', 'success_diff', 'n_win', 'n_loss', 'n_tie', 'n_succ_pos', 'n_succ_neg', 'nb_hat', 'succ_diff_hat',
                'log_e_win', 'log_e_gate', 'log_e_harm', 'win_cross', 'gate_cross', 'deploy', 'harm']


def write_monitor(results_dir: Path, design, episodes, cfg) -> dict:
    idx, eA, eB, blocks = completed_pairs(design, episodes)
    rows = []
    if idx:
        z, tier, dq = pair_scores(eA, eB, tiers_from_config(cfg))
        rows = monitor_table(z, dq, cfg)
        for r, k, tk, b in zip(rows, idx, tier, blocks):
            r['pair_index'] = k; r['decisive_tier'] = int(tk); r['block'] = b
    with open(results_dir / 'monitor_pass1.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=MONITOR_COLS); w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in MONITOR_COLS})
    state = dict(n_pairs_monitored=len(rows), alpha=cfg['alpha'], success_margin=cfg['success_margin'], min_n_pairs=cfg['min_n_pairs'],
                 first_win_cross=first_index(rows, 'win_cross'), first_gate_cross=first_index(rows, 'gate_cross'), first_deploy=first_index(rows, 'deploy'),
                 first_harm=first_index(rows, 'harm'), note='monitoring computed post hoc over the prespecified arrival sequence (tau2 executes arms in batches); execution never stopped early',
                 updated_at=iso(now_ts()))
    (results_dir / 'monitor_state.json').write_text(json.dumps(state, indent=2))
    return state


# ---------------------------------------------------------------- CIs

def t_ci(x, alpha=0.05):
    x = np.asarray(x, float); n = x.size
    if n < 2:
        return dict(n=int(n), mean=float(x.mean()) if n else None, se=None, ci=(None, None))
    se = x.std(ddof=1) / np.sqrt(n); q = stats.t.ppf(1 - alpha / 2, n - 1)
    return dict(n=int(n), mean=float(x.mean()), se=float(se), ci=(float(x.mean() - q * se), float(x.mean() + q * se)))


def welch_ci(x, y, alpha=0.05):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if x.size < 2 or y.size < 2:
        return dict(diff=None, ci=(None, None))
    vx, vy = x.var(ddof=1) / x.size, y.var(ddof=1) / y.size
    df = (vx + vy) ** 2 / (vx ** 2 / (x.size - 1) + vy ** 2 / (y.size - 1)) if vx + vy > 0 else 1
    q = stats.t.ppf(1 - alpha / 2, df); d = y.mean() - x.mean(); se = np.sqrt(vx + vy)
    return dict(diff=float(d), se=float(se), ci=(float(d - q * se), float(d + q * se)), mean_A=float(x.mean()), mean_B=float(y.mean()))


# ---------------------------------------------------------------- (a) online

def online_analysis(design, episodes, cfg, tiers=None, absorbing=True, blocks_keep=None):
    tiers = tiers or tiers_from_config(cfg)
    idx, eA, eB, blocks = completed_pairs(design, episodes)
    if blocks_keep is not None:
        keep = [i for i, b in enumerate(blocks) if b in blocks_keep]
        idx = [idx[i] for i in keep]; eA = [eA[i] for i in keep]; eB = [eB[i] for i in keep]; blocks = [blocks[i] for i in keep]
    pb = pair_blocks(design)
    out = dict(n_pairs=len(idx), design='cross-arrival: prespecified pass-1 pairs, disjoint (task, trial) units, one exposure per arrival', absorbing_rule=absorbing,
               blocks=sorted(set(blocks)), n_pairs_straddling_blocks=int(sum(len(pb[k]) > 1 for k in idx)),
               block_rule='pair block = max block of its two arrivals; block-1 subset = pairs with both arrivals in block 1')
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
    out['tier_decomposition'] = {t.name: dict(wins=int(cells[2 * k + 1]), losses=int(cells[2 * k + 2]), contribution=float((cells[2 * k + 1] - cells[2 * k + 2]) / n)) for k, t in enumerate(tiers)}
    out['ties'] = tie
    out['success_tier_determines_sign'] = success_determines_sign({k: v['contribution'] for k, v in out['tier_decomposition'].items()}, out['net_benefit'])
    rows = monitor_table(z, dq, cfg)
    out['monitoring'] = dict(first_win_cross=first_index(rows, 'win_cross'), first_gate_cross=first_index(rows, 'gate_cross'), first_deploy=first_index(rows, 'deploy'),
                             first_harm=first_index(rows, 'harm'), final_log_e_win=rows[-1]['log_e_win'], final_log_e_gate=rows[-1]['log_e_gate'], final_log_e_harm=rows[-1]['log_e_harm'])
    dep = out['monitoring']['first_deploy'] is not None; harm = out['monitoring']['first_harm'] is not None
    out['guarded_decision'] = 'deploy_B' if dep else ('B_harmful' if harm else 'inconclusive')
    out['fixed_horizon_decision'] = 'B' if lo[0] > 0 and glo[0] > -cfg['success_margin'] else ('A' if hi[0] < 0 else 'inconclusive')
    same_task = np.array([a['task_id'] == b['task_id'] for a, b in zip(eA, eB)])
    out['n_pairs_same_task_different_trial'] = int(same_task.sum())
    return out


# ---------------------------------------------------------------- (b) shadow

def runs_by_task(episodes, arm, names):
    """task_id -> array of outcome vectors, rows sorted by tau2 trial (so the i-th row of A and of B share the trial seed)."""
    d = {}
    for e in sorted(episodes, key=lambda e: (e['trial'] if e['trial'] is not None else -1)):
        if e['arm'] == arm:
            d.setdefault(e['task_id'], []).append(outcome_vector(e, names))
    return {k: np.nan_to_num(np.array(v), nan=0.0) for k, v in d.items()}


def eligible_fn(names, absorbing=True):
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


def shadow_analysis(episodes, cfg, tiers=None, absorbing=True, pairing='all'):
    tiers = tiers or tiers_from_config(cfg); names = [t.name for t in tiers]
    RA = runs_by_task(episodes, A, names); RB = runs_by_task(episodes, B, names)
    common = sorted(set(RA) & set(RB), key=lambda t: (len(t), t))
    out = dict(design='same-task shadow: both arms per (task, trial); trials are replicates within the task cluster', n_tasks=len(common), absorbing_rule=absorbing, pairing=pairing)
    if len(common) < 2:
        return out
    tl = task_level_scores({k: RB[k] for k in common}, {k: RA[k] for k in common}, tiers, eligible=eligible_fn(names, absorbing), pairing=pairing)
    cs = clustered_summary(tl['win'], tl['loss'], alpha=cfg['alpha'])
    out.update(_summ(cs)); out['tier_contribution_mean'] = {t.name: float(tl['tier_contribution'][:, k].mean()) for k, t in enumerate(tiers)}
    out['success_tier_determines_sign'] = success_determines_sign(out['tier_contribution_mean'], out.get('net_benefit'))
    out['task_scores'] = dict(tasks=tl['tasks'], win=tl['win'].tolist(), loss=tl['loss'].tolist(), tie=tl['tie'].tolist())
    out['decision_hierarchical'] = 'B' if cs['nb_ci'][0] > 0 else ('A' if cs['nb_ci'][1] < 0 else 'inconclusive')
    # replicate agreement: fraction of tasks whose two trials give identical outcome vectors within an arm (agent temperature 0.3)
    agree = {}
    for arm, R in ((A, RA), (B, RB)):
        vals = [np.all(R[t][0] == R[t][1]) for t in common if len(R[t]) >= 2]
        agree[arm] = float(np.mean(vals)) if vals else None
    out['replicate_identical_fraction'] = agree
    return out


def _summ(cs):
    keys = ('n_tasks', 'p_win', 'p_loss', 'p_tie', 'net_benefit', 'nb_se', 'nb_ci', 'win_ratio', 'wr_ci', 'win_odds', 'wo_ci')
    return {k: cs.get(k) for k in keys}


# ---------------------------------------------------------------- (c) components

def component_effects(episodes, design, cfg):
    out = {}
    eA = [e for e in episodes if e['arm'] == A]; eB = [e for e in episodes if e['arm'] == B]

    def val(e, c):
        return float(bool(e[c])) if c == 'success' else (float(e[c]) if e[c] is not None else np.nan)

    def per_task(eps, comp):
        d = {}
        for e in eps:
            d.setdefault(e['task_id'], []).append(val(e, comp))
        return {k: float(np.nanmean(v)) for k, v in d.items() if np.isfinite(np.nanmean(v))}
    out['same_task_paired'] = {}
    for c in COMPONENTS:
        ta, tb = per_task(eA, c), per_task(eB, c); common = sorted(set(ta) & set(tb))
        if len(common) >= 2:
            diff = np.array([tb[t] - ta[t] for t in common])
            r = t_ci(diff, cfg['alpha']); r.update(mean_A=float(np.mean([ta[t] for t in common])), mean_B=float(np.mean([tb[t] for t in common])))
            if c != 'success':
                r['median_A'] = float(np.median([ta[t] for t in common])); r['median_B'] = float(np.median([tb[t] for t in common]))
                r['ratio_of_means_B_over_A'] = float(r['mean_B'] / r['mean_A']) if r['mean_A'] > 0 else None
            out['same_task_paired'][c] = r
    idx, pA, pB, _ = completed_pairs(design, episodes)
    out['cross_arrival_independent'] = {}
    for c in COMPONENTS:
        xa = [val(e, c) for e in pA if np.isfinite(val(e, c))]; xb = [val(e, c) for e in pB if np.isfinite(val(e, c))]
        out['cross_arrival_independent'][c] = welch_ci(xa, xb, cfg['alpha'])
    out['failure_accounting'] = {}
    for arm, eps in ((A, eA), (B, eB)):
        terms = {}
        for e in eps:
            terms[e['termination_reason'] or 'none'] = terms.get(e['termination_reason'] or 'none', 0) + 1
        out['failure_accounting'][arm] = dict(n=len(eps), success=int(sum(bool(e['success']) for e in eps)), max_steps=int(sum(bool(e['max_steps_hit']) for e in eps)),
                                              errors=int(sum(e['error'] is not None for e in eps)), termination_reasons=terms,
                                              tokens_estimated_episodes=int(sum((e['tokens_estimated_calls'] or 0) > 0 for e in eps)),
                                              tokens_estimated_calls=int(sum(e['tokens_estimated_calls'] or 0 for e in eps)),
                                              zero_tool_call_episodes=int(sum((e['n_assistant_tool_calls'] or 0) == 0 for e in eps)),
                                              served_models=sorted({e['served_models'] for e in eps if e['served_models']}),
                                              duration_total_s=float(np.nansum([e['duration'] if e['duration'] is not None else np.nan for e in eps])) if eps else None)
    return out


# ---------------------------------------------------------------- (d) decision rules

def decision_rules(shadow, comps, online, cfg):
    """Rules applied to the same data (B = candidate agent vs A = incumbent agent); each returns B / A / none / tradeoff."""
    rows = []
    sp = comps.get('same_task_paired', {})

    def dec_from_ci(ci):
        lo, hi = ci
        if lo is None:
            return 'none'
        return 'B' if lo > 0 else ('A' if hi < 0 else 'none')
    if 'success' in sp:
        rows.append(dict(rule='success_only', data='shadow', estimate=sp['success']['mean'], ci=sp['success']['ci'], decision=dec_from_ci(sp['success']['ci'])))
    if all(k in sp for k in ('success', 'agent_tokens_completion', 'n_assistant_tool_calls')):
        ds, dt, dc = sp['success']['mean'], sp['agent_tokens_completion']['mean'], sp['n_assistant_tool_calls']['mean']
        b_no_worse = ds >= 0 and dt <= 0 and dc <= 0; a_no_worse = ds <= 0 and dt >= 0 and dc >= 0
        par = 'B' if b_no_worse and (ds > 0 or dt < 0 or dc < 0) else ('A' if a_no_worse and (ds < 0 or dt > 0 or dc > 0) else 'tradeoff')
        rows.append(dict(rule='pareto_means', data='shadow', estimate=None, ci=(None, None), decision=par, detail='d_success=%.4f d_tokens=%.1f d_calls=%.2f' % (ds, dt, dc)))
        rt = dt / sp['agent_tokens_completion']['mean_A'] if sp['agent_tokens_completion']['mean_A'] else 0.0
        rc = dc / sp['n_assistant_tool_calls']['mean_A'] if sp['n_assistant_tool_calls']['mean_A'] else 0.0
        for w in UTILITY_GRID:
            u = w[0] * ds - w[1] * rt - w[2] * rc
            rows.append(dict(rule='utility_w=%.2f/%.2f/%.2f' % w, data='shadow', estimate=float(u), ci=(None, None), decision='B' if u > 0 else ('A' if u < 0 else 'none'),
                             detail='u = w1*d_success - w2*rel_d_tokens - w3*rel_d_calls (point estimate only)'))
    if shadow.get('nb_ci'):
        rows.append(dict(rule='hierarchical_nb', data='shadow', estimate=shadow['net_benefit'], ci=shadow['nb_ci'], decision=dec_from_ci(shadow['nb_ci'])))
        if 'success' in sp:
            g = shadow['nb_ci'][0] > 0 and sp['success']['ci'][0] is not None and sp['success']['ci'][0] > -cfg['success_margin']
            rows.append(dict(rule='guarded_hierarchical', data='shadow', estimate=shadow['net_benefit'], ci=shadow['nb_ci'], decision='B' if g else ('A' if shadow['nb_ci'][1] < 0 else 'none'),
                             detail='NB CI > 0 and success CI lower > -%.2f' % cfg['success_margin']))
    if all(k in sp for k in ('success', 'agent_tokens_completion', 'n_assistant_tool_calls')) and sp['success']['ci'][0] is not None:
        c = sp['success']['ci'][0] > -cfg['success_margin'] and sp['agent_tokens_completion']['ci'][1] < 0 and sp['n_assistant_tool_calls']['ci'][1] < 0
        rows.append(dict(rule='conjunction_all_components', data='shadow', estimate=None, ci=(None, None), decision='B' if c else 'none', detail='success non-inferior AND tokens lower AND calls lower (all CIs)'))
    if online.get('nb_cs'):
        rows.append(dict(rule='hierarchical_nb_betting_cs', data='online', estimate=online['net_benefit'], ci=online['nb_cs'], decision=dec_from_ci(online['nb_cs'])))
        rows.append(dict(rule='guarded_anytime', data='online', estimate=online['net_benefit'], ci=online['nb_cs'], decision={'deploy_B': 'B', 'B_harmful': 'A', 'inconclusive': 'none'}[online['guarded_decision']],
                         detail='first_deploy=%s first_harm=%s' % (online['monitoring']['first_deploy'], online['monitoring']['first_harm'])))
        rows.append(dict(rule='success_only_betting_cs', data='online', estimate=online['success_diff_hat'], ci=online['success_diff_cs'], decision=dec_from_ci(online['success_diff_cs'])))
    return rows


# ---------------------------------------------------------------- (e) sensitivity

SENSITIVITY_ORDERS = [
    # (order, absorbing, label)
    (['success', 'agent_tokens_completion', 'n_assistant_tool_calls'], True, 'primary order, absorbing'),
    (['success', 'n_assistant_tool_calls', 'agent_tokens_completion'], True, 'steps before tokens, absorbing'),
    (['success', 'duration', 'agent_tokens_completion'], True, 'duration as tier 2, absorbing'),
    (['success', 'agent_tokens_completion', 'n_assistant_tool_calls'], False, 'lexicographic, non-absorbing (failures ranked by cost)'),
    (['agent_tokens_completion', 'success', 'n_assistant_tool_calls'], False, 'token-first (H4), no eligibility mask'),
]
TOLERANCES = (0.0, 0.05, 0.10, 0.20)


def sensitivity(design, episodes, cfg):
    rows = []
    for tol in TOLERANCES:
        for order, absorbing, label in SENSITIVITY_ORDERS:
            tiers = tiers_from_config(cfg, tolerance=tol, order=order)
            sh = shadow_analysis(episodes, cfg, tiers, absorbing=absorbing)
            on = online_analysis(design, episodes, cfg, tiers, absorbing=absorbing)
            rows.append(dict(tolerance=tol, order='>'.join(order), eligibility='absorbing' if absorbing else 'none', label=label,
                             shadow_nb=sh.get('net_benefit'), shadow_nb_lo=(sh.get('nb_ci') or (None, None))[0], shadow_nb_hi=(sh.get('nb_ci') or (None, None))[1],
                             shadow_decision=sh.get('decision_hierarchical'), online_nb=on.get('net_benefit'), online_nb_lo=(on.get('nb_cs') or (None, None))[0],
                             online_nb_hi=(on.get('nb_cs') or (None, None))[1], online_guarded=on.get('guarded_decision'), online_first_deploy=(on.get('monitoring') or {}).get('first_deploy'),
                             online_first_harm=(on.get('monitoring') or {}).get('first_harm')))
    return rows


def pairing_sensitivity(episodes, cfg):
    return {p: {k: v for k, v in shadow_analysis(episodes, cfg, pairing=p).items() if k != 'task_scores'} for p in ('all', 'offdiagonal', 'diagonal')}


# ---------------------------------------------------------------- report

def _f(x):
    return 'NA' if x is None else ('%.4f' % x if isinstance(x, float) else str(x))


def _ci(ci):
    return 'NA' if not ci or ci[0] is None else '[%.4f, %.4f]' % tuple(ci)


def report_md(summary, results_dir):
    o, s, c = summary['online'], summary['shadow'], summary['components']
    L = ['# tau2 open-model stream: analysis report (skeleton)', '']
    if summary.get('dry_run'):
        L += ['> **MOCK DATA - DRY RUN.** These numbers come from the deterministic mock generator in `run_tau2_open.py --dry-run`. They test the pipeline only and must never be copied into the paper.', '']
    arms = summary.get('arms') or {}
    L += ['Generated %s from `%s`. Scores are B (%s) vs A (%s); user simulator %s for both. Fill the interpretation after the frozen analysis; do not edit numbers by hand.' % (
        summary['generated_at'], results_dir, arms.get('B', 'arm B'), arms.get('A', 'arm A'), arms.get('user', 'user simulator')), '',
          '## Accounting', '', '- Episodes: %d; arms: %s; dry_run=%s' % (summary['n_episodes'], summary['n_per_arm'], summary['dry_run']),
          '- Failure accounting: %s' % json.dumps(c.get('failure_accounting', {})), '',
          '## (a) Online cross-arrival design (prespecified pass-1 pairs)', '',
          '- Pairs: %s; NB=%s, NB CS=%s; WR=%s, WR CS=%s' % (o.get('n_pairs'), _f(o.get('net_benefit')), o.get('nb_cs'), _f(o.get('win_ratio')), o.get('wr_cs')),
          '- Success diff (B-A) = %s, CS %s; guarded decision: %s; first deploy index: %s; first harm index: %s' % (
              _f(o.get('success_diff_hat')), o.get('success_diff_cs'), o.get('guarded_decision'), (o.get('monitoring') or {}).get('first_deploy'), (o.get('monitoring') or {}).get('first_harm')),
          '- Tier decomposition: %s' % json.dumps(o.get('tier_decomposition', {})),
          '- Tier decomposition: success tier determines the sign of NB (H3): %s' % o.get('success_tier_determines_sign'),
          '- Block-1 subset (pairs with both arrivals in block 1 = pairs 1-24, distinct tasks; %s pairs): NB=%s CS=%s guarded=%s' % (
              summary['online_block1'].get('n_pairs'), _f(summary['online_block1'].get('net_benefit')), summary['online_block1'].get('nb_cs'), summary['online_block1'].get('guarded_decision')), '',
          '## (b) Same-task shadow design', '',
          '- Tasks: %s; NB=%s CI=%s; WR=%s CI=%s; decision: %s; replicate-identical fraction: %s' % (s.get('n_tasks'), _f(s.get('net_benefit')), s.get('nb_ci'), _f(s.get('win_ratio')), s.get('wr_ci'), s.get('decision_hierarchical'), s.get('replicate_identical_fraction')),
          '- Pairing sensitivity (NB, CI): %s' % json.dumps({k: (round(v.get('net_benefit'), 4) if v.get('net_benefit') is not None else None, v.get('nb_ci')) for k, v in summary['shadow_pairing'].items()}), '',
          '## (c) Component effects (B - A)', '', '| component | same-task mean diff | CI | cross-arrival diff | CI |', '|---|---|---|---|---|']
    for comp in COMPONENTS:
        a = c.get('same_task_paired', {}).get(comp, {}); b = c.get('cross_arrival_independent', {}).get(comp, {})
        L.append('| %s | %s | %s | %s | %s |' % (comp, _f(a.get('mean')), _ci(a.get('ci')), _f(b.get('diff')), _ci(b.get('ci'))))
    L += ['', '## (d) Decision rules', '', '| rule | data | estimate | CI | decision |', '|---|---|---|---|---|']
    for r in summary['decision_rules']:
        L.append('| %s | %s | %s | %s | %s |' % (r['rule'], r['data'], _f(r['estimate']), _ci(r['ci']), r['decision']))
    L += ['', '## (e) Sensitivity (tolerance x tier order; H4 = token-first row with eligibility "none")', '',
          '| tol | order | eligibility | shadow NB [CI] | shadow dec | online NB [CS] | online guarded |', '|---|---|---|---|---|---|---|']
    for r in summary['sensitivity']:
        L.append('| %s | %s | %s | %s [%s, %s] | %s | %s [%s, %s] | %s |' % (r['tolerance'], r['order'], r['eligibility'], _f(r['shadow_nb']), _f(r['shadow_nb_lo']), _f(r['shadow_nb_hi']), r['shadow_decision'],
                                                                        _f(r['online_nb']), _f(r['online_nb_lo']), _f(r['online_nb_hi']), r['online_guarded']))
    L += ['', '## Hypotheses (protocol.md section 1)', '', '| hypothesis | pre-specified test | result |', '|---|---|---|',
          '| H1 success differs between arms (direction NOT pre-specified; deployment question: can candidate B replace incumbent A under the guarded rule?) | same-task success diff (B-A) CI excludes 0; guarded decision | CI %s; guarded %s |' % (
              _ci(c.get('same_task_paired', {}).get('success', {}).get('ci')), o.get('guarded_decision')),
          '| H2 B uses fewer agent completion tokens per episode | same-task token diff (B-A) CI < 0 | %s |' % _ci(c.get('same_task_paired', {}).get('agent_tokens_completion', {}).get('ci')),
          '| H3 the hierarchical decision is determined by success first | success-tier contribution has the sign of NB and dominates lower tiers (shadow, online) | shadow %s; online %s |' % (
              s.get('success_tier_determines_sign'), o.get('success_tier_determines_sign')),
          '| H4 a token-first rule prefers B if H2 holds | sensitivity row tokens>success>calls (eligibility none) NB > 0 with CI/CS lower bound > 0 | see (e) |',
          '| H5 absolute success levels not comparable to the paper\'s archived commercial-model runs (weaker user simulator) | success rates reported per arm, never compared with archived levels | %s |' % json.dumps({k: v.get('success') for k, v in c.get('failure_accounting', {}).items()}),
          '', '## Interpretation (to be written after unblinding; protocol.md section 12)', '', '_pending_', '', '## Deviations from protocol', '', '_none recorded yet; see protocol.md deviations log_', '']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    ap.add_argument('--config', default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config); rd = Path(args.results_dir)
    design = load_design(rd)
    episodes = load_episodes(rd / 'episodes.csv')
    if not episodes:
        raise SystemExit('no episodes in %s' % rd)
    bad = [e for e in episodes if e.get('config_hash') not in (None, cfg['_config_hash'])]
    if bad:
        raise SystemExit('%d episodes carry a config hash different from the loaded config' % len(bad))
    manifest = json.loads((rd / 'run_manifest.json').read_text()) if (rd / 'run_manifest.json').exists() else {}
    invs = manifest.get('invocations') or []
    dry = any(i.get('dry_run') for i in invs)
    for arm in (A, B):
        p = rd / 'raw' / ('tau2_open_arm%s.json' % arm)
        if p.exists():
            try:
                dry = dry or bool((json.loads(p.read_text()).get('info') or {}).get('mock'))
            except Exception:
                pass
    monitor_state = write_monitor(rd, design, episodes, cfg)
    online = online_analysis(design, episodes, cfg)
    online_b1 = online_analysis(design, episodes, cfg, blocks_keep={1})
    shadow = shadow_analysis(episodes, cfg)
    comps = component_effects(episodes, design, cfg)
    rules = _clean(decision_rules(shadow, comps, online, cfg))
    sens = _clean(sensitivity(design, episodes, cfg))
    pairing = _clean(pairing_sensitivity(episodes, cfg))
    n_per_arm = {arm: sum(e['arm'] == arm for e in episodes) for arm in (A, B)}
    summary = dict(generated_at=iso(now_ts()), results_dir=str(rd), n_episodes=len(episodes), n_per_arm=n_per_arm, dry_run=bool(dry), config_hash=cfg['_config_hash'],
                   arms=dict(A='agent %s' % cfg['arms']['A']['alias'], B='agent %s' % cfg['arms']['B']['alias'], user=cfg['user_alias']),
                   design_sha256=(rd / 'design.sha256').read_text().split()[0], n_invocations=len(invs), monitor_state=monitor_state, online=online, online_block1=online_b1,
                   shadow={k: v for k, v in shadow.items() if k != 'task_scores'}, shadow_pairing=pairing, components=comps, decision_rules=rules, sensitivity=sens)
    summary = _clean(summary)
    (rd / 'summary.json').write_text(json.dumps(summary, indent=2))
    pd.DataFrame(rules).to_csv(rd / 'decision_rules.csv', index=False)
    pd.DataFrame(sens).to_csv(rd / 'sensitivity.csv', index=False)
    if shadow.get('task_scores'):
        ts = shadow['task_scores']
        pd.DataFrame(dict(task_id=ts['tasks'], win=ts['win'], loss=ts['loss'], tie=ts['tie'])).to_csv(rd / 'task_scores.csv', index=False)
    (rd / 'report.md').write_text(report_md(summary, rd))
    print(json.dumps(dict(online={k: online.get(k) for k in ('n_pairs', 'net_benefit', 'nb_cs', 'guarded_decision')},
                          shadow={k: shadow.get(k) for k in ('n_tasks', 'net_benefit', 'nb_ci', 'decision_hierarchical')}), indent=2, default=str))


if __name__ == '__main__':
    main()
