"""Controls of root's 16:05 ruling on decision eligibility during abort and close.

``reviews/eb1_eb5_decision_eligibility_ruling_20260924_1605.md`` (root, on origin/main):

1. "Once any terminal abort is owed before a decision, later reveal/monitor looks must remain in
   the immutable record and partial bounds, but must not create a decision.  The already
   specified postdecision case remains separate ... A fix needs a negative control with a
   crossing during an owed-abort drain, plus a recovery/control path showing that ordinary
   eligible decisions still occur."
2. "Define the earliest eligible decision prefix from durable event ordering, including the
   reason a later look is ineligible; apply that same classification in the orchestrator,
   verifier and results builder.  Preserve the unfiltered reference-rule crossing and all looks
   as diagnostics, but label a crossing inside an ineligible interval as not acted on, with a
   concrete operational reason.  Do not blanket-exempt any missing decision or any look merely
   because a trial later aborted ... Controls must cover both before/after ordering, an
   unresolved worker that survives resume, and the normal eligible crossing."

And the limit the fix step disclosed at 159e747: "an abort with no trigger in the chain (the run
loop's backstop, a refused restart, a hook script) still reports its drain crossing as
LIVE_DECISION_INVALID".  The repair: every abort path writes ``abort_owed`` -- its durable
no-decision point -- before its drain (``lab_orchestrator.World.owe_abort`` /
``write_abort_owed``, ``close_trial``), and ONE function, ``lab_eventlog.decision_eligibility``,
classifies every look for the orchestrator (``World._look_eligibility``), the verifier
(``reference_rule.agreement``) and the builder (``decision_object.eligibility``).

* :class:`ExclusionPointTests` / :class:`OrderingTests` -- the pure classification on minimal
  chains: ``abort_owed`` is a point (and not the earliest when a trigger precedes it); a
  crossing just AFTER the point is not acted on (verifier INFO), one just BEFORE it with no
  decision is ``missed`` (verifier FAIL) even though the trial then aborts; the normal eligible
  crossing is acted on; a decision after the point is invalid.
* :class:`RealChainOrderingTests` -- the same before/after ordering on a PRODUCTION chain (the D3
  tree deploys at n = 44): the point inserted just before vs just after the crossing look.
* :class:`AbortPathsInProcess` -- item 1 and the disclosed limit, on the production
  ``run_trial``: the run loop's backstop, a refused restart (a non-cap OWED abort drained by the
  pump) and a hook raising ``AbortTrial`` each write ``abort_owed`` before the drain that
  reveals the crossing pair; the crossing is logged, takes no decision, and the verifier and the
  builder label it NOT ACTED ON with its reason.  Mutation: the 159e747 behaviour (no point in
  the chain, the decision withheld only in memory) is read LIVE_DECISION_INVALID and FAILs
  ``abort_point_missing``.  Recovery/control paths: no crash, three supervised restarts, and an
  abort after the receipted decision -- each decides at the same crossing, and the post-decision
  abort keeps the decision at its original tau; an abort before the decision's receipt leaves it
  provisional (the matched external-receipt rule), never reported as the result.
* :class:`UnresolvedAcrossResumeInProcess` -- a worker recorded ``alive_unresolved`` by a
  refused resume survives into the next resume, which reveals the crossing pair from its spools:
  not acted on (``unresolved_worker``); mutation (nothing recorded) decides at the same look.
* :class:`SameClassificationTests` -- the three paths call the one function (a spy over a
  production run, the verifier and the builder; an AST check that none of them calls
  ``no_decision_point`` around it), and the orchestrator's classification of every look at write
  time equals the whole-chain classification the verifier and the builder read.  Negative
  control: a "blanket" classifier that exempts looks because the trial later aborted fails that
  equality, and the AST check flags the 159e747 verifier.
* :class:`DecisionCodeBytesTests` -- item 3 of the step: ``lab_monitor``, ``lab_reference_rule``,
  ``lab_coin``, ``lab_design`` and ``lab_enclosure`` are the b049307 git blobs.

New attributes of the repair are looked up at call time, so the module imports on 159e747, where
its controls FAIL (the before run of this step).  Outside the ``experiments/live_ab/tests_*.py``
glob on purpose (repair contract, placement).  Prepared and checked by AI agent sessions; not human
peer review or author sign-off (protocol 14.7).
"""
from __future__ import annotations

import ast
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
REPO = HERE.parents[1]
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_live_ab_results as builder                                 # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_reference_rule                                               # noqa: E402
import lab_verify_log                                                   # noqa: E402
import tests_eb1_cap_estimand as cap                                    # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402

setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule

CAP = cap.CAP
CROSS_N = 44                      # the D3 tree's first crossing (deploy_candidate)
NOT_ACTED = 'NOT_ACTED_ON_abort_before_decision'
INVALID = 'LIVE_DECISION_INVALID (harness defect)'


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


def crossing(events) -> dict:
    """The first logged look whose reference shadow crosses."""
    return next(e for e in of(events, 'monitor_update')
                if e['body']['shadow']['action'] != 'none')


