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

WHAT THIS PANEL CANNOT DO
  The grid has mu_h in {0, 0.40, 0.45} and mu_s in {0, 0.25, -0.03, 0.20}.  There is NO
  cell with mu_h strictly between 0 and 0.40 and none with mu_s strictly between -0.03
  and +0.20, so there is no partially-powered operating point anywhere.  No power curve
  and no minimum detectable effect are estimable from it.  That is a limitation of the
  grid I specified, and it is reported rather than worked around.

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
    """Ground truth per cell, and what a DEPLOY there means."""
    out = {}
    for c in vgen.CELLS:
        delta = vband.DELTA
        # The guarded rule deploys iff the hierarchy lower bound is positive AND the
        # success lower bound exceeds -delta.  A deploy is an ERROR when the true
        # hierarchy effect is not positive, and it is a GUARDRAIL BREACH when the true
        # success effect is at or below -delta.
        hier_null = (c.mu_h <= 0.0)
        guard_at_or_past = (c.mu_s <= -delta)
        if hier_null and c.mu_s == 0.0 and c.mu_h == 0.0:
            kind = "TRUE NULL"
        elif hier_null:
            kind = "hierarchy null"
        elif guard_at_or_past:
            kind = "guardrail boundary"
        else:
            kind = "favourable alternative"
        out[c.id] = {
            "law": vgen.LAW_NAMES[c.law], "delay": c.delay,
            "delay_kind": "informative" if c.delay == "A" else "non-informative",
            "mu_h": c.mu_h, "mu_s": c.mu_s, "kind": kind,
            "deploy_is_error": hier_null,
            "deploy_is_guardrail_breach": guard_at_or_past,
        }
    return out


def load(run_dir: Path) -> Tuple[Dict, Dict, List[str]]:
    """Frozen set: only shards whose receipt reconciles. Partials are excluded by
    ABSENCE OF A RECEIPT, never by swallowing a read error."""
    run_dir = Path(run_dir)
    shards = []
    for d in sorted(run_dir.glob("shard_*")):
        rp = d / "COMPLETED_SHARD_RECEIPT.json"
        if not rp.is_file():
            continue
        r = json.loads(rp.read_text())
        if r.get("status") != "complete":
            continue
        a = r["attempt_counts"]
        if a["failed"] or a["skipped"] or a["missing"]:
            continue
        if r["planned"] != r["observed"]:
            continue
        shards.append((d, r))

    # trial-level decisions, and program-level union events
    trial = defaultdict(lambda: defaultdict(int))          # (cell,constr) -> decision -> n
    prog_any_deploy = defaultdict(set)                     # (cell,constr) -> {program}
    prog_seen = defaultdict(set)
    miscover = defaultdict(lambda: defaultdict(int))       # (cell,constr) -> field -> n
    ntrial = defaultdict(int)
    for d, _r in shards:
        with gzip.open(d / "primary_rows.csv.gz", "rt") as fh:
            head = fh.readline().rstrip("\n").split(",")
            ix = {k: i for i, k in enumerate(head)}
            for line in fh:
                f = line.rstrip("\n").split(",")
                cell, con, dec = f[ix["cell"]], f[ix["construction"]], f[ix["decision"]]
                prog = int(f[ix["program"]])
                key = (cell, con)
                trial[key][dec] += 1
                ntrial[key] += 1
                prog_seen[key].add(prog)
                if dec == "DEPLOY":
                    prog_any_deploy[key].add(prog)
                for fld in ("ever_miscover_h", "ever_miscover_s",
                            "ever_miscover_h_decision_eligible",
                            "ever_miscover_s_decision_eligible"):
                    if f[ix[fld]] not in ("0", ""):
                        miscover[key][fld] += 1
    return ({"trial": trial, "ntrial": ntrial, "prog_any_deploy": prog_any_deploy,
             "prog_seen": prog_seen, "miscover": miscover},
            {d.name: r for d, r in shards}, [d.name for d, _ in shards])


