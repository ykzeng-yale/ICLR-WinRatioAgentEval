"""G3 tests: the statistical core (`lab_monitor`, `lab_enclosure`).

The group whose bugs are unrecoverable (ARCHITECTURE_FINAL.md section 9.2).  Every test runs
offline and deterministically with no model and no network.

The two committed fixtures are regenerated, never typed:

    ./.venv/bin/python experiments/live_ab/tests_lab_stats.py --regenerate

writes `testdata/radius_table.csv` and `testdata/monitor_fixtures.json` from `src/winstats.py`
and from an independent recomputation of the protocol formula; `test_radius_table_file` and
`test_monitor_fixtures_file` assert the committed bytes equal a fresh regeneration, so a
hand-edited fixture fails the suite (PG-20: no radius anywhere is hand-typed).
"""

from __future__ import annotations

import ast
import builtins
import inspect
import itertools
import json
import math
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
_SRC = HERE.parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import winstats  # noqa: E402

import lab_enclosure as enc  # noqa: E402
import lab_monitor as mon  # noqa: E402
from lab_enclosure import (  # noqa: E402
    Enclosure,
    EnclosureError,
    EpisodeView,
    FrozenMismatch,
    PairEnclosure,
)
from lab_monitor import MonitorConfig, MonitorError, MonitorState  # noqa: E402

TESTDATA = HERE / "testdata"
RADIUS_CSV = TESTDATA / "radius_table.csv"
FIXTURES_JSON = TESTDATA / "monitor_fixtures.json"

# The frozen statistical constants (protocol 8.5, Appendix B).  They live here only so that the
# tests can build a config; the modules themselves take them from the frozen config.
ALPHA_GATE = 0.00625
RHO = 100.0
DELTA = 0.03
N_MIN = 100
N_MAX = 568  # the roster ceiling N_P of protocol 3.3 / PG-21

# `n` values of the committed radius table (ARCHITECTURE section 10 cross-group fixtures).
RADIUS_NS = (1, 20, 92, 100, 150, 200, 295, 400, 565, 568, 569, 1000)

FROZEN_HIERARCHY = [
    {
        "name": "success",
        "field": "success",
        "higher_better": True,
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.0,
    },
    {
        "name": "cost",
        "field": "latency_s",
        "higher_better": False,
        "absolute_tolerance": 0.0,
        "relative_tolerance": 0.05,
    },
]

TRIALS = ("T4", "T2", "T1", "T3")


def frozen_config(n_pairs: int = N_MAX) -> dict:
    """The decision-defining subset of `config.json`, as the two modules read it.

    Written here as a LOCAL FAKE so that this group never depends on G5's `config.json`
    (ARCHITECTURE section 10, "Parallelism").
    """
    return {
        "rule_id": "nm_guarded_v3",
        "trials": {t: {"trial_no": i + 1} for i, t in enumerate(TRIALS)},
        "monitor": {
            "construction": "winstats.normal_mixture_radius",
            "variance_process": "n",
            "alpha_program": 0.05,
            "alpha_trial": 0.0125,
            "alpha_gate": ALPHA_GATE,
            "rho": RHO,
            "delta": DELTA,
            "exploratory_margins": [0.10, 0.15],
            "exploratory_margins_decide": False,
            "n_min": N_MIN,
            "n_max": n_pairs,
            "prefix": "current_full_enrolled",
            "clip": [-1.0, 1.0],
            "retention": False,
            "running_intersection": False,
            "prefix_envelope": False,
            "maximize_over_prefixes": False,
            "harm_tail": "hierarchy_upper_only",
            "decision_order": ["harm_keep_incumbent", "deploy_candidate"],
            "deploy_if": "L_h_gt_0_and_L_s_gt_minus_delta_at_same_prefix",
            "harm_if": "U_h_lt_0",
        },
        "hierarchy": [dict(row) for row in FROZEN_HIERARCHY],
        "eligibility_rule": "lower_tiers_require_both_success",
        "tie_rule": "strict_gt_tolerance_so_exact_equality_is_a_tie",
        "roster": {"n_pairs": n_pairs},
    }


def mc_of(n_pairs: int = N_MAX) -> MonitorConfig:
    return MonitorConfig.from_config(frozen_config(n_pairs), "T4")


def tiers() -> list:
    return enc.tiers_from_config(frozen_config())


# ---------------------------------------------------------------------------------------------
# An INDEPENDENT recomputation of the rule, written from protocol_FINAL.md sections 8.2 and 8.4
# and using the `math` module rather than numpy.  Nothing in it imports lab_monitor.  It is what
# "hand-checked" means for the 200 committed fixtures, and it is what the injected-defect tests
# are compared against.
# ---------------------------------------------------------------------------------------------
def independent_radius(n: int, alpha: float = ALPHA_GATE, rho: float = RHO) -> float:
    v = float(n)  # variance_process = n
    return math.sqrt((v + rho) * math.log((v + rho) / (rho * alpha**2))) / n


def independent_band(n: int, s_lower: float, s_upper: float,
                     alpha: float = ALPHA_GATE, rho: float = RHO) -> tuple[float, float, float]:
    r = independent_radius(n, alpha, rho)
    return r, max(-1.0, s_lower / n - r), min(1.0, s_upper / n + r)


def independent_decision(n: int, l_h: float, u_h: float, l_s: float, u_s: float,
                         *, all_collapsed: bool, n_min: int = N_MIN, n_max: int = N_MAX,
                         delta: float = DELTA) -> str:
    at_horizon = n >= n_max and all_collapsed
    if n == 0:
        return "none"
    if n < n_min:
        return "horizon_no_decision" if at_horizon else "none"
    if u_h < 0.0:
        return "harm_keep_incumbent"
    if l_h > 0.0 and l_s > -delta:
        return "deploy_candidate"
    return "horizon_no_decision" if at_horizon else "none"


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def cand(success: int, latency: float, tokens: int = 10) -> EpisodeView:
    return EpisodeView.reveal("candidate", success, latency, tokens)


def inc(success: int, latency: float, tokens: int = 10) -> EpisodeView:
    return EpisodeView.reveal("incumbent", success, latency, tokens)


def pend(arm: str, ell: float = 0.0, tokens: int = 0) -> EpisodeView:
    return EpisodeView.pending(arm, ell=ell, tokens_known=tokens)


def state_from_blocks(blocks, mc: MonitorConfig) -> MonitorState:
    """Build a MonitorState from [(count, h_lo, h_hi, s_lo, s_hi, collapsed, tier), ...]."""
    st = MonitorState(mc)
    total = sum(int(b[0]) for b in blocks)
    for i in range(1, total + 1):
        st.enroll(i)
    pos = 0
    for count, h_lo, h_hi, s_lo, s_hi, collapsed, tier in blocks:
        pe = PairEnclosure(Enclosure(h_lo, h_hi), Enclosure(s_lo, s_hi), bool(collapsed), int(tier))
        for _ in range(int(count)):
            pos += 1
            if not (h_lo == -1.0 and h_hi == 1.0 and s_lo == -1.0 and s_hi == 1.0):
                st.update(pos, pe)
    return st


def uniform_blocks(n: int, h: float, s: float):
    """n pairs all collapsed at hierarchy score `h` and success difference `s`."""
    tier = -1 if h == 0.0 else 0
    return [(n, h, h, s, s, True, tier)]


def open_blocks(n: int):
    return [(n, -1.0, 1.0, -1.0, 1.0, False, -1)]


