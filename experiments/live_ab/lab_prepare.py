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
    # A configuration requesting the injected-decision fixture never reaches a
    # dispatch or a model request. Checked here, on the real entry point, rather
    # than left as an available helper.
    import lab_injected_decision
    lab_injected_decision.assert_no_test_fixture_active(
        cfg, stage='reference sweep startup')

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
        # ORDERING, AGAIN. My sink persisted the coverage record only AFTER
        # _coverage_verdict returned, so ANY exception inside the verdict -- a
        # malformed observation from a real server, say -- lost the observation
        # the sink exists to retain. This is the same defect root caught in the
        # attempt path, reintroduced one layer up. The observation is durable
        # before anything fallible reads it.
        ledger.append({'schema': 'live_ab/load_observation_raw-v1', **entry})
        try:
            verdict = _coverage_verdict(obs, record)
        except Exception as exc:
            failure = dict(key, schema='live_ab/load_coverage_failure-v1',
                           error='verdict raised: %s: %s' % (type(exc).__name__, exc))
            ledger.append(failure)
            invalid_coverage.append(failure)
            raise PreparationRefused(
                'the coverage verdict raised on %s; the raw attempt and the raw '
                'observation are retained and NO further verifier attempt is '
                'started' % (key,)) from exc
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
        # the SAME gate as the fresh path, before any success is returned
        _validate_acquisition(dest, prior, expect_mode, 'reused manifest')
        _record_access(dest, 'reuse', prior.get('roster_mode'), drift)
        return {'manifest': prior, 'roster_mode': prior.get('roster_mode'),
                'reused_existing_manifest': True, 'content_drift': drift}

    manifest = fetch_fn(dest, offline=offline)
    mode = manifest.get('roster_mode')
    _validate_acquisition(dest, manifest, expect_mode, 'fresh acquisition')
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
#: THE ONLY EVIDENCE KIND THAT MAY CERTIFY COVERAGE, root 2026-09-22 02:49:
#: "two distinct server-acknowledged decoding requests/occupied decoding slots
#:  throughout the verifier interval, recorded by pinned server-side lifecycle
#:  start/end events on the same host monotonic clock."
EVIDENCE_SERVER_LIFECYCLE = 'server_lifecycle'
#: Retained and recorded, never certifying. Root: "Stream events/timer lateness
#: can remain diagnostics."
EVIDENCE_CLIENT_ARRIVALS = 'client_stream_arrivals'
#: "Require concurrency at least two, not union coverage of one."
MIN_LOAD_CONCURRENCY = 2

#: WHICH CLOCK THE WINDOWS ARE ON, and it is checked rather than assumed.
#: Measured on this host: clock_gettime(CLOCK_MONOTONIC) -- what llama.cpp's
#: ggml_time_us() reads -- and time.monotonic() -- what lab_data stamps -- differ
#: by 694.15 s (results/live_ab/CLOCK_DOMAIN_FINDING.json). "The same host
#: monotonic clock" is not one clock, so an observation must NAME its clock and
#: it must be the one the verifier record uses. When root authorizes a change to
#: lab_data's stamping, this constant changes with it, in one place.
REQUIRED_WINDOW_CLOCK = 'time.monotonic'
#: The domain a server lifecycle observer reads, and the one v3 records carry.
POSIX_WINDOW_CLOCK = 'clock_gettime(CLOCK_MONOTONIC)'

