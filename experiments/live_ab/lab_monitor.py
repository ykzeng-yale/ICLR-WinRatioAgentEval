"""The live monitor for the live_ab prospective A/B trial (G3, statistical core part 2).

Normative sources: protocol_FINAL.md sections 7.3, 8.1-8.4, 8.8 and ARCHITECTURE_FINAL.md
section 3.8 (signatures), section 4.4 T19 (the `monitor_update` body) and section 7.1 (the state
machine that calls this module).

No I/O, no clock, no randomness.  The decision is evaluated on the CURRENT FULL ENROLLED PREFIX
and on nothing else: no prefix envelope, no maximisation of lower bounds over prefixes, no
retained crossing, no running intersection of bands across looks, no substitution of the number
of completed pairs for n (protocol 8.2, "Prohibited, by name").

Wealth-process read-outs are deliberately absent from this module: the decision rule is the
normal-mixture band and nothing else (protocol 8.8 item 5, PG-16).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from lab_enclosure import (
    ARMS,
    EnclosureError,
    Enclosure,
    EpisodeView,
    FrozenMismatch,
    MonitorError,
    PairEnclosure,
    assert_monotone,
    certified_elapsed,
    pair_enclosure,
    tiers_from_config,
)

try:  # winstats lives in src/ and is a READ-ONLY reference; it is imported, never copied.
    import winstats
except ImportError:  # pragma: no cover - depends on how the test runner set sys.path
    _SRC_DIR = Path(__file__).resolve().parents[2] / "src"
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))
    import winstats


__all__ = [
    "RULE_ID",
    "MonitorConfig",
    "Band",
    "MonitorState",
    "Decision",
    "band",
    "decide",
    "replay",
    "radius_table",
    # re-exported from the lab_common taxonomy via lab_enclosure, so that a caller catching a
    # monitor failure never has to guess which module owns the class
    "EnclosureError",
    "FrozenMismatch",
    "MonitorError",
]


RULE_ID: str = "nm_guarded_v3"

#: The closed set of event types `replay` consumes (ARCHITECTURE 3.8).  Everything else -- every
#: metrics_scrape, server_* and anchor* event -- produces NO look.
CONSUMED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "pair_enrolled",
        "coin_drawn",
        "arm_assigned_by_decision",
        "llm_request",
        "llm_response",
        "llm_error",
        "episode_revealed",
        "decision",
        "traffic_switch",
    }
)

#: The closed set of look triggers (protocol 8.3, `monitor_update.trigger` enum T19).
TRIGGERS: tuple[str, ...] = ("enroll", "reveal", "call", "resume", "drain")

#: protocol 8.8 item 1: exploratory margins, computed into the read-outs and structurally
#: incapable of deciding anything.  They are never passed to `decide`.
EXPLORATORY_MARGINS: tuple[float, float] = (0.10, 0.15)


# --------------------------------------------------------------------------------------------
# Frozen configuration
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class MonitorConfig:
    """The five frozen statistical fields plus the clip, with NO DEFAULTS on the five (audit m9).

    A config that fails to load must raise, never silently install a horizon, a level or a
    margin.
    """

    alpha_gate: float  # 0.00625 = program 0.05 / 4 trials / 2 scores
    rho: float  # 100.0
    delta: float  # 0.03
    n_min: int  # 100
    n_max: int  # N_P from the roster (<= 568); the horizon
    clip_lo: float = -1.0
    clip_hi: float = 1.0

    def __post_init__(self) -> None:
        for name in ("alpha_gate", "rho", "delta", "clip_lo", "clip_hi"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FrozenMismatch(f"monitor.{name} must be a real number")
            value = float(value)
            if value != value or value in (float("inf"), float("-inf")):
                raise FrozenMismatch(f"monitor.{name} must be finite")
            object.__setattr__(self, name, value)
        for name in ("n_min", "n_max"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise FrozenMismatch(f"monitor.{name} must be an int")
        if not 0.0 < self.alpha_gate < 1.0:
            raise FrozenMismatch("alpha_gate must lie in (0, 1)")
        if self.rho <= 0.0:
            raise FrozenMismatch("rho must be positive")
        if not 0.0 <= self.delta < 1.0:
            raise FrozenMismatch("delta must lie in [0, 1)")
        if self.n_min < 1:
            raise FrozenMismatch("n_min must be at least 1")
        if self.n_max < 1:
            raise FrozenMismatch("n_max must be at least 1")
        # The clip is the KNOWN RANGE of the scores, not a tunable window.  Intersecting the
        # band with a range is licensed by thm:normal_cs (`paper/theory.tex:303`) ONLY when
        # that range is known to contain the target; both scores live in [-1, 1] and no
        # narrower range is known here.  A narrower clip does not merely tighten the display:
        # it can manufacture a positive lower endpoint out of zero-score data and fire a FALSE
        # deploy (witness: clip [0.2, 1.0] at 100 zero-score pairs reports L_h = L_s = 0.2 and
        # decides `deploy_candidate`).  So the contract the error message states is enforced
        # exactly, rather than as an ordering check (statistics review section 3).
        if (self.clip_lo, self.clip_hi) != (-1.0, 1.0):
            raise FrozenMismatch(
                "the clip is frozen at [-1.0, 1.0]; it is the known score range, not a "
                f"tunable window (got [{self.clip_lo!r}, {self.clip_hi!r}])"
            )

    @staticmethod
    def from_config(cfg: dict, trial: str) -> "MonitorConfig":
        """Read cfg['monitor'] and cfg['roster']['n_pairs'].

        Raises FrozenMismatch if monitor.n_max is null at run time, if it differs from
        roster.n_pairs, or if any of the five frozen fields is absent.
        """
        if not isinstance(cfg, dict):
            raise FrozenMismatch("config must be an object")
        monitor = cfg.get("monitor")
        if not isinstance(monitor, dict):
            raise FrozenMismatch("config.monitor is missing")
        roster = cfg.get("roster")
        if not isinstance(roster, dict):
            raise FrozenMismatch("config.roster is missing")
        trials = cfg.get("trials")
        if isinstance(trials, dict) and trial not in trials:
            raise FrozenMismatch(f"trial {trial!r} is not one of the frozen trials {sorted(trials)}")

        for key in ("alpha_gate", "rho", "delta", "n_min", "n_max"):
            if key not in monitor:
                raise FrozenMismatch(f"monitor.{key} is absent; the five frozen fields have no defaults")
            if monitor[key] is None:
                raise FrozenMismatch(f"monitor.{key} is null at run time")

        n_pairs = roster.get("n_pairs")
        if n_pairs is None:
            raise FrozenMismatch("roster.n_pairs is null at run time")
        if monitor["n_max"] != n_pairs:
            raise FrozenMismatch(
                f"monitor.n_max ({monitor['n_max']!r}) differs from roster.n_pairs ({n_pairs!r})"
            )

        clip = monitor.get("clip", [-1.0, 1.0])
        if not isinstance(clip, (list, tuple)) or len(clip) != 2:
            raise FrozenMismatch("monitor.clip must be a two-element array")

        # Guard rails: every one of these keys, when present, is decision-defining and frozen.
        _require(monitor, "construction", "winstats.normal_mixture_radius")
        _require(monitor, "variance_process", "n")
        _require(monitor, "prefix", "current_full_enrolled")
        _require(monitor, "retention", False)
        _require(monitor, "running_intersection", False)
        _require(monitor, "prefix_envelope", False)
        _require(monitor, "maximize_over_prefixes", False)
        _require(monitor, "harm_tail", "hierarchy_upper_only")
        _require(monitor, "deploy_if", "L_h_gt_0_and_L_s_gt_minus_delta_at_same_prefix")
        _require(monitor, "harm_if", "U_h_lt_0")
        _require(monitor, "exploratory_margins_decide", False)
        _require(cfg, "rule_id", RULE_ID)
        if monitor.get("decision_order") is not None and list(monitor["decision_order"]) != [
            "harm_keep_incumbent",
            "deploy_candidate",
        ]:
            raise FrozenMismatch("monitor.decision_order is frozen at [harm_keep_incumbent, deploy_candidate]")

        return MonitorConfig(
            alpha_gate=monitor["alpha_gate"],
            rho=monitor["rho"],
            delta=monitor["delta"],
            n_min=monitor["n_min"],
            n_max=monitor["n_max"],
            clip_lo=clip[0],
            clip_hi=clip[1],
        )


def _require(obj: Mapping, key: str, frozen_value: object) -> None:
    """Raise FrozenMismatch when `obj[key]` is present and is not the frozen value."""
    if key not in obj:
        return
    value = obj[key]
    if isinstance(frozen_value, bool):
        if not isinstance(value, bool) or value is not frozen_value:
            raise FrozenMismatch(f"{key} is {value!r}, frozen at {frozen_value!r}")
    elif value != frozen_value:
        raise FrozenMismatch(f"{key} is {value!r}, frozen at {frozen_value!r}")


# --------------------------------------------------------------------------------------------
# The band
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Band:
    """One score's band at one look."""

    n: int
    radius: float
    s_lower: float  # the sums, before dividing
    s_upper: float
    lo: float  # L_j, already clipped
    hi: float  # U_j, already clipped


