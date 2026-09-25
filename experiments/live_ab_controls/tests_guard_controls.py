"""Controls of seven guards no control exercised at 8f0b4ae (the final adversarial verification).

The independent verification of the EB1+EB5 subset at 8f0b4ae (session 60, 2026-09-25) wrote 105
mutants of the code root's rulings concern and ran each against its controls.  Seven that are not
equivalent SURVIVED -- every control and every suite still passed with the guard removed -- so
each guard below was correct but unobserved.  This module gives each one a control on the
production code and, beside it, a MUTATION control: the same function recompiled from its own
source with exactly the verifier's edit (:func:`mutant`, which refuses when the edited text is not
found exactly once), showing the chain the guard prevents.  No production byte is changed.

* :class:`UnresolvedFollowUpInProcess` (W6; root 21:14 item 1, "A phase with a live or
  unaccounted worker remains incomplete"; repair contract EB5): a follow-up worker whose kill is
  never confirmed is recorded ``alive_unresolved``; ``_w_resolve_worker`` frees its permit slot,
  so only the ``unresolved_seen`` guard of ``_w_dispatch_follow_up`` ends the follow-up cohort.
  Control: nothing is assigned or started after the record.  Mutation: the freed slot is refilled
  (all twelve follow-up arrivals run instead of three).  The verifier FAILs neither chain (observed
  when this module was written): it has no rule for a dispatch after an unresolved record.
* :class:`FrozenBranchTests` (R6f; root
  ``reviews/decision_receipt_metadata_ruling_20260924_0324.md``): a decision receipt whose commit
  IS the anchor's file, pushed, but to another branch of the anchor repository.
  ``anchor_commit_problem`` checks ancestry against the branch the row itself names, so only the
  frozen-branch clause of ``decision_evidence_verdict`` refuses it.  (The existing
  ``other_branch`` variant pairs that branch with a commit the repository does not hold, which the
  commit check refuses anyway.)
* :class:`CloseWithOpenWorkInProcess` (E6; root 16:05 item 2; protocol 6.4 and 14.6, amendment
  v3): ``close_trial('ended')`` reached with the crossing pair open and no decision closes as an
  abort with ``abort_owed(close_with_open_work)`` written before its drain.  Mutation: an ended
  trial whose chain carries an ``abort_owed`` -- which the verifier does not FAIL either (observed
  when this module was written; no verifier rule reads ``trial_ended`` after ``abort_owed``).
* :class:`LookGuardInProcess` (E3, E17; protocol 6.4, amendment v3: "If a look ever finds an abort
  owed in memory that no path has written, the look writes it first (``look_guard``) and records a
  finding"): an owed abort kept in memory only (a supervision abort, and an aborting close) -- the
  look writes ``abort_owed(look_guard)``, records the finding and takes no decision.  Mutations:
  the guard removed, and its closing branch removed, each decide during the abort's drain.
* :class:`TwoOwedReasonsInProcess` (E18; protocol 12.2 row 31, "written once per reason"): an
  identity-changing restart owes ``server_identity``; a down inside its drain finds the server at
  the cap, which outranks it.  Both points are written.  Mutation (one ``abort_owed`` per chain):
  the cap abort has no point and the verifier FAILs ``abort_point_missing``.
* :class:`NoRestartDuringOwedAbortInProcess` (C8; ``supervise_down`` item 5, "unless an abort is
  already owed"; root 21:14 item 1): a down inside the drain of a non-cap owed abort restarts
  nothing.  Mutation: a ``server_restarted`` after the ``abort_owed``.  Protocol 5.3 states "nothing
  is restarted" for the cap case only; this control fixes the code's behaviour, not new prose.
* :class:`LateAbortPointTests` (E12; ``lab_verify_log._check_decision_eligibility``): an
  ``abort_owed`` written AFTER its ``trial_aborted`` is not its point; mutation (any ``abort_owed``
  anywhere) accepts it.

The two production chains with an identity-changing restart (``props_sha256`` forced by the
in-process ``lab_server``) also carry the verifier's ``server.lifecycle`` ``verified_start`` FAIL
(the restarted ``/props`` are not the golden object's); those controls assert the rows they are
about, not a whole-chain PASS.  Outside the ``experiments/live_ab/tests_*.py`` glob on purpose
(repair contract, placement).  Prepared and checked by AI agent sessions; not human peer review or
author sign-off (protocol 14.7).
"""
from __future__ import annotations

