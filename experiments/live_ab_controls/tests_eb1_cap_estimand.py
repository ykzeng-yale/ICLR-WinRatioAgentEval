"""The restart-cap estimand of root's 21:14 ruling, encoded and controlled before outcomes.

Root, ``reviews/restart_cap_estimand_ruling_20260923_2114.md`` (origin/main ebcd637), which
WITHDREW the repair contract's reportability default ("no decision from any cap-aborted
trial"), and root 00:22 on "externally receipted".  The three cases, as encoded
(``lab_eventlog.restart_cap_case``; orchestrator, verifier and builder):

* (a) ``before_decision`` -- a fourth restart required before any decision: the trial aborts
  incomplete (``trial_aborted(server_restart_cap)``) and takes NO new decision, even when the
  monitor crosses during the drain (``World._write_one_look``); every attempt, band, failure
  and unknown usage is retained.
* (b) ``after_receipted_decision`` -- required after a decision whose blocking anchor carries
  its chained external receipt (protocol 12.4 item 5; the server time of claim 3 of 1.4, in a
  tree that is not a dry run): the decision and its original tau stand and are reportable;
  the follow-up is truncated and the unrun arrivals are counted.
* (c) ``decision_provisional`` -- required while the logged decision still awaits that
  receipt: nothing post-switch and no finalized claim until the existing receipt rule succeeds
  (``World.raise_pending`` defers, ``ANCHOR_BLOCK`` takes the owed abort only after the
  receipt); if it never succeeds, the existing anchor-failure rule of protocol 6.4 row 26
  (``trial_paused(anchor_unavailable)``) applies with the abort still owed, and a resume that
  obtains the receipt finalizes the decision.

Every behaviour here has a negative control beside it, and each orchestrator rule a MUTATION
control that removes exactly that rule and shows the chain it would have produced -- and that
the verifier FAILs that chain where it can.  Three kinds of run:

* pure functions on synthetic chains;
* the production ``run_trial`` / ``World`` in process on ``dryrun_live_ab``'s mock freeze tree,
  with ``tests_eb1_supervision``'s in-process ``lab_server`` (FakeServers), a SimWorld episode
  and in-process anchor receipts (gated here per trigger) -- fast, and able to crash a server at
  an exact state;
* the REAL production entry path, ``lab_orchestrator.py main()`` as a subprocess against
  ``lab_mock_server`` behind the EB1c shim (``tests_eb1_entry.EntryTree``), with the existing
  ``lab_anchor.py --mock-receipt`` anchor process: cases (b) and (c) (case (a) is
  ``tests_eb1_entry.C6RestartCap``).  To reach a decision on that path in bounded time the
  trees use T1 with the MOCK-ONLY screening prefix ``n_min = 30`` of ``dryrun_live_ab`` (recorded
  in the tree's ``mock_overrides``; the frozen ``n_min`` is 100): the mock serves a stub to
  every first code request and a fix to every repair, so the candidate (single_shot) fails
  and the incumbent (self_test_repair) succeeds in every pair and the frozen band crosses to
  ``harm_keep_incumbent`` at n = 39 (alpha, rho, delta and the band are the frozen ones).

Plus the cap-invariance controls (root item 2: the cap changes nothing in the monitor,
allocation, margin, scoring or first crossing; the five decision files are byte-unchanged
from b049307) and the model-file identity controls (item 3).

**Run the production-path classes alone, on a quiescent host**, as ``tests_eb1_entry`` (the
real host gate refuses a run while another suite's servers or workers are probed).

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_live_ab_results as builder                                 # noqa: E402
import dryrun_live_ab as dry                                            # noqa: E402
import lab_coin                                                         # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_verify_log                                                   # noqa: E402
import receipt_fixture as rf                                            # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402
from lab_common import canonical_json, sha256_file, sha256_text        # noqa: E402

CAP = 3
MOCK = True

#: protocol 5.7 item 2: the module runs under the prescribed TMPDIR, so every ``<TMP>`` token
#: (spool paths, the golden ``model_path``) resolves identically here, in the orchestrator
#: and in the workers -- as ``tests_eb1_entry`` does (its own two functions).
setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule


# --------------------------------------------------------------------------- #
# synthetic chains
# --------------------------------------------------------------------------- #
class Chain:
    """A synthetic event list of trial ``T4``: ``add(type, **body)`` numbers the events.

    Since root's f855e45 / 3e18d69 rulings a decision receipt must be bound to its anchor's
    request and carry its external evidence (``lab_eventlog.decision_receipt_problems``), so
    :meth:`anchor` writes a full anchor body with its ``request_id`` and :meth:`receipt` the
    body the orchestrator chains for a VERIFIED external receipt of that anchor (with
    ``created_at``) or for a MOCK receipt (``created_at=None``: no external evidence at all)
    -- ``receipt_fixture``; ``tests_eb1_receipt_attribution`` controls each clause."""

    TRIAL = 'T4'

    def __init__(self) -> None:
        self.events: list[dict] = []

    def add(self, etype: str, **body) -> int:
        seq = len(self.events)
        self.events.append({'seq': seq, 'type': etype, 'body': body, 'chain': self.TRIAL})
        return seq

    def down(self, sid: str = 'coder') -> int:
        return self.add('server_down', server_id=sid)

    def restart(self, sid: str = 'coder') -> int:
        return self.add('server_restarted', server_id=sid)

    def decision(self) -> int:
        return self.add('decision', kind='harm_keep_incumbent', n=39)

    def anchor(self, anchor_seq: int, trigger: str) -> int:
        return self.add('anchor', **rf.anchor_body(anchor_seq, trigger))

    def receipt(self, anchor_seq: int, created_at: str | None = '2026-09-23T21:14:00Z') -> int:
        anchor = next(e['body'] for e in self.events if e['type'] == 'anchor'
                      and e['body']['anchor_seq'] == anchor_seq)
        if created_at is None:
            return self.add('anchor_receipt', **rf.mock_receipt_body(anchor))
        return self.add('anchor_receipt', **rf.external_receipt_body(anchor, self.TRIAL,
                                                                     created_at=created_at))


def three_restarts(c: Chain) -> None:
    for _ in range(CAP):
        c.down()
        c.restart()


class EstimandFunctionTests(unittest.TestCase):
    """``lab_eventlog.decision_receipt`` / ``restart_cap_required_seq`` / ``restart_cap_case``
    / ``completion_record``: each case differs from its neighbour in ONE event's position."""

    def test_the_cap_binds_at_the_down_that_finds_the_server_at_the_cap(self):
        c = Chain()
        three_restarts(c)
        self.assertIsNone(lab_eventlog.restart_cap_required_seq(c.events, CAP),
                          'three downs answered by three restarts: the cap has not bound')
        fourth = c.down()
        self.assertEqual(lab_eventlog.restart_cap_required_seq(c.events, CAP), fourth)
        self.assertIsNone(lab_eventlog.restart_cap_required_seq(c.events, None),
                          'a simulated run (no cap) never binds')
        # a failed restart counts as an attempted restart; a failed START does not
        c2 = Chain()
        for _ in range(CAP):
            c2.down()
            c2.add('server_start_failed', server_id='coder', kind='restart')
        self.assertEqual(lab_eventlog.restart_cap_required_seq(c2.events + [
            {'seq': 99, 'type': 'server_down', 'body': {'server_id': 'coder'}}], CAP), 99)
        c3 = Chain()
        c3.add('server_start_failed', server_id='coder', kind='start')
        c3.down()
        self.assertIsNone(lab_eventlog.restart_cap_required_seq(c3.events, 0 + 1))

    def test_a_decision_is_receipted_only_by_its_own_anchors_receipt(self):
        c = Chain()
        c.anchor(1, 'trial_started')
        c.receipt(1)
        self.assertEqual(lab_eventlog.decision_receipt(c.events, mock=False)['status'], 'none')
        d = c.decision()
        c.anchor(2, 'decision')
        got = lab_eventlog.decision_receipt(c.events, mock=False)
        self.assertEqual((got['status'], got['decision_seq'], got['anchor_seqs']),
                         ('provisional', d, [2]), 'a local decision event alone')
        # negative control: a receipt answering ANOTHER anchor is not the decision's
        c.receipt(1)
        self.assertEqual(lab_eventlog.decision_receipt(c.events, mock=False)['status'],
                         'provisional')
        c.add('anchor_failed', anchor_seq=2, error_class='timeout', blocking=True)
        got = lab_eventlog.decision_receipt(c.events, mock=False)
        self.assertEqual((got['status'], len(got['failed_seqs'])), ('provisional', 1))
        # a resumed invocation's second decision anchor, receipted with the server time
        c.anchor(3, 'decision')
        r = c.receipt(3)
        got = lab_eventlog.decision_receipt(c.events, mock=False)
        self.assertEqual((got['status'], got['receipt_seq'], got['server_time']),
                         ('receipted', r, '2026-09-23T21:14:00Z'))
        self.assertEqual(lab_eventlog.decision_receipt(c.events, mock=False,
                                                       before_seq=r)['status'], 'provisional')

    def test_a_receipt_without_the_server_time_counts_only_in_a_mock_tree(self):
        c = Chain()
        c.decision()
        c.anchor(2, 'decision')
        c.receipt(2, created_at=None)
        self.assertEqual(lab_eventlog.decision_receipt(c.events, mock=True)['status'],
                         'receipted')
        self.assertEqual(lab_eventlog.decision_receipt(c.events, mock=False)['status'],
                         'provisional')

    def cases(self) -> dict:
        """The four placements of the fourth down around one decision and its receipt."""
        out = {}
        c = Chain()
        three_restarts(c)
        c.down()
        c.decision()                                   # (a) with a (forbidden) late decision
        out['before_decision'] = c.events
        c = Chain()
        three_restarts(c)
        c.decision()
        c.anchor(2, 'decision')
        c.receipt(2)
        c.down()
        out['after_receipted_decision'] = c.events
        c = Chain()
        three_restarts(c)
        c.decision()
        c.anchor(2, 'decision')
        c.down()
        c.receipt(2)
        out['decision_provisional'] = c.events
        c = Chain()
        c.decision()
        c.anchor(2, 'decision')
        c.receipt(2)
        c.down()
        out['none'] = c.events
        return out

    def test_the_three_cases_and_none(self):
        for case, events in self.cases().items():
            with self.subTest(case=case):
                got = lab_eventlog.restart_cap_case(events, CAP, mock=False)
                self.assertEqual(got['case'], case)
                # the case (a) chain's late decision has no anchor: provisional
                self.assertEqual(got['decision']['status'],
                                 'provisional' if case == 'before_decision' else 'receipted')
        a = lab_eventlog.restart_cap_case(self.cases()['before_decision'], CAP, mock=False)
        self.assertEqual(a['decision_after_cap_seq'], a['cap_required_seq'] + 1)
        c = lab_eventlog.restart_cap_case(self.cases()['decision_provisional'], CAP, mock=False)
        self.assertIsNone(c['decision_after_cap_seq'])
        self.assertEqual(c['decision']['status'], 'receipted', 'receipted AFTER the cap')

    def test_completion_counts_arrivals_run_and_follow_up_not_run(self):
        c = Chain()
        c.add('coin_drawn', pair=1, assignment={'1': 'candidate', '2': 'incumbent'})
        c.add('episode_started', arrival=1)
        c.add('episode_started', arrival=2)
        c.decision()
        c.anchor(2, 'decision')
        c.receipt(2)
        c.add('arm_assigned_by_decision', arrival=3)
        c.add('episode_started', arrival=3)
        c.add('arm_assigned_by_decision', arrival=4)          # assigned, never started
        three_restarts(c)
        required = c.down()
        rec = lab_eventlog.completion_record(c.events, [1, 2, 3, 4, 5, 6], CAP, mock=False)
        self.assertEqual(rec, {
            'restart_cap_case': 'after_receipted_decision', 'cap_required_seq': required,
            'decision_seq': 3, 'decision_status': 'receipted', 'decision_receipt_seq': 5,
            'decision_receipt_server_time': '2026-09-23T21:14:00Z',
            'arrivals_total': 6, 'arrivals_run': 3, 'arrivals_not_run': 3,
            'follow_up_run': 1, 'follow_up_not_run': 2})
        lab_eventlog.validate_event('trial_aborted', {
            'status': 'aborted', 'reason': 'server_restart_cap', 'phase': 'post_decision',
            'exposure_ledger': {}, 'reconciliation_totals': {},
            'terminal_failures_by_arm': {}, 'n_torn_recoveries': 0,
            'longest_unreceipted_span_s': 0.0,
            'what_was_known': self.what_was_known(), 'final_head': '0' * 64,
            'completion': rec})
        # negative control: no decision -> no follow-up count; the schema is closed
        rec2 = lab_eventlog.completion_record(c.events[:3], [1, 2, 3], CAP, mock=False)
        self.assertEqual((rec2['restart_cap_case'], rec2['follow_up_not_run'],
                          rec2['arrivals_not_run']), ('none', None, 1))
        with self.assertRaises(lab_common.SchemaError):
            lab_eventlog.validate_event('trial_ended', {
                'status': 'ended', 'reason': None, 'phase': 'randomizing',
                'exposure_ledger': {}, 'reconciliation_totals': {},
                'terminal_failures_by_arm': {}, 'n_torn_recoveries': 0,
                'longest_unreceipted_span_s': 0.0,
                'what_was_known': self.what_was_known(), 'final_head': '0' * 64,
                'completion': dict(rec2, restart_cap_case='cap_ignored')})

    @staticmethod
    def what_was_known() -> dict:
        return {'pairs_enrolled': 0, 'pairs_completed': 0,
                'revealed_by_arm': {'incumbent': 0, 'candidate': 0},
                'L_h': -1.0, 'U_h': 1.0, 'L_s': -1.0, 'U_s': 1.0, 'distance_to_harm': 1.0,
                'distance_to_deploy_h': -1.0, 'distance_to_deploy_s': -0.97,
                'earlier_trials': []}


