#!/usr/bin/env python3
"""eb_descriptive_correction.py -- regenerate ONLY the mislabelled columns.

THE DEFECT, as the reference-delta review of the 04:53 cycle stated it:
``eb_width_diagnostic`` reported ``cumsum((z - mus) ** 2)`` under the name
``realized_variance_sum``.  That sum subtracts a DIFFERENT contemporaneous
running mean at each observation.  It is NOT ``sum_{i<=n} (z_i - mean(z[:n]))^2``,
the ordinary realized prefix variance sum, so the column name and the derived
``clock_minus_realized_variance`` were both misleading.

WHAT IS AND IS NOT AFFECTED.  The mislabel never entered the reference call or
its residual clock, so NO saved mixture width, ratio, running mean or clock
changes.  Only DESCRIPTIVE columns are affected, which is why only those are
regenerated here.

WHY THIS IS A SEPARATE FILE.  The instruction is to repair the description
WITHOUT rerunning unchanged science, and to preserve the old receipt.  So:

  * ``results/live_ab_validation_v2/reference_width_diagnostic.json`` is NOT
    edited, NOT overwritten and NOT deleted.  It keeps its bytes and its label.
  * The reference is NOT called here.  No band, no width, no ratio is
    recomputed; the eight declared latent paths are regenerated deterministically
    and only the two sums of squares and the clock are recomputed from them.
  * The old column is carried forward under its CORRECT name so the old numbers
    remain traceable, and the correctly defined prefix sum is added beside it.

CPU only.  No model call, no network, no reference call.  Writes one JSON under
``results/live_ab_validation_v2/`` and nothing else.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parent
REPO_ROOT = VALIDATION.parents[1]
for _p in (str(VALIDATION), str(HERE), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eb_width_diagnostic as diag                               # noqa: E402

SAVED = (REPO_ROOT / "results" / "live_ab_validation_v2"
         / "reference_width_diagnostic.json")
OUT = (REPO_ROOT / "results" / "live_ab_validation_v2"
       / "reference_width_diagnostic_descriptive_correction.json")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> Dict[str, Any]:
    import vcompare
    vcompare.select_snapshot("v2")
    cfg = vcompare.load_frozen_config()
    gen = vcompare.FrozenGenerator(cfg)

    rows: List[Dict[str, Any]] = []
    for cell_id, prog, trial in diag.STREAMS:
        st = gen.build(cell_id, prog, trial)
        z = np.asarray(st.z_true, dtype=np.float64)
        t = np.arange(1, z.size + 1, dtype=np.float64)
        mus = np.cumsum(z) / t
        clock = diag.residual_clock(z)
        contemporaneous = np.cumsum((z - mus) ** 2)
        prefix_centered = np.cumsum(z * z) - t * mus * mus
        for n in diag.N_GRID:
            if n > z.size:
                continue
            i = n - 1
            rows.append({
                "cell": cell_id, "program": prog, "trial": trial, "n": n,
                "running_mean": float(mus[i]),
                "reference_clock_V_n": float(clock[i]),
                # the OLD column, under its CORRECT name.  Same number, honest
                # label, so the old receipt stays traceable.
                "contemporaneously_centered_squared_residual_sum":
                    float(contemporaneous[i]),
                # the column the old name CLAIMED to be, now actually computed
                "prefix_centered_sum_of_squares": float(prefix_centered[i]),
                "clock_minus_contemporaneously_centered_sum":
                    float(clock[i] - contemporaneous[i]),
                "clock_minus_prefix_centered_sum_of_squares":
                    float(clock[i] - prefix_centered[i]),
            })

    # reconcile against the preserved receipt: every OLD value must reappear
    # unchanged under the corrected name, or the correction is not a relabel.
    reconciliation: Dict[str, Any] = {"checked": 0, "mismatches": []}
    if SAVED.is_file():
        old = json.loads(SAVED.read_text())
        by_key = {(r["cell"], r["n"]): r for r in old.get("rows", [])}
        for r in rows:
            o = by_key.get((r["cell"], r["n"]))
            if o is None or "realized_variance_sum" not in o:
                continue
            reconciliation["checked"] += 1
            for old_name, new_name in (
                    ("realized_variance_sum",
                     "contemporaneously_centered_squared_residual_sum"),
                    ("reference_clock_V_n", "reference_clock_V_n"),
                    ("running_mean", "running_mean")):
                if abs(float(o[old_name]) - float(r[new_name])) > 1e-12:
                    reconciliation["mismatches"].append(
                        {"cell": r["cell"], "n": r["n"], "field": old_name,
                         "saved": o[old_name], "recomputed": r[new_name]})
    reconciliation["all_preserved_values_reproduce"] = (
        not reconciliation["mismatches"])

    witness = next((r for r in rows if r["cell"] == "C8" and r["n"] == 2000),
                   None)
    return {
        "schema": ("live_ab_validation_v2.reference."
                   "width_diagnostic_descriptive_correction.1"),
        "what_this_corrects": (
            "the column previously emitted as 'realized_variance_sum' is a sum "
            "of CONTEMPORANEOUSLY CENTRED squared residuals, not the ordinary "
            "prefix sum of squares about the prefix mean. It is renamed, and "
            "the correctly defined prefix sum is computed beside it."),
        "what_it_does_not_change": [
            "no reference call is made here",
            "no mixture width, ratio, running mean or residual clock changes",
            "the saved receipt is preserved unedited and keeps its label",
            "no scientific rule, alpha, margin, seed or stopping rule is touched",
        ],
        "preserved_receipt": {
            "path": str(SAVED.relative_to(REPO_ROOT)),
            "sha256": _sha(SAVED) if SAVED.is_file() else None,
            "status": "PRESERVED, unedited",
        },
        "reconciliation_against_the_preserved_receipt": reconciliation,
        "review_witness_C8_n2000": (
            {"prefix_centered_sum_of_squares":
                witness["prefix_centered_sum_of_squares"],
             "contemporaneously_centered_squared_residual_sum":
                witness["contemporaneously_centered_squared_residual_sum"],
             "reference_clock_V_n": witness["reference_clock_V_n"],
             "note": ("the reference-delta review reported 1332.8875, "
                      "1328.0053387752 and 1338.3695496439 for these three "
                      "quantities; they are reproduced here independently")}
            if witness else None),
        "alpha_error_history_correction": {
            "old_text": ("wrong error budget (alpha pre-halved against a "
                         "wrapper that halves internally)"),
            "new_text": ("wrong error budget (the FULL alpha = 0.00625 was "
                         "passed to poly_stitching_bound, which applies NO "
                         "split, and compared against the selected wrapper "
                         "confseq_eb, which splits alpha/2 internally; the two "
                         "were not at the same level)"),
            "why": ("the old entry reversed the direction of the error. The "
                    "withdrawn document declared a DIRECT stitched-boundary "
                    "call at the full alpha with no internal split; it did not "
                    "pre-halve anything."),
            "affects_any_current_number": False,
            "repaired_in": "reference/eb_width_diagnostic.py",
        },
        "scope": {
            "streams": [list(s) for s in diag.STREAMS],
            "n_grid": list(diag.N_GRID),
            "rows": len(rows),
            "hierarchy_score_only": True,
            "success_guard_note": (
                "these are hierarchy-score paths only. Nothing here speaks to "
                "success-guard power or to the absence of a useful "
                "variance-adaptive method for the success gate."),
        },
        "rows": rows,
        "provenance": {
            "diagnostic_module_sha256": _sha(HERE / "eb_width_diagnostic.py"),
            "corrector_sha256": _sha(HERE / "eb_descriptive_correction.py"),
            "vcompare_sha256": _sha(VALIDATION / "vcompare.py"),
            "cells_json_sha256": _sha(VALIDATION / "cells.json"),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }


def main() -> int:
    report = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report["review_witness_C8_n2000"], indent=2))
    rec = report["reconciliation_against_the_preserved_receipt"]
    print(f"reconciled {rec['checked']} saved values, "
          f"{len(rec['mismatches'])} mismatches")
    print(f"wrote {OUT}")
    return 0 if rec["all_preserved_values_reproduce"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
