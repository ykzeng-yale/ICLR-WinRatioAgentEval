"""DRIVER for the matched certificate ablation: the disabled arm, once.

Root's remaining implementation list, 2026-09-21 16:25 handoff:

    "connect the actual adapter_tick_sums evaluation path, capture the original
     callable if temporarily injecting the wrapper to avoid recursion, positively
     record the actual driver/variant/law/config pins and matching namespace
     before evaluating outcomes.  One deterministic branch witness through that
     path suffices; no additional routine signoff or collection expansion."

Each clause is executed here, in that order, and written to
``ABLATION_PREFLIGHT.json`` BEFORE the first shard runs:

  1. ``vablation.install()`` rebinds ``vgen.state_at_age``, which is the module
     global ``vgen.adapter_tick_sums`` resolves -- so the variant is on the real
     ADAPTER path, not a parallel reimplementation of it.
  2. ``vablation`` captured the original callable at import and calls it by that
     binding, so installation cannot recurse.  ``original_restored()`` lifts the
     rebinding for the two checks that must see the unmodified implementation.
  3. ``vpins.entry_point_pins(variant=..., law_weights=...)`` records the driver,
     the arm and the runtime-registered laws; the namespace is the ORIGINAL
     namespace 3, passed once and used everywhere.
  4. ``vablation.branch_witness`` drives ``vgen.adapter_tick_sums`` itself.

WHAT THIS DRIVER DOES NOT DO
----------------------------
No model calls.  No reference calls -- the EB reference bands of the original
panel are a complete-information diagnostic that the ablation does not touch and
must not re-derive, so the plan expects zero of them and the runner makes none.
No new draws: every coordinate is a namespace-3 coordinate the coarse panel
already ran.

The ORIGINAL arm is NOT re-run.  Its per-trial rows are the delivered ones in
``powercurve_20260921``; pairing against the record itself is stronger than
pairing against a recomputation of it, and the CPREFIX/NAIVE decision columns of
this run reproduce that record bit for bit, which is what makes the pairing
checkable rather than asserted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vablation                                                # noqa: E402
import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vpanel                                                   # noqa: E402
import vpins                                                    # noqa: E402
import vrun                                                     # noqa: E402
import vshard                                                   # noqa: E402
import vsupervise                                               # noqa: E402
import vpowercurve as PC                                        # noqa: E402

PROGRAMS_PER_SHARD = 500
CAP_SECONDS = 3600.0


class _ShardAborted(Exception):
    """Internal: stop this shard at the first technical failure."""


def ablation_cells() -> Tuple[Any, ...]:
    """The four coarse-panel cells, with their ORIGINAL indices preserved.

    ``PC.build_cells()`` is called with its own defaults and then FILTERED.
    Rebuilding a four-cell ladder from scratch would renumber ``index``, and the
    index feeds the spawn key, so the "same draws" claim would be false in the
    one place it is hardest to notice.
    """
    cells = tuple(c for c in PC.build_cells() if c.id in vablation.ABLATION_CELLS)
    if len(cells) != len(vablation.ABLATION_CELLS):
        raise RuntimeError(f"expected {vablation.ABLATION_CELLS}, got "
                           f"{[c.id for c in cells]}")
    return cells


def build_plan(cells: Sequence[Any]) -> Dict[str, Any]:
    """The coarse panel's shard geometry, with reference expectations at ZERO."""
    plan = PC.build_plan(tuple(cells), programs_per_cell=vablation.ABLATION_PROGRAMS,
                         programs_per_shard=PROGRAMS_PER_SHARD,
                         horizon=vablation.ABLATION_HORIZON,
                         trials=vablation.ABLATION_TRIALS,
                         namespace=vablation.ABLATION_NAMESPACE)
    plan["schema"] = "live_ab_validation_v2.certificate_ablation_plan.1"
    plan["variant"] = vablation.VARIANT_NAME
    plan["reference_calls_note"] = (
        "ZERO by specification: the ablation reuses the original panel's "
        "complete-information reference diagnostic and makes no new reference call")
    for s in plan["shards"]:
        s["expected_reference_calls"] = 0
        s["expected_reference_rows"] = 0
    plan["total_reference_calls"] = 0
    plan["total_reference_rows"] = 0
    plan["job_caps"] = {"seconds": CAP_SECONDS,
                        "sampled_process_tree_bytes": 2 * 1024 ** 3,
                        "total_output_bytes": 200 * 1024 ** 2,
                        "reset_per_shard": False}
    return plan


