"""Controls of the EB1+EB5 subset fix: the two reviews of 988baf7, each finding reproduced first.

Every behaviour below has its negative control beside it, and every orchestrator rule that
changed has a MUTATION control that restores the code path of 988baf7 and shows the chain it
wrote -- and that the verifier or the builder now refuses that chain.  Three kinds of run, as in
``tests_eb1_cap_estimand``: pure functions on synthetic chains; the production ``run_trial`` /
``World`` in process on ``dryrun_live_ab``'s mock freeze tree (``tests_eb1_supervision``'s
in-process ``lab_server``, SimWorld episodes, in-process anchor receipts); and read-only unit
calls of production functions.

* :class:`NoDecisionPointTests` -- ``lab_eventlog.no_decision_point``, the exclusion point of
  ``lab_eventlog.decision_eligibility``, the one classification the orchestrator
  (``World._look_eligibility``), the verifier (``reference_rule.agreement``) and the builder call
  (``tests_decision_eligibility``, root 16:05): each trigger and the event that is NOT one beside
  it.  The 988baf7 mutation below now restricts that gate (``World._look_eligibility``).
* :class:`OwedAbortInProcess` -- reviewer 1 finding 1: a restart that fails its identity or
  smoke stage while the crossing pair is in flight owes an abort; the drain's crossing look now
  takes NO decision; the mutation (the 988baf7 gate: only the cap suppressed a decision) decides
  and is FAILed (``decision_after_no_decision_point``) and reported ``LIVE_DECISION_INVALID``.
* :class:`AbortDrainCrossingInProcess` -- reviewer 1 finding 2: a receipt-mismatch abort (the
  production ``World._auto_abort``) closes over the crossing pair's partner; the close drain's
  crossing look is reported not acted on (INFO), never ``LIVE_DECISION_INVALID``; the same
  chain read without the point is the negative control.  And the same crossing revealed in
  the SAME pump pass as the mismatch: 988baf7 decided there (then aborted post-decision); the
  chain point now withholds that decision too.
* :class:`CapSupersededTests` -- reviewer 1 finding 3: ``trial_aborted(unresolved_worker)``
  superseding the cap satisfies ``cap_abort_iff_required``, on synthetic chains and on the
  production path (the kill of the capped pair's workers never confirmed).
* :class:`ResumeUnresolvedInProcess` -- reviewer 1 finding 4: a resume that cannot confirm an
  orphan's kill records it ``alive_unresolved`` before refusing; the later resume ends
  ``trial_aborted(unresolved_worker)``; the mutation (nothing recorded) ends ``trial_ended``.
* :class:`CounterDeltaTests` / :class:`UnreadableSpoolTests` -- reviewer 1, the two low
  findings on placeholders: a never-read counter is ``null``, an unread spool is ``null`` /
  ``null`` (never the digest of an empty file), in the record, the verdict and the seal.
* :class:`SealAndSpoolRecheckTests` -- reviewer 2 finding 3: the seal's prefix digest and
  ``late_unread``, the verdict's ``spool_grew``, and the verifier's ``spool_after_resolution``,
  each with a control that fails when the guard is removed (in process and on synthetic input).
* :class:`LifecycleRuleControls` -- reviewer 2 finding 4: ``post_switch_after_cap`` and the
  ``completion_record`` recount, each fired by a chain and silent on the unchanged chain.
* :class:`UsageFieldsCountTests` -- reviewer 2 (low): the count half of ``usage_fields``.
* :class:`IdleWaitOverrideTests` -- reviewer 2 (low): a runtime ``resolution_idle_wait_s`` is
  refused outside a dry-run tree.
* :class:`FixtureCacheTests` -- reviewer 2 finding 6: the compiled C test double's cache is used
  only when its compile-time manifest and source markers verify; a planted cache is moved aside.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_live_ab_results as builder                                 # noqa: E402
import dryrun_live_ab as dry                                            # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_verify_log                                                   # noqa: E402
import sm_fixture                                                       # noqa: E402
import tests_eb1_cap_estimand as cap                                    # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402
from lab_common import canonical_json, sha256_bytes, sha256_canonical, sha256_text  # noqa: E402

setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule

CAP = cap.CAP
SUPERVISION = {'server_supervision': {'max_supervised_restarts_per_server_per_trial': CAP,
                                      'on_exceeding': 'abort_trial_incomplete'}}


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


def _chain(*specs) -> list:
    """``(type, body)`` pairs numbered 0..n-1."""
    return [{'seq': i, 'type': t, 'body': dict(b), 'chain': 'T4'}
            for i, (t, b) in enumerate(specs)]


def crossing(events) -> dict:
    """The first logged look whose reference shadow crosses."""
    return next(e for e in of(events, 'monitor_update')
                if e['body']['shadow']['action'] != 'none')


_REAL_ELIGIBILITY = orch.World._look_eligibility


def look_988baf7(self, trigger):
    """MUTATION: the look gate of 988baf7 (``World._look_eligibility`` restricted to what
    988baf7 checked) -- only the restart cap's owed abort or point, the close, or an unresolved
    worker withheld a decision; another owed abort, or an abort trigger already in the chain,
    did not."""
    got = _REAL_ELIGIBILITY(self, trigger)
    if got['eligible'] or got['reason'] in ('decision_logged', 'drain_look',
                                            'server_restart_cap'):
        return got
    point = self.no_decision or {}
    if got['reason'] == 'abort_owed' and point.get('abort_reason') == orch.RESTART_CAP_REASON:
        return got
    if self.pending_abort == orch.RESTART_CAP_REASON or self.closing or self.unresolved_seen:
        return got
    return {'eligible': True, 'reason': None}


# --------------------------------------------------------------------------- #
# the no-decision point
# --------------------------------------------------------------------------- #
class NoDecisionPointTests(unittest.TestCase):

    def point(self, *specs, cap_=CAP, limit=10):
        return lab_eventlog.no_decision_point(_chain(*specs), cap_, failure_limit=limit)

    def test_the_constants_are_the_orchestrators(self):
        self.assertEqual(lab_eventlog.NEVER_HEALTHY_START_STAGES, orch.NEVER_HEALTHY_STAGES)
        self.assertEqual(lab_eventlog.CONSECUTIVE_FAILURE_CLASSES, orch.TERMINAL_CLASSES)

    def test_an_owed_supervision_abort(self):
        inv = ('invocation_started', {})
        for stage in ('gguf', 'serving_manifest', 'identity', 'smoke'):
            with self.subTest(stage=stage):
                got = self.point(inv, ('server_start_failed', {'kind': 'restart',
                                                               'stage': stage}))
                self.assertEqual(got, {'seq': 1, 'reason': 'server_start_failed'})
        # negative controls: a never-healthy restart owes a PAUSE, not an abort
        for stage in ('launch', 'health'):
            self.assertIsNone(self.point(inv, ('server_start_failed',
                                               {'kind': 'restart', 'stage': stage})))
        # ... except a FIRST start (before any invocation_started), which aborts at every stage
        self.assertEqual(self.point(('server_start_failed', {'kind': 'start',
                                                             'stage': 'launch'}))['seq'], 0)
        self.assertEqual(self.point(('server_restarted', {'props_equal_previous': False})),
                         {'seq': 0, 'reason': 'server_identity'})
        self.assertIsNone(self.point(('server_restarted', {'props_equal_previous': True})))

    def test_an_automatic_abort_trigger(self):
        self.assertEqual(self.point(('llm_response', {'receipt_mismatch': ['t']})),
                         {'seq': 0, 'reason': 'receipt_mismatch'})
        self.assertIsNone(self.point(('llm_response', {'receipt_mismatch': []})))
        self.assertEqual(self.point(('episode_revealed', {'outcome': {
            'error_class': 'receipt_mismatch'}}))['reason'], 'receipt_mismatch')

        def reveal(cls):
            return ('episode_revealed', {'outcome': {'error_class': cls}})
        ten = [reveal('worker_died')] * 10
        self.assertEqual(self.point(*ten), {'seq': 9, 'reason': 'infrastructure'})
        self.assertIsNone(self.point(*ten[:9]), 'nine failures are not the rule')
        self.assertIsNone(self.point(*(ten[:9] + [reveal(None)] + ten[:1])),
                          'a revealed success resets the count')
        self.assertIsNone(self.point(*(ten[:5] + [('invocation_started', {})] + ten[:5])),
                          'the orchestrator counts per invocation')
        self.assertEqual(self.point(*ten[:3], limit=3)['seq'], 2)

    def test_an_unresolved_worker_and_the_cap(self):
        self.assertEqual(self.point(('worker_resolved', {'state': 'alive_unresolved'})),
                         {'seq': 0, 'reason': 'unresolved_worker'})
        for state in ('exited', 'killed_reaped'):
            self.assertIsNone(self.point(('worker_resolved', {'state': state})))
        downs = []
        for _ in range(CAP):
            downs += [('server_down', {'server_id': 'coder'}),
                      ('server_restarted', {'server_id': 'coder',
                                            'props_equal_previous': True})]
        downs.append(('server_down', {'server_id': 'coder'}))
        self.assertEqual(self.point(*downs), {'seq': 2 * CAP,
                                               'reason': 'server_restart_cap'})
        self.assertIsNone(self.point(*downs, cap_=None), 'a simulated run never binds')
        # the earliest point wins
        got = self.point(('llm_response', {'receipt_mismatch': ['t']}), *downs)
        self.assertEqual(got, {'seq': 0, 'reason': 'receipt_mismatch'})


# --------------------------------------------------------------------------- #
# reviewer 1 finding 1: an owed abort takes no new decision
# --------------------------------------------------------------------------- #
class OwedAbortInProcess(unittest.TestCase):
    """The D3 tree (the uncapped run deploys at n = 44; its control is
    ``tests_eb1_cap_estimand.CaseAInProcess.test_control_the_uncapped_run_decides_at_the_same_
    crossing``).  The server crashes while pair 44 is in flight and its restart fails at the
    ``identity`` (or ``smoke``) stage: an abort is owed, the pair drains, and its crossing look
    is logged unchanged -- with no decision.  988baf7 took a new decision there and then treated
    the deferred abort as a post-decision abort (reported ``deploy_candidate``)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def run(stage: str, mutated: bool):
            tree = cap.d3_tree()
            cls.trees.append(tree)
            fake = sup.FakeServers()
            fake.script = [None, stage]
            patch = (mock.patch.object(orch.World, '_look_eligibility', look_988baf7)
                     if mutated else mock.patch.object(orch, 'FIX_TEST_NOOP', None,
                                                       create=True))
            with patch:
                status = sup.run(tree, fake, hook=sup.CrashPlan(fake, pairs=(44,)))
            return status, tree.events(), tree
        cls.runs = {(stage, mutated): run(stage, mutated)
                    for stage in ('identity', 'smoke') for mutated in (False, True)}

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def test_a_failed_restart_owes_an_abort_and_the_drain_takes_no_decision(self):
        for stage, reason in (('identity', 'server_identity'), ('smoke', 'receipt_mismatch')):
            with self.subTest(stage=stage):
                status, events, tree = self.runs[(stage, False)]
                self.assertEqual(status, 'aborted')
                (failed,) = of(events, 'server_start_failed')
                self.assertEqual((failed['body']['kind'], failed['body']['stage']),
                                 ('restart', stage))
                self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'], reason)
                self.assertEqual(of(events, 'decision'), [], 'an abort creates no decision')
                look = crossing(events)
                self.assertGreater(look['seq'], failed['seq'])
                self.assertEqual((look['body']['shadow']['action'], look['body']['n']),
                                 ('deploy_candidate', 44))
                _summary, obj = cap.build(tree)
                self.assertEqual((obj['primary_result'], obj['reportable']),
                                 (builder.ABORT_INCOMPLETE_LABEL, False))
                self.assertEqual((obj['crossing_not_acted_on']['kind'],
                                  obj['crossing_not_acted_on']['n'],
                                  obj['crossing_not_acted_on']['no_decision_seq']),
                                 ('deploy_candidate', 44, failed['seq']))
                self.assertEqual(tree.verify_fails(), [])
                self.assertEqual([(sev, row['consequence']) for sev, row in
                                  cap.verifier_rows(tree, 'reference_rule.agreement')],
                                 [('INFO', 'NOT_ACTED_ON_abort_before_decision')])

    def test_mutation_the_988baf7_gate_decides_during_the_owed_abort_and_is_caught(self):
        for stage in ('identity', 'smoke'):
            with self.subTest(stage=stage):
                status, events, tree = self.runs[(stage, True)]
                self.assertEqual(status, 'aborted')
                (failed,) = of(events, 'server_start_failed')
                (decision,) = of(events, 'decision')
                self.assertGreater(decision['seq'], failed['seq'])
                self.assertEqual((decision['body']['kind'], decision['body']['n']),
                                 ('deploy_candidate', 44))
                fails = [(c, d.get('rule')) for c, d in tree.verify_fails()]
                self.assertIn(('reference_rule.agreement', 'decision_after_no_decision_point'),
                              fails)
                _summary, obj = cap.build(tree)
                self.assertEqual(obj['primary_result'],
                                 'LIVE_DECISION_INVALID (harness defect)')
                self.assertTrue(obj['decision_label'].startswith(
                    'not reportable: logged after the no-decision point'))


