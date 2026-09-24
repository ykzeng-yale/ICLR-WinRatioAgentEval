"""Model-free controls for ``experiments/live_ab/lab_schedules.py`` (pre-freeze stages 4 and 5).

Root 2026-09-23 20:40 item 2 (``reviews/prerun_bundle_go_nogo_20260923_2040.md:17``): the drivers must
consume a frozen schedule.  These controls prove the schedules are deterministic, balanced as stated,
write-once, and refused on reload after a single flipped byte; every positive control has a negative one.
No server, request or outcome is involved.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                              # noqa: E402
import lab_schedules                                           # noqa: E402

BASE = 60260919
CFG = json.loads((LIVE / 'config.json').read_text('utf-8'))
ODS = lab_schedules.PLAN_PROPOSED_OPEN_DECISIONS


def s4(base: int = BASE, ods=ODS) -> dict:
    return lab_schedules.stage4_schedule(CFG, base, ods)


def s5(base: int = BASE, ods=ODS, stage4=None) -> dict:
    return lab_schedules.stage5_schedule(CFG, base, ods, stage4 if stage4 is not None else s4(base,
                                                                                            ods))


def reseal(schedule: dict) -> dict:
    """Re-digest a mutated schedule, so a check refuses on its INVARIANT, not on the digest."""
    body = {k: v for k, v in schedule.items() if k != 'schedule_sha256'}
    return dict(body, schedule_sha256=lab_common.sha256_canonical(body))


class Stage4Tests(unittest.TestCase):
    def test_row_counts_and_balance(self) -> None:
        sch = s4()
        lab_schedules.check_stage4(sch)
        eps = [r for r in sch['rows'] if r['kind'] == 'episode']
        self.assertEqual(len(eps), 240)
        self.assertEqual(len(sch['cells']), 8)
        for cell in sch['cells']:
            mine = [e for e in eps if e['cell'] == cell['cell']]
            self.assertEqual(len(mine), 30)
            self.assertEqual({e['task_uid'] for e in mine}, set(CFG['roster']['smoke_tasks']))
            self.assertEqual(sorted({e['repetition'] for e in mine}), [1, 2, 3, 4, 5])
        pairs = [u for u in sch['units'] if u['kind'] == 'pair']
        self.assertEqual(len(pairs), 60)
        for cell in (c for c in sch['cells'] if c['concurrency'] == 2):
            mine = [u for u in pairs if u['cell'] == cell['cell']]
            self.assertEqual(len(mine), 15)
            flat = [x for u in mine for x in u['episodes']]
            self.assertEqual(len(flat), len(set(flat)), 'pairs of a cell must be disjoint')
        self.assertEqual(sch['counts']['server_smoke'], 2)
        self.assertEqual(sch['counts']['gets'], 6)
        self.assertEqual(sch['counts']['wire_attempt_cap'], 602)
        self.assertEqual((sch['counts']['logical_calls_min'], sch['counts']['logical_calls_max']),
                         (360, 600))
        self.assertEqual(sch['status'], 'PROPOSED')
        # every row id the driver consumes is present before the first request
        consumed = set(sch['consumption_order'])
        for u in sch['units']:
            self.assertIn(u['unit_id'], consumed)
        self.assertEqual(sch['consumption_order'][:2], ['s4.srv.start.coder', 's4.srv.start.t3'])

    def test_open_decisions_change_the_schedule_as_the_plan_says(self) -> None:
        other = copy.deepcopy(ODS)
        other['OD2']['retries'] = 'trial_retry_rules'
        other['OD14']['server_smoke'] = 'no_server_smoke'
        sch = s4(ods=other)
        lab_schedules.check_stage4(sch)
        self.assertEqual(sch['counts']['wire_attempt_cap'], 1800)
        self.assertEqual(sch['counts']['server_smoke'], 0)
        self.assertEqual({r['max_connection_retries'] for r in sch['rows']
                          if r['kind'] == 'episode'}, {2})

    def test_negative_open_decisions_are_never_defaulted(self) -> None:
        for bad in (None, {}, {k: v for k, v in ODS.items() if k != 'OD14'},
                    dict(ODS, OD2=dict(ODS['OD2'], retries='sometimes')),
                    dict(ODS, OD1=dict(ODS['OD1'], request_timeout_s=0)),
                    dict(ODS, OD1={k: v for k, v in ODS['OD1'].items() if k != 'status'})):
            with self.subTest(bad=bad):
                with self.assertRaises(lab_schedules.ScheduleRefused):
                    lab_schedules.stage4_schedule(CFG, BASE, bad)

    def test_negative_each_invariant_refuses_its_mutation(self) -> None:
        good = s4()
        mutations = {}
        m = copy.deepcopy(good)                       # an episode moved to another repetition
        next(r for r in m['rows'] if r['kind'] == 'episode')['repetition'] = 2
        mutations['coordinate'] = m
        m = copy.deepcopy(good)                       # a pair that is not disjoint
        pairs = [u for u in m['units'] if u['kind'] == 'pair']
        pairs[1]['episodes'][0] = pairs[0]['episodes'][0]
        mutations['overlapping_pair'] = m
        m = copy.deepcopy(good)                       # a unit missing from the consumption order
        m['consumption_order'].pop(10)
        mutations['consumption'] = m
        m = copy.deepcopy(good)                       # a repeated execution slot
        m['units'][0]['seq'] = m['units'][1]['seq']
        mutations['seq'] = m
        m = copy.deepcopy(good)                       # SERVER_SMOKE dropped although OD14 says yes
        m['rows'] = [r for r in m['rows'] if r['kind'] != 'server_smoke']
        mutations['smoke'] = m
        m = copy.deepcopy(good)                       # a timeout other than OD1's
        next(r for r in m['rows'] if r['kind'] == 'episode')['request_timeout_s'] = 240
        mutations['timeout'] = m
        for name, bad in mutations.items():
            with self.subTest(mutation=name):
                with self.assertRaises(lab_schedules.ScheduleRefused):
                    lab_schedules.check_stage4(reseal(bad))


class Stage5Tests(unittest.TestCase):
    def test_row_counts_orientation_and_links(self) -> None:
        stage4 = s4()
        sch = s5(stage4=stage4)
        lab_schedules.check_stage5(sch, stage4)
        eps = [r for r in sch['rows'] if r['kind'] == 'episode']
        self.assertEqual(len(eps), 240)
        self.assertEqual(len(sch['units']), 120)
        for contrast in ('T1', 'T2', 'T3', 'T4'):
            mine = [u for u in sch['units'] if u['contrast'] == contrast]
            first = [u for u in mine if u['candidate_at_position_1']]
            self.assertEqual((len(mine), len(first)), (30, 15))
            arms = {(e['arm'], e['workflow'], e['server']) for e in eps if e['contrast'] == contrast}
            self.assertEqual(arms, {('candidate', CFG['trials'][contrast]['candidate']['workflow'],
                                     CFG['trials'][contrast]['candidate']['server']),
                                    ('incumbent', CFG['trials'][contrast]['incumbent']['workflow'],
                                     CFG['trials'][contrast]['incumbent']['server'])})
            self.assertEqual(all(u['solo_links_identical'] for u in mine), contrast == 'T4')
        linked = {e['solo_link'] for e in eps}
        conc1 = {r['row_id'] for r in stage4['rows'] if r['kind'] == 'episode'
                 and r['concurrency'] == 1}
        self.assertTrue(linked <= conc1)
        self.assertNotIn('self_test_repair', {r['workflow'] for r in stage4['rows']
                                              if r['kind'] == 'episode' and r['server'] == 't3'
                                              and r['row_id'] in linked})
        self.assertEqual(sch['counts']['wire_attempt_cap'], 420)
        self.assertEqual(sch['stage4_schedule_sha256'], stage4['schedule_sha256'])
        self.assertIsNone(sch['request_timeout_s']['value'])

    def test_negative_orientation_and_link_mutations_are_refused(self) -> None:
        stage4 = s4()
        good = s5(stage4=stage4)
        mutations = {}
        m = copy.deepcopy(good)                        # flip one pair's orientation: 16/14
        u = next(x for x in m['units'] if x['contrast'] == 'T2' and not x['candidate_at_position_1'])
        u['candidate_at_position_1'] = True
        u['episodes'].reverse()
        for position, ep in enumerate(u['episodes'], start=1):
            row = next(r for r in m['rows'] if r['row_id'] == ep)
            row['position'], row['worker_index'] = position, position - 1
        mutations['16_14'] = m
        m = copy.deepcopy(good)                        # a solo link to a concurrency-2 row
        cand2 = next(r['row_id'] for r in stage4['rows'] if r['kind'] == 'episode'
                     and r['concurrency'] == 2)
        next(r for r in m['rows'] if r['kind'] == 'episode')['solo_link'] = cand2
        mutations['link'] = m
        m = copy.deepcopy(good)                        # a pair of two candidates
        eps = [r for r in m['rows'] if r['kind'] == 'episode']
        eps[1]['arm'] = 'candidate'
        mutations['arms'] = m
        for name, bad in mutations.items():
            with self.subTest(mutation=name):
                with self.assertRaises(lab_schedules.ScheduleRefused):
                    lab_schedules.check_stage5(reseal(bad), stage4)

    def test_negative_stage5_refuses_another_stage4_or_other_decisions(self) -> None:
        stage4 = s4()
        other = copy.deepcopy(ODS)
        other['OD2']['retries'] = 'trial_retry_rules'
        with self.assertRaises(lab_schedules.ScheduleRefused):
            lab_schedules.stage5_schedule(CFG, BASE, other, stage4)
        tampered = copy.deepcopy(stage4)
        tampered['smoke_tasks'][0] = 'mbpp_full/1'
        with self.assertRaises(lab_schedules.ScheduleRefused):
            lab_schedules.stage5_schedule(CFG, BASE, ODS, tampered)
        sch = s5(stage4=stage4)
        with self.assertRaises(lab_schedules.ScheduleRefused):
            lab_schedules.check_stage5(sch, s4(base=BASE + 1))


class DeterminismTests(unittest.TestCase):
    def test_same_inputs_same_bytes(self) -> None:
        a = lab_common.canonical_json(s5())
        b = lab_common.canonical_json(s5())
        self.assertEqual(a, b)
        self.assertEqual(lab_common.canonical_json(s4()), lab_common.canonical_json(s4()))

    def test_negative_another_seed_base_gives_another_schedule(self) -> None:
        a, b = s4(), s4(base=BASE + 1)
        self.assertNotEqual([u['seq'] for u in a['units']], [u['seq'] for u in b['units']])
        x, y = s5(), s5(base=BASE + 1)
        self.assertNotEqual(x['orientation'], y['orientation'])

    def test_seed_streams_are_apart_from_the_trial_order_streams(self) -> None:
        import numpy
        order = {tuple(numpy.random.SeedSequence([BASE, e]).generate_state(4)) for e in (1, 2, 3, 4)}
        mine = {tuple(numpy.random.SeedSequence([BASE, t]).generate_state(4))
                for t in (lab_schedules.STAGE4_SEED_TAG, lab_schedules.STAGE5_SEED_TAG)}
        self.assertEqual(len(mine), 2)
        self.assertFalse(order & mine)


class WriteOnceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='sched_'))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_write_then_reload(self) -> None:
        stage4 = s4()
        path = self.tmp / 'STAGE4_SCHEDULE.json'
        digest = lab_schedules.write_schedule(stage4, path)
        self.assertEqual(lab_schedules.load_schedule(path, expected_file_sha256=digest), stage4)
        self.assertEqual(lab_schedules.write_schedule(stage4, path), digest)   # same bytes: no-op

    def test_negative_write_once_refusal(self) -> None:
        path = self.tmp / 'STAGE4_SCHEDULE.json'
        lab_schedules.write_schedule(s4(), path)
        before = path.read_bytes()
        with self.assertRaises(lab_common.WriteOnceViolation):
            lab_schedules.write_schedule(s4(base=BASE + 1), path)
        self.assertEqual(path.read_bytes(), before)

    def test_negative_a_flipped_byte_is_refused_on_reload(self) -> None:
        path = self.tmp / 'STAGE5_SCHEDULE.json'
        digest = lab_schedules.write_schedule(s5(), path)
        data = path.read_bytes()
        i = data.index(b'"repetition":') + len(b'"repetition":')
        for flipped in (data[:i] + (b'4' if data[i:i + 1] != b'4' else b'3') + data[i + 1:],
                        data[:5] + bytes([data[5] ^ 0x01]) + data[6:],
                        data[:-1] + b'x'):
            with self.subTest(offset=i):
                bad = self.tmp / 'bad.json'
                bad.write_bytes(flipped)
                with self.assertRaises(lab_schedules.ScheduleRefused):
                    lab_schedules.load_schedule(bad)
                with self.assertRaises(lab_schedules.ScheduleRefused):
                    lab_schedules.load_schedule(bad, expected_file_sha256=digest)
                bad.unlink()

    def test_negative_an_unchecked_schedule_is_not_written(self) -> None:
        bad = copy.deepcopy(s4())
        bad['units'][0]['seq'] = bad['units'][1]['seq']
        with self.assertRaises(lab_schedules.ScheduleRefused):
            lab_schedules.write_schedule(reseal(bad), self.tmp / 'x.json')
        self.assertFalse((self.tmp / 'x.json').exists())


if __name__ == '__main__':
    unittest.main()
