#!/usr/bin/env python3
"""vpolicy.py -- the versioned CPU OPERATIONAL-POLICY ADAPTER.

WHY THIS MODULE EXISTS
----------------------
The v2 comparison was, until this module, a comparison between TWO DIFFERENT
OBJECTS: an OPERATIONAL policy on one side and an IDEAL ENCLOSURE ORACLE on the
other.  The live rule narrows a partially revealed pair only when a SUFFICIENT
CERTIFICATE fires, with a strictly positive epsilon of headroom.  ``vband``
instead enumerates the feasible cost box directly and asks whether a tier
outcome is ACHIEVABLE anywhere in it.  The two are algebraically the same
threshold and are NOT the same floating-point expression, and one of them
additionally demands ``eps`` of headroom; so they can and do differ exactly at
the thresholds.  Ninety-nine such looks were recorded in the 04:53 v2 run and
were counted as "disagreements", which mislabels a DECLARED DIFFERENCE OF
POLICY as a defect of arithmetic.

The root's ruling (COORDINATOR_DECISIONS revision 18 item 92, and the
04:53 root disposition "Root's scientific decision: retain the conservative
live policy") is:

  * KEEP the conservative live numeric policy.  Do NOT tighten the live rule so
    that the two implementations agree -- tightening a rule until two
    implementations agree is optimising the measurement instead of the thing
    measured.
  * Implement the DECLARED operational policy INDEPENDENTLY, as a separately
    versioned CPU operational adapter, and use THAT for calibration claims
    about the live monitor.
  * Keep the ideal-enclosure oracle (``vband``'s own enumeration) SEPARATELY,
    as an explicitly different observation policy, with oracle containment kept
    as ITS OWN CHECK rather than as a disagreement count.

This module is that adapter.  It is the third object in the comparison, not a
replacement for either of the other two.

WHAT "INDEPENDENT" MEANS HERE, EXACTLY
--------------------------------------
This module imports NOTHING from the monitored implementation.  It imports
``vband`` -- this validation's own code -- for the episode state machine, the
band arithmetic and the final-score rule, all of which are SHARED and unchanged.
What it re-implements is only the OBSERVATION POLICY: which hierarchy values a
partially revealed pair still admits.  That policy is transcribed from the
SHARED MATHEMATICAL CERTIFICATE/EPSILON CONTRACT as the protocol states it
(protocol 7.5 item 5, completed under COORDINATOR_DECISIONS revision 12 ruling
54), not by copying, importing or executing ``experiments/live_ab/``'s source.
The static and dynamic independence guards of F16 apply to this file exactly as
they apply to every other module here, and they must keep passing.

THE DECLARED OPERATIONAL POLICY, TRANSCRIBED
--------------------------------------------
With tolerance ``tol`` = 0.05, certificate epsilon ``eps`` = 1e-9, a revealed
episode ``r`` carrying ``(s_r, L_r)`` and a pending partner carrying only its
certified elapsed cost ``ell``, and ``sgn`` = +1 when the CANDIDATE is the
revealed arm and -1 when the INCUMBENT is:

  (a) both revealed      -> the exact final score, a point.
  (b) neither revealed   -> [-1, +1].  Nothing is excluded.
  (c) exactly one revealed:
        s_r == 0                               -> {-sgn, 0}
        s_r == 1 and (1-tol)*ell > L_r + eps   -> {sgn}          FORWARD
        s_r == 1 and ell > (1-tol)*L_r + eps   -> {0, sgn}       REVERSE
        otherwise                              -> {-1, 0, +1}

and the enclosure is ``[min(feasible), max(feasible)]``.  The success score has
no certificate at all on either side: a revealed episode contributes ``(s, s)``
and a pending one ``(0, 1)``, and the enclosure is
``[s_cand_lo - s_inc_hi, s_cand_hi - s_inc_lo]``.

THE TWO PREDICATES ARE WRITTEN IN THE EXECUTED FORM AND NOT IN THE ALGEBRAIC
ONE.  ``ell > L_r / (1 - tol)`` is the explanatory threshold; the executed float
expression is ``(1 - tol) * ell > L_r + eps``, and the reverse one is
``ell > (1 - tol) * L_r + eps``.  Writing the division form here would
reintroduce exactly the mislabelling the root corrected on 2026-09-21 05:32.

WHAT THIS ADAPTER IS NOT
------------------------
  * NOT a tightening or loosening of the live rule.  It is the same rule,
    written again.  If it disagrees with the live rule anywhere, that is a
    finding about one of the two transcriptions, not a licence to edit either.
  * NOT the oracle.  The oracle stays in ``vband`` and keeps its results.  This
    module never edits, wraps or shadows it.
  * NOT a change to any scientific rule: scoring, alpha, rho, delta, n_min,
    margins, gates, seeds, stopping, deadline and finalization are untouched
    and are not even read here beyond being passed through.

CPU only.  No model call, no network, no file written by this module.
"""
from __future__ import annotations

