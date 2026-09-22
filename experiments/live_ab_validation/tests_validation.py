"""Test suite for the independent #12 validation band, enclosure and fixtures.

SOURCE DECLARATION -- files read while writing this module
----------------------------------------------------------
Read: reviews/arxiv_live_design_guidance.md, src/winstats.py, the issue-#12 task
text, and this directory's own ``vband.py`` / ``vfixtures.py`` / ``vgen.py`` /
``vrun.py``, plus, for the v2 event-schedule regression only,
reviews/cpu_v1_delivery_root_disposition.md section B and this directory's
PROTOCOL.md sections 7.1, 7.3 and 9.  NOT read, opened, grepped or imported:
the #11 monitor, enclosure and reference-rule modules, the #11 frozen protocol's
monitor sections, or anything else under that experiment's directory.

What is checked here, beyond replaying every deterministic fixture:

  * the enclosure algebra (starts full, never widens, refuses contradictions,
    collapses only on a certificate);
  * SOUNDNESS AND COMPLETENESS of the feasible-cost-order predicate, by
    exhibiting an explicit witness point for every value the predicate admits
    and by a brute-force grid sweep for every value it denies;
  * agreement of the partial-data enumeration with ``winstats.compare`` whenever
    both episodes are final, over an exhaustive tolerance-boundary grid and over
    randomised outcomes;
  * a RANDOMISED CONTAINMENT PROPERTY over many seeds: with a hidden ground
    truth per episode and only logically certain facts revealed, every recorded
    enclosure must contain that pair's true score, the running-sum interval must
    bracket the true enrollment-running mean at every look, no enclosure may
    ever widen, and the state must be invariant to reveal order and to repeated
    updates;
  * the COST/LATENCY ENCLOSURE PATH of PROTOCOL 2.5 and 4.3, driven end to end
    through the monitor on streams shaped like the frozen data-generating
    process: elapsed cost accrues, the hierarchy enclosure narrows and collapses
    to a point WITHOUT a certificate, containment holds at every look, and the
    path is shown to be live rather than merely specified;
  * the two guards added after the pre-registration audit -- the import graph
    that enforces the independence rule, and the PROTOCOL.md/cells.json
    agreement check -- each with MUTATION TESTS that deliberately break a copy
    of the input and assert the guard reports it.  A guard that has never fired
    is not known to be a guard.

The randomised programs here -- ``Program`` and ``CostPathProgram`` -- are a
correctness property test for the monitor.  They are NOT the issue-#12
simulation grid and they establish no operating characteristic: no miscoverage
rate, power or error rate is claimed anywhere in this file.  They use
``random.Random`` with fixed integer seeds and touch no namespace-0
``SeedSequence`` stream.  ``CostPathProgram`` is shaped like the frozen
data-generating process of PROTOCOL 4.1-4.3 but shortens the long delay block,
so it is not a cell of that grid at any horizon.  The eight-cell grid, its
ground-truth derivations and its Monte Carlo intervals are a separate,
pre-registered step, and PROTOCOL 0.1 discloses this file by name.

CPU only.  Stdlib ``unittest`` (there is no pytest in this environment), numpy.
Run: ``.venv/bin/python experiments/live_ab_validation/tests_validation.py``
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
import pathlib
import random
import re
import sys
import unittest
from typing import Dict, Hashable, List, Set, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vband  # noqa: E402
import vfixtures  # noqa: E402
import vgen  # noqa: E402
import vrun  # noqa: E402
from vband import (  # noqa: E402
    ALPHA_GATE, CONTINUE, DELTA, DEPLOY, Enclosure, EnclosureContradiction,
    Episode, N_MIN, ProtocolViolation, RETAIN_INCUMBENT, RHO, SwitchPhaseError,
    ValidationError, ValidationMonitor, cost_order_possibilities, decide,
    final_hierarchy_score, hierarchy_feasible_values, normal_mixture_band,
)
from winstats import compare, normal_mixture_radius  # noqa: E402

RTOL = vband.COST_RELATIVE_TOLERANCE
ATOL = vband.COST_ABSOLUTE_TOLERANCE
CAP = 100.0


# ---------------------------------------------------------------------------
# Independent reference helpers (a third transcription of the frozen endpoint)
# ---------------------------------------------------------------------------
def reference_scores(sa: int, ca: float, sb: int, cb: float,
                     rtol: float = RTOL, atol: float = ATOL) -> Tuple[int, int]:
    """(hierarchy, success) written straight from the frozen tier definition."""
    if sa != sb:
        h = 1 if sa > sb else -1
    elif sa == 0:
        h = 0                                   # joint failure: cost ineligible
    else:
        tol = atol + rtol * max(abs(ca), abs(cb))
        d = cb - ca                             # lower cost is better
        h = 0 if abs(d) <= tol else (1 if d > 0 else -1)
    return h, sa - sb


def order_at(ca: float, cb: float, rtol: float = RTOL,
             atol: float = ATOL) -> int:
    tol = atol + rtol * max(abs(ca), abs(cb))
    d = cb - ca
    return 0 if abs(d) <= tol else (1 if d > 0 else -1)


def witness_point(value: int, a_lo: float, a_hi: float, b_lo: float, b_hi: float
                  ) -> Tuple[float, float]:
    """An explicit point of the cost box that should realise ``value``."""
    if value == 1:
        return (a_lo, b_hi)
    if value == -1:
        return (a_hi, b_lo)
    if a_hi >= b_lo and b_hi >= a_lo:           # boxes overlap
        m = max(a_lo, b_lo)
        return (m, m)
    if a_hi < b_lo:
        return (a_hi, b_lo)
    return (a_lo, b_hi)


def brute_orders(a_lo: float, a_hi: float, b_lo: float, b_hi: float,
                 grid: int = 41) -> Set[int]:
    a_pts = np.linspace(a_lo, a_hi, grid) if a_hi > a_lo else np.array([a_lo])
    b_pts = np.linspace(b_lo, b_hi, grid) if b_hi > b_lo else np.array([b_lo])
    return {order_at(float(ca), float(cb)) for ca in a_pts for cb in b_pts}


# ---------------------------------------------------------------------------
# Randomised program generator with a hidden ground truth
# ---------------------------------------------------------------------------
class Program:
    """A randomly generated enrollment/reveal stream with a hidden truth.

    Every emitted fact is LOGICALLY CERTAIN given the hidden truth, so any
    containment failure is a defect in the enclosure arithmetic rather than a
    badly generated stream.  A slot whose destiny is ``timeout`` has its truth
    REDEFINED by the frozen cap rule to (failure, full cap); nothing is dropped.
    """

    def __init__(self, seed: int, n_pairs: int, cap: float = CAP) -> None:
        rng = random.Random(seed)
        self.cap = cap
        self.enroll_events: List[tuple] = []
        self.reveal_events: List[tuple] = []
        self.truth: Dict[Hashable, Tuple[int, float]] = {}
        self.pair_truth: Dict[Hashable, Tuple[int, int]] = {}
        self.pairs: List[Tuple[str, str, str, str]] = []

        for i in range(n_pairs):
            pid, coin = f"p{i}", rng.choice(("AB", "BA"))
            s_first, s_second = f"s{i}a", f"s{i}b"
            self.pairs.append((pid, coin, s_first, s_second))
            self.enroll_events.append(("enroll", pid, coin, s_first, s_second))

            base_cost = rng.uniform(0.5, cap * 0.9)
            for slot in (s_first, s_second):
                destiny = rng.choices(("final", "timeout", "pending"),
                                      weights=(0.7, 0.1, 0.2))[0]
                if destiny == "timeout":
                    truth = (0, cap)
                else:
                    success = 1 if rng.random() < 0.6 else 0
                    if rng.random() < 0.4:      # straddle the 5% tolerance
                        cost = min(cap, max(0.0,
                                            base_cost * (1.0 + rng.uniform(-0.09, 0.09))))
                    else:
                        cost = rng.uniform(0.0, cap)
                    truth = (success, cost)
                self.truth[slot] = truth
                self._emit_facts(rng, slot, destiny, truth)

            slot_a, slot_b = ((s_first, s_second) if coin == "AB"
                              else (s_second, s_first))
            sa, ca = self.truth[slot_a]
            sb, cb = self.truth[slot_b]
            self.pair_truth[pid] = reference_scores(sa, ca, sb, cb)

        rng.shuffle(self.reveal_events)
        self.rng = rng

    def _emit_facts(self, rng: random.Random, slot: str, destiny: str,
                    truth: Tuple[int, float]) -> None:
        success, cost = truth
        for _ in range(rng.randint(0, 3)):
            self.reveal_events.append(("elapsed", slot, rng.uniform(0.0, cost)))
        if rng.random() < 0.5:
            self.reveal_events.append(
                ("succeed", slot) if success == 1 else ("fail", slot))
        if destiny != "timeout" and rng.random() < 0.3:
            self.reveal_events.append(
                ("cost_upper", slot, rng.uniform(cost, self.cap)))
        if destiny == "final":
            self.reveal_events.append(("final", slot, success, cost))
        elif destiny == "timeout":
            self.reveal_events.append(("timeout", slot))

    def script(self, look_every: int = 4) -> List[tuple]:
        events = list(self.enroll_events)
        for k, ev in enumerate(self.reveal_events):
            events.append(ev)
            if look_every and (k + 1) % look_every == 0:
                events.append(("look", f"L{k+1}"))
        events.append(("look", "final"))
        return events

    def true_mean(self, score_index: int) -> float:
        vals = [v[score_index] for v in self.pair_truth.values()]
        return sum(vals) / len(vals) if vals else 0.0


# ===========================================================================
class TestEnclosureAlgebra(unittest.TestCase):

    def test_starts_at_full_range(self):
        e = Enclosure.full()
        self.assertEqual((e.lo, e.hi, e.certified), (-1.0, 1.0, False))

    def test_narrow_never_widens_and_is_idempotent(self):
        e = Enclosure.full().narrow(-0.5, 0.5)
        self.assertEqual((e.lo, e.hi), (-0.5, 0.5))
        self.assertEqual(e.narrow(-1.0, 1.0).as_tuple(), e.as_tuple())
        self.assertEqual(e.narrow(-0.5, 0.5).as_tuple(), e.as_tuple())
        tighter = e.narrow(0.0, 0.25)
        self.assertEqual((tighter.lo, tighter.hi), (0.0, 0.25))
        self.assertLessEqual(tighter.width, e.width)

    def test_contradictory_narrow_raises(self):
        e = Enclosure.full().narrow(0.5, 1.0)
        with self.assertRaises(EnclosureContradiction):
            e.narrow(-1.0, 0.0)

    def test_collapse_requires_containment_and_is_certified(self):
        e = Enclosure.full().narrow(0.0, 1.0)
        c = e.collapse(1.0)
        self.assertTrue(c.certified)
        self.assertEqual((c.lo, c.hi), (1.0, 1.0))
        self.assertEqual(c.collapse(1.0).as_tuple(), c.as_tuple())
        with self.assertRaises(EnclosureContradiction):
            e.collapse(-1.0)
        with self.assertRaises(EnclosureContradiction):
            c.collapse(0.0)

    def test_point_resolved_is_not_certified(self):
        e = Enclosure.full().narrow(1.0, 1.0)
        self.assertTrue(e.resolved)
        self.assertFalse(e.certified)

    def test_scores_stay_in_the_bounded_range(self):
        with self.assertRaises(ValidationError):
            Enclosure(-2.0, 1.0)


class TestEpisodeFacts(unittest.TestCase):

    def test_pending_episode_knows_nothing(self):
        ep = Episode.pending("x", CAP)
        self.assertEqual(ep.success_set(), (0, 1))
        self.assertEqual((ep.cost_lo, ep.cost_hi), (0.0, CAP))
        self.assertFalse(ep.final)

    def test_absence_of_failure_is_not_success(self):
        ep = Episode.pending("x", CAP).with_elapsed_cost(90.0)
        self.assertEqual(ep.success_set(), (0, 1))

    def test_monotone_facts_are_idempotent(self):
        ep = Episode.pending("x", CAP).with_elapsed_cost(10.0).with_success()
        self.assertIs(ep.with_elapsed_cost(10.0), ep)
        self.assertIs(ep.with_elapsed_cost(4.0), ep)
        self.assertIs(ep.with_success(), ep)
        self.assertIs(ep.with_cost_upper(CAP), ep)

    def test_contradictions_raise(self):
        ep = Episode.pending("x", CAP).with_success()
        with self.assertRaises(EnclosureContradiction):
            ep.with_failure()
        with self.assertRaises(EnclosureContradiction):
            ep.with_elapsed_cost(CAP + 1.0)
        fin = ep.finalized(1, 20.0)
        with self.assertRaises(EnclosureContradiction):
            fin.finalized(1, 21.0)
        self.assertIs(fin.finalized(1, 20.0), fin)

    def test_final_outside_established_bounds_raises(self):
        ep = Episode.pending("x", CAP).with_elapsed_cost(40.0)
        with self.assertRaises(EnclosureContradiction):
            ep.finalized(1, 30.0)

    def test_timeout_is_the_frozen_cap_rule(self):
        ep = Episode.pending("x", 50.0).with_elapsed_cost(30.0).timed_out()
        self.assertEqual((ep.success_lo, ep.success_hi), (0, 0))
        self.assertEqual((ep.cost_lo, ep.cost_hi), (50.0, 50.0))
        self.assertTrue(ep.final)


class TestCostOrderPredicate(unittest.TestCase):
    """Soundness and completeness of the feasible-cost-order enumeration."""

    def _boxes(self, n: int = 400, seed: int = 20260919):
        rng = random.Random(seed)
        boxes = [(0.0, 0.0, 0.0, 0.0), (10.0, 10.0, 20.0, 20.0),
                 (95.0, 95.0, 100.0, 100.0), (0.0, CAP, 0.0, CAP),
                 (10.0, 10.0, 80.0, 100.0), (40.0, 60.0, 41.0, 59.0),
                 (0.0, 1e-9, 0.0, 1e-9)]
        for _ in range(n):
            a_lo = rng.uniform(0.0, CAP)
            a_hi = min(CAP, a_lo + rng.choice((0.0, 0.1, 1.0, 5.0, 40.0)))
            b_lo = rng.uniform(0.0, CAP)
            b_hi = min(CAP, b_lo + rng.choice((0.0, 0.1, 1.0, 5.0, 40.0)))
            boxes.append((a_lo, a_hi, b_lo, b_hi))
        return boxes

    def test_every_admitted_value_has_a_witness(self):
        checked = 0
        for a_lo, a_hi, b_lo, b_hi in self._boxes():
            vals = cost_order_possibilities(a_lo, a_hi, b_lo, b_hi)
            self.assertTrue(vals)
            for v in vals:
                ca, cb = witness_point(v, a_lo, a_hi, b_lo, b_hi)
                self.assertTrue(a_lo - 1e-12 <= ca <= a_hi + 1e-12)
                self.assertTrue(b_lo - 1e-12 <= cb <= b_hi + 1e-12)
                self.assertEqual(
                    order_at(ca, cb), v,
                    f"box {(a_lo, a_hi, b_lo, b_hi)} admits {v} with no witness")
                checked += 1
        self.assertGreater(checked, 400)

    def test_no_reachable_value_is_denied(self):
        for a_lo, a_hi, b_lo, b_hi in self._boxes():
            vals = cost_order_possibilities(a_lo, a_hi, b_lo, b_hi)
            missed = brute_orders(a_lo, a_hi, b_lo, b_hi) - vals
            self.assertFalse(
                missed, f"box {(a_lo, a_hi, b_lo, b_hi)} denies reachable {missed}")

    def test_degenerate_box_matches_the_point_rule(self):
        for ca in (0.0, 1.0, 10.0, 95.0, 100.0):
            for cb in (0.0, 1.0, 10.0, 95.0, 100.0):
                self.assertEqual(cost_order_possibilities(ca, ca, cb, cb),
                                 {order_at(ca, cb)})

    def test_rejects_unusable_tolerance(self):
        with self.assertRaises(ValidationError):
            cost_order_possibilities(0.0, 1.0, 0.0, 1.0, rtol=1.0)


class TestAgreementWithCompare(unittest.TestCase):
    """When both episodes are final the enumeration must equal ``compare``."""

    def test_exhaustive_tolerance_boundary_grid(self):
        costs = [0.0, 1.0, 5.0, 19.0, 19.9, 20.0, 21.0, 90.0, 94.9, 95.0,
                 95.1, 100.0]
        checked = 0
        for sa in (0, 1):
            for sb in (0, 1):
                for ca in costs:
                    for cb in costs:
                        ep_a = Episode.pending("a", CAP).finalized(sa, ca)
                        ep_b = Episode.pending("b", CAP).finalized(sb, cb)
                        want_h, want_s = reference_scores(sa, ca, sb, cb)
                        self.assertEqual(final_hierarchy_score(ep_a, ep_b), want_h)
                        self.assertEqual(
                            hierarchy_feasible_values(ep_a, ep_b), frozenset({want_h}))
                        self.assertEqual(
                            vband.success_bounds(ep_a, ep_b),
                            (float(want_s), float(want_s)))
                        checked += 1
        self.assertEqual(checked, 2 * 2 * len(costs) ** 2)

    def test_compare_primitive_agrees_with_the_reference(self):
        rng = random.Random(7)
        tiers = list(vband.TIERS)
        for _ in range(2000):
            sa, sb = rng.randint(0, 1), rng.randint(0, 1)
            ca, cb = rng.uniform(0, CAP), rng.uniform(0, CAP)
            a = np.array([[float(sa), ca]])
            b = np.array([[float(sb), cb]])
            eligible = np.array([[True, bool(sa == 1 and sb == 1)]])
            got, _tier = compare(a, b, tiers, eligible=eligible)
            want, _ = reference_scores(sa, ca, sb, cb)
            self.assertEqual(int(got[0]), want)

    def test_joint_failure_ignores_cost(self):
        ep_a = Episode.pending("a", CAP).finalized(0, 1.0)
        ep_b = Episode.pending("b", CAP).finalized(0, 100.0)
        self.assertEqual(final_hierarchy_score(ep_a, ep_b), 0)


class TestBandAndDecision(unittest.TestCase):

    def test_radius_uses_variance_process_n(self):
        for n in (1, 2, 3, 6, 100, 500, 2000):
            got = vband.radius_from_formula(n)
            want = float(normal_mixture_radius(n, alpha=ALPHA_GATE, rho=RHO,
                                               variance_process=n))
            self.assertAlmostEqual(got, want, places=12)
            self.assertAlmostEqual(got, vfixtures.literal_radius(n), places=12)

    def test_band_denominator_and_clip(self):
        lowers = [1.0, 1.0, -1.0, -1.0]
        uppers = [1.0, 1.0, 1.0, 1.0]
        band = normal_mixture_band(lowers, uppers, 4)
        self.assertEqual(band.n, 4)
        self.assertEqual(band.mean_lower, 0.0)
        self.assertEqual(band.mean_upper, 1.0)
        self.assertEqual((band.lower, band.upper), (-1.0, 1.0))
        n = 2000
        interior = normal_mixture_band([0.5] * n, [0.6] * n, n)
        r = vfixtures.literal_radius(n)
        self.assertAlmostEqual(interior.lower, 0.5 - r, places=12)
        self.assertAlmostEqual(interior.upper, 0.6 + r, places=12)

    def test_zero_prefix_shows_the_full_range(self):
        band = normal_mixture_band([], [], 0)
        self.assertEqual((band.lower, band.upper), (-1.0, 1.0))
        self.assertEqual(band.n, 0)
        self.assertTrue(math.isinf(band.radius))
        self.assertEqual(decide(band, band), CONTINUE)

    def test_decision_rule_boundaries(self):
        b = vfixtures._band_of
        n = 200
        self.assertEqual(decide(b("h", n, .1, .4), b("s", n, -.02, .3)), DEPLOY)
        self.assertEqual(decide(b("h", n, .1, .4), b("s", n, -DELTA, .3)), CONTINUE)
        self.assertEqual(decide(b("h", n, 0.0, .4), b("s", n, .1, .3)), CONTINUE)
        self.assertEqual(decide(b("h", n, -.4, -1e-9), b("s", n, -.9, -.1)),
                         RETAIN_INCUMBENT)
        self.assertEqual(decide(b("h", n, -.4, 0.0), b("s", n, -.9, -.1)), CONTINUE)
        self.assertEqual(decide(b("h", N_MIN - 1, .9, .95),
                                b("s", N_MIN - 1, .9, .95)), CONTINUE)
        self.assertEqual(decide(b("h", N_MIN, .9, .95), b("s", N_MIN, .9, .95)),
                         DEPLOY)

    def test_same_look_conjunction_is_enforced(self):
        b = vfixtures._band_of
        with self.assertRaises(ProtocolViolation):
            decide(b("h", 150, .5, .9), b("s", 120, .5, .9))

    def test_alpha_allocation(self):
        self.assertEqual(vband.PROGRAM_ALPHA, 0.05)
        self.assertEqual(vband.N_TRIALS, 4)
        self.assertEqual(vband.ALPHA_PER_TRIAL, 0.0125)
        self.assertEqual(vband.ALPHA_GATE, 0.00625)
        self.assertAlmostEqual(
            vband.ALPHA_GATE * vband.GATES_PER_TRIAL * vband.N_TRIALS,
            vband.PROGRAM_ALPHA, places=15)


class TestProtocolGuards(unittest.TestCase):

    def test_enrollment_and_slot_uniqueness(self):
        mon = ValidationMonitor()
        mon.enroll("a", "AB", "x1", "x2")
        with self.assertRaises(ProtocolViolation):
            mon.enroll("a", "AB", "x3", "x4")
        with self.assertRaises(ProtocolViolation):
            mon.enroll("b", "AB", "x1", "x5")
        with self.assertRaises(ProtocolViolation):
            mon.enroll("c", "AB", "x6", "x6")
        with self.assertRaises(ProtocolViolation):
            mon.observe_success("x9")

    def test_switch_stops_randomisation_but_not_resolution(self):
        mon = ValidationMonitor()
        mon.enroll("a", "AB", "x1", "x2")
        mon.switch()
        with self.assertRaises(SwitchPhaseError):
            mon.enroll("b", "AB", "x3", "x4")
        mon.finalize("x1", 1, 10.0)
        mon.finalize("x2", 0, 20.0)
        mon.record_followup_arrival("f1")
        self.assertEqual(mon.look("post").n_enrolled, 1)
        with self.assertRaises(ProtocolViolation):
            mon.record_followup_arrival("x1")

    def test_orientation_follows_the_pre_enrolled_coin(self):
        mon = ValidationMonitor()
        mon.enroll("ab", "AB", "u1", "u2")
        mon.enroll("ba", "BA", "v1", "v2")
        self.assertEqual(mon.pairs[0].arm_slots(), ("u1", "u2"))
        self.assertEqual(mon.pairs[1].arm_slots(), ("v2", "v1"))

    def test_audit_requires_history(self):
        mon = ValidationMonitor()
        with self.assertRaises(ValidationError):
            mon.audit_containment()


class TestFixtures(unittest.TestCase):
    """Replay every deterministic acceptance fixture of root item 1."""

    def test_every_fixture_passes(self):
        results = vfixtures.run_all()
        self.assertEqual(len(results), len(vfixtures.ALL_FIXTURES))
        self.assertGreaterEqual(len(results), 17)
        for name, failures in results:
            with self.subTest(fixture=name):
                self.assertEqual(failures, [], f"{name}: {failures}")

    def test_the_register_is_unique_and_ordered(self):
        names = [c.name for c in vfixtures.ALL_FIXTURES]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names, sorted(names), "fixture ids must stay in id order")


# ===========================================================================
class TestImportGraphIndependence(unittest.TestCase):
    """PROTOCOL 12.1 item 4: the only MECHANICAL guard on the independence rule.

    Before the pre-registration audit this test did not exist and independence
    rested entirely on docstring declarations.
    """

    def test_no_module_of_the_forbidden_tree_is_ever_loaded(self):
        failures = vfixtures._f16_import_graph_independence()
        self.assertEqual(failures, [], f"import graph: {failures}")

    # The offending sources below are BUILT from fragments so that this file
    # does not itself contain the literals the guard forbids.  Assembling them
    # is the point: a guard is only known to work once it has fired.
    _LAB = "lab_" + "monitor"
    _ENC = "lab_" + "enclosure"
    _TREE = "experiments/live_" + "ab/"

    def test_the_pinned_tree_is_present_and_the_probe_would_catch_it(self):
        """The pinned #11 copy now sits inside this directory, so the dynamic
        half of F16 has something real to guard against.  This checks the
        probe's path-prefix logic against the actual layout WITHOUT importing
        or reading any pinned module: only directory entries are listed.
        """
        pinned = vfixtures.HERE / "pinned"
        if not pinned.is_dir():
            self.skipTest("the coordinator has not deposited pinned/ yet")
        modules = sorted(p.name for p in pinned.glob("*.py"))
        self.assertTrue(modules, "pinned/ holds no python module to guard against")
        prefix = str(pinned) + os.sep
        for name in modules:
            self.assertTrue(
                str(pinned / name).startswith(prefix),
                f"the F16 probe prefix would not match {name}")
        # and nothing under pinned/ is loaded in THIS interpreter
        for mod in list(sys.modules.values()):
            f = getattr(mod, "__file__", None)
            self.assertFalse(f and f.startswith(prefix),
                             f"a pinned module is already imported: {f}")

    def test_the_static_scanner_reports_a_forbidden_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "offender.py")
            with open(p, "w") as fh:
                fh.write(f"import {self._LAB}\n")
            failures = vfixtures.scan_sources_for_forbidden_paths(
                tmp, require_at_least=1)
        self.assertTrue(any(f"imports {self._LAB}" in f for f in failures),
                        f"scanner missed a forbidden import: {failures}")

    def test_the_static_scanner_reports_a_forbidden_from_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "offender.py"), "w") as fh:
                fh.write(f"from {self._ENC} import PairEnclosure\n")
            failures = vfixtures.scan_sources_for_forbidden_paths(
                tmp, require_at_least=1)
        self.assertTrue(any(f"imports from {self._ENC}" in f for f in failures),
                        f"scanner missed a forbidden from-import: {failures}")

    def test_the_static_scanner_reports_a_path_literal_and_a_dynamic_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "offender.py"), "w") as fh:
                fh.write(f'"""A docstring may name {self._TREE} freely."""\n'
                         f'import importlib\n'
                         f'PATH = "{self._TREE}{self._LAB}.py"\n'
                         f'm = importlib.import_module("{self._LAB}")\n')
            failures = vfixtures.scan_sources_for_forbidden_paths(
                tmp, require_at_least=1)
        joined = " ".join(failures)
        self.assertIn("outside a docstring", joined)
        self.assertIn("import_module", joined)
        self.assertNotIn(":1 ", joined, "the docstring line must stay exempt")

    def test_the_marker_exempts_only_the_line_it_is_on(self):
        import tempfile
        marker = "IMPORT-GUARD" "-LITERAL"
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "offender.py"), "w") as fh:
                fh.write(f'A = "{self._TREE}x.py"  # {marker}\n'
                         f'B = "{self._TREE}y.py"\n')
            failures = vfixtures.scan_sources_for_forbidden_paths(
                tmp, require_at_least=1)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn(":2", failures[0])


# ===========================================================================
class TestProtocolConfigAgreement(unittest.TestCase):
    """PROTOCOL's header claims cells.json is normative and asserted. Check it.

    The claim was false before the audit: no such check existed, and the two
    files had already drifted on the fixture register.
    """

    def setUp(self):
        self.text = vfixtures.PROTOCOL_PATH.read_text()
        self.cfg = json.loads(vfixtures.CELLS_PATH.read_text())

    def _check(self, text=None, cfg=None):
        return vfixtures.check_protocol_config_agreement(
            self.text if text is None else text,
            self.cfg if cfg is None else cfg)

    def test_the_two_documents_agree(self):
        self.assertEqual(self._check(), [])

    def test_a_changed_band_endpoint_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        row = cfg["analytic_reachability"]["expected_path_band_endpoints_Lh_Uh_Ls"]
        row["C5"]["500"][0] += 0.01
        failures = self._check(cfg=cfg)
        self.assertTrue(any("6.3 C5 500 L_h" in f for f in failures), failures)

    def test_a_changed_gate_prefix_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["analytic_reachability"]["expected_path_gate_opening_prefix"]["C7"]["DEPLOY"] = 694
        failures = self._check(cfg=cfg)
        self.assertTrue(any("6.2 C7 DEPLOY" in f for f in failures), failures)

    def test_a_gate_prefix_becoming_never_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["analytic_reachability"]["expected_path_gate_opening_prefix"]["C5"]["L_h>0"] = None
        failures = self._check(cfg=cfg)
        self.assertTrue(any("6.2 C5 L_h>0" in f for f in failures), failures)

    def test_a_changed_parameter_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["parameters"]["delta"] = 0.05
        failures = self._check(cfg=cfg)
        self.assertTrue(any("2.1 delta" in f for f in failures), failures)

    def test_a_changed_atom_cost_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["outcome_atoms"]["definition"][0]["c_candidate"] = 12.0
        failures = self._check(cfg=cfg)
        self.assertTrue(any("4.1 BB+ c_candidate" in f for f in failures), failures)

    def test_a_changed_weight_breaks_both_the_table_and_the_enumeration(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["outcome_laws"]["L2"]["weights"]["BB+"] = 1600
        failures = self._check(cfg=cfg)
        self.assertTrue(any("4.1 L2 w[BB+]" in f for f in failures), failures)
        self.assertTrue(any("mu_h by enumeration" in f or "weights sum to" in f
                            for f in failures), failures)

    def test_a_changed_cost_path_fraction_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["analytic_reachability"]["expected_cost_enclosure_exercise"]["C4"]["500"][0] = 0.01
        failures = self._check(cfg=cfg)
        self.assertTrue(any("6.4 C4 500 point" in f for f in failures), failures)

    def test_a_drifting_fixture_register_is_caught(self):
        """The exact drift the audit found: cells.json renumbered, code not."""
        cfg = copy.deepcopy(self.cfg)
        cfg["fixtures"]["list"][0]["id"] = "F0"
        failures = self._check(cfg=cfg)
        self.assertTrue(any("cells.json register" in f for f in failures), failures)

    def test_a_dropped_protocol_row_is_caught(self):
        text = "\n".join(ln for ln in self.text.splitlines()
                         if not ln.startswith("| `C5` | -0."))
        failures = self._check(text=text)
        self.assertTrue(any("6.3" in f and "C5" in f for f in failures), failures)

    def test_a_changed_protocol_number_is_caught(self):
        text = self.text.replace("| `C8` `L4/A` | 137 | 566 | never | **566** |",
                                 "| `C8` `L4/A` | 137 | 566 | never | **560** |")
        self.assertNotEqual(text, self.text, "the 6.2 C8 row moved; fix this test")
        failures = self._check(text=text)
        self.assertTrue(any("6.2 C8 DEPLOY" in f for f in failures), failures)

    def test_a_missing_hash_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["provenance"]["pinned_primitive"]["sha256"] = "0" * 64
        failures = self._check(cfg=cfg)
        self.assertTrue(any("winstats.py" in f for f in failures), failures)

    # -- the tables PREREG_CHECK_2 N.2 found unguarded ---------------------
    # Each of the five tables below was compared against NOTHING: a mutation
    # sweep over every numeric token of every table row of PROTOCOL.md reported
    # 0 of 44 changes to the section 2.5 table, 0 of 7 to the seed namespaces,
    # 0 of 9 to the decision-level bounds, and 4 of 12 to the budget ladder's
    # grid column.  One test per table, in both directions where the table has
    # two sides that can drift apart.

    def test_a_changed_enclosure_row_is_caught(self):
        """Section 2.5 decides ground truth for the whole cost-path design."""
        cfg = copy.deepcopy(self.cfg)
        cfg["enclosure_rules"]["protocol_2_5_rows"][3]["hierarchy"] = [-1.0, 1.0]
        failures = self._check(cfg=cfg)
        self.assertTrue(any("2.5" in f and "hierarchy" in f for f in failures),
                        failures)

    def test_a_changed_enclosure_row_in_the_protocol_is_caught(self):
        old = "| candidate revealed, `s_C = 1`, both infeasible | `[+1, +1]` | `[0, +1]` |"
        new = "| candidate revealed, `s_C = 1`, both infeasible | `[0, +1]` | `[0, +1]` |"
        self.assertIn(old, self.text, "the 2.5 table moved; fix this test")
        failures = self._check(text=self.text.replace(old, new))
        self.assertTrue(any("2.5" in f and "both infeasible" in f
                            for f in failures), failures)

    def test_an_enclosure_row_inconsistent_with_the_coarse_states_is_caught(self):
        """The ten rows must refine the six states, not contradict them."""
        cfg = copy.deepcopy(self.cfg)
        cfg["enclosure_rules"]["states"][1]["hierarchy"] = [-1.0, 1.0]
        failures = self._check(cfg=cfg)
        self.assertTrue(any("enclosure_rules.states" in f for f in failures),
                        failures)

    def test_a_changed_seed_namespace_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["seeding"]["namespaces"]["1"]["seeds_reused"] = True
        failures = self._check(cfg=cfg)
        self.assertTrue(any("5 namespace 1 reuse" in f for f in failures), failures)

    def test_a_changed_master_seed_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["seeding"]["master_seed"] = 1220260920
        failures = self._check(cfg=cfg)
        self.assertTrue(any("master seed" in f for f in failures), failures)

    def test_a_changed_decision_level_bound_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["reported_quantities"]["decision_level"]["family_any_erroneous"][
            "nominal_bound"] = 0.10
        failures = self._check(cfg=cfg)
        self.assertTrue(any("9.2 family_any_erroneous nominal bound" in f
                            for f in failures), failures)

    def test_a_changed_decision_level_definition_is_caught(self):
        old = "| `false_harm` | trial | trial issues RETAIN_INCUMBENT and `mu_h >= 0` | `0.00625` |"
        new = "| `false_harm` | trial | trial issues RETAIN_INCUMBENT and `mu_h >= 1` | `0.00625` |"
        self.assertIn(old, self.text, "the 9.2 table moved; fix this test")
        failures = self._check(text=self.text.replace(old, new))
        self.assertTrue(any("9.2 false_harm definition" in f for f in failures),
                        failures)

    def test_a_changed_budget_grid_column_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["budget"]["ladder"][0]["programs"]["C3"] = 2000
        cfg["budget"]["ladder"][0]["programs_total"] = 25000
        failures = self._check(cfg=cfg)
        self.assertTrue(any("8.2 T1 grid column" in f for f in failures), failures)

    def test_a_changed_budget_horizon_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["budget"]["ladder"][3]["N_max"] = 2000
        failures = self._check(cfg=cfg)
        self.assertTrue(any("8.2 T4 N_max" in f for f in failures), failures)

    def test_a_changed_look_count_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["parameters"]["decision_eligible_looks"] = 1901
        failures = self._check(cfg=cfg)
        self.assertTrue(any("7.1 decision-eligible" in f for f in failures),
                        failures)

    def test_a_look_count_that_no_longer_follows_from_N_max_is_caught(self):
        """The derivation, not only the transcription: both sides can be wrong."""
        cfg = copy.deepcopy(self.cfg)
        text = self.text.replace("| looks per trial | 2,001 -",
                                 "| looks per trial | 2,002 -")
        self.assertNotEqual(text, self.text, "the 7.1 row moved; fix this test")
        cfg["parameters"]["looks_per_trial"] = 2002
        failures = self._check(text=text, cfg=cfg)
        self.assertTrue(any("looks_per_trial = N_max + 1" in f for f in failures),
                        failures)

    def test_a_changed_horizon_header_is_caught(self):
        old = "| law | `n=100` unresolved / unrevealed | `n=500` | `n=2000` |"
        self.assertIn(old, self.text, "the 6.1 header moved; fix this test")
        failures = self._check(text=self.text.replace(
            old, "| law | `n=100` unresolved / unrevealed | `n=600` | `n=2000` |"))
        self.assertTrue(any("6.1 horizon headers" in f for f in failures), failures)

    def test_a_changed_cell_row_label_is_caught(self):
        old = "| `C6` `L3/A` |"
        self.assertIn(old, self.text, "the 6.2 table moved; fix this test")
        failures = self._check(text=self.text.replace(old, "| `C6` `L3/N` |"))
        self.assertTrue(any("6.2 C6 row label" in f for f in failures), failures)

    def test_a_changed_comparison_tolerance_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["comparison_to_live_ab"]["compared_at_every_look"][
            "per_pair_enclosure_endpoints"] = "absolute difference <= 1e-9"
        failures = self._check(cfg=cfg)
        self.assertTrue(any("12.2 per-pair enclosure tolerance" in f
                            for f in failures), failures)

    def test_a_changed_label_bijection_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["comparison_to_live_ab"]["decision_label_bijection"]["map"][1][
            "validation"] = "RETAIN_INCUMBENT"
        failures = self._check(cfg=cfg)
        self.assertTrue(any("12.2 bijection" in f for f in failures), failures)

    def test_a_stale_fixture_range_is_caught(self):
        """How the B.2 register drift spread: a range nobody recounted."""
        cfg = copy.deepcopy(self.cfg)
        cfg["fixtures"]["deposited_to"] = cfg["fixtures"]["deposited_to"].replace(
            "F01..F18", "F01..F17")
        failures = self._check(cfg=cfg)
        self.assertTrue(any("fixture range" in f for f in failures), failures)

    def test_a_changed_repository_commit_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["provenance"]["repo_commit_at_writing"] = "0" * 40
        failures = self._check(cfg=cfg)
        self.assertTrue(any("header commit" in f for f in failures), failures)


def _table_row_lines(text: str):
    """Every markdown table data row of ``text``, as ``(index, line)``."""
    out = []
    for i, line in enumerate(text.splitlines(keepends=True)):
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|") and len(s) > 1):
            continue
        cells = [c.strip() for c in s[1:-1].split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        out.append((i, line))
    return out


def _perturb(token: str) -> str:
    """A change larger than every tolerance ``check_...`` uses (the largest is 5e-3)."""
    raw = token.replace(",", "")
    try:
        value = float(raw)
    except ValueError:                                      # pragma: no cover
        return token
    if "." in raw:
        places = len(raw.split(".")[1])
        out = f"{value + max(10.0 ** -places, abs(value) * 0.1, 0.02):.{places}f}"
    else:
        out = str(int(value) + (3 if abs(value) < 1 else abs(int(value)) // 10 + 1))
        if "," in token:
            out = f"{int(out):,}"
    return out if out != token else token + "1"


def f15_mutation_coverage(text: str, cfg: dict):
    """Perturb every numeric token of every table row; report what F15 catches.

    This is the measurement PREREG_CHECK_2 N.2 made by hand, kept in the repo so
    the claim in PROTOCOL 11 about what F15 covers is a number anyone can
    reproduce rather than a sentence.  Returns ``(caught, missed, by_section)``
    where ``by_section`` maps a section number to ``[caught, missed]``.
    """
    base = set(vfixtures.check_protocol_config_agreement(text, cfg))
    lines = text.splitlines(keepends=True)
    section, sections = "header", []
    for line in lines:
        hit = re.match(r"^#{2,4} ([0-9]+(?:\.[0-9]+)?)", line)
        if hit:
            section = hit.group(1)
        sections.append(section)
    caught = missed = 0
    by_section: dict = {}
    for i, line in _table_row_lines(text):
        for hit in list(re.finditer(vfixtures._NUM_RE, line)):
            new = _perturb(hit.group(0))
            if new == hit.group(0):
                continue                                    # pragma: no cover
            mutated = lines[:i] + [line[:hit.start()] + new + line[hit.end():]] \
                + lines[i + 1:]
            got = set(vfixtures.check_protocol_config_agreement("".join(mutated), cfg))
            tally = by_section.setdefault(sections[i], [0, 0])
            if got - base:
                caught += 1
                tally[0] += 1
            else:
                missed += 1
                tally[1] += 1
    return caught, missed, by_section


class TestF15MutationCoverage(unittest.TestCase):
    """How much of PROTOCOL.md F15 actually guards, measured, not asserted.

    PREREG_CHECK_2 N.2 ran this sweep by hand and found whole frozen tables
    unguarded while sections 11 and 13 claimed "every numeric table": 384 of 595
    mutations reported, with 0 of 44 changes to the section 2.5 enclosure table,
    0 of 7 to the seed namespaces, 0 of 9 to the decision-level bounds and 4 of
    12 to the budget ladder's grid column.  The sweep now lives here, so the
    claim degrades into a failing test rather than into prose.
    """

    #: sections whose tables carry only frozen values, where nothing may be missed
    FULLY_GUARDED = ("2.2", "2.5", "4.2", "5", "6.1", "6.3", "6.4", "7.1", "8.2",
                     "9.1", "9.3")
    FLOOR = 0.80

    @classmethod
    def setUpClass(cls):
        cls.caught, cls.missed, cls.by_section = f15_mutation_coverage(
            vfixtures.PROTOCOL_PATH.read_text(),
            json.loads(vfixtures.CELLS_PATH.read_text()))

    def test_the_tables_of_frozen_values_have_no_unguarded_number(self):
        for section in self.FULLY_GUARDED:
            with self.subTest(section=section):
                tally = self.by_section.get(section)
                self.assertIsNotNone(tally, f"section {section} has no table rows")
                self.assertEqual(tally[1], 0,
                                 f"section {section}: {tally[1]} numeric tokens "
                                 f"can be changed without F15 noticing")

    def test_overall_coverage_stays_above_the_floor(self):
        total = self.caught + self.missed
        self.assertGreater(total, 500, "the sweep found too few mutations to mean "
                                       "anything")
        self.assertGreaterEqual(
            self.caught / total, self.FLOOR,
            f"F15 catches {self.caught}/{total} mutations, below the "
            f"{self.FLOOR:.0%} floor this suite holds it to")

    def test_the_sweep_can_fail(self):
        """A coverage measurement that cannot report a gap measures nothing."""
        text = vfixtures.PROTOCOL_PATH.read_text()
        cfg = json.loads(vfixtures.CELLS_PATH.read_text())
        cfg["enclosure_rules"].pop("protocol_2_5_rows")
        _, _, by_section = f15_mutation_coverage(text, cfg)
        self.assertGreater(by_section.get("2.5", [0, 0])[1], 0,
                           "removing the 2.5 twin left the sweep reporting no gap")


class TestPinnedFileHashes(unittest.TestCase):
    """F18: the pins must be recomputed from the files, not from each other.

    PREREG_CHECK_2 N.1.  The check this replaces asserted that the same 64-hex
    token appeared in PROTOCOL.md and in cells.json, which two documents can
    satisfy while both disagree with the file on disk -- and did: the pin on
    the #11 vocabulary document was stale by one revision of that document and
    nothing reported it.  Every test below breaks one recorded pin and asserts
    the fixture says so, because a hash check that cannot fail is the defect.
    """

    def setUp(self):
        self.text = vfixtures.PROTOCOL_PATH.read_text()
        self.cfg = json.loads(vfixtures.CELLS_PATH.read_text())
        self.manifest = json.loads(vfixtures.PINNED_MANIFEST.read_text())

    def _check(self, cfg=None, manifest=None, text=None):
        return vfixtures.check_pinned_file_hashes(
            self.cfg if cfg is None else cfg,
            self.manifest if manifest is None else manifest,
            vfixtures.REPO_ROOT, vfixtures.PINNED_DIR,
            self.text if text is None else text)

    def test_every_pin_matches_the_file_it_names(self):
        self.assertEqual(self._check(), [])

    def test_the_fixture_itself_passes(self):
        case = next(c for c in vfixtures.ALL_FIXTURES
                    if c.name == "F18_pinned_file_hashes")
        self.assertEqual(case.run(), [])

    def test_a_stale_provenance_pin_is_caught(self):
        """Exactly the N.1 failure: the file moved, the pin did not."""
        for key in ("formula_source", "pinned_primitive", "vocabulary_alignment"):
            with self.subTest(pin=key):
                cfg = copy.deepcopy(self.cfg)
                cfg["provenance"][key]["sha256"] = "d" * 64
                failures = self._check(cfg=cfg)
                self.assertTrue(any("The pin is stale" in f for f in failures),
                                failures)

    def test_a_pin_absent_from_the_protocol_is_caught(self):
        cfg = copy.deepcopy(self.cfg)
        real = cfg["provenance"]["pinned_primitive"]["sha256"]
        text = self.text.replace(real, "e" * 64)
        self.assertNotEqual(text, self.text, "the header pin moved; fix this test")
        failures = self._check(text=text)
        self.assertTrue(any("does not appear in PROTOCOL.md" in f
                            for f in failures), failures)

    def test_a_stale_pinned_copy_hash_is_caught(self):
        manifest = copy.deepcopy(self.manifest)
        name = sorted(manifest["files"])[0]
        manifest["files"][name] = "f" * 64
        failures = self._check(manifest=manifest)
        self.assertTrue(any(name in f and "PINNED.json records" in f
                            for f in failures), failures)

    def test_a_manifest_that_omits_a_deposited_file_is_caught(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"].pop(sorted(manifest["files"])[0])
        failures = self._check(manifest=manifest)
        self.assertTrue(any("the deposit holds" in f for f in failures), failures)

    def test_a_manifest_naming_a_file_that_is_not_there_is_caught(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"]["lab_absent.py"] = "0" * 64
        failures = self._check(manifest=manifest)
        self.assertTrue(any("the deposit holds" in f for f in failures), failures)

    def test_a_missing_file_is_caught_rather_than_skipped(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["provenance"]["pinned_primitive"]["path"] = "src/no_such_file.py"
        failures = self._check(cfg=cfg)
        self.assertTrue(any("does not exist" in f for f in failures), failures)

    def test_a_source_commit_the_protocol_does_not_name_is_caught(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["source_commit"] = "a" * 40
        failures = self._check(manifest=manifest)
        self.assertTrue(any("does not name the commit" in f for f in failures),
                        failures)

    def test_the_digest_is_the_real_sha256_of_the_bytes(self):
        """Against a second implementation, so the hash is not self-referential."""
        path = vfixtures.CELLS_PATH
        want = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(vfixtures.sha256_file(path), want)


class TestRandomisedContainment(unittest.TestCase):
    """The containment property over many independently seeded programs."""

    SEEDS = 300

    def _run_one(self, seed: int) -> Tuple[ValidationMonitor, Program]:
        rng = random.Random(seed * 7919 + 13)
        program = Program(seed=seed, n_pairs=rng.randint(1, 25))
        mon, _looks = vfixtures.replay(program.script(look_every=rng.randint(2, 6)),
                                       cost_cap=CAP, record_history=True)
        return mon, program

    def test_containment_over_many_seeds(self):
        n_pairs_total = 0
        n_looks_total = 0
        n_certified = 0
        for seed in range(self.SEEDS):
            with self.subTest(seed=seed):
                mon, program = self._run_one(seed)
                n_pairs_total += len(mon.pairs)
                n_looks_total += len(mon.looks)

                # 1. every recorded enclosure contains the hidden true score
                for label, _n, snapshot in mon.history:
                    for pid, (h_enc, s_enc) in snapshot.items():
                        true_h, true_s = program.pair_truth[pid]
                        self.assertTrue(
                            h_enc.contains(true_h),
                            f"seed {seed} {label}: hierarchy {true_h} outside "
                            f"[{h_enc.lo}, {h_enc.hi}] for {pid}")
                        self.assertTrue(
                            s_enc.contains(true_s),
                            f"seed {seed} {label}: success {true_s} outside "
                            f"[{s_enc.lo}, {s_enc.hi}] for {pid}")

                # 2. no enclosure ever widened
                seen: Dict[Hashable, Tuple[Enclosure, Enclosure]] = {}
                for label, _n, snapshot in mon.history:
                    for pid, encs in snapshot.items():
                        prev = seen.get(pid)
                        if prev is not None:
                            for k in (0, 1):
                                self.assertGreaterEqual(prev[k].lo, -1.0)
                                self.assertLessEqual(encs[k].width,
                                                     prev[k].width + 1e-12)
                                self.assertGreaterEqual(encs[k].lo, prev[k].lo - 1e-12)
                                self.assertLessEqual(encs[k].hi, prev[k].hi + 1e-12)
                        seen[pid] = encs

                # 3. every certificate equals the hidden truth
                for pair in mon.pairs:
                    true_h, true_s = program.pair_truth[pair.pair_id]
                    if pair.hierarchy.certified:
                        n_certified += 1
                        self.assertEqual(pair.hierarchy.lo, float(true_h))
                        self.assertEqual(pair.success.lo, float(true_s))

                # 4. the running-sum interval brackets the true running mean at
                #    every look, on that look's own prefix, and the band is
                #    ordered and bounded
                for look in mon.looks:
                    n = look.n_enrolled
                    for idx, band in ((0, look.hierarchy), (1, look.success)):
                        prefix_true = [program.pair_truth[p.pair_id][idx]
                                       for p in mon.pairs[:n]]
                        mean = sum(prefix_true) / n if n else 0.0
                        self.assertLessEqual(band.mean_lower, mean + 1e-12)
                        self.assertGreaterEqual(band.mean_upper, mean - 1e-12)
                        self.assertLessEqual(band.lower, band.upper)
                        self.assertGreaterEqual(band.lower, -1.0)
                        self.assertLessEqual(band.upper, 1.0)
        self.assertGreater(n_pairs_total, 1000)
        self.assertGreater(n_looks_total, 300)
        self.assertGreater(n_certified, 100)

    def test_reveal_order_invariance_over_many_seeds(self):
        for seed in range(60):
            with self.subTest(seed=seed):
                program = Program(seed=seed + 5000, n_pairs=random.Random(seed).randint(2, 12))
                base, _ = vfixtures.replay(
                    program.enroll_events + program.reveal_events, cost_cap=CAP)
                reference = base.state_signature()
                shuffler = random.Random(seed + 991)
                for _ in range(5):
                    shuffled = list(program.reveal_events)
                    shuffler.shuffle(shuffled)
                    other, _ = vfixtures.replay(
                        program.enroll_events + shuffled, cost_cap=CAP)
                    self.assertEqual(other.state_signature(), reference)

    def test_repeated_updates_are_idempotent_over_many_seeds(self):
        for seed in range(60):
            with self.subTest(seed=seed):
                program = Program(seed=seed + 9000,
                                  n_pairs=random.Random(seed).randint(2, 12))
                base, _ = vfixtures.replay(
                    program.enroll_events + program.reveal_events, cost_cap=CAP)
                repeated: List[tuple] = []
                for ev in program.reveal_events:
                    repeated.extend([ev, ev, ev])
                other, _ = vfixtures.replay(
                    program.enroll_events + repeated, cost_cap=CAP)
                self.assertEqual(other.state_signature(), base.state_signature())

    def test_completed_pairs_never_change_the_denominator(self):
        program = Program(seed=424242, n_pairs=40)
        mon, _ = vfixtures.replay(program.script(look_every=5), cost_cap=CAP)
        for look in mon.looks:
            self.assertEqual(look.n_enrolled, look.hierarchy.n)
            self.assertEqual(look.hierarchy.n, look.success.n)
            self.assertLessEqual(look.n_certified, look.n_enrolled)
        self.assertEqual(mon.looks[-1].n_enrolled, 40)


class CostPathProgram:
    """A stream shaped like the frozen DGP of PROTOCOL 4.1-4.3.

    Atoms with their cost columns, a long/short delay, a uniform first-reveal
    offset, a fair first-reveal coin, and the elapsed-cost accrual
    ``ell(a) = (c * a) / D``.  This is the shape ``vgen.py`` will have to
    produce, exercised here against the monitor before that module exists.

    It is NOT the issue-#12 grid and establishes no operating characteristic.
    It uses ``random.Random`` and touches no namespace-0 ``SeedSequence``
    stream, and the long delay block is shortened so the test runs in seconds.
    """

    CAP = 100.0
    SHORT = (0, 19)
    LONG = (20, 60)              # shortened; the grid's block is (100, 699)

    def __init__(self, seed: int, n_pairs: int, weights: Dict[str, int],
                 informative_delay: bool) -> None:
        rng = random.Random(seed)
        self.n_pairs = n_pairs
        self.pairs = []
        atoms = list(weights)
        cum = []
        total = 0
        for a in atoms:
            total += weights[a]
            cum.append(total)
        for i in range(n_pairs):
            k = rng.randrange(total)
            atom = atoms[next(j for j, c in enumerate(cum) if k < c)]
            s_C, s_I, c_C, c_I, Z, D = vfixtures.ATOM_COSTS[atom]
            if informative_delay:
                long_ = (Z == -1) and (rng.randrange(4) < 3)
            else:
                long_ = rng.random() < 0.3
            block = self.LONG if long_ else self.SHORT
            d = rng.randint(*block)
            f = rng.randint(0, d)
            cand_first = rng.random() < 0.5
            # arrival positions: slot_first, slot_second; the coin orients them
            coin = "AB" if cand_first else "BA"
            self.pairs.append(dict(
                pid=f"p{i}", coin=coin, first=f"s{i}a", second=f"s{i}b",
                atom=atom, Z=Z, D=D, d=d, f=f,
                # the arm revealed first is the candidate iff coin == 'AB'
                c_first=(c_C if cand_first else c_I),
                s_first=(s_C if cand_first else s_I),
                c_second=(c_I if cand_first else c_C),
                s_second=(s_I if cand_first else s_C)))

    def run(self, record_history: bool = True) -> ValidationMonitor:
        mon = ValidationMonitor(cost_cap=self.CAP, record_history=record_history)
        for tick, pair in enumerate(self.pairs, start=1):
            mon.enroll(pair["pid"], pair["coin"], pair["first"], pair["second"])
            for j in range(tick):
                p = self.pairs[j]
                age = tick - (j + 1)
                for slot, dur, succ, cost in (
                        (p["first"], p["f"], p["s_first"], p["c_first"]),
                        (p["second"], p["d"], p["s_second"], p["c_second"])):
                    if age == dur:
                        mon.finalize(slot, succ, cost)
                    elif age < dur:
                        mon.observe_elapsed_cost(slot, (cost * age) / dur)
            mon.look(f"n{tick}")
        return mon


class TestCostEnclosurePath(unittest.TestCase):
    """PROTOCOL 2.5 and 4.3: the tier the live effect actually rides on.

    PREREG_CHECK B.6 found that no cell exercised this path at all.  These are
    the end-to-end property tests of the path it now takes.
    """

    LAWS = {
        "L1": {"BB+": 2250, "BB0": 500, "BB-": 2250, "C>I": 1500, "I>C": 1500, "FF": 2000},
        "L2": {"BB+": 1500, "BB0": 500, "BB-": 4000, "C>I": 3000, "I>C": 500, "FF": 500},
        "L3": {"BB+": 5000, "BB0": 300, "BB-": 700, "C>I": 1200, "I>C": 1500, "FF": 1300},
        "L4": {"BB+": 4000, "BB0": 1000, "BB-": 1500, "C>I": 2500, "I>C": 500, "FF": 500},
    }

    def test_containment_and_monotonicity_on_dgp_shaped_streams(self):
        collapsed_uncertified = 0
        looks = 0
        # fixed integer seeds: str.__hash__ is salted per interpreter, and a
        # pre-registration artefact has to reproduce run for run
        for law_i, (law, weights) in enumerate(sorted(self.LAWS.items())):
            for informative in (False, True):
                with self.subTest(law=law, informative=informative):
                    prog = CostPathProgram(seed=9_000 + 10 * law_i + int(informative),
                                           n_pairs=45, weights=weights,
                                           informative_delay=informative)
                    mon = prog.run()
                    truth = {p["pid"]: (p["Z"], p["D"]) for p in prog.pairs}
                    seen: Dict[Hashable, Tuple[Enclosure, Enclosure]] = {}
                    for label, n, snap in mon.history:
                        looks += len(snap)
                        for pid, (h_enc, s_enc) in snap.items():
                            tz, td = truth[pid]
                            self.assertTrue(
                                h_enc.contains(tz),
                                f"{law} {label}: hierarchy {tz} outside "
                                f"[{h_enc.lo}, {h_enc.hi}] for {pid}")
                            self.assertTrue(s_enc.contains(td))
                            prev = seen.get(pid)
                            if prev is not None:
                                self.assertGreaterEqual(h_enc.lo, prev[0].lo - 1e-12)
                                self.assertLessEqual(h_enc.hi, prev[0].hi + 1e-12)
                                self.assertGreaterEqual(s_enc.lo, prev[1].lo - 1e-12)
                                self.assertLessEqual(s_enc.hi, prev[1].hi + 1e-12)
                            seen[pid] = (h_enc, s_enc)
                    for look in mon.looks:
                        n = look.n_enrolled
                        for idx, band in ((0, look.hierarchy), (1, look.success)):
                            mean = sum(truth[p.pair_id][idx]
                                       for p in mon.pairs[:n]) / n
                            self.assertLessEqual(band.mean_lower, mean + 1e-12)
                            self.assertGreaterEqual(band.mean_upper, mean - 1e-12)
                    last = mon.looks[-1]
                    collapsed_uncertified += (last.n_point_resolved
                                              - last.n_certified)
        self.assertGreater(looks, 5000, "pair-look observations checked")
        self.assertGreater(
            collapsed_uncertified, 0,
            "no pair was ever point-resolved without a certificate: the cost "
            "enclosure path is not being exercised by these streams")

    def test_elapsed_cost_alone_collapses_the_hierarchy_without_a_certificate(self):
        """The mechanism, in isolation: one pair, one reveal, cost only."""
        mon = ValidationMonitor(cost_cap=100.0)
        mon.enroll("x", "AB", "xa", "xb")
        mon.finalize("xa", 1, 10.0)                 # candidate: success, cost 10
        self.assertEqual(vfixtures._enc(mon, "x", "hierarchy").as_tuple(),
                         (-1.0, 1.0, False))
        mon.observe_elapsed_cost("xb", 9.4)         # below .95 * 10
        self.assertEqual(vfixtures._enc(mon, "x", "hierarchy").as_tuple(),
                         (-1.0, 1.0, False))
        mon.observe_elapsed_cost("xb", 9.5)         # at .95 * 10
        self.assertEqual(vfixtures._enc(mon, "x", "hierarchy").as_tuple(),
                         (0.0, 1.0, False))
        mon.observe_elapsed_cost("xb", 10.6)        # beyond 10 / .95
        enc = vfixtures._enc(mon, "x", "hierarchy")
        self.assertEqual(enc.as_tuple(), (1.0, 1.0, False))
        self.assertTrue(enc.resolved)
        self.assertFalse(enc.certified,
                         "a cost collapse is a point WITHOUT a certificate")
        # the success enclosure is untouched by cost
        self.assertEqual(vfixtures._enc(mon, "x", "success").as_tuple(),
                         (0.0, 1.0, False))
        # and the eventual certificate agrees with what cost already proved
        mon.finalize("xb", 1, 40.0)
        self.assertEqual(vfixtures._enc(mon, "x", "hierarchy").as_tuple(),
                         (1.0, 1.0, True))

    def test_a_failed_revealed_arm_never_opens_the_cost_tier(self):
        mon = ValidationMonitor(cost_cap=100.0)
        mon.enroll("y", "AB", "ya", "yb")
        mon.finalize("ya", 0, 40.0)                 # candidate failed
        for ell in (0.0, 38.0, 60.0, 99.0):
            mon.observe_elapsed_cost("yb", ell)
            self.assertEqual(vfixtures._enc(mon, "y", "hierarchy").as_tuple(),
                             (-1.0, 0.0, False),
                             "cost is ineligible unless both episodes succeed")

    def test_the_mirror_case_collapses_toward_the_incumbent(self):
        mon = ValidationMonitor(cost_cap=100.0)
        mon.enroll("z", "BA", "z1", "z2")           # z2 is the candidate
        mon.finalize("z1", 1, 10.0)                 # incumbent: success, cost 10
        mon.observe_elapsed_cost("z2", 10.6)
        self.assertEqual(vfixtures._enc(mon, "z", "hierarchy").as_tuple(),
                         (-1.0, -1.0, False))


class TestLargeProgramSmoke(unittest.TestCase):
    """One larger program: containment holds and nothing decides prematurely."""

    def test_four_hundred_pairs(self):
        program = Program(seed=31337, n_pairs=400)
        mon, _ = vfixtures.replay(program.script(look_every=200), cost_cap=CAP,
                                  record_history=False)
        final = mon.looks[-1]
        self.assertEqual(final.n_enrolled, 400)
        for idx, band in ((0, final.hierarchy), (1, final.success)):
            mean = program.true_mean(idx)
            self.assertLessEqual(band.mean_lower, mean + 1e-12)
            self.assertGreaterEqual(band.mean_upper, mean - 1e-12)
        # with a large unresolved fraction the conservative band must abstain
        self.assertEqual(final.decision, CONTINUE)


# ===========================================================================
# THE MISSED-CROSSING REGRESSION  (root disposition section B)
# ===========================================================================
# The root's open finding: the deposited v1 runner OMITS the intermediate drain
# looks at which a completed-data baseline's completion index changes.  At
# horizon 1,000, using delays inside their declared support, there is a
# permitted tick at which BOTH baseline lower bounds are +0.0133027164 and BOTH
# deploy gates cross -- and the v1 runner never evaluates it, so it records no
# decision and no miscoverage for either baseline.
#
# These tests are the permanent regression.  They are written so that they FAIL
# against the v1 schedule and PASS against v2: if the v2 event schedule is ever
# reverted, narrowed back to the enrollment prefixes, or loses the drain
# interior, ``test_v2_evaluates_the_missed_tick_and_both_gates_cross`` fails on
# exactly the tick the root named.  The v1 behaviour is pinned too, from the
# other side, so the difference between the two schedules is a measured fact in
# this suite rather than a claim in a document.
#
# This is a DETERMINISTIC PATH.  It refutes the claim that the v1 look set is
# complete; it is not an estimate of how often such a path occurs, and no rate,
# power or operating characteristic is claimed anywhere below.
# ===========================================================================
class TestMissedCrossingWitness(unittest.TestCase):
    """The root's witness at N_max = 1,000, and the schedule repair that sees it."""

    N_MAX = 1000
    TICK = 1010                 # the permitted drain tick v1 never evaluates
    INDEX = 600                 # both baselines' completion index there
    #: clip(100/600 - r(600), -1, 1), pinned as a literal.  The root's
    #: disposition prints it rounded to ten places as +0.0133027164.
    LOWER = 0.013302716411199761

    @classmethod
    def setUpClass(cls):
        cls.draw = vgen.build_missed_crossing_witness(cls.N_MAX)
        cls.cfg = vrun.make_config(cls.N_MAX, vgen.NAMESPACE_FIXTURE)

    # -- the path is legal --------------------------------------------------
    def test_the_witness_is_a_permitted_path_of_the_frozen_process(self):
        """A witness outside the declared support would prove nothing."""
        r = vgen.witness_reachability(self.draw)
        self.assertEqual(r["cell"], "C1")
        self.assertTrue(r["every_short_offset_in_support"], r)
        self.assertTrue(r["every_long_offset_in_support"], r)
        self.assertTrue(r["first_reveal_equals_full_reveal"])
        self.assertTrue(r["every_atom_has_positive_weight"], r)
        self.assertGreater(r["p_long_under_rule_N"], 0.0)
        # the realized path sums to the truth, so the crossing IS a miscoverage
        self.assertEqual(r["realized_sum_z"], 0)
        self.assertEqual(r["realized_sum_d"], 0)
        self.assertEqual(r["true_mu_h"], 0.0)
        self.assertEqual(r["true_mu_s"], 0.0)

    def test_the_missed_tick_lies_in_the_drain_interior(self):
        """v1 takes no look between the enrollment cap and finalization."""
        self.assertEqual(self.cfg.finalization_tick, self.N_MAX + vgen.DRAIN_W)
        self.assertGreater(self.TICK, self.N_MAX)
        self.assertLess(self.TICK, self.cfg.finalization_tick)

    # -- v1: the defect, pinned from its own side ---------------------------
    def test_v1_schedule_misses_the_crossing_entirely(self):
        """The v1 runner returns NO_DECISION and no miscoverage on this path."""
        recs, n_looks, _ = vrun.evaluate_trial(self.draw, self.cfg,
                                               vrun.SCHEDULE_V1)
        self.assertEqual(n_looks, self.N_MAX + 1)
        series, _, _, _ = vrun.build_series(self.draw, self.cfg)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            rec, s = recs[name], series[name]
            self.assertEqual(rec.decision, vrun.NO_DECISION, name)
            self.assertFalse(rec.ever_miscover_h, name)
            self.assertFalse(rec.ever_miscover_s, name)
            # not "it decided late": the gate never opens at ANY v1 look
            self.assertLess(float(s.l_h.max()), 0.0, name)
            self.assertNotIn(self.TICK, set(s.tick.tolist()),
                             f"{name}: the missed tick must be absent from the "
                             f"v1 axis, or there is nothing to repair")

    # -- v2: THE REGRESSION -------------------------------------------------
    def test_v2_evaluates_the_missed_tick_and_both_gates_cross(self):
        """THE regression.  Reverting the schedule to v1 fails this test.

        At tick 1,010 both completed-data baselines stand at completion index
        600 with score sum +100, so both means are 1/6 and both lower bounds are
        1/6 - r(600).  L_h > 0 and L_s > -delta hold at the SAME look, so the
        deploy gate fires; the truth is 0 in both gates, so both bands exclude
        it.  Every number below is asserted at strict float equality.
        """
        series, _, _, _ = vrun.build_series_v2(self.draw, self.cfg)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            s = series[name]
            pos = int(np.flatnonzero(s.tick == self.TICK)[0])
            self.assertEqual(int(s.index[pos]), self.INDEX, name)
            self.assertEqual(int(s.prefix[pos]), self.N_MAX,
                             f"{name}: the enrolled prefix is pinned in the drain")
            self.assertEqual(float(s.l_h[pos]), self.LOWER, name)
            self.assertEqual(float(s.l_s[pos]), self.LOWER, name)
            self.assertEqual(f"{float(s.l_h[pos]):+.10f}", "+0.0133027164", name)
            # both gates, at the same look
            self.assertGreater(float(s.l_h[pos]), 0.0, name)
            self.assertGreater(float(s.l_s[pos]), -self.cfg.delta, name)
            self.assertGreaterEqual(int(s.index[pos]), self.cfg.n_min, name)
            # and the band excludes the truth in both gates
            self.assertLess(0.0, float(s.l_h[pos]), name)
            self.assertLess(0.0, float(s.l_s[pos]), name)

    def test_v2_records_the_decision_and_both_miscoverages(self):
        """The same crossing, read through the reported per-trial record."""
        recs, n_looks, _ = vrun.evaluate_trial(self.draw, self.cfg,
                                               vrun.SCHEDULE_V2)
        self.assertEqual(n_looks, self.cfg.finalization_tick)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            rec = recs[name]
            self.assertEqual(rec.decision, vrun.DEPLOY, name)
            self.assertTrue(rec.ever_miscover_h, name)
            self.assertTrue(rec.ever_miscover_s, name)
            self.assertTrue(rec.ever_below_h, name)
            self.assertTrue(rec.ever_below_s, name)
            self.assertTrue(rec.decided_in_drain, name)
            self.assertFalse(rec.decided_at_finalization,
                             f"{name}: it decides in the drain INTERIOR, not at "
                             f"the finalization look")

    def test_enrollment_prefix_and_elapsed_time_are_two_separate_records(self):
        """v1 conflated them; on this path they differ by 10 ticks."""
        recs, _, _ = vrun.evaluate_trial(self.draw, self.cfg, vrun.SCHEDULE_V2)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            rec = recs[name]
            self.assertEqual(rec.tau, self.N_MAX, f"{name}: enrolled prefix")
            self.assertEqual(rec.tau_tick, self.TICK, f"{name}: elapsed time")
            self.assertNotEqual(rec.tau, rec.tau_tick, name)
            self.assertEqual(rec.look_prefix, self.N_MAX, name)
            self.assertEqual(rec.look_tick, self.TICK, name)
        # a non-decider takes the two declared caps, also separately
        adapter = recs[vrun.ADAPTER]
        self.assertEqual(adapter.decision, vrun.NO_DECISION)
        self.assertEqual(adapter.tau, self.N_MAX)
        self.assertEqual(adapter.tau_tick, self.cfg.finalization_tick)

    def test_the_regression_discriminates_the_two_schedules(self):
        """A guard that cannot fail proves nothing: show it separates them."""
        v1, _, _ = vrun.evaluate_trial(self.draw, self.cfg, vrun.SCHEDULE_V1)
        v2, _, _ = vrun.evaluate_trial(self.draw, self.cfg, vrun.SCHEDULE_V2)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            self.assertNotEqual(v1[name].decision, v2[name].decision, name)
            self.assertNotEqual(v1[name].ever_miscover_h,
                                v2[name].ever_miscover_h, name)
            self.assertNotEqual(v1[name].tau_tick, v2[name].tau_tick, name)

    def test_the_finest_reading_also_sees_it_and_sees_more(self):
        """The declared sensitivity is a strict superset, and fires no later."""
        batched, _, _, _ = vrun.build_series_v2(self.draw, self.cfg, finest=False)
        finest, _, _, _ = vrun.build_series_v2(self.draw, self.cfg, finest=True)
        recs, _, _ = vrun.evaluate_trial(self.draw, self.cfg,
                                         vrun.SCHEDULE_V2_FINEST)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            self.assertGreater(finest[name].index.size, batched[name].index.size,
                               name)
            self.assertEqual(recs[name].decision, vrun.DEPLOY, name)
            self.assertLessEqual(recs[name].tau_tick, self.TICK, name)
        # the ADAPTER's look set is unchanged by the finest reading, which is the
        # domination theorem of the schedule declaration, not a convenience
        self.assertEqual(finest[vrun.ADAPTER].index.size,
                         batched[vrun.ADAPTER].index.size)

    def test_the_adapter_is_untouched_by_the_repair(self):
        """LASTLOOK_CHECK (b): not one ADAPTER reading moves, under any schedule."""
        out = {}
        for sched in vrun.SCHEDULES:
            recs, _, _ = vrun.evaluate_trial(self.draw, self.cfg, sched)
            rec = recs[vrun.ADAPTER]
            out[sched] = (rec.decision, rec.ever_miscover_h, rec.ever_miscover_s)
        self.assertEqual(len(set(out.values())), 1, out)
        self.assertEqual(out[vrun.SCHEDULE_V1],
                         (vrun.NO_DECISION, False, False))

    def test_the_witness_is_frozen_at_the_horizon_that_actually_ran(self):
        """The same construction at N_max = 2,000, the deposited horizon."""
        draw = vgen.build_missed_crossing_witness(2000)
        cfg = vrun.make_config(2000, vgen.NAMESPACE_FIXTURE)
        r = vgen.witness_reachability(draw)
        self.assertTrue(r["every_long_offset_in_support"], r)
        self.assertEqual(r["realized_sum_z"], 0)
        v1, _, _ = vrun.evaluate_trial(draw, cfg, vrun.SCHEDULE_V1)
        v2, _, _ = vrun.evaluate_trial(draw, cfg, vrun.SCHEDULE_V2)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            self.assertEqual(v1[name].decision, vrun.NO_DECISION, name)
            self.assertEqual(v2[name].decision, vrun.DEPLOY, name)
            self.assertEqual(v2[name].tau_tick, 2010, name)
            self.assertEqual(v2[name].tau, 2000, name)


