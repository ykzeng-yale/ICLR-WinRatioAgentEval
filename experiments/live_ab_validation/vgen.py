"""vgen.py -- the frozen data-generating process of PROTOCOL sections 4 and 5.

Issue #12 (independent CPU validation).  This module implements, exactly as
frozen and with no discretion left to the implementer:

  * section 4.1  the six-atom outcome table with integer weights out of 10,000,
                 sampled by an exact cumulative-threshold lookup;
  * section 4.2  the two delay blocks (SHORT, LONG) and both delay rules -- the
                 noninformative rule ``N`` and the outcome-dependent asymmetric
                 rule ``A``;
  * section 4.3  the reveal schedule (first-reveal offset and the fair
                 first-reveal coin) and the elapsed-cost accrual
                 ``ell(a) = (c * a) / D``, evaluated in that order;
  * section 2.5  the enclosure a pair contributes at any age, derived from the
                 frozen feasibility predicate (NOT from its closed-form
                 reading, which differs at one boundary point);
  * section 5    the seeding scheme: one independent ``SeedSequence`` stream per
                 (namespace, cell, program, trial) and the frozen five-array
                 draw order.

SOURCE DECLARATION -- files read while writing this module
----------------------------------------------------------
Read (the only sources used):
  * experiments/live_ab_validation/PROTOCOL.md   -- the frozen pre-registration
  * experiments/live_ab_validation/cells.json    -- its machine-readable twin,
                                                   normative for every value
  * experiments/live_ab_validation/vband.py      -- the #12 object under test
  * src/winstats.py                              -- the pinned primitives

Deliberately NOT read, opened, grepped or imported (independence constraint,
PROTOCOL 12.1): the #11 monitor and enclosure modules, and the pinned read-only
copy of them that sits beside this file.  Only the comparison module may load
those, and only after the grid has run.

WHY THIS FILE IS VECTORIZED, AND WHAT THAT MAY NOT CHANGE
---------------------------------------------------------
The grid is 8 cells x up to 5,000 programs x 4 trials x up to 2,000 enrolled
pairs x 2,001 looks, so a per-look Python loop over ``vband.ValidationMonitor``
cannot finish inside the frozen budget.  The vectorized path here is an
accelerator and nothing else: every enclosure endpoint it produces is an
integer in {-1, 0, +1}, so the running sums are accumulated exactly, and the
band arithmetic downstream is bit-for-bit what ``vband.normal_mixture_band``
computes from the same endpoints.  ``vrun.py --selfcheck`` drives
``vband.ValidationMonitor`` over whole trials event by event and asserts strict
float equality of every band endpoint at every look; if that check fails, the
accelerator is wrong and the numbers it produced are void.

Nothing in this module chooses, tunes or adapts anything.  CPU only.  No model
call, no API call, no network, no new dependency.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import vband

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CELLS_JSON = HERE / "cells.json"

# ---------------------------------------------------------------------------
# PROTOCOL 5: seeding
# ---------------------------------------------------------------------------
MASTER_SEED = 1220260919
NAMESPACE_GRID = 0          # the reported grid of section 7
NAMESPACE_SMOKE = 1         # the smoke run of section 8.1; discarded seeds
NAMESPACE_FIXTURE = 2       # the frozen fixture and comparison streams

# ---------------------------------------------------------------------------
# PROTOCOL 2.1 / 7.1 / 7.3: frozen parameters
# ---------------------------------------------------------------------------
N_MAX = 2000                # enrolled pairs per trial (root item 4)
DRAIN_W = 200               # finalization drain, in enrollment ticks
TRIALS_PER_PROGRAM = 4
WEIGHT_DENOMINATOR = 10000
DELAY_DENOMINATOR = 40000

COST_CAP = 100.0
RTOL = vband.COST_RELATIVE_TOLERANCE        # 0.05
ATOL = vband.COST_ABSOLUTE_TOLERANCE        # 0.0

SHORT_LOW, SHORT_HIGH = 0, 19
LONG_LOW, LONG_HIGH = 100, 699
MAX_DELAY = LONG_HIGH

# ---------------------------------------------------------------------------
# PROTOCOL 4.1: the six-atom table.  (s_C, s_I, c_C, c_I, Z, D)
# ---------------------------------------------------------------------------
ATOM_ORDER: Tuple[str, ...] = ("BB+", "BB0", "BB-", "C>I", "I>C", "FF")
ATOM_TABLE: Dict[str, Tuple[int, int, float, float, int, int]] = {
    "BB+": (1, 1, 10.0, 40.0, +1, 0),
    "BB0": (1, 1, 40.0, 40.0, 0, 0),
    "BB-": (1, 1, 40.0, 10.0, -1, 0),
    "C>I": (1, 0, 10.0, 40.0, +1, +1),
    "I>C": (0, 1, 40.0, 10.0, -1, -1),
    "FF": (0, 0, 40.0, 40.0, 0, 0),
}
ATOM_SC = np.array([ATOM_TABLE[a][0] for a in ATOM_ORDER], dtype=np.int8)
ATOM_SI = np.array([ATOM_TABLE[a][1] for a in ATOM_ORDER], dtype=np.int8)
ATOM_CC = np.array([ATOM_TABLE[a][2] for a in ATOM_ORDER], dtype=np.float64)
ATOM_CI = np.array([ATOM_TABLE[a][3] for a in ATOM_ORDER], dtype=np.float64)
ATOM_Z = np.array([ATOM_TABLE[a][4] for a in ATOM_ORDER], dtype=np.int8)
ATOM_D = np.array([ATOM_TABLE[a][5] for a in ATOM_ORDER], dtype=np.int8)

# ---------------------------------------------------------------------------
# PROTOCOL 4.1: the four outcome laws
# ---------------------------------------------------------------------------
LAW_WEIGHTS: Dict[str, Dict[str, int]] = {
    "L1": {"BB+": 2250, "BB0": 500, "BB-": 2250, "C>I": 1500, "I>C": 1500, "FF": 2000},
    "L2": {"BB+": 1500, "BB0": 500, "BB-": 4000, "C>I": 3000, "I>C": 500, "FF": 500},
    "L3": {"BB+": 5000, "BB0": 300, "BB-": 700, "C>I": 1200, "I>C": 1500, "FF": 1300},
    "L4": {"BB+": 4000, "BB0": 1000, "BB-": 1500, "C>I": 2500, "I>C": 500, "FF": 500},
}
LAW_NAMES = {"L1": "aa_null", "L2": "pref_boundary",
             "L3": "success_boundary", "L4": "favorable_alt"}


def _weight_vector(law: str) -> np.ndarray:
    return np.array([LAW_WEIGHTS[law][a] for a in ATOM_ORDER], dtype=np.int64)


LAW_WEIGHT_VEC = {law: _weight_vector(law) for law in LAW_WEIGHTS}
LAW_CUMWEIGHTS = {law: np.cumsum(LAW_WEIGHT_VEC[law]) for law in LAW_WEIGHTS}
#: w_neg = w[BB-] + w[I>C], the integer weight of Z = -1 (PROTOCOL 4.2)
LAW_W_NEG = {law: int(LAW_WEIGHTS[law]["BB-"] + LAW_WEIGHTS[law]["I>C"])
             for law in LAW_WEIGHTS}


def mu_h_of(law: str) -> float:
    w = LAW_WEIGHTS[law]
    return (w["BB+"] + w["C>I"] - w["BB-"] - w["I>C"]) / WEIGHT_DENOMINATOR


def mu_s_of(law: str) -> float:
    w = LAW_WEIGHTS[law]
    return (w["C>I"] - w["I>C"]) / WEIGHT_DENOMINATOR


# ---------------------------------------------------------------------------
# PROTOCOL 4: the eight cells
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CellSpec:
    id: str
    index: int
    law: str
    delay: str
    mu_h: float
    mu_s: float
    escalation_eligible: bool

    @property
    def law_name(self) -> str:
        return LAW_NAMES[self.law]

    @property
    def informative_delay(self) -> bool:
        return self.delay == "A"


def _build_cells() -> Tuple[CellSpec, ...]:
    out: List[CellSpec] = []
    idx = 0
    for law in ("L1", "L2", "L3", "L4"):
        for delay in ("N", "A"):
            out.append(CellSpec(
                id=f"C{idx + 1}", index=idx, law=law, delay=delay,
                mu_h=mu_h_of(law), mu_s=mu_s_of(law),
                escalation_eligible=law in ("L2", "L3")))
            idx += 1
    return tuple(out)


CELLS: Tuple[CellSpec, ...] = _build_cells()
CELL_BY_ID: Dict[str, CellSpec] = {c.id: c for c in CELLS}


def p_long_rule_n(law: str) -> float:
    """PROTOCOL 4.2: p_long = 3 * w_neg / 40000 under the noninformative rule."""
    return 3 * LAW_W_NEG[law] / DELAY_DENOMINATOR


# ---------------------------------------------------------------------------
# PROTOCOL 2.5: the cost-tier narrowing thresholds, by the FROZEN PREDICATE
# ---------------------------------------------------------------------------
#: the three (revealed cost, pending cost) pairs a partially revealed pair whose
#: revealed arm SUCCEEDED can present, given the atom cost columns of 4.1
COST_COMBOS: Tuple[Tuple[float, float], ...] = ((10.0, 40.0), (40.0, 10.0),
                                                (40.0, 40.0))


def pending_cheaper_feasible(c_rev, ell):
    """The frozen predicate: the pending arm can still be strictly cheaper.

    ``compare`` calls the cost tier decisive iff
    ``|a - b| > atol + rtol * max(|a|, |b|)``; with the revealed arm's cost known
    exactly and the pending arm bracketed by ``[ell, cost_cap]`` this is the
    corner test of ``vband.cost_order_possibilities``.  Written out with the same
    float operations, in the same order, so that the two agree bit for bit.
    """
    return (c_rev - ell) > (ATOL + RTOL * np.maximum(c_rev, ell))


def tie_feasible(c_rev, ell):
    """The frozen predicate: an exact cost tie is still reachable.

    The boxes ``[c, c]`` and ``[ell, cost_cap]`` overlap iff ``ell <= c``; when
    they do not, the tie survives iff the gap is within tolerance.  This is the
    reading that GOVERNS (PROTOCOL 2.5): its closed-form paraphrase
    ``ell > c / (1 - rtol)`` disagrees with it at the single boundary point
    ``ell = 200/19`` and is not used anywhere in this module.
    """
    return (ell <= c_rev) | ~((ell - c_rev) > (ATOL + RTOL * np.maximum(ell, c_rev)))


#: the two readings of PROTOCOL 2.5.  ``predicate`` is the one that GOVERNS -- it
#: is what ``vband`` computes and what ``compare`` itself uses, and it is the
#: only one the generated streams ever see.  ``closed_form`` is 2.5's own
#: paraphrase, kept solely so that the two can be priced against each other at
#: the 128 boundary states where 2.5 says they disagree.
READINGS = ("predicate", "closed_form")


def _build_threshold_tables(reading: str = "predicate"
                            ) -> Tuple[np.ndarray, np.ndarray]:
    """First age at which the pending-cheaper branch, then the tie, dies.

    Indexed ``[combo, d]``.  A value equal to ``d`` means "never inside this
    pending episode's life".  Built once by evaluating the rule at every
    (d, age) the frozen delay blocks can produce -- no sampling, no tolerance.
    """
    n_d = MAX_DELAY + 1
    ages = np.arange(n_d, dtype=np.int64)
    d_col = ages.reshape(-1, 1)
    a_row = ages.reshape(1, -1)
    inside = a_row < d_col                       # the pending episode's own life
    safe_d = np.where(d_col > 0, d_col, 1)
    narrow = np.empty((len(COST_COMBOS), n_d), dtype=np.int64)
    collapse = np.empty((len(COST_COMBOS), n_d), dtype=np.int64)
    big = n_d + 10
    for ci, (c_rev, c_pend) in enumerate(COST_COMBOS):
        ell = (c_pend * a_row) / safe_d
        if reading == "predicate":
            dead_pend = inside & ~pending_cheaper_feasible(c_rev, ell)
            dead_tie = inside & ~tie_feasible(c_rev, ell)
        elif reading == "closed_form":
            dead_pend = inside & ~(ell < (1.0 - RTOL) * c_rev)
            dead_tie = inside & (ell > c_rev / (1.0 - RTOL))
        else:                                               # pragma: no cover
            raise ValueError(f"unknown reading {reading!r}")
        a1 = np.where(dead_pend, a_row, big).min(axis=1)
        a2 = np.where(dead_tie, a_row, big).min(axis=1)
        narrow[ci] = np.minimum(a1, ages)
        collapse[ci] = np.minimum(a2, ages)
    if np.any(narrow > collapse):               # pragma: no cover - a fixed fact
        raise AssertionError("the tie must die no earlier than the pending branch")
    return narrow, collapse


THRESH_NARROW, THRESH_COLLAPSE = _build_threshold_tables("predicate")
THRESH_NARROW_CF, THRESH_COLLAPSE_CF = _build_threshold_tables("closed_form")


def boundary_state_count() -> int:
    """PROTOCOL 2.5's own number: the states on which the two readings disagree.

    Counted over exactly the grid 2.5 names -- every (atom, revealed arm, d,
    age) with ``d`` in the frozen delay blocks.  2.5 says this is ``128``, all
    of them at elapsed fraction ``5/19``; reproducing that count is a check on
    the predicate implemented above.
    """
    n_d = MAX_DELAY + 1
    ages = np.arange(n_d, dtype=np.int64)
    d_col = ages.reshape(-1, 1)
    a_row = ages.reshape(1, -1)
    inside = a_row < d_col
    in_blocks = np.zeros(n_d, dtype=bool)
    in_blocks[SHORT_LOW:SHORT_HIGH + 1] = True
    in_blocks[LONG_LOW:LONG_HIGH + 1] = True
    per_combo = np.zeros(len(COST_COMBOS), dtype=np.int64)
    for ci in range(len(COST_COMBOS)):
        differs = ((a_row >= THRESH_NARROW[ci].reshape(-1, 1))
                   != (a_row >= THRESH_NARROW_CF[ci].reshape(-1, 1))) | \
                  ((a_row >= THRESH_COLLAPSE[ci].reshape(-1, 1))
                   != (a_row >= THRESH_COLLAPSE_CF[ci].reshape(-1, 1)))
        per_combo[ci] = int((differs & inside & in_blocks.reshape(-1, 1)).sum())
    total = 0
    for ai in range(len(ATOM_ORDER)):
        for cand_first in (True, False):
            _s, combo = _atom_arm_combo(ai, cand_first)
            if combo >= 0:
                total += int(per_combo[combo])
    return total

#: (c_rev, c_pend) -> combo index, via a 2-bit code on "is the cost 40?"
_COMBO_CODE = np.array([-1, 0, 1, 2], dtype=np.int8)


# ---------------------------------------------------------------------------
# PROTOCOL 5: one independent stream per (cell, program, trial)
# ---------------------------------------------------------------------------
def stream(namespace: int, cell_index: int, program_index: int,
           trial_index: int) -> np.random.Generator:
    """The frozen generator of one trial.

    The four coordinates are the whole of the key, so any single trial can be
    replayed in isolation from them alone (PROTOCOL 5).
    """
    ss = np.random.SeedSequence(
        entropy=MASTER_SEED,
        spawn_key=(int(namespace), int(cell_index), int(program_index),
                   int(trial_index)))
    return np.random.Generator(np.random.PCG64(ss))


@dataclass
class TrialDraw:
    """One trial's enrolled pairs, in immutable enrollment order."""

    cell: CellSpec
    namespace: int
    program_index: int
    trial_index: int
    n: int                      # enrolled pairs (the horizon N_max of this run)
    atom: np.ndarray            # int8 index into ATOM_ORDER
    z: np.ndarray               # int8 hierarchy score Z_i
    dsc: np.ndarray             # int8 success score D_i
    d: np.ndarray               # int64 full-resolution offset, enrollment ticks
    f: np.ndarray               # int64 first-reveal offset, f <= d
    cand_first: np.ndarray      # bool, the candidate revealed first
    s_rev: np.ndarray           # int8 success of the first-revealed arm
    c_rev: np.ndarray           # float64 final cost of the first-revealed arm
    c_pend: np.ndarray          # float64 final cost of the second arm
    a_narrow: np.ndarray        # int64 age at which the pending branch dies
    a_collapse: np.ndarray      # int64 age at which the tie dies

    @property
    def resolution_tick(self) -> np.ndarray:
        """Absolute tick at which each pair becomes fully resolved."""
        return np.arange(1, self.n + 1, dtype=np.int64) + self.d

    @property
    def reveal_tick(self) -> np.ndarray:
        """Absolute tick at which each pair's first episode reveals."""
        return np.arange(1, self.n + 1, dtype=np.int64) + self.f


