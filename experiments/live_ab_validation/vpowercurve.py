"""POWER-CURVE PANEL: intermediate hierarchy effects, guardrail held open.

WHY
---
The T1 calibration panel answered what it could and exposed what it could not.  Its
grid has mu_h in {0, 0.40, 0.45}: nothing between 0 and 0.40.  So every ADAPTER
decision rate came out 0.0000 or 1.0000 (sole exception 0.00025 at C4), and the panel
cannot identify a power curve or a minimum detectable effect at a prespecified target
power.  That gap is in the grid I specified.  This panel fills it.

Root's review also narrowed a claim I had overstated, and the narrowing is why this
experiment is worth running rather than merely arguing about:

    "'No partially-powered operating point' does not follow from the grid's effect
     spacing.  Detection probability also depends on joint outcome law, variance, delay,
     guardrail effect, horizon and conservative boundary width."

Exactly so.  Where the transition actually sits is an empirical question, and the only
way to answer it is to put cells there.

THE LADDER
----------
Five hierarchy effects with the SUCCESS GUARDRAIL HELD OPEN at mu_s = +0.20, so that
detection probability is not confounded by the guardrail arm:

    mu_h = 0.05, 0.10, 0.15, 0.20, 0.30      mu_s = +0.20 throughout

Each crossed with both delay arms (N non-informative, A informative), giving 10 cells.
Weight vectors are exact integers over the frozen six atoms, from the frozen identities
mu_h = (BB+ + C>I - BB- - I>C)/10000 and mu_s = (C>I - I>C)/10000, holding
C>I = 2500, I>C = 500, BB0 = 1000, FF = 2000 and splitting the remaining 4000 between
BB+ and BB-.  Holding the other four atoms fixed means the ladder varies ONE thing.

THE FROZEN SOURCE IS NOT EDITED
-------------------------------
``vgen.py``'s bytes are unchanged, so the accepted v2 identity and the T1 evidence stay
valid.  The new laws are registered into vgen's runtime tables ADDITIVELY -- L1..L4 and
CELLS are untouched -- and the panel runs in its OWN namespace, so no seed coordinate
collides with the T1 replay set.

WHAT THIS PANEL WILL AND WILL NOT SHOW
--------------------------------------
It can estimate cell-specific correct-deployment and abstention probabilities with
Monte Carlo uncertainty, and hence locate where detection turns on.  It does NOT
establish coverage or validity: the null cells of the T1 panel do that.  It is a
DIFFERENT namespace and a DIFFERENT law family, so its numbers must never be pooled
with T1's.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402

#: Its own namespace: 0 grid (T1 replay), 1 smoke, 2 fixture, 3 power curve.
NAMESPACE_POWER = 3

#: mu_h ladder.  mu_s is held OPEN so the guardrail cannot confound detection.
MU_H_LADDER: Tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.30)
MU_S_HELD: float = 0.20

#: Atoms held fixed across the ladder, so it varies exactly one thing.
_HELD = {"BB0": 1000, "C>I": 2500, "I>C": 500, "FF": 2000}
_SPLIT = 4000            # shared between BB+ and BB-


def law_weights_for(mu_h: float) -> Dict[str, int]:
    """Exact integer weights realising ``mu_h`` at ``mu_s = MU_S_HELD``."""
    d = int(round(vgen.WEIGHT_DENOMINATOR * mu_h)) - (_HELD["C>I"] - _HELD["I>C"])
    if (_SPLIT + d) % 2:
        raise ValueError(f"mu_h={mu_h} does not land on an integer split")
    w = {"BB+": (_SPLIT + d) // 2, "BB-": (_SPLIT - d) // 2, **_HELD}
    if any(v < 0 for v in w.values()):
        raise ValueError(f"mu_h={mu_h} needs a negative weight: {w}")
    if sum(w.values()) != vgen.WEIGHT_DENOMINATOR:
        raise ValueError(f"weights do not sum to {vgen.WEIGHT_DENOMINATOR}: {w}")
    got_h = (w["BB+"] + w["C>I"] - w["BB-"] - w["I>C"]) / vgen.WEIGHT_DENOMINATOR
    got_s = (w["C>I"] - w["I>C"]) / vgen.WEIGHT_DENOMINATOR
    if abs(got_h - mu_h) > 1e-12 or abs(got_s - MU_S_HELD) > 1e-12:
        raise ValueError(f"weights realise ({got_h}, {got_s}), wanted ({mu_h}, {MU_S_HELD})")
    return w


def law_id(mu_h: float) -> str:
    return f"P{int(round(mu_h * 100)):02d}"


def register_laws() -> Dict[str, Dict[str, int]]:
    """Add the ladder's laws to vgen's runtime tables. ADDITIVE ONLY.

    Refuses to touch an existing law id, so L1..L4 and every accepted T1 number
    remain exactly what they were.  ``vgen.py`` on disk is not modified.
    """
    added = {}
    for mu_h in MU_H_LADDER:
        lid = law_id(mu_h)
        w = law_weights_for(mu_h)
        if lid in vgen.LAW_WEIGHTS and vgen.LAW_WEIGHTS[lid] != w:
            raise ValueError(f"refusing to redefine existing law {lid}")
        vgen.LAW_WEIGHTS[lid] = w
        vec = np.array([w[a] for a in vgen.ATOM_ORDER], dtype=np.int64)
        vgen.LAW_WEIGHT_VEC[lid] = vec
        vgen.LAW_CUMWEIGHTS[lid] = np.cumsum(vec)
        vgen.LAW_W_NEG[lid] = int(w["BB-"] + w["I>C"])
        vgen.LAW_NAMES[lid] = f"power_mu_h_{mu_h:.2f}"
        added[lid] = w
    # the frozen four must be untouched
    for frozen in ("L1", "L2", "L3", "L4"):
        if frozen not in vgen.LAW_WEIGHTS:
            raise ValueError(f"frozen law {frozen} disappeared")
    return added


def build_cells(start_index: int = 100) -> Tuple[Any, ...]:
    """Ten CellSpecs: the ladder crossed with both delay arms.

    ``index`` starts well past the frozen cells so the spawn key of a power-curve
    cell can never collide with a T1 cell even if the namespace were confused.
    """
    register_laws()
    out = []
    idx = start_index
    for mu_h in MU_H_LADDER:
        lid = law_id(mu_h)
        for delay in ("N", "A"):
            out.append(vgen.CellSpec(
                id=f"{lid}{delay}", index=idx, law=lid, delay=delay,
                mu_h=vgen.mu_h_of(lid), mu_s=vgen.mu_s_of(lid),
                escalation_eligible=False))
            idx += 1
    return tuple(out)


def build_plan(cells: Tuple[Any, ...], programs_per_cell: int = 2000,
               programs_per_shard: int = 500, horizon: int = 2000,
               trials: int = 4) -> Dict[str, Any]:
    """A shard plan of the same shape the T1 executor already consumes."""
    import vpanel
    import vrun
    prefixes = list(vrun.make_config(horizon, NAMESPACE_POWER,
                                     schedule=vrun.SCHEDULE_V2).horizons)
    per_primary = programs_per_shard * trials * len(vrun.CONSTRUCTIONS)
    per_ref_rows = (programs_per_shard * trials
                    * vpanel.REFERENCE_CALLS_PER_TRIAL * len(prefixes))
    shards: List[Dict[str, Any]] = []
    seq = 0
    n_blocks = programs_per_cell // programs_per_shard
    for blk in range(n_blocks):
        for c in cells:
            a = blk * programs_per_shard
            seq += 1
            shards.append({
                "sequence": seq, "id": f"{c.id}-p{a:04d}-{a + programs_per_shard - 1:04d}",
                "cell": c.id, "program_start_inclusive": a,
                "program_stop_exclusive": a + programs_per_shard,
                "trial_indices": list(range(trials)),
                "expected_programs": programs_per_shard,
                "expected_trials": programs_per_shard * trials,
                "expected_reference_calls":
                    programs_per_shard * trials * vpanel.REFERENCE_CALLS_PER_TRIAL,
                "expected_primary_rows": per_primary,
                "expected_reference_rows": per_ref_rows})
    n = len(shards)
    return {
        "schema": "live_ab_validation_v2.power_curve_plan.1",
        "namespace": NAMESPACE_POWER, "horizon": horizon,
        "trials_per_program": trials,
        "programs_per_shard": programs_per_shard,
        "allocation": {c.id: programs_per_cell for c in cells},
        "total_programs": programs_per_cell * len(cells),
        "total_trials": programs_per_cell * len(cells) * trials,
        "total_reference_calls":
            programs_per_cell * len(cells) * trials * 2,
        "total_primary_rows": per_primary * n,
        "total_reference_rows": per_ref_rows * n,
        "prefixes": prefixes,
        "mu_h_ladder": list(MU_H_LADDER), "mu_s_held": MU_S_HELD,
        "guardrail_note": ("mu_s is held at +0.20, comfortably above -delta, so "
                           "detection probability is not confounded by the "
                           "success guardrail"),
        "not_poolable_with_T1": ("different namespace and different law family; "
                                 "these numbers must never be pooled with the T1 "
                                 "calibration panel"),
        "job_caps": {"seconds": 5400, "sampled_process_tree_bytes": 2 * 1024 ** 3,
                     "total_output_bytes": 200 * 1024 ** 2, "reset_per_shard": False},
        "shards": shards,
    }