class TestV2EventSchedule(unittest.TestCase):
    """The declared schedule's two structural promises, checked not asserted."""

    def _draws(self, n_max=300, programs=2):
        for cell in vgen.CELLS:
            for p in range(programs):
                for t in range(vgen.TRIALS_PER_PROGRAM):
                    yield vgen.draw_trial(cell, p, t, n_max=n_max,
                                          namespace=vgen.NAMESPACE_SMOKE)

    def test_v1_look_set_is_a_subset_of_v2_state_for_state(self):
        """If this fails, v2 is a different measurement, not an amendment."""
        cfg = vrun.make_config(300, vgen.NAMESPACE_SMOKE)
        n = 0
        for draw in self._draws():
            vrun.assert_v2_reduces_to_v1(draw, cfg)
            n += 1
        self.assertGreaterEqual(n, 64)
        for n_max in sorted(vgen.MISSED_CROSSING_BLOCKS):
            vrun.assert_v2_reduces_to_v1(
                vgen.build_missed_crossing_witness(n_max),
                vrun.make_config(n_max, vgen.NAMESPACE_FIXTURE))

    def test_every_completion_index_change_is_on_the_v2_axis(self):
        """Disposition section B: EVERY required completion-index change.

        For each baseline, collect every tick through the finalization window at
        which its own index changes, and require the v2 axis to carry a look at
        that tick carrying that index.  The check is made live by also asserting
        that changes occur in the drain interior, where v1 had no axis at all.
        """
        n_max = 300
        cfg = vrun.make_config(n_max, vgen.NAMESPACE_SMOKE)
        fin = cfg.finalization_tick
        drain_changes = 0
        for draw in self._draws(n_max=n_max):
            series, _, _, _ = vrun.build_series_v2(draw, cfg)
            cpref, naive = vgen.completion_tick_states(draw, n_max, fin)
            for name, st in ((vrun.CPREFIX, cpref), (vrun.NAIVE, naive)):
                changed = np.flatnonzero(np.diff(st.index, prepend=0) != 0)
                s = series[name]
                axis = dict(zip(s.tick.tolist(), s.index.tolist()))
                for i in changed:
                    tick = int(st.tick[i])
                    self.assertIn(tick, axis, f"{name}: tick {tick} is off the axis")
                    self.assertEqual(axis[tick], int(st.index[i]), name)
                    if tick > n_max:
                        drain_changes += 1
        self.assertGreater(drain_changes, 0,
                           "no completion-index change landed in the drain, so "
                           "this check is vacuous on these draws")

    def test_the_declared_batching_makes_the_adapter_end_of_tick_dominant(self):
        """The domination argument, driven through the frozen enclosure code."""
        cfg = vrun.make_config(120, vgen.NAMESPACE_SMOKE)
        checked = 0
        for draw in self._draws(n_max=120, programs=1):
            checked += vrun.assert_adapter_intratick_domination(draw, cfg)
        self.assertGreater(checked, 500,
                           "no intra-tick adapter state was exercised")

    def test_the_v2_axis_covers_the_whole_finalization_window(self):
        cfg = vrun.make_config(300, vgen.NAMESPACE_SMOKE)
        draw = next(self._draws(n_max=300, programs=1))
        series, _, _, _ = vrun.build_series_v2(draw, cfg)
        ticks = series[vrun.ADAPTER].tick
        self.assertEqual(int(ticks[0]), 1)
        self.assertEqual(int(ticks[-1]), cfg.finalization_tick)
        self.assertEqual(ticks.size, cfg.finalization_tick)
        self.assertTrue(np.array_equal(
            ticks, np.arange(1, cfg.finalization_tick + 1)))
        # the enrolled prefix is pinned through the window, the clock is not
        prefix = series[vrun.ADAPTER].prefix
        self.assertEqual(int(prefix[-1]), cfg.n_max)
        self.assertEqual(int(prefix[cfg.n_max - 1]), cfg.n_max)

    def test_no_scientific_rule_moved_with_the_schedule(self):
        """A schedule says WHICH states are looked at, not what is computed."""
        self.assertEqual(vband.ALPHA_GATE, 0.00625)
        self.assertEqual(vband.RHO, 100.0)
        self.assertEqual(vband.DELTA, 0.03)
        self.assertEqual(vband.N_MIN, 100)
        self.assertEqual(vgen.DRAIN_W, 200)
        cfg = vrun.make_config(300, vgen.NAMESPACE_SMOKE)
        draw = next(self._draws(n_max=300, programs=1))
        v1, _, _, _ = vrun.build_series(draw, cfg)
        v2, _, _, _ = vrun.build_series_v2(draw, cfg)
        # identical band arithmetic wherever the two axes meet
        for name in vrun.CONSTRUCTIONS:
            a, b = v1[name], v2[name]
            pos = np.searchsorted(b.tick, a.tick)
            for f in ("l_h", "u_h", "l_s", "u_s"):
                self.assertTrue(np.array_equal(getattr(b, f)[pos],
                                               getattr(a, f)), f"{name}.{f}")

    def test_v1_output_layout_is_frozen(self):
        """A v1 re-run must still write v1's own record layout."""
        self.assertEqual(vrun.trial_header(vrun.SCHEDULE_V1), vrun.TRIAL_HEADER)
        self.assertIn("decision,tau,decided_at_finalization", vrun.TRIAL_HEADER)
        self.assertNotIn("tau_tick", vrun.TRIAL_HEADER)
        v2 = vrun.trial_header(vrun.SCHEDULE_V2)
        self.assertIn("tau_prefix", v2)
        self.assertIn("tau_tick", v2)
        self.assertIn("schedule", v2)

    def test_it_agrees_with_the_independent_last_look_harness(self):
        """Two implementations of the same amendment, state for state.

        ``vlastlook_check.py`` measured the drain reading (``all_ticks``) and
        the one-event-at-a-time reading (``finest``) independently of this
        runner, and its numbers are already on the record.  If the v2 schedule
        implemented here disagreed with that harness, one of the two is wrong
        and neither measurement could be cited.
        """
        import vlastlook_check as VL

        n_max = 300
        cfg = vrun.make_config(n_max, vgen.NAMESPACE_SMOKE)
        fin = cfg.finalization_tick
        drain = finest = 0
        for cell in vgen.CELLS:
            for t in range(vgen.TRIALS_PER_PROGRAM):
                draw = vgen.draw_trial(cell, 0, t, n_max=n_max,
                                       namespace=vgen.NAMESPACE_SMOKE)
                mine, _, _, _ = vrun.build_series_v2(draw, cfg)
                ticks, states = VL.drain_states(draw, cfg)
                pos = ticks - 1                     # my axis is ticks 1..fin
                for name in (vrun.CPREFIX, vrun.NAIVE):
                    idx, sh, ss = states[name]
                    s = mine[name]
                    self.assertTrue(np.array_equal(s.index[pos], idx), name)
                    self.assertTrue(np.array_equal(s.tick[pos], ticks), name)
                    ev = VL.band_events(idx, sh, ss, cfg, cell.mu_h, cell.mu_s)
                    for theirs, ours in (("lo_h", "l_h"), ("hi_h", "u_h"),
                                         ("lo_s", "l_s"), ("hi_s", "u_s")):
                        self.assertTrue(
                            np.array_equal(ev[theirs], getattr(s, ours)[pos]),
                            f"{cell.id}/{name}/{theirs}")
                    drain += len(ticks)
                theirs = VL.finest_states(draw, cfg)
                pair = dict(zip((vrun.CPREFIX, vrun.NAIVE),
                                vgen.completion_event_states(draw, n_max, fin)))
                for name, ms in pair.items():
                    i2, sh2, ss2, rt2 = theirs[name]
                    self.assertTrue(np.array_equal(ms.index, i2), name)
                    self.assertTrue(np.array_equal(ms.sum_h, sh2), name)
                    self.assertTrue(np.array_equal(ms.sum_s, ss2), name)
                    self.assertTrue(np.array_equal(ms.tick, rt2), name)
                    finest += ms.index.size
        self.assertGreater(drain, 5000)
        self.assertGreater(finest, 5000)

    def test_the_finalization_record_is_retained_for_every_trial(self):
        """Disposition section B: retain unresolved units at finalization.

        v2 lets a trial decide inside the drain, and PROTOCOL 9.5 reports the
        resolution quantities at the DECIDING look.  Without a separate
        finalization record such a trial would leave nothing at the finalization
        look, so v2 records both.  Checked on the witness, where the baselines
        decide at tick 1,010 and the finalization look is tick 1,200.
        """
        draw = vgen.build_missed_crossing_witness(1000)
        cfg = vrun.make_config(1000, vgen.NAMESPACE_FIXTURE)
        recs, _, _ = vrun.evaluate_trial(draw, cfg, vrun.SCHEDULE_V2)
        for name in (vrun.CPREFIX, vrun.NAIVE):
            rec = recs[name]
            self.assertEqual(rec.look_tick, 1010, name)
            # at the deciding look 400 of 1,000 pairs are still unresolved:
            # the 100 of block 601-700 and the 300 of block 701-1,000
            self.assertAlmostEqual(rec.unresolved_fraction, 0.4, places=12)
            self.assertEqual(rec.n_certified, 600, name)
            # and the finalization record is still there, and is different
            self.assertEqual(rec.final_unresolved_fraction, 0.0, name)
            self.assertEqual(rec.final_n_certified, 1000, name)
            self.assertNotEqual(rec.unresolved_fraction,
                                rec.final_unresolved_fraction, name)
        # nothing is censored: the denominator is N_max at both looks
        self.assertEqual(recs[vrun.ADAPTER].look_tick, cfg.finalization_tick)
        self.assertEqual(recs[vrun.ADAPTER].final_unresolved_fraction,
                         recs[vrun.ADAPTER].unresolved_fraction)

    def test_the_drain_arithmetic_agrees_with_the_monitor_itself(self):
        """The looks v2 adds are new code, so they get their own cross-check.

        ``vband.ValidationMonitor`` is driven event by event through the whole
        window -- enrolling nothing after the cap, per PROTOCOL 7.3 -- and every
        sum and band endpoint of the v2 adapter must equal its, at strict float
        equality; both baselines are recomputed from their definitions.
        """
        fails = vrun.selfcheck_v2_drain(n_pairs=25, programs=1, verbose=False)
        self.assertEqual(fails, [], fails[:5])

    def test_unknown_schedules_are_refused(self):
        with self.assertRaises(ValueError):
            vrun.check_schedule("every_look")
        with self.assertRaises(ValueError):
            vrun.make_config(100, 0, schedule="v2")


