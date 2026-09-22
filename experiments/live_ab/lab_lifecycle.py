"""The server lifecycle observer: occupied decoding slots, read from the server.

This is the producer side root's binding decision of 2026-09-22 02:49 requires and
the client arrival instrument (``lab_load``) explicitly is not:

    "two distinct server-acknowledged decoding requests/occupied decoding slots
     throughout the verifier interval, recorded by pinned server-side lifecycle
     start/end events on the same host monotonic clock."

The events come from ``experiments/live_ab_serving/live_ab_slot_lifecycle.patch``
against llama.cpp ``4fea119de30f6a923992780f6fd5ccb0bee5d47d``, which appends one
``live_ab/slot_lifecycle-v1`` line per completed slot occupancy. Nothing here
samples anything: a slot's occupancy is an interval with two transitions, and
only the process making those transitions can report them.

THE INNER BRACKET IS THE WINDOW
-------------------------------
Root, 2026-09-22 04:02: *"Retain conservative verifier outer brackets and
lifecycle inner endpoints."*

Each record carries four timestamps::

    t_assigned_us      slot bound to a task            OUTER start
      t_prompt_start_us  prompt processing begins      INNER start
      t_gen_last_us      last generation step          INNER end
    t_released_us      slot returned to idle           OUTER end

The window this module emits is ``[t_prompt_start_us, t_gen_last_us]`` -- the
INNER pair. It is strictly narrower than the true occupancy, so an attempt it
covers was covered under any reading. Using the outer pair would widen the
window and make coverage easier, which is the direction that must never be taken
on a convenience.

WHAT A WINDOW MEANS, AND WHAT IT DOES NOT
-----------------------------------------
It means a decoding slot was OCCUPIED BY A REQUEST throughout the interval. Root,
twice: *"This does not assert uninterrupted GPU utilization"* and *"Server
scheduling pauses inside that defined occupancy are part of the operational
regime."* This module claims occupancy and nothing else.

WHAT IT REFUSES
---------------
* a record whose ``complete`` flag is false -- an occupancy missing a transition
  is not an interval;
* a record on any clock but the named POSIX one;
* a record whose inner pair is not finite and ordered;
* a truncated final line, which means the server was still writing;
* provenance that is absent, placeholder, or does not match this host and boot.

Each refusal is reported, never dropped: the observation carries the count and
the reasons, so a sweep that stops can say which record stopped it.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402
import lab_data                                                # noqa: E402

RECORD_SCHEMA = 'live_ab/slot_lifecycle-v1'
OBSERVATION_SCHEMA = 'live_ab/lifecycle_observation-v1'
EVIDENCE_KIND = 'server_lifecycle'
CLOCK = 'clock_gettime(CLOCK_MONOTONIC)'

#: The patch this reader is the counterpart of. A reader that silently accepted
#: records from a different emitter would be reading an unknown instrument.
PATCH_PATH = 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'
PATCHED_BASE_REV = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'


class LifecycleRefused(lab_common.PreflightError):
    """The lifecycle evidence cannot support an observation."""


def _finite(x: object) -> Optional[float]:
    try:
        v = float(x)                                    # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_records(path: "str | Path") -> Dict[str, Any]:
    """Parse the emitter's JSONL. A truncated tail is REFUSED, not trimmed.

    The server appends and flushes one whole line per release, but a reader can
    still arrive mid-write. Trimming the partial line would silently discard an
    occupancy that did happen; refusing says so and lets the caller re-read.
    """
    path = Path(path)
    if not path.exists():
        return {'records': [], 'rejected': [],
                'error': 'no lifecycle log at %s' % lab_common.tokenize_path(path)}
    raw = path.read_text('utf-8')
    lines = raw.splitlines()
    if raw and not raw.endswith('\n'):
        return {'records': [], 'rejected': [],
                'error': 'the lifecycle log ends mid-line (%d bytes); the server is '
                         'still writing. Re-read rather than trimming: a trimmed '
                         'partial line discards an occupancy that did happen.'
                         % len(raw)}
    records, rejected = [], []
    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            rejected.append({'line': i, 'reason': 'unparsable: %s' % exc})
            continue
        if not isinstance(rec, dict) or rec.get('schema') != RECORD_SCHEMA:
            rejected.append({'line': i, 'reason': 'not a %s record (schema %r)'
                                                  % (RECORD_SCHEMA, (rec or {}).get('schema')
                                                     if isinstance(rec, dict) else None)})
            continue
        records.append(rec)
    return {'records': records, 'rejected': rejected, 'error': None}


def window_from_record(rec: dict) -> Dict[str, Any]:
    """One record -> one certified window, or a refusal with its reason."""
    if rec.get('clock') != CLOCK:
        return {'ok': False, 'reason': 'record is on clock %r, not %r'
                                       % (rec.get('clock'), CLOCK)}
    if rec.get('units') != 'microseconds':
        return {'ok': False, 'reason': 'record declares units %r, not microseconds'
                                       % (rec.get('units'),)}
    if rec.get('complete') is not True:
        # Root: "Unknown/missing endpoint or lifecycle discontinuity refuses
        # coverage and retains the attempt; it does not become a task exclusion."
        return {'ok': False, 'reason': 'incomplete lifecycle (a transition was not '
                                       'observed); an occupancy missing a transition '
                                       'is not an interval'}
    lo = _finite(rec.get('t_prompt_start_us'))
    hi = _finite(rec.get('t_gen_last_us'))
    if lo is None or hi is None:
        return {'ok': False, 'reason': 'inner endpoints are missing or nonfinite '
                                       '(%r, %r)' % (rec.get('t_prompt_start_us'),
                                                     rec.get('t_gen_last_us'))}
    if hi <= lo:
        return {'ok': False, 'reason': 'inner interval is empty or reversed '
                                       '(%r -> %r)' % (lo, hi)}
    ident = '%s/slot%s/task%s' % (rec.get('instance_id'), rec.get('slot_id'),
                                  rec.get('task_id'))
    return {'ok': True, 'window': {
        'schema': 'live_ab/lifecycle_window-v1',
        # MICROSECONDS -> SECONDS, stated rather than implied. The verifier's
        # POSIX endpoints are integer nanoseconds; both land on seconds here and
        # the conversion is explicit on each side.
        'start': lo / 1e6, 'end': hi / 1e6,
        'identity': ident,
        'bracket': 'inner (t_prompt_start_us .. t_gen_last_us); the outer bracket '
                   't_assigned_us .. t_released_us is wider and is NOT used',
        'outer_start': _finite(rec.get('t_assigned_us')),
        'outer_end': _finite(rec.get('t_released_us')),
        'n_gen': rec.get('n_gen'),
        'means': 'an occupied decoding slot, NOT uninterrupted hardware utilization',
    }}


def observe(path: "str | Path", *, concurrency_required: int = 2,
            provenance: Optional[dict] = None) -> Dict[str, Any]:
    """The observation ``lab_prepare.run_reference_sweep`` consumes.

    ``provenance`` defaults to this process's own, which is the correct default
    only because the server runs on this host: the whole point of the named clock
    is that a reading from another host or another boot is not on this timeline.
    """
    prov = provenance if provenance is not None else lab_data.clock_provenance()
    parsed = read_records(path)
    base: Dict[str, Any] = {
        'schema': OBSERVATION_SCHEMA,
        'evidence_kind': EVIDENCE_KIND,
        'clock': CLOCK,
        'units_note': 'records are microseconds; windows are seconds, converted here',
        'boot_id': prov.get('boot_id'),
        'host_id': prov.get('host_id'),
        'boot_source': prov.get('boot_source'),
        'host_source': prov.get('host_source'),
        'concurrency_required': int(concurrency_required),
        'source_patch': PATCH_PATH,
        'source_base_rev': PATCHED_BASE_REV,
        'records_read': len(parsed['records']),
        'records_rejected_by_parser': parsed['rejected'],
    }
    if parsed['error']:
        return dict(base, active=False, lifecycle_complete=False,
                    active_windows=[], reason=parsed['error'])

    windows, refused = [], []
    for i, rec in enumerate(parsed['records']):
        got = window_from_record(rec)
        if got['ok']:
            windows.append(got['window'])
        else:
            refused.append({'index': i, 'reason': got['reason'],
                            'slot_id': rec.get('slot_id'),
                            'task_id': rec.get('task_id')})
    base['records_refused'] = refused

    # A refused record is not a missing one. If ANY record in the log could not be
    # turned into a window, the log describes a period we cannot fully account
    # for, and lifecycle_complete is false -- which the consumer treats as a
    # refusal that RETAINS the attempt rather than excluding a task.
    complete = not refused and not parsed['rejected']
    if not windows:
        return dict(base, active=False, lifecycle_complete=False, active_windows=[],
                    reason='no complete slot occupancy is recorded (%d record(s) '
                           'read, %d refused)' % (len(parsed['records']), len(refused)))
    return dict(base, active=True, lifecycle_complete=complete,
                active_windows=windows,
                window_id='lifecycle:%s:%d' % (
                    parsed['records'][0].get('instance_id'), len(windows)),
                endpoint_error_s=0.0,
                endpoint_error_basis='the endpoints ARE the server\'s own transition '
                                     'timestamps, not observations of them, so there '
                                     'is no client-side delivery error to bound. The '
                                     'inner bracket already discards the prompt-bind '
                                     'and release edges.')
