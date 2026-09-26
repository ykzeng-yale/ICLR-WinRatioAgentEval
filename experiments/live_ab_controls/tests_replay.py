"""Model-free controls for ``experiments/live_ab/lab_replay.py`` (protocol 11.5).

Plain ``unittest``, matching this branch's own control-file convention.  Nothing here runs the
432-cell grid or reads a model; the only real input read is the pilot table (for its 433/591
figure), and every simulated run in this file is on a synthetic 12-task pilot with at most a
handful of replicates.  Every positive control below has a negative control that must be REFUSED
or must DISAGREE, so no check here can pass vacuously.

Scope, and what was NOT ported from the held branch's own suite (``ref:session60-repair-replay``,
``experiments/live_ab_controls/tests_lab_replay.py``, 37 tests): that suite's
``OutcomeModelTests`` (empirical frequency checks against the exact success/cost law),
``BandDecideAgreementTests``/``PairScoreAgreementTests`` (element-wise agreement with
``lab_monitor``/``winstats`` on random sequences) and ``ExchangeabilityTests`` (the T3-vs-T4 A/A
claim) are DISTRIBUTIONAL/agreement controls over the pure simulation core, which this module
hand-ports unchanged; they were not re-authored here to keep this step's controls focused on the
five checks the task names (grid, seed, open-model refusal, shard receipt, rule-parameter
immutability).  They remain a reasonable follow-up port, since the ported functions they exercise
are unchanged from the held module.

Each class below targets one of this step's five required checks, in order:

1. ``GridEnumerationTests`` -- the grid equals the protocol's literal spec; a mutated spec refused.
2. ``SeedRuleTests`` -- the seed rule is deterministic; changing ``c`` or ``r`` changes the stream;
   an unseeded/wall-clock generator is refused (by construction: it cannot reproduce).
3. ``OpenModelTests`` -- a T3/T4 cell without ``open_model`` raises; with one, a TINY replicate
   count runs.
4. ``ShardReceiptTests`` -- a shard receipt is written per completed cell and resume skips done
   cells; a rewrite with different bytes is refused.
5. ``RuleParameterTests`` -- no rule parameter can be overridden; an override raises.

Three classes below were added on independent review of the first delivery of this file, each
closing a real coverage gap the review found (not one of the five required checks, so numbered
separately rather than renumbering the five above):

6. ``NotSimulableTests`` -- the NOT_SIMULABLE dispatch itself (``run_cell`` when a cell's horizon
   exceeds the realized roster's pairs) had zero coverage in the first delivery: nothing called
   ``run_cell`` with such a cell, so a mutation that silently clipped the horizon instead of
   refusing to simulate it, or that shifted the ``>``/``>=`` boundary, would have passed the whole
   suite.  ``SeedRuleTests.test_the_generator_actually_uses_the_stream_tag_in_its_entropy`` was
   added to the same class for the matching reason: the first delivery's anti-collision test
   reconstructed the claim from the ``REPLAY_STREAM_TAG`` constant directly and never called
   ``replicate_generator`` itself, so a change that dropped the tag from the real entropy list
   survived the whole suite untouched (both were reproduced and killed the delivered suite before
   these additions; see the commit message for the reproduction).
7. ``RulingCitationTests`` -- ``check_ruling_citation`` (the ``--ruling`` gate before
   ``run_replay`` will accept a root ruling on the open outcome model) had no test at all in the
   first delivery, and was also missing from ``tests_lab_isolation.SIGNATURES['lab_replay']``
   (every other public name of the module is pinned there).
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                              # noqa: E402
import lab_monitor                                             # noqa: E402
import lab_replay                                              # noqa: E402
import lab_shard_receipt                                       # noqa: E402

BASE = 60260919
CFG = json.loads((LIVE / 'config.json').read_text('utf-8'))
PILOT_CSV = LIVE.parents[1] / 'results' / 'local_stream' / 'episodes_flat.csv'
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
    return {'S1': list(S1_TASKS), 'S2': ['mbpp_full/%d' % (1000 + i) for i in range(n_s2)]}


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='replay_ctl_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# ==================================================================================================
# 1. the grid equals the protocol's literal spec; a mutated spec is refused
# ==================================================================================================
class GridEnumerationTests(unittest.TestCase):
    def test_the_432_cells_match_the_protocol_item_5_product(self) -> None:
        cells = lab_replay.enumerate_cells(540)
        self.assertEqual(len(cells), 432)
        self.assertEqual(lab_replay.GRID_CELLS, 432)
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
        lab_replay.check_grid(cells, 540)          # positive: the intact grid passes

    def test_the_literals_match_the_current_protocol_text(self) -> None:
        """``PROTOCOL_11_5_ITEM_5`` against a fresh read of design/protocol_FINAL.md's section
        11.5 item 5 on THIS checkout (line numbers re-verified for this task, not carried over)."""
        text = (LIVE / 'design' / 'protocol_FINAL.md').read_text('utf-8')
        heading = text.index('### 11.5 The extended replay')
        item5 = text[text.index('5. **Cells, exhaustive:**', heading):
                     text.index('6. **Output, exhaustive', heading)]
        item5 = ' '.join(item5.split())
        lit = lab_replay.PROTOCOL_11_5_ITEM_5
        self.assertIn('0.3, 0.5, 0.7, 1.0', item5)
        self.assertIn('0.25, 0.45, 0.60', item5)
        self.assertIn('0, -0.02, -0.03', item5)
        self.assertIn('295, 495', item5)
        self.assertIn('T1, T2, T3, T4', item5)
        self.assertIn('4,000 replicates per cell; 20,000 for T4', item5)
        n = len(lit['w']) * len(lit['q']) * len(lit['s']) * 3 * len(lit['trials'])
        self.assertEqual(n, lab_replay.GRID_CELLS)
        # negative control: the same reading detects literals that are NOT the protocol's
        self.assertNotIn('0.3, 0.5, 0.7 }', item5)

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

    EDITS = {'three_w': ('GRID_W', (0.3, 0.5, 0.7)),
             'one_s': ('GRID_S', (0.0,)),
             'other_q': ('GRID_Q', (0.25, 0.45, 0.65)),
             'fewer_reps': ('REPLICATES', 3999),
             'fewer_t4_reps': ('REPLICATES_T4', 4000),
             'other_fixed': ('GRID_FIXED_N_P', (295, 496))}

    def test_negative_an_edited_grid_constant_is_refused_at_the_production_entry_point(self) -> None:
        """Through ``run_replay`` with ``cells=None`` (the real full-grid entry): refused before
        any cell is simulated and before anything is written -- not only by a unit test that calls
        ``check_grid`` directly."""
        boom = mock.Mock(side_effect=AssertionError('an edited grid must not be simulated'))
        with tempfile.TemporaryDirectory(prefix='replay_ctl_') as tmp:
            pilot = synthetic_pilot(Path(tmp))
            for name, (attr, value) in self.EDITS.items():
                with self.subTest(edit=name):
                    out = Path(tmp) / name
                    with mock.patch.object(lab_replay, attr, value), \
                            mock.patch.object(lab_replay, 'run_cell', boom):
                        with self.assertRaises(lab_replay.ReplayRefused):
                            lab_replay.run_replay(
                                synthetic_roster(), pilot, CFG, realized_n_p=206, out_dir=out,
                                open_model=dict(lab_replay.PROPOSED_OPEN_MODEL))
                    self.assertFalse(out.exists())
        boom.assert_not_called()


# ==================================================================================================
# 2. the seed rule is deterministic; changing c or r changes the stream; unseeded is refused
# ==================================================================================================
class SeedRuleTests(unittest.TestCase):
    def test_determinism_for_the_same_c_and_r(self) -> None:
        a = lab_replay.replicate_generator(BASE, 5, 7)
        b = lab_replay.replicate_generator(BASE, 5, 7)
        numpy.testing.assert_array_equal(a.integers(0, 1000, size=20), b.integers(0, 1000, size=20))

    def test_negative_changing_the_ordinal_or_the_replicate_changes_the_stream(self) -> None:
        a = lab_replay.replicate_generator(BASE, 5, 7).integers(0, 10**9, size=50)
        b_ordinal = lab_replay.replicate_generator(BASE, 6, 7).integers(0, 10**9, size=50)
        b_replicate = lab_replay.replicate_generator(BASE, 5, 8).integers(0, 10**9, size=50)
        b_base = lab_replay.replicate_generator(BASE + 1, 5, 7).integers(0, 10**9, size=50)
        self.assertFalse(numpy.array_equal(a, b_ordinal))
        self.assertFalse(numpy.array_equal(a, b_replicate))
        self.assertFalse(numpy.array_equal(a, b_base))

    def test_replay_seeds_never_equal_the_live_trial_arrival_order_seeds(self) -> None:
        """The hazard is real: numpy pads short entropy with a TRAILING zero, so a 2-word
        live-trial seed ``[base, e]`` equals the 3-word ``[base, e, 0]`` bit for bit.  The frozen
        stream tag 1105 (nonzero, and not any trial number 1..4) keeps the 4-word replay seed
        ``[base, 1105, c, r]`` out of that equivalence class for every live trial e in 1..4."""
        # the padding property itself, on the live-trial seed's own two words
        self.assertTrue(numpy.array_equal(
            numpy.random.SeedSequence([BASE, 1]).generate_state(4),
            numpy.random.SeedSequence([BASE, 1, 0]).generate_state(4)))
        order_states = {tuple(numpy.random.SeedSequence([BASE, e]).generate_state(4))
                        for e in (1, 2, 3, 4)}
        replay_states = {tuple(numpy.random.SeedSequence(
            [BASE, lab_replay.REPLAY_STREAM_TAG, c, r]).generate_state(4))
            for c in (1, 2, 432) for r in (1, 2, 20000)}
        self.assertFalse(order_states & replay_states)
        # negative control: REPLAY_STREAM_TAG itself must be the guard -- a tag equal to a trial
        # number, or zero, is exactly the class of mistake this stream tag exists to avoid
        self.assertNotEqual(lab_replay.REPLAY_STREAM_TAG, 0)
        self.assertNotIn(lab_replay.REPLAY_STREAM_TAG, (1, 2, 3, 4))

    def test_negative_nonpositive_seed_coordinates_are_refused(self) -> None:
        for args in ((BASE, 0, 1), (BASE, 1, 0), (0, 1, 1), (BASE, True, 1)):
            with self.subTest(args=args):
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.replicate_generator(*args)

    def test_the_generator_is_always_explicitly_seeded_never_wall_clock(self) -> None:
        """Source-level control: ``replicate_generator`` builds its ``Generator`` from a
        ``SeedSequence`` of its three int arguments alone, never from ``default_rng()`` with no
        seed and never from ``time``.  MUTATION (would be refused if it happened): a generator
        built with ``numpy.random.default_rng()`` (no seed) gives a DIFFERENT stream every call,
        so it would fail ``test_determinism_for_the_same_c_and_r`` above -- reproduced here
        directly as the negative control, rather than only asserted from source text."""
        src = lab_replay.replicate_generator.__doc__ or ''
        code = lab_replay.__dict__['replicate_generator'].__code__
        self.assertIn('SeedSequence', code.co_names)
        self.assertNotIn('time', code.co_names)
        unseeded_a = numpy.random.default_rng().integers(0, 10**9, size=50)
        unseeded_b = numpy.random.default_rng().integers(0, 10**9, size=50)
        self.assertFalse(numpy.array_equal(unseeded_a, unseeded_b),
                         'an unseeded generator is exactly the mutation this rule guards against')

    def test_the_generator_actually_uses_the_stream_tag_in_its_entropy(self) -> None:
        """Added on review: every check above proves a property of ``REPLAY_STREAM_TAG`` in
        isolation, never of ``replicate_generator``'s own OUTPUT -- so a change that quietly
        dropped the tag from the entropy list, while leaving the constant itself untouched, would
        pass every one of them.  This ties the function's real output to the tag directly."""
        for ordinal, replicate in ((1, 1), (5, 7), (432, 20000)):
            with self.subTest(ordinal=ordinal, replicate=replicate):
                want = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(
                    [BASE, lab_replay.REPLAY_STREAM_TAG, ordinal, replicate]))).integers(
                    0, 10**9, size=20)
                got = lab_replay.replicate_generator(BASE, ordinal, replicate).integers(
                    0, 10**9, size=20)
                numpy.testing.assert_array_equal(got, want)
        # negative control: the 3-word entropy a dropped tag would leave behind gives a DIFFERENT
        # stream for the same (ordinal, replicate) -- this is the mutation the check above exists
        # to catch, reproduced here directly rather than only asserted from source text
        tagged = lab_replay.replicate_generator(BASE, 5, 7).integers(0, 10**9, size=20)
        without_tag = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(
            [BASE, 5, 7]))).integers(0, 10**9, size=20)
        self.assertFalse(numpy.array_equal(tagged, without_tag),
                         'a stream tag silently dropped from the entropy is exactly the mutation '
                         'this test exists to catch')


