"""Deterministic acceptance fixtures for the independent #12 validation.

SOURCE DECLARATION -- files read while writing this module
----------------------------------------------------------
Read: reviews/arxiv_live_design_guidance.md, src/winstats.py, the issue-#12 task
text, and this directory's own ``vband.py`` (written by the same independent
author).  NOT read, opened, grepped or imported: experiments/live_ab/lab_monitor.py,
experiments/live_ab/lab_enclosure.py, experiments/live_ab/lab_reference_rule.py,
experiments/live_ab/design/protocol_FINAL.md sections 7-8, or anything else under
experiments/live_ab/.

Every expected value below is derived BY HAND from the frozen definitions, or by
exhaustive enumeration, and written out as a literal together with the
derivation.  The derivations never consult the #11 implementation.

Frozen definitions used in the derivations
------------------------------------------
Tier 0 ``success``: higher better, zero tolerance.
Tier 1 ``cost``:    lower better, relative tolerance .05, absolute tolerance 0,
                    ELIGIBLE ONLY WHEN BOTH EPISODES SUCCEED.
``compare`` calls a tier decisive iff ``|a-b| > atol + rtol*max(|a|,|b|)``; exact
threshold equality is therefore a TIE.  Joint failure is a tie regardless of cost.
Hierarchy score is oriented candidate-minus-incumbent and lies in {-1, 0, +1}.
Success score is ``sA - sB`` in {-1, 0, +1}.

Band (guidance item 3), on the current full enrolled prefix ``n = N(t)``::

    r   = sqrt((n + rho) * log((n + rho) / (rho * alpha_gate**2))) / n
    L_j = clip(sum(lower_j[:n]) / n - r, -1, 1)
    U_j = clip(sum(upper_j[:n]) / n + r, -1, 1)

The fixtures recompute ``r`` from that closed form LITERALLY (``literal_radius``)
rather than calling ``vband``, so the band assembly -- denominator, sign, clip --
is cross-checked against a second transcription of the guidance formula.

Run ``python vfixtures.py`` to execute every fixture and print a report.
"""
from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Hashable, List, Optional, Sequence, Tuple

import vband
from vband import (
    ALPHA_GATE, CONTINUE, DELTA, DEPLOY, Band, Enclosure, EnclosureContradiction,
    LookResult, N_MIN, ProtocolViolation, RETAIN_INCUMBENT, RHO,
    SwitchPhaseError, ValidationError, ValidationMonitor, decide,
    normal_mixture_band,
)

__all__ = ["literal_radius", "LOCKED_RADII", "replay", "FixtureCase",
           "ALL_FIXTURES", "ATOM_COSTS", "run_all", "main",
           "check_protocol_config_agreement", "scan_sources_for_forbidden_paths",
           "check_pinned_file_hashes", "sha256_file",
           "PROTOCOL_PATH", "CELLS_PATH", "HERE", "PINNED_DIR",
           "PINNED_MANIFEST", "REPO_ROOT"]

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PROTOCOL_PATH = HERE / "PROTOCOL.md"
CELLS_PATH = HERE / "cells.json"

_REL = 1e-12
_ABS = 1e-12


def _close(x: float, y: float, rel: float = _REL, abs_: float = _ABS) -> bool:
    return abs(x - y) <= max(abs_, rel * max(abs(x), abs(y)))


# ---------------------------------------------------------------------------
# A second, literal transcription of the guidance radius formula
# ---------------------------------------------------------------------------
def literal_radius(n: int, alpha_gate: float = ALPHA_GATE, rho: float = RHO) -> float:
    """``sqrt((n+rho)*log((n+rho)/(rho*alpha**2)))/n`` written out by hand.

    This duplicates ``normal_mixture_radius(n, alpha, rho, variance_process=n)``
    on purpose: agreement is evidence that ``vband`` passes the intended
    arguments (in particular ``variance_process=n``, i.e. V_n = n for scores
    bounded in [-1,1]).
    """
    if n <= 0:
        raise ValueError("radius undefined at n = 0")
    return math.sqrt((n + rho) * math.log((n + rho) / (rho * alpha_gate ** 2))) / n


# Values locked before any simulation outcome exists, at alpha_gate = .00625,
# rho = 100, computed from the closed form above.
LOCKED_RADII: Dict[int, float] = {
    1: 32.03420194250831,
    2: 16.104000483512714,
    3: 10.793672851202366,
    4: 8.138316425006838,
    6: 5.482581896562951,
    100: 0.4656929205179653,
    500: 0.1692957679307717,
    2000: 0.08323044386401118,
}


# ---------------------------------------------------------------------------
# Event replay
# ---------------------------------------------------------------------------
def replay(events: Sequence[tuple], cost_cap: float = 100.0,
           record_history: bool = False,
           monitor: Optional[ValidationMonitor] = None
           ) -> Tuple[ValidationMonitor, Dict[str, LookResult]]:
    """Replay a declarative event script against a fresh independent monitor.

    Event forms::

        ('enroll', pair_id, coin, slot_first, slot_second[, cap])
        ('succeed', slot) | ('fail', slot)
        ('elapsed', slot, c) | ('cost_upper', slot, c)
        ('final', slot, success, cost) | ('timeout', slot)
        ('switch',) | ('followup', slot)
        ('look', label)
    """
    mon = monitor or ValidationMonitor(cost_cap=cost_cap, record_history=record_history)
    looks: Dict[str, LookResult] = {}
    for ev in events:
        kind = ev[0]
        if kind == "enroll":
            cap = ev[5] if len(ev) > 5 else None
            mon.enroll(ev[1], ev[2], ev[3], ev[4], cost_cap=cap)
        elif kind == "succeed":
            mon.observe_success(ev[1])
        elif kind == "fail":
            mon.observe_failure(ev[1])
        elif kind == "elapsed":
            mon.observe_elapsed_cost(ev[1], ev[2])
        elif kind == "cost_upper":
            mon.observe_cost_upper(ev[1], ev[2])
        elif kind == "final":
            mon.finalize(ev[1], ev[2], ev[3])
        elif kind == "timeout":
            mon.timeout(ev[1])
        elif kind == "switch":
            mon.switch()
        elif kind == "followup":
            mon.record_followup_arrival(ev[1])
        elif kind == "look":
            looks[ev[1]] = mon.look(ev[1])
        else:                                               # pragma: no cover
            raise ValueError(f"unknown event {kind!r}")
    return mon, looks


def _enc(mon: ValidationMonitor, pair_id: Hashable, score: str) -> Enclosure:
    return mon.pairs[mon._pair_index[pair_id]].enclosure(score)


def _expect_enc(fails: List[str], mon: ValidationMonitor, pair_id: Hashable,
                score: str, lo: float, hi: float, certified: bool) -> None:
    enc = _enc(mon, pair_id, score)
    if not (_close(enc.lo, lo) and _close(enc.hi, hi) and enc.certified is certified):
        fails.append(
            f"{pair_id!r}.{score}: got [{enc.lo}, {enc.hi}] certified={enc.certified}, "
            f"expected [{lo}, {hi}] certified={certified}")


def _expect(fails: List[str], label: str, got, want) -> None:
    ok = _close(got, want) if isinstance(got, float) and isinstance(want, float) \
        else got == want
    if not ok:
        fails.append(f"{label}: got {got!r}, expected {want!r}")


def _raises(fails: List[str], label: str, exc, fn: Callable, *a, **kw) -> None:
    try:
        fn(*a, **kw)
    except exc:
        return
    except Exception as e:                                  # noqa: BLE001
        fails.append(f"{label}: raised {type(e).__name__}({e}) instead of "
                     f"{exc.__name__}")
        return
    fails.append(f"{label}: did not raise {exc.__name__}")


def _band_of(name: str, n: int, lower: float, upper: float) -> Band:
    """A synthetic band used to exercise the decision rule in isolation."""
    return Band(name=name, n=n, sum_lower=lower * n, sum_upper=upper * n,
                mean_lower=lower, mean_upper=upper, radius=0.0,
                lower=lower, upper=upper)


@dataclass(frozen=True)
class FixtureCase:
    name: str
    covers: str
    derivation: str
    run: Callable[[], List[str]]


# ===========================================================================
# F01  pre-enrolled AB/BA assignment
# ===========================================================================
def _f01_pre_enrolled_orientation() -> List[str]:
    """Identical physical arrivals, opposite coins => opposite oriented scores.

    HAND DERIVATION.  cap 100.
      p1 coin 'AB': arrival a1 is arm A, a2 is arm B.
          a1 = (success 1, cost 10);  a2 = (success 1, cost 20).
          Tier 0: |1-1| = 0, not > 0  -> not decisive.
          Tier 1 eligible (both succeed).  tol = .05*max(10,20) = 1.0.
          |10-20| = 10 > 1 -> decisive; lower-better sign = sign(-(10-20)) = +1.
          hierarchy(p1) = +1.  success(p1) = 1 - 1 = 0.
      p2 coin 'BA': arrival b1 is arm B, b2 is arm A.
          b1 = (1, 10) is the INCUMBENT, b2 = (1, 20) is the CANDIDATE.
          tol = 1.0, |20-10| = 10 > 1, sign = sign(-(20-10)) = -1.
          hierarchy(p2) = -1.  success(p2) = 0.
      Sums at n = 2: hierarchy lower = upper = +1 + (-1) = 0; success 0.
    """
    fails: List[str] = []
    events = [
        ("enroll", "p1", "AB", "a1", "a2"),
        ("enroll", "p2", "BA", "b1", "b2"),
        ("final", "a1", 1, 10.0), ("final", "a2", 1, 20.0),
        ("final", "b1", 1, 10.0), ("final", "b2", 1, 20.0),
        ("look", "end"),
    ]
    mon, looks = replay(events)
    _expect_enc(fails, mon, "p1", "hierarchy", 1.0, 1.0, True)
    _expect_enc(fails, mon, "p2", "hierarchy", -1.0, -1.0, True)
    _expect_enc(fails, mon, "p1", "success", 0.0, 0.0, True)
    _expect_enc(fails, mon, "p2", "success", 0.0, 0.0, True)
    h1 = _enc(mon, "p1", "hierarchy").lo
    h2 = _enc(mon, "p2", "hierarchy").lo
    _expect(fails, "orientation flips the sign", h1, -h2)
    look = looks["end"]
    _expect(fails, "n enrolled", look.n_enrolled, 2)
    _expect(fails, "hierarchy sum_lower", look.hierarchy.sum_lower, 0.0)
    _expect(fails, "hierarchy sum_upper", look.hierarchy.sum_upper, 0.0)
    _expect(fails, "success sum_lower", look.success.sum_lower, 0.0)
    # arm_slots must follow the pre-enrolled coin, not the arrival order
    _expect(fails, "AB arm slots", mon.pairs[0].arm_slots(), ("a1", "a2"))
    _expect(fails, "BA arm slots", mon.pairs[1].arm_slots(), ("b2", "b1"))
    # the coin must be frozen before either task executes
    mon2 = ValidationMonitor()
    _raises(fails, "outcome before enrollment", ProtocolViolation,
            mon2.finalize, "never_enrolled", 1, 1.0)
    _raises(fails, "bad coin", ValidationError, mon2.enroll, "px", "AA", "x1", "x2")
    return fails


# ===========================================================================
# F02  exact enrollment denominators
# ===========================================================================
def _f02_enrollment_denominator() -> List[str]:
    """The denominator is enrolled pairs, never completed pairs.

    HAND DERIVATION.  Four pairs enrolled; two resolved to hierarchy +1 and
    success 0 (as in F01 p1); two untouched, so their enclosures are the
    starting full range [-1, 1] on both scores.
      hierarchy lowers = [+1, +1, -1, -1] -> sum 0,  mean_lower = 0/4 = 0.0
      hierarchy uppers = [+1, +1, +1, +1] -> sum 4,  mean_upper = 4/4 = 1.0
      success   lowers = [ 0,  0, -1, -1] -> sum -2, mean_lower = -0.5
      success   uppers = [ 0,  0, +1, +1] -> sum  2, mean_upper = +0.5
    A completed-only denominator would give hierarchy mean_lower = 2/2 = 1.0,
    which is the error this fixture exists to catch.
      r(4) = 8.138316425006838, so both hierarchy band ends clip:
      L = clip(0.0 - 8.138..., -1, 1) = -1;  U = clip(1.0 + 8.138..., -1, 1) = +1.
    """
    fails: List[str] = []
    events = [
        ("enroll", "c1", "AB", "s1", "s2"),
        ("enroll", "c2", "AB", "s3", "s4"),
        ("enroll", "c3", "AB", "s5", "s6"),
        ("enroll", "c4", "BA", "s7", "s8"),
        ("final", "s1", 1, 10.0), ("final", "s2", 1, 20.0),
        ("final", "s3", 1, 10.0), ("final", "s4", 1, 20.0),
        ("look", "end"),
    ]
    mon, looks = replay(events)
    look = looks["end"]
    _expect(fails, "n enrolled", look.n_enrolled, 4)
    _expect(fails, "hierarchy mean_lower", look.hierarchy.mean_lower, 0.0)
    _expect(fails, "hierarchy mean_upper", look.hierarchy.mean_upper, 1.0)
    _expect(fails, "success mean_lower", look.success.mean_lower, -0.5)
    _expect(fails, "success mean_upper", look.success.mean_upper, 0.5)
    if _close(look.hierarchy.mean_lower, 1.0):
        fails.append("hierarchy mean_lower equals the completed-only value 1.0")
    _expect(fails, "radius at n=4", look.hierarchy.radius, LOCKED_RADII[4])
    _expect(fails, "radius vs literal transcription", look.hierarchy.radius,
            literal_radius(4))
    _expect(fails, "hierarchy band lower clipped", look.hierarchy.lower, -1.0)
    _expect(fails, "hierarchy band upper clipped", look.hierarchy.upper, 1.0)
    _expect(fails, "no decision below n_min", look.decision, CONTINUE)
    _expect(fails, "unresolved fraction", look.unresolved_fraction, 0.5)
    # n = 0 displays the full range and does not decide
    empty = ValidationMonitor()
    zero = empty.look("n0")
    _expect(fails, "n=0 lower", zero.hierarchy.lower, -1.0)
    _expect(fails, "n=0 upper", zero.hierarchy.upper, 1.0)
    _expect(fails, "n=0 decision", zero.decision, CONTINUE)
    return fails


