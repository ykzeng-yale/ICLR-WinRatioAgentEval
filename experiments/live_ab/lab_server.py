"""llama-server supervision: frozen argv, identity assertion, health, /metrics, smoke.

ARCHITECTURE_FINAL.md 3.10 is the interface contract; protocol_FINAL.md 2.2 (the frozen
launch line and the serving manifest), 2.3 (model identity), 5.3 (supervision), 6.4 rows 5, 6
and 20 and 13.1/13.2 are the rules.

Two things are worth stating in the module that owns them:

* **Three cache switches, not two.**  ``--no-cache-prompt``, ``--cache-ram 0`` and
  ``--slot-prompt-similarity 0.0`` are all structural (critic N7, audit M2).  The request
  field ``cache_prompt`` is not echoed by the server, so cache deactivation has to live in
  the argv and be visible in ``/props``; and without ``--slot-prompt-similarity 0.0`` the
  server may reuse a slot's prefix across the up-to-four calls of a ``self_test_repair``
  episode, which fires ``timings.cache_n != 0`` and irreversibly aborts T2 or T1 under
  protocol 6.4 row 12.
* **A hanging ``/metrics`` must never block enrolment** (PG-10, critic N9): 5 s timeout,
  3 tries, then ``{'ok': False}``, the window is logged unreconciled and the trial continues.

No threads: health is polled by the orchestrator's loop.  **No test in this repository ever
starts a real llama-server**; the identity logic is factored into the pure
:func:`assert_identity` so that it can be exercised against the mock.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import requests

import lab_common

#: The counters of protocol 13.1 / ARCHITECTURE_FINAL.md 8.1, keyed by their Prometheus name.
METRIC_NAMES: dict[str, str] = {
    'llamacpp:prompt_tokens_total': 'prompt_tokens_total',
    'llamacpp:tokens_predicted_total': 'tokens_predicted_total',
    'llamacpp:n_decode_total': 'n_decode_total',
    'llamacpp:requests_processing': 'requests_processing',
    'llamacpp:requests_deferred': 'requests_deferred',
}

#: Closed list of identity findings; each is a reason code, never free text.
IDENTITY_FINDINGS: tuple[str, ...] = (
    'alias', 'total_slots', 'n_ctx', 'model_path', 'build_info', 'models_endpoint',
    'slot_prompt_similarity', 'props_mismatch', 'gguf_bytes', 'gguf_sha256',
)

SMOKE_PROMPT: str = 'Reply with the single word: pong'

#: Started children, so that :func:`stop` can reap a process it started.
_CHILDREN: dict[int, subprocess.Popen] = {}


@dataclass(frozen=True)
class ServerSpec:
    """Everything the frozen launch line and the identity assertion need.

    ``n_ctx`` is the value passed to ``-c``: the **total** context of the process, which
    ``--no-kv-unified`` divides into ``n_slots`` slots of ``n_ctx // n_slots`` tokens each
    (protocol 2.2: ``-np 2 -c 16384`` gives each slot 8,192)."""

    server_id: Literal['coder', 't3']
    port: int
    alias: str
    gguf_path: Path
    gguf_bytes: int
    gguf_sha256: str
    llama_bin: Path
    llama_commit: str
    args: tuple[str, ...]
    log_path: Path
    n_slots: int
    n_ctx: int

    @property
    def ctx_per_slot(self) -> int:
        return self.n_ctx // max(1, self.n_slots)

    @property
    def base_url(self) -> str:
        return 'http://127.0.0.1:%d' % self.port


def server_argv(spec: ServerSpec) -> list[str]:
    """[pure] The frozen command line of protocol 2.2, verbatim and in that order."""
    return [
        str(spec.llama_bin),
        '-m', str(spec.gguf_path),
        '--alias', spec.alias,
        '--host', '127.0.0.1',
        '--port', str(spec.port),
        '-np', str(spec.n_slots),
        '-c', str(spec.n_ctx),
        '--no-kv-unified',
        '-ngl', '99',
        '--jinja',
        '--metrics',
        '--no-context-shift',
        '--offline',
        '--no-cache-prompt',
        '--cache-ram', '0',
        '--slot-prompt-similarity', '0.0',
        '--log-file', str(spec.log_path),
        '--log-timestamps',
    ]


# --------------------------------------------------------------------------- #
# identity
# --------------------------------------------------------------------------- #
def props_slot_prompt_similarity(props: Mapping) -> float | None:
    """The slot-prompt similarity the server reports, at the top level or under
    ``default_generation_settings``.  ``None`` when the object does not report it at all,
    which is itself an identity failure (audit M2)."""
    for holder in (props, props.get('default_generation_settings') or {}):
        if isinstance(holder, Mapping) and 'slot_prompt_similarity' in holder:
            v = holder['slot_prompt_similarity']
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return None


def props_n_ctx_per_slot(props: Mapping) -> int | None:
    """The per-slot context the server reports."""
    dgs = props.get('default_generation_settings')
    if isinstance(dgs, Mapping) and isinstance(dgs.get('n_ctx'), int):
        return int(dgs['n_ctx'])
    if isinstance(props.get('n_ctx'), int):
        return int(props['n_ctx'])
    return None


def assert_identity(spec: ServerSpec, props: Mapping, models: Mapping | None = None,
                    golden_props: Mapping | None = None) -> None:
    """[pure] Raise :class:`lab_common.ServerIdentityError` on any identity deviation.

    Checked, exactly as protocol 2.3 and 5.3 require: the alias; the slot count; the per-slot
    ``n_ctx``; the real path of ``/props.model_path``; the build commit prefix in
    ``build_info``; the ``/v1/models`` listing; **that /props reports a slot-prompt
    similarity of 0.0**; and, when a golden object is supplied, the whole ``/props`` object
    against it.

    ``golden_props`` is ``None`` only in the pre-freeze capture phase (protocol 5.8 item 1),
    where the golden object is being created and cannot yet be compared against."""
    findings: list[str] = []
    if props.get('model_alias') != spec.alias:
        findings.append('alias')
    if props.get('total_slots') != spec.n_slots:
        findings.append('total_slots')
    if props_n_ctx_per_slot(props) != spec.ctx_per_slot:
        findings.append('n_ctx')
    model_path = str(props.get('model_path') or '')
    if model_path.startswith('<'):
        # a tokenized golden object: it can only be compared with the golden value
        if golden_props is not None and model_path != str(golden_props.get('model_path') or ''):
            findings.append('model_path')
    elif os.path.realpath(model_path) != os.path.realpath(str(spec.gguf_path)):
        findings.append('model_path')
    if spec.llama_commit[:7] not in str(props.get('build_info') or ''):
        findings.append('build_info')
    if models is not None:
        ids = [d.get('id') for d in (models.get('data') or [])]
        if spec.alias not in ids:
            findings.append('models_endpoint')
    sps = props_slot_prompt_similarity(props)
    if sps is None or sps != 0.0:
        findings.append('slot_prompt_similarity')
    if golden_props is not None and dict(props) != dict(golden_props):
        findings.append('props_mismatch')
    if findings:
        raise lab_common.ServerIdentityError(','.join(sorted(set(findings))))


def assert_gguf(spec: ServerSpec, *, recompute_sha256: bool = True) -> str:
    """Byte size and SHA-256 of the weights file (protocol 2.3: the cache blob name is not
    proof of its content, so the digest is recomputed).  Returns the digest."""
    p = Path(spec.gguf_path)
    if not p.exists():
        raise lab_common.ServerIdentityError('gguf_bytes')
    if p.stat().st_size != spec.gguf_bytes:
        raise lab_common.ServerIdentityError('gguf_bytes')
    if not recompute_sha256:
        return spec.gguf_sha256
    digest = lab_common.sha256_file(p)
    if digest != spec.gguf_sha256:
        raise lab_common.ServerIdentityError('gguf_sha256')
    return digest


# --------------------------------------------------------------------------- #
# probes
# --------------------------------------------------------------------------- #
def probe(base_url: str, *, timeout: float = 5.0) -> dict:
    """``/props`` and ``/v1/models``.  Raises on a transport failure: a server that cannot be
    probed at start is not a server this harness will attach to."""
    root = _root(base_url)
    try:
        props = requests.get(root + '/props', timeout=timeout).json()
        models = requests.get(root + '/v1/models', timeout=timeout).json()
    except (requests.RequestException, ValueError) as exc:
        raise lab_common.ServerIdentityError('props_mismatch') from exc
    return {'props': props, 'models': models,
            'props_sha256': lab_common.sha256_canonical(props)}


def health(base_url: str, *, timeout: float = 5.0) -> dict:
    """``/health`` plus the busy-slot count.  Never raises: the supervisor of protocol 5.3
    counts consecutive failures and logs ``server_down`` on the third."""
    root = _root(base_url)
    out = {'ok': False, 'slots_busy': 0, 'status': 'no_answer'}
    try:
        r = requests.get(root + '/health', timeout=timeout)
        out['ok'] = r.status_code == 200
        out['status'] = 'ok' if out['ok'] else 'error'
    except requests.RequestException:
        return out
    try:
        slots = requests.get(root + '/slots', timeout=timeout).json()
        if isinstance(slots, list):
            out['slots_busy'] = sum(1 for s in slots if s.get('is_processing'))
    except (requests.RequestException, ValueError):
        pass
    return out


def parse_metrics(text: str) -> dict:
    """[pure] Prometheus text -> the five counters of 8.1.  Unknown lines are ignored;
    a counter the server does not expose is absent from the result."""
    out: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 2 or parts[0] not in METRIC_NAMES:
            continue
        try:
            out[METRIC_NAMES[parts[0]]] = int(float(parts[1]))
        except ValueError:
            continue
    return out


def metrics(base_url: str, *, timeout: float = 5.0, tries: int = 3) -> dict:
    """Scrape ``/metrics``.  On timeout or parse failure after ``tries`` this returns
    ``{'ok': False, ...}`` instead of raising: the window is then logged as unreconciled and
    enrolment continues (PG-10, protocol 6.4 row 20).  A scrape never blocks a pair boundary."""
    root = _root(base_url)
    out: dict[str, Any] = {name: None for name in METRIC_NAMES.values()}
    out['ok'] = False
    out['tries'] = 0
    for attempt in range(max(1, int(tries))):
        out['tries'] = attempt + 1
        try:
            r = requests.get(root + '/metrics', timeout=timeout)
            if r.status_code != 200:
                continue
            parsed = parse_metrics(r.text)
        except requests.RequestException:
            continue
        if not parsed:
            continue
        out.update(parsed)
        out['ok'] = True
        return out
    return out


# --------------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------------- #
def start(spec: ServerSpec, *, golden_props: Mapping | None = None,
          golden: object | None = None, sampling: Mapping | None = None,
          timeout_s: float = 600.0, recompute_gguf_sha256: bool = True) -> dict:
    """Launch the frozen argv, wait for ``/health``, assert identity, run the smoke.

    Returns the ``server_started`` body of event schema T4.  Raises
    :class:`lab_common.ServerIdentityError` when the alias, the slot count, the per-slot
    ``n_ctx``, ``realpath(model_path)``, the build commit, the GGUF bytes or digest, the
    ``/props`` object or the reported slot-prompt similarity deviates from the frozen values.

    ``golden_props`` / ``golden`` / ``sampling`` are ``None`` only in the pre-freeze capture
    phase (protocol 5.8 item 1); outside it the orchestrator always supplies all three and
    the smoke completion of 5.3 is part of the returned body.

    Side effects: a child process in its own session and a log file."""
    argv = server_argv(spec)
    gguf_sha = assert_gguf(spec, recompute_sha256=recompute_gguf_sha256)
    Path(spec.log_path).parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    logf = open(str(spec.log_path), 'ab')
    try:
        proc = subprocess.Popen(argv, stdout=logf, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    finally:
        logf.close()
    _CHILDREN[proc.pid] = proc
    base = spec.base_url
    deadline = time.perf_counter() + timeout_s
    while True:
        if proc.poll() is not None:
            raise lab_common.ServerIdentityError('build_info')   # it died before answering
        if health(base, timeout=2.0)['ok']:
            break
        if time.perf_counter() > deadline:
            stop(proc.pid)
            raise lab_common.PreflightError('server did not become healthy in %.0f s'
                                            % timeout_s)
        time.sleep(0.2)
    load_seconds = time.perf_counter() - t0
    p = probe(base)
    assert_identity(spec, p['props'], p['models'], golden_props)
    smoke_body = {'request_sha256': lab_common.sha256_text(''), 'receipt_matches_golden': False,
                  'usage': {}, 'timings': {}, 'ok': False}
    if golden is not None and sampling is not None:
        smoke_body = smoke(base, spec, golden, sampling)
    return {
        'server_id': spec.server_id,
        'pid': proc.pid,
        'port': spec.port,
        'argv_sha256': lab_common.sha256_canonical(argv),
        'gguf': {'bytes': int(Path(spec.gguf_path).stat().st_size), 'sha256': gguf_sha},
        'props_sha256': p['props_sha256'],
        'props_matches_golden': bool(golden_props is not None
                                     and dict(p['props']) == dict(golden_props)),
        'total_slots': int(p['props'].get('total_slots') or 0),
        'n_ctx': int(props_n_ctx_per_slot(p['props']) or 0),
        'load_seconds': load_seconds,
        'smoke': smoke_body,
    }


def smoke(base_url: str, spec: ServerSpec, golden: object, sampling: Mapping) -> dict:
    """One non-task completion, tagged ``phase = SERVER_SMOKE`` by the caller.

    The receipt of this response enters the reconciliation identity of protocol 13.1 and its
    comparison against the golden object is the first proof, at every start and restart, that
    the sampler settings are the frozen ones.  Raises ``ReceiptMismatch`` /
    ``ServerIdentityError`` on any deviation.

    The comparison is implemented here rather than imported from ``lab_client``: the
    isolation matrix forbids ``lab_server`` to import it, and a second implementation of the
    same frozen rule is a feature, not duplication.  ``tests_lab_serving`` asserts the two
    agree finding for finding."""
    body: dict[str, Any] = {'model': spec.alias,
                            'messages': [{'role': 'user', 'content': SMOKE_PROMPT}]}
    body.update(dict(sampling))
    body['seed'] = 1
    body.setdefault('stream', False)
    body.setdefault('verbose', True)
    body.setdefault('cache_prompt', False)
    url = _root(base_url) + '/v1/chat/completions'
    try:
        r = requests.post(url, json=body, timeout=120)
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise lab_common.PreflightError('smoke completion failed') from exc
    if r.status_code != 200 or not isinstance(data, dict) \
            or 'usage' not in data or 'timings' not in data:
        raise lab_common.PreflightError('smoke completion returned no usage/timings')
    if data.get('model') != spec.alias:
        raise lab_common.ServerIdentityError('alias')
    findings = smoke_receipt_findings(data, golden, seed_sent=body['seed'])
    out = {
        'request_sha256': lab_common.sha256_canonical(body),
        'receipt_matches_golden': not findings,
        'usage': {k: data['usage'][k] for k in sorted(data['usage'])
                  if isinstance(data['usage'][k], int)},
        'timings': {k: data['timings'][k] for k in sorted(data['timings'])},
        'ok': not findings,
    }
    if findings:
        raise lab_common.ReceiptMismatch(','.join(findings))
    return out


def smoke_receipt_findings(data: Mapping, golden: object, *, seed_sent: int) -> list[str]:
    """[pure] The second implementation of the frozen receipt rule of protocol 13.2.

    Returns a sorted list of reason codes from ``lab_client.RECEIPT_FINDINGS``; the detail of
    a mismatch never leaves this process."""
    gold_gen = dict(getattr(golden, 'generation_settings', {}) or {})
    mask = set(getattr(golden, 'mask', ('seed',)) or ('seed',))
    tol = float(getattr(golden, 'float_tolerance', 1e-6))
    verbose = data.get('__verbose') or {}
    gen = verbose.get('generation_settings') if isinstance(verbose, Mapping) else None
    findings: set[str] = set()
    if not isinstance(gen, Mapping):
        return ['generation_settings_absent']
    for key, want in gold_gen.items():
        if key in mask:
            if key not in gen:
                findings.add('generation_settings_missing_key')
            continue
        if key not in gen:
            findings.add('generation_settings_missing_key')
        elif not _same(gen[key], want, tol):
            findings.add('generation_settings_value')
    for key in gen:
        if key not in gold_gen and key not in mask:
            findings.add('generation_settings_unknown_key')
    if 'seed' in mask and gen.get('seed') != seed_sent:
        findings.add('seed_mismatch')
    timings = data.get('timings') or {}
    if timings.get('cache_n') != 0:
        findings.add('cache_n_nonzero')
    cached = verbose.get('tokens_cached') if isinstance(verbose, Mapping) else None
    if cached is None:
        cached = ((data.get('usage') or {}).get('prompt_tokens_details') or {}) \
            .get('cached_tokens')
    if cached != 0:
        findings.add('tokens_cached_nonzero')
    return sorted(findings)


def _same(obs: object, want: object, tol: float) -> bool:
    if isinstance(want, Mapping):
        if not isinstance(obs, Mapping) or set(obs) != set(want):
            return False
        return all(_same(obs[k], want[k], tol) for k in want)
    if isinstance(want, bool):
        return isinstance(obs, bool) and obs == want
    if isinstance(want, int):
        return isinstance(obs, int) and not isinstance(obs, bool) and obs == want
    if isinstance(want, float):
        return (isinstance(obs, (int, float)) and not isinstance(obs, bool)
                and abs(float(obs) - want) <= tol)
    if isinstance(want, (list, tuple)):
        return isinstance(obs, (list, tuple)) and list(obs) == list(want)
    return obs == want


def stop(pid: int, *, grace_s: float = 10.0) -> dict:
    """SIGTERM the process group, then SIGKILL after ``grace_s``."""
    t0 = time.perf_counter()
    proc = _CHILDREN.get(int(pid))
    try:
        os.killpg(int(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            return {'returncode': None, 'seconds': time.perf_counter() - t0}
    deadline = t0 + grace_s
    while time.perf_counter() < deadline:
        if proc is not None:
            if proc.poll() is not None:
                _CHILDREN.pop(int(pid), None)
                return {'returncode': proc.returncode, 'seconds': time.perf_counter() - t0}
        else:
            try:
                os.kill(int(pid), 0)
            except OSError:
                return {'returncode': None, 'seconds': time.perf_counter() - t0}
        time.sleep(0.05)
    try:
        os.killpg(int(pid), signal.SIGKILL)
    except OSError:
        try:
            os.kill(int(pid), signal.SIGKILL)
        except OSError:
            pass
    if proc is not None:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        _CHILDREN.pop(int(pid), None)
        return {'returncode': proc.returncode, 'seconds': time.perf_counter() - t0}
    return {'returncode': None, 'seconds': time.perf_counter() - t0}


def restart(spec: ServerSpec, golden_props: Mapping, *, golden: object | None = None,
            sampling: Mapping | None = None) -> dict:
    """Start again with the identical argv and compare the **full** ``/props`` with the
    golden object; a difference raises ``ServerIdentityError``, which the orchestrator maps
    to ``trial_aborted(server_identity)`` (protocol 6.4 row 6).

    The returned body is T4's plus ``props_equal_previous``."""
    body = start(spec, golden_props=golden_props, golden=golden, sampling=sampling)
    body['props_equal_previous'] = bool(body.get('props_matches_golden'))
    if not body['props_equal_previous']:
        raise lab_common.ServerIdentityError('props_mismatch')
    return body


def _root(base_url: str) -> str:
    u = str(base_url).rstrip('/')
    return u[:-3].rstrip('/') if u.endswith('/v1') else u
