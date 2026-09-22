"""WHICH lock file does each execution path actually take?

Protocol 5.7 is titled "Sandbox under two workers: the host-wide execution lock",
and item 1 is explicit:

    "Each worker wraps `sandbox.run_program` ... in an exclusive `flock` on ONE
     LOCK FILE. At most one generated program exists and runs at any instant,
     exactly as in the audited regime."

The hazard it exists for is stated one paragraph above it: the Seatbelt profile is
allow-default with "one writable directory SHARED BY EVERY RUN ON THE HOST", and
during a verification that directory holds the hidden tests and the nonce sentinel
in clear text. So the property is a property OF THE HOST, not of a trial.

WHY THIS TOOL EXISTS
--------------------
`tool_audit.py` flagged `lab_worker.py` for calling `fcntl.flock` directly while
`lab_data` provides `_ExecutionLock`. Reading it found not one lock but TWO
implementations, and then -- the part that matters -- two different lock FILES.

This tool resolves the paths the way production resolves them and reports them
side by side. It asserts nothing about what the paths should be: that is a design
decision about protocol conformance, and it belongs to the root.

NOTHING IS EXECUTED. No lock is taken, no worker is started, no sandbox runs. It
resolves paths and compares strings.
"""

from __future__ import annotations

import argparse
import json
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

#: The trials the design names. Two are enough to show whether the path is
#: per-trial, but the whole set is resolved so the report is not an extrapolation
#: from a sample of one.
TRIALS = ('T1', 'T2', 'T3', 'T4')


def _workers_share_a_lock() -> Dict[str, Any]:
    """Do BOTH workers of one trial receive the same lock path? Read the source.

    It cannot be measured by resolving paths -- resolving the same trial twice
    trivially returns the same string and measures nothing. The real content is
    STRUCTURAL: the orchestrator builds one `TrialPaths` per trial and the job
    payload each worker receives reads `sandbox_lock` off that one object, so two
    workers cannot get different values. That is checkable, and it has a real
    failure mode: were the payload to derive the lock per worker, this goes False.
    """
    import ast as _ast                                         # noqa: PLC0415
    import inspect                                             # noqa: PLC0415
    import lab_orchestrator                                    # noqa: PLC0415

    src = inspect.getsource(lab_orchestrator)
    tree = _ast.parse(src)
    exprs = []
    for n in _ast.walk(tree):
        if not isinstance(n, _ast.Dict):
            continue
        for k, v in zip(n.keys, n.values):
            if isinstance(k, _ast.Constant) and k.value == 'sandbox_lock':
                exprs.append(_ast.unparse(v))
    from_trial_paths = bool(exprs) and all('paths.sandbox_lock' in e for e in exprs)
    per_trial_calls = sum(
        1 for n in _ast.walk(tree)
        if isinstance(n, _ast.Call) and getattr(n.func, 'id', None) == '_trial_paths')
    return {
        'two_workers_in_one_trial_share_a_lock': from_trial_paths,
        'job_payload_sandbox_lock_expressions': sorted(set(exprs)),
        'all_derive_from_trial_paths': from_trial_paths,
        'trial_paths_call_sites_in_orchestrator': per_trial_calls,
        'why_this_is_the_measurement': (
            'resolving the same trial twice returns the same string and measures '
            'nothing. What makes the two workers share a lock is that the job '
            'payload reads it off ONE TrialPaths per trial -- a structural fact '
            'with a real failure mode.'),
    }


def resolve() -> Dict[str, Any]:
    import lab_orchestrator                                    # noqa: PLC0415

    cfg = json.loads((LAB / 'config.json').read_text('utf-8'))
    sandbox_cfg = cfg.get('sandbox') or {}

    # (a) the path lab_data's reference sweep takes -- lab_data.py:941
    sweep_lock = Path(sandbox_cfg.get('execution_lock_path')
                      or (lab_common.WORK_ROOT / 'sandbox.lock'))

    # (b) the path the orchestrator hands each worker -- lab_orchestrator._trial_paths
    worker_locks = {}
    for trial in TRIALS:
        tp = lab_orchestrator._trial_paths(trial, Path(lab_common.RESULTS_ROOT),
                                           Path(lab_common.WORK_ROOT))
        worker_locks[trial] = Path(tp.sandbox_lock)

    # (c) the worker's own fallback when a job carries no path -- lab_worker main()
    fallback = {t: Path(lab_common.trial_paths(t).sandbox_lock) for t in TRIALS}

    distinct = sorted({str(sweep_lock)} | {str(p) for p in worker_locks.values()})
    per_trial = len({str(p) for p in worker_locks.values()}) == len(TRIALS)

    return {
        'reference_sweep_lock': lab_common.tokenize_path(sweep_lock),
        'worker_lock_by_trial': {t: lab_common.tokenize_path(p)
                                 for t, p in worker_locks.items()},
        'worker_fallback_matches_orchestrator': {
            t: str(fallback[t]) == str(worker_locks[t]) for t in TRIALS},
        'config_execution_lock_path': sandbox_cfg.get('execution_lock_path'),
        'distinct_lock_files': distinct,
        'distinct_lock_file_count': len(distinct),
        'worker_lock_is_per_trial': per_trial,
        'sweep_and_worker_share_a_lock': any(
            str(sweep_lock) == str(p) for p in worker_locks.values()),
        # MEASURED, not asserted. This field was a hard-coded `True` with a
        # reason string beside it -- my own code, flagged by tool_audit's
        # literal-check detector in the cycle after I wrote it. The reason was
        # correct; the field still claimed a check that never ran.
        **_workers_share_a_lock(),
    }