# =============================================================================================
# Band and radius
# =============================================================================================
class TestBand(unittest.TestCase):
    def test_band_matches_winstats(self):
        """lo == max(-1, S/n - normal_mixture_radius(n, alpha, rho, n)) to the last bit."""
        mc = mc_of()
        checked = 0
        for n in (1, 2, 3, 7, 20, 50, 92, 99, 100, 101, 150, 200, 295, 400, 565, 568, 569, 1000):
            for frac in (-1.0, -0.5, -0.03, 0.0, 0.03, 0.25, 0.5, 1.0):
                s = frac * n
                b = mon.band(n, s, s, mc)
                r = float(
                    winstats.normal_mixture_radius(n, alpha=ALPHA_GATE, rho=RHO, variance_process=n)
                )
                self.assertEqual(b.radius, r)
                self.assertEqual(b.lo, max(-1.0, s / n - r))
                self.assertEqual(b.hi, min(1.0, s / n + r))
                # and within 1e-9 of the independent (math-module) recomputation
                ri, lo_i, hi_i = independent_band(n, s, s)
                self.assertLess(abs(b.radius - ri), 1e-9)
                self.assertLess(abs(b.lo - lo_i), 1e-9)
                self.assertLess(abs(b.hi - hi_i), 1e-9)
                checked += 1
        self.assertEqual(checked, 18 * 8)

    def test_variance_process_explicit_equals_default(self):
        """PG-19: the frozen call passes variance_process=n explicitly; it equals the default."""
        for n in RADIUS_NS:
            explicit = float(
                winstats.normal_mixture_radius(n, alpha=ALPHA_GATE, rho=RHO, variance_process=n)
            )
            default = float(winstats.normal_mixture_radius(n, alpha=ALPHA_GATE, rho=RHO))
            self.assertEqual(explicit, default)
            self.assertEqual(mon.band(n, 0.0, 0.0, mc_of(max(n, N_MAX))).radius, explicit)

    def test_radius_fixture(self):
        """The committed table is what winstats produces, row for row."""
        rows = mon.radius_table(RADIUS_NS, mc_of(1000))
        by_n = {row["n"]: row["radius"] for row in rows}
        self.assertEqual(by_n[92], 0.4950264429325317)
        self.assertEqual(by_n[100], 0.4656929205179653)
        self.assertEqual(by_n[295], 0.22870694233462288)
        self.assertEqual(by_n[568], 0.1579515124940428)
        # 569 is a reference row, not a horizon: r is strictly decreasing in n.
        self.assertGreater(by_n[568], by_n[569])
        for row in rows:
            self.assertEqual(row["alpha_gate"], ALPHA_GATE)
            self.assertEqual(row["rho"], RHO)
            self.assertLess(abs(row["radius"] - independent_radius(row["n"])), 1e-9)

    def test_radius_table_file(self):
        """testdata/radius_table.csv equals a fresh regeneration from winstats, byte for byte."""
        self.assertTrue(RADIUS_CSV.exists(), "run tests_lab_stats.py --regenerate")
        self.assertEqual(RADIUS_CSV.read_text(encoding="utf-8"), render_radius_csv())

    def test_clip(self):
        """Endpoints are clipped to [-1, 1] and never outside (PG-18)."""
        mc = mc_of()
        for n in (100, 200, 568):
            hot = mon.band(n, float(n), float(n), mc)
            self.assertEqual(hot.hi, 1.0)
            self.assertLess(hot.lo, 1.0)
            cold = mon.band(n, -float(n), -float(n), mc)
            self.assertEqual(cold.lo, -1.0)
            self.assertGreater(cold.hi, -1.0)
            wide = mon.band(n, -float(n), float(n), mc)
            self.assertEqual((wide.lo, wide.hi), (-1.0, 1.0))
            for b in (hot, cold, wide):
                self.assertTrue(-1.0 <= b.lo <= b.hi <= 1.0)

    def test_band_rejects_bad_prefix(self):
        mc = mc_of()
        with self.assertRaises(MonitorError):
            mon.band(0, 0.0, 0.0, mc)
        with self.assertRaises(MonitorError):
            mon.band(-1, 0.0, 0.0, mc)
        with self.assertRaises(MonitorError):
            mon.band(10, 1.0, 0.0, mc)  # empty summed enclosure
        with self.assertRaises(MonitorError):
            mon.band(10, 0.0, 11.0, mc)  # leaves [-n, n]

    def test_band_reads_no_state(self):
        """Structural: band() references no module state, so it cannot remember an earlier band."""
        tree = ast.parse(Path(mon.__file__).read_text(encoding="utf-8"))
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "band"
        )
        bound = {a.arg for a in fn.args.args}
        body = [n for stmt in fn.body for n in ast.walk(stmt)]
        for node in body:
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                bound.add(node.id)
        free = {
            node.id
            for node in body
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id not in bound
            and not hasattr(builtins, node.id)
        }
        self.assertEqual(free, {"winstats", "MonitorError", "Band"})

    def test_no_running_intersection(self):
        """A path that narrows then widens produces a band that widens too."""
        mc = mc_of()
        st = MonitorState(mc)
        for i in range(1, 101):  # 100 resolved ties: the tightest band this prefix allows
            st.enroll(i)
            st.update(i, PairEnclosure(Enclosure(0.0, 0.0), Enclosure(0.0, 0.0), True, -1))
        tight = st.bands()[0]
        self.assertEqual((tight.lo, tight.hi), (-independent_radius(100), independent_radius(100)))
        for i in range(101, 141):  # 40 freshly enrolled, unresolved pairs at [-1, 1]
            st.enroll(i)
        loose = st.bands()[0]
        self.assertLess(loose.lo, tight.lo)  # the band widened; no memory of the tighter one
        self.assertGreater(loose.hi, tight.hi)
        # and it is exactly the current-prefix band, not an intersection with the earlier one
        self.assertEqual(loose.lo, mon.band(140, -40.0, 40.0, mc).lo)
        self.assertEqual(loose.hi, mon.band(140, -40.0, 40.0, mc).hi)

    def test_no_module_level_band_memory(self):
        """Structural: lab_monitor holds no module-level mutable that a band could accumulate in."""
        tree = ast.parse(Path(mon.__file__).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [t.id for t in targets if isinstance(t, ast.Name)]
                if any(name.startswith("__") for name in names):
                    continue
                self.assertNotIsInstance(node.value, (ast.List, ast.Dict, ast.Set), names)

    def test_no_wealth_process_in_decision_path(self):
        """PG-16: the wealth read-out never appears in decision-defining code."""
        for module in (mon, enc):
            text = Path(module.__file__).read_text(encoding="utf-8").lower()
            self.assertNotIn("betting", text, module.__name__)
            self.assertNotIn("log_e_ternary", text, module.__name__)


# =============================================================================================
# The decision function
# =============================================================================================
class TestDecision(unittest.TestCase):
    def test_n_min(self):
        """No decision below n_min = 100, however extreme the sums."""
        mc = mc_of()
        for n in (1, 2, 50, 92, 99):
            for z, d in ((1.0, 1.0), (-1.0, -1.0)):
                st = state_from_blocks(uniform_blocks(n, z, d), mc)
                self.assertEqual(st.n, n)
                self.assertIsNone(mon.decide(st, mc), f"decided at n={n}")
        st = state_from_blocks(uniform_blocks(100, 1.0, 1.0), mc)
        self.assertIsNotNone(mon.decide(st, mc))  # n_min is 100, inclusive

    def test_deploy_needs_both(self):
        """L_h > 0 alone does not deploy; L_s > -delta alone does not deploy."""
        mc = mc_of()
        n = 500  # strictly below the horizon, so `None` can only mean "did not deploy"
        r = independent_radius(n)
        # hierarchy crosses, success does not (Dbar = 0 -> L_s = -r << -delta)
        st = state_from_blocks(uniform_blocks(n, 0.9, 0.0), mc)
        bh, bs = st.bands()
        self.assertGreater(bh.lo, 0.0)
        self.assertLess(bs.lo, -DELTA)
        self.assertIsNone(mon.decide(st, mc))
        # success guard holds, hierarchy does not
        st = state_from_blocks(uniform_blocks(n, 0.0, r - DELTA / 2.0), mc)
        bh, bs = st.bands()
        self.assertLessEqual(bh.lo, 0.0)
        self.assertGreater(bs.lo, -DELTA)
        self.assertIsNone(mon.decide(st, mc))
        # both -> deploy, at the SAME prefix
        st = state_from_blocks(uniform_blocks(n, 0.9, r - DELTA / 2.0), mc)
        got = mon.decide(st, mc)
        self.assertIsNotNone(got)
        self.assertEqual(got.kind, "deploy_candidate")
        self.assertEqual(got.n, n)
        self.assertEqual(got.band_h.n, got.band_s.n)

    def test_same_prefix_conjunction(self):
        """L_h > 0 at one prefix and L_s > -delta at another never deploys."""
        mc = mc_of()
        # at n = 120: the success guard holds, the hierarchy does not
        st = MonitorState(mc)
        for i in range(1, 121):
            st.enroll(i)
            st.update(i, PairEnclosure(Enclosure(0.0, 0.0), Enclosure(1.0, 1.0), True, -1))
        bh, bs = st.bands()
        self.assertGreater(bs.lo, -DELTA)
        self.assertLess(bh.lo, 0.0)
        self.assertIsNone(mon.decide(st, mc))
        # later the hierarchy crosses but the success guard has gone
        for i in range(121, 401):
            st.enroll(i)
            st.update(i, PairEnclosure(Enclosure(1.0, 1.0), Enclosure(-1.0, -1.0), True, 0))
        bh, bs = st.bands()
        self.assertGreater(bh.lo, 0.0)
        self.assertLess(bs.lo, -DELTA)
        self.assertIsNone(mon.decide(st, mc))

    def test_harm_is_hierarchy_only(self):
        """PG-5: U_s < -delta with U_h > 0 decides nothing."""
        mc = mc_of()
        st = state_from_blocks(uniform_blocks(300, 0.0, -1.0), mc)
        bh, bs = st.bands()
        self.assertGreater(bh.hi, 0.0)
        self.assertLess(bs.hi, -DELTA)
        self.assertIsNone(mon.decide(st, mc))
        snap = st.snapshot()
        self.assertLess(snap["U_s"], -DELTA)  # computed and logged, and it decides nothing
        self.assertFalse(snap["flags"]["harm"])

    def test_harm_before_deploy(self):
        """The frozen order is applied: harm is tested first, in the source and in behaviour."""
        tree = ast.parse(Path(mon.__file__).read_text(encoding="utf-8"))
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "decide"
        )
        kinds = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Decision":
                for kw in node.keywords:
                    if kw.arg == "kind" and isinstance(kw.value, ast.Constant):
                        kinds.append((node.lineno, kw.value.value))
        kinds.sort()
        order = [k for _, k in kinds]
        self.assertIn("harm_keep_incumbent", order)
        self.assertIn("deploy_candidate", order)
        self.assertLess(order.index("harm_keep_incumbent"), order.index("deploy_candidate"))
        mc = mc_of()
        st = state_from_blocks(uniform_blocks(568, -0.9, 1.0), mc)
        bh, bs = st.bands()
        self.assertLess(bh.hi, 0.0)
        self.assertGreater(bs.lo, -DELTA)  # the success guard is satisfied and must not matter
        got = mon.decide(st, mc)
        self.assertEqual(got.kind, "harm_keep_incumbent")

    def test_no_retention(self):
        """A path that crosses at n=120, dips below at n=130, and is evaluated at n=130.

        The crossing at 120 is marginal, so ten losing pairs are enough to undo it.  A rule that
        retained the earlier crossing would still deploy at 130; this one must not.
        """
        mc = mc_of()
        v = independent_radius(120) + 0.002  # just enough for L_h > 0 at n = 120
        st = MonitorState(mc)
        for i in range(1, 121):
            st.enroll(i)
            st.update(i, PairEnclosure(Enclosure(v, v), Enclosure(1.0, 1.0), True, 0))
        crossing = mon.decide(st, mc)
        self.assertIsNotNone(crossing)
        self.assertEqual(crossing.kind, "deploy_candidate")
        self.assertEqual(crossing.n, 120)
        crossing_lo = st.bands()[0].lo
        self.assertGreater(crossing_lo, 0.0)
        for i in range(121, 131):  # ten losing pairs
            st.enroll(i)
            st.update(i, PairEnclosure(Enclosure(-1.0, -1.0), Enclosure(1.0, 1.0), True, 0))
        self.assertEqual(st.n, 130)
        self.assertLess(st.bands()[0].lo, crossing_lo)
        self.assertLess(st.bands()[0].lo, 0.0)  # the dip
        self.assertGreater(st.bands()[1].lo, -DELTA)  # the success guard still holds
        self.assertIsNone(mon.decide(st, mc), "the old crossing was retained")

    def test_first_crossing_only(self):
        """decide returns at the first admissible look and is a pure function of the prefix."""
        mc = mc_of()
        st = MonitorState(mc)
        firsts = []
        for i in range(1, 140):
            st.enroll(i)
            st.update(i, PairEnclosure(Enclosure(1.0, 1.0), Enclosure(1.0, 1.0), True, 0))
            got = mon.decide(st, mc)
            if got is not None:
                firsts.append((i, got.kind))
        self.assertEqual(firsts[0], (N_MIN, "deploy_candidate"))
        # purity: the same state answers the same way however often it is asked
        again = mon.decide(st, mc)
        self.assertEqual((again.kind, again.n), (firsts[-1][1], st.n))
        self.assertEqual(mon.decide(st, mc).n, again.n)

    def test_deploy_threshold_at_scale(self):
        """Conditional, never an impossibility (audit B4).

        With Dbar = 0 and n <= N_P <= 568 no prefix deploys, because r(n) >= r(568) = 0.158 and
        the success guard needs L_s = -r(n) > -0.03.  With a running success difference just
        above r(n) - delta at the same n it DOES deploy: the near-certain abstention is a
        property of the data, not of the rule.
        """
        mc = mc_of()
        for n in (100, 150, 295, 400, 568):
            st = state_from_blocks(uniform_blocks(n, 1.0, 0.0), mc)
            got = mon.decide(st, mc)
            self.assertNotEqual(
                "none" if got is None else got.kind,
                "deploy_candidate",
                f"deployed with Dbar = 0 at n={n}",
            )
            self.assertGreater(independent_radius(n), DELTA)
            r = independent_radius(n)
            above = state_from_blocks(uniform_blocks(n, 1.0, r - DELTA + 1e-4), mc)
            got = mon.decide(above, mc)
            self.assertIsNotNone(got, f"did not deploy just above r(n) - delta at n={n}")
            self.assertEqual(got.kind, "deploy_candidate")

    def test_horizon_no_decision(self):
        mc = mc_of(150)
        st = state_from_blocks(uniform_blocks(149, 0.0, 0.0), mc)
        st.enroll(150)
        self.assertIsNone(mon.decide(st, mc))  # pair 150 is not resolved yet
        st.update(150, PairEnclosure(Enclosure(0.0, 0.0), Enclosure(0.0, 0.0), True, -1))
        got = mon.decide(st, mc)
        self.assertEqual(got.kind, "horizon_no_decision")
        self.assertEqual(got.n, 150)
        self.assertEqual(got.rule_id, "nm_guarded_v3")

    def test_enroll_update_order(self):
        mc = mc_of()
        st = MonitorState(mc)
        with self.assertRaises(MonitorError):
            st.enroll(2)  # only ever position n + 1
        st.enroll(1)
        with self.assertRaises(MonitorError):
            st.enroll(1)
        with self.assertRaises(MonitorError):
            st.enroll(3)
        with self.assertRaises(MonitorError):
            st.update(2, PairEnclosure.full())  # a reveal never creates a pair
        with self.assertRaises(MonitorError):
            st.update(0, PairEnclosure.full())
        point = PairEnclosure(Enclosure(1.0, 1.0), Enclosure(1.0, 1.0), True, 0)
        st.update(1, point)
        before = st.sums()
        st.update(1, point)  # idempotent
        self.assertEqual(st.sums(), before)
        self.assertEqual(st.snapshot()["n_collapsed"], 1)

    def test_fsum_order_independence(self):
        rng = random.Random(4242)
        values = [rng.choice([-1.0, 0.0, 1.0, 0.5, -0.25, 1 / 3]) for _ in range(568)]
        base = math.fsum(values)
        for _ in range(50):
            shuffled = values[:]
            rng.shuffle(shuffled)
            self.assertEqual(math.fsum(shuffled), base)
        # and the state agrees whatever order the pairs collapse in
        mc = mc_of()
        st_a, st_b = MonitorState(mc), MonitorState(mc)
        order = list(range(1, 201))
        for i in order:
            st_a.enroll(i)
            st_b.enroll(i)
        rng.shuffle(order)
        for i in range(1, 201):
            v = values[i % len(values)]
            st_a.update(i, PairEnclosure(Enclosure(v, v), Enclosure(v, v), True, -1))
        for i in order:
            v = values[i % len(values)]
            st_b.update(i, PairEnclosure(Enclosure(v, v), Enclosure(v, v), True, -1))
        self.assertEqual(st_a.sums(), st_b.sums())
        self.assertEqual(repr(st_a.bands()[0]), repr(st_b.bands()[0]))


