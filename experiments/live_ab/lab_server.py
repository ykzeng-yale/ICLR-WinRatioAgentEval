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
:func:`identity_findings` / :func:`assert_identity` so that it can be exercised against the
mock, and :func:`start` is exercised by ``experiments/live_ab_controls`` with a launcher that
is a shell script, never a model.

**The lifecycle is route (a) of root's 20:40 decision** (``reviews/
prerun_bundle_go_nogo_20260923_2040.md`` item 1): :func:`start` either returns a body every
value of which was observed or compared, or stops the child it launched and raises
:class:`lab_common.ServerStartFailed` carrying the ``server_start_failed`` record.  It never
returns a success-valued placeholder.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import os
import re
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

#: The receipt reason codes of protocol 13.2, transcribed from ``lab_client.RECEIPT_FINDINGS``:
#: the isolation matrix (ARCHITECTURE_FINAL.md 3.16) forbids this module to import
#: ``lab_client``, and ``tests_eb1_server`` asserts the two tuples are equal.
RECEIPT_FINDINGS: tuple[str, ...] = (
    'generation_settings_absent', 'generation_settings_missing_key',
    'generation_settings_unknown_key', 'generation_settings_value', 'seed_mismatch',
    'cache_n_nonzero', 'tokens_cached_nonzero', 'model_alias_mismatch',
)

#: The stages of a start, in the order :func:`start` runs them (repair contract EB1).
START_STAGES: tuple[str, ...] = ('gguf', 'serving_manifest', 'launch', 'health',
                                 'identity', 'smoke')

#: The start-failure findings that are neither identity nor receipt codes (contract EB1).
#: ``process_exited``: the launch produced no live process (the OS refused the exec, or the
#: child exited before ``/health`` answered 200).  ``health_timeout``: it never answered
#: within ``timeout_s``.  ``smoke_transport``: the smoke completion did not arrive as an HTTP
#: 200 JSON object.  ``smoke_no_usage``: a key the event schema's closed USAGE / TIMINGS
#: sets require was absent -- never replaced by 0.  ``serving_manifest``: the frozen serving
#: manifest was absent or did not re-verify (protocol 5.3, P:918).
START_FINDINGS: tuple[str, ...] = ('process_exited', 'health_timeout', 'smoke_transport',
                                   'smoke_no_usage', 'serving_manifest')

#: The event schema's closed ``USAGE`` and ``TIMINGS`` key sets (``lab_eventlog.USAGE`` /
#: ``lab_eventlog.TIMINGS``), transcribed because the matrix forbids importing
#: ``lab_eventlog`` here; ``tests_eb1_server`` asserts they agree.  The smoke body is
#: PROJECTED onto exactly these keys: the server reports more (``prompt_per_second``) and an
#: unknown key is a schema violation, a missing one a finding.
SMOKE_USAGE_KEYS: tuple[str, ...] = ('prompt_tokens', 'completion_tokens', 'total_tokens',
                                     'cached_tokens')
SMOKE_TIMINGS_INT_KEYS: tuple[str, ...] = ('cache_n', 'prompt_n', 'predicted_n')
SMOKE_TIMINGS_FLOAT_KEYS: tuple[str, ...] = ('prompt_ms', 'predicted_ms',
                                             'predicted_per_second')

#: The members the frozen serving manifest of protocol 2.2 must carry for :func:`start` to
#: re-verify it.  The other protocol-2.2 fields (``metal_library``, ``resolved_rpath``, the
#: cmake/compiler/SDK strings and log digests) are bound by the manifest's frozen digest
#: only; nothing here recomputes them -- stated, not implied.
SERVING_MANIFEST_REQUIRED: tuple[str, ...] = ('llama_cpp_commit', 'launcher_sha256',
                                              'libraries', 'props_build_info')

SMOKE_PROMPT: str = 'Reply with the single word: pong'

_HEX64_RE = re.compile(r'^[0-9a-f]{64}$')

#: Started children, so that :func:`stop` can reap a process it started.
_CHILDREN: dict[int, subprocess.Popen] = {}
#: Children :func:`stop` reaped, pid -> returncode, so :func:`exit_status` still answers.
_EXITED: dict[int, int | None] = {}


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