# ===========================================================================
# THE DEFERRED FINEST SENSITIVITY: its defect, recorded as a PERMANENT check.
#
# Root disposition of 2026-09-21 02:26 decision 1, and COORDINATOR_DECISIONS
# revision 16 item 78: "Preserve this development code and its failed witness,
# mark it unvalidated/deferred and disable it in the primary execution plan."
#
# So this class does two things that must not be collapsed into one:
#
#   1. It DEMONSTRATES the defect with a passing test, on the root's own
#      (3,2,3) witness. That test passes today because the defect is present.
#      If someone repairs ``completion_event_states``, this test FAILS and says
#      so, which is the correct alarm: the recorded evidence would be stale.
#
#   2. It states the CONTRACT the sensitivity claims but does not meet, as an
#      ``expectedFailure``. That test is the permanent failing check. It is
#      reported as an expected failure for as long as the defect stands, and
#      turns into an "unexpected success" the moment the schedule is repaired.
#
# NEITHER OF THESE IS A REPAIR, and passing them is not validation. The
# sensitivity stays deferred and disabled until it is separately reviewed.
# ===========================================================================
class TestDeferredFinestSensitivityDefect(unittest.TestCase):
    """PRESERVED DEVELOPMENT EVIDENCE for the deferred finest sensitivity."""

    #: The root's witness: three pairs resolving at ticks (3, 2, 3). Pair 2 is
    #: complete at tick 2, but a completed PREFIX needs pair 1, so the prefix is
    #: still 0. At tick 3 pair 1 resolves and the prefix jumps straight to 2.
    RESOLUTION_TICKS = (3, 2, 3)

    def _witness_draw(self):
        """Three pairs with the root's resolution ticks, built directly.

        ``resolution_tick`` is a derived property, ``enrollment + d``, so the
        (3, 2, 3) ticks are produced by the offsets ``d = (2, 0, 0)`` -- the
        SHORT delays the independent review named as permitted values.
        """
        base = vgen.build_missed_crossing_witness(1000)
        n = 3
        res = np.array(self.RESOLUTION_TICKS, dtype=np.int64)
        d = res - np.arange(1, n + 1, dtype=np.int64)       # (2, 0, 0)
        self.assertTrue((d >= 0).all(), d)
        f = np.zeros(n, dtype=np.int64)                     # f <= d, revealed early
        draw = vgen.TrialDraw(
            cell=base.cell, namespace=base.namespace,
            program_index=base.program_index, trial_index=base.trial_index,
            n=n, atom=base.atom[:n].copy(), z=base.z[:n].copy(),
            dsc=base.dsc[:n].copy(), d=d, f=f,
            cand_first=base.cand_first[:n].copy(),
            s_rev=base.s_rev[:n].copy(), c_rev=base.c_rev[:n].copy(),
            c_pend=base.c_pend[:n].copy(),
            a_narrow=base.a_narrow[:n].copy(),
            a_collapse=base.a_collapse[:n].copy())
        self.assertEqual(draw.resolution_tick.tolist(),
                         list(self.RESOLUTION_TICKS))
        return draw

    def test_the_schedule_is_deferred_and_cannot_be_selected_for_a_run(self):
        """The disabling, checked on every route into a run."""
        self.assertIn(vrun.SCHEDULE_V2_FINEST, vrun.DEFERRED_SCHEDULES)
        self.assertNotIn(vrun.SCHEDULE_V2_FINEST, vrun.PRIMARY_PANEL_SCHEDULES)
        self.assertTrue(vrun.is_deferred(vrun.SCHEDULE_V2_FINEST))
        with self.assertRaises(ValueError):
            vrun.check_primary_panel_schedule(vrun.SCHEDULE_V2_FINEST)
        # ... and the primary is NOT disabled by the same mechanism
        for keep in (vrun.SCHEDULE_V1, vrun.SCHEDULE_V2):
            self.assertEqual(vrun.check_primary_panel_schedule(keep), keep)

    def test_the_code_is_preserved_not_deleted(self):
        """Deferral must not become deletion: the evidence has to still exist."""
        self.assertTrue(hasattr(vgen, "completion_event_states"))
        self.assertTrue(callable(vgen.completion_event_states))
        self.assertIn(vrun.SCHEDULE_V2_FINEST, vrun.SCHEDULES)
        self.assertIn(vrun.SCHEDULE_V2_FINEST, vrun.DEFERRAL_REASON)

    def test_the_defect_is_present_and_this_is_what_it_looks_like(self):
        """THE DEFECT, demonstrated on the root's (3,2,3) witness.

        Passes BECAUSE the defect is present. If it ever fails, the iterator
        has been changed and this recorded evidence is stale -- that failure is
        the alarm, not a regression.
        """
        draw = self._witness_draw()
        cpref, _ = vgen.completion_event_states(draw, n_max=3, last_tick=6)
        emitted = list(zip(cpref.tick.tolist(), cpref.index.tolist()))
        # every k from 1 upward is emitted, each dated at the running-max tick
        self.assertIn((3, 1), emitted,
                      f"the defect should emit the unreachable (tick 3, k=1): "
                      f"{emitted}")
        self.assertIn((3, 2), emitted, emitted)
        self.assertIn((3, 3), emitted, emitted)

    def test_the_reachable_prefix_never_takes_the_value_the_iterator_emits(self):
        """Independent confirmation that k = 1 is unattainable at ANY tick.

        Computed from the tick-batched primary, which is a function of the path
        alone: the completed prefix goes 0, 0, 3 over ticks 1..3 and is never 1.
        """
        draw = self._witness_draw()
        cpref_batched, _ = vgen.completion_tick_states(draw, n_max=3, last_tick=6)
        reachable = set(cpref_batched.index.tolist())
        self.assertNotIn(
            1, reachable,
            f"prefix 1 must be unreachable under resolution ticks "
            f"{self.RESOLUTION_TICKS}; reachable set was {sorted(reachable)}")

    @unittest.expectedFailure
    def test_PERMANENT_FAILING_CHECK_finest_states_must_all_be_reachable(self):
        """THE CONTRACT THE DEFERRED SENSITIVITY CLAIMS AND DOES NOT MEET.

        ``completion_event_states`` documents itself as "the exact union over
        every admissible order". This asserts exactly that: every completed
        prefix it emits must be attainable under some tie order, and the
        tick-batched prefix trajectory is the set of attainable values.

        THIS TEST IS EXPECTED TO FAIL and is recorded as an expected failure
        for as long as the defect stands. It is not skipped, not deleted and
        not weakened. If it ever reports an UNEXPECTED SUCCESS, the schedule
        has been repaired and must go back for separate review before it may
        re-enter any panel.
        """
        draw = self._witness_draw()
        cpref_event, _ = vgen.completion_event_states(draw, n_max=3, last_tick=6)
        cpref_batched, _ = vgen.completion_tick_states(draw, n_max=3, last_tick=6)
        reachable = set(cpref_batched.index.tolist())
        unreachable = sorted(set(cpref_event.index.tolist()) - reachable - {0})
        self.assertEqual(
            unreachable, [],
            f"completion_event_states emitted unreachable completed prefixes "
            f"{unreachable} under resolution ticks {self.RESOLUTION_TICKS}; "
            f"attainable prefixes are {sorted(reachable)}")

    @unittest.expectedFailure
    def test_PERMANENT_FAILING_CHECK_finest_fractions_must_be_sub_tick(self):
        """THE SECOND DEFERRED DEFECT: end-of-batch fractions for sub-tick looks.

        ``_look_fractions`` is keyed by TICK and cached by TICK, so two looks
        inside the same tick cannot receive different resolution fractions.
        A finest baseline deciding partway through a tick therefore reports the
        END-OF-BATCH state. Expected to fail while that is true.
        """
        draw = self._witness_draw()
        cache = {}
        cfg = vrun.make_config(3, vgen.NAMESPACE_FIXTURE)
        first = vrun._look_fractions(draw, cfg, 3, cache)
        # a sub-tick look at the same tick must be distinguishable from the
        # end-of-tick look; keyed purely by tick, it cannot be
        self.assertNotEqual(
            len(cache), 1,
            "_look_fractions caches by tick alone, so sub-tick decision state "
            "is not representable; the finest sensitivity's reported "
            f"fractions are end-of-batch. cache={cache!r} first={first!r}")


