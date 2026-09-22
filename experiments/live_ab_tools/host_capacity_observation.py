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

#: The process names protocol 5.7.2's presence test is about.
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


def main() -> int:
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

    clear = not consumers and not listeners
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
                      'consumers': consumers,
                      'listeners': listeners,
                      'load': load}, indent=2))
    print('written:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
