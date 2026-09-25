"""The incremental immutable completed-shard receipt (root 22:20,
`reviews/eb1_eb5_final_subset_bounded_review_20260925_2220.md:19`): "Session60 may then
advance its already assigned EB2-EB4 model-free drivers and EB5 loaded-phase preparation, with
exact code/config/seed pins and incremental immutable completed-shard receipts."  design_notes/
DESIGN_PROPOSAL.md section 5 ("Shape of the incremental immutable completed-shard receipt") and
section 3 item 1 name this module as the FIRST commit: a thin, protocol-free layer over the
existing write-once and durable-append primitives, because every later stage-1..6 / 11.5 driver
needs it to emit a legal receipt.

What this module PERFORMS, and nothing else:

* :func:`shard_id` -- the shard id of a schedule row, a pure function of ``(driver,
  schedule_row)`` and never of wall-clock order (design_notes/DESIGN_PROPOSAL.md section 5:
  "a stable shard id determined by the pre-committed schedule row it fulfills ... never by
  wall-clock order").  ``driver`` is restricted to ``[A-Za-z0-9_-]+`` (adversarial review
  Finding 1): every driver name this design names -- `stage1`.."stage6", the section-11.5
  replay -- is already such a token, and without the restriction a crafted ``driver`` string
  could steer the receipt file outside its own directory (see :func:`write_shard_receipt`).
* :func:`validate_receipt` -- REFUSES (``ShardReceiptError``) a receipt missing any required
  field, an invalid ``pins`` block (including a ``pins.code``/``pins.data`` key that is
  absolute or carries a ``..`` segment, adversarial review Finding 3), malformed ``outputs``
  (same absolute/``..`` refusal on every key), a malformed or out-of-order
  ``start_utc``/``end_utc``, an ``outcome`` outside ``success``/``failure``/``unresolved``, a
  ``harness_pin_delta`` entry that is not itself a non-empty path string (Finding 7), or a
  ``shard_id`` that does not match :func:`shard_id` of its own ``driver``/``schedule_row`` --
  never a partial or best-effort check.
* :func:`write_shard_receipt` -- validates, then writes exactly once through
  ``lab_common.write_json_atomic(path, receipt, durable=True)`` (``lab_common.py:509-548``),
  reused verbatim, not reimplemented: an identical rewrite is a no-op (returns the same
  digest); different bytes raise the existing ``lab_common.WriteOnceViolation``
  (``lab_common.py:920``).  The receipt path is always ``<dir>/<shard_id>.json`` and is
  asserted, after resolution, to still be a child of ``dir`` (Finding 1's second layer, in
  case a receipt was built by hand rather than through :func:`shard_id`), so a shard's
  identity and its file name can never drift apart.  A ``FileNotFoundError`` from
  ``write_json_atomic``'s own ``os.replace`` -- reachable when two writers race on the exact
  same shard id, since its temp file name carries no per-process suffix
  (``lab_common.py:520``; adversarial review Finding 2, the same overlapping-restart shape as
  the killed 17:37Z start / refused 17:42Z run, ``eee9287``) -- is retried once as a plain
  write-once comparison against the race winner's now-existing file, so the loser is told
  ``WriteOnceViolation`` (or sees its own bytes accepted as a no-op), never crashes.
* :func:`completed_shards` -- the resume scan of ``lab_data.AttemptLedger``'s discipline
  (``lab_data.py:748``: "durable append-only sink ... loss or failure of the sink must stop
  preparation rather than silently continue") applied to a write-once receipt directory: it
  lists the shard ids already on disk and reads or rewrites NOTHING, exactly the "list every
  shard id already present ... treats each as immutable and done" resume rule of
  design_notes/DESIGN_PROPOSAL.md section 5.
* :func:`verify_shards` -- read-only.  Recomputes the schedule-row-to-receipt bijection
  design_notes/DESIGN_PROPOSAL.md section 5 names ("every row has exactly one receipt, every
  receipt maps to exactly one row") and each receipt's declared output hash against the actual
  file on disk, returning one finding per problem and an empty list when none exist.  A
  receipt file whose name does not match its own content ``shard_id`` is flagged
  ``misnamed_receipt`` rather than silently accepted (adversarial review Finding 4): the
  identity/filename bijection above only holds for files :func:`write_shard_receipt` itself
  wrote, and this is the read-only check for a directory that may hold other files too --
  found alongside whatever else that file's content implies, never in place of it.  It never
  writes anything, including to repair what it finds.

Deliberately NOT here (design_notes/DESIGN_PROPOSAL.md section 3 item 1: "Keep it free of any
protocol-specific stage logic"): no ``E_PHASE``/event-schema value, no stage 1-6 or 11.5
semantics, no server, no model, no schedule GENERATION (only the shape a schedule row must have
to be hashed).  This keeps the module importable by every future driver without any of them
importing each other's stage logic through it -- MATRIX row: ``lab_common`` only.

Prepared and checked by AI agent sessions; not human peer review or author sign-off
(protocol 14.7).
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path

import lab_common

#: This receipt's own schema tag, bumped on any incompatible shape change.
SCHEMA: str = 'live_ab/shard_receipt-v1'

#: The only legal values of a receipt's ``outcome`` (design_notes/DESIGN_PROPOSAL.md section 5:
#: "success / failure / unresolved -- never omitted").
OUTCOMES: tuple[str, ...] = ('success', 'failure', 'unresolved')

#: Every top-level key a receipt must carry; :func:`validate_receipt` names every one missing,
#: not just the first.
REQUIRED_FIELDS: tuple[str, ...] = (
    'schema', 'shard_id', 'driver', 'schedule_row', 'pins', 'inputs', 'outputs',
    'start_utc', 'end_utc', 'outcome', 'harness_pin_delta')

#: The four pins design_notes/DESIGN_PROPOSAL.md section 4 requires every receipt to carry,
#: "not a subset": code, config, seed, data.
REQUIRED_PIN_KEYS: tuple[str, ...] = ('code', 'config', 'seed', 'data')

_HEX64_RE = re.compile(r'^[0-9a-f]{64}$')
#: Every driver name design_notes/DESIGN_PROPOSAL.md section 2 names (`stage1` .. `stage6`,
#: the section-11.5 replay) already matches this; a `/`, `\`, or `..` component does not, and
#: unrestricted would let a crafted ``driver`` steer :func:`write_shard_receipt`'s output path
#: outside its own receipt directory (adversarial review Finding 1).
_SAFE_DRIVER_RE = re.compile(r'^[A-Za-z0-9_-]+$')
#: Same instant grammar ``lab_eventlog._ISO_RE`` enforces on every chain event
#: (``lab_eventlog.py:69``); duplicated rather than imported so this module keeps its own
#: MATRIX row (``lab_common`` only) and carries no protocol dependency.
_ISO_UTC_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$')


class ShardReceiptError(lab_common.LabError):
    """A receipt failed validation, or a shard id was asked for from a bad driver/row.  Root
    of every refusal this module raises; it is never a bare ``Exception``
    (``lab_common.py`` "every module raises only from this tree")."""


def shard_id(driver: str, schedule_row: Mapping) -> str:
    """[pure] The deterministic shard id of one schedule row: ``<driver>__<16 hex chars of
    sha256_canonical(schedule_row)>``.  A function of the row's content alone -- never of when,
    in what order, or how many times it is called (design_notes/DESIGN_PROPOSAL.md section 5).
    ``schedule_row`` must be a JSON object; anything a schedule generator would not itself
    produce (a set, a float NaN, a non-string key) is refused by ``canonical_json`` beneath
    this call, not silently coerced."""
    if not isinstance(driver, str) or not driver:
        raise ShardReceiptError('driver must be a non-empty string')
    if not _SAFE_DRIVER_RE.match(driver):
        raise ShardReceiptError(
            f'driver {driver!r} must match {_SAFE_DRIVER_RE.pattern} -- a path separator or '
            "'..' component could steer write_shard_receipt's output outside its own receipt "
            'directory (adversarial review Finding 1)')
    if not isinstance(schedule_row, Mapping):
        raise ShardReceiptError('schedule_row must be a JSON object')
    return f'{driver}__{lab_common.sha256_canonical(schedule_row)[:16]}'


def _parse_utc(value: object) -> datetime | None:
    """[pure] A calendar-valid UTC instant from an ISO-8601 ``...Z`` string, or ``None`` for
    anything else -- including a string that matches the grammar but names no real calendar
    instant (month 13, 30 February), mirroring ``lab_eventlog.parse_utc_instant``
    (``lab_eventlog.py:1218-1229``)."""
    if not isinstance(value, str) or not _ISO_UTC_RE.match(value):
        return None
    try:
        return datetime.strptime(value[:19], '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return None


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ShardReceiptError(message)


def _require_safe_relpath(name: object, what: str) -> None:
    """A path key (an ``outputs``, ``pins.code`` or ``pins.data`` key) must be a non-empty
    relative path with no ``..`` segment -- otherwise :func:`verify_shards` could be made to
    read, or a driver's output-hash bookkeeping could be made to name, a file entirely outside
    the declared ``root_for_outputs``/data root (adversarial review Finding 3)."""
    _require(isinstance(name, str) and bool(name),
             f'{what} must be a non-empty relative-path string')
    _require(not Path(name).is_absolute(),
             f'{what} {name!r} must be a relative path, not absolute')
    _require('..' not in Path(name).parts,
             f"{what} {name!r} may not contain a '..' path segment")


def _validate_pins(pins: object) -> None:
    _require(isinstance(pins, Mapping), 'pins must be a JSON object')
    missing = [k for k in REQUIRED_PIN_KEYS if k not in pins]
    _require(not missing, f'pins missing required key(s): {sorted(missing)}')
    code = pins['code']
    _require(isinstance(code, Mapping) and bool(code),
             'pins.code must be a non-empty {file path: sha256} object')
    for name, digest in code.items():
        _require_safe_relpath(name, 'pins.code key')
        _require(isinstance(digest, str) and bool(_HEX64_RE.match(digest)),
                 f'pins.code[{name!r}] must map a file path to a 64-hex sha256')
    config = pins['config']
    _require(isinstance(config, Mapping) and 'sha256' in config,
             "pins.config must be a JSON object carrying at least a 'sha256' key")
    _require(isinstance(config['sha256'], str) and bool(_HEX64_RE.match(config['sha256'])),
             'pins.config.sha256 must be a 64-hex sha256')
    _require(pins['seed'] is not None, 'pins.seed must not be null')
    data = pins['data']
    _require(isinstance(data, Mapping), 'pins.data must be a JSON object of {path: sha256}')
    for name, digest in data.items():
        _require_safe_relpath(name, 'pins.data key')
        _require(isinstance(digest, str) and bool(_HEX64_RE.match(digest)),
                 f'pins.data[{name!r}] must map to a 64-hex sha256')


def _validate_outputs(outputs: object) -> None:
    _require(isinstance(outputs, Mapping),
             'outputs must be a JSON object of {relative path: sha256}')
    for name, digest in outputs.items():
        _require_safe_relpath(name, 'outputs key')
        _require(isinstance(digest, str) and bool(_HEX64_RE.match(digest)),
                 f'outputs[{name!r}] must map to a 64-hex sha256')


def validate_receipt(receipt: object) -> None:
    """Refuse (``ShardReceiptError``, naming exactly what is wrong) any receipt missing a
    required field or carrying an invalid one.  Never partial: every structural problem is
    checked, and the first one found is raised (callers needing every problem at once should
    catch and retry field by field, as no driver in this repository does)."""
    _require(isinstance(receipt, Mapping), 'receipt must be a JSON object')
    missing = [k for k in REQUIRED_FIELDS if k not in receipt]
    _require(not missing, f'missing required field(s): {sorted(missing)}')
    _require(receipt['schema'] == SCHEMA,
             f"schema must be {SCHEMA!r}, got {receipt['schema']!r}")
    _require(isinstance(receipt['driver'], str) and bool(receipt['driver']),
             'driver must be a non-empty string')
    _require(isinstance(receipt['schedule_row'], Mapping), 'schedule_row must be a JSON object')
    _require(isinstance(receipt['shard_id'], str) and bool(receipt['shard_id']),
             'shard_id must be a non-empty string')
    expected = shard_id(receipt['driver'], receipt['schedule_row'])
    _require(receipt['shard_id'] == expected,
             f"shard_id {receipt['shard_id']!r} does not match the deterministic id "
             f"{expected!r} of its own (driver, schedule_row)")
    _validate_pins(receipt['pins'])
    _require(isinstance(receipt['inputs'], Mapping), 'inputs must be a JSON object')
    _validate_outputs(receipt['outputs'])
    start = _parse_utc(receipt['start_utc'])
    end = _parse_utc(receipt['end_utc'])
    _require(start is not None,
             f"start_utc must be an ISO-8601 UTC instant ending in 'Z', got "
             f"{receipt['start_utc']!r}")
    _require(end is not None,
             f"end_utc must be an ISO-8601 UTC instant ending in 'Z', got "
             f"{receipt['end_utc']!r}")
    _require(end >= start, f"end_utc {receipt['end_utc']!r} precedes start_utc "
                          f"{receipt['start_utc']!r}")
    _require(receipt['outcome'] in OUTCOMES,
             f"outcome must be one of {OUTCOMES}, got {receipt['outcome']!r}; never absent")
    _require(isinstance(receipt['harness_pin_delta'], list),
             'harness_pin_delta must be a list (empty when the driver touched no existing '
             'pinned file)')
    _require(all(isinstance(x, str) and bool(x) for x in receipt['harness_pin_delta']),
             'harness_pin_delta entries must each be a non-empty pinned-file-path string '
             '(adversarial review Finding 7 -- a garbage entry would silently weaken the '
             'harness-byte-impact audit trail root asked for)')


def write_shard_receipt(dir: str | Path, receipt: Mapping) -> str:
    """Validate ``receipt`` (:func:`validate_receipt`) and write it exactly once at
    ``<dir>/<shard_id>.json`` through ``lab_common.write_json_atomic(..., durable=True)``
    (``lab_common.py:509-548``): a byte-identical rewrite is a no-op that returns the same
    digest; different bytes raise ``lab_common.WriteOnceViolation`` (``lab_common.py:920``).
    ``dir`` is created if absent.  Returns the receipt's canonical sha256."""
    validate_receipt(receipt)
    d = Path(dir)
    d.mkdir(parents=True, exist_ok=True)
    d_resolved = d.resolve()
    path = (d / f"{receipt['shard_id']}.json").resolve()
    _require(path.parent == d_resolved,
             f"shard_id {receipt['shard_id']!r} would write outside receipt directory "
             f'{d_resolved} -- refused (adversarial review Finding 1; validate_receipt/'
             'shard_id already reject the driver strings that could cause this, so reaching '
             'here means a receipt was hand-built rather than produced through shard_id())')
    try:
        return lab_common.write_json_atomic(path, dict(receipt), durable=True)
    except FileNotFoundError:
        # lab_common.write_json_atomic derives its temp file name from the destination path
        # alone, with no per-process/random suffix (`lab_common.py:520`).  Two writers that
        # compute the SAME shard_id -- the overlapping-restart shape this project has already
        # hit once (killed 17:37Z start, refused 17:42Z run, `eee9287`) -- race on that shared
        # temp file, and the loser's own `os.replace` can raise FileNotFoundError instead of
        # write_json_atomic's own WriteOnceViolation (adversarial review Finding 2).  Since
        # `d.mkdir` above already guarantees path.parent exists, a FileNotFoundError here with
        # the destination now present is exactly that race, not a real missing-directory bug:
        # re-run write_json_atomic's own write-once comparison against the winner's file.  If
        # no winner file materialized, this was not a race and the error is real -- re-raise.
        if not path.exists():
            raise
        return lab_common.write_json_atomic(path, dict(receipt), durable=True)


