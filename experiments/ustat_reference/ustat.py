"""Sequential two-sample U-statistic reference baseline for hierarchical net benefit.

Estimand-aligned all-pairs comparator for the disjoint-pair procedures in
src/winstats.py.  Given n_A runs of system A and n_B runs of system B with the
outcome record (compliant, successful, cost), the hierarchical kernel

    h(a, b) = compliance > success > cost (5% relative tolerance,
              cost tier only when both runs are compliant and successful;
              all other equalities are absorbing ties)

defines the two-sample U-statistics of Bebu & Lachin (2016, Biostatistics
17:178-187) and Bergemann & Hanson (2026, arXiv:2601.22525),

    U_w = (1/(n_A n_B)) sum_i sum_j 1{h(X_i, Y_j) = +1},
    U_l = (1/(n_A n_B)) sum_i sum_j 1{h(X_i, Y_j) = -1},
    U   = U_w - U_l   (net benefit / win difference),

and the Hoeffding projection variance (Bebu-Lachin sigma_uv = (N/m) xi_10 + (N/n) xi_01)

    Var(U) ~ zeta_10 / n_A + zeta_01 / n_B,
    zeta_10 = Var{ g_10(X) },  g_10(x) = E h(x, Y),
    zeta_01 = Var{ g_01(Y) },  g_01(y) = E h(X, y),

estimated (Sen 1960; Bebu-Lachin) by the sample variances of the
per-observation conditional means ghat_10(X_i) = (1/n_B) sum_j h(X_i, Y_j).

Everything is computed in O(n log n) with category counts and searchsorted on
sorted log-costs: A wins on cost against B iff cost_A < 0.95 cost_B, i.e.
log cost_B > log cost_A - log 0.95.  No n_A x n_B matrix is ever formed except
in the brute-force test oracle, which is restricted to n <= 2000.

Sequential procedures (all asymptotic; the precise statements are in README.md):
  * group-sequential (K planned looks) with Lan-DeMets alpha spending; boundaries
    by the Armitage-McPherson-Rowe recursive numerical integration (one-sided).
    The boundary recursion uses the canonical Gaussian-limit covariance
    Cov(Z_k, Z_l) = sqrt(t_k / t_l) of the standardized cumulative all-pairs
    statistics at the looks, i.e. asymptotically independent increments, with
    information fraction t_k = n_k / N as the first-order limit of
    Var(U_N) / Var(U_{n_k}).  This is the joint asymptotic normal law of
    Zhang & Wu (arXiv:2410.06281, Thm 3.4) under converging stage fractions;
    Bergemann & Hanson (arXiv:2601.22525) Prop. 1 is the exact finite-sample
    covariance identity Cov(U_k, U_l) = Var(U_l) for nested looks with fixed
    endpoints.  Covariance alone is not finite-sample independence of the
    increments of the nonlinear statistic, and n_k / N is not the exact
    finite-sample information fraction (the residual 1/n^2 term is dropped).
  * projection-based Gaussian anytime monitoring of the all-pairs statistic
    (method name allpairs_asympcs_projection_gaussian): the lower bound
    U_n - sigma_hat_n u_alpha(n) / n with sigma_hat_n^2 = zeta10_hat + zeta01_hat
    and u_alpha the one-sided normal-mixture boundary (rho^2 = 100) monitored
    from the first look n = 100.  Guarantee: an asymptotic confidence sequence
    (AsympCS) in the sense of Waudby-Smith et al. (2024, time-uniform CLT
    route), obtained through the symmetric-kernel one-sample reduction.  With
    X_i = (A_i, B_i) i.i.d. and k(X_i, X_j) = {h(A_i, B_j) + h(A_j, B_i)} / 2,
    the one-sample order-2 U-statistic U_n^* of k has mean theta and
        U_n = (1 - 1/n) U_n^* + D_n / n,     |U_n - U_n^*| <= 2 / n,
    where D_n is the disjoint-pair mean; the first projection of k is
    {a(A) + b(B)} / 2 with a(A) = E_B h(A,B) - theta, b(B) = E_A h(A,B) - theta,
    so the Hoeffding linear term (1/n) sum_i {a(A_i) + b(B_i)} has variance
    sigma_A^2 + sigma_B^2 = zeta10 + zeta01 under independent arms.  The bounded
    kernel supplies the moment conditions of the strong Gaussian approximation,
    nondegeneracy zeta10 + zeta01 > 0 is required (it holds in every frozen
    scenario; the V > 0 check in the runner is a numerical convention, not a
    theorem for degenerate kernels), and the row/column conditional-mean
    variance estimator is strongly consistent (bounded multi-sample averages
    with repeated-index terms of vanishing order).  It is NOT a finite-sample
    5% crossing bound from n = 100, and it is NOT the delayed-start family of
    Cai, Hu & Li (2026, arXiv:2605.14692, Thms 1-3), whose one-sample
    statement U_n +/- 2 sigma_hat_n gamma(n) it parallels (their 2 sigma_hat is
    our sqrt(zeta10_hat + zeta01_hat)); no two-sample theorem is stated there.

All of these are asymptotic (CLT-based) procedures; the disjoint-pair betting
and normal-mixture procedures in src/winstats.py are exact finite-sample.
"""
from __future__ import annotations
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

