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

    ledger = open_ledger(ledger_path)        # created BEFORE the first attempt
    started = ledger.count
    coverage: List[dict] = []

    def sink(record: dict) -> None:
        # Load coverage is recorded ALONGSIDE the attempt, on the same host clock.
        if load_observer is not None:
            obs = load_observer()
            coverage.append({'uid': record.get('uid'),
                             'run_index': record.get('run_index'),
                             'observation': obs})
            record = dict(record, load_coverage=obs)
        # Unguarded on purpose: a failed durable append must stop preparation.
        ledger.append(record)

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

    outcome.update(completed=True, exclusions=len(exclusions),
                   records_retained=ledger.count - started,
                   load_coverage_records=len(coverage),
                   ended_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    # Retention must be demonstrable, not assumed: every exclusion's digest has to
    # reconstruct from what the ledger actually holds.
    reloaded = ledger.load()
    by_uid: Dict[str, List[dict]] = {}
    for rec in reloaded:
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