def tokenized_props(props: Mapping) -> dict:
    """[pure] The golden form of a raw ``/props`` object.

    Protocol 13.2 (protocol_FINAL.md:2586) captures "the full ``/props`` object (with
    ``model_path`` tokenized)", and 15.2 (P:2862) says ``/props`` fields holding paths are
    tokenized before they are logged.  The ONE tokenization rule is
    ``lab_common.tokenize_path`` (ARCHITECTURE_FINAL.md 3.1, lines 284-288): the object is
    deep-copied through its canonical JSON and ``model_path`` alone is replaced by its
    tokenized form.  Raises ``lab_common.UntokenizablePath`` for a ``model_path`` under no
    known root -- including one that is ALREADY a token, which a real server never reports.

    The pre-freeze capture (stage 1) and every later comparison go through this one
    function, so the golden object and the observed one are tokenized by the same rule."""
    out = json.loads(lab_common.canonical_json(dict(props)))
    if 'model_path' in out:
        out['model_path'] = lab_common.tokenize_path(str(out['model_path']))
    return out


def identity_findings(spec: ServerSpec, props: Mapping, models: Mapping | None = None,
                      golden_props: Mapping | None = None) -> list[str]:
    """[pure] The sorted identity findings of one ``/props`` observation, ``[]`` when none.

    The per-field checks run on the RAW object, exactly as protocol 2.3 and 5.3 require: the
    alias; the slot count; the per-slot ``n_ctx``; that ``realpath(model_path)`` is the real
    path of ``spec.gguf_path`` (a raw ``model_path`` that is not an absolute path -- for
    instance one that is already a token -- cannot be real-path checked and is the finding
    ``model_path``); the build commit prefix in ``build_info``; the ``/v1/models`` listing;
    and that ``/props`` reports a slot-prompt similarity of 0.0.

    When ``golden_props`` is given, the raw object is then TOKENIZED by
    :func:`tokenized_props` and the WHOLE tokenized object is compared with the golden one;
    any difference, or a ``model_path`` that cannot be tokenized, is ``props_mismatch``.
    ``golden_props`` is ``None`` only in the pre-freeze capture (protocol 5.8 item 1)."""
    findings: set[str] = set()
    if props.get('model_alias') != spec.alias:
        findings.add('alias')
    if props.get('total_slots') != spec.n_slots:
        findings.add('total_slots')
    if props_n_ctx_per_slot(props) != spec.ctx_per_slot:
        findings.add('n_ctx')
    model_path = str(props.get('model_path') or '')
    if not os.path.isabs(model_path) \
            or os.path.realpath(model_path) != os.path.realpath(str(spec.gguf_path)):
        findings.add('model_path')
    if spec.llama_commit[:7] not in str(props.get('build_info') or ''):
        findings.add('build_info')
    if models is not None:
        ids = [d.get('id') for d in (models.get('data') or []) if isinstance(d, Mapping)]
        if spec.alias not in ids:
            findings.add('models_endpoint')
    sps = props_slot_prompt_similarity(props)
    if sps is None or sps != 0.0:
        findings.add('slot_prompt_similarity')
    if golden_props is not None:
        try:
            observed = tokenized_props(props)
        except (lab_common.UntokenizablePath, ValueError, TypeError):
            findings.add('props_mismatch')
            findings.add('model_path')
        else:
            if observed != dict(golden_props):
                findings.add('props_mismatch')
    return sorted(findings)


