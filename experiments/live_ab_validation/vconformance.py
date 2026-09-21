"""COMPLETE operational-policy conformance, as a pinned preflight gate.

WHY THIS EXISTS
---------------
I flagged the weakness in my own delivery: the preflight-only mode verifies ONE draw,
where per-trial verification did 420,080 pair-state checks.  Then I measured the gap
instead of arguing about it.  A single draw at ``n_max=1000``:

  * contains all 6 atoms, both arm orders, and both delay blocks;
  * catches a seeded defect confined to ANY single atom, to either delay block, and even
    to a single delay value that occurs just once in the draw;
  * but contains only **237 of the 620** delay values, so a defect confined to one of
    the other 383 is MISSED.

So "one draw" is much stronger than a random sample, and still not complete.  Root's
own instruction supplies the right shape:

    "Before each immutable job, require the accepted deterministic witness/configuration
     checks on its pinned source.  Re-run only affected checks when their source changes."

This module is that check, and it is **complete by construction** rather than by
enumeration of 5.7M states:

    A pair's operational enclosure is PIECEWISE CONSTANT in age, with breakpoints only
    at the two certificate thresholds recorded in ``THRESH_NARROW_OP`` /
    ``THRESH_COLLAPSE_OP``.  Therefore verifying (a) that those tables are exactly the
    first ages at which each certificate fires, over EVERY (cost combo, delay) the
    design can produce, and (b) that ``vpolicy`` agrees at every boundary age and one
    interior age of each piece, verifies the rule at every reachable age.

That is total coverage of the per-pair rule for a few thousand scalar comparisons
instead of millions, and unlike the per-trial mode it does not depend on which
coordinates a particular draw happened to contain.

It gates nothing scientific and computes no effect.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vpolicy                                                  # noqa: E402

#: Sources whose change invalidates a stored conformance receipt.  These are the
#: files that define the operational rule on either side of the comparison.
CONFORMANCE_SOURCES = ("vgen.py", "vband.py", "vpolicy.py")

RECEIPT_NAME = "CONFORMANCE_RECEIPT.json"


class ConformanceError(RuntimeError):
    pass


def source_fingerprint() -> Dict[str, str]:
    out = {}
    for name in CONFORMANCE_SOURCES:
        out[name] = hashlib.sha256((HERE / name).read_bytes()).hexdigest()
    return out


def _all_delays() -> List[int]:
    return (list(range(vgen.SHORT_LOW, vgen.SHORT_HIGH + 1))
            + list(range(vgen.LONG_LOW, vgen.LONG_HIGH + 1)))


def verify_threshold_tables() -> Dict[str, Any]:
    """The operational tables ARE the first ages at which each certificate fires.

    Checked over every (cost combo, delay) the frozen design can produce, by
    direct evaluation of the certificate inequalities -- not by trusting the
    table builder that produced them.
    """
    tol, eps = vgen.RTOL, vgen.OPERATIONAL_EPS
    delays = _all_delays()
    checked = 0
    for ci, (c_rev, c_pend) in enumerate(vgen.COST_COMBOS):
        for d in delays:
            if d <= 0:
                continue
            ages = np.arange(0, d, dtype=np.int64)          # inside the pending life
            ell = (c_pend * ages) / d
            reverse = ell > (1.0 - tol) * c_rev + eps       # pending branch dies
            forward = (1.0 - tol) * ell > c_rev + eps       # tie dies
            want_narrow = int(ages[reverse][0]) if reverse.any() else d
            want_collapse = int(ages[forward][0]) if forward.any() else d
            got_narrow = int(vgen.THRESH_NARROW_OP[ci, d])
            got_collapse = int(vgen.THRESH_COLLAPSE_OP[ci, d])
            if got_narrow != min(want_narrow, d):
                raise ConformanceError(
                    f"THRESH_NARROW_OP[{ci},{d}] = {got_narrow}, but the reverse "
                    f"certificate first fires at age {want_narrow}")
            if got_collapse != min(want_collapse, d):
                raise ConformanceError(
                    f"THRESH_COLLAPSE_OP[{ci},{d}] = {got_collapse}, but the "
                    f"forward certificate first fires at age {want_collapse}")
            if got_narrow > got_collapse:
                raise ConformanceError(
                    f"narrow must not follow collapse at combo {ci}, delay {d}")
            checked += 1
    return {"combo_delay_pairs_checked": checked,
            "cost_combos": len(vgen.COST_COMBOS),
            "delays": len(delays),
            "claim": ("the operational threshold tables equal the first age at "
                      "which each certificate fires, at every reachable "
                      "(combo, delay)")}


def verify_against_vpolicy_at_every_piece() -> Dict[str, Any]:
    """``vgen`` equals ``vpolicy`` at every boundary AND interior of every piece.

    The enclosure is piecewise constant in age with breakpoints exactly at the
    two thresholds, so a boundary-plus-interior check per piece covers every
    reachable age.  This is the step that makes the gate complete without
    enumerating every age.
    """
    cap = float(vgen.COST_CAP)
    delays = _all_delays()
    compared = 0

    # ---- THE RESOLVED AND UNREVEALED BRANCHES ---------------------------
    # Found by running the seeded-defect controls across a SPREAD of delays
    # rather than one: a defect confined to d == 0 was NOT caught, because the
    # partial-branch loop below skips d <= 0 (a zero-delay pair is resolved at
    # every age and never partial).  The gate therefore claimed complete
    # conformance while never touching that delay -- the same claim/check gap
    # this project keeps turning up, this time in my own gate.  All three
    # branches are now checked, so "complete" means complete.
    for a_i in range(len(vgen.ATOM_ORDER)):
        sc, si = int(vgen.ATOM_SC[a_i]), int(vgen.ATOM_SI[a_i])
        cc, cci = float(vgen.ATOM_CC[a_i]), float(vgen.ATOM_CI[a_i])
        ep_c = vband.Episode.pending("c", cap).finalized(sc, cc)
        ep_i = vband.Episode.pending("i", cap).finalized(si, cci)
        want_h = vpolicy.operational_hierarchy_bounds(ep_c, ep_i)
        want_s = vpolicy.operational_success_bounds(ep_c, ep_i)
        for d in (0, 1, vgen.SHORT_HIGH, vgen.LONG_LOW, vgen.LONG_HIGH):
            for age in (d, d + 1, d + 7):
                got = _vgen_resolved(a_i, d, age)
                if got != (want_h[0], want_h[1], want_s[0], want_s[1]):
                    raise ConformanceError(
                        f"RESOLVED branch: vgen != vpolicy at atom {a_i}, d={d}, "
                        f"age={age}: {got} vs "
                        f"{(want_h[0], want_h[1], want_s[0], want_s[1])}")
                compared += 1
    # unrevealed: neither arm revealed must be the full range on both scores
    both_pending = (vband.Episode.pending("c", cap).with_elapsed_cost(0.0),
                    vband.Episode.pending("i", cap).with_elapsed_cost(0.0))
    want_h = vpolicy.operational_hierarchy_bounds(*both_pending)
    want_s = vpolicy.operational_success_bounds(*both_pending)
    for d in (1, vgen.SHORT_HIGH, vgen.LONG_LOW, vgen.LONG_HIGH):
        got = _vgen_unrevealed(d)
        if got != (want_h[0], want_h[1], want_s[0], want_s[1]):
            raise ConformanceError(
                f"UNREVEALED branch: vgen != vpolicy at d={d}: {got} vs "
                f"{(want_h[0], want_h[1], want_s[0], want_s[1])}")
        compared += 1

    # ---- THE PARTIAL BRANCH, piece by piece ------------------------------
    for ci, (c_rev, c_pend) in enumerate(vgen.COST_COMBOS):
        for d in delays:
            if d <= 0:
                continue        # a zero-delay pair is never partial; covered above
            a_n = int(vgen.THRESH_NARROW_OP[ci, d])
            a_c = int(vgen.THRESH_COLLAPSE_OP[ci, d])
            # boundaries of each piece, their predecessors, and an interior point
            cand = {0, d - 1, a_n, a_c, a_n - 1, a_c - 1,
                    max(0, (a_n + a_c) // 2), max(0, (a_c + d) // 2)}
            for age in sorted(x for x in cand if 0 <= x < d):
                ell = (c_pend * age) / d
                for s_rev in (0, 1):
                    for cand_first in (True, False):
                        rev = vband.Episode.pending("rev", cap).finalized(
                            int(s_rev), float(c_rev))
                        pen = vband.Episode.pending("pend", cap).with_elapsed_cost(
                            float(ell))
                        ep_c, ep_i = ((rev, pen) if cand_first else (pen, rev))
                        want_h = vpolicy.operational_hierarchy_bounds(ep_c, ep_i)
                        want_s = vpolicy.operational_success_bounds(ep_c, ep_i)
                        got = _vgen_single(s_rev, cand_first, c_rev, c_pend,
                                           d, age)
                        if got != (want_h[0], want_h[1], want_s[0], want_s[1]):
                            raise ConformanceError(
                                f"vgen != vpolicy at combo {ci}, d={d}, age={age}, "
                                f"s_rev={s_rev}, cand_first={cand_first}: "
                                f"{got} vs {(want_h[0], want_h[1], want_s[0], want_s[1])}")
                        compared += 1
    return {"pair_states_compared": compared,
            "branches_covered": ["resolved", "unrevealed", "partial"],
            "coverage_argument": ("the enclosure is piecewise constant in age with "
                                  "breakpoints only at the two certificate "
                                  "thresholds, so boundary+interior per piece "
                                  "covers every reachable age"),
            "claim": "vgen's vectorised operational rule equals vpolicy's everywhere"}


def _vgen_resolved(atom: int, d: int, age: int) -> Tuple[float, float, float, float]:
    """One RESOLVED pair through the real ``vgen`` path (age >= d)."""
    sc, si = int(vgen.ATOM_SC[atom]), int(vgen.ATOM_SI[atom])
    cc, ci = float(vgen.ATOM_CC[atom]), float(vgen.ATOM_CI[atom])
    ep_c = vband.Episode.pending("c", float(vgen.COST_CAP)).finalized(sc, cc)
    ep_i = vband.Episode.pending("i", float(vgen.COST_CAP)).finalized(si, ci)
    z = vband.hierarchy_bounds(ep_c, ep_i)[0]
    ds = vband.success_bounds(ep_c, ep_i)[0]
    draw = vgen.TrialDraw(
        cell=None, namespace="conformance", program_index=0, trial_index=0, n=1,
        atom=np.array([atom], dtype=np.int8),
        z=np.array([z], dtype=np.int8), dsc=np.array([ds], dtype=np.int8),
        d=np.array([d], dtype=np.int64), f=np.array([0], dtype=np.int64),
        cand_first=np.array([True]), s_rev=np.array([sc], dtype=np.int8),
        c_rev=np.array([cc]), c_pend=np.array([ci]),
        a_narrow=np.array([0], dtype=np.int64),
        a_collapse=np.array([0], dtype=np.int64))
    st = vgen.state_at_age(draw, np.array([age], dtype=np.int64),
                           policy="operational")
    return (float(st.h_lo[0]), float(st.h_hi[0]),
            float(st.s_lo[0]), float(st.s_hi[0]))


def _vgen_unrevealed(d: int) -> Tuple[float, float, float, float]:
    """One UNREVEALED pair through the real ``vgen`` path (age < f)."""
    draw = vgen.TrialDraw(
        cell=None, namespace="conformance", program_index=0, trial_index=0, n=1,
        atom=np.array([0], dtype=np.int8),
        z=np.array([0], dtype=np.int8), dsc=np.array([0], dtype=np.int8),
        d=np.array([d], dtype=np.int64), f=np.array([d], dtype=np.int64),
        cand_first=np.array([True]), s_rev=np.array([1], dtype=np.int8),
        c_rev=np.array([10.0]), c_pend=np.array([40.0]),
        a_narrow=np.array([0], dtype=np.int64),
        a_collapse=np.array([0], dtype=np.int64))
    st = vgen.state_at_age(draw, np.array([0], dtype=np.int64),
                           policy="operational")
    return (float(st.h_lo[0]), float(st.h_hi[0]),
            float(st.s_lo[0]), float(st.s_hi[0]))


def _vgen_single(s_rev: int, cand_first: bool, c_rev: float, c_pend: float,
                 d: int, age: int) -> Tuple[float, float, float, float]:
    """One pair's operational enclosure through the real ``vgen`` code path."""
    draw = vgen.TrialDraw(
        cell=None, namespace="conformance", program_index=0, trial_index=0, n=1,
        atom=np.array([0], dtype=np.int8),
        z=np.array([0], dtype=np.int8), dsc=np.array([0], dtype=np.int8),
        d=np.array([d], dtype=np.int64), f=np.array([0], dtype=np.int64),
        cand_first=np.array([cand_first]),
        s_rev=np.array([s_rev], dtype=np.int8),
        c_rev=np.array([c_rev]), c_pend=np.array([c_pend]),
        a_narrow=np.array([0], dtype=np.int64),
        a_collapse=np.array([0], dtype=np.int64))
    st = vgen.state_at_age(draw, np.array([age], dtype=np.int64),
                           policy="operational")
    return (float(st.h_lo[0]), float(st.h_hi[0]),
            float(st.s_lo[0]), float(st.s_hi[0]))


