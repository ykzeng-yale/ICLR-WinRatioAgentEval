"""Enclosure arithmetic for the live_ab prospective A/B trial (G3, statistical core part 1).

Normative sources: protocol_FINAL.md sections 6.1, 6.2, 6.3, 7.5 (enclosures) and
ARCHITECTURE_FINAL.md section 3.7 (signatures).

Every public function here is [pure]: no I/O, no clock, no randomness, no global mutation.

The one rule that governs the whole file: an enclosure is a set of LOGICALLY FEASIBLE
completions, never a prediction.  It starts at [-1, 1], it is narrowed only by enumerating
feasible completions, it never widens, and it collapses to a point only on a valid final-score
certificate (protocol 7.5 item 1) -- which is either "both episodes revealed with complete finite
outcomes" or "the enumeration of 7.5 item 5 leaves exactly one feasible value".  EXACTNESS SCOPE,
CORRECTED 2026-09-21: "exactly one feasible value" describes THIS MODULE'S declared operational
policy, which is epsilon-conservative by design (CERTIFICATE_EPS) and deliberately retained as such
by the root's 04:53 disposition.  It does NOT claim that the enclosure equals the mathematically
exact feasible set at every state: at the certificate boundaries it is strictly wider, which the
separate ideal-enclosure oracle diagnostic measures and reports.  Conservative containment, not
exactness, is what this module guarantees.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

# --------------------------------------------------------------------------------------------
# Exception taxonomy.
#
# lab_common (G1) owns the taxonomy.  It is imported when it exists so that every module raises
# the *same* class objects; the fallback below exists only so that this module and its tests can
# be developed and run before G1 lands.  `_LAB_COMMON_PRESENT` records which happened, and
# tests_lab_stats asserts the taxonomy is the shared one whenever lab_common is importable.
# --------------------------------------------------------------------------------------------
try:  # pragma: no cover - exercised both ways depending on the tree state
    from lab_common import EnclosureError, FrozenMismatch, LabError, MonitorError

    _LAB_COMMON_PRESENT = True
except ImportError:  # pragma: no cover
    _LAB_COMMON_PRESENT = False

    class LabError(Exception):
        """Root of the live_ab exception tree (local stand-in for lab_common.LabError)."""

    class FrozenMismatch(LabError):
        """A frozen value differs from what the freeze bundle fixed."""

    class EnclosureError(LabError):
        """An enclosure widened, or is empty, or is outside [-1, 1]."""

    class MonitorError(LabError):
        """A monitor invariant was violated."""


try:  # winstats lives in src/ and is a READ-ONLY reference; it is imported, never copied.
    import winstats
except ImportError:  # pragma: no cover - depends on how the test runner set sys.path
    _SRC_DIR = Path(__file__).resolve().parents[2] / "src"
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))
    import winstats


__all__ = [
    "TIER_NAMES",
    "ARMS",
    "Enclosure",
    "EpisodeView",
    "PairEnclosure",
    "tiers_from_config",
    "outcome_vector",
    "final_scores",
    "certified_elapsed",
    "success_enclosure",
    "hierarchy_enclosure",
    "pair_enclosure",
    "assert_monotone",
    "EnclosureError",
    "FrozenMismatch",
    "LabError",
    "MonitorError",
]


TIER_NAMES: tuple[str, ...] = ("success", "latency_s")
# TWO tiers, identical for all four trials (protocol 6.2).  `completion_tokens` is RECORDED and
# NEVER SCORED: it is not a tier, there is no third tier anywhere, and T3 uses the SAME kernel as
# T1/T2/T4.  The v2 three-tier hierarchy at relative tolerance 0.10 is superseded (audit B1).

ARMS: tuple[str, str] = ("incumbent", "candidate")

# The frozen hierarchy, exactly as protocol 6.2 and ARCHITECTURE_FINAL.md section 6.1 write it.
_FROZEN_HIERARCHY: tuple[dict, ...] = (
    {
        "name": "success",
        "field": "success",
        "higher_better": True,
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.0,
    },
    {
        "name": "cost",
        "field": "latency_s",
        "higher_better": False,
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.05,
    },
)

# protocol 7.5 item 5 / config 'enclosure.cost_certificate': (1 - tol) * ell > L_r + 1e-9.
# The SAME epsilon guards the reverse certificate `ell > (1 - tol) * L_r + 1e-9` (protocol 7.5
# item 5, completed under COORDINATOR_DECISIONS revision 12 ruling 54).  Both are one-sided: each
# fires only when its exclusion holds with a margin of `eps`, so a float rounding error smaller
# than `eps` can never forge either.  Neither constant changes: `tol` is 0.05, the certificate
# constant is 0.95 = 1 - tol, and `eps` is 1e-9.
CERTIFICATE_EPS: float = 1e-9


# --------------------------------------------------------------------------------------------
# Enclosure
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Enclosure:
    """A closed interval of feasible values of one pair score, always inside [-1, 1]."""

    lo: float
    hi: float

    def __post_init__(self) -> None:
        """Raise EnclosureError unless -1.0 <= lo <= hi <= 1.0 and both are finite."""
        lo, hi = self.lo, self.hi
        if isinstance(lo, bool) or isinstance(hi, bool):
            raise EnclosureError("enclosure endpoints must be real numbers, not bool")
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            raise EnclosureError("enclosure endpoints must be real numbers")
        lo = float(lo)
        hi = float(hi)
        if lo != lo or hi != hi or lo in (float("inf"), float("-inf")) or hi in (float("inf"), float("-inf")):
            raise EnclosureError("enclosure endpoints must be finite")
        if not (-1.0 <= lo <= hi <= 1.0):
            raise EnclosureError(f"enclosure [{lo!r}, {hi!r}] is empty or outside [-1, 1]")
        object.__setattr__(self, "lo", lo)
        object.__setattr__(self, "hi", hi)

    def narrows_to(self, other: "Enclosure", *, tol: float = 1e-12) -> bool:
        """[pure] True iff other.lo >= self.lo - tol and other.hi <= self.hi + tol."""
        return other.lo >= self.lo - tol and other.hi <= self.hi + tol

    def contains(self, x: float, *, tol: float = 1e-12) -> bool:
        """[pure] True iff x lies in [lo - tol, hi + tol]."""
        return self.lo - tol <= float(x) <= self.hi + tol

    def is_point(self, *, tol: float = 0.0) -> bool:
        """[pure] True iff the enclosure has collapsed to a single value."""
        return self.hi - self.lo <= tol

    @staticmethod
    def full() -> "Enclosure":
        """[pure] The starting enclosure of every score of every pair (protocol 7.5 item 1)."""
        return Enclosure(-1.0, 1.0)


# --------------------------------------------------------------------------------------------
# Episode and pair views
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class EpisodeView:
    """What is known about ONE episode of a pair at a look. Either revealed or pending.

    A terminal failure (worker died, hard cap, interrupted) is a REVEAL, not a pending state:
    success = 0, latency_s = ell, completion_tokens = tokens_known (protocol 6.4, ARCHITECTURE
    3.7).  That is why `assert_monotone` can never fail on a terminal failure.
    """

    arm: Literal["incumbent", "candidate"]
    revealed: bool
    success: int | None  # 0/1 when revealed, None when pending
    latency_s: float | None  # exact when revealed
    completion_tokens: int | None  # exact when revealed
    ell: float  # certified elapsed LOWER bound (0.0 when nothing was spooled)
    tokens_known: int  # completion tokens already receipted (lower bound)

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise EnclosureError(f"unknown arm {self.arm!r}")
        if not isinstance(self.revealed, bool):
            raise EnclosureError("revealed must be a bool")
        if isinstance(self.ell, bool) or not isinstance(self.ell, (int, float)):
            raise EnclosureError("ell must be a real number")
        ell = float(self.ell)
        if ell != ell or ell in (float("inf"), float("-inf")) or ell < 0.0:
            raise EnclosureError("ell must be finite and nonnegative")
        object.__setattr__(self, "ell", ell)
        if isinstance(self.tokens_known, bool) or not isinstance(self.tokens_known, int):
            raise EnclosureError("tokens_known must be an int")
        if self.tokens_known < 0:
            raise EnclosureError("tokens_known must be nonnegative")
        if self.revealed:
            if isinstance(self.success, bool) or self.success not in (0, 1):
                raise EnclosureError("a revealed episode needs success in {0, 1}")
            if isinstance(self.latency_s, bool) or not isinstance(self.latency_s, (int, float)):
                raise EnclosureError("a revealed episode needs a real latency_s")
            lat = float(self.latency_s)
            if lat != lat or lat in (float("inf"), float("-inf")) or lat < 0.0:
                raise EnclosureError("latency_s must be finite and nonnegative")
            object.__setattr__(self, "latency_s", lat)
            if isinstance(self.completion_tokens, bool) or not isinstance(self.completion_tokens, int):
                raise EnclosureError("a revealed episode needs an int completion_tokens")
            if self.completion_tokens < 0:
                raise EnclosureError("completion_tokens must be nonnegative")
        else:
            if self.success is not None or self.latency_s is not None or self.completion_tokens is not None:
                raise EnclosureError("a pending episode carries no outcome fields")

    @staticmethod
    def pending(arm: str, *, ell: float = 0.0, tokens_known: int = 0) -> "EpisodeView":
        """[pure] A not-yet-revealed episode with its certified lower bounds."""
        return EpisodeView(
            arm=arm,  # type: ignore[arg-type]
            revealed=False,
            success=None,
            latency_s=None,
            completion_tokens=None,
            ell=ell,
            tokens_known=tokens_known,
        )

    @staticmethod
    def reveal(arm: str, success: int, latency_s: float, completion_tokens: int,
               *, ell: float | None = None, tokens_known: int | None = None) -> "EpisodeView":
        """[pure] A revealed episode.  `ell` defaults to latency_s, `tokens_known` to the tokens."""
        return EpisodeView(
            arm=arm,  # type: ignore[arg-type]
            revealed=True,
            success=int(success),
            latency_s=float(latency_s),
            completion_tokens=int(completion_tokens),
            ell=float(latency_s) if ell is None else float(ell),
            tokens_known=int(completion_tokens) if tokens_known is None else int(tokens_known),
        )


@dataclass(frozen=True)
class PairEnclosure:
    """The two score enclosures of one enrolled pair at one look."""

    h: Enclosure  # hierarchy score Z_i, positive favours the candidate
    s: Enclosure  # success difference D_i = s_candidate - s_incumbent
    collapsed: bool  # True iff lo == hi for BOTH scores
    decisive_tier: int  # 0 or 1 when a tier decided, -1 for a tie or while open

    def __post_init__(self) -> None:
        if not isinstance(self.h, Enclosure) or not isinstance(self.s, Enclosure):
            raise EnclosureError("a PairEnclosure carries two Enclosures")
        if not isinstance(self.collapsed, bool):
            raise EnclosureError("collapsed must be a bool")
        if isinstance(self.decisive_tier, bool) or self.decisive_tier not in (-1, 0, 1):
            raise EnclosureError("decisive_tier must be -1, 0 or 1")
        # `collapsed` drives the horizon condition, so it may never disagree with the endpoints.
        if self.collapsed != (self.h.is_point() and self.s.is_point()):
            raise EnclosureError(
                "collapsed must be true exactly when both scores are points"
            )

    @staticmethod
    def full() -> "PairEnclosure":
        """[pure] A freshly enrolled pair: [-1, 1] in both scores."""
        return PairEnclosure(Enclosure.full(), Enclosure.full(), False, -1)


# --------------------------------------------------------------------------------------------
# The frozen hierarchy
# --------------------------------------------------------------------------------------------
def _frozen_tiers() -> list[winstats.Tier]:
    return [
        winstats.Tier("success"),
        winstats.Tier("cost", higher_better=False, relative_tolerance=0.05),
    ]


def tiers_from_config(cfg: dict) -> list[winstats.Tier]:
    """[pure] Build the frozen hierarchy from cfg['hierarchy'] (protocol 6.2, Appendix B).

    The same two-row array for ALL FOUR trials.  There is no per-trial tier count, no `n_tiers`
    key and no token tier.  Raises FrozenMismatch if cfg['hierarchy'] is not exactly the frozen
    two-row array (audit B1).
    """
    if not isinstance(cfg, dict):
        raise FrozenMismatch("config must be an object")
    if "n_tiers" in cfg:
        raise FrozenMismatch("config carries an 'n_tiers' key; the hierarchy is frozen at two tiers")
    monitor = cfg.get("monitor")
    if isinstance(monitor, dict) and "n_tiers" in monitor:
        raise FrozenMismatch("config.monitor carries an 'n_tiers' key")
    rows = cfg.get("hierarchy")
    if not isinstance(rows, list):
        raise FrozenMismatch("config.hierarchy is missing or is not an array")
    if len(rows) != len(_FROZEN_HIERARCHY):
        raise FrozenMismatch(
            f"config.hierarchy has {len(rows)} rows; the frozen hierarchy has {len(_FROZEN_HIERARCHY)}"
        )
    for got, want in zip(rows, _FROZEN_HIERARCHY):
        if not isinstance(got, dict):
            raise FrozenMismatch("every hierarchy row must be an object")
        if "n_tiers" in got:
            raise FrozenMismatch("a hierarchy row carries an 'n_tiers' key")
        if set(got) != set(want):
            raise FrozenMismatch(
                f"hierarchy row keys {sorted(got)} differ from the frozen keys {sorted(want)}"
            )
        for key, wanted in want.items():
            value = got[key]
            if key == "higher_better":
                if not isinstance(value, bool) or value is not wanted:
                    raise FrozenMismatch(f"hierarchy row {got.get('name')!r}: {key} is not {wanted!r}")
            elif key in ("absolute_tolerance", "relative_tolerance"):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) != wanted:
                    raise FrozenMismatch(
                        f"hierarchy row {got.get('name')!r}: {key} is {value!r}, frozen at {wanted!r}"
                    )
            else:
                if value != wanted:
                    raise FrozenMismatch(
                        f"hierarchy row {got.get('name')!r}: {key} is {value!r}, frozen at {wanted!r}"
                    )
    rule = cfg.get("eligibility_rule")
    if rule is not None and rule != "lower_tiers_require_both_success":
        raise FrozenMismatch(f"eligibility_rule is {rule!r}, frozen at 'lower_tiers_require_both_success'")
    tie = cfg.get("tie_rule")
    if tie is not None and tie != "strict_gt_tolerance_so_exact_equality_is_a_tie":
        raise FrozenMismatch(f"tie_rule is {tie!r}, frozen at the strict-'>' tie rule")
    return _frozen_tiers()


def _check_tiers(tiers: Sequence[winstats.Tier]) -> float:
    """[pure] Validate the frozen two-tier hierarchy and return the cost relative tolerance."""
    if len(tiers) != 2:
        raise FrozenMismatch(f"the hierarchy is frozen at two tiers; got {len(tiers)}")
    t0, t1 = tiers
    if t0.name != "success" or t0.higher_better is not True:
        raise FrozenMismatch("tier 0 must be Tier('success') with higher_better=True")
    if t0.absolute_tolerance != 0.0 or t0.relative_tolerance != 0.0:
        raise FrozenMismatch("tier 0 must have zero tolerances")
    if t1.name != "cost" or t1.higher_better is not False:
        raise FrozenMismatch("tier 1 must be Tier('cost') with higher_better=False")
    if t1.absolute_tolerance != 0.0:
        raise FrozenMismatch("tier 1 must have absolute_tolerance 0.0")
    if t1.relative_tolerance != 0.05:
        raise FrozenMismatch(
            f"tier 1 relative_tolerance is {t1.relative_tolerance!r}, frozen at 0.05 (the v2 0.10 is superseded)"
        )
    return float(t1.relative_tolerance)


# --------------------------------------------------------------------------------------------
# Outcomes and the collapse certificate
# --------------------------------------------------------------------------------------------
def outcome_vector(view: EpisodeView, names: Sequence[str]) -> list[float]:
    """[pure] Revealed episode -> [success, latency_s] as floats, in TIER_NAMES order.

    `completion_tokens` is recorded on the view and in the record file but is NEVER passed to
    `compare` (protocol 6.1, 6.2).  Raises EnclosureError if the view is pending, because
    winstats.compare requires complete finite outcomes (src/winstats.py:34).
    """
    if not view.revealed:
        raise EnclosureError("compare() is never fed a partial outcome (protocol 7.5 item 7)")
    out: list[float] = []
    for name in names:
        if name == "success":
            out.append(float(view.success))  # type: ignore[arg-type]
        elif name == "latency_s":
            out.append(float(view.latency_s))  # type: ignore[arg-type]
        else:
            raise EnclosureError(
                f"{name!r} is not a scored field; the frozen fields are {TIER_NAMES!r}"
            )
    return out


def final_scores(candidate: EpisodeView, incumbent: EpisodeView,
                 tiers: list[winstats.Tier]) -> tuple[int, int, int]:
    """[pure] THE COLLAPSE CERTIFICATE.  Both views must be revealed.

    Returns (z, decisive_tier, d).  Direction is fixed by argument order: +1 favours the
    candidate.  Joint failure is a tie (eligibility False on the lower tiers).  Exact threshold
    equality is a tie (winstats.compare uses a strict '>').
    """
    _check_tiers(tiers)
    if candidate.arm != "candidate" or incumbent.arm != "incumbent":
        raise EnclosureError("final_scores(candidate, incumbent) takes the arms in that order")
    if not candidate.revealed or not incumbent.revealed:
        raise EnclosureError("final_scores needs both episodes revealed")
    both_succeeded = bool(candidate.success) and bool(incumbent.success)
    eligible = [True, both_succeeded]
    z_arr, tier_arr = winstats.compare(
        outcome_vector(candidate, TIER_NAMES),
        outcome_vector(incumbent, TIER_NAMES),
        tiers,
        eligible,
    )
    z = int(z_arr)
    tier = int(tier_arr)
    d = int(candidate.success) - int(incumbent.success)  # type: ignore[arg-type]
    return z, tier, d


def certified_elapsed(call_stamps: Sequence[tuple[int, int]]) -> float:
    """[pure] ell = max over spooled stamps of (t_e - t_c1) in seconds.

    `t_c1` is the worker's monotonic stamp at entry into the first chat() call and `t_e` runs over
    every send and receive stamp.  Input is [(t_c1_ns, t_e_ns), ...] already extracted from the
    chain.  Returns 0.0 for an empty sequence (critic N5: a worker that died before its first
    request).

    A stamp with t_e < t_c1 is a clock anomaly, not a smaller bound: it is refused rather than
    silently repaired, because `ell` is decision-defining (a false `ell` can forge a certificate).
    """
    best_ns = 0
    for item in call_stamps:
        t_c1, t_e = item
        if isinstance(t_c1, bool) or isinstance(t_e, bool) or not isinstance(t_c1, int) or not isinstance(t_e, int):
            raise EnclosureError("call stamps must be integer nanosecond values")
        delta = t_e - t_c1
        if delta < 0:
            raise EnclosureError(
                f"monotonic stamp {t_e} precedes the first-call stamp {t_c1}; refusing to certify"
            )
        if delta > best_ns:
            best_ns = delta
    return best_ns / 1_000_000_000


# --------------------------------------------------------------------------------------------
# The two enclosures
# --------------------------------------------------------------------------------------------
def _success_bounds(view: EpisodeView) -> tuple[float, float]:
    """[pure] (s_low, s_high).  'Absence of failure is not success' (protocol 7.5 item 3)."""
    if view.revealed:
        s = float(view.success)  # type: ignore[arg-type]
        return s, s
    return 0.0, 1.0


def success_enclosure(candidate: EpisodeView, incumbent: EpisodeView) -> Enclosure:
    """[pure] Root guidance 5, literally:

        lo = s_cand_low - s_inc_high ;  hi = s_cand_high - s_inc_low

    with s_low = s_high = success for a revealed episode and (0, 1) for a pending one.
    """
    if candidate.arm != "candidate" or incumbent.arm != "incumbent":
        raise EnclosureError("success_enclosure(candidate, incumbent) takes the arms in that order")
    a_low, a_high = _success_bounds(candidate)
    b_low, b_high = _success_bounds(incumbent)
    return Enclosure(a_low - b_high, a_high - b_low)


def hierarchy_enclosure(candidate: EpisodeView, incumbent: EpisodeView,
                        tiers: list[winstats.Tier]) -> Enclosure:
    """[pure] Root guidance 5: start at [-1, 1] and narrow ONLY by enumerating feasible
    completions.  The closed list of cases is protocol 7.5 item 5; the result is
    [min(feasible z), max(feasible z)].  No other narrowing exists.

    The enumeration is over EVERY completion of the pending episode: its success in {0, 1} and,
    when it succeeds, every final cost x in [ell, inf).  The single fact a pending state supplies
    is protocol 7.5 item 4's -- a certified elapsed cost CAN ONLY GROW, so x >= ell and nothing
    else is known.  Everything below is derived from that and from the frozen hierarchy (success
    then cost; cost eligible only on joint success; a tier decides iff |a - b| > tol * max(|a|,
    |b|) STRICTLY; joint failure is a tie).

    The two cost thresholds, derived once.  With both episodes successful and the partner
    finishing at x >= 0 against the revealed latency L_r >= 0:
      * the REVEALED episode wins tier 1  iff  x - L_r > tol * max(x, L_r)  iff  x > L_r/(1 - tol)
      * the PENDING partner wins tier 1   iff  L_r - x > tol * max(x, L_r)  iff  x < (1 - tol)*L_r
      * otherwise (1 - tol)*L_r <= x <= L_r/(1 - tol) and tier 1 ties, so the pair ties.

      (a) both revealed  -> [z, z] with z = final_scores(...)[0]
      (b) neither revealed -> [-1, 1]; nothing is excluded, because on joint success every cost
          ordering is still attainable and either episode may still fail
      (c) one revealed (arm r, sgn = +1 if r is the candidate else -1), partner pending with
          certified ell:
            * s_r == 0: feasible = {-sgn, 0}.  Tier 1 is not eligible in any completion (it needs
              JOINT success and the revealed episode already failed), so `ell` is irrelevant here.
            * s_r == 1, FORWARD certificate (1 - tol) * ell > L_r + 1e-9: every feasible x >= ell
              exceeds L_r/(1 - tol), so the revealed episode wins tier 1; and if the partner fails
              it wins tier 0.  feasible = {+sgn}: the score is certain and the enclosure collapses.
            * s_r == 1, REVERSE certificate ell > (1 - tol) * L_r + 1e-9 (and no forward one): a
              partner win would need x < (1 - tol) * L_r <= ell <= x, which is impossible, so the
              PARTNER'S WIN IS INFEASIBLE and that value leaves the enclosure.
              feasible = {0, +sgn} -- a narrowing, not a collapse.
            * s_r == 1, neither certificate: x = ell itself gives a partner win, a cost inside
              [(1 - tol)*L_r, L_r/(1 - tol)] gives a tie and a large cost gives a revealed win.
              feasible = {-1, 0, +1}.

    Every feasible set above is a CONTIGUOUS run of {-1, 0, +1}, so [min, max] equals the feasible
    set exactly and is never a relaxation of it.  (The one non-contiguous set {-sgn, +sgn} cannot
    arise: a tie is infeasible only when ell > L_r/(1 - tol), which is the forward certificate,
    and that already excludes the partner's win.)

    At the frozen tolerance 0.05 the forward certificate constant is 0.95 (protocol 14.3 names it)
    and the reverse certificate reads `ell > 0.95 * L_r + 1e-9`.  No certificate is ever derived
    from tokens: tokens are not a tier at all.
    """
    tol = _check_tiers(tiers)
    if candidate.arm != "candidate" or incumbent.arm != "incumbent":
        raise EnclosureError("hierarchy_enclosure(candidate, incumbent) takes the arms in that order")

    if candidate.revealed and incumbent.revealed:  # (a)
        z = float(final_scores(candidate, incumbent, tiers)[0])
        return Enclosure(z, z)
    if not candidate.revealed and not incumbent.revealed:  # (b)
        return Enclosure.full()

    # (c) exactly one revealed.
    if candidate.revealed:
        revealed, partner, sgn = candidate, incumbent, 1.0
    else:
        revealed, partner, sgn = incumbent, candidate, -1.0

    s_r = int(revealed.success)  # type: ignore[arg-type]
    l_r = float(revealed.latency_s)  # type: ignore[arg-type]
    ell = float(partner.ell)

    if s_r == 0:
        # The partner either succeeds (it wins at tier 0: z = -sgn) or fails (joint failure: tie).
        # Tier 1 is never reached, so `ell` cannot narrow this and is deliberately not consulted.
        feasible = {-sgn, 0.0}
    else:
        # The partner fails -> the revealed episode wins tier 0 (z = +sgn).
        # The partner succeeds -> both succeed and tier 1 decides on latency with relative
        # tolerance `tol`; the partner's final latency x >= ell.
        if (1.0 - tol) * ell > l_r + CERTIFICATE_EPS:
            # FORWARD certificate.  For every feasible x >= ell: x - L_r > tol * x =
            # tol * max(x, L_r), so the revealed episode wins in EVERY feasible completion and the
            # SCORE is certain: exactly one feasible value, sgn.  The TIER is not certain, and
            # this certificate does not claim it is: the partner succeeding decides the pair at
            # tier 1 (latency), the partner failing decides it at tier 0 (success).
            # `pair_enclosure` therefore keeps decisive_tier = -1 until both episodes are
            # revealed (statistics review section 4).
            feasible = {sgn}
        elif ell > (1.0 - tol) * l_r + CERTIFICATE_EPS:
            # REVERSE certificate.  The partner can only win tier 1 at a final cost
            # x < (1 - tol) * L_r, and it has ALREADY spent ell >= (1 - tol) * L_r, which it can
            # never un-spend (item 4).  Its win is therefore infeasible from this state and -sgn
            # leaves the enclosure; a tie and a revealed win both remain feasible, so this
            # NARROWS and does not collapse.  Without this branch the rule would answer [-1, 1]
            # to a state whose own certified evidence has already excluded one of the three
            # values -- the incompleteness of the superseded two-case text (protocol 7.5a).
            feasible = {0.0, sgn}
        else:
            feasible = {-1.0, 0.0, 1.0}
    return Enclosure(min(feasible), max(feasible))


def pair_enclosure(candidate: EpisodeView, incumbent: EpisodeView,
                   tiers: list[winstats.Tier]) -> PairEnclosure:
    """[pure] Both score enclosures of one pair, plus the collapse flag and the decisive tier.

    `collapsed` is True iff lo == hi for BOTH scores, which (see `success_enclosure`) happens
    exactly when both episodes are revealed: a pending episode always leaves the success
    enclosure at least one unit wide.  The FORWARD cost certificate therefore collapses `h` while
    `s` stays open, and `collapsed` stays False -- which is what ARCHITECTURE 3.7's worked
    invariant says ("the success enclosure of such a pair is still open until both episodes are
    revealed").  The REVERSE certificate moves one endpoint of `h` and leaves it open, so it is a
    narrowing and `collapsed` stays False for that reason too.

    `decisive_tier` is the tier that decided the point value, and -1 for a tie or while the pair
    is open.  Under a cost certificate the VALUE of z is certain but the TIER is not (the partner
    failing would decide it at tier 0, the partner succeeding at tier 1), so it is -1 there.
    """
    h = hierarchy_enclosure(candidate, incumbent, tiers)
    s = success_enclosure(candidate, incumbent)
    collapsed = h.is_point() and s.is_point()
    tier = -1
    if candidate.revealed and incumbent.revealed:
        tier = final_scores(candidate, incumbent, tiers)[1]
    return PairEnclosure(h=h, s=s, collapsed=collapsed, decisive_tier=tier)


def assert_monotone(old: PairEnclosure, new: PairEnclosure) -> None:
    """[pure] Raise EnclosureError unless old.h.narrows_to(new.h) and old.s.narrows_to(new.s).

    Called by lab_monitor on every update and by lab_verify_log on every replayed update.
    """
    if not old.h.narrows_to(new.h):
        raise EnclosureError(
            f"hierarchy enclosure widened: [{old.h.lo!r}, {old.h.hi!r}] -> [{new.h.lo!r}, {new.h.hi!r}]"
        )
    if not old.s.narrows_to(new.s):
        raise EnclosureError(
            f"success enclosure widened: [{old.s.lo!r}, {old.s.hi!r}] -> [{new.s.lo!r}, {new.s.hi!r}]"
        )
    if old.collapsed and not new.collapsed:
        raise EnclosureError("a collapsed pair may never re-open")
