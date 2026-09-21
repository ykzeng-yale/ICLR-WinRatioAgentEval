"""vrun.py -- the grid runner of PROTOCOL sections 7 to 9.

Issue #12 (independent CPU validation).  One command, writing only inside its
own output directory:

    .venv/bin/python experiments/live_ab_validation/vrun.py --out results/live_ab_validation

THE v2 EVENT-SCHEDULE AMENDMENT (root disposition section B)
------------------------------------------------------------
The root's open finding is that the deposited v1 runner OMITS the intermediate
looks at which a completed-data baseline's completion index changes: at horizon
1,000 there is a permitted tick at which BOTH baseline lower bounds are
+0.0133027164 and BOTH deploy gates cross, and v1 never evaluates it.  The
schedule declaration below is the repair.  It is a VERSIONED AMENDMENT that sits
beside v1 (PROTOCOL 14): v1's schedule stays reachable and bit-exact, and both
are reported.  Three commands matter here:

    vrun.py --witness                      the missed crossing, both schedules
    vrun.py --schedule v2_tick_batched     the v2 primary (the runner default)
    vrun.py --schedule v1_reduced          reproduce v1, to report beside v2

NOTHING SCIENTIFIC MOVED WITH IT.  A schedule is a measurement contract -- it
says which states are looked at, not what is computed at one.  The margins, the
alpha allocation .00625, rho 100, delta 0.03, n_min 100, the gates, the episode
stopping, deadline and finalization rules, the cells, the weights, the delay
rules, the seeds, the estimators, the flag rule and the positive control are all
exactly as frozen, and ``assert_v2_reduces_to_v1`` checks state for state that
every v1 look is still on the v2 axis carrying the same numbers.

It runs, in this order and no other:

  1. the deterministic fixture gate (section 11), by invoking the frozen
     fixture command in a subprocess and depositing ``fixtures_report.json``;
  2. the one 20-program smoke run of section 8.1, which measures **runtime,
     peak memory, output bytes and counts and nothing else**, from the
     discarded namespace 1, and whose effect columns are never formed into a
     record, never written and never read;
  3. the budget ladder of section 8.2, written to ``budget.json`` BEFORE the
     reported grid starts, with the measured scaling exponent ``beta``;
  4. the reported grid of section 7 from namespace 0, three constructions on
     every simulated path -- the partial-data ADAPTER under test, the matched
     completed-prefix CPREFIX, and the completed-only NAIVE rule, which is
     **INVALID under informative delay** and is labelled so in every row it
     appears in;
  5. the determinism assertion: one cell block is re-run and its records are
     compared byte for byte;
  6. every reported quantity of section 9 with its exact estimator and its
     Wilson score interval, and the precommitted positive control of 9.4.

SOURCE DECLARATION -- files read while writing this module
----------------------------------------------------------
Read: PROTOCOL.md, cells.json, vband.py, vgen.py, vfixtures.py and src/winstats.py.
Deliberately NOT read, opened or imported: the #11 monitor and enclosure
modules, and the pinned read-only copy of them that sits beside this file.  The
comparison module is the only module permitted to load those, and only after
this one has finished.

WHAT THIS MODULE MAY NOT DO
---------------------------
It may not change a cell, a weight, a delay rule, a seed, an estimator, a flag
rule, a threshold or the positive control; all of those are frozen in
PROTOCOL.md and cells.json and are read from there.  It retains every
unfavourable and inconclusive row (section 13.4).  An unflagged result is
reported as "no exceedance was detected at this resolution", never as "the
bound holds".

CPU only.  No model call, no API call, no network, no new dependency.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math

import platform
import resource
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import vband
import vgen

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CELLS_JSON = HERE / "cells.json"
PROTOCOL_MD = HERE / "PROTOCOL.md"
#: The v2 AMENDMENT.  ``PROTOCOL.md`` section 14 makes a change to an estimator
#: or a reported quantity a new protocol version with its own freeze, and says
#: every result keeps the label of the version that produced it.  A v2 run must
#: therefore bind these bytes, not v1's; ``v2_bindings`` does that, and records
#: base and amended identities as SEPARATE fields so the parent is preserved.
PROTOCOL_V2_MD = HERE / "PROTOCOL_V2.md"
#: The amendment's own version string, as declared in PROTOCOL_V2.md line 3.
V2_VERSION_STRING = "v2-cpu-validation"
CANONICAL_OUT = REPO_ROOT / "results" / "live_ab_validation"
#: The v2 DEVELOPMENT output root.  Separate from ``CANONICAL_OUT`` so that a
#: v2 development artifact can never land in v1's deposit, and so that the
#: reported grid has exactly one permitted destination. Root disposition
#: decision 3: "write to a new explicit v2 output location".
V2_OUT_ROOT = REPO_ROOT / "results" / "live_ab_validation_v2"
GUIDANCE_DOC = REPO_ROOT / "reviews" / "arxiv_live_design_guidance.md"
PINNED_PRIMITIVE = REPO_ROOT / "src" / "winstats.py"

# ---------------------------------------------------------------------------
# PROTOCOL 3: the three compared constructions
# ---------------------------------------------------------------------------
ADAPTER, CPREFIX, NAIVE = "ADAPTER", "CPREFIX", "NAIVE"
CONSTRUCTIONS = (ADAPTER, CPREFIX, NAIVE)
CONSTRUCTION_STATUS = {
    ADAPTER: "the object under test",
    CPREFIX: "valid for its own running target",
    NAIVE: "INVALID under informative delay",
}
CONSTRUCTION_INDEX = {
    ADAPTER: "n = enrolled pairs",
    CPREFIX: "k = longest fully resolved prefix",
    NAIVE: "m = count completed",
}

NO_DECISION, DEPLOY, RETAIN_INCUMBENT, CONFLICT = 0, 1, 2, 3
DECISION_LABEL = {NO_DECISION: "NO_DECISION", DEPLOY: "DEPLOY",
                  RETAIN_INCUMBENT: "RETAIN_INCUMBENT", CONFLICT: "CONFLICT"}

# ---------------------------------------------------------------------------
# PROTOCOL 9: the Wilson score interval, at the frozen z
# ---------------------------------------------------------------------------
WILSON_Z = 1.959963984540054


def wilson(x: int, n: int) -> Tuple[float, float, float]:
    """``(rate, lower, upper)`` of the Wilson score 95% interval.

    These intervals quantify Monte Carlo error of this simulation only.  They
    are not confidence intervals for the statistical guarantee, and a Wilson
    interval lying below a nominal level is not a proof that the level holds.
    """
    if n <= 0:
        return (float("nan"), 0.0, 1.0)
    z = WILSON_Z
    z2 = z * z
    centre = (x + z2 / 2.0) / (n + z2)
    half = z / (n + z2) * math.sqrt(x * (n - x) / n + z2 / 4.0)
    return (x / n, max(0.0, centre - half), min(1.0, centre + half))


def is_flagged(lower: float, nominal: Optional[float]) -> bool:
    """PROTOCOL 9.3: FLAG iff the LOWER Wilson limit exceeds the nominal bound."""
    return nominal is not None and lower > nominal


# ---------------------------------------------------------------------------
# The write guard
# ---------------------------------------------------------------------------
class WriteGuard:
    """Refuses, and aborts on, any write outside the run's own directory.

    PROTOCOL 13.1: the run "writes only inside ``results/live_ab_validation/``;
    a guard refuses any path outside that directory and the run aborts rather
    than writing elsewhere".  Two layers: the directory itself must be a
    ``results/live_ab_validation`` directory, and the REPORTED grid must be the
    repository's own one -- an ad-hoc run is forbidden from writing there at
    all, so a shakedown can never be mistaken for the study.

    THE v2 DEVELOPMENT LOCATION.  Root disposition decision 3 asks the runner to
    "write to a new explicit v2 output location" while "preserving the v1
    reproduction path".  So a directory under ``results/live_ab_validation_v2/``
    is also accepted, and it can NEVER be the reported grid: the reported grid's
    single permitted destination is still ``CANONICAL_OUT`` and nothing else.
    That keeps v1's deposit and v2 development physically separate rather than
    separated by a naming convention.
    """

    def __init__(self, out_dir: Path, reported: bool) -> None:
        resolved = Path(out_dir).expanduser().resolve()
        v1_shaped = (resolved.name == "live_ab_validation"
                     and resolved.parent.name == "results")
        v2_shaped = V2_OUT_ROOT.resolve() in resolved.parents \
            or resolved == V2_OUT_ROOT.resolve()
        if not (v1_shaped or v2_shaped):
            raise SystemExit(
                f"write guard: refusing to run with --out {resolved}; the output "
                f"directory must be a 'results/live_ab_validation' directory, or "
                f"a development directory under {V2_OUT_ROOT}")
        if reported and v2_shaped:
            raise SystemExit(
                f"write guard: {V2_OUT_ROOT} is a DEVELOPMENT location and can "
                f"never hold the reported grid; the reported grid writes only "
                f"to {CANONICAL_OUT}")
        if reported and resolved != CANONICAL_OUT.resolve():
            raise SystemExit(
                f"write guard: a reported grid run must write to {CANONICAL_OUT}, "
                f"not {resolved}")
        if not reported and resolved == CANONICAL_OUT.resolve():
            raise SystemExit(
                "write guard: this run carries grid overrides, so it is NOT the "
                "reported grid and is refused write access to the reported "
                "results directory; give it another --out")
        self.root = resolved
        self.reported = reported
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        target = self.root.joinpath(*parts)
        resolved = target.resolve() if target.exists() else \
            (target.parent.resolve() / target.name)
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise SystemExit(f"write guard: refusing to write outside "
                             f"{self.root}: {target}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    def write_text(self, name: str, text: str) -> Path:
        p = self.path(name)
        p.write_text(text)
        return p

    def write_json(self, name: str, payload) -> Path:
        return self.write_text(name, json.dumps(payload, indent=2,
                                                sort_keys=True) + "\n")

    def total_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())


class _ByteCounter(io.RawIOBase):
    """A sink that counts what is written to it and keeps none of it."""

    def __init__(self) -> None:
        self.count = 0

    def writable(self) -> bool:
        return True

    def write(self, payload) -> int:                     # type: ignore[override]
        self.count += len(payload)
        return len(payload)

    def tell(self) -> int:
        return self.count


class RowSink:
    """Per-trial records, appended incrementally, never held in memory in full.

    A window of the uncompressed stream can be retained so that the determinism
    assertion of PROTOCOL 13.1 can re-run one cell block and compare byte for
    byte.  ``discard`` writes nowhere at all and only counts, which is how the
    smoke run measures output bytes without ever forming a per-trial effect
    record on disk (PROTOCOL 8.1).  ``mtime=0`` keeps the gzip container itself
    byte-identical between runs.
    """

    def __init__(self, path: Optional[Path], header: str, discard: bool = False):
        self.discard = discard
        self.raw_bytes = 0
        self._retain: Optional[List[bytes]] = None
        self._fh = _ByteCounter() if discard else open(path, "wb")
        self._gz = gzip.GzipFile(filename="", mode="wb", fileobj=self._fh,
                                 mtime=0)
        if header:
            self.write(header)

    def write(self, text: str) -> None:
        payload = text.encode()
        self.raw_bytes += len(payload)
        if self._retain is not None:
            self._retain.append(payload)
        self._gz.write(payload)

    def start_retaining(self) -> None:
        self._retain = []

    def stop_retaining(self) -> bytes:
        out = b"".join(self._retain or [])
        self._retain = None
        return out

    def close(self) -> int:
        self._gz.close()
        size = self._fh.tell()
        self._fh.close()
        return int(size)


def peak_rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw) if sys.platform == "darwin" else int(raw) * 1024


# ===========================================================================
# THE LEGAL EVENT SCHEDULE  (v2 amendment; root disposition section B)
# ===========================================================================
# The root's open witness: the v1 runner OMITS the intermediate looks at which a
# completed-data baseline's index changes.  At horizon 1,000, with delays inside
# their declared support, there is a permitted tick at which BOTH baseline lower
# bounds are +0.0133027164 and BOTH deploy gates cross, and the v1 runner never
# evaluates it.  Disposition section B requires v2 to "declare the legal event
# schedule and simultaneous-event batching, include every required completion-
# index change through the fixed finalization window, and record both enrollment
# prefix and elapsed decision time".  This block is that declaration.
#
# THE TICK AXIS.  Time is measured in enrollment ticks and in nothing else.
# Pair j is enrolled at tick j.  Enrollment stops at tick N_max (PROTOCOL 7.3),
# the finalization window is the W = 200 further ticks N_max+1 .. N_max+W, and
# the run ends at the finalization tick N_max+W.  The enrolled prefix at tick t
# is n(t) = min(t, N_max) -- it is PINNED through the whole drain, while
# completions keep arriving.  That gap between a pinned prefix and a moving
# completion index is exactly what v1 could not see.
#
# THE THREE DECLARED SCHEDULES.
#
#   v1_reduced        PRESERVED, NOT PRIMARY.  One look at each enrolled prefix
#                     n = 1 .. N_max, plus one look at the finalization tick.
#                     N_max + 1 looks.  The drain interior is not on the axis at
#                     all.  This is the schedule every deposited v1 result was
#                     produced under; it is kept so that v1 can be reproduced
#                     and reported BESIDE v2, per PROTOCOL 14.
#
#   v2_tick_batched   THE v2 PRIMARY.  One look at every tick t = 1 .. N_max+W.
#                     N_max + W looks.
#                     SIMULTANEOUS-EVENT BATCHING, declared: every event dated
#                     tick t -- the enrollment of pair t, and every reveal, cost
#                     threshold crossing and resolution dated t -- is applied
#                     ATOMICALLY, and exactly one look is taken, at the
#                     resulting end-of-tick state.  No tie order is needed, so
#                     this reading is a function of the path alone and requires
#                     no choice the protocol does not make.
#                     v1_reduced's look set is a SUBSET of this one (ticks
#                     1..N_max and the tick N_max+W), state for state, so no v1
#                     event can be lost and every union-over-looks quantity can
#                     only rise.  ``assert_v2_reduces_to_v1`` checks that.
#
#   v2_event_finest   DECLARED SENSITIVITY, not the primary.  v2_tick_batched
#                     plus every intermediate completion-index state the two
#                     completed-data baselines pass through inside a tick, under
#                     the declared sub-tick order of
#                     ``vgen.completion_event_states``: enrollment first, then
#                     every other event of that tick in ascending enrollment
#                     position.  It is NOT the primary because for NAIVE the
#                     intermediate partial sums depend on that order, so the
#                     reading is one admissible schedule rather than a bound
#                     over all of them; for CPREFIX and for the ADAPTER it is
#                     order-free.  Reported beside the primary, never instead.
#
# WHY THE ADAPTER'S LOOK SET IS THE SAME UNDER BOTH v2 SCHEDULES, and why the
# sub-tick order above is the one that makes this true.  At a FIXED enrolled
# prefix the adapter's denominator and radius are frozen and every further fact
# replaces an enclosure by a subinterval of itself, so sum(lower) is
# nondecreasing and sum(upper) nonincreasing: L_h, L_s rise and U_h falls, and
# every event of PROTOCOL 9.1/9.2 that holds at an intermediate state still
# holds at the end-of-tick state.  The ONE event that can widen the band is the
# enrollment of a new pair, which adds a [-1,+1] enclosure and raises the
# denominator -- and that is precisely why the declared order applies it FIRST
# within its tick.  Under any other order there would be intermediate states at
# prefix t-1 carrying more information than the end of tick t-1, and the
# domination argument would fail.  ``assert_adapter_intratick_domination``
# checks the consequence rather than trusting the argument.
#
# WHAT THIS DOES NOT CHANGE.  No margin, no alpha (.00625), no rho (100), no
# delta (0.03), no n_min (100), no gate, no episode stopping, deadline or
# finalization rule, no cell, no weight, no delay rule, no seed, no estimator,
# no flag rule and not the positive control.  A schedule is a MEASUREMENT
# CONTRACT: it says which states are looked at, not what is computed at one.
# ===========================================================================
SCHEDULE_V1 = "v1_reduced"
SCHEDULE_V2 = "v2_tick_batched"
SCHEDULE_V2_FINEST = "v2_event_finest"
SCHEDULES = (SCHEDULE_V1, SCHEDULE_V2, SCHEDULE_V2_FINEST)
V2_SCHEDULES = (SCHEDULE_V2, SCHEDULE_V2_FINEST)

# ===========================================================================
# THE FINEST SENSITIVITY IS DEFERRED AND DISABLED IN THE PRIMARY PANEL.
#
# Root disposition of 2026-09-21 02:26, decision 1, and COORDINATOR_DECISIONS
# revision 16 item 78.  The root found, and an independent review reproduced, a
# defect in ``vgen.completion_event_states``:
#
#   With resolution ticks (3, 2, 3) the completed prefix is 0 through tick 2 --
#   pair 2 is complete but pair 1 is not, and a PREFIX requires pair 1 -- and
#   then jumps STRAIGHT TO 2 at tick 3 when pair 1 resolves.  The iterator
#   nevertheless emits every k from 1 upward, so it inserts a state k = 1 that
#   is unattainable under ANY tie order.  A synthetic band at an unreachable
#   state can manufacture a crossing the declared process never achieves.
#
# A second, separate limitation: ``_look_fractions`` is keyed by TICK, so a
# finest baseline that fires partway through a tick reports that tick's
# END-OF-BATCH unresolved/revealed fractions rather than its own sub-tick state.
#
# WHAT IS DONE ABOUT IT HERE.  The schedule is REMOVED FROM THE PRIMARY PANEL
# and cannot be selected on the runner's command line: ``--schedule`` offers
# only ``PRIMARY_PANEL_SCHEDULES`` and ``main`` refuses a deferred schedule.
# THE CODE IS PRESERVED, NOT DELETED, together with its failing check, as
# development evidence -- that is the root's explicit instruction.  It remains
# reachable through the library API (``build_series_for``, ``evaluate_trial``)
# so that the preserved failing check in ``tests_validation.py`` can keep
# demonstrating the defect, and so that a future repair has something to repair.
#
# IT IS NOT REPAIRED HERE, and must not be described as repaired, validated, or
# as a legal event schedule.  Tick-batched is the primary.
# ===========================================================================
DEFERRED_SCHEDULES = (SCHEDULE_V2_FINEST,)

#: The schedules a RUN may select.  ``v1_reduced`` stays so v1 is reproducible.
PRIMARY_PANEL_SCHEDULES = tuple(s for s in SCHEDULES
                                if s not in DEFERRED_SCHEDULES)

DEFERRAL_REASON = {
    SCHEDULE_V2_FINEST:
        "DEFERRED AND DISABLED (root disposition 2026-09-21 02:26 decision 1; "
        "COORDINATOR_DECISIONS revision 16 item 78). "
        "vgen.completion_event_states emits completed-prefix states that are "
        "unattainable under any tie order: with resolution ticks (3,2,3) the "
        "prefix jumps 0 -> 2 at tick 3 and the code inserts k=1. Its decision "
        "summaries also report end-of-batch resolution fractions for sub-tick "
        "decisions. Code and failing check PRESERVED as development evidence; "
        "not repaired, not validated, not a legal event schedule.",
}


def is_deferred(schedule: str) -> bool:
    """``True`` for a schedule disabled in the primary panel."""
    return schedule in DEFERRED_SCHEDULES


def check_primary_panel_schedule(schedule: str) -> str:
    """Accept only a schedule the primary panel may run.

    Separate from ``check_schedule`` on purpose: the library must still be able
    to BUILD the deferred schedule so its preserved failing check can keep
    demonstrating the defect. Only RUNS are refused.
    """
    schedule = check_schedule(schedule)
    if is_deferred(schedule):
        raise ValueError(
            f"{schedule!r} is deferred and disabled in the primary panel and "
            f"cannot be selected for a run. {DEFERRAL_REASON[schedule]}")
    return schedule

SCHEDULE_LABEL = {
    SCHEDULE_V1: "v1: one look per enrolled prefix + the finalization look "
                 "(the drain interior is not on the axis)",
    SCHEDULE_V2: "v2 PRIMARY: one look per tick 1..N_max+W, simultaneous events "
                 "batched atomically at the end of their tick",
    SCHEDULE_V2_FINEST: "v2 sensitivity, DEFERRED AND DISABLED in the primary "
                        "panel: v2 primary + every intermediate "
                        "completion-index state. Its iterator emits states "
                        "unattainable under any tie order (see "
                        "DEFERRAL_REASON); preserved as development evidence, "
                        "not a validated or legal event schedule",
}

#: The LIBRARY default stays ``v1_reduced`` on purpose.  ``vlastlook_check.py``,
#: ``vcompare.py`` and every deposited-record audit call into this module to
#: reproduce v1's own numbers, and they must keep getting v1's own numbers.  The
#: RUNNER default is ``v2_tick_batched`` (see ``main``'s ``--schedule``), so the
#: new primary is what a run produces and v1 is one explicit flag away.
LIBRARY_DEFAULT_SCHEDULE = SCHEDULE_V1
RUNNER_DEFAULT_SCHEDULE = SCHEDULE_V2


def check_schedule(schedule: str) -> str:
    if schedule not in SCHEDULES:
        raise ValueError(f"unknown schedule {schedule!r}; declared schedules are "
                         f"{', '.join(SCHEDULES)}")
    return schedule


# ---------------------------------------------------------------------------
# Run configuration
# ---------------------------------------------------------------------------
@dataclass
class RunConfig:
    n_max: int
    namespace: int
    radius: np.ndarray                  # radius[i] = r(i); radius[0] = inf
    n_min: int = vband.N_MIN
    delta: float = vband.DELTA
    trials_per_program: int = vgen.TRIALS_PER_PROGRAM
    schedule: str = LIBRARY_DEFAULT_SCHEDULE
    #: WHICH ENCLOSURE RULE THE PRIMARY EVALUATION EXECUTES.  ``"oracle"`` is
    #: the exact feasible set and is a LABELLED DIAGNOSTIC; ``"operational"``
    #: is the certificate rule the deployed monitor runs and is what an actual
    #: calibration must use.  The default stays ``"oracle"`` ONLY so that every
    #: deposited v1 result reproduces bit for bit under its own config; the v2
    #: calibration entry point sets ``"operational"`` explicitly and records it
    #: in the run receipt, so no run can be operational by accident or oracle
    #: by accident.
    policy: str = "oracle"

    def __post_init__(self) -> None:
        if self.policy not in vgen.POLICIES:
            raise ValueError(f"unknown policy {self.policy!r}; "
                             f"expected one of {vgen.POLICIES}")

    @property
    def horizons(self) -> Tuple[int, ...]:
        """PROTOCOL 7.1: n = 100, 500 and N_max (100 / 500 / 1,000 under T4)."""
        return tuple(sorted({h for h in (100, 500, self.n_max)
                             if h <= self.n_max}))

    @property
    def finalization_tick(self) -> int:
        return self.n_max + vgen.DRAIN_W


def make_config(n_max: int, namespace: int,
                schedule: str = LIBRARY_DEFAULT_SCHEDULE,
                policy: str = "oracle") -> RunConfig:
    """Radii come from ``vband.radius_from_formula``, i.e. from the pinned primitive."""
    radius = np.empty(n_max + 1)
    radius[0] = math.inf
    for n in range(1, n_max + 1):
        radius[n] = vband.radius_from_formula(n)
    return RunConfig(n_max=n_max, namespace=namespace, radius=radius,
                     schedule=check_schedule(schedule), policy=policy)


# ---------------------------------------------------------------------------
# One trial: the three constructions, every look, every reported quantity
# ---------------------------------------------------------------------------
@dataclass
class Series:
    """One construction at every look of the schedule in force.

    ``prefix`` and ``tick`` are kept as SEPARATE recorded quantities and are
    never collapsed into one another (disposition section B: v1 conflated them).

      * ``prefix`` is the enrolled prefix, ``n(t) = min(t, N_max)``: the number
        of randomised pairs the denominator counts.  It is pinned at ``N_max``
        for the whole finalization window.
      * ``tick``   is the ELAPSED DECISION TIME in enrollment ticks, which keeps
        running through the drain after the prefix has stopped.  A decision at
        tick 1,010 of a horizon-1,000 trial has prefix 1,000 and elapsed time
        1,010; under v1 only the first of those two numbers existed.

    ``index`` is the construction's own denominator: ``n`` for the ADAPTER,
    ``k`` for CPREFIX, ``m`` for NAIVE.
    """

    index: np.ndarray       # the construction's own index at each look
    prefix: np.ndarray      # the ENROLLED prefix at each look
    tick: np.ndarray        # the enrollment tick at each look (elapsed time)
    l_h: np.ndarray
    u_h: np.ndarray
    l_s: np.ndarray
    u_s: np.ndarray


def _band(sum_lo: np.ndarray, sum_hi: np.ndarray, index: np.ndarray,
          radius: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """``clip(sum/index -+ r(index), -1, 1)``; at index 0 the full range shows.

    Every enclosure endpoint is an integer, so ``sum`` is exact and this is the
    same IEEE arithmetic ``vband.normal_mixture_band`` performs.
    """
    safe = np.maximum(index, 1).astype(np.float64)
    r = radius[index]
    return (np.clip(sum_lo / safe - r, -1.0, 1.0),
            np.clip(sum_hi / safe + r, -1.0, 1.0))


def build_series(draw: vgen.TrialDraw, cfg: RunConfig
                 ) -> Tuple[Dict[str, Series], np.ndarray, np.ndarray, int]:
    """All three constructions at all 2,001 looks of one trial, v1 SCHEDULE.

    Left exactly as it was, and reachable under that name forever: this is the
    schedule every deposited v1 result was produced under, and ``vlastlook_check``
    and the deposited-record audits call it to reproduce those results.  The v2
    schedules are ``build_series_v2``; ``build_series_for`` dispatches.
    """
    if cfg.policy != "oracle":
        # v1 IS the oracle schedule and the oracle rule; there is no operational
        # v1.  Running it under an operational config would hand back oracle
        # numbers wearing an operational label, which is precisely the class of
        # defect this delivery exists to remove.  Refuse instead.
        raise ValueError(
            f"the v1 schedule is defined only for policy='oracle', not "
            f"{cfg.policy!r}; use the v2 schedule for operational runs")
    n = cfg.n_max
    fin_tick = cfg.finalization_tick
    sums = vgen.adapter_prefix_sums(draw, n)
    resolved, revealed, cprefix, running_max = vgen.resolution_counts(draw, n)
    cum_z, cum_d = vgen.prefix_sums_of_scores(draw)
    naive_h = vgen.completed_sums(draw, draw.z, n)
    naive_s = vgen.completed_sums(draw, draw.dsc, n)
    fin_state = vgen.state_at_age(draw, vgen.finalization_ages(draw, n))
    done_final = draw.resolution_tick <= fin_tick

    prefix = np.append(np.arange(1, n + 1, dtype=np.int64), n)
    tick = np.append(np.arange(1, n + 1, dtype=np.int64), fin_tick)

    # -- ADAPTER: the current full enrolled prefix, enclosures and all -------
    idx_a = prefix
    a_h_lo = np.append(sums.h_lo[1:], float(fin_state.h_lo.sum(dtype=np.int64)))
    a_h_hi = np.append(sums.h_hi[1:], float(fin_state.h_hi.sum(dtype=np.int64)))
    a_s_lo = np.append(sums.s_lo[1:], float(fin_state.s_lo.sum(dtype=np.int64)))
    a_s_hi = np.append(sums.s_hi[1:], float(fin_state.s_hi.sum(dtype=np.int64)))
    l_h, u_h = _band(a_h_lo, a_h_hi, idx_a, cfg.radius)
    l_s, u_s = _band(a_s_lo, a_s_hi, idx_a, cfg.radius)
    out = {ADAPTER: Series(idx_a, prefix, tick, l_h, u_h, l_s, u_s)}

    # -- CPREFIX: the longest fully resolved prefix --------------------------
    k_fin = int(np.searchsorted(running_max, fin_tick, side="right"))
    idx_k = np.append(cprefix[1:], k_fin)
    k_h = cum_z[idx_k]
    k_s = cum_d[idx_k]
    l_h, u_h = _band(k_h, k_h, idx_k, cfg.radius)
    l_s, u_s = _band(k_s, k_s, idx_k, cfg.radius)
    out[CPREFIX] = Series(idx_k, prefix, tick, l_h, u_h, l_s, u_s)

    # -- NAIVE: completed-only.  INVALID under informative delay -------------
    idx_m = np.append(resolved[1:], int(done_final.sum()))
    m_h = np.append(naive_h[1:], float(draw.z[done_final].sum(dtype=np.int64)))
    m_s = np.append(naive_s[1:], float(draw.dsc[done_final].sum(dtype=np.int64)))
    l_h, u_h = _band(m_h, m_h, idx_m, cfg.radius)
    l_s, u_s = _band(m_s, m_s, idx_m, cfg.radius)
    out[NAIVE] = Series(idx_m, prefix, tick, l_h, u_h, l_s, u_s)
    return out, resolved, revealed, sums.updates


def build_series_v2(draw: vgen.TrialDraw, cfg: RunConfig, finest: bool = False
                    ) -> Tuple[Dict[str, Series], np.ndarray, np.ndarray, int]:
    """All three constructions on the FULL tick axis, through the drain window.

    The v2 schedule of the block above.  Every tick ``t = 1 .. N_max+W`` carries
    one look at the end-of-tick state; with ``finest`` the two completed-data
    baselines additionally carry every intermediate completion-index state they
    pass through inside a tick, under the declared sub-tick order.

    The ADAPTER's look set is the tick-batched one under both, which is a
    theorem and not a shortcut -- see the domination argument in the schedule
    declaration and ``assert_adapter_intratick_domination``.
    """
    n = cfg.n_max
    fin_tick = cfg.finalization_tick
    # THE CONFIGURED POLICY, not the oracle by default.  This one argument is
    # the whole of the defect the root named: the comparison tool selected the
    # operational monitor while this path silently kept the exact oracle, so a
    # "matched-policy" claim rested on a runner that never ran the policy.
    sums = vgen.adapter_tick_sums(draw, n, fin_tick, policy=cfg.policy)
    resolved, revealed, _, _ = vgen.resolution_counts(draw, n)
    cpref, naive = vgen.completion_tick_states(draw, n, fin_tick)

    ticks = np.arange(1, fin_tick + 1, dtype=np.int64)
    prefix = np.minimum(ticks, n)

    # -- ADAPTER -----------------------------------------------------------
    l_h, u_h = _band(sums.h_lo[1:], sums.h_hi[1:], prefix, cfg.radius)
    l_s, u_s = _band(sums.s_lo[1:], sums.s_hi[1:], prefix, cfg.radius)
    out = {ADAPTER: Series(prefix, prefix, ticks, l_h, u_h, l_s, u_s)}

    # -- the two completed-data baselines ----------------------------------
    states = {CPREFIX: cpref, NAIVE: naive}
    if finest:
        f_cpref, f_naive = vgen.completion_event_states(draw, n, fin_tick)
        states = {CPREFIX: _merge_states(cpref, f_cpref),
                  NAIVE: _merge_states(naive, f_naive)}
    for name, st in states.items():
        l_h, u_h = _band(st.sum_h, st.sum_h, st.index, cfg.radius)
        l_s, u_s = _band(st.sum_s, st.sum_s, st.index, cfg.radius)
        out[name] = Series(st.index, np.minimum(st.tick, n), st.tick,
                           l_h, u_h, l_s, u_s)
    return out, resolved, revealed, sums.updates


def _merge_states(batched: "vgen.CompletionStates", finest: "vgen.CompletionStates"
                  ) -> "vgen.CompletionStates":
    """Union of the two look sets, ordered by (tick, index).

    The batched set is what the primary looks at; the finest set adds the
    intermediate index values a tick's batch skips over.  Sorting by
    ``(tick, index)`` puts each added state at the tick it is first attained and
    immediately before that tick's end state, which is the order the declared
    sub-tick rule produces.  Duplicates are harmless -- the band at a repeated
    state is the same number -- but are dropped so that look COUNTS mean what
    they say.
    """
    tick = np.concatenate([batched.tick, finest.tick])
    index = np.concatenate([batched.index, finest.index])
    sum_h = np.concatenate([batched.sum_h, finest.sum_h])
    sum_s = np.concatenate([batched.sum_s, finest.sum_s])
    order = np.lexsort((index, tick))
    tick, index = tick[order], index[order]
    sum_h, sum_s = sum_h[order], sum_s[order]
    keep = np.ones(tick.size, dtype=bool)
    if tick.size > 1:
        keep[1:] = ~((tick[1:] == tick[:-1]) & (index[1:] == index[:-1])
                     & (sum_h[1:] == sum_h[:-1]) & (sum_s[1:] == sum_s[:-1]))
    return vgen.CompletionStates(index=index[keep], sum_h=sum_h[keep],
                                 sum_s=sum_s[keep], tick=tick[keep])


def build_series_for(draw: vgen.TrialDraw, cfg: RunConfig,
                     schedule: Optional[str] = None
                     ) -> Tuple[Dict[str, Series], np.ndarray, np.ndarray, int]:
    """Dispatch on the declared schedule.  ``None`` means ``cfg.schedule``."""
    sched = check_schedule(cfg.schedule if schedule is None else schedule)
    if sched == SCHEDULE_V1:
        return build_series(draw, cfg)
    return build_series_v2(draw, cfg, finest=(sched == SCHEDULE_V2_FINEST))


def _look_fractions(draw: vgen.TrialDraw, cfg: RunConfig, tick: int,
                    cache: Dict[int, Tuple[float, float, float, float, int, int]]
                    ) -> Tuple[float, float, float, float, int, int]:
    """Resolution quantities at one look (PROTOCOL 9.5), keyed by its TICK.

    v1 keyed this by look index and reconstructed the tick from it; that only
    worked because v1's look index and tick coincided.  On the v2 axis they do
    not, so the tick is passed in.  The prefix is ``min(tick, N_max)``.
    """
    if tick in cache:
        return cache[tick]
    prefix = min(int(tick), cfg.n_max)
    ages = tick - np.arange(1, prefix + 1, dtype=np.int64)
    sub = vgen.TrialDraw(
        cell=draw.cell, namespace=draw.namespace,
        program_index=draw.program_index, trial_index=draw.trial_index,
        n=prefix, atom=draw.atom[:prefix], z=draw.z[:prefix],
        dsc=draw.dsc[:prefix], d=draw.d[:prefix], f=draw.f[:prefix],
        cand_first=draw.cand_first[:prefix], s_rev=draw.s_rev[:prefix],
        c_rev=draw.c_rev[:prefix], c_pend=draw.c_pend[:prefix],
        a_narrow=draw.a_narrow[:prefix], a_collapse=draw.a_collapse[:prefix])
    st = vgen.state_at_age(sub, ages)
    n_res = int(st.resolved.sum())
    n_unrev = int(st.unrevealed.sum())
    n_point_cost = int(st.cost_collapsed.sum())
    n_narrow = int(st.cost_narrowed.sum())
    value = ((prefix - n_res) / prefix, n_unrev / prefix,
             n_point_cost / prefix, n_narrow / prefix,
             n_res, n_res + n_point_cost)
    cache[tick] = value
    return value


@dataclass
class TrialRecord:
    #: PROTOCOL 9.5's decision prefix: the ENROLLED PREFIX at the first firing
    #: look, capped at ``N_max`` for a non-decider.  Never a time.
    tau: int = 0
    #: v2, disposition section B: the ELAPSED DECISION TIME at the same look, in
    #: enrollment ticks, capped at the finalization tick ``N_max + W`` for a
    #: non-decider.  Distinct from ``tau`` for every decision taken in the drain,
    #: where the prefix is pinned and the clock is not.  Under the v1 schedule
    #: the two can differ only at the finalization look.
    tau_tick: int = 0
    decision: int = NO_DECISION
    decided_at_finalization: bool = False
    #: the decision fired inside the finalization window (tick > N_max).  Always
    #: false under the v1 schedule except at the finalization look itself, which
    #: is what makes the v1/v2 difference countable rather than asserted.
    decided_in_drain: bool = False
    ever_below_h: bool = False
    ever_above_h: bool = False
    ever_below_s: bool = False
    ever_above_s: bool = False
    ever_miscover_h_elig: bool = False
    ever_miscover_s_elig: bool = False
    never_conjunct: bool = False
    never_conjunct_all_looks: bool = False
    unresolved_fraction: float = 0.0
    unrevealed_fraction: float = 0.0
    cost_collapsed_fraction: float = 0.0
    cost_narrowed_fraction: float = 0.0
    n_certified: int = 0
    n_point_resolved: int = 0
    look_prefix: int = 0
    look_tick: int = 0
    #: v2, disposition section B ("retain unresolved units at finalization"):
    #: the PROTOCOL 9.5 resolution quantities at the finalization look, recorded
    #: for EVERY trial whether or not it decided earlier.  v1 recorded them only
    #: at the reporting look, so a trial that decides in the drain -- which is
    #: precisely what v2 makes possible -- would otherwise take its unresolved
    #: record away from the finalization look and leave nothing there.  The
    #: denominator is always N_max; nothing is censored, dropped or imputed.
    final_unresolved_fraction: float = 0.0
    final_unrevealed_fraction: float = 0.0
    final_cost_collapsed_fraction: float = 0.0
    final_cost_narrowed_fraction: float = 0.0
    final_n_certified: int = 0
    final_n_point_resolved: int = 0
    #: looks this construction actually evaluated under the schedule in force
    n_looks: int = 0
    horizon: Dict[int, Tuple[float, ...]] = field(default_factory=dict)

    @property
    def ever_miscover_h(self) -> bool:
        return self.ever_below_h or self.ever_above_h

    @property
    def ever_miscover_s(self) -> bool:
        return self.ever_below_s or self.ever_above_s


def evaluate_trial(draw: vgen.TrialDraw, cfg: RunConfig,
                   schedule: Optional[str] = None
                   ) -> Tuple[Dict[str, TrialRecord], int, int]:
    """Every reported quantity of PROTOCOL section 9 for one trial.

    ``schedule`` names the declared event schedule; ``None`` takes
    ``cfg.schedule``, which defaults to ``v1_reduced`` so that every existing v1
    reproduction path keeps returning v1's own numbers.  Nothing computed AT a
    look depends on the schedule: the same band, the same gates, the same
    truths.  The schedule decides only WHICH states are looked at.

    The returned ``n_looks`` is the number of looks on the SHARED tick axis of
    the schedule in force -- ``N_max + 1`` under v1, ``N_max + W`` under both v2
    schedules -- which is what PROTOCOL 9.5's "looks" column has always counted.
    Under ``v2_event_finest`` the two baselines carry further looks that the
    shared axis does not; ``look_counts`` reports those per construction and
    ``run_block`` accounts for them separately, so no v1 counter changes meaning.
    """
    sched = check_schedule(cfg.schedule if schedule is None else schedule)
    series, resolved, revealed, updates = build_series_for(draw, cfg, sched)
    mu_h, mu_s = draw.cell.mu_h, draw.cell.mu_s
    n = cfg.n_max
    fin_tick = cfg.finalization_tick
    cache: Dict[int, Tuple] = {}
    out: Dict[str, TrialRecord] = {}
    n_looks = int(series[ADAPTER].index.size)
    for name in CONSTRUCTIONS:
        s = series[name]
        rec = TrialRecord()
        rec.n_looks = int(s.index.size)
        below_h = mu_h < s.l_h
        above_h = mu_h > s.u_h
        below_s = mu_s < s.l_s
        above_s = mu_s > s.u_s
        rec.ever_below_h = bool(below_h.any())
        rec.ever_above_h = bool(above_h.any())
        rec.ever_below_s = bool(below_s.any())
        rec.ever_above_s = bool(above_s.any())

        eligible = s.index >= cfg.n_min
        rec.ever_miscover_h_elig = bool((eligible & (below_h | above_h)).any())
        rec.ever_miscover_s_elig = bool((eligible & (below_s | above_s)).any())

        deploy_cond = s.l_h > 0.0
        guard_cond = s.l_s > -cfg.delta
        harm_cond = s.u_h < 0.0
        deploy = eligible & deploy_cond & guard_cond
        harm = eligible & harm_cond
        fired = deploy | harm
        # PROTOCOL 9.2: the same-look conjunction, read out directly.  Both the
        # decision-eligible reading and the literal all-looks reading are kept,
        # because 9.2 states the event over "some look" while every other row of
        # its table is gated at n_min.
        both = eligible & deploy_cond & guard_cond
        rec.never_conjunct = bool((eligible & deploy_cond).any()
                                  and (eligible & guard_cond).any()
                                  and not both.any())
        rec.never_conjunct_all_looks = bool(
            deploy_cond.any() and guard_cond.any()
            and not (deploy_cond & guard_cond).any())

        # -- the decision, and its TWO separate coordinates ------------------
        # PROTOCOL 9.5's tau is the ENROLLED PREFIX.  tau_tick is the ELAPSED
        # DECISION TIME on the same look.  v1 emitted one number for both, which
        # was harmless only because v1 never looked anywhere the two differ.
        if fired.any():
            i = int(np.argmax(fired))
            if deploy[i] and harm[i]:
                rec.decision = CONFLICT
            elif deploy[i]:
                rec.decision = DEPLOY
            else:
                rec.decision = RETAIN_INCUMBENT
            rec.tau = int(s.prefix[i])
            rec.tau_tick = int(s.tick[i])
            rec.decided_at_finalization = bool(int(s.tick[i]) == fin_tick)
            rec.decided_in_drain = bool(int(s.tick[i]) > n)
            report_look = i
        else:
            rec.decision = NO_DECISION
            rec.tau = int(cfg.n_max)          # the capped decision prefix rule
            rec.tau_tick = int(fin_tick)      # its elapsed-time counterpart
            report_look = int(s.index.size) - 1

        (rec.unresolved_fraction, rec.unrevealed_fraction,
         rec.cost_collapsed_fraction, rec.cost_narrowed_fraction,
         rec.n_certified, rec.n_point_resolved) = _look_fractions(
            draw, cfg, int(s.tick[report_look]), cache)
        rec.look_prefix = int(s.prefix[report_look])
        rec.look_tick = int(s.tick[report_look])
        if sched != SCHEDULE_V1:
            (rec.final_unresolved_fraction, rec.final_unrevealed_fraction,
             rec.final_cost_collapsed_fraction, rec.final_cost_narrowed_fraction,
             rec.final_n_certified, rec.final_n_point_resolved) = \
                _look_fractions(draw, cfg, fin_tick, cache)

        # -- fixed-horizon summaries (PROTOCOL 9.6) --------------------------
        # A horizon is a prefix, so a horizon look is the LAST look at or before
        # tick h.  On the v1 axis and on the v2 tick axis that is look h-1; on a
        # finest axis it is found by search.  Stated in ticks so the three
        # schedules read the same rule rather than three coincidences.
        fire_tick = int(s.tick[int(np.argmax(fired))]) if fired.any() else None
        for h in cfg.horizons:
            i = int(np.searchsorted(s.tick, h, side="right")) - 1
            unres = 1.0 - resolved[h] / h
            unrev = 1.0 - revealed[h] / h
            by_h = fire_tick is not None and fire_tick <= h
            rec.horizon[h] = (
                float(s.l_h[i]), float(s.u_h[i]), float(s.l_s[i]), float(s.u_s[i]),
                float(bool((below_h[:i + 1] | above_h[:i + 1]).any())),
                float(bool((below_s[:i + 1] | above_s[:i + 1]).any())),
                float(by_h and rec.decision == DEPLOY),
                float(by_h and rec.decision == RETAIN_INCUMBENT),
                float(unres), float(unrev))
        out[name] = rec
    return out, n_looks, int(updates)


def look_counts(series: Dict[str, Series]) -> Dict[str, int]:
    """Looks actually evaluated, per construction, under the schedule in force."""
    return {name: int(series[name].index.size) for name in CONSTRUCTIONS}


# ---------------------------------------------------------------------------
# The primary's operational rule IS the deployed policy, checked not claimed
# ---------------------------------------------------------------------------
def assert_operational_matches_policy(draw: vgen.TrialDraw, cfg: RunConfig,
                                      ticks: Optional[Sequence[int]] = None
                                      ) -> Dict[str, object]:
    """``vgen``'s vectorised operational states equal ``vpolicy``'s, pair by pair.

    WHY THIS EXISTS.  ``vgen`` reimplements the two certificates in vectorised
    form and duplicates ``vpolicy.CERTIFICATE_EPS`` by value, because the
    generator must not import the policy module.  Duplication that nothing
    checks is how a constant drifts silently, so this compares the two
    implementations on EVERY enrolled pair at the given ticks -- not on a
    sampled pair, and not on one tick.

    Returns the counts it actually checked, so a caller cannot mistake an empty
    comparison for a passing one.
    """
    import vpolicy                                             # noqa: E402

    if vgen.OPERATIONAL_EPS != vpolicy.CERTIFICATE_EPS:
        raise AssertionError(
            f"certificate epsilon drifted: vgen {vgen.OPERATIONAL_EPS!r} != "
            f"vpolicy {vpolicy.CERTIFICATE_EPS!r}")
    if vgen.RTOL != vpolicy.OPERATIONAL_TOL:
        raise AssertionError(
            f"cost tolerance drifted: vgen {vgen.RTOL!r} != "
            f"vpolicy {vpolicy.OPERATIONAL_TOL!r}")

    n = cfg.n_max
    if ticks is None:
        ticks = (1, n // 2, n, n + 1, cfg.finalization_tick)
    pos = np.arange(1, draw.n + 1, dtype=np.int64)
    cap = float(vgen.COST_CAP)
    pairs = 0
    for t in ticks:
        t = int(t)
        enrolled = pos <= min(t, n)
        ages = np.maximum(np.where(enrolled, t - pos, 0), 0)
        st = vgen.state_at_age(draw, ages, policy="operational")
        idx = np.flatnonzero(enrolled)
        ell = vgen.elapsed_cost(draw.c_pend, ages, draw.d)
        for i in idx:
            age, d_i, f_i = int(ages[i]), int(draw.d[i]), int(draw.f[i])
            if age >= d_i:                                     # resolved
                a_i = int(draw.atom[i])
                ep_c = vband.Episode.pending("c", cap).finalized(
                    int(vgen.ATOM_SC[a_i]), float(vgen.ATOM_CC[a_i]))
                ep_i = vband.Episode.pending("i", cap).finalized(
                    int(vgen.ATOM_SI[a_i]), float(vgen.ATOM_CI[a_i]))
            elif age >= f_i:                                   # exactly one revealed
                rev = vband.Episode.pending("rev", cap).finalized(
                    int(draw.s_rev[i]), float(draw.c_rev[i]))
                pen = vband.Episode.pending("pend", cap).with_elapsed_cost(float(ell[i]))
                ep_c, ep_i = (rev, pen) if bool(draw.cand_first[i]) else (pen, rev)
            else:                                              # neither revealed
                ep_c = vband.Episode.pending("c", cap).with_elapsed_cost(0.0)
                ep_i = vband.Episode.pending("i", cap).with_elapsed_cost(0.0)
            h = vpolicy.operational_hierarchy_bounds(ep_c, ep_i)
            sb = vpolicy.operational_success_bounds(ep_c, ep_i)
            got = (float(st.h_lo[i]), float(st.h_hi[i]),
                   float(st.s_lo[i]), float(st.s_hi[i]))
            if got != (h[0], h[1], sb[0], sb[1]):
                raise AssertionError(
                    f"operational mismatch at tick {t}, pair {i + 1}: "
                    f"vgen {got} != vpolicy {(h[0], h[1], sb[0], sb[1])}")
            pairs += 1
    if pairs == 0:
        raise AssertionError("no pair was compared; the check proves nothing")
    return {"ticks_checked": [int(t) for t in ticks], "pair_states_compared": pairs,
            "epsilon": float(vgen.OPERATIONAL_EPS), "tol": float(vgen.RTOL)}


# ---------------------------------------------------------------------------
# The two reductions the v2 schedule must satisfy, checked rather than claimed
# ---------------------------------------------------------------------------
def assert_v2_reduces_to_v1(draw: vgen.TrialDraw, cfg: RunConfig) -> None:
    """v1's look set is a SUBSET of v2's, state for state.

    If this ever fails, v2 is not an amendment of v1 but a different
    measurement, and no comparison between the two means anything.  It checks
    the states, not a summary of them: at every one of v1's ``N_max + 1`` looks,
    the v2 axis must carry a look at the same tick with the same index and the
    same four band endpoints, bitwise.
    """
    v1, _, _, _ = build_series(draw, cfg)
    v2, _, _, _ = build_series_v2(draw, cfg, finest=False)
    for name in CONSTRUCTIONS:
        a, b = v1[name], v2[name]
        pos = np.searchsorted(b.tick, a.tick)
        if not np.array_equal(b.tick[pos], a.tick):
            raise AssertionError(f"{name}: a v1 look tick is absent from the v2 axis")
        for field_name in ("index", "prefix", "l_h", "u_h", "l_s", "u_s"):
            got = getattr(b, field_name)[pos]
            want = getattr(a, field_name)
            if not np.array_equal(got, want):
                bad = int(np.flatnonzero(got != want)[0])
                raise AssertionError(
                    f"{name}.{field_name}: v2 differs from v1 at v1 look {bad} "
                    f"(tick {int(a.tick[bad])}): {got[bad]!r} != {want[bad]!r}")


def assert_adapter_intratick_domination(draw: vgen.TrialDraw, cfg: RunConfig,
                                        ticks: Optional[Sequence[int]] = None
                                        ) -> int:
    """The end-of-tick adapter state dominates every intra-tick state of its tick.

    The declared sub-tick order applies the enrollment of pair ``t`` first, so
    every later event of tick ``t`` sits at the same prefix and can only shrink
    an enclosure.  This drives that claim through ``vgen.state_at_age`` directly:
    for each checked tick it forms the partial state in which only the first
    ``j`` events of the tick have landed and asserts ``sum(lower)`` nondecreasing
    and ``sum(upper)`` nonincreasing in ``j``.  Returns the number of intra-tick
    states checked.
    """
    n, fin = cfg.n_max, cfg.finalization_tick
    if ticks is None:
        ticks = range(1, fin + 1)
    positions = np.arange(1, draw.n + 1, dtype=np.int64)
    checked = 0
    for t in ticks:
        prefix = min(int(t), n)
        ages_now = int(t) - positions[:prefix]
        ages_prev = ages_now - 1                       # before this tick's events
        st_now = vgen.state_at_age(_head(draw, prefix), ages_now)
        st_prev = vgen.state_at_age(_head(draw, prefix), np.maximum(ages_prev, 0))
        moved = np.flatnonzero((st_now.h_lo != st_prev.h_lo)
                               | (st_now.h_hi != st_prev.h_hi)
                               | (st_now.s_lo != st_prev.s_lo)
                               | (st_now.s_hi != st_prev.s_hi))
        if moved.size == 0:
            continue
        lo_h = np.array(st_prev.h_lo, dtype=np.int64)
        hi_h = np.array(st_prev.h_hi, dtype=np.int64)
        lo_s = np.array(st_prev.s_lo, dtype=np.int64)
        hi_s = np.array(st_prev.s_hi, dtype=np.int64)
        prev = (lo_h.sum(), hi_h.sum(), lo_s.sum(), hi_s.sum())
        for j in moved:                                # ascending enrollment position
            lo_h[j], hi_h[j] = st_now.h_lo[j], st_now.h_hi[j]
            lo_s[j], hi_s[j] = st_now.s_lo[j], st_now.s_hi[j]
            cur = (lo_h.sum(), hi_h.sum(), lo_s.sum(), hi_s.sum())
            if cur[0] < prev[0] or cur[2] < prev[2]:
                raise AssertionError(f"tick {t}: sum(lower) fell intra-tick")
            if cur[1] > prev[1] or cur[3] > prev[3]:
                raise AssertionError(f"tick {t}: sum(upper) rose intra-tick")
            prev = cur
            checked += 1
    return checked


def _head(draw: vgen.TrialDraw, prefix: int) -> vgen.TrialDraw:
    """The first ``prefix`` enrolled pairs of a draw, as a draw."""
    return vgen.TrialDraw(
        cell=draw.cell, namespace=draw.namespace,
        program_index=draw.program_index, trial_index=draw.trial_index,
        n=prefix, atom=draw.atom[:prefix], z=draw.z[:prefix],
        dsc=draw.dsc[:prefix], d=draw.d[:prefix], f=draw.f[:prefix],
        cand_first=draw.cand_first[:prefix], s_rev=draw.s_rev[:prefix],
        c_rev=draw.c_rev[:prefix], c_pend=draw.c_pend[:prefix],
        a_narrow=draw.a_narrow[:prefix], a_collapse=draw.a_collapse[:prefix])


# ---------------------------------------------------------------------------
# Accumulators
# ---------------------------------------------------------------------------
TRIAL_FIELDS = ("decision", "tau", "tau_tick", "decided_at_finalization",
                "decided_in_drain",
                "ever_below_h", "ever_above_h", "ever_miscover_h",
                "ever_below_s", "ever_above_s", "ever_miscover_s",
                "ever_miscover_h_elig", "ever_miscover_s_elig",
                "never_conjunct", "never_conjunct_all_looks",
                "unresolved_fraction", "unrevealed_fraction",
                "cost_collapsed_fraction", "cost_narrowed_fraction",
                "n_certified", "n_point_resolved", "look_prefix", "look_tick",
                "final_unresolved_fraction", "final_unrevealed_fraction",
                "final_cost_collapsed_fraction", "final_cost_narrowed_fraction",
                "final_n_certified", "final_n_point_resolved")
HORIZON_FIELDS = ("L_h", "U_h", "L_s", "U_s", "miscover_h_so_far",
                  "miscover_s_so_far", "deploy_by", "retain_by",
                  "unresolved_fraction", "unrevealed_fraction")


class CellAccumulator:
    """Per-cell arrays; the per-trial CSV rows themselves stream to disk."""

    def __init__(self, cell: vgen.CellSpec, n_trials: int, horizons,
                 schedule: str = SCHEDULE_V1):
        self.cell = cell
        self.n_trials = n_trials
        self.horizons = tuple(horizons)
        self.schedule = check_schedule(schedule)
        self.i = 0
        self.data = {c: {f: np.zeros(n_trials) for f in TRIAL_FIELDS}
                     for c in CONSTRUCTIONS}
        self.hor = {c: {h: {f: np.zeros(n_trials) for f in HORIZON_FIELDS}
                        for h in self.horizons} for c in CONSTRUCTIONS}

    def add(self, records: Dict[str, TrialRecord]) -> None:
        i = self.i
        for c in CONSTRUCTIONS:
            rec = records[c]
            d = self.data[c]
            d["decision"][i] = rec.decision
            d["tau"][i] = rec.tau
            d["tau_tick"][i] = rec.tau_tick
            d["decided_at_finalization"][i] = rec.decided_at_finalization
            d["decided_in_drain"][i] = rec.decided_in_drain
            d["ever_below_h"][i] = rec.ever_below_h
            d["ever_above_h"][i] = rec.ever_above_h
            d["ever_miscover_h"][i] = rec.ever_miscover_h
            d["ever_below_s"][i] = rec.ever_below_s
            d["ever_above_s"][i] = rec.ever_above_s
            d["ever_miscover_s"][i] = rec.ever_miscover_s
            d["ever_miscover_h_elig"][i] = rec.ever_miscover_h_elig
            d["ever_miscover_s_elig"][i] = rec.ever_miscover_s_elig
            d["never_conjunct"][i] = rec.never_conjunct
            d["never_conjunct_all_looks"][i] = rec.never_conjunct_all_looks
            d["unresolved_fraction"][i] = rec.unresolved_fraction
            d["unrevealed_fraction"][i] = rec.unrevealed_fraction
            d["cost_collapsed_fraction"][i] = rec.cost_collapsed_fraction
            d["cost_narrowed_fraction"][i] = rec.cost_narrowed_fraction
            d["n_certified"][i] = rec.n_certified
            d["n_point_resolved"][i] = rec.n_point_resolved
            d["look_prefix"][i] = rec.look_prefix
            d["look_tick"][i] = rec.look_tick
            d["final_unresolved_fraction"][i] = rec.final_unresolved_fraction
            d["final_unrevealed_fraction"][i] = rec.final_unrevealed_fraction
            d["final_cost_collapsed_fraction"][i] = rec.final_cost_collapsed_fraction
            d["final_cost_narrowed_fraction"][i] = rec.final_cost_narrowed_fraction
            d["final_n_certified"][i] = rec.final_n_certified
            d["final_n_point_resolved"][i] = rec.final_n_point_resolved
            for h in self.horizons:
                vals = rec.horizon[h]
                for f, v in zip(HORIZON_FIELDS, vals):
                    self.hor[c][h][f][i] = v
        self.i += 1


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------
def _fmt(v: float) -> str:
    if isinstance(v, (bool, np.bool_)):
        return "1" if v else "0"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    f = float(v)
    if math.isnan(f):
        return "NA"
    if math.isinf(f):
        return "inf" if f > 0 else "-inf"
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return repr(f)


#: v1's per-trial record layout, frozen.  A v1 re-run must reproduce the
#: deposited ``trials.csv`` byte for byte, so this string may not be touched.
TRIAL_HEADER = ("cell,law,delay,program,trial,construction,construction_status,"
                "decision,tau,decided_at_finalization,ever_below_h,ever_above_h,"
                "ever_miscover_h,ever_below_s,ever_above_s,ever_miscover_s,"
                "ever_miscover_h_decision_eligible,ever_miscover_s_decision_eligible,"
                "never_conjunct,never_conjunct_all_looks,unresolved_fraction,"
                "unrevealed_fraction,cost_collapsed_fraction,cost_narrowed_fraction,"
                "n_certified,n_point_resolved,look_prefix\n")

#: v2's layout.  ``tau`` is gone as a bare name, because that single column is
#: exactly the conflation the disposition names: it is split into ``tau_prefix``
#: (enrolled pairs) and ``tau_tick`` (elapsed enrollment ticks), and the look the
#: record is taken at likewise carries both coordinates.  ``decided_in_drain``
#: makes the new looks countable rather than merely available.
TRIAL_HEADER_V2 = (
    "schedule,cell,law,delay,program,trial,construction,construction_status,"
    "decision,tau_prefix,tau_tick,decided_at_finalization,decided_in_drain,"
    "ever_below_h,ever_above_h,"
    "ever_miscover_h,ever_below_s,ever_above_s,ever_miscover_s,"
    "ever_miscover_h_decision_eligible,ever_miscover_s_decision_eligible,"
    "never_conjunct,never_conjunct_all_looks,unresolved_fraction,"
    "unrevealed_fraction,cost_collapsed_fraction,cost_narrowed_fraction,"
    "n_certified,n_point_resolved,look_prefix,look_tick,n_looks,"
    "final_unresolved_fraction,final_unrevealed_fraction,"
    "final_cost_collapsed_fraction,final_cost_narrowed_fraction,"
    "final_n_certified,final_n_point_resolved\n")


def trial_header(schedule: str = SCHEDULE_V1) -> str:
    return TRIAL_HEADER if check_schedule(schedule) == SCHEDULE_V1 \
        else TRIAL_HEADER_V2


def trial_rows(cell, program, trial, records: Dict[str, TrialRecord],
               schedule: str = SCHEDULE_V1) -> str:
    """One CSV row per construction, in the layout of the schedule in force."""
    v2 = check_schedule(schedule) != SCHEDULE_V1
    out = []
    for c in CONSTRUCTIONS:
        r = records[c]
        head = [schedule] if v2 else []
        head += [cell.id, cell.law, cell.delay, str(program), str(trial), c,
                 CONSTRUCTION_STATUS[c], DECISION_LABEL[r.decision], str(r.tau)]
        if v2:
            head += [str(r.tau_tick)]
        head += [_fmt(r.decided_at_finalization)]
        if v2:
            head += [_fmt(r.decided_in_drain)]
        head += [
            _fmt(r.ever_below_h),
            _fmt(r.ever_above_h), _fmt(r.ever_miscover_h), _fmt(r.ever_below_s),
            _fmt(r.ever_above_s), _fmt(r.ever_miscover_s),
            _fmt(r.ever_miscover_h_elig), _fmt(r.ever_miscover_s_elig),
            _fmt(r.never_conjunct), _fmt(r.never_conjunct_all_looks),
            _fmt(r.unresolved_fraction), _fmt(r.unrevealed_fraction),
            _fmt(r.cost_collapsed_fraction), _fmt(r.cost_narrowed_fraction),
            str(r.n_certified), str(r.n_point_resolved), str(r.look_prefix)]
        if v2:
            head += [str(r.look_tick), str(r.n_looks),
                     _fmt(r.final_unresolved_fraction),
                     _fmt(r.final_unrevealed_fraction),
                     _fmt(r.final_cost_collapsed_fraction),
                     _fmt(r.final_cost_narrowed_fraction),
                     str(r.final_n_certified), str(r.final_n_point_resolved)]
        out.append(",".join(head) + "\n")
    return "".join(out)


@dataclass
class BlockCounts:
    programs: int = 0
    trials: int = 0
    pairs: int = 0
    looks: int = 0
    band_evaluations: int = 0
    enclosure_updates: int = 0
    #: looks summed over the three constructions.  Under v1 and under the v2
    #: primary the three share one axis and this is exactly ``3 * looks``, so it
    #: is suppressed from the emitted record and no v1 counter changes; under
    #: ``v2_event_finest`` the baselines carry more and it is reported.
    construction_looks: int = 0

    def add(self, other: "BlockCounts") -> None:
        self.programs += other.programs
        self.trials += other.trials
        self.pairs += other.pairs
        self.looks += other.looks
        self.band_evaluations += other.band_evaluations
        self.enclosure_updates += other.enclosure_updates
        self.construction_looks += other.construction_looks

    def as_dict(self) -> Dict[str, int]:
        out = {"programs": self.programs, "trials": self.trials,
               "enrolled_pairs": self.pairs, "looks": self.looks,
               "band_evaluations": self.band_evaluations,
               "enclosure_updates": self.enclosure_updates}
        if self.construction_looks != self.looks * len(CONSTRUCTIONS):
            out["construction_looks"] = self.construction_looks
        return out


def run_block(cell: vgen.CellSpec, programs: Sequence[int], cfg: RunConfig,
              sink: Optional[RowSink],
              accum: Optional[CellAccumulator]) -> BlockCounts:
    """One (cell, block of programs).  Records stream out; nothing is buffered."""
    counts = BlockCounts()
    for program in programs:
        for trial in range(cfg.trials_per_program):
            draw = vgen.draw_trial(cell, program, trial, n_max=cfg.n_max,
                                   namespace=cfg.namespace)
            records, n_looks, updates = evaluate_trial(draw, cfg)
            counts.trials += 1
            counts.pairs += cfg.n_max
            counts.looks += n_looks
            total = sum(records[c].n_looks for c in CONSTRUCTIONS)
            counts.construction_looks += total
            counts.band_evaluations += total * 2
            counts.enclosure_updates += updates
            if sink is not None:
                sink.write(trial_rows(cell, program, trial, records,
                                      cfg.schedule))
            if accum is not None:
                accum.add(records)
        counts.programs += 1
    return counts


# ---------------------------------------------------------------------------
# PROTOCOL 9: the reported tables
# ---------------------------------------------------------------------------
NOMINAL_EVER_MISCOVER = vband.ALPHA_GATE            # 0.00625
NOMINAL_TRIAL_ERROR = vband.ALPHA_PER_TRIAL         # 0.0125
NOMINAL_FAMILY = vband.PROGRAM_ALPHA                # 0.05


def _rate_row(cell, construction, extra: Dict[str, object], x: int, n: int,
              nominal: Optional[float]) -> Dict[str, object]:
    rate, lo, hi = wilson(int(x), int(n))
    row = {"cell": cell.id, "law": cell.law, "law_name": cell.law_name,
           "delay": cell.delay, "construction": construction,
           "construction_status": CONSTRUCTION_STATUS[construction]}
    row.update(extra)
    row.update({"x": int(x), "N": int(n), "rate": rate,
                "wilson_lo": lo, "wilson_hi": hi,
                "nominal": "" if nominal is None else nominal,
                "flagged": int(is_flagged(lo, nominal))})
    return row


def miscoverage_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    n = acc.n_trials
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        for gate, mu, below, above, elig in (
                ("hierarchy", cell.mu_h, d["ever_below_h"], d["ever_above_h"],
                 d["ever_miscover_h_elig"]),
                ("success", cell.mu_s, d["ever_below_s"], d["ever_above_s"],
                 d["ever_miscover_s_elig"])):
            miscover = (below > 0) | (above > 0)
            for event, vec in (("ever_miscover", miscover),
                               ("ever_below", below > 0),
                               ("ever_above", above > 0)):
                rows.append(_rate_row(
                    cell, c, {"gate": gate, "mu": mu, "looks": "all",
                              "event": event},
                    int(vec.sum()), n, NOMINAL_EVER_MISCOVER))
            rows.append(_rate_row(
                cell, c, {"gate": gate, "mu": mu,
                          "looks": "decision_eligible", "event": "ever_miscover"},
                int((elig > 0).sum()), n, NOMINAL_EVER_MISCOVER))
    return rows


def decision_rows(acc: CellAccumulator, delta: float) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    n = acc.n_trials
    truth_deploy_correct = (cell.mu_h > 0.0) and (cell.mu_s > -delta)
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        dec = d["decision"]
        deploy = dec == DEPLOY
        retain = dec == RETAIN_INCUMBENT
        conflict = dec == CONFLICT
        none = dec == NO_DECISION
        false_deploy = deploy & (not truth_deploy_correct)
        correct_deploy = deploy & truth_deploy_correct
        false_harm = retain & (cell.mu_h >= 0.0)
        any_err = false_deploy | false_harm
        # PROTOCOL 9.2's two identities, asserted as this tabulates
        if int(false_harm.sum()) != int(retain.sum()):
            raise AssertionError(
                f"{cell.id}/{c}: mu_h = {cell.mu_h} >= 0, so every "
                f"RETAIN_INCUMBENT must be a false harm")
        if truth_deploy_correct:
            if int(false_deploy.sum()) != 0:
                raise AssertionError(
                    f"{cell.id}/{c}: false_deploy must be exactly 0 where DEPLOY "
                    f"is the correct decision")
        elif int(false_deploy.sum()) != int(deploy.sum()):
            raise AssertionError(
                f"{cell.id}/{c}: every DEPLOY in this cell is an error")
        family = any_err.reshape(-1, vgen.TRIALS_PER_PROGRAM).any(axis=1)
        for quantity, vec, unit, nominal in (
                ("false_deploy", false_deploy, "trial", NOMINAL_EVER_MISCOVER),
                ("false_harm", false_harm, "trial", NOMINAL_EVER_MISCOVER),
                ("any_erroneous_trial", any_err, "trial", NOMINAL_TRIAL_ERROR),
                ("correct_deploy", correct_deploy, "trial", None),
                ("deploy", deploy, "trial", None),
                ("retain_incumbent", retain, "trial", None),
                ("no_decision", none, "trial", None),
                ("conflict", conflict, "trial", None),
                ("never_conjunct", d["never_conjunct"] > 0, "trial", None),
                ("never_conjunct_all_looks", d["never_conjunct_all_looks"] > 0,
                 "trial", None),
                ("decided_at_finalization", d["decided_at_finalization"] > 0,
                 "trial", None)) + (
                # v2 only: decisions taken inside the finalization window, i.e.
                # at the looks v1 had no axis for.  This is the count that makes
                # the schedule repair audit itself.
                (("decided_in_drain", d["decided_in_drain"] > 0, "trial", None),)
                if acc.schedule != SCHEDULE_V1 else ()):
            rows.append(_rate_row(cell, c, {"quantity": quantity, "unit": unit},
                                  int(np.count_nonzero(vec)), n, nominal))
        rows.append(_rate_row(
            cell, c, {"quantity": "family_any_erroneous", "unit": "program"},
            int(family.sum()), len(family), NOMINAL_FAMILY))
    return rows


def _quartiles(v: np.ndarray) -> Tuple[float, float, float]:
    if v.size == 0:
        return (float("nan"),) * 3
    q = np.percentile(v, [25, 50, 75])
    return (float(q[0]), float(q[1]), float(q[2]))


#: The two coordinates a decision carries, and the cap each one takes for a
#: non-deciding trial.  v1 emitted only the first row and called it "tau"; the
#: disposition requires both, separately, everywhere a decision time is emitted.
DECISION_COORDINATES = (
    ("tau", "ENROLLED PREFIX at the deciding look, in enrolled pairs. Pinned "
            "at N_max through the whole drain, so it is NOT the baseline "
            "sample size and NOT elapsed time (never wall clock)"),
    ("tau_tick", "ELAPSED CALENDAR TICK of the same look, in enrollment ticks. "
                 "Keeps advancing through the drain after the prefix is pinned "
                 "(a simulation clock, never wall clock, never a latency)"),
)


def decision_time_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    """One row per (construction, coordinate).

    Under v1 the ``tau_tick`` row is not emitted, so a v1 re-run reproduces the
    deposited ``decision_time.csv`` byte for byte.  Under v2 both coordinates
    are emitted and are labelled with their own unit, because in the drain the
    prefix is pinned at ``N_max`` while the clock keeps running: a decision at
    tick 1,010 of a 1,000-pair trial has ``tau = 1,000`` and ``tau_tick = 1,010``
    and reporting either one alone misstates the other.
    """
    rows = []
    cell = acc.cell
    coords = DECISION_COORDINATES if acc.schedule != SCHEDULE_V1 \
        else DECISION_COORDINATES[:1]
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        decided = d["decision"] != NO_DECISION
        for field_name, unit in coords:
            capped = d[field_name]
            cond = d[field_name][decided]
            cq = _quartiles(capped)
            kq = _quartiles(cond)
            row = {
                "cell": cell.id, "law": cell.law, "law_name": cell.law_name,
                "delay": cell.delay, "construction": c,
                "construction_status": CONSTRUCTION_STATUS[c],
                "unit": unit,
                "n_trials": acc.n_trials, "n_deciding": int(decided.sum()),
                "deciding_fraction": float(decided.mean()),
                "capped_fraction": float(1.0 - decided.mean()),
                "capped_q1": cq[0], "capped_median": cq[1], "capped_q3": cq[2],
                "conditional_q1": kq[0], "conditional_median": kq[1],
                "conditional_q3": kq[2]}
            if acc.schedule != SCHEDULE_V1:
                row = {"schedule": acc.schedule, "coordinate": field_name, **row}
            rows.append(row)
    return rows


def unresolved_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    # v2 also reports the PROTOCOL 7.3 finalization record for EVERY trial, not
    # only for the non-deciders: v2 lets a trial decide inside the drain, and
    # without these rows such a trial would leave no record at finalization.
    extra = (("look_tick", "final_unresolved_fraction",
              "final_unrevealed_fraction", "final_cost_collapsed_fraction",
              "final_cost_narrowed_fraction", "final_n_certified",
              "final_n_point_resolved") if acc.schedule != SCHEDULE_V1 else ())
    for c in CONSTRUCTIONS:
        d = acc.data[c]
        for quantity in ("unresolved_fraction", "unrevealed_fraction",
                         "cost_collapsed_fraction", "cost_narrowed_fraction",
                         "n_certified", "n_point_resolved", "look_prefix") + extra:
            v = d[quantity]
            q = _quartiles(v)
            rows.append({
                "cell": cell.id, "law": cell.law, "law_name": cell.law_name,
                "delay": cell.delay, "construction": c,
                "construction_status": CONSTRUCTION_STATUS[c],
                "quantity": quantity, "N": acc.n_trials, "mean": float(v.mean()),
                "q1": q[0], "median": q[1], "q3": q[2]})
    return rows


def horizon_rows(acc: CellAccumulator) -> List[Dict[str, object]]:
    rows = []
    cell = acc.cell
    n = acc.n_trials
    rate_fields = {"miscover_h_so_far": NOMINAL_EVER_MISCOVER,
                   "miscover_s_so_far": NOMINAL_EVER_MISCOVER,
                   "deploy_by": None, "retain_by": None}
    for c in CONSTRUCTIONS:
        for h in acc.horizons:
            for f in HORIZON_FIELDS:
                v = acc.hor[c][h][f]
                base = {"cell": cell.id, "law": cell.law,
                        "law_name": cell.law_name, "delay": cell.delay,
                        "construction": c,
                        "construction_status": CONSTRUCTION_STATUS[c],
                        "horizon": h, "quantity": f, "N": n}
                if f in rate_fields:
                    x = int(np.count_nonzero(v))
                    rate, lo, hi = wilson(x, n)
                    nominal = rate_fields[f]
                    base.update({"kind": "rate", "mean": rate, "q1": "",
                                 "median": "", "q3": "", "x": x, "rate": rate,
                                 "wilson_lo": lo, "wilson_hi": hi,
                                 "nominal": "" if nominal is None else nominal,
                                 "flagged": int(is_flagged(lo, nominal))})
                else:
                    q = _quartiles(v)
                    base.update({"kind": "distribution", "mean": float(v.mean()),
                                 "q1": q[0], "median": q[1], "q3": q[2],
                                 "x": "", "rate": "", "wilson_lo": "",
                                 "wilson_hi": "", "nominal": "", "flagged": 0})
                rows.append(base)
    return rows


def write_csv(guard: WriteGuard, name: str, rows: List[Dict[str, object]],
              note: str) -> None:
    if not rows:
        guard.write_text(name, f"# {note}\n")
        return
    cols = list(rows[0].keys())
    lines = [f"# {note}"]
    lines.append(",".join(cols))
    for r in rows:
        lines.append(",".join(_fmt(r[c]) if not isinstance(r[c], str)
                              else r[c] for c in cols))
    guard.write_text(name, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# PROTOCOL 8.1: the smoke run, and 8.2: the budget ladder
# ---------------------------------------------------------------------------
SMOKE_PERMITTED_FILES = ("timing.json",)
SMOKE_PERMITTED_KEYS = {
    "protocol_smoke", "namespace", "points", "cell", "programs", "N_max",
    "seconds", "seconds_per_program", "peak_rss_bytes", "output_bytes",
    "record_bytes_measured_not_written", "trials", "enrolled_pairs", "looks",
    "band_evaluations", "enclosure_updates", "enclosure_updates_per_pair",
    "measures_only", "seeds", "note", "total_seconds", "total_programs",
    # v2: the name of the schedule that was measured.  A label, not an effect
    # column -- but a required one, because a resource projection taken under
    # one schedule must never be read as the cost of another.
    "event_schedule",
    # v2 REPAIR 1 (root resource audit 2026-09-21 03:43, required repair 1).
    # ``run_smoke`` writes these three and the allowlist did not contain them,
    # so ``assert_smoke_holds_no_effect_record`` exited on 'design' and THE
    # RUNNER REJECTED ITS OWN OUTPUT.  They are added DELIBERATELY and they are
    # all non-outcome metadata:
    #   design           -- prose naming the measurement design that was run
    #   balanced         -- bool: was that design the balanced 2x2
    #   unique_programs  -- int: how many distinct program indices were timed
    # The exclusion of effect columns is unchanged: no coverage number, no
    # decision rate, no estimate and no band endpoint is permitted here, and
    # nothing below is one.
    "design", "balanced", "unique_programs", "unique_program_indices",
    # v2 REPAIR 2 metadata, all counts and labels (see ``select_tier``).
    "program_index_rule", "reference_workload",
}


def run_smoke(guard: WriteGuard, programs: int, verbose: bool = True,
              schedule: str = SCHEDULE_V1) -> Dict[str, object]:
    """PROTOCOL 8.1: exactly one 20-program smoke run, measuring only.

    Its seeds come from namespace 1 and are discarded.  Its effect columns are
    computed (they are what makes the timing representative) but are never
    formed into a per-trial record on disk and are never read: the only values
    that leave this function are seconds, bytes, memory and counts.

    ``schedule`` must be the schedule the grid will actually run, or the budget
    ladder is projecting the cost of a different runner.  v2 evaluates
    ``N_max + W`` looks per trial instead of ``N_max + 1``, so its cost is not
    v1's and must not be read off v1's measurement.

    THE SPLIT IS NOW SCHEDULE-DEPENDENT, and that is the repair.  Root
    disposition decision 3 and COORDINATOR_DECISIONS revision 16 item 79: "the
    current smoke path still uses the old confounded resource design; wire the
    balanced plan into the v2 path while preserving the v1 reproduction path."

      * ``v1_reduced`` keeps the ORIGINAL CONFOUNDED SPLIT -- C1 at 2,000 and
        C2 at 1,000 -- because every deposited v1 budget was selected from it
        and changing it would silently change what v1 reproduction means.
      * every v2 schedule uses the BALANCED 2x2 -- C1 and C2 each crossed with
        horizons 1,000 and 2,000, five programs per group at 20 programs.

    Why the old split could not stay: it varies cell and horizon together, so a
    ratio between its two groups is a sum of a cell effect and a horizon effect
    and cannot identify either. The balanced design is what makes the marginal
    effects of ``vresource_check`` separable, and the budget ladder must be
    projected from the design that was actually analysed.
    """
    schedule = check_schedule(schedule)
    if schedule == SCHEDULE_V1:
        half = programs // 2
        split = ((vgen.CELL_BY_ID["C1"], max(half, 1), 2000),
                 (vgen.CELL_BY_ID["C2"], programs - max(half, 1), 1000))
        design = ("v1 reproduction: the ORIGINAL CONFOUNDED split, C1 at 2,000 "
                  "and C2 at 1,000. Preserved unchanged so that v1's deposited "
                  "budget selection stays reproducible. Cell and horizon vary "
                  "together, so its ratio identifies neither on its own.")
    else:
        per = max(programs // 4, 1)
        split = ((vgen.CELL_BY_ID["C1"], per, 1000),
                 (vgen.CELL_BY_ID["C1"], per, 2000),
                 (vgen.CELL_BY_ID["C2"], per, 1000),
                 (vgen.CELL_BY_ID["C2"], programs - 3 * per, 2000))
        design = ("v2 BALANCED 2x2: cells C1 and C2 each crossed with horizons "
                  "1,000 and 2,000, five programs per group at 20 programs. "
                  "Cell and horizon are orthogonal, so their marginal effects "
                  "are separately estimable.")
    points = []
    total_seconds = 0.0
    program_base = 0
    seed_identities: set = set()
    program_indices: set = set()
    # v2 REPAIR 3 (root resource audit, required repair 3): THE INDEXING RULE IS
    # SCHEDULE-SPECIFIC, because the new rule silently moved v1's seeds.
    #
    #   v1: each group starts its program indices at 0, which is what the
    #       deposited v1 smoke actually drew.  The old C2 group used 0-9; the
    #       incrementing rule gave it 10-19, so the "preserved" v1 reproduction
    #       path was NOT seed-equivalent.  It is restored here.  v1's two groups
    #       are DIFFERENT CELLS, so group-local indices still name distinct
    #       streams -- the RNG key includes the cell.
    #   v2: the balanced design visits the SAME cell twice, so two groups drawing
    #       the same program indices would time the same streams twice rather
    #       than 20 distinct programs.  The incrementing base is required there
    #       and is kept.
    #
    # Deposited v1 result files are untouched either way; this is about the
    # executable reproduction path.
    group_local_indices = (schedule == SCHEDULE_V1)
    for cell, n_programs, n_max in split:
        if n_programs <= 0:
            continue
        cfg = make_config(n_max, vgen.NAMESPACE_SMOKE, schedule=schedule)
        sink = RowSink(None, trial_header(schedule), discard=True)
        first = 0 if group_local_indices else program_base
        t0 = time.perf_counter()
        counts = run_block(cell, range(first, first + n_programs),
                           cfg, sink, None)
        seconds = time.perf_counter() - t0
        program_base += n_programs
        for idx in range(first, first + n_programs):
            seed_identities.add((cell.id, idx))
            program_indices.add(idx)
        record_bytes = sink.close()
        total_seconds += seconds
        points.append({
            "cell": cell.id, "programs": n_programs, "N_max": n_max,
            "seconds": seconds, "seconds_per_program": seconds / n_programs,
            "record_bytes_measured_not_written": int(record_bytes),
            "trials": counts.trials, "enrolled_pairs": counts.pairs,
            "looks": counts.looks, "band_evaluations": counts.band_evaluations,
            "enclosure_updates": counts.enclosure_updates,
            "enclosure_updates_per_pair":
                counts.enclosure_updates / max(counts.pairs, 1)})
        if verbose:
            print(f"  smoke {cell.id} N_max={n_max}: {n_programs} programs in "
                  f"{seconds:.2f}s ({seconds / n_programs:.3f}s/program)")
    record = {
        "protocol_smoke": programs == 20,
        "event_schedule": schedule,
        "design": design,
        "balanced": schedule != SCHEDULE_V1,
        # Counted, not asserted.  ``unique_programs`` is the number of distinct
        # (cell, program) SEED IDENTITIES actually timed; ``unique_program_indices``
        # is the number of distinct program indices, which is smaller whenever a
        # design reuses an index across cells (v1 does).  Two fields because
        # collapsing them once let a repetition count be read as an independent
        # experimental outcome (root resource audit, 2026-09-21).
        "unique_programs": len(seed_identities),
        "unique_program_indices": len(program_indices),
        "program_index_rule": (
            "group-local: every group starts at program index 0, which is what "
            "the deposited v1 smoke drew"
            if group_local_indices else
            "incrementing: each group continues where the last stopped, because "
            "the balanced design visits the same cell twice"),
        "namespace": vgen.NAMESPACE_SMOKE,
        "measures_only": ["wall_clock_seconds", "peak_rss", "output_bytes",
                          "counts"],
        "seeds": "discarded, never reused",
        "note": ("effect columns are never formed into a record here and are "
                 "never read; they play no part in choosing anything"),
        "points": points,
        "total_seconds": total_seconds,
        "total_programs": sum(p["programs"] for p in points),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    guard.write_json("smoke/timing.json", record)
    return record


def assert_smoke_holds_no_effect_record(guard: WriteGuard) -> None:
    """PROTOCOL 8.1's own requirement on this module, checked before the grid."""
    smoke_dir = guard.path("smoke")
    present = sorted(p.name for p in smoke_dir.iterdir() if p.is_file())
    unexpected = [p for p in present if p not in SMOKE_PERMITTED_FILES]
    if unexpected:
        raise SystemExit(f"the smoke directory holds files that are not a "
                         f"timing record: {unexpected}")
    for name in present:
        payload = json.loads((smoke_dir / name).read_text())
        stack = [payload]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    if k not in SMOKE_PERMITTED_KEYS:
                        raise SystemExit(
                            f"the smoke record carries the key {k!r}, which is "
                            f"not a timing, memory, byte or count field")
                    stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)