# ===========================================================================
# THE DECLARED EXTERNAL REFERENCE: isolation, provenance and powerlessness.
#
# Root disposition decision 4 and COORDINATOR_DECISIONS revision 16 item 74.
# These tests check the three properties that make the vendored authors' code
# an acceptable reference rather than a new dependency risk: its bytes are the
# pinned ones, the primary does not import it, and it cannot decide anything.
# ===========================================================================
class TestVendoredAuthorReference(unittest.TestCase):
    """The vendored empirical-Bernstein reference (authors' code)."""

    REF_DIR = pathlib.Path(__file__).resolve().parent / "reference"

    def setUp(self):
        if not (self.REF_DIR / "MANIFEST.json").exists():
            self.skipTest("the reference has not been vendored on this host; "
                          "run reference/vendor.py")
        if str(self.REF_DIR) not in sys.path:
            sys.path.insert(0, str(self.REF_DIR))

    def test_the_primary_does_not_import_the_reference(self):
        """THE ONE-WAY DEPENDENCY. reference -> primary, never the reverse."""
        here = pathlib.Path(__file__).resolve().parent
        for name in ("vrun.py", "vgen.py", "vband.py", "vcompare.py",
                     "vfixtures.py", "vlastlook_check.py", "vresource_check.py"):
            text = (here / name).read_text()
            for forbidden in ("eb_reference", "eb_crosscheck", "confseq_eb",
                              "comparecast"):
                self.assertNotIn(
                    forbidden, text,
                    f"{name} must not reference the external reference "
                    f"({forbidden!r}); the primary must stay independent of it")

    def test_every_vendored_file_matches_its_pinned_hash(self):
        """Provenance: the bytes on disk are the bytes at the pinned commits."""
        manifest = json.loads((self.REF_DIR / "MANIFEST.json").read_text())
        checked = 0
        for entry in manifest["vendored_files"]:
            path = self.REF_DIR / entry["vendored_path"]
            self.assertTrue(path.exists(), entry["vendored_path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], entry["vendored_path"])
            if entry.get("verbatim"):
                self.assertIn(entry["commit"],
                              (vendor_commit := entry["commit"]), vendor_commit)
                checked += 1
        self.assertGreaterEqual(checked, 7, "too few verbatim author files")

    def test_the_mit_notices_are_retained_verbatim(self):
        for name in ("ComparingForecasters-LICENSE.txt", "confseq-LICENSE"):
            text = (self.REF_DIR / "licenses" / name).read_text()
            self.assertIn("MIT License", text, name)
            self.assertIn("Permission is hereby granted, free of charge", text,
                          name)
            self.assertIn("WITHOUT WARRANTY OF ANY KIND", text.upper(), name)

    def test_the_forbidden_constructions_are_not_in_the_importable_tree(self):
        """betting_cs / hedged_cs must be impossible to substitute, not merely
        discouraged: they target a fixed common mean, not our running mean."""
        tree = list((self.REF_DIR / "upstream").rglob("*.py"))
        for path in tree:
            text = path.read_text()
            self.assertNotIn("def betting_cs", text, str(path))
            self.assertNotIn("def hedged_cs", text, str(path))

    def test_the_reference_imports_and_is_the_authors_callable(self):
        import eb_reference
        try:
            fn = eb_reference.load_reference()
        except eb_reference.ReferenceUnavailable as exc:
            self.skipTest(f"reference not built for this interpreter: {exc}")
        self.assertEqual(fn.__name__, "confseq_eb")
        self.assertEqual(fn.__module__, "comparecast.confseq")

    def test_the_frozen_tuning_cannot_drift(self):
        import eb_reference
        self.assertEqual(eb_reference.V_OPT, 10.0)
        self.assertEqual((eb_reference.LO, eb_reference.HI), (-1.0, 1.0))
        self.assertEqual(eb_reference.BOUNDARY_TYPE, "mixture")

    def test_out_of_range_scores_are_refused(self):
        import eb_reference
        try:
            eb_reference.load_reference()
        except eb_reference.ReferenceUnavailable as exc:
            self.skipTest(str(exc))
        with self.assertRaises(ValueError):
            eb_reference.reference_bands(np.array([2.0, 0.0]), 0.00625)
        with self.assertRaises(ValueError):
            eb_reference.reference_bands(np.array([0.0, 0.0]), 1.5)

    def test_the_reference_cannot_enter_the_primary_panel(self):
        import eb_reference
        eb_reference.assert_reference_cannot_decide()
        self.assertEqual(vrun.CONSTRUCTIONS,
                         (vrun.ADAPTER, vrun.CPREFIX, vrun.NAIVE))

    def test_the_crosscheck_is_labelled_as_a_crosscheck_not_the_reference(self):
        import eb_crosscheck
        label = eb_crosscheck.CROSSCHECK_LABEL
        self.assertIn("CROSS-CHECK", label)
        self.assertIn("NOT the author reference", label)

    def test_crosscheck_reproduces_the_theorem_2_centre_and_clock(self):
        """The part of Theorem 2 the cross-check DOES validate."""
        import eb_crosscheck
        import eb_reference
        try:
            eb_reference.load_reference()
        except eb_reference.ReferenceUnavailable as exc:
            self.skipTest(str(exc))
        rng = np.random.default_rng(4242)
        z = rng.choice([-1.0, 0.0, 1.0], size=300, p=[0.25, 0.5, 0.25])
        rep = eb_crosscheck.crosscheck_report(z, 0.00625)
        self.assertTrue(rep["reference_available"])
        self.assertLess(rep["centre_max_abs_diff"], 1e-12)
        self.assertLess(rep["intrinsic_time_roundtrip_max_abs_diff"], 1e-12)

    def test_the_crosscheck_stitching_disagreement_is_recorded(self):
        """The disagreement is EVIDENCE and must stay on the record."""
        import eb_crosscheck
        import eb_reference
        try:
            eb_reference.load_reference()
        except eb_reference.ReferenceUnavailable as exc:
            self.skipTest(str(exc))
        rep = eb_crosscheck.crosscheck_report(
            np.array([1.0, -1.0, 0.0, 1.0] * 50), 0.00625)
        dis = rep["stitching_disagreement"]
        rel = dis["relative"]
        self.assertTrue(all(r < 0 for r in rel),
                        f"the cross-check is narrower than the authors'; that "
                        f"direction is the finding: {rel}")
        self.assertTrue(abs(rel[0]) > abs(rel[-1]),
                        "the gap should shrink with v")


# ===========================================================================
# THE v2 ACTUAL-LIVE SNAPSHOT, and the preservation of v1's.
# Root, issue 12 comment 5754619899: "new v2 actual-live snapshot plus
# preserved v1, paired latent seed coordinates".
# ===========================================================================
class TestV2Snapshot(unittest.TestCase):
    """The v2 snapshot exists, verifies, and did not disturb v1's."""

    HERE = pathlib.Path(__file__).resolve().parent
    V1 = HERE / "pinned" / "PINNED.json"
    V2 = HERE / "pinned_v2" / "PINNED_V2.json"

    def test_v1_snapshot_is_preserved_and_still_verifies(self):
        """v1 must remain byte-exact and reproducible, whatever v2 does."""
        man = json.loads(self.V1.read_text())
        for name, want in man["files"].items():
            got = hashlib.sha256(
                (self.V1.parent / name).read_bytes()).hexdigest()
            self.assertEqual(got, want, f"v1 pinned {name} changed")
        self.assertEqual(man["source_commit"],
                         "577687799e8588077c036b4d94f1afc839d78e4f")

    def test_v2_snapshot_verifies_against_its_manifest(self):
        if not self.V2.exists():
            self.skipTest("v2 snapshot not built on this host; "
                          "run vsnapshot_v2.py --write")
        man = json.loads(self.V2.read_text())
        self.assertEqual(man["version"], "v2-cpu-validation")
        for name, want in man["files"].items():
            got = hashlib.sha256(
                (self.V2.parent / name).read_bytes()).hexdigest()
            self.assertEqual(got, want, f"v2 pinned {name} does not verify")

    def test_the_two_snapshots_are_distinct_and_v2_records_the_difference(self):
        """A fresh snapshot is only worth taking if it captured a change."""
        if not self.V2.exists():
            self.skipTest("v2 snapshot not built on this host")
        v1 = json.loads(self.V1.read_text())
        v2 = json.loads(self.V2.read_text())
        self.assertNotEqual(v1["source_commit"], v2["source_commit"])
        self.assertEqual(v2["parent_v1_snapshot"]["source_commit"],
                         v1["source_commit"])
        changed = set(v2["changed_since_v1_pin"])
        actually = {n for n, h in v2["files"].items()
                    if v1["files"].get(n) != h}
        self.assertEqual(changed, actually,
                         "the manifest's changed-file list must match the bytes")

    def test_the_snapshot_builder_never_imports_the_forbidden_tree(self):
        """vsnapshot_v2.py is exempt from the STATIC name scan, so the narrower
        property -- that it never IMPORTS the live rule -- is checked here."""
        src = (self.HERE / "vsnapshot_v2.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertFalse(a.name.startswith("lab_"), a.name)
            elif isinstance(node, ast.ImportFrom):
                self.assertFalse((node.module or "").startswith("lab_"),
                                 node.module)
            elif isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                self.assertNotIn(name, ("import_module", "spec_from_file_location",
                                        "module_from_spec", "run_path",
                                        "load_module", "__import__"))

    def test_the_wording_corrections_are_carried_forward(self):
        if not self.V2.exists():
            self.skipTest("v2 snapshot not built on this host")
        man = json.loads(self.V2.read_text())
        corr = man["carried_forward_corrections"]
        for key in ("stopped_roster", "exact_feasible_set",
                    "v1_did_not_validate_11"):
            self.assertIn(key, corr)
        self.assertIn("does NOT identify", corr["stopped_roster"])
        self.assertIn("CONSERVATIVE ENCLOSURES", corr["exact_feasible_set"])
        self.assertIn("PAIRED means", man["pairing"])


# ===========================================================================
# THE SMOKE-TO-BUDGET REPAIRS, and the v2 COMPARISON BINDING.
# Root disposition reviews/v2_bindings_root_disposition_20260921_0343.md,
# ranked actions 1 and 2; COORDINATOR_DECISIONS revision 17 item 85.
#
# Every fixture here is NON-TIMED: the seconds are synthetic constants, so the
# repairs are checked without re-timing anything and without disturbing the
# accepted primary measurements.
# ===========================================================================
class _SmokeGuard:
    """The two methods assert_smoke_holds_no_effect_record actually uses."""

    def __init__(self, root):
        self.root = pathlib.Path(root)

    def path(self, name):
        p = self.root / name
        p.mkdir(parents=True, exist_ok=True)
        return p


def _smoke_balanced(c1_1000, c1_2000, c2_1000, c2_2000):
    pts = []
    for cell, h, s in (("C1", 1000, c1_1000), ("C1", 2000, c1_2000),
                       ("C2", 1000, c2_1000), ("C2", 2000, c2_2000)):
        pts.append({"cell": cell, "N_max": h, "programs": 5,
                    "seconds": s * 5, "seconds_per_program": s,
                    "record_bytes_measured_not_written": 1000,
                    "trials": 20, "enrolled_pairs": 100, "looks": 100,
                    "band_evaluations": 100, "enclosure_updates": 100,
                    "enclosure_updates_per_pair": 1.0})
    return {"protocol_smoke": True, "event_schedule": "v2_all_looks_batched",
            "design": "synthetic non-timed fixture", "balanced": True,
            "unique_programs": 20, "unique_program_indices": 20,
            "program_index_rule": "incrementing", "namespace": 1,
            "measures_only": ["wall_clock_seconds"],
            "seeds": "discarded, never reused", "note": "fixture",
            "points": pts, "total_seconds": sum(p["seconds"] for p in pts),
            "total_programs": 20, "peak_rss_bytes": 100_000_000}


def _smoke_v1(c1_2000, c2_1000):
    pts = []
    for cell, h, s, n in (("C1", 2000, c1_2000, 10), ("C2", 1000, c2_1000, 10)):
        pts.append({"cell": cell, "N_max": h, "programs": n,
                    "seconds": s * n, "seconds_per_program": s,
                    "record_bytes_measured_not_written": 1000,
                    "trials": 40, "enrolled_pairs": 100, "looks": 100,
                    "band_evaluations": 100, "enclosure_updates": 100,
                    "enclosure_updates_per_pair": 1.0})
    return {"protocol_smoke": True, "event_schedule": "v1_reduced",
            "design": "synthetic non-timed v1 fixture", "balanced": False,
            "unique_programs": 20, "unique_program_indices": 10,
            "program_index_rule": "group-local", "namespace": 1,
            "measures_only": ["wall_clock_seconds"],
            "seeds": "discarded, never reused", "note": "fixture",
            "points": pts, "total_seconds": sum(p["seconds"] for p in pts),
            "total_programs": 20, "peak_rss_bytes": 100_000_000}


class TestSmokeToBudgetRepairs(unittest.TestCase):

    HERE = pathlib.Path(__file__).resolve().parent

    def setUp(self):
        sys.path.insert(0, str(self.HERE))
        import vrun
        self.vrun = vrun
        self.cfg = json.loads((self.HERE / "cells.json").read_text())

    # -- defect 1: the runner rejected its own metadata --------------------
    def test_the_allowlist_accepts_the_metadata_run_smoke_writes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sd = pathlib.Path(td) / "smoke"
            sd.mkdir(parents=True)
            (sd / "timing.json").write_text(
                json.dumps(_smoke_balanced(1, 2, 1, 2)))
            self.vrun.assert_smoke_holds_no_effect_record(_SmokeGuard(td))

    def test_the_allowlist_still_rejects_an_effect_column(self):
        import tempfile
        rec = _smoke_balanced(1, 2, 1, 2)
        rec["coverage_rate"] = 0.95          # an outcome field
        with tempfile.TemporaryDirectory() as td:
            sd = pathlib.Path(td) / "smoke"
            sd.mkdir(parents=True)
            (sd / "timing.json").write_text(json.dumps(rec))
            with self.assertRaises(SystemExit) as cm:
                self.vrun.assert_smoke_holds_no_effect_record(_SmokeGuard(td))
            self.assertIn("coverage_rate", str(cm.exception))

    def test_every_key_run_smoke_writes_is_on_the_allowlist(self):
        """Read the writer's own literal keys rather than a copy of them."""
        src = (self.HERE / "vrun.py").read_text()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_smoke")
        written = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        written.add(k.value)
        missing = written - self.vrun.SMOKE_PERMITTED_KEYS
        self.assertEqual(missing, set(),
                         f"run_smoke writes keys its own validator rejects: "
                         f"{sorted(missing)}")

    # -- defect 2: the tier selector overwrote C1 with C2 -------------------
    def test_the_selector_no_longer_discards_a_cell(self):
        """The root's own fixture: C1 100/400 against C2 1/2."""
        b = self.vrun.select_tier(_smoke_balanced(100, 400, 1, 2), self.cfg)
        self.assertEqual(b["projection_inputs"]["both_cells_at_2000"],
                         {"C1": 400, "C2": 2})
        self.assertEqual(b["projection_inputs"]["both_cells_at_1000"],
                         {"C1": 100, "C2": 1})
        self.assertEqual(b["s_per_program_2000"], 400)
        self.assertEqual(b["s_per_program_1000"], 100)

    def test_scaling_the_discarded_cell_now_changes_the_projection(self):
        """Under the defect, multiplying C1 by 1,000 changed NO output."""
        a = self.vrun.select_tier(_smoke_balanced(100, 400, 1, 2), self.cfg)
        b = self.vrun.select_tier(
            _smoke_balanced(100_000, 400_000, 1, 2), self.cfg)
        self.assertNotEqual(a["s_per_program_2000"], b["s_per_program_2000"])
        self.assertNotEqual([e["seconds_projected"] for e in a["ladder"]],
                            [e["seconds_projected"] for e in b["ladder"]])

    def test_the_aggregation_rule_is_the_maximum_and_says_so(self):
        agg = self.vrun.aggregate_horizon_costs(
            _smoke_balanced(1.0, 5.0, 3.0, 2.0))
        self.assertEqual(agg["rule"], "maximum measured cell cost per horizon")
        self.assertTrue(agg["both_cell_inputs_retained"])
        self.assertEqual(agg["by_horizon"][1000]["selected_cell"], "C2")
        self.assertEqual(agg["by_horizon"][2000]["selected_cell"], "C1")
        self.assertEqual(agg["by_horizon"][1000]["seconds_per_program"], 3.0)
        self.assertEqual(agg["by_horizon"][2000]["seconds_per_program"], 5.0)

    def test_a_duplicated_cell_horizon_is_refused_not_collapsed(self):
        rec = _smoke_balanced(1, 2, 1, 2)
        rec["points"].append(dict(rec["points"][0]))
        with self.assertRaises(SystemExit):
            self.vrun.aggregate_horizon_costs(rec)

    # -- the v1 path is preserved ------------------------------------------
    def test_the_v1_selection_path_is_untouched_by_the_repair(self):
        v1 = self.vrun.select_tier(_smoke_v1(2.0, 1.0), self.cfg)
        self.assertEqual(v1["s_per_program_2000"], 2.0)   # C1's, as before
        self.assertEqual(v1["s_per_program_1000"], 1.0)   # C2's, as before
        self.assertAlmostEqual(v1["beta"], 1.0, places=12)
        self.assertNotIn("projection_inputs", v1)

    def test_v1_smoke_restores_group_local_program_indices(self):
        """Defect 3: program_base incremented across BOTH v1 groups, moving
        the old C2 group from indices 0-9 to 10-19."""
        src = (self.HERE / "vrun.py").read_text()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_smoke")
        body = ast.get_source_segment(src, fn) or ""
        self.assertIn("group_local_indices", body)
        self.assertIn("SCHEDULE_V1", body)
        # and the rule is recorded in the record the budget reads
        self.assertIn("program_index_rule", self.vrun.SMOKE_PERMITTED_KEYS)

    # -- the reference workload is accounted for ---------------------------
    def test_the_reference_workload_is_priced_but_gates_nothing(self):
        b = self.vrun.select_tier(_smoke_balanced(1, 2, 1, 2), self.cfg)
        acct = b["reference_workload_accounting"]
        self.assertFalse(acct["included_in_the_admissibility_gate"])
        for e in b["ladder"]:
            # the frozen gate still reads the primary projection alone
            self.assertEqual(
                e["admissible"],
                bool(e["within_seconds"] and e["within_bytes"]
                     and e["within_peak_rss"]))

    def test_an_absent_reference_receipt_is_unresolved_not_zero(self):
        real = self.vrun.REFERENCE_TIMING
        try:
            self.vrun.REFERENCE_TIMING = real.parent / "does_not_exist.json"
            w = self.vrun.reference_workload_costs()
            self.assertFalse(w["resolved"])
            self.assertIn("UNRESOLVED", w["unresolved_reason"])
            self.assertNotIn("seconds_per_program_by_horizon", w)
        finally:
            self.vrun.REFERENCE_TIMING = real

    def test_the_reference_receipts_provenance_limits_are_recorded(self):
        w = self.vrun.reference_workload_costs()
        if not w["resolved"]:
            self.skipTest("no reference receipt deposited on this host")
        self.assertIn("workload_declaration_status", w)
        # AMENDED 2026-09-21.  This test previously asserted the workload was
        # "NOT YET DECLARED", which was the correct assertion while it was not
        # declared.  The root has now specified it exactly and it is frozen, so
        # the test asserts the frozen declaration instead.
        self.assertEqual(w["workload_declaration_status"], "DECLARED AND FROZEN")
        self.assertTrue(w["receipt_provenance_limits"])

    def test_the_reference_workload_is_frozen_at_eight_calls_per_program(self):
        """The root's specification, checked as a number and not as prose."""
        wl = self.vrun.REFERENCE_WORKLOAD
        self.assertEqual(tuple(wl["scores_per_trial"]), ("H", "D"))
        self.assertEqual(wl["calls_per_score_per_trial"], 1)
        self.assertEqual(wl["calls_per_trial"], 2)
        self.assertEqual(wl["trials_per_program"], 4)
        self.assertEqual(wl["calls_per_program"], 8)
        self.assertFalse(wl["may_be_silently_dropped"])
        self.assertIn("NONE", wl["decision_authority"])

    def test_the_frozen_amendment_carries_before_and_after_text(self):
        am = self.vrun.REFERENCE_WORKLOAD_AMENDMENT
        self.assertIn("pre-full-calibration", am["kind"])
        self.assertIn("NOT YET DECLARED", am["before"])
        self.assertIn("EIGHT reference calls per program", am["after"])
        self.assertTrue(am["what_did_not_change"])

    def test_the_false_lower_bound_explanation_is_gone(self):
        """The root established the premise was false; it must not survive."""
        w = self.vrun.reference_workload_costs()
        if not w["resolved"]:
            self.skipTest("no reference receipt deposited on this host")
        blob = " ".join(w["receipt_provenance_limits"]).lower()
        self.assertNotIn("lower bound", blob)
        self.assertIn("also included generation and row serialization", blob)


class TestFailClosedTotalWorkloadGuard(unittest.TestCase):
    """The SEPARATE total-workload resource guard must actually REFUSE.

    A gate that has never fired is not known to be a gate, so every refusal
    class is fired here and the enforcement is asserted to RAISE.
    """

    HERE = pathlib.Path(__file__).resolve().parent

    def setUp(self):
        sys.path.insert(0, str(self.HERE))
        import vrun
        self.vrun = vrun
        self.cfg_json = json.loads((self.HERE / "cells.json").read_text())
        self.cap = float(self.cfg_json["budget"]["hard_limits"]["seconds"])

    def _budget(self, **over):
        entry = {"tier": "T1", "programs_total": 28000, "N_max": 2000,
                 "seconds_projected": 100.0, "bytes_projected": 1.0,
                 "peak_rss_projected": 1, "within_seconds": True,
                 "within_bytes": True, "within_peak_rss": True,
                 "admissible": True,
                 "reference_seconds_projected": 200.0,
                 "total_seconds_projected": 300.0,
                 "reference_cost_unresolved": False}
        entry.update(over)
        return {"selected_tier": "T1", "ladder": [entry], "paused": False,
                "reference_workload": {"combined_workload_receipt": {
                    "present": True, "identities": dict(self.IDS),
                    "planned_groups": 12, "groups_total": 12}}}

    #: Guard v2 requires the projection to be BOUND to the run it prices.  An
    #: unbound proposal is refused as `identity_unverifiable`, which is the
    #: point, so the positive control has to supply identities.
    IDS = {"code": "t", "config": "t", "policy": "operational",
           "workload": "eight_call", "receipt": "t"}

    def _proposed(self, **over):
        p = {"identities": dict(self.IDS)}
        p.update(over)
        return p

    def test_an_authorized_total_passes_and_does_not_raise(self):
        v = self.vrun.total_workload_guard(self._budget(), self.cfg_json,
                                           self._proposed())
        self.assertTrue(v["authorized"], v.get("refusal"))
        self.vrun.enforce_total_workload_guard(v)        # must not raise

    def test_an_unbound_projection_is_refused(self):
        """v2: a projection nothing ties to this run cannot authorize it."""
        v = self.vrun.total_workload_guard(self._budget(), self.cfg_json)
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "identity_unverifiable")

    def test_a_nan_projection_is_refused(self):
        """``nan > cap`` is False, so v1 AUTHORIZED this."""
        v = self.vrun.total_workload_guard(
            self._budget(reference_seconds_projected=float("nan"),
                         total_seconds_projected=float("nan")),
            self.cfg_json, self._proposed())
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "non_finite_projection")

    def test_a_negative_projection_is_refused(self):
        v = self.vrun.total_workload_guard(
            self._budget(reference_seconds_projected=-1e9,
                         total_seconds_projected=-1e9),
            self.cfg_json, self._proposed())
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "non_finite_projection")

    def test_the_byte_and_rss_caps_are_checked_too(self):
        """v1 checked ONLY seconds while the config caps three things."""
        for field in ("bytes_projected", "peak_rss_projected"):
            v = self.vrun.total_workload_guard(
                self._budget(**{field: 1.0e12}), self.cfg_json, self._proposed())
            self.assertFalse(v["authorized"], field)
            self.assertEqual(v["refusal_class"], "projected_over_cap", field)

    def test_a_missing_combined_receipt_is_refused(self):
        b = self._budget()
        b["reference_workload"] = {"combined_workload_receipt": {"present": False}}
        v = self.vrun.total_workload_guard(b, self.cfg_json, self._proposed())
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "missing_combined_receipt")

    def test_an_identity_mismatch_is_refused(self):
        v = self.vrun.total_workload_guard(
            self._budget(), self.cfg_json,
            self._proposed(identities=dict(self.IDS, policy="oracle")))
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "identity_mismatch")

    def test_short_group_accounting_is_refused(self):
        b = self._budget()
        b["reference_workload"]["combined_workload_receipt"]["groups_total"] = 5
        v = self.vrun.total_workload_guard(b, self.cfg_json, self._proposed())
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "group_accounting_short")

    def test_the_tier_is_priced_after_the_override_not_before(self):
        """v1 priced the AUTOMATIC tier and let an override change what ran."""
        b = self._budget()
        b["ladder"].append({"tier": "T4", "programs_total": 28000, "N_max": 1000,
                            "seconds_projected": 10.0, "bytes_projected": 1.0,
                            "peak_rss_projected": 1, "admissible": True,
                            "reference_seconds_projected": 20.0,
                            "total_seconds_projected": 30.0,
                            "reference_cost_unresolved": False})
        v = self.vrun.total_workload_guard(b, self.cfg_json,
                                           self._proposed(tier_override="T4"))
        self.assertEqual(v["automatic_tier"], "T1")
        self.assertEqual(v["selected_tier"], "T4")
        self.assertEqual(v["total_seconds_projected"], 30.0)
        self.assertTrue(v["priced_after_override"])

    def test_a_proposal_larger_than_the_priced_tier_is_rescaled(self):
        """Caps must meet the ACTUAL proposed arguments, not the priced tier."""
        v = self.vrun.total_workload_guard(
            self._budget(), self.cfg_json,
            self._proposed(programs_total=28000 * 100))
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "total_over_cap")

    def test_an_unresolved_total_refuses_and_raises(self):
        v = self.vrun.total_workload_guard(
            self._budget(reference_cost_unresolved=True,
                         reference_seconds_projected=None,
                         total_seconds_projected=None), self.cfg_json)
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "unresolved_total_cost")
        with self.assertRaises(self.vrun.TotalResourceRefusal):
            self.vrun.enforce_total_workload_guard(v)

    def test_an_over_cap_total_refuses_even_when_the_primary_is_admissible(self):
        v = self.vrun.total_workload_guard(
            self._budget(reference_seconds_projected=self.cap * 2,
                         total_seconds_projected=self.cap * 2 + 100.0),
            self.cfg_json)
        self.assertTrue(v["primary_only_admissible"])
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "total_over_cap")
        with self.assertRaises(self.vrun.TotalResourceRefusal):
            self.vrun.enforce_total_workload_guard(v)

    def test_no_selected_tier_refuses_and_raises(self):
        b = self._budget()
        b["selected_tier"] = None
        v = self.vrun.total_workload_guard(b, self.cfg_json)
        self.assertFalse(v["authorized"])
        self.assertEqual(v["refusal_class"], "no_tier_selected")
        with self.assertRaises(self.vrun.TotalResourceRefusal):
            self.vrun.enforce_total_workload_guard(v)

    def test_the_guard_carries_no_exemption_list(self):
        v = self.vrun.total_workload_guard(self._budget(), self.cfg_json)
        self.assertEqual(v["exemptions"], [])
        self.assertTrue(v["separate_from_the_scientific_tier_selection"])
        self.assertTrue(v["frozen_selection_rule_unchanged"])