import math
from typing import Dict, Hashable, List, Optional, Sequence, Tuple

import vband

# ---------------------------------------------------------------------------
# Version.  The root asked for a VERSIONED adapter; this is the version, and it
# is recorded into every comparison summary that used it.
# ---------------------------------------------------------------------------
POLICY_ID = "cpu-operational-policy-adapter"
POLICY_VERSION = "1.0.0"
POLICY_LABEL = (
    "independent CPU implementation of the declared live observation policy: "
    "certificate-gated narrowing with epsilon headroom, written from the "
    "shared mathematical contract and not from the monitored source"
)

#: The frozen tolerance of the cost tier.  Same number as the shared contract's;
#: taken from this validation's own constant so that a drift in either would be
#: caught by the equality assertion below rather than silently absorbed.
OPERATIONAL_TOL: float = vband.COST_RELATIVE_TOLERANCE

#: The certificate headroom.  A one-sided margin added to the RIGHT-hand side of
#: each certificate, so a float rounding error smaller than it can never forge a
#: certificate.  Declared here as a constant of the POLICY, not imported.
CERTIFICATE_EPS: float = 1e-9

#: The absolute cost tolerance of the declared tier.  Zero.
OPERATIONAL_ATOL: float = vband.COST_ABSOLUTE_TOLERANCE

if OPERATIONAL_ATOL != 0.0:                                  # pragma: no cover
    raise vband.ValidationError(
        "the declared operational policy is written for a zero absolute cost "
        "tolerance; a nonzero one changes the certificate algebra")


class PolicyError(vband.ValidationError):
    """Raised when the adapter is handed a state its declared policy cannot hold."""


# ---------------------------------------------------------------------------
# 1.  The declared policy, on two episodes
# ---------------------------------------------------------------------------
def _revealed(ep: "vband.Episode") -> bool:
    """The declared policy has exactly two episode states: revealed, or pending.

    ``final`` is the point-outcome certificate, which is what the live notion of
    "revealed" is: success AND cost both certain.
    """
    return bool(ep.final)


def representable(ep: "vband.Episode") -> bool:
    """False for a state the DECLARED policy has no channel for.

    The live observation policy learns an episode's success only at reveal.  A
    state in which success is already certain while the cost is still pending
    cannot be expressed by it.  The adapter does not crash on such a state: it
    treats the success as still unknown, which is CONSERVATIVE (wider, never
    narrower, and never unsound).  It is counted, because an uncounted
    approximation is an undisclosed one.
    """
    return bool(ep.final or not ep.success_known)


def operational_hierarchy_bounds(ep_cand: "vband.Episode",
                                 ep_inc: "vband.Episode",
                                 tol: float = OPERATIONAL_TOL,
                                 eps: float = CERTIFICATE_EPS,
                                 tiers: Sequence["vband.Tier"] = vband.TIERS,
                                 ) -> Tuple[float, float]:
    """The declared operational hierarchy enclosure of one pair.

    ``ep_cand`` is the CANDIDATE arm and ``ep_inc`` the INCUMBENT, in that
    order, so that a positive score means the candidate won.
    """
    if not (0.0 <= tol < 1.0):
        raise PolicyError("require 0 <= tol < 1")
    if eps < 0.0:
        raise PolicyError("the certificate epsilon is a one-sided margin >= 0")

    cand_rev, inc_rev = _revealed(ep_cand), _revealed(ep_inc)

    if cand_rev and inc_rev:                                 # (a)
        z = float(vband.final_hierarchy_score(ep_cand, ep_inc, tiers))
        return (z, z)
    if not cand_rev and not inc_rev:                         # (b)
        return (float(vband.SCORE_LOW), float(vband.SCORE_HIGH))

    # (c) exactly one revealed.
    if cand_rev:
        revealed, partner, sgn = ep_cand, ep_inc, 1.0
    else:
        revealed, partner, sgn = ep_inc, ep_cand, -1.0

    s_r = int(revealed.success_lo)
    l_r = float(revealed.cost_lo)
    # the single fact a pending state supplies: a certified elapsed cost can
    # only grow, so the partner's final cost x satisfies x >= ell.
    ell = float(partner.cost_lo)

    if s_r == 0:
        feasible = {-sgn, 0.0}
    elif (1.0 - tol) * ell > l_r + eps:                      # FORWARD certificate
        feasible = {sgn}
    elif ell > (1.0 - tol) * l_r + eps:                      # REVERSE certificate
        feasible = {0.0, sgn}
    else:
        feasible = {-1.0, 0.0, 1.0}
    return (float(min(feasible)), float(max(feasible)))


