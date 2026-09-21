#!/usr/bin/env python3
"""vtotalguard.py -- exercise and DEMONSTRATE the fail-closed total-workload guard.

The root's requirement is not that a guard exists but that it REFUSES.  A gate
that has never fired is not known to be a gate, so this script fires it, on
purpose, in every way it can fire, and records what happened.

WHAT IT DOES

  1. Rebuilds the smoke record from the ACCEPTED COMMITTED primary resource
     receipt.  No clock is read: every second here is a previously accepted
     measurement re-expressed, exactly as the saved projection was.
  2. Runs the unchanged frozen primary selection, so the scientific tier choice
     is visible beside the guard and is seen not to move.
  3. Runs the SEPARATE total-workload guard on the declared two-score reference
     workload (eight calls per program) and records its verdict.
  4. TRIPS the guard three ways -- unresolved cost, over-cap total with an
     admissible primary, and no selected tier -- and in each case calls
     ``enforce_total_workload_guard`` and records that it RAISED, with the
     exact message.  An unraised case is itself recorded as a FAILURE of the
     demonstration.

CPU only.  No model call, no network, no timing.  Writes one JSON under
``results/live_ab_validation_v2/`` and nothing else.
"""
from __future__ import annotations

import copy
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vrun                                                      # noqa: E402

#: the accepted committed receipt the saved projection was built from
COMMITTED = (REPO_ROOT / "results" / "live_ab_validation_v2"
             / "resource_check_committed" / "balanced_analysis.json")
SAVED_PROJECTION = (REPO_ROOT / "results" / "live_ab_validation_v2"
                    / "budget_projection_repaired.json")
#: v1's demonstration is COMMITTED and is left exactly where it is.  Guard
#: v2 writes its own file rather than re-running into a deposited receipt --
#: the rule adopted after I clobbered one by doing precisely that.
OUT = (REPO_ROOT / "results" / "live_ab_validation_v2"
       / "total_workload_guard_demonstration_v2.json")
OUT_V1 = (REPO_ROOT / "results" / "live_ab_validation_v2"
          / "total_workload_guard_demonstration.json")

#: A fully bound proposal, used ONLY as the positive control: it shows the
#: strengthened guard can still authorize, so its refusals mean something.
CONTROL_IDENTITIES = {"code": "control", "config": "control",
                      "policy": "operational", "workload": "eight_call",
                      "receipt": "control"}


def smoke_from_saved_projection() -> Dict[str, Any]:
    """Rebuild the balanced smoke record from the saved accepted aggregation."""
    saved = json.loads(SAVED_PROJECTION.read_text())
    agg = saved["horizon_aggregation"]["by_horizon"]
    points: List[Dict[str, Any]] = []
    programs_total = 0
    for h_str, slot in sorted(agg.items(), key=lambda kv: int(kv[0])):
        for cell, rec in sorted(slot["cells"].items()):
            points.append({
                "cell": cell, "N_max": int(h_str),
                "programs": int(rec["programs"]),
                "seconds": float(rec["seconds"]),
                "seconds_per_program": float(rec["seconds_per_program"]),
                "record_bytes_measured_not_written":
                    int(rec["record_bytes_measured_not_written"]),
            })
            programs_total += int(rec["programs"])
    return {
        "balanced": True,
        "points": points,
        "total_programs": programs_total,
        "peak_rss_bytes": 96 * 2 ** 20,
        "source": ("rebuilt from the saved accepted aggregation; no clock was "
                   "read to produce it"),
    }


