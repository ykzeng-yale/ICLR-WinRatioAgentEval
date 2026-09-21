"""THE END-TO-END INTEGRATION FIXTURE for the v2 calibration entry point.

Root's 2026-09-21 06:35 disposition:

    "Before any full panel, demonstrate this actual entry point on the existing
    development coordinates with a small deterministic integration fixture: it
    must expose a known oracle-versus-operational boundary, the existing
    first-decision/drain witness, reference call counts, and retained H/D
    outputs.  A FIXTURE THAT ONLY TESTS ``vcompare`` IS INSUFFICIENT."

So every test here drives ``vpanel.run_panel`` -- the real entry point writing
real artifacts to a real directory -- or the primary functions it calls.  None
of them touches ``vcompare``.

Bounded by construction: the largest run below is 3 cells x 1 program x 4
trials at n_max = 300.  No full grid, no panel scale, no live episode.

Run:  python tests_panel.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import vband                                                    # noqa: E402
import vgen                                                     # noqa: E402
import vpanel                                                   # noqa: E402
import vpolicy                                                  # noqa: E402
import vrun                                                     # noqa: E402
from reference import eb_reference                              # noqa: E402


# ---------------------------------------------------------------------------
# The frozen fixture coordinate.
#
# Found by scanning every cell x program x trial at n_max = 120 for the
# EARLIEST tick at which the oracle and operational enclosures disagree.  It is
# the same boundary CLASS the root adjudicated at C2/2011, C3/2160 and C7/2090
# -- a revealed arm of cost 10.0 against a pending elapsed cost of
# 10.526315789473685 -- reproduced here at a coordinate small enough to assert
# exactly.  The forward certificate's margin is EXACTLY ZERO here:
# (1 - tol) * ell = 10.0 and the revealed cost is 10.0, so the strict
# inequality fails on the threshold itself, not merely on the epsilon.
# ---------------------------------------------------------------------------
FIX_CELL = "C1"
FIX_PROGRAM = 1
FIX_TRIAL = 3
FIX_N_MAX = 120
FIX_TICK = 6
FIX_PAIR = 1                       # 1-based enrollment position
FIX_ELL = 10.526315789473685
FIX_REVEALED_COST = 10.0
FIX_ORACLE = (-1.0, -1.0)
FIX_OPERATIONAL = (-1.0, 0.0)


def _cell(cid: str):
    return next(c for c in vgen.CELLS if c.id == cid)


class TestOracleVersusOperationalBoundary(unittest.TestCase):
    """F1.  A KNOWN boundary, asserted by value, on the primary's own path."""

    def setUp(self):
        self.draw = vgen.draw_trial(_cell(FIX_CELL), FIX_PROGRAM, FIX_TRIAL,
                                    n_max=FIX_N_MAX)

    def _states(self, policy):
        pos = np.arange(1, self.draw.n + 1, dtype=np.int64)
        ages = np.maximum(np.where(pos <= min(FIX_TICK, FIX_N_MAX),
                                   FIX_TICK - pos, 0), 0)
        return vgen.state_at_age(self.draw, ages, policy)

    def test_the_fixture_coordinate_is_the_state_it_claims_to_be(self):
        """If the draw ever changes, every number below must stop meaning this."""
        i = FIX_PAIR - 1
        pos = np.arange(1, self.draw.n + 1, dtype=np.int64)
        age = FIX_TICK - pos[i]
        ell = vgen.elapsed_cost(self.draw.c_pend[i], age, self.draw.d[i])
        self.assertEqual(float(self.draw.c_rev[i]), FIX_REVEALED_COST)
        self.assertEqual(float(ell), FIX_ELL)
        self.assertEqual(int(self.draw.s_rev[i]), 1, "the revealed arm succeeded")
        self.assertLess(int(self.draw.f[i]), age, "revealed by this age")
        self.assertGreater(int(self.draw.d[i]), age, "not yet resolved")

    def test_the_two_policies_disagree_exactly_as_recorded(self):
        o, p = self._states("oracle"), self._states("operational")
        i = FIX_PAIR - 1
        self.assertEqual((float(o.h_lo[i]), float(o.h_hi[i])), FIX_ORACLE)
        self.assertEqual((float(p.h_lo[i]), float(p.h_hi[i])), FIX_OPERATIONAL)

    def test_the_operational_interval_contains_the_oracle_one(self):
        """Conservatism is the CLAIM; containment is the check."""
        o, p = self._states("oracle"), self._states("operational")
        self.assertTrue(np.all(p.h_lo <= o.h_lo) and np.all(p.h_hi >= o.h_hi))
        self.assertTrue(np.all(p.s_lo <= o.s_lo) and np.all(p.s_hi >= o.s_hi))

    def test_the_forward_certificate_fails_on_the_threshold_itself(self):
        i = FIX_PAIR - 1
        m = vpolicy.certificate_margins(
            vband.Episode.pending("rev", vgen.COST_CAP).finalized(
                int(self.draw.s_rev[i]), float(self.draw.c_rev[i])),
            vband.Episode.pending("pend", vgen.COST_CAP).with_elapsed_cost(FIX_ELL))
        self.assertIsNotNone(m)
        self.assertEqual(m["forward_margin"], 0.0,
                         "this fixture is the exact-threshold case")
        self.assertGreater(m["reverse_margin"], 0.0)

    def test_the_runner_actually_carries_the_disagreement_into_its_sums(self):
        """The per-pair difference must survive into the tick-batched sums."""
        last = FIX_N_MAX + vgen.DRAIN_W
        o = vgen.adapter_tick_sums(self.draw, FIX_N_MAX, last, policy="oracle")
        p = vgen.adapter_tick_sums(self.draw, FIX_N_MAX, last, policy="operational")
        self.assertNotEqual(float(o.h_hi[FIX_TICK]), float(p.h_hi[FIX_TICK]),
                            "a per-pair difference that vanishes from the sums "
                            "would make the policy seam decorative")
        self.assertEqual(float(p.h_hi[FIX_TICK]) - float(o.h_hi[FIX_TICK]), 1.0)