def operational_success_bounds(ep_cand: "vband.Episode",
                               ep_inc: "vband.Episode") -> Tuple[float, float]:
    """The declared operational success enclosure: no certificate on either side."""
    a_lo, a_hi = ((int(ep_cand.success_lo), int(ep_cand.success_lo))
                  if _revealed(ep_cand) else (0, 1))
    b_lo, b_hi = ((int(ep_inc.success_lo), int(ep_inc.success_lo))
                  if _revealed(ep_inc) else (0, 1))
    return (float(a_lo - b_hi), float(a_hi - b_lo))


# ---------------------------------------------------------------------------
# 2.  The certificate margin, reported rather than assumed
# ---------------------------------------------------------------------------
def certificate_margins(ep_cand: "vband.Episode", ep_inc: "vband.Episode",
                        tol: float = OPERATIONAL_TOL
                        ) -> Optional[Dict[str, float]]:
    """``None`` unless exactly one arm is revealed and it succeeded.

    Each margin is the executed left-hand side minus the executed right-hand
    side WITHOUT the epsilon, so a margin of exactly 0.0 means the certificate
    sits on the threshold and would still not fire at ``eps = 0``, while a
    margin in ``(0, eps]`` means the epsilon alone is what withholds it.
    """
    cand_rev, inc_rev = _revealed(ep_cand), _revealed(ep_inc)
    if cand_rev == inc_rev:
        return None
    revealed, partner = ((ep_cand, ep_inc) if cand_rev else (ep_inc, ep_cand))
    if int(revealed.success_lo) == 0:
        return None
    l_r = float(revealed.cost_lo)
    ell = float(partner.cost_lo)
    return {"forward_margin": (1.0 - tol) * ell - l_r,
            "reverse_margin": ell - (1.0 - tol) * l_r,
            "ell": ell, "revealed_cost": l_r}


# ---------------------------------------------------------------------------
# 3.  The monitor that runs the declared policy
# ---------------------------------------------------------------------------
class OperationalMonitor(vband.ValidationMonitor):
    """``vband.ValidationMonitor`` with the DECLARED OPERATIONAL enclosure policy.

    Everything else -- enrollment ledger, immutable positions, denominator,
    band arithmetic, decision rule, alpha, rho, delta, n_min -- is the shared,
    unchanged code.  ONLY ``_refresh`` differs, because only the observation
    policy differs.  Subclassing rather than copying is deliberate: it makes it
    impossible for this adapter to drift on anything except the one thing it is
    supposed to differ on.
    """

    policy_id = POLICY_ID
    policy_version = POLICY_VERSION

    def __init__(self, *args, certificate_eps: float = CERTIFICATE_EPS,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.certificate_eps = float(certificate_eps)
        #: states the declared policy cannot express and therefore rounds off
        #: conservatively; see ``representable``.
        self.unrepresentable_episode_states = 0
        #: how often each branch of the declared policy fired, cumulatively over
        #: refreshes -- evidence that the certificate paths are live, not merely
        #: written.
        self.branch_counts: Dict[str, int] = {
            "both_revealed": 0, "neither_revealed": 0,
            "revealed_failed": 0, "forward_certificate": 0,
            "reverse_certificate": 0, "no_certificate": 0}

    def _branch(self, ep_cand: "vband.Episode", ep_inc: "vband.Episode") -> str:
        cand_rev, inc_rev = _revealed(ep_cand), _revealed(ep_inc)
        if cand_rev and inc_rev:
            return "both_revealed"
        if not cand_rev and not inc_rev:
            return "neither_revealed"
        revealed, partner = ((ep_cand, ep_inc) if cand_rev else (ep_inc, ep_cand))
        if int(revealed.success_lo) == 0:
            return "revealed_failed"
        tol, eps = self.rtol, self.certificate_eps
        l_r, ell = float(revealed.cost_lo), float(partner.cost_lo)
        if (1.0 - tol) * ell > l_r + eps:
            return "forward_certificate"
        if ell > (1.0 - tol) * l_r + eps:
            return "reverse_certificate"
        return "no_certificate"

    def _refresh(self, pair: "vband.Pair") -> None:
        slot_a, slot_b = pair.arm_slots()
        ep_a, ep_b = self.episodes[slot_a], self.episodes[slot_b]
        for ep in (ep_a, ep_b):
            if not representable(ep):
                self.unrepresentable_episode_states += 1
        self.branch_counts[self._branch(ep_a, ep_b)] += 1
        h_lo, h_hi = operational_hierarchy_bounds(
            ep_a, ep_b, tol=self.rtol, eps=self.certificate_eps, tiers=self.tiers)
        pair.hierarchy = pair.hierarchy.narrow(h_lo, h_hi)
        s_lo, s_hi = operational_success_bounds(ep_a, ep_b)
        pair.success = pair.success.narrow(s_lo, s_hi)
        if ep_a.final and ep_b.final:
            pair.hierarchy = pair.hierarchy.collapse(
                vband.final_hierarchy_score(ep_a, ep_b, self.tiers))
            pair.success = pair.success.collapse(
                vband.final_success_score(ep_a, ep_b))

    # -- provenance ---------------------------------------------------------
    def policy_record(self) -> Dict[str, object]:
        """What ran, so a receipt can state it rather than assert it."""
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_label": POLICY_LABEL,
            "tol": float(self.rtol),
            "certificate_eps": float(self.certificate_eps),
            "forward_predicate": "(1 - tol) * ell > L_r + eps",
            "reverse_predicate": "ell > (1 - tol) * L_r + eps",
            "predicates_are_the_executed_float_expressions": True,
            "division_form_is_explanatory_only": True,
            "branch_counts": dict(self.branch_counts),
            "unrepresentable_episode_states":
                int(self.unrepresentable_episode_states),
            "shared_unchanged": [
                "enrollment ledger and immutable positions",
                "denominator and prefix rule",
                "normal-mixture band arithmetic",
                "decision rule, alpha_gate, rho, delta, n_min",
                "final-score scoring rule",
            ],
        }


