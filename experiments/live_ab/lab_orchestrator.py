"""lab_orchestrator.py -- the single chain writer (ARCHITECTURE_FINAL.md 3.13 and 7).

G5.  One process, one thread, one ``while True:`` with a 50 ms poll.  Every iteration:
reap finished worker processes, ingest new spool bytes, ingest anchor receipts, poll health
on a 5 s timer, take the transition of the table in ARCHITECTURE_FINAL.md 7.1.

Three properties are structural rather than asserted afterwards.

1. **The look cadence is not re-implemented here.**  After every appended event of a type
   ``lab_monitor.replay`` consumes, the orchestrator replays the in-memory chain and writes
   the looks the replay produced but the chain does not yet carry.  The bodies are the
   replay's own snapshots.  The verifier check ``monitor.replay`` therefore cannot fail on
   cadence or on a float, because the live value *is* the replayed value.  The live
   ``MonitorState`` is maintained in parallel only so that the frozen ``lab_monitor.decide``
   can be called on a real state, and its snapshot is compared with the replay's at every
   look: a difference raises ``MonitorError`` and pauses the trial (7.1 row 22).

2. **The shadow is the second code path.**  ``lab_reference_rule.looks_from_chain`` is
   evaluated on the same chain at every look and its values go into ``monitor_update.shadow``
   (protocol 8.9).  A mismatch takes the ``trial_paused(monitor_mismatch)`` transition
   before any decision is acted on.

3. **Resume is a pure function.**  ``plan_resume`` reads nothing and writes nothing; the
   resume path is ``read_chain`` -> ``plan_resume`` -> apply the plan as durable appends.

The orchestrator never imports ``lab_worker`` or ``lab_client``: a worker is a subprocess and
its spool is parsed here by :func:`read_spool_lines`.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

import lab_common
import lab_coin
import lab_data
import lab_enclosure
import lab_eventlog
import lab_hostcheck
import lab_monitor
import lab_reference_rule
import lab_server
import lab_serving_manifest
from lab_common import (AbortTrial, ChainError, MonitorError, PauseTrial, PreflightError,
                        SpoolError, TrialPaths, canonical_json, sha256_bytes,
                        sha256_canonical, sha256_file, sha256_text, tokenize_path,
                        write_json_atomic)
from lab_eventlog import EventLog, read_chain
from lab_monitor import MonitorConfig
from lab_server import ServerSpec

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
#: The states of ARCHITECTURE_FINAL.md 7.1.  ``OPENING_WAIT`` is that table's own
#: ``OPENING.wait`` (row 3) spelled as an identifier, and the three ``ENDED_*`` values are
#: the terminal sinks the table draws as "terminal".
State = Literal['PREFLIGHT', 'OPENING', 'OPENING_WAIT', 'IDLE', 'ENROLLED', 'COMMITTED',
                'RUNNING', 'PARTIAL', 'LOOK', 'DECIDED', 'ANCHOR_BLOCK', 'SWITCHING',
                'POST_DECISION', 'DRAINING', 'PAUSED', 'CLOSING', 'ENDED', 'ABORTED',
                'ENDED_ABORTED', 'ENDED_PAUSED', 'ENDED_REFUSED']

#: The event types ``lab_monitor.replay`` consumes.  Appending one of these is the only
#: thing that can produce a look, so it is the only thing that triggers an evaluation.
CONSUMED: frozenset[str] = frozenset(lab_monitor.CONSUMED_EVENT_TYPES)

#: The six keys of ``timings`` and the four of ``usage`` the event schema declares.  The
#: server reports more (``prompt_per_second``); an unknown key is a schema violation, so the
#: spool's object is projected onto the declared keys rather than copied.
TIMINGS_KEYS: tuple[str, ...] = ('cache_n', 'prompt_n', 'prompt_ms', 'predicted_n',
                                 'predicted_ms', 'predicted_per_second')
USAGE_KEYS: tuple[str, ...] = ('prompt_tokens', 'completion_tokens', 'total_tokens',
                               'cached_tokens')
FINISH_REASONS: frozenset[str] = frozenset({'stop', 'length', 'tool_calls',
                                            'content_filter', 'abort'})

#: Terminal error classes that count towards the ten-consecutive-failures auto abort
#: (protocol 6.4, counted in reveal order).
TERMINAL_CLASSES: frozenset[str] = frozenset({'episode_timeout', 'worker_died',
                                              'interrupted'})

_SHADOW_TOL: float = 1e-9

#: ``trial_aborted.reason`` for a failed first start, by the ``server_start_failed.stage``
#: (repair contract EB1; protocol 6.4 rows 5 and 6): a start that differs from the frozen
#: weights, serving build or golden ``/props`` is ``server_identity``; a smoke whose receipt
#: does not match (or that could not be made) is ``receipt_mismatch``; a server that never
#: came up is ``infrastructure``.
START_FAILURE_REASON: dict[str, str] = {
    'gguf': 'server_identity', 'serving_manifest': 'server_identity',
    'identity': 'server_identity', 'smoke': 'receipt_mismatch',
    'launch': 'infrastructure', 'health': 'infrastructure',
}


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------
def frozen_cfg(cfg: Mapping) -> dict:
    """[pure] The frozen configuration without the runtime overlay.

    ``cfg['_runtime']`` carries what the *invocation* needs (result roots, mock base urls,
    the worker command line, dry-run limits).  It is never part of the frozen file, never
    hashed into the bundle and never read by a rule; every hash and every statistical call
    uses this projection."""
    return {k: v for k, v in dict(cfg).items() if not str(k).startswith('_')}


def runtime(cfg: Mapping) -> dict:
    """[pure] The runtime overlay of this invocation (never frozen, never hashed)."""
    rt = dict(cfg).get('_runtime') or {}
    return dict(rt)


def read_spool_lines(path: str | Path, offset: int = 0) -> tuple[list[dict], int]:
    """Parse the complete lines of a worker spool from ``offset``.

    A trailing incomplete line is ignored and re-read next time; the file is never
    rewritten or truncated (ARCHITECTURE_FINAL.md 5, ingest rules).  Every returned line
    carries ``_offset``, the byte offset at which it starts, which the chain records so a
    reader can find the evidence.  ``spool_seq`` must be gapless: a gap is a ``SpoolError``
    and the attempt is treated as interrupted."""
    p = Path(path)
    if not p.exists():
        return [], offset
    raw = p.read_bytes()
    if offset > len(raw):
        raise SpoolError(f'{p.name}: spool shrank from {offset} to {len(raw)} bytes')
    out: list[dict] = []
    pos = offset
    while True:
        nl = raw.find(b'\n', pos)
        if nl < 0:
            break
        chunk = raw[pos:nl]
        if chunk.strip():
            try:
                row = json.loads(chunk.decode('utf-8'))
            except Exception as exc:                       # noqa: BLE001
                raise SpoolError(f'{p.name}: unparsable line at {pos}: {exc}') from exc
            if not isinstance(row, dict):
                raise SpoolError(f'{p.name}: line at {pos} is not an object')
            row['_offset'] = pos
            out.append(row)
        pos = nl + 1
    return out, pos


def read_whole_spool(path: str | Path) -> list[dict]:
    """Every complete line of a spool, with ``spool_seq`` gaplessness enforced."""
    lines, _ = read_spool_lines(path, 0)
    for i, row in enumerate(lines):
        if int(row.get('spool_seq', -1)) != i:
            raise SpoolError(f'{Path(path).name}: spool_seq gap at line {i}')
    return lines


# ---------------------------------------------------------------------------
# anchor receipts: attribution and the decision receipt's evidence (root f855e45, 3e18d69)
# ---------------------------------------------------------------------------
#: The chain events a line of ``anchor_spool/receipts.jsonl`` turns into: EXACTLY ONE per
#: complete non-blank line, in spool order, so a resumed invocation re-reads the spool from
#: its start and skips as many lines as the chain holds these events (``World._receipt_replay``).
RECEIPT_LINE_EVENTS: tuple[str, ...] = ('anchor_receipt', 'anchor_failed',
                                        'anchor_receipt_rejected')
#: The durable request fields the chained ``anchor`` event must carry identically.
_ANCHOR_BINDING_KEYS: tuple[str, ...] = ('upto_seq', 'upto_h', 'segment_index',
                                         'segment_bytes', 'segment_sha256', 'trigger',
                                         'blocking')


def read_receipt_lines(path: str | Path, offset: int = 0) -> tuple[list[tuple[int, bytes]],
                                                                    int]:
    """``(offset, exact bytes without the newline)`` of every complete non-blank line of the
    anchor process's receipt spool from ``offset``.  Unlike :func:`read_spool_lines` it never
    parses: a line that is not JSON is judged (``malformed``), not a crash.  A trailing
    incomplete line is re-read next time; the file is never rewritten."""
    p = Path(path)
    if not p.exists():
        return [], offset
    raw = p.read_bytes()
    if offset > len(raw):
        raise SpoolError(f'{p.name}: spool shrank from {offset} to {len(raw)} bytes')
    out: list[tuple[int, bytes]] = []
    pos = offset
    while True:
        nl = raw.find(b'\n', pos)
        if nl < 0:
            break
        chunk = raw[pos:nl]
        if chunk.strip():
            out.append((pos, chunk))
        pos = nl + 1
    return out, pos


def _is_hex(value: object, n: int) -> bool:
    return (isinstance(value, str) and len(value) == n
            and all(c in '0123456789abcdef' for c in value))


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


#: The closed problem codes of :func:`anchor_commit_problem` (the pushed commit bound to its
#: anchor, read from the anchor repository; root 3e18d69).
ANCHOR_COMMIT_PROBLEMS: tuple[str, ...] = ('repo_unreadable', 'anchor_outside_repo',
                                           'commit_absent', 'not_on_pushed_branch',
                                           'anchor_file_absent', 'anchor_file_mismatch')


def anchor_commit_problem(repo: str | Path, commit: str, branch: str,
                          anchor_path: str | Path, want_sha256: str) -> str | None:
    """Whether the receipt's pushed ``commit`` is bound to its anchor, read LOCALLY from the
    anchor repository (read-only ``git``, no network): ``None`` when it is, else one code of
    :data:`ANCHOR_COMMIT_PROBLEMS`.

    Root 3e18d69 asks the gate to "verify the pushed commit/anchor-head evidence"; review of
    988baf7 (reviewer 1 finding 5; owner ruling R-push): the gate checked only that ``pushed``
    was true, the commit 40 hex and the branch the frozen name, and ``anchor_file_sha256``
    against a digest anyone can compute from the durable request -- a receipt naming a commit
    that does not exist cleared it.  ``lab_anchor.commit_and_push`` commits the anchor file
    (``anchors/anchor_<anchor_seq>.json``) in the anchor repository and pushes that branch to
    ``origin``, which moves the repository's own ``refs/remotes/origin/<branch>``.  Performs:
    the anchor file lies inside the repository (``anchor_outside_repo``); ``git cat-file -e
    <commit>^{commit}`` (``commit_absent``); ``git merge-base --is-ancestor <commit>
    refs/remotes/origin/<branch>`` -- the commit is on the branch as the repository recorded
    its last push (``not_on_pushed_branch``); ``git show <commit>:<anchor file>`` exists
    (``anchor_file_absent``) and its bytes hash to ``want_sha256``, the digest of this
    anchor's own file object (``anchor_file_mismatch``); a ``git`` that cannot run is
    ``repo_unreadable``.  Does NOT perform: any check that the remote itself (GitHub) holds
    the commit -- no network is read; the push's evidence is the repository's own record of
    it."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(['git', '-C', str(repo)] + list(args), capture_output=True,
                              timeout=60, check=False)
    try:
        rel = Path(anchor_path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except (OSError, ValueError):
        return 'anchor_outside_repo'
    try:
        if git('rev-parse', '--git-dir').returncode != 0:
            return 'repo_unreadable'
        if git('cat-file', '-e', '%s^{commit}' % commit).returncode != 0:
            return 'commit_absent'
        if git('merge-base', '--is-ancestor', commit,
               'refs/remotes/origin/%s' % branch).returncode != 0:
            return 'not_on_pushed_branch'
        shown = git('show', '%s:%s' % (commit, rel))
    except (OSError, subprocess.SubprocessError):
        return 'repo_unreadable'
    if shown.returncode != 0:
        return 'anchor_file_absent'
    if sha256_bytes(shown.stdout) != want_sha256:
        return 'anchor_file_mismatch'
    return None


def decision_evidence_verdict(row: Mapping, request: Mapping, trial: str, *,
                              anchor_branch: str, commit_check) -> tuple[str | None, dict]:
    """[pure] Whether an ``ok`` receipt spool ``row`` bound to the durable DECISION anchor
    ``request`` carries the external evidence of protocol 12.4 items 3 and 5 as root's
    3e18d69 ruling reads them: ``(None, digests)`` when it does, else ``('malformed', {})``
    (evidence missing or unparsable) or ``('conflict', {})`` (evidence present and
    inconsistent with itself or with the request).

    Performs.  Missing -> ``malformed``: ``pushed`` true, a 40-hex ``commit`` and a
    ``branch`` (the pushed commit); a 64-hex ``anchor_file_sha256`` (the anchor head); a
    comment ``comment_id`` (int), a non-empty ``node_id``, parsable ``created_at`` and
    ``updated_at`` (``lab_eventlog.parse_utc_instant``), a 64-hex ``receipt_sha256`` and
    ``comment_body_sha256``, and ``comment_response_b64`` decoding to a JSON object.
    Inconsistent -> ``conflict``: ``branch`` is not the frozen ``anchor.branch`` (when one is
    frozen); ``anchor_file_sha256`` is not the SHA-256 of ``lab_common.anchor_file_object``
    of this request; ``comment_body_sha256`` is not the SHA-256 of
    ``lab_common.anchor_comment_body`` (trial id, ``upto_seq``, ``upto_h``, segment SHA-256);
    the raw response's SHA-256 is not ``receipt_sha256``; the response's own ``id``,
    ``node_id``, ``created_at``, ``updated_at`` differ from the row's, or its ``body`` is not
    exactly that comment body (the metadata is then not the response to the matching body);
    ``updated_at`` earlier than ``created_at``; and, once all of that holds, the pushed commit
    is not bound to this anchor -- ``commit_check(commit, branch, request)`` (the World's
    :func:`anchor_commit_problem` over the anchor repository) names a problem.  No wall-clock
    equality and no latency window is imposed (12.4: no timestamp authority).  Does NOT
    perform: any check that the comment exists on a server, or that the remote holds the
    commit (no network is read; the push is the anchor repository's own record of it)."""
    commit, branch = row.get('commit'), row.get('branch')
    comment_id, node_id = row.get('comment_id'), row.get('node_id')
    created = lab_eventlog.parse_utc_instant(row.get('created_at'))
    updated = lab_eventlog.parse_utc_instant(row.get('updated_at'))
    raw_b64 = row.get('comment_response_b64')
    response: object = None
    raw_response = b''
    if isinstance(raw_b64, str):
        try:
            raw_response = base64.b64decode(raw_b64.encode('ascii'), validate=True)
            response = json.loads(raw_response.decode('utf-8'))
        except (ValueError, binascii.Error, UnicodeError):
            response = None
    if not (row.get('pushed') is True and _is_hex(commit, 40)
            and isinstance(branch, str) and branch
            and _is_hex(row.get('anchor_file_sha256'), 64)
            and _is_int(comment_id) and isinstance(node_id, str) and node_id
            and created is not None and updated is not None
            and _is_hex(row.get('receipt_sha256'), 64)
            and _is_hex(row.get('comment_body_sha256'), 64)
            and isinstance(response, dict)):
        return 'malformed', {}
    body_text = lab_common.anchor_comment_body(trial, request)
    want_file = sha256_canonical(lab_common.anchor_file_object(trial, request))
    assert isinstance(response, dict)
    if ((anchor_branch and branch != anchor_branch)
            or row['anchor_file_sha256'] != want_file
            or row['comment_body_sha256'] != sha256_text(body_text)
            or sha256_bytes(raw_response) != row['receipt_sha256']
            or not _is_int(response.get('id')) or response.get('id') != comment_id
            or response.get('node_id') != node_id
            or response.get('created_at') != row.get('created_at')
            or response.get('updated_at') != row.get('updated_at')
            or response.get('body') != body_text
            or updated < created):
        return 'conflict', {}
    if commit_check(str(commit), str(branch), request) is not None:
        return 'conflict', {}
    return None, {'anchor_file_sha256': want_file,
                  'comment_body_sha256': sha256_text(body_text),
                  'node_id_sha256': sha256_text(node_id)}


def judge_receipt_line(raw: bytes, *, trial: str, request_of, anchors: Mapping[int, Mapping],
                       resolved: Mapping[int, str], resolving_sha: Mapping[int, str],
                       newest_anchor_seq: int, mock: bool, anchor_branch: str,
                       commit_check) -> dict:
    """[pure but for ``request_of`` and ``commit_check``] What ONE line of
    ``anchor_spool/receipts.jsonl`` becomes.

    Root f855e45 (``reviews/eb1_receipt_attribution_review_20260924_0254.md``): 8df2558
    attributed a line whose ``request_id`` no request carried to the NEWEST anchor, and an
    ``ok`` line then became a success-valued ``anchor_receipt`` that could clear the decision
    gate.  Here a line is attributed to an anchor ONLY when its ``request_id`` is bound
    exactly to that anchor's durable request (``request_of(request_id)``: this invocation's,
    or ``anchor_spool/requests.jsonl``) AND that request agrees with the chained ``anchor``
    of its ``anchor_seq`` (``anchors``; the anchor's own ``request_id`` when it carries one).
    Returns ``{'kind', 'type', 'body', 'request_id', 'anchor_seq', 'raw_sha256'}`` with
    ``kind`` one of ``receipt`` (-> ``anchor_receipt``), ``failed`` (-> ``anchor_failed``)
    or ``rejected`` (-> ``anchor_receipt_rejected``, reason in
    ``lab_eventlog.E_RECEIPT_REJECT``, checked in this order): ``malformed`` (not a JSON
    object; ``request_id`` not 32 lowercase hex -- then chained as null; ``ok`` not a bool);
    ``unknown_request``; ``conflict`` (request and chained anchor disagree); for an anchor
    already resolved -- ``duplicate`` (these exact bytes resolved it), ``stale`` (an earlier
    anchor), ``conflict`` (the newest anchor); a failed line whose ``error_class`` is not in
    the closed set -> ``malformed``; an ``ok`` line without a 64-hex ``receipt_sha256`` or
    whose fields the chain cannot hold -> ``malformed``; an ``ok`` line bound to a
    ``decision`` request: outside a MOCK tree it must pass :func:`decision_evidence_verdict`
    (its ``malformed`` / ``conflict``), and in a MOCK tree it must either claim no external
    evidence at all (``lab_eventlog.claims_external_evidence``: the mock anchor's receipt) or
    pass it.  A rejected line resolves nothing: its anchor stays pending and the existing
    timeout / recovery rules apply.  The raw line is never altered; ``raw_sha256`` and
    ``raw_bytes`` identify it in the spool."""
    raw_sha = sha256_bytes(raw)

    def out(kind: str, etype: str, body: dict, rid: str | None = None,
            anchor_seq: int | None = None) -> dict:
        return {'kind': kind, 'type': etype, 'body': body, 'request_id': rid,
                'anchor_seq': anchor_seq, 'raw_sha256': raw_sha}

    def reject(reason: str, rid: str | None = None) -> dict:
        return out('rejected', 'anchor_receipt_rejected',
                   {'request_id': rid, 'reason': reason, 'raw_sha256': raw_sha,
                    'raw_bytes': len(raw)}, rid)

    try:
        row = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError):
        return reject('malformed')
    if not isinstance(row, dict):
        return reject('malformed')
    rid = row.get('request_id')
    if not _is_hex(rid, 32):
        return reject('malformed')
    if not isinstance(row.get('ok'), bool):
        return reject('malformed', rid)
    request = request_of(rid)
    if request is None:
        return reject('unknown_request', rid)
    try:
        anchor_seq = int(request['anchor_seq'])
    except (KeyError, TypeError, ValueError):
        return reject('conflict', rid)
    anchor = anchors.get(anchor_seq)
    if (anchor is None or str(request.get('trial')) != str(trial)
            or str(request.get('request_id')) != rid
            or (anchor.get('request_id') is not None and anchor.get('request_id') != rid)
            or any(request.get(k) != anchor.get(k) for k in _ANCHOR_BINDING_KEYS)):
        return reject('conflict', rid)
    if anchor_seq in resolved:
        if resolving_sha.get(anchor_seq) == raw_sha:
            return reject('duplicate', rid)
        return reject('stale' if anchor_seq < int(newest_anchor_seq) else 'conflict', rid)
    if not row['ok']:
        error_class = row.get('error_class') or 'api'
        if error_class not in lab_eventlog.E_ANCHOR_ERROR.enum:
            return reject('malformed', rid)
        return out('failed', 'anchor_failed',
                   {'anchor_seq': anchor_seq, 'error_class': str(error_class),
                    'blocking': bool(request.get('blocking'))}, rid, anchor_seq)
    commit = row.get('commit')
    if (not _is_hex(row.get('receipt_sha256'), 64)
            or row.get('pushed') not in (True, False, None)
            or (commit is not None and not _is_hex(commit, 40))
            or (row.get('comment_id') is not None and not _is_int(row.get('comment_id')))):
        return reject('malformed', rid)
    body = {
        'anchor_seq': anchor_seq, 'pushed': row.get('pushed') is True,
        'comment_id': row.get('comment_id'), 'created_at': row.get('created_at'),
        'updated_at': row.get('updated_at'), 'receipt_sha256': row['receipt_sha256'],
        'commit_sha256': sha256_text(str(commit or '')), 'request_id': rid,
        'anchor_file_sha256': None, 'comment_body_sha256': None, 'node_id_sha256': None,
    }
    if request.get('trigger') == 'decision' and (
            not mock or lab_eventlog.claims_external_evidence(row)):
        verdict, digests = decision_evidence_verdict(row, request, trial,
                                                     anchor_branch=anchor_branch,
                                                     commit_check=commit_check)
        if verdict is not None:
            return reject(verdict, rid)
        body.update(digests)
    try:
        lab_eventlog.validate_event('anchor_receipt', body)
    except lab_common.SchemaError:
        return reject('malformed', rid)
    return out('receipt', 'anchor_receipt', body, rid, anchor_seq)


def certified_ell_from_spool(lines: Sequence[Mapping]) -> float:
    """[pure] ``ell`` from the spool, through ``lab_enclosure.certified_elapsed``.

    ``t_c1`` is the worker's monotonic stamp at entry into the first ``chat()`` call and
    ``t_e`` runs over every send and receive stamp (protocol 7.5 item 4).  No spooled
    request means ``0.0`` (6.4 row 18)."""
    t_c1: int | None = None
    for row in lines:
        if row.get('kind') == 'call_started':
            v = (row.get('body') or {}).get('t_c1_ns')
            if isinstance(v, int) and not isinstance(v, bool):
                t_c1 = v
                break
    if t_c1 is None:
        return 0.0
    stamps: list[tuple[int, int]] = []
    for row in lines:
        body = row.get('body') or {}
        for key in ('t_send_ns', 't_recv_ns'):
            v = body.get(key)
            if isinstance(v, int) and not isinstance(v, bool):
                stamps.append((t_c1, v))
    return lab_enclosure.certified_elapsed(stamps)


def tokens_known_from_spool(lines: Sequence[Mapping]) -> int:
    """[pure] Completion tokens the server actually reported; never imputed."""
    total = 0
    for row in lines:
        if row.get('kind') != 'call_response':
            continue
        v = ((row.get('body') or {}).get('usage') or {}).get('completion_tokens')
        if isinstance(v, int) and not isinstance(v, bool):
            total += v
    return total


def terminal_outcome(lines: Sequence[Mapping], error_class: str,
                     *, hard_cap_s: float | None = None) -> dict:
    """[pure] The outcome of an attempt that never returned (protocol 6.4 rows 10, 10b, 11,
    11c-11e, 18).

    ``success = 0``; ``latency_s`` is the hard cap for ``episode_timeout`` and the certified
    elapsed time otherwise; tokens are the known tokens, which is ``0`` when no request was
    ever spooled.  Every field is finite, which is what ``winstats.compare`` requires.

    This duplicates ``lab_worker.terminal_reveal`` because the isolation matrix (3.16)
    forbids the orchestrator to import ``lab_worker``; the duplication is reported to the
    coordinator rather than hidden."""
    ell = certified_ell_from_spool(lines)
    known = tokens_known_from_spool(lines)
    if error_class == 'episode_timeout':
        if hard_cap_s is None:
            raise SpoolError('episode_timeout needs the computed hard cap')
        latency = float(hard_cap_s)
    else:
        latency = float(ell)
    starts = [r for r in lines if r.get('kind') == 'call_started']
    n_calls = len({(r.get('body') or {}).get('call_index') for r in starts})
    prompt = 0
    for row in lines:
        if row.get('kind') == 'call_response':
            v = ((row.get('body') or {}).get('usage') or {}).get('prompt_tokens')
            if isinstance(v, int) and not isinstance(v, bool):
                prompt += v
    return {
        'success': 0,
        'latency_s': latency,
        'completion_tokens': known,
        'prompt_tokens': prompt,
        'n_llm_calls': n_calls,
        'n_failed_calls': sum(1 for r in lines if r.get('kind') == 'call_error'),
        'connection_retries': max(0, len(starts) - n_calls),
        'n_self_test_executions': sum(
            1 for r in lines if r.get('kind') == 'sandbox_exec'
            and (r.get('body') or {}).get('purpose') == 'self_test'),
        'n_verifier_executions': sum(
            1 for r in lines if r.get('kind') == 'sandbox_exec'
            and (r.get('body') or {}).get('purpose') == 'verify'),
        'repair_rounds': 0,
        'self_test_passed': None,
        'request_timeout_any': any(
            r.get('kind') == 'call_error'
            and (r.get('body') or {}).get('error_class') == 'timeout' for r in lines),
        'episode_timeout': error_class == 'episode_timeout',
        'verifier_timeout': False,
        'truncated_any': False,
        'sentinel_seen': False,
        'entry_point_defined': False,
        'error_class': error_class,
        'infra_flag': True,
    }


def canonical_job_payload(job: Mapping) -> dict:
    """[pure] The T4 identity projection of PG-14 / protocol 12.3, verbatim.

    Removes exactly ``arm``, ``arrival``, ``pair``, ``position``, ``task_uid``,
    ``worker_index``, ``paths``, ``assignment_seq``, ``payload_sha256`` and ``inv``.  What
    remains must be byte-identical for the two jobs of a T4 pair.

    ``inv`` joined the list in the pre-freeze repair of execution-review finding E3, for
    exactly the reason ``worker_index`` was already in it: the invocation id identifies the
    orchestrator run that dispatched the job, not the scientific configuration under which
    the episode ran.  Protocol 6.4 rows 11c-11e expressly allow the two episodes of one pair
    to be dispatched by different invocations after a pause or crash, so keeping ``inv``
    made ``t4.payload_identity`` -- a FAIL -- fire on a correctly resumed A/A pair whose
    configuration never changed.  Genuine configuration drift still fails, because every
    key that defines the configuration (``trial``, ``workflow``, ``server``, ``sampling``,
    ``limits``, ``sandbox``, ``golden``, ``config_sha256``, ``freeze_bundle_sha256``,
    ``max_repair_rounds``) remains in the payload.  Must stay identical to
    ``lab_worker.CANONICAL_JOB_DROP``."""
    drop = ('arm', 'arrival', 'inv', 'pair', 'position', 'task_uid', 'worker_index',
            'paths', 'assignment_seq', 'payload_sha256')
    return {k: v for k, v in dict(job).items() if k not in drop}


def episode_hard_cap_s(execution: Mapping) -> float:
    """[pure] ``4*(3*T + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s)
    + 60`` (protocol 5.6, PG-15).  Computed from the formula and the pinned
    ``request_timeout_s``; never a typed literal."""
    t = float(execution['request_timeout_s'])
    return (4.0 * (3.0 * t + float(execution['server_recovery_s']) + 6.0)
            + 3.0 * (float(execution['sandbox_timeout_s'])
                     + float(execution['max_lock_wait_s'])) + 60.0)


def unknown_usage_by_request(events: Sequence[Mapping]) -> dict[str, int]:
    """[pure] ``request_id -> arrival`` for every started request whose consumed tokens the
    chain does not know (execution review E1).

    A request is KNOWN only on a complete terminal receipt: an ``llm_response`` (which by
    protocol 5.4 cannot exist without ``usage``, because the client turns a 200 without
    ``usage``/``timings`` into a ``malformed`` error) or an ``llm_error`` that explicitly
    carries ``usage_known: true``.  Everything else is unknown, and that deliberately
    includes the case the earlier recount missed: a durable ``llm_request`` with **no**
    terminal event at all, which ``lab_verify_log`` expressly permits after ``worker_died``,
    ``episode_timeout`` or ``interrupted`` and which the terminal reconstruction reveals
    without minting an ``llm_error`` for the outstanding request.  Counting only
    ``llm_error`` turned those calls into "zero tokens consumed"; they are now counted as
    what they are, unknown.

    Keyed by ``request_id``, so a request can be counted at most once however many events
    mention it, and a retried try -- which spools its own ``call_started`` under a fresh
    ``request_id`` -- is one more genuinely unknown call rather than a double count."""
    started: dict[str, int] = {}
    known: set[str] = set()
    for ev in events:
        etype = ev['type']
        if etype not in ('llm_request', 'llm_response', 'llm_error'):
            continue
        body = ev['body']
        rid = str(body['request_id'])
        if etype == 'llm_request':
            started.setdefault(rid, int(body['arrival']))
        elif etype == 'llm_response':
            known.add(rid)
        else:
            # an error can only be a receipt for a request that started; setdefault keeps a
            # torn chain that lost the llm_request from silently dropping the call.
            started.setdefault(rid, int(body['arrival']))
            if body.get('usage_known', False):
                known.add(rid)
    return {rid: arrival for rid, arrival in started.items() if rid not in known}


# ---------------------------------------------------------------------------
# worker resolution (repair contract EB5; root 20:40 item 3, root 21:15 item 3:
# "Unresolved workers/usage make the phase incomplete, not zero")
# ---------------------------------------------------------------------------
class _WorkerUnknown:
    """The type of :data:`WORKER_UNKNOWN`: never an int, never None, never falsy-by-accident."""

    def __repr__(self) -> str:
        return 'WORKER_UNKNOWN'


#: :meth:`World.finished` of an attempt whose process this invocation does not hold (an
#: attempt rebuilt from the chain on resume): whether it still runs is NOT known from a poll.
#: It used to be ``0`` -- "exited" -- which let a resumed invocation reveal a live orphan as
#: ``interrupted`` (``git show b049307:experiments/live_ab/lab_orchestrator.py``
#: lines 1930-1934).  A caller must compare it by identity (``is WORKER_UNKNOWN``) before
#: reading a return code.
WORKER_UNKNOWN: Any = _WorkerUnknown()

#: The two ``worker_resolved.state`` values that RESOLVE a worker (``lab_eventlog``).
RESOLVED_WORKER_STATES: frozenset[str] = lab_eventlog.WORKER_RESOLVED_STATES
UNRESOLVED_WORKER_REASON: str = 'unresolved_worker'
#: How long a SIGKILL may take to be confirmed (a reaped child, or a pid found gone).
KILL_CONFIRM_S: float = 5.0


def usage_of_lines(lines: Sequence[Mapping]) -> tuple[bool, int]:
    """[pure] ``(usage_complete, unknown_usage_calls)`` of one attempt's spool lines: every
    started request id (``call_started``) without a ``call_response`` is a call whose
    consumed tokens are unknown -- a ``call_error`` (the client never knows the usage of a
    failed try, ``lab_client`` spools ``usage_known: False``) and a call with no terminal line
    at all alike.  Keyed by request id, so a line read twice counts once."""
    started: set[str] = set()
    known: set[str] = set()
    for row in lines:
        rid = (row.get('body') or {}).get('request_id')
        if rid is None:
            continue
        if row.get('kind') == 'call_started':
            started.add(str(rid))
        elif row.get('kind') == 'call_response':
            known.add(str(rid))
    unknown = len(started - known)
    return unknown == 0, unknown


def spool_name(arrival: int, attempt: int = 1) -> str:
    """The stem of an attempt's spool file (``ep_<arrival>_<attempt>``)."""
    return 'ep_%d_%d' % (int(arrival), int(attempt))


def spool_observation(path: str | Path, upto: int | None = None) -> dict:
    """The spool file as it is NOW: ``{'bytes', 'sha256', 'prefix_sha256'}`` -- its size, the
    digest of all of it, and the digest of its first ``upto`` bytes (``None`` when ``upto``
    is None or the file is shorter).  A missing file is 0 bytes (a worker that died before its
    first line); an unreadable one is ``bytes: None``."""
    p = Path(path)
    try:
        raw = p.read_bytes() if p.exists() else b''
    except OSError:
        return {'bytes': None, 'sha256': None, 'prefix_sha256': None}
    prefix = None
    if upto is not None and len(raw) >= int(upto):
        prefix = sha256_bytes(raw[:int(upto)])
    return {'bytes': len(raw), 'sha256': sha256_bytes(raw), 'prefix_sha256': prefix}


def last_worker_resolutions(events: Sequence[Mapping]) -> dict[tuple[int, int], dict]:
    """[pure] ``(arrival, attempt) -> body`` of the LAST ``worker_resolved`` of each attempt
    in ``events``."""
    out: dict[tuple[int, int], dict] = {}
    for ev in events:
        if ev['type'] == 'worker_resolved':
            body = ev['body']
            out[(int(body['arrival']), int(body['attempt']))] = dict(body)
    return out


def effective_worker_states(events: Sequence[Mapping]) -> dict[tuple[int, int], str]:
    """[pure] ``(arrival, attempt) -> state`` over EVERY ``worker_resolved`` of the attempt:
    the first state that does not resolve the worker if there is one (an attempt once
    recorded ``alive_unresolved`` / ``liveness_unknown`` stays unresolved whatever is recorded
    later -- root 21:14: "killing/reaping does not turn unknown historical usage into zero"),
    else the last state.  An attempt with no record is absent."""
    out: dict[tuple[int, int], str] = {}
    for ev in events:
        if ev['type'] != 'worker_resolved':
            continue
        key = (int(ev['body']['arrival']), int(ev['body']['attempt']))
        state = str(ev['body']['state'])
        if out.get(key) in RESOLVED_WORKER_STATES or key not in out:
            out[key] = state
    return out


