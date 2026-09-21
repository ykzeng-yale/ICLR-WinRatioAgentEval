"""The authorized bounded measurement, run as a SUPERVISED child process.

Root, 2026-09-21 08:28, ranked action 3:

    "One changed-workload measurement is authorized after steps 1-2. Use the same
     fixed namespace 1, cells C1/C2, programs 1000-1004, horizons 1000/2000, four
     trials: exactly 20 units / 80 trials / 160 reference calls, NOW IN THE PINNED
     PREFLIGHT-ONLY MODE. Same 300-second / 2-GiB / 200-MiB parent limits ... Compare
     decompressed primary and reference data hashes against this delivery, without
     inspecting effects. Do not repeat the verified-mode baseline, sweep timings,
     change the tier, raise caps, or launch the full grid."

Two roles in one file:

  * **parent** (default): capacity-check, then run the child under ``vsupervise``
    with the authorized caps covering the WHOLE operation, then compare persisted
    data hashes against the delivered baseline.
  * **child** (``--child``): both horizon passes plus the combined receipt, so the
    parent's single supervised window aggregates both -- the previous delivery
    supervised neither and aggregated nothing.

This pass exists because the measured executable workload CHANGED (preflight-only
verification, streamed reference output), not to repair metadata.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vpanel                                                   # noqa: E402
import vpins                                                    # noqa: E402
import vsupervise                                               # noqa: E402

#: The delivered verified-mode baseline's DECOMPRESSED primary hashes, quoted
#: from the root's 08:28 review and independently recomputed by the owner from
#: the deposited bytes before use.
BASELINE_DECOMPRESSED_PRIMARY_SHA256 = {
    1000: "9dd82799d8df7e74b187e30795be14192e3726617d76a3126652646ff2ec6e44",
    2000: "d9fd343f7153acf0fd1b34c8bcb1dc057c2b8923f1ecf5b20e999792b18d425a",
}
BASELINE_DIR = (HERE.parent.parent / "results" / "live_ab_validation_v2"
                / "measurement_20260921")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run_child(out_dir: Path) -> Dict[str, Any]:
    """Both horizon passes, preflight-only, plus the combined receipt."""
    out_dir = Path(out_dir)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.perf_counter()
    per: Dict[str, Any] = {}
    for h in vpins.ALLOWLIST.horizons:
        cfg = vpanel.PanelConfig(
            cells=("C1", "C2"), n_max=h, programs=5,
            mode=vpanel.MODE_MEASUREMENT, namespace=1,
            program_indices=(1000, 1001, 1002, 1003, 1004),
            policy="operational", schedule="v2_tick_batched",
            verification_mode=vpanel.VERIFY_PREFLIGHT,
            label=f"preflight_only_measurement_h{h}")
        t = time.perf_counter()
        r = vpanel.run_panel(cfg, out_dir / f"horizon_{h}")
        per[str(h)] = {"receipt": r, "wall_seconds": time.perf_counter() - t}
    total = time.perf_counter() - t0

    trials = sum(per[h]["receipt"]["counts"]["trials"] for h in per)
    refs = sum(per[h]["receipt"]["counts"]["reference_calls_h"]
               + per[h]["receipt"]["counts"]["reference_calls_d"] for h in per)
    combined = {
        "schema": "live_ab_validation_v2.bounded_measurement.2",
        "authority": ("root disposition 2026-09-21 08:28, ranked action 3: one "
                      "changed-workload measurement in pinned preflight-only mode"),
        "convention": ("descriptive; ONE observed pass under recorded concurrent "
                       "load. NOT calibration, NOT a coverage rate, NOT an "
                       "uncontended benchmark, NOT a guaranteed bound."),
        "why_this_pass_exists": ("the measured executable workload CHANGED "
                                 "(preflight-only verification, streamed reference "
                                 "output); it is not a metadata repair"),
        "verification_mode": vpanel.VERIFY_PREFLIGHT,
        "reference_mode": vpanel.REFERENCE_MODE,
        "authorized_vs_actual": {
            "units": vpins.ALLOWLIST.check_arithmetic(),
            "trial_evaluations_actual": trials,
            "reference_calls_actual": refs,
            "matches_authorization": trials == 80 and refs == 160,
        },
        "observed": {
            "child_total_wall_seconds": total,
            "per_horizon": {h: {
                "wall_seconds": per[h]["wall_seconds"],
                "inner_elapsed_seconds": per[h]["receipt"]["elapsed_seconds"],
                "trials": per[h]["receipt"]["counts"]["trials"],
                "reference_calls": (per[h]["receipt"]["counts"]["reference_calls_h"]
                                    + per[h]["receipt"]["counts"]["reference_calls_d"]),
                "policy_checks": per[h]["receipt"]["counts"]["policy_checks"],
                "policy_pair_states": per[h]["receipt"]["counts"]["policy_pair_states"],
                "getrusage_self_and_reaped_peak_bytes":
                    per[h]["receipt"]["peak_rss_bytes"],
                "outputs": per[h]["receipt"]["outputs"],
            } for h in per},
        },
        "rss_label_note": ("the per-horizon figure above is the getrusage "
                           "self/reaped-child peak, NOT a process-tree peak. The "
                           "simultaneous tree peak is the PARENT's measurement, in "
                           "SUPERVISION.json."),
        "pins": per[str(vpins.ALLOWLIST.horizons[0])]["receipt"]["pins"],
        "pin_drift_check": {h: per[h]["receipt"]["pin_drift_check"] for h in per},
        "timestamps": {"child_started_utc": started,
                       "child_ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                        time.gmtime())},
        "effect_summaries": "WITHHELD; never accumulated in measurement mode.",
    }
    (out_dir / "CHILD_RECEIPT.json").write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n")
    return combined


def compare_against_baseline(out_dir: Path) -> Dict[str, Any]:
    """Persisted DATA hashes against the delivered verified-mode baseline.

    Decompressed primary bytes and the reference CSV bytes only.  No effect
    value is read, printed or compared -- the comparison is over whole-file
    digests, which reveal nothing about any decision.
    """
    rows: Dict[str, Any] = {}
    identical = True
    for h in vpins.ALLOWLIST.horizons:
        new_p = out_dir / f"horizon_{h}" / "primary_rows.csv.gz"
        new_r = out_dir / f"horizon_{h}" / "reference_bands.csv"
        base_r = BASELINE_DIR / f"horizon_{h}" / "reference_bands.csv"
        new_primary = _sha(gzip.decompress(new_p.read_bytes()))
        want_primary = BASELINE_DECOMPRESSED_PRIMARY_SHA256[h]
        new_ref = _sha(new_r.read_bytes())
        want_ref = _sha(base_r.read_bytes()) if base_r.is_file() else None
        ok_p = new_primary == want_primary
        ok_r = (want_ref is None) or (new_ref == want_ref)
        identical &= ok_p and ok_r
        rows[str(h)] = {
            "decompressed_primary_sha256": new_primary,
            "baseline_decompressed_primary_sha256": want_primary,
            "primary_identical": ok_p,
            "reference_csv_sha256": new_ref,
            "baseline_reference_csv_sha256": want_ref,
            "reference_identical": ok_r,
        }
    return {"per_horizon": rows, "all_identical": identical,
            "method": ("whole-file digests of decompressed primary and reference "
                       "text; no effect value inspected"),
            "meaning": ("identical hashes mean the execution-verification "
                        "amendment changed no persisted scientific byte, which is "
                        "what root required it to prove")}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--child", action="store_true",
                    help="internal: run the passes (spawned by the parent)")
    a = ap.parse_args(argv)

    if a.child:
        run_child(a.out)
        return 0

    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        print(f"REFUSING: {out} is non-empty", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    capacity = vpanel.host_capacity()
    du = shutil.disk_usage(str(out))
    capacity["disk_free_bytes_at_target"] = du.free
    adequate = (du.free > 4 * 1024 ** 3
                and capacity["load_fraction_of_cores_1m"] < 4.0)
    if not adequate:
        (out / "CAPACITY_BLOCKED.json").write_text(
            json.dumps({"adequate": False, "capacity": capacity}, indent=2))
        print("capacity insufficient; reported, not forced", file=sys.stderr)
        return 3

    caps = vsupervise.Caps(seconds=vpins.ALLOWLIST.cap_seconds,
                           tree_rss_bytes=vpins.ALLOWLIST.cap_peak_rss_bytes,
                           output_bytes=vpins.ALLOWLIST.cap_output_bytes)
    sup = vsupervise.supervise(
        [sys.executable, str(HERE / "vmeasure.py"), "--child", "--out", str(out)],
        out, caps, label="authorized_preflight_only_measurement")

    result: Dict[str, Any] = {"supervision": sup, "capacity_at_start": capacity}
    if sup["within_caps"]:
        result["comparison_against_baseline"] = compare_against_baseline(out)
    (out / "PARENT_RECEIPT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "within_caps": sup["within_caps"],
        "breach": sup["breach"],
        "wall_seconds": sup["observed"]["wall_seconds"],
        "peak_tree_rss_bytes": sup["observed"]["peak_tree_rss_bytes"],
        "final_output_bytes": sup["observed"]["final_output_bytes"],
        "hashes_identical": result.get("comparison_against_baseline", {}).get("all_identical"),
    }, indent=2, sort_keys=True))
    return 0 if sup["within_caps"] else 1


if __name__ == "__main__":                                     # pragma: no cover
    raise SystemExit(main())
