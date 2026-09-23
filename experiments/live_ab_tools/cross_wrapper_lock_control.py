"""Do the TWO different lock wrappers actually exclude each other?

Root, `reviews/lock_anchor_review_20260923_0348.md`:

    "Two different Python wrappers are not inherently a problem when they hold
     the same physical file with `flock` for the whole creation/execution/deletion
     interval. ... The next bounded owner evidence should show one canonical
     resolved path across T1-T4, sweep, containment and worker fallback and
     across two different checkout work roots, followed by a two-process
     lock-only positive/negative control using THE ACTUAL WRAPPER PATHS."

WHY THIS IS NOT THE FIXTURE I ALREADY HAVE. `TWO_WORKER_CONTAINMENT_*` used
`lab_data._ExecutionLock` for BOTH the holder and the contender. It therefore
showed one wrapper excluding itself. The production worker uses a DIFFERENT class
-- `lab_worker.ExecutionLock`, different poll interval, different clock,
different exception, and a `_LOCK_DEPTH` global the other does not have. Whether
those two exclude EACH OTHER on the canonical inode is the property root's ruling
turns on, and nothing had tested it.

FOUR CASES, and the negative ones are the point:

  holder            contender         expected
  lab_data          lab_worker        REFUSED   (cross-wrapper exclusion)
  lab_worker        lab_data          REFUSED   (and in the other direction)
  lab_data          lab_worker        ACQUIRES  when nobody holds  <- control
  lab_worker        lab_data          ACQUIRES  when nobody holds  <- control

Without the two controls a refusal proves nothing: a stale lock, a permissions
fault or a bug in this harness would look identical to exclusion.

LOCK ONLY. No model, no server, no sandboxed program, no episode, no generated
benchmark. Each contender opens the canonical file, asks for `LOCK_EX | LOCK_NB`
through its real wrapper, and reports.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AUDIT_ROLE = 'reporter'

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'live_ab'
if str(LAB) not in sys.path:                                   # pragma: no cover
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

REPO = HERE.parents[1]

#: Each wrapper driven through its OWN constructor and exception, so the witness
#: exercises production code rather than a reimplementation of it.
CHILD = '''\
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, %(lab)r)
import lab_common

LOCK = Path(%(lock)r)
WRAPPER = %(wrapper)r
WAIT = %(wait)r
SIGNAL = %(signal)r
OUT = Path(%(out)r)
HOLD = %(hold)r

rec = {"pid": os.getpid(), "wrapper": WRAPPER, "lock": str(LOCK), "wait_s": WAIT}

if WRAPPER == "lab_data":
    import lab_data
    ctx = lab_data._ExecutionLock(LOCK, WAIT)
    refusal = lab_common.PreflightError
else:
    import lab_worker
    ctx = lab_worker.ExecutionLock(LOCK, max_lock_wait_s=WAIT)
    refusal = lab_worker.LockWaitExceeded

if not HOLD:
    deadline = time.time() + 30.0
    while SIGNAL and not os.path.exists(SIGNAL):
        if time.time() > deadline:
            rec["error"] = "holder never signalled"
            OUT.write_text(json.dumps(rec)); raise SystemExit(3)
        time.sleep(0.01)

rec["t_start_epoch"] = time.time()
try:
    with ctx:
        rec["acquired"] = True
        rec["t_acquired_epoch"] = time.time()
        if HOLD:
            Path(SIGNAL).write_text("held")
            # bounded: release once the contender has written, or on timeout
            d = time.time() + 30.0
            while not os.path.exists(%(peer_out)r) and time.time() < d:
                time.sleep(0.02)
        rec["t_release_epoch"] = time.time()
except refusal as exc:
    rec["acquired"] = False
    rec["refusal_type"] = type(exc).__name__
    rec["refusal_message"] = str(exc)[:200]
except BaseException as exc:
    rec["acquired"] = False
    rec["unexpected_exception"] = "%%s: %%s" %% (type(exc).__name__, exc)
rec["t_end_epoch"] = time.time()
rec["elapsed_s"] = rec["t_end_epoch"] - rec["t_start_epoch"]
OUT.write_text(json.dumps(rec))
'''


def _spawn(work: Path, tag: str, wrapper: str, lock: Path, wait: float,
           signal: Path, peer_out: Path, hold: bool):
    out = work / ('%s.json' % tag)
    prog = work / ('%s.py' % tag)
    prog.write_text(CHILD % {'lab': str(LAB), 'lock': str(lock),
                             'wrapper': wrapper, 'wait': float(wait),
                             'signal': str(signal), 'out': str(out),
                             'peer_out': str(peer_out), 'hold': bool(hold)},
                    encoding='utf-8')
    return subprocess.Popen([sys.executable, str(prog)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True), out


def _one(work: Path, lock: Path, holder: str, contender: str, wait: float,
         *, with_holder: bool) -> Dict[str, Any]:
    tag = '%s_%s_%s' % (holder, contender, 'held' if with_holder else 'free')
    signal = work / ('%s.signal' % tag)
    c_out = work / ('%s_contender.json' % tag)
    procs = []
    h_out = None
    if with_holder:
        hp, h_out = _spawn(work, '%s_holder' % tag, holder, lock, 5.0, signal,
                           c_out, hold=True)
        procs.append(hp)
        deadline = time.time() + 30.0
        while not signal.exists() and time.time() < deadline:
            time.sleep(0.01)
    else:
        signal.write_text('no holder')
    cp, c_out2 = _spawn(work, '%s_contender' % tag, contender, lock, wait,
                        signal, c_out, hold=False)
    # the contender writes to <tag>_contender.json; keep the holder waiting on it
    procs.append(cp)
    for p in procs:
        try:
            p.wait(timeout=90)
        except subprocess.TimeoutExpired:                       # pragma: no cover
            p.kill()
    row: Dict[str, Any] = {
        'holder_wrapper': holder if with_holder else None,
        'contender_wrapper': contender,
        'holder_present': with_holder,
        'contender': json.loads(c_out2.read_text('utf-8')) if c_out2.exists()
        else {'error': 'no contender record'},
    }
    if h_out is not None and h_out.exists():
        row['holder'] = json.loads(h_out.read_text('utf-8'))
    acquired = row['contender'].get('acquired')
    row['expected_acquired'] = not with_holder
    row['as_expected'] = (acquired == (not with_holder))
    return row


def run(contender_wait_s: float = 2.0) -> Dict[str, Any]:
    cfg = lab_common.harness_config()
    lock = lab_common.canonical_execution_lock(cfg)
    lab_common.assert_canonical_execution_lock(
        lock, cfg, stage='cross_wrapper_lock_control')
    work = Path(lab_common.WORK_ROOT) / '_cross_wrapper' / ('cw_%d' % int(time.time()))
    work.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for holder, contender in (('lab_data', 'lab_worker'),
                              ('lab_worker', 'lab_data')):
        rows.append(_one(work, lock, holder, contender, contender_wait_s,
                         with_holder=True))
        rows.append(_one(work, lock, holder, contender, contender_wait_s,
                         with_holder=False))

    exclusions = [r for r in rows if r['holder_present']]
    controls = [r for r in rows if not r['holder_present']]
    return {
        'schema': 'live_ab/cross_wrapper_lock_control-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'authority': ('root, reviews/lock_anchor_review_20260923_0348.md: "a '
                      'two-process lock-only positive/negative control using the '
                      'actual wrapper paths"'),
        'canonical_lock': lab_common.display_path(lock),
        'cases': rows,
        'cross_wrapper_exclusions_observed': sum(
            1 for r in exclusions if r['contender'].get('acquired') is False),
        'cross_wrapper_exclusions_expected': len(exclusions),
        'controls_acquired': sum(
            1 for r in controls if r['contender'].get('acquired') is True),
        'controls_expected': len(controls),
        'all_as_expected': all(r['as_expected'] for r in rows),
        'what_this_adds': (
            'the existing TWO_WORKER_CONTAINMENT fixture used lab_data for BOTH '
            'sides, so it showed one wrapper excluding itself. This shows the two '
            'DIFFERENT production wrappers excluding each other on the canonical '
            'inode, in both orders.'),
        'what_this_does_not_establish': [
            'anything about sandboxed program containment -- this is lock only',
            'exclusion for arbitrary interleavings: two processes, one hold each',
            'that legacy launchers bypassing the lock are excluded; root leaves '
            'those to the capacity/ownership checks',
        ],
        'nothing_executed': ['no model', 'no server', 'no sandboxed program',
                             'no episode', 'lock acquisition only'],
        'work_dir': lab_common.display_path(work),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path,
                    default=Path(lab_common.RESULTS_ROOT) / 'CROSS_WRAPPER_LOCK_CONTROL.json')
    a = ap.parse_args(argv)
    r = run()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, r)
    print('canonical lock:', r['canonical_lock'])
    for row in r['cases']:
        c = row['contender']
        print('  %-9s holds -> %-9s contends : acquired=%-5s %-18s expected=%-5s %s'
              % (row['holder_wrapper'] or 'nobody', row['contender_wrapper'],
                 c.get('acquired'), c.get('refusal_type') or '',
                 row['expected_acquired'], 'ok' if row['as_expected'] else 'MISMATCH'))
    print('\ncross-wrapper exclusions %d/%d | controls acquired %d/%d | all_as_expected=%s'
          % (r['cross_wrapper_exclusions_observed'], r['cross_wrapper_exclusions_expected'],
             r['controls_acquired'], r['controls_expected'], r['all_as_expected']))
    print('written:', a.out)
    return 0 if r['all_as_expected'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