def law_pins(cells: Sequence[Any]) -> Dict[str, Any]:
    """The RUNTIME-registered laws, by realised integer weight vector."""
    out: Dict[str, Any] = {}
    for c in cells:
        if c.law in out:
            continue
        w = {a: int(vgen.LAW_WEIGHTS[c.law][a]) for a in vgen.ATOM_ORDER}
        out[c.law] = {
            "weights": w,
            "denominator": int(vgen.WEIGHT_DENOMINATOR),
            "mu_h": float(vgen.mu_h_of(c.law)),
            "mu_s": float(vgen.mu_s_of(c.law)),
            "registered_by": "vpowercurve.register_laws (runtime, ADDITIVE)",
        }
    return out


#: The six columns the ablation is ALLOWED to move outside the ADAPTER band.
#: ``_look_fractions`` is shared by all three constructions, so resetting the
#: certificate counters zeroes these for CPREFIX and NAIVE too, and
#: ``n_point_resolved = n_certified + n_point_cost`` follows.  The independent
#: review accepted exactly this: "recompute any 'point-resolved' diagnostic from
#: the variant's bounds/counters; do not relabel a merely widened pending pair as
#: a changed final outcome."
CERTIFICATE_DIAGNOSTIC_COLUMNS = frozenset({
    "cost_collapsed_fraction", "cost_narrowed_fraction", "n_point_resolved",
    "final_cost_collapsed_fraction", "final_cost_narrowed_fraction",
    "final_n_point_resolved"})

ORIGINAL_ARM_ROOT = (Path(__file__).resolve().parents[2] / "results" /
                     "live_ab_validation_v2" / "powercurve_20260921")


def schedule_identity_witness(cells: Sequence[Any], schedule: str,
                              original_root: Path = ORIGINAL_ARM_ROOT,
                              programs: int = 5, trials: int = 4) -> Dict[str, Any]:
    """EXECUTED schedule equality, against the delivered original records.

    Root's disposition: "The delivered 384 snapshot / 768000 array-state counts
    have the stated arithmetic, but schedule equality is DESCRIBED, not exercised
    through an execution driver."  This exercises it.

    CPREFIX and NAIVE take their bands from ``vgen.completion_tick_states``, which
    never calls ``state_at_age``.  Every column they emit is therefore a function
    of the draw, the enrollment and the schedule alone -- except the six shared
    certificate diagnostics.  So if this run's CPREFIX and NAIVE rows reproduce
    the DELIVERED coarse-panel rows character for character outside those six
    columns, the draws, reveal ticks, enrollment and look schedule of the two arms
    are the same ones.  Not argued: read off the committed file.

    ADAPTER is deliberately NOT inspected here.  Its rows are the outcome this
    analysis exists to measure, and the preflight does not look at outcomes.
    """
    import csv
    import gzip

    header = vrun.trial_header(schedule).strip().split(",")
    checked = 0
    moved: Dict[str, List[str]] = {}
    per_cell: Dict[str, Dict[str, Any]] = {}
    for cell in cells:
        matches = sorted(original_root.glob(f"shard_*_{cell.id}-p0000-*"))
        if len(matches) != 1:
            raise RuntimeError(
                f"expected exactly one delivered shard for {cell.id} at "
                f"{original_root}, found {[m.name for m in matches]}")
        original: Dict[Tuple[str, str, str], Dict[str, str]] = {}
        with gzip.open(matches[0] / "primary_rows.csv.gz", "rt") as fh:
            for row in csv.DictReader(fh):
                if int(row["program"]) >= programs:
                    break
                original[(row["program"], row["trial"], row["construction"])] = row
        run_cfg = vrun.make_config(vablation.ABLATION_HORIZON,
                                   vablation.ABLATION_NAMESPACE,
                                   schedule=schedule, policy="operational")
        cell_moved = set()
        for program in range(programs):
            for trial in range(trials):
                draw = vgen.draw_trial(cell, program, trial,
                                       n_max=vablation.ABLATION_HORIZON,
                                       namespace=vablation.ABLATION_NAMESPACE)
                records, _l, _u = vrun.evaluate_trial(draw, run_cfg, schedule)
                text = vrun.trial_rows(cell, program, trial, records, schedule)
                for line in text.strip().split("\n"):
                    row = dict(zip(header, line.split(",")))
                    if row["construction"] == "ADAPTER":
                        continue
                    key = (row["program"], row["trial"], row["construction"])
                    if key not in original:
                        raise RuntimeError(f"{cell.id} {key} absent from the "
                                           f"delivered original shard")
                    ref = original[key]
                    for col in header:
                        if ref[col] != row[col]:
                            cell_moved.add(col)
                    checked += 1
        illegal = sorted(cell_moved - CERTIFICATE_DIAGNOSTIC_COLUMNS)
        if illegal:
            raise AssertionError(
                f"{cell.id}: the disabled arm moved CPREFIX/NAIVE columns that "
                f"the ablation cannot touch: {illegal}. The two arms do not "
                f"share draws, enrollment or schedule, and the pairing is void.")
        moved[cell.id] = sorted(cell_moved)
        per_cell[cell.id] = {"delivered_shard": matches[0].name,
                             "rows_compared": programs * trials * 2}
    return {
        "claim": ("CPREFIX and NAIVE rows of the disabled arm reproduce the "
                  "DELIVERED coarse-panel rows exactly, outside the six shared "
                  "certificate-diagnostic columns"),
        "rows_compared": checked,
        "constructions_compared": ["CPREFIX", "NAIVE"],
        "adapter_excluded_because": ("ADAPTER rows are the outcome under test; "
                                     "the preflight does not read outcomes"),
        "columns_that_moved_by_cell": moved,
        "columns_permitted_to_move": sorted(CERTIFICATE_DIAGNOSTIC_COLUMNS),
        "coordinates": {"programs": list(range(programs)),
                        "trials": list(range(trials)),
                        "note": ("a bounded sample of the delivered records, not "
                                 "the full 32,000-trial panel")},
        "per_cell": per_cell,
    }