class TestPolicyIsTheDeployedPolicy(unittest.TestCase):
    """F2.  vgen's vectorised rule IS vpolicy's, not a lookalike."""

    def test_every_enrolled_pair_matches_vpolicy(self):
        cfg = vrun.make_config(FIX_N_MAX, vgen.NAMESPACE_GRID,
                               schedule=vrun.SCHEDULE_V2, policy="operational")
        draw = vgen.draw_trial(_cell(FIX_CELL), FIX_PROGRAM, FIX_TRIAL,
                               n_max=FIX_N_MAX)
        rep = vrun.assert_operational_matches_policy(draw, cfg)
        self.assertGreater(rep["pair_states_compared"], 0)

    def test_a_drifted_epsilon_is_caught(self):
        cfg = vrun.make_config(FIX_N_MAX, vgen.NAMESPACE_GRID,
                               schedule=vrun.SCHEDULE_V2, policy="operational")
        draw = vgen.draw_trial(_cell(FIX_CELL), FIX_PROGRAM, FIX_TRIAL,
                               n_max=FIX_N_MAX)
        saved = vgen.OPERATIONAL_EPS
        try:
            vgen.OPERATIONAL_EPS = saved * 10.0
            with self.assertRaises(AssertionError):
                vrun.assert_operational_matches_policy(draw, cfg)
        finally:
            vgen.OPERATIONAL_EPS = saved

    def test_v1_refuses_an_operational_policy(self):
        """Oracle numbers under an operational label is the defect, not a fallback."""
        cfg = vrun.make_config(50, vgen.NAMESPACE_GRID,
                               schedule=vrun.SCHEDULE_V1, policy="operational")
        with self.assertRaises(ValueError):
            vrun.build_series(vgen.draw_trial(_cell("C1"), 0, 0, n_max=50), cfg)

    def test_an_unknown_policy_is_rejected_at_config_time(self):
        with self.assertRaises(ValueError):
            vrun.make_config(50, vgen.NAMESPACE_GRID, policy="whatever")

    def test_v1_reproduction_is_preserved(self):
        """The oracle default must still be bit-for-bit what v1 deposited."""
        cfg = vrun.make_config(80, vgen.NAMESPACE_GRID, schedule=vrun.SCHEDULE_V1)
        self.assertEqual(cfg.policy, "oracle")
        draw = vgen.draw_trial(_cell("C1"), 0, 0, n_max=80)
        vrun.assert_v2_reduces_to_v1(draw, cfg)


