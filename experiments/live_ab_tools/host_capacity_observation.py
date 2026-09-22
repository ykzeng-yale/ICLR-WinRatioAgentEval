"""Record a READ-ONLY observation of accelerator occupancy on the trial host.

Protocol 5.7.2 rejects non-baseline foreign accelerator consumers **on presence**,
regardless of CPU percentage. This tool observes that presence and writes down
what it saw. It runs ``ps`` and ``lsof`` and nothing else: **no signal is sent to
any process**, not even one this session started.

WHAT A CLEAN READING IS AND IS NOT
----------------------------------
DTR-AgentEvals, 2026-09-22, correcting me: *"do not infer abandonment from a
no-client snapshot"*. The same caution applies to absence. A reading with no
accelerator consumer present means the gate would pass **at the instant of the
reading**; it is not a guarantee about the next instant and it does not reserve
anything. Any consumer of this receipt must re-observe at its own start.

It is also worth stating what this tool cannot see: a process running inside a VM
(the colima VM on this host), a process owned by another user, and anything that
starts between the ``ps`` call and the ``lsof`` call. The two calls are recorded
with their own timestamps so that window is visible rather than implied.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

# TWO DIFFERENT QUESTIONS, and an earlier version of the pre-build check let one
# masquerade as the other:
#
#   (a) may a TRIAL run?  Protocol 5.7.2: no, if any non-baseline accelerator
#       consumer is PRESENT, regardless of its CPU share.
#   (b) may a BUILD run?  A compile loads no weights and starts no serving
#       experiment, so 5.7.2 does not govern it. What governs it is that a
#       parallel C++ build saturates the cores of a SHARED host, which would
#       degrade a peer's measured block.
#
# Both can refuse, for different reasons, and the reason must be named. A build
# refused "because 5.7.2" would be wrong about its own rule; a build allowed
# "because 5.7.2 does not apply" would ignore the peer it disturbs.

#: The process names protocol 5.7.2's presence test is about.
#:
#: RETAINED ONLY AS THE WEAK SCAN IT IS, for the side-by-side below. The
#: authoritative answer now comes from `lab_hostcheck`, the audited production
#: gate. This tool used to answer 5.7.2 with its own `ps -Ao ...,comm` scan, and
#: I quoted that answer in cycle comments as "the host is clear".
#:
#: TWO DEFECTS, both in the UNDER-detecting direction, which is the dangerous one
#: for a gate that must fail on PRESENCE:
#:
#:   * `comm` is the executable basename only. A consumer launched through a
#:     wrapper -- `python -m something_serving` -- has `comm == python3.12` and is
#:     INVISIBLE. Demonstrated with a live positive control: a child whose command
#:     line named a consumer was detected 1/1 by a command scan and 0/1 by a comm
#:     scan.
#:   * no self-exclusion by PID. A command-based scan without one reports the
#:     OBSERVER as a consumer whenever the pattern appears anywhere on its own
#:     command line -- including in a human-readable label. That is how an ad-hoc
#:     check of mine reported "3 llama-server processes" on a host that had none.
#:
#: `lab_hostcheck` has neither defect: it scans the full command, excludes the
#: caller's own process tree by walking ppid edges (`own_pid_allowlist`), and also
#: detects by OPEN METAL RESOURCE, so it catches a runner renamed to anything.
#: Maintaining a second, weaker detector beside an audited one is how the weaker
#: answer ends up in a report.
CONSUMER_RE = re.compile(r'llama-server|llama\.cpp|mlx|ollama|vllm', re.I)

#: Ports named anywhere in this program's configuration or in the peer project's.
WATCHED_PORTS = (8091, 8092, 8191, 8193)


def _run(cmd: list) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = p.stdout or ''
        err = (p.stderr or '')[:400]
        rc = p.returncode
    except Exception as exc:                                   # noqa: BLE001
        return {'cmd': ' '.join(cmd), 'ok': False, 'at_wall': t0,
                'error': '%s: %s' % (type(exc).__name__, exc)}
    return {'cmd': ' '.join(cmd), 'ok': True, 'at_wall': t0,
            'returncode': rc, 'stdout_lines': len(out.splitlines()),
            'stderr_head': err, '_stdout': out}


def authoritative_scan() -> dict:
    """The AUDITED gate's answer, not this tool's own.

    `lab_hostcheck.preflight_host_quiescent` is the module protocol 5.7.2 is
    implemented in and the one `tests_lab_hostcheck.py` holds to the
    observe-never-signal property. It reports how many processes it scanned and
    how many it allowlisted as the caller's own, so the self-exclusion is
    auditable instead of implicit.
    """
    import lab_hostcheck                                       # noqa: PLC0415
    scan = lab_hostcheck.preflight_host_quiescent()
    return {
        'detector': 'lab_hostcheck.preflight_host_quiescent',
        'findings': list(scan.findings),
        'foreign_consumers_present': bool(scan.findings),
        'degraded': list(scan.degraded),
        'processes_scanned': scan.scanned,
        'own_pids_allowlisted': scan.allowlisted,
        'baseline_processes': [b.get('baseline_id') for b in (scan.baseline or [])],
        'note': ('a DEGRADED scan is not a clean scan: if the detector could not '
                 'read what it needed, absence of findings means absence of '
                 'evidence, not evidence of absence'),
    }


def main() -> int:
    auth = authoritative_scan()

    # The old comm-based scan is kept ONLY to show, in the same receipt, that it
    # can disagree with the audited gate. It never decides anything.
    ps = _run(['ps', '-Ao', 'pid,ppid,etime,rss,comm'])
    consumers = []
    if ps.get('ok'):
        for line in ps.pop('_stdout').splitlines()[1:]:
            if CONSUMER_RE.search(line):
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    consumers.append({'pid': parts[0], 'ppid': parts[1],
                                      'etime': parts[2], 'rss_kb': parts[3],
                                      'comm': parts[4].strip()})
    ps.pop('_stdout', None)

    lsof = _run(['lsof', '-nP', '-iTCP', '-sTCP:LISTEN'])
    listeners = []
    if lsof.get('ok'):
        for line in lsof.pop('_stdout').splitlines():
            for port in WATCHED_PORTS:
                if (':%d' % port) in line:
                    parts = line.split(None, 1)
                    listeners.append({'port': port,
                                      'command': parts[0] if parts else '?',
                                      'line_head': line[:120]})
    lsof.pop('_stdout', None)

    load = None
    try:
        import os
        load = list(os.getloadavg())
    except Exception:                                          # noqa: BLE001
        pass

    # THE VERDICT COMES FROM THE AUDITED GATE. The weak scan is recorded
    # beside it and, when the two disagree, the disagreement is the finding --
    # it is never averaged away or resolved in favour of the cleaner answer.
    clear = (not auth['foreign_consumers_present']
             and not auth['degraded'] and not listeners)
    weak_scan_disagrees = bool(consumers) != auth['foreign_consumers_present']
    receipt = {
        'schema': 'live_ab/host_capacity_observation-v1',
        'observed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'descriptive',
        'protocol': '5.7.2 (presence test)',
        'method': 'ps and lsof only. NO SIGNAL was sent to any process, including '
                  'processes this session started.',
        'accelerator_consumers_present': consumers,
        'watched_ports': list(WATCHED_PORTS),
        'listeners_on_watched_ports': listeners,
        'load_average_1_5_15': load,
        'gate_would_pass_at_this_instant': clear,
        'authoritative_scan': auth,
        'weak_comm_scan_consumers': consumers,
        'weak_scan_disagrees_with_audited_gate': weak_scan_disagrees,
        'which_one_decides': ('lab_hostcheck. The comm-based scan in this file under-detects by construction and is retained only as a comparator.'),
        'what_this_is_not': [
            'NOT a reservation: this reading holds nothing and grants nothing',
            'NOT a guarantee about the next instant -- a consumer may start at any '
            'time, and DTR-AgentEvals correctly warned against inferring '
            'abandonment, or availability, from a snapshot',
            'NOT execution clearance: root clearance is separate and is not granted',
            'BLIND to processes inside the colima VM and to other users\' processes',
        ],
        'measurement_window': {
            'ps': ps, 'lsof': lsof,
            'note': 'two separate calls with their own timestamps; anything starting '
                    'between them is invisible to both, and the gap is recorded '
                    'rather than implied',
        },
    }
    out = lab_common.RESULTS_ROOT / ('HOST_CAPACITY_OBSERVATION_%s.json'
                                     % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({'gate_would_pass_at_this_instant': clear,
                      'audited_findings': len(auth['findings']),
                      'processes_scanned': auth['processes_scanned'],
                      'own_pids_allowlisted': auth['own_pids_allowlisted'],
                      'degraded': auth['degraded'],
                      'weak_scan_disagrees': weak_scan_disagrees,
                      'consumers': consumers,
                      'listeners': listeners,
                      'load': load}, indent=2))
    print('written:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