# --------------------------------------------------------------------------- #
# in process: the production run_trial / World with gated anchor receipts
# --------------------------------------------------------------------------- #
def write_receipt(paths, request_id: str, *, ok: bool) -> None:
    """One line of ``anchor_spool/receipts.jsonl`` in ``lab_anchor``'s MOCK shape (no commit,
    no comment, no server time)."""
    path = paths.anchor_spool / 'receipts.jsonl'
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(canonical_json({
            'request_id': request_id, 'ok': bool(ok), 'commit': None, 'branch': None,
            'pushed': False, 'comment_id': None, 'created_at': None, 'updated_at': None,
            'receipt_sha256': sha256_text(request_id) if ok else None,
            'error_class': None if ok else 'timeout'}) + '\n')


class GatedWorld(sup.SupWorld):
    """``SupWorld`` whose in-process anchor answers each request at once EXCEPT the triggers
    in ``hold`` (never answered in this invocation) and ``fail`` (answered ``ok: false``, as
    ``lab_anchor`` does after its blocking retry window)."""

    hold: frozenset = frozenset()
    fail: frozenset = frozenset()

    def request_anchor(self, trigger, *, blocking):
        orch.World.request_anchor(self, trigger, blocking=blocking)
        if trigger in type(self).hold:
            return
        write_receipt(self.ctx.paths, self.pending_anchor['request_id'],
                      ok=trigger not in type(self).fail)


def run_gated(tree, fake, *, hook=None, hold=(), fail=(), resume=False, **rt) -> str:
    GatedWorld.hold = frozenset(hold)
    GatedWorld.fail = frozenset(fail)
    with mock.patch.object(sup, 'SupWorld', GatedWorld):
        return sup.run(tree, fake, hook=hook, resume=resume, **rt)


def d3_tree(pairs: int = 50) -> sup.Tree:
    """``dryrun_live_ab``'s D3 setting (mock-only delta 0.9, n_min 25): the candidate is faster
    at equal success and the frozen band deploys at n = 44 of 50 pairs."""
    return sup.Tree('T4', pairs=pairs, delta=0.9, n_min=25)


class CrashWhenProvisional:
    """After the three restarts of ``sup.CrashPlan(pairs=(1, 2, 3))``: crash the server at the
    first health poll that sees a logged decision WITHOUT its chained receipt (read from the
    chain, never from the world's cache)."""

    def __init__(self, fake) -> None:
        self.fake = fake
        self.first = sup.CrashPlan(fake, pairs=(1, 2, 3))
        self.fired = False

    def __call__(self, world) -> None:
        self.first(world)
        if self.fired or world.decision is None:
            return
        if lab_eventlog.decision_receipt(world.log.events, mock=True)['status'] == 'receipted':
            return
        self.fired = True
        self.first.fire()


def old_raise_pending(self) -> None:
    """MUTATION: ``World.raise_pending`` of 1dd9df2, without the case-(c) deferral."""
    if self.open_arrivals:
        return
    if self.pending_abort is not None:
        raise orch.AbortTrial(self.pending_abort)
    if self.pending_pause is not None:
        raise orch.PauseTrial(self.pending_pause)


_REAL_STEP = orch._step


def old_anchor_block_step(state, ctx, world):
    """MUTATION: the ``ANCHOR_BLOCK`` state of b049307/1dd9df2, verbatim: it switched as soon as
    no anchor was pending, whether the decision anchor came back receipted or failed."""
    if state != 'ANCHOR_BLOCK':
        return _REAL_STEP(state, ctx, world)
    world.ingest_receipts()
    if world.pending_anchor is not None:
        if world.anchor_timed_out():
            world.pause_reason = 'anchor_unavailable'
            return 'PAUSED'
        return 'ANCHOR_BLOCK'
    assert world.decision is not None
    if world.decision['kind'] == 'horizon_no_decision':
        return 'CLOSING'
    world.write_traffic_switch()
    return 'POST_DECISION'