# ===========================================================================
# F03  repeated-update idempotence
# ===========================================================================
def _f03_repeated_update_idempotence() -> List[str]:
    """Replaying each reveal three times must leave the state untouched.

    HAND DERIVATION.  A = d1 finalises to (success 1, cost 40); B = d2
    finalises to (success 0, cost 12).  Tier 0: 1 > 0 -> hierarchy = +1.
    success = 1 - 0 = +1.  Elapsed-cost updates that do not exceed the current
    lower bound carry no information and must be exact no-ops.
    """
    fails: List[str] = []
    base = [
        ("enroll", "d", "AB", "d1", "d2"),
        ("elapsed", "d1", 30.0), ("succeed", "d1"), ("elapsed", "d1", 40.0),
        ("final", "d1", 1, 40.0),
        ("elapsed", "d2", 5.0), ("fail", "d2"), ("final", "d2", 0, 12.0),
    ]
    repeated: List[tuple] = []
    for ev in base:
        repeated.extend([ev] * (1 if ev[0] == "enroll" else 3))
    mon_a, _ = replay(base)
    mon_b, _ = replay(repeated)
    _expect(fails, "state signature under repeated updates",
            mon_a.state_signature(), mon_b.state_signature())
    _expect_enc(fails, mon_a, "d", "hierarchy", 1.0, 1.0, True)
    _expect_enc(fails, mon_a, "d", "success", 1.0, 1.0, True)
    # a stale elapsed-cost report is an exact no-op
    ep = mon_a.episodes["d1"]
    _expect(fails, "stale elapsed no-op", mon_a.episodes["d1"].with_elapsed_cost(1.0), ep)
    # a second final certificate with the same values is idempotent
    _expect(fails, "identical second certificate", ep.finalized(1, 40.0), ep)
    _raises(fails, "conflicting second certificate", EnclosureContradiction,
            ep.finalized, 0, 40.0)
    # bands are identical too
    _expect(fails, "band lower idempotent",
            mon_a.band("hierarchy").lower, mon_b.band("hierarchy").lower)
    return fails


# ===========================================================================
# F04  nonoverlapping pair ids / arrival positions
# ===========================================================================
def _f04_nonoverlapping_pair_ids() -> List[str]:
    """Pairs occupy two fixed, nonoverlapping arrival positions (guidance item 1)."""
    fails: List[str] = []
    mon = ValidationMonitor()
    mon.enroll("e1", "AB", "t1", "t2")
    _raises(fails, "duplicate pair id", ProtocolViolation,
            mon.enroll, "e1", "AB", "t3", "t4")
    _raises(fails, "reused arrival position (first)", ProtocolViolation,
            mon.enroll, "e2", "AB", "t1", "t5")
    _raises(fails, "reused arrival position (second)", ProtocolViolation,
            mon.enroll, "e3", "BA", "t6", "t2")
    _raises(fails, "self-overlapping pair", ProtocolViolation,
            mon.enroll, "e4", "AB", "t7", "t7")
    _raises(fails, "fact for an unowned position", ProtocolViolation,
            mon.observe_success, "t9")
    mon.enroll("e5", "BA", "t3", "t4")
    _expect(fails, "positions are immutable and sequential",
            [p.position for p in mon.pairs], [0, 1])
    _expect(fails, "enrolled pairs", mon.look("x").n_enrolled, 2)
    return fails


# ===========================================================================
# F05  completion-order permutations
# ===========================================================================
def _f05_completion_order_permutations() -> List[str]:
    """All 720 reveal orders of six episodes give one identical state.

    HAND DERIVATION of the three pair scores.
      q1 'AB' (e1 = A, e2 = B): A = (1, 10), B = (1, 20).
          both succeed; tol = .05*20 = 1.0; |10-20| = 10 > 1 -> A cheaper -> +1.
          hierarchy = +1, success = 0.
      q2 'BA' (e4 = A, e3 = B): A = (0, 7), B = (0, 5).
          JOINT FAILURE -> the cost tier is ineligible -> tie.
          hierarchy = 0, success = 0.
      q3 'AB' (e5 = A, e6 = B): A = (1, 30), B = (0, 8).
          Tier 0 decisive: 1 > 0 -> +1.  hierarchy = +1, success = +1.
      Sums at n = 3: hierarchy = +1 + 0 + +1 = 2 (lower = upper);
                     success   =  0 + 0 + +1 = 1.
      means: hierarchy 2/3, success 1/3.  r(3) = 10.793672851202366 -> both
      band ends clip to -1 and +1.
    """
    fails: List[str] = []
    enroll = [
        ("enroll", "q1", "AB", "e1", "e2"),
        ("enroll", "q2", "BA", "e3", "e4"),
        ("enroll", "q3", "AB", "e5", "e6"),
    ]
    reveals = [
        ("final", "e1", 1, 10.0), ("final", "e2", 1, 20.0),
        ("final", "e3", 0, 5.0), ("final", "e4", 0, 7.0),
        ("final", "e5", 1, 30.0), ("final", "e6", 0, 8.0),
    ]
    reference = None
    n_perm = 0
    for order in itertools.permutations(reveals):
        mon, _ = replay(list(enroll) + list(order))
        sig = mon.state_signature()
        band = (mon.band("hierarchy"), mon.band("success"))
        key = (sig, band)
        n_perm += 1
        if reference is None:
            reference = key
        elif key != reference:
            fails.append(f"reveal order {[e[1] for e in order]} changed the state")
            break
    _expect(fails, "permutations enumerated", n_perm, 720)
    mon, looks = replay(list(enroll) + list(reveals) + [("look", "end")])
    _expect_enc(fails, mon, "q1", "hierarchy", 1.0, 1.0, True)
    _expect_enc(fails, mon, "q2", "hierarchy", 0.0, 0.0, True)
    _expect_enc(fails, mon, "q3", "hierarchy", 1.0, 1.0, True)
    _expect_enc(fails, mon, "q3", "success", 1.0, 1.0, True)
    look = looks["end"]
    _expect(fails, "hierarchy sum", look.hierarchy.sum_lower, 2.0)
    _expect(fails, "success sum", look.success.sum_lower, 1.0)
    _expect(fails, "hierarchy mean", look.hierarchy.mean_lower, 2.0 / 3.0)
    _expect(fails, "success mean", look.success.mean_lower, 1.0 / 3.0)
    _expect(fails, "radius at n=3", look.hierarchy.radius, LOCKED_RADII[3])
    return fails


# ===========================================================================
# F06  joint failures
# ===========================================================================
def _f06_joint_failures() -> List[str]:
    """Both arms fail: the cost tier is ineligible, so the pair ties.

    HAND DERIVATION.  A = (0, 1.0), B = (0, 100.0).
      Tier 0: |0-0| = 0, not > 0 -> not decisive.
      Tier 1: eligible only when BOTH succeed -> ineligible here.
      Hence hierarchy = 0 even though the costs differ by 99 (which would be
      decisive, tol = .05*100 = 5.0, if the tier were eligible).
      success = 0 - 0 = 0.
    Before the costs are known, the two observed failures alone already pin both
    scores to 0: the enclosure narrows to [0, 0] WITHOUT a final-score
    certificate, so it is not yet marked certified.
    """
    fails: List[str] = []
    partial = [
        ("enroll", "f", "AB", "f1", "f2"),
        ("fail", "f1"), ("fail", "f2"), ("look", "partial"),
    ]
    mon, _ = replay(partial)
    _expect_enc(fails, mon, "f", "hierarchy", 0.0, 0.0, False)
    _expect_enc(fails, mon, "f", "success", 0.0, 0.0, False)
    mon.finalize("f1", 0, 1.0)
    mon.finalize("f2", 0, 100.0)
    _expect_enc(fails, mon, "f", "hierarchy", 0.0, 0.0, True)
    _expect_enc(fails, mon, "f", "success", 0.0, 0.0, True)
    # if the cost tier had been eligible the sign would have been +1
    _expect(fails, "cost tier would otherwise be decisive",
            vband.cost_order_possibilities(1.0, 1.0, 100.0, 100.0), {1})
    return fails


# ===========================================================================
# F07  strict tolerance equality
# ===========================================================================
def _f07_strict_tolerance_equality() -> List[str]:
    """Exact threshold equality is a TIE; a hair beyond it is decisive.

    HAND DERIVATION.  Both arms succeed, so the cost tier is eligible.
      (a) A cost 95.0, B cost 100.0.  tol = .05 * max(95, 100) = 5.0 exactly
          (and 0.05*100.0 == 5.0 exactly in IEEE double).  |95 - 100| = 5.0
          exactly.  ``compare`` requires |delta| > tol STRICTLY, so this ties:
          hierarchy = 0.
      (b) A cost 94.9, B cost 100.0.  tol = 5.0; |94.9 - 100| = 5.1 > 5.0 ->
          decisive, A is cheaper -> hierarchy = +1.
      (c) A cost 100.0, B cost 95.0.  tol = 5.0; difference 5.0 -> tie, 0.
    """
    fails: List[str] = []
    _expect(fails, "IEEE: 0.05*100.0", 0.05 * 100.0, 5.0)
    _expect(fails, "IEEE: 100.0-95.0", 100.0 - 95.0, 5.0)
    if not (100.0 - 94.9) > 5.0:
        fails.append("fixture (b) is not strictly beyond the threshold")

    cases = [("tie_lo", 95.0, 100.0, 0.0), ("decisive", 94.9, 100.0, 1.0),
             ("tie_hi", 100.0, 95.0, 0.0)]
    for name, ca, cb, want in cases:
        mon, _ = replay([
            ("enroll", name, "AB", f"{name}A", f"{name}B"),
            ("final", f"{name}A", 1, ca), ("final", f"{name}B", 1, cb),
        ], cost_cap=200.0)
        _expect_enc(fails, mon, name, "hierarchy", want, want, True)
        _expect_enc(fails, mon, name, "success", 0.0, 0.0, True)
    # the same boundary in the enclosure enumeration
    _expect(fails, "enumeration at exact equality",
            vband.cost_order_possibilities(95.0, 95.0, 100.0, 100.0), {0})
    _expect(fails, "enumeration just beyond",
            vband.cost_order_possibilities(94.9, 94.9, 100.0, 100.0), {1})
    return fails


# ===========================================================================
# F08  unknown outcomes
# ===========================================================================
def _f08_unknown_outcomes() -> List[str]:
    """Unresolved scores start at [-1, 1] and narrow only on certain facts.

    HAND DERIVATION.  cap 100.
      (i)   At enrollment nothing is known: sA, sB in {0,1} and costs in [0,100],
            so hierarchy and success are both [-1, +1].
      (ii)  A finalises to (1, 10).  B has reported 80 units of elapsed cost and
            no verdict, so sB in {0,1} and cost_B in [80, 100].
            success: [sA_lo - sB_hi, sA_hi - sB_lo] = [1-1, 1-0] = [0, +1].
            hierarchy, enumerating the feasible completions:
              sB = 0 -> tier 0 decisive, 1 > 0 -> +1.
              sB = 1 -> cost tier eligible, cost_A = 10, cost_B in [80, 100].
                        Best case for B is cost_B = 80: tol = .05*80 = 4.0 and
                        80 - 10 = 70 > 4, so A is cheaper beyond tolerance for
                        EVERY feasible completion -> +1.
            Both branches give +1, so hierarchy narrows to [+1, +1] while B is
            still unresolved -- and, having no final-score certificate, it is
            NOT marked certified.
      (iii) B finalises to (0, 85).  hierarchy collapses to +1 (certified) and
            success to 1 - 0 = +1.  Both lie inside every earlier bound.
    """
    fails: List[str] = []
    mon = ValidationMonitor(cost_cap=100.0, record_history=True)
    mon.enroll("u", "AB", "u1", "u2")
    mon.look("enrolled")
    _expect_enc(fails, mon, "u", "hierarchy", -1.0, 1.0, False)
    _expect_enc(fails, mon, "u", "success", -1.0, 1.0, False)

    mon.finalize("u1", 1, 10.0)
    mon.observe_elapsed_cost("u2", 80.0)
    mon.look("partial")
    _expect_enc(fails, mon, "u", "hierarchy", 1.0, 1.0, False)
    _expect_enc(fails, mon, "u", "success", 0.0, 1.0, False)
    _expect(fails, "point-resolved without a certificate",
            mon.looks[-1].n_point_resolved, 1)
    _expect(fails, "certified count still zero", mon.looks[-1].n_certified, 0)

    mon.finalize("u2", 0, 85.0)
    mon.look("resolved")
    _expect_enc(fails, mon, "u", "hierarchy", 1.0, 1.0, True)
    _expect_enc(fails, mon, "u", "success", 1.0, 1.0, True)
    _expect(fails, "containment audit", mon.audit_containment(), [])
    # a fact that contradicts an established certainty is a defect, not an update
    _raises(fails, "success after failure", EnclosureContradiction,
            mon.observe_success, "u2")
    return fails