def eligibility(events, cap_=CAP, limit=10, actions=None, trigger=None) -> dict:
    return lab_eventlog.decision_eligibility(events, cap_, failure_limit=limit,
                                             reference_actions=actions, next_trigger=trigger)


def _chain(*specs) -> list:
    """``(type, body)`` pairs numbered 0..n-1."""
    return [{'seq': i, 'type': t, 'body': copy.deepcopy(b), 'chain': 'T4'}
            for i, (t, b) in enumerate(specs)]


def renumber(events) -> list:
    out = []
    for i, ev in enumerate(events):
        ev = copy.deepcopy(ev)
        ev['seq'] = i
        out.append(ev)
    return out


def agreement_rows(events, cfg, trial='T4') -> list:
    """The verifier's ``reference_rule.agreement`` rows of an IN-MEMORY chain: the reference
    rule's looks and first crossing, the shared classification, and the verifier's own rule
    function (``lab_verify_log._check_decision_eligibility``) -- what ``verify_trial`` runs, on
    events that are not written to disk."""
    looks = lab_reference_rule.looks_from_chain(events, cfg, trial)
    ref = lab_reference_rule.decide_from_chain(events, cfg, trial)
    try:
        cap_: int | None = lab_common.server_supervision_cap(cfg)
    except lab_common.FrozenMismatch:
        cap_ = None
    elig = lab_eventlog.decision_eligibility(
        events, cap_, failure_limit=lab_verify_log._failure_limit(cfg),
        reference_actions=[lk.action for lk in looks])
    col = lab_verify_log._Collector(trial=trial, mode='full')
    lab_verify_log._check_decision_eligibility(col, events, elig, ref, of(events, 'decision'))
    return [(f.severity, dict(f.detail)) for f in col.findings
            if f.check == 'reference_rule.agreement']


OWED = {'reason': 'harness_defect', 'source': 'supervision', 'decision_logged': False,
        'open_arrivals': [87, 88]}
LOOK = {'trigger': 'reveal', 'n': 44}


# --------------------------------------------------------------------------- #
# the pure classification
# --------------------------------------------------------------------------- #
class ExclusionPointTests(unittest.TestCase):

    def test_abort_owed_is_a_point_with_its_abort_reason_and_source(self):
        got = lab_eventlog.no_decision_point(_chain(('invocation_started', {}),
                                                    ('abort_owed', OWED)), CAP)
        self.assertEqual(got, {'seq': 1, 'reason': 'abort_owed',
                               'abort_reason': 'harness_defect', 'source': 'supervision'})
        # negative controls: an earlier trigger stays the point; no abort_owed, no point
        got = lab_eventlog.no_decision_point(
            _chain(('llm_response', {'receipt_mismatch': ['t']}), ('abort_owed', OWED)), CAP)
        self.assertEqual(got, {'seq': 0, 'reason': 'receipt_mismatch'})
        self.assertIsNone(lab_eventlog.no_decision_point(
            _chain(('invocation_started', {}), ('server_down', {'server_id': 'coder'})), CAP))

    def test_the_schema_is_closed_and_trial_only(self):
        lab_eventlog.validate_event('abort_owed', dict(OWED))
        self.assertIn('abort_owed', lab_eventlog.TRIAL_ONLY_TYPES)
        for bad in (dict(OWED, source='operator_note'), dict(OWED, reason='because'),
                    {k: v for k, v in OWED.items() if k != 'source'}):
            with self.assertRaises(lab_common.SchemaError):
                lab_eventlog.validate_event('abort_owed', bad)

    def test_supervision_state_keeps_an_owed_abort_across_a_crash(self):
        """A crash inside the drain of an abort with no other trigger (a refused restart) used
        to forget the abort on resume; its ``abort_owed`` is now replayed as owed."""
        events = _chain(('invocation_started', {}), ('abort_owed', OWED))
        self.assertEqual(orch.supervision_state(events, CAP).pending_abort, 'harness_defect')
        self.assertIsNone(orch.supervision_state(events[:1], CAP).pending_abort)
        done = _chain(('invocation_started', {}), ('abort_owed', OWED), ('trial_aborted', {}))
        self.assertIsNone(orch.supervision_state(done, CAP).pending_abort,
                          'the terminal record discharges it')