def _trip(name: str, budget: Dict[str, Any], cfg_json: dict,
          mutate, proposed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Trip the guard one way and record whether it actually REFUSED."""
    b = copy.deepcopy(budget)
    mutate(b)
    verdict = vrun.total_workload_guard(b, cfg_json, proposed)
    raised: str = ""
    try:
        vrun.enforce_total_workload_guard(verdict)
    except vrun.TotalResourceRefusal as exc:
        raised = str(exc)
    return {
        "case": name,
        "authorized": bool(verdict.get("authorized")),
        "refusal_class": verdict.get("refusal_class"),
        "total_seconds_projected": verdict.get("total_seconds_projected"),
        "primary_only_admissible": verdict.get("primary_only_admissible"),
        "enforcement_raised": bool(raised),
        "exception_message": raised,
        "demonstration_result": (
            "PASS: the guard refused and execution could not proceed"
            if raised and not verdict.get("authorized") else
            "FAIL: the guard did not refuse"),
    }


def run() -> Dict[str, Any]:
    cfg_json = json.loads((HERE / "cells.json").read_text())
    smoke = smoke_from_saved_projection()
    budget = vrun.select_tier(smoke, cfg_json)
    verdict = vrun.total_workload_guard(budget, cfg_json)

    authorized_path: Dict[str, Any] = {"case": "as_projected", "verdict": verdict}
    try:
        vrun.enforce_total_workload_guard(verdict)
        authorized_path["enforcement_raised"] = False
    except vrun.TotalResourceRefusal as exc:
        authorized_path["enforcement_raised"] = True
        authorized_path["exception_message"] = str(exc)

    cap = float(cfg_json["budget"]["hard_limits"]["seconds"])

    def _unresolved(b: Dict[str, Any]) -> None:
        for e in b["ladder"]:
            e["reference_seconds_projected"] = None
            e["total_seconds_projected"] = None
            e["reference_cost_unresolved"] = True
            e["reference_cost_note"] = ("receipt absent on this host; "
                                        "UNRESOLVED, not zero")

    def _over_cap(b: Dict[str, Any]) -> None:
        for e in b["ladder"]:
            # leave the PRIMARY projection and its admissibility untouched, so
            # the demonstration shows a primary-admissible tier refused on the
            # TOTAL alone
            e["reference_seconds_projected"] = cap * 2.0
            e["total_seconds_projected"] = e["seconds_projected"] + cap * 2.0
            e["reference_cost_unresolved"] = False

    def _no_tier(b: Dict[str, Any]) -> None:
        b["selected_tier"] = None
        b["paused"] = True

    # ---- the four failures root NAMED as still authorizing under v1 -------
    def _nan_reference(b: Dict[str, Any]) -> None:
        for e in b["ladder"]:
            e["reference_seconds_projected"] = float("nan")
            e["total_seconds_projected"] = float("nan")

    def _negative_reference(b: Dict[str, Any]) -> None:
        for e in b["ladder"]:
            e["reference_seconds_projected"] = -1.0e9
            e["total_seconds_projected"] = -1.0e9

    def _huge_bytes(b: Dict[str, Any]) -> None:
        for e in b["ladder"]:
            e["bytes_projected"] = 1.0e12

    def _huge_rss(b: Dict[str, Any]) -> None:
        for e in b["ladder"]:
            e["peak_rss_projected"] = 1.0e12

    def _no_combined_receipt(b: Dict[str, Any]) -> None:
        ref = dict(b["reference_workload"])
        ref["combined_workload_receipt"] = {"present": False}
        b["reference_workload"] = ref

    def _bind(b: Dict[str, Any], **over) -> None:
        ref = dict(b["reference_workload"])
        c = dict(ref.get("combined_workload_receipt") or {})
        c["present"] = True
        c["identities"] = dict(CONTROL_IDENTITIES)
        c.setdefault("planned_groups", 12)
        c["groups_total"] = over.get("groups_total", 12)
        ref["combined_workload_receipt"] = c
        b["reference_workload"] = ref

    def _short_groups(b: Dict[str, Any]) -> None:
        _bind(b, groups_total=5)

    bound = {"identities": dict(CONTROL_IDENTITIES)}
    cases = [
        _trip("unresolved_reference_cost", budget, cfg_json, _unresolved),
        _trip("total_over_cap_with_admissible_primary", budget, cfg_json,
              _over_cap),
        _trip("no_tier_selected", budget, cfg_json, _no_tier),
        # --- newly closed in v2 -------------------------------------------
        _trip("nan_reference_time", budget, cfg_json, _nan_reference, bound),
        _trip("negative_reference_time", budget, cfg_json, _negative_reference,
              bound),
        _trip("excessive_output_bytes", budget, cfg_json, _huge_bytes, bound),
        _trip("excessive_peak_rss", budget, cfg_json, _huge_rss, bound),
        _trip("missing_combined_receipt", budget, cfg_json, _no_combined_receipt,
              bound),
        _trip("identity_mismatch_on_policy", budget, cfg_json, _bind,
              {"identities": dict(CONTROL_IDENTITIES, policy="oracle")}),
        _trip("identities_absent_entirely", budget, cfg_json, _bind, {}),
        _trip("group_accounting_short", budget, cfg_json, _short_groups, bound),
        _trip("proposal_larger_than_priced_tier", budget, cfg_json, _bind,
              dict(bound, programs_total=280000)),
    ]
    all_refused = all(c["enforcement_raised"] and not c["authorized"]
                      for c in cases)

    # ---- the two independent routes to the reference cost, side by side ----
    ref = budget["reference_workload"]
    combined = ref.get("combined_workload_receipt") or {}
    reconciliation: Dict[str, Any] = {
        "route_a_scaled_arithmetic": {
            "what": ("the H-only reference receipt (4 calls/program) scaled by "
                     "the declared score count to the frozen 8-call workload"),
            "is_a_measurement": False,
            "seconds_per_program_by_horizon": {
                h: slot.get("seconds_per_program_scaled_arithmetic",
                            slot.get("seconds_per_program"))
                for h, slot in (ref.get("seconds_per_program_by_horizon")
                                or {}).items()},
            "seconds_per_program_measured_h_only_by_horizon": {
                h: slot.get("seconds_per_program_measured_h_only")
                for h, slot in (ref.get("seconds_per_program_by_horizon")
                                or {}).items()},
        },
        "route_b_measured_missing_scope": {
            "what": ("the contemporaneously measured COMBINED workload minus "
                     "the contemporaneously measured primary-only scope, on "
                     "the authorized 20-unit design. That difference is the "
                     "reference-attributable share, which is the same object "
                     "route A estimates."),
            "is_a_measurement": True,
            "present": bool(combined.get("present")),
            "missing_scope_seconds_per_program_by_horizon": {
                h: slot.get("missing_scope_seconds_per_program")
                for h, slot in (combined.get("seconds_per_program_by_horizon")
                                or {}).items()},
            "whole_combined_seconds_per_program_by_horizon": {
                h: slot.get("combined_seconds_per_program")
                for h, slot in (combined.get("seconds_per_program_by_horizon")
                                or {}).items()},
            "attempts_total": combined.get("attempts_total"),
            "attempts_failed": combined.get("attempts_failed"),
        },
        "route_reconciliation": ref.get("reference_cost_route_reconciliation"),
        "which_the_guard_used": (
            "the LARGER of the two at each horizon, per the resource rule in "
            "reference_workload_costs. The two routes do NOT agree exactly and "
            "neither dominates: the measured missing scope is the larger at "
            "horizon 1,000 and the scaled arithmetic is the larger at horizon "
            "2,000. Both are retained; nothing is discarded."),
        "the_withdrawn_91_2_percent": (
            "NOT reused, NOT reproduced and NOT repaired here. It was "
            "conditional arithmetic on a weak one-score receipt and it does "
            "not carry into a two-score workload."),
    }

    ladder_view = [
        {"tier": e["tier"], "programs_total": e["programs_total"],
         "N_max": e["N_max"],
         "primary_seconds_projected": e["seconds_projected"],
         "primary_admissible": e["admissible"],
         "reference_seconds_projected": e.get("reference_seconds_projected"),
         "total_seconds_projected": e.get("total_seconds_projected"),
         "reference_share_of_total": e.get("reference_share_of_total")}
        for e in budget["ladder"]]

    return {
        "schema": "live_ab_validation_v2.total_workload_guard.demonstration.1",
        "what_this_is": (
            "A demonstration that the separate total-workload resource guard "
            "actually REFUSES. Seconds are re-expressions of the accepted "
            "committed receipt; no clock was read here."),
        "what_this_is_not": (
            "not a resource clearance, not a calibration, not a measurement, "
            "and not an authorization of any grid"),
        "frozen_reference_workload": dict(vrun.REFERENCE_WORKLOAD),
        "amendment": dict(vrun.REFERENCE_WORKLOAD_AMENDMENT),
        "hard_limits": cfg_json["budget"]["hard_limits"],
        "frozen_primary_selection_unchanged": {
            "selected_tier": budget["selected_tier"],
            "paused": budget["paused"],
            "selection_rule": budget["selection_rule"],
            "note": ("this is the frozen scientific rule and it reads the "
                     "PRIMARY projection only; the guard below does not move "
                     "it"),
        },
        "ladder_with_declared_two_score_reference": ladder_view,
        "reference_cost_routes": reconciliation,
        "guard_verdict_as_projected": authorized_path,
        "tripped_cases": cases,
        "every_tripped_case_refused": all_refused,
        "demonstration_result": ("PASS: every way of tripping the guard "
                                 "refused and raised"
                                 if all_refused else
                                 "FAIL: at least one tripped case proceeded"),
        "provenance": {
            "vrun_sha256": vrun.sha256_file(HERE / "vrun.py"),
            "cells_json_sha256": vrun.sha256_file(HERE / "cells.json"),
            "committed_receipt": str(COMMITTED.relative_to(REPO_ROOT)),
            "committed_receipt_sha256": (vrun.sha256_file(COMMITTED)
                                         if COMMITTED.is_file() else None),
            "saved_projection": str(SAVED_PROJECTION.relative_to(REPO_ROOT)),
            "saved_projection_sha256": vrun.sha256_file(SAVED_PROJECTION),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }


def main() -> int:
    report = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({
        "selected_tier_on_primary_only":
            report["frozen_primary_selection_unchanged"]["selected_tier"],
        "guard_as_projected_authorized":
            report["guard_verdict_as_projected"]["verdict"]["authorized"],
        "guard_as_projected_total_seconds":
            report["guard_verdict_as_projected"]["verdict"].get(
                "total_seconds_projected"),
        "tripped": [{c["case"]: c["demonstration_result"]}
                    for c in report["tripped_cases"]],
        "demonstration_result": report["demonstration_result"],
    }, indent=2))
    for c in report["tripped_cases"]:
        print(f"\n--- {c['case']} ---\n{c['exception_message']}")
    print(f"\nwrote {OUT}")
    return 0 if report["every_tripped_case_refused"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
