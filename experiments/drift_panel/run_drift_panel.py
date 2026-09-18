"""Focused drift / unequal-law-null panel for the guarded monitoring rules.

Synthetic CPU-only Monte Carlo. No model or API calls. The frozen plan is
experiments/drift_panel/protocol.md; its sha256 is recorded in the manifest
and the run aborts if --protocol-sha256 does not match the file on disk.

Modes
  --design-check   deterministic target paths only (no random numbers drawn)
  (default)        full panel: MC target verification, sequential cells,
                   fixed-sample permutation cells, csv/manifest/log/figures
"""
import argparse, csv, hashlib, json, os, platform, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import norm, rankdata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from winstats import normal_mixture_radius, betting_log_e_ternary, compare, Tier  # noqa: E402

SEED = 20260919 + (1 if os.environ.get('DRIFT_SMOKE_DIR') else 0)   # smoke tests never touch the real streams
N = 10000
ALPHA = .05
THRESHOLDS = np.array([0., -.03, -.01])      # net benefit, success, compliance
GATES = ['net_benefit', 'success', 'compliance']
VIOL_TOL = 1e-9                              # "at or below threshold" tolerance
CHUNK = 500                                  # replicates per seeded chunk
BATCH = 25                                   # replicates per array batch
LOOKS = np.unique(np.r_[np.arange(100, N + 1, 50), N, np.arange(1, 11) * (N // 10)])
T = np.arange(1, N + 1, dtype=float)
OUT = ROOT / 'results' / 'drift_panel'

# ---------------------------------------------------------------- exact targets

def resource_pref(mu, sigma, tol):
    """P(A cheaper beyond tolerance) - P(B cheaper beyond tolerance).

    cost_A = r*c_t*LN(0,sigma), cost_B = c_t*LN(0,sigma), mu = log r.
    A wins iff cost_A < (1-tol)*cost_B.
    """
    a = np.log1p(-tol); sd = np.sqrt(2.) * sigma
    return norm.cdf((a - mu) / sd) - norm.cdf((a + mu) / sd)


def exact_targets(sa, sb, pa, pb, mu, sigma, tol):
    agree = sa * sb + (1 - sa) * (1 - sb)
    nb = (sa - sb) + agree * (pa - pb) + sa * sb * pa * pb * resource_pref(mu, sigma, tol)
    return np.stack(np.broadcast_arrays(nb, pa - pb, sa - sb))


def solve_mu(nb_target, sa, sb, pa, pb, sigma, tol):
    """Vectorised bisection for mu=log r giving exactly the requested nb_t."""
    sa, sb, pa, pb, sigma, nb_target = np.broadcast_arrays(sa, sb, pa, pb, sigma, nb_target)
    agree = sa * sb + (1 - sa) * (1 - sb)
    need = (nb_target - (sa - sb) - agree * (pa - pb)) / (sa * sb * pa * pb)
    if np.any(np.abs(need) > .98):
        raise ValueError('requested net benefit infeasible')
    lo = np.full(need.shape, -12.); hi = np.full(need.shape, 12.)
    for _ in range(200):
        mid = (lo + hi) / 2
        above = resource_pref(mid, sigma, tol) > need   # decreasing in mu
        lo = np.where(above, mid, lo); hi = np.where(above, hi, mid)
    return (lo + hi) / 2


def blocks(edges, values):
    """Piecewise-constant path: values[k] for edges[k] < t <= edges[k+1]."""
    out = np.empty(N)
    for k, v in enumerate(values):
        out[edges[k]:edges[k + 1]] = v
    return out

# ---------------------------------------------------------------- scenarios

def common_drift():
    p = .75 + .10 * np.sin(2 * np.pi * T / 2000) - .10 * (T > 5000)
    s = .990 + .005 * np.sin(2 * np.pi * T / 2500)
    sigma = .45 * (1 + .3 * np.sin(2 * np.pi * T / 3000))
    scale = np.exp(.5 * np.sin(2 * np.pi * T / 2500)) * (1 + (T > 5000))
    return p, s, sigma, scale


def build_scenarios():
    S = {}
    p, s, sigma, scale = common_drift()
    one = np.ones(N)

    def add(name, family, kind, reps, sa, sb, pa, pb, mu, sigma_, tol=.05, scale_=None, note=''):
        S[name] = dict(family=family, kind=kind, reps=reps, sa=sa * one, sb=sb * one, pa=pa * one,
                       pb=pb * one, mu=mu * one, sigma=sigma_ * one, tol=tol,
                       scale=(one if scale_ is None else scale_), note=note)

    # (A) common drift: both arms share p_t, s_t, sigma_t, cost scale
    add('A1_identical_null', 'A', 'null', 10000, s, s, p, p, 0., sigma, scale_=scale)
    add('A2_success_boundary', 'A', 'null', 10000, s, s, p - .03, p, np.log(.4), sigma, scale_=scale)
    add('A3_compliance_boundary', 'A', 'null', 10000, s - .01, s, p, p, np.log(.4), sigma, scale_=scale)
    add('A4_constant_nb_0p10', 'A', 'power', 2000, s, s, p, p,
        solve_mu(.10, s, s, p, p, sigma, .05), sigma, scale_=scale)
    add('A5_joint_gain', 'A', 'power', 2000, s, s, p + .05, p, np.log(.75), sigma, scale_=scale)
    add('A6_strong_all_gates', 'A', 'power', 2000, s, s - .07, p + .10, p, np.log(.55), sigma, scale_=scale)

    # (B) treatment-by-time drift; stationary baseline sb=.90, pb=.75, sigma=.45
    sb, pb, sg = .90, .75, .45
    e = [0, 3000, N]
    for name, levels in [('B1_nb_pos_then_neg', [.2, -.2]), ('B2_nb_neg_then_pos', [-.2, .2])]:
        nb = blocks(e, levels)
        add(name, 'B', 'drift', 10000, .98, sb, .85, pb, solve_mu(nb, .98, sb, .85, pb, sg, .05), sg)
    # B3a: violator nb+success -> success -> compliance, always at the exact boundary
    e = [0, 2000, 4000, N]
    nb = blocks(e, [0., .2, .2]); dq = blocks(e, [-.03, -.03, .15]); ds = blocks(e, [.08, -.10, -.01])
    add('B3a_alternating_violator', 'B', 'drift', 10000, sb + ds, sb, pb + dq, pb,
        solve_mu(nb, sb + ds, sb, pb + dq, pb, sg, .05), sg)
    # B3b: nb+success -> success -> compliance -> compliance+nb -> nb
    e = [0, 500, 1000, 5000, 8000, N]
    nb = blocks(e, [0., .2, .2, -.3, 0.]); dq = blocks(e, [-.03, -.03, .15, .15, .15])
    ds = blocks(e, [.08, -.10, -.01, -.01, .08])
    add('B3b_cycling_violator', 'B', 'drift', 10000, sb + ds, sb, pb + dq, pb,
        solve_mu(nb, sb + ds, sb, pb + dq, pb, sg, .05), sg)

    # (C) unequal laws, theta = 0 exactly; pa in closed form given r
    def pa_closed(sA, sB, pB, r, sigma_, tol):
        agree = sA * sB + (1 - sA) * (1 - sB)
        rp = resource_pref(np.log(r), sigma_, tol)
        return agree * pB / (agree + sA * sB * pB * rp)
    pa1 = pa_closed(.995, .995, .75, 1.10, .45, .05)
    add('C1_unequal_law_null', 'C', 'null', 10000, .995, .995, pa1, .75, np.log(1.10), .45)
    pa2 = pa_closed(.995, .995, .10, 1.50, .45, .50)
    add('C2_unequal_law_null_tie_heavy', 'C', 'null', 10000, .995, .995, pa2, .10, np.log(1.50), .45, tol=.50)
    for sc in S.values():
        for k in ('sa', 'sb', 'pa', 'pb'):
            if sc[k].min() < 0 or sc[k].max() > 1:
                raise ValueError('probability outside [0,1]')
        sc['step'] = exact_targets(sc['sa'], sc['sb'], sc['pa'], sc['pb'], sc['mu'], sc['sigma'], sc['tol'])
        sc['running'] = np.cumsum(sc['step'], axis=1) / T
        sc['viol_gate'] = sc['running'][:, LOOKS - 1] <= THRESHOLDS[:, None] + VIOL_TOL   # (3, looks)
        sc['viol'] = sc['viol_gate'].any(axis=0)
        sc['cur_gate'] = sc['step'][:, LOOKS - 1] <= THRESHOLDS[:, None] + VIOL_TOL
        sc['cond_null_all_t'] = bool(((sc['step'] <= THRESHOLDS[:, None] + VIOL_TOL).all(axis=1)).any())
    return S

# ---------------------------------------------------------------- data

def generate(rng, b, sc):
    sh = (b, N)
    safe_a = rng.random(sh) < sc['sa']; safe_b = rng.random(sh) < sc['sb']
    suc_a = rng.random(sh) < sc['pa']; suc_b = rng.random(sh) < sc['pb']
    la = sc['mu'] + sc['sigma'] * rng.standard_normal(sh)     # log cost minus common log scale
    lb = sc['sigma'] * rng.standard_normal(sh)
    ds = safe_a.astype(np.int8) - safe_b.astype(np.int8)
    dq = suc_a.astype(np.int8) - suc_b.astype(np.int8)
    z = ds.copy(); tied = ds == 0; z[tied] = dq[tied]
    elig = tied & safe_a & safe_b & suc_a & suc_b
    a = np.log1p(-sc['tol'])
    # |ca-cb| > tol*max(ca,cb)  <=>  |la-lb| > -log(1-tol); the common scale cancels
    d = lb - la
    res = elig & (np.abs(d) > -a)
    z[res] = np.sign(d[res]).astype(np.int8)
    return z, dq, ds


def rule_masks(zs):
    """Boolean (batch, looks) 'deployment condition holds at this look' per rule."""
    e1, e3, c1, c3, w, g, f = [], [], [], [], [], [], []
    a3 = ALPHA / 3
    for z, c in zip(zs, THRESHOLDS):
        pos = np.cumsum(z > 0, axis=1)[:, LOOKS - 1]; neg = np.cumsum(z < 0, axis=1)[:, LOOKS - 1]
        m = (pos - neg) / LOOKS
        se = np.sqrt(np.maximum((pos + neg - LOOKS * m ** 2) / (LOOKS - 1), 0) / LOOKS)
        le = betting_log_e_ternary(pos, neg, LOOKS, c)
        e1.append(le >= np.log(1 / ALPHA)); e3.append(le >= np.log(1 / a3))
        c1.append(m - normal_mixture_radius(LOOKS, ALPHA) > c)
        c3.append(m - normal_mixture_radius(LOOKS, a3) > c)
        w.append(m - norm.ppf(1 - ALPHA) * se > c)
        g.append(m - norm.ppf(1 - ALPHA / 10) * se > c)
    gm = np.isin(LOOKS, np.arange(1, 11) * (N // 10))
    AND = np.logical_and.reduce
    fixed = np.zeros_like(e1[0]); fixed[:, -1] = AND(w)[:, -1]
    return {'win_only_betting': e1[0], 'win_only_normal_mixture': c1[0],
            'guarded_betting': AND(e1), 'guarded_betting_split': AND(e3),
            'guarded_normal_mixture': AND(c1), 'guarded_normal_mixture_split': AND(c3),
            'guarded_repeated_wald': AND(w), 'guarded_group_bonferroni_wald': AND(g) & gm,
            'guarded_fixed_wald': fixed}

RULES = ['win_only_betting', 'win_only_normal_mixture', 'guarded_betting', 'guarded_betting_split',
         'guarded_normal_mixture', 'guarded_normal_mixture_split', 'guarded_repeated_wald',
         'guarded_group_bonferroni_wald', 'guarded_fixed_wald']


def viol_for(rule, sc):
    """Win-only rules make only the net-benefit claim; guarded rules the conjunction."""
    return sc['viol_gate'][0] if rule.startswith('win_only') else sc['viol']


def run_chunk(args):
    name, chunk_index, reps = args
    sc = build_scenarios()[name]
    idx = list(build_scenarios()).index(name)
    child = np.random.SeedSequence([SEED, idx]).spawn(40)[chunk_index]
    rng = np.random.default_rng(child)
    acc = {r: dict(deploy=0, e_first=0, e_any=0, e_cur_first=0, stop_sum=0., stop_sq=0., stops=[]) for r in RULES}
    for begin in range(0, reps, BATCH):
        masks = rule_masks(generate(rng, min(BATCH, reps - begin), sc))
        for r, d in masks.items():
            v = viol_for(r, sc)
            cv = sc['cur_gate'][0] if r.startswith('win_only') else sc['cur_gate'].any(axis=0)
            ever = d.any(axis=1); first = np.argmax(d, axis=1)
            stops = np.where(ever, LOOKS[first], N)
            a = acc[r]
            a['deploy'] += int(ever.sum())
            a['e_first'] += int((ever & v[first]).sum())
            a['e_any'] += int((d & v[None, :]).any(axis=1).sum())
            a['e_cur_first'] += int((ever & cv[first]).sum())
            a['stop_sum'] += float(stops.sum()); a['stop_sq'] += float((stops.astype(float) ** 2).sum())
            a['stops'].extend(stops[ever].tolist())
    return name, chunk_index, acc

# ---------------------------------------------------------------- MC verification with winstats.compare

TIERS = lambda tol: [Tier('compliance'), Tier('success'), Tier('cost', higher_better=False, relative_tolerance=tol)]


def mc_verify(args):
    label, k, prm, draws = args
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 9000 + k]))
    sa, sb, pa, pb, mu, sigma, tol, scale = prm
    A = np.stack([rng.random(draws) < sa, rng.random(draws) < pa,
                  scale * np.exp(mu + sigma * rng.standard_normal(draws))], axis=-1).astype(float)
    B = np.stack([rng.random(draws) < sb, rng.random(draws) < pb,
                  scale * np.exp(sigma * rng.standard_normal(draws))], axis=-1).astype(float)
    both = (A[:, 0] == 1) & (B[:, 0] == 1) & (A[:, 1] == 1) & (B[:, 1] == 1)
    elig = np.stack([np.ones(draws, bool), np.ones(draws, bool), both], axis=-1)
    z, _ = compare(A, B, TIERS(tol), eligible=elig)
    ex = exact_targets(sa, sb, pa, pb, mu, sigma, tol)
    obs = np.array([z.mean(), (A[:, 1] - B[:, 1]).mean(), (A[:, 0] - B[:, 0]).mean()])
    se = np.array([z.std(ddof=1), (A[:, 1] - B[:, 1]).std(ddof=1), (A[:, 0] - B[:, 0]).std(ddof=1)]) / np.sqrt(draws)
    return dict(label=label, draws=draws, exact=ex.tolist(), mc=obs.tolist(), mc_se=se.tolist(),
                z=((obs - ex) / np.where(se > 0, se, np.inf)).tolist(), p_tie=float((z == 0).mean()))

# ---------------------------------------------------------------- fixed-sample permutation test (part C)

PERM_N = 500; PERM_B = 199


def perm_chunk(args):
    label, k, chunk_index, reps, prm_a, prm_b = args
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 8000 + k]).spawn(40)[chunk_index])
    n = PERM_N; rej = rej_s = rej_c = 0
    for _ in range(reps):
        suc = np.r_[rng.random(n) < prm_a[0], rng.random(n) < prm_b[0]].astype(float)
        cost = np.r_[np.exp(prm_a[1] + .45 * rng.standard_normal(n)), np.exp(.45 * rng.standard_normal(n))]
        rk = rankdata(cost)
        lab = np.zeros((PERM_B + 1, 2 * n), bool); lab[:, :n] = True
        lab[1:] = rng.permuted(lab[1:], axis=1)
        def zstat(x):
            sA = lab @ x; mean = n * x.mean(); var = n * n * x.var(ddof=1) / (2 * n)
            return np.abs(sA - mean) / np.sqrt(var) if var > 0 else np.zeros(PERM_B + 1)
        zs_, zc_ = zstat(suc), zstat(rk)
        tmax = np.maximum(zs_, zc_)
        rej += (tmax >= tmax[0] - 1e-12).sum() / (PERM_B + 1) <= ALPHA
        rej_s += (zs_ >= zs_[0] - 1e-12).sum() / (PERM_B + 1) <= ALPHA
        rej_c += (zc_ >= zc_[0] - 1e-12).sum() / (PERM_B + 1) <= ALPHA
    return label, reps, int(rej), int(rej_s), int(rej_c)

