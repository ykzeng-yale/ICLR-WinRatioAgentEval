#!/usr/bin/env python3
"""eb_width_diagnostic.py -- a LIKE-FOR-LIKE width diagnostic, done correctly.

THIS REPLACES A WITHDRAWN CALCULATION, and the withdrawal is the reason this
file states its object so heavily.  ``BOUNDARY_WIDTH_AT_OUR_OPERATING_POINT.md``
(commit 3c6982c) is WITHDRAWN IN FULL and is preserved with its banner.  It
failed in three ways, each of which is closed here by construction:

  (a) WRONG FAMILY.  It called ``poly_stitching_bound``, a STITCHED boundary,
      with ``c = 0``.  The selected reference is ``boundary_type = "mixture"``
      (``eb_reference.py:66``) with ``c = hi - lo = 2``.
      -> HERE: the selected reference is CALLED, through ``eb_reference.
         reference_bands``, so the family, the scale and the tuning are
         whatever that module fixes and cannot drift from it.
  (b) WRONG ERROR BUDGET.  It passed ``alpha = 0.00625`` into a function that
      applies no split, while ``confseq_eb`` performs the ``alpha/2`` split
      INTERNALLY.
      -> HERE: alpha is passed UNHALVED, exactly as ``eb_reference`` requires,
         and the primary side is evaluated at the SAME total two-sided
         ``alpha_gate``, so the two are at the same level.
  (c) WRONG CLOCK.  It used ``n x pilot variance`` as a proxy for the
      predictable residual clock.
      -> HERE: no proxy is used at all.  The reference is run on ACTUAL,
         fully specified score paths, so it accumulates its own real clock
         ``V_n = max(1, sum (z_i - gamma_i)^2)`` with lagged predictable
         centres.  That clock is REPORTED beside the widths, together with the
         realized variance, precisely so the two can be seen to differ.

WHAT THE TWO SIDES ARE.  Both are two-sided anytime-valid confidence sequences
for the running mean of the SAME bounded scores ``z`` in ``[-1, +1]``,
evaluated at the SAME index ``n`` on the SAME path, at the SAME total two-sided
allocation ``alpha_gate``:

  PRIMARY   ``winstats.normal_mixture_radius(n, alpha_gate, rho)``: a normal
            mixture on the PREDICTABLE worst-case clock ``V_n = n``, tuned at
            ``rho = 100``.  Its clock does not depend on the data.
  REFERENCE ``comparecast.confseq.confseq_eb(..., boundary_type="mixture",
            v_opt=10, lo=-1, hi=+1)``: a gamma-exponential mixture on the
            EMPIRICAL residual clock, tuned at ``v_opt = 10``, scale ``c = 2``.

So the comparison prices ONE difference -- a fixed clock against an adaptive
one, under each construction's own tuning -- and it is a fair one only because
everything else is held equal.

WHAT THIS IS NOT, and none of these is a hedge:

  * NOT a statement about the ADAPTER.  The adapter never sees complete latent
    scores; it sees enclosures, and its band is wider than the complete-data
    band on the same path.  This is a COMPLETE-DATA boundary comparison and it
    says nothing about partial-information handling.
  * NOT power, NOT an expected stopping time, NOT a required sample size, and
    NOT evidence that any two systems are genuinely equal.
  * NOT a claim about all ``n`` or all paths.  Only the declared coordinates
    and the declared ``n`` grid below were evaluated, and the output says so.
  * NOT a success-guard result.  Only the hierarchy score ``z`` is evaluated;
    the success-difference gate has no reference here.

CPU only.  No model call, no network.  Writes one JSON under
``results/live_ab_validation_v2/`` and nothing else.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parent
REPO_ROOT = VALIDATION.parents[1]
OUT = (REPO_ROOT / "results" / "live_ab_validation_v2"
       / "reference_width_diagnostic.json")

#: The declared coordinates.  Fully specified, deterministic, and the SAME
#: eight streams the bound v2 comparison replays, so nothing was selected after
#: seeing a width.
STREAMS = tuple((f"C{i}", 0, 0) for i in range(1, 9))

#: The declared n grid, fixed before any width was computed.
N_GRID = (100, 200, 500, 1000, 1500, 2000)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        d = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                           capture_output=True, text=True, timeout=30)
        return d.stdout.strip() if d.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):          # pragma: no cover
        return "unknown"


def residual_clock(z: np.ndarray) -> np.ndarray:
    """The reference's ACTUAL clock: ``max(1, sum (z_i - gamma_i)^2)``.

    Recomputed here only so it can be REPORTED; the reference computes its own
    internally and this value is never fed to it.
    """
    z = np.asarray(z, dtype=np.float64)
    t = np.arange(1, z.size + 1, dtype=np.float64)
    mus = np.cumsum(z) / t
    gammas = np.empty_like(mus)
    gammas[0] = 0.0
    gammas[1:] = mus[:-1]
    return np.maximum(1.0, np.cumsum((z - gammas) ** 2))


def assert_reference_modules_came_from_the_pinned_tree() -> dict:
    """Refuse to report a width unless the pinned tree is what got loaded.

    The reference audit's provenance-hardening item: ``_load_package`` returns
    a same-named package already in ``sys.modules`` WITHOUT checking its
    origin, so a reused interpreter could serve a different ``comparecast`` or
    ``confseq``.  This process is fresh, but "it is fresh" is an assumption,
    and the point of a reference is that its identity is checked rather than
    assumed.  So the origin is verified after loading and the diagnostic
    REFUSES rather than reporting a width from an unidentified package.
    """
    import eb_reference as ref
    ref.load_reference()
    roots = (ref.UPSTREAM.resolve(), ref.BUILD.resolve())
    seen = {}
    for name in ("confseq", "comparecast", "comparecast.confseq",
                 "confseq.boundaries"):
        mod = sys.modules.get(name)
        if mod is None:
            raise SystemExit(
                f"REFUSING: {name} is not loaded after load_reference(); the "
                f"reference tree is not what is being measured")
        f = getattr(mod, "__file__", None)
        if f is None:                                      # pragma: no cover
            raise SystemExit(f"REFUSING: {name} has no __file__ to verify")
        p = Path(f).resolve()
        if not any(str(p).startswith(str(r) + "/") for r in roots):
            raise SystemExit(
                f"REFUSING: {name} was loaded from {p}, which is outside the "
                f"pinned tree {roots}. A width from an unidentified package "
                f"is not a reference measurement.")
        seen[name] = str(p.relative_to(REPO_ROOT))
    return seen


def run() -> dict:
    sys.path.insert(0, str(VALIDATION))
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    import winstats
    import vcompare
    import eb_reference as ref

    module_origins = assert_reference_modules_came_from_the_pinned_tree()

    vcompare.select_snapshot("v2")
    cfg = vcompare.load_frozen_config()
    alpha = float(cfg.alpha_gate)
    rho = float(cfg.rho)
    gen = vcompare.FrozenGenerator(cfg)

    rows = []
    for cell_id, prog, trial in STREAMS:
        st = gen.build(cell_id, prog, trial)
        z = np.asarray(st.z_true, dtype=np.float64)
        if z.min() < -1.0 or z.max() > 1.0:                # pragma: no cover
            raise SystemExit(f"{cell_id}: scores outside [-1,1]")
        lcb, ucb = ref.reference_bands(z, alpha)           # alpha NOT halved
        ref_w = ucb - lcb
        clock = residual_clock(z)
        t = np.arange(1, z.size + 1, dtype=np.float64)
        mus = np.cumsum(z) / t
        # realized variance about the running mean, reported ONLY to show that
        # it is not the clock.  It is never used as one.
        realized_var = np.cumsum((z - mus) ** 2)
        for n in N_GRID:
            if n > z.size:
                continue
            i = n - 1
            prim_r = float(winstats.normal_mixture_radius(
                n, alpha=alpha, rho=rho))
            prim_w = 2.0 * prim_r
            prim_w_clipped = float(min(mus[i] + prim_r, 1.0)
                                   - max(mus[i] - prim_r, -1.0))
            ref_w_clipped = float(min(ucb[i], 1.0) - max(lcb[i], -1.0))
            rows.append({
                "cell": cell_id, "program": prog, "trial": trial, "n": n,
                "running_mean": float(mus[i]),
                "reference_clock_V_n": float(clock[i]),
                "realized_variance_sum": float(realized_var[i]),
                "clock_minus_realized_variance":
                    float(clock[i] - realized_var[i]),
                "clock_over_n": float(clock[i] / n),
                "primary_width_unclipped": prim_w,
                "reference_width_unclipped": float(ref_w[i]),
                "primary_width_clipped": prim_w_clipped,
                "reference_width_clipped": ref_w_clipped,
                "width_ratio_reference_over_primary_unclipped":
                    float(ref_w[i] / prim_w),
                "reference_narrower_unclipped": bool(ref_w[i] < prim_w),
            })

    by_n = {}
    for n in N_GRID:
        sel = [r for r in rows if r["n"] == n]
        if not sel:
            continue
        ratios = [r["width_ratio_reference_over_primary_unclipped"]
                  for r in sel]
        by_n[str(n)] = {
            "streams": len(sel),
            "primary_width_unclipped": sel[0]["primary_width_unclipped"],
            "reference_width_unclipped_min": min(
                r["reference_width_unclipped"] for r in sel),
            "reference_width_unclipped_max": max(
                r["reference_width_unclipped"] for r in sel),
            "ratio_min": min(ratios), "ratio_max": max(ratios),
            "streams_where_reference_is_narrower": sum(
                1 for r in sel if r["reference_narrower_unclipped"]),
        }

    n_rows = len(rows)
    narrower = sum(1 for r in rows if r["reference_narrower_unclipped"])
    report = {
        "schema": "live_ab_validation_v2.reference.width_diagnostic.1",
        "supersedes": {
            "file": ("experiments/live_ab_validation/"
                     "BOUNDARY_WIDTH_AT_OUR_OPERATING_POINT.md"),
            "status": ("WITHDRAWN IN FULL and PRESERVED with its banner. Its "
                       "numbers -- 8,867 pairs, 'tighter at every n', 'no "
                       "crossover', the 1.93x ratio, the revised certifiable "
                       "margin and the proposed sizing paragraph -- are NOT "
                       "reused, reproduced or repaired here."),
            "why_it_failed": ["wrong family (stitched c=0 vs mixture c=2)",
                              "wrong error budget (alpha pre-halved against a "
                              "wrapper that halves internally)",
                              "wrong clock (n x pilot variance as a proxy)"],
        },
        "object_compared": {
            "both_sides": ("two-sided anytime-valid confidence sequences for "
                           "the running mean of the SAME bounded scores, at "
                           "the SAME n, on the SAME path, at the SAME total "
                           "two-sided alpha"),
            "primary": {
                "callable": "src/winstats.py:normal_mixture_radius",
                "family": "normal mixture",
                "clock": "PREDICTABLE worst-case V_n = n (not data-driven)",
                "tuning": {"rho": rho},
                "alpha_convention": "alpha_gate is the TOTAL two-sided budget",
            },
            "reference": {
                "callable": ("comparecast.confseq.confseq_eb via "
                             "reference/eb_reference.py:reference_bands"),
                "family": ref.BOUNDARY_TYPE,
                "clock": ("EMPIRICAL residual clock max(1, sum (z_i-gamma_i)^2) "
                          "with lagged predictable centres, computed BY THE "
                          "REFERENCE ITSELF on the actual path; no proxy"),
                "tuning": {"v_opt": ref.V_OPT, "lo": ref.LO, "hi": ref.HI,
                           "c": ref.HI - ref.LO},
                "alpha_convention": ("alpha passed UNHALVED; confseq_eb "
                                     "applies alpha/2 internally, giving the "
                                     "same total two-sided budget"),
                "label": ref.REFERENCE_LABEL,
            },
            "alpha_gate_both_sides": alpha,
            "same_level": True,
        },
        "scope": {
            "streams_declared": [f"{c}:ns{cfg.namespace}:p{p}:t{t}"
                                 for c, p, t in STREAMS],
            "n_grid_declared": list(N_GRID),
            "rows": n_rows,
            "declared_before_any_width_was_computed": True,
            "this_is_complete_data_only": (
                "z_true is the complete latent hierarchy score. The ADAPTER "
                "does not observe it; it observes enclosures. Nothing here "
                "measures the adapter, partial-information handling, or the "
                "cost of unresolved pairs."),
            "hierarchy_score_only": (
                "only z is evaluated. There is no success-difference (d) "
                "reference here, so this says nothing about success-guard "
                "power or guarded deployment power."),
            "not_power_not_stopping_time": (
                "a width is not power, not an expected stopping time, not a "
                "required sample size, and not evidence that two systems are "
                "genuinely equal."),
            "no_all_n_claim": (
                f"only the {len(N_GRID)} declared n values on "
                f"{len(STREAMS)} declared paths were evaluated. No ordering "
                f"over all n, all paths or the two families is asserted."),
        },
        "summary": {
            "rows_where_reference_is_narrower_unclipped": narrower,
            "rows_total": n_rows,
            "crossover_present_within_the_evaluated_grid": (
                0 < narrower < n_rows),
        },
        "by_n": by_n,
        "rows": rows,
        "provenance": {
            "repo_commit": _git_commit(),
            "cells_json_sha256": _sha(VALIDATION / "cells.json"),
            "eb_reference_sha256": _sha(HERE / "eb_reference.py"),
            "reference_manifest_sha256": _sha(HERE / "MANIFEST.json"),
            "winstats_sha256": _sha(REPO_ROOT / "src" / "winstats.py"),
            "vcompare_sha256": _sha(VALIDATION / "vcompare.py"),
            "this_file_sha256": _sha(Path(__file__).resolve()),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "reference_module_origins_verified": module_origins,
            "reference_module_origin_rule": (
                "every loaded reference module's __file__ was checked to lie "
                "inside reference/upstream/ or reference/_build/ AFTER import; "
                "the diagnostic refuses to emit a width otherwise"),
            "reference_build_product_sha256": _sha(
                ref.BUILD / f"boundaries{__import__('sysconfig').get_config_var('EXT_SUFFIX')}"),
        },
    }
    return report


def main() -> int:
    rep = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(rep["object_compared"]["reference"]["label"])
    print(f"alpha (both sides, total two-sided) = "
          f"{rep['object_compared']['alpha_gate_both_sides']}")
    print()
    hdr = (f"{'n':>6s}{'primary W':>12s}{'ref W min':>12s}{'ref W max':>12s}"
           f"{'ratio min':>11s}{'ratio max':>11s}{'ref narrower':>14s}")
    print(hdr)
    for n, s in rep["by_n"].items():
        print(f"{n:>6s}{s['primary_width_unclipped']:12.6f}"
              f"{s['reference_width_unclipped_min']:12.6f}"
              f"{s['reference_width_unclipped_max']:12.6f}"
              f"{s['ratio_min']:11.4f}{s['ratio_max']:11.4f}"
              f"{s['streams_where_reference_is_narrower']:>10d}/"
              f"{s['streams']}")
    su = rep["summary"]
    print(f"\nreference narrower in {su['rows_where_reference_is_narrower_unclipped']}"
          f" of {su['rows_total']} evaluated (path, n) points; crossover within "
          f"the evaluated grid: {su['crossover_present_within_the_evaluated_grid']}")
    print(f"\nwrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