class OrderingTests(unittest.TestCase):
    """Before/after ordering on minimal chains (the reference actions given per look), read by
    the shared classification AND by the verifier's rule on it (``agreement_rows`` needs a real
    chain; the verifier's rule function is called directly here)."""

    @staticmethod
    def verdict_rows(events, actions) -> list:
        """The verifier's rows; the reference rule's first crossing is the first action that is
        not ``none`` (at n = 44), and a row is named by its ``rule`` when it has one."""
        first = next((a for a in actions if a != 'none'), None)
        ref = ({'kind': first, 'n': 44} if first is not None else {'kind': 'none', 'n': None})
        elig = eligibility(events, actions=actions)
        col = lab_verify_log._Collector(trial='T4', mode='full')
        lab_verify_log._check_decision_eligibility(col, events, elig, ref,
                                                   of(events, 'decision'))
        return [(f.severity, f.detail.get('rule') or f.detail.get('consequence'))
                for f in col.findings]

    def test_a_crossing_just_after_the_point_is_not_acted_on(self):
        ev = _chain(('monitor_update', dict(LOOK, n=43)), ('abort_owed', OWED),
                    ('monitor_update', LOOK), ('trial_aborted', {'reason': 'harness_defect'}))
        got = eligibility(ev, actions=['none', 'deploy_candidate'])
        self.assertEqual(got['exclusion']['seq'], 1)
        self.assertEqual([(lk['eligible'], lk['reason']) for lk in got['looks']],
                         [(True, None), (False, 'abort_owed')])
        self.assertEqual((got['crossing']['verdict'], got['crossing']['reason']),
                         ('not_acted_on', 'abort_owed'))
        self.assertIn('abort was owed', got['crossing']['reason_text'])
        self.assertEqual(self.verdict_rows(ev, ['none', 'deploy_candidate']),
                         [('INFO', NOT_ACTED)])

    def test_a_crossing_just_before_the_point_with_no_decision_is_a_defect(self):
        """No blanket exemption: the trial aborts, but the crossing precedes the point."""
        ev = _chain(('monitor_update', LOOK), ('abort_owed', OWED),
                    ('monitor_update', dict(LOOK, n=45)),
                    ('trial_aborted', {'reason': 'harness_defect'}))
        got = eligibility(ev, actions=['deploy_candidate', 'none'])
        self.assertEqual((got['crossing']['verdict'], got['crossing']['eligible']),
                         ('missed', True))
        self.assertEqual(self.verdict_rows(ev, ['deploy_candidate', 'none']),
                         [('FAIL', 'LIVE_DECISION_INVALID')])

    def test_the_normal_eligible_crossing_is_acted_on(self):
        ev = _chain(('monitor_update', LOOK), ('decision', {'kind': 'deploy_candidate',
                                                            'n': 44, 'monitor_seq': 0}),
                    ('monitor_update', dict(LOOK, trigger='drain')),
                    ('abort_owed', dict(OWED, decision_logged=True)),
                    ('trial_aborted', {'reason': 'harness_defect'}))
        got = eligibility(ev, actions=['deploy_candidate', 'none'])
        self.assertEqual((got['crossing']['verdict'], got['decision_verdict']),
                         ('acted_on', 'eligible'))
        self.assertEqual([lk['reason'] for lk in got['looks']], [None, 'decision_logged'])
        self.assertEqual(self.verdict_rows(ev, ['deploy_candidate', 'none']), [])

    def test_a_decision_after_the_point_is_invalid(self):
        ev = _chain(('abort_owed', OWED), ('monitor_update', LOOK),
                    ('decision', {'kind': 'deploy_candidate', 'n': 44, 'monitor_seq': 1}),
                    ('trial_aborted', {'reason': 'harness_defect'}))
        got = eligibility(ev, actions=['deploy_candidate'])
        self.assertEqual((got['decision_verdict'], got['crossing']['verdict']),
                         ('after_exclusion', 'decision_ineligible'))
        self.assertEqual(self.verdict_rows(ev, ['deploy_candidate']),
                         [('FAIL', 'decision_after_no_decision_point')])

    def test_a_trial_aborted_without_its_point_fails(self):
        ev = _chain(('monitor_update', dict(LOOK, n=43)),
                    ('trial_aborted', {'reason': 'server_identity'}))
        self.assertEqual(self.verdict_rows(ev, ['none']), [('FAIL', 'abort_point_missing')])
        ok = _chain(('abort_owed', dict(OWED, reason='server_identity')),
                    ('trial_aborted', {'reason': 'server_identity'}))
        self.assertEqual(self.verdict_rows(ok, []), [])
        superseded = _chain(('abort_owed', dict(OWED, reason='server_restart_cap')),
                            ('trial_aborted', {'reason': 'unresolved_worker', 'resolution': {
                                'superseded_reason': 'server_restart_cap'}}))
        self.assertEqual(self.verdict_rows(superseded, []), [])

    def test_the_next_look_is_what_the_orchestrator_acts_on(self):
        self.assertEqual(eligibility(_chain(('monitor_update', LOOK)))['next_look'],
                         {'eligible': True, 'reason': None})
        self.assertEqual(eligibility(_chain(('abort_owed', OWED)))['next_look'],
                         {'eligible': False, 'reason': 'abort_owed'})
        self.assertEqual(eligibility(_chain(('monitor_update', LOOK)),
                                     trigger='drain')['next_look'],
                         {'eligible': False, 'reason': 'drain_look'})