class TestPanelEndToEnd(unittest.TestCase):
    """F3.  The real entry point, real artifacts, real counts."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="vpanel_fixture_"))
        cls.cfg = vpanel.PanelConfig(cells=("C2", "C3", "C7"), n_max=300,
                                     programs=1, policy="operational",
                                     label="integration_fixture")
        cls.out = cls.tmp / "run"
        cls.receipt = vpanel.run_panel(cls.cfg, cls.out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_all_three_artifacts_exist(self):
        for name in ("primary_rows.csv.gz", "reference_bands.csv", "receipt.json"):
            self.assertTrue((self.out / name).is_file(), name)

    def test_the_receipt_records_the_policy_actually_executed(self):
        self.assertEqual(self.receipt["config"]["policy"], "operational")
        self.assertGreater(self.receipt["counts"]["policy_pair_states"], 0,
                           "a receipt claiming a policy must also evidence it")

    def test_reference_call_counts_are_exactly_the_frozen_workload(self):
        c = self.receipt["counts"]
        trials = c["trials"]
        self.assertEqual(c["reference_calls_h"], trials)
        self.assertEqual(c["reference_calls_d"], trials)
        self.assertEqual(c["reference_calls_h"] + c["reference_calls_d"],
                         trials * vpanel.REFERENCE_CALLS_PER_TRIAL)
        # four trials per program therefore EIGHT calls per program
        per_program = (c["reference_calls_h"] + c["reference_calls_d"]) / c["programs"]
        self.assertEqual(per_program, 8.0)

    def test_the_hd_outputs_are_retained_not_discarded(self):
        """The defect was computing the bands and dropping them."""
        text = (self.out / "reference_bands.csv").read_text().strip().splitlines()
        self.assertEqual(text[0], vpanel.REFERENCE_HEADER)
        body = text[1:]
        c = self.receipt["counts"]
        want = c["trials"] * len(vpanel.SCORES) * len(self.receipt["declared_prefixes"])
        self.assertEqual(len(body), want)
        self.assertEqual(c["reference_rows"], want)
        scores = {r.split(",")[5] for r in body}
        self.assertEqual(scores, {"H", "D"}, "both score paths must be retained")

    def test_the_retained_band_is_the_reference_band_at_that_prefix(self):
        """A retained number that is not the reference's own is a placeholder."""
        rows = [r.split(",") for r in
                (self.out / "reference_bands.csv").read_text().strip().splitlines()[1:]]
        cell = _cell("C7")
        draw = vgen.draw_trial(cell, 0, 0, n_max=300, namespace=vgen.NAMESPACE_GRID)
        for score, values in (("H", draw.z), ("D", draw.dsc)):
            lo, hi = eb_reference.reference_bands(
                np.asarray(values, dtype=np.float64), vband.ALPHA_GATE)
            for r in rows:
                if r[0] == "C7" and int(r[3]) == 0 and int(r[4]) == 0 and r[5] == score:
                    n = int(r[6])
                    self.assertEqual(float(r[7]), float(lo[n - 1]),
                                     f"{score} lcb at prefix {n}")
                    self.assertEqual(float(r[8]), float(hi[n - 1]),
                                     f"{score} ucb at prefix {n}")

    def test_the_bands_are_indexed_at_the_declared_prefixes(self):
        declared = self.receipt["declared_prefixes"]
        self.assertEqual(declared, list(vrun.make_config(
            300, vgen.NAMESPACE_GRID, schedule=vrun.SCHEDULE_V2).horizons))
        seen = {int(r.split(",")[6]) for r in
                (self.out / "reference_bands.csv").read_text().strip().splitlines()[1:]}
        self.assertEqual(seen, set(declared))

    def test_the_receipt_binds_identities_seeds_and_hashes(self):
        r = self.receipt
        for key in ("panel_version", "config", "seeds", "code_sha256",
                    "reference_sha256", "reference_tuning", "counts",
                    "outputs", "claims"):
            self.assertIn(key, r)
        for name, meta in r["outputs"].items():
            self.assertRegex(meta["sha256"], r"^[0-9a-f]{64}$", name)
        self.assertEqual(r["reference_tuning"]["boundary_type"], "mixture")
        self.assertEqual(r["reference_tuning"]["v_opt"], 10.0)
        self.assertFalse(r["claims"]["is_calibration"])
        self.assertFalse(r["claims"]["is_coverage_rate"])
        self.assertEqual(r["claims"]["convention"], "deterministic-path")

    def test_the_recorded_output_hashes_are_the_bytes_on_disk(self):
        import hashlib
        for name, meta in self.receipt["outputs"].items():
            got = hashlib.sha256((self.out / name).read_bytes()).hexdigest()
            self.assertEqual(got, meta["sha256"], name)

    def test_it_refuses_to_overwrite_a_deposited_receipt(self):
        with self.assertRaises(vpanel.PanelError):
            vpanel.run_panel(self.cfg, self.out)


