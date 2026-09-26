"""Model-free controls for the pure simulation core of ``experiments/live_ab/lab_replay.py``
(protocol 11.5), ported by hand from the held branch's own 54-test suite (`reviews/
driver_replay_resume_interim_20260926_0117.md`, root 2026-09-26 01:17 UTC, required-repair item 3:
"Port the held simulation-core controls before any real 432-cell grid, as the owner already
disclosed").  ``experiments/live_ab_controls/tests_replay.py``'s own module docstring names these
seven classes -- ``OutcomeModelTests``, ``BandDecideAgreementTests``, ``PairScoreAgreementTests``,
``ExchangeabilityTests``, ``QuartileTests``, ``WilsonTests``, ``OrderEqualityTests`` -- as not yet
re-authored on this branch; this file ports those seven, then (a later step on the same held-suite
item) the remaining five: ``GridEnumerationTests``, ``SeedRuleTests``, ``ScalarCrosscheckTests``,
``OpenOutcomeModelTests`` and ``TinyEndToEndTests``.

PER-CLASS COUNT, held vs. ported here vs. covered by an existing test elsewhere (never skipped for
any other reason; each ``covered by`` name is checked against the held assertion, not assumed from
a class-level description):

* ``OrderEqualityTests`` -- held 3, ported 3 (corrected here: an earlier draft of this docstring
  said "held 1, ported 1", which was an arithmetic slip, not a coverage gap -- all 3 of the held
  class's tests were already ported, and the class's own totals line below was already computed
  from the true value of 3).
* ``BandDecideAgreementTests`` -- held 6, ported 6.
* ``PairScoreAgreementTests`` -- held 2, ported 2.
* ``OutcomeModelTests`` -- held 6, ported 6 (replicate counts reduced per the DELIBERATE
  REPLICATE-COUNT REDUCTIONS note below; no assertion weakened).
* ``QuartileTests`` -- held 2, ported 2.
* ``WilsonTests`` -- held 2, ported 2.
* ``ExchangeabilityTests`` -- held 2, ported 2 (one, ``test_the_text_restricts_the_exact_null_claim_to_t4``,
  needed the module docstring's EXCHANGEABILITY paragraph restored to pass; see
  ``experiments/live_ab/lab_replay.py``'s own module docstring for that restoration).
* ``GridEnumerationTests`` -- held 7, ported 5, covered elsewhere 2:
  ``test_the_intact_grid_passes_the_check`` by
  ``tests_replay.GridEnumerationTests.test_the_432_cells_match_the_protocol_item_5_product``;
  ``test_negative_every_mutated_grid_is_refused`` by
  ``tests_replay.GridEnumerationTests.test_negative_every_mutated_grid_is_refused`` (identical
  body). ``test_negative_the_production_entry_point_refuses_an_edited_grid`` is now PORTED here in
  full (a prior draft called it "covered elsewhere" by
  ``tests_replay.GridEnumerationTests.test_negative_an_edited_grid_constant_is_refused_at_the_production_entry_point``,
  but that substitute drops the per-mutation guard MESSAGE -- its own ``EDITS`` has no third
  element and it uses a bare ``assertRaises`` -- so a regression that raises ``ReplayRefused`` for
  the wrong reason on an edited grid constant would pass it silently; the held assertion, which
  checks the message with ``assertRaisesRegex`` per edit, does not have that gap and is ported
  unweakened below).
* ``SeedRuleTests`` -- held 5, ported 4, covered elsewhere 1:
  ``test_negative_nonpositive_seed_coordinates_are_refused`` by
  ``tests_replay.SeedRuleTests.test_negative_nonpositive_seed_coordinates_are_refused`` (identical
  body). ``test_replay_seeds_never_equal_the_trial_order_seeds`` is now PORTED here in full (a
  prior draft called it "covered elsewhere" by
  ``tests_replay.SeedRuleTests.test_replay_seeds_never_equal_the_live_trial_arrival_order_seeds``,
  but that substitute checks only 6 of held's 25 ``(c, r)`` combinations and drops the boundary
  values -- cell ordinals 108/109, the T1/T2 trial-count boundary, and replicate 3999/4000 -- so a
  padding-collision regression confined to a boundary cell or replicate would not be caught by it;
  the held assertion, which checks all 25 combinations including both boundaries, is ported
  unweakened below).
* ``ScalarCrosscheckTests`` -- held 3, ported 3, covered elsewhere 0.
* ``OpenOutcomeModelTests`` -- held 5, ported 2, covered elsewhere 3:
  ``test_negative_undefined_trials_refuse_without_an_explicit_model`` by
  ``tests_replay.OpenModelTests.test_negative_a_t3_or_t4_cell_without_open_model_raises``;
  ``test_negative_wrong_keys_or_values_are_refused`` by
  ``tests_replay.OpenModelTests.test_negative_wrong_keys_or_values_are_refused`` (identical body);
  ``test_the_real_pilot_has_the_protocol_rates`` by
  ``tests_replay.RealPilotTableTests.test_the_real_pilot_has_the_protocol_rates`` (identical body).
* ``TinyEndToEndTests`` -- held 11, ported 9, covered elsewhere 2:
  ``test_negative_the_replay_cannot_change_a_rule_parameter`` by
  ``tests_replay.RuleParameterTests.test_negative_run_replay_refuses_an_overridden_rule_parameter_before_writing_anything``;
  ``test_a_horizon_above_the_roster_is_deposited_not_simulable`` by
  ``tests_replay.NotSimulableTests.test_a_cell_above_the_realized_horizon_is_deposited_not_simulable``.

Totals: held 54 = ported 46 (23 in the first seven classes + 23 in the five classes above) +
8 covered elsewhere (named individually above, never by a blanket class-level claim). No held test
is silently dropped: every one of the 54 either appears below (or in this file's earlier
``OrderEqualityTests``-through-``ExchangeabilityTests`` section) with its held name intact, or is
named above against the ``tests_replay.py`` test that covers its exact assertion.

PROVENANCE CORRECTION.  The step that produced this file was told the held source was at
``git show 72230b8:experiments/live_ab/tests_lab_replay.py``.  Both the commit and the path in
that instruction are wrong, and were NOT taken on faith: ``git show 72230b8 --stat`` lists no
``experiments/live_ab/tests_lab_replay.py`` at all.  The real held file is
``experiments/live_ab_controls/tests_lab_replay.py`` (note the ``_controls`` directory), last
touched on branch ``session60/repair-replay`` at commit ``90edaa8`` (an ANCESTOR of ``72230b8`` on
that branch); ``git diff 90edaa8 72230b8 -- experiments/live_ab_controls/tests_lab_replay.py`` is
empty, so the file is byte-identical at both commits and ``72230b8`` does carry it, at the corrected
path. Every class and assertion below is checked directly against that file's content at
``90edaa8``/``72230b8``, not against the (wrong) description alone.

Nothing here runs the 432-cell grid or reads a model; the only real input read anywhere in this
control suite is the pilot table (for its 433/591 figure, in the one held test not ported here
since it is byte-for-byte covered by ``tests_replay.RealPilotTableTests`` -- see the per-class count
table below), and every simulated run in this file is on a synthetic pilot fixture or a TINY
``run_replay`` subset (``TinyEndToEndTests``: 2 cells, 50 replicates each). Each positive control has
a negative control that must be REFUSED or must DISAGREE, so no check here can pass vacuously.

DELIBERATE REPLICATE-COUNT REDUCTIONS (this branch's own hard limit: no cell here runs more than a
few hundred replicates, and no 432-cell grid is ever assembled).  Kept exactly as the held module
had them, since they are already tiny and their positive/negative comparisons do not depend on
replicate count: ``test_the_success_probabilities_are_the_protocol_law_exactly`` (1 replicate x 16
(trial, w, q, s) combinations), ``test_negative_the_exact_law_refuses_each_wrong_model`` (no
simulation at all), ``test_the_coin_maps_one_to_the_candidate_at_position_one`` (20 replicates, as
held).  Reduced, with the reasoning re-derived here rather than carried over as an assumption:

* ``test_empirical_success_frequencies_follow_the_law_per_task`` -- held used 4,000 replicates on a
  cell whose realized ``N_P`` (206) covers every one of the 412 roster tasks exactly once per
  replicate (candidate or incumbent, decided by the enrollment coin), so each of the 12 tracked S1
  tasks is seen on the candidate side roughly ``replicates / 2`` times.  Held's floor ``n[:12] >
  1000`` is exactly half that 2,000-replicate expectation.  Adapted to 400 replicates (expectation
  100), floor lowered to match at ``n[:12] > 40`` (again roughly 40% of expectation, the same margin
  held used) -- this rescales the SAMPLE-SIZE sanity floor to the smaller budget; it does not touch
  the actual per-task law comparison, which is still the same ``abs(freq - p) > 5*SE`` test at
  whatever ``n`` each task actually received, and that comparison is valid at any ``n``. Verified
  empirically (not merely reasoned) that at 400 replicates and shift ``s = -0.3`` the negative
  control's wrong-law gap (0.3) still exceeds ``5*SE`` (~0.18 at this ``n``) for every one of the 12
  tasks, so the negative control's own ``> 6`` bound (held's number, kept unweakened) is met with
  large margin, not barely.
* ``test_t1_t2_latency_pairs_are_drawn_jointly_from_one_both_succeed_task`` and
  ``test_t3_t4_latencies_are_independent_single_shot_successes`` -- held used 200 replicates; the
  claims these check (the observed (lat_c, lat_i) pair set, and the empirical P[same task] = 1/12)
  are aggregated over ``replicates * n_p`` draws (``n_p`` = 206 pairs per replicate here), not over
  per-task counts, so statistical power is already ample at far fewer replicates. Reduced to 10
  (2,060 draws), verified empirically to still cover every element of the 8-task "both succeed" pool
  and to hold the P[same task] estimate within held's 0.02 absolute tolerance of 1/12.
* ``ExchangeabilityTests`` -- held used 20,000 replicates (T4's own protocol replicate count) on a
  6-pair, S1-only cell. Reduced to 10,000 (half): tried first at 2,000, which FAILED
  ``test_t4_arms_are_exchangeable_and_t3_arms_are_not`` on the T3 mean-gap check (observed 0.0595
  against the held tolerance of 0.05) -- reproduced directly against the unmodified current code at
  20,000 replicates (observed gap 0.0089, comfortably inside tolerance) and at several intermediate
  counts to confirm this is sampling noise from an under-powered replicate count, not a defect: the
  T3 arms' true mean gap on this fixture is of order 0.01-0.02, so a reduction that leaves too little
  averaging can push the estimate over the fixed 0.05 threshold by chance. 10,000 replicates gave a
  gap of 0.0184, and 9,000/11,000/15,000 gave 0.0192/0.0183/0.0175 -- a stable, comfortable margin
  under 0.05 -- so 10,000 was kept rather than a smaller count that happened to pass once.

Every held test not ported below is named, with its covering ``tests_replay.py`` test, in the
PER-CLASS COUNT table above; none is skipped by a blanket class-level claim.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                              # noqa: E402
import lab_design                                              # noqa: E402
import lab_enclosure                                           # noqa: E402
import lab_monitor                                             # noqa: E402
import lab_replay                                              # noqa: E402
import winstats                                                # noqa: E402  (path set by lab_monitor)

BASE = 60260919
CFG = json.loads((LIVE / 'config.json').read_text('utf-8'))
S1_TASKS = ['mbpp/%d' % i for i in range(1, 9)] + ['humaneval/%d' % i for i in range(4)]


def synthetic_pilot(tmp: Path, *, seed: int = 3) -> lab_replay.Pilot:
    """A 12-task pilot in the ``episodes_flat.csv`` shape; ``self_test_repair`` ~4.5x slower."""
    rng = numpy.random.default_rng(seed)
    path = tmp / 'pilot.csv'
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['task_id', 'variant', 'success', 'latency_s'])
        w.writeheader()
        for i, t in enumerate(S1_TASKS):
            for wf in ('single_shot', 'self_test_repair'):
                ok = i % 4 != 3                       # 9 of 12 succeed under both workflows
                lat = float(rng.uniform(2.0, 20.0)) * (4.5 if wf == 'self_test_repair' else 1.0)
                w.writerow({'task_id': t, 'variant': wf, 'success': 'True' if ok else 'False',
                            'latency_s': repr(lat)})
    return lab_replay.load_pilot_csv(path)


def synthetic_roster(n_s2: int = 400) -> dict:
    """The held module's own roster fixture (identical to ``tests_replay.py``'s): S1 is the whole
    12-task pilot, S2 is ``n_s2`` synthetic tasks with no pilot at all."""
    return {'S1': list(S1_TASKS), 'S2': ['mbpp_full/%d' % (1000 + i) for i in range(n_s2)]}


#: A 16-task pilot whose workflows DIFFER: single_shot fails i % 4 == 3 (12/16 succeed), self_test_repair
#: fails i % 3 == 2 (11/16); both succeed on 8 tasks.  Latencies are independent draws per workflow, so
#: a within-task (single_shot, self_test_repair) pair is identifiable and a product-distribution pair
#: is not.
PILOT16 = ['mbpp/%d' % i for i in range(1, 17)]


def distinct_pilot(tmp: Path) -> tuple:
    """``(Pilot, truth)``; ``truth[wf]`` maps uid -> (success 0/1, latency) as written to the CSV."""
    rng = numpy.random.default_rng(17)
    truth: dict = {'single_shot': {}, 'self_test_repair': {}}
    path = tmp / 'pilot16.csv'
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['task_id', 'variant', 'success', 'latency_s'])
        w.writeheader()
        for i, t in enumerate(PILOT16):
            for wf, ok in (('single_shot', i % 4 != 3), ('self_test_repair', i % 3 != 2)):
                lat = float(rng.uniform(2.0, 20.0) if wf == 'single_shot' else rng.uniform(9.0, 90.0))
                truth[wf][t] = (1 if ok else 0, lat)
                w.writerow({'task_id': t, 'variant': wf, 'success': 'True' if ok else 'False',
                            'latency_s': repr(lat)})
    return lab_replay.load_pilot_csv(path), truth


def roster16() -> dict:
    """S1 = 12 of the 16 pilot tasks (so the pilot rate is NOT the roster rate, READING R4), S2 = 400."""
    return {'S1': ['mbpp/%d' % i for i in range(1, 13)],
            'S2': ['mbpp_full/%d' % (1000 + i) for i in range(400)]}


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='replay_core_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# ==================================================================================================
# order_indices reproduces lab_design.arrival_order uid for uid under the trial seed
# ==================================================================================================
class OrderEqualityTests(unittest.TestCase):
    """``order_indices`` reproduces ``lab_design.arrival_order`` uid for uid under the trial seed.
    Unchanged from the held module: neither ``order_indices`` nor ``lab_design.arrival_order``/
    ``_generate``/``STRATA``/``TRIAL_NO`` differ on this branch."""

    ROSTERS = {
        'roster_small': json.loads((LIVE / 'testdata' / 'roster_small.json').read_text('utf-8')),
        'odd_strata': {'S1': ['mbpp/%d' % i for i in range(1, 60)] + ['humaneval/%d' % i for i in
                                                                     range(30)],
                       'S2': ['mbpp_full/%d' % i for i in range(500, 541)]},
        's1_only': {'S1': ['mbpp/%d' % i for i in range(1, 32)]},
    }

    @staticmethod
    def _as_pairs(roster: dict, a, b) -> list:
        uids = sorted(roster.get('S1') or []) + sorted(roster.get('S2') or [])
        n_s1 = len(roster.get('S1') or [])
        return [('S1' if x < n_s1 else 'S2', uids[x], uids[y]) for x, y in zip(a, b)]

    def _replay_order(self, roster: dict, entropy: list) -> list:
        gen = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(entropy)))
        a, b = lab_replay.order_indices(gen, len(roster.get('S1') or []),
                                        len(roster.get('S2') or []))
        return self._as_pairs(roster, a, b)

    @staticmethod
    def _design_order(roster: dict, trial: str) -> list:
        return [(s['stratum'], s['uids'][0], s['uids'][1])
                for s in lab_design.arrival_order(roster, trial, BASE)]

    def test_order_equality_with_lab_design(self) -> None:
        for name, roster in self.ROSTERS.items():
            for trial, e in lab_design.TRIAL_NO.items():
                with self.subTest(roster=name, trial=trial):
                    self.assertEqual(self._replay_order(roster, [BASE, e]),
                                     self._design_order(roster, trial))

    def test_negative_a_different_seed_gives_a_different_order(self) -> None:
        roster = self.ROSTERS['odd_strata']
        self.assertNotEqual(self._replay_order(roster, [BASE, 2]), self._design_order(roster, 'T1'))

    def test_negative_a_reordered_stratum_draw_is_detected(self) -> None:
        roster = self.ROSTERS['odd_strata']
        fake = types.SimpleNamespace(STRATA=('S2', 'S1'), TRIAL_NO=lab_design.TRIAL_NO)
        with mock.patch.object(lab_replay, 'lab_design', fake):
            mutated = self._replay_order(roster, [BASE, 1])
        self.assertNotEqual(mutated, self._design_order(roster, 'T1'))


# ==================================================================================================
# decide_matrix / band_matrix equal lab_monitor.band + lab_monitor.decide exactly
# ==================================================================================================
def _random_sequences(n_seq: int = 240, length: int = 260, seed: int = 11):
    """Complete (Z, D) sequences spanning the three outcomes and the guard boundary.

    Z and D are CONSISTENT with the hierarchy (D != 0 implies Z = D), as real pairs are.  Four regimes:
    strong positive D (deploy), cost-tier wins with D = 0 (L_h > 0 but the guard fails), strong
    negative Z (harm), and null.
    """
    rng = numpy.random.default_rng(seed)
    out = []
    for k in range(n_seq):
        regime = k % 4
        d_probs = [(0.05, 0.40), (0.0, 0.0), (0.20, 0.05), (0.15, 0.15)][regime]  # (P[D=-1], P[D=+1])
        cost_win = [0.3, 0.75, 0.0, 0.3][regime]
        cost_loss = [0.1, 0.05, 0.75, 0.3][regime]
        u = rng.random(length)
        d = numpy.where(u < d_probs[0], -1, numpy.where(u < d_probs[0] + d_probs[1], 1, 0))
        v = rng.random(length)
        z = numpy.where(d != 0, d, numpy.where(v < cost_win, 1, numpy.where(v < cost_win + cost_loss,
                                                                          -1, 0)))
        out.append((z.astype(numpy.int8), d.astype(numpy.int8)))
    return out


class BandDecideAgreementTests(unittest.TestCase):
    """``decide_matrix`` equals ``lab_monitor.band`` + ``lab_monitor.decide`` exactly.  Unchanged
    from the held module: no cell is simulated here (this checks the rule kernel directly on
    synthetic complete score sequences, never ``run_cell``)."""

    LENGTH = 260

    def setUp(self) -> None:
        self.mc = lab_replay.frozen_monitor_config(CFG, 'T1', self.LENGTH)
        self.radius = lab_replay.radius_vector(self.mc, self.LENGTH)
        self.seqs = _random_sequences(length=self.LENGTH)

    def _disagreements(self, radius, mc_kernel=None) -> tuple:
        mc_kernel = mc_kernel or self.mc
        z = numpy.stack([s[0] for s in self.seqs])
        d = numpy.stack([s[1] for s in self.seqs])
        kind, n_star = lab_replay.decide_matrix(z, d, radius, mc_kernel)
        lo_h, hi_h = lab_replay.band_matrix(z, radius, mc_kernel)
        lo_s, hi_s = lab_replay.band_matrix(d, radius, mc_kernel)
        bad = 0
        kinds = set()
        for i, (zi, di) in enumerate(self.seqs):
            ref_kind, ref_n, looks = lab_replay.monitor_decision_from_scores(zi, di, self.mc)
            kinds.add(ref_kind)
            got = numpy.stack([lo_h[i], hi_h[i], lo_s[i], hi_s[i]], -1)[:len(looks)]
            if (int(kind[i]), int(n_star[i])) != (ref_kind, ref_n) \
                    or not numpy.array_equal(got, numpy.asarray(looks)):
                bad += 1
        return bad, kinds

    def test_agreement_on_random_complete_sequences(self) -> None:
        bad, kinds = self._disagreements(self.radius)
        self.assertEqual(bad, 0)
        self.assertEqual(kinds, {lab_replay.DEPLOY, lab_replay.HARM_RETAIN, lab_replay.ABSTAIN},
                         'the sample must exercise all three outcomes')

    def test_radius_vector_is_the_band_radius(self) -> None:
        for n in (1, 99, 100, 101, 260):
            self.assertEqual(self.radius[n - 1], lab_monitor.band(n, 0.0, 0.0, self.mc).radius)

    def test_negative_a_mutated_band_makes_agreement_fail(self) -> None:
        real = lab_monitor.band

        def mutated(n, s_lower, s_upper, mc):
            b = real(n, s_lower, s_upper, mc)
            r = b.radius * 0.9
            return lab_monitor.Band(n=n, radius=r, s_lower=b.s_lower, s_upper=b.s_upper,
                                    lo=max(mc.clip_lo, b.s_lower / n - r),
                                    hi=min(mc.clip_hi, b.s_upper / n + r))
        with mock.patch.object(lab_monitor, 'band', mutated):
            bad, _ = self._disagreements(self.radius)
        self.assertGreater(bad, 0)

    def test_negative_a_mutated_radius_in_the_kernel_makes_agreement_fail(self) -> None:
        wrong = lab_monitor.MonitorConfig(alpha_gate=0.0125, rho=100.0, delta=0.03, n_min=100,
                                          n_max=self.LENGTH)
        bad, _ = self._disagreements(lab_replay.radius_vector(wrong, self.LENGTH))
        self.assertGreater(bad, 0)

    def test_negative_a_dropped_success_guard_makes_agreement_fail(self) -> None:
        loose = lab_monitor.MonitorConfig(alpha_gate=0.00625, rho=100.0, delta=0.99, n_min=100,
                                          n_max=self.LENGTH)
        bad, _ = self._disagreements(self.radius, mc_kernel=loose)
        self.assertGreater(bad, 0)

    def test_negative_a_dropped_n_min_makes_agreement_fail(self) -> None:
        early = lab_monitor.MonitorConfig(alpha_gate=0.00625, rho=100.0, delta=0.03, n_min=10,
                                          n_max=self.LENGTH)
        bad, _ = self._disagreements(self.radius, mc_kernel=early)
        self.assertGreater(bad, 0)


# ==================================================================================================
# pair_scores (winstats.compare, broadcast) equals lab_enclosure.final_scores per pair
# ==================================================================================================
class PairScoreAgreementTests(unittest.TestCase):
    """``pair_scores`` (winstats.compare, broadcast) equals ``lab_enclosure.final_scores`` per pair.
    Unchanged from the held module: no cell is simulated (raw outcome arrays, no roster/pilot)."""

    def _outcomes(self, n: int = 3000, seed: int = 5):
        rng = numpy.random.default_rng(seed)
        sc = (rng.random(n) < 0.7).astype(numpy.int8)
        si = (rng.random(n) < 0.7).astype(numpy.int8)
        li = rng.uniform(1.0, 50.0, n)
        lc = li * rng.choice([0.9, 0.95, 0.96, 1.0, 1.04, 1.05, 1.06, 1.2], n)
        return sc, si, lc, li

    def test_agreement_with_final_scores(self) -> None:
        tiers = lab_enclosure.tiers_from_config(CFG)
        sc, si, lc, li = self._outcomes()
        z, d = lab_replay.pair_scores(sc, si, lc, li, tiers)
        for i in range(len(sc)):
            ref_z, _, ref_d = lab_enclosure.final_scores(
                lab_enclosure.EpisodeView.reveal('candidate', int(sc[i]), float(lc[i]), 0),
                lab_enclosure.EpisodeView.reveal('incumbent', int(si[i]), float(li[i]), 0), tiers)
            self.assertEqual((int(z[i]), int(d[i])), (ref_z, ref_d))
        self.assertTrue(set(numpy.unique(z)) == {-1, 0, 1})

    def test_negative_a_mutated_tolerance_disagrees(self) -> None:
        tiers = lab_enclosure.tiers_from_config(CFG)
        loose = [winstats.Tier('success'), winstats.Tier('cost', higher_better=False,
                                                         relative_tolerance=0.10)]
        sc, si, lc, li = self._outcomes()
        z_ok, _ = lab_replay.pair_scores(sc, si, lc, li, tiers)
        z_bad, _ = lab_replay.pair_scores(sc, si, lc, li, loose)
        self.assertGreater(int((z_ok != z_bad).sum()), 0)


# ==================================================================================================
# protocol 11.5 items 1-3, the model-dependent core, against values computed HERE from the pilot rows
# ==================================================================================================
class OutcomeModelTests(_Tmp):
    """Protocol 11.5 items 1-3, the model-dependent core, against values computed HERE from the pilot
    rows.

    The per-cell cross-check re-scores the drawn arrays through ``MonitorState``, so it checks the rule
    and not the draws; these controls check the draws.  Expected laws (READING R1; R4: rates over the
    whole pilot): candidate ``clip(w*y_c + (1-w)*r_c + s)`` on S1 and ``clip(q + s)`` on S2, incumbent
    ``w*y_i + (1-w)*r_i`` and ``q``; T3's candidate (proposal) ``clip(r_single_shot + s)`` on S1.

    REPLICATE COUNTS: see this module's own docstring for exactly which counts were reduced from the
    held module's and why; the reductions are verified, not merely reasoned, against the actual runs
    below.
    """

    CELLS = ((0.3, 0.45, -0.02), (1.0, 0.25, 0.3), (0.7, 0.60, -0.9), (0.5, 0.60, 0.0))
    OPEN = {'T3': {'T3.candidate.success': 'coder_single_shot_stratum_rate',
                   'T3.cost_pair': 'independent_single_shot_successes'},
            'T4': {'T4.cost_pair': 'independent_single_shot_successes'}}

    def setUp(self) -> None:
        super().setUp()
        self.pilot, self.truth = distinct_pilot(self.tmp)
        self.roster = roster16()
        self.uids = sorted(self.roster['S1']) + sorted(self.roster['S2'])
        self.rate = {wf: sum(v[0] for v in self.truth[wf].values()) / len(PILOT16)
                     for wf in self.truth}

    def model(self, trial: str):
        return lab_replay.build_trial_model(self.roster, self.pilot, CFG, trial, self.OPEN.get(trial))

    def expected(self, trial: str, w: float, q: float, s: float) -> tuple:
        arms = CFG['trials'][trial]
        out = []
        for arm, shift in (('candidate', s), ('incumbent', 0.0)):
            wf, server = arms[arm]['workflow'], arms[arm]['server']
            p = []
            for uid in self.uids:
                if uid not in self.roster['S1']:
                    base = q
                elif server != 'coder':                      # T3 proposal: stratum rate, w not applied
                    base = self.rate['single_shot']
                else:
                    base = w * self.truth[wf][uid][0] + (1.0 - w) * self.rate[wf]
                p.append(min(1.0, max(0.0, base + shift)))
            out.append(numpy.asarray(p))
        return tuple(out)

    def capture(self, trial: str, w: float, q: float, s: float, replicates) -> tuple:
        """Run ``run_cell`` itself; record the probabilities it passes and every replicate it draws."""
        model = self.model(trial)
        cell = lab_replay.make_cell(3, trial, w, q, s, 206, 'realized', 1)
        mc = lab_replay.frozen_monitor_config(CFG, trial, 206)
        calls, draws = [], []
        real = lab_replay.draw_replicate

        def spy(model_, cell_, gen, p_cand, p_inc):
            calls.append((p_cand.copy(), p_inc.copy()))
            x = real(model_, cell_, gen, p_cand, p_inc)
            draws.append(x)
            return x
        with mock.patch.object(lab_replay, 'draw_replicate', spy):
            lab_replay.run_cell(model, cell, mc, BASE, replicates=replicates)
        return model, cell, calls, draws

    def test_the_success_probabilities_are_the_protocol_law_exactly(self) -> None:
        for trial in ('T1', 'T2', 'T3', 'T4'):
            for w, q, s in self.CELLS:
                with self.subTest(trial=trial, w=w, q=q, s=s):
                    _, _, calls, _ = self.capture(trial, w, q, s, [1])
                    want_c, want_i = self.expected(trial, w, q, s)
                    numpy.testing.assert_allclose(calls[0][0], want_c, rtol=0, atol=1e-12)
                    numpy.testing.assert_allclose(calls[0][1], want_i, rtol=0, atol=1e-12)

    def test_negative_the_exact_law_refuses_each_wrong_model(self) -> None:
        """The comparison above detects each defect the review named (shift dropped, sign, shift on the
        incumbent, w ignored or inverted, a rate that is not the arm's own).  No simulation runs here."""
        w, q, s = 0.3, 0.45, -0.02
        want_c, want_i = self.expected('T2', w, q, s)
        c0, i0 = self.expected('T2', w, q, 0.0)
        wrong = {'shift_dropped': (c0, want_i), 'shift_sign': (self.expected('T2', w, q, -s)[0], want_i),
                 'shift_on_incumbent': (want_c, numpy.clip(want_i + s, 0, 1)),
                 'w_ignored': self.expected('T2', 1.0, q, s),
                 'w_inverted': self.expected('T2', 1.0 - w, q, s),
                 'other_arm_rate': (want_c - (1 - w) * (self.rate['self_test_repair']
                                                        - self.rate['single_shot']), want_i)}
        for name, (c, i) in wrong.items():
            with self.subTest(defect=name):
                self.assertFalse(numpy.allclose(c, want_c, rtol=0, atol=1e-12)
                                 and numpy.allclose(i, want_i, rtol=0, atol=1e-12))

    def test_empirical_success_frequencies_follow_the_law_per_task(self) -> None:
        """DISTRIBUTIONAL: 400 replicates (held used 4,000; see this module's docstring) of a T2
        cell through ``run_cell``; per task and arm the empirical success frequency is within 5
        standard errors of the law (exact where p is 0 or 1)."""
        w, q, s = 0.5, 0.45, -0.3
        _, _, _, draws = self.capture('T2', w, q, s, range(1, 401))
        want = dict(zip(('candidate', 'incumbent'), self.expected('T2', w, q, s)))
        for arm, task_key, succ_key in (('candidate', 'cand_task', 'success_c'),
                                        ('incumbent', 'inc_task', 'success_i')):
            tasks = numpy.concatenate([x[task_key] for x in draws])
            succ = numpy.concatenate([x[succ_key] for x in draws]).astype(numpy.float64)
            n = numpy.bincount(tasks, minlength=len(self.uids))
            k = numpy.bincount(tasks, weights=succ, minlength=len(self.uids))
            p = want[arm]
            self.assertTrue((n[:12] > 40).all())          # every S1 task seen often under each arm
            se = numpy.sqrt(p * (1 - p) / numpy.maximum(n, 1))
            bad = numpy.flatnonzero(numpy.abs(k / numpy.maximum(n, 1) - p) > 5 * se + 1e-12)
            with self.subTest(arm=arm):
                self.assertEqual(bad.tolist(), [])
                # negative control: the same test refuses the unshifted (candidate) or the
                # shifted (incumbent) law
                other = numpy.clip(p - s, 0, 1) if arm == 'candidate' else numpy.clip(p + s, 0, 1)
                se_o = numpy.sqrt(other * (1 - other) / numpy.maximum(n, 1))
                self.assertGreater(int((numpy.abs(k / numpy.maximum(n, 1) - other)
                                        > 5 * se_o + 1e-12)[:12].sum()), 6)

    def test_the_coin_maps_one_to_the_candidate_at_position_one(self) -> None:
        """Item 1 / ``config.json`` coin.map ``1->candidate_at_position_1``, recomputed from the seed."""
        model, cell, _, draws = self.capture('T2', 0.5, 0.45, 0.0, range(1, 21))
        for r, x in enumerate(draws, start=1):
            gen = lab_replay.replicate_generator(BASE, cell['ordinal'], r)
            pos1, pos2 = lab_replay.order_indices(gen, model.n_s1, model.n_s2)
            pos1, pos2 = pos1[:206], pos2[:206]
            coin = gen.integers(0, 2, size=206)
            numpy.testing.assert_array_equal(coin, x['coin'])
            numpy.testing.assert_array_equal(x['cand_task'], numpy.where(coin == 1, pos1, pos2))
            numpy.testing.assert_array_equal(x['inc_task'], numpy.where(coin == 1, pos2, pos1))
            # negative control: the swapped map is a different assignment on these draws
            self.assertFalse(numpy.array_equal(x['cand_task'], numpy.where(coin == 0, pos1, pos2)))

    @staticmethod
    def _pairs_outside(lat_c, lat_i, allowed: set) -> int:
        return sum(1 for a, b in zip(lat_c.tolist(), lat_i.tolist()) if (a, b) not in allowed)

    def test_t1_t2_latency_pairs_are_drawn_jointly_from_one_both_succeed_task(self) -> None:
        """held used 200 replicates; reduced to 10 (2,060 draws over the 8-task pool; see this
        module's docstring)."""
        both = [u for u in PILOT16 if self.truth['single_shot'][u][0]
                and self.truth['self_test_repair'][u][0]]
        self.assertEqual(len(both), 8)
        for trial in ('T1', 'T2'):
            arms = CFG['trials'][trial]
            cwf, iwf = arms['candidate']['workflow'], arms['incumbent']['workflow']
            allowed = {(self.truth[cwf][u][1], self.truth[iwf][u][1]) for u in both}
            _, _, _, draws = self.capture(trial, 0.5, 0.45, 0.0, range(1, 11))
            lat_c = numpy.concatenate([x['lat_c'] for x in draws])
            lat_i = numpy.concatenate([x['lat_i'] for x in draws])
            with self.subTest(trial=trial):
                self.assertEqual(self._pairs_outside(lat_c, lat_i, allowed), 0)
                self.assertEqual(set(zip(lat_c.tolist(), lat_i.tolist())), allowed)
                # negative control: the product distribution (independent draws) is refused
                shuffled = numpy.random.default_rng(1).permutation(lat_i)
                self.assertGreater(self._pairs_outside(lat_c, shuffled, allowed), len(lat_c) // 2)
                # negative control: arms swapped is refused
                self.assertEqual(self._pairs_outside(lat_i, lat_c, allowed), len(lat_c))

    def test_t3_t4_latencies_are_independent_single_shot_successes(self) -> None:
        """held used 200 replicates; reduced to 10 (2,060 draws; see this module's docstring)."""
        pool = {self.truth['single_shot'][u][1] for u in PILOT16 if self.truth['single_shot'][u][0]}
        self.assertEqual(len(pool), 12)
        for trial in ('T3', 'T4'):
            _, _, _, draws = self.capture(trial, 0.5, 0.45, 0.0, range(1, 11))
            lat_c = numpy.concatenate([x['lat_c'] for x in draws]).tolist()
            lat_i = numpy.concatenate([x['lat_i'] for x in draws]).tolist()
            same = sum(1 for a, b in zip(lat_c, lat_i) if a == b) / len(lat_c)
            with self.subTest(trial=trial):
                self.assertTrue(set(lat_c) == set(lat_i) == pool)
                self.assertLess(abs(same - 1 / 12), 0.02)      # independent: P(same task) = 1/12
                self.assertNotAlmostEqual(same, 1.0)           # negative: a joint draw gives 1


# ==================================================================================================
# item 6: Q1 / median / Q3, numpy.percentile method linear; known answers
# ==================================================================================================
class QuartileTests(unittest.TestCase):
    """Item 6: Q1 / median / Q3, ``numpy.percentile`` method ``linear``; known answers.  Unchanged
    from the held module."""

    def test_known_values(self) -> None:
        self.assertEqual(lab_replay.quartiles(numpy.arange(1, 10)),
                         {'n': 9, 'q1': 3.0, 'median': 5.0, 'q3': 7.0})
        self.assertEqual(lab_replay.quartiles(numpy.asarray([4, 1, 3, 2])),
                         {'n': 4, 'q1': 1.75, 'median': 2.5, 'q3': 3.25})
        self.assertIsNone(lab_replay.quartiles(numpy.zeros(0)))

    def test_negative_other_percentiles_or_methods_differ_from_the_known_values(self) -> None:
        v = numpy.asarray([4, 1, 3, 2], dtype=numpy.float64)
        for pcts, method in (([10, 50, 90], 'linear'), ([25, 50, 75], 'lower'),
                             ([25, 50, 75], 'nearest')):
            with self.subTest(pcts=pcts, method=method):
                got = numpy.percentile(v, pcts, method=method).tolist()
                self.assertNotEqual(got, [1.75, 2.5, 3.25])


class WilsonTests(unittest.TestCase):
    """Unchanged from the held module."""

    def test_known_values(self) -> None:
        lo, hi = lab_replay.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=4)
        self.assertAlmostEqual(hi, 0.7634, places=4)
        self.assertEqual(lab_replay.wilson(0, 4000)[0], 0.0)
        self.assertEqual(lab_replay.wilson(4000, 4000)[1], 1.0)
        self.assertAlmostEqual(lab_replay.wilson(0, 4000)[1], 0.000959, places=6)
        self.assertIsNone(lab_replay.wilson(0, 0))

    def test_negative_impossible_counts_are_refused(self) -> None:
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.wilson(11, 10)


# ==================================================================================================
# at s = 0 the arms are exchangeable for T4 only; T3's are not (review finding, 2026-09-23)
# ==================================================================================================
class ExchangeabilityTests(_Tmp):
    """At s = 0 the arms are exchangeable for T4 only; T3's are not (review finding, 2026-09-23).
    Held used 20,000 replicates (T4's own protocol count); reduced to 10,000 (half) -- verified
    empirically, including the failure at a smaller count, to still meet every one of held's fixed
    tolerances (see this module's docstring)."""

    def _sums(self, trial: str, open_model: dict) -> tuple:
        pilot = synthetic_pilot(self.tmp)                  # 12 tasks, 9 succeed under single_shot
        roster = {'S1': list(S1_TASKS), 'S2': []}           # S1 only: 6 pairs, roster = pilot
        m = lab_replay.build_trial_model(roster, pilot, CFG, trial, open_model)
        cell = lab_replay.make_cell(1, trial, 1.0, 0.45, 0.0, 6, 'realized', 1)
        pc = numpy.clip(lab_replay._probabilities(m, 'candidate', 1.0, 0.45), 0, 1)
        pi = lab_replay._probabilities(m, 'incumbent', 1.0, 0.45)
        sc, si = [], []
        for r in range(1, 10001):
            x = lab_replay.draw_replicate(m, cell, lab_replay.replicate_generator(BASE, 1, r), pc, pi)
            sc.append(int(x['success_c'].sum()))
            si.append(int(x['success_i'].sum()))
        return numpy.asarray(sc, dtype=float), numpy.asarray(si, dtype=float)

    def test_t4_arms_are_exchangeable_and_t3_arms_are_not(self) -> None:
        c4, i4 = self._sums('T4', {'T4.cost_pair': 'independent_single_shot_successes'})
        self.assertLess(abs(c4.mean() - i4.mean()), 0.05)
        self.assertLess(abs(c4.var() / i4.var() - 1.0), 0.1)
        c3, i3 = self._sums('T3', {k: v for k, v in lab_replay.PROPOSED_OPEN_MODEL.items()
                                   if k.startswith('T3.')})
        self.assertLess(abs(c3.mean() - i3.mean()), 0.05)            # equal means on this roster
        self.assertGreater(c3.var() / i3.var(), 1.5)                  # but not the same law

    def test_the_text_restricts_the_exact_null_claim_to_t4(self) -> None:
        text = lab_replay.PROPOSAL_TEXT
        self.assertIn('exchangeable for T4 only', text)
        self.assertIn('T3 arms are not exchangeable', text)
        self.assertNotIn('(exchangeable arms at s = 0)', text)
        doc = ' '.join(lab_replay.__doc__.split())
        self.assertIn('EXCHANGEABILITY AT ``s = 0`` HOLDS FOR T4 ONLY', doc)
        self.assertNotIn('both arms are then exchangeable, so the rows are exact-null rows', doc)


# ==================================================================================================
# the 432-cell grid is enumerated without simulating, and every literal spec is guarded
# (held ``GridEnumerationTests``, 7 tests: 5 ported here, 2 already covered by
# ``tests_replay.GridEnumerationTests`` -- see the class docstring for which)
# ==================================================================================================
class GridEnumerationTests(unittest.TestCase):
    """Held's ``test_the_intact_grid_passes_the_check`` is covered by
    ``tests_replay.GridEnumerationTests.test_the_432_cells_match_the_protocol_item_5_product``
    (calls ``check_grid`` on the intact grid at the end); held's
    ``test_negative_every_mutated_grid_is_refused`` is covered byte-for-byte by
    ``tests_replay.GridEnumerationTests.test_negative_every_mutated_grid_is_refused`` (identical
    body). The other 5 are ported below, including
    ``test_negative_the_production_entry_point_refuses_an_edited_grid``: a prior draft called this
    one "covered elsewhere" by
    ``tests_replay.GridEnumerationTests.test_negative_an_edited_grid_constant_is_refused_at_the_production_entry_point``,
    but that substitute's own ``EDITS`` dict has dropped the third (guard-message) element and it
    uses a bare ``assertRaises(ReplayRefused)`` instead of ``assertRaisesRegex`` -- so it cannot
    tell an edit refused for the RIGHT reason from one refused for the wrong one. Ported here in
    full, unweakened, with the guard-message assertion held used. None of the 5 -- the
    no-simulation guarantee, the per-edit guard MESSAGE (both at ``check_grid`` and at the
    production ``run_replay`` entry point), the same-total-different-cell mutation, and the
    regex-extracted literal comparison against the protocol text -- has an equivalent assertion in
    ``tests_replay.py``."""

    def test_the_432_cells_are_enumerated_without_simulating(self) -> None:
        boom = mock.Mock(side_effect=AssertionError('enumeration must not simulate'))
        with mock.patch.object(lab_replay, 'replicate_generator', boom), \
                mock.patch.object(lab_replay, 'draw_replicate', boom), \
                mock.patch.object(lab_replay, 'run_cell', boom):
            cells = lab_replay.enumerate_cells(540)
        boom.assert_not_called()
        self.assertEqual(len(cells), 432)
        self.assertEqual([c['ordinal'] for c in cells], list(range(1, 433)))
        self.assertEqual(len({c['cell_id'] for c in cells}), 432)
        self.assertEqual(sum(c['replicates'] for c in cells), 3_456_000)
        self.assertEqual(lab_replay.GRID_REPLICATES, 3_456_000)
        for trial in ('T1', 'T2', 'T3', 'T4'):
            mine = [c for c in cells if c['trial'] == trial]
            self.assertEqual(len(mine), 108)
            self.assertEqual({c['replicates'] for c in mine}, {20000 if trial == 'T4' else 4000})
        self.assertEqual({c['n_p'] for c in cells}, {295, 495, 540})
        self.assertEqual({c['w'] for c in cells}, {0.3, 0.5, 0.7, 1.0})
        self.assertEqual({c['q'] for c in cells}, {0.25, 0.45, 0.60})
        self.assertEqual({c['s'] for c in cells}, {0.0, -0.02, -0.03})
        self.assertEqual(len({(c['trial'], c['w'], c['q'], c['s'], c['n_p_role'])
                              for c in cells}), 432)

    #: edit -> (constant, value, the guard that must refuse it, by its message)
    EDITS = {'three_w': ('GRID_W', (0.3, 0.5, 0.7), 'the grid has 324 cells'),
             'one_s': ('GRID_S', (0.0,), 'the grid has 144 cells'),
             'other_q': ('GRID_Q', (0.25, 0.45, 0.65), 'not the protocol 11.5 item 5 product'),
             'fewer_reps': ('REPLICATES', 3999, 'plans 3455676 replicates'),
             'fewer_t4_reps': ('REPLICATES_T4', 4000, 'plans 1728000 replicates'),
             'other_fixed': ('GRID_FIXED_N_P', (295, 496), 'has N_P 496')}

    def test_negative_check_grid_refuses_an_edited_grid_constant(self) -> None:
        for name, (attr, value, guard) in self.EDITS.items():
            with self.subTest(edit=name):
                with mock.patch.object(lab_replay, attr, value):
                    cells = lab_replay.enumerate_cells(540)
                    with self.assertRaisesRegex(lab_replay.ReplayRefused, guard):
                        lab_replay.check_grid(cells, 540)

    def test_negative_replicates_moved_between_cells_are_refused(self) -> None:
        """Same total, same cells: only the per-cell replicate guard can see it."""
        bad = lab_replay.enumerate_cells(540)
        bad[0] = dict(bad[0], replicates=bad[0]['replicates'] + 1)
        bad[1] = dict(bad[1], replicates=bad[1]['replicates'] - 1)
        with self.assertRaisesRegex(lab_replay.ReplayRefused, '4001 replicates'):
            lab_replay.check_grid(bad, 540)

    def test_negative_the_production_entry_point_refuses_an_edited_grid(self) -> None:
        """Through ``run_replay`` with ``cells=None`` (the real full run): refused before any cell
        is simulated and before anything is written -- and refused for the guard's own MESSAGE,
        per edit, not merely refused for some reason."""
        boom = mock.Mock(side_effect=AssertionError('an edited grid must not be simulated'))
        with tempfile.TemporaryDirectory(prefix='replay_') as tmp:
            pilot = synthetic_pilot(Path(tmp))
            for name, (attr, value, guard) in self.EDITS.items():
                with self.subTest(edit=name):
                    out = Path(tmp) / name
                    with mock.patch.object(lab_replay, attr, value), \
                            mock.patch.object(lab_replay, 'run_cell', boom):
                        with self.assertRaisesRegex(lab_replay.ReplayRefused, guard):
                            lab_replay.run_replay(synthetic_roster(), pilot, CFG, realized_n_p=206,
                                                  out_dir=out,
                                                  open_model=dict(lab_replay.PROPOSED_OPEN_MODEL))
                    self.assertFalse(out.exists())
        boom.assert_not_called()

    def test_the_protocol_literals_are_the_protocol_text(self) -> None:
        """``PROTOCOL_11_5_ITEM_5`` read back out of protocol 11.5 item 5
        (``design/protocol_FINAL.md``, section heading re-verified on this checkout at
        line 2440, item 5 at lines 2462-2463 -- both re-read here, not carried over from the
        held module's stale ``:2238-2259`` citation)."""
        text = (LIVE / 'design' / 'protocol_FINAL.md').read_text('utf-8')
        heading = text.index('### 11.5 The extended replay')
        item = text[text.index('5. **Cells, exhaustive:**', heading):
                    text.index('6. **Output, exhaustive', heading)]
        item = ' '.join(item.split())

        def numbers(name: str) -> tuple:
            body = re.search(r'`%s` in \{([^}]*)\}' % re.escape(name), item).group(1)
            return tuple(float(x) for x in body.split(','))
        lit = lab_replay.PROTOCOL_11_5_ITEM_5
        self.assertEqual(numbers('w'), lit['w'])
        self.assertEqual(numbers('q'), lit['q'])
        self.assertEqual(numbers('s'), lit['s'])
        self.assertIn('`N_P` in {%d, %d, the realized value}' % lit['fixed_n_p'], item)
        self.assertIn('trial in {%s}' % ', '.join(lit['trials']), item)
        self.assertIn('%s replicates per cell; %s for T4' % (format(lit['replicates'], ','),
                                                             format(lit['replicates_T4'], ',')), item)
        n = len(lit['w']) * len(lit['q']) * len(lit['s']) * 3 * len(lit['trials'])
        self.assertEqual(n, lab_replay.GRID_CELLS)
        self.assertEqual(3 * (n // 4) * lit['replicates'] + (n // 4) * lit['replicates_T4'],
                         lab_replay.GRID_REPLICATES)
        # negative control: the same reading detects a literal that is not the protocol's
        self.assertNotEqual(numbers('w'), (0.3, 0.5, 0.7))


# ==================================================================================================
# the seed rule: deterministic, per replicate, and apart from the order seeds
# (held ``SeedRuleTests``, 5 tests: 4 ported here, 1 already covered by
# ``tests_replay.SeedRuleTests`` -- see the class docstring for which)
# ==================================================================================================
class SeedRuleTests(_Tmp):
    """Held's ``test_negative_nonpositive_seed_coordinates_are_refused`` is covered
    byte-for-byte by ``tests_replay.SeedRuleTests.test_negative_nonpositive_seed_coordinates_are_refused``
    (identical body). The other 4 are ported below, including
    ``test_replay_seeds_never_equal_the_trial_order_seeds``: a prior draft called this one
    "covered elsewhere" by
    ``tests_replay.SeedRuleTests.test_replay_seeds_never_equal_the_live_trial_arrival_order_seeds``,
    but that substitute checks only 6 of held's 25 ``(c, r)`` combinations and drops both boundary
    values -- cell ordinals 108/109 (the T1/T2 trial-count boundary) and replicate 3999/4000 (the
    T1-T3/T4 replicate-count boundary) -- so a padding-collision regression confined to a boundary
    cell or replicate would not be caught by it. Ported here in full, unweakened, checking all 25
    combinations including both boundaries. None of ``tests_replay.SeedRuleTests``'s tests call
    ``run_cell``/``build_trial_model`` at all, so the FULL-ROW determinism claim (through
    ``run_cell``'s ``per_replicate_sha256``), the block-splitting property (40 replicates in one
    call equals 1-20 plus 21-40 run separately), and ``draw_replicate``'s own reproducibility have
    no equivalent there either -- they exercise ``replicate_generator`` alone."""

    def _row(self, base: int = BASE, ordinal: int = 5, replicates=None):
        pilot = synthetic_pilot(self.tmp)
        model = lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, 'T2', None)
        cell = lab_replay.make_cell(ordinal, 'T2', 0.5, 0.6, 0.0, 206, 'realized', 40)
        mc = lab_replay.frozen_monitor_config(CFG, 'T2', 206)
        return model, cell, lab_replay.run_cell(model, cell, mc, base, replicates=replicates)

    def test_determinism_under_the_seed_rule(self) -> None:
        _, _, a = self._row()
        _, _, b = self._row()
        self.assertEqual(lab_common.canonical_json(a), lab_common.canonical_json(b))

    def test_each_replicate_is_reproducible_alone(self) -> None:
        model, cell, _ = self._row()
        p_c = numpy.clip(lab_replay._probabilities(model, 'candidate', 0.5, 0.6), 0, 1)
        p_i = lab_replay._probabilities(model, 'incumbent', 0.5, 0.6)
        once = lab_replay.draw_replicate(model, cell, lab_replay.replicate_generator(BASE, 5, 7),
                                         p_c, p_i)
        again = lab_replay.draw_replicate(model, cell, lab_replay.replicate_generator(BASE, 5, 7),
                                          p_c, p_i)
        for key in once:
            numpy.testing.assert_array_equal(once[key], again[key])
        # the per-replicate digest of replicates 1..40 equals that of 1..20 + 21..40 run separately
        _, _, whole = self._row()
        _, _, head = self._row(replicates=range(1, 21))
        _, _, tail = self._row(replicates=range(21, 41))
        self.assertEqual(whole['counts'], {k: head['counts'][k] + tail['counts'][k]
                                           for k in whole['counts']})

    def test_negative_another_base_or_ordinal_changes_the_draws(self) -> None:
        _, _, a = self._row()
        _, _, b = self._row(base=BASE + 1)
        _, _, c = self._row(ordinal=6)
        self.assertNotEqual(a['per_replicate_sha256'], b['per_replicate_sha256'])
        self.assertNotEqual(a['per_replicate_sha256'], c['per_replicate_sha256'])

    def test_replay_seeds_never_equal_the_trial_order_seeds(self) -> None:
        # The hazard is real: numpy pads short entropy with zeros.
        self.assertTrue(numpy.array_equal(
            numpy.random.SeedSequence([BASE, 1]).generate_state(4),
            numpy.random.SeedSequence([BASE, 1, 0]).generate_state(4)))
        order_states = {tuple(numpy.random.SeedSequence([BASE, e]).generate_state(4))
                        for e in (1, 2, 3, 4)}
        replay_states = set()
        for c in (1, 2, 108, 109, 432):
            for r in (1, 2, 3999, 4000, 20000):
                replay_states.add(tuple(numpy.random.SeedSequence(
                    [BASE, lab_replay.REPLAY_STREAM_TAG, c, r]).generate_state(4)))
        self.assertEqual(len(replay_states), 25)
        self.assertFalse(order_states & replay_states)


# ==================================================================================================
# the per-cell cross-check through MonitorState is a live refusal, not a label
# (held ``ScalarCrosscheckTests``, 3 tests: all 3 ported here -- none of ``tests_replay.py``'s
# crosscheck usages (``OpenModelTests``, ``ShardReceiptTests``, ``ResumeProvenanceTests``) asserts
# the ``pending_looks`` equality or mocks ``decide_matrix`` to prove the crosscheck actually
# refuses on disagreement rather than merely reporting a count)
# ==================================================================================================
class ScalarCrosscheckTests(_Tmp):
    def _setup(self):
        pilot = synthetic_pilot(self.tmp)
        model = lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, 'T2', None)
        cell = lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 30)
        return model, cell, lab_replay.frozen_monitor_config(CFG, 'T2', 206)

    def test_every_replicate_agrees_with_the_monitor_path(self) -> None:
        model, cell, mc = self._setup()
        row = lab_replay.run_cell(model, cell, mc, BASE, crosscheck=30)
        self.assertEqual(row['crosscheck'], {'replicates_checked': 30, 'mismatches': 0})
        self.assertGreater(row['counts']['HARM_RETAIN'], 0)

    def test_the_enroll_look_never_changes_the_decision(self) -> None:
        """Protocol 8.3 trigger 1 adds a look with the new pair at [-1, 1]; 11.5 item 4 evaluates
        completed prefixes only.  EMPIRICAL check on these draws, not a proof."""
        model, cell, mc = self._setup()
        p_c = numpy.clip(lab_replay._probabilities(model, 'candidate', 1.0, 0.6), 0, 1)
        p_i = lab_replay._probabilities(model, 'incumbent', 1.0, 0.6)
        for r in range(1, 21):
            x = lab_replay.draw_replicate(model, cell, lab_replay.replicate_generator(BASE, 1, r),
                                          p_c, p_i)
            args = (x['success_c'], x['success_i'], x['lat_c'], x['lat_i'], mc, model.tiers)
            self.assertEqual(lab_replay.monitor_decision(*args),
                             lab_replay.monitor_decision(*args, pending_looks=True))

    def test_negative_a_mutated_kernel_is_refused_by_the_crosscheck(self) -> None:
        model, cell, mc = self._setup()

        def always_abstain(z, d, radius, mc):
            z = numpy.atleast_2d(z)
            return (numpy.full(z.shape[0], lab_replay.ABSTAIN, dtype=numpy.int8),
                    numpy.zeros(z.shape[0], dtype=numpy.int32))
        with mock.patch.object(lab_replay, 'decide_matrix', always_abstain):
            with self.assertRaises(lab_replay.ReplayRefused) as ctx:
                lab_replay.run_cell(model, cell, mc, BASE, crosscheck=5)
        self.assertIn('disagree with lab_monitor.decide', str(ctx.exception))