def assert_identity(spec: ServerSpec, props: Mapping, models: Mapping | None = None,
                    golden_props: Mapping | None = None) -> None:
    """[pure] Raise :class:`lab_common.ServerIdentityError` naming every finding of
    :func:`identity_findings`; return None when there is none."""
    findings = identity_findings(spec, props, models, golden_props)
    if findings:
        raise lab_common.ServerIdentityError(','.join(findings))


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
# the serving manifest (protocol 2.2 item 2, re-verified at every start: P:452, P:918)
# --------------------------------------------------------------------------- #
def serving_manifest_problems(spec: ServerSpec, manifest: Mapping | None,
                              expected_sha256: str | None) -> list[str]:
    """Re-verify the frozen serving manifest against the launcher this start will exec.

    Returns sorted problem LABELS (for the private record and the tests), ``[]`` when every
    check below passed; the chain only ever carries the one closed code
    ``serving_manifest``.  What is PERFORMED, in order:

    1. ``manifest`` is an object and ``expected_sha256`` is a 64-hex digest (``absent``);
    2. ``sha256_canonical(manifest) == expected_sha256`` -- the frozen
       ``llama_cpp.serving_manifest_sha256`` (``digest``);
    3. it carries every :data:`SERVING_MANIFEST_REQUIRED` member (``missing:<key>``);
    4. ``llama_cpp_commit`` equals ``spec.llama_commit`` (``commit``) and
       ``props_build_info`` contains its 7-character prefix (``props_build_info``);
    5. ``spec.llama_bin`` is an ABSOLUTE path to a regular file (``launcher_not_explicit``,
       ``launcher_missing``) whose recomputed SHA-256 is ``launcher_sha256``
       (``launcher_sha256``);
    6. ``libraries`` is a non-empty list (``libraries_empty``) of ``{name, sha256}`` entries
       (``library_entry``); each is resolved BY BASE NAME in the directory of the resolved
       launcher -- the ``@rpath`` of a llama.cpp build at the pinned commit, where the thin
       launcher and its nine libraries sit side by side (protocol 2.2, P:436) -- and its
       recomputed SHA-256 must equal the entry's (``library_missing:<name>``,
       ``library_sha256:<name>``).

    What is NOT performed: re-deriving the dependency closure from the Mach-O load commands
    (``experiments/live_ab_serving/dependency_closure.py`` owns that and this module may not
    import it), so the COMPLETENESS of ``libraries`` is bound by the frozen digest alone; and
    ``metal_library``, ``resolved_rpath`` and the build strings are not recomputed."""
    problems: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(expected_sha256, str) \
            or not _HEX64_RE.match(expected_sha256):
        return ['absent']
    try:
        digest = lab_common.sha256_canonical(dict(manifest))
    except (TypeError, ValueError):
        digest = ''
    if digest != expected_sha256:
        problems.append('digest')
    for key in SERVING_MANIFEST_REQUIRED:
        if key not in manifest:
            problems.append('missing:%s' % key)
    if 'llama_cpp_commit' in manifest and manifest.get('llama_cpp_commit') != spec.llama_commit:
        problems.append('commit')
    if 'props_build_info' in manifest \
            and spec.llama_commit[:7] not in str(manifest.get('props_build_info') or ''):
        problems.append('props_build_info')
    launcher = Path(str(spec.llama_bin))
    if not launcher.is_absolute():
        problems.append('launcher_not_explicit')
        launcher_dir = None
    elif not launcher.is_file():
        problems.append('launcher_missing')
        launcher_dir = None
    else:
        launcher_dir = Path(os.path.realpath(str(launcher))).parent
        try:
            if lab_common.sha256_file(launcher) != manifest.get('launcher_sha256'):
                problems.append('launcher_sha256')
        except OSError:
            problems.append('launcher_missing')
    libraries = manifest.get('libraries')
    if not isinstance(libraries, list) or not libraries:
        problems.append('libraries_empty')
        libraries = []
    for entry in libraries:
        if not isinstance(entry, Mapping) or not isinstance(entry.get('name'), str) \
                or not isinstance(entry.get('sha256'), str) or not entry.get('name'):
            problems.append('library_entry')
            continue
        name = Path(str(entry['name'])).name
        if launcher_dir is None:
            continue                     # already refused above; nothing to resolve against
        target = launcher_dir / name
        try:
            if not target.is_file():
                problems.append('library_missing:%s' % name)
            elif lab_common.sha256_file(target) != entry['sha256']:
                problems.append('library_sha256:%s' % name)
        except OSError:
            problems.append('library_missing:%s' % name)
    return sorted(set(problems))


# --------------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------------- #
def _golden_part(golden: object, name: str, default: object) -> object:
    """``golden`` may be a ``lab_client.GoldenReceipt`` (attributes) or the orchestrator's
    plain mapping ``{props, generation_settings, mask, float_tolerance}``."""
    if isinstance(golden, Mapping):
        return golden.get(name, default)
    return getattr(golden, name, default)