def draw_trial(cell: CellSpec, program_index: int, trial_index: int,
               n_max: int = N_MAX,
               namespace: int = NAMESPACE_GRID) -> TrialDraw:
    """The frozen five-array draw order of PROTOCOL 5, and nothing else.

    All five arrays are drawn unconditionally and at full length, so the stream
    advances identically whichever branch a pair takes.
    """
    rng = stream(namespace, cell.index, program_index, trial_index)
    u_atom = rng.integers(0, WEIGHT_DENOMINATOR, size=n_max)
    u_delay = rng.integers(0, DELAY_DENOMINATOR, size=n_max)
    u_len = rng.random(size=n_max)
    u_first = rng.random(size=n_max)
    u_coin = rng.random(size=n_max)

    atom = np.searchsorted(LAW_CUMWEIGHTS[cell.law], u_atom,
                           side="right").astype(np.int8)
    z = ATOM_Z[atom]
    dsc = ATOM_D[atom]

    if cell.delay == "N":
        is_long = u_delay < 3 * LAW_W_NEG[cell.law]
    elif cell.delay == "A":
        is_long = (z == -1) & (u_delay < 30000)
    else:                                                   # pragma: no cover
        raise ValueError(f"unknown delay rule {cell.delay!r}")

    d = np.where(is_long,
                 LONG_LOW + np.floor(u_len * (LONG_HIGH - LONG_LOW + 1)),
                 np.floor(u_len * (SHORT_HIGH - SHORT_LOW + 1))).astype(np.int64)
    f = np.floor(u_first * (d + 1)).astype(np.int64)
    cand_first = u_coin < 0.5

    s_c, s_i = ATOM_SC[atom], ATOM_SI[atom]
    c_c, c_i = ATOM_CC[atom], ATOM_CI[atom]
    s_rev = np.where(cand_first, s_c, s_i).astype(np.int8)
    c_rev = np.where(cand_first, c_c, c_i)
    c_pend = np.where(cand_first, c_i, c_c)

    code = (c_rev > 20.0).astype(np.int8) * 2 + (c_pend > 20.0).astype(np.int8)
    combo = np.where(s_rev == 1, _COMBO_CODE[code], -1)
    safe_combo = np.maximum(combo, 0)
    a_narrow = np.where(combo >= 0, THRESH_NARROW[safe_combo, d], d)
    a_collapse = np.where(combo >= 0, THRESH_COLLAPSE[safe_combo, d], d)

    return TrialDraw(cell=cell, namespace=namespace, program_index=program_index,
                     trial_index=trial_index, n=int(n_max), atom=atom, z=z,
                     dsc=dsc, d=d, f=f, cand_first=cand_first, s_rev=s_rev,
                     c_rev=c_rev, c_pend=c_pend,
                     a_narrow=np.clip(a_narrow, f, d),
                     a_collapse=np.clip(a_collapse, f, d))