def phase_resolution_verdict(events: Sequence[Mapping], spool_stats: Mapping,
                             server_obs: Mapping) -> dict:
    """[pure] Whether every permitted worker of a phase is resolved, taken BEFORE its terminal
    record (repair contract EB5; root 20:40 item 3: "A successful loaded phase must demonstrate
    all permitted workers resolved before its terminal acceptance").

    ``events``: the chain before the terminal record.  ``spool_stats``: spool stem ->
    :func:`spool_observation` taken at the seal, with ``prefix_sha256`` over the attempt's
    recorded ``spool_bytes_at_resolution``.  ``server_obs``: server id -> ``{'held',
    'observed', 'requests_processing', 'slots_busy'}`` taken after every client was resolved
    (:meth:`World.observe_servers_idle`).  In this harness every attempt is attempt 1
    (``max_attempts = 1``, PG-7), so ``episode_started`` names ``(arrival, 1)``.

    PASS only when all four hold; each failure adds its closed code
    (``lab_eventlog.RESOLUTION_PROBLEMS``):

    1. ``worker_unresolved`` -- some ``episode_started`` whose attempt has no
       ``worker_resolved``, or has one whose state is not ``exited`` / ``killed_reaped``
       (:func:`effective_worker_states`: a later resolution does not undo an unresolved one);
    2. ``call_unresolved`` -- some ``llm_request`` with no ``llm_response`` / ``llm_error``
       whose worker is not resolved.  A started call with no terminal event under a RESOLVED
       worker is not a failure: it is listed in ``unfinished_calls`` with usage ``null`` and
       counted as unknown usage, never as zero and never as unsent;
    3. ``spool_grew`` / ``spool_changed`` / ``spool_unreadable`` -- a resolved attempt's spool
       is now longer than its resolution offset, its first ``spool_bytes_at_resolution`` bytes
       no longer hash to ``spool_sha256_at_resolution`` (or it is shorter), or it could not
       be read;
    4. ``server_busy`` / ``server_unobserved`` -- a server this invocation still held was not
       idle (``requests_processing != 0`` or a busy slot) after the clients were resolved, or
       could not be observed.  A server not held (stopped before the close, or never
       started) runs no request.

    Returns the ``resolution`` object of the terminal record (``lab_eventlog.RESOLUTION``)
    with ``superseded_reason`` None (the caller sets it)."""
    events = list(events)
    started: dict[int, int] = {}
    for ev in events:
        if ev['type'] == 'episode_started':
            started.setdefault(int(ev['body']['arrival']), int(ev['seq']))
    last = last_worker_resolutions(events)
    effective = effective_worker_states(events)
    problems: set[str] = set()
    unresolved: list[dict] = []
    for arrival in sorted(started):
        state = effective.get((arrival, 1), 'no_record')
        if state not in RESOLVED_WORKER_STATES:
            unresolved.append({'arrival': arrival, 'attempt': 1, 'state': state})
            problems.add('worker_unresolved')
    terminals: set[str] = set()
    for ev in events:
        if ev['type'] in ('llm_response', 'llm_error'):
            terminals.add(str(ev['body']['request_id']))
    unfinished: list[dict] = []
    seen: set[str] = set()
    for ev in events:
        if ev['type'] != 'llm_request':
            continue
        body = ev['body']
        rid = str(body['request_id'])
        if rid in terminals or rid in seen:
            continue
        seen.add(rid)
        key = (int(body['arrival']), int(body['attempt']))
        state = effective.get(key, 'no_record')
        unfinished.append({'arrival': key[0], 'attempt': key[1], 'request_id': rid,
                           'worker_state': state, 'usage': None})
        if state not in RESOLVED_WORKER_STATES:
            problems.add('call_unresolved')
    late: list[dict] = []
    for key in sorted(last):
        rec = last[key]
        if effective.get(key) not in RESOLVED_WORKER_STATES:
            continue
        obs = dict(spool_stats.get(spool_name(*key)) or {})
        at = rec['spool_bytes_at_resolution']
        found = obs.get('bytes')
        if not isinstance(found, int) or isinstance(found, bool) or at is None:
            # unreadable now, or unread at its resolution (recorded null): never sealed
            problems.add('spool_unreadable')
            late.append({'arrival': key[0], 'attempt': key[1],
                         'bytes_at_resolution': None if at is None else int(at),
                         'bytes_found': None})
            continue
        at = int(at)
        if found > at:
            problems.add('spool_grew')
        if found < at or obs.get('prefix_sha256') != rec['spool_sha256_at_resolution']:
            problems.add('spool_changed')
        if found != at or obs.get('prefix_sha256') != rec['spool_sha256_at_resolution']:
            late.append({'arrival': key[0], 'attempt': key[1], 'bytes_at_resolution': at,
                         'bytes_found': int(found)})
    servers: list[dict] = []
    for sid in sorted(server_obs):
        obs = dict(server_obs[sid] or {})
        row = {'server_id': str(sid), 'held': bool(obs.get('held')),
               'observed': bool(obs.get('observed')),
               'requests_processing': obs.get('requests_processing'),
               'slots_busy': obs.get('slots_busy')}
        servers.append(row)
        if row['observed']:
            if row['requests_processing'] != 0 or row['slots_busy'] != 0:
                problems.add('server_busy')
        elif row['held']:
            problems.add('server_unobserved')
    return {'verdict': 'FAIL' if problems else 'PASS',
            'problems': [p for p in lab_eventlog.RESOLUTION_PROBLEMS if p in problems],
            'unresolved_attempts': unresolved, 'unfinished_calls': unfinished,
            'late_spools': late, 'servers': servers, 'superseded_reason': None}