# =============================================================================================
# Injected defects: a straightforward independent recomputation must catch them
# =============================================================================================
class TestInjectedDefects(unittest.TestCase):
    def test_injected_defect_sign_slip(self):
        """Adding the radius to the lower endpoint deploys where the real rule abstains."""
        mc = mc_of()
        n, z, d = 500, 0.2, 0.0
        st = state_from_blocks(uniform_blocks(n, z, d), mc)
        bh, bs = st.bands()
        r, lo_h, _ = independent_band(n, bh.s_lower, bh.s_upper)
        _, lo_s, _ = independent_band(n, bs.s_lower, bs.s_upper)
        self.assertLess(abs(bh.lo - lo_h), 1e-12)
        # the defect: L = S/n + r instead of S/n - r
        defect_lo_h = max(-1.0, bh.s_lower / n + r)
        defect_lo_s = max(-1.0, bs.s_lower / n + r)
        self.assertNotAlmostEqual(defect_lo_h, bh.lo, places=6)
        self.assertIsNone(mon.decide(st, mc))
        self.assertTrue(defect_lo_h > 0.0 and defect_lo_s > -DELTA)  # the defect would deploy
        self.assertNotEqual(
            independent_decision(n, defect_lo_h, bh.hi, defect_lo_s, bs.hi, all_collapsed=True),
            independent_decision(n, bh.lo, bh.hi, bs.lo, bs.hi, all_collapsed=True),
            "the independent recomputation did not catch the sign slip",
        )

    def test_injected_defect_swapped_counts(self):
        """Swapping the win and loss counts flips the sign of Zbar and the decision with it."""
        mc = mc_of()
        n, wins, losses = 568, 420, 60
        ties = n - wins - losses
        good = [(wins, 1.0, 1.0, 1.0, 1.0, True, 0),
                (losses, -1.0, -1.0, -1.0, -1.0, True, 0),
                (ties, 0.0, 0.0, 0.0, 0.0, True, -1)]
        bad = [(losses, 1.0, 1.0, 1.0, 1.0, True, 0),
               (wins, -1.0, -1.0, -1.0, -1.0, True, 0),
               (ties, 0.0, 0.0, 0.0, 0.0, True, -1)]
        st_good = state_from_blocks(good, mc)
        st_bad = state_from_blocks(bad, mc)
        d_good = mon.decide(st_good, mc)
        d_bad = mon.decide(st_bad, mc)
        self.assertEqual(d_good.kind, "deploy_candidate")
        self.assertEqual(d_bad.kind, "harm_keep_incumbent")
        self.assertNotEqual(st_good.sums(), st_bad.sums())

    def test_injected_defect_swapped_scores(self):
        """Reading the success band where the hierarchy band belongs changes the decision."""
        mc = mc_of()
        n = 500
        r = independent_radius(n)
        st = state_from_blocks(uniform_blocks(n, r - DELTA / 2.0, r + 0.5), mc)
        bh, bs = st.bands()
        self.assertIsNone(mon.decide(st, mc))  # L_h < 0: the real rule abstains
        self.assertLess(bh.lo, 0.0)
        self.assertGreater(bh.hi, 0.0)
        # the defect: test L_s > 0 and L_h > -delta instead of L_h > 0 and L_s > -delta
        self.assertTrue(bs.lo > 0.0 and bh.lo > -DELTA)


