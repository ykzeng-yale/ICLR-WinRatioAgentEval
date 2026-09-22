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
                       capture_output=True, text=True, cwd=str(REPO), timeout=120)
    for line in (p.stdout or '').splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return os.environ.get('GITHUB_TOKEN', '')


def probe_once(session, token: str) -> dict:
    # BOTH clocks. The wall clock is what theta is about; the monotonic clock is
    # the only one that measures a DURATION, and it is also how a wall-clock STEP
    # during the run becomes visible. The first version used time.time() for
    # both, so its rtt was a difference of wall readings and a clock step mid-run
    # -- the very thing that invalidates the intersection -- was undetectable.
    t0, m0 = time.time(), time.monotonic()
    res = session.get(API, timeout=30, headers={
        'Authorization': 'Bearer %s' % token,
        'Accept': 'application/vnd.github+json',
        'Cache-Control': 'no-cache'})
    t1, m1 = time.time(), time.monotonic()
    date = res.headers.get('Date')
    if not date:
        return {'ok': False, 'reason': 'no Date header',
                'rtt_monotonic_s': m1 - m0}
    dt = email.utils.parsedate_to_datetime(date)
    if dt.tzinfo is None:
        # parsedate_to_datetime returns a NAIVE datetime for a '-0000' zone, and
        # .timestamp() would then read it as LOCAL time -- a whole UTC-offset
        # shift, silently, with consistent=true. An unlabelled zone is refused.
        return {'ok': False, 'reason': 'Date header has no timezone (-0000); a '
                                       'naive datetime would be read as local time',
                'rtt_monotonic_s': m1 - m0}
    d = dt.timestamp()
    return {
        'ok': res.status_code < 300,
        'status': res.status_code,
        'rtt_monotonic_s': m1 - m0,
        'wall_elapsed_s': t1 - t0,
        'wall_minus_monotonic_elapsed_s': (t1 - t0) - (m1 - m0),
        # theta = server - local, bounded; see the module docstring.
        'theta_lo_s': d - t1,
        'theta_hi_s': d + 1.0 - t0,
    }


def consistent_guard_ok(good) -> bool:
    """Placeholder kept explicit: the consistency verdict is computed below and
    an INCONSISTENT intersection is a nonzero exit, not a normal receipt."""
    return True


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
    if not consistent_guard_ok(good):
        pass
    if len(good) < max(5, n // 2):
        print('too few usable probes (%d of %d)' % (len(good), n), file=sys.stderr)
        return 1

    rtts = sorted(p['rtt_monotonic_s'] for p in good)
    lo = max(p['theta_lo_s'] for p in good)     # intersection of the bounds
    hi = min(p['theta_hi_s'] for p in good)
    consistent = lo <= hi
    # The intersection has BREAKDOWN POINT ZERO: one anomalous Date -- a different
    # edge node, a clock step -- can shrink it to a narrow interval that EXCLUDES
    # the true offset, and nothing in a non-empty result reveals that. So the
    # per-probe intervals are also reported pairwise: if the widest and narrowest
    # single-probe bounds disagree, the constant-offset assumption is in doubt
    # even when the intersection is non-empty.
    per_lo = sorted(p['theta_lo_s'] for p in good)
    per_hi = sorted(p['theta_hi_s'] for p in good)
    lo_spread = per_lo[-1] - per_lo[0]
    hi_spread = per_hi[-1] - per_hi[0]

    def q(vals, p):
        # NEAREST-RANK on the ORDER STATISTICS. The previous
        # round(p*(n-1)) index returns vals[-1] -- the sample MAXIMUM -- for every
        # n <= 11 at p=0.95, and reported it as a p95. A percentile that silently
        # equals the maximum is not a percentile.
        if not vals:
            return None
        import math as _m
        k = max(1, min(len(vals), int(_m.ceil(p * len(vals)))))
        return vals[k - 1]

    receipt = {
        'schema': 'live_ab/anchor_clock_probe-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'protocol': '12.4 item 10 (preparation for), 12.6 item 4 (the number it pins)',
        'convention': 'descriptive',
        'writes_performed': 'No REMOTE write: authenticated GET only, no commit, no '
                            'push, no comment, no branch. This is not the drill. It '
                            'DOES write this receipt into the working tree -- an '
                            'earlier version of this field said "NONE.", which was '
                            'not true of the local tree.',
        'probes': len(probes),
        'usable_probes': len(good),
        'rtt_monotonic_s': {'min': rtts[0], 'median': statistics.median(rtts),
                            'p95': q(rtts, 0.95), 'max': rtts[-1],
                            'n': len(rtts),
                            'p95_equals_max': q(rtts, 0.95) == rtts[-1],
                            'note': 'a true duration on one clock. With n=%d a p95 '
                                    'is the %dth order statistic; state n whenever '
                                    'this number is used.' % (len(rtts),
                                                              max(1, int(0.95 * len(rtts) + 0.999)))},
        'clock_offset_server_minus_local_s': {
            'interval': ([lo, hi] if consistent else None),
            'inverted_bounds_when_inconsistent': (None if consistent else [lo, hi]),
            'width_s': (hi - lo) if consistent else None,
            'consistent': consistent,
            'method': 'per probe, theta in [D - t1, D + 1 - t0] (NTP-style, with '
                      'the 1 s Date flooring inside EACH per-probe bound); the '
                      'reported interval is the INTERSECTION of those bounds, '
                      'which is narrower than 1 s and does NOT contain the quantum',
            'method_correction': 'an earlier version of this field claimed "the 1 s '
                                 'quantum of Date is inside the interval by '
                                 'construction". True of each PER-PROBE bound, '
                                 'false of their intersection, which is what is '
                                 'reported. A reader could have concluded no further '
                                 'quantisation allowance was needed downstream.',
            'assumes': 'theta is CONSTANT across the run and every Date comes from '
                       'one clock. The intersection has breakdown point zero: one '
                       'anomalous probe can yield a narrow, non-empty interval that '
                       'EXCLUDES the true offset, and a non-empty result does not '
                       'reveal it. The per-probe spreads below are the check.',
            'per_probe_lo_spread_s': lo_spread,
            'per_probe_hi_spread_s': hi_spread,
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
            'WHICH_CLOCK': 'this offset is measured against the Date header of '
                           'GitHub\'s HTTP frontend on /rate_limit. created_at is '
                           'stamped by the API/persistence layer. THEY ARE NOT SHOWN '
                           'TO BE THE SAME CLOCK, and no conclusion about the sign of '
                           'created_at minus client time may rest on this offset.',
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
    # A fixed filename let a re-run overwrite an inconsistent first measurement,
    # leaving a clean record and no trace of the anomaly. Every sibling artifact
    # in this directory carries a run id; so does this one now.
    out = lab_common.RESULTS_ROOT / ('ANCHOR_CLOCK_PROBE_%s.json'
                                     % time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({k: receipt[k] for k in
                      ('usable_probes', 'rtt_monotonic_s',
                       'clock_offset_server_minus_local_s')}, indent=2))
    print('written:', out)
    if not consistent:
        print('INCONSISTENT: the intersection is empty (lo %.6f > hi %.6f); the '
              'constant-offset assumption failed and no bound is reported'
              % (lo, hi), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
