#!/usr/bin/env python3
"""combined_workload.py -- the AUTHORIZED bounded timing of the missing scope.

WHAT THE ROOT AUTHORIZED, AND ONLY THIS
---------------------------------------
"Narrow resource measurement is authorized: after the intended executable
workload is bound, reuse the existing balanced 20-unit development design
(namespace 1, program indices 1000-1004 per cell crossed with horizons
1000/2000; ten distinct seed-program identities, not 20 independent programs)
to measure only the missing combined workload, recording exact
code/config/binary/environment pins, all attempts, raw times, call counts,
output bytes and correct platform RSS units.  No blanket sweep or full
calibration/live trial is authorized."

The executable workload was bound first: ``vrun.REFERENCE_WORKLOAD`` freezes one
complete-path call per score per trial for BOTH H and D, four trials per
program, so EIGHT reference calls per program, each path computed once and its
bands indexed.  This file measures THAT workload and nothing else.

WHY IT LIVES HERE AND NOT IN THE PRIMARY HARNESS
------------------------------------------------
The one-way dependency rule is reference -> primary, never the reverse, and it
is mechanically enforced: a test asserts that ``vresource_check.py`` does not
contain the reference's name at all.  So the combined measurement, which needs
both sides, lives on the reference side.  The primary keeps no dependency on
the reference, in timing code as in everything else.

WHAT IS TIMED
-------------
Two scopes, measured CONTEMPORANEOUSLY in the same process, on the same draws,
in the same repetition loop, so the difference between them is a paired
measurement on one host and not a subtraction of two receipts taken months and
machines apart:

  PRIMARY_ONLY  generation (``vgen.draw_trial``) + the delivered primary
                (``vrun.evaluate_trial``) + row serialization
                (``vrun.trial_rows`` into a ``RowSink``).
  COMBINED      the same, plus the frozen reference workload: one complete-path
                call on the hierarchy score H and one on the success-difference
                score D, per trial, on the SHARED latent arrays.

The MISSING SCOPE the root asked for is ``COMBINED - PRIMARY_ONLY``, reported
as a paired difference with both raw vectors retained.

WHAT THIS IS NOT
----------------
  * NOT a resource clearance and NOT a calibration.  It measures cost.
  * NOT a claim that the old 91.2% share carries over.  That number was
    conditional arithmetic on a weak ONE-SCORE receipt and is not reused here,
    reproduced here, or repaired here.
  * NOT a lower-bound claim.  The earlier primary timing already included
    generation and row serialization; the scope differences that remain are
    named in the output as differences, not as a proved inequality.
  * NOT 20 independent programs.  The 20 design units rest on TEN distinct
    (namespace, cell, program) seed identities, because the RNG key excludes
    the horizon.  The output says so.

CPU only.  No model call, no network.  Writes one JSON under
``results/live_ab_validation_v2/`` and nothing else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource as _resource
import statistics
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parent
REPO_ROOT = VALIDATION.parents[1]
for _p in (str(VALIDATION), str(HERE), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import vband                                                     # noqa: E402
import vgen                                                      # noqa: E402
import vrun                                                      # noqa: E402
import eb_reference                                              # noqa: E402

#: the authorized design, unchanged from the existing development design
CELLS = ("C1", "C2")
HORIZONS = (1000, 2000)
PROGRAMS_PER_GROUP = 5
PROGRAM_BASE = 1000
NAMESPACE = vgen.NAMESPACE_SMOKE
SCHEDULE = vrun.SCHEDULE_V2

OUT = (REPO_ROOT / "results" / "live_ab_validation_v2"
       / "resource_check_delivered" / "combined_workload_timing.json")


# ---------------------------------------------------------------------------
# platform-correct resident memory
# ---------------------------------------------------------------------------
def rss_bytes() -> int:
    """``ru_maxrss`` in BYTES on every platform this may run on.

    macOS reports bytes; Linux reports kibibytes.  The existing
    ``panel.py:200-202`` multiplies by 1 on both, which is correct on macOS and
    wrong by 1024 on Linux.  That defect is not inherited here, and the unit
    convention is recorded in the output rather than assumed by the reader.
    """
    raw = int(_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss)
    return raw if sys.platform == "darwin" else raw * 1024


RSS_CONVENTION = ("ru_maxrss is BYTES on darwin and KIBIBYTES on linux; this "
                  "harness converts to bytes and records which branch ran")


def _sha256(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def pins() -> Dict[str, Any]:
    """Exact code, config, BINARY and environment pins."""
    built = sorted((HERE / "_build").glob("*.so")) if (HERE / "_build").is_dir() \
        else []
    manifest = HERE / "MANIFEST.json"
    return {
        "code_sha256": {
            name: _sha256(VALIDATION / name)
            for name in ("vrun.py", "vgen.py", "vband.py", "vresource_check.py")},
        "harness_sha256": _sha256(HERE / "combined_workload.py"),
        "reference_module_sha256": _sha256(HERE / "eb_reference.py"),
        "reference_manifest_sha256": _sha256(manifest),
        "config_sha256": {
            "cells.json": _sha256(VALIDATION / "cells.json"),
            "PROTOCOL_V2.md": _sha256(VALIDATION / "PROTOCOL_V2.md")},
        "compiled_binary": [
            {"path": str(p.relative_to(REPO_ROOT)), "sha256": _sha256(p),
             "bytes": p.stat().st_size} for p in built],
        "reference_module_origins": {
            name: getattr(mod, "__file__", None)
            for name, mod in sorted(sys.modules.items())
            if name.split(".")[0] in ("comparecast", "confseq", "eb_reference")},
        "environment": {
            "python": platform.python_version(),
            "python_build": " ".join(platform.python_build()),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "sys_platform": sys.platform,
            "rss_unit_convention": RSS_CONVENTION,
            "rss_branch": ("darwin: bytes" if sys.platform == "darwin"
                           else "linux: kibibytes x 1024"),
        },
        "schedule": SCHEDULE,
        "namespace": NAMESPACE,
        "frozen_reference_workload": dict(vrun.REFERENCE_WORKLOAD),
    }


# ---------------------------------------------------------------------------
# the two timed scopes
# ---------------------------------------------------------------------------
class Counts:
    """Every call the timed region makes, counted rather than assumed."""

    __slots__ = ("generation_calls", "primary_trial_calls", "serialization_calls",
                 "reference_calls_h", "reference_calls_d", "looks",
                 "band_evaluations", "enclosure_updates", "programs", "trials")

    def __init__(self) -> None:
        for s in self.__slots__:
            setattr(self, s, 0)

    def as_dict(self) -> Dict[str, int]:
        out = {s: int(getattr(self, s)) for s in self.__slots__}
        out["reference_calls_total"] = (out["reference_calls_h"]
                                        + out["reference_calls_d"])
        out["reference_calls_per_program"] = (
            out["reference_calls_total"] // max(out["programs"], 1))
        return out


def _one_rep(cell, cfg, header, program_base: int, programs: int,
             alpha: float, with_reference: bool) -> Tuple[float, Counts, int]:
    """One timed repetition of one scope.  Returns (seconds, counts, bytes)."""
    c = Counts()
    sink = vrun.RowSink(None, header, discard=True)
    t0 = time.perf_counter()
    for program in range(program_base, program_base + programs):
        for trial in range(cfg.trials_per_program):
            draw = vgen.draw_trial(cell, program, trial, n_max=cfg.n_max,
                                   namespace=NAMESPACE)
            c.generation_calls += 1
            records, looks, updates = vrun.evaluate_trial(draw, cfg, SCHEDULE)
            c.primary_trial_calls += 1
            c.looks += looks * len(vrun.CONSTRUCTIONS)
            c.band_evaluations += looks * len(vrun.CONSTRUCTIONS) * 2
            c.enclosure_updates += updates
            if with_reference:
                # THE FROZEN WORKLOAD: one COMPLETE-PATH call per score per
                # trial, on the SHARED latent arrays.  Each path is computed
                # ONCE here; indexing its bands at a look is array indexing and
                # is not another call.
                eb_reference.reference_bands(
                    np.asarray(draw.z, dtype=np.float64), alpha)
                c.reference_calls_h += 1
                eb_reference.reference_bands(
                    np.asarray(draw.dsc, dtype=np.float64), alpha)
                c.reference_calls_d += 1
            sink.write(vrun.trial_rows(cell, program, trial, records, SCHEDULE))
            c.serialization_calls += 1
            c.trials += 1
        c.programs += 1
    seconds = time.perf_counter() - t0
    record_bytes = sink.close()
    return seconds, c, int(record_bytes)


def measure_group(cell_id: str, n_max: int, inner: int, alpha: float,
                  programs: int = PROGRAMS_PER_GROUP,
                  program_base: int = PROGRAM_BASE) -> Dict[str, Any]:
    """Both scopes on one (cell, horizon) group, paired, ``inner`` times each."""
    cell = vgen.CELL_BY_ID[cell_id]
    cfg = vrun.make_config(n_max, NAMESPACE, schedule=SCHEDULE)
    header = vrun.trial_header(SCHEDULE)

    # warm BOTH paths outside every timed region, so no repetition measures
    # import-time or first-call lazy work
    warm = vgen.draw_trial(cell, program_base, 0, n_max=n_max, namespace=NAMESPACE)
    vrun.evaluate_trial(warm, cfg, SCHEDULE)
    eb_reference.reference_bands(np.asarray(warm.z, dtype=np.float64), alpha)
    eb_reference.reference_bands(np.asarray(warm.dsc, dtype=np.float64), alpha)
    baseline = rss_bytes()

    scopes: Dict[str, Any] = {}
    counts: Dict[str, Any] = {}
    out_bytes: Dict[str, int] = {}
    for scope, with_ref in (("primary_only", False), ("combined", True)):
        each: List[float] = []
        c = Counts()
        nbytes = 0
        for _ in range(inner):
            secs, c, nbytes = _one_rep(cell, cfg, header, program_base,
                                       programs, alpha, with_ref)
            each.append(secs)
        scopes[scope] = {
            "seconds_each": each,
            "seconds_median": statistics.median(each),
            "seconds_min": min(each), "seconds_max": max(each),
            "seconds_mean": statistics.fmean(each),
            "seconds_stdev": (statistics.stdev(each) if len(each) > 1 else 0.0),
            "seconds_per_program": statistics.median(each) / programs,
        }
        counts[scope] = c.as_dict()
        out_bytes[scope] = nbytes

    med_p = scopes["primary_only"]["seconds_median"]
    med_c = scopes["combined"]["seconds_median"]
    return {
        "cell": cell_id, "N_max": n_max, "programs": programs,
        "program_base": program_base,
        "trials": counts["combined"]["trials"],
        "inner_reps": inner,
        "scopes": scopes,
        "call_counts": counts,
        "record_bytes_measured_not_written": out_bytes,
        "bytes_per_program": {k: v / programs for k, v in out_bytes.items()},
        "missing_scope_seconds_median": med_c - med_p,
        "missing_scope_seconds_per_program": (med_c - med_p) / programs,
        "missing_scope_share_of_combined": ((med_c - med_p) / med_c
                                            if med_c else None),
        "seconds_per_program": med_c / programs,
        "baseline_rss_bytes": baseline,
        "peak_rss_bytes": rss_bytes(),
        "rss_delta_bytes": rss_bytes() - baseline,
    }


# ---------------------------------------------------------------------------
# the design
# ---------------------------------------------------------------------------
def run(inner: int = 20, reps: int = 1, alpha: float = vband.ALPHA_GATE
        ) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    points: List[Dict[str, Any]] = []
    groups = [(c, h) for c in CELLS for h in HORIZONS]

    if not eb_reference.reference_available():
        attempts.append({
            "attempt": 1, "status": "FAILED",
            "what": "import the vendored authors' reference",
            "reason": ("the reference did not import on this host; reporting "
                       "the failure rather than substituting another "
                       "construction")})
        return {"schema": "live_ab_validation_v2.combined_workload.1",
                "reference_available": False, "attempts": attempts,
                "points": [], "pins": pins()}
    attempts.append({"attempt": 1, "status": "OK",
                     "what": "import the vendored authors' reference"})

    n = 1
    for rep in range(reps):
        # rotate the group order every repetition so a systematic drift cannot
        # land on one group
        order = groups[rep % len(groups):] + groups[:rep % len(groups)]
        for cell_id, n_max in order:
            n += 1
            rec = {"attempt": n, "status": "", "what":
                   f"measure_group(cell={cell_id}, N_max={n_max}, inner={inner})",
                   "rep": rep}
            try:
                point = measure_group(cell_id, n_max, inner, alpha)
            except Exception as exc:                             # noqa: BLE001
                rec["status"] = "FAILED"
                rec["exception_type"] = type(exc).__name__
                rec["exception"] = str(exc)[:400]
                rec["traceback_tail"] = traceback.format_exc()[-600:]
                attempts.append(rec)
                continue
            rec["status"] = "OK"
            rec["seconds_median_combined"] = \
                point["scopes"]["combined"]["seconds_median"]
            attempts.append(rec)
            point["rep"] = rep
            points.append(point)

    failed = [a for a in attempts if a["status"] == "FAILED"]
    by_horizon: Dict[str, Dict[str, Any]] = {}
    for p in points:
        slot = by_horizon.setdefault(str(p["N_max"]), {"cells": {}})
        slot["cells"].setdefault(p["cell"], []).append(p["seconds_per_program"])
    for slot in by_horizon.values():
        per_cell = {c: statistics.median(v) for c, v in slot["cells"].items()}
        worst = max(per_cell, key=lambda c: per_cell[c])
        slot["seconds_per_program_by_cell"] = per_cell
        slot["selected_cell"] = worst
        slot["seconds_per_program"] = per_cell[worst]

    return {
        "schema": "live_ab_validation_v2.combined_workload.1",
        "what_this_is": (
            "the bounded measurement of the MISSING COMBINED WORKLOAD SCOPE, "
            "on the authorized balanced 20-unit development design, after the "
            "reference workload was bound in executable form"),
        "what_this_is_not": [
            "not a resource clearance, not a calibration, not a live trial",
            "not a blanket retiming sweep: only the 20 authorized design units",
            "not a reuse of the withdrawn 91.2% share, which was conditional "
            "arithmetic on a weak one-score receipt",
            "not a lower-bound claim: the earlier primary timing already "
            "included generation and row serialization",
        ],
        "timed_scope": {
            "primary_only": ("vgen.draw_trial + vrun.evaluate_trial + "
                             "vrun.trial_rows into a discard RowSink"),
            "combined": ("the same, plus the frozen reference workload: one "
                         "complete-path call on H and one on D per trial, on "
                         "the shared latent arrays"),
            "missing_scope": "combined minus primary_only, measured paired",
            "remaining_scope_differences_named_not_bounded": [
                "the grid's block accumulator, output path and per-batch "
                "summary work are not in either scope",
                "a disk-backed sink differs from this discard sink",
                "process context and warm-up differ from a full grid run",
            ],
        },
        "design": ("balanced 2x2, cells C1/C2 x horizons 1,000/2,000, five "
                   "programs per group, namespace 1, program indices "
                   "1000-1004"),
        "seed_identity_note": (
            "the 20 design units rest on TEN distinct (namespace, cell, "
            "program) seed identities: all groups use program indices "
            "1000-1004 and the RNG key excludes the horizon. Repetitions are "
            "not independent experimental outcomes."),
        "reference_available": True,
        "reference_label": eb_reference.REFERENCE_LABEL,
        "alpha_passed_unhalved": alpha,
        "inner_reps": inner, "outer_reps": reps,
        "attempts": attempts,
        "attempts_total": len(attempts),
        "attempts_failed": len(failed),
        "points": points,
        "by_horizon": by_horizon,
        "measures_only": ["wall_clock_seconds", "peak_rss", "output_bytes",
                          "call_counts"],
        "pins": pins(),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inner", type=int, default=20)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--write", action="store_true",
                    help="deposit the receipt (default: print only)")
    args = ap.parse_args(argv)
    report = run(inner=args.inner, reps=args.reps)
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str))
    for p in report["points"]:
        print(f"{p['cell']} N={p['N_max']:5d} rep{p['rep']}  "
              f"primary {p['scopes']['primary_only']['seconds_median']:.6f}s  "
              f"combined {p['scopes']['combined']['seconds_median']:.6f}s  "
              f"missing {p['missing_scope_seconds_median']:.6f}s  "
              f"({p['missing_scope_share_of_combined'] * 100:.1f}% of combined)  "
              f"ref calls/program "
              f"{p['call_counts']['combined']['reference_calls_per_program']}")
    print(f"\nattempts {report['attempts_total']}, "
          f"failed {report['attempts_failed']}")
    if args.write:
        print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