def start(spec: ServerSpec, *, golden_props: Mapping | None = None,
          golden: object | None = None, sampling: Mapping | None = None,
          timeout_s: float = 600.0, recompute_gguf_sha256: bool = True,
          serving_manifest: Mapping | None = None,
          serving_manifest_sha256: str | None = None,
          mode: str = 'trial', kind: str = 'start', restart_index: int = 0) -> dict:
    """Launch the frozen argv and return the ``server_started`` body (event schema T4), or
    stop what was launched and raise :class:`lab_common.ServerStartFailed`.

    The stages run in the order of :data:`START_STAGES`; the first that fails ends the start:

    * ``gguf`` -- :func:`assert_gguf` (bytes and recomputed SHA-256);
    * ``serving_manifest`` -- :func:`serving_manifest_problems`; an ABSENT manifest is a
      failure of this stage, never a skip (P:918: re-verified at every start and restart);
    * ``launch`` -- the OS refused the exec, or the child exited before ``/health`` answered
      200 (``process_exited``, with the child's return code; never ``build_info``);
    * ``health`` -- no 200 within ``timeout_s`` (``health_timeout``);
    * ``identity`` -- :func:`identity_findings` on the RAW ``/props`` (a probe that fails is
      ``props_mismatch``), the full TOKENIZED object against ``golden_props``, and the raw
      ``build_info`` against the manifest's ``props_build_info``;
    * ``smoke`` -- one SERVER_SMOKE completion projected onto the schema's closed USAGE /
      TIMINGS sets; a missing key is ``smoke_no_usage`` (never 0), a transport failure
      ``smoke_transport``, and the receipt is compared finding for finding with ``golden``.

    On EVERY failure after the child was launched -- including an exception this function
    did not anticipate -- the child is stopped through :func:`stop` before anything is
    raised, so no failed start leaves a process behind.  The raised record's ``returncode``
    is the one that stop observed.

    Refused before any side effect, with ``PreflightError``: ``mode='trial'`` (the default,
    every trial start and restart) without ``golden_props``, ``golden`` and ``sampling`` --
    there is no placeholder smoke; an unknown ``mode`` or ``kind``.  ``mode='capture'`` is
    the pre-freeze capture of protocol 5.8 item 1, where the golden objects are being made:
    it may omit them, and then returns ``props_matches_golden: None`` / ``smoke: None`` --
    values the ``server_started`` schema rejects, so a capture body can never be appended as
    a trial start -- plus ``props_tokenized``, the object stage 1 deposits.

    ``props_sha256`` is the canonical digest of the TOKENIZED ``/props`` object, the same
    form as the golden digest.  Side effects: a child process in its own session and a log
    file."""
    if mode not in ('trial', 'capture'):
        raise lab_common.PreflightError('lab_server.start: unknown mode %r' % (mode,))
    if kind not in ('start', 'restart'):
        raise lab_common.PreflightError('lab_server.start: unknown kind %r' % (kind,))
    if mode == 'trial' and (golden_props is None or golden is None or sampling is None):
        raise lab_common.PreflightError(
            'lab_server.start: a trial start needs golden_props, golden and sampling; a '
            'start that cannot compare is refused, never given a placeholder smoke')
    argv = server_argv(spec)
    record: dict[str, Any] = {
        'server_id': spec.server_id, 'kind': kind, 'stage': None, 'findings': [],
        'pid': 0, 'returncode': None, 'argv_sha256': lab_common.sha256_canonical(argv),
        'props_sha256': None, 'load_seconds': 0.0, 'restart_index': int(restart_index)}

    def fail(stage: str, findings: list[str], proc: subprocess.Popen | None = None,
             **extra: Any) -> None:
        if proc is not None:
            record['pid'] = int(proc.pid)
            stopped = stop(proc.pid)
            rc = proc.returncode if proc.returncode is not None else stopped.get('returncode')
            record['returncode'] = int(rc) if isinstance(rc, int) else None
        record.update(extra)
        record['stage'] = stage
        record['findings'] = sorted(set(findings))
        raise lab_common.ServerStartFailed(record)

    # -- gguf ------------------------------------------------------------------
    try:
        gguf_sha = assert_gguf(spec, recompute_sha256=recompute_gguf_sha256)
    except lab_common.ServerIdentityError as exc:
        fail('gguf', str(exc).split(','))
    except OSError:
        fail('gguf', ['gguf_sha256'])
    # -- serving manifest ------------------------------------------------------
    if serving_manifest_problems(spec, serving_manifest, serving_manifest_sha256):
        fail('serving_manifest', ['serving_manifest'])
    # -- launch ----------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        Path(spec.log_path).parent.mkdir(parents=True, exist_ok=True)
        logf = open(str(spec.log_path), 'ab')
        try:
            proc = subprocess.Popen(argv, stdout=logf, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        finally:
            logf.close()
    except OSError:
        fail('launch', ['process_exited'])
    _CHILDREN[proc.pid] = proc
    try:
        base = spec.base_url
        deadline = time.perf_counter() + float(timeout_s)
        # -- health --------------------------------------------------------------
        while True:
            if proc.poll() is not None:
                fail('launch', ['process_exited'], proc,
                     load_seconds=time.perf_counter() - t0)
            if health(base, timeout=2.0)['ok']:
                break
            if time.perf_counter() > deadline:
                fail('health', ['health_timeout'], proc,
                     load_seconds=time.perf_counter() - t0)
            time.sleep(0.2)
        load_seconds = time.perf_counter() - t0
        # -- identity ------------------------------------------------------------
        try:
            p = probe(base)
        except lab_common.ServerIdentityError as exc:
            fail('identity', str(exc).split(','), proc, load_seconds=load_seconds)
        props, models = p['props'], p['models']
        if not isinstance(props, Mapping) or not isinstance(models, Mapping):
            fail('identity', ['props_mismatch'], proc, load_seconds=load_seconds)
        try:
            props_tok = tokenized_props(props)
            props_sha = lab_common.sha256_canonical(props_tok)
        except (lab_common.UntokenizablePath, ValueError, TypeError):
            props_tok, props_sha = None, None
        findings = identity_findings(spec, props, models, golden_props)
        if props_tok is None:
            findings.append('model_path')
        if isinstance(serving_manifest, Mapping) \
                and props.get('build_info') != serving_manifest.get('props_build_info'):
            findings.append('build_info')
        if findings:
            fail('identity', findings, proc, load_seconds=load_seconds,
                 props_sha256=props_sha)
        props_matches = (None if golden_props is None
                         else bool(props_tok == dict(golden_props)))
        # -- smoke ---------------------------------------------------------------
        smoke_body: dict | None = None
        if golden is not None and sampling is not None:
            smoke_body, smoke_findings = _smoke_attempt(base, spec, golden, sampling)
            if smoke_findings:
                fail('smoke', smoke_findings, proc, load_seconds=load_seconds,
                     props_sha256=props_sha)
        body = {
            'server_id': spec.server_id,
            'pid': int(proc.pid),
            'port': int(spec.port),
            'argv_sha256': record['argv_sha256'],
            'gguf': {'bytes': int(Path(spec.gguf_path).stat().st_size), 'sha256': gguf_sha},
            'props_sha256': props_sha,
            'props_matches_golden': props_matches,
            'total_slots': int(props.get('total_slots') or 0),
            'n_ctx': int(props_n_ctx_per_slot(props) or 0),
            'load_seconds': float(load_seconds),
            'smoke': smoke_body,
        }
        if mode == 'capture':
            body['props_tokenized'] = props_tok
    except lab_common.ServerStartFailed:
        raise
    except BaseException:
        # Anything this function did not anticipate still may not leave the child running.
        stop(proc.pid)
        raise
    return body


def exit_status(pid: int) -> int | None:
    """The return code of a child :func:`start` launched; ``None`` while it is running.

    Answers from ``_CHILDREN`` (polling, which also reaps) and, after :func:`stop` has
    reaped it, from the return code stop recorded.  A pid this module never started raises
    ``LabError``: "unknown" is never reported as "running"."""
    pid = int(pid)
    proc = _CHILDREN.get(pid)
    if proc is not None:
        rc = proc.poll()
        return None if rc is None else int(rc)
    if pid in _EXITED:
        return _EXITED[pid]
    raise lab_common.LabError('pid %d was not started by lab_server' % pid)


def smoke(base_url: str, spec: ServerSpec, golden: object, sampling: Mapping) -> dict:
    """One non-task completion, tagged ``phase = SERVER_SMOKE`` by the caller.

    The receipt of this response enters the reconciliation identity of protocol 13.1 and its
    comparison against the golden object is the first proof, at every start and restart, that
    the sampler settings are the frozen ones.  Returns the smoke sub-object of the
    ``server_started`` body; raises ``ReceiptMismatch`` naming every finding otherwise
    (:func:`start` records the same findings in its failure record instead).

    The comparison is implemented here rather than imported from ``lab_client``: the
    isolation matrix forbids ``lab_server`` to import it, and a second implementation of the
    same frozen rule is a feature, not duplication.  ``tests_lab_serving`` asserts the two
    agree finding for finding."""
    out, findings = _smoke_attempt(base_url, spec, golden, sampling)
    if findings:
        raise lab_common.ReceiptMismatch(','.join(findings))
    assert out is not None
    return out


def _smoke_attempt(base_url: str, spec: ServerSpec, golden: object,
                   sampling: Mapping) -> tuple[dict | None, list[str]]:
    """The smoke completion and its sorted findings.  The body is returned only when every
    key of the closed USAGE / TIMINGS sets was present; it is never padded with zeros."""
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
    except (requests.RequestException, ValueError):
        return None, ['smoke_transport']
    if r.status_code != 200 or not isinstance(data, dict):
        return None, ['smoke_transport']
    findings: set[str] = set()
    usage_raw = data.get('usage') if isinstance(data.get('usage'), Mapping) else None
    timings_raw = data.get('timings') if isinstance(data.get('timings'), Mapping) else None
    verbose = data.get('__verbose') if isinstance(data.get('__verbose'), Mapping) else {}
    usage: dict[str, int] = {}
    timings: dict[str, Any] = {}
    for key in SMOKE_USAGE_KEYS[:3]:
        v = (usage_raw or {}).get(key)
        if isinstance(v, int) and not isinstance(v, bool):
            usage[key] = int(v)
    details = (usage_raw or {}).get('prompt_tokens_details')
    cached = details.get('cached_tokens') if isinstance(details, Mapping) else None
    if not (isinstance(cached, int) and not isinstance(cached, bool)):
        cached = verbose.get('tokens_cached')
    if isinstance(cached, int) and not isinstance(cached, bool):
        usage['cached_tokens'] = int(cached)
    for key in SMOKE_TIMINGS_INT_KEYS:
        v = (timings_raw or {}).get(key)
        if isinstance(v, int) and not isinstance(v, bool):
            timings[key] = int(v)
    for key in SMOKE_TIMINGS_FLOAT_KEYS:
        v = (timings_raw or {}).get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) \
                and v == v and v not in (float('inf'), float('-inf')):
            timings[key] = float(v)
    if set(usage) != set(SMOKE_USAGE_KEYS) or len(timings) != (
            len(SMOKE_TIMINGS_INT_KEYS) + len(SMOKE_TIMINGS_FLOAT_KEYS)):
        findings.add('smoke_no_usage')
    if data.get('model') != spec.alias:
        findings.add('model_alias_mismatch')
    findings.update(smoke_receipt_findings(data, golden, seed_sent=int(body['seed'])))
    if 'smoke_no_usage' in findings:
        return None, sorted(findings)
    out = {
        'request_sha256': lab_common.sha256_canonical(body),
        'receipt_matches_golden': not findings,
        'usage': {k: usage[k] for k in SMOKE_USAGE_KEYS},
        'timings': {k: timings[k] for k in SMOKE_TIMINGS_INT_KEYS + SMOKE_TIMINGS_FLOAT_KEYS},
        'ok': not findings,
    }
    return out, sorted(findings)


