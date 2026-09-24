"""Receipt attribution and the decision receipt's evidence, controlled before any outcome.

Root's BLOCKING finding on WIP 8df2558 (``reviews/eb1_receipt_attribution_review_20260924_0254.md``,
origin/main f855e45): ``World.ingest_receipts`` attributed a receipt line whose ``request_id``
no request carried to the NEWEST anchor; an ``ok`` line became a success-valued
``anchor_receipt`` carrying the line's ``created_at``; ``lab_eventlog.decision_receipt``
accepted it as the decision's external receipt (it checked ``anchor_seq`` and a server time);
and ``ANCHOR_BLOCK`` checks ``decision_receipted()`` before the pending anchor, so the traffic
could switch while the actual decision request was unreceipted.  Root's metadata ruling
(``reviews/decision_receipt_metadata_ruling_20260924_0324.md``, 3e18d69): protocol 12.4 has no
timestamp authority; a decision receipt clears the gate only when bound to the exact durable
request and anchor, with the pushed commit / anchor-head evidence, a comment whose body carries
the trial id, ``upto_seq``, ``upto_h`` and segment SHA-256 and whose returned metadata comes
from the response to that exact body, the response's ``id`` and ``node_id``, parsable
``created_at`` / ``updated_at`` and the raw-response SHA-256.

What is controlled here (each behaviour with its negative control; each production path with
a mutation that restores the defect and is caught):

* :class:`JudgeLineTests` -- ``lab_orchestrator.judge_receipt_line``, the rule every receipt
  line goes through: every rejection reason (``unknown_request``, ``stale``, ``malformed``,
  ``duplicate``, ``conflict``), every missing / inconsistent evidence item of
  ``receipt_fixture.EVIDENCE_VARIANTS`` in a dry-run (MOCK) tree and outside one, the MOCK
  receipt confined to MOCK trees; the complete row is the negative control of each.
* :class:`DecisionReceiptChainTests` -- ``lab_eventlog.decision_receipt`` (the gate's reading of
  the chain, also the verifier's and the builder's): every problem clause, and the 8df2558
  rule as a mutation (it accepts a receipt bound to nothing).
* :class:`AnchorWriterTests` -- ``lab_anchor``: ``post_comment`` now records ``node_id`` and the
  raw response (stubbed ``requests.post``, no network); the anchor file's bytes are unchanged;
  the row ``_handle`` writes in REAL mode (git and HTTP stubbed) is accepted by the
  orchestrator's rule, and the same row answering another body is refused.
* :class:`RuleDisagreementGuardTests` -- in process: were the ingest rule and the chain rule
  ever to disagree, the blocking anchor pauses instead of being re-requested for ever.
* :class:`ProdReceiptGate` -- the REAL production entry path: ``lab_orchestrator.py main()`` as
  a subprocess against ``lab_mock_server`` behind the EB1c shim (``tests_eb1_entry.EntryTree``;
  T1 with the MOCK-ONLY screening prefix of ``tests_eb1_cap_estimand``: the frozen band crosses
  to ``harm_keep_incumbent`` at tau = 39), with the anchor process ``eb1_withhold_anchor.py``
  (the unmodified ``lab_anchor --mock-receipt`` loop, which writes no receipt for the
  ``decision`` trigger).  The control writes the decision's receipt lines into the anchor
  spool as the anchor process would.  E1: while the decision anchor is pending, a
  success-valued external-shaped line with an UNKNOWN request id, a STALE one (the start
  anchor's request), a byte DUPLICATE, a MALFORMED line and one line per evidence variant --
  no decision receipt, no ``traffic_switch``, no post-decision dispatch, one
  ``anchor_receipt_rejected`` each; then the correct external receipt unlocks the SAME tree.
  E2: the same across a pause (``anchor_unavailable``) and ``--resume``, the correct receipt
  answering the decision request CARRIED OVER from the paused invocation; the resumed
  invocation re-reads the spool from its start and chains nothing twice (one chain event per
  spool line), and the restarted anchor process's byte-identical re-answers of requests it had
  already answered (``lab_anchor.serve`` re-reads ``requests.jsonl`` from its start -- an
  observation, not repaired here) are each a ``duplicate``, never a second receipt.  M1 / M2: the 8df2558
  attribution (``eb1_receipt_mutant_entry``), alone and with the 8df2558 gate, fails E1's
  assertions; with the old gate the traffic switches on the unknown line.

The trees are dry-run trees (their ``mock_overrides`` name every substitution), so a MOCK
receipt (no external claim at all) would be accepted there -- by design, and only there
(:class:`JudgeLineTests`); every line the production controls inject claims external evidence
and is judged by the full rule.  Nothing here reads a network: the "external" receipts are
synthetic (``receipt_fixture``), so the controls show what the RULE accepts and refuses,
never that a real comment exists.

**Run the production-path class alone, on a quiescent host**, as ``tests_eb1_entry``.
Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
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
import eb1_receipt_mutant_entry as mutant                               # noqa: E402
import lab_anchor                                                       # noqa: E402
import lab_common                                                       # noqa: E402
import lab_eventlog                                                     # noqa: E402
import lab_orchestrator as orch                                         # noqa: E402
import receipt_fixture as rf                                            # noqa: E402
import tests_eb1_cap_estimand as cap                                    # noqa: E402
import tests_eb1_entry as entry                                         # noqa: E402
import tests_eb1_supervision as sup                                     # noqa: E402
from lab_common import (canonical_json, sha256_bytes, sha256_canonical,   # noqa: E402
                        sha256_text)

TRIAL = 'T4'
BRANCH = rf.ANCHOR_BRANCH
REASONS = ('unknown_request', 'stale', 'malformed', 'duplicate', 'conflict')

setUpModule = entry.setUpModule
tearDownModule = entry.tearDownModule


def of(events, etype) -> list:
    return [e for e in events if e['type'] == etype]


def request_pair(anchor_seq: int, trigger: str) -> tuple[dict, dict]:
    """A chained ``anchor`` body and the durable request it was sent as (the fields
    ``World.request_anchor`` writes)."""
    body = rf.anchor_body(anchor_seq, trigger)
    request = {'request_id': body['request_id'], 'trial': TRIAL,
               'anchor_seq': body['anchor_seq'], 'upto_seq': body['upto_seq'],
               'upto_h': body['upto_h'], 'segment_index': body['segment_index'],
               'segment_bytes': body['segment_bytes'],
               'segment_sha256': body['segment_sha256'], 'trigger': trigger,
               'blocking': True, 'publish_segments': trigger == 'decision'}
    return body, request


def line(row) -> bytes:
    return canonical_json(dict(row)).encode('utf-8')


# --------------------------------------------------------------------------- #
# the rule every receipt line goes through
# --------------------------------------------------------------------------- #
class JudgeLineTests(unittest.TestCase):
    """``lab_orchestrator.judge_receipt_line``.  The world: a start anchor (seq 1, already
    receipted by the line ``start_line``), a periodic anchor (seq 3, unresolved) and the
    pending decision anchor (seq 5, the newest)."""

    def setUp(self) -> None:
        self.start_anchor, self.start = request_pair(1, 'trial_started')
        self.periodic_anchor, self.periodic = request_pair(3, 'every_25_completed_pairs')
        self.decision_anchor, self.decision = request_pair(5, 'decision')
        self.requests = {r['request_id']: r for r in (self.start, self.periodic,
                                                       self.decision)}
        self.anchors = {1: self.start_anchor, 3: self.periodic_anchor,
                        5: self.decision_anchor}
        self.start_line = line(rf.mock_row(self.start))
        self.resolved = {1: 'receipt'}
        self.resolving = {1: sha256_bytes(self.start_line)}
        # the anchor repository: the decision anchor's file committed and pushed (to a local
        # bare origin) exactly as lab_anchor.commit_and_push does -- the pushed commit the
        # complete row names (owner ruling R-push)
        tmp = Path(tempfile.mkdtemp(prefix='eb1r_judge_'))
        self.addCleanup(lambda: __import__('shutil').rmtree(tmp, ignore_errors=True))
        self.repo = rf.AnchorRepo(tmp / 'anchor_repo')
        self.anchors_dir = self.repo.root / 'anchors'
        self.commit = self.repo.commit_anchor(self.anchors_dir, TRIAL, self.decision)
        self.check = self.repo.checker(self.anchors_dir, TRIAL)

    def ext(self, request, **kw) -> dict:
        """``receipt_fixture.external_row`` naming this repository's pushed anchor commit."""
        kw.setdefault('commit', self.commit)
        return rf.external_row(request, **kw)

    def judge(self, raw: bytes, *, mock_tree: bool = False, **over) -> dict:
        kw = dict(trial=TRIAL, request_of=self.requests.get, anchors=self.anchors,
                  resolved=self.resolved, resolving_sha=self.resolving, newest_anchor_seq=5,
                  mock=mock_tree, anchor_branch=BRANCH, commit_check=self.check)
        kw.update(over)
        return orch.judge_receipt_line(raw, **kw)

    def assertRejected(self, verdict: dict, reason: str, raw: bytes,
                       request_id: str | None) -> None:
        self.assertEqual((verdict['kind'], verdict['type']),
                         ('rejected', 'anchor_receipt_rejected'))
        self.assertEqual(verdict['body'], {'request_id': request_id, 'reason': reason,
                                           'raw_sha256': sha256_bytes(raw),
                                           'raw_bytes': len(raw)})
        self.assertIsNone(verdict['anchor_seq'], 'a rejected line is attributed to nothing')
        lab_eventlog.validate_event('anchor_receipt_rejected', verdict['body'])

    # -- the negative control of every rejection ------------------------------------------
    def test_the_complete_external_receipt_is_the_decision_receipt_in_both_trees(self):
        raw = line(self.ext(self.decision))
        for mock_tree in (False, True):
            with self.subTest(mock_tree=mock_tree):
                v = self.judge(raw, mock_tree=mock_tree)
                self.assertEqual((v['kind'], v['type'], v['anchor_seq'], v['request_id']),
                                 ('receipt', 'anchor_receipt', 5,
                                  self.decision['request_id']))
                body = v['body']
                lab_eventlog.validate_event('anchor_receipt', body)
                self.assertEqual(body['anchor_file_sha256'], sha256_canonical(
                    lab_common.anchor_file_object(TRIAL, self.decision_anchor)))
                self.assertEqual(body['comment_body_sha256'], sha256_text(
                    lab_common.anchor_comment_body(TRIAL, self.decision_anchor)))
                self.assertEqual(body['node_id_sha256'], sha256_text(rf.NODE_ID))
                self.assertEqual(lab_eventlog.decision_receipt_problems(
                    body, self.decision_anchor, TRIAL, mock=mock_tree), [],
                    'what the orchestrator chains, the chain rule accepts')

    # -- attribution ---------------------------------------------------------------------
    def test_an_unknown_request_id_is_never_attributed_whatever_its_evidence(self):
        """The finding's line: success-valued, with ``created_at`` and every other piece of
        evidence consistent with the pending decision anchor -- but a request id no durable
        request carries.  8df2558 chained it under the newest anchor (5)."""
        stranger = uuid.uuid4().hex
        raw = line(self.ext(dict(self.decision, request_id=stranger)))
        for mock_tree in (False, True):
            with self.subTest(mock_tree=mock_tree):
                self.assertRejected(self.judge(raw, mock_tree=mock_tree),
                                    'unknown_request', raw, stranger)

    def test_malformed_lines(self):
        rid = self.decision['request_id']
        good = self.ext(self.decision)
        cases = [
            (b'{"request_id":"%s","ok":tru' % rid.encode(), None),
            (b'[1, 2, 3]', None),
            (b'\xff\xfe not utf-8', None),
            (line(dict(good, request_id=None)), None),
            (line(dict(good, request_id=rid.upper())), None),
            (line(dict(good, request_id=rid[:31])), None),
            (line(dict(good, request_id='../../%s' % rid[:24])), None),
            (line(dict(good, ok='true')), rid),
            (line(dict(good, ok=None)), rid),
        ]
        for raw, want_rid in cases:
            with self.subTest(raw=raw[:40]):
                self.assertRejected(self.judge(raw), 'malformed', raw, want_rid)

    def test_duplicate_stale_and_conflict_for_a_resolved_anchor(self):
        # the byte-identical line that resolved the start anchor: duplicate
        self.assertRejected(self.judge(self.start_line), 'duplicate', self.start_line,
                            self.start['request_id'])
        # another line for that earlier, already-receipted anchor: stale
        stale = line(self.ext(self.start))
        self.assertRejected(self.judge(stale), 'stale', stale, self.start['request_id'])
        # another line for the NEWEST anchor once it is resolved: conflict
        first = line(self.ext(self.decision))
        resolved = {**self.resolved, 5: 'receipt'}
        resolving = {**self.resolving, 5: sha256_bytes(first)}
        second = line(self.ext(self.decision, created_at=rf.LATER))
        self.assertRejected(self.judge(second, resolved=resolved, resolving_sha=resolving),
                            'conflict', second, self.decision['request_id'])
        self.assertRejected(self.judge(first, resolved=resolved, resolving_sha=resolving),
                            'duplicate', first, self.decision['request_id'])
        # negative control: an UNRESOLVED earlier anchor's own late line is its receipt
        late = line(rf.mock_row(self.periodic))
        v = self.judge(late)
        self.assertEqual((v['kind'], v['anchor_seq']), ('receipt', 3))

    def test_a_request_that_disagrees_with_its_chained_anchor_is_a_conflict(self):
        raw = line(self.ext(self.decision))
        rid = self.decision['request_id']
        edits = {
            'anchor_head': {5: dict(self.decision_anchor, upto_h='0' * 64)},
            'anchor_request_id': {5: dict(self.decision_anchor, request_id='1' * 32)},
            'anchor_trigger': {5: dict(self.decision_anchor, trigger='trial_ended')},
            'no_chained_anchor': {},
        }
        for name, anchors in edits.items():
            with self.subTest(edit=name):
                self.assertRejected(self.judge(raw, anchors={
                    **{k: v for k, v in self.anchors.items() if k != 5}, **anchors}),
                    'conflict', raw, rid)
        other_trial = dict(self.decision, trial='T1')
        self.assertRejected(self.judge(raw, request_of={rid: other_trial}.get), 'conflict',
                            raw, rid)

    # -- the decision receipt's evidence (root 3e18d69) ----------------------------------
    def test_every_missing_or_inconsistent_evidence_item_is_refused_in_both_trees(self):
        self.assertEqual(len(rf.EVIDENCE_VARIANTS), 24)
        for name, (kw, reason) in rf.EVIDENCE_VARIANTS.items():
            raw = line(self.ext(self.decision, **kw))
            for mock_tree in (False, True):
                with self.subTest(variant=name, mock_tree=mock_tree):
                    self.assertRejected(self.judge(raw, mock_tree=mock_tree), reason, raw,
                                        self.decision['request_id'])

    def test_no_wall_clock_or_latency_window_is_imposed(self):
        """Root 3e18d69: no invented equality with a local clock and no latency window.  A
        comment edited a day later (``updated_at`` > ``created_at``) and server times far from
        any local time are accepted; only the response's own ordering is read."""
        for created, updated in (('2026-09-24T03:30:00Z', '2026-09-25T09:00:00.123456Z'),
                                 ('2001-01-01T00:00:00Z', '2001-01-01T00:00:00Z'),
                                 ('2099-12-31T23:59:59.999999999Z',
                                  '2099-12-31T23:59:59.999999999Z')):
            with self.subTest(created=created):
                raw = line(self.ext(self.decision, created_at=created,
                                           updated_at=updated))
                self.assertEqual(self.judge(raw)['kind'], 'receipt')

    def test_the_mock_receipt_counts_only_in_a_mock_tree(self):
        raw = line(rf.mock_row(self.decision))
        v = self.judge(raw, mock_tree=True)
        self.assertEqual((v['kind'], v['body']['anchor_file_sha256'],
                          v['body']['comment_body_sha256'], v['body']['node_id_sha256']),
                         ('receipt', None, None, None))
        self.assertRejected(self.judge(raw, mock_tree=False), 'malformed', raw,
                            self.decision['request_id'])
        # a local-only commit (``lab_anchor --local-only``) claims no external evidence
        local = line(dict(rf.mock_row(self.decision), commit=rf.COMMIT, branch=BRANCH))
        self.assertEqual(self.judge(local, mock_tree=True)['kind'], 'receipt')
        self.assertRejected(self.judge(local, mock_tree=False), 'malformed', local,
                            self.decision['request_id'])

    def test_the_pushed_commit_must_be_the_anchors_own_in_both_trees(self):
        """Owner ruling R-push (review of 988baf7, reviewer 1 finding 5; root 3e18d69 "verify
        the pushed commit/anchor-head evidence"): a row whose commit is not bound to its
        anchor in the anchor repository is refused ``conflict`` in both trees, and
        ``anchor_commit_problem`` names why.  The complete row with the pushed anchor commit
        is the negative control (``test_the_complete_external_receipt_...``).  Before the
        ruling every one of these rows was accepted as the decision's external receipt."""
        rid = self.decision['request_id']
        path = self.anchors_dir / 'anchor_5.json'
        want = sha256_canonical(lab_common.anchor_file_object(TRIAL, self.decision))

        def refused(name: str, commit: str, problem: str) -> None:
            # each case is judged against the repository as it stands when it is made
            with self.subTest(case=name):
                self.assertEqual(orch.anchor_commit_problem(self.repo.root, commit, BRANCH,
                                                            path, want), problem)
                raw = line(self.ext(self.decision, commit=commit))
                for mock_tree in (False, True):
                    self.assertRejected(self.judge(raw, mock_tree=mock_tree), 'conflict',
                                        raw, rid)
        refused('the_fixture_commit_that_exists_nowhere', rf.COMMIT, 'commit_absent')
        refused('zeros', '0' * 40, 'commit_absent')
        other_repo = rf.AnchorRepo(self.repo.root.parent / 'another_repo')
        other_repo.git('commit', '-q', '--allow-empty', '-m', 'another repository')
        foreign = other_repo.commit_anchor(other_repo.root / 'anchors', TRIAL, self.decision)
        refused('a_commit_of_another_repository', foreign, 'commit_absent')
        refused('committed_but_never_pushed',
                self.repo.commit([path], push=False, message='local only'),
                'not_on_pushed_branch')
        # a pushed commit whose anchors/anchor_5.json is another anchor's file object
        path.write_text(canonical_json(lab_common.anchor_file_object(TRIAL, self.periodic)),
                        encoding='utf-8')
        refused('another_anchors_file', self.repo.commit([path]), 'anchor_file_mismatch')
        # a pushed commit that no longer carries the anchor file at all
        self.repo.git('rm', '-q', '--', 'anchors/anchor_5.json')
        refused('no_anchor_file', self.repo.commit([]), 'anchor_file_absent')
        # the anchor's own pushed commit still verifies, and an anchor file outside the
        # repository is never one it holds
        self.assertIsNone(orch.anchor_commit_problem(self.repo.root, self.commit, BRANCH,
                                                     path, want))
        self.assertEqual(orch.anchor_commit_problem(self.repo.root, self.commit, BRANCH,
                                                    other_repo.root / 'anchors' /
                                                    'anchor_5.json', want),
                         'anchor_outside_repo')
        self.assertEqual(orch.anchor_commit_problem(self.repo.root.parent / 'no_repo',
                                                    self.commit, BRANCH,
                                                    self.repo.root.parent / 'no_repo' / 'x',
                                                    want), 'repo_unreadable')

    def test_non_decision_anchors_and_failures(self):
        rid = self.periodic['request_id']
        v = self.judge(line(rf.mock_row(self.periodic)))
        self.assertEqual((v['kind'], v['body']['request_id']), ('receipt', rid))
        failed = line({'request_id': rid, 'ok': False, 'error_class': 'push'})
        v = self.judge(failed)
        self.assertEqual((v['kind'], v['type'], v['body']),
                         ('failed', 'anchor_failed',
                          {'anchor_seq': 3, 'error_class': 'push', 'blocking': True}))
        bad_class = line({'request_id': rid, 'ok': False, 'error_class': 'kaboom'})
        self.assertRejected(self.judge(bad_class), 'malformed', bad_class, rid)
        # 8df2558 invented receipt_sha256 = sha256_canonical(row) for a line without one
        no_digest = line(dict(rf.mock_row(self.periodic), receipt_sha256=None))
        self.assertRejected(self.judge(no_digest), 'malformed', no_digest, rid)
        bad_time = line(dict(rf.mock_row(self.periodic), created_at='yesterday'))
        self.assertRejected(self.judge(bad_time), 'malformed', bad_time, rid)
        bool_id = line(dict(rf.mock_row(self.periodic), comment_id=True))
        self.assertRejected(self.judge(bool_id), 'malformed', bool_id, rid)