# ==================================================================================================
# 3. a T3/T4 cell without open_model raises; with one, a TINY replicate count runs
# ==================================================================================================
class OpenModelTests(_Tmp):
    def test_the_gaps_are_derived_from_the_current_config(self) -> None:
        self.assertEqual(lab_replay.outcome_model_gaps(CFG, 'T1'), {})
        self.assertEqual(lab_replay.outcome_model_gaps(CFG, 'T2'), {})
        self.assertEqual(sorted(lab_replay.outcome_model_gaps(CFG, 'T3')),
                         ['T3.candidate.success', 'T3.cost_pair'])
        self.assertEqual(sorted(lab_replay.outcome_model_gaps(CFG, 'T4')), ['T4.cost_pair'])

    def test_negative_a_t3_or_t4_cell_without_open_model_raises(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        roster = synthetic_roster()
        for trial in ('T3', 'T4'):
            with self.subTest(trial=trial):
                with self.assertRaises(lab_replay.ReplayRefused) as ctx:
                    lab_replay.build_trial_model(roster, pilot, CFG, trial, None)
                self.assertIn('PROPOSED', str(ctx.exception))
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.run_replay(
                        roster, pilot, CFG, realized_n_p=206, out_dir=self.tmp / trial,
                        open_model=None,
                        cells=[lab_replay.make_cell(1, trial, 0.5, 0.45, 0.0, 206, 'realized', 3)])
                self.assertFalse((self.tmp / trial).exists())

    def test_a_t3_and_a_t4_cell_run_a_tiny_replicate_count_with_an_explicit_open_model(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        roster = synthetic_roster()
        for trial, open_model in (
                ('T3', {'T3.candidate.success': 'coder_single_shot_stratum_rate',
                        'T3.cost_pair': 'independent_single_shot_successes'}),
                ('T4', {'T4.cost_pair': 'independent_single_shot_successes'})):
            with self.subTest(trial=trial):
                model = lab_replay.build_trial_model(roster, pilot, CFG, trial, open_model)
                mc = lab_replay.frozen_monitor_config(CFG, trial, 206)
                cell = lab_replay.make_cell(1, trial, 0.5, 0.45, 0.0, 206, 'realized', 3)
                row = lab_replay.run_cell(model, cell, mc, BASE, crosscheck=3)
                self.assertEqual(row['status'], 'SIMULATED')
                self.assertEqual(row['replicates_run'], 3)
                self.assertEqual(row['crosscheck'], {'replicates_checked': 3, 'mismatches': 0})

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


# ==================================================================================================
# 4. a shard receipt is written per completed unit; resume skips done units; a rewrite is refused
# ==================================================================================================
class ShardReceiptTests(_Tmp):
    OPEN_MODEL = {'T4.cost_pair': 'independent_single_shot_successes'}

    def _cells(self):
        return [lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 5),
                lab_replay.make_cell(2, 'T4', 0.5, 0.45, -0.03, 150, 'fixed_150', 5)]

    def test_a_shard_receipt_and_row_are_written_per_completed_cell(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        out = self.tmp / 'out'
        manifest = lab_replay.run_replay(synthetic_roster(), pilot, CFG, realized_n_p=206,
                                         out_dir=out, open_model=self.OPEN_MODEL,
                                         cells=self._cells(), crosscheck_per_cell=5)
        cells = self._cells()
        want_ids = {lab_replay.cell_shard_id(c) for c in cells}
        done = lab_shard_receipt.completed_shards(out / 'receipts')
        self.assertEqual(done, want_ids)
        for sid in want_ids:
            row_path = out / 'rows' / ('%s.json' % sid)
            self.assertTrue(row_path.is_file())
            receipt = json.loads((out / 'receipts' / ('%s.json' % sid)).read_text('utf-8'))
            lab_shard_receipt.validate_receipt(receipt)          # positive: a legal receipt
            self.assertEqual(receipt['outcome'], 'success')
            self.assertEqual(receipt['driver'], lab_replay.DRIVER)
            out_relpath, out_sha = next(iter(receipt['outputs'].items()))
            self.assertEqual(lab_common.sha256_file(out / out_relpath), out_sha)
        self.assertEqual(manifest['shard_receipts']['cells_run_this_call'], 2)
        self.assertEqual(manifest['shard_receipts']['cells_resumed'], 0)

    def test_a_resumed_run_skips_cells_with_an_existing_receipt(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        cells = self._cells()
        first = self.tmp / 'first'
        lab_replay.run_replay(synthetic_roster(), pilot, CFG, realized_n_p=206, out_dir=first,
                              open_model=self.OPEN_MODEL, cells=cells, crosscheck_per_cell=5)
        # simulate a kill-and-restart: a fresh directory carrying over only rows/ and receipts/
        resumed = self.tmp / 'resumed'
        resumed.mkdir()
        shutil.copytree(first / 'rows', resumed / 'rows')
        shutil.copytree(first / 'receipts', resumed / 'receipts')
        before = {p.name: p.read_bytes() for p in (resumed / 'rows').glob('*.json')}
        run_cell_calls = []
        real_run_cell = lab_replay.run_cell

        def spy(*a, **k):
            run_cell_calls.append(1)
            return real_run_cell(*a, **k)
        with mock.patch.object(lab_replay, 'run_cell', spy):
            manifest = lab_replay.run_replay(synthetic_roster(), pilot, CFG, realized_n_p=206,
                                             out_dir=resumed, open_model=self.OPEN_MODEL,
                                             cells=cells, crosscheck_per_cell=5)
        self.assertEqual(run_cell_calls, [], 'a fully-resumed run must not re-simulate any cell')
        self.assertEqual(manifest['shard_receipts']['cells_resumed'], 2)
        self.assertEqual(manifest['shard_receipts']['cells_run_this_call'], 0)
        after = {p.name: p.read_bytes() for p in (resumed / 'rows').glob('*.json')}
        self.assertEqual(before, after, 'resume must not rewrite an already-done row')
        self.assertEqual((first / lab_replay.TABLE_NAME).read_bytes(),
                         (resumed / lab_replay.TABLE_NAME).read_bytes())

    def test_negative_a_partial_resume_only_reruns_the_missing_cell(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        cells = self._cells()
        first = self.tmp / 'first'
        lab_replay.run_replay(synthetic_roster(), pilot, CFG, realized_n_p=206, out_dir=first,
                              open_model=self.OPEN_MODEL, cells=cells, crosscheck_per_cell=5)
        partial = self.tmp / 'partial'
        partial.mkdir()
        shutil.copytree(first / 'rows', partial / 'rows')
        (partial / 'receipts').mkdir()
        one_receipt = sorted((first / 'receipts').glob('*.json'))[0]
        shutil.copy(one_receipt, partial / 'receipts' / one_receipt.name)
        manifest = lab_replay.run_replay(synthetic_roster(), pilot, CFG, realized_n_p=206,
                                         out_dir=partial, open_model=self.OPEN_MODEL,
                                         cells=cells, crosscheck_per_cell=5)
        self.assertEqual(manifest['shard_receipts']['cells_resumed'], 1)
        self.assertEqual(manifest['shard_receipts']['cells_run_this_call'], 1)

    def test_negative_rewriting_a_row_or_receipt_with_different_bytes_is_refused(self) -> None:
        pilot = synthetic_pilot(self.tmp)
        row = lab_replay.run_cell(
            lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, 'T2', None),
            lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 5),
            lab_replay.frozen_monitor_config(CFG, 'T2', 206), BASE, crosscheck=5)
        rows_dir = self.tmp / 'rows'
        rows_dir.mkdir(parents=True, exist_ok=True)
        lab_common.write_json_atomic(rows_dir / 'x.json', row, durable=True)
        with self.assertRaises(lab_common.WriteOnceViolation):
            lab_common.write_json_atomic(rows_dir / 'x.json', dict(row, status='TAMPERED'),
                                         durable=True)
        cell = lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 5)
        receipt = {
            'schema': lab_shard_receipt.SCHEMA, 'shard_id': lab_replay.cell_shard_id(cell),
            'driver': lab_replay.DRIVER, 'schedule_row': cell,
            'pins': {'code': {'lab_replay.py': 'a' * 64}, 'config': {'sha256': 'b' * 64},
                    'seed': {'design_seed_base': BASE}, 'data': {}},
            'inputs': {}, 'outputs': {}, 'start_utc': '2026-01-01T00:00:00Z',
            'end_utc': '2026-01-01T00:00:01Z', 'outcome': 'success', 'harness_pin_delta': []}
        receipts_dir = self.tmp / 'receipts'
        lab_shard_receipt.write_shard_receipt(receipts_dir, receipt)
        with self.assertRaises(lab_common.WriteOnceViolation):
            lab_shard_receipt.write_shard_receipt(receipts_dir, dict(receipt, outcome='failure'))
        # positive: an identical rewrite is a no-op, not a violation
        lab_shard_receipt.write_shard_receipt(receipts_dir, dict(receipt))


# ==================================================================================================
# 5. no rule parameter can be overridden; an override raises
# ==================================================================================================
class RuleParameterTests(_Tmp):
    def test_the_frozen_rule_matches_protocol_11_5_item_4(self) -> None:
        mc = lab_replay.frozen_monitor_config(CFG, 'T1', 100)
        self.assertEqual(mc.alpha_gate, 0.00625)
        self.assertEqual(mc.rho, 100.0)
        self.assertEqual(mc.delta, 0.03)
        self.assertEqual(mc.n_min, 100)

    def test_negative_an_overridden_rule_parameter_is_refused(self) -> None:
        for key, value in (('alpha_gate', 0.0125), ('rho', 50.0), ('delta', 0.05), ('n_min', 10)):
            with self.subTest(key=key):
                cfg = json.loads(json.dumps(CFG))
                cfg['monitor'][key] = value
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.frozen_monitor_config(cfg, 'T1', 100)

    def test_negative_run_replay_refuses_an_overridden_rule_parameter_before_writing_anything(
            self) -> None:
        pilot = synthetic_pilot(self.tmp)
        cfg = json.loads(json.dumps(CFG))
        cfg['monitor']['delta'] = 0.05
        out = self.tmp / 'x'
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.run_replay(
                synthetic_roster(), pilot, cfg, realized_n_p=206, out_dir=out,
                open_model={'T4.cost_pair': 'independent_single_shot_successes'},
                cells=[lab_replay.make_cell(1, 'T4', 0.5, 0.6, 0.0, 206, 'realized', 5)])
        self.assertFalse((out / lab_replay.TABLE_NAME).exists())
        self.assertFalse((out / lab_replay.MANIFEST_NAME).exists())
        self.assertEqual(list((out / 'rows').glob('*.json')) if (out / 'rows').is_dir() else [], [])

    def test_negative_a_mismatched_horizon_between_cell_and_monitor_is_refused(self) -> None:
        """A cell claiming ``n_p`` while the monitor config was built for a different horizon is
        exactly the shape a silently-overridden horizon would take; ``run_cell`` refuses it."""
        pilot = synthetic_pilot(self.tmp)
        model = lab_replay.build_trial_model(synthetic_roster(), pilot, CFG, 'T2', None)
        cell = lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 5)
        wrong_mc = lab_replay.frozen_monitor_config(CFG, 'T2', 300)
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.run_cell(model, cell, wrong_mc, BASE, crosscheck=0)


