"""Run the two-worker exclusion fixture and deposit its receipt.

The fixture itself lives in `experiments/live_ab/lab_containment.py`, beside the
probe it completes. This runner is deliberately OUTSIDE that directory:
`lab_common.HARNESS_FILES` is a glob over `experiments/live_ab/*.py` and feeds
`harness_file_sha256`, a freeze-bundle key. A reporting tool that sat there would
move a freeze pin every time I improved it.

It sets the PRESCRIBED TMPDIR before anything imports the sandbox. Exporting the
environment variable alone is not enough in-process -- `tempfile` caches
`tempfile.tempdir` on first use -- so both are set, the variable for the child
processes and the module attribute for this one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
LS = HERE.parent / 'local_stream'
for _p in (str(LAB), str(LS)):
    if _p not in sys.path:                                     # pragma: no cover
        sys.path.insert(0, _p)

import lab_common                                              # noqa: E402

REPO = HERE.parents[1]


def _use_prescribed_tmpdir() -> str:
    cfg = json.loads((LAB / 'config.json').read_text('utf-8'))
    want = lab_common.prescribed_tmpdir(cfg)
    os.makedirs(want, exist_ok=True)
    os.environ['TMPDIR'] = want          # for the child processes
    tempfile.tempdir = want              # for this process; the env var is cached
    effective = os.path.realpath(tempfile.gettempdir())
    if effective != os.path.realpath(want):
        raise SystemExit('REFUSE: TMPDIR is %s, prescribed %s' % (effective, want))
    return want


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--contender-wait-s', type=float, default=2.0)
    ap.add_argument('--out', type=Path, default=None)
    a = ap.parse_args(argv)

    _use_prescribed_tmpdir()
    import lab_containment                                     # noqa: PLC0415

    started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    result = lab_containment.run_two_worker(contender_wait_s=a.contender_wait_s)
    result['generated_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    result['started_utc'] = started
    result['convention'] = 'deterministic-path'
    result['authority'] = ('root, in the CORRECTION attached to '
                           'results/live_ab/CONTAINMENT_PROBE_RECEIPT.json: the '
                           'two-worker fixture with an ACTUAL contender blocked, '
                           'plus per-attempt negative-control evidence')
    result['loaded_a_model'] = False
    result['started_a_server'] = False
    result['is_a_trial_episode'] = False

    out = a.out or (Path(lab_common.RESULTS_ROOT)
                    / ('TWO_WORKER_CONTAINMENT_%s.json'
                       % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())))
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, result)

    print('verdict:', result['verdict'])
    for k, v in sorted(result['limbs'].items()):
        print('  %-48s %s' % (k, v))
    c = result['contender_blocked']
    print('\ncontender: acquired=%s refusal=%s after %.3f s'
          % (c.get('acquired'), c.get('refusal_type'), c.get('elapsed_s') or -1))
    ac = result['attempt_containment']
    print('hold %.3f s; attempt started %.3f s after acquire, ended %.3f s before release'
          % (result['holder']['held_s'], ac['margin_before_s'] or -1,
             ac['margin_after_s'] or -1))
    p = result['per_attempt_control']
    print('per-attempt control: %d paired, %d controlled denials, %d denied in both, '
          '%d reachable inside' % (p['attempts_paired'], p['controlled_denials'],
                                   p['denied_in_both'], p['reachable_inside_sandbox']))
    print('lock control (nobody holding) acquired:', result['lock_control_acquired'])
    print('written:', out)
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
