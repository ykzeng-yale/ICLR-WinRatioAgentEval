"""EB1c mutation entry: ``lab_orchestrator.main`` with one repair UNDONE, in this process.

Repair contract EB1, step EB1c, mutation controls.  ``--mutation NAME`` comes first; the rest
of the argv is ``lab_orchestrator.main``'s.  Never used outside ``tests_eb1_entry``.

* ``placeholder`` -- root's 20:40 review found that the orchestrator at b049307 appended
  ``server_started`` with ``props_matches_golden: true`` and a smoke ``receipt_matches_golden:
  true`` / ``ok: true`` without comparing anything (``lab_orchestrator.py`` at b049307,
  ``server_started_body``, the non-simulated branch).  :func:`placeholder_start` restores that
  body in place of ``lab_server.start``: it launches the frozen argv and waits for ``/health``
  (the old code attached to a server that was already listening), then returns the old body.
  ``tests_eb1_entry.MutationControl`` runs C2's scenario (a ``/props`` that differs from the
  golden object) through it: C2's assertions and the verifier's ``server.lifecycle`` must then
  FAIL, so the refusal the controls observe is produced by the comparison.
* ``no_boundary_exit_check`` -- ``World.supervise_exits`` (the pair-boundary exit check EB1c
  added) becomes a no-op, restoring the EB1b behaviour in which a server that exited after
  the last health poll was handed the next pair.  ``tests_eb1_entry.C4bExitBetweenPairs``
  shows its assertions fail under it.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_common                                                       # noqa: E402
import lab_orchestrator                                                 # noqa: E402
import lab_server                                                       # noqa: E402
from lab_common import sha256_canonical, sha256_text                   # noqa: E402

USAGE_KEYS = ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cached_tokens')


def placeholder_start(spec, *, timeout_s: float = 600.0, **_ignored) -> dict:
    """Launch, wait for health, probe -- and claim every comparison passed (the b049307
    body, verbatim but for ``pid``, which is the launched child's so that it is stopped)."""
    argv = lab_server.server_argv(spec)
    Path(spec.log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(str(spec.log_path), 'ab') as logf:
        proc = subprocess.Popen(argv, stdout=logf, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    lab_server._CHILDREN[proc.pid] = proc
    deadline = time.perf_counter() + float(timeout_s)
    while not lab_server.health(spec.base_url, timeout=2.0)['ok']:
        if proc.poll() is not None or time.perf_counter() > deadline:
            lab_server.stop(proc.pid)
            raise lab_common.PreflightError('placeholder_start: never healthy')
        time.sleep(0.2)
    probe = lab_server.probe(spec.base_url)
    props = probe.get('props') or {}
    return {
        'server_id': spec.server_id, 'pid': int(proc.pid),
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


#: The mutations this entry can restore, by name (``--mutation NAME`` comes first).
MUTATIONS: tuple[str, ...] = ('placeholder', 'no_boundary_exit_check')


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--mutation' or argv[1] not in MUTATIONS:
        sys.stderr.write('eb1c_mutant_entry: --mutation {%s} comes first\n'
                         % ','.join(MUTATIONS))
        return 2
    if argv[1] == 'placeholder':
        lab_server.start = placeholder_start
    else:
        # the pre-fix pair boundary: an exited server is seen only by the next health poll
        lab_orchestrator.World.supervise_exits = lambda self: None
    return lab_orchestrator.main(argv[2:])


if __name__ == '__main__':
    sys.exit(main())
