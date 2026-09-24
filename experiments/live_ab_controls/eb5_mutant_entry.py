"""EB5 mutation entry: ``lab_orchestrator.main`` with one piece of the worker resolution UNDONE.

Repair contract EB5 (session 60; root 20:40 item 3, root 21:15 item 3).  ``--mutation NAMES``
comes first (a comma-separated list); the rest of the argv is ``lab_orchestrator.main``'s.
Never used outside ``tests_eb5_resolution``.  Each mutation restores the pre-EB5 behaviour of
one mechanism (the ``O:`` lines below are lines of
``git show b049307:experiments/live_ab/lab_orchestrator.py``), so that a control run
through it shows that THIS mechanism is what produced the behaviour the control asserts:

* ``drain_disabled`` -- ``World.drain_workers`` does nothing: an abort or a pause closes at once
  over running workers (O:2266-2273, O:2606-2651 at b049307).  Controls C2 and C5.
* ``spool_error_no_kill`` -- a ``SpoolError`` reveals the attempt ``interrupted`` and forgets the
  worker, with no kill (O:2474-2475).  Control C3.
* ``wait_times_out`` -- ``subprocess.Popen.wait`` of a WORKER process (its argv carries
  ``--job``) raises ``TimeoutExpired`` whenever it is given a timeout: the SIGKILL is sent but
  its exit is never confirmed (the kill's reap fails).  Control C4.
* ``bypass_verdict`` -- ``phase_resolution_verdict`` always returns a PASS record: the close's
  gate is gone.  Control C9 (with C1's and C4's inputs).
* ``no_orphan_resolution`` -- a resumed invocation resolves no earlier worker and its
  ``interrupted`` reveal no longer checks for one (O:2923-2938, O:1930-1934).  Control C6.
* ``orphan_kill_fails`` -- ``kill_orphan_worker`` sends nothing and reports
  ``alive_unresolved``: the refusal branch of the resume.  Control C6.

A TEST DOUBLE.  Prepared and checked by AI agent sessions; not human peer review or author
sign-off (protocol 14.7).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live_ab'
if str(LIVE) not in sys.path:
    sys.path.insert(0, str(LIVE))

import lab_orchestrator                                                 # noqa: E402

MUTATIONS: tuple[str, ...] = ('drain_disabled', 'spool_error_no_kill', 'wait_times_out',
                               'bypass_verdict', 'no_orphan_resolution', 'orphan_kill_fails')


def _pass_record(events, spool_stats, server_obs) -> dict:
    return {'verdict': 'PASS', 'problems': [], 'unresolved_attempts': [],
            'unfinished_calls': [], 'late_spools': [], 'servers': [],
            'superseded_reason': None}


def apply(name: str) -> None:
    World = lab_orchestrator.World
    if name == 'drain_disabled':
        World.drain_workers = lambda self, *, reveal: None
    elif name == 'spool_error_no_kill':
        def interrupt(self, att):
            self.live_workers.discard(att.arrival)
            self._interrupt(att)
        World.interrupt_unreadable = interrupt
    elif name == 'wait_times_out':
        original = subprocess.Popen.wait

        def wait(self, timeout=None):
            args = self.args if isinstance(self.args, (list, tuple)) else [self.args]
            if timeout is not None and '--job' in [str(a) for a in args]:
                raise subprocess.TimeoutExpired(self.args, timeout)
            return original(self, timeout=timeout)
        subprocess.Popen.wait = wait
    elif name == 'bypass_verdict':
        lab_orchestrator.phase_resolution_verdict = _pass_record
    elif name == 'no_orphan_resolution':
        World.resolve_previous_workers = lambda self, events: True
        World.assert_resolved_before_interrupt = lambda self, arrival: None
    elif name == 'orphan_kill_fails':
        lab_orchestrator.kill_orphan_worker = \
            lambda pid, job_name, **kw: ('alive_unresolved', None)
    else:
        raise SystemExit('unknown mutation %r' % name)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != '--mutation':
        sys.stderr.write('eb5_mutant_entry: --mutation {%s}[,...] comes first\n'
                         % ','.join(MUTATIONS))
        return 2
    names = [n for n in argv[1].split(',') if n]
    if not names or any(n not in MUTATIONS for n in names):
        sys.stderr.write('eb5_mutant_entry: unknown mutation in %r\n' % argv[1])
        return 2
    for name in names:
        apply(name)
    return lab_orchestrator.main(argv[2:])


if __name__ == '__main__':
    sys.exit(main())