# --------------------------------------------------------------------------- #
# before/after ordering on a production chain
# --------------------------------------------------------------------------- #
class RealChainOrderingTests(unittest.TestCase):
    """The D3 tree's production chain (no crash: it deploys at n = 44).  In memory, the decision
    and everything after the crossing look are replaced by the same abort -- ``abort_owed`` and
    ``trial_aborted(harness_defect)`` -- placed just BEFORE or just AFTER the crossing look."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tree = cap.d3_tree()
        fake = sup.FakeServers()
        cls.status = sup.run(cls.tree, fake)
        cls.events = cls.tree.events()
        cls.cfg = cls.tree.frozen_cfg()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tree.close()

    def variant(self, where: str) -> list:
        look = crossing(self.events)
        head = [e for e in self.events if e['seq'] < look['seq']]
        owed = {'seq': -1, 'type': 'abort_owed', 'chain': 'T4', 'body': dict(OWED)}
        end = {'seq': -1, 'type': 'trial_aborted', 'chain': 'T4',
               'body': {'status': 'aborted', 'reason': 'harness_defect'}}
        mid = [owed, look] if where == 'before' else [look, owed]
        return renumber(head + mid + [end])

    def test_control_the_production_chain_acts_on_its_crossing(self):
        self.assertEqual(self.status, 'ended')
        (decision,) = of(self.events, 'decision')
        look = crossing(self.events)
        self.assertEqual((decision['body']['n'], decision['body']['monitor_seq']),
                         (CROSS_N, look['seq']))
        obj = builder.decision_object(self.events, self.cfg, 'T4')
        self.assertEqual(obj['eligibility']['crossing']['verdict'], 'acted_on')
        self.assertEqual(obj['primary_result'], 'deploy_candidate')
        self.assertEqual(agreement_rows(self.events, self.cfg), [])

    def test_the_point_just_before_the_crossing_look_is_not_acted_on(self):
        ev = self.variant('before')
        obj = builder.decision_object(ev, self.cfg, 'T4')
        self.assertEqual((obj['eligibility']['crossing']['verdict'],
                          obj['eligibility']['crossing']['reason']),
                         ('not_acted_on', 'abort_owed'))
        self.assertEqual((obj['primary_result'], obj['reportable']),
                         (builder.ABORT_INCOMPLETE_LABEL, False))
        self.assertEqual(obj['crossing_not_acted_on']['n'], CROSS_N)
        self.assertEqual([(s, r['consequence']) for s, r in agreement_rows(ev, self.cfg)],
                         [('INFO', NOT_ACTED)])

    def test_the_point_just_after_the_crossing_look_leaves_a_defect(self):
        ev = self.variant('after')
        obj = builder.decision_object(ev, self.cfg, 'T4')
        self.assertEqual(obj['eligibility']['crossing']['verdict'], 'missed')
        self.assertEqual((obj['primary_result'], obj['reportable']), (INVALID, False))
        self.assertIsNone(obj['crossing_not_acted_on'])
        rows = agreement_rows(ev, self.cfg)
        self.assertEqual([(s, r['consequence'], r.get('crossing_verdict')) for s, r in rows],
                         [('FAIL', 'LIVE_DECISION_INVALID', 'missed')])


# --------------------------------------------------------------------------- #
# in process: every abort path writes its point before its drain
# --------------------------------------------------------------------------- #
class RaiseAt:
    """A hook script (``SupWorld.hook``, called at every health poll): raise ``make()`` once --
    at the first poll that sees pair ``pair`` in flight before any decision; or (``post``) at
    the first poll of the follow-up cohort with an arrival in flight; or (``provisional``) at
    the first poll after the decision while its blocking receipt is still missing."""

    def __init__(self, make, *, pair: int = CROSS_N, post: bool = False,
                 provisional: bool = False) -> None:
        self.make, self.pair, self.post, self.fired = make, pair, post, False
        self.provisional = provisional

    def __call__(self, world) -> None:
        if self.fired:
            return
        if self.provisional:
            if world.decision is None or world.decision_receipted():
                return
        elif not world.open_arrivals:
            return
        elif self.post:
            if world.phase != 'post_decision':
                return
        elif world.decision is not None or world.pairs_enrolled != self.pair:
            return
        self.fired = True
        raise self.make()


def gate_159e747(real):
    """MUTATION: the 159e747 look gate -- the decision withheld in MEMORY (an owed abort, the
    close, an unresolved worker) as well as by the chain."""
    def gate(self, trigger):
        got = real(self, trigger)
        if got['eligible'] and (self.pending_abort is not None or self.closing
                                or self.unresolved_seen):
            return {'eligible': False, 'reason': 'in_memory'}
        return got
    return gate


def run_scenario(name: str, tree, *, mutated: bool = False, spy: list | None = None) -> str:
    fake = sup.FakeServers()
    hook = None
    if name == 'backstop':
        hook = RaiseAt(lambda: lab_common.ServerIdentityError('the backstop control'))
    elif name == 'hook':
        hook = RaiseAt(lambda: lab_common.AbortTrial('operator_discretion'))
    elif name == 'refused_restart':
        fake.restart_raises = lab_common.PreflightError
        hook = sup.CrashPlan(fake, pairs=(CROSS_N,))
    elif name == 'recovered':
        hook = sup.CrashPlan(fake, pairs=(1, 2, 3))
    elif name == 'post_decision':
        hook = RaiseAt(lambda: lab_common.AbortTrial('operator_discretion'), post=True)
    elif name == 'post_decision_provisional':
        hook = RaiseAt(lambda: lab_common.AbortTrial('operator_discretion'), provisional=True)
    patches = []
    try:
        # on a tree without the repair (the before run: 159e747) there is no abort_owed writer
        # and no shared gate: the mutated run IS that tree's behaviour, and nothing is spied
        if mutated and hasattr(orch.World, 'write_abort_owed'):
            for p in (mock.patch.object(orch.World, 'write_abort_owed', lambda *a, **k: None),
                      mock.patch.object(orch.World, '_look_eligibility',
                                        gate_159e747(orch.World._look_eligibility))):
                p.start()
                patches.append(p)
        if spy is not None and hasattr(orch.World, '_look_eligibility'):
            gate = orch.World._look_eligibility          # the (possibly mutated) gate

            def spying(self, trigger):
                got = gate(self, trigger)
                spy.append({'seq': len(self.log.events), 'trigger': trigger, **got})
                return got
            p = mock.patch.object(orch.World, '_look_eligibility', spying)
            p.start()
            patches.append(p)
        if name == 'post_decision_provisional':
            # the decision's blocking anchor is never answered (``cap.GatedWorld``)
            return cap.run_gated(tree, fake, hook=hook, hold=('decision',))
        return sup.run(tree, fake, hook=hook)
    finally:
        for p in reversed(patches):
            p.stop()


class AbortPathsInProcess(unittest.TestCase):
    """The production ``run_trial`` on the D3 tree (the uncapped run deploys at n = 44)."""

    ABORTS = {'backstop': ('server_identity', 'run_loop_backstop'),
              'refused_restart': ('harness_defect', 'supervision'),
              'hook': ('operator_discretion', 'abort_raised')}

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []
        cls.spies: dict = {}
        cls.runs: dict = {}

        def run(name, mutated=False):
            tree = cap.d3_tree()
            cls.trees.append(tree)
            spy: list = []
            status = run_scenario(name, tree, mutated=mutated, spy=spy)
            cls.spies[(name, mutated)] = spy
            cls.runs[(name, mutated)] = (status, tree.events(), tree)
        for name in cls.ABORTS:
            run(name)
        run('backstop', mutated=True)
        run('refused_restart', mutated=True)
        for name in ('control', 'recovered', 'post_decision', 'post_decision_provisional'):
            run(name)

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def test_every_abort_path_writes_its_point_before_the_drain(self):
        for name, (reason, source) in self.ABORTS.items():
            with self.subTest(path=name):
                status, events, tree = self.runs[(name, False)]
                self.assertEqual(status, 'aborted')
                self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'], reason)
                self.assertEqual(of(events, 'decision'), [], 'an abort creates no decision')
                owed = [e for e in of(events, 'abort_owed') if e['body']['reason'] == reason]
                self.assertEqual(len(owed), 1)
                self.assertEqual((owed[0]['body']['source'],
                                  owed[0]['body']['decision_logged']), (source, False))
                pair = [e for e in of(events, 'episode_revealed')
                        if e['body']['pair'] == CROSS_N]
                self.assertEqual(len(pair), 2)
                self.assertTrue(all(e['seq'] > owed[0]['seq'] for e in pair),
                                'the drain reveals the crossing pair AFTER the point')
                self.assertEqual(sorted(owed[0]['body']['open_arrivals']),
                                 sorted(e['body']['arrival'] for e in pair))
                look = crossing(events)
                self.assertGreater(look['seq'], owed[0]['seq'])
                self.assertEqual((look['body']['shadow']['action'], look['body']['n']),
                                 ('deploy_candidate', CROSS_N),
                                 'the crossing look is logged unchanged')

    def test_the_drain_crossing_is_not_acted_on_in_all_three_paths(self):
        for name, (reason, source) in self.ABORTS.items():
            with self.subTest(path=name):
                status, events, tree = self.runs[(name, False)]
                self.assertEqual(tree.verify_fails(), [])
                rows = cap.verifier_rows(tree, 'reference_rule.agreement')
                self.assertEqual([(s, r['consequence']) for s, r in rows], [('INFO', NOT_ACTED)])
                row = rows[0][1]
                self.assertEqual((row['no_decision_reason'], row['abort_reason'],
                                  row['abort_source']), ('abort_owed', reason, source))
                self.assertTrue(row['reason_text'])
                _summary, obj = cap.build(tree)
                self.assertEqual((obj['primary_result'], obj['reportable']),
                                 (builder.ABORT_INCOMPLETE_LABEL, False))
                self.assertEqual((obj['crossing_not_acted_on']['n'],
                                  obj['crossing_not_acted_on']['abort_source']),
                                 (CROSS_N, source))
                # the unfiltered diagnostics: every look is in decision.json, classified
                self.assertEqual(len(obj['eligibility']['looks']),
                                 len(of(events, 'monitor_update')))
                self.assertEqual(obj['reference_rule']['kind'], 'deploy_candidate')

    def test_mutation_without_the_point_is_the_159e747_reading(self):
        """The 159e747 behaviour (no ``abort_owed``; the decision withheld in memory only): the
        same drain crossing is read LIVE_DECISION_INVALID, and the verifier also FAILs the
        abort without its point."""
        for name in ('backstop', 'refused_restart'):
            with self.subTest(path=name):
                status, events, tree = self.runs[(name, True)]
                self.assertEqual(status, 'aborted')
                self.assertEqual((of(events, 'abort_owed'), of(events, 'decision')), ([], []))
                fails = {(c, d.get('consequence') or d.get('rule'))
                         for c, d in tree.verify_fails()}
                self.assertIn(('reference_rule.agreement', 'LIVE_DECISION_INVALID'), fails)
                self.assertIn(('reference_rule.agreement', 'abort_point_missing'), fails)
                summary, obj = cap.build(tree)
                self.assertEqual((obj['primary_result'], obj['reportable']), (INVALID, False))
                # root 19:05: the summary never reports the missed crossing's trial as 'none'
                row = summary['trials']['T4']
                self.assertEqual((row['decision'], row['reportable'], row['logged_decision']),
                                 (INVALID, False, 'none'))

    def test_recovery_and_control_paths_still_decide_at_the_eligible_crossing(self):
        for name in ('control', 'recovered', 'post_decision'):
            with self.subTest(path=name):
                status, events, tree = self.runs[(name, False)]
                (decision,) = of(events, 'decision')
                look = crossing(events)
                self.assertEqual((decision['body']['kind'], decision['body']['n'],
                                  decision['body']['monitor_seq']),
                                 ('deploy_candidate', CROSS_N, look['seq']))
                self.assertEqual(tree.verify_fails(), [])
                self.assertEqual(cap.verifier_rows(tree, 'reference_rule.agreement'), [])
                _summary, obj = cap.build(tree)
                self.assertEqual(obj['eligibility']['crossing']['verdict'], 'acted_on')
                self.assertEqual((obj['primary_result'], obj['reportable']),
                                 ('deploy_candidate', True))
        self.assertEqual(self.runs[('control', False)][0], 'ended')
        status, events, _tree = self.runs[('recovered', False)]
        self.assertEqual((status, len(of(events, 'server_restarted'))), ('ended', CAP))

    def test_the_post_decision_abort_keeps_the_decision_at_its_original_tau(self):
        """Root 16:05 item 1: "The already specified postdecision case remains separate": the
        abort follows the receipted decision; its point says a decision was logged, the
        decision stays at n = 44, and the follow-up is truncated."""
        status, events, tree = self.runs[('post_decision', False)]
        self.assertEqual(status, 'aborted')
        (end,) = of(events, 'trial_aborted')
        (owed,) = of(events, 'abort_owed')
        (decision,) = of(events, 'decision')
        self.assertEqual((end['body']['reason'], owed['body']['decision_logged']),
                         ('operator_discretion', True))
        self.assertLess(decision['seq'], owed['seq'])
        self.assertTrue(of(events, 'traffic_switch'), 'the receipt came before the switch')
        _summary, obj = cap.build(tree)
        self.assertEqual((obj['decision']['n'], obj['decision_status']), (CROSS_N, 'receipted'))
        self.assertGreater(end['body']['completion']['arrivals_not_run'], 0)

    def test_a_post_decision_abort_before_the_receipt_leaves_the_decision_provisional(self):
        """The matched external-receipt rule (root 21:14; 16:05 item 1): an abort taken while
        the decision's own blocking anchor has no receipt keeps the decision at its tau as a
        PROVISIONAL event -- logged, labelled, never reported as the result -- and nothing
        post-switch runs.  Its control is the receipted run above."""
        status, events, tree = self.runs[('post_decision_provisional', False)]
        self.assertEqual(status, 'aborted')
        (decision,) = of(events, 'decision')
        (owed,) = of(events, 'abort_owed')
        self.assertEqual((decision['body']['n'], decision['body']['monitor_seq']),
                         (CROSS_N, crossing(events)['seq']))
        self.assertEqual((owed['body']['decision_logged'], owed['body']['reason']),
                         (True, 'operator_discretion'))
        self.assertEqual((of(events, 'traffic_switch'), of(events, 'arm_assigned_by_decision')),
                         ([], []))
        self.assertEqual([c for c, _d in tree.verify_fails()], [])
        _summary, obj = cap.build(tree)
        self.assertEqual(obj['eligibility']['crossing']['verdict'], 'acted_on')
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision_status']),
                         (builder.PROVISIONAL_LABEL, False, 'provisional'))
        self.assertEqual(obj['decision']['n'], CROSS_N)

    def test_the_orchestrator_acted_on_exactly_the_shared_classification(self):
        """The spy records the orchestrator's classification of every look at the moment it
        wrote it; the builder's (and the verifier's) whole-chain classification of the same
        looks is identical, look by look."""
        for key in list(self.ABORTS) + ['control', 'recovered', 'post_decision',
                                        'post_decision_provisional']:
            with self.subTest(run=key):
                status, events, tree = self.runs[(key, False)]
                spy = self.spies[(key, False)]
                whole = builder.eligibility_object(events, tree.frozen_cfg(), 'T4')['looks']
                self.assertEqual(len(spy), len(whole))
                self.assertEqual([(s['seq'], s['eligible'], s['reason']) for s in spy],
                                 [(lk['seq'], lk['eligible'], lk['reason']) for lk in whole])


# --------------------------------------------------------------------------- #
# an unresolved worker that survives a resume
# --------------------------------------------------------------------------- #
def _drop_unresolved_records(real_append):
    """MUTATION (988baf7): the resume's refusal records nothing."""
    def append(self, etype, body, *, durable=False):
        if etype == 'worker_resolved' and body['state'] not in orch.RESOLVED_WORKER_STATES:
            return None
        return real_append(self, etype, body, durable=durable)
    return append


