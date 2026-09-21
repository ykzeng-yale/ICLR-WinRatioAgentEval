"""panel.py -- the comparison panel: primary constructions PLUS the declared
external reference, on the same scores, the same prefix, the same allocation.

THE DEPENDENCY RUNS ONE WAY.  This module imports the primary (``vrun``,
``vgen``, ``vband``).  The primary imports nothing from here.  That is how the
reference is "wired into the comparison panel" without the primary ever
depending on it: the panel is assembled on the reference's side of the line,
so deleting this whole directory leaves the primary bit-identical.

WHAT IS HELD IDENTICAL between the primary and the reference, so that any
difference is a difference of construction and not of setup:

  * THE SAME LATENT SCORES.  ``draw.z``, the bounded ternary scores in
    enrollment order, from the same seed coordinates. No re-draw.
  * THE SAME PREFIX.  The reference is evaluated on the full latent prefix
    ``n``, which is what ``confseq_eb`` targets: the running mean of ``z[:n]``.
  * THE SAME ERROR ALLOCATION.  ``vband.ALPHA_GATE`` = .00625, the existing
    two-sided per-gate allocation. Not re-derived, not re-split.
  * THE SAME LEGAL LOOKS.  The reference's band is read at the primary's own
    look prefixes under the schedule in force.

WHAT THE REFERENCE IS NOT GIVEN, and this is a target statement rather than a
handicap: the reference sees COMPLETE scores. Under informative delay the
primary's ADAPTER does not, and the completed-prefix baseline targets its own
``mu_bar_k`` rather than the enrolled-prefix mean. The literature document is
explicit that a difference in TARGET must not be scored as a coverage failure.
So the panel labels the reference ``simulator_only=True``: it is a
full-information reference, not a deployable asynchronous oracle, and the
comparison is of width at a common prefix, not of decisions.

THE REFERENCE CANNOT OVERRIDE ANY DECISION.  Structurally, not by convention:
``panel_rows`` copies the primary's decision fields through unchanged and
computes the reference's columns into a separate namespace prefixed
``ref_``. It never writes a decision, a tau, a gate or a flag, and
``assert_panel_cannot_decide`` re-checks that on every call.

Usage:
    .venv/bin/python experiments/live_ab_validation/reference/panel.py --demo
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

HERE = Path(__file__).resolve().parent
PRIMARY = HERE.parent
for _p in (str(HERE), str(PRIMARY)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eb_crosscheck                                        # noqa: E402
import eb_reference                                         # noqa: E402
import vband                                                # noqa: E402  primary
import vgen                                                 # noqa: E402  primary
import vrun                                                 # noqa: E402  primary

#: The reference's role, carried on every row so that a row read out of context
#: still says what it is.
ROLE = "declared_reference_never_overrides"

#: Numeric columns the reference is allowed to contribute.  Anything not on
#: this list or in ``REFERENCE_METADATA`` is refused.
REFERENCE_COLUMNS = ("ref_lcb", "ref_ucb", "ref_width", "ref_covers_truth")

#: Descriptive labels the reference carries so a row read out of context still
#: says what it is.  These are strings and booleans about ROLE, never about an
#: outcome, and are held separate from ``REFERENCE_COLUMNS`` so that widening
#: one list can never quietly widen the other.
REFERENCE_METADATA = ("ref_role", "ref_simulator_only", "ref_target")

#: Decision quantities the reference must never write.
FORBIDDEN_COLUMNS = ("decision", "tau", "tau_tick", "decided_at_finalization",
                     "decided_in_drain", "ever_miscover_h", "ever_miscover_s",
                     "flag", "gate", "deploy", "retain")


def assert_panel_cannot_decide(rows: List[Dict[str, object]]) -> None:
    """Refuse any row in which the reference wrote a decision quantity."""
    for row in rows:
        for col in row:
            if not col.startswith("ref_"):
                continue
            if col not in REFERENCE_COLUMNS + REFERENCE_METADATA:
                raise AssertionError(
                    f"the reference contributed an undeclared column {col!r}; "
                    f"only {REFERENCE_COLUMNS + REFERENCE_METADATA} are permitted")
        for bad in FORBIDDEN_COLUMNS:
            if f"ref_{bad}" in row:                          # pragma: no cover
                raise AssertionError(
                    f"the reference wrote a decision quantity ref_{bad}")
    eb_reference.assert_reference_cannot_decide()


def panel_rows(draw: "vgen.TrialDraw", cfg: "vrun.RunConfig",
               schedule: Optional[str] = None,
               alpha: float = vband.ALPHA_GATE) -> List[Dict[str, object]]:
    """One row per (construction, look prefix) for the primary, plus the
    reference's band at the same prefixes as separate ``ref_`` columns.

    Raises ``eb_reference.ReferenceUnavailable`` if the vendored authors' code
    cannot be imported. It does NOT fall back to the cross-check or to any
    other construction: the coordinator's instruction is to report import or
    resource failure rather than silently substituting.
    """
    sched = vrun.check_schedule(cfg.schedule if schedule is None else schedule)
    series, _, _, _ = vrun.build_series_for(draw, cfg, sched)

    z = np.asarray(draw.z, dtype=np.float64)
    ref_lo, ref_hi = eb_reference.reference_bands(z, alpha)     # may raise
    running_mean = np.cumsum(z) / np.arange(1, z.size + 1)

    rows: List[Dict[str, object]] = []
    for name in vrun.CONSTRUCTIONS:
        s = series[name]
        for i in range(int(s.index.size)):
            prefix = int(s.prefix[i])
            # the reference is a FULL-LATENT-PREFIX object: read it at the
            # primary's own look prefix, clipped into range
            j = min(max(prefix, 1), int(z.size)) - 1
            rows.append({
                "construction": name,
                "schedule": sched,
                "look_index": int(s.index[i]),
                "prefix": prefix,
                "tick": int(s.tick[i]),
                "primary_l_h": float(s.l_h[i]),
                "primary_u_h": float(s.u_h[i]),
                "primary_width_h": float(s.u_h[i] - s.l_h[i]),
                # ---- the declared reference, in its own namespace ----------
                "ref_role": ROLE,
                "ref_simulator_only": True,
                "ref_target": "running mean of the COMPLETE latent prefix",
                "ref_lcb": float(ref_lo[j]),
                "ref_ucb": float(ref_hi[j]),
                "ref_width": float(ref_hi[j] - ref_lo[j]),
                "ref_covers_truth": bool(
                    ref_lo[j] <= draw.cell.mu_h <= ref_hi[j]),
            })
    assert_panel_cannot_decide(rows)
    return rows


def panel_summary(draw: "vgen.TrialDraw", cfg: "vrun.RunConfig",
                  schedule: Optional[str] = None,
                  alpha: float = vband.ALPHA_GATE) -> Dict[str, object]:
    """Width-at-common-prefix summary, plus the cross-check, for one trial."""
    rows = panel_rows(draw, cfg, schedule, alpha)
    z = np.asarray(draw.z, dtype=np.float64)
    out: Dict[str, object] = {
        "schema": "live_ab_validation_v2.reference.panel.1",
        "cell": draw.cell.id, "n_max": cfg.n_max,
        "schedule": rows[0]["schedule"], "alpha_gate": float(alpha),
        "reference_label": eb_reference.REFERENCE_LABEL,
        "reference_tuning": {"v_opt": eb_reference.V_OPT,
                             "lo": eb_reference.LO, "hi": eb_reference.HI,
                             "boundary_type": eb_reference.BOUNDARY_TYPE},
        "rows": len(rows),
        "constructions": list(vrun.CONSTRUCTIONS),
        "reference_is_a_construction": False,
        "reference_can_override_a_decision": False,
    }
    for name in vrun.CONSTRUCTIONS:
        sel = [r for r in rows if r["construction"] == name]
        final = sel[-1]
        out[f"{name}_final"] = {
            "prefix": final["prefix"], "tick": final["tick"],
            "primary_width_h": final["primary_width_h"],
            "ref_width": final["ref_width"],
            "ref_over_primary": (final["ref_width"] / final["primary_width_h"]
                                 if final["primary_width_h"] else None)}
    out["crosscheck"] = eb_crosscheck.crosscheck_report(z, alpha)
    return out


def reference_resource(inner: int = 20, programs: int = 5,
                       program_base: int = 1000,
                       alpha: float = vband.ALPHA_GATE) -> Dict[str, object]:
    """Time the DECLARED REFERENCE on the authorized balanced coordinates.

    The same 2x2 the delivered-runner measurement uses -- cells C1/C2 crossed
    with horizons 1,000/2,000, five programs per group, namespace 1, program
    indices 1000-1004 -- so the reference's cost is stated on the SAME
    coordinates and is comparable rather than merely adjacent.

    It lives here rather than in ``vresource_check.py`` so that the measurement
    harness keeps no dependency on the reference: the one-way rule holds for
    timing code as well as for the primary.

    Measures only: seconds, peak resident memory, counts. No band value, no
    coverage and no decision leaves this function.
    """
    import resource as _resource
    import time

    def _rss() -> int:
        return _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss * (
            1 if sys.platform != "darwin" else 1)

    if not eb_reference.reference_available():
        return {"schema": "live_ab_validation_v2.reference.resource.1",
                "reference_available": False,
                "reason": "the vendored authors' reference did not import; "
                          "reporting the failure, not substituting"}
    points: List[Dict[str, object]] = []
    baseline = _rss()
    for cell_id in ("C1", "C2"):
        cell = vgen.CELL_BY_ID[cell_id]
        for n_max in (1000, 2000):
            cfg = vrun.make_config(n_max, vgen.NAMESPACE_SMOKE,
                                   schedule=vrun.SCHEDULE_V2)
            draws = [vgen.draw_trial(cell, p, t, n_max=n_max,
                                     namespace=vgen.NAMESPACE_SMOKE)
                     for p in range(program_base, program_base + programs)
                     for t in range(cfg.trials_per_program)]
            eb_reference.reference_bands(np.asarray(draws[0].z,
                                                    dtype=np.float64), alpha)
            each: List[float] = []
            for _ in range(inner):
                t0 = time.perf_counter()
                for d in draws:
                    eb_reference.reference_bands(
                        np.asarray(d.z, dtype=np.float64), alpha)
                each.append(time.perf_counter() - t0)
            med = sorted(each)[len(each) // 2]
            points.append({
                "cell": cell_id, "N_max": n_max, "programs": programs,
                "trials": len(draws), "inner_reps": inner,
                "seconds_median": med,
                "seconds_min": min(each), "seconds_max": max(each),
                "seconds_per_program": med / programs,
                "peak_rss_bytes": _rss()})
    return {
        "schema": "live_ab_validation_v2.reference.resource.1",
        "reference_available": True,
        "reference_label": eb_reference.REFERENCE_LABEL,
        "role": "DECLARED REFERENCE. Its cost is reported beside the primary's "
                "and is NOT part of any budget ladder, tier decision or "
                "admissibility claim: the reference decides nothing, so it "
                "gates nothing.",
        "design": "balanced 2x2, cells C1/C2 x horizons 1,000/2,000, five "
                  "programs per group, namespace 1, program indices 1000-1004",
        "baseline_rss_bytes": baseline,
        "measures_only": ["wall_clock_seconds", "peak_rss", "counts"],
        "points": points,
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true",
                    help="one deterministic trial; no grid, no sweep")
    ap.add_argument("--resource", action="store_true",
                    help="time the reference on the authorized balanced "
                         "coordinates; measures only")
    ap.add_argument("--inner", type=int, default=20)
    ap.add_argument("--cell", default="C1")
    ap.add_argument("--n-max", type=int, default=1000)
    args = ap.parse_args(argv)
    if args.resource:
        print(json.dumps(reference_resource(inner=args.inner), indent=2))
        return 0
    if not args.demo:
        ap.error("only --demo and --resource are available here; "
                 "the grid is not authorized")

    if not eb_reference.reference_available():
        print("REFERENCE UNAVAILABLE -- reporting the failure, not substituting",
              file=sys.stderr)
        return 2
    cell = vgen.CELL_BY_ID[args.cell]
    cfg = vrun.make_config(args.n_max, vgen.NAMESPACE_FIXTURE,
                           schedule=vrun.SCHEDULE_V2)
    draw = vgen.draw_trial(cell, 0, 0, n_max=args.n_max,
                           namespace=vgen.NAMESPACE_FIXTURE)
    print(json.dumps(panel_summary(draw, cfg), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
