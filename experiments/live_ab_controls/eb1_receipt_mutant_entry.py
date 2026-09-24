"""Receipt-attribution mutation entry: ``lab_orchestrator.main`` with the 8df2558 receipt path.

Root's blocking finding on WIP 8df2558 (``reviews/eb1_receipt_attribution_review_20260924_0254.md``,
origin/main f855e45).  ``--mutation NAME`` comes first; the rest of the argv is
``lab_orchestrator.main``'s.  Used only by ``tests_eb1_receipt_attribution``.

* ``newest_anchor_attribution`` -- ``World.ingest_receipts`` of 8df2558, VERBATIM
  (:func:`ingest_8df2558`): a line whose ``request_id`` no request carries is attributed to
  ``self.anchor_seq``, the NEWEST anchor, and an ``ok`` line becomes an ``anchor_receipt``
  carrying the line's ``created_at``.  The current ``lab_eventlog.decision_receipt`` stays: the
  misattributed receipt carries no ``request_id`` and cannot open the gate, so what catches
  this mutation is the control's attribution assertions (no ``anchor_receipt_rejected``; an
  ``anchor_receipt`` chained from the unknown line; the good line never chained because its
  anchor already counts as resolved).
* ``newest_anchor_attribution_old_gate`` -- the same, plus ``lab_eventlog.decision_receipt`` of
  8df2558 (:func:`decision_receipt_8df2558`: ``anchor_seq`` and ``created_at`` suffice).  This is
  the path root's finding describes: the unknown line becomes the decision's "external
  receipt", ``ANCHOR_BLOCK`` checks ``decision_receipted()`` before the pending anchor, and the
  traffic switches and the follow-up is dispatched while the decision request is unanswered.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_eventlog                                                     # noqa: E402
import lab_orchestrator                                                 # noqa: E402
from lab_common import sha256_canonical, sha256_text                   # noqa: E402

read_spool_lines = lab_orchestrator.read_spool_lines


def ingest_8df2558(self) -> bool:
    """``World.ingest_receipts`` at 8df2558 (and 5ae183d), verbatim but for this docstring."""
    path = self.ctx.paths.anchor_spool / 'receipts.jsonl'
    lines, self.receipt_offset = read_spool_lines(path, self.receipt_offset)
    got = False
    for row in lines:
        pending = self.pending_anchor
        request = self._anchor_request(row.get('request_id'))
        anchor_seq = (int(request['anchor_seq']) if request is not None
                      else self.anchor_seq)
        if pending is not None and row.get('request_id') == pending['request_id']:
            got = True
            self.pending_anchor = None
            if pending.get('trigger') == 'decision' and not (
                    row.get('ok') and (self.tree_mock
                                       or row.get('created_at') is not None)):
                # failed, or "ok" without the external server time of a decision
                # receipt (12.4 item 3; claim 3 of 1.4) -- a local-only commit is not
                # an external receipt outside a MOCK tree
                self.decision_anchor_failed = True
        seen = self.anchor_resolved.get(anchor_seq)
        if seen == 'receipt' or (seen is not None and not row.get('ok')):
            continue
        self.anchor_resolved[anchor_seq] = 'receipt' if row.get('ok') else 'failed'
        if row.get('ok'):
            self.append('anchor_receipt', {
                'anchor_seq': anchor_seq,
                'pushed': bool(row.get('pushed')),
                'comment_id': (int(row['comment_id'])
                               if row.get('comment_id') is not None else None),
                'created_at': row.get('created_at'),
                'updated_at': row.get('updated_at'),
                'receipt_sha256': str(row.get('receipt_sha256') or sha256_canonical(row)),
                'commit_sha256': sha256_text(str(row.get('commit') or '')),
            }, durable=True)
            self.receipts_obtained += 1
        else:
            answered = request if request is not None else pending
            self.append('anchor_failed', {
                'anchor_seq': anchor_seq,
                'error_class': str(row.get('error_class') or 'api'),
                'blocking': bool(answered['blocking']) if answered else False,
            }, durable=True)
    return got


def decision_receipt_8df2558(events, *, mock: bool, before_seq=None) -> dict:
    """``lab_eventlog.decision_receipt`` at 8df2558, verbatim but for this docstring."""
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


MUTATIONS: tuple[str, ...] = ('newest_anchor_attribution',
                              'newest_anchor_attribution_old_gate')


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--mutation' or argv[1] not in MUTATIONS:
        sys.stderr.write('eb1_receipt_mutant_entry: --mutation {%s} comes first\n'
                         % ','.join(MUTATIONS))
        return 2
    lab_orchestrator.World.ingest_receipts = ingest_8df2558
    if argv[1] == 'newest_anchor_attribution_old_gate':
        lab_eventlog.decision_receipt = decision_receipt_8df2558
    return lab_orchestrator.main(argv[2:])


if __name__ == '__main__':
    sys.exit(main())