# ===========================================================================
# F09  cap / timeout finalization
# ===========================================================================
def _f09_cap_timeout_finalization() -> List[str]:
    """The cap is an explicit finalisation rule, never a silent censor or drop.

    HAND DERIVATION.  cap 50.
      g1 reports 30 units of elapsed cost, then hits the cap.  The frozen rule
      finalises it as (success 0, cost 50) -- consistent with the prior bounds
      sA in {0,1} and cost_A in [30, 50].
      g2 finalises to (1, 12).  A failed, B succeeded: tier 0 gives 0 < 1 ->
      hierarchy = -1; success = 0 - 1 = -1.
      The pair stays in the ledger at its enrollment position: n is still 1.
    """
    fails: List[str] = []
    mon = ValidationMonitor(cost_cap=50.0, record_history=True)
    mon.enroll("g", "AB", "g1", "g2")
    mon.observe_elapsed_cost("g1", 30.0)
    mon.look("pending")
    _expect_enc(fails, mon, "g", "hierarchy", -1.0, 1.0, False)
    mon.timeout("g1")
    ep = mon.episodes["g1"]
    _expect(fails, "timeout success", (ep.success_lo, ep.success_hi), (0, 0))
    _expect(fails, "timeout cost", (ep.cost_lo, ep.cost_hi), (50.0, 50.0))
    _expect(fails, "timeout final", ep.final, True)
    mon.finalize("g2", 1, 12.0)
    mon.look("end")
    _expect_enc(fails, mon, "g", "hierarchy", -1.0, -1.0, True)
    _expect_enc(fails, mon, "g", "success", -1.0, -1.0, True)
    _expect(fails, "capped pair still enrolled", mon.looks[-1].n_enrolled, 1)
    _expect(fails, "containment audit", mon.audit_containment(), [])
    # the rule cannot overwrite an established certainty
    mon2 = ValidationMonitor(cost_cap=50.0)
    mon2.enroll("h", "AB", "h1", "h2")
    mon2.observe_success("h1")
    _raises(fails, "timeout contradicting an observed success",
            EnclosureContradiction, mon2.timeout, "h1")
    # a final cost above the cap is rejected rather than silently clipped
    mon3 = ValidationMonitor(cost_cap=50.0)
    mon3.enroll("i", "AB", "i1", "i2")
    _raises(fails, "final cost above the cap", ValidationError,
            mon3.finalize, "i1", 1, 60.0)
    return fails


# ===========================================================================
# F10  switch-phase exclusion
# ===========================================================================
def _f10_switch_phase_exclusion() -> List[str]:
    """At the crossing randomisation stops; in-flight pairs are still finished.

    HAND DERIVATION (guidance item 7).  Two pairs are enrolled and the switch
    fires with j1 still unresolved.  After the switch:
      * enrolling a new pair is an error;
      * j1 may still be finalised under its original assignment;
      * later all-one-arm traffic is logged as a follow-up cohort and NEVER
        enters the denominator, so n stays 2.
      Pair scores: k = (A (1,10), B (1,20)) -> +1 as in F01.
                   j = (A (0, 9), B (1, 30)) -> tier 0: 0 < 1 -> -1, success -1.
      Sums at n = 2: hierarchy 0, success -1.
    """
    fails: List[str] = []
    mon = ValidationMonitor(cost_cap=100.0)
    mon.enroll("k", "AB", "k1", "k2")
    mon.enroll("j", "AB", "j1", "j2")
    mon.finalize("k1", 1, 10.0)
    mon.finalize("k2", 1, 20.0)
    _raises(fails, "follow-up before the switch", ProtocolViolation,
            mon.record_followup_arrival, "z1")
    pos = mon.switch()
    _expect(fails, "switch position", pos, 2)
    _raises(fails, "enrollment after the switch", SwitchPhaseError,
            mon.enroll, "late", "AB", "L1", "L2")
    mon.finalize("j1", 0, 9.0)          # in-flight pair still finishes
    mon.finalize("j2", 1, 30.0)
    mon.record_followup_arrival("z1")
    mon.record_followup_arrival("z2")
    _raises(fails, "follow-up reusing an enrolled position", ProtocolViolation,
            mon.record_followup_arrival, "k1")
    look = mon.look("post_switch")
    _expect(fails, "follow-up traffic excluded from n", look.n_enrolled, 2)
    _expect(fails, "follow-up arrivals logged", len(mon.followup_arrivals), 2)
    _expect(fails, "hierarchy sum", look.hierarchy.sum_lower, 0.0)
    _expect(fails, "success sum", look.success.sum_lower, -1.0)
    _expect(fails, "look records the switch", look.switched, True)
    _expect(fails, "idempotent switch", mon.switch(), 2)
    return fails


# ===========================================================================
# F11  containment of every ultimately resolved score in every prior bound
# ===========================================================================
_F11_TRUTH: Dict[str, Tuple[float, float]] = {
    # pair -> (hierarchy, success), derived by hand below
    "r1": (1.0, 0.0),
    "r2": (-1.0, -1.0),
    "r3": (0.0, 0.0),
    "r4": (0.0, 0.0),
    "r5": (-1.0, -1.0),
    "r6": (1.0, 1.0),
}


def _f11_containment_audit() -> List[str]:
    """A multi-look run whose every prior bound must contain the final score.

    HAND DERIVATION of the six pair scores (cap 200).
      r1 'AB' (k1 = A, k2 = B): (1,10) vs (1,20); tol = 1.0, diff 10 -> +1; s 0.
      r2 'AB' (k3 = A, k4 = B): (0,50) vs (1,30); tier 0: 0 < 1 -> -1; s -1.
      r3 'BA' (k6 = A, k5 = B): A (1,41) vs B (1,40); tol = .05*41 = 2.05,
                                |41-40| = 1.0 <= 2.05 -> TIE 0; s 0.
      r4 'AB' (k7 = A, k8 = B): (0,9) vs (0,99); joint failure -> 0; s 0.
      r5 'BA' (k10 = A, k9 = B): A (0,70) vs B (1,60); 0 < 1 -> -1; s -1.
      r6 'AB' (k11 = A, k12 = B): (1,5) vs (0,80); 1 > 0 -> +1; s +1.
      Final sums at n = 6: hierarchy 1-1+0+0-1+1 = 0; success 0-1+0+0-1+1 = -1.
      Final means: hierarchy 0.0, success -1/6.
      r(6) = 5.482581896562951, so at the final look both bands still clip to
      [-1, +1]: six pairs cannot support a decision, and the rule abstains.
    """
    fails: List[str] = []
    events: List[tuple] = [
        ("enroll", "r1", "AB", "k1", "k2", 200.0),
        ("enroll", "r2", "AB", "k3", "k4", 200.0),
        ("look", "L0"),
        ("elapsed", "k1", 3.0), ("succeed", "k1"),
        ("enroll", "r3", "BA", "k5", "k6", 200.0),
        ("look", "L1"),
        ("final", "k1", 1, 10.0), ("elapsed", "k2", 12.0),
        ("enroll", "r4", "AB", "k7", "k8", 200.0),
        ("fail", "k3"),
        ("look", "L2"),
        ("final", "k2", 1, 20.0), ("final", "k3", 0, 50.0),
        ("enroll", "r5", "BA", "k9", "k10", 200.0),
        ("enroll", "r6", "AB", "k11", "k12", 200.0),
        ("look", "L3"),
        ("final", "k4", 1, 30.0), ("succeed", "k5"), ("elapsed", "k6", 20.0),
        ("fail", "k7"), ("elapsed", "k8", 40.0),
        ("look", "L4"),
        ("final", "k5", 1, 40.0), ("final", "k6", 1, 41.0),
        ("final", "k7", 0, 9.0), ("final", "k8", 0, 99.0),
        ("look", "L5"),
        ("succeed", "k9"), ("fail", "k10"), ("succeed", "k11"), ("fail", "k12"),
        ("look", "L6"),
        ("final", "k9", 1, 60.0), ("final", "k10", 0, 70.0),
        ("final", "k11", 1, 5.0), ("final", "k12", 0, 80.0),
        ("look", "L7"),
    ]
    mon, looks = replay(events, cost_cap=200.0, record_history=True)

    for pid, (h, s) in _F11_TRUTH.items():
        _expect_enc(fails, mon, pid, "hierarchy", h, h, True)
        _expect_enc(fails, mon, pid, "success", s, s, True)

    defects = mon.audit_containment()
    if defects:
        fails.extend(defects)

    # enclosures must be monotonically nested across looks, never widening
    for score in ("hierarchy", "success"):
        seen: Dict[Hashable, Enclosure] = {}
        for label, _n, snap in mon.history:
            for pid, (h_enc, s_enc) in snap.items():
                enc = h_enc if score == "hierarchy" else s_enc
                prev = seen.get(pid)
                if prev is not None and (enc.lo < prev.lo - 1e-12
                                         or enc.hi > prev.hi + 1e-12):
                    fails.append(f"{label}: {pid!r}.{score} widened from "
                                 f"[{prev.lo},{prev.hi}] to [{enc.lo},{enc.hi}]")
                seen[pid] = enc

    end = looks["L7"]
    _expect(fails, "final n", end.n_enrolled, 6)
    _expect(fails, "final hierarchy sum", end.hierarchy.sum_lower, 0.0)
    _expect(fails, "final success sum", end.success.sum_lower, -1.0)
    _expect(fails, "final hierarchy mean", end.hierarchy.mean_lower, 0.0)
    _expect(fails, "final success mean", end.success.mean_lower, -1.0 / 6.0)
    _expect(fails, "radius at n=6", end.hierarchy.radius, LOCKED_RADII[6])
    _expect(fails, "six pairs cannot decide", end.decision, CONTINUE)

    # at every look taken after enrollment closed, the running-sum interval must
    # bracket the finally realised running mean on that same prefix
    true_h = sum(v[0] for v in _F11_TRUTH.values()) / 6.0
    true_s = sum(v[1] for v in _F11_TRUTH.values()) / 6.0
    for label in ("L3", "L4", "L5", "L6", "L7"):
        lk = looks[label]
        if not (lk.hierarchy.mean_lower - 1e-12 <= true_h
                <= lk.hierarchy.mean_upper + 1e-12):
            fails.append(f"{label}: hierarchy running mean {true_h} outside "
                         f"[{lk.hierarchy.mean_lower}, {lk.hierarchy.mean_upper}]")
        if not (lk.success.mean_lower - 1e-12 <= true_s
                <= lk.success.mean_upper + 1e-12):
            fails.append(f"{label}: success running mean {true_s} outside "
                         f"[{lk.success.mean_lower}, {lk.success.mean_upper}]")
    return fails


# ===========================================================================
# F12  band assembly against a literal transcription of the formula
# ===========================================================================
def _f12_band_formula() -> List[str]:
    """Denominator, sign, radius argument and clip, checked against the formula."""
    fails: List[str] = []
    _expect(fails, "program alpha split", vband.ALPHA_GATE, 0.00625)
    _expect(fails, "four trials x two gates",
            vband.ALPHA_GATE * vband.N_TRIALS * vband.GATES_PER_TRIAL,
            vband.PROGRAM_ALPHA)
    _expect(fails, "rho", vband.RHO, 100.0)
    _expect(fails, "delta", vband.DELTA, 0.03)
    _expect(fails, "n_min", vband.N_MIN, 100)

    for n, locked in LOCKED_RADII.items():
        got = vband.radius_from_formula(n)
        if not _close(got, locked):
            fails.append(f"radius(n={n}): got {got!r}, locked {locked!r}")
        if not _close(got, literal_radius(n)):
            fails.append(f"radius(n={n}) disagrees with the literal transcription")

    # a ledger with a known interior band: n = 2000 pairs, mean_lower .5,
    # mean_upper .6, r(2000) = 0.08323044386401118
    n = 2000
    lowers = [0.5] * n
    uppers = [0.6] * n
    band = normal_mixture_band(lowers, uppers, n, name="synthetic")
    r = literal_radius(n)
    _expect(fails, "interior band lower", band.lower, 0.5 - r)
    _expect(fails, "interior band upper", band.upper, 0.6 + r)
    _expect(fails, "interior band n", band.n, n)

    # clipping to [-1, 1]
    clipped = normal_mixture_band([-1.0] * 4, [1.0] * 4, 4, name="clip")
    _expect(fails, "clipped lower", clipped.lower, -1.0)
    _expect(fails, "clipped upper", clipped.upper, 1.0)

    # the prefix really is a prefix: a shorter one uses only the first entries
    mixed_lo = [1.0, 1.0, -1.0, -1.0]
    mixed_hi = [1.0, 1.0, 1.0, 1.0]
    short = normal_mixture_band(mixed_lo, mixed_hi, 2, name="prefix2")
    full = normal_mixture_band(mixed_lo, mixed_hi, 4, name="prefix4")
    _expect(fails, "prefix 2 mean_lower", short.mean_lower, 1.0)
    _expect(fails, "prefix 4 mean_lower", full.mean_lower, 0.0)
    _raises(fails, "prefix beyond the ledger", ValidationError,
            normal_mixture_band, mixed_lo, mixed_hi, 5)
    _raises(fails, "radius at n=0", ValidationError, vband.radius_from_formula, 0)
    return fails


