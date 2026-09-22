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
SEAL_SCHEMA = 'live_ab/acquisition_seal-v1'
ERROR_SCHEMA = 'live_ab/acquisition_error-v1'
OBSERVATION_SCHEMA = 'live_ab/lifecycle_observation-v1'
EVIDENCE_KIND = 'server_lifecycle'
CLOCK = 'clock_gettime(CLOCK_MONOTONIC)'

#: The patch this reader is the counterpart of. A reader that silently accepted
#: records from a different emitter would be reading an unknown instrument.
PATCH_PATH = 'experiments/live_ab_serving/live_ab_slot_lifecycle.patch'
PATCHED_BASE_REV = '4fea119de30f6a923992780f6fd5ccb0bee5d47d'


class LifecycleRefused(lab_common.PreflightError):
    """The lifecycle evidence cannot support an observation."""


#: ggml_time_us() truncates to whole microseconds, so a recorded start may be up
#: to one microsecond EARLIER than the transition it names. Root, 2026-09-22
#: 04:59: "account for the one-microsecond ggml_time_us quantization ... by
#: moving the server start INWARD, keeping its end conservative and recording the
#: bound. Do not infer zero error from the absence of network delivery error."
QUANTIZATION_US = 1

#: Values that are not identifiers, however many of them agree.
PLACEHOLDER_IDS = frozenset({'', 'none', 'null', 'unknown', 'n/a', '-'})