# ---------------------------------------------------------------------------
# PROTOCOL 2.5 + 4.3: the enclosure a pair contributes at a given age
# ---------------------------------------------------------------------------
@dataclass
class PairState:
    h_lo: np.ndarray
    h_hi: np.ndarray
    s_lo: np.ndarray
    s_hi: np.ndarray
    resolved: np.ndarray
    unrevealed: np.ndarray
    cost_narrowed: np.ndarray
    cost_collapsed: np.ndarray


def elapsed_cost(c_pend, age, d):
    """PROTOCOL 4.3: ``ell(a) = (c * a) / D``, in that evaluation order.

    With integer ``c`` and ``a`` the numerator is exact, so a threshold is hit
    at exactly the same age on every machine.
    """
    return (c_pend * age) / np.where(d > 0, d, 1)


def state_at_age(draw: TrialDraw, ages) -> PairState:
    """Every pair's enclosure at the given per-pair age, from the frozen table.

    ``ages`` broadcasts against the per-pair arrays, so a whole stack of ages
    can be evaluated at once.  Endpoints are integers in {-1, 0, +1} in every
    row of PROTOCOL 2.5, which is what makes the running sums exact.
    """
    age = np.asarray(ages)
    d, f = draw.d, draw.f
    resolved = age >= d
    unrevealed = age < f
    partial = ~resolved & ~unrevealed

    ell = elapsed_cost(draw.c_pend, age, d)
    q = np.where(pending_cheaper_feasible(draw.c_rev, ell), -1,
                 np.where(tie_feasible(draw.c_rev, ell), 0, 1)).astype(np.int8)

    succeeded = draw.s_rev == 1
    first_is_candidate = draw.cand_first
    h_lo_p = np.where(succeeded, np.where(first_is_candidate, q, -1),
                      np.where(first_is_candidate, -1, 0))
    h_hi_p = np.where(succeeded, np.where(first_is_candidate, 1, -q),
                      np.where(first_is_candidate, 0, 1))
    s_lo_p = np.where(succeeded, np.where(first_is_candidate, 0, -1),
                      np.where(first_is_candidate, -1, 0))
    s_hi_p = np.where(succeeded, np.where(first_is_candidate, 1, 0),
                      np.where(first_is_candidate, 0, 1))

    h_lo = np.where(resolved, draw.z, np.where(partial, h_lo_p, -1)).astype(np.int8)
    h_hi = np.where(resolved, draw.z, np.where(partial, h_hi_p, 1)).astype(np.int8)
    s_lo = np.where(resolved, draw.dsc, np.where(partial, s_lo_p, -1)).astype(np.int8)
    s_hi = np.where(resolved, draw.dsc, np.where(partial, s_hi_p, 1)).astype(np.int8)

    # PROTOCOL 9.5: "narrowed" is narrower than the success information alone
    # would give, which for a revealed-and-successful arm is the full range.
    narrowed = partial & succeeded & (q != -1)
    collapsed = partial & succeeded & (q == 1)
    return PairState(h_lo=h_lo, h_hi=h_hi, s_lo=s_lo, s_hi=s_hi,
                     resolved=resolved, unrevealed=unrevealed,
                     cost_narrowed=narrowed, cost_collapsed=collapsed)


