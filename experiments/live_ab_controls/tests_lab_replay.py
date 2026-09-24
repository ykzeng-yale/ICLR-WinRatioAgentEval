"""Model-free controls for ``experiments/live_ab/lab_replay.py`` (protocol 11.5, plan stage 8).

Root 2026-09-23 20:40 item 2 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:17``): the replay is
implemented, NOT run.  Nothing here runs the 432-cell grid or reads a model; the only real input read is
the pilot table (for its 433/591 figure), and every run is on a synthetic 12-task pilot.

Each positive control has a negative control that must be REFUSED or must DISAGREE, so no check here
passes vacuously (``CONTRACT.md``: "a control that cannot fail is not a control").
"""
from __future__ import annotations

import copy
import csv
import json
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
PILOT_CSV = LIVE.parents[1] / 'results' / 'local_stream' / 'episodes_flat.csv'
S1_TASKS = ['mbpp/%d' % i for i in range(1, 9)] + ['humaneval/%d' % i for i in range(4)]


def synthetic_pilot(tmp: Path, *, n_tasks: int = 12, seed: int = 3) -> lab_replay.Pilot:
    """A 12-task pilot in the ``episodes_flat.csv`` shape; self_test_repair ~4.5x slower."""
    rng = numpy.random.default_rng(seed)
    tasks = S1_TASKS if n_tasks == 12 else ['mbpp/%d' % i for i in range(1, n_tasks + 1)]
    path = tmp / 'pilot.csv'
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['task_id', 'variant', 'success', 'latency_s'])
        w.writeheader()
        for i, t in enumerate(tasks):
            for wf in ('single_shot', 'self_test_repair'):
                ok = i % 4 != 3                       # 9 of 12 succeed under both workflows
                lat = float(rng.uniform(2.0, 20.0)) * (4.5 if wf == 'self_test_repair' else 1.0)
                w.writerow({'task_id': t, 'variant': wf, 'success': 'True' if ok else 'False',
                            'latency_s': repr(lat)})
    return lab_replay.load_pilot_csv(path)


def synthetic_roster(n_s2: int = 400) -> dict:
    return {'S1': list(S1_TASKS), 'S2': ['mbpp_full/%d' % (1000 + i) for i in range(n_s2)]}


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='replay_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# ------------------------------------------------------------------------------------------------
class GridEnumerationTests(unittest.TestCase):
    """Protocol 11.5 item 5: exhaustive 432 cells, 3,456,000 replicates -- enumerated, never simulated."""

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

    def test_the_intact_grid_passes_the_check(self) -> None:
        lab_replay.check_grid(lab_replay.enumerate_cells(540), 540)

    def test_negative_every_mutated_grid_is_refused(self) -> None:
        good = lab_replay.enumerate_cells(540)
        dropped = good[:-1]
        duplicated = good + [good[0]]
        swapped = [good[1], good[0]] + good[2:]
        fewer_t4 = [dict(c, replicates=4000) if c['trial'] == 'T4' else c for c in good]
        other_n_p = lab_replay.enumerate_cells(541)
        for name, bad in (('dropped', dropped), ('duplicated', duplicated), ('swapped', swapped),
                          ('fewer_t4', fewer_t4), ('other_realized', other_n_p)):
            with self.subTest(mutation=name):
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.check_grid(bad, 540)


# ------------------------------------------------------------------------------------------------
class SeedRuleTests(_Tmp):
    """The stated per-replicate rule: deterministic, per replicate, and apart from the order seeds."""

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

    def test_negative_nonpositive_seed_coordinates_are_refused(self) -> None:
        for args in ((BASE, 0, 1), (BASE, 1, 0), (0, 1, 1), (BASE, True, 1)):
            with self.subTest(args=args):
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.replicate_generator(*args)


# ------------------------------------------------------------------------------------------------
class OrderEqualityTests(unittest.TestCase):
    """``order_indices`` reproduces ``lab_design.arrival_order`` uid for uid under the trial seed."""

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


# ------------------------------------------------------------------------------------------------
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
    """``decide_matrix`` equals ``lab_monitor.band`` + ``lab_monitor.decide`` exactly."""

    LENGTH = 260

    def setUp(self) -> None:
        self.mc = lab_replay.frozen_monitor_config(CFG, 'T1', self.LENGTH)
        self.radius = lab_replay.radius_vector(self.mc, self.LENGTH)
        self.seqs = _random_sequences(length=self.LENGTH)

    def _disagreements(self, radius, mc_kernel=None) -> tuple[int, set]:
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