# --------------------------------------------------------------------------- #
# reviewer 1 finding 2: a crossing left undecided by an abort's drain
# --------------------------------------------------------------------------- #
class MismatchAt44World(sup.SupWorld):
    """``SupWorld`` whose pair-44 position-1 episode answers with a receipt mismatch (the
    production ``World._auto_abort`` then aborts ``receipt_mismatch``).  ``hold_partner``: pair
    44's position 2 does not finish until the trial is closing, so it is revealed by the close
    drain; otherwise both are revealed in the same pump pass."""

    hold_partner = True

    def finished(self, att):                                 # type: ignore[override]
        lazy = self.__dict__.setdefault('_lazy', {})
        if att.arrival in lazy and att.pair == 44:
            if att.position == 2 and type(self).hold_partner and not self.closing:
                return None
            if att.position == 1:
                del lazy[att.arrival]
                dry.run_sim_episode(att.job, dict(self.scenario or sup.SCENARIO,
                                                  receipt_mismatch=True))
                lines, _ = orch.read_spool_lines(att.spool, 0)
                for row in lines:
                    if row.get('kind') == 'call_response':
                        usage = (row.get('body') or {}).get('usage') or {}
                        type(self).fake.count(att.server_id, usage.get('prompt_tokens', 0),
                                              usage.get('completion_tokens', 0))
                return None
        return super().finished(att)