class TestPanelFailsClosed(unittest.TestCase):
    """F4.  Every refusal demonstrated, not described."""

    def test_the_call_budget_assertion_actually_fires(self):
        with self.assertRaises(vpanel.PanelError):
            vpanel.assert_reference_call_budget(
                {"reference_calls_h": 3, "reference_calls_d": 3}, trials=4)

    def test_unpaired_h_and_d_calls_are_refused(self):
        with self.assertRaises(vpanel.PanelError):
            vpanel.assert_reference_call_budget(
                {"reference_calls_h": 5, "reference_calls_d": 3}, trials=4)

    def test_a_correct_budget_passes(self):
        vpanel.assert_reference_call_budget(
            {"reference_calls_h": 4, "reference_calls_d": 4}, trials=4)

    def test_an_operational_v1_config_is_refused(self):
        with self.assertRaises(vpanel.PanelError):
            vpanel.PanelConfig(cells=("C1",), n_max=50, programs=1,
                               policy="operational", schedule=vrun.SCHEDULE_V1)

    def test_an_unknown_cell_is_refused(self):
        tmp = Path(tempfile.mkdtemp(prefix="vpanel_bad_"))
        try:
            with self.assertRaises(vpanel.PanelError):
                vpanel.run_panel(
                    vpanel.PanelConfig(cells=("C99",), n_max=50, programs=1),
                    tmp / "run")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_primary_never_names_the_reference(self):
        """THE ONE-WAY DEPENDENCY, read off the source rather than asserted."""
        rep = vpanel.assert_reference_is_not_consulted()
        self.assertFalse(rep["reference_named_in_primary"])
        self.assertIn("vrun.py", rep["primary_sources_checked"])
        self.assertIn("vgen.py", rep["primary_sources_checked"])


class TestDrainAndFirstDecisionWitness(unittest.TestCase):
    """F5.  The drain window, and an HONEST record of what it does NOT show.

    Root asked the fixture to expose "the existing first-decision/drain
    witness".  Two separate facts, and only one of them reproduces here:

      * The drain LOOKS exist on the primary's own axis and are evaluated --
        asserted below.
      * A drain-window DECISION does not occur at fixture scale.  Scanning all
        eight cells x 3 programs x 4 trials at n_max = 400 and again at 1,000
        (192 trials) found ZERO decisions with tau > N_max and ZERO cases where
        the v1 and v2 schedules reached different (decision, tau).  The root's
        own tick-1200-to-1010 witness is a CONSTRUCTED one, not a draw from
        these cells, which is consistent with that.

    So this fixture does NOT reproduce the decision-timing half, and says so
    rather than implying it.  Recording the negative scan is the point.
    """

    def test_the_drain_window_carries_real_looks_on_the_primary_axis(self):
        cfg = vrun.make_config(FIX_N_MAX, vgen.NAMESPACE_GRID,
                               schedule=vrun.SCHEDULE_V2, policy="operational")
        draw = vgen.draw_trial(_cell(FIX_CELL), FIX_PROGRAM, FIX_TRIAL,
                               n_max=FIX_N_MAX)
        series, _, _, _ = vrun.build_series_for(draw, cfg, vrun.SCHEDULE_V2)
        ticks = series[vrun.ADAPTER].tick
        self.assertEqual(int(ticks[-1]), cfg.finalization_tick)
        drain = int((ticks > FIX_N_MAX).sum())
        self.assertEqual(drain, vgen.DRAIN_W,
                         "every drain tick must carry a look")
        # and the enclosure must still be narrowing in there
        self.assertGreaterEqual(float(series[vrun.ADAPTER].l_h[-1]),
                                float(series[vrun.ADAPTER].l_h[FIX_N_MAX - 1]))

    def test_no_drain_window_decision_at_fixture_scale(self):
        """The negative result, executed rather than remembered."""
        cfg = vrun.make_config(400, vgen.NAMESPACE_GRID,
                               schedule=vrun.SCHEDULE_V2, policy="operational")
        late = 0
        for cell in vgen.CELLS[:4]:
            for trial in range(2):
                draw = vgen.draw_trial(cell, 0, trial, n_max=400)
                rec, _, _ = vrun.evaluate_trial(draw, cfg, vrun.SCHEDULE_V2)
                for name in vrun.CONSTRUCTIONS:
                    r = rec[name]
                    if r.decision != 0 and r.tau is not None and r.tau > 400:
                        late += 1
        self.assertEqual(late, 0,
                         "if this ever fires, the fixture has found the "
                         "decision-timing witness and this test must be "
                         "rewritten to assert it rather than its absence")