# ---------------------------------------------------------------------------
# The adapter's running enclosure sums, maintained incrementally
# ---------------------------------------------------------------------------
#: how many enclosure changes a pair can contribute over a whole trial: it
#: enters at its enrollment tick, may reveal, may cross the two cost-tier
#: thresholds of PROTOCOL 2.5, and finally resolves.
BREAKPOINTS_PER_PAIR = 5


@dataclass
class PrefixSums:
    """Exact running enclosure sums, indexed by enrolled prefix ``n``."""

    h_lo: np.ndarray
    h_hi: np.ndarray
    s_lo: np.ndarray
    s_hi: np.ndarray
    updates: int                # enclosure changes actually applied


def adapter_prefix_sums(draw: TrialDraw, n_max: Optional[int] = None) -> PrefixSums:
    """``sum(lower[:n])`` and ``sum(upper[:n])`` at every look, for both scores.

    A pair's enclosure is piecewise constant in its age and changes at most
    four times (reveal, the two cost thresholds, resolution), so the sums are
    maintained as a difference array over enrollment ticks rather than
    recomputed per look.  This is the incremental property PROTOCOL 8.1
    requires; ``vrun.py`` counts the updates and asserts it.

    Every endpoint is an integer, so the accumulation is exact and the means
    downstream are bit-for-bit those of ``vband.normal_mixture_band``.
    """
    n = draw.n if n_max is None else int(n_max)
    positions = np.arange(1, draw.n + 1, dtype=np.int64)
    ages = np.stack([np.zeros(draw.n, dtype=np.int64), draw.f,
                     draw.a_narrow, draw.a_collapse, draw.d])
    st = state_at_age(draw, ages)
    ticks = np.minimum(positions[None, :] + ages, n + 1).ravel()

    out: List[np.ndarray] = []
    for values in (st.h_lo, st.h_hi, st.s_lo, st.s_hi):
        v = values.astype(np.int64)
        delta = v.copy()
        delta[1:] -= v[:-1]
        totals = np.bincount(ticks, weights=delta.ravel().astype(np.float64),
                             minlength=n + 2)[:n + 1]
        out.append(np.cumsum(totals))
    updates = int(np.count_nonzero(
        np.concatenate([np.ones((1, draw.n), dtype=bool),
                        (np.diff(st.h_lo, axis=0) != 0)
                        | (np.diff(st.h_hi, axis=0) != 0)
                        | (np.diff(st.s_lo, axis=0) != 0)
                        | (np.diff(st.s_hi, axis=0) != 0)])))
    return PrefixSums(h_lo=out[0], h_hi=out[1], s_lo=out[2], s_hi=out[3],
                      updates=updates)


