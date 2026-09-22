"""Deposit the load-observer receipt.

This tool lives OUTSIDE ``experiments/live_ab/`` on purpose: ``HARNESS_FILES``
globs that directory, and a reporting tool is not part of the pinned harness
(the D8 lesson, when ``freeze_status.py`` took the glob from 26 to 27).

WHAT THE RECEIPT IS EVIDENCE OF. Every number it carries comes from a SCRIPTED
ARRIVAL SERIES -- a fixture, not a server. It demonstrates that the observer's
decision rules do what they claim on inputs whose ground truth is known by
construction. It is NOT evidence about the coder server, about llama.cpp, or
about any real load, and the receipt says so in its own fields so the claim
cannot be separated from the artifact later.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
for p in (str(LAB),):
    if p not in sys.path:
        sys.path.insert(0, p)

import lab_common                                              # noqa: E402
import lab_load                                                # noqa: E402
import lab_prepare                                             # noqa: E402

GAP = lab_load.DEFAULT_MAX_INTERIOR_GAP_S
ATTEMPT = {'interval_schema': lab_prepare.INTERVAL_SCHEMA_V2,
           'verification_started_monotonic': 100.0,
           'verification_ended_monotonic': 100.5}


def dense(gid, t0, t1, step=0.05):
    out, t = [], t0
    while t <= t1 + 1e-9:
        out.append((gid, round(t, 6)))
        t += step
    return out


def probe(n=lab_load.MIN_JITTER_SAMPLES, lateness=0.002):
    p = lab_load.JitterProbe()
    for _ in range(n):
        p.observe_sample(lateness)
    return p


def case(name, script, *, expect_valid, note):
    obs = lab_load.ContinuousLoadObserver(
        lab_load.ScriptedLoad(script), max_interior_gap_s=GAP, jitter=probe())
    with obs:
        o = obs.observe()
    v = lab_prepare._coverage_verdict(o, ATTEMPT)
    return {
        'case': name,
        'note': note,
        'arrivals': len(script),
        'active': o['active'],
        'windows': len(o.get('active_windows') or []),
        'endpoint_error_s': o.get('endpoint_error_s'),
        'max_interior_gap_s_measured': o.get('max_interior_gap_s_measured'),
        'max_interior_gap_s_allowed': o.get('max_interior_gap_s_allowed'),
        'observation_digest': lab_load.observation_digest(o),
        'coverage_valid': v['valid'],
        'coverage_reason': v['reason'],
        'expected_valid': expect_valid,
        'as_expected': bool(v['valid']) == expect_valid,
    }


def main() -> int:
    cases = [
        case('dense_single_generation', dense('g0', 99.0, 102.0),
             expect_valid=True,
             note='one generation producing continuously across the attempt'),
        case('two_concurrent_generations',
             sorted(dense('g0', 99.0, 102.0, 0.1) + dense('g1', 99.05, 102.05, 0.1),
                    key=lambda x: x[1]),
             expect_valid=True,
             note='the trial regime: workers=2, arrivals interleave. An earlier '
                  'version of the splitting rule reported NO LOAD on exactly this '
                  'input -- silently, and in the safe-looking direction.'),
        case('gap_straddling_the_attempt',
             dense('g0', 99.0, 100.1) + dense('g0', 100.8, 102.0),
             expect_valid=False,
             note='0.7 s of unobserved time inside the attempt; the window splits '
                  'and the attempt is NOT covered'),
        case('no_arrivals', [], expect_valid=False,
             note='silence is reported as absence of evidence, not as quiet load'),
    ]
    unmeasured = lab_load.ContinuousLoadObserver(
        lab_load.ScriptedLoad(dense('g0', 99.0, 102.0)),
        max_interior_gap_s=GAP, jitter=probe(n=lab_load.MIN_JITTER_SAMPLES - 1))
    with unmeasured:
        u = unmeasured.observe()
    cases.append({
        'case': 'unmeasured_endpoint_bound',
        'note': 'load present, but fewer than %d probe samples stand behind the '
                'endpoint bound' % lab_load.MIN_JITTER_SAMPLES,
        'arrivals': len(unmeasured.arrivals()),
        'active': u['active'],
        'windows': len(u.get('active_windows') or []),
        'reason': u.get('reason'),
        'expected_valid': False,
        'as_expected': u['active'] is False,
    })

    receipt = {
        'schema': 'live_ab/load_observer_receipt-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'protocol': '3.2 rule 4',
        'module': 'experiments/live_ab/lab_load.py',
        'specification': 'experiments/live_ab/design/SERVING_LOAD_REHEARSAL.md',
        'convention': 'deterministic-path',
        'evidence_is_about': 'a SCRIPTED ARRIVAL SERIES, not a server. These cases '
                             'show the observer decides correctly on inputs whose '
                             'ground truth is known by construction. They are NOT '
                             'evidence about the coder server or about any real load.',
        'real_source_status': {
            'implemented': 'lab_load.StreamingHttpLoad',
            'executed': False,
            'why_not': 'prefreeze model execution requires explicit root review, '
                       'which has not been granted, and the host is treated as '
                       'occupied pending the shared-compute answer.',
        },
        'tolerances_are_pre_registered': False,
        'tolerances': {'max_interior_gap_s': GAP,
                       'endpoint_error_floor_s': lab_load.DEFAULT_ENDPOINT_ERROR_FLOOR_S,
                       'min_jitter_samples': lab_load.MIN_JITTER_SAMPLES},
        'cases': cases,
        'all_cases_as_expected': all(c['as_expected'] for c in cases),
    }
    out = lab_common.RESULTS_ROOT / 'LOAD_OBSERVER_RECEIPT.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({'written': str(out),
                      'all_cases_as_expected': receipt['all_cases_as_expected'],
                      'cases': [(c['case'], c['as_expected']) for c in cases]},
                     indent=2))
    return 0 if receipt['all_cases_as_expected'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
