"""One OS process per episode: the spool, the host-wide execution lock, the outcome.

ARCHITECTURE_FINAL.md 3.12 is the interface contract; protocol_FINAL.md 5.1 (one process per
episode, the spool as the recovery source), 5.5-5.6 (seeds, timeouts, ``max_attempts = 1``),
5.7 (the host-wide execution lock) and 6.4 (the failure-to-outcome table) are the rules.

Four facts this module exists to guarantee:

* **The attempt began iff a fsynced ``job_accepted`` spool line exists** (PG-7, critic N4).
  That line, not ``episode_started``, is the evidence; an assigned arrival without it is
  dispatched on resume as its one and only attempt (6.4 row 11c).
* **At most one generated program runs on this host at any instant.**  ``sandbox.py``'s
  containment was audited for one program at a time, and its one writable directory is
  shared by every run on the host, so two concurrent workers would let one worker's
  generated program read or overwrite the other's verification program.  The wrapper is
  installed on ``sandbox.run_program`` **before** ``agent`` and ``verify`` are imported, so
  both ``from sandbox import run_program`` bindings pick it up and every call path — self
  tests and hidden-test verification alike — takes the ``flock`` (protocol 5.7 item 1).
* **There is no re-run of any kind.**  ``max_attempts = 1``: a returned episode is never
  re-run and an attempt that does not return is revealed as a failure endpoint.
* **Every failure mode has exactly one finite outcome**, including the worker that died
  before its first POST: ``latency_s = 0.0``, ``tokens_known = 0`` (6.4 row 18, critic N5),
  so ``winstats.compare`` can never be handed a non-finite value.

A worker never writes the event chain and never learns the monitor state.  The episode hard
cap is enforced by the orchestrator, which kills the process group: a worker has no timer of
its own beyond the client's per-request timeout.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Literal, Sequence, TypedDict

import lab_common
from lab_client import (GoldenReceipt, LlamaClient, Spool, load_used_seeds, read_spool)

#: Keys removed before the T4 byte-identity comparison of two jobs of one pair.
#: The list is fixed by protocol 12.3 and PG-14 and may not be extended after the freeze:
#: ``worker_index`` is in it because the two jobs of a pair necessarily run in different
#: slots, ``inv`` because they may be dispatched by different orchestrator invocations
#: (protocol 6.4 rows 11c-11e), and the task content is deliberately **not** in the job for
#: the same reason (it is loaded from the roster file named by ``paths['tasks']``).  Every
#: key that defines the scientific configuration of the episode stays in the payload, so
#: real configuration drift between the two arms of a T4 pair still fails
#: ``t4.payload_identity``.  ``inv`` was added pre-freeze by the repair of execution-review
#: finding E3; nothing here is frozen yet, and the list must stay identical to the one in
#: ``lab_orchestrator.canonical_job_payload``.
CANONICAL_JOB_DROP: tuple[str, ...] = (
    'arm', 'arrival', 'inv', 'pair', 'position', 'task_uid', 'worker_index', 'paths',
    'assignment_seq', 'payload_sha256')

#: Outcome-level error classes (protocol 6.4).  The five per-request classes live in
#: ``lab_client.ERROR_CLASSES``; the orchestrator owns the last three.
OUTCOME_ERROR_CLASSES: tuple[str, ...] = (
    'timeout', 'connection', 'http_4xx', 'http_5xx', 'malformed', 'receipt_mismatch',
    'worker_died', 'episode_timeout', 'interrupted')

WORKER_ERROR_EXIT: int = 3


class Job(TypedDict, total=False):
    trial: str
    inv: str
    arrival: int
    attempt: int
    pair: int
    position: int
    arm: Literal['incumbent', 'candidate']
    workflow: Literal['single_shot', 'self_test_repair']
    task_uid: str
    server: dict
    worker_index: int
    sampling: dict
    limits: dict
    paths: dict
    assignment_seq: int
    payload_sha256: str


# --------------------------------------------------------------------------- #
# frozen arithmetic (protocol 5.6; computed, never typed)
# --------------------------------------------------------------------------- #
def request_timeout_s(c_max: float) -> float:
    """[pure] ``max(180, 30 * ceil(4 * c_max / 30))`` from the slowest call of the
    out-of-design calibration (protocol 5.6)."""
    return float(max(180.0, 30.0 * math.ceil(4.0 * float(c_max) / 30.0)))


def episode_hard_cap_s(execution: dict) -> float:
    """[pure] ``4*(3*T + server_recovery_s + 6) + 3*(sandbox_timeout_s + max_lock_wait_s) + 60``.

    The worst case of protocol 5.6 with ``max_recovery_waits_per_call = 1``: four calls, each
    with three tries, one recovery wait and its backoffs, plus three self-test executions each
    with its bounded lock wait.  **The harness computes this from the formula and the pinned
    ``request_timeout_s``; it never reads a typed literal** (PG-15, audit M12), which is why
    ``config.json`` carries ``episode_hard_cap_s: null`` until this function has run."""
    t = float(execution['request_timeout_s'])
    rec = float(execution['server_recovery_s'])
    sbx = float(execution['sandbox_timeout_s'])
    lock = float(execution['max_lock_wait_s'])
    return 4.0 * (3.0 * t + rec + 6.0) + 3.0 * (sbx + lock) + 60.0


def canonical_job_payload(job: Job) -> dict:
    """[pure] The job with the frozen removal list of PG-14 / protocol 12.3 dropped.

    In T4 the two jobs of a pair must have byte-identical canonical payloads; the verifier
    checks it.  ``worker_index`` is removed because it is the slot, not the arm, so the seed
    partition can give neither arm an advantage (audit M1)."""
    return {k: v for k, v in dict(job).items() if k not in CANONICAL_JOB_DROP}


def payload_sha256(job: Job) -> str:
    """[pure] The digest the job file and ``episode_started`` carry."""
    return lab_common.sha256_canonical(canonical_job_payload(job))


# --------------------------------------------------------------------------- #
# tokenized paths
# --------------------------------------------------------------------------- #
def resolve_token_path(tok: str | Path) -> Path:
    """The inverse of :func:`lab_common.tokenize_path`.

    Job files carry tokenized paths so that no tracked artifact holds an absolute path
    (PG-11); the worker resolves them against the same roots."""
    s = str(tok)
    # <HOST_WORK> FIRST, and resolved from the FROZEN config pin rather than this
    # checkout. That is the whole point: a job serialized in one clone and read in
    # another must name the same lock inode. Every other token is deliberately
    # checkout-relative and stays that way.
    if s == lab_common.HOST_WORK_TOKEN or s.startswith(lab_common.HOST_WORK_TOKEN + '/'):
        return lab_common.resolve_execution_lock_token(s, lab_common.harness_config())
    roots = {
        '<WORK>': lab_common.WORK_ROOT,
        '<RESULTS>': lab_common.RESULTS_ROOT,
        '<REPO>': lab_common.REPO_ROOT,
        '<HOME>': Path.home(),
        '<TMP>': Path(tempfile.gettempdir()),
    }
    for token, root in roots.items():
        if s == token:
            return Path(root)
        if s.startswith(token + '/'):
            return Path(root) / s[len(token) + 1:]
    if s.startswith('<'):
        raise lab_common.UntokenizablePath(s)
    return Path(s)


def load_task(job: Job) -> dict:
    """The task named by ``job['task_uid']``, from the roster file at ``paths['tasks']``.

    The task content is deliberately **not** carried in the job: the two jobs of a T4 pair
    are different tasks, and the frozen removal list of PG-14 cannot be extended to hide a
    ``task`` key, so carrying it would break the byte-identity check.  ``paths`` is in the
    removal list, which is why the *path* may live there."""
    paths = job.get('paths') or {}
    if 'tasks' not in paths:
        raise lab_common.PreflightError(
            "job['paths']['tasks'] is required: the worker loads task content from the "
            'roster file, never from the job payload')
    p = resolve_token_path(paths['tasks'])
    raw = Path(p).read_text(encoding='utf-8').strip()
    rows = (json.loads(raw) if raw.lstrip().startswith('[')
            else [json.loads(l) for l in raw.splitlines() if l.strip()])
    uid = job['task_uid']
    for row in rows:
        if str(row.get('uid')) == str(uid):
            return dict(row)
    raise lab_common.PreflightError('task %s is not in the roster file' % uid)


# --------------------------------------------------------------------------- #
# the host-wide execution lock (protocol 5.7)
# --------------------------------------------------------------------------- #
_LOCK_DEPTH = 0


def execution_lock_held() -> bool:
    """True while this process holds the host-wide execution lock."""
    return _LOCK_DEPTH > 0


class ExecutionLock:
    """Exclusive ``flock`` on one file, shared by every worker on this host.

    ``flock`` is held by the open file description, so two descriptions conflict even inside
    one process: a probe that opens the file again and asks for ``LOCK_EX | LOCK_NB`` is a
    faithful test of whether the lock is held."""

    def __init__(self, path: str | Path, *, max_lock_wait_s: float = 120.0) -> None:
        self.path = Path(path)
        self.max_lock_wait_s = float(max_lock_wait_s)
        self.wait_s = 0.0
        self._fd: int | None = None

    def __enter__(self) -> 'ExecutionLock':
        global _LOCK_DEPTH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        t0 = time.perf_counter()
        deadline = t0 + self.max_lock_wait_s
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.perf_counter() >= deadline:
                    os.close(self._fd)
                    self._fd = None
                    self.wait_s = time.perf_counter() - t0
                    raise LockWaitExceeded(
                        'execution lock not acquired in %.1f s' % self.max_lock_wait_s)
                time.sleep(0.01)
        self.wait_s = time.perf_counter() - t0
        _LOCK_DEPTH += 1
        return self

    def __exit__(self, *exc: object) -> None:
        global _LOCK_DEPTH
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None
                _LOCK_DEPTH = max(0, _LOCK_DEPTH - 1)


class LockWaitExceeded(lab_common.LabError):
    """``max_lock_wait_s`` exceeded for one execution (protocol 6.4 row 7)."""


def install_execution_lock(sandbox_lock_path: str | Path, spool: Spool | None = None,
                           *, max_lock_wait_s: float = 120.0) -> Callable:
    """Wrap ``sandbox.run_program`` in the host-wide lock and return the wrapper.

    Called **before** ``agent`` and ``verify`` are imported, so that their
    ``from sandbox import run_program`` binds the wrapper; when they are already imported
    (a test, a resumed process) their module attribute is rebound as well, so no call path
    can bypass the lock.  ``run_program`` creates and removes its ``p_*`` directory inside
    the call, so creation, execution and deletion are all inside the lock.

    Exceeding ``max_lock_wait_s`` fails that one execution as a sandbox kill (protocol 6.4
    row 7): the wrapper returns the sandbox's own failure shape, which is a failed self-test
    in the agent's loop and ``success = 0`` with ``verifier_timeout`` in verification."""
    lab_common.add_import_paths()
    import sandbox

    original = sandbox.run_program
    if getattr(original, '_lab_execution_lock', False):
        original = original._lab_original                       # type: ignore[attr-defined]

    def wrapper(source: str, **kwargs: Any) -> dict:
        purpose = _caller_purpose()
        try:
            with ExecutionLock(sandbox_lock_path, max_lock_wait_s=max_lock_wait_s) as lock:
                t0 = time.perf_counter()
                run = original(source, **kwargs)
                seconds = time.perf_counter() - t0
                wait_s = lock.wait_s
        except LockWaitExceeded as exc:
            run = {
                'passed': False, 'returncode': None, 'stdout': '', 'stderr': str(exc),
                'stdout_tail': '', 'timed_out': True, 'seconds': float(max_lock_wait_s),
                'executed': False, 'flags': [], 'limits_applied': '',
                'sandbox_kind': None, 'profile_sha256': None,
            }
            seconds = float(max_lock_wait_s)
            wait_s = float(max_lock_wait_s)
        if spool is not None:
            spool.write('sandbox_exec', {
                'purpose': purpose,
                'lock_wait_s': float(wait_s),
                'seconds': float(seconds),
                'returncode': run.get('returncode'),
                'timed_out': bool(run.get('timed_out')),
                'profile_sha256': run.get('profile_sha256') or '',
            }, durable=False)
        return run

    wrapper._lab_execution_lock = True                          # type: ignore[attr-defined]
    wrapper._lab_original = original                            # type: ignore[attr-defined]
    sandbox.run_program = wrapper
    for name in ('agent', 'verify'):
        mod = sys.modules.get(name)
        if mod is not None and getattr(mod, 'run_program', None) is not None:
            mod.run_program = wrapper
    return wrapper


