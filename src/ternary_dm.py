"""Isolated complete-data Dirichlet-mixture test for iid ternary scores.

The four numerical routines were extracted without changing their formulas
from contributed wincs.py at commit 168e7be. They do not use that module's
generic projection solver or its two-sided betting inversion helpers.

Counts use (win, tie, loss) order and must be nonnegative integers with the
same shape. The Dirichlet prior must be fixed, finite and positive. The
model is iid categorical records with a fixed probability vector. This is
not a mean-only drift or adaptive-HT inference routine, a simultaneous
multi-gate confidence region, or an asynchronous lower-score plug-in.

Reference: Lindon and Malek, NeurIPS 2022, Section 2, Theorem 2.4.
See evidence/dm_baseline.md for assumptions, proof and reproduction record.
"""
from __future__ import annotations

import numpy as np
from scipy.special import gammaln


def log_beta(a):
    a = np.asarray(a, float)
    return gammaln(a).sum(-1) - gammaln(a.sum(-1))


def loglik(counts, p):
    counts = np.asarray(counts, float); p = np.asarray(p, float)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(counts > 0, counts * np.log(p), 0.0).sum(-1)


def ternary_constrained_loglik(xw, xt, xl, c):
    """Constrained maximum log likelihood at pw-pl=c, including endpoints."""
    xw = np.asarray(xw, float); xt = np.asarray(xt, float); xl = np.asarray(xl, float)
    c = np.asarray(c, float)
    n = xw + xt + xl
    lo = np.maximum(0.0, -c); hi = (1 - c) / 2
    A = -2 * xw - 2 * xl - 2 * xt
    B = xw * (1 - c) + xl * (1 - c) - 2 * xl * c - 2 * xt * c
    C = xl * c * (1 - c)
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
    """Log composite-null e-process for iid ternary mean <= threshold.

    The null likelihood is maximized at the MLE when it is feasible and
    otherwise at the equality boundary. Infimum of point-null mixture
    martingales is dominated by the true-null martingale; it need not
    itself be a martingale. The function is not monotone in raw scores.
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


def validated_log_eprocess(xw, xt, xl, threshold=0.0, prior=(1.0, 1.0, 1.0)):
    """Checked public entry point; broadcasts counts and candidate thresholds."""
    w, t, l, c = np.broadcast_arrays(
        np.asarray(xw, float), np.asarray(xt, float),
        np.asarray(xl, float), np.asarray(threshold, float))
    for x in (w, t, l):
        if not np.all(np.isfinite(x) & (x >= 0) & (x == np.floor(x))):
            raise ValueError('Categorical counts must be finite nonnegative integers.')
    if not np.all(np.isfinite(c) & (c >= -1) & (c <= 1)):
        raise ValueError('The ternary null threshold must lie in [-1, 1].')
    a = np.asarray(prior, float)
    if a.shape != (3,) or not np.all(np.isfinite(a) & (a > 0)):
        raise ValueError('The fixed Dirichlet prior needs three positive finite parameters.')
    return ternary_log_eprocess_nb(w, t, l, c, a)