# =============================================================================================
# Enclosures
# =============================================================================================
class TestEnclosure(unittest.TestCase):
    def test_enclosure_rejects_invalid(self):
        for lo, hi in ((-1.5, 0.0), (0.0, 1.5), (0.5, 0.4), (float("nan"), 0.0)):
            with self.assertRaises(EnclosureError):
                Enclosure(lo, hi)
        with self.assertRaises(EnclosureError):
            Enclosure(float("inf"), 1.0)

    def test_enclosure_starts_full(self):
        """An enrolled, unresolved pair is [-1, 1] in both scores."""
        mc = mc_of()
        st = MonitorState(mc)
        st.enroll(1)
        self.assertEqual(st.sums(), (-1.0, 1.0, -1.0, 1.0))
        pe = enc.pair_enclosure(pend("candidate"), pend("incumbent"), tiers())
        self.assertEqual((pe.h.lo, pe.h.hi), (-1.0, 1.0))
        self.assertEqual((pe.s.lo, pe.s.hi), (-1.0, 1.0))
        self.assertFalse(pe.collapsed)
        self.assertEqual(pe.decisive_tier, -1)
        self.assertEqual((Enclosure.full().lo, Enclosure.full().hi), (-1.0, 1.0))

    def test_collapsed_flag_cannot_lie(self):
        """`collapsed` drives the horizon condition, so it must match the endpoints."""
        with self.assertRaises(EnclosureError):
            PairEnclosure(Enclosure(-1.0, 1.0), Enclosure(-1.0, 1.0), True, -1)
        with self.assertRaises(EnclosureError):
            PairEnclosure(Enclosure(0.0, 0.0), Enclosure(0.0, 0.0), False, -1)
        with self.assertRaises(EnclosureError):
            PairEnclosure(Enclosure(1.0, 1.0), Enclosure(0.0, 1.0), True, -1)  # certificate only
        with self.assertRaises(EnclosureError):
            PairEnclosure(Enclosure(0.0, 0.0), Enclosure(0.0, 0.0), True, 2)

    def test_completed_prefix_readout(self):
        """protocol 8.8 item 6: the band on the completed prefix, logged and never decisive."""
        mc = mc_of()
        st = MonitorState(mc)
        for i in range(1, 121):
            st.enroll(i)
        self.assertEqual(st.snapshot()["readouts"]["completed_prefix"]["n"], 0)
        point = PairEnclosure(Enclosure(1.0, 1.0), Enclosure(1.0, 1.0), True, 0)
        for i in range(1, 101):
            st.update(i, point)
        st.update(110, point)  # a later pair resolves out of order
        snap = st.snapshot()
        self.assertEqual(snap["n"], 120)
        self.assertEqual(snap["n_collapsed"], 101)
        # the completed PREFIX stops at the first unresolved pair; it is not the collapsed count
        completed = snap["readouts"]["completed_prefix"]
        self.assertEqual(completed["n"], 100)
        self.assertEqual(completed["L_h"], mon.band(100, 100.0, 100.0, mc).lo)
        self.assertNotEqual(completed["L_h"], snap["L_h"])
        self.assertGreater(completed["L_h"], snap["L_h"])  # the enrolled prefix is the wider one

    def test_enclosure_never_widens(self):
        mc = mc_of()
        st = MonitorState(mc)
        st.enroll(1)
        st.update(1, PairEnclosure(Enclosure(0.0, 1.0), Enclosure(0.0, 1.0), False, -1))
        with self.assertRaises(EnclosureError):
            st.update(1, PairEnclosure(Enclosure(-1.0, 1.0), Enclosure(0.0, 1.0), False, -1))
        with self.assertRaises(EnclosureError):
            st.update(1, PairEnclosure(Enclosure(0.0, 1.0), Enclosure(-1.0, 1.0), False, -1))
        with self.assertRaises(EnclosureError):
            enc.assert_monotone(
                PairEnclosure(Enclosure(0.0, 0.0), Enclosure(0.0, 0.0), True, -1),
                PairEnclosure(Enclosure(-1.0, 1.0), Enclosure(-1.0, 1.0), False, -1),
            )

    def test_success_enclosure_formula(self):
        """[sA_low - sB_high, sA_high - sB_low] for all 9 combinations of revealed/pending."""
        options_c = {
            "pending": (pend("candidate"), 0.0, 1.0),
            "fail": (cand(0, 3.0), 0.0, 0.0),
            "ok": (cand(1, 3.0), 1.0, 1.0),
        }
        options_i = {
            "pending": (pend("incumbent"), 0.0, 1.0),
            "fail": (inc(0, 3.0), 0.0, 0.0),
            "ok": (inc(1, 3.0), 1.0, 1.0),
        }
        seen = 0
        for (_, (cv, a_lo, a_hi)), (_, (iv, b_lo, b_hi)) in itertools.product(
            options_c.items(), options_i.items()
        ):
            e = enc.success_enclosure(cv, iv)
            self.assertEqual(e.lo, a_lo - b_hi)
            self.assertEqual(e.hi, a_hi - b_lo)
            seen += 1
        self.assertEqual(seen, 9)

    def test_absence_of_failure_is_not_success(self):
        """A pending episode has s_low = 0 whatever its trace shows (protocol 7.5 item 3)."""
        busy = pend("candidate", ell=900.0, tokens=100000)
        e = enc.success_enclosure(busy, inc(1, 1.0))
        self.assertEqual((e.lo, e.hi), (-1.0, 0.0))

    def test_hierarchy_enumeration(self):
        t = tiers()
        # (b) neither revealed
        e = enc.hierarchy_enclosure(pend("candidate"), pend("incumbent"), t)
        self.assertEqual((e.lo, e.hi), (-1.0, 1.0))
        # (c) s_r == 0, revealed is the candidate (sgn = +1) -> feasible {-1, 0}
        e = enc.hierarchy_enclosure(cand(0, 5.0), pend("incumbent", ell=99.0), t)
        self.assertEqual((e.lo, e.hi), (-1.0, 0.0))
        # (c) s_r == 0, revealed is the incumbent (sgn = -1) -> feasible {0, +1}
        e = enc.hierarchy_enclosure(pend("candidate", ell=99.0), inc(0, 5.0), t)
        self.assertEqual((e.lo, e.hi), (0.0, 1.0))
        # (c) s_r == 1, certificate does NOT bind -> [-1, 1]
        e = enc.hierarchy_enclosure(cand(1, 100.0), pend("incumbent", ell=1.0), t)
        self.assertEqual((e.lo, e.hi), (-1.0, 1.0))
        # (c) s_r == 1, certificate binds for the candidate -> [1, 1]
        e = enc.hierarchy_enclosure(cand(1, 5.0), pend("incumbent", ell=100.0), t)
        self.assertEqual((e.lo, e.hi), (1.0, 1.0))
        # (c) s_r == 1, certificate binds for the incumbent -> [-1, -1]
        e = enc.hierarchy_enclosure(pend("candidate", ell=100.0), inc(1, 5.0), t)
        self.assertEqual((e.lo, e.hi), (-1.0, -1.0))
        # (a) both revealed
        e = enc.hierarchy_enclosure(cand(1, 5.0), inc(1, 100.0), t)
        self.assertEqual((e.lo, e.hi), (1.0, 1.0))

    def test_certificate_boundary(self):
        """The certificate is exactly `0.95 * ell > L_r + 1e-9`, strict (audit B1)."""
        t = tiers()
        l_r = 1.0
        for ell in (
            0.0,
            l_r,
            (l_r + 1e-9) / 0.95,
            math.nextafter((l_r + 1e-9) / 0.95, 0.0),
            math.nextafter((l_r + 1e-9) / 0.95, math.inf),
            (l_r + 1e-9) / 0.95 + 1e-12,
            2.0,
        ):
            binds = (1.0 - 0.05) * ell > l_r + 1e-9
            e = enc.hierarchy_enclosure(cand(1, l_r), pend("incumbent", ell=ell), t)
            self.assertEqual(
                (e.lo, e.hi), (1.0, 1.0) if binds else (-1.0, 1.0), f"ell={ell!r}"
            )
        # the frozen 0.95 collapses where the superseded v2 constant 0.9 would not (audit B1)
        ell = (l_r + 1e-9) / 0.92
        self.assertTrue(0.95 * ell > l_r + 1e-9)
        self.assertFalse(0.90 * ell > l_r + 1e-9)
        e = enc.hierarchy_enclosure(cand(1, l_r), pend("incumbent", ell=ell), t)
        self.assertEqual((e.lo, e.hi), (1.0, 1.0))

    def test_certificate_collapses_mid_pair(self):
        """h collapses to [sgn, sgn] with the partner pending; s stays open; monotone holds."""
        mc = mc_of()
        t = tiers()
        st = MonitorState(mc)
        st.enroll(1)
        partner_ell = 0.0
        prev = PairEnclosure.full()
        for partner_ell in (0.0, 1.0, 4.0, 100.0):
            pe = enc.pair_enclosure(cand(1, 5.0), pend("incumbent", ell=partner_ell), t)
            enc.assert_monotone(prev, pe)
            st.update(1, pe)
            prev = pe
        self.assertEqual((prev.h.lo, prev.h.hi), (1.0, 1.0))
        self.assertEqual((prev.s.lo, prev.s.hi), (0.0, 1.0))
        self.assertFalse(prev.collapsed)  # the success enclosure is still open
        self.assertEqual(prev.decisive_tier, -1)
        # and the partner's eventual reveal is inside it, either way it goes
        for partner in (inc(1, 100.0), inc(0, 100.0)):
            final = enc.pair_enclosure(cand(1, 5.0), partner, t)
            enc.assert_monotone(prev, final)
            self.assertTrue(prev.h.contains(final.h.lo))
            self.assertTrue(prev.s.contains(final.s.lo))
            self.assertTrue(final.collapsed)

    def test_equality_is_tie(self):
        """Exact threshold equality is a tie, in `success` and in `latency_s`."""
        t = tiers()
        z, tier, d = enc.final_scores(cand(1, 10.0), inc(1, 10.0), t)
        self.assertEqual((z, tier, d), (0, -1, 0))
        # tier 1: |a - b| == tol * max(|a|, |b|) exactly -> a tie (strict '>')
        z, tier, d = enc.final_scores(cand(1, 95.0), inc(1, 100.0), t)
        self.assertEqual(abs(95.0 - 100.0), 0.05 * 100.0)
        self.assertEqual((z, tier, d), (0, -1, 0))
        # one ulp past the boundary it decides
        z, tier, _ = enc.final_scores(cand(1, math.nextafter(95.0, 0.0)), inc(1, 100.0), t)
        self.assertEqual((z, tier), (1, 1))
        # success equality at tier 0 falls through to tier 1
        z, tier, _ = enc.final_scores(cand(0, 1.0), inc(0, 100.0), t)
        self.assertEqual((z, tier), (0, -1))  # ineligible: not both succeeded

    def test_joint_failure_is_tie(self):
        t = tiers()
        z, tier, d = enc.final_scores(cand(0, 1.0), inc(0, 5000.0), t)
        self.assertEqual((z, tier, d), (0, -1, 0))
        pe = enc.pair_enclosure(cand(0, 1.0), inc(0, 5000.0), t)
        self.assertEqual((pe.h.lo, pe.h.hi), (0.0, 0.0))
        self.assertEqual((pe.s.lo, pe.s.hi), (0.0, 0.0))
        self.assertTrue(pe.collapsed)
        self.assertEqual(pe.decisive_tier, -1)

    def test_cost_tier_requires_both_success(self):
        t = tiers()
        # candidate fails but is far faster: tier 1 is ineligible, tier 0 decides for incumbent
        z, tier, d = enc.final_scores(cand(0, 1.0), inc(1, 5000.0), t)
        self.assertEqual((z, tier, d), (-1, 0, -1))

    def test_terminal_failure_collapses(self):
        """A terminal failure is a reveal: success=0, latency=ell, tokens=tokens_known."""
        mc = mc_of()
        t = tiers()
        st = MonitorState(mc)
        st.enroll(1)
        pending = enc.pair_enclosure(pend("candidate", ell=42.0, tokens=7), inc(1, 3.0), t)
        st.update(1, pending)
        dead = EpisodeView.reveal("candidate", 0, 42.0, 7)  # latency_s = ell, tokens = known
        final = enc.pair_enclosure(dead, inc(1, 3.0), t)
        enc.assert_monotone(pending, final)
        st.update(1, final)
        self.assertTrue(final.collapsed)
        self.assertEqual((final.h.lo, final.h.hi), (-1.0, -1.0))
        self.assertEqual((final.s.lo, final.s.hi), (-1.0, -1.0))

    def test_certified_elapsed(self):
        self.assertEqual(enc.certified_elapsed([]), 0.0)  # PG-9 / critic N5
        self.assertEqual(enc.certified_elapsed([(1_000_000_000, 3_500_000_000)]), 2.5)
        stamps = [(100, 200), (100, 900), (100, 400)]
        self.assertEqual(enc.certified_elapsed(stamps), 800 / 1e9)
        with self.assertRaises(EnclosureError):
            enc.certified_elapsed([(500, 400)])
        with self.assertRaises(EnclosureError):
            enc.certified_elapsed([(1.0, 2.0)])  # ns stamps are ints
        # it only ever rises as more stamps arrive
        acc, last = [], 0.0
        for t_e in (150, 120, 900, 300, 1200):
            acc.append((100, t_e))
            value = enc.certified_elapsed(acc)
            self.assertGreaterEqual(value, last)
            last = value

    def test_no_certificate_from_tokens(self):
        """Tokens are not a tier: a huge token lower bound narrows nothing."""
        t = tiers()
        e = enc.hierarchy_enclosure(cand(1, 100.0), pend("incumbent", ell=1.0, tokens=10**9), t)
        self.assertEqual((e.lo, e.hi), (-1.0, 1.0))
        with self.assertRaises(EnclosureError):
            enc.outcome_vector(cand(1, 3.0), ("success", "completion_tokens"))

    def test_outcome_vector_refuses_partial(self):
        with self.assertRaises(EnclosureError):
            enc.outcome_vector(pend("candidate", ell=5.0), enc.TIER_NAMES)
        self.assertEqual(enc.outcome_vector(cand(1, 2.5), enc.TIER_NAMES), [1.0, 2.5])
        self.assertEqual(enc.TIER_NAMES, ("success", "latency_s"))

    def test_arm_order_is_checked(self):
        t = tiers()
        with self.assertRaises(EnclosureError):
            enc.final_scores(inc(1, 1.0), cand(1, 2.0), t)  # swapped arms
        with self.assertRaises(EnclosureError):
            enc.success_enclosure(inc(1, 1.0), cand(1, 2.0))

    def test_two_tiers_only(self):
        """The same frozen two-row hierarchy for all four trials; anything else is a mismatch."""
        for trial in TRIALS:
            cfg = frozen_config()
            MonitorConfig.from_config(cfg, trial)
            t = enc.tiers_from_config(cfg)
            self.assertEqual(len(t), 2)
            self.assertEqual(t[0], winstats.Tier("success"))
            self.assertEqual(
                t[1], winstats.Tier("cost", higher_better=False, relative_tolerance=0.05)
            )
        third = frozen_config()
        third["hierarchy"].append(
            {
                "name": "tokens",
                "field": "completion_tokens",
                "higher_better": False,
                "absolute_tolerance": 0.0,
                "relative_tolerance": 0.10,
            }
        )
        with self.assertRaises(FrozenMismatch):
            enc.tiers_from_config(third)
        counted = frozen_config()
        counted["n_tiers"] = 3
        with self.assertRaises(FrozenMismatch):
            enc.tiers_from_config(counted)
        loose = frozen_config()
        loose["hierarchy"][1]["relative_tolerance"] = 0.10
        with self.assertRaises(FrozenMismatch):
            enc.tiers_from_config(loose)
        flipped = frozen_config()
        flipped["hierarchy"][1]["higher_better"] = True
        with self.assertRaises(FrozenMismatch):
            enc.tiers_from_config(flipped)
        with self.assertRaises(FrozenMismatch):
            enc.tiers_from_config({})

    def test_frozen_config_guards(self):
        for mutate in (
            lambda c: c["monitor"].pop("n_max"),
            lambda c: c["monitor"].update(n_max=None),
            lambda c: c["monitor"].update(n_max=567),
            lambda c: c["monitor"].pop("alpha_gate"),
            lambda c: c["monitor"].pop("delta"),
            lambda c: c["monitor"].pop("n_min"),
            lambda c: c["monitor"].pop("rho"),
            lambda c: c["monitor"].update(retention=True),
            lambda c: c["monitor"].update(running_intersection=True),
            lambda c: c["monitor"].update(harm_tail="either"),
            lambda c: c["monitor"].update(variance_process="completed"),
            lambda c: c["monitor"].update(decision_order=["deploy_candidate", "harm_keep_incumbent"]),
            lambda c: c["roster"].update(n_pairs=None),
        ):
            cfg = frozen_config()
            mutate(cfg)
            with self.assertRaises(FrozenMismatch):
                MonitorConfig.from_config(cfg, "T4")
        with self.assertRaises(FrozenMismatch):
            MonitorConfig.from_config(frozen_config(), "T9")


