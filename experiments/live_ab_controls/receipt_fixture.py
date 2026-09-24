"""Anchor-receipt fixtures of the receipt-attribution controls (root f855e45, 3e18d69).

Root's blocking finding on WIP 8df2558 (``reviews/eb1_receipt_attribution_review_20260924_0254.md``)
and its decision-receipt metadata ruling (``reviews/decision_receipt_metadata_ruling_20260924_0324.md``).
These helpers build what the controls inject or compare with:

* :func:`external_row` -- ONE line of ``anchor_spool/receipts.jsonl`` exactly as
  ``lab_anchor._handle`` writes it in its REAL mode for a request (a push and an issue comment),
  around a SYNTHETIC GitHub-shaped response (``id``, ``node_id``, ``body``, the two server times;
  no URL, no account).  ``drop`` / ``override`` / ``response_override`` make the evidence
  variants of :data:`EVIDENCE_VARIANTS`.  No network is touched and no real receipt exists: a
  control that "unlocks" with such a row shows the orchestrator's RULE accepts complete,
  consistent evidence -- it cannot show that a real comment exists (nothing here can).
* :func:`mock_row` -- the line ``lab_anchor --mock-receipt`` writes (no external evidence).
* :func:`append_line` -- append a line to the receipt spool as the anchor process does
  (``O_APPEND``, one ``write``, fsync), never rewriting what is there.
* :func:`anchor_body` / :func:`external_receipt_body` / :func:`mock_receipt_body` -- synthetic
  CHAIN bodies for the pure ``lab_eventlog.decision_receipt`` tests.

Outside the ``experiments/live_ab/tests_*.py`` glob on purpose (repair contract, placement).
Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Mapping

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                                       # noqa: E402
from lab_common import (canonical_json, sha256_bytes, sha256_canonical,   # noqa: E402
                        sha256_text)

CREATED_AT = '2026-09-24T03:30:00Z'
LATER = '2026-09-24T03:31:05Z'
EARLIER = '2026-09-24T03:29:00Z'
COMMENT_ID = 5806999001
NODE_ID = 'IC_kwDOSyntheticNode01'
COMMIT = 'c0ffee' + 'ab' * 17
ANCHOR_BRANCH = 'session60/live-ab-anchors'


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode('ascii')


def external_row(request: Mapping, *, trial: str | None = None,
                 branch: str = ANCHOR_BRANCH, created_at: str = CREATED_AT,
                 updated_at: str | None = None, comment_id: int = COMMENT_ID,
                 node_id: str = NODE_ID, commit: str = COMMIT, drop: tuple = (),
                 override: Mapping | None = None,
                 response_override: Mapping | None = None) -> dict:
    """A REAL-mode receipt line for ``request`` (a durable anchor request) whose evidence is
    complete and consistent -- unless ``drop`` removes row fields, ``override`` replaces row
    fields AFTER the response is hashed and encoded, or ``response_override`` edits the
    response before it is hashed and encoded (so the row and its response still agree on
    the hash but the response says something else)."""
    trial = str(trial if trial is not None else request['trial'])
    body_text = lab_common.anchor_comment_body(trial, request)
    updated_at = updated_at or created_at
    response = {'id': comment_id, 'node_id': node_id, 'body': body_text,
                'created_at': created_at, 'updated_at': updated_at,
                'author_association': 'OWNER'}
    response.update(dict(response_override or {}))
    raw = canonical_json(response).encode('utf-8')
    row = {
        'request_id': str(request['request_id']), 'ok': True, 'commit': commit,
        'branch': branch, 'pushed': True, 'comment_id': comment_id,
        'created_at': created_at, 'updated_at': updated_at,
        'receipt_sha256': sha256_bytes(raw), 'error_class': None,
        'anchor_file_sha256': sha256_canonical(lab_common.anchor_file_object(trial, request)),
        'node_id': node_id, 'comment_body_sha256': sha256_text(body_text),
        'comment_response_b64': b64(raw),
    }
    for key in drop:
        row.pop(key, None)
    row.update(dict(override or {}))
    return row


def mock_row(request: Mapping, *, trial: str | None = None) -> dict:
    """The line ``lab_anchor --mock-receipt`` writes: no commit, no push, no comment."""
    trial = str(trial if trial is not None else request['trial'])
    digest = sha256_canonical(lab_common.anchor_file_object(trial, request))
    return {'request_id': str(request['request_id']), 'ok': True, 'commit': None,
            'branch': None, 'pushed': False, 'comment_id': None, 'created_at': None,
            'updated_at': None, 'receipt_sha256': digest, 'error_class': None,
            'anchor_file_sha256': digest, 'node_id': None, 'comment_body_sha256': None,
            'comment_response_b64': None}


#: Every way a row BOUND to the decision request can lack or contradict the evidence of
#: root 3e18d69, with the reason the orchestrator must give (``malformed``: missing or
#: unparsable; ``conflict``: present and inconsistent).  name -> (kwargs of
#: :func:`external_row`, reason).
EVIDENCE_VARIANTS: dict[str, tuple[dict, str]] = {
    # the pushed commit / anchor head
    'not_pushed': ({'override': {'pushed': False}}, 'malformed'),
    'no_commit': ({'drop': ('commit',)}, 'malformed'),
    'no_branch': ({'drop': ('branch',)}, 'malformed'),
    'no_anchor_file': ({'drop': ('anchor_file_sha256',)}, 'malformed'),
    'other_branch': ({'branch': 'session60/some-other-branch'}, 'conflict'),
    'anchor_file_of_another_head': ({'override': {'anchor_file_sha256': 'e' * 64}},
                                    'conflict'),
    # the comment and its response
    'no_comment_id': ({'drop': ('comment_id',)}, 'malformed'),
    'no_node_id': ({'drop': ('node_id',)}, 'malformed'),
    'no_created_at': ({'drop': ('created_at',)}, 'malformed'),
    'no_updated_at': ({'drop': ('updated_at',)}, 'malformed'),
    'unparsable_created_at': ({'override': {'created_at': '2026-13-40T99:00:00Z'}},
                              'malformed'),
    'unparsable_updated_at': ({'override': {'updated_at': 'yesterday'}}, 'malformed'),
    'no_response_sha256': ({'drop': ('receipt_sha256',)}, 'malformed'),
    'no_comment_body_sha256': ({'drop': ('comment_body_sha256',)}, 'malformed'),
    'no_raw_response': ({'drop': ('comment_response_b64',)}, 'malformed'),
    'raw_response_not_json': ({'override': {'comment_response_b64': b64(b'<html>')}},
                              'malformed'),
    'response_sha256_of_other_bytes': ({'override': {'receipt_sha256': 'd' * 64}},
                                       'conflict'),
    'comment_body_sha256_of_other_text': ({'override': {'comment_body_sha256': 'c' * 64}},
                                          'conflict'),
    'response_to_another_body': ({'response_override': {'body': '{"trial":"T0"}'}},
                                 'conflict'),
    'response_id_differs': ({'response_override': {'id': COMMENT_ID + 1}}, 'conflict'),
    'response_node_id_differs': ({'response_override': {'node_id': 'IC_kwDOOther'}},
                                 'conflict'),
    'response_created_at_differs': ({'response_override': {'created_at': LATER}},
                                    'conflict'),
    'response_updated_at_differs': ({'response_override': {'updated_at': LATER}},
                                    'conflict'),
    'updated_before_created': ({'updated_at': EARLIER}, 'conflict'),
}


class AnchorRepo:
    """A throwaway ANCHOR repository for the pushed-commit evidence (root 3e18d69; review of
    988baf7, owner ruling R-push): ``lab_orchestrator.anchor_commit_problem`` reads the commit a
    decision receipt names from the anchor repository, so a control whose receipt must clear
    the gate commits the anchor's file there and pushes it, exactly as
    ``lab_anchor.commit_and_push`` does (explicit path, ``git push origin <branch>``).

    ``root`` becomes a git repository on ``branch`` whose ``origin`` is a local BARE repository
    beside it -- a directory, no network -- so a push moves ``refs/remotes/origin/<branch>`` as
    a real push does.  Only files :meth:`commit` names are ever added."""

    def __init__(self, root: Path, branch: str = ANCHOR_BRANCH) -> None:
        self.root = Path(root)
        self.branch = str(branch)
        self.origin = self.root.parent / (self.root.name + '_anchor_origin.git')
        self.root.mkdir(parents=True, exist_ok=True)
        self.git('init', '-q')
        # a local identity, no signing and no hooks in THIS repository, so that the real
        # ``lab_anchor.commit_and_push`` (plain ``git``) commits here as the fixture does
        for key, value in (('user.name', 'anchor-fixture'),
                           ('user.email', 'anchor-fixture@invalid'),
                           ('commit.gpgsign', 'false'), ('core.hooksPath', '/dev/null')):
            self.git('config', key, value)
        self.git('checkout', '-q', '-b', self.branch)
        _run_git(self.origin.parent, 'init', '-q', '--bare', str(self.origin))
        self.git('remote', 'add', 'origin', str(self.origin))
        # the branch's first commit, pushed (``commit_and_push`` reads ``HEAD``'s branch)
        self.commit([], message='anchor branch')

    def git(self, *args: str) -> str:
        return _run_git(self.root, *args)

    def commit(self, paths, *, push: bool = True, message: str = 'anchor') -> str:
        """Commit exactly ``paths`` (and push the branch unless ``push`` is false); returns
        the new commit id."""
        rel = [str(Path(p).resolve().relative_to(self.root.resolve())) for p in paths]
        self.git('add', '--', *rel)
        self.git('commit', '-q', '--allow-empty', '-m', message)
        if push:
            self.git('push', '-q', 'origin', self.branch)
        return self.git('rev-parse', 'HEAD').strip()

    def commit_anchor(self, anchors_dir: Path, trial: str, request: Mapping, *,
                      push: bool = True) -> str:
        """Write the anchor file of ``request`` (the bytes ``lab_anchor.write_anchor_file``
        writes) under ``anchors_dir`` unless it is already there, commit it and push."""
        path = Path(anchors_dir) / ('anchor_%d.json' % int(request['anchor_seq']))
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(canonical_json(lab_common.anchor_file_object(trial, request)),
                            encoding='utf-8')
        return self.commit([path], push=push)

    def checker(self, anchors_dir: Path, trial: str):
        """The ``commit_check`` of ``lab_orchestrator.judge_receipt_line`` over this
        repository -- what ``World.anchor_commit_check`` computes for its own tree."""
        import lab_orchestrator

        def check(commit: str, branch: str, request: Mapping) -> str | None:
            path = Path(anchors_dir) / ('anchor_%d.json' % int(request['anchor_seq']))
            want = sha256_canonical(lab_common.anchor_file_object(trial, request))
            return lab_orchestrator.anchor_commit_problem(self.root, commit, branch, path,
                                                          want)
        return check


def _run_git(cwd: Path, *args: str) -> str:
    """``git`` in ``cwd`` with a fixture identity, no signing, no hooks; raises on failure."""
    import subprocess
    res = subprocess.run(['git', '-c', 'user.name=anchor-fixture',
                          '-c', 'user.email=anchor-fixture@invalid', '-c', 'commit.gpgsign=false',
                          '-c', 'core.hooksPath=/dev/null', '-C', str(cwd)] + list(args),
                         capture_output=True, text=True, timeout=60, check=False)
    if res.returncode != 0:
        raise RuntimeError('git %s: %s' % (' '.join(args), res.stderr.strip()))
    return res.stdout


def append_line(spool: Path, line: bytes | Mapping) -> bytes:
    """Append ONE line to ``anchor_spool/receipts.jsonl`` as the anchor process does (one
    ``write`` under ``O_APPEND``, then fsync).  ``line`` is a row (canonical JSON) or raw
    bytes (a malformed line).  Returns the line's bytes without its newline."""
    raw = (bytes(line) if isinstance(line, (bytes, bytearray))
           else canonical_json(dict(line)).encode('utf-8'))
    spool = Path(spool)
    spool.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(spool), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, raw + b'\n')
        os.fsync(fd)
    finally:
        os.close(fd)
    return raw