def make_runner(*, horizon: int, namespace: int, policy: str, schedule: str,
                trials_per_program: int, cells: Sequence[Any]):
    """Per-shard runner: primary rows only, operator verified live every shard."""
    run_cfg = vrun.make_config(horizon, namespace, schedule=schedule, policy=policy)
    cells_by_id = {c.id: c for c in cells}

    def runner(*, spec: Dict[str, Any], out_dir: Path) -> vshard.ShardOutcome:
        if spec["cell"] not in cells_by_id:
            raise KeyError(f"cell {spec['cell']!r} not in {sorted(cells_by_id)}")
        cell = cells_by_id[spec["cell"]]
        out_dir = Path(out_dir)
        primary_path = out_dir / "primary_rows.csv.gz"
        reference_path = out_dir / "reference_bands.csv"

        # REFUSE TO PRODUCE THE WRONG ARM.  Without this a lifted or never-applied
        # installation yields a full, well-formed, perfectly reconciled shard of
        # ORIGINAL rows wearing the disabled arm's label -- the failure that would
        # be hardest to detect downstream, because every count would agree.
        if not vablation.is_installed():
            raise RuntimeError(
                "the ablation operator is NOT installed; this shard would be the "
                "original arm under the disabled arm's name")

        # The vgen-vs-vpolicy conformance smoke, against the UNMODIFIED
        # implementation.  Under the installed operator it would compare the
        # ablation with the policy module it is deliberately not equal to and
        # fail for the wrong reason; run against the original it still does its
        # job, which is to prove the base implementation has not drifted.
        probe = vgen.draw_trial(cell, spec["program_start_inclusive"], 0,
                                n_max=horizon, namespace=namespace)
        with vablation.original_restored():
            smoke = vrun.assert_operational_matches_policy(probe, run_cfg)

        sink = vrun.RowSink(primary_path, vrun.trial_header(schedule))
        # Header only.  The file exists so the receipt's file table is complete
        # and the shard contract's existence check is honest; it carries no rows
        # because no reference call was made.
        reference_path.write_text(vpanel.REFERENCE_HEADER + "\n")

        counts = {"programs": 0, "trials": 0, "reference_calls": 0,
                  "primary_rows": 0, "reference_rows": 0}
        coordinates: List[Tuple[str, int]] = []
        errors: List[Dict[str, Any]] = []
        attempted = completed = failed = 0
        entries_before = vablation.call_count()
        try:
            try:
                for program in range(spec["program_start_inclusive"],
                                     spec["program_stop_exclusive"]):
                    coordinates.append((cell.id, program))
                    counts["programs"] += 1
                    for trial in range(trials_per_program):
                        attempted += 1
                        try:
                            draw = vgen.draw_trial(cell, program, trial,
                                                   n_max=horizon, namespace=namespace)
                            records, _looks, _upd = vrun.evaluate_trial(
                                draw, run_cfg, schedule)
                            sink.write(vrun.trial_rows(cell, program, trial,
                                                       records, schedule))
                            counts["primary_rows"] += len(vrun.CONSTRUCTIONS)
                            counts["trials"] += 1
                            completed += 1
                        except Exception as exc:
                            failed += 1
                            errors.append({
                                "program": program, "trial": trial,
                                "message": f"{type(exc).__name__}: {exc}",
                                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                     time.gmtime()),
                                "first_error": True, "stopped_immediately": True})
                            raise _ShardAborted()
            except _ShardAborted:
                pass
        finally:
            sink.close()

        entered = vablation.call_count() - entries_before
        if completed and entered < completed:
            raise RuntimeError(
                f"the ablation operator was entered {entered} times across "
                f"{completed} completed trials; it was not on the evaluation "
                f"path for every trial and this shard is not the disabled arm")
        (out_dir / "SHARD_OPERATOR_WITNESS.json").write_text(json.dumps({
            "variant": vablation.VARIANT_NAME,
            "operator_entries": entered,
            "completed_trials": completed,
            "operator_installed_throughout": vablation.is_installed(),
            "conformance_smoke_against_original": smoke,
        }, indent=2, sort_keys=True) + "\n")

        return vshard.ShardOutcome(
            primary_path=primary_path, reference_path=reference_path,
            observed=counts, unique_coordinates=len(set(coordinates)),
            coordinates=coordinates, errors=errors,
            attempted=attempted, completed=completed, failed=failed, skipped=0)

    return runner