def smoke_receipt_findings(data: Mapping, golden: object, *, seed_sent: int) -> list[str]:
    """[pure] The second implementation of the frozen receipt rule of protocol 13.2.

    Returns a sorted list of reason codes from :data:`RECEIPT_FINDINGS` (equal to
    ``lab_client.RECEIPT_FINDINGS``); the detail of a mismatch never leaves this process."""
    gold_gen = dict(_golden_part(golden, 'generation_settings', {}) or {})
    mask = set(_golden_part(golden, 'mask', ('seed',)) or ('seed',))
    tol = float(_golden_part(golden, 'float_tolerance', 1e-6))
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
    """SIGTERM the process group, then SIGKILL after ``grace_s``.  A child this module
    started is reaped and its return code kept for :func:`exit_status`."""
    t0 = time.perf_counter()
    proc = _CHILDREN.get(int(pid))

    def reaped() -> dict:
        _CHILDREN.pop(int(pid), None)
        _EXITED[int(pid)] = proc.returncode
        return {'returncode': proc.returncode, 'seconds': time.perf_counter() - t0}

    if proc is not None and proc.poll() is not None:
        return reaped()                  # already exited: never signal a reused pid
    try:
        os.killpg(int(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            if proc is not None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                if proc.returncode is not None:
                    return reaped()
            return {'returncode': None, 'seconds': time.perf_counter() - t0}
    deadline = t0 + grace_s
    while time.perf_counter() < deadline:
        if proc is not None:
            if proc.poll() is not None:
                return reaped()
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
        if proc.returncode is not None:
            return reaped()
        return {'returncode': None, 'seconds': time.perf_counter() - t0}
    return {'returncode': None, 'seconds': time.perf_counter() - t0}


def _pid_alive(pid: int) -> bool:
    """Whether ``pid`` still names a live process.  A child of this module is polled (and
    so reaped); any other pid is probed with signal 0, and a pid we may not signal is alive."""
    pid = int(pid)
    proc = _CHILDREN.get(pid)
    if proc is not None:
        return proc.poll() is None
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def restart(spec: ServerSpec, golden_props: Mapping, *,
            previous_props_sha256: str | None = None, golden: object | None = None,
            sampling: Mapping | None = None, timeout_s: float = 600.0,
            previous_pid: int | None = None, restart_index: int = 1,
            serving_manifest: Mapping | None = None,
            serving_manifest_sha256: str | None = None,
            recompute_gguf_sha256: bool = True) -> dict:
    """A supervised restart with the identical argv (protocol 5.3): the CALLER has already
    stopped the old process.  Returns T4's body plus ``props_equal_previous``.

    Refused before any side effect, with ``PreflightError``: ``previous_pid`` absent or
    still alive (two servers on one port would make every comparison below meaningless);
    ``previous_props_sha256`` not a 64-hex digest; ``restart_index`` below 1; and, through
    :func:`start`'s trial mode, any of ``golden_props`` / ``golden`` / ``sampling`` absent.

    Every stage of :func:`start` runs again -- GGUF, serving manifest, launch, health, the
    full tokenized ``/props`` against the golden object, the smoke -- with ``kind='restart'``
    in any failure record.  ``props_equal_previous`` is an ACTUAL comparison of the new
    tokenized ``/props`` digest with ``previous_props_sha256``, not a copy of the golden
    flag; a False value is returned, not raised, and the orchestrator maps it to
    ``trial_aborted(server_identity)`` (protocol 6.4 row 6)."""
    if previous_pid is None or _pid_alive(int(previous_pid)):
        raise lab_common.PreflightError(
            'lab_server.restart: the previous server (pid %r) must be stopped by the caller '
            'first' % (previous_pid,))
    if not isinstance(previous_props_sha256, str) \
            or not _HEX64_RE.match(previous_props_sha256):
        raise lab_common.PreflightError(
            'lab_server.restart: previous_props_sha256 must be the 64-hex digest of the '
            'previous start, so that props_equal_previous is a comparison')
    if int(restart_index) < 1:
        raise lab_common.PreflightError('lab_server.restart: restart_index starts at 1')
    body = start(spec, golden_props=golden_props, golden=golden, sampling=sampling,
                 timeout_s=timeout_s, recompute_gguf_sha256=recompute_gguf_sha256,
                 serving_manifest=serving_manifest,
                 serving_manifest_sha256=serving_manifest_sha256, mode='trial',
                 kind='restart', restart_index=int(restart_index))
    body['props_equal_previous'] = bool(body['props_sha256'] == previous_props_sha256)
    return body


def _root(base_url: str) -> str:
    u = str(base_url).rstrip('/')
    return u[:-3].rstrip('/') if u.endswith('/v1') else u
