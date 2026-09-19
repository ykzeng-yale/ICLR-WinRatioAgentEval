"""Round 9 re-analysis of the completed local stream (POST HOC; see protocol_addendum_round9.md).

analysis.py is the frozen, preregistered analysis and is NOT edited; this file imports its functions and
re-runs them from the unchanged raw evidence (episodes.jsonl, design.json, monitor_pass1.csv) with

  * the corrected two-sided betting CS of src/wincs.py (hedged capital (K+ + K-)/2 against 1/delta), and
  * two explicitly separated inferential readings of the cross-arrival contrast E1:
      R1 design-based, conditional on the realized pairing: Hoeffding-type normal-mixture CS
         (src/winstats.normal_mixture_radius, V_n = n, rho = 100, two-sided alpha) for the RUNNING AVERAGE
         mu_bar_n of the pair means; no iid / stationarity / sampling assumption;
      R2 superpopulation model (ASSUMPTION: roster = iid sample of tasks): corrected betting CS, decided-pair
         win-ratio CS and the preregistered one-sided e-processes, for the fixed mean theta_P.
  * E2 finite-roster reading (Neyman-conservative task-level variance) next to the superpopulation reading,
    plus an assumption-free fixed-n Hoeffding interval;
  * pair-level (not independent-arm Welch) component intervals for pass 1;
  * resource accounting per arm (prompt / completion / total tokens, model calls, latency).

No model call, no git command, raw evidence is only read. Writes (results dir): summary_v2.json,
decision_rules_v2.csv, sensitivity_v2.csv, running_cs_v2.csv, resources_v2.csv. It also re-derives
task_scores.csv and episodes_flat.csv in memory and asserts they equal the preserved v1 files (they do not
depend on the CS), instead of rewriting them.

Usage: .venv/bin/python experiments/local_stream/analysis_v2.py [--results-dir results/local_stream]
"""
from __future__ import annotations
import argparse, hashlib, io, json, math, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analysis as v1  # frozen analysis functions (they now resolve to the corrected src/wincs.py)  # noqa: E402
from common import RESULTS_DIR, load_config, read_jsonl, iso, now_ts  # noqa: E402
from design import load_design  # noqa: E402
from run_stream import A, B, completed_pairs, pair_scores, tiers_from_config, monitor_table, first_index  # noqa: E402
from winstats import normal_mixture_radius  # noqa: E402
from wincs import betting_cs_ternary, win_ratio_cs_decided  # noqa: E402

RHO = 100.0  # as in the paper's src/winstats.normal_mixture_radius default; fixed here before computing anything
HARM_LABEL = 'composite harm signal for B; incumbent A retained'
LABELS = {'B_harmful': HARM_LABEL, 'deploy_B': 'guarded approval of B', 'inconclusive': 'inconclusive'}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def first_true(n, mask):
    mask = np.asarray(mask, bool)
    return int(n[np.argmax(mask)]) if mask.any() else None


def running_cs(z, dq, cfg):
    """Per-n running estimates with the R1 normal-mixture CS and the R2 corrected betting CS."""
    z = np.asarray(z); dq = np.asarray(dq); n = np.arange(1, len(z) + 1)
    alpha = cfg['alpha']
    pos, neg = np.cumsum(z > 0), np.cumsum(z < 0); qp, qn = np.cumsum(dq > 0), np.cumsum(dq < 0)
    nb = (pos - neg) / n; sd = (qp - qn) / n
    rad = normal_mixture_radius(n, alpha, RHO)                                   # V_n = n: predictable range 2 -> r^2/4 = 1 per pair
    blo, bhi = betting_cs_ternary(pos, n - pos - neg, neg, alpha)
    glo, ghi = betting_cs_ternary(qp, n - qp - qn, qn, alpha)
    wlo, whi = win_ratio_cs_decided(pos, neg, alpha)
    df = pd.DataFrame(dict(n=n, nb_hat=nb, r1_radius=rad, r1_nb_lo=np.maximum(nb - rad, -1), r1_nb_hi=np.minimum(nb + rad, 1),
                           r2_nb_lo=blo, r2_nb_hi=bhi, succ_diff_hat=sd, r1_sd_lo=np.maximum(sd - rad, -1), r1_sd_hi=np.minimum(sd + rad, 1),
                           r2_sd_lo=glo, r2_sd_hi=ghi, r2_wr_lo=wlo, r2_wr_hi=whi))
    return df


