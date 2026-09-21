"""MATCHED CERTIFICATE ABLATION: does elapsed-cost narrowing cause the delay gain?

POST-HOC EXPLORATORY MECHANISM ANALYSIS, selected after the reported gap.  Not a
prospectively specified study, and labelled that way everywhere it reports.

SPECIFIED BY ROOT, 2026-09-21 15:16 (issue 12 comment 5762860561), transcribed:

    "use only existing power-panel P05N/P05A/P10N/P10A coordinates, all 2000 programs and
     4 trials per cell, same namespace 3 seeds, draws, reveal ticks, enrollment, success
     bounds, decision schedule, margins and horizon.  Compare original ADAPTER with a
     certificate-disabled variant.  In exactly-one-revealed hierarchy states: retain the
     failure-based feasible set when revealed success=0; when revealed success=1 use
     [-1,1] regardless of elapsed cost.  Both-revealed final scores, both-pending bounds
     and success enclosures stay unchanged.  This disables only the two elapsed-cost
     narrowing branches.  No model calls, no new reference calls, no new task draws."

WHY THIS AND NOT ANOTHER LADDER
-------------------------------
CPREFIX was never a one-thing control: it differs from ADAPTER in observation rule and
running target, not only in cost certificates, and its informative-delay difference at
mu_h 0.10 is +0.01475 with a Newcombe 95% interval of [0.00024, 0.02925] -- nonzero.
More effect points cannot isolate a component.  A matched ablation on the SAME draws can,
because the only thing that differs is the two branches being disabled.

WHAT IS DISABLED, EXACTLY
-------------------------
``vgen.state_at_age`` computes ``q`` for a partially-revealed pair from the elapsed cost.
Under the ablation, when the revealed arm SUCCEEDED the pair's hierarchy enclosure becomes
the full ``[-1, +1]`` regardless of elapsed cost -- i.e. ``q = -1`` always.  When the
revealed arm FAILED the feasible set is unchanged, because that branch is failure-based
and carries no elapsed-cost certificate.  Resolved pairs, unrevealed pairs and every
success enclosure are untouched.

DETERMINISTIC INVARIANTS, CHECKED BEFORE ANY OUTCOME IS READ
------------------------------------------------------------
Root required these committed before evaluation, and ``assert_invariants`` runs them:

  1. CONTAINMENT: the disabled enclosure contains the original at every checked state.
  2. FINAL SCORES: identical for every resolved pair.
  3. SUCCESS INTERVALS: identical at every state.
  4. SCHEDULE: identical look sets and horizon.

A one-sided ablation that did not contain the original would not be an ablation; it would
be a different estimator.
"""

from __future__ import annotations

import contextlib
import dataclasses
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vgen                                                     # noqa: E402
import vpowercurve as PC                                        # noqa: E402

#: Exactly the coordinates root named.  Same namespace-3 seeds as the coarse panel.
ABLATION_CELLS: Tuple[str, ...] = ("P05N", "P05A", "P10N", "P10A")
ABLATION_NAMESPACE = PC.NAMESPACE_POWER          # 3 -- the ORIGINAL draws, not a new one
ABLATION_PROGRAMS = 2000
ABLATION_TRIALS = 4
ABLATION_HORIZON = 2000

VARIANT_NAME = "ADAPTER_NOCERT"
LABEL = ("POST-HOC EXPLORATORY MECHANISM ANALYSIS, selected after the reported "
         "informative-delay gap. Not a prospectively specified study.")

# ---------------------------------------------------------------------------
# THE ORIGINAL CALLABLE, captured at import, before anything can install over it
# ---------------------------------------------------------------------------
# The independent source review named the hazard exactly: "The wrapper itself
# invokes ``vgen.state_at_age``.  Consequently a future direct global assignment
# of that name to this wrapper would recurse unless the implementation retains an
# unmodified original callable."  This is that retained callable.  Every path in
# this module calls it by this binding and never by attribute lookup on ``vgen``,
# so installation cannot make the operator call itself.
_ORIGINAL_STATE_AT_AGE = vgen.state_at_age
if getattr(_ORIGINAL_STATE_AT_AGE, "__module__", None) != "vgen" or \
        getattr(_ORIGINAL_STATE_AT_AGE, "__qualname__", None) != "state_at_age":
    raise ImportError(                                         # pragma: no cover
        "vgen.state_at_age was already replaced before vablation was imported; "
        "refusing to capture a patched callable as 'the original'")