# --------------------------------------------------------------------------- #
# synthetic chain bodies (pure decision_receipt tests)
# --------------------------------------------------------------------------- #
def request_id_of(anchor_seq: int) -> str:
    return '%032x' % (0xa11c0000 + int(anchor_seq))


def anchor_body(anchor_seq: int, trigger: str, *, request_id: str | None = None) -> dict:
    """A chained ``anchor`` body with synthetic digests and its request id."""
    return {'anchor_seq': int(anchor_seq), 'upto_seq': 10 * int(anchor_seq),
            'upto_h': sha256_text('h%d' % anchor_seq), 'segment_index': int(anchor_seq),
            'segment_bytes': 1000 + int(anchor_seq),
            'segment_sha256': sha256_text('seg%d' % anchor_seq), 'cumulative_bytes': 5000,
            'pairs_enrolled': 1, 'pairs_completed': 1,
            'records_manifest_sha256': sha256_text('rm'), 'server_log_sha256': {},
            'server_log_bytes': {}, 'trigger': str(trigger), 'blocking': True,
            'request_id': request_id or request_id_of(anchor_seq)}


def external_receipt_body(anchor: Mapping, trial: str, *, created_at: str = CREATED_AT,
                          updated_at: str | None = None) -> dict:
    """The ``anchor_receipt`` body the orchestrator chains for a verified external decision
    receipt of ``anchor``."""
    return {'anchor_seq': int(anchor['anchor_seq']), 'pushed': True,
            'comment_id': COMMENT_ID, 'created_at': created_at,
            'updated_at': updated_at or created_at, 'receipt_sha256': sha256_text('raw'),
            'commit_sha256': sha256_text(COMMIT), 'request_id': anchor['request_id'],
            'anchor_file_sha256': sha256_canonical(
                lab_common.anchor_file_object(trial, anchor)),
            'comment_body_sha256': sha256_text(lab_common.anchor_comment_body(trial, anchor)),
            'node_id_sha256': sha256_text(NODE_ID)}


def mock_receipt_body(anchor: Mapping) -> dict:
    """The ``anchor_receipt`` body of a MOCK receipt (no external evidence)."""
    return {'anchor_seq': int(anchor['anchor_seq']), 'pushed': False, 'comment_id': None,
            'created_at': None, 'updated_at': None, 'receipt_sha256': sha256_text('mock'),
            'commit_sha256': sha256_text(''), 'request_id': anchor['request_id'],
            'anchor_file_sha256': None, 'comment_body_sha256': None, 'node_id_sha256': None}