def _typed_id(value: object, field: str) -> Optional[str]:
    """A non-placeholder identifier, or None. Absence is never an identity.

    Root's witness: with instance and task omitted from both records, the reader
    built ``None/slot0/taskNone`` and ``None/slot1/taskNone`` and COUNTED THEM AS
    TWO LIFETIMES -- string construction turning absence into countable identity.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        v = value.strip()
        return v if v and v.lower() not in PLACEHOLDER_IDS else None
    return None


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
        return {'records': [], 'rejected': [], 'seals': [], 'writer_errors': [],
                'error': 'no lifecycle log at %s' % lab_common.tokenize_path(path)}
    raw = path.read_text('utf-8')
    lines = raw.splitlines()
    if raw and not raw.endswith('\n'):
        return {'records': [], 'rejected': [], 'seals': [], 'writer_errors': [],
                'error': 'the lifecycle log ends mid-line (%d bytes); the server is '
                         'still writing. Re-read rather than trimming: a trimmed '
                         'partial line discards an occupancy that did happen.'
                         % len(raw)}
    records, rejected, seals, errors = [], [], [], []
    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            rejected.append({'line': i, 'reason': 'unparsable: %s' % exc})
            continue
        if not isinstance(rec, dict):
            rejected.append({'line': i, 'reason': 'not a JSON object'})
            continue
        schema = rec.get('schema')
        if schema == RECORD_SCHEMA:
            records.append(rec)
        elif schema == SEAL_SCHEMA:
            # DEFECT FOUND BY THE NATIVE FIXTURE, 2026-09-22 05:57, and it is the
            # reason root asked for one: "Test real serialization/reader
            # interoperability, not only Python dictionaries shaped to resemble
            # it." The built binary wrote its closing seal and THIS READER
            # REJECTED IT as "not a slot_lifecycle-v1 record" -- so a correctly
            # sealed acquisition was counted as containing garbage and refused.
            # The seal is the one line that proves the log is finished.
            seals.append(rec)
        elif schema == ERROR_SCHEMA:
            errors.append(rec)
        else:
            rejected.append({'line': i, 'reason': 'unknown schema %r' % (schema,)})
    return {'records': records, 'rejected': rejected, 'seals': seals,
            'writer_errors': errors, 'error': None}


def window_from_record(rec: dict, *, expected: Optional[dict] = None) -> Dict[str, Any]:
    """One record -> one certified window, or a refusal with its reason.

    ``expected`` is the run manifest the supervisor persisted before dispatch:
    the binary, the patch, the host and kernel-boot digests and the server
    instance identity it launched. The record is compared against it. Root,
    2026-09-22 04:59: "the reader compares it to the expected manifest and
    verifier provenance INSTEAD OF INVENTING A SOURCE IDENTITY FROM ITS OWN
    PROCESS" -- which is exactly what the first version did, stamping the
    caller's provenance onto whatever file it was handed, so a copied log or one
    from a previous boot read as local and current.
    """
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
    # TYPED, NON-PLACEHOLDER IDENTIFIERS. Absence is not an identity.
    inst = _typed_id(rec.get('instance_id'), 'instance_id')
    slot = _typed_id(rec.get('slot_id'), 'slot_id')
    task = _typed_id(rec.get('task_id'), 'task_id')
    missing = [n for n, v in (('instance_id', inst), ('slot_id', slot),
                              ('task_id', task)) if v is None]
    if missing:
        return {'ok': False, 'reason': 'record carries no usable %s; an absent '
                                       'identifier is not an identity and must not '
                                       'be spelled into one' % ', '.join(missing)}

    # THE ECHO CONTRACT, END TO END. Root, 2026-09-22 06:16: "The C++ emitter
    # sends run_token/instance_id, NOT host/boot digests. Validate each record
    # and seal against the fresh token in the supervisor's persisted expected
    # manifest, then bind that manifest to measured observer/verifier host/boot.
    # ... do not demand nonexistent per-record host/boot fields."
    #
    # My reader demanded host_id and boot_id ON EVERY RECORD -- fields the real
    # emitter never writes. Only my hand-written Python fixtures carried them, so
    # the positive case passed on bytes the instrument cannot produce, and the
    # first loaded run would have failed on format. The record is bound by its
    # TOKEN; the manifest is bound to the host (see observe()).
    if expected is not None:
        want = _typed_id(expected.get('instance_id'), 'instance_id')
        token = _typed_id(rec.get('run_token'), 'run_token') or inst
        if want is None or token != want:
            return {'ok': False,
                    'reason': 'record run token %r does not match the launched run '
                              'manifest %r; a log that cannot be bound to the '
                              'producer the supervisor started is not evidence'
                              % (token, want)}

    # INTEGER MICROSECOND TRANSITIONS, and the ORDER VERIFIED rather than trusted.
    ts = {}
    for name in ('t_assigned_us', 't_prompt_start_us', 't_gen_last_us',
                 't_released_us'):
        v = rec.get(name)
        if not isinstance(v, int) or isinstance(v, bool):
            return {'ok': False, 'reason': '%s is not an integer microsecond '
                                           'reading (%r)' % (name, v)}
        ts[name] = v
    ordered = (ts['t_assigned_us'] <= ts['t_prompt_start_us']
               <= ts['t_gen_last_us'] <= ts['t_released_us'])
    if not ordered:
        # Root's witness: complete=true with assignment AFTER release still
        # certified. "A boolean does not independently validate the record's
        # consistency."
        return {'ok': False,
                'reason': 'the four transitions are not ordered '
                          '(assigned %d, prompt %d, gen_last %d, released %d); the '
                          "record's own complete flag does not validate it"
                          % (ts['t_assigned_us'], ts['t_prompt_start_us'],
                             ts['t_gen_last_us'], ts['t_released_us'])}
    lo, hi = ts['t_prompt_start_us'], ts['t_gen_last_us']
    if hi <= lo:
        return {'ok': False, 'reason': 'inner interval is empty or reversed '
                                       '(%r -> %r)' % (lo, hi)}

    # QUANTIZATION, INWARD. A truncated start may name an instant up to one
    # microsecond before the transition, so the start moves later; the end is
    # left where it is, which is the conservative direction for both.
    lo_q = lo + QUANTIZATION_US
    if hi <= lo_q:
        return {'ok': False,
                'reason': 'the inner interval does not survive the %d us '
                          'quantization allowance' % QUANTIZATION_US}
    ident = '%s/slot%s' % (inst, slot)          # the OCCUPIED SLOT, not the task
    return {'ok': True, 'window': {
        'schema': 'live_ab/lifecycle_window-v1',
        # MICROSECONDS -> SECONDS, stated rather than implied. The verifier's
        # POSIX endpoints are integer nanoseconds; both land on seconds here and
        # the conversion is explicit on each side.
        'start': lo_q / 1e6, 'end': hi / 1e6,
        'identity': ident,
        'lifetime_identity': '%s/task%s' % (ident, task),
        'quantization_allowance_us': QUANTIZATION_US,
        'raw_inner_start_us': lo,
        'bracket': 'inner (t_prompt_start_us .. t_gen_last_us); the outer bracket '
                   't_assigned_us .. t_released_us is wider and is NOT used',
        'outer_start': ts['t_assigned_us'],
        'outer_end': ts['t_released_us'],
        'n_gen': rec.get('n_gen'),
        'means': 'an occupied decoding slot, NOT uninterrupted hardware utilization',
    }}


def sequence_problem(seqs: List, declared: object) -> Optional[str]:
    """Exactly one record per sequence value in ``0..declared-1``, or why not.

    Root, 2026-09-22 06:16: "For a nonnegative integer seal count, require
    EXACTLY ONE non-boolean integer for each value in 0..count-1; reject missing,
    DUPLICATE, EXTRA and out-of-range values. File order need not be numeric
    because sequence allocation precedes the writer mutex."

    My first version took a SET DIFFERENCE, which is blind to duplicates and to
    extras: two records both numbered 3, with 4 missing, gave an empty gap and
    passed. A multiset is the right object because the producer allocates each
    number exactly once.
    """
    if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
        return 'the seal declares %r records, not a nonnegative integer' % (declared,)
    bad = [q for q in seqs if isinstance(q, bool) or not isinstance(q, int)]
    if bad:
        return 'a record carries a non-integer seq (%r)' % (bad[:3],)
    counts: Dict[int, int] = {}
    for q in seqs:
        counts[q] = counts.get(q, 0) + 1
    missing = sorted(v for v in range(declared) if v not in counts)
    duplicate = sorted(v for v, n in counts.items() if n > 1)
    out_of_range = sorted(v for v in counts if v < 0 or v >= declared)
    if missing or duplicate or out_of_range:
        return ('sequence multiset does not match the seal count %d: missing %s, '
                'duplicated %s, out of range %s'
                % (declared, missing[:5], duplicate[:5], out_of_range[:5]))
    if len(seqs) != declared:
        return ('the file carries %d records and the seal declares %d'
                % (len(seqs), declared))
    return None


def _overlaps_on_one_slot(windows: List[dict]) -> Optional[str]:
    """Two occupancies of the SAME slot that overlap in time.

    Root's witness: same instance, same slot, two different task ids, overlapping
    -- counted as TWO concurrent lifetimes. One slot cannot be occupied twice at
    once, so such a pair is not two loads; it is a record set that cannot be
    true, and "request labels can inflate slot concurrency" is exactly the way a
    concurrency requirement gets met without the concurrency.
    """
    by_slot: Dict[str, List[dict]] = {}
    for w in windows:
        by_slot.setdefault(w['identity'], []).append(w)
    for ident, ws in by_slot.items():
        ws = sorted(ws, key=lambda x: x['start'])
        for a, b in zip(ws, ws[1:]):
            if b['start'] < a['end']:
                return ('slot %s reports two overlapping occupancies (%s and %s); '
                        'one slot cannot be occupied twice at once'
                        % (ident, a.get('lifetime_identity'),
                           b.get('lifetime_identity')))
    return None


def observe(path: "str | Path", *, concurrency_required: int = 2,
            expected: Optional[dict] = None,
            provenance: Optional[dict] = None) -> Dict[str, Any]:
    """The observation ``lab_prepare.run_reference_sweep`` consumes.

    ``expected`` is the run manifest the supervisor persisted BEFORE dispatch.
    When it is supplied every record is bound to it. When it is not, the records
    are read but the observation is marked ``producer_bound: False`` and carries
    no certifying claim about which producer wrote them -- the first version
    silently stamped this process's provenance onto any file it was handed, so a
    copied log or one from a previous boot read as local and current.
    """
    prov = provenance if provenance is not None else lab_data.clock_provenance()

    # THE LINK ROOT'S WITNESS BROKE, 2026-09-22 05:42:
    #   "Our independent witness uses FOREIGN RECORDS PLUS A MATCHING FOREIGN
    #    MANIFEST, with local observer/verifier provenance, and still obtains
    #    producer_bound=true, lifecycle_complete=true, coverage_valid=true.
    #    Records-to-manifest comparison alone does not close the original
    #    copied-log finding."
    #
    # Exactly right, and the shape of the error is familiar: I checked that two
    # things AGREE WITH EACH OTHER without checking that either is the thing it
    # claims to be. A foreign log and a foreign manifest agree perfectly. The
    # manifest must therefore be tied to INDEPENDENTLY MEASURED observer
    # provenance before anything it vouches for can certify; the existing
    # observer-to-verifier check then completes the chain.
    manifest_mismatch = None
    if expected is not None:
        for field in ('host_id', 'boot_id'):
            want, got = expected.get(field), prov.get(field)
            if not isinstance(want, str) or not want or \
                    want.strip().lower() in PLACEHOLDER_IDS:
                manifest_mismatch = ('the expected manifest carries no usable %s '
                                     '(%r)' % (field, want))
                break
            if want != got:
                manifest_mismatch = (
                    'the expected manifest names %s %r but this observer measured '
                    '%r. A manifest that agrees with its own records proves only '
                    'that they were written together, not that they were written '
                    'HERE on THIS boot.' % (field, want, got))
                break

    parsed = read_records(path)
    # THE ACTUAL SIDECAR. Root: "Read and retain the actual <log>.error output in
    # the acquisition path; any terminal writer failure refuses the acquisition."
    # The producer writes failures to a SEPARATE file precisely so a failing log
    # cannot hide its own failure -- which is useless if the reader never opens
    # it. A seal-close error, in particular, is invisible anywhere else.
    sidecar_path = Path(str(path) + '.error')
    sidecar: List[dict] = []
    sidecar_unreadable = None
    if sidecar_path.exists():
        try:
            for line in sidecar_path.read_text('utf-8').splitlines():
                if line.strip():
                    try:
                        sidecar.append(json.loads(line))
                    except ValueError:
                        sidecar.append({'unparsable': line[:200]})
        except OSError as exc:
            sidecar_unreadable = '%s: %s' % (type(exc).__name__, exc)
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
        'producer_bound': expected is not None and manifest_mismatch is None,
        'manifest_bound_to_observer': expected is not None and manifest_mismatch is None,
        # Root, 2026-09-22 05:42: "Binary/patch fields are presently echoed
        # metadata, and sequence/seal validation is not yet implemented in the
        # reader: label these PENDING until the planned producer/consumer
        # completion." Labelled here rather than implied by their presence.
        'pending_not_yet_validated': ['binary_sha256 and patch_sha256 are ECHOED '
                                      'METADATA, not verified against the running '
                                      'binary',
                                      'record sequence numbers and the closing seal '
                                      'are not yet emitted or validated'],
        'expected_manifest': ({k: expected.get(k) for k in
                               ('host_id', 'boot_id', 'instance_id', 'binary_sha256',
                                'patch_sha256')} if expected else None),
        'source_patch': PATCH_PATH,
        'source_base_rev': PATCHED_BASE_REV,
        'records_read': len(parsed['records']),
        'records_rejected_by_parser': parsed['rejected'],
    }
    if manifest_mismatch is not None:
        # A refused attempt, retained -- never a task exclusion.
        base['manifest_mismatch'] = manifest_mismatch
        return dict(base, active=False, lifecycle_complete=False,
                    active_windows=[], reason=manifest_mismatch)
    if parsed['error']:
        return dict(base, active=False, lifecycle_complete=False,
                    active_windows=[], reason=parsed['error'])

    windows, refused = [], []
    for i, rec in enumerate(parsed['records']):
        got = window_from_record(rec, expected=expected)
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
    # THE SEAL AND SEQUENCE CONTRACT, root 2026-09-22 04:59: "Durable
    # assignment/start records paired with terminal/release records and a final
    # sequence/count seal provide a finite check for a missing endpoint or lost
    # final line. Missing terminal/seal, unfinished request, writer failure or
    # sequence gap is unresolved/refused, never an excluded task. A
    # newline-terminated subset alone is not a complete acquisition."
    seals, writer_errors = parsed.get('seals') or [], parsed.get('writer_errors') or []
    base['seals'] = seals
    base['writer_errors'] = writer_errors
    base['sidecar_path'] = sidecar_path.name
    base['sidecar_records'] = sidecar
    base['sidecar_unreadable'] = sidecar_unreadable
    seal_problem = None
    if not seals:
        seal_problem = ('the acquisition carries NO CLOSING SEAL, so the writer did '
                        'not finish: a newline-terminated subset is not a complete '
                        'acquisition, and a crashed producer leaves exactly this')
    elif len(seals) > 1:
        seal_problem = ('the acquisition carries %d seals; a log is sealed once'
                        % len(seals))
    else:
        seal = seals[0]
        if seal.get('write_failures'):
            seal_problem = ('the producer recorded %r write failure(s); the log is '
                            'not known to be whole' % seal.get('write_failures'))
        elif expected is not None and seal.get('run_token') != expected.get('instance_id'):
            seal_problem = ('the seal names run token %r, not the launched %r'
                            % (seal.get('run_token'), expected.get('instance_id')))
        else:
            seal_problem = sequence_problem(
                [r.get('seq') for r in parsed['records']], seal.get('records'))
    if sidecar:
        seal_problem = seal_problem or (
            'the producer recorded %d failure(s) in its %s sidecar (%s); any '
            'terminal writer failure refuses the acquisition'
            % (len(sidecar), sidecar_path.name,
               [e.get('stage') for e in sidecar[:3]]))
    if sidecar_unreadable:
        seal_problem = seal_problem or ('the sidecar exists and could not be read '
                                        '(%s); an unreadable failure channel is not '
                                        'an absent one' % sidecar_unreadable)
    if writer_errors:
        seal_problem = seal_problem or ('the producer wrote %d acquisition error(s) '
                                        'into the main log' % len(writer_errors))
    base['seal_problem'] = seal_problem

    complete = not refused and not parsed['rejected'] and seal_problem is None
    overlap = _overlaps_on_one_slot(windows)
    if overlap is not None:
        base['impossible_overlap'] = overlap
        return dict(base, active=False, lifecycle_complete=False,
                    active_windows=[], reason=overlap)
    if expected is None:
        # Unbound records are readable and are NOT certifying evidence.
        complete = False
        base['unbound_reason'] = ('no run manifest was supplied, so these records '
                                  'are not bound to the producer the supervisor '
                                  'launched')
    if not windows:
        return dict(base, active=False, lifecycle_complete=False, active_windows=[],
                    reason='no complete slot occupancy is recorded (%d record(s) '
                           'read, %d refused)' % (len(parsed['records']), len(refused)))
    return dict(base, active=True, lifecycle_complete=complete,
                active_windows=windows,
                window_id='lifecycle:%s:%d' % (
                    parsed['records'][0].get('instance_id'), len(windows)),
                endpoint_error_s=0.0,
                endpoint_error_basis=(
                    'ZERO here does NOT mean "no error": the %d us ggml_time_us '
                    'quantization is already charged against each window by moving '
                    'its START INWARD in window_from_record, so charging it again '
                    'here would double it. The endpoints are the server\'s own '
                    'transition timestamps rather than observations of them, so '
                    'there is no client-side delivery error to bound -- root, '
                    '2026-09-22: "Do not infer zero error from the absence of '
                    'network delivery error."' % QUANTIZATION_US))