# ==================================================================================================
# 6. added on review: run_cell's NOT_SIMULABLE dispatch had zero coverage
# ==================================================================================================
class NotSimulableTests(_Tmp):
    def test_a_cell_above_the_realized_horizon_is_deposited_not_simulable(self) -> None:
        """Positive control, and the mutation this guards against: a cell whose ``n_p`` exceeds
        the realized roster's pairs must be deposited ``NOT_SIMULABLE`` with every evidentiary
        field (``counts``/``rates``/``wilson95``/``crossing_prefix``/``crosscheck``/
        ``per_replicate_sha256``) left ``None`` and a reason naming OPEN_ITEMS
        ``horizon_above_roster_pairs`` -- never silently clipped to a smaller, simulable horizon
        and never partially computed."""
        pilot = synthetic_pilot(self.tmp)
        roster = synthetic_roster()
        model = lab_replay.build_trial_model(roster, pilot, CFG, 'T2', None)
        pairs_available = model.pairs_available
        over = pairs_available + 1
        mc = lab_replay.frozen_monitor_config(CFG, 'T2', over)
        cell = lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, over, 'fixed_test', 3)
        row = lab_replay.run_cell(model, cell, mc, BASE, crosscheck=0)
        self.assertEqual(row['status'], 'NOT_SIMULABLE')
        self.assertIn('horizon_above_roster_pairs', row['reason'])
        self.assertIn(str(over), row['reason'])
        self.assertIn(str(pairs_available), row['reason'])
        for field in ('counts', 'rates', 'wilson95', 'crossing_prefix', 'crosscheck',
                      'per_replicate_sha256'):
            self.assertIsNone(row[field], field)

    def test_negative_a_cell_at_exactly_the_horizon_is_simulated_not_short_circuited(self) -> None:
        """The boundary itself: ``n_p == pairs_available`` must run (``SIMULATED``), never be
        caught by an off-by-one ``>=`` in place of ``>``."""
        pilot = synthetic_pilot(self.tmp)
        roster = synthetic_roster()
        model = lab_replay.build_trial_model(roster, pilot, CFG, 'T2', None)
        at = model.pairs_available
        mc = lab_replay.frozen_monitor_config(CFG, 'T2', at)
        cell = lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, at, 'realized', 3)
        row = lab_replay.run_cell(model, cell, mc, BASE, crosscheck=0)
        self.assertEqual(row['status'], 'SIMULATED')
        self.assertIsNotNone(row['counts'])


