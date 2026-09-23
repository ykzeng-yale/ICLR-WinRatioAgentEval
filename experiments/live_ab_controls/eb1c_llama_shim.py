"""EB1c argv shim: the frozen llama-server command line, answered by ``lab_mock_server``.

Repair contract EB1, step EB1c (session 60, after root's 20:40 NO-GO,
``reviews/prerun_bundle_go_nogo_20260923_2040.md`` item 1: "Verify the real production entry
path with bounded model-free controls").  ``lab_orchestrator.main`` launches whatever
``--llama-bin`` names with the argv of ``lab_server.server_argv`` (lab_server.py:147-168).  In
the controls of ``tests_eb1_entry.py`` that launcher is a two-line ``/bin/sh`` script written
into the control's temporary host directory::

    #!/bin/sh
    EB1C_SHIM_STATE='<state dir>' exec '<python>' '<this file>' "$@"

so the pid ``lab_server.start`` records is, after two ``exec``s, the pid of THIS process, which
then runs ``lab_mock_server.main`` in-process: ``lab_server.stop`` signals the process group it
started and reaps exactly this process (no intermediate parent survives a ``killpg``).

What it performs:

* **The argv is parsed strictly.**  Every flag of ``server_argv`` is known; any other token,
  a missing value, or a missing ``--port``/``--alias`` exits 2 before anything listens, so a
  launch line that drifted from the frozen one surfaces as ``process_exited`` at the launch
  stage, never as a server that quietly ignored a flag.  ``-m`` must name an existing file.
* ``--port``, ``--alias`` and ``--log-file`` are MAPPED: port and alias go to
  ``lab_mock_server.main``; one line per launch is appended to the log file.
* **The scenario is keyed by start count.**  ``$EB1C_SHIM_STATE/scenarios.json`` is a list of
  mock scenarios; the N-th launch (0-based, counted by the lines of
  ``$EB1C_SHIM_STATE/launches.jsonl``, appended under ``flock``) serves entry
  ``min(N, len - 1)``.  That is how a restart comes back different (C5) or never healthy (C7)
  with ``lab_mock_server`` UNCHANGED: the mock already has a real exit (``os._exit`` under its
  ``main``) and a fault matcher; what it lacked was a notion of "which start is this", and
  that belongs to the launcher, not to the server.
* An entry may carry a ``_shim`` object, removed before the mock sees the scenario:
  ``{"exit_before_listen": CODE}`` exits CODE without binding (a launch that dies at once);
  ``{"never_listen": true}`` sleeps without binding until signalled (a server that never
  answers ``/health``); ``{"exit_after_responses": N, "exit_code": CODE}`` serves normally
  and ``os._exit(CODE)``s right AFTER the N-th completion response (the smoke counts) has been
  written -- a process that dies between pairs, with no request in flight.  The last one
  wraps the mock's completion handler in this process; ``lab_mock_server``'s own ``exit``
  fault dies BEFORE answering, so it cannot express "answered, then died".
* Every launch is recorded in ``launches.jsonl`` as ``{start, pid, argv, scenario_index,
  scenario_sha256}`` BEFORE it serves, so a control can map every pid in the chain to the
  scenario that process was scripted to serve, and can prove no launched pid outlives the run.

Not a model, not a llama-server, no network beyond 127.0.0.1.  Standard library plus
``lab_mock_server`` only.  This is a TEST DOUBLE: nothing it serves is an observation.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

#: The flags of ``lab_server.server_argv`` that take one value, and those that take none.
#: ``tests_eb1_entry`` asserts this is exactly the frozen argv's vocabulary.
VALUE_FLAGS: frozenset[str] = frozenset({'-m', '--alias', '--host', '--port', '-np', '-c',
                                         '-ngl', '--cache-ram', '--slot-prompt-similarity',
                                         '--log-file'})
BARE_FLAGS: frozenset[str] = frozenset({'--no-kv-unified', '--jinja', '--metrics',
                                        '--no-context-shift', '--offline',
                                        '--no-cache-prompt', '--log-timestamps'})
STATE_ENV: str = 'EB1C_SHIM_STATE'
USAGE_EXIT: int = 2


def parse_argv(argv: list[str]) -> dict[str, str] | None:
    """[pure] ``{flag: value}`` of a frozen llama-server argv (bare flags map to ``''``), or
    None when the argv carries an unknown token, a flag twice, a flag without its value, or
    no ``--port`` / ``--alias`` / ``-m``."""
    out: dict[str, str] = {}
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in out:
            return None
        if tok in BARE_FLAGS:
            out[tok] = ''
            i += 1
        elif tok in VALUE_FLAGS:
            if i + 1 >= len(argv):
                return None
            out[tok] = argv[i + 1]
            i += 2
        else:
            return None
    if not all(k in out for k in ('--port', '--alias', '-m')):
        return None
    return out


def _record_launch(state: Path, argv: list[str]) -> tuple[int, dict]:
    """Append this launch to ``launches.jsonl`` under an exclusive lock and return its
    0-based start index and the scenario entry it serves."""
    scenarios = json.loads((state / 'scenarios.json').read_text(encoding='utf-8'))
    if isinstance(scenarios, dict):
        scenarios = [scenarios]
    with open(state / 'launches.jsonl', 'a+', encoding='utf-8') as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0)
            start = sum(1 for line in fh if line.strip())
            index = min(start, len(scenarios) - 1)
            entry = dict(scenarios[index])
            row = {'start': start, 'pid': os.getpid(), 'argv': list(argv),
                   'scenario_index': index,
                   'scenario_sha256': hashlib.sha256(json.dumps(
                       entry, sort_keys=True).encode('utf-8')).hexdigest(),
                   't_wall': time.time()}
            fh.seek(0, os.SEEK_END)
            fh.write(json.dumps(row, sort_keys=True) + '\n')
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return start, entry


def _exit_after_responses(mock_module, n: int, code: int) -> None:
    """Wrap the mock's completion handler so that the process exits right after the
    ``n``-th completion response has been written (a real exit: nothing is flushed or
    closed, as when a server process dies)."""
    import threading
    handler = mock_module._Handler
    original = handler._complete
    lock = threading.Lock()
    served = [0]

    def _complete(self, body):
        original(self, body)
        try:
            self.wfile.flush()
        except OSError:
            pass
        with lock:
            served[0] += 1
            done = served[0] >= n
        if done:
            os._exit(code)

    handler._complete = _complete


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    flags = parse_argv(argv)
    state_dir = os.environ.get(STATE_ENV)
    if flags is None or not state_dir or not os.path.isfile(flags['-m']):
        sys.stderr.write('eb1c_llama_shim: refused argv %r (state %r)\n' % (argv, state_dir))
        return USAGE_EXIT
    state = Path(state_dir)
    start, entry = _record_launch(state, argv)
    shim = dict(entry.pop('_shim', None) or {})
    log_file = flags.get('--log-file')
    if log_file:
        with open(log_file, 'a', encoding='utf-8') as fh:
            fh.write('eb1c_llama_shim start=%d pid=%d shim=%s\n'
                     % (start, os.getpid(), json.dumps(shim, sort_keys=True)))
    if 'exit_before_listen' in shim:
        return int(shim['exit_before_listen'])
    if shim.get('never_listen'):
        while True:                     # until lab_server.stop signals the process group
            time.sleep(0.5)
    scenario_path = state / ('scenario_%d.json' % start)
    scenario_path.write_text(json.dumps(entry, sort_keys=True), encoding='utf-8')
    import lab_mock_server
    if shim.get('exit_after_responses'):
        _exit_after_responses(lab_mock_server, int(shim['exit_after_responses']),
                              int(shim.get('exit_code', 9)))
    return lab_mock_server.main(['--scenario', str(scenario_path),
                                 '--port', str(int(flags['--port'])),
                                 '--alias', flags['--alias']])


if __name__ == '__main__':
    sys.exit(main())