def e1_v2(design, episodes, cfg, online):
    idx, eA, eB = completed_pairs(design, episodes, 1)
    z, tier, dq = pair_scores(eA, eB, tiers_from_config(cfg))
    df = running_cs(z, dq, cfg); n = df['n'].values; N = len(z); last = df.iloc[-1]
    margin = cfg['success_margin']; min_n = cfg['min_n_pairs']
    # consistency with the raw monitor file (raw evidence, read only)
    mon = pd.read_csv(Path(cfg['_results_dir']) / 'monitor_pass1.csv')
    assert len(mon) == N and (mon['z'].values == z).all() and (mon['success_diff'].values == dq).all(), 'monitor_pass1.csv disagrees with reconstructed scores'
    rows = monitor_table(z, dq, cfg)
    assert np.allclose([r['log_e_harm'] for r in rows], mon['log_e_harm'].values, atol=1e-9)
    thr = math.log(1 / cfg['alpha'])
    pre = mon[(mon['n'] < min_n) & (mon['log_e_harm'] >= thr)]
    r1 = dict(
        reading='R1 design-based, conditional on the realized pairing; target = running average mu_bar_n of the pair means; no sampling assumption',
        method='normal-mixture (Hoeffding-type sub-Gaussian) CS, V_n = n, rho = %g, two-sided alpha = %g; NO running intersection (the target moves with n)' % (RHO, cfg['alpha']),
        n=N, radius_at_n=float(last['r1_radius']),
        nb_hat=float(last['nb_hat']), nb_cs=(float(last['r1_nb_lo']), float(last['r1_nb_hi'])),
        first_n_nb_upper_below_0=first_true(n, df['r1_nb_hi'].values < 0),
        first_n_nb_upper_below_0_at_or_after_min_n=first_true(n, (df['r1_nb_hi'].values < 0) & (n >= min_n)),
        stays_below_0_from=_stays_from(n, df['r1_nb_hi'].values < 0),
        success_diff_hat=float(last['succ_diff_hat']), success_diff_cs=(float(last['r1_sd_lo']), float(last['r1_sd_hi'])),
        first_n_success_lower_above_minus_margin=first_true(n, df['r1_sd_lo'].values > -margin),
        first_n_success_upper_below_0=first_true(n, df['r1_sd_hi'].values < 0),
        gate_threshold=-margin,
        gate_status='not established: lower bound %.4f <= -%.2f at n = %d' % (last['r1_sd_lo'], margin, N) if last['r1_sd_lo'] <= -margin else 'established')
    r2 = dict(
        reading='R2 superpopulation model (ASSUMPTION: the 591-task roster is an iid sample from a task distribution P); target = theta_P',
        method='corrected hedged betting CS (src/wincs.py, (K+ + K-)/2 vs 1/delta), decided-pair win-ratio CS, preregistered one-sided e-processes',
        n=N, nb_hat=float(last['nb_hat']), nb_cs=(float(last['r2_nb_lo']), float(last['r2_nb_hi'])),
        first_n_nb_upper_below_0=first_true(n, df['r2_nb_hi'].values < 0),
        stays_below_0_from=_stays_from(n, df['r2_nb_hi'].values < 0),
        wr_hat=online.get('win_ratio'), wr_cs=(float(last['r2_wr_lo']), float(last['r2_wr_hi'])),
        success_diff_hat=float(last['succ_diff_hat']), success_diff_cs=(float(last['r2_sd_lo']), float(last['r2_sd_hi'])),
        first_n_success_lower_above_minus_margin=first_true(n, df['r2_sd_lo'].values > -margin),
        gate_threshold=-margin)
    monitor = dict(
        first_win_cross=first_index(rows, 'win_cross'), first_gate_cross=first_index(rows, 'gate_cross'), first_deploy=first_index(rows, 'deploy'),
        first_harm=first_index(rows, 'harm'), log_e_harm_at_first_harm=(float(mon.loc[mon['n'] == first_index(rows, 'harm'), 'log_e_harm'].iloc[0]) if first_index(rows, 'harm') else None),
        harm_above_threshold_before_min_n=(dict(n=int(pre['n'].iloc[0]), log_e=float(pre['log_e_harm'].iloc[0])) if len(pre) else None),
        final_log_e=dict(win=rows[-1]['log_e_win'], gate=rows[-1]['log_e_gate'], harm=rows[-1]['log_e_harm']),
        max_log_e=dict(win=float(mon['log_e_win'].max()), gate=float(mon['log_e_gate'].max()), harm=float(mon['log_e_harm'].max())),
        threshold=thr, unaffected_by_two_sided_fix=True,
        status_R1='DESCRIPTIVE. The one-sided e-processes test the pointwise conditional null (harm: mu_k >= 0 for EVERY realized pair k), '
                  'which is a stronger null than mu_bar_n >= 0 or theta_N >= 0; no guarantee about mu_bar_n or theta_N is claimed from a crossing.',
        status_R2='Under the iid-roster model E[Z_k | F_{k-1}] = theta_P, so the crossings have the stated anytime type-I guarantee at alpha for H0: theta_P >= 0 (harm), theta_P <= 0 (win), E[D] <= -margin (gate).',
        guarded_decision_code=online['guarded_decision'], guarded_decision_label=LABELS[online['guarded_decision']],
        label_note='Unfavourable result for B on the prespecified COMPOSITE (driven by the latency tier); not a success-rate or safety harm, and not a reverse guarded approval of A: A is retained as the incumbent.')
    return df, dict(R1=r1, R2=r2, monitor=monitor, scores=dict(wins=int((z > 0).sum()), ties=int((z == 0).sum()), losses=int((z < 0).sum())))