def aggregate_horizon_costs(smoke: Dict[str, object]) -> Dict[str, object]:
    """v2 REPAIR 2: collapse the balanced design to one cost per horizon,
    WITHOUT discarding a cell.

    THE DEFECT THIS REPLACES.  ``select_tier`` built ``{p['N_max']: p for p in
    smoke['points']}``.  On the balanced 2x2 that dict has four entries written
    into two keys, and the later C2 group SILENTLY OVERWROTE C1.  Half the
    balanced timing design never reached the budget, and the root's fixture
    showed the overwrite is total: multiplying both C1 costs by 1,000 changed
    no output at all.

    THE RULE, which is the root's and is binding (root disposition ranked
    action 2; COORDINATOR_DECISIONS revision 17 item 85):

      * **retain both cell inputs at each horizon**, and
      * **project from the MAXIMUM measured cell cost at each horizon**.

    It is outcome-independent -- it reads seconds only, never an effect column
    -- and it is CONSERVATIVE: it projects from the more expensive cell, so a
    tier admitted under it is admitted under either cell's own cost.

    It is a RESOURCE rule and nothing more. It is not an inferential guarantee,
    it is not a statement that the cells differ, and it is not a reason to
    change the scientific horizon after outcomes are known.

    The v1 path does not pass through here at all; see ``select_tier``.
    """
    by_horizon: Dict[int, Dict[str, object]] = {}
    for p in smoke["points"]:
        h = int(p["N_max"])
        slot = by_horizon.setdefault(h, {"horizon": h, "cells": {}})
        cells = slot["cells"]                               # type: ignore[index]
        cell = str(p["cell"])
        if cell in cells:                                   # pragma: no cover
            raise SystemExit(
                f"two smoke points share (cell={cell}, N_max={h}); the "
                f"balanced design must visit each (cell, horizon) once, and "
                f"collapsing them is the defect this function exists to "
                f"prevent")
        cells[cell] = {
            "seconds": p["seconds"],
            "seconds_per_program": p["seconds_per_program"],
            "programs": p["programs"],
            "record_bytes_measured_not_written":
                p["record_bytes_measured_not_written"],
        }
    for h, slot in by_horizon.items():
        cells = slot["cells"]                               # type: ignore[index]
        costs = {c: v["seconds_per_program"] for c, v in cells.items()}
        worst = max(costs, key=lambda c: costs[c])
        slot["seconds_per_program_by_cell"] = costs
        slot["selected_cell"] = worst
        slot["seconds_per_program"] = costs[worst]
        slot["cells_retained"] = sorted(cells)
        slot["spread_ratio"] = (max(costs.values()) / min(costs.values())
                                if min(costs.values()) > 0 else None)
    return {
        "rule": "maximum measured cell cost per horizon",
        "rule_authority": (
            "root disposition 2026-09-21 03:43 ranked action 2; "
            "COORDINATOR_DECISIONS revision 17 item 85"),
        "rule_is_outcome_independent": True,
        "rule_is_not_an_inferential_guarantee": (
            "a conservative resource aggregator. It says nothing about whether "
            "the cells differ and licenses no change to the scientific horizon."),
        "by_horizon": by_horizon,
        "both_cell_inputs_retained": True,
    }


