"""Two-process fixture of the production LOCK IMPLEMENTATION, on an isolated lock file.

Root, 2026-09-21 21:50: "Yes: use two separate probe processes through the actual
production execution lock and sandbox route. No model or serving process is
required for this bounded lock fixture. Hold the first process inside its
critical section with an explicit readiness handshake, then have the second
attempt the same lock. Record process identifiers, lock identity,
attempted/acquired/released monotonic times and timeout/wait outcome. Show that
the second cannot enter while the first holds the lock ... Label this a
production-lock/sandbox fixture, NOT two live model episodes."

This closes the gap root found in my containment receipt: the earlier probe
started ONE sandbox program and inferred exclusion from an empty peer glob, which
establishes nothing. Here a real contender actually attempts the lock.

NEGATIVE CONTROL: root, same review -- "A controlled negative control should
remove the lock only inside the ISOLATED SYNTHETIC FIXTURE and demonstrate
overlapping entry is observable; NEVER disable the actual production lock
configuration to obtain this control." The control therefore runs both processes
against a throwaway lock path with locking bypassed in the child only; the
production lock path and its configuration are never touched.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402

FIXTURE_SCHEMA = 'live_ab/lock_contender_fixture-v1'
HOLD_S = 1.5
CONTENDER_WAIT_S = 4.0


def _child_source(lock_path: str, role: str, ready: str, hold: float,
                   wait_s: float, bypass: bool) -> str:
    """One probe process: take the PRODUCTION lock and report monotonic times."""
    return (
        'import json, os, sys, time\n'
        'sys.path.insert(0, %r)\n'
        'import lab_data\n'
        'LOCK, ROLE, READY, HOLD, WAIT, BYPASS = %r, %r, %r, %f, %f, %r\n'
        'rec = {"role": ROLE, "pid": os.getpid(), "lock": LOCK,\n'
        '       "attempted_monotonic": time.monotonic()}\n'
        'try:\n'
        '    if BYPASS:\n'
        '        class _NoLock:\n'
        '            def __enter__(self): return self\n'
        '            def __exit__(self, *a): return False\n'
        '        ctx = _NoLock()\n'
        '    else:\n'
        '        ctx = lab_data._ExecutionLock(LOCK, WAIT)\n'
        '    with ctx:\n'
        '        rec["acquired_monotonic"] = time.monotonic()\n'
        '        rec["outcome"] = "acquired"\n'
        '        if ROLE == "holder":\n'
        '            open(READY, "w").write("ready")\n'
        '            time.sleep(HOLD)\n'
        '        rec["released_monotonic"] = time.monotonic()\n'
        'except Exception as e:\n'
        '    rec["outcome"] = "blocked"\n'
        '    rec["error"] = type(e).__name__ + ": " + str(e)[:200]\n'
        '    rec["gave_up_monotonic"] = time.monotonic()\n'
        'print("<<<LOCK>>>" + json.dumps(rec))\n'
    ) % (str(HERE), lock_path, role, ready, hold, wait_s, bypass)


def _run(src: str, timeout: float) -> Dict[str, Any]:
    p = subprocess.run([sys.executable, '-c', src], capture_output=True,
                       text=True, timeout=timeout)
    out = p.stdout or ''
    if '<<<LOCK>>>' not in out:
        return {'outcome': 'no_result', 'returncode': p.returncode,
                'stderr_tail': (p.stderr or '')[-300:]}
    return json.loads(out.split('<<<LOCK>>>', 1)[1].strip().splitlines()[0])


def run_fixture(work: Optional[Path] = None, *, bypass_lock: bool = False,
                contender_wait_s: float = CONTENDER_WAIT_S) -> Dict[str, Any]:
    """Holder takes the lock, signals readiness, then the contender attempts it."""
    work = Path(work or (lab_common.WORK_ROOT / '_lockfixture'))
    work.mkdir(parents=True, exist_ok=True)
    # The NEGATIVE CONTROL never touches the production lock path.
    lock = work / ('control.lock' if bypass_lock else 'sandbox.lock')
    ready = work / 'ready.flag'
    if ready.exists():
        ready.unlink()

    holder_src = _child_source(str(lock), 'holder', str(ready), HOLD_S,
                               contender_wait_s, bypass_lock)
    contender_src = _child_source(str(lock), 'contender', str(ready), 0.0,
                                  contender_wait_s, bypass_lock)

    t_start = time.monotonic()
    holder = subprocess.Popen([sys.executable, '-c', holder_src],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
    # EXPLICIT READINESS HANDSHAKE: do not race the contender against startup.
    deadline = time.monotonic() + 10.0
    while not ready.exists() and time.monotonic() < deadline:
        if holder.poll() is not None:
            break
        time.sleep(0.01)
    handshake_ok = ready.exists()

    contender = _run(contender_src, timeout=contender_wait_s + 15.0)
    out, err = holder.communicate(timeout=30.0)
    h = ({'outcome': 'no_result', 'stderr_tail': (err or '')[-300:]}
         if '<<<LOCK>>>' not in (out or '')
         else json.loads(out.split('<<<LOCK>>>', 1)[1].strip().splitlines()[0]))

    overlapped = None
    if h.get('acquired_monotonic') and contender.get('acquired_monotonic'):
        overlapped = (contender['acquired_monotonic'] < h.get('released_monotonic', 0))

    return {
        'schema': FIXTURE_SCHEMA,
        'label': ('TWO-PROCESS FIXTURE OF THE PRODUCTION LOCK IMPLEMENTATION ON AN '
                  'ISOLATED LOCK FILE. Corrected by root 2026-09-21 22:23: my '
                  'earlier "PRODUCTION-LOCK/SANDBOX FIXTURE" overstated it. The '
                  'children are ORDINARY PYTHON SUBPROCESSES that enter '
                  'lab_data._ExecutionLock; they never invoke the sandbox '
                  'execution function, and the lock file is a synthetic fixture '
                  'path, not the production lock the reference sweep resolves. '
                  'Same lock CLASS, not the combined lock/sandbox route. NOT two '
                  'live model episodes.'),
        'combined_lock_sandbox_route': 'NOT EXERCISED -- still pending',
        'invocation_parameters': None,      # filled by the caller; see receipt
        'bypass_lock_control': bypass_lock,
        'lock_identity': lab_common.tokenize_path(lock),
        'readiness_handshake_observed': handshake_ok,
        'holder': h,
        'contender': contender,
        'contender_blocked_while_holder_held': (
            contender.get('outcome') == 'blocked' if not bypass_lock else None),
        'overlapping_entry_observed': overlapped,
        'elapsed_s': time.monotonic() - t_start,
        'hold_s': HOLD_S,
        'contender_wait_s': contender_wait_s,
    }