def _ps_process(pid: int) -> tuple[str, str | None]:
    """``('gone' | 'row' | 'unknown', text)``: one ``ps -o lstart=,stat=,command= -p PID``.
    ps's exit 1 with no output is "no such process"; anything else it could not answer is
    unknown, never "gone"."""
    try:
        res = subprocess.run(['ps', '-o', 'lstart=,stat=,command=', '-p', str(int(pid))],
                             capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return 'unknown', None
    out = (res.stdout or '').strip()
    if res.returncode == 1 and not out:
        return 'gone', None
    if res.returncode != 0 or not out:
        return 'unknown', None
    return 'row', out


def probe_worker(pid: int, job_name: str, *, not_after_ns: int | None = None) -> str:
    """Whether the worker process an earlier invocation recorded is STILL that worker
    (repair contract EB5 item 3): ``'alive'``, ``'gone'`` or ``'unknown'``.

    Liveness is read from the pid AND the process's identity, never from the pid alone (a pid
    is reused): ``'alive'`` only when ``ps`` shows the pid running (not a zombie), its command
    line names this attempt's job file (``--job .../<job_name>``) and its start time
    (``lstart``, one-second resolution) is not after ``not_after_ns`` (+2 s; the
    ``episode_started`` dispatch stamp, which follows the spawn).  A pid that is not running,
    is a zombie (it has exited and waits for its parent), or is running something else, is
    ``'gone'``.  This process's own pid is ``'gone'`` (a simulated in-process worker).  A child
    of THIS process that has exited is reaped here.  ``'unknown'`` when ``ps`` could not
    answer.  Performs: at most one ``waitpid(WNOHANG)``, one signal-0 probe, one ``ps``."""
    pid = int(pid)
    if pid <= 0 or pid == os.getpid():
        return 'gone'
    try:
        got, _status = os.waitpid(pid, os.WNOHANG)
        if got == pid:
            return 'gone'
    except ChildProcessError:
        pass
    except OSError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return 'gone'
    except PermissionError:
        pass
    except OSError:
        return 'unknown'
    kind, text = _ps_process(pid)
    if kind != 'row':
        return kind
    parts = str(text).split(None, 6)
    if len(parts) < 7:
        return 'unknown'
    lstart, stat, command = ' '.join(parts[:5]), parts[5], parts[6]
    if 'Z' in stat:
        return 'gone'
    if str(job_name) not in command or '--job' not in command:
        return 'gone'
    if not_after_ns is not None:
        try:
            started = time.mktime(time.strptime(lstart, '%a %b %d %H:%M:%S %Y'))
        except (ValueError, OverflowError):
            return 'unknown'
        if started > float(not_after_ns) / 1e9 + 2.0:
            return 'gone'
    return 'alive'


def kill_orphan_worker(pid: int, job_name: str, *, not_after_ns: int | None = None,
                       wait_s: float = KILL_CONFIRM_S) -> tuple[str, int | None]:
    """Kill a live orphan worker (its own process group: ``lab_orchestrator`` spawns every
    worker with ``start_new_session``) and confirm it is gone: ``('killed_reaped', rc)`` or
    ``('alive_unresolved', None)``.  ``rc`` is known only when the orphan is a child of this
    process.  Never signals this process's own group."""
    pid = int(pid)
    try:
        pgid = os.getpgid(pid)
    except OSError:
        pgid = None
    try:
        if pgid is not None and pgid == pid and pgid != os.getpgrp():
            os.killpg(pgid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        return 'alive_unresolved', None
    deadline = time.monotonic() + float(wait_s)
    while True:
        try:
            got, status = os.waitpid(pid, os.WNOHANG)
            if got == pid:
                return 'killed_reaped', (os.waitstatus_to_exitcode(status)
                                         if hasattr(os, 'waitstatus_to_exitcode') else None)
        except ChildProcessError:
            pass
        except OSError:
            pass
        if probe_worker(pid, job_name, not_after_ns=not_after_ns) == 'gone':
            return 'killed_reaped', None
        if time.monotonic() >= deadline:
            return 'alive_unresolved', None
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# the program-wide seed registry (protocol 5.5; execution review E2)
# ---------------------------------------------------------------------------
#: The one file every worker of every trial reads before its first request.  It lives at the
#: PROGRAM work root, not under a trial, because protocol 5.5 promises "the used-seed set of
#: earlier trials of the program" and a per-trial file cannot carry one.
SEED_REGISTRY_NAME: str = 'used_seeds.json'


def seed_registry_path(work_root: str | Path) -> Path:
    """[pure] ``<work root>/used_seeds.json`` -- program-wide, above every trial."""
    return Path(work_root) / SEED_REGISTRY_NAME


def seeds_from_spool_lines(lines: Iterable[Mapping]) -> set[int]:
    """[pure] Every seed a worker durably committed to sending, from its spool lines.

    ``call_started`` is fsynced BEFORE the POST (protocol 5.5, and see
    ``lab_client.LlamaClient.chat``), so a spool is never behind the chain: a seed reaches
    the spool first and becomes ``llm_request`` only when the orchestrator next ingests.
    That ordering is what makes the registry crash-durable -- a seed sent by a worker the
    orchestrator never got to ingest is still recoverable from the spool it left behind."""
    out: set[int] = set()
    for row in lines:
        if row.get('kind') != 'call_started':
            continue
        body = row.get('body') or {}
        seed = body.get('seed')
        if isinstance(seed, int) and not isinstance(seed, bool):
            out.add(int(seed))
    return out


def seed_registry_reconstruct(work_root: str | Path) -> set[int]:
    """Every seed this PROGRAM has already committed to sending, rebuilt from the spools.

    Reads ``<work root>/*/spools/*.jsonl`` across every trial directory, plus whatever the
    registry file already holds.  The spools are the write-ahead record and are a superset
    of the chain's ``llm_request`` seeds, so this reconstruction survives a crash at any
    point: after an unclean exit the registry file may be stale, but no seed that was ever
    sent can be missing from the spool that recorded it before the POST.

    Malformed or partially written spool lines are skipped rather than raising: the registry
    exists to widen the exclusion set, and a torn last line has its own chain-level check.
    A seed that cannot be read is a seed that may be re-drawn, which protocol 5.5 grades a
    logged DEFECT, never a refusal -- but the reconstruction is run at every start and every
    resume precisely so that a re-draw stays the rare case rather than the normal one."""
    root = Path(work_root)
    seeds: set[int] = set()
    path = seed_registry_path(root)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            raw = []
        if isinstance(raw, list):
            seeds.update(int(v) for v in raw
                         if isinstance(v, int) and not isinstance(v, bool))
    if not root.exists():
        return seeds
    for spool in sorted(root.glob('*/spools/*.jsonl')):
        try:
            text = spool.read_text(encoding='utf-8')
        except OSError:
            continue
        rows: list[Mapping] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue                    # a torn tail line; the chain checks that
            if isinstance(row, dict):
                rows.append(row)
        seeds |= seeds_from_spool_lines(rows)
    return seeds


def write_seed_registry(path: str | Path, seeds: Iterable[int]) -> str:
    """Rewrite the registry durably and atomically; returns the sha256 of its bytes.

    A sorted JSON list of ints -- the exact shape ``lab_client.load_used_seeds`` reads, and
    the reason a test pins writer and reader against each other.  The registry GROWS across
    the program, so this is deliberately not ``write_json_atomic``, which is write-once and
    would refuse the second seed.  The write is still all-or-nothing: the bytes are fsynced
    into a temporary file, ``os.replace`` swaps it in, and the directory entry is fsynced,
    so a crash leaves either the previous complete registry or this one."""
    out = sorted({int(s) for s in seeds})
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json(out).encode('utf-8')
    tmp = p.with_name(p.name + '.tmp')
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        written = os.write(fd, data)
        if written != len(data):
            raise lab_common.TornWrite(
                '%d of %d bytes written to %s' % (written, len(data), tokenize_path(tmp)))
        lab_common.fullsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(p))
    lab_common._fullsync_dir(p.parent)
    return sha256_bytes(data)


def exposure_recount(events: Sequence[Mapping]) -> dict:
    """[pure] The exposure ledger, per phase x arm, recomputed from the chain alone.

    The verifier recounts it independently and compares byte for byte
    (``exposure.ledger``), so this function and the verifier's must agree exactly.

    ``prompt_tokens`` / ``completion_tokens`` are the tokens the chain can PROVE were
    consumed.  When ``unknown_usage_calls`` is non-zero the server consumed tokens that no
    receipt reports, so the two token totals are a LOWER BOUND and ``tokens_are_lower_bound``
    says so in the ledger itself: missing usage is never rewritten as zero.

    Repair contract EB5 (root 21:15 item 3;
    ``git show b049307:experiments/live_ab/lab_orchestrator.py`` lines 460-464): a call of an
    arrival that was never REVEALED -- the in-flight partner of a mid-pair abort, an attempt
    whose worker could not be resolved -- used to be dropped, because only a reveal gives it
    an arm and a phase (``if arm is not None and phase is not None``), so
    ``tokens_are_lower_bound`` could read False with a live partner's calls on the chain.
    Such calls now stay in the ledger, in the ``unrevealed`` cell: its ``episodes`` are the
    started arrivals with no reveal, its tokens the usage of their ``llm_response`` events and
    its ``unknown_usage_calls`` their calls without a usage receipt.  A response of a revealed
    arrival that the chain carries only AFTER its reveal (a late call of a worker still being
    resolved) is added to that arrival's cell.  ``totals`` is the whole trial: its token sums
    are ``null`` with ``null_reason: 'unknown_usage'`` whenever any call's usage is unknown --
    never a sum presented as complete (protocol 13.1, P:2535).  The verifier recounts every
    cell independently and compares byte for byte (``lab_verify_log._recount_exposure``)."""
    out: dict = {phase: {arm: {'episodes': 0, 'wall_seconds': 0.0, 'prompt_tokens': 0,
                               'completion_tokens': 0, 'unknown_usage_calls': 0,
                               'tokens_are_lower_bound': False}
                         for arm in lab_common.ARMS}
                 for phase in ('randomizing', 'post_decision')}
    unrevealed = {'episodes': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
                  'unknown_usage_calls': 0, 'tokens_are_lower_bound': False}
    arm_of: dict[int, str] = {}
    phase_of: dict[int, str] = {}
    started: set[int] = set()
    for ev in events:
        if ev['type'] == 'episode_started':
            started.add(int(ev['body']['arrival']))
        if ev['type'] != 'episode_revealed':
            continue
        body = ev['body']
        arrival = int(body['arrival'])
        arm = body['arm']
        phase = 'post_decision' if body.get('post_decision') else 'randomizing'
        arm_of[arrival] = arm
        phase_of[arrival] = phase
        row = out[phase][arm]
        row['episodes'] += 1
        row['wall_seconds'] += float(body['outcome']['latency_s'])
        row['prompt_tokens'] += int(body['outcome']['prompt_tokens'])
        row['completion_tokens'] += int(body['outcome']['completion_tokens'])
    for ev in events:
        if ev['type'] != 'llm_response':
            continue
        arrival = int(ev['body']['arrival'])
        prompt, completion = _usage_pair(ev['body'].get('usage'))
        if arrival not in arm_of:
            unrevealed['prompt_tokens'] += prompt
            unrevealed['completion_tokens'] += completion
    revealed_at: dict[int, int] = {}
    for ev in events:
        if ev['type'] == 'episode_revealed':
            revealed_at.setdefault(int(ev['body']['arrival']), int(ev['seq']))
        elif ev['type'] == 'llm_response':
            arrival = int(ev['body']['arrival'])
            if arrival in revealed_at and int(ev['seq']) > revealed_at[arrival]:
                prompt, completion = _usage_pair(ev['body'].get('usage'))
                row = out[phase_of[arrival]][arm_of[arrival]]
                row['prompt_tokens'] += prompt
                row['completion_tokens'] += completion
    for arrival in unknown_usage_by_request(events).values():
        arm = arm_of.get(arrival)
        phase = phase_of.get(arrival)
        if arm is not None and phase is not None:
            out[phase][arm]['unknown_usage_calls'] += 1
        else:
            unrevealed['unknown_usage_calls'] += 1
            started.add(int(arrival))
    unrevealed['episodes'] = len(started - set(arm_of))
    unrevealed['tokens_are_lower_bound'] = unrevealed['unknown_usage_calls'] > 0
    for phase in ('randomizing', 'post_decision'):
        for arm in out[phase]:
            out[phase][arm]['wall_seconds'] = round(out[phase][arm]['wall_seconds'], 6)
            out[phase][arm]['tokens_are_lower_bound'] = \
                out[phase][arm]['unknown_usage_calls'] > 0
    cells = [out[p][a] for p in ('randomizing', 'post_decision') for a in out[p]]
    cells.append(unrevealed)
    unknown = sum(int(c['unknown_usage_calls']) for c in cells)
    out['unrevealed'] = unrevealed
    out['totals'] = {
        'prompt_tokens': (None if unknown else sum(int(c['prompt_tokens']) for c in cells)),
        'completion_tokens': (None if unknown
                              else sum(int(c['completion_tokens']) for c in cells)),
        'unknown_usage_calls': unknown,
        'null_reason': 'unknown_usage' if unknown else None}
    return out


# ---------------------------------------------------------------------------
# usage reconciliation windows (protocol 13.1; repair contract EB1 item 3)
# ---------------------------------------------------------------------------
#: The five ``/metrics`` counters of a ``metrics_scrape`` / ``server_down.last_counters``.
COUNTER_KEYS: tuple[str, ...] = ('prompt_tokens_total', 'tokens_predicted_total',
                                 'n_decode_total', 'requests_processing', 'requests_deferred')

#: The scrape points at which the counters are EXACT: the server is idle and every response
#: it served is already a chain event (protocol 13.1, P:2538-2548: "exact reconciliation
#: exists only at quiescent points").  ``trial_start`` follows only the smoke, a
#: ``pair_boundary`` follows both reveals of a pair, ``quiescent`` follows the drain of the
#: follow-up cohort, ``trial_end`` follows the last reveal.  A ``restart`` scrape is taken
#: while recovering clients may already be sending to the new process (lab_client waits for
#: ``/health``, not for ``server_restarted``), so it closes no window.
QUIESCENT_SCRAPE_POINTS: frozenset[str] = frozenset({'trial_start', 'pair_boundary',
                                                     'quiescent', 'trial_end'})


def _usage_pair(usage: Mapping | None) -> tuple[int, int]:
    u = dict(usage or {})
    return int(u.get('prompt_tokens') or 0), int(u.get('completion_tokens') or 0)


def reconciliation_windows(events: Sequence[Mapping], server_ids: Iterable[str],
                           *, last_seq: int | None = None) -> list[dict]:
    """[pure] The ``usage_reconciliation`` bodies of one trial chain, one per server PROCESS.

    A server's counters start at 0 in every new process (ARCHITECTURE 8.3, A:2266-2269), so
    the chain is cut into windows at every ``server_started`` / ``server_restarted`` of that
    server; the first window starts at seq 0.  Each window's client usage is the SERVER_SMOKE
    usage of the body that opened it (protocol 5.3, P:921-922: the smoke "enters the
    reconciliation identity") plus the ``llm_response`` usage of that server inside the window.

    * A window a ``server_down`` of that server cut is ``counters_lost: true`` with a null
      residual and no defect: the tail between its last scrape and the crash died with the
      process (protocol 6.4 row 5, "counters lost across a crash reported as an unreconciled
      window").
    * Otherwise the window is reconciled at its LAST EXACT scrape: an ``ok`` scrape at a
      :data:`QUIESCENT_SCRAPE_POINTS` point at whose seq the chain shows NO open attempt on
      that server (an ``episode_started`` of the server with no ``episode_revealed`` of the
      same arrival before the scrape).  The point name alone is not proof of quiescence: a
      ``trial_end`` scrape follows a mid-pair abort with workers still running, and a
      response the server has counted but the chain has not yet ingested would be a
      spurious defect (EB1 fix, reviewer 1 finding 4).  ``counter_delta`` is that scrape's
      counters (the process started at 0), ``client_usage_sum`` the smoke plus the responses
      appended before the scrape, and any non-zero residual is a ``reconciliation_defect``.
      A window with no exact scrape is ``counters_lost: true`` (unreconciled, row 20), never
      a residual against a guessed counter; its ``counter_delta`` is the last counters read
      in it, or ``null`` / ``null`` when none was ever read (never 0).
    * ``window`` is ``'restart'`` when a supervised restart bounds it (it opened at a
      ``server_restarted`` or a ``server_down`` cut it) and ``'trial'`` otherwise.

    ``last_seq`` is the seq the last window runs to (default: the last event's)."""
    events = list(events)
    end = int(last_seq if last_seq is not None
              else (events[-1]['seq'] if events else 0))
    out: list[dict] = []
    for sid in sorted(set(str(s) for s in server_ids)):
        windows: list[dict] = []
        cur: dict = {'from': 0, 'opened_by': None, 'base': (0, 0), 'responses': [],
                     'point': None, 'cut': None, 'last_counters': None}
        open_on_server: set[int] = set()
        for ev in events:
            etype = ev['type']
            body = ev.get('body') or {}
            if etype == 'episode_revealed':
                open_on_server.discard(int(body.get('arrival', -1)))
                continue
            if body.get('server_id') != sid:
                continue
            if etype == 'episode_started':
                open_on_server.add(int(body.get('arrival', -1)))
                continue
            seq = int(ev['seq'])
            if etype in ('server_started', 'server_restarted'):
                base = _usage_pair((body.get('smoke') or {}).get('usage'))
                if cur['opened_by'] is not None or cur['responses'] or cur['cut'] is not None:
                    cur['to'] = seq - 1
                    windows.append(cur)
                    cur = {'from': seq, 'opened_by': etype, 'base': base, 'responses': [],
                           'point': None, 'cut': None, 'last_counters': None}
                else:
                    cur['opened_by'] = etype
                    cur['base'] = base
            elif etype == 'server_down':
                if cur['cut'] is None:
                    cur['cut'] = seq
            elif etype == 'llm_response':
                cur['responses'].append((seq,) + _usage_pair(body.get('usage')))
            elif etype == 'metrics_scrape' and body.get('ok'):
                counters = body.get('counters') or {}
                prompt = counters.get('prompt_tokens_total')
                predicted = counters.get('tokens_predicted_total')
                if not all(isinstance(v, int) and not isinstance(v, bool)
                           for v in (prompt, predicted)):
                    continue
                cur['last_counters'] = (int(prompt), int(predicted))
                if cur['cut'] is None and body.get('point') in QUIESCENT_SCRAPE_POINTS \
                        and not open_on_server:
                    cur['point'] = (seq, int(prompt), int(predicted))
        cur['to'] = end
        windows.append(cur)
        for w in windows:
            label = 'restart' if (w['opened_by'] == 'server_restarted'
                                  or w['cut'] is not None) else 'trial'
            if w['cut'] is not None or w['point'] is None:
                upto = w['cut'] if w['cut'] is not None else w['to']
                prompt = w['base'][0] + sum(r[1] for r in w['responses'] if r[0] <= upto)
                predicted = w['base'][1] + sum(r[2] for r in w['responses'] if r[0] <= upto)
                # the last counters read in the window, or null when none ever was: a
                # count never observed is unknown, never 0 (review of 988baf7, reviewer 1;
                # root 21:14, reconciliation carries unknown usage explicitly)
                known = w['last_counters']
                out.append({
                    'server_id': sid, 'window': label, 'window_from_seq': int(w['from']),
                    'window_to_seq': int(upto),
                    'counter_delta': ({'prompt': None, 'predicted': None} if known is None
                                      else {'prompt': int(known[0]),
                                            'predicted': int(known[1])}),
                    'client_usage_sum': {'prompt': int(prompt), 'predicted': int(predicted)},
                    'residual': {'prompt': None, 'predicted': None},
                    'reconciliation_defect': False, 'counters_lost': True})
                continue
            at, c_prompt, c_predicted = w['point']
            prompt = w['base'][0] + sum(r[1] for r in w['responses'] if r[0] < at)
            predicted = w['base'][1] + sum(r[2] for r in w['responses'] if r[0] < at)
            residual = {'prompt': c_prompt - prompt, 'predicted': c_predicted - predicted}
            out.append({
                'server_id': sid, 'window': label, 'window_from_seq': int(w['from']),
                'window_to_seq': int(at),
                'counter_delta': {'prompt': int(c_prompt), 'predicted': int(c_predicted)},
                'client_usage_sum': {'prompt': int(prompt), 'predicted': int(predicted)},
                'residual': residual,
                'reconciliation_defect': bool(residual['prompt'] or residual['predicted']),
                'counters_lost': False})
    return out


def client_usage_totals(events: Sequence[Mapping], server_ids: Iterable[str]) -> dict:
    """[pure] Per server, every client-observed usage the chain carries: the SERVER_SMOKE
    usage of each start and restart plus every ``llm_response`` (``trial_ended.
    reconciliation_totals``).  Unknown usage is not in it and is not zero: it is counted by
    ``unknown_usage_by_request``."""
    out: dict = {}
    for sid in sorted(set(str(s) for s in server_ids)):
        prompt = predicted = 0
        for ev in events:
            body = ev.get('body') or {}
            if body.get('server_id') != sid:
                continue
            if ev['type'] in ('server_started', 'server_restarted'):
                p, c = _usage_pair((body.get('smoke') or {}).get('usage'))
            elif ev['type'] == 'llm_response':
                p, c = _usage_pair(body.get('usage'))
            else:
                continue
            prompt += p
            predicted += c
        out[sid] = {'prompt': prompt, 'predicted': predicted}
    return out


# ---------------------------------------------------------------------------
# supervision state, rebuilt from the chain (repair contract EB1 items 2 and 4)
# ---------------------------------------------------------------------------
#: The ``server_start_failed.stage`` values of a server that never became healthy.  After a
#: supervised restart (or a resume start) they are ``trial_paused(server_unrecoverable)``
#: after the pair (protocol 14.6, P:2789); every other stage aborts by
#: :data:`START_FAILURE_REASON`.
NEVER_HEALTHY_STAGES: frozenset[str] = frozenset({'launch', 'health'})

RESTART_CAP_REASON: str = 'server_restart_cap'


@dataclass(frozen=True)
class SupervisionState:
    """What supervision must carry across an invocation boundary, read from the chain alone.

    ``restarts``: attempted supervised restarts per server (``server_restarted`` plus
    ``server_start_failed`` with ``kind='restart'``), the counter the cap bounds.
    ``props_sha256``: the tokenized ``/props`` digest of each server's last verified start,
    the ``previous_props_sha256`` of its next restart.  ``down_overlap``: every arrival that
    was in flight at a ``server_down`` (its reveal carries ``infra_flag``, P:1387-1388).
    ``unresolved_down``: server -> seq of a ``server_down`` that no restart, failed restart,
    pause or abort has followed yet.  ``pending_abort`` / ``pending_pause``: the outcome the
    chain owes and does not yet carry.  ``cap_required``: a ``server_down`` found its server
    already at the cap -- a restart beyond the cap would have been required."""
    restarts: dict
    props_sha256: dict
    down_overlap: frozenset
    unresolved_down: dict
    pending_abort: str | None
    pending_pause: str | None
    cap_required: bool


def supervision_state(events: Sequence[Mapping], cap: int | None) -> SupervisionState:
    """[pure] Replay the server lifecycle events of a chain into a :class:`SupervisionState`.

    The rules are the live ones of :meth:`World.supervise_down`, :meth:`World.start_servers`
    and :meth:`World.resume_servers`: a ``server_down`` of a server whose attempted restarts
    already reach ``cap`` owes ``trial_aborted(server_restart_cap)`` (and overrides any other
    pending outcome); a FIRST start's failure -- a ``kind='start'`` record before the chain's
    first ``invocation_started``, which only a resumed invocation writes -- owes
    ``trial_aborted(<START_FAILURE_REASON>)`` at every stage, exactly as
    :meth:`World.start_servers` ends it; a failed restart, or a failed start of a resumed
    invocation, owes ``trial_paused(server_unrecoverable)`` when it never became healthy and
    ``trial_aborted(<START_FAILURE_REASON>)`` otherwise; a ``server_restarted`` whose
    ``props_equal_previous`` is false owes ``trial_aborted(server_identity)``.  A
    ``trial_paused`` discharges a pending pause and every unresolved ``server_down``, never a
    pending abort; ``trial_aborted`` discharges everything.  ``cap`` None (a simulated run)
    never binds.

    The first-start rule is the EB1 fix of reviewer 1 finding 1: it used to replay a
    never-healthy FIRST start as a pause, so an orchestrator that died between the durable
    ``server_start_failed`` and ``trial_aborted(infrastructure)`` was resumed into a pause
    and then into the whole trial the live rules had aborted."""
    restarts: dict = {}
    props: dict = {}
    overlap: set = set()
    unresolved: dict = {}
    pending_abort: str | None = None
    pending_pause: str | None = None
    cap_required = False
    first_invocation = True
    for ev in events:
        etype = ev['type']
        body = ev.get('body') or {}
        sid = body.get('server_id')
        if etype == 'invocation_started':
            first_invocation = False
        elif etype in ('server_started', 'server_restarted'):
            props[sid] = body.get('props_sha256')
            unresolved.pop(sid, None)
            if etype == 'server_restarted':
                restarts[sid] = restarts.get(sid, 0) + 1
                if body.get('props_equal_previous') is False and pending_abort is None:
                    pending_abort = 'server_identity'
        elif etype == 'server_start_failed':
            if body.get('kind') == 'restart':
                restarts[sid] = restarts.get(sid, 0) + 1
            unresolved.pop(sid, None)
            stage = str(body.get('stage'))
            if body.get('kind') == 'start' and first_invocation:
                if pending_abort is None:
                    pending_abort = START_FAILURE_REASON.get(stage, 'infrastructure')
            elif stage in NEVER_HEALTHY_STAGES:
                pending_pause = pending_pause or 'server_unrecoverable'
            elif pending_abort is None:
                pending_abort = START_FAILURE_REASON.get(stage, 'infrastructure')
        elif etype == 'server_down':
            overlap.update(int(r['arrival']) for r in (body.get('inflight') or []))
            if cap is not None and restarts.get(sid, 0) >= int(cap):
                pending_abort = RESTART_CAP_REASON
                cap_required = True
            else:
                unresolved[sid] = int(ev['seq'])
        elif etype == 'trial_paused':
            pending_pause = None
            unresolved.clear()
        elif etype == 'trial_aborted':
            pending_abort = pending_pause = None
            unresolved.clear()
    return SupervisionState(restarts=restarts, props_sha256=props,
                            down_overlap=frozenset(overlap), unresolved_down=unresolved,
                            pending_abort=pending_abort, pending_pause=pending_pause,
                            cap_required=cap_required)


# ---------------------------------------------------------------------------
# the run context and the exclusive lock
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RunContext:
    trial: str
    inv: str
    cfg: dict
    bundle_sha: str
    paths: TrialPaths
    order: list
    tasks: dict
    mc: MonitorConfig
    servers: dict
    golden: dict
    #: THE serving-manifest artifact of this invocation's freeze tree,
    #: ``<results_root>/freeze/serving_manifest.json`` (``lab_serving_manifest.artifact_path``;
    #: root 01:53).  Its path only: preflight and every ``lab_server.start`` / ``restart``
    #: read and re-verify the file itself, so no copy taken earlier is ever compared.
    serving_manifest_path: Path | None = None


class RunLock:
    """Exclusive ``O_CREAT|O_EXCL`` lock holding ``{pid, inv, argv, t_wall_ns}``.

    A lock whose pid is dead is stale and is removed; a live pid raises ``PreflightError``
    (``test_two_orchestrators_refused``)."""

    def __init__(self, path: Path, inv: str) -> None:
        self.path = Path(path)
        self.inv = inv
        self.held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                if self._stale():
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                raise PreflightError(f'another orchestrator holds {self.path.name}')
            payload = canonical_json({'pid': os.getpid(), 'inv': self.inv,
                                      'argv': argv_tokens(sys.argv),
                                      't_wall_ns': time.time_ns()})
            os.write(fd, payload.encode('utf-8'))
            lab_common.fullsync(fd)
            os.close(fd)
            self.held = True
            return
        raise PreflightError(f'could not take {self.path.name}')

    def _stale(self) -> bool:
        try:
            held = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:                                   # noqa: BLE001
            return True
        pid = int(held.get('pid', -1))
        if pid <= 0:
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        return False

    def release(self) -> None:
        if self.held:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self.held = False


def tokenize_or_name(p: str) -> str | None:
    """The tokenized path when the string is one, else ``None``.

    Tracked artifacts carry no absolute path (ARCHITECTURE_FINAL.md 2.3), and the string
    discipline of PG-11 admits a `<TOKEN>/...` path and nothing else that looks like one,
    so an argument outside every known root is left out of ``argv_tokens`` and is covered
    by ``argv_sha256``, which hashes the whole line."""
    try:
        return tokenize_path(p)
    except Exception:                                       # noqa: BLE001
        return None


def argv_tokens(argv: Sequence[str]) -> list[str]:
    """[pure] The tokenizable elements of a command line, in order."""
    out: list[str] = []
    for item in argv:
        tok = tokenize_or_name(str(item))
        if tok is not None:
            out.append(tok)
    return out


# ---------------------------------------------------------------------------
# freeze-bundle members: what a run can recompute, and the refusal each one earns
# ---------------------------------------------------------------------------
#: Which closed ``E_PREFLIGHT`` reason code a drifting bundle member is refused under.  The
#: vocabulary is the event schema's and is NOT extended here; a member with no more specific
#: code is refused as ``preflight_rule_failed``.
MEMBER_REFUSAL: dict[str, str] = {
    'config_sha256': 'config_sha',
    'rule_block_sha256': 'config_sha',
    'roster_sha256': 'roster_sha',
    'task_content_sha256': 'roster_sha',
    'arrival_order_sha256': 'order_sha',
    'harness_file_sha256': 'harness_file_sha',
    'reused_file_sha256': 'harness_file_sha',
    'winstats_sha256': 'winstats_sha',
    'gguf_sha256': 'gguf_sha256',
    'serving_manifest_sha256': 'serving_manifest',
    'golden_props_sha256': 'golden_objects',
    'golden_generation_settings_sha256': 'golden_objects',
    'hardware_allowlist': 'hardware_allowlist',
}


# ---------------------------------------------------------------------------
# the golden objects: READ FROM THE FREEZE TREE (the serving manifest: lab_serving_manifest)
# ---------------------------------------------------------------------------
#: ARCHITECTURE_FINAL.md 2.2 (lines 190-191) deposits the golden objects of protocol 13.2
#: in the freeze tree as ``golden_props_<server>.json`` and
#: ``golden_generation_settings_<server>.json``.  Each file's identity is the canonical
#: digest of its OBJECT (the one digest convention of ``lab_common.freeze_bundle_sha256``),
#: which ``config.receipt.<member>.<server>`` records.
GOLDEN_FILES: dict[str, str] = {
    'golden_props_sha256': 'golden_props_%s.json',
    'golden_generation_settings_sha256': 'golden_generation_settings_%s.json',
}

def _read_json_object(path: Path) -> tuple[dict | None, str]:
    """``(object, digest)``: the canonical digest of a JSON object file, or ``(None,
    MEMBER_ABSENT)`` when it is missing, unreadable or not an object.  An unreadable file is
    never "agreeing" -- it is absent."""
    try:
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, lab_common.MEMBER_ABSENT
    if not isinstance(obj, dict):
        return None, lab_common.MEMBER_ABSENT
    try:
        return obj, sha256_canonical(obj)
    except (TypeError, ValueError):
        return None, lab_common.MEMBER_ABSENT


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 \
        and all(c in '0123456789abcdef' for c in value)


def load_golden_objects(freeze_dir: Path, cfg: Mapping,
                        server_ids: Iterable[str]) -> tuple[dict, list[dict]]:
    """Read the golden objects of ``server_ids`` from the freeze tree and compare each
    file's canonical digest with the one ``config.receipt`` records.

    Returns ``(golden, rows)``.  ``golden`` maps a server id to the plain object the worker
    and ``lab_server.start`` compare against -- ``{props, generation_settings, mask,
    float_tolerance}`` -- and holds a server ONLY when both of its files loaded and matched.
    ``rows`` are drift rows (``{'item', 'expected', 'found'}``, 64-hex both sides) for every
    digest that is null in the configuration, every file that is missing, unreadable or not
    an object, every digest mismatch, and every golden ``/props`` whose ``model_path`` is not
    tokenized (protocol 13.2, P:2586: the golden object carries the TOKENIZED path, so an
    absolute one could never equal an observation).  Empty rows mean every check passed."""
    receipt = dict((frozen_cfg(cfg).get('receipt') or {}))
    golden: dict = {}
    rows: list[dict] = []
    for sid in sorted(set(str(x) for x in server_ids)):
        loaded: dict = {}
        for member, pattern in GOLDEN_FILES.items():
            want = (receipt.get(member) or {}).get(sid) if isinstance(
                receipt.get(member), Mapping) else None
            obj, found = _read_json_object(Path(freeze_dir) / (pattern % sid))
            item = '%s.%s' % (member, sid)
            if not _hex64(want):
                rows.append({'item': item, 'expected': lab_common.MEMBER_ABSENT,
                             'found': found})
                continue
            if obj is None or found != want:
                rows.append({'item': item, 'expected': str(want), 'found': found})
                continue
            loaded[member] = obj
        props = loaded.get('golden_props_sha256')
        if props is not None and not str(props.get('model_path') or '').startswith('<'):
            rows.append({'item': 'golden_props_model_path.%s' % sid,
                         'expected': sha256_text('tokenized model_path'),
                         'found': sha256_text(str(props.get('model_path')))})
            props = None
        if props is not None and 'golden_generation_settings_sha256' in loaded:
            golden[sid] = {
                'props': props,
                'generation_settings': loaded['golden_generation_settings_sha256'],
                'mask': [str(m) for m in (receipt.get('mask') or ['seed'])],
                'float_tolerance': float(receipt.get('float_tolerance', 1e-6)),
            }
    return golden, rows


def observed_sandbox_profile_sha256() -> str | None:
    """The sha256 of the seatbelt profile THIS host would actually enforce, or None.

    Delegates to ``lab_data``, whose matrix row carries the ``(s)`` grant to reach the
    pilot's ``sandbox`` module through ``lab_common.add_import_paths()``.  This
    module's own row of ARCHITECTURE_FINAL.md 3.16 forbids the pilot outright, and
    ``tests_lab_isolation`` refuses a direct import here -- correctly: the fix for a
    forbidden import is to route through the module that owns the access, never to
    widen the row or to re-derive the profile text locally.  A local re-derivation
    would be a second implementation of the profile and could silently drift from the
    one the sandbox actually builds, which is the only thing worth observing.
    """
    return lab_data.observed_sandbox_profile_sha256()


def observed_bundle_members(freeze_dir: Path, *, trial: str | None = None,
                            bundle: Mapping | None = None,
                            harness_dir: Path | None = None,
                            src_dir: Path | None = None,
                            reused_dir: Path | None = None) -> dict:
    """Recompute every ``lab_common.BUNDLE_MEMBERS_RECOMPUTED`` member from the deposited
    freeze tree and the working copy.

    Reads files; compares nothing and raises nothing on a mismatch -- the comparison is
    ``lab_common.verify_bundle_members``.  A member whose source cannot be read is simply
    absent from the result, and the comparison then reports it as drift, so an artifact that
    the freeze names and that has gone missing refuses the run rather than passing it.

    ``bundle`` is read only to match the recorded SHAPE of ``arrival_order_sha256`` (a bundle
    may carry one digest for the running trial or a table over the four trials); no recorded
    VALUE is ever copied into the observation.  The three directory arguments exist so that a
    test can point the harness/core/reused lookups at a copy of the tree; a run leaves them
    unset and the real locations are used.
    """
    freeze_dir = Path(freeze_dir)
    src_dir = Path(src_dir) if src_dir is not None else lab_common.SRC_DIR
    reused_dir = Path(reused_dir) if reused_dir is not None else lab_common.LS_DIR
    recorded = dict(bundle or {})
    out: dict = {}

    # --- the frozen configuration and everything it pins --------------------
    cfg_path = freeze_dir / 'config.json'
    cfg: dict | None = None
    if cfg_path.exists():
        out['config_sha256'] = sha256_file(cfg_path)
        try:
            loaded = json.loads(cfg_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            loaded = None
        if isinstance(loaded, dict):
            cfg = frozen_cfg(loaded)
    if cfg is not None:
        try:
            out['rule_block_sha256'] = lab_common.rule_block_sha256(cfg)
        except lab_common.FrozenMismatch:
            pass
        if cfg.get('protocol_version') is not None:
            out['protocol_version'] = str(cfg['protocol_version'])
        gguf = {k: str((v or {}).get('sha256_expected'))
                for k, v in sorted((cfg.get('servers') or {}).items())
                if isinstance(v, Mapping) and v.get('sha256_expected') is not None}
        if gguf:
            out['gguf_sha256'] = gguf
        # The serving manifest and the four golden objects are HASHED FROM THEIR FILES in
        # the freeze tree (repair contract EB1 item 7).  This used to copy the configuration's
        # own digests into the observation, so the drift row compared the config with
        # itself: a golden file that was missing, unreadable or edited could never drift.
        # The manifest is read by lab_serving_manifest.read_artifact (a regular file whose
        # bytes are its canonical JSON); anything else is absent here.
        _, manifest_found, manifest_bad = lab_serving_manifest.read_artifact(
            lab_serving_manifest.artifact_path(freeze_dir.absolute()))
        if not manifest_bad and manifest_found:
            out['serving_manifest_sha256'] = manifest_found
        receipt = cfg.get('receipt') or {}
        server_names = {str(k) for k in (cfg.get('servers') or {})}
        for member, pattern in GOLDEN_FILES.items():
            names = set(server_names)
            if isinstance(recorded.get(member), Mapping):
                names |= {str(k) for k in recorded[member]}
            got = {}
            for sid in sorted(names):
                _, found = _read_json_object(freeze_dir / (pattern % sid))
                if found != lab_common.MEMBER_ABSENT:
                    got[sid] = found
            if got:
                out[member] = got
        if receipt.get('mask') is not None:
            out['receipt_mask_sha256'] = sha256_canonical(receipt['mask'])
        sandbox = cfg.get('sandbox') or {}
        # The profile digest is OBSERVED FROM THE SANDBOX, never copied from the frozen
        # config.  Copying it would make this member's drift row compare the config with
        # itself: it would read as "recomputed and compared" -- which is what
        # BUNDLE_MEMBERS_RECOMPUTED declares it to be -- while being incapable of
        # reporting any disagreement.  The profile text is derived from the owner home,
        # the base-interpreter prefix and the sandbox base under the AMBIENT TMPDIR, so
        # this observes the profile that would ACTUALLY be enforced.  That is the point:
        # `results/live_ab/SANDBOX_TMPDIR_RECONCILIATION.json` records a run that forgets
        # to export TMPDIR silently getting a different profile "with no error anywhere".
        # Observed here, that run drifts against the pin instead of passing.
        observed_profile = observed_sandbox_profile_sha256()
        if observed_profile is not None:
            out['sandbox_profile_sha256'] = observed_profile
        if sandbox.get('containment_probe_sha256') is not None:
            out['containment_probe_sha256'] = str(sandbox['containment_probe_sha256'])
        if cfg.get('environment_lock_sha256') is not None:
            out['environment_lock_sha256'] = str(cfg['environment_lock_sha256'])
        if cfg.get('hardware_allowlist') is not None:
            out['hardware_allowlist'] = [str(x) for x in cfg['hardware_allowlist']]

    # --- the roster, by its own rule, not by the digest it carries ----------
    roster_path = freeze_dir / 'roster.json'
    if roster_path.exists():
        try:
            roster = json.loads(roster_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            roster = None
        if isinstance(roster, dict):
            # lab_data.roster_sha256 RECOMPUTES the digest from the object, so a roster
            # whose content was rewritten together with its own `roster_sha256` field --
            # which `check_roster` accepts -- still fails against the bundle.
            out['roster_sha256'] = lab_data.roster_sha256(roster)
            if roster.get('task_content_sha256') is not None:
                out['task_content_sha256'] = str(roster['task_content_sha256'])

    # --- the arrival orders -------------------------------------------------
    order_member = recorded.get('arrival_order_sha256')
    if isinstance(order_member, str) and trial:
        path = freeze_dir / ('arrival_order_%s.json' % trial)
        if path.exists():
            out['arrival_order_sha256'] = sha256_file(path)
    else:
        names = set(k for k in (order_member or {}) if isinstance(order_member, Mapping))
        names |= {t for t in lab_common.TRIALS
                  if (freeze_dir / ('arrival_order_%s.json' % t)).exists()}
        orders = {t: sha256_file(freeze_dir / ('arrival_order_%s.json' % t))
                  for t in sorted(names)
                  if (freeze_dir / ('arrival_order_%s.json' % t)).exists()}
        if orders:
            out['arrival_order_sha256'] = orders

    # --- the code: the harness, the reused pilot modules, the pinned core ---
    if harness_dir is None:
        out['harness_file_sha256'] = lab_common.harness_file_hashes()
    else:
        hdir = Path(harness_dir)
        out['harness_file_sha256'] = {n: sha256_file(hdir / n)
                                      for n in lab_common.HARNESS_FILES
                                      if (hdir / n).exists()}
    reused = {n: sha256_file(reused_dir / n) for n in lab_common.REUSED_FILES
              if (reused_dir / n).exists()}
    if reused:
        out['reused_file_sha256'] = reused
    winstats = src_dir / 'winstats.py'
    if winstats.exists():
        out['winstats_sha256'] = sha256_file(winstats)
    return out


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
#: Protocol 7.5 item 4: the perf_counter/monotonic deltas are compared over a
#: TEN SECOND interval against clock_equivalence_tolerance_ms = 1.
CLOCK_WINDOW_PROTOCOL_S: float = 10.0


def _drift_label(text: str) -> str:
    """A drift ``item`` the event schema accepts (1-64 chars of ``[A-Za-z0-9_.+-]``)."""
    out = ''.join(c if (c.isalnum() and c.isascii()) or c in '_.+-' else '-' for c in text)
    return (out or 'item')[:64]


def _gguf_drift(server_id: str, spec: ServerSpec) -> dict | None:
    """The drift row of one server's weights file, or None when it is the frozen one.

    The path must be EXPLICIT and absolute (``--gguf <server>=<path>``; the bare file name
    of the servers block is not a path), the size must be the frozen byte count, and the
    recomputed SHA-256 the frozen digest.  The file is hashed once."""
    item = _drift_label('gguf.%s' % server_id)
    want = str(spec.gguf_sha256) if _hex64(spec.gguf_sha256) else lab_common.MEMBER_ABSENT
    path = Path(str(spec.gguf_path))
    if not path.is_absolute() or not path.is_file():
        return {'item': item, 'expected': want, 'found': lab_common.MEMBER_ABSENT}
    try:
        size = path.stat().st_size
        if size != int(spec.gguf_bytes):
            return {'item': item, 'expected': want,
                    'found': sha256_text('bytes:%d' % size)}
        found = sha256_file(path)
    except OSError:
        return {'item': item, 'expected': want, 'found': lab_common.MEMBER_ABSENT}
    if found != spec.gguf_sha256:
        return {'item': item, 'expected': want, 'found': found}
    return None


def simulated_path(rt: Mapping) -> bool:
    """Whether this invocation is SIMULATED: a harness installed a substitute world
    (``WORLD_FACTORY``) AND the runtime overlay says ``sim``.  Only then may the overlay
    replace the frozen golden objects (``make_context``, ``preflight``).  Either alone is
    not enough: the overlay can come from inside the configuration file, and a substitute
    world with ``sim`` unset supervises its servers live."""
    return WORLD_FACTORY is not None and bool(dict(rt).get('sim'))


def health_failures_to_down(cfg: Mapping) -> int:
    """[pure] ``execution.health_failures_to_down`` (protocol 5.3, P:917: "3 consecutive
    failures"), a positive int; raises ``ValueError`` otherwise.  No default."""
    value = (frozen_cfg(cfg).get('execution') or {}).get('health_failures_to_down')
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError('execution.health_failures_to_down is not a positive int')
    return int(value)


def supervision_config_problems(cfg: Mapping, *, sim: bool) -> list[tuple[str, str]]:
    """[pure] ``[(drift label, problem)]`` for the two frozen supervision inputs of a
    non-simulated run -- ``server_supervision`` read by ``lab_common.server_supervision_cap``
    and ``execution.health_failures_to_down`` -- and ``[]`` when both are well formed or
    ``sim`` is true."""
    if sim:
        return []
    out: list[tuple[str, str]] = []
    try:
        lab_common.server_supervision_cap(frozen_cfg(cfg))
    except lab_common.FrozenMismatch as exc:
        out.append(('server_supervision', str(exc)))
    try:
        health_failures_to_down(cfg)
    except ValueError as exc:
        out.append(('execution.health_failures_to_down', str(exc)))
    return out


def preflight(ctx: RunContext) -> dict:
    """Every refusal before seq 0 (ARCHITECTURE_FINAL.md 3.13, protocol 6.4 row 21).

    Returns the ``invocation_started.drift`` payload: a list of
    ``{'item', 'expected', 'found'}``, empty when nothing drifted.  A failure raises
    ``PreflightError`` carrying the closed reason codes; the caller writes
    ``preflight_refused`` to the **program** chain before a trial's seq 0 and
    ``invocation_refused`` in the trial chain at a later invocation of an open trial."""
    rt = runtime(ctx.cfg)
    cfg = frozen_cfg(ctx.cfg)
    # THE ACTUAL TRIAL ENTRY POINT, root 2026-09-22 02:49: "Injected-decision
    # tests 8 pass establish refusal on run_reference_sweep only. The trial entry
    # point also exists in lab_orchestrator; its preflight/run_trial path must
    # reject fixture activation BEFORE DISPATCH. Reachability must be checked
    # through that real path."  Raised here, before any drift accounting, so a
    # fixture-requesting configuration never reaches seq 0.
    lab_common.assert_no_fixture(ctx.cfg, stage='trial preflight')
    lab_common.assert_no_fixture(cfg, stage='trial preflight (frozen config)')
    failed: list[str] = []
    drift: list[dict] = []

    def _drift(item: str, expected: str, found: str) -> None:
        drift.append({'item': item, 'expected': expected, 'found': found})

    freeze_dir = Path(rt.get('freeze_dir') or (Path(rt['results_root']) / 'freeze'))
    # --- the frozen files ---------------------------------------------------
    cfg_path = freeze_dir / 'config.json'
    if cfg_path.exists():
        found = sha256_file(cfg_path)
        want = str(rt.get('config_sha256') or found)
        if found != want:
            failed.append('config_sha')
            _drift('config_sha256', want, found)
    else:
        failed.append('config_sha')
    for name, item in (('roster.json', 'roster_sha'),
                       (f'arrival_order_{ctx.trial}.json', 'order_sha')):
        p = freeze_dir / name
        if not p.exists():
            failed.append(item)
    bundle_path = freeze_dir / 'freeze_bundle.json'
    bundle: dict | None = None
    if bundle_path.exists():
        try:
            bundle = lab_common.load_freeze_bundle(bundle_path)
        except lab_common.FreezeIncomplete:
            bundle = None
            failed.append('freeze_bundle_drift')
        if bundle is not None:
            found = lab_common.freeze_bundle_sha256(bundle)
            if found != ctx.bundle_sha:
                failed.append('freeze_bundle_drift')
                _drift('freeze_bundle_sha256', ctx.bundle_sha, found)
    elif not rt.get('allow_missing_bundle'):
        failed.append('freeze_bundle_drift')

    # --- every MEMBER of the frozen bundle, against its recorded hash --------
    # The digest check above proves only that nobody edited the BUNDLE.  Provenance review
    # section 3: the root held an unchanged bundle carrying the original `config_sha256`,
    # changed `monitor.delta` from .03 to .04, and preflight returned `[]`.  Each member the
    # freeze names is therefore recomputed from the deposited tree and the working copy and
    # compared with the value the approved bundle records, with the bundle held FIXED.
    if bundle is not None:
        observed = observed_bundle_members(freeze_dir, trial=ctx.trial, bundle=bundle)
        for row in lab_common.verify_bundle_members(bundle, observed):
            failed.append(MEMBER_REFUSAL.get(str(row['item']).split('.', 1)[0],
                                             'preflight_rule_failed'))
            drift.append(dict(row))
        # The hardware identity is COMPARED here, not merely recorded at trial start.
        allowlist = bundle.get('hardware_allowlist')
        if isinstance(allowlist, list) and allowlist:
            identity = lab_common.hardware_identity()
            if identity not in [str(x) for x in allowlist]:
                failed.append('hardware_allowlist')
                _drift('hardware_identity',
                       sha256_canonical(sorted(str(x) for x in allowlist)),
                       sha256_text(identity))

    # --- the golden objects and the serving manifest (repair contract EB1 item 7) ---
    # Read from the FREEZE TREE and compared, file by file, with the digests the frozen
    # configuration records; null, missing, unreadable or different refuses before seq 0.
    # This runs on every path, simulated or not: a mock freeze tree deposits mock golden
    # files exactly as a real one deposits real ones.
    servers = dict(getattr(ctx, 'servers', None) or {})
    _, golden_rows = load_golden_objects(freeze_dir, cfg, servers)
    if golden_rows:
        failed.append('golden_objects')
        drift.extend(golden_rows)
    # --- the serving manifest (protocol 2.2 item 2; root 01:53) ---------------------
    # THE artifact is ``<results_root>/freeze/serving_manifest.json`` and nothing else:
    # a runtime or configuration key that would name another location, a context whose
    # path differs, a missing / symlinked / non-canonical file, a null configuration
    # digest or a different canonical digest refuses before seq 0 (lab_serving_manifest).
    # The runtime facts are re-verified against it below, on the real path.
    sm_path = lab_serving_manifest.artifact_path(
        Path(rt['results_root']).absolute() / 'freeze')
    want_manifest = (cfg.get('llama_cpp') or {}).get(lab_serving_manifest.CONFIG_DIGEST_KEY)
    sm_labels = list(lab_serving_manifest.override_problems(ctx.cfg, rt['results_root']))
    if getattr(ctx, 'serving_manifest_path', None) is not None \
            and Path(str(ctx.serving_manifest_path)) != sm_path:
        sm_labels.append('context_path')
    manifest, manifest_found, artifact_labels = lab_serving_manifest.verify_artifact(
        sm_path, want_manifest)
    if artifact_labels:
        drift.append({'item': 'serving_manifest_sha256',
                      'expected': (str(want_manifest) if _hex64(want_manifest)
                                   else lab_common.MEMBER_ABSENT),
                      'found': manifest_found or lab_common.MEMBER_ABSENT})
    for label in sm_labels + artifact_labels:
        failed.append('serving_manifest')
        _drift(_drift_label('serving_manifest.%s' % label),
               sha256_text('serving manifest re-verifies'), sha256_text(label))
    # --- supervision (repair contract EB1 items 1-2) ------------------------------------
    # Every invocation that starts a server supervises it, and supervision has two frozen
    # inputs: the restart cap (root 20:40 item 4, config.server_supervision) and the
    # consecutive-health-failure threshold (protocol 5.3, config.execution.
    # health_failures_to_down).  Absent or malformed, the run is refused here, before seq 0,
    # under the closed code ``preflight_rule_failed``: there is no default cap and no default
    # threshold.  A simulated invocation starts no server and supervises none.
    for label, problem in supervision_config_problems(cfg, sim=bool(rt.get('sim'))):
        failed.append('preflight_rule_failed')
        _drift(label, sha256_text('%s per repair contract EB1' % label), sha256_text(problem))
    # A path is SIMULATED only when a harness installed a substitute world AND the runtime
    # says ``sim``; the runtime overlay alone -- which ``main`` also accepts from inside the
    # configuration file -- cannot make it so.  On the real path a runtime ``sim`` (it would
    # skip the host gate and write the simulated server body) is refused.  A runtime
    # ``golden`` (it would replace the frozen objects every receipt is compared with) is
    # refused on EVERY path that is not simulated -- including a substitute world with
    # ``sim`` unset, whose servers are supervised live (EB1 fix, reviewer 1 finding 8:
    # the refusal used to key on the substitute world alone); ``make_context`` applies the
    # overlay under the same predicate, :func:`simulated_path`.
    if WORLD_FACTORY is None and rt.get('sim'):
        failed.append('preflight_rule_failed')
        _drift('runtime_sim_without_substitute_world',
               sha256_text('no runtime sim on the real path'),
               sha256_text('sim=%r' % (rt.get('sim'),)))
    # The close's server-idle bound is the frozen ``execution.request_timeout_s`` (repair
    # contract EB5 item 4).  A runtime ``resolution_idle_wait_s`` replaces it; it exists for
    # the model-free controls, whose trees are dry runs, and is refused on every tree that
    # is not one (review of 988baf7, reviewer 2: the comment said "controls only" and no
    # code enforced it).
    if rt.get('resolution_idle_wait_s') is not None \
            and not (cfg.get('mock') or cfg.get('mock_overrides')):
        failed.append('preflight_rule_failed')
        _drift('runtime_resolution_idle_wait_override',
               sha256_text('execution.request_timeout_s bounds the close idle wait'),
               sha256_text('resolution_idle_wait_s=%r' % (rt.get('resolution_idle_wait_s'),)))
    if 'golden' in rt and not simulated_path(rt):
        failed.append('golden_objects')
        try:
            found_override = sha256_canonical(rt['golden'])
        except (TypeError, ValueError):
            found_override = sha256_text(repr(type(rt['golden'])))
        _drift('runtime_golden_override', lab_common.MEMBER_ABSENT, found_override)
    if WORLD_FACTORY is None:
        # Each server's weights and the launcher, explicitly named, against the frozen
        # values: the GGUF bytes and recomputed SHA-256 of the servers block (protocol 2.3:
        # the cache blob name is not proof of its content) and every runtime fact of the
        # serving manifest -- launcher path and digest, the closure re-resolved from the
        # load commands, LC_RPATH, the embedded Metal library, the re-hashed build
        # provenance (lab_serving_manifest.runtime_problems says exactly what it performs).
        # ``lab_server.start`` repeats both at every start and restart; this is the
        # pre-seq-0 refusal of protocol 6.4 row 21, at EVERY invocation, resume included.
        for sid, spec in sorted(servers.items()):
            row = _gguf_drift(sid, spec)
            if row is not None:
                failed.append('weights_hash')
                drift.append(row)
            # Root 21:14 item 3 / the 21:15 EB1 corrections: the MEASURED digest must equal
            # the frozen servers entry, and that entry records two digests -- the declared
            # ``sha256_expected`` (what ``_gguf_drift`` measures against) and the freeze's own
            # ``sha256_recomputed``.  A freeze whose two disagree (or whose recomputation is
            # absent) cannot be matched by any file, so it is refused here too.  Performs: a
            # string comparison of the two frozen values; the file itself is hashed once,
            # above, and never taken from the configuration.
            recomputed = ((cfg.get('servers') or {}).get(sid) or {}).get('sha256_recomputed')
            if recomputed != spec.gguf_sha256:
                failed.append('weights_hash')
                _drift(_drift_label('gguf_recomputed.%s' % sid),
                       str(spec.gguf_sha256) if _hex64(spec.gguf_sha256)
                       else lab_common.MEMBER_ABSENT,
                       str(recomputed) if _hex64(recomputed) else lab_common.MEMBER_ABSENT)
            if manifest is not None:
                for label in lab_serving_manifest.runtime_problems(
                        manifest, launcher=spec.llama_bin, llama_commit=spec.llama_commit):
                    failed.append('serving_manifest')
                    _drift(_drift_label('serving_manifest.%s.%s' % (sid, label)),
                           sha256_text('serving manifest re-verifies'), sha256_text(label))
        # The golden /props carries the TOKENIZED ``-m`` path (protocol 13.2, P:2586) and a
        # llama-server reports its ``-m`` argument verbatim as ``model_path``, so the first
        # start can match the golden object only if ``tokenize_path(--gguf path)`` IS the
        # golden ``model_path``.  The same file under another spelling (a symlink, a
        # snapshot link versus its blob) passes the bytes and SHA-256 check above and would
        # fail the first start's identity stage AFTER seq 0 -- an irreversible
        # trial_aborted(server_identity).  Refused here instead, under ``golden_objects``
        # (the golden object does not match this invocation); EB1 fix, reviewer 1 finding 3.
        # Performs: one tokenize_path per server whose golden object loaded; compares
        # strings.  Does not resolve symlinks (the server does not either).
        for sid, spec in sorted(servers.items()):
            gold_path = str(((ctx.golden or {}).get(sid) or {}).get('props', {})
                            .get('model_path') or '')
            if not gold_path:
                continue                     # no golden object: refused above already
            try:
                ours = lab_common.tokenize_path(str(spec.gguf_path))
            except lab_common.UntokenizablePath:
                ours = ''
            if ours != gold_path:
                failed.append('golden_objects')
                _drift(_drift_label('golden_model_path.%s' % sid), sha256_text(gold_path),
                       sha256_text(ours or 'untokenizable'))
        # protocol 6.4 row 21 (``port_busy``): each server's frozen port must be free
        # before seq 0, except for the recorded servers of this trial that a resume stops
        # first (:func:`chain_orphan_server_pids`).  ``lab_server.start`` never takes
        # another process's answers as its child's (it requires the child to be the port's
        # only listener), so a busy port at the FIRST start would be an irreversible
        # trial_aborted(infrastructure) after seq 0; refused here instead.  An unreadable
        # listener table refuses too: "could not tell" is not "free".  EB1 fix, reviewers
        # 1 and 2 (foreign listener).
        ours_listening = chain_orphan_server_pids(ctx) if servers else set()
        for sid, spec in sorted(servers.items()):
            holders = lab_server.listening_pids(int(spec.port))
            if holders is None or (holders - ours_listening):
                failed.append('port_busy')
                _drift(_drift_label('port.%s' % sid), sha256_text('port %d free' % spec.port),
                       sha256_text('unreadable' if holders is None
                                   else 'held by %d process(es)'
                                   % len(holders - ours_listening)))

    # --- the independent reference rule (protocol 8.6) ----------------------
    # `lab_reference_rule.py` is also a harness file, so the member check above covers it;
    # this names it in its own right, because a reference rule that drifts from the value the
    # frozen configuration pins is the one defect that would let the verifier agree with a
    # decision code that had itself moved.
    want_ref = str((cfg.get('monitor') or {}).get('reference_rule_sha256') or '')
    ref_path = lab_common.HERE / 'lab_reference_rule.py'
    if want_ref and ref_path.exists():
        found_ref = sha256_file(ref_path)
        if found_ref != want_ref:
            failed.append('harness_file_sha')
            _drift('reference_rule_sha256', want_ref, found_ref)

    # --- winstats, the pinned read-only core --------------------------------
    wpath = lab_common.SRC_DIR / 'winstats.py'
    want_w = str(cfg.get('monitor', {}).get('winstats_sha256') or '')
    if wpath.exists() and want_w:
        found_w = sha256_file(wpath)
        if found_w != want_w:
            failed.append('winstats_sha')
            _drift('winstats_sha256', want_w, found_w)

    # --- the environment ----------------------------------------------------
    for var in sorted(os.environ):
        if var.startswith(('ANTHROPIC', 'OPENAI')) and var.endswith(('KEY', 'TOKEN')):
            failed.append('api_key_env')
            break
    floor_gb = float(rt.get('free_disk_floor_gb', 20.0))
    try:
        usage = os.statvfs(str(lab_common.REPO_ROOT))
        free_gb = usage.f_bavail * usage.f_frsize / 1e9
    except OSError:
        free_gb = floor_gb
    if free_gb < floor_gb:
        failed.append('disk_low')

    # --- clock equivalence (protocol 7.5 item 4) ----------------------------
    # THE WINDOW IS THE PROTOCOL'S, root 2026-09-22 04:02: "The reviewer found a
    # protocol 10-second check but an orchestrator default of 0.05 seconds. Make
    # the actual frozen invocation use the protocol's 10-second window and record
    # that effective value."
    #
    # WHY THE DEFAULT MATTERED. The tolerance is 1 ms. A RELATIVE rate difference
    # between the two clocks that would accumulate to more than 1 ms over the
    # protocol's 10 s shows up as 0.005 ms over 50 ms, so the check as invoked
    # was about 200x less sensitive than the one 7.5 item 4 specifies -- it would
    # have passed clocks the protocol intends to refuse, and passed them quietly.
    #
    # A shorter window remains settable for offline tests, which cannot sleep
    # 10 s per preflight, but it is now RECORDED as an effective value and
    # flagged as below protocol, so no receipt can show a weakened check without
    # saying so.
    # PRODUCTION REFUSES A SHORT WINDOW. Root, 2026-09-22 06:16: "require a
    # finite window of at least ten seconds both when validating the prospective
    # freeze and at every actual production preflight ... The runtime
    # short-window override currently remains allowed and flagged; LOGGING A
    # WEAKENED CHECK DOES NOT ENFORCE THE PROTOCOL. Keep explicitly
    # shortened/labeled offline fixtures separate from production, and ensure
    # they cannot supply a production preflight receipt."
    #
    # PRODUCTION IS THE DEFAULT. An offline fixture must declare itself, so a
    # runtime that simply forgot to say what it is gets the strict path. The
    # previous cycle recorded the effective window and let it through; recording
    # a weakened check is not enforcing one.
    #
    # The refusal reuses the EXISTING closed reason code `clock_equivalence`
    # rather than widening E_PREFLIGHT, which is a G1 closed vocabulary: the
    # failure IS a clock-equivalence preflight failure -- the check could not be
    # performed at protocol sensitivity -- and the drift row carries the detail.
    tol_ms = float(cfg.get('enclosure', {}).get('clock_equivalence_tolerance_ms', 1))
    window_s = float(rt.get('clock_window_s', CLOCK_WINDOW_PROTOCOL_S))
    preflight_mode = str(rt.get('preflight_mode', 'production'))
    p0, m0 = time.perf_counter(), time.monotonic()
    time.sleep(window_s)
    dp, dm = time.perf_counter() - p0, time.monotonic() - m0
    clock_equivalence = {
        'window_s_effective': window_s,
        'window_s_protocol': CLOCK_WINDOW_PROTOCOL_S,
        'below_protocol_window': window_s < CLOCK_WINDOW_PROTOCOL_S,
        'tolerance_ms': tol_ms,
        'perf_counter_delta_s': dp,
        'monotonic_delta_s': dm,
        'difference_ms': abs(dp - dm) * 1000.0,
        'sensitivity_note': ('a relative rate difference is measured over the '
                             'window, so a window below %g s detects proportionally '
                             'less of it at the same tolerance'
                             % CLOCK_WINDOW_PROTOCOL_S),
    }
    clock_equivalence['preflight_mode'] = preflight_mode
    # A receipt from a shortened window is NOT a production preflight receipt,
    # and says so in the field a consumer would read.
    clock_equivalence['production_receipt'] = (
        preflight_mode == 'production'
        and not clock_equivalence['below_protocol_window'])
    # WRITTEN WHERE A CONSUMER CAN READ IT. `runtime(cfg)` returns a COPY, so
    # the previous cycle's `rt['clock_equivalence'] = ...` wrote into a throwaway
    # dict and vanished the moment preflight returned. I reported that value as
    # "recorded" and it was recorded nowhere: the field existed for the length of
    # one function call. Root asked for the effective metadata retained "through
    # its ordinary receipt path", and the runtime block on the context IS that
    # path -- it is what make_context builds and what the caller reads afterwards.
    rt['clock_equivalence'] = clock_equivalence
    try:
        ctx.cfg.setdefault('_runtime', {})['clock_equivalence'] = clock_equivalence
    except (AttributeError, TypeError):                       # pragma: no cover
        pass
    if preflight_mode == 'production' and clock_equivalence['below_protocol_window']:
        failed.append('clock_equivalence')
        _drift('clock_window_s', '>= %g (protocol 7.5 item 4)'
               % CLOCK_WINDOW_PROTOCOL_S,
               '%g in preflight_mode=production' % window_s)
    if abs(dp - dm) * 1000.0 > tol_ms:
        failed.append('clock_equivalence')
        _drift('clock_equivalence_ms', '<= %g' % tol_ms,
               '%.6f over %g s' % (clock_equivalence['difference_ms'], window_s))

    # --- the worktree (protocol 2.1 guard 1) --------------------------------
    expected_tree = rt.get('worktree')
    if expected_tree:
        observed = git_identity()
        for key in ('branch', 'commit'):
            want_v = expected_tree.get(key)
            if want_v and observed.get(key) != want_v:
                failed.append('worktree_identity')
                _drift(f'worktree_{key}', sha256_text(str(want_v)),
                       sha256_text(str(observed.get(key))))

    if failed:
        # The refusal carries its own evidence.  `preflight_refused` has always had a
        # `drift` field and the caller had nothing to put in it, so a refusal named a
        # reason code and never said WHICH artifact moved; the member rows above are
        # exactly that missing evidence.
        error = PreflightError(','.join(sorted(set(failed))))
        error.drift = drift
        raise error
    return drift


# ---------------------------------------------------------------------------
# host quiescence (protocol 5.7, lab_hostcheck)
# ---------------------------------------------------------------------------
def host_scan_is_required(cfg: Mapping) -> bool:
    """[pure] Whether this invocation must hold the host to protocol 5.7.

    A simulated invocation starts no server and makes no model call, so there is no
    latency measurement for a foreign accelerator load to corrupt and nothing to protect.
    Every other invocation is gated, and there is deliberately NO key that turns the gate
    off for a real one: the whole point of 5.7 is that the primary endpoint rides on the
    latency tier, and a gate an operator can switch off is a gate that will be off."""
    return not runtime(cfg).get('sim')


def own_harness_pids(world: 'World | None' = None) -> set[int]:
    """This orchestrator, plus the servers and workers it started.

    Descendants are added by the scan itself, so a server started through a shell is
    covered by the shell's pid alone."""
    pids = {os.getpid()}
    if world is not None:
        pids |= {int(p) for p in world.server_pids.values() if p}
        pids |= {int(a.pid) for a in world.attempts.values() if getattr(a, 'pid', 0)}
    return pids


def chain_orphan_server_pids(ctx: RunContext) -> set[int]:
    """The server pids an EARLIER invocation of this trial started and never recorded as
    stopped (:func:`chain_server_pids`) that are STILL that server --
    ``lab_server.orphan_server`` True: alive and listening on the frozen port of the server
    the chain names.  These are what a resume stops first (:meth:`World.stop_chain_orphans`),
    so before the chain is opened they are this harness's own processes, not foreign ones.

    Read-only: the chain is read and verified with ``lab_eventlog.read_chain`` (no lock is
    held yet, nothing is appended); a chain that is absent or does not verify yields the
    empty set, so the gate then fails closed on such a process.  A pid that is dead, that
    no longer listens on its port (the OS reused it), or whose listener table could not be
    read is NOT in the set.  EB1 fix, reviewer 1 finding 2: the gate used to allowlist only
    the new orchestrator's pid, so a surviving llama-server of a killed invocation refused
    every resume as a foreign accelerator consumer before the orphan stop could run."""
    events_dir = ctx.paths.events
    if not lab_eventlog.segment_paths(events_dir):
        return set()
    try:
        events = lab_eventlog.read_chain(events_dir, ctx.trial, ctx.bundle_sha).events
    except (ChainError, lab_common.SchemaError, OSError, ValueError):
        return set()
    out: set[int] = set()
    for server_id, pid in chain_server_pids(events):
        spec = (getattr(ctx, 'servers', None) or {}).get(server_id)
        if spec is not None and lab_server.orphan_server(pid, int(spec.port)) is True:
            out.add(int(pid))
    return out


def host_quiescence_gate(ctx: RunContext) -> lab_hostcheck.ScanResult | None:
    """The HARD gate of protocol 5.7, run before a trial may open its chain.

    Returns the clean scan, returns None when this invocation is not gated, and otherwise
    raises ``lab_hostcheck.HostNotQuiescent`` -- which is a ``PreflightError`` -- naming
    the offenders.  It refuses on an unproven host as well as on a dirty one.

    Allowlisted: this orchestrator (:func:`own_harness_pids`) and, on a resume, the
    recorded servers of this trial that are still that server
    (:func:`chain_orphan_server_pids`), which the resume stops before it starts anything.
    Nothing else: an unrecorded llama-server, or a recorded pid that is no longer listening
    on its frozen port, is still a foreign consumer.  The run lock is taken AFTER this gate,
    so if another invocation of the same trial is alive, the lock refuses the run before
    anything is stopped."""
    if not host_scan_is_required(ctx.cfg):
        return None
    return lab_hostcheck.preflight_host_quiescent(
        own_harness_pids() | chain_orphan_server_pids(ctx))


def write_host_quiescence_refused(ctx: RunContext,
                                  exc: lab_hostcheck.HostNotQuiescent) -> None:
    """Name the offenders in the PROGRAM chain, beside the ``preflight_refused`` that
    carries the closed reason code.  Before a trial's seq 0 there is no trial chain to
    write to, exactly as for every other refusal (critic N1)."""
    rt = runtime(ctx.cfg)
    events_dir = Path(rt['results_root']) / lab_common.PROGRAM_CHAIN_ID / 'events'
    scan = lab_hostcheck.ScanResult(findings=list(exc.findings),
                                    degraded=list(exc.degraded))
    body = dict(lab_hostcheck.chain_body(scan), trial=ctx.trial, point='trial_start')
    try:
        log = EventLog(events_dir, lab_common.PROGRAM_CHAIN_ID, ctx.bundle_sha, ctx.inv,
                       create=not lab_eventlog.segment_paths(events_dir))
    except ChainError:
        return
    try:
        log.append('host_quiescence_refused', body, durable=True)
    except lab_common.SchemaError:
        # A record we cannot write in the schema's vocabulary must not take the refusal
        # down with it: the refusal itself is already carried by preflight_refused.
        pass
    finally:
        log.close()


def git_identity(repo: Path | None = None) -> dict:
    """The worktree's real path, ``HEAD`` branch and ``HEAD`` commit (read-only git)."""
    root = Path(repo) if repo is not None else lab_common.REPO_ROOT
    out: dict = {'path': str(root.resolve()), 'branch': None, 'commit': None}
    for key, args in (('branch', ['rev-parse', '--abbrev-ref', 'HEAD']),
                      ('commit', ['rev-parse', 'HEAD'])):
        try:
            res = subprocess.run(['git', '-C', str(root)] + args, capture_output=True,
                                 text=True, timeout=20, check=False)
            if res.returncode == 0:
                out[key] = res.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return out


# ---------------------------------------------------------------------------
# resume, as a pure function (ARCHITECTURE_FINAL.md 3.13, protocol 14.5)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResumePlan:
    phase: Literal['randomizing', 'post_decision', 'ended', 'aborted']
    next_pair: int | None
    reenroll_pair: int | None
    bound_assignments: dict
    orphan_reveals: list
    orphan_rejections: list
    interrupted: list
    dispatch_after_resume: list
    decision_seq: int | None
    pending_decision_steps: list
    monitor_prefix: int
    findings: list


def plan_resume(events: Sequence[Mapping], spools: Mapping, order: Sequence,
                cfg: Mapping) -> ResumePlan:
    """[pure] No I/O, no clock, no process inspection.

    ``events`` is the verified chain; ``spools`` maps ``'ep_<arrival>_<attempt>'`` to the
    parsed spool lines (complete lines only).  The ten rules of ARCHITECTURE_FINAL.md 3.13
    in order:

      1. every chain-valid ``coin_drawn`` / ``arm_assigned_by_decision`` binds -- never a
         redraw (protocol 4.2 invariant v);
      2. a ``pair_enrolled`` with no coin is re-enrolled (``re_enrolled: true``) and then
         receives its one coin;
      3. assignment + ``episode_revealed`` -> nothing to do, ever;
      4. assignment + a spool whose ``episode_final`` passes every orphan check ->
         ``orphan_reveals`` (``recovered_orphan: true``);
      5. assignment + a spool that fails one -> ``orphan_rejections`` + ``interrupted``;
      6. assignment + ``job_accepted`` and no usable terminal line -> ``interrupted``;
      7. assignment + no ``job_accepted`` at all -> ``dispatch_after_resume`` (PG-7: nothing
         had run, so dispatching it now is not a re-run);
      8. orphan reveals are emitted first, in arrival order;
      9. a ``decision`` closes randomization for ever and lists the missing decision steps;
     10. ``monitor_prefix`` is the enrolled prefix.
    """
    events = list(events)
    revealed: set[int] = set()
    coins: dict[int, int] = {}                 # pair -> seq of its coin
    assignments: dict[int, str] = {}           # arrival -> arm
    assign_seq: dict[int, int] = {}
    enrolled: dict[int, dict] = {}             # pair -> body
    decision_seq: int | None = None
    have_switch = False
    have_decision_anchor = False
    have_decision_receipt = False
    status: str | None = None
    findings: list[str] = []
    started_pairs: list[int] = []

    for ev in events:
        etype = ev.get('type')
        body = ev.get('body') or {}
        if etype == 'pair_enrolled':
            pair = int(body['pair'])
            if pair not in enrolled:
                enrolled[pair] = dict(body)
                started_pairs.append(pair)
        elif etype == 'coin_drawn':
            pair = int(body['pair'])
            coins.setdefault(pair, int(ev['seq']))
            for arrival_s, arm in (body.get('assignment') or {}).items():
                arrival = int(arrival_s)
                assignments[arrival] = str(arm)
                assign_seq.setdefault(arrival, int(ev['seq']))
        elif etype == 'arm_assigned_by_decision':
            arrival = int(body['arrival'])
            assignments[arrival] = str(body['arm'])
            assign_seq.setdefault(arrival, int(ev['seq']))
        elif etype == 'episode_revealed':
            revealed.add(int(body['arrival']))
        elif etype == 'decision':
            decision_seq = int(ev['seq'])
        elif etype == 'traffic_switch':
            have_switch = True
        elif etype == 'anchor' and decision_seq is not None:
            have_decision_anchor = True
        elif etype == 'anchor_receipt' and decision_seq is not None \
                and int(ev['seq']) > decision_seq:
            have_decision_receipt = True
        elif etype in ('trial_ended', 'trial_aborted'):
            status = 'ended' if etype == 'trial_ended' else 'aborted'

    orphan_reveals: list[dict] = []
    orphan_rejections: list[dict] = []
    interrupted: list[int] = []
    dispatch_after_resume: list[int] = []

    for arrival in sorted(assignments):
        if arrival in revealed:
            continue                                        # rule 3
        key = f'ep_{arrival}_1'
        lines = list(spools.get(key) or [])
        accepted = [r for r in lines if r.get('kind') == 'job_accepted']
        if not accepted:
            dispatch_after_resume.append(arrival)            # rule 7 / PG-7
            continue
        finals = [r for r in lines if r.get('kind') == 'episode_final']
        if not finals:
            interrupted.append(arrival)                      # rule 6
            continue
        failure = _orphan_check(lines, finals[-1])
        if failure is None:
            orphan_reveals.append({'arrival': arrival, 'final': finals[-1],
                                   'lines': lines})          # rule 4
        else:
            orphan_rejections.append({'arrival': arrival, 'attempt': 1,
                                      'check_failed': failure,
                                      'record_sha256': (finals[-1].get('body') or {}
                                                        ).get('record_sha256'),
                                      'spool_sha256': sha256_canonical(
                                          [dict(r, _offset=None) for r in lines])})
            interrupted.append(arrival)                      # rule 5

    orphan_reveals.sort(key=lambda row: row['arrival'])       # rule 8
    interrupted.sort()
    dispatch_after_resume.sort()

    reenroll_pair = None
    for pair in sorted(enrolled):
        if pair not in coins:
            reenroll_pair = pair                              # rule 2
            findings.append('pair_enrolled_without_coin')
            break

    monitor_prefix = len(coins)                               # rule 10
    if monitor_prefix != len(enrolled):
        # COORDINATOR_DECISIONS ruling 17 (revision 4) settled the three-way disagreement
        # that used to be recorded here: n grows at `coin_drawn` and never at
        # `pair_enrolled`, because a pair whose coin has not been drawn and fsynced is not
        # randomized and holds no position in the monitor.  Counting coins is therefore the
        # RULE, not a conservative choice between readings, and protocol 8.3 trigger 1 was
        # corrected in place to say so.  The gap is still reported, because it means this
        # resume found a staged pair that must be re-enrolled before it is randomized.
        findings.append('staged_pair_without_coin_excluded_from_prefix')

    if status is not None:
        phase = status
    elif decision_seq is not None:
        phase = 'post_decision'
    else:
        phase = 'randomizing'

    pending: list[str] = []
    if decision_seq is not None:
        if not have_decision_anchor:
            pending.append('anchor')
        if not have_decision_receipt:
            pending.append('receipt')
        if not have_switch:
            pending.append('traffic_switch')

    next_pair: int | None = None
    if phase == 'randomizing':
        done = max(coins) if coins else 0
        if reenroll_pair is not None:
            next_pair = reenroll_pair
        elif done < len(order):
            next_pair = done + 1
    return ResumePlan(phase=phase, next_pair=next_pair, reenroll_pair=reenroll_pair,
                      bound_assignments=dict(assignments), orphan_reveals=orphan_reveals,
                      orphan_rejections=orphan_rejections, interrupted=interrupted,
                      dispatch_after_resume=dispatch_after_resume,
                      decision_seq=decision_seq, pending_decision_steps=pending,
                      monitor_prefix=monitor_prefix, findings=findings)


def _orphan_check(lines: Sequence[Mapping], final: Mapping) -> str | None:
    """[pure] The orphan checks of protocol 14.5 item 3 / ARCHITECTURE 5.

    Returns ``None`` when the spool may be revealed from, else the check id that failed."""
    body = final.get('body') or {}
    if not body.get('record_sha256'):
        return 'record_missing'
    outcome = body.get('outcome')
    if not isinstance(outcome, dict) or 'success' not in outcome:
        return 'outcome_mismatch'
    accepted = next((r for r in lines if r.get('kind') == 'job_accepted'), None)
    if accepted is None:
        return 'pid_mismatch'
    if accepted.get('pid') != final.get('pid'):
        return 'pid_mismatch'
    if accepted.get('inv') != final.get('inv'):
        return 'inv_mismatch'
    starts = {(r.get('body') or {}).get('request_id')
              for r in lines if r.get('kind') == 'call_started'}
    terminals = {(r.get('body') or {}).get('request_id')
                 for r in lines if r.get('kind') in ('call_response', 'call_error')}
    if starts - terminals:
        return 'call_unterminated'
    return None


# ---------------------------------------------------------------------------
# periodic integrity and the arm-blind status file
# ---------------------------------------------------------------------------
def worktree_check(ctx: RunContext, world: 'World') -> dict | None:
    """Every ``execution.worktree_check_s`` seconds: recompute the digest of every readable
    freeze-bundle file, of every CLOSED chain segment and of ``src/winstats.py``, and
    re-assert the worktree path, ``HEAD`` branch and ``HEAD`` commit.

    Returns ``None`` when everything matches, else the observed/expected digest list, which
    the caller turns into ``trial_paused(worktree_drift)`` (protocol 6.4 row 27).  A changed
    CLOSED segment is ``trial_aborted(chain_unreadable)`` and is recorded as an environment
    event, never as a 12.6 editing finding against the operator."""
    digests: list[dict] = []
    for tok, expected in sorted(world.integrity_digests.items()):
        path = world.integrity_paths[tok]
        try:
            observed = sha256_file(path) if Path(path).exists() else '0' * 64
        except OSError:
            observed = '0' * 64
        if observed != expected:
            digests.append({'file': tok, 'expected': expected, 'observed': observed})
    rt = runtime(ctx.cfg)
    expected_tree = rt.get('worktree')
    if expected_tree:
        observed = git_identity()
        for key in ('branch', 'commit'):
            want = expected_tree.get(key)
            if want and observed.get(key) != want:
                digests.append({'file': f'<REPO>/.git/{key}',
                                'expected': sha256_text(str(want)),
                                'observed': sha256_text(str(observed.get(key)))})
    return {'digests': digests} if digests else None


def status_snapshot(ctx: RunContext, world: 'World') -> dict:
    """The arm-blind ``status.json`` of protocol 14.7.

    No outcome, no coin, no statistic, no band: the key set is exactly this frozen list and
    a test asserts it."""
    return {
        'trial': ctx.trial,
        'phase': world.phase,
        'pairs_enrolled': world.pairs_enrolled,
        'pairs_completed': world.pairs_completed,
        'elapsed_s': round(time.monotonic() - world.t0_mono, 3),
        'servers_ok': dict(world.server_ok),
        'receipts_obtained': world.receipts_obtained,
        'terminal_failure_count': world.terminal_failures,
    }


# ---------------------------------------------------------------------------
# the episode record the orchestrator keeps for one arrival
# ---------------------------------------------------------------------------
@dataclass
class Attempt:
    arrival: int
    attempt: int
    pair: int | None
    position: int | None
    arm: str
    workflow: str
    server_id: str
    task_uid: str
    spool: Path
    job: dict
    assignment_seq: int
    post_decision: bool
    started_after_resume: bool = False
    partner_concurrent: bool = False
    recovered_orphan: bool = False
    proc: Any = None
    pid: int = 0
    offset: int = 0
    dispatched_mono: float = 0.0
    finished: bool = False
    revealed: bool = False
    ended_mono: float | None = None
    calls: dict = field(default_factory=dict)
    lines: list = field(default_factory=list)
    logged: set = field(default_factory=set)
    suppress_final: bool = False
    worker_index: int = 0
    #: the ``worker_resolved`` body of this attempt's worker, once written (repair contract
    #: EB5); ``None`` while the process may still run -- a used send permit.
    resolution: dict | None = None


# ---------------------------------------------------------------------------
# the world: every side effect of the state machine
# ---------------------------------------------------------------------------
class World:
    """The live handles: the chain, the monitor, the subprocesses, the servers and the
    anchor spool.  ``step`` performs every side effect through a method of this object, so
    the transition table can be driven against a substitute (the dry runs use
    :class:`SimWorld`, which replaces only the dispatch of a worker process)."""

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.rt = runtime(ctx.cfg)
        self.cfg = frozen_cfg(ctx.cfg)
        self.t0_mono = time.monotonic()
        self.log: EventLog | None = None
        self.monitor = lab_monitor.MonitorState(ctx.mc)
        self.tiers = lab_enclosure.tiers_from_config(self.cfg)
        self.attempts: dict[int, Attempt] = {}
        self.open_arrivals: list[int] = []
        self.pair_of_arrival: dict[int, int] = {}
        self.pairs_enrolled = 0
        self.pairs_completed = 0
        self.reveal_index = 0
        self.terminal_failures = 0
        self.consecutive_terminal = 0
        self.receipts_obtained = 0
        self.decision: dict | None = None
        self.decision_seq: int | None = None
        self.decided_arm: str | None = None
        self.anchor_seq = 0
        self.pending_anchor: dict | None = None
        self.receipt_offset = 0
        self.server_ok: dict[str, bool] = {}
        self.server_pids: dict[str, int] = {}
        self.phase = 'randomizing'
        self.looks_written = 0
        self.deferred_resume = False
        self.next_arrival_cursor = 0
        self.post_decision_dispatched = 0
        self.abort_reason: str | None = None
        self.pause_reason: str | None = None
        self.pause_digests: list | None = None
        self.last_health = 0.0
        self.last_worktree = time.monotonic()
        self.integrity_digests: dict[str, str] = {}
        self.integrity_paths: dict[str, Path] = {}
        self.counters: dict[str, dict] = {}
        self.usage_sum: dict[str, dict] = {}
        self.findings: list[str] = []
        self.poll_s = float(self.cfg.get('execution', {}).get('poll_interval_ms', 50)) / 1000.
        if self.rt.get('poll_interval_ms') is not None:
            self.poll_s = float(self.rt['poll_interval_ms']) / 1000.0
        self.hard_cap_s = float(self.rt.get('episode_hard_cap_s')
                                or episode_hard_cap_s(self._execution()))
        self.max_pairs = int(self.rt.get('max_pairs') or len(ctx.order))
        self.mock = bool(self.rt.get('mock'))
        #: The program-wide used-seed registry of protocol 5.5 (execution review E2).  Held
        #: in memory and mirrored to ``<work root>/used_seeds.json``, which every worker of
        #: every trial reads before its first request.
        self.seed_registry_path = seed_registry_path(self.work_root())
        self.used_seeds: set[int] = set()
        self._seeds_on_disk: int = -1
        # -- supervision (repair contract EB1 items 1-2; protocol 5.3) -----------------
        # The cap and the threshold are frozen inputs that preflight has already refused
        # when absent or malformed on a non-simulated run; a simulated run supervises
        # nothing and carries None.
        try:
            self.restart_cap: int | None = (None if self.rt.get('sim')
                                            else lab_common.server_supervision_cap(self.cfg))
        except lab_common.FrozenMismatch:
            self.restart_cap = None
        try:
            self.health_threshold: int | None = (None if self.rt.get('sim')
                                                 else health_failures_to_down(self.cfg))
        except ValueError:
            self.health_threshold = None
        #: consecutive failed ``/health`` polls per server; reset by a good poll or a restart.
        self.health_failures: dict[str, int] = {}
        #: attempted supervised restarts per server in this trial (rebuilt on resume).
        self.restarts: dict[str, int] = {}
        #: tokenized ``/props`` digest of each server's last verified start or restart.
        self.server_props_sha: dict[str, str] = {}
        #: arrivals in flight at any ``server_down``: their reveal carries ``infra_flag``.
        self.down_overlap: set[int] = set()
        #: server -> seq of a ``server_down`` the chain has not yet resolved (resume only).
        self.unresolved_down: dict[str, int] = {}
        #: the outcome supervision owes once every open attempt is revealed: an abort
        #: (``server_restart_cap``, ``server_identity``, ``receipt_mismatch``,
        #: ``harness_defect``) or ``server_unrecoverable``.  While either is set nothing new
        #: is dispatched and the pump drains; an abort outranks a pause.
        self.pending_abort: str | None = None
        self.pending_pause: str | None = None
        #: resume only: the previous invocation's server pids by server, and those of them
        #: that are provably no longer that server (dead, or alive and not listening on its
        #: port: a reused pid, never signalled).
        self.previous_pids: dict[str, int] = {}
        self.previous_gone: set[int] = set()
        # -- the restart-cap estimand (root 21:14 ruling; root 00:22) --------------------
        #: the frozen tree is a dry run (the verifier's and the builder's MOCK rule): only
        #: there may a decision receipt without an external server time count as one
        #: (``lab_eventlog.decision_receipt``).
        self.tree_mock = bool(self.cfg.get('mock') or self.cfg.get('mock_overrides'))
        #: every anchor request of this chain by request id (this invocation's, and the
        #: previous invocations' read back from ``anchor_spool/requests.jsonl``): a receipt
        #: is chained under the ``anchor_seq`` of the request it answers.
        self.anchor_requests: dict[str, dict] = {}
        #: ``anchor_seq`` -> ``'receipt'`` / ``'failed'`` as chained: a receipt line read
        #: again (a resumed invocation re-reads the receipt spool from its start) is not
        #: chained twice.
        self.anchor_resolved: dict[int, str] = {}
        #: ``anchor_seq`` -> SHA-256 of the receipt line that resolved it (a later line with
        #: these exact bytes is a ``duplicate``; any other later line is never chained over it).
        self.anchor_resolving_sha: dict[int, str] = {}
        #: resume only: the chain's receipt-line events (:data:`RECEIPT_LINE_EVENTS`) in
        #: order -- one per receipt spool line an earlier invocation consumed; those lines
        #: are replayed (state rebuilt, nothing appended), every later line is judged.
        self._receipt_replay: list[Mapping] = []
        self._receipt_lines_read = 0
        self.receipts_rejected = 0
        #: this invocation's blocking ``decision`` anchor came back ``ok: false``
        #: (protocol 6.4 row 26, 12.4 item 2: ``trial_paused(anchor_unavailable)``).
        self.decision_anchor_failed = False
        self._decision_receipted = False
        # -- worker resolution (repair contract EB5; root 20:40 item 3, 21:15 item 3) ------
        #: arrivals whose worker THIS invocation spawned and has not resolved yet: every one
        #: is a used send permit (no orchestrator gate can revoke a live worker's POST), so
        #: nothing terminal, no pause and no new pair may be written while one is here.
        self.live_workers: set[int] = set()
        #: a worker was recorded ``alive_unresolved`` / ``liveness_unknown`` (by this
        #: invocation, or by an earlier one on this chain): the phase can no longer complete,
        #: so nothing new is enrolled or dispatched and no decision is taken; the close's
        #: resolution verdict then refuses ``trial_ended`` (it is the one gate, EB5 C9).
        self.unresolved_seen = False
        #: set by :meth:`close_trial`: a look written while the trial closes (the abort drain's
        #: reveals, the final flush) never takes a decision -- an abort can only remove
        #: decisions, never create one (protocol 6.4).
        self.closing = False
        #: the chain's no-decision point (``lab_eventlog.no_decision_point``) as of the last
        #: :meth:`_write_looks`; ``failure_limit`` is the ten-failure rule's frozen count.
        self.no_decision: dict | None = None
        self.failure_limit = int(((self.cfg.get('execution') or {}).get('auto_abort') or {})
                                 .get('consecutive_infrastructure_failures', 10))
        #: how long the close waits for every held server to be idle once the clients are
        #: resolved (``execution.request_timeout_s``, the frozen budget of one request; a
        #: runtime ``resolution_idle_wait_s`` overrides it -- :func:`preflight` refuses that
        #: override unless the frozen tree is a dry run, so only the controls can set it).
        self.idle_wait_s = float(self.rt.get('resolution_idle_wait_s')
                                 if self.rt.get('resolution_idle_wait_s') is not None
                                 else self._execution()['request_timeout_s'])

    # -- configuration --------------------------------------------------------
    def _execution(self) -> dict:
        ex = dict(self.cfg.get('execution') or {})
        if ex.get('request_timeout_s') is None:
            ex['request_timeout_s'] = float(self.rt.get('request_timeout_s') or 180.0)
        return ex

    def work_root(self) -> Path:
        """The PROGRAM work root, one level above this trial's ``paths.work``."""
        rt_root = self.rt.get('work_root')
        return Path(rt_root) if rt_root else Path(self.ctx.paths.work).parent

    # -- the used-seed registry (protocol 5.5; execution review E2) -----------
    def load_seed_registry(self) -> None:
        """Rebuild the program-wide used-seed set and publish it, before any episode starts.

        Called at trial start AND at resume, so a worker never draws against a set that a
        crash left stale.  The reconstruction reads every trial's spools, which is what makes
        the set program-wide and what makes it survive an unclean exit; the file is then
        rewritten so that the next worker reads the repaired set rather than the stale one.
        """
        self.used_seeds = seed_registry_reconstruct(self.work_root())
        self._seeds_on_disk = -1
        self.persist_seed_registry()

    def note_seed(self, seed: int) -> None:
        """Record a seed a worker committed to sending (its ``call_started`` spool line)."""
        self.used_seeds.add(int(seed))

    def persist_seed_registry(self) -> None:
        """Mirror the in-memory set to disk when it has grown.

        Called before every dispatch, so the worker about to start reads every seed its
        predecessors committed to.  Pair-synchronous execution (COORDINATOR_DECISIONS C2)
        is what makes that complete rather than merely current: pair i+1 is enrolled only
        after both episodes of pair i are revealed, and a reveal follows the ingest of that
        episode's whole spool, so no earlier request of this worker's own half of the seed
        space is still unseen when the file is written.  The two concurrent workers of one
        pair cannot collide with each other at all, because the low bit of the seed carries
        ``worker_index``."""
        if len(self.used_seeds) == self._seeds_on_disk:
            return
        write_seed_registry(self.seed_registry_path, self.used_seeds)
        self._seeds_on_disk = len(self.used_seeds)

    # -- the chain ------------------------------------------------------------
    def open_chain(self, *, create: bool) -> None:
        self.log = EventLog(self.ctx.paths.events, self.ctx.trial, self.ctx.bundle_sha,
                            self.ctx.inv, create=create)

    def append(self, etype: str, body: dict, *, durable: bool = False):
        assert self.log is not None
        ev = self.log.append(etype, body, durable=durable)
        if etype in CONSUMED:
            self.evaluate()
        return ev

    # -- the look (cadence and bodies come from lab_monitor.replay) -----------
    def evaluate(self) -> dict | None:
        """Write every look the replay produces that the chain does not yet carry.

        Returns the ``Decision`` (as a dict) when the frozen ``lab_monitor.decide`` decided
        at the last look, else ``None``.  A trailing ``resume`` look is deferred: the
        replay places it at the last fully enrolled prefix *before any new enrollment*
        (protocol 8.3 trigger 4), which is only known once the next consumed event exists.
        :meth:`flush_looks` writes it when the trial can enroll no further."""
        return self._write_looks(defer_resume=True)

    def flush_looks(self) -> dict | None:
        return self._write_looks(defer_resume=False)

    def _write_looks(self, *, defer_resume: bool) -> dict | None:
        assert self.log is not None
        events = self.log.events
        try:
            looks = lab_monitor.replay(events, self.cfg, self.ctx.trial)
        except Exception as exc:                            # noqa: BLE001
            raise MonitorError(f'{type(exc).__name__}: {exc}') from exc
        if len(looks) < self.looks_written:
            raise MonitorError('the replay lost a look that the chain carries')
        if len(looks) == self.looks_written:
            return None          # no new look: the shadow is not evaluated at a non-look
        try:
            refs = lab_reference_rule.looks_from_chain(events, self.cfg, self.ctx.trial)
        except Exception as exc:                            # noqa: BLE001
            # protocol 6.4 row 17: an exception raised by the shadow reference rule pauses
            # the trial and is a decision_code_defect candidate that no re-freeze repairs.
            raise MonitorError(f'reference rule: {type(exc).__name__}: {exc}') from exc
        new = looks[self.looks_written:]
        if defer_resume and new and new[-1].get('trigger') == 'resume':
            new = new[:-1]
            self.deferred_resume = True
        elif new:
            self.deferred_resume = False
        # The no-decision point of this chain (``lab_eventlog.no_decision_point``), read
        # once: every look written below is appended after every event it reads, and a
        # ``monitor_update`` is never itself such a point.
        self.no_decision = lab_eventlog.no_decision_point(
            events, self.restart_cap, failure_limit=self.failure_limit)
        decision = None
        for snap in new:
            decision = self._write_one_look(snap, refs)
        return decision

    def _write_one_look(self, snap: Mapping, refs: Sequence) -> dict | None:
        index = self.looks_written
        trigger = str(snap['trigger'])
        pair_updated = snap.get('pair_updated')
        enc_obj = snap.get('pair_enclosure')
        # keep the live MonitorState in step with the replay, then cross-check it
        if pair_updated is not None and enc_obj is not None:
            pair = int(pair_updated)
            enc = lab_enclosure.PairEnclosure(
                h=lab_enclosure.Enclosure(float(enc_obj['h'][0]), float(enc_obj['h'][1])),
                s=lab_enclosure.Enclosure(float(enc_obj['s'][0]), float(enc_obj['s'][1])),
                collapsed=bool(enc_obj['collapsed']),
                decisive_tier=int(enc_obj['decisive_tier']))
            if trigger == 'enroll':
                self.monitor.enroll(pair)
            self.monitor.update(pair, enc)
        live = self.monitor.snapshot()
        for key in ('n', 'n_collapsed', 'sum_lower_h', 'sum_upper_h', 'sum_lower_s',
                    'sum_upper_s', 'radius', 'L_h', 'U_h', 'L_s', 'U_s'):
            if repr(live.get(key)) != repr(snap.get(key)):
                raise MonitorError(
                    f'the live monitor and the replay differ in {key} at look {index}')
        shadow, mismatch = self._shadow_for(index, trigger, snap, refs)
        body = {k: snap[k] for k in ('n', 'n_collapsed', 'sum_lower_h', 'sum_upper_h',
                                     'sum_lower_s', 'sum_upper_s', 'radius', 'L_h', 'U_h',
                                     'L_s', 'U_s', 'flags', 'readouts', 'sums_fsum')}
        body['trigger'] = trigger
        body['pair_updated'] = None if pair_updated is None else int(pair_updated)
        body['pair_enclosure'] = (
            {'h': [-1.0, 1.0], 's': [-1.0, 1.0], 'collapsed': False, 'decisive_tier': -1}
            if enc_obj is None else
            {'h': [float(enc_obj['h'][0]), float(enc_obj['h'][1])],
             's': [float(enc_obj['s'][0]), float(enc_obj['s'][1])],
             'collapsed': bool(enc_obj['collapsed']),
             'decisive_tier': int(enc_obj['decisive_tier'])})
        body['shadow'] = shadow
        body['monitor_code_sha256'] = self.monitor_code_sha256
        assert self.log is not None
        self.log.append('monitor_update', body, durable=False)
        self.looks_written += 1
        if mismatch:
            raise PauseTrial('monitor_mismatch')
        if trigger == 'drain' or self.decision is not None:
            return None                     # the decision prefix is closed at the crossing
        if self.pending_abort is not None or self.no_decision is not None:
            # An abort is owed, or its trigger is in the chain: the trial takes no new
            # decision (protocol 6.4: "An abort can only remove decisions, never create
            # one").  Root 21:14 ruling, case (a): a fourth restart was required before any
            # decision.  Review of 988baf7, reviewer 1 finding 1: the same holds for EVERY
            # owed abort -- a restart that failed its identity or smoke stage used to leave
            # the drain free to take a new decision, which the deferred abort then treated
            # as a post-decision abort.  The look above is logged exactly as without the
            # abort (the band, the enclosures and the reference rule's shadow are untouched);
            # only the decision event is not appended.  ``no_decision`` is the chain's own
            # point (``lab_eventlog.no_decision_point``), which the verifier and the builder
            # read: a crossing after it is reported not acted on.
            return None
        if self.closing or self.unresolved_seen:
            # Repair contract EB5: a look logged while the trial closes (the abort drain's
            # reveals) or while an unresolved worker makes the phase incomplete takes no
            # decision -- the look itself is logged unchanged.
            return None
        # The decision is taken here, immediately after the monitor_update it quotes
        # (ordering invariant 7): nothing may sit between the two lines.
        return self.take_decision(lab_monitor.decide(self.monitor, self.ctx.mc))

    def _shadow_for(self, index: int, trigger: str, snap: Mapping,
                    refs: Sequence) -> tuple[dict, bool]:
        """The reference rule's values for this look, and the mismatch flag (protocol 8.9).

        ``lab_reference_rule`` emits its ``resume`` look at ``invocation_started`` while
        ``lab_monitor.replay`` emits it at the last fully enrolled prefix before the next
        enrollment, so the two lists agree element for element only on their non-``resume``
        subsequences.  The shadow of a non-``resume`` look is the reference look at the same
        index of that subsequence; the shadow of a ``resume`` look is the reference's
        immediately preceding non-``resume`` look, which is at the same prefix with the same
        enclosures.  Every decision-bearing look is therefore compared value for value."""
        plain = [lk for lk in refs if lk.trigger != 'resume']
        j = self.plain_looks_written
        if trigger == 'resume':
            ref = plain[j - 1] if j > 0 else None
        else:
            ref = plain[j] if j < len(plain) else None
            self.plain_looks_written = j + 1
        if ref is None:
            return ({'n': int(snap['n']), 'L_h': float(snap['L_h']),
                     'U_h': float(snap['U_h']), 'L_s': float(snap['L_s']),
                     'U_s': float(snap['U_s']), 'action': 'none', 'mismatch': True}, True)
        mismatch = (int(ref.n) != int(snap['n'])
                    or abs(float(ref.L_h) - float(snap['L_h'])) > _SHADOW_TOL
                    or abs(float(ref.U_h) - float(snap['U_h'])) > _SHADOW_TOL
                    or abs(float(ref.L_s) - float(snap['L_s'])) > _SHADOW_TOL
                    or abs(float(ref.U_s) - float(snap['U_s'])) > _SHADOW_TOL
                    or abs(float(ref.sum_lower_h) - float(snap['sum_lower_h'])) > _SHADOW_TOL
                    or abs(float(ref.sum_upper_h) - float(snap['sum_upper_h'])) > _SHADOW_TOL
                    or abs(float(ref.sum_lower_s) - float(snap['sum_lower_s'])) > _SHADOW_TOL
                    or abs(float(ref.sum_upper_s) - float(snap['sum_upper_s'])) > _SHADOW_TOL)
        return ({'n': int(ref.n), 'L_h': float(ref.L_h), 'U_h': float(ref.U_h),
                 'L_s': float(ref.L_s), 'U_s': float(ref.U_s), 'action': str(ref.action),
                 'mismatch': bool(mismatch)}, bool(mismatch))

    plain_looks_written = 0

    @property
    def monitor_code_sha256(self) -> str:
        if not hasattr(self, '_mcs'):
            self._mcs = sha256_file(lab_common.HERE / 'lab_monitor.py')
        return self._mcs

    # -- what_was_known -------------------------------------------------------
    def what_was_known(self) -> dict:
        snap = self.monitor.snapshot()
        lh, uh = float(snap['L_h']), float(snap['U_h'])
        ls = float(snap['L_s'])
        by_arm = {'incumbent': 0, 'candidate': 0}
        for att in self.attempts.values():
            if att.revealed:
                by_arm[att.arm] = by_arm.get(att.arm, 0) + 1
        return {
            'pairs_enrolled': self.pairs_enrolled,
            'pairs_completed': self.pairs_completed,
            'revealed_by_arm': by_arm,
            'L_h': lh, 'U_h': uh, 'L_s': ls, 'U_s': float(snap['U_s']),
            'distance_to_harm': uh,
            'distance_to_deploy_h': lh,
            'distance_to_deploy_s': ls + float(self.ctx.mc.delta),
            'earlier_trials': list(self.rt.get('earlier_trials') or []),
        }

    # -- servers --------------------------------------------------------------
    def start_servers(self) -> None:
        """Start every server this trial uses, through ``lab_server.start`` (route (a) of
        root's 20:40 decision, item 1).

        On success the body ``lab_server.start`` returned -- every value observed or
        compared, nothing hard-coded -- is appended as ``server_started`` and the pid is
        recorded in ``server_pids`` BEFORE ``scrape('trial_start')``, so the soft host scan
        counts the server as this harness's own process.  On ``ServerStartFailed`` the record
        is appended as ``server_start_failed`` (durable), every server already started is
        stopped with a ``server_stopped`` record, and the trial is aborted: ``server_identity``
        for the GGUF, the serving manifest or the identity stage (protocol 6.4 row 6),
        ``receipt_mismatch`` for the smoke, ``infrastructure`` for launch or health (row 5).
        A call ``lab_server.start`` REFUSED (it launched nothing) is a harness defect, and so
        is any other ``Exception`` out of the start or the append (``lab_server.start``
        converts what it did not anticipate after a launch into ``ServerStartFailed``, so
        what is left launched nothing that is still running or is already held and stopped
        here): the servers held are stopped and the trial ends in
        ``trial_aborted(harness_defect)``, never in an exception escaping after
        ``trial_started`` (EB1 fix, reviewer 1 finding 7).

        A simulated invocation starts nothing and appends :meth:`sim_server_started_body`."""
        if self.rt.get('sim'):
            for server_id, spec in sorted(self.ctx.servers.items()):
                self.append('server_started', self.sim_server_started_body(server_id, spec),
                            durable=True)
            return
        for server_id in sorted(self.ctx.servers):
            try:
                self._start_one(server_id)
            except lab_common.ServerStartFailed as exc:
                self.append('server_start_failed', dict(exc.record), durable=True)
                self.stop_servers()
                raise AbortTrial(START_FAILURE_REASON[str(exc.record['stage'])]) from None
            except PreflightError:
                self.stop_servers()
                raise AbortTrial('harness_defect') from None
            except Exception:
                self.stop_servers()
                raise AbortTrial('harness_defect') from None

    def _server_call_kwargs(self, server_id: str) -> dict:
        """The frozen inputs every ``lab_server.start`` / ``restart`` of one server gets."""
        golden = self.ctx.golden.get(server_id)
        return {'golden': golden, 'sampling': dict(self.cfg.get('sampling') or {}),
                'serving_manifest_path': self.ctx.serving_manifest_path,
                'serving_manifest_sha256': (self.cfg.get('llama_cpp') or {}).get(
                    lab_serving_manifest.CONFIG_DIGEST_KEY)}

    def _start_one(self, server_id: str) -> dict:
        """``lab_server.start`` in trial mode; on success the returned body is appended as
        ``server_started`` and the pid is held.  Raises what ``lab_server.start`` raises (the
        caller decides what a failure means: an abort at the first start, the supervision
        rules on resume)."""
        spec = self.ctx.servers[server_id]
        kw = self._server_call_kwargs(server_id)
        body = lab_server.start(
            spec, golden_props=(kw['golden'] or {}).get('props'),
            timeout_s=float(self.rt.get('server_start_timeout_s') or 600.0),
            mode='trial', kind='start', restart_index=0, **kw)
        self.server_pids[server_id] = int(body['pid'])
        self.server_props_sha[server_id] = str(body['props_sha256'])
        self.health_failures[server_id] = 0
        self.append('server_started', body, durable=True)
        self.server_ok[server_id] = bool(body['props_matches_golden'] and body['smoke']['ok'])
        return body

    def _stop_server(self, server_id: str) -> None:
        """Stop (or reap) one held server and append its durable ``server_stopped`` with the
        return code the stop observed; the pid is dropped, so it is never stopped twice."""
        pid = int(self.server_pids.get(server_id) or 0)
        if not pid:
            return
        result = lab_server.stop(pid)
        self.server_pids.pop(server_id, None)
        self.server_ok[server_id] = False
        self.append('server_stopped', {
            'server_id': server_id, 'pid': pid,
            'returncode': (int(result['returncode'])
                           if result.get('returncode') is not None else None),
            'seconds': float(result.get('seconds') or 0.0)}, durable=True)

    def stop_servers(self) -> None:
        """Stop every server this invocation started and still holds, each with a durable
        ``server_stopped`` record carrying the return code the stop observed.  The pid is
        dropped once stopped, so no server is stopped (or recorded) twice."""
        for server_id in sorted(self.server_pids):
            self._stop_server(server_id)

    def sim_server_started_body(self, server_id: str, spec: ServerSpec) -> dict:
        """The body of a SIMULATED start, which starts nothing and compares nothing.

        Every digest that would name an observation is ``lab_eventlog.SIM_SERVER_SHA256``,
        the pid is 0 and the GGUF byte count is 0 (no file was read), and every comparison
        flag is False, because no comparison was performed.  ``lab_eventlog.
        is_sim_server_body`` recognises the body by those sentinels alone, without reading
        a single comparison flag.  Usage and timings are zero because no completion was
        made; a simulated chain carries the MOCK banner in every derived file."""
        sim = lab_eventlog.SIM_SERVER_SHA256
        return {
            'server_id': server_id, 'pid': 0, 'port': int(spec.port),
            'argv_sha256': sha256_canonical(lab_server.server_argv(spec)),
            'gguf': {'bytes': 0, 'sha256': sim},
            'props_sha256': sim, 'props_matches_golden': False,
            'total_slots': int(spec.n_slots), 'n_ctx': int(spec.ctx_per_slot),
            'load_seconds': 0.0,
            'smoke': {'request_sha256': sim, 'receipt_matches_golden': False,
                      'usage': {k: 0 for k in USAGE_KEYS},
                      'timings': {'cache_n': 0, 'prompt_n': 0, 'prompt_ms': 0.0,
                                  'predicted_n': 0, 'predicted_ms': 0.0,
                                  'predicted_per_second': 0.0},
                      'ok': False}}

    def scrape(self, point: str, *, server_ids: Iterable[str] | None = None) -> None:
        """``metrics_scrape`` (durable) for every server of the trial, or for ``server_ids``
        only -- the ``restart`` scrape of protocol 13.1 (P:2546) is of the restarted server."""
        execution = self.cfg.get('execution') or {}
        only = None if server_ids is None else {str(s) for s in server_ids}
        for server_id, spec in sorted(self.ctx.servers.items()):
            if only is not None and server_id not in only:
                continue
            if self.rt.get('sim'):
                counters = self._sim_counters(server_id)
                ok, tries = True, 1
            else:
                got = lab_server.metrics(
                    spec.base_url, timeout=float(execution.get('metrics_timeout_s', 5)),
                    tries=int(execution.get('metrics_tries', 3)))
                ok = bool(got.get('ok'))
                tries = int(execution.get('metrics_tries', 3)) if not ok else 1
                counters = {k: (int(got[k]) if isinstance(got.get(k), int) else None)
                            for k in ('prompt_tokens_total', 'tokens_predicted_total',
                                      'n_decode_total', 'requests_processing',
                                      'requests_deferred')}
            self.counters[server_id] = counters
            self.append('metrics_scrape', {
                'server_id': server_id, 'point': point, 'ok': ok, 'counters': counters,
                'tries': tries, 'unreconciled': not ok}, durable=True)
        self.host_scan(point)

    def host_scan(self, point: str) -> None:
        """protocol 5.7 inside a running trial: the OBSERVING half of the gate.

        It never raises and never stops the trial -- a mid-trial refusal would throw away
        the pairs already enrolled, and the decision about contention belongs to the
        operator and to the analysis.  What it must do is leave a record: the event is
        written whether or not anything was found, so that a reader can see positively
        that the host was scanned at this point and what was seen."""
        # `self.cfg` is the FROZEN projection and carries no runtime overlay, so the
        # simulation predicate must be read from the context's own configuration.
        if point not in ('trial_start', 'quiescent') \
                or not host_scan_is_required(self.ctx.cfg):
            return
        scan = lab_hostcheck.soft_host_check(own_harness_pids(self))
        try:
            self.append('foreign_load_detected',
                        dict(lab_hostcheck.chain_body(scan), point=point), durable=True)
        except lab_common.SchemaError as exc:                # pragma: no cover - belt
            self.findings.append(f'host_scan_unwritable:{type(exc).__name__}')

    def _sim_counters(self, server_id: str) -> dict:
        """In a simulated run the counters are the exact sum of the receipted usage, so the
        reconciliation residual is 0 by construction.  Every derived file of such a run
        carries the MOCK banner."""
        assert self.log is not None
        prompt = predicted = 0
        for ev in self.log.events:
            if ev['type'] == 'llm_response' and ev['body']['server_id'] == server_id:
                prompt += int(ev['body']['usage']['prompt_tokens'])
                predicted += int(ev['body']['usage']['completion_tokens'])
        return {'prompt_tokens_total': prompt, 'tokens_predicted_total': predicted,
                'n_decode_total': predicted, 'requests_processing': 0,
                'requests_deferred': 0}

    def health_poll(self) -> None:
        """The supervisor of protocol 5.3 (P:915-922), every ``execution.health_poll_s``.

        For each server this invocation holds: first ``lab_server.exit_status`` -- a child
        that has exited is down at once (``detected_by='exit'``, with its return code);
        otherwise ``/health`` is polled and logged as ``server_health``, and the
        ``execution.health_failures_to_down``-th CONSECUTIVE failure is down
        (``detected_by='health'``).  A down server goes to :meth:`supervise_down`.  A server
        this invocation does not hold (never started, or stopped after a failed restart) is
        not polled.  A simulated run polls nothing real and supervises nothing."""
        execution = self.cfg.get('execution') or {}
        every = float(execution.get('health_poll_s', 5))
        now = time.monotonic()
        if now - self.last_health < every:
            return
        self.last_health = now
        for server_id, spec in sorted(self.ctx.servers.items()):
            if self.rt.get('sim'):
                self.server_ok[server_id] = True
                self.append('server_health', {'server_id': server_id, 'ok': True,
                                              'slots_busy': len(self.open_arrivals),
                                              'rss_bytes': 0, 'clock_anomaly': False})
                continue
            pid = int(self.server_pids.get(server_id) or 0)
            if not pid:
                continue
            try:
                returncode = lab_server.exit_status(pid)
            except lab_common.LabError:
                returncode = None          # not a child of this process: /health decides
            if returncode is not None:
                self.server_ok[server_id] = False
                self.supervise_down(server_id, 'exit', int(returncode))
                continue
            got = lab_server.health(spec.base_url)
            ok = bool(got.get('ok'))
            self.server_ok[server_id] = ok
            self.append('server_health', {'server_id': server_id, 'ok': ok,
                                          'slots_busy': int(got.get('slots_busy') or 0),
                                          'rss_bytes': 0, 'clock_anomaly': False})
            if ok:
                self.health_failures[server_id] = 0
                continue
            self.health_failures[server_id] = self.health_failures.get(server_id, 0) + 1
            threshold = self.health_threshold
            if threshold is None:
                # preflight refuses this before seq 0; reaching it is the harness's defect
                self.pending_abort = self.pending_abort or 'harness_defect'
                continue
            if self.health_failures[server_id] >= threshold:
                self.supervise_down(server_id, 'health', None)

    def supervise_exits(self) -> None:
        """The exit half of :meth:`health_poll`, unthrottled, at a pair boundary (IDLE).

        For each server this invocation holds, ``lab_server.exit_status`` -- a non-blocking
        ``Popen.poll`` of its own child -- and, when the process has exited,
        :meth:`supervise_down` (``detected_by='exit'``) before anything is enrolled.  Without
        it a server that died after the last health poll (``execution.health_poll_s``) was
        handed a whole new pair, whose two arrivals then waited on recovery and were revealed
        with ``infra_flag`` (EB1c control C6, pre-fix: an ``ok: false`` ``pair_boundary``
        scrape followed by ``pair_enrolled``).  ``/health`` is NOT polled here: the
        consecutive-failure rule of protocol 5.3 keeps its cadence.  Does nothing on a
        simulated run, for a server not held, or for a pid this process did not start.
        Not called before the follow-up cohort's one-at-a-time dispatch, which still relies on
        the health poll's cadence."""
        if self.rt.get('sim'):
            return
        for server_id in sorted(self.ctx.servers):
            pid = int(self.server_pids.get(server_id) or 0)
            if not pid:
                continue
            try:
                returncode = lab_server.exit_status(pid)
            except lab_common.LabError:
                continue                   # not a child of this process: /health decides
            if returncode is not None:
                self.server_ok[server_id] = False
                self.supervise_down(server_id, 'exit', int(returncode))

    def supervise_down(self, server_id: str, detected_by: str,
                       returncode: int | None) -> None:
        """One ``server_down`` and what supervision does about it (repair contract EB1 item
        2; protocol 5.3, 5.6 row 5, 14.6; root 20:40 item 4).

        1. Every open spool is ingested first, so that each response the dying process
           served is a chain event of ITS reconciliation window, not of the next one.
        2. ``server_down`` (durable): the arrivals still in flight on that server with their
           arms, the last scraped counters, ``counters_lost: true`` (a process's counters die
           with it, A:2266-2269).  Those arrivals' reveals carry ``infra_flag`` (P:1387-1388).
        3. The old process is stopped -- a hung one by SIGTERM/SIGKILL, an exited one only
           reaped -- and recorded as ``server_stopped``.
        4. If the server's attempted supervised restarts already reach the frozen cap, a
           further restart would be required: nothing is restarted, nothing new is
           dispatched, the open attempts drain through the ordinary pump (the hard-cap kill
           still applies) and are revealed, and then ``trial_aborted(server_restart_cap)``.
           This outranks any other pending outcome.  No replacement trial, no extra pair.
           Root's 21:14 ruling fixes what the abort means by where the chain stands
           (``lab_eventlog.restart_cap_case``): (a) before any decision -- incomplete, and
           no decision is taken afterwards (:meth:`_write_one_look`); (b) after a decision
           whose blocking anchor carries its chained external receipt -- the decision and
           its tau stand and the follow-up is truncated; (c) while the logged decision still
           awaits that receipt -- the abort waits in ``ANCHOR_BLOCK`` for the existing
           receipt rule (:meth:`raise_pending`), and if the receipt never comes the existing
           anchor-failure rule pauses the trial (``anchor_unavailable``) with the abort still
           owed.  The cap touches no monitor input, allocation, margin or score.
        5. Otherwise, unless an abort is already owed, :meth:`supervised_restart`."""
        self._ingest_open()
        old_pid = int(self.server_pids.get(server_id) or 0)
        inflight = [{'arrival': int(a), 'arm': self.attempts[a].arm}
                    for a in sorted(self.open_arrivals)
                    if a in self.attempts and self.attempts[a].server_id == server_id
                    and not self.attempts[a].revealed]
        counters = self.counters.get(server_id) or {}
        self.down_overlap.update(row['arrival'] for row in inflight)
        self.append('server_down', {
            'server_id': server_id, 'detected_by': detected_by,
            'returncode': None if returncode is None else int(returncode),
            'inflight': inflight,
            'last_counters': {k: (int(counters[k]) if isinstance(counters.get(k), int)
                                  else None) for k in COUNTER_KEYS},
            'counters_lost': True}, durable=True)
        self.server_ok[server_id] = False
        self.health_failures[server_id] = 0
        if old_pid:
            self._stop_server(server_id)
        if self.restart_cap is None:
            # preflight refuses this before seq 0; reaching it is the harness's defect, and
            # an unbounded restart is never the fallback
            self.pending_abort = self.pending_abort or 'harness_defect'
            return
        if self.restarts.get(server_id, 0) >= self.restart_cap:
            self.pending_abort = RESTART_CAP_REASON
            return
        if self.pending_abort is not None:
            return                      # an abort is owed: the trial drains, nothing restarts
        self.supervised_restart(server_id, previous_pid=old_pid)

    def supervised_restart(self, server_id: str, *, previous_pid: int) -> None:
        """``lab_server.restart`` with the identical argv, the golden objects, the frozen
        sampling, the previous start's ``/props`` digest and ``timeout_s =
        execution.server_recovery_s`` (protocol 5.6).  The attempt counts towards the cap
        whether or not it succeeds.

        Success: the pid is held, ``server_restarted`` (durable) is appended and the
        restarted server is scraped (``metrics_scrape(restart)``, P:2546).  A body whose
        ``props_equal_previous`` is false owes ``trial_aborted(server_identity)`` (6.4 row 6).
        Failure: ``server_start_failed(kind=restart)`` is appended as raised, then a server
        that never became healthy (stage ``launch`` / ``health``) owes
        ``trial_paused(server_unrecoverable)`` after the pair (P:2789), and a GGUF, serving
        manifest, identity or smoke failure owes ``trial_aborted`` by
        :data:`START_FAILURE_REASON`.  A call ``lab_server.restart`` REFUSED (it launched
        nothing) owes ``trial_aborted(harness_defect)``, and so does any other ``Exception``
        out of it (``lab_server.start`` converts what it did not anticipate after a launch
        into ``ServerStartFailed``, which is recorded and counted above; EB1 fix, reviewer 1
        finding 7: a plain exception used to escape through the pump, leaving the down
        unanswered and the trial without a terminal event)."""
        spec = self.ctx.servers[server_id]
        index = self.restarts.get(server_id, 0) + 1
        self.restarts[server_id] = index
        kw = self._server_call_kwargs(server_id)
        timeout_s = float((self.cfg.get('execution') or {}).get('server_recovery_s', 180))
        try:
            body = lab_server.restart(
                spec, (kw['golden'] or {}).get('props'),
                previous_props_sha256=self.server_props_sha.get(server_id),
                timeout_s=timeout_s, previous_pid=int(previous_pid), restart_index=index,
                **kw)
        except lab_common.ServerStartFailed as exc:
            self.append('server_start_failed', dict(exc.record), durable=True)
            stage = str(exc.record.get('stage'))
            if stage in NEVER_HEALTHY_STAGES:
                self.pending_pause = self.pending_pause or 'server_unrecoverable'
            elif self.pending_abort is None:
                self.pending_abort = START_FAILURE_REASON.get(stage, 'infrastructure')
            return
        except Exception:               # PreflightError (refused) or anything unconverted
            if self.pending_abort is None:
                self.pending_abort = 'harness_defect'
            return
        self.server_pids[server_id] = int(body['pid'])
        self.server_props_sha[server_id] = str(body['props_sha256'])
        self.health_failures[server_id] = 0
        self.append('server_restarted', body, durable=True)
        self.server_ok[server_id] = bool(body['props_matches_golden'] and body['smoke']['ok'])
        if not body.get('props_equal_previous', False) and self.pending_abort is None:
            self.pending_abort = 'server_identity'
        self.scrape('restart', server_ids=[server_id])

    def _ingest_open(self) -> None:
        """Ingest the new spool bytes of every open attempt (as the pump does, without
        reaping or the hard cap); a spool that cannot be read is an interrupted attempt,
        revealed only once its worker is killed and reaped (repair contract EB5 item 1)."""
        for arrival in list(self.open_arrivals):
            att = self.attempts.get(arrival)
            if att is None or att.revealed:
                continue
            try:
                ingest_spool(self, att)
            except SpoolError:
                self.interrupt_unreadable(att)

    def raise_pending(self) -> None:
        """Take the owed supervision outcome once nothing is open: an abort before a pause.

        While a logged decision still awaits its blocking receipt it is NOT taken here
        (root 21:14 ruling, case (c)): the decision is provisional, nothing post-switch is
        dispatched, and ``ANCHOR_BLOCK`` takes the owed outcome only once the existing receipt
        rule has succeeded -- or, if it never does, the existing anchor-failure rule pauses
        the trial (``anchor_unavailable``, protocol 6.4 row 26) with the outcome still owed
        (``supervision_state``: an owed abort survives a pause).  An abort taken before the
        receipt would supersede the decision's blocking anchor with its own.  Nothing is
        taken while a worker this invocation spawned is still unresolved (repair contract
        EB5)."""
        if self.open_arrivals or self.live_workers:
            return
        if self.pending_abort is None and self.pending_pause is None:
            return
        if self.decision is not None and not self.decision_receipted():
            return
        if self.pending_abort is not None:
            raise AbortTrial(self.pending_abort)
        if self.pending_pause is not None:
            raise PauseTrial(self.pending_pause)

    # -- anchors --------------------------------------------------------------
    def request_anchor(self, trigger: str, *, blocking: bool) -> None:
        assert self.log is not None
        seg_path = self.ctx.paths.events / (lab_eventlog.SEGMENT_FMT
                                            % self.log.segment_index)
        raw = seg_path.read_bytes() if seg_path.exists() else b''
        self.anchor_seq += 1
        publish = trigger in (self.cfg.get('anchor', {}).get('publish_segments_at') or [])
        # One id for the chained anchor and its durable request (root f855e45): a receipt
        # line is attributed to this anchor only when it carries exactly this id, and the
        # chain itself binds the anchor_receipt to the anchor (lab_eventlog.decision_receipt).
        request_id = uuid.uuid4().hex
        body = {
            'anchor_seq': self.anchor_seq,
            'upto_seq': max(0, self.log.seq - 1),
            'upto_h': self.log.head,
            'segment_index': self.log.segment_index,
            'segment_bytes': len(raw),
            'segment_sha256': sha256_bytes(raw),
            'cumulative_bytes': self._cumulative_bytes(len(raw)),
            'pairs_enrolled': self.pairs_enrolled,
            'pairs_completed': self.pairs_completed,
            'records_manifest_sha256': self.records_manifest_sha256(),
            'server_log_sha256': {}, 'server_log_bytes': {},
            'trigger': trigger, 'blocking': bool(blocking), 'request_id': request_id,
        }
        self.log.close_segment(anchor_body=body)
        request = {
            'request_id': request_id, 'trial': self.ctx.trial,
            'anchor_seq': self.anchor_seq, 'upto_seq': body['upto_seq'],
            'upto_h': body['upto_h'], 'segment_index': body['segment_index'],
            'segment_bytes': body['segment_bytes'],
            'segment_sha256': body['segment_sha256'], 'trigger': trigger,
            'blocking': bool(blocking), 'publish_segments': bool(publish),
        }
        path = self.ctx.paths.anchor_spool / 'requests.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            lab_common.append_line_durable(fd, canonical_json(request), durable=True)
        finally:
            os.close(fd)
        self.pending_anchor = request
        self.anchor_requests[str(request['request_id'])] = request
        if trigger == 'decision':
            self.decision_anchor_failed = False
        self._anchor_t0 = time.monotonic()

    def _cumulative_bytes(self, current: int) -> int:
        total = 0
        for p in lab_eventlog.segment_paths(self.ctx.paths.events)[:-1]:
            total += p.stat().st_size
        return total + current

    def records_manifest_sha256(self) -> str:
        rec_dir = self.ctx.paths.records
        names = sorted(p.name for p in rec_dir.glob('*.json')) if rec_dir.exists() else []
        return sha256_canonical(names)

    def _anchor_request(self, request_id: object) -> dict | None:
        """The anchor request a receipt line answers, by its request id: this invocation's
        own, else read back from the durable ``anchor_spool/requests.jsonl`` (a previous
        invocation's request, answered after that invocation ended).  ``None`` when no
        request carries the id."""
        rid = str(request_id or '')
        if rid in self.anchor_requests:
            return self.anchor_requests[rid]
        path = self.ctx.paths.anchor_spool / 'requests.jsonl'
        try:
            rows, _ = read_spool_lines(path, 0)
        except (OSError, SpoolError):
            rows = []
        for row in rows:
            if row.get('request_id') is not None and row.get('anchor_seq') is not None:
                self.anchor_requests.setdefault(str(row['request_id']), dict(row))
        return self.anchor_requests.get(rid)

    def anchor_commit_check(self, commit: str, branch: str, request: Mapping) -> str | None:
        """:func:`anchor_commit_problem` for ``request``'s anchor in the anchor repository --
        the one ``lab_anchor`` commits in (``_runtime.repo``, else the repository root) -- and
        that anchor's own file object; a problem is kept in :attr:`findings`."""
        repo = Path(self.rt.get('repo') or lab_common.REPO_ROOT)
        anchor_path = self.ctx.paths.anchors / ('anchor_%d.json' % int(request['anchor_seq']))
        want = sha256_canonical(lab_common.anchor_file_object(self.ctx.trial, request))
        problem = anchor_commit_problem(repo, commit, branch, anchor_path, want)
        if problem is not None:
            self.findings.append('decision_commit_unbound:%s:%d'
                                 % (problem, int(request['anchor_seq'])))
        return problem

    def decision_receipted(self) -> bool:
        """Whether the logged decision is externally receipted on the chain as it stands
        (``lab_eventlog.decision_receipt``; root 00:22).  Once true it stays true."""
        if self.decision is None or self.log is None:
            return False
        if not self._decision_receipted:
            self._decision_receipted = lab_eventlog.decision_receipt(
                self.log.events, mock=self.tree_mock)['status'] == 'receipted'
        return self._decision_receipted

    def ingest_receipts(self) -> bool:
        """Turn each new line of the anchor process's receipt spool into EXACTLY ONE chain
        event: ``anchor_receipt``, ``anchor_failed`` or ``anchor_receipt_rejected``.

        The orchestrator remains the only writer of the chain (AD-2, PG-12).  Root f855e45:
        a line is attributed to an anchor only when its ``request_id`` is bound exactly to
        that anchor's durable request (:func:`judge_receipt_line`); an unknown, stale,
        malformed, duplicate or conflicting line creates NO ``anchor_receipt`` -- it is
        chained as ``anchor_receipt_rejected`` (digest and length of its bytes, which stay
        in the spool), resolves nothing, and leaves the pending anchor pending, so the
        existing timeout / recovery rules apply (``ANCHOR_BLOCK`` -> ``anchor_unavailable``).
        It never falls back to the newest anchor (8df2558 did) and never overwrites the line
        that resolved an anchor.  Root 3e18d69: an ``ok`` line answering a ``decision``
        request is its external receipt only with the evidence of
        :func:`decision_evidence_verdict` (MOCK tree: or no external claim at all).  A
        resumed invocation re-reads the spool from its start and REPLAYS the lines the chain
        already accounts for (one event each): nothing is chained twice.  A blocking
        ``decision`` request answered by an accepted ``ok: false`` line sets
        :attr:`decision_anchor_failed`.  Returns whether the pending request was resolved."""
        path = self.ctx.paths.anchor_spool / 'receipts.jsonl'
        lines, self.receipt_offset = read_receipt_lines(path, self.receipt_offset)
        got = False
        anchors: dict[int, Mapping] | None = None
        for _offset, raw in lines:
            index = self._receipt_lines_read
            self._receipt_lines_read += 1
            if index < len(self._receipt_replay):
                self._replay_receipt_line(self._receipt_replay[index], raw)
                continue
            if anchors is None:
                assert self.log is not None
                anchors = {int(e['body']['anchor_seq']): e['body']
                           for e in self.log.events if e['type'] == 'anchor'}
            verdict = judge_receipt_line(
                raw, trial=self.ctx.trial, request_of=self._anchor_request, anchors=anchors,
                resolved=self.anchor_resolved, resolving_sha=self.anchor_resolving_sha,
                newest_anchor_seq=self.anchor_seq, mock=self.tree_mock,
                anchor_branch=str((self.cfg.get('anchor') or {}).get('branch') or ''),
                commit_check=self.anchor_commit_check)
            if verdict['kind'] == 'rejected':
                self.append('anchor_receipt_rejected', verdict['body'], durable=True)
                self.receipts_rejected += 1
                continue
            anchor_seq = int(verdict['anchor_seq'])
            pending = self.pending_anchor
            answers_pending = (pending is not None
                               and verdict['request_id'] == pending['request_id'])
            self.anchor_resolved[anchor_seq] = verdict['kind']
            self.anchor_resolving_sha[anchor_seq] = verdict['raw_sha256']
            self.append(verdict['type'], verdict['body'], durable=True)
            if verdict['kind'] == 'receipt':
                self.receipts_obtained += 1
                if answers_pending and pending.get('trigger') == 'decision' \
                        and self.decision is not None and not self.decision_receipted():
                    # Cannot happen while this rule and lab_eventlog.decision_receipt agree;
                    # if they ever disagree, the blocking anchor is treated as failed (a
                    # pause, 6.4 row 26) rather than re-requested for ever by ANCHOR_BLOCK.
                    self.findings.append('decision_receipt_rule_disagreement:%d'
                                         % anchor_seq)
                    self.decision_anchor_failed = True
            elif answers_pending and pending.get('trigger') == 'decision':
                self.decision_anchor_failed = True
            if answers_pending:
                got = True
                self.pending_anchor = None
        return got

    def _replay_receipt_line(self, event: Mapping, raw: bytes) -> None:
        """A receipt line an earlier invocation already turned into ``event``: rebuild the
        line's digest for duplicate detection; a line that does not match its event (other
        bytes, another request id) is a finding, never re-chained."""
        digest = sha256_bytes(raw)
        body = event.get('body') or {}
        if event['type'] == 'anchor_receipt_rejected':
            if body.get('raw_sha256') != digest:
                self.findings.append('receipt_replay_mismatch:%d' % int(event['seq']))
            return
        try:
            rid = json.loads(raw.decode('utf-8')).get('request_id')
        except (UnicodeError, ValueError, AttributeError):
            rid = None
        if body.get('request_id') is not None and rid != body.get('request_id'):
            self.findings.append('receipt_replay_mismatch:%d' % int(event['seq']))
        self.anchor_resolving_sha.setdefault(int(body['anchor_seq']), digest)

    # -- dispatch -------------------------------------------------------------
    def build_job(self, *, arrival: int, attempt: int, pair: int | None,
                  position: int | None, arm: str, worker_index: int,
                  assignment_seq: int) -> dict:
        ctx = self.ctx
        trial_cfg = (self.cfg.get('trials') or {}).get(ctx.trial) or {}
        arm_cfg = trial_cfg.get(arm) or {}
        server_id = str(arm_cfg.get('server') or 'coder')
        spec = ctx.servers[server_id]
        execution = self._execution()
        uid = self.uid_of_arrival(arrival)
        job: dict = {
            'trial': ctx.trial,
            'inv': ctx.inv,
            'arrival': arrival,
            'attempt': attempt,
            'pair': pair or 0,
            'position': position or 0,
            'arm': arm,
            'workflow': str(arm_cfg.get('workflow') or 'single_shot'),
            'task_uid': uid,
            'server': {'server_id': server_id, 'base_url': spec.base_url,
                       'alias': spec.alias},
            'worker_index': worker_index,
            'sampling': dict(self.cfg.get('sampling') or {}),
            'limits': {
                'request_timeout_s': float(execution['request_timeout_s']),
                'max_connection_retries': int(execution.get('max_connection_retries', 2)),
                'server_recovery_s': float(execution.get('server_recovery_s', 180)),
                'max_lock_wait_s': float(execution.get('max_lock_wait_s', 120)),
            },
            'sandbox': dict(self.cfg.get('sandbox') or {}),
            'max_repair_rounds': int(self.cfg.get('max_repair_rounds', 2)),
            'golden': self.ctx.golden.get(server_id) or {},
            'config_sha256': str(self.rt.get('config_sha256') or ''),
            'freeze_bundle_sha256': ctx.bundle_sha,
            'paths': {
                'spool': tokenize_path(ctx.paths.spools / f'ep_{arrival}_{attempt}.jsonl'),
                'records': tokenize_path(ctx.paths.records),
                'requests': tokenize_path(ctx.paths.requests),
                # <HOST_WORK>/sandbox.lock, NOT tokenize_path(): a <WORK> token would
                # resolve against whatever checkout reads this job.
                'sandbox_lock': lab_common.tokenize_execution_lock(
                    lab_common.harness_config()),
                'tasks': str(self.rt.get('tasks_path') or ''),
                # protocol 5.5 promises "the used-seed set of earlier TRIALS of the
                # PROGRAM", so the registry is the one at the program work root; a per-trial
                # file could never carry it (execution review E2).
                'used_seeds': tokenize_path(self.seed_registry_path),
            },
            'assignment_seq': assignment_seq,
        }
        job['payload_sha256'] = sha256_canonical(canonical_job_payload(job))
        return job

    def uid_of_arrival(self, arrival: int) -> str:
        for slot in self.ctx.order:
            arrivals = list(slot['arrivals'])
            if arrival in arrivals:
                return str(slot['uids'][arrivals.index(arrival)])
        raise PreflightError(f'arrival {arrival} is not in the frozen order')

    def dispatch(self, att: Attempt) -> None:
        """Write and fsync the job file, spawn the worker, then ``episode_started``."""
        ctx = self.ctx
        ctx.paths.jobs.mkdir(parents=True, exist_ok=True)
        ctx.paths.spools.mkdir(parents=True, exist_ok=True)
        # protocol 5.5: the worker loads the used-seed set at start, so it must be on disk
        # and current before the process exists -- not after (execution review E2).
        self.persist_seed_registry()
        job_path = ctx.paths.jobs / f'job_{att.arrival}_{att.attempt}.json'
        try:
            job_sha = write_json_atomic(job_path, att.job, durable=True)
        except lab_common.WriteOnceViolation:
            # PG-7: this attempt never started, but an earlier invocation had already
            # written and fsynced its job file.  That file is the frozen input of this one
            # and only attempt; it is reused, never rewritten.
            att.job = json.loads(job_path.read_text(encoding='utf-8'))
            job_sha = sha256_file(job_path)
        att.pid = self.spawn(att, job_path)
        att.dispatched_mono = time.monotonic()
        self.attempts[att.arrival] = att
        self.live_workers.add(att.arrival)
        if att.arrival not in self.open_arrivals:
            self.open_arrivals.append(att.arrival)
        self.append('episode_started', {
            'arrival': att.arrival, 'pair': att.pair or 0, 'position': att.position or 0,
            'arm': att.arm, 'workflow': att.workflow, 'server_id': att.server_id,
            'worker_pid': int(att.pid), 'task_uid': att.task_uid,
            'assignment_seq': int(att.assignment_seq),
            'payload_sha256': str(att.job['payload_sha256']), 'job_sha256': job_sha,
            'enqueued_ns': time.time_ns(), 'dispatched_ns': time.time_ns(),
            'started_after_resume': bool(att.started_after_resume),
            'partner_concurrent': bool(att.partner_concurrent)})

    def spawn(self, att: Attempt, job_path: Path) -> int:
        """One OS process per episode (AD-1).  The orchestrator never imports the worker.

        The fixture refusal is here, BEFORE Popen, and not only in preflight: a
        configuration can reach a dispatch by a route that did not pass preflight,
        and this is the last point at which no process exists yet.
        """
        lab_common.assert_no_fixture(self.ctx.cfg, stage='episode spawn')
        cmd = list(self.rt.get('worker_cmd')
                   or [sys.executable, str(lab_common.HERE / 'lab_worker.py')])
        self.ctx.paths.logs.mkdir(parents=True, exist_ok=True)
        log_path = self.ctx.paths.logs / f'worker_{att.arrival}_{att.attempt}.log'
        handle = open(log_path, 'ab')
        proc = subprocess.Popen(cmd + ['--job', str(job_path)], stdout=handle,
                                stderr=handle, start_new_session=True,
                                cwd=str(lab_common.HERE))
        att.proc = proc
        att._log_handle = handle                            # type: ignore[attr-defined]
        return proc.pid

    def kill(self, att: Attempt) -> bool:
        """SIGKILL the worker's process group and confirm the exit.  Returns True only when
        the process is REAPED (its return code is then ``att.proc.returncode``), False when
        its exit could not be confirmed within :data:`KILL_CONFIRM_S` -- never swallowed:
        the caller records ``worker_resolved(alive_unresolved)`` and the trial owes
        ``trial_aborted(unresolved_worker)`` (repair contract EB5 item 1; the old ``kill``
        caught every exception of ``proc.wait`` and the reveal followed whether or not the
        process had exited, ``git show b049307:experiments/live_ab/lab_orchestrator.py``
        lines 1914-1928).  An attempt this invocation does not hold (``proc`` None, rebuilt on
        resume) is killed by pid only if
        :func:`probe_worker` says it is still that worker."""
        proc = att.proc
        if proc is None:
            state, _rc = kill_orphan_worker(att.pid, 'job_%d_%d.json' % (att.arrival,
                                                                          att.attempt))
            return state == 'killed_reaped'
        if proc.poll() is not None:
            return True
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=KILL_CONFIRM_S)
        except subprocess.TimeoutExpired:
            return False
        return proc.returncode is not None

    def finished(self, att: Attempt) -> Any:
        """The worker's return code once it has exited, ``None`` while it runs, and
        :data:`WORKER_UNKNOWN` when this invocation holds no process for it (an attempt
        rebuilt from the chain): that is unknown, never "exited" (repair contract EB5
        item 3)."""
        proc = att.proc
        if proc is None:
            return WORKER_UNKNOWN
        return proc.poll()


# ---------------------------------------------------------------------------
# ingest: spool lines become chain events
# ---------------------------------------------------------------------------
def _project(obj: Mapping, keys: Sequence[str], *, floats: Sequence[str] = ()) -> dict:
    out: dict = {}
    for key in keys:
        v = obj.get(key)
        if key in floats:
            out[key] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) \
                else 0.0
        else:
            out[key] = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) \
                else 0
    return out