#: Where the reference's own resource receipt is deposited.  Read-only here.
REFERENCE_TIMING = (REPO_ROOT / "results" / "live_ab_validation_v2"
                    / "resource_check_delivered" / "reference_timing.json")

#: Where the MEASURED combined-workload receipt is deposited, when one exists.
#: This is the receipt whose timed region covers the whole declared workload --
#: shared generation, the primary evaluation, BOTH reference calls and row
#: serialization -- rather than the primary alone or the reference alone.
COMBINED_TIMING = (REPO_ROOT / "results" / "live_ab_validation_v2"
                   / "resource_check_delivered" / "combined_workload_timing.json")


# ---------------------------------------------------------------------------
# THE FROZEN REFERENCE WORKLOAD
#
# Post-development, PRE-FULL-CALIBRATION amendment.  Root disposition of
# 2026-09-21 04:53 ("Root's resource and reference decisions") and
# COORDINATOR_DECISIONS revision 18 item 94.  Frozen here, in executable form,
# BEFORE any calibration run; the before/after text is carried in
# ``REFERENCE_WORKLOAD_AMENDMENT`` so the change is auditable rather than
# merely asserted.
# ---------------------------------------------------------------------------
REFERENCE_WORKLOAD: Dict[str, object] = {
    "status": "DECLARED AND FROZEN",
    "frozen_as": "post-development, pre-full-calibration amendment",
    "authority": ("root disposition 2026-09-21 04:53; COORDINATOR_DECISIONS "
                  "revision 18 item 94"),
    "scores_per_trial": ("H", "D"),
    "calls_per_score_per_trial": 1,
    "calls_per_trial": 2,
    "trials_per_program": vgen.TRIALS_PER_PROGRAM,
    "calls_per_program": 2 * vgen.TRIALS_PER_PROGRAM,
    "path_rule": ("ONE complete-path call per score per trial on the SHARED "
                  "latent arrays and the fixed prefix grid already used by the "
                  "corresponding full-information diagnostics. Each full path "
                  "is computed ONCE and its returned bands are INDEXED at every "
                  "look; the path is never recomputed per look and never "
                  "recomputed per baseline."),
    "shared_draws": ("the reference consumes the SAME latent arrays the primary "
                     "is evaluated on; generation is shared, not repeated"),
    "decision_authority": (
        "NONE, and unchanged. The reference remains a FULL-INFORMATION "
        "DIAGNOSTIC. It gates no tier, overrides no decision and has no "
        "authority to alter primary trial stopping."),
    "may_be_silently_dropped": False,
    "drop_rule": ("The comparator may not be silently dropped and the workload "
                  "may not be changed after outcomes are seen. If its cost "
                  "cannot be met, the TOTAL-WORKLOAD GUARD refuses and the "
                  "matter is escalated for a scoped decision."),
    "accounted_components": [
        "shared stream generation",
        "primary evaluation and its looks",
        "the H reference call",
        "the D reference call",
        "row serialization and output volume",
        "combined peak resident memory",
    ],
}

