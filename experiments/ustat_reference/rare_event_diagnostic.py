"""Archived rare-event diagnostic for Section 4.7 of evidence/ustat_reference_report.md (Round 9 correction 4).

Re-runs ONLY the `compliance_boundary` calibration scenario ((.985,.995,.75,.75,.4): compliance difference
exactly -0.01 = threshold) on the frozen calibration seed stream of run_ustat_reference.py,
SeedSequence([20260918, 100 + 9]), 10,000 replicates of 10,000 records per arm, batch 25, and records every
FALSE rejection of the COMPONENT compliance gate (each rule's first crossing of that single gate; this is the
convention-free gate-level event `gate_compliance_<rule>` of null_calibration.csv, NOT a guarded deployment
under either the simultaneous or the retained convention).

Because the compliance kernel is additive, g(a) - g(b), the all-pairs statistic is the difference of arm
compliance means and its projection variance is (s_A^2 + s_B^2)/n; the formulas below are copied from
ustat.hierarchical_prefix_stats / run_ustat_reference.decisions, and the data come from the same
ustat.generate_raw call with the same batch shape, so the random stream is identical.  The script asserts
that its rejection counts equal the `gate_compliance_*` rows of results/ustat_reference/null_calibration.csv.

Primary rule: allpairs_asympcs_projection_gaussian (199 looks).  The other rules' compliance-gate first
crossings are archived too because Section 4.7 tabulates them.

Output: results/ustat_reference/rare_event_diagnostic.csv (one row per false compliance-gate rejection:
rule, replicate, first-crossing look n, noncompliant runs in each arm among the first n, U, variance estimate,
test statistic and boundary at that look) and rare_event_diagnostic_manifest.json (seeds, code hashes, runtime,
summary).  Single process (the stream is one sequential generator); no model or API calls; CPU only.
"""
import argparse, csv, hashlib, json, os, platform, resource, sys, time
from pathlib import Path
import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'experiments')); sys.path.insert(0, str(HERE))
from winstats import betting_log_e_ternary
import ustat as US

ALPHA = .05
SCENARIO = 'compliance_boundary'
PARAMS = (.985, .995, .75, .75, .4)       # run_ustat_reference.CALIBRATION_SCENARIOS['compliance_boundary']
SEED_INDEX = 9                             # run_ustat_reference.CALIBRATION_SEED_INDEX['compliance_boundary']
C = -0.01                                  # compliance threshold (run_online_methods.THRESHOLDS[2])
ASYMPCS = 'allpairs_asympcs_projection_gaussian'


