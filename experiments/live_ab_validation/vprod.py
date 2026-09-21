"""THE PRODUCTION SHARD RUNNER: real primary + real H/D reference, one shard.

Root, 2026-09-21 10:58, ranked repair 1:

    "Connect and test the actual complete path.  `vlaunch.main --child` still exits as
     unimplemented; the real primary/reference shard runner remains absent. ...
     Implement one supervised serial child iterating the fixed plan with explicit
     program/trial indices; use the existing scientific routines, close both files,
     validate/publish receipts, and return to the parent for final reconciliation and a
     persisted terminal job receipt."

This is that runner.  It calls the ALREADY ACCEPTED scientific routines --
``vgen.draw_trial``, ``vrun.evaluate_trial``, ``vrun.trial_rows`` and
``eb_reference.reference_bands`` -- with explicit indices from the reviewed plan
entry.  It invents no estimator and changes no science.

SCIENTIFIC ROUTINES ARE INJECTED
--------------------------------
``draw_fn``, ``evaluate_fn``, ``rows_fn`` and ``reference_fn`` default to the real
ones.  Tests inject stubs so the REAL orchestration can be exercised end to end
without running the grid or calling the native reference -- which is exactly what root
asked for: "one positive roundtrip and refusal cases through the real orchestration
with injected stub scientific functions."

MEASUREMENT-ONLY DISCIPLINE
---------------------------
No decision label is accumulated or summarised anywhere here.  Primary rows are written
as the design produces them, because writing them is part of the measured workload, but
nothing in this module reads, counts or branches on an effect.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vpanel                                                   # noqa: E402
import vrun                                                     # noqa: E402
import vshard                                                   # noqa: E402
from reference import eb_reference                              # noqa: E402


class _ShardAborted(Exception):
    """Internal: stop this shard at the first technical failure."""


def _default_reference(values, alpha):
    return eb_reference.reference_bands(np.asarray(values, dtype=np.float64), alpha)


def make_runner(*, horizon: int, namespace: int, policy: str, schedule: str,
                alpha_gate: float, trials_per_program: int,
                verification_mode: str = vpanel.VERIFY_PREFLIGHT,
                draw_fn: Callable = vgen.draw_trial,
                evaluate_fn: Callable = vrun.evaluate_trial,
                rows_fn: Callable = vrun.trial_rows,
                reference_fn: Callable = _default_reference,
                smoke_fn: Optional[Callable] = vrun.assert_operational_matches_policy,
                ) -> Callable[..., vshard.ShardOutcome]:
    """Build the per-shard runner bound to the frozen execution parameters."""

    run_cfg = vrun.make_config(horizon, namespace, schedule=schedule, policy=policy)
    prefixes = run_cfg.horizons
    cells_by_id = {c.id: c for c in vgen.CELLS}

    def runner(*, spec: Dict[str, Any], out_dir: Path) -> vshard.ShardOutcome:
        cell = cells_by_id[spec["cell"]]
        out_dir = Path(out_dir)
        primary_path = out_dir / "primary_rows.csv.gz"
        reference_path = out_dir / "reference_bands.csv"

        # ONE-DRAW SMOKE at shard entry -- the agreed preflight, and the only
        # verification on this path.  The optional conformance checker is NOT
        # an execution gate.
        smoke_pair_states = 0
        if smoke_fn is not None and policy == "operational":
            probe = draw_fn(cell, spec["program_start_inclusive"], 0,
                            n_max=horizon, namespace=namespace)
            smoke_pair_states = int(
                smoke_fn(probe, run_cfg)["pair_states_compared"])

        sink = vrun.RowSink(primary_path, vrun.trial_header(schedule))
        ref_fh = reference_path.open("w")
        ref_fh.write(vpanel.REFERENCE_HEADER + "\n")

        counts = {"programs": 0, "trials": 0, "reference_calls": 0,
                  "primary_rows": 0, "reference_rows": 0}
        coordinates: List[Tuple[str, int]] = []
        errors: List[Dict[str, Any]] = []
        attempted = completed = failed = 0
        try:
          try:
            for program in range(spec["program_start_inclusive"],
                                 spec["program_stop_exclusive"]):
                coordinates.append((cell.id, program))
                counts["programs"] += 1
                for trial in range(trials_per_program):
                    attempted += 1
                    try:
                        draw = draw_fn(cell, program, trial, n_max=horizon,
                                       namespace=namespace)
                        records, _looks, _upd = evaluate_fn(draw, run_cfg, schedule)
                        sink.write(rows_fn(cell, program, trial, records, schedule))
                        counts["primary_rows"] += len(vrun.CONSTRUCTIONS)

                        for score, values in (("H", draw.z), ("D", draw.dsc)):
                            lo, hi = reference_fn(values, alpha_gate)
                            counts["reference_calls"] += 1
                            arr = np.asarray(values, dtype=np.float64)
                            run_mean = np.cumsum(arr) / np.arange(1, arr.size + 1)
                            for n in prefixes:
                                if n < 1 or n > arr.size:
                                    continue
                                i = n - 1
                                ref_fh.write(
                                    f"{cell.id},{cell.law},{cell.delay},{program},"
                                    f"{trial},{score},{int(n)},{float(lo[i])!r},"
                                    f"{float(hi[i])!r},{float(run_mean[i])!r},"
                                    f"{float(hi[i] - lo[i])!r},"
                                    f"complete_information_reference_diagnostic\n")
                                counts["reference_rows"] += 1
                        counts["trials"] += 1
                        completed += 1
                    except Exception as exc:
                        # STOP IMMEDIATELY.  Root: an injected first-trial
                        # failure "still invokes the three later trials in a
                        # four-trial fixture".  Continuing after a technical
                        # failure does more work whose value is already void and
                        # buries the first error among later ones.  The `finally`
                        # below still closes both handles.
                        failed += 1
                        errors.append({
                            "program": program, "trial": trial,
                            "message": f"{type(exc).__name__}: {exc}",
                            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime()),
                            "first_error": True,
                            "stopped_immediately": True})
                        raise _ShardAborted()
          except _ShardAborted:
            pass            # the first error is already recorded; stop here
        finally:
            # BOTH FILES CLOSED before anything is reconciled or published.
            sink.close()
            ref_fh.flush()
            os.fsync(ref_fh.fileno())
            ref_fh.close()

        return vshard.ShardOutcome(
            primary_path=primary_path, reference_path=reference_path,
            observed=counts, unique_coordinates=len(set(coordinates)),
            coordinates=coordinates, errors=errors,
            attempted=attempted, completed=completed, failed=failed, skipped=0)

    runner.smoke_enabled = smoke_fn is not None                # type: ignore[attr-defined]
    runner.prefixes = list(prefixes)                           # type: ignore[attr-defined]
    return runner