def _caller_purpose() -> str:
    """``verify`` when the call came from the hidden-test verifier, else ``self_test``.

    ``agent.py`` and ``verify.py`` are the only two callers in the frozen pilot, and both
    bind ``run_program`` at module level, so the calling frame's module name separates the
    agent's own tests (inside ``latency_s``) from hidden-test verification (outside it)."""
    frame = sys._getframe(1)
    for _ in range(6):
        if frame is None:
            break
        name = frame.f_globals.get('__name__')
        if name in ('verify', 'agent'):
            return 'verify' if name == 'verify' else 'self_test'
        frame = frame.f_back                                     # type: ignore[assignment]
    return 'self_test'


# --------------------------------------------------------------------------- #
# failure-to-outcome (protocol 6.4)
# --------------------------------------------------------------------------- #
def certified_ell(lines: Sequence[dict]) -> float:
    """[pure] ``ell = max over spooled request events of (t_e - t_c1)``, in seconds.

    ``t_c1`` comes from the first ``call_started``; ``t_e`` ranges over every ``t_send_ns``
    and ``t_recv_ns``.  **No spooled request means ``ell = 0.0``** (critic N5, 6.4 row 18).
    It is a valid lower bound on ``latency_s`` because ``t_0 <= t_c1``, ``t_final >= t_e`` and
    there is exactly one attempt per arrival, so the endpoint clock never restarts."""
    t_c1: int | None = None
    for row in lines:
        if row.get('kind') == 'call_started':
            v = (row.get('body') or {}).get('t_c1_ns')
            if isinstance(v, int):
                t_c1 = v
                break
    if t_c1 is None:
        return 0.0
    best = 0
    for row in lines:
        body = row.get('body') or {}
        for key in ('t_send_ns', 't_recv_ns'):
            v = body.get(key)
            if isinstance(v, int):
                best = max(best, v - t_c1)
    return max(0.0, best / 1e9)