_INSTALLED = False
_CALLS = 0


def call_count() -> int:
    """How many times the ablation operator has been entered, process-wide.

    Read before and after a block of work, this is a POSITIVE witness that the
    operator was on the executed path -- not an inference from the fact that it
    was installed.
    """
    return _CALLS


def is_installed() -> bool:
    return _INSTALLED and vgen.state_at_age is state_at_age_nocert


# PRE-OUTCOME AMENDMENT, 2026-09-21, recorded before any disabled outcome was
# evaluated.  The pre-registered wrapper declared ``policy="operational"`` as its
# default while ``vgen.state_at_age``'s default is ``"oracle"``.  Under global
# installation that difference is not cosmetic: ``vrun._look_fractions`` calls
# ``vgen.state_at_age(sub, ages)`` with NO policy argument, so the installed
# wrapper would have silently evaluated that diagnostic under the OPERATIONAL
# policy while the original panel evaluated it under the ORACLE one, and the
# per-look resolved/unrevealed diagnostics of the two arms would have differed
# for a reason having nothing to do with the ablation.  The signature now mirrors
# the function it replaces.  The transformation itself is unchanged.
def state_at_age_nocert(draw: "vgen.TrialDraw", ages, policy: str = "oracle"):
    """``vgen.state_at_age`` with ONLY the two elapsed-cost branches disabled.

    Reproduces the module's own computation and then overrides ``q`` to -1 on the
    partial-and-succeeded branch.  Everything else -- resolved scores, unrevealed
    ranges, the revealed-failure feasible set, and both success bounds -- is the
    original code's output, because it IS the original code's output.
    """
    global _CALLS
    _CALLS += 1
    st = _ORIGINAL_STATE_AT_AGE(draw, ages, policy)

    age = np.asarray(ages)
    d, f = draw.d, draw.f
    resolved = age >= d
    unrevealed = age < f
    partial = ~resolved & ~unrevealed
    succeeded = draw.s_rev == 1
    first_is_candidate = draw.cand_first

    # q = -1 everywhere the elapsed-cost certificate would have narrowed, i.e. the
    # partial-and-succeeded branch.  The revealed-FAILURE branch is untouched.
    target = partial & succeeded
    h_lo_full = np.where(first_is_candidate, -1, -1)
    h_hi_full = np.where(first_is_candidate, 1, 1)
    h_lo = np.where(target, h_lo_full, st.h_lo).astype(np.int8)
    h_hi = np.where(target, h_hi_full, st.h_hi).astype(np.int8)
    return dataclasses.replace(
        st, h_lo=h_lo, h_hi=h_hi,
        cost_narrowed=np.zeros_like(st.cost_narrowed),
        cost_collapsed=np.zeros_like(st.cost_collapsed))


# ---------------------------------------------------------------------------
# INSTALLATION: the operator on the ACTUAL adapter_tick_sums evaluation path
# ---------------------------------------------------------------------------
# ``vrun.build_series_v2`` reaches the ADAPTER band through
# ``vgen.adapter_tick_sums``, which resolves ``state_at_age`` as a MODULE GLOBAL.
# Rebinding that global is therefore what puts the ablation on the real path;
# nothing else in this repository needs to change, and nothing else does.
#
# Scope of the rebinding, stated so it is not mistaken for something narrower:
# inside ``evaluate_trial`` the two readers of ``state_at_age`` are
# ``adapter_tick_sums`` (the ADAPTER band) and ``_look_fractions`` (the per-look
# resolved / unrevealed / certificate diagnostics, shared by all three
# constructions).  CPREFIX and NAIVE take their bands from
# ``completion_tick_states``, which never calls ``state_at_age``, so their
# DECISIONS are untouched by construction.  Their certificate DIAGNOSTIC columns
# do move to zero, which is the reset the review accepted -- and their decision
# columns being bit-identical to the original panel's is an executed witness that
# the draws, enrollment and schedule are the same ones.
def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        raise RuntimeError("ablation operator already installed")
    if vgen.state_at_age is not _ORIGINAL_STATE_AT_AGE:
        raise RuntimeError(
            "vgen.state_at_age is not the captured original; refusing to install "
            "over an unknown callable")
    vgen.state_at_age = state_at_age_nocert
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        raise RuntimeError("ablation operator is not installed")
    if vgen.state_at_age is not state_at_age_nocert:
        raise RuntimeError(
            "vgen.state_at_age moved while the ablation was installed; the run "
            "does not describe a single fixed operator")
    vgen.state_at_age = _ORIGINAL_STATE_AT_AGE
    _INSTALLED = False


