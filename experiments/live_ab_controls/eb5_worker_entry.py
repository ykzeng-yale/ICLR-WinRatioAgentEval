"""EB5 worker entry: ``eb1c_worker_entry`` plus a file barrier between ``call_started`` and the
POST (control C5).

Repair contract EB5 (session 60; root 20:40 item 3: "A worker with a used permit can invoke POST
after the terminal snapshot").  At b049307 no test exercised the third interleaving -- the
permit granted before the snapshot and the POST entered after it: the send-permit controls of
``experiments/live_ab_serving/tests_supervisor_entry.py`` (``in_flight`` / ``not_yet_sent``)
are fake-thread interleavings, not a real late POST.  This control is a test-only ``worker_cmd``
wrapper that blocks on a file barrier
between ``call_started`` (``lab_client.py``: spooled and fsynced first) and ``session.post``.
This is that wrapper::

    <python> eb5_worker_entry.py --harness-config CFG --barrier-dir DIR --job JOB

It relocates the harness configuration exactly as ``eb1c_worker_entry`` does, and then, ONLY
when ``DIR/hold_<arrival>`` exists for this job's arrival, wraps ``requests.Session.post`` so
that the FIRST post of the process first creates ``DIR/at_<arrival>`` (the worker has spooled
``call_started`` and is about to send) and then waits until ``DIR/release_<arrival>`` exists.
Every other job runs the unmodified ``lab_worker.main``.  Released before the orchestrator's
snapshot, the POST reaches the server while the attempt is still ingested; released after it,
the POST is a LATE POST -- unless the worker was killed at the barrier, which is what the EB5
drain does at the hard cap.

A TEST DOUBLE.  Prepared and checked by AI agent sessions; not human peer review or author
sign-off (protocol 14.7).
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parent / 'live_ab')):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _arrival_of(argv: list[str]) -> int | None:
    if '--job' not in argv:
        return None
    match = re.search(r'job_(\d+)_\d+\.json$', argv[argv.index('--job') + 1])
    return int(match.group(1)) if match else None


def install_barrier(barrier: Path, arrival: int) -> None:
    import requests
    original = requests.Session.post
    state = {'held': False}

    def post(self, *args, **kwargs):
        if not state['held']:
            state['held'] = True
            (barrier / ('at_%d' % arrival)).write_text(str(os.getpid()), encoding='utf-8')
            while not (barrier / ('release_%d' % arrival)).exists():
                time.sleep(0.02)
        return original(self, *args, **kwargs)

    requests.Session.post = post


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 4 or argv[0] != '--harness-config' or argv[2] != '--barrier-dir':
        sys.stderr.write('eb5_worker_entry: --harness-config PATH --barrier-dir DIR first\n')
        return 2
    barrier = Path(argv[3])
    rest = [argv[0], argv[1]] + argv[4:]
    arrival = _arrival_of(rest)
    if arrival is not None and (barrier / ('hold_%d' % arrival)).exists():
        install_barrier(barrier, arrival)
    import eb1c_worker_entry
    return eb1c_worker_entry.main(rest)


if __name__ == '__main__':
    sys.exit(main())
