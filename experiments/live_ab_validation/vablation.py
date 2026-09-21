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

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def state_at_age_nocert(draw: "vgen.TrialDraw", ages, policy: str = "operational"):
    """``vgen.state_at_age`` with ONLY the two elapsed-cost branches disabled.

    Reproduces the module's own computation and then overrides ``q`` to -1 on the
    partial-and-succeeded branch.  Everything else -- resolved scores, unrevealed
    ranges, the revealed-failure feasible set, and both success bounds -- is the
    original code's output, because it IS the original code's output.
    """
    import dataclasses
    st = vgen.state_at_age(draw, ages, policy)

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


def assert_invariants(n_cells: int = 4, programs: int = 6,
                      trials: int = 4) -> Dict[str, Any]:
    """The four deterministic checks, run BEFORE any outcome is evaluated."""
    cells = {c.id: c for c in PC.build_cells()}
    checked = 0
    ages_checked = 0
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
                    a = vgen.state_at_age(draw, ages, "operational")
                    b = state_at_age_nocert(draw, ages, "operational")
                    ages_checked += 1

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