# --------------------------------------------------------------------------- #
# the chain rule the gate, the verifier and the builder read
# --------------------------------------------------------------------------- #
class DecisionReceiptChainTests(unittest.TestCase):
    """``lab_eventlog.decision_receipt`` / ``decision_receipt_problems`` on synthetic chains:
    a decision (seq 0), its blocking anchor (seq 1, anchor_seq 2) and one receipt (seq 2)."""

    def chain(self, receipt: dict | None, *, anchor: dict | None = None,
              chain_id: str | None = TRIAL) -> list[dict]:
        anchor = anchor if anchor is not None else rf.anchor_body(2, 'decision')
        events = [{'seq': 0, 'type': 'decision', 'body': {'kind': 'harm_keep_incumbent'}},
                  {'seq': 1, 'type': 'anchor', 'body': anchor}]
        if receipt is not None:
            events.append({'seq': 2, 'type': 'anchor_receipt', 'body': receipt})
        for ev in events:
            if chain_id is not None:
                ev['chain'] = chain_id
        return events

    def status(self, events, *, mock_tree: bool = False) -> dict:
        return lab_eventlog.decision_receipt(events, mock=mock_tree)

    def test_the_complete_receipt_is_receipted_in_both_trees(self):
        anchor = rf.anchor_body(2, 'decision')
        events = self.chain(rf.external_receipt_body(anchor, TRIAL))
        for mock_tree in (False, True):
            got = self.status(events, mock_tree=mock_tree)
            self.assertEqual((got['status'], got['receipt_seq'], got['server_time'],
                              got['unqualified']),
                             ('receipted', 2, rf.CREATED_AT, []))
        lab_eventlog.validate_event('anchor', anchor)
        lab_eventlog.validate_event('anchor_receipt', events[2]['body'])

    def test_each_missing_or_inconsistent_clause_leaves_the_decision_provisional(self):
        anchor = rf.anchor_body(2, 'decision')
        good = rf.external_receipt_body(anchor, TRIAL)
        edits = {
            'request_unbound': {'request_id': None},
            'request_mismatch': {'request_id': 'f' * 32},
            'not_pushed': {'pushed': False},
            'no_commit': {'commit_sha256': lab_eventlog.NO_COMMIT_SHA256},
            'no_anchor_file': {'anchor_file_sha256': None},
            'anchor_file_mismatch': {'anchor_file_sha256': 'e' * 64},
            'no_comment_body': {'comment_body_sha256': None},
            'comment_body_mismatch': {'comment_body_sha256': 'c' * 64},
            'no_comment_id': {'comment_id': None},
            'no_node_id': {'node_id_sha256': None},
            'no_created_at': {'created_at': None},
            'no_updated_at': {'updated_at': None},
            'updated_before_created': {'updated_at': rf.EARLIER},
        }
        for problem, edit in edits.items():
            body = dict(good, **edit)
            if edit.get('request_id', 0) is None:
                body.pop('request_id')
            for mock_tree in (False, True):
                with self.subTest(problem=problem, mock_tree=mock_tree):
                    got = self.status(self.chain(body), mock_tree=mock_tree)
                    self.assertEqual(got['status'], 'provisional')
                    self.assertEqual(got['unqualified'][0]['seq'], 2)
                    self.assertIn(problem, got['unqualified'][0]['problems'])
        # the chain id is the trial the expected bodies are recomputed for
        got = self.status(self.chain(good, chain_id=None))
        self.assertIn('no_trial', got['unqualified'][0]['problems'])
        got = self.status(self.chain(good, chain_id='T1'))
        self.assertIn('anchor_file_mismatch', got['unqualified'][0]['problems'])
        self.assertIn('comment_body_mismatch', got['unqualified'][0]['problems'])

    def test_an_anchor_without_its_request_id_can_never_be_receipted(self):
        anchor = rf.anchor_body(2, 'decision')
        receipt = rf.external_receipt_body(anchor, TRIAL)
        bare = {k: v for k, v in anchor.items() if k != 'request_id'}
        lab_eventlog.validate_event('anchor', bare)          # an older chain still validates
        got = self.status(self.chain(receipt, anchor=bare))
        self.assertEqual((got['status'], got['unqualified'][0]['problems']),
                         ('provisional', ['request_unbound']))

    def test_the_mock_receipt_counts_only_in_a_mock_tree_and_only_bound(self):
        anchor = rf.anchor_body(2, 'decision')
        body = rf.mock_receipt_body(anchor)
        self.assertEqual(self.status(self.chain(body), mock_tree=True)['status'], 'receipted')
        got = self.status(self.chain(body), mock_tree=False)
        self.assertEqual(got['status'], 'provisional')
        self.assertIn('not_pushed', got['unqualified'][0]['problems'])
        unbound = {k: v for k, v in body.items() if k != 'request_id'}
        got = self.status(self.chain(unbound), mock_tree=True)
        self.assertEqual((got['status'], got['unqualified'][0]['problems']),
                         ('provisional', ['request_unbound']))

    def test_mutation_the_8df2558_rule_accepts_a_receipt_bound_to_nothing(self):
        """The finding's receipt as 8df2558 chained it: the decision anchor's ``anchor_seq``
        and the line's ``created_at``, nothing else.  The old rule receipts the decision;
        the current rule does not (negative control of the attribution fix at chain level)."""
        body = {'anchor_seq': 2, 'pushed': True, 'comment_id': 1, 'created_at': rf.CREATED_AT,
                'updated_at': rf.CREATED_AT, 'receipt_sha256': 'a' * 64,
                'commit_sha256': sha256_text('x')}
        lab_eventlog.validate_event('anchor_receipt', body)
        events = self.chain(body)
        self.assertEqual(mutant.decision_receipt_8df2558(events, mock=False)['status'],
                         'receipted')
        self.assertEqual(self.status(events)['status'], 'provisional')