def run_mismatch(tree, fake, *, hold_partner: bool, mutated: bool = False) -> str:
    MismatchAt44World.hold_partner = bool(hold_partner)
    patch = (mock.patch.object(orch.World, '_look_eligibility', look_988baf7) if mutated
             else mock.patch.object(orch, 'FIX_TEST_NOOP', None, create=True))
    with patch, mock.patch.object(sup, 'SupWorld', MismatchAt44World):
        return sup.run(tree, fake)


class AbortDrainCrossingInProcess(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def run(hold_partner: bool, mutated: bool = False):
            tree = cap.d3_tree()
            cls.trees.append(tree)
            status = run_mismatch(tree, sup.FakeServers(), hold_partner=hold_partner,
                                  mutated=mutated)
            return status, tree.events(), tree
        cls.drain = run(True)
        cls.same_pass = run(False)
        cls.same_pass_988baf7 = run(False, mutated=True)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def mismatch_seq(self, events) -> int:
        return next(e['seq'] for e in of(events, 'llm_response')
                    if e['body'].get('receipt_mismatch'))

    def test_the_drain_crossing_is_not_acted_on_never_live_decision_invalid(self):
        status, events, tree = self.drain
        self.assertEqual(status, 'aborted')
        self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'], 'receipt_mismatch')
        self.assertEqual(of(events, 'decision'), [])
        look = crossing(events)
        self.assertEqual((look['body']['shadow']['action'], look['body']['n']),
                         ('deploy_candidate', 44))
        self.assertGreater(look['seq'], self.mismatch_seq(events))
        self.assertEqual(tree.verify_fails(), [])
        rows = cap.verifier_rows(tree, 'reference_rule.agreement')
        self.assertEqual([(sev, row['consequence'], row['no_decision_reason'])
                          for sev, row in rows],
                         [('INFO', 'NOT_ACTED_ON_abort_before_decision', 'receipt_mismatch')])
        _summary, obj = cap.build(tree)
        self.assertEqual((obj['primary_result'], obj['reportable']),
                         (builder.ABORT_INCOMPLETE_LABEL, False))

    def test_negative_control_the_same_chain_read_without_the_point_is_a_disagreement(self):
        """What the verifier and the builder of 988baf7 said of this chain (they exempted the
        cap alone): the exemption is what changes the reading."""
        _status, _events, tree = self.drain
        real = lab_eventlog.no_decision_point
        only_cap = (lambda events, cap_, **kw: (
            lambda p: p if p is not None and p['reason'] == 'server_restart_cap' else None)(
                real(events, cap_, **kw)))
        with mock.patch.object(lab_eventlog, 'no_decision_point', only_cap):
            fails = [(c, d.get('consequence')) for c, d in tree.verify_fails()]
            _summary, obj = cap.build(tree)
        self.assertIn(('reference_rule.agreement', 'LIVE_DECISION_INVALID'), fails)
        self.assertEqual(lab_verify_log.condition_list('reference_rule.agreement'), 'B')
        self.assertEqual(obj['primary_result'], 'LIVE_DECISION_INVALID (harness defect)')

    def test_the_same_pass_crossing_now_takes_no_decision(self):
        """Both of pair 44 revealed in the pump pass that ingested the mismatch: the look
        follows the trigger in the chain, so it takes no decision (and the pump then aborts)."""
        status, events, tree = self.same_pass
        self.assertEqual((status, of(events, 'trial_aborted')[0]['body']['reason']),
                         ('aborted', 'receipt_mismatch'))
        self.assertEqual(of(events, 'decision'), [])
        self.assertGreater(crossing(events)['seq'], self.mismatch_seq(events))
        self.assertEqual(tree.verify_fails(), [])

    def test_mutation_988baf7_decided_after_the_trigger_and_is_caught(self):
        status, events, tree = self.same_pass_988baf7
        (decision,) = of(events, 'decision')
        self.assertGreater(decision['seq'], self.mismatch_seq(events))
        self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'], 'receipt_mismatch')
        fails = [(c, d.get('rule')) for c, d in tree.verify_fails()]
        self.assertIn(('reference_rule.agreement', 'decision_after_no_decision_point'), fails)


# --------------------------------------------------------------------------- #
# reviewer 1 finding 3: the cap abort superseded by unresolved_worker
# --------------------------------------------------------------------------- #
def _required_chain(terminal_body: dict, *, required: bool = True) -> list:
    specs = []
    for _ in range(CAP):
        specs += [('server_down', {'server_id': 'coder'}),
                  ('server_restarted', {'server_id': 'coder', 'props_equal_previous': True})]
    if required:
        specs.append(('server_down', {'server_id': 'coder'}))
    specs.append(('trial_aborted', terminal_body))
    return _chain(*specs)


def lifecycle_fails(events, cfg=SUPERVISION, arrivals=None) -> list:
    col = lab_verify_log._Collector(trial='T4', mode='full')
    lab_verify_log._check_server_lifecycle(col, events, cfg, arrivals)
    return [f.detail.get('rule') for f in col.findings
            if f.check == 'server.lifecycle' and f.severity == 'FAIL']


class CapSupersededTests(unittest.TestCase):

    def test_unresolved_worker_superseding_the_cap_is_the_cap_abort(self):
        body = {'reason': 'unresolved_worker',
                'resolution': {'superseded_reason': 'server_restart_cap'}}
        self.assertNotIn('cap_abort_iff_required', lifecycle_fails(_required_chain(body)))
        # the negative controls: another superseded reason is not the cap's abort, and a
        # "superseded cap" where the cap never bound is a cap abort that was not required
        other = {'reason': 'unresolved_worker',
                 'resolution': {'superseded_reason': 'receipt_mismatch'}}
        self.assertIn('cap_abort_iff_required', lifecycle_fails(_required_chain(other)))
        self.assertIn('cap_abort_iff_required',
                      lifecycle_fails(_required_chain(body, required=False)))
        self.assertNotIn('cap_abort_iff_required', lifecycle_fails(
            _required_chain({'reason': 'server_restart_cap'})))

    def test_the_production_chain_verifies(self):
        """Reviewer 1's reproduction: the cap binds at pair 44, whose hung workers' kill is
        never confirmed, so the close writes ``trial_aborted(unresolved_worker)`` superseding
        ``server_restart_cap`` -- which 988baf7's verifier FAILed (``cap_abort_iff_required``)."""
        tree = cap.d3_tree()
        self.addCleanup(tree.close)
        fake = sup.FakeServers()
        with mock.patch.object(sup.SupWorld, 'kill', lambda self, att: False):
            status = sup.run(tree, fake, hook=sup.CrashPlan(fake, pairs=(1, 2, 3, 44)),
                             stuck_pairs=(44,), episode_hard_cap_s=1.0)
        events = tree.events()
        self.assertEqual(status, 'aborted')
        (end,) = of(events, 'trial_aborted')
        self.assertEqual((end['body']['reason'], end['body']['resolution']['superseded_reason']),
                         ('unresolved_worker', 'server_restart_cap'))
        self.assertIn('alive_unresolved', {e['body']['state']
                                           for e in of(events, 'worker_resolved')})
        self.assertEqual(tree.verify_fails(), [])


# --------------------------------------------------------------------------- #
# reviewer 1 finding 4: an unresolved orphan found at resume is recorded
# --------------------------------------------------------------------------- #
def _drop_unresolved_records(real_append):
    """MUTATION (988baf7): the resume's refusal records nothing -- a ``worker_resolved`` of an
    unresolved state is not appended."""
    def append(self, etype, body, *, durable=False):
        if etype == 'worker_resolved' and body['state'] not in orch.RESOLVED_WORKER_STATES:
            return None
        return real_append(self, etype, body, durable=durable)
    return append


class ResumeUnresolvedInProcess(unittest.TestCase):

    def run_three(self, mutated: bool):
        tree = sup.Tree('T4', pairs=4)
        self.addCleanup(tree.close)
        fake = sup.FakeServers()

        polls = []

        def crash(world):
            # the orchestrator dies with pair 2 in flight, at the poll AFTER the pass that ran
            # its episodes (their spools exist; nothing of them is ingested yet)
            if world.pairs_enrolled == 2 and world.open_arrivals:
                polls.append(1)
                if len(polls) == 2:
                    fake.survive_stop = True
                    raise sup.Crash()
        self.assertEqual(sup.run(tree, fake, hook=crash), 'crashed')
        fake.survive_stop = False
        # the workers were mid-episode: each spool keeps its job_accepted and first
        # call_started only, so the resume reveals them ``interrupted`` (they RAN)
        events = tree.events()
        revealed = {e['body']['arrival'] for e in of(events, 'episode_revealed')}
        cut = 0
        for ev in of(events, 'episode_started'):
            if ev['body']['arrival'] in revealed:
                continue
            spool = tree.work / tree.trial / 'spools' / ('ep_%d_1.jsonl' % ev['body']['arrival'])
            lines = spool.read_bytes().split(b'\n')
            spool.write_bytes(b'\n'.join(lines[:2]) + b'\n')
            cut += 1
        self.assertEqual(cut, 2, 'both workers of pair 2 were in flight')
        first_len = len(events)
        real_append = orch.World.append
        patch = (mock.patch.object(orch.World, 'append', _drop_unresolved_records(real_append))
                 if mutated else mock.patch.object(orch, 'FIX_TEST_NOOP', None, create=True))
        # resume 1: the orphan is still that worker and its kill cannot be confirmed
        with patch, mock.patch.object(orch, 'probe_worker', lambda *a, **k: 'alive'), \
                mock.patch.object(orch, 'kill_orphan_worker',
                                  lambda *a, **k: ('alive_unresolved', None)):
            self.assertEqual(sup.run(tree, fake, resume=True), 'refused')
        second = tree.events()[first_len:]
        # resume 2: the orphan is gone
        with mock.patch.object(orch, 'probe_worker', lambda *a, **k: 'gone'):
            status = sup.run(tree, fake, resume=True)
        return status, second, tree.events(), tree

    def test_the_refusal_records_the_worker_and_the_phase_ends_incomplete(self):
        status, second, events, tree = self.run_three(False)
        states = [e['body']['state'] for e in second if e['type'] == 'worker_resolved']
        self.assertTrue(states and set(states) == {'alive_unresolved'}, states)
        self.assertEqual((second[-1]['type'], second[-1]['body']['status']),
                         ('invocation_ended', 'refused'))
        self.assertEqual(status, 'aborted')
        interrupted = [e for e in events if e['type'] == 'episode_revealed'
                       and e['body']['outcome'].get('error_class') == 'interrupted']
        self.assertEqual(len(interrupted), 2, 'the ran-and-now-gone workers are revealed')
        end = of(events, 'trial_aborted')[-1]
        self.assertEqual(end['body']['reason'], 'unresolved_worker')
        self.assertIn('worker_unresolved', end['body']['resolution']['problems'])
        self.assertEqual(of(events, 'trial_ended'), [])
        self.assertEqual(tree.verify_fails(), [], 'the chain says what happened')

    def test_mutation_the_unrecorded_refusal_lets_the_later_resume_end_the_trial(self):
        status, second, events, _tree = self.run_three(True)
        self.assertEqual([e for e in second if e['type'] == 'worker_resolved'
                          and e['body']['state'] == 'alive_unresolved'], [])
        self.assertEqual(status, 'ended', 'the same fact, the opposite terminal outcome')
        self.assertEqual(len(of(events, 'trial_ended')), 1)


# --------------------------------------------------------------------------- #
# reviewer 1, low: placeholders for observations never made
# --------------------------------------------------------------------------- #
class CounterDeltaTests(unittest.TestCase):

    def windows(self, *scrapes) -> list:
        events = _chain(
            ('server_started', {'server_id': 'coder',
                                'smoke': {'usage': {'prompt_tokens': 10,
                                                    'completion_tokens': 5}}}),
            ('llm_response', {'server_id': 'coder', 'arrival': 1,
                              'usage': {'prompt_tokens': 100, 'completion_tokens': 50}}),
            *scrapes)
        return orch.reconciliation_windows(events, ['coder'])

    def test_a_window_whose_counters_were_never_read_is_null_never_zero(self):
        failed = ('metrics_scrape', {'server_id': 'coder', 'ok': False, 'point': 'trial_end',
                                     'counters': {}})
        (w,) = self.windows(failed, failed)
        self.assertEqual((w['counter_delta'], w['counters_lost'], w['residual']),
                         ({'prompt': None, 'predicted': None}, True,
                          {'prompt': None, 'predicted': None}))
        self.assertEqual(w['client_usage_sum'], {'prompt': 110, 'predicted': 55})
        lab_eventlog.validate_event('usage_reconciliation', w)
        # negative control: a counter that WAS read is written, as an int
        read = ('metrics_scrape', {'server_id': 'coder', 'ok': True, 'point': 'pair_boundary',
                                   'counters': {'prompt_tokens_total': 7,
                                                'tokens_predicted_total': 3}})
        (w2,) = self.windows(read, failed)
        self.assertEqual(w2['counter_delta'], {'prompt': 7, 'predicted': 3})
        lab_eventlog.validate_event('usage_reconciliation', w2)


class UnreadableSpoolTests(unittest.TestCase):

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='fix_spool_'))
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_an_unreadable_spool_is_recorded_unread(self):
        unreadable = self.root / 'ep_2_1.jsonl'
        unreadable.mkdir()                              # read_bytes raises: unreadable
        body = orch._w__resolution_body(None, 2, 1, 4242, 'killed_reaped', None, unreadable)
        self.assertEqual((body['spool_bytes_at_resolution'],
                          body['spool_sha256_at_resolution']), (None, None))
        lab_eventlog.validate_event('worker_resolved', body)
        self.assertNotEqual(body['spool_sha256_at_resolution'], sha256_bytes(b''))
        # negative control: a readable spool is recorded as it is
        readable = self.root / 'ep_3_1.jsonl'
        readable.write_bytes(b'{"x": 1}\n')
        body = orch._w__resolution_body(None, 3, 1, 4243, 'exited', 0, readable)
        self.assertEqual((body['spool_bytes_at_resolution'],
                          body['spool_sha256_at_resolution']),
                         (9, sha256_bytes(b'{"x": 1}\n')))

    def test_the_verdict_and_the_verifier_fail_an_unread_spool(self):
        events = _chain(('episode_started', {'arrival': 2}),
                        ('worker_resolved', {'arrival': 2, 'attempt': 1, 'pid': 1,
                                             'state': 'exited', 'returncode': 0,
                                             'spool_bytes_at_resolution': None,
                                             'spool_sha256_at_resolution': None}))
        v = orch.phase_resolution_verdict(events, {'ep_2_1': {'bytes': 9, 'sha256': 'a' * 64,
                                                              'prefix_sha256': None}}, {})
        self.assertEqual((v['verdict'], v['problems']), ('FAIL', ['spool_unreadable']))
        self.assertEqual(v['late_spools'], [{'arrival': 2, 'attempt': 1,
                                             'bytes_at_resolution': None,
                                             'bytes_found': None}])
        recount = lab_verify_log._resolution_recount(events, [], v['late_spools'])
        self.assertEqual(recount['problems'], v['problems'], 'the two readings agree')