def _stays_from(n, mask):
    """Smallest n0 such that mask holds for every n >= n0 (None if it fails at the end)."""
    mask = np.asarray(mask, bool)
    if not mask[-1]:
        return None
    bad = np.where(~mask)[0]
    return int(n[bad[-1] + 1]) if len(bad) else int(n[0])


def pair_level_components(design, episodes, cfg):
    """Pass-1 component contrasts from PAIR-LEVEL differences d_k = X_B,k - X_A,k (replaces the independent-arm Welch wording).

    R1: conditional on the pairing the d_k are independent, not identically distributed; the t interval on d_k is
    (asymptotically) conservative for the average of their means (Neyman-type). R2: iid pair differences.
    """
    idx, pA, pB = completed_pairs(design, episodes, 1)
    out = {}
    for c in ('success', 'latency_s', 'completion_tokens', 'prompt_tokens', 'n_llm_calls', 'n_executions'):
        f = (lambda e: float(bool(e[c]))) if c == 'success' else (lambda e: float(e[c]))
        xa = np.array([f(e) for e in pA]); xb = np.array([f(e) for e in pB])
        r = v1.t_ci(xb - xa, cfg['alpha']); r.update(mean_A=float(xa.mean()), mean_B=float(xb.mean()))
        out[c] = r
    return out


def e2_v2(episodes, cfg, shadow, comps):
    """Finite-roster and superpopulation readings of E2, plus an assumption-free Hoeffding interval."""
    ts = shadow['task_scores']; s = np.array(ts['win']) - np.array(ts['loss']); N = s.size
    h = math.sqrt(2 * math.log(2 / cfg['alpha']) / N)          # range 2: P(|mean - E mean| >= t) <= 2 exp(-N t^2 / 2)
    succ = comps['same_task_paired']['success']; margin = cfg['success_margin']
    byA = {e['task_id']: bool(e['success']) for e in episodes if e['variant'] == A}; byB = {e['task_id']: bool(e['success']) for e in episodes if e['variant'] == B}
    d = np.array([float(byB[t]) - float(byA[t]) for t in ts['tasks']])
    return dict(
        n_tasks=int(N), nb_hat=float(s.mean()), task_level_sd=float(s.std(ddof=1)),
        finite_roster=dict(target='theta_roster = (1/N) sum_t E h(Y_B(t), Y_A(t)) over the N = 591 roster tasks; randomness = model sampling only',
                           interval_t=tuple(shadow['nb_ci']), interval_status='conservative (Neyman-type): E[s^2/N] = Var(mean) + (1/(N(N-1))) sum_t (tau_t - tau_bar)^2 >= Var(mean); normal approximation',
                           interval_hoeffding=(max(-1.0, float(s.mean() - h)), min(1.0, float(s.mean() + h))), hoeffding_radius=h,
                           hoeffding_status='exact finite-sample, independent task scores in [-1,1], no normal approximation, fixed n (not time-uniform)'),
        superpopulation=dict(target='theta_task,P = E_{t~P} E h(Y_B(t), Y_A(t))', interval_t=tuple(shadow['nb_ci']), interval_status='conventional task-clustered t interval (one cluster = one task)'),
        success_difference=dict(hat=float(d.mean()), b_only=int((d > 0).sum()), a_only=int((d < 0).sum()), interval_t=tuple(succ['ci']),
                                margin=-margin, slack_above_margin=float(succ['ci'][0] + margin),
                                interval_hoeffding=(float(d.mean() - h), float(d.mean() + h)),
                                robust_noninferiority=False,
                                note='lower end clears the margin by %.6f under the t approximation only; the Hoeffding interval reaches %.3f. NOT a robust non-inferiority result.' % (succ['ci'][0] + margin, d.mean() - h)))