# --------------------------------------------------------------------------- #
# the anchor process: node_id, the raw response, and writer/checker agreement
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, content: bytes, status_code: int = 201) -> None:
        self.content = content
        self.status_code = status_code

    def json(self):
        return json.loads(self.content)


class AnchorWriterTests(unittest.TestCase):

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='eb1r_anchor_'))
        self.addCleanup(lambda: __import__('shutil').rmtree(self.root, ignore_errors=True))
        self.paths = lab_common.TrialPaths(
            trial=TRIAL, results=self.root / 'r', events=self.root / 'r' / 'events',
            anchors=self.root / 'r' / 'anchors', work=self.root / 'w',
            jobs=self.root / 'w' / 'jobs', spools=self.root / 'w' / 'spools',
            records=self.root / 'w' / 'records', requests=self.root / 'w' / 'requests',
            anchor_spool=self.root / 'w' / 'anchor_spool',
            anchors_private=self.root / 'w' / 'anchors_private',
            logs=self.root / 'w' / 'logs', run_lock=self.root / 'w' / 'run.lock',
            sandbox_lock=self.root / 'w' / 'sandbox.lock')
        self.anchor, self.request = request_pair(5, 'decision')
        os.environ['EB1R_STUB_TOKEN'] = 'stub-token-not-a-credential'
        self.addCleanup(os.environ.pop, 'EB1R_STUB_TOKEN', None)
        # the anchor repository the REAL lab_anchor.commit_and_push commits in and pushes
        # from (its origin a local bare repository: no network)
        self.repo = rf.AnchorRepo(self.paths.results)

    def post(self, content: bytes, status: int = 201) -> dict:
        with mock.patch('requests.post', lambda url, **kw: _Resp(content, status)):
            return lab_anchor.post_comment(lab_anchor.DEFAULT_ISSUE_API_BASE, 13, 'body',
                                           'EB1R_STUB_TOKEN')

    def test_the_anchor_file_bytes_are_those_of_8df2558(self):
        req = self.request
        old = {'trial': str(req['trial']), 'anchor_seq': int(req['anchor_seq']),
               'upto_seq': int(req['upto_seq']), 'upto_h': str(req['upto_h']),
               'segment_index': int(req['segment_index']),
               'segment_bytes': int(req['segment_bytes']),
               'segment_sha256': str(req['segment_sha256']), 'trigger': str(req['trigger']),
               'blocking': bool(req['blocking'])}
        path = lab_anchor.write_anchor_file(self.paths, req)
        self.assertEqual(path.read_bytes(), canonical_json(old).encode('utf-8'))
        old_body = canonical_json({'trial': req.get('trial'), 'upto_seq': req.get('upto_seq'),
                                   'upto_h': req.get('upto_h'),
                                   'segment_sha256': req.get('segment_sha256')})
        self.assertEqual(lab_common.anchor_comment_body(TRIAL, req), old_body)

    def test_post_comment_records_node_id_and_the_raw_response(self):
        content = canonical_json({'id': 77, 'node_id': 'IC_x', 'created_at': rf.CREATED_AT,
                                  'updated_at': rf.LATER, 'body': 'body'}).encode()
        got = self.post(content)
        self.assertEqual((got['ok'], got['comment_id'], got['node_id'], got['created_at'],
                          got['updated_at'], got['receipt_sha256']),
                         (True, 77, 'IC_x', rf.CREATED_AT, rf.LATER, sha256_bytes(content)))
        self.assertEqual(base64.b64decode(got['response_b64']), content)
        # negative controls: nothing is invented for a field the response lacks
        bare = canonical_json({'id': 77, 'created_at': rf.CREATED_AT}).encode()
        got = self.post(bare)
        self.assertEqual((got['ok'], got['node_id'], got['updated_at']), (True, None, None))
        self.assertFalse(self.post(b'[1]')['ok'])
        self.assertFalse(self.post(content, status=422)['ok'])
        self.assertIsNone(self.post(content, status=422)['node_id'])

    def handle(self, echo) -> dict:
        """``lab_anchor._handle`` in REAL mode for the decision request: the REAL
        ``commit_and_push`` in a local anchor repository (explicit path, commit, ``git push
        origin <branch>`` to a local bare origin), ``requests.post`` stubbed with a response
        built by ``echo(posted_body)``."""
        cfg = {'anchor': {'comment_triggers': ['decision'], 'issue': 13, 'branch': BRANCH},
               '_runtime': {'anchor_mode': 'real', 'token_env': 'EB1R_STUB_TOKEN',
                            'repo': str(self.repo.root)}}

        def fake_post(url, json=None, **kw):
            return _Resp(canonical_json(echo(json['body'])).encode('utf-8'))
        path = self.paths.anchors / 'anchor_5.json'
        if path.exists():
            # this test answers ONE request three times: the file an earlier answer committed
            # is removed first, so that the real commit_and_push has something to commit
            self.repo.git('rm', '-q', '--', 'anchors/anchor_5.json')
            self.repo.commit([], message='remove the earlier answer\'s anchor file')
        with mock.patch('requests.post', fake_post):
            return lab_anchor._handle(self.paths, cfg, self.request, mode='real', wait_s=0.0)

    def judge(self, receipt: dict) -> dict:
        return orch.judge_receipt_line(
            line(receipt), trial=TRIAL, request_of={self.request['request_id']:
                                                    self.request}.get,
            anchors={5: self.anchor}, resolved={}, resolving_sha={}, newest_anchor_seq=5,
            mock=False, anchor_branch=BRANCH,
            commit_check=self.repo.checker(self.paths.anchors, TRIAL))

    def test_the_real_mode_row_is_the_decision_receipt_and_another_body_is_not(self):
        def echo(body):
            return {'id': rf.COMMENT_ID, 'node_id': rf.NODE_ID, 'body': body,
                    'created_at': rf.CREATED_AT, 'updated_at': rf.CREATED_AT}
        receipt = self.handle(echo)
        self.assertEqual((receipt['ok'], receipt['node_id'], receipt['pushed']),
                         (True, rf.NODE_ID, True))
        self.assertEqual(receipt['commit'], self.repo.git('rev-parse', 'HEAD').strip(),
                         'the commit lab_anchor made and pushed')
        self.assertEqual(receipt['anchor_file_sha256'], sha256_canonical(
            lab_common.anchor_file_object(TRIAL, self.request)))
        v = self.judge(receipt)
        self.assertEqual((v['kind'], v['anchor_seq']), ('receipt', 5))
        # the private receipt carries the same row (work/ only)
        private = (self.paths.anchors_private / 'receipts.jsonl').read_text().splitlines()
        self.assertEqual(json.loads(private[-1]), receipt)
        # negative control: the server's response is to ANOTHER body
        receipt = self.handle(lambda body: dict(echo(body), body=body + ' '))
        v = self.judge(receipt)
        self.assertEqual((v['kind'], v['body']['reason']), ('rejected', 'conflict'))
        # and one without node_id is not a decision receipt
        receipt = self.handle(lambda body: {k: x for k, x in echo(body).items()
                                            if k != 'node_id'})
        v = self.judge(receipt)
        self.assertEqual((v['kind'], v['body']['reason']), ('rejected', 'malformed'))