LOG_TOL = float(np.log(0.95))  # relative 5% tolerance on the cost tier


# ----------------------------------------------------------------------------
# Data generation: exactly the stream of experiments/run_simulations.generate
# ----------------------------------------------------------------------------

def generate_raw(rng, shape, params):
    """Draw the SAME random stream as run_simulations.generate and return raw runs.

    Returns dict with boolean safe/success and float cost arrays for arms A and B,
    plus the disjoint-pair scores (z, dq, ds) recomputed exactly as the paper does.
    Position i of arm A and position i of arm B form disjoint pair i.
    """
    sa, sb, pa, pb, cost_ratio = params
    safe_a = rng.random(shape) < sa
    safe_b = rng.random(shape) < sb
    success_a = rng.random(shape) < pa
    success_b = rng.random(shape) < pb
    cost_a = cost_ratio * rng.lognormal(0, .45, shape)
    cost_b = rng.lognormal(0, .45, shape)
    ds = safe_a.astype(np.int8) - safe_b.astype(np.int8)
    dq = success_a.astype(np.int8) - success_b.astype(np.int8)
    z = ds.copy()
    tied_safe = ds == 0
    z[tied_safe] = dq[tied_safe]
    eligible = tied_safe & safe_a & safe_b & success_a & success_b
    meaningful = np.abs(cost_a - cost_b) > .05 * np.maximum(cost_a, cost_b)
    resource = eligible & meaningful
    z[resource] = np.sign(cost_b[resource] - cost_a[resource]).astype(np.int8)
    return dict(safe_a=safe_a, safe_b=safe_b, success_a=success_a, success_b=success_b,
                cost_a=cost_a, cost_b=cost_b, z=z, dq=dq, ds=ds)


def category(safe, success):
    """0 = noncompliant & failed, 1 = noncompliant & succeeded, 2 = compliant & failed, 3 = compliant & succeeded."""
    return 2 * np.asarray(safe, dtype=np.int64) + np.asarray(success, dtype=np.int64)


# ----------------------------------------------------------------------------
# Kernel: brute force oracle (small n only)
# ----------------------------------------------------------------------------

def kernel_matrix(safe_a, succ_a, cost_a, safe_b, succ_b, cost_b):
    """h(X_i, Y_j) for all pairs; restricted to n_A * n_B <= 2000**2."""
    n_a, n_b = len(safe_a), len(safe_b)
    if n_a > 2000 or n_b > 2000:
        raise ValueError('brute-force kernel matrix restricted to n <= 2000')
    sa = np.asarray(safe_a, np.int8)[:, None]; sb = np.asarray(safe_b, np.int8)[None, :]
    qa = np.asarray(succ_a, np.int8)[:, None]; qb = np.asarray(succ_b, np.int8)[None, :]
    ca = np.asarray(cost_a, float)[:, None]; cb = np.asarray(cost_b, float)[None, :]
    h = np.sign(sa - sb).astype(np.int8)
    tied = h == 0
    h = np.where(tied, np.sign(qa - qb).astype(np.int8), h)
    elig = tied & (sa == 1) & (sb == 1) & (qa == 1) & (qb == 1)
    meaningful = np.abs(ca - cb) > .05 * np.maximum(ca, cb)
    res = elig & meaningful
    h = np.where(res, np.sign(cb - ca).astype(np.int8), h)
    return h


# ----------------------------------------------------------------------------
# O(n log n) prefix statistics at many looks
# ----------------------------------------------------------------------------