class TestOperationalPolicyAdapter(unittest.TestCase):
    """The versioned CPU adapter for the DECLARED live observation policy."""

    HERE = pathlib.Path(__file__).resolve().parent
    CAP = 100.0

    def setUp(self):
        sys.path.insert(0, str(self.HERE))
        import vband, vpolicy
        self.vband, self.vpolicy = vband, vpolicy

    def _state(self, ell, cost, revealed_arm, success=1):
        vb = self.vband
        rev = vb.Episode.pending("r", self.CAP).finalized(int(success), cost)
        pend = vb.Episode.pending("p", self.CAP).with_elapsed_cost(ell)
        return (rev, pend) if revealed_arm == "candidate" else (pend, rev)

    def test_the_adapter_is_versioned(self):
        c = self.vpolicy.policy_constants()
        self.assertEqual(c["policy_id"], "cpu-operational-policy-adapter")
        self.assertRegex(c["policy_version"], r"^\d+\.\d+\.\d+$")
        self.assertFalse(c["imports_the_monitored_source"])
        self.assertEqual(c["certificate_eps"], 1e-9)
        self.assertEqual(c["tol"], 0.05)

    def test_the_executed_predicates_are_not_the_division_form(self):
        """The root's 05:32 correction, asserted against the source text."""
        text = (self.HERE / "vpolicy.py").read_text()
        self.assertIn("(1.0 - tol) * ell > l_r + eps", text)
        self.assertIn("ell > (1.0 - tol) * l_r + eps", text)

    def test_the_six_reproduced_states_of_the_root_ledger(self):
        """All six states the root enumerated, adapter side, by enumeration."""
        expect = {
            (10.526315789473685, 10.0, "incumbent"): (-1.0, 0.0),
            (10.526315789473685, 10.0, "candidate"): (0.0, 1.0),
            (9.5, 10.0, "incumbent"): (-1.0, 1.0),
            (9.5, 10.0, "candidate"): (-1.0, 1.0),
            (38.0, 40.0, "incumbent"): (-1.0, 1.0),
            (38.0, 40.0, "candidate"): (-1.0, 1.0),
        }
        for (ell, cost, arm), want in expect.items():
            cand, inc = self._state(ell, cost, arm)
            got = self.vpolicy.operational_hierarchy_bounds(cand, inc)
            self.assertEqual(got, want, f"ell={ell} cost={cost} arm={arm}")

    def test_both_boundaries_survive_epsilon_zero(self):
        """A margin of exactly zero is a difference of FORM, not of epsilon."""
        for ell, cost in ((10.526315789473685, 10.0), (9.5, 10.0), (38.0, 40.0)):
            cand, inc = self._state(ell, cost, "candidate")
            m = self.vpolicy.certificate_margins(cand, inc)
            self.assertTrue(m["forward_margin"] == 0.0
                            or m["reverse_margin"] == 0.0,
                            f"ell={ell} cost={cost}: {m}")
            at_eps_0 = self.vpolicy.operational_hierarchy_bounds(
                cand, inc, eps=0.0)
            at_eps = self.vpolicy.operational_hierarchy_bounds(cand, inc)
            self.assertEqual(at_eps_0, at_eps)

    def test_the_operational_enclosure_always_contains_the_oracles(self):
        """Containment is the SEPARATE check; a failure would be unsound."""
        import itertools
        costs = (0.0, 1.0, 9.5, 10.0, 10.526315789473685, 38.0, 40.0, 41.0)
        checked = wider = 0
        for ell, cost, arm, succ in itertools.product(
                costs, costs, ("candidate", "incumbent"), (0, 1)):
            if ell > self.CAP or cost > self.CAP:
                continue
            cand, inc = self._state(ell, cost, arm, success=succ)
            rep = self.vpolicy.containment_report(cand, inc)
            for score in ("hierarchy", "success"):
                checked += 1
                self.assertTrue(rep[score]["operational_contains_oracle"],
                                f"{score} ell={ell} cost={cost} arm={arm} "
                                f"succ={succ}: {rep[score]}")
                wider += int(rep[score]["operational_strictly_wider"])
        self.assertGreater(checked, 200)
        self.assertGreater(wider, 0, "the two policies must actually differ "
                                     "somewhere, or this check is vacuous")

    def test_the_monitor_shares_everything_except_the_policy(self):
        vb, vp = self.vband, self.vpolicy
        mon = vp.OperationalMonitor(cost_cap=self.CAP)
        self.assertIsInstance(mon, vb.ValidationMonitor)
        self.assertEqual(mon.alpha_gate, vb.ALPHA_GATE)
        self.assertEqual(mon.rho, vb.RHO)
        self.assertEqual(mon.delta, vb.DELTA)
        self.assertEqual(mon.n_min, vb.N_MIN)
        self.assertEqual(vp.OperationalMonitor._refresh.__qualname__,
                         "OperationalMonitor._refresh")
        # everything else must be INHERITED, not re-implemented
        for name in ("enroll", "finalize", "observe_elapsed_cost", "band",
                     "look", "score_bounds"):
            self.assertIs(getattr(vp.OperationalMonitor, name),
                          getattr(vb.ValidationMonitor, name), name)

    def test_the_certificate_branches_actually_fire(self):
        """A branch that never fires is not known to be implemented."""
        mon = self.vpolicy.OperationalMonitor(cost_cap=self.CAP)
        mon.enroll(1, "AB", ("C", 1), ("I", 1))
        mon.finalize(("I", 1), 1, 10.0)
        mon.observe_elapsed_cost(("C", 1), 9.6)      # reverse certificate
        self.assertEqual(mon.branch_counts["reverse_certificate"], 1)
        mon.observe_elapsed_cost(("C", 1), 11.0)     # forward certificate
        self.assertEqual(mon.branch_counts["forward_certificate"], 1)
        enc = mon.pairs[0].hierarchy
        self.assertEqual((enc.lo, enc.hi), (-1.0, -1.0))