INTERVAL_SCHEMA_V1 = 'live_ab/attempt_interval-v1'
#: v3 carries the NAMED POSIX readings beside the legacy ones.
INTERVAL_SCHEMA_V3 = 'live_ab/attempt_interval-v3'
INTERVAL_SCHEMA_V2 = 'live_ab/attempt_interval-v2'


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
    # DELEGATES to the one shared policy in lab_common (root 2026-09-22). Two
    # implementations of one directory rule is how a path quietly stops being
    # checked; the exception type stays PreparationRefused, which IS a
    # PreflightError, so existing callers and tests keep their contract.
    import os
    import tempfile as _tf
    try:
        lab_common.assert_tmpdir(cfg, stage='preparation', tmp_root=tmp_root)
    except lab_common.PreflightError as exc:
        raise PreparationRefused(str(exc)) from None
    declared = ((cfg or {}).get('sandbox') or {}).get('tmpdir')
    want = os.path.join(tmp_root, declared.split('/', 1)[1])
    effective = os.path.realpath(_tf.gettempdir())
    if False:
        raise PreparationRefused(
            'TMPDIR is %s but protocol 5.7 item 2 prescribes %s. The Seatbelt '
            'profile digest is a function of TMPDIR, so preparing under the wrong '
            'one silently produces a profile hash that no production run can '
            'reproduce. Export TMPDIR=%s and retry.'
            % (lab_common.tokenize_path(Path(effective)), want, want))
    return {'prescribed_tmpdir': want,
            'sandbox_base_dir': os.path.join(want, 'ls_sbx'),
            'checked': True}


def _finite(x: object) -> "float | None":
    """A finite float, or None. NaN and infinities are NOT numbers we may order."""
    try:
        v = float(x)                      # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if v != v or v in (float('inf'), float('-inf')):
        return None
    return v


