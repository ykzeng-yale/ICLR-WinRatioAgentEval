"""Model-free controls for ``experiments/live_ab/lab_replay.py`` (protocol 11.5, plan stage 8).

Root 2026-09-23 20:40 item 2 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:17``): the replay is
implemented, NOT run.  Nothing here runs the 432-cell grid or reads a model; the only real input read is
the pilot table (for its 433/591 figure), and every run is on a synthetic 12-task pilot.

Each positive control has a negative control that must be REFUSED or must DISAGREE, so no check here
passes vacuously ("a control that cannot fail is not a control").  The outcome model of protocol 11.5
items 1-3 (the w-mixture success law, the arm's own pilot rate, the candidate shift, the coin map, the
joint within-task latency draw) is controlled by ``OutcomeModelTests`` on a synthetic pilot whose two
workflows have DIFFERENT outcomes and rates, with every expected value computed here from the pilot rows,
not from ``lab_replay``'s own helpers.
"""
from __future__ import annotations

import copy
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

    # The first version compared enumerate_cells(n) with enumerate_cells(n) at the production entry
    # point, so an edited GRID_* tuple passed and was written as 'full_432'.
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
        """Through ``run_replay`` with ``cells=None`` (the real full run): refused before any cell is
        simulated and before anything is written."""
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
        """``PROTOCOL_11_5_ITEM_5`` read back out of protocol 11.5 item 5 (design/protocol_FINAL.md)."""
        text = (LIVE / 'design' / 'protocol_FINAL.md').read_text('utf-8')
        item = text[text.index('5. **Cells, exhaustive:**'):text.index('6. **Output, exhaustive')]
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
class OutcomeModelTests(_Tmp):
    """Protocol 11.5 items 1-3, the model-dependent core, against values computed HERE from the pilot
    rows.

    The per-cell cross-check re-scores the drawn arrays through ``MonitorState``, so it checks the rule
    and not the draws; these controls check the draws.  Expected laws (READING R1; R4: rates over the
    whole pilot): candidate ``clip(w*y_c + (1-w)*r_c + s)`` on S1 and ``clip(q + s)`` on S2, incumbent
    ``w*y_i + (1-w)*r_i`` and ``q``; T3's candidate (proposal) ``clip(r_single_shot + s)`` on S1.
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
        incumbent, w ignored or inverted, a rate that is not the arm's own)."""
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
        """DISTRIBUTIONAL: 4,000 replicates of a T2 cell through ``run_cell``; per task and arm the
        empirical success frequency is within 5 standard errors of the law (exact where p is 0 or 1)."""
        w, q, s = 0.5, 0.45, -0.3
        _, _, _, draws = self.capture('T2', w, q, s, range(1, 4001))
        want = dict(zip(('candidate', 'incumbent'), self.expected('T2', w, q, s)))
        for arm, task_key, succ_key in (('candidate', 'cand_task', 'success_c'),
                                        ('incumbent', 'inc_task', 'success_i')):
            tasks = numpy.concatenate([x[task_key] for x in draws])
            succ = numpy.concatenate([x[succ_key] for x in draws]).astype(numpy.float64)
            n = numpy.bincount(tasks, minlength=len(self.uids))
            k = numpy.bincount(tasks, weights=succ, minlength=len(self.uids))
            p = want[arm]
            self.assertTrue((n[:12] > 1000).all())          # every S1 task seen often under each arm
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
        both = [u for u in PILOT16 if self.truth['single_shot'][u][0]
                and self.truth['self_test_repair'][u][0]]
        self.assertEqual(len(both), 8)
        for trial in ('T1', 'T2'):
            arms = CFG['trials'][trial]
            cwf, iwf = arms['candidate']['workflow'], arms['incumbent']['workflow']
            allowed = {(self.truth[cwf][u][1], self.truth[iwf][u][1]) for u in both}
            _, _, _, draws = self.capture(trial, 0.5, 0.45, 0.0, range(1, 201))
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
        pool = {self.truth['single_shot'][u][1] for u in PILOT16 if self.truth['single_shot'][u][0]}
        self.assertEqual(len(pool), 12)
        for trial in ('T3', 'T4'):
            _, _, _, draws = self.capture(trial, 0.5, 0.45, 0.0, range(1, 201))
            lat_c = numpy.concatenate([x['lat_c'] for x in draws]).tolist()
            lat_i = numpy.concatenate([x['lat_i'] for x in draws]).tolist()
            same = sum(1 for a, b in zip(lat_c, lat_i) if a == b) / len(lat_c)
            with self.subTest(trial=trial):
                self.assertTrue(set(lat_c) == set(lat_i) == pool)
                self.assertLess(abs(same - 1 / 12), 0.02)      # independent: P(same task) = 1/12
                self.assertNotAlmostEqual(same, 1.0)           # negative: a joint draw gives 1


class QuartileTests(unittest.TestCase):
    """Item 6: Q1 / median / Q3, ``numpy.percentile`` method ``linear``; known answers."""

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


class ExchangeabilityTests(_Tmp):
    """At s = 0 the arms are exchangeable for T4 only; T3's are not (review finding, 2026-09-23)."""

    def _sums(self, trial: str, open_model: dict) -> tuple:
        pilot = synthetic_pilot(self.tmp)                  # 12 tasks, 9 succeed under single_shot
        roster = {'S1': list(S1_TASKS), 'S2': []}           # S1 only: 6 pairs, roster = pilot
        m = lab_replay.build_trial_model(roster, pilot, CFG, trial, open_model)
        cell = lab_replay.make_cell(1, trial, 1.0, 0.45, 0.0, 6, 'realized', 1)
        pc = numpy.clip(lab_replay._probabilities(m, 'candidate', 1.0, 0.45), 0, 1)
        pi = lab_replay._probabilities(m, 'incumbent', 1.0, 0.45)
        sc, si = [], []
        for r in range(1, 20001):
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
        """The first version recorded RULED for any non-empty text, including a fixture that said it
        was not a ruling."""
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