def _wins_losses_vs(cat_self, logcost_self, cnt_other, sorted_other, cum_other, n_other_elig):
    """Per-observation counts of wins and losses of each 'self' run against the
    prefix of the other arm, at every look (vectorized over looks).

    cat_self: (N,) categories of self runs. logcost_self: (N,).
    cnt_other: (K, 4) category counts of the other arm's prefix at each look.
    sorted_other: (M,) sorted log-costs of the other arm's eligible (cat 3) runs.
    cum_other: (K, M+1) cum_other[k, p] = number of the first p sorted eligible
               runs that fall inside the prefix at look k.
    n_other_elig: (K,) = cum_other[:, -1].
    Returns wins, losses of shape (K, N) (counts against the other prefix).
    'wins' means the self run is preferred; roles are symmetric.
    """
    K = cnt_other.shape[0]
    c = cat_self[None, :]
    n0, n1, n2, n3 = (cnt_other[:, i][:, None] for i in range(4))
    # cost tier (only meaningful for cat 3 vs cat 3)
    p_hi = np.searchsorted(sorted_other, logcost_self - LOG_TOL, side='right')  # #sorted <= l - log.95
    p_lo = np.searchsorted(sorted_other, logcost_self + LOG_TOL, side='left')   # #sorted <  l + log.95
    cost_wins = n_other_elig[:, None] - cum_other[:, p_hi]      # other cost > self cost/0.95
    cost_losses = cum_other[:, p_lo]                            # other cost < 0.95 self cost
    wins = np.where(c == 3, n0 + n1 + n2 + cost_wins,
           np.where(c == 2, n0 + n1,
           np.where(c == 1, n0, 0)))
    losses = np.where(c == 3, cost_losses,
             np.where(c == 2, n3,
             np.where(c == 1, n2 + n3, n1 + n2 + n3)))
    return wins, losses


def _prefix_structures(cat, logcost, looks):
    """Category prefix counts and eligible sorted-cost prefix cumulative counts."""
    N = len(cat); K = len(looks)
    onehot = np.zeros((N, 4), np.int64); onehot[np.arange(N), cat] = 1
    cnt = np.cumsum(onehot, axis=0)[looks - 1]                  # (K, 4)
    idx = np.flatnonzero(cat == 3)
    order = np.argsort(logcost[idx], kind='stable')
    sorted_cost = logcost[idx][order]; orig = idx[order]         # (M,)
    inprefix = orig[None, :] < looks[:, None]                    # (K, M)
    cum = np.zeros((K, len(idx) + 1), np.int64); np.cumsum(inprefix, axis=1, out=cum[:, 1:])
    return cnt, sorted_cost, cum, cum[:, -1]


def hierarchical_prefix_stats(safe_a, succ_a, cost_a, safe_b, succ_b, cost_b, looks):
    """All-pairs hierarchical U-statistic and projection variance components at each look.

    Arm prefixes: the first n_k runs of A and the first n_k runs of B (n_A = n_B = n_k).
    Returns dict of arrays over looks: U (net benefit), pw, pl, zeta10, zeta01,
    var_u = zeta10/n + zeta01/n (Bebu-Lachin / Sen), plus the same for the
    success and compliance component kernels g(a) - g(b) (difference of means).
    """
    looks = np.asarray(looks, np.int64); n = looks.astype(float)
    cat_a = category(safe_a, succ_a); cat_b = category(safe_b, succ_b)
    la = np.log(np.asarray(cost_a, float)); lb = np.log(np.asarray(cost_b, float))
    cnt_a, sorted_a, cum_a, nelig_a = _prefix_structures(cat_a, la, looks)
    cnt_b, sorted_b, cum_b, nelig_b = _prefix_structures(cat_b, lb, looks)
    N = len(cat_a); mask = np.arange(N)[None, :] < looks[:, None]  # (K, N)
    wa, la_ = _wins_losses_vs(cat_a, la, cnt_b, sorted_b, cum_b, nelig_b)   # A runs vs B prefix
    wb, lb_ = _wins_losses_vs(cat_b, lb, cnt_a, sorted_a, cum_a, nelig_a)   # B runs vs A prefix
    W = np.sum(np.where(mask, wa, 0), axis=1).astype(float)
    L = np.sum(np.where(mask, la_, 0), axis=1).astype(float)
    W_b = np.sum(np.where(mask, wb, 0), axis=1).astype(float)
    L_b = np.sum(np.where(mask, lb_, 0), axis=1).astype(float)
    if not (np.array_equal(W, L_b) and np.array_equal(L, W_b)):
        raise AssertionError('all-pairs win/loss counts are not symmetric between arms')
    U = (W - L) / n**2; pw = W / n**2; pl = L / n**2
    g10 = np.where(mask, (wa - la_) / n[:, None], np.nan)          # ghat_10(X_i) at each look
    g01 = np.where(mask, (lb_ - wb) / n[:, None], np.nan)          # ghat_01(Y_j) = mean_i h(X_i, Y_j)
    zeta10 = np.nanvar(g10, axis=1, ddof=1); zeta01 = np.nanvar(g01, axis=1, ddof=1)
    out = dict(n=looks, U=U, pw=pw, pl=pl, zeta10=zeta10, zeta01=zeta01,
               var_u=zeta10 / n + zeta01 / n, var_h=pw + pl - U**2)
    for name, xa, xb in (('success', succ_a, succ_b), ('compliance', safe_a, safe_b)):
        xa = np.asarray(xa, float); xb = np.asarray(xb, float)
        ma = np.cumsum(xa)[looks - 1] / n; mb = np.cumsum(xb)[looks - 1] / n
        va = (np.cumsum(xa**2)[looks - 1] - n * ma**2) / (n - 1)
        vb = (np.cumsum(xb**2)[looks - 1] - n * mb**2) / (n - 1)
        out[f'U_{name}'] = ma - mb; out[f'zeta10_{name}'] = va; out[f'zeta01_{name}'] = vb
        out[f'var_u_{name}'] = va / n + vb / n
    return out


