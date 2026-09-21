"""eb_crosscheck.py -- MY OWN implementation, written from the theorem statement.

THIS IS A CROSS-CHECK.  IT IS NOT THE AUTHOR REFERENCE AND MUST NEVER BE
DESCRIBED AS ONE.

The coordinator's default was to implement Choe-Ramdas Theorem 2 from the
theorem statement and add no dependency.  The root overruled that
(COORDINATOR_DECISIONS revision 16 item 74):

    "The VALUE of an external reference is that it was written by someone else.
    A reimplementation by me, validated by me, is not an external reference at
    all -- it is the same single point of failure wearing a citation."

So this file survives in the role the root assigned it: a separately labelled
cross-check of the vendored authors' code in ``eb_reference.py``.  It is not the
reference, it is not a construction in the primary panel, it decides nothing,
and it is not a valid bound to rely on -- see THE DISAGREEMENT below.

WHAT I IMPLEMENTED, and from what.  Theorem 2's confidence sequence for the
time-varying average conditional mean of bounded scores has four moving parts,
and I implemented each from the statement rather than from the authors' code:

  1. PREDICTABLE CENTRES.  ``gamma_t`` must be measurable with respect to the
     previous step, so it is the running mean LAGGED BY ONE, with ``gamma_1 = 0``.
     Using the current running mean instead would be the classic error: the
     centre would depend on the observation it is centring.
  2. THE INTRINSIC-TIME CLOCK.  ``V_t = max(1, sum_i (z_i - gamma_i)^2)``,
     cumulative squared PREDICTION RESIDUALS, not an empirical variance about
     the final mean, and floored at one.  This is the empirical-Bernstein part:
     the clock is data-driven, which is what makes the width adapt.
  3. THE SCALE.  ``c = hi - lo = 2`` for scores in ``[-1, +1]``.  The score
     bound is NOT replaced by a plug-in Gaussian variance.
  4. A SUB-EXPONENTIAL UNIFORM BOUNDARY applied to that clock, and the radius
     at step ``t`` is ``B(V_t) / t``.

For part 4 I implemented the CLOSED-FORM POLYNOMIAL-STITCHED boundary of
Howard, Ramdas, McAuliffe and Sekhon (2021), Theorem 1:

    k1 = (eta^(1/4) + eta^(-1/4)) / sqrt(2),   k2 = (sqrt(eta) + 1) / 2
    ell(v) = s * log log(eta * v / v_min) + log( zeta(s) / (alpha * (log eta)^s) )
    B(v)   = k1 * sqrt(v * ell(v)) + k2 * c * ell(v),   v floored at v_min

and THAT TRANSCRIPTION WAS WRONG; the corrected form is below.

The authors' reference uses a CONJUGATE-MIXTURE boundary instead of a stitched
one, so the two radii are not expected to be equal even when both are correct.
Which is tighter, where, and by how much is a measurement and not a fact about
the families: no general ordering is asserted here.  That difference is a
boundary sub-type difference and is reported, not reconciled.

=============================== THE DISAGREEMENT ===========================
MY STITCHED BOUNDARY DID NOT REPRODUCE THE AUTHORS' ``poly_stitching_bound``,
which computes the SAME published object.  Measured at the per-side allocation
this module actually uses, alpha/2 = .003125, with v_min = 10, c = 2, s = 1.4,
eta = 2 (reproduce with ``python eb_crosscheck.py``):

    v = 10     mine  28.587185   theirs  37.151466   relative -2.305e-01
    v = 50     mine  50.455912   theirs  56.962414   relative -1.142e-01
    v = 200    mine  84.029110   theirs  87.938563   relative -4.446e-02
    v = 1000   mine 165.272913   theirs 167.213768   relative -1.161e-02
    v = 5000   mine 347.345667   theirs 348.268675   relative -2.650e-03

MY BOUNDARY VALUES WERE SMALLER, i.e. my stitched radius was narrower than the
authors' for the same nominal alpha, and that is the unsafe direction: an
under-wide boundary understates uncertainty.

MY DIAGNOSIS OF THE CAUSE WAS WRONG AND IS WITHDRAWN.  I wrote that "the gap
shrinks with ``v``, so the leading ``sqrt(v * ell)`` term is right and the
discrepancy is in the constant inside ``ell``."  It is not in ``ell`` at all.
The root identified it exactly: with ``A = k1**2 * v * ell`` and
``B = k2 * c * ell``, my code returned ``sqrt(A) + B`` where the theorem's own
pinned implementation returns ``sqrt(A + B**2) + B``
(``upstream/confseq/uniform_boundaries.h:505-510``).  THE OMITTED TERM IS THE
NONNEGATIVE ``B**2`` INSIDE THE RADICAL.  ``ell`` is identical on both sides,
which is also why the gap shrinks with ``v`` -- ``B**2`` is second order in
``log`` terms while ``A`` grows linearly in ``v`` -- so the very observation I
used to locate the fault was consistent with the real fault and I read it as
confirmation of the wrong hypothesis.

THE REPAIR is ``stitched_boundary_repaired``, restored from the theorem and
verified afterwards against the authors' compiled ``poly_stitching_bound``:
**maximum absolute difference 0.0 at all five probe values**.  Nothing was
tuned to reach that.  ``stitched_boundary`` is preserved unchanged above it,
because a failed calculation that has been quoted must stay legible.

TWO FACTS THAT MUST NOT BE CONFLATED.  The bullet above is about the STITCHED
BOUNDARY alone.  The FULL confidence sequence built on the ORIGINAL (defective)
stitched boundary was nevertheless WIDER than the authors' reference on the
path measured here.  "My boundary constant was too small" and "my intervals
came out wider" are both true, of different objects.  THE EXPLANATION I
ATTACHED TO THAT -- "the authors' conjugate MIXTURE boundary is tighter than
any stitched boundary near the tuning point" -- IS WITHDRAWN: one configured
path does not establish an ordering over a family, and the root's narrowing
applies here too.  Neither fact licenses using this cross-check as a bound.

WHAT THIS CROSS-CHECK DOES ESTABLISH.  ``crosscheck_report`` verifies against
the authors' code, to machine precision (max abs diff ~1e-16), that my
predictable centres and my intrinsic-time clock equal theirs. That is the
Theorem-2-specific machinery -- the lagged centre and the squared-residual
clock -- independently reproduced. The open discrepancy is confined to the
boundary constant.
============================================================================
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

CROSSCHECK_LABEL = (
    "CROSS-CHECK (mine, from the theorem statement): Choe & Ramdas Theorem 2 "
    "with a Howard et al. Theorem 1 polynomial-stitched sub-exponential "
    "boundary. NOT the author reference. NOT a validated bound: its stitching "
    "constant disagrees with the authors' poly_stitching_bound and is narrower.")

#: Same frozen tuning as the reference, so that any difference in output is a
#: difference of construction and never of configuration.
V_OPT = 10.0
LO = -1.0
HI = 1.0
#: Stitching parameters.  ``s`` distributes crossing probability over epochs and
#: ``eta`` sets their spacing; these are the authors' documented defaults for
#: the stitched family and are fixed here before any comparison.
S_PARAM = 1.4
ETA_PARAM = 2.0


def _zeta(s: float) -> float:
    """Riemann zeta, for the stitching normaliser."""
    try:
        from scipy.special import zeta as _sz
        return float(_sz(s, 1))
    except ImportError:                                    # pragma: no cover
        n = np.arange(1, 2_000_001, dtype=np.float64)
        return float(np.sum(n ** (-s)))


def predictable_centres(z: np.ndarray) -> np.ndarray:
    """Theorem 2's ``gamma``: the running mean LAGGED BY ONE, ``gamma_1 = 0``."""
    z = np.asarray(z, dtype=np.float64)
    t = np.arange(1, z.size + 1, dtype=np.float64)
    mus = np.cumsum(z) / t
    gammas = np.empty_like(mus)
    gammas[0] = 0.0
    gammas[1:] = mus[:-1]
    return gammas