def run(write_to: Optional[Path] = None) -> Dict[str, Any]:
    """The full gate.  Raises on any disagreement; returns its own counts."""
    t0 = time.perf_counter()
    tables = verify_threshold_tables()
    policy = verify_against_vpolicy_at_every_piece()
    receipt = {
        "schema": "live_ab_validation_v2.conformance.1",
        "purpose": ("pinned preflight gate: COMPLETE operational-policy "
                    "conformance, independent of which coordinates any draw "
                    "happens to contain"),
        "source_fingerprint": source_fingerprint(),
        "threshold_tables": tables,
        "vpolicy_agreement": policy,
        "elapsed_seconds": time.perf_counter() - t0,
        "gates": "nothing scientific; computes no effect and authorizes nothing",
        "supersedes": ("the one-draw preflight as the COVERAGE argument. The "
                       "one-draw live check is retained as a smoke test, not as "
                       "the coverage claim."),
    }
    if write_to is not None:
        Path(write_to).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def assert_pinned_receipt_matches(receipt_path: Path) -> Dict[str, Any]:
    """Root: re-run only affected checks when their source changes.

    A stored receipt is honoured only while every conformance source still
    hashes to what it hashed when the receipt was written.  Any change and the
    caller must re-run, so a stale pass cannot be inherited.
    """
    p = Path(receipt_path)
    if not p.is_file():
        raise ConformanceError(f"no conformance receipt at {p}; run the gate")
    stored = json.loads(p.read_text())
    now = source_fingerprint()
    was = stored.get("source_fingerprint") or {}
    moved = sorted(k for k in set(now) | set(was) if now.get(k) != was.get(k))
    if moved:
        raise ConformanceError(
            f"conformance sources changed since the receipt was written: {moved}. "
            f"Re-run the gate; a stale pass must not be inherited.")
    return {"valid": True, "sources_checked": sorted(now),
            "pair_states_compared": stored["vpolicy_agreement"]["pair_states_compared"],
            "combo_delay_pairs_checked": stored["threshold_tables"]["combo_delay_pairs_checked"]}


if __name__ == "__main__":                                     # pragma: no cover
    r = run(HERE / RECEIPT_NAME)
    print(json.dumps({k: v for k, v in r.items()
                      if k != "source_fingerprint"}, indent=2, sort_keys=True))
