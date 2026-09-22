"""Read-only clock and round-trip characterisation for the anchor drill.

Protocol 12.4 item 10 requires ONE ANCHOR DRILL before the freeze, against the
real remote on a drill branch and the real issue thread, and 12.6 item 4 pins the
number it produces -- ``posting_latency_p95_s``, the second term of the
time-sandwich tolerance ``30 s + posting_latency_p95_s``.

THE DRILL IS A WRITING OPERATION AND THIS TOOL DOES NOT WRITE.  It issues
authenticated GETs only: no commit, no push, no comment, no branch.  What it
establishes is the part of the drill's arithmetic that can be established without
posting anything, and -- more usefully -- what the drill's number can and cannot
mean once it is measured.

WHAT ``posting_latency`` IS, WRITTEN OUT
---------------------------------------
For one anchor: ``L = created_at_server - t_wall_client`` at the moment the
anchor event was logged.  Two properties of that difference decide how it may be
used, and neither is visible in the protocol's one-line definition:

1. **It carries the clock offset.**  ``L`` is a difference between two DIFFERENT
   clocks, so it equals ``true latency + (server clock - local clock)``.  A local
   clock 2 s slow inflates every ``L`` by 2 s; one 2 s fast can make ``L``
   NEGATIVE.  A p95 taken over such values is a p95 of latency-plus-offset.

2. **A constant offset CANCELS in the audit that uses it.**  The sandwich audit
   (12.6 item 4) compares ``Δcreated_at`` against ``Δt_wall`` for CONSECUTIVE
   receipts.  Writing ``created_at_k = t_k + θ + L_k`` gives
   ``Δcreated_at - Δt_wall = L_{k+1} - L_k``: the offset θ disappears.  So the
   quantity the audit is actually sensitive to is the VARIATION of posting
   latency between consecutive anchors, not its level.

Pinning ``p95(L)`` -- the pre-registered definition -- is therefore CONSERVATIVE
when the offset is positive (a larger tolerance, a less sensitive audit) and
ANTI-conservative when it is negative.  This tool measures the offset so the
drill can state which case it is in.  **It does not redefine the pinned
quantity**; the pre-registration says p95 of posting latency and that is root's
to change, not this tool's.

3. **One-second quantisation.**  GitHub's ``created_at`` and the HTTP ``Date``
   header both have ONE SECOND resolution.  Sub-second latency is not resolvable
   from them at all, and any p95 derived from them is quantised to whole seconds.
   The drill's number must be reported with that granularity stated, not as a
   float that implies precision the source does not have.

THE OFFSET BOUND
----------------
With ``t0`` the local clock before the request, ``t1`` after the response, and
``D`` the server's ``Date`` header, the response was generated at some local
instant ``u ∈ [t0, t1]`` whose server time lies in ``[D, D+1)``.  So

    θ = server_clock - local_clock  ∈  [D - t1,  D + 1 - t0]

and the intersection over probes is the tightest interval this method gives.  Its
width is bounded below by the round-trip time plus the 1 s quantum: this is an
NTP-style bound, not a point estimate, and it is reported as an interval.
"""

from __future__ import annotations

import email.utils
import json
import os
import statistics
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

API = 'https://api.github.com/rate_limit'
DEFAULT_PROBES = 20


def _token() -> str:
    """The osxkeychain token, via git credential fill.  Never printed, never stored."""
    p = subprocess.run(['git', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True, cwd=str(REPO))
    for line in (p.stdout or '').splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return os.environ.get('GITHUB_TOKEN', '')


def probe_once(session, token: str) -> dict:
    t0 = time.time()
    res = session.get(API, timeout=30, headers={
        'Authorization': 'Bearer %s' % token,
        'Accept': 'application/vnd.github+json',
        'Cache-Control': 'no-cache'})
    t1 = time.time()
    date = res.headers.get('Date')
    if not date:
        return {'ok': False, 'reason': 'no Date header', 'rtt_s': t1 - t0}
    d = email.utils.parsedate_to_datetime(date).timestamp()
    return {
        'ok': res.status_code < 300,
        'status': res.status_code,
        'rtt_s': t1 - t0,
        # theta = server - local, bounded; see the module docstring.
        'theta_lo_s': d - t1,
        'theta_hi_s': d + 1.0 - t0,
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    n = int(argv[0]) if argv else DEFAULT_PROBES
    import requests

    token = _token()
    if not token:
        print('no token; refusing to report an unmeasured offset', file=sys.stderr)
        return 2

    session = requests.Session()
    probes = []
    for _ in range(n):
        try:
            probes.append(probe_once(session, token))
        except Exception as exc:                               # noqa: BLE001
            probes.append({'ok': False, 'reason': '%s: %s' % (type(exc).__name__, exc)})
        time.sleep(0.25)

    good = [p for p in probes if p.get('ok')]
    if len(good) < max(5, n // 2):
        print('too few usable probes (%d of %d)' % (len(good), n), file=sys.stderr)
        return 1

    rtts = sorted(p['rtt_s'] for p in good)
    lo = max(p['theta_lo_s'] for p in good)     # intersection of the bounds
    hi = min(p['theta_hi_s'] for p in good)
    consistent = lo <= hi

    def q(vals, p):
        i = min(len(vals) - 1, max(0, int(round(p * (len(vals) - 1)))))
        return vals[i]

    receipt = {
        'schema': 'live_ab/anchor_clock_probe-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'protocol': '12.4 item 10 (preparation for), 12.6 item 4 (the number it pins)',
        'convention': 'descriptive',
        'writes_performed': 'NONE. Authenticated GET only: no commit, no push, no '
                            'comment, no branch. This is not the drill.',
        'probes': len(probes),
        'usable_probes': len(good),
        'rtt_s': {'min': rtts[0], 'median': statistics.median(rtts),
                  'p95': q(rtts, 0.95), 'max': rtts[-1]},
        'clock_offset_server_minus_local_s': {
            'interval': [lo, hi],
            'width_s': (hi - lo) if consistent else None,
            'consistent': consistent,
            'method': 'NTP-style bound from the HTTP Date header; the 1 s quantum of '
                      'Date is inside the interval by construction',
            'note': 'an INTERVAL, not a point estimate. A point estimate here would '
                    'claim a resolution the 1 s Date header does not have.',
        },
        'consequences_for_the_drill': {
            'posting_latency_carries_this_offset': True,
            'offset_cancels_in_the_sandwich_difference': True,
            'created_at_resolution_s': 1,
            'implication': 'p95 of (created_at - t_wall) is a p95 of latency PLUS '
                           'offset, quantised to whole seconds. The sandwich audit '
                           'compares DIFFERENCES of consecutive receipts, in which a '
                           'constant offset cancels, so the audit is sensitive to the '
                           'VARIATION of posting latency, not its level.',
            'not_redefined_here': 'the pre-registration pins p95 of posting latency; '
                                  'changing that definition is root\'s call, not this '
                                  'tool\'s. The drill will report both p95(L) and '
                                  'p95(|L_k+1 - L_k|) so either can be assessed.',
        },
        'what_this_does_not_establish': [
            'any posting latency: no write was performed',
            'identifier-leak hygiene: that needs the real remote and the real issue '
            'thread (12.4 item 10), because a throwaway repository lacks the real '
            'account and repository names',
            'that GitHub latency at drill time resembles latency now',
        ],
    }
    out = lab_common.RESULTS_ROOT / 'ANCHOR_CLOCK_PROBE.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({k: receipt[k] for k in
                      ('usable_probes', 'rtt_s', 'clock_offset_server_minus_local_s')},
                     indent=2))
    print('written:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