def old_ingest_receipts(self) -> bool:
    """MUTATION: ``World.ingest_receipts`` of 1dd9df2, verbatim: every line under the newest
    anchor's seq, re-chained whenever the spool is re-read."""
    path = self.ctx.paths.anchor_spool / 'receipts.jsonl'
    lines, self.receipt_offset = orch.read_spool_lines(path, self.receipt_offset)
    got = False
    for row in lines:
        pending = self.pending_anchor
        anchor_seq = self.anchor_seq
        if pending is not None and row.get('request_id') == pending['request_id']:
            got = True
            self.pending_anchor = None
        if row.get('ok'):
            self.append('anchor_receipt', {
                'anchor_seq': anchor_seq, 'pushed': bool(row.get('pushed')),
                'comment_id': (int(row['comment_id'])
                               if row.get('comment_id') is not None else None),
                'created_at': row.get('created_at'), 'updated_at': row.get('updated_at'),
                'receipt_sha256': str(row.get('receipt_sha256')
                                      or lab_common.sha256_canonical(row)),
                'commit_sha256': sha256_text(str(row.get('commit') or ''))}, durable=True)
            self.receipts_obtained += 1
        else:
            self.append('anchor_failed', {
                'anchor_seq': anchor_seq, 'error_class': str(row.get('error_class') or 'api'),
                'blocking': bool(pending['blocking']) if pending else False}, durable=True)
    return got


def old_decision_receipt(events, *, mock: bool, before_seq=None) -> dict:
    """MUTATION: ``lab_eventlog.decision_receipt`` of 8df2558, verbatim but for its docstring:
    any ``anchor_receipt`` carrying a decision anchor's ``anchor_seq`` and (outside a MOCK tree)
    a ``created_at`` counted -- root f855e45 / 3e18d69 replaced it (no request binding, no
    push/comment/``node_id`` evidence).  Paired with :func:`old_ingest_receipts`, whose
    receipts carry no ``request_id`` and so can never satisfy the current rule: alone, that
    ingest would re-request the decision anchor for ever."""
    evs = [e for e in events if before_seq is None or int(e['seq']) < int(before_seq)]
    out: dict = {'status': 'none', 'decision_seq': None, 'anchor_seqs': [],
                 'receipt_seq': None, 'server_time': None, 'failed_seqs': []}
    decision = next((e for e in evs if e['type'] == 'decision'), None)
    if decision is None:
        return out
    dseq = int(decision['seq'])
    anchors: dict[int, int] = {}
    for ev in evs:
        if int(ev['seq']) <= dseq:
            continue
        body = ev.get('body') or {}
        if ev['type'] == 'anchor' and body.get('trigger') == 'decision':
            anchors.setdefault(int(body['anchor_seq']), int(ev['seq']))
        elif ev['type'] == 'anchor_receipt' and int(body.get('anchor_seq', -1)) in anchors:
            if out['receipt_seq'] is None and (mock or body.get('created_at') is not None):
                out['receipt_seq'] = int(ev['seq'])
                out['server_time'] = body.get('created_at')
        elif ev['type'] == 'anchor_failed' and int(body.get('anchor_seq', -1)) in anchors:
            out['failed_seqs'].append(int(ev['seq']))
    out.update(status='receipted' if out['receipt_seq'] is not None else 'provisional',
               decision_seq=dseq, anchor_seqs=sorted(anchors))
    return out


_REAL_ELIGIBILITY = orch.World._look_eligibility


def look_without_case_a(self, trigger):
    """MUTATION: the look gate (``World._look_eligibility``, the orchestrator's call of
    ``lab_eventlog.decision_eligibility``) without the case-(a) rule: a look whose ONLY reason
    is the cap -- the cap's point (``server_restart_cap``: the ``server_down`` that required the
    fourth restart) or the cap's own ``abort_owed`` -- is let take a decision."""
    got = _REAL_ELIGIBILITY(self, trigger)
    point = self.no_decision or {}
    if not got['eligible'] and (
            got['reason'] == 'server_restart_cap'
            or (got['reason'] == 'abort_owed'
                and point.get('abort_reason') == orch.RESTART_CAP_REASON)):
        return {'eligible': True, 'reason': None}
    return got


def build(tree: sup.Tree) -> tuple[dict, dict]:
    out = tree.root / ('built_%d' % time.monotonic_ns())
    summary = builder.build([tree.trial], tree.bundle_sha, results_root=tree.results,
                            work_root=tree.work, out_dir=out, mock=True)
    return summary, json.loads((out / tree.trial / 'decision.json').read_text('utf-8'))


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


def verifier_rows(tree: sup.Tree, check: str) -> list:
    report = lab_verify_log.verify_trial(tree.trial, tree.bundle_sha, mode='full',
                                         results_root=tree.results, work_root=tree.work)
    return [(f.severity, dict(f.detail)) for f in report.findings if f.check == check]