# =============================================================================================
# Containment: every ultimately revealed score lies inside every prior enclosure
# =============================================================================================
def _histories(sc, lc, si, li, ell_fracs):
    """Every interleaving of the two episodes' (ell raise ..., reveal) sequences."""
    c_events = [("ell", "candidate", f * lc) for f in ell_fracs] + [("reveal", "candidate", None)]
    i_events = [("ell", "incumbent", f * li) for f in ell_fracs] + [("reveal", "incumbent", None)]
    k = len(c_events)
    for positions in itertools.combinations(range(2 * k), k):
        order = []
        ci = ii = 0
        chosen = set(positions)
        for slot in range(2 * k):
            if slot in chosen:
                order.append(c_events[ci])
                ci += 1
            else:
                order.append(i_events[ii])
                ii += 1
        yield order


def _walk(order, sc, lc, si, li, t):
    """Apply a history and return (list of enclosures, final PairEnclosure)."""
    c_view = pend("candidate")
    i_view = pend("incumbent")
    seen = [enc.pair_enclosure(c_view, i_view, t)]
    for kind, arm, value in order:
        if kind == "ell":
            if arm == "candidate":
                if c_view.revealed:
                    continue
                c_view = pend("candidate", ell=value)
            else:
                if i_view.revealed:
                    continue
                i_view = pend("incumbent", ell=value)
        else:
            if arm == "candidate":
                c_view = cand(sc, lc)
            else:
                i_view = inc(si, li)
        seen.append(enc.pair_enclosure(c_view, i_view, t))
    return seen, seen[-1]