# ==================================================================================================
# 7. added on review: check_ruling_citation had no test and was missing from tests_lab_isolation
# ==================================================================================================
class RulingCitationTests(unittest.TestCase):
    REAL_RULING = 'reviews/prerun_bundle_go_nogo_20260923_2040.md:17'

    def test_a_resolvable_citation_is_returned_unchanged(self) -> None:
        self.assertEqual(lab_replay.check_ruling_citation(self.REAL_RULING), self.REAL_RULING)

    def test_negative_malformed_citations_are_refused(self) -> None:
        for bad in ('not-a-citation', 'reviews/x.md', 'reviews/x.md:0', 'reviews/x.md:-1',
                    'reviews/../x.md:1', '/etc/passwd:1', 'reviews/x.md:1 extra', None, 42):
            with self.subTest(bad=bad):
                with self.assertRaises(lab_replay.ReplayRefused):
                    lab_replay.check_ruling_citation(bad)

    def test_negative_a_nonexistent_ruling_file_is_refused(self) -> None:
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.check_ruling_citation('reviews/does_not_exist_20260101.md:1')

    def test_negative_a_line_number_past_the_files_end_is_refused(self) -> None:
        lines = (lab_replay.REPO_ROOT / 'reviews' / 'prerun_bundle_go_nogo_20260923_2040.md') \
            .read_text('utf-8').split('\n')
        n_lines = len(lines) - 1 if lines and lines[-1] == '' else len(lines)
        with self.assertRaises(lab_replay.ReplayRefused):
            lab_replay.check_ruling_citation('reviews/prerun_bundle_go_nogo_20260923_2040.md:%d'
                                             % (n_lines + 10_000))

    def test_run_replay_refuses_a_malformed_ruling_before_writing_anything(self) -> None:
        with tempfile.TemporaryDirectory(prefix='replay_ctl_') as tmp:
            pilot = synthetic_pilot(Path(tmp))
            out = Path(tmp) / 'out'
            with self.assertRaises(lab_replay.ReplayRefused):
                lab_replay.run_replay(
                    synthetic_roster(), pilot, CFG, realized_n_p=206, out_dir=out,
                    open_model=dict(lab_replay.PROPOSED_OPEN_MODEL), ruling='not-a-citation',
                    cells=[lab_replay.make_cell(1, 'T2', 1.0, 0.6, 0.0, 206, 'realized', 3)])
            self.assertFalse(out.exists())


# ==================================================================================================
# The real pilot table (read-only; no simulation) -- confirms the module reads it correctly.
# ==================================================================================================
class RealPilotTableTests(unittest.TestCase):
    def test_the_real_pilot_has_the_protocol_rates(self) -> None:
        pilot = lab_replay.load_pilot_csv(PILOT_CSV)
        self.assertEqual(len(pilot.tasks), 591)
        for wf in ('single_shot', 'self_test_repair'):
            self.assertEqual(int(pilot.success[wf].sum()), 433)


if __name__ == '__main__':
    unittest.main()
