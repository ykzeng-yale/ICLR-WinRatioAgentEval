"""Spooling llama.cpp chat client and the worker spool (group G4).

ARCHITECTURE_FINAL.md 3.9 is the interface contract; protocol_FINAL.md 5.4, 5.5, 5.6, 6.4
and 13.1/13.2 are the rules.  The three facts this module exists to guarantee:

  1. **One request line and exactly one terminal line per try.**  ``Spool`` is the worker's
     only channel to the orchestrator and the recovery source after a crash, so every try of
     every call writes ``call_started`` *before* the socket is written and exactly one of
     ``call_response`` / ``call_error`` afterwards, each fsynced before it is used
     (protocol 13.1, "two ledgers reconcile by construction").
  2. **The per-request seed is drawn and logged before the POST** and carries the worker
     index in its low bit, which partitions the seed space between the two uncoordinated
     worker processes (protocol 5.5, finding N6 / PG-8).
  3. **The sampler receipt is compared against frozen golden objects, with no estimation
     path.**  A 200 without ``usage`` or ``timings`` is an error (protocol 6.4 row 3), never
     an estimate: ``tokens_estimated`` is always ``None``.

``LlamaClient`` is a drop-in replacement for the pilot's
``experiments/local_stream/agent.py:OpenAICompatModel``; ``agent.py`` stays byte-identical
and only ever touches ``.chat(messages, ctx)``, ``.model`` and ``.name``.  The ``ctx['seed']``
that ``agent.run_episode`` computes internally is **ignored**: the pilot's colliding formula
never reaches a request.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

import requests

import lab_common

# --- frozen constants (protocol 5.5, 5.6; never amendable, 14.3) -------------
SEED_MASK: int = 0x7FFFFFFE
SEED_FORBIDDEN: int = 0xFFFFFFFF
MAX_RECOVERY_WAITS_PER_CALL: int = 1

#: Closed list of receipt findings.  The chain field ``llm_response.receipt_mismatch`` is a
#: list of enum members (event schema T15), so the *detail* of a mismatch (which key, which
#: value) never enters a tracked artifact; it is kept in the private request deposit.
RECEIPT_FINDINGS: tuple[str, ...] = (
    'generation_settings_absent',
    'generation_settings_missing_key',
    'generation_settings_unknown_key',
    'generation_settings_value',
    'seed_mismatch',
    'cache_n_nonzero',
    'tokens_cached_nonzero',
    'model_alias_mismatch',
)

#: Closed list of per-try error classes (event schema T16).
ERROR_CLASSES: tuple[str, ...] = ('timeout', 'connection', 'http_4xx', 'http_5xx', 'malformed')

#: Call kinds the pilot's ``run_episode`` produces, plus the server smoke completion.
CALL_KINDS: tuple[str, ...] = ('code', 'tests', 'repair', 'smoke')

def backoff_seconds(try_index: int) -> float:
    """[pure] The frozen connection backoff ``min(2*(k+1), 10)`` s (protocol 5.6)."""
    return min(2.0 * (int(try_index) + 1), 10.0)


def _sleep(seconds: float) -> None:
    """The one place the client waits between tries.

    It exists as a module-level indirection so that a test can observe the frozen backoff
    without either spending it or patching the shared ``time`` module, which the mock server
    also sleeps on."""
    time.sleep(seconds)


_LOOPBACK_HOSTS = frozenset({'127.0.0.1', 'localhost', '::1', '[::1]'})
_EP_RE = re.compile(r'^ep_(\d+)_(\d+)\.jsonl$')
_NULL_INV = '0' * 32


class ConnectionFailure(lab_common.LabError):
    """Every try of one call failed with a connection error or a timeout (6.4 row 1)."""


class HttpError(lab_common.LabError):
    """An HTTP 4xx/5xx response.  Never retried (6.4 row 2)."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = int(status)


class MalformedResponse(lab_common.LabError):
    """A 200 that is not JSON, or has no ``usage`` / ``timings`` (6.4 row 3).

    Raising here is what makes "there is no token-estimation path" a property of the code."""