def ingest_spool(world: World, att: Attempt) -> bool:
    """Read the new bytes of one attempt's spool and append the chain events they imply.

    ``call_started`` -> ``llm_request``; ``call_response`` -> ``llm_response``;
    ``call_error`` -> ``llm_error``; ``job_accepted`` -> ``job_accepted``;
    ``episode_final`` -> ``episode_revealed`` (durable).  ``sandbox_exec`` is folded into
    the reveal.  Returns True when a reveal was written."""
    lines, att.offset = read_spool_lines(att.spool, att.offset)
    revealed = False
    for row in lines:
        base = len(att.lines)
        if int(row.get('spool_seq', base)) != base:
            raise SpoolError(f'spool_seq gap on arrival {att.arrival}')
        att.lines.append(row)
        kind = row.get('kind')
        body = row.get('body') or {}
        if kind == 'call_started':
            att.calls[str(body['request_id'])] = dict(body)
            # E2: the seed is now used, whatever happens to the request afterwards.  Noted
            # from the SPOOL rather than from the chain event below, because the spool line
            # is durable before the POST and is seen even when this row was already
            # projected by an earlier invocation and is about to be skipped as a duplicate.
            if isinstance(body.get('seed'), int) and not isinstance(body.get('seed'), bool):
                world.note_seed(int(body['seed']))
        key = (str(kind), str(body.get('request_id') or ''))
        if key in att.logged:
            # already a chain event of an earlier invocation: the spool is evidence, the
            # chain is the chronology, and an event is never written twice.
            continue
        att.logged.add(key)
        if kind == 'job_accepted':
            world.append('job_accepted', {
                'arrival': att.arrival, 'attempt': att.attempt,
                'worker_pid': int(row.get('pid') or att.pid),
                'spool_offset': int(row['_offset']),
                'worker_t_wall_ns': int(row.get('t_wall_ns') or 0),
                'worker_t_mono_ns': int(row.get('t_mono_ns') or 0)})
        elif kind == 'call_started':
            world.append('llm_request', {
                'arrival': att.arrival, 'attempt': att.attempt,
                'call_index': int(body['call_index']),
                'request_id': str(body['request_id']),
                'server_id': att.server_id,
                't_c1_ns': int(body['t_c1_ns']), 't_send_ns': int(body['t_send_ns']),
                'kind': str(body['kind']), 'try_index': int(body['try_index']),
                'body_sha256': str(body['body_sha256']),
                'messages_sha256': str(body['messages_sha256']),
                'n_messages': int(body['n_messages']),
                'prompt_chars': int(body['prompt_chars']),
                'seed': int(body['seed']),
                'sampling_sent': dict(body.get('sampling_sent') or {}),
                'spool_offset': int(row['_offset']),
                # ARCHITECTURE 3.9 calls it body['fsync_ms'], section 5 fsync_ms_prev and
                # T14 spool_fsync_ms: one quantity, three names.  Section 5 is normative
                # for the spool, T14 for the chain, so the mapping is made here.
                'spool_fsync_ms': float(body.get('fsync_ms_prev') or 0.0),
                'partner_inflight': _partner_inflight(world, att),
                'recovered': bool(att.recovered_orphan)})
        elif kind == 'call_response':
            started = att.calls.get(str(body['request_id'])) or {}
            usage = dict(body.get('usage') or {})
            timings = dict(body.get('timings') or {})
            finish = str(body.get('finish_reason') or 'stop')
            world.append('llm_response', {
                'arrival': att.arrival, 'attempt': att.attempt,
                'call_index': int(started.get('call_index', body.get('call_index', 0))),
                'request_id': str(body['request_id']), 'server_id': att.server_id,
                't_c1_ns': int(started.get('t_c1_ns') or 0),
                't_send_ns': int(started.get('t_send_ns') or 0),
                'http_status': int(body.get('http_status') or 200),
                'model_matches_alias': bool(body.get('model_matches_alias', True)),
                'finish_reason': finish if finish in FINISH_REASONS else 'stop',
                'usage': _project(usage, USAGE_KEYS),
                'timings': _project(timings, TIMINGS_KEYS,
                                    floats=('prompt_ms', 'predicted_ms',
                                            'predicted_per_second')),
                'generation_settings_sha256': str(body['generation_settings_sha256']),
                'receipt_mismatch': [str(x) for x in (body.get('receipt_mismatch') or [])],
                'id_slot': int(body.get('id_slot') if body.get('id_slot') is not None
                               else -1),
                'truncated': bool(body.get('truncated')),
                'tokens_cached': int(usage.get('cached_tokens') or 0),
                'tokens_evaluated': int(timings.get('prompt_n') or 0),
                'tokens_predicted': int(timings.get('predicted_n') or 0),
                'rendered_prompt_sha256': str(body['rendered_prompt_sha256']),
                'content_sha256': str(body['content_sha256']),
                'client_seconds': float(body.get('client_seconds') or 0.0),
                't_recv_ns': int(body.get('t_recv_ns') or 0)})
        elif kind == 'call_error':
            started = att.calls.get(str(body['request_id'])) or {}
            world.append('llm_error', {
                'arrival': att.arrival, 'attempt': att.attempt,
                'call_index': int(started.get('call_index', 0)),
                'request_id': str(body['request_id']), 'server_id': att.server_id,
                't_c1_ns': int(started.get('t_c1_ns') or 0),
                't_send_ns': int(started.get('t_send_ns') or 0),
                'error_class': str(body['error_class']),
                'http_status': (int(body['http_status'])
                                if body.get('http_status') is not None else None),
                'error_sha256': str(body['error_sha256']),
                'client_seconds': float(body.get('client_seconds') or 0.0),
                'will_retry': bool(body.get('will_retry')),
                'usage_known': False, 'bracketing_scrapes': [],
                'bound_is_joint': False})
        elif kind == 'episode_final':
            if att.suppress_final:
                # protocol 14.5 item 3: the spool failed an orphan check, so its terminal
                # line is kept as evidence and is NEVER revealed from.  The attempt is
                # revealed as `interrupted` by the caller (6.4 row 11).
                continue
            reveal_from_final(world, att, row)
            revealed = True
        elif kind == 'worker_error':
            world.findings.append(f'worker_error:{body.get("stage")}')
    return revealed