def intrinsic_time(z: np.ndarray) -> np.ndarray:
    """``V_t = max(1, sum (z_i - gamma_i)^2)`` -- cumulative squared residuals."""
    z = np.asarray(z, dtype=np.float64)
    gammas = predictable_centres(z)
    return np.maximum(1.0, np.cumsum((z - gammas) ** 2))


def stitched_boundary(v: np.ndarray, alpha: float, v_min: float = V_OPT,
                      c: float = HI - LO, s: float = S_PARAM,
                      eta: float = ETA_PARAM) -> np.ndarray:
    """My closed-form polynomial-stitched sub-exponential boundary.

    See THE DISAGREEMENT in the module docstring: this does NOT reproduce the
    authors' ``poly_stitching_bound`` and is narrower. Do not rely on it.
    """
    v = np.maximum(np.asarray(v, dtype=np.float64), v_min)
    k1 = (eta ** 0.25 + eta ** -0.25) / np.sqrt(2.0)
    k2 = (np.sqrt(eta) + 1.0) / 2.0
    ell = s * np.log(np.log(eta * v / v_min)) + np.log(
        _zeta(s) / (alpha * np.log(eta) ** s))
    return k1 * np.sqrt(v * ell) + k2 * c * ell


def stitched_boundary_repaired(v: np.ndarray, alpha: float,
                               v_min: float = V_OPT, c: float = HI - LO,
                               s: float = S_PARAM,
                               eta: float = ETA_PARAM) -> np.ndarray:
    """The SAME boundary with the omitted squared term restored.

    THE DEFECT, identified exactly by the root and verified here against the
    pinned author source rather than taken on trust.  Writing

        A = k1**2 * v * ell        B = k2 * c * ell

    ``stitched_boundary`` above returns ``sqrt(A) + B``.  Howard et al.'s
    Theorem 1 polynomial-stitched boundary, as the pinned implementation writes
    it at ``upstream/confseq/uniform_boundaries.h:505-510``, is

        PolyStitchingBound::operator()(v, alpha):
            use_v = max(v, v_min)
            ell   = s*log(log(eta*use_v/v_min)) + A_ + log(1/alpha)
            term2 = k2_ * c_ * ell
            return sqrt(k1_*k1_*use_v*ell + term2*term2) + term2

    i.e. ``sqrt(A + B**2) + B``.  The omitted term is the nonnegative ``B**2``
    INSIDE the radical.  ``ell``, ``k1``, ``k2``, ``s``, ``eta``, ``c`` and
    ``v_min`` are unchanged -- the earlier diagnosis that the discrepancy lived
    in a constant inside ``ell`` was WRONG, and this repair does not touch
    ``ell``.

    HOW THIS WAS REPAIRED, because it matters as much as the result.  The term
    was read off the cited theorem's own implementation and restored.  NOTHING
    WAS TUNED: no constant was fitted, no parameter was searched, and the
    repaired form was not adjusted after comparing it to the authors' output.
    ``crosscheck_report`` then checks it against the authors' compiled
    ``poly_stitching_bound`` as a consequence, not as a target.

    ``stitched_boundary`` is PRESERVED above, unchanged, with its banner.  A
    failed calculation that has been quoted must stay legible.

    This repairs a CROSS-CHECK.  It does not make the cross-check the
    reference, it is not a validated bound for this project's use, and a
    boundary being narrower or wider than another proves nothing about the
    primary theorem.
    """
    v = np.maximum(np.asarray(v, dtype=np.float64), v_min)
    k1 = (eta ** 0.25 + eta ** -0.25) / np.sqrt(2.0)
    k2 = (np.sqrt(eta) + 1.0) / 2.0
    ell = s * np.log(np.log(eta * v / v_min)) + np.log(
        _zeta(s) / (alpha * np.log(eta) ** s))
    term2 = k2 * c * ell
    return np.sqrt(k1 * k1 * v * ell + term2 * term2) + term2