def seal(root: Path, events: list, spools: dict) -> tuple[dict, dict]:
    """``World.seal_deposit`` on a stub world whose chain is ``events`` and whose spool
    directory holds ``spools`` (stem -> bytes, or None for an unreadable entry)."""
    records = root / 'records'
    spool_dir = root / 'spools'
    records.mkdir(parents=True, exist_ok=True)
    spool_dir.mkdir(parents=True, exist_ok=True)
    for stem, data in spools.items():
        path = spool_dir / ('%s.jsonl' % stem)
        if data is None:
            path.mkdir()
        else:
            path.write_bytes(data)
    appended: list = []
    stub = SimpleNamespace(log=SimpleNamespace(events=events),
                           ctx=SimpleNamespace(paths=SimpleNamespace(records=records,
                                                                     spools=spool_dir)))
    stub.append = lambda etype, body, durable=False: appended.append((etype, body))
    stats = orch._w_seal_deposit(stub)
    ((etype, body),) = appended
    assert etype == 'deposit_sealed'
    lab_eventlog.validate_event('deposit_sealed', body)
    return body, stats


def resolved(arrival: int, data: bytes | None) -> dict:
    return {'arrival': arrival, 'attempt': 1, 'pid': 100 + arrival, 'state': 'exited',
            'returncode': 0,
            'spool_bytes_at_resolution': None if data is None else len(data),
            'spool_sha256_at_resolution': None if data is None else sha256_bytes(data)}