def _partner_inflight(world: World, att: Attempt) -> bool:
    if att.pair is None:
        return False
    for arrival in world.open_arrivals:
        if arrival == att.arrival:
            continue
        other = world.attempts.get(arrival)
        if other is not None and other.pair == att.pair and not other.revealed:
            return True
    return False


def _overlap(world: World, att: Attempt) -> dict:
    partner = None
    if att.pair is not None:
        for arrival, other in world.attempts.items():
            if arrival != att.arrival and other.pair == att.pair:
                partner = other
                break
    if partner is None:
        return {'seconds_with_partner': 0.0, 'partner_arm': None,
                'partner_state_at_verify': None}
    end_self = att.ended_mono if att.ended_mono is not None else time.monotonic()
    end_partner = partner.ended_mono if partner.ended_mono is not None else time.monotonic()
    start = max(att.dispatched_mono, partner.dispatched_mono)
    stop = min(end_self, end_partner)
    state = 'revealed' if partner.revealed else (
        'running' if partner.proc is not None else 'not_started')
    return {'seconds_with_partner': float(round(max(0.0, stop - start), 6)),
            'partner_arm': partner.arm, 'partner_state_at_verify': state}


def reveal_from_final(world: World, att: Attempt, row: Mapping) -> None:
    body = dict(row.get('body') or {})
    outcome = dict(body['outcome'])
    att.ended_mono = time.monotonic()
    _reveal(world, att, outcome=outcome,
            record_sha256=str(body['record_sha256']),
            final_code_sha256=str(body.get('final_code_sha256')
                                  or sha256_text('')),
            verify_program_sha256=str(body.get('verify_program_sha256')
                                      or sha256_text('')),
            static_flags=[str(x) for x in (body.get('static_flags') or [])],
            hack_flags=[str(x) for x in (body.get('hack_flags') or [])],
            worker_t_start_ns=int(body.get('t_start_ns') or 0),
            worker_t_end_ns=int(body.get('t_end_ns') or 0),
            verify_seconds=float(body.get('verify_seconds') or 0.0))


