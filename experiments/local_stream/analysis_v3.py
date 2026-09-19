"""Round 10 re-analysis of the completed local stream (POST HOC; see protocol_addendum_round10.md).

analysis.py (frozen, preregistered) and analysis_v2.py (Round 9) are NOT edited; this file imports them and re-reads
the unchanged raw evidence (episodes.jsonl, design.json). It responds to the Round 10 audit of PR 8:

  * E2 same-task uncertainty (findings 1-2). The task-level t interval and the task-level Hoeffding interval are
    kept but labelled MODEL-BASED: they need independent task scores with stable task-specific episode laws and no
    relevant pass/period effects (the t interval additionally a Lindeberg / variance-growth regularity condition).
    Neither is a consequence of the two-pass AB/BA design, in which the two tasks of a design pair share one
    orientation coin and complementary pass positions.
  * ORIENTATION-PAIR CLUSTER analysis. Clusters = the 295 design pairs of design.json + the singleton unpaired task
    (G = 296). Target = assignment-averaged same-task preference over the roster. Estimator = total score / 591.
    (a) cluster-robust linearization variance  G/(G-1) * sum_g e_g^2 / 591^2,  e_g = T_g - n_g * NB_hat, with a
        t reference on G-1 df (APPROXIMATE);
    (b) exact range-based final-time Hoeffding bound under INDEPENDENT CLUSTERS,
        radius sqrt(2 * (4*295 + 1) * log(2/alpha)) / 591   (= 0.15794 at alpha = 0.05).
    The same two intervals are given for the same-task success difference. Independent clusters is still an
    assumption (shared machine state across clusters is not excluded by the design).
  * A DESCRIPTIVE pass/period table: per variant, success rate, mean latency and mean completion tokens in pass 1
    versus pass 2 with simple differences. No inference is claimed (the two pass groups of a variant are different
    tasks, so the difference mixes task composition with any period effect).
  * R1 / R2 wording: running-conditional-mean target under a stated filtration (R1); unconditional model-based
    inference over hypothetical iid rosters (R2). The E1 numbers are those of analysis_v2.py (summary_v2.json).

No model call, no git command, no execution of generated programs; raw evidence is only read.
Writes (results dir): summary_v3.json, decision_rules_v3.csv, e2_cluster_v3.csv, pass_effects_v3.csv.

Usage: .venv/bin/python experiments/local_stream/analysis_v3.py [--results-dir results/local_stream]
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analysis as v1  # frozen  # noqa: E402
import analysis_v2 as v2  # Round 9, unchanged  # noqa: E402
from common import RESULTS_DIR, load_config, read_jsonl, iso, now_ts  # noqa: E402
from design import load_design  # noqa: E402
from run_stream import A, B  # noqa: E402

E2_MODEL = ('MODEL-BASED: valid under independent task scores with stable task-specific episode laws and no relevant pass/period effects; '
            'NOT implied by the two-pass AB/BA design (the two tasks of a design pair share one orientation coin and complementary pass positions)')
E2_T_EXTRA = 'approximate: additionally needs a Lindeberg / variance-growth regularity condition (boundedness alone is not enough) and a well-behaved variance estimator'
CLUSTER_MODEL = ('valid under INDEPENDENT ORIENTATION-PAIR CLUSTERS (arbitrary dependence inside a design pair); independence ACROSS clusters is still an assumption: '
                 'shared machine state (thermal, cache, server history) across clusters is not excluded by the design')
R1_TARGET = ('running conditional mean (1/n) sum_{k<=n} mu_k, mu_k = E[Z_k | F_(k-1)], F_k = sigma(design information independent of future outcomes, revealed pair data up to k)')
R1_EXTRA = ('the reading mu_k = [m(s_k,t_k)+m(t_k,s_k)]/2 and E_design[mu_bar] = theta_N hold ONLY under an additional orientation-independent, history-independent stable '
            'episode-law model (thermal state, order and caching can affect latency); not assumed for the CS')
R2_MODEL = ('unconditional MODEL-BASED inference over hypothetical iid rosters with independent stable episode laws; F = past revealed pair data plus design information independent '
            'of future task values (NOT the entire realized roster); not a guarantee conditional on the curated benchmark')
COUNTEREXAMPLE = ('Two tasks forming one design pair; both workflows are identical within a task and period. Task 1 succeeds in pass 1 and fails in pass 2; task 2 fails in pass 1 '
                  'and succeeds in pass 2. Under one fair AB/BA orientation the two same-task success scores are (1, 1); under the other they are (-1, -1). Each task\'s mean score '
                  'is 0, but Var((S1+S2)/2) = 1 while s^2/2 = 0 in both realizations. No model noise is needed: positive covariance inside the orientation pair defeats the '
                  'variance identity; in general E[s^2/N] acquires the extra term -2 sum_{i<j} Cov(S_i,S_j) / (N(N-1)).')


def cluster_hoeffding_radius(n_pairs, n_single, n_tasks, alpha):
    """Exact final-time Hoeffding radius for (sum of independent cluster totals) / n_tasks.

    A pair total lies in [-2, 2] (range 4), a singleton in [-1, 1] (range 2):
    P(|sum - E sum| >= t) <= 2 exp(-2 t^2 / sum range^2), sum range^2 = 16 n_pairs + 4 n_single = 4 (4 n_pairs + n_single)."""
    return math.sqrt(2.0 * (4 * n_pairs + n_single) * math.log(2.0 / alpha)) / n_tasks


def cluster_table(design, task_ids, s, d, episodes):
    """One row per orientation-pair cluster (design pair; the unpaired arrival is its own cluster)."""
    sv = dict(zip(task_ids, s)); dv = dict(zip(task_ids, d))
    lat = {(e['task_id'], e['variant']): float(e['latency_s']) for e in episodes}
    groups = {}
    for a in design['arrivals']:
        key = ('pair', a['pair_index']) if a['pair_index'] is not None else ('single', a['arrival_index'])
        groups.setdefault(key, []).append(a)
    rows = []
    for (kind, idx), arr in sorted(groups.items(), key=lambda kv: min(x['arrival_index'] for x in kv[1])):
        arr = sorted(arr, key=lambda x: x['arrival_index'])
        assert (kind == 'pair' and len(arr) == 2 and {x['pass1_variant'] for x in arr} == {A, B} and len({x['orientation'] for x in arr}) == 1) or (kind == 'single' and len(arr) == 1), (kind, idx)
        rows.append(dict(cluster=('pair_%03d' % idx) if kind == 'pair' else 'unpaired_arrival_%d' % idx, kind=kind, n_tasks=len(arr),
                         orientation=arr[0]['orientation'], task_1=arr[0]['task_id'], task_2=arr[1]['task_id'] if len(arr) == 2 else '',
                         pass1_variant_task_1=arr[0]['pass1_variant'], pass1_variant_task_2=arr[1]['pass1_variant'] if len(arr) == 2 else '',
                         score_task_1=int(sv[arr[0]['task_id']]), score_task_2=int(sv[arr[1]['task_id']]) if len(arr) == 2 else '',
                         score_total=int(sum(sv[x['task_id']] for x in arr)),
                         success_diff_task_1=int(dv[arr[0]['task_id']]), success_diff_task_2=int(dv[arr[1]['task_id']]) if len(arr) == 2 else '',
                         success_diff_total=int(sum(dv[x['task_id']] for x in arr))))
    return pd.DataFrame(rows)


def cluster_inference(T, ng, alpha, n_pairs, n_single):
    """Ratio-type estimator total/N with the linearization (cluster totals) variance, plus the exact Hoeffding bound."""
    T = np.asarray(T, float); ng = np.asarray(ng, float); G = T.size; N = float(ng.sum())
    est = T.sum() / N; e = T - ng * est
    var = G / (G - 1.0) * float((e ** 2).sum()) / N ** 2; se = math.sqrt(var); q = float(stats.t.ppf(1 - alpha / 2, G - 1))
    h = cluster_hoeffding_radius(n_pairs, n_single, N, alpha)
    return dict(estimate=float(est), n_clusters=int(G), n_tasks=int(N), cluster_robust_se=se, t_df=int(G - 1), t_quantile=q,
                interval_cluster_t=(est - q * se, est + q * se), interval_cluster_t_status='APPROXIMATE (t reference on G-1 df); ' + CLUSTER_MODEL,
                hoeffding_cluster_radius=h, interval_cluster_hoeffding=(max(-1.0, est - h), min(1.0, est + h)),
                interval_cluster_hoeffding_status='exact finite-sample, final-time (not time-uniform), range-based; ' + CLUSTER_MODEL)


def e2_v3(design, episodes, cfg, shadow, comps):
    alpha = cfg['alpha']; margin = cfg['success_margin']
    ts = shadow['task_scores']; tasks = list(ts['tasks']); s = np.array(ts['win']) - np.array(ts['loss']); N = s.size
    assert set(np.unique(s)) <= {-1.0, 0.0, 1.0} or set(np.unique(s)) <= {-1, 0, 1}, 'one A and one B episode per task expected'
    byA = {e['task_id']: bool(e['success']) for e in episodes if e['variant'] == A}; byB = {e['task_id']: bool(e['success']) for e in episodes if e['variant'] == B}
    d = np.array([float(byB[t]) - float(byA[t]) for t in tasks])
    ct = cluster_table(design, tasks, s, d, episodes)
    n_pairs = int((ct['kind'] == 'pair').sum()); n_single = int((ct['kind'] == 'single').sum())
    assert n_pairs == design['n_pairs'] == 295 and n_single == design['n_unpaired'] == 1 and int(ct['n_tasks'].sum()) == N == 591
    h_task = math.sqrt(2 * math.log(2 / alpha) / N)
    out = {}
    for name, x, tot, t_ci in (('net_benefit', s, ct['score_total'].values, tuple(shadow['nb_ci'])),
                               ('success_difference', d, ct['success_diff_total'].values, tuple(comps['same_task_paired']['success']['ci']))):
        x = np.asarray(x, float); se_task = float(x.std(ddof=1) / math.sqrt(N))
        cl = cluster_inference(tot, ct['n_tasks'].values, alpha, n_pairs, n_single)
        assert abs(cl['estimate'] - x.mean()) < 1e-12
        pr = ct[ct['kind'] == 'pair']; c1 = 'score_task_1' if name == 'net_benefit' else 'success_diff_task_1'; c2 = c1.replace('_1', '_2')
        a1 = pr[c1].astype(float).values; a2 = pr[c2].astype(float).values
        out[name] = dict(
            estimate=float(x.mean()), n_tasks=int(N), task_level_sd=float(x.std(ddof=1)), task_level_se=se_task,
            task_level=dict(interval_t=t_ci, interval_t_status=E2_MODEL + '; ' + E2_T_EXTRA,
                            hoeffding_radius=h_task, interval_hoeffding=(max(-1.0, float(x.mean() - h_task)), min(1.0, float(x.mean() + h_task))),
                            interval_hoeffding_status='exact finite-sample final-time bound ONLY under the same model (independent task scores in [-1,1]); ' + E2_MODEL),
            orientation_pair_cluster=cl,
            se_ratio_cluster_over_task=cl['cluster_robust_se'] / se_task,
            within_pair_descriptive=dict(n_pairs=int(len(pr)), pearson_corr_of_the_two_task_scores=(float(np.corrcoef(a1, a2)[0, 1]) if a1.std() > 0 and a2.std() > 0 else None),
                                         mean_product_minus_product_of_means=float((a1 * a2).mean() - a1.mean() * a2.mean()),
                                         note='descriptive; position 1 / position 2 of the design pair'))
    sd = out['success_difference']; lows = dict(task_t=sd['task_level']['interval_t'][0], task_hoeffding=sd['task_level']['interval_hoeffding'][0],
                                                 cluster_t=sd['orientation_pair_cluster']['interval_cluster_t'][0], cluster_hoeffding=sd['orientation_pair_cluster']['interval_cluster_hoeffding'][0])
    sd['margin'] = -margin; sd['b_only'] = int((d > 0).sum()); sd['a_only'] = int((d < 0).sum())
    sd['lower_ends'] = lows; sd['lower_end_minus_margin'] = {k: v + margin for k, v in lows.items()}
    # CERTIFIED would require a lower end above the margin under an interval whose assumptions hold by design; none does.
    sd['margin_certified_by_any_interval'] = False
    sd['margin_note'] = ('The -%.2f margin is NOT certified by any of these intervals: the task-level t interval clears it by %.6f only under the independence + CLT model '
                         '(not a design property); the cluster-robust t interval lower end is %.6f and the two Hoeffding lower ends are %.4f (task-level, model-based) and %.4f '
                         '(cluster-level).' % (margin, lows['task_t'] + margin, lows['cluster_t'], lows['task_hoeffding'], lows['cluster_hoeffding']))
    # exposure-order split of the same-task score (descriptive)
    p1 = {a['task_id']: a['pass1_variant'] for a in design['arrivals']}
    order = np.array(['A_then_B' if p1[t] == A else 'B_then_A' for t in tasks])
    by_order = {o: dict(n_tasks=int((order == o).sum()), mean_score=float(s[order == o].mean()), mean_success_diff=float(d[order == o].mean())) for o in ('A_then_B', 'B_then_A')}
    return dict(target='assignment-averaged same-task preference over the roster: (1/591) sum_t E[S_t], the expectation taken over the orientation coins (which fix the pass in which '
                       'each workflow sees task t) and over episode randomness; S_t = h(Y_B(t), Y_A(t)) from the one A and one B episode of task t',
                estimator='total same-task score / 591', clusters='295 design pairs of design.json (shared AB/BA coin, complementary pass positions) + singleton unpaired task mbpp/256; G = 296',
                counterexample=COUNTEREXAMPLE, lindeberg_note='Bounded independent scores do not by themselves give a CLT: for S_t ~ Bernoulli(1/N) independently, all N = 591 scores are 0 '
                'with probability (1-1/591)^591 = %.6f and the zero-width t interval then excludes the mean 1/591.' % ((1 - 1 / 591) ** 591),
                net_benefit=out['net_benefit'], success_difference=sd, by_exposure_order_descriptive=by_order), ct


def pass_effects(episodes):
    rows = []
    for v, letter in ((A, 'A'), (B, 'B')):
        g = {}
        for p in (1, 2):
            eps = [e for e in episodes if e['variant'] == v and int(e['pass']) == p]
            g[p] = dict(n=len(eps), succ=float(np.mean([bool(e['success']) for e in eps])), lat=float(np.mean([float(e['latency_s']) for e in eps])),
                        med=float(np.median([float(e['latency_s']) for e in eps])), tok=float(np.mean([float(e['completion_tokens']) for e in eps])))
        rows.append(dict(arm=letter, variant=v, n_pass1=g[1]['n'], n_pass2=g[2]['n'],
                         success_rate_pass1=g[1]['succ'], success_rate_pass2=g[2]['succ'], success_rate_diff_pass2_minus_pass1=g[2]['succ'] - g[1]['succ'],
                         mean_latency_s_pass1=g[1]['lat'], mean_latency_s_pass2=g[2]['lat'], mean_latency_s_diff_pass2_minus_pass1=g[2]['lat'] - g[1]['lat'],
                         median_latency_s_pass1=g[1]['med'], median_latency_s_pass2=g[2]['med'],
                         mean_completion_tokens_pass1=g[1]['tok'], mean_completion_tokens_pass2=g[2]['tok'], mean_completion_tokens_diff_pass2_minus_pass1=g[2]['tok'] - g[1]['tok']))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results-dir', default=str(RESULTS_DIR))
    args = ap.parse_args(argv)
    rd = Path(args.results_dir); cfg = load_config(None); cfg['_results_dir'] = str(rd)
    from data import load_tasks
    tasks_by_uid = {t['uid']: t for t in load_tasks()}
    design = load_design(rd, 1); episodes = read_jsonl(rd / 'episodes.jsonl')
    assert len(episodes) == 1182, len(episodes)
    S2 = json.loads((rd / 'summary_v2.json').read_text())          # regenerated by run_v3_all.py with the endpoint-fixed wincs before this step
    shadow = v1.shadow_analysis(episodes, cfg, tasks_by_uid); comps = v1.component_effects(episodes, design, cfg, 1)
    assert abs(shadow['net_benefit'] - S2['shadow']['net_benefit']) < 1e-12
    e2, ct = e2_v3(design, episodes, cfg, shadow, comps)
    pe = pass_effects(episodes)
    assert abs(cluster_hoeffding_radius(295, 1, 591, 0.05) - 0.15794) < 5e-6

    # E1: numbers of analysis_v2 (unchanged); Round 10 wording
    R1 = dict(S2['e1']['R1']); R2 = dict(S2['e1']['R2']); mon = dict(S2['e1']['monitor'])
    R1.update(reading='R1: running conditional mean (POST HOC)', target=R1_TARGET, filtration='F_k = sigma(design information independent of future outcomes, revealed pair data up to k)',
              assumption='bounded scores and the stated filtration only (Z_k - mu_k is a martingale difference with range 2); no iid / stationarity / independence-of-pairs assumption',
              interpretation_condition=R1_EXTRA,
              joint_coverage_note='the separate 95% CSs for NB and for the success difference are NOT a joint 95% region',
              post_hoc_note='rho = 100 was fixed after the outcomes of this experiment had been seen (post hoc); fixing it before computing these intervals does not preregister the analysis')
    R2.update(reading='R2: iid-roster superpopulation MODEL', model=R2_MODEL, filtration='F = past revealed pair data plus design information independent of future task values (NOT the entire realized roster)')
    mon['status_R1'] = ('DESCRIPTIVE. The fixed-stake one-sided e-processes test the pointwise conditional null (harm: mu_k >= 0 for every k); no guarantee about the running conditional mean '
                        'or theta_N is claimed from a crossing, and no new theorem is imported.')
    mon['status_R2'] = 'Under the R2 model E[Z_k | F_(k-1)] = theta_P for the stated (coarse) filtration, so the crossings carry the anytime type-I guarantee at alpha for theta_P; model-based, not conditional on the curated roster.'

    # decision rules: same numbers as v2, Round 10 reading labels, plus the cluster rows
    rules = []
    for r in S2['decision_rules']:
        r = dict(r)
        if r['data'] == 'shadow':
            r['reading'] = 'E2 task-level, MODEL-BASED (independent task scores, stable episode laws, no pass/period effects; t interval approximate)'
        elif r['reading'].startswith('R1'):
            r['reading'] = 'R1 (running conditional mean given the stated filtration; POST HOC)'
        else:
            r['reading'] = 'R2 (iid-roster MODEL; unconditional, not conditional on the curated benchmark)'
        rules.append(r)
    nbc = e2['net_benefit']['orientation_pair_cluster']; sdc = e2['success_difference']['orientation_pair_cluster']
    dec = lambda c: 'A' if c[1] < 0 else ('B' if c[0] > 0 else 'none')
    rules += [dict(rule='hierarchical_nb_cluster_robust_t', data='shadow', estimate=nbc['estimate'], ci=list(nbc['interval_cluster_t']), decision=dec(nbc['interval_cluster_t']),
                   reading='E2 orientation-pair clusters (G = 296), APPROXIMATE, independent clusters assumed', detail='POST HOC (Round 10); cluster-robust SE %.6f' % nbc['cluster_robust_se']),
              dict(rule='hierarchical_nb_cluster_hoeffding', data='shadow', estimate=nbc['estimate'], ci=list(nbc['interval_cluster_hoeffding']), decision=dec(nbc['interval_cluster_hoeffding']),
                   reading='E2 orientation-pair clusters, exact final-time Hoeffding, independent clusters assumed', detail='POST HOC (Round 10); radius %.5f' % nbc['hoeffding_cluster_radius']),
              dict(rule='success_only_cluster_robust_t', data='shadow', estimate=sdc['estimate'], ci=list(sdc['interval_cluster_t']), decision=dec(sdc['interval_cluster_t']),
                   reading='E2 orientation-pair clusters (G = 296), APPROXIMATE, independent clusters assumed', detail='POST HOC (Round 10); -0.03 margin NOT certified'),
              dict(rule='success_only_cluster_hoeffding', data='shadow', estimate=sdc['estimate'], ci=list(sdc['interval_cluster_hoeffding']), decision=dec(sdc['interval_cluster_hoeffding']),
                   reading='E2 orientation-pair clusters, exact final-time Hoeffding, independent clusters assumed', detail='POST HOC (Round 10); -0.03 margin NOT certified')]

    old_e2 = S2['e2']
    e2_old_vs_new = dict(
        v2=dict(task_t=list(old_e2['finite_roster']['interval_t']), task_t_label_v2='"conservative (Neyman-type)" [WITHDRAWN as a design-based statement]',
                task_hoeffding=list(old_e2['finite_roster']['interval_hoeffding']), task_hoeffding_label_v2='described in v2 as needing no assumption [WITHDRAWN]',
                success_task_t=list(old_e2['success_difference']['interval_t']), success_task_hoeffding=list(old_e2['success_difference']['interval_hoeffding'])),
        v3=dict(task_t=list(e2['net_benefit']['task_level']['interval_t']), task_hoeffding=list(e2['net_benefit']['task_level']['interval_hoeffding']), task_level_label='MODEL-BASED',
                cluster_t=list(nbc['interval_cluster_t']), cluster_hoeffding=list(nbc['interval_cluster_hoeffding']),
                success_task_t=list(e2['success_difference']['task_level']['interval_t']), success_task_hoeffding=list(e2['success_difference']['task_level']['interval_hoeffding']),
                success_cluster_t=list(sdc['interval_cluster_t']), success_cluster_hoeffding=list(sdc['interval_cluster_hoeffding'])))
    summary = v1._clean(dict(
        generated_at=iso(now_ts()), analysis='analysis_v3.py (POST HOC Round 10; analysis.py frozen, analysis_v2.py unchanged)', results_dir='<REPO>/results/local_stream',
        n_episodes=len(episodes), config_hash=cfg['_config_hash'],
        inputs_sha256={f: v2.sha256_file(rd / f) for f in ('episodes.jsonl', 'monitor_pass1.csv', 'monitor_state.json', 'design.json', 'run_manifest.json')},
        wincs_sha256=v2.sha256_file(HERE.parents[1] / 'src' / 'wincs.py'), summary_v2_sha256=v2.sha256_file(rd / 'summary_v2.json'),
        online_label=S2['online_label'], e1=dict(R1=R1, R2=R2, monitor=mon, scores=S2['e1']['scores']),
        e2=e2, e2_old_vs_new=e2_old_vs_new, pass_effects=dict(rows=pe, status='DESCRIPTIVE ONLY, no inference: for a given variant the pass-1 and pass-2 episodes are on DIFFERENT tasks '
                                                                 '(a random split of the roster), so a difference mixes task composition with any period effect'),
        e1_vs_e2=S2['e1_vs_e2'], decision_rules=rules))
    (rd / 'summary_v3.json').write_text(json.dumps(summary, indent=2))
    pd.DataFrame(v1._clean(rules)).to_csv(rd / 'decision_rules_v3.csv', index=False)
    ct.to_csv(rd / 'e2_cluster_v3.csv', index=False)
    pd.DataFrame(pe).to_csv(rd / 'pass_effects_v3.csv', index=False)
    print(json.dumps(dict(e2_old_vs_new=e2_old_vs_new, nb_task_se=e2['net_benefit']['task_level_se'], nb_cluster_se=nbc['cluster_robust_se'], se_ratio=e2['net_benefit']['se_ratio_cluster_over_task'],
                          sd_task_se=e2['success_difference']['task_level_se'], sd_cluster_se=sdc['cluster_robust_se'], within_pair=e2['net_benefit']['within_pair_descriptive'],
                          by_order=e2['by_exposure_order_descriptive'], pass_effects=pe), indent=1, default=str))


if __name__ == '__main__':
    main()