REFERENCE_WORKLOAD_AMENDMENT: Dict[str, object] = {
    "kind": "post-development, pre-full-calibration amendment",
    "date_utc": "2026-09-21",
    "before": (
        "NOT YET DECLARED. How many reference calls the primary grid will "
        "actually make is not fixed by any frozen document. The totals below "
        "assume ONE reference evaluation per program at the tier's horizon, "
        "which is stated as an ASSUMPTION and is not a prespecified workload. "
        "It must be predeclared before any tier is relied on."),
    "after": (
        "DECLARED AND FROZEN. One complete-path reference call per score per "
        "trial, for BOTH the hierarchy score H and the success-difference "
        "score D, on the shared latent arrays and the fixed prefix grid. Four "
        "trials per program therefore mean EIGHT reference calls per program. "
        "Each full path is computed once and its bands are indexed; it is not "
        "rerun at each look or separately for each baseline. The reference "
        "keeps its complete-information status and has no primary decision "
        "authority."),
    "why": (
        "The old text was not merely imprecise, it was numerically wrong in "
        "two directions at once. The resource review established that the "
        "receipt behind it already contained FOUR trial calls per program, not "
        "one, and that each of those was ONE SCORE STREAM (H only). A two-score "
        "panel executes twice that again. 'One evaluation per program' "
        "understated the executed workload by a factor of eight."),
    "what_did_not_change": [
        "the scientific design and the outcome-independent primary tier",
        "alpha, margins, seeds, scoring, stopping, deadline, finalization",
        "the reference's zero decision authority",
        "every previously deposited receipt, which is preserved unedited",
    ],
    "supersedes_field": "reference_workload_costs()['workload_declaration_status']",
}