class TestTimedCoreIdentity(unittest.TestCase):
    """F6.  The identity that binds a projection to the run it prices.

    Guard v2 refuses `identity_unverifiable`.  The root supplied the principle
    -- "a whole-file hash difference alone does not prove the timed core
    changed" -- so the identity has to distinguish the two, and these tests
    check that it actually does rather than that it claims to.
    """

    def setUp(self):
        import videntity
        self.vi = videntity
        self.src = {m: (HERE / f"{m}.py").read_text() for m in videntity.TIMED_MODULES}

    def test_the_closure_is_not_empty(self):
        """An identity over nothing matches anything."""
        closure = self.vi.timed_core_closure(self.src)
        self.assertGreater(len(closure), 10)
        names = {f"{m}.{n}" for m, n in closure}
        for entry in ("vgen.draw_trial", "vrun.evaluate_trial", "vrun.trial_rows"):
            self.assertIn(entry, names)

    def test_an_empty_closure_raises_rather_than_returning_a_digest(self):
        with self.assertRaises(self.vi.IdentityError):
            self.vi.timed_core_identity(self.src, entry_points=(("vgen", "nope"),))

    def test_a_docstring_edit_does_NOT_move_the_timed_core(self):
        """The whole point: documentation is not executable change."""
        before = self.vi.timed_core_identity(self.src)["timed_core_sha256"]
        edited = dict(self.src)
        edited["vgen"] = edited["vgen"].replace(
            '"""PROTOCOL 4.3: ``ell(a) = (c * a) / D``, in that evaluation order.',
            '"""ENTIRELY DIFFERENT PROSE that changes no executable structure.',
            1)
        self.assertNotEqual(edited["vgen"], self.src["vgen"], "the edit must land")
        after = self.vi.timed_core_identity(edited)["timed_core_sha256"]
        self.assertEqual(before, after)

    def test_an_executable_edit_DOES_move_the_timed_core(self):
        """And the converse, or the identity would be decorative."""
        before = self.vi.timed_core_identity(self.src)["timed_core_sha256"]
        edited = dict(self.src)
        edited["vgen"] = edited["vgen"].replace(
            "return (c_pend * age) / np.where(d > 0, d, 1)",
            "return (c_pend * age) / np.where(d > 0, d, 2)", 1)
        self.assertNotEqual(edited["vgen"], self.src["vgen"], "the edit must land")
        after = self.vi.timed_core_identity(edited)["timed_core_sha256"]
        self.assertNotEqual(before, after)

    # ---- the root's three counterexamples, kept as REGRESSION tests -------
    # reviews/evidence/v2_identity_checks_20260921_0750.py.  They are asserted
    # in the direction that REFUTES the fingerprint, so nobody can quietly
    # promote it back into an authorization path and have the suite agree.

    def test_counterexample_1_it_misses_module_level_constants(self):
        """The refutation: an executable edit this identity cannot see."""
        before = self.vi.timed_core_identity(self.src)["timed_core_sha256"]
        needle = "OPERATIONAL_EPS: float = 1e-9"
        self.assertIn(needle, self.src["vgen"])
        edited = dict(self.src)
        edited["vgen"] = edited["vgen"].replace(needle, "OPERATIONAL_EPS: float = 1.0")
        after = self.vi.timed_core_identity(edited)["timed_core_sha256"]
        self.assertEqual(before, after,
                         "this EQUALITY is the defect, recorded deliberately")
        # and the mutation really does change behaviour, at revealed cost 10
        # against pending lower cost 11:
        self.assertTrue((1 - 0.05) * 11 > 10 + 1e-9)
        self.assertFalse((1 - 0.05) * 11 > 10 + 1.0)

    def test_counterexample_2_partly_missing_entry_is_now_REJECTED(self):
        """The one defect of the three that is a plain bug, so it is fixed."""
        with self.assertRaises(self.vi.IdentityError):
            self.vi.timed_core_identity(
                self.src, (("vrun", "evaluate_trial"), ("vrun", "MISSING_ENTRY")))

    def test_counterexample_3_orchestrator_and_reference_are_outside_scope(self):
        ident = self.vi.timed_core_identity(self.src)
        members = ident["per_member_sha256"]
        self.assertFalse(any(m.startswith("vpanel.") for m in members))
        self.assertFalse(any(m.startswith("eb_reference.") for m in members))

    def test_the_authorization_surface_is_GONE_not_deprecated(self):
        with self.assertRaises(self.vi.IdentityError):
            self.vi.identities(HERE, policy="operational")