def tokens_known(lines: Sequence[dict]) -> int:
    """[pure] Completion tokens the server actually reported for this attempt.

    A request without a response contributes nothing and is listed under unknown usage; the
    value is never imputed and never defaulted to a non-zero number (protocol 13.1)."""
    total = 0
    for row in lines:
        if row.get('kind') != 'call_response':
            continue
        usage = ((row.get('body') or {}).get('usage') or {})
        v = usage.get('completion_tokens')
        if isinstance(v, int) and not isinstance(v, bool):
            total += v
    return total


def terminal_reveal(lines: Sequence[dict], error_class: str, *,
                    hard_cap_s: float | None = None) -> dict:
    """[pure] The outcome of an attempt that never returned (protocol 6.4 rows 10, 10b, 11, 18).

    ``success = 0``; ``latency_s`` is the hard cap for ``episode_timeout`` and the certified
    elapsed time otherwise; tokens are the known tokens, which is ``0`` when no request was
    ever spooled.  Every field is finite by construction, which is what ``winstats.compare``
    requires.

    Returns ``{'outcome': <the T17 outcome object>, 'certified_ell': float,
    'tokens_known': int}``."""
    if error_class not in OUTCOME_ERROR_CLASSES:
        raise lab_common.SpoolError('unknown error_class %r' % (error_class,))
    ell = certified_ell(lines)
    known = tokens_known(lines)
    if error_class == 'episode_timeout':
        if hard_cap_s is None:
            raise lab_common.SpoolError('episode_timeout needs the computed hard cap')
        latency = float(hard_cap_s)
    else:
        latency = float(ell)
    # `n_llm_calls` counts LOGICAL calls, as the pilot's record does; the tries beyond the
    # first of each are the connection retries, each of which is a fresh sample (5.6).
    tries = [r for r in lines if r.get('kind') == 'call_started']
    n_calls = len({(r.get('body') or {}).get('call_index') for r in tries})
    n_failed = sum(1 for r in lines if r.get('kind') == 'call_error')
    n_retries = max(0, len(tries) - n_calls)
    prompt = 0
    for row in lines:
        if row.get('kind') == 'call_response':
            v = ((row.get('body') or {}).get('usage') or {}).get('prompt_tokens')
            if isinstance(v, int) and not isinstance(v, bool):
                prompt += v
    timeout_any = any(r.get('kind') == 'call_error'
                      and (r.get('body') or {}).get('error_class') == 'timeout'
                      for r in lines)
    outcome = {
        'success': 0,
        'latency_s': latency,
        'completion_tokens': known,
        'prompt_tokens': prompt,
        'n_llm_calls': n_calls,
        'n_failed_calls': n_failed,
        'connection_retries': n_retries,
        'n_self_test_executions': sum(1 for r in lines if r.get('kind') == 'sandbox_exec'
                                      and (r.get('body') or {}).get('purpose') == 'self_test'),
        'n_verifier_executions': sum(1 for r in lines if r.get('kind') == 'sandbox_exec'
                                     and (r.get('body') or {}).get('purpose') == 'verify'),
        'repair_rounds': 0,
        'self_test_passed': None,
        'request_timeout_any': bool(timeout_any),
        'episode_timeout': error_class == 'episode_timeout',
        'verifier_timeout': False,
        'truncated_any': False,
        'sentinel_seen': False,
        'entry_point_defined': False,
        'error_class': error_class,
        'infra_flag': True,
    }
    return {'outcome': outcome, 'certified_ell': ell, 'tokens_known': known}