class UnresolvedAcrossResumeInProcess(unittest.TestCase):
    """The orchestrator dies with pair 44 in flight, after its episodes ran into complete spools
    and before they were ingested.  Resume 1 finds the workers alive and cannot confirm their
    kill: ``worker_resolved(alive_unresolved)``, refused.  Resume 2 finds them gone and reveals
    pair 44 from its spools -- the crossing look -- which the recorded unresolved worker makes
    NOT eligible."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.trees = []
        cls.runs = {mutated: cls.run_three(mutated) for mutated in (False, True)}

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    @classmethod
    def run_three(cls, mutated: bool):
        tree = cap.d3_tree()
        cls.trees.append(tree)
        fake = sup.FakeServers()
        polls = []

        def crash(world):
            if world.decision is None and world.pairs_enrolled == CROSS_N \
                    and world.open_arrivals:
                polls.append(1)
                if len(polls) == 2:
                    fake.survive_stop = True
                    raise sup.Crash()
        first = sup.run(tree, fake, hook=crash)
        fake.survive_stop = False
        first_len = len(tree.events())
        real_append = orch.World.append
        patch = (mock.patch.object(orch.World, 'append', _drop_unresolved_records(real_append))
                 if mutated else mock.patch.object(orch, 'ELIG_TEST_NOOP', None, create=True))
        with patch, mock.patch.object(orch, 'probe_worker', lambda *a, **k: 'alive'), \
                mock.patch.object(orch, 'kill_orphan_worker',
                                  lambda *a, **k: ('alive_unresolved', None)):
            second = sup.run(tree, fake, resume=True)
        with mock.patch.object(orch, 'probe_worker', lambda *a, **k: 'gone'):
            third = sup.run(tree, fake, resume=True)
        return (first, second, third), first_len, tree.events(), tree

    def test_the_crossing_revealed_after_the_record_is_not_acted_on(self):
        statuses, first_len, events, tree = self.runs[False]
        self.assertEqual(statuses, ('crashed', 'refused', 'aborted'))
        unresolved = [e for e in of(events, 'worker_resolved')
                      if e['body']['state'] == 'alive_unresolved']
        self.assertTrue(unresolved)
        self.assertGreater(unresolved[0]['seq'], first_len - 1, 'recorded by the resume')
        look = crossing(events)
        self.assertEqual((look['body']['shadow']['action'], look['body']['n']),
                         ('deploy_candidate', CROSS_N))
        self.assertGreater(look['seq'], unresolved[0]['seq'])
        self.assertEqual(of(events, 'decision'), [])
        self.assertEqual(of(events, 'trial_aborted')[-1]['body']['reason'], 'unresolved_worker')
        self.assertEqual(tree.verify_fails(), [])
        rows = cap.verifier_rows(tree, 'reference_rule.agreement')
        self.assertEqual([(s, r['consequence'], r['no_decision_reason']) for s, r in rows],
                         [('INFO', NOT_ACTED, 'unresolved_worker')])
        _summary, obj = cap.build(tree)
        self.assertEqual((obj['primary_result'], obj['crossing_not_acted_on']['n'],
                          obj['crossing_not_acted_on']['no_decision_reason']),
                         (builder.ABORT_INCOMPLETE_LABEL, CROSS_N, 'unresolved_worker'))

    def test_mutation_the_unrecorded_worker_lets_the_same_look_decide(self):
        statuses, _first_len, events, tree = self.runs[True]
        self.assertEqual(statuses[:2], ('crashed', 'refused'))
        self.assertEqual([e for e in of(events, 'worker_resolved')
                          if e['body']['state'] == 'alive_unresolved'], [])
        (decision,) = of(events, 'decision')
        self.assertEqual((decision['body']['n'], decision['body']['monitor_seq']),
                         (CROSS_N, crossing(events)['seq']))


# --------------------------------------------------------------------------- #
# one function, one classification
# --------------------------------------------------------------------------- #
THREE = {'orchestrator': LIVE / 'lab_orchestrator.py', 'verifier': LIVE / 'lab_verify_log.py',
         'builder': LIVE / 'build_live_ab_results.py'}


def called_names(source: str) -> set:
    """The attribute or plain names every Call node of ``source`` calls."""
    out = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            fn = node.func
            out.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, 'id', None))
    return out


def blanket_classifier(events, cap_, **kw):
    """NEGATIVE CONTROL: a classification that exempts every look after the first crossing when
    the trial LATER aborted -- a blanket exemption read from the terminal record."""
    got = lab_eventlog.decision_eligibility(events, cap_, **kw)
    if any(e['type'] == 'trial_aborted' for e in events) and got['decision_seq'] is None:
        for lk in got['looks']:
            lk.update(eligible=False, reason='trial_aborted_later')
    return got


class SameClassificationTests(unittest.TestCase):

    def test_the_three_paths_call_the_one_function_and_not_the_point_alone(self):
        for who, path in THREE.items():
            with self.subTest(path=who):
                names = called_names(path.read_text('utf-8'))
                self.assertIn('decision_eligibility', names)
                self.assertNotIn('no_decision_point', names)
        # negative control: the 159e747 verifier composed its own reading around the point
        old = subprocess.run(['git', '-C', str(REPO), 'show',
                              '159e747:experiments/live_ab/lab_verify_log.py'],
                             capture_output=True, text=True, check=False)
        if old.returncode != 0:
            self.skipTest('git history is not available')
        names = called_names(old.stdout)
        self.assertIn('no_decision_point', names)
        self.assertNotIn('decision_eligibility', names)

    def test_the_spy_sees_the_orchestrator_the_verifier_and_the_builder(self):
        tree = sup.Tree('T4', pairs=4)
        self.addCleanup(tree.close)
        real = lab_eventlog.decision_eligibility
        callers: list = []

        def spy(*a, **k):
            callers.append(sys._getframe(1).f_globals.get('__name__'))
            return real(*a, **k)
        with mock.patch.object(lab_eventlog, 'decision_eligibility', spy):
            self.assertEqual(sup.run(tree, sup.FakeServers()), 'ended')
            n_orch = callers.count('lab_orchestrator')
            self.assertEqual(tree.verify_fails(), [])
            cap.build(tree)
        self.assertEqual(n_orch, len(of(tree.events(), 'monitor_update')),
                         'the orchestrator classified every look it wrote')
        self.assertIn('lab_verify_log', callers)
        self.assertIn('build_live_ab_results', callers)

    def test_every_look_classified_by_its_prefix_equals_the_whole_chain(self):
        """What the orchestrator had (the chain before the look) and what the verifier and the
        builder read (the whole chain) classify every look alike, on chains with an owed abort,
        a triggered abort and a normal decision.  Negative control: a blanket classifier, which
        reads the trial's later abort, does not."""
        tree = cap.d3_tree()
        self.addCleanup(tree.close)
        fake = sup.FakeServers()
        fake.restart_raises = lab_common.PreflightError
        self.assertEqual(sup.run(tree, fake, hook=sup.CrashPlan(fake, pairs=(CROSS_N,))),
                         'aborted')
        events = tree.events()
        chains = [events] + [_chain(('monitor_update', dict(LOOK, n=43)), ('abort_owed', OWED),
                                    ('monitor_update', LOOK), ('trial_aborted', {}))]
        for classify, same in ((lab_eventlog.decision_eligibility, True),
                               (blanket_classifier, False)):
            for chain in chains:
                whole = classify(chain, CAP)['looks']
                prefix = [(lk['seq'],) + tuple(
                    (lambda nl: (nl['eligible'], nl['reason']))(classify(
                        [e for e in chain if e['seq'] < lk['seq']], CAP,
                        next_trigger=lk['trigger'])['next_look']))
                    for lk in whole]
                pairs = [(lk['seq'], lk['eligible'], lk['reason']) for lk in whole]
                if same:
                    self.assertEqual(prefix, pairs)
                    self.assertTrue(any(not lk['eligible'] for lk in whole))
                elif chain is events:
                    self.assertNotEqual(prefix, pairs, 'the negative control must differ')


