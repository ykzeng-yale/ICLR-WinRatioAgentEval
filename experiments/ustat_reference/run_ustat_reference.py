"""Sequential all-pairs U-statistic reference baselines vs the paper's disjoint-pair rules.

Same generator, scenarios, seed convention, looks, thresholds and one-sided
alpha = 0.05 per gate as experiments/run_online_methods.py.

Execution accounting (the root convention of paper/pairing_efficiency.tex and
reviews/round6_pairing_efficiency_identity.md): each replicate draws N = 10000
records per arm = 2N executions = N disjoint pairs; at a look with n records per
arm both designs have consumed the same 2n executions.  The disjoint-pair rules
see pair i = (A_i, B_i) (the paper's stream); the all-pairs rules compare every
A_i with every B_j among the same executions (n_A = n_B = n at each look).
"runs per arm" in the outputs therefore equals the paper's "pairs".

Methods (each as win_only_* on the net-benefit gate only, and guarded_* as the
intersection-union of three gates: net benefit > 0, success difference > -0.03,
compliance difference > -0.01, each at its own one-sided level 0.05):
  allpairs_fixed_wald      fixed-horizon Wald at n = 10000 (Bebu-Lachin anchor; a single look)
  allpairs_gs_obf          group sequential, K = 10 equally spaced looks, Lan-DeMets O'Brien-Fleming-type spending
  allpairs_gs_pocock       same with Lan-DeMets Pocock-type spending
  allpairs_gs_hsd          same with Hwang-Shih-DeCani gamma = -3 spending (Bergemann-Hanson)
  allpairs_asympcs_projection_gaussian
                           projection-based Gaussian anytime monitoring of the all-pairs statistic at the
                           paper's 199 looks: U_n - sigma_hat_n u_alpha(n)/n with sigma_hat_n^2 = zeta10_hat
                           + zeta01_hat and the one-sided normal-mixture boundary (rho^2 = 100) from the first
                           look n = 100.  Guarantee: an asymptotic confidence sequence (Waudby-Smith et al.
                           time-uniform-CLT route) via the symmetric-kernel one-sample reduction described in
                           ustat.py; NOT a finite-sample 5% crossing bound from n = 100 and NOT the delayed-start
                           family of Cai, Hu & Li.
  disjoint_gs_obf          the SAME group-sequential OBF rule applied to the disjoint-pair mean (design isolation)
  disjoint_betting         the paper's betting e-process recomputed on this stream

Guarded conventions (both are written for every multi-look rule):
  guarded_<rule>_simultaneous  the paper's rule: deploy at the first look at which all three gate statistics
                               are beyond their boundaries at that same look (same-look conjunction).  This is
                               the convention of results/online_methods_results.csv (guarded_betting,
                               guarded_group_bonferroni_wald, guarded_fixed_wald) and the only convention used
                               for comparisons against the paper; guarded_disjoint_betting_simultaneous is the
                               row checked for exact reproduction of the paper's guarded_betting row.
  guarded_<rule>_retained      each gate's sequential test stops at its own first crossing and that crossing is
                               retained; deploy at the first look by which all three gates have crossed
                               (possibly at different looks).  Reported for completeness; not compared to the
                               paper and not claimed to reproduce any paper row.
  win_only_<rule> rows have a single gate and are convention-free; guarded_allpairs_fixed_wald has one look, at
  which the two conventions coincide, so it carries no suffix.

Calibration mode (--calibration-only, fresh seed streams SeedSequence([seed, 100 + index])): null and
tie_heavy_null (net-benefit boundary theta = 0 with both guardrails strictly favorable), success_boundary
((.995,.995,.72,.75,.4): success difference exactly -0.03 = threshold, net benefit and compliance comfortably
favorable) and compliance_boundary ((.985,.995,.75,.75,.4): compliance difference exactly -0.01 = threshold),
both as in experiments/run_stress_tests.py.  Guarded deployment in the boundary scenarios is a type I error of
the guarded rule at that guardrail boundary.

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
ASYMPCS = 'allpairs_asympcs_projection_gaussian'
CALIBRATION_SCENARIOS = {
    'null': SCENARIOS['null'],
    'tie_heavy_null': SCENARIOS['tie_heavy_null'],
    'success_boundary': (.995, .995, .72, .75, .4),      # experiments/run_stress_tests.py
    'compliance_boundary': (.985, .995, .75, .75, .4),   # experiments/run_stress_tests.py
}
# seed index: position in run_online_methods.SCENARIOS for its members (unchanged from the first calibration run),
# then 8 and 9 for the two boundary scenarios that are not members of SCENARIOS.
CALIBRATION_SEED_INDEX = {'null': 0, 'tie_heavy_null': 6, 'success_boundary': 8, 'compliance_boundary': 9}
PAPER_RESULTS = ROOT / 'results' / 'online_methods_results.csv'


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
    """Boolean decision arrays (batch, K) per method; True at look k means 'deploy at look k'.

    For every gate two (batch, K) states are kept: `now[g]` (the gate's statistic is beyond its boundary at
    look k) and `ever[g]` = cumulative maximum of `now[g]` (the gate has crossed at or before look k).
    guarded_*_simultaneous = AND of `now`; guarded_*_retained = AND of `ever`; win_only_* = now['nb'] (its
    first True coincides with that of ever['nb'], so the win-only rows are convention-free).
    """
    U, V, extra = batch_stats(raw, looks)
    K = len(looks); b = raw['z'].shape[0]
    group_idx = np.flatnonzero(np.isin(looks, np.arange(1, 11) * (looks[-1] // 10)))
    out = {}
    gate_ever = {}  # method -> gate -> (batch,) ever rejected by the end (convention-free)

    def register(name, now, single_look=False):
        ever = {g: np.maximum.accumulate(now[g], axis=1) for g in GATES}
        out['win_only_' + name] = now['nb']
        if single_look:
            out['guarded_' + name] = np.logical_and.reduce([now[g] for g in GATES])
        else:
            out[f'guarded_{name}_simultaneous'] = np.logical_and.reduce([now[g] for g in GATES])
            out[f'guarded_{name}_retained'] = np.logical_and.reduce([ever[g] for g in GATES])
        gate_ever[name] = {g: ever[g][:, -1] for g in GATES}

    def planned_look_states(zmat_by_gate, cvec):
        now = {}
        for g in GATES:
            nw = np.zeros((b, K), bool); nw[:, group_idx] = zmat_by_gate[g] >= cvec[None, :]; now[g] = nw
        return now

    # fixed-horizon Wald anchor (all pairs, n = 10000 per arm; one look)
    now = {}
    for g, c in zip(GATES, THRESHOLDS):
        z = US.zstat(U[g][:, -1], V[g][:, -1], c)
        d = np.zeros((b, K), bool); d[:, -1] = z > norm.ppf(1 - ALPHA); now[g] = d
    register('allpairs_fixed_wald', now, single_look=True)

    # group-sequential all-pairs, K = 10 planned looks
    for kind, cvec in bounds.items():
        zg = {g: US.zstat(U[g][:, group_idx], V[g][:, group_idx], c) for g, c in zip(GATES, THRESHOLDS)}   # (batch, 10)
        register(f'allpairs_gs_{kind}', planned_look_states(zg, cvec))

    # projection-based Gaussian anytime monitoring (asymptotic CS) on the all-pairs statistic at all 199 looks
    now = {}
    for g, c in zip(GATES, THRESHOLDS):
        sig = np.sqrt(np.maximum(V[g], 0) * looks[None, :])       # sigma_hat = sqrt(zeta10_hat + zeta01_hat) with n_A = n_B = n
        lower = U[g] - sig * cs_u[None, :] / looks[None, :]
        now[g] = (lower > c) & (V[g] > 0)                           # V > 0: numerical convention (no evidence from a degenerate estimate)
    register(ASYMPCS, now)

    # disjoint-pair comparators on the same executions
    zs = [raw['z'], raw['dq'], raw['ds']]
    zg = {}; bet_now = {}
    for g, z, c in zip(GATES, zs, THRESHOLDS):
        pos = np.cumsum(z > 0, axis=1)[:, looks - 1]; neg = np.cumsum(z < 0, axis=1)[:, looks - 1]
        means = (pos - neg) / looks
        s2 = np.maximum((pos + neg - looks * means**2) / (looks - 1), 0); se = np.sqrt(s2 / looks)
        zg[g] = US.zstat(means[:, group_idx], se[:, group_idx]**2, c)
        bet_now[g] = betting_log_e_ternary(pos, neg, looks, c) >= np.log(1 / ALPHA)   # exactly run_online_methods.evaluate
    register('disjoint_gs_obf', planned_look_states(zg, bounds['obf']))
    register('disjoint_betting', bet_now)
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
    return dict(name=name, seed_index=j, accum=accum, gates=gates, finals=finals, seconds=time.perf_counter() - t0,
                maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def convention_of(method):
    if method.endswith('_simultaneous'): return 'simultaneous (same-look conjunction; paper convention)'
    if method.endswith('_retained'): return 'retained (each gate keeps its first crossing)'
    if method.startswith('win_only_'): return 'single gate (convention-free)'
    if method == 'guarded_allpairs_fixed_wald': return 'single look (conventions coincide)'
    return ''


def boundary_gate_of(targets):
    for g, c, tv in zip(GATES, THRESHOLDS, targets):
        if abs(tv - c) < 1e-9: return g
    return ''


def source_hashes():
    return {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ('ustat.py', 'run_ustat_reference.py')}


def machine():
    return dict(python=platform.python_version(), numpy=np.__version__, platform=platform.platform(),
                cpu_count=os.cpu_count(), machine=platform.machine())


def reproduction_check(rows, replicates):
    """Compare the recomputed disjoint betting rows with results/online_methods_results.csv (read-only).

    Only win_only_disjoint_betting <-> win_only_betting and guarded_disjoint_betting_simultaneous <-> guarded_betting
    are expected to be identical (same stream, same rule, same conjunction convention).  The retained-crossing row
    is listed for information only and is not expected to match.
    """
    with PAPER_RESULTS.open() as fh:
        paper = {(r['scenario'], r['method']): r for r in csv.DictReader(fh)}
    mine = {(r['scenario'], r['method']): r for r in rows}
    pairs = [('win_only_disjoint_betting', 'win_only_betting', True),
             ('guarded_disjoint_betting_simultaneous', 'guarded_betting', True),
             ('guarded_disjoint_betting_retained', 'guarded_betting', False)]
    fields = [('deployments', 'deployments'), ('mean_runs_per_arm_used', 'mean_pairs_used'),
              ('median_runs_among_deployments', 'median_pairs_among_deployments'), ('rate_ci_lower', 'rate_ci_lower'),
              ('rate_ci_upper', 'rate_ci_upper'), ('mean_runs_mcse', 'mean_pairs_mcse')]
    report = {'paper_file': str(PAPER_RESULTS.relative_to(ROOT)), 'paper_sha256': hashlib.sha256(PAPER_RESULTS.read_bytes()).hexdigest(),
              'replicates': replicates, 'comparisons': {}, 'all_expected_rows_identical': True}
    for my_m, paper_m, expected in pairs:
        per = {}
        for scen in SCENARIOS:
            a = mine.get((scen, my_m)); p = paper.get((scen, paper_m))
            if a is None or p is None:
                per[scen] = dict(identical=False, missing=True); continue
            same = all(str(a[fa]) == str(p[fp]) for fa, fp in fields)
            per[scen] = dict(identical=same, recomputed=dict(deployments=int(a['deployments']), mean_runs=float(a['mean_runs_per_arm_used']),
                                                              median=a['median_runs_among_deployments']),
                             paper=dict(deployments=int(p['deployments']), mean_pairs=float(p['mean_pairs_used']),
                                        median=p['median_pairs_among_deployments']))
            if expected and not same: report['all_expected_rows_identical'] = False
        report['comparisons'][f'{my_m} vs paper {paper_m}'] = dict(expected_identical=expected, per_scenario=per,
                                                                     all_identical=all(v['identical'] for v in per.values()))
    return report


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
                    help='run only the four calibration nulls (null, tie_heavy_null, success_boundary, compliance_boundary) with fresh '
                         'seed streams SeedSequence([seed, 100 + index]) and write null_calibration.csv / calibration_manifest.json '
                         'instead of the main study files')
    args = ap.parse_args(); start = time.time()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    looks = np.unique(np.r_[np.arange(100, args.pairs + 1, 50), args.pairs, np.arange(1, 11) * (args.pairs // 10)])
    t10 = np.arange(1, 11) / 10
    bounds = {kind: US.gs_boundaries(t10, US.spending(kind, t10, ALPHA)) for kind in SPENDING}
    cs_u = US.one_sided_normal_mixture_boundary(looks.astype(float), ALPHA, 100.)
    if args.calibration_only:
        jobs = [(100 + CALIBRATION_SEED_INDEX[n], n, p, vars(args), looks, bounds, cs_u) for n, p in CALIBRATION_SCENARIOS.items()]
        with get_context('fork').Pool(min(args.workers, len(jobs))) as pool:
            results = pool.map(run_scenario, jobs)
        rows = []
        for res in results:
            targets = exact_targets(CALIBRATION_SCENARIOS[res['name']]); bg = boundary_gate_of(targets)
            base = dict(scenario=res['name'], replicates=args.replicates, true_net_benefit=targets[0], true_success_difference=targets[1],
                        true_safety_difference=targets[2], boundary_gate=bg, admissible=all(x > c for x, c in zip(targets, THRESHOLDS)))
            for method, acc in res['accum'].items():
                low, high = US.wilson(acc['deploy'], args.replicates); m = acc['stop_sum'] / args.replicates
                rows.append(dict(base, method=method, convention=convention_of(method), deployments=acc['deploy'],
                                 deployment_rate=acc['deploy'] / args.replicates, rate_ci_lower=low, rate_ci_upper=high,
                                 mean_runs_per_arm_used=m))
            for method, gg in res['gates'].items():
                for g in GATES:
                    low, high = US.wilson(gg[g], args.replicates)
                    rows.append(dict(base, method='gate_' + g + '_' + method, convention='single gate, ever rejected by n = %d' % args.pairs,
                                     deployments=gg[g], deployment_rate=gg[g] / args.replicates, rate_ci_lower=low, rate_ci_upper=high,
                                     mean_runs_per_arm_used=''))
        with (out_dir / 'null_calibration.csv').open('w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        (out_dir / 'calibration_manifest.json').write_text(json.dumps(dict(
            arguments=vars(args), alpha=ALPHA, thresholds=THRESHOLDS, gates=GATES,
            scenarios=CALIBRATION_SCENARIOS, truths={k: exact_targets(v) for k, v in CALIBRATION_SCENARIOS.items()},
            seeds=dict(convention='numpy SeedSequence([seed, 100 + index])', seed=args.seed, index=CALIBRATION_SEED_INDEX),
            seconds=time.time() - start, workers=min(args.workers, len(jobs)),
            per_scenario={r['name']: dict(seconds=r['seconds'], maxrss_bytes=r['maxrss'], seed_index=r['seed_index']) for r in results},
            peak_rss_bytes_parent=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            peak_rss_bytes_max_child=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            source_sha256=source_hashes(), **machine(),
            interpretation='Type I error at the named boundary: in null/tie_heavy_null the net-benefit gate is at its boundary (theta = 0); '
                           'in success_boundary the success difference equals its threshold -0.03; in compliance_boundary the compliance '
                           'difference equals its threshold -0.01. Every guarded deployment is an error in all four scenarios. '
                           'Wilson 95% intervals. Records per arm = pairs; 2n executions at a look with n records per arm.'),
            indent=2, default=float))
        for res in results:
            print(res['name'], {k: round(v['deploy'] / args.replicates, 4) for k, v in res['accum'].items() if k.startswith('guarded')}, f"{res['seconds']:.0f}s")
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
        timing[name] = dict(seconds=res['seconds'], maxrss_bytes=res['maxrss'], seed_index=res['seed_index'])
        for method, acc in res['accum'].items():
            low, high = US.wilson(acc['deploy'], args.replicates); m = acc['stop_sum'] / args.replicates
            rows.append(dict(scenario=name, method=method, convention=convention_of(method), replicates=args.replicates, max_runs_per_arm=args.pairs,
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
    repro = reproduction_check(rows, args.replicates) if PAPER_RESULTS.exists() else {'paper_file': 'missing'}
    (out_dir / 'ustat_reference_reproduction_check.json').write_text(json.dumps(repro, indent=2))
    print('reproduction of paper betting rows (win_only + guarded simultaneous) identical:', repro.get('all_expected_rows_identical'))
    ru_self = resource.getrusage(resource.RUSAGE_SELF); ru_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    manifest = dict(arguments=vars(args), alpha=ALPHA, thresholds=THRESHOLDS, gates=GATES, looks=looks.tolist(),
                    group_sequential_looks=(np.arange(1, 11) * (args.pairs // 10)).tolist(), information_fractions=t10.tolist(),
                    boundaries_z_scale={k: v.tolist() for k, v in bounds.items()}, boundary_validation=validation,
                    asympcs=dict(method=ASYMPCS,
                                 boundary='one-sided normal mixture (Howard et al. 2021), V=n, rho2=100, sigma_hat=sqrt(zeta10_hat+zeta01_hat), monitored from n=100',
                                 guarantee='asymptotic confidence sequence (Waudby-Smith et al. time-uniform CLT route) via the symmetric-kernel '
                                           'one-sample reduction k(X_i,X_j)={h(A_i,B_j)+h(A_j,B_i)}/2 (see ustat.py and README); not a finite-sample '
                                           '5% crossing bound from n=100; not the Cai-Hu-Li delayed-start family',
                                 u_over_n_at_looks=dict(zip(map(int, looks[[0, 18, 38, 98, 198]]), (cs_u / looks)[[0, 18, 38, 98, 198]].round(5).tolist()))),
                    group_sequential=dict(covariance='canonical Gaussian-limit covariance Cov(Z_k,Z_l)=sqrt(t_k/t_l) (asymptotic independent increments); '
                                                     'information fraction t_k=n_k/N is the first-order limit, not the exact finite-sample fraction'),
                    conventions=dict(simultaneous='deploy at the first look at which all three gate statistics are beyond their boundaries at that look '
                                                  '(paper convention; used for all comparisons with results/online_methods_results.csv)',
                                     retained='each gate keeps its first crossing; deploy at the first look by which all three have crossed',
                                     win_only='single gate, convention-free', fixed_wald='single look, conventions coincide'),
                    seeds=dict(convention='numpy SeedSequence([seed, scenario_index]); scenario_index = position in run_online_methods.SCENARIOS', seed=args.seed,
                               efficiency_mc_seeds=[1000 + j for j in range(len(SCENARIOS))]),
                    scenarios=SCENARIOS, seconds_total=time.time() - start, workers=min(args.workers, len(jobs)), per_scenario=timing,
                    peak_rss_bytes_parent=ru_self.ru_maxrss, peak_rss_bytes_max_child=ru_child.ru_maxrss, **machine(),
                    source_sha256=source_hashes(),
                    upstream_sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in
                                     ('src/winstats.py', 'experiments/run_simulations.py', 'experiments/run_online_methods.py', 'results/online_methods_results.csv')},
                    reproduction_check_all_expected_rows_identical=repro.get('all_expected_rows_identical'),
                    interpretation='Synthetic independent streams, not live A/B results. All-pairs, group-sequential and AsympCS rules are asymptotic; '
                                   'disjoint_betting is exact finite-sample. Group-sequential rules use only the 10 planned looks. Execution accounting: '
                                   'N records per arm = 2N executions = N disjoint pairs, so max_runs_per_arm = 10000 is the paper\'s max_pairs = 10000 '
                                   'and a look with n records per arm has consumed 2n executions for both designs.')
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, default=float))
    print('done', f'{time.time() - start:.0f}s')


if __name__ == '__main__':
    main()