# ===========================================================================
# F13  the frozen decision rule, including the same-look conjunction
# ===========================================================================
def _f13_decision_rule() -> List[str]:
    """DEPLOY iff L_h > 0 and L_s > -delta; RETAIN iff U_h < 0; else CONTINUE.

    Both inequalities are STRICT, both are read at the same look on the same
    prefix, and nothing is decided below n_min = 100.
    """
    fails: List[str] = []
    n = 150
    cases = [
        ("deploy", _band_of("h", n, 0.10, 0.40), _band_of("s", n, -0.02, 0.30), DEPLOY),
        ("success margin exactly -delta",
         _band_of("h", n, 0.10, 0.40), _band_of("s", n, -DELTA, 0.30), CONTINUE),
        ("success margin below -delta",
         _band_of("h", n, 0.10, 0.40), _band_of("s", n, -0.05, 0.30), CONTINUE),
        ("hierarchy lower exactly zero",
         _band_of("h", n, 0.0, 0.40), _band_of("s", n, 0.10, 0.30), CONTINUE),
        ("harm", _band_of("h", n, -0.40, -0.01),
         _band_of("s", n, -0.60, -0.10), RETAIN_INCUMBENT),
        ("harm upper exactly zero",
         _band_of("h", n, -0.40, 0.0), _band_of("s", n, -0.60, -0.10), CONTINUE),
        ("straddling", _band_of("h", n, -0.20, 0.20),
         _band_of("s", n, -0.20, 0.20), CONTINUE),
    ]
    for label, hb, sb, want in cases:
        _expect(fails, f"decision[{label}]", decide(hb, sb), want)

    # n_min gate: a decisive-looking band below n_min still abstains
    _expect(fails, "below n_min",
            decide(_band_of("h", N_MIN - 1, 0.5, 0.9),
                   _band_of("s", N_MIN - 1, 0.5, 0.9)), CONTINUE)
    _expect(fails, "at n_min",
            decide(_band_of("h", N_MIN, 0.5, 0.9),
                   _band_of("s", N_MIN, 0.5, 0.9)), DEPLOY)
    # same-look conjunction: the two gates must be read on one prefix
    _raises(fails, "mismatched prefixes", ProtocolViolation, decide,
            _band_of("h", 150, 0.5, 0.9), _band_of("s", 120, 0.5, 0.9))
    # deploy and harm are mutually exclusive because L <= U
    for lo in (-0.5, -0.01, 0.0, 0.01, 0.5):
        hb = _band_of("h", n, lo, lo + 0.2)
        sb = _band_of("s", n, 0.5, 0.9)
        d = decide(hb, sb)
        if d == DEPLOY and hb.upper < 0.0:
            fails.append("deploy and harm fired together")
    return fails


# ===========================================================================
# F14  the radius agreement, over the whole range, at strict equality
# ===========================================================================
def _f14_radius_sweep() -> List[str]:
    """`vband.radius_from_formula` vs a literal transcription, n = 1..20,000.

    PROTOCOL 2.2 states the agreement at STRICT float equality over the whole
    range, not at a tolerance and not at a sample of points, so the fixture
    makes exactly that assertion.  What it establishes is narrow: that vband
    passes the intended arguments to the pinned primitive, in particular
    ``variance_process = n``.  It is not evidence about the primitive itself.
    """
    fails: List[str] = []
    mismatches = 0
    first: Optional[Tuple[int, float, float]] = None
    for n in range(1, 20001):
        got = vband.radius_from_formula(n)
        want = literal_radius(n)
        if got != want:
            mismatches += 1
            if first is None:
                first = (n, got, want)
    if mismatches:
        fails.append(f"radius sweep: {mismatches} of 20000 n disagree with the "
                     f"literal transcription; first {first!r}")
    # the same, straight against the pinned primitive
    for n in (1, 2, 3, 4, 6, 17, 100, 500, 999, 2000, 12345, 20000):
        pinned = float(vband.normal_mixture_radius(n, alpha=ALPHA_GATE, rho=RHO,
                                                   variance_process=n))
        if pinned != literal_radius(n):
            fails.append(f"pinned primitive at n={n}: {pinned!r} != "
                         f"{literal_radius(n)!r}")
    for n, locked in LOCKED_RADII.items():
        if literal_radius(n) != locked:
            fails.append(f"LOCKED_RADII[{n}] = {locked!r} != {literal_radius(n)!r}")
    _raises(fails, "literal radius at n=0", ValueError, literal_radius, 0)
    return fails


# ===========================================================================
# F16  the import graph -- the only mechanical guard on the independence rule
# ===========================================================================
_FORBIDDEN_IMPORT_RE = re.compile(r"^(lab_[A-Za-z0-9_]*|.*live_ab\..*|pinned(\..*)?)$")
_FORBIDDEN_TEXT = ("experiments/live_ab/", "live_ab_validation/pinned/",  # IMPORT-GUARD-LITERAL
                   "lab_monitor", "lab_enclosure", "lab_reference_rule")  # IMPORT-GUARD-LITERAL
_DYNAMIC_IMPORT_NAMES = ("__import__", "exec", "eval")
_DYNAMIC_IMPORT_ATTRS = ("import_module", "run_module", "run_path", "load_module",
                         "spec_from_file_location", "module_from_spec")
#: the single module allowed to load the pinned #11 copy (PROTOCOL 12.1 item 3)
_COMPARISON_MODULE = "vcompare.py"
#: Modules exempt from the STATIC half of the scan only.  The dynamic half
#: still applies to every module without exception, so an exemption here buys
#: the right to NAME a forbidden path, never the right to import one.
#:
#:   vcompare.py      loads the pinned #11 copy at the comparison step, which
#:                    is what PROTOCOL 12.1 item 3 authorises it to do.
#:   vsnapshot_v2.py  BUILDS the v2 snapshot, so it must name the three live
#:                    rule modules in order to copy their bytes. It reads them
#:                    with Path.read_bytes and never imports them; it is not on
#:                    any evaluation path and nothing imports it.
_STATIC_SCAN_EXEMPT = (_COMPARISON_MODULE, "vsnapshot_v2.py")
#: A line carrying this marker may name a forbidden path.  The marker is a
#: deliberate, greppable act and every use of it is visible in review; the
#: dynamic half of F16 still catches an actual import.  Today it exempts only
#: this guard's own definitions and the provenance hash table of F15.
_GUARD_MARKER = "IMPORT-GUARD" "-LITERAL"


def _docstring_constants(tree: ast.AST) -> set:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and \
                    isinstance(body[0].value, ast.Constant) and \
                    isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _f16_import_graph_independence() -> List[str]:
    """No #12 module may reach the #11 monitor, and it is checked, not declared.

    Two independent checks.  (1) DYNAMIC: a fresh interpreter imports every #12
    module and reports any entry of ``sys.modules`` whose ``__file__`` lies
    under ``experiments/live_ab/`` or ``.../pinned/``.  (2) STATIC: every source
    file in this directory except the comparison module is parsed, and neither
    an import of a forbidden name, nor a dynamic-import call, nor a non-docstring
    string literal naming either path is allowed.  Docstrings are exempt because
    the source declarations name exactly the files they promise NOT to read.
    """
    fails: List[str] = []
    live_ab = str(REPO_ROOT / "experiments" / "live_ab") + os.sep
    pinned = str(HERE / "pinned") + os.sep
    probe = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(HERE)!r})\n"
        "import vband, vfixtures, tests_validation\n"
        "bad = []\n"
        "for name, mod in list(sys.modules.items()):\n"
        "    f = getattr(mod, '__file__', None)\n"
        f"    if f and (f.startswith({live_ab!r}) or f.startswith({pinned!r})):\n"
        "        bad.append([name, f])\n"
        "print('RESULT ' + json.dumps(bad))\n"
    )
    try:
        done = subprocess.run([sys.executable, "-c", probe], capture_output=True,
                              text=True, timeout=180, cwd=str(HERE))
    except (OSError, subprocess.SubprocessError) as exc:
        fails.append(f"import-graph probe could not run: {type(exc).__name__}: {exc}")
        return fails
    if done.returncode != 0:
        fails.append(f"import-graph probe exited {done.returncode}: "
                     f"{done.stderr.strip()[-400:]}")
        return fails
    line = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not line:
        fails.append(f"import-graph probe produced no result: {done.stdout[-400:]}")
        return fails
    loaded = json.loads(line[-1][len("RESULT "):])
    for name, path in loaded:
        fails.append(f"module {name} loaded from the forbidden tree: {path}")

    fails.extend(scan_sources_for_forbidden_paths(HERE))
    return fails