def resolution_counts(draw: TrialDraw, n_max: Optional[int] = None
                      ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-look resolution bookkeeping, all as cumulative counts over ticks.

    Returns ``(resolved, revealed, cprefix_index, resolved_score_sum_h)`` where
    every array is indexed by the enrolled prefix ``n``:

      * ``resolved[n]``  = #{j <= n : d_j <= n - j}, the completed count ``m``;
      * ``revealed[n]``  = #{j <= n : f_j <= n - j};
      * ``cprefix_index[n]`` = ``k(n) = max{k : every pair 1..k is resolved}``;
      * ``resolved_score_sum_h[n]`` = sum of Z over the completed set.
    """
    n = draw.n if n_max is None else int(n_max)
    res_tick = np.minimum(draw.resolution_tick, n + 1)
    rev_tick = np.minimum(draw.reveal_tick, n + 1)
    resolved = np.cumsum(np.bincount(res_tick, minlength=n + 2)[:n + 1])
    revealed = np.cumsum(np.bincount(rev_tick, minlength=n + 2)[:n + 1])
    running_max = np.maximum.accumulate(draw.resolution_tick)
    cprefix = np.searchsorted(running_max, np.arange(n + 1), side="right")
    return resolved, revealed, cprefix, running_max


def completed_sums(draw: TrialDraw, values: np.ndarray,
                   n_max: Optional[int] = None) -> np.ndarray:
    """``sum of values over {j : pair j is fully resolved}`` at every look."""
    n = draw.n if n_max is None else int(n_max)
    res_tick = np.minimum(draw.resolution_tick, n + 1)
    totals = np.bincount(res_tick, weights=values.astype(np.float64),
                         minlength=n + 2)[:n + 1]
    return np.cumsum(totals)


def prefix_sums_of_scores(draw: TrialDraw) -> Tuple[np.ndarray, np.ndarray]:
    """Cumulative true scores by enrollment position, for the ``CPREFIX`` index."""
    return (np.concatenate([[0.0], np.cumsum(draw.z.astype(np.float64))]),
            np.concatenate([[0.0], np.cumsum(draw.dsc.astype(np.float64))]))


def finalization_ages(draw: TrialDraw, n_max: Optional[int] = None) -> np.ndarray:
    """PROTOCOL 7.3: the drain look at tick ``N_max + W``, prefix still ``N_max``."""
    n = draw.n if n_max is None else int(n_max)
    return (n + DRAIN_W) - np.arange(1, draw.n + 1, dtype=np.int64)


# ===========================================================================
# PROTOCOL 6: the analytic reachability arithmetic, recomputed independently
# ===========================================================================
# Nothing below is used by the grid.  It is an exact expectation under the
# frozen law -- no random number is drawn -- and it exists so that this
# generator can be checked, value for value, against the pre-registered tables
# of PROTOCOL 6 that were computed before it was written.  A mismatch is a
# defect in one of the two and is reported, never patched away.
# ===========================================================================
def _delay_pmfs() -> Tuple[np.ndarray, np.ndarray]:
    short = np.zeros(MAX_DELAY + 1)
    short[SHORT_LOW:SHORT_HIGH + 1] = 1.0 / (SHORT_HIGH - SHORT_LOW + 1)
    long_ = np.zeros(MAX_DELAY + 1)
    long_[LONG_LOW:LONG_HIGH + 1] = 1.0 / (LONG_HIGH - LONG_LOW + 1)
    return short, long_


def _age_kernels(max_age: int, reading: str = "predicate"):
    """Per-branch age kernels: everything the section 6 enumeration needs.

    For each branch (short, long) and age ``a``:
      ``surv[a]``     = P(d > a)                       (the pair is unresolved)
      ``unrev[a]``    = P(f > a) = E[(d-a)^+ / (d+1)]  (neither arm revealed)
      ``partial[a]``  = P(f <= a < d) = E[1{d>a} (a+1)/(d+1)]
      ``narrow[c][a]``/``collapse[c][a]`` = the same, restricted to the states in
      which the cost tier has narrowed / collapsed the hierarchy enclosure,
      for each (revealed cost, pending cost) combination ``c``.
    """
    ages = np.arange(max_age, dtype=np.int64)
    d_vals = np.arange(MAX_DELAY + 1, dtype=np.int64)
    d_col = d_vals.reshape(-1, 1)
    a_row = ages.reshape(1, -1)
    live = d_col > a_row                                    # d > a
    weight_partial = np.where(live, (a_row + 1) / (d_col + 1), 0.0)
    weight_unrev = np.where(live, (d_col - a_row) / (d_col + 1), 0.0)

    t_narrow = THRESH_NARROW if reading == "predicate" else THRESH_NARROW_CF
    t_collapse = THRESH_COLLAPSE if reading == "predicate" else THRESH_COLLAPSE_CF
    kernels = {}
    for name, pmf in zip(("short", "long"), _delay_pmfs()):
        entry = {
            "surv": pmf @ live.astype(np.float64),
            "unrev": pmf @ weight_unrev,
            "partial": pmf @ weight_partial,
            "narrow": [], "collapse": [],
        }
        for ci in range(len(COST_COMBOS)):
            narrowed = live & (a_row >= t_narrow[ci].reshape(-1, 1))
            collapsed = live & (a_row >= t_collapse[ci].reshape(-1, 1))
            entry["narrow"].append(pmf @ np.where(narrowed, weight_partial, 0.0))
            entry["collapse"].append(pmf @ np.where(collapsed, weight_partial, 0.0))
        kernels[name] = entry
    return kernels


def _atom_arm_combo(atom_index: int, cand_first: bool) -> Tuple[int, int]:
    """``(success of the revealed arm, cost-combo index or -1)``."""
    s_c, s_i = int(ATOM_SC[atom_index]), int(ATOM_SI[atom_index])
    c_c, c_i = float(ATOM_CC[atom_index]), float(ATOM_CI[atom_index])
    s_rev = s_c if cand_first else s_i
    c_rev = c_c if cand_first else c_i
    c_pend = c_i if cand_first else c_c
    if s_rev != 1:
        return s_rev, -1
    return s_rev, COST_COMBOS.index((c_rev, c_pend))


def analytic_profiles(cell: CellSpec, max_age: int, kernels=None) -> Dict[str, np.ndarray]:
    """Exact per-age expectations under the frozen law (PROTOCOL 6's method).

    For each pair age ``a``, the enclosure state is enumerated over
    (atom, long/short branch, d, f, first-revealed arm) with its exact
    probability.  No random number is drawn.
    """
    if kernels is None:
        kernels = _age_kernels(max_age)
    zero = np.zeros(max_age)
    acc = {k: zero.copy() for k in
           ("unresolved", "unrevealed", "cost_collapsed", "cost_narrowed",
            "h_lo", "h_hi", "s_lo", "s_hi")}
    weights = LAW_WEIGHT_VEC[cell.law] / WEIGHT_DENOMINATOR
    for ai, atom in enumerate(ATOM_ORDER):
        p_atom = float(weights[ai])
        if p_atom == 0.0:
            continue
        if cell.delay == "N":
            p_long = p_long_rule_n(cell.law)
        else:
            p_long = 0.75 if int(ATOM_Z[ai]) == -1 else 0.0
        for branch, p_branch in (("short", 1.0 - p_long), ("long", p_long)):
            if p_branch == 0.0:
                continue
            k = kernels[branch]
            base = p_atom * p_branch
            acc["unresolved"] += base * k["surv"]
            acc["unrevealed"] += base * k["unrev"]
            for cand_first in (True, False):
                w = base * 0.5
                s_rev, combo = _atom_arm_combo(ai, cand_first)
                part = k["partial"]
                narrow = k["narrow"][combo] if combo >= 0 else zero
                collapse = k["collapse"][combo] if combo >= 0 else zero
                if combo >= 0:
                    acc["cost_narrowed"] += w * narrow
                    acc["cost_collapsed"] += w * collapse
                # resolved contribution
                done = 1.0 - k["surv"]
                h_lo = w * done * float(ATOM_Z[ai])
                h_hi = h_lo.copy()
                s_lo = w * done * float(ATOM_D[ai])
                s_hi = s_lo.copy()
                # unrevealed contribution: the full range on both scores
                h_lo = h_lo - w * k["unrev"]
                h_hi = h_hi + w * k["unrev"]
                s_lo = s_lo - w * k["unrev"]
                s_hi = s_hi + w * k["unrev"]
                # partially revealed contribution, PROTOCOL 2.5 row by row
                if s_rev == 1:
                    q = -part + narrow + collapse
                    if cand_first:
                        h_lo = h_lo + w * q
                        h_hi = h_hi + w * part
                        s_lo = s_lo + 0.0
                        s_hi = s_hi + w * part
                    else:
                        h_lo = h_lo - w * part
                        h_hi = h_hi - w * q
                        s_lo = s_lo - w * part
                        s_hi = s_hi + 0.0
                else:
                    if cand_first:
                        h_lo = h_lo - w * part
                        h_hi = h_hi + 0.0
                        s_lo = s_lo - w * part
                        s_hi = s_hi + 0.0
                    else:
                        h_lo = h_lo + 0.0
                        h_hi = h_hi + w * part
                        s_lo = s_lo + 0.0
                        s_hi = s_hi + w * part
                acc["h_lo"] += h_lo
                acc["h_hi"] += h_hi
                acc["s_lo"] += s_lo
                acc["s_hi"] += s_hi
    return acc


def _prefix_mean(profile: np.ndarray, n: int) -> float:
    return float(profile[:n].sum() / n)


def _final_mean(profile: np.ndarray, n_max: int) -> float:
    return float(profile[DRAIN_W:DRAIN_W + n_max].sum() / n_max)


def analytic_tables(cell: CellSpec, n_max: int = N_MAX,
                    kernels=None) -> Dict[str, Dict[str, object]]:
    """PROTOCOL 6.1, 6.2, 6.3 and 6.4 for one cell, recomputed from scratch."""
    horizons = [100, 500, n_max]
    profiles = analytic_profiles(cell, n_max + DRAIN_W, kernels=kernels)
    out: Dict[str, Dict[str, object]] = {"unresolved": {}, "cost": {}, "band": {}}
    for h in horizons:
        out["unresolved"][str(h)] = (_prefix_mean(profiles["unresolved"], h),
                                     _prefix_mean(profiles["unrevealed"], h))
        out["cost"][str(h)] = (_prefix_mean(profiles["cost_collapsed"], h),
                               _prefix_mean(profiles["cost_narrowed"], h))
    out["unresolved"]["FINAL"] = (_final_mean(profiles["unresolved"], n_max),
                                  _final_mean(profiles["unrevealed"], n_max))
    out["cost"]["FINAL"] = (_final_mean(profiles["cost_collapsed"], n_max),
                            _final_mean(profiles["cost_narrowed"], n_max))

    radius = np.array([vband.radius_from_formula(n) for n in range(1, n_max + 1)])
    cum_h_lo = np.cumsum(profiles["h_lo"])
    cum_h_hi = np.cumsum(profiles["h_hi"])
    cum_s_lo = np.cumsum(profiles["s_lo"])
    idx = np.arange(1, n_max + 1)
    l_h = np.clip(cum_h_lo[:n_max] / idx - radius, -1.0, 1.0)
    u_h = np.clip(cum_h_hi[:n_max] / idx + radius, -1.0, 1.0)
    l_s = np.clip(cum_s_lo[:n_max] / idx - radius, -1.0, 1.0)
    for h in horizons:
        out["band"][str(h)] = (float(l_h[h - 1]), float(u_h[h - 1]),
                               float(l_s[h - 1]))
    fin = (_final_mean(profiles["h_lo"], n_max),
           _final_mean(profiles["h_hi"], n_max),
           _final_mean(profiles["s_lo"], n_max))
    r_fin = vband.radius_from_formula(n_max)
    out["band"]["FINAL"] = (float(np.clip(fin[0] - r_fin, -1.0, 1.0)),
                            float(np.clip(fin[1] + r_fin, -1.0, 1.0)),
                            float(np.clip(fin[2] - r_fin, -1.0, 1.0)))

    n_min = vband.N_MIN
    delta = vband.DELTA

    def _first(mask: np.ndarray) -> Optional[int]:
        eligible = mask.copy()
        eligible[:n_min - 1] = False
        hits = np.flatnonzero(eligible)
        return int(hits[0] + 1) if hits.size else None

    open_h = _first(l_h > 0.0)
    open_s = _first(l_s > -delta)
    open_u = _first(u_h < 0.0)
    deploy = _first((l_h > 0.0) & (l_s > -delta))
    out["gates"] = {"L_h>0": open_h, "L_s>-delta": open_s, "U_h<0": open_u,
                    "DEPLOY": deploy}
    return out


def _round4(x: float) -> float:
    return float(Decimal(repr(float(x))).quantize(Decimal("0.0001"),
                                                  rounding=ROUND_HALF_UP))


def selfcheck(n_max: int = N_MAX, verbose: bool = True,
              reading: str = "predicate") -> List[str]:
    """Recompute PROTOCOL 6 from this generator and compare to ``cells.json``.

    This is the strongest available check that the data-generating process and
    the enclosure arithmetic implemented here are the ones the frozen
    pre-registration describes: the tables it compares against were computed by
    the protocol's author, before this module existed, by an independent
    enumeration.

    ``reading`` selects which reading of the PROTOCOL 2.5 thresholds the
    ENUMERATION uses.  It never touches the generated streams, which always use
    the governing predicate.
    """
    cfg = json.loads(CELLS_JSON.read_text())
    ar = cfg["analytic_reachability"]
    if n_max == N_MAX:
        want_unres = ar["expected_unresolved_unrevealed_fraction"]
        want_cost = ar["expected_cost_enclosure_exercise"]
        want_band = ar["expected_path_band_endpoints_Lh_Uh_Ls"]
        want_gate = ar["expected_path_gate_opening_prefix"]
    else:
        variant = ar["T4_variant_N_max_1000"]
        want_unres = variant["expected_unresolved_unrevealed_fraction"]
        want_cost = variant["expected_cost_enclosure_exercise"]
        want_band = variant["expected_path_band_endpoints_Lh_Uh_Ls"]
        want_gate = variant["expected_path_gate_opening_prefix"]
    fails: List[str] = []
    kernels = _age_kernels(n_max + DRAIN_W, reading=reading)
    for cell in CELLS:
        got = analytic_tables(cell, n_max=n_max, kernels=kernels)
        for key in got["unresolved"]:
            want = want_unres[cell.law][key]
            have = [_round4(v) for v in got["unresolved"][key]]
            if have != [float(w) for w in want]:
                fails.append(f"6.1 {cell.id} n={key}: got {have} want {want}")
        for key in got["cost"]:
            want = want_cost[cell.id][key]
            have = [_round4(v) for v in got["cost"][key]]
            if have != [float(w) for w in want]:
                fails.append(f"6.4 {cell.id} n={key}: got {have} want {want}")
        for key in got["band"]:
            want = want_band[cell.id][key]
            have = [_round4(v) for v in got["band"][key]]
            if have != [float(w) for w in want]:
                fails.append(f"6.3 {cell.id} n={key}: got {have} want {want}")
        want = want_gate[cell.id]
        for key, have in got["gates"].items():
            if have != want[key]:
                fails.append(f"6.2 {cell.id} {key}: got {have} want {want[key]}")
        if verbose:
            print(f"  {cell.id} {cell.law}/{cell.delay}: "
                  f"unresolved {got['unresolved'][str(n_max)][0]:.4f} "
                  f"cost-point {got['cost']['500'][0]:.4f} "
                  f"L_h({n_max})={got['band'][str(n_max)][0]:+.4f} "
                  f"gates {got['gates']}")
    return fails


def selfcheck_report(n_max: int = N_MAX, verbose: bool = True) -> Dict[str, object]:
    """Price PROTOCOL 6 under both readings of the 2.5 thresholds.

    The generated streams always use the governing predicate.  This reports
    which reading reproduces the frozen tables, so that a difference between
    the two is a stated finding with a magnitude rather than a silent choice.
    """
    out: Dict[str, object] = {"n_max": n_max,
                              "boundary_states": boundary_state_count()}
    for reading in READINGS:
        if verbose:
            print(f"\n-- PROTOCOL 2.5 threshold reading: {reading} --")
        fails = selfcheck(n_max=n_max, verbose=verbose and reading == "predicate",
                          reading=reading)
        out[reading] = fails
        if verbose:
            print(f"   {len(fails)} disagreement(s) with the frozen tables")
    return out


# ---------------------------------------------------------------------------
# The frozen values of this module agree with the machine-readable twin
# ---------------------------------------------------------------------------
def verify_against_cells_json() -> List[str]:
    """Every constant transcribed above, checked against ``cells.json``.

    ``cells.json`` is normative for every numeric value (PROTOCOL header), so a
    disagreement here means this module is wrong, and it fails loudly rather
    than running with a value the pre-registration does not carry.
    """
    cfg = json.loads(CELLS_JSON.read_text())
    fails: List[str] = []

    def _eq(label: str, got, want) -> None:
        if isinstance(got, float) or isinstance(want, float):
            ok = abs(float(got) - float(want)) <= 1e-12
        else:
            ok = got == want
        if not ok:
            fails.append(f"{label}: this module has {got!r}, cells.json has {want!r}")

    par = cfg["parameters"]
    _eq("master_seed", MASTER_SEED, cfg["seeding"]["master_seed"])
    _eq("N_max", N_MAX, par["N_max"])
    _eq("drain_W", DRAIN_W, par["drain_W"])
    _eq("trials_per_program", TRIALS_PER_PROGRAM, par["trials_per_program"])
    _eq("cost_cap", COST_CAP, par["cost_model"]["cost_cap"])
    _eq("weight_denominator", WEIGHT_DENOMINATOR,
        cfg["outcome_atoms"]["weight_denominator"])
    _eq("atom order", list(ATOM_ORDER), cfg["outcome_atoms"]["order"])
    for row in cfg["outcome_atoms"]["definition"]:
        want = (row["s_candidate"], row["s_incumbent"], row["c_candidate"],
                row["c_incumbent"], row["Z"], row["D"])
        _eq(f"atom {row['atom']}", ATOM_TABLE[row["atom"]], want)
    for law, spec in cfg["outcome_laws"].items():
        _eq(f"{law} weights", LAW_WEIGHTS[law], spec["weights"])
        _eq(f"{law} mu_h", mu_h_of(law), spec["mu_h"])
        _eq(f"{law} mu_s", mu_s_of(law), spec["mu_s"])
        _eq(f"{law} w_neg", LAW_W_NEG[law], spec["w_neg"])
        _eq(f"{law} name", LAW_NAMES[law], spec["name"])
    blocks = cfg["delay_blocks"]
    _eq("SHORT low", SHORT_LOW, blocks["SHORT"]["low"])
    _eq("SHORT high", SHORT_HIGH, blocks["SHORT"]["high"])
    _eq("LONG low", LONG_LOW, blocks["LONG"]["low"])
    _eq("LONG high", LONG_HIGH, blocks["LONG"]["high"])
    for want in cfg["cells"]:
        cell = CELL_BY_ID[want["id"]]
        _eq(f"{cell.id} index", cell.index, want["cell_index"])
        _eq(f"{cell.id} law", cell.law, want["law"])
        _eq(f"{cell.id} delay", cell.delay, want["delay"])
        _eq(f"{cell.id} mu_h", cell.mu_h, want["mu_h"])
        _eq(f"{cell.id} mu_s", cell.mu_s, want["mu_s"])
        _eq(f"{cell.id} p_long", p_long_rule_n(cell.law), want["p_long"])
        _eq(f"{cell.id} escalation", cell.escalation_eligible,
            want["escalation_eligible"])
    ns = cfg["seeding"]["namespaces"]
    for got, key in ((NAMESPACE_GRID, "0"), (NAMESPACE_SMOKE, "1"),
                     (NAMESPACE_FIXTURE, "2")):
        if str(got) != key and key not in ns:                # pragma: no cover
            fails.append(f"namespace {got} missing from cells.json")
    return fails


_IMPORT_FAILS = verify_against_cells_json()
if _IMPORT_FAILS:                                            # pragma: no cover
    raise AssertionError("vgen disagrees with the frozen cells.json: "
                         + "; ".join(_IMPORT_FAILS))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selfcheck", action="store_true",
                    help="recompute PROTOCOL section 6 and compare to cells.json")
    ap.add_argument("--n-max", type=int, default=N_MAX)
    args = ap.parse_args(argv)
    print(f"vgen: {len(CELLS)} cells, master seed {MASTER_SEED}, "
          f"N_max {args.n_max}, drain {DRAIN_W}")
    print("frozen constants agree with cells.json")
    if not args.selfcheck:
        return 0
    print(f"\nrecomputing PROTOCOL 6.1-6.4 at N_max={args.n_max} "
          f"(exact enumeration, no simulation):")
    report = selfcheck_report(n_max=args.n_max)
    print(f"\nPROTOCOL 2.5 boundary states between the two readings: "
          f"{report['boundary_states']} (2.5 states 128)")
    for reading in READINGS:
        fails = report[reading]
        print(f"\n{reading}: {len(fails)} disagreement(s)")
        for f in fails:
            print(f"    {f}")
    predicate_fails = report["predicate"]
    closed_fails = report["closed_form"]
    if not predicate_fails:
        print("\nall of PROTOCOL 6.1, 6.2, 6.3 and 6.4 reproduced exactly "
              "under the governing predicate")
        return 0
    if not closed_fails:
        print("\nFINDING: the frozen PROTOCOL 6.3/6.4 tables are reproduced "
              "exactly by the CLOSED-FORM reading of the 2.5 thresholds and "
              "not by the predicate that 2.5 says governs. The generator uses "
              "the PREDICATE, as 2.5 requires. Reported, not patched.")
        return 2
    print("\nneither reading reproduces the frozen tables")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