class TestContainment(unittest.TestCase):
    def test_enclosure_containment_exhaustive(self):
        """Exhaustive over all interleavings on a small grid."""
        t = tiers()
        latencies = (1.0, 2.0, 2.1, 40.0)
        ell_fracs = (0.5, 1.0)
        checked = 0
        for sc, si in itertools.product((0, 1), repeat=2):
            for lc, li in itertools.product(latencies, repeat=2):
                z, _, d = enc.final_scores(cand(sc, lc), inc(si, li), t)
                for order in _histories(sc, lc, si, li, ell_fracs):
                    seen, final = _walk(order, sc, lc, si, li, t)
                    self.assertEqual((final.h.lo, final.h.hi), (float(z), float(z)))
                    self.assertEqual((final.s.lo, final.s.hi), (float(d), float(d)))
                    for k, pe in enumerate(seen):
                        self.assertTrue(pe.h.contains(z), f"{order} step {k}: z={z} not in h")
                        self.assertTrue(pe.s.contains(d), f"{order} step {k}: d={d} not in s")
                        if k:
                            enc.assert_monotone(seen[k - 1], pe)
                    checked += 1
        self.assertEqual(checked, 4 * 16 * 20)

    def test_enclosure_containment_random(self):
        """10,000 random pair histories; the final (z, d) is inside every intermediate."""
        t = tiers()
        rng = random.Random(60260919)
        histories = 0
        for _ in range(10000):
            sc, si = rng.randint(0, 1), rng.randint(0, 1)
            lc = round(rng.uniform(0.05, 400.0), 6)
            li = round(rng.uniform(0.05, 400.0), 6)
            # ell is a valid LOWER bound on the episode's own latency (protocol 7.5 item 4)
            fracs = sorted(rng.uniform(0.0, 1.0) for _ in range(rng.randint(0, 3)))
            c_events = [("ell", "candidate", f * lc) for f in fracs]
            fracs = sorted(rng.uniform(0.0, 1.0) for _ in range(rng.randint(0, 3)))
            i_events = [("ell", "incumbent", f * li) for f in fracs]
            c_events.append(("reveal", "candidate", None))
            i_events.append(("reveal", "incumbent", None))
            order = []
            while c_events or i_events:
                if c_events and (not i_events or rng.random() < 0.5):
                    order.append(c_events.pop(0))
                else:
                    order.append(i_events.pop(0))
            z, _, d = enc.final_scores(cand(sc, lc), inc(si, li), t)
            seen, final = _walk(order, sc, lc, si, li, t)
            self.assertEqual(final.h.lo, float(z))
            self.assertEqual(final.s.lo, float(d))
            for k, pe in enumerate(seen):
                self.assertTrue(pe.h.contains(z))
                self.assertTrue(pe.s.contains(d))
                if k:
                    enc.assert_monotone(seen[k - 1], pe)
            histories += 1
        self.assertEqual(histories, 10000)

    def test_reorder_invariance(self):
        """Any admissible permutation of a set of reveal-order events gives the same end state."""
        mc = mc_of()
        t = tiers()
        rng = random.Random(11)
        n = 120
        finals = []
        for i in range(n):
            sc, si = rng.randint(0, 1), rng.randint(0, 1)
            lc = round(rng.uniform(1.0, 50.0), 4)
            li = round(rng.uniform(1.0, 50.0), 4)
            finals.append((sc, lc, si, li))
        reference = None
        for trial in range(6):
            st = MonitorState(mc)
            for i in range(1, n + 1):
                st.enroll(i)
            order = list(range(n))
            rng.shuffle(order)
            for i in order:  # pairs resolve in an arbitrary order
                sc, lc, si, li = finals[i]
                st.update(i + 1, enc.pair_enclosure(cand(sc, lc), inc(si, li), t))
            got = (st.sums(), repr(st.bands()), repr(mon.decide(st, mc)))
            if reference is None:
                reference = got
            else:
                self.assertEqual(got, reference, f"permutation {trial} differed")


# =============================================================================================
# Replay
# =============================================================================================
def _ev(seq, etype, body, inv="a" * 32, trial="T4"):
    return {"seq": seq, "type": etype, "chain": trial, "inv": inv, "body": body}


class _ChainBuilder:
    """A local fake of the trial chain, written to G3's reading of ARCHITECTURE section 4.4."""

    def __init__(self, inv="a" * 32):
        self.events: list[dict] = []
        self.inv = inv
        self.arrival = 0

    def _add(self, etype, body):
        self.events.append(_ev(len(self.events), etype, body, inv=self.inv))

    def enroll(self, pair, candidate_first=True):
        a1, a2 = self.arrival + 1, self.arrival + 2
        self.arrival += 2
        self._add("pair_enrolled", {"pair": pair, "stratum": "S1", "arrivals": [a1, a2]})
        arms = ("candidate", "incumbent") if candidate_first else ("incumbent", "candidate")
        self._add(
            "coin_drawn",
            {"pair": pair, "bit": int(candidate_first), "assignment": {str(a1): arms[0], str(a2): arms[1]}},
        )
        return a1, a2

    def call(self, arrival, t_c1, t_send, t_recv=None, tokens=None):
        body = {"arrival": arrival, "attempt": 1, "t_c1_ns": t_c1, "t_send_ns": t_send}
        self._add("llm_request", body)
        if t_recv is not None:
            resp = {"arrival": arrival, "attempt": 1, "t_c1_ns": t_c1, "t_recv_ns": t_recv}
            if tokens is not None:
                resp["usage"] = {"completion_tokens": tokens}
            self._add("llm_response", resp)

    def reveal(self, arrival, pair, arm, success, latency, tokens=5, post_decision=False):
        self._add(
            "episode_revealed",
            {
                "arrival": arrival,
                "pair": pair,
                "position": 1,
                "arm": arm,
                "outcome": {"success": success, "latency_s": latency, "completion_tokens": tokens},
                "certified_ell": latency,
                "tokens_known": tokens,
                "post_decision": post_decision,
            },
        )

    def noise(self):
        self._add("metrics_scrape", {"server_id": "coder", "point": "pair_boundary", "ok": True})
        self._add("server_health", {"server_id": "coder", "ok": True})
        self._add("anchor", {"anchor_seq": 0, "upto_seq": len(self.events)})

    def decision(self, kind, n):
        self._add("decision", {"kind": kind, "n": n, "rule_id": "nm_guarded_v3"})


def _live_looks(chain, cfg, trial):
    """An independent event walk that drives MonitorState directly (the 'live' orchestrator).

    It is deliberately a different code path from `lab_monitor.replay`: a flat loop with its own
    bookkeeping, written from ARCHITECTURE 7.1 rows 6, 7, 7b, 8 and 12.
    """
    mc = MonitorConfig.from_config(cfg, trial)
    t = enc.tiers_from_config(cfg)
    st = MonitorState(mc)
    looks = []
    views: dict[int, EpisodeView] = {}
    stamps: dict[int, list[tuple[int, int]]] = {}
    ells: dict[int, float] = {}
    arms: dict[int, str] = {}
    pair_of: dict[int, int] = {}
    members: dict[int, list[int]] = {}
    decided = False

    def snap(trigger, pair):
        s = st.snapshot()
        s["trigger"] = trigger
        s["pair_updated"] = pair
        looks.append(s)

    def refresh(pair):
        vs = [views[a] for a in members[pair]]
        c = next(v for v in vs if v.arm == "candidate")
        i = next(v for v in vs if v.arm == "incumbent")
        pe = enc.pair_enclosure(c, i, t)
        st.update(pair, pe)

    for event in chain:
        body = event["body"]
        etype = event["type"]
        if etype == "pair_enrolled":
            members[body["pair"]] = list(body["arrivals"])
            for a in body["arrivals"]:
                pair_of[a] = body["pair"]
        elif etype == "coin_drawn":
            pair = body["pair"]
            for a in members[pair]:
                arms[a] = body["assignment"][str(a)]
                views[a] = pend(arms[a])
                stamps[a] = []
                ells[a] = 0.0
            st.enroll(pair)
            refresh(pair)
            snap("enroll", pair)
        elif etype in ("llm_request", "llm_response", "llm_error"):
            a = body["arrival"]
            if a not in views or views[a].revealed:
                continue
            for key in ("t_send_ns", "t_recv_ns"):
                if body.get(key) is not None:
                    stamps[a].append((body["t_c1_ns"], body[key]))
            new = enc.certified_elapsed(stamps[a])
            if new > ells[a]:
                ells[a] = new
                views[a] = pend(arms[a], ell=new)
                refresh(pair_of[a])
                snap("call", pair_of[a])
        elif etype == "episode_revealed":
            if body.get("post_decision"):
                continue
            a = body["arrival"]
            o = body["outcome"]
            views[a] = EpisodeView.reveal(arms[a], o["success"], o["latency_s"], o["completion_tokens"])
            refresh(pair_of[a])
            snap("drain" if decided else "reveal", pair_of[a])
        elif etype == "decision":
            decided = True
    return looks