def reference_workload_costs() -> Dict[str, object]:
    """The PLANNED external-reference compute, priced from its own receipt.

    WHY THIS EXISTS.  ``reference/panel.py`` excludes the reference from every
    budget ladder on the grounds that it cannot decide anything.  The root
    rejects that as a resource argument: "Reference-only decision authority
    does not make its compute free", and "Scientific reference-only status does
    not make that computation free: keep inferential decision authority
    separate from total resource accounting."

    So the two are kept separate and BOTH are reported:

      * DECISION AUTHORITY -- unchanged and still zero. The reference gates
        nothing, and ``admissible`` below is still decided by the frozen
        ``cells.json`` selection rule on the PRIMARY projection alone. Nothing
        here moves a tier.
      * RESOURCE ACCOUNTING -- the reference's measured cost per program is
        priced into a separate total, and where a tier's primary+reference
        total would exceed the frozen cap that is FLAGGED rather than hidden.

    Provenance is recorded exactly, including the receipt's weaknesses: this
    receipt carries min/median/max summaries only, with no raw timing vectors,
    no interpreter or environment record and no code hashes, so it is NOT an
    exact-pin receipt of the strength of the committed primary receipt. It is
    reported as the weaker artifact it is.

    An absent or unusable receipt yields ``resolved: False`` with a reason.
    The cost is then UNRESOLVED, which is not the same as zero and is never
    silently rendered as zero.
    """
    out: Dict[str, object] = {
        "role_for_decisions": (
            "NONE. The reference overrides no decision and gates no tier; the "
            "frozen selection rule reads the primary projection only."),
        "role_for_resources": (
            "COUNTED. Planned reference calls are real compute and are priced "
            "into a separate total (root disposition, ranked action 2)."),
        "receipt": str(REFERENCE_TIMING.relative_to(REPO_ROOT)),
        "resolved": False,
    }
    if not REFERENCE_TIMING.is_file():
        out["unresolved_reason"] = (
            f"{out['receipt']} is absent on this host, so the planned "
            f"reference workload has NO measured cost. It is reported as "
            f"UNRESOLVED, never as zero.")
        return out
    try:
        rec = json.loads(REFERENCE_TIMING.read_text())
        pts = rec["points"]
    except (OSError, ValueError, KeyError) as exc:           # pragma: no cover
        out["unresolved_reason"] = f"receipt unreadable: {exc!r}"
        return out
    by_horizon: Dict[int, Dict[str, object]] = {}
    for p in pts:
        h = int(p["N_max"])
        slot = by_horizon.setdefault(h, {"cells": {}})
        slot["cells"][str(p["cell"])] = p["seconds_per_program"]  # type: ignore[index]
    for h, slot in by_horizon.items():
        costs = slot["cells"]                                # type: ignore[index]
        worst = max(costs, key=lambda c: costs[c])
        slot["selected_cell"] = worst
        slot["seconds_per_program"] = costs[worst]
    out.update({
        "resolved": True,
        "receipt_sha256": sha256_file(REFERENCE_TIMING),
        "reference_available_at_measurement": rec.get("reference_available"),
        "design": rec.get("design"),
        "aggregation_rule": (
            "maximum measured cell cost per horizon -- the SAME conservative "
            "rule the primary projection uses, so the two totals are formed "
            "the same way"),
        "seconds_per_program_by_horizon": {
            str(h): slot for h, slot in sorted(by_horizon.items())},
        "receipt_provenance_limits": [
            "min/median/max summaries only; no raw per-repetition timing "
            "vectors, unlike the committed primary receipt",
            "no generation timestamp, interpreter or environment record",
            "no code, harness or binary hashes, so it is NOT an exact-pin "
            "receipt and must not be described as one",
            "panel.py times the band call on PRE-GENERATED draws. The primary "
            "receipt's timed region ALSO included generation and row "
            "serialization -- that was established from its own source and is "
            "not in doubt -- so the two scopes overlap rather than nest, and "
            "adding them double-counts nothing but also certifies nothing. The "
            "genuine remaining scope differences are the grid's accumulator, "
            "its output path and its per-batch summary work, a disk-backed "
            "sink against a discard sink, and warm-up and process context. "
            "These are named limitations, NOT a mathematical bound in either "
            "direction.",
            "its four groups share one process, so its RSS is a cumulative "
            "high-water mark and is not attributable per group",
            "it measures ONE score stream (hierarchy H only) and FOUR trial "
            "calls per program; the frozen workload is TWO scores, so it "
            "prices HALF the declared calls",
        ],
        "measured_scope_vs_declared_workload": {
            "receipt_calls_per_program": int(vgen.TRIALS_PER_PROGRAM),
            "declared_calls_per_program":
                int(REFERENCE_WORKLOAD["calls_per_program"]),
            "scale_factor_applied": 2.0,
            "this_is_arithmetic_not_measurement": (
                "the H-only receipt is scaled by the declared score count. "
                "That is conditional arithmetic on a weak receipt, exactly the "
                "kind of number the root withdrew when it was presented as "
                "measured compute. It is labelled as arithmetic here and a "
                "MEASURED combined receipt supersedes it when one exists."),
        },
        "workload_declaration_status": "DECLARED AND FROZEN",
        "workload": dict(REFERENCE_WORKLOAD),
        "workload_amendment": dict(REFERENCE_WORKLOAD_AMENDMENT),
    })
    # Scale the H-only receipt onto the DECLARED two-score workload.  Labelled
    # arithmetic, never presented as a measurement.
    scale = float(REFERENCE_WORKLOAD["calls_per_program"]) / float(
        vgen.TRIALS_PER_PROGRAM)
    for slot in out["seconds_per_program_by_horizon"].values():   # type: ignore[union-attr]
        slot["seconds_per_program_measured_h_only"] = slot["seconds_per_program"]
        slot["seconds_per_program"] = slot["seconds_per_program"] * scale
    # A MEASURED combined receipt, if one has been deposited, is reported beside
    # the scaled arithmetic and never silently replaces it.
    combined = _combined_workload_receipt()
    out["combined_workload_receipt"] = combined
    # CONSERVATIVE RECONCILIATION.  Two independent routes reach the
    # reference-attributable per-program cost: the scaled H-only arithmetic and
    # the measured missing scope.  Neither is discarded and the LARGER is used,
    # per horizon -- the same conservative convention the primary projection
    # already uses across cells.  This is a RESOURCE rule; it moves no tier and
    # touches no scientific parameter.
    routes: Dict[str, object] = {}
    if combined.get("present"):
        meas_by_h = combined["seconds_per_program_by_horizon"]    # type: ignore[index]
        for h, slot in out["seconds_per_program_by_horizon"].items():  # type: ignore[union-attr]
            arith = float(slot["seconds_per_program"])
            meas = meas_by_h.get(h)
            if meas is None:
                routes[h] = {"scaled_arithmetic": arith, "measured": None,
                             "used": "scaled_arithmetic",
                             "reason": "no measurement at this horizon"}
                continue
            meas_v = float(meas["seconds_per_program"])
            chosen = max(arith, meas_v)
            slot["seconds_per_program_scaled_arithmetic"] = arith
            slot["seconds_per_program_measured_missing_scope"] = meas_v
            slot["seconds_per_program"] = chosen
            routes[h] = {
                "scaled_arithmetic": arith,
                "measured_missing_scope": meas_v,
                "ratio_measured_over_arithmetic": (meas_v / arith
                                                   if arith else None),
                "used": ("measured_missing_scope" if chosen == meas_v
                         else "scaled_arithmetic"),
                "rule": "the larger of the two, per horizon",
            }
    out["reference_cost_route_reconciliation"] = {
        "routes_by_horizon": routes,
        "rule": ("the larger of the scaled arithmetic and the measured "
                 "missing scope, per horizon; neither route is discarded"),
        "is_a_resource_rule_only": True,
        "withdrawn_91_2_percent": (
            "NOT reused, NOT reproduced and NOT repaired. It was conditional "
            "arithmetic on a weak one-score receipt and does not carry into a "
            "two-score workload."),
    }
    return out


def _combined_workload_receipt() -> Dict[str, object]:
    """The measured combined-workload receipt, or an explicit absence."""
    if not COMBINED_TIMING.is_file():
        return {"present": False,
                "path": str(COMBINED_TIMING.relative_to(REPO_ROOT)),
                "note": ("no measured combined-workload receipt on this host; "
                         "the scaled arithmetic above is all there is, and it "
                         "is arithmetic")}
    try:
        rec = json.loads(COMBINED_TIMING.read_text())
    except (OSError, ValueError) as exc:                         # pragma: no cover
        return {"present": False, "unreadable": f"{exc!r}"}
    by_h: Dict[str, Dict[str, object]] = {}
    for p in rec.get("points", []):
        h = str(int(p["N_max"]))
        slot = by_h.setdefault(h, {"combined_cells": {}, "missing_cells": {}})
        cell = str(p["cell"])
        slot["combined_cells"].setdefault(cell, []).append(          # type: ignore[union-attr]
            float(p["seconds_per_program"]))
        slot["missing_cells"].setdefault(cell, []).append(           # type: ignore[union-attr]
            float(p["missing_scope_seconds_per_program"]))
    for slot in by_h.values():
        for key, src in (("combined", "combined_cells"),
                         ("missing_scope", "missing_cells")):
            per_cell = {c: statistics.median(v)                      # type: ignore[union-attr]
                        for c, v in slot[src].items()}
            worst = max(per_cell, key=lambda c: per_cell[c])
            slot[f"{key}_seconds_per_program_by_cell"] = per_cell
            slot[f"{key}_selected_cell"] = worst
            slot[f"{key}_seconds_per_program"] = per_cell[worst]
            slot.pop(src)
        # the field the guard's reconciliation reads: the REFERENCE-ONLY share
        # of the combined workload, which is the object route A also estimates
        slot["seconds_per_program"] = slot["missing_scope_seconds_per_program"]
    return {
        "present": True,
        "path": str(COMBINED_TIMING.relative_to(REPO_ROOT)),
        "receipt_sha256": sha256_file(COMBINED_TIMING),
        "schema": rec.get("schema"),
        "scope": rec.get("timed_scope"),
        "aggregation_rule": ("median over repetitions, then the MAXIMUM "
                             "measured cell per horizon"),
        "seconds_per_program_is": (
            "the MISSING SCOPE (combined minus primary-only), which is the "
            "reference-attributable share and is the object comparable with "
            "the scaled arithmetic. The whole combined cost is reported "
            "separately under combined_seconds_per_program."),
        "seconds_per_program_by_horizon": by_h,
        "attempts_total": rec.get("attempts_total"),
        "attempts_failed": rec.get("attempts_failed"),
        "bytes_per_program": rec.get("bytes_per_program"),
        "pins": (rec.get("pins") or {}).get("environment"),
    }


# ---------------------------------------------------------------------------
# THE FAIL-CLOSED TOTAL-WORKLOAD RESOURCE GUARD
#
# Root disposition of 2026-09-21 04:53 and COORDINATOR_DECISIONS revision 18
# item 94: "Add a separate FAIL-CLOSED total-resource guard for unresolved and
# over-cap costs."  The resource review states the requirement precisely --
# there must be TWO DIFFERENT DECISIONS: the frozen scientific tier selection,
# which is unchanged and reads the primary projection only, and a SEPARATE
# authorization of the ENTIRE DECLARED EXECUTION WORKLOAD, which refuses.
#
# What makes this fail-closed rather than advisory:
#   * an UNRESOLVED total refuses.  Unresolved is not zero and is not a pass.
#   * an OVER-CAP total refuses, even when the primary-only tier is admissible.
#   * a MISSING or unselected tier refuses.
#   * the caller cannot proceed past it: ``enforce_total_workload_guard`` raises
#     ``TotalResourceRefusal``, which is a SystemExit, before the grid starts.
#   * it carries NO exemption list.  A gate with an exemption is the defect this
#     study exists to find.
#
# What it deliberately does NOT do: it does not move a tier, change alpha,
# margins, seeds, scoring or stopping, and it gives the comparator no
# inferential authority.  Respecting a compute cap is not a scientific decision.
# ---------------------------------------------------------------------------
class TotalResourceRefusal(SystemExit):
    """Raised when the projected TOTAL workload is unresolved or over cap."""


def _finite_nonneg(value: object) -> bool:
    """A projected total must be a real, finite, nonnegative number.

    WHY THIS EXISTS.  ``float("nan") > cap`` is **False**, so a NaN projection
    walked straight through the v1 cap test and AUTHORIZED; so did a negative
    total.  Guard v1 therefore had a cap test that a missing measurement could
    satisfy.  Every numeric total now passes through here first.
    """
    try:
        x = float(value)                                       # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return math.isfinite(x) and x >= 0.0


#: Every hard limit declared in the config, paired with the ladder field that
#: projects it.  Guard v1 checked ONLY ``seconds`` while the config also caps
#: output bytes and peak RSS, so a workload could be authorized while projected
#: to blow either of the other two.  Adding a cap to the config now adds it to
#: the guard.
_CAP_FIELDS = (
    ("seconds", "seconds_projected", "total_seconds_projected"),
    ("output_bytes", "bytes_projected", None),
    ("peak_rss_bytes", "peak_rss_projected", None),
)

#: Identities that must match before a projection may authorize execution.  A
#: projection priced against different code, a different config, a different
#: policy or a different reference workload is not a projection OF the run
#: being proposed.
_REQUIRED_IDENTITIES = ("code", "config", "policy", "workload", "receipt")