def _coverage_verdict(obs: object, record: dict, *,
                      allow_legacy_audit: bool = False) -> Dict[str, Any]:
    """Whether the observation's certified active intervals CONTAIN the attempt.

    Root, 2026-09-21 21:50, on the arithmetic domain -- all three reproduced:
      * ``resolution_ms=-500`` EXPANDED a window and falsely certified coverage;
      * a reversed attempt ``[100.5, 100]`` returned valid;
      * a NaN attempt start returned valid, because comparisons on NaN do not
        establish the intended order.
    Finite ordered endpoints and a finite NONNEGATIVE error bound are now
    required before any coverage is computed.

    AND A CLAIM OF MINE THAT ROOT CORRECTED. I wrote that this discount meant
    "a coarse sampler cannot certify a gap it could not have seen". That
    overstates it. Root: "A series of active samples cannot become proof of
    continuous activity merely by shrinking the ends ... A sampler's cadence is
    not automatically an endpoint-error bound and says nothing about unobserved
    interior gaps."

    So the contract is now explicit and the arithmetic is conditional on it:
    each window must MEAN a continuously active interval on the verifier's own
    monotonic clock, and ``endpoint_error_s`` must be an INDEPENDENTLY JUSTIFIED
    bound on the uncertainty of that interval's endpoints -- not a sampling
    cadence reinterpreted as one. Under that contract, narrowing [a,b] to
    [a+e, b-e] is conservative. Without it, this function computes a union that
    means nothing, which is why the contract fields are required rather than
    defaulted.
    """
    if not isinstance(obs, dict):
        return {'valid': False, 'reason': 'observation is not a mapping'}
    if obs.get('active') is not True:
        return {'valid': False, 'reason': 'observation does not report active load'}
    if obs.get('window_id') in (None, ''):
        return {'valid': False, 'reason': 'observation omits window_id'}

    # --- WHAT KIND OF EVIDENCE THIS IS -------------------------------------
    # ROOT'S BINDING DESIGN CHOICE, 2026-09-22 02:49
    # (reviews/live_load_root_decision_20260922_0237.md):
    #
    #   "Define the load criterion operationally before collection: TWO DISTINCT
    #    SERVER-ACKNOWLEDGED DECODING REQUESTS/OCCUPIED DECODING SLOTS THROUGHOUT
    #    THE VERIFIER INTERVAL, recorded by pinned server-side lifecycle start/end
    #    events on the same host monotonic clock. ... Require concurrency at least
    #    two, not union coverage of one; use distinct source/request identities.
    #    ... Client POST-to-response outstanding intervals alone do not identify
    #    server decoding lifetime."
    #
    # My arrival instrument is therefore NOT certification and cannot be made into
    # it by any tolerance: a server may finish producing before buffered events
    # reach the client, and output at two instants does not establish activity
    # between them. Root: "Stream events/timer lateness can remain diagnostics."
    #
    # So the evidence kind is declared and checked FIRST, before any arithmetic.
    kind = obs.get('evidence_kind')
    if kind != EVIDENCE_SERVER_LIFECYCLE:
        return {'valid': False, 'evidence_kind': kind,
                'reason': 'coverage may be certified only from %r. This observation '
                          'declares %r. Root 2026-09-22: client POST-to-response '
                          'outstanding intervals and client stream arrivals do not '
                          'identify server decoding lifetime, and no gap tolerance '
                          'or endpoint bound converts them into it. Such evidence is '
                          'retained as a DIAGNOSTIC.'
                          % (EVIDENCE_SERVER_LIFECYCLE, kind)}
    # THE CLOCK IS NAMED AND CHECKED, not assumed. Which domain is required
    # depends on the record's schema, and the check happens in the schema branch
    # below; an observation that names NO domain is refused here.
    clock = obs.get('clock')
    if not isinstance(clock, str) or not clock:
        return {'valid': False, 'clock': clock,
                'reason': 'the observation names no clock domain. On this host '
                          'clock_gettime(CLOCK_MONOTONIC) and time.monotonic() '
                          'differ by 694 s and the gap grows at every sleep, so '
                          '"the same host monotonic clock" must be named and '
                          'checked, never assumed.'}
    if clock not in (REQUIRED_WINDOW_CLOCK, POSIX_WINDOW_CLOCK):
        return {'valid': False, 'clock': clock,
                'reason': 'unsupported clock domain %r; supported: %r, %r. An '
                          'unsupported clock refuses coverage and retains the '
                          'attempt.' % (clock, REQUIRED_WINDOW_CLOCK,
                                        POSIX_WINDOW_CLOCK)}
    if obs.get('lifecycle_complete') is not True:
        return {'valid': False,
                'reason': 'the observation does not assert lifecycle_complete. Root: '
                          '"Unknown/missing endpoint or lifecycle discontinuity '
                          'refuses coverage and retains the attempt; it does not '
                          'become a task exclusion."'}
    # STRICT. int() truncates toward zero and accepts numeric strings, so an
    # observation asking for 2.9 lifetimes was satisfied by 2 and the string '2'
    # was accepted as 2. A declaration that is not an integer is not a
    # declaration.
    required = obs.get('concurrency_required')
    if not isinstance(required, int) or isinstance(required, bool):
        return {'valid': False,
                'reason': 'concurrency_required must be an integer, got %r (%s); '
                          'int() would truncate 2.9 to 2 and accept the string "2"'
                          % (required, type(required).__name__)}
    if required < MIN_LOAD_CONCURRENCY:
        return {'valid': False,
                'reason': 'concurrency_required is %d; the operational load '
                          'definition requires at least %d distinct server-'
                          'acknowledged lifetimes, not union coverage of one'
                          % (required, MIN_LOAD_CONCURRENCY)}

    # --- the endpoint error bound: finite and NONNEGATIVE -------------------
    # `resolution_ms` is accepted as the legacy spelling, but it is read as an
    # endpoint ERROR BOUND, which root required be independently justified.
    raw_e = obs.get('endpoint_error_s')
    if raw_e is None and obs.get('resolution_ms') is not None:
        ms = _finite(obs.get('resolution_ms'))
        raw_e = None if ms is None else ms / 1000.0
    e = _finite(raw_e)
    if e is None:
        return {'valid': False,
                'reason': 'endpoint error bound is missing or not a finite number'}
    if e < 0:
        return {'valid': False,
                'reason': 'endpoint error bound is negative (%r); a negative bound '
                          'would EXPAND each window and certify coverage that was '
                          'never observed' % (raw_e,)}

    # --- the attempt interval: finite and ordered --------------------------
    # SCHEMA-DIRECTED PARSING, root 2026-09-21 22:56: "Use a declared
    # interval-version branch, NOT a fallback after failed numeric conversion ...
    # Missing, null or invalid v2 verifier endpoints refuse; older aliases cannot
    # rescue a malformed v2 record."
    #
    # My previous code fell back to the v1 aliases whenever either named endpoint
    # was nonfinite, so a v2-labelled record with a NaN named start and valid
    # aliases returned VALID. That is invalid-data substitution.
    #
    # Root also corrected my reasoning: certifying a genuinely WIDER legacy
    # interval is STRICTER, not looser, because activity must be proved
    # throughout it. Legacy evidence is therefore retained -- behind an explicit
    # audit route that names the version it certified, never as a silent rescue.
    schema = record.get('interval_schema')
    if schema == INTERVAL_SCHEMA_V3:
        # THE MATCHED DOMAIN, root 2026-09-22 03:19: "Compare server lifecycle
        # timestamps only to the matching CLOCK_MONOTONIC verifier interval ...
        # Do not compare a Python-monotonic interval to a POSIX-clock lifecycle,
        # even if both are on the same host."
        # HOLE (c), root 2026-09-22 04:02: "v3 record clock_domain_posix=
        # 'time.monotonic' and observation same legacy label -> coverage valid."
        # The check was EQUALITY of two labels, so two equally WRONG labels
        # matched. The domain must be the exact named POSIX constant, not merely
        # agreed between the two parties.
        if clock != POSIX_WINDOW_CLOCK:
            return {'valid': False, 'clock': clock,
                    'reason': 'a v3 record must be certified on the exact named '
                              'POSIX domain %r; the observation declares %r. Two '
                              'sides agreeing on a wrong label is not a matching '
                              'clock.' % (POSIX_WINDOW_CLOCK, clock)}
        if record.get('clock_domain_posix') != POSIX_WINDOW_CLOCK:
            return {'valid': False,
                    'reason': 'the v3 record declares POSIX domain %r, not the exact '
                              'named %r' % (record.get('clock_domain_posix'),
                                            POSIX_WINDOW_CLOCK)}
        # HOLES (a) and (b): identity must be PRESENT, NON-PLACEHOLDER and MATCHED
        # on both sides. Equality alone certified two absent identities (both
        # None), two 'unknown's, and ignored a host mismatch entirely.
        bad = _provenance_mismatch(record, obs)
        if bad is not None:
            return {'valid': False, 'reason': bad}
        if record.get('clock_domain_posix') != clock:
            return {'valid': False, 'clock': clock,
                    'reason': 'clock domain mismatch: the observation is on %r and '
                              'the v3 record names %r for its POSIX readings. A '
                              'mismatch refuses coverage and RETAINS the attempt; '
                              'it is never a task exclusion.'
                              % (clock, record.get('clock_domain_posix'))}
        s_ns = record.get('verification_started_posix_ns')
        e_ns = record.get('verification_ended_posix_ns')
        if not isinstance(s_ns, int) or not isinstance(e_ns, int):
            return {'valid': False, 'interval_version': INTERVAL_SCHEMA_V3,
                    'reason': 'a v3 record must carry INTEGER nanosecond POSIX '
                              'endpoints; got %r and %r. Unsupported clock or '
                              'malformed timing refuses coverage and retains the '
                              'attempt.' % (s_ns, e_ns)}
        start, end = s_ns / 1e9, e_ns / 1e9
        certified_version = INTERVAL_SCHEMA_V3
    elif schema == INTERVAL_SCHEMA_V2:
        start = _finite(record.get('verification_started_monotonic'))
        end = _finite(record.get('verification_ended_monotonic'))
        if start is None or end is None:
            return {'valid': False, 'interval_version': INTERVAL_SCHEMA_V2,
                    'reason': 'record declares %s but its named verifier endpoints '
                              'are missing, null or nonfinite; legacy aliases may '
                              'not rescue a malformed v2 record'
                              % INTERVAL_SCHEMA_V2}
        # HOLE (d), root 2026-09-22 04:02: an unsupported POSIX reader silently
        # emitted v2, and a legacy-domain observation then certified it -- "current
        # source can silently turn unavailable new instrumentation into accepted
        # legacy production." New production now requires v3. v1/v2 remain readable
        # ONLY through the explicit historical audit route, which names the version
        # it certifies; constructor compatibility must not let a new run downgrade
        # its own contract.
        if not allow_legacy_audit:
            return {'valid': False, 'interval_version': INTERVAL_SCHEMA_V2,
                    'reason': 'this is a PRODUCTION check and the record is %s. New '
                              'production requires %s with the named POSIX domain '
                              'and verified host/boot provenance; v2 is readable '
                              'only through the explicit historical audit route '
                              '(allow_legacy_audit=True).'
                              % (INTERVAL_SCHEMA_V2, INTERVAL_SCHEMA_V3)}
        if clock != REQUIRED_WINDOW_CLOCK:
            return {'valid': False, 'clock': clock,
                    'reason': 'a v2 record carries only %r endpoints and the '
                              'observation is on %r; the domains do not match'
                              % (REQUIRED_WINDOW_CLOCK, clock)}
        certified_version = INTERVAL_SCHEMA_V2
    elif schema in (None, INTERVAL_SCHEMA_V1) and allow_legacy_audit:
        start = _finite(record.get('started_monotonic'))
        end = _finite(record.get('ended_monotonic'))
        if start is None or end is None:
            return {'valid': False, 'interval_version': INTERVAL_SCHEMA_V1,
                    'reason': 'legacy audit record has no finite wider interval'}
        certified_version = INTERVAL_SCHEMA_V1
    elif schema in (None, INTERVAL_SCHEMA_V1):
        return {'valid': False, 'interval_version': schema,
                'reason': 'record is legacy (%r) and this is a PRODUCTION check; '
                          'legacy evidence is readable only through the explicit '
                          'audit route (allow_legacy_audit=True), which names the '
                          'version it certifies' % (schema,)}
    else:
        return {'valid': False, 'interval_version': schema,
                'reason': 'unsupported interval schema %r; an unknown version is a '
                          'schema error, not an invitation to guess an interval '
                          'from whatever field names are present' % (schema,)}
    if start is None or end is None:
        return {'valid': False,
                'reason': 'the attempt carries no finite monotonic endpoints, so no '
                          'window can be shown to contain it'}
    if end < start:
        return {'valid': False,
                'reason': 'the attempt interval is reversed (start %r > end %r)'
                          % (start, end)}
    # Root: "Uncertainty in verifier endpoints, if any, must EXPAND the verifier
    # interval rather than make coverage easier."
    # Root 2026-09-21 22:23: "`_finite(record.get('endpoint_error_s')) or 0.0`
    # collapses an explicitly invalid value to the same zero used for absence.
    # ... Default to zero only when the field is ABSENT; reject an explicitly
    # malformed value." Reproduced: NaN, +inf and the string 'invalid' all
    # returned valid coverage. An ABSENT field means "no stated uncertainty";
    # a PRESENT unusable one means the bound is unknown, which is not zero.
    # Root 2026-09-21 22:56: "explicit null is unknown and must REFUSE, not be
    # treated as absent." Absence means the contract's default of no stated
    # uncertainty; a present null means the bound was not determined.
    if 'endpoint_error_s' not in record:
        v_err = 0.0
    else:
        v_err = _finite(record.get('endpoint_error_s'))
        if v_err is None:
            return {'valid': False,
                    'reason': 'verifier endpoint_error_s is present but not a finite '
                              'number (%r); an unusable bound is not zero'
                              % (record.get('endpoint_error_s'),)}
    if v_err < 0:
        return {'valid': False, 'reason': 'verifier endpoint error bound is negative'}
    start, end = start - v_err, end + v_err

    windows = obs.get('active_windows')
    if not isinstance(windows, list) or not windows:
        return {'valid': False,
                'reason': 'observation carries no active_windows; a post-attempt '
                          'sample is not coverage of the interval'}
    certified: List[tuple] = []
    for w in windows:
        if not isinstance(w, dict):
            return {'valid': False, 'reason': 'an active window is not a mapping'}
        ws, we = _finite(w.get('start')), _finite(w.get('end'))
        if ws is None or we is None:
            return {'valid': False,
                    'reason': 'an active window lacks finite numeric endpoints'}
        if we < ws:
            return {'valid': False,
                    'reason': 'an active window is reversed (start %r > end %r)'
                              % (ws, we)}
        # DISTINCT SOURCE/REQUEST IDENTITY, root 2026-09-22: "use distinct
        # source/request identities". Two windows of the SAME lifetime must not
        # both count toward concurrency, and the reviewer noted my generator
        # named its lifetimes gen_000000.. with no per-source prefix, so two
        # sources routed into one observer would COLLIDE in identity. An
        # unidentified window cannot be counted at all.
        # IDENTITY MUST BE A STRING, not stringified. certified.append((..,
        # str(ident))) made distinctness a property of the Python repr: a slot
        # written once as 0 and once as '0' became TWO distinct lifetimes, which
        # is precisely the fabrication concurrency exists to prevent.
        ident = w.get('identity')
        if not isinstance(ident, str) or not ident:
            return {'valid': False,
                    'reason': 'an active window carries no string identity (got %r); '
                              'concurrency of at least %d DISTINCT server-'
                              'acknowledged lifetimes cannot be established from '
                              'anonymous windows, and stringifying a value would '
                              'make 0 and "0" two different slots'
                              % (w.get('identity'), MIN_LOAD_CONCURRENCY)}
        if we <= ws:
            return {'valid': False,
                    'reason': 'an active window has zero duration (start == end == '
                              '%r); an instant is not an occupied lifetime' % (ws,)}
        lo, hi = ws + e, we - e          # inward contraction, e >= 0 guaranteed
        if hi > lo:
            certified.append((lo, hi, ident))
    if not certified:
        return {'valid': False,
                'reason': 'no window survives its own endpoint error bound; nothing '
                          'is certified'}

    # --- CONCURRENCY, not union -------------------------------------------
    # THE REVIEWER'S FINDING, 2026-09-22 (reviews/live_load_review_20260922_0237.md
    # finding 1): "The specification prescribes two concurrent generations, whereas
    # _coverage_verdict accepts the UNION of windows: that verifies at least one
    # window covers a time, not two distinct concurrent loads. The saved
    # single-generation case expressly passes."
    #
    # Exactly right, and the single-generation case passing was the evidence. The
    # union walk below is replaced by a sweep over the number of DISTINCT
    # identities active at each instant, and the minimum of that count across the
    # whole attempt must reach the required concurrency.
    worst = _min_concurrency(certified, start, end)
    if worst['count'] < required:
        return {'valid': False,
                'concurrency_required': required,
                'concurrency_observed_min': worst['count'],
                'reason': 'at monotonic %.6f only %d distinct lifetime(s) cover the '
                          'attempt; %d are required. Union coverage by one lifetime '
                          'is not the operational load definition.'
                          % (worst['at'], worst['count'], required)}
    return {'valid': True,
            'interval_version': certified_version,
            'evidence_kind': kind,
            'concurrency_required': required,
            'concurrency_observed_min': worst['count'],
            'certified_interval': 'the verifier call inside the lock'
                                  if certified_version == INTERVAL_SCHEMA_V2
                                  else 'the legacy wider span including lock wait',
            'reason': 'at least %d distinct server-acknowledged decoding lifetimes '
                      'were occupied throughout the attempt interval' % required,
            'conditional_on': 'each window being a SERVER-ACKNOWLEDGED decoding '
                              'lifetime recorded from pinned server-side start/end '
                              'events on the same host monotonic clock as the '
                              'verifier. This asserts occupied decoding slots, NOT '
                              'continuously busy hardware: server scheduling pauses '
                              'inside a lifetime are part of the operational regime.'}


