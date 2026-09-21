"""THE IMMUTABLE T1 LAUNCHER AND MANIFEST.  Refuses by default; runs only when cleared.

Root, 2026-09-21 09:09, handoff item 1:

    "Deliver the exact immutable T1 launcher and manifest, with eight frozen cell
     allocations (C1/C2/C7/C8: 2000 programs each; C3-C6: 5000 each), horizon 2000,
     four trials, 28,000 programs / 112,000 trials / 224,000 H/D reference calls.
     Preserve the declared namespace-0 replay seed coordinates and all prior
     development exposure labels; this is NOT a fresh holdout.  Bind operational
     policy, tick-batched schedule, preflight-only mode, both references and complete
     coordinates/counts.  Reject malformed/nonfinite/unsupported requests rather than
     silently changing tier.  A dry-run/refusal check may inspect the proposed
     manifest without evaluating trials."

and item 2, on the supervisor:

    "Bind that one launcher to the existing parent supervisor over the WHOLE T1 job,
     with cumulative 5400-second / 2-GiB sampled process-tree / 200-MiB output limits
     ... DO NOT RESET LIMITS PER CELL/SHARD. ... a cap breach is an incomplete study
     and is returned to root, never an automatic retry or a completed subset selected
     by outcome."

WHAT THIS FILE WILL AND WILL NOT DO
-----------------------------------
``build_manifest()`` and ``dry_run()`` evaluate NO trial.  They construct the frozen
request, bind the pins, and report whether it would be refused.  That is the artifact
root asked to review.

``launch()`` refuses unless an explicit clearance token is supplied, because root's
disposition ends: *"Full-grid execution is not cleared by this report."*  Nothing in a
receipt, a cap margin or a successful dry run constitutes clearance, and the refusal
says so by name rather than by a boolean nobody can trace.

THE EXPOSURE LABEL IS NOT COSMETIC
----------------------------------
These are namespace-0 replay coordinates that development has already touched.  The
manifest carries that label so no downstream reader can mistake the result for a fresh
confirmatory holdout.  ``FRESH_HOLDOUT`` is ``False`` and there is no switch to flip it.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vpanel                                                   # noqa: E402
import vpins                                                    # noqa: E402
import vrun                                                     # noqa: E402
import vsupervise                                               # noqa: E402

LAUNCHER_VERSION = "t1-launcher-1"

#: THE FROZEN T1 ALLOCATION, transcribed from the 09:09 handoff.  Not a default,
#: not a parameter with a default: any request that differs is refused.
T1_ALLOCATION: Dict[str, int] = {
    "C1": 2000, "C2": 2000, "C7": 2000, "C8": 2000,
    "C3": 5000, "C4": 5000, "C5": 5000, "C6": 5000,
}
T1_HORIZON = 2000
T1_TRIALS_PER_PROGRAM = 4
T1_NAMESPACE = vgen.NAMESPACE_GRID          # namespace 0, the declared replay seeds
T1_POLICY = "operational"
T1_SCHEDULE = vrun.SCHEDULE_V2
T1_VERIFICATION_MODE = vpanel.VERIFY_PREFLIGHT

T1_EXPECTED_PROGRAMS = 28_000
T1_EXPECTED_TRIALS = 112_000
T1_EXPECTED_REFERENCE_CALLS = 224_000

#: Cumulative over the WHOLE job.  Root: "Do not reset limits per cell/shard."
T1_CAP_SECONDS = 5400.0
T1_CAP_TREE_RSS_BYTES = 2 * 1024 ** 3
T1_CAP_OUTPUT_BYTES = 200 * 1024 ** 2

#: These coordinates have prior development exposure.  There is no switch.
FRESH_HOLDOUT = False
EXPOSURE_LABEL = ("namespace-0 replay coordinates with PRIOR DEVELOPMENT EXPOSURE; "
                  "post-v1 development/paired reuse, NOT a fresh confirmatory holdout")

#: The one token that turns the launcher from a refusal into a run.  It must be
#: supplied explicitly by a human/root decision recorded on the issue.
CLEARANCE_SENTINEL = "ROOT-CLEARED-T1-ATTEMPT"


class LaunchRefused(RuntimeError):
    """The launcher refused.  This is the expected outcome until clearance."""


def _finite_positive_int(name: str, v: Any) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise LaunchRefused(f"{name} must be a number, got {type(v).__name__}")
    if isinstance(v, float):
        if not math.isfinite(v):
            raise LaunchRefused(f"{name} is not finite: {v!r}")
        if v != int(v):
            raise LaunchRefused(f"{name} must be integral, got {v!r}")
    iv = int(v)
    if iv <= 0:
        raise LaunchRefused(f"{name} must be positive, got {iv}")
    return iv


def validate_request(request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Refuse anything that is not exactly the frozen T1 request.

    Root: "Reject malformed/nonfinite/unsupported requests rather than silently
    changing tier."  Every mismatch raises with the field named; nothing is
    coerced, clamped or downgraded to a smaller tier.
    """
    req = dict(request or {})
    alloc = req.get("allocation", T1_ALLOCATION)
    if not isinstance(alloc, dict):
        raise LaunchRefused("allocation must be a mapping of cell id to programs")
    known = {c.id for c in vgen.CELLS}
    unknown = sorted(set(alloc) - known)
    if unknown:
        raise LaunchRefused(f"unknown cells in allocation: {unknown}")
    missing = sorted(known - set(alloc))
    if missing:
        raise LaunchRefused(
            f"allocation omits cells {missing}; T1 is the full eight-cell design "
            f"and a partial grid is a different study, not a smaller T1")
    clean = {k: _finite_positive_int(f"allocation[{k}]", v) for k, v in alloc.items()}
    if clean != T1_ALLOCATION:
        diffs = {k: (clean[k], T1_ALLOCATION[k]) for k in sorted(T1_ALLOCATION)
                 if clean[k] != T1_ALLOCATION[k]}
        raise LaunchRefused(
            f"allocation differs from the frozen T1 allocation at {diffs} "
            f"(got, expected). Refused rather than silently running a "
            f"different tier.")

    horizon = _finite_positive_int("horizon", req.get("horizon", T1_HORIZON))
    if horizon != T1_HORIZON:
        raise LaunchRefused(f"horizon {horizon} != frozen {T1_HORIZON}")
    trials = _finite_positive_int("trials_per_program",
                                  req.get("trials_per_program", T1_TRIALS_PER_PROGRAM))
    if trials != T1_TRIALS_PER_PROGRAM:
        raise LaunchRefused(f"trials_per_program {trials} != frozen {T1_TRIALS_PER_PROGRAM}")
    ns = req.get("namespace", T1_NAMESPACE)
    if ns != T1_NAMESPACE:
        raise LaunchRefused(
            f"namespace {ns!r} != the declared replay namespace {T1_NAMESPACE}")
    for field, want in (("policy", T1_POLICY), ("schedule", T1_SCHEDULE),
                        ("verification_mode", T1_VERIFICATION_MODE)):
        got = req.get(field, want)
        if got != want:
            raise LaunchRefused(f"{field} {got!r} != frozen {want!r}")
    alpha = req.get("alpha_gate", vband.ALPHA_GATE)
    if float(alpha) != float(vband.ALPHA_GATE):
        raise LaunchRefused(
            f"alpha_gate {alpha!r} != frozen {vband.ALPHA_GATE!r}")
    if not req.get("with_reference", True):
        raise LaunchRefused("both H and D reference paths are part of the frozen "
                            "workload; a run without them is a different study")

    programs = sum(clean.values())
    n_trials = programs * trials
    n_refs = n_trials * vpanel.REFERENCE_CALLS_PER_TRIAL
    if (programs, n_trials, n_refs) != (T1_EXPECTED_PROGRAMS, T1_EXPECTED_TRIALS,
                                        T1_EXPECTED_REFERENCE_CALLS):
        raise LaunchRefused(
            f"derived counts {(programs, n_trials, n_refs)} != declared "
            f"{(T1_EXPECTED_PROGRAMS, T1_EXPECTED_TRIALS, T1_EXPECTED_REFERENCE_CALLS)}")
    return {"allocation": clean, "horizon": horizon,
            "trials_per_program": trials, "namespace": ns,
            "policy": T1_POLICY, "schedule": T1_SCHEDULE,
            "verification_mode": T1_VERIFICATION_MODE,
            "alpha_gate": float(alpha), "with_reference": True,
            "programs": programs, "trials": n_trials,
            "reference_calls": n_refs}