def outcome_from_record(rec: dict, stats: dict) -> dict:
    """[pure] The T17 outcome object of an attempt that returned.

    ``success`` is the archived verifier label and nothing else; ``latency_s`` is the pilot's
    ``agent.py:247`` wall clock; the three timeout fields are separate (protocol 6.1); and
    ``infra_flag`` carries the part of the closed list of 6.4 that a worker can see — any
    ``llm_error`` of any class, any retried try, any recovery wait, a receipt mismatch.  The
    orchestrator ORs in the parts only it knows (``server_down`` overlap, ``clock_anomaly``,
    rows 10/11/11c-e)."""
    error_class = None
    if stats.get('receipt_mismatch'):
        error_class = 'receipt_mismatch'
    elif stats.get('error_classes'):
        error_class = stats['error_classes'][-1]
    infra = bool(stats.get('error_classes') or stats.get('retried_tries')
                 or stats.get('recovery_waits') or stats.get('receipt_mismatch'))
    return {
        'success': int(bool(rec.get('success'))),
        'latency_s': float(rec.get('latency_s') or 0.0),
        'completion_tokens': int(rec.get('completion_tokens') or 0),
        'prompt_tokens': int(rec.get('prompt_tokens') or 0),
        'n_llm_calls': int(rec.get('n_llm_calls') or 0),
        'n_failed_calls': int(stats.get('n_failed_calls') or 0),
        # every retried try, including those of a call that ultimately failed: the pilot's
        # own counter only sees the retries of calls that returned.
        'connection_retries': int(stats.get('retried_tries') or 0),
        'n_self_test_executions': int(stats.get('n_self_test_executions') or 0),
        'n_verifier_executions': int(stats.get('n_verifier_executions') or 0),
        'repair_rounds': int(rec.get('repair_rounds') or 0),
        'self_test_passed': (None if rec.get('self_test_passed') is None
                             else bool(rec.get('self_test_passed'))),
        'request_timeout_any': bool(stats.get('request_timeout_any')),
        'episode_timeout': False,     # the cap is the orchestrator's; a returned attempt is not capped
        'verifier_timeout': bool(rec.get('timed_out')),
        'truncated_any': bool(stats.get('truncated_any')),
        'sentinel_seen': bool(rec.get('sentinel_seen')),
        'entry_point_defined': bool(rec.get('entry_point_defined')),
        'error_class': error_class,
        'infra_flag': infra,
    }


