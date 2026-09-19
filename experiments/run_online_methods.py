"""Online monitoring study: multinomial (Dirichlet-mixture) e-process vs baselines.

Extends experiments/run_simulations.py (same six prespecified scenarios and
generator, same looks, same guardrail thresholds) with:
  * win_only_multinomial / guarded_multinomial: composite-null e-processes
    E_n = inf_{p in H0} M_n(p) from the Dirichlet-multinomial mixture
    martingale on the ternary cell counts (win/tie/loss) of each score.
  * two tie-heavy scenarios added on 2026-09-18 (labelled as extensions).
  * a confidence-sequence width comparison for net benefit.
All streams are synthetic; none are live A/B experiments.
"""
import argparse, csv, hashlib, json, platform, sys, time
from pathlib import Path
import numpy as np
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src')); sys.path.insert(0, str(ROOT / 'experiments'))
from winstats import normal_mixture_radius, betting_log_e_ternary
from wincs import ternary_log_eprocess_nb, MultinomialCS
from run_simulations import SCENARIOS as BASE_SCENARIOS, generate, exact_targets, wilson

SCENARIOS = dict(BASE_SCENARIOS)
SCENARIOS.update({
    'tie_heavy_null': (.995, .995, .30, .30, 1.),      # both fail ~49%: absorbing ties
    'tie_heavy_efficiency': (.995, .995, .30, .30, .55),
})
THRESHOLDS = [0., -.03, -.01]
PRIOR = (1., 1., 1.)