def hierarchical_full_sample(safe_a, succ_a, cost_a, safe_b, succ_b, cost_b):
    """Fixed-horizon all-pairs statistic with unequal arm sizes allowed (single look)."""
    cat_a = category(safe_a, succ_a); cat_b = category(safe_b, succ_b)
    la = np.log(np.asarray(cost_a, float)); lb = np.log(np.asarray(cost_b, float))
    na, nb = len(cat_a), len(cat_b)
    cnt_a, sorted_a, cum_a, nelig_a = _prefix_structures(cat_a, la, np.array([na]))
    cnt_b, sorted_b, cum_b, nelig_b = _prefix_structures(cat_b, lb, np.array([nb]))
    wa, la_ = _wins_losses_vs(cat_a, la, cnt_b, sorted_b, cum_b, nelig_b)
    wb, lb_ = _wins_losses_vs(cat_b, lb, cnt_a, sorted_a, cum_a, nelig_a)
    W = wa.sum(); L = la_.sum()
    assert W == lb_.sum() and L == wb.sum()
    U = (W - L) / (na * nb)
    g10 = (wa[0] - la_[0]) / nb; g01 = (lb_[0] - wb[0]) / na
    z10 = g10.var(ddof=1); z01 = g01.var(ddof=1)
    return dict(U=U, pw=W / (na * nb), pl=L / (na * nb), zeta10=z10, zeta01=z01, var_u=z10 / na + z01 / nb)


# ----------------------------------------------------------------------------
# Population quantities for the simulation scenarios (efficiency ratio)
# ----------------------------------------------------------------------------

def conditional_mean_given_a(safe_a, succ_a, logcost_a, sb, pb, sigma=.45):
    """g_10(x) = E h(x, Y) for Y ~ arm B law (compliance sb, success pb, log-cost N(0, sigma^2))."""
    safe_a = np.asarray(safe_a, float); succ_a = np.asarray(succ_a, float); l = np.asarray(logcost_a, float)
    win_cost = 1 - norm.cdf((l - LOG_TOL) / sigma)     # P(log cost_B > l - log .95)
    lose_cost = norm.cdf((l + LOG_TOL) / sigma)        # P(log cost_B < l + log .95)
    g_unsafe = -sb + (1 - sb) * (succ_a * (1 - pb) - (1 - succ_a) * pb)
    g_safe = (1 - sb) + sb * (succ_a * ((1 - pb) + pb * (win_cost - lose_cost)) - (1 - succ_a) * pb)
    return np.where(safe_a == 1, g_safe, g_unsafe)


def conditional_mean_given_b(safe_b, succ_b, logcost_b, sa, pa, log_ratio, sigma=.45):
    """g_01(y) = E h(X, y), X ~ arm A law (compliance sa, success pa, log-cost log_ratio + N(0, sigma^2))."""
    # by antisymmetry g_01(y) = -E h'(y, X) where h' is the same kernel with roles swapped
    return -conditional_mean_given_a(safe_b, succ_b, np.asarray(logcost_b, float) - log_ratio, sa, pa, sigma)