# --------------------------------------------------------------------------- #
# the episode
# --------------------------------------------------------------------------- #
def run_job(job: Job, *, sandbox_lock_path: Path) -> dict:
    """The whole episode, in one process, in the order of ARCHITECTURE_FINAL.md 3.12.

    Every exception inside ``run_episode`` is already an outcome: the pilot records it and
    grades the last candidate that exists.  An exception **outside** ``run_episode`` (a
    record write failure, a lock failure) is spooled as ``worker_error`` and the process
    exits 3; the orchestrator treats that as a worker death (6.4 row 10)."""
    t_start_ns = time.monotonic_ns()
    # THE WORKER'S OWN STARTUP CHECK, root 2026-09-22: "World.spawn and
    # lab_worker.run_job exist and were already identified. Wire their common
    # startup paths."  Checked on the JOB the worker actually received, before
    # the spool is opened and long before any model request: the worker is a
    # separate OS process and cannot rely on the orchestrator's check having run
    # in some other process.
    lab_common.assert_no_fixture(job, stage='worker run_job startup')
    lab_common.assert_no_fixture(job.get('cfg'), stage='worker run_job startup (cfg)')
    # TMPDIR AT THE WORKER'S OWN ENTRY POINT. The worker is a separate OS process
    # with its own environment, so a check that ran in the orchestrator says
    # nothing about this process's TMPDIR -- and the Seatbelt profile digest this
    # process will produce is a function of it. Checked only when the job carries
    # the sandbox block that declares it, so a job shape without one is a
    # configuration error surfaced elsewhere rather than a TMPDIR failure here.
    if isinstance(job.get('cfg'), dict) and (job['cfg'].get('sandbox') or {}).get('tmpdir'):
        lab_common.assert_tmpdir(job['cfg'], stage='worker run_job startup')
    elif (job.get('sandbox') or {}).get('tmpdir'):
        lab_common.assert_tmpdir(job, stage='worker run_job startup')
    paths = job.get('paths') or {}
    spool = Spool(resolve_token_path(paths['spool']))
    if job.get('inv'):
        spool.set_inv(str(job['inv']))
    stage = 'job_accepted'
    try:
        spool.write('job_accepted', {
            'arm': job['arm'],
            'workflow': job['workflow'],
            'task_uid': job['task_uid'],
            'job_sha256': lab_common.sha256_canonical(dict(job)),
            'payload_sha256': str(job.get('payload_sha256') or payload_sha256(job)),
        }, durable=True)

        stage = 'execution_lock'
        limits = dict(job.get('limits') or {})
        install_execution_lock(sandbox_lock_path, spool,
                               max_lock_wait_s=float(limits.get('max_lock_wait_s', 120.0)))

        stage = 'imports'
        lab_common.add_import_paths()
        import agent                                           # noqa: E402  (after the patch)
        import verify as verify_mod                            # noqa: E402

        stage = 'task'
        task = load_task(job)

        stage = 'client'
        server = dict(job.get('server') or {})
        golden = _golden_from_job(job)
        client = LlamaClient(
            base_url=str(server['base_url']), alias=str(server['alias']),
            sampling=dict(job.get('sampling') or {}), spool=spool, golden=golden,
            request_timeout_s=float(limits.get('request_timeout_s', 180.0)),
            max_connection_retries=int(limits.get('max_connection_retries', 2)),
            server_recovery_s=float(limits.get('server_recovery_s', 180.0)),
            arrival=int(job['arrival']), attempt=int(job['attempt']),
            trial=str(job['trial']), worker_index=int(job['worker_index']))
        if 'requests' in paths:
            client.request_dir = resolve_token_path(paths['requests'])
        client.used_seeds = load_used_seeds(
            resolve_token_path(paths['used_seeds']) if 'used_seeds' in paths else None,
            int(job['worker_index']))

        stage = 'run_episode'
        cfg = _cfg_for_agent(job, limits)
        meta = {
            'trial': int(str(job['trial'])[1:]) if str(job['trial'])[1:].isdigit() else 1,
            'arrival_index': int(job['arrival']),
            'pair_index': int(job.get('pair') or 0),
            'orientation': int(job.get('position') or 0),
            'pass': None,
            'harness_git_hash': str(job.get('freeze_bundle_sha256') or ''),
        }
        rec = agent.run_episode(task, str(job['workflow']), client, cfg, meta)

        stage = 'record'
        rec = json.loads(lab_common.canonical_json(rec))       # plain JSON types only
        record_sha = lab_common.sha256_canonical(rec)
        record_dir = resolve_token_path(paths['records'])
        record_dir.mkdir(parents=True, exist_ok=True)
        lab_common.write_json_atomic(record_dir / ('%s.json' % record_sha), rec, durable=True)

        stage = 'episode_final'
        lines = read_spool(spool.path)
        stats = dict(client.stats())
        stats['n_self_test_executions'] = sum(
            1 for r in lines if r.get('kind') == 'sandbox_exec'
            and (r.get('body') or {}).get('purpose') == 'self_test')
        stats['n_verifier_executions'] = sum(
            1 for r in lines if r.get('kind') == 'sandbox_exec'
            and (r.get('body') or {}).get('purpose') == 'verify')
        outcome = outcome_from_record(rec, stats)
        t_end_ns = time.monotonic_ns()
        verify_program = ''
        if rec.get('final_code'):
            try:
                verify_program = verify_mod.build_program(task, rec['final_code'], None)
            except (ValueError, KeyError):
                verify_program = ''
        spool.write('episode_final', {
            'record_sha256': record_sha,
            'outcome': outcome,
            'final_code_sha256': lab_common.sha256_text(str(rec.get('final_code') or '')),
            'verify_program_sha256': lab_common.sha256_text(verify_program),
            't_start_ns': t_start_ns,
            't_end_ns': t_end_ns,
            'verify_seconds': float(rec.get('verify_seconds') or 0.0),
            'static_flags': list(rec.get('static_flags') or []),
            'hack_flags': list(rec.get('hack_flags') or []),
            'certified_ell': certified_ell(lines),
            'tokens_known': tokens_known(lines),
            'seed_collisions': int(stats.get('seed_collisions') or 0),
            'receipt_mismatch': list(stats.get('receipt_mismatch') or []),
        }, durable=True)
        return outcome
    except BaseException as exc:                # noqa: BLE001 - re-raised after spooling
        try:
            spool.write('worker_error', {
                'stage': stage,
                'error_sha256': lab_common.sha256_text(
                    '%s: %s' % (type(exc).__name__, exc)),
            }, durable=True)
        except Exception:                        # noqa: BLE001 - the spool itself is gone
            pass
        raise
    finally:
        spool.close()