def scan_sources_for_forbidden_paths(directory: Path,
                                     require_at_least: int = 3) -> List[str]:
    """The static half of F16, over any directory, so that it can be tested.

    A guard that has never fired is not known to be a guard; the mutation tests
    in ``tests_validation.py`` point this at a temporary directory containing
    deliberate violations and assert that each one is reported.
    """
    fails: List[str] = []
    checked = 0
    for src in sorted(Path(directory).glob("*.py")):
        if src.name in _STATIC_SCAN_EXEMPT:
            continue
        checked += 1
        text = src.read_text()
        lines = text.splitlines()
        tree = ast.parse(text, filename=str(src))
        doc_ids = _docstring_constants(tree)

        def _exempt(node) -> bool:
            lo = getattr(node, "lineno", 1)
            hi = getattr(node, "end_lineno", lo) or lo
            return any(_GUARD_MARKER in lines[i - 1]
                       for i in range(lo, min(hi, len(lines)) + 1))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _FORBIDDEN_IMPORT_RE.match(alias.name):
                        fails.append(f"{src.name}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and _FORBIDDEN_IMPORT_RE.match(node.module):
                    fails.append(f"{src.name}:{node.lineno} imports from {node.module}")
            elif isinstance(node, ast.Call):
                fn = node.func
                nm = (fn.attr if isinstance(fn, ast.Attribute) else
                      fn.id if isinstance(fn, ast.Name) else None)
                hit = (isinstance(fn, ast.Name) and nm in _DYNAMIC_IMPORT_NAMES) or \
                      (isinstance(fn, ast.Attribute) and nm in _DYNAMIC_IMPORT_ATTRS)
                if hit and not _exempt(node):
                    fails.append(f"{src.name}:{node.lineno} calls {nm}(), which can "
                                 f"import outside the static graph")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in doc_ids:
                for needle in _FORBIDDEN_TEXT:
                    if needle in node.value and not _exempt(node):
                        fails.append(f"{src.name}:{node.lineno} names {needle!r} "
                                     f"outside a docstring")
    if checked < require_at_least:
        fails.append(f"static scan saw only {checked} source files; expected at "
                     f"least {require_at_least}")
    return fails


# ===========================================================================
# F17  the atom cost table and the cost enclosure path
# ===========================================================================
#: (s_C, s_I, c_C, c_I, Z, D) -- PROTOCOL 4.1, transcribed by hand.
ATOM_COSTS: Dict[str, Tuple[int, int, float, float, int, int]] = {
    "BB+": (1, 1, 10.0, 40.0, +1, 0),
    "BB0": (1, 1, 40.0, 40.0, 0, 0),
    "BB-": (1, 1, 40.0, 10.0, -1, 0),
    "C>I": (1, 0, 10.0, 40.0, +1, +1),
    "I>C": (0, 1, 40.0, 10.0, -1, -1),
    "FF": (0, 0, 40.0, 40.0, 0, 0),
}
COST_CAP = 100.0
#: every d the frozen delay blocks can produce, plus the boundary-hitting ones
_F17_SHORT = tuple(range(1, 20))
_F17_LONG = (100, 114, 133, 152, 171, 190, 199, 209, 300, 400, 500, 600, 699)


def _f17_partial_state(atom: str, cand_first: bool, ell: float
                       ) -> Tuple[float, float]:
    """The enclosure vband reports for one partially revealed state."""
    s_C, s_I, c_C, c_I, _Z, _D = ATOM_COSTS[atom]
    if cand_first:
        ep_c = vband.Episode.pending("c", COST_CAP).finalized(s_C, c_C)
        ep_i = vband.Episode.pending("i", COST_CAP).with_elapsed_cost(ell)
    else:
        ep_i = vband.Episode.pending("i", COST_CAP).finalized(s_I, c_I)
        ep_c = vband.Episode.pending("c", COST_CAP).with_elapsed_cost(ell)
    return vband.hierarchy_bounds(ep_c, ep_i)


def _f17_closed_form(atom: str, cand_first: bool, ell: float
                     ) -> Tuple[float, float]:
    """PROTOCOL 2.5's closed-form reading: thresholds .95c and c/.95."""
    s_C, s_I, c_C, c_I, _Z, _D = ATOM_COSTS[atom]
    rtol = vband.COST_RELATIVE_TOLERANCE
    if cand_first:
        if s_C == 0:
            return (-1.0, 0.0)
        c = c_C
        if ell < (1.0 - rtol) * c:
            return (-1.0, 1.0)
        return (0.0, 1.0) if ell <= c / (1.0 - rtol) else (1.0, 1.0)
    if s_I == 0:
        return (0.0, 1.0)
    c = c_I
    if ell < (1.0 - rtol) * c:
        return (-1.0, 1.0)
    return (-1.0, 0.0) if ell <= c / (1.0 - rtol) else (-1.0, -1.0)


def _f17_atom_cost_table() -> List[str]:
    """The atom cost columns, and the cost enclosure path they open.

    Four assertions.
      (a) every atom's cost pair reproduces the frozen Z and D through the
          pinned ``winstats.compare``, so the ground truth of PROTOCOL 4.1 is
          untouched by the cost columns;
      (b) over the frozen state grid the hierarchy enclosure always contains
          the true Z -- a false narrowing here would silently corrupt every
          coverage number in the study;
      (c) it narrows monotonically as elapsed cost accrues and never widens;
      (d) the closed-form reading of PROTOCOL 2.5 agrees with the governing
          predicate EXCEPT at the enumerated boundary ell = c/(1-rtol), where
          the predicate wins.  PROTOCOL 2.5 states that set; this fixture is
          what makes the statement checkable.
    """
    fails: List[str] = []
    rtol = vband.COST_RELATIVE_TOLERANCE

    # (a) the cost columns reproduce the frozen Z / D column
    for atom, (s_C, s_I, c_C, c_I, Z, D) in ATOM_COSTS.items():
        ep_c = vband.Episode.pending("c", COST_CAP).finalized(s_C, c_C)
        ep_i = vband.Episode.pending("i", COST_CAP).finalized(s_I, c_I)
        _expect(fails, f"atom {atom} Z via winstats.compare",
                vband.final_hierarchy_score(ep_c, ep_i), Z)
        _expect(fails, f"atom {atom} D", vband.final_success_score(ep_c, ep_i), D)
    # the tie atoms really are ties, and the decisive ones really are decisive
    _expect(fails, "BB0 costs are equal", ATOM_COSTS["BB0"][2], ATOM_COSTS["BB0"][3])
    _expect(fails, "tolerance at the (10,40) pair", 0.05 * 40.0, 2.0)
    if not (abs(10.0 - 40.0) > 0.05 * 40.0):
        fails.append("the (10,40) cost pair is not decisive on the cost tier")
    # arm exchangeability of L1 survives the cost columns
    swapped = {a: (v[1], v[0], v[3], v[2], -v[4], -v[5])
               for a, v in ATOM_COSTS.items()}
    for a, b in (("BB+", "BB-"), ("C>I", "I>C"), ("BB0", "BB0"), ("FF", "FF")):
        if swapped[a] != ATOM_COSTS[b]:
            fails.append(f"arm swap does not map {a} to {b}: {swapped[a]} vs "
                         f"{ATOM_COSTS[b]}")

    # (b)-(d) the state grid
    boundary: List[Tuple[str, bool, int, int]] = []
    n_states = 0
    n_point = 0
    for atom, (s_C, s_I, c_C, c_I, Z, D) in ATOM_COSTS.items():
        for cand_first in (True, False):
            scale = c_I if cand_first else c_C
            revealed_cost = c_C if cand_first else c_I
            revealed_ok = (s_C if cand_first else s_I) == 1
            for d in _F17_SHORT + _F17_LONG:
                prev: Optional[Tuple[float, float]] = None
                for a in range(0, d):
                    ell = (scale * a) / d
                    lo, hi = _f17_partial_state(atom, cand_first, ell)
                    n_states += 1
                    if not (lo - 1e-12 <= Z <= hi + 1e-12):
                        fails.append(f"{atom} cand_first={cand_first} d={d} a={a}: "
                                     f"true Z={Z} outside [{lo}, {hi}]")
                    if prev is not None and (lo < prev[0] - 1e-12
                                             or hi > prev[1] + 1e-12):
                        fails.append(f"{atom} cand_first={cand_first} d={d} a={a}: "
                                     f"enclosure widened from {prev} to {(lo, hi)}")
                    prev = (lo, hi)
                    if lo == hi:
                        n_point += 1
                        if not revealed_ok:
                            fails.append(
                                f"{atom} cand_first={cand_first} d={d} a={a}: the "
                                f"cost tier collapsed a pair whose revealed arm failed")
                    closed = _f17_closed_form(atom, cand_first, ell)
                    if closed != (lo, hi):
                        boundary.append((atom, cand_first, d, a))
                        if ell != revealed_cost / (1.0 - rtol):
                            fails.append(
                                f"{atom} cand_first={cand_first} d={d} a={a}: the "
                                f"closed form {closed} and the predicate {(lo, hi)} "
                                f"disagree away from the boundary (ell={ell!r})")
    _expect(fails, "states exercised", n_states, 47484)
    if n_point == 0:
        fails.append("no state collapsed to a point: the cost path is not exercised")
    # The closed form and the predicate disagree exactly at ell = c/(1-rtol),
    # reached at elapsed fraction 5/19 by the (10, 40) cost pairs.  Four
    # (atom, revealed arm) combinations reach it, at each of the seven multiples
    # of 19 in this grid: 28 states.  Asserting the COUNT as well as the shape
    # keeps this check from passing vacuously if the grid ever stops reaching
    # the boundary at all.
    for atom, cand_first, d, a in boundary:
        if a * 19 != d * 5:
            fails.append(f"unexpected boundary state {atom} cand_first={cand_first} "
                         f"d={d} a={a} (a/d is not 5/19)")
    _expect(fails, "boundary states reached", len(boundary), 28)
    # a pending episode that has not started carries no cost information
    for atom in ATOM_COSTS:
        for cand_first in (True, False):
            lo, hi = _f17_partial_state(atom, cand_first, 0.0)
            s_C, s_I = ATOM_COSTS[atom][0], ATOM_COSTS[atom][1]
            want = ((-1.0, 0.0) if s_C == 0 else (-1.0, 1.0)) if cand_first else \
                   ((0.0, 1.0) if s_I == 0 else (-1.0, 1.0))
            _expect(fails, f"{atom} cand_first={cand_first} at ell=0", (lo, hi), want)
    return fails


# ===========================================================================
# F18  the provenance pins, recomputed from the files themselves
# ===========================================================================
#: the coordinator's read-only deposit and its manifest.  Naming the directory
#: this way keeps the forbidden path literal out of the source (F16).
PINNED_DIR = HERE / "pinned"
PINNED_MANIFEST = PINNED_DIR / "PINNED.json"


def sha256_file(path: Path) -> str:
    """The SHA-256 of a file's bytes.

    Binary mode, streamed, never decoded.  For the three sources under
    ``pinned/`` this is the whole of this directory's contact with the #11
    monitor before ``vcompare.py`` exists: the bytes go into ``hashlib`` and the
    only value that comes out is a digest (PROTOCOL 12.1 item 3).
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _f18_pinned_file_hashes() -> List[str]:
    """Every pin is recomputed from the file it names, not from another string.

    PREREG_CHECK_2 N.1: the pin on ``protocol_FINAL.md`` was stale and nothing
    caught it, because the only check that looked at a pin asserted that the same
    64-hex token appeared in PROTOCOL.md and in cells.json.  Two documents can
    agree with each other while both disagree with the file on disk.  This
    fixture opens each pinned file, hashes it, and compares the digest against
    the recorded pin, so a stale pin fails loudly.
    """
    return check_pinned_file_hashes(
        json.loads(CELLS_PATH.read_text()),
        json.loads(PINNED_MANIFEST.read_text()),
        REPO_ROOT, PINNED_DIR, PROTOCOL_PATH.read_text())


def check_pinned_file_hashes(cfg: dict, manifest: dict, repo_root: Path,
                             pinned_dir: Path, protocol_text: str) -> List[str]:
    """The body of F18, taking its inputs, so that it can be tested.

    ``tests_validation.py`` perturbs a copy of each recorded digest, and a copy of
    the manifest's file list, and asserts that every perturbation is reported: a
    hash check that cannot fail is the defect it is here to prevent.
    """
    fails: List[str] = []
    doc_hashes = set(re.findall(r"\b[0-9a-f]{64}\b", protocol_text))

    # -- the three provenance pins, hashed from the files they name ----------
    prov = cfg["provenance"]
    for key in ("formula_source", "pinned_primitive", "vocabulary_alignment"):
        entry = prov.get(key)
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            fails.append(f"provenance.{key}: no path/sha256 pair in cells.json")
            continue
        rel, want = entry["path"], entry["sha256"]
        path = repo_root / rel
        if not path.is_file():
            fails.append(f"provenance.{key}: {rel} does not exist")
            continue
        got = sha256_file(path)
        if got != want:
            # A pin may legitimately fall behind the file it names when the OTHER study
            # moves after this pre-registration was frozen and after this grid ran. That
            # is not a licence to re-pin: coordinator ruling 60 forbids asserting that a
            # completed run covered a version that did not exist when it ran. So the
            # invariant this fixture actually enforces is "no pin is SILENTLY stale":
            # a supersession passes only when it is recorded explicitly AND its recorded
            # successor hash is itself verified against the file on disk. A pin that
            # simply drifted, with no record, still fails exactly as before.
            sup = entry.get("superseded_by")
            # `supersedes` binds the record to the EXACT pin it excuses, so mutating the
            # pin breaks the binding and the mutation is caught, as the N.1 test requires.
            if (isinstance(sup, dict) and sup.get("sha256") == got
                    and sup.get("supersedes") == want
                    and str(sup.get("reason", "")).strip() and str(sup.get("ruling", "")).strip()):
                pass  # documented supersession, successor hash verified against the file
            else:
                fails.append(f"provenance.{key}: {rel} hashes to {got}, but cells.json "
                             f"pins {want}. The pin is stale: recompute it before the "
                             f"freeze commit, or record superseded_by with the successor "
                             f"hash, a reason and the ruling that forbids re-pinning")
        if want not in doc_hashes:
            fails.append(f"provenance.{key}: the pin recorded for {rel} does not "
                         f"appear in PROTOCOL.md")

    # -- the pinned deposit, against its own manifest ------------------------
    if not pinned_dir.is_dir():
        fails.append(f"{pinned_dir.name}/ does not exist")
        return fails
    recorded = manifest.get("files")
    if not isinstance(recorded, dict) or not recorded:
        fails.append("PINNED.json carries no 'files' map")
        return fails
    present = sorted(p.name for p in pinned_dir.glob("*.py"))
    if sorted(recorded) != present:
        fails.append(f"PINNED.json lists {sorted(recorded)} but the deposit holds "
                     f"{present}")
    for name in sorted(set(recorded) & set(present)):
        got = sha256_file(pinned_dir / name)
        if got != recorded[name]:
            fails.append(f"pinned/{name} hashes to {got}, but PINNED.json records "
                         f"{recorded[name]}")
    commit = str(manifest.get("source_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        fails.append(f"PINNED.json source_commit {commit!r} is not a 40-hex commit id")
    elif commit not in protocol_text and commit[:7] not in protocol_text:
        fails.append("PROTOCOL.md does not name the commit PINNED.json was taken from")
    return fails


# ===========================================================================
# F15  PROTOCOL.md and cells.json must agree, value for value
# ===========================================================================
_NUM_RE = re.compile(r"[-+]?(?:\d[\d,]*\.?\d*|\.\d+)")


def _clean(cell: str) -> str:
    return cell.replace("`", "").replace("*", "").strip()


def _nums(cell: str) -> List[float]:
    out = []
    for tok in _NUM_RE.findall(_clean(cell)):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:                                  # pragma: no cover
            pass
    return out


def _num(cell: str) -> Optional[float]:
    got = _nums(cell)
    return got[0] if got else None


def _md_tables(text: str) -> List[List[List[str]]]:
    """Every markdown pipe table, as a list of rows of cell strings."""
    tables: List[List[List[str]]] = []
    cur: List[List[str]] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and len(s) > 1:
            cells = [c.strip() for c in s[1:-1].split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue                                    # separator row
            cur.append(cells)
        else:
            if len(cur) >= 2:
                tables.append(cur)
            cur = []
    if len(cur) >= 2:
        tables.append(cur)
    return tables


def _find_table(tables, *needles: str) -> Optional[List[List[str]]]:
    for t in tables:
        head = " | ".join(t[0]).lower()
        if all(n.lower() in head for n in needles):
            return t
    return None


def _rows_by_key(table) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for row in table[1:]:
        key = _clean(row[0]).split()[0] if _clean(row[0]) else ""
        if key:
            out.setdefault(key, row)
    return out


def _row_starting(table, prefix: str) -> Optional[List[str]]:
    """The first data row whose first cell starts with ``prefix``.

    Several tables of PROTOCOL.md key their rows on a phrase rather than a single
    token, so ``_rows_by_key`` (which takes the first word) collides on them.
    """
    low = prefix.lower()
    return next((r for r in table[1:] if _clean(r[0]).lower().startswith(low)), None)


def _label(cell: str) -> str:
    """A row label, normalised for comparison with its twin in cells.json."""
    return re.sub(r"\s+", " ", _clean(cell).replace(",", " ").lower()).strip()


def _interval(fails: List[str], label: str, cell: str, want) -> None:
    """One ``[lo, hi]`` enclosure cell against its twin.

    ``want`` is either two numbers or two symbols (``["Z", "Z"]``); a symbolic row
    must carry no number at all, which is what makes the resolved row of section
    2.5 distinguishable from a numeric one.
    """
    if all(isinstance(v, str) for v in want):
        if _nums(cell):
            fails.append(f"{label}: PROTOCOL {cell!r} carries a number where "
                         f"cells.json has {want}")
        for sym in want:
            if sym not in _clean(cell):
                fails.append(f"{label}: PROTOCOL {cell!r} does not name {sym!r}")
        return
    got = _nums(cell)
    if len(got) != 2:
        fails.append(f"{label}: PROTOCOL {cell!r} did not parse as an interval")
        return
    for g, w, end in zip(got, want, ("lower", "upper")):
        _eq(fails, f"{label} {end}", g, w)
    if got[0] > got[1]:
        fails.append(f"{label}: PROTOCOL {cell!r} is an inverted interval")


def _eq(fails: List[str], label: str, got, want, tol: float = 5e-9) -> None:
    if got is None:
        fails.append(f"{label}: missing in PROTOCOL.md")
        return
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        if abs(float(got) - float(want)) > tol:
            fails.append(f"{label}: PROTOCOL {got!r} != cells.json {want!r}")
    elif got != want:
        fails.append(f"{label}: PROTOCOL {got!r} != cells.json {want!r}")


def _f15_protocol_config_agreement() -> List[str]:
    """Every numeric table of PROTOCOL.md, parsed and compared to cells.json.

    The header of PROTOCOL.md calls cells.json "normative for every numeric
    value ... and a fixture asserts it".  Before the pre-registration audit no
    such fixture existed and the two files had already drifted (the fixture
    register named F0..F12 while the code implemented F01..F13).  This is that
    fixture.  It parses the markdown tables rather than the prose, so a value
    that appears only in prose is outside its reach; every table that carries a
    frozen number is inside it.
    """
    return check_protocol_config_agreement(PROTOCOL_PATH.read_text(),
                                           json.loads(CELLS_PATH.read_text()))


def check_protocol_config_agreement(text: str, cfg: dict) -> List[str]:
    """The body of F15, taking the two documents, so that it can be tested.

    ``tests_validation.py`` mutates a copy of each document and asserts that the
    mutation is reported; a comparison that cannot fail proves nothing.
    """
    fails: List[str] = []
    tables = _md_tables(text)
    P = cfg["parameters"]
    AR = cfg["analytic_reachability"]

    # -- the three pinned hashes ------------------------------------------
    doc_hashes = set(re.findall(r"\b[0-9a-f]{64}\b", text))
    for key, path in (("formula_source", "reviews/arxiv_live_design_guidance.md"),
                      ("pinned_primitive", "src/winstats.py"),
                      ("vocabulary_alignment",
                       "experiments/live_ab/design/protocol_FINAL.md")):  # IMPORT-GUARD-LITERAL
        want = cfg["provenance"][key]["sha256"]
        if want not in doc_hashes:
            fails.append(f"hash of {path} in cells.json is not in PROTOCOL.md")
    # The three strings above are only strings.  F18_pinned_file_hashes is what
    # makes them pins: it opens each file and hashes it (PREREG_CHECK_2 N.1).

    # -- the rest of the header table: commit, interpreter, numpy ----------
    t = _find_table(tables, "field", "value")
    if t is None:
        fails.append("header provenance table not found")
    else:
        prov = cfg["provenance"]
        row = _row_starting(t, "repository state")
        if row is None:
            fails.append("header: no 'repository state at writing' row")
        else:
            got = re.findall(r"\b[0-9a-f]{40}\b", _clean(row[1]))
            if got != [prov["repo_commit_at_writing"]]:
                fails.append(f"header commit: PROTOCOL {got} != cells.json "
                             f"{prov['repo_commit_at_writing']}")
        row = _row_starting(t, "environment")
        if row is None:
            fails.append("header: no 'environment' row")
        else:
            cell = _clean(row[1])
            for label, pattern, want in (
                    ("CPython", r"CPython ([0-9.]+)", prov["python"]),
                    ("numpy", r"numpy ([0-9.]+)", prov["numpy"])):
                m = re.search(pattern, cell)
                if not m:
                    fails.append(f"header environment: no {label} version")
                elif m.group(1) != want:
                    fails.append(f"header {label}: PROTOCOL {m.group(1)} != "
                                 f"cells.json {want}")

    # -- 2.1 frozen parameters --------------------------------------------
    t = _find_table(tables, "symbol", "value", "source")
    if t is None:
        fails.append("2.1 parameter table not found")
    else:
        rows = _rows_by_key(t)
        for key, want in (("alpha_gate", P["alpha_gate"]), ("rho", P["rho"]),
                          ("delta", P["delta"]), ("n_min", P["n_min"]),
                          ("N_max", P["N_max"]), ("W", P["drain_W"])):
            row = rows.get(key)
            if row is None:
                fails.append(f"2.1: no row for {key}")
            else:
                _eq(fails, f"2.1 {key}", _num(row[1]), want)
        for label, want in (("trials", P["trials_per_program"]),
                            ("program", P["alpha_program"])):
            row = next((r for r in t[1:] if _clean(r[0]).startswith(label)), None)
            if row is None:
                fails.append(f"2.1: no row starting {label!r}")
            else:
                _eq(fails, f"2.1 {label}", _num(row[1]), want)
        # the alpha ladder, in both places section 2.1 writes it
        row = rows.get("alpha_gate")
        if row is not None:
            got = _nums(row[2])
            want = [P["alpha_program"], P["alpha_per_trial"]]
            if len(got) < 3:
                fails.append(f"2.1 alpha_gate source cell parsed {got}; it must "
                             f"carry the program and per-trial budgets")
            else:
                for g, w, lab in zip(got[-2:], want, ("program", "per trial")):
                    _eq(fails, f"2.1 alpha ladder ({lab})", g, w)
        row = _row_starting(t, "program budget")
        if row is None:
            fails.append("2.1: no 'program budget' row")
        else:
            got = _nums(row[1])
            want = [P["alpha_program"], P["trials_per_program"], P["alpha_per_trial"]]
            if got != want:
                fails.append(f"2.1 program budget: PROTOCOL {got} != cells.json {want}")
        row = rows.get("variance_process")
        if row is not None:
            # `[-1,1]` parses as one token under _NUM_RE (the comma reads as a
            # thousands separator), so the bracketed pair is matched directly.
            m = re.search(r"\[\s*([-+.\d]+)\s*,\s*([-+.\d]+)\s*\]", _clean(row[2]))
            if m is None:
                fails.append("2.1 variance_process row names no score range")
            else:
                _eq(fails, "2.1 score range",
                    [float(m.group(1)), float(m.group(2))],
                    [float(x) for x in P["score_range"]])
        # and the ladder must close, in cells.json's own numbers
        _eq(fails, "2.1 alpha_program = trials x alpha_per_trial",
            P["trials_per_program"] * P["alpha_per_trial"], P["alpha_program"])
        _eq(fails, "2.1 alpha_per_trial = gates x alpha_gate",
            P["gates_per_trial"] * P["alpha_gate"], P["alpha_per_trial"])

    # -- 2.2 radius reference values --------------------------------------
    t = _find_table(tables, "r(n)")
    if t is None:
        fails.append("2.2 radius table not found")
    else:
        seen = {}
        for row in t[1:]:
            for i in range(0, len(row) - 1, 2):
                n, r = _num(row[i]), _num(row[i + 1])
                if n is not None and r is not None:
                    seen[str(int(n))] = r
        want = P["radius_reference_values"]
        if set(seen) != set(want):
            fails.append(f"2.2 radius table keys {sorted(seen)} != "
                         f"{sorted(want)}")
        for k in set(seen) & set(want):
            _eq(fails, f"2.2 r({k})", seen[k], want[k], tol=5e-7)
            _eq(fails, f"2.2 r({k}) vs the formula", round(literal_radius(int(k)), 6),
                want[k], tol=5e-7)
    m = re.search(r"Smallest `n` with `r\(n\) < x`:(.+?)\n\n", text, re.S)
    if not m:
        fails.append("2.2 'smallest n with r(n) < x' sentence not found")
    else:
        got = {k: int(v.replace(",", ""))
               for k, v in re.findall(r"`?([0-9.]+)`? -> ([\d,]+)", m.group(1))}
        want = {k: int(v) for k, v in P["first_n_with_radius_below"].items()}
        if got != want:
            fails.append(f"2.2 first-n-below: PROTOCOL {got} != cells.json {want}")

    # -- 2.5 the enclosure-row table ---------------------------------------
    # PREREG_CHECK_2 N.2: this is the table that decides ground truth for the
    # whole cost-path design, cells.json was declared normative over it, and
    # nothing compared the two.  All 44 numbers below were unguarded.
    ER = cfg["enclosure_rules"]
    t = _find_table(tables, "state of pair", "hierarchy enclosure",
                    "success enclosure")
    if t is None:
        fails.append("2.5 enclosure-row table not found")
    else:
        want_rows = ER.get("protocol_2_5_rows")
        if want_rows is None:
            fails.append("2.5: cells.json carries no enclosure_rules."
                         "protocol_2_5_rows to compare the table against")
            want_rows = []
        doc_rows = [r for r in t[1:] if _clean(r[0])]
        if len(doc_rows) != len(want_rows):
            fails.append(f"2.5: {len(doc_rows)} rows against {len(want_rows)} in "
                         f"cells.json")
        for i, (row, want) in enumerate(zip(doc_rows, want_rows)):
            if _label(row[0]) != _label(want["label"]):
                fails.append(f"2.5 row {i}: PROTOCOL {_clean(row[0])!r} != "
                             f"cells.json {want['label']!r}")
                continue
            _interval(fails, f"2.5 [{want['label']}] hierarchy", row[1],
                      want["hierarchy"])
            _interval(fails, f"2.5 [{want['label']}] success", row[2],
                      want["success"])
        # the ten rows must be a refinement of the six coarse states above them
        states = {s["state"]: s for s in ER["states"]}
        groups: Dict[str, List[dict]] = {}
        for want in want_rows:
            groups.setdefault(want["refines"], []).append(want)
        if set(groups) != set(states):
            fails.append(f"2.5 rows refine {sorted(groups)}, but enclosure_rules."
                         f"states holds {sorted(states)}")
        for name, rows_of in groups.items():
            state = states.get(name)
            if state is None:
                continue
            widest = rows_of[0]
            for key in ("hierarchy", "success"):
                if widest[key] != state[key]:
                    fails.append(f"2.5 {name}: widest row {key} {widest[key]} != "
                                 f"enclosure_rules.states {state[key]}")
            if len(rows_of) > 1 and not state.get("cost_relevant"):
                fails.append(f"2.5 {name}: {len(rows_of)} rows for a state the cost "
                             f"tier cannot touch")
            for later in rows_of[1:]:
                if later["success"] != widest["success"]:
                    fails.append(f"2.5 {name}: the success enclosure moves within a "
                                 f"group; the cost tier cannot touch it")
                lo, hi = later["hierarchy"]
                wlo, whi = widest["hierarchy"]
                if not (isinstance(lo, (int, float)) and lo >= wlo and hi <= whi):
                    fails.append(f"2.5 {name}: {later['label']!r} is not inside the "
                                 f"widest row of its group")

    # -- 4 the eight cells -------------------------------------------------
    t = _find_table(tables, "cell", "index", "outcome law", "delay rule")
    if t is None:
        fails.append("4 cells table not found")
    else:
        rows = _rows_by_key(t)
        if len(rows) != len(cfg["cells"]):
            fails.append(f"4: {len(rows)} cell rows against "
                         f"{len(cfg['cells'])} in cells.json")
        for cell in cfg["cells"]:
            row = rows.get(cell["id"])
            if row is None:
                fails.append(f"4: no row for {cell['id']}")
                continue
            _eq(fails, f"4 {cell['id']} index", _num(row[1]), cell["cell_index"])
            if _clean(row[2]).split()[0] != cell["law"]:
                fails.append(f"4 {cell['id']} law: {_clean(row[2])!r} vs "
                             f"{cell['law']}")
            if _clean(row[3]).split()[0] != cell["delay"]:
                fails.append(f"4 {cell['id']} delay: {_clean(row[3])!r} vs "
                             f"{cell['delay']}")
            _eq(fails, f"4 {cell['id']} mu_h", _num(row[4]), cell["mu_h"])
            _eq(fails, f"4 {cell['id']} mu_s", _num(row[5]), cell["mu_s"])
            got = _clean(row[6]).lower().startswith("yes")
            _eq(fails, f"4 {cell['id']} escalation", got,
                cell["escalation_eligible"])

    # -- 4.1 the atom table, with its cost columns -------------------------
    t = _find_table(tables, "atom", "s_C", "s_I", "c_C", "c_I")
    if t is None:
        fails.append("4.1 atom table not found")
    else:
        rows = _rows_by_key(t)
        for atom in cfg["outcome_atoms"]["definition"]:
            row = rows.get(atom["atom"])
            if row is None:
                fails.append(f"4.1: no row for atom {atom['atom']}")
                continue
            for col, key in ((1, "s_candidate"), (2, "s_incumbent"),
                             (3, "c_candidate"), (4, "c_incumbent"),
                             (6, "Z"), (7, "D")):
                _eq(fails, f"4.1 {atom['atom']} {key}", _num(row[col]), atom[key])
            hand = ATOM_COSTS[atom["atom"]]
            _eq(fails, f"4.1 {atom['atom']} vs the fixture's own table",
                (hand[0], hand[1], hand[2], hand[3], hand[4], hand[5]),
                (atom["s_candidate"], atom["s_incumbent"], atom["c_candidate"],
                 atom["c_incumbent"], atom["Z"], atom["D"]))

    # -- 4.1 weights and ground truth --------------------------------------
    t = _find_table(tables, "law", "BB+", "mu_h = E[Z]")
    if t is None:
        fails.append("4.1 weights table not found")
    else:
        rows = _rows_by_key(t)
        order = cfg["outcome_atoms"]["order"]
        for law, spec in cfg["outcome_laws"].items():
            row = rows.get(law)
            if row is None:
                fails.append(f"4.1: no weights row for {law}")
                continue
            for i, atom in enumerate(order):
                _eq(fails, f"4.1 {law} w[{atom}]", _num(row[1 + i]),
                    spec["weights"][atom])
            _eq(fails, f"4.1 {law} mu_h", _num(row[7]), spec["mu_h"])
            _eq(fails, f"4.1 {law} mu_s", _num(row[8]), spec["mu_s"])
            total = sum(spec["weights"].values())
            if total != cfg["outcome_atoms"]["weight_denominator"]:
                fails.append(f"4.1 {law} weights sum to {total}")
            mu_h = (spec["weights"]["BB+"] + spec["weights"]["C>I"]
                    - spec["weights"]["BB-"] - spec["weights"]["I>C"]) / total
            mu_s = (spec["weights"]["C>I"] - spec["weights"]["I>C"]) / total
            _eq(fails, f"4.1 {law} mu_h by enumeration", mu_h, spec["mu_h"])
            _eq(fails, f"4.1 {law} mu_s by enumeration", mu_s, spec["mu_s"])

    # -- 4.1 induced score distributions -----------------------------------
    t = _find_table(tables, "P(Z=+1)")
    if t is None:
        fails.append("4.1 induced distribution table not found")
    else:
        rows = _rows_by_key(t)
        for law, spec in cfg["outcome_laws"].items():
            row = rows.get(law)
            if row is None:
                fails.append(f"4.1: no induced row for {law}")
                continue
            for col, key in ((1, "P_Z"), (2, "P_D")):
                got = _nums(row[col])
                want = [spec[key]["+1"], spec[key]["0"], spec[key]["-1"]]
                if len(got) != 3:
                    fails.append(f"4.1 {law} {key}: parsed {got}")
                else:
                    for g, w, lab in zip(got, want, ("+1", "0", "-1")):
                        _eq(fails, f"4.1 {law} {key}[{lab}]", g, w, tol=5e-5)

    # -- 4.2 the delay table -----------------------------------------------
    t = _find_table(tables, "w_neg", "p_long")
    if t is None:
        fails.append("4.2 delay table not found")
    else:
        rows = _rows_by_key(t)
        by_law = {c["law"]: c for c in cfg["cells"]}
        for law, spec in cfg["outcome_laws"].items():
            row = rows.get(law)
            if row is None:
                fails.append(f"4.2: no delay row for {law}")
                continue
            _eq(fails, f"4.2 {law} w_neg", _num(row[1]), spec["w_neg"])
            got = _nums(row[2])
            _eq(fails, f"4.2 {law} p_long", got[-1] if got else None,
                by_law[law]["p_long"], tol=5e-6)
            if got and abs(got[0] - 3 * spec["w_neg"]) > 1e-9:
                fails.append(f"4.2 {law}: numerator {got[0]} != 3 * w_neg")
            den = re.search(r"/\s*(\d+)\s*$",
                            cfg["delay_rules"]["N"]["p_long_formula"])
            if den is None:
                fails.append("4.2: delay_rules.N.p_long_formula names no denominator")
            elif len(got) >= 3:
                _eq(fails, f"4.2 {law} denominator", got[1], float(den.group(1)))
            _eq(fails, f"4.2 {law} E[d]", _num(row[3]), by_law[law]["E_d"],
                tol=5e-3)

    # -- 5 seeding: the namespaces and the master seed ----------------------
    # PREREG_CHECK_2 N.2: the namespace table was compared against nothing.
    S = cfg["seeding"]
    t = _find_table(tables, "namespace", "use")
    if t is None:
        fails.append("5 namespace table not found")
    else:
        rows = _rows_by_key(t)
        if set(rows) != set(S["namespaces"]):
            fails.append(f"5: PROTOCOL namespaces {sorted(rows)} != cells.json "
                         f"{sorted(S['namespaces'])}")
        for key, spec in sorted(S["namespaces"].items()):
            row = rows.get(key)
            if row is None:
                fails.append(f"5: no row for namespace {key}")
                continue
            got_sections = _nums(row[1])
            want_sections = [float(x) for x in spec["protocol_sections"]]
            if got_sections != want_sections:
                fails.append(f"5 namespace {key}: PROTOCOL names sections "
                             f"{got_sections} != cells.json {want_sections}")
            reused = _clean(row[2]).lower().startswith("yes")
            if _clean(row[2]).lower().startswith("no"):
                reused = False
            elif not reused:
                fails.append(f"5 namespace {key}: reuse column {_clean(row[2])!r} "
                             f"is neither yes nor no")
            _eq(fails, f"5 namespace {key} reuse", reused, spec["seeds_reused"])
    seeds = set(re.findall(r"entropy\s*=\s*(\d+)", text))
    seeds |= set(re.findall(r"Master seed, frozen:\s*`?(\d+)", text))
    if not seeds:
        fails.append("5: PROTOCOL.md writes no master seed")
    elif seeds != {str(S["master_seed"])}:
        fails.append(f"5 master seed: PROTOCOL.md writes {sorted(seeds)} != "
                     f"cells.json {S['master_seed']}")

    # -- 6.1 / 6.2 / 6.3 / 6.4 ---------------------------------------------
    horizons = ("100", "500", "2000", "FINAL")

    def _horizon_header(table, label: str) -> None:
        """The `n=100` / `n=500` / `n=2000` column headers of a section 6 table.

        Unguarded before PREREG_CHECK_2 N.2: a header could name one horizon
        while its column carried another's values.
        """
        got = [n for cell in table[0][1:] for n in _nums(cell)]
        want = [float(h) for h in cfg["grid"]["fixed_horizon_summaries"]]
        if got != want:
            fails.append(f"{label} horizon headers: PROTOCOL {got} != cells.json "
                         f"{want}")

    def _cell_row_label(row, cid: str, label: str) -> None:
        """A section 6 row's `C1` `L1/N` label against the cell it names."""
        parts = _clean(row[0]).split()
        cell = next((c for c in cfg["cells"] if c["id"] == cid), None)
        if cell is None or len(parts) < 2:
            return
        want = f"{cell['law']}/{cell['delay']}"
        if parts[1] != want:
            fails.append(f"{label} {cid} row label: PROTOCOL {parts[1]!r} != "
                         f"cells.json {want!r}")

    t = _find_table(tables, "unresolved / unrevealed")
    if t is None:
        fails.append("6.1 table not found")
    else:
        _horizon_header(t, "6.1")
        rows = _rows_by_key(t)
        want_all = AR["expected_unresolved_unrevealed_fraction"]
        for law in ("L1", "L2", "L3", "L4"):
            row = rows.get(law)
            if row is None:
                fails.append(f"6.1: no row for {law}")
                continue
            for i, h in enumerate(horizons):
                got = _nums(row[1 + i])
                want = want_all[law][h]
                if len(got) != 2:
                    fails.append(f"6.1 {law} {h}: parsed {got}")
                    continue
                _eq(fails, f"6.1 {law} {h} unresolved", got[0] / 100.0, want[0],
                    tol=5e-5)
                _eq(fails, f"6.1 {law} {h} unrevealed", got[1] / 100.0, want[1],
                    tol=5e-5)

    t = _find_table(tables, "L_h > 0", "DEPLOY at")
    if t is None:
        fails.append("6.2 gate table not found")
    else:
        rows = _rows_by_key(t)
        want_all = AR["expected_path_gate_opening_prefix"]
        for cid in [c["id"] for c in cfg["cells"]]:
            row = rows.get(cid)
            if row is None:
                fails.append(f"6.2: no row for {cid}")
                continue
            _cell_row_label(row, cid, "6.2")
            for i, key in enumerate(("L_h>0", "L_s>-delta", "U_h<0", "DEPLOY")):
                cell = _clean(row[1 + i]).lower()
                got = None if cell == "never" else _num(row[1 + i])
                want = want_all[cid][key]
                if (got is None) != (want is None) or (
                        got is not None and int(got) != int(want)):
                    fails.append(f"6.2 {cid} {key}: PROTOCOL {got} != "
                                 f"cells.json {want}")

    t = _find_table(tables, "L_h`/`U_h`/`L_s")
    if t is None:
        fails.append("6.3 band endpoint table not found")
    else:
        _horizon_header(t, "6.3")
        rows = _rows_by_key(t)
        want_all = AR["expected_path_band_endpoints_Lh_Uh_Ls"]
        for cid in [c["id"] for c in cfg["cells"]]:
            row = rows.get(cid)
            if row is None:
                fails.append(f"6.3: no row for {cid}")
                continue
            for i, h in enumerate(horizons):
                got = _nums(row[1 + i])
                want = want_all[cid][h]
                if len(got) != 3:
                    fails.append(f"6.3 {cid} {h}: parsed {got}")
                    continue
                for g, w, lab in zip(got, want, ("L_h", "U_h", "L_s")):
                    _eq(fails, f"6.3 {cid} {h} {lab}", g, w, tol=5e-5)

    t = _find_table(tables, "point / narrowed")
    if t is None:
        fails.append("6.4 cost-path table not found")
    else:
        _horizon_header(t, "6.4")
        rows = _rows_by_key(t)
        want_all = AR["expected_cost_enclosure_exercise"]
        for cid in [c["id"] for c in cfg["cells"]]:
            row = rows.get(cid)
            if row is None:
                fails.append(f"6.4: no row for {cid}")
                continue
            for i, h in enumerate(horizons):
                got = _nums(row[1 + i])
                want = want_all[cid][h]
                if len(got) != 2:
                    fails.append(f"6.4 {cid} {h}: parsed {got}")
                    continue
                _eq(fails, f"6.4 {cid} {h} point", got[0] / 100.0, want[0], tol=5e-5)
                _eq(fails, f"6.4 {cid} {h} narrowed", got[1] / 100.0, want[1],
                    tol=5e-5)
                if want[0] > want[1]:
                    fails.append(f"6.4 {cid} {h}: point fraction exceeds narrowed")

    # -- 7.1 the grid -------------------------------------------------------
    t = _find_table(tables, "quantity", "value")
    if t is None:
        fails.append("7.1 grid table not found")
    else:
        G = cfg["grid"]
        want_rows = (("programs per cell", G["programs_per_cell"]),
                     ("trials per program", G["trials_per_program"]),
                     ("enrolled pairs per trial", G["max_enrolled_pairs_per_trial"]),
                     ("looks per trial", P["looks_per_trial"]),
                     ("decision-eligible looks", P["decision_eligible_looks"]))
        for label, want in want_rows:
            row = next((r for r in t[1:] if _clean(r[0]).startswith(label)), None)
            if row is None:
                fails.append(f"7.1: no row starting {label!r}")
            else:
                _eq(fails, f"7.1 {label}", _num(row[1]), want)
        row = next((r for r in t[1:]
                    if _clean(r[0]).startswith("fixed-horizon")), None)
        if row is not None:
            _eq(fails, "7.1 fixed-horizon summaries",
                [int(x) for x in _nums(row[1])], G["fixed_horizon_summaries"])
        # the two derived look counts, whole cell and not just the first number
        # (PREREG_CHECK_2 N.2: the prefix range and n_min were unguarded)
        row = _row_starting(t, "looks per trial")
        if row is not None:
            _eq(fails, "7.1 looks-per-trial derivation", _nums(row[1]),
                [float(P["looks_per_trial"]), 1.0, float(P["N_max"])])
        row = _row_starting(t, "decision-eligible looks")
        if row is not None:
            _eq(fails, "7.1 decision-eligible derivation", _nums(row[1]),
                [float(P["decision_eligible_looks"]), float(P["n_min"])])
        _eq(fails, "7.1 looks_per_trial = N_max + 1", P["N_max"] + 1,
            P["looks_per_trial"])
        _eq(fails, "7.1 decision_eligible_looks = N_max - n_min + 2",
            P["N_max"] - P["n_min"] + 2, P["decision_eligible_looks"])
        row = _row_starting(t, "constructions per trial")
        if row is not None:
            _eq(fails, "7.1 constructions per trial", _num(row[1]),
                float(len(cfg["constructions"])))
            for con in cfg["constructions"]:
                if con["id"] not in _clean(row[1]):
                    fails.append(f"7.1: construction {con['id']} is not named")

    # -- 8.2 the budget ladder ---------------------------------------------
    t = _find_table(tables, "tier", "grid", "programs total")
    if t is None:
        fails.append("8.2 ladder table not found")
    else:
        rows = _rows_by_key(t)
        cell_ids = [c["id"] for c in cfg["cells"]]
        for tier in cfg["budget"]["ladder"]:
            row = rows.get(tier["tier"])
            if row is None:
                fails.append(f"8.2: no row for {tier['tier']}")
                continue
            _eq(fails, f"8.2 {tier['tier']} programs total", _num(row[-1]),
                tier["programs_total"])
            got = sum(tier["programs"].values())
            if got != tier["programs_total"]:
                fails.append(f"8.2 {tier['tier']}: per-cell programs sum to {got}, "
                             f"not {tier['programs_total']}")
            # the GRID column, which carries the per-cell allocation and N_max and
            # was compared against nothing before PREREG_CHECK_2 N.2
            grid_cell = _clean(row[1])
            per_cell: Dict[str, int] = {}
            for names, count in re.findall(r"((?:C\d[ ,]*)+)at\s+([\d,]+)", grid_cell):
                for cid in re.findall(r"C\d", names):
                    per_cell[cid] = int(count.replace(",", ""))
            m = re.search(r"all eight cells at\s+([\d,]+)", grid_cell)
            if m:
                for cid in cell_ids:
                    per_cell.setdefault(cid, int(m.group(1).replace(",", "")))
            if per_cell != tier["programs"]:
                fails.append(f"8.2 {tier['tier']} grid column: PROTOCOL {per_cell} "
                             f"!= cells.json {tier['programs']}")
            m = re.search(r"N_max\s*=\s*([\d,]+)", grid_cell)
            if m is None:
                fails.append(f"8.2 {tier['tier']}: the grid column names no N_max")
            else:
                _eq(fails, f"8.2 {tier['tier']} N_max",
                    float(m.group(1).replace(",", "")), float(tier["N_max"]))
            m = re.search(r"summaries become\s+([\d,\s/]+)", grid_cell)
            want_summaries = tier.get("fixed_horizon_summaries")
            if (m is not None) != (want_summaries is not None):
                fails.append(f"8.2 {tier['tier']}: PROTOCOL "
                             f"{'names' if m else 'names no'} replacement horizon "
                             f"summaries, cells.json does not agree")
            elif m is not None:
                _eq(fails, f"8.2 {tier['tier']} horizon summaries",
                    [int(x) for x in _nums(m.group(1))], want_summaries)

    # -- 9.1 / 9.2 the nominal bounds --------------------------------------
    # PREREG_CHECK_2 N.2: every decision-level nominal bound was unguarded.
    RQ = cfg["reported_quantities"]
    t = _find_table(tables, "quantity", "event")
    if t is None:
        fails.append("9.1 per-gate table not found")
    else:
        row = _row_starting(t, "nominal bound")
        if row is None:
            fails.append("9.1: no 'nominal bound' row")
        else:
            _eq(fails, "9.1 nominal bound", _num(row[1]), P["alpha_gate"])
    t = _find_table(tables, "quantity", "unit", "nominal bound")
    if t is None:
        fails.append("9.2 decision-level table not found")
    else:
        rows = _rows_by_key(t)
        if set(rows) != set(RQ["decision_level"]):
            fails.append(f"9.2: PROTOCOL rows {sorted(rows)} != cells.json "
                         f"{sorted(RQ['decision_level'])}")
        for key, spec in sorted(RQ["decision_level"].items()):
            row = rows.get(key)
            if row is None:
                fails.append(f"9.2: no row for {key}")
                continue
            _eq(fails, f"9.2 {key} unit", _clean(row[1]).lower(),
                str(spec["unit"]).lower())
            if "nominal_bound" in spec:
                _eq(fails, f"9.2 {key} nominal bound", _num(row[3]),
                    spec["nominal_bound"])
            elif _clean(row[3]) not in ("-", "--"):
                fails.append(f"9.2 {key}: PROTOCOL gives a bound {_clean(row[3])!r} "
                             f"where cells.json records none")
            # the numbers inside the definition, section cross-references removed
            got = _nums(re.sub(r"\(section [0-9.]+\)", "", row[2]))
            want = _nums(str(spec["event"]))
            want += [float(re.sub(r"\D", "", c) or 0)
                     for c in spec.get("possible_only_in", [])]
            if got != want:
                fails.append(f"9.2 {key} definition: PROTOCOL numbers {got} != "
                             f"cells.json {want}")

    # -- 9.3 the flag thresholds -------------------------------------------
    t = _find_table(tables, "flag at", "smallest detectable")
    if t is None:
        fails.append("9.3 flag threshold table not found")
    else:
        keys = {"per-gate": "per_gate_ever_miscoverage",
                "trial-level": "any_erroneous_trial",
                "family-level": "family_any_erroneous"}
        by_q: Dict[str, List[dict]] = {}
        for e in cfg["exceedance_flag"]["thresholds"]:
            by_q.setdefault(e["quantity"], []).append(e)
        # the header names the two program counts the thresholds are computed at
        head_counts = [n for cell in t[0][1:] for n in _nums(cell)]
        want_counts = sorted({float(e["N"]) / (P["trials_per_program"]
                                               if e["quantity"] != "family_any_erroneous"
                                               else 1)
                              for e in cfg["exceedance_flag"]["thresholds"]})
        if head_counts != want_counts:
            fails.append(f"9.3 header program counts: PROTOCOL {head_counts} != "
                         f"cells.json {want_counts}")
        for row in t[1:]:
            label = _clean(row[0])
            key = next((v for k, v in keys.items() if label.startswith(k)), None)
            if key is None:
                fails.append(f"9.3: unrecognised row {label!r}")
                continue
            entries = sorted(by_q.get(key, []), key=lambda e: e["N"])
            if len(entries) != 2:
                fails.append(f"9.3 {key}: {len(entries)} entries in cells.json")
                continue
            bound = _nums(label)
            if bound:
                _eq(fails, f"9.3 {key} bound", bound[-1], entries[0]["bound"])
            for j, e in enumerate(entries):
                off = 1 + 3 * j
                _eq(fails, f"9.3 {key} N", _num(row[off]), e["N"])
                _eq(fails, f"9.3 {key} flag at", _num(row[off + 1]), e["flag_at_x"])
                _eq(fails, f"9.3 {key} multiple", _num(row[off + 2]),
                    e["smallest_detectable_multiple"], tol=5e-4)

    # -- 12.2 the comparison criteria and the label bijection ---------------
    CMP = cfg["comparison_to_live_ab"]
    t = _find_table(tables, "compared", "criterion")
    if t is None:
        fails.append("12.2 comparison criteria table not found")
    else:
        want_crit = CMP["compared_at_every_look"]
        for key, label in (("L_h_U_h_L_s_U_s", "L_h"),
                           ("per_pair_enclosure_endpoints", "per-pair enclosure")):
            row = _row_starting(t, label)
            if row is None:
                fails.append(f"12.2: no row starting {label!r}")
                continue
            got = re.search(r"<=\s*([0-9.e+-]+)", _clean(row[1]))
            want = re.search(r"<=\s*([0-9.e+-]+)", str(want_crit[key]))
            if got is None or want is None:
                fails.append(f"12.2 {label}: no numeric tolerance found")
            elif float(got.group(1)) != float(want.group(1)):
                fails.append(f"12.2 {label} tolerance: PROTOCOL {got.group(1)} != "
                             f"cells.json {want.group(1)}")
    t = _find_table(tables, "#11 label", "#12 label")
    if t is None:
        fails.append("12.2 label bijection table not found")
    else:
        got_map = [(_label(r[0]), _label(r[1])) for r in t[1:] if _clean(r[0])]
        want_map = [(_label(m["live_ab"]), _label(m["validation"]))
                    for m in CMP["decision_label_bijection"]["map"]]
        want_map.append(("anything else", "-"))
        if got_map != want_map:
            fails.append(f"12.2 bijection: PROTOCOL {got_map} != cells.json "
                         f"{want_map}")

    # -- 11 the fixture register -------------------------------------------
    t = _find_table(tables, "id", "assertion")
    code_ids = [c.name for c in ALL_FIXTURES]
    cfg_ids = [f["id"] for f in cfg["fixtures"]["list"]]
    if t is None:
        fails.append("11 fixture register not found")
    else:
        doc_ids = [_clean(r[0]) for r in t[1:] if _clean(r[0])]
        if doc_ids != code_ids:
            fails.append(f"11 register vs vfixtures.ALL_FIXTURES:\n"
                         f"      PROTOCOL {doc_ids}\n      code     {code_ids}")
    if cfg_ids != code_ids:
        fails.append(f"cells.json register vs vfixtures.ALL_FIXTURES:\n"
                     f"      cells.json {cfg_ids}\n      code       {code_ids}")
    # The four places that print the register as a RANGE must end at the last
    # registered fixture.  The register drift of B.2 spread exactly this way, and
    # a range is the form a reader trusts without counting.  (Narrower ranges
    # inside prose - "F01-F11 and F17 derive ..." - are claims about a subset and
    # are deliberately not matched here.)
    last = code_ids[-1][1:3] if code_ids else "00"

    def _range_end(where: str, blob: str) -> None:
        got = re.findall(r"F01[^A-Za-z0-9]{1,12}F(\d{2})", blob)
        if not got:
            fails.append(f"{where}: no fixture range found")
        for end in got:
            if end != last:
                fails.append(f"{where} prints the fixture range F01..F{end}, but "
                             f"the register ends at F{last}")

    t13 = _find_table(tables, "file", "status", "provides")
    if t13 is not None:
        row = _row_starting(t13, "vfixtures.py")
        if row is not None:
            _range_end("13.0 vfixtures.py row", _clean(row[2]))
    t13 = _find_table(tables, "file", "content")
    if t13 is not None:
        row = _row_starting(t13, "fixtures_report.json")
        if row is not None:
            _range_end("13.2 fixtures_report.json row", _clean(row[1]))
        row = _row_starting(t13, "horizon_summaries.csv")
        if row is not None:
            _eq(fails, "13.2 horizon summaries",
                [int(x) for x in _nums(row[1])][1:],
                cfg["grid"]["fixed_horizon_summaries"])
    _range_end("cells.json fixtures.deposited_to",
               str(cfg["fixtures"]["deposited_to"]))
    _range_end("cells.json modules.vfixtures.py",
               str(cfg["modules"]["exist_at_the_freeze_commit"]["vfixtures.py"]))

    # -- 13.0 the module map ------------------------------------------------
    t = _find_table(tables, "file", "status", "provides")
    if t is None:
        fails.append("13.0 module table not found")
    else:
        exists = set(cfg["modules"]["exist_at_the_freeze_commit"])
        planned = set(cfg["modules"]["specified_here_but_do_not_exist_at_the_freeze_commit"])
        for row in t[1:]:
            name = _clean(row[0])
            status = _clean(row[1]).lower()
            if "not written" in status:
                if name not in planned:
                    fails.append(f"13.0 {name}: PROTOCOL says not written, "
                                 f"cells.json does not list it as planned")
            elif status.startswith("exists"):
                if name not in exists:
                    fails.append(f"13.0 {name}: PROTOCOL says exists, cells.json "
                                 f"does not list it as existing")
                if not (HERE / name).exists():
                    fails.append(f"13.0 {name}: PROTOCOL says it exists; it does not")
            else:
                fails.append(f"13.0 {name}: unrecognised status {status!r}")
        for name in planned:
            if (HERE / name).exists():
                fails.append(f"13.0 {name} is listed as not written but exists")
        for name in exists:
            if not (HERE / name).exists():
                fails.append(f"13.0 {name} is listed as existing but does not")

    # -- internal consistency of cells.json itself --------------------------
    for cell in cfg["cells"]:
        law = cfg["outcome_laws"][cell["law"]]
        _eq(fails, f"cells.json {cell['id']} mu_h vs law", cell["mu_h"], law["mu_h"])
        _eq(fails, f"cells.json {cell['id']} mu_s vs law", cell["mu_s"], law["mu_s"])
        _eq(fails, f"cells.json {cell['id']} p_long vs w_neg", cell["p_long"],
            3 * law["w_neg"] / 40000.0, tol=5e-9)
    t4 = AR["T4_variant_N_max_1000"]
    for cid, want in AR["expected_path_gate_opening_prefix"].items():
        if cid.startswith("C"):
            got = t4["expected_path_gate_opening_prefix"][cid]
            if got != want:
                fails.append(f"T4 gate row {cid}: {got} != {want}")
    return fails


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
ALL_FIXTURES: Tuple[FixtureCase, ...] = (
    FixtureCase("F01_pre_enrolled_orientation",
                "pre-enrolled AB/BA assignment",
                _f01_pre_enrolled_orientation.__doc__ or "",
                _f01_pre_enrolled_orientation),
    FixtureCase("F02_enrollment_denominator",
                "exact enrollment denominators; n = 0 abstention",
                _f02_enrollment_denominator.__doc__ or "",
                _f02_enrollment_denominator),
    FixtureCase("F03_repeated_update_idempotence",
                "repeated-update idempotence",
                _f03_repeated_update_idempotence.__doc__ or "",
                _f03_repeated_update_idempotence),
    FixtureCase("F04_nonoverlapping_pair_ids",
                "nonoverlapping pair ids and arrival positions",
                _f04_nonoverlapping_pair_ids.__doc__ or "",
                _f04_nonoverlapping_pair_ids),
    FixtureCase("F05_completion_order_permutations",
                "completion-order permutations (all 720)",
                _f05_completion_order_permutations.__doc__ or "",
                _f05_completion_order_permutations),
    FixtureCase("F06_joint_failures",
                "joint failures tie",
                _f06_joint_failures.__doc__ or "",
                _f06_joint_failures),
    FixtureCase("F07_strict_tolerance_equality",
                "strict tolerance equality",
                _f07_strict_tolerance_equality.__doc__ or "",
                _f07_strict_tolerance_equality),
    FixtureCase("F08_unknown_outcomes",
                "unknown outcomes; narrowing without a certificate",
                _f08_unknown_outcomes.__doc__ or "",
                _f08_unknown_outcomes),
    FixtureCase("F09_cap_timeout_finalization",
                "cap and timeout finalisation",
                _f09_cap_timeout_finalization.__doc__ or "",
                _f09_cap_timeout_finalization),
    FixtureCase("F10_switch_phase_exclusion",
                "switch-phase exclusion",
                _f10_switch_phase_exclusion.__doc__ or "",
                _f10_switch_phase_exclusion),
    FixtureCase("F11_containment_audit",
                "every resolved score inside every prior bound",
                _f11_containment_audit.__doc__ or "",
                _f11_containment_audit),
    FixtureCase("F12_band_formula",
                "band assembly vs a literal transcription of the formula",
                _f12_band_formula.__doc__ or "",
                _f12_band_formula),
    FixtureCase("F13_decision_rule",
                "frozen decision rule and same-look conjunction",
                _f13_decision_rule.__doc__ or "",
                _f13_decision_rule),
    FixtureCase("F14_radius_sweep",
                "radius agreement at strict equality over n = 1..20,000",
                _f14_radius_sweep.__doc__ or "",
                _f14_radius_sweep),
    FixtureCase("F15_protocol_config_agreement",
                "PROTOCOL.md and cells.json agree value for value",
                _f15_protocol_config_agreement.__doc__ or "",
                _f15_protocol_config_agreement),
    FixtureCase("F16_import_graph_independence",
                "the independence constraint, machine-checked",
                _f16_import_graph_independence.__doc__ or "",
                _f16_import_graph_independence),
    FixtureCase("F17_atom_cost_table",
                "atom cost columns and the cost enclosure path",
                _f17_atom_cost_table.__doc__ or "",
                _f17_atom_cost_table),
    FixtureCase("F18_pinned_file_hashes",
                "every provenance pin recomputed from the file it names",
                _f18_pinned_file_hashes.__doc__ or "",
                _f18_pinned_file_hashes),
)


def run_all() -> List[Tuple[str, List[str]]]:
    """Run every fixture; return ``[(name, failures)]`` with failures empty on pass."""
    out: List[Tuple[str, List[str]]] = []
    for case in ALL_FIXTURES:
        try:
            out.append((case.name, case.run()))
        except Exception as exc:                            # noqa: BLE001
            out.append((case.name, [f"raised {type(exc).__name__}: {exc}"]))
    return out


def main() -> int:
    results = run_all()
    failed = 0
    for name, fails in results:
        if fails:
            failed += 1
            print(f"FAIL {name}")
            for f in fails:
                print(f"       {f}")
        else:
            print(f"ok   {name}")
    print(f"\n{len(results) - failed}/{len(results)} fixtures passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