def band(n: int, s_lower: float, s_upper: float, mc: MonitorConfig) -> Band:
    """[pure] THE decision primitive.  Exactly the root's guidance, no variation:

        r  = winstats.normal_mixture_radius(n, alpha=mc.alpha_gate, rho=mc.rho, variance_process=n)
        lo = max(mc.clip_lo, s_lower / n - r)
        hi = min(mc.clip_hi, s_upper / n + r)

    `variance_process=n` is passed explicitly even though it equals the default, because the
    frozen call is what the protocol quotes (PG-19).  n >= 1 is required (MonitorError
    otherwise); at n == 0 the caller displays the full range [-1, 1] and does not decide.

    This function reads nothing but its arguments.  There is no band memory of any kind.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise MonitorError("n must be an int")
    if n < 1:
        raise MonitorError("band() requires n >= 1; at n == 0 the full range is displayed")
    for name, value in (("s_lower", s_lower), ("s_upper", s_upper)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MonitorError(f"{name} must be a real number")
        value = float(value)
        if value != value or value in (float("inf"), float("-inf")):
            raise MonitorError(f"{name} must be finite")
    s_lower = float(s_lower)
    s_upper = float(s_upper)
    if s_lower > s_upper:
        raise MonitorError(f"the summed enclosure [{s_lower!r}, {s_upper!r}] is empty")
    if s_lower < -n or s_upper > n:
        raise MonitorError(
            f"the summed enclosure [{s_lower!r}, {s_upper!r}] leaves [-n, n] at n = {n}"
        )
    r = float(winstats.normal_mixture_radius(n, alpha=mc.alpha_gate, rho=mc.rho, variance_process=n))
    lo = max(mc.clip_lo, s_lower / n - r)
    hi = min(mc.clip_hi, s_upper / n + r)
    return Band(n=n, radius=r, s_lower=s_lower, s_upper=s_upper, lo=lo, hi=hi)


# --------------------------------------------------------------------------------------------
# Monitor state
# --------------------------------------------------------------------------------------------
class MonitorState:
    """Enrollment-indexed, append-only in the enrollment dimension, updatable in place.

    Internally four parallel lists indexed by enrollment position 0..n-1 (`_lo_h`, `_hi_h`,
    `_lo_s`, `_hi_s`), plus `_collapsed` and `_tier`.  A pair occupies an immutable enrollment
    position from its enrollment to the end of the trial (protocol 7.3 item 1); a reveal-order
    event updates the enclosure at that position and nothing else (item 3).
    """

    def __init__(self, mc: MonitorConfig) -> None:
        if not isinstance(mc, MonitorConfig):
            raise MonitorError("MonitorState needs a MonitorConfig")
        self._mc = mc
        self._lo_h: list[float] = []
        self._hi_h: list[float] = []
        self._lo_s: list[float] = []
        self._hi_s: list[float] = []
        self._collapsed: list[bool] = []
        self._tier: list[int] = []

    # -- prefix ------------------------------------------------------------------------------
    @property
    def n(self) -> int:
        """The CURRENT FULL ENROLLED PREFIX N(t) (protocol 7.3 item 2)."""
        return len(self._lo_h)

    @property
    def config(self) -> MonitorConfig:
        return self._mc

    def _n_collapsed(self) -> int:
        return sum(1 for flag in self._collapsed if flag)

    def _all_collapsed(self) -> bool:
        return all(self._collapsed)

    def _completed_prefix(self) -> int:
        """The leading run of collapsed positions: the longest PREFIX of resolved pairs."""
        k = 0
        for flag in self._collapsed:
            if not flag:
                break
            k += 1
        return k

    def _at(self, pair: int) -> PairEnclosure:
        i = pair - 1
        return PairEnclosure(
            Enclosure(self._lo_h[i], self._hi_h[i]),
            Enclosure(self._lo_s[i], self._hi_s[i]),
            self._collapsed[i],
            self._tier[i],
        )

    # -- mutation ----------------------------------------------------------------------------
    def enroll(self, pair: int) -> None:
        """Append one position at [-1, 1] for both scores.

        Raises MonitorError unless pair == self.n + 1 (pairs are enrolled in order, never
        created out of order).
        """
        if isinstance(pair, bool) or not isinstance(pair, int):
            raise MonitorError("pair must be an int")
        if pair != self.n + 1:
            raise MonitorError(f"pair {pair} enrolled out of order at prefix {self.n}")
        if pair > self._mc.n_max:
            raise MonitorError(
                f"pair {pair} exceeds the frozen horizon n_max = {self._mc.n_max}"
            )
        self._lo_h.append(-1.0)
        self._hi_h.append(1.0)
        self._lo_s.append(-1.0)
        self._hi_s.append(1.0)
        self._collapsed.append(False)
        self._tier.append(-1)

    def update(self, pair: int, enc: PairEnclosure) -> None:
        """Replace the enclosure of an EXISTING enrollment position.

        Raises MonitorError if pair > self.n (a reveal never creates a pair) and EnclosureError
        if the enclosure widens.  Idempotent: applying the same enclosure twice changes nothing.
        """
        if isinstance(pair, bool) or not isinstance(pair, int):
            raise MonitorError("pair must be an int")
        if pair < 1:
            raise MonitorError(f"pair index {pair} is not a valid enrollment position")
        if pair > self.n:
            raise MonitorError(
                f"pair {pair} is not enrolled at prefix {self.n}; a reveal never creates a pair"
            )
        if not isinstance(enc, PairEnclosure):
            raise MonitorError("update needs a PairEnclosure")
        assert_monotone(self._at(pair), enc)
        i = pair - 1
        self._lo_h[i] = enc.h.lo
        self._hi_h[i] = enc.h.hi
        self._lo_s[i] = enc.s.lo
        self._hi_s[i] = enc.s.hi
        self._collapsed[i] = bool(enc.collapsed)
        self._tier[i] = int(enc.decisive_tier)

    # -- read-out ----------------------------------------------------------------------------
    def sums(self) -> tuple[float, float, float, float]:
        """[pure] (sum lower_h, sum upper_h, sum lower_s, sum upper_s) over the FULL prefix.

        math.fsum over the enrollment-ordered lists, recomputed from scratch at every look --
        never an incremental accumulator -- so that the live value and the replayed value are
        identical bit for bit whatever the order of the reveals.
        """
        return (
            math.fsum(self._lo_h),
            math.fsum(self._hi_h),
            math.fsum(self._lo_s),
            math.fsum(self._hi_s),
        )

    def bands(self) -> tuple[Band, Band] | None:
        """(band_h, band_s) at n = self.n, or None when n == 0."""
        n = self.n
        if n == 0:
            return None
        lo_h, hi_h, lo_s, hi_s = self.sums()
        return band(n, lo_h, hi_h, self._mc), band(n, lo_s, hi_s, self._mc)

    def _completed_prefix_bands(self) -> tuple[int, tuple[Band, Band] | None]:
        k = self._completed_prefix()
        if k == 0:
            return 0, None
        return k, (
            band(k, math.fsum(self._lo_h[:k]), math.fsum(self._hi_h[:k]), self._mc),
            band(k, math.fsum(self._lo_s[:k]), math.fsum(self._hi_s[:k]), self._mc),
        )

    def snapshot(self) -> dict:
        """JSON-ready dict for the `monitor_update` body (ARCHITECTURE 4.4 T19).

        The statistical fields only.  `trigger`, `pair_updated` and `pair_enclosure` are supplied
        by the caller that knows which event produced the look (`replay` fills them in); the
        orchestrator additionally attaches `shadow` (the reference rule of protocol 8.9) and
        `monitor_code_sha256`.  `readouts.s1_restricted` is null here because the monitor holds
        no stratum labels -- protocol 8.8 item 2 is computed by the results builder.
        """
        mc = self._mc
        n = self.n
        lo_h, hi_h, lo_s, hi_s = self.sums()
        if n == 0:
            # protocol 7.3 item 7: at n = 0 the full range is displayed and nothing is decided.
            return {
                "n": 0,
                "n_collapsed": 0,
                "sum_lower_h": 0.0,
                "sum_upper_h": 0.0,
                "sum_lower_s": 0.0,
                "sum_upper_s": 0.0,
                "radius": None,
                "L_h": mc.clip_lo,
                "U_h": mc.clip_hi,
                "L_s": mc.clip_lo,
                "U_s": mc.clip_hi,
                "flags": {
                    "n_min_ok": False,
                    "harm": False,
                    "deploy": False,
                    "success_guard_ok": False,
                },
                "readouts": {
                    "L_s_vs_010": mc.clip_lo + EXPLORATORY_MARGINS[0],
                    "L_s_vs_015": mc.clip_lo + EXPLORATORY_MARGINS[1],
                    "s1_restricted": None,
                    "completed_prefix": {
                        "n": 0,
                        "L_h": mc.clip_lo,
                        "U_h": mc.clip_hi,
                        "L_s": mc.clip_lo,
                        "U_s": mc.clip_hi,
                    },
                },
                "sums_fsum": True,
            }
        bh, bs = band(n, lo_h, hi_h, mc), band(n, lo_s, hi_s, mc)
        k, cbands = self._completed_prefix_bands()
        if cbands is None:
            completed = {
                "n": 0,
                "L_h": mc.clip_lo,
                "U_h": mc.clip_hi,
                "L_s": mc.clip_lo,
                "U_s": mc.clip_hi,
            }
        else:
            cbh, cbs = cbands
            completed = {
                "n": k,
                "L_h": cbh.lo,
                "U_h": cbh.hi,
                "L_s": cbs.lo,
                "U_s": cbs.hi,
            }
        success_guard_ok = bs.lo > -mc.delta
        return {
            "n": n,
            "n_collapsed": self._n_collapsed(),
            "sum_lower_h": bh.s_lower,
            "sum_upper_h": bh.s_upper,
            "sum_lower_s": bs.s_lower,
            "sum_upper_s": bs.s_upper,
            "radius": bh.radius,
            "L_h": bh.lo,
            "U_h": bh.hi,
            "L_s": bs.lo,
            "U_s": bs.hi,
            "flags": {
                "n_min_ok": n >= mc.n_min,
                "harm": bh.hi < 0.0,
                "deploy": bh.lo > 0.0 and success_guard_ok,
                "success_guard_ok": success_guard_ok,
            },
            "readouts": {
                # protocol 8.8 item 1: the value of L_s against -0.10 and -0.15, as slack.
                # Structurally incapable of deciding: never read by `decide`.
                "L_s_vs_010": bs.lo + EXPLORATORY_MARGINS[0],
                "L_s_vs_015": bs.lo + EXPLORATORY_MARGINS[1],
                "s1_restricted": None,
                "completed_prefix": completed,
            },
            "sums_fsum": True,
        }


# --------------------------------------------------------------------------------------------
# The decision
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Decision:
    kind: Literal["deploy_candidate", "harm_keep_incumbent", "horizon_no_decision"]
    n: int
    band_h: Band
    band_s: Band
    rule_id: str = RULE_ID


def decide(state: MonitorState, mc: MonitorConfig) -> Decision | None:
    """[pure] THE decision function, evaluated on the CURRENT prefix only (protocol 8.4).

        n = state.n
        if n == 0 or n < mc.n_min:   -> None        (except the horizon check below)
        bh, bs = state.bands()
        if bh.hi < 0.0:                        -> harm_keep_incumbent          # U_h < 0
        if bh.lo > 0.0 and bs.lo > -mc.delta:  -> deploy_candidate             # L_h>0, L_s>-delta
        if n >= mc.n_max and every pair collapsed: -> horizon_no_decision
        else -> None

    Order is frozen (harm first).  Comparisons are strict, in float64, on the clipped endpoints.
    The harm tail is the HIERARCHY tail only: `U_s < -delta` is computed and logged (it is in the
    snapshot read-outs) and NEVER decides anything (PG-5, COORDINATOR rev2 item 1).

    Nothing about an earlier look is consulted: a crossing that is no longer true at this prefix
    does not decide (protocol 8.2, "no retained crossing").
    """
    if not isinstance(state, MonitorState):
        raise MonitorError("decide needs a MonitorState")
    if not isinstance(mc, MonitorConfig):
        raise MonitorError("decide needs a MonitorConfig")
    n = state.n
    if n == 0:
        return None
    bands = state.bands()
    assert bands is not None  # n >= 1
    bh, bs = bands
    at_horizon = n >= mc.n_max and state._all_collapsed()
    if n < mc.n_min:
        if at_horizon:
            return Decision(kind="horizon_no_decision", n=n, band_h=bh, band_s=bs)
        return None
    if bh.hi < 0.0:
        return Decision(kind="harm_keep_incumbent", n=n, band_h=bh, band_s=bs)
    if bh.lo > 0.0 and bs.lo > -mc.delta:
        return Decision(kind="deploy_candidate", n=n, band_h=bh, band_s=bs)
    if at_horizon:
        return Decision(kind="horizon_no_decision", n=n, band_h=bh, band_s=bs)
    return None


# --------------------------------------------------------------------------------------------
# Replay
# --------------------------------------------------------------------------------------------
class _Episode:
    """Private bookkeeping for one episode of one pair while `replay` walks the chain."""

    __slots__ = ("arm", "stamps", "first_t_c1", "ell", "tokens_known", "view")

    def __init__(self, arm: str) -> None:
        self.arm = arm
        self.stamps: list[tuple[int, int]] = []
        self.first_t_c1: int | None = None
        self.ell: float = 0.0
        self.tokens_known: int = 0
        self.view = EpisodeView.pending(arm)

    def refresh_pending(self) -> None:
        self.view = EpisodeView.pending(self.arm, ell=self.ell, tokens_known=self.tokens_known)


def replay(events: Sequence[Mapping], cfg: dict, trial: str) -> list[dict]:
    """[pure] Rebuild every look from the chain alone; one snapshot per look, in order.

    Consumes exactly the event types of `CONSUMED_EVENT_TYPES` and nothing else.  Each
    `EpisodeView` is reconstructed from the chain (including `ell` via
    lab_enclosure.certified_elapsed on the worker stamps carried in
    llm_request/llm_response/llm_error) and enroll/update are applied in event order.

    A look is emitted for exactly the evaluation triggers of protocol 8.3 and for nothing else:

      * 'enroll'  -- one per `coin_drawn`.  The prefix `n` is the count of chain-valid
        `coin_drawn` events (protocol 7.3 item 2) and the orchestrator's own enroll look is
        written in state COMMITTED, i.e. after the coin (ARCHITECTURE 7.1 rows 5 and 6).  In a
        well-formed chain each `pair_enrolled` is followed immediately by its `coin_drawn` with
        no other consumed event between them, so this is the same look list that protocol 8.3
        trigger 1 describes, and it never enrols a pair that was never randomized.
      * 'reveal'  -- every pre-decision `episode_revealed`.
      * 'call'    -- every llm_request/llm_response/llm_error of a PENDING episode of an enrolled
        pair that RAISES that episode's certified `ell`.  A call event that does not raise `ell`
        produces no look.
      * 'resume'  -- one per resume boundary, at the last fully enrolled prefix before any new
        enrollment (protocol 14.5 item 4).  A resume boundary is a change of the envelope's `inv`
        field; see the note in the module tests.  None is emitted while n == 0.
      * 'drain'   -- a post-decision reveal of a PRE-decision pair, which updates the enclosure
        and emits a snapshot but never a decision.

    Post-decision reveals (`post_decision: true`) are IGNORED: the decision prefix is closed at
    the crossing.  A pre-decision pair that resolves after the decision DOES update its enclosure
    (guidance 7) but produces no new look that can decide.

    The caller (lab_verify_log) compares this list element-wise with the logged `monitor_update`
    bodies.
    """
    mc = MonitorConfig.from_config(cfg, trial)
    tiers = tiers_from_config(cfg)
    state = MonitorState(mc)

    looks: list[dict] = []
    pair_of_arrival: dict[int, int] = {}
    arrivals_of_pair: dict[int, list[int]] = {}
    episodes: dict[int, _Episode] = {}
    decided = False
    seen_inv: set[str] = set()
    pending_resume = False

    def _emit(trigger: str, pair_updated: int | None, enc: PairEnclosure | None) -> None:
        snap = state.snapshot()
        snap["trigger"] = trigger
        snap["pair_updated"] = pair_updated
        snap["pair_enclosure"] = (
            None
            if enc is None
            else {
                "h": [enc.h.lo, enc.h.hi],
                "s": [enc.s.lo, enc.s.hi],
                "collapsed": bool(enc.collapsed),
                "decisive_tier": int(enc.decisive_tier),
            }
        )
        looks.append(snap)

    def _update_pair(pair: int) -> PairEnclosure:
        arrivals = arrivals_of_pair[pair]
        views = [episodes[a].view for a in arrivals]
        candidate = next((v for v in views if v.arm == "candidate"), None)
        incumbent = next((v for v in views if v.arm == "incumbent"), None)
        if candidate is None or incumbent is None:
            raise MonitorError(f"pair {pair} does not carry one episode of each arm")
        enc = pair_enclosure(candidate, incumbent, tiers)
        state.update(pair, enc)
        return enc

    def _flush_resume() -> None:
        nonlocal pending_resume
        if pending_resume and state.n > 0 and not decided:
            _emit("resume", None, None)
        pending_resume = False

    for event in events:
        if not isinstance(event, Mapping):
            raise MonitorError("every chain event must be a mapping")
        chain = event.get("chain")
        if chain is not None and chain != trial:
            continue
        etype = event.get("type")
        if etype not in CONSUMED_EVENT_TYPES:
            continue
        inv = event.get("inv")
        if inv is not None and inv not in seen_inv:
            if seen_inv:
                _flush_resume()
                pending_resume = True
            seen_inv.add(inv)
        body = event.get("body")
        if not isinstance(body, Mapping):
            raise MonitorError(f"{etype} carries no body")

        if etype == "pair_enrolled":
            pair = int(body["pair"])
            arrivals = [int(a) for a in body["arrivals"]]
            if len(arrivals) != 2:
                raise MonitorError(f"pair {pair} does not have exactly two arrivals")
            arrivals_of_pair[pair] = arrivals
            for arrival in arrivals:
                pair_of_arrival[arrival] = pair

        elif etype == "coin_drawn":
            pair = int(body["pair"])
            assignment = body["assignment"]
            if pair not in arrivals_of_pair:
                raise MonitorError(f"coin_drawn for pair {pair} without a pair_enrolled")
            assigned: list[str] = []
            for arrival in arrivals_of_pair[pair]:
                arm = assignment.get(str(arrival), assignment.get(arrival))
                if arm not in ARMS:
                    raise MonitorError(f"arrival {arrival} of pair {pair} has no arm assignment")
                episodes[arrival] = _Episode(arm)
                assigned.append(arm)
            if sorted(assigned) != sorted(ARMS):
                raise MonitorError(f"pair {pair} is not one episode of each arm")
            _flush_resume()
            state.enroll(pair)
            enc = _update_pair(pair)
            _emit("enroll", pair, enc)

        elif etype in ("llm_request", "llm_response", "llm_error"):
            if decided:
                # After a decision the ONLY look is the drain reveal: protocol 9.1 item 4
                # ("its reveal updates its enrollment-indexed record as usual,
                # monitor_update with trigger='drain', no second decision") and
                # ARCHITECTURE_FINAL.md 7.1 row 12, whose DRAINING row writes a
                # monitor_update at the `episode_final` and at nothing else.  The decision
                # prefix is closed at the crossing, so a call that raises `ell` of the
                # drained episode narrows its enclosure at the drain reveal and produces
                # no look of its own.  [G5 integration fix, see README.]
                continue
            arrival = int(body["arrival"])
            pair = pair_of_arrival.get(arrival)
            if pair is None or pair > state.n:
                continue  # not an enrolled pair: no look (protocol 8.3 trigger 3)
            episode = episodes.get(arrival)
            if episode is None or episode.view.revealed:
                continue  # a call event of a revealed episode raises nothing
            t_c1 = body.get("t_c1_ns", episode.first_t_c1)
            if t_c1 is None:
                continue
            t_c1 = int(t_c1)
            if episode.first_t_c1 is None:
                episode.first_t_c1 = t_c1
            new_stamps = [
                (episode.first_t_c1, int(body[key]))
                for key in ("t_send_ns", "t_recv_ns")
                if body.get(key) is not None
            ]
            if not new_stamps:
                continue
            episode.stamps.extend(new_stamps)
            usage = body.get("usage")
            if isinstance(usage, Mapping) and usage.get("completion_tokens") is not None:
                episode.tokens_known += int(usage["completion_tokens"])
            new_ell = certified_elapsed(episode.stamps)
            if new_ell <= episode.ell:
                continue  # did not raise `ell`: NO look (ARCHITECTURE 7.1 row 7b)
            episode.ell = new_ell
            episode.refresh_pending()
            enc = _update_pair(pair)
            _emit("call", pair, enc)

        elif etype == "episode_revealed":
            if bool(body.get("post_decision", False)):
                continue  # the decision prefix is closed at the crossing
            arrival = int(body["arrival"])
            pair = pair_of_arrival.get(arrival)
            if pair is None or pair > state.n:
                continue
            episode = episodes.get(arrival)
            if episode is None:
                continue
            outcome = body["outcome"]
            episode.view = EpisodeView.reveal(
                episode.arm,
                int(outcome["success"]),
                float(outcome["latency_s"]),
                int(outcome["completion_tokens"]),
            )
            enc = _update_pair(pair)
            _emit("drain" if decided else "reveal", pair, enc)

        elif etype == "decision":
            decided = True

        # 'arm_assigned_by_decision' and 'traffic_switch' are consumed but produce no look.

    _flush_resume()
    return looks


# --------------------------------------------------------------------------------------------
# The radius table (freeze bundle deliverable)
# --------------------------------------------------------------------------------------------
def radius_table(ns: Sequence[int], mc: MonitorConfig) -> list[dict]:
    """[pure] [{'n': n, 'radius': r, 'alpha_gate': ..., 'rho': ...}, ...] for the freeze bundle.

    Regenerated from src/winstats.py.  No radius anywhere in this program is hand-typed (PG-20).
    """
    rows: list[dict] = []
    for n in ns:
        if isinstance(n, bool) or not isinstance(n, int):
            raise MonitorError("radius_table takes integer prefixes")
        if n < 1:
            raise MonitorError("radius_table requires n >= 1")
        rows.append(
            {
                "n": n,
                "radius": float(
                    winstats.normal_mixture_radius(
                        n, alpha=mc.alpha_gate, rho=mc.rho, variance_process=n
                    )
                ),
                "alpha_gate": mc.alpha_gate,
                "rho": mc.rho,
            }
        )
    return rows