def _cfg_for_agent(job: Job, limits: dict) -> dict:
    """The pilot's cfg dict.  ``sandbox_*`` and ``max_repair_rounds`` are frozen values from
    the job; ``_config_hash`` is the frozen config digest the record carries."""
    sbx = dict(job.get('sandbox') or {})
    return {
        'base_url': str((job.get('server') or {}).get('base_url') or ''),
        'model': str((job.get('server') or {}).get('alias') or ''),
        'temperature': float((job.get('sampling') or {}).get('temperature', 0.7)),
        'top_p': float((job.get('sampling') or {}).get('top_p', 0.95)),
        'max_tokens': int((job.get('sampling') or {}).get('max_tokens', 1024)),
        'request_timeout_s': float(limits.get('request_timeout_s', 180.0)),
        'max_connection_retries': int(limits.get('max_connection_retries', 2)),
        'sandbox_timeout_s': float(sbx.get('timeout_s', 10.0)),
        'sandbox_mem_bytes': int(sbx.get('mem_bytes_requested_not_enforced_on_macos',
                                         2147483648)),
        'sandbox_cpu_s': int(sbx.get('cpu_s', 10)),
        'sandbox_output_cap_bytes': int(sbx.get('output_cap_bytes', 65536)),
        'max_repair_rounds': int(job.get('max_repair_rounds', 2)),
        '_config_hash': str(job.get('config_sha256') or ''),
    }