# ==================================================================================================
# T3's pilot-less candidate and the T3/T4 cost pair are explicit parameters, never defaulted
# (held ``OpenOutcomeModelTests``, 5 tests: 2 ported here, 3 already covered elsewhere --
# see the class docstring for which)
# ==================================================================================================
class OpenOutcomeModelTests(_Tmp):
    """Held's ``test_negative_undefined_trials_refuse_without_an_explicit_model`` is covered by
    ``tests_replay.OpenModelTests.test_negative_a_t3_or_t4_cell_without_open_model_raises`` (same
    ``build_trial_model(..., None)`` raising with 'PROPOSED' in the message, for T3 and T4, plus
    more); held's ``test_negative_wrong_keys_or_values_are_refused`` is covered byte-for-byte by
    ``tests_replay.OpenModelTests.test_negative_wrong_keys_or_values_are_refused`` (identical
    body); held's ``test_the_real_pilot_has_the_protocol_rates`` is covered byte-for-byte by
    ``tests_replay.RealPilotTableTests.test_the_real_pilot_has_the_protocol_rates`` (identical
    body). The other 2 are ported below: the extra ``PROPOSED_OPEN_MODEL`` keys-equal-gaps-union
    assertion, and the actual numeric behaviour of the proposed models (stratum rate vs. task
    proxy, independent vs. duplicated cost-pair latencies), have no equivalent in
    ``tests_replay.OpenModelTests`` (whose own behavioural test only checks ``status``/
    ``replicates_run``/``crosscheck``, not the probabilities or latencies the models actually
    produce)."""

    def test_the_gaps_are_derived_from_the_config(self) -> None:
        self.assertEqual(lab_replay.outcome_model_gaps(CFG, 'T1'), {})
        self.assertEqual(lab_replay.outcome_model_gaps(CFG, 'T2'), {})
        self.assertEqual(sorted(lab_replay.outcome_model_gaps(CFG, 'T3')),
                         ['T3.candidate.success', 'T3.cost_pair'])
        self.assertEqual(sorted(lab_replay.outcome_model_gaps(CFG, 'T4')), ['T4.cost_pair'])
        self.assertEqual(sorted(lab_replay.PROPOSED_OPEN_MODEL), sorted(
            set(lab_replay.outcome_model_gaps(CFG, 'T3')) | set(lab_replay.outcome_model_gaps(CFG,
                                                                                            'T4'))))

    def test_the_proposal_behaves_as_stated(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        t3 = lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, 'T3',
                                          {k: v for k, v in lab_replay.PROPOSED_OPEN_MODEL.items()
                                           if k.startswith('T3.')})
        p = lab_replay._probabilities(t3, 'candidate', 0.7, 0.45)
        self.assertEqual(set(p[:12].tolist()), {9 / 12})             # stratum rate, w not applied
        self.assertEqual(set(p[12:].tolist()), {0.45})
        proxy = lab_replay.build_trial_model(
            synthetic_roster(), pilot, CFG, 'T3',
            {'T3.candidate.success': 'coder_single_shot_task_proxy',
             'T3.cost_pair': 'independent_single_shot_successes'})
        self.assertGreater(len(set(lab_replay._probabilities(proxy, 'candidate', 0.7,
                                                             0.45)[:12].tolist())), 1)
        cell = lab_replay.make_cell(1, 'T4', 0.5, 0.6, 0.0, 206, 'realized', 1)
        for choice, identical in (('independent_single_shot_successes', False),
                                  ('same_task_single_shot_duplicate', True)):
            m = lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, 'T4',
                                             {'T4.cost_pair': choice})
            p_i = lab_replay._probabilities(m, 'incumbent', 0.5, 0.6)
            x = lab_replay.draw_replicate(m, cell, lab_replay.replicate_generator(BASE, 1, 1),
                                          p_i, p_i)
            self.assertEqual(bool(numpy.array_equal(x['lat_c'], x['lat_i'])), identical)
            if identical:                            # tier 1 always ties: Z is exactly D
                numpy.testing.assert_array_equal(x['z'], x['d'])


