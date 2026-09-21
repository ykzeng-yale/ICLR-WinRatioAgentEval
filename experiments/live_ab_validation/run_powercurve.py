"""Driver for the power-curve panel: supervised parent, serial child, shard receipts."""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0, str(HERE))
import vband, vgen, vpanel, vpins, vprod, vshard, vsupervise           # noqa: E402
import vpowercurve as PC                                               # noqa: E402


def run_child(out: Path, fine: bool = False) -> int:
    if fine:
        cells = PC.build_cells(PC.CELL_INDEX_BASE_FINE, PC.MU_H_LADDER_FINE)
        plan = PC.build_plan(cells, programs_per_cell=1000,
                             namespace=PC.NAMESPACE_POWER_FINE)
        ns = PC.NAMESPACE_POWER_FINE
    else:
        cells = PC.build_cells(); plan = PC.build_plan(cells); ns = PC.NAMESPACE_POWER
    (out / "POWERCURVE_PLAN.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    pins = vpins.entry_point_pins(
        policy="operational", schedule=vrun_sched(), prefixes=plan["prefixes"],
        # BUG, found by root: this passed PC.NAMESPACE_POWER (3) while the run
        # actually used ns (4 for the fine ladder), so every fine receipt records
        # coordinates.namespace = 4 beside pins.run_identity.namespace = 3.
        programs=[], cells=[c.id for c in cells], namespace=ns,
        alpha_gate=vband.ALPHA_GATE, trials_per_program=plan["trials_per_program"],
        workload="2_calls_per_trial", verification_mode=vpanel.VERIFY_PREFLIGHT,
        reference_mode=vpanel.REFERENCE_MODE, normalized_horizon=plan["horizon"],
        expected_trials=plan["total_trials"],
        expected_reference_calls=plan["total_reference_calls"])
    job_id = "PC-" + hashlib.sha256(
        json.dumps(plan["allocation"], sort_keys=True).encode()).hexdigest()[:12]
    attempt = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    job = vshard.JobCounters(started_perf=time.perf_counter())
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ctx = {"source_commit": pins["detail"]["repo"]["head"],
           "manifest_digest": pins["receipt"], "pins": pins,
           "job_id": job_id, "attempt_id": attempt,
           "root_clearance_reference": "OWNER-AUTHORIZED (power-curve panel)",
           "namespace": ns, "horizon": plan["horizon"],
           "prefixes": plan["prefixes"], "policy": "operational",
           "schedule": vrun_sched(), "alpha_gate": vband.ALPHA_GATE,
           "reference_modes": ["H", "D"],
           # was hardcoded to "namespace-3", wrong for any panel not on ns 3
           "exposure_label": (f"namespace-{ns} power-curve coordinates, FRESH for "
                              f"this panel; not poolable with the namespace-0 T1 "
                              f"replay set or with another power namespace")}
    runner = vprod.make_runner(
        horizon=plan["horizon"], namespace=ns, policy="operational",
        schedule=vrun_sched(), alpha_gate=vband.ALPHA_GATE,
        trials_per_program=plan["trials_per_program"], cells=cells)
    try:
        for entry in plan["shards"]:
            vshard.run_shard(entry, out, runner, job=job, attempt=attempt,
                             job_id=job_id, context=ctx)
    except Exception as exc:
        vshard.write_failure_receipt(out, job_id, attempt, type(exc).__name__,
                                     {"message": str(exc)}, job)
        return 5
    data = vshard.finalize_job(out, plan, job, supervision=None, context=ctx, stage="data")
    data["child_counters"] = job.snapshot()
    data["job_started_utc"] = started
    (out / "PC_CHILD_DATA_RECEIPT.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n")
    return 0 if data["data_completion"] else 6


def vrun_sched():
    import vrun
    return vrun.SCHEDULE_V2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--fine", action="store_true")
    a = ap.parse_args(argv)
    if a.child:
        a.out.mkdir(parents=True, exist_ok=True)
        return run_child(a.out, fine=a.fine)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        print(f"REFUSING: {out} non-empty", file=sys.stderr); return 2
    out.mkdir(parents=True, exist_ok=True)
    caps = vsupervise.Caps(seconds=5400.0, tree_rss_bytes=2 * 1024 ** 3,
                           output_bytes=200 * 1024 ** 2)
    sup = vsupervise.supervise(
        [sys.executable, str(HERE / "run_powercurve.py"), "--child", "--out", str(out)]
        + (["--fine"] if a.fine else []),
        out, caps, label="power_curve_panel",
        require_available_ram_bytes=2 * 1024 ** 3)
    if a.fine:
        cells = PC.build_cells(PC.CELL_INDEX_BASE_FINE, PC.MU_H_LADDER_FINE)
        plan = PC.build_plan(cells, programs_per_cell=1000,
                             namespace=PC.NAMESPACE_POWER_FINE)
    else:
        cells = PC.build_cells(); plan = PC.build_plan(cells)
    child_p = out / "PC_CHILD_DATA_RECEIPT.json"
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
    final = vshard.finalize_job(out, plan, job, supervision=sup, context=ctx, stage="final")
    (out / "PC_JOB_RECEIPT.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"within_caps": sup["within_caps"], "breach": sup["breach"],
                      "wall_seconds": sup["observed"]["wall_seconds"],
                      "scientific_completion": final["scientific_completion"]},
                     indent=2, sort_keys=True))
    return 0 if final["scientific_completion"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