# --------------------------------------------------------------------------- #
# in process: a disagreement between the two rules cannot loop
# --------------------------------------------------------------------------- #
class RuleDisagreementGuardTests(unittest.TestCase):
    """``World.ingest_receipts``: were an accepted receipt of the pending decision request not
    receipted by the chain rule, ``ANCHOR_BLOCK`` would re-request the decision anchor for ever
    (the 8df2558 ingest under the current chain rule did exactly that in
    ``tests_eb1_cap_estimand.ReceiptIngestTests`` before its mutation was paired with the old
    gate: 10,000 segments).  The guard treats the anchor as failed: a pause.  Production
    ``run_trial`` in process on ``dryrun_live_ab``'s D3 tree (``tests_eb1_cap_estimand``)."""

    def run_d3(self, disagree: bool):
        tree = cap.d3_tree()
        self.addCleanup(tree.close)
        fake = sup.FakeServers()
        real = lab_eventlog.decision_receipt

        def disagreeing(events, *, mock, before_seq=None):
            out = real(events, mock=mock, before_seq=before_seq)
            if out['status'] == 'receipted':
                out = dict(out, status='provisional', receipt_seq=None, server_time=None)
            return out
        patch = (mock.patch.object(lab_eventlog, 'decision_receipt', disagreeing) if disagree
                 else mock.patch.object(orch, 'EB1R_TEST_NOOP', None, create=True))
        with patch:
            status = cap.run_gated(tree, fake, blocking_wait_s=0.5)
        return status, tree.events()

    def test_a_disagreement_pauses_after_one_decision_anchor(self):
        status, events = self.run_d3(True)
        self.assertEqual(status, 'paused')
        decision_anchors = [e for e in of(events, 'anchor')
                            if e['body']['trigger'] == 'decision']
        self.assertEqual(len(decision_anchors), 1, 'not re-requested')
        self.assertEqual(of(events, 'trial_paused')[-1]['body']['reason_code'],
                         'anchor_unavailable')
        self.assertEqual(of(events, 'traffic_switch'), [])

    def test_control_without_the_disagreement_the_same_tree_switches(self):
        status, events = self.run_d3(False)
        self.assertEqual(status, 'ended')
        self.assertEqual(len(of(events, 'traffic_switch')), 1)
        self.assertEqual(lab_eventlog.decision_receipt(events, mock=True)['status'],
                         'receipted')