class PairScoreAgreementTests(unittest.TestCase):
    """``pair_scores`` (winstats.compare, broadcast) equals ``lab_enclosure.final_scores`` per pair."""

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


class ScalarCrosscheckTests(_Tmp):
    """The per-cell cross-check through ``MonitorState`` is a live refusal, not a label."""

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


# ------------------------------------------------------------------------------------------------
class OpenOutcomeModelTests(_Tmp):
    """T3's pilot-less candidate and the T3/T4 cost pair are explicit parameters, never defaulted."""

    def test_the_gaps_are_derived_from_the_config(self) -> None:
        self.assertEqual(lab_replay.outcome_model_gaps(CFG, 'T1'), {})
        self.assertEqual(lab_replay.outcome_model_gaps(CFG, 'T2'), {})
        self.assertEqual(sorted(lab_replay.outcome_model_gaps(CFG, 'T3')),
                         ['T3.candidate.success', 'T3.cost_pair'])
        self.assertEqual(sorted(lab_replay.outcome_model_gaps(CFG, 'T4')), ['T4.cost_pair'])
        self.assertEqual(sorted(lab_replay.PROPOSED_OPEN_MODEL), sorted(
            set(lab_replay.outcome_model_gaps(CFG, 'T3')) | set(lab_replay.outcome_model_gaps(CFG,
                                                                                            'T4'))))

    def test_negative_undefined_trials_refuse_without_an_explicit_model(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        for trial in ('T3', 'T4'):
            with self.subTest(trial=trial):
                with self.assertRaises(lab_replay.ReplayRefused) as ctx:
                    lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, trial, None)
                self.assertIn('PROPOSED', str(ctx.exception))

    def test_negative_wrong_keys_or_values_are_refused(self) -> None:
        for bad in ({'T4.cost_pair': 'something_else'},
                    {'T4.cost_pair': 'independent_single_shot_successes', 'T1.cost_pair': 'x'},
                    {}):
            with self.subTest(bad=bad):
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.check_open_model(CFG, bad, ['T4'])
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.check_open_model(CFG, {'T4.cost_pair': 'independent_single_shot_successes'},
                                        ['T1'])

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

    def test_the_real_pilot_has_the_protocol_rates(self) -> None:
        """Reads the pilot table only (no simulation): 433/591 under both workflows."""
        pilot = lab_replay.load_pilot_csv(PILOT_CSV)
        self.assertEqual(len(pilot.tasks), 591)
        for wf in ('single_shot', 'self_test_repair'):
            self.assertEqual(int(pilot.success[wf].sum()), 433)


# ------------------------------------------------------------------------------------------------
class TinyEndToEndTests(_Tmp):
    """2 cells x 50 replicates on a synthetic 12-task pilot, through ``run_replay``: table, manifest,
    write-once, verification, and the refusals around them."""

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

    def test_ruled_model_is_recorded_as_ruled(self) -> None:
        manifest = self._run(self.tmp / 'r', ruling='reviews/EXAMPLE.md:1 (fixture, not a ruling)')
        self.assertEqual(manifest['open_outcome_model']['status'], 'RULED')
        self.assertIsNone(manifest['open_outcome_model']['needs'])

    def test_negative_realized_n_p_must_follow_the_roster_rule(self) -> None:
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.run_replay(synthetic_roster(), synthetic_pilot(self.tmp), CFG,
                                  realized_n_p=205, out_dir=self.tmp / 'x', open_model=None,
                                  cells=[lab_replay.make_cell(1, 'T1', 1.0, 0.6, 0.0, 205, 'r', 2)])

    def test_negative_the_replay_cannot_change_a_rule_parameter(self) -> None:
        cfg = copy.deepcopy(CFG)
        cfg['monitor']['delta'] = 0.05
        with self.assertRaises(lab_replay.ReplayRefused):
            self._run(self.tmp / 'x', cfg=cfg)
        self.assertFalse((self.tmp / 'x' / lab_replay.TABLE_NAME).exists())

    def test_a_horizon_above_the_roster_is_deposited_not_simulable(self) -> None:
        out = self.tmp / 'ns'
        self._run(out, open_model=None,
                  cells=[lab_replay.make_cell(1, 'T1', 1.0, 0.6, 0.0, 495, 'fixed_495', 5)])
        row = json.loads((out / lab_replay.TABLE_NAME).read_text('utf-8'))['rows'][0]
        self.assertEqual(row['status'], 'NOT_SIMULABLE')
        self.assertIsNone(row['counts'])
        self.assertIn('exceeds', row['reason'])


class WilsonTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
