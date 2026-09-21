"""T1 CALIBRATION PANEL ANALYSIS.

Design vetted by a four-lens adversarial review (false certification, coverage,
power/abstention, controls) before any number was computed.  The binding points it
established, each implemented here:

UNIT OF REPLICATION
  The TRIAL is the independent draw: ``vgen.stream`` spawns on
  (namespace, cell_index, program_index, trial_index) and no program-level latent is
  drawn, so intra-program correlation is zero BY CONSTRUCTION, not by measurement.
  The PROGRAM is the reporting unit, because ``PROGRAM_ALPHA = 0.05`` is defined per
  program and the family event is ``.any()`` over that program's 4 trials.  A
  program-level union event must be compared against a program-level threshold.

  CONSTRUCTION is a WITHIN-trial factor: ADAPTER, CPREFIX and NAIVE are built from ONE
  TrialDraw.  They are paired, and stacking them into a common denominator is
  prohibited.  CELL is BETWEEN-unit and unpaired, so delay contrasts (C1/C2, C3/C4,
  C5/C6, C7/C8) are unpaired and McNemar is prohibited.

WHAT THIS PANEL CANNOT DO -- NARROWED AFTER REVIEW
  This FINITE GRID does not identify a power curve or a minimum detectable effect at a
  prespecified target power.  It CAN estimate cell-specific correct-deployment and
  abstention probabilities with Monte Carlo uncertainty.

  My first version claimed more: that NO partially-powered operating point EXISTS,
  inferred from the spacing of mu_h alone.  That does not follow.  Detection probability
  also depends on the joint outcome law, variance, delay, guardrail effect, horizon and
  the conservative boundary width, so a nonzero fixed effect can have intermediate power
  at this horizon.  The narrower statement is the supported one.

EXPOSURE
  These are namespace-0 replay coordinates with prior development exposure.  Not a
  fresh confirmatory holdout.  Every table carries it.
"""

from __future__ import annotations

import gzip
import glob
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402

CONSTRUCTIONS = ("ADAPTER", "CPREFIX", "NAIVE")