def implementations() -> List[Dict[str, Any]]:
    """The two `flock` wrappers, and how they differ where it is observable."""
    import inspect                                             # noqa: PLC0415
    import lab_data                                            # noqa: PLC0415
    import lab_worker                                          # noqa: PLC0415

    out = []
    for label, cls in (('lab_data._ExecutionLock', lab_data._ExecutionLock),
                       ('lab_worker.ExecutionLock', lab_worker.ExecutionLock)):
        src = inspect.getsource(cls)
        out.append({
            'implementation': label,
            'wait_parameter': ('max_wait_s' if 'max_wait_s' in src
                               else 'max_lock_wait_s'),
            'poll_sleep_s': next((s for s in ('0.05', '0.01') if 'sleep(%s)' % s in src),
                                 'unknown'),
            'clock': 'time.monotonic' if 'monotonic' in src else 'time.perf_counter',
            'raises': ('PreflightError' if 'PreflightError' in src
                       else 'LockWaitExceeded'),
            'tracks_depth_global': '_LOCK_DEPTH' in src,
        })
    return out


def report() -> Dict[str, Any]:
    paths = resolve()
    impls = implementations()
    conforms = (paths['distinct_lock_file_count'] == 1)
    return {
        'schema': 'live_ab/lock_topology-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'deterministic-path',
        'protocol_requirement': (
            'protocol 5.7 item 1: an exclusive flock on ONE LOCK FILE; "at most '
            'one generated program exists and runs at any instant". The hazard it '
            'addresses is a Seatbelt writable directory SHARED BY EVERY RUN ON '
            'THE HOST, so the property is host-wide, not per-trial.'),
        'paths': paths,
        'implementations': impls,
        'implementation_count': len(impls),
        'conforms_to_one_lock_file': conforms,
        'finding': (None if conforms else {
            'what': ('production resolves %d distinct lock files, not one'
                     % paths['distinct_lock_file_count']),
            'covered': ('the two workers WITHIN a trial: they share the trial lock, '
                        'which is the case 5.7 is titled for'),
            'not_covered': [
                'two trials running concurrently -- different lock files',
                'a reference sweep and an episode worker -- different lock files',
            ],
            'why_it_matters': (
                'the shared writable sandbox base is /private/tmp/labsbx/ls_sbx for '
                'EVERY run on the host regardless of trial, and during verification '
                'it holds hidden tests and the nonce sentinel in clear text. A lock '
                'that is not host-wide does not exclude the reader 5.7 names.'),
            'has_it_bitten': (
                'NO. 0 trial episodes and 0 calibration episodes have ever run, so '
                'nothing has been corrupted. This is latent, not manifested.'),
            'decision_is_roots': (
                'pointing every path at one host-wide lock file changes a '
                'production lock path, which is a protocol-conformance change. It '
                'is not made here.'),
        }),
        'corrects_my_own_claim': {
            'where': ('issue #11 comment of 2026-09-22 12:25, on the two-worker '
                      'containment fixture'),
            'i_said': ('"a real second process contends for the PRODUCTION lock '
                       '<WORK>/sandbox.lock"'),
            'what_is_true': (
                'that is the lock `lab_data` and `lab_containment` take, and the '
                'fixture is valid evidence for it. It is NOT the lock an episode '
                'worker takes: the worker uses a DIFFERENT CLASS '
                '(lab_worker.ExecutionLock) on a DIFFERENT FILE '
                '(<WORK>/<trial>/sandbox.lock). Saying "the production lock" '
                'implied a single lock, and there is more than one.'),
            'what_the_fixture_still_shows': (
                'exclusion on the reference-sweep/containment lock, with its '
                'controls. Nothing in it is withdrawn; its SCOPE is narrower than '
                'my sentence implied.'),
        },
        'nothing_executed': ['no lock taken', 'no worker started', 'no sandbox run',
                             'no production path changed'],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path,
                    default=Path(lab_common.RESULTS_ROOT) / 'LOCK_TOPOLOGY.json')
    a = ap.parse_args(argv)
    r = report()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(a.out, r)
    p = r['paths']
    print('protocol 5.7 item 1 requires ONE lock file.')
    print('  reference sweep          :', p['reference_sweep_lock'])
    for t, v in p['worker_lock_by_trial'].items():
        print('  worker, trial %-3s        : %s' % (t, v))
    print('  distinct lock files      :', p['distinct_lock_file_count'])
    print('  conforms                 :', r['conforms_to_one_lock_file'])
    print('\nimplementations:')
    for i in r['implementations']:
        print('  %-26s poll=%-5s clock=%-18s raises=%s depth=%s'
              % (i['implementation'], i['poll_sleep_s'], i['clock'],
                 i['raises'], i['tracks_depth_global']))
    print('\nwritten:', a.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