def first_cross(now):
    hit = now.any(axis=1)
    return hit, np.argmax(now, axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--replicates', type=int, default=10000)
    ap.add_argument('--pairs', type=int, default=10000)
    ap.add_argument('--batch', type=int, default=25)
    ap.add_argument('--seed', type=int, default=20260918)
    ap.add_argument('--out', type=str, default=str(ROOT / 'results' / 'ustat_reference'))
    args = ap.parse_args(); t0 = time.time()
    out_dir = Path(args.out)
    looks = np.unique(np.r_[np.arange(100, args.pairs + 1, 50), args.pairs, np.arange(1, 11) * (args.pairs // 10)])
    n = looks.astype(float); K = len(looks)
    group_idx = np.flatnonzero(np.isin(looks, np.arange(1, 11) * (looks[-1] // 10)))
    t10 = np.arange(1, 11) / 10
    bounds = {kind: US.gs_boundaries(t10, US.spending(kind, t10, ALPHA)) for kind in ('obf', 'pocock', 'hsd')}
    cs_u = US.one_sided_normal_mixture_boundary(n, ALPHA, 100.)
    rng = np.random.default_rng(np.random.SeedSequence([args.seed, 100 + SEED_INDEX]))
    rows = []; counts = {}
    for begin in range(0, args.replicates, args.batch):
        b = min(args.batch, args.replicates - begin)
        raw = US.generate_raw(rng, (b, args.pairs), PARAMS)
        xa = raw['safe_a'].astype(float); xb = raw['safe_b'].astype(float)
        ca = np.cumsum(xa, axis=1)[:, looks - 1]; cb = np.cumsum(xb, axis=1)[:, looks - 1]     # compliant counts (x^2 = x)
        ma = ca / n; mb = cb / n
        va = (ca - n * ma**2) / (n - 1); vb = (cb - n * mb**2) / (n - 1)
        U = ma - mb; V = va / n + vb / n                                                        # as hierarchical_prefix_stats
        nonc_a = (looks[None, :] - ca).astype(int); nonc_b = (looks[None, :] - cb).astype(int)
        rules = {}
        # projection-Gaussian asymptotic CS, 199 looks (as run_ustat_reference.decisions)
        sig = np.sqrt(np.maximum(V, 0) * looks[None, :]); lower = U - sig * cs_u[None, :] / looks[None, :]
        rules[ASYMPCS] = ((lower > C) & (V > 0), V, lower, np.full(K, C), 'CS lower bound vs threshold')
        # fixed Wald and group-sequential all-pairs
        z = US.zstat(U, V, C)
        now = np.zeros((b, K), bool); now[:, -1] = z[:, -1] > norm.ppf(1 - ALPHA)
        rules['allpairs_fixed_wald'] = (now, V, z, np.full(K, norm.ppf(1 - ALPHA)), 'z vs boundary')
        for kind, cvec in bounds.items():
            now = np.zeros((b, K), bool); now[:, group_idx] = z[:, group_idx] >= cvec[None, :]
            bd = np.full(K, np.nan); bd[group_idx] = cvec
            rules[f'allpairs_gs_{kind}'] = (now, V, z, bd, 'z vs boundary')
        # disjoint-pair rules on ds (as run_ustat_reference.decisions)
        ds = raw['ds']
        pos = np.cumsum(ds > 0, axis=1)[:, looks - 1]; neg = np.cumsum(ds < 0, axis=1)[:, looks - 1]
        means = (pos - neg) / looks
        s2 = np.maximum((pos + neg - looks * means**2) / (looks - 1), 0); Vd = s2 / looks
        zd = US.zstat(means, np.sqrt(Vd)**2, C)
        now = np.zeros((b, K), bool); now[:, group_idx] = zd[:, group_idx] >= bounds['obf'][None, :]
        bd = np.full(K, np.nan); bd[group_idx] = bounds['obf']
        rules['disjoint_gs_obf'] = (now, Vd, zd, bd, 'z vs boundary')
        loge = betting_log_e_ternary(pos, neg, looks, C)
        rules['disjoint_betting'] = (loge >= np.log(1 / ALPHA), Vd, loge, np.full(K, np.log(1 / ALPHA)), 'log e-value vs log(1/alpha)')
        for rule, (now, var, stat, bd, stat_kind) in rules.items():
            hit, k = first_cross(now)
            counts[rule] = counts.get(rule, 0) + int(hit.sum())
            for r in np.flatnonzero(hit):
                kk = k[r]
                rows.append(dict(scenario=SCENARIO, rule=rule, event='false rejection of the component compliance gate (first crossing)',
                                 replicate=begin + int(r), first_crossing_runs_per_arm=int(looks[kk]),
                                 noncompliant_a=int(nonc_a[r, kk]), noncompliant_b=int(nonc_b[r, kk]),
                                 u_compliance=float(U[r, kk]), variance_estimate=float(var[r, kk]),
                                 statistic=float(stat[r, kk]), boundary=float(bd[kk]), statistic_kind=stat_kind))
    # consistency with the archived calibration file
    cal = {}
    cal_path = out_dir / 'null_calibration.csv'
    if cal_path.exists():
        with cal_path.open() as fh:
            for r in csv.DictReader(fh):
                if r['scenario'] == SCENARIO and r['method'].startswith('gate_compliance_'):
                    cal[r['method'][len('gate_compliance_'):]] = int(r['deployments'])
    match = {rule: (counts[rule], cal.get(rule)) for rule in counts}
    full = args.replicates == 10000 and args.pairs == 10000 and args.batch == 25 and args.seed == 20260918
    if full and cal:
        bad = {k: v for k, v in match.items() if v[0] != v[1]}
        if bad: raise AssertionError(f'compliance-gate counts differ from null_calibration.csv: {bad}')
    rows.sort(key=lambda r: (r['rule'], r['replicate']))
    with (out_dir / 'rare_event_diagnostic.csv').open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summary = {}
    for rule in counts:
        rr = [r for r in rows if r['rule'] == rule]
        fc = np.array([r['first_crossing_runs_per_arm'] for r in rr]); na = np.array([r['noncompliant_a'] for r in rr]); nb = np.array([r['noncompliant_b'] for r in rr])
        lo, hi = US.wilson(len(rr), args.replicates)
        summary[rule] = dict(false_rejections=len(rr), replicates=args.replicates, rate=len(rr) / args.replicates, wilson95=[float(lo), float(hi)],
                             first_crossing_quantiles_10_25_50_75_90=np.quantile(fc, [.1, .25, .5, .75, .9]).tolist(),
                             count_first_crossing_le_500=int((fc <= 500).sum()), share_first_crossing_le_500=float((fc <= 500).mean()),
                             count_first_crossing_le_1000=int((fc <= 1000).sum()), share_first_crossing_le_1000=float((fc <= 1000).mean()),
                             count_zero_noncompliant_a=int((na == 0).sum()), count_zero_noncompliant_b=int((nb == 0).sum()),
                             median_noncompliant_a=float(np.median(na)), median_noncompliant_b=float(np.median(nb)),
                             median_variance_estimate=float(np.median([r['variance_estimate'] for r in rr])))
    (out_dir / 'rare_event_diagnostic_manifest.json').write_text(json.dumps(dict(
        purpose='Archive of the Section 4.7 first-crossing / rare-event diagnostic (component compliance gate, compliance_boundary only)',
        arguments=vars(args), scenario=SCENARIO, params=PARAMS, threshold=C, alpha=ALPHA,
        seeds=dict(convention='numpy SeedSequence([seed, 100 + index]) as run_ustat_reference.py --calibration-only', seed=args.seed, index=SEED_INDEX,
                   entropy=[args.seed, 100 + SEED_INDEX], batch=args.batch),
        event='component compliance-gate false rejection (convention-free); not a guarded deployment',
        counts_vs_null_calibration={k: dict(diagnostic=v[0], null_calibration_csv=v[1], identical=v[0] == v[1]) for k, v in match.items()},
        summary=summary, rows_written=len(rows), seconds=time.time() - t0, workers=1,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        source_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ('rare_event_diagnostic.py', 'ustat.py', 'run_ustat_reference.py')},
        upstream_sha256={'src/winstats.py': hashlib.sha256((ROOT / 'src' / 'winstats.py').read_bytes()).hexdigest()},
        output_sha256={'rare_event_diagnostic.csv': hashlib.sha256((out_dir / 'rare_event_diagnostic.csv').read_bytes()).hexdigest()},
        python=platform.python_version(), numpy=np.__version__, platform=platform.platform(), cpu_count=os.cpu_count(), machine=platform.machine()),
        indent=2, default=float))
    print(json.dumps({k: dict(n=v['false_rejections'], q=v['first_crossing_quantiles_10_25_50_75_90'], le500=v['share_first_crossing_le_500'],
                              le1000=v['share_first_crossing_le_1000'], zeroA=v['count_zero_noncompliant_a'],
                              medA=v['median_noncompliant_a'], medB=v['median_noncompliant_b']) for k, v in summary.items()}, indent=1))
    print('done', f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