# ---------------------------------------------------------------- helpers

def wilson(k, n):
    z = norm.ppf(.975); p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(c - r, 0.), min(c + r, 1.)


def design_summary(S):
    out = {}
    for name, sc in S.items():
        vg = sc['viol_gate']
        segs = []
        for j in range(3):
            idx = np.flatnonzero(vg[j])
            if idx.size:
                cuts = np.flatnonzero(np.diff(idx) > 1)
                starts = np.r_[idx[0], idx[cuts + 1]]; ends = np.r_[idx[cuts], idx[-1]]
                segs.append({GATES[j]: [[int(LOOKS[a]), int(LOOKS[b])] for a, b in zip(starts, ends)]})
        out[name] = dict(family=sc['family'], kind=sc['kind'], replicates=sc['reps'], cost_tolerance=sc['tol'],
            step_target_min=sc['step'].min(axis=1).tolist(), step_target_max=sc['step'].max(axis=1).tolist(),
            running_target_at_final_look=sc['running'][:, -1].tolist(),
            cost_ratio_range=[float(np.exp(sc['mu'].min())), float(np.exp(sc['mu'].max()))],
            looks_with_any_running_violation=int(sc['viol'].sum()), total_looks=int(LOOKS.size),
            conditional_null_of_one_fixed_gate_holds_at_every_step=sc['cond_null_all_t'],
            running_violation_look_ranges=segs)
    return out

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--design-check', action='store_true')
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--protocol-sha256', default=None)
    ap.add_argument('--smoke', action='store_true', help='tiny run into scratch dir; not a result')
    args = ap.parse_args()
    if args.workers > 5:
        raise ValueError('at most 5 workers')
    S = build_scenarios()
    if args.design_check:
        print(json.dumps(design_summary(S), indent=1)); return
    proto = Path(__file__).with_name('protocol.md')
    proto_hash = hashlib.sha256(proto.read_bytes()).hexdigest()
    if bool(os.environ.get('DRIFT_SMOKE_DIR')) != args.smoke:
        raise SystemExit('DRIFT_SMOKE_DIR must be set exactly when --smoke is used')
    if not args.smoke and args.protocol_sha256 != proto_hash:
        raise SystemExit(f'protocol hash mismatch: file {proto_hash}')
    out = OUT if not args.smoke else Path(os.environ['DRIFT_SMOKE_DIR'])
    (out / 'figures').mkdir(parents=True, exist_ok=True)
    log = (out / 'run.log').open('w')
    def say(*a):
        msg = time.strftime('%Y-%m-%dT%H:%M:%S ') + ' '.join(str(x) for x in a)
        print(msg, flush=True); log.write(msg + '\n'); log.flush()
    start = time.time()
    say('protocol sha256', proto_hash, 'workers', args.workers, 'smoke', args.smoke)
    names = list(S)

    # 1. MC verification of exact targets through winstats.compare
    draws = 10 ** 6 if not args.smoke else 10 ** 4
    jobs = []; k = 0
    for name, sc in S.items():
        if sc['family'] == 'A':
            ts = [0, 1999, 4999, 5000, 9999]
        else:
            key = np.stack([sc[q] for q in ('sa', 'pa', 'mu')]); ts = list(np.unique(key, axis=1, return_index=True)[1])
        for t in sorted(int(x) for x in ts):
            prm = tuple(float(sc[q][t]) for q in ('sa', 'sb', 'pa', 'pb', 'mu', 'sigma')) + (sc['tol'], float(sc['scale'][t]))
            jobs.append((f'{name}@t={t + 1}', k, prm, draws)); k += 1
    with ProcessPoolExecutor(args.workers) as ex:
        verif = list(ex.map(mc_verify, jobs))
    worst = max(abs(z) for v in verif for z in v['z'] if np.isfinite(z))
    say('target verification:', len(verif), 'parameter sets x', draws, 'draws; max |z| =', round(worst, 3))
    for v in verif:
        if v['label'].startswith('C'):
            say(' ', v['label'], 'exact nb', v['exact'][0], 'mc nb', v['mc'][0], 'se', v['mc_se'][0], 'p_tie', v['p_tie'])

    # 2. sequential cells
    jobs = []
    for name, sc in S.items():
        reps = sc['reps'] if not args.smoke else 50
        for ci, b in enumerate(range(0, reps, CHUNK)):
            jobs.append((name, ci, min(CHUNK, reps - b)))
    merged = {n: {r: dict(deploy=0, e_first=0, e_any=0, e_cur_first=0, stop_sum=0., stop_sq=0., stops=[]) for r in RULES} for n in names}
    done = {n: 0 for n in names}
    with ProcessPoolExecutor(args.workers) as ex:
        for name, ci, acc in ex.map(run_chunk, jobs):
            for r in RULES:
                for q, v in acc[r].items():
                    if q == 'stops': merged[name][r][q].extend(v)
                    else: merged[name][r][q] += v
            done[name] += 1
            say('chunk', name, ci, 'elapsed', round(time.time() - start, 1))
    rows = []
    for name, sc in S.items():
        reps = sc['reps'] if not args.smoke else 50
        for r in RULES:
            a = merged[name][r]; m = a['stop_sum'] / reps
            row = dict(scenario=name, family=sc['family'], cell_kind=sc['kind'], rule=r, replicates=reps, max_pairs=N,
                       final_running_net_benefit=sc['running'][0, -1], final_running_success_diff=sc['running'][1, -1],
                       final_running_compliance_diff=sc['running'][2, -1],
                       fixed_gate_conditional_null_every_step=sc['cond_null_all_t'],
                       looks_with_running_violation=int(viol_for(r, sc).sum()), total_looks=int(LOOKS.size))
            for key, lab in [('deploy', 'ever_deploy'), ('e_first', 'E_running_first'), ('e_any', 'E_running_any'),
                             ('e_cur_first', 'E_current_first')]:
                lo, hi = wilson(a[key], reps)
                row.update({f'{lab}_count': a[key], f'{lab}_rate': a[key] / reps, f'{lab}_lo': lo, f'{lab}_hi': hi})
            row.update(mean_pairs_used=m, mean_pairs_mcse=float(np.sqrt(max(a['stop_sq'] / reps - m * m, 0) / reps)),
                       mean_executions_used=2 * m,
                       median_pairs_among_deployments=float(np.median(a['stops'])) if a['stops'] else '')
            rows.append(row)
        say(name, {r: (merged[name][r]['deploy'], merged[name][r]['e_any']) for r in RULES})
    with (out / 'results.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    # 3. permutation cells
    c1, c2 = S['C1_unequal_law_null'], S['C2_unequal_law_null_tie_heavy']
    pcells = [('C0_equal_law_perm_calibration', 0, 10000, (.75, 0.), (.75, 0.)),
              ('C1_unequal_law_null', 1, 2000, (float(c1['pa'][0]), float(c1['mu'][0])), (.75, 0.)),
              ('C2_unequal_law_null_tie_heavy', 2, 2000, (float(c2['pa'][0]), float(c2['mu'][0])), (.10, 0.))]
    jobs = []
    for label, k, reps, pa_, pb_ in pcells:
        reps = reps if not args.smoke else 40
        for ci, b in enumerate(range(0, reps, CHUNK)):
            jobs.append((label, k, ci, min(CHUNK, reps - b), pa_, pb_))
    pm = {}
    with ProcessPoolExecutor(args.workers) as ex:
        for label, reps, a, b, c in ex.map(perm_chunk, jobs):
            q = pm.setdefault(label, [0, 0, 0, 0]); q[0] += reps; q[1] += a; q[2] += b; q[3] += c
    prow = []
    for label, (reps, a, b, c) in pm.items():
        for stat, kk in [('perm_max_success_costrank', a), ('perm_success_only', b), ('perm_costrank_only', c)]:
            lo, hi = wilson(kk, reps)
            prow.append(dict(cell=label, test=stat, pairs=PERM_N, permutations=PERM_B, replicates=reps,
                             rejections=kk, rejection_rate=kk / reps, lo=lo, hi=hi))
    with (out / 'permutation_results.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=prow[0].keys()); w.writeheader(); w.writerows(prow)
    say('permutation', pm)

    seconds = time.time() - start
    manifest = dict(protocol_sha256=proto_hash, seed=SEED, seed_rule='SeedSequence([20260919, scenario_index]).spawn(40)[chunk]; '
                    'verification SeedSequence([20260919, 9000+k]); permutation SeedSequence([20260919, 8000+k]).spawn(40)[chunk]',
                    scenario_index={n: i for i, n in enumerate(names)}, alpha=ALPHA, split_alpha=ALPHA / 3,
                    thresholds=THRESHOLDS.tolist(), looks=LOOKS.tolist(), max_pairs=N, max_executions=2 * N, chunk=CHUNK,
                    batch=BATCH, workers=args.workers, violation_tolerance=VIOL_TOL, design=design_summary(S),
                    target_verification=verif, target_verification_max_abs_z=worst, permutation=dict(pairs=PERM_N, B=PERM_B),
                    seconds=seconds, python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                    platform=platform.platform(), smoke=args.smoke,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    core_sha256=hashlib.sha256((ROOT / 'src' / 'winstats.py').read_bytes()).hexdigest(),
                    interpretation='Synthetic independent-pair streams; not live A/B results; no model calls.')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    say('done seconds', round(seconds, 1))
    log.close()


if __name__ == '__main__':
    main()