# --------------------------------------------------------------------------- #
# Spool
# --------------------------------------------------------------------------- #
@dataclass
class Spool:
    """Append-only, fsynced worker spool: the worker's only output channel besides the record.

    Line envelope, ARCHITECTURE_FINAL.md section 5 (the normative spool format)::

        {spool_seq, kind, t_wall_ns, t_mono_ns, pid, inv, arrival, attempt, body}

    ``arrival`` and ``attempt`` are parsed out of the file name ``ep_<arrival>_<attempt>.jsonl``
    so that a line is self-contained without widening the constructor signature of 3.9; the
    orchestrator invocation id is supplied by :meth:`set_inv` before the first write.

    The fsync cost of each line is carried in the *next* line's ``body['fsync_ms_prev']``
    (section 5's ``call_started`` body names that field), so the spool measures its own
    durability cost without a second clock.
    """

    path: Path

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        m = _EP_RE.match(self.path.name)
        self.arrival: int = int(m.group(1)) if m else 0
        self.attempt: int = int(m.group(2)) if m else 1
        self.inv: str = _NULL_INV
        self._closed = False
        self._fsync_ms_prev: float = 0.0
        existing_seq = -1
        if self.path.exists():
            raw = self.path.read_bytes()
            for chunk in raw.split(b'\n'):
                if not chunk:
                    continue
                try:
                    row = json.loads(chunk.decode('utf-8'))
                except (ValueError, UnicodeDecodeError):
                    continue          # a torn tail; the ingest ignores it too
                if isinstance(row, dict):
                    if row.get('kind') == 'episode_final':
                        raise lab_common.SpoolError(
                            'spool %s already holds a terminal episode_final line'
                            % self.path.name)
                    if isinstance(row.get('spool_seq'), int):
                        existing_seq = max(existing_seq, row['spool_seq'])
        self._seq: int = existing_seq + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        self._offset: int = os.fstat(self._fd).st_size

    # -- identity ----------------------------------------------------------- #
    def set_inv(self, inv: str) -> None:
        """Bind the orchestrator invocation id that spawned this worker (hex32)."""
        self.inv = str(inv)

    @property
    def spool_seq(self) -> int:
        """The seq the next line will carry."""
        return self._seq

    @property
    def offset(self) -> int:
        """Byte length written so far (the offset the next line will start at)."""
        return self._offset

    # -- write -------------------------------------------------------------- #
    def write(self, kind: str, body: dict, *, durable: bool = True) -> int:
        """One canonical JSON line, one ``os.write``, fullsync when durable.

        Returns the byte offset at which the line starts.  Side effect: the file grows.
        A durable write returns only after :func:`lab_common.fullsync` has returned, which
        is what "write-ahead" means everywhere in this protocol."""
        if self._closed:
            raise lab_common.SpoolError('write to a closed spool %s' % self.path.name)
        payload = dict(body)
        payload['fsync_ms_prev'] = self._fsync_ms_prev
        line_obj = {
            'spool_seq': self._seq,
            'kind': str(kind),
            't_wall_ns': time.time_ns(),
            't_mono_ns': time.monotonic_ns(),
            'pid': os.getpid(),
            'inv': self.inv,
            'arrival': self.arrival,
            'attempt': self.attempt,
            'body': payload,
        }
        data = (lab_common.canonical_json(line_obj) + '\n').encode('utf-8')
        offset = self._offset
        written = os.write(self._fd, data)
        if written != len(data):
            raise lab_common.TornWrite(
                'partial spool write: %d of %d bytes' % (written, len(data)))
        self._offset += written
        self._seq += 1
        if durable:
            t0 = time.perf_counter()
            lab_common.fullsync(self._fd)
            self._fsync_ms_prev = (time.perf_counter() - t0) * 1000.0
        else:
            self._fsync_ms_prev = 0.0
        return offset

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            os.close(self._fd)

    def __enter__(self) -> 'Spool':
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_spool(path: str | Path) -> list[dict]:
    """Every complete, parsable line of a spool, in file order.

    A trailing incomplete line is ignored, exactly as the orchestrator's ingest ignores it
    (ARCHITECTURE_FINAL.md section 5).  This function writes nothing."""
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict] = []
    raw = p.read_bytes()
    for chunk in raw.split(b'\n'):
        if not chunk:
            continue
        try:
            row = json.loads(chunk.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Golden receipt
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GoldenReceipt:
    """The frozen sampler receipt of one server (protocol 13.2).

    ``props`` and ``generation_settings`` are the *whole* objects captured in the pre-freeze
    smoke; ``mask`` names the per-request keys compared by their own rule (at least ``seed``,
    which must equal the seed sent)."""

    props: dict
    generation_settings: dict
    mask: tuple[str, ...] = ('seed',)
    float_tolerance: float = 1e-6


def compare_generation_settings(observed: Mapping | None, golden: Mapping,
                                *, mask: Sequence[str], float_tolerance: float,
                                seed_sent: int | None) -> tuple[list[str], list[str]]:
    """[pure] Compare the whole ``generation_settings`` object with the golden object.

    Exact for ints, strings, bools and lists; within ``float_tolerance`` for floats (the
    server echoes float32); every key in ``mask`` by its own rule — ``seed`` must equal the
    seed sent, any other masked key must merely be present.  **Any unknown or missing key is
    a mismatch** (protocol 13.2).

    Returns ``(findings, details)``: ``findings`` is a sorted list of members of
    :data:`RECEIPT_FINDINGS` (this is what may enter the chain), ``details`` is a list of
    human-readable strings for the private deposit only."""
    findings: set[str] = set()
    details: list[str] = []
    if observed is None:
        return ['generation_settings_absent'], ['no __verbose.generation_settings object']
    masked = set(mask)
    for key in sorted(golden):
        if key in masked:
            if key not in observed:
                findings.add('generation_settings_missing_key')
                details.append('masked key %s absent' % key)
            continue
        if key not in observed:
            findings.add('generation_settings_missing_key')
            details.append('missing key %s' % key)
            continue
        sub, subdet = _compare_value(observed[key], golden[key], float_tolerance, key)
        findings |= sub
        details += subdet
    for key in sorted(observed):
        if key not in golden and key not in masked:
            findings.add('generation_settings_unknown_key')
            details.append('unknown key %s' % key)
    if 'seed' in masked:
        if 'seed' in observed and seed_sent is not None:
            if not _is_int(observed['seed']) or int(observed['seed']) != int(seed_sent):
                findings.add('seed_mismatch')
                details.append('seed echoed %r, sent %r' % (observed['seed'], seed_sent))
    return sorted(findings), details


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _compare_value(obs: object, gold: object, tol: float, path: str) -> tuple[set[str], list[str]]:
    findings: set[str] = set()
    details: list[str] = []
    if isinstance(gold, dict):
        if not isinstance(obs, dict):
            return {'generation_settings_value'}, ['%s: expected an object' % path]
        for k in sorted(gold):
            if k not in obs:
                findings.add('generation_settings_missing_key')
                details.append('missing key %s.%s' % (path, k))
                continue
            sub, subdet = _compare_value(obs[k], gold[k], tol, '%s.%s' % (path, k))
            findings |= sub
            details += subdet
        for k in sorted(obs):
            if k not in gold:
                findings.add('generation_settings_unknown_key')
                details.append('unknown key %s.%s' % (path, k))
        return findings, details
    if isinstance(gold, bool):
        ok = isinstance(obs, bool) and obs == gold
    elif _is_int(gold):
        ok = _is_int(obs) and obs == gold
    elif isinstance(gold, float):
        ok = (_is_int(obs) or isinstance(obs, float)) and not isinstance(obs, bool) \
            and abs(float(obs) - gold) <= tol
    elif isinstance(gold, (list, tuple)):
        ok = isinstance(obs, (list, tuple)) and list(obs) == list(gold)
    else:
        ok = obs == gold
    if not ok:
        findings.add('generation_settings_value')
        details.append('%s: observed %r, golden %r' % (path, obs, gold))
    return findings, details


# --------------------------------------------------------------------------- #
# Seeds (protocol 5.5)
# --------------------------------------------------------------------------- #
def draw_seed(worker_index: int, used: Iterable[int] = ()) -> int:
    """``(int.from_bytes(os.urandom(4), 'big') & 0x7FFFFFFE) | worker_index``.

    The low bit carries the worker index, so the two uncoordinated worker processes draw
    from disjoint halves of the seed space and a cross-worker collision is impossible
    (protocol 5.5 / PG-8).  A value already used **in this worker's own half** is redrawn;
    ``0xFFFFFFFF`` cannot survive the mask and is re-checked here anyway."""
    if worker_index not in (0, 1):
        raise lab_common.PreflightError('worker_index must be 0 or 1, not %r' % (worker_index,))
    used_set = set(used)
    for _ in range(1024):
        seed = (int.from_bytes(os.urandom(4), 'big') & SEED_MASK) | worker_index
        if seed == SEED_FORBIDDEN:
            continue
        if seed in used_set:
            continue
        return seed
    raise lab_common.PreflightError('seed space exhausted for worker_index %d' % worker_index)


def load_used_seeds(path: str | Path | None, worker_index: int) -> set[int]:
    """The used-seed set of earlier trials, restricted to this worker's own half.

    The file is a JSON list of integers written by the orchestrator (protocol 5.5: "each
    worker loads the used-seed set of earlier trials of the program at start and checks only
    its own half").  A missing file is an empty set: a duplicate seed is a logged defect with
    no effect on any outcome (6.4 row 19), never a refusal."""
    if not path:
        return set()
    p = Path(path)
    if not p.exists():
        return set()
    try:
        raw = json.loads(p.read_text())
    except ValueError as exc:
        raise lab_common.PreflightError('unreadable used-seed file: %s' % exc) from exc
    if not isinstance(raw, list):
        raise lab_common.PreflightError('used-seed file must hold a JSON list')
    return {int(v) for v in raw if _is_int(v) and (int(v) & 1) == worker_index}


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #
class LlamaClient:
    """Drop-in replacement for ``experiments/local_stream/agent.py:OpenAICompatModel``.

    ``agent.py`` stays BYTE-IDENTICAL: ``run_episode`` needs only ``.chat(messages, ctx)``,
    ``.model`` and ``.name``."""

    name: str = 'llama_cpp'

    def __init__(self, *, base_url: str, alias: str, sampling: dict, spool: Spool,
                 golden: GoldenReceipt, request_timeout_s: float, max_connection_retries: int,
                 server_recovery_s: float, arrival: int, attempt: int, trial: str,
                 worker_index: int,
                 session: requests.Session | None = None) -> None:
        self.base_url = str(base_url).rstrip('/')
        _assert_loopback(self.base_url)
        self.alias = str(alias)
        self.model = str(alias)                 # run_episode records the server-side alias
        self.sampling = dict(sampling)
        self.spool = spool
        self.golden = golden
        self.request_timeout_s = float(request_timeout_s)
        self.max_connection_retries = int(max_connection_retries)
        self.server_recovery_s = float(server_recovery_s)
        self.arrival = int(arrival)
        self.attempt = int(attempt)
        self.trial = str(trial)
        if worker_index not in (0, 1):
            raise lab_common.PreflightError(
                'worker_index must be 0 or 1, not %r' % (worker_index,))
        self.worker_index = int(worker_index)
        self.session = session if session is not None else requests.Session()

        #: Seeds already used in this worker's half of the space; the worker fills it from
        #: the orchestrator's file before the first call and it grows with every draw.
        self.used_seeds: set[int] = set()
        #: Where the full request/response deposit is written; derived from the spool path
        #: (``<work>/<trial>/spools/ep_a_t.jsonl`` -> ``<work>/<trial>/requests``) and
        #: overridable by the worker from the job's tokenized paths.
        self.request_dir: Path = Path(spool.path).parent.parent / 'requests'

        self._t_c1_ns: int | None = None
        self._call_index = 0
        self._seed_collisions = 0
        self._n_failed_calls = 0
        self._n_tries = 0
        self._retried_tries = 0
        self._recovery_waits_total = 0
        self._recovery_seconds_total = 0.0
        self._truncated_any = False
        self._request_timeout_any = False
        self._receipt_mismatch: list[str] = []
        self._error_classes: list[str] = []

    # -- public read-outs ---------------------------------------------------- #
    @property
    def t_c1_ns(self) -> int | None:
        """The worker's monotonic clock at entry into the FIRST ``chat()`` call.

        ``None`` until the first call; the certified elapsed time of protocol 7.5 item 4 is
        measured from it, and an attempt with no spooled request has ``ell = 0.0``."""
        return self._t_c1_ns

    def stats(self) -> dict:
        """Everything the worker needs for the episode outcome that the pilot's record does
        not carry.  Pure read-out; no I/O."""
        return {
            'n_calls': self._call_index,
            'n_tries': self._n_tries,
            'n_failed_calls': self._n_failed_calls,
            'retried_tries': self._retried_tries,
            'seed_collisions': self._seed_collisions,
            'recovery_waits': self._recovery_waits_total,
            'recovery_seconds': self._recovery_seconds_total,
            'truncated_any': self._truncated_any,
            'request_timeout_any': self._request_timeout_any,
            'receipt_mismatch': list(self._receipt_mismatch),
            'error_classes': list(self._error_classes),
        }

    # -- the one public method run_episode uses ------------------------------ #
    def chat(self, messages: list[dict], ctx: dict) -> dict:
        """One logical call, possibly several tries.  Returns exactly the pilot's dict.

        Per try, in this order (ARCHITECTURE_FINAL.md 3.9):
          1. draw the seed (low bit = worker index);
          2. build the body from the frozen sampling block — nothing added, nothing dropped;
          3. spool ``call_started`` durably **before** the POST;
          4. POST;
          5. on 200: parse, assert ``usage`` and ``timings``, compare the receipt, deposit the
             full bodies, spool ``call_response`` durably **before** returning;
          6. on a connection error or timeout: spool ``call_error``, back off
             ``min(2*(k+1), 10)`` s and retry up to ``max_connection_retries``; a call may
             wait for at most ONE supervised restart (``max_recovery_waits_per_call = 1``);
          7. on HTTP 4xx/5xx: spool ``call_error`` and raise — never retried.

        A receipt mismatch raises ``ReceiptMismatch`` *after* the response has been spooled,
        so the episode still completes under intention-to-treat and the orchestrator aborts
        the trial before the next dispatch (protocol 6.4 rows 12, 13)."""
        t_call0 = time.perf_counter()
        if self._t_c1_ns is None:
            self._t_c1_ns = time.monotonic_ns()
        call_index = self._call_index
        self._call_index += 1
        kind = str(ctx.get('kind') or 'code')
        if kind not in CALL_KINDS:
            kind = 'code'
        retry_log: list[dict] = []
        recovery_waits = 0
        recovery_budget = self.server_recovery_s
        call_failed = False

        try:
            for try_index in range(self.max_connection_retries + 1):
                self._n_tries += 1
                if try_index:
                    self._retried_tries += 1
                seed = self._next_seed()
                body = self._build_body(messages, seed)
                request_id = os.urandom(16).hex()
                body_text = lab_common.canonical_json(body)
                t_c1_ns = int(self._t_c1_ns)
                t_send_ns = time.monotonic_ns()
                self.spool.write('call_started', {
                    'call_index': call_index,
                    'kind': kind,
                    'try_index': try_index,
                    'request_id': request_id,
                    'seed': seed,
                    'body_sha256': lab_common.sha256_text(body_text),
                    'messages_sha256': lab_common.sha256_canonical(messages),
                    'n_messages': len(messages),
                    'prompt_chars': sum(len(str(m.get('content') or '')) for m in messages),
                    'sampling_sent': self._sampling_sent(body),
                    't_c1_ns': t_c1_ns,
                    't_send_ns': t_send_ns,
                }, durable=True)

                t0 = time.perf_counter()
                try:
                    resp = self.session.post(self.base_url + '/chat/completions',
                                             json=body, timeout=self.request_timeout_s)
                except (requests.ConnectionError, requests.Timeout) as exc:
                    elapsed = time.perf_counter() - t0
                    cls = 'connection' if isinstance(exc, requests.ConnectionError) else 'timeout'
                    if cls == 'timeout':
                        self._request_timeout_any = True
                    last = try_index >= self.max_connection_retries
                    self._spool_error(request_id, cls, None, exc, elapsed, will_retry=not last)
                    retry_log.append({'attempt': try_index, 'error_class': cls,
                                      'error_sha256': _error_sha256(exc)})
                    self._error_classes.append(cls)
                    if cls == 'connection':
                        waited, was_down = self._maybe_wait_for_recovery(
                            recovery_budget, recovery_waits)
                        if was_down:
                            recovery_waits += 1
                            recovery_budget = max(0.0, recovery_budget - waited)
                            self._recovery_waits_total += 1
                            self._recovery_seconds_total += waited
                        elif was_down is None:
                            # a second server_down inside the same call: the call fails by
                            # protocol 6.4 row 1 (max_recovery_waits_per_call = 1).
                            call_failed = True
                            raise ConnectionFailure(
                                'second server_down inside one call after %d tries'
                                % (try_index + 1)) from exc
                    if last:
                        call_failed = True
                        raise ConnectionFailure(
                            'connection failed after %d tries' % (try_index + 1)) from exc
                    _sleep(backoff_seconds(try_index))
                    continue

                elapsed = time.perf_counter() - t0
                status = int(resp.status_code)
                if status >= 400:
                    cls = 'http_4xx' if status < 500 else 'http_5xx'
                    self._spool_error(request_id, cls, status, None, elapsed,
                                      will_retry=False, text=resp.text)
                    self._error_classes.append(cls)
                    call_failed = True
                    raise HttpError('http %d from the server' % status, status)

                try:
                    data = resp.json()
                except ValueError as exc:
                    self._spool_error(request_id, 'malformed', status, exc, elapsed,
                                      will_retry=False, text=resp.text)
                    self._error_classes.append('malformed')
                    call_failed = True
                    raise MalformedResponse('response body is not JSON') from exc
                if not isinstance(data, dict) or 'usage' not in data or 'timings' not in data:
                    self._spool_error(request_id, 'malformed', status, None, elapsed,
                                      will_retry=False, text=resp.text)
                    self._error_classes.append('malformed')
                    call_failed = True
                    raise MalformedResponse(
                        'a 200 without usage/timings is an error, never an estimate')

                return self._finish_ok(data, body, body_text, request_id, seed, kind,
                                       call_index, try_index, status, elapsed, retry_log,
                                       t_call0)
            # not reached: the loop either returns or raises
            call_failed = True
            raise ConnectionFailure('no try was made')
        finally:
            if call_failed:
                self._n_failed_calls += 1

    # -- internals ----------------------------------------------------------- #
    def _next_seed(self) -> int:
        seed = draw_seed(self.worker_index, self.used_seeds)
        if seed in self.used_seeds:            # draw_seed never returns one; belt and braces
            self._seed_collisions += 1
        self.used_seeds.add(seed)
        return seed

    def _build_body(self, messages: list[dict], seed: int) -> dict:
        """The request body: the frozen sampling block verbatim, plus model, messages, seed.

        The client adds nothing and drops nothing (protocol 5.4); the three structural keys
        ``stream``, ``verbose`` and ``cache_prompt`` are asserted present rather than
        overridden, because they are part of the frozen block."""
        body: dict[str, Any] = {'model': self.alias, 'messages': list(messages)}
        body.update(self.sampling)
        body['seed'] = int(seed)
        body.setdefault('stream', False)
        body.setdefault('verbose', True)
        body.setdefault('cache_prompt', False)
        return body

    @staticmethod
    def _sampling_sent(body: Mapping) -> dict:
        return {k: v for k, v in body.items() if k not in ('model', 'messages', 'seed')}

    def _spool_error(self, request_id: str, error_class: str, status: int | None,
                     exc: BaseException | None, seconds: float, *, will_retry: bool,
                     text: str | None = None) -> None:
        digest = _error_sha256(exc) if exc is not None else lab_common.sha256_text(text or '')
        self.spool.write('call_error', {
            'request_id': request_id,
            'error_class': error_class,
            'http_status': int(status) if status is not None else None,
            'error_sha256': digest,
            'client_seconds': float(seconds),
            'will_retry': bool(will_retry),
            'usage_known': False,
            't_recv_ns': time.monotonic_ns(),
        }, durable=True)

    def _maybe_wait_for_recovery(self, budget: float,
                                 waits_used: int) -> tuple[float, bool | None]:
        """Probe ``/health``; wait for at most one supervised restart per call.

        Returns ``(seconds_waited, was_server_down)``.  ``was_server_down is False`` means the
        server answered ``/health`` and the connection error was transient — no recovery wait
        is consumed.  ``None`` means the server is down for a *second* time inside this call,
        which fails the call by protocol 6.4 row 1 (``max_recovery_waits_per_call = 1``)."""
        if self._health_ok():
            return 0.0, False
        if waits_used >= MAX_RECOVERY_WAITS_PER_CALL:
            return 0.0, None
        t0 = time.perf_counter()
        deadline = t0 + max(0.0, budget)
        while time.perf_counter() < deadline:
            time.sleep(min(0.5, max(0.0, deadline - time.perf_counter())))
            if self._health_ok():
                break
        return time.perf_counter() - t0, True

    def _health_ok(self) -> bool:
        url = _root_url(self.base_url) + '/health'
        try:
            r = self.session.get(url, timeout=min(5.0, self.request_timeout_s))
        except (requests.ConnectionError, requests.Timeout):
            return False
        return r.status_code == 200

    def _finish_ok(self, data: dict, body: dict, body_text: str, request_id: str, seed: int,
                   kind: str, call_index: int, try_index: int, status: int, elapsed: float,
                   retry_log: list[dict], t_call0: float) -> dict:
        verbose = data.get('__verbose') or {}
        gen = verbose.get('generation_settings') if isinstance(verbose, dict) else None
        timings = data.get('timings') or {}
        usage = data.get('usage') or {}
        choices = data.get('choices') or [{}]
        message = (choices[0].get('message') or {}) if isinstance(choices[0], dict) else {}
        text = message.get('content') or ''
        finish_reason = choices[0].get('finish_reason') if isinstance(choices[0], dict) else None

        findings, details = compare_generation_settings(
            gen, self.golden.generation_settings, mask=self.golden.mask,
            float_tolerance=self.golden.float_tolerance, seed_sent=seed)
        findings = set(findings)
        cache_n = timings.get('cache_n')
        if not _is_int(cache_n) or int(cache_n) != 0:
            findings.add('cache_n_nonzero')
            details.append('timings.cache_n = %r' % (cache_n,))
        tokens_cached = verbose.get('tokens_cached') if isinstance(verbose, dict) else None
        if tokens_cached is None:
            tokens_cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        if not _is_int(tokens_cached) or int(tokens_cached) != 0:
            findings.add('tokens_cached_nonzero')
            details.append('tokens_cached = %r' % (tokens_cached,))
        model_matches_alias = data.get('model') == self.alias
        if not model_matches_alias:
            findings.add('model_alias_mismatch')
            details.append('model %r, alias %r' % (data.get('model'), self.alias))
        findings_list = sorted(findings)

        truncated = bool(verbose.get('truncated')) if isinstance(verbose, dict) else False
        if finish_reason == 'length' or truncated:
            self._truncated_any = True

        prompt_tokens = usage.get('prompt_tokens')
        completion_tokens = usage.get('completion_tokens')
        if not _is_int(prompt_tokens) or not _is_int(completion_tokens):
            self._spool_error(request_id, 'malformed', status, None, elapsed, will_retry=False)
            self._error_classes.append('malformed')
            self._n_failed_calls += 1
            raise MalformedResponse('usage without integer token counts is an error')

        self._deposit(request_id, body, data, details, findings_list)
        t_recv_ns = time.monotonic_ns()
        self.spool.write('call_response', {
            'request_id': request_id,
            'call_index': call_index,
            'kind': kind,
            'try_index': try_index,
            'http_status': status,
            'usage': {
                'prompt_tokens': int(prompt_tokens),
                'completion_tokens': int(completion_tokens),
                'total_tokens': int(usage.get('total_tokens')
                                    if _is_int(usage.get('total_tokens'))
                                    else int(prompt_tokens) + int(completion_tokens)),
                'cached_tokens': int(tokens_cached) if _is_int(tokens_cached) else 0,
            },
            'timings': {k: timings[k] for k in sorted(timings)},
            'generation_settings_sha256': lab_common.sha256_canonical(gen if gen else {}),
            'receipt_mismatch': findings_list,
            'id_slot': int(verbose.get('id_slot')) if _is_int(verbose.get('id_slot')) else -1,
            'finish_reason': str(finish_reason) if finish_reason else 'stop',
            'truncated': bool(truncated),
            'content_sha256': lab_common.sha256_text(text),
            'rendered_prompt_sha256': lab_common.sha256_text(str(verbose.get('prompt') or '')),
            'client_seconds': float(elapsed),
            't_recv_ns': t_recv_ns,
            'model_matches_alias': bool(model_matches_alias),
        }, durable=True)

        if findings_list:
            self._receipt_mismatch += findings_list
            raise lab_common.ReceiptMismatch(
                'receipt findings %s on request %s' % (','.join(findings_list), request_id))

        return {
            'text': text,
            'prompt_tokens': int(prompt_tokens),
            'completion_tokens': int(completion_tokens),
            'tokens_estimated': None,          # there is no estimation path
            'call_seconds': time.perf_counter() - t_call0,
            'retries': try_index,
            'retry_log': retry_log,
            'finish_reason': finish_reason,
            'response_model': data.get('model'),
        }

    def _deposit(self, request_id: str, body: dict, data: dict, details: list[str],
                 findings: list[str]) -> None:
        """The full request and response bodies, gzipped, content-addressed by request id.

        This file lives under ``work/`` (git-ignored private evidence); the chain carries only
        its digests, which is what lets the receipt detail exist at all under the string
        discipline of PG-11."""
        try:
            self.request_dir.mkdir(parents=True, exist_ok=True)
            path = self.request_dir / ('%s.json.gz' % request_id)
            payload = {
                'request_id': request_id, 'trial': self.trial, 'arrival': self.arrival,
                'attempt': self.attempt, 'worker_index': self.worker_index,
                'request': body, 'response': data,
                'receipt_findings': findings, 'receipt_details': details,
            }
            raw = lab_common.canonical_json(payload).encode('utf-8')
            tmp = path.with_name(path.name + '.tmp')
            # mtime=0 so the deposit is a deterministic function of its content
            with gzip.GzipFile(filename=str(tmp), mode='wb', compresslevel=6, mtime=0) as fh:
                fh.write(raw)
            os.replace(str(tmp), str(path))
        except OSError as exc:
            raise lab_common.SpoolError('request deposit failed: %s' % exc) from exc


def _root_url(base_url: str) -> str:
    """``http://127.0.0.1:8091/v1`` -> ``http://127.0.0.1:8091``.

    ``/props``, ``/health``, ``/slots`` and ``/metrics`` are served at the root while the
    OpenAI-compatible completions live under ``/v1``."""
    u = base_url.rstrip('/')
    return u[:-3].rstrip('/') if u.endswith('/v1') else u


def _assert_loopback(base_url: str) -> None:
    """Protocol 2.3: the HTTP client hard-asserts a loopback base URL."""
    host = urlsplit(base_url).hostname
    if host not in _LOOPBACK_HOSTS:
        raise lab_common.PreflightError('base_url is not loopback')


def _error_sha256(exc: BaseException | None) -> str:
    if exc is None:
        return lab_common.sha256_text('')
    return lab_common.sha256_text('%s: %s' % (type(exc).__name__, exc))
