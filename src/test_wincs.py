"""Tests for wincs: bounds vs brute force, time-uniform coverage, clustered CIs."""
import sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from winstats import Tier, compare
from wincs import (classify, cell_counts, cell_signs, functionals, MultinomialCS, linear_bound, ratio_bound,
                   cs_threshold, loglik, log_mixture_martingale, ternary_constrained_loglik, ternary_log_eprocess_nb,
                   task_level_scores, clustered_summary, task_bootstrap, compare_censored, pairs_for_power, nb_from_win_ratio)


def simplex_grid(m=400):
    g = np.linspace(0, 1, m + 1)
    pw, pl = np.meshgrid(g, g, indexing='ij')
    ok = pw + pl <= 1 + 1e-12
    pw, pl = pw[ok], pl[ok]
    return np.stack([pw, 1 - pw - pl, pl], -1)  # cells: win, tie, loss ordering NOT used; we map below


def test_linear_and_ratio_bounds_vs_grid():
    rng = np.random.default_rng(1)
    prior = np.ones(3); delta = 0.05
    for trial in range(6):
        n = int(rng.integers(5, 400))
        p = rng.dirichlet([2, 2, 2])
        x = rng.multinomial(n, p).astype(float)  # cells: [tie, win, loss]
        cn = cs_threshold(x, prior, delta)
        # brute-force grid on simplex
        g = np.linspace(1e-6, 1 - 1e-6, 801)
        W, L = np.meshgrid(g, g, indexing='ij'); ok = W + L < 1 - 1e-9
        W, L = W[ok], L[ok]; T = 1 - W - L
        P = np.stack([T, W, L], -1)
        inside = loglik(x, P) > cn
        assert inside.any(), 'grid found empty CS'
        nb = W - L
        lo, hi = MultinomialCS(1, delta, 1.0).net_benefit(x)
        assert lo <= nb[inside].min() + 2e-3 and lo >= nb[inside].min() - 5e-3, (lo, nb[inside].min())
        assert hi >= nb[inside].max() - 2e-3 and hi <= nb[inside].max() + 5e-3, (hi, nb[inside].max())
        wr = W / L
        rlo, rhi = MultinomialCS(1, delta, 1.0).win_ratio(x)
        gmin, gmax = wr[inside].min(), wr[inside].max()
        assert rlo <= gmin * 1.02 + 1e-3 and rlo >= gmin * 0.97 - 1e-3, (rlo, gmin)
        assert (np.isinf(rhi) and gmax > 50) or (rhi >= gmax * 0.98 - 1e-3 and rhi <= gmax * 1.03 + 1e-3), (rhi, gmax)
    print('bounds vs grid ok')


def test_time_uniform_coverage():
    """Empirical probability that the true p ever leaves the CS <= delta."""
    rng = np.random.default_rng(2); delta = 0.1; reps = 4000; N = 3000
    for p in ([0.5, 0.3, 0.2], [0.05, 0.9, 0.05], [0.2, 0.2, 0.6]):
        cells = rng.choice(3, size=(reps, N), p=p)
        onehot = np.eye(3)[cells]
        counts = np.cumsum(onehot, axis=1)
        logM = log_mixture_martingale(counts, np.array(p), np.ones(3))
        ever = (logM >= np.log(1 / delta)).any(axis=1).mean()
        se = np.sqrt(delta * (1 - delta) / reps)
        assert ever <= delta + 3 * se, (p, ever)
        print(f'  p={p}: ever-miscover rate {ever:.4f} <= delta={delta}')
    print('time-uniform coverage ok')


def test_eprocess_matches_cs():
    """Rejecting H0: NB<=c via e-process must coincide with CS lower bound > c."""
    rng = np.random.default_rng(3); delta = 0.05; prior = np.ones(3)
    for _ in range(40):
        n = int(rng.integers(3, 300)); p = rng.dirichlet([1, 1, 1])
        x = rng.multinomial(n, p).astype(float)  # [tie, win, loss]
        c = float(rng.uniform(-0.5, 0.5))
        loge = ternary_log_eprocess_nb(x[1], x[0], x[2], c, prior=(1, 1, 1))  # (win, tie, loss)
        lo, hi = MultinomialCS(1, delta, 1.0).net_benefit(x)
        reject_e = loge >= np.log(1 / delta)
        reject_cs = lo > c
        if abs(lo - c) > 1e-3:
            assert reject_e == reject_cs, (n, x, c, loge, lo)
    # closed-form constrained loglik vs numeric
    from scipy.optimize import minimize_scalar
    for _ in range(40):
        x = rng.multinomial(int(rng.integers(1, 200)), rng.dirichlet([1, 1, 1])).astype(float)
        c = float(rng.uniform(-0.6, 0.6))
        f = lambda u: -(np.where(x[1] > 0, x[1] * np.log(max(u + c, 1e-300)), 0) + np.where(x[0] > 0, x[0] * np.log(max(1 - 2 * u - c, 1e-300)), 0) + np.where(x[2] > 0, x[2] * np.log(max(u, 1e-300)), 0))
        lo_u, hi_u = max(0, -c), (1 - c) / 2
        num = -minimize_scalar(f, bounds=(lo_u, hi_u), method='bounded', options={'xatol': 1e-12}).fun
        cf = ternary_constrained_loglik(x[1], x[0], x[2], c)
        assert abs(cf - num) < 1e-6, (x, c, cf, num)
    print('e-process/CS agreement and closed form ok')