def _reveal(world: World, att: Attempt, *, outcome: dict, record_sha256: str,
            final_code_sha256: str, verify_program_sha256: str, static_flags: list,
            hack_flags: list, worker_t_start_ns: int, worker_t_end_ns: int,
            verify_seconds: float) -> None:
    if att.revealed:
        return
    lock_wait = float(sum(float((r.get('body') or {}).get('lock_wait_s') or 0.0)
                          for r in att.lines if r.get('kind') == 'sandbox_exec'))
    ell = certified_ell_from_spool(att.lines)
    known = tokens_known_from_spool(att.lines)
    usage_complete, unknown_calls = usage_of_lines(att.lines)
    att.revealed = True
    att.ended_mono = att.ended_mono or time.monotonic()
    if att.arrival in world.open_arrivals:
        world.open_arrivals.remove(att.arrival)
    if att.arrival in world.down_overlap and not outcome.get('infra_flag'):
        # protocol 6.4 (P:1387-1388): "any overlap with a server_down interval" sets
        # infra_flag, and only the orchestrator knows it (lab_worker.outcome_from_record ORs
        # in the rest).  The arrival was in flight at a server_down of its server.
        outcome = dict(outcome, infra_flag=True)
    world.reveal_index += 1
    world.append('episode_revealed', {
        'arrival': att.arrival, 'pair': att.pair or 0, 'position': att.position or 0,
        'arm': att.arm, 'reveal_index': world.reveal_index - 1, 'outcome': outcome,
        'record_sha256': record_sha256, 'final_code_sha256': final_code_sha256,
        'verify_program_sha256': verify_program_sha256,
        'static_flags': static_flags, 'hack_flags': hack_flags,
        'worker_t_start_ns': worker_t_start_ns, 'worker_t_end_ns': worker_t_end_ns,
        'verify_seconds': float(verify_seconds),
        'sandbox_lock_wait_s': float(round(lock_wait, 6)),
        'overlap': _overlap(world, att), 'certified_ell': ell, 'tokens_known': known,
        'recovered_orphan': bool(att.recovered_orphan),
        'post_decision': bool(att.post_decision),
        'usage_complete': bool(usage_complete),
        'unknown_usage_calls': int(unknown_calls)}, durable=True)
    cls = outcome.get('error_class')
    if cls in TERMINAL_CLASSES:
        world.terminal_failures += 1
        world.consecutive_terminal += 1
    else:
        world.consecutive_terminal = 0
    if att.pair is not None:
        both = [a for a, o in world.attempts.items() if o.pair == att.pair]
        if len(both) == 2 and all(world.attempts[a].revealed for a in both):
            world.pairs_completed += 1


# ---------------------------------------------------------------------------
# the state machine (ARCHITECTURE_FINAL.md 7.1)
# ---------------------------------------------------------------------------
def step(state: State, ctx: RunContext, world: 'World') -> tuple[State, list]:
    """[pure-ish] One transition of the table in ARCHITECTURE_FINAL.md 7.1.

    Every side effect is performed through a ``World`` method, never through a module-level
    call, so the table can be driven against a substitute world."""
    before = world.log.seq if world.log is not None else 0
    nxt = _step(state, ctx, world)
    events = [] if world.log is None else world.log.events[before:]
    return nxt, events


def _step(state: State, ctx: RunContext, world: World) -> State:      # noqa: C901
    rt = world.rt
    if state == 'PREFLIGHT':
        return 'OPENING'

    if state == 'OPENING':
        existing = lab_eventlog.segment_paths(ctx.paths.events)
        # protocol 5.5 / execution review E2: rebuild the program-wide used-seed set from
        # every trial's spools before anything can be dispatched.  This runs on BOTH the
        # fresh-start and the resume branch, because the crash a resume follows is exactly
        # the case where the registry file can be behind the spools.
        world.load_seed_registry()
        if not existing:
            world.open_chain(create=True)
            world.append('trial_started', trial_started_body(ctx, world), durable=True)
            world.start_servers()
            world.scrape('trial_start')
            world.request_anchor('trial_started', blocking=True)
            return 'OPENING_WAIT'                            # type: ignore[return-value]
        world.open_chain(create=False)
        return resume_into(ctx, world)

    if state == 'OPENING_WAIT':                              # type: ignore[comparison-overlap]
        if world.ingest_receipts() or world.pending_anchor is None:
            return 'IDLE'
        if world.anchor_timed_out():
            world.pause_reason = 'anchor_unavailable'
            return 'PAUSED'
        return 'OPENING_WAIT'                                # type: ignore[return-value]

    if state == 'IDLE':
        # A held server whose process has already exited is answered (restart, cap, failure)
        # BEFORE a pair is enrolled onto it (EB1c: the C6 control showed a pair enrolled and
        # dispatched to an exited server that the 5 s health poll had not yet seen).
        world.supervise_exits()
        # Nothing is open here, so an outcome supervision owes is taken now, before any
        # enrollment (repair contract EB1: no new arrival after a failed restart or the cap).
        world.raise_pending()
        if world.pairs_enrolled >= world.max_pairs or world.unresolved_seen:
            # the horizon: no further enrollment is possible, so a deferred resume look is
            # written here and the frozen decide() runs on it (7.1 row 4a).  A worker that
            # could not be resolved ends enrollment too (repair contract EB5): the close
            # then refuses trial_ended by the resolution verdict.
            world.flush_looks()
            return 'DECIDED' if world.decision is not None else 'CLOSING'
        world.scrape('pair_boundary')
        world.enroll_next_pair()
        return 'ENROLLED'

    if state == 'ENROLLED':
        world.draw_coin()
        return 'COMMITTED'

    if state == 'COMMITTED':
        world.dispatch_pair()
        return 'DECIDED' if world.decision is not None else 'RUNNING'

    if state in ('RUNNING', 'PARTIAL'):
        world.pump()
        if world.decision is not None:
            return 'DECIDED'
        if not world.open_arrivals and not world.live_workers:
            # the pair boundary waits for both workers to be RESOLVED, not only revealed
            # (repair contract EB5: a live worker is a used send permit)
            return 'IDLE'
        if any(world.attempts[a].revealed for a in world.pair_arrivals()):
            return 'PARTIAL'
        return 'RUNNING'

    if state == 'DECIDED':
        if world.pending_anchor is None and not world.decision_anchor_done:
            world.request_anchor('decision', blocking=True)
            world.decision_anchor_done = True
        return 'DRAINING'

    if state == 'DRAINING':
        world.pump()
        if world.open_arrivals or world.live_workers:
            return 'DRAINING'
        return 'ANCHOR_BLOCK'

    if state == 'ANCHOR_BLOCK':
        # Protocol 9.1 steps 1-2 and 12.4 item 5: nothing post-switch before the decision's
        # CHAINED external receipt (root 21:14 ruling case (c); root 00:22).  The servers
        # stay supervised while the receipt is awaited (up to 30 minutes), so a restart the
        # cap forbids is recorded when it is required, not after the switch.
        if not rt.get('sim'):
            world.health_poll()
        world.ingest_receipts()
        assert world.decision is not None
        if world.decision_receipted():
            # A supervision outcome owed while the decision was provisional (a restart-cap
            # abort, a failed restart) is taken now, before any switch: the decision stands
            # at its original tau and the follow-up is truncated (ruling cases (b)/(c)).
            world.raise_pending()
            if world.decision['kind'] == 'horizon_no_decision':
                return 'CLOSING'
            world.write_traffic_switch()
            return 'POST_DECISION'
        if world.pending_anchor is None:
            if world.decision_anchor_failed:
                # 6.4 row 26 / 12.4 item 2: a blocking receipt that could not be obtained
                # (the anchor process retried for its full window) is a pause, never a
                # switch.  It used to fall through to traffic_switch with no receipt.
                world.pause_reason = 'anchor_unavailable'
                return 'PAUSED'
            # No decision anchor is outstanding in THIS invocation (a resumed invocation,
            # or a trigger that found another request pending): request it now (14.5).
            world.request_anchor('decision', blocking=True)
            world.decision_anchor_done = True
            return 'ANCHOR_BLOCK'
        if world.anchor_timed_out():
            world.pause_reason = 'anchor_unavailable'
            return 'PAUSED'
        return 'ANCHOR_BLOCK'

    if state == 'POST_DECISION':
        world.pump()
        if world.dispatch_follow_up():
            return 'POST_DECISION'
        if world.open_arrivals or world.live_workers:
            return 'POST_DECISION'
        return 'CLOSING'

    if state == 'CLOSING':
        # the resolution verdict may turn the close into trial_aborted(unresolved_worker)
        if world.close_trial('ended') == 'aborted':
            return 'ENDED_ABORTED'                           # type: ignore[return-value]
        return 'ENDED'

    if state == 'ABORTED':
        world.close_trial('aborted')
        return 'ENDED_ABORTED'                               # type: ignore[return-value]

    if state == 'PAUSED':
        world.write_pause()
        return 'ENDED_PAUSED'                                # type: ignore[return-value]

    return state


def trial_started_body(ctx: RunContext, world: World) -> dict:
    cfg = frozen_cfg(ctx.cfg)
    rt = runtime(ctx.cfg)
    monitor = cfg['monitor']
    arms: dict = {}
    for arm in lab_common.ARMS:
        arm_cfg = (cfg['trials'][ctx.trial]).get(arm) or {}
        server_id = str(arm_cfg.get('server') or 'coder')
        spec = ctx.servers[server_id]
        arms[arm] = {'workflow': str(arm_cfg['workflow']), 'server_id': server_id,
                     'alias': spec.alias, 'gguf_sha256': spec.gguf_sha256}
    return {
        'freeze_bundle_sha256': ctx.bundle_sha,
        'program_head': str(rt.get('program_head') or '0' * 64),
        'config_sha256': str(rt.get('config_sha256') or ''),
        'rule_block_sha256': lab_common.rule_block_sha256(cfg),
        'order_sha256': str(rt.get('order_sha256') or ''),
        'roster_sha256': str(rt.get('roster_sha256') or ''),
        'task_content_sha256': str(rt.get('task_content_sha256') or ''),
        'n_pairs_max': int(ctx.mc.n_max),
        'arms': arms,
        'monitor': {
            'rule_id': str(cfg['rule_id']),
            'construction': str(monitor['construction']),
            'alpha_gate': float(monitor['alpha_gate']), 'rho': float(monitor['rho']),
            'delta': float(monitor['delta']), 'n_min': int(monitor['n_min']),
            'variance_process': str(monitor['variance_process']),
            'clip': [float(x) for x in monitor['clip']],
            'prefix': str(monitor['prefix']), 'retention': bool(monitor['retention']),
            'running_intersection': bool(monitor['running_intersection']),
            'harm_tail': str(monitor['harm_tail']),
            'tiers': [{'name': str(t['name']), 'higher_better': bool(t['higher_better']),
                       'relative_tolerance': float(t['relative_tolerance'])}
                      for t in cfg['hierarchy']],
            'eligibility': str(cfg['eligibility_rule']),
        },
        'coin': {'source': str(cfg['coin']['source']), 'bit': str(cfg['coin']['bit']),
                 'map': str(cfg['coin']['map']), 'unit': str(cfg['coin']['unit'])},
        'seed_rule': dict(cfg['seed_rule']),
        'failure_rules_sha256': str(rt.get('failure_rules_sha256')
                                    or sha256_canonical(cfg.get('plumbing_fail_conditions'))),
        'harness_file_sha256': dict(rt.get('harness_file_sha256')
                                    or lab_common.harness_file_hashes()),
        'reused_file_sha256': dict(rt.get('reused_file_sha256') or _reused_hashes()),
        'winstats_sha256': sha256_file(lab_common.SRC_DIR / 'winstats.py'),
        'sandbox_profile_sha256': str(cfg['sandbox'].get('profile_sha256')
                                      or sha256_text('sandbox-profile-not-pinned')),
        # The frozen digests as recorded, never a stand-in: the fallback that wrote
        # sha256_text(<server id>) for a null digest is gone (repair contract EB1 item 7).
        # Preflight refuses a null digest for every server this trial starts; a server the
        # trial does not start and whose digest is null is left out, not invented.
        'golden_props_sha256': {k: str(v)
                                for k, v in (cfg['receipt']['golden_props_sha256']).items()
                                if v is not None},
        'golden_generation_settings_sha256': {
            k: str(v)
            for k, v in (cfg['receipt']['golden_generation_settings_sha256']).items()
            if v is not None},
        'hardware': lab_common.hardware_info(),
        'packages': lab_common.package_versions(),
        'llama_cpp_commit_sha256': sha256_text(str(cfg['llama_cpp']['commit'])),
        'refreezes_in_force': list(rt.get('refreezes_in_force') or []),
    }


def _reused_hashes() -> dict:
    out: dict = {}
    for name in lab_common.REUSED_FILES:
        p = lab_common.LS_DIR / name
        if p.exists():
            out[name] = sha256_file(p)
    return out


# ---------------------------------------------------------------------------
# World: the transitions that need more than a few lines
# ---------------------------------------------------------------------------
def _install(cls):
    """Attach the long transition methods to :class:`World` without a 900-line class."""
    for name, fn in list(globals().items()):
        if name.startswith('_w_'):
            setattr(cls, name[3:], fn)
    return cls


def _w_anchor_timed_out(self: World) -> bool:
    limit = float((self.cfg.get('anchor') or {}).get('blocking_wait_minutes', 30)) * 60.0
    limit = float(self.rt.get('blocking_wait_s', limit))
    return (time.monotonic() - self._anchor_t0) > limit if self.pending_anchor else False


def _w_enroll_next_pair(self: World) -> None:
    slot = self.ctx.order[self.pairs_enrolled]
    self.flush_looks()
    self.append('pair_enrolled', {
        'pair': int(slot['pair']), 'stratum': str(slot['stratum']),
        'arrivals': [int(a) for a in slot['arrivals']],
        'task_uids': [str(u) for u in slot['uids']],
        'phase': 'randomizing', 're_enrolled': False}, durable=True)
    self._current_pair = int(slot['pair'])


def _w_reenroll_pair(self: World, pair: int) -> None:
    slot = self.ctx.order[pair - 1]
    self.append('pair_enrolled', {
        'pair': int(slot['pair']), 'stratum': str(slot['stratum']),
        'arrivals': [int(a) for a in slot['arrivals']],
        'task_uids': [str(u) for u in slot['uids']],
        'phase': 'randomizing', 're_enrolled': True}, durable=True)
    self._current_pair = int(slot['pair'])


def _w_draw_coin(self: World) -> None:
    """protocol 4.2: the coin is drawn and fsynced BEFORE either episode is dispatched."""
    pair = self._current_pair
    slot = self.ctx.order[pair - 1]
    coin, assigned, event = lab_coin.draw_and_commit(self.log, slot)
    self._assignment = {int(k): str(v) for k, v in assigned.items()}
    self._assignment_seq = int(event['seq'])
    self.pairs_enrolled += 1
    self.evaluate()                       # the coin is a consumed event: the enroll look


def _w_pair_arrivals(self: World) -> list:
    pair = getattr(self, '_current_pair', None)
    if pair is None:
        return []
    return [a for a, att in self.attempts.items() if att.pair == pair]


def _w_dispatch_pair(self: World) -> dict | None:
    pair = self._current_pair
    slot = self.ctx.order[pair - 1]
    for position, arrival in enumerate(slot['arrivals'], start=1):
        arm = self._assignment[int(arrival)]
        worker_index = position - 1
        job = self.build_job(arrival=int(arrival), attempt=1, pair=pair,
                             position=position, arm=arm, worker_index=worker_index,
                             assignment_seq=self._assignment_seq)
        att = Attempt(arrival=int(arrival), attempt=1, pair=pair, position=position,
                      arm=arm, workflow=str(job['workflow']),
                      server_id=str(job['server']['server_id']),
                      task_uid=str(job['task_uid']),
                      spool=self.ctx.paths.spools / f'ep_{arrival}_1.jsonl', job=job,
                      assignment_seq=self._assignment_seq, post_decision=False,
                      worker_index=worker_index)
        self.pair_of_arrival[int(arrival)] = pair
        self.dispatch(att)
    return None


def _w_take_decision(self: World, decision: Any) -> dict | None:
    """Append the ``decision`` event immediately after the ``monitor_update`` it quotes."""
    if decision is None or self.decision is not None:
        return None
    if isinstance(decision, dict):
        kind, n = decision['kind'], decision['n']
        band_h, band_s = decision['band_h'], decision['band_s']
    else:
        kind, n = decision.kind, decision.n
        band_h, band_s = decision.band_h, decision.band_s
    assert self.log is not None
    prev = self.log.events[-1]
    if prev['type'] != 'monitor_update':
        raise MonitorError('a decision must immediately follow its monitor_update')
    inflight = [{'arrival': a, 'arm': self.attempts[a].arm}
                for a in sorted(self.open_arrivals) if a in self.attempts]
    body = {
        'kind': kind, 'rule_id': lab_monitor.RULE_ID, 'n': int(n),
        'monitor_seq': int(prev['seq']), 'radius': float(band_h.radius),
        'L_h': float(band_h.lo), 'U_h': float(band_h.hi), 'L_s': float(band_s.lo),
        'U_s': float(band_s.hi), 'delta': float(self.ctx.mc.delta),
        'alpha_gate': float(self.ctx.mc.alpha_gate), 'inflight': inflight,
        'next_unassigned_arrival': self.next_unassigned_arrival(),
        'decided_on_resume': bool(getattr(self, '_resumed', False)),
    }
    ev = self.append('decision', body, durable=True)
    self.decision = body
    self.decision_seq = int(ev['seq'])
    self.decided_arm = ('candidate' if kind == 'deploy_candidate'
                        else 'incumbent' if kind == 'harm_keep_incumbent' else None)
    self.phase = 'draining'
    return body


def _w_next_unassigned_arrival(self: World) -> int | None:
    for slot in self.ctx.order:
        for arrival in slot['arrivals']:
            if int(arrival) not in self.attempts:
                return int(arrival)
    return None


def _w_pump(self: World) -> dict | None:
    """Reap workers, ingest spools, poll health, enforce the hard cap, take the look."""
    self.health_poll()
    self.ingest_receipts()
    self.pump_attempts()
    # E2: flush the used-seed registry as soon as this pump saw new seeds, not only at the
    # next dispatch.  Without this the LAST pair's seeds never reach the file -- the trial
    # ends with no further dispatch -- and the next trial of the program would start from a
    # registry that is missing them.  The reconstruction at that trial's start would still
    # recover them from the spools, but a file that disagrees with the spools is exactly the
    # kind of quiet staleness this repair exists to remove.  The call is a no-op unless the
    # set actually grew, so a 50 ms poll does not rewrite the file.
    self.persist_seed_registry()
    # While supervision owes an abort the pump only drains: no other automatic abort may
    # pre-empt it, so the reason the chain ends with is the one supervision determined
    # (trial_aborted(server_restart_cap) exists iff the cap bound -- verifier
    # server.lifecycle).  An owed PAUSE does not suspend the automatic aborts: an abort
    # outranks a pause.
    if self.pending_abort is None:
        self._auto_abort()
    self.raise_pending()
    return self.decision


def _job_name(att: Attempt) -> str:
    return 'job_%d_%d.json' % (int(att.arrival), int(att.attempt))