def efficiency_components(params, n_mc=1_000_000, seed=0):
    """Monte Carlo Var(h), zeta_10, zeta_01 for the hierarchical kernel under a scenario.

    Var(h) is the disjoint-pair score variance; zeta_10 + zeta_01 is the
    all-pairs asymptotic variance per index (n_A = n_B = n).  The ratio
    Var(h)/(zeta_10+zeta_01) is the asymptotic relative efficiency of the
    all-pairs statistic over disjoint pairs at equal run budgets.
    The conditional means are computed analytically given each sampled run.
    """
    sa, sb, pa, pb, r = params
    rng = np.random.default_rng(seed)
    raw = generate_raw(rng, (n_mc,), params)
    z = raw['z'].astype(float)
    pw, pl = np.mean(z > 0), np.mean(z < 0)
    var_h = pw + pl - (pw - pl)**2
    g10 = conditional_mean_given_a(raw['safe_a'], raw['success_a'], np.log(raw['cost_a']), sb, pb)
    g01 = conditional_mean_given_b(raw['safe_b'], raw['success_b'], np.log(raw['cost_b']), sa, pa, np.log(r))
    zeta10 = g10.var(ddof=1); zeta01 = g01.var(ddof=1)
    return dict(theta_mc=float(pw - pl), theta_from_g10=float(g10.mean()), theta_from_g01=float(g01.mean()),
                pw=float(pw), pl=float(pl), var_h=float(var_h), zeta10=float(zeta10), zeta01=float(zeta01),
                are_allpairs_vs_disjoint=float(var_h / (zeta10 + zeta01)),
                theta_mcse=float(np.std(z, ddof=1) / np.sqrt(n_mc)))


# ----------------------------------------------------------------------------
# Group-sequential boundaries: Lan-DeMets alpha spending, one-sided
# ----------------------------------------------------------------------------

def spending(kind, t, alpha, gamma=-3.):
    """Cumulative one-sided alpha spent at information fraction t in (0, 1]."""
    t = np.asarray(t, float)
    if kind == 'obf':        # Lan-DeMets O'Brien-Fleming-type
        return 2 * (1 - norm.cdf(norm.ppf(1 - alpha / 2) / np.sqrt(t)))
    if kind == 'pocock':     # Lan-DeMets Pocock-type
        return alpha * np.log(1 + (np.e - 1) * t)
    if kind == 'hsd':        # Hwang-Shih-DeCani (gamma = -3 in Bergemann & Hanson)
        return alpha * (1 - np.exp(-gamma * t)) / (1 - np.exp(-gamma))
    if kind == 'kim_demets2':  # Zhang & Wu: alpha t^2
        return alpha * t**2
    raise ValueError(kind)


def _simpson_weights(m, h):
    if m % 2 == 0:
        raise ValueError('Simpson needs an odd number of points')
    w = np.ones(m); w[1:-1:2] = 4; w[2:-1:2] = 2
    return w * h / 3


def gs_boundaries(t, alpha_spent, grid_points=2001, lower=-12.):
    """One-sided group-sequential boundaries on the standardized scale.

    t: information fractions t_1 < ... < t_K = 1; alpha_spent: cumulative
    one-sided alpha to be spent by each look (nondecreasing, last = alpha).
    The Brownian-motion sum process S_k = B(t_k) has independent normal
    increments; the sub-density of S_k on the continuation region is
    propagated by numerical integration (Armitage, McPherson & Rowe 1969;
    Lan & DeMets 1983) on a Simpson grid, and each boundary b_k solves
    P(no earlier exit, S_k >= b_k) = alpha_k - alpha_{k-1} by root finding.
    Returns z-scale boundaries c_k = b_k / sqrt(t_k).
    """
    t = np.asarray(t, float); a = np.asarray(alpha_spent, float)
    K = len(t); incr = np.diff(np.r_[0., a])
    if np.any(incr < -1e-15) or np.any(np.diff(t) <= 0) or abs(t[-1] - 1) > 1e-12:
        raise ValueError('need increasing t ending at 1 and nondecreasing spending')
    c = np.zeros(K)
    # look 1
    c[0] = norm.ppf(1 - incr[0]); b_prev = c[0] * np.sqrt(t[0])
    grid = np.linspace(lower * np.sqrt(t[0]), b_prev, grid_points)
    f = norm.pdf(grid, scale=np.sqrt(t[0]))          # sub-density of S_1 on continuation region
    w = _simpson_weights(grid_points, grid[1] - grid[0])
    for k in range(1, K):
        dt = t[k] - t[k - 1]; sd = np.sqrt(dt)
        def exit_prob(b):
            return np.sum(w * f * norm.sf((b - grid) / sd))
        target = incr[k]
        if target <= 0:
            b_k = np.inf
        else:
            b_k = brentq(lambda b: exit_prob(b) - target, -5 * np.sqrt(t[k]), 12 * np.sqrt(t[k]), xtol=1e-12)
        c[k] = b_k / np.sqrt(t[k])
        if k < K - 1:
            hi = b_k if np.isfinite(b_k) else 12 * np.sqrt(t[k])
            new_grid = np.linspace(lower * np.sqrt(t[k]), hi, grid_points)
            # f_k(s) = int f_{k-1}(u) phi((s-u)/sd)/sd du
            kern = norm.pdf((new_grid[:, None] - grid[None, :]) / sd) / sd
            f = kern @ (w * f)
            grid = new_grid; w = _simpson_weights(grid_points, grid[1] - grid[0])
    return c