# --------------------------------------------------------------------------- #
# the REAL production entry path
# --------------------------------------------------------------------------- #
HOLD_S = 3.0            # the gate is watched this long after the last wrong line is chained
SETTLE_S = 60.0         # at most this long for the wrong lines to be chained
READ_EVERY_S = 0.25


def requests_of(t) -> list[dict]:
    path = t.work / t.trial / 'anchor_spool' / 'requests.jsonl'
    out = []
    if path.exists():
        for raw in path.read_bytes().split(b'\n'):
            if raw.strip():
                try:
                    out.append(json.loads(raw))
                except ValueError:
                    pass
    return out


def spool_of(t) -> Path:
    return t.work / t.trial / 'anchor_spool' / 'receipts.jsonl'


def spool_lines(t) -> list[bytes]:
    path = spool_of(t)
    if not path.exists():
        return []
    raw = path.read_bytes()
    return [chunk for chunk in raw.split(b'\n')[:-1] if chunk.strip()]


def resolving_line(t, request_id: str) -> bytes:
    """The line the withholding (mock) anchor process wrote for ``request_id``."""
    for raw in spool_lines(t):
        try:
            if json.loads(raw).get('request_id') == request_id:
                return raw
        except ValueError:
            continue
    raise AssertionError('no receipt line for %s' % request_id)


