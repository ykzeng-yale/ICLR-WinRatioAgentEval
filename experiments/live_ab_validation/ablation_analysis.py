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
population outside this fixed synthetic replay design.

FOUR ESTIMANDS, EACH WITH ITS OWN LABELLED INTERVAL
---------------------------------------------------
Root, 18:17: "use Wilson marginals, Newcombe independent-cell differences and
paired-variance Monte Carlo intervals for paired contrasts with explicit method
labels.  Different estimands need not share one interval formula."  They do not,
and they are never mixed within a single reported number:

  * PAIRED differences (the headline D, and the change in the A-minus-N
    contrast) use the NORMAL interval on the paired mean.  This is what root
    specified, and D is a bounded three-valued variate over 8,000 pairs.
  * SINGLE-ARM means (``tau_tick_original``, ``tau_tick_disabled``) use the same
    one-sample normal arithmetic but are NOT paired and are NOT contrasts, and
    they now say so.  Sharing the helper is fine; sharing the label was not.
  * MARGINAL deployment proportions use WILSON, because the delivered coarse
    panel reports Wilson for the identical counts and a second interval on the
    same count under a different convention is a defect, not a supplement.
  * The A-minus-N contrast WITHIN one arm, a difference of two INDEPENDENT
    proportions, uses NEWCOMBE's hybrid score, as this project already did for
    the CPREFIX comparison.

Three of these four were mislabelled or misapplied in the first delivered
version of this file.  Corrected after delivery -- two by self-audit, the
single-arm label by root's review.  The headline paired numbers never moved, and
no rerun was required for any of the three.

An alternative approximation is not wrong merely because it differs from this
project's convention.  These labels record WHICH estimator produced a number, so
that two numbers are never compared across conventions by accident.

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
#: The intended coordinate grid of every ablation cell.
EXPECTED_PROGRAMS = 2000
EXPECTED_TRIALS = 4


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