def analyse(run_dir: Path) -> Dict[str, Any]:
    agg, receipts, names = load(run_dir)
    truth = cell_truth()
    cells = sorted({k[0] for k in agg["ntrial"]})
    delta = vband.DELTA

    rows = []
    for cell in cells:
        for con in CONSTRUCTIONS:
            key = (cell, con)
            n_t = agg["ntrial"].get(key, 0)
            if not n_t:
                continue
            t = agg["trial"][key]
            n_p = len(agg["prog_seen"][key])
            k_p = len(agg["prog_any_deploy"][key])
            lo, hi = wilson(k_p, n_p)
            rows.append({
                "cell": cell, "construction": con, **{k: truth[cell][k] for k in
                    ("law", "delay_kind", "mu_h", "mu_s", "kind",
                     "deploy_is_error", "deploy_is_guardrail_breach")},
                "trials": n_t, "programs": n_p,
                "trial_deploy": t.get("DEPLOY", 0),
                "trial_retain": t.get("RETAIN", 0),
                "trial_no_decision": t.get("NO_DECISION", 0),
                "trial_abstention_rate": t.get("NO_DECISION", 0) / n_t,
                "program_any_deploy": k_p,
                "program_deploy_rate": k_p / n_p,
                "program_deploy_wilson95": [lo, hi],
                "miscover_h": agg["miscover"][key].get("ever_miscover_h", 0),
                "miscover_s": agg["miscover"][key].get("ever_miscover_s", 0),
                "miscover_h_eligible":
                    agg["miscover"][key].get("ever_miscover_h_decision_eligible", 0),
                "miscover_s_eligible":
                    agg["miscover"][key].get("ever_miscover_s_decision_eligible", 0),
            })

    def rate(cell, con):
        for r in rows:
            if r["cell"] == cell and r["construction"] == con:
                return r
        return None

    # The headline contrast: informative delay, hierarchy null.
    contrasts = []
    for cell in cells:
        if truth[cell]["delay_kind"] != "informative" or not truth[cell]["deploy_is_error"]:
            continue
        a, nv = rate(cell, "ADAPTER"), rate(cell, "NAIVE")
        if a and nv:
            contrasts.append({
                "cell": cell, "kind": truth[cell]["kind"],
                "adapter_program_deploy_rate": a["program_deploy_rate"],
                "adapter_wilson95": a["program_deploy_wilson95"],
                "naive_program_deploy_rate": nv["program_deploy_rate"],
                "naive_wilson95": nv["program_deploy_wilson95"],
                "note": ("both are FALSE CERTIFICATION rates: the true hierarchy "
                         "effect is not positive in this cell"),
            })

    guardrail = [r for r in rows
                 if r["deploy_is_guardrail_breach"] and r["construction"] == "ADAPTER"]
    power = [r for r in rows
             if r["kind"] == "favourable alternative" and r["construction"] == "ADAPTER"]

    return {
        "schema": "live_ab_validation_v2.t1_analysis.1",
        "run_dir": str(run_dir),
        "shards_analysed": len(names),
        "shards_expected": 56,
        "complete_panel": len(names) == 56,
        "exposure": EXPOSURE,
        "frozen_constants": {"program_alpha": vband.PROGRAM_ALPHA,
                             "alpha_per_trial": vband.ALPHA_PER_TRIAL,
                             "alpha_gate": vband.ALPHA_GATE,
                             "delta": delta},
        "unit_of_replication": {
            "independent_draw": "trial (structural: spawn_key includes trial_index)",
            "reporting_unit": "program (PROGRAM_ALPHA is defined per program)",
            "construction": "WITHIN-trial, paired; never stacked into one denominator",
            "cell": "BETWEEN-unit, unpaired; delay contrasts are unpaired",
        },
        "rows": rows,
        "headline_contrast_informative_delay": contrasts,
        "guardrail_cells": guardrail,
        "power_cells": power,
        "conventions": {
            "program_deploy_rate": "descriptive (observed rate) with design-based Wilson 95% interval",
            "trial_abstention_rate": "descriptive",
            "miscover_*": "descriptive counts of an ever-event over the trial's look sequence",
        },
        "MUST_NOT_CLAIM": [
            "a power curve or minimum detectable effect: the grid has NO partially-powered "
            "operating point (mu_h in {0,0.40,0.45}, nothing between 0 and 0.40)",
            "that the bands are well-calibrated: a 0/1 decision function cannot distinguish "
            "a correctly-targeted band from a correctly-targeted AND vacuously wide one",
            "that this is a fresh confirmatory result: it is replay data with prior exposure",
            "pooling constructions into one denominator, or pooling cells with different truth",
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