class CaseAInProcess(unittest.TestCase):
    """Case (a): the fourth down is required while pair 44 -- the pair whose reveal crosses the
    frozen band in the uncapped run -- is in flight.  The drain reveals it and the monitor
    logs the crossing look exactly as it would without the cap (``shadow.action`` deploy), but
    NO decision is taken; the trial ends ``trial_aborted(server_restart_cap)``, the builder
    reports it incomplete (no decision, not a null) and names the crossing not acted on, and
    the verifier labels the case and fails nothing.  Mutation control: without the rule the
    same run appends a decision after the cap -- which the verifier FAILs
    (``decision_after_cap``) and the builder refuses to report."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def make(mutated: bool):
            tree = d3_tree()
            cls.trees.append(tree)
            fake = sup.FakeServers()
            patch = (mock.patch.object(orch.World, '_look_eligibility', look_without_case_a)
                     if mutated else mock.patch.object(orch, 'CAP_TEST_NOOP', None,
                                                       create=True))
            with patch:
                status = sup.run(tree, fake, hook=sup.CrashPlan(fake, pairs=(1, 2, 3, 44)))
            return status, tree.events(), tree
        cls.real = make(False)
        cls.mutant = make(True)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def test_the_crossing_during_the_cap_drain_is_logged_and_not_acted_on(self):
        status, events, tree = self.real
        self.assertEqual(status, 'aborted')
        self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'], 'server_restart_cap')
        required = lab_eventlog.restart_cap_required_seq(events, CAP)
        self.assertIsNotNone(required)
        crossing = [e for e in of(events, 'monitor_update')
                    if e['body']['shadow']['action'] != 'none']
        self.assertTrue(crossing, 'the fixture must cross during the drain')
        self.assertGreater(crossing[0]['seq'], required)
        self.assertEqual((crossing[0]['body']['shadow']['action'], crossing[0]['body']['n']),
                         ('deploy_candidate', 44))
        self.assertEqual(of(events, 'decision'), [], 'no new decision (case a)')
        comp = of(events, 'trial_aborted')[0]['body']['completion']
        self.assertEqual((comp['restart_cap_case'], comp['decision_status'],
                          comp['follow_up_not_run']), ('before_decision', 'none', None))
        self.assertEqual(comp['arrivals_not_run'],
                         100 - len({e['body']['arrival'] for e in of(events, 'episode_started')}))
        summary, decision = build(tree)
        self.assertEqual((decision['primary_result'], decision['reportable']),
                         (builder.RESTART_CAP_INCOMPLETE_LABEL, False))
        self.assertEqual(decision['crossing_not_acted_on']['kind'], 'deploy_candidate')
        self.assertEqual(decision['crossing_not_acted_on']['n'], 44)
        self.assertIs(decision['agreement_kind_and_prefix'], True)
        self.assertEqual(summary['trials']['T4']['restart_cap_case'], 'before_decision')
        self.assertEqual(tree.verify_fails(), [])
        agreement = verifier_rows(tree, 'reference_rule.agreement')
        self.assertEqual([(sev, row['consequence']) for sev, row in agreement],
                         [('INFO', 'NOT_ACTED_ON_restart_cap_before_decision')])
        self.assertIn(('INFO', 'before_decision'),
                      [(sev, row.get('case')) for sev, row in
                       verifier_rows(tree, 'server.lifecycle')])

    def test_mutation_without_the_rule_decides_after_the_cap_and_fails_the_verifier(self):
        status, events, tree = self.mutant
        self.assertEqual(status, 'aborted')
        required = lab_eventlog.restart_cap_required_seq(events, CAP)
        (decision,) = of(events, 'decision')
        self.assertGreater(decision['seq'], required, 'a decision AFTER the cap was required')
        fails = [d.get('rule') for c, d in tree.verify_fails() if c == 'server.lifecycle']
        self.assertIn('decision_after_cap', fails)
        _, obj = build(tree)
        self.assertEqual((obj['primary_result'], obj['reportable']),
                         (builder.RESTART_CAP_INCOMPLETE_LABEL, False))
        self.assertTrue(obj['decision_label'].startswith('not reportable: logged after'))

    def test_control_the_uncapped_run_decides_at_the_same_crossing(self):
        tree = d3_tree()
        self.addCleanup(tree.close)
        fake = sup.FakeServers()
        self.assertEqual(sup.run(tree, fake, hook=sup.CrashPlan(fake, pairs=(1, 2, 3))),
                         'ended')
        (decision,) = of(tree.events(), 'decision')
        self.assertEqual((decision['body']['kind'], decision['body']['n']),
                         ('deploy_candidate', 44))


class CaseCInProcess(unittest.TestCase):
    """Case (c): the fourth down is required at the first health poll after the decision,
    while its blocking anchor has not been answered (the in-process anchor holds the
    ``decision`` request).  The abort is NOT taken: no ``traffic_switch``, no follow-up
    dispatch; the existing anchor-failure rule times out into ``trial_paused(
    anchor_unavailable)`` with the abort still owed and the decision provisional (not
    reportable).  The resume ingests the late receipt of that same request -- attributed to
    the decision's own anchor -- and only then takes the owed ``trial_aborted(
    server_restart_cap)``: the decision is finalized at its original tau and the follow-up
    is counted as not run.  Mutation control: without the deferral the abort supersedes the
    decision anchor and the trial ends with a decision that can never be receipted."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def first(mutated: bool):
            tree = d3_tree()
            cls.trees.append(tree)
            fake = sup.FakeServers()
            patch = (mock.patch.object(orch.World, 'raise_pending', old_raise_pending)
                     if mutated else mock.patch.object(orch, 'CAP_TEST_NOOP', None,
                                                       create=True))
            with patch:
                status = run_gated(tree, fake, hook=CrashWhenProvisional(fake),
                                   hold={'decision'}, blocking_wait_s=0.5)
            return status, tree.events(), tree, fake
        cls.real = first(False)
        cls.mutant = first(True)
        status, events, tree, fake = cls.real
        cls.paused = (status, list(events))
        # the channel returns: the anchor process answers the held request late
        held = [json.loads(line) for line in
                (tree.work / tree.trial / 'anchor_spool' / 'requests.jsonl')
                .read_text('utf-8').splitlines() if line.strip()]
        cls.held = [r for r in held if r['trigger'] == 'decision']
        paths = orch._trial_paths(tree.trial, tree.results, tree.work)
        for req in cls.held:
            write_receipt(paths, req['request_id'], ok=True)
        cls.resumed = (run_gated(tree, fake, resume=True, blocking_wait_s=0.5), tree.events())

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def test_the_owed_abort_waits_and_the_anchor_failure_rule_pauses(self):
        status, events = self.paused
        self.assertEqual(status, 'paused')
        required = lab_eventlog.restart_cap_required_seq(events, CAP)
        dseq = of(events, 'decision')[0]['seq']
        self.assertGreater(required, dseq)
        self.assertEqual(lab_eventlog.restart_cap_case(events, CAP, mock=MOCK)['case'],
                         'decision_provisional')
        self.assertEqual(lab_eventlog.decision_receipt(events, mock=MOCK)['status'],
                         'provisional')
        self.assertEqual(of(events, 'trial_paused')[-1]['body']['reason_code'],
                         'anchor_unavailable')
        for etype in ('traffic_switch', 'arm_assigned_by_decision', 'trial_aborted',
                      'trial_ended'):
            self.assertEqual(of(events, etype), [], etype)
        self.assertEqual([e['type'] for e in events if e['seq'] > required
                          and e['type'] == 'episode_started'], [])
        state = orch.supervision_state(events, CAP)
        self.assertEqual(state.pending_abort, orch.RESTART_CAP_REASON, 'still owed')
        self.assertEqual(len(self.held), 1)
        tree = self.real[2]
        obj = builder.decision_object(events, tree.frozen_cfg(), 'T4')
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['restart_cap']['case']),
                         (builder.PROVISIONAL_LABEL, False, 'decision_provisional'))

    def test_the_resume_obtains_the_receipt_then_takes_the_owed_abort(self):
        status, events = self.resumed
        self.assertEqual(status, 'aborted')
        (aborted,) = of(events, 'trial_aborted')
        self.assertEqual(aborted['body']['reason'], 'server_restart_cap')
        receipt = lab_eventlog.decision_receipt(events, mock=MOCK)
        self.assertEqual(receipt['status'], 'receipted')
        decision_event = of(events, 'decision')[0]
        first_anchor = next(e for e in of(events, 'anchor')
                            if e['body']['trigger'] == 'decision')
        self.assertEqual(receipt['anchor_seqs'], [first_anchor['body']['anchor_seq']],
                         'the late receipt answers the decision\'s OWN anchor; none was re-requested')
        self.assertLess(receipt['receipt_seq'], aborted['seq'])
        self.assertGreater(receipt['receipt_seq'], of(events, 'invocation_started')[0]['seq'])
        self.assertEqual(of(events, 'traffic_switch') + of(events, 'arm_assigned_by_decision'),
                         [], 'nothing post-switch: the follow-up is truncated whole')
        self.assertEqual(len(of(events, 'decision')), 1)
        self.assertEqual(decision_event, of(self.paused[1], 'decision')[0],
                         'the decision event, its tau and its band are unchanged')
        comp = aborted['body']['completion']
        assigned = sup.assigned_arrivals(events)
        self.assertEqual((comp['restart_cap_case'], comp['decision_status'],
                          comp['follow_up_run'], comp['follow_up_not_run']),
                         ('decision_provisional', 'receipted', 0, 100 - len(assigned)))
        tree = self.real[2]
        summary, obj = build(tree)
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision']['n']),
                         ('deploy_candidate', True, 44))
        self.assertIn('provisional when the cap bound, receipted afterwards',
                      obj['decision_label'])
        self.assertEqual(summary['trials']['T4']['follow_up_not_run'], 100 - len(assigned))
        self.assertEqual(tree.verify_fails(), [])
        # every anchor receipt chained once (the resume re-read the spool from its start)
        seqs = [e['body']['anchor_seq'] for e in of(events, 'anchor_receipt')]
        self.assertEqual(len(seqs), len(set(seqs)))

    def test_mutation_without_the_deferral_aborts_over_the_pending_receipt(self):
        status, events, tree, _ = self.mutant
        self.assertEqual(status, 'aborted')
        self.assertEqual(lab_eventlog.restart_cap_case(events, CAP, mock=MOCK)['case'],
                         'decision_provisional', 'the same situation as the real run')
        (aborted,) = of(events, 'trial_aborted')
        self.assertEqual(aborted['body']['reason'], 'server_restart_cap')
        self.assertEqual(lab_eventlog.decision_receipt(events, mock=MOCK)['status'],
                         'provisional', 'terminal with the decision never receipted')
        self.assertEqual(of(events, 'trial_paused'), [])
        _, obj = build(tree)
        self.assertEqual((obj['primary_result'], obj['reportable']),
                         (builder.PROVISIONAL_LABEL, False))


class AnchorFailureTests(unittest.TestCase):
    """Case (c)'s "no post-switch dispatch without the receipt", independent of the cap: the
    decision's blocking anchor comes back ``ok: false`` (the anchor process exhausted its
    retry window).  The existing rule of protocol 6.4 row 26 applies: ``trial_paused(
    anchor_unavailable)``, no switch.  Mutation control: b049307's ``ANCHOR_BLOCK`` switched
    and dispatched the follow-up with no receipt, which the verifier now FAILs
    (``switch_before_decision_receipt``)."""

    def run_one(self, mutated: bool):
        tree = d3_tree()
        self.addCleanup(tree.close)
        fake = sup.FakeServers()
        patch = (mock.patch.object(orch, '_step', old_anchor_block_step) if mutated
                 else mock.patch.object(orch, 'CAP_TEST_NOOP', None, create=True))
        with patch:
            status = run_gated(tree, fake, fail={'decision'}, blocking_wait_s=0.5)
        return status, tree.events(), tree

    def test_a_failed_decision_anchor_pauses_and_never_switches(self):
        status, events, tree = self.run_one(False)
        self.assertEqual(status, 'paused')
        self.assertEqual(of(events, 'trial_paused')[-1]['body']['reason_code'],
                         'anchor_unavailable')
        self.assertEqual(len(of(events, 'anchor_failed')), 1)
        self.assertEqual(of(events, 'traffic_switch') + of(events, 'arm_assigned_by_decision'),
                         [])
        self.assertEqual(tree.verify_fails(), [])

    def test_mutation_the_old_anchor_block_switches_without_a_receipt(self):
        status, events, tree = self.run_one(True)
        self.assertEqual(status, 'ended')
        self.assertTrue(of(events, 'traffic_switch') and of(events, 'arm_assigned_by_decision'))
        self.assertEqual(lab_eventlog.decision_receipt(events, mock=MOCK)['status'],
                         'provisional')
        fails = [d.get('rule') for c, d in tree.verify_fails() if c == 'server.lifecycle']
        self.assertIn('switch_before_decision_receipt', fails)


