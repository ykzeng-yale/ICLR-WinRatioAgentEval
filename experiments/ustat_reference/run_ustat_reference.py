"""Sequential all-pairs U-statistic reference baselines vs the paper's disjoint-pair rules.

Same generator, scenarios, seeds convention, looks, thresholds and one-sided
alpha = 0.05 per gate as experiments/run_online_methods.py.  Each replicate
draws 10000 runs of A and 10000 runs of B; the disjoint-pair rules see pair i
= (A_i, B_i) (the paper's stream), the all-pairs rules compare every A_i with
every B_j among the same executions (n_A = n_B = n at each look).

Methods (each as win_only_* on the net-benefit gate only, and guarded_* as the
intersection-union of three gates: net benefit > 0, success difference > -0.03,
compliance difference > -0.01, each at its own level 0.05):
  allpairs_fixed_wald   fixed-horizon Wald at n = 10000 (Bebu-Lachin anchor)
  allpairs_gs_obf       group sequential, K = 10 equally spaced looks, Lan-DeMets O'Brien-Fleming-type spending
  allpairs_gs_pocock    same with Lan-DeMets Pocock-type spending
  allpairs_gs_hsd       same with Hwang-Shih-DeCani gamma = -3 spending (Bergemann-Hanson)
  allpairs_asympcs      asymptotic anytime-valid CS at the paper's 199 looks (one-sided normal mixture, rho^2 = 100)
  disjoint_gs_obf       the SAME group-sequential OBF rule applied to the disjoint-pair mean (design isolation)
  disjoint_betting      the paper's betting e-process recomputed on this stream (must equal results/online_methods_results.csv)
Guarded rules use "ever rejected" semantics: a gate's sequential test stops at
its first crossing and deployment happens at the first look at which all
three gates have crossed.  *_simultaneous variants use the paper's convention
(all three gate statistics beyond their boundaries at the same look).

All-pairs / group-sequential / AsympCS rules are asymptotic; the betting rule
is exact finite-sample.  Group-sequential rules use only 10 planned looks.
"""
import argparse, csv, hashlib, json, os, platform, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'experiments')); sys.path.insert(0, str(HERE))
from winstats import betting_log_e_ternary
from run_simulations import exact_targets
from run_online_methods import SCENARIOS, THRESHOLDS
import ustat as US

ALPHA = .05
GATES = ('nb', 'success', 'compliance')
SPENDING = {'obf': 'obf', 'pocock': 'pocock', 'hsd': 'hsd'}


def batch_stats(raw, looks):
    """Per-replicate all-pairs statistics over looks -> dict gate -> (U, var) arrays (batch, K)."""
    b = raw['z'].shape[0]; K = len(looks)
    U = {g: np.zeros((b, K)) for g in GATES}; V = {g: np.zeros((b, K)) for g in GATES}
    extra = {'zeta10': np.zeros((b, K)), 'zeta01': np.zeros((b, K)), 'var_h': np.zeros((b, K))}
    for r in range(b):
        st = US.hierarchical_prefix_stats(raw['safe_a'][r], raw['success_a'][r], raw['cost_a'][r],
                                          raw['safe_b'][r], raw['success_b'][r], raw['cost_b'][r], looks)
        U['nb'][r] = st['U']; V['nb'][r] = st['var_u']
        U['success'][r] = st['U_success']; V['success'][r] = st['var_u_success']
        U['compliance'][r] = st['U_compliance']; V['compliance'][r] = st['var_u_compliance']
        extra['zeta10'][r] = st['zeta10']; extra['zeta01'][r] = st['zeta01']; extra['var_h'][r] = st['var_h']
    return U, V, extra