#: Values that are not identities, however equal two of them are.
PLACEHOLDER_IDENTITIES = frozenset({'', 'unknown', 'none', 'null', 'n/a', '-'})


def _provenance_mismatch(record: dict, obs: dict) -> Optional[str]:
    """Why these two readings are not on one timeline -- or None if they are.

    ROOT'S FOUR COUNTEREXAMPLES, 2026-09-22 04:02, all of which CERTIFIED:
      * record and observation both ``boot_id=None``
      * both ``boot_id='unknown'``
      * ``host_id='hostA'`` versus ``'hostB'``, same boot string (host ignored)
      * both relabelled to the legacy clock

    The first three share one cause: the check tested metadata EQUALITY, and two
    equally absent or equally unknown identities are equal. Equality is not
    evidence of origin. Presence, non-placeholder value and agreement are now all
    required, on BOTH sides, for BOTH identities.
    """
    for field, label in (('boot_id', 'kernel boot session'), ('host_id', 'host')):
        r, o = record.get(field), obs.get(field)
        for who, val in (('attempt record', r), ('observation', o)):
            if not isinstance(val, str) or val.strip().lower() in PLACEHOLDER_IDENTITIES:
                return ('the %s carries no usable %s identity (%s=%r). An absent or '
                        'placeholder identity is not an identity, and two equally '
                        'absent ones are not a match.' % (who, label, field, val))
        if r != o:
            return ('%s identity differs between the attempt record and the '
                    'observation (%s versus %s); the two readings are not on one '
                    'timeline' % (label, r, o))
    for field in ('boot_source', 'host_source'):
        if not record.get(field):
            return ('the attempt record does not declare %s; provenance must name '
                    'WHAT was read, not only that something was' % field)
    return None