class ReceiptIngestTests(unittest.TestCase):
    """The case of a chain is decided by WHICH anchor a receipt answers.  A resumed invocation
    re-reads the receipt spool from its start; each line is chained under the anchor_seq of
    the request it answers and at most once.  Mutation control: 1dd9df2's ingest re-chained
    every old line under the newest anchor's seq -- the start anchor's receipt then "answers"
    the decision anchor a resume requests.  The mutation restores 1dd9df2/8df2558's receipt
    path whole (:func:`old_ingest_receipts` with :func:`old_decision_receipt`, the gate it was
    paired with; see ``tests_eb1_receipt_attribution`` for the attribution itself)."""

    def run_pair(self, mutated: bool):
        tree = d3_tree(pairs=6)
        self.addCleanup(tree.close)
        fake = sup.FakeServers()

        def crash(world):                      # the orchestrator dies mid-trial
            if world.pairs_enrolled == 3 and world.open_arrivals:
                fake.survive_stop = True
                raise sup.Crash()
        patch = (mock.patch.object(orch.World, 'ingest_receipts', old_ingest_receipts)
                 if mutated else mock.patch.object(orch, 'CAP_TEST_NOOP', None, create=True))
        gate = (mock.patch.object(lab_eventlog, 'decision_receipt', old_decision_receipt)
                if mutated else mock.patch.object(orch, 'CAP_TEST_NOOP2', None, create=True))
        with patch, gate:
            self.assertEqual(sup.run(tree, fake, hook=crash), 'crashed')
            fake.survive_stop = False
            self.assertEqual(sup.run(tree, fake, resume=True), 'ended')
        return tree.events()

    def test_a_resume_chains_each_receipt_once_under_its_own_anchor(self):
        events = self.run_pair(False)
        by_anchor: dict = {}
        for e in of(events, 'anchor_receipt'):
            by_anchor.setdefault(e['body']['anchor_seq'], []).append(e['seq'])
        self.assertEqual(sorted(by_anchor), sorted(e['body']['anchor_seq']
                                                   for e in of(events, 'anchor')))
        self.assertTrue(all(len(v) == 1 for v in by_anchor.values()), by_anchor)
        for e in of(events, 'anchor_receipt'):
            anchor = next(a for a in of(events, 'anchor')
                          if a['body']['anchor_seq'] == e['body']['anchor_seq'])
            self.assertLess(anchor['seq'], e['seq'])

    def test_mutation_the_old_ingest_duplicates_and_misattributes(self):
        events = self.run_pair(True)
        seqs = [e['body']['anchor_seq'] for e in of(events, 'anchor_receipt')]
        self.assertNotEqual(len(seqs), len(set(seqs)), 'a line chained twice')


# --------------------------------------------------------------------------- #
# root item 2: the cap changes nothing in the monitor, allocation, margin, scoring or
# first crossing
# --------------------------------------------------------------------------- #
FROZEN_DECISION_CODE_B049307: dict[str, str] = {
    'lab_monitor.py': '94d70b8d766376a697271087a1879de32170d4827bb25211c33f550232c2af91',
    'lab_reference_rule.py': '8f8b69f01e09a92ca77a665e19bbd8f8eeba0ceef1ddab0bc3cb09b0fb9ee6fd',
    'lab_coin.py': '6d85578daf3e3fa6bb1160156547b191157d8a005d638fcb818afb14ec50314c',
    'lab_design.py': 'd615e369d579a42acc2042e3580cb1d02a4b4171993dca735352c9b75d975b82',
    'lab_enclosure.py': '42f1b57dff684988cc0725bc0e64d982cd4b8b24f7ff68198c77d8d8a53966c6',
}


