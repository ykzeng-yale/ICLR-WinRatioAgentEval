"""Win statistics for agent evaluation: cells, confidence sequences, offline inference.

Every pairwise comparison of two agent runs under a prespecified outcome
hierarchy lands in exactly one of 2T+1 cells: tie, or (decisive tier k,
direction). All win statistics (net benefit, win ratio, win odds, tier
contributions) are functionals of the cell-probability vector p on the
simplex. For a stream of independent pairs the cell counts are multinomial,
so one time-uniform confidence sequence (CS) for p, built from the
Dirichlet-multinomial mixture martingale (Lindon & Malek, 2022), yields
simultaneous anytime-valid CSs for every functional. Offline benchmark data
with replicate runs per task use task-clustered U-statistic inference.

This module implements established constructions; see paper/ for credits.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.special import gammaln, logsumexp
from scipy.optimize import minimize, brentq
from scipy.stats import norm, t as student_t

try:
    from winstats import Tier, compare
except ImportError:  # pragma: no cover
    from .winstats import Tier, compare  # type: ignore


# ----------------------------------------------------------------------------
# Cells
# ----------------------------------------------------------------------------

def cells_from_comparison(sign, tier_index):
    """Map (signed preference, decisive tier) to cell index in 0..2T.

    cell 0 = tie; cell 2k+1 = win decided at tier k; cell 2k+2 = loss at tier k.
    """
    sign = np.asarray(sign); tier_index = np.asarray(tier_index)
    cell = np.zeros(sign.shape, dtype=np.int16)
    win = sign > 0; loss = sign < 0
    cell[win] = 2 * tier_index[win] + 1
    cell[loss] = 2 * tier_index[loss] + 2
    return cell


def classify(a, b, tiers, eligible=None):
    """Classify pairs of outcome vectors into hierarchy cells (see compare)."""
    sign, tier_index = compare(a, b, tiers, eligible)
    return cells_from_comparison(sign, tier_index)


def cell_counts(cells, n_tiers):
    cells = np.asarray(cells)
    return np.bincount(cells.ravel(), minlength=2 * n_tiers + 1).astype(float)


def cell_signs(n_tiers):
    """Score s_k in {-1,0,+1} for each cell (net benefit = sum_k s_k p_k)."""
    s = np.zeros(2 * n_tiers + 1)
    s[1::2] = 1.0; s[2::2] = -1.0
    return s


def win_loss_masks(n_tiers):
    w = np.zeros(2 * n_tiers + 1, bool); l = np.zeros(2 * n_tiers + 1, bool)
    w[1::2] = True; l[2::2] = True
    return w, l


def functionals(p, n_tiers):
    """All standard win statistics from a cell-probability vector."""
    p = np.asarray(p, float)
    w, l = win_loss_masks(n_tiers)
    pw, pl = p[..., w].sum(-1), p[..., l].sum(-1)
    pt = 1.0 - pw - pl
    out = dict(p_win=pw, p_loss=pl, p_tie=pt, net_benefit=pw - pl,
               win_ratio=np.where(pl > 0, pw / np.where(pl > 0, pl, 1), np.inf),
               win_odds=(pw + pt / 2) / np.maximum(pl + pt / 2, 1e-300))
    out['tier_contribution'] = np.stack([p[..., 2 * k + 1] - p[..., 2 * k + 2] for k in range(n_tiers)], -1)
    out['tier_decided'] = np.stack([p[..., 2 * k + 1] + p[..., 2 * k + 2] for k in range(n_tiers)], -1)
    return out


# ----------------------------------------------------------------------------
# Dirichlet-multinomial mixture martingale and confidence sequence
# ----------------------------------------------------------------------------

def log_beta(a):
    a = np.asarray(a, float)
    return gammaln(a).sum(-1) - gammaln(a.sum(-1))


def log_mixture_martingale(counts, p, prior):
    """log M_n(p) = log B(prior+x) - log B(prior) - sum_k x_k log p_k.

    Under iid multinomial(p) cells, M_n(p) is a nonnegative martingale with
    M_0 = 1 (predictable Dirichlet mixture of likelihood ratios), so
    P(exists n: M_n(p) >= 1/delta) <= delta (Ville).
    """
    counts = np.asarray(counts, float); p = np.asarray(p, float); prior = np.asarray(prior, float)
    with np.errstate(divide='ignore', invalid='ignore'):
        loglik = np.where(counts > 0, counts * np.log(p), 0.0).sum(-1)
    return log_beta(prior + counts) - log_beta(prior) - loglik


def cs_threshold(counts, prior, delta):
    """c_n such that CS_n = {p : sum_k x_k log p_k > c_n}."""
    counts = np.asarray(counts, float); prior = np.asarray(prior, float)
    return log_beta(prior + counts) - log_beta(prior) + np.log(delta)


def loglik(counts, p):
    counts = np.asarray(counts, float); p = np.asarray(p, float)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(counts > 0, counts * np.log(p), 0.0).sum(-1)


def in_cs(counts, p, prior, delta):
    return loglik(counts, p) > cs_threshold(counts, prior, delta)


def _mle(counts):
    counts = np.asarray(counts, float)
    n = counts.sum()
    return counts / n if n > 0 else np.full(counts.shape, 1 / counts.size)


def linear_bound(counts, coef, prior, delta, maximize=True, tol=1e-10):
    """sup or inf of sum_k coef_k p_k over the CS (a convex set).

    Solves max c'p s.t. ell(p) >= c_n, p in simplex, by maximizing the
    Lagrangian c'p + lam*ell(p) in closed form for each lam and bisecting on
    lam so the constraint is active (ell is strictly concave where counts>0).
    Zero-count cells receive mass only if they carry the extremal coefficient.
    """
    counts = np.asarray(counts, float); coef = np.asarray(coef, float)
    sgn = 1.0 if maximize else -1.0
    c = sgn * coef
    K = counts.size
    cn = cs_threshold(counts, prior, delta)
    n = counts.sum()
    if n == 0:  # CS is (essentially) the whole simplex.
        return sgn * c.max()
    # Vertex candidate: all mass at a max-coefficient cell (feasible only if
    # every positive-count cell shares that coefficient, i.e. ell finite).
    cmax = c.max()
    pos = counts > 0
    zero_top = (~pos) & (c >= cmax - 1e-15)

    def p_of(lam, nu):
        # p_k = lam*x_k/(nu - c_k) for positive-count cells.
        p = np.zeros(K)
        p[pos] = lam * counts[pos] / (nu - c[pos])
        return p

    def solve_nu(lam):
        # find nu > max c over positive cells s.t. sum over positive cells = 1 - m0
        # where m0 = mass on zero-count top cells. Mass on those cells is a
        # free variable r in [0,1): we treat nu = cmax exactly when zero_top
        # exists (then r = 1 - sum p_pos with nu=cmax if that is < 1).
        lo = c[pos].max()
        if zero_top.any() and cmax > lo + 1e-15:
            # nu is pinned at cmax if the positive cells fit under it.
            s = (lam * counts[pos] / (cmax - c[pos])).sum()
            if s <= 1:
                return cmax, 1 - s
        # otherwise find nu>lo with sum=1
        f = lambda nu: (lam * counts[pos] / (nu - c[pos])).sum() - 1
        hi = lo + max(lam * counts[pos].sum(), 1e-12) * 2 + 1
        while f(hi) > 0:
            hi = lo + (hi - lo) * 2
        nu = brentq(f, lo + 1e-14 * max(1, abs(lo)), hi, xtol=1e-14)
        return nu, 0.0

    def ell_at(lam):
        nu, r = solve_nu(lam)
        p = p_of(lam, nu)
        return loglik(counts, p), p, r

    # ell increases with lam (more weight on likelihood); find lam s.t. ell = cn.
    lam_lo, lam_hi = 1e-12, 1.0
    e_lo = ell_at(lam_lo)[0]
    if e_lo >= cn:  # even (almost) pure objective is inside CS: vertex optimum
        _, p, r = ell_at(lam_lo)
        val = (c * p).sum() + r * cmax
        return sgn * val
    while ell_at(lam_hi)[0] < cn:
        lam_hi *= 4
        if lam_hi > 1e12:
            break
    for _ in range(200):
        mid = np.sqrt(lam_lo * lam_hi)
        e = ell_at(mid)[0]
        if e < cn:
            lam_lo = mid
        else:
            lam_hi = mid
        if lam_hi / lam_lo - 1 < tol:
            break
    _, p, r = ell_at(lam_hi)
    return sgn * ((c * p).sum() + r * cmax)


def ratio_bound(counts, num, den, prior, delta, maximize=True, lo=1e-6, hi=1e6, iters=80):
    """sup/inf of (num'p)/(den'p) over the CS by bisection on r with linear
    sub-problems: (num'p)/(den'p) >= r for some p in CS iff max (num - r den)'p >= 0.
    Returns inf when the ratio is unbounded above within the CS."""
    counts = np.asarray(counts, float); num = np.asarray(num, float); den = np.asarray(den, float)
    if maximize:
        # check unbounded: is there p in CS with den'p == 0? -> inf of den'p over CS == 0
        if linear_bound(counts, den, prior, delta, maximize=False) <= 1e-12:
            return np.inf
        a, b = lo, hi
        if linear_bound(counts, num - b * den, prior, delta, True) >= 0:
            return np.inf
        for _ in range(iters):
            m = np.sqrt(a * b)
            if linear_bound(counts, num - m * den, prior, delta, True) >= 0:
                a = m
            else:
                b = m
        return b
    else:
        if linear_bound(counts, num, prior, delta, maximize=False) <= 1e-12:
            return 0.0
        a, b = lo, hi
        if linear_bound(counts, num - a * den, prior, delta, False) <= 0:
            return 0.0
        for _ in range(iters):
            m = np.sqrt(a * b)
            # ratio <= m attainable iff min (num - m den)'p <= 0
            if linear_bound(counts, num - m * den, prior, delta, False) <= 0:
                b = m
            else:
                a = m
        return a


@dataclass
class MultinomialCS:
    """Time-uniform confidence sequence for the cell-probability vector.

    prior: Dirichlet parameters (fixed before data); delta: error level.
    All functional bounds are simultaneously valid: they are images of the
    single set CS_n, and P(exists n: p_true not in CS_n) <= delta.
    """
    n_tiers: int
    delta: float = 0.05
    prior: float | np.ndarray = 1.0

    def _prior(self):
        K = 2 * self.n_tiers + 1
        return np.full(K, self.prior, float) if np.isscalar(self.prior) else np.asarray(self.prior, float)

    def net_benefit(self, counts):
        s = cell_signs(self.n_tiers); pr = self._prior()
        return (linear_bound(counts, s, pr, self.delta, False), linear_bound(counts, s, pr, self.delta, True))

    def tier_contribution(self, counts, k):
        s = np.zeros(2 * self.n_tiers + 1); s[2 * k + 1] = 1; s[2 * k + 2] = -1; pr = self._prior()
        return (linear_bound(counts, s, pr, self.delta, False), linear_bound(counts, s, pr, self.delta, True))

    def p_win(self, counts):
        w, _ = win_loss_masks(self.n_tiers); pr = self._prior()
        return (linear_bound(counts, w.astype(float), pr, self.delta, False), linear_bound(counts, w.astype(float), pr, self.delta, True))

    def p_loss(self, counts):
        _, l = win_loss_masks(self.n_tiers); pr = self._prior()
        return (linear_bound(counts, l.astype(float), pr, self.delta, False), linear_bound(counts, l.astype(float), pr, self.delta, True))

    def win_ratio(self, counts):
        w, l = win_loss_masks(self.n_tiers); pr = self._prior()
        return (ratio_bound(counts, w.astype(float), l.astype(float), pr, self.delta, False),
                ratio_bound(counts, w.astype(float), l.astype(float), pr, self.delta, True))

    def win_odds(self, counts):
        w, l = win_loss_masks(self.n_tiers); pr = self._prior()
        tie = ~(w | l)
        num = w.astype(float) + 0.5 * tie; den = l.astype(float) + 0.5 * tie
        return (ratio_bound(counts, num, den, pr, self.delta, False), ratio_bound(counts, num, den, pr, self.delta, True))

    def contains(self, counts, p):
        return in_cs(counts, p, self._prior(), self.delta)


# ----------------------------------------------------------------------------
# Ternary closed forms (win/tie/loss) for fast vectorized simulation
# ----------------------------------------------------------------------------

def ternary_constrained_loglik(xw, xt, xl, c):
    """max of xw log pw + xt log pt + xl log pl subject to pw - pl = c.

    Vectorized closed form: with pl = u, pw = u + c, pt = 1 - 2u - c the
    stationarity condition is a quadratic in u.
    """
    xw = np.asarray(xw, float); xt = np.asarray(xt, float); xl = np.asarray(xl, float)
    c = np.asarray(c, float)
    n = xw + xt + xl
    lo = np.maximum(0.0, -c); hi = (1 - c) / 2  # u in [lo, hi]
    # d/du: xw/(u+c) + xl/u - 2xt/(1-2u-c) = 0
    # => xw*u*(1-2u-c) + xl*(u+c)*(1-2u-c) - 2xt*u*(u+c) = 0
    A = -2 * xw - 2 * xl - 2 * xt
    B = xw * (1 - c) + xl * (1 - c) - 2 * xl * c - 2 * xt * c
    C = xl * c * (1 - c)
    # Solve A u^2 + B u + C = 0, choose root in (lo, hi).
    with np.errstate(invalid='ignore', divide='ignore'):
        disc = np.sqrt(np.maximum(B * B - 4 * A * C, 0))
        r1 = (-B + disc) / (2 * A); r2 = (-B - disc) / (2 * A)
    cand = np.stack([r1, r2, lo, hi], -1)
    cand = np.clip(cand, lo[..., None], hi[..., None])
    pl = cand; pw = cand + c[..., None]; pt = 1 - 2 * cand - c[..., None]
    with np.errstate(divide='ignore', invalid='ignore'):
        ll = (np.where(xw[..., None] > 0, xw[..., None] * np.log(np.maximum(pw, 0)), 0)
              + np.where(xt[..., None] > 0, xt[..., None] * np.log(np.maximum(pt, 0)), 0)
              + np.where(xl[..., None] > 0, xl[..., None] * np.log(np.maximum(pl, 0)), 0))
    ll = np.where(np.isnan(ll), -np.inf, ll)
    return ll.max(-1)


def ternary_log_eprocess_nb(xw, xt, xl, threshold=0.0, prior=(1.0, 1.0, 1.0)):
    """log e-process for H0: net benefit <= threshold, ternary cells.

    E_n = inf_{p in H0} M_n(p) = exp(log B(prior+x) - log B(prior) - sup_{H0} ell(p)).
    Because ell is concave and H0 = {pw - pl <= c} is a half-space, the
    supremum is at the unconstrained MLE if it satisfies the constraint and
    otherwise on the boundary pw - pl = c.
    """
    xw = np.asarray(xw, float); xt = np.asarray(xt, float); xl = np.asarray(xl, float)
    n = xw + xt + xl
    prior = np.asarray(prior, float)
    counts = np.stack([xw, xt, xl], -1)
    mle_nb = np.where(n > 0, (xw - xl) / np.maximum(n, 1), 0.0)
    ll_mle = loglik(counts, counts / np.maximum(n, 1)[..., None])
    ll_bd = ternary_constrained_loglik(xw, xt, xl, np.broadcast_to(threshold, xw.shape))
    sup_ll = np.where(mle_nb <= threshold, ll_mle, ll_bd)
    return log_beta(prior + counts) - log_beta(prior) - sup_ll


# ----------------------------------------------------------------------------
# Offline benchmark inference (task-clustered U-statistics)
# ----------------------------------------------------------------------------

def task_level_scores(a_runs, b_runs, tiers, eligible=None, pairing='all'):
    """Per-task average win/loss indicators from replicate runs.

    a_runs, b_runs: dicts task -> array (K, T) of outcomes (T tiers).
    pairing='all' averages all K_A*K_B cross comparisons (independent-run
    target); 'diagonal' uses only i==i (shared-seed target); both are
    unbiased for their own within-task expectation.
    Returns arrays (tasks,) of mean win, mean loss, mean tie, plus per-tier
    contribution means (tasks, T) and the ordered task list.
    """
    tasks = sorted(set(a_runs) & set(b_runs))
    W, L, TT, C, D = [], [], [], [], []
    nT = len(tiers)
    for t in tasks:
        A = np.asarray(a_runs[t], float); B = np.asarray(b_runs[t], float)
        if pairing == 'all':
            sign, tier = compare(A[:, None, :], B[None, :, :], tiers, None if eligible is None else eligible(A[:, None, :], B[None, :, :]))
        elif pairing == 'diagonal':
            k = min(len(A), len(B))
            sign, tier = compare(A[:k], B[:k], tiers, None if eligible is None else eligible(A[:k], B[:k]))
        elif pairing == 'offdiagonal':
            sign, tier = compare(A[:, None, :], B[None, :, :], tiers, None if eligible is None else eligible(A[:, None, :], B[None, :, :]))
            m = ~np.eye(len(A), len(B), dtype=bool)
            sign, tier = sign[m], tier[m]
        else:
            raise ValueError(pairing)
        W.append((sign > 0).mean()); L.append((sign < 0).mean()); TT.append((sign == 0).mean())
        C.append([((sign > 0) & (tier == k)).mean() - ((sign < 0) & (tier == k)).mean() for k in range(nT)])
        D.append([(tier == k).mean() for k in range(nT)])
    return dict(tasks=tasks, win=np.array(W), loss=np.array(L), tie=np.array(TT),
                tier_contribution=np.array(C), tier_decided=np.array(D))


def clustered_summary(win, loss, weights=None, alpha=0.05):
    """Net benefit, win ratio, win odds with task-cluster (delta-method) CIs.

    win, loss: per-task mean win/loss indicators (clusters). weights: optional
    fixed nonnegative task weights (e.g. equal-domain weighting), normalized.
    Uses a t reference with T-1 df; log scale for ratios.
    """
    win = np.asarray(win, float); loss = np.asarray(loss, float); T = win.size
    w = np.ones(T) / T if weights is None else np.asarray(weights, float) / np.sum(weights)
    pw = float(np.sum(w * win)); pl = float(np.sum(w * loss)); pt = 1 - pw - pl
    # Weighted cluster covariance of the (win, loss) means: sum w_t^2 (x_t - mean)^2 * T/(T-1)
    dw = win - pw; dl = loss - pl
    fac = T / (T - 1) if T > 1 else np.nan
    vw = float(np.sum(w**2 * dw**2) * fac); vl = float(np.sum(w**2 * dl**2) * fac)
    cwl = float(np.sum(w**2 * dw * dl) * fac)
    q = student_t.ppf(1 - alpha / 2, T - 1) if T > 1 else np.nan
    nb = pw - pl; v_nb = vw + vl - 2 * cwl
    out = dict(n_tasks=T, p_win=pw, p_loss=pl, p_tie=pt, net_benefit=nb, nb_se=np.sqrt(max(v_nb, 0)),
               nb_ci=(nb - q * np.sqrt(max(v_nb, 0)), nb + q * np.sqrt(max(v_nb, 0))))
    if pw > 0 and pl > 0:
        lwr = np.log(pw / pl); v = vw / pw**2 + vl / pl**2 - 2 * cwl / (pw * pl)
        out.update(win_ratio=pw / pl, log_wr_se=np.sqrt(max(v, 0)),
                   wr_ci=(np.exp(lwr - q * np.sqrt(max(v, 0))), np.exp(lwr + q * np.sqrt(max(v, 0)))))
        num = pw + pt / 2; den = pl + pt / 2  # win odds = (1+nb)/(1-nb)
        # log WO = log(1+nb) - log(1-nb); d/dnb = 1/(1+nb) + 1/(1-nb) = 2/(1-nb^2)
        g = 2 / (1 - nb**2); v_lwo = g**2 * v_nb
        out.update(win_odds=num / den, wo_ci=(np.exp(np.log(num / den) - q * np.sqrt(max(v_lwo, 0))),
                                            np.exp(np.log(num / den) + q * np.sqrt(max(v_lwo, 0)))))
    else:
        out.update(win_ratio=np.inf if pw > 0 else np.nan, wr_ci=(np.nan, np.nan),
                   win_odds=(pw + pt / 2) / (pl + pt / 2) if (pl + pt / 2) > 0 else np.inf, wo_ci=(np.nan, np.nan))
    return out


def task_bootstrap(win, loss, n_boot=10000, seed=0, weights=None):
    """Percentile bootstrap over tasks for net benefit and log win ratio."""
    rng = np.random.default_rng(seed)
    win = np.asarray(win, float); loss = np.asarray(loss, float); T = win.size
    idx = rng.integers(0, T, (n_boot, T))
    if weights is None:
        pw = win[idx].mean(1); pl = loss[idx].mean(1)
    else:
        w = np.asarray(weights, float)[idx]; w = w / w.sum(1, keepdims=True)
        pw = (w * win[idx]).sum(1); pl = (w * loss[idx]).sum(1)
    nb = pw - pl
    with np.errstate(divide='ignore', invalid='ignore'):
        lwr = np.log(pw) - np.log(pl)
    return dict(nb_ci=tuple(np.percentile(nb, [2.5, 97.5])),
                wr_ci=tuple(np.exp(np.nanpercentile(lwr[np.isfinite(lwr)], [2.5, 97.5]))) if np.isfinite(lwr).any() else (np.nan, np.nan),
                frac_wr_undefined=float(np.mean(~np.isfinite(lwr))))


def stratified_combine(estimates, variances, weights):
    """Fixed-weight combination of stratum net benefits (e.g., domains)."""
    w = np.asarray(weights, float); w = w / w.sum()
    return float(np.sum(w * estimates)), float(np.sum(w**2 * variances))


# ----------------------------------------------------------------------------
# Censored latency comparison (timeouts as censoring, Pocock-style)
# ----------------------------------------------------------------------------

def compare_censored(t_a, done_a, t_b, done_b, margin=0.0, relative=False):
    """Pairwise time comparison with right-censoring (smaller time is better).

    t: observed time (completion time or timeout); done: 1 if completed.
    A wins iff A completed and t_a + margin < t_b (B had not finished by then,
    whether it completed later or was still running when censored). Symmetric
    for B. Otherwise the pair is a tie (indeterminate or within margin).
    """
    t_a = np.asarray(t_a, float); t_b = np.asarray(t_b, float)
    done_a = np.asarray(done_a, bool); done_b = np.asarray(done_b, bool)
    m = margin * np.maximum(t_a, t_b) if relative else margin
    a_win = done_a & (t_a + m < t_b)
    b_win = done_b & (t_b + m < t_a)
    return a_win.astype(np.int8) - b_win.astype(np.int8)


# ----------------------------------------------------------------------------
# Design helpers
# ----------------------------------------------------------------------------

def pairs_for_power(net_benefit, p_tie, alpha=0.05, power=0.8, one_sided=True):
    """Fixed-horizon pairs needed to detect a net benefit with given tie rate.

    Var of a single ternary score is (1 - p_tie) - nb^2.
    """
    za = norm.ppf(1 - alpha) if one_sided else norm.ppf(1 - alpha / 2)
    zb = norm.ppf(power)
    var = (1 - p_tie) - net_benefit**2
    return float(np.ceil((za + zb)**2 * var / net_benefit**2))


def nb_from_win_ratio(win_ratio, p_tie):
    """Net benefit implied by a win ratio and tie probability."""
    pl = (1 - p_tie) / (1 + win_ratio)
    return (1 - p_tie) - 2 * pl


# ----------------------------------------------------------------------------
# Betting confidence sequences on bounded projections (main online engine)
# ----------------------------------------------------------------------------

def default_stakes(n_bets=40, lo=1e-4, hi=0.5):
    """Prespecified geometric stake grid for scores with range 2 (|z-m|<=2)."""
    return np.geomspace(lo, hi, n_bets)


def betting_log_capital_ternary(pos, tie, neg, m, stakes=None):
    """log of the hedged mixture capital for candidate mean m of a ternary
    score z in {-1,0,1}: K(m) = max(K+(m), K-(m)) where K± mix over ±stakes.

    pos, tie, neg: counts (broadcastable). m: candidate mean (scalar or array
    broadcastable with counts). Returns log K(m). Valid for any predictable
    stake grid fixed in advance (Waudby-Smith & Ramdas, 2024)."""
    lam = default_stakes() if stakes is None else np.asarray(stakes, float)
    pos = np.asarray(pos, float)[..., None]; tie = np.asarray(tie, float)[..., None]; neg = np.asarray(neg, float)[..., None]
    m = np.asarray(m, float)[..., None]
    def logk(l):
        with np.errstate(divide='ignore', invalid='ignore'):
            lk = pos * np.log1p(l * (1 - m)) + tie * np.log1p(-l * m) + neg * np.log1p(l * (-1 - m))
        lk = np.where(np.isnan(lk), -np.inf, lk)
        return logsumexp(lk, axis=-1) - np.log(lam.size)
    return np.maximum(logk(lam), logk(-lam))


def _invert_capital(logcap, delta, lo0=-1.0, hi0=1.0, coarse=201, iters=14):
    """Invert a quasi-convex capital process: CS = {m : logcap(m) < log(1/delta)}.

    logcap(m) must accept an array m broadcastable with the count arrays and
    return log capital with the counts' shape. Coarse grid, then elementwise
    bisection of both boundaries. Returns (lo, hi) with nan when empty."""
    thr = np.log(1 / delta)
    ms = np.linspace(lo0, hi0, coarse)
    inside = np.stack([logcap(np.asarray(m)) < thr for m in ms], -1)
    any_in = inside.any(-1)
    first = np.argmax(inside, axis=-1); last = inside.shape[-1] - 1 - np.argmax(inside[..., ::-1], axis=-1)
    # lower boundary between ms[first-1] (outside) and ms[first] (inside)
    a = np.where(first > 0, ms[np.maximum(first - 1, 0)], lo0); b = ms[first]
    for _ in range(iters):
        mid = (a + b) / 2
        ins = logcap(mid) < thr
        a = np.where(ins, a, mid); b = np.where(ins, mid, b)
    lo = np.where(first > 0, b, lo0)
    a = ms[last]; b = np.where(last < coarse - 1, ms[np.minimum(last + 1, coarse - 1)], hi0)
    for _ in range(iters):
        mid = (a + b) / 2
        ins = logcap(mid) < thr
        a = np.where(ins, mid, a); b = np.where(ins, b, mid)
    hi = np.where(last < coarse - 1, a, hi0)
    return np.where(any_in, lo, np.nan), np.where(any_in, hi, np.nan)


def betting_cs_ternary(pos, tie, neg, delta=0.05, stakes=None, coarse=201):
    """Two-sided time-uniform CS for the mean of a ternary score by inverting
    the hedged mixture capital process (quasi-convex in m)."""
    pos = np.asarray(pos, float); tie = np.asarray(tie, float); neg = np.asarray(neg, float)
    f = lambda m: betting_log_capital_ternary(pos, tie, neg, np.broadcast_to(m, pos.shape), stakes)
    return _invert_capital(f, delta, -1.0, 1.0, coarse)


def betting_log_capital_bernoulli(k, n, q, stakes=None):
    """log hedged capital for a Bernoulli mean q from k successes in n trials
    (scores in {0,1}; stakes scaled to range 1)."""
    lam = (default_stakes() if stakes is None else np.asarray(stakes, float)) * 2.0  # |x-q|<=1 => lam<1
    k = np.asarray(k, float)[..., None]; n = np.asarray(n, float)[..., None]; q = np.asarray(q, float)[..., None]
    def logk(l):
        with np.errstate(divide='ignore', invalid='ignore'):
            lk = k * np.log1p(l * (1 - q)) + (n - k) * np.log1p(-l * q)
        lk = np.where(np.isnan(lk), -np.inf, lk)
        return logsumexp(lk, axis=-1) - np.log(lam.size)
    return np.maximum(logk(lam), logk(-lam))


def win_ratio_cs_decided(n_win, n_loss, delta=0.05, stakes=None, coarse=201):
    """Time-uniform CS for the win ratio from decided (non-tied) pairs.

    Among decided pairs the win indicator is Bernoulli(q) with q = WR/(1+WR)
    (for iid pairs, conditioning on 'decided' preserves independence), so a
    betting CS for q over the decided subsequence maps to WR = q/(1-q).
    Returns (lower, upper); upper is inf if q=1 is not excluded."""
    n_win = np.asarray(n_win, float); n_loss = np.asarray(n_loss, float); n = n_win + n_loss
    f = lambda q: betting_log_capital_bernoulli(n_win, n, np.broadcast_to(q, n_win.shape), stakes)
    qlo, qhi = _invert_capital(f, delta, 0.0, 1.0, coarse)
    with np.errstate(divide='ignore', invalid='ignore'):
        return qlo / (1 - qlo), np.where(qhi >= 1 - 1e-12, np.inf, qhi / (1 - qhi))


def win_odds_from_nb(nb):
    """Win odds = (1+NB)/(1-NB); monotone, so CS bounds map directly."""
    nb = np.asarray(nb, float)
    with np.errstate(divide='ignore'):
        return (1 + nb) / (1 - nb)
