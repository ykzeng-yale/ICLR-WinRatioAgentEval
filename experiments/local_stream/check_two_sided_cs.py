"""Regression check for the corrected two-sided betting CS (Round 9 audit, item P1a).

POST HOC analysis-code check; no model call, no git command, CPU only.

(a) Witness (exact enumeration). For ONE fair +/-1 observation and candidate mean m = 0 the
    two one-sided mixture capitals over the prespecified stake grid are
        K+ = mean_lambda (1 + lambda z),   K- = mean_lambda (1 - lambda z).
    E max(K+, K-) = 1 + mean(lambda) > 1, so max(K+, K-) is NOT a unit-initial nonnegative
    supermartingale and thresholding it at 1/delta has no level-delta guarantee (union bound: 2 delta).
    The hedged capital (K+ + K-)/2 has expectation exactly 1 (it is a test martingale).
    The check also confirms that src/wincs.betting_log_capital_ternary IS the hedged capital.

(b) Monte Carlo time-uniform miscoverage of the corrected CS: reps >= 2000 streams of length N = 2000;
    the CS misses the true mean at time n iff the hedged log capital at the true mean is >= log(1/delta)
    (this is the definition of the inverted set); for a subset of streams the actual interval returned by
    wincs.betting_cs_ternary / win_ratio_cs_decided is also compared with the truth at every n.
    The uncorrected max rule is simulated next to it for information only.

Usage: .venv/bin/python experiments/local_stream/check_two_sided_cs.py [--reps 2000] [--n 2000] [--out results/local_stream/two_sided_cs_check.json]
Exit status 1 if any assertion fails.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from wincs import (betting_cs_ternary, betting_log_capital_bernoulli, betting_log_capital_ternary,  # noqa: E402
                   default_stakes, win_ratio_cs_decided)


def one_sided_log_capitals(pos, tie, neg, m, stakes=None):
    """log K+ and log K- separately (same formula as wincs, before hedging)."""
    lam = default_stakes() if stakes is None else np.asarray(stakes, float)
    pos = np.asarray(pos, float)[..., None]; tie = np.asarray(tie, float)[..., None]; neg = np.asarray(neg, float)[..., None]
    m = np.asarray(m, float)[..., None]

    def logk(l):
        with np.errstate(divide='ignore', invalid='ignore'):
            lk = pos * np.log1p(l * (1 - m)) + tie * np.log1p(-l * m) + neg * np.log1p(l * (-1 - m))
        return logsumexp(np.where(np.isnan(lk), -np.inf, lk), axis=-1) - np.log(lam.size)
    return logk(lam), logk(-lam)


def witness():
    lam = default_stakes()
    out = {}
    e_max = e_hedge = e_hedge_wincs = 0.0
    for z, pr in ((+1, 0.5), (-1, 0.5)):                      # exact enumeration of the fair +/-1 law
        pos, neg = (1, 0) if z > 0 else (0, 1)
        lkp, lkm = one_sided_log_capitals(pos, 0, neg, 0.0)
        kp, km = float(np.exp(lkp)), float(np.exp(lkm))
        e_max += pr * max(kp, km); e_hedge += pr * (kp + km) / 2
        e_hedge_wincs += pr * float(np.exp(betting_log_capital_ternary(pos, 0, neg, 0.0)))
        out['z=%+d' % z] = dict(K_plus=kp, K_minus=km, max=max(kp, km), hedged=(kp + km) / 2)
    out.update(mean_stake=float(lam.mean()), expected_max=e_max, expected_hedged=e_hedge, expected_wincs_capital=e_hedge_wincs,
               closed_form_expected_max=float(1 + lam.mean()))
    assert e_max > 1 + 1e-6, e_max
    assert abs(e_max - (1 + lam.mean())) < 1e-12
    assert abs(e_hedge - 1) < 1e-12, e_hedge
    assert abs(e_hedge_wincs - 1) < 1e-12, 'wincs.betting_log_capital_ternary is not the hedged capital: %r' % e_hedge_wincs
    # the same identity for the Bernoulli (decided-pair win-ratio) capital at q = 1/2
    eb = 0.5 * float(np.exp(betting_log_capital_bernoulli(1, 1, 0.5))) + 0.5 * float(np.exp(betting_log_capital_bernoulli(0, 1, 0.5)))
    out['expected_wincs_bernoulli_capital'] = eb
    assert abs(eb - 1) < 1e-12, eb
    return out


def simulate(p, reps, n, delta, seed, n_interval_check=100, chunk=250):
    """p = (p_win, p_tie, p_loss). Returns ever-miscoverage of hedged CS, of the max rule, and of the decided-pair WR CS."""
    rng = np.random.default_rng(seed)
    p = np.asarray(p, float); m_true = float(p[0] - p[2]); thr = np.log(1 / delta)
    q_true = float(p[0] / (p[0] + p[2]))
    miss_h = miss_max = miss_wr = 0; first_times = []
    disagree = 0; checked = 0
    for start in range(0, reps, chunk):
        r = min(chunk, reps - start)
        z = rng.choice([1, 0, -1], size=(r, n), p=p)
        pos = np.cumsum(z > 0, 1).astype(float); neg = np.cumsum(z < 0, 1).astype(float); tie = np.arange(1, n + 1)[None, :] - pos - neg
        lkp, lkm = one_sided_log_capitals(pos, tie, neg, np.full(pos.shape, m_true))
        hed = np.logaddexp(lkp, lkm) - np.log(2)
        # the library function must equal the hedge (guards against a silent regression to max)
        lib = betting_log_capital_ternary(pos, tie, neg, np.full(pos.shape, m_true))
        assert np.allclose(lib, hed, atol=1e-9), 'library capital differs from the hedged capital'
        mh = (hed >= thr).any(1); mm = (np.maximum(lkp, lkm) >= thr).any(1)
        miss_h += int(mh.sum()); miss_max += int(mm.sum())
        first_times += [int(np.argmax(row >= thr)) + 1 for row in hed[mh]]
        wr = betting_log_capital_bernoulli(pos, pos + neg, np.full(pos.shape, q_true))
        miss_wr += int((wr >= thr).any(1).sum())
        if checked < n_interval_check:                       # compare with the actual returned intervals
            k = min(r, n_interval_check - checked)
            lo, hi = betting_cs_ternary(pos[:k], tie[:k], neg[:k], delta)
            out = ((lo > m_true) | (hi < m_true)).any(1)
            disagree += int((out != mh[:k]).sum())
            # conservative inversion: interval miss implies capital miss; never the reverse by more than bisection width
            assert not (out & ~mh[:k]).any(), 'returned interval excludes the truth while the capital is below threshold'
            wlo, whi = win_ratio_cs_decided(pos[:k], neg[:k], delta)
            wr_true = q_true / (1 - q_true)
            wout = ((wlo > wr_true) | (whi < wr_true)).any(1)
            assert not (wout & ~(wr[:k] >= thr).any(1)).any()
            checked += k
    se = lambda x: float(np.sqrt(max(x / reps * (1 - x / reps), 1e-12) / reps))
    return dict(p_win_tie_loss=p.tolist(), true_mean=m_true, reps=reps, n=n, delta=delta, seed=seed,
                ever_miss_hedged=miss_h / reps, ever_miss_hedged_mc_se=se(miss_h),
                ever_miss_uncorrected_max_rule=miss_max / reps, ever_miss_max_mc_se=se(miss_max),
                ever_miss_wr_decided_hedged=miss_wr / reps,
                median_first_miss_time=(float(np.median(first_times)) if first_times else None),
                interval_check_streams=checked, interval_vs_capital_disagreements=disagree)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--reps', type=int, default=2000)
    ap.add_argument('--n', type=int, default=2000)
    ap.add_argument('--delta', type=float, default=0.05)
    ap.add_argument('--out', default=str(REPO / 'results/local_stream/two_sided_cs_check.json'))
    args = ap.parse_args(argv)
    if args.reps < 2000 or args.n < 2000:
        print('WARNING: the Round 9 check requires reps >= 2000 and n >= 2000', file=sys.stderr)
    t0 = time.time()
    res = dict(witness=witness(), simulations=[])
    print('witness: E max(K+,K-) = %.8f > 1;  E (K+ + K-)/2 = %.12f;  E wincs capital = %.12f' % (
        res['witness']['expected_max'], res['witness']['expected_hedged'], res['witness']['expected_wincs_capital']))
    laws = [((0.5, 0.0, 0.5), 9001),            # fair +/-1: the audit's witness law, symmetric so both tails matter
            ((0.3, 0.4, 0.3), 9002),            # symmetric with ties
            ((69 / 295, 18 / 295, 208 / 295), 9003)]  # the observed E1 proportions as a plug-in law (not a claim about the truth)
    for p, seed in laws:
        r = simulate(p, args.reps, args.n, args.delta, seed)
        res['simulations'].append(r)
        print('p=%s: ever-miss hedged %.4f (MC se %.4f) <= delta %.2f ; uncorrected max rule %.4f ; WR(decided) hedged %.4f' % (
            [round(x, 3) for x in p], r['ever_miss_hedged'], r['ever_miss_hedged_mc_se'], args.delta, r['ever_miss_uncorrected_max_rule'], r['ever_miss_wr_decided_hedged']))
        assert r['ever_miss_hedged'] <= args.delta, r
        assert r['ever_miss_wr_decided_hedged'] <= args.delta, r
    res['elapsed_s'] = time.time() - t0
    res['note'] = ('iid streams, so this checks the R2 (superpopulation) reading of protocol_addendum_round9.md; '
                   'the max-rule column is informational (its guarantee is 2*delta by the union bound).')
    Path(args.out).write_text(json.dumps(res, indent=2))
    print('all two-sided CS checks passed in %.1fs -> %s' % (res['elapsed_s'], args.out))


if __name__ == '__main__':
    main()