# --------------------------------------------------------------------------- #
# reviewer 2 finding 3: the seal's offsets and the verifier's re-check
# --------------------------------------------------------------------------- #
class SealAndSpoolRecheckTests(unittest.TestCase):

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='fix_seal_'))
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_the_seal_hashes_the_resolution_prefix_and_lists_the_late_bytes(self):
        data = b'{"spool_seq": 0}\n'
        events = _chain(('episode_started', {'arrival': 2}),
                        ('worker_resolved', resolved(2, data)))
        body, stats = seal(self.root / 'grew', events, {'ep_2_1': data + b'{"late": 1}\n'})
        self.assertEqual(body['late_unread'], [{'arrival': 2, 'attempt': 1,
                                                'bytes_at_resolution': len(data),
                                                'bytes_found': len(data) + 12}])
        # the deposit seals the PREFIX: the pre-EB5 whole-file digest is not what is sealed
        self.assertEqual(body['deposit_sha256'], sha256_canonical(
            {'records': [], 'spools': [sha256_bytes(data)]}))
        self.assertNotEqual(body['deposit_sha256'], sha256_canonical(
            {'records': [], 'spools': [sha256_bytes(data + b'{"late": 1}\n')]}))
        self.assertEqual(body['deposit_bytes'], len(data))
        v = orch.phase_resolution_verdict(events, stats, {})
        self.assertEqual((v['verdict'], v['problems']), ('FAIL', ['spool_grew']))
        # negative control: the spool as it was at resolution
        body, stats = seal(self.root / 'same', events, {'ep_2_1': data})
        self.assertEqual(body['late_unread'], [])
        self.assertEqual(orch.phase_resolution_verdict(events, stats, {})['verdict'], 'PASS')
        # an unreadable spool is sealed unread (null), never as an empty file
        body, _stats = seal(self.root / 'unread', events, {'ep_2_1': None})
        self.assertEqual(body['late_unread'], [{'arrival': 2, 'attempt': 1,
                                                'bytes_at_resolution': len(data),
                                                'bytes_found': None}])
        self.assertEqual(body['deposit_sha256'], sha256_canonical(
            {'records': [], 'spools': [None]}))

    def test_the_verifier_rechecks_every_resolved_spool_after_the_terminal_record(self):
        data = b'{"spool_seq": 0}\n'
        events = _chain(('episode_started', {'arrival': 2}),
                        ('worker_resolved', resolved(2, data)))
        spools = self.root / 'spools'
        spools.mkdir()
        path = spools / 'ep_2_1.jsonl'

        def rules():
            col = lab_verify_log._Collector(trial='T4', mode='full')
            lab_verify_log._check_workers_resolved(col, events, spools)
            return [f.detail.get('rule') for f in col.findings]
        path.write_bytes(data)
        self.assertNotIn('spool_after_resolution', rules(), 'negative control')
        path.write_bytes(data + b'late\n')
        self.assertIn('spool_after_resolution', rules())
        path.write_bytes(b'X' + data[1:])
        self.assertIn('spool_after_resolution', rules(), 'same length, other bytes')
        path.unlink()
        path.mkdir()
        self.assertIn('spool_after_resolution', rules(), 'unreadable')

    def test_in_process_bytes_after_a_resolution_are_late_and_refuse_the_phase(self):
        """The production close: pair 1's workers are resolved, then (at pair 2) bytes are
        appended to one of their spools; the seal lists them, the verdict fails
        ``spool_grew`` -> ``trial_aborted(unresolved_worker)``, and the verifier's re-check
        FAILs.  Negative control: the same run without the append ends ``trial_ended``."""
        def run(append: bool):
            tree = sup.Tree('T4', pairs=3)
            self.addCleanup(tree.close)
            fake = sup.FakeServers()
            done = []

            def hook(world):
                if append and not done and world.pairs_enrolled == 2:
                    rec = next(e['body'] for e in world.log.events
                               if e['type'] == 'worker_resolved')
                    spool = world.ctx.paths.spools / ('ep_%d_1.jsonl' % rec['arrival'])
                    with open(spool, 'ab') as fh:
                        fh.write(b'{"late": true}\n')
                    done.append(rec['arrival'])
            status = sup.run(tree, fake, hook=hook)
            return status, tree.events(), tree, done
        status, events, tree, done = run(True)
        self.assertEqual(status, 'aborted')
        end = of(events, 'trial_aborted')[-1]['body']
        self.assertEqual(end['reason'], 'unresolved_worker')
        self.assertIn('spool_grew', end['resolution']['problems'])
        (sealed,) = of(events, 'deposit_sealed')
        self.assertEqual([r['arrival'] for r in sealed['body']['late_unread']], done)
        fails = [(c, d.get('rule')) for c, d in tree.verify_fails()]
        self.assertIn(('workers.resolved', 'spool_after_resolution'), fails)
        status, events, tree, _done = run(False)
        self.assertEqual(status, 'ended')
        self.assertEqual(of(events, 'deposit_sealed')[0]['body']['late_unread'], [])
        self.assertEqual(tree.verify_fails(), [])