class DecisionCodeUnchangedTests(unittest.TestCase):
    """The five decision-defining files are byte-identical to b049307 (``git show b049307:
    experiments/live_ab/<file> | shasum -a 256``, transcribed), and the cap sits outside the
    rule block."""

    def test_the_five_files_carry_their_b049307_digests(self):
        for name, digest in FROZEN_DECISION_CODE_B049307.items():
            with self.subTest(name=name):
                self.assertEqual(sha256_file(LIVE / name), digest)

    def test_control_one_changed_byte_is_seen(self):
        tmp = Path(tempfile.mkdtemp(prefix='eb1cap_digest_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        copy_path = tmp / 'lab_monitor.py'
        copy_path.write_bytes((LIVE / 'lab_monitor.py').read_bytes() + b'\n')
        self.assertNotEqual(sha256_file(copy_path),
                            FROZEN_DECISION_CODE_B049307['lab_monitor.py'])

    def test_the_cap_is_outside_the_rule_block_and_the_margin_is_inside(self):
        cfg = json.loads((LIVE / 'config.json').read_text('utf-8'))
        cfg[lab_common.SERVER_SUPERVISION_KEY] = {
            'max_supervised_restarts_per_server_per_trial': 3,
            'on_exceeding': lab_common.SERVER_SUPERVISION_ON_EXCEEDING}
        base = lab_common.rule_block_sha256(cfg)
        for cap in (0, 7):
            other = copy.deepcopy(cfg)
            other[lab_common.SERVER_SUPERVISION_KEY][
                'max_supervised_restarts_per_server_per_trial'] = cap
            self.assertEqual(lab_common.rule_block_sha256(other), base)
        absent = {k: v for k, v in cfg.items() if k != lab_common.SERVER_SUPERVISION_KEY}
        self.assertEqual(lab_common.rule_block_sha256(absent), base)
        # negative control: the margin IS in the rule block
        margin = copy.deepcopy(cfg)
        margin['monitor']['delta'] = 0.04
        self.assertNotEqual(lab_common.rule_block_sha256(margin), base)


class FixedCoins:
    """A deterministic stand-in for ``lab_coin.draw`` (the coin's entropy source), so two runs
    draw the same coin sequence and their chains can be compared event for event."""

    def __init__(self) -> None:
        self.k = 0

    def __call__(self) -> lab_coin.Coin:
        raw = sha256_text('eb1cap-coin-%d' % self.k)[:16]
        self.k += 1
        return lab_coin.Coin(raw_hex=raw, bit=bytes.fromhex(raw)[0] & 1)


MONITOR_KEYS = ('trigger', 'n', 'n_collapsed', 'sum_lower_h', 'sum_upper_h', 'sum_lower_s',
                'sum_upper_s', 'radius', 'L_h', 'U_h', 'L_s', 'U_s', 'pair_updated',
                'pair_enclosure', 'flags', 'shadow', 'readouts')


def monitor_trace(events) -> list:
    return [{k: e['body'][k] for k in MONITOR_KEYS} for e in of(events, 'monitor_update')]


class CapInvarianceTests(unittest.TestCase):
    """Root item 2 on the running path: one coin sequence, three runs -- no cap (``free``),
    the cap bound after the receipted decision (``capped_b``, case b) and the cap bound at
    pair 20 (``capped_a``, case a).  The allocation (every enrollment and coin), every
    monitor output (band, sums, enclosures, flags, shadow) and the decision are identical on
    each chain's common prefix; the cap only ends a chain earlier.  Negative control: a run
    whose incumbent is slower still (another scoring input) changes the monitor trace, so the
    comparison can see a difference when one exists."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []

        def make(pairs_crash, post=0, scenario=None):
            tree = d3_tree()
            cls.trees.append(tree)
            fake = sup.FakeServers()
            with mock.patch.object(lab_coin, 'draw', FixedCoins()):
                status = sup.run(tree, fake, scenario=scenario,
                                 hook=sup.CrashPlan(fake, pairs=pairs_crash, post=post))
            return status, tree.events()
        cls.free = make((1, 2, 3))
        cls.capped_b = make((1, 2, 3), post=1)
        cls.capped_a = make((1, 2, 3, 20))
        other = copy.deepcopy(sup.SCENARIO)
        other['incumbent']['latency_scale'] = 9.0
        other['candidate']['p_good'] = 0.8
        cls.other = make((1, 2, 3), scenario=other)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    @staticmethod
    def allocation(events) -> list:
        return [(e['type'], e['body']) for e in events
                if e['type'] in ('pair_enrolled', 'coin_drawn')]

    def test_the_runs_are_the_cases_they_claim(self):
        self.assertEqual([s for s, _ in (self.free, self.capped_b, self.capped_a)],
                         ['ended', 'aborted', 'aborted'])
        self.assertEqual(lab_eventlog.restart_cap_case(self.capped_b[1], CAP, mock=MOCK)['case'],
                         'after_receipted_decision')
        self.assertEqual(lab_eventlog.restart_cap_case(self.capped_a[1], CAP, mock=MOCK)['case'],
                         'before_decision')

    def test_case_b_changes_no_allocation_no_monitor_output_and_not_the_decision(self):
        free, capped = self.free[1], self.capped_b[1]
        dseq = of(capped, 'decision')[0]['seq']
        pre = [e for e in capped if e['seq'] <= dseq]
        free_pre = [e for e in free if e['seq'] <= of(free, 'decision')[0]['seq']]
        self.assertEqual(self.allocation(pre), self.allocation(free_pre))
        self.assertEqual(monitor_trace(pre), monitor_trace(free_pre))
        self.assertEqual(of(capped, 'decision')[0]['body'], of(free, 'decision')[0]['body'])
        # the whole randomized phase, including the drain looks after the decision
        self.assertEqual(self.allocation(capped), self.allocation(free))
        self.assertEqual(monitor_trace(capped), monitor_trace(free))

    def test_case_a_is_a_prefix_of_the_uncapped_run(self):
        free, capped = self.free[1], self.capped_a[1]
        k = len(of(capped, 'monitor_update'))
        self.assertGreater(k, 0)
        self.assertEqual(monitor_trace(capped), monitor_trace(free)[:k])
        alloc = self.allocation(capped)
        self.assertEqual(alloc, self.allocation(free)[:len(alloc)])
        self.assertEqual(of(capped, 'decision'), [])
        self.assertEqual(lab_verify_log.lab_reference_rule.decide_from_chain(
            free, json.loads((self.trees[0].freeze / 'config.json').read_text('utf-8')),
            'T4')['n'], of(free, 'decision')[0]['body']['n'], 'the first crossing')

    def test_control_a_different_scoring_input_changes_the_trace(self):
        self.assertEqual(self.allocation(self.other[1])[:4], self.allocation(self.free[1])[:4],
                         'same coins')
        self.assertNotEqual(monitor_trace(self.other[1]), monitor_trace(self.free[1]))



# --------------------------------------------------------------------------- #
# root item 3: the model file's identity is MEASURED, before seq 0 and at every start
# --------------------------------------------------------------------------- #
class FrozenRecomputedDigestTests(unittest.TestCase):
    """Real-path preflight (``WORLD_FACTORY`` unset) compares the frozen servers entry's two
    digests: a freeze whose ``sha256_recomputed`` differs from ``sha256_expected`` (or is
    absent) cannot be matched by any file and is refused ``weights_hash``
    (``gguf_recomputed.<server>``).  Negative control: the agreeing freeze is not refused for
    that item."""

    def items(self, edit) -> set:
        tree = sup.Tree('T4', pairs=2)
        self.addCleanup(tree.close)
        tree.edit_config(edit)
        with self.assertRaises(lab_common.PreflightError) as caught:
            orch.preflight(tree.ctx())
        return {r['item'] for r in getattr(caught.exception, 'drift', [])}

    def test_a_freeze_whose_two_digests_disagree_is_refused(self):
        def disagree(cfg):
            cfg['servers']['coder']['sha256_recomputed'] = '7' * 64
        self.assertIn('gguf_recomputed.coder', self.items(disagree))

        def absent(cfg):
            cfg['servers']['coder']['sha256_recomputed'] = None
        self.assertIn('gguf_recomputed.coder', self.items(absent))
        # control: the mock freeze's agreeing pair (the other refusals of this bare tree --
        # no --gguf path, no launcher -- are the real path's and not the point here)
        self.assertNotIn('gguf_recomputed.coder', self.items(lambda cfg: None))


# --------------------------------------------------------------------------- #
# the REAL production entry path: main() as a subprocess, the EB1c shim, the mock anchor
# --------------------------------------------------------------------------- #
#: The mock outcomes of the harm trees: every first code request gets the stub and every
#: repair the reference, so in T1 the candidate (single_shot) fails and the incumbent
#: (self_test_repair: code, failing self-test, repair) succeeds -- a hierarchy score of -1 in
#: every pair, whichever orientation its coin drew.
HARM_OUTCOMES = {'single_shot': {'p_good': 0.0},
                 'self_test_repair': {'p_good': 0.0, 'p_selftest_fails': 0.0,
                                      'p_repair_fixes': 1.0}}
HARM_TRIAL = 'T1'
HARM_PAIRS = 44
HARM_N_MIN = 30                  # MOCK-ONLY screening prefix (dryrun_live_ab._screen rule)
BLOCKING_S = 20.0                # the anchor wait of the case (c) tree (frozen: 30 minutes)
QUIET_WAIT_S = 900.0


def quiet_host(limit_s: float = QUIET_WAIT_S) -> None:
    """Wait (read-only polls of the REAL host gate) until it would pass: a macOS baseline
    process such as mediaanalysisd is intermittently active, and the gate rightly refuses a
    run then.  Returns when quiet or at the limit (the run's own gate then decides)."""
    import lab_hostcheck
    deadline = time.monotonic() + float(limit_s)
    while time.monotonic() < deadline:
        try:
            lab_hostcheck.preflight_host_quiescent(orch.own_harness_pids())
            return
        except lab_hostcheck.HostNotQuiescent:
            time.sleep(10.0)


def host_refusals(t) -> int:
    return sum(1 for e in t.program_chain() if e['type'] == 'preflight_refused'
               and 'host_not_quiescent' in (e['body'].get('checks_failed') or []))


def run_entry(t, *, extra_argv: tuple = (), anchor: bool = True, on_poll=None,
              timeout_s: float = 900.0) -> bool:
    """``lab_orchestrator.py main()`` as a subprocess on tree ``t`` (with the existing
    ``lab_anchor.py --mock-receipt`` process unless ``anchor`` is false); ``on_poll(t, proc,
    anchor_proc)`` runs every 50 ms while it lives and may return a new anchor process (or
    None once it stopped it).  Sets ``t.proc`` / ``t.returncode`` / ``t.stdout``; returns
    whether the run was refused by the REAL host gate (a new ``host_not_quiescent`` record)."""
    before = host_refusals(t)
    anchor_proc = (dry._start_anchor(t.trial, json.loads(t.run_config.read_text('utf-8')),
                                     t.results, t.work) if anchor else None)
    log_path = t.work / ('invocation_%d.log' % time.monotonic_ns())
    try:
        with open(log_path, 'wb') as log:
            proc = subprocess.Popen([sys.executable, str(LIVE / 'lab_orchestrator.py')]
                                    + t.argv() + list(extra_argv), cwd=str(LIVE),
                                    env=entry.child_env(), stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        t.proc = proc
        deadline = time.monotonic() + timeout_s
        while proc.poll() is None and time.monotonic() < deadline:
            if on_poll is not None:
                anchor_proc = on_poll(t, proc, anchor_proc)
            time.sleep(0.05)
        if proc.poll() is None:
            entry.with_group_kill(proc)
        proc.wait(timeout=30)
    finally:
        dry._stop_anchor(anchor_proc)
    t.returncode = proc.returncode
    t.stdout = log_path.read_text('utf-8', 'replace')
    return host_refusals(t) > before


def harm_scenario(t, crash_after: int | None = None) -> dict:
    """The good scenario with :data:`HARM_OUTCOMES`; with ``crash_after = N`` the process
    really exits (``os._exit(9)`` under the mock's ``main``) at its N-th chat completion
    request (the smoke is the first).  ``N >= 3`` for every restarted process: a call a crash
    interrupted is retried after the client's one recovery wait as the new process's second
    or first request and is served -- no call meets two downs, so every episode keeps its
    outcome and every pair still scores -1.  (The mock's uid-keyed faults cannot aim at a
    pair here: the mock roster gives ``mbpp/90NN`` and ``mbpp_full/90NN`` one prompt, and
    ``lab_mock_server.recover_uid`` resolves both to the first.)"""
    sc = copy.deepcopy(t.good_scenario)
    sc['outcomes'] = copy.deepcopy(HARM_OUTCOMES)
    sc['faults'] = ([] if crash_after is None else
                    [{'match': {'after_requests': int(crash_after)}, 'do': 'exit', 'code': 9}])
    return sc


#: three supervised restarts early in the randomized phase, then a process that serves on
THREE_EARLY_RESTARTS = (3, 4, 4, None)


def kill_server_when(etype: str, state: dict):
    """An ``on_poll`` that SIGKILLs the newest launched server once the chain carries
    ``etype`` (the control's own crash, at a chain state no request count can aim at)."""
    def on_poll(t, proc, anchor_proc):
        if 'killed' in state:
            return anchor_proc
        try:
            events = t.chain()
        except (lab_common.ChainError, ValueError, OSError):   # a line mid-write
            return anchor_proc
        if of(events, etype):
            pid = int(t.launches()[-1]['pid'])
            os.kill(pid, signal.SIGKILL)
            state['killed'] = pid
            state['at_seq'] = len(events)
        return anchor_proc
    return on_poll


def expected_harm_tau(t) -> int:
    """The FROZEN band's own first crossing when every pair scores -1: the smallest ``n >=
    n_min`` with ``band(n, -n, -n).hi < 0`` (``lab_monitor.band``, the tree's alpha_gate and
    rho), asserted to be crossed only once the pair is fully revealed (``band(n, -(n-1),
    -(n-1)).hi >= 0``), so it does not depend on the order of the pair's two reveals."""
    import lab_monitor
    cfg = json.loads((t.freeze / 'config.json').read_text('utf-8'))
    mc = lab_monitor.MonitorConfig.from_config(cfg, t.trial)
    for n in range(int(mc.n_min), HARM_PAIRS + 1):
        if lab_monitor.band(n, -float(n), -float(n), mc).hi < 0:
            assert lab_monitor.band(n, -float(n - 1), -float(n - 1), mc).hi >= 0
            return n
    raise AssertionError('the frozen band never crosses within the tree')


#: Every event the cap, supervision or the anchors write: none of them may move a monitor
#: output (root item 2).  The replay of a chain STRIPPED of them must reproduce every look.
NON_MONITOR_TYPES = ('server_started', 'server_restarted', 'server_start_failed',
                     'server_down', 'server_stopped', 'server_health', 'metrics_scrape',
                     'anchor', 'anchor_receipt', 'anchor_failed', 'trial_paused',
                     'invocation_started', 'invocation_ended', 'trial_aborted')


class ProdCase(entry.EntryCase):
    """Shared helpers of the production-path cases (the EB1c ``EntryCase`` assertions)."""

    def harm_tree(self, name: str, **build_kw):
        quiet_host()
        t = entry.EntryTree(name, n_pairs=HARM_PAIRS, trial=HARM_TRIAL,
                            freeze_kw={'n_min': HARM_N_MIN})
        self.addCleanup(t.cleanup)
        t.build(**build_kw)
        t.set_scenarios([harm_scenario(t, n) for n in THREE_EARLY_RESTARTS])
        return t

    def run_fresh(self, make, **run_kw):
        """Build and run a fresh tree, again (at most twice more) only when the REAL host
        gate refused it -- a busy baseline process is not the behaviour under test."""
        for attempt in range(3):
            t = make()
            if not run_entry(t, **run_kw):
                return t
            quiet_host()
        self.fail('the host gate refused three runs: ' + str(entry.host_refusal(
            t.program_chain())))

    def assertAll(self, t, events, case: str) -> None:
        """The monitor is blind to the cap, the verifier's ``server.lifecycle`` fails nothing
        and labels ``case``, every success-valued server body names a launch scripted to
        serve (all four here: each crashes only after serving), the verifier CLI PASSes, and
        nothing outlives the run."""
        self.assertMonitorBlindToTheCap(t, events)
        self.assertEqual(entry.lifecycle_rules(t), [])
        self.assertEqual(entry.lifecycle_case(t), case)
        self.assertNoSuccessForBadLaunch(t, set(range(len(t.scenarios))))
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)

    def assertMonitorBlindToTheCap(self, t, events) -> None:
        """Root item 2 on the production path: every logged look is reproduced by the
        frozen monitor's replay of the chain with every supervision, server and anchor event
        removed, and the reference rule's first crossing on that stripped chain is the
        logged decision."""
        import lab_monitor
        import lab_reference_rule
        cfg = json.loads((t.freeze / 'config.json').read_text('utf-8'))
        stripped = [e for e in events if e['type'] not in NON_MONITOR_TYPES]
        snaps = lab_monitor.replay(stripped, cfg, t.trial)
        logged = of(events, 'monitor_update')
        self.assertEqual(len(snaps), len(logged))
        for snap, look in zip(snaps, logged):
            for key in ('n', 'sum_lower_h', 'sum_upper_h', 'sum_lower_s', 'sum_upper_s',
                        'radius', 'L_h', 'U_h', 'L_s', 'U_s'):
                self.assertEqual(repr(snap[key]), repr(look['body'][key]), key)
        ref = lab_reference_rule.decide_from_chain(stripped, cfg, t.trial)
        (decision,) = of(events, 'decision')
        self.assertEqual((ref['kind'], ref['n']),
                         (decision['body']['kind'], decision['body']['n']))


class ProdCaseB(ProdCase):
    """Case (b) through ``main()``: three supervised restarts in pairs 1-3, the frozen band
    crosses to ``harm_keep_incumbent`` at tau = 39, the mock anchor receipts the decision,
    the traffic switches, and the server dies at the repair call of follow-up pair 41 --
    the fourth down.  ``trial_aborted(server_restart_cap)``; the decision stands at its
    original tau and is reported; the follow-up is truncated and every unrun arrival is
    counted; the verifier PASSes and labels the case.  Negative controls: C1 (no cap,
    ``none``), C6 (case a) and :class:`ProdCaseC` (the same trial, the receipt not yet
    chained when the cap binds: provisional, not reportable)."""

    def test_case_b_the_receipted_decision_stands_and_the_follow_up_is_counted(self):
        state: dict = {}

        def make():
            state.clear()
            return self.harm_tree('PB')
        t = self.run_fresh(make, on_poll=kill_server_when('traffic_switch', state))
        self.assertEqual(t.returncode, 1, t.stdout[-3000:])
        self.assertIn('killed', state)
        events = t.chain()
        tau = expected_harm_tau(t)
        skel = entry.lifecycle(events)
        self.assertEqual(skel[-1], ('trial_aborted', 'server_restart_cap'))
        self.assertEqual([s for s in skel if s[0] == 'server_down'],
                         [('server_down', 'exit')] * 4)
        self.assertEqual(len(of(events, 'server_restarted')), 3)
        self.assertEqual(len(t.launches()), 4, 'one start and exactly three restarts')
        self.assertEqual(int(t.launches()[-1]['pid']), state['killed'])
        (decision,) = of(events, 'decision')
        self.assertEqual((decision['body']['kind'], decision['body']['n']),
                         ('harm_keep_incumbent', tau))
        receipt = lab_eventlog.decision_receipt(events, mock=True)
        (switch,) = of(events, 'traffic_switch')
        downs = of(events, 'server_down')
        fourth = downs[3]
        self.assertTrue(all(d['seq'] < decision['seq'] for d in downs[:3]),
                        'the three restarts came before the decision')
        self.assertEqual(fourth['body']['returncode'], -signal.SIGKILL)
        self.assertLess(decision['seq'], receipt['receipt_seq'])
        self.assertLess(receipt['receipt_seq'], switch['seq'])
        self.assertLess(switch['seq'], fourth['seq'])
        self.assertEqual(lab_eventlog.restart_cap_required_seq(events, CAP), fourth['seq'])
        follow = {int(e['body']['arrival']) for e in of(events, 'arm_assigned_by_decision')}
        self.assertTrue({int(r['arrival']) for r in fourth['body']['inflight']} <= follow)
        tail = [e for e in events if e['seq'] > fourth['seq']]
        self.assertEqual(of(tail, 'episode_started') + of(tail, 'arm_assigned_by_decision')
                         + of(tail, 'server_restarted') + of(tail, 'decision'), [])
        (aborted,) = of(events, 'trial_aborted')
        comp = aborted['body']['completion']
        total = 2 * HARM_PAIRS
        started = {int(e['body']['arrival']) for e in of(events, 'episode_started')}
        self.assertEqual((comp['restart_cap_case'], comp['cap_required_seq'],
                          comp['decision_status'], comp['decision_seq']),
                         ('after_receipted_decision', fourth['seq'], 'receipted',
                          decision['seq']))
        self.assertEqual((comp['arrivals_total'], comp['arrivals_run'],
                          comp['arrivals_not_run'], comp['follow_up_run'],
                          comp['follow_up_not_run']),
                         (total, len(started), total - len(started),
                          len(follow & started), total - len(sup.assigned_arrivals(events))))
        self.assertGreater(comp['follow_up_not_run'], 0, 'the follow-up was truncated')
        # the results: the decision at its original tau, reportable, the truncation counted
        out = builder.build([t.trial], t.bundle_sha, results_root=t.results,
                            work_root=t.work, out_dir=t.root / 'derived')
        obj = json.loads((t.root / 'derived' / t.trial / 'decision.json').read_text('utf-8'))
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision']['n'],
                          obj['restart_cap']['case']),
                         ('harm_keep_incumbent', True, tau, 'after_receipted_decision'))
        self.assertTrue(obj['decision_label'].startswith(
            'decision stands at tau=%d; follow-up truncated by the restart cap (%d '
            % (tau, comp['follow_up_not_run'])), obj['decision_label'])
        row = out['trials'][t.trial]
        self.assertEqual((row['decision'], row['reportable'], row['follow_up_not_run']),
                         ('harm_keep_incumbent', True, comp['follow_up_not_run']))
        self.assertAll(t, events, 'after_receipted_decision')



class ProdCaseC(ProdCase):
    """Case (c) through ``main()``: the same trial, but the mock anchor process is stopped
    right after it receipts the START anchor, so the decision's blocking anchor is never
    answered in this invocation.  When the decision event is in the chain the control kills
    the server (SIGKILL): the supervisor, which keeps polling while the receipt is awaited,
    records the fourth down -- the cap binds while the decision is provisional.  Nothing
    post-switch happens; after ``_runtime.blocking_wait_s`` (20 s; frozen: 30 minutes) the
    existing anchor-failure rule pauses the trial ``anchor_unavailable`` with the abort owed:
    the builder reports the decision PROVISIONAL (not reportable).  Then the channel returns:
    ``--resume`` with the anchor process running obtains the decision's receipt and only then
    takes the owed ``trial_aborted(server_restart_cap)``; the decision is finalized at its
    original tau, the whole follow-up counted as not run; the verifier PASSes and labels
    ``decision_provisional``.  Negative control: :class:`ProdCaseB` (receipt before the cap:
    case b, reportable at once)."""

    def test_case_c_provisional_until_the_receipt_then_the_owed_abort(self):
        state: dict = {}

        kill = kill_server_when('decision', state)

        def on_poll(t, proc, anchor_proc):
            receipts = t.work / t.trial / 'anchor_spool' / 'receipts.jsonl'
            if anchor_proc is not None:
                if receipts.exists() and receipts.read_bytes().count(b'\n') >= 1:
                    # the start anchor is receipted: the channel goes away
                    state['receipts_at_stop'] = receipts.read_bytes().count(b'\n')
                    dry._stop_anchor(anchor_proc)
                    return None
                return anchor_proc
            return kill(t, proc, None)

        def make():
            state.clear()
            return self.harm_tree('PC', runtime={'blocking_wait_s': BLOCKING_S})
        t = self.run_fresh(make, on_poll=on_poll)
        self.assertEqual(t.returncode, 2, t.stdout[-3000:])
        self.assertEqual(state.get('receipts_at_stop'), 1, 'only the start anchor answered')
        self.assertIn('killed', state)
        tau = expected_harm_tau(t)
        events = t.chain()
        (decision,) = of(events, 'decision')
        self.assertEqual((decision['body']['kind'], decision['body']['n']),
                         ('harm_keep_incumbent', tau))
        downs = of(events, 'server_down')
        self.assertEqual(len(downs), 4)
        self.assertTrue(all(d['seq'] < decision['seq'] for d in downs[:3]))
        fourth = downs[3]
        self.assertEqual((fourth['body']['detected_by'], fourth['body']['returncode'],
                          fourth['body']['inflight']), ('exit', -signal.SIGKILL, []))
        self.assertEqual(int(t.launches()[-1]['pid']), state['killed'])
        self.assertGreater(fourth['seq'], decision['seq'])
        self.assertEqual(lab_eventlog.restart_cap_case(events, CAP, mock=True)['case'],
                         'decision_provisional')
        self.assertEqual(lab_eventlog.decision_receipt(events, mock=True)['status'],
                         'provisional')
        self.assertEqual(entry.lifecycle(events)[-1], ('trial_paused', 'anchor_unavailable'))
        for etype in ('traffic_switch', 'arm_assigned_by_decision', 'trial_aborted',
                      'trial_ended'):
            self.assertEqual(of(events, etype), [], etype)
        self.assertEqual(orch.supervision_state(events, CAP).pending_abort,
                         orch.RESTART_CAP_REASON, 'the abort is still owed')
        cfg = json.loads((t.freeze / 'config.json').read_text('utf-8'))
        obj = builder.decision_object(events, cfg, t.trial)
        self.assertEqual((obj['primary_result'], obj['reportable']),
                         (builder.PROVISIONAL_LABEL, False))
        self.assertEqual(entry.lifecycle_rules(t), [])
        self.assertEqual(entry.lifecycle_case(t), 'decision_provisional')
        self.assertNoOrphans(t)
        paused_decision = copy.deepcopy(decision)
        paused_len = len(events)

        # -- the channel returns: resume with the anchor process ----------------------
        for attempt in range(3):
            if not run_entry(t, extra_argv=('--resume',)):
                break
            quiet_host()
        else:
            self.fail('the host gate refused three resumes')
        self.assertEqual(t.returncode, 1, t.stdout[-3000:])
        events = t.chain()
        self.assertEqual(events[:paused_len][-1]['type'],
                         [e['type'] for e in events][paused_len - 1])
        (decision,) = of(events, 'decision')
        self.assertEqual(decision, paused_decision, 'the decision and its tau are unchanged')
        (aborted,) = of(events, 'trial_aborted')
        self.assertEqual(aborted['body']['reason'], 'server_restart_cap')
        receipt = lab_eventlog.decision_receipt(events, mock=True)
        self.assertEqual(receipt['status'], 'receipted')
        self.assertGreater(receipt['receipt_seq'], paused_len)
        self.assertLess(receipt['receipt_seq'], aborted['seq'])
        self.assertEqual(of(events, 'traffic_switch') + of(events, 'arm_assigned_by_decision'),
                         [], 'nothing post-switch: the follow-up is truncated whole')
        resumed = [e for e in events if e['seq'] >= paused_len]
        self.assertEqual(of(resumed, 'server_started') + of(resumed, 'episode_started'), [],
                         'the resume starts no server and dispatches nothing')
        comp = aborted['body']['completion']
        total = 2 * HARM_PAIRS
        self.assertEqual((comp['restart_cap_case'], comp['decision_status'],
                          comp['follow_up_run'], comp['follow_up_not_run'],
                          comp['arrivals_not_run']),
                         ('decision_provisional', 'receipted', 0, total - 2 * tau,
                          total - 2 * tau))
        out = builder.build([t.trial], t.bundle_sha, results_root=t.results,
                            work_root=t.work, out_dir=t.root / 'derived')
        obj = json.loads((t.root / 'derived' / t.trial / 'decision.json').read_text('utf-8'))
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision']['n']),
                         ('harm_keep_incumbent', True, tau))
        self.assertIn('provisional when the cap bound, receipted afterwards',
                      obj['decision_label'])
        self.assertEqual(out['trials'][t.trial]['follow_up_not_run'], total - 2 * tau)
        seqs = [e['body']['anchor_seq'] for e in of(events, 'anchor_receipt')]
        self.assertEqual(len(seqs), len(set(seqs)), 'every receipt chained once')
        self.assertAll(t, events, 'decision_provisional')