def evaluate(zs, looks, alpha):
    all_e, all_m, all_normal, all_z, all_fixed, all_group = [], [], [], [], [], []
    for z, c in zip(zs, THRESHOLDS):
        pos = np.cumsum(z > 0, axis=1)[:, looks - 1]
        neg = np.cumsum(z < 0, axis=1)[:, looks - 1]
        tie = looks - pos - neg
        means = (pos - neg) / looks
        s2 = np.maximum((pos + neg - looks * means**2) / (looks - 1), 0)
        se = np.sqrt(s2 / looks)
        all_e.append(betting_log_e_ternary(pos, neg, looks, c) >= np.log(1 / alpha))
        all_m.append(ternary_log_eprocess_nb(pos, tie, neg, c, PRIOR) >= np.log(1 / alpha))
        all_normal.append(means - normal_mixture_radius(looks, alpha) > c)
        all_z.append(means - norm.ppf(1 - alpha) * se > c)
        all_fixed.append(means[:, -1] - norm.ppf(1 - alpha) * se[:, -1] > c)
        all_group.append(means - norm.ppf(1 - alpha / 10) * se > c)
    group_mask = np.isin(looks, np.arange(1, 11) * (looks[-1] // 10))
    out = {
        'win_only_betting': all_e[0],
        'win_only_multinomial': all_m[0],
        'guarded_betting': np.logical_and.reduce(all_e),
        'guarded_multinomial': np.logical_and.reduce(all_m),
        'guarded_normal_mixture': np.logical_and.reduce(all_normal),
        'guarded_repeated_wald': np.logical_and.reduce(all_z),
        'guarded_group_bonferroni_wald': np.logical_and.reduce(all_group) & group_mask,
    }
    fixed = np.zeros_like(all_e[0]); fixed[:, -1] = np.logical_and.reduce(all_fixed)
    out['guarded_fixed_wald'] = fixed
    return out


def betting_cs_ternary(z, ms, bets=40, delta=0.05):
    """Two-sided hedged mixture-betting CS for the mean of scores in [-1,1].

    Fixed geometric grid of stakes (prespecified), equal weights; for each
    candidate mean m the hedged capital is (K+ + K-)/2 ; CS = {m: capital < 1/delta}.
    z: (reps, n) scores; ms: candidate means grid. Returns (lower, upper) per rep.
    """
    lam = np.geomspace(1e-4, .5, bets)  # stakes in units where |z-m|<=2 => lam<0.5 keeps 1+lam(z-m)>0
    reps, n = z.shape
    lo = np.full(reps, -1.); hi = np.full(reps, 1.)
    # log K+(m) = logsumexp_lam sum_i log(1+lam(z_i-m)) - log(bets); K-(m) uses -lam
    from scipy.special import logsumexp
    pos = (z > 0).sum(1); neg = (z < 0).sum(1); tie = n - pos - neg
    inside = np.zeros((reps, ms.size), bool)
    for j, m in enumerate(ms):
        # counts-based since z ternary: log(1+lam(1-m)), log(1+lam(0-m)), log(1+lam(-1-m))
        def logK(l):
            with np.errstate(invalid='ignore', divide='ignore'):
                lk = (pos[:, None] * np.log1p(l * (1 - m)) + tie[:, None] * np.log1p(l * (0 - m))
                      + neg[:, None] * np.log1p(l * (-1 - m)))
            return logsumexp(lk, axis=1) - np.log(bets)
        cap = np.logaddexp(logK(lam), logK(-lam)) - np.log(2)  # hedged capital (theta=1/2), level delta
        inside[:, j] = cap < np.log(1 / delta)
    for r in range(reps):
        idx = np.where(inside[r])[0]
        if idx.size:
            lo[r], hi[r] = ms[idx[0]], ms[idx[-1]]
        else:
            lo[r], hi[r] = np.nan, np.nan
    return lo, hi


def width_study(rng, reps, ns, delta=0.05):
    rows = []
    params = SCENARIOS['efficiency_gain']  # nb ~ .36, moderate ties
    z = generate(rng, (reps, max(ns)), params)[0]
    cs = MultinomialCS(1, delta, 1.0)
    ms = np.linspace(-1, 1, 801)
    for n in ns:
        pos = (z[:, :n] > 0).sum(1); neg = (z[:, :n] < 0).sum(1); tie = n - pos - neg
        counts = np.stack([tie, pos, neg], 1).astype(float)
        w_multi = np.array([np.diff(cs.net_benefit(c))[0] for c in counts])
        w_norm = 2 * normal_mixture_radius(n, delta) * np.ones(reps)
        lo, hi = betting_cs_ternary(z[:, :n], ms, delta=delta)
        w_bet = hi - lo
        w_fixed = 2 * norm.ppf(1 - delta / 2) * np.sqrt(np.maximum(((pos + neg) / n - ((pos - neg) / n)**2), 0) / n)
        for name, w in [('multinomial_dirichlet_cs', w_multi), ('normal_mixture_cs', w_norm), ('betting_mixture_cs', w_bet), ('fixed_wald_ci_invalid_sequentially', w_fixed)]:
            rows.append(dict(n_pairs=n, method=name, mean_width=float(np.nanmean(w)), width_mcse=float(np.nanstd(w) / np.sqrt(reps)), replicates=reps))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--replicates', type=int, default=2000)
    ap.add_argument('--pairs', type=int, default=10000)
    ap.add_argument('--batch', type=int, default=25)
    ap.add_argument('--seed', type=int, default=20260918)
    ap.add_argument('--width-replicates', type=int, default=200)
    args = ap.parse_args(); start = time.time()
    looks = np.unique(np.r_[np.arange(100, args.pairs + 1, 50), args.pairs, np.arange(1, 11) * (args.pairs // 10)])
    rows = []; alpha = .05
    for j, (name, params) in enumerate(SCENARIOS.items()):
        rng = np.random.default_rng(np.random.SeedSequence([args.seed, j]))
        accum = {}; targets = exact_targets(params)
        admissible = all(x > c for x, c in zip(targets, THRESHOLDS))
        for begin in range(0, args.replicates, args.batch):
            batch = min(args.batch, args.replicates - begin)
            decisions = evaluate(generate(rng, (batch, args.pairs), params), looks, alpha)
            for method, d in decisions.items():
                success = d.any(axis=1)
                stops = np.where(success, looks[np.argmax(d, axis=1)], args.pairs)
                acc = accum.setdefault(method, {'deploy': 0, 'stop_sum': 0., 'stop_sq': 0., 'positive_stop': []})
                acc['deploy'] += int(success.sum()); acc['stop_sum'] += float(stops.sum())
                acc['stop_sq'] += float((stops.astype(float)**2).sum())
                acc['positive_stop'].extend(stops[success].tolist())
        for method, acc in accum.items():
            low, high = wilson(acc['deploy'], args.replicates)
            m = acc['stop_sum'] / args.replicates
            rows.append(dict(scenario=name, method=method, replicates=args.replicates, max_pairs=args.pairs,
                             true_net_benefit=targets[0], true_success_difference=targets[1], true_safety_difference=targets[2],
                             admissible=admissible, deployments=acc['deploy'], deployment_rate=acc['deploy'] / args.replicates,
                             rate_ci_lower=low, rate_ci_upper=high, mean_pairs_used=m,
                             mean_pairs_mcse=np.sqrt(max(acc['stop_sq'] / args.replicates - m * m, 0) / args.replicates),
                             median_pairs_among_deployments=float(np.median(acc['positive_stop'])) if acc['positive_stop'] else ''))
        print(name, {k: round(v['deploy'] / args.replicates, 4) for k, v in accum.items()}, f'{time.time()-start:.0f}s', flush=True)
    with (ROOT / 'results' / 'online_methods_results.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    wrows = width_study(np.random.default_rng(np.random.SeedSequence([args.seed, 99])), args.width_replicates, [100, 250, 500, 1000, 2000, 5000, 10000], alpha)
    with (ROOT / 'results' / 'cs_width.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=wrows[0].keys()); w.writeheader(); w.writerows(wrows)
    manifest = dict(arguments=vars(args), alpha=alpha, thresholds=THRESHOLDS, dirichlet_prior=PRIOR, looks=looks.tolist(),
                    scenarios=SCENARIOS, seconds=time.time() - start, python=platform.python_version(), numpy=np.__version__,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    core_sha256={f: hashlib.sha256((ROOT / 'src' / f).read_bytes()).hexdigest() for f in ['winstats.py', 'wincs.py']},
                    interpretation='Synthetic independent-pair streams; not live A/B experiment results. tie_heavy_* scenarios were added 2026-09-18 after the first six were run.')
    (ROOT / 'results' / 'online_methods_manifest.json').write_text(json.dumps(manifest, indent=2))
    print('done', f'{time.time()-start:.0f}s')


if __name__ == '__main__':
    main()