# --------------------------------------------------------------------------- #
# reviewer 2 finding 4: post_switch_after_cap and completion_record
# --------------------------------------------------------------------------- #
class LifecycleRuleControls(unittest.TestCase):

    def case_b(self, *, late_switch: bool) -> list:
        c = cap.Chain()
        c.decision()
        c.anchor(2, 'decision')
        c.receipt(2)
        if not late_switch:
            c.add('traffic_switch', decision_seq=0, arm='incumbent',
                  effective_from_arrival=3, anchor_wait_ms=0, switch_latency_ms=0)
        cap.three_restarts(c)
        c.down()
        if late_switch:
            c.add('traffic_switch', decision_seq=0, arm='incumbent',
                  effective_from_arrival=3, anchor_wait_ms=0, switch_latency_ms=0)
        return c.events

    def test_post_switch_after_cap_fires_and_its_control_is_silent(self):
        self.assertIn('post_switch_after_cap', lifecycle_fails(self.case_b(late_switch=True)))
        self.assertNotIn('post_switch_after_cap',
                         lifecycle_fails(self.case_b(late_switch=False)))

    def test_the_completion_record_is_recounted_field_by_field(self):
        events = self.case_b(late_switch=False)
        arrivals = [1, 2, 3, 4, 5, 6]
        rec = lab_eventlog.completion_record(events, arrivals, CAP, mock=False)
        good = events + [{'seq': len(events), 'type': 'trial_aborted', 'chain': 'T4',
                          'body': {'reason': 'server_restart_cap', 'completion': rec}}]
        self.assertNotIn('completion_record', lifecycle_fails(good, arrivals=arrivals))
        for field, value in (('follow_up_not_run', rec['follow_up_not_run'] + 1),
                             ('arrivals_not_run', rec['arrivals_not_run'] - 1),
                             ('restart_cap_case', 'before_decision')):
            with self.subTest(field=field):
                bad = [dict(e) for e in good]
                bad[-1] = dict(bad[-1], body=dict(bad[-1]['body'],
                                                  completion=dict(rec, **{field: value})))
                col = lab_verify_log._Collector(trial='T4', mode='full')
                lab_verify_log._check_server_lifecycle(col, bad, SUPERVISION, arrivals)
                rows = [f.detail for f in col.findings if f.detail.get('rule')
                        == 'completion_record']
                self.assertEqual([r.get('fields') for r in rows], [field])
        # a chain the cap bound in must carry the record
        bare = good[:-1] + [dict(good[-1], body={'reason': 'server_restart_cap'})]
        self.assertIn('completion_record', lifecycle_fails(bare, arrivals=arrivals))


