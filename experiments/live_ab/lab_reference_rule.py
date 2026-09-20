"""The reference rule of protocol_FINAL.md section 8.9: a SECOND, independent code path.

Group G1.  Permitted imports: standard library + numpy + src/winstats.py ONLY.  This module
imports nothing from the `lab_*` namespace at all -- not lab_monitor, not lab_enclosure,
not even lab_common -- so that no defect of the live statistical core can reach the shadow
(ARCHITECTURE_FINAL.md 3.8b / 3.16, AD-7).

It is written against protocol_FINAL.md sections 6.2, 6.3, 7.3, 7.5 and 8.1-8.4 and against
nothing else.  It is decision-defining code: it is in the freeze bundle with its own
SHA-256 (`monitor.reference_rule_sha256`), it can never be amended, and a proven defect in
it is protocol 6.4 row 24.

Rule, restated from the protocol so that this file is self-contained:

  * 7.3  A pair occupies an immutable enrollment position.  The denominator is always `n`,
         the number of fully enrolled pairs, never the number completed.
  * 7.5  Enclosures start at [-1, 1] and are narrowed ONLY by enumerating feasible
         completions.  Success enclosure [sA_low - sB_high, sA_high - sB_low] with A the
         candidate.  Cost certificate: with the revealed episode successful and the partner
         pending at certified elapsed `ell`, (1 - tol) * ell > L_r + 1e-9 collapses the
         hierarchy enclosure to [sgn, sgn].
  * 8.2  r = normal_mixture_radius(n, alpha=alpha_gate, rho=rho, variance_process=n);
         L_j = sum(lower_j[:n])/n - r, U_j = sum(upper_j[:n])/n + r, clipped to [-1, 1].
  * 8.3  Evaluation triggers: every pair_enrolled; every pre-decision episode_revealed;
         every ingested llm_request / llm_response / llm_error that RAISES the certified
         `ell` of a still-pending episode of an enrolled pair; every resume, once; and
         every post-decision drain reveal, which updates but never decides.
  * 8.4  At n >= n_min, in this fixed order: U_h < 0 -> harm_keep_incumbent;
         L_h > 0 and L_s > -delta -> deploy_candidate; otherwise continue.
  * 8.9  The normative decision of a trial is the FIRST prefix n* >= n_min at which a
         condition of 8.4 holds, or abstention.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np                                             # noqa: E402
import winstats                                                # noqa: E402

CALL_TYPES: tuple[str, ...] = ('llm_request', 'llm_response', 'llm_error')

#: The event types that carry an evaluation of the rule.  A resumed invocation that writes
#: none of them before the trial ends never reaches "the last fully enrolled prefix before
#: any new enrollment" and therefore produces no resume evaluation (protocol 8.3 trigger 4).
EVALUATION_BEARING: frozenset[str] = frozenset(
    {'pair_enrolled', 'coin_drawn', 'arm_assigned_by_decision', 'episode_revealed',
     'decision', 'traffic_switch'} | set(CALL_TYPES))
FULL_LO: float = -1.0
FULL_HI: float = 1.0


@dataclass(frozen=True)
class RefLook:
    trigger: str            # 'enroll' | 'reveal' | 'call' | 'resume' | 'drain'
    n: int
    sum_lower_h: float
    sum_upper_h: float
    sum_lower_s: float
    sum_upper_s: float
    radius: float
    L_h: float
    U_h: float
    L_s: float
    U_s: float
    action: str             # 'none'|'harm_keep_incumbent'|'deploy_candidate'|
                            # 'horizon_no_decision'


# ---------------------------------------------------------------------------
# the frozen hierarchy (protocol 6.2), rebuilt from the config and checked
# ---------------------------------------------------------------------------
def _tiers(cfg: Mapping) -> tuple[list, float]:
    """The two-tier hierarchy of protocol 6.2 and its cost tolerance.  Raises ValueError
    unless the config carries exactly the frozen two-row array."""
    rows = cfg.get('hierarchy')
    if not isinstance(rows, (list, tuple)) or len(rows) != 2:
        raise ValueError('hierarchy must be exactly the frozen two-row array (protocol 6.2)')
    want = (('success', True, 0.0, 0.0), ('cost', False, 0.0, 0.05))
    got = []
    for row in rows:
        got.append((row.get('name'), bool(row.get('higher_better')),
                    float(row.get('absolute_tolerance', 0.0)),
                    float(row.get('relative_tolerance', 0.0))))
    if tuple(got) != want:
        raise ValueError(f'hierarchy {got!r} is not the frozen two-row array {want!r}')
    tiers = [winstats.Tier('success', higher_better=True, absolute_tolerance=0.0,
                           relative_tolerance=0.0),
             winstats.Tier('cost', higher_better=False, absolute_tolerance=0.0,
                           relative_tolerance=0.05)]
    return tiers, 0.05


def _monitor_constants(cfg: Mapping) -> tuple[float, float, float, int, int]:
    """(alpha_gate, rho, delta, n_min, n_max).  No defaults anywhere: a config that fails
    to carry one of the five frozen statistical fields raises (audit m9)."""
    mon = cfg.get('monitor')
    if not isinstance(mon, Mapping):
        raise ValueError('config has no monitor block')
    for key in ('alpha_gate', 'rho', 'delta', 'n_min'):
        if mon.get(key) is None:
            raise ValueError(f'monitor.{key} is required and has no default')
    n_max = mon.get('n_max')
    if n_max is None:
        roster = cfg.get('roster') or {}
        n_max = roster.get('n_pairs')
    if n_max is None:
        raise ValueError('monitor.n_max (== roster.n_pairs) is required and has no default')
    return (float(mon['alpha_gate']), float(mon['rho']), float(mon['delta']),
            int(mon['n_min']), int(n_max))


# ---------------------------------------------------------------------------
# enrollment-indexed records
# ---------------------------------------------------------------------------
class _Episode:
    __slots__ = ('arm', 'revealed', 'success', 'latency_s', 't_c1_ns', 't_max_ns')

    def __init__(self) -> None:
        self.arm: str | None = None
        self.revealed: bool = False
        self.success: int | None = None
        self.latency_s: float | None = None
        self.t_c1_ns: int | None = None
        self.t_max_ns: int | None = None

    @property
    def ell(self) -> float:
        """Certified elapsed lower bound (protocol 7.5 item 4).  0.0 when no request was
        ever spooled (finding N5)."""
        if self.t_c1_ns is None or self.t_max_ns is None:
            return 0.0
        return max(0.0, (self.t_max_ns - self.t_c1_ns) / 1e9)

    def note_stamp(self, t_c1_ns: int | None, stamps: Sequence[int]) -> bool:
        """Fold worker stamps in; True iff the certified elapsed time rose."""
        before = self.ell
        if t_c1_ns is not None:
            self.t_c1_ns = t_c1_ns if self.t_c1_ns is None else min(self.t_c1_ns, t_c1_ns)
        for t in stamps:
            if t is None:
                continue
            self.t_max_ns = t if self.t_max_ns is None else max(self.t_max_ns, t)
        return self.ell > before


class _Pair:
    __slots__ = ('pair', 'arrivals', 'episodes')

    def __init__(self, pair: int, arrivals: Sequence[int]) -> None:
        self.pair = pair
        self.arrivals = (int(arrivals[0]), int(arrivals[1]))
        self.episodes: dict[int, _Episode] = {a: _Episode() for a in self.arrivals}

    def by_arm(self, arm: str) -> _Episode | None:
        for ep in self.episodes.values():
            if ep.arm == arm:
                return ep
        return None


def _success_enclosure(cand: _Episode | None, inc: _Episode | None) -> tuple[float, float]:
    """protocol 7.5 item 2, literally.  A pending episode has s_low = 0, s_high = 1:
    absence of failure is not success (item 3)."""
    def lo_hi(ep: _Episode | None) -> tuple[float, float]:
        if ep is not None and ep.revealed:
            s = float(ep.success or 0)
            return s, s
        return 0.0, 1.0
    a_lo, a_hi = lo_hi(cand)
    b_lo, b_hi = lo_hi(inc)
    return a_lo - b_hi, a_hi - b_lo


def _hierarchy_enclosure(cand: _Episode | None, inc: _Episode | None,
                         tiers: list, tol: float) -> tuple[float, float, int]:
    """protocol 7.5 item 5 by enumeration.  Returns (lo, hi, decisive_tier)."""
    both = (cand is not None and cand.revealed and inc is not None and inc.revealed)
    if both:
        assert cand is not None and inc is not None
        both_ok = bool(cand.success) and bool(inc.success)
        a = [float(cand.success or 0), float(cand.latency_s or 0.0)]
        b = [float(inc.success or 0), float(inc.latency_s or 0.0)]
        z, tier = winstats.compare(np.asarray(a), np.asarray(b), tiers,
                                   eligible=np.asarray([True, both_ok]))
        zi = int(np.asarray(z).reshape(())[()])
        ti = int(np.asarray(tier).reshape(())[()])
        return float(zi), float(zi), ti
    revealed = None
    pending = None
    sgn = 0.0
    if cand is not None and cand.revealed and (inc is None or not inc.revealed):
        revealed, pending, sgn = cand, inc, 1.0
    elif inc is not None and inc.revealed and (cand is None or not cand.revealed):
        revealed, pending, sgn = inc, cand, -1.0
    if revealed is None:
        return FULL_LO, FULL_HI, -1                 # neither revealed
    ell = pending.ell if pending is not None else 0.0
    if not revealed.success:
        # the partner either succeeds (it wins tier 0: Z = -sgn) or fails (joint failure,
        # a tie: Z = 0)
        feasible = (0.0, -sgn)
        return min(feasible), max(feasible), -1
    # revealed episode succeeded
    l_r = float(revealed.latency_s or 0.0)
    if (1.0 - tol) * ell > l_r + 1e-9:
        return sgn, sgn, 1                          # the cost certificate binds
    return FULL_LO, FULL_HI, -1


def _pair_enclosure(p: _Pair, tiers: list, tol: float) -> tuple[float, float, float, float,
                                                                bool, int]:
    cand = p.by_arm('candidate')
    inc = p.by_arm('incumbent')
    s_lo, s_hi = _success_enclosure(cand, inc)
    h_lo, h_hi, tier = _hierarchy_enclosure(cand, inc, tiers, tol)
    collapsed = (h_lo == h_hi and s_lo == s_hi)
    for lo, hi in ((h_lo, h_hi), (s_lo, s_hi)):
        if not (FULL_LO - 1e-12 <= lo <= hi <= FULL_HI + 1e-12):
            raise ValueError(f'enclosure [{lo}, {hi}] is outside [-1, 1]')
    return h_lo, h_hi, s_lo, s_hi, collapsed, tier


# ---------------------------------------------------------------------------
# the band and the decision (protocol 8.2, 8.4)
# ---------------------------------------------------------------------------
def _radius(n: int, alpha_gate: float, rho: float) -> float:
    return float(winstats.normal_mixture_radius(n, alpha=alpha_gate, rho=rho,
                                                variance_process=n))


def _look(trigger: str, pairs: Sequence[_Pair], tiers: list, tol: float,
          alpha_gate: float, rho: float, delta: float, n_min: int, n_max: int,
          decided: bool) -> RefLook:
    n = len(pairs)
    if n == 0:
        raise ValueError('a look at n == 0 decides nothing and is never recorded')
    lows_h: list[float] = []
    highs_h: list[float] = []
    lows_s: list[float] = []
    highs_s: list[float] = []
    n_collapsed = 0
    for p in pairs:
        h_lo, h_hi, s_lo, s_hi, collapsed, _ = _pair_enclosure(p, tiers, tol)
        lows_h.append(h_lo)
        highs_h.append(h_hi)
        lows_s.append(s_lo)
        highs_s.append(s_hi)
        n_collapsed += int(collapsed)
    sum_lower_h = math.fsum(lows_h)
    sum_upper_h = math.fsum(highs_h)
    sum_lower_s = math.fsum(lows_s)
    sum_upper_s = math.fsum(highs_s)
    r = _radius(n, alpha_gate, rho)
    L_h = max(FULL_LO, sum_lower_h / n - r)
    U_h = min(FULL_HI, sum_upper_h / n + r)
    L_s = max(FULL_LO, sum_lower_s / n - r)
    U_s = min(FULL_HI, sum_upper_s / n + r)
    action = 'none'
    if not decided and trigger != 'drain':
        if n >= n_min:
            if U_h < 0.0:
                action = 'harm_keep_incumbent'
            elif L_h > 0.0 and L_s > -delta:
                action = 'deploy_candidate'
        if action == 'none' and n >= n_max and n_collapsed == n:
            action = 'horizon_no_decision'
    return RefLook(trigger=trigger, n=n, sum_lower_h=sum_lower_h, sum_upper_h=sum_upper_h,
                   sum_lower_s=sum_lower_s, sum_upper_s=sum_upper_s, radius=r,
                   L_h=L_h, U_h=U_h, L_s=L_s, U_s=U_s, action=action)


# ---------------------------------------------------------------------------
# the public interface (ARCHITECTURE_FINAL.md 3.8b)
# ---------------------------------------------------------------------------
def looks_from_chain(events: Sequence[Mapping], cfg: Mapping, trial: str) -> list[RefLook]:
    """[pure] The whole rule, rebuilt independently: enrollment-indexed records, the
    enclosure enumeration of protocol 7.5 (including the 0.95 cost certificate), math.fsum
    over the full prefix, winstats.normal_mixture_radius(n, alpha, rho,
    variance_process=n), the clip to [-1, 1], and the decision order harm-then-deploy at
    n >= n_min.  Scores of resolved pairs are computed ONLY through winstats.compare.  No
    import of lab_monitor, lab_enclosure or lab_common."""
    tiers, tol = _tiers(cfg)
    alpha_gate, rho, delta, n_min, n_max = _monitor_constants(cfg)
    pairs: list[_Pair] = []
    by_index: dict[int, _Pair] = {}
    staged: dict[int, _Pair] = {}
    arrival_pair: dict[int, _Pair] = {}
    decided = False
    resume_boundary = False
    resume_armed = False
    looks: list[RefLook] = []

    def emit(trigger: str) -> None:
        looks.append(_look(trigger, pairs, tiers, tol, alpha_gate, rho, delta,
                           n_min, n_max, decided))

    def flush_resume() -> None:
        """protocol 8.3 trigger 4: the resume evaluation is made *once*, at the last fully
        enrolled prefix **before any new enrollment** -- that is, after the recovered
        orphans have been revealed (14.5 items 3 and 6) and before the next pair is
        randomized (14.5 item 4).  After a decision nothing is evaluated but the drain
        reveal (9.1 item 4), so a resume in the follow-up phase produces no look."""
        nonlocal resume_armed, resume_boundary
        if resume_armed and pairs and not decided:
            emit('resume')
        resume_armed = False
        resume_boundary = False

    for ev in events:
        if ev.get('chain') not in (None, trial):
            continue
        etype = ev.get('type')
        body: Any = ev.get('body') or {}
        if resume_boundary and etype in EVALUATION_BEARING:
            resume_armed = True
        if etype == 'pair_enrolled':
            idx = int(body['pair'])
            if idx in by_index or idx in staged:
                # A re-enrollment after a crash between pair_enrolled and coin_drawn
                # (protocol 12.2 #7, re_enrolled) restates an existing position: the
                # prefix does not grow, so it is not a new evaluation.
                if not body.get('re_enrolled'):
                    raise ValueError(f'pair {idx} enrolled twice without re_enrolled')
                continue
            if idx != len(pairs) + 1:
                raise ValueError(f'pair {idx} enrolled out of order at prefix {len(pairs)}')
            # The prefix n is "the count of chain-valid coin_drawn events" and "changes
            # only at a coin_drawn" (protocol 7.3 item 2), and the state machine writes
            # the enroll evaluation in state COMMITTED, i.e. after the coin
            # (ARCHITECTURE_FINAL.md 7.1 rows 5 and 6).  A pre-enrolled pair that was
            # never randomized therefore holds no position and produces no evaluation.
            # [G5 integration fix, see README.]
            staged[idx] = _Pair(idx, body['arrivals'])
        elif etype == 'coin_drawn':
            idx = int(body['pair'])
            p = staged.pop(idx, None) or by_index.get(idx)
            if p is None:
                raise ValueError(f'coin_drawn for unenrolled pair {idx}')
            fresh = idx not in by_index
            if fresh and idx != len(pairs) + 1:
                raise ValueError(
                    f'pair {idx} randomized out of order at prefix {len(pairs)}')
            for arrival_s, arm in body['assignment'].items():
                a = int(arrival_s)
                if a not in p.episodes:
                    raise ValueError(f'coin_drawn assigns arrival {a} outside pair {idx}')
                p.episodes[a].arm = arm
            if fresh:
                # the resume evaluation is at the prefix BEFORE this new enrollment
                flush_resume()
                pairs.append(p)
                by_index[idx] = p
                for a in p.arrivals:
                    arrival_pair[a] = p
                emit('enroll')
        elif etype in CALL_TYPES:
            if decided:
                continue
            a = int(body['arrival'])
            p = arrival_pair.get(a)
            if p is None:
                continue                                  # a follow-up-cohort arrival
            ep = p.episodes[a]
            if ep.revealed:
                continue
            stamps = [body.get('t_send_ns'), body.get('t_recv_ns')]
            if ep.note_stamp(body.get('t_c1_ns'), [s for s in stamps if s is not None]):
                emit('call')
        elif etype == 'episode_revealed':
            if body.get('post_decision'):
                continue                                  # outside all inference (9.x)
            a = int(body['arrival'])
            p = arrival_pair.get(a)
            if p is None:
                continue
            ep = p.episodes[a]
            if ep.arm is None:
                ep.arm = body['arm']
            if ep.revealed:
                raise ValueError(f'arrival {a} revealed twice')
            out = body['outcome']
            ep.revealed = True
            ep.success = int(out['success'])
            ep.latency_s = float(out['latency_s'])
            emit('drain' if decided else 'reveal')
        elif etype == 'decision':
            decided = True
        elif etype == 'invocation_started':
            if body.get('resumed'):
                # "every resume, once" (protocol 8.3 trigger 4): a boundary whose
                # evaluation the previous invocation never reached is still one resume, so
                # it is flushed here, at the prefix it held, before the new boundary opens.
                flush_resume()
                resume_boundary = True
                resume_armed = False
    flush_resume()
    return looks


def shadow_step(events: Sequence[Mapping], cfg: Mapping, trial: str) -> RefLook:
    """[pure] The last look of looks_from_chain(...) -- what the orchestrator calls at
    every evaluation to fill `monitor_update.shadow` and to set `shadow.mismatch`
    (protocol 8.9)."""
    looks = looks_from_chain(events, cfg, trial)
    if not looks:
        raise ValueError('no evaluation has occurred yet on this chain')
    return looks[-1]


def decide_from_chain(events: Sequence[Mapping], cfg: Mapping, trial: str) -> dict:
    """[pure] The NORMATIVE decision of a trial (protocol 8.9): the FIRST prefix
    n* >= n_min at which a condition of 8.4 holds, or abstention."""
    looks = looks_from_chain(events, cfg, trial)
    for lk in looks:
        if lk.action != 'none':
            return {'kind': lk.action, 'n': lk.n, 'L_h': lk.L_h, 'U_h': lk.U_h,
                    'L_s': lk.L_s, 'U_s': lk.U_s}
    if looks:
        lk = looks[-1]
        return {'kind': 'none', 'n': None, 'L_h': lk.L_h, 'U_h': lk.U_h,
                'L_s': lk.L_s, 'U_s': lk.U_s}
    return {'kind': 'none', 'n': None, 'L_h': FULL_LO, 'U_h': FULL_HI,
            'L_s': FULL_LO, 'U_s': FULL_HI}