def _golden_from_job(job: Job) -> GoldenReceipt:
    """The frozen golden objects of this server, carried in the job by the orchestrator."""
    g = dict(job.get('golden') or {})
    return GoldenReceipt(
        props=dict(g.get('props') or {}),
        generation_settings=dict(g.get('generation_settings') or {}),
        mask=tuple(g.get('mask') or ('seed',)),
        float_tolerance=float(g.get('float_tolerance', 1e-6)))


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--job <path to job json>``.  Exits 0 on a completed episode, 3 on a worker
    error.  Nothing is printed: stdout and stderr belong to the job's log file."""
    ap = argparse.ArgumentParser(prog='lab_worker')
    ap.add_argument('--job', required=True)
    args = ap.parse_args(argv)
    job = json.loads(Path(args.job).read_text(encoding='utf-8'))
    paths = job.get('paths') or {}
    lock = resolve_token_path(paths['sandbox_lock']) if 'sandbox_lock' in paths \
        else lab_common.trial_paths(str(job['trial'])).sandbox_lock
    # PRODUCTION ENTRY BINDING CHECK. EVERY SPELLING, NO EXCEPTIONS.
    #
    # The previous version discriminated on token shape: a string beginning '<'
    # had to be canonical, anything else was waved through as an "explicit
    # fixture". Root: "lab_worker.main skips the canonical check for any string
    # not beginning `<`, including arbitrary absolute and relative paths ... a
    # path or flag cannot designate itself an isolated fixture." An arbitrary job
    # could therefore hand the worker any lock it liked and run effectively
    # unlocked, which is precisely the splitting this check exists to prevent.
    #
    # I built that hole because it made four worker tests pass. Isolation now
    # lives in the test process, which patches the canonical root; the production
    # reader validates unconditionally.
    #
    # The job's own sandbox block is checked for agreement first, so a job cannot
    # quietly relocate the host root and then satisfy the check against its own
    # relocated pin.
    lab_common.assert_host_root_agreement(
        job.get('cfg') or {}, stage='lab_worker.main')
    if 'sandbox_lock' in paths:
        # the SPELLING, before it is resolved: <WORK>/sandbox.lock resolves to the
        # canonical file here and to a different file in a clone.
        lab_common.assert_canonical_lock_spelling(
            paths['sandbox_lock'], lab_common.harness_config(),
            stage='lab_worker.main')
    lab_common.assert_canonical_execution_lock(
        lock, lab_common.harness_config(), stage='lab_worker.main')

    try:
        run_job(job, sandbox_lock_path=lock)
    except BaseException:                       # noqa: BLE001 - already spooled
        sys.stderr.write(traceback.format_exc())
        return WORKER_ERROR_EXIT
    return 0


if __name__ == '__main__':
    sys.exit(main())
