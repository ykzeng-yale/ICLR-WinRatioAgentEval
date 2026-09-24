"""lab_anchor.py -- the anchor process (ARCHITECTURE_FINAL.md 3.14, protocol 12.4).

Critic N13 / ``PROTOCOL-GAP PG-12``: the anchor process is a **separate process with a
spool**, exactly like a worker.  **It never appends to the chain.**  The orchestrator
writes ``anchor_spool/requests.jsonl`` and reads ``anchor_spool/receipts.jsonl``, and it
alone appends ``anchor``, ``anchor_receipt`` and ``anchor_failed`` (AD-2).

This process therefore never reads the chain's *meaning*, only its bytes: it imports
``lab_common`` and nothing else from the ``lab_*`` namespace.

Modes (``main``):

``--local-only``   commit without pushing or commenting.  It exists ONLY for the mock dry
                   runs and the anchor drill of protocol 12.4 item 10 and is never used in
                   a trial, whose blocking anchors require real receipts.
``--dry-run``      write receipts with ``ok=False`` and ``error_class='dry_run'``.
``--mock-receipt`` mock dry runs only: a receipt over the local anchor file's own bytes,
                   with no commit, no push and no comment.  It carries **no external
                   evidence of any kind**; every artifact of such a run is stamped ``MOCK``
                   and the trial it belongs to is not a trial.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Mapping, Sequence, TypedDict

import lab_common
from lab_common import (TrialPaths, append_line_durable, canonical_json, sha256_bytes,
                        sha256_file, sha256_text, tokenize_path)

#: Release-hygiene patterns, ``class:regex`` (protocol 15.2).  The scanner reports the
#: class and the line, never the matched text.
DEFAULT_PATTERNS: tuple[str, ...] = (
    r'url:https?://',
    r'account:github\.com[:/][A-Za-z0-9_.-]+',
    r'commit_id:\b[0-9a-f]{40}\b',
    r'absolute_path:(?<![A-Za-z0-9_])/(Users|home)/[A-Za-z0-9_.-]+/',
    r'token:(gh[pousr]_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{16,})',
)

#: The one path allowlisted by exact string (protocol 5.7 item 2).
ALLOWLISTED_LITERALS: tuple[str, ...] = ('/private/tmp/labsbx',)

ERROR_CLASSES: tuple[str, ...] = ('tree_state', 'push', 'api', 'scanner', 'timeout',
                                  'dry_run')


class AnchorRequest(TypedDict):
    request_id: str
    trial: str
    anchor_seq: int
    upto_seq: int
    upto_h: str
    segment_index: int
    segment_bytes: int
    segment_sha256: str
    trigger: str
    blocking: bool
    publish_segments: bool


class AnchorReceipt(TypedDict):
    request_id: str
    ok: bool
    commit: str | None
    branch: str | None
    pushed: bool
    comment_id: int | None
    created_at: str | None
    updated_at: str | None
    receipt_sha256: str | None
    error_class: str | None
    #: The evidence the orchestrator checks before a DECISION receipt clears its blocking
    #: gate (root f855e45 / 3e18d69; ``lab_orchestrator.judge_receipt_line``): the SHA-256
    #: of the anchor file's bytes as written (the anchor head: ``upto_seq``/``upto_h``), and
    #: of a comment (12.4 item 3) its ``node_id``, the SHA-256 of the exact body posted and
    #: the RAW response bytes (base64), whose SHA-256 is ``receipt_sha256`` and whose own
    #: ``id``/``node_id``/``created_at``/``updated_at``/``body`` must agree with this row.
    anchor_file_sha256: str | None
    node_id: str | None
    comment_body_sha256: str | None
    comment_response_b64: str | None


# ---------------------------------------------------------------------------
# the anchor file
# ---------------------------------------------------------------------------
def write_anchor_file(paths: TrialPaths, req: AnchorRequest) -> Path:
    """``anchors/anchor_<anchor_seq>.json`` -- integers and hex digests only.

    No URL, no commit id, no account name, no free text: during the randomized phase the
    anchor branch receives anchor files only, which is what makes the arm-blind status file
    of protocol 14.7 meaningful (12.4 item 6)."""
    path = Path(paths.anchors) / ('anchor_%d.json' % int(req['anchor_seq']))
    path.parent.mkdir(parents=True, exist_ok=True)
    # the one definition the orchestrator's receipt check recomputes (lab_common)
    body = lab_common.anchor_file_object(str(req['trial']), req)
    if path.exists() and path.read_text(encoding='utf-8') == canonical_json(body):
        return path
    lab_common.write_json_atomic(path, body, durable=True)
    return path


# ---------------------------------------------------------------------------
# the release-hygiene scanner
# ---------------------------------------------------------------------------
def scan_for_identifiers(paths: Sequence[Path], patterns: Sequence[str]) -> list[dict]:
    """Return hits as ``{'path': tokenized, 'pattern_class': str, 'line': int}``.

    **Never the matched text**: the point of the scanner is to withhold an identifier, so
    reporting it would defeat it.  ``patterns`` entries are ``class:regex``; a bare regex is
    reported under the class ``token``."""
    compiled: list[tuple[str, re.Pattern]] = []
    for raw in patterns:
        cls, sep, rx = str(raw).partition(':')
        if not sep or ' ' in cls:
            cls, rx = 'token', str(raw)
        compiled.append((cls, re.compile(rx)))
    hits: list[dict] = []
    for path in paths:
        p = Path(path)
        if not p.exists() or not p.is_file():
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        try:
            tok = tokenize_path(p)
        except lab_common.UntokenizablePath:
            tok = '<TMP>/' + p.name
        for lineno, line in enumerate(text.splitlines(), start=1):
            probe = line
            for literal in ALLOWLISTED_LITERALS:
                probe = probe.replace(literal, '')
            for cls, rx in compiled:
                if rx.search(probe):
                    hits.append({'path': tok, 'pattern_class': cls, 'line': lineno})
    return hits


# ---------------------------------------------------------------------------
# git and the issue comment
# ---------------------------------------------------------------------------
def commit_and_push(repo: Path, files: Sequence[Path], message_id: str, *,
                    expect_branch: str, expect_parent: str, push: bool) -> dict:
    """``git add`` of EXPLICIT paths only, then commit and optionally push.

    Before committing, the real path of the working tree, its ``HEAD`` branch, the expected
    parent commit and a clean index are asserted (protocol 12.4 item 2, the first of the two
    shared-clone guards of protocol 2.1).  Never ``git add -A``, never a rebase, never a
    force push, never a reset.  A violated assertion returns
    ``{'ok': False, 'error_class': 'tree_state'}`` -- it does not raise, so the caller can
    spool the failure; on a blocking anchor that becomes ``trial_paused(anchor_unavailable)``
    (6.4 row 26)."""
    repo = Path(repo)
    def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(['git', '-C', str(repo)] + list(args), capture_output=True,
                              text=True, timeout=120, check=check)

    try:
        branch = _git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
        parent = _git('rev-parse', 'HEAD').stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                'branch': None, 'pushed': False}
    if expect_branch and branch != expect_branch:
        return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                'branch': branch, 'pushed': False}
    if expect_parent and parent != expect_parent:
        return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                'branch': branch, 'pushed': False}
    staged = _git('diff', '--cached', '--name-only').stdout.strip()
    if staged:
        return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                'branch': branch, 'pushed': False}
    rel: list[str] = []
    for f in files:
        try:
            rel.append(str(Path(f).resolve().relative_to(repo.resolve())))
        except ValueError:
            return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                    'branch': branch, 'pushed': False}
    add = _git('add', '--', *rel)
    if add.returncode != 0:
        return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                'branch': branch, 'pushed': False}
    commit = _git('commit', '-m', str(message_id))
    if commit.returncode != 0:
        return {'ok': False, 'error_class': 'tree_state', 'commit': None,
                'branch': branch, 'pushed': False}
    head = _git('rev-parse', 'HEAD').stdout.strip()
    pushed = False
    if push:
        res = _git('push', 'origin', branch)
        if res.returncode != 0:
            return {'ok': False, 'error_class': 'push', 'commit': head,
                    'branch': branch, 'pushed': False}
        pushed = True
    return {'ok': True, 'error_class': None, 'commit': head, 'branch': branch,
            'pushed': pushed}


#: The REPOSITORY-SPECIFIC issue API base.
#:
#: `post_comment` appends "/issues/<n>/comments". With the old default
#: "https://api.github.com" that composes to
#: "https://api.github.com/issues/13/comments", which addresses no repository.
#: Root, reviews/lock_anchor_review_20260923_0348.md: "Supply
#: `https://api.github.com/repos/ykzeng-yale/ICLR-WinRatioAgentEval` as the base,
#: yielding the repository-specific issue13 endpoint."
DEFAULT_ISSUE_API_BASE: str = 'https://api.github.com/repos/ykzeng-yale/ICLR-WinRatioAgentEval'


def assert_repo_scoped_api(api: str, *, stage: str) -> str:
    """An issue API base that names no repository cannot address an issue.

    Checked rather than assumed: the composed URL is what matters, and a base
    without "/repos/<owner>/<name>" silently produces a well-formed URL that
    addresses nothing.
    """
    base = str(api).rstrip('/')
    if '/repos/' not in base:
        raise ValueError(
            'issue API base %r at %s names no repository; "%s/issues/N/comments" '
            'would address nothing. Expected a ".../repos/<owner>/<name>" base.'
            % (base, stage, base))
    return base


_NO_COMMENT: dict = {'ok': False, 'error_class': 'api', 'comment_id': None, 'node_id': None,
                    'created_at': None, 'updated_at': None, 'receipt_sha256': None,
                    'response_b64': None}


def post_comment(api: str, issue: int, body: str, token_env: str) -> dict:
    """One issue comment (protocol 12.4 item 3).  The API response fields ``id``,
    ``node_id``, ``created_at`` and ``updated_at`` and the SHA-256 of the raw response are
    recorded; the body text never is (the caller records its SHA-256).  ``node_id`` was
    omitted until root's 3e18d69 ruling.  ``response_b64`` is the raw response bytes, so that
    the orchestrator can check that these fields are the response's own and that the
    response echoes the exact body posted; it lives in the anchor spool and the private
    receipt under ``work/`` only, never in the chain.  Nothing here judges the response: a
    missing field is returned as ``None`` and refused by the orchestrator."""
    import requests                                    # imported here: never at import time
    token = os.environ.get(str(token_env) or '')
    if not token:
        return dict(_NO_COMMENT)
    # REFUSE a base that names no repository, before any request is made.
    url = '%s/issues/%d/comments' % (
        assert_repo_scoped_api(api, stage='post_comment'), int(issue))
    try:
        res = requests.post(url, json={'body': str(body)}, timeout=60, headers={
            'Authorization': 'Bearer %s' % token,
            'Accept': 'application/vnd.github+json'})
    except Exception:                                   # noqa: BLE001
        return dict(_NO_COMMENT)
    if res.status_code >= 300:
        return dict(_NO_COMMENT)
    try:
        data = res.json()
    except ValueError:
        return dict(_NO_COMMENT)
    if not isinstance(data, dict):
        return dict(_NO_COMMENT)
    node_id = data.get('node_id')
    try:
        comment_id = int(data.get('id')) if data.get('id') is not None else None
    except (TypeError, ValueError):
        comment_id = None
    return {'ok': True, 'error_class': None,
            'comment_id': comment_id,
            'node_id': node_id if isinstance(node_id, str) else None,
            'created_at': data.get('created_at'), 'updated_at': data.get('updated_at'),
            'receipt_sha256': sha256_bytes(res.content),
            'response_b64': base64.b64encode(bytes(res.content)).decode('ascii')}


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------
def serve(paths: TrialPaths, cfg: Mapping, *, once: bool = False) -> int:
    """Read new lines of ``anchor_spool/requests.jsonl``; for each, write the anchor file,
    run the scanner over the files to be committed, commit / push / comment, and append an
    ``AnchorReceipt`` line to ``anchor_spool/receipts.jsonl`` (durable).

    A blocking request is retried for up to ``cfg['anchor']['blocking_wait_minutes']``; a
    periodic request is attempted once and its failure is spooled immediately, because a
    failed periodic push never blocks and never changes an outcome (protocol 12.4 item 5).
    ``once`` processes the backlog and exits."""
    rt = dict(dict(cfg).get('_runtime') or {})
    mode = str(rt.get('anchor_mode') or 'real')
    anchor_cfg = dict(dict(cfg).get('anchor') or {})
    wait_s = float(rt.get('blocking_wait_s',
                          float(anchor_cfg.get('blocking_wait_minutes', 30)) * 60.0))
    req_path = Path(paths.anchor_spool) / 'requests.jsonl'
    rec_path = Path(paths.anchor_spool) / 'receipts.jsonl'
    req_path.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    idle_since = time.monotonic()
    poll_s = float(rt.get('anchor_poll_s', 0.05))
    deadline = float(rt.get('anchor_max_idle_s', 0.0))
    handled = 0
    while True:
        rows, offset = _read_new(req_path, offset)
        for row in rows:
            receipt = _handle(paths, cfg, row, mode=mode, wait_s=wait_s)
            _append_receipt(rec_path, receipt)
            handled += 1
            idle_since = time.monotonic()
        if once and not rows:
            return handled
        if deadline and (time.monotonic() - idle_since) > deadline:
            return handled
        time.sleep(poll_s)


def _read_new(path: Path, offset: int) -> tuple[list[dict], int]:
    if not path.exists():
        return [], offset
    raw = path.read_bytes()
    out: list[dict] = []
    pos = offset
    while True:
        nl = raw.find(b'\n', pos)
        if nl < 0:
            break
        chunk = raw[pos:nl]
        if chunk.strip():
            try:
                out.append(json.loads(chunk.decode('utf-8')))
            except ValueError:
                pass
        pos = nl + 1
    return out, pos


def _append_receipt(path: Path, receipt: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        append_line_durable(fd, canonical_json(dict(receipt)), durable=True)
    finally:
        os.close(fd)


def _handle(paths: TrialPaths, cfg: Mapping, req: Mapping, *, mode: str,
            wait_s: float) -> dict:
    anchor_file = write_anchor_file(paths, req)          # type: ignore[arg-type]
    receipt: dict = {'request_id': str(req.get('request_id') or uuid.uuid4().hex),
                     'ok': False, 'commit': None, 'branch': None, 'pushed': False,
                     'comment_id': None, 'created_at': None, 'updated_at': None,
                     'receipt_sha256': None, 'error_class': None,
                     'anchor_file_sha256': sha256_file(anchor_file), 'node_id': None,
                     'comment_body_sha256': None, 'comment_response_b64': None}
    if mode == 'dry_run':
        receipt['error_class'] = 'dry_run'
        return receipt

    files = [anchor_file]
    if req.get('publish_segments'):
        files.extend(sorted(Path(paths.events).glob('seg_*.jsonl'))[:-1])
    hits = scan_for_identifiers(files, DEFAULT_PATTERNS)
    if hits:
        # 12.4 item 6: a hit withholds that file while anchoring continues.  The
        # orchestrator turns the failure into `publication_withheld`; no sanitized copy of
        # the chain is ever produced.
        files = [f for f in files
                 if all(h['path'] != _tok(f) for h in hits)]
        if not files:
            receipt['error_class'] = 'scanner'
            return receipt

    if mode == 'mock':
        # MOCK ONLY: no commit, no push, no comment, no external evidence whatever.
        receipt['ok'] = True
        receipt['receipt_sha256'] = sha256_file(anchor_file)
        return receipt

    anchor_cfg = dict(dict(cfg).get('anchor') or {})
    rt = dict(dict(cfg).get('_runtime') or {})
    repo = Path(rt.get('repo') or lab_common.REPO_ROOT)
    deadline = time.monotonic() + (wait_s if req.get('blocking') else 0.0)
    while True:
        out = commit_and_push(
            repo, files, 'live_ab anchor %s/%s' % (req.get('trial'),
                                                   req.get('anchor_seq')),
            expect_branch=str(rt.get('expect_branch') or anchor_cfg.get('branch') or ''),
            expect_parent=str(rt.get('expect_parent') or ''),
            push=mode != 'local')
        if out.get('ok'):
            receipt.update({'ok': True, 'commit': out.get('commit'),
                            'branch': out.get('branch'),
                            'pushed': bool(out.get('pushed')),
                            'receipt_sha256': sha256_text(str(out.get('commit') or ''))})
            break
        receipt['error_class'] = out.get('error_class') or 'push'
        if not req.get('blocking') or time.monotonic() >= deadline:
            return receipt
        time.sleep(1.0)

    if mode == 'real' and str(req.get('trigger')) in tuple(
            anchor_cfg.get('comment_triggers') or ()):
        body = lab_common.anchor_comment_body(str(req.get('trial')), req)
        comment = post_comment(str(rt.get('api') or DEFAULT_ISSUE_API_BASE),
                               int(anchor_cfg.get('issue') or 0), body,
                               str(rt.get('token_env') or 'GITHUB_TOKEN'))
        if comment.get('ok'):
            receipt.update({'comment_id': comment.get('comment_id'),
                            'node_id': comment.get('node_id'),
                            'created_at': comment.get('created_at'),
                            'updated_at': comment.get('updated_at'),
                            'receipt_sha256': comment.get('receipt_sha256'),
                            'comment_body_sha256': sha256_text(body),
                            'comment_response_b64': comment.get('response_b64')})
        else:
            receipt['error_class'] = 'api'
            receipt['ok'] = False
    _write_private(paths, receipt)
    return receipt


def _tok(path: Path) -> str:
    try:
        return tokenize_path(path)
    except lab_common.UntokenizablePath:
        return '<TMP>/' + Path(path).name


def _write_private(paths: TrialPaths, receipt: Mapping) -> None:
    """The identified receipt (comment ids, commit ids) lives under ``work/`` only."""
    path = Path(paths.anchors_private) / 'receipts.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        append_line_durable(fd, canonical_json(dict(receipt)), durable=True)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--trial T1 --config ... [--once] [--local-only] [--dry-run]``.

    ``--local-only`` commits without pushing or commenting; it exists ONLY for the mock dry
    runs and the anchor drill of protocol 12.4 item 10 and is never used in a trial.
    ``--dry-run`` writes receipts with ``ok=False, error_class='dry_run'``.
    ``--mock-receipt`` is the mock dry runs' offline receipt: no git, no network, no
    external evidence."""
    ap = argparse.ArgumentParser(prog='lab_anchor')
    ap.add_argument('--trial', required=True)
    ap.add_argument('--config', required=True)
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--local-only', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--mock-receipt', action='store_true')
    ap.add_argument('--results', default=None)
    ap.add_argument('--work', default=None)
    ap.add_argument('--max-idle-s', type=float, default=0.0)
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    rt = cfg.setdefault('_runtime', {})
    if args.dry_run:
        rt['anchor_mode'] = 'dry_run'
    elif args.mock_receipt:
        rt['anchor_mode'] = 'mock'
    elif args.local_only:
        rt['anchor_mode'] = 'local'
    rt.setdefault('anchor_mode', 'real')
    if args.max_idle_s:
        rt['anchor_max_idle_s'] = float(args.max_idle_s)
    results = Path(args.results or rt.get('results_root') or lab_common.RESULTS_ROOT)
    work = Path(args.work or rt.get('work_root') or lab_common.WORK_ROOT)
    trial = str(args.trial)
    paths = TrialPaths(
        trial=trial, results=results / trial, events=results / trial / 'events',
        anchors=results / trial / 'anchors', work=work / trial,
        jobs=work / trial / 'jobs', spools=work / trial / 'spools',
        records=work / trial / 'records', requests=work / trial / 'requests',
        anchor_spool=work / trial / 'anchor_spool',
        anchors_private=work / trial / 'anchors_private', logs=work / trial / 'logs',
        run_lock=work / trial / 'run.lock', sandbox_lock=work / trial / 'sandbox.lock')
    serve(paths, cfg, once=bool(args.once))
    return 0


if __name__ == '__main__':                                   # pragma: no cover
    sys.exit(main())