def completed_shards(dir: str | Path) -> frozenset[str]:
    """The resume scan (design_notes/DESIGN_PROPOSAL.md section 5: "On restart, the driver
    first lists every shard id already present on disk ... and treats each as immutable and
    done").  Every shard's receipt path is always ``<dir>/<shard_id>.json``
    (:func:`write_shard_receipt`), so listing the directory's ``*.json`` stems is the whole
    scan -- no receipt is opened, parsed or rewritten.  ``dir`` absent is zero shards done, not
    an error: a driver's first attempt need not create the directory first."""
    d = Path(dir)
    if not d.is_dir():
        return frozenset()
    return frozenset(p.stem for p in d.glob('*.json') if p.is_file())


def verify_shards(dir: str | Path, schedule_rows: Iterable[tuple[str, Mapping]],
                  root_for_outputs: str | Path) -> list[dict]:
    """Read-only verifier.  ``schedule_rows`` is an iterable of ``(driver, schedule_row)``
    pairs -- exactly what :func:`shard_id` derives a receipt's own id from -- covering every row
    the frozen schedule expects a shard for.  Returns one finding dict per problem (key
    ``kind``), never fewer even when everything is fine (``[]``); writes and repairs nothing.

    Finding kinds: ``output_hash_mismatch`` (a receipt's declared output sha256 does not match
    the file at ``root_for_outputs`` / that relative path, or the file is missing);
    ``missing_receipt`` (a schedule row with no receipt); ``orphan_receipt`` (a receipt whose
    shard id matches no schedule row); ``duplicate_receipt`` (more than one receipt file
    declaring the same ``shard_id`` -- grouped by the CONTENT of ``shard_id``, not by file name,
    since a duplicate is exactly two files disagreeing with the one-file-per-id convention
    :func:`write_shard_receipt` itself enforces; no output check is attempted for a duplicated
    id, since which copy to trust is itself the finding); ``misnamed_receipt`` (a receipt file
    whose name does not match its own content ``shard_id`` -- :func:`write_shard_receipt` never
    produces this, only external corruption does; raised alongside, never instead of,
    ``duplicate_receipt``/``orphan_receipt``/``output_hash_mismatch`` when those also apply to
    the same file, since a wrong file name is a distinct problem from what the content itself
    says, adversarial review Finding 4); ``malformed_receipt`` (unparseable JSON, or a receipt
    :func:`validate_receipt` refuses).
    """
    d = Path(dir)
    root = Path(root_for_outputs)
    expected: dict[str, tuple[str, Mapping]] = {}
    for driver, row in schedule_rows:
        expected[shard_id(driver, row)] = (driver, row)

    findings: list[dict] = []
    receipts_by_shard: dict[str, list[Path]] = {}
    if d.is_dir():
        for path in sorted(d.glob('*.json')):
            try:
                obj = json.loads(path.read_text('utf-8'))
                validate_receipt(obj)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError,
                    ShardReceiptError) as exc:
                findings.append({'kind': 'malformed_receipt', 'file': str(path),
                                 'reason': str(exc)})
                continue
            if path.stem != obj['shard_id']:
                findings.append({'kind': 'misnamed_receipt', 'file': str(path),
                                 'shard_id': obj['shard_id']})
            receipts_by_shard.setdefault(obj['shard_id'], []).append(path)

    for sid in sorted(receipts_by_shard):
        files = receipts_by_shard[sid]
        if len(files) > 1:
            findings.append({'kind': 'duplicate_receipt', 'shard_id': sid,
                             'files': sorted(str(f) for f in files)})
            continue
        if sid not in expected:
            findings.append({'kind': 'orphan_receipt', 'shard_id': sid, 'file': str(files[0])})
            continue
        obj = json.loads(files[0].read_text('utf-8'))
        for relpath, want in sorted(obj['outputs'].items()):
            full = root / relpath
            found = lab_common.sha256_file(full) if full.is_file() else None
            if found != want:
                findings.append({'kind': 'output_hash_mismatch', 'shard_id': sid,
                                 'path': relpath, 'expected': want, 'found': found})

    for sid in sorted(set(expected) - set(receipts_by_shard)):
        findings.append({'kind': 'missing_receipt', 'shard_id': sid})

    return findings