# ---------------------------------------------------------------------------
# 4.  Oracle containment, as its OWN check
# ---------------------------------------------------------------------------
def oracle_bounds(ep_cand: "vband.Episode", ep_inc: "vband.Episode",
                  rtol: float = vband.COST_RELATIVE_TOLERANCE,
                  atol: float = vband.COST_ABSOLUTE_TOLERANCE
                  ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """The IDEAL ENCLOSURE ORACLE's bounds, unchanged, for side-by-side use."""
    return (vband.hierarchy_bounds(ep_cand, ep_inc, rtol=rtol, atol=atol),
            vband.success_bounds(ep_cand, ep_inc))


def containment_report(ep_cand: "vband.Episode", ep_inc: "vband.Episode",
                       tol: float = OPERATIONAL_TOL,
                       eps: float = CERTIFICATE_EPS,
                       slack: float = 1e-12) -> Dict[str, object]:
    """Does the operational enclosure CONTAIN the oracle's, on one pair state?

    This is the separate check the root asked for.  It is NOT a disagreement
    count: the operational policy is EXPECTED to be wider, and the scientific
    question is only whether it ever fails to contain -- which would be an
    unsound narrowing and a real defect.
    """
    op_h = operational_hierarchy_bounds(ep_cand, ep_inc, tol=tol, eps=eps)
    op_s = operational_success_bounds(ep_cand, ep_inc)
    (or_h, or_s) = oracle_bounds(ep_cand, ep_inc)
    out: Dict[str, object] = {}
    for name, op, orc in (("hierarchy", op_h, or_h), ("success", op_s, or_s)):
        contains = (op[0] <= orc[0] + slack) and (op[1] >= orc[1] - slack)
        strictly_wider = ((orc[0] - op[0]) > slack) or ((op[1] - orc[1]) > slack)
        out[name] = {
            "operational": [float(op[0]), float(op[1])],
            "oracle": [float(orc[0]), float(orc[1])],
            "operational_contains_oracle": bool(contains),
            "operational_strictly_wider": bool(strictly_wider),
            "width_excess": float((op[1] - op[0]) - (orc[1] - orc[0])),
        }
    return out


def policy_constants() -> Dict[str, object]:
    """Every constant this adapter runs on, for a receipt to quote exactly."""
    return {
        "policy_id": POLICY_ID,
        "policy_version": POLICY_VERSION,
        "policy_label": POLICY_LABEL,
        "tol": OPERATIONAL_TOL,
        "certificate_eps": CERTIFICATE_EPS,
        "absolute_cost_tolerance": OPERATIONAL_ATOL,
        "score_range": [vband.SCORE_LOW, vband.SCORE_HIGH],
        "imports_the_monitored_source": False,
        "reimplements": "the observation policy only",
    }