class TestV2AllLookSchedule(unittest.TestCase):
    """v2 must compare every tick through N+W; v1 must keep its skip."""

    HERE = pathlib.Path(__file__).resolve().parent

    def setUp(self):
        sys.path.insert(0, str(self.HERE))
        import vcompare
        self.vcompare = vcompare

    def tearDown(self):
        self.vcompare.select_snapshot("v1")

    def test_the_snapshot_defaults_are_the_two_the_root_specified(self):
        d = self.vcompare.SNAPSHOT_DEFAULTS
        self.assertEqual(d["v1"]["policy"], "oracle")
        self.assertFalse(d["v1"]["compare_drain_looks"])
        self.assertEqual(d["v2"]["policy"], "operational")
        self.assertTrue(d["v2"]["compare_drain_looks"])

    def test_resolution_of_auto_and_of_explicit_overrides(self):
        vc = self.vcompare
        self.assertEqual(vc.resolve_policy("v1", "auto"), "oracle")
        self.assertEqual(vc.resolve_policy("v2", "auto"), "operational")
        self.assertEqual(vc.resolve_policy("v2", "oracle"), "oracle")
        self.assertFalse(vc.resolve_drain_schedule("v1", "auto"))
        self.assertTrue(vc.resolve_drain_schedule("v2", "auto"))
        self.assertTrue(vc.resolve_drain_schedule("v1", "all"))
        self.assertFalse(vc.resolve_drain_schedule("v2", "final-only"))
        with self.assertRaises(vc.ComparisonRefusal):
            vc.resolve_policy("v2", "whatever")
        with self.assertRaises(vc.ComparisonRefusal):
            vc.resolve_drain_schedule("v2", "whatever")

    def test_the_csv_carries_a_drain_look_column(self):
        self.assertIn("drain_look", self.vcompare.LOOK_FIELDS)

    def test_the_drain_schedule_changes_the_number_of_looks(self):
        """The repair is asserted on executed look counts, not on prose."""
        vc = self.vcompare
        vc.select_snapshot("v2")
        cfg = vc.load_frozen_config()
        pinned = vc.verify_and_load_pinned(verbose=False)
        gen = vc.FrozenGenerator(cfg)
        st = gen.build("C1", 0, 0)
        n_max, fin = st.n_max, st.finalization_tick
        seen = {}
        for drain in (False, True):
            ledger = vc.DefectLedger()
            rows = []

            class _W:
                def writerow(self, row):
                    rows.append(row)

            out = vc.compare_cell_stream(st, cfg, pinned, ledger, _W(), 10**9,
                                         verbose=False, policy="oracle",
                                         compare_drain_looks=drain)
            seen[drain] = (out.looks, out.drain_looks,
                           sum(1 for r in rows if r.get("drain_look")))
        self.assertEqual(seen[False][1], 0, "v1 mode must take no drain look")
        self.assertEqual(seen[False][2], 0, "v1 mode must write no drain row")
        self.assertEqual(seen[False][0], n_max + 1)
        self.assertEqual(seen[True][0], fin)
        self.assertEqual(seen[True][1], fin - n_max - 1)
        self.assertEqual(seen[True][2], fin - n_max - 1)