def test_offline_clustered_coverage():
    rng = np.random.default_rng(4); reps = 1500; T = 60; K = 4; cover = 0
    tiers = [Tier('success'), Tier('cost', False, relative_tolerance=0.05)]
    # truth by large simulation of the same generator
    def gen(rng, T, K):
        diff = rng.normal(0, 1.0, T)  # task difficulty shared by both systems
        pa = 1 / (1 + np.exp(-(0.3 - diff))); pb = 1 / (1 + np.exp(-(0.0 - diff)))
        A = {t: np.column_stack([rng.random(K) < pa[t], np.exp(rng.normal(0, .4, K) + 0.1 * diff[t])]) for t in range(T)}
        B = {t: np.column_stack([rng.random(K) < pb[t], np.exp(rng.normal(0.2, .4, K) + 0.1 * diff[t])]) for t in range(T)}
        return A, B
    A, B = gen(np.random.default_rng(99), 20000, 4)
    s = task_level_scores(A, B, tiers)
    truth = s['win'].mean() - s['loss'].mean()
    for _ in range(reps):
        A, B = gen(rng, T, K)
        s = task_level_scores(A, B, tiers)
        out = clustered_summary(s['win'], s['loss'])
        cover += out['nb_ci'][0] <= truth <= out['nb_ci'][1]
    rate = cover / reps
    assert 0.93 <= rate <= 0.975, rate
    print(f'offline clustered CI coverage {rate:.3f} (truth {truth:.3f}) ok')


def test_misc():
    z = compare_censored([1, 5, 3, 2], [1, 0, 1, 0], [2, 4, 3, 1], [1, 1, 1, 1])
    assert list(z) == [1, -1, 0, -1]
    z2 = compare_censored([2, 4, 3, 1], [1, 1, 1, 1], [1, 5, 3, 2], [1, 0, 1, 0])
    assert list(z2) == [-1, 1, 0, 1]
    n = pairs_for_power(0.1, 0.5)
    assert 200 < n < 400, n
    assert abs(nb_from_win_ratio(1.0, 0.3)) < 1e-12
    tiers = [Tier('a'), Tier('b', False)]
    c = classify([[1, 3.0], [0, 1.0], [1, 2.0]], [[0, 1.0], [0, 1.0], [1, 3.0]], tiers)
    assert list(c) == [1, 0, 3]
    cnt = cell_counts(c, 2); f = functionals(cnt / cnt.sum(), 2)
    assert abs(f['net_benefit'] - 2 / 3) < 1e-12 and abs(f['tier_contribution'][1] - 1 / 3) < 1e-12
    print('misc ok')


if __name__ == '__main__':
    t0 = time.time()
    test_misc(); test_linear_and_ratio_bounds_vs_grid(); test_eprocess_matches_cs(); test_time_uniform_coverage(); test_offline_clustered_coverage()
    print(f'all wincs tests passed in {time.time()-t0:.1f}s')


def test_betting_cs():
    from wincs import betting_cs_ternary, win_ratio_cs_decided, betting_log_capital_ternary
    rng = np.random.default_rng(7); delta = 0.1; reps = 1000; N = 2000
    p = [0.35, 0.4, 0.25]; nb = p[0] - p[2]; wr = p[0] / p[2]
    cells = rng.choice(3, size=(reps, N), p=p); oh = np.eye(3)[cells]; cnt = np.cumsum(oh, axis=1)
    looks = np.arange(20, N + 1, 20)
    pos = cnt[:, looks - 1, 0]; tie = cnt[:, looks - 1, 1]; neg = cnt[:, looks - 1, 2]
    lo, hi = betting_cs_ternary(pos, tie, neg, delta)
    miss = ((lo > nb) | (hi < nb)).any(1).mean()
    assert miss <= delta + 3 * np.sqrt(delta * (1 - delta) / reps), miss
    wlo, whi = win_ratio_cs_decided(pos, neg, delta)
    missw = ((wlo > wr) | (whi < wr)).any(1).mean()
    assert missw <= delta + 3 * np.sqrt(delta * (1 - delta) / reps), missw
    print(f'betting CS ever-miss {miss:.3f}, WR CS ever-miss {missw:.3f} (delta {delta}); final widths nb {np.mean(hi[:,-1]-lo[:,-1]):.3f} wr [{np.mean(wlo[:,-1]):.2f},{np.mean(whi[:,-1]):.2f}] truth {wr:.2f}')