def resources(episodes):
    rows = []
    for v, letter in ((A, 'A'), (B, 'B')):
        eps = [e for e in episodes if e['variant'] == v]
        pt = sum(int(e['prompt_tokens']) for e in eps); ct = sum(int(e['completion_tokens']) for e in eps)
        calls = sum(int(e['n_llm_calls']) for e in eps); lat = np.array([float(e['latency_s']) for e in eps])
        rows.append(dict(arm=letter, variant=v, episodes=len(eps), successes=int(sum(bool(e['success']) for e in eps)), model_calls=calls,
                         call_records=int(sum(len(e.get('llm_call_seconds') or []) for e in eps)),
                         prompt_tokens=pt, completion_tokens=ct, total_tokens=pt + ct, tokens_estimated_episodes=int(sum(bool(e.get('tokens_estimated')) for e in eps)),
                         latency_sum_s=float(lat.sum()), latency_mean_s=float(lat.mean()), latency_median_s=float(np.median(lat)),
                         n_executions_incl_hidden_verifier=int(sum(int(e['n_executions']) for e in eps)),
                         agent_self_test_executions=int(sum(int(e['n_executions']) - 1 for e in eps)),
                         verify_seconds_sum=float(sum(float(e.get('verify_seconds') or 0) for e in eps))))
    a, b = rows
    ratios = {k: (b[k] / a[k] if a[k] else None) for k in ('model_calls', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'latency_mean_s')}
    return rows, ratios


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    args = ap.parse_args(argv)
    rd = Path(args.results_dir); cfg = load_config(None); cfg['_results_dir'] = str(rd)
    from data import load_tasks
    tasks_by_uid = {t['uid']: t for t in load_tasks()}
    design = load_design(rd, 1); episodes = read_jsonl(rd / 'episodes.jsonl')
    assert len(episodes) == 1182 or 'dryrun' in str(rd), len(episodes)

    online = v1.online_analysis(design, episodes, cfg, 1)          # corrected wincs via import
    shadow = v1.shadow_analysis(episodes, cfg, tasks_by_uid)
    comps = v1.component_effects(episodes, design, cfg, 1)
    comps['cross_arrival_pair_level'] = pair_level_components(design, episodes, cfg)
    comps['cross_arrival_independent_NOTE'] = 'v1 Welch independent-arm intervals kept for traceability only; superseded by cross_arrival_pair_level (Round 9)'
    running, e1 = e1_v2(design, episodes, cfg, online)
    e2 = e2_v2(episodes, cfg, shadow, comps)
    res_rows, res_ratios = resources(episodes)

    # decision rules: frozen rule code, corrected CS, relabelled guarded outcome; plus the R1 row
    rules = v1._clean(v1.decision_rules(shadow, comps, online, cfg))
    for r in rules:
        r['reading'] = 'E2 (finite-roster conservative / superpopulation)' if r['data'] == 'shadow' else 'R2 (iid-roster assumption)'
        if r['rule'] == 'guarded_anytime':
            r['decision'] = 'retain A' if online['guarded_decision'] == 'B_harmful' else r['decision']
            r['detail'] = (r.get('detail') or '') + '; label: ' + LABELS[online['guarded_decision']] + ' (not a reverse guarded approval of A; descriptive under R1)'
    r1 = e1['R1']
    rules.append(dict(rule='hierarchical_nb_normal_mixture_cs', data='online', estimate=r1['nb_hat'], ci=list(r1['nb_cs']),
                      decision='A' if r1['nb_cs'][1] < 0 else ('B' if r1['nb_cs'][0] > 0 else 'none'), reading='R1 (design-based, running average mu_bar_n)',
                      detail='POST HOC (Round 9); first n with upper bound < 0: %s' % r1['first_n_nb_upper_below_0']))
    rules.append(dict(rule='success_only_normal_mixture_cs', data='online', estimate=r1['success_diff_hat'], ci=list(r1['success_diff_cs']),
                      decision='none' if r1['success_diff_cs'][0] <= 0 <= r1['success_diff_cs'][1] else ('B' if r1['success_diff_cs'][0] > 0 else 'A'),
                      reading='R1 (design-based, running average)', detail='POST HOC (Round 9)'))
    sens = v1._clean(v1.sensitivity(design, episodes, cfg, tasks_by_uid, 1))
    for r in sens:
        r['online_guarded_label'] = LABELS.get(r['online_guarded'], r['online_guarded'])

    # old (v1) numbers for the old-vs-new table
    v1dir = rd / 'v1_pre_round9'; old = json.loads((v1dir / 'summary.json').read_text())['online'] if (v1dir / 'summary.json').exists() else {}
    old_new = {k: dict(v1_uncorrected=old.get(k), v2_corrected_R2=list(online[k]) if online.get(k) else None) for k in ('nb_cs', 'success_diff_cs', 'wr_cs')}
    old_new['nb_cs']['v2_R1_normal_mixture'] = list(r1['nb_cs']); old_new['success_diff_cs']['v2_R1_normal_mixture'] = list(r1['success_diff_cs'])
    # CS-independent outputs must be unchanged
    unchanged = {}
    if shadow.get('task_scores') and (v1dir / 'task_scores.csv').exists():
        ts = shadow['task_scores']; buf = io.StringIO()
        pd.DataFrame(dict(task_id=ts['tasks'], benchmark=[tasks_by_uid[t]['benchmark'] for t in ts['tasks']], win=ts['win'], loss=ts['loss'], tie=ts['tie'])).to_csv(buf, index=False)
        unchanged['task_scores.csv'] = hashlib.sha256(buf.getvalue().encode()).hexdigest() == sha256_file(v1dir / 'task_scores.csv')
        assert unchanged['task_scores.csv'], 'task_scores.csv would change; it must not depend on the CS'
    for k in ('net_benefit', 'win_ratio', 'p_win', 'p_loss', 'p_tie', 'success_diff_hat', 'tier_decomposition', 'monitoring'):
        assert v1._clean(online[k]) == old.get(k, v1._clean(online[k])), 'point estimate %s changed' % k
    e1_e2 = dict(e1_nb=online['net_benefit'], e2_nb=shadow['net_benefit'], difference_e1_minus_e2=online['net_benefit'] - shadow['net_benefit'],
                 status='DESCRIPTIVE ONLY: different targets, shared episodes (pass-1 episodes enter both), different unit counts and exposure passes; no joint uncertainty is claimed for the difference.')

    summary = v1._clean(dict(
        generated_at=iso(now_ts()), analysis='analysis_v2.py (POST HOC Round 9 re-analysis; analysis.py remains the frozen original)',
        results_dir='<REPO>/results/local_stream', n_episodes=len(episodes), config_hash=cfg['_config_hash'],
        inputs_sha256={f: sha256_file(rd / f) for f in ('episodes.jsonl', 'monitor_pass1.csv', 'monitor_state.json', 'design.json', 'run_manifest.json')},
        wincs_sha256=sha256_file(HERE.parents[1] / 'src' / 'wincs.py'),
        online=online, online_label=LABELS[online['guarded_decision']], e1=e1, shadow={k: v for k, v in shadow.items() if k != 'task_scores'}, e2=e2,
        components=comps, resources=dict(per_arm=res_rows, ratio_B_over_A=res_ratios,
                                         totals=dict(model_calls=sum(r['model_calls'] for r in res_rows), prompt_tokens=sum(r['prompt_tokens'] for r in res_rows),
                                                     completion_tokens=sum(r['completion_tokens'] for r in res_rows), total_tokens=sum(r['total_tokens'] for r in res_rows)),
                                         note='completion tokens are generation counts, not dollars, energy or total compute; prompt tokens are reported because B uses far more of them; '
                                              'n_executions includes the one hidden-verifier execution per episode, which latency_s excludes'),
        old_vs_new_intervals=old_new, e1_vs_e2=e1_e2, cs_independent_outputs_unchanged=unchanged, decision_rules=rules, sensitivity=sens))
    (rd / 'summary_v2.json').write_text(json.dumps(summary, indent=2))
    pd.DataFrame(rules).to_csv(rd / 'decision_rules_v2.csv', index=False)
    pd.DataFrame(sens).to_csv(rd / 'sensitivity_v2.csv', index=False)
    running.to_csv(rd / 'running_cs_v2.csv', index=False)
    pd.DataFrame(res_rows).to_csv(rd / 'resources_v2.csv', index=False)
    print(json.dumps(dict(old_vs_new=old_new, R1=dict(nb_cs=r1['nb_cs'], first_excl=r1['first_n_nb_upper_below_0'], sd_cs=r1['success_diff_cs']),
                          R2=dict(nb_cs=e1['R2']['nb_cs'], first_excl=e1['R2']['first_n_nb_upper_below_0'], wr_cs=e1['R2']['wr_cs'], sd_cs=e1['R2']['success_diff_cs']),
                          e2_success=e2['success_difference'], resources=res_rows), indent=1, default=str))


if __name__ == '__main__':
    main()