def start_withholding_anchor(t, withhold=('decision',)):
    cfg = json.loads(t.run_config.read_text('utf-8'))
    cfg_path = t.work / ('anchor_cfg_%s.json' % t.trial)
    cfg_path.write_text(canonical_json(cfg), encoding='utf-8')
    return subprocess.Popen(
        [sys.executable, str(HERE / 'eb1_withhold_anchor.py'), '--withhold',
         ','.join(withhold), '--trial', t.trial, '--config', str(cfg_path), '--mock-receipt',
         '--results', str(t.results), '--work', str(t.work), '--max-idle-s', '900'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(LIVE))


def run_invocation(t, *, on_poll=None, extra_argv: tuple = (), mutation: str | None = None,
                   timeout_s: float = 900.0) -> bool:
    """``lab_orchestrator.py main()`` (or ``eb1_receipt_mutant_entry.py --mutation NAME``) as a
    subprocess on tree ``t`` with the withholding anchor process; ``on_poll(t)`` every 50 ms.
    Returns whether the REAL host gate refused the run."""
    before = cap.host_refusals(t)
    anchor_proc = start_withholding_anchor(t)
    script = [str(LIVE / 'lab_orchestrator.py')] if mutation is None else [
        str(HERE / 'eb1_receipt_mutant_entry.py'), '--mutation', mutation]
    log_path = t.work / ('invocation_%d.log' % time.monotonic_ns())
    try:
        with open(log_path, 'wb') as log:
            proc = subprocess.Popen([sys.executable] + script + t.argv() + list(extra_argv),
                                    cwd=str(LIVE), env=entry.child_env(), stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        t.proc = proc
        deadline = time.monotonic() + timeout_s
        while proc.poll() is None and time.monotonic() < deadline:
            if on_poll is not None:
                on_poll(t)
            time.sleep(0.05)
        if proc.poll() is None:
            entry.with_group_kill(proc)
        proc.wait(timeout=30)
    finally:
        dry._stop_anchor(anchor_proc)
    t.returncode = proc.returncode
    t.stdout = log_path.read_text('utf-8', 'replace')
    return cap.host_refusals(t) > before


class Injector:
    """``on_poll``: when the ``nth`` decision request (0-based, over ``requests.jsonl``) is
    durable, append ``bad(t, decision_requests)`` to the receipt spool; wait until the chain
    holds one ``anchor_receipt_rejected`` per wrong line (at most :data:`SETTLE_S`), watch the
    gate for :data:`HOLD_S` more, keep the chain as it then stands (``before_good``), append
    ``good(...)``; and, once a ``traffic_switch`` is chained, ``after_switch(...)``."""

    def __init__(self, *, nth: int, bad, good=None, after_switch=None,
                 settle_s: float = SETTLE_S) -> None:
        self.nth, self.bad, self.good, self.after_switch = nth, bad, good, after_switch
        self.settle_s = float(settle_s)
        self.state = 'wait'
        self.bad_lines: list[bytes] = []
        self.good_lines: list[bytes] = []
        self.late_lines: list[bytes] = []
        self.before_good: list[dict] | None = None
        self.decisions: list[dict] = []
        self._next = 0.0

    def __call__(self, t) -> None:
        now = time.monotonic()
        if self.state == 'wait':
            decisions = [r for r in requests_of(t) if r.get('trigger') == 'decision']
            if len(decisions) > self.nth:
                self.decisions = decisions
                for item in self.bad(t, decisions):
                    self.bad_lines.append(rf.append_line(spool_of(t), item))
                self.t_bad = now
                self.state = 'settle'
            return
        if self.state == 'done' or now < self._next:
            return
        self._next = now + READ_EVERY_S
        try:
            events = t.chain()
        except (lab_common.ChainError, lab_common.SchemaError, ValueError, OSError):
            return
        if self.state == 'settle':
            digests = {sha256_bytes(b) for b in self.bad_lines}
            chained = [e for e in of(events, 'anchor_receipt_rejected')
                       if e['body']['raw_sha256'] in digests]
            if len(chained) >= len(self.bad_lines) or now - self.t_bad > self.settle_s:
                self.t_hold = now
                self.state = 'hold'
            return
        if self.state == 'hold':
            if now - self.t_hold >= HOLD_S:
                self.before_good = events
                for item in (self.good(t, self.decisions) if self.good else []):
                    self.good_lines.append(rf.append_line(spool_of(t), item))
                self.state = 'good' if self.after_switch else 'done'
            return
        if self.state == 'good' and of(events, 'traffic_switch'):
            decisions = [r for r in requests_of(t) if r.get('trigger') == 'decision']
            for item in self.after_switch(t, decisions):
                self.late_lines.append(rf.append_line(spool_of(t), item))
            self.state = 'done'


def gate_problems(events: list[dict], inj: Injector, reasons: list[str],
                  request: dict) -> list[str]:
    """E1's assertions as a list of violations (``[]``: all hold).  The mutation controls
    run the same function on the mutants' chains: each must violate it."""
    out: list[str] = []
    # the chain as it stood when the good line was written -- or, if the run ended before,
    # the whole chain (none of it can then be the good line's doing)
    before = inj.before_good if inj.before_good is not None else events
    if inj.before_good is None:
        out.append('the good line was never written')
    for etype in ('traffic_switch', 'arm_assigned_by_decision'):
        if of(before, etype):
            out.append('%s_before_the_decision_receipt' % etype)
    if lab_eventlog.decision_receipt(before, mock=True)['status'] == 'receipted':
        out.append('receipted_before_the_decision_receipt')
    digests = [sha256_bytes(b) for b in inj.bad_lines]
    rejected = {e['body']['raw_sha256']: e for e in of(events, 'anchor_receipt_rejected')}
    got = [rejected[d]['body']['reason'] if d in rejected else None for d in digests]
    if got != list(reasons):
        out.append('rejections %r != %r' % (got, list(reasons)))
    anchor = next((e for e in of(events, 'anchor')
                   if e['body'].get('request_id') == request['request_id']), None)
    if anchor is None:
        out.append('no chained anchor carries the decision request id')
        return out
    receipts = [e for e in of(events, 'anchor_receipt')
                if e['body']['anchor_seq'] == anchor['body']['anchor_seq']]
    if len(receipts) != 1 or receipts[0]['body'].get('request_id') != request['request_id']:
        out.append('the decision anchor has %d receipts, bound to %r'
                   % (len(receipts), [r['body'].get('request_id') for r in receipts]))
    unbound = [e for e in of(events, 'anchor_receipt') if not e['body'].get('request_id')]
    if unbound:
        out.append('%d anchor_receipt(s) bound to no request' % len(unbound))
    state = lab_eventlog.decision_receipt(events, mock=True)
    switches = of(events, 'traffic_switch')
    if state['status'] != 'receipted' or not switches:
        out.append('never unlocked: %s, %d switch(es)' % (state['status'], len(switches)))
    elif not (receipts and state['receipt_seq'] == receipts[0]['seq']
              and max([r['seq'] for r in rejected.values()] or [-1]) < state['receipt_seq']
              < switches[0]['seq']):
        out.append('the switch does not follow the decision request\'s own receipt')
    return out


class ProdReceiptGate(cap.ProdCase):
    """E1, E2, M1, M2 through ``main()`` (see the module docstring)."""

    def harm_tree(self, name: str, **build_kw):
        cap.quiet_host()
        t = entry.EntryTree(name, n_pairs=cap.HARM_PAIRS, trial=cap.HARM_TRIAL,
                            freeze_kw={'n_min': cap.HARM_N_MIN})
        self.addCleanup(t.cleanup)
        # the anchor repository (``_runtime.repo``, as lab_anchor reads it) is the tree's
        # results root: a control's good receipt names a commit that really carries the
        # decision anchor's file and was pushed (owner ruling R-push)
        runtime = dict(build_kw.pop('runtime', {}) or {}, repo=str(t.results))
        t.build(runtime=runtime, **build_kw)
        t.set_scenarios([cap.harm_scenario(t, None)])
        self.branch = str(json.loads((t.freeze / 'config.json').read_text('utf-8'))
                          ['anchor']['branch'])
        t.anchor_repo = rf.AnchorRepo(t.results, branch=self.branch)
        return t

    def fresh(self, name: str, inj_factory, *, mutation: str | None = None,
              blocking_s: float = 120.0):
        """A fresh tree and ONE invocation (again, at most twice more, only when the REAL host
        gate refused it)."""
        refusals = []
        for _ in range(3):
            t = self.harm_tree(name, runtime={'blocking_wait_s': blocking_s})
            inj = inj_factory()
            if not run_invocation(t, on_poll=inj, mutation=mutation):
                return t, inj
            refusals.append(entry.host_refusal(t.program_chain()))
            cap.quiet_host()
        self.fail('the host gate refused three runs: %s' % refusals)

    def resume(self, t, inj) -> None:
        refusals = []
        for _ in range(3):
            if not run_invocation(t, on_poll=inj, extra_argv=('--resume',)):
                return
            refusals.append(entry.host_refusal(t.program_chain()))
            cap.quiet_host()
        self.fail('the host gate refused three resumes: %s' % refusals)

    # -- the wrong lines ---------------------------------------------------------------------
    def e1_bad(self, t, decisions) -> list:
        """(line, reason) pairs: unknown, stale, duplicate, malformed, every evidence variant."""
        req = decisions[0]
        start = next(r for r in requests_of(t) if r['trigger'] == 'trial_started')
        pairs = [
            (rf.external_row(dict(req, request_id=uuid.uuid4().hex), branch=self.branch),
             'unknown_request'),
            (rf.external_row(start, branch=self.branch), 'stale'),
            (resolving_line(t, start['request_id']), 'duplicate'),
            (b'{"request_id":"%s","ok":tru' % req['request_id'].encode(), 'malformed'),
            # complete and consistent, but its commit is bound to nothing (R-push)
            (rf.external_row(req, branch=self.branch), 'conflict'),
        ]
        for kw, reason in rf.EVIDENCE_VARIANTS.values():
            kw = dict(kw)
            kw.setdefault('branch', self.branch)
            pairs.append((rf.external_row(req, **kw), reason))
        return pairs

    def good_for(self, index: int):
        """The decision request's receipt: its anchor file (written by the anchor process)
        committed and pushed in the tree's anchor repository, and the row naming that
        commit."""
        def good(t, decisions):
            req = decisions[index]
            commit = t.anchor_repo.commit_anchor(t.results / t.trial / 'anchors', t.trial,
                                                 req)
            return [rf.external_row(req, branch=self.branch, commit=commit)]
        return good

    def line_event_pairs(self, t, events) -> list[tuple[bytes, dict]]:
        """The receipt spool's lines paired with the chain's receipt-line events (one per
        line, in order: ``lab_orchestrator.RECEIPT_LINE_EVENTS``); a rejected line's event
        carries that line's digest and length, an accepted one its request id."""
        lines = spool_lines(t)
        evs = [e for e in events if e['type'] in orch.RECEIPT_LINE_EVENTS]
        self.assertEqual(len(evs), len(lines), 'one chain event per receipt line')
        for raw, ev in zip(lines, evs):
            if ev['type'] == 'anchor_receipt_rejected':
                self.assertEqual((ev['body']['raw_sha256'], ev['body']['raw_bytes']),
                                 (sha256_bytes(raw), len(raw)))
            elif ev['type'] == 'anchor_receipt':
                self.assertEqual(ev['body']['request_id'], json.loads(raw)['request_id'])
        return list(zip(lines, evs))

    def assertEndedAndVerified(self, t, events) -> None:
        self.assertEqual(t.returncode, 0, t.stdout[-3000:])
        self.assertEqual(events[-1]['type'], 'anchor_receipt', 'the end anchor answered')
        self.assertEqual(len(of(events, 'trial_ended')), 1)
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        builder.build([t.trial], t.bundle_sha, results_root=t.results, work_root=t.work,
                      out_dir=t.root / 'derived')
        obj = json.loads((t.root / 'derived' / t.trial / 'decision.json').read_text('utf-8'))
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision']['n']),
                         ('harm_keep_incumbent', True, cap.expected_harm_tau(t)))
        self.assertNoOrphans(t)

    # -- E1 ------------------------------------------------------------------------------------
    def test_e1_wrong_lines_hold_the_gate_and_the_matched_receipt_unlocks_it(self):
        reasons: list[str] = []

        def make():
            def bad(t, decisions):
                pairs = self.e1_bad(t, decisions)
                reasons[:] = [r for _, r in pairs]
                return [line for line, _ in pairs]
            return Injector(nth=0, bad=bad, good=self.good_for(0))
        t, inj = self.fresh('RA1', make)
        events = t.chain()
        self.assertEqual(len(inj.bad_lines), 5 + len(rf.EVIDENCE_VARIANTS))
        self.assertEqual(set(reasons), set(REASONS), 'every reason is exercised')
        self.assertEqual(gate_problems(events, inj, reasons, inj.decisions[0]), [])
        # while the wrong lines were chained the decision stayed provisional and nothing
        # post-decision was dispatched: the anchor request was the pending one throughout
        before = inj.before_good
        self.assertEqual(lab_eventlog.decision_receipt(before, mock=True)['status'],
                         'provisional')
        self.assertEqual(of(before, 'anchor_receipt_rejected')[-1]['body']['raw_sha256'],
                         sha256_bytes(inj.bad_lines[-1]))
        (decision,) = of(events, 'decision')
        self.assertEqual((decision['body']['kind'], decision['body']['n']),
                         ('harm_keep_incumbent', cap.expected_harm_tau(t)))
        # every chained anchor carries its durable request's id; the raw lines stay in the
        # spool, unaltered, beside the rows the anchor process wrote
        ids = [r['request_id'] for r in requests_of(t)]
        self.assertEqual([e['body']['request_id'] for e in of(events, 'anchor')], ids)
        lines = spool_lines(t)
        for raw in inj.bad_lines + inj.good_lines:
            self.assertIn(raw, lines)
        self.line_event_pairs(t, events)
        self.assertEndedAndVerified(t, events)

    # -- E2 ------------------------------------------------------------------------------------
    def test_e2_the_same_across_a_pause_and_resume_with_the_anchor_carried_over(self):
        def first_bad(t, decisions):
            req = decisions[0]
            start = next(r for r in requests_of(t) if r['trigger'] == 'trial_started')
            return [rf.external_row(dict(req, request_id=uuid.uuid4().hex),
                                    branch=self.branch),
                    rf.external_row(start, branch=self.branch)]
        t, inj1 = self.fresh('RA2', lambda: Injector(nth=0, bad=first_bad),
                             blocking_s=15.0)
        self.assertEqual(t.returncode, 2, t.stdout[-3000:])
        paused = t.chain()
        self.assertEqual(of(paused, 'trial_paused')[-1]['body']['reason_code'],
                         'anchor_unavailable')
        self.assertEqual([e['body']['reason'] for e in of(paused, 'anchor_receipt_rejected')],
                         ['unknown_request', 'stale'])
        for etype in ('traffic_switch', 'arm_assigned_by_decision', 'trial_ended'):
            self.assertEqual(of(paused, etype), [], etype)
        self.assertEqual(lab_eventlog.decision_receipt(paused, mock=True)['status'],
                         'provisional')
        carried = inj1.decisions[0]

        # -- --resume: the decision request of the paused invocation is still unanswered ----
        second_reasons = ['unknown_request', 'duplicate', 'malformed', 'conflict',
                          'malformed']

        def second_bad(t, decisions):
            start = next(r for r in requests_of(t) if r['trigger'] == 'trial_started')
            return [rf.external_row(dict(carried, request_id=uuid.uuid4().hex),
                                    branch=self.branch),
                    resolving_line(t, start['request_id']),
                    rf.external_row(carried, branch=self.branch, drop=('node_id',)),
                    rf.external_row(carried, branch=self.branch,
                                    response_override={'body': '{"trial":"T1"}'}),
                    rf.external_row(decisions[1], branch=self.branch,
                                    drop=('comment_response_b64',))]
        inj2 = Injector(nth=1, bad=second_bad, good=self.good_for(0),
                        after_switch=self.good_for(1))
        self.resume(t, inj2)
        events = t.chain()
        self.assertEqual(events[:len(paused)], paused, 'the paused chain is a prefix')
        self.assertEqual(gate_problems(events, inj2, second_reasons, carried), [])
        receipt = lab_eventlog.decision_receipt(events, mock=True)
        first_anchor = next(e for e in of(events, 'anchor')
                            if e['body']['request_id'] == carried['request_id'])
        self.assertEqual(events[receipt['receipt_seq']]['body']['anchor_seq'],
                         first_anchor['body']['anchor_seq'], 'the carried-over anchor')
        self.assertLess(first_anchor['seq'], len(paused))
        self.assertGreater(receipt['receipt_seq'], len(paused))
        # nothing re-chained by the resumed invocation's re-read of the spool: one chain
        # event per spool line, in order, across both invocations; and the restarted anchor
        # process's re-answers of the requests it had already answered (lab_anchor.serve
        # re-reads requests.jsonl from its start: byte-identical MOCK lines) are each a
        # ``duplicate``, never a second receipt
        pairs = self.line_event_pairs(t, events)
        seen: dict[bytes, dict] = {}
        repeats = 0
        first_rejected: set[str] = set()
        for raw, ev in pairs:
            if raw in seen:
                # a byte-identical repeat of a line that resolved an anchor: the injected
                # duplicate, and (observed) the restarted anchor process's re-answers
                repeats += 1
                self.assertEqual((ev['type'], ev['body']['reason']),
                                 ('anchor_receipt_rejected', 'duplicate'))
                self.assertIn(seen[raw]['type'], ('anchor_receipt', 'anchor_failed'))
                continue
            seen[raw] = ev
            if ev['type'] == 'anchor_receipt_rejected':
                first_rejected.add(sha256_bytes(raw))
        resolving = {sha256_bytes(raw) for raw, ev in seen.items()
                     if ev['type'] in ('anchor_receipt', 'anchor_failed')}
        injected = {sha256_bytes(b) for b in inj1.bad_lines + inj2.bad_lines}
        self.assertEqual(first_rejected, injected - resolving,
                         'every other rejection is one of the injected wrong lines')
        self.assertEqual(len(injected - resolving), 2 + len(second_reasons) - 1)
        rejected = of(events, 'anchor_receipt_rejected')
        self.assertEqual(len(rejected), len(first_rejected) + repeats)
        seqs = [e['body']['anchor_seq'] for e in of(events, 'anchor_receipt')]
        self.assertEqual(len(seqs), len(set(seqs)), 'each anchor receipted once')
        # the resumed invocation's own decision anchor, answered after the switch
        second_anchor = next(e for e in of(events, 'anchor')
                             if e['body']['request_id'] == inj2.decisions[1]['request_id'])
        late = next(e for e in of(events, 'anchor_receipt')
                    if e['body']['anchor_seq'] == second_anchor['body']['anchor_seq'])
        self.assertGreater(late['seq'], of(events, 'traffic_switch')[0]['seq'])
        self.assertEndedAndVerified(t, events)

    # -- M1 / M2 -------------------------------------------------------------------------------
    def unknown_only(self, t, decisions):
        return [rf.external_row(dict(decisions[0], request_id=uuid.uuid4().hex),
                                branch=self.branch)]

    def test_mutation_m1_newest_anchor_attribution_is_caught(self):
        t, inj = self.fresh('RM1', lambda: Injector(nth=0, bad=self.unknown_only,
                                                    good=self.good_for(0), settle_s=1.0),
                            mutation='newest_anchor_attribution', blocking_s=20.0)
        events = t.chain()
        problems = gate_problems(events, inj, ['unknown_request'], inj.decisions[0])
        self.assertIn("rejections [None] != ['unknown_request']", problems)
        self.assertTrue(any(p.endswith('anchor_receipt(s) bound to no request')
                            for p in problems), problems)
        self.assertTrue(any(p.startswith('never unlocked') for p in problems), problems)
        decision_anchor = next(e for e in of(events, 'anchor')
                               if e['body']['request_id'] == inj.decisions[0]['request_id'])
        misattributed = [e for e in of(events, 'anchor_receipt')
                         if e['body']['anchor_seq'] == decision_anchor['body']['anchor_seq']]
        self.assertEqual(len(misattributed), 1)
        self.assertEqual(misattributed[0]['body']['created_at'], rf.CREATED_AT)
        self.assertIsNotNone(inj.before_good, 'the good line was written')
        self.assertLess(misattributed[0]['seq'], len(inj.before_good),
                        'chained from the UNKNOWN line, before the good one was written')
        self.assertNotIn('the good line was never written', problems)
        self.assertEqual(t.returncode, 2, 'the good receipt was swallowed: the trial pauses')

    def test_mutation_m2_with_the_8df2558_gate_the_traffic_switches_on_the_unknown_line(self):
        t, inj = self.fresh('RM2', lambda: Injector(nth=0, bad=self.unknown_only,
                                                    good=self.good_for(0), settle_s=1.0),
                            mutation='newest_anchor_attribution_old_gate', blocking_s=20.0)
        events = t.chain()
        problems = gate_problems(events, inj, ['unknown_request'], inj.decisions[0])
        self.assertIn('traffic_switch_before_the_decision_receipt', problems)
        # the switch came before the good line was written (or the run ended without it)
        before = inj.before_good if inj.before_good is not None else events
        self.assertEqual(len(of(before, 'traffic_switch')), 1)
        self.assertEqual(mutant.decision_receipt_8df2558(before, mock=True)['status'],
                         'receipted', 'the old rule read the unknown line as the receipt')
        self.assertEqual(lab_eventlog.decision_receipt(before, mock=True)['status'],
                         'provisional', 'the current rule does not')
        # the verifier (current rule) FAILs the mutant's chain
        report = t.verify()
        self.assertEqual(report['verdict'], 'FAIL')
        self.assertIn('switch.phase', {f['check'] for f in report['findings']
                                       if f['severity'] == 'FAIL'})


class ProdCaseBExternalReceipt(ProdReceiptGate):
    """Case (b) of root's 21:14 ruling through ``main()`` with an EVIDENCE-BEARING decision
    receipt (review of 988baf7, reviewer 1: case (b) on the production path was shown only
    with the mock anchor's receipt, which claims no evidence and counts only in a dry-run
    tree).  Three supervised restarts in pairs 1-3 (``tests_eb1_cap_estimand``'s
    THREE_EARLY_RESTARTS), the frozen band crosses to ``harm_keep_incumbent`` at tau = 39,
    the withholding anchor process answers no ``decision`` request, and the control answers
    it with ``receipt_fixture.external_row`` naming a commit that really carries the decision
    anchor's file and was pushed in the tree's anchor repository -- judged by the full rule
    (every evidence item and the commit binding of owner ruling R-push).  Once the traffic
    has switched the control SIGKILLs the server: the fourth down, ``trial_aborted(
    server_restart_cap)``.  The decision stands at its tau, receipted by a receipt that the
    NON-mock rule accepts too; the follow-up is truncated and counted; the verifier PASSes.
    Negative controls: E1 above (the same gate holds on every wrong line, including a
    complete row whose commit is bound to nothing), and ``tests_eb1_cap_estimand.ProdCaseC``
    (the receipt not yet chained when the cap binds: provisional, not reportable)."""

    def test_case_b_the_externally_receipted_decision_stands(self):
        state: dict = {}
        refusals = []
        for _ in range(3):
            t = self.harm_tree('RB', runtime={'blocking_wait_s': 120.0})
            t.set_scenarios([cap.harm_scenario(t, n) for n in cap.THREE_EARLY_RESTARTS])
            inj = Injector(nth=0, bad=lambda t, decisions: [], good=self.good_for(0))
            state.clear()

            def on_poll(t, inj=inj):
                inj(t)
                if 'killed' in state:
                    return
                try:
                    events = t.chain()
                except (lab_common.ChainError, lab_common.SchemaError, ValueError, OSError):
                    return
                if of(events, 'traffic_switch'):
                    pid = int(t.launches()[-1]['pid'])
                    os.kill(pid, __import__('signal').SIGKILL)
                    state['killed'] = pid
            if not run_invocation(t, on_poll=on_poll):
                break
            refusals.append(entry.host_refusal(t.program_chain()))
            cap.quiet_host()
        else:
            self.fail('the host gate refused three runs: %s' % refusals)
        self.assertEqual(t.returncode, 1, t.stdout[-3000:])
        self.assertIn('killed', state)
        events = t.chain()
        tau = cap.expected_harm_tau(t)
        (decision,) = of(events, 'decision')
        self.assertEqual((decision['body']['kind'], decision['body']['n']),
                         ('harm_keep_incumbent', tau))
        # the decision receipt is the injected, evidence-bearing one -- accepted by the rule
        # outside a dry-run tree as well (mock=False), not by the mock exemption
        full = lab_eventlog.decision_receipt(events, mock=False)
        self.assertEqual(full['status'], 'receipted')
        receipt = events[full['receipt_seq']]['body']
        self.assertEqual((receipt['created_at'], receipt['node_id_sha256']),
                         (rf.CREATED_AT, sha256_text(rf.NODE_ID)))
        self.assertEqual(receipt['request_id'], inj.decisions[0]['request_id'])
        self.assertEqual(len(inj.good_lines), 1)
        self.assertEqual(receipt['receipt_sha256'],
                         json.loads(inj.good_lines[0])['receipt_sha256'])
        (switch,) = of(events, 'traffic_switch')
        downs = of(events, 'server_down')
        self.assertEqual(len(downs), 4)
        self.assertLess(full['receipt_seq'], switch['seq'])
        self.assertLess(switch['seq'], downs[3]['seq'])
        (aborted,) = of(events, 'trial_aborted')
        self.assertEqual(aborted['body']['reason'], 'server_restart_cap')
        comp = aborted['body']['completion']
        self.assertEqual((comp['restart_cap_case'], comp['decision_status'],
                          comp['decision_receipt_seq'], comp['decision_receipt_server_time']),
                         ('after_receipted_decision', 'receipted', full['receipt_seq'],
                          rf.CREATED_AT))
        self.assertGreater(comp['follow_up_not_run'], 0, 'the follow-up was truncated')
        builder.build([t.trial], t.bundle_sha, results_root=t.results, work_root=t.work,
                      out_dir=t.root / 'derived')
        obj = json.loads((t.root / 'derived' / t.trial / 'decision.json').read_text('utf-8'))
        self.assertEqual((obj['primary_result'], obj['reportable'], obj['decision']['n'],
                          obj['restart_cap']['case']),
                         ('harm_keep_incumbent', True, tau, 'after_receipted_decision'))
        report = t.verify()
        self.assertEqual((report['_exit'], report['verdict']), (0, 'PASS'), report['_stdout'])
        self.assertNoOrphans(t)


if __name__ == '__main__':
    unittest.main()