def _w_pump_attempts(self: World) -> None:
    """One pass over the attempts: ingest every open spool, reveal from a final line, reap
    an exited worker, enforce the hard cap -- and resolve every worker (repair contract EB5).

    * A worker seen to have exited is recorded ``worker_resolved(exited, rc)`` BEFORE the
      ingest of its last lines and before a ``worker_died`` reveal.
    * At the hard cap the worker is killed and its exit confirmed (``kill`` returns whether
      it was reaped) and ``worker_resolved(killed_reaped | alive_unresolved)`` is written
      BEFORE the ``episode_timeout`` reveal.
    * A spool that cannot be read (``SpoolError``) no longer reveals ``interrupted`` over a
      live worker: the worker is killed and reaped first (EB5 item 1;
      ``git show b049307:experiments/live_ab/lab_orchestrator.py`` lines 2474-2475 revealed it via
      ``_interrupt`` with no kill at all).
    * A worker whose attempt is already revealed (``episode_final`` is written just before
      the process exits) is still polled until its exit is confirmed (:meth:`poll_resolutions`);
      it used to be skipped and never polled again (b049307 lines 2477-2478).
    Never raises ``SpoolError``."""
    for arrival in list(self.open_arrivals):
        att = self.attempts[arrival]
        if att.revealed:
            continue
        try:
            ingest_spool(self, att)
        except SpoolError:
            self.interrupt_unreadable(att)
            continue
        if att.revealed:
            continue
        ended = self._exit_state(att)
        if ended is not None:
            if att.resolution is None:
                self.resolve_worker(att, *ended)
            try:
                ingest_spool(self, att)
            except SpoolError:
                self._interrupt(att)
                continue
            if not att.revealed:
                self._terminal(att, 'worker_died' if ended[0] == 'exited' else 'interrupted')
        elif (time.monotonic() - att.dispatched_mono) > self.hard_cap_s:
            if att.resolution is None:
                self.kill_and_resolve(att)
            try:
                ingest_spool(self, att)
            except SpoolError:
                self._interrupt(att)
                continue
            if not att.revealed:
                self._terminal(att, 'episode_timeout')
    self.poll_resolutions()


def _w_interrupt_unreadable(self: World, att: Attempt) -> None:
    """A spool that cannot be read (``SpoolError``): kill the worker and confirm its exit,
    THEN reveal the attempt ``interrupted`` (repair contract EB5 item 1).  The worker is
    killed because its spool can no longer be trusted as the record of what it sends; a
    worker left running would keep POSTing after its reveal (control C3)."""
    if att.resolution is None:
        self.kill_and_resolve(att)
    self._interrupt(att)


def _w__exit_state(self: World, att: Attempt) -> tuple[str, int | None] | None:
    """``('exited', rc)`` once the worker has exited, ``None`` while it runs.  For an attempt
    this invocation holds no process for (``finished`` is :data:`WORKER_UNKNOWN`) the pid and
    the process identity decide (:func:`probe_worker`): gone -> ``('exited', None)``, a ps
    that cannot answer -> ``('liveness_unknown', None)``, still that worker -> ``None``."""
    rc = self.finished(att)
    if rc is WORKER_UNKNOWN:
        seen = probe_worker(att.pid, _job_name(att))
        if seen == 'gone':
            return 'exited', None
        if seen == 'unknown':
            return 'liveness_unknown', None
        return None
    if rc is None:
        return None
    return 'exited', int(rc)


def _w_poll_resolutions(self: World) -> None:
    """Resolve every worker whose attempt is already revealed: poll it until its exit is
    confirmed, and kill it at the hard cap.  Lines it spools after its reveal (a late call)
    are still ingested -- they are chain evidence and stay in the exposure ledger -- up to the
    moment it is resolved."""
    for arrival in sorted(self.live_workers):
        att = self.attempts.get(arrival)
        if att is None or not att.revealed or att.resolution is not None:
            continue
        try:
            ingest_spool(self, att)
        except SpoolError:
            self.kill_and_resolve(att)
            continue
        ended = self._exit_state(att)
        if ended is not None:
            self.resolve_worker(att, *ended)
        elif (time.monotonic() - att.dispatched_mono) > self.hard_cap_s:
            self.kill_and_resolve(att)
        else:
            continue
        try:
            ingest_spool(self, att)
        except SpoolError:
            self.findings.append('late_spool_unreadable:%d' % arrival)


def _w_resolve_worker(self: World, att: Attempt, state: str,
                      returncode: int | None) -> dict:
    """Append ``worker_resolved`` (durable) for ``att`` with the spool's size and digest AT
    this moment (the offset the deposit is sealed to) and stop treating the worker as a live
    permit.  A state that does not resolve the worker (``alive_unresolved`` /
    ``liveness_unknown``) is final: nothing observed later turns it into a resolution
    (:func:`phase_resolution_verdict` fails an attempt with ANY unresolved record -- root
    21:14: "killing/reaping does not turn unknown historical usage into zero"), the worker is
    no longer polled, and :attr:`unresolved_seen` stops all further enrollment and dispatch:
    a phase with a live or unaccounted worker is incomplete (root 20:40 item 3, 21:15 item
    3), and the close writes ``trial_aborted(unresolved_worker)``."""
    body = self._resolution_body(att.arrival, att.attempt, att.pid, state, returncode,
                                 att.spool)
    self.append('worker_resolved', body, durable=True)
    att.resolution = body
    self.live_workers.discard(att.arrival)
    if state not in RESOLVED_WORKER_STATES:
        self.unresolved_seen = True
    return body


def _w__resolution_body(self: World, arrival: int, attempt: int, pid: int, state: str,
                        returncode: int | None, spool: Path) -> dict:
    # an unreadable spool is recorded unread (null, null): never the size and digest of an
    # empty file (review of 988baf7, reviewer 1) -- the verdict fails it ``spool_unreadable``
    obs = spool_observation(spool)
    readable = isinstance(obs['bytes'], int) and obs['sha256'] is not None
    return {'arrival': int(arrival), 'attempt': int(attempt), 'pid': int(pid),
            'state': str(state),
            'returncode': None if returncode is None else int(returncode),
            'spool_bytes_at_resolution': int(obs['bytes']) if readable else None,
            'spool_sha256_at_resolution': str(obs['sha256']) if readable else None}


def _w_kill_and_resolve(self: World, att: Attempt) -> dict:
    """Kill the worker (unless it has already exited) and record what was confirmed."""
    ended = self._exit_state(att)
    if ended is not None and ended[0] == 'exited':
        return self.resolve_worker(att, 'exited', ended[1])
    reaped = self.kill(att)
    rc = (att.proc.returncode if reaped and att.proc is not None
          and att.proc.returncode is not None else None)
    return self.resolve_worker(att, 'killed_reaped' if reaped else 'alive_unresolved', rc)


def _w_drain_workers(self: World, *, reveal: bool) -> None:
    """The BOUNDED drain an abort and a pause run first (repair contract EB5 item 2; ARCHITECTURE
    7.1 rows 24b/27, "let in-flight episodes finish into their spools";
    ``git show b049307:experiments/live_ab/lab_orchestrator.py`` lines 2266-2273 and 2606-2625:
    abort and pause used to close at once, with workers still running and their spools still
    growing).

    The attempts are pumped until every worker this invocation spawned is resolved -- the
    hard-cap kill still applies, and a kill whose exit cannot be confirmed resolves the attempt
    as ``alive_unresolved`` -- so the loop ends at the latest one hard cap plus
    :data:`KILL_CONFIRM_S` after the last dispatch.  ``reveal`` (the abort, and the close of an
    ended trial): open attempts are ingested and revealed as the pump does, the looks they
    produce are logged and take no decision (:attr:`closing`), and neither an automatic abort
    nor an owed outcome is raised from inside the drain.  Not ``reveal`` (a pause): the
    processes are only waited for (or killed at the cap); their spools are read by the resumed
    invocation, which reveals them (the monitor may be what paused the trial, so no look is
    written here)."""
    while True:
        waiting = [a for a in self.open_arrivals
                   if a in self.attempts and not self.attempts[a].revealed] if reveal else []
        if not waiting and not self.live_workers:
            return
        if reveal:
            try:
                self.pump_attempts()
            except (MonitorError, PauseTrial, lab_common.EnclosureError) as exc:
                self.findings.append('drain_look:%s' % type(exc).__name__)
        else:
            for arrival in sorted(self.live_workers):
                att = self.attempts[arrival]
                ended = self._exit_state(att)
                if ended is not None:
                    self.resolve_worker(att, *ended)
                elif (time.monotonic() - att.dispatched_mono) > self.hard_cap_s:
                    self.kill_and_resolve(att)
        time.sleep(max(0.005, self.poll_s))


def server_idle_observation(base_url: str, *, timeout: float = 5.0) -> dict:
    """One observation of a server's in-flight work: ``/metrics`` ``requests_processing``
    (``lab_server.metrics``) and the busy slots of ``/slots`` (``lab_server.health``), each
    ``None`` when it could not be read -- an unread value is never 0 (``slots_read``)."""
    got = lab_server.metrics(base_url, timeout=timeout, tries=1)
    processing = got.get('requests_processing') if got.get('ok') else None
    if not (isinstance(processing, int) and not isinstance(processing, bool)):
        processing = None
    seen = lab_server.health(base_url, timeout=timeout)
    busy = seen.get('slots_busy') if (seen.get('ok') and seen.get('slots_read', True)) \
        else None
    if not (isinstance(busy, int) and not isinstance(busy, bool)):
        busy = None
    return {'observed': processing is not None and busy is not None,
            'requests_processing': processing, 'slots_busy': busy}


def _w_observe_servers_idle(self: World) -> dict:
    """After every client is resolved: each server this invocation still holds, observed until
    it is idle (``requests_processing == 0`` and no busy slot) or :attr:`idle_wait_s` has
    passed (repair contract EB5 item 4; control C1 of ``tests_eb5_resolution``: a killed
    client's request may still be decoding on the server).  A held server whose process has
    exited holds no request and is not held.  A simulated run's servers are the simulated
    counters (idle by construction)."""
    out: dict = {}
    deadline = time.monotonic() + max(0.0, float(self.idle_wait_s))
    for server_id, spec in sorted(self.ctx.servers.items()):
        if self.rt.get('sim'):
            out[server_id] = {'held': False, 'observed': True, 'requests_processing': 0,
                              'slots_busy': 0}
            continue
        pid = int(self.server_pids.get(server_id) or 0)
        held = bool(pid)
        if held:
            try:
                held = lab_server.exit_status(pid) is None
            except lab_common.LabError:
                held = True
        obs = {'held': held, 'observed': False, 'requests_processing': None,
               'slots_busy': None}
        while held:
            got = server_idle_observation(spec.base_url)
            if got['observed']:
                obs.update(got)
                if got['requests_processing'] == 0 and got['slots_busy'] == 0:
                    break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.2)
        out[server_id] = obs
    return out


def _w__terminal(self: World, att: Attempt, error_class: str) -> None:
    """An attempt that never returned (protocol 6.4 rows 10, 10b, 11, 11c-11e, 18).

    There is no ``run_episode`` record, so the orchestrator deposits its own reconstruction
    under the same content-addressed scheme and names it in the reveal: the deposit is
    complete, the outcome re-derives from the spool, and the file says in its first key
    that it was reconstructed and is not a worker record."""
    outcome = terminal_outcome(att.lines, error_class, hard_cap_s=self.hard_cap_s)
    record = {
        'reconstructed_by': 'lab_orchestrator',
        'terminal_failure': True,
        'trial': self.ctx.trial,
        'arrival': int(att.arrival),
        'attempt': int(att.attempt),
        'arm': att.arm,
        'error_class': error_class,
        'outcome': outcome,
        'certified_ell': certified_ell_from_spool(att.lines),
        'tokens_known': tokens_known_from_spool(att.lines),
        'spool_sha256': sha256_canonical(
            [{k: v for k, v in row.items() if k != '_offset'} for row in att.lines]),
    }
    digest = sha256_canonical(record)
    self.ctx.paths.records.mkdir(parents=True, exist_ok=True)
    write_json_atomic(self.ctx.paths.records / f'{digest}.json', record, durable=True)
    _reveal(self, att, outcome=outcome, record_sha256=digest,
            final_code_sha256=sha256_text(''), verify_program_sha256=sha256_text(''),
            static_flags=[], hack_flags=[], worker_t_start_ns=0, worker_t_end_ns=0,
            verify_seconds=0.0)


def _w__interrupt(self: World, att: Attempt) -> None:
    self._terminal(att, 'interrupted')


def _w__auto_abort(self: World) -> None:
    """The deterministic aborts of protocol 6.4 (rows 12, 13 and the ten-failure rule)."""
    if self.consecutive_terminal >= self.failure_limit:
        raise AbortTrial('infrastructure')
    assert self.log is not None
    for ev in self.log.events[self._abort_cursor:]:
        if ev['type'] == 'llm_response' and ev['body'].get('receipt_mismatch'):
            self._abort_cursor = len(self.log.events)
            raise AbortTrial('receipt_mismatch')
        if ev['type'] == 'episode_revealed' \
                and ev['body']['outcome'].get('error_class') == 'receipt_mismatch':
            self._abort_cursor = len(self.log.events)
            raise AbortTrial('receipt_mismatch')
        if ev['type'] == 'server_restarted' and not ev['body'].get('props_equal_previous',
                                                                  True):
            self._abort_cursor = len(self.log.events)
            raise AbortTrial('server_identity')
    self._abort_cursor = len(self.log.events)


def _w_write_traffic_switch(self: World) -> None:
    assert self.decision is not None and self.decision_seq is not None
    arm = self.decided_arm or 'incumbent'
    arrival = self.next_unassigned_arrival()
    wait_ms = int((time.monotonic() - self._anchor_t0) * 1000.0)
    self.append('traffic_switch', {
        'decision_seq': int(self.decision_seq), 'arm': arm,
        'effective_from_arrival': int(arrival or 0), 'anchor_wait_ms': wait_ms,
        'switch_latency_ms': wait_ms}, durable=True)
    self.phase = 'post_decision'


def _w_dispatch_follow_up(self: World) -> bool:
    """The work-conserving follow-up cohort (protocol 5.1, 9.3): one arrival at a time to
    whichever worker is free, all under the decided arm.  No pair, no coin, no look."""
    workers = int((self.cfg.get('execution') or {}).get('workers', 2))
    if self.pending_abort is not None or self.pending_pause is not None:
        return False                  # supervision owes an abort or a pause: drain only
    if self.unresolved_seen:
        return False                  # EB5: an unresolved worker ends all dispatch
    if len(set(self.open_arrivals) | self.live_workers) >= workers:
        return False                  # a live worker holds its slot until it is resolved
    arrival = self.next_unassigned_arrival()
    if arrival is None:
        return False
    if self.post_decision_dispatched and self.post_decision_dispatched % 50 == 0:
        if self.open_arrivals or self.live_workers:
            return False                              # drain before the quiescent scrape
        # The cohort of 50 has drained -- nothing is open -- so this scrape IS quiescent;
        # it is taken before the next arrival is dispatched.  (It used to be taken right
        # after dispatching the 50th arrival, with that arrival still open: EB1 fix,
        # reviewer 1 finding 4.)  A crash between this scrape and the next dispatch repeats
        # it on resume, which is one more exact scrape, never a wrong one.
        self.scrape('quiescent')
    arm = self.decided_arm or 'incumbent'
    ev = self.append('arm_assigned_by_decision', {
        'arrival': int(arrival), 'arm': arm,
        'decision_seq': int(self.decision_seq or 0)}, durable=True)
    used = {a.worker_index for a in self.attempts.values()
            if a.arrival in self.open_arrivals}
    worker_index = 0 if 0 not in used else 1
    job = self.build_job(arrival=int(arrival), attempt=1, pair=None, position=None,
                         arm=arm, worker_index=worker_index,
                         assignment_seq=int(ev['seq']))
    att = Attempt(arrival=int(arrival), attempt=1, pair=None, position=None, arm=arm,
                  workflow=str(job['workflow']),
                  server_id=str(job['server']['server_id']),
                  task_uid=str(job['task_uid']),
                  spool=self.ctx.paths.spools / f'ep_{arrival}_1.jsonl', job=job,
                  assignment_seq=int(ev['seq']), post_decision=True,
                  worker_index=worker_index)
    self.dispatch(att)
    self.post_decision_dispatched += 1
    return True


def _w_close_trial(self: World, status: str) -> str:
    """CLOSING / ABORTED (7.1 rows 26 and 27), with the worker resolution of repair contract
    EB5 (root 20:40 item 3; root 21:15 item 3, "Unresolved workers/usage make the phase
    incomplete, not zero"):

    1. the bounded drain (:meth:`drain_workers`): every open attempt is revealed and every
       worker this invocation spawned is resolved, or recorded ``alive_unresolved`` when its
       kill could not be confirmed -- an abort no longer closes over running workers;
    2. every server still held is observed until idle (:meth:`observe_servers_idle`);
    3. scrape, reconciliation, the exposure ledger, the server stops as before; the deposit
       is sealed to the recorded resolution offsets (:meth:`seal_deposit`);
    4. :func:`phase_resolution_verdict` over the chain, the seal's spool observations and the
       server observation.  If it does not PASS there is NO ``trial_ended``: the terminal
       record is ``trial_aborted(unresolved_worker)``, its ``resolution`` lists every
       unresolved attempt and unfinished call, and names the abort reason it superseded.
       Every terminal record carries its ``resolution`` (verifier ``workers.resolved``).

    Returns the status actually written (``'ended'`` or ``'aborted'``)."""
    assert self.log is not None
    self.closing = True
    self.drain_workers(reveal=True)
    self.flush_looks()
    server_obs = self.observe_servers_idle()
    self.scrape('trial_end')
    self.reconcile()
    ledger = exposure_recount(self.log.events)
    write_json_atomic(self.ctx.paths.results / 'exposure_ledger.json', ledger,
                      durable=True)
    if self.rt.get('sim'):
        # the simulated servers were never started; their stop records say pid 0
        for server_id in sorted(self.ctx.servers):
            self.append('server_stopped', {
                'server_id': server_id, 'pid': 0, 'returncode': None, 'seconds': 0.0},
                durable=True)
    else:
        # Only servers this invocation actually started and still holds are stopped and
        # recorded; a server whose start failed was stopped by lab_server.start and is
        # described by its server_start_failed record, and one stopped already is not
        # stopped (or recorded) twice.
        self.stop_servers()
    spool_stats = self.seal_deposit()
    resolution = phase_resolution_verdict(self.log.events, spool_stats, server_obs)
    if resolution['verdict'] != 'PASS':
        resolution['superseded_reason'] = (
            self.abort_reason if status == 'aborted'
            and self.abort_reason != UNRESOLVED_WORKER_REASON else None)
        status = 'aborted'
        self.abort_reason = UNRESOLVED_WORKER_REASON
    self.append('invocation_ended', {
        'status': 'ended' if status == 'ended' else 'aborted',
        'counts': {'pairs_enrolled': self.pairs_enrolled,
                   'pairs_completed': self.pairs_completed,
                   'looks': self.looks_written,
                   'terminal_failures': self.terminal_failures}}, durable=True)
    body = {
        'status': status,
        'reason': self.abort_reason if status == 'aborted' else None,
        'phase': self.phase if self.phase in ('randomizing', 'draining', 'post_decision')
                 else 'randomizing',
        'exposure_ledger': ledger,
        'reconciliation_totals': dict(self.usage_sum),
        'terminal_failures_by_arm': self._terminal_by_arm(),
        'n_torn_recoveries': sum(1 for e in self.log.events
                                 if e['type'] == 'log_recovery'),
        'longest_unreceipted_span_s': 0.0,
        'what_was_known': self.what_was_known(),
        'final_head': self.log.head,
        # Root 21:14 ruling: the restart-cap case, the decision's receipt state and the
        # cap's effect on completion and exposure (arrivals not run, follow-up not run),
        # over the chain before this record; the verifier's server.lifecycle recounts it.
        'completion': lab_eventlog.completion_record(
            self.log.events, [int(a) for slot in self.ctx.order for a in slot['arrivals']],
            self.restart_cap, mock=self.tree_mock),
        # repair contract EB5: the resolution verdict taken before this record
        'resolution': resolution,
    }
    self.append('trial_ended' if status == 'ended' else 'trial_aborted', body,
                durable=True)
    self.request_anchor('trial_ended' if status == 'ended' else 'trial_aborted',
                        blocking=True)
    self.wait_for_receipt()
    return status


def _w__terminal_by_arm(self: World) -> dict:
    out = {arm: 0 for arm in lab_common.ARMS}
    assert self.log is not None
    for ev in self.log.events:
        if ev['type'] == 'episode_revealed' \
                and ev['body']['outcome'].get('error_class') in TERMINAL_CLASSES:
            out[ev['body']['arm']] = out.get(ev['body']['arm'], 0) + 1
    return out


def _w_reconcile(self: World) -> None:
    """The ``usage_reconciliation`` records of the trial (PG-10; repair contract EB1 item 3):
    one per server PROCESS, from :func:`reconciliation_windows` over the chain as it stands
    -- the SERVER_SMOKE usage of every start and restart is in its window, and a window a
    restart cut is ``counters_lost`` rather than a residual.  ``usage_sum`` (the trial's
    ``reconciliation_totals``) is :func:`client_usage_totals`: smoke plus responses."""
    assert self.log is not None
    events = list(self.log.events)
    last = int(self.log.seq - 1)
    self.usage_sum = client_usage_totals(events, self.ctx.servers)
    for body in reconciliation_windows(events, self.ctx.servers, last_seq=last):
        self.append('usage_reconciliation', body, durable=True)


def _w_seal_deposit(self: World) -> dict:
    """``deposit_sealed``: the records and the spools, each spool sealed only up to its
    worker's recorded resolution offset (repair contract EB5 item 2;
    ``git show b049307:experiments/live_ab/lab_orchestrator.py`` lines 2691-2701: the old seal
    hashed every spool whole, including spools that live workers were still writing -- a
    digest of a possibly growing file presented as sealed).  A spool found longer than that
    offset, or whose first ``spool_bytes_at_resolution`` bytes no longer hash to the recorded
    digest, is listed in ``late_unread``: its later bytes are never read.  A spool whose worker
    is not resolved is sealed as it stands (the resolution verdict fails on that worker
    anyway).  A spool that cannot be read, or was not read at its resolution, is sealed
    ``null`` -- never the digest of an empty file (review of 988baf7, reviewer 1).  Returns the
    observation of every spool (stem -> :func:`spool_observation`), which the resolution
    verdict reads: the verdict and the seal see the same bytes."""
    assert self.log is not None
    records = sorted(self.ctx.paths.records.glob('*.json')) \
        if self.ctx.paths.records.exists() else []
    spools = sorted(self.ctx.paths.spools.glob('*.jsonl')) \
        if self.ctx.paths.spools.exists() else []
    last = last_worker_resolutions(self.log.events)
    by_stem = {spool_name(*key): rec for key, rec in last.items()
               if rec['state'] in RESOLVED_WORKER_STATES}
    stats: dict = {}
    sealed: list = []
    late: list = []
    total = sum(p.stat().st_size for p in records)
    for path in spools:
        rec = by_stem.get(path.stem)
        upto = rec['spool_bytes_at_resolution'] if rec is not None else None
        obs = spool_observation(path, upto)
        stats[path.stem] = obs
        found = obs['bytes'] if isinstance(obs['bytes'], int) else None
        if rec is None:
            # an unreadable spool is sealed as unread (null), never as an empty file
            sealed.append(obs['sha256'])
            total += found or 0
            continue
        if upto is None or found is None or obs['prefix_sha256'] is None:
            # unread at its resolution, unreadable now, or shorter than its offset: nothing
            # of it is sealed (null), never an empty file's digest
            sealed.append(None)
            late.append({'arrival': int(rec['arrival']), 'attempt': int(rec['attempt']),
                         'bytes_at_resolution': None if upto is None else int(upto),
                         'bytes_found': found})
            continue
        sealed.append(obs['prefix_sha256'])
        total += min(found, int(upto))
        if found != upto or obs['prefix_sha256'] != rec['spool_sha256_at_resolution']:
            late.append({'arrival': int(rec['arrival']), 'attempt': int(rec['attempt']),
                         'bytes_at_resolution': int(upto), 'bytes_found': int(found)})
    for stem, rec in sorted(by_stem.items()):
        if stem not in stats:
            # a worker that died before its first line left no spool: observed as 0 bytes,
            # which is what its resolution recorded (a spool appearing later is late)
            path = self.ctx.paths.spools / ('%s.jsonl' % stem)
            stats[stem] = spool_observation(path, rec['spool_bytes_at_resolution'])
    manifest = {'records': [sha256_file(p) for p in records], 'spools': sealed}
    self.append('deposit_sealed', {
        'deposit_sha256': sha256_canonical(manifest),
        'deposit_bytes': int(total),
        'n_records': len(records), 'n_spools': len(spools),
        'late_unread': late}, durable=True)
    return stats


def _w_write_pause(self: World) -> None:
    # Repair contract EB5 item 2: the bounded drain first -- every worker this invocation
    # spawned runs into its spool or is killed at its hard cap, and is resolved; the resumed
    # invocation reveals what the spools hold.  A pause no longer ends over running workers.
    self.drain_workers(reveal=False)
    # An invocation that ends paused leaves no server behind: the servers it started are
    # stopped, each with a durable server_stopped record, before trial_paused (repair
    # contract EB1 item 4).  The resumed invocation stops any recorded server that is still
    # running and starts and verifies every server again before its first dispatch
    # (resume_into -> stop_chain_orphans, resume_servers).
    if not self.rt.get('sim'):
        self.stop_servers()
    reason = self.pause_reason or 'operator_discretion'
    body: dict = {'reason_code': reason, 'what_was_known': self.what_was_known()}
    if self.pause_digests is not None:
        body['digests'] = self.pause_digests
    self.append('trial_paused', body, durable=True)
    self.append('invocation_ended', {
        'status': 'paused',
        'counts': {'pairs_enrolled': self.pairs_enrolled,
                   'pairs_completed': self.pairs_completed,
                   'looks': self.looks_written}}, durable=True)
    self.request_anchor('trial_paused', blocking=True)
    self.wait_for_receipt()


def _w_wait_for_receipt(self: World) -> None:
    deadline = time.monotonic() + float(self.rt.get('blocking_wait_s', 30.0))
    while self.pending_anchor is not None and time.monotonic() < deadline:
        if self.ingest_receipts():
            break
        time.sleep(min(0.05, self.poll_s))


World._anchor_t0 = 0.0
World._abort_cursor = 0
World.decision_anchor_done = False


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------
def resume_into(ctx: RunContext, world: World) -> State:
    """7.1 row 2a: ``invocation_started`` (D); ``plan_resume``; emit orphan reveals,
    ``orphan_rejected`` and interrupted reveals in arrival order; replay the monitor."""
    assert world.log is not None
    world._resumed = True
    events = world.log.events
    spools: dict[str, list] = {}
    if ctx.paths.spools.exists():
        for path in sorted(ctx.paths.spools.glob('ep_*.jsonl')):
            try:
                spools[path.stem] = read_whole_spool(path)
            except SpoolError:
                spools[path.stem] = []
    plan = plan_resume(events, spools, ctx.order, frozen_cfg(ctx.cfg))
    world.rebuild_from_chain(events, plan)
    drift = runtime(ctx.cfg).get('drift') or []
    world.append('invocation_started', {
        'pid': os.getpid(),
        'argv_sha256': sha256_canonical(sys.argv),
        'argv_tokens': argv_tokens(sys.argv),
        'resumed': True, 'head_at_start': world.log.head,
        'state': {'pairs_enrolled': world.pairs_enrolled,
                  'pairs_completed': world.pairs_completed,
                  'open_attempts': len(plan.interrupted) + len(plan.orphan_reveals),
                  'phase': 'randomizing' if plan.phase == 'randomizing'
                           else 'post_decision'},
        'boottime_hash': lab_common.boottime_hash() or '0' * 64,
        'drift': list(drift)}, durable=True)

    # (0) Repair contract EB5 item 3: every worker an earlier invocation spawned and never
    # recorded as resolved is resolved NOW, before any server is touched and before anything
    # is revealed: gone -> worker_resolved(exited); still that worker (pid + start time + its
    # job file, probe_worker) -> killed by process group and reaped -> worker_resolved(
    # killed_reaped).  If one cannot be resolved the invocation REFUSES: nothing is revealed
    # (never a live orphan as `interrupted`), nothing is started or dispatched.
    if not world.resolve_previous_workers(events):
        return 'ENDED_REFUSED'                               # type: ignore[return-value]
    # The plan is taken again over the spools as they stand after the kills: a worker that
    # wrote its final line between the first plan and its kill is revealed from it.
    events = world.log.events
    spools = {}
    if ctx.paths.spools.exists():
        for path in sorted(ctx.paths.spools.glob('ep_*.jsonl')):
            try:
                spools[path.stem] = read_whole_spool(path)
            except SpoolError:
                spools[path.stem] = []
    plan = plan_resume(events, spools, ctx.order, frozen_cfg(ctx.cfg))

    live = plan.phase in ('randomizing', 'post_decision')
    supervised = not world.rt.get('sim')
    # (1) Repair contract EB1 item 4: a server an earlier invocation started and never
    # recorded as stopped is stopped now, if it is provably still that server.
    if supervised:
        world.stop_chain_orphans(events)

    # (2) Everything recoverable from the spools, BEFORE any server is started: those
    # responses were served by the previous process and belong to its reconciliation window.
    # (A pair enrolled without its coin has, by pair-synchronous execution, no open
    # predecessor, so these lists are empty whenever plan.reenroll_pair is set.)
    for row in plan.orphan_reveals:
        world.reveal_orphan(dict(row, plan=plan), recovered=True)
    for row in plan.orphan_rejections:
        world.append('orphan_rejected', {
            'arrival': int(row['arrival']), 'attempt': int(row['attempt']),
            'check_failed': str(row['check_failed']),
            'record_sha256': row.get('record_sha256'),
            'spool_sha256': str(row['spool_sha256'])}, durable=True)
    for arrival in plan.interrupted:
        world.reveal_interrupted(arrival, spools.get(f'ep_{arrival}_1') or [], plan)

    # (3) The servers, started and verified again through lab_server BEFORE any dispatch --
    # unless the chain already owes an abort or a pause (a crash inside supervision), in
    # which case nothing is started and nothing is dispatched.
    if supervised and live and world.pending_abort is None and world.pending_pause is None:
        world.resume_servers()

    # (4) Dispatch, only while supervision owes nothing.
    owed = world.pending_abort is not None or world.pending_pause is not None
    if plan.reenroll_pair is not None and not owed:
        world.reenroll_pair(plan.reenroll_pair)
        world.draw_coin()
        world.dispatch_pair()
        return 'RUNNING'
    for arrival in plan.dispatch_after_resume:
        if world.pending_abort is not None:
            # The trial ends here and every assigned arrival must be revealed: one that was
            # never run is revealed as interrupted (success 0, known tokens), not dropped.
            world.reveal_interrupted(arrival, spools.get(f'ep_{arrival}_1') or [], plan)
        elif world.pending_pause is None:
            world.redispatch(arrival, plan)
        # under an owed pause it stays assigned and is dispatched by the next resume
    world.raise_pending()

    if plan.phase == 'post_decision':
        if plan.pending_decision_steps:
            if 'anchor' in plan.pending_decision_steps:
                world.request_anchor('decision', blocking=True)
                world.decision_anchor_done = True
            return 'ANCHOR_BLOCK'
        return 'POST_DECISION'
    if world.open_arrivals:
        return 'RUNNING'
    return 'IDLE'


def _w_resolve_previous_workers(self: World, events: Sequence[Mapping]) -> bool:
    """Resume, repair contract EB5 item 3: resolve every worker an earlier invocation spawned
    whose attempt has no resolving ``worker_resolved`` yet; True when all are resolved.

    The workers are the ``episode_started`` of the chain (pid ``worker_pid``, dispatched at
    ``dispatched_ns``) and -- because ``episode_started`` is not durable -- every spool whose
    ``job_accepted`` names a pid for an arrival the chain never recorded as started.  Each
    is read by :func:`probe_worker` (pid AND identity: its command line names its own job
    file, it started no later than its dispatch): gone -> ``worker_resolved(exited)`` with
    return code null (it was never this process's child); still that worker ->
    :func:`kill_orphan_worker` (SIGKILL to its own process group, then confirmed gone) ->
    ``worker_resolved(killed_reaped)``.  One that cannot be resolved (its kill not confirmed,
    or ``ps`` could not answer) is RECORDED as it was found -- ``worker_resolved(
    alive_unresolved | liveness_unknown)``, durable -- and then this invocation refuses --
    ``invocation_ended(refused)`` with the counts -- and reveals, starts and dispatches
    nothing.  A later resume tries again to resolve the process (it must be gone before
    anything is revealed), but the unresolved record is never undone
    (:func:`effective_worker_states`; protocol 14.6): the phase cannot complete and its close
    is ``trial_aborted(unresolved_worker)``, exactly as when the same fact is observed inside
    one invocation.  Review of 988baf7, reviewer 1 finding 4: the refusal used to record
    nothing, so a later resume recorded the orphan ``exited`` and the trial could end
    ``trial_ended``.  ``finished()`` of such an attempt used to be ``0`` ("exited"), and
    ``_w_reveal_interrupted`` revealed it with no liveness check (``git show
    b049307:experiments/live_ab/lab_orchestrator.py`` lines 1930-1934 and 2923-2938)."""
    last = last_worker_resolutions(events)
    candidates: dict[int, tuple[int, int | None]] = {}
    for ev in events:
        if ev['type'] == 'episode_started':
            body = ev['body']
            candidates.setdefault(int(body['arrival']),
                                  (int(body['worker_pid']), int(body['dispatched_ns'])))
    spool_dir = self.ctx.paths.spools
    if spool_dir.exists():
        for path in sorted(spool_dir.glob('ep_*_1.jsonl')):
            try:
                arrival = int(path.stem.split('_')[1])
            except (IndexError, ValueError):
                continue
            if arrival in candidates:
                continue
            first = b''
            try:
                with open(path, 'rb') as fh:
                    first = fh.readline()
                row = json.loads(first.decode('utf-8'))
            except (OSError, ValueError, UnicodeDecodeError):
                row = None
            pid = row.get('pid') if isinstance(row, dict) \
                and row.get('kind') == 'job_accepted' else None
            if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
                candidates[arrival] = (pid, None)
    refused = {'alive_unresolved': 0, 'liveness_unknown': 0}
    for arrival in sorted(candidates):
        rec = last.get((arrival, 1))
        if rec is not None and rec['state'] in RESOLVED_WORKER_STATES:
            continue
        pid, not_after = candidates[arrival]
        job = 'job_%d_1.json' % arrival
        seen = probe_worker(pid, job, not_after_ns=not_after)
        rc: int | None = None
        if seen == 'gone':
            state = 'exited'
        elif seen == 'alive':
            state, rc = kill_orphan_worker(pid, job, not_after_ns=not_after)
        else:
            state = 'liveness_unknown'
        body = self._resolution_body(arrival, 1, pid, state, rc,
                                     spool_dir / ('%s.jsonl' % spool_name(arrival)))
        if state not in RESOLVED_WORKER_STATES:
            refused[state] += 1
            if rec is None or rec['state'] != state or rec['pid'] != pid:
                # recorded once per state found (a resume that finds the same process in the
                # same state again adds nothing): the phase is incomplete from here on
                self.append('worker_resolved', body, durable=True)
            self.unresolved_seen = True
            continue
        self.append('worker_resolved', body, durable=True)
        att = self.attempts.get(arrival)
        if att is not None:
            att.resolution = body
            if att.revealed:
                # a worker that outlived its own reveal may have spooled calls after it:
                # they are chain evidence and stay in the exposure ledger (never "unsent")
                att.offset, att.lines = 0, []
                try:
                    ingest_spool(self, att)
                except SpoolError:
                    self.findings.append('late_spool_unreadable:%d' % arrival)
    if refused['alive_unresolved'] or refused['liveness_unknown']:
        self.append('invocation_ended', {
            'status': 'refused',
            'counts': {'workers_alive_unresolved': refused['alive_unresolved'],
                       'workers_liveness_unknown': refused['liveness_unknown'],
                       'pairs_enrolled': self.pairs_enrolled,
                       'pairs_completed': self.pairs_completed}}, durable=True)
        return False
    return True