import __future__
import inspect
import shutil
import sys
import tempfile
import textwrap
import time
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
for _p in (str(HERE), str(LIVE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lab_common                                                       # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import lab_verify_log                                                   # noqa: E402
import receipt_fixture as rf                                            # noqa: E402
import tests_decision_eligibility as elig                               # noqa: E402
import tests_eb1_cap_estimand as cap                                    # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_receipt_attribution as attr                            # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402
from lab_common import canonical_json, sha256_canonical                 # noqa: E402

setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule

CROSS_N = elig.CROSS_N            # the D3 tree deploys at n = 44 (pair 44 = arrivals 87, 88)
NOT_ACTED = elig.NOT_ACTED


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


class MutationNotApplicable(AssertionError):
    """The text a mutation edits is not in the function exactly once."""


def mutant(fn, old: str, new: str):
    """MUTATION: ``fn`` recompiled from its own source text with ``old`` (the text as it stands in
    the file, indentation included) replaced by ``new``, bound to ``fn``'s LIVE module globals.
    Refuses (:class:`MutationNotApplicable`) unless ``old`` occurs exactly once, so a control
    whose mutation no longer applies errors visibly instead of passing."""
    src = inspect.getsource(fn)
    if src.count(old) != 1:
        raise MutationNotApplicable('mutation text found %d times in %s: %r'
                                    % (src.count(old), fn.__qualname__, old[:70]))
    code = compile(textwrap.dedent(src.replace(old, new)), inspect.getsourcefile(fn), 'exec',
                   flags=__future__.annotations.compiler_flag, dont_inherit=True)
    scratch: dict = {}
    exec(code, dict(fn.__globals__), scratch)                          # noqa: S102
    made = scratch[fn.__name__]
    out = types.FunctionType(made.__code__, fn.__globals__, fn.__name__, made.__defaults__,
                             made.__closure__)
    out.__kwdefaults__ = made.__kwdefaults__
    return out


def _noop_patch():
    return mock.patch.object(orch, 'GUARD_TEST_NOOP', None, create=True)


class RunsCase(unittest.TestCase):
    """``setUpClass`` runs each scenario once (``run_one(key)``); a mutation that does not
    apply is kept and raised by the test that reads it, so the unmutated control still runs
    (on a tree whose source already carries the mutant, that control is what fails)."""

    runs: dict = {}
    trees: list = []

    @classmethod
    def run_all(cls, keys, run_one) -> None:
        cls.trees, cls.runs = [], {}
        for key in keys:
            try:
                cls.runs[key] = run_one(key)
            except MutationNotApplicable as exc:
                cls.runs[key] = exc

    @classmethod
    def tearDownClass(cls) -> None:
        for tree in cls.trees:
            tree.close()

    def run_of(self, key):
        got = self.runs[key]
        if isinstance(got, MutationNotApplicable):
            raise got
        return got


# --------------------------------------------------------------------------- #
# W6: an unresolved follow-up worker ends all dispatch
# --------------------------------------------------------------------------- #
class StuckFollowUpWorld(sup.SupWorld):
    """``SupWorld`` whose FIRST follow-up attempt never finishes and whose kill is never
    confirmed (``kill`` returns false: the exit could not be confirmed)."""

    stuck: int | None = None

    def finished(self, att):                                 # type: ignore[override]
        if att.post_decision and type(self).stuck in (None, att.arrival):
            type(self).stuck = att.arrival
            return None
        return super().finished(att)

    def kill(self, att) -> bool:                             # type: ignore[override]
        if att.arrival == type(self).stuck:
            return False
        return super().kill(att)


class PastTheHardCap:
    """Hook: once ``after`` follow-up arrivals were dispatched, put the stuck attempt one second
    past the frozen hard cap (as if that time had passed), so the next pump kills it."""

    def __init__(self, after: int = 3) -> None:
        self.after, self.fired = after, False

    def __call__(self, world) -> None:
        stuck = StuckFollowUpWorld.stuck
        if self.fired or stuck is None or world.post_decision_dispatched < self.after:
            return
        att = world.attempts.get(stuck)
        if att is None or att.revealed:
            return
        self.fired = True
        att.dispatched_mono = time.monotonic() - (world.hard_cap_s + 1.0)


W6_OLD = ('    if self.unresolved_seen:\n'
          '        return False                  # EB5: an unresolved worker ends all dispatch')
W6_NEW = '    if False:\n        return False'


class UnresolvedFollowUpInProcess(RunsCase):
    """The D3 tree: the decision at n = 44 is receipted, the follow-up cohort (arrivals 89-100)
    runs; its first arrival hangs and its kill is never confirmed."""

    @classmethod
    def setUpClass(cls) -> None:
        def run_one(mutated: bool):
            patch = (mock.patch.object(orch.World, 'dispatch_follow_up',
                                       mutant(orch._w_dispatch_follow_up, W6_OLD, W6_NEW))
                     if mutated else _noop_patch())
            tree = cap.d3_tree()
            cls.trees.append(tree)
            StuckFollowUpWorld.stuck = None
            with patch, mock.patch.object(sup, 'SupWorld', StuckFollowUpWorld):
                status = sup.run(tree, sup.FakeServers(), hook=PastTheHardCap())
            return status, tree.events(), StuckFollowUpWorld.stuck, tree
        cls.run_all((False, True), run_one)

    def record(self, events, stuck) -> dict:
        (rec,) = [e for e in of(events, 'worker_resolved')
                  if e['body']['state'] == 'alive_unresolved']
        self.assertEqual(rec['body']['arrival'], stuck)
        self.assertIn(stuck, {e['body']['arrival'] for e in of(events, 'arm_assigned_by_decision')},
                      'the unresolved worker is a follow-up attempt')
        return rec

    def after(self, events, rec, etype) -> list:
        return [e['body']['arrival'] for e in of(events, etype) if e['seq'] > rec['seq']]

    def test_nothing_is_assigned_or_started_after_the_unresolved_record(self):
        status, events, stuck, tree = self.run_of(False)
        self.assertEqual(status, 'aborted')
        rec = self.record(events, stuck)
        self.assertEqual(self.after(events, rec, 'arm_assigned_by_decision'), [])
        self.assertEqual(self.after(events, rec, 'episode_started'), [])
        (end,) = of(events, 'trial_aborted')
        self.assertEqual(end['body']['reason'], 'unresolved_worker')
        self.assertGreater(end['body']['completion']['follow_up_not_run'], 0,
                           'arrivals remained that the guard withheld')
        self.assertEqual(of(events, 'trial_ended'), [])
        self.assertEqual(tree.verify_fails(), [])

    def test_mutation_without_the_guard_the_freed_slot_is_refilled(self):
        status, events, stuck, _tree = self.run_of(True)
        rec = self.record(events, stuck)
        self.assertTrue(self.after(events, rec, 'arm_assigned_by_decision'),
                        'the follow-up cohort continues beside the unresolved worker')
        self.assertTrue(self.after(events, rec, 'episode_started'))


# --------------------------------------------------------------------------- #
# R6f: the pushed commit on another branch of the anchor repository
# --------------------------------------------------------------------------- #
R6F_OLD = '    if ((anchor_branch and branch != anchor_branch)'
R6F_NEW = '    if ((False)'
OTHER = 'scratch/other'


class FrozenBranchTests(unittest.TestCase):
    """``judge_receipt_line`` on a complete external decision row whose commit carries exactly
    this anchor's file and is pushed -- to ``origin/scratch/other``, never to the frozen
    ``anchor.branch``."""

    def setUp(self) -> None:
        self.anchor, self.request = attr.request_pair(5, 'decision')
        root = Path(tempfile.mkdtemp(prefix='guard_r6f_'))
        self.addCleanup(shutil.rmtree, root, True)
        self.repo = rf.AnchorRepo(root / 'anchor_repo')
        self.anchors_dir = self.repo.root / 'anchors'
        self.path = self.anchors_dir / 'anchor_5.json'
        self.want = sha256_canonical(lab_common.anchor_file_object(attr.TRIAL, self.request))

    def commit_on(self, branch: str) -> str:
        self.repo.git('checkout', '-q', '-B', branch)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(canonical_json(lab_common.anchor_file_object(attr.TRIAL,
                                                                          self.request)),
                             encoding='utf-8')
        self.repo.git('add', '--', 'anchors/anchor_5.json')
        self.repo.git('commit', '-q', '--allow-empty', '-m', 'anchor on ' + branch)
        self.repo.git('push', '-q', 'origin', branch)
        commit = self.repo.git('rev-parse', 'HEAD').strip()
        self.repo.git('checkout', '-q', rf.ANCHOR_BRANCH)
        return commit

    def judge(self, commit: str, branch: str, *, mock_tree: bool) -> dict:
        row = rf.external_row(self.request, commit=commit, branch=branch)
        return orch.judge_receipt_line(
            attr.line(row), trial=attr.TRIAL,
            request_of={self.request['request_id']: self.request}.get,
            anchors={5: self.anchor}, resolved={}, resolving_sha={}, newest_anchor_seq=5,
            mock=mock_tree, anchor_branch=rf.ANCHOR_BRANCH,
            commit_check=self.repo.checker(self.anchors_dir, attr.TRIAL))

    def test_a_commit_pushed_to_another_branch_is_a_conflict_in_both_trees(self):
        commit = self.commit_on(OTHER)
        # the commit IS bound to this anchor on the branch the row names: the commit check
        # alone would accept it; on the frozen branch it is not
        self.assertIsNone(orch.anchor_commit_problem(self.repo.root, commit, OTHER, self.path,
                                                     self.want))
        self.assertEqual(orch.anchor_commit_problem(self.repo.root, commit, rf.ANCHOR_BRANCH,
                                                    self.path, self.want),
                         'not_on_pushed_branch')
        for mock_tree in (False, True):
            with self.subTest(mock_tree=mock_tree):
                got = self.judge(commit, OTHER, mock_tree=mock_tree)
                self.assertEqual((got['kind'], got['type'], got['body'].get('reason')),
                                 ('rejected', 'anchor_receipt_rejected', 'conflict'))

    def test_control_the_same_file_pushed_to_the_frozen_branch_is_the_receipt(self):
        commit = self.commit_on(rf.ANCHOR_BRANCH)
        got = self.judge(commit, rf.ANCHOR_BRANCH, mock_tree=False)
        self.assertEqual((got['kind'], got['type']), ('receipt', 'anchor_receipt'))

    def test_mutation_without_the_branch_clause_the_other_branch_row_is_the_receipt(self):
        commit = self.commit_on(OTHER)
        with mock.patch.object(orch, 'decision_evidence_verdict',
                               mutant(orch.decision_evidence_verdict, R6F_OLD, R6F_NEW)):
            got = self.judge(commit, OTHER, mock_tree=False)
        self.assertEqual((got['kind'], got['type']), ('receipt', 'anchor_receipt'))


# --------------------------------------------------------------------------- #
# E6 and E17: the close of an ENDED trial that finds open work and no decision
# --------------------------------------------------------------------------- #
class CloseEndedAt:
    """Hook: at the first poll that sees pair ``pair`` in flight before any decision, call
    ``close_trial('ended')`` -- a caller this module does not know -- then stop the loop (the
    close wrote the terminal record)."""

    def __init__(self, pair: int = CROSS_N) -> None:
        self.pair, self.fired, self.open, self.status, self.world = pair, False, None, None, None

    def __call__(self, world) -> None:
        if self.fired or world.decision is not None or world.pairs_enrolled != self.pair \
                or not world.open_arrivals:
            return
        self.fired, self.world = True, world
        self.open = sorted(world.open_arrivals)
        self.status = world.close_trial('ended')
        raise sup.Crash()


E6_OLD = "    if status == 'ended' and self.decision is None and any("
E6_NEW = "    if False and status == 'ended' and self.decision is None and any("


def run_close(tree, *, patches=()) -> CloseEndedAt:
    hook = CloseEndedAt()
    with mock.patch.multiple(orch.World, **dict(patches)) if patches else _noop_patch():
        sup.run(tree, sup.FakeServers(), hook=hook)
    return hook


class CloseWithOpenWorkInProcess(RunsCase):

    @classmethod
    def setUpClass(cls) -> None:
        def run_one(mutated: bool):
            patches = ({'close_trial': mutant(orch._w_close_trial, E6_OLD, E6_NEW)}
                       if mutated else {})
            tree = cap.d3_tree()
            cls.trees.append(tree)
            return run_close(tree, patches=patches), tree.events(), tree
        cls.run_all((False, True), run_one)

    def test_it_closes_as_an_abort_whose_point_precedes_its_drain(self):
        hook, events, tree = self.run_of(False)
        self.assertEqual(hook.status, 'aborted')
        self.assertEqual(len(hook.open), 2, 'both arrivals of pair 44 were open')
        (owed,) = of(events, 'abort_owed')
        self.assertEqual((owed['body']['reason'], owed['body']['source'],
                          owed['body']['decision_logged'], sorted(owed['body']['open_arrivals'])),
                         ('harness_defect', 'close_with_open_work', False, hook.open))
        reveals = [e for e in of(events, 'episode_revealed') if e['body']['arrival'] in hook.open]
        self.assertEqual(len(reveals), 2)
        self.assertTrue(all(e['seq'] > owed['seq'] for e in reveals))
        (end,) = of(events, 'trial_aborted')
        self.assertEqual(end['body']['reason'], 'harness_defect')
        self.assertEqual((of(events, 'trial_ended'), of(events, 'decision')), ([], []))
        look = elig.crossing(events)
        self.assertEqual((look['body']['n'], look['body']['shadow']['action']),
                         (CROSS_N, 'deploy_candidate'))
        self.assertGreater(look['seq'], owed['seq'])
        self.assertEqual(tree.verify_fails(), [])
        rows = cap.verifier_rows(tree, 'reference_rule.agreement')
        self.assertEqual([(s, r['consequence'], r['abort_source']) for s, r in rows],
                         [('INFO', NOT_ACTED, 'close_with_open_work')])

    def test_mutation_without_the_branch_it_ends_over_an_owed_abort(self):
        hook, events, _tree = self.run_of(True)
        self.assertEqual(hook.status, 'ended')
        self.assertEqual(len(of(events, 'trial_ended')), 1)
        self.assertEqual(of(events, 'trial_aborted'), [])
        self.assertEqual([e['body']['source'] for e in of(events, 'abort_owed')], ['look_guard'],
                         'an ended trial whose chain says an abort was owed')


# --------------------------------------------------------------------------- #
# E3 and E17: the look guard
# --------------------------------------------------------------------------- #
E3_OLD = "        if owed is not None and cls['next_look']['eligible']:"
E17_OLD = "        if owed is None and self.closing and self.decision is None:"
GUARD_NEW = '        if False:'
_REAL_WRITE = orch.World.write_abort_owed


def owe_in_memory(self, reason, source='supervision', *, override=False):
    """A supervision abort owed IN MEMORY only (a path that did not write its point)."""
    if override or self.pending_abort is None:
        self.pending_abort = str(reason)


def close_write_dropped(self, reason, source):
    """The close's own ``abort_owed`` not written (a path that did not write its point); every
    other writer, the look guard included, is the production one."""
    if source in ('close_with_open_work', 'abort_raised'):
        return None
    return _REAL_WRITE(self, reason, source)


class Remember:
    """Hook wrapper keeping the world (its in-memory ``findings`` are not chained)."""

    def __init__(self, inner=None) -> None:
        self.inner, self.world = inner, None

    def __call__(self, world) -> None:
        self.world = world
        if self.inner is not None:
            self.inner(world)


class LookGuardInProcess(RunsCase):
    """(A) a refused restart while pair 44 is in flight owes ``harness_defect`` -- kept in
    memory only; (B) ``close_trial('ended')`` over pair 44 with the close's own point not
    written.  In both the drain reveals pair 44, whose look crosses (deploy at n = 44)."""

    @classmethod
    def setUpClass(cls) -> None:
        real_gate = orch.World._look_eligibility

        def run_one(key):
            case, mutated = key
            patches: dict = {}
            if mutated is not None:
                patches['_look_eligibility'] = mutant(
                    real_gate, E3_OLD if mutated == 'E3' else E17_OLD, GUARD_NEW)
            tree = cap.d3_tree()
            cls.trees.append(tree)
            if case == 'A':
                fake = sup.FakeServers()
                fake.restart_raises = lab_common.PreflightError
                hook = Remember(sup.CrashPlan(fake, pairs=(CROSS_N,)))
                patches['owe_abort'] = owe_in_memory
                with mock.patch.multiple(orch.World, **patches):
                    status = sup.run(tree, fake, hook=hook)
                world = hook.world
            else:
                patches['write_abort_owed'] = close_write_dropped
                close = run_close(tree, patches=patches)
                status, world = close.status, close.world
            return status, tree.events(), world, tree
        cls.run_all((('A', None), ('A', 'E3'), ('B', None), ('B', 'E17'), ('B', 'E3')),
                    run_one)

    def test_the_look_writes_the_point_records_the_finding_and_takes_no_decision(self):
        for case in ('A', 'B'):
            with self.subTest(case=case):
                status, events, world, tree = self.run_of((case, None))
                self.assertEqual(status, 'aborted')
                self.assertEqual([(e['body']['reason'], e['body']['source'],
                                   e['body']['decision_logged'])
                                  for e in of(events, 'abort_owed')],
                                 [('harness_defect', 'look_guard', False)])
                owed = of(events, 'abort_owed')[0]
                self.assertIn('abort_point_written_by_look_guard:harness_defect',
                              world.findings)
                self.assertEqual(of(events, 'decision'), [])
                look = elig.crossing(events)
                self.assertEqual(look['body']['n'], CROSS_N)
                self.assertGreater(look['seq'], owed['seq'], 'the point precedes the look')
                self.assertEqual(of(events, 'trial_aborted')[-1]['body']['reason'],
                                 'harness_defect')
                self.assertEqual(tree.verify_fails(), [])

    def test_mutation_without_the_guard_the_drain_decides(self):
        for key in (('A', 'E3'), ('B', 'E17'), ('B', 'E3')):
            with self.subTest(case=key):
                _status, events, world, _tree = self.run_of(key)
                (decision,) = of(events, 'decision')
                self.assertEqual((decision['body']['kind'], decision['body']['n']),
                                 ('deploy_candidate', CROSS_N))
                self.assertNotIn('look_guard',
                                 [e['body']['source'] for e in of(events, 'abort_owed')])
                self.assertFalse([f for f in world.findings if 'look_guard' in f])


# --------------------------------------------------------------------------- #
# E18 and C8: a down inside the drain of an owed identity abort
# --------------------------------------------------------------------------- #
class IdentityThenDown:
    """Hook.  The server exits at the first poll that sees each pair of ``early`` in flight
    (plain supervised restarts); at pair 44 it exits and its restart answers with other
    ``/props`` (``props_equal_previous`` false: ``server_identity`` owed, the server running);
    then, inside that abort's drain, it exits once more."""

    def __init__(self, fake: sup.FakeServers, early=()) -> None:
        self.fake, self.early, self.done, self.stage = fake, set(early), set(), 0

    def __call__(self, world) -> None:
        if world.decision is not None or not world.open_arrivals:
            return
        pair = world.pairs_enrolled
        if pair in self.early and pair not in self.done and world.pending_abort is None:
            self.done.add(pair)
            self.fake.crash('coder')
        elif self.stage == 0 and pair == CROSS_N and world.pending_abort is None:
            self.stage = 1
            self.fake.overrides = {'props_sha256': 'e' * 64}
            self.fake.crash('coder')
        elif self.stage == 1 and world.pending_abort == 'server_identity' \
                and self.fake.alive(self.fake.current['coder']):
            self.stage = 2
            self.fake.crash('coder')


E18_OLD = ("        if any(e['type'] == 'abort_owed' and e['body'].get('reason') == reason\n"
           "               for e in self.log.events):")
E18_NEW = "        if any(e['type'] == 'abort_owed' for e in self.log.events):"
C8_OLD = ('        if self.pending_abort is not None:\n'
          '            return                      # an abort is owed: the trial drains, nothing '
          'restarts')
C8_NEW = '        if False:\n            return'


def run_identity(tree, early, patches: dict) -> tuple[str, IdentityThenDown]:
    fake = sup.FakeServers()
    hook = IdentityThenDown(fake, early=early)
    with mock.patch.multiple(orch.World, **patches) if patches else _noop_patch():
        status = sup.run(tree, fake, hook=hook)
    return status, hook


def lifecycle(events) -> list:
    return [(e['seq'], e['type']) for e in events
            if e['type'] in ('server_down', 'server_restarted', 'abort_owed', 'trial_aborted')]


class TwoOwedReasonsInProcess(RunsCase):
    """Two supervised restarts at pairs 1 and 2, the identity-changing third at pair 44, and a
    down inside its drain: the fourth restart the cap forbids."""

    @classmethod
    def setUpClass(cls) -> None:
        def run_one(mutated: bool):
            patches = ({'write_abort_owed': mutant(orch.World.write_abort_owed, E18_OLD,
                                                   E18_NEW)} if mutated else {})
            tree = cap.d3_tree()
            cls.trees.append(tree)
            status, hook = run_identity(tree, (1, 2), patches)
            return status, hook, tree.events(), tree
        cls.run_all((False, True), run_one)

    def test_both_reasons_are_written_and_the_cap_abort_has_its_point(self):
        status, hook, events, tree = self.run_of(False)
        self.assertEqual((status, hook.stage), ('aborted', 2))
        self.assertEqual(len(of(events, 'server_restarted')), cap.CAP)
        self.assertEqual([(e['body']['reason'], e['body']['source'])
                          for e in of(events, 'abort_owed')],
                         [('server_identity', 'supervision'),
                          (orch.RESTART_CAP_REASON, 'supervision')])
        (end,) = of(events, 'trial_aborted')
        self.assertEqual(end['body']['reason'], orch.RESTART_CAP_REASON)
        self.assertEqual(of(events, 'decision'), [])
        fails = {(c, d.get('rule')) for c, d in tree.verify_fails()}
        self.assertNotIn(('reference_rule.agreement', 'abort_point_missing'), fails)
        self.assertNotIn(('server.lifecycle', 'cap_abort_iff_required'), fails)

    def test_mutation_one_point_per_chain_leaves_the_cap_abort_without_its_point(self):
        status, _hook, events, tree = self.run_of(True)
        self.assertEqual(status, 'aborted')
        self.assertEqual([e['body']['reason'] for e in of(events, 'abort_owed')],
                         ['server_identity'])
        self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'],
                         orch.RESTART_CAP_REASON)
        fails = {(c, d.get('rule')) for c, d in tree.verify_fails()}
        self.assertIn(('reference_rule.agreement', 'abort_point_missing'), fails)


class NoRestartDuringOwedAbortInProcess(RunsCase):
    """The identity-changing restart at pair 44 is the first; the down inside its drain finds
    one restart used, below the cap."""

    @classmethod
    def setUpClass(cls) -> None:
        def run_one(mutated: bool):
            patches = ({'supervise_down': mutant(orch.World.supervise_down, C8_OLD, C8_NEW)}
                       if mutated else {})
            tree = cap.d3_tree()
            cls.trees.append(tree)
            status, hook = run_identity(tree, (), patches)
            return status, hook, tree.events(), tree
        cls.run_all((False, True), run_one)

    @staticmethod
    def restarts_after_the_point(events) -> list:
        (owed,) = of(events, 'abort_owed')
        return [s for s, t in lifecycle(events) if t == 'server_restarted' and s > owed['seq']]

    def test_a_down_inside_the_owed_abort_drain_restarts_nothing(self):
        status, hook, events, _tree = self.run_of(False)
        self.assertEqual((status, hook.stage), ('aborted', 2))
        (owed,) = of(events, 'abort_owed')
        self.assertEqual((owed['body']['reason'], owed['body']['source']),
                         ('server_identity', 'supervision'))
        downs = [s for s, t in lifecycle(events) if t == 'server_down']
        self.assertEqual(len(downs), 2)
        self.assertGreater(downs[1], owed['seq'], 'the second down is inside the drain')
        self.assertEqual(self.restarts_after_the_point(events), [])
        self.assertEqual(len(of(events, 'server_restarted')), 1)
        self.assertEqual(of(events, 'trial_aborted')[0]['body']['reason'], 'server_identity')
        self.assertEqual(of(events, 'decision'), [])

    def test_mutation_the_down_inside_the_drain_is_restarted(self):
        _status, hook, events, _tree = self.run_of(True)
        self.assertEqual(hook.stage, 2)
        self.assertEqual(len(self.restarts_after_the_point(events)), 1)


# --------------------------------------------------------------------------- #
# E12: the verifier's abort point must PRECEDE its trial_aborted
# --------------------------------------------------------------------------- #
E12_OLD = "                  if e['type'] == 'abort_owed' and int(e['seq']) < int(ev['seq'])}"
E12_NEW = "                  if e['type'] == 'abort_owed'}"


class LateAbortPointTests(unittest.TestCase):

    LATE = elig._chain(('monitor_update', dict(elig.LOOK, n=43)),
                       ('trial_aborted', {'reason': 'server_identity'}),
                       ('abort_owed', dict(elig.OWED, reason='server_identity')))
    EARLY = elig._chain(('monitor_update', dict(elig.LOOK, n=43)),
                        ('abort_owed', dict(elig.OWED, reason='server_identity')),
                        ('trial_aborted', {'reason': 'server_identity'}))

    def test_an_abort_owed_after_its_trial_aborted_is_not_its_point(self):
        self.assertEqual(elig.OrderingTests.verdict_rows(self.LATE, ['none']),
                         [('FAIL', 'abort_point_missing')])
        self.assertEqual(elig.OrderingTests.verdict_rows(self.EARLY, ['none']), [])

    def test_mutation_any_abort_owed_anywhere_accepts_the_late_one(self):
        with mock.patch.object(lab_verify_log, '_check_decision_eligibility',
                               mutant(lab_verify_log._check_decision_eligibility, E12_OLD,
                                      E12_NEW)):
            self.assertEqual(elig.OrderingTests.verdict_rows(self.LATE, ['none']), [])


class MutantHelperTests(unittest.TestCase):

    def test_the_helper_refuses_a_text_it_does_not_find_once(self):
        with self.assertRaises(MutationNotApplicable):
            mutant(orch._w_dispatch_follow_up, 'no such text', 'x')
        same = mutant(orch._w_dispatch_follow_up, W6_OLD, W6_OLD)
        self.assertIs(same.__globals__, orch._w_dispatch_follow_up.__globals__)


if __name__ == '__main__':
    unittest.main()