def _min_concurrency(intervals: List[tuple], start: float,
                     end: float) -> Dict[str, Any]:
    """Fewest DISTINCT identities simultaneously active anywhere in [start, end].

    A sweep over interval endpoints: the active set changes only at a boundary,
    so the minimum over the closed attempt interval is attained on one of the
    segments between consecutive boundaries (or at ``start`` itself).

    Distinctness is by identity, so a lifetime that contributes two windows
    counts once. Closed intervals throughout: a lifetime that ends exactly when
    the attempt ends still covers it.
    """
    bounds = sorted({start, end} | {b for lo, hi, _ in intervals
                                    for b in (lo, hi) if start <= b <= end})
    worst_count, worst_at = None, start
    probes: List[float] = []
    for i, b in enumerate(bounds):
        probes.append(b)
        if i + 1 < len(bounds):
            probes.append((b + bounds[i + 1]) / 2.0)   # inside the open segment
    for t in probes:
        if t < start or t > end:
            continue
        active = {ident for lo, hi, ident in intervals if lo <= t <= hi}
        if worst_count is None or len(active) < worst_count:
            worst_count, worst_at = len(active), t
    return {'count': 0 if worst_count is None else worst_count, 'at': worst_at}

def _validate_acquisition(dest: Path, manifest: dict, expect_mode: "str | None",
                          path_label: str) -> None:
    """The single pre-return gate for BOTH acquisition paths.

    Root, 2026-09-22 00:01: "expect_mode='EXT' must refuse an S1 result EVEN WHEN
    S2 IS LEGITIMATELY ABSENT on that host. The expectation is a caller
    requirement, not a claim that missing bytes cannot occur ... Check it on every
    acquisition path, INCLUDING REUSE OF A PRIOR MANIFEST, before returning
    success. Verify required-source integrity in either mode; required S1
    corruption/missingness must never become success with a drift warning."

    My previous code checked the expectation only on the fresh-fetch path, and the
    reused-manifest path returned drift as a warning field. Both are closed here,
    in one place, so the two paths cannot diverge again.
    """
    mode = manifest.get('roster_mode')
    if expect_mode == 'EXT' and mode != 'EXT':
        raise PreparationRefused(
            '%s: a previous acquisition established roster_mode EXT and this one '
            'resolved %r. An explicit EXT expectation is BINDING even when S2 is '
            'legitimately absent: that mismatch is exactly what the expectation '
            'exists to surface. Restore the identical pinned bytes, or record a '
            'deliberate design decision to run a different study -- dropping the '
            'argument is not authority to erase the persisted expectation.'
            % (path_label, mode))

    # REQUIRED-SOURCE INTEGRITY, in EITHER mode. A required source that is absent
    # or whose bytes differ from the pin is a refusal, never a drift warning.
    # NO CALLER-VISIBLE BYPASS. Root 2026-09-22 00:34: "do not allow a normal
    # production configuration/entry point to clear required-byte validation."
    # The bypass keyword I added for synthetic fixtures is removed; tests now
    # patch lab_data.SOURCES to tiny real files and run the DEFAULT path.
    for name, spec in lab_data.SOURCES.items():
        if not spec.get('required'):
            continue
        f = dest / spec['filename']
        if not f.is_file():
            raise PreparationRefused(
                '%s: required source %s is absent from %s; a required source may '
                'never become success with a drift warning'
                % (path_label, name, lab_common.tokenize_path(dest)))
        if lab_common.sha256_file(f) != spec['sha256']:
            raise PreparationRefused(
                '%s: required source %s does not match its pinned sha256; refusing '
                'rather than reporting drift' % (path_label, name))