class TestV2ComparisonBinding(unittest.TestCase):
    """vcompare must bind the snapshot it compares against, and say which."""

    HERE = pathlib.Path(__file__).resolve().parent

    def setUp(self):
        sys.path.insert(0, str(self.HERE))
        import vcompare
        self.vcompare = vcompare

    def tearDown(self):
        self.vcompare.select_snapshot("v1")      # leave the default in place

    def test_v1_is_the_default_and_resolves_to_v1s_own_paths(self):
        v = self.vcompare.select_snapshot("v1")
        self.assertEqual(v["version"], "v1-cpu-validation")
        self.assertEqual(self.vcompare.PINNED_DIR.name, "pinned")
        self.assertEqual(self.vcompare.PROTOCOL_PATH.name, "PROTOCOL.md")
        self.assertEqual(self.vcompare.RESULTS_ROOT.name, "live_ab_validation")

    def test_v2_resolves_to_the_regenerated_snapshot_and_the_v2_tree(self):
        v = self.vcompare.select_snapshot("v2")
        self.assertEqual(v["version"], "v2-cpu-validation")
        self.assertEqual(self.vcompare.PINNED_DIR.name, "pinned_v2")
        self.assertEqual(self.vcompare.PROTOCOL_PATH.name, "PROTOCOL_V2.md")
        self.assertEqual(self.vcompare.RESULTS_ROOT.name,
                         "live_ab_validation_v2")

    def test_the_v2_write_guard_refuses_the_v1_results_tree(self):
        """PRESERVE v1: a v2 comparison must not be able to write into it."""
        self.vcompare.select_snapshot("v2")
        with self.assertRaises(SystemExit):
            self.vcompare.guarded_out_dir(
                str(self.HERE.parents[1] / "results" / "live_ab_validation"))

    def test_an_unknown_snapshot_is_refused(self):
        with self.assertRaises(SystemExit):
            self.vcompare.select_snapshot("v3")
        self.vcompare.select_snapshot("v1")

    def test_the_binding_records_recomputed_hashes_and_both_disclosures(self):
        self.vcompare.select_snapshot("v2")
        if not self.vcompare.PINNED_MANIFEST.is_file():
            self.skipTest("v2 snapshot not built on this host")
        pinned = self.vcompare.verify_and_load_pinned(verbose=False)
        b = self.vcompare.snapshot_binding(pinned)
        self.assertEqual(b["snapshot_id"], "v2")
        man = json.loads(self.vcompare.PINNED_MANIFEST.read_text())
        self.assertEqual(b["snapshot_file_sha256_recomputed_here"],
                         man["files"])
        self.assertEqual(b["snapshot_source_commit"], man["source_commit"])
        self.assertIsNotNone(b["operative_protocol_sha256"])
        self.assertIsNotNone(b["base_protocol_sha256"])
        # the two disclosed, unrepaired limitations travel with the artifact
        self.assertFalse(b["epsilon_policy"]["repaired_here"])
        self.assertFalse(b["stopped_target"]["repaired_here"])
        self.assertIn("lab_data.py", b["stopped_target"]["disclosed_unrepaired_claim"])

    def test_the_replay_command_names_the_snapshot_it_came_from(self):
        self.vcompare.select_snapshot("v2")
        src = (self.HERE / "vcompare.py").read_text()
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == "replay_command")
        body = ast.get_source_segment(src, fn) or ""
        self.assertIn("--snapshot", body)

    def test_the_boundary_analysis_does_not_blame_epsilon_by_default(self):
        """A zero margin is a difference of algebraic form, not of epsilon."""
        rows = [{"defect_class": "per_pair_enclosure_endpoint",
                 "ell": 10.0 / 0.95, "revealed_cost": 10.0,
                 "enc12_lo": -1.0, "enc12_hi": -1.0,
                 "enc11_lo": -1.0, "enc11_hi": 0.0}]
        a = self.vcompare.certificate_boundary_analysis(rows, 1e-9, 0.05)
        self.assertEqual(a["rows_classified"], 1)
        self.assertEqual(a["margin_exactly_zero"], 1)
        self.assertEqual(a["margin_inside_epsilon"], 0)
        self.assertEqual(a["pinned_encloses_candidate"], 1)


