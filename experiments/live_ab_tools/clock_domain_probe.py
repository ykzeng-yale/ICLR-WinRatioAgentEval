"""Are the server's clock and the verifier's clock the same clock?

Root's binding design choice, 2026-09-22 02:49, requires decoding-slot lifetimes
"recorded by pinned server-side lifecycle start/end events **on the same host
monotonic clock**" as the verifier interval.

That phrase contains an assumption worth testing before anything is built on it.
On this host it is FALSE as written:

* ``llama.cpp``'s ``ggml_time_us()`` reads ``clock_gettime(CLOCK_MONOTONIC)``
  (ggml/src/ggml.c:568-572, the POSIX branch).
* the verifier stamps its attempt endpoints with Python's ``time.monotonic()``
  (lab_data.py:805-813).

On macOS those are two different timelines. ``time.monotonic()`` is
``mach_absolute_time()``, which does NOT advance while the machine is asleep;
``clock_gettime(CLOCK_MONOTONIC)`` does. Their difference is the accumulated
sleep time since boot: it is not zero, it is not a constant of the platform, and
**it grows by an unpredictable amount whenever the machine sleeps** -- including
between a lifecycle event and the verifier interval it is supposed to cover.

This is not a defect in root's decision; it is an unstated precondition of it.
The repair is small and exact -- stamp both ends on ONE named clock -- but it
touches ``lab_data.py``, which is pinned by ``harness_file_sha256``, so it is a
disclosed prefreeze change and root's to authorize.

This tool writes no code and changes nothing. It measures.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LAB = REPO / 'experiments' / 'live_ab'
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import lab_common                                              # noqa: E402

READS = 2000


def _named_clocks() -> dict:
    out = {'time.monotonic': time.monotonic()}
    for name in ('CLOCK_MONOTONIC', 'CLOCK_MONOTONIC_RAW', 'CLOCK_UPTIME_RAW',
                 'CLOCK_BOOTTIME', 'CLOCK_REALTIME'):
        clk = getattr(time, name, None)
        if clk is None:
            continue
        try:
            out['clock_gettime(%s)' % name] = time.clock_gettime(clk)
        except OSError:
            continue
    return out


def main() -> int:
    # The interleaved read establishes that the difference is a real offset
    # between timelines, not a sampling artefact: each CLOCK_MONOTONIC read is
    # bracketed by two time.monotonic() reads, so the bracket width bounds how
    # much of the difference could be elapsed time.
    diffs, brackets = [], []
    for _ in range(READS):
        a = time.monotonic()
        b = time.clock_gettime(time.CLOCK_MONOTONIC)
        c = time.monotonic()
        diffs.append(b - a)
        brackets.append(c - a)
    diffs.sort()
    spread = diffs[-1] - diffs[0]
    max_bracket = max(brackets)

    snapshot = _named_clocks()
    same_domain = abs(diffs[len(diffs) // 2]) <= max_bracket

    receipt = {
        'schema': 'live_ab/clock_domain_probe-v1',
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'convention': 'descriptive',
        'question': "root 2026-09-22 requires server lifecycle events and verifier "
                    "endpoints on 'the same host monotonic clock'. Are the two "
                    "clocks actually in use the same clock?",
        'platform': {'system': platform.system(), 'release': platform.release(),
                     'machine': platform.machine(),
                     'python': platform.python_version()},
        'server_clock': {
            'reader': 'ggml_time_us()',
            'implementation': 'clock_gettime(CLOCK_MONOTONIC)',
            'evidence': 'llama.cpp ggml/src/ggml.c:568-572, POSIX branch',
        },
        'verifier_clock': {
            'reader': 'time.monotonic()',
            'evidence': 'experiments/live_ab/lab_data.py:805-813',
        },
        'reads': READS,
        'difference_clock_gettime_minus_monotonic_s': {
            'min': diffs[0], 'median': diffs[len(diffs) // 2], 'max': diffs[-1],
            'spread_across_reads_s': spread,
        },
        'max_bracket_width_s': max_bracket,
        'bracket_meaning': 'each CLOCK_MONOTONIC read sits between two '
                           'time.monotonic() reads; the bracket bounds how much of '
                           'the difference could be elapsed time rather than offset',
        'same_clock_domain': same_domain,
        'verdict': ('THE TWO CLOCKS ARE THE SAME DOMAIN' if same_domain else
                    'THE TWO CLOCKS ARE DIFFERENT TIMELINES: the median difference '
                    'exceeds the bracket width by orders of magnitude, so it is an '
                    'offset between timelines, not elapsed time.'),
        'why_on_macos': 'time.monotonic() is mach_absolute_time(), which does not '
                        'advance while the machine sleeps; clock_gettime('
                        'CLOCK_MONOTONIC) does. The difference is accumulated sleep '
                        'since boot.',
        'why_it_matters': 'a server-side lifetime [t_start, t_end] in the server '
                          'clock and a verifier interval in time.monotonic() cannot '
                          'be compared at all without a conversion, and the offset '
                          'CHANGES whenever the machine sleeps -- possibly between '
                          'the lifecycle event and the interval it must cover.',
        'clock_snapshot_s': snapshot,
        'proposed_repair': {
            'change': 'stamp the verifier attempt endpoints with '
                      'time.clock_gettime(time.CLOCK_MONOTONIC) -- the same clock '
                      'ggml_time_us() reads -- or record BOTH readings per endpoint.',
            'files_touched': ['experiments/live_ab/lab_data.py'],
            'status': 'NOT APPLIED. lab_data.py is pinned by harness_file_sha256, so '
                      'this is a disclosed prefreeze change and root authorizes it.',
            'recording_both_is_safer': 'recording both costs one extra syscall per '
                                       'endpoint and makes the offset measurable at '
                                       'every attempt instead of assumed once.',
        },
        'what_this_does_not_establish': [
            'that the running server process reads the same clock as the source '
            'says: the binary was not run, connected to or inspected',
            'the size of the offset at any future time; it changes with sleep',
            'anything about a Linux host, where the two readers may well agree',
        ],
    }
    out = lab_common.RESULTS_ROOT / 'CLOCK_DOMAIN_FINDING.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    lab_common.write_json_atomic(out, receipt)
    print(json.dumps({k: receipt[k] for k in
                      ('same_clock_domain', 'verdict',
                       'difference_clock_gettime_minus_monotonic_s',
                       'max_bracket_width_s')}, indent=2))
    print('written:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