if __name__ == '__main__':
    test_betting_cs()


def test_boundary_laws_issue4():
    """Issue #4: deterministic boundary laws and constant functionals must be exact."""
    from wincs import cs_threshold
    lo, hi = MultinomialCS(1).net_benefit([0, 3, 0]); assert hi == 1.0 and -0.66 < lo < -0.65, (lo, hi)
    assert linear_bound([2, 3, 4], [1, 1, 1], np.ones(3), .05, False) == 1.0
    assert linear_bound([2, 3, 4], [1, 1, 1], np.ones(3), .05, True) == 1.0
    lo, hi = MultinomialCS(1).net_benefit([5, 0, 0]); assert abs(lo + hi) < 1e-12 and 0 < hi < 1
    lo, hi = MultinomialCS(1).net_benefit([0, 0, 7]); assert lo == -1.0 and hi < 0.3
    wlo, whi = MultinomialCS(1).win_ratio([0, 3, 0]); assert np.isinf(whi) and 0 < wlo < 1
    wlo, whi = MultinomialCS(1).win_ratio([0, 0, 7]); assert wlo == 0.0 and whi < 2
    rng = np.random.default_rng(5); bad = 0
    g = np.linspace(0, 1, 601); W, L = np.meshgrid(g, g, indexing='ij'); ok = W + L <= 1 + 1e-12; W, L = W[ok], L[ok]; T = 1 - W - L
    P = np.stack([T, W, L], -1)
    for t in range(200):
        n = int(rng.integers(1, 80)); x = rng.multinomial(n, rng.dirichlet([.3, .3, .3])).astype(float)
        inside = loglik(x, P) >= cs_threshold(x, np.ones(3), .05); nb = W - L
        lo, hi = MultinomialCS(1, .05, 1.0).net_benefit(x)
        # bounds must contain the grid set (conservative) and be within grid resolution of it
        if not (lo <= nb[inside].min() + 1e-9 and hi >= nb[inside].max() - 1e-9 and lo >= nb[inside].min() - 4e-3 and hi <= nb[inside].max() + 4e-3):
            bad += 1
    assert bad == 0, bad
    print('boundary-law and conservativeness checks ok (issue #4)')


if __name__ == '__main__':
    test_boundary_laws_issue4()


def test_shift_equivariance_pr5():
    """PR #5 review: bounds must be shift-equivariant and conservative for huge offsets."""
    from wincs import cs_threshold
    x = np.array([2., 3., 4.]); c = 1e12 + np.array([0., 1., 2.]); prior = np.ones(3); p = np.array([.04, .12, .84])
    upper = linear_bound(x, c, prior, .05)
    assert abs(p.sum() - 1) < 1e-15 and loglik(x, p) > cs_threshold(x, prior, .05)
    assert c @ p <= upper + 1e-3, (c @ p, upper)                      # feasible point never exceeds the bound
    base_hi = linear_bound(x, c - 1e12, prior, .05); base_lo = linear_bound(x, c - 1e12, prior, .05, False)
    assert abs(upper - (base_hi + 1e12)) < 1e-3 and abs(linear_bound(x, c, prior, .05, False) - (base_lo + 1e12)) < 1e-3
    rng = np.random.default_rng(11)
    for _ in range(300):
        n = int(rng.integers(1, 200)); xx = rng.multinomial(n, rng.dirichlet([.5, .5, .5])).astype(float)
        cc = rng.normal(size=3) * rng.choice([1, 1e3, 1e6]); K = rng.normal() * rng.choice([1, 1e6, 1e9])
        for mx in (True, False):
            a = linear_bound(xx, cc, prior, .05, mx); b = linear_bound(xx, cc + K, prior, .05, mx)
            assert abs((b - K) - a) <= 1e-9 * max(1.0, abs(K), np.abs(cc).max()), (xx, cc, K, a, b)
        # feasible random points never beat the bounds
        for _ in range(20):
            q = rng.dirichlet(xx + 0.5)
            if loglik(xx, q) > cs_threshold(xx, prior, .05):
                assert cc @ q <= linear_bound(xx, cc, prior, .05) + 1e-9 * max(1, np.abs(cc).max())
                assert cc @ q >= linear_bound(xx, cc, prior, .05, False) - 1e-9 * max(1, np.abs(cc).max())
    print('shift-equivariance and feasible-point conservativeness ok (PR #5 review)')