# ---------------------------------------------------------------------------
# Worker startup enforcement: BOTH ends, per root 2026-09-22 01:07
# ---------------------------------------------------------------------------
# "The supervisor must set and validate the child environment before launching
#  workers. Each actual worker must use the shared prescribed-directory check at
#  startup and after restart, before any model or sandbox dispatch. This also
#  covers direct invocation. The worker's RESOLVED directory is authoritative: an
#  environment string alone does not establish Python's resolved/cached temporary
#  directory. Do not change a running process's cache to force a pass."
#
# Two check points, because a single one misses a case: validating only at launch
# leaves a directly-invoked or restarted worker unguarded, and validating only in
# the worker allows a supervisor to create workers it should never have created.

def _safe_token(path: object) -> str:
    """Tokenized path, or a redacted marker when it cannot be tokenized."""
    try:
        return lab_common.tokenize_path(Path(str(path)))
    except Exception:
        return '<UNTOKENIZABLE-PATH-REDACTED>'


def launch_environment(cfg: dict, base_env: "dict | None" = None) -> Dict[str, str]:
    """The child environment a supervisor must use, validated BEFORE any worker.

    Returns the environment to pass to the child. Raises before a worker is
    created if the prescribed directory cannot be established, so no worker is
    ever spawned into a wrong TMPDIR.
    """
    import os
    declared = ((cfg or {}).get('sandbox') or {}).get('tmpdir')
    if declared != PRESCRIBED_TMPDIR_TOKEN:
        raise PreparationRefused(
            'config.sandbox.tmpdir is %r; protocol 5.7 item 2 prescribes %r. No '
            'worker is launched.' % (declared, PRESCRIBED_TMPDIR_TOKEN))
    want = '/private/tmp/' + declared.split('/', 1)[1]
    if not Path(want).is_dir():
        raise PreparationRefused(
            'the prescribed TMPDIR %s does not exist; create it before launching '
            'workers rather than letting each worker resolve elsewhere' % want)
    env = dict(os.environ if base_env is None else base_env)
    env['TMPDIR'] = want
    return env