def total_workload_guard(budget: Dict[str, object],
                         cfg_json: dict,
                         proposed: Optional[Dict[str, object]] = None
                         ) -> Dict[str, object]:
    """[pure] Authorize, or REFUSE, the entire declared execution workload.

    ``proposed`` carries the ACTUAL arguments execution would run with -- any
    tier override, the programs and horizon, and the identity fingerprints of
    the code, config, policy and reference workload the projection was priced
    against.  Guard v1 priced the AUTOMATIC tier and then let an execution
    override change what actually ran, so the authorized number and the
    executed number could differ.  The override is now resolved FIRST and the
    pricing follows it.
    """
    limits = cfg_json["budget"]["hard_limits"]
    cap_seconds = float(limits["seconds"])
    proposed = dict(proposed or {})
    ladder = list(budget.get("ladder") or [])

    # ---- 1. RESOLVE THE OVERRIDE BEFORE PRICING ANYTHING ------------------
    automatic = budget.get("selected_tier")
    override = proposed.get("tier_override")
    selected = override if override is not None else automatic

    verdict: Dict[str, object] = {
        "guard": "fail_closed_total_workload_resource_guard",
        "version": "2.0.0",
        "authority": ("root disposition 2026-09-21 06:35 "
                      "('close the named guard and provenance failures'); "
                      "COORDINATOR_DECISIONS revision 19"),
        "separate_from_the_scientific_tier_selection": True,
        "frozen_selection_rule_unchanged": True,
        "gives_the_comparator_no_inferential_authority": True,
        "exemptions": [],
        "cap_seconds": cap_seconds,
        "caps_checked": [name for name, _, _ in _CAP_FIELDS],
        "automatic_tier": automatic,
        "tier_override": override,
        "selected_tier": selected,
        "priced_after_override": True,
        "covers": list(REFERENCE_WORKLOAD["accounted_components"]),
    }
    if override is not None and override != automatic:
        verdict["override_note"] = (
            f"execution proposes tier {override!r} while the frozen primary "
            f"rule selected {automatic!r}; the TOTAL is priced against "
            f"{override!r}, which is what would actually run")
    if selected is None:
        verdict.update({
            "authorized": False,
            "refusal_class": "no_tier_selected",
            "refusal": ("no tier was selected by the frozen primary rule, so "
                        "there is no total workload to authorize. REFUSED."),
        })
        return verdict
    entry = next((e for e in ladder if e.get("tier") == selected), None)
    if entry is None:                                            # pragma: no cover
        verdict.update({
            "authorized": False,
            "refusal_class": "selected_tier_missing_from_ladder",
            "refusal": f"tier {selected!r} is not in the ladder. REFUSED.",
        })
        return verdict
    primary = entry.get("seconds_projected")
    ref = entry.get("reference_seconds_projected")
    verdict["primary_seconds_projected"] = primary
    verdict["reference_seconds_projected"] = ref
    if entry.get("reference_cost_unresolved") or ref is None:
        verdict.update({
            "authorized": False,
            "refusal_class": "unresolved_total_cost",
            "total_seconds_projected": None,
            "refusal": (
                "the declared reference workload has NO resolved cost at this "
                "tier, so the TOTAL is unresolved. Unresolved is not zero and "
                "is not a pass: execution is REFUSED until the cost is measured "
                "or the workload is rescoped by a decision on the record."),
            "reference_cost_note": entry.get("reference_cost_note"),
        })
        return verdict
    # ---- 2. EVERY PROJECTED TOTAL MUST BE A REAL NUMBER -------------------
    # NaN slid through the v1 cap test because ``nan > cap`` is False; so did a
    # negative total.  A cap test a missing measurement can satisfy is not a
    # cap test.
    nonfinite = [name for name, own, tot in _CAP_FIELDS
                 for field in ((tot or own),)
                 if not _finite_nonneg(entry.get(field))]
    if not _finite_nonneg(primary) or not _finite_nonneg(ref) or nonfinite:
        verdict.update({
            "authorized": False,
            "refusal_class": "non_finite_projection",
            "total_seconds_projected": None,
            "nonfinite_fields": nonfinite,
            "refusal": (
                "a projected total is not a finite nonnegative number "
                f"(primary={primary!r}, reference={ref!r}, "
                f"nonfinite={nonfinite}). NaN is not a small number and a "
                "negative projection is not headroom: both silently PASSED the "
                "v1 cap comparison. Execution is REFUSED until every projected "
                "total is measured as a real quantity."),
        })
        return verdict

    total = float(primary) + float(ref)
    verdict["total_seconds_projected"] = total
    verdict["reference_share_of_total"] = (float(ref) / total) if total else None
    verdict["primary_only_admissible"] = bool(entry.get("admissible"))

    # ---- 3. EVERY DECLARED CAP, AGAINST THE ACTUAL PROPOSED ARGUMENTS -----
    breaches: List[Dict[str, object]] = []
    for name, own_field, total_field in _CAP_FIELDS:
        if name not in limits:
            continue
        cap = float(limits[name])
        value = total if total_field == "total_seconds_projected" \
            else float(entry.get(own_field))
        scale = _proposed_scale(proposed, entry)
        value = value * scale
        verdict.setdefault("checked", {})[name] = {          # type: ignore[union-attr]
            "cap": cap, "projected": value, "scale_from_proposed": scale}
        if value > cap:
            breaches.append({"cap_name": name, "cap": cap, "projected": value})
    if breaches:
        first = breaches[0]
        verdict.update({
            "authorized": False,
            "refusal_class": ("total_over_cap"
                              if first["cap_name"] == "seconds"
                              else "projected_over_cap"),
            "cap_breaches": breaches,
            "refusal": (
                "the proposed workload breaches "
                + "; ".join(f"{b['cap_name']} ({b['projected']:.1f} > {b['cap']:.1f})"
                            for b in breaches)
                + ". The primary-only tier is "
                f"{'admissible' if entry.get('admissible') else 'not admissible'}, "
                "which does not matter here: the total is what is being "
                "authorized. Execution is REFUSED. Report it for a scoped "
                "decision; do not drop the comparator and do not choose a "
                "different workload after outcomes."),
        })
        return verdict

    # ---- 4. PROVENANCE: the projection must be OF this run ----------------
    prov = _provenance_verdict(budget, proposed)
    verdict["provenance"] = prov
    if not prov["ok"]:
        verdict.update({
            "authorized": False,
            "refusal_class": prov["refusal_class"],
            "refusal": prov["refusal"],
        })
        return verdict

    verdict.update({
        "authorized": True,
        "refusal_class": None,
        "refusal": None,
        "headroom_seconds": cap_seconds - total,
    })
    return verdict


def _proposed_scale(proposed: Dict[str, object],
                    entry: Dict[str, object]) -> float:
    """How much bigger the PROPOSED run is than the tier that was priced.

    A cap checked against the ladder's own numbers is checked against the tier
    as priced, not against what execution was actually asked to do.  If the
    proposal names more programs than the entry was priced for, every cap is
    checked against the larger figure.  Absent a proposal this is 1.0 and the
    behaviour is the ladder's own.
    """
    want = proposed.get("programs_total")
    priced = entry.get("programs_total")
    if want is None or not priced:
        return 1.0
    try:
        return max(1.0, float(want) / float(priced))
    except (TypeError, ValueError, ZeroDivisionError):        # pragma: no cover
        return 1.0


def _provenance_verdict(budget: Dict[str, object],
                        proposed: Dict[str, object]) -> Dict[str, object]:
    """Identities and group accounting, required rather than assumed.

    Guard v1 would authorize on the old scaled H-only arithmetic with NO
    contemporaneous combined receipt behind it.  Root: "Retain old arithmetic
    as historical description rather than authority to execute an unresolved
    workload."  So route A stays in the record and route B is what authorizes.
    """
    ref = dict(budget.get("reference_workload") or {})
    combined = dict(ref.get("combined_workload_receipt") or {})
    out: Dict[str, object] = {"ok": True, "refusal_class": None, "refusal": None,
                              "combined_receipt_present": bool(combined.get("present")),
                              "identities_checked": list(_REQUIRED_IDENTITIES)}

    if not combined.get("present"):
        out.update({
            "ok": False,
            "refusal_class": "missing_combined_receipt",
            "refusal": (
                "no contemporaneous COMBINED workload receipt backs this "
                "projection. The scaled H-only arithmetic is retained as "
                "historical DESCRIPTION and is not authority to execute an "
                "unresolved workload. Execution is REFUSED until the combined "
                "scope is measured."),
        })
        return out

    declared = dict(proposed.get("identities") or {})
    recorded = dict(combined.get("identities") or ref.get("identities") or {})
    mismatched = []
    missing = []
    for name in _REQUIRED_IDENTITIES:
        want, got = declared.get(name), recorded.get(name)
        if want is None or got is None:
            missing.append(name)
        elif want != got:
            mismatched.append({"identity": name, "proposed": want, "priced": got})
    out["identity_mismatches"] = mismatched
    out["identities_missing"] = missing
    if mismatched:
        out.update({
            "ok": False,
            "refusal_class": "identity_mismatch",
            "refusal": (
                f"the projection was priced against different {', '.join(m['identity'] for m in mismatched)}"
                " than the run being proposed, so it is not a projection OF "
                "this run. Execution is REFUSED."),
        })
        return out
    if missing:
        out.update({
            "ok": False,
            "refusal_class": "identity_unverifiable",
            "refusal": (
                f"identities {missing} are absent from the proposal or the "
                "receipt, so the projection cannot be shown to price THIS run. "
                "Unverifiable is not verified. Execution is REFUSED."),
        })
        return out

    planned = combined.get("planned_groups")
    attempts = combined.get("attempts_total")
    recorded_groups = combined.get("groups_total")
    out["group_accounting"] = {"planned": planned, "recorded": recorded_groups,
                               "attempts": attempts}
    if planned is None or recorded_groups is None:
        out.update({
            "ok": False,
            "refusal_class": "group_accounting_absent",
            "refusal": ("the combined receipt does not account for its planned "
                        "timing groups, so its total cannot be shown to cover "
                        "the declared workload. Execution is REFUSED."),
        })
        return out
    if int(recorded_groups) < int(planned):
        out.update({
            "ok": False,
            "refusal_class": "group_accounting_short",
            "refusal": (
                f"the combined receipt records {recorded_groups} timing groups "
                f"against {planned} planned, so part of the declared workload "
                "was never measured. Execution is REFUSED."),
        })
    return out


def enforce_total_workload_guard(verdict: Dict[str, object]) -> None:
    """REFUSE to proceed unless the total workload was authorized.

    This is the half that makes the guard fail-closed rather than advisory: it
    raises, and the caller cannot continue past it.
    """
    if verdict.get("authorized"):
        return
    raise TotalResourceRefusal(
        "TOTAL-WORKLOAD RESOURCE GUARD REFUSED "
        f"({verdict.get('refusal_class')}): {verdict.get('refusal')} "
        "This guard is separate from the frozen scientific tier selection and "
        "carries no exemption.")


def select_tier(smoke: Dict[str, object], cfg_json: dict) -> Dict[str, object]:
    """PROTOCOL 8.2: the ladder, from runtime and memory measurements alone."""
    limits = cfg_json["budget"]["hard_limits"]
    balanced = bool(smoke.get("balanced"))
    aggregation: Optional[Dict[str, object]] = None
    if balanced:
        # v2: cell-aware, both inputs retained, maximum cost per horizon.
        aggregation = aggregate_horizon_costs(smoke)
        by_h = aggregation["by_horizon"]                    # type: ignore[index]
        if 2000 not in by_h or 1000 not in by_h:
            return {"beta": None, "selected_tier": None, "paused": True,
                    "ladder": [], "hard_limits": limits,
                    "horizon_aggregation": aggregation,
                    "note": "the smoke run did not produce both horizon points, "
                            "so the scaling exponent cannot be measured and no "
                            "tier may be selected"}
        s_2000 = by_h[2000]["seconds_per_program"]
        s_1000 = by_h[1000]["seconds_per_program"]
    else:
        # v1: the ORIGINAL schedule-specific path, preserved byte-for-byte in
        # its arithmetic.  Its confounded split has exactly one cell per
        # horizon, so keying by horizon discards nothing there and the
        # deposited v1 selection stays reproducible.
        points = {p["N_max"]: p for p in smoke["points"]}
        if len(points) != len(smoke["points"]):             # pragma: no cover
            raise SystemExit(
                "the v1 selection path was handed a smoke record with more "
                "than one cell per horizon; that is the balanced design and it "
                "must set balanced=True so the cell-aware path is used")
        if 2000 not in points or 1000 not in points:
            return {"beta": None, "selected_tier": None, "paused": True,
                    "ladder": [], "hard_limits": limits,
                    "note": "the smoke run did not produce both horizon points, "
                            "so the scaling exponent cannot be measured and no "
                            "tier may be selected"}
        s_2000 = points[2000]["seconds_per_program"]
        s_1000 = points[1000]["seconds_per_program"]
    beta = math.log(s_2000 / s_1000) / math.log(2.0)
    record_bytes = sum(p["record_bytes_measured_not_written"] for p in
                       smoke["points"])
    bytes_per_program = record_bytes / max(int(smoke["total_programs"]), 1)
    reference = reference_workload_costs()
    ref_by_h = reference.get("seconds_per_program_by_horizon") or {}
    ladder = []
    selected = None
    for tier in cfg_json["budget"]["ladder"]:
        total = tier["programs_total"]
        n_max = tier["N_max"]
        seconds = s_2000 * total * (n_max / 2000.0) ** beta
        out_bytes = bytes_per_program * total
        entry = {"tier": tier["tier"], "programs_total": total, "N_max": n_max,
                 "seconds_projected": seconds,
                 "bytes_projected": out_bytes,
                 "peak_rss_projected": int(smoke["peak_rss_bytes"]),
                 "within_seconds": seconds <= limits["seconds"],
                 "within_bytes": out_bytes <= limits["output_bytes"],
                 "within_peak_rss":
                     int(smoke["peak_rss_bytes"]) <= limits["peak_rss_bytes"]}
        # The FROZEN selection rule, unchanged: it reads the primary
        # projection only.  No line below may enter this boolean.
        entry["admissible"] = bool(entry["within_seconds"]
                                   and entry["within_bytes"]
                                   and entry["within_peak_rss"])
        # ---- resource accounting for the planned reference workload --------
        slot = ref_by_h.get(str(n_max))
        if slot is None:
            entry["reference_seconds_projected"] = None
            entry["total_seconds_projected"] = None
            entry["reference_cost_unresolved"] = True
            entry["reference_cost_note"] = (
                reference.get("unresolved_reason")
                or f"no measured reference cost at horizon {n_max}; UNRESOLVED, "
                   f"not zero")
        else:
            ref_seconds = float(slot["seconds_per_program"]) * total
            entry["reference_seconds_projected"] = ref_seconds
            entry["total_seconds_projected"] = seconds + ref_seconds
            entry["reference_cost_unresolved"] = False
            entry["total_within_seconds"] = (
                seconds + ref_seconds <= limits["seconds"])
            entry["reference_share_of_total"] = (
                ref_seconds / (seconds + ref_seconds)
                if (seconds + ref_seconds) > 0 else None)
            entry["reference_changes_admissibility"] = bool(
                entry["within_seconds"] and not entry["total_within_seconds"])
        ladder.append(entry)
        if selected is None and entry["admissible"]:
            selected = tier["tier"]
    flagged = [e["tier"] for e in ladder
               if e.get("reference_changes_admissibility")]
    out: Dict[str, object] = {
        "beta": beta, "s_per_program_2000": s_2000,
        "s_per_program_1000": s_1000,
        "bytes_per_program": bytes_per_program,
        "ladder": ladder, "selected_tier": selected,
        "paused": selected is None,
        "selection_rule": cfg_json["budget"]["selection_rule"],
        "hard_limits": limits,
        "reference_workload": reference,
        "reference_workload_accounting": {
            "included_in_total_seconds": bool(reference.get("resolved")),
            "included_in_the_admissibility_gate": False,
            "why_not": (
                "the selection rule is frozen in cells.json and reads "
                "seconds_projected. Changing what that gate consumes would be "
                "a change to a scientific rule, which is not authorized. The "
                "reference total is therefore reported BESIDE the gate, and "
                "any tier the reference would push over the cap is named."),
            "tiers_admissible_on_primary_but_over_cap_with_reference": flagged,
        },
    }
    if aggregation is not None:
        out["horizon_aggregation"] = aggregation
        out["projection_inputs"] = {
            "s_per_program_2000_from_cell":
                aggregation["by_horizon"][2000]["selected_cell"],   # type: ignore[index]
            "s_per_program_1000_from_cell":
                aggregation["by_horizon"][1000]["selected_cell"],   # type: ignore[index]
            "both_cells_at_2000":
                aggregation["by_horizon"][2000]["seconds_per_program_by_cell"],  # type: ignore[index]
            "both_cells_at_1000":
                aggregation["by_horizon"][1000]["seconds_per_program_by_cell"],  # type: ignore[index]
            "note": ("the projection uses the maximum; BOTH cell measurements "
                     "are retained here so the discarded-cell defect cannot "
                     "recur invisibly"),
        }
    else:
        out["horizon_aggregation"] = {
            "rule": "v1 schedule-specific path: one cell per horizon, keyed by "
                    "horizon exactly as the deposited v1 budget was selected",
            "both_cell_inputs_retained": "not applicable (one cell per horizon)",
        }
    return out


def assert_incremental(smoke: Dict[str, object]) -> Dict[str, object]:
    """PROTOCOL 8.1: the running sums are maintained incrementally, not recomputed."""
    worst = 0.0
    for p in smoke["points"]:
        per_pair = p["enclosure_updates_per_pair"]
        worst = max(worst, per_pair)
        if per_pair > vgen.BREAKPOINTS_PER_PAIR:
            raise SystemExit(
                f"the enclosure sums are not incremental: {per_pair:.2f} updates "
                f"per pair, above the {vgen.BREAKPOINTS_PER_PAIR} a pair can "
                f"logically make")
    return {"enclosure_updates_per_pair_max": worst,
            "bound_per_pair": vgen.BREAKPOINTS_PER_PAIR,
            "incremental": True}


# ---------------------------------------------------------------------------
# The fixture gate and the manifest
# ---------------------------------------------------------------------------
def run_fixture_gate(guard: WriteGuard) -> Dict[str, object]:
    """PROTOCOL 11: run the frozen fixture command and deposit its report.

    The fixtures are run in a SUBPROCESS, exactly as the frozen command runs
    them, so that this module's own interpreter never loads anything the
    independence rule keeps out of it.
    """
    cmd = [sys.executable, str(HERE / "vfixtures.py")]
    done = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    cases: Dict[str, str] = {}
    for line in done.stdout.splitlines():
        if line.startswith("ok   "):
            cases[line[5:].strip()] = "pass"
        elif line.startswith("FAIL "):
            cases[line[5:].strip()] = "fail"
    report = {"command": "vfixtures.py", "returncode": done.returncode,
              "cases": cases, "passed": sum(1 for v in cases.values()
                                            if v == "pass"),
              "total": len(cases),
              "stderr_tail": done.stderr.strip()[-2000:]}
    guard.write_json("fixtures_report.json", report)
    return report


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_commit() -> str:
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              capture_output=True, text=True, timeout=30)
        return done.stdout.strip() if done.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):       # pragma: no cover
        return "unknown"


