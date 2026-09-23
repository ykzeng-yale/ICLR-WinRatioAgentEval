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
                'ENDED_ABORTED', 'ENDED_PAUSED']

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
    says so in the ledger itself: missing usage is never rewritten as zero."""
    out: dict = {phase: {arm: {'episodes': 0, 'wall_seconds': 0.0, 'prompt_tokens': 0,
                               'completion_tokens': 0, 'unknown_usage_calls': 0,
                               'tokens_are_lower_bound': False}
                         for arm in lab_common.ARMS}
                 for phase in ('randomizing', 'post_decision')}
    arm_of: dict[int, str] = {}
    phase_of: dict[int, str] = {}
    for ev in events:
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
    for arrival in unknown_usage_by_request(events).values():
        arm = arm_of.get(arrival)
        phase = phase_of.get(arrival)
        if arm is not None and phase is not None:
            out[phase][arm]['unknown_usage_calls'] += 1
    for phase in out:
        for arm in out[phase]:
            out[phase][arm]['wall_seconds'] = round(out[phase][arm]['wall_seconds'], 6)
            out[phase][arm]['tokens_are_lower_bound'] = \
                out[phase][arm]['unknown_usage_calls'] > 0
    return out


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
    'hardware_allowlist': 'hardware_allowlist',
}


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
        manifest = (cfg.get('llama_cpp') or {}).get('serving_manifest_sha256')
        if manifest is not None:
            out['serving_manifest_sha256'] = str(manifest)
        receipt = cfg.get('receipt') or {}
        for member in ('golden_props_sha256', 'golden_generation_settings_sha256'):
            table = receipt.get(member)
            if isinstance(table, Mapping):
                got = {k: str(v) for k, v in sorted(table.items()) if v is not None}
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


def host_quiescence_gate(ctx: RunContext) -> lab_hostcheck.ScanResult | None:
    """The HARD gate of protocol 5.7, run before a trial may open its chain.

    Returns the clean scan, returns None when this invocation is not gated, and otherwise
    raises ``lab_hostcheck.HostNotQuiescent`` -- which is a ``PreflightError`` -- naming
    the offenders.  It refuses on an unproven host as well as on a dirty one."""
    if not host_scan_is_required(ctx.cfg):
        return None
    return lab_hostcheck.preflight_host_quiescent(own_harness_pids())


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
        for server_id, spec in sorted(self.ctx.servers.items()):
            body = self.server_started_body(server_id, spec)
            self.append('server_started', body, durable=True)
            self.server_ok[server_id] = True

    def server_started_body(self, server_id: str, spec: ServerSpec) -> dict:
        if self.rt.get('sim'):
            return {
                'server_id': server_id, 'pid': 0, 'port': int(spec.port),
                'argv_sha256': sha256_canonical(lab_server.server_argv(spec)),
                'gguf': {'bytes': int(spec.gguf_bytes), 'sha256': spec.gguf_sha256},
                'props_sha256': sha256_text('sim'), 'props_matches_golden': True,
                'total_slots': int(spec.n_slots), 'n_ctx': int(spec.ctx_per_slot),
                'load_seconds': 0.0,
                'smoke': {'request_sha256': sha256_text('sim'),
                          'receipt_matches_golden': True,
                          'usage': {k: 0 for k in USAGE_KEYS},
                          'timings': {'cache_n': 0, 'prompt_n': 0, 'prompt_ms': 0.0,
                                      'predicted_n': 0, 'predicted_ms': 0.0,
                                      'predicted_per_second': 0.0},
                          'ok': True}}
        probe = lab_server.probe(spec.base_url)
        props = probe.get('props') or {}
        return {
            'server_id': server_id, 'pid': int(self.server_pids.get(server_id, 0)),
            'port': int(spec.port),
            'argv_sha256': sha256_canonical(lab_server.server_argv(spec)),
            'gguf': {'bytes': int(spec.gguf_bytes), 'sha256': spec.gguf_sha256},
            'props_sha256': sha256_canonical(props),
            'props_matches_golden': True,
            'total_slots': int(props.get('total_slots') or spec.n_slots),
            'n_ctx': int(lab_server.props_n_ctx_per_slot(props) or spec.ctx_per_slot),
            'load_seconds': 0.0,
            'smoke': {'request_sha256': sha256_text('mock'),
                      'receipt_matches_golden': True,
                      'usage': {k: 0 for k in USAGE_KEYS},
                      'timings': {'cache_n': 0, 'prompt_n': 0, 'prompt_ms': 0.0,
                                  'predicted_n': 0, 'predicted_ms': 0.0,
                                  'predicted_per_second': 0.0},
                      'ok': True}}

    def scrape(self, point: str) -> None:
        execution = self.cfg.get('execution') or {}
        for server_id, spec in sorted(self.ctx.servers.items()):
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
        execution = self.cfg.get('execution') or {}
        every = float(execution.get('health_poll_s', 5))
        now = time.monotonic()
        if now - self.last_health < every:
            return
        self.last_health = now
        for server_id, spec in sorted(self.ctx.servers.items()):
            if self.rt.get('sim'):
                ok, busy = True, len(self.open_arrivals)
            else:
                got = lab_server.health(spec.base_url)
                ok = bool(got.get('ok'))
                busy = int(got.get('slots_busy') or 0)
            self.server_ok[server_id] = ok
            self.append('server_health', {'server_id': server_id, 'ok': ok,
                                          'slots_busy': busy, 'rss_bytes': 0,
                                          'clock_anomaly': False})

    # -- anchors --------------------------------------------------------------
    def request_anchor(self, trigger: str, *, blocking: bool) -> None:
        assert self.log is not None
        seg_path = self.ctx.paths.events / (lab_eventlog.SEGMENT_FMT
                                            % self.log.segment_index)
        raw = seg_path.read_bytes() if seg_path.exists() else b''
        self.anchor_seq += 1
        publish = trigger in (self.cfg.get('anchor', {}).get('publish_segments_at') or [])
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
            'trigger': trigger, 'blocking': bool(blocking),
        }
        self.log.close_segment(anchor_body=body)
        request = {
            'request_id': uuid.uuid4().hex, 'trial': self.ctx.trial,
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

    def ingest_receipts(self) -> bool:
        """Turn the anchor process's receipts into ``anchor_receipt`` / ``anchor_failed``.

        The orchestrator remains the only writer of the chain (AD-2, PG-12)."""
        path = self.ctx.paths.anchor_spool / 'receipts.jsonl'
        lines, self.receipt_offset = read_spool_lines(path, self.receipt_offset)
        got = False
        for row in lines:
            pending = self.pending_anchor
            anchor_seq = self.anchor_seq
            if pending is not None and row.get('request_id') == pending['request_id']:
                got = True
                self.pending_anchor = None
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
                self.append('anchor_failed', {
                    'anchor_seq': anchor_seq,
                    'error_class': str(row.get('error_class') or 'api'),
                    'blocking': bool(pending['blocking']) if pending else False,
                }, durable=True)
        return got

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

    def kill(self, att: Attempt) -> None:
        proc = att.proc
        if proc is None:
            return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:                               # noqa: BLE001
                pass
        try:
            proc.wait(timeout=5)
        except Exception:                                   # noqa: BLE001
            pass

    def finished(self, att: Attempt) -> int | None:
        proc = att.proc
        if proc is None:
            return 0
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
    att.revealed = True
    att.ended_mono = att.ended_mono or time.monotonic()
    if att.arrival in world.open_arrivals:
        world.open_arrivals.remove(att.arrival)
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
        'post_decision': bool(att.post_decision)}, durable=True)
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
        if world.pairs_enrolled >= world.max_pairs:
            # the horizon: no further enrollment is possible, so a deferred resume look is
            # written here and the frozen decide() runs on it (7.1 row 4a).
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
        if not world.open_arrivals:
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
        if world.open_arrivals:
            return 'DRAINING'
        return 'ANCHOR_BLOCK'

    if state == 'ANCHOR_BLOCK':
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

    if state == 'POST_DECISION':
        world.pump()
        if world.dispatch_follow_up():
            return 'POST_DECISION'
        if world.open_arrivals:
            return 'POST_DECISION'
        return 'CLOSING'

    if state == 'CLOSING':
        world.close_trial('ended')
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
        'golden_props_sha256': {k: str(v or sha256_text(k))
                                for k, v in (cfg['receipt']['golden_props_sha256']).items()},
        'golden_generation_settings_sha256': {
            k: str(v or sha256_text(k))
            for k, v in (cfg['receipt']['golden_generation_settings_sha256']).items()},
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
    decision = None
    for arrival in list(self.open_arrivals):
        att = self.attempts[arrival]
        try:
            ingest_spool(self, att)
        except SpoolError:
            self._interrupt(att)
            continue
        if att.revealed:
            continue
        rc = self.finished(att)
        if rc is not None:
            ingest_spool(self, att)
            if not att.revealed:
                self._terminal(att, 'worker_died')
        elif (time.monotonic() - att.dispatched_mono) > self.hard_cap_s:
            self.kill(att)
            ingest_spool(self, att)
            if not att.revealed:
                self._terminal(att, 'episode_timeout')
    # E2: flush the used-seed registry as soon as this pump saw new seeds, not only at the
    # next dispatch.  Without this the LAST pair's seeds never reach the file -- the trial
    # ends with no further dispatch -- and the next trial of the program would start from a
    # registry that is missing them.  The reconstruction at that trial's start would still
    # recover them from the spools, but a file that disagrees with the spools is exactly the
    # kind of quiet staleness this repair exists to remove.  The call is a no-op unless the
    # set actually grew, so a 50 ms poll does not rewrite the file.
    self.persist_seed_registry()
    self._auto_abort()
    return self.decision


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
    limit = int(((self.cfg.get('execution') or {}).get('auto_abort') or {})
                .get('consecutive_infrastructure_failures', 10))
    if self.consecutive_terminal >= limit:
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
    if len(self.open_arrivals) >= workers:
        return False
    arrival = self.next_unassigned_arrival()
    if arrival is None:
        return False
    if self.post_decision_dispatched and self.post_decision_dispatched % 50 == 0 \
            and self.open_arrivals:
        return False                                  # drain before the quiescent scrape
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
    if self.post_decision_dispatched % 50 == 0:
        self.scrape('quiescent')
    return True


def _w_close_trial(self: World, status: str) -> None:
    """CLOSING / ABORTED (7.1 rows 26 and 27)."""
    assert self.log is not None
    self.flush_looks()
    self.scrape('trial_end')
    self.reconcile()
    ledger = exposure_recount(self.log.events)
    write_json_atomic(self.ctx.paths.results / 'exposure_ledger.json', ledger,
                      durable=True)
    for server_id in sorted(self.ctx.servers):
        pid = int(self.server_pids.get(server_id, 0))
        result = {'returncode': None, 'seconds': 0.0}
        if pid and not self.rt.get('sim'):
            result = lab_server.stop(pid)
        self.append('server_stopped', {
            'server_id': server_id, 'pid': pid,
            'returncode': (int(result['returncode'])
                           if result.get('returncode') is not None else None),
            'seconds': float(result.get('seconds') or 0.0)}, durable=True)
    self.seal_deposit()
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
    }
    self.append('trial_ended' if status == 'ended' else 'trial_aborted', body,
                durable=True)
    self.request_anchor('trial_ended' if status == 'ended' else 'trial_aborted',
                        blocking=True)
    self.wait_for_receipt()


def _w__terminal_by_arm(self: World) -> dict:
    out = {arm: 0 for arm in lab_common.ARMS}
    assert self.log is not None
    for ev in self.log.events:
        if ev['type'] == 'episode_revealed' \
                and ev['body']['outcome'].get('error_class') in TERMINAL_CLASSES:
            out[ev['body']['arm']] = out.get(ev['body']['arm'], 0) + 1
    return out


def _w_reconcile(self: World) -> None:
    """One ``usage_reconciliation`` per server for the whole-trial window (PG-10)."""
    assert self.log is not None
    for server_id in sorted(self.ctx.servers):
        prompt = predicted = 0
        for ev in self.log.events:
            if ev['type'] == 'llm_response' and ev['body']['server_id'] == server_id:
                prompt += int(ev['body']['usage']['prompt_tokens'])
                predicted += int(ev['body']['usage']['completion_tokens'])
        counters = self.counters.get(server_id) or {}
        delta = {'prompt': int(counters.get('prompt_tokens_total') or 0),
                 'predicted': int(counters.get('tokens_predicted_total') or 0)}
        summed = {'prompt': prompt, 'predicted': predicted}
        residual = {'prompt': delta['prompt'] - prompt,
                    'predicted': delta['predicted'] - predicted}
        lost = not bool(counters)
        self.usage_sum[server_id] = summed
        self.append('usage_reconciliation', {
            'server_id': server_id, 'window': 'trial', 'window_from_seq': 0,
            'window_to_seq': int(self.log.seq - 1), 'counter_delta': delta,
            'client_usage_sum': summed,
            'residual': {'prompt': None if lost else residual['prompt'],
                         'predicted': None if lost else residual['predicted']},
            'reconciliation_defect': bool(not lost and (residual['prompt']
                                                        or residual['predicted'])),
            'counters_lost': bool(lost)}, durable=True)


def _w_seal_deposit(self: World) -> None:
    records = sorted(self.ctx.paths.records.glob('*.json')) \
        if self.ctx.paths.records.exists() else []
    spools = sorted(self.ctx.paths.spools.glob('*.jsonl')) \
        if self.ctx.paths.spools.exists() else []
    manifest = {'records': [sha256_file(p) for p in records],
                'spools': [sha256_file(p) for p in spools]}
    self.append('deposit_sealed', {
        'deposit_sha256': sha256_canonical(manifest),
        'deposit_bytes': sum(p.stat().st_size for p in records + spools),
        'n_records': len(records), 'n_spools': len(spools)}, durable=True)


def _w_write_pause(self: World) -> None:
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

    if plan.reenroll_pair is not None:
        world.reenroll_pair(plan.reenroll_pair)
        world.draw_coin()
        world.dispatch_pair()
        return 'RUNNING'

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
    for arrival in plan.dispatch_after_resume:
        world.redispatch(arrival, plan)

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
    self.pairs_completed = sum(
        1 for pair in set(self.pair_of_arrival.values())
        if len([a for a, p in self.pair_of_arrival.items() if p == pair
                and self.attempts.get(a) is not None and self.attempts[a].revealed]) == 2)
    self.post_decision_dispatched = sum(1 for e in events
                                        if e['type'] == 'arm_assigned_by_decision')


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
    att.offset = 0
    att.lines = []
    att.suppress_final = True
    if arrival not in self.open_arrivals:
        self.open_arrivals.append(arrival)
    ingest_spool(self, att)
    if not att.revealed:
        self._terminal(att, 'interrupted')


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
    ``'paused'``).  Single-threaded."""
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
            if nxt in ('ENDED', 'ENDED_ABORTED', 'ENDED_PAUSED'):
                status = {'ENDED': 'ended', 'ENDED_ABORTED': 'aborted',
                          'ENDED_PAUSED': 'paused'}[nxt]
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
    servers: dict[str, ServerSpec] = {}
    for server_id, sc in sorted((fcfg.get('servers') or {}).items()):
        if server_id not in used:
            continue
        port = int((rt.get('ports') or {}).get(server_id, sc['port']))
        servers[server_id] = ServerSpec(
            server_id=server_id, port=port, alias=str(sc['alias']),
            gguf_path=Path(str(rt.get('gguf_path') or sc['file'])),
            gguf_bytes=int(sc['bytes']), gguf_sha256=str(sc['sha256_expected']),
            llama_bin=Path(str(rt.get('llama_bin') or 'llama-server')),
            llama_commit=str(fcfg['llama_cpp']['commit']),
            args=tuple(str(a) for a in fcfg['llama_args']),
            log_path=paths.logs / f'llama_{port}.log',
            n_slots=int(fcfg['execution']['workers']),
            n_ctx=int(_arg_value(fcfg['llama_args'], '-c', 16384)))
    golden = dict(rt.get('golden') or {})
    mc = MonitorConfig.from_config(fcfg, trial)
    rt.setdefault('config_sha256', sha256_file(freeze_dir / 'config.json'))
    rt.setdefault('order_sha256', sha256_file(order_path))
    rt.setdefault('roster_sha256', sha256_file(freeze_dir / 'roster.json'))
    rt.setdefault('task_content_sha256', str(roster.get('task_content_sha256')
                                             or sha256_canonical(roster)))
    cfg['_runtime'] = rt
    return RunContext(trial=trial, inv=inv or uuid.uuid4().hex, cfg=cfg,
                      bundle_sha=str(rt['bundle_sha']), paths=paths, order=list(order),
                      tasks=tasks, mc=mc, servers=servers, golden=golden)


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
    [--mock URL] [--max-pairs N (mock only)] [--results DIR] [--work DIR]``.
    Exit 0 ended, 1 aborted, 2 paused, 3 preflight refusal."""
    ap = argparse.ArgumentParser(prog='lab_orchestrator')
    ap.add_argument('--trial', required=True, choices=list(lab_common.TRIALS))
    ap.add_argument('--config', required=True)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--mock', default=None)
    ap.add_argument('--max-pairs', type=int, default=None)
    ap.add_argument('--results', default=None)
    ap.add_argument('--work', default=None)
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    results_root = Path(args.results or lab_common.RESULTS_ROOT)
    work_root = Path(args.work or lab_common.WORK_ROOT)
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
    return {'ended': 0, 'aborted': 1, 'paused': 2}.get(status, 1)


if __name__ == '__main__':                                   # pragma: no cover
    sys.exit(main())