def assert_worker_startup(cfg: dict, *, phase: str = 'startup') -> Dict[str, Any]:
    """The worker-side check. Call at startup AND after restart, BEFORE dispatch.

    Uses the SAME shared helper as preparation, so the two cannot drift. The
    worker's own RESOLVED temporary directory is authoritative -- root was
    explicit that an environment string does not establish what Python has
    already cached. This function therefore never mutates the cache to force a
    pass: a mismatched worker refuses and is replaced, it does not repair itself.
    """
    import os
    import tempfile as _tf
    checked = assert_prescribed_tmpdir(cfg)          # the shared helper
    env_str = os.environ.get('TMPDIR')
    resolved = os.path.realpath(_tf.gettempdir())
    if env_str and os.path.realpath(env_str) != resolved:
        # A DIAGNOSTIC MUST NOT BREAK THE REFUSAL IT REPORTS. tokenize_path raises
        # on a path outside the known roots, which is exactly the situation here,
        # so an untokenizable value is redacted rather than allowed to turn a
        # clean refusal into an UntokenizablePath traceback.
        raise PreparationRefused(
            'worker %s: TMPDIR env is %s but Python has RESOLVED %s. The resolved '
            'directory is authoritative and this process will not rewrite its own '
            'cache to agree; refuse and relaunch.'
            % (phase, _safe_token(env_str), _safe_token(resolved)))
    return {'phase': phase, 'resolved_tmpdir': resolved,
            'sandbox_base_dir': checked['sandbox_base_dir'],
            'checked_before_dispatch': True}