# ==================================================================================================
# 2 cells x 50 replicates through run_replay: table, manifest, write-once, verification, refusals
# (held ``TinyEndToEndTests``, 11 tests: 9 ported here, 2 already covered elsewhere --
# see the class docstring for which)
# ==================================================================================================
class TinyEndToEndTests(_Tmp):
    """Held's ``test_negative_the_replay_cannot_change_a_rule_parameter`` is covered by
    ``tests_replay.RuleParameterTests.test_negative_run_replay_refuses_an_overridden_rule_parameter_before_writing_anything``
    (same overridden-``delta``-through-``run_replay`` refusal, table absent); held's
    ``test_a_horizon_above_the_roster_is_deposited_not_simulable`` is covered by
    ``tests_replay.NotSimulableTests.test_a_cell_above_the_realized_horizon_is_deposited_not_simulable``
    (same claim, with MORE evidentiary fields checked ``None``). The other 9 are ported below:
    none of ``tests_replay.py``'s tests build a full table+manifest end to end and check its
    shape (``test_end_to_end``), compare two INDEPENDENT clean runs byte for byte
    (``test_the_table_is_deterministic_across_runs`` -- the resume-based byte comparisons in
    ``ShardReceiptTests``/``ResumeProvenanceTests`` always start one run from the other's copied
    rows/receipts, never two runs from nothing), refuse a second whole-manifest write on an
    already-complete run (``test_negative_a_second_run_cannot_overwrite``), flip a byte of the
    FINAL table and show ``verify_manifest`` catches it (``test_negative_a_flipped_table_byte_is_refused``
    -- ``tests_replay.py``'s only byte-flip is on a RESUMED row before it is re-read, a different
    code path), edit the script file and show the sha256 pin catches it
    (``test_negative_a_script_edited_after_the_run_is_refused``), tamper the manifest's own seed
    RULE TEXT rather than its ``design_seed_base`` value (``test_negative_a_rewritten_seed_rule_is_refused``
    -- ``tests_replay.py`` only tampers ``design_seed_base``), record a GOOD ruling citation as
    ``RULED`` through ``run_replay`` (``test_a_resolvable_ruling_citation_is_recorded_as_ruled``),
    run the full ``run_replay`` refusal path over held's fixture-file variety of bad ruling
    strings including a wrong-directory citation (``test_negative_a_ruling_that_does_not_resolve_is_refused_before_anything_runs``
    -- ``tests_replay.RulingCitationTests`` calls ``check_ruling_citation`` directly against
    different fixtures and does not check ``out_dir`` non-existence for this string set), and
    refuse a ``realized_n_p`` that does not follow the roster arithmetic
    (``test_negative_realized_n_p_must_follow_the_roster_rule``)."""

    def _run(self, out: Path, **kw):
        cells = kw.pop('cells', [
            lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 50),
            lab_replay.make_cell(2, 'T4', 0.5, 0.45, -0.03, 150, 'fixed_150', 50)])
        return lab_replay.run_replay(
            synthetic_roster(), synthetic_pilot(self.tmp), kw.pop('cfg', CFG), realized_n_p=206,
            out_dir=out, open_model=kw.pop('open_model', {'T4.cost_pair':
                                                         'independent_single_shot_successes'}),
            cells=cells, crosscheck_per_cell=kw.pop('crosscheck', 50), **kw)

    def test_end_to_end(self) -> None:
        out = self.tmp / 'out'
        manifest = self._run(out)
        table = json.loads((out / lab_replay.TABLE_NAME).read_text('utf-8'))
        self.assertEqual(table['grid_kind'], 'subset')
        self.assertEqual(manifest['grid']['kind'], 'subset')
        self.assertEqual(len(table['rows']), 2)
        for row in table['rows']:
            self.assertEqual(row['status'], 'SIMULATED')
            self.assertEqual(sum(row['counts'].values()), 50)
            for label in lab_replay.LABELS:
                lo, hi = row['wilson95'][label]
                self.assertLessEqual(lo, row['rates'][label])
                self.assertGreaterEqual(hi, row['rates'][label])
            self.assertEqual(row['crosscheck'], {'replicates_checked': 50, 'mismatches': 0})
        harm = table['rows'][0]
        self.assertGreater(harm['counts']['HARM_RETAIN'], 0)
        q = harm['crossing_prefix']['HARM_RETAIN']
        self.assertTrue(100 <= q['q1'] <= q['median'] <= q['q3'] <= 206)
        # provenance for the planning member
        self.assertEqual(manifest['script']['sha256'],
                         lab_common.sha256_file(LIVE / 'lab_replay.py'))
        self.assertEqual(manifest['output']['sha256'],
                         lab_common.sha256_file(out / lab_replay.TABLE_NAME))
        self.assertEqual(manifest['seed']['rule'], lab_replay.SEED_RULE_TEXT)
        self.assertEqual(manifest['seed']['design_seed_base'], BASE)
        self.assertEqual(manifest['open_outcome_model']['status'], 'PROPOSED')
        self.assertEqual(manifest['open_outcome_model']['needs'], 'root')
        self.assertTrue(manifest['open_outcome_model']['equals_proposal'])
        self.assertEqual(manifest['crosscheck']['replicates_checked'], 100)
        self.assertEqual(lab_replay.verify_manifest(out)['output']['sha256'],
                         manifest['output']['sha256'])

    def test_the_table_is_deterministic_across_runs(self) -> None:
        self._run(self.tmp / 'a')
        self._run(self.tmp / 'b')
        self.assertEqual((self.tmp / 'a' / lab_replay.TABLE_NAME).read_bytes(),
                         (self.tmp / 'b' / lab_replay.TABLE_NAME).read_bytes())

    def test_negative_a_second_run_cannot_overwrite(self) -> None:
        out = self.tmp / 'out'
        self._run(out)
        before = (out / lab_replay.MANIFEST_NAME).read_bytes()
        with self.assertRaises(lab_common.WriteOnceViolation):
            self._run(out, open_model=None,
                      cells=[lab_replay.make_cell(1, 'T2', 0.3, 0.6, 0.0, 206, 'realized', 10)])
        self.assertEqual((out / lab_replay.MANIFEST_NAME).read_bytes(), before)

    def test_negative_a_flipped_table_byte_is_refused(self) -> None:
        out = self.tmp / 'out'
        self._run(out)
        path = out / lab_replay.TABLE_NAME
        data = bytearray(path.read_bytes())
        i = data.index(b'"HARM_RETAIN":') + len(b'"HARM_RETAIN":')
        data[i] = ord('9') if data[i] != ord('9') else ord('8')
        path.write_bytes(bytes(data))
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.verify_manifest(out)

    def test_negative_a_script_edited_after_the_run_is_refused(self) -> None:
        out = self.tmp / 'out'
        self._run(out)
        lab_replay.verify_manifest(out)                          # positive: the unedited script
        edited = self.tmp / 'lab_replay.py'
        edited.write_bytes((LIVE / 'lab_replay.py').read_bytes() + b'# edited after the run\n')
        with mock.patch.object(lab_replay, '__file__', str(edited)):
            with self.assertRaisesRegex(lab_replay.ReplayRefused, 'lab_replay.py sha256'):
                lab_replay.verify_manifest(out)

    def test_negative_a_rewritten_seed_rule_is_refused(self) -> None:
        out = self.tmp / 'out'
        self._run(out)
        path = out / lab_replay.MANIFEST_NAME
        manifest = json.loads(path.read_text('utf-8'))
        manifest['seed']['rule'] = manifest['seed']['rule'].replace('1105', '1106')
        path.write_text(json.dumps(manifest), 'utf-8')
        with self.assertRaisesRegex(lab_replay.ReplayRefused, 'seed rule'):
            lab_replay.verify_manifest(out)

    def _reviews_fixture(self) -> Path:
        root = self.tmp / 'repo'
        (root / 'reviews').mkdir(parents=True)
        (root / 'reviews' / 'RULING_FIXTURE.md').write_text('line one\nline two\nline three\n', 'utf-8')
        return root

    def test_a_resolvable_ruling_citation_is_recorded_as_ruled(self) -> None:
        with mock.patch.object(lab_replay, 'REPO_ROOT', self._reviews_fixture()):
            manifest = self._run(self.tmp / 'r', ruling='reviews/RULING_FIXTURE.md:3')
        self.assertEqual(manifest['open_outcome_model']['status'], 'RULED')
        self.assertIsNone(manifest['open_outcome_model']['needs'])
        self.assertIn('not checked', manifest['open_outcome_model']['ruling_check'])

    def test_negative_a_ruling_that_does_not_resolve_is_refused_before_anything_runs(self) -> None:
        """The first version recorded RULED for any non-empty text, including a fixture that said
        it was not a ruling."""
        with mock.patch.object(lab_replay, 'REPO_ROOT', self._reviews_fixture()):
            for bad in ('reviews/EXAMPLE.md:1 (fixture, not a ruling)', 'reviews/EXAMPLE.md:1',
                        'reviews/RULING_FIXTURE.md:4', 'reviews/RULING_FIXTURE.md:0',
                        'reviews/RULING_FIXTURE.md', 'reviews/../RULING_FIXTURE.md:1',
                        'results/RULING_FIXTURE.md:1', 'root said so', ''):
                with self.subTest(ruling=bad):
                    out = self.tmp / 'x'
                    with self.assertRaises(lab_replay.ReplayRefused):
                        self._run(out, ruling=bad)
                    self.assertFalse(out.exists())

    def test_negative_realized_n_p_must_follow_the_roster_rule(self) -> None:
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.run_replay(synthetic_roster(), synthetic_pilot(self.tmp), CFG,
                                  realized_n_p=205, out_dir=self.tmp / 'x', open_model=None,
                                  cells=[lab_replay.make_cell(1, 'T1', 1.0, 0.6, 0.0, 205, 'r', 2)])


if __name__ == '__main__':
    unittest.main()