if __name__ == '__main__':
    test_shift_equivariance_pr5()


def test_endpoint_normalization_round10():
    """Round 10 audit, finding 4: the hedged capital must be exactly 1 at n = 0 and at the endpoint means of
    degenerate samples; a stake with a zero factor may only kill the capital when its count is positive."""
    from wincs import betting_log_capital_ternary, betting_log_capital_bernoulli, betting_cs_ternary, win_ratio_cs_decided
    cases = [((0, 0, 0), -1.0), ((0, 0, 0), 0.0), ((0, 0, 0), 1.0), ((5, 0, 0), 1.0), ((0, 0, 5), -1.0), ((0, 7, 0), 0.0)]
    for (p, t, n), m in cases:
        cap = float(np.exp(betting_log_capital_ternary(p, t, n, m)))
        assert abs(cap - 1.0) < 1e-12, ((p, t, n), m, cap)
    for k, n, q in [(5, 5, 1.0), (0, 5, 0.0), (0, 0, 0.0), (0, 0, 0.3), (0, 0, 1.0)]:
        cap = float(np.exp(betting_log_capital_bernoulli(k, n, q)))
        assert abs(cap - 1.0) < 1e-12, (k, n, q, cap)
    # a positive count on a zero factor still kills that stake: one loss observed, candidate m = 1 -> K+ stake 0.5 dies,
    # but the capital stays finite and LARGE (strong evidence against m = 1), never nan
    lc = float(betting_log_capital_ternary(0, 0, 50, 1.0)); assert np.isfinite(lc) and lc > np.log(1e6), lc
    lc = float(betting_log_capital_bernoulli(0, 50, 1.0)); assert np.isfinite(lc) and lc > np.log(1e6), lc
    # vectorised endpoints agree with the scalar calls
    v = np.exp(betting_log_capital_ternary(np.array([0, 5, 0, 0]), np.array([0, 0, 0, 7]), np.array([0, 0, 5, 0]), np.array([1.0, 1.0, -1.0, 0.0])))
    assert np.allclose(v, 1.0, atol=1e-12), v
    # conservative intervals that contain the sample mean, for random count vectors including zeros
    rng = np.random.default_rng(10); delta = 0.05
    counts = rng.integers(0, 40, size=(200, 3)); counts[rng.random((200, 3)) < 0.3] = 0
    counts[:6] = [[0, 0, 0], [5, 0, 0], [0, 0, 5], [0, 7, 0], [1, 0, 0], [0, 0, 1]]
    pos, tie, neg = counts[:, 0], counts[:, 1], counts[:, 2]; n = counts.sum(1)
    lo, hi = betting_cs_ternary(pos, tie, neg, delta)
    mean = np.where(n > 0, (pos - neg) / np.maximum(n, 1), 0.0)
    assert np.all(np.isfinite(lo)) and np.all(np.isfinite(hi)) and np.all(lo >= -1) and np.all(hi <= 1)
    assert np.all(lo <= mean + 1e-12) and np.all(mean <= hi + 1e-12), (counts[(lo > mean) | (hi < mean)])
    thr = np.log(1 / delta)      # returned endpoints are outside iterates (capital >= 1/delta) or the range limits
    for arr, edge in ((lo, -1.0), (hi, 1.0)):
        lc = betting_log_capital_ternary(pos, tie, neg, arr)
        assert np.all((lc >= thr - 1e-9) | (arr == edge)), 'endpoint not conservative'
    assert lo[0] == -1.0 and hi[0] == 1.0, 'n = 0 must give the trivial interval'
    assert hi[1] == 1.0 and lo[2] == -1.0, 'all-wins / all-losses must keep the matching endpoint'
    nd = pos + neg; wlo, whi = win_ratio_cs_decided(pos, neg, delta)
    with np.errstate(divide='ignore', invalid='ignore'):
        wr = np.where(neg > 0, pos / np.maximum(neg, 1), np.inf)
    ok = nd > 0
    assert np.all(wlo[ok] <= wr[ok] + 1e-12) and np.all(wr[ok] <= whi[ok] + 1e-12)
    assert np.all(wlo[~ok] == 0.0) and np.all(np.isinf(whi[~ok])), 'no decided pair must give [0, inf]'
    assert np.all(np.isinf(whi[(neg == 0)])) and np.all(wlo[(pos == 0)] == 0.0)


if __name__ == '__main__':
    test_endpoint_normalization_round10()
    print('round 10 endpoint tests passed')