class UsageFieldsCountTests(unittest.TestCase):

    def rules(self, unknown_calls: int) -> list:
        rid = sha256_text('fix-usage')[:32]
        events = _chain(('episode_started', {'arrival': 2}),
                        ('llm_request', {'arrival': 2, 'attempt': 1, 'request_id': rid}),
                        ('episode_revealed', {'arrival': 2, 'outcome': {'error_class': None},
                                              'usage_complete': False,
                                              'unknown_usage_calls': unknown_calls}))
        col = lab_verify_log._Collector(trial='T4', mode='full')
        lab_verify_log._check_workers_resolved(col, events, None)
        return [f.detail.get('rule') for f in col.findings]

    def test_a_wrong_count_with_the_right_flag_is_refused(self):
        self.assertIn('usage_fields', self.rules(5))
        self.assertNotIn('usage_fields', self.rules(1), 'negative control: the recount')


# --------------------------------------------------------------------------- #
# reviewer 2 (low): the runtime idle-wait override
# --------------------------------------------------------------------------- #
class IdleWaitOverrideTests(unittest.TestCase):

    def items(self, tree, **rt) -> set:
        with mock.patch.object(orch, 'WORLD_FACTORY', dry.SimWorld):
            try:
                orch.preflight(tree.ctx(sim=True, **rt))
            except lab_common.PreflightError as exc:
                return {r['item'] for r in getattr(exc, 'drift', [])}
        return set()

    def test_refused_outside_a_dry_run_tree_only(self):
        tree = sup.Tree('T4', pairs=2)
        self.addCleanup(tree.close)
        self.assertNotIn('runtime_resolution_idle_wait_override',
                         self.items(tree, resolution_idle_wait_s=2.0), 'a dry-run tree')
        tree.edit_config(lambda cfg: (cfg.pop('mock', None), cfg.pop('mock_overrides', None)))
        self.assertIn('runtime_resolution_idle_wait_override',
                      self.items(tree, resolution_idle_wait_s=2.0))
        self.assertNotIn('runtime_resolution_idle_wait_override', self.items(tree),
                         'negative control: no override')