def v2_bindings(cfg: RunConfig) -> Dict[str, object]:
    """The amendment, reference and harness hashes a v2 run must bind.

    Root disposition decision 3 and COORDINATOR_DECISIONS revision 16 item 79:
    the manifest reported the FROZEN CELL-FILE version and hashed the OLD
    protocol, so a v2 run was labelled with v1's identity.  The repair is to
    record BASE and AMENDED versions SEPARATELY -- the parent v1 identity is
    preserved, not overwritten -- and to hash the actual operative bytes:
    ``PROTOCOL_V2.md``, the vendored external reference's manifest, and the
    measurement harness that produced the budget.

    A hash that is absent is reported as ``None`` with a reason, never omitted:
    a missing binding must be visible in the artifact, not inferred from a gap.
    """
    base_version = json.loads(CELLS_JSON.read_text())["version"]
    is_v2 = cfg.schedule != SCHEDULE_V1
    out: Dict[str, object] = {
        # the PARENT identity, preserved unchanged
        "base_protocol_version": base_version,
        "base_protocol_document": str(PROTOCOL_MD.relative_to(REPO_ROOT)),
        "base_protocol_sha256": sha256_file(PROTOCOL_MD)
        if PROTOCOL_MD.exists() else None,
        # the OPERATIVE identity of this run
        "amended": is_v2,
        "amendment_version": None,
        "amendment_document": None,
        "amendment_sha256": None,
        "operative_protocol_version": base_version,
        "event_schedule": cfg.schedule,
        "event_schedule_meaning": SCHEDULE_LABEL[cfg.schedule],
        "deferred_schedules": list(DEFERRED_SCHEDULES),
        "deferral_reason": DEFERRAL_REASON,
        "primary_panel_schedules": list(PRIMARY_PANEL_SCHEDULES),
    }
    if is_v2:
        if PROTOCOL_V2_MD.exists():
            out["amendment_version"] = V2_VERSION_STRING
            out["amendment_document"] = str(
                PROTOCOL_V2_MD.relative_to(REPO_ROOT))
            out["amendment_sha256"] = sha256_file(PROTOCOL_V2_MD)
            out["operative_protocol_version"] = V2_VERSION_STRING
        else:
            out["amendment_missing_reason"] = (
                f"{PROTOCOL_V2_MD} does not exist; a v2 run cannot bind its "
                f"amendment and this run is NOT bound to one")

    # THE COMPARISON SNAPSHOT (root resource audit, required repair 4).
    # write_manifest's source glob is TOP-LEVEL ONLY, so neither it nor this
    # function bound pinned_v2/PINNED_V2.json or its three snapshot files, and
    # a v2 run's manifest therefore did not say which #11 rule its comparison
    # would target.  The hashes are recomputed here, not copied from the
    # manifest, so a snapshot edited after it was written cannot pass.
    snap_dir = HERE / "pinned_v2"
    snap_manifest = snap_dir / "PINNED_V2.json"
    if snap_manifest.is_file():
        snap = json.loads(snap_manifest.read_text())
        listed = dict(snap.get("files") or {})
        recomputed = {p.name: sha256_file(p)
                      for p in sorted(snap_dir.glob("*.py"))}
        out["comparison_snapshot"] = {
            "manifest": str(snap_manifest.relative_to(REPO_ROOT)),
            "manifest_sha256": sha256_file(snap_manifest),
            "source_commit": snap.get("source_commit"),
            "files_sha256_recomputed": recomputed,
            "agrees_with_manifest": recomputed == listed,
            "parent_v1_snapshot_source_commit":
                (snap.get("parent_v1_snapshot") or {}).get("source_commit"),
            "bound_by": ("vcompare.py --snapshot v2, which resolves to this "
                         "directory, PROTOCOL_V2.md and "
                         "results/live_ab_validation_v2/"),
        }
    else:
        out["comparison_snapshot"] = None
        out["comparison_snapshot_missing_reason"] = (
            f"{snap_manifest} is absent: this run binds NO v2 comparison "
            f"snapshot. Reported as absent rather than defaulted to v1's.")

    # the DECLARED EXTERNAL REFERENCE.  The primary does not import it; the
    # manifest records only its provenance, so that a result says which
    # reference was available when it was produced.
    ref_manifest = HERE / "reference" / "MANIFEST.json"
    if ref_manifest.exists():
        ref = json.loads(ref_manifest.read_text())
        out["external_reference"] = {
            "manifest_sha256": sha256_file(ref_manifest),
            "callable": ref.get("reference_callable"),
            "role": ref.get("role"),
            "bound_parameters": ref.get("bound_parameters"),
            "vendored_files": {e["vendored_path"]: e["sha256"]
                               for e in ref.get("vendored_files", [])},
            "build_product_sha256": (ref.get("build_product") or {}).get("sha256"),
            "note": "Declared reference only. Reported beside the primary, "
                    "never instead of it; it overrides no decision and the "
                    "primary does not import it."}
    else:
        out["external_reference"] = None
        out["external_reference_missing_reason"] = (
            "reference/MANIFEST.json absent: the authors' empirical-Bernstein "
            "reference was not vendored on this host. Reported as absent "
            "rather than substituted.")
    return out


def write_manifest(guard: WriteGuard, tier: Optional[str], cfg: RunConfig,
                   grid: Dict[str, int],
                   harness: Optional[Dict[str, object]] = None) -> None:
    sources = {}
    for p in sorted(HERE.glob("*.py")):
        sources[p.name] = sha256_file(p)
    for p in (CELLS_JSON, PROTOCOL_MD, PROTOCOL_V2_MD, PINNED_PRIMITIVE,
              GUIDANCE_DOC):
        if p.exists():
            sources[str(p.relative_to(REPO_ROOT))] = sha256_file(p)
    bindings = v2_bindings(cfg)
    guard.write_json("manifest.json", {
        "study": "live_ab_validation (issue 12)",
        # PARENT identity, kept for continuity with the v1 deposit.  The
        # OPERATIVE identity of this run is bindings["operative_protocol_version"];
        # these are deliberately two fields and never one.
        "protocol_version": bindings["base_protocol_version"],
        "v2_bindings": bindings,
        "measurement_harness": harness,
        "master_seed": vgen.MASTER_SEED,
        "grid_namespace": cfg.namespace,
        "namespace_of_the_reported_grid": vgen.NAMESPACE_GRID,
        "sha256": sources,
        "numpy": np.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repo_commit": repo_commit(),
        "selected_budget_tier": tier,
        "N_max": cfg.n_max,
        # PROTOCOL 14: every result keeps the label of the version that produced
        # it.  The event schedule is that label, and it is recorded here so that
        # a v1 file and a v2 file can never be read as the same measurement.
        "event_schedule": cfg.schedule,
        "event_schedule_meaning": SCHEDULE_LABEL[cfg.schedule],
        "drain_W": vgen.DRAIN_W,
        "finalization_tick": cfg.finalization_tick,
        "programs_per_cell": grid,
        "reported_grid": guard.reported,
        "coverage_target_boundary": json.loads(
            CELLS_JSON.read_text())["coverage_target_boundary"],
    })


# ---------------------------------------------------------------------------
# Correctness cross-checks (no output files, nothing reported)
# ---------------------------------------------------------------------------
def _drive_vband(draw: vgen.TrialDraw, n_pairs: int,
                 last_tick: Optional[int] = None):
    """Replay a whole trial through ``vband.ValidationMonitor``, event by event.

    With ``last_tick`` past ``n_pairs`` the replay continues through the
    finalization window: enrollment stops at ``n_pairs`` (PROTOCOL 7.3) and the
    remaining ticks only age the pairs already enrolled, which is exactly what
    the v2 schedule looks at and what v1 never did.  Returns one look per tick.
    """
    mon = vband.ValidationMonitor(cost_cap=vgen.COST_CAP)
    s_c, s_i = vgen.ATOM_SC[draw.atom], vgen.ATOM_SI[draw.atom]
    looks = []
    last = n_pairs if last_tick is None else int(last_tick)
    for n in range(1, last + 1):
        if n <= n_pairs:
            mon.enroll(n, "AB", (n, "C"), (n, "I"))
        for j in range(1, min(n, n_pairs) + 1):
            k, age = j - 1, n - j
            first = (j, "C") if draw.cand_first[k] else (j, "I")
            second = (j, "I") if draw.cand_first[k] else (j, "C")
            s_first = int(s_c[k] if draw.cand_first[k] else s_i[k])
            s_second = int(s_i[k] if draw.cand_first[k] else s_c[k])
            if age >= draw.f[k]:
                mon.finalize(first, s_first, float(draw.c_rev[k]))
            elif draw.f[k] > 0:
                mon.observe_elapsed_cost(
                    first, (float(draw.c_rev[k]) * age) / int(draw.f[k]))
            if age >= draw.d[k]:
                mon.finalize(second, s_second, float(draw.c_pend[k]))
            elif draw.d[k] > 0:
                mon.observe_elapsed_cost(
                    second, (float(draw.c_pend[k]) * age) / int(draw.d[k]))
        looks.append(mon.look())
    return mon, looks


def selfcheck_v2_drain(n_pairs: int = 30, programs: int = 2,
                       verbose: bool = True) -> List[str]:
    """The v2 drain arithmetic against ``vband`` and against the definitions.

    The looks v2 adds are ones no v1 code path ever produced, so they get their
    own cross-check rather than inheriting v1's.  For every tick of the whole
    window, including all ``W`` drain ticks:

      * the ADAPTER's four sums and four band endpoints must equal
        ``vband.ValidationMonitor``'s, at STRICT float equality, with the
        monitor driven event by event and enrolling nothing after the cap;
      * both baselines' index and score sums must equal a from-scratch
        recomputation of their PROTOCOL 3 definitions at that tick.
    """
    fails: List[str] = []
    cfg = make_config(n_pairs, vgen.NAMESPACE_SMOKE)
    fin = cfg.finalization_tick
    checked = drain_checked = 0
    for cell in vgen.CELLS:
        for program in range(programs):
            draw = vgen.draw_trial(cell, program, 0, n_max=n_pairs,
                                   namespace=vgen.NAMESPACE_SMOKE)
            series, _, _, _ = build_series_v2(draw, cfg)
            sums = vgen.adapter_tick_sums(draw, n_pairs, fin)
            a = series[ADAPTER]
            _, looks = _drive_vband(draw, n_pairs, last_tick=fin)
            for i, look in enumerate(looks):
                checked += 1
                if i + 1 > n_pairs:
                    drain_checked += 1
                for got, want, nm in (
                        (sums.h_lo[i + 1], look.hierarchy.sum_lower, "sum_h_lo"),
                        (sums.h_hi[i + 1], look.hierarchy.sum_upper, "sum_h_hi"),
                        (sums.s_lo[i + 1], look.success.sum_lower, "sum_s_lo"),
                        (sums.s_hi[i + 1], look.success.sum_upper, "sum_s_hi"),
                        (a.l_h[i], look.hierarchy.lower, "L_h"),
                        (a.u_h[i], look.hierarchy.upper, "U_h"),
                        (a.l_s[i], look.success.lower, "L_s"),
                        (a.u_s[i], look.success.upper, "U_s")):
                    if float(got) != float(want):
                        fails.append(f"{cell.id}/p{program} tick {i + 1} {nm}: "
                                     f"v2 {got!r} != vband {want!r}")
                if fails:
                    return fails
            # the two baselines, from their definitions, at every tick
            positions = np.arange(1, n_pairs + 1, dtype=np.int64)
            for t in range(1, fin + 1):
                done = (positions + draw.d) <= t
                m = int(done.sum())
                k = int(np.argmin(done)) if not done.all() else n_pairs
                for nm, idx_want, sh_want in (
                        (CPREFIX, k, int(draw.z[:k].sum())),
                        (NAIVE, m, int(draw.z[done].sum()))):
                    s = series[nm]
                    if int(s.index[t - 1]) != idx_want:
                        fails.append(f"{cell.id}/p{program} tick {t}: {nm} index "
                                     f"{int(s.index[t - 1])} != {idx_want}")
                    got = s.l_h[t - 1]
                    want = _band(np.array([float(sh_want)]),
                                 np.array([float(sh_want)]),
                                 np.array([idx_want]), cfg.radius)[0][0]
                    if float(got) != float(want):
                        fails.append(f"{cell.id}/p{program} tick {t}: {nm} L_h "
                                     f"{got!r} != {want!r}")
                if fails:
                    return fails
    if verbose:
        print(f"  v2 drain: {checked} ticks cross-checked against "
              f"vband.ValidationMonitor at strict float equality, of which "
              f"{drain_checked} are drain ticks v1 never evaluated: "
              f"{len(fails)} mismatch(es)")
    return fails


def selfcheck_brute_force(n_pairs: int = 300, verbose: bool = True) -> List[str]:
    """The incremental machinery against a direct look-by-look recomputation.

    ``vband`` covers the ADAPTER only.  This covers what it cannot: the
    difference-array running sums at a realistic prefix, the CPREFIX index
    ``k(t) = max{k : every pair 1..k is fully resolved}``, the completed count
    ``m`` and the completed-only sums, each recomputed from scratch at every
    look by the definition in PROTOCOL 3.
    """
    fails: List[str] = []
    cfg = make_config(n_pairs, vgen.NAMESPACE_SMOKE)
    for cell in vgen.CELLS[:4]:
        draw = vgen.draw_trial(cell, 11, 1, n_max=n_pairs,
                               namespace=vgen.NAMESPACE_SMOKE)
        sums = vgen.adapter_prefix_sums(draw, n_pairs)
        resolved, revealed, cprefix, _rm = vgen.resolution_counts(draw, n_pairs)
        naive_h = vgen.completed_sums(draw, draw.z, n_pairs)
        for n in range(1, n_pairs + 1):
            positions = np.arange(1, n + 1, dtype=np.int64)
            sub = vgen.TrialDraw(
                cell=cell, namespace=draw.namespace, program_index=11,
                trial_index=1, n=n, atom=draw.atom[:n], z=draw.z[:n],
                dsc=draw.dsc[:n], d=draw.d[:n], f=draw.f[:n],
                cand_first=draw.cand_first[:n], s_rev=draw.s_rev[:n],
                c_rev=draw.c_rev[:n], c_pend=draw.c_pend[:n],
                a_narrow=draw.a_narrow[:n], a_collapse=draw.a_collapse[:n])
            st = vgen.state_at_age(sub, n - positions)
            done = draw.d[:n] <= (n - positions)
            m = int(done.sum())
            k = 0
            for j in range(n):
                if not done[j]:
                    break
                k = j + 1
            if float(sums.h_lo[n]) != float(st.h_lo.sum(dtype=np.int64)):
                fails.append(f"{cell.id} n={n}: incremental h_lo sum differs")
            if float(sums.s_hi[n]) != float(st.s_hi.sum(dtype=np.int64)):
                fails.append(f"{cell.id} n={n}: incremental s_hi sum differs")
            if int(resolved[n]) != m:
                fails.append(f"{cell.id} n={n}: completed count {resolved[n]} != {m}")
            if int(cprefix[n]) != k:
                fails.append(f"{cell.id} n={n}: CPREFIX index {cprefix[n]} != {k}")
            if float(naive_h[n]) != float(draw.z[:n][done].sum(dtype=np.int64)):
                fails.append(f"{cell.id} n={n}: completed-only sum differs")
            if int(revealed[n]) != int((draw.f[:n] <= (n - positions)).sum()):
                fails.append(f"{cell.id} n={n}: revealed count differs")
            if fails:
                return fails
    if verbose:
        print(f"  brute-force: {4 * n_pairs} looks recomputed from the "
              f"definitions, 0 mismatch(es)")
    return fails