class TestReplay(unittest.TestCase):
    def _chain(self):
        b = _ChainBuilder()
        rng = random.Random(7)
        for pair in range(1, 7):
            a1, a2 = b.enroll(pair, candidate_first=bool(pair % 2))
            arms = {a1: "candidate", a2: "incumbent"} if pair % 2 else {a1: "incumbent", a2: "candidate"}
            base = pair * 10**9
            b.call(a1, base, base + 10**8, base + 3 * 10**8, tokens=40)
            b.noise()
            b.call(a2, base, base + 10**8, base + 9 * 10**8, tokens=55)
            b.call(a2, base, base + 9 * 10**8, base + 9 * 10**8)  # raises nothing
            for arrival in (a1, a2):
                b.reveal(arrival, pair, arms[arrival], rng.randint(0, 1), round(rng.uniform(1, 9), 3))
            b.noise()
        return b

    def test_replay_equals_live(self):
        cfg = frozen_config(6)
        b = self._chain()
        replayed = mon.replay(b.events, cfg, "T4")
        live = _live_looks(b.events, cfg, "T4")
        self.assertEqual(len(replayed), len(live))
        self.assertGreater(len(replayed), 6)
        for r, l in zip(replayed, live):
            self.assertEqual(r["n"], l["n"])
            self.assertEqual(r["trigger"], l["trigger"])
            self.assertEqual(r["pair_updated"], l["pair_updated"])
            self.assertEqual(r["n_collapsed"], l["n_collapsed"])
            for key in ("sum_lower_h", "sum_upper_h", "sum_lower_s", "sum_upper_s",
                        "radius", "L_h", "U_h", "L_s", "U_s"):
                self.assertEqual(repr(r[key]), repr(l[key]), key)

    def test_replay_cadence_is_the_closed_trigger_set(self):
        """No look at a metrics_scrape, a server_* or an anchor event; one per enroll."""
        cfg = frozen_config(6)
        looks = mon.replay(self._chain().events, cfg, "T4")
        self.assertEqual(set(l["trigger"] for l in looks) - set(mon.TRIGGERS), set())
        self.assertEqual(sum(1 for l in looks if l["trigger"] == "enroll"), 6)
        self.assertEqual(sum(1 for l in looks if l["trigger"] == "reveal"), 12)
        # 2 raising call events per pair (the t_send of the first request and its t_recv) x 2 arms
        self.assertEqual(sum(1 for l in looks if l["trigger"] == "call"), 6 * 4)
        ns = [l["n"] for l in looks]
        self.assertEqual(ns, sorted(ns))  # non-decreasing
        enroll_ns = [l["n"] for l in looks if l["trigger"] == "enroll"]
        self.assertEqual(enroll_ns, list(range(1, 7)))

    def test_replay_excludes_post_decision(self):
        """Post-decision reveals never enter the monitor; a pre-decision pair drains."""
        cfg = frozen_config(4)
        b = _ChainBuilder()
        a1, a2 = b.enroll(1)
        b.reveal(a1, 1, "candidate", 1, 2.0)
        b.reveal(a2, 1, "incumbent", 0, 9.0)
        a3, a4 = b.enroll(2)
        b.call(a4, 10**9, 10**9 + 10**8)  # the partner is still running at the decision
        b.reveal(a3, 2, "candidate", 1, 2.0)
        b.decision("deploy_candidate", 2)
        # PG-2: the decision is taken with one episode pending; it drains under its original arm
        b.reveal(a4, 2, "incumbent", 1, 90.0)
        b._add("traffic_switch", {"decision_seq": 0, "arm": "candidate", "effective_from_arrival": 5})
        post = b.arrival + 1
        b.arrival += 1
        b._add("arm_assigned_by_decision", {"arrival": post, "arm": "candidate", "decision_seq": 0})
        b._add(
            "episode_revealed",
            {
                "arrival": post,
                "pair": 0,
                "position": 1,
                "arm": "candidate",
                "outcome": {"success": 1, "latency_s": 1.0, "completion_tokens": 3},
                "certified_ell": 1.0,
                "tokens_known": 3,
                "post_decision": True,
            },
        )
        looks = mon.replay(b.events, cfg, "T4")
        triggers = [l["trigger"] for l in looks]
        self.assertEqual(
            triggers, ["enroll", "reveal", "reveal", "enroll", "call", "reveal", "drain"]
        )
        drain = looks[-1]
        self.assertEqual(drain["n"], 2)
        self.assertEqual(drain["n_collapsed"], 2)
        self.assertEqual(drain["pair_updated"], 2)
        # the follow-up cohort adds nothing: the decision prefix is closed at the crossing
        self.assertEqual(max(l["n"] for l in looks), 2)

    def test_replay_resume_look(self):
        """One look per resume boundary, at the last fully enrolled prefix."""
        cfg = frozen_config(4)
        b = _ChainBuilder()
        a1, a2 = b.enroll(1)
        b.reveal(a1, 1, "candidate", 1, 2.0)
        b.reveal(a2, 1, "incumbent", 0, 9.0)
        b.inv = "b" * 32  # a new invocation: the resume boundary
        a3, a4 = b.enroll(2)
        b.reveal(a3, 2, "candidate", 0, 2.0)
        b.reveal(a4, 2, "incumbent", 0, 9.0)
        looks = mon.replay(b.events, cfg, "T4")
        triggers = [l["trigger"] for l in looks]
        self.assertEqual(triggers, ["enroll", "reveal", "reveal", "resume", "enroll", "reveal", "reveal"])
        resume = looks[3]
        self.assertEqual(resume["n"], 1)  # the last fully enrolled prefix, before the new pair
        self.assertIsNone(resume["pair_updated"])

    def test_replay_ignores_other_chains_and_events(self):
        cfg = frozen_config(4)
        b = _ChainBuilder()
        a1, a2 = b.enroll(1)
        b.reveal(a1, 1, "candidate", 1, 2.0)
        b.reveal(a2, 1, "incumbent", 1, 2.0)
        foreign = [dict(e, chain="T2") for e in b.events]
        self.assertEqual(mon.replay(foreign, cfg, "T4"), [])
        mixed = list(b.events) + foreign
        self.assertEqual(len(mon.replay(mixed, cfg, "T4")), 3)

    def test_replay_call_must_raise_ell(self):
        cfg = frozen_config(4)
        b = _ChainBuilder()
        a1, a2 = b.enroll(1)
        b.call(a1, 1000, 1000)  # t_send == t_c1: ell stays 0.0, no look
        b.call(a1, 1000, 1000, 1000)
        looks = mon.replay(b.events, cfg, "T4")
        self.assertEqual([l["trigger"] for l in looks], ["enroll"])
        b.call(a1, 1000, 2000)  # now it rises
        looks = mon.replay(b.events, cfg, "T4")
        self.assertEqual([l["trigger"] for l in looks], ["enroll", "call"])

    def test_replay_snapshot_shape(self):
        cfg = frozen_config(4)
        b = _ChainBuilder()
        a1, a2 = b.enroll(1)
        b.reveal(a1, 1, "candidate", 1, 2.0)
        looks = mon.replay(b.events, cfg, "T4")
        snap = looks[-1]
        for key in ("trigger", "n", "n_collapsed", "sum_lower_h", "sum_upper_h", "sum_lower_s",
                    "sum_upper_s", "radius", "L_h", "U_h", "L_s", "U_s", "pair_updated",
                    "pair_enclosure", "flags", "readouts", "sums_fsum"):
            self.assertIn(key, snap)
        self.assertTrue(snap["sums_fsum"])
        self.assertEqual(set(snap["flags"]), {"n_min_ok", "harm", "deploy", "success_guard_ok"})
        self.assertEqual(
            set(snap["readouts"]), {"L_s_vs_010", "L_s_vs_015", "s1_restricted", "completed_prefix"}
        )
        self.assertEqual(json.loads(json.dumps(snap)), snap)  # JSON-ready