def gs_exit_probabilities(t, c, drift=0., grid_points=2001, lower=-12.):
    """Probability of first crossing at each look for boundaries c (z-scale) with drift
    theta per unit information (S_k = B(t_k) + drift * t_k).  Used for validation."""
    t = np.asarray(t, float); c = np.asarray(c, float); K = len(t)
    b = c * np.sqrt(t)
    probs = np.zeros(K)
    probs[0] = norm.sf(b[0], loc=drift * t[0], scale=np.sqrt(t[0]))
    grid = np.linspace(lower * np.sqrt(t[0]) + drift * t[0], b[0], grid_points)
    f = norm.pdf(grid, loc=drift * t[0], scale=np.sqrt(t[0]))
    w = _simpson_weights(grid_points, grid[1] - grid[0])
    for k in range(1, K):
        dt = t[k] - t[k - 1]; sd = np.sqrt(dt)
        probs[k] = np.sum(w * f * norm.sf((b[k] - grid - drift * dt) / sd))
        if k < K - 1:
            new_grid = np.linspace(lower * np.sqrt(t[k]) + drift * t[k], b[k], grid_points)
            kern = norm.pdf((new_grid[:, None] - grid[None, :] - drift * dt) / sd) / sd
            f = kern @ (w * f); grid = new_grid; w = _simpson_weights(grid_points, grid[1] - grid[0])
    return probs


# ----------------------------------------------------------------------------
# One-sided normal-mixture boundary (Howard et al. 2021) for the asymptotic CS
# ----------------------------------------------------------------------------

def one_sided_normal_mixture_boundary(v, alpha=.05, rho2=100.):
    """Boundary u(v) with P(exists t: S_t >= u(V_t)) <= alpha for a process with
    sub-Gaussian (here: asymptotically Gaussian) increments and variance process V.

    Mixture of exp(lambda S - lambda^2 V / 2) over lambda ~ half-normal with
    variance 1/rho2 gives the closed form
        M = 2 sqrt(rho2/(V+rho2)) exp(S^2/(2(V+rho2))) Phi(S/sqrt(V+rho2)),
    increasing in S >= 0; Ville's inequality gives the boundary by solving M = 1/alpha.
    (Two-sided closed form sqrt((V+rho2) log((V+rho2)/(rho2 alpha^2))) is the
    paper's normal_mixture_radius; this is its exact one-sided counterpart.)
    """
    v = np.atleast_1d(np.asarray(v, float))
    out = np.empty_like(v)
    for i, vi in enumerate(v):
        rhs = np.log(1 / alpha) - np.log(2 * np.sqrt(rho2 / (vi + rho2)))
        fun = lambda x: x**2 / 2 + norm.logcdf(x) - rhs
        x = brentq(fun, 0., 60.)
        out[i] = x * np.sqrt(vi + rho2)
    return out


# ----------------------------------------------------------------------------
# Decision rules
# ----------------------------------------------------------------------------

def wilson(k, n):
    z = norm.ppf(.975); p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - r, c + r


def zstat(u, var, c):
    """(U - c)/sqrt(var); zero-variance estimates give no evidence (z = -inf)."""
    u = np.asarray(u, float); var = np.asarray(var, float)
    with np.errstate(divide='ignore', invalid='ignore'):
        z = (u - c) / np.sqrt(var)
    return np.where(var > 0, z, -np.inf)