class TestWholeFilePinsBindExecution(unittest.TestCase):
    """F7.  The replacement the root ruled for: whole-file pins, complete scope."""

    def setUp(self):
        import vpins
        self.vpins = vpins

    def _pins(self):
        return self.vpins.entry_point_pins(
            policy="operational", schedule=vrun.SCHEDULE_V2, prefixes=[100, 500],
            programs=[1000], cells=["C1"], namespace=1, alpha_gate=vband.ALPHA_GATE,
            trials_per_program=4, workload="2_calls_per_trial")

    def test_the_pin_covers_the_orchestrator_reference_and_guard(self):
        """Exactly the scope counterexample 3 showed the fingerprint omitted."""
        files = self._pins()["detail"]["source"]["files"]
        for needed in ("vpanel.py", "reference/eb_reference.py", "vrun.py",
                       "vgen.py", "vband.py", "vpolicy.py", "vtotalguard.py"):
            self.assertIn(needed, files, needed)

    def test_the_compiled_reference_binary_is_pinned(self):
        b = self._pins()["detail"]["source"]["binaries"]
        self.assertTrue(b, "a rebuilt .so must not be invisible")
        self.assertTrue(any(k.endswith(".so") for k in b))

    def test_a_module_level_constant_edit_DOES_move_the_whole_file_pin(self):
        """The whole point of choosing whole-file over the fingerprint."""
        before = self._pins()["code"]
        src = HERE / "vgen.py"
        original = src.read_bytes()
        try:
            src.write_text(original.decode().replace(
                "OPERATIONAL_EPS: float = 1e-9",
                "OPERATIONAL_EPS: float = 1.0", 1))
            after = self._pins()["code"]
        finally:
            src.write_bytes(original)
        self.assertNotEqual(before, after,
                            "the edit the fingerprint missed must move this pin")

    def test_drift_across_a_measurement_is_detected_and_refused(self):
        before = self._pins()
        src = HERE / "vgen.py"
        original = src.read_bytes()
        try:
            src.write_bytes(original + b"\n# drift\n")
            after = self._pins()
            with self.assertRaises(self.vpins.PinError):
                self.vpins.assert_unchanged(before, after)
        finally:
            src.write_bytes(original)

    def test_no_drift_passes_and_reports_what_it_compared(self):
        rep = self.vpins.assert_unchanged(self._pins(), self._pins())
        self.assertFalse(rep["drift"])
        self.assertIn("vpanel.py", rep["files_compared"])

    def test_these_pins_satisfy_guard_v2(self):
        import json as _json
        cfg = _json.loads((HERE / "cells.json").read_text())
        ids = {k: self._pins()[k] for k in
               ("code", "config", "policy", "workload", "receipt")}
        entry = {"tier": "T1", "programs_total": 10, "N_max": 2000,
                 "seconds_projected": 100.0, "bytes_projected": 1.0,
                 "peak_rss_projected": 1, "admissible": True,
                 "reference_seconds_projected": 200.0,
                 "total_seconds_projected": 300.0,
                 "reference_cost_unresolved": False}
        budget = {"selected_tier": "T1", "ladder": [entry], "paused": False,
                  "reference_workload": {"combined_workload_receipt": {
                      "present": True, "identities": dict(ids),
                      "planned_groups": 12, "groups_total": 12}}}
        ok = vrun.total_workload_guard(budget, cfg, {"identities": ids})
        self.assertTrue(ok["authorized"], ok.get("refusal"))


