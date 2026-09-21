"""PAIRED analysis of the matched certificate ablation, exactly as root specified.

Root handoff, 2026-09-21 16:25:

    "Root specifies paired trial indicators D = original-deploy minus
     disabled-deploy; estimate meanD and its Monte Carlo uncertainty from the
     paired variance.  For the change in A-minus-N contrast, combine the
     independent cell-specific paired variances.  Retain all four joint
     first-decision categories and times: per-look enclosure nesting does not
     prove universal first-decision-label monotonicity when deploy and retain
     compete.  Report capped timing separately from decision-conditional timing
     and preserve inherited original-panel provenance limitations.  A null
     mechanism contrast is acceptable."

WHY PAIRED AND NOT TWO-SAMPLE
-----------------------------
The two arms are the SAME 32,000 trials -- same namespace-3 seeds, draws, reveal
ticks and enrollment -- re-evaluated under two operators.  A two-sample interval
would throw away the pairing and describe an independence that does not hold.
The paired variance is the variance of the per-trial difference, and it is the
only honest uncertainty here.

WHAT "UNCERTAINTY" MEANS IN THIS FILE
------------------------------------
MONTE CARLO uncertainty over this panel's own finite draws.  Not a confidence
statement about agent systems, about informative delay in general, or about any
population outside this fixed synthetic replay design.  Every interval below is
a normal approximation on a bounded three-valued difference; at these counts that
is adequate for reading the sign and rough magnitude and is not a coverage claim.

TWO ASYMMETRIES THAT ARE NOT SYMMETRIC
--------------------------------------
1. Deploy and retain COMPETE as stopping labels.  Widening the ADAPTER enclosure
   can remove a deploy opportunity AND a retain opportunity at the same look, so
   an original early retain can precede a later deploy opportunity the wider
   variant reaches.  The first-decision LABEL is therefore not provably monotone
   even though the per-look enclosures nest.  The full 4x4 joint table is kept
   for this reason, not for completeness.
2. Timing conditional on deciding is conditioned ON THE OUTCOME.  The set of
   trials that decide in both arms is selected by the thing being measured, so
   the decision-conditional difference is descriptive only.  The capped reading,
   which keeps every trial and assigns non-deciders the finalization tick, is
   reported separately and is the one that carries the whole panel.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

REPO = HERE.parents[1]
ORIGINAL_ROOT = REPO / "results" / "live_ab_validation_v2" / "powercurve_20260921"
DISABLED_ROOT = (REPO / "results" / "live_ab_validation_v2" / "ablation_20260921"
                 / "disabled_arm")

CELLS = ("P05N", "P05A", "P10N", "P10A")
#: The four decision labels the writer actually emits.  There is no bare
#: "RETAIN": a lookup for that name silently matched nothing once already, and
#: 29 retention events went unseen because of it.
LABELS = ("NO_DECISION", "DEPLOY", "RETAIN_INCUMBENT", "CONFLICT")
Z95 = 1.959963984540054
FINALIZATION_TICK = 2200
HORIZON = 2000


def _load_adapter(root: Path, cell: str) -> Dict[Tuple[int, int], Dict[str, str]]:
    """Every ADAPTER row for one cell, keyed by (program, trial)."""
    rows: Dict[Tuple[int, int], Dict[str, str]] = {}
    shards = sorted(root.glob(f"shard_*_{cell}-p*"))
    if not shards:
        raise FileNotFoundError(f"no shards for {cell} under {root}")
    for shard in shards:
        with gzip.open(shard / "primary_rows.csv.gz", "rt") as fh:
            for row in csv.DictReader(fh):
                if row["construction"] != "ADAPTER":
                    continue
                key = (int(row["program"]), int(row["trial"]))
                if key in rows:
                    raise ValueError(f"{cell} {key} appears twice under {root}")
                rows[key] = row
    return rows


def _mc(values: np.ndarray) -> Dict[str, float]:
    """Mean and its Monte Carlo standard error, with a normal 95% interval."""
    v = np.asarray(values, dtype=np.float64)
    n = int(v.size)
    mean = float(v.mean())
    sd = float(v.std(ddof=1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n else float("nan")
    return {"n": n, "mean": mean, "sd": sd, "mc_se": se,
            "ci95_lo": mean - Z95 * se, "ci95_hi": mean + Z95 * se}


def _combine(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    """Difference of two INDEPENDENT cell estimates, variances added.

    P05N and P05A carry different cell indices, hence different spawn keys and
    disjoint draws; the same holds for the P10 pair.  So the delay arms are
    independent and their paired variances combine additively.  The pairing is
    WITHIN a cell, across arms -- never across cells.
    """
    diff = a["mean"] - b["mean"]
    se = math.sqrt(a["mc_se"] ** 2 + b["mc_se"] ** 2)
    return {"difference": diff, "mc_se": se,
            "ci95_lo": diff - Z95 * se, "ci95_hi": diff + Z95 * se}


def analyse_cell(cell: str, original_root: Path = ORIGINAL_ROOT,
                 disabled_root: Path = DISABLED_ROOT) -> Dict[str, Any]:
    orig = _load_adapter(original_root, cell)
    dis = _load_adapter(disabled_root, cell)
    if set(orig) != set(dis):
        only_o = sorted(set(orig) - set(dis))[:3]
        only_d = sorted(set(dis) - set(orig))[:3]
        raise ValueError(
            f"{cell}: the two arms do not cover the same coordinates "
            f"(original-only e.g. {only_o}, disabled-only e.g. {only_d}); "
            f"the pairing is void")
    keys = sorted(orig)

    lab_o = np.array([orig[k]["decision"] for k in keys])
    lab_d = np.array([dis[k]["decision"] for k in keys])
    unknown = sorted((set(lab_o) | set(lab_d)) - set(LABELS))
    if unknown:
        raise ValueError(f"{cell}: unrecognised decision labels {unknown}")

    dep_o = (lab_o == "DEPLOY").astype(np.float64)
    dep_d = (lab_d == "DEPLOY").astype(np.float64)
    d_paired = dep_o - dep_d

    tick_o = np.array([int(orig[k]["tau_tick"]) for k in keys], dtype=np.float64)
    tick_d = np.array([int(dis[k]["tau_tick"]) for k in keys], dtype=np.float64)
    pre_o = np.array([int(orig[k]["tau_prefix"]) for k in keys], dtype=np.float64)
    pre_d = np.array([int(dis[k]["tau_prefix"]) for k in keys], dtype=np.float64)

    decided_both = (lab_o != "NO_DECISION") & (lab_d != "NO_DECISION")

    joint: Dict[str, int] = {}
    for a in LABELS:
        for b in LABELS:
            c = int(np.count_nonzero((lab_o == a) & (lab_d == b)))
            if c:
                joint[f"original={a} -> disabled={b}"] = c

    # PROTOCOL 9.2 false_harm: RETAIN_INCUMBENT while mu_h >= 0.  Every cell on
    # this ladder has mu_h > 0, so a retention here IS the frozen error event.
    harm_o = int(np.count_nonzero(lab_o == "RETAIN_INCUMBENT"))
    harm_d = int(np.count_nonzero(lab_d == "RETAIN_INCUMBENT"))

    return {
        "cell": cell,
        "paired_trials": len(keys),
        "deploy_rate_original": _mc(dep_o),
        "deploy_rate_disabled": _mc(dep_d),
        "paired_difference_original_minus_disabled": _mc(d_paired),
        "discordant_pairs": {
            "deploy_only_original": int(np.count_nonzero(d_paired > 0)),
            "deploy_only_disabled": int(np.count_nonzero(d_paired < 0)),
            "concordant": int(np.count_nonzero(d_paired == 0))},
        "joint_first_decision_categories": joint,
        "false_harm_events_protocol_9_2": {
            "original": harm_o, "disabled": harm_d,
            "definition": "RETAIN_INCUMBENT while mu_h >= 0; mu_h > 0 in every "
                          "cell of this ladder"},
        "timing_capped_all_trials": {
            "note": ("every trial retained; a non-decider carries tau_tick = "
                     f"{FINALIZATION_TICK} and tau_prefix = {HORIZON} by the "
                     "capped-decision rule, so this reading is driven by the "
                     "decision RATE as much as by decision speed"),
            "tau_tick_original": _mc(tick_o),
            "tau_tick_disabled": _mc(tick_d),
            "tau_tick_paired_difference": _mc(tick_o - tick_d),
            "tau_prefix_paired_difference": _mc(pre_o - pre_d)},
        "timing_decision_conditional": {
            "note": ("restricted to trials that decided in BOTH arms. This set "
                     "is SELECTED ON THE OUTCOME under test, so the reading is "
                     "descriptive and its interval is not a coverage statement"),
            "trials_deciding_in_both_arms": int(decided_both.sum()),
            "tau_tick_paired_difference":
                _mc(tick_o[decided_both] - tick_d[decided_both])
                if decided_both.any() else None,
            "tau_prefix_paired_difference":
                _mc(pre_o[decided_both] - pre_d[decided_both])
                if decided_both.any() else None},
    }


def analyse(original_root: Path = ORIGINAL_ROOT,
            disabled_root: Path = DISABLED_ROOT) -> Dict[str, Any]:
    cells = {c: analyse_cell(c, original_root, disabled_root) for c in CELLS}

    contrasts: Dict[str, Any] = {}
    for mu, n_cell, a_cell in (("0.05", "P05N", "P05A"), ("0.10", "P10N", "P10A")):
        dn = cells[n_cell]["paired_difference_original_minus_disabled"]
        da = cells[a_cell]["paired_difference_original_minus_disabled"]
        contrasts[f"mu_h={mu}"] = {
            "change_in_A_minus_N_deploy_contrast": _combine(da, dn),
            "reading": ("how much of the informative-minus-non-informative "
                        "deployment gap is removed when the two elapsed-cost "
                        "certificate branches are disabled"),
            "A_minus_N_original": _combine(
                cells[a_cell]["deploy_rate_original"],
                cells[n_cell]["deploy_rate_original"]),
            "A_minus_N_disabled": _combine(
                cells[a_cell]["deploy_rate_disabled"],
                cells[n_cell]["deploy_rate_disabled"]),
            "independence": ("P05N/P05A and P10N/P10A carry different cell "
                             "indices, hence different spawn keys and disjoint "
                             "draws, so the cell-specific paired variances add"),
        }

    return {
        "schema": "live_ab_validation_v2.certificate_ablation_analysis.1",
        "label": ("POST-HOC EXPLORATORY MECHANISM ANALYSIS, selected after the "
                  "reported informative-delay gap. Not a prospectively specified "
                  "study. Every number below is DESIGN-BASED MONTE CARLO over "
                  "this panel's own finite draws."),
        "cells": cells,
        "contrasts": contrasts,
        "inherited_provenance_limitations": [
            "The original arm's records come from the coarse power-curve panel, "
            "whose provenance qualifications carry over unchanged to every "
            "comparison here; this analysis repairs none of them.",
            "The coarse panel is namespace 3 and its own law family. Nothing "
            "here may be pooled with the namespace-0 T1 calibration panel or "
            "with the namespace-4 fine ladder.",
            "The disabled arm re-evaluates THE SAME draws. Its rows are not an "
            "independent sample and must never be pooled with the original "
            "arm's to form a larger panel.",
            "vpins.entry_point_pins gained `variant` and `law_weights` keys for "
            "this run, so its `receipt` aggregate is not comparable with "
            "receipts written before 2026-09-21; the source files it digests "
            "are unchanged in meaning.",
        ],
        "must_not_claim": [
            "that cost narrowing explains every ADAPTER difference between the "
            "informative and non-informative delay arms",
            "that any result here generalises beyond this fixed synthetic replay "
            "design to informative-delay systems at large",
            "that a difference, or the absence of one, was prospectively "
            "predicted -- the ablation was selected after the gap was reported",
            "that the paired intervals are coverage statements; they are Monte "
            "Carlo uncertainty over this panel's finite draws",
            "that the decision-conditional timing reading is anything but "
            "descriptive: its conditioning set is selected on the outcome",
            "that a null contrast refutes the mechanism, or that a non-null one "
            "establishes it outside these four coordinates",
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", type=Path, default=ORIGINAL_ROOT)
    ap.add_argument("--disabled", type=Path, default=DISABLED_ROOT)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    result = analyse(a.original, a.disabled)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.out:
        a.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