class ProdModelFileIdentity(entry.EntryCase):
    """Root item 3 through ``main()``: the weights file is identified by its MEASURED bytes
    and SHA-256 (never the configuration's copy), before seq 0 and at every start, AND by its
    tokenized path (the golden ``/props`` ``model_path``).  A different file at the right
    tokenized name -- the golden object's own path, same byte count, other content -- is
    refused before seq 0 (``weights_hash``, the drift row carrying the digest measured from
    that file); the same swap after the first start is refused at the restart's GGUF stage.
    Negative control: the correct file starts, and its body carries the measured digest."""

    n_pairs = 1

    def swapped_bytes(self, t) -> bytes:
        good = t.gguf.read_bytes()
        bad = good[:-1] + bytes([good[-1] ^ 0xFF])
        self.assertEqual(len(bad), len(good))
        self.assertNotEqual(bad, good)
        return bad

    def test_control_the_correct_file_starts_with_its_measured_digest(self):
        quiet_host()
        t = self.tree('GG0')
        self.assertFalse(run_entry(t), 'host gate')
        self.assertEqual(t.returncode, 0, t.stdout[-3000:])
        (started,) = of(t.chain(), 'server_started')
        frozen = json.loads((t.freeze / 'config.json').read_text('utf-8'))['servers']['coder']
        self.assertEqual(started['body']['gguf'],
                         {'bytes': t.gguf.stat().st_size, 'sha256': sha256_file(t.gguf)})
        self.assertEqual((frozen['bytes'], frozen['sha256_expected'],
                          frozen['sha256_recomputed']),
                         (t.gguf.stat().st_size, sha256_file(t.gguf), sha256_file(t.gguf)))
        self.assertEqual(lab_common.tokenize_path(str(t.gguf)), t.golden_props['model_path'])
        self.assertNoOrphans(t)

    def test_a_different_file_at_the_right_tokenized_name_is_refused_before_seq_0(self):
        quiet_host()
        t = self.tree('GG1')
        frozen_digest = sha256_file(t.gguf)
        t.gguf.write_bytes(self.swapped_bytes(t))
        self.assertEqual(lab_common.tokenize_path(str(t.gguf)), t.golden_props['model_path'],
                         'the right tokenized name')
        self.assertFalse(run_entry(t, anchor=False), 'host gate')
        self.assertEqual(t.returncode, 1, t.stdout[-3000:])
        self.assertEqual(t.chain(), [], 'no trial chain before seq 0')
        self.assertEqual(t.launches(), [], 'nothing was launched')
        (refused,) = of(t.program_chain(), 'preflight_refused')
        self.assertEqual(refused['body']['checks_failed'], ['weights_hash'])
        row = next(r for r in refused['body']['drift'] if r['item'] == 'gguf.coder')
        self.assertEqual((row['expected'], row['found']), (frozen_digest, sha256_file(t.gguf)),
                         'the digest was measured from the file actually named')
        self.assertNoOrphans(t)

    def test_a_file_swapped_after_the_first_start_is_refused_at_the_restart(self):
        quiet_host()
        t = self.tree('GG2', n_pairs=2)
        t.set_scenarios(entry.crash_first(t, t.good_scenario))
        bad = self.swapped_bytes(t)
        done: dict = {}

        def on_poll(tree, proc, anchor_proc):
            if 'swapped' not in done:
                try:
                    events = tree.chain()
                except (lab_common.ChainError, ValueError, OSError):   # a line mid-write
                    events = []
                if of(events, 'server_started'):
                    tree.gguf.write_bytes(bad)
                    done['swapped'] = True
            return anchor_proc
        self.assertFalse(run_entry(t, on_poll=on_poll), 'host gate')
        self.assertEqual(t.returncode, 1, t.stdout[-3000:])
        events = t.chain()
        self.assertEqual(entry.lifecycle(events), [
            ('server_started',), ('server_down', 'exit'), ('server_stopped',),
            ('server_start_failed', 'restart', 'gguf', ('gguf_sha256',)),
            ('trial_aborted', 'server_identity')])
        self.assertEqual(len(t.launches()), 1, 'the GGUF stage refused before any launch')
        self.assertEqual(entry.lifecycle_rules(t), [])
        self.assertNoOrphans(t)


if __name__ == '__main__':                                   # pragma: no cover
    unittest.main()