def _w_rebuild_from_chain(self: World, events: Sequence[Mapping], plan: ResumePlan) -> None:
    """Rebuild the live state from the verified chain: the monitor by replaying it, the
    attempts from their assignment and reveal events.  Nothing is recomputed from a clock
    or a process, so two invocations from the same bytes rebuild the same state."""
    looks = lab_monitor.replay(list(events), self.cfg, self.ctx.trial)
    for snap in looks:
        pair_updated = snap.get('pair_updated')
        enc_obj = snap.get('pair_enclosure')
        if pair_updated is None or enc_obj is None:
            continue
        pair = int(pair_updated)
        enc = lab_enclosure.PairEnclosure(
            h=lab_enclosure.Enclosure(float(enc_obj['h'][0]), float(enc_obj['h'][1])),
            s=lab_enclosure.Enclosure(float(enc_obj['s'][0]), float(enc_obj['s'][1])),
            collapsed=bool(enc_obj['collapsed']),
            decisive_tier=int(enc_obj['decisive_tier']))
        if snap['trigger'] == 'enroll':
            self.monitor.enroll(pair)
        self.monitor.update(pair, enc)
    logged = sum(1 for e in events if e['type'] == 'monitor_update')
    if logged != len(looks):
        self.findings.append(f'cadence_gap:{logged}!={len(looks)}')
    self.looks_written = logged
    self.plain_looks_written = sum(
        1 for e in events
        if e['type'] == 'monitor_update' and e['body']['trigger'] != 'resume')
    self.pairs_enrolled = plan.monitor_prefix
    self.anchor_seq = sum(1 for e in events if e['type'] == 'anchor')
    self.reveal_index = sum(1 for e in events if e['type'] == 'episode_revealed')
    self.receipts_obtained = sum(1 for e in events if e['type'] == 'anchor_receipt')
    # which anchors the chain has already resolved: the receipt spool is re-read from its
    # start by this invocation, and a line already chained is not chained again
    for e in events:
        if e['type'] == 'anchor_receipt':
            self.anchor_resolved[int(e['body']['anchor_seq'])] = 'receipt'
        elif e['type'] == 'anchor_failed':
            self.anchor_resolved.setdefault(int(e['body']['anchor_seq']), 'failed')
    # one chain event per receipt line consumed (root f855e45): those lines are replayed
    self.receipts_rejected = sum(1 for e in events if e['type'] == 'anchor_receipt_rejected')
    self._receipt_replay = [e for e in events if e['type'] in RECEIPT_LINE_EVENTS]
    self._receipt_lines_read = 0
    self._current_pair = plan.monitor_prefix
    for ev in events:
        if ev['type'] == 'pair_enrolled':
            for position, arrival in enumerate(ev['body']['arrivals'], start=1):
                self.pair_of_arrival[int(arrival)] = int(ev['body']['pair'])
        elif ev['type'] == 'decision':
            self.decision = dict(ev['body'])
            self.decision_seq = int(ev['seq'])
            self.decided_arm = ('candidate' if ev['body']['kind'] == 'deploy_candidate'
                                else 'incumbent'
                                if ev['body']['kind'] == 'harm_keep_incumbent' else None)
            self.decision_anchor_done = True
            self.phase = 'draining'
        elif ev['type'] == 'traffic_switch':
            self.phase = 'post_decision'
        elif ev['type'] == 'episode_started':
            body = ev['body']
            arrival = int(body['arrival'])
            att = Attempt(arrival=arrival, attempt=1,
                          pair=int(body['pair']) or None,
                          position=int(body['position']) or None, arm=str(body['arm']),
                          workflow=str(body['workflow']),
                          server_id=str(body['server_id']),
                          task_uid=str(body['task_uid']),
                          spool=self.ctx.paths.spools / f'ep_{arrival}_1.jsonl',
                          job={}, assignment_seq=int(body['assignment_seq']),
                          post_decision=self.decision is not None)
            att.pid = int(body['worker_pid'])
            self.attempts[arrival] = att
        elif ev['type'] == 'job_accepted':
            att = self.attempts.get(int(ev['body']['arrival']))
            if att is not None:
                att.logged.add(('job_accepted', ''))
        elif ev['type'] in ('llm_request', 'llm_response', 'llm_error'):
            att = self.attempts.get(int(ev['body']['arrival']))
            if att is not None:
                kind = {'llm_request': 'call_started', 'llm_response': 'call_response',
                        'llm_error': 'call_error'}[ev['type']]
                att.logged.add((kind, str(ev['body']['request_id'])))
        elif ev['type'] == 'episode_revealed':
            arrival = int(ev['body']['arrival'])
            att = self.attempts.get(arrival)
            if att is not None:
                att.revealed = True
                att.logged.add(('episode_final', ''))
        elif ev['type'] == 'worker_resolved':
            att = self.attempts.get(int(ev['body']['arrival']))
            if att is not None:
                att.resolution = dict(ev['body'])
            if ev['body']['state'] not in RESOLVED_WORKER_STATES:
                # an earlier invocation's pump or pause drain recorded a worker it could
                # not resolve: the phase can no longer complete (EB5)
                self.unresolved_seen = True
    self.pairs_completed = sum(
        1 for pair in set(self.pair_of_arrival.values())
        if len([a for a, p in self.pair_of_arrival.items() if p == pair
                and self.attempts.get(a) is not None and self.attempts[a].revealed]) == 2)
    self.post_decision_dispatched = sum(1 for e in events
                                        if e['type'] == 'arm_assigned_by_decision')
    # Supervision is rebuilt from the chain too (repair contract EB1 item 2): the attempted
    # restarts per server that the cap bounds, the previous start's /props digest, the
    # arrivals whose reveal carries infra_flag, and any outcome the chain still owes.
    sup = supervision_state(events, self.restart_cap)
    self.restarts = dict(sup.restarts)
    self.server_props_sha = {str(k): str(v) for k, v in sup.props_sha256.items()
                             if v is not None}
    self.down_overlap = set(sup.down_overlap)
    self.unresolved_down = dict(sup.unresolved_down)
    self.pending_abort = sup.pending_abort
    self.pending_pause = sup.pending_pause


def chain_server_pids(events: Sequence[Mapping]) -> list[tuple[str, int]]:
    """[pure] ``(server_id, pid)`` of every server a ``server_started`` / ``server_restarted``
    recorded and no later ``server_stopped`` of the same server and pid closed, in chain
    order.  A simulated body's pid 0 is never one."""
    held: dict[tuple[str, int], int] = {}
    for ev in events:
        body = ev.get('body') or {}
        if ev['type'] in ('server_started', 'server_restarted'):
            pid = int(body.get('pid') or 0)
            if pid > 0:
                held[(str(body['server_id']), pid)] = int(ev['seq'])
        elif ev['type'] == 'server_stopped':
            held.pop((str(body.get('server_id')), int(body.get('pid') or 0)), None)
    return [key for key, _ in sorted(held.items(), key=lambda kv: kv[1])]


def _w_stop_chain_orphans(self: World, events: Sequence[Mapping]) -> None:
    """Resume, repair contract EB1 item 4: stop every server pid the chain records as started
    and not stopped that is STILL THAT SERVER (``lab_server.orphan_server``: alive and
    listening on its frozen port), each with a durable ``server_stopped``.

    A recorded pid that is dead needs nothing.  One that is alive but not listening on the
    port was given by the OS to another program and is never signalled.  One whose listener
    table could not be read is not signalled either; it is named in ``findings`` and, if it
    still holds the port, the start that follows fails and is handled by the supervision
    rules.  The previous invocation's pids are remembered for :meth:`resume_servers`."""
    self.previous_pids = {}
    for server_id, pid in chain_server_pids(events):
        self.previous_pids[server_id] = pid
        spec = self.ctx.servers.get(server_id)
        if spec is None:
            continue
        state = lab_server.orphan_server(pid, int(spec.port))
        if state is None:
            self.findings.append('orphan_server_unverifiable:%s' % server_id)
            continue
        if not state:
            self.previous_gone.add(pid)
            continue
        result = lab_server.stop(pid)
        self.append('server_stopped', {
            'server_id': server_id, 'pid': int(pid),
            'returncode': (int(result['returncode'])
                           if result.get('returncode') is not None else None),
            'seconds': float(result.get('seconds') or 0.0)}, durable=True)


def _w_resume_servers(self: World) -> None:
    """Resume, repair contract EB1 item 4: start and verify every server again before any
    dispatch.

    A server whose ``server_down`` the chain left unresolved (the previous invocation died
    inside supervision) is RESTARTED through :meth:`supervised_restart`, so the down is
    followed by its restart (or failed restart) and the attempt counts towards the cap; the
    other servers are started through ``lab_server.start``.  A failed start follows the
    supervision rules, not the first-start ones: never healthy -> ``trial_paused(
    server_unrecoverable)``; anything else -> ``trial_aborted`` by
    :data:`START_FAILURE_REASON`; a refused call, or any other ``Exception`` out of the
    start -> ``trial_aborted(harness_defect)``.  After
    a failure no further server is started.  Every server started here is scraped
    (``metrics_scrape(restart)``)."""
    started: list[str] = []
    for server_id in sorted(self.ctx.servers):
        if self.pending_abort is not None or self.pending_pause is not None:
            break
        if server_id in self.unresolved_down:
            previous = int(self.previous_pids.get(server_id) or 0)
            if previous in self.previous_gone:
                # dead, or alive but not listening on the frozen port (a reused pid): the
                # previous server is gone and nothing of ours is left to stop or to guard
                previous = 0
            self.unresolved_down.pop(server_id, None)
            self.supervised_restart(server_id, previous_pid=previous)
            continue
        try:
            self._start_one(server_id)
        except lab_common.ServerStartFailed as exc:
            self.append('server_start_failed', dict(exc.record), durable=True)
            stage = str(exc.record.get('stage'))
            if stage in NEVER_HEALTHY_STAGES:
                self.pending_pause = 'server_unrecoverable'
            else:
                self.pending_abort = START_FAILURE_REASON.get(stage, 'infrastructure')
            break
        except Exception:
            # PreflightError (refused), or an exception lab_server.start did not convert (EB1
            # fix, reviewer 1 finding 7): nothing more is started, the trial owes the abort
            self.pending_abort = 'harness_defect'
            break
        started.append(server_id)
    if started:
        self.scrape('restart', server_ids=started)


def _w__ensure_attempt(self: World, arrival: int, plan: ResumePlan) -> Attempt | None:
    """The bookkeeping object of an arrival whose spool exists but whose (non-durable)
    ``episode_started`` was never written -- a crash between the fsynced job file and that
    line.  The attempt is reconstructed from the frozen order and the binding assignment,
    never from a clock or a process: the spool is the evidence that it began (PG-7)."""
    att = self.attempts.get(arrival)
    if att is not None:
        return att
    arm = plan.bound_assignments.get(arrival)
    if arm is None:
        return None
    pair = self.pair_of_arrival.get(arrival)
    slot = self.ctx.order[pair - 1] if pair else None
    position = (list(slot['arrivals']).index(arrival) + 1) if slot else None
    arm_cfg = ((self.cfg.get('trials') or {}).get(self.ctx.trial) or {}).get(arm) or {}
    att = Attempt(arrival=arrival, attempt=1, pair=pair, position=position, arm=arm,
                  workflow=str(arm_cfg.get('workflow') or 'single_shot'),
                  server_id=str(arm_cfg.get('server') or 'coder'),
                  task_uid=self.uid_of_arrival(arrival),
                  spool=self.ctx.paths.spools / f'ep_{arrival}_1.jsonl', job={},
                  assignment_seq=self._assignment_seq_of(arrival),
                  post_decision=self.decision is not None,
                  worker_index=(position - 1) if position else 0)
    self.attempts[arrival] = att
    return att


def _w_reveal_orphan(self: World, row: Mapping, *, recovered: bool) -> None:
    """Reveal an attempt from its own complete spool (protocol 14.5 item 3).

    The unlogged remainder of the spool is ingested first, so every ``call_started`` has a
    chain event before the reveal that depends on it; lines an earlier invocation already
    turned into chain events are skipped.  Nothing is re-run."""
    arrival = int(row['arrival'])
    att = self._ensure_attempt(arrival, row['plan'])
    if att is None or att.revealed:
        return
    att.recovered_orphan = recovered
    att.offset = 0
    att.lines = []
    if arrival not in self.open_arrivals:
        self.open_arrivals.append(arrival)
    ingest_spool(self, att)


def _w_reveal_interrupted(self: World, arrival: int, lines: Sequence[Mapping],
                          plan: ResumePlan) -> None:
    """6.4 row 11: an attempt that started and holds no usable terminal line is revealed
    as ``interrupted`` with ``success = 0`` and ``latency_s`` = the certified elapsed time.
    Nothing is re-run."""
    att = self._ensure_attempt(arrival, plan)
    if att is None or att.revealed:
        return
    self.assert_resolved_before_interrupt(int(arrival))
    att.offset = 0
    att.lines = []
    att.suppress_final = True
    if arrival not in self.open_arrivals:
        self.open_arrivals.append(arrival)
    ingest_spool(self, att)
    if not att.revealed:
        self._terminal(att, 'interrupted')


def _w_assert_resolved_before_interrupt(self: World, arrival: int) -> None:
    """Repair contract EB5 item 3: never an ``interrupted`` reveal over a worker that is not
    recorded as resolved.  An arrival that ran (its spool holds bytes) must have, as its LAST
    ``worker_resolved``, a resolving state -- its process confirmed gone now;
    :meth:`resolve_previous_workers` runs first and refuses the invocation otherwise, so
    reaching the raise is the harness's own defect, never a reveal.  An EARLIER unresolved
    record of the same worker (a refused resume) still makes the phase incomplete
    (:func:`effective_worker_states`, the verdict), but does not forbid revealing a process
    that is now confirmed gone."""
    assert self.log is not None
    path = self.ctx.paths.spools / ('%s.jsonl' % spool_name(arrival))
    ran = path.exists() and path.stat().st_size > 0
    last = last_worker_resolutions(self.log.events).get((int(arrival), 1))
    state = None if last is None else last['state']
    if ran and state not in RESOLVED_WORKER_STATES:
        raise lab_common.LabError('refusing to reveal arrival %d as interrupted: its '
                                  'worker is not resolved' % int(arrival))


def _w_redispatch(self: World, arrival: int, plan: ResumePlan) -> None:
    """PG-7 / 6.4 rows 11c-11e: an assigned arrival with no ``job_accepted`` never ran, so
    it is dispatched now as its one and only attempt, flagged ``started_after_resume``."""
    pair = self.pair_of_arrival.get(arrival)
    arm = plan.bound_assignments[arrival]
    slot = None if pair is None else self.ctx.order[pair - 1]
    position = (list(slot['arrivals']).index(arrival) + 1) if slot else None
    worker_index = (position - 1) if position else 0
    job = self.build_job(arrival=arrival, attempt=1, pair=pair, position=position,
                         arm=arm, worker_index=worker_index,
                         assignment_seq=self._assignment_seq_of(arrival))
    att = Attempt(arrival=arrival, attempt=1, pair=pair, position=position, arm=arm,
                  workflow=str(job['workflow']),
                  server_id=str(job['server']['server_id']),
                  task_uid=str(job['task_uid']),
                  spool=self.ctx.paths.spools / f'ep_{arrival}_1.jsonl', job=job,
                  assignment_seq=self._assignment_seq_of(arrival),
                  post_decision=self.decision is not None,
                  worker_index=worker_index)
    att.started_after_resume = True
    att.partner_concurrent = bool(
        pair is not None and any(a in plan.dispatch_after_resume
                                 for a in self.ctx.order[pair - 1]['arrivals']
                                 if int(a) != arrival))
    self.dispatch(att)
    if pair is not None:
        self._current_pair = pair


def _w__assignment_seq_of(self: World, arrival: int) -> int:
    assert self.log is not None
    for ev in self.log.events:
        if ev['type'] == 'coin_drawn' and str(arrival) in (ev['body'].get('assignment') or {}):
            return int(ev['seq'])
        if ev['type'] == 'arm_assigned_by_decision' \
                and int(ev['body']['arrival']) == arrival:
            return int(ev['seq'])
    raise PreflightError(f'arrival {arrival} has no assignment event')


_install(World)


# ---------------------------------------------------------------------------
# run_trial
# ---------------------------------------------------------------------------
#: The substitute-world seam of ARCHITECTURE_FINAL.md 3.13 ("so that the transition table
#: can be unit-tested with a fake World").  A trial always runs against :class:`World`; the
#: mock dry runs replace only the dispatch of a worker process, and every artifact they
#: produce carries the MOCK banner.
WORLD_FACTORY: Any = None


def run_trial(ctx: RunContext, *, resume: bool = True) -> str:
    """The whole trial.  Returns the terminal status (``'ended'`` | ``'aborted'`` |
    ``'paused'``), or ``'refused'`` when a resumed invocation could not resolve an earlier
    invocation's worker (repair contract EB5).  Single-threaded."""
    rt = runtime(ctx.cfg)
    ctx.paths.mkdirs()
    lock = RunLock(ctx.paths.run_lock, ctx.inv)
    world = (WORLD_FACTORY or World)(ctx)
    status = 'aborted'
    try:
        try:
            drift = preflight(ctx)
            # THE SECOND SIBLING FOUND BY THE runtime() SWEEP, 2026-09-22.
            # `rt` here is runtime(ctx.cfg), which returns a COPY, so this write
            # vanished when run_trial returned -- and a repository-wide grep
            # finds NO READER of rt['drift'] anywhere, so nothing ever noticed.
            # It is persisted to the context's runtime block, where a reader
            # would look, rather than deleted: the drift is already carried into
            # the chain by invocation_started, so this is a convenience copy, and
            # a convenience that silently evaporates is worse than one that does
            # not exist. NOTHING READS IT TODAY -- that is stated rather than
            # implied by its presence.
            rt['drift'] = drift
            ctx.cfg.setdefault('_runtime', {})['drift'] = drift
        except PreflightError as exc:
            write_preflight_refused(ctx, str(exc), drift=getattr(exc, 'drift', None))
            return 'aborted'
        # protocol 5.7.  Last of the pre-seq-0 refusals, because it is the only one that
        # reads the rest of the machine: a foreign accelerator job is reported by name and
        # a host the scan could not read is refused as well.
        try:
            host_quiescence_gate(ctx)
        except lab_hostcheck.HostNotQuiescent as exc:
            # The closed reason code first, as for every other refusal; then the record
            # that names the offenders, which only this gate can write.
            write_preflight_refused(ctx, 'host_not_quiescent')
            write_host_quiescence_refused(ctx, exc)
            return 'aborted'
        lock.acquire()
        world.integrity_paths, world.integrity_digests = integrity_baseline(ctx)
        state: State = 'PREFLIGHT'
        existing = lab_eventlog.segment_paths(ctx.paths.events)
        if existing and not resume:
            raise PreflightError('the trial chain exists and --resume was not given')
        while True:
            try:
                nxt, _ = step(state, ctx, world)
            except PauseTrial as exc:
                world.pause_reason = exc.reason
                state = 'PAUSED'
                continue
            except AbortTrial as exc:
                world.abort_reason = exc.reason
                state = 'ABORTED'
                continue
            except (MonitorError, lab_common.EnclosureError) as exc:
                world.findings.append(f'monitor_exception:{exc}')
                world.pause_reason = 'monitor_exception'
                state = 'PAUSED'
                continue
            except (lab_common.ServerStartFailed, lab_common.ServerIdentityError,
                    lab_common.ReceiptMismatch) as exc:
                # What lab_server can raise, caught so that a server failure after
                # trial_started ends in trial_aborted rather than in an escaping exception
                # (repair contract EB1 item 10).  start_servers already converts its own
                # failures; this is the backstop.  An exception raised while the trial is
                # already closing is not looped on: it propagates.
                if world.log is None or state in ('ABORTED', 'PAUSED', 'CLOSING'):
                    raise
                if isinstance(exc, lab_common.ServerStartFailed):
                    try:
                        world.append('server_start_failed', dict(exc.record), durable=True)
                    except lab_common.SchemaError:
                        world.findings.append('server_start_failed_unwritable')
                    world.abort_reason = START_FAILURE_REASON.get(
                        str(exc.record.get('stage')), 'infrastructure')
                elif isinstance(exc, lab_common.ReceiptMismatch):
                    world.abort_reason = 'receipt_mismatch'
                else:
                    world.abort_reason = 'server_identity'
                state = 'ABORTED'
                continue
            if nxt in ('ENDED', 'ENDED_ABORTED', 'ENDED_PAUSED', 'ENDED_REFUSED'):
                status = {'ENDED': 'ended', 'ENDED_ABORTED': 'aborted',
                          'ENDED_PAUSED': 'paused', 'ENDED_REFUSED': 'refused'}[nxt]
                break
            if nxt == state:
                time.sleep(world.poll_s)
            drifted = maybe_worktree_check(ctx, world)
            if drifted is not None and state not in ('PAUSED', 'ABORTED', 'CLOSING'):
                world.pause_digests = drifted['digests']
                world.pause_reason = 'worktree_drift'
                state = 'PAUSED'
                continue
            state = nxt
            write_status(ctx, world)
        return status
    finally:
        try:
            # No llama-server outlives its orchestrator.  Every orderly exit (ended, aborted,
            # paused) has already stopped and recorded its servers; this only acts when an
            # exception escaped, and then it stops without writing, because the chain's
            # state is exactly what escaped.
            for pid in list(getattr(world, 'server_pids', {}).values()):
                if pid:
                    lab_server.stop(int(pid))
        finally:
            try:
                if world.log is not None:
                    world.log.close()
            finally:
                lock.release()


def maybe_worktree_check(ctx: RunContext, world: World) -> dict | None:
    every = float((frozen_cfg(ctx.cfg).get('execution') or {}).get('worktree_check_s', 60))
    every = float(runtime(ctx.cfg).get('worktree_check_s', every))
    now = time.monotonic()
    if now - world.last_worktree < every:
        return None
    world.last_worktree = now
    return worktree_check(ctx, world)


def integrity_baseline(ctx: RunContext) -> tuple[dict, dict]:
    """The digests ``worktree_check`` re-asserts every 60 s: the freeze files, the closed
    chain segments and ``src/winstats.py``."""
    paths: dict[str, Path] = {}
    digests: dict[str, str] = {}
    rt = runtime(ctx.cfg)
    freeze_dir = Path(rt.get('freeze_dir') or (Path(rt['results_root']) / 'freeze'))
    candidates = list(freeze_dir.glob('*.json')) + list(freeze_dir.glob('*.csv'))
    candidates.append(lab_common.SRC_DIR / 'winstats.py')
    for path in candidates:
        if path.exists():
            tok = tokenize_or_name(str(path))
            if tok is None:
                continue
            paths[tok] = path
            digests[tok] = sha256_file(path)
    for path in lab_eventlog.segment_paths(ctx.paths.events)[:-1]:
        tok = tokenize_or_name(str(path))
        if tok is None:
            continue
        paths[tok] = path
        digests[tok] = sha256_file(path)
    return paths, digests


def write_status(ctx: RunContext, world: World) -> None:
    try:
        path = ctx.paths.results / 'status.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(status_snapshot(ctx, world)), encoding='utf-8')
    except OSError:
        pass


def write_preflight_refused(ctx: RunContext, reasons: str, *,
                            drift: Sequence[Mapping] | None = None) -> None:
    """Before a trial's seq 0 the refusal goes to the PROGRAM chain (critic N1).

    ``drift`` is the evidence ``preflight`` attached to the ``PreflightError``: the
    ``{'item', 'expected', 'found'}`` rows naming the bundle members that moved.  A reader
    of the chain therefore sees WHICH frozen artifact drifted, not only that something
    did."""
    rt = runtime(ctx.cfg)
    events_dir = Path(rt['results_root']) / lab_common.PROGRAM_CHAIN_ID / 'events'
    checks = [r for r in reasons.split(',') if r]
    rows = [dict(row) for row in (drift or [])]
    try:
        log = EventLog(events_dir, lab_common.PROGRAM_CHAIN_ID, ctx.bundle_sha, ctx.inv,
                       create=not lab_eventlog.segment_paths(events_dir))
    except ChainError:
        return
    try:
        log.append('preflight_refused', {'trial': ctx.trial, 'checks_failed': checks,
                                         'drift': rows}, durable=True)
    except lab_common.SchemaError:
        log.append('preflight_refused', {'trial': ctx.trial,
                                         'checks_failed': ['worktree_identity'],
                                         'drift': []}, durable=True)
    finally:
        log.close()


# ---------------------------------------------------------------------------
# building a RunContext
# ---------------------------------------------------------------------------
def make_context(trial: str, cfg: dict, *, results_root: Path, work_root: Path,
                 inv: str | None = None) -> RunContext:
    """Assemble the frozen inputs of one invocation.

    ``cfg['_runtime']`` must already carry ``results_root``/``work_root`` (as strings) and
    may carry the dry-run overlay.  The frozen files are read from
    ``<results_root>/freeze``."""
    rt = runtime(cfg)
    freeze_dir = Path(rt.get('freeze_dir') or (Path(results_root) / 'freeze'))
    fcfg = frozen_cfg(cfg)
    roster = lab_data.load_roster(freeze_dir / 'roster.json')
    lab_eventlog.set_roster_uids(
        [str(u) for u in roster.get('tasks', [])]
        + [str(u) for u in roster.get('S1', [])] + [str(u) for u in roster.get('S2', [])])
    order_path = freeze_dir / f'arrival_order_{trial}.json'
    document = json.loads(order_path.read_text(encoding='utf-8'))
    order = document['pairs'] if isinstance(document, dict) else document
    tasks = lab_data.load_tasks_by_uid(roster, Path(rt.get('sources_dir') or freeze_dir))
    paths = _trial_paths(trial, Path(results_root), Path(work_root))
    # Only the servers this trial's two arms actually use are started and scraped: in
    # T1/T2/T4 both arms are on `coder`, and only T3 keeps two servers resident (protocol
    # 5.2).  A server no arm uses would produce an empty reconciliation window.
    used = {str((fcfg['trials'][trial].get(arm) or {}).get('server') or 'coder')
            for arm in lab_common.ARMS}
    # Each server has ITS OWN weights path (``--gguf <server>=<path>``): a single runtime path
    # used to be shared by every server, so T3 would have started both on one file.  The
    # launcher is named explicitly too (``--llama-bin``).  Preflight refuses, on the real
    # path, a bare name, a missing file or bytes that are not the frozen ones.
    gguf_paths = {str(k): str(v) for k, v in dict(rt.get('gguf_paths') or {}).items()}
    servers: dict[str, ServerSpec] = {}
    for server_id, sc in sorted((fcfg.get('servers') or {}).items()):
        if server_id not in used:
            continue
        port = int((rt.get('ports') or {}).get(server_id, sc['port']))
        servers[server_id] = ServerSpec(
            server_id=server_id, port=port, alias=str(sc['alias']),
            gguf_path=Path(gguf_paths.get(server_id) or str(sc['file'])),
            gguf_bytes=int(sc['bytes']), gguf_sha256=str(sc['sha256_expected']),
            llama_bin=Path(str(rt.get('llama_bin') or 'llama-server')),
            llama_commit=str(fcfg['llama_cpp']['commit']),
            args=tuple(str(a) for a in fcfg['llama_args']),
            log_path=paths.logs / f'llama_{port}.log',
            n_slots=int(fcfg['execution']['workers']),
            n_ctx=int(_arg_value(fcfg['llama_args'], '-c', 16384)))
    # The golden objects come from the FREEZE TREE (ARCHITECTURE_FINAL.md 2.2 lines 190-191),
    # never from the invocation.  Only a simulated invocation (:func:`simulated_path`: a
    # substitute world AND runtime ``sim``) may overlay its own; preflight refuses the
    # overlay everywhere else.
    golden, _ = load_golden_objects(freeze_dir, fcfg, servers)
    if simulated_path(rt) and rt.get('golden') is not None:
        golden = dict(rt['golden'])
    # THE serving-manifest artifact: fixed under the results root, never the runtime
    # ``freeze_dir`` (preflight refuses a runtime freeze_dir that is not this one).
    serving_manifest_path = lab_serving_manifest.artifact_path(
        Path(results_root).absolute() / 'freeze')
    mc = MonitorConfig.from_config(fcfg, trial)
    rt.setdefault('config_sha256', sha256_file(freeze_dir / 'config.json'))
    rt.setdefault('order_sha256', sha256_file(order_path))
    rt.setdefault('roster_sha256', sha256_file(freeze_dir / 'roster.json'))
    rt.setdefault('task_content_sha256', str(roster.get('task_content_sha256')
                                             or sha256_canonical(roster)))
    cfg['_runtime'] = rt
    return RunContext(trial=trial, inv=inv or uuid.uuid4().hex, cfg=cfg,
                      bundle_sha=str(rt['bundle_sha']), paths=paths, order=list(order),
                      tasks=tasks, mc=mc, servers=servers, golden=golden,
                      serving_manifest_path=serving_manifest_path)


def _arg_value(args: Sequence[str], flag: str, default: int) -> int:
    args = list(args)
    if flag in args:
        try:
            return int(args[args.index(flag) + 1])
        except (IndexError, ValueError):
            return default
    return default


def _trial_paths(trial: str, results_root: Path, work_root: Path,
                 *, execution_lock: Path | str | None = None) -> TrialPaths:
    results = Path(results_root) / trial
    work = Path(work_root) / trial
    return TrialPaths(trial=trial, results=results, events=results / 'events',
                      anchors=results / 'anchors', work=work, jobs=work / 'jobs',
                      spools=work / 'spools', records=work / 'records',
                      requests=work / 'requests', anchor_spool=work / 'anchor_spool',
                      anchors_private=work / 'anchors_private', logs=work / 'logs',
                      run_lock=work / 'run.lock',
                      # HOST-WIDE, not per trial: protocol 5.7 item 1 wants one
                      # lock inode. run_lock stays per trial.
                      sandbox_lock=(Path(execution_lock)
                                    if execution_lock is not None
                                    else lab_common.canonical_execution_lock(
                                        lab_common.harness_config())))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI: ``--trial T4 --config results/live_ab/freeze/config.json [--resume]
    [--mock URL] [--max-pairs N (mock only)] [--results DIR] [--work DIR]
    [--llama-bin PATH] [--gguf coder=PATH] [--gguf t3=PATH]``.
    Exit 0 ended, 1 aborted, 2 paused, 3 preflight refusal or a resumed invocation that
    refused because an earlier invocation's worker could not be resolved (EB5)."""
    ap = argparse.ArgumentParser(prog='lab_orchestrator')
    ap.add_argument('--trial', required=True, choices=list(lab_common.TRIALS))
    ap.add_argument('--config', required=True)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--mock', default=None)
    ap.add_argument('--max-pairs', type=int, default=None)
    ap.add_argument('--results', default=None)
    ap.add_argument('--work', default=None)
    # The launcher and each server's weights are named EXPLICITLY on the real path; the
    # launcher is verified against the frozen serving manifest and each GGUF against the
    # frozen servers block, before seq 0 and again at every start.
    ap.add_argument('--llama-bin', default=None)
    ap.add_argument('--gguf', action='append', default=[], metavar='SERVER=PATH')
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    # Absolute: the server runs in its launcher's directory (lab_serving_manifest.
    # server_cwd), so a relative log path would name another file there, and THE serving
    # manifest is the absolute <results_root>/freeze/serving_manifest.json.
    results_root = Path(args.results or lab_common.RESULTS_ROOT).absolute()
    work_root = Path(args.work or lab_common.WORK_ROOT).absolute()
    rt = cfg.setdefault('_runtime', {})
    rt['results_root'] = str(results_root)
    rt['work_root'] = str(work_root)
    if args.mock:
        rt['mock'] = True
        port = int(str(args.mock).rstrip('/').rsplit(':', 1)[-1].split('/')[0])
        rt['ports'] = {'coder': port, 't3': port}
    if args.max_pairs is not None:
        if not args.mock:
            raise SystemExit('--max-pairs is a mock-only option')
        rt['max_pairs'] = int(args.max_pairs)
    if args.llama_bin:
        rt['llama_bin'] = str(Path(args.llama_bin).absolute())
    if args.gguf:
        paths: dict[str, str] = {}
        for item in args.gguf:
            server_id, sep, path = str(item).partition('=')
            if not sep or server_id not in ('coder', 't3') or not path or server_id in paths:
                raise SystemExit('--gguf takes SERVER=PATH once per server (coder, t3)')
            paths[server_id] = str(Path(path).absolute())
        rt['gguf_paths'] = paths
    # ONE canonical digest convention (lab_common.freeze_bundle_sha256): the bundle's
    # identity is the digest of its canonical JSON object, never of the file's raw bytes.
    # The default used to be `sha256_file`, which disagreed with the digest preflight
    # computes, so a pretty-printed copy of the very same bundle produced
    # `freeze_bundle_drift` (provenance review section 3, "Also confirmed").
    bundle_file = results_root / 'freeze' / 'freeze_bundle.json'
    rt.setdefault('bundle_sha', lab_common.freeze_bundle_sha256_of_file(bundle_file)
                  if bundle_file.exists() else '0' * 64)
    try:
        ctx = make_context(args.trial, cfg, results_root=results_root,
                           work_root=work_root)
    except PreflightError:
        return 3
    status = run_trial(ctx, resume=args.resume)
    return {'ended': 0, 'aborted': 1, 'paused': 2, 'refused': 3}.get(status, 1)


if __name__ == '__main__':                                   # pragma: no cover
    sys.exit(main())