# --------------------------------------------------------------------------- #
# reviewer 2 finding 6: the compiled test double's cache
# --------------------------------------------------------------------------- #
class FixtureCacheTests(unittest.TestCase):
    """Under an isolated temporary directory (never the shared cache)."""

    def setUp(self) -> None:
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix='fix_cache_')))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patcher = mock.patch.object(tempfile, 'tempdir', str(self.tmp))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_planted_cache_is_moved_aside_and_the_sources_compiled_again(self):
        cache = sm_fixture.compiled()
        self.assertEqual(sm_fixture.cache_problems(cache), [], 'the fresh compile verifies')
        uses = [json.loads(line) for line in
                (self.tmp / sm_fixture.USES_LOG).read_text('utf-8').splitlines()]
        self.assertEqual(uses[-1]['event'], 'compiled')
        self.assertEqual(uses[-1]['outputs']['llama-server'], sha256_bytes(
            (cache / 'llama-server').read_bytes()))
        # a launcher built from OTHER source (its marker differs), re-signed so it would run
        sm_fixture.flip(cache / 'llama-server', sm_fixture.LAUNCHER_MARKER, resign=True)
        planted = (cache / 'llama-server').read_bytes()
        self.assertIn('markers:llama-server', sm_fixture.cache_problems(cache))
        again = sm_fixture.compiled()
        self.assertEqual(again, cache)
        self.assertNotEqual((again / 'llama-server').read_bytes(), planted)
        self.assertEqual(sm_fixture.cache_problems(again), [])
        aside = [p for p in self.tmp.iterdir() if '.untrusted.' in p.name]
        self.assertEqual(len(aside), 1)
        self.assertEqual((aside[0] / 'llama-server').read_bytes(), planted)
        # a cache with no manifest at all (trusted by its name alone before this fix)
        (again / sm_fixture.CACHE_MANIFEST).unlink()
        self.assertEqual(sm_fixture.cache_problems(again), ['manifest_unreadable'])
        self.assertEqual(sm_fixture.cache_problems(sm_fixture.compiled()), [])
        self.assertEqual([json.loads(line)['event'] for line in
                          (self.tmp / sm_fixture.USES_LOG).read_text('utf-8').splitlines()],
                         ['compiled', 'compiled', 'compiled'])
        # negative control: an intact cache is used as it is
        before = (cache / 'llama-server').read_bytes()
        self.assertEqual((sm_fixture.compiled() / 'llama-server').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