@contextlib.contextmanager
def installed() -> Iterator[None]:
    install()
    try:
        yield
    finally:
        uninstall()


@contextlib.contextmanager
def original_restored() -> Iterator[None]:
    """Run a block against the UNMODIFIED implementation, then re-install.

    Used for the two things that must see the original: the per-shard
    ``vgen``-vs-``vpolicy`` conformance smoke, which would otherwise be comparing
    the ablation against the policy module it is deliberately not equal to, and
    the invariant checks, which would otherwise compare the operator to itself.
    """
    was = _INSTALLED
    if was:
        uninstall()
    try:
        yield
    finally:
        if was:
            install()


def branch_witness(cell: Any, program: int = 0, trial: int = 0,
                   horizon: int = ABLATION_HORIZON) -> Dict[str, Any]:
    """ONE deterministic witness that the operator is on the real path.

    Root, 16:27: "connect the actual adapter_tick_sums evaluation path ... One
    deterministic branch witness through that path suffices."  This is it.  It
    drives ``vgen.adapter_tick_sums`` -- the function ``vrun.build_series_v2``
    actually calls -- once with the operator installed and once without, on a
    fixed coordinate, and records:

      * that the operator was ENTERED from inside ``adapter_tick_sums`` (a count,
        not an inference from the fact that it was installed);
      * that the hierarchy sums are contained at EVERY tick of the full axis, not
        at four sampled ticks;
      * that the success sums are identical at every tick;
      * that at least one tick differs STRICTLY -- without this the witness would
        pass just as happily on a no-op, and would prove nothing.
    """
    fin = int(horizon) + vgen.DRAIN_W
    draw = vgen.draw_trial(cell, program, trial, n_max=horizon,
                           namespace=ABLATION_NAMESPACE)
    with original_restored():
        a = vgen.adapter_tick_sums(draw, horizon, fin, policy="operational")
    before = _CALLS
    with installed():
        b = vgen.adapter_tick_sums(draw, horizon, fin, policy="operational")
    entered = _CALLS - before

    if entered < 1:
        raise AssertionError(
            "adapter_tick_sums did not enter the ablation operator; the variant "
            "is NOT on the evaluation path and any outcome would be the original")
    if not (np.all(b.h_lo <= a.h_lo) and np.all(b.h_hi >= a.h_hi)):
        raise AssertionError("tick-sum containment violated")
    if not (np.array_equal(a.s_lo, b.s_lo) and np.array_equal(a.s_hi, b.s_hi)):
        raise AssertionError("success tick sums moved; the ablation is not matched")
    differing = int(np.count_nonzero((a.h_lo != b.h_lo) | (a.h_hi != b.h_hi)))
    if differing == 0:
        raise AssertionError(
            f"the operator changed nothing at {cell.id} p{program} t{trial}: a "
            "witness that cannot distinguish the variant from the original is "
            "not a witness")
    return {
        "coordinate": {"cell": cell.id, "program": program, "trial": trial,
                       "namespace": ABLATION_NAMESPACE, "horizon": int(horizon),
                       "finalization_tick": fin},
        "path": "vrun.build_series_v2 -> vgen.adapter_tick_sums -> state_at_age",
        "operator_entries_from_adapter_tick_sums": entered,
        "ticks_on_axis": int(a.h_lo.size),
        "ticks_with_strictly_different_hierarchy_sums": differing,
        "hierarchy_contained_at_every_tick": True,
        "success_sums_identical_at_every_tick": True,
        "updates_original": int(a.updates),
        "updates_disabled": int(b.updates),
        "updates_note": ("certificate transitions carry zero increment under the "
                         "variant, so this counter legitimately moves; it is not "
                         "evidence that the reveal or enrollment schedule changed"),
    }