# --------------------------------------------------------------------------- #
# nothing decision-defining moved
# --------------------------------------------------------------------------- #
FIVE = ('lab_monitor.py', 'lab_reference_rule.py', 'lab_coin.py', 'lab_design.py',
        'lab_enclosure.py')


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(REPO)] + list(args), capture_output=True, text=True,
                          check=False)


class DecisionCodeBytesTests(unittest.TestCase):

    def test_the_five_files_are_the_b049307_blobs(self):
        if _git('rev-parse', '--verify', 'b049307^{commit}').returncode != 0:
            self.skipTest('git history is not available')
        for name in FIVE:
            with self.subTest(name=name):
                want = _git('rev-parse', 'b049307:experiments/live_ab/%s' % name).stdout.strip()
                got = _git('hash-object', str(LIVE / name)).stdout.strip()
                self.assertEqual(got, want)
        # negative control: a copy with one byte more is another blob
        tmp = Path(tempfile.mkdtemp(prefix='elig_bytes_'))
        self.addCleanup(shutil.rmtree, tmp, True)
        copy_path = tmp / 'lab_monitor.py'
        copy_path.write_bytes((LIVE / 'lab_monitor.py').read_bytes() + b'#')
        self.assertNotEqual(_git('hash-object', str(copy_path)).stdout.strip(),
                            _git('rev-parse', 'b049307:experiments/live_ab/lab_monitor.py')
                            .stdout.strip())

    def test_the_monitor_block_of_the_config_is_unchanged(self):
        if _git('rev-parse', '--verify', 'b049307^{commit}').returncode != 0:
            self.skipTest('git history is not available')
        old = json.loads(_git('show', 'b049307:experiments/live_ab/config.json').stdout)
        new = json.loads((LIVE / 'config.json').read_text('utf-8'))
        self.assertEqual(new['monitor'], old['monitor'])
        self.assertEqual(lab_common.rule_block_sha256(new), lab_common.rule_block_sha256(old))


if __name__ == '__main__':                                   # pragma: no cover
    unittest.main()
