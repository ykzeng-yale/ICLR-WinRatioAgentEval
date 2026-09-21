"""THE preparation entry point: the reference sweep, wired to a durable ledger.

Root, 2026-09-21 20:05: "At this exact tree, ``AttemptLedger`` construction and
``on_attempt=ledger.append`` appear only in ``tests_lab_design.py``;
``sweep_references`` still permits ``on_attempt=None``. The tests demonstrate that
the production sink implementation CAN be connected, not that the production
preparation entry point ALREADY connects it. ... Connect the actual finite
preparation/sweep entry point to a ledger created before the first verifier
attempt, and make a missing sink or failed durable append stop that entry point."

This module is that entry point. It exists so no one can run the real sweep
through the default no-sink path by accident.

WHY IT LIVES INSIDE THE PINNED HARNESS DIRECTORY
------------------------------------------------
``lab_common.HARNESS_FILES`` globs ``experiments/live_ab/*.py`` and feeds
``harness_file_sha256``, so adding this file moves that pin. That is correct and
intended: root, same review, "Required execution/containment code must still be
pinned even if added now ... Do not move execution-relevant code outside the pin
set just to avoid changing a hash." A sweep driver is execution-relevant. The
purely DESCRIPTIVE status reporter was moved out for the opposite reason.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not start a server, call a model, or provide the protocol 3.2 rule 4 load
regime. ``run_reference_sweep`` REFUSES unless the caller passes an explicit,
already-authorized load-coverage observer, because an unloaded sweep produces a
roster that violates rule 4 and nothing in the artifact can tell the two apart
afterwards.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                                  # pragma: no cover
    sys.path.insert(0, str(HERE))

import lab_common                                              # noqa: E402
import lab_data                                                # noqa: E402


class PreparationRefused(lab_common.PreflightError):
    """Preparation may not begin, or may not continue."""


def open_ledger(path: "str | Path") -> lab_data.AttemptLedger:
    """Create the retention ledger BEFORE any verifier attempt, or refuse.

    A ledger that cannot be created is a preparation that must not start: the
    sweep would otherwise produce exclusions whose preimage was never recorded,
    which is the defect D1 exists to prevent.
    """
    path = Path(path)
    try:
        ledger = lab_data.AttemptLedger(path)
    except OSError as exc:
        raise PreparationRefused(
            'cannot create the retention ledger at %s (%s); preparation does not '
            'start without a durable sink'
            % (lab_common.tokenize_path(path), type(exc).__name__)) from None
    # A pre-existing ledger with a malformed tail is unresolved failure evidence
    # from an earlier run.  Root: "refuse a continuation that would append onto
    # malformed JSON without an explicit preserved-tail recovery rule."
    try:
        ledger.load()
    except ValueError as exc:
        raise PreparationRefused(str(exc)) from None
    return ledger


def run_reference_sweep(tasks: Sequence[dict], cfg: dict, *,
                        ledger_path: "str | Path",
                        load_observer: Optional[Callable[[], dict]] = None,
                        require_load: bool = True,
                        on_progress: Optional[Callable] = None,
                        enforce_tmpdir: bool = True,
                        sweep_fn: Callable = lab_data.sweep_references,
                        ) -> Dict[str, Any]:
    """The finite preparation sweep, with retention wired and load enforced.

    ``load_observer`` returns the server-side activity observation covering the
    attempt about to run -- root 2026-09-21 20:05 requires per-attempt coverage
    "evidenced by reusable load windows", not one request per attempt. It must
    report the covering window identifiers and the timing resolution, and
    ``require_load`` may be cleared ONLY for offline plumbing tests, never for a
    roster-producing run.
    """
    if require_load and load_observer is None:
        raise PreparationRefused(
            'protocol 3.2 rule 4 requires the reference sweep to run under the '
            "trial's load regime, and no load observer was supplied. An unloaded "
            'sweep yields a LARGER roster with correct-looking counts, and the '
            'deposited artifact cannot distinguish it afterwards. Refusing.')

    # TMPDIR ENFORCEMENT AT THE REAL ENTRY POINT, root 2026-09-21 20:43: "The new
    # assertion currently has no callers: adding a helper alone did not yet
    # enforce even preparation. Wire it and show valid/mismatched startup
    # fixtures through the real entry points." Correct -- I added the helper and
    # called it only from the containment probe, so nothing was enforced here.
    # Checked BEFORE the ledger, so a wrong-TMPDIR run never reaches the sandbox.
    if enforce_tmpdir:
        assert_prescribed_tmpdir(cfg)

    ledger = open_ledger(ledger_path)        # created BEFORE the first attempt
    started = ledger.count
    coverage: List[dict] = []

    invalid_coverage: List[dict] = []

    def sink(record: dict) -> None:
        # ORDERING REPAIR, root 2026-09-21 20:43: "Store every raw attempt BEFORE
        # fallible observation processing; invalid coverage must never produce
        # completed preparation or a scientific task exclusion."
        #
        # My first version called load_observer() and only then appended. If the
        # observer raised, the RAW ATTEMPT WAS LOST -- the exact retention failure
        # this ledger exists to prevent, reintroduced by the coverage feature.
        # The raw attempt is now durable before anything fallible touches it.
        ledger.append(record)                       # (1) RAW, always, first
        if load_observer is None:
            return
        # IMMEDIATE STOP, root 2026-09-21 21:17: "Retain the distinction between
        # eventual refusal and IMMEDIATE STOP: the new sink accumulates
        # invalid_coverage and returns, allowing more verifier attempts before
        # the post-sweep refusal. Persist the raw attempt and observer
        # failure/invalid observation, then RAISE from that sink so no next
        # attempt starts ... do not run a whole invalid sweep to learn it is
        # invalid." Correct: my version refused only after sweep_fn finished.
        key = {'uid': record.get('uid'), 'run_index': record.get('run_index')}
        try:                                        # (2) then the fallible part
            obs = load_observer()
        except Exception as exc:
            failure = dict(key, schema='live_ab/load_coverage_failure-v1',
                           error='%s: %s' % (type(exc).__name__, exc))
            ledger.append(failure)                  # PERSIST the error, not only in memory
            invalid_coverage.append(failure)
            raise PreparationRefused(
                'load observation failed on %s; the raw attempt and this error are '
                'retained and NO further verifier attempt is started'
                % (key,)) from exc
        entry = dict(key, observation=obs)
        verdict = _coverage_verdict(obs, record)
        ledger.append({'schema': 'live_ab/load_coverage-v1', **entry,
                       'valid': verdict['valid'], 'reason': verdict['reason']})
        coverage.append(entry)
        if not verdict['valid']:
            invalid_coverage.append(dict(entry, reason=verdict['reason']))
            raise PreparationRefused(
                'load coverage is invalid on %s (%s); the raw attempt is retained, '
                'no task is excluded on account of it, and NO further verifier '
                'attempt is started' % (key, verdict['reason']))

    outcome: Dict[str, Any] = {
        'schema': 'live_ab/preparation_sweep-v1',
        'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'ledger_path': lab_common.tokenize_path(Path(ledger_path)),
        'load_required': bool(require_load),
    }
    try:
        exclusions = sweep_fn(list(tasks), cfg, on_progress=on_progress,
                              on_attempt=sink)
    except Exception as exc:
        outcome.update(completed=False, error='%s: %s' % (type(exc).__name__, exc),
                       records_retained=ledger.count - started,
                       ended_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        raise PreparationRefused(lab_common.canonical_json(outcome)) from exc

    # Root: "invalid coverage must never produce COMPLETED preparation or a
    # scientific task exclusion." A missing or unusable observation is not a
    # reference failure and must not become one.
    if invalid_coverage:
        raise PreparationRefused(
            'load coverage was missing or invalid for %d attempt(s) (e.g. %s). The '
            'raw attempts are retained; this preparation is NOT completed and no '
            'task is excluded on account of it. Stop and diagnose.'
            % (len(invalid_coverage), invalid_coverage[:2]))
    outcome.update(completed=True, exclusions=len(exclusions),
                   records_retained=ledger.count - started,
                   load_coverage_records=len(coverage),
                   ended_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    # Retention must be demonstrable, not assumed: every exclusion's digest has to
    # reconstruct from what the ledger actually holds.
    reloaded = ledger.load()
    by_uid: Dict[str, List[dict]] = {}
    for rec in reloaded:
        # The ledger now carries TWO record kinds -- attempt records and load
        # coverage entries, both keyed by uid. Only attempt records are part of
        # the digest preimage; mixing a coverage entry in would corrupt the
        # reconstruction. Filter by schema rather than by presence of a field.
        if rec.get('schema') != lab_data.ATTEMPT_RECORD_SCHEMA:
            continue
        by_uid.setdefault(rec.get('uid'), []).append(rec)
    unreconstructed = [e['uid'] for e in exclusions
                       if lab_data.reconstruct_detail_sha256(
                           by_uid.get(e['uid'], [])) != e['detail_sha256']]
    if unreconstructed:
        raise PreparationRefused(
            'the retained ledger does not reconstruct the digests of %d exclusion(s) '
            '(e.g. %s); retention did not hold and this sweep is not usable'
            % (len(unreconstructed), unreconstructed[:3]))
    outcome['all_digests_reconstruct_from_ledger'] = True
    return {'exclusions': exclusions, 'receipt': outcome, 'coverage': coverage}


# ---------------------------------------------------------------------------
# D4/D5: source acquisition -- refuse-or-restore, idempotent, content-addressed
# ---------------------------------------------------------------------------
# Root, 2026-09-21 18:54:
#   "Gitignored raw data is consistent with repository policy; absence from Git
#    alone is not a scientific defect. Use durable content-addressed cache plus
#    exact revision/hash/size and a documented retrieval path; no dependency on
#    ephemeral temp directories. The protocol allows S1 fallback when the original
#    S2 download fails, but this preparation has verified S2 and selected EXT. A
#    later missing cache must REFUSE OR RESTORE the same verified bytes, not
#    silently change to S1. ... Make repeat acquisition of identical content
#    idempotent while retaining original acquisition provenance and recording
#    later accesses separately. A changed filesystem origin should not overwrite
#    or invalidate a content-identical source manifest."
#
# The policy lives here rather than inside `lab_data.fetch_sources` so that
# module's ARCHITECTURE section 3.4 signature stays fixed; the driver is where
# root asked for the wiring anyway.

ACCESS_LOG_NAME = 'source_accesses.jsonl'


def _content_key(manifest: dict) -> dict:
    """The CONTENT identity of a source manifest: what it resolved, not where from.

    ``origin`` and ``from_cache`` are deliberately excluded. They are the fields
    that change merely because a first call copied the files into ``dest``, which
    is what made `fetch_sources` non-idempotent (D5): a second call with identical
    inputs produced different manifest bytes and tripped the write-once guard.
    """
    return {name: {k: v for k, v in (spec or {}).items()
                   if k in ('present', 'filename', 'bytes', 'sha256', 'revision',
                            'records', 'stratum', 'reason')}
            for name, spec in sorted((manifest.get('sources') or {}).items())}


def acquire_sources(dest: "str | Path", *, offline: bool = True,
                    expect_mode: Optional[str] = None,
                    enforce_tmpdir: bool = False,
                    fetch_fn: Callable = lab_data.fetch_sources) -> Dict[str, Any]:
    """Resolve the pinned sources, refusing a silent downgrade.

    ``expect_mode`` is the roster mode a previous verified acquisition established.
    When it is ``'EXT'`` and this resolution would yield ``'S1'``, the call RAISES
    instead of returning a half roster: that downgrade is the silent-halving defect
    (D4), where an absent optional source quietly turns 564 pairs into 295 with no
    exception anywhere. If ``expect_mode`` is None it is read from a prior manifest
    in ``dest``, so the guard arms itself once a mode has ever been established.
    """
    dest = Path(dest)
    if enforce_tmpdir:
        assert_prescribed_tmpdir(json.loads(
            (Path(__file__).resolve().parent / 'config.json').read_text('utf-8')))
    prior_path = dest / 'sources.json'
    prior = None
    if prior_path.is_file():
        try:
            prior = json.loads(prior_path.read_text('utf-8'))
        except ValueError as exc:
            raise PreparationRefused(
                'the existing source manifest at %s is unreadable (%s); resolve it '
                'explicitly rather than acquiring over it'
                % (lab_common.tokenize_path(prior_path), exc)) from None
    if expect_mode is None and prior is not None:
        expect_mode = prior.get('roster_mode')

    if prior is not None:
        # IDEMPOTENCE (D5): a manifest already exists. Re-verify the CONTENT on
        # disk rather than rewriting the manifest, so a changed filesystem origin
        # cannot invalidate a content-identical acquisition.
        drift = []
        for name, spec in lab_data.SOURCES.items():
            rec = (prior.get('sources') or {}).get(name) or {}
            if not rec.get('present'):
                continue
            f = dest / spec['filename']
            if not f.is_file():
                drift.append('%s: recorded present but absent from dest' % name)
                continue
            if lab_common.sha256_file(f) != spec['sha256']:
                drift.append('%s: bytes on disk differ from the pinned sha256' % name)
        if drift and expect_mode == 'EXT':
            raise PreparationRefused(
                'a previously verified EXT acquisition can no longer be restored '
                'from %s (%s). Root: "A later missing cache must refuse or restore '
                'the same verified bytes, not silently change to S1." Refusing.'
                % (lab_common.tokenize_path(dest), '; '.join(drift)))
        _record_access(dest, 'reuse', prior.get('roster_mode'), drift)
        return {'manifest': prior, 'roster_mode': prior.get('roster_mode'),
                'reused_existing_manifest': True, 'content_drift': drift}

    manifest = fetch_fn(dest, offline=offline)
    mode = manifest.get('roster_mode')
    if expect_mode == 'EXT' and mode != 'EXT':
        raise PreparationRefused(
            'a previous acquisition established roster_mode EXT and this one '
            'resolved %r. Silently continuing would halve the roster (564 pairs '
            'to 295) with no exception anywhere. Restore the verified S2 bytes or '
            'stop.' % (mode,))
    _record_access(dest, 'acquire', mode, [])
    return {'manifest': manifest, 'roster_mode': mode,
            'reused_existing_manifest': False, 'content_drift': []}


def _record_access(dest: Path, kind: str, mode: "str | None",
                   drift: Sequence[str]) -> None:
    """Later accesses are recorded SEPARATELY from the original acquisition.

    Root: "retaining original acquisition provenance and recording later accesses
    separately." The write-once ``sources.json`` is never rewritten; this append-only
    log carries who looked and when.
    """
    entry = {'schema': 'live_ab/source_access-v1', 'kind': kind,
             'roster_mode': mode, 'content_drift': list(drift),
             'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    ledger = lab_data.AttemptLedger(Path(dest) / ACCESS_LOG_NAME)
    ledger.append(entry)


PRESCRIBED_TMPDIR_TOKEN = '<TMP>/labsbx'


def assert_prescribed_tmpdir(cfg: dict, *, tmp_root: str = '/private/tmp') -> Dict[str, Any]:
    """Refuse to prepare unless TMPDIR is the one config declares.

    Protocol 5.7 item 2 says "TMPDIR is set to the neutral path carried in
    config.json as the token ``<TMP>/labsbx``" -- passive voice, and nothing in
    the code enforced it. A run that forgets to export it silently gets the
    ambient TMPDIR and a DIFFERENT Seatbelt profile digest, with no error. That
    is not hypothetical: I computed and promoted an ambient-TMPDIR digest into
    config, ARCHITECTURE 6.1 and protocol Appendix B before noticing.

    The digest DEPENDS on TMPDIR by design -- 5.7 item 2 says so explicitly and
    records the resulting hash in the freeze bundle and per episode. Silently
    getting the wrong TMPDIR is the defect, not the dependence.
    """
    import os
    import tempfile as _tf
    declared = ((cfg or {}).get('sandbox') or {}).get('tmpdir')
    if declared != PRESCRIBED_TMPDIR_TOKEN:
        raise PreparationRefused(
            'config.sandbox.tmpdir is %r; protocol 5.7 item 2 prescribes %r'
            % (declared, PRESCRIBED_TMPDIR_TOKEN))
    want = os.path.join(tmp_root, declared.split('/', 1)[1])
    effective = os.path.realpath(_tf.gettempdir())
    if effective != os.path.realpath(want):
        raise PreparationRefused(
            'TMPDIR is %s but protocol 5.7 item 2 prescribes %s. The Seatbelt '
            'profile digest is a function of TMPDIR, so preparing under the wrong '
            'one silently produces a profile hash that no production run can '
            'reproduce. Export TMPDIR=%s and retry.'
            % (lab_common.tokenize_path(Path(effective)), want, want))
    return {'prescribed_tmpdir': want,
            'sandbox_base_dir': os.path.join(want, 'ls_sbx'),
            'checked': True}


def _coverage_verdict(obs: object, record: dict) -> Dict[str, Any]:
    """Whether an observation actually COVERS the attempt's interval.

    Root, 2026-09-21 21:17: "Required load coverage is still metadata presence,
    not interval validation. `_coverage_is_valid` checks `active is True` and
    nonempty `window_id`/`resolution_ms` only. It does not compare actual
    verifier start/end times with active-load windows on the agreed clock. A
    post-attempt result containing those three fields passes."

    That was exactly right. Presence of three fields is not coverage. This
    compares the attempt's own monotonic endpoints against the observation's
    active windows on the same clock, and requires the windows to span the whole
    interval -- with the stated timing resolution charged AGAINST the claim, so
    a coarse sampler cannot certify a gap it could not have seen.
    """
    if not isinstance(obs, dict):
        return {'valid': False, 'reason': 'observation is not a mapping'}
    if obs.get('active') is not True:
        return {'valid': False, 'reason': 'observation does not report active load'}
    for key in ('window_id', 'resolution_ms'):
        if obs.get(key) in (None, ''):
            return {'valid': False, 'reason': 'observation omits %s' % key}

    start, end = record.get('started_monotonic'), record.get('ended_monotonic')
    if start is None or end is None:
        return {'valid': False,
                'reason': 'the attempt carries no monotonic endpoints, so no '
                          'window can be shown to cover it'}
    windows = obs.get('active_windows')
    if not isinstance(windows, list) or not windows:
        return {'valid': False,
                'reason': 'observation carries no active_windows to compare against '
                          "the attempt's interval; a post-attempt sample is not "
                          'coverage of the interval'}
    try:
        res_s = float(obs['resolution_ms']) / 1000.0
    except (TypeError, ValueError):
        return {'valid': False, 'reason': 'resolution_ms is not numeric'}

    # Charge the sampling resolution against the claim: a window is only credited
    # over the span it could actually have observed.
    covered: List[tuple] = []
    for w in windows:
        try:
            ws, we = float(w['start']), float(w['end'])
        except (TypeError, ValueError, KeyError):
            return {'valid': False, 'reason': 'an active window lacks numeric endpoints'}
        covered.append((ws + res_s, we - res_s))
    covered.sort()
    cursor = float(start)
    for ws, we in covered:
        if ws > cursor:
            break                       # a gap the windows do not span
        cursor = max(cursor, we)
    if cursor < float(end):
        return {'valid': False,
                'reason': 'active windows leave %.3fs of the attempt interval '
                          'uncovered at the stated resolution' % (float(end) - cursor)}
    return {'valid': True, 'reason': 'active windows span the attempt interval'}