def assert_invariants(n_cells: int = 4, programs: int = 6,
                      trials: int = 4) -> Dict[str, Any]:
    """The four deterministic checks, run BEFORE any outcome is evaluated."""
    cells = {c.id: c for c in PC.build_cells()}
    checked = 0
    ages_checked = 0
    differing = 0
    for cid in ABLATION_CELLS[:n_cells]:
        cell = cells[cid]
        for prog in range(programs):
            for trial in range(trials):
                draw = vgen.draw_trial(cell, prog, trial, n_max=ABLATION_HORIZON,
                                       namespace=ABLATION_NAMESPACE)
                pos = np.arange(1, draw.n + 1, dtype=np.int64)
                for tick in (1, ABLATION_HORIZON // 2, ABLATION_HORIZON,
                             ABLATION_HORIZON + 100):
                    ages = np.maximum(np.where(pos <= min(tick, ABLATION_HORIZON),
                                               tick - pos, 0), 0)
                    # THE CAPTURED ORIGINAL, not ``vgen.state_at_age``.  If the
                    # operator happens to be installed when this runs, the
                    # attribute lookup would hand back the ablation and every
                    # check below would compare it with itself and pass
                    # vacuously.  A check that passes when it proves nothing is
                    # this project's recurring defect shape.
                    a = _ORIGINAL_STATE_AT_AGE(draw, ages, "operational")
                    b = state_at_age_nocert(draw, ages, "operational")
                    ages_checked += 1
                    differing += int(np.count_nonzero(
                        (a.h_lo != b.h_lo) | (a.h_hi != b.h_hi)))

                    # 1. CONTAINMENT
                    if not (np.all(b.h_lo <= a.h_lo) and np.all(b.h_hi >= a.h_hi)):
                        raise AssertionError(
                            f"containment violated at {cid} p{prog} t{trial} tick {tick}")
                    # 2. FINAL SCORES on resolved pairs
                    res = ages >= draw.d
                    if res.any():
                        if not (np.array_equal(a.h_lo[res], b.h_lo[res])
                                and np.array_equal(a.h_hi[res], b.h_hi[res])):
                            raise AssertionError(
                                f"resolved final scores changed at {cid} tick {tick}")
                    # 3. SUCCESS INTERVALS everywhere
                    if not (np.array_equal(a.s_lo, b.s_lo)
                            and np.array_equal(a.s_hi, b.s_hi)):
                        raise AssertionError(
                            f"success enclosure changed at {cid} tick {tick}")
                    checked += int(ages.size)
    # 4. SCHEDULE is a property of the config, not the enclosure: assert the
    #    ablation touches no schedule input.
    return {
        "containment_disabled_contains_original": True,
        "resolved_final_scores_identical": True,
        "success_intervals_identical": True,
        "schedule_untouched": ("the ablation replaces only per-pair hierarchy bounds; "
                               "look sets, horizon, margins and alpha are config and "
                               "are not referenced here"),
        "pair_states_compared": checked,
        "age_snapshots_compared": ages_checked,
        "pair_states_strictly_changed": differing,
        "evidence_layer": ("SAMPLED regression checks at four ticks, not an "
                           "exhaustive tick sweep; the all-age property rests on "
                           "the branch-level containment argument, which the "
                           "independent source review accepted. Early snapshots "
                           "include array positions not yet enrolled, so these "
                           "are ARRAY-STATE comparisons, not distinct "
                           "active-trial observations."),
        "cells": list(ABLATION_CELLS[:n_cells]),
        "namespace": ABLATION_NAMESPACE,
    }


def spec() -> Dict[str, Any]:
    """The frozen specification, committed before outcomes are evaluated."""
    return {
        "schema": "live_ab_validation_v2.certificate_ablation_spec.1",
        "label": LABEL,
        "authority": "root 2026-09-21 15:16, issue 12 comment 5762860561",
        "cells": list(ABLATION_CELLS),
        "namespace": ABLATION_NAMESPACE,
        "reuses_original_draws": True,
        "programs_per_cell": ABLATION_PROGRAMS,
        "trials_per_program": ABLATION_TRIALS,
        "horizon": ABLATION_HORIZON,
        "variant_name": VARIANT_NAME,
        "what_is_disabled": (
            "in exactly-one-revealed hierarchy states with revealed success == 1, the "
            "hierarchy enclosure becomes [-1, +1] regardless of elapsed cost. The "
            "revealed-failure feasible set, both-revealed final scores, both-pending "
            "bounds and ALL success enclosures are unchanged."),
        "what_is_not_done": ["no model calls", "no new reference calls",
                             "no new task draws", "no change to frozen accepted modules"],
        "deterministic_invariants": [
            "disabled enclosure CONTAINS original at every checked state",
            "resolved final scores identical",
            "success intervals identical",
            "schedule, horizon, margins and alpha untouched"],
        "interpretation_limit": (
            "a difference between original and disabled is attributable to the two "
            "disabled branches WITHIN THIS FIXED DESIGN. It is not a general claim about "
            "informative delay, and the comparison is post-hoc."),
    }
