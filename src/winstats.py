"""Prespecified hierarchical comparisons and finite-sample monitoring.

These are implementations of established bounded-mean martingale constructions,
not claims of a new confidence-sequence inequality. See paper/theory.tex.
"""
from dataclasses import dataclass
import numpy as np
from scipy.special import logsumexp


@dataclass(frozen=True)
class Tier:
    name: str
    higher_better: bool = True
    absolute_tolerance: float = 0.0
    relative_tolerance: float = 0.0

    def __post_init__(self):
        if any(not np.isfinite(t) or t < 0 for t in (self.absolute_tolerance, self.relative_tolerance)):
            raise ValueError('Tier tolerances must be finite and nonnegative')
        if not isinstance(self.higher_better, bool):
            raise ValueError('higher_better must be a boolean')


def compare(a, b, tiers, eligible=None):
    """Broadcast arrays (..., tiers); ties include exact threshold equality.

    eligible is an optional (..., tiers) mask, fixed by the outcome protocol.
    Returns signed preference and zero-based decisive tier (-1 for tie).
    """
    if not tiers:
        raise ValueError('At least one comparison tier is required')
    a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
    if a.ndim == 0:
        raise ValueError('Outcomes need a final tier dimension')
    if a.shape[-1] != len(tiers) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Expected complete finite outcomes and one column per tier')
    result = np.zeros(a.shape[:-1], dtype=np.int8)
    tier_index = np.full(a.shape[:-1], -1, dtype=np.int16)
    for k, tier in enumerate(tiers):
        tol = tier.absolute_tolerance + tier.relative_tolerance * np.maximum(np.abs(a[..., k]), np.abs(b[..., k]))
        delta = (a[..., k] - b[..., k]) * (1 if tier.higher_better else -1)
        decisive = (tier_index == -1) & (np.abs(delta) > tol)
        if eligible is not None:
            decisive &= np.asarray(eligible)[..., k]
        result[decisive] = np.sign(delta[decisive]).astype(np.int8)
        tier_index[decisive] = k
    return result, tier_index


def normal_mixture_radius(n, alpha=.05, rho=100., variance_process=None):
    """Two-sided normal-mixture CS for scores in [-1,1]; V=n by default.

    For other known predictable ranges r_i use V=sum(r_i**2/4).
    rho and alpha must be fixed before observing monitored outcomes.
    """
    n = np.asarray(n, float)
    if alpha <= 0 or alpha >= 1 or rho <= 0 or np.any(n <= 0):
        raise ValueError('Require 0<alpha<1, rho>0, n>0')
    v = n if variance_process is None else np.asarray(variance_process, float)
    return np.sqrt((v + rho) * np.log((v + rho) / (rho * alpha**2))) / n


def betting_log_e_ternary(positive, negative, n, threshold=0., bets=40):
    """Mixture of constant bets for Z in {-1,0,1}, H0:E[Z|past]<=threshold.

    Counts may have arbitrary broadcast shapes. Parameters are chosen ex ante.
    This tests a stationary or pointwise conditional null; it does not test an
    unrestricted drifting running-average null.
    """
    if not -1 < threshold < 1:
        raise ValueError('Threshold must lie in (-1,1)')
    positive, negative, n = np.broadcast_arrays(positive, negative, n)
    if np.any(positive < 0) or np.any(negative < 0) or np.any(positive + negative > n):
        raise ValueError('Invalid ternary counts')
    lam = np.geomspace(1e-4, .99/(1+threshold), bets)
    zero = n-positive-negative
    wealth = (positive[..., None]*np.log1p(lam*(1-threshold))
              + negative[..., None]*np.log1p(lam*(-1-threshold))
              + zero[..., None]*np.log1p(-lam*threshold))
    return logsumexp(wealth, axis=-1) - np.log(bets)


def summary(scores):
    z = np.asarray(scores)
    w, l, t = np.mean(z > 0), np.mean(z < 0), np.mean(z == 0)
    return dict(p_win=float(w), p_loss=float(l), p_tie=float(t),
                net_benefit=float(w-l), win_ratio=float(w/l) if l else None,
                win_odds=float((w+t/2)/(l+t/2)) if l+t/2 else None)