def build_manifest(request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The immutable T1 manifest.  Evaluates NO trial."""
    spec = validate_request(request)
    cells = tuple(sorted(spec["allocation"]))
    pins = vpins.entry_point_pins(
        policy=spec["policy"], schedule=spec["schedule"],
        prefixes=vrun.make_config(spec["horizon"], spec["namespace"],
                                  schedule=spec["schedule"]).horizons,
        programs=[], cells=list(cells), namespace=spec["namespace"],
        alpha_gate=spec["alpha_gate"],
        trials_per_program=spec["trials_per_program"],
        workload=f"{vpanel.REFERENCE_CALLS_PER_TRIAL}_calls_per_trial",
        verification_mode=spec["verification_mode"],
        reference_mode=vpanel.REFERENCE_MODE,
        normalized_horizon=spec["horizon"],
        expected_trials=spec["trials"],
        expected_reference_calls=spec["reference_calls"])
    return {
        "schema": "live_ab_validation_v2.t1_manifest.1",
        "launcher_version": LAUNCHER_VERSION,
        "authority": ("root disposition 2026-09-21 09:09, handoff item 1. "
                      "DELIVERED FOR REVIEW; execution is NOT cleared by it."),
        "frozen_request": spec,
        "per_cell_programs": dict(sorted(spec["allocation"].items())),
        "seed_coordinates": {
            "namespace": spec["namespace"],
            "rule": "vgen.stream(namespace, cell.index, program_index, trial_index)",
            "program_index_range_per_cell": "0 .. programs-1, contiguous",
            "cell_indices": {c.id: c.index for c in vgen.CELLS
                             if c.id in spec["allocation"]},
        },
        "exposure": {"fresh_holdout": FRESH_HOLDOUT, "label": EXPOSURE_LABEL},
        "caps_cumulative_over_whole_job": {
            "seconds": T1_CAP_SECONDS,
            "tree_rss_bytes": T1_CAP_TREE_RSS_BYTES,
            "output_bytes": T1_CAP_OUTPUT_BYTES,
            "not_reset_per_cell_or_shard": True,
        },
        "planning_ledger": {
            "source": ("accepted preflight-only resource ledger, root 09:09: "
                       "0.9558524173 s per ten programs at horizon 2000"),
            "t1_projected_seconds": 2676.3868,
            "convention": ("descriptive measurement + deterministic same-horizon "
                           "extrapolation, conditional on a C1/C2 mixture and the "
                           "recorded host load"),
            "not_a_guarantee": ("does NOT guarantee all eight cells finish within "
                                "5400 s; C3-C6 are unmeasured at this scale"),
        },
        "pins": pins,
        "clearance": {
            "required": True,
            "sentinel": CLEARANCE_SENTINEL,
            "status": "NOT CLEARED",
            "note": ("no receipt, cap margin or successful dry run constitutes "
                     "clearance; only an explicit root decision does"),
        },
        "on_cap_breach": ("INCOMPLETE STUDY, returned to root. Never an automatic "
                          "retry, never a completed subset selected by outcome."),
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def dry_run(request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Inspect the proposed manifest and report refusals. Evaluates NO trial."""
    result: Dict[str, Any] = {"evaluated_trials": 0,
                              "note": "manifest inspection only; no trial evaluated"}
    try:
        result["manifest"] = build_manifest(request)
        result["would_validate"] = True
        result["refusal"] = None
    except LaunchRefused as exc:
        result["would_validate"] = False
        result["refusal"] = str(exc)
    result["would_execute"] = False
    result["why_not"] = ("execution requires the explicit clearance sentinel; "
                         "a valid manifest is not clearance")
    return result


def launch(out_dir: Path, request: Optional[Dict[str, Any]] = None,
           clearance: Optional[str] = None) -> Dict[str, Any]:
    """Refuse, or run the whole T1 job under ONE supervisor window."""
    manifest = build_manifest(request)
    if clearance != CLEARANCE_SENTINEL:
        raise LaunchRefused(
            "T1 execution is NOT CLEARED. Root's 09:09 disposition states "
            "'Full-grid execution is not cleared by this report.' Supply the "
            "explicit clearance sentinel only after root records that decision. "
            "A passing dry run, an accepted resource ledger and headroom under "
            "the caps are all necessary and none of them is sufficient.")

    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise LaunchRefused(f"{out_dir} is non-empty; use a fresh directory")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "T1_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    caps = vsupervise.Caps(seconds=T1_CAP_SECONDS,
                           tree_rss_bytes=T1_CAP_TREE_RSS_BYTES,
                           output_bytes=T1_CAP_OUTPUT_BYTES)
    sup = vsupervise.supervise(
        [sys.executable, str(HERE / "vlaunch.py"), "--child",
         "--out", str(out_dir)],
        out_dir, caps, label="t1_full_grid",
        require_available_ram_bytes=T1_CAP_TREE_RSS_BYTES)
    return {"manifest": manifest, "supervision": sup,
            "complete": bool(sup["within_caps"]),
            "on_breach": manifest["on_cap_breach"]}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", action="store_true",
                    help="print the immutable T1 manifest and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="inspect the manifest and report refusals; runs nothing")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--clearance", default=None)
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    if a.manifest:
        print(json.dumps(build_manifest(), indent=2, sort_keys=True))
        return 0
    if a.dry_run:
        print(json.dumps(dry_run(), indent=2, sort_keys=True))
        return 0
    if a.child:                                                # pragma: no cover
        raise SystemExit("the T1 child path is not implemented while execution "
                         "is uncleared; the launcher must not be able to run a "
                         "grid it has no clearance for")
    if a.out is None:
        ap.error("--out is required to launch")
    try:
        r = launch(a.out, clearance=a.clearance)
    except LaunchRefused as exc:
        print(json.dumps({"refused": True, "reason": str(exc)}, indent=2))
        return 3
    print(json.dumps({"complete": r["complete"]}, indent=2))
    return 0 if r["complete"] else 1


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