def crosscheck_bands(z: np.ndarray, alpha: float) -> Tuple[np.ndarray, np.ndarray]:
    """My EB confidence sequence.  NOT the reference; NOT a validated bound."""
    z = np.asarray(z, dtype=np.float64)
    if z.size == 0:
        return np.zeros(0), np.zeros(0)
    t = np.arange(1, z.size + 1, dtype=np.float64)
    mus = np.cumsum(z) / t
    vs = intrinsic_time(z)
    # two-sided: split the per-gate allocation, exactly as the reference does
    half = float(alpha) / 2.0
    radii = stitched_boundary(vs, half) / t
    return mus - radii, mus + radii


def crosscheck_report(z: np.ndarray, alpha: float) -> Dict[str, object]:
    """Compare my implementation against the VENDORED AUTHORS' reference.

    Reports agreement and disagreement.  Reconciles neither side: where the two
    differ, both numbers are recorded and the difference is named.
    """
    import eb_reference as ref

    z = np.asarray(z, dtype=np.float64)
    t = np.arange(1, z.size + 1, dtype=np.float64)
    out: Dict[str, object] = {
        "schema": "live_ab_validation_v2.reference.crosscheck.1",
        "n": int(z.size), "alpha": float(alpha),
        "reference_label": ref.REFERENCE_LABEL,
        "crosscheck_label": CROSSCHECK_LABEL,
    }
    try:
        r_lo, r_hi = ref.reference_bands(z, alpha)
    except ref.ReferenceUnavailable as exc:
        out["reference_available"] = False
        out["reference_error"] = repr(exc)
        return out
    out["reference_available"] = True

    c_lo, c_hi = crosscheck_bands(z, alpha)
    mus = np.cumsum(z) / t
    vs = intrinsic_time(z)

    # -- AGREEMENT 1: the centre.  Both must be the plain running mean. -----
    r_centre = (r_lo + r_hi) / 2.0
    out["centre_max_abs_diff"] = float(np.max(np.abs(r_centre - mus)))

    # -- AGREEMENT 2: the intrinsic-time clock.  Checked by feeding MY vs into
    # the authors' own boundary and asking whether their radii come back.  If
    # they do, my centres and my clock equal theirs to machine precision, which
    # is the part of Theorem 2 this cross-check actually validates.
    from confseq import boundaries                        # authors' code
    half = float(alpha) / 2.0
    their_radii = (r_hi - r_lo) / 2.0
    rebuilt = np.asarray(boundaries.gamma_exponential_mixture_bound(
        vs, half, V_OPT, c=HI - LO, alpha_opt=half), dtype=np.float64) / t
    out["intrinsic_time_roundtrip_max_abs_diff"] = float(
        np.max(np.abs(rebuilt - their_radii)))

    # -- DISAGREEMENT 1: my stitched boundary vs THEIR stitched boundary. ----
    probe_v = np.array([10.0, 50.0, 200.0, 1000.0, 5000.0])
    mine_b = stitched_boundary(probe_v, half)
    theirs_b = np.array([boundaries.poly_stitching_bound(
        float(v), half, V_OPT, HI - LO, S_PARAM, ETA_PARAM) for v in probe_v])
    out["stitching_disagreement"] = {
        "note": "SAME published object (Howard et al. Theorem 1), two "
                "implementations, NOT reconciled. Mine is narrower, which is "
                "the unsafe direction, so the cross-check is not a usable bound.",
        "v": probe_v.tolist(), "mine": mine_b.tolist(),
        "theirs_poly_stitching_bound": theirs_b.tolist(),
        "relative": ((mine_b - theirs_b) / theirs_b).tolist()}

    # -- THE REPAIR of disagreement 1, from the theorem, preserving the original
    repaired_b = stitched_boundary_repaired(probe_v, half)
    out["stitching_repair"] = {
        "defect": ("the omitted nonnegative B**2 inside sqrt(A + B**2), with "
                   "A = k1**2 * v * ell and B = k2 * c * ell. NOT a constant "
                   "inside ell: the earlier diagnosis was wrong and is "
                   "withdrawn."),
        "method": ("restored from the cited theorem's own pinned "
                   "implementation, upstream/confseq/uniform_boundaries.h "
                   "lines 505-510. No constant was fitted and no parameter was "
                   "searched; the agreement below is a consequence of the "
                   "repair, not its target."),
        "original_preserved_as": "stitched_boundary (unchanged, with its banner)",
        "v": probe_v.tolist(),
        "original": mine_b.tolist(),
        "repaired": repaired_b.tolist(),
        "theirs_poly_stitching_bound": theirs_b.tolist(),
        "repaired_minus_theirs": (repaired_b - theirs_b).tolist(),
        "repaired_max_abs_diff_vs_authors": float(
            np.max(np.abs(repaired_b - theirs_b))),
        "repaired_max_rel_diff_vs_authors": float(
            np.max(np.abs((repaired_b - theirs_b) / theirs_b))),
        "what_this_does_not_establish": (
            "the repaired cross-check is still a CROSS-CHECK. It is not the "
            "declared reference, it is not a validated bound for this study, "
            "and neither its narrowness nor its width says anything about the "
            "primary theorem."),
    }

    # -- DISAGREEMENT 2: full CS width, stitched (mine) vs mixture (theirs). -
    r_w, c_w = r_hi - r_lo, c_hi - c_lo
    out["width_comparison"] = {
        "note": "Different boundary sub-types: the authors use a conjugate "
                "mixture, this cross-check a stitched boundary. A difference "
                "here is expected even if both were correct, and is NOT "
                "evidence about either. Reported, not reconciled.",
        "reference_width_final": float(r_w[-1]),
        "crosscheck_width_final": float(c_w[-1]),
        "ratio_final": float(c_w[-1] / r_w[-1]) if r_w[-1] else None,
        "ratio_min": float(np.min(c_w / r_w)),
        "ratio_max": float(np.max(c_w / r_w))}
    return out


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    rng = np.random.default_rng(12345)
    z = rng.choice([-1.0, 0.0, 1.0], size=1000, p=[0.2, 0.6, 0.2])
    print(CROSSCHECK_LABEL)
    print(json.dumps(crosscheck_report(z, 0.00625), indent=2))