def _mc(values: np.ndarray, kind: str = "paired") -> Dict[str, float]:
    """Sample mean and its Monte Carlo standard error, with a normal 95% interval.

    The arithmetic is the generic one-sample normal interval.  ``kind`` names the
    ESTIMAND so the emitted label describes what was actually averaged.

    CORRECTION, root 2026-09-21 18:17: "Correct the generic sample-mean helper
    label so single-arm timing means are not called paired."  This helper
    hardcoded "normal on the paired mean", which was true of the paired
    differences it was written for and FALSE of ``tau_tick_original`` and
    ``tau_tick_disabled``, which are one arm's own mean over 8,000 trials and
    involve no pairing at all.  The numbers were right; the label was not, and a
    reader could have taken a single-arm mean for a paired contrast.  No rerun
    was needed and none was done.

    ``kind="paired"``   -- a within-cell paired difference; the estimator root
                           specified: "estimate meanD and its Monte Carlo
                           uncertainty from the paired variance."
    ``kind="single_arm"`` -- one arm's own mean; NOT a contrast of any kind.

    Never used for a marginal proportion -- see ``_rate``.
    """
    labels = {
        "paired": "normal on the paired mean (within-cell paired difference)",
        "single_arm": ("normal on a single-arm sample mean; NOT a paired "
                       "quantity and not a contrast"),
    }
    if kind not in labels:
        raise ValueError(f"unknown estimand kind {kind!r}; "
                         f"expected one of {sorted(labels)}")
    v = np.asarray(values, dtype=np.float64)
    n = int(v.size)
    mean = float(v.mean())
    sd = float(v.std(ddof=1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n else float("nan")
    return {"n": n, "mean": mean, "sd": sd, "mc_se": se,
            "ci95_lo": mean - Z95 * se, "ci95_hi": mean + Z95 * se,
            "estimand": kind, "interval_method": labels[kind]}


def _rate(indicator: np.ndarray) -> Dict[str, float]:
    """A marginal deployment proportion, with a WILSON score interval.

    CONVENTION FIX, 2026-09-21 (self-audit, after delivery).  The first version
    of this file put a normal interval on these proportions.  The delivered
    coarse panel reports WILSON for the identical counts -- PC_ANALYSIS.json
    gives [0.0022189, 0.0047579] for P05N's 26/8000 where the normal interval
    gives [0.0020027, 0.0044973].  Publishing a second, different interval on the
    SAME count is exactly the convention-mixing these readouts exist to prevent,
    and at rates this small the normal interval is the wrong one.  The paired
    difference is unaffected and stays on the method root specified.
    """
    from t1_analysis import wilson                             # the panel's own
    k = int(np.count_nonzero(indicator))
    n = int(indicator.size)
    lo, hi = wilson(k, n)
    return {"n": n, "events": k, "mean": k / n if n else float("nan"),
            "ci95_lo": lo, "ci95_hi": hi,
            "interval_method": "Wilson score, matching PC_ANALYSIS.json"}


def _newcombe(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    """Difference of two INDEPENDENT proportions, Newcombe's hybrid-score method.

    Used for the A-minus-N contrast WITHIN one arm, where the two cells are
    independent samples: P05N/P05A and P10N/P10A carry different cell indices,
    hence different spawn keys and disjoint draws.  Newcombe rather than a normal
    combination, for the same reason and with the same authority as ``_rate``:
    it is the method this project already used for the CPREFIX comparison.
    """
    d = a["mean"] - b["mean"]
    lo = d - math.sqrt((a["mean"] - a["ci95_lo"]) ** 2 + (b["ci95_hi"] - b["mean"]) ** 2)
    hi = d + math.sqrt((a["ci95_hi"] - a["mean"]) ** 2 + (b["mean"] - b["ci95_lo"]) ** 2)
    return {"difference": d, "ci95_lo": lo, "ci95_hi": hi,
            "interval_method": "Newcombe hybrid score, independent cells"}


def _combine(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    """Difference of two INDEPENDENT PAIRED means, variances added.

    This is the estimator root specified for the change in the A-minus-N
    contrast: "For the change in A-minus-N contrast, combine the independent
    cell-specific paired variances."  Both inputs must be ``_mc`` results on
    paired differences, never ``_rate`` results -- a paired variance and a
    binomial variance are not interchangeable.
    """
    if "mc_se" not in a or "mc_se" not in b:
        raise TypeError("_combine takes paired-difference estimates from _mc, "
                        "not marginal rates; combining a paired variance with a "
                        "binomial one would describe neither")
    if a.get("estimand") != "paired" or b.get("estimand") != "paired":
        raise TypeError(
            f"_combine requires PAIRED estimands, got "
            f"{a.get('estimand')!r} and {b.get('estimand')!r}; combining "
            f"single-arm variances here would silently report a difference of "
            f"two independent means as a change in a paired contrast")
    diff = a["mean"] - b["mean"]
    se = math.sqrt(a["mc_se"] ** 2 + b["mc_se"] ** 2)
    return {"difference": diff, "mc_se": se,
            "ci95_lo": diff - Z95 * se, "ci95_hi": diff + Z95 * se,
            "interval_method": "normal, independent cell-specific paired variances"}


def analyse_cell(cell: str, original_root: Path = ORIGINAL_ROOT,
                 disabled_root: Path = DISABLED_ROOT) -> Dict[str, Any]:
    orig = _load_adapter(original_root, cell)
    dis = _load_adapter(disabled_root, cell)
    # THE ABSOLUTE GRID, not merely agreement between the arms.  The set-equality
    # check below would pass vacuously if BOTH arms were short by the same
    # coordinates -- a check that agrees with itself and proves nothing, which is
    # this project's recurring defect shape.  Assert the intended grid first.
    want = {(p, t) for p in range(EXPECTED_PROGRAMS)
            for t in range(EXPECTED_TRIALS)}
    for name, got in (("original", orig), ("disabled", dis)):
        if set(got) != want:
            missing = sorted(want - set(got))[:3]
            extra = sorted(set(got) - want)[:3]
            raise ValueError(
                f"{cell}: the {name} arm is not the intended "
                f"{EXPECTED_PROGRAMS}x{EXPECTED_TRIALS} grid ({len(got)} rows; "
                f"missing e.g. {missing}, extra e.g. {extra})")
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
        "deploy_rate_original": _rate(dep_o),
        "deploy_rate_disabled": _rate(dep_d),
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
            "tau_tick_original": _mc(tick_o, "single_arm"),
            "tau_tick_disabled": _mc(tick_d, "single_arm"),
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
            "A_minus_N_original": _newcombe(
                cells[a_cell]["deploy_rate_original"],
                cells[n_cell]["deploy_rate_original"]),
            "A_minus_N_disabled": _newcombe(
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
            "that certificates explain NONE of the delay effect in all regimes; "
            "two rungs of one law family cannot support a universal negative",
            "that an interval including zero shows NO effect -- at mu_h = 0.05 "
            "the contrast shrinks in point estimate and its direction is simply "
            "unresolved at this sample size",
            "that differing baseline rates confound the contrast. The pairing is "
            "WITHIN-cell and exact. Different curve positions explain "
            "heterogeneity and nonlinearity of a correctly paired intervention "
            "contrast across rungs; they do not invalidate it.",
            "that the measured mu_h = 0.10 widening may be suppressed as 'merely "
            "null'; it is a result and is reported with its uncertainty",
            "that any result here generalises beyond this fixed synthetic replay "
            "design to informative-delay systems at large",
            "that a difference, or the absence of one, was prospectively "
            "predicted -- the ablation was selected after the gap was reported",
            "that the paired intervals are coverage statements; they are Monte "
            "Carlo uncertainty over this panel's finite draws",
            "that the decision-conditional timing reading is anything but "
            "descriptive: its conditioning set is selected on the outcome",
            "that the positive within-cell original-minus-disabled differences "
            "bear on the A-minus-N explanation; they answer a DIFFERENT question "
            "-- whether the branches contribute deployments at all",
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