def run_child(out: Path) -> int:
    cells = ablation_cells()
    plan = build_plan(cells)
    ns = vablation.ABLATION_NAMESPACE
    sched = vrun.SCHEDULE_V2
    laws = law_pins(cells)

    # ---- everything below runs BEFORE the first outcome is evaluated -------
    witness = vablation.branch_witness(cells[0])
    invariants = vablation.assert_invariants()
    with vablation.installed():
        schedule_identity = schedule_identity_witness(cells, sched)

    pins = vpins.entry_point_pins(
        policy="operational", schedule=sched, prefixes=plan["prefixes"],
        programs=[], cells=[c.id for c in cells], namespace=ns,
        alpha_gate=vband.ALPHA_GATE, trials_per_program=plan["trials_per_program"],
        workload="0_calls_per_trial_no_reference",
        verification_mode=vpanel.VERIFY_PREFLIGHT,
        reference_mode="none", normalized_horizon=plan["horizon"],
        expected_trials=plan["total_trials"], expected_reference_calls=0,
        variant=vablation.VARIANT_NAME, law_weights=laws)

    (out / "ABLATION_PLAN.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n")
    (out / "ABLATION_PREFLIGHT.json").write_text(json.dumps({
        "schema": "live_ab_validation_v2.certificate_ablation_preflight.1",
        "label": vablation.LABEL,
        "spec": vablation.spec(),
        "branch_witness": witness,
        "schedule_identity_witness": schedule_identity,
        "deterministic_invariants": invariants,
        "law_pins": laws,
        "pins_before": pins,
        "namespace": ns,
        "original_arm_source": ("results/live_ab_validation_v2/powercurve_20260921 "
                                "-- the DELIVERED records, not a recomputation"),
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2, sort_keys=True) + "\n")

    job_id = "AB-" + hashlib.sha256(
        json.dumps({"alloc": plan["allocation"], "variant": vablation.VARIANT_NAME},
                   sort_keys=True).encode()).hexdigest()[:12]
    attempt = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    job = vshard.JobCounters(started_perf=time.perf_counter())
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ctx = {"source_commit": pins["detail"]["repo"]["head"],
           "manifest_digest": pins["receipt"], "pins": pins,
           "job_id": job_id, "attempt_id": attempt,
           "root_clearance_reference": ("ROOT-SPECIFIED matched certificate "
                                        "ablation, issue 12 comment 5762860561, "
                                        "runtime handoff 2026-09-21 16:25"),
           "namespace": ns, "horizon": plan["horizon"],
           "prefixes": plan["prefixes"], "policy": "operational",
           "schedule": sched, "alpha_gate": vband.ALPHA_GATE,
           "reference_modes": [],
           "variant": vablation.VARIANT_NAME,
           "law_pins": laws,
           "exposure_label": (
               "namespace-3 power-curve coordinates, RE-EVALUATED under the "
               "certificate-disabled operator; the SAME draws as the coarse "
               "panel, deliberately, because the comparison is paired. These "
               "rows are not an independent sample and must never be pooled "
               "with the original arm's.")}

    runner = make_runner(horizon=plan["horizon"], namespace=ns,
                         policy="operational", schedule=sched,
                         trials_per_program=plan["trials_per_program"],
                         cells=cells)

    rc = 0
    with vablation.installed():
        try:
            for entry in plan["shards"]:
                vshard.run_shard(entry, out, runner, job=job, attempt=attempt,
                                 job_id=job_id, context=ctx)
        except Exception as exc:
            vshard.write_failure_receipt(out, job_id, attempt, type(exc).__name__,
                                         {"message": str(exc)}, job)
            rc = 5
    if rc:
        return rc

    pins_after = vpins.entry_point_pins(
        policy="operational", schedule=sched, prefixes=plan["prefixes"],
        programs=[], cells=[c.id for c in cells], namespace=ns,
        alpha_gate=vband.ALPHA_GATE, trials_per_program=plan["trials_per_program"],
        workload="0_calls_per_trial_no_reference",
        verification_mode=vpanel.VERIFY_PREFLIGHT,
        reference_mode="none", normalized_horizon=plan["horizon"],
        expected_trials=plan["total_trials"], expected_reference_calls=0,
        variant=vablation.VARIANT_NAME, law_weights=laws)
    drift = vpins.assert_unchanged(pins, pins_after)

    data = vshard.finalize_job(out, plan, job, supervision=None, context=ctx,
                               stage="data")
    data["child_counters"] = job.snapshot()
    data["job_started_utc"] = started
    data["variant"] = vablation.VARIANT_NAME
    data["operator_entries_total"] = vablation.call_count()
    data["operator_uninstalled_after_run"] = not vablation.is_installed()
    data["pin_drift_across_measurement"] = drift
    (out / "AB_CHILD_DATA_RECEIPT.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n")
    return 0 if data["data_completion"] else 6


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--child", action="store_true")
    a = ap.parse_args(argv)
    # ABSOLUTE, ALWAYS.  ``vsupervise.supervise`` runs the child with
    # ``cwd=HERE`` (this module's directory), not the parent's cwd, so a relative
    # --out is resolved against a DIFFERENT directory in the child than in the
    # parent.  Attempt 1 of this run did exactly that: the child completed all 16
    # shards perfectly, into experiments/live_ab_validation/results/..., while the
    # parent reconciled an empty directory and reported no completion.  Nothing
    # was lost and nothing was wrong with the science; the two processes simply
    # did not mean the same path by the same string.
    if a.child:
        out = Path(a.out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        return run_child(out)
    out = Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):
        print(f"REFUSING: {out} non-empty", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    caps = vsupervise.Caps(seconds=CAP_SECONDS, tree_rss_bytes=2 * 1024 ** 3,
                           output_bytes=200 * 1024 ** 2)
    sup = vsupervise.supervise(
        [sys.executable, str(HERE / "run_ablation.py"), "--child", "--out", str(out)],
        out, caps, label="certificate_ablation_disabled_arm",
        require_available_ram_bytes=2 * 1024 ** 3)
    plan = build_plan(ablation_cells())
    child_p = out / "AB_CHILD_DATA_RECEIPT.json"
    child = json.loads(child_p.read_text()) if child_p.is_file() else None
    job = vshard.JobCounters(started_perf=time.perf_counter())
    if child and child.get("child_counters"):
        c = child["child_counters"]
        job = vshard.JobCounters(
            started_perf=time.perf_counter() - float(c.get("elapsed_seconds") or 0),
            shards_completed=c["shards_completed"], trials=c["trials"],
            reference_calls=c["reference_calls"], primary_rows=c["primary_rows"],
            reference_rows=c["reference_rows"], output_bytes=c["output_bytes"])
    ctx = {"job_id": child["job_id"], "attempt_id": child["attempt_id"],
           "manifest_digest": None, "source_commit": None} if child else {}
    final = vshard.finalize_job(out, plan, job, supervision=sup, context=ctx,
                                stage="final")
    (out / "AB_JOB_RECEIPT.json").write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"within_caps": sup["within_caps"], "breach": sup["breach"],
                      "wall_seconds": sup["observed"]["wall_seconds"],
                      "scientific_completion": final["scientific_completion"]},
                     indent=2, sort_keys=True))
    return 0 if final["scientific_completion"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