class TestModesAndBounds(unittest.TestCase):
    """F8.  The entry point CALLS the guard, and refuses outside its allowlist."""

    def test_non_frozen_alpha_is_refused(self):
        """It was used by the reference and ignored by the primary."""
        with self.assertRaises(vpanel.PanelError):
            vpanel.PanelConfig(cells=("C1",), n_max=300, programs=1, alpha_gate=0.5)

    def test_non_frozen_trial_count_is_refused(self):
        with self.assertRaises(vpanel.PanelError):
            vpanel.PanelConfig(cells=("C1",), n_max=300, programs=1,
                               trials_per_program=2)

    def test_measurement_mode_refuses_every_off_allowlist_coordinate(self):
        base = dict(mode=vpanel.MODE_MEASUREMENT, namespace=1,
                    program_indices=(1000, 1001, 1002, 1003, 1004))
        for bad in (dict(cells=("C3",), n_max=1000, programs=5),
                    dict(cells=("C1",), n_max=300, programs=5),
                    dict(cells=("C1",), n_max=1000, programs=5, namespace=0)):
            kw = dict(base); kw.update(bad)
            with self.assertRaises(vpanel.PanelError):
                vpanel.PanelConfig(**kw)

    def test_measurement_mode_requires_explicit_authorized_indices(self):
        with self.assertRaises(vpanel.PanelError):
            vpanel.PanelConfig(cells=("C1",), n_max=1000, programs=5,
                               mode=vpanel.MODE_MEASUREMENT, namespace=1)

    def test_the_authorized_coordinates_are_accepted_and_count_correctly(self):
        import vpins
        c = vpanel.PanelConfig(cells=("C1", "C2"), n_max=1000, programs=5,
                               mode=vpanel.MODE_MEASUREMENT, namespace=1,
                               program_indices=(1000, 1001, 1002, 1003, 1004))
        self.assertEqual(c.trials, 40)          # one horizon; two horizons = 80
        self.assertEqual(vpins.ALLOWLIST.check_arithmetic(),
                         {"units": 20, "trial_evaluations": 80,
                          "reference_calls": 160, "seed_program_identities": 10})

    def test_fixture_mode_is_bounded_and_the_bound_is_enforced(self):
        tmp = Path(tempfile.mkdtemp(prefix="vpanel_bound_"))
        try:
            cfg = vpanel.PanelConfig(cells=("C1", "C2"), n_max=2000, programs=20,
                                     mode=vpanel.MODE_FIXTURE)
            with self.assertRaises(vpanel.PanelError):
                vpanel.run_panel(cfg, tmp / "run")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_full_grid_mode_is_REFUSED_by_the_entry_point_itself(self):
        """Not by a flag, and not by a helper nobody calls."""
        tmp = Path(tempfile.mkdtemp(prefix="vpanel_fullgrid_"))
        try:
            cfg = vpanel.PanelConfig(cells=("C1",), n_max=1000, programs=1,
                                     mode=vpanel.MODE_FULL_GRID)
            with self.assertRaises((vrun.TotalResourceRefusal, vpanel.PanelError)):
                vpanel.run_panel(cfg, tmp / "run")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    r = unittest.main(verbosity=2, exit=False).result
    print(f"\nran={r.testsRun} failures={len(r.failures)} errors={len(r.errors)}")
    raise SystemExit(1 if (r.failures or r.errors) else 0)