def selfcheck(n_pairs: int = 35, programs: int = 2,
              verbose: bool = True) -> List[str]:
    """The accelerator is exactly ``vband``, or these numbers are void.

    Drives ``vband.ValidationMonitor`` over whole trials, event by event, and
    asserts STRICT FLOAT EQUALITY of every band endpoint, every enclosure
    endpoint and every decision at every look against the vectorized path this
    module runs the grid with.  Also re-runs one trial twice and asserts the
    streams are identical, and checks the radius table against
    ``vband.radius_from_formula`` at strict equality.
    """
    fails: List[str] = []
    cfg = make_config(n_pairs, vgen.NAMESPACE_SMOKE)
    checked = 0
    for cell in vgen.CELLS:
        for program in range(programs):
            draw = vgen.draw_trial(cell, program, 0, n_max=n_pairs,
                                   namespace=vgen.NAMESPACE_SMOKE)
            sums = vgen.adapter_prefix_sums(draw, n_pairs)
            idx = np.arange(1, n_pairs + 1)
            l_h, u_h = _band(sums.h_lo[1:], sums.h_hi[1:], idx, cfg.radius)
            l_s, u_s = _band(sums.s_lo[1:], sums.s_hi[1:], idx, cfg.radius)
            mon, looks = _drive_vband(draw, n_pairs)
            for i, look in enumerate(looks):
                checked += 1
                pairs = ((sums.h_lo[i + 1], look.hierarchy.sum_lower, "sum_h_lo"),
                         (sums.h_hi[i + 1], look.hierarchy.sum_upper, "sum_h_hi"),
                         (sums.s_lo[i + 1], look.success.sum_lower, "sum_s_lo"),
                         (sums.s_hi[i + 1], look.success.sum_upper, "sum_s_hi"),
                         (l_h[i], look.hierarchy.lower, "L_h"),
                         (u_h[i], look.hierarchy.upper, "U_h"),
                         (l_s[i], look.success.lower, "L_s"),
                         (u_s[i], look.success.upper, "U_s"))
                for got, want, name in pairs:
                    if float(got) != float(want):
                        fails.append(f"{cell.id}/p{program} look n={i + 1} "
                                     f"{name}: vectorized {got!r} != vband {want!r}")
                decision = vband.decide(look.hierarchy, look.success)
                mine = DEPLOY if (idx[i] >= cfg.n_min and l_h[i] > 0
                                  and l_s[i] > -cfg.delta) else (
                    RETAIN_INCUMBENT if (idx[i] >= cfg.n_min and u_h[i] < 0)
                    else NO_DECISION)
                if DECISION_LABEL[mine].replace("NO_DECISION", "CONTINUE") != \
                        decision:
                    fails.append(f"{cell.id}/p{program} look n={i + 1}: decision "
                                 f"{DECISION_LABEL[mine]} != vband {decision}")
            state = vgen.state_at_age(draw, n_pairs - np.arange(1, n_pairs + 1))
            for k, pair in enumerate(mon.pairs):
                got = (pair.hierarchy.lo, pair.hierarchy.hi,
                       pair.success.lo, pair.success.hi)
                want = (float(state.h_lo[k]), float(state.h_hi[k]),
                        float(state.s_lo[k]), float(state.s_hi[k]))
                if got != want:
                    fails.append(f"{cell.id}/p{program} pair {k + 1} enclosure "
                                 f"{got} != vband {want}")
            last = looks[-1]
            n_res = int(state.resolved.sum())
            if last.n_certified != n_res:
                fails.append(f"{cell.id}/p{program}: certified {last.n_certified}"
                             f" != {n_res}")
            if last.n_point_resolved != n_res + int(state.cost_collapsed.sum()):
                fails.append(f"{cell.id}/p{program}: point-resolved count differs")
    # the radius table is the pinned primitive, at strict equality
    for n in sorted({1, 2, max(n_pairs // 2, 1), n_pairs}):
        if cfg.radius[n] != vband.radius_from_formula(n):
            fails.append(f"radius({n}) differs from vband")
    # two draws of the same stream are identical
    a = vgen.draw_trial(vgen.CELLS[3], 7, 2, n_max=200,
                        namespace=vgen.NAMESPACE_SMOKE)
    b = vgen.draw_trial(vgen.CELLS[3], 7, 2, n_max=200,
                        namespace=vgen.NAMESPACE_SMOKE)
    for name in ("atom", "d", "f", "cand_first"):
        if not np.array_equal(getattr(a, name), getattr(b, name)):
            fails.append(f"the stream is not reproducible in {name}")
    if verbose:
        print(f"  cross-checked {checked} looks against vband.ValidationMonitor "
              f"at strict float equality: {len(fails)} mismatch(es)")
    return fails


# ---------------------------------------------------------------------------
# The missed-crossing witness, as a runnable report
# ---------------------------------------------------------------------------
#: The exact lower bound both baselines stand at, at the missed tick of the
#: horizon-1,000 witness: ``clip(100/600 - r(600), -1, 1)``.  Pinned as a literal
#: so that a change of the radius, the clip, the index or the block sizes is a
#: test failure and not a silently different number.  The root's disposition
#: prints it rounded to ten places as +0.0133027164.
WITNESS_LOWER_BOUND_1000 = 0.013302716411199761
WITNESS_TICK_1000 = 1010
WITNESS_INDEX_1000 = 600


def witness_report(n_max: int = 1000) -> Dict[str, object]:
    """The witness, both schedules, as data.  Draws nothing and writes nothing."""
    draw = vgen.build_missed_crossing_witness(n_max)
    cfg = make_config(n_max, vgen.NAMESPACE_FIXTURE)
    cell = draw.cell
    out: Dict[str, object] = {
        "n_max": n_max, "finalization_tick": cfg.finalization_tick,
        "drain_interior": [n_max + 1, cfg.finalization_tick - 1],
        "reachability": vgen.witness_reachability(draw),
        "blocks": [list(b) for b in vgen.MISSED_CROSSING_BLOCKS[n_max]],
        "by_schedule": {},
    }
    for sched in SCHEDULES:
        series, _, _, _ = build_series_for(draw, cfg, sched)
        recs, _, _ = evaluate_trial(draw, cfg, sched)
        per: Dict[str, object] = {}
        for name in CONSTRUCTIONS:
            s, r = series[name], recs[name]
            elig = s.index >= cfg.n_min
            fired = (elig & (s.l_h > 0.0) & (s.l_s > -cfg.delta)) | (elig & (s.u_h < 0.0))
            first = int(np.argmax(fired)) if fired.any() else None
            per[name] = {
                "looks": int(s.index.size),
                "decision": DECISION_LABEL[r.decision],
                "tau_prefix": r.tau, "tau_tick": r.tau_tick,
                "decided_in_drain": r.decided_in_drain,
                "ever_miscover_h": r.ever_miscover_h,
                "ever_miscover_s": r.ever_miscover_s,
                "first_firing_tick": None if first is None else int(s.tick[first]),
                "first_firing_index": None if first is None else int(s.index[first]),
                "L_h_at_first_firing": None if first is None else float(s.l_h[first]),
                "L_s_at_first_firing": None if first is None else float(s.l_s[first]),
                "max_L_h_over_all_looks": float(s.l_h.max()),
                "firing_looks": int(fired.sum()),
            }
        out["by_schedule"][sched] = per
    out["truth"] = {"mu_h": cell.mu_h, "mu_s": cell.mu_s}
    return out


def report_missed_crossing_witness(n_max: int = 1000) -> bool:
    """Print the witness and return True iff v2 sees what v1 missed."""
    rep = witness_report(n_max)
    reach = rep["reachability"]
    print("=" * 78)
    print("THE MISSED-CROSSING WITNESS (root disposition section B)")
    print("=" * 78)
    print(f"  cell {reach['cell']} = {reach['law']}/{reach['delay_rule']}, "
          f"N_max = {rep['n_max']:,}, finalization tick "
          f"{rep['finalization_tick']:,}, drain interior "
          f"{rep['drain_interior'][0]:,}..{rep['drain_interior'][1]:,}")
    for lo, hi, atom, tick in rep["blocks"]:
        z, dsc = vgen.ATOM_TABLE[atom][4], vgen.ATOM_TABLE[atom][5]
        when = "enrollment" if tick == 0 else f"tick {tick:,}"
        print(f"    pairs {lo:>5,}-{hi:<5,} {atom:<4} Z={z:+d} D={dsc:+d}  "
              f"resolve at {when}")
    print(f"  SHORT offsets {reach['short_offsets_used']} in support "
          f"{reach['short_support']}: {reach['every_short_offset_in_support']}; "
          f"LONG offsets {reach['long_offsets_used']} in support "
          f"{reach['long_support']}: {reach['every_long_offset_in_support']}")
    print(f"  f == d (first reveal is the full reveal, probability 1/(d+1) > 0): "
          f"{reach['first_reveal_equals_full_reveal']}; atoms {reach['atoms_used']} "
          f"all carry positive weight: {reach['every_atom_has_positive_weight']}")
    print(f"  realized sum Z = {reach['realized_sum_z']}, sum D = "
          f"{reach['realized_sum_d']}, against the truth mu_h = "
          f"{reach['true_mu_h']:+.4f}, mu_s = {reach['true_mu_s']:+.4f}")
    for sched in SCHEDULES:
        print(f"\n  {sched}  --  {SCHEDULE_LABEL[sched]}")
        for name in CONSTRUCTIONS:
            p = rep["by_schedule"][sched][name]
            tick = "-" if p["first_firing_tick"] is None else f"{p['first_firing_tick']:,}"
            lo = "-" if p["L_h_at_first_firing"] is None \
                else f"{p['L_h_at_first_firing']:+.12f}"
            ls = "-" if p["L_s_at_first_firing"] is None \
                else f"{p['L_s_at_first_firing']:+.12f}"
            print(f"    {name:<8} looks={p['looks']:>6,}  "
                  f"{p['decision']:<16} tau_prefix={p['tau_prefix']:<6,} "
                  f"tau_tick={p['tau_tick']:<6,} drain={str(p['decided_in_drain']):<5} "
                  f"miscover_h={str(p['ever_miscover_h']):<5} "
                  f"miscover_s={str(p['ever_miscover_s']):<5}")
            print(f"             first firing tick {tick:>7}  L_h={lo}  L_s={ls}  "
                  f"firing looks {p['firing_looks']}")
    v1 = rep["by_schedule"][SCHEDULE_V1]
    v2 = rep["by_schedule"][SCHEDULE_V2]
    ok = all(v1[b]["decision"] == "NO_DECISION" and not v1[b]["ever_miscover_h"]
             and v2[b]["decision"] == "DEPLOY" and v2[b]["ever_miscover_h"]
             and v2[b]["ever_miscover_s"] for b in (CPREFIX, NAIVE))
    print(f"\n  v1 misses the crossing and v2 catches it, for BOTH baselines: {ok}")
    return ok


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def positive_control(rows: List[Dict[str, object]]) -> Dict[str, object]:
    """PROTOCOL 9.4, precommitted and frozen before any outcome existed."""
    cells = ("C2", "C4", "C6")
    flagged = []
    for r in rows:
        if (r["construction"] == NAIVE and r.get("gate") == "hierarchy"
                and r.get("event") == "ever_miscover"
                and r.get("looks") == "all" and r["cell"] in cells):
            if r["flagged"]:
                flagged.append(r["cell"])
    passed = bool(flagged)
    return {
        "statement": ("NAIVE's hierarchy ever-miscoverage must be FLAGGED in at "
                      "least one of C2, C4, C6"),
        "flagged_cells": flagged,
        "passed": passed,
        "consequence_if_failed": (
            "the measurement apparatus itself is reported as unvalidated, the "
            "ADAPTER results of this run are reported as uninterpretable, and "
            "the cause is investigated before any of them is cited"),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    ap.add_argument("--smoke", type=int, default=None, metavar="N",
                    help="run only the measurement-only smoke run, with N programs")
    ap.add_argument("--selfcheck", action="store_true",
                    help="cross-check the accelerator against vband and stop")
    ap.add_argument("--cells", default=None,
                    help="ad-hoc: restrict to these cell ids")
    ap.add_argument("--programs", type=int, default=None,
                    help="ad-hoc: programs per cell")
    ap.add_argument("--n-max", type=int, default=None, help="ad-hoc: horizon")
    ap.add_argument("--tier", default=None, help="ad-hoc: force a budget tier")
    ap.add_argument(
        "--schedule", default=RUNNER_DEFAULT_SCHEDULE,
        choices=list(PRIMARY_PANEL_SCHEDULES),
        help=("the declared legal event schedule. Default "
              f"{RUNNER_DEFAULT_SCHEDULE!r} (the v2 primary: one look per tick "
              "through the finalization window, simultaneous events batched). "
              f"{SCHEDULE_V1!r} reproduces the deposited v1 results and is kept "
              "so the two can be run side by side; it is preserved, not "
              f"primary. {SCHEDULE_V2_FINEST!r} is DEFERRED AND DISABLED and is "
              "deliberately not offered here: its completed-prefix iterator "
              "emits states unattainable under any tie order. Its code and its "
              "failing check are preserved as development evidence."))
    ap.add_argument("--witness", action="store_true",
                    help="run the missed-crossing witness and the two schedule "
                         "reductions, print them, and stop. Draws no grid.")
    args = ap.parse_args(argv)

    # Defence in depth: argparse ``choices`` already excludes the deferred
    # sensitivity, but ``main`` is also called programmatically, and a disabled
    # schedule must be refused on every route into a run, not only on the one
    # the command line happens to take.
    check_primary_panel_schedule(args.schedule)

    if args.witness:
        return 0 if report_missed_crossing_witness() else 1

    if args.selfcheck:
        print("vrun selfcheck: the vectorized path against vband, event by event")
        fails = selfcheck()
        fails += selfcheck_brute_force()
        fails += selfcheck_v2_drain()
        for f in fails[:20]:
            print(f"  MISMATCH {f}")
        print(f"\nvgen against the frozen PROTOCOL 6 tables:")
        report = vgen.selfcheck_report(verbose=False)
        print(f"  boundary states between the 2.5 readings: "
              f"{report['boundary_states']} (PROTOCOL 2.5 states 128)")
        for reading in vgen.READINGS:
            print(f"  {reading}: {len(report[reading])} disagreement(s)")
        return 1 if fails else 0

    overrides = (args.cells is not None or args.programs is not None
                 or args.n_max is not None or args.tier is not None
                 or (args.smoke is not None and args.smoke != 20))
    reported = not overrides
    # An ad-hoc run never draws from namespace 0.  The reported grid's streams
    # stay unseen until the reported grid runs (PROTOCOL 5, 8.1).
    grid_namespace = vgen.NAMESPACE_GRID if reported else vgen.NAMESPACE_SMOKE
    guard = WriteGuard(Path(args.out), reported=reported)
    cfg_json = json.loads(CELLS_JSON.read_text())
    started = time.time()
    print(f"live_ab_validation grid runner -> {guard.root}")
    print(f"  reported grid: {reported} (grid namespace {grid_namespace})")

    # ---- 1. the fixture gate ------------------------------------------------
    # The gate is FAIL-CLOSED FOR THE REPORTED GRID and carries no exemption for
    # any case.  It is evaluated here and enforced at step 4, immediately before
    # the grid draws its first namespace-0 stream, because the measurement-only
    # smoke run of PROTOCOL 8.1 produces no reported quantity and 8.2 requires
    # budget.json to be written BEFORE the grid starts.  Deferring the raise by
    # two measurement-only steps is not an exemption: no failing case ever lets
    # the grid run.
    fixtures = None
    fixture_failures: List[str] = []
    if reported:
        print("\n[1/6] fixture gate (PROTOCOL 11)")
        fixtures = run_fixture_gate(guard)
        fixture_failures = sorted(k for k, v in fixtures["cases"].items()
                                  if v != "pass")
        if fixtures["returncode"] != 0 and not fixture_failures:
            fixture_failures = ["<the fixture command failed without naming a case>"]
        print(f"  {fixtures['passed']}/{fixtures['total']} fixtures passed")
        if fixture_failures:
            print(f"  GATE CLOSED: {fixture_failures}")
            print("  The reported grid does not run until they pass. The gate "
                  "carries no exemption for any case, because a gate with an "
                  "exemption is the defect this study exists to find. The "
                  "measurement-only steps 2 and 3 still run, and budget.json "
                  "records the gate as closed.")

    # ---- 2. the smoke run ---------------------------------------------------
    n_smoke = args.smoke if args.smoke is not None else 20
    print(f"\n[2/6] smoke run (PROTOCOL 8.1), namespace {vgen.NAMESPACE_SMOKE}, "
          f"{n_smoke} programs, measuring runtime and memory only, "
          f"under schedule {args.schedule}")
    smoke = run_smoke(guard, n_smoke, schedule=args.schedule)
    assert_smoke_holds_no_effect_record(guard)
    incremental = assert_incremental(smoke)
    print(f"  peak RSS {smoke['peak_rss_bytes'] / 2**20:.0f} MiB; "
          f"{incremental['enclosure_updates_per_pair_max']:.2f} enclosure "
          f"updates per pair (bound {vgen.BREAKPOINTS_PER_PAIR})")

    # ---- 3. the budget ladder ----------------------------------------------
    print("\n[3/6] budget ladder (PROTOCOL 8.2), written before the grid runs")
    budget = select_tier(smoke, cfg_json)
    budget["incremental_property"] = incremental
    budget["smoke"] = smoke
    budget["protocol_smoke"] = smoke["protocol_smoke"]
    budget["fixture_gate"] = {
        "ran": fixtures is not None,
        "passed": None if fixtures is None else fixtures["passed"],
        "total": None if fixtures is None else fixtures["total"],
        "failing_cases": fixture_failures,
        "closed": bool(fixture_failures),
        "fail_closed_for_the_reported_grid": True,
        "exemptions": [],
    }
    # ---- the SEPARATE fail-closed total-workload resource guard ------------
    # Two different decisions, kept apart on purpose: the frozen scientific tier
    # selection above (primary projection only, unchanged), and this
    # authorization of the ENTIRE declared workload, which refuses.
    total_guard = total_workload_guard(budget, cfg_json)
    budget["total_workload_guard"] = total_guard
    budget["grid_may_start"] = bool(not fixture_failures
                                    and not budget["paused"]
                                    and total_guard["authorized"])
    if overrides:
        budget["reported_grid"] = False
        budget["note"] = ("this run carries grid overrides; it is a shakedown, "
                          "not the reported grid, and its tier is not a "
                          "PROTOCOL 8.2 selection")
    guard.write_json("budget.json", budget)
    if budget["beta"] is not None:
        print(f"  beta = {budget['beta']:.3f}; "
              f"s/program at 2000 = {budget['s_per_program_2000']:.3f}")
    for entry in budget["ladder"]:
        print(f"  {entry['tier']}: {entry['seconds_projected'] / 60:8.1f} min, "
              f"{entry['bytes_projected'] / 2**20:7.1f} MiB -> "
              f"{'admissible' if entry['admissible'] else 'over budget'}")
    print(f"  TOTAL-WORKLOAD GUARD (separate, fail-closed): "
          f"{'AUTHORIZED' if total_guard['authorized'] else 'REFUSED'}"
          + ("" if total_guard["authorized"]
             else f" [{total_guard['refusal_class']}]"))
    if args.smoke is not None:
        print(f"\nsmoke run complete; selected tier would be "
              f"{budget['selected_tier']}")
        return 0
    if budget["paused"] and not overrides:
        print("\nPAUSED: even T4 exceeds a hard limit. The run does not silently "
              "shrink further, does not drop a cell and does not reduce the "
              "number of constructions (PROTOCOL 8.2).")
        return 3

    # ---- 4. the reported grid ----------------------------------------------
    # The fail-closed TOTAL-workload guard runs before anything is executed, and
    # it raises rather than warning.  It is deliberately checked separately from
    # (and after) the frozen primary selection, so that a primary-admissible
    # tier whose TOTAL is unresolved or over cap still cannot start.
    enforce_total_workload_guard(total_guard)
    if fixture_failures:
        raise SystemExit(
            "the fixture gate is fail-closed and these cases did not pass: "
            f"{fixture_failures}. The reported grid does not run until they do. "
            "This module carries no exemption for any case, because a gate with "
            "an exemption is the defect this study exists to find. budget.json "
            "has been written with the PROTOCOL 8.1 measurement and the 8.2 "
            "projection, and records the gate as closed.")
    tier_name = args.tier or budget["selected_tier"]
    tier = next(t for t in cfg_json["budget"]["ladder"] if t["tier"] == tier_name)
    n_max = args.n_max if args.n_max is not None else tier["N_max"]
    cell_ids = (args.cells.split(",") if args.cells
                else [c["id"] for c in cfg_json["cells"]])
    grid = {cid: (args.programs if args.programs is not None
                  else tier["programs"][cid]) for cid in cell_ids}
    cfg = make_config(n_max, grid_namespace, schedule=args.schedule)
    # Bind the MEASUREMENT HARNESS that produced the budget, by hash.  The
    # protocol/resource review found the old inventory omitted the executing
    # harness, so a budget could not be traced to the code that measured it.
    harness = {
        "budget_measured_by": "vrun.run_smoke",
        "design": smoke.get("design"),
        "balanced": smoke.get("balanced"),
        "unique_programs": smoke.get("unique_programs"),
        "schedule_measured": smoke.get("event_schedule"),
        "harness_sha256": {name: sha256_file(HERE / name)
                           for name in ("vrun.py", "vgen.py", "vband.py")},
        "note": "The budget ladder is projected from the design named here. A "
                "budget measured under one schedule must not be read as the "
                "cost of another; v2 evaluates N_max+W looks per trial.",
    }
    write_manifest(guard, tier_name, cfg, grid, harness=harness)
    print(f"\n[4/6] the reported grid: tier {tier_name}, N_max {n_max}, "
          f"{sum(grid.values())} programs over {len(grid)} cells")
    print(f"      event schedule: {cfg.schedule}")
    print(f"      {SCHEDULE_LABEL[cfg.schedule]}")
    if cfg.schedule == SCHEDULE_V1:
        print("      v1 IS NOT THE PRIMARY. It is kept runnable so that the "
              "deposited v1 results can be reproduced and reported BESIDE v2 "
              "(PROTOCOL 14), not replaced by it.")

    sink = RowSink(guard.path("trials.csv.gz"), trial_header(cfg.schedule))
    totals = BlockCounts()
    per_cell_counts: Dict[str, Dict[str, int]] = {}
    mis_rows: List[Dict[str, object]] = []
    dec_rows: List[Dict[str, object]] = []
    time_rows: List[Dict[str, object]] = []
    unres_rows: List[Dict[str, object]] = []
    hor_rows: List[Dict[str, object]] = []
    determinism_block: Optional[Tuple[str, range, bytes]] = None
    limits = cfg_json["budget"]["hard_limits"]

    for cid in cell_ids:
        cell = vgen.CELL_BY_ID[cid]
        n_programs = grid[cid]
        acc = CellAccumulator(cell, n_programs * cfg.trials_per_program,
                              cfg.horizons, schedule=cfg.schedule)
        cell_counts = BlockCounts()
        t0 = time.perf_counter()
        for start in range(0, n_programs, 100):
            block = range(start, min(start + 100, n_programs))
            if determinism_block is None:
                sink.start_retaining()
            cell_counts.add(run_block(cell, block, cfg, sink, acc))
            if determinism_block is None:
                determinism_block = (cid, block, sink.stop_retaining())
            rss = peak_rss_bytes()
            if rss > limits["peak_rss_bytes"]:
                raise SystemExit(f"peak RSS {rss} exceeds the frozen 2 GiB limit; "
                                 f"the run stops and reports what it has")
            written = guard.total_bytes()
            if written > limits["output_bytes"]:
                raise SystemExit(f"output bytes {written} exceed the frozen "
                                 f"200 MiB limit; the run stops and reports")
        totals.add(cell_counts)
        per_cell_counts[cid] = cell_counts.as_dict()
        mis_rows.extend(miscoverage_rows(acc))
        dec_rows.extend(decision_rows(acc, cfg.delta))
        time_rows.extend(decision_time_rows(acc))
        unres_rows.extend(unresolved_rows(acc))
        hor_rows.extend(horizon_rows(acc))
        print(f"  {cid} {cell.law}/{cell.delay}: {n_programs} programs, "
              f"{cell_counts.trials} trials in {time.perf_counter() - t0:.1f}s")
        del acc
    sink.close()

    # ---- 5. determinism ------------------------------------------------------
    print("\n[5/6] determinism: re-running one cell block and comparing bytes")
    cid, block, first_bytes = determinism_block
    replay = RowSink(None, "", discard=True)
    replay.start_retaining()
    run_block(vgen.CELL_BY_ID[cid], block, cfg, replay, None)
    second_bytes = replay.stop_retaining()
    replay.close()
    identical = first_bytes == second_bytes
    print(f"  {cid} programs {block.start}-{block.stop - 1}: "
          f"{len(first_bytes)} bytes, identical = {identical}")
    if not identical:
        raise SystemExit("the run is not deterministic; its outputs are void")

    # ---- 6. the reported tables ---------------------------------------------
    print("\n[6/6] writing the reported tables")
    caption = ("Coverage here is coverage of a BOUNDED ARBITRARY-RUNNING-MEAN "
               "target of a synthetic stream and establishes nothing causal; "
               "NAIVE is INVALID under informative delay and is reported only "
               "to exhibit the failure mode; an unflagged row means no "
               "exceedance was detected at this resolution, never that the "
               "bound holds.")
    write_csv(guard, "miscoverage.csv", mis_rows, "PROTOCOL 9.1. " + caption)
    write_csv(guard, "decisions.csv", dec_rows, "PROTOCOL 9.2. " + caption)
    write_csv(guard, "decision_time.csv", time_rows,
              "PROTOCOL 9.5. THREE DISTINCT COORDINATES, never interchangeable: "
              "tau is the DECISION PREFIX in ENROLLED PAIRS; tau_tick is the "
              "ELAPSED CALENDAR TICK of the same look; and the baseline sample "
              "index is the COMPLETED count (k for CPREFIX, m for NAIVE), which "
              "is not the enrolled prefix once the drain begins. v1 emitted one "
              "number for all three, which was harmless only because v1 never "
              "looked anywhere they differ. Neither tick nor prefix is ever wall "
              "clock, and none of these is a paired comparison between "
              "constructions.")
    write_csv(guard, "unresolved.csv", unres_rows,
              "PROTOCOL 9.5: resolution quantities at the deciding look, or at "
              "the finalization look for non-deciding trials.")
    write_csv(guard, "horizon_summaries.csv", hor_rows,
              "PROTOCOL 9.6. " + caption)
    control = positive_control(mis_rows)
    compute = {
        "timing": {"wall_clock_seconds": time.time() - started,
                   "started_unix": started},
        "peak_rss_bytes": peak_rss_bytes(),
        "output_bytes": guard.total_bytes(),
        "per_cell": per_cell_counts,
        "total": totals.as_dict(),
        "tier": tier_name,
        "N_max": n_max,
        "determinism_check": {
            "cell": cid, "programs": [block.start, block.stop - 1],
            "bytes_compared": len(first_bytes), "identical": identical,
            "scope": ("one cell block was re-run from its seed coordinates and "
                      "its per-trial records compared byte for byte"),
            "files_that_cannot_be_byte_identical_between_runs": [
                "compute.json (its timing fields)",
                "budget.json (it IS the smoke measurement and the projection)",
                "smoke/timing.json (the same measurement)"],
            "files_that_are_byte_identical_between_runs": [
                "trials.csv.gz", "miscoverage.csv", "decisions.csv",
                "decision_time.csv", "unresolved.csv", "horizon_summaries.csv",
                "manifest.json", "fixtures_report.json"]},
        "positive_control": control,
        "fixtures": None if fixtures is None else
        {"passed": fixtures["passed"], "total": fixtures["total"]},
        "reported_grid": reported,
    }
    guard.write_json("compute.json", compute)
    print(f"\npositive control (PROTOCOL 9.4): "
          f"{'PASSED' if control['passed'] else 'NOT MET'}; "
          f"flagged in {control['flagged_cells'] or 'no cell'}")
    if not control["passed"]:
        print("  " + control["consequence_if_failed"])
    print(f"wrote {guard.total_bytes() / 2**20:.1f} MiB to {guard.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