def decisions(raw, looks, bounds, cs_u):
    """Boolean decision arrays (batch, K) per method; True at look k means 'deploy at look k'."""
    U, V, extra = batch_stats(raw, looks)
    K = len(looks); b = raw['z'].shape[0]
    group_idx = np.flatnonzero(np.isin(looks, np.arange(1, 11) * (looks[-1] // 10)))
    group_mask = np.zeros(K, bool); group_mask[group_idx] = True
    out = {}
    gate_ever = {}  # method -> gate -> (batch,) ever rejected by the end

    def register(name, per_gate_state):
        """per_gate_state: dict gate -> (batch, K) boolean 'gate rejected at or before look k'."""
        all_ = np.logical_and.reduce([per_gate_state[g] for g in GATES])
        out['win_only_' + name] = per_gate_state['nb']
        out['guarded_' + name] = all_
        gate_ever[name] = {g: per_gate_state[g][:, -1] for g in GATES}

    # fixed-horizon Wald anchor (all pairs, n = 10000 per arm)
    st = {}
    for g, c in zip(GATES, THRESHOLDS):
        z = US.zstat(U[g][:, -1], V[g][:, -1], c)
        d = np.zeros((b, K), bool); d[:, -1] = z > norm.ppf(1 - ALPHA); st[g] = d
    register('allpairs_fixed_wald', st)

    # group-sequential all-pairs, K = 10 planned looks
    for kind, cvec in bounds.items():
        st = {}; sim = {}
        for g, c in zip(GATES, THRESHOLDS):
            z = US.zstat(U[g][:, group_idx], V[g][:, group_idx], c)          # (batch, 10)
            cross = z >= cvec[None, :]
            ever = np.zeros((b, K), bool); ever[:, group_idx] = np.maximum.accumulate(cross, axis=1)
            now = np.zeros((b, K), bool); now[:, group_idx] = cross
            st[g] = ever; sim[g] = now
        register(f'allpairs_gs_{kind}', st)
        out[f'guarded_allpairs_gs_{kind}_simultaneous'] = np.logical_and.reduce([sim[g] for g in GATES])

    # asymptotic anytime-valid CS on all-pairs statistic at all 199 looks
    st = {}; sim = {}
    for g, c in zip(GATES, THRESHOLDS):
        sig = np.sqrt(np.maximum(V[g], 0) * looks[None, :])       # sigma_hat = sqrt(zeta10 + zeta01) with n_A = n_B = n
        lower = U[g] - sig * cs_u[None, :] / looks[None, :]
        rej = (lower > c) & (V[g] > 0)
        st[g] = np.maximum.accumulate(rej, axis=1); sim[g] = rej
    register('allpairs_asympcs', st)
    out['guarded_allpairs_asympcs_simultaneous'] = np.logical_and.reduce([sim[g] for g in GATES])

    # disjoint-pair comparators on the same executions
    zs = [raw['z'], raw['dq'], raw['ds']]
    st_gs = {}; st_bet = {}; bet_now = {}
    for g, z, c in zip(GATES, zs, THRESHOLDS):
        pos = np.cumsum(z > 0, axis=1)[:, looks - 1]; neg = np.cumsum(z < 0, axis=1)[:, looks - 1]
        means = (pos - neg) / looks
        s2 = np.maximum((pos + neg - looks * means**2) / (looks - 1), 0); se = np.sqrt(s2 / looks)
        zz = US.zstat(means[:, group_idx], se[:, group_idx]**2, c)
        cross = zz >= bounds['obf'][None, :]
        ever = np.zeros((b, K), bool); ever[:, group_idx] = np.maximum.accumulate(cross, axis=1); st_gs[g] = ever
        e = betting_log_e_ternary(pos, neg, looks, c) >= np.log(1 / ALPHA)
        bet_now[g] = e; st_bet[g] = np.maximum.accumulate(e, axis=1)
    register('disjoint_gs_obf', st_gs)
    register('disjoint_betting', st_bet)
    out['guarded_disjoint_betting_simultaneous'] = np.logical_and.reduce([bet_now[g] for g in GATES])
    out['win_only_disjoint_betting_simultaneous'] = bet_now['nb']
    final = dict(U_allpairs=U['nb'][:, -1], var_allpairs=V['nb'][:, -1],
                 U_disjoint=(np.sum(raw['z'] > 0, 1) - np.sum(raw['z'] < 0, 1)) / looks[-1],
                 zeta10=extra['zeta10'][:, -1], zeta01=extra['zeta01'][:, -1], var_h=extra['var_h'][:, -1])
    return out, gate_ever, final


def run_scenario(job):
    j, name, params, args, looks, bounds, cs_u = job
    t0 = time.perf_counter()
    rng = np.random.default_rng(np.random.SeedSequence([args['seed'], j]))
    accum = {}; gates = {}; finals = {k: [] for k in ('U_allpairs', 'var_allpairs', 'U_disjoint', 'zeta10', 'zeta01', 'var_h')}
    for begin in range(0, args['replicates'], args['batch']):
        batch = min(args['batch'], args['replicates'] - begin)
        raw = US.generate_raw(rng, (batch, args['pairs']), params)
        dec, gate_ever, final = decisions(raw, looks, bounds, cs_u)
        for k, v in final.items(): finals[k].extend(v.tolist())
        for method, d in dec.items():
            success = d.any(axis=1)
            stops = np.where(success, looks[np.argmax(d, axis=1)], args['pairs'])
            acc = accum.setdefault(method, {'deploy': 0, 'stop_sum': 0., 'stop_sq': 0., 'positive_stop': []})
            acc['deploy'] += int(success.sum()); acc['stop_sum'] += float(stops.sum())
            acc['stop_sq'] += float((stops.astype(float)**2).sum()); acc['positive_stop'].extend(stops[success].tolist())
        for method, gd in gate_ever.items():
            gg = gates.setdefault(method, {g: 0 for g in GATES})
            for g in GATES: gg[g] += int(gd[g].sum())
    return dict(name=name, accum=accum, gates=gates, finals=finals, seconds=time.perf_counter() - t0,
                maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--replicates', type=int, default=2000)
    ap.add_argument('--pairs', type=int, default=10000)
    ap.add_argument('--batch', type=int, default=25)
    ap.add_argument('--seed', type=int, default=20260918)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--mc-pairs', type=int, default=1_000_000)
    ap.add_argument('--out', type=str, default=str(ROOT / 'results' / 'ustat_reference'))
    ap.add_argument('--calibration-only', action='store_true',
                    help='run only the null and tie_heavy_null scenarios with a fresh seed stream (SeedSequence([seed, 100 + j])) '
                         'and write null_calibration.csv / calibration_manifest.json instead of the main study files')
    args = ap.parse_args(); start = time.time()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    looks = np.unique(np.r_[np.arange(100, args.pairs + 1, 50), args.pairs, np.arange(1, 11) * (args.pairs // 10)])
    t10 = np.arange(1, 11) / 10
    bounds = {kind: US.gs_boundaries(t10, US.spending(kind, t10, ALPHA)) for kind in SPENDING}
    cs_u = US.one_sided_normal_mixture_boundary(looks.astype(float), ALPHA, 100.)
    if args.calibration_only:
        names = ['null', 'tie_heavy_null']
        jobs = [(100 + list(SCENARIOS).index(n), n, SCENARIOS[n], vars(args), looks, bounds, cs_u) for n in names]
        with get_context('fork').Pool(len(jobs)) as pool:
            results = pool.map(run_scenario, jobs)
        rows = []
        for res in results:
            for method, acc in res['accum'].items():
                low, high = US.wilson(acc['deploy'], args.replicates)
                rows.append(dict(scenario=res['name'], method=method, replicates=args.replicates, deployments=acc['deploy'],
                                 deployment_rate=acc['deploy'] / args.replicates, rate_ci_lower=low, rate_ci_upper=high))
            for method, gg in res['gates'].items():
                for g in GATES:
                    low, high = US.wilson(gg[g], args.replicates)
                    rows.append(dict(scenario=res['name'], method='gate_' + g + '_' + method, replicates=args.replicates, deployments=gg[g],
                                     deployment_rate=gg[g] / args.replicates, rate_ci_lower=low, rate_ci_upper=high))
        with (out_dir / 'null_calibration.csv').open('w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        (out_dir / 'calibration_manifest.json').write_text(json.dumps(dict(
            arguments=vars(args), seeds='SeedSequence([seed, 100 + scenario_index])', seconds=time.time() - start,
            per_scenario={r['name']: dict(seconds=r['seconds'], maxrss_bytes=r['maxrss']) for r in results},
            peak_rss_bytes_max_child=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ('ustat.py', 'run_ustat_reference.py')}), indent=2, default=float))
        print('calibration done', f'{time.time() - start:.0f}s'); return
    validation = {
        'ld_obf_k5_alpha025_one_sided': US.gs_boundaries(np.arange(1, 6) / 5, US.spending('obf', np.arange(1, 6) / 5, .025)).round(4).tolist(),
        'ld_obf_k5_alpha025_reference': [4.877, 3.357, 2.680, 2.290, 2.031],
        'k10_alpha05_boundaries': {k: v.round(4).tolist() for k, v in bounds.items()},
        'k10_exit_probability_sums': {k: float(US.gs_exit_probabilities(t10, v).sum()) for k, v in bounds.items()},
    }
    # efficiency components (Monte Carlo, analytic conditional means)
    eff_rows = []
    for j, (name, params) in enumerate(SCENARIOS.items()):
        e = US.efficiency_components(params, n_mc=args.mc_pairs, seed=1000 + j)
        th = exact_targets(params)[0]; n = args.pairs
        e.update(scenario=name, theta_exact=th, n_mc_pairs=args.mc_pairs,
                 predicted_fixed_power_nb_disjoint=float(norm.cdf(th * np.sqrt(n / e['var_h']) - norm.ppf(1 - ALPHA))),
                 predicted_fixed_power_nb_allpairs=float(norm.cdf(th * np.sqrt(n / (e['zeta10'] + e['zeta01'])) - norm.ppf(1 - ALPHA))))
        eff_rows.append(e)
    jobs = [(j, name, params, vars(args), looks, bounds, cs_u) for j, (name, params) in enumerate(SCENARIOS.items())]
    if args.workers > 1:
        with get_context('fork').Pool(min(args.workers, len(jobs))) as pool:
            results = pool.map(run_scenario, jobs)
    else:
        results = [run_scenario(job) for job in jobs]
    rows = []; gate_rows = []; est_rows = []; timing = {}
    for res, (name, params) in zip(results, SCENARIOS.items()):
        targets = exact_targets(params); admissible = all(x > c for x, c in zip(targets, THRESHOLDS))
        timing[name] = dict(seconds=res['seconds'], maxrss_bytes=res['maxrss'])
        for method, acc in res['accum'].items():
            low, high = US.wilson(acc['deploy'], args.replicates); m = acc['stop_sum'] / args.replicates
            rows.append(dict(scenario=name, method=method, replicates=args.replicates, max_runs_per_arm=args.pairs,
                             true_net_benefit=targets[0], true_success_difference=targets[1], true_safety_difference=targets[2],
                             admissible=admissible, deployments=acc['deploy'], deployment_rate=acc['deploy'] / args.replicates,
                             rate_ci_lower=low, rate_ci_upper=high, mean_runs_per_arm_used=m,
                             mean_runs_mcse=np.sqrt(max(acc['stop_sq'] / args.replicates - m * m, 0) / args.replicates),
                             median_runs_among_deployments=float(np.median(acc['positive_stop'])) if acc['positive_stop'] else ''))
        for method, gg in res['gates'].items():
            for g, c, tv in zip(GATES, THRESHOLDS, targets):
                low, high = US.wilson(gg[g], args.replicates)
                gate_rows.append(dict(scenario=name, method=method, gate=g, threshold=c, true_value=tv, gate_true=tv > c,
                                      rejections=gg[g], rejection_rate=gg[g] / args.replicates, rate_ci_lower=low, rate_ci_upper=high))
        f = {k: np.asarray(v) for k, v in res['finals'].items()}
        est_rows.append(dict(scenario=name, theta_exact=targets[0], mean_U_allpairs=f['U_allpairs'].mean(), mean_U_disjoint=f['U_disjoint'].mean(),
                             empirical_var_U_allpairs=f['U_allpairs'].var(ddof=1), mean_estimated_var_U_allpairs=f['var_allpairs'].mean(),
                             empirical_var_U_disjoint=f['U_disjoint'].var(ddof=1), mean_var_h_over_n=f['var_h'].mean() / args.pairs,
                             empirical_variance_ratio_disjoint_over_allpairs=f['U_disjoint'].var(ddof=1) / f['U_allpairs'].var(ddof=1),
                             mean_zeta10_hat=f['zeta10'].mean(), mean_zeta01_hat=f['zeta01'].mean(), replicates=args.replicates))
        print(name, {k: round(v['deploy'] / args.replicates, 4) for k, v in res['accum'].items() if k.startswith('guarded')}, f"{res['seconds']:.0f}s", flush=True)
    for fname, rws in (('ustat_reference_results.csv', rows), ('ustat_reference_gate_rates.csv', gate_rows),
                       ('ustat_reference_efficiency.csv', eff_rows), ('ustat_reference_estimator_check.csv', est_rows)):
        with (out_dir / fname).open('w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rws[0].keys())); w.writeheader(); w.writerows(rws)
    ru_self = resource.getrusage(resource.RUSAGE_SELF); ru_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    manifest = dict(arguments=vars(args), alpha=ALPHA, thresholds=THRESHOLDS, gates=GATES, looks=looks.tolist(),
                    group_sequential_looks=(np.arange(1, 11) * (args.pairs // 10)).tolist(), information_fractions=t10.tolist(),
                    boundaries_z_scale={k: v.tolist() for k, v in bounds.items()}, boundary_validation=validation,
                    asympcs=dict(boundary='one-sided normal mixture (Howard et al. 2021), V=n, rho2=100, sigma_hat=sqrt(zeta10_hat+zeta01_hat)',
                                 u_over_n_at_looks=dict(zip(map(int, looks[[0, 18, 38, 98, 198]]), (cs_u / looks)[[0, 18, 38, 98, 198]].round(5).tolist()))),
                    seeds=dict(convention='numpy SeedSequence([seed, scenario_index]); scenario_index = position in run_online_methods.SCENARIOS', seed=args.seed,
                               efficiency_mc_seeds=[1000 + j for j in range(len(SCENARIOS))]),
                    scenarios=SCENARIOS, seconds_total=time.time() - start, per_scenario=timing,
                    peak_rss_bytes_parent=ru_self.ru_maxrss, peak_rss_bytes_max_child=ru_child.ru_maxrss,
                    python=platform.python_version(), numpy=np.__version__, platform=platform.platform(),
                    source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ('ustat.py', 'run_ustat_reference.py')},
                    upstream_sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in
                                     ('src/winstats.py', 'experiments/run_simulations.py', 'experiments/run_online_methods.py')},
                    interpretation='Synthetic independent streams, not live A/B results. All-pairs, group-sequential and AsympCS rules are asymptotic; '
                                   'disjoint_betting is exact finite-sample. Group-sequential rules use only the 10 planned looks. Runs used are per arm '
                                   '(1 run per arm = 1 disjoint pair), so max_runs_per_arm = 10000 is the same execution budget as max_pairs = 10000.')
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, default=float))
    print('done', f'{time.time() - start:.0f}s')


if __name__ == '__main__':
    main()
