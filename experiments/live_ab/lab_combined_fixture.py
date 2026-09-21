"""Combined lock+sandbox exclusion fixture, in the REAL execution topology.

Root, 2026-09-21 23:29, which rejected my proposed design:

    "For combined lock/sandbox evidence, follow the real execution topology:
     trusted supervisor acquires the lock OUTSIDE the sandbox and holds it
     throughout sandbox execution. Do NOT ask sandboxed candidate code to open or
     acquire the supervisor lock itself. That would test a different
     architecture, could be denied by intended containment, and is not required."

My stated default had been to run both processes' payloads through the sandbox
and have each attempt the lock. That tests an architecture this system does not
have: in production the supervisor is trusted and the sandboxed program never
knows the lock exists.

TOPOLOGY ACTUALLY BUILT
-----------------------
  holder supervisor   : acquire lock -> launch bounded sandbox program ->
                        observe it ACTIVE -> publish trusted readiness ->
                        hold until the program ends -> release
  contender supervisor: attempt the SAME lock through the SAME wrapper.
                        Blocked means its sandbox program never started during
                        the holder's protected execution.

Root: "Its expected blocked outcome means its sandbox program does NOT start
during the holder's protected execution. This is the required exclusion
demonstration, not a reason to insist both payloads run concurrently."

Label: a SYNTHETIC INTEGRATION CHECK of this path. Not live model evidence, not a
general concurrency or security theorem.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402

LS_DIR = lab_common.REPO_ROOT / 'experiments' / 'local_stream'
FIXTURE_SCHEMA = 'live_ab/combined_lock_sandbox_fixture-v1'


def _supervisor_source(lock: str, role: str, ready: str, active: str,
                       hold_s: float, wait_s: float) -> str:
    """A trusted supervisor: lock OUTSIDE, sandbox program INSIDE."""
    return (
        'import json, os, sys, time\n'
        'sys.path.insert(0, %r); sys.path.insert(0, %r)\n'
        'import lab_data, sandbox as SB\n'
        'LOCK, ROLE, READY, ACTIVE, HOLD, WAIT = %r, %r, %r, %r, %f, %f\n'
        'rec = {"role": ROLE, "pid": os.getpid(), "lock": LOCK,\n'
        '       "lock_requested": time.monotonic()}\n'
        'try:\n'
        # THE SUPERVISOR holds the lock. The sandboxed program never sees it.
        '    with lab_data._ExecutionLock(LOCK, WAIT):\n'
        '        rec["lock_acquired"] = time.monotonic()\n'
        '        prog = ("import time\\n"\n'
        '                "open(\'sandbox_active\', \'w\').write(\'active\')\\n"\n'
        '                "time.sleep(%%f)\\n"\n'
        '                "print(\'SANDBOX_DONE\')\\n") %% (HOLD,)\n'
        '        rec["sandbox_started"] = time.monotonic()\n'
        '        run = SB.run_program(prog, timeout_s=HOLD + 20.0, mem_bytes=2<<30,\n'
        '                             cpu_seconds=30, output_cap=65536)\n'
        '        rec["sandbox_ended"] = time.monotonic()\n'
        '        rec["sandbox_kind"] = run.get("sandbox_kind")\n'
        '        rec["sandbox_ok"] = "SANDBOX_DONE" in (run.get("stdout") or "")\n'
        '        rec["outcome"] = "acquired"\n'
        '    rec["lock_released"] = time.monotonic()\n'
        'except Exception as e:\n'
        '    rec["outcome"] = "blocked"\n'
        '    rec["error"] = type(e).__name__ + ": " + str(e)[:200]\n'
        '    rec["gave_up"] = time.monotonic()\n'
        '    rec["sandbox_started"] = None\n'
        'print("<<<SUP>>>" + json.dumps(rec))\n'
    ) % (str(HERE), str(LS_DIR), lock, role, ready, active, hold_s, wait_s)


def _parse(out: str) -> Dict[str, Any]:
    if '<<<SUP>>>' not in (out or ''):
        return {'outcome': 'no_result'}
    return json.loads(out.split('<<<SUP>>>', 1)[1].strip().splitlines()[0])


def run_fixture(work: Optional[Path] = None, *, hold_s: float = 2.0,
                contender_wait_s: float = 1.0) -> Dict[str, Any]:
    work = Path(work or (lab_common.WORK_ROOT / '_combined_fixture'))
    work.mkdir(parents=True, exist_ok=True)
    # Fresh isolated fixture directory and ONE explicit lock file both
    # supervisors are pointed at, as root required.
    lock = work / 'combined.lock'
    active = work / 'sandbox_active.flag'
    ready = work / 'ready.flag'
    for f in (active, ready):
        if f.exists():
            f.unlink()

    holder = subprocess.Popen(
        [sys.executable, '-c',
         _supervisor_source(str(lock), 'holder', str(ready), str(active),
                            hold_s, contender_wait_s)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # TRUSTED readiness: the supervisor process observes the sandbox program's
    # own marker. The contender is not released until the sandboxed payload is
    # demonstrably ACTIVE inside the holder's protected section.
    # The marker lands in the sandbox's OWN run directory (base/p_*/sandbox_active),
    # because that is the only location the Seatbelt profile lets the program
    # write. The supervisor-side poll is the trusted observation.
    sys.path.insert(0, str(LS_DIR))
    import sandbox as _SB
    base = Path(_SB.sandbox_base_dir())
    deadline = time.monotonic() + 30.0
    seen = []
    while not seen and time.monotonic() < deadline:
        if holder.poll() is not None:
            break
        seen = list(base.glob('p_*/sandbox_active'))
        if not seen:
            time.sleep(0.01)
    sandbox_active_observed = bool(seen)
    sandbox_active_at = time.monotonic() if sandbox_active_observed else None

    c = subprocess.run(
        [sys.executable, '-c',
         _supervisor_source(str(lock), 'contender', str(ready), str(work / 'c.flag'),
                            0.1, contender_wait_s)],
        capture_output=True, text=True, timeout=contender_wait_s + 60.0)
    contender = _parse(c.stdout)
    out, err = holder.communicate(timeout=60.0)
    h = _parse(out)
    if h.get('outcome') == 'no_result':
        h['stderr_tail'] = (err or '')[-300:]

    return {
        'schema': FIXTURE_SCHEMA,
        'label': ('SYNTHETIC INTEGRATION CHECK of the combined lock+sandbox route. '
                  'Two independent TRUSTED SUPERVISORS; the lock is held OUTSIDE '
                  'the sandbox and the sandboxed program never references it. NOT '
                  'live model evidence, NOT a general concurrency or security '
                  'theorem.'),
        'topology': 'supervisor acquires lock -> launches sandbox program -> holds '
                    'until it ends -> releases; contender attempts the same lock '
                    'through the same wrapper',
        'lock_identity': lab_common.tokenize_path(lock),
        'same_lock_file_for_both': True,
        'holder': h,
        'contender': contender,
        'holder_sandbox_active_before_contender_tried': sandbox_active_observed,
        'liveness_marker': ('written by the sandboxed program into its OWN run '
                            'directory under the writable sandbox base -- the only '
                            'place the profile permits. An earlier version had it '
                            'write into the fixture work dir and the profile '
                            'correctly DENIED that, which is containment working.'),
        'sandbox_active_observed_monotonic': sandbox_active_at,
        'contender_blocked': contender.get('outcome') == 'blocked',
        'contender_sandbox_never_started': contender.get('sandbox_started') is None,
        'hold_s': hold_s,
        'contender_wait_s': contender_wait_s,
    }