# =============================================================================================
# Committed fixtures
# =============================================================================================
class TestFixtures(unittest.TestCase):
    def test_monitor_fixtures_file(self):
        self.assertTrue(FIXTURES_JSON.exists(), "run tests_lab_stats.py --regenerate")
        self.assertEqual(FIXTURES_JSON.read_text(encoding="utf-8"), render_fixtures_json())

    def test_monitor_fixtures(self):
        """Every committed (n, sums) -> (L, U, decision) triple, against the live modules."""
        data = json.loads(FIXTURES_JSON.read_text(encoding="utf-8"))
        self.assertEqual(len(data["cases"]), 200)
        self.assertEqual(data["params"]["alpha_gate"], ALPHA_GATE)
        self.assertEqual(data["params"]["n_min"], N_MIN)
        self.assertEqual(data["params"]["delta"], DELTA)
        mc = mc_of(data["params"]["n_max"])
        kinds = set()
        for case in data["cases"]:
            n = case["n"]
            bh = mon.band(n, case["sum_lower_h"], case["sum_upper_h"], mc)
            bs = mon.band(n, case["sum_lower_s"], case["sum_upper_s"], mc)
            self.assertEqual(bh.radius, case["radius"], case["id"])
            self.assertEqual(bh.lo, case["L_h"], case["id"])
            self.assertEqual(bh.hi, case["U_h"], case["id"])
            self.assertEqual(bs.lo, case["L_s"], case["id"])
            self.assertEqual(bs.hi, case["U_s"], case["id"])
            # the independent recomputation agrees
            ri, lo_i, hi_i = independent_band(n, case["sum_lower_h"], case["sum_upper_h"])
            self.assertLess(abs(ri - case["radius"]), 1e-9, case["id"])
            self.assertLess(abs(lo_i - case["L_h"]), 1e-9, case["id"])
            self.assertLess(abs(hi_i - case["U_h"]), 1e-9, case["id"])
            self.assertEqual(
                independent_decision(
                    n, case["L_h"], case["U_h"], case["L_s"], case["U_s"],
                    all_collapsed=case["all_collapsed"], n_max=data["params"]["n_max"],
                ),
                case["decision"],
                case["id"],
            )
            # and lab_monitor.decide agrees on a state rebuilt from the blocks
            st = state_from_blocks(case["blocks"], mc)
            self.assertEqual(st.n, n, case["id"])
            self.assertEqual(st.sums()[0], case["sum_lower_h"], case["id"])
            self.assertEqual(st.sums()[1], case["sum_upper_h"], case["id"])
            self.assertEqual(st.sums()[2], case["sum_lower_s"], case["id"])
            self.assertEqual(st.sums()[3], case["sum_upper_s"], case["id"])
            got = mon.decide(st, mc)
            self.assertEqual("none" if got is None else got.kind, case["decision"], case["id"])
            kinds.add(case["decision"])
        self.assertEqual(
            kinds, {"none", "deploy_candidate", "harm_keep_incumbent", "horizon_no_decision"}
        )

    def test_signatures_match_architecture(self):
        """The public signatures of ARCHITECTURE sections 3.7 and 3.8, name for name."""
        expected = {
            (enc, "tiers_from_config"): "(cfg: 'dict') -> 'list[winstats.Tier]'",
            (enc, "outcome_vector"): "(view: 'EpisodeView', names: 'Sequence[str]') -> 'list[float]'",
            (enc, "certified_elapsed"): "(call_stamps: 'Sequence[tuple[int, int]]') -> 'float'",
            (enc, "success_enclosure"):
                "(candidate: 'EpisodeView', incumbent: 'EpisodeView') -> 'Enclosure'",
            (enc, "final_scores"): (
                "(candidate: 'EpisodeView', incumbent: 'EpisodeView', tiers: 'list[winstats.Tier]')"
                " -> 'tuple[int, int, int]'"
            ),
            (enc, "hierarchy_enclosure"): (
                "(candidate: 'EpisodeView', incumbent: 'EpisodeView', tiers: 'list[winstats.Tier]')"
                " -> 'Enclosure'"
            ),
            (enc, "pair_enclosure"): (
                "(candidate: 'EpisodeView', incumbent: 'EpisodeView', tiers: 'list[winstats.Tier]')"
                " -> 'PairEnclosure'"
            ),
            (enc, "assert_monotone"): "(old: 'PairEnclosure', new: 'PairEnclosure') -> 'None'",
            (mon, "band"):
                "(n: 'int', s_lower: 'float', s_upper: 'float', mc: 'MonitorConfig') -> 'Band'",
            (mon, "decide"): "(state: 'MonitorState', mc: 'MonitorConfig') -> 'Decision | None'",
            (mon, "replay"):
                "(events: 'Sequence[Mapping]', cfg: 'dict', trial: 'str') -> 'list[dict]'",
            (mon, "radius_table"): "(ns: 'Sequence[int]', mc: 'MonitorConfig') -> 'list[dict]'",
        }
        for (module, name), sig in expected.items():
            self.assertEqual(str(inspect.signature(getattr(module, name))), sig, name)
        for name in ("h", "s", "collapsed", "decisive_tier"):
            self.assertIn(name, PairEnclosure.__dataclass_fields__)
        for name in ("arm", "revealed", "success", "latency_s", "completion_tokens", "ell",
                     "tokens_known"):
            self.assertIn(name, EpisodeView.__dataclass_fields__)
        for name in ("n", "radius", "s_lower", "s_upper", "lo", "hi"):
            self.assertIn(name, mon.Band.__dataclass_fields__)
        for name in ("alpha_gate", "rho", "delta", "n_min", "n_max", "clip_lo", "clip_hi"):
            self.assertIn(name, MonitorConfig.__dataclass_fields__)
        self.assertEqual(mon.Decision("horizon_no_decision", 1, None, None).rule_id, "nm_guarded_v3")

    def test_taxonomy_is_lab_commons(self):
        """When lab_common exists, the exceptions raised here are its classes, not local ones."""
        try:
            import lab_common
        except ImportError:  # pragma: no cover - G1 not landed yet
            self.skipTest("lab_common not present yet")
        self.assertTrue(enc._LAB_COMMON_PRESENT)
        self.assertIs(EnclosureError, lab_common.EnclosureError)
        self.assertIs(MonitorError, lab_common.MonitorError)
        self.assertIs(FrozenMismatch, lab_common.FrozenMismatch)


# =============================================================================================
# Fixture generation (regenerated, never typed)
# =============================================================================================
def render_radius_csv() -> str:
    rows = mon.radius_table(RADIUS_NS, mc_of(max(RADIUS_NS)))
    lines = ["n,radius"]
    for row in rows:
        lines.append(f"{row['n']},{row['radius']!r}")
    return "\n".join(lines) + "\n"


def _case(case_id: int, blocks) -> dict:
    n = sum(int(b[0]) for b in blocks)
    lo_h = math.fsum(v for b in blocks for v in [b[1]] * int(b[0]))
    hi_h = math.fsum(v for b in blocks for v in [b[2]] * int(b[0]))
    lo_s = math.fsum(v for b in blocks for v in [b[3]] * int(b[0]))
    hi_s = math.fsum(v for b in blocks for v in [b[4]] * int(b[0]))
    n_collapsed = sum(int(b[0]) for b in blocks if b[5])
    all_collapsed = n_collapsed == n
    mc = mc_of(N_MAX)
    bh = mon.band(n, lo_h, hi_h, mc)
    bs = mon.band(n, lo_s, hi_s, mc)
    verdict = independent_decision(
        n, bh.lo, bh.hi, bs.lo, bs.hi, all_collapsed=all_collapsed, n_max=N_MAX
    )
    return {
        "id": case_id,
        "n": n,
        "blocks": [[int(b[0]), b[1], b[2], b[3], b[4], bool(b[5]), int(b[6])] for b in blocks],
        "sum_lower_h": lo_h,
        "sum_upper_h": hi_h,
        "sum_lower_s": lo_s,
        "sum_upper_s": hi_s,
        "n_collapsed": n_collapsed,
        "all_collapsed": all_collapsed,
        "radius": bh.radius,
        "L_h": bh.lo,
        "U_h": bh.hi,
        "L_s": bs.lo,
        "U_s": bs.hi,
        "decision": verdict,
    }


def _build_cases() -> list[dict]:
    rng = random.Random(60260919)
    specs: list[list] = []

    # A. below n_min, as extreme as the scores allow: nothing may decide.
    for n in (1, 2, 5, 17, 42, 63, 77, 91, 92, 99):
        specs.append(uniform_blocks(n, 1.0, 1.0))
        specs.append(uniform_blocks(n, -1.0, -1.0))

    # B. clipping at both ends.
    for n in (100, 150, 200, 295, 400, 568):
        specs.append(uniform_blocks(n, 1.0, 1.0))
        specs.append(uniform_blocks(n, -1.0, -1.0))
        specs.append(open_blocks(n))

    # C. the deploy boundary, from both sides, in both coordinates.
    for n in (100, 150, 200, 295, 400, 500, 568):
        r = independent_radius(n)
        for eps in (-1e-3, -1e-6, 1e-6, 1e-3):
            specs.append(uniform_blocks(n, min(1.0, r + 1e-3), max(-1.0, min(1.0, r - DELTA + eps))))
            specs.append(uniform_blocks(n, max(-1.0, min(1.0, r + eps)), min(1.0, r - DELTA + 1e-3)))

    # D. the harm boundary (U_h < 0), from both sides.
    for n in (100, 150, 200, 295, 400, 500, 568):
        r = independent_radius(n)
        for eps in (-1e-3, -1e-6, 1e-6, 1e-3):
            specs.append(uniform_blocks(n, max(-1.0, -r + eps), 0.0))

    # E. the horizon, resolved and unresolved.
    for zbar in (0.0, 0.1, -0.1):
        specs.append(uniform_blocks(N_MAX, zbar, 0.0))
        specs.append([(N_MAX - 1, zbar, zbar, 0.0, 0.0, True, -1), (1, -1.0, 1.0, -1.0, 1.0, False, -1)])
    specs.append(uniform_blocks(N_MAX - 1, 0.0, 0.0))

    # F. random mixtures of collapsed and open pairs.
    while len(specs) < 200:
        n = rng.randint(1, N_MAX)
        open_n = rng.randint(0, min(3, n))
        rest = n - open_n
        wins = rng.randint(0, rest)
        losses = rng.randint(0, rest - wins)
        ties = rest - wins - losses
        blocks = []
        if wins:
            d = float(rng.choice([1, 0]))  # a tier-1 win has d = 0, a tier-0 win has d = +1
            blocks.append((wins, 1.0, 1.0, d, d, True, 0 if d else 1))
        if losses:
            d = float(rng.choice([-1, 0]))
            blocks.append((losses, -1.0, -1.0, d, d, True, 0 if d else 1))
        if ties:
            blocks.append((ties, 0.0, 0.0, 0.0, 0.0, True, -1))
        if open_n:
            blocks.append((open_n, -1.0, 1.0, -1.0, 1.0, False, -1))
        if not blocks:
            continue
        specs.append(blocks)

    specs = specs[:200]
    return [_case(i, blocks) for i, blocks in enumerate(specs)]


def render_fixtures_json() -> str:
    payload = {
        "schema": "live_ab/monitor_fixtures/v1",
        "provenance": {
            "generator": "experiments/live_ab/tests_lab_stats.py --regenerate",
            "radius_from": "src/winstats.py normal_mixture_radius",
            "checked_against": "independent recomputation of protocol_FINAL.md 8.2 and 8.4 "
            "using the math module (tests_lab_stats.independent_band / independent_decision)",
            "hand_typed_values": False,
        },
        "params": {
            "alpha_gate": ALPHA_GATE,
            "rho": RHO,
            "delta": DELTA,
            "n_min": N_MIN,
            "n_max": N_MAX,
            "variance_process": "n",
            "clip": [-1.0, 1.0],
        },
        "block_format": ["count", "h_lo", "h_hi", "s_lo", "s_hi", "collapsed", "decisive_tier"],
        "cases": _build_cases(),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def regenerate() -> list[Path]:
    TESTDATA.mkdir(parents=True, exist_ok=True)
    RADIUS_CSV.write_text(render_radius_csv(), encoding="utf-8")
    FIXTURES_JSON.write_text(render_fixtures_json(), encoding="utf-8")
    return [RADIUS_CSV, FIXTURES_JSON]


if __name__ == "__main__":
    if "--regenerate" in sys.argv:
        for path in regenerate():
            print(f"wrote {path}")
    else:
        unittest.main()