class TestCrosscheckRepairAndWidthDiagnostic(unittest.TestCase):
    """The B**2 repair, and the replacement width diagnostic's discipline."""

    HERE = pathlib.Path(__file__).resolve().parent

    def setUp(self):
        sys.path.insert(0, str(self.HERE / "reference"))
        sys.path.insert(0, str(self.HERE))
        import eb_crosscheck
        self.x = eb_crosscheck

    def test_the_original_defective_boundary_is_preserved_unchanged(self):
        """A failed calculation that was quoted must stay legible."""
        import numpy as np
        probe = np.array([10.0, 50.0, 200.0, 1000.0, 5000.0])
        got = self.x.stitched_boundary(probe, 0.003125)
        # the exact values the audit tabulated for the ORIGINAL formula
        want = [28.5871851682, 50.4559119055, 84.0291099487,
                165.2729126644, 347.3456673770]
        for g, w in zip(got, want):
            self.assertAlmostEqual(float(g), w, places=8)

    def test_the_repair_restores_B_squared_under_the_radical(self):
        """sqrt(A) + B  ->  sqrt(A + B**2) + B, and nothing else moves."""
        import numpy as np
        probe = np.array([10.0, 50.0, 200.0, 1000.0, 5000.0])
        a = float(0.003125)
        k1 = (self.x.ETA_PARAM ** 0.25 + self.x.ETA_PARAM ** -0.25) / np.sqrt(2)
        k2 = (np.sqrt(self.x.ETA_PARAM) + 1.0) / 2.0
        v = probe
        ell = (self.x.S_PARAM * np.log(np.log(
            self.x.ETA_PARAM * v / self.x.V_OPT))
            + np.log(self.x._zeta(self.x.S_PARAM)
                     / (a * np.log(self.x.ETA_PARAM) ** self.x.S_PARAM)))
        A = k1 * k1 * v * ell
        B = k2 * (self.x.HI - self.x.LO) * ell
        np.testing.assert_allclose(
            self.x.stitched_boundary(v, a), np.sqrt(A) + B, rtol=0, atol=1e-12)
        np.testing.assert_allclose(
            self.x.stitched_boundary_repaired(v, a),
            np.sqrt(A + B ** 2) + B, rtol=0, atol=1e-12)

    def test_the_repaired_boundary_matches_the_authors_exactly(self):
        """A CONSEQUENCE of the repair, never its target: nothing was tuned."""
        import numpy as np
        try:
            import eb_reference as ref
            ref.load_reference()
            from confseq import boundaries
        except Exception:                                   # noqa: BLE001
            self.skipTest("the compiled author reference is not built here")
        probe = np.array([10.0, 50.0, 200.0, 1000.0, 5000.0])
        a = 0.003125
        mine = self.x.stitched_boundary_repaired(probe, a)
        theirs = np.array([boundaries.poly_stitching_bound(
            float(v), a, self.x.V_OPT, self.x.HI - self.x.LO,
            self.x.S_PARAM, self.x.ETA_PARAM) for v in probe])
        np.testing.assert_array_equal(mine, theirs)

    def test_the_withdrawn_note_is_preserved_with_its_banner(self):
        p = self.HERE / "BOUNDARY_WIDTH_AT_OUR_OPERATING_POINT.md"
        self.assertTrue(p.is_file(), "the withdrawn note must not be deleted")
        head = p.read_text()[:4000].upper()
        self.assertIn("WITHDRAWN", head)

    def test_the_diagnostic_declares_family_scale_alpha_and_clock(self):
        import eb_width_diagnostic as d
        src = (self.HERE / "reference" / "eb_width_diagnostic.py").read_text()
        # it must CALL the selected reference rather than re-specify a boundary
        self.assertIn("reference_bands", src)
        # The module NAMES the withdrawn note's three defects in prose, so the
        # scan must look at what the code CALLS, not at what it says --
        # otherwise explaining a mistake would be indistinguishable from
        # repeating it. Identifiers only: no string literal is examined.
        tree = ast.parse(src)
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                if name:
                    called.add(name)
            elif isinstance(node, (ast.Name, ast.Attribute)):
                called.add(getattr(node, "attr", None)
                           or getattr(node, "id", ""))
        for forbidden in ("poly_stitching_bound", "stitched_boundary",
                          "stitched_boundary_repaired", "crosscheck_bands"):
            self.assertNotIn(forbidden, called,
                             f"the replacement diagnostic must not use "
                             f"{forbidden}: the selected reference is the "
                             f"mixture, called through eb_reference")
        # and it must never pre-halve alpha, which was defect (b)
        for node in ast.walk(tree):
            if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                    and isinstance(node.left, ast.Name)
                    and node.left.id == "alpha"):
                self.fail("alpha is divided in the replacement diagnostic; "
                          "confseq_eb halves it internally")
        self.assertEqual(d.N_GRID, (100, 200, 500, 1000, 1500, 2000))
        self.assertEqual(len(d.STREAMS), 8)

    def test_the_diagnostic_refuses_a_foreign_reference_module(self):
        import eb_width_diagnostic as d
        try:
            import eb_reference as ref
            ref.load_reference()
        except Exception:                                   # noqa: BLE001
            self.skipTest("the compiled author reference is not built here")
        real = sys.modules.get("comparecast")
        try:
            import types
            fake = types.ModuleType("comparecast")
            fake.__file__ = "/tmp/not_the_pinned_tree/comparecast/__init__.py"
            sys.modules["comparecast"] = fake
            with self.assertRaises(SystemExit):
                d.assert_reference_modules_came_from_the_pinned_tree()
        finally:
            if real is not None:
                sys.modules["comparecast"] = real
            else:                                           # pragma: no cover
                sys.modules.pop("comparecast", None)

    def test_the_diagnostics_clock_is_the_residual_clock_not_a_variance(self):
        """The withdrawn note's third defect: a variance proxy for the clock."""
        import numpy as np
        import eb_width_diagnostic as d
        # the audit's own deterministic example: same terminal variance,
        # different residual clocks
        a = np.array([1.0, 1.0, -1.0, -1.0])
        b = np.array([1.0, -1.0, 1.0, -1.0])
        self.assertAlmostEqual(float(a.var()), float(b.var()), places=12)
        ca, cb = d.residual_clock(a)[-1], d.residual_clock(b)[-1]
        self.assertNotAlmostEqual(float(ca), float(cb), places=6)
        self.assertAlmostEqual(float(ca), 61.0 / 9.0, places=9)
        self.assertAlmostEqual(float(cb), 70.0 / 9.0, places=9)


def _run() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print(f"\nran={result.testsRun} failures={len(result.failures)} "
          f"errors={len(result.errors)} skipped={len(result.skipped)}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(_run())


class PinSuccessorAmendmentTests(unittest.TestCase):
    """The focused pin tests root asked for, 2026-09-22 04:27:
    "Deliver the immutable amendment and focused F18/pin tests, including a
    correct successor, wrong successor and mutated original pin. Report their
    exact counts, not 'every suite.'"

    Each case drives the REAL `check_pinned_file_hashes` on a deep copy, so
    nothing on disk is touched.
    """

    HERE = pathlib.Path(__file__).resolve().parent
    REPO = HERE.parent.parent

    ORIGINAL = '3c76e8ebfee7f62f239b391191fb30db6adebcfe22931844e273268e0dd7d2c2'
    PREVIOUS = 'b1ff97cc163ce7ea121ebd578a4c37de09d5ed7223f2029e5d56118cdc790822'
    CURRENT = 'd63717a5519f650394db8aca7eb33d7a15ccfedbaffe78600d9ea3fb7b76294d'

    def _inputs(self):
        import copy
        cfg = copy.deepcopy(json.loads(
            (self.HERE / 'cells.json').read_text(encoding='utf-8')))
        manifest = json.loads(
            vfixtures.PINNED_MANIFEST.read_text(encoding='utf-8'))
        # The SAME protocol text F18 itself passes: this experiment's own
        # PROTOCOL.md, not the pinned file. The check requires the recorded pin
        # (or its successor) to be stated in the report as well as in cells.json,
        # which is exactly root's "add a short dated amendment in the
        # protocol/report" obligation, enforced mechanically.
        protocol = vfixtures.PROTOCOL_PATH.read_text(encoding='utf-8')
        return cfg, manifest, protocol

    def _va(self, cfg):
        return cfg['provenance']['vocabulary_alignment']

    def _run(self, cfg, manifest, protocol):
        return vfixtures.check_pinned_file_hashes(
            cfg, manifest, self.REPO, vfixtures.PINNED_DIR, protocol)

    def _vocab_failures(self, fails):
        return [f for f in fails if 'vocabulary_alignment' in f]

    def test_the_amendment_on_disk_leaves_the_original_pin_untouched(self):
        cfg, _, _ = self._inputs()
        va = self._va(cfg)
        self.assertEqual(va['sha256'], self.ORIGINAL)
        self.assertEqual(va['superseded_by']['sha256'], self.CURRENT)
        self.assertEqual(va['superseded_by']['supersedes'], self.ORIGINAL)

    def test_the_previous_successor_is_preserved_not_overwritten(self):
        """Root: "Preserve the existing successor object in an additive history
        entry." The enclosure ruling is substantive history, not a stale value."""
        cfg, _, _ = self._inputs()
        prior = self._va(cfg)['superseded_by']['prior_successors']
        self.assertEqual(len(prior), 1)
        self.assertEqual(prior[0]['sha256'], self.PREVIOUS)
        self.assertIn('enclosure', prior[0]['reason'].lower())
        self.assertIn('ruling 60', prior[0]['ruling'])

    def test_a_correct_successor_passes(self):
        cfg, manifest, protocol = self._inputs()
        self.assertEqual(self._vocab_failures(self._run(cfg, manifest, protocol)), [])

    def test_a_WRONG_successor_fails(self):
        cfg, manifest, protocol = self._inputs()
        self._va(cfg)['superseded_by']['sha256'] = 'f' * 64
        self.assertNotEqual(
            self._vocab_failures(self._run(cfg, manifest, protocol)), [])

    def test_MUTATING_THE_ORIGINAL_PIN_still_fails(self):
        """The one that matters: the amendment must not have opened a door to
        rewriting the original study's source identity."""
        cfg, manifest, protocol = self._inputs()
        self._va(cfg)['sha256'] = self.CURRENT      # the tempting "fix"
        self.assertNotEqual(
            self._vocab_failures(self._run(cfg, manifest, protocol)), [])

    def test_a_successor_that_is_recorded_but_stale_fails(self):
        """The invariant F18 actually enforces: no pin is SILENTLY stale."""
        cfg, manifest, protocol = self._inputs()
        self._va(cfg)['superseded_by']['sha256'] = self.PREVIOUS   # the old one
        self.assertNotEqual(
            self._vocab_failures(self._run(cfg, manifest, protocol)), [])
