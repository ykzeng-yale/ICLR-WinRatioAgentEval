"""Independent re-implementation of the issue-11 live monitor band and decision rule.

Issue #12 (independent CPU validation).  The scientific point of this module is
that it is written FROM THE FORMULA ALONE, so that a disagreement with the #11
monitor is evidence of a defect in one of the two implementations rather than a
shared bug.

SOURCE DECLARATION -- files read while writing this module
----------------------------------------------------------
Read (the only sources used):
  * reviews/arxiv_live_design_guidance.md   -- the design/formula document
  * src/winstats.py                         -- the pinned primitives
                                               (``Tier``, ``compare``,
                                               ``normal_mixture_radius``)
  * the issue-#12 task text supplied by the coordinator

Deliberately NOT read, opened, grepped or imported (independence constraint):
  * experiments/live_ab/lab_monitor.py
  * experiments/live_ab/lab_enclosure.py
  * experiments/live_ab/lab_reference_rule.py
  * experiments/live_ab/design/protocol_FINAL.md  (sections 7 and 8)
  * any other file under experiments/live_ab/

A pinned read-only copy of the #11 monitor is loaded, by hash, ONLY at the later
comparison step, which lives outside this module.  Any disagreement found there
is reported as a defect and is never reconciled by editing either side.

Frozen decision rule transcribed from the guidance document
-----------------------------------------------------------
Guidance item 3 gives, at a look on a selected enrollment prefix ``n`` and for
each score ``j``::

    r   = normal_mixture_radius(n, alpha=alpha_gate, rho=100., variance_process=n)
    L_j = sum(lower_j[:n]) / n - r
    U_j = sum(upper_j[:n]) / n + r

with the bounds optionally intersected with ``[-1, 1]`` (we always intersect).
The primary rule uses the CURRENT FULL ENROLLED PREFIX ``n = N(t)`` at every
event; no maximisation over prefixes is performed.

Guidance item 6 plus the frozen coordinator allocation give:

    DEPLOY            iff  L_hierarchy > 0  and  L_success > -delta
    RETAIN INCUMBENT  iff  U_hierarchy < 0

both evaluated at the SAME look and the SAME prefix (same-look conjunction),
and only once ``n >= n_min``.  Program alpha .05 over four prespecified trials
gives .0125 per trial; two monitored scores per trial give alpha_gate = .00625
per score.  One two-sided band per score serves both tails (guidance item 4),
so no further split is taken for the deploy and harm tails.  delta = 0.03,
n_min = 100, rho = 100.

Enclosure semantics (guidance items 3 and 5)
--------------------------------------------
Every enrolled pair holds its score in an immutable enrollment position.  An
unresolved score starts at the full range ``[-1, 1]`` and is NARROWED only on
logically certain facts; it is never widened, never dropped, and never appended
as a fresh observation.  The success-component enclosure is
``[sA_low - sB_high, sA_high - sB_low]``.  The hierarchy enclosure is obtained
by exhaustive enumeration of the feasible completions.  A score is COLLAPSED to
a point, and marked certified, only on a valid final-score certificate, i.e.
when both episodes of the pair are final and ``winstats.compare`` is evaluable
on complete finite outcomes.

Target and interpretation boundary
-----------------------------------
The band is a two-sided band for the ENROLLMENT-RUNNING conditional-mean target
on the current full enrolled prefix.  Coverage is of a bounded arbitrary running
mean; reading the sign of that target as a causal pair-orientation effect needs
the separate design assumptions of guidance items 1, 2 and 7 (pre-enrolled
nonoverlapping arrival positions, one fresh coin per pair, no cross-pair
interference, frozen both-systems configuration).  Nothing in this module
establishes those assumptions.

CPU only.  No model call, no API call, no network, no new dependency.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, FrozenSet, Hashable, List, Optional, Sequence, Set, Tuple

import numpy as np

# --- pinned primitives -------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(_REPO_ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from winstats import Tier, compare, normal_mixture_radius  # noqa: E402

__all__ = [
    "PROGRAM_ALPHA", "N_TRIALS", "GATES_PER_TRIAL", "ALPHA_PER_TRIAL", "ALPHA_GATE",
    "RHO", "DELTA", "N_MIN", "COST_RELATIVE_TOLERANCE", "COST_ABSOLUTE_TOLERANCE",
    "TIERS", "SCORE_NAMES", "DEPLOY", "RETAIN_INCUMBENT", "CONTINUE",
    "ValidationError", "EnclosureContradiction", "ProtocolViolation", "SwitchPhaseError",
    "Enclosure", "Episode", "Pair", "Band", "LookResult", "ValidationMonitor",
    "cost_order_possibilities", "hierarchy_bounds", "success_bounds",
    "final_hierarchy_score", "final_success_score",
    "normal_mixture_band", "decide", "radius_from_formula",
]

# --- frozen program constants (guidance item 4 + coordinator allocation) -----
PROGRAM_ALPHA = 0.05
N_TRIALS = 4
GATES_PER_TRIAL = 2                                     # hierarchy, success
ALPHA_PER_TRIAL = PROGRAM_ALPHA / N_TRIALS              # .0125
ALPHA_GATE = ALPHA_PER_TRIAL / GATES_PER_TRIAL          # .00625, one band per score
RHO = 100.0
DELTA = 0.03
N_MIN = 100

# --- frozen endpoint definition (guidance item 5) ---------------------------
COST_RELATIVE_TOLERANCE = 0.05
COST_ABSOLUTE_TOLERANCE = 0.0
TIERS = (
    Tier("success"),
    Tier("cost", higher_better=False,
         absolute_tolerance=COST_ABSOLUTE_TOLERANCE,
         relative_tolerance=COST_RELATIVE_TOLERANCE),
)
SCORE_NAMES = ("hierarchy", "success")

DEPLOY = "DEPLOY"
RETAIN_INCUMBENT = "RETAIN_INCUMBENT"
CONTINUE = "CONTINUE"

SCORE_LOW, SCORE_HIGH = -1.0, 1.0
_SLACK = 1e-9           # absolute slack for float containment checks only


class ValidationError(Exception):
    """Base class for independent-validation failures."""


class EnclosureContradiction(ValidationError):
    """A newly asserted fact is inconsistent with an already certain fact."""


class ProtocolViolation(ValidationError):
    """An event violates the frozen enrollment/reveal protocol."""


class SwitchPhaseError(ProtocolViolation):
    """Enrollment attempted after the traffic switch (guidance item 7)."""


# ---------------------------------------------------------------------------
# Enclosure
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Enclosure:
    """A bound on one not-necessarily-resolved score, valued in [-1, 1].

    ``certified`` is True only when the value was collapsed on a final-score
    certificate.  A degenerate interval reached by enumeration is logically just
    as tight but is deliberately NOT marked certified: the distinction records
    whether a valid final score exists, which is what guidance item 5 licenses
    a collapse on.
    """

    lo: float
    hi: float
    certified: bool = False

    def __post_init__(self) -> None:
        if not (math.isfinite(self.lo) and math.isfinite(self.hi)):
            raise ValidationError("Enclosure bounds must be finite")
        if self.lo > self.hi + _SLACK:
            raise EnclosureContradiction(f"Empty enclosure [{self.lo}, {self.hi}]")
        if self.lo < SCORE_LOW - _SLACK or self.hi > SCORE_HIGH + _SLACK:
            raise ValidationError(
                f"Enclosure [{self.lo}, {self.hi}] escapes the bounded score range")

    # -- construction --------------------------------------------------------
    @classmethod
    def full(cls) -> "Enclosure":
        """The starting bound of every unresolved score: the full range."""
        return cls(SCORE_LOW, SCORE_HIGH, False)

    # -- queries -------------------------------------------------------------
    @property
    def width(self) -> float:
        return self.hi - self.lo

    @property
    def resolved(self) -> bool:
        """True when the bound is a point, however it got there."""
        return self.hi - self.lo <= _SLACK

    def contains(self, value: float, slack: float = _SLACK) -> bool:
        return self.lo - slack <= value <= self.hi + slack

    # -- monotone updates ----------------------------------------------------
    def narrow(self, lo: float, hi: float) -> "Enclosure":
        """Intersect with a newly certain bound.  Never widens; idempotent."""
        if lo > hi + _SLACK:
            raise EnclosureContradiction(f"Cannot narrow to empty [{lo}, {hi}]")
        new_lo = max(self.lo, float(lo))
        new_hi = min(self.hi, float(hi))
        if new_lo > new_hi + _SLACK:
            raise EnclosureContradiction(
                f"Fact [{lo}, {hi}] contradicts established bound "
                f"[{self.lo}, {self.hi}]")
        new_lo = min(new_lo, new_hi)
        if self.certified and not (new_lo - _SLACK <= self.lo <= new_hi + _SLACK):
            raise EnclosureContradiction("Fact contradicts a final-score certificate")
        out = Enclosure(new_lo, new_hi, self.certified)
        if out.width > self.width + _SLACK:          # defensive: never widen
            raise ValidationError("narrow() widened an enclosure")
        return out

    def collapse(self, value: float) -> "Enclosure":
        """Collapse on a valid final-score certificate."""
        value = float(value)
        if not self.contains(value):
            raise EnclosureContradiction(
                f"Final score {value} lies outside the established bound "
                f"[{self.lo}, {self.hi}]")
        if self.certified and abs(self.lo - value) > _SLACK:
            raise EnclosureContradiction(
                f"Second certificate {value} disagrees with {self.lo}")
        return Enclosure(value, value, True)

    def as_tuple(self) -> Tuple[float, float, bool]:
        return (self.lo, self.hi, self.certified)


# ---------------------------------------------------------------------------
# Episode state (one arm of one pair)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Episode:
    """What is LOGICALLY CERTAIN about one episode so far.

    ``success`` is known iff ``success_lo == success_hi``.  ``cost`` is bracketed
    by ``[cost_lo, cost_hi]``: elapsed cost is a valid lower bound only because
    the frozen accounting makes cost nondecreasing, and the frozen resource cap
    is a valid upper bound.  Absence of failure so far is NOT success
    (guidance item 5): a pending episode keeps ``success_lo=0, success_hi=1``.
    """

    slot_id: Hashable
    cost_cap: float
    success_lo: int = 0
    success_hi: int = 1
    cost_lo: float = 0.0
    cost_hi: float = math.inf
    final: bool = False

    def __post_init__(self) -> None:
        if self.success_lo not in (0, 1) or self.success_hi not in (0, 1):
            raise ValidationError("success bounds must be 0/1")
        if self.success_lo > self.success_hi:
            raise EnclosureContradiction(f"slot {self.slot_id}: success bounds crossed")
        if not (math.isfinite(self.cost_cap) and self.cost_cap >= 0):
            raise ValidationError("cost_cap must be finite and nonnegative")
        if self.cost_hi == math.inf:      # unspecified upper bound means "the cap"
            object.__setattr__(self, "cost_hi", float(self.cost_cap))
        if self.cost_lo < -_SLACK:
            raise ValidationError("costs are nonnegative by the frozen accounting")
        if self.cost_lo > self.cost_hi + _SLACK:
            raise EnclosureContradiction(f"slot {self.slot_id}: cost bounds crossed")
        if self.cost_hi > self.cost_cap + _SLACK:
            raise ValidationError("cost upper bound exceeds the frozen resource cap")
        if self.final and (self.success_lo != self.success_hi
                           or abs(self.cost_hi - self.cost_lo) > _SLACK):
            raise ValidationError("a final episode must be a point outcome")

    @classmethod
    def pending(cls, slot_id: Hashable, cost_cap: float) -> "Episode":
        return cls(slot_id=slot_id, cost_cap=float(cost_cap),
                   cost_lo=0.0, cost_hi=float(cost_cap))

    # -- queries -------------------------------------------------------------
    @property
    def success_known(self) -> bool:
        return self.success_lo == self.success_hi

    def success_set(self) -> Tuple[int, ...]:
        return tuple(range(self.success_lo, self.success_hi + 1))

    # -- monotone updates (all idempotent) -----------------------------------
    def _guard_final(self, what: str) -> None:
        if self.final:
            raise EnclosureContradiction(
                f"slot {self.slot_id}: {what} after the final certificate")

    def with_failure(self) -> "Episode":
        if self.success_hi == 0:
            return self
        if self.success_lo == 1:
            raise EnclosureContradiction(f"slot {self.slot_id}: failure after success")
        self._guard_final("failure")
        return replace(self, success_hi=0)

    def with_success(self) -> "Episode":
        if self.success_lo == 1:
            return self
        if self.success_hi == 0:
            raise EnclosureContradiction(f"slot {self.slot_id}: success after failure")
        self._guard_final("success")
        return replace(self, success_lo=1)

    def with_elapsed_cost(self, elapsed: float) -> "Episode":
        elapsed = float(elapsed)
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValidationError("elapsed cost must be finite and nonnegative")
        if elapsed <= self.cost_lo:
            return self                     # no new information; idempotent
        if elapsed > self.cost_hi + _SLACK:
            raise EnclosureContradiction(
                f"slot {self.slot_id}: elapsed {elapsed} exceeds upper bound "
                f"{self.cost_hi}")
        self._guard_final("elapsed cost")
        return replace(self, cost_lo=min(elapsed, self.cost_hi))

    def with_cost_upper(self, bound: float) -> "Episode":
        bound = float(bound)
        if bound >= self.cost_hi:
            return self
        if bound < self.cost_lo - _SLACK:
            raise EnclosureContradiction(
                f"slot {self.slot_id}: cost upper bound {bound} below lower bound")
        self._guard_final("cost upper bound")
        return replace(self, cost_hi=max(bound, self.cost_lo))

    def finalized(self, success: int, cost: float) -> "Episode":
        """Apply a final-outcome certificate.  Idempotent for identical input."""
        success = int(success)
        cost = float(cost)
        if success not in (0, 1):
            raise ValidationError("success must be 0 or 1")
        if not math.isfinite(cost) or cost < 0:
            raise ValidationError("final cost must be finite and nonnegative")
        if self.final:
            if success == self.success_lo and abs(cost - self.cost_lo) <= _SLACK:
                return self
            raise EnclosureContradiction(
                f"slot {self.slot_id}: second final certificate disagrees")
        if success not in self.success_set():
            raise EnclosureContradiction(
                f"slot {self.slot_id}: final success {success} contradicts "
                f"established bound")
        if not (self.cost_lo - _SLACK <= cost <= self.cost_hi + _SLACK):
            raise EnclosureContradiction(
                f"slot {self.slot_id}: final cost {cost} outside "
                f"[{self.cost_lo}, {self.cost_hi}]")
        if cost > self.cost_cap + _SLACK:
            raise ValidationError(f"slot {self.slot_id}: final cost exceeds the cap")
        return replace(self, success_lo=success, success_hi=success,
                       cost_lo=cost, cost_hi=cost, final=True)

    def timed_out(self) -> "Episode":
        """The frozen cap/timeout finalisation rule.

        Guidance item 5: infrastructure loss and cap exhaustion are handled by
        the frozen outcome/missingness rule, never by deletion.  The rule fixed
        here is: an episode that reaches the cap is finalised as a FAILURE that
        consumed the full cap.  This is applied identically on both labels.
        """
        return self.finalized(0, self.cost_cap)


# ---------------------------------------------------------------------------
# Score enclosures from episode facts
# ---------------------------------------------------------------------------
def cost_order_possibilities(a_lo: float, a_hi: float, b_lo: float, b_hi: float,
                             rtol: float = COST_RELATIVE_TOLERANCE,
                             atol: float = COST_ABSOLUTE_TOLERANCE) -> Set[int]:
    """Feasible signed cost-tier preferences for A over B (lower cost better).

    ``compare`` calls the tier decisive iff ``|a-b| > atol + rtol*max(|a|,|b|)``
    and then takes ``sign(-(a-b))``.  Costs are nonnegative, so ``|.| = .``.

    With ``0 <= rtol < 1`` the predicate ``(cB - cA) - atol - rtol*max(cA,cB) > 0``
    is nonincreasing in ``cA`` (derivative ``-1 - rtol*1{cA>cB}``) and increasing
    in ``cB`` (derivative ``1 - rtol*1{cB>cA} >= 1-rtol > 0``), so ``+1`` is
    achievable iff it is achievable at the corner ``(cA, cB) = (a_lo, b_hi)``,
    and symmetrically ``-1`` at ``(a_hi, b_lo)``.  A tie is achievable iff the
    boxes overlap (take ``cA = cB``) or the closest corner pair is within
    tolerance.  Exhaustively checked against a brute-force grid in the tests.
    """
    if not (0.0 <= rtol < 1.0) or atol < 0.0:
        raise ValidationError("require 0 <= rtol < 1 and atol >= 0")
    vals: Set[int] = set()
    if (b_hi - a_lo) > atol + rtol * max(abs(a_lo), abs(b_hi)):
        vals.add(1)
    if (a_hi - b_lo) > atol + rtol * max(abs(a_hi), abs(b_lo)):
        vals.add(-1)
    if a_hi >= b_lo and b_hi >= a_lo:                       # boxes overlap
        vals.add(0)
    elif a_hi < b_lo:
        if (b_lo - a_hi) <= atol + rtol * max(abs(a_hi), abs(b_lo)):
            vals.add(0)
    else:                                                   # b_hi < a_lo
        if (a_lo - b_hi) <= atol + rtol * max(abs(a_lo), abs(b_hi)):
            vals.add(0)
    if not vals:                                            # pragma: no cover
        raise ValidationError("empty feasible cost-order set")
    return vals


def hierarchy_feasible_values(ep_a: Episode, ep_b: Episode,
                              rtol: float = COST_RELATIVE_TOLERANCE,
                              atol: float = COST_ABSOLUTE_TOLERANCE) -> FrozenSet[int]:
    """Exhaustive enumeration of the hierarchy scores still reachable.

    Tier 0 is success (higher better, zero tolerance).  Tier 1 is cost (lower
    better, relative tolerance) and is ELIGIBLE ONLY WHEN BOTH EPISODES SUCCEED,
    so a joint failure is a tie no matter how the costs differ (guidance item 5).
    """
    vals: Set[int] = set()
    for sa in ep_a.success_set():
        for sb in ep_b.success_set():
            if sa > sb:
                vals.add(1)
            elif sa < sb:
                vals.add(-1)
            elif sa == 0:
                vals.add(0)                                 # joint failure ties
            else:
                vals |= cost_order_possibilities(
                    ep_a.cost_lo, ep_a.cost_hi, ep_b.cost_lo, ep_b.cost_hi,
                    rtol=rtol, atol=atol)
    if not vals:                                            # pragma: no cover
        raise ValidationError("empty feasible hierarchy set")
    return frozenset(vals)


def hierarchy_bounds(ep_a: Episode, ep_b: Episode,
                     rtol: float = COST_RELATIVE_TOLERANCE,
                     atol: float = COST_ABSOLUTE_TOLERANCE) -> Tuple[float, float]:
    vals = hierarchy_feasible_values(ep_a, ep_b, rtol=rtol, atol=atol)
    return (float(min(vals)), float(max(vals)))


def success_bounds(ep_a: Episode, ep_b: Episode) -> Tuple[float, float]:
    """``[sA_low - sB_high, sA_high - sB_low]`` exactly as guidance item 5 states."""
    return (float(ep_a.success_lo - ep_b.success_hi),
            float(ep_a.success_hi - ep_b.success_lo))


def _require_final(ep_a: Episode, ep_b: Episode) -> None:
    if not (ep_a.final and ep_b.final):
        raise ProtocolViolation(
            "a final-score certificate needs complete finite outcomes on both arms")


def final_hierarchy_score(ep_a: Episode, ep_b: Episode,
                          tiers: Sequence[Tier] = TIERS) -> int:
    """The final hierarchy score via the pinned ``winstats.compare``."""
    _require_final(ep_a, ep_b)
    a = np.array([[float(ep_a.success_lo), float(ep_a.cost_lo)]])
    b = np.array([[float(ep_b.success_lo), float(ep_b.cost_lo)]])
    both_succeed = bool(ep_a.success_lo == 1 and ep_b.success_lo == 1)
    eligible = np.array([[True, both_succeed]])
    result, _tier = compare(a, b, list(tiers), eligible=eligible)
    return int(result[0])


def final_success_score(ep_a: Episode, ep_b: Episode) -> int:
    _require_final(ep_a, ep_b)
    return int(ep_a.success_lo - ep_b.success_lo)


# ---------------------------------------------------------------------------
# Pair (an immutable enrollment position)
# ---------------------------------------------------------------------------
@dataclass
class Pair:
    pair_id: Hashable
    position: int
    coin: str                       # 'AB' or 'BA'
    slot_first: Hashable
    slot_second: Hashable
    hierarchy: Enclosure
    success: Enclosure

    def arm_slots(self) -> Tuple[Hashable, Hashable]:
        """Return ``(slot_of_arm_A, slot_of_arm_B)`` for this pair's coin.

        The coin is drawn and logged BEFORE either task executes (guidance
        item 1).  'AB' means the first arrival position carries the candidate A;
        'BA' means the second one does.  The score is always oriented as
        candidate minus incumbent, so the positive direction matches the live
        candidate label.
        """
        if self.coin == "AB":
            return (self.slot_first, self.slot_second)
        return (self.slot_second, self.slot_first)

    def enclosure(self, score: str) -> Enclosure:
        if score == "hierarchy":
            return self.hierarchy
        if score == "success":
            return self.success
        raise ValidationError(f"unknown score {score!r}")


# ---------------------------------------------------------------------------
# Band and decision
# ---------------------------------------------------------------------------
def radius_from_formula(n: int, alpha_gate: float = ALPHA_GATE,
                        rho: float = RHO) -> float:
    """``normal_mixture_radius(n, alpha=alpha_gate, rho=rho, variance_process=n)``.

    Balanced orientation keeps both scores in [-1,1], so V_n = n (guidance
    item 3).  Kept as a named wrapper so that fixtures can compare it against a
    literal transcription of the closed form.
    """
    if n <= 0:
        raise ValidationError("radius is undefined at n = 0")
    return float(normal_mixture_radius(int(n), alpha=alpha_gate, rho=rho,
                                       variance_process=int(n)))


@dataclass(frozen=True)
class Band:
    name: str
    n: int
    sum_lower: float
    sum_upper: float
    mean_lower: float
    mean_upper: float
    radius: float
    lower: float
    upper: float

    @property
    def width(self) -> float:
        return self.upper - self.lower


def normal_mixture_band(lowers: Sequence[float], uppers: Sequence[float], n: int,
                        alpha_gate: float = ALPHA_GATE, rho: float = RHO,
                        name: str = "") -> Band:
    """The guidance item 3 band on the enrollment prefix ``n``.

    ``lowers``/``uppers`` are indexed by IMMUTABLE ENROLLMENT POSITION.  The
    denominator is ``n``, the number of fully enrolled/randomised pairs -- never
    the number completed (guidance item 2).  At ``n = 0`` the full range is
    displayed and no decision is taken.
    """
    n = int(n)
    if n < 0 or n > len(lowers) or len(lowers) != len(uppers):
        raise ValidationError("prefix n must index the enrollment ledger")
    if n == 0:
        return Band(name=name, n=0, sum_lower=0.0, sum_upper=0.0,
                    mean_lower=SCORE_LOW, mean_upper=SCORE_HIGH, radius=math.inf,
                    lower=SCORE_LOW, upper=SCORE_HIGH)
    s_lo = float(math.fsum(lowers[:n]))
    s_hi = float(math.fsum(uppers[:n]))
    r = radius_from_formula(n, alpha_gate=alpha_gate, rho=rho)
    lower = min(max(s_lo / n - r, SCORE_LOW), SCORE_HIGH)
    upper = min(max(s_hi / n + r, SCORE_LOW), SCORE_HIGH)
    if lower > upper:                                       # pragma: no cover
        raise ValidationError("band lower exceeded band upper")
    return Band(name=name, n=n, sum_lower=s_lo, sum_upper=s_hi,
                mean_lower=s_lo / n, mean_upper=s_hi / n, radius=r,
                lower=lower, upper=upper)


def decide(hierarchy: Band, success: Band, delta: float = DELTA,
           n_min: int = N_MIN) -> str:
    """The frozen finite decision policy, with the same-look conjunction enforced.

    DEPLOY            iff L_hierarchy > 0 and L_success > -delta
    RETAIN INCUMBENT  iff U_hierarchy < 0
    otherwise CONTINUE (abstention is preserved; there is no third action).
    """
    if hierarchy.n != success.n:
        raise ProtocolViolation(
            "the deploy conjunction must be read at one look on one prefix "
            f"(hierarchy n={hierarchy.n}, success n={success.n})")
    if hierarchy.n < n_min:
        return CONTINUE
    if hierarchy.lower > 0.0 and success.lower > -delta:
        return DEPLOY
    if hierarchy.upper < 0.0:
        return RETAIN_INCUMBENT
    return CONTINUE


@dataclass(frozen=True)
class LookResult:
    label: str
    n_enrolled: int
    hierarchy: Band
    success: Band
    decision: str
    n_certified: int
    n_point_resolved: int
    switched: bool

    @property
    def unresolved_fraction(self) -> float:
        if self.n_enrolled == 0:
            return 0.0
        return 1.0 - self.n_certified / self.n_enrolled


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------
class ValidationMonitor:
    """Independent enrollment ledger, enclosure bookkeeping, band and decision.

    Guidance item 2 in full: every pair keeps its immutable enrollment position;
    reveal events update the EXISTING enclosure of that position; an update is
    never appended as a new observation; slow pairs are never dropped; the
    denominator is never the number completed; scores are never sorted by reveal
    time.  Consequently the state is invariant to the order in which reveals of
    distinct episodes arrive, and repeated identical updates are idempotent.
    """

    def __init__(self, cost_cap: float = 100.0, alpha_gate: float = ALPHA_GATE,
                 rho: float = RHO, delta: float = DELTA, n_min: int = N_MIN,
                 tiers: Sequence[Tier] = TIERS,
                 cost_relative_tolerance: float = COST_RELATIVE_TOLERANCE,
                 cost_absolute_tolerance: float = COST_ABSOLUTE_TOLERANCE,
                 record_history: bool = False) -> None:
        self.cost_cap = float(cost_cap)
        self.alpha_gate = float(alpha_gate)
        self.rho = float(rho)
        self.delta = float(delta)
        self.n_min = int(n_min)
        self.tiers = tuple(tiers)
        self.rtol = float(cost_relative_tolerance)
        self.atol = float(cost_absolute_tolerance)
        self.record_history = bool(record_history)

        self.pairs: List[Pair] = []                         # by enrollment position
        self._pair_index: Dict[Hashable, int] = {}
        self._slot_owner: Dict[Hashable, int] = {}
        self.episodes: Dict[Hashable, Episode] = {}
        self.switched = False
        self.switch_position: Optional[int] = None
        self.followup_arrivals: List[Hashable] = []
        self.looks: List[LookResult] = []
        self.history: List[Tuple[str, int, Dict[Hashable, Tuple[Enclosure, Enclosure]]]] = []

    # -- enrollment ----------------------------------------------------------
    def enroll(self, pair_id: Hashable, coin: str,
               slot_first: Hashable, slot_second: Hashable,
               cost_cap: Optional[float] = None) -> int:
        """Freeze one pair: two nonoverlapping arrival positions and one coin."""
        if self.switched:
            raise SwitchPhaseError(
                "randomisation stopped at the traffic switch; post-switch traffic "
                "is an operational follow-up cohort, not new pairs")
        if coin not in ("AB", "BA"):
            raise ValidationError("coin must be 'AB' or 'BA'")
        if pair_id in self._pair_index:
            raise ProtocolViolation(f"duplicate pair id {pair_id!r}")
        if slot_first == slot_second:
            raise ProtocolViolation(
                f"pair {pair_id!r}: the two arrival positions must be distinct")
        for slot in (slot_first, slot_second):
            if slot in self._slot_owner:
                raise ProtocolViolation(
                    f"arrival position {slot!r} already belongs to pair "
                    f"{self.pairs[self._slot_owner[slot]].pair_id!r}; pairs must "
                    f"occupy nonoverlapping arrival positions")
        cap = self.cost_cap if cost_cap is None else float(cost_cap)
        position = len(self.pairs)
        pair = Pair(pair_id=pair_id, position=position, coin=coin,
                    slot_first=slot_first, slot_second=slot_second,
                    hierarchy=Enclosure.full(), success=Enclosure.full())
        self.pairs.append(pair)
        self._pair_index[pair_id] = position
        for slot in (slot_first, slot_second):
            self._slot_owner[slot] = position
            self.episodes[slot] = Episode.pending(slot, cap)
        return position

    def switch(self) -> int:
        """Record the traffic switch (guidance item 7).

        Enrollment stops.  Every already-enrolled pair is retained and finished
        under its original assignment and frozen horizon; its updates are still
        accepted.  Later all-one-arm traffic is a follow-up cohort excluded from
        the estimator.
        """
        if not self.switched:
            self.switched = True
            self.switch_position = len(self.pairs)
        return int(self.switch_position or 0)

    def record_followup_arrival(self, slot_id: Hashable) -> None:
        """Log post-switch single-arm traffic, excluded from ``n`` by construction."""
        if not self.switched:
            raise ProtocolViolation("follow-up cohort exists only after the switch")
        if slot_id in self._slot_owner:
            raise ProtocolViolation(
                f"{slot_id!r} is an enrolled arrival position, not follow-up traffic")
        self.followup_arrivals.append(slot_id)

    # -- reveals -------------------------------------------------------------
    def _owner(self, slot_id: Hashable) -> Pair:
        if slot_id not in self._slot_owner:
            raise ProtocolViolation(
                f"no enrolled pair owns arrival position {slot_id!r}; the pair and "
                f"its coin must be frozen before either task executes")
        return self.pairs[self._slot_owner[slot_id]]

    def _apply(self, slot_id: Hashable, new_episode: Episode) -> None:
        pair = self._owner(slot_id)
        self.episodes[slot_id] = new_episode
        self._refresh(pair)

    def observe_failure(self, slot_id: Hashable) -> None:
        self._apply(slot_id, self._owner_episode(slot_id).with_failure())

    def observe_success(self, slot_id: Hashable) -> None:
        self._apply(slot_id, self._owner_episode(slot_id).with_success())

    def observe_elapsed_cost(self, slot_id: Hashable, elapsed: float) -> None:
        """Elapsed cost is a lower bound ONLY because cost cannot decrease."""
        self._apply(slot_id, self._owner_episode(slot_id).with_elapsed_cost(elapsed))

    def observe_cost_upper(self, slot_id: Hashable, bound: float) -> None:
        self._apply(slot_id, self._owner_episode(slot_id).with_cost_upper(bound))

    def finalize(self, slot_id: Hashable, success: int, cost: float) -> None:
        self._apply(slot_id, self._owner_episode(slot_id).finalized(success, cost))

    def timeout(self, slot_id: Hashable) -> None:
        """Apply the frozen cap/timeout finalisation rule -- never a deletion."""
        self._apply(slot_id, self._owner_episode(slot_id).timed_out())

    def _owner_episode(self, slot_id: Hashable) -> Episode:
        self._owner(slot_id)
        return self.episodes[slot_id]

    # -- enclosure bookkeeping ----------------------------------------------
    def _refresh(self, pair: Pair) -> None:
        slot_a, slot_b = pair.arm_slots()
        ep_a, ep_b = self.episodes[slot_a], self.episodes[slot_b]
        h_lo, h_hi = hierarchy_bounds(ep_a, ep_b, rtol=self.rtol, atol=self.atol)
        pair.hierarchy = pair.hierarchy.narrow(h_lo, h_hi)
        s_lo, s_hi = success_bounds(ep_a, ep_b)
        pair.success = pair.success.narrow(s_lo, s_hi)
        if ep_a.final and ep_b.final:
            pair.hierarchy = pair.hierarchy.collapse(
                final_hierarchy_score(ep_a, ep_b, self.tiers))
            pair.success = pair.success.collapse(final_success_score(ep_a, ep_b))

    # -- looks ---------------------------------------------------------------
    def score_bounds(self, score: str) -> Tuple[List[float], List[float]]:
        lowers = [p.enclosure(score).lo for p in self.pairs]
        uppers = [p.enclosure(score).hi for p in self.pairs]
        return lowers, uppers

    def band(self, score: str, prefix: Optional[int] = None) -> Band:
        lowers, uppers = self.score_bounds(score)
        n = len(self.pairs) if prefix is None else int(prefix)
        return normal_mixture_band(lowers, uppers, n, alpha_gate=self.alpha_gate,
                                   rho=self.rho, name=score)

    def look(self, label: str = "") -> LookResult:
        """One evaluation trigger on the CURRENT FULL ENROLLED PREFIX."""
        n = len(self.pairs)
        h_band = self.band("hierarchy")
        s_band = self.band("success")
        decision = decide(h_band, s_band, delta=self.delta, n_min=self.n_min)
        result = LookResult(
            label=label or f"look{len(self.looks)}",
            n_enrolled=n, hierarchy=h_band, success=s_band, decision=decision,
            n_certified=sum(1 for p in self.pairs if p.hierarchy.certified),
            n_point_resolved=sum(1 for p in self.pairs if p.hierarchy.resolved),
            switched=self.switched)
        self.looks.append(result)
        if self.record_history:
            snapshot = {p.pair_id: (p.hierarchy, p.success) for p in self.pairs}
            self.history.append((result.label, n, snapshot))
        return result

    # -- snapshots -----------------------------------------------------------
    def state_signature(self) -> Tuple:
        """A total, order-independent snapshot used by the idempotence fixtures."""
        pairs = tuple(
            (p.position, p.pair_id, p.coin, p.slot_first, p.slot_second,
             p.hierarchy.as_tuple(), p.success.as_tuple())
            for p in self.pairs)
        episodes = tuple(
            (slot, e.success_lo, e.success_hi, e.cost_lo, e.cost_hi, e.final,
             e.cost_cap)
            for slot, e in sorted(self.episodes.items(), key=lambda kv: str(kv[0])))
        return (pairs, episodes, self.switched, self.switch_position,
                tuple(self.followup_arrivals))

    def resolved_scores(self, score: str) -> List[Optional[float]]:
        out: List[Optional[float]] = []
        for p in self.pairs:
            enc = p.enclosure(score)
            out.append(enc.lo if enc.certified else None)
        return out

    def audit_containment(self) -> List[str]:
        """Check every recorded look against the ultimately certified scores.

        Returns a list of defect strings; empty means the audit passed.  Needs
        ``record_history=True``.
        """
        if not self.record_history:
            raise ValidationError("audit_containment() needs record_history=True")
        defects: List[str] = []
        finals = {p.pair_id: {s: (p.enclosure(s).lo if p.enclosure(s).certified else None)
                              for s in SCORE_NAMES}
                  for p in self.pairs}
        for label, n, snapshot in self.history:
            for pair_id, (h_enc, s_enc) in snapshot.items():
                for score, enc in (("hierarchy", h_enc), ("success", s_enc)):
                    final = finals[pair_id][score]
                    if final is None:
                        continue
                    if not enc.contains(final):
                        defects.append(
                            f"{label}: pair {pair_id!r} {score} final {final} "
                            f"outside prior bound [{enc.lo}, {enc.hi}]")
        return defects