#: The writer's ACTUAL labels (vrun.DECISION_LABEL).  My first version read
#: "RETAIN", which matches nothing, so 29 real RETAIN_INCUMBENT events vanished
#: and the table showed zero retentions everywhere -- which read like a finding.
DECISION_LABELS = ("NO_DECISION", "DEPLOY", "RETAIN_INCUMBENT", "CONFLICT")
EXPOSURE = ("namespace-0 replay coordinates with PRIOR DEVELOPMENT EXPOSURE; "
            "NOT a fresh confirmatory holdout")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """Wilson score interval.  Correct at k=0 and k=n, where Wald is degenerate."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def cell_truth() -> Dict[str, Dict[str, Any]]:
    """Ground truth per cell and the FROZEN error events of PROTOCOL 9.2.

        false_deploy = DEPLOY           AND NOT(mu_h > 0 AND mu_s > -delta)
        false_harm   = RETAIN_INCUMBENT AND mu_h >= 0
        family_any_erroneous = any over the program's trials of (false_deploy OR false_harm)

    Two corrections from the root's 13:20 review, both of which changed results:

    * ``deploy_is_error`` was HIERARCHY-ONLY, so a deploy in C5/C6 -- where the
      hierarchy truth is +0.40 but the success truth is -0.03, at the guardrail
      -- did not count as an error.  It is one: the full conjunction fails.
    * EVERY law here has mu_h >= 0, so a retention is a false harm in EVERY
      cell, including the favourable ones.  There was no such event in my table
      because of the label bug above.
    """
    out = {}
    delta = vband.DELTA
    for c in vgen.CELLS:
        deploy_correct = (c.mu_h > 0.0) and (c.mu_s > -delta)
        if c.mu_h == 0.0 and c.mu_s == 0.0:
            kind = "TRUE NULL"
        elif c.mu_h <= 0.0:
            kind = "hierarchy null"
        elif c.mu_s <= -delta:
            kind = "guardrail boundary"
        else:
            kind = "favourable alternative"
        out[c.id] = {
            "law": vgen.LAW_NAMES[c.law], "delay": c.delay,
            "delay_kind": "informative" if c.delay == "A" else "non-informative",
            "mu_h": c.mu_h, "mu_s": c.mu_s, "kind": kind,
            "deploy_is_correct": deploy_correct,
            "deploy_is_error": not deploy_correct,          # FULL conjunction
            "deploy_error_reason": (None if deploy_correct else
                                    ("hierarchy not positive" if c.mu_h <= 0.0
                                     else "success guardrail violated")),
            "retain_is_false_harm": (c.mu_h >= 0.0),
        }
    return out


def load(run_dir: Path, truth: Dict[str, Any]) -> Tuple[Dict, List[str]]:
    """Accumulate the FROZEN trial and program events. Partials excluded by absence
    of a receipt, never by swallowing a read error."""
    run_dir = Path(run_dir)
    shards = []
    for d in sorted(run_dir.glob("shard_*")):
        rp = d / "COMPLETED_SHARD_RECEIPT.json"
        if not rp.is_file():
            continue
        r = json.loads(rp.read_text())
        a = r["attempt_counts"]
        if (r.get("status") != "complete" or a["failed"] or a["skipped"]
                or a["missing"] or r["planned"] != r["observed"]):
            continue
        shards.append((d, r))

    A = lambda: defaultdict(int)
    trial_dec = defaultdict(A)          # (cell,con) -> label -> n
    trial_ev = defaultdict(A)           # (cell,con) -> event -> n
    prog_ev = defaultdict(lambda: defaultdict(set))   # (cell,con) -> event -> {prog}
    prog_seen = defaultdict(set)
    ntrial = defaultdict(int)
    timing = defaultdict(list)          # (cell,con) -> [tau_prefix] for DECIDING trials
    frac = defaultdict(A)               # (cell,con) -> field -> running sum

    MIS = ("ever_below_h", "ever_above_h", "ever_miscover_h",
           "ever_below_s", "ever_above_s", "ever_miscover_s",
           "ever_miscover_h_decision_eligible", "ever_miscover_s_decision_eligible")
    FRACS = ("final_unresolved_fraction", "final_unrevealed_fraction",
             "final_cost_collapsed_fraction", "final_cost_narrowed_fraction")

    for d, _r in shards:
        with gzip.open(d / "primary_rows.csv.gz", "rt") as fh:
            ix = {k: i for i, k in enumerate(fh.readline().rstrip("\n").split(","))}
            for line in fh:
                f = line.rstrip("\n").split(",")
                cell, con = f[ix["cell"]], f[ix["construction"]]
                dec, prog = f[ix["decision"]], int(f[ix["program"]])
                key = (cell, con)
                t = truth[cell]
                ntrial[key] += 1
                trial_dec[key][dec] += 1
                prog_seen[key].add(prog)

                # ---- FROZEN EVENTS (PROTOCOL 9.2) --------------------------
                fd = (dec == "DEPLOY") and t["deploy_is_error"]
                fh_ = (dec == "RETAIN_INCUMBENT") and t["retain_is_false_harm"]
                cd = (dec == "DEPLOY") and t["deploy_is_correct"]
                if fd:
                    trial_ev[key]["false_deploy"] += 1
                    prog_ev[key]["false_deploy"].add(prog)
                if fh_:
                    trial_ev[key]["false_harm"] += 1
                    prog_ev[key]["false_harm"].add(prog)
                if fd or fh_:
                    trial_ev[key]["any_error"] += 1
                    prog_ev[key]["family_any_erroneous"].add(prog)
                if cd:
                    trial_ev[key]["correct_deploy"] += 1
                    prog_ev[key]["any_correct_deploy"].add(prog)
                if dec == "DEPLOY":
                    prog_ev[key]["any_deploy"].add(prog)
                if dec == "NO_DECISION":
                    trial_ev[key]["abstain"] += 1

                for m in MIS:
                    if f[ix[m]] not in ("0", ""):
                        trial_ev[key][m] += 1
                if dec != "NO_DECISION":
                    trial_ev[key]["deciding"] += 1
                    try:
                        timing[key].append(int(f[ix["tau_prefix"]]))
                    except (ValueError, KeyError):
                        pass
                    if f[ix["decided_in_drain"]] not in ("0", ""):
                        trial_ev[key]["decided_in_drain"] += 1
                    if f[ix["decided_at_finalization"]] not in ("0", ""):
                        trial_ev[key]["decided_at_finalization"] += 1
                for fl in FRACS:
                    try:
                        frac[key][fl] += float(f[ix[fl]])
                    except (ValueError, KeyError):
                        pass

    return ({"dec": trial_dec, "ev": trial_ev, "prog": prog_ev,
             "prog_seen": prog_seen, "n": ntrial, "timing": timing, "frac": frac},
            [d.name for d, _ in shards])


def _rate(k: int, n: int) -> Dict[str, Any]:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (k / n if n else float("nan")),
            "wilson95": [lo, hi]}


def analyse(run_dir: Path) -> Dict[str, Any]:
    truth = cell_truth()
    agg, names = load(run_dir, truth)
    cells = sorted({k[0] for k in agg["n"]})

    # FROZEN ALERT RULE: flag when the Wilson LOWER limit exceeds the nominal
    # level.  This replaces the ">0.01 star" of my first version, which was
    # neither the frozen rule nor a labelled descriptive threshold.
    nom_trial = vband.ALPHA_PER_TRIAL
    nom_prog = vband.PROGRAM_ALPHA
    nom_band = vband.ALPHA_GATE

    rows, alerts = [], []
    for cell in cells:
        t = truth[cell]
        for con in CONSTRUCTIONS:
            key = (cell, con)
            n = agg["n"].get(key, 0)
            if not n:
                continue
            d, e, P = agg["dec"][key], agg["ev"][key], agg["prog"][key]
            np_ = len(agg["prog_seen"][key])
            tm = agg["timing"][key]
            row = {
                "cell": cell, "construction": con,
                **{k2: t[k2] for k2 in ("law", "delay_kind", "mu_h", "mu_s", "kind",
                                        "deploy_is_correct", "deploy_is_error",
                                        "deploy_error_reason", "retain_is_false_harm")},
                "trials": n, "programs": np_,
                "decisions": {lab: d.get(lab, 0) for lab in DECISION_LABELS},
                "decisions_reconcile": sum(d.get(l, 0) for l in DECISION_LABELS) == n,
                # ---- frozen TRIAL-denominator events ----------------------
                "trial_false_deploy": _rate(e.get("false_deploy", 0), n),
                "trial_false_harm": _rate(e.get("false_harm", 0), n),
                "trial_any_error": _rate(e.get("any_error", 0), n),
                "trial_correct_deploy": _rate(e.get("correct_deploy", 0), n),
                "trial_abstention": _rate(e.get("abstain", 0), n),
                # ---- frozen PROGRAM family event -------------------------
                "program_family_any_erroneous": _rate(len(P["family_any_erroneous"]), np_),
                "program_any_correct_deploy": _rate(len(P["any_correct_deploy"]), np_),
                "program_any_deploy_DESCRIPTIVE": _rate(len(P["any_deploy"]), np_),
                # ---- coverage: two-sided AND directional -----------------
                "miscover_h_twosided": _rate(e.get("ever_miscover_h", 0), n),
                "miscover_h_below": _rate(e.get("ever_below_h", 0), n),
                "miscover_h_above": _rate(e.get("ever_above_h", 0), n),
                "miscover_s_twosided": _rate(e.get("ever_miscover_s", 0), n),
                "miscover_s_below": _rate(e.get("ever_below_s", 0), n),
                "miscover_s_above": _rate(e.get("ever_above_s", 0), n),
                "miscover_h_decision_eligible":
                    _rate(e.get("ever_miscover_h_decision_eligible", 0), n),
                "miscover_s_decision_eligible":
                    _rate(e.get("ever_miscover_s_decision_eligible", 0), n),
                # ---- timing / resolution, with denominators --------------
                "deciding_trials": e.get("deciding", 0),
                "deciding_fraction": e.get("deciding", 0) / n,
                "tau_prefix_median_DECIDING_ONLY": (sorted(tm)[len(tm) // 2] if tm else None),
                "decided_in_drain": e.get("decided_in_drain", 0),
                "decided_at_finalization": e.get("decided_at_finalization", 0),
                "mean_final_unresolved_fraction": agg["frac"][key]["final_unresolved_fraction"] / n,
                "mean_final_cost_narrowed_fraction": agg["frac"][key]["final_cost_narrowed_fraction"] / n,
            }
            rows.append(row)
            for name, nominal, scope in (
                    ("trial_any_error", nom_trial, "trial"),
                    ("program_family_any_erroneous", nom_prog, "program"),
                    ("miscover_h_twosided", nom_band, "band"),
                    ("miscover_s_twosided", nom_band, "band")):
                r = row[name]
                if r["n"] and r["wilson95"][0] > nominal:
                    alerts.append({"cell": cell, "construction": con,
                                   "readout": name, "observed": r["rate"],
                                   "wilson95": r["wilson95"], "nominal": nominal,
                                   "scope": scope,
                                   "rule": "Wilson LOWER limit exceeds the nominal level"})
    return {
        "schema": "live_ab_validation_v2.t1_analysis.2",
        "run_dir": str(run_dir), "shards_analysed": len(names), "shards_expected": 56,
        "provisional_unless_root_accepts_snapshot": True,
        "completeness_note": ("shard count alone is NOT scientific completion; the "
                              "accepted terminal job receipt supplies that"),
        "exposure": EXPOSURE,
        "nominal_levels": {"program": nom_prog, "per_trial": nom_trial, "per_band": nom_band,
                           "delta": vband.DELTA},
        "frozen_event_definitions": {
            "false_deploy": "DEPLOY AND NOT(mu_h > 0 AND mu_s > -delta)",
            "false_harm": "RETAIN_INCUMBENT AND mu_h >= 0",
            "family_any_erroneous": "any over a program's trials of (false_deploy OR false_harm)"},
        "alert_rule": "Wilson LOWER limit exceeds the nominal level; a flag prompts diagnosis and neither a flag nor its absence establishes a theorem",
        "alerts": alerts,
        "rows": rows,
        "MUST_NOT_CLAIM": [
            "a power curve or a minimum detectable effect at a prespecified target power: "
            "this FINITE GRID does not identify one. (Narrowed after review: the earlier "
            "claim that no partially-powered operating point EXISTS did not follow from "
            "effect spacing alone, since detection probability also depends on the joint "
            "outcome law, variance, delay, guardrail effect, horizon and boundary width.)",
            "that the bands are demonstrated well-calibrated by near-boundary decision rates alone",
            "that this is a fresh confirmatory result: replay data with prior exposure",
            "pooling constructions into one denominator, or pooling cells with different truth",
            "that marginal Wilson intervals are simultaneous or anytime-valid",
        ],
    }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    res = analyse(a.run)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")

    t = cell_truth()
    print(f"T1 CALIBRATION PANEL — {res['shards_analysed']}/56 shards"
          f"{'  (COMPLETE)' if res['complete_panel'] else '  (PARTIAL)'}")
    print(f"exposure: {EXPOSURE}")
    print()
    print(f"{'cell':5}{'truth':22}{'delay':16}{'constr':9}"
          f"{'prog deploy':>13}{'rate':>9}   95% Wilson")
    for r in res["rows"]:
        star = " *" if (r["deploy_is_error"] and r["program_deploy_rate"] > 0.01) else ""
        lo, hi = r["program_deploy_wilson95"]
        print(f"{r['cell']:5}{r['kind']:22}{r['delay_kind']:16}{r['construction']:9}"
              f"{r['program_any_deploy']:>6}/{r['programs']:<6}{r['program_deploy_rate']:>9.4f}"
              f"   [{lo:.4f}, {hi:.4f}]{star}")
    print()
    print("HEADLINE — informative delay, hierarchy null (a deploy is a false certification):")
    for c in res["headline_contrast_informative_delay"]:
        print(f"  {c['cell']}: ADAPTER {c['adapter_program_deploy_rate']:.4f}"
              f"  vs  NAIVE {c['naive_program_deploy_rate']:.4f}")
    print()
    print("GUARDRAIL (mu_h favourable, mu_s at/below -delta; ADAPTER must not deploy):")
    for r in res["guardrail_cells"]:
        print(f"  {r['cell']}: {r['program_any_deploy']}/{r['programs']} "
              f"= {r['program_deploy_rate']:.4f}   mu_h={r['mu_h']} mu_s={r['mu_s']}")
    print()
    for m in res["MUST_NOT_CLAIM"]:
        print(f"  MUST NOT CLAIM: {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
